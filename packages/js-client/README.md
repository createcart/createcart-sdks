# @createcart/client — Browser Client SDK

A single, dependency-free `createcart.js` that talks to the CreateCart API from any
website. It has **two divided surfaces** so the customer and the business get exactly
the powers they should — and nothing more. **No theme, no UI** — each tenant builds
its own look on top.

- **Language:** JavaScript (vanilla, UMD-style global) · **File:** `createcart.js`
- **Global:** `window.CreateCart` · **npm (later):** `@createcart/client`

---

## The two surfaces

| Surface | Who | Can do | Needs |
|---------|-----|--------|-------|
| `CreateCart.Store` | **Customer** | view all items/combos, manage *their own* cart, checkout & pay | nothing |
| `CreateCart.Admin` | **Business (a tenant)** | add / update / delete items, price, availability, stock, categories, combos | tenant **`password`** → sent as `X-Tenant-Key` |
| `CreateCart.Platform` | **CreateCart owner** | onboard tenants (id, name, password, base URL), list tenants | platform **`adminKey`** → `X-Admin-Key` |

The division is enforced **server-side**: tenant mutations require the tenant's
password (the platform key also works as superuser); onboarding requires the
platform key. `Admin.me()` validates a tenant login (401 on wrong password).

## What's inside

```
packages/js-client/
├─ createcart.js     # the library (Store + Admin + HttpError)
└─ README.md
```

## API

**`new CreateCart.Store({ baseUrl, tenant, cartId? })`**

| Group | Methods |
|-------|---------|
| Menu (read) | `getMenu()`, `listItems(params)`, `getItem(id)`, `listCombos()` |
| Cart | `getCart()`, `addToCart(itemId, qty)`, `increment(id, by)`, `decrement(id, by)`, `setQuantity(id, qty)`, `removeItem(id)`, `clearCart()` |
| Checkout | `checkout()`, `verifyPayment(payload)`, **`pay(opts)`** — one-call checkout (handles mock instantly; loads Razorpay `checkout.js` and opens the widget for real) |

`Store` auto-creates and persists a per-browser cart id in `localStorage`
(`cc_cart_<tenant>`), so a returning customer keeps their cart.

**`new CreateCart.Admin({ baseUrl, tenant, adminKey })`**

Menu: `addItem(item)`, `updateItem(id, fields)`, `deleteItem(id)`, `setPrice(id, price)`,
`setAvailability(id, bool)`, `setStock(id, n)`, `addCategory(cat)`, `addCombo(combo)`,
plus read-throughs `listItems()` / `getMenu()`, and `me()` to validate login.

Orders: `listOrders(status?)`, `getOrder(id)`, `advanceOrder(id, note?)`,
`setOrderStatus(id, status, note?)`, `cancelOrder(id, reason?)`,
`assignCourier(id, {name, phone?, tracking_url?})`.

Errors throw `CreateCart.HttpError` with `.status` and `.detail`.

## Use — customer

```html
<script src="js/createcart.js"></script>
<script>
  const store = new CreateCart.Store({
    baseUrl: "http://localhost:8000",
    tenant: "brahmana-naivedyam",
  });

  const items = await store.listItems({ available_only: true });  // render YOUR UI from this
  await store.addToCart("plain-dosa", 2);
  const cart = await store.getCart();        // cart.totals.grand_total

  // one-call checkout (auto-detects mock vs Razorpay)
  const result = await store.pay({ prefill: { contact: "98...", email: "a@b.c" },
                                   theme: { color: "#F97316" } });  // tenant's own color
  if (result && result.status === "paid") { /* show success */ }
</script>
```

## Use — business (admin panel only)

```html
<script src="js/createcart.js"></script>
<script>
  const admin = new CreateCart.Admin({
    baseUrl: "http://localhost:8000",
    tenant: "brahmana-naivedyam",
    adminKey: "createcart-admin",
  });
  await admin.addItem({ name: "Filter Coffee", price: "30", icon: "☕" });
  await admin.setPrice("filter-coffee", "35");
  await admin.setAvailability("filter-coffee", false);
</script>
```

## Theme note

This library is **theme-free**. The only place a color appears is the optional
`theme` you pass to `pay()`, which is forwarded to the Razorpay widget — so each
tenant supplies its own brand color. All page styling lives in the tenant's HTML/CSS.

## Install

- **Now:** copy `createcart.js` into the tenant site (vendoring), or `<script src>` it.
- **Later:** publish to npm and `import { Store, Admin } from "@createcart/client"`.
