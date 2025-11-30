#!/usr/bin/env python3
"""
Topology Configuration: Hierarchical 3-Tier with 13 Switches

Topology Structure:
                    ┌──────┐
                    │  s1  │ CORE (Broker here)
                    │ 10GB │
                    └───┬──┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │     │  s3   │     │  s4   │  AGGREGATION
      │Floor 1│     │Floor 2│     │Floor 3│
      └───┬───┘     └───┬───┘     └───┬───┘
          │             │             │
      ┌───┼───┐     ┌───┼───┐     ┌───┼───┐
      │   │   │     │   │   │     │   │   │
     s5  s6  s7    s8  s9 s10   s11 s12 s13  EDGE (Access)
      │   │   │     │   │   │     │   │   │
    IoT IoT IoT   IoT IoT IoT   IoT IoT IoT

Use Case: Smart Building (3 floors, 3 rooms per floor)
- s1: Core/Gateway switch
- s2-s4: Aggregation switches (1 per floor)
- s5-s13: Edge/Access switches (1 per room, 9 total)
- Each edge switch: 2 publishers (1 anomaly + 1 normal)
- Total: 18 publishers + 1 broker/subscriber

Switch Count: 13
Host Count: 19 (1 broker + 18 publishers)
Total Hops: 3 (edge → aggregation → core)
"""

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time
import signal
import sys
import os
import subprocess

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
MQTT_DIR = os.path.join(PROJECT_ROOT, 'shared/mqtt')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'shared/config')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results/02-hierarchical-13switches')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Network Configuration for QoS Testing
# ENABLE_BANDWIDTH_LIMIT = False  # Set to True to enable bandwidth limits
ENABLE_BANDWIDTH_LIMIT = True  # Set to True to enable bandwidth limits
# LINK_BANDWIDTH_MBPS = 10     # 10 Mbps - Too high, no congestion
# LINK_BANDWIDTH_MBPS = 0.05   # 50 Kbps - HTB quantum warning, not reliable
# LINK_BANDWIDTH_MBPS = 0.03   # 30 Kbps - TOO LOW! HTB doesn't work (<100 Kbps)
LINK_BANDWIDTH_MBPS = 1        # 1 Mbps - Minimum for reliable HTB operation (need high msg rate for congestion)
ENABLE_QOS_QUEUES = True       # Set to True to configure OVS queues


class HierarchicalTopology:
    """Hierarchical 3-tier topology with 13 switches"""

    def __init__(self):
        self.net = None
        self.publishers = []

    def build(self):
        """Build the hierarchical Mininet topology"""
        setLogLevel('info')

        # Use TCLink if bandwidth limiting is enabled
        if ENABLE_BANDWIDTH_LIMIT:
            self.net = Mininet(controller=RemoteController, autoSetMacs=True, link=TCLink)
            info(f'*** Bandwidth limiting ENABLED: {LINK_BANDWIDTH_MBPS} Mbps per link\n')
        else:
            self.net = Mininet(controller=RemoteController, autoSetMacs=True)
            info('*** Bandwidth limiting DISABLED\n')

        info('*** Building Hierarchical 3-Tier Topology (13 switches)\n')

        # Add controller
        c0 = self.net.addController('c0', controller=RemoteController,
                                     ip='127.0.0.1', port=6633)

        # ==========================================
        # LAYER 1: Core Switch
        # ==========================================
        info('*** Adding Core Switch\n')
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')

        # Broker + Subscriber on core (shortened name to avoid interface name limit)
        # Using /16 subnet mask so all 10.0.x.x hosts can communicate
        h_broker = self.net.addHost('broker', ip='10.0.0.1/16')
        if ENABLE_BANDWIDTH_LIMIT:
            self.net.addLink(h_broker, s1, bw=LINK_BANDWIDTH_MBPS)
        else:
            self.net.addLink(h_broker, s1)

        # ==========================================
        # LAYER 2: Aggregation Switches (3)
        # ==========================================
        info('*** Adding Aggregation Switches\n')
        s2 = self.net.addSwitch('s2', protocols='OpenFlow13')  # Floor 1
        s3 = self.net.addSwitch('s3', protocols='OpenFlow13')  # Floor 2
        s4 = self.net.addSwitch('s4', protocols='OpenFlow13')  # Floor 3

        # Connect aggregation to core
        if ENABLE_BANDWIDTH_LIMIT:
            self.net.addLink(s2, s1, bw=LINK_BANDWIDTH_MBPS)
            self.net.addLink(s3, s1, bw=LINK_BANDWIDTH_MBPS)
            self.net.addLink(s4, s1, bw=LINK_BANDWIDTH_MBPS)
        else:
            self.net.addLink(s2, s1)
            self.net.addLink(s3, s1)
            self.net.addLink(s4, s1)

        # ==========================================
        # LAYER 3: Edge Switches (9) + Publishers
        # ==========================================
        info('*** Adding Edge Switches and Publishers\n')

        # Floor 1 Edge Switches (s5, s6, s7)
        edge_switches_f1 = []
        for i in range(5, 8):  # s5, s6, s7
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s2, bw=LINK_BANDWIDTH_MBPS)  # Connect to aggregation s2
            else:
                self.net.addLink(sw, s2)
            edge_switches_f1.append(sw)

        # Floor 2 Edge Switches (s8, s9, s10)
        edge_switches_f2 = []
        for i in range(8, 11):  # s8, s9, s10
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s3, bw=LINK_BANDWIDTH_MBPS)  # Connect to aggregation s3
            else:
                self.net.addLink(sw, s3)
            edge_switches_f2.append(sw)

        # Floor 3 Edge Switches (s11, s12, s13)
        edge_switches_f3 = []
        for i in range(11, 14):  # s11, s12, s13
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s4, bw=LINK_BANDWIDTH_MBPS)  # Connect to aggregation s4
            else:
                self.net.addLink(sw, s4)
            edge_switches_f3.append(sw)

        # ==========================================
        # Publishers: 2 per edge switch
        # ==========================================
        # Floor 1 subnet: 10.0.1.x (using /16 for connectivity)
        host_id = 1
        for idx, sw in enumerate(edge_switches_f1):
            # Anomaly publisher (shortened name: f1r1a = floor1 room1 anomaly)
            h_anomaly = self.net.addHost(f'f1r{idx+1}a',
                                          ip=f'10.0.1.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_anomaly, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_anomaly, sw)
            self.publishers.append({
                'host': h_anomaly,
                'type': 'anomaly',
                'floor': 1,
                'room': idx + 1,
                'switch': sw.name
            })
            host_id += 1

            # Normal publisher (shortened name: f1r1n = floor1 room1 normal)
            h_normal = self.net.addHost(f'f1r{idx+1}n',
                                         ip=f'10.0.1.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_normal, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_normal, sw)
            self.publishers.append({
                'host': h_normal,
                'type': 'normal',
                'floor': 1,
                'room': idx + 1,
                'switch': sw.name
            })
            host_id += 1

        # Floor 2 subnet: 10.0.2.x (using /16 for connectivity)
        host_id = 1
        for idx, sw in enumerate(edge_switches_f2):
            h_anomaly = self.net.addHost(f'f2r{idx+1}a',
                                          ip=f'10.0.2.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_anomaly, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_anomaly, sw)
            self.publishers.append({
                'host': h_anomaly,
                'type': 'anomaly',
                'floor': 2,
                'room': idx + 1,
                'switch': sw.name
            })
            host_id += 1

            h_normal = self.net.addHost(f'f2r{idx+1}n',
                                         ip=f'10.0.2.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_normal, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_normal, sw)
            self.publishers.append({
                'host': h_normal,
                'type': 'normal',
                'floor': 2,
                'room': idx + 1,
                'switch': sw.name
            })
            host_id += 1

        # Floor 3 subnet: 10.0.3.x (using /16 for connectivity)
        host_id = 1
        for idx, sw in enumerate(edge_switches_f3):
            h_anomaly = self.net.addHost(f'f3r{idx+1}a',
                                          ip=f'10.0.3.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_anomaly, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_anomaly, sw)
            self.publishers.append({
                'host': h_anomaly,
                'type': 'anomaly',
                'floor': 3,
                'room': idx + 1,
                'switch': sw.name
            })
            host_id += 1

            h_normal = self.net.addHost(f'f3r{idx+1}n',
                                         ip=f'10.0.3.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_normal, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_normal, sw)
            self.publishers.append({
                'host': h_normal,
                'type': 'normal',
                'floor': 3,
                'room': idx + 1,
                'switch': sw.name
            })
            host_id += 1

        info(f'*** Topology built: 13 switches, {len(self.publishers)} publishers\n')
        return self.net

    def configure_ovs_queues(self):
        """Configure OVS QoS queues for priority-based forwarding"""
        if not ENABLE_QOS_QUEUES:
            info('*** OVS QoS queues configuration DISABLED\n')
            return

        info('*** Configuring OVS QoS Queues...\n')

        # Configure queues for all switches
        switches = ['s1', 's2', 's3', 's4', 's5', 's6', 's7',
                    's8', 's9', 's10', 's11', 's12', 's13']

        for switch_name in switches:
            try:
                # Get all interfaces for this switch (except lo and the switch itself)
                result = subprocess.run(
                    f'ovs-vsctl list-ports {switch_name}',
                    shell=True, capture_output=True, text=True
                )

                if result.returncode != 0:
                    continue

                ports = result.stdout.strip().split('\n')

                for port in ports:
                    if not port:
                        continue

                    # Configure QoS with HTB (Hierarchical Token Bucket)
                    # Queue 1: High priority (70% min, 100% max) - for anomaly traffic
                    # Queue 2: Low priority (30% min, 50% max) - for normal traffic
                    max_rate = LINK_BANDWIDTH_MBPS * 1000000  # Convert to bps
                    queue1_min = int(max_rate * 0.7)  # 70% guaranteed
                    queue1_max = max_rate              # 100% max
                    queue2_min = int(max_rate * 0.3)  # 30% guaranteed
                    queue2_max = int(max_rate * 0.5)  # 50% max

                    cmd = (
                        f'ovs-vsctl -- set port {port} qos=@newqos '
                        f'-- --id=@newqos create qos type=linux-htb other-config:max-rate={max_rate} '
                        f'queues:1=@q1 queues:2=@q2 '
                        f'-- --id=@q1 create queue other-config:min-rate={queue1_min} other-config:max-rate={queue1_max} '
                        f'-- --id=@q2 create queue other-config:min-rate={queue2_min} other-config:max-rate={queue2_max}'
                    )

                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        info(f'  ✓ {switch_name}:{port} - Queue 1 (anomaly): {queue1_min/1000000:.1f}-{queue1_max/1000000:.1f} Mbps\n')
                        info(f'                     - Queue 2 (normal): {queue2_min/1000000:.1f}-{queue2_max/1000000:.1f} Mbps\n')

            except Exception as e:
                info(f'  ✗ Failed to configure {switch_name}: {str(e)}\n')

        info('*** OVS QoS configuration complete\n')

    def start(self):
        """Start the network"""
        if not self.net:
            raise RuntimeError("Topology not built. Call build() first.")

        self.net.start()
        info('*** Network started successfully\n')
        info(f'*** Total switches: 13 (1 core + 3 aggregation + 9 edge)\n')
        info(f'*** Total publishers: {len(self.publishers)}\n')
        info(f'*** Network depth: 3 hops (edge → agg → core)\n')

        # Wait for network to stabilize
        time.sleep(5)

        # Configure QoS queues if enabled
        if ENABLE_QOS_QUEUES:
            self.configure_ovs_queues()
            time.sleep(2)

    def start_mqtt_components(self):
        """Start MQTT broker, publishers, and subscriber"""
        h_broker = self.net.get('broker')

        info('*** Starting MQTT Broker on Core Switch\n')
        h_broker.cmd(f'mosquitto -v -c {CONFIG_DIR}/mosquitto.conf > {LOG_DIR}/mosquitto.log 2>&1 &')
        time.sleep(3)

        info('*** Starting Enhanced Subscriber on Core\n')
        # Pass configuration as environment variables
        env_vars = (
            f'ENABLE_BANDWIDTH_LIMIT={str(ENABLE_BANDWIDTH_LIMIT)} '
            f'LINK_BANDWIDTH_MBPS={LINK_BANDWIDTH_MBPS} '
            f'ENABLE_QOS_QUEUES={str(ENABLE_QOS_QUEUES)} '
            f'SCENARIO_NAME="02-hierarchical-13switches" '
            f'TOPOLOGY_TYPE="Hierarchical 3-Tier (13 switches, 19 hosts)" '
            f'NUM_SWITCHES=13 '
            f'NUM_PUBLISHERS={len(self.publishers)} '
        )
        h_broker.cmd(f'{env_vars}python3 {MQTT_DIR}/subscriber_enhanced.py > {LOG_DIR}/subscriber.log 2>&1 &')
        time.sleep(2)

        info(f'*** Starting {len(self.publishers)} Publishers\n')
        for idx, pub_info in enumerate(self.publishers):
            host = pub_info['host']
            pub_type = pub_info['type']
            floor = pub_info['floor']
            room = pub_info['room']

            # Set device name with floor and room info
            device_name = f"sensor_f{floor}r{room}_{pub_type}"

            if pub_type == 'anomaly':
                script = f'{MQTT_DIR}/publisher_anomaly.py'
            else:
                script = f'{MQTT_DIR}/publisher_normal.py'

            # Override DEVICE, BROKER_IP, and MSG_RATE env variables
            # MSG_RATE=20 means 20 messages per second (high rate for congestion testing)
            host.cmd(f'DEVICE={device_name} BROKER_IP=10.0.0.1 MSG_RATE=20 python3 {script} > {LOG_DIR}/publisher_{device_name}.log 2>&1 &')

            # Stagger publisher starts
            if idx % 3 == 0:
                time.sleep(1)

        info('*** All MQTT components started\n')

    def cleanup(self):
        """Stop all components and clean up"""
        info('*** Stopping MQTT components\n')

        # Stop all publishers
        for pub_info in self.publishers:
            host = pub_info['host']
            host.cmd('pkill -f publisher')

        # Stop broker and subscriber
        h_broker = self.net.get('broker')
        if h_broker:
            h_broker.cmd('pkill -TERM -f subscriber_enhanced')
            time.sleep(3)
            h_broker.cmd('pkill -f subscriber_enhanced')
            h_broker.cmd('pkill -f mosquitto')

        info('*** Stopping network\n')
        if self.net:
            self.net.stop()


def run_topology(duration_seconds=0):
    """Run the hierarchical topology"""
    topology = HierarchicalTopology()

    def signal_handler(sig, frame):
        topology.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        topology.build()
        topology.start()
        topology.start_mqtt_components()

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

    parser = argparse.ArgumentParser(description='Hierarchical 3-Tier Topology')
    parser.add_argument('--duration', type=int, default=0,
                       help='Duration in seconds (0 = run forever)')
    args = parser.parse_args()

    run_topology(args.duration)
