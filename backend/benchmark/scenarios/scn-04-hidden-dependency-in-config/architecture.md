# RetailCo Architecture — scn-04-hidden-dependency-in-config

A dependency (order-service -> kafka) is only visible in one weak artifact (service catalog note).

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