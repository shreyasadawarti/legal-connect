import re
from datetime import datetime
from typing import Any, Optional

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.database import get_database
from app.main import app


class _Result:
    def __init__(self, inserted_id: Any) -> None:
        self.inserted_id = inserted_id


class _UpdateResult:
    def __init__(self, matched_count: int = 0, modified_count: int = 0) -> None:
        self.matched_count = matched_count
        self.modified_count = modified_count


class _DeleteResult:
    def __init__(self, deleted_count: int = 0) -> None:
        self.deleted_count = deleted_count


def _eq(actual: Any, expected: Any) -> bool:
    if isinstance(expected, ObjectId) or isinstance(actual, ObjectId):
        return str(actual) == str(expected)
    return actual == expected


def _match_condition(actual: Any, condition: Any) -> bool:
    if not isinstance(condition, dict):
        return _eq(actual, condition)
    for op, value in condition.items():
        if op == "$in":
            if actual not in value:
                return False
        elif op == "$nin":
            if actual in value:
                return False
        elif op == "$ne":
            if _eq(actual, value):
                return False
        elif op == "$type":
            expected_type = value if isinstance(value, str) else (value or "")
            if expected_type == "double":
                if not isinstance(actual, float):
                    return False
            elif expected_type == "string":
                if not isinstance(actual, str):
                    return False
            elif expected_type == "int":
                if not isinstance(actual, int):
                    return False
            elif expected_type == "bool":
                if not isinstance(actual, bool):
                    return False
            elif expected_type == "null":
                if actual is not None:
                    return False
            elif expected_type == "array":
                if not isinstance(actual, list):
                    return False
        elif op == "$gte":
            if not (actual is not None and actual >= value):
                return False
        elif op == "$gt":
            if not (actual is not None and actual > value):
                return False
        elif op == "$lte":
            if not (actual is not None and actual <= value):
                return False
        elif op == "$lt":
            if not (actual is not None and actual < value):
                return False
        elif op == "$regex":
            pattern = value
            options = condition.get("$options", "")
            if not isinstance(actual, str):
                return False
            flags = 0
            if "i" in options:
                flags |= re.IGNORECASE
            if re.search(pattern, actual, flags) is None:
                return False
        else:
            return False
    return True


def _matches(doc: dict[str, Any], filt: dict[str, Any]) -> bool:
    for key, expected in filt.items():
        if key == "$or":
            if not any(_matches(doc, sub) for sub in expected):
                return False
            continue
        actual = doc.get(key)
        if isinstance(actual, list) and not isinstance(expected, dict) and key != "$or":
            if isinstance(expected, list):
                if actual != expected:
                    return False
                continue
            if expected not in actual:
                return False
            continue
        matched = (
            _match_condition(actual, expected)
            if isinstance(expected, dict)
            else _eq(actual, expected)
        )
        if not matched:
            return False
    return True


class _FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs
        self._sort = None
        self._skip = 0
        self._limit = None

    def sort(self, key: Any, direction: int = 1) -> "_FakeCursor":
        key_name = key[0] if isinstance(key, (list, tuple)) else key
        self._sort = (key_name, direction)
        return self

    def skip(self, n: int) -> "_FakeCursor":
        self._skip = n
        return self

    def limit(self, n: int) -> "_FakeCursor":
        self._limit = n
        return self

    async def to_list(self, length: Optional[int] = None) -> list[dict[str, Any]]:
        docs = self._docs
        if self._sort:
            key_name, direction = self._sort
            docs = list(docs)
            docs.sort(
                key=lambda d: d.get(key_name) if d.get(key_name) is not None else "",
                reverse=(direction == -1),
            )
        if self._skip:
            docs = docs[self._skip :]
        if self._limit is not None:
            docs = docs[: self._limit]
        return [dict(d) for d in docs]


class _FakeAggregation:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    async def to_list(self, length: Optional[int] = None) -> list[dict[str, Any]]:
        return [dict(d) for d in self._docs]


class FakeCollection:
    """Minimal in-memory stand-in for a Motor collection (methods the repos use)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._docs: list[dict[str, Any]] = []
        self._next_id = 1

    def _new_id(self) -> ObjectId:
        return ObjectId(f"{self._next_id:024x}")

    async def create_index(self, key, **kwargs) -> str:
        return "idx"

    async def find_one(self, filt: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        filt = filt or {}
        for doc in self._docs:
            if _matches(doc, filt):
                return dict(doc)
        return None

    def find(self, filt: Optional[dict[str, Any]] = None) -> "_FakeCursor":
        filt = filt or {}
        selected = [doc for doc in self._docs if _matches(doc, filt)]
        return _FakeCursor(selected)

    async def count_documents(self, filt: dict[str, Any]) -> int:
        if not filt:
            return len(self._docs)
        return len([d for d in self._docs if _matches(d, filt)])

    def aggregate(self, pipeline: list[dict[str, Any]]) -> "_FakeAggregation":
        docs = [dict(d) for d in self._docs]
        for stage in pipeline:
            for op, val in stage.items():
                if op == "$match":
                    docs = [d for d in docs if _matches(d, val)]
                elif op == "$unwind":
                    field = val.lstrip("$")
                    expanded: list[dict[str, Any]] = []
                    for d in docs:
                        arr = d.get(field)
                        if not isinstance(arr, list):
                            continue
                        for item in arr:
                            nd = dict(d)
                            nd[field] = item
                            expanded.append(nd)
                    docs = expanded
                elif op == "$sort":
                    for key, direction in val.items():
                        docs.sort(
                            key=lambda d, k=key: d.get(k) if d.get(k) is not None else "",
                            reverse=(direction == -1),
                        )
                elif op == "$limit":
                    docs = docs[: val]
                elif op == "$group":
                    _id_spec = val.get("_id")
                    grouped: dict[Any, dict[str, Any]] = {}
                    for d in docs:
                        if isinstance(_id_spec, dict) and "$dateToString" in _id_spec:
                            raw = d.get(_id_spec["$dateToString"].get("date", "").lstrip("$"))
                            if isinstance(raw, datetime):
                                key = raw.strftime(_id_spec["$dateToString"].get("format", "%Y-%m"))
                            else:
                                key = None
                        elif isinstance(_id_spec, str):
                            key = d.get(_id_spec.lstrip("$"))
                        else:
                            key = _id_spec
                        if key not in grouped:
                            before: dict[str, Any] = {"_id": key}
                            for k, acc in val.items():
                                if k == "_id":
                                    continue
                                if isinstance(acc, dict) and acc.get("$sum") == 1:
                                    before[k] = 0
                                elif isinstance(acc, dict) and "$sum" in acc:
                                    before[k] = 0.0
                                elif isinstance(acc, str) and acc.startswith("$"):
                                    before[k] = d.get(acc.lstrip("$"))
                            grouped[key] = before
                        for k, acc in val.items():
                            if k == "_id":
                                continue
                            if isinstance(acc, dict) and acc.get("$sum") == 1:
                                grouped[key][k] += 1
                            elif isinstance(acc, dict) and "$sum" in acc:
                                grouped[key][k] += float(d.get(acc["$sum"].lstrip("$"), 0) or 0)
                    docs = list(grouped.values())
        return _FakeAggregation(docs)

    async def _apply_update(self, doc: dict[str, Any], update: dict[str, Any]) -> None:
        for op, fields in update.items():
            if op == "$set":
                for k, v in fields.items():
                    doc[k] = v
            elif op == "$setOnInsert":
                for k, v in fields.items():
                    doc.setdefault(k, v)

    async def insert_one(self, doc: dict[str, Any]):
        _id = doc.get("_id") or self._new_id()
        doc = dict(doc)
        doc["_id"] = _id
        self._docs.append(doc)
        self._next_id += 1
        return _Result(_id)

    async def update_one(self, filt: dict[str, Any], update: dict[str, Any]):
        for doc in self._docs:
            if _matches(doc, filt):
                await self._apply_update(doc, update)
                return _UpdateResult(1, 1)
        return _UpdateResult(0, 0)

    async def update_many(self, filt: dict[str, Any], update: dict[str, Any]):
        matched = 0
        for doc in self._docs:
            if _matches(doc, filt):
                await self._apply_update(doc, update)
                matched += 1
        return _UpdateResult(matched, matched)

    async def find_one_and_update(self, filt: dict[str, Any], update: dict[str, Any], **kwargs):
        upsert = kwargs.get("upsert", False)
        return_document = kwargs.get("return_document", False)
        for doc in self._docs:
            if _matches(doc, filt):
                await self._apply_update(doc, update)
                return dict(doc)
        if upsert:
            new_doc: dict[str, Any] = {}
            for op, fields in update.items():
                if op in ("$set", "$setOnInsert"):
                    new_doc.update(fields)
            # Any non-operator key in $set-style filters within $set is already applied.
            new_doc["_id"] = self._new_id()
            for k, v in filt.items():
                if not k.startswith("$"):
                    new_doc.setdefault(k, v)
            self._docs.append(new_doc)
            self._next_id += 1
            return dict(new_doc)
        return None

    async def delete_one(self, filt: dict[str, Any]):
        for i, doc in enumerate(self._docs):
            if _matches(doc, filt):
                del self._docs[i]
                return _DeleteResult(1)
        return _DeleteResult(0)


class FakeDatabase:
    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        if name not in self._collections:
            self._collections[name] = FakeCollection(name)
        return self._collections[name]


@pytest.fixture
def fake_db():
    return FakeDatabase()


@pytest.fixture
async def client(fake_db):
    async def _override():
        return fake_db

    app.dependency_overrides[get_database] = _override
    # Disable slowapi rate limiting so tests are not throttled by cumulative
    # per-IP counters across a shared app instance.
    limiter = app.state.limiter
    was_enabled = getattr(limiter, "enabled", True)
    try:
        limiter.enabled = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        try:
            limiter.enabled = was_enabled
        except Exception:  # noqa: BLE001
            pass
