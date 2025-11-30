#!/bin/bash
###############################################################################
# Run Full Experiment - Scenario 09: DSCP QoS with Ring Topology
#
# Topology: 1 Core + 3 Aggregation (Ring) + 9 Edge = 13 switches
# Ring: s2 ↔ s3 ↔ s4 ↔ s2 (redundancy at aggregation layer)
#
# Usage: ./run_experiment.sh [duration]
#        ./run_experiment.sh 120  (2 minutes)
###############################################################################

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
RYU_ENV="/home/aldi/ryu39"

# Parse duration
DURATION=${1:-120}

echo "=============================================================="
echo "  SCENARIO 09: DSCP-Based QoS with Ring Topology"
echo "=============================================================="
echo ""
echo "Topology: 1 Core + 3 Aggregation (Ring) + 9 Edge"
echo "  - 13 switches total"
echo "  - 15 links (3 core-agg + 3 ring + 9 agg-edge)"
echo "  - Ring: s2 ↔ s3 ↔ s4 ↔ s2"
echo "Duration: $DURATION seconds"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "[CLEANUP] Stopping all components..."

    if [ ! -z "$RYU_PID" ]; then
        kill $RYU_PID 2>/dev/null || true
        echo "  ✓ Ryu controller stopped"
    fi

    sudo pkill -f mosquitto 2>/dev/null || true
    sudo pkill -f publisher 2>/dev/null || true
    sudo pkill -f subscriber 2>/dev/null || true
    sudo mn -c > /dev/null 2>&1 || true

    echo "  ✓ Cleanup complete"
    echo ""
}

trap cleanup EXIT

# Initial cleanup - remove any leftover from previous runs
echo "[INIT] Cleaning up previous runs..."
sudo pkill -f ryu-manager 2>/dev/null || true
sudo pkill -f mosquitto 2>/dev/null || true
sudo pkill -f publisher 2>/dev/null || true
sudo pkill -f subscriber 2>/dev/null || true
sudo mn -c > /dev/null 2>&1 || true
sleep 2
echo "  ✓ Initial cleanup complete"
echo ""

# Create results directory first (so we can save controller log there)
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_RESULTS_DIR="$PROJECT_ROOT/results/09-dscp-qos-13switches-ring/run_$TIMESTAMP"
mkdir -p "$RUN_RESULTS_DIR/logs"

echo "Results will be saved to: $RUN_RESULTS_DIR"
echo ""

# Step 1: Start Ryu Controller
echo "[1/2] Starting Ryu Controller..."
source "$RYU_ENV/bin/activate"

"$RYU_ENV/bin/python3.9" -u "$RYU_ENV/bin/ryu-manager" \
    "$SCENARIO_DIR/controller_dscp.py" \
    ryu.app.ofctl_rest \
    > "$RUN_RESULTS_DIR/logs/ryu_controller.log" 2>&1 &

RYU_PID=$!
echo "  ✓ Controller started (PID: $RYU_PID)"
echo "  ✓ Controller log: $RUN_RESULTS_DIR/logs/ryu_controller.log"

sleep 3

if ! ps -p $RYU_PID > /dev/null; then
    echo "[ERROR] Controller failed to start!"
    echo "Check: $RUN_RESULTS_DIR/logs/ryu_controller.log"
    exit 1
fi

# Step 2: Run Topology
echo ""
echo "[2/2] Starting Network Topology..."
echo ""

cd "$RUN_RESULTS_DIR"

# Write experiment header to log
{
    echo "=============================================================="
    echo "  SCENARIO 09: DSCP-Based QoS with Ring Topology"
    echo "=============================================================="
    echo ""
    echo "Topology: 1 Core + 3 Aggregation (Ring) + 9 Edge"
    echo "  - 13 switches total"
    echo "  - 15 links (3 core-agg + 3 ring + 9 agg-edge)"
    echo "  - Ring: s2 ↔ s3 ↔ s4 ↔ s2"
    echo "Duration: $DURATION seconds (send) + $DURATION seconds (drain)"
    echo "Total Time: $((DURATION * 2)) seconds"
    echo "Start Time: $(date)"
    echo ""
} > "$RUN_RESULTS_DIR/logs/experiment.log"

# Run topology and append all output to experiment.log (while also displaying)
sudo python3 "$SCENARIO_DIR/topology_config.py" --duration "$DURATION" 2>&1 | tee -a "$RUN_RESULTS_DIR/logs/experiment.log"

echo ""
echo "=============================================================="
echo "  EXPERIMENT COMPLETE!"
echo "=============================================================="
echo ""

if [ -d "$RUN_RESULTS_DIR" ]; then
    echo "Results saved to: $RUN_RESULTS_DIR"
    echo ""

    if [ -f "$RUN_RESULTS_DIR/metrics_summary.txt" ]; then
        echo "=== METRICS SUMMARY ==="
        cat "$RUN_RESULTS_DIR/metrics_summary.txt"
        echo ""
    fi

    if [ -f "$RUN_RESULTS_DIR/mqtt_metrics_log.csv" ]; then
        echo "CSV data: mqtt_metrics_log.csv"
        echo "Total messages: $(wc -l < "$RUN_RESULTS_DIR/mqtt_metrics_log.csv")"
    fi
fi

echo ""
echo "All logs saved to: $RUN_RESULTS_DIR/logs/"
echo "  - experiment.log     : Topology build, STP, QoS, MQTT logs"
echo "  - ryu_controller.log : SDN controller logs"
echo "  - publisher_*.log    : Per-publisher logs"
echo "  - subscriber.log     : Subscriber logs"
echo ""
