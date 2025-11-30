#!/usr/bin/env python3
"""
Topology Configuration: Single Switch with 3 Hosts

Topology:
    h1 (10.0.0.1) - Publisher Anomaly
           |
          [s1] ---- h3 (10.0.0.3) - MQTT Broker + Subscriber
           |
    h2 (10.0.0.2) - Publisher Normal

Switch: OpenFlow 1.3
Controller: Remote @ 127.0.0.1:6633
"""

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
import time
import signal
import sys
import os

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
MQTT_DIR = os.path.join(PROJECT_ROOT, 'shared/mqtt')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'shared/config')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results/01-single-switch-3hosts')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

# Ensure directories exist
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


class SingleSwitchTopology:
    """Single switch topology with 3 hosts"""

    def __init__(self):
        self.net = None

    def build(self):
        """Build the Mininet topology"""
        setLogLevel('info')
        self.net = Mininet(controller=RemoteController, autoSetMacs=True)

        info('*** Building topology: Single Switch, 3 Hosts\n')

        # Add controller
        c0 = self.net.addController('c0', controller=RemoteController,
                                     ip='127.0.0.1', port=6633)

        # Add switch with OpenFlow 1.3
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')

        # Add hosts with specific IPs
        h1 = self.net.addHost('h1', ip='10.0.0.1/24')
        h2 = self.net.addHost('h2', ip='10.0.0.2/24')
        h3 = self.net.addHost('h3', ip='10.0.0.3/24')

        # Add links
        self.net.addLink(h1, s1)
        self.net.addLink(h2, s1)
        self.net.addLink(h3, s1)

        info('*** Topology built successfully\n')
        return self.net

    def start(self):
        """Start the network"""
        if not self.net:
            raise RuntimeError("Topology not built. Call build() first.")

        self.net.start()
        info('*** Network started successfully\n')
        info('*** Hosts: h1(10.0.0.1), h2(10.0.0.2), h3(10.0.0.3)\n')

        # Wait for network to stabilize
        time.sleep(3)

    def start_mqtt_components(self):
        """Start MQTT broker, publishers, and subscriber"""
        h1 = self.net.get('h1')
        h2 = self.net.get('h2')
        h3 = self.net.get('h3')

        info('*** Starting MQTT Broker on h3\n')
        h3.cmd(f'mosquitto -v -c {CONFIG_DIR}/mosquitto.conf > {LOG_DIR}/mosquitto.log 2>&1 &')
        time.sleep(2)

        info('*** Starting Subscriber on h3\n')
        h3.cmd(f'python3 {MQTT_DIR}/subscriber_enhanced.py > {LOG_DIR}/subscriber.log 2>&1 &')
        time.sleep(2)

        info('*** Starting Publisher Normal on h2\n')
        h2.cmd(f'python3 {MQTT_DIR}/publisher_normal.py > {LOG_DIR}/publisher_normal.log 2>&1 &')
        time.sleep(2)

        info('*** Starting Publisher Anomaly on h1\n')
        h1.cmd(f'python3 {MQTT_DIR}/publisher_anomaly.py > {LOG_DIR}/publisher_anomaly.log 2>&1 &')

        info('*** All MQTT components started\n')

    def cleanup(self):
        """Stop all components and clean up"""
        info('*** Stopping MQTT components\n')
        h1 = self.net.get('h1')
        h2 = self.net.get('h2')
        h3 = self.net.get('h3')

        if h1:
            h1.cmd('pkill -f publisher_anomaly')
        if h2:
            h2.cmd('pkill -f publisher_normal')
        if h3:
            h3.cmd('pkill -TERM -f subscriber_enhanced')
            time.sleep(3)  # Wait for graceful shutdown
            h3.cmd('pkill -f subscriber_enhanced')
            h3.cmd('pkill -f mosquitto')

        info('*** Stopping network\n')
        if self.net:
            self.net.stop()


def run_topology(duration_seconds=0):
    """
    Run the topology

    Args:
        duration_seconds: Run for specified duration (0 = run forever)
    """
    topology = SingleSwitchTopology()

    # Setup signal handlers
    def signal_handler(sig, frame):
        topology.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Build and start network
        topology.build()
        topology.start()

        # Start MQTT components
        topology.start_mqtt_components()

        # Run for specified duration or forever
        if duration_seconds > 0:
            info(f'*** Running for {duration_seconds} seconds...\n')
            time.sleep(duration_seconds)
            topology.cleanup()
        else:
            info('*** Running until interrupted (Ctrl+C)...\n')
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        topology.cleanup()
    except Exception as e:
        info(f'*** Error: {e}\n')
        topology.cleanup()
        raise


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Single Switch Topology')
    parser.add_argument('--duration', type=int, default=0,
                       help='Duration in seconds (0 = run forever)')
    args = parser.parse_args()

    run_topology(args.duration)
