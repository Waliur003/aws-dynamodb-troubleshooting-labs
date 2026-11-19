# Lab 07 — Amazon DynamoDB GSI Query Not Returning Results

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve Amazon DynamoDB Global Secondary Index (GSI) queries that return fewer records than expected.

In production, applications use DynamoDB Global Secondary Indexes to retrieve data using attributes other than the base table's primary key.

For example, an order-management application may store orders using `order_id` as the primary key but need to retrieve all orders belonging to a specific customer.

A Global Secondary Index allows the application to query orders using `customer_id` instead of scanning the entire table.

However, GSI queries can return unexpected results when:

- The application uses an incorrect index partition-key value.
- Items are missing required GSI key attributes.
- Recent changes have not yet propagated to the GSI.
- The application queries the wrong index.
- The GSI is not yet ACTIVE.
- The application expects strongly consistent reads from an eventually consistent index.

In this lab, we create a DynamoDB table named `ddb-lab07-orders` in the `us-east-1` AWS Region.

The base table uses `order_id` as its partition key.

We create a Global Secondary Index named `CustomerOrdersIndex` with:

- Partition key: `customer_id`
- Sort key: `created_at`
- Projection type: `ALL`

We insert sample customer orders, intentionally omit an indexed attribute from one item, and investigate why the item appears in the base table but not in the GSI.

We also reproduce an incorrect customer-ID query and investigate GSI eventual consistency.

Finally, we correct the missing attributes, verify index synchronization, review CloudWatch monitoring and security considerations, and delete the temporary AWS resources.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Verify AWS CLI and Identity
          |
          v
Configure Lab Environment
          |
          v
Create DynamoDB Table
          |
          v
Create CustomerOrdersIndex
          |
          v
Wait for ACTIVE Status
          |
          v
Insert Three Orders
          |
          v
Verify Base Table Records
          |
          v
Query Global Secondary Index
          |
          v
Fault 01 — Wrong Customer ID
          |
          v
Query Returns Zero Items
          |
          v
Correct GSI Partition Key
          |
          v
Fault 02 — Missing GSI Sort Key
          |
          v
Base Table Contains Order
          |
          v
GSI Does Not Contain Order
          |
          v
Inspect Index Key Schema
          |
          v
Populate Missing created_at
          |
          v
Wait for Index Synchronization
          |
          v
Verify Two Customer Orders
          |
          v
Fault 03 — Eventual Consistency
          |
          v
Insert New Order
          |
          v
Immediately Query GSI
          |
          v
Inspect Propagation Behavior
          |
          v
Verify Three Customer Orders
          |
          v
CloudWatch and Root Cause Analysis
          |
          v
Security and Cost Review
          |
          v
Delete Temporary Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-007 |
| Lab Name | GSI Query Not Returning Results |
| Difficulty | Intermediate |
| Primary Service | Amazon DynamoDB |
| Supporting Services | AWS IAM, STS, CloudWatch |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, jq |
| Table Name | `ddb-lab07-orders` |
| Base Table Partition Key | `order_id` |
| Base Table Key Type | String |
| Global Secondary Index | `CustomerOrdersIndex` |
| GSI Partition Key | `customer_id` |
| GSI Sort Key | `created_at` |
| GSI Key Types | String |
| GSI Projection | ALL |
| Billing Mode | PAY_PER_REQUEST |
| Initial Items | 3 |
| Final Items | 4 |
| Fault 01 | Wrong GSI partition-key value |
| Fault 02 | Missing GSI sort-key attribute |
| Fault 03 | Eventual consistency |
| Additional Validation | Strongly consistent GSI read rejected |
| Primary Operations | Query, GetItem |
| Supporting Operations | PutItem, BatchWriteItem, UpdateItem |
| Root Cause | Incorrect index key or incomplete indexed item |
| Remediation | Correct keys and validate index propagation |
| Recovery | Successful GSI Query |
| Project Tag | DynamoDB-Troubleshooting-Lab07 |
| Cleanup | Delete temporary DynamoDB table and GSI |

### Learning Objectives

- Understand DynamoDB Global Secondary Indexes.
- Understand GSI partition keys and sort keys.
- Understand alternate data access patterns.
- Create a GSI using AWS CLI.
- Query data through a GSI.
- Understand sparse indexes.
- Investigate missing GSI attributes.
- Understand eventual consistency.
- Distinguish base table reads from GSI reads.
- Inspect GSI status.
- Understand GSI projection types.
- Troubleshoot incorrect index-key values.
- Update missing index-key attributes.
- Verify index propagation.
- Investigate CloudWatch GSI metrics.
- Apply IAM least privilege.
- Understand GSI security implications.
- Perform production root cause analysis.
- Safely clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

An e-commerce company stores customer orders in Amazon DynamoDB.

The application needs two common database access patterns.

**Access Pattern 1: Retrieve an order using its ID.**

The application retrieves a specific order using:

```text
order_id = ORD-7001
```

**Access Pattern 2: Retrieve all orders belonging to a customer.**

The application retrieves orders using:

```text
customer_id = CUST-1001
```

To support the second access pattern, engineers create a Global Secondary Index called:

```text
CustomerOrdersIndex
```

The GSI uses:

```text
Partition Key: customer_id
Sort Key: created_at
```

The table contains three orders.

| order_id | customer_id | created_at | status |
|---|---|---|---|
| ORD-7001 | CUST-1001 | 2026-11-19T10:00:00Z | PENDING |
| ORD-7002 | CUST-1002 | 2026-11-19T10:05:00Z | SHIPPED |
| ORD-7003 | CUST-1001 | Missing | PROCESSING |

The application expects two orders for customer `CUST-1001`.

However, its GSI query returns only:

```text
ORD-7001
```

The development team suspects that ORD-7003 was deleted or never inserted.

The Cloud Engineer investigates the base table and discovers that ORD-7003 still exists.

Further investigation reveals that ORD-7003 does not contain the `created_at` attribute.

Because `created_at` is part of the GSI key schema, DynamoDB does not include that item in the index.

The engineer corrects the missing attribute and waits for index propagation.

After synchronization, the GSI returns both orders.

### Incident Symptoms

- GSI Query returns fewer records than expected.
- The missing record exists in the base table.
- The DynamoDB table remains ACTIVE.
- The GSI remains ACTIVE.
- A required GSI key attribute is absent.
- Incorrect index partition-key values return no matching items.
- Newly written records may briefly be absent from the index.
- Correcting attributes restores index visibility after propagation.

### Business Impact

GSI query problems can cause:

- Missing customer orders.
- Incomplete customer dashboards.
- Incorrect reporting.
- Failed application lookups.
- Delayed order processing.
- Confusing application behavior.
- Increased database troubleshooting.
- Inconsistent user experiences.

### Incident Objective

Determine why a record exists in a DynamoDB base table but does not appear in a Global Secondary Index query.

Restore the expected access pattern without rebuilding healthy database infrastructure.

---

## 3. AWS Architecture

### Healthy Architecture

```text
                  Order Application
                         |
                         v
                   Amazon DynamoDB
                         |
                         v
                  ddb-lab07-orders
                         |
            +------------+------------+
            |                         |
            v                         v
       Base Table             Global Secondary Index
            |                         |
            v                         v
    PK = order_id            CustomerOrdersIndex
                                      |
                             +--------+--------+
                             |                 |
                             v                 v
                     PK = customer_id   SK = created_at
                             |                 |
                             +--------+--------+
                                      |
                                      v
                               Query Customer
                                      |
                                      v
                               Matching Orders
```

### Broken Architecture — Sparse Index

```text
                  DynamoDB Base Table
                          |
                 +--------+--------+
                 |                 |
                 v                 v
              ORD-7001          ORD-7003
                 |                 |
                 v                 v
          customer_id exists  customer_id exists
          created_at exists   created_at missing
                 |                 |
                 v                 v
            GSI Eligible      GSI Ineligible
                 |                 |
                 v                 |
              Indexed              |
                 |                 |
                 +--------+--------+
                          |
                          v
                Query CustomerOrdersIndex
                          |
                          v
                 Only ORD-7001 Returned
```

### Recovered Architecture

```text
                  DynamoDB Base Table
                          |
                          v
                 Update ORD-7003
                          |
                          v
               Add Missing created_at
                          |
                          v
                GSI Key Requirements
                       Satisfied
                          |
                          v
                GSI Synchronization
                          |
                          v
                CustomerOrdersIndex
                          |
                          v
                Query CUST-1001
                          |
                          v
               ORD-7001 + ORD-7003
```

### AWS Components

| Component | Purpose |
|---|---|
| DynamoDB Base Table | Stores complete order records |
| Global Secondary Index | Supports alternate query patterns |
| Partition Key | Identifies partition access |
| Sort Key | Orders indexed records |
| BatchWriteItem | Creates initial test data |
| GetItem | Verifies base-table records |
| Query | Retrieves indexed customer orders |
| UpdateItem | Adds missing index attributes |
| DescribeTable | Inspects index configuration |
| AWS STS | Verifies identity |
| IAM | Controls database access |
| CloudWatch | Provides operational metrics |
| AWS CLI | Executes troubleshooting commands |
| jq | Validates JSON responses |

---

## 4. Understanding Global Secondary Indexes

A Global Secondary Index allows DynamoDB queries using a key schema different from the base table's primary key.

### Base Table

```text
Table: ddb-lab07-orders

Partition Key: order_id
```

Example lookup:

```text
order_id = ORD-7001
```

### Global Secondary Index

```text
Index: CustomerOrdersIndex

Partition Key: customer_id
Sort Key: created_at
```

Example query:

```text
customer_id = CUST-1001
```

### Key Comparison

| Property | Base Table | GSI |
|---|---|---|
| Name | ddb-lab07-orders | CustomerOrdersIndex |
| Partition Key | order_id | customer_id |
| Sort Key | None | created_at |
| Access Pattern | Find order by ID | Find customer's orders |
| Strong Consistency | Supported | Not supported |
| Data Source | Primary table data | Asynchronously maintained index |

### Why Use a GSI?

Without an appropriate secondary index, retrieving all orders for a customer may require inefficient table-wide access.

A GSI supports a targeted Query operation.

### Important Concept

A GSI stores a separate, asynchronously maintained representation of indexed table items.

It does not provide strongly consistent reads.

---

## 5. Understanding Sparse Indexes

A sparse GSI contains only items that satisfy its index-key requirements.

For this lab, the index requires:

```text
customer_id
created_at
```

An item must have both attributes with appropriate key types to be represented in the index.

### Example

Item ORD-7001:

```json
{
  "order_id": {"S": "ORD-7001"},
  "customer_id": {"S": "CUST-1001"},
  "created_at": {"S": "2026-11-19T10:00:00Z"}
}
```

This item qualifies for the GSI.

Item ORD-7003:

```json
{
  "order_id": {"S": "ORD-7003"},
  "customer_id": {"S": "CUST-1001"}
}
```

This item does not qualify because `created_at` is missing.

### Sparse Index Behavior

| Item | customer_id | created_at | GSI Representation |
|---|---|---|---|
| ORD-7001 | Present | Present | Yes |
| ORD-7002 | Present | Present | Yes |
| ORD-7003 | Present | Missing | No |

### Production Lesson

A record can exist in the base table without being represented in a GSI.

This is expected DynamoDB behavior, not necessarily an index failure.

---

## 6. Understanding GSI Eventual Consistency

DynamoDB synchronizes GSI data asynchronously.

When an application writes an item to the base table, the corresponding index update may not be visible immediately.

### Example

```text
PutItem Successful
        |
        v
Base Table Updated
        |
        v
GetItem Returns New Data
        |
        v
GSI Update Pending
        |
        v
Query May Return Older Results
        |
        v
GSI Synchronization
        |
        v
Query Returns Updated Data
```

### Important Requirements

- GSI reads are eventually consistent.
- Strongly consistent reads are not supported on GSIs.
- Index propagation time is not guaranteed.
- Applications requiring immediate read-after-write consistency may need a different access pattern.
- Repeated queries should use bounded retries.

### Common Mistake

Using:

```text
ConsistentRead = true
```

on a GSI query.

This results in a validation error because strongly consistent GSI reads are unsupported.

---

## 7. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- jq.
- AWS account.
- DynamoDB permissions.

### Relevant IAM Actions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:ListTables
dynamodb:ListTagsOfResource
dynamodb:BatchWriteItem
dynamodb:PutItem
dynamodb:GetItem
dynamodb:Query
dynamodb:Scan
dynamodb:UpdateItem
dynamodb:DeleteTable

cloudwatch:GetMetricStatistics
```

For IAM policies, consider both the table ARN and the appropriate index ARN when authorizing index queries.

### Safety Requirements

- Use a dedicated temporary table.
- Do not modify production GSIs.
- Use fabricated customer identifiers.
- Verify account and Region.
- Avoid large scans.
- Keep test data small.
- Do not publish credentials.
- Confirm resource ownership before cleanup.

### Resource Tag

```text
Project = DynamoDB-Troubleshooting-Lab07
```

---

## 8. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 07-gsi-query-not-returning-results

cd 07-gsi-query-not-returning-results
```

### Step 2 — Verify Tools

```bash
aws --version

jq --version

aws sts get-caller-identity
```

### Step 3 — Configure Variables

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export TABLE_NAME="ddb-lab07-orders"

export INDEX_NAME="CustomerOrdersIndex"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab07"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"

export INDEX_ARN="${TABLE_ARN}/index/${INDEX_NAME}"
```

### Step 4 — Verify Variables

```bash
echo "$AWS_REGION"
echo "$TABLE_NAME"
echo "$INDEX_NAME"
echo "$TABLE_ARN"
echo "$INDEX_ARN"
```

### Step 5 — Create Evidence Directory

```bash
mkdir -p evidence
```

### Step 6 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
evidence/
lab07-resources.env

*.log

__pycache__/
*.pyc
.venv/

.env
.env.*
*.pem
*.key
EOF
```

---

## 9. Verify AWS Account and Existing Resources

### Step 1 — Verify Caller

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

### Step 3 — List Tables

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

### Step 4 — Check Lab Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected before creation:

```text
ResourceNotFoundException
```

If the table exists, verify its ownership.

Do not overwrite unrelated resources.

---

## 10. Create DynamoDB Table With GSI

### Step 1 — Create Table and Index

```bash
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=order_id,AttributeType=S \
    AttributeName=customer_id,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
  --key-schema \
    AttributeName=order_id,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "CustomerOrdersIndex",
      "KeySchema": [
        {
          "AttributeName": "customer_id",
          "KeyType": "HASH"
        },
        {
          "AttributeName": "created_at",
          "KeyType": "RANGE"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      }
    }
  ]' \
  --billing-mode PAY_PER_REQUEST \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Configuration Explanation

| Parameter | Purpose |
|---|---|
| Table Name | ddb-lab07-orders |
| Table Partition Key | order_id |
| Index Name | CustomerOrdersIndex |
| GSI Partition Key | customer_id |
| GSI Sort Key | created_at |
| Projection | ALL |
| Billing Mode | PAY_PER_REQUEST |
| Project Tag | Lab identification |

### Step 2 — Wait for Table

```bash
aws dynamodb wait table-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Index

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.GlobalSecondaryIndexes[].{
    Name:IndexName,
    Status:IndexStatus,
    Keys:KeySchema,
    Projection:Projection.ProjectionType
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
Name = CustomerOrdersIndex
Status = ACTIVE
Projection = ALL
```

If the index remains in CREATING status, allow creation to complete before proceeding.

### Step 4 — Save Table Metadata

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/table-description.json
```

---

## 11. Insert Initial Test Orders

### Step 1 — Create `orders.json`

```bash
cat > orders.json <<'EOF'
{
  "ddb-lab07-orders": [
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-7001"},
          "customer_id": {"S": "CUST-1001"},
          "created_at": {"S": "2026-11-19T10:00:00Z"},
          "status": {"S": "PENDING"},
          "amount": {"N": "150"}
        }
      }
    },
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-7002"},
          "customer_id": {"S": "CUST-1002"},
          "created_at": {"S": "2026-11-19T10:05:00Z"},
          "status": {"S": "SHIPPED"},
          "amount": {"N": "200"}
        }
      }
    },
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-7003"},
          "customer_id": {"S": "CUST-1001"},
          "status": {"S": "PROCESSING"},
          "amount": {"N": "300"}
        }
      }
    }
  ]
}
EOF
```

### Step 2 — Validate JSON

```bash
jq . orders.json
```

### Step 3 — Insert Orders

```bash
aws dynamodb batch-write-item \
  --request-items file://orders.json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "UnprocessedItems": {}
}
```

If the response contains unprocessed requests, retry only those requests before continuing.

### Step 4 — Inspect Base Table

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: three orders.

### Step 5 — Save Evidence

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/base-table-items.json
```

### Step 6 — Validate

```bash
jq -e '
  ([.Items[].order_id.S] | sort) ==
  ["ORD-7001","ORD-7002","ORD-7003"]
' evidence/base-table-items.json
```

Expected:

```text
true
```

---

## 12. Establish Healthy GSI Baseline

### Step 1 — Query CustomerOrdersIndex

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION"
```

Expected after propagation:

```text
Count = 1
```

ORD-7001 should appear.

ORD-7003 should not appear because `created_at` is missing.

### Step 2 — Save Baseline

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION" \
  > evidence/healthy-gsi-query.json
```

### Step 3 — Validate

```bash
jq -e '
  .Count == 1 and
  .Items[0].order_id.S == "ORD-7001"
' evidence/healthy-gsi-query.json
```

Expected:

```text
true
```

Allow newly written indexed items to propagate before treating a temporarily empty result as a fault.

---

## 13. Fault Injection 01 — Wrong GSI Partition-Key Value

### Production Problem

The application requests:

```text
customer_id = CUST-9999
```

The actual customer identifier is:

```text
customer_id = CUST-1001
```

### Step 1 — Query Incorrect Customer

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-9999"}
  }' \
  --region "$AWS_REGION"
```

Expected relevant response:

```json
{
  "Items": [],
  "Count": 0,
  "ScannedCount": 0
}
```

### Step 2 — Save Evidence

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-9999"}
  }' \
  --region "$AWS_REGION" \
  > evidence/wrong-gsi-key.json
```

### Step 3 — Validate

```bash
jq -e '
  .Count == 0 and
  (.Items | length) == 0
' evidence/wrong-gsi-key.json
```

Expected:

```text
true
```

### Root Cause

The request uses a valid GSI key structure but an incorrect partition-key value.

DynamoDB successfully executes the query and returns no matching items.

This is not necessarily a validation or table-availability problem.

---

## 14. Remediation 01 — Correct GSI Partition Key

### Step 1 — Query Correct Customer

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION"
```

Expected after synchronization: ORD-7001.

### Step 2 — Save Recovery Evidence

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION" \
  > evidence/recovered-gsi-key.json
```

### Step 3 — Validate

```bash
jq -e '
  .Count == 1 and
  .Items[0].order_id.S == "ORD-7001"
' evidence/recovered-gsi-key.json
```

Expected:

```text
true
```

### Recovery Comparison

| Property | Broken | Recovered |
|---|---|---|
| customer_id | CUST-9999 | CUST-1001 |
| Query | Successful but empty | Matching record |
| Table | Healthy | Healthy |
| GSI | Healthy | Healthy |
| Application Configuration | Incorrect | Correct |

**Fault 01 resolved when the correct customer identifier retrieves ORD-7001.**

---

## 15. Fault Injection 02 — Missing GSI Sort Key

### Production Problem

The application expects two orders for CUST-1001.

However, the GSI returns only ORD-7001.

### Step 1 — Query GSI

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION"
```

Expected after propagation:

```text
Count = 1
```

### Step 2 — Retrieve ORD-7003 From Base Table

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-7003"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: ORD-7003 exists.

### Step 3 — Save Item Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-7003"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/missing-indexed-order.json
```

### Step 4 — Verify Missing Attribute

```bash
jq -e '
  .Item.order_id.S == "ORD-7003" and
  .Item.customer_id.S == "CUST-1001" and
  (.Item | has("created_at") | not)
' evidence/missing-indexed-order.json
```

Expected:

```text
true
```

### Step 5 — Inspect GSI Key Schema

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.GlobalSecondaryIndexes[].{
    Name:IndexName,
    Status:IndexStatus,
    Keys:KeySchema
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Root Cause

ORD-7003 exists in the base table but lacks the GSI sort key `created_at`.

DynamoDB does not represent the item in the sparse GSI.

The GSI itself is operating correctly.

---

## 16. Remediation 02 — Populate Missing GSI Attribute

### Remediation Objective

Add a valid `created_at` attribute to ORD-7003 so the item qualifies for the GSI.

The timestamp used here is fabricated lab data. In production, recover a trustworthy timestamp from the authoritative system.

### Step 1 — Update ORD-7003

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-7003"}}' \
  --update-expression \
    "SET created_at = :timestamp" \
  --condition-expression \
    "attribute_exists(order_id) AND attribute_not_exists(created_at)" \
  --expression-attribute-values '{
    ":timestamp": {"S": "2026-11-19T10:10:00Z"}
  }' \
  --return-values ALL_NEW \
  --region "$AWS_REGION"
```

### Step 2 — Verify Base Table Update

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-7003"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
created_at = 2026-11-19T10:10:00Z
```

### Step 3 — Query GSI Again

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION"
```

Expected after propagation:

```text
Count = 2
```

Orders:

```text
ORD-7001
ORD-7003
```

### Step 4 — Save Recovery Evidence

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION" \
  > evidence/sparse-index-recovered.json
```

### Step 5 — Validate

```bash
jq -e '
  .Count == 2 and
  ([.Items[].order_id.S] | sort) ==
  ["ORD-7001","ORD-7003"]
' evidence/sparse-index-recovered.json
```

Expected:

```text
true
```

If the index has not synchronized, wait and repeat the query.

**Fault 02 resolved when ORD-7003 appears in the GSI.**

---

## 17. Fault Investigation 03 — GSI Eventual Consistency

### Production Problem

A newly inserted order exists in the base table but may not immediately appear in its GSI.

This occurs because GSI propagation is asynchronous.

### Step 1 — Create ORD-7004

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-7004"},
    "customer_id": {"S": "CUST-1001"},
    "created_at": {"S": "2026-11-19T10:15:00Z"},
    "status": {"S": "PENDING"},
    "amount": {"N": "250"}
  }' \
  --condition-expression \
    "attribute_not_exists(order_id)" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Base Table

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-7004"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: ORD-7004 exists.

### Step 3 — Query GSI Immediately

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION"
```

Possible results:

```text
2 orders
```

or:

```text
3 orders
```

The timing is not deterministic.

### Step 4 — Inspect Propagation

The expected final index representation is:

```text
ORD-7001
ORD-7003
ORD-7004
```

Because index synchronization may complete quickly, an actual temporary missing-item result is not guaranteed during this experiment.

### Important Finding

A newly written record can be present in the base table while its GSI representation is still propagating.

This is normal eventual-consistency behavior.

---

## 18. Additional Fault — Unsupported Strongly Consistent GSI Read

### Production Problem

An engineer attempts to force strongly consistent reads on a GSI.

### Step 1 — Attempt Query With ConsistentRead

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
ValidationException
```

### Step 2 — Save Failure Evidence

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/gsi-strong-read-output.json \
  2> evidence/gsi-strong-read-error.log

echo "Exit code: $?"
```

### Step 3 — Inspect Error

```bash
cat evidence/gsi-strong-read-error.log
```

### Root Cause

DynamoDB GSIs support eventually consistent reads only.

### Remediation

Remove `--consistent-read` when querying a GSI.

If the application requires strongly consistent access to a specific item, use an appropriate base-table GetItem operation with the full primary key.

---

## 19. Verify GSI Propagation With Bounded Retries

### Step 1 — Execute Verification Loop

```bash
for attempt in {1..10}; do

  aws dynamodb query \
    --table-name "$TABLE_NAME" \
    --index-name "$INDEX_NAME" \
    --key-condition-expression \
      "customer_id = :customer" \
    --expression-attribute-values '{
      ":customer": {"S": "CUST-1001"}
    }' \
    --region "$AWS_REGION" \
    > evidence/gsi-propagation.json || break

  if jq -e '
    ([.Items[].order_id.S] | sort) ==
    ["ORD-7001","ORD-7003","ORD-7004"]
  ' evidence/gsi-propagation.json >/dev/null; then

    echo "GSI synchronization verified"
    break

  fi

  echo "Waiting for index propagation — attempt $attempt"

  sleep 2

done
```

### Step 2 — Verify Result

```bash
jq -e '
  .Count == 3 and
  ([.Items[].order_id.S] | sort) ==
  ["ORD-7001","ORD-7003","ORD-7004"]
' evidence/gsi-propagation.json
```

Expected after synchronization:

```text
true
```

### Important Production Lesson

Do not use infinite retries.

If propagation is not verified within a reasonable application-specific window, investigate the index status, throttling, request correctness, and application data model.

---

## 20. Production Investigation — Inspect GSI Health

### Step 1 — Inspect Index Status

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.GlobalSecondaryIndexes[].{
    Name:IndexName,
    Status:IndexStatus,
    Backfilling:Backfilling,
    Projection:Projection
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
CustomerOrdersIndex = ACTIVE
```

### Step 2 — Inspect Index Key Schema

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.GlobalSecondaryIndexes[].KeySchema' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
[
  [
    {
      "AttributeName": "customer_id",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "created_at",
      "KeyType": "RANGE"
    }
  ]
]
```

### Step 3 — Inspect Projection

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.GlobalSecondaryIndexes[].Projection' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
[
  {
    "ProjectionType": "ALL"
  }
]
```

### Step 4 — Inspect Base Table Keys

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --consistent-read \
  --projection-expression \
    "order_id, customer_id, created_at" \
  --region "$AWS_REGION"
```

This Scan is appropriate because the lab contains only four small items.

### Step 5 — Save Final Table Metadata

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/final-table-description.json
```

### Important Note

The GSI `ItemCount` reported by DescribeTable is not continuously updated.

Use actual Query results to verify the index records for this lab.

---

## 21. CloudWatch Investigation

Amazon DynamoDB provides CloudWatch metrics for Global Secondary Index capacity and performance.

### Relevant Metrics

| Metric | Purpose |
|---|---|
| ConsumedReadCapacityUnits | GSI read capacity consumption |
| ConsumedWriteCapacityUnits | GSI write capacity consumption |
| ReadThrottleEvents | Read throttling events |
| WriteThrottleEvents | Write throttling events |
| SuccessfulRequestLatency | Successful request latency |

### Step 1 — Configure Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' \
  '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u \
  '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect GSI Read Capacity

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=GlobalSecondaryIndexName,Value="$INDEX_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 3 — Inspect GSI Write Capacity

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=GlobalSecondaryIndexName,Value="$INDEX_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 4 — Save Monitoring Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=GlobalSecondaryIndexName,Value="$INDEX_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION" \
  > evidence/gsi-write-capacity.json
```

### Monitoring Interpretation

CloudWatch metrics help identify index capacity consumption and performance issues.

However, they do not directly prove why a particular item is missing from an index.

For this incident, the most important evidence is the item's actual attributes and the GSI key schema.

Metrics may not appear immediately because of publication delays.

---

## 22. Root Cause Analysis

### Incident Summary

The DynamoDB table and Global Secondary Index were healthy.

The application experienced missing query results because the requested data did not match the GSI access requirements.

### Fault Comparison

| Fault | Symptom | Root Cause | Remediation |
|---|---|---|---|
| Wrong customer ID | Zero results | Incorrect GSI partition-key value | Correct customer ID |
| Missing created_at | Missing indexed order | Sparse GSI behavior | Populate index key |
| Recent write | Temporary missing record possible | Eventual consistency | Bounded verification |
| Strong read | ValidationException | Unsupported GSI consistency mode | Remove strong-read option |

### Five Whys — Missing Indexed Order

**Why 1 — Why did the GSI return fewer records?**

ORD-7003 was absent from the index.

**Why 2 — Why was ORD-7003 absent?**

The item did not contain `created_at`.

**Why 3 — Why was created_at required?**

It was configured as the GSI sort key.

**Why 4 — Why did the application omit the attribute?**

The simulated data-ingestion workflow did not populate all attributes required by the intended GSI access pattern.

**Why 5 — How can the issue be prevented?**

Validate indexed attributes when creating records, enforce application data contracts, and test GSI queries after deployments.

### Root Cause Diagram

```text
Application Creates Order
          |
          v
Missing created_at Attribute
          |
          v
Base Table Accepts Item
          |
          v
GSI Key Requirements Evaluated
          |
          v
Required Sort Key Missing
          |
          v
Item Excluded From GSI
          |
          v
Query Returns Fewer Results
```

### Root Cause Conclusion

The GSI was operating according to its design.

The underlying problem was incomplete application data rather than index corruption.

---

## 23. Production Troubleshooting Decision Tree

```text
GSI Query Missing Results
           |
           v
Verify AWS Account and Region
           |
           v
DescribeTable
           |
           v
GSI Exists and ACTIVE?
           |
       +---+---+
       |       |
      No      Yes
       |       |
       v       v
Investigate   Verify Index Name
Index State          |
                     v
             Check GSI Key Schema
                     |
                     v
             Verify Query Key Value
                     |
                     v
             Item in Base Table?
                     |
                +----+----+
                |         |
               No        Yes
                |         |
                v         v
         Investigate    Inspect GSI
         Source Data    Key Attributes
                          |
                    +-----+-----+
                    |           |
                 Missing      Present
                    |           |
                    v           v
             Correct Data   Check Propagation
                    |           |
                    +-----+-----+
                          |
                          v
                    Retry Query
                          |
                          v
                    Verify Results
```

### Investigation Checklist

| Check | Expected Result |
|---|---|
| AWS Account | Correct |
| Region | us-east-1 |
| Base Table | ddb-lab07-orders |
| Base Table Status | ACTIVE |
| GSI | CustomerOrdersIndex |
| GSI Status | ACTIVE |
| GSI Partition Key | customer_id |
| GSI Sort Key | created_at |
| GSI Projection | ALL |
| Query Customer ID | Correct |
| Indexed Attributes | Present |
| Read Consistency | Eventual |
| Final Query | Expected records returned |

---

## 24. Cloud Security Engineering Considerations

### IAM Least Privilege

IAM policies should authorize only the required DynamoDB operations and resources.

For a GSI Query, permissions may need to reference the index ARN.

### Data Exposure Through Index Projections

This lab uses:

```text
ProjectionType = ALL
```

This projects all base-table attributes into the GSI for eligible items.

In production, this may be unnecessary.

Review whether `KEYS_ONLY` or `INCLUDE` would better satisfy the application's requirements while limiting indexed data and cost.

### Multi-Tenant Isolation

A partition key such as `customer_id` does not automatically enforce authorization.

Applications must ensure that authenticated users can access only permitted customer records.

### Input Validation

Validate customer identifiers and required indexed attributes before writing database items.

### Monitoring

Monitor unusual database query patterns, index capacity, and authorization failures.

### Logging

Avoid including sensitive customer records in troubleshooting logs.

### Security Principle

**A Global Secondary Index introduces another access path to application data. Cloud Security Engineers must review both the index design and the authorization controls protecting that access.**

---

## 25. Cost Management

### Potential Charges

| AWS Resource | Cost Consideration |
|---|---|
| DynamoDB Table | Read/write requests and storage |
| Global Secondary Index | Index storage and access costs |
| Index Projection ALL | Additional indexed attribute storage |
| CloudWatch | Applicable monitoring charges |
| IAM | No separate standard IAM role charge |
| AWS CLI | No separate CLI fee |

### Lab Cost Controls

- Use one temporary DynamoDB table.
- Use one GSI.
- Store only four fabricated orders.
- Avoid unnecessary table-wide scans.
- Use bounded propagation checks.
- Delete the table after completing the exercise.

### Production Cost Consideration

GSIs can improve query efficiency but create additional storage and write overhead.

Design indexes around actual access patterns.

---

## 26. Final Recovery Verification

### Step 1 — Query Customer CUST-1001

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --region "$AWS_REGION" \
  > evidence/final-customer-orders.json
```

### Step 2 — Validate Three Orders

```bash
jq -e '
  .Count == 3 and
  ([.Items[].order_id.S] | sort) ==
  ["ORD-7001","ORD-7003","ORD-7004"]
' evidence/final-customer-orders.json
```

Expected:

```text
true
```

### Step 3 — Query CUST-1002

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --index-name "$INDEX_NAME" \
  --key-condition-expression \
    "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1002"}
  }' \
  --region "$AWS_REGION"
```

Expected: ORD-7002.

### Step 4 — Verify Index Status

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.GlobalSecondaryIndexes[].{
    Name:IndexName,
    Status:IndexStatus
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
CustomerOrdersIndex = ACTIVE
```

### Step 5 — Verify Base Table

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/final-base-table-items.json
```

### Step 6 — Validate Four Orders

```bash
jq -e '
  ([.Items[].order_id.S] | sort) ==
  ["ORD-7001","ORD-7002","ORD-7003","ORD-7004"]
' evidence/final-base-table-items.json
```

Expected:

```text
true
```

### Recovery Summary

| Component | Broken | Recovered |
|---|---|---|
| Customer ID | Incorrect | Correct |
| ORD-7003 created_at | Missing | Present |
| ORD-7003 GSI Visibility | Absent | Indexed |
| ORD-7004 GSI Visibility | May be delayed | Visible |
| GSI Status | ACTIVE | ACTIVE |
| Final CUST-1001 Results | One or fewer initially | Three |
| Base Table | Healthy | Healthy |

---

## 27. Save Lab Environment and Cleanup

### Step 1 — Save Resource Variables

```bash
cat > lab07-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export INDEX_NAME="$INDEX_NAME"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab07-resources.env
```

### Step 2 — Restore Variables When Needed

```bash
source lab07-resources.env
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

### Step 4 — Verify Resource Tags

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab07
```

### Step 5 — Delete Temporary Table

Only after verifying this is the disposable lab table:

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

Deleting the base table also deletes the associated GSI.

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| CustomerOrdersIndex | Deleted with table |
| Test Orders | Deleted |
| IAM Roles | None created |
| Lambda | None created |
| EC2 | None created |
| NAT Gateway | None created |
| Local JSON Files | Retained |
| Evidence Files | Retained locally |

---

## 28. Interview Questions and Answers

### Q1. What is a DynamoDB Global Secondary Index?

A GSI provides an additional way to query DynamoDB data using a different key schema from the base table.

### Q2. What is the difference between a base table and a GSI?

The base table stores the original items. A GSI maintains an alternate representation of qualifying items using its own key schema.

### Q3. What is a sparse GSI?

A GSI that represents only items containing the attributes required by its index key schema.

### Q4. Why can an item exist in a base table but not appear in a GSI?

It may lack a required GSI key attribute or the index update may not have propagated yet.

### Q5. What happens if the GSI sort key is missing?

The item is not represented in that GSI.

### Q6. Are DynamoDB GSIs strongly consistent?

No. GSI reads are eventually consistent.

### Q7. What happens if ConsistentRead=true is used on a GSI?

DynamoDB rejects the request with a validation error.

### Q8. How do you check GSI status?

Use DescribeTable and inspect GlobalSecondaryIndexes and IndexStatus.

### Q9. What does ACTIVE mean for a GSI?

The index is available for normal query operations.

### Q10. What is ProjectionType=ALL?

It projects all base-table attributes into the index for indexed items.

### Q11. What are the other GSI projection types?

KEYS_ONLY and INCLUDE.

### Q12. Does ProjectionType=ALL include items missing GSI keys?

No. Projection type does not override sparse-index behavior.

### Q13. Can a GSI use different key attributes from the base table?

Yes. Supporting alternate key access patterns is a primary purpose of GSIs.

### Q14. How can you troubleshoot missing GSI results?

Verify the index, Query key values, base-table item, required GSI attributes, index status, and synchronization behavior.

### Q15. Why shouldn't you immediately rebuild a GSI when records are missing?

The issue may be caused by incorrect application data, query parameters, or eventual consistency rather than index infrastructure.

### Q16. How do GSIs affect cost?

They introduce additional indexed storage and read/write usage.

### Q17. Can a GSI partition key enforce tenant isolation?

No. Access authorization must be enforced separately.

### Q18. What IAM resource should be considered for Query operations against a GSI?

The appropriate index ARN.

### Q19. What is a common GSI eventual-consistency troubleshooting mistake?

Assuming that a successful base-table write guarantees immediate visibility through the GSI.

### Q20. How would you explain this lab in a technical interview?

I created a DynamoDB table using AWS CLI with `order_id` as the partition key.

I also created a Global Secondary Index named `CustomerOrdersIndex` with `customer_id` as the partition key and `created_at` as the sort key.

I inserted three sample orders and reproduced a situation where the GSI returned fewer records than expected.

I verified that a missing order existed in the base table but was absent from the GSI because the required `created_at` attribute was missing.

I investigated the index configuration using DescribeTable and compared its key schema with the actual item attributes.

I corrected the missing attribute using UpdateItem and verified that the GSI eventually returned the order.

I also investigated incorrect GSI partition-key values and demonstrated eventual consistency by inserting another order.

Finally, I verified the expected records, reviewed CloudWatch metrics and IAM security considerations, and deleted the temporary resources.

This lab demonstrated DynamoDB GSI troubleshooting, sparse-index behavior, eventual consistency, and production root cause analysis.

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
│   └── README.md
│
├── 06-conditional-check-failed/
│   └── README.md
│
├── 07-gsi-query-not-returning-results/
│   ├── README.md
│   ├── .gitignore
│   ├── orders.json
│   ├── lab07-resources.env
│   │
│   └── evidence/
│       ├── table-description.json
│       ├── base-table-items.json
│       ├── healthy-gsi-query.json
│       ├── wrong-gsi-key.json
│       ├── recovered-gsi-key.json
│       ├── missing-indexed-order.json
│       ├── sparse-index-recovered.json
│       ├── gsi-strong-read-output.json
│       ├── gsi-strong-read-error.log
│       ├── gsi-propagation.json
│       ├── final-table-description.json
│       ├── gsi-write-capacity.json
│       ├── final-customer-orders.json
│       └── final-base-table-items.json
│
├── 08-dynamodb-streams-not-triggering/
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

Evidence files exist locally only after the corresponding commands have been executed.

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Production troubleshooting documentation |
| .gitignore | Excludes local evidence and configuration |
| orders.json | Initial three fabricated orders |
| lab07-resources.env | Local AWS configuration |
| table-description.json | Initial table and GSI metadata |
| base-table-items.json | Base-table verification |
| healthy-gsi-query.json | Initial indexed records |
| wrong-gsi-key.json | Incorrect customer-ID evidence |
| recovered-gsi-key.json | Correct customer-ID query |
| missing-indexed-order.json | Missing GSI key evidence |
| sparse-index-recovered.json | Corrected item indexing |
| gsi-strong-read-error.log | Unsupported strong-consistency request |
| gsi-propagation.json | Index synchronization verification |
| gsi-write-capacity.json | CloudWatch GSI metrics |
| final-customer-orders.json | Final customer-specific query |
| final-base-table-items.json | Final base-table records |

### Recommended Public GitHub Structure

```text
07-gsi-query-not-returning-results/
├── README.md
├── .gitignore
└── orders.json
```

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 07
07-gsi-query-not-returning-results/evidence/
07-gsi-query-not-returning-results/lab07-resources.env

# Local AWS environment
.env
.env.*
*-resources.env

# Python
__pycache__/
*.pyc
.venv/

# Credentials
*.pem
*.key

# Logs
*.log
```

Do not commit AWS credentials, sensitive customer records, or unreviewed account-specific evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how DynamoDB Global Secondary Index queries can return unexpected results even when the base table and index infrastructure are healthy.

We created a DynamoDB table with a Global Secondary Index supporting customer-order queries.

We inserted sample orders and verified that the base table contained the expected records.

First, we intentionally queried the GSI using an incorrect customer identifier.

The Query operation succeeded but returned no matching items.

After correcting the partition-key value, the expected indexed record was returned.

Next, we investigated a record that existed in the base table but was missing from the GSI.

The investigation revealed that the item lacked the required GSI sort-key attribute.

We corrected the item using UpdateItem and verified that it became visible in the index after synchronization.

Finally, we investigated GSI eventual consistency.

We inserted a new order and compared base-table visibility with GSI query behavior.

We also demonstrated that GSIs do not support strongly consistent reads.

We completed the lab by inspecting index status, reviewing CloudWatch monitoring, applying security considerations, and cleaning up temporary resources.

**Key Lesson:** A missing GSI result should be investigated by comparing the GSI key schema, requested values, actual item attributes, index status, and synchronization behavior before making infrastructure changes.

### Skills Demonstrated

- Amazon DynamoDB.
- Global Secondary Indexes.
- GSI partition keys.
- GSI sort keys.
- Sparse indexes.
- Eventual consistency.
- GSI projections.
- DescribeTable.
- Query.
- GetItem.
- PutItem.
- BatchWriteItem.
- UpdateItem.
- AWS CLI v2.
- Linux Bash.
- jq.
- CloudWatch investigation.
- Index synchronization verification.
- Root cause analysis.
- IAM least privilege.
- Multi-tenant security.
- Data access troubleshooting.
- AWS cost management.
- Resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-007 |
| Scenario | GSI Query Not Returning Results |
| Base Table | ddb-lab07-orders |
| Region | us-east-1 |
| Base Partition Key | order_id |
| GSI | CustomerOrdersIndex |
| GSI Partition Key | customer_id |
| GSI Sort Key | created_at |
| Projection | ALL |
| Billing Mode | PAY_PER_REQUEST |
| Initial Orders | 3 |
| Fault 01 | Incorrect customer ID |
| Fault 01 Result | Zero items |
| Fault 01 Remediation | Correct partition-key value |
| Fault 02 | Missing created_at |
| Fault 02 Result | Missing indexed order |
| Fault 02 Remediation | Populate required attribute |
| Fault 03 | Eventual consistency |
| Fault 03 Result | Possible temporary propagation delay |
| Additional Error | ValidationException for strong GSI read |
| Final Base-Table Items | 4 |
| Final CUST-1001 GSI Results | 3 |
| Final GSI Status | ACTIVE |
| Cleanup | Table and GSI deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Production DynamoDB engineers must understand that Global Secondary Indexes provide eventually consistent, alternate access paths to qualifying items. Correct index-key attributes, query parameters, synchronization checks, and access controls are essential for reliable GSI operations.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [Using Global Secondary Indexes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)
- [Sparse Index Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes-general-sparse-indexes.html)
- [AWS CLI — CreateTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/create-table.html)
- [AWS CLI — DescribeTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/describe-table.html)
- [AWS CLI — Query](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/query.html)
- [AWS CLI — GetItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-item.html)
- [AWS CLI — UpdateItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/update-item.html)
- [DynamoDB Query Key Conditions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.KeyConditionExpressions.html)
- [DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [DynamoDB IAM Access Control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/UsingIAMWithDDB.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)