#!/usr/bin/env python3
"""
DSCP-Based QoS Controller for Scenario 09 (Ring Topology)
1 Core + 3 Aggregation (Ring) + 9 Edge = 13 Switches

TOPOLOGY:
                                   ┌─────┴─────┐
                                   │    s1     │
                                   │   CORE    │
                                   └─────┬─────┘
                                         │
                ┌────────────────────────┼────────────────────────┐
                │                        │                        │
          ┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐
          │    s2     │◄══════════►│    s3     │◄══════════►│    s4     │
          │   AGG 1   │◄══════════════════════════════════►│   AGG 3   │
          └─────┬─────┘            └─────┬─────┘            └─────┬─────┘
                │                        │                        │
            3 EDGE                    3 EDGE                   3 EDGE

Ring provides redundancy: if s2↔s1 fails, traffic can go s2→s3→s1 or s2→s4→s1

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
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class DSCPQoSController(app_manager.RyuApp):
    """DSCP-based QoS Controller for Ring Topology"""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DSCPQoSController, self).__init__(*args, **kwargs)
        print("="*70)
        print("DSCP-Based QoS Controller Starting (Scenario 09 - Ring)")
        print("="*70)
        print("Topology: 13 switches (1 core + 3 agg ring + 9 edge)")
        print("Ring: s2 ↔ s3 ↔ s4 ↔ s2 (redundancy)")
        print("")
        print("Supported DSCP Values:")
        print("  DSCP 46 (EF)    → Queue 1 (Very High Priority)")
        print("  DSCP 34 (AF41)  → Queue 2 (High Priority)")
        print("  DSCP 26 (AF31)  → Queue 3 (Medium Priority)")
        print("  DSCP 10 (AF11)  → Queue 4 (Low Priority)")
        print("  DSCP 0  (BE)    → Queue 5 (Best Effort)")
        print("="*70)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Install flow rules when switch connects"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        print("="*70)
        print(f"Switch s{dpid} connected! Installing flows...")
        print("="*70)

        # FLOW 1: ARP Traffic (Priority 100)
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        print(f"[s{dpid}] Flow installed: ARP → FLOOD (priority 100)")

        # FLOW 2: DSCP 46 (EF - Very High) → Queue 1
        match_ef = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)
        actions_ef = [
            parser.OFPActionSetQueue(1),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 60, match_ef, actions_ef)
        print(f"[s{dpid}] Flow installed: DSCP 46 (EF) → Queue 1")

        # FLOW 3: DSCP 34 (AF41 - High) → Queue 2
        match_af41 = parser.OFPMatch(eth_type=0x0800, ip_dscp=34)
        actions_af41 = [
            parser.OFPActionSetQueue(2),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 55, match_af41, actions_af41)
        print(f"[s{dpid}] Flow installed: DSCP 34 (AF41) → Queue 2")

        # FLOW 4: DSCP 26 (AF31 - Medium) → Queue 3
        match_af31 = parser.OFPMatch(eth_type=0x0800, ip_dscp=26)
        actions_af31 = [
            parser.OFPActionSetQueue(3),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 50, match_af31, actions_af31)
        print(f"[s{dpid}] Flow installed: DSCP 26 (AF31) → Queue 3")

        # FLOW 5: DSCP 10 (AF11 - Low) → Queue 4
        match_af11 = parser.OFPMatch(eth_type=0x0800, ip_dscp=10)
        actions_af11 = [
            parser.OFPActionSetQueue(4),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 45, match_af11, actions_af11)
        print(f"[s{dpid}] Flow installed: DSCP 10 (AF11) → Queue 4")

        # FLOW 6: DSCP 0 (BE - Best Effort) → Queue 5
        match_be = parser.OFPMatch(eth_type=0x0800, ip_dscp=0)
        actions_be = [
            parser.OFPActionSetQueue(5),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 40, match_be, actions_be)
        print(f"[s{dpid}] Flow installed: DSCP 0 (BE) → Queue 5")

        # FLOW 7: Default Flow
        match_default = parser.OFPMatch()
        actions_default = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 0, match_default, actions_default)
        print(f"[s{dpid}] Flow installed: Default → NORMAL")

        print("="*70)
        print(f"Switch s{dpid} ready!")
        print("="*70)
        print()

    def add_flow(self, datapath, priority, match, actions, buffer_id=None,
                 idle_timeout=0, hard_timeout=0):
        """Helper to install flow rule"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(
                datapath=datapath, buffer_id=buffer_id, priority=priority,
                match=match, instructions=inst,
                idle_timeout=idle_timeout, hard_timeout=hard_timeout
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath, priority=priority, match=match,
                instructions=inst, idle_timeout=idle_timeout, hard_timeout=hard_timeout
            )

        datapath.send_msg(mod)
