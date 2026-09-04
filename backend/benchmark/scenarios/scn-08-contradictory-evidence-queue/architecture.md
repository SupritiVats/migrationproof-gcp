# RetailCo Architecture — scn-08-contradictory-evidence-queue

order-service->kafka: config says active, architecture doc says kafka was decommissioned.

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
- order-service->kafka: kafka message broker was decommissioned and replaced by pubsub