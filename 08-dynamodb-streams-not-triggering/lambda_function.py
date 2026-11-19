import json


def lambda_handler(event, context):
    records = event.get("Records", [])

    for record in records:
        event_name = record.get("eventName", "UNKNOWN")

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