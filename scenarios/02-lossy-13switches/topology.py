#!/usr/bin/env python3
"""
Scenario 02: Lossy Network - 13 Switch with Packet Loss

Same topology as Scenario 01, but with simulated packet loss:
- Core links: 10% packet loss
- Edge links: 5% packet loss
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
SCENARIO_NAME = "02-lossy-13switches"
LINK_BANDWIDTH_MBPS = 0.2
MSG_RATE = 10
DURATION = 300
DRAIN_RATIO = 1.0

# Packet loss configuration
CORE_LOSS_PERCENT = 10   # 10% loss on core links
EDGE_LOSS_PERCENT = 5    # 5% loss on edge links

SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, f'results/{SCENARIO_NAME}')


class Scenario02Topology(BaseTopology):
    """13-switch topology with packet loss."""
    
    def __init__(self):
        super().__init__(SCENARIO_NAME)
    
    def build(self):
        setLogLevel('info')
        
        info(f'*** Building {SCENARIO_NAME}\n')
        info(f'*** Packet Loss: Core {CORE_LOSS_PERCENT}%, Edge {EDGE_LOSS_PERCENT}%\n')
        
        self.net = Mininet(controller=RemoteController, autoSetMacs=True, link=TCLink)
        self.net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
        
        bw = LINK_BANDWIDTH_MBPS
        
        # Core
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')
        self.switches['s1'] = s1
        
        broker = self.net.addHost('broker', ip='10.0.0.1/16')
        self.hosts['broker'] = broker
        self.broker_host = broker
        self.net.addLink(broker, s1, bw=bw, loss=CORE_LOSS_PERCENT)
        
        # Aggregation
        for i in [2, 3, 4]:
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            self.switches[f's{i}'] = sw
            self.net.addLink(sw, s1, bw=bw, loss=CORE_LOSS_PERCENT)
        
        # Edge + Hosts
        floor_agg = {1: 's2', 2: 's3', 3: 's4'}
        edge_start = {1: 5, 2: 8, 3: 11}
        host_ip = 2
        
        for floor in [1, 2, 3]:
            agg_sw = self.switches[floor_agg[floor]]
            for room in [1, 2, 3]:
                edge_num = edge_start[floor] + room - 1
                edge_sw = self.net.addSwitch(f's{edge_num}', protocols='OpenFlow13')
                self.switches[f's{edge_num}'] = edge_sw
                self.net.addLink(edge_sw, agg_sw, bw=bw, loss=EDGE_LOSS_PERCENT)
                
                for sensor_type in ['anomaly', 'normal']:
                    h_name = get_host_name(floor, room, sensor_type)
                    h = self.net.addHost(h_name, ip=f'10.0.0.{host_ip}/16')
                    self.hosts[h_name] = h
                    self.publishers.append((h, sensor_type, floor, room, edge_num))
                    self.net.addLink(h, edge_sw, bw=bw, loss=EDGE_LOSS_PERCENT)
                    host_ip += 1
        
        self.net.start()
        time.sleep(3)
        self.configure_qos_queues(LINK_BANDWIDTH_MBPS)
        
        return self.net


def run_experiment(duration=DURATION, drain_ratio=DRAIN_RATIO):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(RESULTS_DIR, f'run_{timestamp}')
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.join(run_dir, 'logs'), exist_ok=True)
    os.chdir(run_dir)
    
    topo = Scenario02Topology()
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
    args = parser.parse_args()
    run_experiment(args.duration, args.drain_ratio)
