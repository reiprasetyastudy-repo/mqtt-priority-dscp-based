#!/usr/bin/env python3
"""
DSCP-Based Priority Topology - Scenario 06
Hierarchical 3-Tier with 13 Switches

Topology Structure:
                    ┌──────┐
                    │  s1  │ CORE (Broker here)
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

APPROACH: DSCP Tagging in IP Header with 5 Priority Levels
- Publishers SET DSCP value in IP header
- Controller matches DSCP value → Sets Queue
- No MAC learning needed, no packet-in classification
- DSCP processing in data plane (switch directly matches DSCP)

5 Priority Levels:
- DSCP 46 (EF - Very High)   → Queue 1 (60-80%)
- DSCP 34 (AF41 - High)      → Queue 2 (45-60%)
- DSCP 26 (AF31 - Medium)    → Queue 3 (30-45%)
- DSCP 10 (AF11 - Low)       → Queue 4 (15-30%)
- DSCP 0  (BE - Best Effort) → Queue 5 (5-15%)

Switch Count: 13
Host Count: 19 (1 broker + 18 publishers)
Total Hops: 3 (edge → aggregation → core)
"""

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time
import signal
import sys
import os
import subprocess
import argparse

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results/06-dscp-qos-13switches')

# LOG_DIR will be set dynamically based on current working directory (results/run_xxx/)
LOG_DIR = None  # Will be set in start_mqtt_components()

# Ensure directories exist
os.makedirs(RESULTS_DIR, exist_ok=True)

# Network Configuration
ENABLE_BANDWIDTH_LIMIT = True
LINK_BANDWIDTH_MBPS = 0.5      # 0.5 Mbps - CREATE HIGH CONGESTION!
MSG_RATE = 50                   # 50 msg/s per publisher
                                # Calculation: 18 publishers × 50 msg/s × 150 bytes × 8 bits
                                #            = 1,080,000 bps = 1.08 Mbps
                                # Utilization: 1080 Kbps / 500 Kbps = 216% (VERY HIGH CONGESTION!)


class DSCPHierarchicalTopology:
    """Hierarchical 3-tier topology with 13 switches and DSCP-based QoS"""

    def __init__(self):
        self.net = None
        self.publishers = []

    def build(self):
        """Build the hierarchical Mininet topology"""
        setLogLevel('info')

        # Use TCLink for bandwidth limiting
        if ENABLE_BANDWIDTH_LIMIT:
            self.net = Mininet(controller=RemoteController, autoSetMacs=True, link=TCLink)
            info(f'*** Bandwidth limiting ENABLED: {LINK_BANDWIDTH_MBPS} Mbps per link\n')
        else:
            self.net = Mininet(controller=RemoteController, autoSetMacs=True)
            info('*** Bandwidth limiting DISABLED\n')

        info('*** Building Hierarchical 3-Tier Topology with DSCP QoS (13 switches)\n')

        # Add controller
        c0 = self.net.addController('c0', controller=RemoteController,
                                     ip='127.0.0.1', port=6633)

        # ==========================================
        # LAYER 1: Core Switch
        # ==========================================
        info('*** Adding Core Switch\n')
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')

        # Broker + Subscriber on core
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
                self.net.addLink(sw, s2, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(sw, s2)
            edge_switches_f1.append(sw)

        # Floor 2 Edge Switches (s8, s9, s10)
        edge_switches_f2 = []
        for i in range(8, 11):  # s8, s9, s10
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s3, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(sw, s3)
            edge_switches_f2.append(sw)

        # Floor 3 Edge Switches (s11, s12, s13)
        edge_switches_f3 = []
        for i in range(11, 14):  # s11, s12, s13
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s4, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(sw, s4)
            edge_switches_f3.append(sw)

        # ==========================================
        # Publishers: 2 per edge switch
        # ==========================================
        # Floor 1 subnet: 10.0.1.x (using /16 for connectivity)
        host_id = 1
        for idx, sw in enumerate(edge_switches_f1):
            # Anomaly publisher
            h_anomaly = self.net.addHost(f'f1r{idx+1}a', ip=f'10.0.1.{host_id}/16')
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

            # Normal publisher
            h_normal = self.net.addHost(f'f1r{idx+1}n', ip=f'10.0.1.{host_id}/16')
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

        # Floor 2 subnet: 10.0.2.x
        host_id = 1
        for idx, sw in enumerate(edge_switches_f2):
            h_anomaly = self.net.addHost(f'f2r{idx+1}a', ip=f'10.0.2.{host_id}/16')
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

            h_normal = self.net.addHost(f'f2r{idx+1}n', ip=f'10.0.2.{host_id}/16')
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

        # Floor 3 subnet: 10.0.3.x
        host_id = 1
        for idx, sw in enumerate(edge_switches_f3):
            h_anomaly = self.net.addHost(f'f3r{idx+1}a', ip=f'10.0.3.{host_id}/16')
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

            h_normal = self.net.addHost(f'f3r{idx+1}n', ip=f'10.0.3.{host_id}/16')
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
        """Configure OVS QoS queues with 5 priority levels for DSCP-based forwarding"""
        if not ENABLE_BANDWIDTH_LIMIT:
            info('*** OVS QoS queues configuration DISABLED\n')
            return

        info('*** Configuring OVS QoS Queues (5 priority levels)...\n')

        # Configure queues for all 13 switches
        switches = ['s1', 's2', 's3', 's4', 's5', 's6', 's7',
                    's8', 's9', 's10', 's11', 's12', 's13']

        for switch_name in switches:
            try:
                # Get all interfaces for this switch
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

                    # Configure QoS with HTB (5 queues for 5 DSCP levels)
                    max_rate = int(LINK_BANDWIDTH_MBPS * 1000000)  # Convert to bps

                    # Queue bandwidth allocation (min-max percentages)
                    q1_min = int(max_rate * 0.60)  # 60% min
                    q1_max = int(max_rate * 0.80)  # 80% max
                    q2_min = int(max_rate * 0.45)  # 45% min
                    q2_max = int(max_rate * 0.60)  # 60% max
                    q3_min = int(max_rate * 0.30)  # 30% min
                    q3_max = int(max_rate * 0.45)  # 45% max
                    q4_min = int(max_rate * 0.15)  # 15% min
                    q4_max = int(max_rate * 0.30)  # 30% max
                    q5_min = int(max_rate * 0.05)  # 5% min
                    q5_max = int(max_rate * 0.15)  # 15% max

                    cmd = (
                        f'ovs-vsctl -- set port {port} qos=@newqos '
                        f'-- --id=@newqos create qos type=linux-htb other-config:max-rate={max_rate} '
                        f'queues:1=@q1 queues:2=@q2 queues:3=@q3 queues:4=@q4 queues:5=@q5 '
                        f'-- --id=@q1 create queue other-config:min-rate={q1_min} other-config:max-rate={q1_max} '
                        f'-- --id=@q2 create queue other-config:min-rate={q2_min} other-config:max-rate={q2_max} '
                        f'-- --id=@q3 create queue other-config:min-rate={q3_min} other-config:max-rate={q3_max} '
                        f'-- --id=@q4 create queue other-config:min-rate={q4_min} other-config:max-rate={q4_max} '
                        f'-- --id=@q5 create queue other-config:min-rate={q5_min} other-config:max-rate={q5_max}'
                    )

                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                    if result.returncode == 0:
                        info(f'  ✓ {switch_name}:{port}\n')
                        info(f'      Q1 (DSCP 46): {q1_min/1000:.0f}-{q1_max/1000:.0f} Kbps\n')
                        info(f'      Q2 (DSCP 34): {q2_min/1000:.0f}-{q2_max/1000:.0f} Kbps\n')
                        info(f'      Q3 (DSCP 26): {q3_min/1000:.0f}-{q3_max/1000:.0f} Kbps\n')
                        info(f'      Q4 (DSCP 10): {q4_min/1000:.0f}-{q4_max/1000:.0f} Kbps\n')
                        info(f'      Q5 (DSCP 0):  {q5_min/1000:.0f}-{q5_max/1000:.0f} Kbps\n')
                    else:
                        info(f'  ✗ {switch_name}:{port} - Failed: {result.stderr}\n')

            except Exception as e:
                info(f'  ✗ Failed to configure {switch_name}: {str(e)}\n')

        info('*** OVS QoS configuration complete (5 queues)\n')

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

        # Configure OVS queues (CRITICAL for priority mechanism!)
        if ENABLE_BANDWIDTH_LIMIT:
            self.configure_ovs_queues()
            time.sleep(2)

    def start_mqtt_components(self, duration=None):
        """Start MQTT broker, publishers, and subscriber"""
        global LOG_DIR
        
        # Set LOG_DIR based on current working directory (should be results/run_xxx/)
        LOG_DIR = os.path.join(os.getcwd(), 'logs')
        os.makedirs(LOG_DIR, exist_ok=True)
        info(f'*** Logs will be saved to: {LOG_DIR}\n')
        
        info('*** Starting MQTT Broker on Core Switch\n')
        h_broker = self.net.get('broker')
        h_broker.cmd(f'mosquitto -c {PROJECT_ROOT}/shared/config/mosquitto.conf -d')
        time.sleep(3)

        info('*** Starting Enhanced Subscriber on Core\n')
        env_vars = (
            f'ENABLE_BANDWIDTH_LIMIT={str(ENABLE_BANDWIDTH_LIMIT)} '
            f'LINK_BANDWIDTH_MBPS={LINK_BANDWIDTH_MBPS} '
            f'ENABLE_QOS_QUEUES=True '
            f'SCENARIO_NAME="06-dscp-qos-13switches" '
            f'TOPOLOGY_TYPE="DSCP Hierarchical 3-Tier (13 switches, 19 hosts)" '
            f'NUM_SWITCHES=13 '
            f'NUM_PUBLISHERS={len(self.publishers)} '
        )
        h_broker.cmd(f'{env_vars}python3 {PROJECT_ROOT}/shared/mqtt/subscriber_enhanced.py > {LOG_DIR}/subscriber.log 2>&1 &')
        time.sleep(2)

        info(f'*** Starting {len(self.publishers)} Publishers with DSCP tagging\n')
        for idx, pub_info in enumerate(self.publishers):
            host = pub_info['host']
            pub_type = pub_info['type']
            floor = pub_info['floor']
            room = pub_info['room']

            device_name = f"sensor_f{floor}r{room}_{pub_type}"

            # IMPORTANT: Use DSCP publishers from scenario 06 directory!
            if pub_type == 'anomaly':
                script = f'{SCENARIO_DIR}/publisher_dscp46_veryhigh.py'
            else:
                script = f'{SCENARIO_DIR}/publisher_dscp0_besteffort.py'

            # Start publisher with DSCP tagging
            host.cmd(f'DEVICE={device_name} BROKER_IP=10.0.0.1 MSG_RATE={MSG_RATE} python3 {script} > {LOG_DIR}/publisher_{device_name}.log 2>&1 &')

            # Stagger publisher starts
            if idx % 3 == 0:
                time.sleep(1)

        info('*** All MQTT components started\n')
        info(f'*** Publisher logs: {LOG_DIR}/publisher_*.log\n')
        info(f'*** Subscriber log: {LOG_DIR}/subscriber.log\n')

        if duration:
            info(f'*** Publishers will send for {duration} seconds...\n')
            info(f'*** Total experiment time: {duration * 2}s ({duration}s send + {duration}s drain)\n')
            time.sleep(duration)
            
            # Stop publishers first
            info('*** Stopping publishers...\n')
            for pub_info in self.publishers:
                host = pub_info['host']
                host.cmd('pkill -f publisher')
            
            # Wait for in-flight messages to arrive (drain time = duration)
            info(f'*** Waiting {duration}s for in-flight messages (drain time)...\n')
            time.sleep(duration)
            
            info('*** Stopping subscriber and broker...\n')
            self.stop_mqtt()
        else:
            info('*** Press Ctrl+C to stop\n')
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                info('\n*** Stopping MQTT components\n')
                self.stop_mqtt()

    def stop_mqtt(self):
        """Stop subscriber and broker (publishers already stopped)"""
        h_broker = self.net.get('broker')
        if h_broker:
            info('  Stopping subscriber (waiting for summary generation)...\n')
            h_broker.cmd('pkill -TERM -f subscriber_enhanced')
            time.sleep(30)
            h_broker.cmd('pkill -f subscriber_enhanced')
            h_broker.cmd('pkill -f mosquitto')

        time.sleep(2)

    def stop(self):
        """Stop the network"""
        if self.net:
            info('*** Stopping network\n')
            self.net.stop()


def main():
    """Main function to run the DSCP hierarchical topology"""
    parser = argparse.ArgumentParser(description='DSCP-Based Hierarchical Topology - Scenario 06')
    parser.add_argument('--duration', type=int, help='Duration in seconds')
    args = parser.parse_args()

    setLogLevel('info')

    topology = DSCPHierarchicalTopology()

    def signal_handler(sig, frame):
        topology.stop_mqtt()
        topology.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        topology.build()
        topology.start()
        topology.start_mqtt_components(duration=args.duration)
        topology.stop()
    except KeyboardInterrupt:
        topology.stop_mqtt()
        topology.stop()
    except Exception as e:
        info(f'*** Error: {e}\n')
        topology.stop_mqtt()
        topology.stop()
        raise


if __name__ == '__main__':
    main()
