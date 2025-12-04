#!/bin/bash
# Scenario 02: Lossy Network - 13 Switches with Packet Loss
set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
SCENARIO_NAME="02-lossy-13switches"
RYU_ENV="/home/aldi/ryu39"
DURATION=${1:-300}

echo "=============================================================="
echo "  SCENARIO 02: Lossy Network (13 Switches)"
echo "=============================================================="
echo "  Packet Loss: Core 10%, Edge 5%"
echo "  Duration: ${DURATION}s send + ${DURATION}s drain"
echo ""

cleanup() {
    sudo pkill -f "ryu-manager" 2>/dev/null || true
    sudo pkill -f "mosquitto" 2>/dev/null || true
    sudo mn -c > /dev/null 2>&1 || true
}
trap cleanup EXIT

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_DIR="$PROJECT_ROOT/results/$SCENARIO_NAME/run_$TIMESTAMP"
mkdir -p "$RUN_DIR/logs"

echo "[1/2] Starting Controller..."
source "$RYU_ENV/bin/activate"
"$RYU_ENV/bin/python3.9" -u "$RYU_ENV/bin/ryu-manager" \
    "$PROJECT_ROOT/shared/sdn/controller.py" \
    > "$RUN_DIR/logs/ryu_controller.log" 2>&1 &
sleep 3

echo "[2/2] Starting Topology..."
cd "$RUN_DIR"
sudo python3 "$SCENARIO_DIR/topology.py" --duration "$DURATION" --output-dir "$RUN_DIR" 2>&1 | tee logs/experiment.log

echo "Results: $RUN_DIR"
