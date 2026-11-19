import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--payload-kib", type=int, default=8)
    parser.add_argument("--prefix", default="SPIKE")
    parser.add_argument("--output", default="evidence/load-summary.json")
    args = parser.parse_args()

    if not (1 <= args.count <= 240):
        parser.error("count must be between 1 and 240")

    if not (1 <= args.workers <= 12):
        parser.error("workers must be between 1 and 12")

    if not (1 <= args.payload_kib <= 8):
        parser.error("payload-kib must be between 1 and 8")

    client = boto3.client(
        "dynamodb",
        region_name=args.region,
        config=Config(
            connect_timeout=5,
            read_timeout=15,
            retries={
                "mode": "standard",
                "total_max_attempts": 1,
            },
        ),
    )

    payload = "X" * (args.payload_kib * 1024)

    def write_item(index):
        order_id = f"{args.prefix}-{index:04d}"

        try:
            client.put_item(
                TableName=args.table,
                Item={
                    "order_id": {"S": order_id},
                    "payload": {"S": payload},
                    "status": {"S": "TEST"},
                },
            )
            return {"status": "success"}

        except ClientError as error:
            details = error.response
            code = details["Error"]["Code"]

            return {
                "status": "error",
                "code": code,
                "throttling_reasons": details.get(
                    "ThrottlingReasons", []
                ),
            }

    with ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        results = list(executor.map(
            write_item, range(args.count)
        ))

    counts = Counter(
        result.get("code", "Success")
        for result in results
    )

    throttling_reasons = []
    for result in results:
        throttling_reasons.extend(
            result.get("throttling_reasons", [])
        )

    summary = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "table": args.table,
        "attempted": args.count,
        "workers": args.workers,
        "payload_kib": args.payload_kib,
        "results": dict(counts),
        "throttling_reasons": throttling_reasons[:10],
    }

    print(json.dumps(summary, indent=2))

    with open(args.output, "w") as file:
        json.dump(summary, file, indent=2)


if __name__ == "__main__":
    main()