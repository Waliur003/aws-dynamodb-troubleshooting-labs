# Lab 04 — Amazon DynamoDB Wrong Partition Key

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve Amazon DynamoDB data retrieval failures caused by incorrect partition-key values, missing sort keys, and incorrect primary-key attribute names.

In production, applications commonly retrieve records from DynamoDB using primary keys.

A DynamoDB table can use either a simple primary key consisting of a partition key or a composite primary key consisting of both a partition key and a sort key.

For a composite primary key, DynamoDB uses the combination of both values to uniquely identify an item.

In this lab, we create a DynamoDB table named `ddb-lab04-orders` in the `us-east-1` Region.

The table uses:

- Partition key: `customer_id`
- Sort key: `order_id`
- Key data types: String
- Billing mode: PAY_PER_REQUEST

We insert three fabricated customer orders and verify successful data retrieval.

Next, we reproduce three production-style problems:

1. An application uses the wrong partition-key value.
2. An application calls GetItem without the required sort key.
3. An application uses an incorrect partition-key attribute name.

These problems produce different behaviors.

A valid request with an incorrect partition-key value normally returns no matching item.

An incomplete primary key or incorrect key attribute name can produce `ValidationException`.

We investigate each failure using AWS CLI, table metadata, GetItem, Query, request JSON, and evidence files.

After identifying the root cause, we correct the requests, verify successful data retrieval, review cloud security implications, and clean up the temporary AWS resources.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Configure AWS CLI and Region
          |
          v
Create DynamoDB Table
          |
          v
Configure Composite Primary Key
          |
          v
Wait for ACTIVE Status
          |
          v
Insert Three Test Orders
          |
          v
Verify Healthy GetItem
          |
          v
Verify Query for CUST-1001
          |
          v
Fault 01 — Wrong Partition-Key Value
          |
          v
GetItem Returns No Item
          |
          v
Investigate Customer ID
          |
          v
Correct Partition-Key Value
          |
          v
Verify Order Retrieved
          |
          v
Fault 02 — Missing Sort Key
          |
          v
ValidationException
          |
          v
Supply Complete Primary Key
          |
          v
Verify Order Retrieved
          |
          v
Fault 03 — Wrong Key Attribute Name
          |
          v
ValidationException
          |
          v
Correct Attribute Name
          |
          v
Verify Order Retrieved
          |
          v
Compare GetItem and Query
          |
          v
Root Cause Analysis
          |
          v
Verify All Three Orders
          |
          v
Cloud Security Review
          |
          v
Cost Management
          |
          v
Resource Cleanup
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-004 |
| Lab Name | DynamoDB Wrong Partition Key |
| Difficulty | Intermediate |
| Primary Service | Amazon DynamoDB |
| Supporting Services | AWS IAM, STS, CloudWatch |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, jq |
| Table Name | `ddb-lab04-orders` |
| Partition Key | `customer_id` |
| Partition-Key Type | String |
| Sort Key | `order_id` |
| Sort-Key Type | String |
| Primary Key | Composite |
| Billing Mode | PAY_PER_REQUEST |
| Test Items | 3 |
| Primary Operations | GetItem, Query |
| Supporting Operations | BatchWriteItem, Scan, DescribeTable |
| Fault 01 | Wrong partition-key value |
| Fault 02 | Missing sort key |
| Fault 03 | Wrong partition-key attribute name |
| Expected Fault 01 Result | No Item returned |
| Expected Faults 02–03 Result | ValidationException |
| Remediation | Correct primary-key values and structure |
| Recovery | Successful GetItem and Query |
| Resource Tag | DynamoDB-Troubleshooting-Lab04 |
| Cleanup | Delete temporary DynamoDB table |

### Learning Objectives

- Understand DynamoDB partition keys.
- Understand DynamoDB sort keys.
- Understand composite primary keys.
- Create DynamoDB tables using AWS CLI.
- Insert items using BatchWriteItem.
- Retrieve items using GetItem.
- Retrieve item collections using Query.
- Understand primary-key uniqueness.
- Troubleshoot incorrect partition-key values.
- Troubleshoot missing sort keys.
- Troubleshoot incorrect attribute names.
- Distinguish missing items from validation errors.
- Investigate DynamoDB key schemas.
- Understand KeyConditionExpression.
- Collect production incident evidence.
- Perform root cause analysis.
- Apply configuration-based remediation.
- Verify database recovery.
- Understand multi-tenant database security.
- Manage DynamoDB costs.
- Safely clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management application that stores customer orders in Amazon DynamoDB.

The application uses a table named:

`ddb-lab04-orders`

The table contains orders belonging to multiple customers.

Each order is identified by the combination of:

`customer_id + order_id`

Example data:

| customer_id | order_id | status | amount |
|---|---|---|---|
| CUST-1001 | ORD-4001 | Processing | 150 |
| CUST-1001 | ORD-4002 | Shipped | 200 |
| CUST-1002 | ORD-4003 | Pending | 300 |

Under normal conditions, the application retrieves an order using:

```json
{
  "customer_id": {"S": "CUST-1001"},
  "order_id": {"S": "ORD-4001"}
}
```

During a deployment, an engineer introduces an incorrect customer identifier.

The application begins using:

```text
customer_id = CUST-9999
```

instead of:

```text
customer_id = CUST-1001
```

The application sends a valid GetItem request, but DynamoDB cannot find an item matching the specified key combination.

The request succeeds without returning an Item field.

The application reports that the order cannot be found.

The development team initially suspects a missing database record.

However, the Cloud Engineering team investigates and discovers:

- The DynamoDB table exists.
- The table status is ACTIVE.
- The AWS account and Region are correct.
- The requested order still exists.
- The partition-key value is incorrect.
- A request using the correct key retrieves the order.

The investigation also identifies additional application errors involving incomplete and incorrectly named primary keys.

After correcting the requests, all expected orders can be retrieved successfully.

### Incident Symptoms

- GetItem returns no Item for an incorrect customer ID.
- Query returns no records for an incorrect partition-key value.
- GetItem with a missing sort key produces ValidationException.
- GetItem with an incorrect key attribute name produces ValidationException.
- The DynamoDB table remains ACTIVE.
- Existing data is preserved.
- Corrected requests successfully retrieve records.

### Business Impact

Incorrect partition-key usage can cause:

- Failed order lookups.
- Incorrect application responses.
- Missing customer information.
- Broken customer dashboards.
- Failed API requests.
- Data retrieval inconsistencies.
- Unnecessary database troubleshooting.
- Application reliability problems.

In multi-tenant systems, incorrect customer identifiers can also create security risks if access controls do not properly isolate tenant data.

### Incident Objective

Determine whether a failed DynamoDB retrieval results from an incorrect key value, missing key component, incorrectly named attribute, or a genuinely missing record.

Restore the application without unnecessarily changing the table schema or stored data.

---

## 3. AWS Architecture

### Healthy Architecture

```text
              Order Application
                     |
                     v
               AWS SDK / CLI
                     |
                     v
              Amazon DynamoDB
                     |
                     v
            ddb-lab04-orders
                     |
                     v
              Composite Key
                     |
           +---------+---------+
           |                   |
           v                   v
      customer_id           order_id
       CUST-1001            ORD-4001
           |                   |
           +---------+---------+
                     |
                     v
               GetItem
                     |
                     v
             Matching Item Found
                     |
                     v
             Order Retrieved
```

### Broken Architecture — Wrong Partition-Key Value

```text
              Order Application
                     |
                     v
            Incorrect Customer ID
                     |
                     v
            customer_id = CUST-9999
            order_id    = ORD-4001
                     |
                     v
               DynamoDB GetItem
                     |
                     v
           Valid Primary-Key Format
                     |
                     v
            No Matching Item
                     |
                     v
            Response Without Item
```

### Broken Architecture — Incomplete Primary Key

```text
              Order Application
                     |
                     v
              GetItem Request
                     |
                     v
            customer_id = CUST-1001
                     |
                     v
             Sort Key Missing
                     |
                     v
           DynamoDB Key Validation
                     |
                     v
             ValidationException
```

### Recovered Architecture

```text
              Order Application
                     |
                     v
            Correct Primary Key
                     |
          +----------+----------+
          |                     |
          v                     v
    customer_id              order_id
     CUST-1001               ORD-4001
          |                     |
          +----------+----------+
                     |
                     v
               DynamoDB GetItem
                     |
                     v
             Matching Item Found
                     |
                     v
              Order Retrieved
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon DynamoDB | Stores order data |
| DynamoDB Table | Holds customer orders |
| Partition Key | Groups items by customer ID |
| Sort Key | Differentiates orders within a customer |
| GetItem | Retrieves a specific item |
| Query | Retrieves matching items by key conditions |
| Scan | Inspects all records in the small test table |
| DescribeTable | Inspects table configuration |
| AWS STS | Verifies AWS identity |
| IAM | Authorizes database operations |
| AWS CLI | Executes DynamoDB requests |
| Bash | Manages configuration |
| jq | Generates and validates JSON |

---

## 4. Understanding DynamoDB Partition Keys

The partition key is a required component of every DynamoDB table's primary key.

DynamoDB uses the partition-key value as input to its internal data-distribution mechanism.

Items with the same partition-key value can belong to the same logical item collection when the table also has a sort key.

For example:

```text
customer_id = CUST-1001
```

can be associated with multiple orders.

### Example

| Partition Key | Sort Key |
|---|---|
| CUST-1001 | ORD-4001 |
| CUST-1001 | ORD-4002 |
| CUST-1002 | ORD-4003 |

### Partition-Key Requirements

- Every item must contain the partition key.
- The partition-key type must match the table schema.
- A String partition key cannot have an empty String value.
- A Query operation requires a partition-key equality condition.
- A partition-key value alone does not uniquely identify an item when the table also has a sort key.

### Important Concept

Using an incorrect but valid partition-key value does not necessarily produce an exception.

DynamoDB can successfully process the request and return no matching item.

---

## 5. Understanding Composite Primary Keys

A composite primary key contains:

1. A partition key.
2. A sort key.

For this lab:

```text
Partition Key: customer_id
Sort Key: order_id
```

Together:

```text
customer_id + order_id
```

uniquely identify an item.

### Example

```text
CUST-1001 + ORD-4001
```

and:

```text
CUST-1001 + ORD-4002
```

are two different items.

### Primary-Key Configuration

| Attribute | Key Type | Data Type |
|---|---|---|
| customer_id | HASH | String |
| order_id | RANGE | String |

`HASH` identifies the partition key.

`RANGE` identifies the sort key.

### GetItem Requirement

For a composite-key table, GetItem requires both attributes.

### Query Requirement

Query requires an equality condition on the partition key.

A sort-key condition is optional.

This makes Query useful when an application needs multiple orders belonging to one customer.

---

## 6. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- jq.
- AWS account.
- DynamoDB create/read/write/delete permissions.

### Relevant IAM Actions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:ListTables
dynamodb:ListTagsOfResource
dynamodb:BatchWriteItem
dynamodb:GetItem
dynamodb:Query
dynamodb:Scan
dynamodb:DeleteTable
```

These are relevant actions, not a complete deployable IAM policy.

### Safety Rules

- Use a dedicated temporary DynamoDB table.
- Never modify unrelated production tables.
- Use fabricated customer and order identifiers.
- Verify account and Region before deploying resources.
- Keep the test data set small.
- Do not publish credentials.
- Review IAM permissions.
- Verify the resource tag before deletion.
- Delete temporary resources after testing.

### Resource Identification

The lab uses:

```text
Project = DynamoDB-Troubleshooting-Lab04
```

---

## 7. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 04-wrong-partition-key

cd 04-wrong-partition-key
```

### Step 2 — Verify Tools

```bash
aws --version

jq --version

aws sts get-caller-identity
```

Install jq if needed:

```bash
sudo apt update
sudo apt install -y jq
```

### Step 3 — Configure Variables

```bash
export AWS_REGION="us-east-1"
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export TABLE_NAME="ddb-lab04-orders"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab04"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"

export CORRECT_CUSTOMER="CUST-1001"
export WRONG_CUSTOMER="CUST-9999"
export ORDER_ID="ORD-4001"
```

### Step 4 — Verify Variables

```bash
echo "$AWS_REGION"
echo "$TABLE_NAME"
echo "$TABLE_ARN"
echo "$CORRECT_CUSTOMER"
```

### Step 5 — Create Evidence Directory

```bash
mkdir -p evidence
```

### Step 6 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
evidence/
lab04-resources.env

*.log

__pycache__/
*.pyc

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

### Step 2 — Verify Region

```bash
echo "$AWS_REGION"
```

Expected:

```text
us-east-1
```

### Step 3 — List Existing Tables

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

### Step 4 — Check for Existing Lab Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected before table creation:

```text
ResourceNotFoundException
```

If a table already exists, verify its ownership before continuing.

Do not overwrite or delete an unrelated table.

---

## 9. Create DynamoDB Table

### Step 1 — Create Composite-Key Table

```bash
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=customer_id,AttributeType=S \
    AttributeName=order_id,AttributeType=S \
  --key-schema \
    AttributeName=customer_id,KeyType=HASH \
    AttributeName=order_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Configuration Explanation

| Parameter | Purpose |
|---|---|
| Table Name | ddb-lab04-orders |
| customer_id | Partition key |
| order_id | Sort key |
| AttributeType=S | String |
| HASH | Partition-key definition |
| RANGE | Sort-key definition |
| PAY_PER_REQUEST | On-demand capacity |
| Project Tag | Lab identification |

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
    Keys:KeySchema,
    Attributes:AttributeDefinitions
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Step 4 — Save Metadata

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/table-description.json
```

Expected status:

```text
ACTIVE
```

---

## 10. Insert Three Test Orders

### Step 1 — Create `orders.json`

```bash
cat > orders.json <<'EOF'
{
  "ddb-lab04-orders": [
    {
      "PutRequest": {
        "Item": {
          "customer_id": {"S": "CUST-1001"},
          "order_id": {"S": "ORD-4001"},
          "status": {"S": "Processing"},
          "amount": {"N": "150"}
        }
      }
    },
    {
      "PutRequest": {
        "Item": {
          "customer_id": {"S": "CUST-1001"},
          "order_id": {"S": "ORD-4002"},
          "status": {"S": "Shipped"},
          "amount": {"N": "200"}
        }
      }
    },
    {
      "PutRequest": {
        "Item": {
          "customer_id": {"S": "CUST-1002"},
          "order_id": {"S": "ORD-4003"},
          "status": {"S": "Pending"},
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

### Step 3 — Insert Items

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

If UnprocessedItems is not empty, retry the unprocessed requests before continuing.

### Step 4 — Verify Data

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected: three test orders.

The order of scanned items is not guaranteed.

### Step 5 — Save Initial Evidence

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/initial-items.json
```

---

## 11. Establish Healthy GetItem Baseline

### Step 1 — Retrieve ORD-4001

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{
    "customer_id": {"S": "CUST-1001"},
    "order_id": {"S": "ORD-4001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected response includes:

```json
{
  "Item": {
    "customer_id": {"S": "CUST-1001"},
    "order_id": {"S": "ORD-4001"},
    "status": {"S": "Processing"},
    "amount": {"N": "150"}
  }
}
```

### Step 2 — Save Healthy Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{
    "customer_id": {"S": "CUST-1001"},
    "order_id": {"S": "ORD-4001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/healthy-get-item.json
```

### Step 3 — Validate

```bash
jq -e '
  .Item.customer_id.S == "CUST-1001" and
  .Item.order_id.S == "ORD-4001"
' evidence/healthy-get-item.json
```

Expected:

```text
true
```

### Step 4 — Query Customer Orders

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
Count = 2
```

### Healthy Baseline

| Component | Expected Result |
|---|---|
| Table | ACTIVE |
| AWS Region | Correct |
| Partition Key | customer_id |
| Sort Key | order_id |
| GetItem | Successful |
| Query | Two matching orders |
| Exception | None |

---

## 12. Fault Injection 01 — Wrong Partition-Key Value

### Production Fault

The application requests:

```text
customer_id = CUST-9999
order_id = ORD-4001
```

The actual record belongs to:

```text
customer_id = CUST-1001
order_id = ORD-4001
```

### Step 1 — Configure Incorrect Customer

```bash
export APP_CUSTOMER_ID="$WRONG_CUSTOMER"
```

Verify:

```bash
echo "$APP_CUSTOMER_ID"
```

Expected:

```text
CUST-9999
```

### Step 2 — Generate Wrong Key

```bash
jq -n \
  --arg customer "$APP_CUSTOMER_ID" \
  --arg order "$ORDER_ID" \
  '{
    customer_id: {S: $customer},
    order_id: {S: $order}
  }' > wrong-partition-key.json
```

### Step 3 — Inspect Request

```bash
jq . wrong-partition-key.json
```

### Step 4 — Attempt GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://wrong-partition-key.json \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```json
{}
```

The request succeeds, but the response does not contain an Item.

### Step 5 — Capture Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://wrong-partition-key.json \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/wrong-partition-key-response.json
```

### Step 6 — Validate Missing Item

```bash
jq -e 'has("Item") | not' \
  evidence/wrong-partition-key-response.json
```

Expected:

```text
true
```

### Important Observation

This is not ResourceNotFoundException.

The table exists, the request is valid, and DynamoDB successfully performs the lookup.

No item matches the supplied composite key.

---

## 13. Investigate Fault 01 — Incorrect Customer ID

### Step 1 — Inspect Configuration

```bash
echo "Application Customer: $APP_CUSTOMER_ID"

echo "Expected Customer: $CORRECT_CUSTOMER"

echo "Order: $ORDER_ID"
```

### Step 2 — Query Incorrect Customer

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-9999"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Items": [],
  "Count": 0,
  "ScannedCount": 0
}
```

Additional response fields may be present.

### Step 3 — Query Correct Customer

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
Count = 2
```

### Step 4 — Inspect Table Schema

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.KeySchema' \
  --output json \
  --region "$AWS_REGION"
```

### Step 5 — Save Investigation Evidence

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/correct-customer-query.json
```

### Investigation Findings

- The table exists.
- The data exists.
- The wrong customer ID returns no items.
- The correct customer ID returns two orders.
- The key structure is valid.
- The application has an incorrect partition-key value.

**Root Cause:** Incorrect customer identifier in the request.

---

## 14. Remediation 01 — Correct Partition-Key Value

### Step 1 — Restore Correct Customer

```bash
export APP_CUSTOMER_ID="$CORRECT_CUSTOMER"
```

### Step 2 — Generate Correct Key

```bash
jq -n \
  --arg customer "$APP_CUSTOMER_ID" \
  --arg order "$ORDER_ID" \
  '{
    customer_id: {S: $customer},
    order_id: {S: $order}
  }' > correct-partition-key.json
```

### Step 3 — Retry GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://correct-partition-key.json \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: ORD-4001 is returned.

### Step 4 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://correct-partition-key.json \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-partition-key.json
```

### Step 5 — Verify Recovery

```bash
jq -e '
  .Item.customer_id.S == "CUST-1001" and
  .Item.order_id.S == "ORD-4001"
' evidence/recovered-partition-key.json
```

Expected:

```text
true
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| Customer ID | CUST-9999 | CUST-1001 |
| Order ID | ORD-4001 | ORD-4001 |
| Key Structure | Valid | Valid |
| GetItem Response | No Item | Item returned |
| Table Modification | None | None |

**Fault 01 is resolved when the corrected composite key retrieves ORD-4001.**

---

## 15. Fault Injection 02 — Missing Sort Key

### Production Fault

The application attempts GetItem using only the partition key.

However, the table uses a composite primary key.

### Step 1 — Create Incomplete Key

```bash
cat > missing-sort-key.json <<'EOF'
{
  "customer_id": {"S": "CUST-1001"}
}
EOF
```

### Step 2 — Inspect JSON

```bash
jq . missing-sort-key.json
```

### Step 3 — Attempt GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://missing-sort-key.json \
  --region "$AWS_REGION"
```

Expected:

```text
ValidationException
```

A common message is:

```text
The provided key element does not match the schema
```

### Step 4 — Save Failure Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://missing-sort-key.json \
  --region "$AWS_REGION" \
  > evidence/missing-sort-key-output.json \
  2> evidence/missing-sort-key-error.log

echo "Exit code: $?"
```

Expected: nonzero exit code.

### Step 5 — Inspect Error

```bash
cat evidence/missing-sort-key-error.log
```

### Root Cause

The GetItem request does not include the required sort key.

Unlike an incorrect key value, an incomplete primary-key structure violates the table schema.

---

## 16. Remediation 02 — Supply Complete Primary Key

### Step 1 — Create Correct Key

```bash
cat > complete-primary-key.json <<'EOF'
{
  "customer_id": {"S": "CUST-1001"},
  "order_id": {"S": "ORD-4002"}
}
EOF
```

### Step 2 — Retry GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://complete-primary-key.json \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: ORD-4002 is returned.

### Step 3 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://complete-primary-key.json \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-sort-key.json
```

### Step 4 — Validate

```bash
jq -e '.Item.order_id.S == "ORD-4002"' \
  evidence/recovered-sort-key.json
```

Expected:

```text
true
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| Partition Key | Present | Present |
| Sort Key | Missing | Present |
| GetItem | ValidationException | Success |
| Table Schema | Unchanged | Unchanged |

**Fault 02 is resolved when GetItem receives both required primary-key attributes.**

### Production Alternative

If the application only knows the customer ID and needs all customer orders, use Query instead of GetItem.

---

## 17. Fault Injection 03 — Incorrect Key Attribute Name

### Production Fault

The table requires:

```text
customer_id
```

The application sends:

```text
customerId
```

### Step 1 — Create Invalid Key

```bash
cat > wrong-key-name.json <<'EOF'
{
  "customerId": {"S": "CUST-1001"},
  "order_id": {"S": "ORD-4001"}
}
EOF
```

### Step 2 — Inspect JSON

```bash
jq . wrong-key-name.json
```

### Step 3 — Attempt GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://wrong-key-name.json \
  --region "$AWS_REGION"
```

Expected:

```text
ValidationException
```

### Step 4 — Capture Failure

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://wrong-key-name.json \
  --region "$AWS_REGION" \
  > evidence/wrong-key-name-output.json \
  2> evidence/wrong-key-name-error.log

echo "Exit code: $?"
```

### Step 5 — Inspect Error

```bash
cat evidence/wrong-key-name-error.log
```

### Step 6 — Compare Schema

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.KeySchema' \
  --output json \
  --region "$AWS_REGION"
```

### Root Cause

The request uses an attribute name that does not match the actual table's partition-key name.

DynamoDB treats `customer_id` and `customerId` as different attributes.

---

## 18. Remediation 03 — Correct Attribute Name

### Step 1 — Create Correct Key

```bash
cat > fixed-key-name.json <<'EOF'
{
  "customer_id": {"S": "CUST-1001"},
  "order_id": {"S": "ORD-4001"}
}
EOF
```

### Step 2 — Retry GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://fixed-key-name.json \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: ORD-4001 is returned.

### Step 3 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key file://fixed-key-name.json \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-key-name.json
```

### Step 4 — Verify

```bash
jq -e '
  .Item.customer_id.S == "CUST-1001" and
  .Item.order_id.S == "ORD-4001"
' evidence/recovered-key-name.json
```

Expected:

```text
true
```

**Fault 03 is resolved when the request uses the correct primary-key attribute names.**

---

## 19. Understanding GetItem vs. Query

GetItem and Query solve different data retrieval problems.

### GetItem

GetItem retrieves an item using its complete primary key.

For a composite-key table:

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{
    "customer_id": {"S": "CUST-1001"},
    "order_id": {"S": "ORD-4001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Query by Partition Key

Query can retrieve all items for a given partition-key value.

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression "customer_id = :customer" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
Count = 2
```

### Query by Partition Key and Sort Key

```bash
aws dynamodb query \
  --table-name "$TABLE_NAME" \
  --key-condition-expression \
    "customer_id = :customer AND order_id = :order" \
  --expression-attribute-values '{
    ":customer": {"S": "CUST-1001"},
    ":order": {"S": "ORD-4001"}
  }' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
Count = 1
```

### Comparison

| Feature | GetItem | Query |
|---|---|---|
| Full primary key required | Yes | No, sort-key condition optional |
| Partition-key equality | Exact key provided | Required |
| Retrieve one specific item | Yes | Yes |
| Retrieve multiple items in partition | No | Yes |
| Supports sort-key conditions | Complete key only | Yes |
| Strongly consistent table read | Supported | Supported |

### Production Recommendation

Use GetItem when the complete primary key is known.

Use Query when retrieving an item collection based on a partition-key value and optional sort-key conditions.

---

## 20. Root Cause Analysis

### Incident Summary

The application generated incorrect DynamoDB key references.

The database infrastructure itself remained healthy.

### Fault Comparison

| Fault | Operation | Behavior | Root Cause |
|---|---|---|---|
| 01 | GetItem | No Item returned | Wrong partition-key value |
| 02 | GetItem | ValidationException | Missing sort key |
| 03 | GetItem | ValidationException | Incorrect key attribute name |

### Five Whys — Wrong Partition-Key Value

**Why 1 — Why did the application fail to retrieve the order?**

DynamoDB returned no matching item.

**Why 2 — Why wasn't the order found?**

The request used the wrong customer ID.

**Why 3 — Why was the customer ID incorrect?**

The application used an incorrect value in its request configuration or data mapping.

**Why 4 — Why wasn't the mismatch detected?**

The simulated deployment did not validate the relationship between the customer and order identifiers.

**Why 5 — How can this be prevented?**

Use consistent primary-key conventions, validate request identifiers, and test DynamoDB access patterns before deployment.

### Root Cause Diagram

```text
Application Deployment
          |
          v
Incorrect Key Configuration
          |
          +--------------------------+
          |                          |
          v                          v
Wrong Value                   Invalid Key Structure
          |                          |
          v                          v
Valid GetItem                 GetItem Validation
          |                          |
          v                          v
No Matching Item              ValidationException
          |
          v
Application Reports Missing Order
```

### Root Cause Conclusion

The correct remediation is to fix the request data or key structure.

There is no need to recreate the DynamoDB table or change its schema.

---

## 21. Production Investigation Decision Tree

```text
DynamoDB GetItem Problem
           |
           v
Check AWS Account and Region
           |
           v
DescribeTable
           |
           v
Table ACTIVE?
           |
       +---+---+
       |       |
      No      Yes
       |       |
       v       v
Investigate  Inspect KeySchema
Table State      |
                v
         Check Key Names
                |
                v
         Check Key Types
                |
                v
       Both Key Parts Present?
                |
           +----+----+
           |         |
          No        Yes
           |         |
           v         v
     Fix Request   Run GetItem
                     |
               +-----+-----+
               |           |
               v           v
          No Item        Item Found
               |           |
               v           v
        Verify Values    Success
               |
               v
         Query Customer
               |
               v
        Correct Identifier
               |
               v
         Retry GetItem
```

### Troubleshooting Checklist

| Check | Expected Result |
|---|---|
| AWS Account | Correct |
| AWS Region | us-east-1 |
| Table Name | ddb-lab04-orders |
| Table Status | ACTIVE |
| Partition Key Name | customer_id |
| Partition Key Type | String |
| Sort Key Name | order_id |
| Sort Key Type | String |
| Request Key Structure | Complete |
| Requested Values | Match stored item |

---

## 22. CloudWatch and Operational Investigation

Amazon DynamoDB publishes operational metrics to CloudWatch.

However, a request that successfully returns no matching item is not necessarily a database error.

A wrong partition-key value can therefore produce an application-level problem without producing a DynamoDB exception.

### Relevant Metrics

| Metric | Purpose |
|---|---|
| SuccessfulRequestLatency | Successful request latency |
| ConsumedReadCapacityUnits | Read capacity usage |
| ReadThrottleEvents | Read throttling |
| SystemErrors | Service-side errors |
| UserErrors | Client-side request errors |

### Step 1 — Set Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect GetItem Latency

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name SuccessfulRequestLatency \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=Operation,Value=GetItem \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Consumed Read Capacity

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 4 — Save Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name SuccessfulRequestLatency \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=Operation,Value=GetItem \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --region "$AWS_REGION" \
  > evidence/getitem-latency.json
```

### Operational Lesson

CloudWatch metrics provide supporting evidence.

For this incident, the strongest diagnostic evidence is the requested primary key, table key schema, and GetItem response.

---

## 23. Cloud Security Engineering Considerations

### Partition Keys Are Not Authorization Controls

A partition key determines how items are identified and accessed.

It does not automatically determine whether a user is authorized to read the data.

### Multi-Tenant Security

In a multi-tenant application, each customer may have records associated with a customer identifier.

For example:

```text
CUST-1001
CUST-1002
```

The application must ensure that one customer cannot retrieve another customer's data simply by modifying the customer ID supplied to the database.

### Fine-Grained Access Control

DynamoDB supports condition keys such as:

`dynamodb:LeadingKeys`

These can help restrict appropriate item-level access patterns through IAM policy conditions.

### Security Best Practices

- Derive customer identity from trusted authentication context.
- Do not blindly trust customer IDs submitted by clients.
- Use least-privilege IAM permissions.
- Validate primary-key values.
- Implement tenant isolation in application authorization.
- Protect sensitive attributes.
- Avoid logging customer data unnecessarily.
- Review data access patterns.
- Test cross-tenant access restrictions.
- Use appropriate encryption and backup controls.

### Security Principle

**Correct primary-key usage is necessary for data retrieval, but secure authorization is separately required to prevent unauthorized data access.**

---

## 24. Additional Production Troubleshooting Scenarios

### Scenario 1 — Incorrect Customer Identifier

The application sends the wrong customer ID.

**Symptom:** GetItem returns no Item.

**Remediation:** Correct the partition-key value.

### Scenario 2 — Missing Sort Key

The application sends only the partition key to GetItem.

**Symptom:** ValidationException.

**Remediation:** Include the required sort key.

### Scenario 3 — Incorrect Key Attribute Name

The application uses `customerId` instead of `customer_id`.

**Symptom:** ValidationException.

**Remediation:** Match the actual key schema.

### Scenario 4 — Incorrect Key Data Type

The application sends a Number where the schema requires String.

**Symptom:** ValidationException.

**Remediation:** Correct the key type.

### Scenario 5 — Wrong DynamoDB Region

The application requests the table from an incorrect Region.

**Symptom:** ResourceNotFoundException if the table does not exist there.

**Remediation:** Correct the Region.

### Scenario 6 — Wrong AWS Account

The application uses unexpected AWS credentials.

**Symptom:** Resource lookup or authorization problems.

**Remediation:** Verify the caller identity and intended resource account.

### Scenario 7 — Incorrect Query Condition

The application uses an incorrect KeyConditionExpression.

**Symptom:** ValidationException or empty query results, depending on the problem.

**Remediation:** Use the required partition-key equality and an appropriate sort-key condition.

---

## 25. Cost Management

### Cost Components

| Service | Cost Consideration |
|---|---|
| DynamoDB On-Demand | Read and write requests |
| DynamoDB Storage | Stored item data |
| CloudWatch | Applicable metrics and monitoring |
| IAM | No separate standard IAM charge |
| AWS CLI | No separate CLI fee |

### Lab Cost Controls

- Use one disposable table.
- Store only three small items.
- Use on-demand billing.
- Avoid large table scans.
- Avoid uncontrolled test loops.
- Delete the table after verification.

### Production Cost Considerations

Efficient partition-key design and appropriate Query operations help avoid unnecessary table-wide scans.

Poor access patterns can increase database costs and application latency.

Actual charges depend on AWS pricing, account eligibility, and usage.

---

## 26. Save Lab Environment and Verify Recovery

### Step 1 — Save Resource Variables

```bash
cat > lab04-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab04-resources.env
```

### Step 2 — Restore Variables When Needed

```bash
source lab04-resources.env
```

### Step 3 — Save Final Table Contents

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/final-items.json
```

### Step 4 — Validate All Three Items

```bash
jq -e '
  ([.Items[] | [.customer_id.S, .order_id.S]] | sort) ==
  [
    ["CUST-1001", "ORD-4001"],
    ["CUST-1001", "ORD-4002"],
    ["CUST-1002", "ORD-4003"]
  ]
' evidence/final-items.json
```

Expected:

```text
true
```

This verification assumes the dedicated table contains exactly the three intended test items.

### Step 5 — Verify Table Status

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

### Recovery Comparison

| Component | Fault 01 | Fault 02 | Fault 03 | Recovered |
|---|---|---|---|---|
| Partition-key value | Wrong | Correct | Correct | Correct |
| Partition-key name | Correct | Correct | Wrong | Correct |
| Sort key | Present | Missing | Present | Present |
| GetItem result | No Item | ValidationException | ValidationException | Item returned |
| Table configuration | Healthy | Healthy | Healthy | Healthy |

---

## 27. AWS Resource Cleanup

**Warning:** Delete only the DynamoDB table created for Lab 04.

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
Project = DynamoDB-Troubleshooting-Lab04
```

### Step 3 — Inspect Test Items

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Verify that the table contains only disposable test records.

### Step 4 — Delete Table

```bash
aws dynamodb delete-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 5 — Wait for Deletion

```bash
aws dynamodb wait table-not-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 6 — Verify Deletion

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

This is the expected result after intentionally deleting the table.

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| Three Test Orders | Deleted with table |
| IAM Roles | None created |
| Lambda | None created |
| EC2 | None created |
| RDS | None created |
| NAT Gateway | None created |
| Local Source Files | Retained |
| Local Evidence Files | Retained |

---

## 28. Interview Questions and Answers

### Q1. What is a DynamoDB partition key?

A required primary-key component used by DynamoDB to distribute and identify items.

### Q2. What is a sort key?

An optional primary-key component that differentiates items sharing the same partition-key value.

### Q3. What is a composite primary key?

A primary key consisting of both a partition key and a sort key.

### Q4. Can multiple items have the same partition-key value?

Yes, when a sort key is present and the full primary-key combinations remain unique.

### Q5. What happens if GetItem uses an incorrect partition-key value?

If the key structure is valid but no item matches, the response normally has no Item field.

### Q6. Does a wrong partition-key value always return ValidationException?

No. A correctly structured but unmatched key normally results in no returned item.

### Q7. Why does GetItem require both keys in a composite-key table?

Both components together uniquely identify an item.

### Q8. What happens if the sort key is missing?

DynamoDB can return ValidationException.

### Q9. What happens if the partition-key attribute name is incorrect?

The request can fail with ValidationException because it does not match the key schema.

### Q10. What is the difference between GetItem and Query?

GetItem retrieves a specific item by complete primary key. Query retrieves matching items using partition-key equality and optional sort-key conditions.

### Q11. Can Query retrieve all orders for a customer?

Yes, if the customer ID is the partition key.

### Q12. Does Query require the sort key?

No. Query requires the partition key and can optionally use a sort-key condition.

### Q13. What does HASH represent in a DynamoDB key schema?

The partition key.

### Q14. What does RANGE represent?

The sort key.

### Q15. How do you inspect DynamoDB primary-key configuration?

Use DescribeTable to inspect KeySchema and AttributeDefinitions.

### Q16. Is a DynamoDB partition key a security boundary?

No. Authorization must be enforced independently.

### Q17. How can DynamoDB support fine-grained tenant isolation?

Appropriate IAM policies can use condition keys such as `dynamodb:LeadingKeys`, combined with correct authentication and authorization architecture.

### Q18. Why should you avoid Scan for normal customer-order retrieval?

Scan reads across table data and can be inefficient. Query is generally preferable for access patterns supported by the table key design.

### Q19. How can incorrect partition keys affect performance?

Poor partition-key design can concentrate traffic, increase throttling risk, and reduce workload distribution efficiency.

### Q20. How would you explain this lab in a technical interview?

I created an Amazon DynamoDB table using a composite primary key consisting of `customer_id` and `order_id`.

I inserted three sample orders and verified successful GetItem and Query operations.

Next, I intentionally used an incorrect customer ID when retrieving an order.

The request was valid, but DynamoDB returned no matching item.

I investigated the application configuration, queried the expected customer partition, and verified that the order still existed.

After correcting the customer ID, GetItem succeeded.

I then reproduced two additional failures.

The first involved omitting the sort key from GetItem.

The second involved using the wrong partition-key attribute name.

Both requests produced ValidationException because they did not match the table's primary-key schema.

I corrected the requests, verified the expected records, and reviewed DynamoDB data modeling, IAM least privilege, multi-tenant security, and resource cleanup.

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
│   ├── README.md
│   ├── .gitignore
│   │
│   ├── orders.json
│   │
│   ├── wrong-partition-key.json
│   ├── correct-partition-key.json
│   │
│   ├── missing-sort-key.json
│   ├── complete-primary-key.json
│   │
│   ├── wrong-key-name.json
│   ├── fixed-key-name.json
│   │
│   ├── lab04-resources.env
│   │
│   └── evidence/
│       ├── table-description.json
│       ├── initial-items.json
│       ├── healthy-get-item.json
│       ├── wrong-partition-key-response.json
│       ├── correct-customer-query.json
│       ├── recovered-partition-key.json
│       ├── missing-sort-key-output.json
│       ├── missing-sort-key-error.log
│       ├── recovered-sort-key.json
│       ├── wrong-key-name-output.json
│       ├── wrong-key-name-error.log
│       ├── recovered-key-name.json
│       ├── getitem-latency.json
│       └── final-items.json
│
├── 05-provisioned-throughput-exceeded/
├── 06-conditional-check-failed/
├── 07-gsi-query-not-returning-results/
├── 08-dynamodb-streams-not-triggering/
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

The repository structure represents the intended lab files. Generated evidence files are created only after their corresponding commands are executed.

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Full production troubleshooting documentation |
| .gitignore | Excludes generated evidence and local configuration |
| orders.json | Three fabricated order records |
| wrong-partition-key.json | Incorrect customer ID |
| correct-partition-key.json | Corrected customer ID |
| missing-sort-key.json | Invalid incomplete primary key |
| complete-primary-key.json | Correct composite primary key |
| wrong-key-name.json | Incorrect partition-key attribute name |
| fixed-key-name.json | Corrected attribute name |
| lab04-resources.env | Local environment variables |
| table-description.json | Table configuration evidence |
| healthy-get-item.json | Baseline successful retrieval |
| wrong-partition-key-response.json | Empty item result |
| correct-customer-query.json | Query investigation |
| recovered-partition-key.json | Fault 01 recovery |
| missing-sort-key-error.log | Fault 02 error |
| recovered-sort-key.json | Fault 02 recovery |
| wrong-key-name-error.log | Fault 03 error |
| recovered-key-name.json | Fault 03 recovery |
| getitem-latency.json | CloudWatch metrics |
| final-items.json | Final data verification |

### Recommended Public GitHub Structure

```text
04-wrong-partition-key/
├── README.md
├── .gitignore
├── orders.json
├── wrong-partition-key.json
├── correct-partition-key.json
├── missing-sort-key.json
├── complete-primary-key.json
├── wrong-key-name.json
└── fixed-key-name.json
```

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 04
04-wrong-partition-key/evidence/
04-wrong-partition-key/lab04-resources.env

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

Do not publish real customer data, AWS credentials, or unreviewed account-specific evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how incorrect DynamoDB partition-key usage can cause data retrieval problems even when the table and stored records are healthy.

We created a DynamoDB table using a composite primary key consisting of a partition key and sort key.

We inserted three sample orders and verified successful GetItem and Query operations.

Next, we intentionally used an incorrect partition-key value.

DynamoDB processed the request successfully but returned no matching item.

We investigated the customer identifier, compared the requested key against stored records, and retrieved the order using the correct partition-key value.

We then reproduced a missing sort-key problem.

Because GetItem requires the complete primary key, DynamoDB rejected the incomplete request with ValidationException.

After supplying the required sort key, retrieval succeeded.

Finally, we reproduced an error caused by an incorrect partition-key attribute name.

We inspected the table schema, corrected the attribute name, and verified successful recovery.

The lab also demonstrated when to use GetItem versus Query, how to inspect DynamoDB key schemas, and why partition keys should not be treated as authorization controls.

We reviewed CloudWatch monitoring, IAM least privilege, multi-tenant data isolation, cost management, and resource cleanup.

**Key Lesson:** A correct DynamoDB request requires both the right primary-key structure and the right values. An incorrect value may return no item, while an invalid key structure can cause ValidationException.

### Skills Demonstrated

- Amazon DynamoDB.
- Partition-key design.
- Sort-key design.
- Composite primary keys.
- GetItem.
- Query.
- BatchWriteItem.
- Scan.
- DescribeTable.
- DynamoDB key schema investigation.
- Wrong partition-key troubleshooting.
- Missing sort-key troubleshooting.
- Incorrect attribute-name troubleshooting.
- ValidationException investigation.
- AWS CLI v2.
- Linux Bash.
- jq.
- CloudWatch metrics.
- Root cause analysis.
- Data retrieval remediation.
- IAM least privilege.
- Multi-tenant security.
- Recovery verification.
- AWS resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-004 |
| Scenario | DynamoDB Wrong Partition Key |
| Table | ddb-lab04-orders |
| Region | us-east-1 |
| Partition Key | customer_id |
| Sort Key | order_id |
| Key Types | String |
| Billing Mode | PAY_PER_REQUEST |
| Initial Test Orders | Three |
| Healthy GetItem | Successful |
| Healthy Query | Two customer orders |
| Fault 01 | Wrong partition-key value |
| Fault 01 Result | No Item |
| Fault 01 Remediation | Correct customer ID |
| Fault 02 | Missing sort key |
| Fault 02 Result | ValidationException |
| Fault 02 Remediation | Supply complete primary key |
| Fault 03 | Wrong key attribute name |
| Fault 03 Result | ValidationException |
| Fault 03 Remediation | Correct attribute name |
| Final Verification | Three orders present |
| Cleanup | Table deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** DynamoDB troubleshooting requires understanding partition keys, sort keys, primary-key schemas, GetItem, Query, and the difference between valid requests that return no data and invalid requests rejected by DynamoDB.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [DynamoDB Primary Keys](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html)
- [DynamoDB GetItem API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_GetItem.html)
- [DynamoDB Query API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_Query.html)
- [AWS CLI — CreateTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/create-table.html)
- [AWS CLI — GetItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-item.html)
- [AWS CLI — Query](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/query.html)
- [AWS CLI — DescribeTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/describe-table.html)
- [Query Key Condition Expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.KeyConditionExpressions.html)
- [Fine-Grained Access Control](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)
- [DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)