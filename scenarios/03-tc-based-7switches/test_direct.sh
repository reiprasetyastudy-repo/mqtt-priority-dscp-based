#!/bin/bash
# Direct Test - Menggunakan controller_v2.py langsung (no run_experiment.sh)

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"

echo "=========================================="
echo "  Scenario 03 - DIRECT Test"
echo "=========================================="
echo ""
echo "Using controller_v2.py (MAC Learning + SetQueue)"
echo "Duration: 5 minutes"
echo ""
echo "=========================================="

# Cleanup
echo "[1/5] Cleanup..."
sudo pkill -f mosquitto 2>/dev/null || true
sudo pkill -f publisher 2>/dev/null || true
sudo pkill -f subscriber 2>/dev/null || true
sudo pkill -f ryu-manager 2>/dev/null || true
sudo mn -c 2>/dev/null || true
sleep 2

# Start controller_v2
echo ""
echo "[2/5] Starting controller_v2.py..."
source /home/aldi/ryu39/bin/activate
/home/aldi/ryu39/bin/python3.9 -u /home/aldi/ryu39/bin/ryu-manager \
    "$SCENARIO_DIR/controller_v2.py" \
    ryu.app.ofctl_rest > "$PROJECT_ROOT/logs/ryu.log" 2>&1 &

# Wait for controller
sleep 3
if curl -s http://127.0.0.1:8080/stats/switches > /dev/null 2>&1; then
    echo "  ✓ Controller ready"
else
    echo "  ✗ Controller failed to start!"
    exit 1
fi

# Create results directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RESULTS_DIR="$PROJECT_ROOT/results/03-tc-based-7switches/run_$TIMESTAMP"
mkdir -p "$RESULTS_DIR"

echo ""
echo "[3/5] Starting topology..."
echo "  Results: $RESULTS_DIR"

# Run topology (save output to results dir)
cd "$RESULTS_DIR"
sudo python3 "$SCENARIO_DIR/topology_config.py" --duration 300 2>&1 | tee topology.log

echo ""
echo "[4/5] Generating summary..."

# Generate summary from CSV
python3 << 'EOF'
import csv, os

LOG_FILE = "mqtt_metrics_log.csv"
SUMMARY_FILE = "metrics_summary.txt"

class MetricsAnalyzer:
    def __init__(self):
        self.delays = {'anomaly': [], 'normal': []}
        self.received_seq = {'anomaly': set(), 'normal': set()}
        self.max_seq = {'anomaly': -1, 'normal': -1}
        self.timestamps = []

    def analyze_csv(self, filename):
        if not os.path.exists(filename):
            print(f"ERROR: {filename} not found!")
            return
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
            return {'expected': 0, 'received': 0, 'lost': 0, 'loss_rate': 0}
        expected_count = self.max_seq[msg_type] + 1
        received_count = len(self.received_seq[msg_type])
        lost_count = expected_count - received_count
        loss_rate = (lost_count / expected_count * 100) if expected_count > 0 else 0
        return {
            'expected': expected_count,
            'received': received_count,
            'lost': lost_count,
            'loss_rate': loss_rate
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
analyzer.analyze_csv(LOG_FILE)

if not analyzer.delays['anomaly'] and not analyzer.delays['normal']:
    print("No data collected!")
    exit(1)

summary = analyzer.get_summary()

# Save summary
output = []
output.append("=" * 70)
output.append(" " * 20 + "SIMULATION SUMMARY")
output.append("=" * 70)
output.append("")

for msg_type in ['anomaly', 'normal']:
    if summary[msg_type]:
        s = summary[msg_type]
        loss = s['loss_info']
        output.append(f"{msg_type.upper()}:")
        output.append(f"  Messages Received : {s['count']}")
        output.append(f"  Avg Delay         : {s['avg_delay']:.2f} ms")
        output.append(f"  Min Delay         : {s['min_delay']:.2f} ms")
        output.append(f"  Max Delay         : {s['max_delay']:.2f} ms")
        output.append(f"  Std Dev Delay     : {s['std_delay']:.2f} ms")
        output.append(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms")
        output.append(f"  Max Seq Number    : {s['max_seq']}")
        output.append(f"")
        output.append(f"  PACKET LOSS:")
        output.append(f"    Expected        : {loss['expected']} messages")
        output.append(f"    Received        : {loss['received']} messages")
        output.append(f"    Lost            : {loss['lost']} messages")
        output.append(f"    Loss Rate       : {loss['loss_rate']:.2f}%")
        output.append("")

output.append(f"TOTAL:")
output.append(f"  Duration          : {summary['total']['duration']:.2f} s")
output.append(f"  Total Messages    : {summary['total']['total_messages']}")
output.append(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s")
output.append("=" * 70)

# Print
for line in output:
    print(line)

# Save
with open(SUMMARY_FILE, 'w') as f:
    for line in output:
        f.write(line + "\n")

# Analysis
anomaly_delay = summary['anomaly']['avg_delay'] if summary['anomaly'] else 0
normal_delay = summary['normal']['avg_delay'] if summary['normal'] else 0
diff = normal_delay - anomaly_delay
diff_pct = (diff / anomaly_delay) * 100 if anomaly_delay > 0 else 0

print("")
print("ANALYSIS:")
print("=" * 70)
print(f"Anomaly Avg Delay : {anomaly_delay:.2f} ms")
print(f"Normal Avg Delay  : {normal_delay:.2f} ms")
print(f"Difference        : {diff:.2f} ms ({diff_pct:.1f}%)")
print("")

if diff_pct > 50:
    print("✅ PRIORITY WORKS! Normal {:.1f}% SLOWER".format(diff_pct))
    print("   MAC Learning + Queue fix is SUCCESSFUL!")
elif diff_pct > 20:
    print("⚠️  PARTIAL SUCCESS ({:.1f}% slower)".format(diff_pct))
elif abs(diff_pct) < 5:
    print("❌ NO EFFECT (±5%)")
else:
    print("❌ REVERSED! Anomaly {:.1f}% slower!".format(abs(diff_pct)))

print("=" * 70)
EOF

echo ""
echo "[5/5] Cleanup..."
sudo pkill -f mosquitto 2>/dev/null || true
sudo pkill -f publisher 2>/dev/null || true
sudo pkill -f subscriber 2>/dev/null || true
sudo pkill -f ryu-manager 2>/dev/null || true
sudo mn -c 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Test Complete!"
echo "=========================================="
echo "Results saved to: $RESULTS_DIR"
echo ""
