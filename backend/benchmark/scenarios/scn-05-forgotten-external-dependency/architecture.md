# RetailCo Architecture — scn-05-forgotten-external-dependency

payment-service depends on an external payment API outside migration scope.

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