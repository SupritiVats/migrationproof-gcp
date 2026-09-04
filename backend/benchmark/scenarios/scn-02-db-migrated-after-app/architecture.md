# RetailCo Architecture — scn-02-db-migrated-after-app

checkout-api (Wave 1) depends on mysql-prod, but mysql-prod is scheduled for Wave 3.

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