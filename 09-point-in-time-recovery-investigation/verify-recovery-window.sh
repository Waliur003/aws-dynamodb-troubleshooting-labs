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
      echo "ERROR: Recovery point is earlier than the recoverable window."
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

  echo "Attempt $attempt: recovery point not yet eligible."
  sleep 30
done

echo "Recovery point did not become eligible in the bounded check."
exit 1
