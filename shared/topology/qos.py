#!/usr/bin/env python3
"""
QoS Queue Configuration Functions

Functions for configuring HTB queues on OVS switches.
"""

import subprocess


def configure_switch_queues(switch_name, bandwidth_bps):
    """
    Configure HTB queues on a single switch.
    
    Creates 2 queues:
    - Queue 1: High priority (DSCP 46) - 60-80% bandwidth
    - Queue 5: Best effort (DSCP 0)   - 5-15% bandwidth
    
    Args:
        switch_name: Switch name (e.g., 's1')
        bandwidth_bps: Link bandwidth in bits per second
    """
    # Get all ports on this switch
    result = subprocess.run(
        ['ovs-vsctl', 'list-ports', switch_name],
        capture_output=True, text=True
    )
    ports = result.stdout.strip().split('\n')
    
    for port in ports:
        if not port:
            continue
        configure_port_queues(port, bandwidth_bps)


def configure_port_queues(port, bandwidth_bps):
    """
    Configure HTB queues on a single port.
    
    Args:
        port: Port name (e.g., 's1-eth1')
        bandwidth_bps: Link bandwidth in bits per second
    """
    subprocess.run([
        'ovs-vsctl', 'set', 'port', port,
        'qos=@newqos', '--',
        '--id=@newqos', 'create', 'qos', 'type=linux-htb',
        f'other-config:max-rate={bandwidth_bps}',
        'queues:1=@q1', 'queues:5=@q5', '--',
        '--id=@q1', 'create', 'queue',
        f'other-config:min-rate={int(bandwidth_bps * 0.6)}',
        f'other-config:max-rate={int(bandwidth_bps * 0.8)}', '--',
        '--id=@q5', 'create', 'queue',
        f'other-config:min-rate={int(bandwidth_bps * 0.05)}',
        f'other-config:max-rate={int(bandwidth_bps * 0.15)}'
    ], capture_output=True)


def clear_switch_qos(switch_name):
    """
    Clear QoS configuration from a switch.
    
    Args:
        switch_name: Switch name (e.g., 's1')
    """
    result = subprocess.run(
        ['ovs-vsctl', 'list-ports', switch_name],
        capture_output=True, text=True
    )
    ports = result.stdout.strip().split('\n')
    
    for port in ports:
        if port:
            subprocess.run(
                ['ovs-vsctl', 'clear', 'port', port, 'qos'],
                capture_output=True
            )
    
    # Clean up QoS and Queue entries
    subprocess.run(
        ['ovs-vsctl', '--all', 'destroy', 'qos'],
        capture_output=True
    )
    subprocess.run(
        ['ovs-vsctl', '--all', 'destroy', 'queue'],
        capture_output=True
    )
