# RetailCo Architecture — scn-03-stale-dns-reference

DNS record for mysql-prod was marked decommissioned, but application config still references it.

## Services
- **frontend** (service)
- **load-balancer** (service)
- **checkout-api** (service)
- **order-service** (service)
- **payment-service** (service)
- **mysql-prod** (database)
- **redis** (database)
- **kafka** (service)
- **monitoring** (service)
- **external-payment-api** (external_api)

## Notes