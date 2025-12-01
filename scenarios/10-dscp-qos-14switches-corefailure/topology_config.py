#!/usr/bin/env python3
"""
Scenario 10: DSCP-Based QoS with Dual Core - Core Failure Test

Same topology as Scenario 09, but with Core Switch failure simulation.

Topology:
                    MQTT Broker
                         │
                  ┌──────┴──────┐
                  │             │
              ┌───┴───┐     ┌───┴───┐
              │  s1   │─────│  s2   │  CORE (2 switches)
              └───┬───┘     └───┬───┘
                  │╲           ╱│
                  │ ╲─────────╱ │
                  │  ╲       ╱  │
                  │   ╲     ╱   │
              ┌───┼─────╳──────┼───┐
              │   │    ╱ ╲     │   │
              ▼   ▼   ▼   ▼    ▼   ▼
          ┌───────┐ ┌───────┐ ┌───────┐
          │  s3   │ │  s4   │ │  s5   │  DISTRIBUTION
          │Floor 1│ │Floor 2│ │Floor 3│  Each connects to BOTH cores
          └───┬───┘ └───┬───┘ └───┬───┘
              │         │         │
        ┌─────┼───┐ ┌───┼───┐ ┌───┼─────┐
        │     │   │ │   │   │ │   │     │
       s6    s7  s8 s9 s10 s11 s12 s13  s14  EDGE (9 switches)

Test Phases:
- Phase 1 (0-30s): Normal operation - both cores active
- Phase 2 (30s+): Core 2 (s2) disabled - traffic via Core 1 only

This tests the redundancy of the dual-core design.
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

# Project paths
PROJECT_ROOT = "/home/mqtt-sdn"
SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))

# LOG_DIR will be set dynamically
LOG_DIR = None

# Network configuration
LINK_BANDWIDTH_MBPS = 0.5
MSG_RATE = 50

# Core failure configuration
PHASE1_DURATION = 30  # seconds before core failure

# DSCP values
DSCP_ANOMALY = 46
DSCP_NORMAL = 0


class DualCoreFailureTopology:
    """Dual Core Topology with Core Failure Simulation"""
    
    def __init__(self):
        self.net = None
        self.switches = {}
        self.hosts = {}
        self.publishers = []
        self.core2_links = []  # Links to disable for core failure
        
    def build(self):
        """Build the dual core topology"""
        info('*** Creating Dual Core Topology (14 switches) - Core Failure Test\n')
        
        self.net = Mininet(
            controller=RemoteController,
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=True
        )
        
        # Add controller
        info('*** Adding controller\n')
        self.net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
        
        # Create switches
        info('*** Creating switches\n')
        
        # Core switches
        self.switches['s1'] = self.net.addSwitch('s1', protocols='OpenFlow13')
        self.switches['s2'] = self.net.addSwitch('s2', protocols='OpenFlow13')
        info('  - Core switches: s1 (primary), s2 (will fail)\n')
        
        # Distribution switches
        for i in range(3, 6):
            self.switches[f's{i}'] = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
        info('  - Distribution switches: s3, s4, s5\n')
        
        # Edge switches
        for i in range(6, 15):
            self.switches[f's{i}'] = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
        info('  - Edge switches: s6-s14\n')
        
        # Create hosts
        info('*** Creating hosts\n')
        
        self.hosts['broker'] = self.net.addHost('broker', ip='10.0.0.1/16')
        
        floor_map = {
            's6': (1, 1), 's7': (1, 2), 's8': (1, 3),
            's9': (2, 1), 's10': (2, 2), 's11': (2, 3),
            's12': (3, 1), 's13': (3, 2), 's14': (3, 3)
        }
        
        for switch_name, (floor, room) in floor_map.items():
            h_anomaly = self.net.addHost(
                f'f{floor}r{room}a',
                ip=f'10.0.{floor}.{room * 10 + 1}/16'
            )
            self.hosts[f'f{floor}r{room}a'] = h_anomaly
            self.publishers.append({
                'host': h_anomaly,
                'type': 'anomaly',
                'floor': floor,
                'room': room,
                'switch': switch_name
            })
            
            h_normal = self.net.addHost(
                f'f{floor}r{room}n',
                ip=f'10.0.{floor}.{room * 10 + 2}/16'
            )
            self.hosts[f'f{floor}r{room}n'] = h_normal
            self.publishers.append({
                'host': h_normal,
                'type': 'normal',
                'floor': floor,
                'room': room,
                'switch': switch_name
            })
        
        info(f'  - Created {len(self.publishers)} publisher hosts\n')
        
        # Create links
        info('*** Creating links\n')
        
        bw = LINK_BANDWIDTH_MBPS
        
        # Broker to Core 1
        self.net.addLink(self.hosts['broker'], self.switches['s1'], bw=bw)
        info('  - Broker -> s1 (Core1)\n')
        
        # Core interconnect - this link will be disabled
        link_core = self.net.addLink(self.switches['s1'], self.switches['s2'], bw=bw)
        self.core2_links.append(('s1', 's2', link_core))
        info('  - s1 <-> s2 (Core interconnect - will be disabled)\n')
        
        # Core to Distribution links
        for dist in ['s3', 's4', 's5']:
            self.net.addLink(self.switches['s1'], self.switches[dist], bw=bw)
            link_c2 = self.net.addLink(self.switches['s2'], self.switches[dist], bw=bw)
            self.core2_links.append(('s2', dist, link_c2))
        info('  - Core1/Core2 <-> Distribution (Core2 links will be disabled)\n')
        
        # Distribution to Edge links
        dist_to_edge = {
            's3': ['s6', 's7', 's8'],
            's4': ['s9', 's10', 's11'],
            's5': ['s12', 's13', 's14']
        }
        
        for dist, edges in dist_to_edge.items():
            for edge in edges:
                self.net.addLink(self.switches[dist], self.switches[edge], bw=bw)
        info('  - Distribution -> Edge links\n')
        
        # Host to Edge links
        for pub in self.publishers:
            switch = self.switches[pub['switch']]
            self.net.addLink(pub['host'], switch, bw=bw)
        
        info(f'*** Topology built: 14 switches, {len(self.publishers)} publishers\n')
        
        return self.net
    
    def start(self):
        """Start the network"""
        info('*** Starting network\n')
        self.net.start()
        
        # Enable STP on all switches to prevent loops
        info('*** Enabling STP on all switches\n')
        for switch_name in self.switches.keys():
            subprocess.run(['ovs-vsctl', 'set', 'Bridge', switch_name, 'stp_enable=true'], capture_output=True)
        info('  - STP enabled on 14 switches\n')
        
        # Wait for STP convergence
        info('*** Waiting 35s for STP convergence...\n')
        time.sleep(35)
        
        time.sleep(5)
        
    def configure_qos(self):
        """Configure QoS queues"""
        info('*** Configuring QoS queues\n')
        
        bw_bps = int(LINK_BANDWIDTH_MBPS * 1000000)
        
        for switch_name in self.switches.keys():
            result = subprocess.run(
                ['ovs-vsctl', 'list-ports', switch_name],
                capture_output=True, text=True
            )
            ports = result.stdout.strip().split('\n')
            
            for port in ports:
                if not port:
                    continue
                    
                queue_config = (
                    f'-- set port {port} qos=@newqos '
                    f'-- --id=@newqos create qos type=linux-htb '
                    f'other-config:max-rate={bw_bps} '
                    f'queues:1=@q1 queues:2=@q2 queues:3=@q3 queues:4=@q4 queues:5=@q5 '
                    f'-- --id=@q1 create queue other-config:min-rate={int(bw_bps*0.6)} other-config:max-rate={int(bw_bps*0.8)} '
                    f'-- --id=@q2 create queue other-config:min-rate={int(bw_bps*0.45)} other-config:max-rate={int(bw_bps*0.6)} '
                    f'-- --id=@q3 create queue other-config:min-rate={int(bw_bps*0.3)} other-config:max-rate={int(bw_bps*0.45)} '
                    f'-- --id=@q4 create queue other-config:min-rate={int(bw_bps*0.15)} other-config:max-rate={int(bw_bps*0.3)} '
                    f'-- --id=@q5 create queue other-config:min-rate={int(bw_bps*0.05)} other-config:max-rate={int(bw_bps*0.15)}'
                )
                
                subprocess.run(['ovs-vsctl'] + queue_config.split(), capture_output=True)
        
        info('*** QoS queues configured\n')
    
    def disable_core2(self):
        """Disable Core 2 (s2) by bringing down all its links"""
        info('\n')
        info('=' * 60 + '\n')
        info('  CORE FAILURE: Disabling Core 2 (s2)\n')
        info('=' * 60 + '\n')
        
        # Method 1: Bring down interfaces on s2
        result = subprocess.run(
            ['ovs-vsctl', 'list-ports', 's2'],
            capture_output=True, text=True
        )
        ports = result.stdout.strip().split('\n')
        
        for port in ports:
            if port:
                subprocess.run(['ip', 'link', 'set', port, 'down'], capture_output=True)
                info(f'  - Disabled interface: {port}\n')
        
        # Log the failure
        with open(os.path.join(os.getcwd(), 'core_failure_log.txt'), 'w') as f:
            f.write(f"Core Failure Event\n")
            f.write(f"==================\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Failed Switch: s2 (Core 2)\n")
            f.write(f"Disabled Ports: {', '.join(ports)}\n")
            f.write(f"\nTraffic should now route through s1 (Core 1) only.\n")
        
        info('  - Core 2 disabled. Traffic will route via Core 1.\n')
        info('=' * 60 + '\n\n')
    
    def start_mqtt_components(self, duration=None):
        """Start MQTT components with core failure simulation"""
        global LOG_DIR
        
        LOG_DIR = os.path.join(os.getcwd(), 'logs')
        os.makedirs(LOG_DIR, exist_ok=True)
        info(f'*** Logs will be saved to: {LOG_DIR}\n')
        
        h_broker = self.hosts['broker']
        
        # Start Mosquitto
        info('*** Starting Mosquitto broker\n')
        h_broker.cmd('mosquitto -c /home/mqtt-sdn/mosquitto.conf -d')
        time.sleep(2)
        
        # Start subscriber with phase tracking
        info('*** Starting Subscriber (with phase tracking)\n')
        env_vars = (
            f'SCENARIO_NAME=10-dscp-qos-14switches-corefailure '
            f'TOPOLOGY_TYPE="DSCP Dual Core + Core Failure Test" '
            f'NUM_SWITCHES=14 '
            f'NUM_PUBLISHERS={len(self.publishers)} '
            f'ENABLE_BANDWIDTH_LIMIT=True '
            f'LINK_BANDWIDTH_MBPS={LINK_BANDWIDTH_MBPS} '
            f'ENABLE_QOS_QUEUES=True '
            f'PHASE1_DURATION={PHASE1_DURATION} '
        )
        
        h_broker.cmd(f'{env_vars}python3 {SCENARIO_DIR}/subscriber_corefailure.py > {LOG_DIR}/subscriber.log 2>&1 &')
        time.sleep(2)
        
        # Start publishers
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
                time.sleep(0.5)
        
        info('*** All MQTT components started\n')
        
        if duration:
            # Calculate phases
            phase2_duration = duration - PHASE1_DURATION
            total_time = duration * 2  # send + drain
            
            info(f'\n*** Experiment Timeline:\n')
            info(f'  Phase 1 (Normal)      : 0 - {PHASE1_DURATION}s\n')
            info(f'  Phase 2 (Core Failure): {PHASE1_DURATION} - {duration}s\n')
            info(f'  Drain Time            : {duration} - {total_time}s\n')
            info(f'  Total Time            : {total_time}s\n\n')
            
            # Phase 1: Normal operation
            info(f'*** Phase 1: Normal operation ({PHASE1_DURATION}s)\n')
            time.sleep(PHASE1_DURATION)
            
            # Trigger core failure
            self.disable_core2()
            
            # Phase 2: Core failure
            info(f'*** Phase 2: Core failure operation ({phase2_duration}s)\n')
            time.sleep(phase2_duration)
            
            # Stop publishers
            info('*** Stopping publishers...\n')
            for pub_info in self.publishers:
                pub_info['host'].cmd('pkill -f publisher_dscp')
            
            # Drain time
            info(f'*** Waiting {duration}s for in-flight messages...\n')
            time.sleep(duration)
            
            # Stop subscriber and broker
            info('*** Stopping subscriber and broker...\n')
            h_broker.cmd('pkill -f subscriber_corefailure')
            time.sleep(2)
            h_broker.cmd('pkill -f mosquitto')
    
    def stop(self):
        """Stop the network"""
        if self.net:
            info('*** Stopping network\n')
            self.net.stop()


def run_experiment(duration=60):
    """Run the experiment"""
    setLogLevel('info')
    
    topo = DualCoreFailureTopology()
    
    try:
        topo.build()
        topo.start()
        topo.configure_qos()
        topo.start_mqtt_components(duration=duration)
        
    except KeyboardInterrupt:
        info('\n*** Interrupted by user\n')
    except Exception as e:
        info(f'\n*** Error: {e}\n')
        import traceback
        traceback.print_exc()
    finally:
        topo.stop()


if __name__ == '__main__':
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    run_experiment(duration)
