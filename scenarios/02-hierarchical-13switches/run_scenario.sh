#!/bin/bash
# ==========================================
# Scenario 02: Hierarchical 3-Tier (13 Switches)
# ==========================================
# Topology: 13 switches in 3-tier hierarchy
# - 1 Core switch (s1)
# - 3 Aggregation switches (s2-s4)
# - 9 Edge switches (s5-s13)
# - 18 publishers (9 anomaly + 9 normal)
# Filtering: Subnet-based (10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24)
# Usage: ./run_scenario.sh [duration]

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
SCENARIO_NAME="02-hierarchical-13switches"
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
        echo ""
        echo "Valid formats:"
        echo "  60 or 60s  = 60 seconds"
        echo "  5m         = 5 minutes"
        echo "  1h         = 1 hour"
        exit 1
    fi
    AUTO_STOP=true
fi

echo "=========================================="
echo "  Scenario: $SCENARIO_NAME"
echo "=========================================="
echo "Topology: Hierarchical 3-Tier (Smart Building)"
echo "  - 1 Core switch (s1) - Gateway + Broker"
echo "  - 3 Aggregation switches (s2-s4) - Per floor"
echo "  - 9 Edge switches (s5-s13) - Per room"
echo "  - 18 Publishers (9 anomaly + 9 normal)"
echo ""
echo "Network Depth: 3 hops (Edge → Aggregation → Core)"
echo ""
echo "Filtering Method: Subnet-based"
echo "  - Floor 1 (10.0.1.0/24) → s5, s6, s7"
echo "  - Floor 2 (10.0.2.0/24) → s8, s9, s10"
echo "  - Floor 3 (10.0.3.0/24) → s11, s12, s13"
echo "  - Anomaly traffic → Queue 1, Priority 20"
echo "  - Normal traffic  → Queue 2, Priority 10"
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
    echo "Please start controller in another terminal:"
    echo "  cd $PROJECT_ROOT"
    echo "  ./run_ryu_controller.sh"
    echo ""
    echo "Or use the master script:"
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
sudo pkill -f topology_config 2>/dev/null || true
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

# Change to results directory so CSV files are saved there
cd "$RUN_RESULTS_DIR"

# Run topology
if [ "$AUTO_STOP" = true ]; then
    # Start topology in background
    sudo python3 "$SCENARIO_DIR/topology_config.py" --duration "$DURATION_SECONDS" &
    TOPOLOGY_PID=$!

    # Show progress bar with countdown
    echo ""
    echo "=========================================="
    echo "  Simulation Running"
    echo "=========================================="
    echo ""

    ELAPSED=0
    while [ $ELAPSED -lt $DURATION_SECONDS ]; do
        # Check if topology process still running
        if ! kill -0 $TOPOLOGY_PID 2>/dev/null; then
            echo ""
            echo "[INFO] Topology stopped early"
            break
        fi

        # Calculate remaining time
        REMAINING=$((DURATION_SECONDS - ELAPSED))

        # Format time
        if [ $REMAINING -ge 3600 ]; then
            HOURS=$((REMAINING / 3600))
            MINS=$(( (REMAINING % 3600) / 60 ))
            SECS=$((REMAINING % 60))
            TIME_STR="${HOURS}h ${MINS}m ${SECS}s"
        elif [ $REMAINING -ge 60 ]; then
            MINS=$((REMAINING / 60))
            SECS=$((REMAINING % 60))
            TIME_STR="${MINS}m ${SECS}s"
        else
            TIME_STR="${REMAINING}s"
        fi

        # Progress bar
        PERCENT=$((ELAPSED * 100 / DURATION_SECONDS))
        BAR_LENGTH=40
        FILLED=$((PERCENT * BAR_LENGTH / 100))
        BAR=$(printf '%*s' "$FILLED" | tr ' ' '█')
        EMPTY=$(printf '%*s' $((BAR_LENGTH - FILLED)) | tr ' ' '░')

        # Print progress (overwrite line)
        printf "\r[%3d%%] [%s%s] Remaining: %s   " "$PERCENT" "$BAR" "$EMPTY" "$TIME_STR"

        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done

    # Wait for topology to finish
    wait $TOPOLOGY_PID 2>/dev/null || true

    echo ""
    echo ""

    # Generate summary after simulation
    echo ""
    echo "=========================================="
    echo "  Generating Metrics Summary"
    echo "=========================================="

    python3 << 'PYTHON_SUMMARY'
import csv
import os
import sys

LOG_FILE = "mqtt_metrics_log.csv"
SUMMARY_FILE = "metrics_summary.txt"

if not os.path.exists(LOG_FILE):
    print(f"[WARNING] No CSV data found at {LOG_FILE}")
    sys.exit(0)

class MetricsAnalyzer:
    def __init__(self):
        self.delays = {'anomaly': [], 'normal': []}
        self.received_seq = {'anomaly': set(), 'normal': set()}
        self.max_seq = {'anomaly': -1, 'normal': -1}
        self.timestamps = []

    def analyze_csv(self, filename):
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                msg_type = row.get('type', '')
                if msg_type not in ['anomaly', 'normal']:
                    continue
                delay = float(row.get('delay_ms', 0))
                seq = int(row.get('seq', 0))
                timestamp = float(row.get('timestamp_sent', 0))
                self.delays[msg_type].append(delay)
                self.received_seq[msg_type].add(seq)
                self.timestamps.append(timestamp)
                if seq > self.max_seq[msg_type]:
                    self.max_seq[msg_type] = seq

    def calculate_jitter(self, msg_type):
        delays = self.delays[msg_type]
        if len(delays) < 2:
            return 0
        jitters = [abs(delays[i] - delays[i-1]) for i in range(1, len(delays))]
        return sum(jitters) / len(jitters)

    def calculate_loss_rate(self, msg_type):
        if self.max_seq[msg_type] < 0:
            return {'expected': 0, 'received': 0, 'lost': 0, 'loss_rate': 0, 'lost_seqs': []}
        expected_count = self.max_seq[msg_type] + 1
        received_count = len(self.received_seq[msg_type])
        lost_count = expected_count - received_count
        loss_rate = (lost_count / expected_count * 100) if expected_count > 0 else 0
        lost_seqs = sorted(set(range(expected_count)) - self.received_seq[msg_type])
        return {
            'expected': expected_count,
            'received': received_count,
            'lost': lost_count,
            'loss_rate': loss_rate,
            'lost_seqs': lost_seqs
        }

    def get_summary(self):
        if len(self.timestamps) < 2:
            total_time = 0
        else:
            total_time = max(self.timestamps) - min(self.timestamps)
        summary = {}
        for msg_type in ['anomaly', 'normal']:
            delays = self.delays[msg_type]
            loss_info = self.calculate_loss_rate(msg_type)
            if len(delays) > 0:
                mean_delay = sum(delays) / len(delays)
                variance = sum((x - mean_delay)**2 for x in delays) / len(delays)
                std_delay = variance ** 0.5 if len(delays) > 1 else 0
                summary[msg_type] = {
                    'count': len(delays),
                    'avg_delay': mean_delay,
                    'min_delay': min(delays),
                    'max_delay': max(delays),
                    'std_delay': std_delay,
                    'avg_jitter': self.calculate_jitter(msg_type),
                    'max_seq': self.max_seq[msg_type],
                    'loss_info': loss_info
                }
            else:
                summary[msg_type] = None
        total_messages = len(self.delays['anomaly']) + len(self.delays['normal'])
        summary['total'] = {
            'duration': total_time,
            'total_messages': total_messages,
            'throughput': total_messages / total_time if total_time > 0 else 0
        }
        return summary

analyzer = MetricsAnalyzer()
try:
    analyzer.analyze_csv(LOG_FILE)
    summary = analyzer.get_summary()

    print("\n" + "=" * 70)
    print(" " * 20 + "SIMULATION SUMMARY")
    print("=" * 70)

    for msg_type in ['anomaly', 'normal']:
        if summary[msg_type]:
            s = summary[msg_type]
            loss = s['loss_info']
            print(f"\n{msg_type.upper()}:")
            print(f"  Messages Received : {s['count']}")
            print(f"  Avg Delay         : {s['avg_delay']:.2f} ms")
            print(f"  Min Delay         : {s['min_delay']:.2f} ms")
            print(f"  Max Delay         : {s['max_delay']:.2f} ms")
            print(f"  Std Dev Delay     : {s['std_delay']:.2f} ms")
            print(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms")
            print(f"  Max Seq Number    : {s['max_seq']}")
            print(f"\n  PACKET LOSS:")
            print(f"    Expected        : {loss['expected']} messages")
            print(f"    Received        : {loss['received']} messages")
            print(f"    Lost            : {loss['lost']} messages")
            print(f"    Loss Rate       : {loss['loss_rate']:.2f}%")
            if loss['lost'] > 0 and loss['lost'] <= 20:
                print(f"    Lost Seq Numbers: {loss['lost_seqs']}")
            elif loss['lost'] > 20:
                print(f"    Lost Seq Numbers: {loss['lost_seqs'][:20]} ... (first 20)")

    print(f"\nTOTAL:")
    print(f"  Duration          : {summary['total']['duration']:.2f} s")
    print(f"  Total Messages    : {summary['total']['total_messages']}")
    print(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s")
    print("=" * 70 + "\n")

    # Save to file
    with open(SUMMARY_FILE, "w") as f:
        f.write("=" * 70 + "\n")
        f.write(" " * 20 + "SIMULATION SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        for msg_type in ['anomaly', 'normal']:
            if summary[msg_type]:
                s = summary[msg_type]
                loss = s['loss_info']
                f.write(f"{msg_type.upper()}:\n")
                f.write(f"  Messages Received : {s['count']}\n")
                f.write(f"  Avg Delay         : {s['avg_delay']:.2f} ms\n")
                f.write(f"  Min Delay         : {s['min_delay']:.2f} ms\n")
                f.write(f"  Max Delay         : {s['max_delay']:.2f} ms\n")
                f.write(f"  Std Dev Delay     : {s['std_delay']:.2f} ms\n")
                f.write(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms\n")
                f.write(f"  Max Seq Number    : {s['max_seq']}\n")
                f.write(f"\n  PACKET LOSS:\n")
                f.write(f"    Expected        : {loss['expected']} messages\n")
                f.write(f"    Received        : {loss['received']} messages\n")
                f.write(f"    Lost            : {loss['lost']} messages\n")
                f.write(f"    Loss Rate       : {loss['loss_rate']:.2f}%\n")
                if loss['lost'] > 0:
                    f.write(f"    Lost Seq Numbers: {loss['lost_seqs']}\n")
                f.write("\n")
        f.write(f"TOTAL:\n")
        f.write(f"  Duration          : {summary['total']['duration']:.2f} s\n")
        f.write(f"  Total Messages    : {summary['total']['total_messages']}\n")
        f.write(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s\n")

    print(f"Summary saved to: {os.path.abspath(SUMMARY_FILE)}\n")
except Exception as e:
    print(f"[ERROR] Failed to generate summary: {e}")
    import traceback
    traceback.print_exc()
PYTHON_SUMMARY

    echo ""
    echo "=========================================="
    echo "  Experiment Complete!"
    echo "=========================================="
    echo "Results saved to:"
    echo "  $RUN_RESULTS_DIR"
    echo ""
    echo "Files:"
    echo "  - mqtt_metrics_log.csv    (raw data)"
    echo "  - metrics_summary.txt     (analysis)"
    echo "=========================================="
else
    echo "Starting topology (manual stop mode)..."
    echo "Press Ctrl+C to stop"
    echo ""
    sudo python3 "$SCENARIO_DIR/topology_config.py"
fi
