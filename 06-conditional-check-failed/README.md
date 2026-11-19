# Lab 06 — Amazon DynamoDB ConditionalCheckFailedException

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve Amazon DynamoDB `ConditionalCheckFailedException` errors caused by failed conditional write operations.

In production, applications frequently use DynamoDB conditional expressions to protect data from unintended changes.

Conditional writes are especially useful in e-commerce platforms, inventory management systems, financial applications, distributed systems, and applications where multiple processes may update the same record.

A conditional write succeeds only when the specified condition evaluates to true.

When the condition evaluates to false, DynamoDB rejects the write and can return:

```text
ConditionalCheckFailedException
```

In this lab, we create a DynamoDB table named `ddb-lab06-orders` in the `us-east-1` AWS Region.

The table uses a String partition key named `order_id` and on-demand billing.

We insert a sample order containing:

- Order ID
- Customer name
- Order status
- Version number
- Order amount

We then intentionally reproduce three production-style failures:

1. Duplicate order creation using `attribute_not_exists`.
2. Stale version updates using optimistic concurrency control.
3. Invalid order-state transitions using conditional status checks.

We investigate each failure using AWS CLI, DynamoDB GetItem, conditional expressions, version attributes, and saved troubleshooting evidence.

We remediate the failures without removing essential data-protection conditions.

Finally, we verify successful recovery, review security considerations, investigate CloudWatch metrics, and delete the temporary DynamoDB table.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Verify AWS CLI and Identity
          |
          v
Configure Lab Variables
          |
          v
Create DynamoDB Table
          |
          v
Wait for ACTIVE Status
          |
          v
Insert Order ORD-6001
          |
          v
Verify Healthy Baseline
          |
          v
Fault 01 — Duplicate PutItem
          |
          v
ConditionalCheckFailedException
          |
          v
Verify Original Data Protected
          |
          v
Create Order ORD-6002
          |
          v
Fault 02 — Stale Version
          |
          v
Update v1 to v2
          |
          v
Attempt Update Using v1
          |
          v
ConditionalCheckFailedException
          |
          v
Read Current Version
          |
          v
Resolve Update Conflict
          |
          v
Update v2 to v3
          |
          v
Fault 03 — Invalid Status
          |
          v
Attempt to Cancel Shipped Order
          |
          v
ConditionalCheckFailedException
          |
          v
Verify Shipped Order Protected
          |
          v
Cancel Eligible Pending Order
          |
          v
Verify Final Data
          |
          v
CloudWatch Investigation
          |
          v
Root Cause Analysis
          |
          v
Security and Cost Review
          |
          v
Resource Cleanup
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-006 |
| Lab Name | ConditionalCheckFailedException |
| Difficulty | Intermediate |
| Primary Service | Amazon DynamoDB |
| Supporting Services | AWS IAM, STS, CloudWatch |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, jq |
| Table Name | `ddb-lab06-orders` |
| Partition Key | `order_id` |
| Partition-Key Type | String |
| Sort Key | None |
| Billing Mode | PAY_PER_REQUEST |
| Operations | PutItem, UpdateItem, GetItem, Scan |
| Expected Error | ConditionalCheckFailedException |
| Fault 01 | Duplicate item creation |
| Fault 02 | Stale version update |
| Fault 03 | Invalid status transition |
| Version Attribute | `version` |
| Status Attribute | `status` |
| Initial Order | ORD-6001 |
| Additional Order | ORD-6002 |
| Root Cause | Conditional expression evaluates to false |
| Remediation | Resolve conflicts and satisfy valid conditions |
| Recovery | Successful conditional writes |
| Project Tag | DynamoDB-Troubleshooting-Lab06 |
| Cleanup | Delete temporary DynamoDB table |

### Learning Objectives

- Understand DynamoDB conditional expressions.
- Understand ConditionalCheckFailedException.
- Understand conditional PutItem.
- Understand conditional UpdateItem.
- Prevent duplicate item creation.
- Understand optimistic concurrency control.
- Understand version attributes.
- Prevent lost updates.
- Investigate stale application state.
- Understand conditional order-state transitions.
- Use ExpressionAttributeNames.
- Use ExpressionAttributeValues.
- Use ReturnValues.
- Investigate ReturnValuesOnConditionCheckFailure.
- Verify database data integrity.
- Investigate CloudWatch conditional failure metrics.
- Perform production root cause analysis.
- Apply least-privilege IAM permissions.
- Safely clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

An e-commerce company operates an order-management application.

Customer orders are stored in Amazon DynamoDB.

Each order contains an order identifier, customer name, status, amount, and version number.

Example:

| Attribute | Value |
|---|---|
| order_id | ORD-6001 |
| customer | Rahim |
| status | PENDING |
| version | 1 |
| amount | 150 |

The application supports multiple services that interact with the same order.

For example:

- An order-processing service creates orders.
- A payment-processing service updates order status.
- A shipping service marks orders as shipped.
- A customer service application handles cancellations.

Multiple services may attempt to modify the same order.

To protect data integrity, the application uses conditional writes.

During a production incident, two application processes attempt to update the same order.

Application A reads version `1` and successfully updates the order to version `2`.

Application B previously read version `1` and attempts another update using that outdated version.

DynamoDB rejects Application B's write because its expected version does not match the current version.

The application receives:

```text
ConditionalCheckFailedException
```

The Cloud Engineering team investigates the error.

The investigation confirms:

- The DynamoDB table exists.
- The table remains ACTIVE.
- The AWS account and Region are correct.
- IAM permissions are sufficient.
- The order exists.
- The requested condition evaluates to false.
- DynamoDB correctly rejects the conflicting update.

Instead of removing the condition, the engineer inspects the current record, resolves the conflict, and issues a valid conditional update.

The application successfully updates the order without overwriting another process's changes.

### Incident Symptoms

- PutItem returns ConditionalCheckFailedException.
- UpdateItem returns ConditionalCheckFailedException.
- The table remains ACTIVE.
- Existing items remain readable.
- Expected versions differ from stored versions.
- Duplicate creation attempts are rejected.
- Invalid state transitions are rejected.
- Correct conditional writes succeed.

### Business Impact

Conditional write conflicts may affect:

- Order-processing workflows.
- Customer transactions.
- Inventory updates.
- Payment processing.
- Concurrent application requests.
- Background workers.
- State synchronization.
- Distributed application reliability.

However, conditional failures can also demonstrate that the database is correctly protecting data integrity.

### Incident Objective

Determine why the condition evaluated to false and resolve the application conflict without removing important business rules or overwriting valid data.

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
            Conditional PutItem
                    |
                    v
           Condition Evaluated
                    |
                    v
                 True
                    |
                    v
              Amazon DynamoDB
                    |
                    v
               Item Stored
                    |
                    v
             GetItem Verification
```

### Broken Architecture — Duplicate Item

```text
             Order Application
                    |
                    v
          Create Existing Order
                    |
                    v
       attribute_not_exists(order_id)
                    |
                    v
              Condition False
                    |
                    v
       ConditionalCheckFailedException
                    |
                    v
          Existing Item Protected
```

### Broken Architecture — Stale Version

```text
              DynamoDB Order
                Version 1
                    |
            +-------+-------+
            |               |
            v               v
       Application A   Application B
         Reads v1        Reads v1
            |               |
            v               |
       Updates to v2        |
            |               |
            v               v
          Success       Expects v1
                            |
                            v
                    Condition False
                            |
                            v
              ConditionalCheckFailedException
```

### Recovered Architecture

```text
                Application
                     |
                     v
              Read Current Item
                     |
                     v
               Version = 2
                     |
                     v
             Resolve Data Conflict
                     |
                     v
          Construct Conditional Update
                     |
                     v
          Expected Version = 2
                     |
                     v
              Condition True
                     |
                     v
                 UpdateItem
                     |
                     v
               Version = 3
                     |
                     v
               GetItem Success
```

### AWS Components

| Component | Purpose |
|---|---|
| DynamoDB | Stores orders |
| PutItem | Creates items |
| UpdateItem | Modifies items |
| GetItem | Retrieves current item state |
| ConditionExpression | Defines write requirements |
| Version Attribute | Supports optimistic concurrency |
| AWS STS | Identifies AWS principal |
| IAM | Authorizes database operations |
| CloudWatch | Monitors conditional failures |
| AWS CLI | Performs troubleshooting |
| Bash | Manages lab configuration |
| jq | Validates JSON evidence |

---

## 4. Understanding Conditional Writes

DynamoDB conditional writes allow applications to modify data only when specific conditions are satisfied.

### Example

An application wants to create an order only if it does not already exist.

The application uses:

```text
attribute_not_exists(order_id)
```

If the item does not exist, the condition evaluates to true.

DynamoDB creates the item.

If the item already exists, the condition evaluates to false.

DynamoDB rejects the write.

### Common Condition Expressions

| Condition | Meaning | Production Use |
|---|---|---|
| `attribute_not_exists(order_id)` | Item key does not exist | Prevent duplicates |
| `attribute_exists(order_id)` | Item key exists | Prevent accidental creation |
| `#v = :expected` | Version matches expected value | Optimistic locking |
| `#s = :expected` | Status matches expected value | State transition validation |
| `#qty >= :requested` | Sufficient quantity exists | Inventory protection |

### Conditional Write Evaluation

```text
Application Sends Write
           |
           v
DynamoDB Evaluates Condition
           |
       +---+---+
       |       |
       v       v
      True    False
       |       |
       v       v
    Write    ConditionalCheckFailedException
    Applied       |
                  v
             Write Not Applied
```

The condition is evaluated atomically as part of the write operation.

---

## 5. Understanding Optimistic Concurrency Control

Optimistic concurrency control prevents an application from overwriting data that another process has changed.

It commonly uses a version attribute.

### Example

Initial order:

```text
order_id = ORD-6001
version = 1
status = PENDING
```

Application A updates the order:

```text
Expected version = 1
New version = 2
New status = PROCESSING
```

Application B attempts another update:

```text
Expected version = 1
Actual version = 2
```

The condition evaluates to false.

DynamoDB rejects Application B's update.

### Why Version Numbers Matter

Without version checking, two processes can overwrite each other's changes.

This is called a lost-update problem.

### Version-Based Protection

```text
Read Item
    |
    v
Read Version
    |
    v
Construct Update
    |
    v
Condition: version = expected
    |
    v
Update Version Atomically
    |
    v
Write Applied or Rejected
```

### Production Benefit

Optimistic concurrency control protects data without requiring applications to hold a database lock for every read-modify-write operation.

---

## 6. Prerequisites and Safety

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
dynamodb:PutItem
dynamodb:UpdateItem
dynamodb:GetItem
dynamodb:Scan
dynamodb:DeleteTable

cloudwatch:GetMetricStatistics
```

These are relevant permissions rather than a complete IAM policy.

### Safety Requirements

- Use a dedicated DynamoDB table.
- Use fabricated customer orders.
- Never test destructive operations against production data.
- Preserve conditional expressions during remediation.
- Do not blindly overwrite existing items.
- Verify AWS account and Region.
- Avoid uncontrolled retries.
- Verify resource ownership before cleanup.

### Resource Identification

```text
Project = DynamoDB-Troubleshooting-Lab06
```

---

## 7. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 06-conditional-check-failed

cd 06-conditional-check-failed
```

### Step 2 — Verify AWS CLI

```bash
aws --version
```

### Step 3 — Verify jq

```bash
jq --version
```

### Step 4 — Verify AWS Identity

```bash
aws sts get-caller-identity
```

### Step 5 — Configure Lab Variables

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export TABLE_NAME="ddb-lab06-orders"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab06"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"
```

### Step 6 — Verify Variables

```bash
echo "$AWS_REGION"
echo "$TABLE_NAME"
echo "$TABLE_ARN"
```

### Step 7 — Prepare Evidence Directory

```bash
mkdir -p evidence
```

### Step 8 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
evidence/
lab06-resources.env

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

### Step 1 — Verify Caller Identity

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

### Step 3 — List DynamoDB Tables

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

### Step 4 — Verify Lab Table Does Not Already Exist

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Before table creation, expected:

```text
ResourceNotFoundException
```

If the name already exists, verify ownership before proceeding.

---

## 9. Create DynamoDB Table

### Step 1 — Create Table

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
```

### Step 4 — Save Table Evidence

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/table-description.json
```

### Table Configuration

| Parameter | Value |
|---|---|
| Table | ddb-lab06-orders |
| Partition Key | order_id |
| Key Type | String |
| Billing Mode | PAY_PER_REQUEST |
| Status | ACTIVE |

---

## 10. Establish Healthy Baseline

### Step 1 — Create `order-6001.json`

```bash
cat > order-6001.json <<'EOF'
{
  "order_id": {"S": "ORD-6001"},
  "customer": {"S": "Rahim"},
  "status": {"S": "PENDING"},
  "version": {"N": "1"},
  "amount": {"N": "150"}
}
EOF
```

### Step 2 — Validate JSON

```bash
jq . order-6001.json
```

### Step 3 — Insert Order

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://order-6001.json \
  --region "$AWS_REGION"
```

Expected: successful PutItem.

### Step 4 — Retrieve Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 5 — Save Baseline Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/healthy-order.json
```

### Step 6 — Validate Initial State

```bash
jq -e '
  .Item.version.N == "1" and
  .Item.status.S == "PENDING"
' evidence/healthy-order.json
```

Expected:

```text
true
```

### Healthy Baseline

| Attribute | Expected Value |
|---|---|
| order_id | ORD-6001 |
| customer | Rahim |
| status | PENDING |
| version | 1 |
| amount | 150 |

---

## 11. Fault Injection 01 — Duplicate Order Creation

### Production Problem

An application attempts to create an order that already exists.

A duplicate request might be caused by:

- Network retries.
- Application bugs.
- Duplicate event processing.
- Repeated customer submissions.
- Concurrent order-processing requests.

### Step 1 — Create Duplicate Payload

```bash
cat > duplicate-order.json <<'EOF'
{
  "order_id": {"S": "ORD-6001"},
  "customer": {"S": "Rahim"},
  "status": {"S": "PENDING"},
  "version": {"N": "1"},
  "amount": {"N": "999"}
}
EOF
```

The duplicate payload contains a different amount.

The original order amount is `150`.

### Step 2 — Attempt Conditional PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://duplicate-order.json \
  --condition-expression \
    "attribute_not_exists(order_id)" \
  --region "$AWS_REGION"
```

Expected:

```text
ConditionalCheckFailedException
```

### Step 3 — Save Failure Evidence

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://duplicate-order.json \
  --condition-expression \
    "attribute_not_exists(order_id)" \
  --region "$AWS_REGION" \
  > evidence/duplicate-output.json \
  2> evidence/duplicate-error.log

echo "Exit code: $?"
```

Expected: nonzero exit code.

### Step 4 — Inspect Error

```bash
cat evidence/duplicate-error.log
```

### Root Cause

The item already exists.

Therefore:

```text
attribute_not_exists(order_id) = false
```

DynamoDB correctly rejects the duplicate request.

---

## 12. Investigate Duplicate Order Protection

### Step 1 — Retrieve Existing Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 2 — Save Protection Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/duplicate-protection.json
```

### Step 3 — Verify Amount Is Unchanged

```bash
jq -e '.Item.amount.N == "150"' \
  evidence/duplicate-protection.json
```

Expected:

```text
true
```

### Investigation Findings

| Item | Result |
|---|---|
| Original Order | Exists |
| Duplicate Request | Rejected |
| Original Amount | 150 |
| Attempted Amount | 999 |
| Final Amount | 150 |
| Data Overwritten | No |

### Production Lesson

A ConditionalCheckFailedException can indicate that DynamoDB successfully prevented an accidental overwrite.

---

## 13. Remediation 01 — Handle Duplicate Creation

### Important Remediation Principle

Do not remove the condition simply to make the write succeed.

First determine whether the request is a legitimate duplicate or a new order with an incorrectly reused identifier.

For this lab, we create a new order using another order ID.

### Step 1 — Create `order-6002.json`

```bash
cat > order-6002.json <<'EOF'
{
  "order_id": {"S": "ORD-6002"},
  "customer": {"S": "Karim"},
  "status": {"S": "PENDING"},
  "version": {"N": "1"},
  "amount": {"N": "200"}
}
EOF
```

### Step 2 — Insert Using Conditional PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item file://order-6002.json \
  --condition-expression \
    "attribute_not_exists(order_id)" \
  --region "$AWS_REGION"
```

Expected: success.

### Step 3 — Verify New Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6002"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Recovery Results

| Operation | Result |
|---|---|
| Duplicate ORD-6001 | Rejected |
| Original ORD-6001 | Preserved |
| New ORD-6002 | Created |
| Data Integrity | Maintained |

**Fault 01 resolved without overwriting the original order.**

---

## 14. Fault Injection 02 — Stale Version Update

### Production Problem

Two application processes attempt to update the same order.

Application A successfully changes the order.

Application B attempts an update using an outdated version number.

### Initial State

```text
Order: ORD-6001
Status: PENDING
Version: 1
```

### Step 1 — Application A Performs Valid Update

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --update-expression \
    "SET #s = :new_status, #v = #v + :one" \
  --condition-expression \
    "#v = :expected" \
  --expression-attribute-names '{
    "#s": "status",
    "#v": "version"
  }' \
  --expression-attribute-values '{
    ":new_status": {"S": "PROCESSING"},
    ":one": {"N": "1"},
    ":expected": {"N": "1"}
  }' \
  --return-values ALL_NEW \
  --region "$AWS_REGION"
```

### Expected State

```text
Status = PROCESSING
Version = 2
```

### Step 2 — Verify Current Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 3 — Application B Uses Stale Version

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --update-expression \
    "SET #s = :new_status, #v = #v + :one" \
  --condition-expression \
    "#v = :expected" \
  --expression-attribute-names '{
    "#s": "status",
    "#v": "version"
  }' \
  --expression-attribute-values '{
    ":new_status": {"S": "SHIPPED"},
    ":one": {"N": "1"},
    ":expected": {"N": "1"}
  }' \
  --return-values-on-condition-check-failure ALL_OLD \
  --region "$AWS_REGION"
```

Expected:

```text
ConditionalCheckFailedException
```

### Why Did It Fail?

The condition expects:

```text
version = 1
```

But DynamoDB contains:

```text
version = 2
```

The condition evaluates to false.

### Step 4 — Capture Failure Evidence

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --update-expression \
    "SET #s = :new_status, #v = #v + :one" \
  --condition-expression \
    "#v = :expected" \
  --expression-attribute-names '{
    "#s": "status",
    "#v": "version"
  }' \
  --expression-attribute-values '{
    ":new_status": {"S": "SHIPPED"},
    ":one": {"N": "1"},
    ":expected": {"N": "1"}
  }' \
  --return-values-on-condition-check-failure ALL_OLD \
  --region "$AWS_REGION" \
  > evidence/stale-version-output.json \
  2> evidence/stale-version-error.log

echo "Exit code: $?"
```

### Step 5 — Inspect Error

```bash
cat evidence/stale-version-error.log
```

The CLI may include additional item information in the error output.

---

## 15. Investigate Optimistic Concurrency Conflict

### Step 1 — Retrieve Current Item

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 2 — Compare Expected and Actual Versions

| Component | Version |
|---|---|
| Application B expected | 1 |
| DynamoDB actual | 2 |
| Condition | `version = 1` |
| Evaluation | False |

### Step 3 — Save Data Protection Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/stale-version-protected.json
```

### Step 4 — Verify Stale Update Was Rejected

```bash
jq -e '
  .Item.version.N == "2" and
  .Item.status.S == "PROCESSING"
' evidence/stale-version-protected.json
```

Expected:

```text
true
```

### Investigation Findings

| Component | Result |
|---|---|
| Table | ACTIVE |
| Order | Exists |
| Application Expected Version | 1 |
| Actual Version | 2 |
| Conditional Update | Rejected |
| Existing Changes | Preserved |

### Root Cause

Application B attempted an update using stale application state.

DynamoDB rejected the update to prevent a lost-update conflict.

---

## 16. Remediation 02 — Resolve Stale Version

### Remediation Objective

Read the current order, verify that the intended update is still valid, and issue a new conditional update.

### Step 1 — Inspect Current State

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --query 'Item.{Status:status.S,Version:version.N}' \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Status": "PROCESSING",
  "Version": "2"
}
```

### Step 2 — Retry With Current Version

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --update-expression \
    "SET #s = :new_status, #v = #v + :one" \
  --condition-expression \
    "#v = :expected AND #s = :current_status" \
  --expression-attribute-names '{
    "#s": "status",
    "#v": "version"
  }' \
  --expression-attribute-values '{
    ":new_status": {"S": "SHIPPED"},
    ":current_status": {"S": "PROCESSING"},
    ":one": {"N": "1"},
    ":expected": {"N": "2"}
  }' \
  --return-values ALL_NEW \
  --region "$AWS_REGION"
```

Expected:

```text
Status = SHIPPED
Version = 3
```

### Step 3 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/version-recovered.json
```

### Step 4 — Validate Recovery

```bash
jq -e '
  .Item.version.N == "3" and
  .Item.status.S == "SHIPPED"
' evidence/version-recovered.json
```

Expected:

```text
true
```

### Recovery Summary

| Attribute | Before | After |
|---|---|---|
| Version | 2 | 3 |
| Status | PROCESSING | SHIPPED |
| Condition | Stale | Current |
| Update | Rejected | Successful |
| Data Integrity | Preserved | Preserved |

**Fault 02 resolved through a valid conditional update.**

---

## 17. Fault Injection 03 — Invalid Status Transition

### Production Problem

An outdated application workflow attempts to cancel an order that has already been shipped.

The current order is:

```text
order_id = ORD-6001
status = SHIPPED
version = 3
```

The application attempts cancellation only if the status is PENDING.

### Step 1 — Attempt Invalid Cancellation

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --update-expression \
    "SET #s = :new_status" \
  --condition-expression \
    "#s = :expected_status" \
  --expression-attribute-names '{
    "#s": "status"
  }' \
  --expression-attribute-values '{
    ":new_status": {"S": "CANCELLED"},
    ":expected_status": {"S": "PENDING"}
  }' \
  --region "$AWS_REGION"
```

Expected:

```text
ConditionalCheckFailedException
```

### Step 2 — Capture Failure

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --update-expression \
    "SET #s = :new_status" \
  --condition-expression \
    "#s = :expected_status" \
  --expression-attribute-names '{
    "#s": "status"
  }' \
  --expression-attribute-values '{
    ":new_status": {"S": "CANCELLED"},
    ":expected_status": {"S": "PENDING"}
  }' \
  --region "$AWS_REGION" \
  > evidence/status-condition-output.json \
  2> evidence/status-condition-error.log

echo "Exit code: $?"
```

### Step 3 — Inspect Error

```bash
cat evidence/status-condition-error.log
```

### Step 4 — Verify Original Status Remains

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/status-protected.json
```

### Step 5 — Validate

```bash
jq -e '
  .Item.status.S == "SHIPPED" and
  .Item.version.N == "3"
' evidence/status-protected.json
```

Expected:

```text
true
```

### Root Cause

The order was already SHIPPED.

The requested condition required PENDING.

The condition evaluated to false.

DynamoDB correctly rejected the cancellation.

---

## 18. Remediation 03 — Perform Valid State Transition

### Important Principle

Do not remove the condition and cancel the shipped order merely to produce a successful API response.

The condition represents a business rule.

For this lab, we will cancel ORD-6002, which is still PENDING.

### Step 1 — Verify ORD-6002

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6002"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
status = PENDING
version = 1
```

### Step 2 — Perform Valid Conditional Update

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6002"}}' \
  --update-expression \
    "SET #s = :cancelled, #v = #v + :one" \
  --condition-expression \
    "#s = :pending AND #v = :expected" \
  --expression-attribute-names '{
    "#s": "status",
    "#v": "version"
  }' \
  --expression-attribute-values '{
    ":cancelled": {"S": "CANCELLED"},
    ":pending": {"S": "PENDING"},
    ":one": {"N": "1"},
    ":expected": {"N": "1"}
  }' \
  --return-values ALL_NEW \
  --region "$AWS_REGION"
```

Expected:

```text
status = CANCELLED
version = 2
```

### Step 3 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6002"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/status-recovered.json
```

### Step 4 — Verify

```bash
jq -e '
  .Item.status.S == "CANCELLED" and
  .Item.version.N == "2"
' evidence/status-recovered.json
```

Expected:

```text
true
```

**Fault 03 resolved by preserving the invalid-transition protection and using a valid eligible order.**

---

## 19. Understanding ReturnValuesOnConditionCheckFailure

DynamoDB supports returning an item when a conditional write fails.

This can help investigate the item's current state without always issuing a separate diagnostic read.

### Example

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-6001"}}' \
  --update-expression \
    "SET #s = :new_status" \
  --condition-expression \
    "#v = :expected" \
  --expression-attribute-names '{
    "#s": "status",
    "#v": "version"
  }' \
  --expression-attribute-values '{
    ":new_status": {"S": "PROCESSING"},
    ":expected": {"N": "1"}
  }' \
  --return-values-on-condition-check-failure ALL_OLD \
  --region "$AWS_REGION"
```

The expected version is intentionally stale.

### Possible Result

```text
ConditionalCheckFailedException
```

The service may include the existing item in the failed-condition response.

Depending on the AWS CLI version and output handling, this information may appear in the error details rather than normal stdout.

### Supported Values

| Value | Meaning |
|---|---|
| NONE | Do not return item attributes on condition failure |
| ALL_OLD | Return the item associated with the failed condition |

### Security Consideration

Only request returned item attributes when needed.

Avoid exposing sensitive customer information in application error logs.

---

## 20. Root Cause Analysis

### Incident Summary

The DynamoDB table remained healthy throughout all three faults.

The application attempted writes that did not satisfy the specified conditions.

### Fault Comparison

| Fault | Operation | Condition | Root Cause |
|---|---|---|---|
| Duplicate order | PutItem | attribute_not_exists | Item already exists |
| Stale version | UpdateItem | version = expected | Version mismatch |
| Invalid status | UpdateItem | status = expected | State mismatch |

### Five Whys — Stale Version

**Why 1 — Why did UpdateItem fail?**

DynamoDB returned ConditionalCheckFailedException.

**Why 2 — Why did the condition fail?**

The stored version had changed.

**Why 3 — Why did the application use an outdated version?**

Another process had already updated the order.

**Why 4 — Why did a conflict occur?**

Multiple application processes operated on shared mutable data.

**Why 5 — How can the conflict be handled safely?**

Use optimistic concurrency control, refresh the current item, resolve conflicting changes, and retry conditionally only when the intended operation remains valid.

### Root Cause Diagram

```text
Multiple Application Processes
             |
             v
       Read Shared Item
             |
             v
       One Process Updates
             |
             v
       Item Version Changes
             |
             v
       Another Process Uses
           Stale Version
             |
             v
       Condition Evaluated
             |
             v
            False
             |
             v
ConditionalCheckFailedException
```

### Root Cause Conclusion

The failures came from application-level conditions rather than unavailable database infrastructure.

The appropriate response depends on the conflict.

Some failures require retry after conflict resolution.

Others should remain rejected because they enforce important business rules.

---

## 21. Production Troubleshooting Decision Tree

```text
ConditionalCheckFailedException
             |
             v
       Verify AWS Account
             |
             v
       Verify Table and Key
             |
             v
     Inspect ConditionExpression
             |
             v
       Read Current Item
             |
             v
       Identify Failed Condition
             |
       +-----+-----+
       |           |
       v           v
   Duplicate     State Mismatch
       |           |
       v           v
  Reject or     Inspect Version
  Resolve ID     and Status
                   |
             +-----+-----+
             |           |
             v           v
       Valid Retry     Invalid
             |         Transition
             v           |
       Conditional       v
         Update       Reject Request
             |
             v
       Verify Recovery
```

### Troubleshooting Checklist

| Check | Expected |
|---|---|
| AWS Account | Correct |
| AWS Region | us-east-1 |
| Table | ddb-lab06-orders |
| Table Status | ACTIVE |
| Item Exists | Verified |
| ConditionExpression | Inspected |
| Expected Version | Compared |
| Current Version | Retrieved |
| Expected Status | Compared |
| Current Status | Retrieved |
| Business Rule | Preserved |

---

## 22. CloudWatch Monitoring

Amazon DynamoDB provides a CloudWatch metric named:

```text
ConditionalCheckFailedRequests
```

This metric can help identify increases in conditional write failures.

### Step 1 — Configure Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' \
  '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u \
  '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect Conditional Failures

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConditionalCheckFailedRequests \
  --dimensions Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 3 — Save Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConditionalCheckFailedRequests \
  --dimensions Name=TableName,Value="$TABLE_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION" \
  > evidence/conditional-failures-metrics.json
```

### Monitoring Interpretation

An increase in conditional failures may indicate:

- Duplicate requests.
- Application race conditions.
- High write concurrency.
- Stale cached data.
- Incorrect expected versions.
- Invalid business-state transitions.

However, some conditional failures are expected and desirable.

A production monitoring strategy should distinguish normal business-rule rejection from unexpected application errors.

CloudWatch metric publication may be delayed.

---

## 23. Additional Production Troubleshooting Scenarios

### Scenario 1 — Duplicate Payment Request

A payment-processing application receives the same event twice.

**Solution:** Use an idempotency key and conditional item creation.

### Scenario 2 — Concurrent Inventory Updates

Two customers attempt to purchase the final item.

**Solution:** Use a conditional inventory update that verifies sufficient quantity.

### Scenario 3 — Two Workers Process the Same Job

Two workers attempt to claim a pending job.

**Solution:** Use a conditional update to ensure only one worker successfully claims the job.

### Scenario 4 — Stale Cached Version

An application updates an item using a version retrieved from an outdated cache.

**Solution:** Read the current item and resolve the conflict.

### Scenario 5 — Invalid Order Cancellation

The application attempts to cancel an already shipped order.

**Solution:** Preserve the state-transition condition and reject the invalid operation.

### Scenario 6 — Accidental Item Creation

UpdateItem may create an item under certain circumstances when no matching item exists.

**Solution:** Use `attribute_exists(order_id)` when the operation must modify an existing record only.

### Scenario Summary

| Scenario | Protection |
|---|---|
| Duplicate order | attribute_not_exists |
| Concurrent edits | Version comparison |
| Invalid status change | Status condition |
| Inventory protection | Quantity condition |
| Worker coordination | Conditional state update |
| Update existing only | attribute_exists |

---

## 24. Cloud Security Engineering Considerations

### Data Integrity

Conditional writes help prevent accidental overwrites and invalid data transitions.

### IAM Least Privilege

Applications should receive only the permissions required to read or modify relevant DynamoDB items.

### Prevent Unintended Updates

Use conditions to ensure updates affect only items in an appropriate state.

### Avoid Blind Retries

A conditional failure may represent a genuine business conflict.

Retrying without inspecting the current state can increase costs and repeatedly fail.

### Optimistic Concurrency

Version-based checks help prevent lost updates in distributed systems.

### Audit Application Changes

Use appropriate application logs and CloudTrail configuration to investigate changes.

### Secure Error Logging

Avoid exposing sensitive attributes through diagnostic messages.

### Production Security Principle

**Conditional expressions protect data integrity, while IAM controls authorization. Production systems often need both.**

---

## 25. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| DynamoDB On-Demand | Read and write requests |
| Conditional Writes | Capacity consumed according to DynamoDB rules |
| DynamoDB Storage | Stored items |
| CloudWatch | Applicable monitoring charges |
| IAM | No separate standard IAM role charge |
| AWS CLI | No separate CLI fee |

### Lab Cost Controls

- Use only two small test orders.
- Avoid unbounded retry loops.
- Use on-demand billing.
- Avoid unnecessary table scans.
- Delete the temporary table after testing.

### Important Note

Failed conditional writes can consume write capacity.

Repeatedly retrying a condition that remains false wastes resources without resolving the conflict.

---

## 26. Save Lab Environment and Verify Recovery

### Step 1 — Save Resource Variables

```bash
cat > lab06-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab06-resources.env
```

### Step 2 — Restore Variables When Needed

```bash
source lab06-resources.env
```

### Step 3 — Save Final Orders

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/final-items.json
```

### Step 4 — Validate Expected Final State

```bash
jq -e '
  ([.Items[] | {
    id: .order_id.S,
    status: .status.S,
    version: .version.N
  }] | sort_by(.id)) ==
  [
    {"id":"ORD-6001","status":"SHIPPED","version":"3"},
    {"id":"ORD-6002","status":"CANCELLED","version":"2"}
  ]
' evidence/final-items.json
```

Expected:

```text
true
```

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

| Item | Initial State | Final State |
|---|---|---|
| ORD-6001 | PENDING, v1 | SHIPPED, v3 |
| ORD-6002 | PENDING, v1 | CANCELLED, v2 |
| Duplicate Attempt | Rejected | Original preserved |
| Stale Update | Rejected | Latest version preserved |
| Invalid Cancellation | Rejected | Shipped order protected |

This verification assumes the dedicated lab table contains only the two intended orders.

---

## 27. AWS Resource Cleanup

**Warning:** Delete only the disposable DynamoDB table created for Lab 06.

### Step 1 — Verify Table

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

### Step 2 — Verify Project Tag

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab06
```

### Step 3 — Review Test Items

```bash
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Confirm the records are disposable.

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

The error is expected after intentional deletion.

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| Test Orders | Deleted with table |
| IAM Roles | None created |
| EC2 | None created |
| Lambda | None created |
| NAT Gateway | None created |
| Local JSON Files | Retained |
| Local Evidence | Retained |

---

## 28. Interview Questions and Answers

### Q1. What causes ConditionalCheckFailedException?

DynamoDB returns this error when a conditional write's ConditionExpression evaluates to false.

### Q2. What does attribute_not_exists do?

It checks whether an attribute does not exist.

It is commonly used to prevent duplicate item creation.

### Q3. Why is conditional PutItem useful?

It prevents an application from accidentally replacing an existing item when the specified condition requires that the item does not already exist.

### Q4. What is optimistic concurrency control?

A technique that allows updates only when the stored version matches the version expected by the application.

### Q5. What is a version attribute?

An attribute that tracks changes to an item and supports conflict detection.

### Q6. What is a lost-update problem?

A situation where one application's write overwrites changes made by another application without recognizing the conflict.

### Q7. How do conditional writes prevent lost updates?

They reject writes that use outdated expected values.

### Q8. What does ReturnValuesOnConditionCheckFailure do?

It can return the existing item when a conditional write fails, helping with investigation.

### Q9. Should a conditional failure always be retried?

No. Some failures represent genuine conflicts or business-rule violations.

### Q10. How should applications handle stale versions?

Read the current state, resolve the conflict, and retry conditionally only when the intended update is still valid.

### Q11. Can conditional expressions validate business-state transitions?

Yes. For example, an application can allow cancellation only when the current status is PENDING.

### Q12. What happens when a condition evaluates to false?

The requested write is rejected.

### Q13. Is ConditionalCheckFailedException always a database problem?

No. It often indicates that DynamoDB correctly enforced a data-integrity condition.

### Q14. Can CloudWatch monitor conditional write failures?

Yes. The ConditionalCheckFailedRequests metric provides useful operational context.

### Q15. What is the difference between IAM and conditional expressions?

IAM controls authorization. Conditional expressions control whether a write is valid for the current item state.

### Q16. Can failed conditional writes consume capacity?

Yes. DynamoDB can charge capacity for evaluating failed conditional writes.

### Q17. Why are conditional writes useful in distributed systems?

They help coordinate concurrent writers and prevent unintended changes.

### Q18. How would you explain this lab in a technical interview?

I created a DynamoDB table using AWS CLI and inserted two test orders.

First, I reproduced ConditionalCheckFailedException using a duplicate PutItem request with attribute_not_exists.

The condition prevented the duplicate request from overwriting the existing order.

Next, I simulated a stale version update using optimistic concurrency control.

One application advanced the order from version 1 to version 2, while another attempted to update the item using the outdated version 1.

DynamoDB rejected the stale update.

I investigated the current item state and corrected the update using the current version.

Finally, I attempted an invalid cancellation of an already shipped order.

DynamoDB rejected the request because the status was not PENDING.

I then demonstrated a valid cancellation using an eligible pending order.

I verified the final order statuses and versions, reviewed CloudWatch metrics, and cleaned up the temporary DynamoDB table.

This lab helped me understand conditional writes, optimistic concurrency, data-integrity protection, and production incident troubleshooting.

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
│   ├── README.md
│   ├── .gitignore
│   ├── order-6001.json
│   ├── duplicate-order.json
│   ├── order-6002.json
│   ├── lab06-resources.env
│   │
│   └── evidence/
│       ├── table-description.json
│       ├── healthy-order.json
│       ├── duplicate-output.json
│       ├── duplicate-error.log
│       ├── duplicate-protection.json
│       ├── stale-version-output.json
│       ├── stale-version-error.log
│       ├── stale-version-protected.json
│       ├── version-recovered.json
│       ├── status-condition-output.json
│       ├── status-condition-error.log
│       ├── status-protected.json
│       ├── status-recovered.json
│       ├── conditional-failures-metrics.json
│       └── final-items.json
│
├── 07-gsi-query-not-returning-results/
├── 08-dynamodb-streams-not-triggering/
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

The structure represents the intended lab files. Generated evidence files exist only after the corresponding commands have been executed.

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Production troubleshooting documentation |
| .gitignore | Excludes local evidence and configuration |
| order-6001.json | Initial test order |
| duplicate-order.json | Duplicate creation fault |
| order-6002.json | Additional eligible order |
| lab06-resources.env | Local AWS variables |
| table-description.json | Table configuration |
| healthy-order.json | Healthy baseline |
| duplicate-error.log | Duplicate request error |
| duplicate-protection.json | Original item protection evidence |
| stale-version-error.log | Optimistic-locking failure |
| stale-version-protected.json | Stale update protection |
| version-recovered.json | Version conflict recovery |
| status-condition-error.log | Invalid transition error |
| status-protected.json | Shipped order protection |
| status-recovered.json | Successful cancellation |
| conditional-failures-metrics.json | CloudWatch conditional failure metrics |
| final-items.json | Final recovery verification |

### Recommended Public GitHub Structure

```text
06-conditional-check-failed/
├── README.md
├── .gitignore
├── order-6001.json
├── duplicate-order.json
└── order-6002.json
```

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 06
06-conditional-check-failed/evidence/
06-conditional-check-failed/lab06-resources.env

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

Do not commit real customer data, credentials, or unreviewed account-specific evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how DynamoDB conditional expressions protect application data from unintended writes.

We created a DynamoDB table with a String partition key and inserted an initial test order.

First, we attempted to create a duplicate order using a conditional PutItem request.

DynamoDB rejected the request with ConditionalCheckFailedException because the item already existed.

We verified that the original order amount remained unchanged.

Next, we simulated a stale version update.

One application successfully updated an order from version 1 to version 2.

Another application attempted an update while still expecting version 1.

DynamoDB rejected the outdated request and preserved the latest changes.

We investigated the stored version, resolved the conflict, and successfully updated the order to version 3.

Finally, we simulated an invalid cancellation of an already shipped order.

The conditional status check rejected the request and prevented an invalid state transition.

We demonstrated a valid cancellation using a different order in PENDING status.

After completing the recovery tests, we reviewed CloudWatch monitoring, optimistic locking, IAM least privilege, data-integrity protection, cost management, and resource cleanup.

**Key Lesson:** ConditionalCheckFailedException does not necessarily indicate a DynamoDB outage. It often means that DynamoDB correctly prevented a duplicate write, stale update, or invalid business-state transition.

### Skills Demonstrated

- Amazon DynamoDB.
- Conditional PutItem.
- Conditional UpdateItem.
- GetItem.
- ConditionExpression.
- attribute_not_exists.
- attribute_exists.
- Optimistic concurrency control.
- Version attributes.
- Lost-update prevention.
- Business-state validation.
- ReturnValuesOnConditionCheckFailure.
- CloudWatch monitoring.
- AWS CLI v2.
- Linux Bash.
- jq.
- Root cause analysis.
- Production incident troubleshooting.
- Data-integrity protection.
- IAM least privilege.
- Secure remediation.
- Recovery verification.
- AWS resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-006 |
| Scenario | ConditionalCheckFailedException |
| Table | ddb-lab06-orders |
| Region | us-east-1 |
| Partition Key | order_id |
| Billing Mode | PAY_PER_REQUEST |
| Initial Order | ORD-6001 |
| Fault 01 | Duplicate PutItem |
| Fault 01 Result | ConditionalCheckFailedException |
| Fault 01 Protection | Original item preserved |
| Fault 02 | Stale version update |
| Fault 02 Result | ConditionalCheckFailedException |
| Fault 02 Remediation | Retry with current version after conflict review |
| Fault 03 | Invalid status transition |
| Fault 03 Result | ConditionalCheckFailedException |
| Fault 03 Remediation | Reject invalid transition and update eligible order |
| Final ORD-6001 Status | SHIPPED |
| Final ORD-6001 Version | 3 |
| Final ORD-6002 Status | CANCELLED |
| Final ORD-6002 Version | 2 |
| Cleanup | DynamoDB table deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Production DynamoDB applications should use conditional writes to protect data integrity, prevent duplicate item creation, detect stale updates, and enforce valid business-state transitions. Engineers must investigate why a condition failed before deciding whether to retry, reject, or resolve the operation.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [DynamoDB Condition Expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)
- [AWS CLI — PutItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/put-item.html)
- [AWS CLI — UpdateItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/update-item.html)
- [AWS CLI — GetItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-item.html)
- [DynamoDB Optimistic Locking](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBMapper.OptimisticLocking.html)
- [DynamoDB Update Expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html)
- [DynamoDB Expression Attribute Names](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ExpressionAttributeNames.html)
- [DynamoDB CloudWatch Metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)