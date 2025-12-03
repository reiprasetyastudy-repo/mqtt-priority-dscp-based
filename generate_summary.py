#!/usr/bin/env python3
"""
Generate Summary - Main Entry Point

Usage:
    python3 generate_summary.py <path_to_mqtt_metrics_log.csv>

Example:
    python3 generate_summary.py results/01-baseline/run_2025-12-03/mqtt_metrics_log.csv
"""

import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from shared.analysis.metrics import generate_summary
from shared.analysis.packet_loss import parse_publisher_logs
from shared.analysis.export import save_summary_txt, save_summary_csv, print_summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_summary.py <path_to_mqtt_metrics_log.csv>")
        print("Example: python3 generate_summary.py results/01-baseline/run_*/mqtt_metrics_log.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    print(f"Processing: {csv_file}")
    print("=" * 60)
    
    # Determine logs directory
    csv_dir = os.path.dirname(csv_file)
    logs_dir = os.path.join(csv_dir, 'logs')
    
    # Parse publisher logs for accurate packet loss
    publisher_stats = {}
    if os.path.exists(logs_dir):
        publisher_stats = parse_publisher_logs(logs_dir)
    else:
        print(f"Note: logs/ directory not found, using sequence-based estimation")
    
    # Generate summary
    summary = generate_summary(csv_file, publisher_stats)
    
    # Print to console
    print_summary(summary)
    
    # Save to files
    output_dir = csv_dir
    save_summary_txt(summary, os.path.join(output_dir, 'metrics_summary.txt'))
    save_summary_csv(summary, os.path.join(output_dir, 'metrics_summary.csv'))
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
