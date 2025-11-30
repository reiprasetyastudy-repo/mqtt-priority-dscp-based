#!/usr/bin/env python3
"""
QoS Controller for Scenario 04

Main SDN controller with MAC learning and QoS prioritization.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4, tcp

from config.config_loader import load_config
from controller.mac_learning import MACLearningTable
from controller.flow_manager import FlowManager
from qos.classifier import TrafficClassifier
from utils.constants import EtherType, IPProtocol


class QoSController(app_manager.RyuApp):
    """
    SDN Controller with QoS prioritization.

    Features:
    - MAC learning for L2 forwarding
    - Traffic classification (anomaly vs normal)
    - Queue-based QoS (priority differentiation)
    - Explicit port forwarding (no OFPP_NORMAL)
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(QoSController, self).__init__(*args, **kwargs)

        # Load configuration
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config/scenario_config.yaml'
        )
        self.config = load_config(config_path)

        # Initialize components
        self.mac_table = MACLearningTable()
        self.flow_manager = FlowManager()
        self.classifier = TrafficClassifier()

        self.logger.info("="*70)
        self.logger.info(f"QoS Controller Initialized - {self.config.name}")
        self.logger.info(f"Classification: {self.config.qos.classification_method}")
        self.logger.info("="*70)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Handle switch connection and install default flows.

        Args:
            ev: EventOFPSwitchFeatures event
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        self.logger.info("="*70)
        self.logger.info(f"[SWITCH] s{dpid} connected")
        self.logger.info("="*70)

        # Install table-miss flow (send to controller)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]
        self.flow_manager.add_flow(
            datapath,
            self.config.qos.table_miss_priority,
            match,
            actions
        )

        # Install base protocol flows
        self._install_base_flows(datapath)

        self.logger.info(f"[SWITCH] s{dpid} ready for traffic")
        self.logger.info("="*70)

    def _install_base_flows(self, datapath):
        """
        Install base flows for ARP and ICMP.

        Args:
            datapath: Datapath object
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # ARP - Flood to all ports
        match_arp = parser.OFPMatch(eth_type=EtherType.ARP)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.flow_manager.add_flow(
            datapath,
            self.config.qos.arp_priority,
            match_arp,
            actions_arp
        )
        self.logger.info(f"  ✓ ARP: priority {self.config.qos.arp_priority} → FLOOD")

        # ICMP - Flood to all ports
        match_icmp = parser.OFPMatch(eth_type=EtherType.IPv4, ip_proto=IPProtocol.ICMP)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.flow_manager.add_flow(
            datapath,
            self.config.qos.icmp_priority,
            match_icmp,
            actions_icmp
        )
        self.logger.info(f"  ✓ ICMP: priority {self.config.qos.icmp_priority} → FLOOD")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Handle packet-in events for MAC learning and QoS.

        This is the core logic:
        1. Learn source MAC
        2. Classify traffic (if MQTT)
        3. Install flow with queue assignment
        4. Forward packet

        Args:
            ev: EventOFPPacketIn event
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        # Parse packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Ignore LLDP
        if eth.ethertype == EtherType.LLDP:
            return

        dst_mac = eth.dst
        src_mac = eth.src

        # Learn source MAC
        is_new = self.mac_table.learn(dpid, src_mac, in_port)

        # Determine output port
        out_port = self.mac_table.get_port(dpid, dst_mac, ofproto.OFPP_FLOOD)

        # Classify traffic and determine queue
        queue_id = None
        priority = 10  # Default priority

        # Check if MQTT traffic
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)

        if ip_pkt and tcp_pkt:
            is_mqtt = self.classifier.is_mqtt_traffic(
                tcp_pkt.dst_port,
                self.config.mqtt.port
            )

            if is_mqtt:
                # Classify MQTT traffic
                src_ip = ip_pkt.src
                queue_id, priority, traffic_type = self.classifier.classify(
                    src_ip,
                    method=self.config.qos.classification_method
                )

                self.logger.info(
                    f"  [MQTT] s{dpid} port{in_port}: {src_ip} → "
                    f"Queue {queue_id} ({traffic_type})"
                )

        # Prepare actions
        actions = []

        # Add SetQueue action if classified
        if queue_id is not None:
            actions.append(parser.OFPActionSetQueue(queue_id))

        # Add output action (EXPLICIT PORT - NOT OFPP_NORMAL!)
        actions.append(parser.OFPActionOutput(out_port))

        # Install flow if not flooding
        if out_port != ofproto.OFPP_FLOOD:
            # Create match
            if ip_pkt and tcp_pkt and tcp_pkt.dst_port == self.config.mqtt.port:
                # Specific match for MQTT flows
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=EtherType.IPv4,
                    ipv4_src=ip_pkt.src,
                    ipv4_dst=ip_pkt.dst,
                    ip_proto=IPProtocol.TCP,
                    tcp_dst=self.config.mqtt.port
                )
            else:
                # Generic L2 match
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=dst_mac,
                    eth_src=src_mac
                )

            # Install flow with idle timeout
            self.flow_manager.add_flow(
                datapath,
                priority,
                match,
                actions,
                idle_timeout=self.config.timing.flow_idle_timeout,
                hard_timeout=self.config.timing.flow_hard_timeout
            )

        # Send packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        self.flow_manager.send_packet_out(
            datapath,
            in_port,
            actions,
            data=data,
            buffer_id=msg.buffer_id
        )
