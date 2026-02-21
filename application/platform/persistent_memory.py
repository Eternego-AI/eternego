"""Persistent memory — a keyed store backed by JSON files on disk."""

import json
from pathlib import Path
from typing import Callable

from application.platform import crypto

_cache: dict[str, "Storage"] = {}


class Storage:
    def __init__(self, path: Path, initial_content: list | None = None):
        self.store = {
            "path": path,
            "content": initial_content if initial_content is not None else [],
        }


def _hash(storage_id: str) -> str:
    return crypto.sha256(json.dumps(_cache[storage_id].store["content"], sort_keys=True))


def load(storage_id: str, path: Path) -> str:
    if storage_id in _cache and read(storage_id):
        return _hash(storage_id)
    path = Path(path)
    content = json.loads(path.read_text()) if path.exists() else []
    _cache[storage_id] = Storage(path, content)
    return _hash(storage_id)


def append(storage_id: str, item: dict) -> None:
    _cache[storage_id].store["content"].append(item)
    save(storage_id)


def filter_by(storage_id: str, predicate: Callable[[dict], bool]) -> list:
    return [item for item in read(storage_id) if predicate(item)]


def remove_where(storage_id: str, predicate: Callable[[dict], bool]) -> None:
    _cache[storage_id].store["content"] = [
        item for item in _cache[storage_id].store["content"] if not predicate(item)
    ]
    save(storage_id)


def clear(storage_id: str) -> None:
    _cache[storage_id].store["content"] = []
    save(storage_id)


def read(storage_id: str) -> list:
    return _cache[storage_id].store["content"] if storage_id in _cache else []


def verify(storage_id: str, confirm_hash: str) -> bool:
    if storage_id not in _cache:
        return False
    return _hash(storage_id) == confirm_hash


def save(storage_id: str) -> None:
    _cache[storage_id].store["path"].write_text(json.dumps(_cache[storage_id].store["content"], indent=2))
