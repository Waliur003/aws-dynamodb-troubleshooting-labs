# Lab 05 — Amazon DynamoDB Provisioned Throughput Exceeded

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve Amazon DynamoDB write throttling caused by insufficient provisioned throughput.

In production, DynamoDB applications frequently experience traffic spikes during product launches, promotional campaigns, batch-processing jobs, or sudden increases in customer activity.

When an application generates more read or write demand than the available throughput can support, DynamoDB may throttle requests.

For provisioned-capacity tables, one possible exception is:

```text
ProvisionedThroughputExceededException
```

In this lab, we create a DynamoDB table named `ddb-lab05-orders` in the `us-east-1` AWS Region.

The table uses:

- Partition key: `order_id`
- Partition-key type: String
- Billing mode: PROVISIONED
- Read capacity: 1 RCU
- Write capacity: 1 WCU

We first insert a small order to establish a healthy baseline.

Next, we create a Python Boto3 script that generates a bounded concurrent write workload.

The script sends up to 120 write requests using 12 workers, with approximately 8 KiB of payload per item.

The workload is designed to exceed the table's configured write capacity and reproduce DynamoDB throttling.

We investigate the resulting exceptions, throttling reasons, provisioned capacity settings, and CloudWatch metrics.

We then increase the table's provisioned write capacity from 1 WCU to 100 WCU.

To verify recovery safely, we execute a smaller, controlled workload and confirm successful PutItem operations.

Finally, we review exponential backoff, performance monitoring, security considerations, cost optimization, and safe cleanup.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Verify AWS CLI and Boto3
          |
          v
Configure AWS Environment
          |
          v
Create DynamoDB Table
          |
          v
Provision 1 RCU and 1 WCU
          |
          v
Wait for ACTIVE Status
          |
          v
Insert Baseline Order
          |
          v
Verify Healthy GetItem
          |
          v
Create Python Load Generator
          |
          v
Disable Automatic SDK Retries
          |
          v
Generate Concurrent Writes
          |
          v
DynamoDB Throttling
          |
          v
ProvisionedThroughputExceededException
          |
          v
Inspect Throttling Reasons
          |
          v
Check Provisioned Capacity
          |
          v
Investigate CloudWatch Metrics
          |
          v
Root Cause Analysis
          |
          v
Increase WCU from 1 to 100
          |
          v
Run Controlled Recovery Workload
          |
          v
Verify Successful PutItem
          |
          v
Verify GetItem
          |
          v
Review Retry Strategies
          |
          v
Security and Cost Review
          |
          v
Delete Temporary DynamoDB Table
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-005 |
| Lab Name | Provisioned Throughput Exceeded |
| Difficulty | Intermediate |
| Primary Service | Amazon DynamoDB |
| Supporting Services | CloudWatch, IAM, AWS STS |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Python 3, Boto3, Bash, jq |
| Table Name | `ddb-lab05-orders` |
| Partition Key | `order_id` |
| Partition-Key Type | String |
| Initial Billing Mode | PROVISIONED |
| Initial RCU | 1 |
| Initial WCU | 1 |
| Fault Injection | Concurrent PutItem workload |
| Initial Test Requests | 120 |
| Initial Workers | 12 |
| Initial Payload | Approximately 8 KiB |
| Expected Error | ProvisionedThroughputExceededException |
| Primary Throttling Reason | TableWriteProvisionedThroughputExceeded |
| Remediation | Increase WCU and reduce write pressure |
| Recovery WCU | 100 |
| Recovery Requests | 24 |
| Recovery Workers | 2 |
| Recovery Payload | Approximately 1 KiB |
| Recovery Verification | Successful PutItem and GetItem |
| Project Tag | DynamoDB-Troubleshooting-Lab05 |
| Cleanup | Delete temporary DynamoDB table |

### Learning Objectives

- Understand DynamoDB provisioned capacity.
- Understand Read Capacity Units.
- Understand Write Capacity Units.
- Understand DynamoDB write throttling.
- Understand ProvisionedThroughputExceededException.
- Create provisioned-capacity tables using AWS CLI.
- Generate bounded concurrent workloads.
- Use Boto3 for DynamoDB troubleshooting.
- Configure Boto3 retry behavior.
- Inspect DynamoDB throttling reasons.
- Identify table-level capacity bottlenecks.
- Investigate CloudWatch throttling metrics.
- Understand burst capacity.
- Increase provisioned write capacity.
- Reduce application request pressure.
- Understand exponential backoff and jitter.
- Verify successful recovery.
- Understand capacity-related security risks.
- Control AWS resource costs.
- Perform root cause analysis.
- Clean up temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

An e-commerce company operates an online shopping application.

Customer orders are stored in Amazon DynamoDB.

The application normally processes a small number of orders per second.

The DynamoDB table uses provisioned capacity with:

```text
Read Capacity: 1 RCU
Write Capacity: 1 WCU
```

During a flash sale, customer traffic increases rapidly.

Hundreds of customers begin placing orders simultaneously.

The application generates more write requests than the configured provisioned throughput can support.

DynamoDB starts throttling requests.

The application reports:

```text
ProvisionedThroughputExceededException
```

Some orders are not immediately written to the database.

The development team initially suspects a DynamoDB service outage.

The Cloud Engineering team investigates and discovers:

- The table exists.
- The table status is ACTIVE.
- AWS credentials and Region are correct.
- Individual low-volume writes work.
- The application generates a high write workload.
- The table has only 1 provisioned WCU.
- DynamoDB is throttling requests.
- CloudWatch provides supporting throughput and throttling metrics.

The engineer identifies insufficient provisioned write capacity relative to the workload as the primary cause.

The team increases capacity, reduces request pressure, and applies appropriate retry handling.

After remediation, controlled write requests succeed.

### Incident Symptoms

- PutItem requests are throttled.
- ProvisionedThroughputExceededException appears.
- Write success rates decline during traffic spikes.
- The DynamoDB table remains ACTIVE.
- Individual low-volume writes may still succeed.
- Provisioned write capacity is insufficient for the offered workload.
- CloudWatch may show write throttling.
- Increased capacity and controlled request rates improve reliability.

### Business Impact

DynamoDB write throttling can cause:

- Failed order submissions.
- Delayed transaction processing.
- Increased application latency.
- Failed API requests.
- Retry storms.
- Increased customer complaints.
- Data ingestion delays.
- Reduced service availability.
- Potential revenue loss during high-traffic periods.

### Incident Objective

Identify whether DynamoDB throttling originates from insufficient provisioned capacity, concentrated partition traffic, an index bottleneck, or another applicable throughput limit.

Apply the appropriate remediation while controlling cost and preserving application reliability.

---

## 3. AWS Architecture

### Healthy Architecture

```text
             Order Application
                     |
                     v
              Small Write Load
                     |
                     v
                AWS SDK
                     |
                     v
             Amazon DynamoDB
                     |
                     v
            Provisioned Capacity
                     |
                     v
            Available Throughput
                     |
                     v
                PutItem
                     |
                     v
              Item Stored
```

### Broken Architecture

```text
             Order Application
                     |
                     v
            High Write Traffic
                     |
                     v
           Concurrent PutItem
                     |
                     v
             Amazon DynamoDB
                     |
                     v
                1 WCU
                     |
                     v
         Insufficient Write Capacity
                     |
                     v
             Write Throttling
                     |
                     v
    ProvisionedThroughputExceededException
```

### Recovered Architecture

```text
             Order Application
                     |
                     v
          Controlled Write Requests
                     |
                     v
         SDK Retry and Backoff
                     |
                     v
             Amazon DynamoDB
                     |
                     v
               100 WCU
                     |
                     v
            Available Throughput
                     |
                     v
             Successful PutItem
                     |
                     v
             GetItem Verification
                     |
                     v
             CloudWatch Monitoring
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon DynamoDB | Stores order data |
| DynamoDB Table | Receives write requests |
| Provisioned WCU | Controls nominal write throughput |
| Provisioned RCU | Controls nominal read throughput |
| AWS CLI | Creates and updates table configuration |
| Python | Generates test workload |
| Boto3 | Sends concurrent DynamoDB requests |
| CloudWatch | Monitors throughput and throttling |
| AWS STS | Verifies caller identity |
| IAM | Authorizes database operations |
| Bash | Manages variables and commands |
| jq | Inspects JSON evidence |

---

## 4. Understanding Read and Write Capacity Units

DynamoDB supports provisioned throughput capacity.

The application or infrastructure team configures the amount of read and write capacity available to the table.

### Read Capacity Units

One RCU supports approximately:

- One strongly consistent read per second for an item up to 4 KB.
- Two eventually consistent reads per second for an item up to 4 KB.

Larger items consume additional capacity.

### Write Capacity Units

One WCU supports approximately one standard write per second for an item up to 1 KB.

Larger items consume more WCUs.

### Write Capacity Examples

| Item Size | Approximate WCU per Standard Write |
|---|---:|
| Up to 1 KiB | 1 |
| Up to 2 KiB | 2 |
| Up to 4 KiB | 4 |
| Up to 8 KiB | 8 |
| Up to 16 KiB | 16 |

### Example

The Lab 05 table initially has:

```text
WCU = 1
```

A standard write containing an 8-KiB item requires approximately:

```text
8 WCU
```

The write's consumed capacity exceeds the nominal capacity available in one second.

DynamoDB may use available burst capacity, so individual writes can still succeed temporarily.

### Important Production Concept

Throttling is not determined solely by total requests per second.

Other relevant factors include:

- Item size.
- Provisioned table throughput.
- Burst capacity.
- Partition-level throughput.
- Global Secondary Index capacity.
- Access-pattern distribution.
- Applicable service quotas.

---

## 5. Understanding ProvisionedThroughputExceededException

`ProvisionedThroughputExceededException` indicates that a request was throttled because provisioned throughput was insufficient for the request pattern.

### Example

```text
An error occurred
(ProvisionedThroughputExceededException)
when calling the PutItem operation
```

### Common Causes

- Provisioned write capacity is too low.
- Provisioned read capacity is too low.
- A workload experiences a sudden traffic spike.
- A large batch job increases demand.
- A GSI becomes a write bottleneck.
- A partition or key range receives concentrated traffic.
- Application retries increase request pressure.

### Throttling Flow

```text
Application Generates Writes
            |
            v
DynamoDB Receives Requests
            |
            v
Evaluate Available Throughput
            |
       +----+----+
       |         |
       v         v
   Capacity    Capacity
   Available   Insufficient
       |         |
       v         v
    Success   Throttling
                 |
                 v
   ProvisionedThroughputExceededException
```

### Important Distinction

A throttled request is not necessarily evidence that DynamoDB is unhealthy.

DynamoDB may be operating correctly by enforcing capacity limits.

---

## 6. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Python 3.
- Python virtual environment support.
- Boto3.
- jq.
- AWS account.
- IAM permissions to manage the dedicated DynamoDB table.

### Relevant IAM Actions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:ListTables
dynamodb:ListTagsOfResource
dynamodb:PutItem
dynamodb:GetItem
dynamodb:UpdateTable
dynamodb:DeleteTable

cloudwatch:GetMetricStatistics
```

These are relevant actions rather than a complete IAM policy.

### Safety Requirements

- Use a temporary DynamoDB table.
- Do not load test production resources.
- Keep the workload bounded.
- Avoid infinite request loops.
- Use fabricated data.
- Verify resource tags before changing capacity.
- Avoid unnecessary high provisioned capacity.
- Do not publish AWS credentials.
- Delete the table after testing.

### Load-Test Limits

The Python script limits:

```text
Maximum Requests: 240
Maximum Workers: 12
Maximum Payload: 8 KiB
```

The default fault-injection workload uses 120 attempted requests.

These limits help prevent uncontrolled traffic generation.

---

## 7. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 05-provisioned-throughput-exceeded

cd 05-provisioned-throughput-exceeded
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

### Step 4 — Create Python Virtual Environment

```bash
python3 -m venv .venv

source .venv/bin/activate
```

### Step 5 — Install Boto3

```bash
python -m pip install boto3
```

### Step 6 — Verify Boto3

```bash
python -c "import boto3; print('Boto3 ready')"
```

### Step 7 — Configure AWS Variables

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export TABLE_NAME="ddb-lab05-orders"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab05"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"
```

### Step 8 — Verify Variables

```bash
echo "$AWS_REGION"
echo "$TABLE_NAME"
echo "$TABLE_ARN"
```

### Step 9 — Prepare Evidence

```bash
mkdir -p evidence
```

### Step 10 — Configure `.gitignore`

```bash
cat > .gitignore <<'EOF'
.venv/
evidence/
lab05-resources.env

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

## 8. Verify AWS Account and Region

### Step 1 — Verify AWS Identity

```bash
aws sts get-caller-identity
```

### Step 2 — Verify AWS Region

```bash
echo "$AWS_REGION"
```

Expected:

```text
us-east-1
```

### Step 3 — List DynamoDB Tables

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

### Step 4 — Check Existing Lab Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected before creation:

```text
ResourceNotFoundException
```

If a table with that name already exists, do not overwrite or modify it without verifying ownership.

---

## 9. Create DynamoDB Table With Low Capacity

### Step 1 — Create Table

```bash
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=order_id,AttributeType=S \
  --key-schema \
    AttributeName=order_id,KeyType=HASH \
  --billing-mode PROVISIONED \
  --provisioned-throughput \
    ReadCapacityUnits=1,WriteCapacityUnits=1 \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Configuration Explanation

| Parameter | Purpose |
|---|---|
| Table Name | ddb-lab05-orders |
| Partition Key | order_id |
| Key Type | String |
| Billing Mode | PROVISIONED |
| RCU | 1 |
| WCU | 1 |
| Project Tag | Identifies disposable lab resource |

### Step 2 — Wait for ACTIVE State

```bash
aws dynamodb wait table-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Provisioned Capacity

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    TableName:TableName,
    Status:TableStatus,
    ReadCapacity:ProvisionedThroughput.ReadCapacityUnits,
    WriteCapacity:ProvisionedThroughput.WriteCapacityUnits
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "TableName": "ddb-lab05-orders",
  "Status": "ACTIVE",
  "ReadCapacity": 1,
  "WriteCapacity": 1
}
```

### Step 4 — Save Table Metadata

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/initial-table.json
```

---

## 10. Establish Healthy Baseline

### Step 1 — Insert One Small Order

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-5001"},
    "status": {"S": "Processing"},
    "amount": {"N": "150"}
  }' \
  --return-consumed-capacity TOTAL \
  --region "$AWS_REGION"
```

Expected: successful PutItem with consumed-capacity information.

### Step 2 — Retrieve the Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-5001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 3 — Save Healthy Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-5001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/healthy-get-item.json
```

### Step 4 — Validate

```bash
jq -e '.Item.order_id.S == "ORD-5001"' \
  evidence/healthy-get-item.json
```

Expected:

```text
true
```

### Baseline Findings

| Component | Expected Result |
|---|---|
| DynamoDB Table | ACTIVE |
| Billing Mode | PROVISIONED |
| RCU | 1 |
| WCU | 1 |
| Small PutItem | Successful |
| GetItem | Successful |

The initial baseline demonstrates that low-volume operations can succeed before the write spike.

---

## 11. Create Python Write Load Generator

### Step 1 — Create `write_load.py`

```python
import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--table", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--payload-kib", type=int, default=8)
    parser.add_argument("--prefix", default="SPIKE")
    parser.add_argument(
        "--output",
        default="evidence/load-summary.json"
    )

    args = parser.parse_args()

    if not (1 <= args.count <= 240):
        parser.error("count must be between 1 and 240")

    if not (1 <= args.workers <= 12):
        parser.error("workers must be between 1 and 12")

    if not (1 <= args.payload_kib <= 8):
        parser.error("payload-kib must be between 1 and 8")

    client = boto3.client(
        "dynamodb",
        region_name=args.region,
        config=Config(
            connect_timeout=5,
            read_timeout=15,
            retries={
                "mode": "standard",
                "total_max_attempts": 1
            }
        )
    )

    payload = "X" * (args.payload_kib * 1024)

    def write_item(index):
        order_id = f"{args.prefix}-{index:04d}"

        try:
            client.put_item(
                TableName=args.table,
                Item={
                    "order_id": {"S": order_id},
                    "payload": {"S": payload},
                    "status": {"S": "TEST"}
                }
            )

            return {"status": "success"}

        except ClientError as error:
            details = error.response
            code = details["Error"]["Code"]

            return {
                "status": "error",
                "code": code,
                "throttling_reasons": details.get(
                    "ThrottlingReasons", []
                )
            }

    with ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        results = list(
            executor.map(write_item, range(args.count))
        )

    counts = Counter(
        result.get("code", "Success")
        for result in results
    )

    throttling_reasons = []

    for result in results:
        throttling_reasons.extend(
            result.get("throttling_reasons", [])
        )

    summary = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "table": args.table,
        "attempted": args.count,
        "workers": args.workers,
        "payload_kib": args.payload_kib,
        "results": dict(counts),
        "throttling_reasons": throttling_reasons[:10]
    }

    print(json.dumps(summary, indent=2))

    with open(args.output, "w") as file:
        json.dump(summary, file, indent=2)


if __name__ == "__main__":
    main()
```

### Step 2 — Verify Python Syntax

```bash
python -m py_compile write_load.py
```

### Step 3 — Understand the Script

| Component | Purpose |
|---|---|
| argparse | Configures bounded workload parameters |
| ThreadPoolExecutor | Sends concurrent requests |
| Boto3 | Communicates with DynamoDB |
| Config | Controls SDK retry behavior |
| PutItem | Generates write demand |
| ClientError | Captures AWS API exceptions |
| Counter | Aggregates successful and failed requests |
| JSON summary | Saves incident evidence |

### Important Retry Configuration

```python
retries={
    "mode": "standard",
    "total_max_attempts": 1
}
```

This configures one total attempt, disabling normal SDK retries for the test.

In production, retries should normally be enabled with an appropriate strategy.

---

## 12. Fault Injection — Generate Concurrent Writes

### Step 1 — Execute Load Test

```bash
python write_load.py \
  --table "$TABLE_NAME" \
  --region "$AWS_REGION" \
  --count 120 \
  --workers 12 \
  --payload-kib 8 \
  --prefix SPIKE \
  --output evidence/throttling-summary.json
```

### Workload Configuration

| Parameter | Value |
|---|---:|
| Attempted Writes | 120 |
| Concurrent Workers | 12 |
| Payload per Item | Approximately 8 KiB |
| Provisioned WCU | 1 |
| Automatic SDK Retries | Disabled |

The combined item size is slightly larger than the payload alone because of the order ID, attribute names, and other attributes.

### Step 2 — Inspect Output

```bash
jq . evidence/throttling-summary.json
```

### Illustrative Result

```json
{
  "table": "ddb-lab05-orders",
  "attempted": 120,
  "workers": 12,
  "payload_kib": 8,
  "results": {
    "Success": 5,
    "ProvisionedThroughputExceededException": 115
  }
}
```

The numbers above are examples, not guaranteed measurements.

Actual results depend on DynamoDB capacity behavior, available burst capacity, request timing, and other conditions.

### Step 3 — Check Failure Distribution

```bash
jq '.results' \
  evidence/throttling-summary.json
```

### Step 4 — Optional Second Bounded Test

If the first test does not produce the desired exception, a second bounded test can be performed:

```bash
python write_load.py \
  --table "$TABLE_NAME" \
  --region "$AWS_REGION" \
  --count 240 \
  --workers 12 \
  --payload-kib 8 \
  --prefix SPIKE2 \
  --output evidence/throttling-summary-second-test.json
```

Do not run the test indefinitely.

### Expected Observation

The write workload can exceed provisioned throughput and produce throttling.

---

## 13. Investigate Throttling Reasons

DynamoDB may include structured throttling reasons in its exception responses.

These can help distinguish table capacity problems from key-range or index bottlenecks.

### Step 1 — Inspect Throttling Details

```bash
jq '.throttling_reasons' \
  evidence/throttling-summary.json
```

### Example

```json
[
  {
    "reason": "TableWriteProvisionedThroughputExceeded",
    "resource": "arn:aws:dynamodb:us-east-1:123456789012:table/ddb-lab05-orders"
  }
]
```

The example uses illustrative fields and values; inspect the exact response keys returned by the SDK.

### Common Throttling Reasons

| Reason | Meaning |
|---|---|
| TableWriteProvisionedThroughputExceeded | Table write capacity exceeded |
| TableReadProvisionedThroughputExceeded | Table read capacity exceeded |
| IndexWriteProvisionedThroughputExceeded | GSI write capacity exceeded |
| TableWriteKeyRangeThroughputExceeded | Write demand concentrated on a key range |
| TableWriteAccountLimitExceeded | Account-level write throughput limit |

### Lab Target

The intended investigation focuses on:

```text
TableWriteProvisionedThroughputExceeded
```

This reason indicates that provisioned table write throughput is the relevant bottleneck.

### Important Distinction

If the actual reason indicates key-range throughput exceeded, the investigation should consider partition-key distribution rather than assuming that increasing table-wide WCU alone will resolve the problem.

---

## 14. Investigate Provisioned Capacity

### Step 1 — Inspect Provisioned Throughput

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.ProvisionedThroughput' \
  --output json \
  --region "$AWS_REGION"
```

Expected capacity values:

```json
{
  "ReadCapacityUnits": 1,
  "WriteCapacityUnits": 1
}
```

The actual response may include additional throughput metadata.

### Step 2 — Verify Billing Mode

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.BillingModeSummary' \
  --output json \
  --region "$AWS_REGION"
```

For provisioned billing, BillingModeSummary may be absent or may identify PROVISIONED, depending on the table metadata returned.

The explicit provisioned-throughput configuration is the primary evidence for this lab.

### Step 3 — Inspect Table Status

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.TableStatus' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
ACTIVE
```

### Step 4 — Save Table Configuration

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/throttled-table-description.json
```

### Investigation Findings

| Component | Expected State |
|---|---|
| Table | Exists |
| Table Status | ACTIVE |
| Billing | Provisioned |
| RCU | 1 |
| WCU | 1 |
| Write Demand | High relative to WCU |
| Throttling | Expected |
| Likely Root Cause | Insufficient provisioned write throughput |

---

## 15. CloudWatch Investigation

Amazon CloudWatch provides operational metrics for DynamoDB.

These metrics help determine whether the workload experienced throttling and how much throughput it consumed.

### Relevant Metrics

| Metric | Purpose |
|---|---|
| ConsumedWriteCapacityUnits | Write capacity consumed |
| WriteThrottleEvents | Write-related throttling events |
| ThrottledRequests | Requests that experienced throttling |
| SuccessfulRequestLatency | Latency of successful requests |
| ConsumedReadCapacityUnits | Read capacity consumed |
| SystemErrors | Service-side errors |

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

### Step 4 — Inspect Throttled PutItem Requests

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=Operation,Value=PutItem \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 5 — Save CloudWatch Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name WriteThrottleEvents \
  --dimensions Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION" \
  > evidence/write-throttle-metrics.json
```

### Understanding the Results

A spike in WriteThrottleEvents supports the diagnosis that the workload experienced write throttling.

ConsumedWriteCapacityUnits provides information about capacity actually used.

ThrottledRequests shows request-level throttling behavior.

CloudWatch metrics can be delayed, so empty results immediately after the test do not necessarily mean that no throttling occurred.

### Production Investigation Principle

Use the exact API exception and throttling reason together with CloudWatch metrics and provisioned capacity settings.

Do not rely on one metric alone.

---

## 16. Root Cause Analysis

### Primary Root Cause

The DynamoDB table was configured with only 1 provisioned WCU.

The test workload attempted 120 concurrent writes containing approximately 8 KiB of payload per item.

The offered write demand substantially exceeded the table's nominal provisioned write throughput.

DynamoDB therefore throttled some requests.

### Root Cause Diagram

```text
Application Traffic Spike
          |
          v
Concurrent PutItem Requests
          |
          v
Large Write Payloads
          |
          v
Provisioned Table: 1 WCU
          |
          v
Demand Exceeds Available Throughput
          |
          v
DynamoDB Write Throttling
          |
          v
ProvisionedThroughputExceededException
```

### Five Whys

**Why 1 — Why did PutItem fail?**

DynamoDB throttled write requests.

**Why 2 — Why were requests throttled?**

The write demand exceeded available throughput.

**Why 3 — Why was throughput insufficient?**

The table was configured with only 1 WCU.

**Why 4 — Why wasn't the capacity problem detected earlier?**

The simulated application did not have sufficient workload testing and capacity planning.

**Why 5 — How can the problem be prevented?**

Use capacity planning, appropriate provisioned throughput, auto scaling where suitable, CloudWatch monitoring, controlled request rates, and retry strategies.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-DDB-005 |
| AWS Service | DynamoDB |
| Table | ddb-lab05-orders |
| Billing Mode | PROVISIONED |
| Initial WCU | 1 |
| Workload | Concurrent large PutItem requests |
| Error | ProvisionedThroughputExceededException |
| Primary Cause | Insufficient write capacity |
| Remediation | Increase capacity and control workload |

---

## 17. Remediation 01 — Increase Provisioned WCU

### Remediation Objective

Increase the table's write capacity from:

```text
1 WCU
```

to:

```text
100 WCU
```

This is a temporary capacity increase for the lab.

### Step 1 — Update Table Capacity

```bash
aws dynamodb update-table \
  --table-name "$TABLE_NAME" \
  --provisioned-throughput \
    ReadCapacityUnits=1,WriteCapacityUnits=100 \
  --region "$AWS_REGION"
```

### Step 2 — Wait for Table Activation

```bash
aws dynamodb wait table-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Updated Capacity

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    Status:TableStatus,
    RCU:ProvisionedThroughput.ReadCapacityUnits,
    WCU:ProvisionedThroughput.WriteCapacityUnits
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Status": "ACTIVE",
  "RCU": 1,
  "WCU": 100
}
```

### Step 4 — Save Remediation Evidence

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/increased-capacity.json
```

### Remediation Comparison

| Capacity | Before | After |
|---|---:|---:|
| RCU | 1 | 1 |
| WCU | 1 | 100 |
| Billing Mode | PROVISIONED | PROVISIONED |

### Important Note

A table-wide capacity increase is appropriate when insufficient table-level provisioned throughput is the confirmed bottleneck.

It may not resolve a hot partition or unrelated quota restriction.

---

## 18. Remediation 02 — Reduce Application Write Pressure

### Production Problem

Increasing WCU alone is not always sufficient.

A sudden workload spike may still cause throttling when offered demand exceeds available throughput.

Applications should also manage request concurrency and retry behavior.

### Step 1 — Execute Controlled Recovery Workload

```bash
python write_load.py \
  --table "$TABLE_NAME" \
  --region "$AWS_REGION" \
  --count 24 \
  --workers 2 \
  --payload-kib 1 \
  --prefix RECOVERY \
  --output evidence/recovery-summary.json
```

### Recovery Parameters

| Parameter | Value |
|---|---:|
| Requests | 24 |
| Workers | 2 |
| Payload | Approximately 1 KiB |
| Provisioned WCU | 100 |

### Step 2 — Inspect Results

```bash
jq . evidence/recovery-summary.json
```

### Expected Example

```json
{
  "attempted": 24,
  "workers": 2,
  "payload_kib": 1,
  "results": {
    "Success": 24
  }
}
```

The full summary includes additional metadata.

### Step 3 — Validate All Writes Succeeded

```bash
jq -e '
  .attempted == 24 and
  .results.Success == 24 and
  ((.results | keys) == ["Success"])
' evidence/recovery-summary.json
```

Expected:

```text
true
```

### Recovery Interpretation

The increased-capacity table successfully handles the smaller, controlled workload when no throttling errors are observed.

This is a recovery verification for the controlled workload.

It is not proof that the original larger write spike would succeed without throttling.

That would require a comparable workload test.

---

## 19. Verify PutItem and GetItem Recovery

### Step 1 — Retrieve a Recovery Item

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"RECOVERY-0000"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: the recovery item is returned.

### Step 2 — Save Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"RECOVERY-0000"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  --query 'Item.{OrderID:order_id.S,Status:status.S}' \
  --output json \
  > evidence/recovered-item.json
```

### Step 3 — Verify Order ID

```bash
jq -e '.OrderID == "RECOVERY-0000"' \
  evidence/recovered-item.json
```

Expected:

```text
true
```

### Step 4 — Verify Table Capacity

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    Status:TableStatus,
    WCU:ProvisionedThroughput.WriteCapacityUnits
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Recovery Comparison

| Component | Broken State | Recovered State |
|---|---|---|
| WCU | 1 | 100 |
| Test Requests | 120 | 24 |
| Workers | 12 | 2 |
| Payload | Approximately 8 KiB | Approximately 1 KiB |
| Throttling | Expected | Normally none |
| PutItem | Some failures | Expected success |
| GetItem | Successful items only | Recovery item verified |

---

## 20. Production Retry Strategy — Exponential Backoff

DynamoDB throttling may be temporary.

Production applications should generally retry eligible requests using exponential backoff with jitter.

### Example Boto3 Configuration

```python
import boto3
from botocore.config import Config

client = boto3.client(
    "dynamodb",
    region_name="us-east-1",
    config=Config(
        retries={
            "mode": "standard",
            "total_max_attempts": 5
        }
    )
)
```

### Retry Explanation

| Setting | Meaning |
|---|---|
| standard | Standard SDK retry mode |
| total_max_attempts | Total number of attempts, including initial request |
| 5 | Initial attempt plus up to four retries |

### Why Backoff Matters

Without appropriate backoff:

```text
Application Request
        |
        v
DynamoDB Throttles
        |
        v
Immediate Retry
        |
        v
More Throttling
        |
        v
Retry Storm
```

With controlled retry behavior:

```text
Application Request
        |
        v
DynamoDB Throttles
        |
        v
Wait With Backoff and Jitter
        |
        v
Retry Request
        |
        v
Successful Operation
```

### Important Production Considerations

- Keep retries bounded.
- Use exponential backoff with jitter.
- Monitor retry counts.
- Control request concurrency.
- Avoid retry storms.
- Design writes for safe retry behavior.
- Use conditional writes where duplicate or overwrite risks exist.
- Do not rely on retries to compensate indefinitely for insufficient capacity.

---

## 21. Additional Production Troubleshooting Scenarios

### Scenario 1 — Table Write Capacity Exceeded

**Symptom:** Write requests are throttled.

**Investigation:** Inspect WCU and ConsumedWriteCapacityUnits.

**Remediation:** Increase capacity or control workload demand.

### Scenario 2 — Table Read Capacity Exceeded

**Symptom:** Read requests are throttled.

**Investigation:** Inspect RCU consumption and read throttling metrics.

**Remediation:** Adjust read capacity or application access patterns.

### Scenario 3 — GSI Write Throttling

**Symptom:** Table writes fail because a Global Secondary Index is a bottleneck.

**Investigation:** Inspect GSI throughput and throttling reasons.

**Remediation:** Adjust index capacity or improve write distribution.

### Scenario 4 — Hot Partition

**Symptom:** Concentrated partition-key traffic causes throttling.

**Investigation:** Inspect key-range throttling reasons and access patterns.

**Remediation:** Improve partition-key design or distribute workload.

### Scenario 5 — Large Item Writes

**Symptom:** Write operations consume more capacity than expected.

**Investigation:** Inspect item size and consumed WCU.

**Remediation:** Reduce item size where practical.

### Scenario 6 — Account-Level Throughput Limits

**Symptom:** Requests are throttled despite otherwise appropriate table configuration.

**Investigation:** Inspect throttling reason and relevant service quotas.

**Remediation:** Review and request applicable quota adjustments if justified.

### Scenario 7 — Application Retry Storm

**Symptom:** Throttling causes increasing retry traffic.

**Investigation:** Inspect application retry configuration and concurrency.

**Remediation:** Use bounded retries, backoff, jitter, and workload smoothing.

---

## 22. Cloud Security Engineering Considerations

DynamoDB throttling is primarily an availability and performance issue, but it can also have security implications.

### Excessive Request Activity

An application bug, compromised credential, or abusive traffic pattern could generate unusually high DynamoDB request volumes.

### IAM Least Privilege

Applications should receive only the DynamoDB permissions required for their workloads.

Do not grant unrestricted DynamoDB permissions while troubleshooting throughput.

### Monitor Unexpected Usage

Investigate unusual changes in:

- Request volume.
- Consumed capacity.
- Throttling events.
- AWS costs.
- Application errors.

### Protect Production Availability

Use appropriately designed rate limits, monitoring, alarms, and workload controls.

### CloudTrail

Use CloudTrail to investigate relevant configuration changes and supported data events when configured.

### Cost Protection

Configure AWS Budgets and anomaly detection where appropriate.

### Security Principle

**Excessive database request traffic can affect both availability and cost. Production systems should combine least-privilege permissions, workload controls, monitoring, and capacity planning.**

---

## 23. Capacity Planning and DynamoDB Auto Scaling

Provisioned capacity should reflect expected application demand.

### Manual Provisioning

Engineers configure RCU and WCU directly.

Advantages:

- Explicit capacity control.
- Predictable nominal provisioned throughput.
- Suitable for stable workloads.

Disadvantages:

- Requires capacity planning.
- Sudden spikes may cause throttling.
- Overprovisioning can increase costs.

### DynamoDB Auto Scaling

DynamoDB auto scaling can adjust provisioned capacity within configured minimum and maximum limits.

It is useful for workloads with changing demand, but scaling is not instantaneous.

Sudden bursts may still experience throttling before capacity adjusts.

### On-Demand Capacity

On-demand mode removes the need to configure provisioned RCU and WCU.

It can be useful for unpredictable workloads, but it still has applicable throughput limits and cost considerations.

### Comparison

| Feature | Provisioned | On-Demand |
|---|---|---|
| Configure RCU/WCU | Yes | No |
| Auto scaling available | Yes | Not applicable in the same form |
| Capacity planning | Important | Less manual provisioning |
| Throttling possible | Yes | Yes |
| Billing | Provisioned capacity | Usage-based requests |

### Production Recommendation

Choose the capacity mode based on workload patterns, operational requirements, cost, and service limits.

---

## 24. Cost Management

### Potential Charges

| AWS Service | Cost Consideration |
|---|---|
| DynamoDB Provisioned Capacity | Configured RCU and WCU |
| DynamoDB Storage | Stored items |
| CloudWatch | Applicable monitoring charges |
| CloudTrail | Applicable configured logging |
| IAM | No separate standard IAM role fee |
| AWS CLI | No separate CLI fee |

### Lab Cost Controls

- Use one temporary table.
- Keep the initial capacity at 1 RCU and 1 WCU.
- Use bounded test requests.
- Limit Python concurrency.
- Increase WCU only for the recovery exercise.
- Avoid repeated high-volume tests.
- Delete the table after verification.

### Important Warning

The remediation temporarily increases provisioned write capacity to 100 WCU.

Provisioned capacity may incur charges while configured.

Do not leave this configuration running unnecessarily.

### Production Cost Considerations

Overprovisioned tables can increase costs.

Underprovisioned tables can cause throttling and application failures.

The goal is to balance reliability, performance, and cost.

---

## 25. Save Lab Environment Configuration

### Step 1 — Create `lab05-resources.env`

```bash
cat > lab05-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab05-resources.env
```

### Step 2 — Restore Variables Later

```bash
source lab05-resources.env
```

### Step 3 — Activate Python Environment

```bash
source .venv/bin/activate
```

### Step 4 — Verify Resources

```bash
echo "$TABLE_NAME"
echo "$TABLE_ARN"
echo "$AWS_REGION"
```

### Step 5 — Verify Project Tag

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab05
```

---

## 26. Final Recovery Verification

### Step 1 — Verify DynamoDB Table Status

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.TableStatus' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
ACTIVE
```

### Step 2 — Verify WCU

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.ProvisionedThroughput.WriteCapacityUnits' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
100
```

### Step 3 — Inspect Recovery Summary

```bash
jq . evidence/recovery-summary.json
```

### Step 4 — Verify Successful Writes

```bash
jq -e '
  .attempted == 24 and
  .results.Success == 24 and
  ((.results | keys) == ["Success"])
' evidence/recovery-summary.json
```

Expected:

```text
true
```

### Step 5 — Verify Recovery Item

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"RECOVERY-0000"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Final Verification Table

| Test | Expected Result |
|---|---|
| Table status | ACTIVE |
| Initial WCU | 1 |
| Fault workload | Throttling observed |
| Throttling reason | Table-level provisioned write bottleneck |
| Recovery WCU | 100 |
| Recovery workload | Successful |
| Recovery GetItem | Item returned |
| IAM changes | None |
| Data integrity | Successful writes preserved |

The exact result must be validated from the actual lab output.

---

## 27. AWS Resource Cleanup

**Warning:** Delete only the disposable DynamoDB table created for Lab 05.

### Step 1 — Verify Table Identity

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

### Step 2 — Verify Resource Tags

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab05
```

### Step 3 — Delete DynamoDB Table

```bash
aws dynamodb delete-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 4 — Wait for Deletion

```bash
aws dynamodb wait table-not-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Deletion

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

The error is expected because the lab table was intentionally deleted.

### Step 6 — Deactivate Virtual Environment

```bash
deactivate
```

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| Provisioned WCU | No longer configured |
| Test Records | Deleted with table |
| Python Virtual Environment | Retained locally |
| Python Script | Retained |
| Evidence Files | Retained locally |
| IAM Roles | None created |
| Lambda | None created |
| EC2 | None created |
| NAT Gateway | None created |

---

## 28. Interview Questions and Answers

### Q1. What is ProvisionedThroughputExceededException?

It is a DynamoDB exception indicating that a request was throttled because provisioned throughput was insufficient for the request.

### Q2. What is an RCU?

A Read Capacity Unit represents provisioned read throughput.

One RCU supports one strongly consistent read per second for an item up to 4 KB, or two eventually consistent reads per second for that size.

### Q3. What is a WCU?

A Write Capacity Unit represents provisioned write throughput.

One WCU supports one standard write per second for an item up to 1 KB.

### Q4. Why can a large item consume more WCU?

Write capacity consumption increases with item size, rounded to the applicable capacity unit.

### Q5. What causes DynamoDB write throttling?

Write demand can exceed available provisioned capacity, key-range throughput, index capacity, or other applicable limits.

### Q6. Why can DynamoDB sometimes process requests above provisioned capacity?

DynamoDB can use available burst capacity under certain conditions.

### Q7. Which CloudWatch metrics help investigate write throttling?

ConsumedWriteCapacityUnits, WriteThrottleEvents, and ThrottledRequests are useful metrics.

### Q8. What is TableWriteProvisionedThroughputExceeded?

A throttling reason indicating that provisioned table write capacity is insufficient.

### Q9. What is TableWriteKeyRangeThroughputExceeded?

A throttling reason indicating that write demand has exceeded the throughput available to a key range.

### Q10. What is a hot partition?

A partition or key range receiving disproportionately high traffic.

### Q11. Does increasing table WCU always solve throttling?

No. The bottleneck may involve a hot partition, GSI, account quota, or another limit.

### Q12. What is exponential backoff?

A retry strategy that increases the waiting period between retries.

### Q13. Why is jitter useful?

Jitter randomizes retry timing, reducing the chance that many clients retry simultaneously.

### Q14. What is DynamoDB auto scaling?

A feature that adjusts provisioned capacity within configured limits based on utilization.

### Q15. Can DynamoDB auto scaling prevent every sudden traffic spike?

No. Scaling takes time, and very sudden demand changes can still cause throttling.

### Q16. What is the difference between provisioned and on-demand capacity?

Provisioned mode uses explicitly configured capacity. On-demand mode charges primarily based on requests without requiring manual RCU/WCU provisioning.

### Q17. Why did this lab disable Boto3 automatic retries?

To make throttling exceptions easier to observe during controlled fault injection.

### Q18. Why shouldn't production applications disable retries?

Appropriate retries help recover from transient throttling and other retryable failures.

### Q19. How does throttling relate to Cloud Security Engineering?

Unexpected request spikes can affect availability and cost, potentially resulting from application defects, abusive traffic, or compromised credentials.

### Q20. How would you explain this lab in a technical interview?

I created a DynamoDB table in `us-east-1` using provisioned capacity with 1 RCU and 1 WCU.

I inserted a small item and verified that normal PutItem and GetItem operations worked.

Next, I created a Python Boto3 script to generate a bounded concurrent write workload.

The script disabled automatic retries to expose throttling exceptions directly.

The workload attempted 120 writes using 12 workers, with approximately 8 KiB of payload per request.

I investigated the resulting ProvisionedThroughputExceededException, the table's provisioned capacity, and DynamoDB throttling reasons.

I also used CloudWatch to inspect consumed write capacity and write throttling metrics.

The investigation identified insufficient provisioned write capacity relative to workload demand.

I increased the table's capacity from 1 WCU to 100 WCU and reduced request pressure.

I then ran a controlled recovery workload and verified successful writes using GetItem.

Finally, I reviewed exponential backoff, capacity planning, IAM least privilege, cost management, and resource cleanup.

---

## 29. Repository Structure

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
│   ├── README.md
│   ├── .gitignore
│   ├── write_load.py
│   ├── lab05-resources.env
│   │
│   ├── .venv/
│   │
│   └── evidence/
│       ├── initial-table.json
│       ├── healthy-get-item.json
│       ├── throttling-summary.json
│       ├── throttling-summary-second-test.json
│       ├── throttled-table-description.json
│       ├── write-throttle-metrics.json
│       ├── increased-capacity.json
│       ├── recovery-summary.json
│       └── recovered-item.json
│
├── 06-conditional-check-failed/
├── 07-gsi-query-not-returning-results/
├── 08-dynamodb-streams-not-triggering/
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

Evidence files are generated by their corresponding commands. The second throttling summary exists only if the optional second test is performed.

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Complete production troubleshooting documentation |
| .gitignore | Excludes local configuration and generated files |
| write_load.py | Bounded concurrent DynamoDB write generator |
| lab05-resources.env | Local AWS resource variables |
| initial-table.json | Initial table configuration |
| healthy-get-item.json | Healthy baseline evidence |
| throttling-summary.json | Fault-injection results |
| throttling-summary-second-test.json | Optional second load-test results |
| throttled-table-description.json | Capacity investigation evidence |
| write-throttle-metrics.json | CloudWatch throttling evidence |
| increased-capacity.json | Remediation configuration |
| recovery-summary.json | Recovery workload results |
| recovered-item.json | Final recovery verification |

### Recommended Public GitHub Structure

```text
05-provisioned-throughput-exceeded/
├── README.md
├── .gitignore
└── write_load.py
```

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 05
05-provisioned-throughput-exceeded/.venv/
05-provisioned-throughput-exceeded/evidence/
05-provisioned-throughput-exceeded/lab05-resources.env

# Python
__pycache__/
*.pyc
.venv/

# Local AWS configuration
.env
.env.*
*-resources.env

# Credentials
*.pem
*.key

# Logs
*.log
```

Do not commit credentials, real customer data, or unreviewed account-specific troubleshooting evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how Amazon DynamoDB can throttle write requests when application demand exceeds available provisioned throughput.

We created a DynamoDB table with 1 RCU and 1 WCU.

We inserted a small order and verified successful PutItem and GetItem operations.

Next, we built a Python Boto3 script that generated concurrent write requests.

The workload intentionally placed high write demand on the low-capacity DynamoDB table.

We used the resulting exception details and throttling reasons to investigate the cause.

We inspected provisioned capacity using DescribeTable and reviewed CloudWatch throughput and throttling metrics.

The investigation demonstrated that the table's configured write capacity was insufficient for the simulated workload.

We increased provisioned write capacity from 1 WCU to 100 WCU.

We also reduced the size and concurrency of the recovery workload.

After remediation, we verified that controlled write operations succeeded and that the inserted data could be retrieved.

Finally, we reviewed exponential backoff, auto scaling, hot partitions, IAM least privilege, cost management, and resource cleanup.

**Key Lesson:** DynamoDB throughput troubleshooting requires understanding capacity consumption, workload demand, throttling reasons, CloudWatch metrics, and retry behavior. Increasing WCU can resolve a confirmed table-level capacity bottleneck, but other throttling causes require different remediations.

### Skills Demonstrated

- Amazon DynamoDB.
- Provisioned capacity.
- RCU and WCU calculations.
- PutItem and GetItem.
- DynamoDB throttling.
- ProvisionedThroughputExceededException.
- Throttling reason analysis.
- Table capacity inspection.
- UpdateTable.
- CloudWatch metrics.
- Python.
- Boto3.
- Concurrent workload generation.
- SDK retry configuration.
- Exponential backoff.
- Capacity planning.
- Root cause analysis.
- Production incident investigation.
- Performance remediation.
- Cloud Security Engineering.
- AWS cost management.
- Resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-005 |
| Scenario | Provisioned Throughput Exceeded |
| Table | ddb-lab05-orders |
| Region | us-east-1 |
| Billing Mode | PROVISIONED |
| Initial RCU | 1 |
| Initial WCU | 1 |
| Healthy Baseline | Successful |
| Fault Injection | Concurrent PutItem workload |
| Fault Requests | 120 |
| Concurrent Workers | 12 |
| Fault Payload | Approximately 8 KiB |
| Expected Exception | ProvisionedThroughputExceededException |
| Investigation | Capacity, exceptions, CloudWatch |
| Root Cause | Insufficient provisioned write capacity |
| Recovery WCU | 100 |
| Recovery Workload | 24 controlled writes |
| Recovery Verification | Successful PutItem and GetItem |
| Cleanup | Table deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Production DynamoDB troubleshooting requires distinguishing table-level provisioned-capacity exhaustion from partition-level throttling, index bottlenecks, and service quotas. Engineers should combine capacity planning, appropriate retries, workload controls, monitoring, and cost awareness to maintain database reliability.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [Provisioned Throughput in DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/provisioned-capacity-mode.html)
- [DynamoDB Read and Write Operations](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/read-write-operations.html)
- [DynamoDB Throttling Troubleshooting](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TroubleshootingThrottling.html)
- [DynamoDB Throttling Reasons](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/throttling-diagnosing-workflow.html)
- [DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [AWS CLI — CreateTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/create-table.html)
- [AWS CLI — DescribeTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/describe-table.html)
- [AWS CLI — UpdateTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/update-table.html)
- [AWS CLI — PutItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/put-item.html)
- [Boto3 DynamoDB Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)
- [Boto3 Retry Configuration](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html)
- [DynamoDB Auto Scaling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)