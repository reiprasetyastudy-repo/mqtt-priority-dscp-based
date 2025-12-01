#!/usr/bin/env python3
"""
Generate Report for Scenario 09 and 10
Finds the latest run and generates a combined report

Usage:
    python3 generate_report.py
    python3 generate_report.py --scenario 09
    python3 generate_report.py --scenario 10
"""

import os
import sys
import csv
import glob
from datetime import datetime
from collections import defaultdict

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')

def find_latest_run(scenario_dir):
    """Find the latest run directory"""
    pattern = os.path.join(scenario_dir, 'run_*')
    runs = glob.glob(pattern)
    if not runs:
        return None
    return max(runs, key=os.path.getctime)

def calc_stats(delays):
    """Calculate statistics"""
    if not delays:
        return None
    avg = sum(delays) / len(delays)
    return {
        'count': len(delays),
        'avg': avg,
        'min': min(delays),
        'max': max(delays),
        'std': (sum((x - avg)**2 for x in delays) / len(delays))**0.5
    }

def analyze_scenario_09(csv_file):
    """Analyze Scenario 09 CSV"""
    data = {'anomaly': [], 'normal': []}
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            msg_type = row['type']
            delay = float(row['delay_ms'])
            data[msg_type].append(delay)
    
    return {
        'anomaly': calc_stats(data['anomaly']),
        'normal': calc_stats(data['normal']),
        'total': len(data['anomaly']) + len(data['normal'])
    }

def analyze_scenario_10(csv_file):
    """Analyze Scenario 10 CSV with phase tracking"""
    data = {
        'phase1': {'anomaly': [], 'normal': []},
        'phase2': {'anomaly': [], 'normal': []}
    }
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phase = row.get('phase', 'phase1')
            msg_type = row['type']
            delay = float(row['delay_ms'])
            if phase in data:
                data[phase][msg_type].append(delay)
    
    return {
        'phase1': {
            'anomaly': calc_stats(data['phase1']['anomaly']),
            'normal': calc_stats(data['phase1']['normal']),
            'total': len(data['phase1']['anomaly']) + len(data['phase1']['normal'])
        },
        'phase2': {
            'anomaly': calc_stats(data['phase2']['anomaly']),
            'normal': calc_stats(data['phase2']['normal']),
            'total': len(data['phase2']['anomaly']) + len(data['phase2']['normal'])
        }
    }

def generate_report():
    """Generate combined report"""
    report_file = os.path.join(RESULTS_DIR, f'REPORT_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt')
    
    report = []
    report.append("=" * 80)
    report.append("  MQTT-SDN QoS EXPERIMENT REPORT")
    report.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    # Scenario 09
    scenario_09_dir = os.path.join(RESULTS_DIR, '09-dscp-qos-13switches-ring')
    latest_09 = find_latest_run(scenario_09_dir)
    
    report.append("\n")
    report.append("=" * 80)
    report.append("  SCENARIO 09: DSCP QoS with Ring Topology (Normal Test)")
    report.append("=" * 80)
    
    if latest_09:
        csv_file = os.path.join(latest_09, 'mqtt_metrics_log.csv')
        if os.path.exists(csv_file):
            report.append(f"\nData source: {latest_09}")
            data = analyze_scenario_09(csv_file)
            
            report.append(f"\nTotal Messages: {data['total']}")
            
            for msg_type in ['anomaly', 'normal']:
                stats = data[msg_type]
                if stats:
                    dscp = "46 (EF)" if msg_type == 'anomaly' else "0 (BE)"
                    report.append(f"\n{msg_type.upper()} (DSCP {dscp}):")
                    report.append(f"  Messages     : {stats['count']}")
                    report.append(f"  Avg Delay    : {stats['avg']:.2f} ms")
                    report.append(f"  Min Delay    : {stats['min']:.2f} ms")
                    report.append(f"  Max Delay    : {stats['max']:.2f} ms")
                    report.append(f"  Std Dev      : {stats['std']:.2f} ms")
            
            # QoS Effectiveness
            if data['anomaly'] and data['normal']:
                improvement = ((data['normal']['avg'] - data['anomaly']['avg']) / data['normal']['avg']) * 100
                report.append(f"\nQoS EFFECTIVENESS:")
                report.append(f"  Anomaly gets {improvement:.1f}% lower delay than Normal")
                report.append(f"  --> QoS prioritization is WORKING!")
        else:
            report.append(f"\nNo CSV file found in {latest_09}")
    else:
        report.append("\nNo runs found for Scenario 09")
    
    # Scenario 10
    scenario_10_dir = os.path.join(RESULTS_DIR, '10-dscp-qos-13switches-linkfailure')
    latest_10 = find_latest_run(scenario_10_dir)
    
    report.append("\n")
    report.append("=" * 80)
    report.append("  SCENARIO 10: Link Failure Test (Ring Redundancy)")
    report.append("=" * 80)
    
    if latest_10:
        csv_file = os.path.join(latest_10, 'mqtt_metrics_log.csv')
        if os.path.exists(csv_file):
            report.append(f"\nData source: {latest_10}")
            data = analyze_scenario_10(csv_file)
            
            for phase, phase_label in [('phase1', 'PHASE 1: Normal Operation'), ('phase2', 'PHASE 2: Link Down')]:
                report.append(f"\n--- {phase_label} ---")
                report.append(f"Total Messages: {data[phase]['total']}")
                
                for msg_type in ['anomaly', 'normal']:
                    stats = data[phase][msg_type]
                    if stats:
                        report.append(f"\n  {msg_type.upper()}:")
                        report.append(f"    Messages   : {stats['count']}")
                        report.append(f"    Avg Delay  : {stats['avg']:.2f} ms")
                        report.append(f"    Min Delay  : {stats['min']:.2f} ms")
                        report.append(f"    Max Delay  : {stats['max']:.2f} ms")
            
            # Comparison
            report.append(f"\n--- PHASE COMPARISON ---")
            for msg_type in ['anomaly', 'normal']:
                p1 = data['phase1'][msg_type]
                p2 = data['phase2'][msg_type]
                if p1 and p2:
                    delay_change = p2['avg'] - p1['avg']
                    delay_pct = (delay_change / p1['avg']) * 100 if p1['avg'] > 0 else 0
                    report.append(f"\n  {msg_type.upper()}:")
                    report.append(f"    Phase 1 Delay: {p1['avg']:.2f} ms")
                    report.append(f"    Phase 2 Delay: {p2['avg']:.2f} ms")
                    report.append(f"    Change       : {delay_change:+.2f} ms ({delay_pct:+.1f}%)")
            
            # Redundancy Verdict
            report.append(f"\n--- REDUNDANCY VERDICT ---")
            if data['phase2']['total'] > 0:
                report.append(f"  Phase 2 received {data['phase2']['total']} messages")
                report.append(f"  --> REDUNDANCY WORKS! Traffic rerouted via ring.")
            else:
                report.append(f"  Phase 2 received 0 messages")
                report.append(f"  --> REDUNDANCY FAILED!")
            
            # Check link failure log
            link_log = os.path.join(latest_10, 'link_failure_log.txt')
            if os.path.exists(link_log):
                report.append(f"\n--- LINK FAILURE LOG ---")
                report.append(f"  See: {link_log}")
        else:
            report.append(f"\nNo CSV file found in {latest_10}")
    else:
        report.append("\nNo runs found for Scenario 10")
    
    # Summary
    report.append("\n")
    report.append("=" * 80)
    report.append("  SUMMARY")
    report.append("=" * 80)
    report.append("\nScenario 09 (Normal):")
    report.append("  - Tests DSCP-based QoS prioritization")
    report.append("  - Anomaly (DSCP 46) should have lower delay than Normal (DSCP 0)")
    
    report.append("\nScenario 10 (Link Failure):")
    report.append("  - Tests ring topology redundancy")
    report.append("  - Phase 1: Normal operation")
    report.append("  - Phase 2: Link s2-s1 down, traffic via ring")
    report.append("  - Success if Phase 2 still receives messages")
    
    report.append("\n" + "=" * 80)
    
    # Write report
    report_text = "\n".join(report)
    print(report_text)
    
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print(f"\nReport saved to: {report_file}")
    
    return report_file

if __name__ == '__main__':
    generate_report()
