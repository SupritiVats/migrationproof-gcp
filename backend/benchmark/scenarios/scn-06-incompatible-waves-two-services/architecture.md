# RetailCo Architecture — scn-06-incompatible-waves-two-services

order-service (Wave 1) depends on checkout-api, but checkout-api is pushed to Wave 2.

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