#!/bin/bash
# =============================================================================
# AUTOMATED EXPERIMENT RUNNER
# =============================================================================
# Runs all scenarios (01, 02, 05, 06) with 3 repetitions each.
# Designed to run in background with nohup.
#
# Usage:
#   nohup sudo ./run_all_experiments.sh > experiment_master.log 2>&1 &
#   tail -f experiment_master.log  # Monitor progress
#
# =============================================================================

set -e

# Configuration
SCENARIOS=("01-baseline-13switches" "02-lossy-13switches" "05-dualredundant-17switches" "06-distfailure-17switches")
RUNS_PER_SCENARIO=3
DURATION=600          # 10 minutes send phase
DELAY_BETWEEN_RUNS=180  # 3 minutes between runs

# Paths
PROJECT_ROOT="/home/mqtt-sdn"
SCENARIOS_DIR="$PROJECT_ROOT/scenarios"
RYU_VENV="/home/aldi/ryu39"

# Colors for output (disabled in nohup, but useful for manual runs)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_header() {
    echo ""
    echo "============================================================"
    log "$1"
    echo "============================================================"
}

cleanup() {
    log "Cleaning up..."
    sudo mn -c > /dev/null 2>&1 || true
    sudo pkill -f ryu-manager > /dev/null 2>&1 || true
    sudo pkill -f mosquitto > /dev/null 2>&1 || true
    sudo pkill -f publisher > /dev/null 2>&1 || true
    sudo pkill -f subscriber > /dev/null 2>&1 || true
    sleep 5
    log "Cleanup done"
}

start_controller() {
    log "Starting Ryu controller..."
    source "$RYU_VENV/bin/activate"
    cd "$PROJECT_ROOT/shared/sdn"
    ryu-manager controller.py --ofp-tcp-listen-port 6633 > /dev/null 2>&1 &
    sleep 5
    log "Controller started"
}

run_scenario() {
    local scenario=$1
    local run_num=$2
    local scenario_dir="$SCENARIOS_DIR/$scenario"
    
    log "[$scenario] Run $run_num/$RUNS_PER_SCENARIO STARTED"
    
    local start_time=$(date +%s)
    
    # Run the experiment
    cd "$scenario_dir"
    sudo python3 topology.py --duration $DURATION
    
    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))
    
    log "[$scenario] Run $run_num/$RUNS_PER_SCENARIO COMPLETED (${minutes}m ${seconds}s)"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

log_header "EXPERIMENT BATCH STARTED"
log "Scenarios: ${SCENARIOS[*]}"
log "Runs per scenario: $RUNS_PER_SCENARIO"
log "Duration per run: $DURATION seconds (+ drain phase)"
log "Delay between runs: $DELAY_BETWEEN_RUNS seconds"

total_runs=$((${#SCENARIOS[@]} * RUNS_PER_SCENARIO))
current_run=0
batch_start=$(date +%s)

for scenario in "${SCENARIOS[@]}"; do
    log_header "SCENARIO: $scenario"
    
    for run in $(seq 1 $RUNS_PER_SCENARIO); do
        current_run=$((current_run + 1))
        
        log "--- Overall Progress: $current_run / $total_runs ---"
        
        # Cleanup before each run
        cleanup
        
        # Start fresh controller
        start_controller
        
        # Run experiment
        run_scenario "$scenario" "$run"
        
        # Delay between runs (except for the last one)
        if [ $current_run -lt $total_runs ]; then
            log "Waiting $DELAY_BETWEEN_RUNS seconds before next run..."
            sleep $DELAY_BETWEEN_RUNS
        fi
    done
    
    log "[$scenario] ALL $RUNS_PER_SCENARIO RUNS COMPLETED"
done

# Final cleanup
cleanup

batch_end=$(date +%s)
total_elapsed=$((batch_end - batch_start))
total_hours=$((total_elapsed / 3600))
total_minutes=$(((total_elapsed % 3600) / 60))

log_header "ALL EXPERIMENTS COMPLETED"
log "Total scenarios: ${#SCENARIOS[@]}"
log "Total runs: $total_runs"
log "Total time: ${total_hours}h ${total_minutes}m"
log "Results saved in: $PROJECT_ROOT/results/"

echo ""
echo "============================================================"
echo "  EXPERIMENT BATCH FINISHED SUCCESSFULLY!"
echo "============================================================"
