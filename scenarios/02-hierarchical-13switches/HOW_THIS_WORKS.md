# 📚 How This Works: SDN-based Priority Mechanism for IoT Data

**Scenario:** 02-hierarchical-13switches
**Purpose:** Demonstrate priority-based data transmission using Software Defined Networking (SDN)
**Last Updated:** 2025-11-10

---

## 📋 Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Component Roles](#2-component-roles)
3. [Bandwidth Limiting Mechanism](#3-bandwidth-limiting-mechanism)
4. [Queue Configuration](#4-queue-configuration)
5. [Priority Decision Logic](#5-priority-decision-logic)
6. [Packet Journey (End-to-End Flow)](#6-packet-journey-end-to-end-flow)
7. [Why Priority Works](#7-why-priority-works)
8. [Configuration Parameters](#8-configuration-parameters)
9. [Validation & Debugging](#9-validation--debugging)

---

## 1. System Architecture

### 1.1 Control Plane vs Data Plane

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTROL PLANE                                │
│  (Decision Making - Tidak lewatkan traffic)                     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │   RYU CONTROLLER                                      │     │
│  │   Process: python3 ryu-manager                        │     │
│  │   Location: 127.0.0.1:6633 (OpenFlow)                │     │
│  │             127.0.0.1:8080 (REST API)                 │     │
│  │                                                        │     │
│  │   Applications Running:                               │     │
│  │   ├─ controller.py (Our SDN App)                      │     │
│  │   └─ ryu.app.ofctl_rest (Monitoring API)             │     │
│  └───────────────────────────────────────────────────────┘     │
│                             │                                   │
│                             │ OpenFlow Protocol                 │
│                             │ (Flow Rules Installation)         │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PLANE                                   │
│  (Execution - Forward traffic sesuai rules)                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  OPEN vSWITCH (s1, s2, ..., s13)                    │       │
│  │  - Receive flow rules from controller               │       │
│  │  - Match packets against flow table                 │       │
│  │  - Execute actions (queue assignment, forwarding)   │       │
│  │  - Apply bandwidth limits & QoS                     │       │
│  └─────────────────────────────────────────────────────┘       │
│         │                  │                  │                 │
│    Port s5-eth0       Port s5-eth1       Port s5-eth2          │
│    (To s2)            (To f1r1a)         (To f1r1n)            │
│         │                  │                  │                 │
│    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐          │
│    │Queue 1  │        │Queue 1  │        │Queue 1  │          │
│    │70-100%  │        │70-100%  │        │70-100%  │          │
│    │Anomaly  │        │Anomaly  │        │Anomaly  │          │
│    ├─────────┤        ├─────────┤        ├─────────┤          │
│    │Queue 2  │        │Queue 2  │        │Queue 2  │          │
│    │30-50%   │        │30-50%   │        │30-50%   │          │
│    │Normal   │        │Normal   │        │Normal   │          │
│    └────┬────┘        └────┬────┘        └────┬────┘          │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                │
│                            │                                    │
│                   ┌────────▼────────┐                          │
│                   │  Physical Port  │                          │
│                   │  Bandwidth:     │                          │
│                   │  0.05 or 0.1    │                          │
│                   │  Mbps (Limited) │                          │
│                   └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Network Topology

```
                    ┌──────────────┐
                    │ RYU          │ Control Plane
                    │ CONTROLLER   │ (127.0.0.1:6633)
                    └──────┬───────┘
                           │ OpenFlow
                    ┌──────▼───────┐
                    │   s1 (CORE)  │ Data Plane
                    │  + Broker    │ (10.0.0.1)
                    └──────┬───────┘
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼────┐     ┌─────▼────┐     ┌────▼─────┐
    │s2 (AGG)  │     │s3 (AGG)  │     │s4 (AGG)  │
    │ Floor 1  │     │ Floor 2  │     │ Floor 3  │
    └─────┬────┘     └─────┬────┘     └────┬─────┘
          │                │                │
    ┌─────┼────┐     ┌─────┼────┐     ┌────┼─────┐
    │     │    │     │     │    │     │    │     │
 ┌──▼─┬──▼─┬──▼──┐ ┌▼──┬──▼─┬──▼──┐ ┌▼──┬─▼──┬──▼──┐
 │s5  │s6  │s7   │ │s8 │s9  │s10  │ │s11│s12 │s13  │ EDGE
 │.1.x│.1.x│.1.x │ │.2.x│.2.x│.2.x │ │.3.x│.3.x│.3.x│
 └─┬──┴─┬──┴──┬──┘ └─┬─┴──┬─┴──┬──┘ └─┬─┴──┬─┴──┬──┘
   │    │     │      │    │    │      │    │    │
  h1   h2    h3     h4   h5   h6     h7   h8   h9    Publishers
 (a)  (n)   (a)    (n)  (a)  (n)    (a)  (n)  (a)    (18 total)

Legend:
  (a) = anomaly publisher (odd IP: .1, .3, .5) → Queue 1
  (n) = normal publisher (even IP: .2, .4, .6) → Queue 2
```

---

## 2. Component Roles

### 2.1 Ryu Framework

**File:** Ryu is installed in `/home/aldi/ryu39/`

**Role:** SDN Controller Platform
- Provides framework for building SDN applications
- Manages OpenFlow communication with switches
- Handles events (switch connection, packet arrival, etc.)
- Exposes REST API for monitoring

**Analogy:** Operating System for SDN apps

**Important:** Ryu does NOT decide priority! It's just the platform.

---

### 2.2 Priority Controller (Our SDN App)

**File:** `controller.py`

**Role:** Priority Decision Logic
- **Detects** when switches connect to controller
- **Decides** which traffic gets which priority
- **Installs** flow rules to switches via OpenFlow
- **Assigns** packets to Queue 1 or Queue 2

**Key Functions:**

```python
@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
def switch_features_handler(self, ev):
    """Triggered when switch connects to controller"""
    # Identify switch type (core, aggregation, edge)
    # Install appropriate flow rules
```

```python
def install_edge_flows(self, datapath, dpid):
    """Install flow rules for edge switches"""

    # Rule 1: Anomaly traffic → Queue 1
    for ip in [1, 3, 5]:  # Odd IPs
        match = OFPMatch(ipv4_src=f"10.0.{floor}.{ip}", tcp_dst=1883)
        actions = [
            OFPActionSetQueue(1),  # Assign to Queue 1
            OFPActionOutput(NORMAL)
        ]
        add_flow(datapath, priority=20, match, actions)

    # Rule 2: Normal traffic → Queue 2
    for ip in [2, 4, 6]:  # Even IPs
        match = OFPMatch(ipv4_src=f"10.0.{floor}.{ip}", tcp_dst=1883)
        actions = [
            OFPActionSetQueue(2),  # Assign to Queue 2
            OFPActionOutput(NORMAL)
        ]
        add_flow(datapath, priority=15, match, actions)
```

**Analogy:** Traffic cop giving instructions

---

### 2.3 Open vSwitch (OVS)

**Role:** Programmable Software Switch (Data Plane)
- Receives flow rules from controller
- Stores rules in flow table
- Matches incoming packets against flow table
- Executes actions (queue assignment, forwarding)
- Applies bandwidth limits via Linux TC (Traffic Control)

**Flow Table Example (Switch s5):**

```
Priority | Match Condition              | Action
---------|------------------------------|-------------------------
100      | eth_type=ARP                 | OUTPUT(NORMAL)
90       | eth_type=IPv4, ip_proto=ICMP | OUTPUT(NORMAL)
20       | ip_src=10.0.1.1, tcp_dst=1883| SET_QUEUE(1), OUTPUT(NORMAL)
20       | ip_src=10.0.1.3, tcp_dst=1883| SET_QUEUE(1), OUTPUT(NORMAL)
20       | ip_src=10.0.1.5, tcp_dst=1883| SET_QUEUE(1), OUTPUT(NORMAL)
15       | ip_src=10.0.1.2, tcp_dst=1883| SET_QUEUE(2), OUTPUT(NORMAL)
15       | ip_src=10.0.1.4, tcp_dst=1883| SET_QUEUE(2), OUTPUT(NORMAL)
15       | ip_src=10.0.1.6, tcp_dst=1883| SET_QUEUE(2), OUTPUT(NORMAL)
12       | ip_src=10.0.0.1              | OUTPUT(NORMAL)
0        | * (any)                      | DROP
```

**Analogy:** Traffic light executing instructions

---

### 2.4 TC/HTB (Traffic Control / Hierarchical Token Bucket)

**Role:** Kernel-level Bandwidth Management
- Limits bandwidth on each port
- Implements queues (Queue 1, Queue 2)
- Schedules packet transmission based on queue priority
- Enforces bandwidth allocation (70-100% vs 30-50%)

**Location:** Linux kernel (inside Mininet network namespace)

**Analogy:** Physical road width and lane management

---

### 2.5 Mininet TCLink

**File:** `topology_config.py`

**Role:** Network Emulation with Bandwidth Limits

```python
# Create link with bandwidth limit
self.net.addLink(host1, switch1, bw=0.05)  # 0.05 Mbps = 50 Kbps
```

**What happens internally:**
```bash
# Mininet executes these commands in the network namespace:
tc qdisc add dev s1-eth1 root handle 1: htb default 1
tc class add dev s1-eth1 parent 1: classid 1:1 htb rate 0.05mbit
```

**Result:** Physical port `s1-eth1` limited to 50 Kbps maximum throughput

---

## 3. Bandwidth Limiting Mechanism

### 3.1 Where Bandwidth is Limited

**Answer: At EVERY PORT on EVERY SWITCH**

```
Example: Switch s5 has 4 ports, ALL limited:

s5-eth0 (to s2):    50 Kbps ← Link to aggregation switch
s5-eth1 (to f1r1a): 50 Kbps ← Link to anomaly publisher
s5-eth2 (to f1r1n): 50 Kbps ← Link to normal publisher
s5-eth3 (to f1r2a): 50 Kbps ← Link to anomaly publisher
```

**Total:** 13 switches × ~3-4 ports each = ~40 bandwidth-limited links

### 3.2 How Bandwidth Limit is Applied

**File:** `topology_config.py`, lines 56-59

```python
# Configuration
ENABLE_BANDWIDTH_LIMIT = True
LINK_BANDWIDTH_MBPS = 0.05  # ← CHANGE THIS to adjust bandwidth
ENABLE_QOS_QUEUES = True
```

**Process:**

**Step 1: Link Creation (Mininet)**
```python
# Line ~96
self.net.addLink(h_broker, s1, bw=LINK_BANDWIDTH_MBPS)
```

**Step 2: TC Configuration (Automatic)**
```bash
# Mininet internally runs:
tc qdisc add dev s1-eth1 root handle 1: htb default 1
tc class add dev s1-eth1 parent 1: classid 1:1 htb rate 50000  # 50 Kbps
```

**Step 3: OVS Queue Configuration (Manual)**
```python
# Function: configure_ovs_queues(), lines 261-315

max_rate = LINK_BANDWIDTH_MBPS * 1000000  # 0.05 × 1,000,000 = 50,000 bps

# Queue 1 (Anomaly): 70-100% of bandwidth
queue1_min = int(max_rate * 0.7)  # 35,000 bps guaranteed
queue1_max = max_rate              # 50,000 bps maximum

# Queue 2 (Normal): 30-50% of bandwidth
queue2_min = int(max_rate * 0.3)  # 15,000 bps guaranteed
queue2_max = int(max_rate * 0.5)  # 25,000 bps maximum

# Apply to OVS
ovs-vsctl -- set port s5-eth0 qos=@newqos \
  -- --id=@newqos create qos type=linux-htb \
     other-config:max-rate=50000 \
     queues:1=@q1 queues:2=@q2 \
  -- --id=@q1 create queue \
     other-config:min-rate=35000 \
     other-config:max-rate=50000 \
  -- --id=@q2 create queue \
     other-config:min-rate=15000 \
     other-config:max-rate=25000
```

### 3.3 Bandwidth Distribution

```
Total Port Bandwidth: 50 Kbps
│
├─ Queue 1 (Anomaly): 35-50 Kbps
│  ├─ Guaranteed: 35 Kbps (70%)
│  └─ Maximum: 50 Kbps (100% if Queue 2 idle)
│
└─ Queue 2 (Normal): 15-25 Kbps
   ├─ Guaranteed: 15 Kbps (30%)
   └─ Maximum: 25 Kbps (50% even if bandwidth available)
```

**Key Point:** Queue 2 NEVER gets more than 50% even if bandwidth available!

---

## 4. Queue Configuration

### 4.1 Queue Assignment Logic

**Decision made by:** SDN Controller (controller.py)

**Based on:** Source IP address (last octet)

```python
# Edge switch flow rules:

# Anomaly publishers (odd IP: .1, .3, .5) → Queue 1
IP 10.0.1.1 → Queue 1 (Priority 20)
IP 10.0.1.3 → Queue 1 (Priority 20)
IP 10.0.1.5 → Queue 1 (Priority 20)

# Normal publishers (even IP: .2, .4, .6) → Queue 2
IP 10.0.2.2 → Queue 2 (Priority 15)
IP 10.0.2.4 → Queue 2 (Priority 15)
IP 10.0.2.6 → Queue 2 (Priority 15)
```

### 4.2 Queue Properties

| Property | Queue 1 (Anomaly) | Queue 2 (Normal) |
|----------|-------------------|------------------|
| **Min Bandwidth** | 70% (35 Kbps @ 0.05 Mbps) | 30% (15 Kbps @ 0.05 Mbps) |
| **Max Bandwidth** | 100% (50 Kbps @ 0.05 Mbps) | 50% (25 Kbps @ 0.05 Mbps) |
| **Priority** | High | Low |
| **Scheduler** | HTB (Hierarchical Token Bucket) | HTB |
| **Traffic Type** | MQTT from odd IPs | MQTT from even IPs |

### 4.3 Queue Behavior Under Load

**Scenario 1: Low Network Load (< 30%)**
```
Total traffic: 10 Kbps
├─ Queue 1: Gets what it needs (e.g., 5 Kbps)
└─ Queue 2: Gets what it needs (e.g., 5 Kbps)

Result: Both queues happy, no congestion
```

**Scenario 2: Moderate Load (30-70%)**
```
Total traffic: 40 Kbps (exceeds total capacity of 50 Kbps)
├─ Queue 1: Gets 35 Kbps (guaranteed minimum)
└─ Queue 2: Gets 15 Kbps (remaining bandwidth)

Result: Queue 1 prioritized, Queue 2 starts experiencing delay
```

**Scenario 3: High Load (> 70%)**
```
Total traffic: 60 Kbps (both queues want more than available)
├─ Queue 1: Gets 35-50 Kbps (up to 100% of port)
└─ Queue 2: Gets 0-15 Kbps (whatever left)

Result: Queue 1 gets priority, Queue 2 heavily throttled
```

**This is why bandwidth limiting is NECESSARY to see priority effect!**

---

## 5. Priority Decision Logic

### 5.1 Two Types of Priority

**Type 1: Flow Priority (OpenFlow)**
- Controls which flow rule is checked FIRST
- Does NOT affect forwarding speed
- Only determines matching order in flow table

```python
priority=20  # Anomaly flow rule (checked first)
priority=15  # Normal flow rule (checked second)
priority=0   # Default drop (checked last)
```

**Type 2: Queue Priority (QoS)**
- Controls bandwidth allocation
- DOES affect forwarding speed
- Determines delay and throughput

```python
SET_QUEUE(1)  # High priority queue (70-100% bandwidth)
SET_QUEUE(2)  # Low priority queue (30-50% bandwidth)
```

**Important:** Queue priority is what makes anomaly data faster!

### 5.2 Classification Method

**Method:** IP-based classification

**Logic:**
```python
last_octet = int(ip_src.split('.')[-1])

if last_octet in [1, 3, 5]:
    # Odd IP → Anomaly
    queue = 1
    priority = 20
elif last_octet in [2, 4, 6]:
    # Even IP → Normal
    queue = 2
    priority = 15
else:
    # Unknown → Drop
    queue = None
    priority = 0
```

**Alternative:** Could use subnet-based, DSCP, VLAN, or DPI (Deep Packet Inspection)

---

## 6. Packet Journey (End-to-End Flow)

### 6.1 Complete Flow: Anomaly Message

**Scenario:** Publisher `f1r1a` (10.0.1.1) sends MQTT message to broker (10.0.0.1)

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Publisher Sends Message                                │
└─────────────────────────────────────────────────────────────────┘

Host: f1r1a (10.0.1.1)
  ├─ Process: publisher_anomaly.py
  ├─ Creates MQTT packet:
  │    Source IP: 10.0.1.1
  │    Dest IP: 10.0.0.1
  │    Dest Port: 1883 (MQTT)
  │    Payload: {"device":"sensor_f1r1a","type":"anomaly","value":85,...}
  └─ Send via interface f1r1a-eth0
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Edge Switch s5 Receives Packet                         │
└─────────────────────────────────────────────────────────────────┘

Switch: s5 (EDGE)
Port: s5-eth1 (connected to f1r1a)

Action: Packet Arrives
  ├─ Extract headers:
  │    eth_type: 0x0800 (IPv4)
  │    ip_src: 10.0.1.1
  │    ip_dst: 10.0.0.1
  │    ip_proto: 6 (TCP)
  │    tcp_dst: 1883
  │
  ├─ Lookup Flow Table (descending priority):
  │    Priority 100: ARP? NO (eth_type=0x0800, not 0x0806)
  │    Priority 90: ICMP? NO (ip_proto=6, not 1)
  │    Priority 20: ip_src=10.0.1.1, tcp_dst=1883? YES! ✅
  │
  └─ Execute Actions:
       ├─ SET_QUEUE(1) → Assign to Queue 1
       └─ OUTPUT(NORMAL) → Forward to destination (s2)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Queueing at Output Port s5-eth0                        │
└─────────────────────────────────────────────────────────────────┘

Port: s5-eth0 (to aggregation switch s2)
Bandwidth: 50 Kbps total

Queues:
  ├─ Queue 1: [PKT1, PKT2, PKT3, ...]  ← Our packet goes here
  │    - Min: 35 Kbps
  │    - Max: 50 Kbps
  │    - Current load: 18 Kbps
  │
  └─ Queue 2: [PKT10, PKT11, ...]
       - Min: 15 Kbps
       - Max: 25 Kbps
       - Current load: 12 Kbps

HTB Scheduler:
  ├─ Check Queue 1 first (high priority)
  ├─ Dequeue packet from Queue 1
  ├─ Allocate bandwidth: 35 Kbps guaranteed
  └─ Transmit packet
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Aggregation Switch s2 Receives Packet                  │
└─────────────────────────────────────────────────────────────────┘

Switch: s2 (AGGREGATION - Floor 1)
Port: s2-eth2 (from s5)

Action: Lookup Flow Table
  ├─ Priority 20: MQTT to broker? YES! ✅
  └─ Execute Actions:
       └─ OUTPUT(NORMAL) → Forward to s1 (core)

Note: No queue assignment here (already in Queue 1 from edge)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Core Switch s1 Receives Packet                         │
└─────────────────────────────────────────────────────────────────┘

Switch: s1 (CORE)
Port: s1-eth2 (from s2)

Action: Lookup Flow Table
  ├─ Priority 20: MQTT to broker (10.0.0.1)? YES! ✅
  └─ Execute Actions:
       └─ OUTPUT(1) → Forward to broker host via s1-eth1
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Broker Receives Message                                │
└─────────────────────────────────────────────────────────────────┘

Host: broker (10.0.0.1)
Process: mosquitto (MQTT broker)

Action: Receive & Forward to Subscriber
  ├─ Broker receives MQTT PUBLISH message
  ├─ Lookup topic: "iot/data"
  ├─ Forward to subscriber (same host)
  └─ Subscriber calculates delay:
       publish_timestamp = 2025-11-10T15:30:00.000Z
       receive_timestamp = 2025-11-10T15:30:00.032Z
       delay = 32 ms ✅ (Low delay due to Queue 1!)
```

### 6.2 Comparison: Normal Message Flow

**Same path, but different queue:**

```
Host f1r1n (10.0.1.2) → s5 (Queue 2) → s2 → s1 → broker

Key Difference at s5:
  ├─ Match: ip_src=10.0.1.2, tcp_dst=1883 (Priority 15)
  ├─ Action: SET_QUEUE(2) ← Goes to Queue 2!
  └─ Queue 2 properties:
       - Min: 15 Kbps (only 30% guaranteed)
       - Max: 25 Kbps (capped at 50%)
       - Lower priority in scheduler

Result:
  └─ Delay: 35 ms ⚠️ (Higher delay due to Queue 2)
```

---

## 7. Why Priority Works

### 7.1 The Key Mechanism

**Without Congestion (Low Traffic):**
```
Total traffic: 10 Kbps
Available bandwidth: 50 Kbps

Queue 1 (Anomaly): 5 Kbps → Delay: 2 ms
Queue 2 (Normal):  5 Kbps → Delay: 2 ms

Result: NO DIFFERENCE (no congestion, priority not needed!)
```

**With Congestion (High Traffic):**
```
Total traffic: 40 Kbps
Available bandwidth: 50 Kbps (congested at 80%)

Queue 1 (Anomaly): Gets 35 Kbps → Delay: 15 ms ✅
Queue 2 (Normal):  Gets 15 Kbps → Delay: 22 ms ⚠️

Result: 7 ms difference (30% improvement!)
```

**This is why we use 0.05 Mbps bandwidth:**
- Creates congestion (~37% network load)
- Forces scheduler to prioritize Queue 1
- Makes priority effect visible in measurements

### 7.2 Mathematical Model

**Delay Calculation (Simplified):**

```
Delay = Transmission_Delay + Queueing_Delay + Propagation_Delay

Where:
  Transmission_Delay = Packet_Size / Bandwidth
  Queueing_Delay = Queue_Length / Service_Rate
  Propagation_Delay ≈ 0 (virtual network)
```

**Queue 1 (High Priority):**
```
Service_Rate = 35-50 Kbps (70-100%)
Average_Queue_Length = 2 packets (low due to priority)
Queueing_Delay = 2 × 128 bytes / 35000 bps ≈ 5.8 ms
```

**Queue 2 (Low Priority):**
```
Service_Rate = 15-25 Kbps (30-50%)
Average_Queue_Length = 5 packets (high due to low priority)
Queueing_Delay = 5 × 128 bytes / 15000 bps ≈ 34 ms
```

**Result:** Queue 2 has ~6x higher queueing delay!

---

## 8. Configuration Parameters

### 8.1 Bandwidth Configuration

**File:** `topology_config.py`

**Line 56-59:**
```python
ENABLE_BANDWIDTH_LIMIT = True   # Enable/disable bandwidth limiting
LINK_BANDWIDTH_MBPS = 0.05      # Bandwidth per link (Mbps)
ENABLE_QOS_QUEUES = True        # Enable/disable queue configuration
```

**To Change Bandwidth:**
1. Edit `LINK_BANDWIDTH_MBPS` value (e.g., 0.1, 0.5, 1.0)
2. Run test: `sudo ./run_experiment.sh --scenario 02-hierarchical-13switches --duration 120`
3. All queues auto-adjust proportionally

### 8.2 Queue Bandwidth Allocation

**File:** `topology_config.py`

**Line ~290-295:**
```python
# Queue 1 (Anomaly)
queue1_min = int(max_rate * 0.7)  # 70% guaranteed
queue1_max = max_rate              # 100% maximum

# Queue 2 (Normal)
queue2_min = int(max_rate * 0.3)  # 30% guaranteed
queue2_max = int(max_rate * 0.5)  # 50% maximum
```

**To Change Allocation:**
```python
# Example: More aggressive priority (80/20 split)
queue1_min = int(max_rate * 0.8)  # 80% guaranteed
queue2_min = int(max_rate * 0.2)  # 20% guaranteed
```

### 8.3 Flow Rules Priority

**File:** `controller.py`

**Line 138, 158:**
```python
# Anomaly traffic
self.add_flow(datapath, priority=20, match_anomaly, actions_anomaly)

# Normal traffic
self.add_flow(datapath, priority=15, match_normal, actions_normal)
```

**To Change Flow Priority:**
- Higher number = higher priority
- Must maintain: Anomaly > Normal > Default (0)

---

## 9. Validation & Debugging

### 9.1 Verify Flow Rules Installed

```bash
# Check flow table for switch s5
sudo ovs-ofctl -O OpenFlow13 dump-flows s5

# Expected output:
# priority=100,arp actions=NORMAL
# priority=20,tcp,nw_src=10.0.1.1,tp_dst=1883 actions=set_queue:1,NORMAL
# priority=20,tcp,nw_src=10.0.1.3,tp_dst=1883 actions=set_queue:1,NORMAL
# priority=15,tcp,nw_src=10.0.1.2,tp_dst=1883 actions=set_queue:2,NORMAL
# priority=15,tcp,nw_src=10.0.1.4,tp_dst=1883 actions=set_queue:2,NORMAL
```

### 9.2 Verify Queue Configuration

```bash
# Check QoS configuration for port s5-eth0
sudo ovs-vsctl list qos

# Check queues
sudo ovs-vsctl list queue

# Expected: 2 queues per port with min-rate and max-rate configured
```

### 9.3 Verify Bandwidth Limit

```bash
# Check TC configuration on switch port
sudo tc class show dev s5-eth0

# Expected output:
# class htb 1:1 root rate 50Kbit ...
```

### 9.4 Monitor Queue Usage (Real-time)

```bash
# Check packet count per flow rule
sudo ovs-ofctl -O OpenFlow13 dump-flows s5 | grep "set_queue"

# Example output:
# priority=20,tcp,nw_src=10.0.1.1,tp_dst=1883 actions=set_queue:1,NORMAL
#   n_packets=120, n_bytes=15360  ← 120 packets went to Queue 1
# priority=15,tcp,nw_src=10.0.1.2,tp_dst=1883 actions=set_queue:2,NORMAL
#   n_packets=118, n_bytes=15104  ← 118 packets went to Queue 2
```

### 9.5 Common Issues

**Issue 1: No priority effect visible**
- **Cause:** Bandwidth too high, no congestion
- **Fix:** Reduce `LINK_BANDWIDTH_MBPS` to 0.05 or 0.1

**Issue 2: All traffic goes to Queue 1**
- **Cause:** Missing flow rules for Queue 2
- **Fix:** Check controller logs, verify flow rules installed

**Issue 3: HTB quantum warning**
- **Cause:** Very low bandwidth (<0.1 Mbps)
- **Fix:** Add `other-config:r2q=1` to QoS config (optional, cosmetic)

**Issue 4: Zero messages received**
- **Cause:** Flow rules not installed or broker not started
- **Fix:** Check controller logs, verify switches connected

---

## 📚 References

- **Topology Config:** `topology_config.py`
- **SDN Controller:** `controller.py`
- **Publisher Scripts:** `../../shared/mqtt/publisher_*.py`
- **Subscriber Script:** `../../shared/mqtt/subscriber_enhanced.py`
- **Experiment Report:** `EXPERIMENT_REPORT.md`
- **Results:** `../../results/02-hierarchical-13switches/`

---

## 📝 Summary

**Key Takeaways:**

1. **Control Plane (Ryu + controller.py)** decides which traffic gets priority
2. **Data Plane (OVS + TC/HTB)** executes priority via queue assignment
3. **Bandwidth limiting** creates congestion to make priority visible
4. **Queue allocation** (70-100% vs 30-50%) determines actual speed difference
5. **Flow rules** installed at edge switches classify traffic by source IP
6. **Priority effect** only visible under network congestion (>30% load)

**This entire system demonstrates:**
> "Critical IoT data (anomaly) can be transmitted faster than normal data by using SDN-based queue prioritization, especially under network congestion."

---

**Last Updated:** 2025-11-10
**Version:** 2.2 (After controller bug fix)
