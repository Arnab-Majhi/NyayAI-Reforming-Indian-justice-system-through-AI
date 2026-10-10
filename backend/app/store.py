"""Small document store: MongoDB or explicitly selected, durable SQLite demo storage."""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager

from . import config


class StorageUnavailable(RuntimeError):
    pass


class Store:
    def __init__(self, mode=None, path=None):
        self.mode = mode or config.STORAGE
        self.path = path or config.DATA / "nyayaai.sqlite3"
        self.lock = threading.RLock()
        self.mongo = None

    def connect(self):
        if self.mode == "mongodb":
            from pymongo import MongoClient
            try:
                self.mongo = MongoClient(os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=2500)
                self.mongo.admin.command("ping")
                self.db = self.mongo[os.getenv("MONGODB_DATABASE", "nyayaai_demo")]
                for name in COLLECTIONS:
                    self.db[name].create_index("id", unique=True)
                for name in ("cases", "documents", "reports", "filings", "tasks"):
                    self.db[name].create_index("owner_id")
                    self.db[name].create_index("case_id")
                self.db.cases.create_index([("status", 1), ("category", 1)])
            except Exception as exc:
                raise StorageUnavailable("MongoDB unavailable. Start MongoDB or explicitly set STORAGE_MODE=sqlite in backend/.env.") from exc
        elif self.mode == "sqlite":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connection() as db:
                db.execute("CREATE TABLE IF NOT EXISTS records (collection TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(collection,id))")
                db.execute("CREATE INDEX IF NOT EXISTS records_collection ON records(collection)")
        else:
            raise StorageUnavailable("STORAGE_MODE must be mongodb or sqlite.")

    @contextmanager
    def connection(self):
        with sqlite3.connect(self.path, timeout=10) as db:
            yield db

    def all(self, collection):
        if self.mode == "mongodb":
            return list(self.db[collection].find({}, {"_id": 0}))
        with self.connection() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body FROM records WHERE collection=?", (collection,))]

    def get(self, collection, identifier):
        if self.mode == "mongodb":
            return self.db[collection].find_one({"id": identifier}, {"_id": 0})
        with self.connection() as db:
            row = db.execute("SELECT body FROM records WHERE collection=? AND id=?", (collection, identifier)).fetchone()
            return json.loads(row[0]) if row else None

    def put(self, collection, record):
        if self.mode == "mongodb":
            self.db[collection].replace_one({"id": record["id"]}, record, upsert=True)
        else:
            with self.connection() as db:
                db.execute("INSERT INTO records VALUES(?,?,?) ON CONFLICT(collection,id) DO UPDATE SET body=excluded.body", (collection, record["id"], json.dumps(record)))
        return record

    def delete(self, collection, identifier):
        if self.mode == "mongodb":
            self.db[collection].delete_one({"id": identifier})
        else:
            with self.connection() as db:
                db.execute("DELETE FROM records WHERE collection=? AND id=?", (collection, identifier))

    def clear(self):
        for name in COLLECTIONS:
            if self.mode == "mongodb":
                self.db[name].delete_many({})
            else:
                with self.connection() as db:
                    db.execute("DELETE FROM records WHERE collection=?", (name,))

    def ping(self):
        if self.mode == "mongodb":
            self.mongo.admin.command("ping")
        else:
            with self.connection() as db:
                db.execute("SELECT count(*) FROM records").fetchone()


COLLECTIONS = ("users", "sessions", "cases", "documents", "sources", "filings", "tasks", "predictions", "reports", "audit", "research", "conversations")
store = Store()