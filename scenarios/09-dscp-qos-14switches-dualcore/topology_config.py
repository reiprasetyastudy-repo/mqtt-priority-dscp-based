#!/usr/bin/env python3
"""
Scenario 09: DSCP-Based QoS with Dual Core Topology (14 Switches)

Topology (from tier 2.png):
- 2 Core Switches (s1, s2) - Dual core for redundancy
- 3 Distribution Switches (s3, s4, s5) - One per floor
- 9 Edge Switches (s6-s14) - Three per floor
- Total: 14 switches, 19 hosts (1 broker + 18 publishers)

Network Design:

                         MQTT Broker + Subscriber
                                  │
                  ┌───────────────┴───────────────┐
                  │                               │
              ┌───┴───┐                       ┌───┴───┐
              │  s1   │───────────────────────│  s2   │
              │ Core1 │                       │ Core2 │
              └───┬───┘                       └───┬───┘
                  │                               │
       ┌──────────┼──────────┬──────────┬────────┼──────────┐
       │          │          │          │        │          │
       │          │          │          │        │          │
       ▼          ▼          ▼          ▼        ▼          ▼
   ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐
   │  s3   │  │  s3   │  │  s4   │  │  s4   │  │  s5   │  │  s5   │
   │(from  │  │(from  │  │(from  │  │(from  │  │(from  │  │(from  │
   │  s1)  │  │  s2)  │  │  s1)  │  │  s2)  │  │  s1)  │  │  s2)  │
   └───────┘  └───────┘  └───────┘  └───────┘  └───────┘  └───────┘
        ╲         ╱           ╲         ╱           ╲         ╱
         ╲       ╱             ╲       ╱             ╲       ╱
          ╲     ╱               ╲     ╱               ╲     ╱
       ┌───────┐             ┌───────┐             ┌───────┐
       │  s3   │             │  s4   │             │  s5   │
       │Floor 1│             │Floor 2│             │Floor 3│
       └───┬───┘             └───┬───┘             └───┬───┘
           │                     │                     │
     ┌─────┼─────┐         ┌─────┼─────┐         ┌─────┼─────┐
     │     │     │         │     │     │         │     │     │
    s6    s7    s8        s9   s10   s11       s12   s13   s14
     │     │     │         │     │     │         │     │     │
    2h    2h    2h        2h    2h    2h        2h    2h    2h

Simplified View (actual connections):

                    MQTT Broker
                         │
                  ┌──────┴──────┐
                  │             │
              ┌───┴───┐     ┌───┴───┐
              │  s1   │     │  s2   │  CORE (2 switches, NOT connected to each other)
              └───┬───┘     └───┬───┘
                  │╲           ╱│
                  │ ╲─────────╱ │
                  │  ╲       ╱  │
                  │   ╲     ╱   │
              ┌───┼─────╳──────┼───┐
              │   │    ╱ ╲     │   │
              ▼   ▼   ▼   ▼    ▼   ▼
          ┌───────┐ ┌───────┐ ┌───────┐
          │  s3   │ │  s4   │ │  s5   │  DISTRIBUTION (3 switches)
          │Floor 1│ │Floor 2│ │Floor 3│  Each connects to BOTH cores!
          └───┬───┘ └───┬───┘ └───┬───┘
              │         │         │
        ┌─────┼───┐ ┌───┼───┐ ┌───┼─────┐
        │     │   │ │   │   │ │   │     │
       s6    s7  s8 s9 s10 s11 s12 s13  s14  EDGE (9 switches)

Connections Summary (Non-Stacking):
- Broker → s1 AND s2 (dual-homed for redundancy)
- s1 and s2 are NOT connected to each other (non-stacking)
- s1 → s3, s4, s5 (core1 to all distributions)
- s2 → s3, s4, s5 (core2 to all distributions)
- s3 → s6, s7, s8 (floor 1)
- s4 → s9, s10, s11 (floor 2)
- s5 → s12, s13, s14 (floor 3)

Redundancy:
- Each distribution switch connects to BOTH core switches
- If Core1 fails, traffic routes through Core2
- Standard enterprise/data center design

DSCP Priority:
- DSCP 46 (EF): Anomaly/Critical traffic - Queue 1 (highest)
- DSCP 0 (BE): Normal traffic - Queue 5 (lowest)
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

# LOG_DIR will be set dynamically based on current working directory (results/run_xxx/)
LOG_DIR = None

# Network configuration
LINK_BANDWIDTH_MBPS = 0.5   # 500 Kbps - creates congestion for QoS testing
MSG_RATE = 50               # 50 msg/s per publisher

# DSCP values
DSCP_ANOMALY = 46  # EF - Expedited Forwarding
DSCP_NORMAL = 0    # BE - Best Effort


class DualCoreTopology:
    """Dual Core Topology with 14 switches"""
    
    def __init__(self):
        self.net = None
        self.switches = {}
        self.hosts = {}
        self.publishers = []
        
    def build(self):
        """Build the dual core topology"""
        info('*** Creating Dual Core Topology (14 switches)\n')
        
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
        
        # Core switches (2)
        self.switches['s1'] = self.net.addSwitch('s1', protocols='OpenFlow13')  # Core 1
        self.switches['s2'] = self.net.addSwitch('s2', protocols='OpenFlow13')  # Core 2
        info('  - Core switches: s1, s2\n')
        
        # Distribution switches (3) - one per floor
        for i in range(3, 6):
            self.switches[f's{i}'] = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
        info('  - Distribution switches: s3 (Floor1), s4 (Floor2), s5 (Floor3)\n')
        
        # Edge switches (9) - three per floor
        for i in range(6, 15):
            self.switches[f's{i}'] = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
        info('  - Edge switches: s6-s14\n')
        
        # Create hosts
        info('*** Creating hosts\n')
        
        # Broker host - connected to Core 1
        self.hosts['broker'] = self.net.addHost('broker', ip='10.0.0.1/16')
        
        # Publisher hosts - 2 per edge switch (1 anomaly + 1 normal)
        host_id = 2
        floor_map = {
            's6': (1, 1), 's7': (1, 2), 's8': (1, 3),   # Floor 1
            's9': (2, 1), 's10': (2, 2), 's11': (2, 3), # Floor 2
            's12': (3, 1), 's13': (3, 2), 's14': (3, 3) # Floor 3
        }
        
        for switch_name, (floor, room) in floor_map.items():
            # Anomaly publisher
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
            
            # Normal publisher
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
        
        # Broker to BOTH Core switches (for redundancy)
        self.net.addLink(self.hosts['broker'], self.switches['s1'], bw=bw)
        self.net.addLink(self.hosts['broker'], self.switches['s2'], bw=bw)
        info('  - Broker -> s1 (Core1)\n')
        info('  - Broker -> s2 (Core2)\n')
        
        # Non-stacking: Core switches are NOT directly connected
        # Redundancy is provided via distribution switches
        info('  - s1 and s2 NOT connected (non-stacking design)\n')
        
        # Core to Distribution links (each distribution connects to BOTH cores)
        for dist in ['s3', 's4', 's5']:
            self.net.addLink(self.switches['s1'], self.switches[dist], bw=bw)
            self.net.addLink(self.switches['s2'], self.switches[dist], bw=bw)
        info('  - Core1/Core2 <-> s3, s4, s5 (full mesh)\n')
        
        # Distribution to Edge links
        dist_to_edge = {
            's3': ['s6', 's7', 's8'],    # Floor 1
            's4': ['s9', 's10', 's11'],  # Floor 2
            's5': ['s12', 's13', 's14']  # Floor 3
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
        info('*** Enabling STP on all switches (required for dual-core topology)\n')
        for switch_name in self.switches.keys():
            subprocess.run(['ovs-vsctl', 'set', 'Bridge', switch_name, 'stp_enable=true'], capture_output=True)
        info('  - STP enabled on 14 switches\n')
        
        # Wait for STP convergence (30-50 seconds typically)
        info('*** Waiting 35s for STP convergence...\n')
        time.sleep(35)
        
        # Wait for switches to connect
        info('*** Waiting for switches to connect to controller...\n')
        time.sleep(5)
        
    def configure_qos(self):
        """Configure QoS queues on all switches"""
        info('*** Configuring QoS queues\n')
        
        bw_bps = int(LINK_BANDWIDTH_MBPS * 1000000)
        
        for switch_name, switch in self.switches.items():
            # Get all interfaces for this switch
            result = subprocess.run(
                ['ovs-vsctl', 'list-ports', switch_name],
                capture_output=True, text=True
            )
            ports = result.stdout.strip().split('\n')
            
            for port in ports:
                if not port:
                    continue
                    
                # Create QoS with 5 queues
                # Queue 1: DSCP 46 (highest priority) - 60-80% bandwidth
                # Queue 5: DSCP 0 (lowest priority) - 5-15% bandwidth
                
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
                
                subprocess.run(
                    ['ovs-vsctl'] + queue_config.split(),
                    capture_output=True
                )
        
        info('*** QoS queues configured on all switches\n')
    
    def start_mqtt_components(self, duration=None):
        """Start MQTT broker, publishers, and subscriber"""
        global LOG_DIR
        
        # Set LOG_DIR based on current working directory
        LOG_DIR = os.path.join(os.getcwd(), 'logs')
        os.makedirs(LOG_DIR, exist_ok=True)
        info(f'*** Logs will be saved to: {LOG_DIR}\n')
        
        h_broker = self.hosts['broker']
        
        # Start Mosquitto broker
        info('*** Starting Mosquitto broker\n')
        h_broker.cmd('mosquitto -c /home/mqtt-sdn/mosquitto.conf -d')
        time.sleep(2)
        
        # Start subscriber with environment variables
        info('*** Starting Subscriber\n')
        env_vars = (
            f'SCENARIO_NAME=09-dscp-qos-14switches-dualcore '
            f'TOPOLOGY_TYPE="DSCP Dual Core (14 switches)" '
            f'NUM_SWITCHES=14 '
            f'NUM_PUBLISHERS={len(self.publishers)} '
            f'ENABLE_BANDWIDTH_LIMIT=True '
            f'LINK_BANDWIDTH_MBPS={LINK_BANDWIDTH_MBPS} '
            f'ENABLE_QOS_QUEUES=True '
        )
        
        h_broker.cmd(f'{env_vars}python3 {PROJECT_ROOT}/shared/mqtt/subscriber_enhanced.py > {LOG_DIR}/subscriber.log 2>&1 &')
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
        info(f'*** Publisher logs: {LOG_DIR}/publisher_*.log\n')
        info(f'*** Subscriber log: {LOG_DIR}/subscriber.log\n')
        
        if duration:
            info(f'*** Publishers will send for {duration} seconds...\n')
            info(f'*** Total experiment time: {duration * 2}s ({duration}s send + {duration}s drain)\n')
            time.sleep(duration)
            
            # Stop publishers
            info('*** Stopping publishers...\n')
            for pub_info in self.publishers:
                pub_info['host'].cmd('pkill -f publisher_dscp')
            
            # Wait for in-flight messages (drain time)
            info(f'*** Waiting {duration}s for in-flight messages (drain time)...\n')
            time.sleep(duration)
            
            # Stop subscriber
            info('*** Stopping subscriber...\n')
            h_broker.cmd('pkill -f subscriber_enhanced')
            time.sleep(2)
            
            # Stop broker
            info('*** Stopping broker...\n')
            h_broker.cmd('pkill -f mosquitto')
    
    def stop(self):
        """Stop the network"""
        if self.net:
            info('*** Stopping network\n')
            self.net.stop()


def run_experiment(duration=60):
    """Run the experiment"""
    setLogLevel('info')
    
    topo = DualCoreTopology()
    
    try:
        # Build and start
        topo.build()
        topo.start()
        
        # Configure QoS
        topo.configure_qos()
        
        # Run MQTT experiment
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
