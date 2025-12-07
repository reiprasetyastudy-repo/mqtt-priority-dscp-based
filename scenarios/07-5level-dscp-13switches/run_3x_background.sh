#!/bin/bash
#
# Run Scenario 07 - 3 Repetitions in Background
#
# This script runs the 3x experiment in background using nohup
# so you can disconnect from terminal safely.
#
# Usage: sudo ./run_3x_background.sh [DURATION]
#   DURATION: Send phase duration in seconds (default: 600)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Parse arguments
DURATION=${1:-600}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

# Calculate estimated time
TOTAL_PER_RUN=$((DURATION + 10 + DURATION))
DELAY_BETWEEN_RUNS=180
TOTAL_TIME=$((TOTAL_PER_RUN * 3 + DELAY_BETWEEN_RUNS * 2))
TOTAL_MINUTES=$((TOTAL_TIME / 60))
HOURS=$((TOTAL_MINUTES / 60))
MINUTES=$((TOTAL_MINUTES % 60))

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}  Scenario 07: 5-Level DSCP - Background Execution (3x Reps)  ${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  - Duration: ${DURATION}s per run"
echo "  - Repetitions: 3x"
echo "  - Mode: Background (nohup)"
echo ""
if [ $HOURS -gt 0 ]; then
    echo -e "${YELLOW}Estimated Total Time: ${HOURS}h ${MINUTES}min${NC}"
else
    echo -e "${YELLOW}Estimated Total Time: ${MINUTES}min${NC}"
fi
echo ""

# Create log directory with timestamp
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_DIR="$PROJECT_ROOT/results/07-5level-dscp-13switches/background_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

NOHUP_LOG="$LOG_DIR/nohup_output.log"
PROCESS_PID_FILE="$LOG_DIR/process.pid"

echo -e "${GREEN}Background logs will be saved to:${NC}"
echo "  $NOHUP_LOG"
echo ""

# Start experiment in background
echo -e "${YELLOW}Starting experiment in background...${NC}"

cd "$SCRIPT_DIR"

# Run with nohup and redirect all output
nohup bash -c "
    # Save PID
    echo \$\$ > '$PROCESS_PID_FILE'

    # Run the experiment
    ./run_3x_experiments.sh $DURATION

    # Save exit code
    EXIT_CODE=\$?
    echo \"\" >> '$NOHUP_LOG'
    echo \"Experiment finished with exit code: \$EXIT_CODE\" >> '$NOHUP_LOG'
    echo \"Finished at: \$(date)\" >> '$NOHUP_LOG'

    # Remove PID file when done
    rm -f '$PROCESS_PID_FILE'

    exit \$EXIT_CODE
" > "$NOHUP_LOG" 2>&1 &

BACKGROUND_PID=$!

# Wait a moment to check if process started
sleep 2

# Check if still running
if ps -p $BACKGROUND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Experiment started successfully in background!${NC}"
    echo ""
    echo -e "${CYAN}Process Information:${NC}"
    echo "  PID: $BACKGROUND_PID"
    echo "  Log: $NOHUP_LOG"
    echo "  Status: Running"
    echo ""
    echo -e "${YELLOW}Monitor Progress:${NC}"
    echo "  # Follow the log in real-time"
    echo "  tail -f $NOHUP_LOG"
    echo ""
    echo "  # Check if still running"
    echo "  ps -p $BACKGROUND_PID"
    echo ""
    echo "  # View current status"
    echo "  cat $NOHUP_LOG | tail -50"
    echo ""
    echo -e "${YELLOW}Stop Experiment:${NC}"
    echo "  # Kill the background process"
    echo "  sudo kill $BACKGROUND_PID"
    echo ""
    echo "  # Force kill if needed"
    echo "  sudo kill -9 $BACKGROUND_PID"
    echo ""
    echo "  # Cleanup (after killing)"
    echo "  sudo mn -c"
    echo "  sudo pkill -f ryu-manager"
    echo "  sudo pkill -f mosquitto"
    echo ""
    echo -e "${GREEN}You can now safely disconnect from this terminal!${NC}"
    echo -e "${GREEN}The experiment will continue running in the background.${NC}"
    echo ""
    if [ $HOURS -gt 0 ]; then
        echo -e "${CYAN}Expected completion: $(date -d "+${TOTAL_TIME} seconds" '+%Y-%m-%d %H:%M:%S') (${HOURS}h ${MINUTES}min from now)${NC}"
    else
        echo -e "${CYAN}Expected completion: $(date -d "+${TOTAL_TIME} seconds" '+%Y-%m-%d %H:%M:%S') (${MINUTES}min from now)${NC}"
    fi
else
    echo -e "${RED}✗ Failed to start background process${NC}"
    echo "Check log: $NOHUP_LOG"
    exit 1
fi
