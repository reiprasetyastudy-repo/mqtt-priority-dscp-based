#!/usr/bin/env python3
"""
DSCP-Based QoS Controller

Single source controller for all scenarios.
Matches DSCP values in IP header and sets appropriate queues.

Flow Rules:
- ARP traffic     → FLOOD (priority 100)
- DSCP 46 (EF)    → Queue 1 - Very High Priority (priority 60)
- DSCP 0  (BE)    → Queue 5 - Best Effort (priority 40)
- Default         → NORMAL (priority 0)
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class DSCPQoSController(app_manager.RyuApp):
    """
    SDN Controller with DSCP-based QoS.
    
    Matches DSCP value in IP header and assigns traffic to queues:
    - DSCP 46 (Expedited Forwarding) → Queue 1 (high priority)
    - DSCP 0  (Best Effort)          → Queue 5 (low priority)
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DSCPQoSController, self).__init__(*args, **kwargs)
        self._print_banner()

    def _print_banner(self):
        """Print controller startup banner."""
        print("=" * 60)
        print("  DSCP-Based QoS Controller")
        print("=" * 60)
        print("  DSCP 46 (EF) → Queue 1 (High Priority)")
        print("  DSCP 0  (BE) → Queue 5 (Best Effort)")
        print("=" * 60)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Install flow rules when switch connects."""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        print(f"[Controller] Switch s{dpid} connected, installing flows...")

        # Flow 1: ARP → FLOOD
        self._add_flow(
            datapath, 100,
            parser.OFPMatch(eth_type=0x0806),
            [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        )

        # Flow 2: DSCP 46 (EF) → Queue 1
        self._add_flow(
            datapath, 60,
            parser.OFPMatch(eth_type=0x0800, ip_dscp=46),
            [parser.OFPActionSetQueue(1),
             parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        )

        # Flow 3: DSCP 0 (BE) → Queue 5
        self._add_flow(
            datapath, 40,
            parser.OFPMatch(eth_type=0x0800, ip_dscp=0),
            [parser.OFPActionSetQueue(5),
             parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        )

        # Flow 4: Default → NORMAL
        self._add_flow(
            datapath, 0,
            parser.OFPMatch(),
            [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        )

        print(f"[Controller] Switch s{dpid} ready (4 flows installed)")

    def _add_flow(self, datapath, priority, match, actions):
        """Helper to install a flow rule."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )

        datapath.send_msg(mod)
