# Scenario 08: DSCP-Based QoS with Packet Loss (13 Switches - Lossy Network)

## Overview

This scenario extends **Scenario 06** by adding **realistic packet loss** to simulate wireless IoT networks (WiFi, LoRa, Zigbee, Cellular). This provides a more realistic testing environment for DSCP-based QoS under lossy network conditions.

**Key Features:**
- 13 OpenFlow switches (1 core + 3 aggregation + 9 edge)
- 19 hosts (1 broker + 18 publishers)
- DSCP tagging in IP headers for traffic prioritization
- 5 priority queues with HTB (Hierarchical Token Bucket)
- **Packet loss simulation** (5% at core, 2% at edge)
- Moderate congestion (108% utilization vs 216% in Scenario 06)

**Compared to Scenario 06:**
- ✅ **Higher bandwidth:** 1.0 Mbps (vs 0.5 Mbps) - moderate congestion
- ✅ **Packet loss enabled:** 5% core links, 2% edge links
- ✅ **Realistic wireless simulation:** WiFi/LoRa/Cellular packet loss patterns
- ✅ **Lower utilization:** 108% (vs 216%) - combined with packet loss creates realistic stress

## Network Topology

```
                    ┌──────┐
                    │  s1  │ CORE (Broker: 10.0.0.1)
                    └───┬──┘  5% packet loss
                        │
          ┌─────────────┼─────────────┐
          │             │             │
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │     │  s3   │     │  s4   │  AGGREGATION
      │Floor 1│     │Floor 2│     │Floor 3│
      └───┬───┘     └───┬───┘     └───┬───┘  2% packet loss
          │             │             │
      ┌───┼───┐     ┌───┼───┐     ┌───┼───┐
      │   │   │     │   │   │     │   │   │
     s5  s6  s7    s8  s9 s10   s11 s12 s13  EDGE (Access)
      │   │   │     │   │   │     │   │   │
    IoT IoT IoT   IoT IoT IoT   IoT IoT IoT
```

**Use Case:** Wireless Smart Building
- **s1:** Core/Gateway switch with wireless backhaul (5% loss)
- **s2-s4:** Aggregation switches (one per floor)
- **s5-s13:** Edge/Access switches with wireless sensors (2% loss)
- **Publishers:** 2 per room (1 anomaly + 1 normal) = 18 total
- **Subnets:**
  - Floor 1: 10.0.1.x/16 (s5, s6, s7)
  - Floor 2: 10.0.2.x/16 (s8, s9, s10)
  - Floor 3: 10.0.3.x/16 (s11, s12, s13)
  - Broker: 10.0.0.1/16

## Network Characteristics

### Packet Loss Configuration

| Link Type                  | Packet Loss | Simulates                        |
|----------------------------|-------------|----------------------------------|
| **Core links** (s1 ↔ broker) | 5%        | Wireless gateway/backhaul (WiFi) |
| **Aggregation links** (s2-s4 ↔ s1) | 5% | Wireless inter-floor links |
| **Edge links** (s5-s13 ↔ s2-s4) | 2%    | Wireless sensor links (LoRa/Zigbee) |
| **Publisher links** (hosts ↔ edge) | 0% | Wired connection to edge switch |

**Why These Values:**
- **5% core loss:** Typical WiFi packet loss in moderate interference
- **2% edge loss:** LoRa/Zigbee typical outdoor packet loss
- **Asymmetric loss:** Core links experience higher loss due to aggregated traffic

### Bandwidth & Congestion

- **Bandwidth:** 1.0 Mbps per link (2x Scenario 06)
- **Message Rate:** 50 msg/s per publisher
- **Total Load:** 18 publishers × 50 msg/s × 60 Kbps = 1.08 Mbps
- **Network Utilization:** 108% (moderate congestion)
- **Total Packet Loss:** ~5-7% end-to-end (combined probability)

**Impact on QoS:**
- DSCP priority STILL matters even with higher bandwidth
- Packet loss creates additional stress beyond congestion
- Tests QoS resilience under realistic wireless conditions

## Priority Levels

This scenario supports **5 DSCP priority levels** with corresponding OVS queues:

| DSCP Value | Traffic Class           | Queue | Bandwidth Allocation | Use Case                    |
|------------|-------------------------|-------|----------------------|-----------------------------|
| **46**     | EF (Expedited Forwarding) | 1     | 60-80% (High)        | Critical anomaly alerts     |
| **34**     | AF41 (High Priority)      | 2     | 45-60% (Medium-High) | Important sensor data       |
| **26**     | AF31 (Medium Priority)    | 3     | 30-45% (Medium)      | Regular monitoring          |
| **10**     | AF11 (Low Priority)       | 4     | 15-30% (Low)         | Background data collection  |
| **0**      | BE (Best Effort)          | 5     | 5-15% (Very Low)     | Non-critical traffic        |

**Note:** Packet loss affects all priority levels, but high-priority traffic gets better bandwidth allocation and queue treatment.

## How It Works

### DSCP Approach with Packet Loss

1. **Publishers** set DSCP value in IP header using socket options
   ```python
   ip_tos = DSCP_VALUE << 2  # Convert DSCP to TOS
   sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, ip_tos)
   ```

2. **Mininet TCLink** applies packet loss using Linux TC NetEm
   ```python
   self.net.addLink(sw, s1, cls=TCLink, bw=1.0, loss=5)  # 5% random loss
   ```

3. **Controller** installs flow rules matching DSCP → Queue mapping
   ```python
   match = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)
   actions = [parser.OFPActionSetQueue(1), parser.OFPActionOutput(NORMAL)]
   ```

4. **Switches** process traffic in data plane with queue prioritization

5. **OVS Queues** enforce bandwidth allocation using HTB

**Combined Effect:**
- High-priority traffic gets better bandwidth allocation
- Packet loss still affects all traffic (realistic)
- DSCP priority reduces impact of congestion
- Results show QoS benefit even under packet loss

## Running the Experiment

### Quick Start

```bash
cd /home/mqtt-sdn/scenarios/08-dscp-qos-13switches-lossy
sudo ./run_experiment.sh 300  # Run for 5 minutes
```

### Configuration

**Packet Loss Settings** (in `topology_config.py`):
```python
ENABLE_PACKET_LOSS = True        # Enable packet loss simulation
CORE_PACKET_LOSS_PCT = 5         # 5% loss at core links
EDGE_PACKET_LOSS_PCT = 2         # 2% loss at edge links
```

**Bandwidth Settings:**
```python
ENABLE_BANDWIDTH_LIMIT = True
LINK_BANDWIDTH_MBPS = 1.0        # 1.0 Mbps (moderate congestion)
MSG_RATE = 50                    # 50 msg/s per publisher
```

**Disable Packet Loss (to compare with Scenario 06):**
```python
ENABLE_PACKET_LOSS = False       # Disable packet loss
```

### Results Location

Results are saved to timestamped directories:
```
/home/mqtt-sdn/results/08-dscp-qos-13switches-lossy/run_YYYY-MM-DD_HH-MM-SS/
├── mqtt_metrics_log.csv      # Detailed per-message metrics
└── metrics_summary.txt        # Aggregated statistics
```

## File Structure

```
08-dscp-qos-13switches-lossy/
├── controller_dscp.py              # DSCP-based controller (5 levels)
├── topology_config.py              # 13-switch topology with packet loss
├── run_experiment.sh               # Automated experiment launcher
├── publisher_dscp46_veryhigh.py    # DSCP 46 (EF - Very High)
├── publisher_dscp34_high.py        # DSCP 34 (AF41 - High)
├── publisher_dscp26_medium.py      # DSCP 26 (AF31 - Medium)
├── publisher_dscp10_low.py         # DSCP 10 (AF11 - Low)
├── publisher_dscp0_besteffort.py   # DSCP 0 (BE - Best Effort)
└── README.md                       # This file
```

## Expected Results

Under lossy network conditions (108% utilization + 5-7% packet loss):

- **DSCP 46 traffic:** Low delay (~5-15 ms), 5-7% packet loss
- **DSCP 34 traffic:** Medium delay (~20-50 ms), 5-7% packet loss
- **DSCP 26 traffic:** Higher delay (~80-150 ms), 6-8% packet loss
- **DSCP 10 traffic:** High delay (~300-600 ms), 8-10% packet loss
- **DSCP 0 traffic:** Very high delay (1000+ ms), 10-15% packet loss

**Key Observations:**
- DSCP priority differentiates delay even with packet loss
- Higher priority traffic may experience slightly lower loss (queue drops vs random loss)
- Jitter increases for low-priority traffic due to combined congestion + loss
- End-to-end packet loss: 5-7% (network) + variable (queue drops)

## Comparison with Scenario 06

| Feature                  | **Scenario 06**    | **Scenario 08**      |
|--------------------------|-------------------|----------------------|
| **Switches**             | 13                | 13                   |
| **Topology**             | 3-tier            | 3-tier               |
| **Publishers**           | 18                | 18                   |
| **Bandwidth**            | 0.5 Mbps          | **1.0 Mbps**         |
| **Packet Loss**          | None (0%)         | **5% core, 2% edge** |
| **Utilization**          | 216% (high)       | **108% (moderate)**  |
| **Stress Type**          | Congestion only   | **Congestion + Loss**|
| **Realism**              | Wired network     | **Wireless network** |
| **Use Case**             | Wired IoT         | **WiFi/LoRa/Cellular IoT** |

**When to Use Each:**
- **Scenario 06:** Testing extreme congestion (wired network)
- **Scenario 08:** Testing realistic wireless conditions (WiFi/LoRa)

## Troubleshooting

### Very High Packet Loss (>20%)

**Cause:** Combined network loss + queue drops due to congestion

**Fix:** Increase bandwidth in `topology_config.py`:
```python
LINK_BANDWIDTH_MBPS = 1.5  # Reduce congestion
```

### No Delay Differentiation

**Cause:** Not enough congestion (packet loss alone doesn't cause queuing)

**Fix:** Decrease bandwidth:
```python
LINK_BANDWIDTH_MBPS = 0.8  # Increase congestion
```

### Packet Loss Not Applied

**Check:** Verify TCLink is enabled in logs:
```bash
grep "Bandwidth limiting ENABLED" /home/mqtt-sdn/logs/mininet.log
```

**Fix:** Ensure both flags are True:
```python
ENABLE_BANDWIDTH_LIMIT = True
ENABLE_PACKET_LOSS = True
```

## Using Different Priority Levels

The scenario provides templates for all 5 DSCP levels. To test a specific priority:

```bash
# On host f1r1a (Floor 1, Room 1, Anomaly)
DEVICE=test_sensor BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp46_veryhigh.py

# On host f2r2n (Floor 2, Room 2, Normal)
DEVICE=test_sensor BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp0_besteffort.py
```

**Environment Variables:**
- `DEVICE`: Sensor identifier
- `BROKER_IP`: MQTT broker IP (default: 10.0.0.1)
- `MSG_RATE`: Messages per second (default: 50)

## References

- **DSCP RFC:** RFC 2474 (Differentiated Services)
- **OpenFlow:** v1.3 specification
- **HTB Queueing:** Linux Hierarchical Token Bucket
- **TC NetEm:** Linux Traffic Control Network Emulation
- **MQTT:** v3.1.1 protocol

## Notes

- Currently uses 2 priority levels (DSCP 46 and 0) for anomaly/normal traffic
- All 5 publisher templates are provided for future expansion
- Controller supports all 5 DSCP levels
- Packet loss is applied at link layer (before queue processing)
- Combined packet loss probability: ~5-7% end-to-end (multi-hop)
