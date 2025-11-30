#!/bin/bash
# ==========================================
# Master Experiment Runner
# ==========================================
# Runs SDN-MQTT experiments with automatic controller and scenario management
#
# Usage:
#   ./run_experiment.sh --scenario SCENARIO_NAME --duration TIME
#   ./run_experiment.sh --list
#
# Examples:
#   ./run_experiment.sh --scenario 01-single-switch-3hosts --duration 60
#   ./run_experiment.sh --scenario 01-single-switch-3hosts --duration 5m
#   ./run_experiment.sh --list

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIOS_DIR="$PROJECT_ROOT/scenarios"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SCENARIO=""
DURATION=""
AUTO_CONTROLLER=true
KEEP_CONTROLLER_RUNNING=false

# ==========================================
# Functions
# ==========================================

show_help() {
    cat << EOF
${BLUE}═══════════════════════════════════════════════════════════════════${NC}
  SDN-MQTT Experiment Runner
${BLUE}═══════════════════════════════════════════════════════════════════${NC}

${GREEN}USAGE:${NC}
  ./run_experiment.sh --scenario SCENARIO_NAME --duration TIME
  ./run_experiment.sh --list
  ./run_experiment.sh --help

${GREEN}OPTIONS:${NC}
  --scenario NAME     Scenario to run (e.g., 01-single-switch-3hosts)
  --duration TIME     Duration (e.g., 60, 5m, 1h, or omit for manual stop)
  --list              List all available scenarios
  --no-auto-controller  Don't auto-start controller (use existing)
  --keep-controller   Keep controller running after experiment
  --help              Show this help message

${GREEN}EXAMPLES:${NC}
  # Run scenario for 60 seconds (auto-start controller)
  ./run_experiment.sh --scenario 01-single-switch-3hosts --duration 60

  # Run scenario for 5 minutes
  ./run_experiment.sh --scenario 01-single-switch-3hosts --duration 5m

  # Run until manually stopped (Ctrl+C)
  ./run_experiment.sh --scenario 01-single-switch-3hosts

  # Use existing controller
  ./run_experiment.sh --scenario 01-single-switch-3hosts --duration 60 --no-auto-controller

  # Keep controller running after experiment
  ./run_experiment.sh --scenario 01-single-switch-3hosts --duration 60 --keep-controller

  # List available scenarios
  ./run_experiment.sh --list

${BLUE}═══════════════════════════════════════════════════════════════════${NC}
EOF
}

list_scenarios() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "  Available Scenarios"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    if [ ! -d "$SCENARIOS_DIR" ] || [ -z "$(ls -A "$SCENARIOS_DIR" 2>/dev/null)" ]; then
        echo -e "${RED}No scenarios found in $SCENARIOS_DIR${NC}"
        exit 1
    fi

    for scenario_dir in "$SCENARIOS_DIR"/*; do
        if [ -d "$scenario_dir" ]; then
            scenario_name=$(basename "$scenario_dir")
            readme="$scenario_dir/README.md"

            echo -e "${GREEN}📁 $scenario_name${NC}"

            if [ -f "$readme" ]; then
                # Extract first line description
                desc=$(grep -m 1 "^#" "$readme" 2>/dev/null | sed 's/^# //' || echo "No description")
                echo "   $desc"
            fi

            # Check if scenario has required files
            if [ -f "$scenario_dir/run_scenario.sh" ]; then
                echo -e "   ✓ run_scenario.sh"
            else
                echo -e "   ${RED}✗ run_scenario.sh missing${NC}"
            fi

            if [ -f "$scenario_dir/topology_config.py" ]; then
                echo -e "   ✓ topology_config.py"
            else
                echo -e "   ${RED}✗ topology_config.py missing${NC}"
            fi

            if [ -f "$scenario_dir/controller.py" ]; then
                echo -e "   ✓ controller.py"
            else
                echo -e "   ${RED}✗ controller.py missing${NC}"
            fi

            echo ""
        fi
    done

    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
}

start_controller() {
    local scenario_name=$1
    local controller_file="$SCENARIOS_DIR/$scenario_name/controller.py"

    if [ ! -f "$controller_file" ]; then
        echo -e "${RED}[ERROR] Controller not found: $controller_file${NC}"
        exit 1
    fi

    echo -e "${YELLOW}[CONTROLLER] Starting Ryu controller for scenario: $scenario_name${NC}"

    # Stop any existing controller
    pkill -9 -f ryu-manager 2>/dev/null || true
    sleep 2

    # Start controller
    source /home/aldi/ryu39/bin/activate
    /home/aldi/ryu39/bin/python3.9 -u /home/aldi/ryu39/bin/ryu-manager "$controller_file" ryu.app.ofctl_rest > "$PROJECT_ROOT/logs/ryu.log" 2>&1 &
    CONTROLLER_PID=$!

    # Wait for controller to be ready
    echo -n "  Waiting for controller to start"
    for i in {1..30}; do
        if curl -s http://127.0.0.1:8080/stats/switches > /dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}  ✓ Controller ready (PID: $CONTROLLER_PID)${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done

    echo ""
    echo -e "${RED}[ERROR] Controller failed to start${NC}"
    exit 1
}

stop_controller() {
    if pgrep -f ryu-manager > /dev/null; then
        echo -e "${YELLOW}[CONTROLLER] Stopping Ryu controller...${NC}"
        pkill -9 -f ryu-manager 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}  ✓ Controller stopped${NC}"
    fi
}

run_scenario() {
    local scenario_name=$1
    local duration=$2
    local scenario_dir="$SCENARIOS_DIR/$scenario_name"
    local scenario_script="$scenario_dir/run_scenario.sh"

    if [ ! -d "$scenario_dir" ]; then
        echo -e "${RED}[ERROR] Scenario not found: $scenario_name${NC}"
        echo "Run './run_experiment.sh --list' to see available scenarios"
        exit 1
    fi

    if [ ! -f "$scenario_script" ]; then
        echo -e "${RED}[ERROR] Scenario script not found: $scenario_script${NC}"
        exit 1
    fi

    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "  Running Experiment"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Scenario: ${GREEN}$scenario_name${NC}"
    if [ -n "$duration" ]; then
        echo -e "  Duration: ${GREEN}$duration${NC}"
    else
        echo -e "  Duration: ${YELLOW}Manual stop (Ctrl+C)${NC}"
    fi
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Run the scenario
    cd "$scenario_dir"
    if [ -n "$duration" ]; then
        sudo bash run_scenario.sh "$duration"
    else
        sudo bash run_scenario.sh
    fi
}

# ==========================================
# Parse Arguments
# ==========================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --scenario)
            SCENARIO="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --list)
            list_scenarios
            exit 0
            ;;
        --no-auto-controller)
            AUTO_CONTROLLER=false
            shift
            ;;
        --keep-controller)
            KEEP_CONTROLLER_RUNNING=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run './run_experiment.sh --help' for usage information"
            exit 1
            ;;
    esac
done

# ==========================================
# Main Execution
# ==========================================

# Check if scenario is provided
if [ -z "$SCENARIO" ]; then
    echo -e "${RED}[ERROR] No scenario specified${NC}"
    echo ""
    show_help
    exit 1
fi

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Start controller if needed
if [ "$AUTO_CONTROLLER" = true ]; then
    start_controller "$SCENARIO"

    # Setup cleanup trap
    cleanup() {
        echo ""
        echo -e "${YELLOW}[CLEANUP] Experiment interrupted${NC}"
        if [ "$KEEP_CONTROLLER_RUNNING" = false ]; then
            stop_controller
        else
            echo -e "${YELLOW}[INFO] Keeping controller running (--keep-controller)${NC}"
        fi
        exit 0
    }
    trap cleanup SIGINT SIGTERM
else
    # Check if controller is already running
    if ! curl -s http://127.0.0.1:8080/stats/switches > /dev/null 2>&1; then
        echo -e "${RED}[ERROR] No controller running and --no-auto-controller specified${NC}"
        echo "Either:"
        echo "  1. Remove --no-auto-controller flag, or"
        echo "  2. Start controller manually: ./run_ryu_controller.sh"
        exit 1
    fi
    echo -e "${GREEN}[INFO] Using existing controller${NC}"
fi

# Run the scenario
run_scenario "$SCENARIO" "$DURATION"

# Cleanup
if [ "$AUTO_CONTROLLER" = true ] && [ "$KEEP_CONTROLLER_RUNNING" = false ]; then
    echo ""
    stop_controller
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "  Experiment Complete!"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
