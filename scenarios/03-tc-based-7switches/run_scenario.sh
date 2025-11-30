#!/bin/bash
# ==========================================
# Scenario 03: TC-Based Priority (7 Switches)
# ==========================================
# Simple & Proven approach using TC (Traffic Control)
# Usage: ./run_scenario.sh [duration]

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
SCENARIO_NAME="03-tc-based-7switches"
RESULTS_DIR="$PROJECT_ROOT/results/$SCENARIO_NAME"
LOG_DIR="$PROJECT_ROOT/logs"

# Parse duration parameter
DURATION_SECONDS=0
AUTO_STOP=false

if [ $# -gt 0 ]; then
    DURATION_INPUT=$1

    # Parse format: 30, 60s, 5m, 1h
    if [[ "$DURATION_INPUT" =~ ^([0-9]+)s?$ ]]; then
        DURATION_SECONDS="${BASH_REMATCH[1]}"
    elif [[ "$DURATION_INPUT" =~ ^([0-9]+)m$ ]]; then
        MINUTES="${BASH_REMATCH[1]}"
        DURATION_SECONDS=$((MINUTES * 60))
    elif [[ "$DURATION_INPUT" =~ ^([0-9]+)h$ ]]; then
        HOURS="${BASH_REMATCH[1]}"
        DURATION_SECONDS=$((HOURS * 3600))
    else
        echo "[ERROR] Invalid duration format: $DURATION_INPUT"
        exit 1
    fi
    AUTO_STOP=true
fi

echo "=========================================="
echo "  Scenario: $SCENARIO_NAME"
echo "=========================================="
echo "Topology: TC-Based Priority (Simple & Proven)"
echo "  - 1 Core switch (s1) - Broker"
echo "  - 2 Aggregation switches (s2-s3)"
echo "  - 4 Edge switches (s4-s7)"
echo "  - 8 Publishers (4 anomaly + 4 normal)"
echo ""
echo "Priority Mechanism: TC (Traffic Control)"
echo "  - Anomaly traffic: TOS=0x10 (High priority)"
echo "  - Normal traffic: TOS=0x00 (Best effort)"
echo ""

if [ "$AUTO_STOP" = true ]; then
    echo "Duration: $DURATION_INPUT ($DURATION_SECONDS seconds)"
else
    echo "Duration: Manual stop (Ctrl+C)"
fi

echo "=========================================="
echo ""

# Check if Ryu Controller is running
echo "[1/3] Checking prerequisites..."
if ! curl -s http://127.0.0.1:8080/stats/switches > /dev/null 2>&1; then
    echo "[ERROR] Ryu Controller not running!"
    echo ""
    echo "Please start controller:"
    echo "  cd $PROJECT_ROOT"
    echo "  ./run_experiment.sh --scenario $SCENARIO_NAME --duration $DURATION_INPUT"
    exit 1
fi
echo "  ✓ Ryu Controller detected"

# Cleanup old processes
echo ""
echo "[2/3] Cleaning up old processes..."
sudo pkill -f mosquitto 2>/dev/null || true
sudo pkill -f publisher 2>/dev/null || true
sudo pkill -f subscriber 2>/dev/null || true
sudo mn -c 2>/dev/null || true
echo "  ✓ Cleanup complete"

# Create timestamped results directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RUN_RESULTS_DIR="$RESULTS_DIR/run_$TIMESTAMP"
mkdir -p "$RUN_RESULTS_DIR"
mkdir -p "$LOG_DIR"

echo ""
echo "[3/3] Starting topology..."
echo "  Results will be saved to: $RUN_RESULTS_DIR"
echo ""

# Change to results directory
cd "$RUN_RESULTS_DIR"

# Run topology
sudo python3 "$SCENARIO_DIR/topology_config.py" --duration "$DURATION_SECONDS"

echo ""
echo "=========================================="
echo "  Experiment Complete!"
echo "=========================================="
echo "Results saved to:"
echo "  $RUN_RESULTS_DIR"
echo "=========================================="
