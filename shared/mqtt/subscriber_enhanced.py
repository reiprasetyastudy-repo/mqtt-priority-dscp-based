import paho.mqtt.client as mqtt
import json
import time
import csv
import signal
import sys
import os
from collections import defaultdict

LOG_FILE = "mqtt_metrics_log.csv"
SUMMARY_FILE = "metrics_summary.txt"

# Read configuration from environment variables
CONFIG = {
    'bandwidth_limit_enabled': os.environ.get('ENABLE_BANDWIDTH_LIMIT', 'Unknown'),
    'bandwidth_mbps': os.environ.get('LINK_BANDWIDTH_MBPS', 'Unknown'),
    'qos_queues_enabled': os.environ.get('ENABLE_QOS_QUEUES', 'Unknown'),
    'scenario': os.environ.get('SCENARIO_NAME', 'Unknown'),
    'topology': os.environ.get('TOPOLOGY_TYPE', 'Unknown'),
    'num_switches': os.environ.get('NUM_SWITCHES', 'Unknown'),
    'num_publishers': os.environ.get('NUM_PUBLISHERS', 'Unknown'),
}

class MetricsCollector:
    def __init__(self):
        self.delays = {'anomaly': [], 'normal': []}
        # Per-device tracking for correct packet loss calculation AND per-sensor metrics
        self.device_data = defaultdict(lambda: {
            'type': None,
            'received_seq': set(),
            'min_seq': float('inf'),
            'max_seq': -1,
            'delays': []  # Track delays per device for per-sensor metrics
        })
        self.first_timestamp = None
        self.last_timestamp = None
        self.message_count = 0
        self.prev_delay = {'anomaly': None, 'normal': None}
        self.jitter_values = {'anomaly': [], 'normal': []}

    def update(self, msg_type, delay, seq, timestamp, device):
        self.delays[msg_type].append(delay)
        self.message_count += 1

        # Per-device sequence and delay tracking
        self.device_data[device]['type'] = msg_type
        self.device_data[device]['received_seq'].add(seq)
        self.device_data[device]['delays'].append(delay)
        if seq < self.device_data[device]['min_seq']:
            self.device_data[device]['min_seq'] = seq
        if seq > self.device_data[device]['max_seq']:
            self.device_data[device]['max_seq'] = seq

        # Calculate jitter
        if self.prev_delay[msg_type] is not None:
            jitter = abs(delay - self.prev_delay[msg_type])
            self.jitter_values[msg_type].append(jitter)
        self.prev_delay[msg_type] = delay

        if self.first_timestamp is None:
            self.first_timestamp = timestamp
        self.last_timestamp = timestamp

    def calculate_avg_jitter(self, msg_type):
        if len(self.jitter_values[msg_type]) == 0:
            return 0
        return sum(self.jitter_values[msg_type]) / len(self.jitter_values[msg_type])

    def calculate_loss_rate(self, msg_type):
        """Calculate packet loss per-device then aggregate by message type
        
        Uses range-based calculation: expected = max_seq - min_seq + 1
        This correctly handles cases where sequence doesn't start from 0.
        """
        loss_by_type = []
        total_expected = 0
        total_received = 0
        total_lost = 0
        num_devices = 0

        for device, data in self.device_data.items():
            if data['type'] == msg_type:
                num_devices += 1
                min_seq = data['min_seq']
                max_seq = data['max_seq']
                
                if max_seq < 0 or min_seq == float('inf'):
                    continue

                # Correct formula: only count the range we actually saw
                expected = max_seq - min_seq + 1
                received = len(data['received_seq'])
                lost = expected - received
                loss_rate = (lost / expected * 100) if expected > 0 else 0

                loss_by_type.append(loss_rate)
                total_expected += expected
                total_received += received
                total_lost += lost

        # Calculate aggregate loss rate
        aggregate_loss_rate = (total_lost / total_expected * 100) if total_expected > 0 else 0
        avg_loss_per_device = (sum(loss_by_type) / len(loss_by_type)) if loss_by_type else 0

        return {
            'num_devices': num_devices,
            'expected': total_expected,
            'received': total_received,
            'lost': total_lost,
            'loss_rate': aggregate_loss_rate,
            'avg_loss_per_device': avg_loss_per_device
        }

    def get_summary(self):
        total_time = self.last_timestamp - self.first_timestamp if self.first_timestamp else 0

        summary = {}
        for msg_type in ['anomaly', 'normal']:
            delays = self.delays[msg_type]
            loss_info = self.calculate_loss_rate(msg_type)

            if len(delays) > 0:
                summary[msg_type] = {
                    'count': len(delays),
                    'avg_delay': sum(delays) / len(delays),
                    'min_delay': min(delays),
                    'max_delay': max(delays),
                    'std_delay': (sum((x - sum(delays)/len(delays))**2 for x in delays) / len(delays))**0.5 if len(delays) > 1 else 0,
                    'avg_jitter': self.calculate_avg_jitter(msg_type),
                    'num_devices': loss_info['num_devices'],
                    'loss_info': loss_info
                }
            else:
                summary[msg_type] = None

        summary['total'] = {
            'duration': total_time,
            'total_messages': self.message_count,
            'throughput': self.message_count / total_time if total_time > 0 else 0
        }

        return summary

    def get_per_sensor_metrics(self):
        """Get per-sensor metrics sorted by highest average delay"""
        sensor_metrics = []
        
        for device, data in self.device_data.items():
            if not data['delays']:
                continue
                
            delays = data['delays']
            min_seq = data['min_seq']
            max_seq = data['max_seq']
            
            # Calculate packet loss
            if max_seq >= 0 and min_seq != float('inf'):
                expected = max_seq - min_seq + 1
                received = len(data['received_seq'])
                lost = expected - received
                loss_rate = (lost / expected * 100) if expected > 0 else 0
            else:
                expected = received = lost = 0
                loss_rate = 0
            
            avg_delay = sum(delays) / len(delays)
            
            sensor_metrics.append({
                'device': device,
                'type': data['type'],
                'avg_delay': avg_delay,
                'min_delay': min(delays),
                'max_delay': max(delays),
                'count': len(delays),
                'expected': expected,
                'lost': lost,
                'loss_rate': loss_rate
            })
        
        # Sort by highest average delay
        sensor_metrics.sort(key=lambda x: x['avg_delay'], reverse=True)
        return sensor_metrics

    def get_per_floor_metrics(self):
        """Get per-floor aggregated metrics"""
        floor_data = defaultdict(lambda: {
            'anomaly': {'delays': [], 'received': 0, 'expected': 0, 'lost': 0},
            'normal': {'delays': [], 'received': 0, 'expected': 0, 'lost': 0}
        })
        
        for device, data in self.device_data.items():
            if not data['delays']:
                continue
            
            # Extract floor from device name (e.g., sensor_f1r1_anomaly -> floor 1)
            try:
                floor = device.split('_')[1][1]  # Get 'f1' -> '1'
            except:
                floor = '?'
            
            msg_type = data['type']
            min_seq = data['min_seq']
            max_seq = data['max_seq']
            
            if max_seq >= 0 and min_seq != float('inf'):
                expected = max_seq - min_seq + 1
                received = len(data['received_seq'])
                lost = expected - received
            else:
                expected = received = lost = 0
            
            floor_data[floor][msg_type]['delays'].extend(data['delays'])
            floor_data[floor][msg_type]['received'] += received
            floor_data[floor][msg_type]['expected'] += expected
            floor_data[floor][msg_type]['lost'] += lost
        
        # Calculate averages
        result = {}
        for floor in sorted(floor_data.keys()):
            result[floor] = {}
            for msg_type in ['anomaly', 'normal']:
                fd = floor_data[floor][msg_type]
                if fd['delays']:
                    loss_rate = (fd['lost'] / fd['expected'] * 100) if fd['expected'] > 0 else 0
                    result[floor][msg_type] = {
                        'avg_delay': sum(fd['delays']) / len(fd['delays']),
                        'count': len(fd['delays']),
                        'loss_rate': loss_rate
                    }
                else:
                    result[floor][msg_type] = None
        
        return result

metrics = MetricsCollector()

# CSV Header
with open(LOG_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["device", "type", "value", "seq", "timestamp_sent", "delay_ms"])

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        recv_time = time.time()
        delay = (recv_time - data["timestamp"]) * 1000  # ms

        # Update metrics (now includes device parameter)
        metrics.update(data['type'], delay, data['seq'], data['timestamp'], data['device'])

        # Log to CSV
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                data["device"],
                data["type"],
                data["value"],
                data["seq"],
                data["timestamp"],
                delay
            ])

        print(f"[{data['type']:7s}] seq={data['seq']:4d} delay={delay:5.2f}ms")

    except Exception as e:
        print(f"Error processing message: {e}")

def cleanup(signal_num=None, frame=None):
    print("\n\n" + "=" * 70)
    print(" " * 20 + "SIMULATION SUMMARY")
    print("=" * 70)

    # Print configuration
    print("\nCONFIGURATION:")
    print(f"  Scenario          : {CONFIG['scenario']}")
    print(f"  Topology          : {CONFIG['topology']}")
    print(f"  Switches          : {CONFIG['num_switches']}")
    print(f"  Publishers        : {CONFIG['num_publishers']}")
    print(f"  Bandwidth Limit   : {CONFIG['bandwidth_limit_enabled']}")
    if CONFIG['bandwidth_limit_enabled'].lower() == 'true':
        try:
            bw_mbps = float(CONFIG['bandwidth_mbps'])
            bw_kbps = bw_mbps * 1000
            print(f"  Bandwidth         : {bw_mbps} Mbps ({bw_kbps:.0f} Kbps)")
        except:
            print(f"  Bandwidth         : {CONFIG['bandwidth_mbps']} Mbps")
    print(f"  QoS Queues        : {CONFIG['qos_queues_enabled']}")

    summary = metrics.get_summary()

    # Print to console
    for msg_type in ['anomaly', 'normal']:
        if summary[msg_type]:
            s = summary[msg_type]
            loss = s['loss_info']

            print(f"\n{msg_type.upper()}:")
            print(f"  Devices           : {s['num_devices']}")
            print(f"  Messages Received : {s['count']}")
            print(f"  Avg Delay         : {s['avg_delay']:.2f} ms")
            print(f"  Min Delay         : {s['min_delay']:.2f} ms")
            print(f"  Max Delay         : {s['max_delay']:.2f} ms")
            print(f"  Std Dev Delay     : {s['std_delay']:.2f} ms")
            print(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms")
            print(f"\n  PACKET LOSS:")
            print(f"    Expected        : {loss['expected']} messages")
            print(f"    Received        : {loss['received']} messages")
            print(f"    Lost            : {loss['lost']} messages")
            print(f"    Loss Rate       : {loss['loss_rate']:.2f}%")
            print(f"    Avg Loss/Device : {loss['avg_loss_per_device']:.2f}%")

    print(f"\nTOTAL:")
    print(f"  Duration          : {summary['total']['duration']:.2f} s")
    print(f"  Total Messages    : {summary['total']['total_messages']}")
    print(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s")

    # Get per-sensor and per-floor metrics
    sensor_metrics = metrics.get_per_sensor_metrics()
    floor_metrics = metrics.get_per_floor_metrics()

    # Print per-sensor metrics (top 10 highest delay)
    print("\n" + "=" * 70)
    print(" " * 15 + "PER-SENSOR METRICS (Top 10 by Delay)")
    print("=" * 70)
    print(f"{'Device':<35} {'Type':<8} {'Avg Delay':>12} {'Count':>8} {'Loss%':>8}")
    print("-" * 70)
    for s in sensor_metrics[:10]:
        print(f"{s['device']:<35} {s['type']:<8} {s['avg_delay']:>10.2f}ms {s['count']:>8} {s['loss_rate']:>7.2f}%")

    # Print per-floor metrics
    print("\n" + "=" * 70)
    print(" " * 20 + "PER-FLOOR SUMMARY")
    print("=" * 70)
    print(f"{'Floor':<8} {'Type':<10} {'Avg Delay':>12} {'Count':>8} {'Loss%':>8}")
    print("-" * 70)
    for floor, data in floor_metrics.items():
        for msg_type in ['anomaly', 'normal']:
            if data.get(msg_type):
                m = data[msg_type]
                print(f"Floor {floor:<3} {msg_type:<10} {m['avg_delay']:>10.2f}ms {m['count']:>8} {m['loss_rate']:>7.2f}%")

    # Calculate QoS improvement
    if summary['anomaly'] and summary['normal']:
        anomaly_delay = summary['anomaly']['avg_delay']
        normal_delay = summary['normal']['avg_delay']
        if normal_delay > 0:
            improvement = (normal_delay - anomaly_delay) / normal_delay * 100
            print("\n" + "=" * 70)
            print(f"  QoS IMPROVEMENT: {improvement:.1f}% lower delay for anomaly traffic")
            print("=" * 70)

    # Save to file
    with open(SUMMARY_FILE, "w") as f:
        f.write("=" * 70 + "\n")
        f.write(" " * 20 + "SIMULATION SUMMARY\n")
        f.write("=" * 70 + "\n\n")

        # Write configuration
        f.write("CONFIGURATION:\n")
        f.write(f"  Scenario          : {CONFIG['scenario']}\n")
        f.write(f"  Topology          : {CONFIG['topology']}\n")
        f.write(f"  Switches          : {CONFIG['num_switches']}\n")
        f.write(f"  Publishers        : {CONFIG['num_publishers']}\n")
        f.write(f"  Bandwidth Limit   : {CONFIG['bandwidth_limit_enabled']}\n")
        if CONFIG['bandwidth_limit_enabled'].lower() == 'true':
            try:
                bw_mbps = float(CONFIG['bandwidth_mbps'])
                bw_kbps = bw_mbps * 1000
                f.write(f"  Bandwidth         : {bw_mbps} Mbps ({bw_kbps:.0f} Kbps)\n")
            except:
                f.write(f"  Bandwidth         : {CONFIG['bandwidth_mbps']} Mbps\n")
        f.write(f"  QoS Queues        : {CONFIG['qos_queues_enabled']}\n")
        f.write("\n" + "=" * 70 + "\n\n")

        for msg_type in ['anomaly', 'normal']:
            if summary[msg_type]:
                s = summary[msg_type]
                loss = s['loss_info']

                f.write(f"{msg_type.upper()}:\n")
                f.write(f"  Devices           : {s['num_devices']}\n")
                f.write(f"  Messages Received : {s['count']}\n")
                f.write(f"  Avg Delay         : {s['avg_delay']:.2f} ms\n")
                f.write(f"  Min Delay         : {s['min_delay']:.2f} ms\n")
                f.write(f"  Max Delay         : {s['max_delay']:.2f} ms\n")
                f.write(f"  Std Dev Delay     : {s['std_delay']:.2f} ms\n")
                f.write(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms\n")
                f.write(f"\n  PACKET LOSS:\n")
                f.write(f"    Expected        : {loss['expected']} messages\n")
                f.write(f"    Received        : {loss['received']} messages\n")
                f.write(f"    Lost            : {loss['lost']} messages\n")
                f.write(f"    Loss Rate       : {loss['loss_rate']:.2f}%\n")
                f.write(f"    Avg Loss/Device : {loss['avg_loss_per_device']:.2f}%\n")
                f.write("\n")

        f.write(f"TOTAL:\n")
        f.write(f"  Duration          : {summary['total']['duration']:.2f} s\n")
        f.write(f"  Total Messages    : {summary['total']['total_messages']}\n")
        f.write(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s\n")

        # Write per-sensor metrics
        f.write("\n" + "=" * 70 + "\n")
        f.write(" " * 15 + "PER-SENSOR METRICS (Sorted by Delay)\n")
        f.write("=" * 70 + "\n")
        f.write(f"{'Device':<35} {'Type':<8} {'Avg Delay':>12} {'Count':>8} {'Loss%':>8}\n")
        f.write("-" * 70 + "\n")
        for s in sensor_metrics:
            f.write(f"{s['device']:<35} {s['type']:<8} {s['avg_delay']:>10.2f}ms {s['count']:>8} {s['loss_rate']:>7.2f}%\n")

        # Write per-floor metrics
        f.write("\n" + "=" * 70 + "\n")
        f.write(" " * 20 + "PER-FLOOR SUMMARY\n")
        f.write("=" * 70 + "\n")
        f.write(f"{'Floor':<8} {'Type':<10} {'Avg Delay':>12} {'Count':>8} {'Loss%':>8}\n")
        f.write("-" * 70 + "\n")
        for floor, data in floor_metrics.items():
            for msg_type in ['anomaly', 'normal']:
                if data.get(msg_type):
                    m = data[msg_type]
                    f.write(f"Floor {floor:<3} {msg_type:<10} {m['avg_delay']:>10.2f}ms {m['count']:>8} {m['loss_rate']:>7.2f}%\n")

        # Write QoS improvement
        if summary['anomaly'] and summary['normal']:
            anomaly_delay = summary['anomaly']['avg_delay']
            normal_delay = summary['normal']['avg_delay']
            if normal_delay > 0:
                improvement = (normal_delay - anomaly_delay) / normal_delay * 100
                f.write("\n" + "=" * 70 + "\n")
                f.write(f"  QoS IMPROVEMENT: {improvement:.1f}% lower delay for anomaly traffic\n")
                f.write("=" * 70 + "\n")

    print(f"\n" + "=" * 70)
    print(f"Metrics saved to:")
    print(f"  - CSV Data  : {os.path.abspath(LOG_FILE)}")
    print(f"  - Summary   : {os.path.abspath(SUMMARY_FILE)}")
    print("=" * 70 + "\n")

    sys.exit(0)

# Setup signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# MQTT Client setup
client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("iot/data")

print("=" * 70)
print(" " * 15 + "ENHANCED SUBSCRIBER STARTED")
print("=" * 70)
print("Collecting metrics:")
print("  - End-to-End Delay")
print("  - Jitter")
print("  - Packet Loss Rate")
print("  - Throughput")
print("\nPress Ctrl+C to stop and view summary.")
print("=" * 70 + "\n")

try:
    client.loop_forever()
except KeyboardInterrupt:
    cleanup()
