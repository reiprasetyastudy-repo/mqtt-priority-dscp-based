#!/bin/bash
#
# Run Scenario 07 - 3 Repetitions
#
# This script runs the 5-Level DSCP experiment 3 times automatically
# for statistical consistency and reproducibility.
#
# Usage: sudo ./run_3x_experiments.sh [DURATION]
#   DURATION: Send phase duration in seconds (default: 600 = 10 minutes)
#

set -e  # Exit on error

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
DURATION=${1:-600}  # Default: 10 minutes
REPETITIONS=3
DELAY_BETWEEN_RUNS=180  # 3 minutes delay between runs

# Calculate timings
DRAIN_TIME=$DURATION
CLEANUP_TIME=10
TOTAL_PER_RUN=$((DURATION + CLEANUP_TIME + DRAIN_TIME))
TOTAL_TIME=$((TOTAL_PER_RUN * REPETITIONS + DELAY_BETWEEN_RUNS * (REPETITIONS - 1)))

# Convert to minutes for display
TOTAL_MINUTES=$((TOTAL_TIME / 60))
HOURS=$((TOTAL_MINUTES / 60))
MINUTES=$((TOTAL_MINUTES % 60))

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}     Scenario 07: 5-Level DSCP - 3 Repetition Experiment      ${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  - Repetitions: ${REPETITIONS}x"
echo "  - Duration per run: ${DURATION}s (send phase)"
echo "  - Drain per run: ${DRAIN_TIME}s"
echo "  - Delay between runs: ${DELAY_BETWEEN_RUNS}s (3 min)"
echo "  - Publishers: 15 (5 DSCP levels × 3 floors)"
echo "  - DSCP Levels: 46, 34, 26, 10, 0"
echo ""
echo -e "${YELLOW}Time Breakdown per Run:${NC}"
echo "  1. Send Phase:     ${DURATION}s"
echo "  2. Cleanup Buffer: ${CLEANUP_TIME}s"
echo "  3. Drain Phase:    ${DRAIN_TIME}s"
echo "  ─────────────────────────"
echo "  Total per run:     ${TOTAL_PER_RUN}s (~$((TOTAL_PER_RUN / 60)) min)"
echo ""
echo -e "${YELLOW}Total Estimated Time:${NC}"
if [ $HOURS -gt 0 ]; then
    echo "  ${HOURS}h ${MINUTES}min (~${TOTAL_TIME}s total)"
else
    echo "  ${MINUTES}min (~${TOTAL_TIME}s total)"
fi
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

# Create master results directory with timestamp
MASTER_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MASTER_RESULTS_DIR="$PROJECT_ROOT/results/07-5level-dscp-13switches/batch_3x_${MASTER_TIMESTAMP}"
mkdir -p "$MASTER_RESULTS_DIR"

echo -e "${GREEN}Results will be saved to:${NC}"
echo "  $MASTER_RESULTS_DIR"
echo ""

# Confirmation
read -p "Press ENTER to start, or Ctrl+C to cancel... "
echo ""

# Log file
LOG_FILE="$MASTER_RESULTS_DIR/batch_experiment.log"
touch "$LOG_FILE"

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to run single experiment
run_single_experiment() {
    local run_number=$1
    local run_dir="$MASTER_RESULTS_DIR/run_${run_number}"

    echo ""
    echo -e "${CYAN}================================================================${NC}"
    echo -e "${CYAN}                    Run ${run_number} of ${REPETITIONS}                           ${NC}"
    echo -e "${CYAN}================================================================${NC}"
    echo ""

    log "Starting Run ${run_number}/${REPETITIONS}"

    # Cleanup previous run
    echo -e "${YELLOW}[1/5] Cleaning up previous runs...${NC}"
    log "Cleanup started for Run ${run_number}"
    mn -c > /dev/null 2>&1 || true
    pkill -f ryu-manager > /dev/null 2>&1 || true
    pkill -f mosquitto > /dev/null 2>&1 || true
    sleep 2

    # Start Ryu controller
    echo -e "${YELLOW}[2/5] Starting Ryu controller...${NC}"
    log "Starting Ryu controller for Run ${run_number}"
    cd "$PROJECT_ROOT"
    source ryu39/bin/activate
    ryu-manager --verbose shared/sdn/controller.py > "$run_dir/ryu_controller.log" 2>&1 &
    RYU_PID=$!
    sleep 3

    # Check if Ryu started
    if ! ps -p $RYU_PID > /dev/null; then
        log "ERROR: Failed to start Ryu controller for Run ${run_number}"
        echo -e "${RED}ERROR: Failed to start Ryu controller${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Ryu controller started (PID: $RYU_PID)${NC}"
    log "Ryu controller started with PID $RYU_PID"

    # Run experiment
    echo -e "${YELLOW}[3/5] Running experiment (${DURATION}s send + ${DRAIN_TIME}s drain)...${NC}"
    log "Running topology.py for Run ${run_number}"

    cd "$SCRIPT_DIR"
    START_TIME=$(date +%s)

    if python3 topology.py --duration $DURATION --output-dir "$run_dir"; then
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo -e "${GREEN}✓ Experiment completed in ${ELAPSED}s${NC}"
        log "Run ${run_number} completed successfully in ${ELAPSED}s"
    else
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo -e "${RED}✗ Experiment failed after ${ELAPSED}s${NC}"
        log "ERROR: Run ${run_number} failed after ${ELAPSED}s"
        return 1
    fi

    # Verify results
    echo -e "${YELLOW}[4/5] Verifying results...${NC}"
    if [ -f "$run_dir/metrics_summary.txt" ]; then
        echo -e "${GREEN}✓ Summary file generated${NC}"
        log "Summary file verified for Run ${run_number}"

        # Show quick summary
        echo ""
        echo -e "${BLUE}Quick Summary for Run ${run_number}:${NC}"
        grep -A 10 "=== DSCP" "$run_dir/metrics_summary.txt" | head -20 || true
        echo ""
    else
        echo -e "${YELLOW}⚠ Warning: Summary file not found, but experiment may have completed${NC}"
        log "WARNING: Summary file not found for Run ${run_number}"
    fi

    # Cleanup
    echo -e "${YELLOW}[5/5] Cleaning up...${NC}"
    log "Cleanup started after Run ${run_number}"
    mn -c > /dev/null 2>&1 || true
    pkill -f ryu-manager > /dev/null 2>&1 || true
    pkill -f mosquitto > /dev/null 2>&1 || true

    log "Run ${run_number} finished"
    echo -e "${GREEN}✓ Run ${run_number} complete!${NC}"

    return 0
}

# Main experiment loop
log "Batch experiment started: ${REPETITIONS} runs with ${DURATION}s each"
log "Master results directory: $MASTER_RESULTS_DIR"

SUCCESS_COUNT=0
FAILED_RUNS=()

for i in $(seq 1 $REPETITIONS); do
    # Create run directory
    RUN_DIR="$MASTER_RESULTS_DIR/run_${i}"
    mkdir -p "$RUN_DIR/logs"

    # Run experiment
    if run_single_experiment $i; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        FAILED_RUNS+=($i)
        echo -e "${RED}Run $i failed, but continuing with remaining runs...${NC}"
        log "Run $i marked as failed"
    fi

    # Delay between runs (except after last run)
    if [ $i -lt $REPETITIONS ]; then
        echo ""
        echo -e "${CYAN}────────────────────────────────────────────────────────${NC}"
        echo -e "${YELLOW}Waiting ${DELAY_BETWEEN_RUNS}s before next run...${NC}"
        log "Delay ${DELAY_BETWEEN_RUNS}s before Run $((i + 1))"

        for countdown in $(seq $DELAY_BETWEEN_RUNS -1 1); do
            printf "\r  Time until next run: %3ds " $countdown
            sleep 1
        done
        printf "\r                                \r"
        echo -e "${GREEN}✓ Ready for next run${NC}"
        echo ""
    fi
done

# Final cleanup
echo ""
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}                    Final Cleanup                              ${NC}"
echo -e "${CYAN}================================================================${NC}"
log "Final cleanup started"
mn -c > /dev/null 2>&1 || true
pkill -f ryu-manager > /dev/null 2>&1 || true
pkill -f mosquitto > /dev/null 2>&1 || true

# Summary
echo ""
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}                    Experiment Summary                         ${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "${GREEN}Completed: ${SUCCESS_COUNT}/${REPETITIONS} runs${NC}"

if [ ${#FAILED_RUNS[@]} -gt 0 ]; then
    echo -e "${RED}Failed runs: ${FAILED_RUNS[*]}${NC}"
    log "Failed runs: ${FAILED_RUNS[*]}"
else
    echo -e "${GREEN}All runs completed successfully!${NC}"
    log "All ${REPETITIONS} runs completed successfully"
fi

echo ""
echo -e "${YELLOW}Results Location:${NC}"
echo "  $MASTER_RESULTS_DIR"
echo ""
echo -e "${YELLOW}Individual Run Results:${NC}"
for i in $(seq 1 $REPETITIONS); do
    RUN_DIR="$MASTER_RESULTS_DIR/run_${i}"
    if [ -f "$RUN_DIR/metrics_summary.txt" ]; then
        echo -e "  ${GREEN}✓${NC} Run $i: $RUN_DIR"
    else
        echo -e "  ${RED}✗${NC} Run $i: $RUN_DIR (no summary)"
    fi
done

echo ""
echo -e "${YELLOW}View Results:${NC}"
echo "  # View all summaries"
echo "  cat $MASTER_RESULTS_DIR/run_*/metrics_summary.txt"
echo ""
echo "  # View specific run"
echo "  cat $MASTER_RESULTS_DIR/run_1/metrics_summary.txt"
echo ""
echo "  # View batch log"
echo "  cat $MASTER_RESULTS_DIR/batch_experiment.log"

log "Batch experiment completed: ${SUCCESS_COUNT}/${REPETITIONS} successful"
echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}                    All Done!                                  ${NC}"
echo -e "${GREEN}================================================================${NC}"
