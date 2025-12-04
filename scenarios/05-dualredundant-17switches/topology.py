#!/usr/bin/env python3
"""
Scenario 05: Dual Redundant - 17 Switch Topology

Full redundancy at all layers:
- 2 Core switches
- 6 Distribution switches (2 per floor)
- 9 Edge switches (1 per room, connected to both distribution)

This provides maximum fault tolerance with STP managing loops.
"""

import os
import sys
import time
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel, info

from shared.config import get_host_name, get_device_name, BROKER_IP
from shared.topology import BaseTopology

# =============================================================================
# SCENARIO CONFIGURATION
# =============================================================================
SCENARIO_NAME = "05-dualredundant-17switches"
LINK_BANDWIDTH_MBPS = 0.2
MSG_RATE = 10
DURATION = 600               # 10 minutes
DRAIN_RATIO = 1.0

SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, f'results/{SCENARIO_NAME}')


class Scenario05Topology(BaseTopology):
    """17-switch fully redundant topology."""
    
    def __init__(self):
        super().__init__(SCENARIO_NAME)
    
    def build(self):
        setLogLevel('info')
        
        info(f'*** Building {SCENARIO_NAME}\n')
        info(f'*** Full redundancy: 2 Core + 6 Dist + 9 Edge\n')
        
        self.net = Mininet(controller=RemoteController, autoSetMacs=True, link=TCLink)
        self.net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
        
        bw = LINK_BANDWIDTH_MBPS
        
        # === CORE LAYER ===
        core1 = self.net.addSwitch('s1', protocols='OpenFlow13')
        core2 = self.net.addSwitch('s2', protocols='OpenFlow13')
        self.switches['s1'] = core1
        self.switches['s2'] = core2
        
        # Broker connects to both cores
        broker = self.net.addHost('broker', ip='10.0.0.1/16')
        self.hosts['broker'] = broker
        self.broker_host = broker
        self.net.addLink(broker, core1, bw=bw)
        self.net.addLink(broker, core2, bw=bw)
        
        # === DISTRIBUTION LAYER (2 per floor) ===
        dist_switches = {}  # {floor: [sw_a, sw_b]}
        sw_num = 3
        
        for floor in [1, 2, 3]:
            dist_a = self.net.addSwitch(f's{sw_num}', protocols='OpenFlow13')
            dist_b = self.net.addSwitch(f's{sw_num+1}', protocols='OpenFlow13')
            self.switches[f's{sw_num}'] = dist_a
            self.switches[f's{sw_num+1}'] = dist_b
            dist_switches[floor] = (dist_a, dist_b)
            
            # Each distribution connects to both cores
            self.net.addLink(dist_a, core1, bw=bw)
            self.net.addLink(dist_a, core2, bw=bw)
            self.net.addLink(dist_b, core1, bw=bw)
            self.net.addLink(dist_b, core2, bw=bw)
            
            sw_num += 2
        
        # === EDGE LAYER + HOSTS ===
        host_ip = 2
        
        for floor in [1, 2, 3]:
            dist_a, dist_b = dist_switches[floor]
            for room in [1, 2, 3]:
                edge_sw = self.net.addSwitch(f's{sw_num}', protocols='OpenFlow13')
                self.switches[f's{sw_num}'] = edge_sw
                
                # Edge connects to both distribution switches
                self.net.addLink(edge_sw, dist_a, bw=bw)
                self.net.addLink(edge_sw, dist_b, bw=bw)
                
                # Add sensors
                for sensor_type in ['anomaly', 'normal']:
                    h_name = get_host_name(floor, room, sensor_type)
                    h = self.net.addHost(h_name, ip=f'10.0.0.{host_ip}/16')
                    self.hosts[h_name] = h
                    self.publishers.append((h, sensor_type, floor, room, sw_num))
                    self.net.addLink(h, edge_sw, bw=bw)
                    host_ip += 1
                
                sw_num += 1
        
        info(f'*** Topology: {len(self.switches)} switches, {len(self.hosts)} hosts\n')
        
        self.net.start()
        time.sleep(3)
        
        # Enable STP (required for redundant topology)
        self.enable_stp(wait_time=45)
        self.configure_qos_queues(LINK_BANDWIDTH_MBPS)
        
        return self.net


def run_experiment(duration=DURATION, drain_ratio=DRAIN_RATIO, output_dir=None):
    # Use provided output_dir or create new one
    if output_dir and os.path.exists(output_dir):
        run_dir = output_dir
    else:
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(RESULTS_DIR, f'run_{timestamp}')
        os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.join(run_dir, 'logs'), exist_ok=True)
    os.chdir(run_dir)
    
    topo = Scenario05Topology()
    topo.log_dir = os.path.join(run_dir, 'logs')
    
    try:
        topo.build()
        topo.start_broker()
        topo.start_subscriber(SCENARIO_DIR)
        result = topo.run_experiment(duration, drain_ratio, SCENARIO_DIR, MSG_RATE, LINK_BANDWIDTH_MBPS)
        
        csv_file = os.path.join(run_dir, 'mqtt_metrics_log.csv')
        if os.path.exists(csv_file):
            os.system(f'python3 {PROJECT_ROOT}/generate_summary.py {csv_file}')
    finally:
        topo.cleanup()
    
    return run_dir


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', '-d', type=int, default=DURATION)
    parser.add_argument('--drain-ratio', '-r', type=float, default=DRAIN_RATIO)
    parser.add_argument('--output-dir', '-o', type=str, default=None,
                        help='Output directory')
    args = parser.parse_args()
    run_experiment(args.duration, args.drain_ratio, args.output_dir)
