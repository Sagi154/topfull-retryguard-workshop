#!/bin/bash
set -x
rm -rf /home/idozacharia/experiments/results/smoketest_rho_verify_20260916
mkdir -p /home/idozacharia/experiments/results/smoketest_rho_verify_20260916
cd /home/idozacharia/experiments
source /home/idozacharia/TopFull/venv/bin/activate
nohup python3 envoy_retry_collector.py --params /tmp/envoy_retry_params_smoketest.json > /tmp/collector_smoketest.out 2>&1 &
COLLECTOR_PID=$!
disown
sleep 2
nohup /tmp/traffic_loop.sh > /tmp/traffic_smoketest.out 2>&1 &
TRAFFIC_PID=$!
disown
echo "COLLECTOR_PID=$COLLECTOR_PID TRAFFIC_PID=$TRAFFIC_PID"
sleep 150
echo "---PS---"
ps aux | grep -E 'envoy_retry_collector|traffic_loop' | grep -v grep
echo "---HEADER---"
head -1 /home/idozacharia/experiments/results/smoketest_rho_verify_20260916/service_inbound.csv 2>&1
echo "---TAIL---"
tail -5 /home/idozacharia/experiments/results/smoketest_rho_verify_20260916/service_inbound.csv 2>&1
echo "---KILL---"
kill $COLLECTOR_PID 2>/dev/null
kill $TRAFFIC_PID 2>/dev/null
sleep 1
echo DONE_SMOKETEST_V4
