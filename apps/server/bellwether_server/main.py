"""Importable app for uvicorn locally and Mangum on Lambda.

    uvicorn bellwether_server.main:app --port 8789

The store is chosen by environment: BELLWETHER_TABLE selects DynamoDB,
otherwise memory (which reseeds the simulated persona on each start).
"""

from __future__ import annotations

import os

from .app import build_app
from .store import DynamoStore, MemoryStore

table = os.environ.get("BELLWETHER_TABLE")
store = DynamoStore(table) if table else MemoryStore()
app = build_app(store=store)
