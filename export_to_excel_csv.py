#!/usr/bin/env python3
"""Export Summary to Excel-compatible CSV"""

import sys
import csv
import os
from statistics import mean, stdev
from collections import defaultdict

def calculate_summary(csv_file):
    delays = {'anomaly': [], 'normal': []}
    jitter_values = {'anomaly': [], 'normal': []}
    prev_delay = {'anomaly': None, 'normal': None}
    device_data = defaultdict(lambda: {'type': None, 'received_seq': set(), 'max_seq': -1})
    message_count = 0
    first_timestamp = None
    last_timestamp = None

    print(f"Reading: {csv_file}")
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            device, msg_type = row['device'], row['type']
            delay, seq, timestamp = float(row['delay_ms']), int(row['seq']), float(row['timestamp_sent'])

            delays[msg_type].append(delay)
            message_count += 1

            if prev_delay[msg_type] is not None:
                jitter_values[msg_type].append(abs(delay - prev_delay[msg_type]))
            prev_delay[msg_type] = delay

            device_data[device]['type'] = msg_type
            device_data[device]['received_seq'].add(seq)
            if seq > device_data[device]['max_seq']:
                device_data[device]['max_seq'] = seq

            if first_timestamp is None:
                first_timestamp = timestamp
            last_timestamp = timestamp

    loss_by_type = {'anomaly': [], 'normal': []}
    total_by_type = {'anomaly': {'expected': 0, 'received': 0, 'lost': 0},
                     'normal': {'expected': 0, 'received': 0, 'lost': 0}}

    for device, data in device_data.items():
        msg_type = data['type']
        expected = data['max_seq'] + 1
        received = len(data['received_seq'])
        lost = expected - received
        loss_rate = (lost / expected * 100) if expected > 0 else 0

        loss_by_type[msg_type].append(loss_rate)
        total_by_type[msg_type]['expected'] += expected
        total_by_type[msg_type]['received'] += received
        total_by_type[msg_type]['lost'] += lost

    duration = last_timestamp - first_timestamp if first_timestamp else 0

    summary = {}
    for msg_type in ['anomaly', 'normal']:
        if delays[msg_type]:
            t = total_by_type[msg_type]
            summary[msg_type] = {
                'count': len(delays[msg_type]),
                'avg_delay': mean(delays[msg_type]),
                'min_delay': min(delays[msg_type]),
                'max_delay': max(delays[msg_type]),
                'std_delay': stdev(delays[msg_type]) if len(delays[msg_type]) > 1 else 0,
                'avg_jitter': mean(jitter_values[msg_type]) if jitter_values[msg_type] else 0,
                'num_devices': len([d for d, info in device_data.items() if info['type'] == msg_type]),
                'expected': t['expected'],
                'received': t['received'],
                'lost': t['lost'],
                'loss_rate': (t['lost'] / t['expected'] * 100) if t['expected'] > 0 else 0,
                'avg_loss_per_device': mean(loss_by_type[msg_type]) if loss_by_type[msg_type] else 0
            }

    summary['total'] = {'duration': duration, 'total_messages': message_count,
                       'throughput': message_count / duration if duration > 0 else 0}
    return summary

def save_excel_csv(summary, output_file):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['MQTT-SDN METRICS SUMMARY'])
        writer.writerow([])

        for msg_type in ['anomaly', 'normal']:
            if msg_type in summary and summary[msg_type]:
                s = summary[msg_type]
                writer.writerow([f'{msg_type.upper()} TRAFFIC'])
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

        writer.writerow(['TOTAL'])
        writer.writerow(['Metric', 'Value', 'Unit'])
        writer.writerow(['Duration', f"{summary['total']['duration']:.2f}", 's'])
        writer.writerow(['Total Messages', summary['total']['total_messages'], 'messages'])
        writer.writerow(['Throughput', f"{summary['total']['throughput']:.2f}", 'msg/s'])

    print(f"Excel CSV saved: {output_file}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 export_to_excel_csv.py <mqtt_metrics_log.csv>")
        sys.exit(1)

    csv_file = sys.argv[1]
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        sys.exit(1)

    summary = calculate_summary(csv_file)
    output = os.path.join(os.path.dirname(csv_file), "metrics_summary_excel.csv")
    save_excel_csv(summary, output)
    print("Done! Open with Excel or LibreOffice.")
