#!/bin/bash
###############################################################################
# Run Full Experiment - Scenario 05 DSCP QoS
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
echo "  SCENARIO 05: DSCP-Based QoS (7 Switches)"
echo "=============================================================="
echo ""
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

# Step 1: Start Ryu Controller
echo "[1/2] Starting Ryu Controller..."
source "$RYU_ENV/bin/activate"

"$RYU_ENV/bin/python3.9" -u "$RYU_ENV/bin/ryu-manager" \
    "$SCENARIO_DIR/controller_dscp.py" \
    ryu.app.ofctl_rest \
    > "$PROJECT_ROOT/logs/ryu.log" 2>&1 &

RYU_PID=$!
echo "  ✓ Controller started (PID: $RYU_PID)"

# Wait for controller to initialize
sleep 3

# Check if controller is still running
if ! ps -p $RYU_PID > /dev/null; then
    echo "[ERROR] Controller failed to start!"
    echo "Check: $PROJECT_ROOT/logs/ryu.log"
    exit 1
fi

# Step 2: Run Topology
echo ""
echo "[2/2] Starting Network Topology..."
echo ""

# Create timestamped results directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_RESULTS_DIR="$PROJECT_ROOT/results/05-dscp-qos-7switches/run_$TIMESTAMP"
mkdir -p "$RUN_RESULTS_DIR"

echo "Results will be saved to: $RUN_RESULTS_DIR"
echo ""

# Change to results directory
cd "$RUN_RESULTS_DIR"

sudo python3 "$SCENARIO_DIR/topology_config.py" --duration "$DURATION"

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
        echo "--------------------------------------------------------------"
        echo "METRICS SUMMARY:"
        echo "--------------------------------------------------------------"
        cat "$RUN_RESULTS_DIR/metrics_summary.txt"
        echo "--------------------------------------------------------------"
    fi
fi

echo ""
