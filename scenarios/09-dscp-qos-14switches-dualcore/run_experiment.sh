#!/bin/bash
#
# Scenario 09: DSCP-Based QoS with Dual Core Topology (14 Switches)
#
# Topology: 2 Core + 3 Distribution + 9 Edge = 14 switches
# Redundancy: Each distribution connects to BOTH core switches
#

SCENARIO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="/home/mqtt-sdn"
RYU_ENV="/home/aldi/ryu39"

# Default duration
DURATION=${1:-60}

echo "=============================================================="
echo "  SCENARIO 09: Dual Core Topology (14 Switches)"
echo "=============================================================="
echo ""
echo "Configuration:"
echo "  - Topology    : 2 Core + 3 Distribution + 9 Edge"
echo "  - Switches    : 14"
echo "  - Publishers  : 18 (9 anomaly + 9 normal)"
echo "  - Duration    : ${DURATION}s send + ${DURATION}s drain"
echo "  - Redundancy  : Dual core (enterprise standard)"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "[Cleanup] Stopping all components..."
    sudo pkill -f "ryu-manager" 2>/dev/null
    sudo pkill -f "publisher_dscp" 2>/dev/null
    sudo pkill -f "subscriber" 2>/dev/null
    sudo pkill -f "mosquitto" 2>/dev/null
    sudo mn -c 2>/dev/null
    echo "  ✓ Cleanup complete"
    echo ""
}

trap cleanup EXIT

# Create timestamped results directory FIRST
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_RESULTS_DIR="$PROJECT_ROOT/results/09-dscp-qos-14switches-dualcore/run_$TIMESTAMP"
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
echo "[2/2] Starting Dual Core Topology..."
echo ""

cd "$RUN_RESULTS_DIR"

# Write experiment header to log
{
    echo "=============================================================="
    echo "  SCENARIO 09: Dual Core Topology"
    echo "  Started: $(date)"
    echo "=============================================================="
    echo ""
    echo "Configuration:"
    echo "  - Topology: 2 Core + 3 Distribution + 9 Edge = 14 switches"
    echo "  - Publishers: 18 (9 anomaly DSCP 46 + 9 normal DSCP 0)"
    echo "  - Duration: ${DURATION}s send + ${DURATION}s drain"
    echo "  - Bandwidth: 0.5 Mbps per link"
    echo ""
} > experiment.log

# Run the topology (this will block until complete)
sudo python3 "$SCENARIO_DIR/topology_config.py" $DURATION 2>&1 | tee -a experiment.log

echo ""
echo "=============================================================="
echo "  EXPERIMENT COMPLETE"
echo "=============================================================="
echo ""
echo "Results saved to: $RUN_RESULTS_DIR"
echo "  - mqtt_metrics_log.csv"
echo "  - metrics_summary.txt"
echo "  - logs/"
echo ""
