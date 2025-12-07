#!/bin/bash
#
# Run Scenario 07: 5-Level DSCP Priority Test
#
# This script runs the experiment with all 5 DSCP priority levels.
# Usage: sudo ./run_experiment.sh [DURATION]
#   DURATION: Send phase duration in seconds (default: 600)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Parse arguments
DURATION=${1:-600}  # Default: 10 minutes

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Scenario 07: 5-Level DSCP Test${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Configuration:"
echo "  - Duration: ${DURATION}s (send phase)"
echo "  - Drain: ${DURATION}s (1:1 ratio)"
echo "  - Publishers: 15 (5 levels × 3 floors)"
echo "  - DSCP Levels: 46, 34, 26, 10, 0"
echo "  - Topology: 13 switches (hierarchical)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

# Cleanup previous run
echo -e "${YELLOW}Cleaning up previous runs...${NC}"
mn -c > /dev/null 2>&1 || true
pkill -f ryu-manager > /dev/null 2>&1 || true
pkill -f mosquitto > /dev/null 2>&1 || true
sleep 2

# Start Ryu controller
echo -e "${YELLOW}Starting Ryu controller...${NC}"
cd "$PROJECT_ROOT"
source ryu39/bin/activate
ryu-manager --verbose shared/sdn/controller.py > /dev/null 2>&1 &
RYU_PID=$!
sleep 3

# Check if Ryu started
if ! ps -p $RYU_PID > /dev/null; then
    echo -e "${RED}ERROR: Failed to start Ryu controller${NC}"
    exit 1
fi

echo -e "${GREEN}Ryu controller started (PID: $RYU_PID)${NC}"

# Run experiment
echo -e "${YELLOW}Running experiment...${NC}"
cd "$SCRIPT_DIR"
python3 topology.py --duration $DURATION

# Show results location
LATEST_RUN=$(ls -td "$PROJECT_ROOT/results/07-5level-dscp-13switches/run_"* 2>/dev/null | head -1)
if [ -n "$LATEST_RUN" ]; then
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}Experiment Complete!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo "Results saved to:"
    echo "  $LATEST_RUN"
    echo ""
    echo "View summary:"
    echo "  cat $LATEST_RUN/metrics_summary.txt"
    echo ""
    echo "View CSV:"
    echo "  cat $LATEST_RUN/metrics_summary.csv"
fi

# Cleanup
echo -e "${YELLOW}Cleaning up...${NC}"
mn -c > /dev/null 2>&1 || true
pkill -f ryu-manager > /dev/null 2>&1 || true
pkill -f mosquitto > /dev/null 2>&1 || true

echo -e "${GREEN}Done!${NC}"
