"""Storage: feature rows, annotations, spoken-check results, and small
metadata. Never text.

The design follows Nightlight's event log. What is stored is the raw day
feature rows, exactly as the extractor produced them. Assessments, tiers,
trends and reports are derived from those rows on every read by the pure
engine, never stored, so a summary can never drift from the days that
produced it and a config change re-derives the whole history.

Two implementations behind one interface: memory for tests and the local
server, DynamoDB when deployed. The MCP layer and the API never know which.
"""

from __future__ import annotations

import json
from collections import defaultdict


class Store:
    """The interface. Synchronous on purpose: boto3 is synchronous, FastAPI
    runs sync handlers in a threadpool, and the calls are tiny."""

    def put_day(self, profile_id: str, day: dict) -> None:
        raise NotImplementedError

    def list_days(self, profile_id: str) -> list[dict]:
        raise NotImplementedError

    def put_annotation(self, profile_id: str, date: str, note: str) -> None:
        raise NotImplementedError

    def list_annotations(self, profile_id: str) -> dict[str, str]:
        raise NotImplementedError

    def put_check(self, profile_id: str, check: dict) -> None:
        raise NotImplementedError

    def list_checks(self, profile_id: str) -> list[dict]:
        raise NotImplementedError

    def put_meta(self, profile_id: str, key: str, value: str) -> None:
        raise NotImplementedError

    def get_meta(self, profile_id: str, key: str) -> str | None:
        raise NotImplementedError

    def reset(self, profile_id: str) -> None:
        raise NotImplementedError


class MemoryStore(Store):
    def __init__(self) -> None:
        self._days: dict[str, dict[str, dict]] = defaultdict(dict)
        self._ann: dict[str, dict[str, str]] = defaultdict(dict)
        self._checks: dict[str, list[dict]] = defaultdict(list)
        self._meta: dict[str, dict[str, str]] = defaultdict(dict)

    def put_day(self, profile_id, day):
        self._days[profile_id][day["date"]] = dict(day)

    def list_days(self, profile_id):
        return [self._days[profile_id][d] for d in sorted(self._days[profile_id])]

    def put_annotation(self, profile_id, date, note):
        self._ann[profile_id][date] = note

    def list_annotations(self, profile_id):
        return dict(self._ann[profile_id])

    def put_check(self, profile_id, check):
        self._checks[profile_id].append(dict(check))

    def list_checks(self, profile_id):
        return sorted(self._checks[profile_id], key=lambda c: c.get("at", ""))

    def put_meta(self, profile_id, key, value):
        self._meta[profile_id][key] = value

    def get_meta(self, profile_id, key):
        return self._meta[profile_id].get(key)

    def reset(self, profile_id):
        for table in (self._days, self._ann, self._checks, self._meta):
            table.pop(profile_id, None)


class DynamoStore(Store):
    """One on-demand table. Partition key ``PROFILE#{id}``; sort-key
    prefixes ``DAY#``, ``ANN#``, ``CHECK#``, ``META#``. Reading a profile's
    history is a single partition query."""

    def __init__(self, table_name: str, client=None) -> None:
        import boto3  # lazy: tests never touch AWS

        self._table = (client or boto3.resource("dynamodb")).Table(table_name)

    @staticmethod
    def _pk(profile_id: str) -> str:
        return f"PROFILE#{profile_id}"

    def _query(self, profile_id: str, prefix: str) -> list[dict]:
        from boto3.dynamodb.conditions import Key

        items: list[dict] = []
        kwargs = {
            "KeyConditionExpression": Key("pk").eq(self._pk(profile_id))
            & Key("sk").begins_with(prefix)
        }
        while True:
            res = self._table.query(**kwargs)
            items.extend(res.get("Items", []))
            if "LastEvaluatedKey" not in res:
                return items
            kwargs["ExclusiveStartKey"] = res["LastEvaluatedKey"]

    def put_day(self, profile_id, day):
        self._table.put_item(
            Item={
                "pk": self._pk(profile_id),
                "sk": f"DAY#{day['date']}",
                # Stored as a JSON string: DynamoDB floats need Decimal, and
                # a feature row is read back whole, never queried by field.
                "body": json.dumps(day),
            }
        )

    def list_days(self, profile_id):
        rows = self._query(profile_id, "DAY#")
        return [json.loads(r["body"]) for r in sorted(rows, key=lambda r: r["sk"])]

    def put_annotation(self, profile_id, date, note):
        self._table.put_item(
            Item={"pk": self._pk(profile_id), "sk": f"ANN#{date}", "note": note}
        )

    def list_annotations(self, profile_id):
        return {r["sk"][4:]: r["note"] for r in self._query(profile_id, "ANN#")}

    def put_check(self, profile_id, check):
        self._table.put_item(
            Item={
                "pk": self._pk(profile_id),
                "sk": f"CHECK#{check.get('at', '')}#{check.get('kind', '')}",
                "body": json.dumps(check),
            }
        )

    def list_checks(self, profile_id):
        rows = self._query(profile_id, "CHECK#")
        return [json.loads(r["body"]) for r in sorted(rows, key=lambda r: r["sk"])]

    def put_meta(self, profile_id, key, value):
        self._table.put_item(
            Item={"pk": self._pk(profile_id), "sk": f"META#{key}", "value": value}
        )

    def get_meta(self, profile_id, key):
        res = self._table.get_item(Key={"pk": self._pk(profile_id), "sk": f"META#{key}"})
        item = res.get("Item")
        return item["value"] if item else None

    def reset(self, profile_id):
        from boto3.dynamodb.conditions import Key

        rows = []
        kwargs = {"KeyConditionExpression": Key("pk").eq(self._pk(profile_id))}
        while True:
            res = self._table.query(**kwargs)
            rows.extend(res.get("Items", []))
            if "LastEvaluatedKey" not in res:
                break
            kwargs["ExclusiveStartKey"] = res["LastEvaluatedKey"]
        with self._table.batch_writer() as batch:
            for r in rows:
                batch.delete_item(Key={"pk": r["pk"], "sk": r["sk"]})
