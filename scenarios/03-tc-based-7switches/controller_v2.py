#!/usr/bin/env python3
"""
MAC Learning Controller with Queue Support - Scenario 03

KEY FIX: Implement proper MAC learning dengan EXPLICIT PORT forwarding
- NO OFPP_NORMAL! (Yang bikin queue tidak work)
- Install flow rules dengan specific output port
- SetQueue action akan work karena tidak bypass OpenFlow pipeline

This is the PROVEN approach untuk QoS dengan OpenFlow!
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4, tcp


class MACLearningQoSController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MACLearningQoSController, self).__init__(*args, **kwargs)

        # MAC learning table: {dpid: {mac_address: port}}
        self.mac_to_port = {}

        # Switch layer mapping
        self.CORE_SWITCHES = [1]
        self.AGG_SWITCHES = [2, 3]
        self.EDGE_SWITCHES = [4, 5, 6, 7]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # Initialize MAC table for this switch
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("=" * 70)
        self.logger.info(f"[Ryu] Switch Connected: s{dpid}")
        self.logger.info("=" * 70)

        # Install table-miss flow entry
        # Packet-In untuk MAC learning (priority 0)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Install high priority flows untuk protocol support
        self.install_base_flows(datapath, dpid)

        self.logger.info(f"[Ryu] Switch s{dpid} ready for MAC learning")
        self.logger.info("=" * 70)

    def install_base_flows(self, datapath, dpid):
        """Install base flows for ARP, ICMP (tidak perlu MAC learning)"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Priority 100: ARP - Flood ke semua port
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        self.logger.info(f"  ✓ ARP: priority 100 → FLOOD")

        # Priority 90: ICMP - Flood
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 90, match_icmp, actions_icmp)
        self.logger.info(f"  ✓ ICMP: priority 90 → FLOOD")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0, hard_timeout=0):
        """Install flow entry"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst,
                                    idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst,
                                    idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Handle Packet-In event untuk MAC learning

        CRITICAL: Ini adalah tempat dimana kita:
        1. Learn MAC address → port mapping
        2. Classify traffic (anomaly vs normal)
        3. Install flow dengan QUEUE assignment dan EXPLICIT OUTPUT PORT
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # Ignore LLDP packet
            return

        dst_mac = eth.dst
        src_mac = eth.src

        # Learn source MAC
        self.mac_to_port[dpid][src_mac] = in_port

        # Determine output port
        if dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD

        # Classify traffic and determine queue
        queue_id = None
        priority = 10  # Default priority

        # Check if this is MQTT traffic
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)

        if ip_pkt and tcp_pkt and tcp_pkt.dst_port == 1883:
            # MQTT traffic detected!
            src_ip = ip_pkt.src

            # Classify based on IP (odd=anomaly, even=normal)
            ip_last_octet = int(src_ip.split('.')[-1])

            if ip_last_octet % 2 == 1:
                # Anomaly traffic → Queue 1 (High priority)
                queue_id = 1
                priority = 20
                traffic_type = "ANOMALY"
            else:
                # Normal traffic → Queue 2 (Low priority)
                queue_id = 2
                priority = 15
                traffic_type = "NORMAL"

            self.logger.info(f"  [MQTT] s{dpid} port{in_port}: {src_ip} → "
                           f"Queue {queue_id} ({traffic_type})")

        # Prepare actions
        actions = []

        # Add SetQueue action if queue is determined
        if queue_id is not None:
            actions.append(parser.OFPActionSetQueue(queue_id))

        # Add output action dengan EXPLICIT PORT (NOT OFPP_NORMAL!)
        actions.append(parser.OFPActionOutput(out_port))

        # Install flow to avoid packet_in next time (if not flooding)
        if out_port != ofproto.OFPP_FLOOD:
            # Create match based on packet characteristics
            if ip_pkt and tcp_pkt and tcp_pkt.dst_port == 1883:
                # MQTT flow - match specific untuk better control
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=0x0800,
                    ipv4_src=ip_pkt.src,
                    ipv4_dst=ip_pkt.dst,
                    ip_proto=6,
                    tcp_dst=1883
                )
            else:
                # Generic flow
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=dst_mac,
                    eth_src=src_mac
                )

            # Install flow dengan idle_timeout untuk dynamic adaptation
            self.add_flow(datapath, priority, match, actions,
                         idle_timeout=30, hard_timeout=0)

        # Send packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                   in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
