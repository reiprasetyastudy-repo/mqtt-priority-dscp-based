#!/bin/bash
#
# Scenario 10: DSCP-Based QoS with Dual Core - Core Failure Test
#
# Same topology as Scenario 09, but with Core 2 failure simulation
#
# Phases:
# - Phase 1 (0-30s): Normal operation - both cores active
# - Phase 2 (30s+): Core 2 disabled - traffic via Core 1 only
#

SCENARIO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="/home/mqtt-sdn"
RYU_ENV="/home/aldi/ryu39"

# Default duration
DURATION=${1:-60}

echo "=============================================================="
echo "  SCENARIO 10: Dual Core + Core Failure Test"
echo "=============================================================="
echo ""
echo "Configuration:"
echo "  - Topology    : 2 Core + 3 Distribution + 9 Edge"
echo "  - Switches    : 14"
echo "  - Publishers  : 18 (9 anomaly + 9 normal)"
echo "  - Duration    : ${DURATION}s send + ${DURATION}s drain"
echo ""
echo "Test Phases:"
echo "  - Phase 1 (0-30s)  : Normal operation (both cores active)"
echo "  - Phase 2 (30s+)   : Core 2 disabled (failover to Core 1)"
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

# Create timestamped results directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_RESULTS_DIR="$PROJECT_ROOT/results/10-dscp-qos-14switches-corefailure/run_$TIMESTAMP"
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
    exit 1
fi

# Step 2: Run Topology with Core Failure
echo ""
echo "[2/2] Starting Dual Core Topology with Core Failure Test..."
echo ""

cd "$RUN_RESULTS_DIR"

{
    echo "=============================================================="
    echo "  SCENARIO 10: Dual Core + Core Failure Test"
    echo "  Started: $(date)"
    echo "=============================================================="
    echo ""
    echo "Configuration:"
    echo "  - Topology: 2 Core + 3 Distribution + 9 Edge = 14 switches"
    echo "  - Publishers: 18 (9 anomaly DSCP 46 + 9 normal DSCP 0)"
    echo "  - Duration: ${DURATION}s send + ${DURATION}s drain"
    echo ""
    echo "Test Phases:"
    echo "  - Phase 1 (0-30s): Normal operation"
    echo "  - Phase 2 (30s+): Core 2 (s2) disabled"
    echo ""
} > experiment.log

sudo python3 "$SCENARIO_DIR/topology_config.py" $DURATION 2>&1 | tee -a experiment.log

echo ""
echo "=============================================================="
echo "  EXPERIMENT COMPLETE"
echo "=============================================================="
echo ""
echo "Results saved to: $RUN_RESULTS_DIR"
echo "  - mqtt_metrics_log.csv"
echo "  - metrics_summary.txt"
echo "  - core_failure_log.txt"
echo "  - logs/"
echo ""
