#!/usr/bin/env python3
"""
TC-Based Priority Controller for 7-Switch Topology

APPROACH: TOS/DSCP Marking (bukan OpenFlow Queue)
- Controller MARK IP TOS field pada packet
- TC (Traffic Control) di Mininet link handle priority berdasarkan TOS
- Proven approach yang lebih reliable!

Topology:
- 1 Core switch (s1)
- 2 Aggregation switches (s2, s3)
- 4 Edge switches (s4-s7)

Subnets:
- 10.0.1.x = Floor 1 (s4, s5)
- 10.0.2.x = Floor 2 (s6, s7)
- 10.0.0.x = Core (broker @ 10.0.0.1)

Priority Classification (IP-based):
- Anomaly (odd IPs .1, .3): TOS=0x10 (High priority)
- Normal (even IPs .2, .4): TOS=0x00 (Best effort)
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class TCBasedPriorityController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TCBasedPriorityController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        # Switch layer mapping
        self.CORE_SWITCHES = [1]
        self.AGG_SWITCHES = [2, 3]
        self.EDGE_SWITCHES = [4, 5, 6, 7]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id

        self.logger.info("=" * 70)
        self.logger.info(f"[Ryu] Switch Connected: s{dpid} (dpid={dpid})")
        self.logger.info("=" * 70)

        # Install flows based on switch type
        if dpid in self.CORE_SWITCHES:
            self.logger.info(f"[Ryu] Installing CORE flows for s{dpid}")
            self.install_core_flows(datapath)
        elif dpid in self.AGG_SWITCHES:
            self.logger.info(f"[Ryu] Installing AGGREGATION flows for s{dpid}")
            self.install_aggregation_flows(datapath)
        elif dpid in self.EDGE_SWITCHES:
            self.logger.info(f"[Ryu] Installing EDGE flows for s{dpid}")
            self.install_edge_flows(datapath, dpid)
        else:
            self.logger.warning(f"[Ryu] Unknown switch s{dpid}")
            self.install_default_flows(datapath)

        self.logger.info(f"[Ryu] Flow installation complete for s{dpid}")
        self.logger.info("=" * 70)

    def add_flow(self, datapath, priority, match, actions):
        """Add a flow entry to the switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    def install_edge_flows(self, datapath, dpid):
        """
        Install flows for Edge switches (s4-s7)

        CRITICAL: Mark TOS field untuk priority!
        - Anomaly traffic: TOS=0x10 (IPTOS_LOWDELAY)
        - Normal traffic: TOS=0x00 (Best effort)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Determine floor: s4,s5=floor1, s6,s7=floor2
        if dpid in [4, 5]:
            floor = 1
        else:
            floor = 2

        self.logger.info(f"  Edge switch s{dpid} handles Floor {floor} subnet 10.0.{floor}.0/24")

        # Priority 100: ARP
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        self.logger.info(f"  ✓ ARP traffic: priority 100 → NORMAL")

        # Priority 90: ICMP
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 90, match_icmp, actions_icmp)

        # Priority 20: Anomaly MQTT → Mark TOS=0x10
        # 2 anomaly publishers per edge switch (IP .1, .3)
        anomaly_ips = [1, 3]
        for ip_suffix in anomaly_ips:
            ip_addr = f"10.0.{floor}.{ip_suffix}"
            match_anomaly = parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=ip_addr,
                ip_proto=6,
                tcp_dst=1883
            )
            actions_anomaly = [
                parser.OFPActionSetField(ip_dscp=4),  # DSCP=4 → TOS=0x10 (IPTOS_LOWDELAY)
                parser.OFPActionOutput(ofproto.OFPP_NORMAL)
            ]
            self.add_flow(datapath, 20, match_anomaly, actions_anomaly)
        self.logger.info(f"  ✓ Anomaly MQTT (odd IPs .1,.3) → TOS=0x10 (HIGH priority)")

        # Priority 15: Normal MQTT → No TOS marking (TOS=0x00)
        # 2 normal publishers per edge switch (IP .2, .4)
        normal_ips = [2, 4]
        for ip_suffix in normal_ips:
            ip_addr = f"10.0.{floor}.{ip_suffix}"
            match_normal = parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=ip_addr,
                ip_proto=6,
                tcp_dst=1883
            )
            actions_normal = [
                # No TOS marking = TOS=0x00 (Best effort)
                parser.OFPActionOutput(ofproto.OFPP_NORMAL)
            ]
            self.add_flow(datapath, 15, match_normal, actions_normal)
        self.logger.info(f"  ✓ Normal MQTT (even IPs .2,.4) → TOS=0x00 (NORMAL priority)")

        # Priority 12: Broker return traffic
        match_broker = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src="10.0.0.1"
        )
        actions_broker = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 12, match_broker, actions_broker)
        self.logger.info(f"  ✓ Broker return traffic: priority 12 → NORMAL")

        # Priority 0: Drop
        match_default = parser.OFPMatch()
        actions_default = []
        self.add_flow(datapath, 0, match_default, actions_default)
        self.logger.info(f"  ✓ Default: priority 0 → DROP")

    def install_aggregation_flows(self, datapath):
        """Install flows for Aggregation switches (s2-s3)"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info(f"  Aggregation switch - Forward all traffic")

        # Priority 100: ARP
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        self.logger.info(f"  ✓ ARP traffic: priority 100 → NORMAL")

        # Priority 90: ICMP
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 90, match_icmp, actions_icmp)

        # Priority 20: MQTT to broker (TOS marking preserved)
        match_mqtt = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_dst="10.0.0.1",
            ip_proto=6,
            tcp_dst=1883
        )
        actions_mqtt = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 20, match_mqtt, actions_mqtt)
        self.logger.info(f"  ✓ MQTT to broker: priority 20 → NORMAL (TOS preserved)")

        # Priority 15: Broker return
        match_broker = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src="10.0.0.1"
        )
        actions_broker = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 15, match_broker, actions_broker)
        self.logger.info(f"  ✓ Broker return: priority 15 → NORMAL")

        # Priority 10: Other IP traffic
        match_other = parser.OFPMatch(eth_type=0x0800)
        actions_other = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 10, match_other, actions_other)

        # Priority 0: Drop
        match_default = parser.OFPMatch()
        actions_default = []
        self.add_flow(datapath, 0, match_default, actions_default)

    def install_core_flows(self, datapath):
        """Install flows for Core switch (s1)"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info(f"  Core switch - Gateway to broker @ 10.0.0.1")

        # Priority 100: ARP
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        self.logger.info(f"  ✓ ARP traffic: priority 100 → NORMAL")

        # Priority 90: ICMP
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 90, match_icmp, actions_icmp)

        # Priority 20: MQTT to broker
        match_mqtt = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_dst="10.0.0.1",
            ip_proto=6,
            tcp_dst=1883
        )
        actions_mqtt = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 20, match_mqtt, actions_mqtt)
        self.logger.info(f"  ✓ MQTT to broker: priority 20 → NORMAL")

        # Priority 15: Broker return
        match_broker = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src="10.0.0.1"
        )
        actions_broker = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 15, match_broker, actions_broker)
        self.logger.info(f"  ✓ Broker return: priority 15 → NORMAL")

        # Priority 10: All other IP traffic
        match_ip = parser.OFPMatch(eth_type=0x0800)
        actions_ip = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 10, match_ip, actions_ip)

        # Priority 0: Drop
        match_default = parser.OFPMatch()
        actions_default = []
        self.add_flow(datapath, 0, match_default, actions_default)

    def install_default_flows(self, datapath):
        """Fallback flows for unknown switches"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # ARP
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)

        # All traffic to NORMAL
        match_all = parser.OFPMatch()
        actions_all = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 10, match_all, actions_all)

        self.logger.info(f"  ✓ Default flows installed (NORMAL forwarding)")
