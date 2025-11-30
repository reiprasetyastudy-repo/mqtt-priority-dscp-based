#!/bin/bash
###############################################################################
# Run Full Experiment - Scenario 06 DSCP QoS (13 Switches)
#
# Starts controller + topology in one script
# Usage: ./run_experiment.sh [duration]
#        ./run_experiment.sh 300  (5 minutes)
###############################################################################

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
RYU_ENV="/home/aldi/ryu39"

# Parse duration
DURATION=${1:-300}

echo "=============================================================="
echo "  SCENARIO 06: DSCP-Based QoS (13 Switches)"
echo "=============================================================="
echo ""
echo "Topology: Hierarchical 3-Tier (13 switches, 19 hosts)"
echo "Duration: $DURATION seconds"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "[CLEANUP] Stopping all components..."

    # Kill Ryu
    if [ ! -z "$RYU_PID" ]; then
        kill $RYU_PID 2>/dev/null || true
        echo "  ✓ Ryu controller stopped"
    fi

    # Cleanup Mininet
    sudo pkill -f mosquitto 2>/dev/null || true
    sudo pkill -f publisher 2>/dev/null || true
    sudo pkill -f subscriber 2>/dev/null || true
    sudo mn -c > /dev/null 2>&1 || true

    echo "  ✓ Cleanup complete"
    echo ""
}

trap cleanup EXIT

# Create timestamped results directory FIRST
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_RESULTS_DIR="$PROJECT_ROOT/results/06-dscp-qos-13switches/run_$TIMESTAMP"
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

# Wait for controller to initialize
sleep 3

# Check if controller is still running
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
    echo "  SCENARIO 06: DSCP-Based QoS (13 Switches)"
    echo "=============================================================="
    echo ""
    echo "Topology: Hierarchical 3-Tier (13 switches, 19 hosts)"
    echo "Duration: $DURATION seconds (send) + $DURATION seconds (drain)"
    echo "Total Time: $((DURATION * 2)) seconds"
    echo "Start Time: $(date)"
    echo ""
} > "$RUN_RESULTS_DIR/logs/experiment.log"

# Run topology and append output to experiment.log
sudo python3 "$SCENARIO_DIR/topology_config.py" --duration "$DURATION" 2>&1 | tee -a "$RUN_RESULTS_DIR/logs/experiment.log"

echo ""
echo "=============================================================="
echo "  EXPERIMENT COMPLETE!"
echo "=============================================================="
echo ""

# Display results location and summary
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
echo "  - experiment.log     : Topology build, QoS, MQTT logs"
echo "  - ryu_controller.log : SDN controller logs"
echo "  - publisher_*.log    : Per-publisher logs"
echo "  - subscriber.log     : Subscriber logs"
echo ""
