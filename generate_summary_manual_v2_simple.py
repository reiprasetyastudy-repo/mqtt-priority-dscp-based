#!/usr/bin/env python3
"""
Manual Summary Generator v2 - Simple version with CSV export for Excel

Usage:
    python3 generate_summary_manual_v2_simple.py <path_to_mqtt_metrics_log.csv>

Example:
    python3 generate_summary_manual_v2_simple.py /home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-24_13-36-51/mqtt_metrics_log.csv
"""

import sys
import csv
import os
from statistics import mean, stdev
from collections import defaultdict

def calculate_summary(csv_file):
    """Calculate metrics summary from CSV file with per-device packet loss"""

    # Per-type aggregated metrics
    delays = {'anomaly': [], 'normal': []}
    jitter_values = {'anomaly': [], 'normal': []}
    prev_delay = {'anomaly': None, 'normal': None}

    # Per-device tracking for packet loss
    device_data = defaultdict(lambda: {
        'type': None,
        'received_seq': set(),
        'max_seq': -1
    })

    message_count = 0
    first_timestamp = None
    last_timestamp = None

    print(f"Reading CSV: {csv_file}")
    print("Processing messages...")

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            device = row['device']
            msg_type = row['type']
            delay = float(row['delay_ms'])
            seq = int(row['seq'])
            timestamp = float(row['timestamp_sent'])

            # Aggregate delay
            delays[msg_type].append(delay)
            message_count += 1

            # Calculate jitter
            if prev_delay[msg_type] is not None:
                jitter = abs(delay - prev_delay[msg_type])
                jitter_values[msg_type].append(jitter)
            prev_delay[msg_type] = delay

            # Per-device sequence tracking
            device_data[device]['type'] = msg_type
            device_data[device]['received_seq'].add(seq)
            if seq > device_data[device]['max_seq']:
                device_data[device]['max_seq'] = seq

            if first_timestamp is None:
                first_timestamp = timestamp
            last_timestamp = timestamp

            if message_count % 10000 == 0:
                print(f"  Processed {message_count} messages...")

    print(f"Total messages processed: {message_count}")
    print(f"Total unique devices: {len(device_data)}")

    # Calculate per-device packet loss, then aggregate by type
    loss_by_type = {'anomaly': [], 'normal': []}
    total_expected_by_type = {'anomaly': 0, 'normal': 0}
    total_received_by_type = {'anomaly': 0, 'normal': 0}
    total_lost_by_type = {'anomaly': 0, 'normal': 0}

    print("\nPer-device packet loss:")
    for device, data in sorted(device_data.items()):
        msg_type = data['type']
        max_seq = data['max_seq']
        expected = max_seq + 1  # seq starts from 0
        received = len(data['received_seq'])
        lost = expected - received
        loss_rate = (lost / expected * 100) if expected > 0 else 0

        loss_by_type[msg_type].append(loss_rate)
        total_expected_by_type[msg_type] += expected
        total_received_by_type[msg_type] += received
        total_lost_by_type[msg_type] += lost

        if loss_rate > 0:  # Only print devices with packet loss
            print(f"  {device:30s} ({msg_type:7s}): {received:5d}/{expected:5d} ({loss_rate:5.2f}% loss)")

    # Calculate summary
    duration = last_timestamp - first_timestamp if first_timestamp and last_timestamp else 0

    summary = {}
    for msg_type in ['anomaly', 'normal']:
        if delays[msg_type]:
            # Aggregate packet loss rate
            avg_loss_rate = mean(loss_by_type[msg_type]) if loss_by_type[msg_type] else 0

            summary[msg_type] = {
                'count': len(delays[msg_type]),
                'avg_delay': mean(delays[msg_type]),
                'min_delay': min(delays[msg_type]),
                'max_delay': max(delays[msg_type]),
                'std_delay': stdev(delays[msg_type]) if len(delays[msg_type]) > 1 else 0,
                'avg_jitter': mean(jitter_values[msg_type]) if jitter_values[msg_type] else 0,
                'num_devices': len([d for d, info in device_data.items() if info['type'] == msg_type]),
                'expected': total_expected_by_type[msg_type],
                'received': total_received_by_type[msg_type],
                'lost': total_lost_by_type[msg_type],
                'loss_rate': (total_lost_by_type[msg_type] / total_expected_by_type[msg_type] * 100)
                            if total_expected_by_type[msg_type] > 0 else 0,
                'avg_loss_per_device': avg_loss_rate
            }

    summary['total'] = {
        'duration': duration,
        'total_messages': message_count,
        'throughput': message_count / duration if duration > 0 else 0
    }

    return summary

def print_summary(summary):
    """Print summary to console"""
    print("\n" + "=" * 70)
    print(" " * 20 + "SIMULATION SUMMARY")
    print("=" * 70 + "\n")

    for msg_type in ['anomaly', 'normal']:
        if msg_type in summary and summary[msg_type]:
            s = summary[msg_type]
            print(f"{msg_type.upper()}:")
            print(f"  Devices           : {s['num_devices']}")
            print(f"  Messages Received : {s['count']}")
            print(f"  Avg Delay         : {s['avg_delay']:.2f} ms")
            print(f"  Min Delay         : {s['min_delay']:.2f} ms")
            print(f"  Max Delay         : {s['max_delay']:.2f} ms")
            print(f"  Std Dev Delay     : {s['std_delay']:.2f} ms")
            print(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms")
            print(f"\n  PACKET LOSS:")
            print(f"    Expected        : {s['expected']} messages")
            print(f"    Received        : {s['received']} messages")
            print(f"    Lost            : {s['lost']} messages")
            print(f"    Loss Rate       : {s['loss_rate']:.2f}%")
            print(f"    Avg Loss/Device : {s['avg_loss_per_device']:.2f}%")
            print()

    print(f"TOTAL:")
    print(f"  Duration          : {summary['total']['duration']:.2f} s")
    print(f"  Total Messages    : {summary['total']['total_messages']}")
    print(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s")
    print()

def save_summary(summary, output_file):
    """Save summary to file"""
    with open(output_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write(" " * 20 + "SIMULATION SUMMARY\n")
        f.write("=" * 70 + "\n\n")

        for msg_type in ['anomaly', 'normal']:
            if msg_type in summary and summary[msg_type]:
                s = summary[msg_type]
                f.write(f"{msg_type.upper()}:\n")
                f.write(f"  Devices           : {s['num_devices']}\n")
                f.write(f"  Messages Received : {s['count']}\n")
                f.write(f"  Avg Delay         : {s['avg_delay']:.2f} ms\n")
                f.write(f"  Min Delay         : {s['min_delay']:.2f} ms\n")
                f.write(f"  Max Delay         : {s['max_delay']:.2f} ms\n")
                f.write(f"  Std Dev Delay     : {s['std_delay']:.2f} ms\n")
                f.write(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms\n")
                f.write(f"\n  PACKET LOSS:\n")
                f.write(f"    Expected        : {s['expected']} messages\n")
                f.write(f"    Received        : {s['received']} messages\n")
                f.write(f"    Lost            : {s['lost']} messages\n")
                f.write(f"    Loss Rate       : {s['loss_rate']:.2f}%\n")
                f.write(f"    Avg Loss/Device : {s['avg_loss_per_device']:.2f}%\n")
                f.write("\n")

        f.write(f"TOTAL:\n")
        f.write(f"  Duration          : {summary['total']['duration']:.2f} s\n")
        f.write(f"  Total Messages    : {summary['total']['total_messages']}\n")
        f.write(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s\n")

    print(f"Text summary saved to: {output_file}")

def save_summary_csv(summary, output_file):
    """Save summary to CSV file (Excel-compatible)"""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Title
        writer.writerow(['MQTT-SDN METRICS SUMMARY'])
        writer.writerow([])

        # Anomaly Section
        if 'anomaly' in summary and summary['anomaly']:
            s = summary['anomaly']
            writer.writerow(['ANOMALY TRAFFIC'])
            writer.writerow(['Metric', 'Value', 'Unit'])
            writer.writerow(['Devices', s['num_devices'], ''])
            writer.writerow(['Messages Received', s['count'], 'messages'])
            writer.writerow(['Avg Delay', f"{s['avg_delay']:.2f}", 'ms'])
            writer.writerow(['Min Delay', f"{s['min_delay']:.2f}", 'ms'])
            writer.writerow(['Max Delay', f"{s['max_delay']:.2f}", 'ms'])
            writer.writerow(['Std Dev Delay', f"{s['std_delay']:.2f}", 'ms'])
            writer.writerow(['Avg Jitter', f"{s['avg_jitter']:.2f}", 'ms'])
            writer.writerow([])
            writer.writerow(['PACKET LOSS'])
            writer.writerow(['Expected', s['expected'], 'messages'])
            writer.writerow(['Received', s['received'], 'messages'])
            writer.writerow(['Lost', s['lost'], 'messages'])
            writer.writerow(['Loss Rate', f"{s['loss_rate']:.2f}", '%'])
            writer.writerow(['Avg Loss/Device', f"{s['avg_loss_per_device']:.2f}", '%'])
            writer.writerow([])

        # Normal Section
        if 'normal' in summary and summary['normal']:
            s = summary['normal']
            writer.writerow(['NORMAL TRAFFIC'])
            writer.writerow(['Metric', 'Value', 'Unit'])
            writer.writerow(['Devices', s['num_devices'], ''])
            writer.writerow(['Messages Received', s['count'], 'messages'])
            writer.writerow(['Avg Delay', f"{s['avg_delay']:.2f}", 'ms'])
            writer.writerow(['Min Delay', f"{s['min_delay']:.2f}", 'ms'])
            writer.writerow(['Max Delay', f"{s['max_delay']:.2f}", 'ms'])
            writer.writerow(['Std Dev Delay', f"{s['std_delay']:.2f}", 'ms'])
            writer.writerow(['Avg Jitter', f"{s['avg_jitter']:.2f}", 'ms'])
            writer.writerow([])
            writer.writerow(['PACKET LOSS'])
            writer.writerow(['Expected', s['expected'], 'messages'])
            writer.writerow(['Received', s['received'], 'messages'])
            writer.writerow(['Lost', s['lost'], 'messages'])
            writer.writerow(['Loss Rate', f"{s['loss_rate']:.2f}", '%'])
            writer.writerow(['Avg Loss/Device', f"{s['avg_loss_per_device']:.2f}", '%'])
            writer.writerow([])

        # Total Section
        writer.writerow(['TOTAL'])
        writer.writerow(['Metric', 'Value', 'Unit'])
        writer.writerow(['Duration', f"{summary['total']['duration']:.2f}", 's'])
        writer.writerow(['Total Messages', summary['total']['total_messages'], 'messages'])
        writer.writerow(['Throughput', f"{summary['total']['throughput']:.2f}", 'msg/s'])

    print(f"CSV summary saved to: {output_file} (open with Excel)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate_summary_manual_v2_simple.py <path_to_mqtt_metrics_log.csv>")
        print("\nExample:")
        print("  python3 generate_summary_manual_v2_simple.py /home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-24_13-36-51/mqtt_metrics_log.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)

    # Calculate summary
    summary = calculate_summary(csv_file)

    # Print to console
    print_summary(summary)

    # Save to file in same directory as CSV
    output_dir = os.path.dirname(csv_file)

    # Save text summary
    output_txt = os.path.join(output_dir, "metrics_summary_v2.txt")
    save_summary(summary, output_txt)

    # Save CSV summary (Excel-compatible)
    output_csv = os.path.join(output_dir, "metrics_summary_v2_excel.csv")
    save_summary_csv(summary, output_csv)

    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)
