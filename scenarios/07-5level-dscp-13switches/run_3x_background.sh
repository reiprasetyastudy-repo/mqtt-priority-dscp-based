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
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Parse arguments
DURATION=${1:-600}
REPETITIONS=3
DELAY_BETWEEN_RUNS=180

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

# Calculate estimated time
TOTAL_PER_RUN=$((DURATION + 10 + DURATION))
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
MASTER_RESULTS_DIR="$PROJECT_ROOT/results/07-5level-dscp-13switches/batch_3x_${TIMESTAMP}"
mkdir -p "$MASTER_RESULTS_DIR"

NOHUP_LOG="$MASTER_RESULTS_DIR/nohup_output.log"
BATCH_LOG="$MASTER_RESULTS_DIR/batch_experiment.log"

echo -e "${GREEN}Background logs will be saved to:${NC}"
echo "  $NOHUP_LOG"
echo "  $MASTER_RESULTS_DIR"
echo ""

# Create the background script
BACKGROUND_SCRIPT="$MASTER_RESULTS_DIR/run_background.sh"

cat > "$BACKGROUND_SCRIPT" << 'HEREDOC_EOF'
#!/bin/bash

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "BATCH_LOG_PLACEHOLDER"
}

# Function to run single experiment
run_single_experiment() {
    local run_number=$1
    local duration=DURATION_PLACEHOLDER
    local run_dir="MASTER_RESULTS_DIR_PLACEHOLDER/run_${run_number}"

    echo ""
    echo "================================================================"
    echo "                    Run ${run_number} of 3                      "
    echo "================================================================"
    echo ""

    log "Starting Run ${run_number}/3"

    # Cleanup
    echo "[1/5] Cleaning up..."
    log "Cleanup started for Run ${run_number}"
    mn -c > /dev/null 2>&1 || true
    pkill -f ryu-manager > /dev/null 2>&1 || true
    pkill -f mosquitto > /dev/null 2>&1 || true
    sleep 2

    # Start Ryu
    echo "[2/5] Starting Ryu controller..."
    log "Starting Ryu controller for Run ${run_number}"
    cd "PROJECT_ROOT_PLACEHOLDER"
    source ryu39/bin/activate
    ryu-manager --verbose shared/sdn/controller.py > "$run_dir/ryu_controller.log" 2>&1 &
    RYU_PID=$!
    sleep 3

    if ! ps -p $RYU_PID > /dev/null; then
        log "ERROR: Failed to start Ryu controller for Run ${run_number}"
        echo "ERROR: Failed to start Ryu controller"
        return 1
    fi

    echo "✓ Ryu controller started (PID: $RYU_PID)"
    log "Ryu controller started with PID $RYU_PID"

    # Run experiment
    echo "[3/5] Running experiment (${duration}s send + ${duration}s drain)..."
    log "Running topology.py for Run ${run_number}"

    cd "SCRIPT_DIR_PLACEHOLDER"
    START_TIME=$(date +%s)

    if python3 topology.py --duration $duration --output-dir "$run_dir"; then
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo "✓ Experiment completed in ${ELAPSED}s"
        log "Run ${run_number} completed successfully in ${ELAPSED}s"
    else
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo "✗ Experiment failed after ${ELAPSED}s"
        log "ERROR: Run ${run_number} failed after ${ELAPSED}s"
        return 1
    fi

    # Verify
    echo "[4/5] Verifying results..."
    if [ -f "$run_dir/metrics_summary.txt" ]; then
        echo "✓ Summary file generated"
        log "Summary file verified for Run ${run_number}"
    else
        echo "⚠ Warning: Summary file not found"
        log "WARNING: Summary file not found for Run ${run_number}"
    fi

    # Cleanup
    echo "[5/5] Cleaning up..."
    log "Cleanup started after Run ${run_number}"
    mn -c > /dev/null 2>&1 || true
    pkill -f ryu-manager > /dev/null 2>&1 || true
    pkill -f mosquitto > /dev/null 2>&1 || true

    log "Run ${run_number} finished"
    echo "✓ Run ${run_number} complete!"

    return 0
}

# Main loop
log "Batch experiment started: 3 runs with DURATION_PLACEHOLDER seconds each"
log "Master results directory: MASTER_RESULTS_DIR_PLACEHOLDER"

SUCCESS_COUNT=0
FAILED_RUNS=()

for i in 1 2 3; do
    RUN_DIR="MASTER_RESULTS_DIR_PLACEHOLDER/run_${i}"
    mkdir -p "$RUN_DIR/logs"

    if run_single_experiment $i; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        FAILED_RUNS+=($i)
        echo "Run $i failed, but continuing..."
        log "Run $i marked as failed"
    fi

    # Delay between runs (except after last)
    if [ $i -lt 3 ]; then
        echo ""
        echo "Waiting 180s before next run..."
        log "Delay 180s before Run $((i + 1))"
        sleep 180
        echo "Ready for next run"
        echo ""
    fi
done

# Final cleanup
echo ""
echo "================================================================"
echo "                    Final Cleanup                              "
echo "================================================================"
log "Final cleanup started"
mn -c > /dev/null 2>&1 || true
pkill -f ryu-manager > /dev/null 2>&1 || true
pkill -f mosquitto > /dev/null 2>&1 || true

# Summary
echo ""
echo "================================================================"
echo "                    Experiment Summary                         "
echo "================================================================"
echo ""
echo "Completed: ${SUCCESS_COUNT}/3 runs"

if [ ${#FAILED_RUNS[@]} -gt 0 ]; then
    echo "Failed runs: ${FAILED_RUNS[*]}"
    log "Failed runs: ${FAILED_RUNS[*]}"
else
    echo "All runs completed successfully!"
    log "All 3 runs completed successfully"
fi

echo ""
echo "Results Location:"
echo "  MASTER_RESULTS_DIR_PLACEHOLDER"
echo ""

log "Batch experiment completed: ${SUCCESS_COUNT}/3 successful"
echo "Done!"
HEREDOC_EOF

# Replace placeholders
sed -i "s|DURATION_PLACEHOLDER|$DURATION|g" "$BACKGROUND_SCRIPT"
sed -i "s|MASTER_RESULTS_DIR_PLACEHOLDER|$MASTER_RESULTS_DIR|g" "$BACKGROUND_SCRIPT"
sed -i "s|PROJECT_ROOT_PLACEHOLDER|$PROJECT_ROOT|g" "$BACKGROUND_SCRIPT"
sed -i "s|SCRIPT_DIR_PLACEHOLDER|$SCRIPT_DIR|g" "$BACKGROUND_SCRIPT"
sed -i "s|BATCH_LOG_PLACEHOLDER|$BATCH_LOG|g" "$BACKGROUND_SCRIPT"

chmod +x "$BACKGROUND_SCRIPT"

# Run in background
echo -e "${YELLOW}Starting experiment in background...${NC}"

nohup "$BACKGROUND_SCRIPT" > "$NOHUP_LOG" 2>&1 &
BACKGROUND_PID=$!

# Wait to check if started
sleep 2

if ps -p $BACKGROUND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Experiment started successfully in background!${NC}"
    echo ""
    echo -e "${CYAN}Process Information:${NC}"
    echo "  PID: $BACKGROUND_PID"
    echo "  Log: $NOHUP_LOG"
    echo "  Results: $MASTER_RESULTS_DIR"
    echo ""
    echo -e "${YELLOW}Monitor Progress:${NC}"
    echo "  tail -f $NOHUP_LOG"
    echo ""
    echo -e "${YELLOW}Check Status:${NC}"
    echo "  ps -p $BACKGROUND_PID"
    echo ""
    echo -e "${YELLOW}Stop Experiment:${NC}"
    echo "  sudo kill $BACKGROUND_PID"
    echo "  sudo mn -c && sudo pkill -f ryu-manager && sudo pkill -f mosquitto"
    echo ""
    echo -e "${GREEN}✓ You can now safely disconnect from this terminal!${NC}"
    echo ""
    if [ $HOURS -gt 0 ]; then
        echo -e "${CYAN}Expected completion: $(date -d "+${TOTAL_TIME} seconds" '+%Y-%m-%d %H:%M:%S') (${HOURS}h ${MINUTES}min)${NC}"
    else
        echo -e "${CYAN}Expected completion: $(date -d "+${TOTAL_TIME} seconds" '+%Y-%m-%d %H:%M:%S') (${MINUTES}min)${NC}"
    fi
else
    echo -e "${RED}✗ Failed to start background process${NC}"
    echo "Check log: $NOHUP_LOG"
    exit 1
fi
