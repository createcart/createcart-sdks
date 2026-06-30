"""Database handle + tenant registry (tenant_id 0..n ↔ english name).

Owns the shared ``tenants`` table and creates the per-tenant data tables
(``menu_items_<id>``, ``categories_<id>``, ``combos_<id>``, ``carts_<id>``,
``payments_<id>``) on demand. A new connection is opened per operation, so the
handle is safe to share across threads/requests.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Optional

# English-word / slug tenant names only — also keeps generated table names safe.
_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def _per_tenant_ddl(tid: int) -> list[str]:
    return [
        f"""CREATE TABLE IF NOT EXISTS menu_items_{tid} (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, name_localized TEXT,
            description TEXT, price TEXT, currency TEXT, image_url TEXT, icon TEXT,
            category TEXT, tags TEXT, available INTEGER, stock INTEGER,
            sort_order INTEGER, metadata TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS categories_{tid} (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, sort_order INTEGER, metadata TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS combos_{tid} (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, price TEXT, currency TEXT,
            description TEXT, item_ids TEXT, tags TEXT, available INTEGER,
            sort_order INTEGER, metadata TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS carts_{tid} (
            cart_id TEXT PRIMARY KEY, data TEXT NOT NULL)""",
        f"""CREATE TABLE IF NOT EXISTS payments_{tid} (
            order_id TEXT PRIMARY KEY, status TEXT, amount INTEGER, currency TEXT,
            provider TEXT, cart_id TEXT, payment_id TEXT, data TEXT NOT NULL)""",
        f"""CREATE TABLE IF NOT EXISTS deliveries_{tid} (
            order_id TEXT PRIMARY KEY, status TEXT, created_at TEXT,
            data TEXT NOT NULL)""",
    ]


class Database:
    """SQLite database + tenant registry."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        # Cache of resolved tenant ids so repeat store builds don't re-hit the DB.
        self._tenant_ids: dict[str, int] = {}
        parent = Path(self.path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS tenants ("
                "  id INTEGER PRIMARY KEY,"      # 0..n, assigned explicitly
                "  name TEXT NOT NULL UNIQUE,"
                "  password_hash TEXT,"          # opaque hash (API hashes/verifies)
                "  base_url TEXT)"               # the tenant's API base URL
            )
            # Migrate older DBs that predate the auth columns.
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(tenants)")}
            if "password_hash" not in cols:
                conn.execute("ALTER TABLE tenants ADD COLUMN password_hash TEXT")
            if "base_url" not in cols:
                conn.execute("ALTER TABLE tenants ADD COLUMN base_url TEXT")
            conn.commit()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ── tenant registry ──────────────────────────────────────────────────
    def get_or_create_tenant(self, name: str, *, tenant_id: Optional[int] = None) -> int:
        """Return the tenant_id for ``name``, creating it (and its per-tenant
        tables) if new. IDs are assigned sequentially from 0, or you may pass an
        explicit ``tenant_id`` when onboarding."""
        cached = self._tenant_ids.get(name)
        if cached is not None:
            return cached
        if not _NAME_RE.match(name):
            raise ValueError(
                f"invalid tenant name {name!r}: use a lowercase english "
                "word/slug like 'brahmana-naivedyam'"
            )
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT id FROM tenants WHERE name=?", (name,)
            ).fetchone()
            if row is not None:
                tid = int(row["id"])
            elif tenant_id is not None:
                taken = conn.execute(
                    "SELECT 1 FROM tenants WHERE id=?", (tenant_id,)
                ).fetchone()
                if taken:
                    raise ValueError(f"tenant id {tenant_id} is already in use")
                tid = int(tenant_id)
                conn.execute("INSERT INTO tenants(id, name) VALUES(?, ?)", (tid, name))
            else:
                m = conn.execute("SELECT MAX(id) AS m FROM tenants").fetchone()["m"]
                tid = 0 if m is None else int(m) + 1
                conn.execute(
                    "INSERT INTO tenants(id, name) VALUES(?, ?)", (tid, name)
                )
            for ddl in _per_tenant_ddl(tid):
                conn.execute(ddl)
            conn.commit()
        self._tenant_ids[name] = tid
        return tid

    def update_tenant(
        self,
        name: str,
        *,
        password_hash: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """Set the password hash and/or base URL for an existing tenant."""
        sets, vals = [], []
        if password_hash is not None:
            sets.append("password_hash=?")
            vals.append(password_hash)
        if base_url is not None:
            sets.append("base_url=?")
            vals.append(base_url)
        if not sets:
            return
        vals.append(name)
        with closing(self.connect()) as conn:
            conn.execute(
                f"UPDATE tenants SET {', '.join(sets)} WHERE name=?", vals
            )
            conn.commit()

    def get_tenant(self, name: str) -> Optional[dict]:
        """Full tenant record (id, name, password_hash, base_url) or None."""
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT id, name, password_hash, base_url FROM tenants WHERE name=?",
                (name,),
            ).fetchone()
            return dict(row) if row else None

    def delete_tenant(self, name: str) -> bool:
        """Delete a tenant and DROP all of its per-tenant tables (menu, carts,
        payments, deliveries, …). Returns True if a tenant was removed. This is
        destructive and irreversible — all of the tenant's data goes with it."""
        tid = self.tenant_id(name)
        if tid is None:
            return False
        with closing(self.connect()) as conn:
            for base in (
                "menu_items", "categories", "combos", "carts", "payments", "deliveries",
            ):
                conn.execute(f"DROP TABLE IF EXISTS {base}_{tid}")
            conn.execute("DELETE FROM tenants WHERE name=?", (name,))
            conn.commit()
        self._tenant_ids.pop(name, None)
        return True

    def list_tenants_full(self) -> list[dict]:
        """All tenants as dicts with id, name, base_url (no password)."""
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT id, name, base_url FROM tenants ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def tenant_id(self, name: str) -> Optional[int]:
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT id FROM tenants WHERE name=?", (name,)
            ).fetchone()
            return int(row["id"]) if row else None

    def tenant_name(self, tenant_id: int) -> Optional[str]:
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT name FROM tenants WHERE id=?", (tenant_id,)
            ).fetchone()
            return row["name"] if row else None

    def list_tenants(self) -> list[tuple[int, str]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT id, name FROM tenants ORDER BY id"
            ).fetchall()
            return [(int(r["id"]), r["name"]) for r in rows]
