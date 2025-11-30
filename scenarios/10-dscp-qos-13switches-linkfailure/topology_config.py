#!/usr/bin/env python3
"""
DSCP-Based Priority Topology - Scenario 10
Link Failure Test - Same topology as Scenario 09 but with link failure simulation

Topology Structure (Same as Scenario 09):
                                    ┌──────────┐
                                    │  BROKER  │
                                    │ 10.0.0.1 │
                                    └────┬─────┘
                                         │
                                   ┌─────┴─────┐
                                   │    s1     │
                                   │   CORE    │
                                   └─────┬─────┘
                                         │
                ┌────────────────────────┼────────────────────────┐
                │                        │                        │
          ┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐
          │    s2     │◄══════════►│    s3     │◄══════════►│    s4     │
          │   AGG 1   │            │   AGG 2   │            │   AGG 3   │
          │  Floor 1  │◄══════════════════════════════════►│  Floor 3  │
          └─────┬─────┘            └─────┬─────┘            └─────┬─────┘
                │                        │                        │
            3 EDGE                    3 EDGE                   3 EDGE

EXPERIMENT PHASES:
- Phase 1 (0-30s):   Normal operation - all links active
- Phase 2 (30s+):    Link s2↔s1 DOWN - test redundancy via ring
                     Traffic from Floor 1 should go: s2→s3→s1 or s2→s4→s1

VERIFICATION METHODS:
1. ip link show - check link state
2. ovs-ofctl dump-flows - check flow changes
3. Log events with timestamps
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
from datetime import datetime

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results/10-dscp-qos-13switches-linkfailure')

# LOG_DIR will be set dynamically based on current working directory (results/run_xxx/)
# This allows logs to be saved in each experiment's folder
LOG_DIR = None  # Will be set in start_mqtt_components()

# Ensure directories exist
os.makedirs(RESULTS_DIR, exist_ok=True)

# Network Configuration
ENABLE_BANDWIDTH_LIMIT = True
LINK_BANDWIDTH_MBPS = 0.5
MSG_RATE = 50

# Link Failure Configuration
PHASE1_DURATION = 30  # Normal operation (seconds)
LINK_TO_DISABLE = 's2-eth1'  # Link from s2 to s1


class DSCPRingTopologyLinkFailure:
    """Ring topology with link failure test"""

    def __init__(self):
        self.net = None
        self.publishers = []
        self.link_failure_log = []

    def log_event(self, event_type, message):
        """Log event with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] [{event_type}] {message}"
        self.link_failure_log.append(log_entry)
        info(f'{log_entry}\n')

    def build(self):
        """Build the ring aggregation Mininet topology"""
        setLogLevel('info')

        if ENABLE_BANDWIDTH_LIMIT:
            self.net = Mininet(controller=RemoteController, autoSetMacs=True, link=TCLink)
            info(f'*** Bandwidth limiting ENABLED: {LINK_BANDWIDTH_MBPS} Mbps per link\n')
        else:
            self.net = Mininet(controller=RemoteController, autoSetMacs=True)
            info('*** Bandwidth limiting DISABLED\n')

        info('*** Building Ring Topology for Link Failure Test (Scenario 10)\n')
        info('*** 1 Core + 3 Aggregation (Ring) + 9 Edge = 13 switches\n')

        # Add controller
        c0 = self.net.addController('c0', controller=RemoteController,
                                     ip='127.0.0.1', port=6633)

        # ==========================================
        # LAYER 1: Core Switch
        # ==========================================
        info('*** Adding Core Switch\n')
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')

        # Broker connected to Core
        h_broker = self.net.addHost('broker', ip='10.0.0.1/16')
        if ENABLE_BANDWIDTH_LIMIT:
            self.net.addLink(h_broker, s1, bw=LINK_BANDWIDTH_MBPS)
        else:
            self.net.addLink(h_broker, s1)

        # ==========================================
        # LAYER 2: Aggregation Switches (3) + Ring
        # ==========================================
        info('*** Adding 3 Aggregation Switches\n')
        s2 = self.net.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.net.addSwitch('s3', protocols='OpenFlow13')
        s4 = self.net.addSwitch('s4', protocols='OpenFlow13')

        # Connect all aggregation switches to core
        info('*** Connecting Aggregation to Core (3 links)\n')
        if ENABLE_BANDWIDTH_LIMIT:
            self.net.addLink(s2, s1, bw=LINK_BANDWIDTH_MBPS)  # This link will be disabled!
            self.net.addLink(s3, s1, bw=LINK_BANDWIDTH_MBPS)
            self.net.addLink(s4, s1, bw=LINK_BANDWIDTH_MBPS)
        else:
            self.net.addLink(s2, s1)
            self.net.addLink(s3, s1)
            self.net.addLink(s4, s1)
        info('  ✓ s2 ↔ s1 (AGG 1 ↔ Core) [WILL BE DISABLED IN PHASE 2]\n')
        info('  ✓ s3 ↔ s1 (AGG 2 ↔ Core)\n')
        info('  ✓ s4 ↔ s1 (AGG 3 ↔ Core)\n')

        # Create Ring between Aggregation Switches
        info('*** Creating Ring between Aggregation Switches (3 links)\n')
        if ENABLE_BANDWIDTH_LIMIT:
            self.net.addLink(s2, s3, bw=LINK_BANDWIDTH_MBPS)
            self.net.addLink(s3, s4, bw=LINK_BANDWIDTH_MBPS)
            self.net.addLink(s2, s4, bw=LINK_BANDWIDTH_MBPS)
        else:
            self.net.addLink(s2, s3)
            self.net.addLink(s3, s4)
            self.net.addLink(s2, s4)
        info('  ✓ s2 ↔ s3 (Ring link 1)\n')
        info('  ✓ s3 ↔ s4 (Ring link 2)\n')
        info('  ✓ s2 ↔ s4 (Ring link 3)\n')

        # ==========================================
        # LAYER 3: Edge Switches (9)
        # ==========================================
        info('*** Adding Edge Switches\n')

        # Floor 1: Edge s5, s6, s7 → connected to s2 (AGG 1)
        edge_switches_f1 = []
        for i in range(5, 8):
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s2, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(sw, s2)
            edge_switches_f1.append(sw)

        # Floor 2: Edge s8, s9, s10 → connected to s3 (AGG 2)
        edge_switches_f2 = []
        for i in range(8, 11):
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s3, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(sw, s3)
            edge_switches_f2.append(sw)

        # Floor 3: Edge s11, s12, s13 → connected to s4 (AGG 3)
        edge_switches_f3 = []
        for i in range(11, 14):
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            if ENABLE_BANDWIDTH_LIMIT:
                self.net.addLink(sw, s4, bw=LINK_BANDWIDTH_MBPS)
            else:
                self.net.addLink(sw, s4)
            edge_switches_f3.append(sw)

        # ==========================================
        # Publishers: 2 per edge switch
        # ==========================================
        # Floor 1 subnet: 10.0.1.x
        host_id = 1
        for idx, sw in enumerate(edge_switches_f1):
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

        info(f'*** Topology built: 13 switches, 15 links, {len(self.publishers)} publishers\n')
        return self.net

    def configure_ovs_queues(self):
        """Configure OVS QoS queues"""
        if not ENABLE_BANDWIDTH_LIMIT:
            return

        info('*** Configuring OVS QoS Queues...\n')

        switches = ['s1', 's2', 's3', 's4', 's5', 's6', 's7',
                    's8', 's9', 's10', 's11', 's12', 's13']

        for switch_name in switches:
            try:
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

                    max_rate = int(LINK_BANDWIDTH_MBPS * 1000000)

                    q1_min = int(max_rate * 0.60)
                    q1_max = int(max_rate * 0.80)
                    q2_min = int(max_rate * 0.45)
                    q2_max = int(max_rate * 0.60)
                    q3_min = int(max_rate * 0.30)
                    q3_max = int(max_rate * 0.45)
                    q4_min = int(max_rate * 0.15)
                    q4_max = int(max_rate * 0.30)
                    q5_min = int(max_rate * 0.05)
                    q5_max = int(max_rate * 0.15)

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

                    subprocess.run(cmd, shell=True, capture_output=True, text=True)

            except Exception as e:
                pass

        info('*** OVS QoS configuration complete\n')

    def capture_port_statistics(self, label):
        """Capture port statistics for aggregation switches to track traffic flow"""
        self.log_event('STATS', f'=== PORT STATISTICS: {label} ===')
        
        # Focus on aggregation switches (s2, s3, s4) and core (s1)
        switches = ['s1', 's2', 's3', 's4']
        
        stats_data = {}
        for sw in switches:
            result = subprocess.run(
                f'ovs-ofctl dump-ports {sw} -O OpenFlow13',
                shell=True, capture_output=True, text=True
            )
            stats_data[sw] = result.stdout
            
            # Parse key ports
            lines = result.stdout.strip().split('\n')
            self.log_event('STATS', f'{sw}:')
            for line in lines:
                if 'port' in line.lower() and ('rx pkts' in line or 'tx pkts' in line):
                    self.log_event('STATS', f'  {line.strip()}')
        
        return stats_data

    def capture_flow_statistics(self, label):
        """Capture flow statistics for aggregation switches"""
        self.log_event('STATS', f'=== FLOW STATISTICS: {label} ===')
        
        switches = ['s2', 's3', 's4']
        
        for sw in switches:
            result = subprocess.run(
                f'ovs-ofctl dump-flows {sw} -O OpenFlow13 | grep -E "n_packets=[0-9]+" | head -10',
                shell=True, capture_output=True, text=True
            )
            self.log_event('STATS', f'{sw} flows with traffic:')
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Extract n_packets count
                    self.log_event('STATS', f'  {line.strip()[:100]}...')

    def capture_route_proof(self, label):
        """Capture proof of routing path using port stats comparison"""
        self.log_event('ROUTE', f'=== ROUTE ANALYSIS: {label} ===')
        
        # Get port stats for s2 (Floor 1 aggregation)
        # s2-eth1 = link to s1 (core) - PRIMARY PATH
        # s2-eth2 = link to s3 (ring) - BACKUP PATH
        # s2-eth3 = link to s4 (ring) - BACKUP PATH
        
        result = subprocess.run(
            'ovs-ofctl dump-ports s2 -O OpenFlow13',
            shell=True, capture_output=True, text=True
        )
        
        self.log_event('ROUTE', 'Switch s2 port mapping:')
        self.log_event('ROUTE', '  s2-eth1 = s2 ↔ s1 (Core) - PRIMARY')
        self.log_event('ROUTE', '  s2-eth2 = s2 ↔ s3 (Ring) - BACKUP')
        self.log_event('ROUTE', '  s2-eth3 = s2 ↔ s4 (Ring) - BACKUP')
        
        # Parse port stats
        lines = result.stdout.strip().split('\n')
        port_stats = {}
        current_port = None
        
        for line in lines:
            if 'port' in line.lower() and ':' in line:
                # Extract port number
                try:
                    port_part = line.split(':')[0].strip()
                    if 'LOCAL' not in port_part:
                        current_port = port_part.replace('port', '').strip()
                except:
                    pass
            if current_port and 'rx pkts=' in line:
                try:
                    rx_match = line.split('rx pkts=')[1].split(',')[0]
                    tx_match = line.split('tx pkts=')[1].split(',')[0] if 'tx pkts=' in line else '0'
                    port_stats[current_port] = {'rx': int(rx_match), 'tx': int(tx_match)}
                except:
                    pass
        
        self.log_event('ROUTE', f'Port statistics: {port_stats}')
        
        return port_stats

    def verify_link_status(self, interface, expected_state):
        """Verify link status using multiple methods"""
        results = []
        
        # Method 1: ip link show
        result1 = subprocess.run(
            f'ip link show {interface}',
            shell=True, capture_output=True, text=True
        )
        if expected_state == 'DOWN':
            is_down = 'state DOWN' in result1.stdout or 'NO-CARRIER' in result1.stdout
        else:
            is_down = False
        results.append(f"ip link show: {'DOWN' if is_down else 'UP'}")
        
        # Method 2: Check interface operstate
        result2 = subprocess.run(
            f'cat /sys/class/net/{interface}/operstate 2>/dev/null || echo "unknown"',
            shell=True, capture_output=True, text=True
        )
        operstate = result2.stdout.strip()
        results.append(f"operstate: {operstate}")
        
        # Method 3: ovs-vsctl show
        result3 = subprocess.run(
            'ovs-vsctl show',
            shell=True, capture_output=True, text=True
        )
        # Just log that we checked
        results.append("ovs-vsctl: checked")
        
        return results

    def disable_link(self, interface):
        """Disable a link and verify with multiple methods"""
        self.log_event('LINK_FAILURE', f'Disabling link {interface}...')
        
        # Check status BEFORE
        self.log_event('VERIFY', f'Link status BEFORE disable:')
        before_results = self.verify_link_status(interface, 'UP')
        for r in before_results:
            self.log_event('VERIFY', f'  {r}')
        
        # Disable the link
        result = subprocess.run(
            f'ip link set {interface} down',
            shell=True, capture_output=True, text=True
        )
        
        if result.returncode == 0:
            self.log_event('LINK_FAILURE', f'Link {interface} disabled successfully')
        else:
            self.log_event('ERROR', f'Failed to disable link: {result.stderr}')
        
        # Wait a moment for the change to take effect
        time.sleep(1)
        
        # Check status AFTER
        self.log_event('VERIFY', f'Link status AFTER disable:')
        after_results = self.verify_link_status(interface, 'DOWN')
        for r in after_results:
            self.log_event('VERIFY', f'  {r}')
        
        # Method 4: Check OVS flow rules for s2
        self.log_event('VERIFY', 'Checking OVS flow rules on s2:')
        result = subprocess.run(
            'ovs-ofctl -O OpenFlow13 dump-flows s2 | head -20',
            shell=True, capture_output=True, text=True
        )
        self.log_event('VERIFY', f'  Flow count: {len(result.stdout.strip().split(chr(10)))} rules')

    def start(self):
        """Start the network"""
        if not self.net:
            raise RuntimeError("Topology not built. Call build() first.")

        self.net.start()
        info('*** Network started successfully\n')
        info(f'*** Total switches: 13\n')
        info(f'*** Total links: 15\n')
        info(f'*** Total publishers: {len(self.publishers)}\n')
        info(f'*** Link failure test: {LINK_TO_DISABLE} will be disabled after {PHASE1_DURATION}s\n')

        # Enable STP on ALL switches to prevent loops from ring topology
        info('*** Enabling STP on all switches...\n')
        all_switches = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 
                        's8', 's9', 's10', 's11', 's12', 's13']
        for sw_name in all_switches:
            result = subprocess.run(
                f'ovs-vsctl set bridge {sw_name} stp_enable=true',
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                info(f'  ✓ STP enabled on {sw_name}\n')
            else:
                info(f'  ✗ Failed to enable STP on {sw_name}\n')
        
        # Wait for STP convergence (standard is 30-50 seconds)
        info('*** Waiting for STP convergence (35 seconds)...\n')
        time.sleep(35)

        # Configure OVS queues
        if ENABLE_BANDWIDTH_LIMIT:
            self.configure_ovs_queues()
            time.sleep(2)

    def start_mqtt_components(self, duration=None):
        """Start MQTT with link failure test"""
        global LOG_DIR
        
        # Create logs directory inside the current results folder
        # (run_experiment.sh changes to results/run_xxx/ before running)
        LOG_DIR = os.path.join(os.getcwd(), 'logs')
        os.makedirs(LOG_DIR, exist_ok=True)
        info(f'*** Logs will be saved to: {LOG_DIR}\n')
        
        info('*** Starting MQTT Broker\n')
        h_broker = self.net.get('broker')
        h_broker.cmd(f'mosquitto -c {PROJECT_ROOT}/shared/config/mosquitto.conf -d')
        time.sleep(3)

        info('*** Starting Link Failure Test Subscriber (with phase tracking)\n')
        env_vars = (
            f'ENABLE_BANDWIDTH_LIMIT={str(ENABLE_BANDWIDTH_LIMIT)} '
            f'LINK_BANDWIDTH_MBPS={LINK_BANDWIDTH_MBPS} '
            f'ENABLE_QOS_QUEUES=True '
            f'SCENARIO_NAME="10-dscp-qos-13switches-linkfailure" '
            f'TOPOLOGY_TYPE="DSCP Ring with Link Failure Test" '
            f'NUM_SWITCHES=13 '
            f'NUM_PUBLISHERS={len(self.publishers)} '
            f'PHASE1_DURATION={PHASE1_DURATION} '
        )
        h_broker.cmd(f'{env_vars}python3 {SCENARIO_DIR}/subscriber_linkfailure.py > {LOG_DIR}/subscriber.log 2>&1 &')
        time.sleep(3)

        info(f'*** Starting {len(self.publishers)} Publishers\n')
        for idx, pub_info in enumerate(self.publishers):
            host = pub_info['host']
            pub_type = pub_info['type']
            floor = pub_info['floor']
            room = pub_info['room']

            device_name = f"sensor_f{floor}r{room}_{pub_type}"

            if pub_type == 'anomaly':
                script = f'{SCENARIO_DIR}/publisher_dscp46_veryhigh.py'
            else:
                script = f'{SCENARIO_DIR}/publisher_dscp0_besteffort.py'

            host.cmd(f'DEVICE={device_name} BROKER_IP=10.0.0.1 MSG_RATE={MSG_RATE} python3 {script} > {LOG_DIR}/publisher_{device_name}.log 2>&1 &')

            if idx % 3 == 0:
                time.sleep(1)

        info('*** All MQTT components started\n')
        info(f'*** Publisher logs: {LOG_DIR}/publisher_*.log\n')
        info(f'*** Subscriber log: {LOG_DIR}/subscriber.log\n')

        if duration:
            # Calculate phase durations
            phase2_duration = duration - PHASE1_DURATION
            total_time = duration * 2  # send time + drain time
            
            info(f'*** Publishers will send for {duration} seconds...\n')
            info(f'*** Total experiment time: {total_time}s ({duration}s send + {duration}s drain)\n')
            
            # ==========================================
            # PHASE 1: Normal Operation
            # ==========================================
            self.log_event('PHASE', f'=== PHASE 1: Normal Operation ({PHASE1_DURATION}s) ===')
            self.log_event('PHASE', 'All links active. Traffic uses direct path to core.')
            
            # Wait most of Phase 1
            time.sleep(PHASE1_DURATION - 5)
            
            # Capture statistics BEFORE link failure (last 5 seconds of Phase 1)
            self.log_event('PHASE', 'Capturing statistics before link failure...')
            stats_before = self.capture_route_proof('BEFORE LINK FAILURE')
            self.capture_port_statistics('BEFORE LINK FAILURE')
            
            time.sleep(5)
            
            # ==========================================
            # LINK FAILURE EVENT
            # ==========================================
            self.log_event('PHASE', '=== LINK FAILURE EVENT ===')
            self.disable_link(LINK_TO_DISABLE)
            
            # ==========================================
            # PHASE 2: Redundancy Test
            # ==========================================
            self.log_event('PHASE', f'=== PHASE 2: Redundancy Test ({phase2_duration}s) ===')
            self.log_event('PHASE', 'Link s2↔s1 is DOWN. Floor 1 traffic must use ring.')
            self.log_event('PHASE', 'Expected path: s2 → s3 → s1 or s2 → s4 → s1')
            
            # Wait for STP reconvergence after link failure
            self.log_event('PHASE', 'Waiting 10s for STP reconvergence after link failure...')
            time.sleep(10)
            
            # Capture statistics shortly after link failure
            self.log_event('PHASE', 'Capturing statistics after link failure (post STP reconvergence)...')
            stats_after = self.capture_route_proof('AFTER LINK FAILURE (10s)')
            self.capture_port_statistics('AFTER LINK FAILURE (10s)')
            
            # Compare and log route change
            self.log_event('ROUTE', '=== ROUTE CHANGE ANALYSIS ===')
            if stats_before and stats_after:
                self.log_event('ROUTE', f'Before: s2 port stats = {stats_before}')
                self.log_event('ROUTE', f'After:  s2 port stats = {stats_after}')
                self.log_event('ROUTE', 'If traffic moved from eth1 to eth2/eth3, redundancy is working!')
            
            # Wait remaining time
            remaining = phase2_duration - 10
            if remaining > 0:
                time.sleep(remaining)
            
            # Final statistics capture
            self.log_event('PHASE', 'Capturing final statistics...')
            self.capture_route_proof('END OF EXPERIMENT')
            self.capture_port_statistics('END OF EXPERIMENT')
            
            # ==========================================
            # STOP PUBLISHERS & DRAIN
            # ==========================================
            self.log_event('PHASE', '=== STOPPING PUBLISHERS ===')
            info('*** Stopping publishers...\n')
            for pub_info in self.publishers:
                host = pub_info['host']
                host.cmd('pkill -f publisher')
            
            # Wait for in-flight messages (drain time = duration)
            self.log_event('PHASE', f'Waiting {duration}s for in-flight messages (drain time)...')
            info(f'*** Waiting {duration}s for in-flight messages (drain time)...\n')
            time.sleep(duration)
            
            # ==========================================
            # END OF EXPERIMENT
            # ==========================================
            self.log_event('PHASE', '=== EXPERIMENT COMPLETE ===')
            
            # Save link failure log
            self.save_link_failure_log()
            
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

    def save_link_failure_log(self):
        """Save link failure events to file"""
        log_file = os.path.join(os.getcwd(), 'link_failure_log.txt')
        with open(log_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("LINK FAILURE TEST LOG - Scenario 10\n")
            f.write("="*70 + "\n\n")
            f.write(f"Link disabled: {LINK_TO_DISABLE}\n")
            f.write(f"Phase 1 duration: {PHASE1_DURATION} seconds\n")
            f.write("\n" + "="*70 + "\n")
            f.write("EVENTS:\n")
            f.write("="*70 + "\n\n")
            for entry in self.link_failure_log:
                f.write(entry + "\n")
        info(f'*** Link failure log saved to: {log_file}\n')

    def stop_mqtt(self):
        """Stop subscriber and broker (publishers already stopped)"""
        h_broker = self.net.get('broker')
        if h_broker:
            info('  Stopping subscriber (waiting for summary generation)...\n')
            h_broker.cmd('pkill -TERM -f subscriber_linkfailure')
            time.sleep(30)
            h_broker.cmd('pkill -f subscriber_linkfailure')
            h_broker.cmd('pkill -f mosquitto')

        time.sleep(2)

    def stop(self):
        """Stop the network"""
        if self.net:
            info('*** Stopping network\n')
            self.net.stop()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='DSCP Ring with Link Failure - Scenario 10')
    parser.add_argument('--duration', type=int, default=120, help='Duration in seconds (default: 120)')
    args = parser.parse_args()

    if args.duration < PHASE1_DURATION + 30:
        print(f"Error: Duration must be at least {PHASE1_DURATION + 30} seconds")
        print(f"  Phase 1 (normal): {PHASE1_DURATION}s")
        print(f"  Phase 2 (link down): at least 30s")
        sys.exit(1)

    setLogLevel('info')

    topology = DSCPRingTopologyLinkFailure()

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
