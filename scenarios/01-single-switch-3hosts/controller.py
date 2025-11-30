from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp

class PriorityController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def add_flow(self, datapath, priority, match, actions):
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

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        print("[Ryu] ==== SWITCH CONNECTED! Installing flows... ====")
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # 1️⃣ Default flow - drop unknown packets
        match = parser.OFPMatch()
        actions = []
        self.add_flow(datapath, 0, match, actions)

        # 2️⃣ Normal traffic (queue 2) - FIXED: added eth_type
        match_normal = parser.OFPMatch(eth_type=0x0800, ipv4_src="10.0.0.2", ip_proto=6, tcp_dst=1883)
        actions_normal = [
            parser.OFPActionSetQueue(2),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 10, match_normal, actions_normal)

        # 3️⃣ Anomaly traffic (queue 1) - FIXED: added eth_type
        match_anomaly = parser.OFPMatch(eth_type=0x0800, ipv4_src="10.0.0.1", ip_proto=6, tcp_dst=1883)
        actions_anomaly = [
            parser.OFPActionSetQueue(1),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 20, match_anomaly, actions_anomaly)

        # 4️⃣ Allow return traffic from broker (h3) to clients
        match_broker = parser.OFPMatch(eth_type=0x0800, ipv4_src="10.0.0.3")
        actions_broker = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 15, match_broker, actions_broker)

        # 5️⃣ Allow ARP traffic (required for IP resolution)
        match_arp = parser.OFPMatch(eth_type=0x0806)  # ARP
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)

        print("[Ryu] Flow rules installed:")
        print(" - Queue 1: anomaly (10.0.0.1 → port 1883)")
        print(" - Queue 2: normal (10.0.0.2 → port 1883)")
        print(" - Priority 15: broker return traffic (10.0.0.3 → any)")
        print(" - Priority 100: ARP traffic")
