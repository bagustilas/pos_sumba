"""
Supabase REST API client untuk POS SUMBA Web
Menggunakan 'requests' murni — tanpa package supabase-py
"""

import os
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _base_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


# ─── QUERY BUILDER ──────────────────────────────────────────
class QueryBuilder:
    def __init__(self, table: str):
        self._table   = table
        self._filters = []       # list of (col, operator, value)
        self._select  = "*"
        self._order   = None
        self._limit   = None
        self._offset  = None
        self._range_from = None
        self._range_to   = None
        self._single  = False
        self._method  = "GET"
        self._body    = None
        self._count   = None     # "exact" | None

    def select(self, columns: str, count: str = None):
        self._select = columns
        self._count  = count
        return self

    def eq(self, col: str, val):
        self._filters.append((col, "eq", val))
        return self

    def neq(self, col: str, val):
        self._filters.append((col, "neq", val))
        return self

    def ilike(self, col: str, pattern: str):
        self._filters.append((col, "ilike", pattern))
        return self

    def lt(self, col: str, val):
        self._filters.append((col, "lt", val))
        return self

    def lte(self, col: str, val):
        self._filters.append((col, "lte", val))
        return self

    def gte(self, col: str, val):
        self._filters.append((col, "gte", val))
        return self

    def order(self, col: str, desc: bool = False):
        self._order = f"{col}.{'desc' if desc else 'asc'}"
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def range(self, from_: int, to_: int):
        """Pagination: ambil baris from_ sampai to_ (inclusive)"""
        self._range_from = from_
        self._range_to   = to_
        return self

    def single(self):
        self._single = True
        return self

    def insert(self, data):
        self._method = "POST"
        self._body   = data
        return self

    def update(self, data: dict):
        self._method = "PATCH"
        self._body   = data
        return self

    def delete(self):
        self._method = "DELETE"
        return self

    def execute(self):
        url = f"{SUPABASE_URL}/rest/v1/{self._table}"

        qs = []

        if self._method == "GET":
            qs.append(("select", self._select))

        for col, op, val in self._filters:
            qs.append((col, f"{op}.{val}"))

        if self._order:
            qs.append(("order", self._order))
        if self._limit:
            qs.append(("limit", str(self._limit)))
        if self._offset:
            qs.append(("offset", str(self._offset)))

        headers = _base_headers()

        # Range header untuk pagination
        if self._range_from is not None and self._range_to is not None:
            headers["Range"] = f"{self._range_from}-{self._range_to}"
            headers["Range-Unit"] = "items"

        # Count header untuk total rows
        if self._count == "exact":
            headers["Prefer"] = "count=exact"

        if self._single:
            headers["Accept"] = "application/vnd.pgrst.object+json"

        if self._method == "GET":
            resp = requests.get(url, headers=headers, params=qs)
        elif self._method == "POST":
            resp = requests.post(url, headers=headers, params=qs, json=self._body)
        elif self._method == "PATCH":
            resp = requests.patch(url, headers=headers, params=qs, json=self._body)
        elif self._method == "DELETE":
            resp = requests.delete(url, headers=headers, params=qs)

        if resp.status_code == 406:
            return _Result(None, None)

        resp.raise_for_status()

        try:
            data = resp.json()
        except Exception:
            data = None

        # Ambil total count dari header Content-Range
        # Format: "0-49/32193"
        count = None
        content_range = resp.headers.get("Content-Range", "")
        if "/" in content_range:
            try:
                count = int(content_range.split("/")[1])
            except:
                pass

        return _Result(data, count)


class _Result:
    def __init__(self, data, count=None):
        self.data  = data
        self.count = count


# ─── TABLE ACCESSOR ─────────────────────────────────────────
class SupabaseClient:
    def table(self, name: str) -> QueryBuilder:
        return QueryBuilder(name)


_client = SupabaseClient()


def get_supabase() -> SupabaseClient:
    return _client