"""The MenuRegistry — every menu-related operation lives here.

The registry keeps the catalog in memory and persists the whole thing through
its :class:`~createcart_registry.storage.base.MenuStore` after each mutation.
It is the single entry point an app or API layer talks to.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Optional

from .exceptions import (
    DuplicateItemError,
    ItemNotFoundError,
    OutOfStockError,
)
from .models import Category, Combo, MenuCatalog, MenuItem, slugify
from .storage.base import MenuStore
from .storage.memory import InMemoryStore


class MenuRegistry:
    """All menu operations: items, categories, combos, pricing, availability
    and stock."""

    def __init__(
        self,
        store: Optional[MenuStore] = None,
        *,
        tenant: Optional[str] = None,
        currency: str = "INR",
    ) -> None:
        self._store: MenuStore = store or InMemoryStore()
        self._catalog: MenuCatalog = self._store.load()
        if tenant is not None:
            self._catalog.tenant = tenant
        if not self._catalog.currency:
            self._catalog.currency = currency

    # ── persistence ──────────────────────────────────────────────────────
    def _persist(self) -> None:
        self._store.save(self._catalog)

    def reload(self) -> None:
        """Drop in-memory state and re-read from the backing store."""
        self._catalog = self._store.load()

    @property
    def catalog(self) -> MenuCatalog:
        """The current catalog (live object — treat as read-only)."""
        return self._catalog

    def _unique_id(self, base: str, existing: Iterable[str]) -> str:
        existing = set(existing)
        slug = slugify(base) or "item"
        if slug not in existing:
            return slug
        i = 2
        while f"{slug}-{i}" in existing:
            i += 1
        return f"{slug}-{i}"

    # ── items: create / read / update / delete ───────────────────────────
    def add_item(
        self,
        name: str,
        *,
        id: Optional[str] = None,
        price: Decimal | float | int | str = 0,
        name_localized: Optional[str] = None,
        description: str = "",
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        icon: Optional[str] = None,
        image_url: Optional[str] = None,
        available: bool = True,
        stock: Optional[int] = None,
        sort_order: int = 0,
        currency: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MenuItem:
        """Create and persist a new menu item. ``id`` defaults to a slug of the
        name and is made unique automatically."""
        item_id = id or self._unique_id(name, (i.id for i in self._catalog.items))
        if any(i.id == item_id for i in self._catalog.items):
            raise DuplicateItemError(f"item id already exists: {item_id!r}")
        item = MenuItem(
            id=item_id,
            name=name,
            name_localized=name_localized,
            description=description,
            price=price,
            currency=currency or self._catalog.currency,
            category=category,
            tags=tags or [],
            icon=icon,
            image_url=image_url,
            available=available,
            stock=stock,
            sort_order=sort_order,
            metadata=metadata or {},
        )
        self._catalog.items.append(item)
        self._persist()
        return item

    def get_item(self, item_id: str) -> MenuItem:
        for item in self._catalog.items:
            if item.id == item_id:
                return item
        raise ItemNotFoundError(f"no item with id {item_id!r}")

    def find_item(self, item_id: str) -> Optional[MenuItem]:
        """Like :meth:`get_item` but returns ``None`` instead of raising."""
        try:
            return self.get_item(item_id)
        except ItemNotFoundError:
            return None

    def update_item(self, item_id: str, **fields: Any) -> MenuItem:
        """Patch arbitrary fields on an item (validated by the model)."""
        item = self.get_item(item_id)
        unknown = set(fields) - set(MenuItem.model_fields)
        if unknown:
            raise ValueError(f"unknown item fields: {sorted(unknown)}")
        # Merge onto a plain dict, then re-validate so coercion (e.g. price ->
        # Decimal) and constraints apply cleanly.
        data = item.model_dump()
        data.update(fields)
        updated = MenuItem.model_validate(data)
        idx = self._catalog.items.index(item)
        self._catalog.items[idx] = updated
        self._persist()
        return updated

    def remove_item(self, item_id: str) -> None:
        item = self.get_item(item_id)
        self._catalog.items.remove(item)
        # Drop references from combos so we never dangle.
        for combo in self._catalog.combos:
            if item_id in combo.item_ids:
                combo.item_ids.remove(item_id)
        self._persist()

    # ── items: listing / search ──────────────────────────────────────────
    def list_items(
        self,
        *,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        available_only: bool = False,
        in_stock_only: bool = False,
    ) -> list[MenuItem]:
        """Return items filtered and sorted by ``sort_order`` then ``name``."""
        items = self._catalog.items
        if category is not None:
            items = [i for i in items if i.category == category]
        if tag is not None:
            items = [i for i in items if tag in i.tags]
        if available_only:
            items = [i for i in items if i.available]
        if in_stock_only:
            items = [i for i in items if i.in_stock]
        return sorted(items, key=lambda i: (i.sort_order, i.name.lower()))

    def search(self, query: str) -> list[MenuItem]:
        """Case-insensitive search across name, localized name, description and
        tags."""
        q = query.strip().lower()
        if not q:
            return []
        hits = []
        for item in self._catalog.items:
            haystack = " ".join(
                filter(
                    None,
                    [
                        item.name,
                        item.name_localized or "",
                        item.description,
                        " ".join(item.tags),
                    ],
                )
            ).lower()
            if q in haystack:
                hits.append(item)
        return sorted(hits, key=lambda i: (i.sort_order, i.name.lower()))

    def count(self, *, available_only: bool = False) -> int:
        if available_only:
            return sum(1 for i in self._catalog.items if i.available)
        return len(self._catalog.items)

    # ── pricing ──────────────────────────────────────────────────────────
    def set_price(self, item_id: str, price: Decimal | float | int | str) -> MenuItem:
        return self.update_item(item_id, price=price)

    # ── availability & stock ─────────────────────────────────────────────
    def set_available(self, item_id: str, available: bool) -> MenuItem:
        return self.update_item(item_id, available=available)

    def is_available(self, item_id: str) -> bool:
        return self.get_item(item_id).in_stock

    def set_stock(self, item_id: str, stock: Optional[int]) -> MenuItem:
        """Set absolute stock. ``None`` means untracked / unlimited."""
        if stock is not None and stock < 0:
            raise OutOfStockError("stock cannot be negative")
        return self.update_item(item_id, stock=stock)

    def adjust_stock(self, item_id: str, delta: int) -> MenuItem:
        """Add ``delta`` (negative to consume). Raises if it would go below 0.
        No-op on untracked (``stock is None``) items."""
        item = self.get_item(item_id)
        if item.stock is None:
            return item
        new_stock = item.stock + delta
        if new_stock < 0:
            raise OutOfStockError(
                f"{item_id!r}: only {item.stock} in stock, cannot apply {delta}"
            )
        return self.update_item(item_id, stock=new_stock)

    # ── categories ───────────────────────────────────────────────────────
    def add_category(
        self,
        name: str,
        *,
        id: Optional[str] = None,
        sort_order: int = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Category:
        cat_id = id or self._unique_id(name, (c.id for c in self._catalog.categories))
        if any(c.id == cat_id for c in self._catalog.categories):
            raise DuplicateItemError(f"category id already exists: {cat_id!r}")
        category = Category(
            id=cat_id, name=name, sort_order=sort_order, metadata=metadata or {}
        )
        self._catalog.categories.append(category)
        self._persist()
        return category

    def list_categories(self) -> list[Category]:
        return sorted(
            self._catalog.categories, key=lambda c: (c.sort_order, c.name.lower())
        )

    def remove_category(self, category_id: str, *, unassign_items: bool = True) -> None:
        for category in self._catalog.categories:
            if category.id == category_id:
                self._catalog.categories.remove(category)
                break
        else:
            raise ItemNotFoundError(f"no category with id {category_id!r}")
        if unassign_items:
            for item in self._catalog.items:
                if item.category == category_id:
                    item.category = None
        self._persist()

    def items_by_category(self) -> dict[Optional[str], list[MenuItem]]:
        """Group every item by its category id (``None`` key = uncategorized)."""
        grouped: dict[Optional[str], list[MenuItem]] = {}
        for item in self.list_items():
            grouped.setdefault(item.category, []).append(item)
        return grouped

    # ── combos ───────────────────────────────────────────────────────────
    def add_combo(
        self,
        name: str,
        *,
        price: Decimal | float | int | str = 0,
        id: Optional[str] = None,
        description: str = "",
        item_ids: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        available: bool = True,
        sort_order: int = 0,
        currency: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Combo:
        combo_id = id or self._unique_id(name, (c.id for c in self._catalog.combos))
        if any(c.id == combo_id for c in self._catalog.combos):
            raise DuplicateItemError(f"combo id already exists: {combo_id!r}")
        for ref in item_ids or []:
            if not any(i.id == ref for i in self._catalog.items):
                raise ItemNotFoundError(f"combo references unknown item {ref!r}")
        combo = Combo(
            id=combo_id,
            name=name,
            price=price,
            currency=currency or self._catalog.currency,
            description=description,
            item_ids=item_ids or [],
            tags=tags or [],
            available=available,
            sort_order=sort_order,
            metadata=metadata or {},
        )
        self._catalog.combos.append(combo)
        self._persist()
        return combo

    def list_combos(self, *, available_only: bool = False) -> list[Combo]:
        combos = self._catalog.combos
        if available_only:
            combos = [c for c in combos if c.available]
        return sorted(combos, key=lambda c: (c.sort_order, c.name.lower()))

    def remove_combo(self, combo_id: str) -> None:
        for combo in self._catalog.combos:
            if combo.id == combo_id:
                self._catalog.combos.remove(combo)
                self._persist()
                return
        raise ItemNotFoundError(f"no combo with id {combo_id!r}")

    # ── bulk import / export ─────────────────────────────────────────────
    def import_items(self, items: Iterable[dict[str, Any]]) -> list[MenuItem]:
        """Bulk-create items from plain dicts. Persists once at the end."""
        created = []
        for raw in items:
            data = dict(raw)
            name = data.pop("name")
            created.append(self._add_item_no_persist(name=name, **data))
        self._persist()
        return created

    def _add_item_no_persist(self, name: str, **kwargs: Any) -> MenuItem:
        item_id = kwargs.pop("id", None) or self._unique_id(
            name, (i.id for i in self._catalog.items)
        )
        if any(i.id == item_id for i in self._catalog.items):
            raise DuplicateItemError(f"item id already exists: {item_id!r}")
        kwargs.setdefault("currency", self._catalog.currency)
        item = MenuItem(id=item_id, name=name, **kwargs)
        self._catalog.items.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        """The whole catalog as JSON-ready primitives (for an API response)."""
        return self._catalog.model_dump(mode="json")

    def to_json(self, *, indent: int | None = 2) -> str:
        return self._catalog.model_dump_json(indent=indent)
