#!/bin/bash
###############################################################################
# Run Scenario 04 - Modular QoS
#
# This script:
# 1. Starts Ryu controller
# 2. Runs the topology with MQTT
# 3. Cleans up after completion
#
# Usage:
#   ./run_scenario.sh [DURATION_SECONDS]
#
# Examples:
#   ./run_scenario.sh 300    # Run for 5 minutes
#   ./run_scenario.sh        # Run with CLI (interactive)
###############################################################################

set -e  # Exit on error

# Configuration
SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/mqtt-sdn"
RYU_ENV="/home/aldi/ryu39"
DURATION=${1:-""}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."

    # Kill Ryu controller
    if [ ! -z "$RYU_PID" ]; then
        log_info "Stopping Ryu controller (PID: $RYU_PID)"
        kill $RYU_PID 2>/dev/null || true
    fi

    # Kill any remaining processes
    sudo pkill -f mosquitto 2>/dev/null || true
    sudo pkill -f publisher 2>/dev/null || true
    sudo pkill -f subscriber 2>/dev/null || true

    # Clean Mininet
    sudo mn -c > /dev/null 2>&1 || true

    log_success "Cleanup complete"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Print header
echo "=========================================================================="
echo "  Scenario 04: Modular SDN-based QoS for IoT"
echo "=========================================================================="
echo ""

# Check if Ryu environment exists
if [ ! -d "$RYU_ENV" ]; then
    log_error "Ryu environment not found at $RYU_ENV"
    exit 1
fi

# Check if running as root for Mininet
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Step 1: Start Ryu Controller
log_info "Starting Ryu controller..."
source "$RYU_ENV/bin/activate"

"$RYU_ENV/bin/python3.9" -u "$RYU_ENV/bin/ryu-manager" \
    "$SCENARIO_DIR/run_controller.py" \
    ryu.app.ofctl_rest \
    > "$PROJECT_ROOT/logs/ryu.log" 2>&1 &

RYU_PID=$!
log_success "Ryu controller started (PID: $RYU_PID)"

# Wait for controller to initialize
sleep 3

# Check if controller is still running
if ! ps -p $RYU_PID > /dev/null; then
    log_error "Ryu controller failed to start. Check logs/ryu.log"
    exit 1
fi

# Step 2: Run Topology
log_info "Starting network topology..."

if [ -z "$DURATION" ]; then
    log_info "Running in CLI mode (press Ctrl+D to exit CLI)"
    python3 "$SCENARIO_DIR/main.py" --cli
else
    log_info "Running for $DURATION seconds"
    python3 "$SCENARIO_DIR/main.py" --duration "$DURATION"
fi

# Step 3: Generate summary
log_info "Simulation complete"

# Find latest results directory
LATEST_RESULTS=$(ls -td "$PROJECT_ROOT/results/04-modular-qos"/run_* 2>/dev/null | head -1)

if [ ! -z "$LATEST_RESULTS" ]; then
    log_success "Results saved to: $LATEST_RESULTS"

    # Check if summary exists
    if [ -f "$LATEST_RESULTS/metrics_summary.txt" ]; then
        echo ""
        echo "=========================================================================="
        echo "  RESULTS SUMMARY"
        echo "=========================================================================="
        cat "$LATEST_RESULTS/metrics_summary.txt"
    else
        log_warning "Summary file not generated. Check subscriber logs."
    fi
else
    log_warning "No results directory found"
fi

echo ""
echo "=========================================================================="
echo "  Scenario Complete!"
echo "=========================================================================="
