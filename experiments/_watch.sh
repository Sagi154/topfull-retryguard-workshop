#!/bin/bash
for i in $(seq 1 40); do
  envoy=$(pgrep -c -f envoy_retry_collector.py || true)
  metric=$(pgrep -c -f metric_collector.py || true)
  echo "TICK $(date -u) envoy=$envoy metric=$metric"
  sleep 20
done
