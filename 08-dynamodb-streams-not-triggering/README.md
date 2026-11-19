# Lab 08 — Amazon DynamoDB Streams Not Triggering

**AWS DynamoDB Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve a production-style event-processing failure involving Amazon DynamoDB Streams and AWS Lambda.

In modern cloud applications, DynamoDB Streams is commonly used to capture database changes and trigger downstream processing.

For example, when an e-commerce application creates an order, DynamoDB Streams can record the change and AWS Lambda can process the event.

This architecture supports:

- Event-driven applications.
- Order processing.
- Inventory synchronization.
- Audit logging.
- Data transformation.
- Serverless automation.
- Notification systems.
- Real-time data processing.

However, DynamoDB Streams events may not reach Lambda when the integration is incorrectly configured.

Possible causes include disabled event source mappings, incorrect stream ARNs, insufficient IAM permissions, Lambda execution failures, and event filtering.

In this lab, we create a DynamoDB table named `ddb-lab08-orders` with Streams enabled.

We configure the stream view type as `NEW_AND_OLD_IMAGES`.

Next, we deploy a Python Lambda function and connect it to the DynamoDB Stream through an event source mapping.

We intentionally create the mapping in a disabled state.

The application successfully writes an order to DynamoDB, but Lambda does not process the stream event.

We investigate the table, stream, Lambda configuration, IAM role, and event source mapping.

After identifying the disabled mapping, we enable it and verify that Lambda processes DynamoDB INSERT and MODIFY events.

Finally, we investigate no-op updates, inspect CloudWatch metrics, review cloud security considerations, and delete all temporary AWS resources.

### Troubleshooting Workflow

```text
Prepare WSL2 Ubuntu
          |
          v
Configure AWS CLI
          |
          v
Create DynamoDB Table
          |
          v
Enable DynamoDB Streams
          |
          v
Configure NEW_AND_OLD_IMAGES
          |
          v
Create IAM Execution Role
          |
          v
Attach Stream Permissions
          |
          v
Create Python Lambda Function
          |
          v
Deploy Lambda
          |
          v
Create Event Source Mapping
          |
          v
Mapping State = DISABLED
          |
          v
Insert DynamoDB Order
          |
          v
Stream Captures INSERT
          |
          v
Lambda Not Invoked
          |
          v
Investigate Stream Configuration
          |
          v
Investigate Event Source Mapping
          |
          v
Verify IAM Permissions
          |
          v
Root Cause Identified
          |
          v
Enable Event Source Mapping
          |
          v
Process Retained Stream Records
          |
          v
Generate New INSERT / MODIFY
          |
          v
Verify CloudWatch Logs
          |
          v
Investigate No-Op Updates
          |
          v
Review Lambda Metrics
          |
          v
Verify Complete Recovery
          |
          v
Delete AWS Lab Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-DDB-008 |
| Lab Name | DynamoDB Streams Not Triggering |
| Difficulty | Intermediate–Advanced |
| Primary AWS Services | DynamoDB, Lambda |
| Supporting Services | IAM, CloudWatch Logs, STS |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python 3, jq |
| DynamoDB Table | `ddb-lab08-orders` |
| Partition Key | `order_id` |
| Partition-Key Type | String |
| Billing Mode | PAY_PER_REQUEST |
| DynamoDB Streams | Enabled |
| Stream View Type | NEW_AND_OLD_IMAGES |
| Lambda Function | `ddb-lab08-stream-processor` |
| Lambda Runtime | Python 3.12 |
| Lambda Handler | `lambda_function.lambda_handler` |
| IAM Role | `ddb-lab08-lambda-role` |
| Event Source Mapping | Initially disabled |
| Starting Position | TRIM_HORIZON |
| Batch Size | 10 |
| Primary Fault | DynamoDB events not invoking Lambda |
| Root Cause | Disabled event source mapping |
| Remediation | Enable event source mapping |
| Verification | CloudWatch event markers |
| Additional Scenario | No-op UpdateItem |
| Project Tag | DynamoDB-Troubleshooting-Lab08 |
| Cleanup | DynamoDB, Lambda, IAM, event source mapping, CloudWatch Logs |

### Learning Objectives

- Understand DynamoDB Streams.
- Understand INSERT, MODIFY, and REMOVE events.
- Configure DynamoDB Streams using AWS CLI.
- Understand StreamViewType.
- Inspect DynamoDB Stream ARNs.
- Create IAM execution roles for Lambda.
- Understand stream-reading IAM permissions.
- Deploy Python Lambda functions.
- Understand Lambda event source mappings.
- Reproduce a disabled event source mapping.
- Investigate missing Lambda invocations.
- Troubleshoot stream-to-Lambda integration.
- Enable a disabled event source mapping.
- Verify stream event processing.
- Understand TRIM_HORIZON and LATEST.
- Investigate CloudWatch Logs.
- Understand Lambda IteratorAge.
- Investigate no-op DynamoDB updates.
- Apply least-privilege IAM permissions.
- Perform production root cause analysis.
- Safely clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

An e-commerce company uses Amazon DynamoDB to store customer orders.

The application requires an event-driven workflow.

Whenever an order is created or updated, the company wants to process the change automatically.

The architecture uses:

```text
DynamoDB → DynamoDB Streams → Lambda → CloudWatch Logs
```

A sample order is created:

```text
Order ID: ORD-8001
Status: PENDING
Amount: 150
```

The DynamoDB table successfully stores the order.

The Stream captures the INSERT event.

However, the downstream Lambda function does not process the event.

The application team notices that expected processing logs are missing.

The team suspects one of several possible problems:

- DynamoDB Streams is disabled.
- The event source mapping does not exist.
- The event source mapping is disabled.
- Lambda has insufficient IAM permissions.
- The mapping references the wrong Stream ARN.
- Lambda has execution errors.
- Events are filtered.
- The application did not actually modify the record.

The Cloud Engineering team begins investigating.

Using AWS CLI, the engineer verifies that:

- The DynamoDB table is ACTIVE.
- DynamoDB Streams is enabled.
- The Stream ARN exists.
- The Lambda function is Active.
- The IAM execution role exists.
- The event source mapping points to the correct Stream ARN.
- The event source mapping is Disabled.

The engineer identifies the disabled mapping as the root cause.

After enabling the mapping, Lambda resumes polling the stream.

The function processes the retained and newly generated events.

CloudWatch Logs confirm successful processing.

### Incident Symptoms

- DynamoDB PutItem succeeds.
- DynamoDB Streams is enabled.
- Lambda function exists.
- Lambda does not process new stream records.
- Expected application event logs are missing.
- Event source mapping state is Disabled.
- Enabling the mapping restores processing.

### Business Impact

A broken stream-processing pipeline can cause:

- Delayed order processing.
- Missing notifications.
- Delayed inventory synchronization.
- Incomplete audit processing.
- Data synchronization failures.
- Event-driven workflow interruptions.
- Increased operational risk.
- Inconsistent downstream application state.

### Incident Objective

Identify why DynamoDB Stream records are not reaching Lambda and restore event processing without unnecessarily recreating working infrastructure.

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
                 Orders Table
                      |
                      v
                DynamoDB Stream
                      |
                      v
              Event Source Mapping
                    ENABLED
                      |
                      v
                 AWS Lambda
                      |
                      v
              Process Stream Batch
                      |
                      v
                CloudWatch Logs
                      |
                      v
                Verify Delivery
```

### Broken Architecture

```text
              Order Application
                      |
                      v
                DynamoDB PutItem
                      |
                      v
                Item Stored
                      |
                      v
                DynamoDB Stream
                      |
                      v
              Event Source Mapping
                    DISABLED
                      |
                      X
                      |
                 AWS Lambda
                 Not Invoked
                      |
                      X
                      |
               Expected Logs Missing
```

### Recovered Architecture

```text
                 DynamoDB Table
                       |
                       v
                 Stream Records
                       |
                       v
                Event Source Mapping
                      ENABLED
                       |
                       v
                Lambda Polling
                       |
                       v
                Lambda Invocation
                       |
                       v
                Process Records
                       |
                       v
                Structured Log Events
                       |
                       v
                CloudWatch Logs
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon DynamoDB | Stores application orders |
| DynamoDB Streams | Captures item changes |
| AWS Lambda | Processes change events |
| Event Source Mapping | Polls stream and invokes Lambda |
| IAM Execution Role | Grants Lambda required permissions |
| CloudWatch Logs | Stores Lambda processing logs |
| CloudWatch Metrics | Monitors Lambda health |
| AWS STS | Verifies AWS caller identity |
| AWS CLI | Creates and investigates resources |
| Python | Implements Lambda handler |
| Bash | Manages configuration and deployment |
| jq | Inspects JSON evidence |

---

## 4. Understanding DynamoDB Streams

DynamoDB Streams captures item-level modifications in DynamoDB tables.

Streams records are generated for actual changes to table data.

### Stream Event Types

| Event Type | Meaning | Example |
|---|---|---|
| INSERT | Item created | New order |
| MODIFY | Existing item updated | Order status changed |
| REMOVE | Item deleted | Order removed |

### Example INSERT Event

```json
{
  "eventName": "INSERT",
  "dynamodb": {
    "Keys": {
      "order_id": {
        "S": "ORD-8001"
      }
    },
    "NewImage": {
      "order_id": {
        "S": "ORD-8001"
      },
      "status": {
        "S": "PENDING"
      }
    }
  }
}
```

This is a simplified example of a DynamoDB Stream record.

Actual Lambda events also contain metadata such as event IDs, source identifiers, sequence numbers, and stream ARNs.

### Important Characteristics

- Streams captures item changes.
- Stream records are retained for 24 hours.
- DynamoDB Streams records are ordered for changes to the same item.
- Lambda processes records using event source mappings.
- Stream delivery and Lambda processing can involve retries.
- Event consumers should be designed for duplicate processing.

### Production Lesson

A successful DynamoDB write and a successful downstream Lambda invocation are separate operations.

---

## 5. Understanding Stream View Types

DynamoDB supports four stream view types.

| Stream View Type | Captured Data |
|---|---|
| KEYS_ONLY | Primary-key attributes |
| NEW_IMAGE | New item image |
| OLD_IMAGE | Previous item image |
| NEW_AND_OLD_IMAGES | Both item images when applicable |

### Lab Configuration

```text
StreamEnabled = true

StreamViewType = NEW_AND_OLD_IMAGES
```

### Example MODIFY

Before:

```json
{
  "order_id": "ORD-8002",
  "status": "PROCESSING"
}
```

After:

```json
{
  "order_id": "ORD-8002",
  "status": "SHIPPED"
}
```

With NEW_AND_OLD_IMAGES, the MODIFY record can include both versions.

### Security Consideration

Full item images may contain sensitive information.

Production systems should avoid logging entire stream records unless genuinely necessary and appropriately protected.

---

## 6. Understanding Lambda Event Source Mappings

A Lambda event source mapping connects Lambda to a supported event source such as DynamoDB Streams.

For DynamoDB Streams, Lambda polls the stream and invokes the configured function with batches of records.

### Architecture

```text
DynamoDB Stream
       |
       v
Lambda Event Source Mapping
       |
       v
Poll Stream Records
       |
       v
Invoke Lambda Function
       |
       v
Process Batch
```

### Important Mapping Settings

| Setting | Purpose |
|---|---|
| EventSourceArn | Identifies the DynamoDB Stream |
| FunctionName | Identifies the Lambda function |
| Enabled | Controls event polling |
| StartingPosition | Determines initial record position |
| BatchSize | Maximum records per invocation batch |
| FilterCriteria | Optional event filtering |
| MaximumRetryAttempts | Controls applicable retry behavior |
| BisectBatchOnFunctionError | Helps isolate failing batches |

### Enabled vs. Disabled

**Enabled:** Lambda can poll and process eligible stream records.

**Disabled:** The mapping stops polling the stream.

Disabling the mapping does not delete the table, stream, or Lambda function.

---

## 7. Understanding TRIM_HORIZON and LATEST

When a mapping begins reading a stream, its starting position matters.

### TRIM_HORIZON

Starts from the oldest available retained stream records.

Useful for processing existing unexpired events when a new mapping starts.

### LATEST

Starts near the current end of the stream.

Records generated before the mapping begins polling may not be processed.

### Comparison

| Starting Position | Behavior |
|---|---|
| TRIM_HORIZON | Oldest retained available records |
| LATEST | New records from the initial stream position |

### Lab Choice

```text
StartingPosition = TRIM_HORIZON
```

This makes the experiment suitable for checking whether retained events can be processed after enabling a disabled mapping.

### Important Limitation

DynamoDB Streams retains records for 24 hours.

Events older than the retention window cannot be recovered from that stream.

---

## 8. Prerequisites and Safety

### Required Tools

- AWS CLI v2.
- WSL2 Ubuntu.
- Python 3.
- Bash.
- jq.
- AWS account.
- DynamoDB, Lambda, IAM, and CloudWatch Logs permissions.

### Relevant IAM Actions

```text
sts:GetCallerIdentity

dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:PutItem
dynamodb:GetItem
dynamodb:UpdateItem
dynamodb:DeleteTable
dynamodb:ListTagsOfResource

dynamodb:DescribeStream
dynamodb:GetShardIterator
dynamodb:GetRecords
dynamodb:ListStreams

lambda:CreateFunction
lambda:GetFunction
lambda:GetFunctionConfiguration
lambda:DeleteFunction
lambda:CreateEventSourceMapping
lambda:GetEventSourceMapping
lambda:UpdateEventSourceMapping
lambda:DeleteEventSourceMapping
lambda:ListEventSourceMappings
lambda:ListTags

iam:CreateRole
iam:GetRole
iam:AttachRolePolicy
iam:DetachRolePolicy
iam:DeleteRole
iam:ListAttachedRolePolicies
iam:PassRole

logs:CreateLogGroup
logs:PutRetentionPolicy
logs:DescribeLogStreams
logs:FilterLogEvents
logs:DeleteLogGroup

cloudwatch:GetMetricStatistics
```

These are relevant actions for the lab, not a complete IAM policy.

### Safety Requirements

- Use dedicated lab resource names.
- Never modify unrelated production resources.
- Use fabricated customer orders.
- Verify the AWS account and Region.
- Avoid logging sensitive item values.
- Use least-privilege IAM permissions.
- Apply log retention settings.
- Confirm resource ownership before deletion.

---

## 9. Prepare WSL2 Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-dynamodb-troubleshooting-labs

mkdir -p 08-dynamodb-streams-not-triggering

cd 08-dynamodb-streams-not-triggering
```

### Step 2 — Verify Tools

```bash
aws --version

python3 --version

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

export TABLE_NAME="ddb-lab08-orders"

export FUNCTION_NAME="ddb-lab08-stream-processor"

export ROLE_NAME="ddb-lab08-lambda-role"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export PROJECT_TAG="DynamoDB-Troubleshooting-Lab08"

export TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${TABLE_NAME}"

export FUNCTION_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"
```

### Step 4 — Verify Variables

```bash
echo "$AWS_REGION"

echo "$TABLE_NAME"

echo "$FUNCTION_NAME"

echo "$ROLE_NAME"
```

### Step 5 — Create Evidence Directory

```bash
mkdir -p evidence
```

### Step 6 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
evidence/
lab08-resources.env

*.zip
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

## 10. Verify AWS Account and Existing Resources

### Step 1 — Verify AWS Identity

```bash
aws sts get-caller-identity
```

### Step 2 — Check DynamoDB Table

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Check Lambda Function

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 4 — Check IAM Role

```bash
aws iam get-role \
  --role-name "$ROLE_NAME"
```

Expected if resources have not been created:

```text
ResourceNotFoundException
```

or:

```text
NoSuchEntity
```

If any named resource already exists, verify ownership before proceeding.

Do not overwrite unrelated resources.

---

## 11. Create DynamoDB Table With Streams

### Step 1 — Create Table

```bash
aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=order_id,AttributeType=S \
  --key-schema \
    AttributeName=order_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --stream-specification \
    StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 2 — Wait for ACTIVE Status

```bash
aws dynamodb wait table-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Stream Configuration

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    Name:TableName,
    Status:TableStatus,
    StreamEnabled:StreamSpecification.StreamEnabled,
    StreamViewType:StreamSpecification.StreamViewType,
    StreamArn:LatestStreamArn
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
TableStatus = ACTIVE

StreamEnabled = true

StreamViewType = NEW_AND_OLD_IMAGES
```

### Step 4 — Capture Stream ARN

```bash
export STREAM_ARN=$(aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.LatestStreamArn' \
  --output text \
  --region "$AWS_REGION")
```

### Step 5 — Verify Stream ARN

```bash
echo "$STREAM_ARN"
```

### Step 6 — Inspect Stream

```bash
aws dynamodbstreams describe-stream \
  --stream-arn "$STREAM_ARN" \
  --region "$AWS_REGION" \
  --query 'StreamDescription.{
    Status:StreamStatus,
    ViewType:StreamViewType,
    ARN:StreamArn
  }'
```

Expected:

```text
StreamStatus = ENABLED
```

### Step 7 — Save Evidence

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION" \
  > evidence/table-description.json
```

---

## 12. Create Lambda IAM Execution Role

### Step 1 — Create Trust Policy

Create `lambda-trust-policy.json`:

```bash
cat > lambda-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

### Step 2 — Create IAM Role

```bash
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document \
    file://lambda-trust-policy.json \
  --tags Key=Project,Value="$PROJECT_TAG"
```

### Step 3 — Attach AWS Managed Policy

```bash
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn \
    arn:aws:iam::aws:policy/service-role/AWSLambdaDynamoDBExecutionRole
```

### Step 4 — Verify Permissions

```bash
aws iam list-attached-role-policies \
  --role-name "$ROLE_NAME"
```

Expected:

```text
AWSLambdaDynamoDBExecutionRole
```

### Step 5 — Capture Role ARN

```bash
export ROLE_ARN=$(aws iam get-role \
  --role-name "$ROLE_NAME" \
  --query 'Role.Arn' \
  --output text)
```

### Step 6 — Verify Role

```bash
echo "$ROLE_ARN"
```

### Production Consideration

The AWS managed policy simplifies the lab.

For production environments, consider a custom policy scoped to the required DynamoDB Stream ARN and CloudWatch Logs resources.

---

## 13. Create Python Lambda Function

### Step 1 — Create `lambda_function.py`

```python
import json


def lambda_handler(event, context):
    records = event.get("Records", [])

    for record in records:
        event_name = record.get(
            "eventName", "UNKNOWN"
        )

        dynamodb = record.get("dynamodb", {})

        keys = dynamodb.get("Keys", {})

        order_id = (
            keys.get("order_id", {}).get("S", "UNKNOWN")
        )

        print(json.dumps({
            "marker": "LAB08_EVENT",
            "event": event_name,
            "order_id": order_id,
            "event_id": record.get("eventID")
        }))

    return {
        "statusCode": 200,
        "processed_records": len(records)
    }
```

### Step 2 — Verify Python Syntax

```bash
python3 -m py_compile lambda_function.py
```

### Step 3 — Create Deployment Package

```bash
python3 - <<'PY'
from zipfile import ZipFile

with ZipFile("lambda-package.zip", "w") as z:
    z.write("lambda_function.py")
PY
```

### Step 4 — Verify Package

```bash
ls -lh lambda-package.zip
```

### Lambda Processing Logic

```text
Lambda Receives Stream Batch
              |
              v
        Iterate Records
              |
              v
          Read Event Type
              |
              v
          Read Order ID
              |
              v
        Write Structured Log
              |
              v
       Return Processed Count
```

### Important Security Principle

The function logs only the event type, order ID, and event ID.

It does not log full item images.

---

## 14. Deploy Lambda Function

### Step 1 — Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name "$LOG_GROUP" \
  --region "$AWS_REGION"
```

### Step 2 — Configure Log Retention

```bash
aws logs put-retention-policy \
  --log-group-name "$LOG_GROUP" \
  --retention-in-days 7 \
  --region "$AWS_REGION"
```

### Step 3 — Create Lambda

```bash
aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime python3.12 \
  --handler lambda_function.lambda_handler \
  --role "$ROLE_ARN" \
  --zip-file fileb://lambda-package.zip \
  --timeout 15 \
  --memory-size 128 \
  --tags Project="$PROJECT_TAG" \
  --region "$AWS_REGION"
```

If the role has just been created, IAM propagation may temporarily prevent Lambda from assuming it. Verify the role and retry creation if necessary.

### Step 4 — Wait for Active State

```bash
aws lambda wait function-active-v2 \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{
    Name:FunctionName,
    State:State,
    Runtime:Runtime,
    Role:Role,
    Handler:Handler
  }' \
  --region "$AWS_REGION"
```

Expected:

```text
State = Active

Runtime = python3.12
```

### Step 6 — Save Evidence

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > evidence/lambda-configuration.json
```

---

## 15. Fault Injection — Disabled Event Source Mapping

### Production Fault

The Lambda event source mapping is disabled.

Therefore, Lambda does not poll the DynamoDB Stream.

### Step 1 — Create Disabled Mapping

```bash
aws lambda create-event-source-mapping \
  --function-name "$FUNCTION_NAME" \
  --event-source-arn "$STREAM_ARN" \
  --starting-position TRIM_HORIZON \
  --batch-size 10 \
  --no-enabled \
  --region "$AWS_REGION"
```

### Step 2 — Capture Mapping UUID

```bash
export MAPPING_UUID=$(aws lambda list-event-source-mappings \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --query 'EventSourceMappings[0].UUID' \
  --output text)
```

This assumes the new lab function has only the mapping created in this exercise.

### Step 3 — Verify UUID

```bash
echo "$MAPPING_UUID"
```

### Step 4 — Inspect Mapping

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --region "$AWS_REGION" \
  --query '{
    UUID:UUID,
    State:State,
    FunctionArn:FunctionArn,
    EventSourceArn:EventSourceArn,
    StartingPosition:StartingPosition
  }'
```

Expected after mapping creation completes:

```text
State = Disabled
```

### Step 5 — Save Fault Evidence

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --region "$AWS_REGION" \
  > evidence/disabled-mapping.json
```

### Root Cause

A disabled event source mapping prevents Lambda from polling DynamoDB Stream records.

---

## 16. Reproduce Missing Lambda Invocation

### Step 1 — Insert Order ORD-8001

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-8001"},
    "status": {"S": "PENDING"},
    "amount": {"N": "150"}
  }' \
  --condition-expression \
    "attribute_not_exists(order_id)" \
  --region "$AWS_REGION"
```

Expected: successful PutItem.

### Step 2 — Verify Order Exists

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-8001"}}' \
  --consistent-read \
  --region "$AWS_REGION"
```

### Step 3 — Verify Mapping Remains Disabled

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --query '{
    State:State,
    LastResult:LastProcessingResult
  }' \
  --region "$AWS_REGION"
```

Expected:

```text
State = Disabled
```

### Step 4 — Inspect CloudWatch Log Streams

```bash
aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --region "$AWS_REGION"
```

Because the mapping is disabled and the function has not been invoked separately, stream-triggered processing logs should not be present.

### Fault Findings

| Component | Result |
|---|---|
| DynamoDB PutItem | Successful |
| Item ORD-8001 | Exists |
| DynamoDB Streams | Enabled |
| Lambda Function | Active |
| Event Source Mapping | Disabled |
| Lambda Stream Processing | Not running |
| Expected Event Logs | Missing |

---

## 17. Production Investigation — Verify Stream Configuration

### Step 1 — Inspect DynamoDB Stream

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --query 'Table.{
    StreamEnabled:StreamSpecification.StreamEnabled,
    ViewType:StreamSpecification.StreamViewType,
    LatestStreamArn:LatestStreamArn
  }' \
  --region "$AWS_REGION"
```

### Step 2 — Verify Current Stream ARN

```bash
echo "$STREAM_ARN"
```

### Step 3 — Inspect Stream Directly

```bash
aws dynamodbstreams describe-stream \
  --stream-arn "$STREAM_ARN" \
  --region "$AWS_REGION"
```

### Step 4 — Verify Lambda State

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{
    State:State,
    LastUpdateStatus:LastUpdateStatus
  }' \
  --region "$AWS_REGION"
```

Expected:

```text
State = Active
```

### Investigation Findings

- The DynamoDB table exists.
- Streams is enabled.
- The Stream ARN is present.
- The Lambda function is Active.
- The incident is not caused by a missing DynamoDB table.

---

## 18. Investigate Event Source Mapping

### Step 1 — List Mappings

```bash
aws lambda list-event-source-mappings \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Specific Mapping

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --region "$AWS_REGION"
```

### Step 3 — Compare Stream ARNs

```bash
echo "Current DynamoDB Stream:"
echo "$STREAM_ARN"

echo "Mapping Stream:"
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --query EventSourceArn \
  --output text \
  --region "$AWS_REGION"
```

Both ARNs should match.

### Step 4 — Inspect IAM Policy Attachments

```bash
aws iam list-attached-role-policies \
  --role-name "$ROLE_NAME"
```

### Step 5 — Inspect Mapping State

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --query '{
    State:State,
    StateTransitionReason:StateTransitionReason,
    LastProcessingResult:LastProcessingResult,
    LastModified:LastModified
  }' \
  --region "$AWS_REGION"
```

### Root Cause Findings

| Investigation | Finding |
|---|---|
| Table Status | ACTIVE |
| Streams | Enabled |
| Stream ARN | Correct |
| Lambda State | Active |
| IAM Policy | Attached |
| Mapping ARN | Matches Stream |
| Mapping State | Disabled |
| Root Cause | Lambda polling disabled |

---

## 19. Remediation — Enable Event Source Mapping

### Step 1 — Enable Mapping

```bash
aws lambda update-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --enabled \
  --region "$AWS_REGION"
```

### Step 2 — Verify Mapping State

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --query '{
    State:State,
    LastProcessingResult:LastProcessingResult,
    EventSourceArn:EventSourceArn
  }' \
  --region "$AWS_REGION"
```

The mapping may temporarily show:

```text
Enabling
```

Expected final state:

```text
Enabled
```

### Step 3 — Save Remediation Evidence

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --region "$AWS_REGION" \
  > evidence/enabled-mapping.json
```

### Why the Remediation Works

An enabled mapping allows Lambda to poll the configured DynamoDB Stream.

Lambda can then invoke the function with eligible stream records.

Since the mapping uses TRIM_HORIZON, available retained records created before activation may also be processed.

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| DynamoDB Table | ACTIVE | ACTIVE |
| DynamoDB Streams | Enabled | Enabled |
| Lambda Function | Active | Active |
| Event Source Mapping | Disabled | Enabled |
| Stream Polling | Stopped | Active |
| Event Processing | Not occurring | Restored |

---

## 20. Verify INSERT Event Processing

### Step 1 — Create ORD-8002

```bash
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item '{
    "order_id": {"S": "ORD-8002"},
    "status": {"S": "PROCESSING"},
    "amount": {"N": "200"}
  }' \
  --condition-expression \
    "attribute_not_exists(order_id)" \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --format short \
  --region "$AWS_REGION"
```

### Expected Application Log

```json
{
  "marker": "LAB08_EVENT",
  "event": "INSERT",
  "order_id": "ORD-8002",
  "event_id": "example-event-id"
}
```

The event ID is generated by AWS.

### Step 3 — Save Evidence

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --format short \
  --region "$AWS_REGION" \
  > evidence/recovered-lambda-logs.txt
```

### Step 4 — Inspect Markers

```bash
grep 'LAB08_EVENT' \
  evidence/recovered-lambda-logs.txt
```

Expected: the INSERT event for ORD-8002 appears after processing completes.

---

## 21. Verify MODIFY Event Processing

### Step 1 — Update Order Status

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-8002"}}' \
  --update-expression \
    "SET #s = :status" \
  --expression-attribute-names '{
    "#s": "status"
  }' \
  --expression-attribute-values '{
    ":status": {"S": "SHIPPED"}
  }' \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --format short \
  --region "$AWS_REGION"
```

### Expected Event

```json
{
  "marker": "LAB08_EVENT",
  "event": "MODIFY",
  "order_id": "ORD-8002",
  "event_id": "example-event-id"
}
```

### Step 3 — Verify Mapping Health

```bash
aws lambda get-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --query '{
    State:State,
    LastProcessingResult:LastProcessingResult
  }' \
  --region "$AWS_REGION"
```

Expected state:

```text
Enabled
```

After successful batch processing, LastProcessingResult may indicate:

```text
OK
```

### Verification Conclusion

The DynamoDB Stream is successfully connected to Lambda through the enabled event source mapping.

---

## 22. Additional Fault — No-Op Update Does Not Trigger Stream Event

### Production Problem

An application executes UpdateItem but does not actually change the stored data.

For example, the order already has status:

```text
SHIPPED
```

The application sets it to:

```text
SHIPPED
```

again.

Because no actual item change occurs, DynamoDB does not create a new stream record for the no-op update.

### Step 1 — Verify Current Status

```bash
aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-8002"}}' \
  --consistent-read \
  --query 'Item.status' \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "S": "SHIPPED"
}
```

### Step 2 — Repeat Existing Value

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-8002"}}' \
  --update-expression \
    "SET #s = :status" \
  --expression-attribute-names '{
    "#s": "status"
  }' \
  --expression-attribute-values '{
    ":status": {"S": "SHIPPED"}
  }' \
  --region "$AWS_REGION"
```

Expected: successful UpdateItem.

No additional stream record should be generated for an unchanged item.

### Step 3 — Make a Real Modification

```bash
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key '{"order_id":{"S":"ORD-8002"}}' \
  --update-expression \
    "SET #s = :status" \
  --expression-attribute-names '{
    "#s": "status"
  }' \
  --expression-attribute-values '{
    ":status": {"S": "DELIVERED"}
  }' \
  --region "$AWS_REGION"
```

### Step 4 — Verify Event

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --format short \
  --region "$AWS_REGION"
```

Expected: a MODIFY event for ORD-8002.

### Important Lesson

A successful DynamoDB API operation does not always generate a new DynamoDB Stream record.

The item must actually change.

---

## 23. CloudWatch Investigation

### Relevant Lambda Metrics

| Metric | Meaning |
|---|---|
| Invocations | Function invocation count |
| Errors | Failed function invocations |
| Duration | Function execution duration |
| IteratorAge | Stream processing lag indicator |
| Throttles | Lambda invocation throttling |

### Step 1 — Configure Time Window

```bash
export START_TIME=$(date -u -d '30 minutes ago' \
  '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u \
  '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect Invocations

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Errors

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

### Step 4 — Inspect IteratorAge

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name IteratorAge \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Maximum \
  --region "$AWS_REGION"
```

### Step 5 — Save Invocation Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION" \
  > evidence/lambda-invocations.json
```

### Monitoring Interpretation

A disabled mapping may produce no stream-triggered Lambda invocations.

After remediation, successful event processing should generate invocation activity.

IteratorAge helps investigate processing delays.

Application logs are still important because invocation metrics do not identify which specific order records were processed.

---

## 24. Root Cause Analysis

### Primary Root Cause

The DynamoDB Stream and Lambda function were correctly created, but the event source mapping was disabled.

As a result, Lambda did not poll and process the available Stream records.

### Five Whys

**Why 1 — Why did Lambda not process the order?**

The Lambda function did not receive stream event batches.

**Why 2 — Why did Lambda not receive event batches?**

The event source mapping was disabled.

**Why 3 — Why does a disabled mapping prevent processing?**

Lambda stops polling the configured event source while the mapping is disabled.

**Why 4 — Why was this not immediately detected?**

The simulated environment lacked monitoring for event source mapping configuration and missing downstream processing.

**Why 5 — How can this be prevented?**

Use infrastructure-as-code configuration, deployment verification, monitoring, and operational checks for the event-driven pipeline.

### Root Cause Diagram

```text
Order Created
      |
      v
DynamoDB PutItem Successful
      |
      v
DynamoDB Stream Record Created
      |
      v
Lambda Event Source Mapping
      |
      v
Mapping Disabled
      |
      v
Stream Polling Stopped
      |
      v
Lambda Not Invoked
      |
      v
Downstream Event Processing Missing
```

### Fault Comparison

| Fault | Root Cause | Remediation |
|---|---|---|
| Disabled mapping | Polling stopped | Enable mapping |
| Streams disabled | No active stream | Enable Streams |
| Wrong stream ARN | Incorrect resource reference | Update or recreate mapping |
| Missing IAM permissions | Unable to read stream | Correct role permissions |
| Lambda handler failure | Execution error | Fix function |
| No-op update | No item change | Perform actual modification |
| Event filtering | Event excluded | Correct filter criteria |
| Expired stream records | Retention exceeded | Recover from another source |

### Root Cause Conclusion

The primary incident was caused by incorrect event source mapping configuration rather than DynamoDB table availability.

---

## 25. Production Troubleshooting Decision Tree

```text
DynamoDB Streams Not Triggering
               |
               v
      Verify DynamoDB Table
               |
               v
         Table ACTIVE?
               |
          +----+----+
          |         |
         No        Yes
          |         |
          v         v
     Fix Table   Streams Enabled?
                    |
               +----+----+
               |         |
              No        Yes
               |         |
               v         v
        Enable Streams   Check Stream ARN
                              |
                              v
                     Mapping Exists?
                              |
                         +----+----+
                         |         |
                        No        Yes
                         |         |
                         v         v
                   Create Mapping  Check State
                                      |
                                 +----+----+
                                 |         |
                              Disabled   Enabled
                                 |         |
                                 v         v
                            Enable Mapping Check IAM
                                           |
                                           v
                                     Check Lambda
                                           |
                                           v
                                     Inspect Logs
                                           |
                                           v
                                     Verify Events
```

### Investigation Checklist

| Check | Expected |
|---|---|
| AWS Account | Correct |
| AWS Region | us-east-1 |
| DynamoDB Table | ACTIVE |
| Stream Enabled | True |
| Stream View Type | NEW_AND_OLD_IMAGES |
| Stream ARN | Present |
| Lambda Function | Active |
| IAM Role | Correct |
| Stream Permissions | Sufficient |
| Event Source Mapping | Enabled |
| Mapping ARN | Matches current Stream |
| Lambda Logs | Event markers |
| Event Processing | Successful |

---

## 26. Cloud Security Engineering Considerations

### IAM Least Privilege

Lambda execution roles should have only the permissions necessary to consume the required stream and write logs.

### Stream Data Exposure

DynamoDB Stream images may contain sensitive application data.

Avoid logging complete records unnecessarily.

### CloudWatch Log Retention

Use an appropriate retention period to limit unnecessary storage and exposure.

For this lab:

```text
Retention = 7 days
```

### Monitor Configuration Changes

Unexpected changes to event source mappings can interrupt critical workflows.

Use CloudTrail and operational monitoring to investigate configuration changes.

### Idempotency

Stream events can be delivered more than once.

Applications should use appropriate idempotency controls to prevent duplicate processing.

### Avoid Processing Loops

A Lambda function that writes back to the same DynamoDB table may generate additional stream events.

Design such workflows carefully to avoid recursive event processing.

### Error Handling

Production systems may use:

- Bounded retries.
- Partial batch failure handling.
- BisectBatchOnFunctionError.
- Failure destinations.
- CloudWatch alarms.
- IteratorAge monitoring.

### Security Principle

**Event-driven cloud architectures require secure permissions, reliable processing, appropriate monitoring, and protection against duplicate or recursive event execution.**

---

## 27. Save Environment and Cleanup Resources

### Step 1 — Save Variables

```bash
cat > lab08-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export TABLE_NAME="$TABLE_NAME"
export TABLE_ARN="$TABLE_ARN"
export FUNCTION_NAME="$FUNCTION_NAME"
export FUNCTION_ARN="$FUNCTION_ARN"
export ROLE_NAME="$ROLE_NAME"
export ROLE_ARN="$ROLE_ARN"
export LOG_GROUP="$LOG_GROUP"
export STREAM_ARN="$STREAM_ARN"
export MAPPING_UUID="$MAPPING_UUID"
export PROJECT_TAG="$PROJECT_TAG"
EOF

chmod 600 lab08-resources.env
```

### Step 2 — Verify DynamoDB Ownership

```bash
aws dynamodb list-tags-of-resource \
  --resource-arn "$TABLE_ARN" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Lambda Ownership

```bash
aws lambda list-tags \
  --resource "$FUNCTION_ARN" \
  --region "$AWS_REGION"
```

Confirm:

```text
Project = DynamoDB-Troubleshooting-Lab08
```

### Step 4 — Delete Event Source Mapping

```bash
aws lambda delete-event-source-mapping \
  --uuid "$MAPPING_UUID" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Mapping Deletion

```bash
aws lambda list-event-source-mappings \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

If the mapping is still deleting, allow deletion to finish before proceeding.

### Step 6 — Delete Lambda Function

```bash
aws lambda delete-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 7 — Delete CloudWatch Log Group

```bash
aws logs delete-log-group \
  --log-group-name "$LOG_GROUP" \
  --region "$AWS_REGION"
```

### Step 8 — Detach IAM Policy

```bash
aws iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn \
    arn:aws:iam::aws:policy/service-role/AWSLambdaDynamoDBExecutionRole
```

### Step 9 — Delete IAM Role

```bash
aws iam delete-role \
  --role-name "$ROLE_NAME"
```

### Step 10 — Delete DynamoDB Table

```bash
aws dynamodb delete-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 11 — Wait for Deletion

```bash
aws dynamodb wait table-not-exists \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

### Step 12 — Verify Deletion

```bash
aws dynamodb describe-table \
  --table-name "$TABLE_NAME" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Cleanup Summary

| Resource | Expected State |
|---|---|
| DynamoDB Table | Deleted |
| DynamoDB Stream | Deleted with table |
| Lambda Function | Deleted |
| Event Source Mapping | Deleted |
| IAM Execution Role | Deleted |
| CloudWatch Log Group | Deleted |
| Local Source Code | Retained |
| Evidence Files | Retained |

---

## 28. Interview Questions and Answers

### Q1. What is DynamoDB Streams?

A feature that captures item-level changes in DynamoDB tables.

### Q2. Which events can DynamoDB Streams generate?

INSERT, MODIFY, and REMOVE.

### Q3. What does NEW_AND_OLD_IMAGES mean?

The stream record includes old and new item images where applicable.

### Q4. How does Lambda consume DynamoDB Streams?

Through a Lambda event source mapping that polls the stream and invokes the function.

### Q5. What happens when an event source mapping is disabled?

Lambda stops polling and processing records through that mapping.

### Q6. Does disabling the mapping delete stream records?

No. Records remain available according to the stream's retention period.

### Q7. What is the retention period for DynamoDB Streams?

24 hours.

### Q8. What is TRIM_HORIZON?

A starting position that begins with the oldest available stream records.

### Q9. What is LATEST?

A starting position that begins near the end of the stream.

### Q10. Why might Lambda fail to receive DynamoDB events?

Common causes include disabled mappings, missing permissions, incorrect Stream ARNs, missing mappings, and configuration errors.

### Q11. Which IAM permissions are relevant for reading DynamoDB Streams?

DescribeStream, GetShardIterator, GetRecords, and ListStreams.

### Q12. How do you inspect an event source mapping?

Use the AWS CLI GetEventSourceMapping operation.

### Q13. How do you enable a disabled mapping?

Use UpdateEventSourceMapping with Enabled set to true.

### Q14. Why might the Stream ARN change?

Disabling and re-enabling DynamoDB Streams creates a new stream.

### Q15. What is IteratorAge?

A Lambda metric that helps measure how far behind stream processing is.

### Q16. Does every successful UpdateItem create a stream record?

No. An update that does not actually modify the item does not generate a new change record.

### Q17. Why should stream consumers be idempotent?

Because event processing can involve duplicate delivery or retries.

### Q18. What is the security risk of logging full DynamoDB Stream images?

They may contain sensitive application data.

### Q19. How can you prevent recursive stream-processing loops?

Avoid uncontrolled writes back to the source table and implement safeguards around event processing.

### Q20. How would you explain this lab in a technical interview?

I created a DynamoDB table with Streams enabled and configured NEW_AND_OLD_IMAGES.

I deployed a Python Lambda function and connected it to the DynamoDB Stream using an event source mapping.

I intentionally created the mapping in a disabled state.

I inserted an order into DynamoDB and verified that the database write succeeded but Lambda did not process the event.

I investigated the DynamoDB Stream ARN, Lambda function configuration, IAM execution role, and event source mapping using AWS CLI.

The investigation identified the disabled event source mapping as the root cause.

I enabled the mapping and generated additional INSERT and MODIFY events.

I verified successful event processing through CloudWatch Logs and Lambda metrics.

I also investigated no-op updates, stream retention, retry behavior, and IAM security.

Finally, I deleted the temporary AWS resources.

This lab helped me understand how to troubleshoot production event-driven architectures using DynamoDB Streams, Lambda, IAM, and CloudWatch.

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
│   └── README.md
│
├── 08-dynamodb-streams-not-triggering/
│   ├── README.md
│   ├── .gitignore
│   │
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── lambda-package.zip
│   ├── lab08-resources.env
│   │
│   └── evidence/
│       ├── table-description.json
│       ├── lambda-configuration.json
│       ├── disabled-mapping.json
│       ├── enabled-mapping.json
│       ├── recovered-lambda-logs.txt
│       └── lambda-invocations.json
│
├── 09-point-in-time-recovery-investigation/
└── 10-dynamodb-hot-partition/
```

The repository structure shows the intended local files.

Generated archives, local environment files, and evidence files should remain excluded from Git.

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Production troubleshooting documentation |
| .gitignore | Excludes local files and evidence |
| lambda_function.py | Lambda stream-processing handler |
| lambda-trust-policy.json | IAM role trust policy |
| lambda-package.zip | Generated Lambda deployment package |
| lab08-resources.env | Local environment variables |
| table-description.json | DynamoDB configuration evidence |
| lambda-configuration.json | Lambda runtime and role configuration |
| disabled-mapping.json | Fault evidence |
| enabled-mapping.json | Remediation evidence |
| recovered-lambda-logs.txt | Processed event evidence |
| lambda-invocations.json | CloudWatch invocation metric evidence |

### Recommended Public GitHub Structure

```text
08-dynamodb-streams-not-triggering/
├── README.md
├── .gitignore
├── lambda_function.py
└── lambda-trust-policy.json
```

### Recommended Root `.gitignore`

```gitignore
# DynamoDB Lab 08
08-dynamodb-streams-not-triggering/evidence/
08-dynamodb-streams-not-triggering/lab08-resources.env
08-dynamodb-streams-not-triggering/lambda-package.zip

# Generated files
*.zip
*.log
__pycache__/
*.pyc
.venv/

# Local configuration
.env
.env.*
*-resources.env

# Credentials
*.pem
*.key
```

Do not commit AWS credentials, customer data, or unreviewed account-specific troubleshooting evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how DynamoDB Streams and AWS Lambda work together to build event-driven cloud applications.

We created a DynamoDB table with Streams enabled and configured NEW_AND_OLD_IMAGES.

We created an IAM execution role and attached the permissions required for Lambda to consume DynamoDB Streams.

We developed a Python Lambda function that processed stream records and generated structured CloudWatch Logs.

Next, we intentionally created a disabled event source mapping.

We inserted an order into the DynamoDB table and verified that the write succeeded.

However, Lambda did not process the event because the event source mapping was disabled.

We investigated the table configuration, stream status, Lambda function, IAM role, and event source mapping.

After identifying the root cause, we enabled the event source mapping.

We then generated additional INSERT and MODIFY events.

CloudWatch Logs confirmed that Lambda was processing DynamoDB Stream records.

We also investigated no-op updates and learned that DynamoDB Streams only records actual item changes.

Finally, we reviewed CloudWatch monitoring, stream retention, retry behavior, idempotency, IAM least privilege, and safe AWS resource cleanup.

**Key Lesson:** When DynamoDB Streams does not trigger Lambda, investigate the stream configuration, event source mapping, IAM permissions, Lambda execution health, and actual item changes before rebuilding resources.

### Skills Demonstrated

- Amazon DynamoDB.
- DynamoDB Streams.
- AWS Lambda.
- Python Lambda functions.
- Lambda event source mappings.
- AWS IAM execution roles.
- DynamoDB Stream permissions.
- NEW_AND_OLD_IMAGES.
- INSERT events.
- MODIFY events.
- TRIM_HORIZON.
- CloudWatch Logs.
- CloudWatch metrics.
- Lambda IteratorAge.
- Event-driven troubleshooting.
- AWS CLI v2.
- Linux Bash.
- jq.
- Root cause analysis.
- Serverless architecture.
- IAM least privilege.
- Secure event processing.
- Production incident remediation.
- Resource cleanup.

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-DDB-008 |
| Scenario | DynamoDB Streams Not Triggering |
| DynamoDB Table | ddb-lab08-orders |
| Region | us-east-1 |
| Partition Key | order_id |
| Billing Mode | PAY_PER_REQUEST |
| Streams | Enabled |
| Stream View Type | NEW_AND_OLD_IMAGES |
| Lambda Function | ddb-lab08-stream-processor |
| Lambda Runtime | Python 3.12 |
| Initial Mapping State | Disabled |
| Root Cause | Disabled event source mapping |
| Remediation | Enable mapping |
| Starting Position | TRIM_HORIZON |
| INSERT Verification | Successful |
| MODIFY Verification | Successful |
| CloudWatch Logs | LAB08_EVENT markers |
| Additional Investigation | No-op updates |
| Final Mapping State | Enabled before cleanup |
| Cleanup | AWS resources deleted |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Production event-driven architectures require more than a healthy database and function. DynamoDB Streams, Lambda event source mappings, IAM permissions, record processing, logging, and operational monitoring must all work together for reliable event delivery.

---

## Official AWS Documentation

- [Amazon DynamoDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [Using AWS Lambda with DynamoDB Streams](https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html)
- [Lambda DynamoDB Event Source Mappings](https://docs.aws.amazon.com/lambda/latest/dg/services-dynamodb-eventsourcemapping.html)
- [AWS CLI — CreateTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/create-table.html)
- [AWS CLI — DescribeTable](https://docs.aws.amazon.com/cli/latest/reference/dynamodb/describe-table.html)
- [AWS CLI — CreateFunction](https://docs.aws.amazon.com/cli/latest/reference/lambda/create-function.html)
- [AWS CLI — CreateEventSourceMapping](https://docs.aws.amazon.com/cli/latest/reference/lambda/create-event-source-mapping.html)
- [AWS CLI — GetEventSourceMapping](https://docs.aws.amazon.com/cli/latest/reference/lambda/get-event-source-mapping.html)
- [AWS CLI — UpdateEventSourceMapping](https://docs.aws.amazon.com/cli/latest/reference/lambda/update-event-source-mapping.html)
- [AWSLambdaDynamoDBExecutionRole Managed Policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambdaDynamoDBExecutionRole.html)
- [Lambda CloudWatch Metrics](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)
- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)