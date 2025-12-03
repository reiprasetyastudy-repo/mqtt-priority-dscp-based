#!/usr/bin/env python3
"""
Base Topology Class

Common functionality for all scenario topologies.
Extend this class and implement build_topology() for specific scenarios.
"""

import os
import sys
import time
import subprocess
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel, info

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.config.naming import get_host_name, get_device_name
from shared.config.defaults import BROKER_IP


class BaseTopology:
    """
    Base class for all scenario topologies.
    
    Provides common methods for:
    - QoS queue configuration
    - Starting/stopping MQTT components
    - Experiment timing and drain phase management
    """

    def __init__(self, scenario_name):
        """
        Initialize base topology.
        
        Args:
            scenario_name: Name of the scenario (e.g., '01-baseline')
        """
        self.scenario_name = scenario_name
        self.net = None
        self.switches = {}
        self.hosts = {}
        self.publishers = []  # List of (host, type, floor, room, edge_sw)
        self.broker_host = None
        self.log_dir = None

    def create_network(self, enable_bandwidth=True):
        """
        Create Mininet network with optional bandwidth limiting.
        
        Args:
            enable_bandwidth: If True, use TCLink for bandwidth control
        """
        setLogLevel('info')
        
        if enable_bandwidth:
            self.net = Mininet(
                controller=RemoteController,
                autoSetMacs=True,
                link=TCLink
            )
        else:
            self.net = Mininet(
                controller=RemoteController,
                autoSetMacs=True
            )
        
        # Add controller
        self.net.addController(
            'c0',
            controller=RemoteController,
            ip='127.0.0.1',
            port=6633
        )
        
        return self.net

    def configure_qos_queues(self, bandwidth_mbps):
        """
        Configure HTB QoS queues on all switches.
        
        Queue 1: High priority (DSCP 46) - 60-80% bandwidth
        Queue 5: Best effort (DSCP 0)   - 5-15% bandwidth
        
        Args:
            bandwidth_mbps: Link bandwidth in Mbps
        """
        info('*** Configuring QoS Queues\n')
        
        rate = int(bandwidth_mbps * 1_000_000)  # Convert to bps
        
        for sw_name in self.switches.keys():
            # Get all ports on this switch
            result = subprocess.run(
                ['ovs-vsctl', 'list-ports', sw_name],
                capture_output=True, text=True
            )
            ports = result.stdout.strip().split('\n')
            
            for port in ports:
                if not port:
                    continue
                    
                subprocess.run([
                    'ovs-vsctl', 'set', 'port', port,
                    'qos=@newqos', '--',
                    '--id=@newqos', 'create', 'qos', 'type=linux-htb',
                    f'other-config:max-rate={rate}',
                    'queues:1=@q1', 'queues:5=@q5', '--',
                    '--id=@q1', 'create', 'queue',
                    f'other-config:min-rate={int(rate * 0.6)}',
                    f'other-config:max-rate={int(rate * 0.8)}', '--',
                    '--id=@q5', 'create', 'queue',
                    f'other-config:min-rate={int(rate * 0.05)}',
                    f'other-config:max-rate={int(rate * 0.15)}'
                ], capture_output=True)
        
        info('  ✓ QoS queues configured\n')

    def enable_stp(self, wait_time=45):
        """
        Enable STP on all switches (for topologies with redundant links).
        
        Args:
            wait_time: Seconds to wait for STP convergence
        """
        info('*** Enabling STP on all switches\n')
        
        for sw_name in self.switches.keys():
            subprocess.run(
                ['ovs-vsctl', 'set', 'bridge', sw_name, 'stp_enable=true'],
                capture_output=True
            )
        
        info('  ✓ STP enabled\n')
        info(f'*** Waiting for STP convergence ({wait_time}s)\n')
        time.sleep(wait_time)

    def start_broker(self):
        """Start Mosquitto MQTT broker on broker host."""
        info('*** Starting MQTT Broker\n')
        self.broker_host.cmd('mosquitto -c /etc/mosquitto/mosquitto.conf &')
        time.sleep(2)
        info('  ✓ Broker started\n')

    def start_subscriber(self, scenario_dir, env_vars=None):
        """
        Start MQTT subscriber.
        
        Args:
            scenario_dir: Path to scenario directory
            env_vars: Optional environment variables string
        """
        info('*** Starting Subscriber\n')
        
        subscriber_script = os.path.join(
            PROJECT_ROOT, 'shared/mqtt/subscriber_enhanced.py'
        )
        
        cmd = f'python3 {subscriber_script} > {self.log_dir}/subscriber.log 2>&1 &'
        if env_vars:
            cmd = f'{env_vars} {cmd}'
        
        self.broker_host.cmd(cmd)
        time.sleep(2)
        info('  ✓ Subscriber started\n')

    def start_publishers(self, scenario_dir, msg_rate, bandwidth_mbps):
        """
        Start all publishers.
        
        Args:
            scenario_dir: Path to scenario directory
            msg_rate: Messages per second per publisher
            bandwidth_mbps: Link bandwidth (for env vars)
        """
        info('*** Starting Publishers\n')
        
        for host, sensor_type, floor, room, edge_sw in self.publishers:
            # Determine script
            if sensor_type == 'anomaly':
                script = os.path.join(scenario_dir, 'publisher_dscp46_veryhigh.py')
            else:
                script = os.path.join(scenario_dir, 'publisher_dscp0_besteffort.py')
            
            # Get device name for MQTT payload
            device_name = get_device_name(floor, room, sensor_type)
            
            # Start publisher with environment variables
            host.cmd(
                f'DEVICE={device_name} '
                f'BROKER_IP={BROKER_IP} '
                f'MSG_RATE={msg_rate} '
                f'python3 {script} > {self.log_dir}/{host.name}.log 2>&1 &'
            )
            time.sleep(0.05)  # Small delay between starts
        
        info(f'  ✓ Started {len(self.publishers)} publishers\n')

    def stop_publishers(self):
        """Stop all publisher processes."""
        info('*** Stopping Publishers\n')
        for host, _, _, _, _ in self.publishers:
            host.cmd('pkill -f publisher_dscp')
        time.sleep(1)
        info('  ✓ Publishers stopped\n')

    def stop_subscriber(self):
        """Stop subscriber process."""
        info('*** Stopping Subscriber\n')
        self.broker_host.cmd('pkill -f subscriber')
        time.sleep(1)
        info('  ✓ Subscriber stopped\n')

    def get_message_count(self):
        """Get current message count from CSV file."""
        csv_file = os.path.join(os.getcwd(), 'mqtt_metrics_log.csv')
        if os.path.exists(csv_file):
            with open(csv_file, 'r') as f:
                return sum(1 for _ in f) - 1  # Minus header
        return 0

    def run_experiment(self, duration, drain_ratio, scenario_dir, msg_rate, bandwidth_mbps):
        """
        Run the complete experiment with proper timing.
        
        Args:
            duration: Send phase duration in seconds
            drain_ratio: Drain time = duration × drain_ratio
            scenario_dir: Path to scenario directory
            msg_rate: Messages per second per publisher
            bandwidth_mbps: Link bandwidth in Mbps
        """
        drain_time = int(duration * drain_ratio)
        total_time = duration + drain_time
        
        # Print timing info
        info(f'\n{"="*60}\n')
        info(f'EXPERIMENT TIMING:\n')
        info(f'  Send phase  : {duration} seconds\n')
        info(f'  Drain phase : {drain_time} seconds (ratio: {drain_ratio})\n')
        info(f'  Total time  : {total_time} seconds\n')
        info(f'{"="*60}\n\n')
        
        start_time = time.time()
        
        # ========== PHASE 1: SEND ==========
        info(f'*** [PHASE 1] Send phase started at {time.strftime("%H:%M:%S")}\n')
        
        self.start_publishers(scenario_dir, msg_rate, bandwidth_mbps)
        
        # Wait for send duration
        time.sleep(duration)
        
        send_end_time = time.time()
        actual_send = send_end_time - start_time
        info(f'*** [PHASE 1] Send phase ended at {time.strftime("%H:%M:%S")}\n')
        info(f'    Actual duration: {actual_send:.1f}s (expected: {duration}s)\n')
        
        # ========== STOP PUBLISHERS ==========
        self.stop_publishers()
        
        msg_before_drain = self.get_message_count()
        info(f'    Messages before drain: {msg_before_drain}\n')
        
        # ========== PHASE 2: DRAIN ==========
        info(f'\n*** [PHASE 2] Drain phase started at {time.strftime("%H:%M:%S")}\n')
        info(f'    Waiting for queued messages...\n')
        
        time.sleep(drain_time)
        
        drain_end_time = time.time()
        actual_drain = drain_end_time - send_end_time
        
        msg_after_drain = self.get_message_count()
        drain_messages = msg_after_drain - msg_before_drain
        
        info(f'*** [PHASE 2] Drain phase ended at {time.strftime("%H:%M:%S")}\n')
        info(f'    Actual duration: {actual_drain:.1f}s (expected: {drain_time}s)\n')
        info(f'    Messages during drain: {drain_messages}\n')
        
        # ========== VERIFICATION ==========
        total_actual = drain_end_time - start_time
        info(f'\n{"="*60}\n')
        info(f'TIMING VERIFICATION:\n')
        info(f'  Expected total : {total_time}s\n')
        info(f'  Actual total   : {total_actual:.1f}s\n')
        info(f'  Difference     : {abs(total_actual - total_time):.1f}s\n')
        
        if drain_messages > 0:
            info(f'\n  ✓ DRAIN OK: {drain_messages} messages received after publishers stopped\n')
        else:
            info(f'\n  ⚠ WARNING: No messages received during drain phase\n')
        
        info(f'{"="*60}\n\n')
        
        # ========== CLEANUP ==========
        self.stop_subscriber()
        
        return {
            'total_messages': msg_after_drain,
            'drain_messages': drain_messages,
            'actual_duration': total_actual
        }

    def cleanup(self):
        """Stop the network."""
        if self.net:
            info('*** Stopping Network\n')
            self.net.stop()
