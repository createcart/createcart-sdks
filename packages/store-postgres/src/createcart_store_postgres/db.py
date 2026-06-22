"""Postgres database handle + tenant registry (tenant_id 0..n ↔ english name).

Mirrors ``createcart-store-sqlite`` exactly, but on Postgres (e.g. Supabase).
Owns the shared ``tenants`` table and creates the per-tenant data tables
(``menu_items_<id>``, ``categories_<id>``, ``combos_<id>``, ``carts_<id>``,
``payments_<id>``, ``deliveries_<id>``) on demand.

A new connection is opened per operation, which suits serverless runtimes
(Vercel functions) behind Supabase's transaction pooler. Pass the pooler URI as
the DSN there; a direct connection string works for persistent hosts.
"""

from __future__ import annotations

import re
from typing import Optional

import psycopg
from psycopg.rows import dict_row

# English-word / slug tenant names only — also keeps generated table names safe.
_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def _per_tenant_ddl(tid: int) -> list[str]:
    return [
        f"""CREATE TABLE IF NOT EXISTS menu_items_{tid} (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, name_localized TEXT,
            description TEXT, price TEXT, currency TEXT, image_url TEXT, icon TEXT,
            category TEXT, tags TEXT, available BOOLEAN, stock INTEGER,
            sort_order INTEGER, metadata TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS categories_{tid} (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, sort_order INTEGER, metadata TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS combos_{tid} (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, price TEXT, currency TEXT,
            description TEXT, item_ids TEXT, tags TEXT, available BOOLEAN,
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


class PgDatabase:
    """Postgres database + tenant registry. ``dsn`` is a libpq connection string."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS tenants ("
                "  id INTEGER PRIMARY KEY,"      # 0..n, assigned explicitly
                "  name TEXT NOT NULL UNIQUE,"
                "  password_hash TEXT,"          # opaque hash (API hashes/verifies)
                "  base_url TEXT)"               # the tenant's API base URL
            )
            # Idempotent migration for older DBs that predate the auth columns.
            conn.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS password_hash TEXT")
            conn.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS base_url TEXT")

    def connect(self) -> psycopg.Connection:
        """Open a connection. Used as a context manager: commits on success,
        rolls back on error, and closes on exit (mirrors the SQLite backend).

        ``prepare_threshold=None`` disables server-side prepared statements, which
        the Supabase **transaction pooler** (pgbouncer, transaction mode) does not
        support — required for serverless/Vercel. Harmless on a direct connection.
        """
        return psycopg.connect(
            self.dsn, row_factory=dict_row, prepare_threshold=None
        )

    # ── tenant registry ──────────────────────────────────────────────────
    def get_or_create_tenant(self, name: str, *, tenant_id: Optional[int] = None) -> int:
        """Return the tenant_id for ``name``, creating it (and its per-tenant
        tables) if new. IDs are assigned sequentially from 0, or you may pass an
        explicit ``tenant_id`` when onboarding."""
        if not _NAME_RE.match(name):
            raise ValueError(
                f"invalid tenant name {name!r}: use a lowercase english "
                "word/slug like 'brahmana-naivedyam'"
            )
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM tenants WHERE name=%s", (name,)
            ).fetchone()
            if row is not None:
                tid = int(row["id"])
            elif tenant_id is not None:
                taken = conn.execute(
                    "SELECT 1 FROM tenants WHERE id=%s", (tenant_id,)
                ).fetchone()
                if taken:
                    raise ValueError(f"tenant id {tenant_id} is already in use")
                tid = int(tenant_id)
                conn.execute("INSERT INTO tenants(id, name) VALUES(%s, %s)", (tid, name))
            else:
                m = conn.execute("SELECT MAX(id) AS m FROM tenants").fetchone()["m"]
                tid = 0 if m is None else int(m) + 1
                conn.execute("INSERT INTO tenants(id, name) VALUES(%s, %s)", (tid, name))
            for ddl in _per_tenant_ddl(tid):
                conn.execute(ddl)
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
            sets.append("password_hash=%s")
            vals.append(password_hash)
        if base_url is not None:
            sets.append("base_url=%s")
            vals.append(base_url)
        if not sets:
            return
        vals.append(name)
        with self.connect() as conn:
            conn.execute(f"UPDATE tenants SET {', '.join(sets)} WHERE name=%s", vals)

    def get_tenant(self, name: str) -> Optional[dict]:
        """Full tenant record (id, name, password_hash, base_url) or None."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, name, password_hash, base_url FROM tenants WHERE name=%s",
                (name,),
            ).fetchone()
            return dict(row) if row else None

    def list_tenants_full(self) -> list[dict]:
        """All tenants as dicts with id, name, base_url (no password)."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, name, base_url FROM tenants ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def tenant_id(self, name: str) -> Optional[int]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM tenants WHERE name=%s", (name,)
            ).fetchone()
            return int(row["id"]) if row else None

    def tenant_name(self, tenant_id: int) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT name FROM tenants WHERE id=%s", (tenant_id,)
            ).fetchone()
            return row["name"] if row else None

    def list_tenants(self) -> list[tuple[int, str]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, name FROM tenants ORDER BY id"
            ).fetchall()
            return [(int(r["id"]), r["name"]) for r in rows]
