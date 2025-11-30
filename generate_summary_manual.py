#!/usr/bin/env python3
"""
Manual Summary Generator for Existing CSV Data

Usage:
    python3 generate_summary_manual.py <path_to_mqtt_metrics_log.csv>

Example:
    python3 generate_summary_manual.py /home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-24_13-36-51/mqtt_metrics_log.csv
"""

import sys
import csv
import os
from statistics import mean, stdev

def calculate_summary(csv_file):
    """Calculate metrics summary from CSV file"""

    delays = {'anomaly': [], 'normal': []}
    received_seq = {'anomaly': set(), 'normal': set()}
    max_seq = {'anomaly': -1, 'normal': -1}
    jitter_values = {'anomaly': [], 'normal': []}
    prev_delay = {'anomaly': None, 'normal': None}
    message_count = 0
    first_timestamp = None
    last_timestamp = None

    print(f"Reading CSV: {csv_file}")
    print("Processing messages...")

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            msg_type = row['type']
            delay = float(row['delay_ms'])
            seq = int(row['seq'])
            timestamp = float(row['timestamp_sent'])  # Use sent timestamp

            delays[msg_type].append(delay)
            received_seq[msg_type].add(seq)
            message_count += 1

            if seq > max_seq[msg_type]:
                max_seq[msg_type] = seq

            # Calculate jitter
            if prev_delay[msg_type] is not None:
                jitter = abs(delay - prev_delay[msg_type])
                jitter_values[msg_type].append(jitter)
            prev_delay[msg_type] = delay

            if first_timestamp is None:
                first_timestamp = timestamp
            last_timestamp = timestamp

            if message_count % 10000 == 0:
                print(f"  Processed {message_count} messages...")

    print(f"Total messages processed: {message_count}")

    # Calculate summary
    duration = last_timestamp - first_timestamp if first_timestamp and last_timestamp else 0

    summary = {}
    for msg_type in ['anomaly', 'normal']:
        if delays[msg_type]:
            expected = max_seq[msg_type] + 1
            received = len(received_seq[msg_type])
            lost = expected - received
            loss_rate = (lost / expected * 100) if expected > 0 else 0

            summary[msg_type] = {
                'count': len(delays[msg_type]),
                'avg_delay': mean(delays[msg_type]),
                'min_delay': min(delays[msg_type]),
                'max_delay': max(delays[msg_type]),
                'std_delay': stdev(delays[msg_type]) if len(delays[msg_type]) > 1 else 0,
                'avg_jitter': mean(jitter_values[msg_type]) if jitter_values[msg_type] else 0,
                'max_seq': max_seq[msg_type],
                'expected': expected,
                'received': received,
                'lost': lost,
                'loss_rate': loss_rate
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
        if msg_type in summary:
            s = summary[msg_type]
            print(f"{msg_type.upper()}:")
            print(f"  Messages Received : {s['count']}")
            print(f"  Avg Delay         : {s['avg_delay']:.2f} ms")
            print(f"  Min Delay         : {s['min_delay']:.2f} ms")
            print(f"  Max Delay         : {s['max_delay']:.2f} ms")
            print(f"  Std Dev Delay     : {s['std_delay']:.2f} ms")
            print(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms")
            print(f"  Max Seq Number    : {s['max_seq']}")
            print(f"\n  PACKET LOSS:")
            print(f"    Expected        : {s['expected']} messages")
            print(f"    Received        : {s['received']} messages")
            print(f"    Lost            : {s['lost']} messages")
            print(f"    Loss Rate       : {s['loss_rate']:.2f}%")
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
            if msg_type in summary:
                s = summary[msg_type]
                f.write(f"{msg_type.upper()}:\n")
                f.write(f"  Messages Received : {s['count']}\n")
                f.write(f"  Avg Delay         : {s['avg_delay']:.2f} ms\n")
                f.write(f"  Min Delay         : {s['min_delay']:.2f} ms\n")
                f.write(f"  Max Delay         : {s['max_delay']:.2f} ms\n")
                f.write(f"  Std Dev Delay     : {s['std_delay']:.2f} ms\n")
                f.write(f"  Avg Jitter        : {s['avg_jitter']:.2f} ms\n")
                f.write(f"  Max Seq Number    : {s['max_seq']}\n")
                f.write(f"\n  PACKET LOSS:\n")
                f.write(f"    Expected        : {s['expected']} messages\n")
                f.write(f"    Received        : {s['received']} messages\n")
                f.write(f"    Lost            : {s['lost']} messages\n")
                f.write(f"    Loss Rate       : {s['loss_rate']:.2f}%\n")
                f.write("\n")

        f.write(f"TOTAL:\n")
        f.write(f"  Duration          : {summary['total']['duration']:.2f} s\n")
        f.write(f"  Total Messages    : {summary['total']['total_messages']}\n")
        f.write(f"  Throughput        : {summary['total']['throughput']:.2f} msg/s\n")

    print(f"Summary saved to: {output_file}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate_summary_manual.py <path_to_mqtt_metrics_log.csv>")
        print("\nExample:")
        print("  python3 generate_summary_manual.py /home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-24_13-36-51/mqtt_metrics_log.csv")
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
    output_file = os.path.join(output_dir, "metrics_summary.txt")
    save_summary(summary, output_file)

    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)
