#!/bin/bash
for i in $(seq 1 300); do
  curl -s -o /dev/null http://localhost:30440/
  curl -s -o /dev/null http://localhost:30440/product/OLJCESPC7Z
  curl -s -o /dev/null http://localhost:30440/product/66VCHSJNUP
  curl -s -o /dev/null -X POST -d "product_id=OLJCESPC7Z&quantity=1" http://localhost:30440/cart
  curl -s -o /dev/null http://localhost:30440/cart
  sleep 0.3
done
echo TRAFFIC_DONE
