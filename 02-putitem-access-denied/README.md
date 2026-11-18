# Lab 02 — Amazon DynamoDB PutItem AccessDenied

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an Amazon DynamoDB `AccessDeniedException` caused by a restrictive resource-based policy.

In a production environment, applications frequently use DynamoDB to store orders, customer records, session data, configuration information, and application events.

These applications require appropriate IAM authorization to perform operations such as `GetItem`, `PutItem`, `UpdateItem`, and `DeleteItem`.

If the application lacks permission or an applicable policy explicitly denies access, DynamoDB can reject the operation.

Example:

```text
An error occurred (AccessDeniedException)
when calling the PutItem operation
```

In this lab, we deploy a DynamoDB table named `ddb-lab02-orders` in the `us-east-1` Region.

The table uses `order_id` as its partition key and on-demand billing.

We first insert an order and verify successful retrieval, establishing a healthy baseline.

Next, we intentionally attach a resource-based policy that explicitly denies `dynamodb:PutItem` for principals in our AWS account.

We attempt another PutItem operation and reproduce `AccessDeniedException`.

We then investigate the current AWS identity, table ARN, resource-based policy, and IAM authorization behavior.

After identifying the explicit deny, we remove the restrictive lab policy.

Finally, we repeat the write operation, verify that DynamoDB stores the item, and clean up the temporary AWS resources.

This lab emphasizes production troubleshooting, IAM least privilege, AWS security policy evaluation, and safe incident remediation.

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
Insert Baseline Order
          |
          v
Verify GetItem Success
          |
          v
Inspect Resource Policy
          |
          v
Create Explicit Deny Policy
          |
          v
Attach Policy to DynamoDB Table
          |
          v
Attempt PutItem
          |
          v
AccessDeniedException
          |
          v
Verify Existing Item Still Readable
          |
          v
Inspect IAM Identity and Table Policy
          |
          v
Identify Explicit Deny
          |
          v
Remove Restrictive Policy
          |
          v
Retry PutItem
          |
          v
Verify New Item Exists
          |
          v
Review CloudTrail and Security
          |
          v
Clean Up Lab Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-002 |
| Lab Name | DynamoDB PutItem AccessDenied |
| Difficulty | Intermediate |
| Primary Service | Amazon DynamoDB |
| Supporting Services | AWS IAM, STS, CloudTrail |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, jq |
| Table Name | `ddb-lab02-orders` |
| Partition Key | `order_id` |
| Partition Key Type | String |
| Billing Mode | PAY_PER_REQUEST |
| Healthy Operation | PutItem, GetItem |
| Broken Operation | PutItem |
| Expected Error | AccessDeniedException |
| Fault Injection | Resource-based explicit deny |
| Denied Action | `dynamodb:PutItem` |
| Policy Condition | `aws:PrincipalAccount` |
| Protected Resource | Lab 02 table ARN |
| Initial Test Item | `ORD-2001` |
| Rejected Test Item | `ORD-2003` |
| Remediation | Delete restrictive resource policy |
| Recovery Verification | Successful PutItem and GetItem |
| Resource Tag | `DynamoDB-Troubleshooting-Lab02` |
| Cleanup | DynamoDB table and policy |

### Learning Objectives

- Understand DynamoDB authorization.
- Understand PutItem and GetItem.
- Understand IAM identity-based policies.
- Understand DynamoDB resource-based policies.
- Understand explicit and implicit denies.
- Understand AWS policy evaluation.
- Identify the AWS principal making a request.
- Investigate AccessDeniedException.
- Inspect resource-based policies.
- Apply and remove DynamoDB resource policies.
- Reproduce authorization failures.
- Understand eventual consistency of policy updates.
- Preserve existing data during troubleshooting.
- Apply least-privilege security practices.
- Verify successful remediation.
- Investigate CloudTrail management events.
- Safely remove temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-processing application that writes customer orders to Amazon DynamoDB.

The application uses:

```text
Table: ddb-lab02-orders
Region: us-east-1
Operation: PutItem
```

Under normal conditions, the application writes orders successfully.

Example:

```json
{
  "order_id": "ORD-2001",
  "customer": "Rahim",
  "status": "Processing",
  "amount": 150
}
```

During a security configuration change, a restrictive resource-based policy is attached to the DynamoDB table.

The policy explicitly denies:

```text
dynamodb:PutItem
```

The application can still read existing orders, but it can no longer insert new records.

The application begins reporting:

```text
AccessDeniedException
```

Developers initially suspect a DynamoDB service problem.

The Cloud Security Engineer investigates the issue and discovers:

- The DynamoDB table exists.
- The table status is ACTIVE.
- The AWS account is correct.
- The Region is correct.
- The table ARN is correct.
- Existing items remain readable.
- PutItem requests are denied.
- A resource-based policy explicitly denies PutItem.

The engineer identifies the resource-policy deny as the root cause.

After removing the unintended deny, the application successfully writes new orders again.

### Incident Symptoms

- PutItem returns AccessDeniedException.
- GetItem continues working.
- The DynamoDB table remains ACTIVE.
- Existing data is preserved.
- IAM identity-based permissions were not changed.
- The table resource policy contains an explicit deny.
- Removing the deny restores write operations.

### Business Impact

A PutItem authorization failure may cause:

- Failed order creation.
- Failed transactions.
- Interrupted workflows.
- Application errors.
- Failed background jobs.
- Delayed customer operations.
- Increased support tickets.
- Data ingestion failures.
- Reduced application availability.

### Incident Objective

Identify the authorization policy responsible for rejecting DynamoDB writes.

Restore the intended application access without granting unnecessary permissions or weakening unrelated security controls.

---

## 3. AWS Architecture

### Healthy Architecture

```text
              Order Application
                     |
                     v
                 AWS CLI
                     |
                     v
              AWS Credentials
                     |
                     v
             IAM Authorization
                     |
                     v
             PutItem Allowed
                     |
                     v
              Amazon DynamoDB
                     |
                     v
             ddb-lab02-orders
                     |
                     v
                Item Stored
                     |
                     v
              GetItem Success
```

### Broken Architecture

```text
              Order Application
                     |
                     v
              PutItem Request
                     |
                     v
               DynamoDB Table
                     |
                     v
             Resource-Based Policy
                     |
                     v
             Explicit PutItem Deny
                     |
                     v
             IAM Policy Evaluation
                     |
                     v
              AccessDeniedException
                     |
                     v
                 Write Rejected
```

### Recovered Architecture

```text
              Order Application
                     |
                     v
              PutItem Request
                     |
                     v
             IAM Policy Evaluation
                     |
                     v
              Restrictive Deny Removed
                     |
                     v
             Existing Allow Applies
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

### AWS Components

| Component | Purpose |
|---|---|
| Amazon DynamoDB | Stores application orders |
| DynamoDB Table | Resource protected by IAM policies |
| PutItem | Writes items |
| GetItem | Retrieves items |
| IAM | Evaluates access permissions |
| Resource-Based Policy | Controls access to a table |
| AWS STS | Identifies the calling principal |
| AWS CloudTrail | Provides audit evidence where configured |
| AWS CLI | Creates, modifies, and investigates resources |
| Linux Bash | Configures environment and captures evidence |
| jq | Generates and analyzes JSON |

---

## 4. Understanding DynamoDB PutItem

`PutItem` creates an item or replaces an existing item with the same primary key.

Example:

```bash
aws dynamodb put-item \
  --table-name ddb-lab02-orders \
  --item '{
    "order_id": {"S": "ORD-2001"},
    "customer": {"S": "Rahim"}
  }'
```

### Required Authorization

The caller must be authorized to perform:

```text
dynamodb:PutItem
```

against the target DynamoDB table.

### DynamoDB Operations

| Operation | Required Action |
|---|---|
| PutItem | `dynamodb:PutItem` |
| GetItem | `dynamodb:GetItem` |
| UpdateItem | `dynamodb:UpdateItem` |
| DeleteItem | `dynamodb:DeleteItem` |
| Query | `dynamodb:Query` |
| Scan | `dynamodb:Scan` |
| DescribeTable | `dynamodb:DescribeTable` |

An application may have permission to read from DynamoDB without having permission to write.

### Important Data Protection Note

PutItem can replace an existing item if no condition prevents replacement.

Production applications should use conditional expressions when they need to prevent accidental overwrites.

---

## 5. Understanding IAM Authorization

AWS IAM determines whether a principal is authorized to perform a requested action on a resource.

### Identity-Based Policies

Identity-based policies attach permissions to IAM users, groups, or roles.

Example:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dynamodb:PutItem",
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/ddb-lab02-orders"
    }
  ]
}
```

The account number is illustrative.

### Resource-Based Policies

DynamoDB supports resource-based policies that attach permissions directly to supported DynamoDB resources.

These policies can allow or deny applicable principals and actions.

### Explicit Deny

An applicable explicit deny overrides an allow.

```text
IAM Identity-Based Allow
          |
          v
Resource-Based Explicit Deny
          |
          v
Access Denied
```

### Implicit Deny

If a request lacks a required applicable allow, IAM denies access by default.

### Explicit vs. Implicit Deny

| Type | Meaning |
|---|---|
| Implicit Deny | No sufficient applicable allow |
| Explicit Deny | A policy explicitly rejects the action |
| Explicit Deny Priority | Overrides applicable allows |

### Other Authorization Controls

Production access may also depend on:

- Permissions boundaries.
- Session policies.
- Service control policies.
- Resource control policies.
- VPC endpoint policies.
- Relevant resource-based policies.

For this lab, the specific fault is an explicit deny attached directly to the DynamoDB table.

---

## 6. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- jq.
- AWS account.
- DynamoDB resource-policy management permissions.

### Relevant AWS Permissions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:ListTagsOfResource
dynamodb:PutItem
dynamodb:GetItem
dynamodb:PutResourcePolicy
dynamodb:GetResourcePolicy
dynamodb:DeleteResourcePolicy
dynamodb:DeleteTable
```

These are relevant actions rather than a complete deployable IAM policy.

### Safety Requirements

- Use a dedicated temporary table.
- Do not modify production IAM policies.
- Do not attach the deny to shared resources.
- Review the policy before applying it.
- Verify the table ARN.
- Keep the denied action limited to PutItem.
- Do not deny table-policy recovery actions.
- Preserve existing table data.
- Remove the policy after the test.
- Confirm resource tags before cleanup.

### Important Warning

The fault-injection policy intentionally prevents same-account principals from writing to the lab table.

It must not be attached to a production table.

---

## 7. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 02-putitem-access-denied

cd 02-putitem-access-denied
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

export TABLE_NAME="ddb-lab02-orders"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab02"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"
```

### Step 4 — Verify Variables

```bash
echo "$AWS_REGION"
echo "$TABLE_NAME"
echo "$TABLE_ARN"
```

### Step 5 — Prepare Evidence Directory

```bash
mkdir -p evidence
```

### Step 6 — Configure `.gitignore`

```bash
cat > .gitignore <<'EOF'
evidence/
lab02-resources.env
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

## 8. Verify AWS Identity and Resources

### Step 1 — Identify the Caller

```bash
aws sts get-caller-identity
```

Verify the account ID before continuing.

### Step 2 — Inspect Existing Tables

```bash
aws dynamodb list-tables \
  --region "$AWS_REGION" \
  --output table
```

### Step 3 — Check Whether the Lab Table Exists

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Before creating the table, the expected error is:

```text
ResourceNotFoundException
```

If a table already exists, verify ownership before proceeding.

### Step 4 — Verify Intended ARN

```bash
echo "$TABLE_ARN"
```

Expected format:

```text
arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/ddb-lab02-orders
```

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

### Configuration Explanation

| Parameter | Purpose |
|---|---|
| `--table-name` | Specifies DynamoDB table |
| `AttributeType=S` | String partition key |
| `KeyType=HASH` | Partition key |
| `PAY_PER_REQUEST` | On-demand billing |
| Project tag | Identifies lab resource |

### Step 2 — Wait for ACTIVE State

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
  "Name": "ddb-lab02-orders",
  "Status": "ACTIVE"
}
```

The full output also contains the actual table ARN.

### Step 4 — Verify Tags

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab02
```

---

## 10. Establish Healthy PutItem Baseline

### Step 1 — Insert Order ORD-2001

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-2001"},
    "customer": {"S": "Rahim"},
    "status": {"S": "Processing"},
    "amount": {"N": "150"}
  }' \
  --region "$AWS_REGION"
```

Expected: successful operation without an authorization error.

### Step 2 — Retrieve the Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-2001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Item": {
    "order_id": {"S": "ORD-2001"},
    "customer": {"S": "Rahim"},
    "status": {"S": "Processing"},
    "amount": {"N": "150"}
  }
}
```

Attribute ordering can differ.

### Step 3 — Save Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-2001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/healthy-get-item.json
```

### Step 4 — Validate Item

```bash
jq -e '.Item.order_id.S == "ORD-2001"' \
  evidence/healthy-get-item.json
```

Expected:

```text
true
```

### Healthy Baseline Findings

| Check | Expected Result |
|---|---|
| Table | Exists |
| Table Status | ACTIVE |
| PutItem | Successful |
| GetItem | Successful |
| Existing IAM Authorization | Allows write |
| Resource-Based Deny | Not applied |

---

## 11. Inspect Existing DynamoDB Resource Policy

### Step 1 — Retrieve Resource Policy

```bash
aws dynamodb get-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

For a new table with no resource-based policy, expected:

```text
PolicyNotFoundException
```

### Step 2 — Understand the Result

A missing resource policy is not automatically a security problem.

The caller can still receive authorization through its identity-based permissions and other applicable controls.

### Step 3 — Verify No Existing Policy Is Overwritten

If the table already has a resource policy, stop and review its ownership.

Do not replace an existing production policy just to reproduce this incident.

---

## 12. Fault Injection — Create Explicit Deny Policy

### Step 1 — Create `deny-putitem-policy.json`

```bash
jq -n \
  --arg account "$ACCOUNT_ID" \
  --arg table "$TABLE_ARN" \
  '{
    Version: "2012-10-17",
    Statement: [
      {
        Sid: "Lab02DenyPutItem",
        Effect: "Deny",
        Principal: "*",
        Action: "dynamodb:PutItem",
        Resource: $table,
        Condition: {
          StringEquals: {
            "aws:PrincipalAccount": $account
          }
        }
      }
    ]
  }' > deny-putitem-policy.json
```

### Step 2 — Inspect Generated Policy

```bash
jq . deny-putitem-policy.json
```

Example structure:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Lab02DenyPutItem",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "dynamodb:PutItem",
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/ddb-lab02-orders",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalAccount": "123456789012"
        }
      }
    }
  ]
}
```

Use the account number generated by your environment.

### Policy Explanation

| Field | Value | Meaning |
|---|---|---|
| Sid | Lab02DenyPutItem | Statement identifier |
| Effect | Deny | Rejects matching action |
| Principal | `*` | Matches principals subject to condition |
| Action | dynamodb:PutItem | Only PutItem |
| Resource | Lab 02 table ARN | Specific table |
| Condition | aws:PrincipalAccount | Restricts matching to specified account |

The wildcard Principal does not grant access because this is a Deny statement.

### Step 3 — Validate the Action Scope

Confirm that the policy does not deny:

```text
dynamodb:GetItem
dynamodb:DeleteResourcePolicy
dynamodb:DeleteTable
```

The policy should only deny:

```text
dynamodb:PutItem
```

---

## 13. Attach Resource-Based Policy

### Step 1 — Apply the Deny

```bash
aws dynamodb put-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --policy file://deny-putitem-policy.json \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Applied Policy

```bash
aws dynamodb get-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq .
```

Look for:

```text
Sid = Lab02DenyPutItem
Effect = Deny
Action = dynamodb:PutItem
```

### Step 3 — Save Policy Evidence

```bash
aws dynamodb get-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION" \
  > evidence/deny-policy-attached.json
```

### Important: Eventual Consistency

DynamoDB resource-policy updates are eventually consistent.

The policy may not be immediately visible or effective after the API call.

A GetResourcePolicy request may temporarily report the previous policy or PolicyNotFoundException.

Verify policy propagation before concluding that fault injection failed.

---

## 14. Reproduce AccessDeniedException

### Step 1 — Attempt a New PutItem

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-2002"},
    "customer": {"S": "Karim"},
    "status": {"S": "Pending"},
    "amount": {"N": "250"}
  }' \
  --region "$AWS_REGION"
```

Expected after policy propagation:

```text
An error occurred (AccessDeniedException)
when calling the PutItem operation
```

If the request succeeds immediately after the policy was attached, allow the policy to propagate and test again with a bounded number of attempts.

### Step 2 — Save Failure Evidence

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-2003"},
    "customer": {"S": "Test"},
    "status": {"S": "Pending"}
  }' \
  --region "$AWS_REGION" \
  > evidence/access-denied-output.json \
  2> evidence/access-denied-error.log

echo "Exit code: $?"
```

Expected: a nonzero exit code.

### Step 3 — Inspect Error

```bash
cat evidence/access-denied-error.log
```

### Step 4 — Identify the Denied Operation

The error concerns:

```text
dynamodb:PutItem
```

The table still exists, but the request is not authorized.

### Broken-State Findings

| Component | Expected Result |
|---|---|
| Table | ACTIVE |
| Table ARN | Correct |
| AWS Region | Correct |
| PutItem | AccessDeniedException |
| GetItem | Remains available |
| Resource-Based Policy | Explicit deny |
| Root Cause | Authorization policy |

---

## 15. Verify Read Operations Still Work

### Step 1 — Read the Baseline Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-2001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected: ORD-2001 is returned.

### Step 2 — Verify Rejected Order Is Missing

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-2003"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

If the PutItem request was rejected, expected output has no Item field.

Example:

```json
{}
```

### Step 3 — Save Read Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-2001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/read-still-works.json
```

### Why This Matters

The application can still read existing data.

The failure is isolated to the write operation.

This supports the diagnosis that a PutItem-specific permission is being denied.

---

## 16. Investigate AWS Principal and Table

### Step 1 — Identify the Caller

```bash
aws sts get-caller-identity
```

### Step 2 — Verify Table Status

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
Status = ACTIVE
```

### Step 3 — Verify the Table ARN

```bash
echo "$TABLE_ARN"
```

### Step 4 — Compare Resource Policy

```bash
aws dynamodb get-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq \
  '.Statement[] | select(.Effect == "Deny")'
```

### Step 5 — Confirm the Relevant Action

Look for:

```text
Action: dynamodb:PutItem
Effect: Deny
```

### Investigation Finding

The current caller can read the table but cannot write because the table resource-based policy explicitly denies PutItem for matching principals.

---

## 17. Understand the IAM Evaluation Result

### Before Fault Injection

```text
Identity-Based Permission
          |
          v
PutItem Allowed
          |
          v
Resource Policy Has No Deny
          |
          v
Write Successful
```

### After Fault Injection

```text
Identity-Based Allow
          |
          v
Resource-Based Explicit Deny
          |
          v
Explicit Deny Takes Precedence
          |
          v
AccessDeniedException
```

### IAM Evaluation Summary

| Policy Type | Effect |
|---|---|
| Identity-based policy | May allow PutItem |
| Resource-based policy | Explicitly denies PutItem |
| IAM evaluation | Deny |
| DynamoDB result | AccessDeniedException |

### Production Lesson

Adding an Allow policy does not override an applicable explicit deny.

The appropriate remediation is determined by whether the deny is intentional.

For this controlled incident, the deny is unintended and must be removed.

---

## 18. Root Cause Analysis

### Root Cause

A resource-based policy attached to the DynamoDB table explicitly denied `dynamodb:PutItem`.

Although the caller was previously authorized to perform PutItem, the new explicit deny overrode the existing allow.

### Root Cause Diagram

```text
Security Configuration Change
          |
          v
PutResourcePolicy
          |
          v
Lab02DenyPutItem Statement
          |
          v
Effect = Deny
          |
          v
Action = dynamodb:PutItem
          |
          v
Application Sends PutItem
          |
          v
IAM Authorization Evaluation
          |
          v
AccessDeniedException
```

### Five Whys

**Why 1 — Why did PutItem fail?**

DynamoDB returned AccessDeniedException.

**Why 2 — Why was PutItem denied?**

A table resource-based policy explicitly denied the action.

**Why 3 — Why did the deny override the existing permission?**

AWS IAM gives applicable explicit denies precedence over allows.

**Why 4 — Why was the restrictive policy present?**

The simulated security configuration introduced it.

**Why 5 — How can the incident be prevented?**

Review resource-policy changes, validate application permissions, maintain policy version control, and test critical database operations after security deployments.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-DDB-002 |
| Error | AccessDeniedException |
| Operation | PutItem |
| Table | ddb-lab02-orders |
| Region | us-east-1 |
| Table Status | ACTIVE |
| Existing Data | Readable |
| Policy Type | Resource-based |
| Denied Action | dynamodb:PutItem |
| Root Cause | Explicit deny |
| Remediation | Remove unintended policy |

---

## 19. Remediation — Remove Restrictive Policy

### Step 1 — Verify Target Table

```bash
echo "$TABLE_NAME"
echo "$TABLE_ARN"
```

Confirm:

```text
ddb-lab02-orders
```

### Step 2 — Review Policy One Final Time

```bash
aws dynamodb get-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq .
```

Confirm that the policy is the one created for the lab.

### Step 3 — Delete Resource Policy

```bash
aws dynamodb delete-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

### Step 4 — Verify Removal

```bash
aws dynamodb get-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Expected after propagation:

```text
PolicyNotFoundException
```

### Step 5 — Do Not Broaden IAM Permissions

Do not attach AdministratorAccess or grant `dynamodb:*` to remediate this incident.

The initial successful PutItem demonstrated that the application already had suitable authorization before the deny was attached.

---

## 20. Verify Successful PutItem Recovery

### Step 1 — Retry the Write

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-2003"},
    "customer": {"S": "Test"},
    "status": {"S": "Pending"}
  }' \
  --region "$AWS_REGION"
```

Expected: success without AccessDeniedException.

If the deny was just removed and the request still fails, verify policy propagation and other applicable authorization controls.

### Step 2 — Retrieve New Order

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-2003"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Item": {
    "order_id": {"S": "ORD-2003"},
    "customer": {"S": "Test"},
    "status": {"S": "Pending"}
  }
}
```

### Step 3 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-2003"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-putitem.json
```

### Step 4 — Validate

```bash
jq -e '.Item.order_id.S == "ORD-2003"' \
  evidence/recovered-putitem.json
```

Expected:

```text
true
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| Table Status | ACTIVE | ACTIVE |
| Region | Correct | Correct |
| GetItem | Successful | Successful |
| PutItem | AccessDeniedException | Successful |
| Resource Policy | Explicit deny | Removed |
| Existing Data | Preserved | Preserved |
| IAM Identity Policy | Unchanged | Unchanged |

---

## 21. Additional Investigation — Identity-Based Policy

A real production AccessDeniedException may originate from missing identity-based permissions.

### Example Least-Privilege Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowOrderWrites",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/ddb-lab02-orders"
    }
  ]
}
```

Replace the example ARN with the correct production resource ARN when designing an actual permission policy.

This policy is for illustration only; it is not required to complete the lab.

### Investigation Checklist

Verify:

- The principal making the request.
- Its IAM role or user.
- Applicable identity-based permissions.
- The table ARN.
- Any explicit deny.
- Permissions boundaries.
- Session policies.
- Organization-level controls.
- DynamoDB resource-based policies.

### Important Distinction

An implicit deny caused by a missing allow and an explicit deny caused by a restrictive policy require different remediation strategies.

---

## 22. Additional Investigation — CloudTrail

CloudTrail can help identify who made changes to DynamoDB policies.

Relevant management events include:

```text
PutResourcePolicy
DeleteResourcePolicy
CreateTable
DeleteTable
```

### Example — Investigate Policy Changes

```bash
aws cloudtrail lookup-events \
  --lookup-attributes \
    AttributeKey=EventName,AttributeValue=PutResourcePolicy \
  --max-results 20 \
  --region "$AWS_REGION"
```

This requires `cloudtrail:LookupEvents` and suitable CloudTrail event visibility.

Inspect event time, user identity, event source, and affected resource.

### PutItem Data Events

DynamoDB item operations such as PutItem are data events.

Their presence in CloudTrail depends on whether appropriate data-event logging was configured.

Do not assume that every DynamoDB write attempt appears automatically in CloudTrail event history.

---

## 23. Additional Troubleshooting Scenarios

### Scenario 1 — Missing PutItem Allow

**Symptom:** AccessDeniedException even though no explicit deny exists.

**Investigation:** Inspect the application's identity-based permissions.

**Remediation:** Grant only the required action on the intended resource, if the access is authorized.

### Scenario 2 — Incorrect Table ARN

**Symptom:** A policy grants PutItem, but requests still fail.

**Investigation:** Compare the actual table ARN with the policy resource.

**Remediation:** Correct the authorized resource reference.

### Scenario 3 — Organization SCP Deny

**Symptom:** Identity and resource policies appear to allow access, but requests remain denied.

**Investigation:** Check applicable AWS Organizations service control policies.

**Remediation:** Follow the organization's security approval process.

### Scenario 4 — Resource Policy Deny

**Symptom:** The application could write before a resource-policy change but cannot afterward.

**Investigation:** Inspect the table's resource-based policy.

**Remediation:** Correct the unintended deny without weakening unrelated restrictions.

### Scenario 5 — Wrong AWS Account

**Symptom:** The application uses an unexpected identity or account.

**Investigation:**

```bash
aws sts get-caller-identity
```

**Remediation:** Correct the application's AWS profile or role configuration.

### Scenario 6 — Wrong AWS Region

**Symptom:** DynamoDB cannot find the intended table.

**Investigation:** Verify the configured Region and table ARN.

**Remediation:** Use the correct regional endpoint.

### Scenario 7 — Invalid Item Structure

**Symptom:** PutItem fails with ValidationException.

**Investigation:** Inspect the table key schema and request attribute types.

**Remediation:** Correct the request payload.

### Scenario Comparison

| Error | Likely Investigation |
|---|---|
| AccessDeniedException | IAM and resource policies |
| ResourceNotFoundException | Table, Region, account, index |
| ValidationException | Request and schema |
| ConditionalCheckFailedException | ConditionExpression |
| ProvisionedThroughputExceededException | Capacity and throttling |

---

## 24. Cloud Security Engineering Considerations

### IAM Least Privilege

Applications should receive only the permissions required for their operations.

For example, an order-writing service may require PutItem but not DeleteTable.

### Understand Explicit Deny

An explicit deny overrides an allow.

Cloud Security Engineers must understand policy evaluation before making changes.

### Protect Production Databases

Never attach experimental deny policies to shared production tables.

### Review Resource Policies

Policy changes should be reviewed, version-controlled, and tested.

### Use Infrastructure as Code

Manage DynamoDB permissions through Terraform or CloudFormation where appropriate.

### Audit Security Changes

Use CloudTrail and organizational monitoring to investigate policy modifications.

### Protect Data Integrity

Access-control changes should not unnecessarily alter existing database items.

### Avoid Overprivileged Remediation

Granting broad permissions can conceal the original problem and introduce security risks.

### Security Principle

**Correct the policy responsible for the failure rather than bypassing authorization controls.**

---

## 25. Cost Management

### Potential Charges

| AWS Resource | Cost Consideration |
|---|---|
| DynamoDB Table | Storage and requests |
| DynamoDB On-Demand | Read/write usage |
| CloudTrail | Applicable trail and data-event charges |
| CloudWatch | Applicable monitoring charges |
| AWS CLI | No separate CLI usage charge |
| IAM | No separate standard role charge |

### Cost Optimization

- Use on-demand capacity.
- Store only fabricated test records.
- Limit repeated requests.
- Do not create unnecessary AWS services.
- Remove temporary policies.
- Delete the test table after completing the lab.

### Important Note

Resource-based policy operations do not require a running EC2 instance or NAT Gateway for this lab.

AWS charges depend on account eligibility, service usage, and current pricing.

---

## 26. Save Resource Configuration and Verify Ownership

### Step 1 — Save Resource Variables

```bash
cat > lab02-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab02-resources.env
```

### Step 2 — Restore Variables When Needed

```bash
source lab02-resources.env
```

### Step 3 — Verify Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  --query 'Table.{Name:TableName,Status:TableStatus,ARN:TableArn}'
```

### Step 4 — Verify Tags

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab02
```

### Step 5 — Verify Policy Removal

```bash
aws dynamodb get-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Expected after eventual consistency:

```text
PolicyNotFoundException
```

---

## 27. AWS Resource Cleanup

**Warning:** Delete only the resources created for Lab 02.

### Step 1 — Confirm Lab Table

```bash
echo "$TABLE_NAME"
```

Expected:

```text
ddb-lab02-orders
```

### Step 2 — Inspect Table Metadata

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Project Tag

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

### Step 4 — Remove the Lab Resource Policy if Still Present

```bash
aws dynamodb delete-resource-policy \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

Only perform this against the dedicated lab table and policy.

### Step 5 — Delete DynamoDB Table

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

The error is expected because the disposable table was deleted.

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| Resource Policy | Removed |
| Test Orders | Deleted with table |
| IAM Identity Policies | Unchanged |
| IAM Roles | None created |
| EC2 | None created |
| Lambda | None created |
| RDS | None created |
| NAT Gateway | None created |

---

## 28. Interview Questions and Answers

### Q1. What causes DynamoDB AccessDeniedException?

The caller is not authorized to perform the requested DynamoDB operation under applicable IAM and resource access policies.

### Q2. What permission is required for PutItem?

`dynamodb:PutItem` on the intended DynamoDB table.

### Q3. What is an identity-based IAM policy?

A policy attached to an IAM identity, such as a user or role.

### Q4. What is a resource-based policy?

A policy attached directly to a supported AWS resource that controls access by principals.

### Q5. What is an explicit deny?

A policy statement that explicitly rejects a matching request.

### Q6. Can an Allow override an explicit deny?

No. Applicable explicit denies take precedence over allows.

### Q7. What is an implicit deny?

A request is denied when no sufficient applicable allow authorizes it.

### Q8. How do you identify the current AWS principal?

Use:

```bash
aws sts get-caller-identity
```

### Q9. How do you inspect a DynamoDB resource-based policy?

```bash
aws dynamodb get-resource-policy \
  --resource-arn TABLE_ARN
```

### Q10. How do you attach a DynamoDB resource-based policy?

Use `aws dynamodb put-resource-policy` with the resource ARN and policy document.

### Q11. How do you remove an unintended DynamoDB resource policy?

Use `aws dynamodb delete-resource-policy` after confirming the policy and affected resource.

### Q12. Why can GetItem succeed while PutItem fails?

The authorization policies may allow reads while denying writes.

### Q13. Why shouldn't you grant AdministratorAccess to resolve AccessDeniedException?

It introduces unnecessary privileges and may not override an explicit deny.

### Q14. What can CloudTrail reveal during this incident?

It can help identify management events such as resource-policy changes, including who performed them and when.

### Q15. Are DynamoDB PutItem data events automatically present in CloudTrail?

Not necessarily. Relevant data-event capture must be configured.

### Q16. What does eventual consistency mean for resource-policy changes?

A newly applied or removed policy may not be immediately reflected by subsequent reads or authorization behavior.

### Q17. What security controls might affect DynamoDB permissions?

Identity policies, resource policies, SCPs, permissions boundaries, session policies, and other applicable authorization controls.

### Q18. How would you explain this lab in an interview?

I deployed a DynamoDB table in `us-east-1` using AWS CLI with on-demand capacity.

I created a sample order and verified that PutItem and GetItem worked.

Next, I attached a resource-based policy that explicitly denied `dynamodb:PutItem`.

The write operation began failing with AccessDeniedException.

I investigated the current AWS principal, DynamoDB table ARN, table status, and resource-based policy.

I confirmed that existing records were still readable and that only PutItem was being denied.

The investigation identified the explicit deny as the root cause.

I removed the unintended policy, retried the write operation, and successfully retrieved the new item.

Finally, I reviewed IAM least privilege, CloudTrail auditing, production security considerations, and AWS resource cleanup.

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
│   ├── README.md
│   ├── .gitignore
│   ├── deny-putitem-policy.json
│   ├── lab02-resources.env
│   │
│   └── evidence/
│       ├── healthy-get-item.json
│       ├── deny-policy-attached.json
│       ├── access-denied-output.json
│       ├── access-denied-error.log
│       ├── read-still-works.json
│       └── recovered-putitem.json
│
├── 03-validation-exception/
├── 04-wrong-partition-key/
├── 05-provisioned-throughput-exceeded/
├── 06-conditional-check-failed/
├── 07-gsi-query-not-returning-results/
├── 08-dynamodb-streams-not-triggering/
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

Evidence and local configuration files appear only after their corresponding commands are executed.

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Complete troubleshooting documentation |
| .gitignore | Excludes local evidence and sensitive files |
| deny-putitem-policy.json | Intentional resource-based deny |
| lab02-resources.env | Local resource configuration |
| healthy-get-item.json | Baseline successful read |
| deny-policy-attached.json | Applied policy evidence |
| access-denied-output.json | Failed write standard output |
| access-denied-error.log | AccessDeniedException evidence |
| read-still-works.json | Confirms read access |
| recovered-putitem.json | Successful recovery evidence |

### Recommended Public GitHub Structure

```text
02-putitem-access-denied/
├── README.md
├── .gitignore
└── deny-putitem-policy.json
```

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 02
02-putitem-access-denied/evidence/
02-putitem-access-denied/lab02-resources.env

# Local AWS configuration
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

Review the generated policy JSON before publication. It includes your account ID and table ARN; account IDs are not credentials, but account-specific details may be unnecessary in a public portfolio.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how a DynamoDB write operation can fail due to IAM authorization even when the table itself is healthy.

We created a DynamoDB table and confirmed successful PutItem and GetItem operations.

Next, we intentionally attached a resource-based policy that denied `dynamodb:PutItem`.

The application received AccessDeniedException when attempting to write a new order.

We investigated AWS identity, table metadata, the resource-based policy, and IAM explicit-deny behavior.

We also verified that existing orders remained readable.

The investigation confirmed that the table was not missing or unavailable.

The failure originated from a restrictive authorization policy.

We removed the unintended deny and repeated the PutItem operation.

The write succeeded, and GetItem returned the new order.

Finally, the lab covered CloudTrail investigations, least-privilege permissions, secure policy remediation, cost management, and resource cleanup.

**Key Lesson:** A DynamoDB AccessDeniedException should be investigated through IAM policy evaluation. Adding broad permissions is not a substitute for identifying the actual deny or missing authorization.

### Skills Demonstrated

- Amazon DynamoDB.
- PutItem and GetItem.
- DynamoDB resource-based policies.
- IAM identity-based policies.
- IAM explicit deny.
- IAM implicit deny.
- Policy evaluation logic.
- Resource ARN investigation.
- AWS STS.
- AWS CLI v2.
- Linux Bash.
- jq.
- Authorization troubleshooting.
- CloudTrail investigation.
- Root cause analysis.
- Security policy remediation.
- Least-privilege access.
- Recovery verification.
- AWS resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-002 |
| Scenario | DynamoDB PutItem AccessDenied |
| Table | ddb-lab02-orders |
| Region | us-east-1 |
| Billing Mode | PAY_PER_REQUEST |
| Healthy Baseline | Successful PutItem and GetItem |
| Fault Injection | Resource-based explicit deny |
| Denied Action | dynamodb:PutItem |
| Broken Operation | PutItem |
| Broken Response | AccessDeniedException |
| Existing Data | Readable |
| Root Cause | Explicit deny in resource policy |
| Remediation | Remove restrictive resource policy |
| Recovery | Successful PutItem |
| Data Verification | Successful GetItem |
| Cleanup | DynamoDB table deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Cloud Security Engineers must understand how identity-based and resource-based policies interact, why explicit denies override allows, and how to restore authorized access without compromising least-privilege security.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [DynamoDB Resource-Based Policies](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/access-control-resource-based.html)
- [DynamoDB Resource Policy Examples](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/rbac-examples.html)
- [AWS CLI — PutResourcePolicy](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/put-resource-policy.html)
- [AWS CLI — GetResourcePolicy](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-resource-policy.html)
- [AWS CLI — DeleteResourcePolicy](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/delete-resource-policy.html)
- [AWS CLI — PutItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/put-item.html)
- [AWS CLI — GetItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-item.html)
- [AWS IAM Policy Evaluation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- [AWS CloudTrail Documentation](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)