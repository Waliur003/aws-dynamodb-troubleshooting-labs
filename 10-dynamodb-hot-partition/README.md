# Lab 10 — Amazon DynamoDB Hot Partition

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and remediate uneven partition-key traffic in Amazon DynamoDB.

In production, DynamoDB applications may experience performance problems when a large percentage of read or write operations target a small number of partition-key values.

This situation is commonly associated with a **hot partition key** or **hot partition**.

Although DynamoDB automatically distributes data and supports adaptive capacity, heavily concentrated workloads can encounter throughput limitations under certain conditions.

A production incident may produce throttling reasons such as:

```text
TableWriteKeyRangeThroughputExceeded
```

This indicates that write traffic has exceeded the throughput available to a particular key range.

However, not every uneven workload produces physical partition throttling.

In this lab, we create a DynamoDB table named `ddb-lab10-orders` in the `us-east-1` AWS Region.

The table uses a composite primary key:

- Partition key: `tenant_bucket`
- Sort key: `order_id`

We then develop a Python Boto3 workload generator to simulate a multi-tenant e-commerce application.

The initial workload creates 100 orders:

- 80 orders for one busy tenant.
- 20 orders distributed across ten other tenants.

This demonstrates a workload where 80% of writes target one logical partition-key value.

We investigate the distribution using Python, jq, AWS CLI, and CloudWatch metrics.

Next, we implement **ten-way write sharding**.

Instead of writing every order for the busiest tenant under one key, we distribute its 80 new orders across ten partition-key values.

Each shard receives eight records.

We then verify that all 80 sharded orders exist and can be retrieved using DynamoDB Query operations.

Finally, we review partition-key design, adaptive capacity, throughput throttling, security considerations, operational trade-offs, cost management, and safe resource cleanup.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Verify AWS CLI and Boto3
          |
          v
Configure Environment Variables
          |
          v
Create DynamoDB Table
          |
          v
Configure Composite Primary Key
          |
          v
Deploy Python Workload Generator
          |
          v
Generate 100 Initial Writes
          |
          v
80 Writes Target One Tenant
          |
          v
Analyze Partition-Key Distribution
          |
          v
Query Hot Tenant
          |
          v
Investigate CloudWatch Metrics
          |
          v
Understand Throttling Reasons
          |
          v
Root Cause Analysis
          |
          v
Implement Ten-Way Write Sharding
          |
          v
Generate 80 Sharded Writes
          |
          v
Verify Eight Writes Per Shard
          |
          v
Query All Ten Shards
          |
          v
Verify All 80 Orders
          |
          v
Review Read-Path Trade-offs
          |
          v
Security and Cost Investigation
          |
          v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-010 |
| Lab Name | DynamoDB Hot Partition |
| Difficulty | Advanced |
| Primary AWS Service | Amazon DynamoDB |
| Supporting Services | CloudWatch, IAM, STS |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Python 3, Boto3, Bash, jq |
| Table Name | `ddb-lab10-orders` |
| Partition Key | `tenant_bucket` |
| Sort Key | `order_id` |
| Key Types | String |
| Billing Mode | PAY_PER_REQUEST |
| Workload Type | Multi-tenant order processing |
| Initial Workload | 100 writes |
| Busy Tenant | TENANT-1001 |
| Busy Tenant Writes | 80 |
| Other Tenant Writes | 20 |
| Initial Hot-Key Concentration | 80% |
| Remediation | Write sharding |
| Number of Shards | 10 |
| Recovery Workload | 80 additional writes |
| Writes Per Shard | 8 |
| Primary Verification | Query and JSON analysis |
| Optional Diagnostic | TableWriteKeyRangeThroughputExceeded |
| Project Tag | DynamoDB-Troubleshooting-Lab10 |
| Cleanup | Delete temporary DynamoDB table |

### Learning Objectives

- Understand DynamoDB partition keys.
- Understand composite primary keys.
- Understand logical partition-key distribution.
- Understand physical partition throughput limitations.
- Identify skewed application access patterns.
- Distinguish hot-key traffic from confirmed throttling.
- Understand DynamoDB adaptive capacity.
- Investigate throttling reasons.
- Understand TableWriteKeyRangeThroughputExceeded.
- Use CloudWatch to investigate write throttling.
- Use Python and Boto3 for workload generation.
- Measure partition-key distribution.
- Implement write sharding.
- Understand deterministic shard assignment.
- Understand Query fan-out.
- Retrieve records from multiple shards.
- Understand write and read trade-offs.
- Apply cloud security considerations.
- Understand noisy-neighbor risks.
- Perform root cause analysis.
- Manage AWS costs.
- Clean up temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A multi-tenant e-commerce application uses Amazon DynamoDB to store customer orders.

Each tenant represents a business customer using the platform.

Most tenants generate relatively low request volumes.

However, a large enterprise customer starts a promotional campaign that produces significantly more orders than normal.

The tenant is identified as:

```text
TENANT-1001
```

The application's DynamoDB table uses the tenant identifier as its partition-key value.

The table also uses `order_id` as its sort key.

This design allows the application to query orders belonging to a particular tenant.

During the promotion, the busy tenant generates most of the application's writes.

Other tenants continue generating normal traffic.

The engineering team observes that access traffic is heavily concentrated on one logical partition key.

At sufficiently high request rates, this type of access pattern can contribute to hot-key or key-range throttling.

The team investigates:

- DynamoDB table configuration.
- Provisioned versus on-demand capacity.
- Partition-key design.
- Application request distribution.
- CloudWatch write metrics.
- DynamoDB throttling reasons.
- Potential physical partition throughput limits.

The engineers identify a workload-distribution concern: too much application traffic depends on one logical partition-key value.

The team evaluates write sharding to distribute the busiest tenant's orders across multiple key values.

After implementing sharding, the application spreads new writes across ten logical shard keys.

The workload becomes more evenly distributed.

### Incident Symptoms

Depending on actual production traffic, symptoms may include:

- Uneven key access.
- High traffic to one tenant.
- Increased DynamoDB request latency.
- Intermittent write throttling.
- Key-range throughput exceptions.
- Application retries.
- Increased request processing time.
- Reduced throughput efficiency.

### Important Lab Limitation

This lab uses a bounded workload of approximately 180 total write operations.

It demonstrates workload skew and improved key distribution.

It does **not** intentionally generate enough traffic to guarantee physical partition throttling.

Actual throttling must be confirmed using DynamoDB exception details and monitoring.

### Business Impact

At production scale, hot-key traffic may contribute to:

- Delayed order submissions.
- Increased API latency.
- Failed database writes.
- Application retry storms.
- Reduced customer experience.
- Noisy-neighbor problems.
- Higher infrastructure costs.
- Availability risks.

### Incident Objective

Identify a potentially problematic partition-key access pattern and demonstrate a more distributed data model without unnecessarily generating high-cost traffic.

---

## 3. AWS Architecture

### Original Architecture

```text
                   Order Application
                           |
                           v
                    Incoming Orders
                           |
                  +--------+--------+
                  |                 |
                  v                 v
             TENANT-1001       Other Tenants
                  |                 |
                  v                 v
               80 Writes        20 Writes
                  |                 |
                  v                 v
            One Logical Key     Ten Other Keys
                  |                 |
                  v                 v
             Concentrated       Distributed
                Access            Access
                  |
                  v
          Potential Hot-Key Pressure
```

### Broken Access Pattern

```text
                 DynamoDB Table
                  ddb-lab10-orders
                         |
                         v
                 tenant_bucket
                         |
                         v
                    TENANT-1001
                         |
                  +------+------+ 
                  |      |      |
                  v      v      v
                Order  Order  Order
                  |      |      |
                  +------+------+
                         |
                         v
                 80% of Test Writes
                         |
                         v
                Uneven Key Distribution
```

### Recovered Architecture

```text
                 Order Application
                         |
                         v
                   Shard Logic
                         |
               +---------+---------+
               |         |         |
               v         v         v
           Shard 00  Shard 01   ... Shard 09
               |         |         |
               v         v         v
            8 Writes  8 Writes  ... 8 Writes
               |         |         |
               +---------+---------+
                         |
                         v
                    DynamoDB
                         |
                         v
               More Distributed Access
```

### AWS Components

| Component | Purpose |
|---|---|
| DynamoDB | Stores multi-tenant order data |
| Composite Primary Key | Identifies tenant buckets and individual orders |
| Partition Key | Determines logical access grouping |
| Sort Key | Identifies records within a partition key |
| Boto3 | Generates controlled workloads |
| BatchWriteItem | Writes multiple items efficiently |
| Query | Retrieves partition-specific records |
| DescribeTable | Inspects table configuration |
| CloudWatch | Provides capacity and throttling metrics |
| IAM | Controls DynamoDB access |
| AWS STS | Verifies AWS identity |
| Python Counter | Measures logical key distribution |
| jq | Validates workload evidence |

---

## 4. Understanding DynamoDB Partitions

DynamoDB distributes table data across physical storage partitions.

A partition key is used in determining where data is stored.

A composite primary key includes:

```text
Partition Key + Sort Key
```

For this lab:

```text
tenant_bucket + order_id
```

### Example

| tenant_bucket | order_id |
|---|---|
| TENANT-1001 | HOT-0000 |
| TENANT-1001 | HOT-0001 |
| TENANT-1001 | HOT-0002 |
| TENANT-2000 | OTHER-0000 |

The first three records share a partition-key value but have different sort keys.

### Logical vs. Physical Partition

A logical partition-key value is the value used by an application to group records.

A physical partition is part of DynamoDB's underlying storage infrastructure.

These concepts are related but not identical.

DynamoDB may distribute item collections across physical partitions depending on conditions such as data size, access patterns, and index configuration.

### Production Lesson

Concentrating requests on one logical partition key can create throughput risks under sufficiently high demand, but the logical-key distribution alone does not prove physical partition throttling.

---

## 5. Understanding Hot Partitions

A hot partition is associated with disproportionate access to a limited part of DynamoDB's partitioned data.

### Example

```text
TENANT-1001  → 80 Writes

TENANT-2000  →  2 Writes
TENANT-2001  →  2 Writes
TENANT-2002  →  2 Writes
TENANT-2003  →  2 Writes
TENANT-2004  →  2 Writes
TENANT-2005  →  2 Writes
TENANT-2006  →  2 Writes
TENANT-2007  →  2 Writes
TENANT-2008  →  2 Writes
TENANT-2009  →  2 Writes
```

### Initial Distribution

| Measurement | Result |
|---|---:|
| Total Writes | 100 |
| Hot Tenant Writes | 80 |
| Other Tenant Writes | 20 |
| Hot Tenant Share | 80% |
| Other Tenant Share | 20% |

### Common Causes

- Low-cardinality partition keys.
- One unusually busy customer.
- One high-volume event source.
- Concentrated reads.
- Concentrated writes.
- Inappropriate key design.
- Uneven traffic distribution.

### Important Distinction

A hot logical key can become a performance concern, but DynamoDB adaptive capacity may accommodate the pattern without throttling.

Performance troubleshooting must use actual AWS diagnostics.

---

## 6. Understanding DynamoDB Throughput Limits

DynamoDB partition throughput is not unlimited.

A physical partition supports up to approximately:

| Operation | Throughput |
|---|---|
| Standard writes | 1,000 write capacity units per second |
| Strongly consistent reads | 3,000 read capacity units per second |
| Eventually consistent reads | Up to 6,000 read units per second for 4-KB items |

These limits are relevant to partition-level throughput analysis.

Actual application performance also depends on item size, partition-key design, capacity mode, adaptive capacity, and other applicable limits.

### Example

If a single hot key generates a large number of writes every second, it may eventually encounter a key-range throughput limitation.

Increasing overall table capacity does not necessarily eliminate every partition-level bottleneck.

### Production Principle

Always identify the actual limiting resource before selecting a remediation.

---

## 7. Understanding Throttling Reasons

DynamoDB can return structured throttling reasons.

These help identify whether the limitation involves:

- Table provisioned capacity.
- Index provisioned capacity.
- Physical key-range throughput.
- On-demand throughput limits.
- Account-level throughput limits.

### Common Write Throttling Reasons

| Throttling Reason | Meaning |
|---|---|
| TableWriteProvisionedThroughputExceeded | Table provisioned write capacity exceeded |
| TableWriteKeyRangeThroughputExceeded | Table key-range write throughput exceeded |
| IndexWriteProvisionedThroughputExceeded | GSI provisioned write capacity exceeded |
| IndexWriteKeyRangeThroughputExceeded | GSI key-range write throughput exceeded |
| TableWriteMaxOnDemandThroughputExceeded | Configured on-demand write limit exceeded |

### Key Distinction

```text
TableWriteProvisionedThroughputExceeded
```

indicates a different bottleneck from:

```text
TableWriteKeyRangeThroughputExceeded
```

A partition-key redesign is especially relevant when traffic concentration is confirmed to be a key-range bottleneck.

---

## 8. Understanding DynamoDB Adaptive Capacity

DynamoDB adaptive capacity helps tables handle uneven traffic patterns.

It can allocate more throughput to heavily accessed partitions within the applicable table and physical partition limits.

DynamoDB may also split partitions to improve performance under suitable conditions.

### Adaptive Capacity Benefits

- Helps accommodate uneven demand.
- Reduces some effects of traffic skew.
- Improves throughput utilization.
- Reduces the need for unnecessary manual changes.

### Important Limitations

Adaptive capacity does not guarantee that every hot-key workload can scale indefinitely.

Very concentrated workloads may still encounter key-range limits.

### Production Lesson

Do not automatically add write sharding to every application.

First investigate whether the current data model and DynamoDB adaptive capacity already satisfy the workload's performance requirements.

---

## 9. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Python 3.
- Boto3.
- Bash.
- jq.
- AWS account.

### Relevant IAM Actions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:PutItem
dynamodb:BatchWriteItem
dynamodb:Query
dynamodb:GetItem
dynamodb:ListTagsOfResource
dynamodb:DeleteTable

cloudwatch:GetMetricStatistics
```

These are relevant actions, not a complete IAM policy.

### Safety Requirements

- Use a temporary DynamoDB table.
- Avoid production load testing.
- Keep workload size bounded.
- Do not intentionally overwhelm AWS services.
- Use fabricated tenant identifiers.
- Avoid infinite loops.
- Verify AWS Region and account.
- Confirm tags before deletion.
- Monitor costs.

### Lab Workload Limit

The planned workload contains:

```text
Original Workload: 100 Writes

Sharded Workload: 80 Writes

Total: 180 Writes
```

Repeated test executions may overwrite items with the same keys and should not be used as uncontrolled stress tests.

---

## 10. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 10-dynamodb-hot-partition

cd 10-dynamodb-hot-partition
```

### Step 2 — Verify Tools

```bash
aws --version

python3 --version

jq --version

aws sts get-caller-identity
```

### Step 3 — Install Dependencies

```bash
sudo apt update

sudo apt install -y python3-venv jq
```

### Step 4 — Create Virtual Environment

```bash
python3 -m venv .venv

source .venv/bin/activate
```

### Step 5 — Install Boto3

```bash
python -m pip install boto3
```

### Step 6 — Verify Installation

```bash
python -c "import boto3; print('Boto3 ready')"
```

### Step 7 — Configure Variables

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export TABLE_NAME="ddb-lab10-orders"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab10"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"
```

### Step 8 — Verify

```bash
echo "$AWS_REGION"

echo "$TABLE_NAME"

echo "$TABLE_ARN"
```

### Step 9 — Prepare Evidence

```bash
mkdir -p evidence
```

### Step 10 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
.venv/
evidence/
lab10-resources.env

__pycache__/
*.pyc
*.log

.env
.env.*
*.pem
*.key
EOF
```

---

## 11. Verify AWS Account and Resources

### Step 1 — Verify AWS Identity

```bash
aws sts get-caller-identity
```

### Step 2 — Verify Region

```bash
echo "$AWS_REGION"
```

Expected:

```text
us-east-1
```

### Step 3 — Verify Table Does Not Exist

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected before creation:

```text
ResourceNotFoundException
```

If a resource with the same name already exists, verify ownership before continuing.

---

## 12. Create DynamoDB Table

### Step 1 — Create Table

```bash
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=tenant_bucket,AttributeType=S \
    AttributeName=order_id,AttributeType=S \
  --key-schema \
    AttributeName=tenant_bucket,KeyType=HASH \
    AttributeName=order_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 2 — Wait for ACTIVE Status

```bash
aws dynamodb wait table-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    Name:TableName,
    Status:TableStatus,
    KeySchema:KeySchema
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
Status = ACTIVE

tenant_bucket = HASH

order_id = RANGE
```

### Step 4 — Save Evidence

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/table-description.json
```

---

## 13. Create Python Workload Generator

### Step 1 — Create `workload.py`

```python
import argparse
import json
from collections import Counter
from datetime import datetime, timezone

import boto3


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--table", required=True)

    parser.add_argument(
        "--region",
        default="us-east-1"
    )

    parser.add_argument(
        "--mode",
        choices=["hot", "sharded"],
        required=True
    )

    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    dynamodb = boto3.resource(
        "dynamodb",
        region_name=args.region
    )

    table = dynamodb.Table(args.table)

    records = []
    counts = Counter()

    if args.mode == "hot":

        # 80 writes to one logical partition key.
        for i in range(80):

            records.append({
                "tenant_bucket": "TENANT-1001",
                "tenant_id": "TENANT-1001",
                "order_id": f"HOT-{i:04d}",
                "status": "PENDING",
                "amount": 100
            })

        # 20 writes across 10 other tenant keys.
        for i in range(20):

            tenant = f"TENANT-{2000 + (i % 10)}"

            records.append({
                "tenant_bucket": tenant,
                "tenant_id": tenant,
                "order_id": f"OTHER-{i:04d}",
                "status": "PENDING",
                "amount": 100
            })

    else:

        # 80 writes distributed across 10 shard keys.
        for i in range(80):

            shard = i % 10

            records.append({
                "tenant_bucket": f"TENANT-1001#{shard:02d}",
                "tenant_id": "TENANT-1001",
                "order_id": f"SHARD-{i:04d}",
                "status": "PENDING",
                "amount": 100
            })

    # Batch writer retries unprocessed batch items.
    with table.batch_writer() as batch:

        for item in records:

            batch.put_item(Item=item)

            counts[item["tenant_bucket"]] += 1

    result = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "mode": args.mode,

        "table": args.table,

        "attempted": len(records),

        "completed": len(records),

        "partition_key_counts": dict(
            sorted(counts.items())
        ),

        "largest_partition_key_count": max(
            counts.values()
        )
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

### Step 2 — Verify Python Syntax

```bash
python -m py_compile workload.py
```

### Step 3 — Understand the Script

| Component | Purpose |
|---|---|
| argparse | Controls workload settings |
| boto3.resource | Connects to DynamoDB |
| table.batch_writer | Writes batches and retries unprocessed items |
| Counter | Measures distribution |
| hot mode | Creates concentrated writes |
| sharded mode | Creates distributed writes |
| JSON summary | Records test evidence |

### Important Limitation

The `completed` field represents successful completion of the batch writer without an unhandled exception.

It is not a precise per-request performance benchmark.

The partition-key counts represent the generated write workload.

---

## 14. Fault Injection — Generate Hot-Key Workload

### Step 1 — Execute Initial Workload

```bash
python workload.py \
  --table "$TABLE_NAME" \
  --region "$AWS_REGION" \
  --mode hot \
  --output evidence/hot-workload.json
```

### Step 2 — Inspect Results

```bash
jq . evidence/hot-workload.json
```

Expected relevant summary:

```json
{
  "mode": "hot",
  "attempted": 100,
  "completed": 100,
  "largest_partition_key_count": 80
}
```

### Step 3 — Inspect Key Distribution

```bash
jq -r '
  .partition_key_counts |
  to_entries |
  sort_by(-.value)[] |
  "\(.key) \(.value)"
' evidence/hot-workload.json
```

Expected:

```text
TENANT-1001 80

TENANT-2000 2
TENANT-2001 2
TENANT-2002 2
TENANT-2003 2
TENANT-2004 2
TENANT-2005 2
TENANT-2006 2
TENANT-2007 2
TENANT-2008 2
TENANT-2009 2
```

### Step 4 — Calculate Concentration

```bash
jq '
  {
    total_writes: .attempted,

    hot_key_writes:
      .partition_key_counts["TENANT-1001"],

    hot_key_percentage:
      (
        .partition_key_counts["TENANT-1001"]
        / .attempted * 100
      )
  }
' evidence/hot-workload.json
```

Expected:

```json
{
  "total_writes": 100,
  "hot_key_writes": 80,
  "hot_key_percentage": 80
}
```

### Fault Findings

| Measurement | Result |
|---|---:|
| Total Writes | 100 |
| Hot Tenant | TENANT-1001 |
| Hot Tenant Writes | 80 |
| Other Tenant Writes | 20 |
| Hot-Key Concentration | 80% |

### Investigation Conclusion

The original application workload is heavily concentrated on one logical partition-key value.

This demonstrates a potential hot-key design concern.

---

## 15. Verify Hot-Key Records in DynamoDB

### Step 1 — Query Hot Tenant

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression \
    "tenant_bucket = :tenant" \
  --expression-attribute-values '{
    ":tenant": {"S": "TENANT-1001"}
  }' \
  --select COUNT \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
Count = 80
```

### Step 2 — Save Evidence

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression \
    "tenant_bucket = :tenant" \
  --expression-attribute-values '{
    ":tenant": {"S": "TENANT-1001"}
  }' \
  --select COUNT \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/hot-key-query.json
```

### Step 3 — Validate

```bash
jq -e '.Count == 80' \
  evidence/hot-key-query.json
```

Expected:

```text
true
```

### Step 4 — Query Normal Tenant

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression \
    "tenant_bucket = :tenant" \
  --expression-attribute-values '{
    ":tenant": {"S": "TENANT-2000"}
  }' \
  --select COUNT \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
Count = 2
```

### Comparison

| Tenant | Records |
|---|---:|
| TENANT-1001 | 80 |
| TENANT-2000 | 2 |

The comparison confirms a large imbalance in records written per logical partition-key value.

---

## 16. Investigate DynamoDB Throttling

### Production Scenario

A high-volume application may return a throttling exception when request demand exceeds available throughput.

For a physical key-range write bottleneck, an applicable throttling reason is:

```text
TableWriteKeyRangeThroughputExceeded
```

### Throttling Investigation Workflow

```text
Application Write Failure
          |
          v
Inspect ClientError
          |
          v
Read ThrottlingReasons
          |
          v
Identify Limiting Resource
          |
     +----+----+
     |         |
     v         v
Table Limit   Key-Range Limit
     |         |
     v         v
Capacity      Access Pattern
Planning      Investigation
     |         |
     v         v
Adjust        Redesign Keys
Capacity      if Appropriate
```

### Example Boto3 Exception Inspection

The following example shows how an application can inspect an actual throttling exception:

```python
from botocore.exceptions import ClientError

try:
    # Execute an application DynamoDB write here.
    pass

except ClientError as error:
    response = error.response

    print(response.get("Error", {}))

    print(
        response.get("ThrottlingReasons", [])
    )
```

This example is for understanding error handling.

It is not an additional fault-injection script.

### Important Note

If the lab produces no throttling exception, do not report an actual TableWriteKeyRangeThroughputExceeded incident.

The confirmed observation remains the uneven logical partition-key distribution.

---

## 17. CloudWatch Investigation

CloudWatch provides operational metrics for DynamoDB throughput and throttling.

### Relevant Metrics

| Metric | Purpose |
|---|---|
| ConsumedWriteCapacityUnits | Consumed write capacity |
| WriteThrottleEvents | Write throttling activity |
| WriteKeyRangeThroughputThrottleEvents | Key-range-related write throttling |
| ThrottledRequests | Requests experiencing throttling |
| SuccessfulRequestLatency | Successful request latency |

### Step 1 — Configure Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' \
  '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u \
  '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect Consumed Write Capacity

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Write Throttling

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name WriteThrottleEvents \
  --dimensions Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Key-Range Throttling

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name WriteKeyRangeThroughputThrottleEvents \
  --dimensions Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 5 — Save Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name WriteKeyRangeThroughputThrottleEvents \
  --dimensions Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION" \
  > evidence/keyrange-throttling-metrics.json
```

### Monitoring Interpretation

The workload's concentration does not guarantee key-range throttle events.

If the metric returns zero or no datapoints, report that no throttling was confirmed by the metric.

CloudWatch datapoints may also be delayed.

---

## 18. Investigate Hot Keys With Contributor Insights

CloudWatch Contributor Insights for DynamoDB can help identify frequently accessed or throttled partition keys.

### Production Uses

- Identify high-traffic keys.
- Investigate skewed access.
- Analyze throttled keys.
- Support data-model optimization.
- Investigate noisy tenants.

### Example Production Investigation

```text
DynamoDB Throttling
          |
          v
CloudWatch Contributor Insights
          |
          v
Identify Frequently Accessed Keys
          |
          v
Find Hot Tenant
          |
          v
Analyze Application Access Pattern
          |
          v
Evaluate Write Sharding
```

### Important Cost Consideration

Contributor Insights may incur additional charges.

We do not enable it in this lab.

Instead, the Python workload generator produces local distribution evidence.

---

## 19. Root Cause Analysis

### Primary Finding

The busiest tenant accounts for 80% of the initial write workload.

The application uses the tenant ID directly as the DynamoDB partition-key value.

This concentrates traffic on one logical key.

### Root Cause Diagram

```text
Multi-Tenant Application
          |
          v
Uneven Tenant Traffic
          |
          v
One Enterprise Tenant Dominates
          |
          v
All Writes Use Same Partition Key
          |
          v
80% of Writes Target TENANT-1001
          |
          v
Potential Throughput Concentration
          |
          v
Evaluate Data Model
          |
          v
Write Sharding
```

### Five Whys

**Why 1 — Why is the workload concentrated?**

Most writes target TENANT-1001.

**Why 2 — Why do they target one key?**

The application uses the tenant identifier directly as the partition key.

**Why 3 — Why can this become a problem?**

At sufficiently high traffic levels, key-range throughput may become a bottleneck.

**Why 4 — Why might increasing table capacity not fully resolve it?**

The limiting resource may be a particular key range rather than total table capacity.

**Why 5 — How can it be improved?**

Evaluate partition-key redesign, write sharding, workload smoothing, and appropriate capacity planning.

### Root Cause Conclusion

The lab demonstrates a potentially problematic logical key design.

A physical partition bottleneck is not claimed without supporting DynamoDB metrics or exception details.

---

## 20. Remediation — Implement Write Sharding

### Remediation Objective

Distribute writes for the busiest tenant across ten logical partition-key values.

### Before

```text
TENANT-1001
    |
    v
80 Writes
```

### After

```text
TENANT-1001#00 → 8 Writes
TENANT-1001#01 → 8 Writes
TENANT-1001#02 → 8 Writes
TENANT-1001#03 → 8 Writes
TENANT-1001#04 → 8 Writes
TENANT-1001#05 → 8 Writes
TENANT-1001#06 → 8 Writes
TENANT-1001#07 → 8 Writes
TENANT-1001#08 → 8 Writes
TENANT-1001#09 → 8 Writes
```

### Step 1 — Run Sharded Workload

```bash
python workload.py \
  --table "$TABLE_NAME" \
  --region "$AWS_REGION" \
  --mode sharded \
  --output evidence/sharded-workload.json
```

### Step 2 — Inspect Results

```bash
jq . evidence/sharded-workload.json
```

### Step 3 — Display Shard Counts

```bash
jq -r '
  .partition_key_counts |
  to_entries |
  sort_by(.key)[] |
  "\(.key) \(.value)"
' evidence/sharded-workload.json
```

Expected:

```text
TENANT-1001#00 8
TENANT-1001#01 8
TENANT-1001#02 8
TENANT-1001#03 8
TENANT-1001#04 8
TENANT-1001#05 8
TENANT-1001#06 8
TENANT-1001#07 8
TENANT-1001#08 8
TENANT-1001#09 8
```

### Step 4 — Validate Distribution

```bash
jq -e '
  .attempted == 80 and
  .completed == 80 and
  (.partition_key_counts | length) == 10 and
  ([.partition_key_counts[]] | all(. == 8))
' evidence/sharded-workload.json
```

Expected:

```text
true
```

### Remediation Finding

The sharded workload distributes 80 writes over ten partition-key values.

This reduces the concentration per logical key from 80 writes to eight writes in this controlled workload.

---

## 21. Compare Before and After

### Before Remediation

| Key | Writes |
|---|---:|
| TENANT-1001 | 80 |
| Other Tenants Combined | 20 |

### After Remediation

| Shard | Writes |
|---|---:|
| TENANT-1001#00 | 8 |
| TENANT-1001#01 | 8 |
| TENANT-1001#02 | 8 |
| TENANT-1001#03 | 8 |
| TENANT-1001#04 | 8 |
| TENANT-1001#05 | 8 |
| TENANT-1001#06 | 8 |
| TENANT-1001#07 | 8 |
| TENANT-1001#08 | 8 |
| TENANT-1001#09 | 8 |
| **Total** | **80** |

### Distribution Comparison

| Measurement | Original | Sharded |
|---|---:|---:|
| Busy Tenant Writes | 80 | 80 |
| Busy Tenant Partition Keys | 1 | 10 |
| Maximum Writes Per Busy-Tenant Key | 80 | 8 |
| Logical Distribution | Concentrated | Distributed |
| Physical Throttling Reduction | Not measured | Not measured |

### Important Conclusion

The lab proves that the logical key distribution improved.

It does not benchmark real production throughput or latency.

---

## 22. Verify Sharded Records

### Step 1 — Query Shard 00

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression \
    "tenant_bucket = :bucket" \
  --expression-attribute-values '{
    ":bucket": {"S": "TENANT-1001#00"}
  }' \
  --select COUNT \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
Count = 8
```

### Step 2 — Query Every Shard

```bash
for i in {0..9}; do

  printf -v shard "%02d" "$i"

  echo "Checking shard $shard"

  aws dynamodb query \
    --table-name "$TABLE_NAME" \
    --key-condition-expression \
      "tenant_bucket = :bucket" \
    --expression-attribute-values "{
      \":bucket\": {
        \"S\": \"TENANT-1001#${shard}\"
      }
    }" \
    --select COUNT \
    --consistent-read \
    --query Count \
    --output text \
    --region "$AWS_REGION"

done
```

Expected: ten counts, each equal to `8`.

### Step 3 — Save Shard 00 Evidence

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression \
    "tenant_bucket = :bucket" \
  --expression-attribute-values '{
    ":bucket": {"S": "TENANT-1001#00"}
  }' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/shard00-items.json
```

### Step 4 — Validate Shard 00

```bash
jq -e '
  .Count == 8 and
  ([.Items[].tenant_bucket.S] |
    all(. == "TENANT-1001#00"))
' evidence/shard00-items.json
```

Expected:

```text
true
```

### Recovery Finding

Each shard contains the expected subset of the new workload.

---

## 23. Verify All Sharded Orders

### Step 1 — Save All Ten Shard Queries

```bash
for i in {0..9}; do

  printf -v shard "%02d" "$i"

  aws dynamodb query \
    --table-name "$TABLE_NAME" \
    --key-condition-expression \
      "tenant_bucket = :bucket" \
    --expression-attribute-values "{
      \":bucket\": {
        \"S\": \"TENANT-1001#${shard}\"
      }
    }" \
    --consistent-read \
    --region "$AWS_REGION" \
    > "evidence/shard-${shard}.json"

done
```

### Step 2 — Combine Query Results

```bash
jq -s '
  [.[].Items[]] |
  {
    total_items: length,

    distinct_shards:
      ([.[].tenant_bucket.S] | unique | length),

    distinct_orders:
      ([.[].order_id.S] | unique | length)
  }
' evidence/shard-*.json \
  > evidence/sharded-query-summary.json
```

### Step 3 — Inspect Summary

```bash
jq . evidence/sharded-query-summary.json
```

Expected:

```json
{
  "total_items": 80,
  "distinct_shards": 10,
  "distinct_orders": 80
}
```

### Step 4 — Validate

```bash
jq -e '
  .total_items == 80 and
  .distinct_shards == 10 and
  .distinct_orders == 80
' evidence/sharded-query-summary.json
```

Expected:

```text
true
```

### Verification Conclusion

All 80 sharded orders are retrievable across the ten shard keys.

---

## 24. Understanding Write Sharding Trade-Offs

Write sharding helps distribute write traffic, but it introduces additional complexity.

### Before Sharding

```text
Query TENANT-1001
        |
        v
     80 Orders
```

### After Sharding

```text
Query TENANT-1001#00
Query TENANT-1001#01
Query TENANT-1001#02
Query TENANT-1001#03
Query TENANT-1001#04
Query TENANT-1001#05
Query TENANT-1001#06
Query TENANT-1001#07
Query TENANT-1001#08
Query TENANT-1001#09
           |
           v
     Merge Query Results
           |
           v
        80 Orders
```

### Advantages

- Spreads write activity across more key values.
- Can reduce concentrated key-range demand.
- Supports high-volume tenant workloads.
- Provides additional flexibility for scaling.

### Disadvantages

- Requires multiple Query operations.
- Increases read-path complexity.
- Requires result aggregation.
- May increase read costs.
- Complicates pagination.
- Requires careful shard assignment.
- Makes ordered queries more complex.

### Production Design Recommendation

Use deterministic shard assignment when possible.

For example, compute the shard number from a stable hash of the order identifier.

This helps the application locate a particular record later.

Random sharding may also work for some access patterns, but requires an appropriate lookup strategy.

### Important Migration Consideration

The original `TENANT-1001` records remain in the table.

The sharded workload creates additional records under new partition keys.

This lab does not migrate or delete the original 80 records.

A production migration must account for historical records and readers that may need to query both old and new key formats during the transition.

---

## 25. Production Troubleshooting Decision Tree

```text
DynamoDB Performance Incident
          |
          v
Inspect Application Errors
          |
          v
Check ThrottlingReasons
          |
     +----+----+
     |         |
     v         v
Provisioned   Key-Range
Capacity      Throughput
Exceeded      Exceeded
     |         |
     v         v
Investigate   Identify Hot Keys
Capacity            |
     |               v
     v         Analyze Access Pattern
Right-Size          |
Throughput          v
               Evaluate Sharding
                     |
                     v
               Test New Key Design
                     |
                     v
               Verify Record Access
                     |
                     v
               Monitor Throttling
                     |
                     v
               Measure Performance
```

### Production Investigation Checklist

| Check | Expected |
|---|---|
| AWS Account | Correct |
| AWS Region | us-east-1 |
| DynamoDB Table | ACTIVE |
| Billing Mode | PAY_PER_REQUEST |
| Partition-Key Schema | Verified |
| Sort-Key Schema | Verified |
| Application Traffic | Measured |
| Hot Logical Key | Identified |
| Throttling Reasons | Inspected if present |
| CloudWatch Metrics | Reviewed |
| Sharding Design | Evaluated |
| Records Per Shard | Verified |
| Query Fan-Out | Understood |
| Security Controls | Reviewed |

---

## 26. Cloud Security Engineering Considerations

### Noisy-Neighbor Risk

Multi-tenant applications may experience uneven traffic when one customer generates significantly more requests than others.

At sufficiently high traffic, concentrated demand can affect availability.

### Tenant Isolation

Partition keys do not automatically enforce tenant authorization.

Applications must validate that callers are authorized to access the requested tenant's records.

### IAM Least Privilege

Application roles should receive only the DynamoDB permissions required for their workloads.

### Request Rate Limiting

Use appropriate application-level rate limits to reduce abusive or unexpected request pressure.

### Monitoring

Investigate unusual write patterns, throttling, and cost changes.

### Credential Compromise

Unexpected high request volume could be caused by:

- Compromised application credentials.
- Application bugs.
- Automated abusive traffic.
- Misconfigured background jobs.

These are possibilities to investigate, not conclusions that can be drawn from traffic skew alone.

### Logging

Do not include sensitive tenant data unnecessarily in application logs.

### Cost Protection

AWS Budgets and cost anomaly monitoring can help identify unexpected spending.

### Security Principle

**Reliable multi-tenant cloud applications require authorization, workload isolation, appropriate partition-key design, and operational monitoring.**

---

## 27. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| DynamoDB On-Demand | Read and write requests |
| DynamoDB Storage | Stored records |
| CloudWatch | Applicable monitoring costs |
| Contributor Insights | Additional charges if enabled |
| AWS CLI | No separate CLI fee |
| IAM | No separate standard IAM role fee |

### Lab Cost Controls

- Use one temporary table.
- Limit the workload to 180 writes.
- Avoid unnecessary high-volume testing.
- Do not enable paid Contributor Insights rules.
- Use small test records.
- Delete the table after completion.

### Production Cost Considerations

Write sharding may improve throughput distribution but can introduce additional read operations.

The best design balances:

- Write throughput.
- Read performance.
- Operational complexity.
- Data model requirements.
- Cost.

---

## 28. Save Environment and Cleanup

### Step 1 — Save Resource Variables

```bash
cat > lab10-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab10-resources.env
```

### Step 2 — Restore Variables Later

```bash
source lab10-resources.env

source .venv/bin/activate
```

### Step 3 — Verify Table Identity

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    Name:TableName,
    Status:TableStatus,
    ARN:TableArn
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Step 4 — Verify Project Tag

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab10
```

### Step 5 — Delete Temporary Table

Only after confirming ownership:

```bash
aws dynamodb delete-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 6 — Wait for Deletion

```bash
aws dynamodb wait table-not-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 7 — Verify Deletion

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Step 8 — Deactivate Python Virtual Environment

```bash
deactivate
```

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| Test Orders | Deleted |
| IAM Roles | None created |
| Lambda Functions | None created |
| CloudWatch Alarms | None created |
| Contributor Insights | Not enabled |
| Local Python Script | Retained |
| Local Evidence Files | Retained |
| Virtual Environment | Retained locally |

---

## 29. Interview Questions and Answers

### Q1. What is a hot partition in DynamoDB?

A situation where disproportionately high request traffic targets a limited part of DynamoDB's partitioned data, potentially exceeding its available throughput.

### Q2. What is a hot logical partition key?

A partition-key value receiving unusually high traffic compared with other keys.

### Q3. Are logical partition keys and physical partitions the same?

No. DynamoDB manages underlying physical partitions and may split or redistribute data depending on access patterns and other conditions.

### Q4. What is the physical partition write throughput limit?

A DynamoDB physical partition supports up to approximately 1,000 write capacity units per second.

### Q5. What is TableWriteKeyRangeThroughputExceeded?

A throttling reason indicating that write traffic exceeded the throughput available to a table key range.

### Q6. What is TableWriteProvisionedThroughputExceeded?

A throttling reason indicating that table-level provisioned write throughput was insufficient.

### Q7. Can on-demand DynamoDB tables experience throttling?

Yes. On-demand capacity does not eliminate physical partition, configured throughput, or applicable quota limits.

### Q8. What is adaptive capacity?

A DynamoDB capability that helps accommodate uneven workloads by allocating capacity to frequently accessed partitions within applicable limits.

### Q9. What is write sharding?

A technique that spreads writes across multiple partition-key values instead of concentrating them on one key.

### Q10. How does write sharding help?

It distributes a logical workload over a wider set of key values, potentially reducing concentrated throughput demand.

### Q11. What are the disadvantages of write sharding?

It introduces query fan-out, additional read operations, result aggregation, and more complex shard management.

### Q12. How do you verify write sharding?

Inspect generated key distributions and query each shard to verify stored records.

### Q13. Does write sharding guarantee no throttling?

No. Performance depends on traffic rates, item size, capacity, physical partition behavior, and other service limits.

### Q14. What is CloudWatch Contributor Insights?

A monitoring capability that can identify frequently accessed or throttled keys and help investigate skewed DynamoDB workloads.

### Q15. Can a GSI experience hot partitions?

Yes. A GSI can experience concentrated access patterns and key-range throughput limitations.

### Q16. Why might increasing WCU not solve a hot partition?

If a physical key range is the bottleneck, increasing total table capacity may not remove the limiting condition.

### Q17. How can you prevent noisy-neighbor problems?

Use appropriate tenant isolation, rate limiting, workload controls, monitoring, and data-model design.

### Q18. How does partition-key design relate to Cloud Security Engineering?

Poorly distributed workloads can affect service availability. Cloud Security Engineers help protect systems against operational failures and potentially abusive traffic patterns.

### Q19. Why didn't this lab intentionally force physical partition throttling?

Because the purpose was to demonstrate the access pattern and remediation without generating unnecessarily expensive high-volume traffic.

### Q20. How would you explain this lab in a technical interview?

I created a DynamoDB table using a composite primary key with tenant_bucket as the partition key and order_id as the sort key.

I developed a Python Boto3 workload generator to simulate a multi-tenant order-processing application.

The initial test generated 100 writes, with 80% targeting one tenant partition-key value.

I analyzed the workload distribution using Python and jq and verified the stored records through DynamoDB Query operations.

I investigated how concentrated partition-key traffic can contribute to hot-key problems and reviewed DynamoDB throttling reasons, adaptive capacity, and CloudWatch metrics.

Next, I implemented ten-way write sharding to distribute the busiest tenant's 80 new orders across ten partition-key values.

Each shard received eight records.

I verified the new distribution and retrieved all 80 orders using queries across the ten shards.

Finally, I reviewed the read-path trade-offs, IAM security, noisy-neighbor considerations, cost management, and resource cleanup.

The lab demonstrated partition-key design, hot-key investigation, write sharding, and production-style DynamoDB performance troubleshooting.

---

## 30. Repository Structure and Lessons Learned

### Repository Structure

```text
aws-dynamodb-troubleshooting-labs/
│
├── README.md
├── .gitignore
│
├── 01-table-not-found/
│   └── README.md
│
├── 02-putitem-access-denied/
│   └── README.md
│
├── 03-validation-exception/
│   └── README.md
│
├── 04-wrong-partition-key/
│   └── README.md
│
├── 05-provisioned-throughput-exceeded/
│   └── README.md
│
├── 06-conditional-check-failed/
│   └── README.md
│
├── 07-gsi-query-not-returning-results/
│   └── README.md
│
├── 08-dynamodb-streams-not-triggering/
│   └── README.md
│
├── 09-point-in-time-recovery-investigation/
│   └── README.md
│
└── 10-dynamodb-hot-partition/
    ├── README.md
    ├── .gitignore
    ├── workload.py
    ├── lab10-resources.env
    │
    ├── .venv/
    │
    └── evidence/
        ├── table-description.json
        ├── hot-workload.json
        ├── hot-key-query.json
        ├── keyrange-throttling-metrics.json
        ├── sharded-workload.json
        ├── shard00-items.json
        ├── shard-00.json
        ├── shard-01.json
        ├── shard-02.json
        ├── shard-03.json
        ├── shard-04.json
        ├── shard-05.json
        ├── shard-06.json
        ├── shard-07.json
        ├── shard-08.json
        ├── shard-09.json
        └── sharded-query-summary.json
```

The structure represents the expected local lab files. Evidence files are generated when their corresponding commands are executed.

### Recommended Public GitHub Structure

```text
10-dynamodb-hot-partition/
├── README.md
├── .gitignore
└── workload.py
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Complete troubleshooting documentation |
| .gitignore | Excludes environment and evidence files |
| workload.py | Hot-key and sharded workload generator |
| lab10-resources.env | Local AWS variables |
| table-description.json | DynamoDB table metadata |
| hot-workload.json | Initial workload distribution |
| hot-key-query.json | Hot tenant verification |
| keyrange-throttling-metrics.json | CloudWatch key-range metric evidence |
| sharded-workload.json | Sharded workload distribution |
| shard00-items.json | Shard 00 verification |
| shard-00.json through shard-09.json | Per-shard query evidence |
| sharded-query-summary.json | Final combined recovery verification |

### Lessons Learned

This lab demonstrates how uneven partition-key access can become a performance concern for DynamoDB applications.

We created a DynamoDB table with a composite primary key.

We developed a Python Boto3 script to simulate a multi-tenant order-processing workload.

The initial workload generated 100 writes, with 80 writes targeting one tenant.

We investigated the distribution using Python, jq, and AWS CLI.

The analysis confirmed that 80% of the workload targeted one logical partition-key value.

We reviewed DynamoDB physical partition limits, adaptive capacity, throttling reasons, and CloudWatch monitoring.

Next, we implemented ten-way write sharding.

The new workload distributed 80 writes across ten partition-key values, with eight writes per shard.

We verified the sharded data using DynamoDB Query operations and combined the results to confirm that all 80 orders were retrievable.

We also reviewed the trade-offs of write sharding, including additional read operations, query fan-out, and data-model complexity.

Finally, we investigated cloud security considerations, cost management, and safe resource cleanup.

**Key Lesson:** Hot-partition troubleshooting requires understanding the difference between uneven logical key access and confirmed physical throughput limits. Engineers should use DynamoDB diagnostics, workload measurements, and access-pattern analysis before modifying the partition-key design.

### Skills Demonstrated

- Amazon DynamoDB.
- Composite primary keys.
- Partition-key design.
- Logical key distribution.
- Physical partition throughput.
- Hot-key investigation.
- DynamoDB adaptive capacity.
- Write throttling diagnostics.
- CloudWatch metrics.
- Python.
- Boto3.
- BatchWriteItem.
- Query.
- Write sharding.
- Shard distribution analysis.
- Query fan-out.
- Data-model optimization.
- AWS CLI v2.
- Linux Bash.
- jq.
- Root cause analysis.
- Multi-tenant architecture.
- IAM least privilege.
- Noisy-neighbor risk analysis.
- Cost management.
- Resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-010 |
| Scenario | DynamoDB Hot Partition |
| Table | ddb-lab10-orders |
| Region | us-east-1 |
| Partition Key | tenant_bucket |
| Sort Key | order_id |
| Billing Mode | PAY_PER_REQUEST |
| Original Workload | 100 writes |
| Busy Tenant | TENANT-1001 |
| Busy Tenant Writes | 80 |
| Hot-Key Concentration | 80% |
| Actual Key-Range Throttling | Not required for lab |
| Root Design Concern | Concentrated key access |
| Remediation | Write sharding |
| Shard Count | 10 |
| Sharded Workload | 80 writes |
| Writes Per Shard | 8 |
| Verified Sharded Orders | 80 |
| Read-Path Trade-offs | Reviewed |
| Cleanup | DynamoDB table deleted |
| Lab Status | Complete upon successful verification |

**Key Takeaway:** Production DynamoDB performance depends on effective partition-key design, workload distribution, adaptive capacity, and accurate diagnosis of throughput limitations. Write sharding is an important optimization technique, but it should be used when the workload and access patterns justify its added complexity.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [Best Practices for Partition Keys](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- [Using Write Sharding](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-sharding.html)
- [DynamoDB Adaptive Capacity](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/burst-adaptive-capacity.html)
- [DynamoDB Throttling Troubleshooting](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TroubleshootingThrottling.html)
- [Key-Range Throughput Throttling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/throttling-key-range-limit-exceeded-mitigation.html)
- [CloudWatch Contributor Insights for DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/contributorinsights_HowItWorks.html)
- [DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [AWS CLI — CreateTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/create-table.html)
- [AWS CLI — Query](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/query.html)
- [Boto3 DynamoDB Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)