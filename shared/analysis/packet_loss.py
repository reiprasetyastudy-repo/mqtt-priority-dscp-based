#!/usr/bin/env python3
"""
Packet Loss Calculation

Functions for parsing publisher logs and calculating accurate packet loss.
"""

import os
import re
import glob


def parse_publisher_logs(logs_dir):
    """
    Parse publisher logs to get actual sent count per device.
    
    Args:
        logs_dir: Path to logs directory
        
    Returns:
        dict: {device_name: {'sent': count, 'last_seq': seq, 'type': type}}
    """
    publisher_stats = {}
    
    if not os.path.exists(logs_dir):
        print(f"Warning: Logs directory not found: {logs_dir}")
        return publisher_stats
    
    # Find all publisher log files
    log_patterns = [
        os.path.join(logs_dir, 'publisher_*.log'),
        os.path.join(logs_dir, 'f*.log'),
    ]
    
    log_files = []
    for pattern in log_patterns:
        log_files.extend(glob.glob(pattern))
    
    # Remove duplicates
    log_files = list(set(log_files))
    
    if not log_files:
        print(f"Warning: No publisher logs found in {logs_dir}")
        return publisher_stats
    
    print(f"Parsing {len(log_files)} publisher logs...")
    
    for log_file in sorted(log_files):
        stats = parse_single_publisher_log(log_file)
        if stats:
            publisher_stats[stats['device']] = {
                'sent': stats['count'],
                'last_seq': stats['last_seq'],
                'type': stats['type']
            }
    
    print(f"  Found {len(publisher_stats)} publisher devices")
    return publisher_stats


def parse_single_publisher_log(log_file):
    """
    Parse a single publisher log file.
    
    Args:
        log_file: Path to log file
        
    Returns:
        dict: {'device': name, 'count': count, 'last_seq': seq, 'type': type}
        or None if parsing fails
    """
    device_name = None
    msg_type = None
    last_seq = -1
    msg_count = 0
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Extract device name from header
                if line.startswith('Device') and ':' in line:
                    device_name = line.split(':')[1].strip()
                
                # Extract traffic type
                if line.startswith('Traffic Type') and ':' in line:
                    msg_type = line.split(':')[1].strip().lower()
                
                # Count messages (lines with seq=)
                seq_match = re.search(r'seq=(\d+)', line)
                if seq_match:
                    seq = int(seq_match.group(1))
                    last_seq = max(last_seq, seq)
                    msg_count += 1
        
        if device_name and msg_count > 0:
            return {
                'device': device_name,
                'count': msg_count,
                'last_seq': last_seq,
                'type': msg_type or ('anomaly' if 'anomaly' in device_name else 'normal')
            }
    
    except Exception as e:
        print(f"  Warning: Error parsing {log_file}: {e}")
    
    return None


def calculate_packet_loss(sent, received):
    """
    Calculate packet loss statistics.
    
    Args:
        sent: Number of messages sent
        received: Number of messages received
        
    Returns:
        dict: {'lost': count, 'rate': percentage}
    """
    lost = sent - received
    rate = (lost / sent * 100) if sent > 0 else 0
    
    return {
        'lost': lost,
        'rate': rate
    }


def print_packet_loss_report(publisher_stats, received_by_device):
    """
    Print detailed packet loss report.
    
    Args:
        publisher_stats: Dict from parse_publisher_logs()
        received_by_device: Dict of {device: received_count}
    """
    print("\n" + "=" * 70)
    print("PACKET LOSS (Publisher Sent vs Subscriber Received)")
    print("=" * 70)
    
    total_sent = {'anomaly': 0, 'normal': 0}
    total_received = {'anomaly': 0, 'normal': 0}
    
    for device in sorted(publisher_stats.keys()):
        stats = publisher_stats[device]
        sent = stats['sent']
        received = received_by_device.get(device, 0)
        lost = sent - received
        loss_rate = (lost / sent * 100) if sent > 0 else 0
        
        msg_type = stats['type']
        total_sent[msg_type] += sent
        total_received[msg_type] += received
        
        status = "OK" if loss_rate == 0 else f"{loss_rate:.2f}% loss"
        print(f"  {device:30s}: Sent {sent:6d}, Received {received:6d}, Lost {lost:4d} ({status})")
    
    print("\nSUMMARY:")
    for msg_type in ['anomaly', 'normal']:
        sent = total_sent[msg_type]
        received = total_received[msg_type]
        lost = sent - received
        rate = (lost / sent * 100) if sent > 0 else 0
        print(f"  {msg_type.upper():8s}: Sent {sent:6d}, Received {received:6d}, Lost {lost:5d} ({rate:.2f}%)")
