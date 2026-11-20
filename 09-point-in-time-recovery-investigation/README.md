# Lab 09 — Amazon DynamoDB Point-in-Time Recovery Investigation

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and recover accidentally modified Amazon DynamoDB data using Point-in-Time Recovery (PITR).

In production, application bugs, incorrect deployments, unauthorized changes, and human errors can corrupt important database records.

For example, an application might accidentally overwrite an order amount, change an order status, or delete records.

Although DynamoDB provides highly available database infrastructure, it cannot automatically determine whether an authorized application write contains incorrect business data.

Point-in-Time Recovery allows engineers to restore a DynamoDB table to an eligible historical point within its configured recovery window.

In this lab, we create a DynamoDB table named `ddb-lab09-orders` in the `us-east-1` AWS Region.

We enable PITR with a one-day recovery period.

We then insert three healthy customer orders and record a pre-incident recovery checkpoint.

Next, we intentionally corrupt an order by changing:

- Amount: `150` → `9999`
- Status: `PENDING` → `CANCELLED`

The incorrect update succeeds, simulating a real application data-integrity incident.

We investigate the available recovery window, verify that our checkpoint is eligible, and restore the original data into a new DynamoDB table.

We then compare the corrupted source table against the restored table, verify all original records, review operational configuration and security implications, and clean up both temporary tables.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Verify AWS Identity
          |
          v
Create Source DynamoDB Table
          |
          v
Inspect Initial PITR Status
          |
          v
Enable Point-in-Time Recovery
          |
          v
Configure 1-Day Recovery Period
          |
          v
Verify PITR Enabled
          |
          v
Insert Three Healthy Orders
          |
          v
Verify Original Data
          |
          v
Record Pre-Incident Checkpoint
          |
          v
Fault Injection — Corrupt ORD-9001
          |
          v
Verify Incorrect Amount and Status
          |
          v
Investigate PITR Recovery Window
          |
          v
Check Recovery Point Eligibility
          |
          v
RestoreTableToPointInTime
          |
          v
Create Separate Recovery Table
          |
          v
Wait for ACTIVE Status
          |
          v
Verify Recovered ORD-9001
          |
          v
Compare Source and Recovery Tables
          |
          v
Validate All Three Orders
          |
          v
Review Security and Recovery Strategy
          |
          v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-009 |
| Lab Name | DynamoDB Point-in-Time Recovery Investigation |
| Difficulty | Intermediate–Advanced |
| Primary AWS Service | Amazon DynamoDB |
| Supporting Services | IAM, AWS STS, CloudTrail |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, jq |
| Source Table | `ddb-lab09-orders` |
| Recovery Table | `ddb-lab09-orders-recovered` |
| Partition Key | `order_id` |
| Partition-Key Type | String |
| Billing Mode | PAY_PER_REQUEST |
| Backup Feature | Point-in-Time Recovery |
| PITR Recovery Period | 1 day |
| Initial Records | 3 |
| Corrupted Order | ORD-9001 |
| Original Amount | 150 |
| Corrupted Amount | 9999 |
| Original Status | PENDING |
| Corrupted Status | CANCELLED |
| Fault | Accidental application update |
| Recovery Operation | RestoreTableToPointInTime |
| Recovery Destination | New DynamoDB table |
| Verification | GetItem and Scan |
| Project Tag | DynamoDB-Troubleshooting-Lab09 |
| Cleanup | Delete both temporary tables |

### Learning Objectives

- Understand DynamoDB Point-in-Time Recovery.
- Understand continuous backup protection.
- Understand PITR recovery periods.
- Configure PITR using AWS CLI.
- Inspect DescribeContinuousBackups.
- Understand EarliestRestorableDateTime.
- Understand LatestRestorableDateTime.
- Identify valid recovery timestamps.
- Simulate accidental data corruption.
- Investigate authorized but incorrect database writes.
- Restore a table using RestoreTableToPointInTime.
- Understand why restores create new tables.
- Verify restored data integrity.
- Compare source and restored tables.
- Understand selective item recovery.
- Review disaster recovery planning.
- Understand RPO and RTO.
- Review IAM backup permissions.
- Understand restored-table configuration requirements.
- Manage backup and restoration costs.
- Perform safe AWS resource cleanup.

---

## 2. Production Incident Scenario

### Incident Description

An e-commerce company stores customer orders in Amazon DynamoDB.

The orders table supports daily business operations including payment processing, inventory management, and order tracking.

The table contains:

| Order ID | Customer ID | Status | Amount |
|---|---|---|---:|
| ORD-9001 | CUST-1001 | PENDING | 150 |
| ORD-9002 | CUST-1002 | PROCESSING | 200 |
| ORD-9003 | CUST-1003 | SHIPPED | 300 |

During an application deployment, a software bug incorrectly updates ORD-9001.

The order amount changes from `150` to `9999`.

The order status changes from `PENDING` to `CANCELLED`.

DynamoDB successfully processes the request because the application has permission to update the record.

However, the business data is now incorrect.

The application team detects the issue and reports it to Cloud Engineering.

The engineer investigates the affected table and confirms:

- The DynamoDB table is ACTIVE.
- The table has not been deleted.
- Application credentials are valid.
- The incorrect update succeeded.
- The original values have been overwritten.
- PITR was enabled before the incident.
- A recovery checkpoint exists before the corruption.

The Cloud Engineer uses DynamoDB PITR to restore the historical table state into a separate recovery table.

The original source table remains available.

After the restore, the engineer validates the recovered order and verifies that the original amount and status are present.

### Incident Symptoms

- Database requests succeed.
- An order contains incorrect business values.
- The table remains ACTIVE.
- No availability exception is required for the incident to occur.
- The application has overwritten a valid record.
- PITR provides an eligible historical recovery point.
- Restoring the table recovers the earlier data.

### Business Impact

Accidental DynamoDB data corruption can cause:

- Incorrect customer orders.
- Payment discrepancies.
- Financial reporting errors.
- Inventory inconsistencies.
- Customer complaints.
- Data integrity incidents.
- Increased operational risk.
- Business process disruption.

### Incident Objective

Recover the original customer order data while preserving the existing source table and avoiding unnecessary loss of legitimate transactions.

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
               ddb-lab09-orders
                      |
                      v
                Healthy Orders
                      |
              +-------+-------+
              |               |
              v               v
          ORD-9001         ORD-9002
          Amount 150       Amount 200
          PENDING          PROCESSING
                      |
                      v
                PITR Enabled
                      |
                      v
             Continuous Recovery
                  Protection
```

### Broken Architecture

```text
              Order Application
                      |
                      v
                Application Bug
                      |
                      v
               DynamoDB UpdateItem
                      |
                      v
                 ORD-9001
                      |
                      v
             Incorrect Data Written
                      |
              +-------+-------+
              |               |
              v               v
        Amount = 9999    Status = CANCELLED
                      |
                      v
              Data Integrity Incident
```

### Recovered Architecture

```text
                Source DynamoDB Table
                    ddb-lab09-orders
                            |
                            v
                   PITR Recovery Window
                            |
                            v
                  Pre-Incident Timestamp
                            |
                            v
                RestoreTableToPointInTime
                            |
                            v
                   NEW DynamoDB Table
              ddb-lab09-orders-recovered
                            |
                            v
                   Recovered ORD-9001
                            |
                  +---------+---------+
                  |                   |
                  v                   v
             Amount = 150       Status = PENDING
                            |
                            v
                   Recovery Validated
```

### AWS Components

| Component | Purpose |
|---|---|
| DynamoDB Source Table | Stores live application data |
| Point-in-Time Recovery | Maintains continuous recovery protection |
| DescribeContinuousBackups | Reports PITR status and recovery window |
| UpdateContinuousBackups | Enables and configures PITR |
| RestoreTableToPointInTime | Restores historical data |
| DynamoDB Recovery Table | Stores restored records |
| GetItem | Verifies individual items |
| Scan | Verifies all lab records |
| AWS STS | Verifies caller identity |
| IAM | Controls backup and restore permissions |
| CloudTrail | Supports auditing of relevant management events |
| AWS CLI | Performs the recovery workflow |
| Bash | Automates timestamp validation |
| jq | Inspects and validates JSON |

---

## 4. Understanding DynamoDB Point-in-Time Recovery

DynamoDB PITR provides continuous backup protection for a table.

When enabled, the feature allows restoring a table to an eligible point within its configured recovery period.

### Recovery Period

```text
Minimum: 1 day
Maximum: 35 days
```

For this lab:

```text
RecoveryPeriodInDays = 1
```

### Recovery Window

```text
EarliestRestorableDateTime
             |
             v
     Available Recovery History
             |
             v
       Selected Restore Point
             |
             v
LatestRestorableDateTime
```

A recovery timestamp must lie between the earliest and latest available recovery timestamps.

### Important PITR Characteristics

- PITR must be enabled before the data changes that need recovery.
- Recovery is limited to the available recovery window.
- PITR supports recovery to eligible second-level timestamps.
- Restores create a new DynamoDB table.
- The source table remains unchanged.
- Some operational settings must be configured again after restoration.
- PITR incurs additional charges.

### Production Lesson

Point-in-Time Recovery is useful for accidental modifications, unintended deletes, and certain data-integrity incidents.

It does not automatically prevent incorrect application writes.

---

## 5. Understanding Recovery Window Timestamps

DynamoDB reports two important PITR timestamps.

### EarliestRestorableDateTime

The earliest available point to which the table can currently be restored.

### LatestRestorableDateTime

The latest available point to which the table can currently be restored.

The latest restorable point is typically approximately five minutes behind the current time.

### Example

```text
Current Time:               18:45 UTC
Earliest Restorable Time:   17:00 UTC
Latest Restorable Time:     18:40 UTC
Requested Recovery Time:    18:30 UTC
```

In this example, 18:30 UTC is within the eligible recovery window.

### Invalid Example

```text
Latest Restorable Time:     18:40 UTC
Requested Recovery Time:    18:43 UTC
```

The requested point is newer than the latest available recovery time.

The engineer must verify eligibility again later.

### Important Principle

Never assume that an arbitrary timestamp is recoverable.

Always inspect the actual window returned by DynamoDB.

---

## 6. PITR vs. On-Demand Backup

DynamoDB supports continuous point-in-time recovery and on-demand backups.

| Feature | PITR | On-Demand Backup |
|---|---|---|
| Backup Type | Continuous | Snapshot |
| Recovery Point | Eligible second within window | Backup snapshot |
| Recovery Period | 1–35 days | Until backup expiration or deletion |
| Restore Destination | New table | New table |
| Suitable for | Accidental changes | Planned backups and retention |
| Requires Manual Snapshot | No | Yes |
| Additional Charges | Yes | Yes |

### When to Use PITR

- Accidental record updates.
- Unintended table data deletion.
- Application data corruption.
- Recovery to a known historical point.

### When to Use On-Demand Backups

- Planned application migrations.
- Pre-deployment snapshots.
- Long-term backup retention.
- Specific compliance requirements.

### Production Consideration

Some organizations use both approaches as part of a wider disaster recovery strategy.

---

## 7. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- jq.
- AWS account.
- Permissions to manage the dedicated DynamoDB resources.

### Relevant IAM Actions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:ListTables
dynamodb:ListTagsOfResource
dynamodb:TagResource
dynamodb:PutItem
dynamodb:BatchWriteItem
dynamodb:GetItem
dynamodb:Scan
dynamodb:UpdateItem
dynamodb:UpdateContinuousBackups
dynamodb:DescribeContinuousBackups
dynamodb:RestoreTableToPointInTime
dynamodb:DeleteTable
```

These are relevant actions, not a complete deployable IAM policy.

### Safety Rules

- Use only disposable lab tables.
- Never intentionally corrupt production data.
- Verify AWS account and Region.
- Use fabricated order data.
- Enable PITR before performing the incident simulation.
- Record the recovery checkpoint carefully.
- Verify timestamps before restoration.
- Restore to a separate table.
- Do not replace the source table without a controlled recovery plan.
- Verify project tags before deleting resources.

### Resource Tag

```text
Project = DynamoDB-Troubleshooting-Lab09
```

---

## 8. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 09-point-in-time-recovery-investigation

cd 09-point-in-time-recovery-investigation
```

### Step 2 — Verify Tools

```bash
aws --version

jq --version

date --version

aws sts get-caller-identity
```

### Step 3 — Configure Environment Variables

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export SOURCE_TABLE="ddb-lab09-orders"

export RECOVERY_TABLE="ddb-lab09-orders-recovered"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab09"

export SOURCE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${SOURCE_TABLE}"

export RECOVERY_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${RECOVERY_TABLE}"
```

### Step 4 — Verify Configuration

```bash
echo "$AWS_REGION"

echo "$SOURCE_TABLE"

echo "$RECOVERY_TABLE"

echo "$SOURCE_ARN"
```

### Step 5 — Prepare Evidence Directory

```bash
mkdir -p evidence
```

### Step 6 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
evidence/
lab09-resources.env
recovery-point.env

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

## 9. Verify AWS Account and Resources

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

### Step 3 — Check Source Table

```bash
aws dynamodb describe-table \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION"
```

### Step 4 — Check Recovery Table

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION"
```

Expected before creating these resources:

```text
ResourceNotFoundException
```

If either table exists, verify ownership before proceeding.

Do not modify unrelated DynamoDB tables.

---

## 10. Create Source DynamoDB Table

### Step 1 — Create Table

```bash
aws dynamodb create-table \
  --table-name "$SOURCE_TABLE" \
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
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Table

```bash
aws dynamodb describe-table \
  --table-name "$SOURCE_TABLE" \
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

### Step 4 — Save Evidence

```bash
aws dynamodb describe-table \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION" \
  > evidence/source-table-description.json
```

### Table Configuration

| Property | Value |
|---|---|
| Table Name | ddb-lab09-orders |
| Partition Key | order_id |
| Key Type | String |
| Billing Mode | PAY_PER_REQUEST |
| Region | us-east-1 |

---

## 11. Inspect Initial PITR Configuration

### Step 1 — Check Continuous Backups

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION"
```

### Step 2 — Inspect PITR Status

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription' \
  --output json \
  --region "$AWS_REGION"
```

Expected for a newly created table without PITR enabled:

```text
PointInTimeRecoveryStatus = DISABLED
```

### Step 3 — Save Baseline

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION" \
  > evidence/pitr-before.json
```

### Important Distinction

DynamoDB may report:

```text
ContinuousBackupsStatus = ENABLED
```

while:

```text
PointInTimeRecoveryStatus = DISABLED
```

The continuous backup status alone does not prove that PITR is enabled.

The PointInTimeRecoveryStatus field is the relevant setting for this investigation.

---

## 12. Enable Point-in-Time Recovery

### Step 1 — Enable PITR

```bash
aws dynamodb update-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --point-in-time-recovery-specification \
    PointInTimeRecoveryEnabled=true,RecoveryPeriodInDays=1 \
  --region "$AWS_REGION"
```

### Configuration Explanation

| Parameter | Meaning |
|---|---|
| PointInTimeRecoveryEnabled | Enables PITR |
| RecoveryPeriodInDays | Configured recovery history |
| 1 | One-day recovery period |

### Step 2 — Verify PITR Status

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription' \
  --output json \
  --region "$AWS_REGION"
```

Expected after activation:

```text
PointInTimeRecoveryStatus = ENABLED
```

### Step 3 — Verify Recovery Period

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.RecoveryPeriodInDays' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
1
```

### Step 4 — Save Enabled Configuration

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION" \
  > evidence/pitr-enabled.json
```

### Production Lesson

PITR must be enabled before the incident to provide recovery history for the affected data.

Enabling it after corruption does not recreate earlier historical versions that were never protected.

---

## 13. Insert Healthy Customer Orders

### Step 1 — Create `orders.json`

```bash
cat > orders.json <<'EOF'
{
  "ddb-lab09-orders": [
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-9001"},
          "customer_id": {"S": "CUST-1001"},
          "status": {"S": "PENDING"},
          "amount": {"N": "150"}
        }
      }
    },
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-9002"},
          "customer_id": {"S": "CUST-1002"},
          "status": {"S": "PROCESSING"},
          "amount": {"N": "200"}
        }
      }
    },
    {
      "PutRequest": {
        "Item": {
          "order_id": {"S": "ORD-9003"},
          "customer_id": {"S": "CUST-1003"},
          "status": {"S": "SHIPPED"},
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

### Step 3 — Insert Records

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

If UnprocessedItems is not empty, retry those requests before continuing.

### Step 4 — Verify Records

```bash
aws dynamodb scan \
  --table-name "$SOURCE_TABLE" \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected records:

| Order ID | Status | Amount |
|---|---|---:|
| ORD-9001 | PENDING | 150 |
| ORD-9002 | PROCESSING | 200 |
| ORD-9003 | SHIPPED | 300 |

### Step 5 — Save Healthy Evidence

```bash
aws dynamodb scan \
  --table-name "$SOURCE_TABLE" \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/healthy-orders.json
```

### Step 6 — Validate

```bash
jq -e '
  .Count == 3 and
  ([.Items[] |
    {id: .order_id.S, status: .status.S, amount: .amount.N}
  ] | sort_by(.id)) ==
  [
    {"id":"ORD-9001","status":"PENDING","amount":"150"},
    {"id":"ORD-9002","status":"PROCESSING","amount":"200"},
    {"id":"ORD-9003","status":"SHIPPED","amount":"300"}
  ]
' evidence/healthy-orders.json
```

Expected:

```text
true
```

---

## 14. Record Pre-Incident Recovery Checkpoint

### Production Objective

Record a timestamp after the healthy writes and before the accidental corruption.

The selected timestamp must later fall inside the eligible recovery window.

### Step 1 — Confirm Healthy Baseline

```bash
jq -e '.Count == 3' \
  evidence/healthy-orders.json
```

### Step 2 — Record UTC Checkpoint

```bash
sleep 3

export RECOVERY_POINT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

echo "$RECOVERY_POINT"
```

Example:

```text
2026-11-19T18:30:00Z
```

The example timestamp is illustrative.

Use the actual timestamp generated during the lab.

### Step 3 — Save Environment File

```bash
printf 'export RECOVERY_POINT="%s"\n' \
  "$RECOVERY_POINT" > recovery-point.env

chmod 600 recovery-point.env
```

### Step 4 — Save Evidence

```bash
cat > evidence/recovery-checkpoint.json <<EOF
{
  "source_table": "$SOURCE_TABLE",
  "recovery_point_utc": "$RECOVERY_POINT",
  "expected_order": "ORD-9001",
  "expected_status": "PENDING",
  "expected_amount": "150"
}
EOF
```

### Checkpoint Importance

The recovery point represents the healthy state that existed before the incident.

It must not be confused with the time the problem was discovered or with the latest available recovery timestamp.

---

## 15. Fault Injection — Accidental Data Corruption

### Production Fault

An application bug updates an existing order with incorrect values.

### Step 1 — Corrupt ORD-9001

```bash
aws dynamodb update-item \
  --table-name "$SOURCE_TABLE" \
  --key '{"order_id":{"S":"ORD-9001"}}' \
  --update-expression \
    "SET #s = :status, #a = :amount" \
  --condition-expression \
    "attribute_exists(order_id)" \
  --expression-attribute-names '{
    "#s": "status",
    "#a": "amount"
  }' \
  --expression-attribute-values '{
    ":status": {"S": "CANCELLED"},
    ":amount": {"N": "9999"}
  }' \
  --return-values ALL_NEW \
  --region "$AWS_REGION"
```

### Step 2 — Retrieve Corrupted Order

```bash
aws dynamodb get-item \
  --table-name "$SOURCE_TABLE" \
  --key '{"order_id":{"S":"ORD-9001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

Expected:

```text
status = CANCELLED
amount = 9999
```

### Step 3 — Save Incident Evidence

```bash
aws dynamodb get-item \
  --table-name "$SOURCE_TABLE" \
  --key '{"order_id":{"S":"ORD-9001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/corrupted-order.json
```

### Step 4 — Validate Corruption

```bash
jq -e '
  .Item.status.S == "CANCELLED" and
  .Item.amount.N == "9999"
' evidence/corrupted-order.json
```

Expected:

```text
true
```

### Incident Comparison

| Attribute | Healthy | Corrupted |
|---|---|---|
| order_id | ORD-9001 | ORD-9001 |
| customer_id | CUST-1001 | CUST-1001 |
| status | PENDING | CANCELLED |
| amount | 150 | 9999 |

### Investigation Finding

The table remains healthy, but the application has successfully written incorrect data.

This is a data-integrity problem, not a database-availability problem.

---

## 16. Investigate PITR Recovery Window

### Step 1 — Inspect PITR Metadata

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription' \
  --output json \
  --region "$AWS_REGION"
```

### Step 2 — Save Recovery Window

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION" \
  > evidence/recovery-window.json
```

### Step 3 — Inspect Available Timestamps

```bash
jq -r '
  .ContinuousBackupsDescription.PointInTimeRecoveryDescription |
  "Earliest: \(.EarliestRestorableDateTime)\nLatest: \(.LatestRestorableDateTime)"
' evidence/recovery-window.json
```

### Step 4 — Compare Checkpoint

```bash
echo "Requested Recovery Point:"
echo "$RECOVERY_POINT"
```

### Expected Relationship

```text
EarliestRestorableDateTime
          |
          v
    RECOVERY_POINT
          |
          v
LatestRestorableDateTime
```

### Common Mistake

Attempting to restore to a checkpoint that is more recent than LatestRestorableDateTime.

### Correct Response

Verify the recovery window again after it advances.

Do not restore to the latest available point without confirming that it precedes the corruption.

---

## 17. Create Automated Recovery Window Validation

### Step 1 — Create `verify-recovery-window.sh`

```bash
cat > verify-recovery-window.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?AWS_REGION is required}"
: "${SOURCE_TABLE:?SOURCE_TABLE is required}"
: "${RECOVERY_POINT:?RECOVERY_POINT is required}"

target_epoch=$(date -u -d "$RECOVERY_POINT" +%s)

for attempt in $(seq 1 30); do

  aws dynamodb describe-continuous-backups \
    --table-name "$SOURCE_TABLE" \
    --region "$AWS_REGION" \
    > evidence/recovery-window.json

  status=$(jq -r '
    .ContinuousBackupsDescription
    .PointInTimeRecoveryDescription
    .PointInTimeRecoveryStatus // "UNKNOWN"
  ' evidence/recovery-window.json)

  earliest=$(jq -r '
    .ContinuousBackupsDescription
    .PointInTimeRecoveryDescription
    .EarliestRestorableDateTime // empty
  ' evidence/recovery-window.json)

  latest=$(jq -r '
    .ContinuousBackupsDescription
    .PointInTimeRecoveryDescription
    .LatestRestorableDateTime // empty
  ' evidence/recovery-window.json)

  if [[ "$status" != "ENABLED" ]]; then
    echo "PITR is not enabled. Status: $status"
    exit 1
  fi

  if [[ -n "$earliest" && -n "$latest" ]]; then

    earliest_epoch=$(date -u -d "$earliest" +%s)
    latest_epoch=$(date -u -d "$latest" +%s)

    if (( target_epoch < earliest_epoch )); then
      echo "ERROR: Recovery point precedes recovery window."
      exit 1
    fi

    if (( target_epoch <= latest_epoch )); then
      echo "Recovery point is eligible."
      echo "Target: $RECOVERY_POINT"
      echo "Earliest: $earliest"
      echo "Latest: $latest"
      exit 0
    fi

  fi

  echo "Attempt $attempt: checkpoint not yet eligible."

  sleep 30

done

echo "Recovery point not eligible within bounded verification."
exit 1
EOF
```

### Step 2 — Make Executable

```bash
chmod +x verify-recovery-window.sh
```

### Step 3 — Run Validation

```bash
./verify-recovery-window.sh
```

### Expected Successful Result

```text
Recovery point is eligible.
```

### Safety Behavior

The script checks:

- PITR status.
- Earliest restorable time.
- Latest restorable time.
- Selected checkpoint.

It exits if the checkpoint falls outside the available recovery window.

The loop is bounded to 30 attempts, each separated by 30 seconds.

### Important Note

The validator checks timestamp eligibility. It does not guarantee that the underlying historical data has the expected values.

That must be verified after restoration.

---

## 18. Restore Table to Pre-Incident Point

### Step 1 — Verify Recovery Destination Does Not Exist

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION"
```

Expected before restoration:

```text
ResourceNotFoundException
```

### Step 2 — Restore Table

Only proceed after the recovery-window validation succeeds.

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name "$SOURCE_TABLE" \
  --target-table-name "$RECOVERY_TABLE" \
  --restore-date-time "$RECOVERY_POINT" \
  --region "$AWS_REGION"
```

### Configuration Explanation

| Parameter | Meaning |
|---|---|
| source-table-name | Existing table |
| target-table-name | New recovery table |
| restore-date-time | Historical recovery point |
| region | AWS Region |

### Step 3 — Inspect Restore Status

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --query 'Table.{
    Name:TableName,
    Status:TableStatus,
    ARN:TableArn,
    RestoreSummary:RestoreSummary
  }' \
  --output json \
  --region "$AWS_REGION"
```

The table may initially be in CREATING state.

### Step 4 — Wait for ACTIVE

```bash
aws dynamodb wait table-exists \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Status

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --query 'Table.TableStatus' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
ACTIVE
```

### Step 6 — Tag Recovery Table

```bash
aws dynamodb tag-resource \
  --resource-arn "$RECOVERY_ARN" \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 7 — Save Restore Evidence

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION" \
  > evidence/recovered-table-description.json
```

### Important Recovery Principle

The source table is not overwritten.

DynamoDB creates a new table containing the restored historical data.

---

## 19. Verify Recovered Order

### Step 1 — Retrieve ORD-9001

```bash
aws dynamodb get-item \
  --table-name "$RECOVERY_TABLE" \
  --key '{"order_id":{"S":"ORD-9001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Expected Response

```json
{
  "Item": {
    "order_id": {"S": "ORD-9001"},
    "customer_id": {"S": "CUST-1001"},
    "status": {"S": "PENDING"},
    "amount": {"N": "150"}
  }
}
```

### Step 2 — Save Recovery Evidence

```bash
aws dynamodb get-item \
  --table-name "$RECOVERY_TABLE" \
  --key '{"order_id":{"S":"ORD-9001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/recovered-order.json
```

### Step 3 — Validate Original Values

```bash
jq -e '
  .Item.order_id.S == "ORD-9001" and
  .Item.status.S == "PENDING" and
  .Item.amount.N == "150"
' evidence/recovered-order.json
```

Expected:

```text
true
```

### Recovery Finding

The restored table contains the original pre-incident order values.

---

## 20. Compare Source and Restored Tables

### Step 1 — Retrieve Source Order

```bash
aws dynamodb get-item \
  --table-name "$SOURCE_TABLE" \
  --key '{"order_id":{"S":"ORD-9001"}}' \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/source-after-restore.json
```

### Step 2 — Inspect Corrupted Source

```bash
jq '{
  order_id: .Item.order_id.S,
  status: .Item.status.S,
  amount: .Item.amount.N
}' evidence/source-after-restore.json
```

### Step 3 — Inspect Recovered Order

```bash
jq '{
  order_id: .Item.order_id.S,
  status: .Item.status.S,
  amount: .Item.amount.N
}' evidence/recovered-order.json
```

### Expected Comparison

| Attribute | Source Table | Recovery Table |
|---|---|---|
| order_id | ORD-9001 | ORD-9001 |
| customer_id | CUST-1001 | CUST-1001 |
| status | CANCELLED | PENDING |
| amount | 9999 | 150 |

### Important Lesson

PITR does not automatically repair the source table.

The recovered data remains in a separate table until engineers perform an appropriate recovery or migration operation.

---

## 21. Verify Complete Table Recovery

### Step 1 — Scan Recovery Table

```bash
aws dynamodb scan \
  --table-name "$RECOVERY_TABLE" \
  --consistent-read \
  --region "$AWS_REGION" \
  > evidence/all-recovered-orders.json
```

### Step 2 — Validate Three Records

```bash
jq -e '
  .Count == 3 and
  ([.Items[] |
    {id: .order_id.S, status: .status.S, amount: .amount.N}
  ] | sort_by(.id)) ==
  [
    {"id":"ORD-9001","status":"PENDING","amount":"150"},
    {"id":"ORD-9002","status":"PROCESSING","amount":"200"},
    {"id":"ORD-9003","status":"SHIPPED","amount":"300"}
  ]
' evidence/all-recovered-orders.json
```

Expected:

```text
true
```

### Step 3 — Verify Source Table Is Still ACTIVE

```bash
aws dynamodb describe-table \
  --table-name "$SOURCE_TABLE" \
  --query 'Table.TableStatus' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
ACTIVE
```

### Step 4 — Verify Recovery Table Is ACTIVE

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --query 'Table.TableStatus' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
ACTIVE
```

### Verification Results

| Test | Expected |
|---|---|
| Source Table | ACTIVE |
| Recovery Table | ACTIVE |
| Original Order Status | Recovered |
| Original Order Amount | Recovered |
| Other Orders | Preserved at checkpoint |
| Recovery Item Count | 3 |
| Source Table Overwritten | No |
| PITR Restore | Successful |

---

## 22. Investigate Restored-Table Configuration

Restoring a table does not automatically recreate every operational setting.

### Step 1 — Inspect Recovery Table PITR

```bash
aws dynamodb describe-continuous-backups \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Stream and Security Configuration

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --query 'Table.{
    Streams:StreamSpecification,
    StreamArn:LatestStreamArn,
    SSE:SSEDescription,
    DeletionProtection:DeletionProtectionEnabled
  }' \
  --region "$AWS_REGION"
```

### Step 3 — Verify Tags

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$RECOVERY_ARN" \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Table Schema

```bash
aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --query 'Table.{
    Keys:KeySchema,
    Attributes:AttributeDefinitions,
    Billing:BillingModeSummary
  }' \
  --region "$AWS_REGION"
```

### Production Recovery Checklist

| Configuration | Action After Restore |
|---|---|
| Data | Verify restored records |
| Table Key Schema | Verify |
| GSIs and LSIs | Verify restored configuration |
| Encryption | Verify |
| Tags | Reapply as necessary |
| PITR | Reconfigure if required |
| DynamoDB Streams | Reconfigure if required |
| TTL | Reconfigure if required |
| IAM Policies | Verify access |
| CloudWatch Alarms | Recreate or update |
| Auto Scaling | Reconfigure if applicable |
| Application References | Update only during controlled cutover |

### Production Lesson

Restoring data is only one part of disaster recovery.

The recovered table must also be operationally ready before it is used by production applications.

---

## 23. Root Cause Analysis

### Incident Summary

The DynamoDB table remained healthy.

The application successfully performed an incorrect update that corrupted the business data.

PITR was enabled before the incident and provided a recoverable historical state.

### Root Cause Diagram

```text
Application Deployment
          |
          v
Incorrect Data Update
          |
          v
DynamoDB Accepts Request
          |
          v
Order Data Corrupted
          |
          v
Incident Detected
          |
          v
Investigate PITR
          |
          v
Locate Healthy Checkpoint
          |
          v
Restore to New Table
          |
          v
Verify Original Data
```

### Five Whys

**Why 1 — Why was the order incorrect?**

The application overwrote the amount and status with incorrect values.

**Why 2 — Why did DynamoDB accept the update?**

The request was authorized and satisfied the supplied write condition.

**Why 3 — Why was the incorrect data not prevented?**

The simulated application lacked sufficient business-value validation.

**Why 4 — How could the original data be recovered?**

PITR was enabled before the incident.

**Why 5 — How can similar incidents be prevented?**

Combine application validation, conditional writes, least-privilege IAM, monitoring, backup protection, and tested recovery procedures.

### Root Cause Conclusion

The incident was caused by incorrect application behavior, not a DynamoDB infrastructure outage.

Point-in-Time Recovery provided a method to reconstruct the earlier database state.

---

## 24. Production Recovery Decision Tree

```text
DynamoDB Data Corruption
          |
          v
Identify Affected Records
          |
          v
Determine Incident Timeline
          |
          v
Is PITR Enabled?
          |
      +---+---+
      |       |
     No      Yes
      |       |
      v       v
Check Other  Inspect Recovery Window
Backups           |
                  v
          Valid Pre-Incident Point?
                  |
             +----+----+
             |         |
            No        Yes
             |         |
             v         v
       Investigate   Restore New Table
       Alternatives       |
                          v
                  Verify Restored Data
                          |
                          v
                Determine Recovery Scope
                          |
                     +----+----+
                     |         |
                     v         v
                Few Items   Broad Corruption
                     |         |
                     v         v
                 Selective   Coordinated
                 Recovery    Table Cutover
                     |         |
                     +----+----+
                          |
                          v
                  Validate Production
```

### Production Investigation Checklist

| Check | Expected |
|---|---|
| AWS Account | Correct |
| AWS Region | Correct |
| Source Table | Exists |
| PITR Status | ENABLED |
| Incident Time | Identified |
| Recovery Point | Before corruption |
| Recovery Window | Valid |
| Restore Destination | Separate table |
| Recovered Table | ACTIVE |
| Recovered Data | Verified |
| Operational Settings | Reviewed |
| Production Cutover | Controlled if required |

---

## 25. Cloud Security Engineering Considerations

### Least-Privilege IAM

Restrict which identities can manage DynamoDB backup settings, restore tables, and delete production resources.

### Protect PITR

Unnecessary or unauthorized changes to PITR configuration can affect recoverability.

### CloudTrail Investigation

Review relevant management activity when determining how backup settings or tables were modified.

### Encryption

Verify encryption settings on restored tables.

### Restored Data Access

Recovered tables can contain sensitive historical customer information.

Ensure the new table has appropriate access restrictions.

### Application Data Validation

Use conditional expressions and input validation to prevent incorrect business updates.

### Backup Testing

Regularly test recovery procedures instead of assuming that enabled backups automatically provide a usable recovery process.

### Protect Post-Incident Transactions

Do not blindly overwrite legitimate orders created after the selected recovery timestamp.

### Security Principle

**Reliable cloud security includes prevention, detection, recovery, and validation of data integrity—not just database availability.**

---

## 26. Disaster Recovery — RPO and RTO

### Recovery Point Objective

RPO defines the maximum acceptable amount of data loss measured in time.

For example:

```text
RPO = 5 minutes
```

This means the business aims to tolerate no more than five minutes of lost changes.

DynamoDB PITR has a latest restorable time that usually lags behind the present.

Production recovery design must account for this behavior.

### Recovery Time Objective

RTO defines how quickly the application should recover after an incident.

Example:

```text
RTO = 1 hour
```

This represents a business target, not a guaranteed DynamoDB restore duration.

### PITR Recovery Factors

- Table size.
- Number of secondary indexes.
- Restore duration.
- Recovery validation.
- Application configuration.
- Data migration or cutover requirements.

### Practical Lesson

PITR availability alone does not guarantee that an organization's RPO or RTO requirements will be met.

These objectives should be tested through recovery exercises.

---

## 27. Cost Management

### Potential Charges

| AWS Resource | Cost Consideration |
|---|---|
| Source DynamoDB Table | Storage and requests |
| PITR | Continuous backup storage |
| Restore Operation | Restoration charges |
| Recovery Table | Storage and requests |
| CloudTrail | Applicable logging charges |
| AWS CLI | No separate CLI fee |

### Lab Cost Controls

- Use only one source table.
- Configure one-day PITR.
- Insert only three sample orders.
- Perform one restoration.
- Avoid repeated restore operations.
- Delete both tables after testing.

### Important Pricing Detail

DynamoDB PITR is billed primarily based on the protected table's backup storage size; shortening the recovery window from 35 days to one day does not by itself proportionally reduce PITR charges.

The one-day window is used here to keep the exercise's recovery scope small, not as a guarantee of lower PITR pricing.

### Production Cost Consideration

Backup protection must balance recovery requirements, retention policies, and cost.

---

## 28. Save Environment and Cleanup

### Step 1 — Save Resource Variables

```bash
cat > lab09-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export SOURCE_TABLE="$SOURCE_TABLE"
export RECOVERY_TABLE="$RECOVERY_TABLE"
export SOURCE_ARN="$SOURCE_ARN"
export RECOVERY_ARN="$RECOVERY_ARN"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab09-resources.env
```

### Step 2 — Restore Environment

```bash
source lab09-resources.env

source recovery-point.env
```

### Step 3 — Verify Table Ownership

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$SOURCE_ARN" \
  --region "$AWS_REGION"

aws dynamodb list-tags-of-resource \
  --resource-arn "$RECOVERY_ARN" \
  --region "$AWS_REGION"
```

Both should contain:

```text
Project = DynamoDB-Troubleshooting-Lab09
```

### Step 4 — Delete Recovery Table

Only after confirming ownership and completing validation:

```bash
aws dynamodb delete-table \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION"
```

### Step 5 — Wait for Recovery Table Deletion

```bash
aws dynamodb wait table-not-exists \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION"
```

### Step 6 — Delete Source Table

```bash
aws dynamodb delete-table \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION"
```

### Step 7 — Wait for Source Table Deletion

```bash
aws dynamodb wait table-not-exists \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION"
```

### Step 8 — Verify Cleanup

```bash
aws dynamodb describe-table \
  --table-name "$SOURCE_TABLE" \
  --region "$AWS_REGION"

aws dynamodb describe-table \
  --table-name "$RECOVERY_TABLE" \
  --region "$AWS_REGION"
```

Expected for both:

```text
ResourceNotFoundException
```

### Cleanup Summary

| Resource | Expected State |
|---|---|
| Source DynamoDB Table | Deleted |
| Recovery DynamoDB Table | Deleted |
| Active Table PITR Configuration | No longer applicable after deletion |
| IAM Roles | None created |
| Lambda | None created |
| EC2 | None created |
| Local Scripts | Retained |
| Local Evidence | Retained |

DynamoDB may maintain its documented system backup for a deleted PITR-enabled table. That is separate from an active user table.

---

## 29. Repository Structure and Interview Preparation

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
│   ├── README.md
│   ├── .gitignore
│   ├── orders.json
│   ├── verify-recovery-window.sh
│   ├── lab09-resources.env
│   ├── recovery-point.env
│   │
│   └── evidence/
│       ├── source-table-description.json
│       ├── pitr-before.json
│       ├── pitr-enabled.json
│       ├── healthy-orders.json
│       ├── recovery-checkpoint.json
│       ├── corrupted-order.json
│       ├── recovery-window.json
│       ├── recovered-table-description.json
│       ├── recovered-order.json
│       ├── source-after-restore.json
│       └── all-recovered-orders.json
│
└── 10-dynamodb-hot-partition/
```

### Recommended Public GitHub Structure

```text
09-point-in-time-recovery-investigation/
├── README.md
├── .gitignore
├── orders.json
└── verify-recovery-window.sh
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Production troubleshooting documentation |
| .gitignore | Excludes generated evidence |
| orders.json | Three healthy customer orders |
| verify-recovery-window.sh | Validates PITR timestamp eligibility |
| lab09-resources.env | Local AWS resource variables |
| recovery-point.env | Recorded healthy checkpoint |
| source-table-description.json | Source table metadata |
| pitr-before.json | Initial backup configuration |
| pitr-enabled.json | Enabled PITR evidence |
| healthy-orders.json | Original item values |
| recovery-checkpoint.json | Recovery timestamp information |
| corrupted-order.json | Incident evidence |
| recovery-window.json | Available recovery timestamps |
| recovered-table-description.json | Restored table metadata |
| recovered-order.json | Recovered ORD-9001 |
| source-after-restore.json | Source data after restoration |
| all-recovered-orders.json | Full recovered data verification |

### Interview Questions

**Q1. What is DynamoDB PITR?**

Continuous backup protection that enables restoration to an eligible historical point within the configured recovery window.

**Q2. What is the maximum recovery period?**

35 days.

**Q3. What is the minimum configurable recovery period?**

One day.

**Q4. What is EarliestRestorableDateTime?**

The earliest timestamp available for restoration.

**Q5. What is LatestRestorableDateTime?**

The most recent timestamp currently available for restoration.

**Q6. Why might the latest recovery timestamp lag behind current time?**

Because continuous backup recovery availability is not necessarily current to the exact present second.

**Q7. Does PITR restore directly into the original table?**

No. It creates a separate table.

**Q8. Does the original table remain available during restoration?**

Yes, the restore does not overwrite the existing table.

**Q9. Which AWS CLI command restores historical DynamoDB data?**

RestoreTableToPointInTime.

**Q10. Does a restored table inherit every operational setting?**

No. Several settings, including PITR, tags, Streams, auto scaling, and monitoring configuration, require review or reconfiguration.

**Q11. Can PITR recover from an incorrect application update?**

Yes, if the required historical point is available in the recovery window.

**Q12. Why should engineers verify the recovered data before cutover?**

To ensure the restored state is correct and avoid introducing additional data loss.

**Q13. What is RPO?**

The maximum acceptable data loss measured in time.

**Q14. What is RTO?**

The target time for recovering application functionality after an incident.

**Q15. How do you prevent accidentally losing legitimate post-incident writes?**

Identify later transactions and plan selective recovery, reconciliation, or a coordinated application cutover.

**Q16. Which IAM controls matter for PITR?**

Restricting who can manage continuous backups, restore tables, and delete critical resources.

**Q17. Does PITR prevent invalid application updates?**

No. It provides historical recovery, not business-rule validation.

**Q18. Why should PITR restoration be tested before an emergency?**

Recovery timing, operational settings, and application dependencies must be verified to understand actual recovery capabilities.

### Interview Explanation

In this lab, I created an Amazon DynamoDB table in the `us-east-1` Region and enabled Point-in-Time Recovery.

I inserted three sample customer orders and recorded a healthy recovery checkpoint.

Next, I simulated an application bug that accidentally changed an order amount from 150 to 9999 and its status from PENDING to CANCELLED.

I verified the corrupted values and investigated the available recovery window using DescribeContinuousBackups.

After confirming that the recorded checkpoint was eligible, I restored the table to that historical point using RestoreTableToPointInTime.

DynamoDB created a separate recovery table.

I compared the corrupted source data with the restored data and confirmed that the original order values were recovered.

I also verified the other records, inspected the restored table configuration, reviewed disaster recovery considerations, and cleaned up both temporary tables.

This lab demonstrated DynamoDB backup investigation, Point-in-Time Recovery, data integrity verification, and production disaster recovery troubleshooting.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how Amazon DynamoDB Point-in-Time Recovery can be used to investigate and recover from accidental data corruption.

We created a DynamoDB table and enabled PITR with a one-day recovery period.

We inserted three sample orders and verified that their initial values were correct.

We recorded a healthy recovery checkpoint before introducing an application error.

Next, we intentionally changed one order's amount and status to incorrect values.

DynamoDB accepted the request because it was authorized and did not violate the supplied conditions.

We investigated the PITR recovery window and learned that recovery timestamps must fall between EarliestRestorableDateTime and LatestRestorableDateTime.

We created a Bash script to validate the recovery point before restoration.

Once the checkpoint became eligible, we restored the original table state into a separate DynamoDB table.

We verified that the recovery table contained the original order amount and status.

We also confirmed that the source table remained unchanged.

Finally, we reviewed operational settings, selective recovery strategies, RPO, RTO, security permissions, cost management, and safe resource cleanup.

**Key Lesson:** DynamoDB PITR is a data recovery capability, not a substitute for application validation or operational recovery planning. Engineers must verify the recovery point, restore to a separate table, validate the data, and protect legitimate transactions before a production cutover.

### Skills Demonstrated

- Amazon DynamoDB.
- Point-in-Time Recovery.
- Continuous backup configuration.
- Recovery-window investigation.
- DescribeContinuousBackups.
- UpdateContinuousBackups.
- RestoreTableToPointInTime.
- UTC timestamp handling.
- Bash automation.
- AWS CLI v2.
- jq.
- GetItem.
- UpdateItem.
- BatchWriteItem.
- Scan.
- Data corruption investigation.
- Recovery verification.
- Source and recovery table comparison.
- Disaster recovery planning.
- RPO and RTO.
- IAM least privilege.
- Data integrity protection.
- AWS cost management.
- Resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-009 |
| Scenario | Point-in-Time Recovery Investigation |
| Region | us-east-1 |
| Source Table | ddb-lab09-orders |
| Recovery Table | ddb-lab09-orders-recovered |
| Partition Key | order_id |
| Billing Mode | PAY_PER_REQUEST |
| PITR | Enabled |
| Recovery Period | 1 day |
| Initial Orders | 3 |
| Corrupted Order | ORD-9001 |
| Original Amount | 150 |
| Corrupted Amount | 9999 |
| Original Status | PENDING |
| Corrupted Status | CANCELLED |
| Recovery Timestamp | Pre-incident checkpoint |
| Restore Method | RestoreTableToPointInTime |
| Recovered Amount | 150 |
| Recovered Status | PENDING |
| Recovered Record Count | 3 |
| Source Table After Restore | Unchanged |
| Cleanup | Both temporary tables deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Production DynamoDB disaster recovery requires more than enabling backups. Engineers must understand recovery windows, select accurate timestamps, validate restored data, review configuration differences, and execute safe recovery procedures without losing legitimate business transactions.

---

## Official AWS Documentation

- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [DynamoDB Point-in-Time Recovery](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html)
- [Enable PITR](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery_Howitworks.html)
- [Restore DynamoDB Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/pointintimerecovery_restores.html)
- [PITR Restoration Tutorial](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.Tutorial.html)
- [AWS CLI — DescribeContinuousBackups](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/describe-continuous-backups.html)
- [AWS CLI — UpdateContinuousBackups](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/update-continuous-backups.html)
- [AWS CLI — RestoreTableToPointInTime](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/restore-table-to-point-in-time.html)
- [AWS CLI — GetItem](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/get-item.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)