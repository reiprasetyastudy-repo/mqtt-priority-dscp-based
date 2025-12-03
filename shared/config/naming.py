#!/usr/bin/env python3
"""
Sensor Naming Functions

Standardized naming for hosts and devices across all scenarios.
"""


def get_host_name(floor, room, sensor_type):
    """
    Get short host name for Mininet.
    
    Must be short because Linux interface names have 15 char limit.
    Format: f{floor}r{room}{a|n} → e.g., f1r1a, f1r1n
    
    Args:
        floor: Floor number (1, 2, 3, ...)
        room: Room number (1, 2, 3, ...)
        sensor_type: 'anomaly' or 'normal'
        
    Returns:
        str: Short host name (max 5 chars)
    """
    suffix = 'a' if sensor_type == 'anomaly' else 'n'
    return f'f{floor}r{room}{suffix}'


def get_device_name(floor, room, sensor_type):
    """
    Get full device name for MQTT payload.
    
    This name appears in the MQTT message and CSV logs.
    Format: sensor_f{floor}r{room}_{type} → e.g., sensor_f1r1_anomaly
    
    Args:
        floor: Floor number (1, 2, 3, ...)
        room: Room number (1, 2, 3, ...)
        sensor_type: 'anomaly' or 'normal'
        
    Returns:
        str: Full device name
    """
    return f'sensor_f{floor}r{room}_{sensor_type}'


def parse_device_name(device_name):
    """
    Parse device name to extract floor, room, and type.
    
    Args:
        device_name: e.g., 'sensor_f1r1_anomaly'
        
    Returns:
        tuple: (floor, room, sensor_type) or (None, None, None) if parsing fails
    """
    try:
        # sensor_f1r1_anomaly → ['sensor', 'f1r1', 'anomaly']
        parts = device_name.split('_')
        if len(parts) >= 3:
            location = parts[1]  # f1r1
            sensor_type = parts[2]  # anomaly or normal
            
            # Parse f1r1 → floor=1, room=1
            floor = int(location[1])
            room = int(location[3])
            
            return floor, room, sensor_type
    except (IndexError, ValueError):
        pass
    
    return None, None, None
