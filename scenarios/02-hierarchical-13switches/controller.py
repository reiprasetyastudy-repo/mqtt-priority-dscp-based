#!/usr/bin/env python3
"""
=================================================================================
Hierarchical SDN Controller for IoT Priority-Based Data Transmission
=================================================================================

PURPOSE:
Demonstrate bahwa anomaly/critical IoT data dapat ditransmisikan lebih cepat
daripada normal data menggunakan SDN queue-based prioritization.

=================================================================================
ARCHITECTURE: 3-Tier Hierarchical Topology
=================================================================================

Topology (13 switches, 19 hosts):
- Layer 1 CORE:        s1 (gateway + broker @ 10.0.0.1)
- Layer 2 AGGREGATION: s2-s4 (per-floor switches)
- Layer 3 EDGE:        s5-s13 (per-room switches, 18 IoT publishers)

Network Mapping:
- 10.0.1.0/24 = Floor 1 (s5, s6, s7)    → 6 publishers
- 10.0.2.0/24 = Floor 2 (s8, s9, s10)   → 6 publishers
- 10.0.3.0/24 = Floor 3 (s11, s12, s13) → 6 publishers
- 10.0.0.0/24 = Core    (s1)            → 1 broker

=================================================================================
HOW PRIORITY MECHANISM WORKS (Step-by-Step)
=================================================================================

1. TRAFFIC CLASSIFICATION (at Edge Layer)
   ----------------------------------------
   - Anomaly publishers use ODD IPs:  10.0.x.1, 10.0.x.3, 10.0.x.5
   - Normal publishers use EVEN IPs:  10.0.x.2, 10.0.x.4, 10.0.x.6
   - Controller installs flow rules to match source IP + tcp_dst=1883

2. QUEUE ASSIGNMENT (at Edge Layer)
   ---------------------------------
   - Anomaly traffic → OFPActionSetQueue(1) → Queue 1 (HIGH PRIORITY)
   - Normal traffic  → OFPActionSetQueue(2) → Queue 2 (LOW PRIORITY)

3. OVS QUEUE CONFIGURATION (via topology_config.py)
   -------------------------------------------------
   - Queue 1: min=70% BW, max=100% BW (guaranteed high bandwidth)
   - Queue 2: min=30% BW, max=50% BW  (limited bandwidth)
   - Uses Linux HTB (Hierarchical Token Bucket) for rate limiting

4. HTB SCHEDULING (at Kernel Level)
   ---------------------------------
   - Saat congestion terjadi (>70% utilization):
     * Queue 1 packets diproses LEBIH DULU
     * Queue 2 packets MENUNGGU sampai Queue 1 selesai
     * Result: Anomaly delay < Normal delay

5. PACKET JOURNEY
   --------------
   [Publisher 10.0.1.1]
        ↓ (MQTT publish)
   [Edge Switch s5] ← CLASSIFICATION HAPPENS HERE!
        ↓ (Queue 1 assigned, priority 20)
   [Agg Switch s2]  ← Queue maintained
        ↓
   [Core Switch s1] ← Queue maintained
        ↓
   [Broker 10.0.0.1]

=================================================================================
FLOW RULES PRIORITY HIERARCHY
=================================================================================

Edge Switches (s5-s13):
  Priority 100: ARP traffic              → NORMAL (required for connectivity)
  Priority 90:  ICMP traffic             → NORMAL (for testing: pingall)
  Priority 20:  Anomaly MQTT (odd IPs)   → Queue 1 + NORMAL
  Priority 15:  Normal MQTT (even IPs)   → Queue 2 + NORMAL
  Priority 12:  Broker return traffic    → NORMAL (TCP ACK, responses)
  Priority 0:   Default (unknown)        → DROP (security)

Aggregation Switches (s2-s4):
  Priority 100: ARP                      → NORMAL
  Priority 90:  ICMP                     → NORMAL
  Priority 20:  MQTT to broker           → NORMAL (maintain queue from edge)
  Priority 15:  Broker return            → NORMAL
  Priority 10:  Other IP traffic         → NORMAL
  Priority 0:   Default                  → DROP

Core Switch (s1):
  Priority 100: ARP                      → NORMAL
  Priority 90:  ICMP                     → NORMAL
  Priority 20:  MQTT to broker           → NORMAL
  Priority 15:  Broker return            → NORMAL
  Priority 10:  Other IP traffic         → NORMAL
  Priority 0:   Default                  → DROP

=================================================================================
KEY DESIGN DECISIONS
=================================================================================

WHY IP-based classification (not subnet-based)?
  ✓ More specific control (per-device granularity)
  ✓ Prevents bug: all traffic going to same queue
  ✓ Scalable: each device gets explicit flow rule

WHY Queue assignment at Edge layer?
  ✓ Closest to traffic source
  ✓ Early classification prevents congestion propagation
  ✓ Aggregation/Core switches respect queue from edge

WHY OFPP_NORMAL action?
  ✓ Leverage OVS built-in MAC learning (simpler than explicit rules)
  ✓ Queue assignment persists through NORMAL forwarding
  ✓ Reduces controller complexity (no per-port output rules)

WHY Priority 20 for anomaly, 15 for normal?
  ✓ Priority determines OpenFlow matching order (higher = checked first)
  ✓ Prevents anomaly flows from accidentally matching normal rules
  ✓ Clear separation for debugging (distinct priority levels)

WHY ARP at Priority 100?
  ✓ Without ARP, IP-to-MAC resolution fails → no connectivity
  ✓ Must be processed before ANY other traffic
  ✓ Critical for network bootstrapping

=================================================================================
VALIDATION COMMANDS (untuk testing)
=================================================================================

1. Check flow rules installed:
   $ sudo ovs-ofctl -O OpenFlow13 dump-flows s5

2. Check queue configuration:
   $ sudo ovs-vsctl list qos
   $ sudo ovs-vsctl list queue

3. Check queue statistics (real-time):
   $ sudo ovs-ofctl -O OpenFlow13 dump-queues s5

4. Test connectivity:
   $ sudo mn -c
   $ sudo python3 topology_config.py
   mininet> pingall
   mininet> h1 ping -c 3 10.0.0.1

5. Monitor traffic classification:
   $ tail -f /home/mqtt-sdn/logs/ryu.log

=================================================================================
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types


class HierarchicalQoSController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(HierarchicalQoSController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        # Switch layer mapping
        self.CORE_SWITCHES = [1]
        self.AGG_SWITCHES = [2, 3, 4]
        self.EDGE_SWITCHES = list(range(5, 14))  # 5-13

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id

        self.logger.info("=" * 70)
        self.logger.info(f"[Ryu] Switch Connected: s{dpid} (dpid={dpid})")
        self.logger.info("=" * 70)

        # Determine switch layer and install appropriate flows
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
            self.logger.warning(f"[Ryu] Unknown switch s{dpid}, using default flows")
            self.install_default_flows(datapath)

        self.logger.info(f"[Ryu] Flow installation complete for s{dpid}")
        self.logger.info("=" * 70)

    def add_flow(self, datapath, priority, match, actions, queue_id=None):
        """
        Add a flow entry to the switch's flow table

        HOW OPENFLOW WORKS:
        1. Controller (Ryu) mengirim pesan OFPFlowMod ke switch
        2. Switch menyimpan flow rule di flow table (in-memory)
        3. Setiap packet yang masuk di-compare dengan flow table
        4. Packet match dengan rule tertinggi priority → execute actions
        5. Jika tidak ada match → hit default rule (priority 0)

        Parameters:
        - datapath: OpenFlow switch connection object
        - priority: Integer (0-65535), higher = diproses lebih dulu
        - match: OFPMatch object dengan criteria (src_ip, dst_port, etc)
        - actions: List of OFPAction objects (SetQueue, Output, etc)
        - queue_id: (unused) kept for backward compatibility

        FLOW TABLE EXAMPLE (after installation):
        Priority | Match                              | Action
        ---------|------------------------------------|-----------------------
        100      | eth_type=0x0806                   | output:NORMAL
        20       | ipv4_src=10.0.1.1, tcp_dst=1883   | set_queue:1, output:NORMAL
        15       | ipv4_src=10.0.1.2, tcp_dst=1883   | set_queue:2, output:NORMAL
        0        | (empty match)                      | drop

        OpenFlow Message Flow:
        Controller → OFPFlowMod → Switch → Flow Table Updated
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Create instruction: Apply actions immediately (not write to action set)
        # OFPIT_APPLY_ACTIONS = execute actions in-order saat packet match
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        # Create flow modification message
        mod = parser.OFPFlowMod(
            datapath=datapath,    # Target switch
            priority=priority,     # Flow priority (higher = checked first)
            match=match,           # Match criteria
            instructions=inst      # Actions to execute
        )

        # Send message to switch via OpenFlow protocol
        datapath.send_msg(mod)

    def install_edge_flows(self, datapath, dpid):
        """
        Install flows for Edge switches (s5-s13)

        CRITICAL FUNCTION: Ini adalah titik PERTAMA dimana traffic classification terjadi!

        Logic Flow:
        1. Classify MQTT traffic based on SOURCE IP (odd=anomaly, even=normal)
           - Anomaly: 10.0.x.1, 10.0.x.3, 10.0.x.5 (IP ganjil)
           - Normal:  10.0.x.2, 10.0.x.4, 10.0.x.6 (IP genap)

        2. Assign to appropriate OVS Queue:
           - Anomaly → Queue 1 (guaranteed 70% bandwidth, max 100%)
           - Normal  → Queue 2 (guaranteed 30% bandwidth, max 50%)

        3. Forward packet ke aggregation layer menggunakan OFPP_NORMAL
           - OFPP_NORMAL = biarkan OVS handle MAC learning & forwarding
           - Queue assignment tetap attached ke packet saat forwarding

        Why IP-based classification?
        - Lebih specific daripada subnet-based (per-device control)
        - Mencegah false classification (semua traffic ke queue yang sama)
        - Scalable untuk topologi besar dengan banyak publisher

        Why Queue at Edge Layer?
        - Queue assignment harus dilakukan SEBELUM congestion terjadi
        - Edge switch adalah titik terdekat dengan source traffic
        - Aggregation & Core switch akan respect queue priority dari edge
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Determine which floor this edge switch belongs to
        # Math logic: dpid 5-7 → floor 1, dpid 8-10 → floor 2, dpid 11-13 → floor 3
        floor = ((dpid - 5) // 3) + 1  # s5-s7=floor1, s8-s10=floor2, s11-s13=floor3
        subnet = f"10.0.{floor}.0"

        self.logger.info(f"  Edge switch s{dpid} handles Floor {floor} subnet {subnet}/24")

        # ====================
        # Priority 100: ARP (Address Resolution Protocol)
        # ====================
        # WHY Priority 100 (highest)?
        # - ARP HARUS diproses sebelum semua traffic lain
        # - Tanpa ARP, tidak ada IP-to-MAC mapping → network tidak berfungsi
        # - Jika ARP di-drop, MQTT traffic tidak akan bisa reach destination
        #
        # Flow Match:
        # - eth_type=0x0806 → Ethernet type untuk ARP packets
        #
        # Action:
        # - OFPP_NORMAL → Biarkan OVS handle ARP processing (MAC learning)
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        self.logger.info(f"  ✓ ARP traffic: priority 100 → NORMAL")

        # ====================
        # Priority 90: ICMP (Internet Control Message Protocol)
        # ====================
        # For ping testing & network diagnostics
        # - Allows testing connectivity dengan command: pingall, ping 10.0.x.x
        # - Priority 90 → di bawah ARP tapi di atas MQTT traffic
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 90, match_icmp, actions_icmp)

        # ====================
        # Priority 20: Anomaly MQTT Traffic (odd IPs) → Queue 1
        # ====================
        # CRITICAL: Ini adalah CORE LOGIC untuk priority mechanism!
        #
        # WHY Priority 20 (high)?
        # - Harus diproses SEBELUM normal traffic (priority 15)
        # - Kalau sama-sama priority 20, OpenFlow akan match FIRST INSTALLED
        #
        # Flow Match Criteria (MUST ALL MATCH):
        # - eth_type=0x0800    → IPv4 packet
        # - ipv4_src=10.0.x.y  → Source IP (specific per publisher)
        # - ip_proto=6         → TCP protocol
        # - tcp_dst=1883       → MQTT broker port
        #
        # Actions (executed IN ORDER):
        # 1. OFPActionSetQueue(1) → Assign packet ke Queue 1 (HIGH PRIORITY)
        #    - Queue 1 config: min=70% BW, max=100% BW
        #    - HTB akan guarantee 70% bandwidth untuk queue ini
        #    - Saat ada congestion, queue 1 akan dapat bandwidth lebih dulu
        #
        # 2. OFPActionOutput(OFPP_NORMAL) → Forward packet
        #    - OFPP_NORMAL = gunakan MAC learning table OVS
        #    - Packet akan di-forward ke aggregation switch
        #    - Queue assignment tetap attached ke packet!
        #
        # Loop through 3 anomaly publishers per edge switch (IP .1, .3, .5)
        anomaly_ips = [1, 3, 5]
        for ip_suffix in anomaly_ips:
            ip_addr = f"10.0.{floor}.{ip_suffix}"
            match_anomaly = parser.OFPMatch(
                eth_type=0x0800,      # IPv4
                ipv4_src=ip_addr,     # Source IP (specific device)
                ip_proto=6,           # TCP
                tcp_dst=1883          # MQTT port
            )
            actions_anomaly = [
                parser.OFPActionSetQueue(1),  # HIGH PRIORITY QUEUE
                parser.OFPActionOutput(ofproto.OFPP_NORMAL)
            ]
            self.add_flow(datapath, 20, match_anomaly, actions_anomaly)
        self.logger.info(f"  ✓ Anomaly MQTT (odd IPs .1,.3,.5) → Queue 1, priority 20")

        # ====================
        # Priority 15: Normal MQTT Traffic (even IPs) → Queue 2
        # ====================
        # WHY Priority 15 (lower than anomaly)?
        # - Normal traffic TIDAK prioritas, boleh delay lebih lama
        # - Priority lebih rendah = diproses SETELAH anomaly traffic
        # - Kalau congestion terjadi, normal traffic akan antri lebih lama
        #
        # Flow Match: Sama seperti anomaly, tapi IP genap (.2, .4, .6)
        #
        # Actions:
        # 1. OFPActionSetQueue(2) → Assign ke Queue 2 (LOW PRIORITY)
        #    - Queue 2 config: min=30% BW, max=50% BW
        #    - Hanya guaranteed 30% bandwidth
        #    - Max capped at 50% (tidak boleh "curi" bandwidth anomaly)
        #
        # 2. OFPActionOutput(OFPP_NORMAL) → Forward packet
        #
        # Loop through 3 normal publishers per edge switch (IP .2, .4, .6)
        normal_ips = [2, 4, 6]
        for ip_suffix in normal_ips:
            ip_addr = f"10.0.{floor}.{ip_suffix}"
            match_normal = parser.OFPMatch(
                eth_type=0x0800,      # IPv4
                ipv4_src=ip_addr,     # Source IP (specific device)
                ip_proto=6,           # TCP
                tcp_dst=1883          # MQTT port
            )
            actions_normal = [
                parser.OFPActionSetQueue(2),  # LOW PRIORITY QUEUE
                parser.OFPActionOutput(ofproto.OFPP_NORMAL)
            ]
            self.add_flow(datapath, 15, match_normal, actions_normal)
        self.logger.info(f"  ✓ Normal MQTT (even IPs .2,.4,.6) → Queue 2, priority 15")

        # ====================
        # Priority 12: Broker Return Traffic
        # ====================
        # WHY Priority 12?
        # - Broker response (MQTT ACK, PUBLISH to subscribers) harus work
        # - Tanpa ini, TCP handshake tidak complete → connection fail
        # - Priority 12 = di antara normal traffic (15) dan default (10)
        #
        # Flow Match:
        # - ipv4_src=10.0.0.1 → Traffic FROM broker
        # - Tidak perlu match tcp_src karena broker bisa gunakan ephemeral ports
        #
        # Action:
        # - OFPP_NORMAL → Forward balik ke publisher via MAC learning
        # - TIDAK perlu queue assignment (return traffic biasanya kecil: ACK packets)
        match_broker = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src="10.0.0.1"   # FROM broker
        )
        actions_broker = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 12, match_broker, actions_broker)
        self.logger.info(f"  ✓ Broker return traffic: priority 12 → NORMAL")

        # ====================
        # Priority 0: Drop All Other Traffic (Default Deny)
        # ====================
        # WHY Priority 0 (lowest)?
        # - Semua traffic yang TIDAK match rule di atas akan hit rule ini
        # - Security: Unknown traffic di-DROP (not forwarded)
        # - Performance: Prevent unnecessary traffic flooding network
        #
        # Flow Match:
        # - Empty match = match EVERYTHING
        #
        # Action:
        # - Empty actions = DROP packet (tidak ada output port)
        match_default = parser.OFPMatch()
        actions_default = []  # Empty = DROP
        self.add_flow(datapath, 0, match_default, actions_default)
        self.logger.info(f"  ✓ Default: priority 0 → DROP")

    def install_aggregation_flows(self, datapath):
        """
        Install flows for Aggregation switches (s2-s4)

        Function:
        1. Forward MQTT traffic from edge switches to core
        2. Maintain queue priority from edge layer
        3. Forward broker return traffic back to edge
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        floor = dpid - 1  # s2=floor1, s3=floor2, s4=floor3
        self.logger.info(f"  Aggregation switch s{dpid} for Floor {floor}")

        # ====================
        # Priority 100: ARP
        # ====================
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        self.logger.info(f"  ✓ ARP traffic: priority 100 → NORMAL")

        # ====================
        # Priority 90: ICMP
        # ====================
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 90, match_icmp, actions_icmp)

        # ====================
        # Priority 20: MQTT traffic to broker (maintain queue priority)
        # ====================
        match_mqtt = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_dst="10.0.0.1",  # To broker
            ip_proto=6,
            tcp_dst=1883
        )
        actions_mqtt = [
            # Queue priority maintained from edge layer via 802.1p or queue id
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]
        self.add_flow(datapath, 20, match_mqtt, actions_mqtt)
        self.logger.info(f"  ✓ MQTT to broker: priority 20 → NORMAL (queue maintained)")

        # ====================
        # Priority 15: Broker return traffic
        # ====================
        match_broker = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src="10.0.0.1"
        )
        actions_broker = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 15, match_broker, actions_broker)
        self.logger.info(f"  ✓ Broker return: priority 15 → NORMAL")

        # ====================
        # Priority 10: Inter-floor traffic (if any)
        # ====================
        match_other = parser.OFPMatch(eth_type=0x0800)
        actions_other = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 10, match_other, actions_other)
        self.logger.info(f"  ✓ Other IP traffic: priority 10 → NORMAL")

        # ====================
        # Priority 0: Drop
        # ====================
        match_default = parser.OFPMatch()
        actions_default = []
        self.add_flow(datapath, 0, match_default, actions_default)
        self.logger.info(f"  ✓ Default: priority 0 → DROP")

    def install_core_flows(self, datapath):
        """
        Install flows for Core switch (s1)

        Function:
        1. Forward MQTT traffic to broker host
        2. Forward broker responses back to publishers
        3. Handle inter-floor routing if needed
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info(f"  Core switch - Gateway to broker @ 10.0.0.1")

        # ====================
        # Priority 100: ARP
        # ====================
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)
        self.logger.info(f"  ✓ ARP traffic: priority 100 → NORMAL")

        # ====================
        # Priority 90: ICMP
        # ====================
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 90, match_icmp, actions_icmp)

        # ====================
        # Priority 20: MQTT traffic to broker
        # ====================
        match_mqtt = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_dst="10.0.0.1",
            ip_proto=6,
            tcp_dst=1883
        )
        actions_mqtt = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 20, match_mqtt, actions_mqtt)
        self.logger.info(f"  ✓ MQTT to broker (10.0.0.1): priority 20 → NORMAL")

        # ====================
        # Priority 15: Broker return traffic
        # ====================
        match_broker = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src="10.0.0.1"
        )
        actions_broker = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 15, match_broker, actions_broker)
        self.logger.info(f"  ✓ Broker return traffic: priority 15 → NORMAL")

        # ====================
        # Priority 10: All other IP traffic
        # ====================
        match_ip = parser.OFPMatch(eth_type=0x0800)
        actions_ip = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 10, match_ip, actions_ip)
        self.logger.info(f"  ✓ Other IP traffic: priority 10 → NORMAL")

        # ====================
        # Priority 0: Drop
        # ====================
        match_default = parser.OFPMatch()
        actions_default = []
        self.add_flow(datapath, 0, match_default, actions_default)
        self.logger.info(f"  ✓ Default: priority 0 → DROP")

    def install_default_flows(self, datapath):
        """Fallback flows for unknown switches"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # ARP
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 100, match_arp, actions_arp)

        # All traffic to NORMAL (let spanning tree handle it)
        match_all = parser.OFPMatch()
        actions_all = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        self.add_flow(datapath, 10, match_all, actions_all)

        self.logger.info(f"  ✓ Default flows installed (NORMAL forwarding)")
