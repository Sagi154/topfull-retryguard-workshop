# Locust APIs and the Online Boutique services they traverse

TopFull + RetryGuard Workshop — TAU Deepness Lab

Each of the five Locust names is one HTTP call to the **frontend**, not a call to a backend service. TopFull treats that call as an **entry API** whose **execution path** is the set of Online Boutique services the request then touches.

Sources:

- Paper: [context/TopFull.pdf](../context/TopFull.pdf). API 1–5 are `postcheckout`, `getproduct`, `getcart`, `postcart`, `emptycart`, distinguished by URL. Figure 2 is the Boutique topology. Figure 3 draws the Get Product and Post Checkout paths sharing recommendations.
- Path sets: `TopFull_master/online_boutique_scripts/src/config/online_boutique.json` in [kaist-ina/TopFull](https://github.com/kaist-ina/TopFull). The JSON list is the set of services on the path, not the call order.
- HTTP tasks: `TopFull_loadgen/locust_online_boutique.py` in the same repo. `WebsiteUser.wait_time = constant_throughput(1)` (about one request per second per user). `goodput_threshold` is **1 second** for all five.
- Call order: Online Boutique v0.8.0 handlers (`src/frontend/handlers.go`, `src/checkoutservice/main.go`, `src/recommendationservice/recommendation_server.py`) — the app TopFull deploys.

The load generator starts each tag on its own (`--tags <name>`). A Locust user issues only that tag. These are separate paths that overlap on shared services, not one shopper walking browse → cart → checkout.

Empirical edge counts from S1 try runs 28–35 (which tag moves which Envoy edge): [2026-09-22-locust-api-to-boutique-service-mapping.md](../docs/superpowers/specs/2026-09-22-locust-api-to-boutique-service-mapping.md).

## getproduct — product page

`GET /product/0PUK6V6EV0` (always that one SKU), with a random `priority` header from 0–99.

The frontend product page calls, in order:

1. `productcatalogservice` — `GetProduct`
2. `currencyservice` — list currencies and convert the price
3. `cartservice` — `GetCart`, only to show the cart badge
4. `recommendationservice` — `ListRecommendations`, which itself calls `productcatalogservice.ListProducts`
5. `adservice` — `GetAds` for that product’s categories

Path: **frontend → currency, cart, catalog, recommendations (→ catalog), ads.** This is the only API that hits ads. Checkout, payment, and email stay off this path.

## getcart — cart page

`GET /cart`.

The cart page calls:

1. `currencyservice` — list currencies
2. `cartservice` — `GetCart`
3. `recommendationservice` — recommendations for the items in the cart, which again calls `productcatalogservice.ListProducts`
4. `shippingservice` — `GetQuote`
5. For **each item** in the cart: `productcatalogservice.GetProduct` and `currencyservice.Convert`

Path: **frontend → currency, cart, recommendations (→ catalog), shipping, catalog.** Viewing the cart is the wide fan-out. Shipping here is a quote for the page, not a shipment.

## postcart — add to cart

`POST /cart` with a random product id and a quantity in {1, 2, 3, 4, 5, 10}.

The handler calls `productcatalogservice.GetProduct`, then `cartservice.AddItem`, then returns HTTP 302 to `/cart`. TopFull’s recorded path stops at those two backends: **frontend → catalog, cart.** The cart-page fan-out (shipping quote, recommendations, per-item prices) is the separate `getcart` API.

## emptycart — empty the cart

`POST /cart/empty`.

The handler calls `cartservice.EmptyCart` and redirects to `/`. Path: **frontend → cart.** Catalog, currency, shipping, and checkout stay off this path.

`cartservice` stores the cart in **redis-cart**. Figure 2 of the paper draws that cache. TopFull’s API path lists leave Redis out; they stop at `cartservice`.

## postcheckout — place an order

`POST /cart/checkout` with a fixed address and card body.

The frontend calls `checkoutservice.PlaceOrder`. Checkout then runs this chain:

1. `cartservice.GetCart`
2. For each item: `productcatalogservice.GetProduct` and `currencyservice.Convert`
3. `shippingservice.GetQuote`, then `currencyservice.Convert` on the shipping cost
4. `paymentservice.Charge`
5. `shippingservice.ShipOrder`
6. `cartservice.EmptyCart`
7. `emailservice.SendOrderConfirmation`

After that returns, the frontend renders the confirmation page: `recommendationservice` (which calls catalog) and `currencyservice` again.

Path: **frontend → checkout → cart, catalog, currency, shipping, payment, email**, plus **recommendations** on the confirmation page. This is the only API that reaches checkout, payment, and email.

This tag never adds items itself, so that user’s cart is empty and the per-item catalog loop inside checkout usually does no work. Quote, charge, ship, email, and the confirmation-page recommendation still run.

## How the paths overlap

```text
getproduct:   frontend → catalog, currency, cart, recommendations → catalog, ads
getcart:      frontend → cart, currency, recommendations → catalog, shipping (quote), catalog (per item)
postcart:     frontend → catalog, cart
emptycart:    frontend → cart
postcheckout: frontend → checkout → cart, catalog, currency, shipping, payment, email
                              └→ recommendations → catalog
```

`paymentservice`, `emailservice`, `shippingservice`, `currencyservice`, and `adservice` are leaves: nothing calls onward from them. `recommendationservice` calls `productcatalogservice`. Checkout is the other fan-out point.

Figure 3 uses two of these paths on purpose. Get Product and Post Checkout both go through **recommendations**. If Recommend and Checkout are overloaded at the same time, shedding inside each service can waste work on Get Product requests that still fail later. TopFull rate-limits these five URLs at the entry, using the execution path, instead of shedding inside each service.
