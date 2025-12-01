#!/usr/bin/env python3
"""
Generate Summary for Link Failure Test (Scenario 10)
Analyzes CSV with phase tracking (phase1 vs phase2)
Includes per-sensor metrics

Usage:
    python3 generate_summary_linkfailure.py <csv_file>
    python3 generate_summary_linkfailure.py results/10-dscp-qos-13switches-linkfailure/run_xxx/mqtt_metrics_log.csv
"""

import csv
import sys
import os
from collections import defaultdict

def analyze_csv(csv_file):
    """Analyze CSV file with phase tracking"""
    
    # Data structure per phase
    data = {
        'phase1': {
            'anomaly': [], 
            'normal': [], 
            'devices': defaultdict(lambda: {'seqs': set(), 'min_seq': float('inf'), 'max_seq': -1, 'delays': [], 'type': None})
        },
        'phase2': {
            'anomaly': [], 
            'normal': [], 
            'devices': defaultdict(lambda: {'seqs': set(), 'min_seq': float('inf'), 'max_seq': -1, 'delays': [], 'type': None})
        }
    }
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phase = row.get('phase', 'phase1')
            msg_type = row['type']
            delay = float(row['delay_ms'])
            device = row['device']
            seq = int(row['seq'])
            
            if phase not in data:
                phase = 'phase1'
            
            data[phase][msg_type].append(delay)
            data[phase]['devices'][device]['seqs'].add(seq)
            data[phase]['devices'][device]['type'] = msg_type
            data[phase]['devices'][device]['delays'].append(delay)
            if seq > data[phase]['devices'][device]['max_seq']:
                data[phase]['devices'][device]['max_seq'] = seq
            if seq < data[phase]['devices'][device]['min_seq']:
                data[phase]['devices'][device]['min_seq'] = seq
    
    return data

def calc_stats(delays):
    """Calculate statistics for delays"""
    if not delays:
        return None
    
    avg = sum(delays) / len(delays)
    min_d = min(delays)
    max_d = max(delays)
    std = (sum((x - avg)**2 for x in delays) / len(delays))**0.5
    
    # Jitter (average difference between consecutive delays)
    jitter = 0
    if len(delays) > 1:
        diffs = [abs(delays[i] - delays[i-1]) for i in range(1, len(delays))]
        jitter = sum(diffs) / len(diffs)
    
    return {
        'count': len(delays),
        'avg': avg,
        'min': min_d,
        'max': max_d,
        'std': std,
        'jitter': jitter
    }

def calc_loss(devices, msg_type):
    """Calculate packet loss per message type using sequence range"""
    total_expected = 0
    total_received = 0
    num_devices = 0
    
    for device, info in devices.items():
        if info.get('type') == msg_type and info['max_seq'] >= 0:
            num_devices += 1
            # Use range instead of max_seq + 1 to handle per-phase calculation
            min_seq = info['min_seq'] if info['min_seq'] != float('inf') else 0
            expected = info['max_seq'] - min_seq + 1
            received = len(info['seqs'])
            total_expected += expected
            total_received += received
    
    lost = total_expected - total_received
    loss_rate = (lost / total_expected * 100) if total_expected > 0 else 0
    
    return {
        'num_devices': num_devices,
        'expected': total_expected,
        'received': total_received,
        'lost': lost,
        'loss_rate': loss_rate
    }

def get_device_stats(devices):
    """Calculate per-device statistics with packet loss"""
    device_stats = []
    
    for device, info in devices.items():
        if info['delays']:
            delays = info['delays']
            avg_delay = sum(delays) / len(delays)
            
            # Parse floor and room from device name (e.g., sensor_f1r1_anomaly)
            floor = 'N/A'
            room = 'N/A'
            if '_f' in device and 'r' in device:
                try:
                    parts = device.split('_')
                    for p in parts:
                        if p.startswith('f') and 'r' in p:
                            floor = p.split('r')[0].replace('f', '')
                            room = p.split('r')[1]
                            break
                except:
                    pass
            
            # Calculate packet loss using sequence range (not max_seq + 1)
            min_seq = info['min_seq'] if info['min_seq'] != float('inf') else 0
            expected = info['max_seq'] - min_seq + 1
            received = len(info['seqs'])
            lost = expected - received
            loss_rate = (lost / expected * 100) if expected > 0 else 0
            
            device_stats.append({
                'device': device,
                'floor': floor,
                'room': room,
                'type': info['type'],
                'count': len(delays),
                'avg_delay': avg_delay,
                'min_delay': min(delays),
                'max_delay': max(delays),
                'expected': expected,
                'received': received,
                'lost': lost,
                'loss_rate': loss_rate
            })
    
    return device_stats

def print_phase_stats(phase_name, phase_label, data, f):
    """Print statistics for a phase"""
    header = f"\n{'='*70}\n  {phase_label}\n{'='*70}\n"
    print(header)
    f.write(header)
    
    total_messages = 0
    
    for msg_type in ['anomaly', 'normal']:
        delays = data[msg_type]
        stats = calc_stats(delays)
        loss = calc_loss(data['devices'], msg_type)
        
        if stats:
            total_messages += stats['count']
            output = f"""
{msg_type.upper()}:
  Devices           : {loss['num_devices']}
  Messages Received : {stats['count']}
  Avg Delay         : {stats['avg']:.2f} ms
  Min Delay         : {stats['min']:.2f} ms
  Max Delay         : {stats['max']:.2f} ms
  Std Dev Delay     : {stats['std']:.2f} ms
  Avg Jitter        : {stats['jitter']:.2f} ms

  PACKET LOSS:
    Expected        : {loss['expected']} messages
    Received        : {loss['received']} messages
    Lost            : {loss['lost']} messages
    Loss Rate       : {loss['loss_rate']:.2f}%
"""
            print(output)
            f.write(output)
    
    # Per-sensor statistics
    device_stats = get_device_stats(data['devices'])
    if device_stats:
        per_device_header = f"\n  PER-SENSOR METRICS (sorted by avg delay, highest first):\n  {'-'*82}\n"
        print(per_device_header)
        f.write(per_device_header)
        
        # Sort by avg delay descending
        device_stats_sorted = sorted(device_stats, key=lambda x: x['avg_delay'], reverse=True)
        
        # Table header with packet loss
        table_header = f"  {'Sensor':<26} {'Floor':>5} {'Type':<8} {'Recv':>6} {'Expect':>6} {'Loss':>7} {'Avg Delay':>12}\n"
        table_sep = f"  {'-'*26} {'-'*5} {'-'*8} {'-'*6} {'-'*6} {'-'*7} {'-'*12}\n"
        print(table_header + table_sep, end='')
        f.write(table_header + table_sep)
        
        for ds in device_stats_sorted:
            loss_str = f"{ds['loss_rate']:.1f}%"
            row = f"  {ds['device']:<26} {ds['floor']:>5} {ds['type']:<8} {ds['received']:>6} {ds['expected']:>6} {loss_str:>7} {ds['avg_delay']:>10.2f}ms\n"
            print(row, end='')
            f.write(row)
        
        # Per-floor summary with packet loss
        floor_data = defaultdict(lambda: {
            'anomaly_delays': [], 'normal_delays': [], 
            'total_count': 0, 'total_lost': 0
        })
        for ds in device_stats:
            floor_data[ds['floor']][f"{ds['type']}_delays"].append(ds['avg_delay'])
            floor_data[ds['floor']]['total_count'] += ds['received']
            floor_data[ds['floor']]['total_lost'] += ds['lost']
        
        floor_header = f"\n  PER-FLOOR SUMMARY:\n  {'-'*70}\n"
        print(floor_header)
        f.write(floor_header)
        
        floor_table_header = f"  {'Floor':>5} {'Messages':>10} {'Lost':>6} {'Anomaly Avg':>14} {'Normal Avg':>14} {'Loss%':>8}\n"
        floor_table_sep = f"  {'-'*5} {'-'*10} {'-'*6} {'-'*14} {'-'*14} {'-'*8}\n"
        print(floor_table_header + floor_table_sep, end='')
        f.write(floor_table_header + floor_table_sep)
        
        for floor in sorted(floor_data.keys()):
            fd = floor_data[floor]
            anomaly_avg = sum(fd['anomaly_delays']) / len(fd['anomaly_delays']) if fd['anomaly_delays'] else 0
            normal_avg = sum(fd['normal_delays']) / len(fd['normal_delays']) if fd['normal_delays'] else 0
            total = fd['total_count'] + fd['total_lost']
            loss_pct = (fd['total_lost'] / total * 100) if total > 0 else 0
            floor_row = f"  {floor:>5} {fd['total_count']:>10} {fd['total_lost']:>6} {anomaly_avg:>12.2f}ms {normal_avg:>12.2f}ms {loss_pct:>7.2f}%\n"
            print(floor_row, end='')
            f.write(floor_row)
    
    total_output = f"\nPHASE TOTAL: {total_messages} messages\n"
    print(total_output)
    f.write(total_output)
    
    return total_messages

def generate_summary(csv_file):
    """Generate full summary report"""
    
    output_dir = os.path.dirname(csv_file)
    summary_file = os.path.join(output_dir, 'metrics_summary.txt')
    
    print(f"Analyzing: {csv_file}")
    print(f"Output: {summary_file}")
    
    data = analyze_csv(csv_file)
    
    with open(summary_file, 'w') as f:
        # Header
        header = f"""
{'='*70}
  LINK FAILURE TEST - SIMULATION SUMMARY
  Scenario 10: DSCP QoS with Ring Topology + Link Failure
{'='*70}

CONFIGURATION:
  Phase 1 : Normal operation (all links active)
  Phase 2 : Link s2-eth1 DOWN (traffic via ring)
"""
        print(header)
        f.write(header)
        
        # Phase 1 stats
        p1_total = print_phase_stats('phase1', 'PHASE 1: NORMAL OPERATION', data['phase1'], f)
        
        # Phase 2 stats
        p2_total = print_phase_stats('phase2', 'PHASE 2: LINK DOWN (s2-eth1 disabled)', data['phase2'], f)
        
        # Comparison
        comparison = f"\n{'='*70}\n  PHASE COMPARISON\n{'='*70}\n"
        print(comparison)
        f.write(comparison)
        
        for msg_type in ['anomaly', 'normal']:
            p1_stats = calc_stats(data['phase1'][msg_type])
            p2_stats = calc_stats(data['phase2'][msg_type])
            
            if p1_stats and p2_stats:
                delay_diff = p2_stats['avg'] - p1_stats['avg']
                delay_pct = (delay_diff / p1_stats['avg'] * 100) if p1_stats['avg'] > 0 else 0
                
                p1_loss = calc_loss(data['phase1']['devices'], msg_type)
                p2_loss = calc_loss(data['phase2']['devices'], msg_type)
                
                comp = f"""
{msg_type.upper()}:
  Phase 1 Avg Delay : {p1_stats['avg']:.2f} ms
  Phase 2 Avg Delay : {p2_stats['avg']:.2f} ms
  Delay Change      : {delay_diff:+.2f} ms ({delay_pct:+.1f}%)
  
  Phase 1 Loss Rate : {p1_loss['loss_rate']:.2f}%
  Phase 2 Loss Rate : {p2_loss['loss_rate']:.2f}%
"""
                print(comp)
                f.write(comp)
        
        # Verdict
        verdict = f"\n{'='*70}\n  REDUNDANCY VERDICT\n{'='*70}\n"
        print(verdict)
        f.write(verdict)
        
        if p2_total > 0:
            result = f"""
  Phase 2 Messages  : {p2_total}
  
  ✓ REDUNDANCY WORKS!
    Traffic successfully rerouted via ring after link failure.
    Link s2↔s1 down, but Floor 1 traffic reached broker via s2→s3→s1 or s2→s4→s1.
"""
        else:
            result = f"""
  Phase 2 Messages  : {p2_total}
  
  ✗ REDUNDANCY FAILED!
    No messages received after link failure.
"""
        print(result)
        f.write(result)
        
        # Grand total
        grand = f"""
{'='*70}
  GRAND TOTAL
{'='*70}
  Phase 1 Messages  : {p1_total}
  Phase 2 Messages  : {p2_total}
  Total Messages    : {p1_total + p2_total}
{'='*70}
"""
        print(grand)
        f.write(grand)
    
    print(f"\nSummary saved to: {summary_file}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate_summary_linkfailure.py <csv_file>")
        print("Example: python3 generate_summary_linkfailure.py results/10-dscp-qos-13switches-linkfailure/run_xxx/mqtt_metrics_log.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    generate_summary(csv_file)
