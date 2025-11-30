#!/bin/bash
###############################################################################
# Run Full Experiment - Scenario 10: Link Failure Test
#
# Same topology as Scenario 09 but with link failure simulation
# - Phase 1 (0-30s):  Normal operation - all links active
# - Phase 2 (30s+):   Link s2↔s1 DOWN - test redundancy via ring
#
# Usage: ./run_experiment.sh [duration]
#        ./run_experiment.sh 120  (2 minutes minimum recommended)
###############################################################################

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
RYU_ENV="/home/aldi/ryu39"

# Parse duration (minimum 60 seconds: 30s phase1 + 30s phase2)
DURATION=${1:-120}

if [ "$DURATION" -lt 60 ]; then
    echo "Error: Duration must be at least 60 seconds"
    echo "  Phase 1 (normal): 30s"
    echo "  Phase 2 (link down): at least 30s"
    exit 1
fi

echo "=============================================================="
echo "  SCENARIO 10: Link Failure Test"
echo "=============================================================="
echo ""
echo "Topology: Same as Scenario 09 (Ring)"
echo "  - 13 switches (1 core + 3 agg ring + 9 edge)"
echo "  - Link s2↔s1 will be DISABLED after 30 seconds"
echo ""
echo "Phases:"
echo "  - Phase 1 (0-30s):  Normal - all links active"
echo "  - Phase 2 (30s+):   Link Down - test redundancy"
echo ""
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

    # Re-enable the link if it was disabled
    sudo ip link set s2-eth1 up 2>/dev/null || true

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
RUN_RESULTS_DIR="$PROJECT_ROOT/results/10-dscp-qos-13switches-linkfailure/run_$TIMESTAMP"
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

# Step 2: Run Topology with Link Failure Test
echo ""
echo "[2/2] Starting Network Topology with Link Failure Test..."
echo ""

cd "$RUN_RESULTS_DIR"

# Write experiment header to log
{
    echo "=============================================================="
    echo "  SCENARIO 10: DSCP QoS with Link Failure Test"
    echo "=============================================================="
    echo ""
    echo "Topology: 1 Core + 3 Aggregation (Ring) + 9 Edge"
    echo "  - 13 switches total"
    echo "  - Ring: s2 ↔ s3 ↔ s4 ↔ s2 (redundancy)"
    echo "  - Link s2-s1 will be disabled after 30s"
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

    if [ -f "$RUN_RESULTS_DIR/link_failure_log.txt" ]; then
        echo "=== LINK FAILURE LOG ==="
        cat "$RUN_RESULTS_DIR/link_failure_log.txt"
        echo ""
    fi

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
echo "  - experiment.log     : Topology build, STP, QoS, link failure logs"
echo "  - ryu_controller.log : SDN controller logs"
echo "  - publisher_*.log    : Per-publisher logs"
echo "  - subscriber.log     : Subscriber logs"
echo ""
