#!/usr/bin/env python3
"""
DSCP-Based Priority Topology - Scenario 05

Topology: 1 Core + 2 Agg + 4 Edge = 7 switches (SAMA seperti Scenario 03)
Publishers: 8 total (4 anomaly + 4 normal)

APPROACH: DSCP Tagging di IP Header
- Publisher SET DSCP value di IP header (DSCP 46 untuk anomaly, DSCP 0 untuk normal)
- Controller match DSCP value → Set Queue
- Lebih simple! Tidak perlu MAC learning, tidak perlu packet-in classification
- DSCP processing di data plane (switch langsung match DSCP)
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time
import os
import argparse
import subprocess

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))  # Scenario 05 directory
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results/05-dscp-qos-7switches')

# Ensure directories exist
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Network Configuration
ENABLE_BANDWIDTH_LIMIT = True
LINK_BANDWIDTH_MBPS = 0.5      # 0.5 Mbps - CREATE HIGH CONGESTION! (~96% utilization)
MSG_RATE = 50                   # 50 msg/s per publisher
                                # Calculation: 8 publishers × 50 msg/s × 150 bytes × 8 bits
                                #            = 480,000 bps = 480 Kbps
                                # Utilization: 480 Kbps / 500 Kbps = 96% (HIGH CONGESTION!)
                                # This will create clear queue differentiation ✅


class DSCPTopology:
    def __init__(self):
        self.net = None
        self.publishers = []

    def build(self):
        """Build topology - SAMA dengan Scenario 03"""
        info('*** Building DSCP-Based Topology (7 switches)\n')

        # Create network with remote controller
        self.net = Mininet(
            controller=RemoteController,
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=True,
            autoStaticArp=False
        )

        # Add controller
        c0 = self.net.addController(
            'c0',
            controller=RemoteController,
            ip='127.0.0.1',
            port=6633
        )

        info('*** Adding Core Switch\n')
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')

        # Add broker host at core
        h_broker = self.net.addHost('broker', ip='10.0.0.1/16')

        if ENABLE_BANDWIDTH_LIMIT:
            info(f'*** Bandwidth limiting ENABLED: {LINK_BANDWIDTH_MBPS} Mbps per link\n')
            self.net.addLink(h_broker, s1, bw=LINK_BANDWIDTH_MBPS)
        else:
            self.net.addLink(h_broker, s1)

        info('*** Adding Aggregation Switches\n')
        s2 = self.net.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.net.addSwitch('s3', protocols='OpenFlow13')

        # Core to Aggregation links
        if ENABLE_BANDWIDTH_LIMIT:
            self.net.addLink(s1, s2, bw=LINK_BANDWIDTH_MBPS)
            self.net.addLink(s1, s3, bw=LINK_BANDWIDTH_MBPS)
        else:
            self.net.addLink(s1, s2)
            self.net.addLink(s1, s3)

        info('*** Adding Edge Switches and Publishers\n')

        # Floor 1: s4, s5 (under s2)
        edge_switches_f1 = []
        for i in range(2):
            sw = self.net.addSwitch(f's{4+i}', protocols='OpenFlow13')
            edge_switches_f1.append(sw)
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(s2, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(s2, sw)

        # Floor 2: s6, s7 (under s3)
        edge_switches_f2 = []
        for i in range(2):
            sw = self.net.addSwitch(f's{6+i}', protocols='OpenFlow13')
            edge_switches_f2.append(sw)
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(s3, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(s3, sw)

        # Add publishers to Floor 1 (subnet 10.0.1.x)
        host_id = 1
        for idx, sw in enumerate(edge_switches_f1):
            # Anomaly publisher (odd IP)
            h_anomaly = self.net.addHost(f'f1r{idx+1}a', ip=f'10.0.1.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_anomaly, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_anomaly, sw)
            self.publishers.append({
                'host': h_anomaly,
                'type': 'anomaly',
                'floor': 1,
                'room': idx + 1
            })
            host_id += 1

            # Normal publisher (even IP)
            h_normal = self.net.addHost(f'f1r{idx+1}n', ip=f'10.0.1.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_normal, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_normal, sw)
            self.publishers.append({
                'host': h_normal,
                'type': 'normal',
                'floor': 1,
                'room': idx + 1
            })
            host_id += 1

        # Add publishers to Floor 2 (subnet 10.0.2.x)
        host_id = 1
        for idx, sw in enumerate(edge_switches_f2):
            # Anomaly publisher (odd IP)
            h_anomaly = self.net.addHost(f'f2r{idx+1}a', ip=f'10.0.2.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_anomaly, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_anomaly, sw)
            self.publishers.append({
                'host': h_anomaly,
                'type': 'anomaly',
                'floor': 2,
                'room': idx + 1
            })
            host_id += 1

            # Normal publisher (even IP)
            h_normal = self.net.addHost(f'f2r{idx+1}n', ip=f'10.0.2.{host_id}/16')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(h_normal, sw, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(h_normal, sw)
            self.publishers.append({
                'host': h_normal,
                'type': 'normal',
                'floor': 2,
                'room': idx + 1
            })
            host_id += 1

        info(f'*** Topology built: 7 switches, {len(self.publishers)} publishers\n')

        return self.net

    def configure_ovs_queues(self):
        """
        Configure OVS QoS queues untuk 5 Priority Levels

        Queue allocation (percentage of link bandwidth):
        - Queue 1 (DSCP 46 - EF):    60-80% (Very High Priority)
        - Queue 2 (DSCP 34 - AF41):  45-60% (High Priority)
        - Queue 3 (DSCP 26 - AF31):  30-45% (Medium Priority)
        - Queue 4 (DSCP 10 - AF11):  15-30% (Low Priority)
        - Queue 5 (DSCP 0  - BE):     5-15% (Best Effort)

        This MUST be done for queue mechanism to work!
        """
        info('*** Configuring OVS QoS Queues (5 levels)...\n')

        # Configure queues for all switches
        switches = ['s1', 's2', 's3', 's4', 's5', 's6', 's7']

        for switch_name in switches:
            try:
                # Get all ports for this switch
                result = subprocess.run(
                    f'ovs-vsctl list-ports {switch_name}',
                    shell=True, capture_output=True, text=True
                )

                if result.returncode != 0:
                    continue

                ports = result.stdout.strip().split('\n')

                for port in ports:
                    if not port or port.strip() == '':
                        continue

                    # Calculate bandwidth for each queue
                    max_rate = int(LINK_BANDWIDTH_MBPS * 1000000)  # Convert to bps

                    # Queue 1: DSCP 46 (EF - Very High) - 60-80%
                    q1_min = int(max_rate * 0.60)
                    q1_max = int(max_rate * 0.80)

                    # Queue 2: DSCP 34 (AF41 - High) - 45-60%
                    q2_min = int(max_rate * 0.45)
                    q2_max = int(max_rate * 0.60)

                    # Queue 3: DSCP 26 (AF31 - Medium) - 30-45%
                    q3_min = int(max_rate * 0.30)
                    q3_max = int(max_rate * 0.45)

                    # Queue 4: DSCP 10 (AF11 - Low) - 15-30%
                    q4_min = int(max_rate * 0.15)
                    q4_max = int(max_rate * 0.30)

                    # Queue 5: DSCP 0 (BE - Best Effort) - 5-15%
                    q5_min = int(max_rate * 0.05)
                    q5_max = int(max_rate * 0.15)

                    # Create QoS with 5 queues and ATTACH to port
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
        info(f'*** Total switches: 7 (1 core + 2 agg + 4 edge)\n')
        info(f'*** Total publishers: {len(self.publishers)}\n')
        info(f'*** Network depth: 3 hops (edge → agg → core)\n')

        # Wait for network to stabilize
        time.sleep(5)

        # Configure OVS queues (CRITICAL untuk priority mechanism!)
        if ENABLE_BANDWIDTH_LIMIT:
            self.configure_ovs_queues()

    def run_mqtt(self, duration=None):
        """Start MQTT broker, publishers, and subscriber"""
        info('*** Starting MQTT Broker on Core Switch\n')
        h_broker = self.net.get('broker')
        h_broker.cmd(f'mosquitto -c {PROJECT_ROOT}/shared/config/mosquitto.conf -d')
        time.sleep(2)

        info('*** Starting Enhanced Subscriber on Core\n')
        # Pass configuration as environment variables
        env_vars = (
            f'ENABLE_BANDWIDTH_LIMIT={str(ENABLE_BANDWIDTH_LIMIT)} '
            f'LINK_BANDWIDTH_MBPS={LINK_BANDWIDTH_MBPS} '
            f'ENABLE_QOS_QUEUES=True '  # Using OVS queues
            f'SCENARIO_NAME="05-dscp-qos" '
            f'TOPOLOGY_TYPE="DSCP-Based Hierarchical (7 switches, 8 publishers)" '
            f'NUM_SWITCHES=7 '
            f'NUM_PUBLISHERS={len(self.publishers)} '
        )
        h_broker.cmd(f'{env_vars}python3 {PROJECT_ROOT}/shared/mqtt/subscriber_enhanced.py > {LOG_DIR}/subscriber.log 2>&1 &')
        time.sleep(2)

        info('*** Starting Publishers\n')
        for idx, pub in enumerate(self.publishers):
            host = pub['host']
            pub_type = pub['type']
            floor = pub['floor']
            room = pub['room']

            device_name = f"sensor_f{floor}r{room}_{pub_type}"

            # IMPORTANT: Use DSCP publishers from scenario 05 directory!
            if pub_type == 'anomaly':
                script = f'{SCENARIO_DIR}/publisher_dscp46_veryhigh.py'
            else:
                script = f'{SCENARIO_DIR}/publisher_dscp0_besteffort.py'

            # Start publisher with DSCP tagging
            host.cmd(f'DEVICE={device_name} BROKER_IP=10.0.0.1 MSG_RATE={MSG_RATE} python3 {script} > {LOG_DIR}/publisher_{device_name}.log 2>&1 &')

            # Stagger publisher starts
            if idx % 2 == 0:
                time.sleep(0.5)

        info('*** All MQTT components started\n')

        # Run for specified duration
        if duration:
            info(f'*** Running for {duration} seconds...\n')
            time.sleep(duration)
            info('*** Stopping MQTT components\n')
            self.stop_mqtt()
        else:
            info('*** Press Ctrl+C to stop\n')
            try:
                CLI(self.net)
            except KeyboardInterrupt:
                info('\n*** Stopping MQTT components\n')
                self.stop_mqtt()

    def stop_mqtt(self):
        """Stop all MQTT components"""
        # Stop all publishers
        for pub in self.publishers:
            host = pub['host']
            host.cmd('pkill -f publisher')

        # Stop subscriber
        h_broker = self.net.get('broker')
        h_broker.cmd('pkill -f subscriber')
        h_broker.cmd('pkill -f mosquitto')

        time.sleep(2)

    def stop(self):
        """Stop the network"""
        if self.net:
            info('*** Stopping network\n')
            self.net.stop()


def main():
    parser = argparse.ArgumentParser(description='DSCP-Based Priority Topology - Scenario 05')
    parser.add_argument('--duration', type=int, help='Duration in seconds')
    args = parser.parse_args()

    setLogLevel('info')

    # Create and run DSCP topology
    topology = DSCPTopology()
    topology.build()
    topology.start()
    topology.run_mqtt(duration=args.duration)
    topology.stop()


if __name__ == '__main__':
    main()
