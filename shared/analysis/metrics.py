#!/usr/bin/env python3
"""
Metrics Calculation Functions

Core functions for calculating delay, jitter, and other metrics.
"""

import csv
from collections import defaultdict
from statistics import mean, stdev
import numpy as np


def calculate_delay_stats(delays):
    """
    Calculate delay statistics.
    
    Args:
        delays: List of delay values in milliseconds
        
    Returns:
        dict: Statistics (avg, min, max, std)
    """
    if not delays:
        return {'avg': 0, 'min': 0, 'max': 0, 'std': 0}
    
    return {
        'avg': mean(delays),
        'min': min(delays),
        'max': max(delays),
        'std': stdev(delays) if len(delays) > 1 else 0
    }


def calculate_jitter(delays):
    """
    Calculate jitter (variation in delay).
    
    Jitter is the average absolute difference between consecutive delays.
    
    Args:
        delays: List of delay values in milliseconds
        
    Returns:
        float: Average jitter in milliseconds
    """
    if len(delays) < 2:
        return 0.0
    
    jitter_values = []
    for i in range(1, len(delays)):
        jitter = abs(delays[i] - delays[i-1])
        if np.isfinite(jitter):
            jitter_values.append(jitter)
    
    return mean(jitter_values) if jitter_values else 0.0


def calculate_per_device_jitter(device_delays):
    """
    Calculate jitter per device, then aggregate.
    
    This is the correct method - jitter should be calculated
    within each device's message stream, not across devices.
    
    Args:
        device_delays: Dict of {device_name: [delays]}
        
    Returns:
        float: Aggregate average jitter
    """
    all_jitter = []
    
    for device, delays in device_delays.items():
        if len(delays) >= 2:
            device_jitter = calculate_jitter(delays)
            if device_jitter > 0:
                all_jitter.append(device_jitter)
    
    return mean(all_jitter) if all_jitter else 0.0


def parse_csv_metrics(csv_file):
    """
    Parse CSV file and extract metrics.
    
    Args:
        csv_file: Path to mqtt_metrics_log.csv
        
    Returns:
        dict: Parsed data organized by device and type
    """
    data = {
        'devices': defaultdict(lambda: {
            'type': None,
            'delays': [],
            'sequences': set(),
            'min_seq': float('inf'),
            'max_seq': -1
        }),
        'by_type': {
            'anomaly': {'delays': [], 'count': 0},
            'normal': {'delays': [], 'count': 0}
        },
        'total_messages': 0,
        'first_timestamp': None,
        'last_timestamp': None
    }
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            device = row['device']
            msg_type = row['type']
            delay = float(row['delay_ms'])
            seq = int(row['seq'])
            timestamp = float(row['timestamp_sent'])
            
            # Per-device tracking
            data['devices'][device]['type'] = msg_type
            data['devices'][device]['delays'].append(delay)
            data['devices'][device]['sequences'].add(seq)
            data['devices'][device]['min_seq'] = min(
                data['devices'][device]['min_seq'], seq
            )
            data['devices'][device]['max_seq'] = max(
                data['devices'][device]['max_seq'], seq
            )
            
            # By type tracking
            data['by_type'][msg_type]['delays'].append(delay)
            data['by_type'][msg_type]['count'] += 1
            
            # Overall tracking
            data['total_messages'] += 1
            if data['first_timestamp'] is None:
                data['first_timestamp'] = timestamp
            data['last_timestamp'] = timestamp
    
    return data


def generate_summary(csv_file, publisher_stats=None):
    """
    Generate complete summary from CSV data.
    
    Args:
        csv_file: Path to mqtt_metrics_log.csv
        publisher_stats: Optional dict from publisher log parsing
        
    Returns:
        dict: Complete summary statistics
    """
    data = parse_csv_metrics(csv_file)
    
    summary = {
        'total_messages': data['total_messages'],
        'total_devices': len(data['devices']),
        'duration': (data['last_timestamp'] - data['first_timestamp']) 
                   if data['first_timestamp'] else 0,
        'anomaly': None,
        'normal': None,
        'devices': []
    }
    
    # Calculate per-type metrics
    for msg_type in ['anomaly', 'normal']:
        type_data = data['by_type'][msg_type]
        if type_data['count'] > 0:
            # Get device delays for jitter calculation
            device_delays = {
                d: info['delays'] 
                for d, info in data['devices'].items() 
                if info['type'] == msg_type
            }
            
            delay_stats = calculate_delay_stats(type_data['delays'])
            jitter = calculate_per_device_jitter(device_delays)
            
            # Calculate packet loss
            sent = 0
            received = 0
            for device, info in data['devices'].items():
                if info['type'] == msg_type:
                    # Get sent count: use MAX of publisher log and seq range
                    # (log may be truncated due to buffering when process killed)
                    seq_range = info['max_seq'] - info['min_seq'] + 1
                    if publisher_stats and device in publisher_stats:
                        log_count = publisher_stats[device]['sent']
                        sent += max(log_count, seq_range)
                    else:
                        sent += seq_range
                    received += len(info['sequences'])
            
            lost = sent - received
            loss_rate = (lost / sent * 100) if sent > 0 else 0
            
            summary[msg_type] = {
                'count': type_data['count'],
                'devices': len(device_delays),
                'delay': delay_stats,
                'jitter': jitter,
                'packet_loss': {
                    'sent': sent,
                    'received': received,
                    'lost': lost,
                    'rate': loss_rate
                }
            }
    
    # Per-device summary
    for device, info in sorted(data['devices'].items()):
        if not info['delays']:
            continue
            
        # Parse floor from device name
        floor = 'N/A'
        if '_f' in device and 'r' in device:
            try:
                parts = device.split('_')
                for p in parts:
                    if p.startswith('f') and 'r' in p:
                        floor = p.split('r')[0].replace('f', '')
                        break
            except:
                pass
        
        # Get sent count: use MAX of publisher log and seq range
        seq_range = info['max_seq'] - info['min_seq'] + 1
        if publisher_stats and device in publisher_stats:
            log_count = publisher_stats[device]['sent']
            sent = max(log_count, seq_range)
        else:
            sent = seq_range
        
        received = len(info['sequences'])
        lost = sent - received
        loss_rate = (lost / sent * 100) if sent > 0 else 0
        
        summary['devices'].append({
            'name': device,
            'floor': floor,
            'type': info['type'],
            'sent': sent,
            'received': received,
            'lost': lost,
            'loss_rate': loss_rate,
            'delay': calculate_delay_stats(info['delays']),
            'jitter': calculate_jitter(info['delays'])
        })
    
    # Sort by delay descending
    summary['devices'].sort(key=lambda x: x['delay']['avg'], reverse=True)
    
    return summary
