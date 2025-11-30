#!/usr/bin/env python3
"""
Flow Manager for Scenario 04

Manages OpenFlow flow rule installation.
"""

from ryu.ofproto import ofproto_v1_3


class FlowManager:
    """
    Manages OpenFlow flow rule installation.

    Provides clean interface for flow operations.
    """

    @staticmethod
    def add_flow(datapath, priority, match, actions, buffer_id=None,
                 idle_timeout=0, hard_timeout=0):
        """
        Install flow rule on switch.

        Args:
            datapath: Datapath object (switch connection)
            priority: Flow priority
            match: OFPMatch object
            actions: List of OFPAction objects
            buffer_id: Buffer ID (optional)
            idle_timeout: Idle timeout in seconds (0 = no timeout)
            hard_timeout: Hard timeout in seconds (0 = no timeout)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Create instructions
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

        # Send flow mod
        datapath.send_msg(mod)

    @staticmethod
    def delete_flow(datapath, priority, match):
        """
        Delete flow rule from switch.

        Args:
            datapath: Datapath object
            priority: Flow priority
            match: OFPMatch object
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            priority=priority,
            match=match
        )

        datapath.send_msg(mod)

    @staticmethod
    def send_packet_out(datapath, in_port, actions, data=None, buffer_id=None):
        """
        Send packet out from switch.

        Args:
            datapath: Datapath object
            in_port: Input port
            actions: List of output actions
            data: Packet data (if buffer_id is None)
            buffer_id: Buffer ID (if packet is buffered)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if buffer_id is None:
            buffer_id = ofproto.OFP_NO_BUFFER

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )

        datapath.send_msg(out)

    @staticmethod
    def create_match(parser, **kwargs):
        """
        Create OFPMatch object.

        Args:
            parser: Datapath parser
            **kwargs: Match fields (in_port, eth_dst, ipv4_src, etc.)

        Returns:
            OFPMatch object
        """
        return parser.OFPMatch(**kwargs)

    @staticmethod
    def create_output_action(parser, port):
        """
        Create output action.

        Args:
            parser: Datapath parser
            port: Output port

        Returns:
            OFPActionOutput object
        """
        return parser.OFPActionOutput(port)

    @staticmethod
    def create_set_queue_action(parser, queue_id):
        """
        Create set queue action.

        Args:
            parser: Datapath parser
            queue_id: Queue ID

        Returns:
            OFPActionSetQueue object
        """
        return parser.OFPActionSetQueue(queue_id)
