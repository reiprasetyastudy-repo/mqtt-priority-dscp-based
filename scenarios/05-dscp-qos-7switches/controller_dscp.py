#!/usr/bin/env python3
"""
DSCP-Based QoS Controller for Scenario 05
Support 5 Priority Levels

SIMPLE APPROACH:
- Match DSCP field di IP header
- Set Queue berdasarkan DSCP value
- TIDAK PERLU MAC learning (lebih simple dari Scenario 03!)
- TIDAK PERLU packet-in classification

5 Priority Levels (Standard DSCP Values):
┌──────────┬──────────────────┬────────┬──────────────────┐
│ DSCP Val │ Class            │ Queue  │ Bandwidth        │
├──────────┼──────────────────┼────────┼──────────────────┤
│ 46       │ EF (Very High)   │ Queue 1│ 60-80%          │
│ 34       │ AF41 (High)      │ Queue 2│ 45-60%          │
│ 26       │ AF31 (Medium)    │ Queue 3│ 30-45%          │
│ 10       │ AF11 (Low)       │ Queue 4│ 15-30%          │
│ 0        │ BE (Best Effort) │ Queue 5│ 5-15%           │
└──────────┴──────────────────┴────────┴──────────────────┘

Flow Rules (OpenFlow Priority):
1. ARP traffic        → FLOOD         (priority 100)
2. DSCP 46 (EF)       → Queue 1       (priority 60)
3. DSCP 34 (AF41)     → Queue 2       (priority 55)
4. DSCP 26 (AF31)     → Queue 3       (priority 50)
5. DSCP 10 (AF11)     → Queue 4       (priority 45)
6. DSCP 0  (BE)       → Queue 5       (priority 40)
7. Default            → NORMAL        (priority 0)
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class DSCPQoSController(app_manager.RyuApp):
    """
    Controller yang match DSCP value di IP header
    untuk set queue priority

    Support 5 priority levels dengan DSCP standard values
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DSCPQoSController, self).__init__(*args, **kwargs)
        print("="*70)
        print("DSCP-Based QoS Controller Starting (5 Priority Levels)...")
        print("="*70)
        print("Supported DSCP Values:")
        print("  DSCP 46 (EF)    → Queue 1 (Very High Priority)")
        print("  DSCP 34 (AF41)  → Queue 2 (High Priority)")
        print("  DSCP 26 (AF31)  → Queue 3 (Medium Priority)")
        print("  DSCP 10 (AF11)  → Queue 4 (Low Priority)")
        print("  DSCP 0  (BE)    → Queue 5 (Best Effort)")
        print("="*70)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Event handler saat switch connect ke controller
        Install semua flow rules di sini
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        print("="*70)
        print(f"Switch s{dpid} connected! Installing flows...")
        print("="*70)

        # ========================================
        # FLOW 1: ARP Traffic (Priority 100)
        # ========================================
        # ARP perlu di-flood untuk network discovery
        match_arp = parser.OFPMatch(eth_type=0x0806)  # ARP
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        print(f"[s{dpid}] Flow installed: ARP → FLOOD (priority 100)")

        # ========================================
        # FLOW 2: DSCP 46 (EF - Very High) → Queue 1 (Priority 60)
        # ========================================
        match_ef = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)
        actions_ef = [
            parser.OFPActionSetQueue(1),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 60, match_ef, actions_ef)
        print(f"[s{dpid}] Flow installed: DSCP 46 (EF - Very High) → Queue 1")

        # ========================================
        # FLOW 3: DSCP 34 (AF41 - High) → Queue 2 (Priority 55)
        # ========================================
        match_af41 = parser.OFPMatch(eth_type=0x0800, ip_dscp=34)
        actions_af41 = [
            parser.OFPActionSetQueue(2),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 55, match_af41, actions_af41)
        print(f"[s{dpid}] Flow installed: DSCP 34 (AF41 - High) → Queue 2")

        # ========================================
        # FLOW 4: DSCP 26 (AF31 - Medium) → Queue 3 (Priority 50)
        # ========================================
        match_af31 = parser.OFPMatch(eth_type=0x0800, ip_dscp=26)
        actions_af31 = [
            parser.OFPActionSetQueue(3),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 50, match_af31, actions_af31)
        print(f"[s{dpid}] Flow installed: DSCP 26 (AF31 - Medium) → Queue 3")

        # ========================================
        # FLOW 5: DSCP 10 (AF11 - Low) → Queue 4 (Priority 45)
        # ========================================
        match_af11 = parser.OFPMatch(eth_type=0x0800, ip_dscp=10)
        actions_af11 = [
            parser.OFPActionSetQueue(4),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 45, match_af11, actions_af11)
        print(f"[s{dpid}] Flow installed: DSCP 10 (AF11 - Low) → Queue 4")

        # ========================================
        # FLOW 6: DSCP 0 (BE - Best Effort) → Queue 5 (Priority 40)
        # ========================================
        match_be = parser.OFPMatch(eth_type=0x0800, ip_dscp=0)
        actions_be = [
            parser.OFPActionSetQueue(5),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 40, match_be, actions_be)
        print(f"[s{dpid}] Flow installed: DSCP 0 (BE - Best Effort) → Queue 5")

        # ========================================
        # FLOW 7: Default Flow (Priority 0)
        # ========================================
        # Untuk traffic lain yang tidak match (e.g., ICMP)
        match_default = parser.OFPMatch()
        actions_default = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 0, match_default, actions_default)
        print(f"[s{dpid}] Flow installed: Default → NORMAL (priority 0)")

        print("="*70)
        print(f"Switch s{dpid} ready! All 7 flows installed (5 DSCP levels)")
        print("="*70)
        print()

    def add_flow(self, datapath, priority, match, actions, buffer_id=None,
                 idle_timeout=0, hard_timeout=0):
        """
        Helper function untuk install flow rule ke switch

        Args:
            datapath: Switch datapath object
            priority: Flow priority (higher = more important)
            match: OFPMatch object (match conditions)
            actions: List of actions (e.g., output, set queue)
            buffer_id: Buffer ID (optional)
            idle_timeout: Timeout jika tidak ada traffic (0 = permanent)
            hard_timeout: Timeout maksimal (0 = permanent)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Create instruction: apply actions
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        # Create flow mod message
        if buffer_id:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                buffer_id=buffer_id,
                priority=priority,
                match=match,
                instructions=inst,
                idle_timeout=idle_timeout,
                hard_timeout=hard_timeout
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                priority=priority,
                match=match,
                instructions=inst,
                idle_timeout=idle_timeout,
                hard_timeout=hard_timeout
            )

        # Send flow mod to switch
        datapath.send_msg(mod)
