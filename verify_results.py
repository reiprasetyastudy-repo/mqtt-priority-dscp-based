#!/usr/bin/env python3
"""
Verify Results - Check all experiment results for correctness

This script:
1. Verifies all metrics_summary.txt files use correct format (from generate_summary.py)
2. Checks packet loss calculations are based on publisher logs (not received range)
3. Regenerates any incorrect summaries

Usage:
    python3 verify_results.py [--fix]
    
Options:
    --fix    Regenerate any incorrect summaries
"""

import os
import sys
import glob
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')

def check_summary_format(summary_file):
    """
    Check if summary file uses correct format.
    
    Correct: Uses "Sent" (from generate_summary.py with publisher logs)
    Wrong: Uses "Expected" (from subscriber's internal calculation)
    
    Returns:
        tuple: (is_correct, anomaly_loss, normal_loss)
    """
    with open(summary_file, 'r') as f:
        content = f.read()
    
    # Check format
    uses_sent = 'Sent            :' in content
    uses_expected = 'Expected        :' in content
    
    if uses_expected and not uses_sent:
        return False, None, None
    
    # Extract loss rates
    anomaly_loss = None
    normal_loss = None
    
    # Find ANOMALY section
    anomaly_match = re.search(r'ANOMALY:.*?Loss Rate\s*:\s*([\d.]+)%', content, re.DOTALL)
    if anomaly_match:
        anomaly_loss = float(anomaly_match.group(1))
    
    # Find NORMAL section
    normal_match = re.search(r'NORMAL:.*?Loss Rate\s*:\s*([\d.]+)%', content, re.DOTALL)
    if normal_match:
        normal_loss = float(normal_match.group(1))
    
    return True, anomaly_loss, normal_loss


def regenerate_summary(run_dir):
    """Regenerate summary for a run directory."""
    csv_file = os.path.join(run_dir, 'mqtt_metrics_log.csv')
    if os.path.exists(csv_file):
        os.system(f'python3 {PROJECT_ROOT}/generate_summary.py {csv_file}')
        return True
    return False


def main():
    fix_mode = '--fix' in sys.argv
    
    print("=" * 70)
    print("VERIFIKASI HASIL EKSPERIMEN")
    print("=" * 70)
    print()
    
    # Find all result directories
    run_dirs = glob.glob(os.path.join(RESULTS_DIR, '*/run_*/'))
    
    correct_count = 0
    wrong_count = 0
    results = []
    
    for run_dir in sorted(run_dirs):
        summary_file = os.path.join(run_dir, 'metrics_summary.txt')
        
        if not os.path.exists(summary_file):
            continue
        
        # Extract scenario and run info
        parts = run_dir.rstrip('/').split('/')
        scenario = parts[-2]
        run_name = parts[-1]
        
        is_correct, anomaly_loss, normal_loss = check_summary_format(summary_file)
        
        if is_correct:
            correct_count += 1
            status = "✓ OK"
        else:
            wrong_count += 1
            status = "✗ SALAH"
            if fix_mode:
                print(f"Regenerating: {run_dir}")
                regenerate_summary(run_dir)
                is_correct, anomaly_loss, normal_loss = check_summary_format(summary_file)
                status = "✓ FIXED" if is_correct else "✗ FAILED"
        
        results.append({
            'scenario': scenario,
            'run': run_name,
            'anomaly_loss': anomaly_loss,
            'normal_loss': normal_loss,
            'status': status
        })
    
    # Print results table
    print(f"{'Skenario':<35} {'Run':<25} {'Anomaly':<10} {'Normal':<10} {'Status':<10}")
    print("-" * 90)
    
    for r in results:
        anomaly_str = f"{r['anomaly_loss']:.2f}%" if r['anomaly_loss'] is not None else "N/A"
        normal_str = f"{r['normal_loss']:.2f}%" if r['normal_loss'] is not None else "N/A"
        print(f"{r['scenario']:<35} {r['run']:<25} {anomaly_str:<10} {normal_str:<10} {r['status']:<10}")
    
    print()
    print("=" * 70)
    print(f"Total: {correct_count} benar, {wrong_count} salah")
    
    if wrong_count > 0 and not fix_mode:
        print()
        print("Jalankan dengan --fix untuk memperbaiki file yang salah:")
        print(f"  python3 {sys.argv[0]} --fix")
    
    print("=" * 70)
    
    return 0 if wrong_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
