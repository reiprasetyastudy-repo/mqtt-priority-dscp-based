#!/usr/bin/env python3
"""
Enhanced Subscriber with Phase Tracking for Link Failure Test (Scenario 10)

Tracks metrics separately for:
- Phase 1: Normal operation (before link failure)
- Phase 2: Link down (after link failure)

This allows comparison of QoS performance before/after link failure.
"""

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
    'scenario': os.environ.get('SCENARIO_NAME', '10-dscp-qos-13switches-linkfailure'),
    'topology': os.environ.get('TOPOLOGY_TYPE', 'DSCP Ring with Link Failure'),
    'num_switches': os.environ.get('NUM_SWITCHES', '13'),
    'num_publishers': os.environ.get('NUM_PUBLISHERS', '18'),
    'phase1_duration': int(os.environ.get('PHASE1_DURATION', '30')),
}


class PhaseMetricsCollector:
    """Collects metrics separately for each phase"""
    
    def __init__(self, phase1_duration):
        self.phase1_duration = phase1_duration
        self.start_time = None
        self.link_failure_time = None
        
        # Metrics per phase: phase1 (normal), phase2 (link_down)
        self.delays = {
            'phase1': {'anomaly': [], 'normal': []},
            'phase2': {'anomaly': [], 'normal': []}
        }
        
        # Per-device tracking per phase (with min_seq for correct packet loss calc)
        self.device_data = {
            'phase1': defaultdict(lambda: {'type': None, 'received_seq': set(), 'min_seq': float('inf'), 'max_seq': -1}),
            'phase2': defaultdict(lambda: {'type': None, 'received_seq': set(), 'min_seq': float('inf'), 'max_seq': -1})
        }
        
        # Timestamps
        self.first_timestamp = {'phase1': None, 'phase2': None}
        self.last_timestamp = {'phase1': None, 'phase2': None}
        self.message_count = {'phase1': 0, 'phase2': 0}
        
        # Jitter tracking
        self.prev_delay = {
            'phase1': {'anomaly': None, 'normal': None},
            'phase2': {'anomaly': None, 'normal': None}
        }
        self.jitter_values = {
            'phase1': {'anomaly': [], 'normal': []},
            'phase2': {'anomaly': [], 'normal': []}
        }
    
    def get_current_phase(self):
        """Determine current phase based on elapsed time"""
        if self.start_time is None:
            self.start_time = time.time()
        
        elapsed = time.time() - self.start_time
        
        if elapsed < self.phase1_duration:
            return 'phase1'
        else:
            if self.link_failure_time is None:
                self.link_failure_time = time.time()
                print(f"\n{'='*70}")
                print(f"  PHASE TRANSITION: Link Failure Occurred!")
                print(f"  Time: {elapsed:.1f}s - Switching to Phase 2 (Link Down)")
                print(f"{'='*70}\n")
            return 'phase2'
    
    def update(self, msg_type, delay, seq, timestamp, device):
        phase = self.get_current_phase()
        
        self.delays[phase][msg_type].append(delay)
        self.message_count[phase] += 1
        
        # Per-device sequence tracking
        self.device_data[phase][device]['type'] = msg_type
        self.device_data[phase][device]['received_seq'].add(seq)
        if seq < self.device_data[phase][device]['min_seq']:
            self.device_data[phase][device]['min_seq'] = seq
        if seq > self.device_data[phase][device]['max_seq']:
            self.device_data[phase][device]['max_seq'] = seq
        
        # Calculate jitter
        if self.prev_delay[phase][msg_type] is not None:
            jitter = abs(delay - self.prev_delay[phase][msg_type])
            self.jitter_values[phase][msg_type].append(jitter)
        self.prev_delay[phase][msg_type] = delay
        
        # Track timestamps per phase
        if self.first_timestamp[phase] is None:
            self.first_timestamp[phase] = timestamp
        self.last_timestamp[phase] = timestamp
        
        return phase
    
    def calculate_avg_jitter(self, phase, msg_type):
        if len(self.jitter_values[phase][msg_type]) == 0:
            return 0
        return sum(self.jitter_values[phase][msg_type]) / len(self.jitter_values[phase][msg_type])
    
    def calculate_loss_rate(self, phase, msg_type):
        """Calculate packet loss per-device for a specific phase
        
        Uses range-based calculation: expected = max_seq - min_seq + 1
        This correctly handles per-phase packet loss without counting
        sequences from other phases.
        """
        total_expected = 0
        total_received = 0
        total_lost = 0
        num_devices = 0
        loss_rates = []
        
        for device, data in self.device_data[phase].items():
            if data['type'] == msg_type:
                num_devices += 1
                min_seq = data['min_seq']
                max_seq = data['max_seq']
                
                if max_seq < 0 or min_seq == float('inf'):
                    continue
                
                # Correct formula: only count the range within this phase
                expected = max_seq - min_seq + 1
                received = len(data['received_seq'])
                lost = expected - received
                loss_rate = (lost / expected * 100) if expected > 0 else 0
                
                loss_rates.append(loss_rate)
                total_expected += expected
                total_received += received
                total_lost += lost
        
        aggregate_loss_rate = (total_lost / total_expected * 100) if total_expected > 0 else 0
        avg_loss_per_device = (sum(loss_rates) / len(loss_rates)) if loss_rates else 0
        
        return {
            'num_devices': num_devices,
            'expected': total_expected,
            'received': total_received,
            'lost': total_lost,
            'loss_rate': aggregate_loss_rate,
            'avg_loss_per_device': avg_loss_per_device
        }
    
    def get_phase_summary(self, phase):
        """Get summary for a specific phase"""
        first_ts = self.first_timestamp[phase]
        last_ts = self.last_timestamp[phase]
        total_time = last_ts - first_ts if first_ts and last_ts else 0
        
        summary = {}
        for msg_type in ['anomaly', 'normal']:
            delays = self.delays[phase][msg_type]
            loss_info = self.calculate_loss_rate(phase, msg_type)
            
            if len(delays) > 0:
                avg_delay = sum(delays) / len(delays)
                summary[msg_type] = {
                    'count': len(delays),
                    'avg_delay': avg_delay,
                    'min_delay': min(delays),
                    'max_delay': max(delays),
                    'std_delay': (sum((x - avg_delay)**2 for x in delays) / len(delays))**0.5,
                    'avg_jitter': self.calculate_avg_jitter(phase, msg_type),
                    'num_devices': loss_info['num_devices'],
                    'loss_info': loss_info
                }
            else:
                summary[msg_type] = None
        
        summary['total'] = {
            'duration': total_time,
            'total_messages': self.message_count[phase],
            'throughput': self.message_count[phase] / total_time if total_time > 0 else 0
        }
        
        return summary
    
    def get_full_summary(self):
        """Get summary for both phases"""
        return {
            'phase1': self.get_phase_summary('phase1'),
            'phase2': self.get_phase_summary('phase2'),
            'config': CONFIG
        }


# Initialize collector with phase1 duration
metrics = PhaseMetricsCollector(CONFIG['phase1_duration'])

# CSV Header with phase column
with open(LOG_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["device", "type", "value", "seq", "timestamp_sent", "delay_ms", "phase"])


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        recv_time = time.time()
        delay = (recv_time - data["timestamp"]) * 1000  # ms
        
        # Update metrics and get current phase
        phase = metrics.update(data['type'], delay, data['seq'], data['timestamp'], data['device'])
        
        # Log to CSV with phase
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                data["device"],
                data["type"],
                data["value"],
                data["seq"],
                data["timestamp"],
                delay,
                phase
            ])
        
        phase_label = "NORMAL" if phase == "phase1" else "LINK_DOWN"
        print(f"[{phase_label:9s}] [{data['type']:7s}] seq={data['seq']:4d} delay={delay:5.2f}ms")
    
    except Exception as e:
        print(f"Error processing message: {e}")


def print_phase_summary(f, phase_name, phase_label, summary):
    """Print summary for a phase to file and console"""
    header = f"\n{'='*70}\n  {phase_label}\n{'='*70}\n"
    print(header)
    f.write(header)
    
    for msg_type in ['anomaly', 'normal']:
        if summary[msg_type]:
            s = summary[msg_type]
            loss = s['loss_info']
            
            output = f"""
{msg_type.upper()}:
  Devices           : {s['num_devices']}
  Messages Received : {s['count']}
  Avg Delay         : {s['avg_delay']:.2f} ms
  Min Delay         : {s['min_delay']:.2f} ms
  Max Delay         : {s['max_delay']:.2f} ms
  Std Dev Delay     : {s['std_delay']:.2f} ms
  Avg Jitter        : {s['avg_jitter']:.2f} ms

  PACKET LOSS:
    Expected        : {loss['expected']} messages
    Received        : {loss['received']} messages
    Lost            : {loss['lost']} messages
    Loss Rate       : {loss['loss_rate']:.2f}%
"""
            print(output)
            f.write(output)
    
    total = summary['total']
    total_output = f"""
PHASE TOTAL:
  Duration          : {total['duration']:.2f} s
  Total Messages    : {total['total_messages']}
  Throughput        : {total['throughput']:.2f} msg/s
"""
    print(total_output)
    f.write(total_output)


def cleanup(signal_num=None, frame=None):
    full_summary = metrics.get_full_summary()
    
    with open(SUMMARY_FILE, "w") as f:
        # Header
        header = f"""
{'='*70}
  LINK FAILURE TEST - SIMULATION SUMMARY
  Scenario 10: DSCP QoS with Ring Topology + Link Failure
{'='*70}

CONFIGURATION:
  Scenario          : {CONFIG['scenario']}
  Topology          : {CONFIG['topology']}
  Switches          : {CONFIG['num_switches']}
  Publishers        : {CONFIG['num_publishers']}
  Bandwidth Limit   : {CONFIG['bandwidth_limit_enabled']}
  Bandwidth         : {CONFIG['bandwidth_mbps']} Mbps
  QoS Queues        : {CONFIG['qos_queues_enabled']}
  Phase 1 Duration  : {CONFIG['phase1_duration']} seconds

TEST PHASES:
  Phase 1 (0-{CONFIG['phase1_duration']}s)  : Normal operation - all links active
  Phase 2 ({CONFIG['phase1_duration']}s+)   : Link s2↔s1 DOWN - traffic via ring
"""
        print(header)
        f.write(header)
        
        # Phase 1 Summary
        print_phase_summary(f, 'phase1', 
                           f"PHASE 1: NORMAL OPERATION (0-{CONFIG['phase1_duration']}s)", 
                           full_summary['phase1'])
        
        # Phase 2 Summary
        print_phase_summary(f, 'phase2', 
                           f"PHASE 2: LINK DOWN ({CONFIG['phase1_duration']}s+)", 
                           full_summary['phase2'])
        
        # Comparison
        comparison = f"""
{'='*70}
  PHASE COMPARISON (Impact of Link Failure)
{'='*70}
"""
        print(comparison)
        f.write(comparison)
        
        for msg_type in ['anomaly', 'normal']:
            p1 = full_summary['phase1'].get(msg_type)
            p2 = full_summary['phase2'].get(msg_type)
            
            if p1 and p2:
                delay_diff = p2['avg_delay'] - p1['avg_delay']
                delay_pct = (delay_diff / p1['avg_delay'] * 100) if p1['avg_delay'] > 0 else 0
                
                comp_output = f"""
{msg_type.upper()}:
  Phase 1 Avg Delay : {p1['avg_delay']:.2f} ms
  Phase 2 Avg Delay : {p2['avg_delay']:.2f} ms
  Delay Increase    : {delay_diff:+.2f} ms ({delay_pct:+.1f}%)
  
  Phase 1 Loss Rate : {p1['loss_info']['loss_rate']:.2f}%
  Phase 2 Loss Rate : {p2['loss_info']['loss_rate']:.2f}%
"""
                print(comp_output)
                f.write(comp_output)
        
        # Redundancy verdict
        p2_anomaly = full_summary['phase2'].get('anomaly')
        p2_normal = full_summary['phase2'].get('normal')
        
        if p2_anomaly or p2_normal:
            total_p2_messages = full_summary['phase2']['total']['total_messages']
            verdict = f"""
{'='*70}
  REDUNDANCY VERDICT
{'='*70}

  Phase 2 Messages Received: {total_p2_messages}
  
"""
            if total_p2_messages > 0:
                verdict += "  ✓ REDUNDANCY WORKS! Traffic successfully rerouted via ring.\n"
                verdict += "    Link failure did NOT cause complete network outage.\n"
            else:
                verdict += "  ✗ REDUNDANCY FAILED! No messages received after link failure.\n"
            
            print(verdict)
            f.write(verdict)
        
        footer = f"""
{'='*70}
Metrics saved to:
  - CSV Data  : {os.path.abspath(LOG_FILE)}
  - Summary   : {os.path.abspath(SUMMARY_FILE)}
{'='*70}
"""
        print(footer)
        f.write(footer)
    
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
print(" " * 10 + "LINK FAILURE TEST SUBSCRIBER STARTED")
print("=" * 70)
print(f"\nPhase 1 Duration: {CONFIG['phase1_duration']} seconds (Normal Operation)")
print(f"Phase 2 Start   : After {CONFIG['phase1_duration']}s (Link Down)")
print("\nCollecting metrics per phase:")
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
