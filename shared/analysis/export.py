#!/usr/bin/env python3
"""
Export Functions

Functions for exporting summary data to various formats.
"""

import csv
import os


def save_summary_txt(summary, output_file):
    """
    Save summary to text file.
    
    Args:
        summary: Summary dict from generate_summary()
        output_file: Output file path
    """
    with open(output_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write(" " * 20 + "SIMULATION SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        
        for msg_type in ['anomaly', 'normal']:
            if summary.get(msg_type):
                s = summary[msg_type]
                d = s['delay']
                pl = s['packet_loss']
                
                f.write(f"{msg_type.upper()}:\n")
                f.write(f"  Devices           : {s['devices']}\n")
                f.write(f"  Messages Received : {s['count']}\n")
                f.write(f"  Avg Delay         : {d['avg']:.2f} ms\n")
                f.write(f"  Min Delay         : {d['min']:.2f} ms\n")
                f.write(f"  Max Delay         : {d['max']:.2f} ms\n")
                f.write(f"  Std Dev Delay     : {d['std']:.2f} ms\n")
                f.write(f"  Avg Jitter        : {s['jitter']:.2f} ms\n")
                f.write(f"\n  PACKET LOSS:\n")
                f.write(f"    Sent            : {pl['sent']} messages\n")
                f.write(f"    Received        : {pl['received']} messages\n")
                f.write(f"    Lost            : {pl['lost']} messages\n")
                f.write(f"    Loss Rate       : {pl['rate']:.2f}%\n")
                f.write("\n")
        
        f.write(f"TOTAL:\n")
        f.write(f"  Duration          : {summary['duration']:.2f} s\n")
        f.write(f"  Total Messages    : {summary['total_messages']}\n")
        throughput = summary['total_messages'] / summary['duration'] if summary['duration'] > 0 else 0
        f.write(f"  Throughput        : {throughput:.2f} msg/s\n")
        f.write("\n")
        
        # Per-device table
        if summary['devices']:
            f.write("=" * 90 + "\n")
            f.write("PER-SENSOR METRICS\n")
            f.write("=" * 90 + "\n\n")
            
            f.write(f"{'Sensor':<26} {'Floor':>5} {'Type':<8} {'Recv':>6} {'Sent':>6} {'Loss':>7} {'Avg Delay':>12}\n")
            f.write(f"{'-'*26} {'-'*5} {'-'*8} {'-'*6} {'-'*6} {'-'*7} {'-'*12}\n")
            
            for ds in summary['devices']:
                loss_str = f"{ds['loss_rate']:.1f}%"
                f.write(f"{ds['name']:<26} {ds['floor']:>5} {ds['type']:<8} ")
                f.write(f"{ds['received']:>6} {ds['sent']:>6} {loss_str:>7} ")
                f.write(f"{ds['delay']['avg']:>10.2f}ms\n")
    
    print(f"Summary saved to: {output_file}")


def save_summary_csv(summary, output_file):
    """
    Save summary to CSV file (Excel-compatible).
    
    Args:
        summary: Summary dict from generate_summary()
        output_file: Output file path
    """
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        writer.writerow(['SIMULATION SUMMARY'])
        writer.writerow([])
        
        for msg_type in ['anomaly', 'normal']:
            if summary.get(msg_type):
                s = summary[msg_type]
                d = s['delay']
                pl = s['packet_loss']
                
                writer.writerow([f'{msg_type.upper()} TRAFFIC'])
                writer.writerow(['Metric', 'Value', 'Unit'])
                writer.writerow(['Devices', s['devices'], ''])
                writer.writerow(['Messages Received', s['count'], ''])
                writer.writerow(['Avg Delay', f"{d['avg']:.2f}", 'ms'])
                writer.writerow(['Min Delay', f"{d['min']:.2f}", 'ms'])
                writer.writerow(['Max Delay', f"{d['max']:.2f}", 'ms'])
                writer.writerow(['Std Dev Delay', f"{d['std']:.2f}", 'ms'])
                writer.writerow(['Avg Jitter', f"{s['jitter']:.2f}", 'ms'])
                writer.writerow([])
                writer.writerow(['PACKET LOSS'])
                writer.writerow(['Sent', pl['sent'], 'messages'])
                writer.writerow(['Received', pl['received'], 'messages'])
                writer.writerow(['Lost', pl['lost'], 'messages'])
                writer.writerow(['Loss Rate', f"{pl['rate']:.2f}", '%'])
                writer.writerow([])
        
        writer.writerow(['TOTAL'])
        writer.writerow(['Duration', f"{summary['duration']:.2f}", 's'])
        writer.writerow(['Total Messages', summary['total_messages'], ''])
        throughput = summary['total_messages'] / summary['duration'] if summary['duration'] > 0 else 0
        writer.writerow(['Throughput', f"{throughput:.2f}", 'msg/s'])
        writer.writerow([])
        
        # Per-device table
        if summary['devices']:
            writer.writerow(['PER-SENSOR METRICS'])
            writer.writerow(['Sensor', 'Floor', 'Type', 'Received', 'Sent', 'Loss%', 'Avg Delay (ms)'])
            
            for ds in summary['devices']:
                writer.writerow([
                    ds['name'],
                    ds['floor'],
                    ds['type'],
                    ds['received'],
                    ds['sent'],
                    f"{ds['loss_rate']:.1f}",
                    f"{ds['delay']['avg']:.2f}"
                ])
    
    print(f"CSV saved to: {output_file}")


def print_summary(summary):
    """
    Print summary to console.
    
    Args:
        summary: Summary dict from generate_summary()
    """
    print("\n" + "=" * 70)
    print(" " * 20 + "SIMULATION SUMMARY")
    print("=" * 70 + "\n")
    
    for msg_type in ['anomaly', 'normal']:
        if summary.get(msg_type):
            s = summary[msg_type]
            d = s['delay']
            pl = s['packet_loss']
            
            print(f"{msg_type.upper()}:")
            print(f"  Devices           : {s['devices']}")
            print(f"  Messages Received : {s['count']}")
            print(f"  Avg Delay         : {d['avg']:.2f} ms")
            print(f"  Min Delay         : {d['min']:.2f} ms")
            print(f"  Max Delay         : {d['max']:.2f} ms")
            print(f"  Std Dev Delay     : {d['std']:.2f} ms")
            print(f"  Avg Jitter        : {s['jitter']:.2f} ms")
            print(f"\n  PACKET LOSS:")
            print(f"    Sent            : {pl['sent']} messages")
            print(f"    Received        : {pl['received']} messages")
            print(f"    Lost            : {pl['lost']} messages")
            print(f"    Loss Rate       : {pl['rate']:.2f}%")
            print()
    
    print(f"TOTAL:")
    print(f"  Duration          : {summary['duration']:.2f} s")
    print(f"  Total Messages    : {summary['total_messages']}")
    throughput = summary['total_messages'] / summary['duration'] if summary['duration'] > 0 else 0
    print(f"  Throughput        : {throughput:.2f} msg/s")
    print()
