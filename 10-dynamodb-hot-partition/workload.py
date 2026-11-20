import argparse
import json
from collections import Counter
from datetime import datetime, timezone

import boto3


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--table", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument(
        "--mode",
        choices=["hot", "sharded"],
        required=True
    )
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    dynamodb = boto3.resource(
        "dynamodb",
        region_name=args.region
    )

    table = dynamodb.Table(args.table)

    records = []
    counts = Counter()

    if args.mode == "hot":

        # 80 writes for one very busy tenant.
        for i in range(80):
            records.append({
                "tenant_bucket": "TENANT-1001",
                "tenant_id": "TENANT-1001",
                "order_id": f"HOT-{i:04d}",
                "status": "PENDING",
                "amount": 100
            })

        # 20 writes evenly distributed across 10 tenants.
        for i in range(20):
            tenant = f"TENANT-{2000 + (i % 10)}"

            records.append({
                "tenant_bucket": tenant,
                "tenant_id": tenant,
                "order_id": f"OTHER-{i:04d}",
                "status": "PENDING",
                "amount": 100
            })

    else:

        # 80 writes distributed across 10 shard keys.
        for i in range(80):
            shard = i % 10

            records.append({
                "tenant_bucket": f"TENANT-1001#{shard:02d}",
                "tenant_id": "TENANT-1001",
                "order_id": f"SHARD-{i:04d}",
                "status": "PENDING",
                "amount": 100
            })

    with table.batch_writer() as batch:
        for item in records:
            batch.put_item(Item=item)
            counts[item["tenant_bucket"]] += 1

    result = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "mode": args.mode,
        "table": args.table,
        "attempted": len(records),
        "completed": len(records),
        "partition_key_counts": dict(
            sorted(counts.items())
        ),
        "largest_partition_key_count": max(
            counts.values()
        )
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()