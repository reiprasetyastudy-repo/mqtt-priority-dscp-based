#!/bin/bash
###############################################################################
# Scenario 01: Baseline - 13 Switch Hierarchical Topology
#
# Usage: ./run_experiment.sh [duration]
#        ./run_experiment.sh 300  (5 minutes)
###############################################################################

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
SCENARIO_NAME="01-baseline-13switches"
RYU_ENV="/home/aldi/ryu39"

# Parse arguments
DURATION=${1:-300}

echo "=============================================================="
echo "  SCENARIO 01: Baseline (13 Switches)"
echo "=============================================================="
echo ""
echo "Configuration:"
echo "  - Topology   : Hierarchical 3-Tier"
echo "  - Switches   : 13 (1 Core + 3 Agg + 9 Edge)"
echo "  - Publishers : 18 (9 anomaly + 9 normal)"
echo "  - Bandwidth  : 0.2 Mbps"
echo "  - Msg Rate   : 10 msg/s"
echo "  - Duration   : ${DURATION}s send + ${DURATION}s drain"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "[Cleanup] Stopping all components..."
    sudo pkill -f "ryu-manager" 2>/dev/null || true
    sudo pkill -f "mosquitto" 2>/dev/null || true
    sudo pkill -f "publisher" 2>/dev/null || true
    sudo pkill -f "subscriber" 2>/dev/null || true
    sudo mn -c > /dev/null 2>&1 || true
    echo "  Done"
}

trap cleanup EXIT

# Create results directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_DIR="$PROJECT_ROOT/results/$SCENARIO_NAME/run_$TIMESTAMP"
mkdir -p "$RUN_DIR/logs"

echo "Results: $RUN_DIR"
echo ""

# Start Ryu Controller
echo "[1/2] Starting Ryu Controller..."
source "$RYU_ENV/bin/activate"

"$RYU_ENV/bin/python3.9" -u "$RYU_ENV/bin/ryu-manager" \
    "$PROJECT_ROOT/shared/sdn/controller.py" \
    > "$RUN_DIR/logs/ryu_controller.log" 2>&1 &

RYU_PID=$!
echo "  Controller PID: $RYU_PID"
sleep 3

if ! ps -p $RYU_PID > /dev/null; then
    echo "[ERROR] Controller failed to start!"
    cat "$RUN_DIR/logs/ryu_controller.log"
    exit 1
fi

# Run Topology
echo ""
echo "[2/2] Starting Topology..."
echo ""

cd "$RUN_DIR"

sudo python3 "$SCENARIO_DIR/topology.py" --duration "$DURATION" 2>&1 | tee logs/experiment.log

echo ""
echo "=============================================================="
echo "  EXPERIMENT COMPLETE"
echo "=============================================================="
echo "Results: $RUN_DIR"
echo ""
