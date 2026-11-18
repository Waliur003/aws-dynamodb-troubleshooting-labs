# Lab 01 — Amazon DynamoDB Table Not Found

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an Amazon DynamoDB `ResourceNotFoundException` caused by an incorrect table name or AWS Region.

In production, applications frequently access DynamoDB through AWS SDKs, AWS Lambda functions, containers, EC2 instances, and other services.

These applications normally reference DynamoDB tables using configuration values such as:

```bash
DYNAMODB_TABLE=ddb-lab01-orders
AWS_REGION=us-east-1
```

If an application references a table that does not exist in the selected AWS account and Region, DynamoDB can reject the operation.

Example:

```text
An error occurred (ResourceNotFoundException)
when calling the GetItem operation:
Requested resource not found
```

In this lab, we create a DynamoDB table named `ddb-lab01-orders` using on-demand capacity.

The table stores two fabricated customer orders and uses `order_id` as its partition key.

We first confirm that the table is `ACTIVE`, insert the items, and retrieve an order successfully.

We then introduce two production-style configuration failures.

**Fault 1 — Incorrect Table Name**

The application requests `ddb-lab01-order` instead of `ddb-lab01-orders`.

**Fault 2 — Incorrect AWS Region**

The application requests the correct table name in `us-west-2`, while the actual table is located in `us-east-1`.

Both scenarios can generate `ResourceNotFoundException`.

We investigate using AWS CLI, AWS STS, table inventory, table metadata, environment variables, and saved troubleshooting evidence.

We remediate each failure by correcting the application configuration.

Finally, we verify successful data retrieval, review security and cost considerations, and remove the temporary DynamoDB table.

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
Insert Two Test Orders
          |
          v
Verify Healthy GetItem
          |
          v
Inject Incorrect Table Name
          |
          v
ResourceNotFoundException
          |
          v
Investigate Table Inventory
          |
          v
Identify Incorrect Configuration
          |
          v
Restore Correct Table Name
          |
          v
Verify GetItem Recovery
          |
          v
Inject Incorrect AWS Region
          |
          v
ResourceNotFoundException
          |
          v
Compare Regional Tables
          |
          v
Inspect Table ARN
          |
          v
Restore Correct Region
          |
          v
Verify GetItem Recovery
          |
          v
Review CloudWatch and Security
          |
          v
Root Cause Analysis
          |
          v
Verify Both Test Orders
          |
          v
Clean Up Lab Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-001 |
| Lab Name | DynamoDB Table Not Found |
| Difficulty | Beginner |
| Primary Service | Amazon DynamoDB |
| Supporting Services | AWS STS, IAM, CloudWatch |
| AWS Region | `us-east-1` |
| Fault Injection Region | `us-west-2` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, jq |
| Table Name | `ddb-lab01-orders` |
| Incorrect Table Name | `ddb-lab01-order` |
| Partition Key | `order_id` |
| Partition Key Type | String |
| Sort Key | None |
| Billing Mode | PAY_PER_REQUEST |
| Test Items | 2 |
| Healthy Operation | GetItem |
| Main Exception | ResourceNotFoundException |
| Fault 1 | Incorrect table name |
| Fault 2 | Incorrect AWS Region |
| Remediation | Correct resource references |
| Recovery Verification | Successful GetItem |
| Data Type | Fabricated order data |
| Cleanup | Delete temporary DynamoDB table |

### Learning Objectives

- Understand DynamoDB tables and items.
- Understand partition keys.
- Create DynamoDB tables using AWS CLI.
- Understand on-demand capacity.
- Insert records using BatchWriteItem.
- Retrieve items using GetItem.
- Understand DynamoDB resource identification.
- Understand `ResourceNotFoundException`.
- Troubleshoot incorrect table names.
- Troubleshoot incorrect AWS Regions.
- Verify AWS account identity.
- Inspect DynamoDB table metadata.
- Understand DynamoDB table states.
- Distinguish missing tables from missing items.
- Investigate application environment variables.
- Collect incident evidence.
- Perform root cause analysis.
- Apply configuration-based remediation.
- Verify successful recovery.
- Understand DynamoDB security practices.
- Perform safe resource cleanup.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management platform that stores order information in Amazon DynamoDB.

The application uses the table:

```text
ddb-lab01-orders
```

The production environment is configured to access DynamoDB in:

```text
us-east-1
```

The table contains customer orders identified by a unique `order_id`.

A normal application request retrieves an order using the DynamoDB GetItem operation.

During an application deployment, an engineer accidentally changes the table configuration.

Original:

```bash
DYNAMODB_TABLE=ddb-lab01-orders
```

Incorrect:

```bash
DYNAMODB_TABLE=ddb-lab01-order
```

The application starts failing when retrieving orders.

The error resembles:

```text
ResourceNotFoundException:
Requested resource not found
```

The development team reports that DynamoDB is unavailable.

However, the Cloud Engineering team checks the AWS account and discovers that the actual table still exists and is healthy.

The problem is not a DynamoDB service outage.

The problem is an incorrect table reference.

After correcting the table name, the application successfully retrieves orders.

A second scenario demonstrates the same error when an application uses the wrong AWS Region.

### Incident Symptoms

- DynamoDB GetItem fails.
- `ResourceNotFoundException` appears.
- Application requests cannot retrieve order information.
- The actual DynamoDB table remains ACTIVE.
- AWS CLI can list the table in the correct Region.
- The application configuration references the wrong table or Region.
- Correcting the configuration restores data access.

### Business Impact

A table-not-found incident can result in:

- Failed order retrieval.
- Application errors.
- Broken API responses.
- Interrupted customer workflows.
- Increased support requests.
- Unavailable business data.
- Failed scheduled jobs.
- Delayed transaction processing.
- Reduced service reliability.

### Incident Objective

Identify whether the DynamoDB error originates from an incorrect table name, AWS Region, account, resource state, or deployment configuration.

Apply the smallest appropriate correction without recreating a healthy production database.

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
             AWS Account
                    |
                    v
              us-east-1
                    |
                    v
             Amazon DynamoDB
                    |
                    v
          ddb-lab01-orders
                    |
                    v
              ACTIVE Table
                    |
                    v
        Partition Key: order_id
                    |
                    v
             GetItem Request
                    |
                    v
           Order ORD-1001
                    |
                    v
              Success
```

### Broken Architecture — Incorrect Table Name

```text
             Order Application
                    |
                    v
              Configuration
                    |
                    v
       DYNAMODB_TABLE=ddb-lab01-order
                    |
                    v
              AWS SDK / CLI
                    |
                    v
             Amazon DynamoDB
                    |
                    v
             Table Lookup
                    |
                    v
           Requested Table Missing
                    |
                    v
         ResourceNotFoundException
```

### Broken Architecture — Incorrect Region

```text
             Order Application
                    |
                    v
           Table: ddb-lab01-orders
                    |
                    v
             Region: us-west-2
                    |
                    v
             Amazon DynamoDB
                    |
                    v
          Table Not Found in Region
                    |
                    v
         ResourceNotFoundException

Actual Table:
ddb-lab01-orders
Region: us-east-1
```

### Recovered Architecture

```text
             Order Application
                    |
                    v
           Correct Configuration
                    |
          +---------+----------+
          |                    |
          v                    v
  ddb-lab01-orders         us-east-1
          |                    |
          +---------+----------+
                    |
                    v
             Amazon DynamoDB
                    |
                    v
              ACTIVE Table
                    |
                    v
               GetItem
                    |
                    v
            Order Retrieved
```

### AWS Components

| Component | Purpose |
|---|---|
| DynamoDB | Stores order records |
| Table | Contains DynamoDB items |
| Partition Key | Identifies items |
| AWS CLI | Sends database requests |
| AWS STS | Verifies current AWS identity |
| IAM | Authorizes DynamoDB operations |
| AWS Region | Determines the regional database endpoint |
| CloudWatch | Provides operational metrics |
| Bash | Manages environment variables |
| jq | Inspects JSON output |

---

## 4. Understanding Amazon DynamoDB

Amazon DynamoDB is a fully managed NoSQL database service.

It supports key-value and document data models.

### Main Concepts

| Concept | Description |
|---|---|
| Table | Collection of items |
| Item | Group of attributes |
| Attribute | Individual data field |
| Partition Key | Required primary key component |
| Sort Key | Optional second primary key component |
| GetItem | Retrieves an item by primary key |
| PutItem | Writes an item |
| Scan | Reads items from a table |
| Query | Retrieves items using key conditions |

### Example Table

**Table:** `ddb-lab01-orders`

| order_id | customer | status | amount |
|---|---|---|---|
| ORD-1001 | Rahim | Processing | 150 |
| ORD-1002 | Karim | Shipped | 200 |

The partition key is:

```text
order_id
```

Every item in this table requires a unique partition-key value.

### DynamoDB Attribute Types

The AWS CLI uses typed attribute values.

Examples:

```json
{
  "customer": {"S": "Rahim"},
  "amount": {"N": "150"}
}
```

`S` means String.

`N` means Number.

The numeric value is represented as a string in the low-level DynamoDB API format.

### Billing Mode

This lab uses:

```text
PAY_PER_REQUEST
```

On-demand billing eliminates the need to configure provisioned read and write capacity for the small lab workload.

---

## 5. Understanding ResourceNotFoundException

`ResourceNotFoundException` indicates that DynamoDB could not access the referenced table or index resource.

Typical causes include:

1. Incorrect table name.
2. Incorrect AWS Region.
3. Incorrect AWS account or profile.
4. Table not created.
5. Table deleted.
6. Incorrect index reference.
7. Resource not in an appropriate state.

### Example Error

```text
An error occurred (ResourceNotFoundException)
when calling the GetItem operation:
Requested resource not found
```

### Missing Table vs. Missing Item

These situations are different.

**Missing table:**

```text
GetItem
   |
   v
Table Does Not Exist
   |
   v
ResourceNotFoundException
```

**Missing item:**

```text
GetItem
   |
   v
Table Exists
   |
   v
Primary Key Not Found
   |
   v
Successful API Response
Without Item Attribute
```

For an existing table, GetItem normally does not throw `ResourceNotFoundException` merely because an item is absent.

### Why Resource Identification Matters

DynamoDB tables are associated with AWS accounts and Regions.

The following reference identifies the intended table:

```text
arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/ddb-lab01-orders
```

The Region and account ID are part of the ARN.

---

## 6. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- jq.
- AWS account.
- Permissions to create, read, list, tag, and delete DynamoDB tables.
- Permissions to call AWS STS.

### Relevant IAM Actions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:ListTables
dynamodb:ListTagsOfResource
dynamodb:BatchWriteItem
dynamodb:GetItem
dynamodb:Scan
dynamodb:DeleteTable

cloudwatch:GetMetricStatistics
```

These are relevant actions, not a complete IAM policy.

### Safety Rules

- Use only fabricated data.
- Do not modify existing production tables.
- Do not automatically recreate missing production databases.
- Verify AWS account and Region.
- Check whether the lab table name is already in use.
- Use a dedicated table.
- Limit test items.
- Verify resource tags before deletion.
- Do not commit AWS credentials.
- Delete temporary lab resources when finished.

### Resource Ownership

The lab uses:

```text
Project = DynamoDB-Troubleshooting-Lab01
```

This tag helps identify the temporary table during cleanup.

---

## 7. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 01-table-not-found

cd 01-table-not-found
```

### Step 2 — Verify AWS CLI

```bash
aws --version
```

### Step 3 — Verify AWS Identity

```bash
aws sts get-caller-identity
```

### Step 4 — Inspect Configured Region

```bash
aws configure get region
```

### Step 5 — Configure Lab Variables

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab01"

export TABLE_NAME="ddb-lab01-orders"

export WRONG_TABLE_NAME="ddb-lab01-order"

export WRONG_REGION="us-west-2"
```

### Step 6 — Verify Variables

```bash
echo "$AWS_REGION"

echo "$TABLE_NAME"

echo "$WRONG_TABLE_NAME"

echo "$WRONG_REGION"
```

### Step 7 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
lab01-resources.env

evidence/

*.log

__pycache__/
*.pyc

.env
.env.*
*.pem
*.key
EOF
```

### Step 8 — Prepare Evidence Directory

```bash
mkdir -p evidence
```

---

## 8. Verify AWS Account and Region

### Step 1 — Verify Current Identity

```bash
aws sts get-caller-identity \
  --output json
```

### Step 2 — Retrieve Account ID

```bash
echo "$ACCOUNT_ID"
```

### Step 3 — Verify AWS Region

```bash
echo "$AWS_REGION"
```

Expected:

```text
us-east-1
```

### Step 4 — Verify Current DynamoDB Tables

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

### Step 5 — Check for Existing Lab Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Before creating the table, a missing table is expected to produce:

```text
ResourceNotFoundException
```

If the name already exists, do not overwrite or delete it without verifying ownership.

### Why This Step Matters

A production application might use a valid table name but the wrong AWS credentials.

Checking the caller identity can reveal an incorrect AWS profile or deployment account.

---

## 9. Create DynamoDB Table

### Step 1 — Create the Table

```bash
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=order_id,AttributeType=S \
  --key-schema \
    AttributeName=order_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --tags \
    Key=Project,Value="$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Understanding the Configuration

| Parameter | Meaning |
|---|---|
| `--table-name` | DynamoDB table name |
| `--attribute-definitions` | Defines primary-key attribute type |
| `AttributeType=S` | String key |
| `KeyType=HASH` | Partition key |
| `PAY_PER_REQUEST` | On-demand capacity |
| `--tags` | Resource identification |

### Step 2 — Wait for Table Activation

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
    ARN:TableArn
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected relevant values:

```json
{
  "Name": "ddb-lab01-orders",
  "Status": "ACTIVE"
}
```

The actual response also contains the table ARN.

### Step 4 — Save Healthy Table Metadata

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/healthy-table.json
```

### Step 5 — Verify Key Schema

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

---

## 10. Insert Sample Orders

### Step 1 — Create `orders.json`

```bash
cat > orders.json <<'EOF'
{
  "ddb-lab01-orders": [
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-1001"},
          "customer": {"S": "Rahim"},
          "status": {"S": "Processing"},
          "amount": {"N": "150"}
        }
      }
    },
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-1002"},
          "customer": {"S": "Karim"},
          "status": {"S": "Shipped"},
          "amount": {"N": "200"}
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

### Step 3 — Insert Data

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

If `UnprocessedItems` contains entries, those requests need to be retried.

### Step 4 — Verify Items

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 5 — Save Sample Data Evidence

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/initial-items.json
```

The order of items returned by Scan is not guaranteed.

---

## 11. Establish Healthy GetItem Baseline

### Step 1 — Retrieve First Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Item": {
    "order_id": {"S": "ORD-1001"},
    "customer": {"S": "Rahim"},
    "status": {"S": "Processing"},
    "amount": {"N": "150"}
  }
}
```

Attribute ordering may differ.

### Step 2 — Save Healthy GetItem Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/healthy-get-item.json
```

### Step 3 — Validate Retrieved Item

```bash
jq -e \
  '.Item.order_id.S == "ORD-1001"' \
  evidence/healthy-get-item.json
```

Expected:

```text
true
```

### Healthy Baseline Summary

| Check | Expected Result |
|---|---|
| AWS Account | Correct |
| AWS Region | us-east-1 |
| Table | Exists |
| Table Status | ACTIVE |
| Sample Items | Inserted |
| GetItem | Successful |
| Exception | None |

---

## 12. Fault Injection 1 — Incorrect Table Name

### Production Fault

The application refers to:

```text
ddb-lab01-order
```

instead of:

```text
ddb-lab01-orders
```

### Step 1 — Configure Incorrect Table Name

```bash
export DYNAMODB_TABLE="$WRONG_TABLE_NAME"
```

### Step 2 — Verify Incorrect Variable

```bash
echo "$DYNAMODB_TABLE"
```

Expected:

```text
ddb-lab01-order
```

### Step 3 — Send GetItem Request

```bash
aws dynamodb get-item \
  --table-name "$DYNAMODB_TABLE" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --region "$AWS_REGION"
```

Expected:

```text
An error occurred (ResourceNotFoundException)
when calling the GetItem operation:
Requested resource not found
```

### Step 4 — Attempt DescribeTable

```bash
aws dynamodb describe-table \
  --table-name "$DYNAMODB_TABLE" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Fault 1 Results

| Item | Finding |
|---|---|
| Actual Table | ddb-lab01-orders |
| Requested Table | ddb-lab01-order |
| AWS Region | Correct |
| Error | ResourceNotFoundException |
| Lambda or Backend Code | Not applicable |
| Cause | Incorrect table name |

---

## 13. Capture Fault 1 Evidence

### Step 1 — Save GetItem Error

```bash
aws dynamodb get-item \
  --table-name "$DYNAMODB_TABLE" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --region "$AWS_REGION" \
  > evidence/wrong-table-output.json \
  2> evidence/wrong-table-error.log

echo "Exit code: $?"
```

The exit code should be nonzero.

### Step 2 — Inspect Error

```bash
cat evidence/wrong-table-error.log
```

### Step 3 — Save Incorrect Table Metadata Failure

```bash
aws dynamodb describe-table \
  --table-name "$DYNAMODB_TABLE" \
  --region "$AWS_REGION" \
  > evidence/wrong-table-description.json \
  2> evidence/wrong-table-description-error.log
```

### Step 4 — Save Configuration Evidence

```bash
printf 'Actual table: %s\n' "$TABLE_NAME" \
  > evidence/table-name-comparison.txt

printf 'Requested table: %s\n' "$DYNAMODB_TABLE" \
  >> evidence/table-name-comparison.txt

printf 'Region: %s\n' "$AWS_REGION" \
  >> evidence/table-name-comparison.txt
```

### Step 5 — Inspect Evidence

```bash
cat evidence/table-name-comparison.txt
```

### Evidence Interpretation

The failure is reproducible when the incorrect table name is used.

The same AWS account and Region can still access the correctly named table.

This provides evidence that the root cause is resource configuration rather than an AWS service outage.

---

## 14. Investigate Fault 1 — Table Inventory

### Step 1 — Verify AWS Identity

```bash
aws sts get-caller-identity
```

### Step 2 — List Available Tables

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

Find:

```text
ddb-lab01-orders
```

### Step 3 — Compare References

```bash
echo "Application table: $DYNAMODB_TABLE"

echo "Actual table: $TABLE_NAME"
```

### Step 4 — Inspect Correct Table

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

Expected:

```json
{
  "Name": "ddb-lab01-orders",
  "Status": "ACTIVE"
}
```

### Step 5 — Save Inventory Evidence

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output json \
  > evidence/table-inventory.json
```

### Investigation Findings

The requested table name does not match the table that exists.

The AWS account and Region are correct.

The actual table remains ACTIVE.

**Root cause: Incorrect application table-name configuration.**

---

## 15. Root Cause Analysis — Fault 1

### Root Cause Diagram

```text
Application Deployment
         |
         v
Incorrect Environment Variable
         |
         v
DYNAMODB_TABLE=ddb-lab01-order
         |
         v
GetItem Request
         |
         v
DynamoDB Resource Lookup
         |
         v
Requested Table Not Found
         |
         v
ResourceNotFoundException
```

### Five Whys

**Why 1 — Why did GetItem fail?**

DynamoDB returned ResourceNotFoundException.

**Why 2 — Why couldn't DynamoDB find the table?**

The request referenced the wrong table name.

**Why 3 — Why was the table name incorrect?**

The application environment variable contained a typo.

**Why 4 — Why wasn't the typo detected?**

The simulated deployment did not validate the table reference before serving requests.

**Why 5 — How can this be prevented?**

Manage table references using Infrastructure as Code outputs, reviewed configuration, and deployment smoke tests.

### Root Cause Summary

| Item | Finding |
|---|---|
| Fault | Incorrect table name |
| Expected Table | ddb-lab01-orders |
| Requested Table | ddb-lab01-order |
| AWS Account | Correct |
| AWS Region | Correct |
| Table Health | ACTIVE |
| Root Cause | Environment variable typo |
| Remediation | Correct table reference |

---

## 16. Remediation 1 — Restore Correct Table Name

### Step 1 — Fix Application Configuration

```bash
export DYNAMODB_TABLE="$TABLE_NAME"
```

### Step 2 — Verify Updated Variable

```bash
echo "$DYNAMODB_TABLE"
```

Expected:

```text
ddb-lab01-orders
```

### Step 3 — Retry GetItem

```bash
aws dynamodb get-item \
  --table-name "$DYNAMODB_TABLE" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 4 — Save Recovered Response

```bash
aws dynamodb get-item \
  --table-name "$DYNAMODB_TABLE" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-table-name.json
```

### Step 5 — Verify Recovery

```bash
jq -e \
  '.Item.order_id.S == "ORD-1001"' \
  evidence/recovered-table-name.json
```

Expected:

```text
true
```

### Recovery Summary

| Item | Broken | Recovered |
|---|---|---|
| Table Variable | ddb-lab01-order | ddb-lab01-orders |
| Table Exists | No | Yes |
| GetItem | Exception | Success |
| Database Changes | None | None |
| Application Data | Unchanged | Unchanged |

**Fault 1 is resolved when the corrected table reference successfully retrieves the intended item.**

---

## 17. Fault Injection 2 — Incorrect AWS Region

### Production Fault

The application uses the correct table name but sends its request to the wrong AWS Region.

Actual:

```text
us-east-1
```

Incorrect:

```text
us-west-2
```

### Step 1 — Verify Actual Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region us-east-1 \
  --query 'Table.TableStatus' \
  --output text
```

Expected:

```text
ACTIVE
```

### Step 2 — Request Table in Wrong Region

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$WRONG_REGION"
```

Expected if the table does not also exist in that Region:

```text
ResourceNotFoundException
```

### Step 3 — Attempt GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --region "$WRONG_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Step 4 — Compare Regions

```bash
echo "Actual Region: $AWS_REGION"

echo "Incorrect Region: $WRONG_REGION"
```

### Fault 2 Results

| Item | Finding |
|---|---|
| Table Name | Correct |
| Actual Region | us-east-1 |
| Requested Region | us-west-2 |
| Error | ResourceNotFoundException |
| Root Cause | Incorrect AWS Region |

**Important:** If an unrelated table with the same name already exists in `us-west-2`, this test may not return ResourceNotFoundException. Stop and investigate rather than modifying that table.

---

## 18. Capture Fault 2 Evidence

### Step 1 — Save Wrong-Region Error

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --region "$WRONG_REGION" \
  > evidence/wrong-region-output.json \
  2> evidence/wrong-region-error.log

echo "Exit code: $?"
```

### Step 2 — Inspect Error

```bash
cat evidence/wrong-region-error.log
```

### Step 3 — Save Table Inventories

Correct Region:

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output json \
  > evidence/tables-us-east-1.json
```

Incorrect Region:

```bash
aws dynamodb list-tables \
  --region "$WRONG_REGION" \
  --output json \
  > evidence/tables-us-west-2.json
```

### Step 4 — Inspect Inventory Comparison

```bash
cat evidence/tables-us-east-1.json | jq .

cat evidence/tables-us-west-2.json | jq .
```

### Step 5 — Save Region Comparison

```bash
printf 'Actual Region: %s\n' "$AWS_REGION" \
  > evidence/region-comparison.txt

printf 'Requested Region: %s\n' "$WRONG_REGION" \
  >> evidence/region-comparison.txt

printf 'Table Name: %s\n' "$TABLE_NAME" \
  >> evidence/region-comparison.txt
```

### Evidence Interpretation

The table exists in `us-east-1`.

The application requested the table from `us-west-2`.

The same table name is not automatically available across AWS Regions.

---

## 19. Investigate Fault 2 — AWS Account and Region

### Step 1 — Verify AWS Profile

```bash
aws configure list
```

### Step 2 — Verify Account

```bash
aws sts get-caller-identity
```

### Step 3 — Inspect Environment Variables

```bash
echo "$AWS_REGION"

echo "$AWS_DEFAULT_REGION"
```

### Step 4 — Inspect Table Inventory in Correct Region

```bash
aws dynamodb list-tables \
  --region us-east-1 \
  --output table
```

### Step 5 — Inspect Table Inventory in Incorrect Region

```bash
aws dynamodb list-tables \
  --region us-west-2 \
  --output table
```

### Step 6 — Inspect Table ARN

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.TableArn' \
  --output text \
  --region us-east-1
```

Expected ARN structure:

```text
arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/ddb-lab01-orders
```

### Step 7 — Inspect Table Status

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.TableStatus' \
  --output text \
  --region us-east-1
```

Expected:

```text
ACTIVE
```

### Investigation Findings

The table is available in the correct AWS account and Region.

The application request targets a different Region.

**Root cause: Incorrect regional configuration.**

---

## 20. Root Cause Analysis and Remediation — Fault 2

### Root Cause Diagram

```text
Application Configuration
          |
          v
AWS Region = us-west-2
          |
          v
DynamoDB GetItem
          |
          v
DynamoDB Endpoint in us-west-2
          |
          v
Table Not Found
          |
          v
ResourceNotFoundException
```

### Five Whys

**Why 1 — Why did the application fail?**

DynamoDB returned ResourceNotFoundException.

**Why 2 — Why wasn't the table found?**

The request targeted the wrong AWS Region.

**Why 3 — Why was the wrong Region used?**

The application or CLI configuration specified `us-west-2`.

**Why 4 — Why wasn't the mismatch detected?**

The simulated deployment lacked a Region validation check.

**Why 5 — How can this be prevented?**

Validate account, Region, table ARN, and environment-specific resource configuration before deployment.

### Step 1 — Restore Region

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"
```

### Step 2 — Verify

```bash
echo "$AWS_REGION"
```

### Step 3 — Retry GetItem

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 4 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-region.json
```

### Step 5 — Validate

```bash
jq -e \
  '.Item.order_id.S == "ORD-1001"' \
  evidence/recovered-region.json
```

Expected:

```text
true
```

### Recovery Comparison

| Item | Broken | Recovered |
|---|---|---|
| Table Name | Correct | Correct |
| Region | us-west-2 | us-east-1 |
| Resource Lookup | Failed | Successful |
| GetItem | ResourceNotFoundException | Item returned |
| Database Changes | None | None |

---

## 21. Additional Diagnostic — DynamoDB Table State

A table may exist but not yet be available for the requested operation.

### Step 1 — Inspect Table State

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

### Common Table States

| Status | Description |
|---|---|
| CREATING | Table creation in progress |
| ACTIVE | Table available for normal operations |
| UPDATING | Table configuration update in progress |
| DELETING | Table deletion in progress |
| ARCHIVING | Table archival in progress |
| ARCHIVED | Table archived |

A table in an unsuitable lifecycle state can cause operations to fail.

### Step 2 — Wait for ACTIVE Status

```bash
aws dynamodb wait table-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

The waiter polls DescribeTable until it reports `ACTIVE`.

### Production Recommendation

Applications and deployment workflows should verify table readiness before issuing dependent database operations.

---

## 22. Additional Diagnostic — Missing Table vs. Missing Item

This distinction is important in production troubleshooting.

### Scenario A — Missing Table

```bash
aws dynamodb get-item \
  --table-name "table-that-does-not-exist-lab01" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Scenario B — Existing Table, Missing Item

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-9999"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: a successful response without an `Item` field.

Often the CLI displays:

```json
{}
```

### Comparison

| Scenario | API Result | Meaning |
|---|---|---|
| Table missing | ResourceNotFoundException | Resource not found |
| Table exists, item missing | No Item field | Requested key not found |
| Table exists, item found | Item returned | Successful retrieval |
| Invalid key schema | ValidationException | Request structure incorrect |
| Permission denied | AccessDeniedException | Authorization failure |

### Why This Matters

A Cloud Engineer should not troubleshoot a missing item as if the entire DynamoDB table were unavailable.

The error category determines the correct investigation path.

---

## 23. CloudWatch Monitoring and Operational Investigation

### CloudWatch Metrics

DynamoDB publishes operational metrics to Amazon CloudWatch.

Relevant metrics include:

| Metric | Purpose |
|---|---|
| SuccessfulRequestLatency | Latency of successful DynamoDB requests |
| ConsumedReadCapacityUnits | Read capacity consumption |
| ConsumedWriteCapacityUnits | Write capacity consumption |
| ReadThrottleEvents | Read throttling activity |
| WriteThrottleEvents | Write throttling activity |
| SystemErrors | DynamoDB service-side errors |
| UserErrors | Client-side request errors |

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
    Name=Operation,Value=GetItem \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Read Capacity Consumption

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

### Step 4 — Inspect UserErrors

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

`UserErrors` is a broad service-level client-error metric. It is not a reliable table-specific proof that a particular missing-table request occurred.

### Step 5 — Save Metric Evidence

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
  > evidence/get-item-latency.json
```

### Metric Interpretation

A missing-table error is best diagnosed using the exact API exception, requested table name, Region, and account identity.

CloudWatch provides supporting operational context.

Metrics may appear after a publication delay.

DynamoDB does not automatically create Lambda-style application log streams for each GetItem request.

---

## 24. Cloud Security Engineering Considerations

### Verify AWS Identity

An incorrect AWS profile can direct requests to the wrong account.

Always inspect:

```bash
aws sts get-caller-identity
```

### IAM Least Privilege

Applications should receive only the DynamoDB permissions required for their tasks.

For example, an order-reading application generally should not receive unrestricted permissions to delete DynamoDB tables.

### Avoid Recreating Production Tables

A missing table can indicate:

- Incorrect application configuration.
- Wrong AWS account.
- Wrong Region.
- Deployment failure.
- Accidental deletion.
- Infrastructure drift.

Creating a replacement table without investigation may cause data loss or hide a more serious incident.

### CloudTrail Investigation

For suspected table deletion or unauthorized configuration changes, investigate AWS CloudTrail management events.

For example, review relevant CreateTable, DeleteTable, and UpdateTable activities.

DynamoDB data events require appropriate CloudTrail configuration and are not necessarily recorded by default.

### Infrastructure as Code

Manage DynamoDB tables with Terraform or CloudFormation.

For example:

```text
Terraform DynamoDB Table
         |
         v
Output Table Name / ARN
         |
         v
Application Configuration
         |
         v
Deployment Validation
```

### Data Protection

Production DynamoDB workloads should use appropriate encryption, access controls, and backup configurations.

### Security Principle

**A resource lookup error should trigger identity and configuration investigation, not unrestricted IAM permissions or uncontrolled database recreation.**

---

## 25. Cost Management

### AWS Cost Components

| Component | Potential Cost |
|---|---|
| DynamoDB On-Demand | Read and write requests |
| DynamoDB Storage | Stored item data |
| CloudWatch | Applicable metrics and monitoring |
| AWS CLI | No separate CLI charge |
| IAM | No separate standard IAM role charge |

### Lab Cost Controls

- Use only two small test items.
- Use on-demand billing.
- Avoid large Scan operations.
- Avoid repeated unnecessary API calls.
- Do not create additional tables without a reason.
- Delete the test table after verification.

### Important Note

The actual cost depends on AWS pricing, account eligibility, and resource usage.

A small lab is generally inexpensive, but it should not be assumed to be completely free.

---

## 26. Recovery Verification

### Step 1 — Verify Correct Account

```bash
aws sts get-caller-identity
```

### Step 2 — Verify Correct Region

```bash
echo "$AWS_REGION"
```

Expected:

```text
us-east-1
```

### Step 3 — Verify Table Status

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

### Step 4 — Verify First Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 5 — Verify Second Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1002"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 6 — Save Final Verification Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/final-order-1001.json
```

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-1002"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/final-order-1002.json
```

### Step 7 — Validate Both Items

```bash
jq -e \
  '.Item.order_id.S == "ORD-1001"' \
  evidence/final-order-1001.json
```

```bash
jq -e \
  '.Item.order_id.S == "ORD-1002"' \
  evidence/final-order-1002.json
```

### Recovery Comparison

| Check | Fault 1 | Fault 2 | Recovered |
|---|---|---|---|
| Table Name | Wrong | Correct | Correct |
| Region | Correct | Wrong | Correct |
| Table Status | ACTIVE in correct Region | ACTIVE in correct Region | ACTIVE |
| GetItem | Exception | Exception | Success |
| Data Changes | None | None | None |

**Recovery is confirmed when the correctly configured GetItem requests retrieve both orders from the intended table.**

---

## 27. AWS Resource Cleanup

**Warning:** Delete only the DynamoDB table created for this lab.

### Step 1 — Verify Table Name

```bash
echo "$TABLE_NAME"
```

Expected:

```text
ddb-lab01-orders
```

### Step 2 — Verify Table ARN

```bash
export TABLE_ARN=$(aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query Table.TableArn \
  --output text \
  --region "$AWS_REGION")

echo "$TABLE_ARN"
```

### Step 3 — Verify Resource Tags

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab01
```

### Step 4 — Verify Data Is Disposable

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Confirm that the table contains only the intended test data.

### Step 5 — Delete Table

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

This exception is expected because the table has intentionally been deleted.

### Step 8 — Confirm Table Inventory

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

The lab table should no longer appear.

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| Test Orders | Deleted with table |
| EC2 | Not created |
| Lambda | Not created |
| IAM Roles | Not created |
| NAT Gateway | Not created |
| RDS | Not created |
| Local Source Files | Retained |
| Local Evidence | Retained for documentation |

---

## 28. Interview Questions and Answers

### Q1. What is ResourceNotFoundException in DynamoDB?

It indicates that the requested table or index resource could not be found or accessed in its expected state.

### Q2. What are common reasons for ResourceNotFoundException?

Incorrect table name, AWS Region, AWS account, missing table, deleted table, incorrect index, or resource state.

### Q3. How do you check whether a table exists?

```bash
aws dynamodb describe-table \
  --table-name TABLE_NAME
```

### Q4. How do you list DynamoDB tables?

```bash
aws dynamodb list-tables
```

### Q5. Why is AWS Region important?

DynamoDB tables belong to specific AWS Regions. A table in one Region does not automatically exist in another.

### Q6. How do you verify your AWS account?

```bash
aws sts get-caller-identity
```

### Q7. What is the difference between GetItem and Scan?

GetItem retrieves a specific item using its primary key. Scan reads items from a table without requiring a key condition.

### Q8. What happens if GetItem requests a missing item?

The request can succeed without returning an `Item` element.

### Q9. What happens if GetItem requests a missing table?

DynamoDB can return ResourceNotFoundException.

### Q10. What is the purpose of DescribeTable?

DescribeTable retrieves table metadata such as its name, status, key schema, ARN, and configuration.

### Q11. Why should you wait for ACTIVE table status?

A newly created table may not yet be ready for normal item operations.

### Q12. What does PAY_PER_REQUEST mean?

It is DynamoDB's on-demand capacity mode, where request charges are based on usage rather than explicitly provisioned RCUs and WCUs.

### Q13. Can two AWS Regions contain DynamoDB tables with the same name?

Yes. Table names are unique within an account and Region, not globally across all Regions.

### Q14. Why can this be dangerous?

An application using the wrong Region might access a different table with the same name rather than return an obvious error.

### Q15. Should you automatically create a missing production table?

No. First investigate whether the table is missing, incorrectly referenced, deleted, or located in another account or Region.

### Q16. How can Terraform help prevent this error?

Terraform can manage DynamoDB resources and expose table names and ARNs through outputs, reducing manual configuration mistakes.

### Q17. What is the difference between ResourceNotFoundException and AccessDeniedException?

ResourceNotFoundException indicates a resource lookup or state problem. AccessDeniedException indicates an authorization problem.

### Q18. How would you explain this lab in a technical interview?

I created an Amazon DynamoDB table using AWS CLI in the `us-east-1` Region.

The table used `order_id` as its partition key and on-demand billing.

I inserted two sample orders and verified successful GetItem operations.

Next, I intentionally configured an incorrect table name and reproduced ResourceNotFoundException.

I investigated the error by verifying AWS identity, listing DynamoDB tables, inspecting table metadata, and comparing the application configuration with the actual resource name.

The investigation identified a table-name typo.

I corrected the configuration and verified that GetItem succeeded.

I then reproduced the same exception by requesting the correct table in the wrong AWS Region.

I compared table inventories in `us-east-1` and `us-west-2`, inspected the table ARN, and confirmed that the actual table existed only in the intended Region.

I restored the correct Region and verified both test orders.

Finally, I reviewed IAM least privilege, resource identification, deployment validation, and safe cleanup.

---

## 29. Repository Structure

```text
aws-dynamodb-troubleshooting-labs/
│
├── README.md
├── .gitignore
│
├── 01-table-not-found/
│   ├── README.md
│   ├── .gitignore
│   ├── orders.json
│   ├── lab01-resources.env
│   │
│   └── evidence/
│       ├── healthy-table.json
│       ├── initial-items.json
│       ├── healthy-get-item.json
│       ├── wrong-table-output.json
│       ├── wrong-table-error.log
│       ├── wrong-table-description.json
│       ├── wrong-table-description-error.log
│       ├── table-name-comparison.txt
│       ├── table-inventory.json
│       ├── recovered-table-name.json
│       ├── wrong-region-output.json
│       ├── wrong-region-error.log
│       ├── tables-us-east-1.json
│       ├── tables-us-west-2.json
│       ├── region-comparison.txt
│       ├── recovered-region.json
│       ├── get-item-latency.json
│       ├── final-order-1001.json
│       └── final-order-1002.json
│
├── 02-putitem-access-denied/
├── 03-validation-exception/
├── 04-wrong-partition-key/
├── 05-provisioned-throughput-exceeded/
├── 06-conditional-check-failed/
├── 07-gsi-query-not-returning-results/
├── 08-dynamodb-streams-not-triggering/
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

The repository structure shows the intended local lab files. Generated evidence files will appear only after their corresponding commands are executed.

### Recommended Public GitHub Files

```text
01-table-not-found/
├── README.md
├── .gitignore
└── orders.json
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Complete production troubleshooting documentation |
| .gitignore | Excludes local evidence and configuration |
| orders.json | Fabricated DynamoDB order data |
| lab01-resources.env | Optional local environment configuration |
| healthy-table.json | Table configuration |
| initial-items.json | Initial sample records |
| healthy-get-item.json | Baseline GetItem response |
| wrong-table-error.log | Incorrect table-name error |
| table-name-comparison.txt | Expected and actual table references |
| recovered-table-name.json | Successful table-name recovery |
| wrong-region-error.log | Incorrect Region error |
| tables-us-east-1.json | Correct-Region table inventory |
| tables-us-west-2.json | Wrong-Region table inventory |
| recovered-region.json | Successful regional recovery |
| final-order-1001.json | Final verification of first order |
| final-order-1002.json | Final verification of second order |

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 01
01-table-not-found/lab01-resources.env
01-table-not-found/evidence/

# Local AWS configuration
.env
.env.*
*-resources.env
*-secrets.env

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

This lab demonstrates how Amazon DynamoDB can return ResourceNotFoundException even when the intended table is healthy.

We created a DynamoDB table in `us-east-1` using on-demand capacity.

The table used `order_id` as its partition key and stored two fabricated customer orders.

We confirmed the table was ACTIVE and retrieved an order successfully.

Next, we intentionally used an incorrect table name and reproduced ResourceNotFoundException.

We investigated the problem using AWS CLI, table inventory, configuration comparison, and DescribeTable.

The investigation identified an incorrect application environment variable.

After restoring the correct table name, GetItem succeeded.

We then reproduced a similar failure using an incorrect AWS Region.

We compared table inventories in two Regions and inspected the DynamoDB table ARN.

This confirmed that the table existed in `us-east-1`, while the application requested it from `us-west-2`.

After restoring the correct Region, the application successfully retrieved the stored orders.

We also reviewed the difference between missing tables and missing items, DynamoDB table states, IAM least privilege, CloudWatch metrics, resource identification, and cleanup.

**Key Lesson:** When DynamoDB returns ResourceNotFoundException, first verify the AWS account, Region, exact table or index name, and resource state before changing application code or recreating infrastructure.

### Skills Demonstrated

- Amazon DynamoDB.
- DynamoDB table creation.
- DynamoDB on-demand capacity.
- Partition-key configuration.
- BatchWriteItem.
- GetItem.
- Scan.
- DescribeTable.
- ListTables.
- ResourceNotFoundException troubleshooting.
- AWS Region investigation.
- AWS account verification.
- DynamoDB ARN analysis.
- Linux Bash.
- AWS CLI v2.
- jq.
- CloudWatch metrics.
- Root cause analysis.
- Configuration remediation.
- Recovery verification.
- IAM least privilege.
- AWS cost management.
- Resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-001 |
| Scenario | DynamoDB Table Not Found |
| Table | ddb-lab01-orders |
| Region | us-east-1 |
| Partition Key | order_id |
| Billing Mode | PAY_PER_REQUEST |
| Test Items | 2 |
| Healthy Baseline | Successful GetItem |
| Fault 1 | Incorrect table name |
| Fault 1 Error | ResourceNotFoundException |
| Fault 1 Remediation | Correct table name |
| Fault 2 | Incorrect AWS Region |
| Fault 2 Error | ResourceNotFoundException |
| Fault 2 Remediation | Correct AWS Region |
| Recovery | Successful GetItem |
| Data Changes During Remediation | None |
| Cleanup | DynamoDB table deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** DynamoDB resource troubleshooting requires accurate identification of AWS account, Region, table name, resource state, and application configuration. Correct diagnosis helps engineers restore service without introducing unnecessary database changes.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [DynamoDB Error Handling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.Errors.html)
- [AWS CLI — Create Table](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/create-table.html)
- [AWS CLI — Describe Table](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/describe-table.html)
- [AWS CLI — List Tables](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/list-tables.html)
- [AWS CLI — Get Item](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-item.html)
- [AWS CLI — Batch Write Item](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/batch-write-item.html)
- [AWS CLI — Wait for Table Exists](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/wait/table-exists.html)
- [AWS CLI — Wait for Table Not Exists](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/wait/table-not-exists.html)
- [DynamoDB Table States](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithTables.Basics.html)
- [DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [DynamoDB Security](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/security.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)