

The issue is that we have not been able to keep several independent services overloaded at the same time.

Right now the two services we can load are checkoutservice and recommendationservice.

- **recommendationservice** is fed by the browse calls (`getproduct`, `getcart`) and by the confirmation page after checkout.
- **checkoutservice** is fed only by `postcheckout`. PlaceOrder then continues through paymentservice and emailservice (shipping, cart, catalog, and currency sit on that same call).

We have overloaded checkoutservice and recommendationservice together on the same hold. On those holds the rest of the checkout chain (payment, email) stayed cool, so we have not gotten the chain hot at the same time as both of them. Catalog, cart, currency, shipping, and ads stay cool as well.

We have been varying user-count splits and CPU tables, and that is still as wide as it gets.

One cause we think you may have run into: Locust is closed-loop (`constant_throughput(1)`), one swarm per API. Once the storefront is saturated, more users do not raise throughput - it caps near 600 req/s - so extra users wait instead of pushing more backends over the edge.

Did you get several microservices overloaded at once? If so, which user-count split and which CPU table (millicores and replica counts) were actually live when that happened?