/*!
 * CreateCart browser client SDK
 * Two clearly divided surfaces:
 *   • CreateCart.Store  — customer: view menu + manage their own cart
 *   • CreateCart.Admin  — business: add/edit/delete menu items, price, stock
 * Framework-agnostic, dependency-free. Works from any <script> tag.
 */
(function (global) {
  "use strict";

  class HttpError extends Error {
    constructor(status, detail) {
      super(detail || "HTTP " + status);
      this.name = "HttpError";
      this.status = status;
      this.detail = detail;
    }
  }

  async function request(baseUrl, path, opts) {
    opts = opts || {};
    const res = await fetch(baseUrl.replace(/\/$/, "") + path, {
      method: opts.method || "GET",
      headers: Object.assign({ "Content-Type": "application/json" }, opts.headers || {}),
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(function () { return null; });
    if (!res.ok) throw new HttpError(res.status, data && data.detail);
    return data;
  }

  function qs(params) {
    const s = new URLSearchParams();
    Object.keys(params || {}).forEach(function (k) {
      if (params[k] !== undefined && params[k] !== null && params[k] !== "")
        s.set(k, params[k]);
    });
    const str = s.toString();
    return str ? "?" + str : "";
  }

  /* ── Customer surface: view all + cart ─────────────────────────────── */
  class Store {
    constructor(cfg) {
      cfg = cfg || {};
      this.baseUrl = cfg.baseUrl;
      this.tenant = cfg.tenant;
      this.cartId = cfg.cartId || Store.ensureCartId(this.tenant);
    }

    /** Stable per-browser cart id, persisted in localStorage. */
    static ensureCartId(tenant) {
      const key = "cc_cart_" + tenant;
      let id = null;
      try { id = localStorage.getItem(key); } catch (e) {}
      if (!id) {
        id = "c-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
        try { localStorage.setItem(key, id); } catch (e) {}
      }
      return id;
    }

    _m(p) { return "/api/" + this.tenant + p; }
    _c(p) { return "/api/" + this.tenant + "/carts/" + this.cartId + p; }

    // menu (read-only)
    getMenu() { return request(this.baseUrl, this._m("/menu")); }
    listItems(params) { return request(this.baseUrl, this._m("/items" + qs(params))); }
    getItem(id) { return request(this.baseUrl, this._m("/items/" + id)); }
    listCombos() { return request(this.baseUrl, this._m("/combos")); }

    // cart
    getCart() { return request(this.baseUrl, this._c("")); }
    addToCart(itemId, quantity) {
      return request(this.baseUrl, this._c("/items"),
        { method: "POST", body: { item_id: itemId, quantity: quantity || 1 } });
    }
    increment(itemId, by) {
      return request(this.baseUrl, this._c("/items/" + itemId + "/increment"),
        { method: "POST", body: { by: by || 1 } });
    }
    decrement(itemId, by) {
      return request(this.baseUrl, this._c("/items/" + itemId + "/decrement"),
        { method: "POST", body: { by: by || 1 } });
    }
    setQuantity(itemId, quantity) {
      return request(this.baseUrl, this._c("/items/" + itemId),
        { method: "PUT", body: { quantity: quantity } });
    }
    removeItem(itemId) {
      return request(this.baseUrl, this._c("/items/" + itemId), { method: "DELETE" });
    }
    clearCart() {
      return request(this.baseUrl, this._c("/clear"), { method: "POST" });
    }

    // checkout: create a payment order priced server-side from this cart
    checkout() {
      return request(this.baseUrl, this._c("/checkout"), { method: "POST" });
    }
    // verify a completed payment (clears the cart + creates a delivery order)
    verifyPayment(payload) {
      return request(this.baseUrl, this._m("/payments/verify"),
        { method: "POST", body: payload });
    }
    // track a delivery order by id (status + timeline)
    getDelivery(orderId) {
      return request(this.baseUrl, this._m("/deliveries/" + orderId));
    }

    // ── customer auth (Sign in with Google) ──────────────────────────
    getAuthConfig() {                          // { provider, client_id? }
      return request(this.baseUrl, "/api/auth/config");
    }
    googleLogin(idToken) {                      // verify token -> user identity
      return request(this.baseUrl, "/api/auth/google",
        { method: "POST", body: { id_token: idToken } });
    }
    myOrders(idToken) {                         // signed-in user's past orders
      return request(this.baseUrl, this._m("/my-orders"),
        { headers: { "X-Auth-Token": idToken } });
    }

    /**
     * One-call checkout that handles both providers:
     *  • mock     -> immediately verifies the server-issued pair (local demo)
     *  • razorpay -> loads checkout.js, opens the widget, verifies on success
     * Pass opts.customer ({name, phone, address}) to attach it to the delivery
     * order created on success.
     * Returns the verify result ({status:'paid', delivery_order_id, ...}) or
     * null on cancel.
     */
    async pay(opts) {
      opts = opts || {};
      const order = await this.checkout();
      if (order.provider === "mock") {
        const mp = order.mock_payment;
        return this.verifyPayment({
          order_id: order.order_id,
          payment_id: mp.payment_id,
          signature: mp.signature,
          customer: opts.customer,
          id_token: opts.idToken,
        });
      }
      // razorpay
      await Store._loadRazorpay();
      const self = this;
      return new Promise(function (resolve, reject) {
        const rzp = new window.Razorpay({
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          name: order.name,
          order_id: order.order_id,
          prefill: opts.prefill || {},
          theme: opts.theme || {},   // tenant passes its own brand color
          handler: function (res) {
            self.verifyPayment({
              order_id: res.razorpay_order_id,
              payment_id: res.razorpay_payment_id,
              signature: res.razorpay_signature,
              customer: opts.customer,
              id_token: opts.idToken,
            }).then(resolve).catch(reject);
          },
          modal: { ondismiss: function () { resolve(null); } },
        });
        rzp.open();
      });
    }

    static _loadRazorpay() {
      if (window.Razorpay) return Promise.resolve();
      return new Promise(function (resolve, reject) {
        const s = document.createElement("script");
        s.src = "https://checkout.razorpay.com/v1/checkout.js";
        s.onload = resolve;
        s.onerror = function () { reject(new Error("failed to load Razorpay")); };
        document.head.appendChild(s);
      });
    }
  }

  /* ── Business surface: requires admin key ──────────────────────────── */
  class Admin {
    constructor(cfg) {
      cfg = cfg || {};
      this.baseUrl = cfg.baseUrl;
      this.tenant = cfg.tenant;
      // the tenant's own password, sent as X-Tenant-Key (adminKey accepted as alias)
      this.password = cfg.password || cfg.adminKey;
    }
    _h() { return { "X-Tenant-Key": this.password }; }
    _m(p) { return "/api/" + this.tenant + p; }

    // read-throughs (so an admin UI can use one client)
    listItems(params) { return request(this.baseUrl, this._m("/items" + qs(params))); }
    getMenu() { return request(this.baseUrl, this._m("/menu")); }

    // validate tenant + password at login (throws 401 if wrong); returns identity
    me() {
      return request(this.baseUrl, this._m("/admin/me"), { headers: this._h() });
    }

    // menu mutations
    addItem(item) {
      return request(this.baseUrl, this._m("/items"),
        { method: "POST", body: item, headers: this._h() });
    }
    updateItem(id, fields) {
      return request(this.baseUrl, this._m("/items/" + id),
        { method: "PATCH", body: fields, headers: this._h() });
    }
    deleteItem(id) {
      return request(this.baseUrl, this._m("/items/" + id),
        { method: "DELETE", headers: this._h() });
    }
    setPrice(id, price) {
      return request(this.baseUrl, this._m("/items/" + id + "/price"),
        { method: "POST", body: { price: price }, headers: this._h() });
    }
    setAvailability(id, available) {
      return request(this.baseUrl, this._m("/items/" + id + "/availability"),
        { method: "POST", body: { available: available }, headers: this._h() });
    }
    setStock(id, stock) {
      return request(this.baseUrl, this._m("/items/" + id + "/stock/set"),
        { method: "POST", body: { stock: stock }, headers: this._h() });
    }
    addCategory(category) {
      return request(this.baseUrl, this._m("/categories"),
        { method: "POST", body: category, headers: this._h() });
    }
    addCombo(combo) {
      return request(this.baseUrl, this._m("/combos"),
        { method: "POST", body: combo, headers: this._h() });
    }

    // ── orders (deliveries) ──────────────────────────────────────────
    listOrders(status) {
      return request(this.baseUrl, this._m("/deliveries" + qs({ status: status })),
        { headers: this._h() });
    }
    getOrder(orderId) {                       // status + timeline (public track)
      return request(this.baseUrl, this._m("/deliveries/" + orderId));
    }
    advanceOrder(orderId, note) {
      return request(this.baseUrl, this._m("/deliveries/" + orderId + "/advance"),
        { method: "POST", body: { note: note }, headers: this._h() });
    }
    setOrderStatus(orderId, status, note) {
      return request(this.baseUrl, this._m("/deliveries/" + orderId + "/status"),
        { method: "POST", body: { status: status, note: note }, headers: this._h() });
    }
    cancelOrder(orderId, reason) {
      return request(this.baseUrl, this._m("/deliveries/" + orderId + "/cancel"),
        { method: "POST", body: { reason: reason }, headers: this._h() });
    }
    assignCourier(orderId, courier) {         // { name, phone?, tracking_url? }
      return request(this.baseUrl, this._m("/deliveries/" + orderId + "/courier"),
        { method: "POST", body: courier, headers: this._h() });
    }
  }

  /* ── Platform surface: CreateCart owner — onboards tenants ─────────── */
  class Platform {
    constructor(cfg) {
      cfg = cfg || {};
      this.baseUrl = cfg.baseUrl;
      this.adminKey = cfg.adminKey;          // the global platform key
    }
    _h() { return { "X-Admin-Key": this.adminKey }; }

    listTenants() {
      return request(this.baseUrl, "/api/_tenants", { headers: this._h() });
    }
    getTenant(name) {
      return request(this.baseUrl, "/api/_tenants/" + name, { headers: this._h() });
    }
    // onboard: { name, password, base_url, id? }
    createTenant(tenant) {
      return request(this.baseUrl, "/api/_tenants",
        { method: "POST", body: tenant, headers: this._h() });
    }
  }

  global.CreateCart = {
    Store: Store, Admin: Admin, Platform: Platform, HttpError: HttpError,
  };
})(typeof window !== "undefined" ? window : this);
