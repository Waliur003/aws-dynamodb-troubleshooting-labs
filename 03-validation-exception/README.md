# Lab 03 — Amazon DynamoDB ValidationException

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve Amazon DynamoDB `ValidationException` errors caused by invalid request structures and primary-key schema mismatches.

In production, applications commonly interact with DynamoDB through AWS Lambda, EC2 instances, containers, APIs, and AWS SDKs.

These applications must construct requests that satisfy DynamoDB's data validation requirements.

If an application sends an item without its required partition key, uses the wrong key data type, or sends an empty primary-key value, DynamoDB can reject the operation.

Example:

```text
An error occurred (ValidationException)
when calling the PutItem operation
```

In this lab, we create a DynamoDB table named `ddb-lab03-orders` in `us-east-1`.

The table uses a String partition key named `order_id` and on-demand billing.

We first insert a correctly structured order and verify successful retrieval.

Next, we intentionally reproduce four production-style validation failures:

1. PutItem with a missing partition key.
2. PutItem with an incorrect partition-key data type.
3. PutItem with an empty partition-key value.
4. GetItem with an incorrect primary-key data type.

We investigate these failures using AWS CLI, Linux Bash, JSON request files, DynamoDB table metadata, and application-level evidence.

We compare each failed request against the table's actual key schema, correct the invalid data, and verify successful DynamoDB operations.

Finally, we confirm that all four expected orders exist, review security considerations, and delete the temporary DynamoDB table.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Verify AWS CLI and Identity
          |
          v
Configure AWS Region
          |
          v
Create DynamoDB Table
          |
          v
Wait for ACTIVE Status
          |
          v
Inspect Primary Key Schema
          |
          v
Insert Valid Order ORD-3001
          |
          v
Verify Healthy GetItem
          |
          v
Fault 01 — Missing Partition Key
          |
          v
ValidationException
          |
          v
Add Required Partition Key
          |
          v
Verify ORD-3002
          |
          v
Fault 02 — Incorrect Key Type
          |
          v
ValidationException
          |
          v
Correct Number to String
          |
          v
Verify ORD-3003
          |
          v
Fault 03 — Empty Partition Key
          |
          v
ValidationException
          |
          v
Provide Nonempty Key
          |
          v
Verify ORD-3004
          |
          v
Fault 04 — Invalid GetItem Key
          |
          v
ValidationException
          |
          v
Correct GetItem Key Type
          |
          v
Verify ORD-3001
          |
          v
Root Cause Analysis
          |
          v
Verify All Four Orders
          |
          v
Security and Cost Review
          |
          v
Clean Up DynamoDB Table
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-003 |
| Lab Name | DynamoDB ValidationException |
| Difficulty | Intermediate |
| Primary Service | Amazon DynamoDB |
| Supporting Services | AWS IAM, STS, CloudWatch |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, jq |
| DynamoDB Table | `ddb-lab03-orders` |
| Partition Key | `order_id` |
| Partition Key Type | String (`S`) |
| Sort Key | None |
| Billing Mode | PAY_PER_REQUEST |
| Primary Operation | PutItem |
| Additional Operation | GetItem |
| Expected Exception | ValidationException |
| Fault 01 | Missing partition key |
| Fault 02 | Incorrect partition-key data type |
| Fault 03 | Empty partition-key value |
| Fault 04 | Invalid GetItem key type |
| Root Cause | Request does not match DynamoDB validation requirements |
| Remediation | Correct request JSON and primary-key attributes |
| Recovery | Successful PutItem and GetItem |
| Test Records | Four valid orders |
| Project Tag | DynamoDB-Troubleshooting-Lab03 |
| Cleanup | Delete temporary DynamoDB table |

### Learning Objectives

- Understand DynamoDB item validation.
- Understand primary-key schemas.
- Understand partition keys.
- Understand DynamoDB attribute types.
- Create tables using AWS CLI.
- Inspect table metadata using DescribeTable.
- Perform PutItem and GetItem operations.
- Reproduce ValidationException.
- Troubleshoot missing primary keys.
- Troubleshoot incorrect key data types.
- Troubleshoot empty key values.
- Troubleshoot incorrect GetItem requests.
- Validate JSON using jq.
- Collect troubleshooting evidence.
- Perform root cause analysis.
- Correct application request structures.
- Verify successful database operations.
- Understand schema validation and data security.
- Apply AWS resource cleanup procedures.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management application that stores customer orders in Amazon DynamoDB.

The application uses a table named:

```text
ddb-lab03-orders
```

The table's primary key is:

```text
order_id
```

The partition key must contain a String value.

A normal application request resembles:

```json
{
  "order_id": "ORD-3001",
  "customer": "Rahim",
  "status": "Processing",
  "amount": 150
}
```

During an application deployment, a developer changes how order IDs are serialized.

Instead of sending a String, the application begins sending the partition key as a Number.

The application starts receiving:

```text
ValidationException
```

The development team suspects a database configuration issue.

However, the Cloud Engineering team discovers that the DynamoDB table is healthy.

The table exists, the Region is correct, and the application has the necessary permissions.

The problem comes from the structure of the request sent to DynamoDB.

The investigation identifies multiple possible validation failures involving primary keys.

The engineer compares the failing requests against the table's key schema and corrects the invalid attributes.

After remediation, the application successfully stores and retrieves orders.

### Incident Symptoms

- PutItem fails with ValidationException.
- GetItem may fail with ValidationException.
- The table remains ACTIVE.
- AWS account and Region are correct.
- IAM authorization is sufficient.
- Request JSON contains invalid primary-key attributes.
- Corrected requests succeed.
- Existing data is preserved.

### Business Impact

DynamoDB validation failures can cause:

- Failed order creation.
- Failed customer transactions.
- Rejected database writes.
- Broken application APIs.
- Data ingestion failures.
- Delayed business workflows.
- Increased application errors.
- Incomplete processing.
- Reduced service reliability.

### Incident Objective

Identify the invalid request attributes, determine which DynamoDB validation requirement was violated, and restore operations without unnecessarily changing table infrastructure.

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
              PutItem Request
                     |
                     v
       order_id = "ORD-3001"
              Type = String
                     |
                     v
              Amazon DynamoDB
                     |
                     v
          Primary Key Validation
                     |
                     v
               Request Valid
                     |
                     v
             Item Successfully
                  Stored
                     |
                     v
               GetItem
                     |
                     v
              Order Retrieved
```

### Broken Architecture

```text
             Order Application
                     |
                     v
              PutItem Request
                     |
             +-------+-------+
             |               |
             v               v
       Missing Key       Wrong Key Type
             |               |
             +-------+-------+
                     |
                     v
              DynamoDB API
                     |
                     v
          Primary Key Validation
                     |
                     v
            ValidationException
                     |
                     v
               Write Rejected
```

### Recovered Architecture

```text
             Order Application
                     |
                     v
           Validated Request JSON
                     |
                     v
          order_id = String Value
                     |
                     v
             Amazon DynamoDB
                     |
                     v
             Validation Success
                     |
                     v
               PutItem
                     |
                     v
              Item Stored
                     |
                     v
               GetItem
                     |
                     v
              HTTP/Application
               Operation Success
```

### AWS Components

| Component | Purpose |
|---|---|
| DynamoDB | Stores order data |
| DynamoDB Table | Contains order items |
| Partition Key | Uniquely identifies an item |
| PutItem | Creates or replaces an item |
| GetItem | Retrieves an item |
| DescribeTable | Provides table schema |
| AWS STS | Verifies AWS identity |
| IAM | Authorizes DynamoDB operations |
| AWS CLI | Executes database requests |
| Bash | Manages configuration and files |
| jq | Validates and inspects JSON |
| CloudWatch | Provides operational metrics |

---

## 4. Understanding DynamoDB Data Types

Amazon DynamoDB supports multiple attribute types.

### Common Attribute Types

| Type | Meaning | Example |
|---|---|---|
| S | String | `{"S":"ORD-3001"}` |
| N | Number | `{"N":"150"}` |
| B | Binary | Binary data |
| BOOL | Boolean | `{"BOOL":true}` |
| NULL | Null | `{"NULL":true}` |
| L | List | `{"L":[]}` |
| M | Map | `{"M":{}}` |
| SS | String Set | Collection of strings |
| NS | Number Set | Collection of numbers |
| BS | Binary Set | Collection of binary values |

### Example DynamoDB Item

```json
{
  "order_id": {"S": "ORD-3001"},
  "customer": {"S": "Rahim"},
  "status": {"S": "Processing"},
  "amount": {"N": "150"}
}
```

### Understanding String and Number

A String attribute uses:

```json
{"S":"ORD-3001"}
```

A Number attribute uses:

```json
{"N":"150"}
```

Although the numeric value is written inside quotation marks in DynamoDB's low-level API format, its attribute type is Number.

### Important Concept

DynamoDB does not enforce a fixed schema for most non-key attributes.

For example, different items can contain different optional attributes.

However, primary-key attributes must satisfy the table's key schema.

For Lab 03:

```text
Partition Key: order_id
Required Type: String
Required Value: Nonempty
```

---

## 5. Understanding ValidationException

`ValidationException` occurs when a request violates a DynamoDB validation requirement.

Common examples include:

- Missing required primary-key attributes.
- Incorrect primary-key types.
- Empty String or Binary key values.
- Invalid request expressions.
- Incorrect key structures.
- Invalid request parameters.

### Example Error

```text
An error occurred (ValidationException)
when calling the PutItem operation
```

### Request Validation Flow

```text
Application Constructs Request
               |
               v
         AWS CLI / SDK
               |
               v
          DynamoDB API
               |
               v
       Validate Request
               |
       +-------+-------+
       |               |
       v               v
     Valid           Invalid
       |               |
       v               v
  Operation       ValidationException
  Accepted              |
                        v
                  Request Rejected
```

### ValidationException vs. Other Errors

| Exception | Main Investigation |
|---|---|
| ResourceNotFoundException | Table, index, Region, account |
| AccessDeniedException | IAM authorization |
| ValidationException | Request structure and schema |
| ConditionalCheckFailedException | Failed condition |
| ProvisionedThroughputExceededException | Throughput and capacity |

A validation error should not automatically be treated as an IAM problem.

---

## 6. Prerequisites and Safety

### Requirements

- AWS account.
- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- jq.
- DynamoDB create/read/write/delete permissions.
- AWS STS access.

### Relevant IAM Permissions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:ListTables
dynamodb:ListTagsOfResource
dynamodb:PutItem
dynamodb:GetItem
dynamodb:Scan
dynamodb:DeleteTable
```

These are required actions for the exercise, not a complete IAM policy.

### Safety Rules

- Use a dedicated table.
- Never use production customer data.
- Use fabricated orders.
- Do not change production table schemas.
- Verify the AWS account and Region.
- Keep data small.
- Use bounded test requests.
- Do not publish credentials.
- Verify ownership before deletion.
- Delete the temporary table after the lab.

### Resource Tag

```text
Project = DynamoDB-Troubleshooting-Lab03
```

---

## 7. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 03-validation-exception

cd 03-validation-exception
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

export TABLE_NAME="ddb-lab03-orders"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab03"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"
```

### Step 4 — Verify Variables

```bash
echo "$AWS_REGION"
echo "$TABLE_NAME"
echo "$TABLE_ARN"
```

### Step 5 — Create Evidence Directory

```bash
mkdir -p evidence
```

### Step 6 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
evidence/
lab03-resources.env

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

## 8. Create DynamoDB Table

### Step 1 — Check Existing Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

If the table does not exist, the expected error is:

```text
ResourceNotFoundException
```

If it already exists, verify ownership before proceeding.

### Step 2 — Create Table

```bash
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=order_id,AttributeType=S \
  --key-schema \
    AttributeName=order_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 3 — Wait for ACTIVE Status

```bash
aws dynamodb wait table-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 4 — Verify Table

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

Expected:

```text
TableName = ddb-lab03-orders
TableStatus = ACTIVE
```

### Step 5 — Save Metadata

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/table-description.json
```

---

## 9. Inspect Primary-Key Schema

### Step 1 — Retrieve Key Schema

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.KeySchema' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
[
  {
    "AttributeName": "order_id",
    "KeyType": "HASH"
  }
]
```

### Step 2 — Inspect Attribute Definitions

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.AttributeDefinitions' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
[
  {
    "AttributeName": "order_id",
    "AttributeType": "S"
  }
]
```

### Step 3 — Save Schema Evidence

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    KeySchema:KeySchema,
    AttributeDefinitions:AttributeDefinitions
  }' \
  --output json \
  --region "$AWS_REGION" \
  > evidence/key-schema.json
```

### Schema Investigation

| Property | Requirement |
|---|---|
| Key Name | order_id |
| Key Type | String |
| Key Role | Partition Key |
| Required | Yes |
| Empty String Allowed | No |
| Sort Key | None |

This schema is the reference for investigating every failure.

---

## 10. Establish Healthy Baseline

### Step 1 — Insert Valid Order

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-3001"},
    "customer": {"S": "Rahim"},
    "status": {"S": "Processing"},
    "amount": {"N": "150"}
  }' \
  --region "$AWS_REGION"
```

Expected: successful PutItem.

### Step 2 — Retrieve Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected response includes:

```json
{
  "Item": {
    "order_id": {"S": "ORD-3001"},
    "customer": {"S": "Rahim"},
    "status": {"S": "Processing"},
    "amount": {"N": "150"}
  }
}
```

Attribute ordering can vary.

### Step 3 — Save Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/healthy-get-item.json
```

### Step 4 — Validate

```bash
jq -e '.Item.order_id.S == "ORD-3001"' \
  evidence/healthy-get-item.json
```

Expected:

```text
true
```

### Baseline Findings

| Component | Expected State |
|---|---|
| Table | ACTIVE |
| Table Schema | Correct |
| AWS Region | us-east-1 |
| PutItem | Successful |
| GetItem | Successful |
| Key Type | String |

---

## 11. Fault Injection 01 — Missing Partition Key

### Production Problem

The application constructs an order without the required `order_id` attribute.

### Step 1 — Create Invalid Item

```bash
cat > invalid-missing-key.json <<'EOF'
{
  "customer": {"S": "Karim"},
  "status": {"S": "Pending"},
  "amount": {"N": "200"}
}
EOF
```

### Step 2 — Inspect JSON

```bash
jq . invalid-missing-key.json
```

The partition key is missing.

### Step 3 — Attempt PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://invalid-missing-key.json \
  --region "$AWS_REGION"
```

Expected:

```text
ValidationException
```

The error normally identifies the missing primary-key attribute.

### Step 4 — Capture Failure

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://invalid-missing-key.json \
  --region "$AWS_REGION" \
  > evidence/fault01-output.json \
  2> evidence/fault01-error.log

echo "Exit code: $?"
```

Expected: nonzero exit code.

### Step 5 — Inspect Error

```bash
cat evidence/fault01-error.log
```

### Root Cause

The item lacks the required partition key.

DynamoDB cannot store an item in this table without `order_id`.

---

## 12. Remediation 01 — Add Required Partition Key

### Step 1 — Create Corrected Item

```bash
cat > fixed-missing-key.json <<'EOF'
{
  "order_id": {"S": "ORD-3002"},
  "customer": {"S": "Karim"},
  "status": {"S": "Pending"},
  "amount": {"N": "200"}
}
EOF
```

### Step 2 — Validate JSON

```bash
jq . fixed-missing-key.json
```

### Step 3 — Retry PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://fixed-missing-key.json \
  --region "$AWS_REGION"
```

Expected: success.

### Step 4 — Verify GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3002"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 5 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3002"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/fault01-recovered.json
```

**Fault 01 is resolved when ORD-3002 can be retrieved successfully.**

---

## 13. Fault Injection 02 — Incorrect Partition-Key Type

### Production Problem

The DynamoDB table requires a String partition key.

The application incorrectly sends a Number value.

### Step 1 — Create Invalid Item

```bash
cat > invalid-key-type.json <<'EOF'
{
  "order_id": {"N": "3003"},
  "customer": {"S": "Hasan"},
  "status": {"S": "Processing"},
  "amount": {"N": "300"}
}
EOF
```

### Step 2 — Verify Incorrect Type

```bash
jq '.order_id' invalid-key-type.json
```

Expected:

```json
{
  "N": "3003"
}
```

### Step 3 — Attempt PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://invalid-key-type.json \
  --region "$AWS_REGION"
```

Expected:

```text
ValidationException
```

### Step 4 — Capture Evidence

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://invalid-key-type.json \
  --region "$AWS_REGION" \
  > evidence/fault02-output.json \
  2> evidence/fault02-error.log

echo "Exit code: $?"
```

### Step 5 — Inspect Error

```bash
cat evidence/fault02-error.log
```

### Root Cause

The request uses `N` for the partition key, while the table requires `S`.

### Schema Comparison

| Property | Table Requirement | Invalid Request |
|---|---|---|
| Attribute | order_id | order_id |
| Type | String | Number |
| Value | String identifier | Numeric value |
| Result | Valid | ValidationException |

---

## 14. Remediation 02 — Correct Key Data Type

### Step 1 — Create Corrected Item

```bash
cat > fixed-key-type.json <<'EOF'
{
  "order_id": {"S": "ORD-3003"},
  "customer": {"S": "Hasan"},
  "status": {"S": "Processing"},
  "amount": {"N": "300"}
}
EOF
```

### Step 2 — Retry PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://fixed-key-type.json \
  --region "$AWS_REGION"
```

### Step 3 — Verify Item

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3003"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 4 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3003"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/fault02-recovered.json
```

**Fault 02 is resolved when ORD-3003 is stored and retrieved using a String key.**

---

## 15. Fault Injection 03 — Empty Partition-Key Value

### Production Problem

The application passes an empty String as the partition key.

### Step 1 — Create Invalid Item

```bash
cat > invalid-empty-key.json <<'EOF'
{
  "order_id": {"S": ""},
  "customer": {"S": "Nadia"},
  "status": {"S": "Pending"}
}
EOF
```

### Step 2 — Inspect Key

```bash
jq '.order_id' invalid-empty-key.json
```

Expected:

```json
{
  "S": ""
}
```

### Step 3 — Attempt PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://invalid-empty-key.json \
  --region "$AWS_REGION"
```

Expected:

```text
ValidationException
```

### Step 4 — Capture Error

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://invalid-empty-key.json \
  --region "$AWS_REGION" \
  > evidence/fault03-output.json \
  2> evidence/fault03-error.log

echo "Exit code: $?"
```

### Step 5 — Inspect Error

```bash
cat evidence/fault03-error.log
```

### Root Cause

The primary-key attribute contains an empty String.

DynamoDB does not permit empty String or Binary values for table or index key attributes.

Empty Strings may be permitted for certain non-key attributes.

---

## 16. Remediation 03 — Provide Nonempty Key

### Step 1 — Create Corrected Item

```bash
cat > fixed-empty-key.json <<'EOF'
{
  "order_id": {"S": "ORD-3004"},
  "customer": {"S": "Nadia"},
  "status": {"S": "Pending"}
}
EOF
```

### Step 2 — Retry PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://fixed-empty-key.json \
  --region "$AWS_REGION"
```

### Step 3 — Verify Item

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3004"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 4 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3004"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/fault03-recovered.json
```

**Fault 03 is resolved when ORD-3004 is successfully stored and retrieved.**

---

## 17. Fault Injection 04 — Invalid GetItem Key Type

### Production Problem

The application uses a Number key to retrieve an item from a table that requires a String key.

### Step 1 — Send Invalid GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"N":"3001"}}' \
  --region "$AWS_REGION"
```

Expected:

```text
ValidationException
```

A common error message is:

```text
The provided key element does not match the schema
```

### Step 2 — Capture Failure

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"N":"3001"}}' \
  --region "$AWS_REGION" \
  > evidence/fault04-output.json \
  2> evidence/fault04-error.log

echo "Exit code: $?"
```

### Step 3 — Inspect Error

```bash
cat evidence/fault04-error.log
```

### Step 4 — Verify Table Schema

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    KeySchema:KeySchema,
    AttributeDefinitions:AttributeDefinitions
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Root Cause

The GetItem request does not match the primary-key data type required by the table.

---

## 18. Remediation 04 — Correct GetItem Key

### Step 1 — Use Correct String Key

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 2 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-3001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-get-item.json
```

### Step 3 — Validate

```bash
jq -e '.Item.order_id.S == "ORD-3001"' \
  evidence/recovered-get-item.json
```

Expected:

```text
true
```

### Recovery Comparison

| Property | Broken | Recovered |
|---|---|---|
| GetItem key | Number | String |
| Key format | `{"N":"3001"}` | `{"S":"ORD-3001"}` |
| Operation | ValidationException | Success |
| Table configuration | Unchanged | Unchanged |

---

## 19. Production Investigation — Compare Request and Schema

### Step 1 — Confirm AWS Account

```bash
aws sts get-caller-identity
```

### Step 2 — Confirm Region

```bash
echo "$AWS_REGION"
```

Expected:

```text
us-east-1
```

### Step 3 — Inspect Table Status

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    Name:TableName,
    Status:TableStatus
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Key Schema

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.KeySchema' \
  --output json \
  --region "$AWS_REGION"
```

### Step 5 — Inspect Key Attribute Type

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.AttributeDefinitions' \
  --output json \
  --region "$AWS_REGION"
```

### Step 6 — Compare Failed Requests

```bash
jq . invalid-missing-key.json
jq . invalid-key-type.json
jq . invalid-empty-key.json
```

### Investigation Checklist

| Check | Expected |
|---|---|
| Table exists | Yes |
| Table status | ACTIVE |
| Partition key | order_id |
| Partition-key type | S |
| Partition-key value | Nonempty |
| Request JSON | Valid DynamoDB structure |
| IAM permissions | Sufficient |
| AWS Region | Correct |

### Important Finding

The issue is not that DynamoDB is unavailable.

The issue is that the application-generated request violates a database validation requirement.

---

## 20. Root Cause Analysis

### Root Cause Summary

Four invalid requests were generated using incorrect primary-key attributes.

### Fault Comparison

| Fault | Operation | Invalid Condition | Root Cause |
|---|---|---|---|
| 01 | PutItem | `order_id` missing | Required key absent |
| 02 | PutItem | `order_id` uses N | Key type mismatch |
| 03 | PutItem | Empty `order_id` | Invalid key value |
| 04 | GetItem | Key uses N | Incorrect GetItem schema |

### Five Whys — Incorrect Key Type

**Why 1 — Why did PutItem fail?**

DynamoDB returned ValidationException.

**Why 2 — Why was the request rejected?**

The partition-key type did not match the table schema.

**Why 3 — Why was the type incorrect?**

The application serialized the order ID as a Number instead of a String.

**Why 4 — Why wasn't the error detected earlier?**

The simulated deployment did not validate request data against the expected key schema.

**Why 5 — How can the incident be prevented?**

Implement input validation, consistent serialization, integration tests, and structured error monitoring.

### Root Cause Diagram

```text
Application Deployment
          |
          v
Incorrect Request Serialization
          |
          v
Invalid DynamoDB Item / Key
          |
          v
DynamoDB API Validation
          |
          v
Schema Requirement Violated
          |
          v
ValidationException
          |
          v
Application Operation Fails
```

### Root Cause Conclusion

The application request structure must be corrected.

Changing the DynamoDB table's primary-key schema is not an appropriate quick fix for an application serialization error.

---

## 21. Verify Complete Recovery

### Step 1 — Retrieve All Lab Items

Because this is a small disposable table:

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 2 — Save Final Evidence

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/final-items.json
```

### Step 3 — Validate Four Order IDs

```bash
jq -e '
  ([.Items[].order_id.S] | sort) ==
  ["ORD-3001","ORD-3002","ORD-3003","ORD-3004"]
' evidence/final-items.json
```

Expected:

```text
true
```

### Step 4 — Verify Table Status

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

### Final Verification Table

| Order | Source | Expected |
|---|---|---|
| ORD-3001 | Initial healthy baseline | Present |
| ORD-3002 | Fault 01 remediation | Present |
| ORD-3003 | Fault 02 remediation | Present |
| ORD-3004 | Fault 03 remediation | Present |
| ORD-3001 GetItem | Fault 04 remediation | Successful |

The scan verification assumes only these four items are stored in the lab table.

### Recovery Criteria

The incident is considered resolved when all four items are present, the corrected requests succeed, and the table remains ACTIVE.

---

## 22. CloudWatch and Logging Investigation

### Monitoring Context

DynamoDB provides CloudWatch metrics that support operational monitoring.

Relevant examples include:

| Metric | Purpose |
|---|---|
| SuccessfulRequestLatency | Latency for successful DynamoDB requests |
| ConsumedReadCapacityUnits | Read capacity consumption |
| ConsumedWriteCapacityUnits | Write capacity consumption |
| UserErrors | Aggregated client-side errors |
| SystemErrors | Service-side errors |

### Step 1 — Configure Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect Successful Request Latency

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name SuccessfulRequestLatency \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=Operation,Value=PutItem \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --region "$AWS_REGION"
```

### Step 3 — Inspect UserErrors

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

The UserErrors metric can provide broad service-level context. It is not a substitute for the exact validation exception captured from the failed request.

### Step 4 — Save Metric Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name SuccessfulRequestLatency \
  --dimensions \
    Name=TableName,Value="$TABLE_NAME" \
    Name=Operation,Value=PutItem \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --region "$AWS_REGION" \
  > evidence/putitem-latency.json
```

### Monitoring Lessons

- Capture exact API exceptions.
- Log failed operation names.
- Log safe request metadata.
- Avoid logging sensitive item contents.
- Monitor error-rate changes after deployments.
- Correlate application events with DynamoDB metrics.

Metrics may not be immediately available because of publication delay.

---

## 23. Additional Production Troubleshooting Scenarios

### Scenario 1 — Missing Sort Key

A table uses a composite primary key, but the request supplies only the partition key.

**Investigation:** Inspect KeySchema and verify both key attributes.

**Remediation:** Supply the required sort key.

### Scenario 2 — Incorrect Attribute Name

The application uses:

```text
orderId
```

instead of:

```text
order_id
```

**Investigation:** Compare application JSON against the actual key schema.

**Remediation:** Correct the attribute name.

### Scenario 3 — Invalid ConditionExpression

The application provides malformed expression syntax.

**Investigation:** Inspect the expression and placeholder values.

**Remediation:** Correct the expression.

### Scenario 4 — Incorrect Number Representation

A low-level DynamoDB request sends an improperly formatted Number attribute.

**Investigation:** Verify DynamoDB AttributeValue syntax.

**Remediation:** Supply a valid Number string.

### Scenario 5 — Incorrect Primary-Key Assumption

An application expects one key attribute but the actual table has both a partition key and sort key.

**Investigation:** Use DescribeTable.

**Remediation:** Align application requests with the table's schema.

### Scenario 6 — Missing Item vs. Invalid Key

A request with a correctly structured but nonexistent key normally returns no Item.

A request with an incorrectly typed key can produce ValidationException.

### Scenario Comparison

| Symptom | Investigation |
|---|---|
| Missing key | Required key attributes |
| Wrong key type | AttributeDefinitions |
| Empty key | Key value validation |
| Invalid expression | Expression syntax |
| Item not returned | Correct key but no matching data |
| ResourceNotFoundException | Table or index identity |
| AccessDeniedException | Authorization |

---

## 24. Cloud Security Engineering Considerations

### Validate Application Input

Applications should validate incoming data before constructing DynamoDB requests.

For this lab:

```text
order_id must be a nonempty String
```

### Prevent Invalid Identifiers

Reject missing, empty, or incorrectly typed IDs before database operations.

### Apply IAM Least Privilege

Do not change database permissions to fix a request validation problem.

### Protect Sensitive Information

Avoid writing customer details or secrets into troubleshooting logs.

### Use Structured Error Logging

Capture the exception type and affected operation without exposing sensitive payload contents.

### Prevent Accidental Overwrites

PutItem can replace an existing item that has the same primary key.

For operations where overwriting is unsafe, use appropriate conditional expressions.

### Secure CI/CD Workflows

Include automated tests that verify database request compatibility with the deployed schema.

### Security Principle

**Validate untrusted application inputs and preserve a consistent data contract before making DynamoDB API requests.**

---

## 25. Cost Management

### Potential Charges

| AWS Service | Cost Consideration |
|---|---|
| DynamoDB On-Demand | Read and write requests |
| DynamoDB Storage | Stored item size |
| CloudWatch | Applicable metric and monitoring charges |
| AWS CLI | No separate CLI fee |
| IAM | No separate standard IAM role fee |

### Lab Cost Controls

- Use four small test items.
- Use on-demand billing.
- Limit failed requests.
- Avoid large production table scans.
- Do not provision EC2, RDS, or NAT Gateway resources.
- Delete the temporary table after testing.

Actual costs depend on pricing, account eligibility, and usage.

---

## 26. Save Environment Configuration

### Step 1 — Create `lab03-resources.env`

```bash
cat > lab03-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab03-resources.env
```

### Step 2 — Load Variables Later

```bash
source lab03-resources.env
```

### Step 3 — Verify Resource Configuration

```bash
echo "$TABLE_NAME"
echo "$TABLE_ARN"
echo "$AWS_REGION"
```

### Step 4 — Verify Table Tags

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab03
```

---

## 27. AWS Resource Cleanup

**Warning:** Delete only the disposable DynamoDB table created for this lab.

### Step 1 — Confirm Table Identity

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    Name:TableName,
    ARN:TableArn,
    Status:TableStatus
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Step 2 — Verify Project Tag

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

### Step 3 — Review Test Items

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Confirm that the table contains only disposable test records.

### Step 4 — Delete DynamoDB Table

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

This error is expected after intentionally deleting the table.

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| Test Orders | Deleted with table |
| IAM Roles | None created |
| EC2 | None created |
| Lambda | None created |
| RDS | None created |
| NAT Gateway | None created |
| Local JSON Files | Retained |
| Local Evidence | Retained |

---

## 28. Interview Questions and Answers

### Q1. What causes DynamoDB ValidationException?

It occurs when a request violates DynamoDB validation rules, such as supplying missing or incorrectly typed primary-key attributes.

### Q2. What is a partition key?

A required primary-key component used by DynamoDB to identify and distribute items.

### Q3. Must a partition key be present in PutItem?

Yes. Every item must include the required primary-key attributes.

### Q4. Can DynamoDB accept a Number when the key schema requires String?

No. Primary-key attribute types must match the schema.

### Q5. Can a partition key contain an empty String?

No. Empty String values are not permitted for table or index key attributes.

### Q6. Can non-key String attributes contain empty values?

Yes, where supported by DynamoDB's attribute constraints.

### Q7. How do you investigate a key schema mismatch?

Use DescribeTable to inspect KeySchema and AttributeDefinitions.

### Q8. What is the difference between PutItem and GetItem?

PutItem writes or replaces an item. GetItem retrieves an item using its primary key.

### Q9. What is the difference between ValidationException and AccessDeniedException?

ValidationException concerns request validity. AccessDeniedException concerns authorization.

### Q10. What happens when GetItem requests a nonexistent item with a valid key?

The operation can succeed without returning an Item element.

### Q11. What happens when GetItem uses the wrong key type?

DynamoDB can return ValidationException.

### Q12. What does `S` mean in DynamoDB JSON?

String.

### Q13. What does `N` mean in DynamoDB JSON?

Number.

### Q14. Why does DynamoDB represent Number values as strings in its low-level API?

It uses string-encoded numeric representations to preserve numeric precision during communication.

### Q15. Is DynamoDB completely schemaless?

Non-key attributes are flexible, but the table's primary-key schema is enforced.

### Q16. Should an engineer change IAM permissions to fix ValidationException?

No. First correct the invalid request.

### Q17. How can developers prevent these incidents?

Use input validation, consistent data serialization, integration tests, and schema-aware application code.

### Q18. How would you explain this lab in an interview?

I created a DynamoDB table using AWS CLI with a String partition key named `order_id`.

I inserted an initial order and verified successful PutItem and GetItem operations.

Next, I intentionally created four validation failures.

First, I submitted an item without the required partition key.

Second, I submitted an item using a Number value where the table required a String.

Third, I used an empty String as the primary-key value.

Fourth, I attempted GetItem using an incorrectly typed key.

DynamoDB rejected the invalid operations with ValidationException.

I investigated the errors by examining the table schema using DescribeTable and comparing the failed request JSON files against KeySchema and AttributeDefinitions.

I corrected each request and verified successful database operations.

Finally, I confirmed the intended orders were stored, reviewed secure input validation, and cleaned up the temporary table.

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
│   ├── README.md
│   ├── .gitignore
│   │
│   ├── invalid-missing-key.json
│   ├── fixed-missing-key.json
│   │
│   ├── invalid-key-type.json
│   ├── fixed-key-type.json
│   │
│   ├── invalid-empty-key.json
│   ├── fixed-empty-key.json
│   │
│   ├── lab03-resources.env
│   │
│   └── evidence/
│       ├── table-description.json
│       ├── key-schema.json
│       ├── healthy-get-item.json
│       │
│       ├── fault01-output.json
│       ├── fault01-error.log
│       ├── fault01-recovered.json
│       │
│       ├── fault02-output.json
│       ├── fault02-error.log
│       ├── fault02-recovered.json
│       │
│       ├── fault03-output.json
│       ├── fault03-error.log
│       ├── fault03-recovered.json
│       │
│       ├── fault04-output.json
│       ├── fault04-error.log
│       ├── recovered-get-item.json
│       │
│       ├── final-items.json
│       └── putitem-latency.json
│
├── 04-wrong-partition-key/
├── 05-provisioned-throughput-exceeded/
├── 06-conditional-check-failed/
├── 07-gsi-query-not-returning-results/
├── 08-dynamodb-streams-not-triggering/
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Production troubleshooting documentation |
| .gitignore | Excludes generated evidence and local configuration |
| invalid-missing-key.json | Reproduces missing partition key |
| fixed-missing-key.json | Corrected item with required key |
| invalid-key-type.json | Reproduces incorrect key data type |
| fixed-key-type.json | Corrected String partition key |
| invalid-empty-key.json | Reproduces empty key failure |
| fixed-empty-key.json | Corrected nonempty key |
| lab03-resources.env | Local resource variables |
| table-description.json | DynamoDB table metadata |
| key-schema.json | Key schema evidence |
| healthy-get-item.json | Initial successful retrieval |
| fault01–fault04 logs | Error evidence |
| fault01–fault03 recovered JSON | Successful remediation evidence |
| recovered-get-item.json | Final GetItem remediation |
| final-items.json | Four-order verification |
| putitem-latency.json | CloudWatch latency evidence |

The repository structure includes expected local files; evidence files are generated only when the corresponding commands have been run.

### Recommended Public GitHub Structure

```text
03-validation-exception/
├── README.md
├── .gitignore
├── invalid-missing-key.json
├── fixed-missing-key.json
├── invalid-key-type.json
├── fixed-key-type.json
├── invalid-empty-key.json
└── fixed-empty-key.json
```

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 03
03-validation-exception/evidence/
03-validation-exception/lab03-resources.env

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

# Generated logs
*.log
```

Do not publish real customer data, AWS credentials, or unreviewed account-specific evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how DynamoDB rejects requests that violate its validation requirements.

We created a DynamoDB table with a String partition key and inserted a valid order.

We then reproduced four different validation failures.

The first failure involved a missing partition key.

The second involved an incorrect primary-key type.

The third involved an empty partition-key value.

The fourth involved an incorrect GetItem key type.

We investigated each error using AWS CLI, request JSON, DynamoDB table metadata, and the key schema.

The investigations demonstrated that primary-key attribute names, types, and values must match the table's requirements.

We corrected the requests and successfully stored or retrieved the intended orders.

We verified the final table contents and reviewed application input validation, IAM least privilege, operational monitoring, and resource cleanup.

**Key Lesson:** A DynamoDB ValidationException should first be investigated by comparing the request against the table's primary-key schema and API validation requirements. Healthy database infrastructure does not need to be rebuilt to fix incorrectly structured requests.

### Skills Demonstrated

- Amazon DynamoDB.
- DynamoDB primary-key design.
- Partition-key troubleshooting.
- DynamoDB attribute types.
- PutItem.
- GetItem.
- Scan.
- DescribeTable.
- ValidationException investigation.
- Missing-key remediation.
- Incorrect-type remediation.
- Empty-key remediation.
- JSON validation.
- AWS CLI v2.
- Linux Bash.
- jq.
- CloudWatch metrics.
- Root cause analysis.
- Application data validation.
- Secure remediation.
- Recovery verification.
- AWS cost management.
- Resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-003 |
| Scenario | DynamoDB ValidationException |
| Table | ddb-lab03-orders |
| Region | us-east-1 |
| Partition Key | order_id |
| Partition-Key Type | String |
| Billing Mode | PAY_PER_REQUEST |
| Initial Healthy PutItem | Successful |
| Fault 01 | Missing partition key |
| Fault 01 Error | ValidationException |
| Fault 01 Remediation | Add required key |
| Fault 02 | Incorrect key data type |
| Fault 02 Error | ValidationException |
| Fault 02 Remediation | Use String key |
| Fault 03 | Empty partition key |
| Fault 03 Error | ValidationException |
| Fault 03 Remediation | Use nonempty key |
| Fault 04 | Invalid GetItem key |
| Fault 04 Error | ValidationException |
| Fault 04 Remediation | Match key schema |
| Final Test Records | Four valid orders |
| Recovery | Successful PutItem and GetItem |
| Cleanup | DynamoDB table deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** DynamoDB data validation troubleshooting requires understanding primary-key requirements, attribute data types, request serialization, and the difference between invalid requests and missing or unauthorized resources.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [DynamoDB PutItem API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_PutItem.html)
- [DynamoDB GetItem API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_GetItem.html)
- [AWS CLI — PutItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/put-item.html)
- [AWS CLI — GetItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-item.html)
- [AWS CLI — DescribeTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/describe-table.html)
- [Working With DynamoDB Items](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html)
- [DynamoDB Data Types and Naming Rules](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html)
- [DynamoDB Constraints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html)
- [DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)