# Scenario 07: DSCP-Based QoS (13 Switches - Core Bottleneck)

## Overview

This scenario uses the same **hierarchical 3-tier topology** as Scenario 06, but with a **critical architectural difference**: bandwidth limiting is applied **only at the core switch (s1)**, creating a realistic backbone bottleneck scenario.

**Key Difference from Scenario 06:**
- **Scenario 06**: All links limited to 0.5 Mbps (congestion everywhere)
- **Scenario 07**: Only core switch limited to 0.5 Mbps, other links at 10 Mbps (realistic backbone bottleneck)

**Key Features:**
- 13 OpenFlow switches (1 core + 3 aggregation + 9 edge)
- 19 hosts (1 broker + 18 publishers)
- **Core bottleneck:** s1 links at 0.5 Mbps (216% utilization)
- **High-capacity edge:** Other links at 10 Mbps (10.8% utilization)
- DSCP tagging in IP headers for traffic prioritization
- 5 priority queues with HTB (Hierarchical Token Bucket)
- 3-hop network depth (edge → aggregation → core)

## Network Topology

```
                    ┌──────┐
                    │  s1  │ CORE (Broker: 10.0.0.1)
                    └───┬──┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │     │  s3   │     │  s4   │  AGGREGATION
      │Floor 1│     │Floor 2│     │Floor 3│
      └───┬───┘     └───┬───┘     └───┬───┘
          │             │             │
      ┌───┼───┐     ┌───┼───┐     ┌───┼───┐
      │   │   │     │   │   │     │   │   │
     s5  s6  s7    s8  s9 s10   s11 s12 s13  EDGE (Access)
      │   │   │     │   │   │     │   │   │
    IoT IoT IoT   IoT IoT IoT   IoT IoT IoT
```

**Use Case:** Smart Building
- **s1:** Core/Gateway switch with broker
- **s2-s4:** Aggregation switches (one per floor)
- **s5-s13:** Edge/Access switches (one per room, 9 total)
- **Publishers:** 2 per room (1 anomaly + 1 normal) = 18 total
- **Subnets:**
  - Floor 1: 10.0.1.x/16 (s5, s6, s7)
  - Floor 2: 10.0.2.x/16 (s8, s9, s10)
  - Floor 3: 10.0.3.x/16 (s11, s12, s13)
  - Broker: 10.0.0.1/16

## Priority Levels

This scenario supports **5 DSCP priority levels** with corresponding OVS queues:

| DSCP Value | Traffic Class           | Queue | Bandwidth Allocation | Use Case                    |
|------------|-------------------------|-------|----------------------|-----------------------------|
| **46**     | EF (Expedited Forwarding) | 1     | 60-80% (High)        | Critical anomaly alerts     |
| **34**     | AF41 (High Priority)      | 2     | 45-60% (Medium-High) | Important sensor data       |
| **26**     | AF31 (Medium Priority)    | 3     | 30-45% (Medium)      | Regular monitoring          |
| **10**     | AF11 (Low Priority)       | 4     | 15-30% (Low)         | Background data collection  |
| **0**      | BE (Best Effort)          | 5     | 5-15% (Very Low)     | Non-critical traffic        |

## How It Works

### DSCP Approach (Simple & Efficient)

1. **Publishers** set DSCP value in IP header using socket options
   ```python
   ip_tos = DSCP_VALUE << 2  # Convert DSCP to TOS
   sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, ip_tos)
   ```

2. **Controller** installs flow rules matching DSCP → Queue mapping
   ```python
   match = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)
   actions = [parser.OFPActionSetQueue(1), parser.OFPActionOutput(NORMAL)]
   ```

3. **Switches** process traffic in data plane (no packet-in needed)

4. **OVS Queues** enforce bandwidth allocation using HTB

**Advantages over Scenario 03 (MAC Learning):**
- ✅ No MAC learning table needed
- ✅ No packet-in processing overhead
- ✅ Simpler controller logic
- ✅ More scalable (data plane processing)

## Running the Experiment

### Quick Start

```bash
cd /home/mqtt-sdn/scenarios/07-dscp-qos-13switches-core-bottleneck
sudo ./run_experiment.sh 300  # Run for 5 minutes
```

### Default Configuration

- **Core Switch (s1) Bandwidth:** 0.5 Mbps (BOTTLENECK)
- **Other Links Bandwidth:** 10 Mbps (high capacity)
- **Message Rate:** 50 msg/s per publisher
- **Total Load:** 18 publishers × 50 msg/s = 900 msg/s (1.08 Mbps)
- **Core Utilization:** 1080 Kbps / 500 Kbps = ~216% (highly congested at core)
- **Edge Utilization:** 1080 Kbps / 10,000 Kbps = ~10.8% (no congestion at edge)

### Results Location

Results are saved to timestamped directories:
```
/home/mqtt-sdn/results/07-dscp-qos-13switches-core-bottleneck/run_YYYY-MM-DD_HH-MM-SS/
├── mqtt_metrics_log.csv      # Detailed per-message metrics
└── metrics_summary.txt        # Aggregated statistics
```

## Why Core Bottleneck?

This scenario is **more realistic** than uniform bandwidth limiting because:

1. **Enterprise Networks:** Core/backbone switches typically have more traffic than edge switches
2. **Internet Architecture:** Bottlenecks often occur at gateway/core routers, not at access layer
3. **Cloud Connectivity:** Uplink to cloud/internet is often limited, while internal network is fast
4. **Cost Optimization:** Edge switches are cheaper with higher capacity, core switches handle aggregated traffic

**Real-World Example:**
- Office building with 1 Gbps edge switches
- But only 100 Mbps internet uplink (core bottleneck)
- Internal traffic flows fast, but internet-bound traffic competes for limited bandwidth

## Bandwidth Distribution

| Layer | Switches | Bandwidth per Link | Congestion Level |
|-------|----------|-------------------|------------------|
| **Core** | s1 | 0.5 Mbps | **HIGH** (216% utilization) |
| **Aggregation** | s2, s3, s4 | 10 Mbps | Low (10.8% utilization) |
| **Edge** | s5-s13 | 10 Mbps | Low (10.8% utilization) |

The bottleneck is **only at the core switch**, making priority differentiation most visible there.

## File Structure

```
07-dscp-qos-13switches-core-bottleneck/
├── controller_dscp.py              # DSCP-based controller (5 levels)
├── topology_config.py              # 13-switch hierarchical topology with core bottleneck
├── run_experiment.sh               # Automated experiment launcher
├── publisher_dscp46_veryhigh.py    # DSCP 46 (EF - Very High)
├── publisher_dscp34_high.py        # DSCP 34 (AF41 - High)
├── publisher_dscp26_medium.py      # DSCP 26 (AF31 - Medium)
├── publisher_dscp10_low.py         # DSCP 10 (AF11 - Low)
├── publisher_dscp0_besteffort.py   # DSCP 0 (BE - Best Effort)
└── README.md                       # This file
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

## Expected Results

Under high congestion (216% utilization), you should observe:

- **DSCP 46 traffic:** Very low delay (~1-5 ms)
- **DSCP 34 traffic:** Low delay (~10-30 ms)
- **DSCP 26 traffic:** Medium delay (~50-100 ms)
- **DSCP 10 traffic:** High delay (~200-500 ms)
- **DSCP 0 traffic:** Very high delay (1000+ ms)

**Priority Differentiation:** 100x-1000x between highest and lowest priority

## Troubleshooting

### No Priority Differentiation

**Cause:** Network not congested enough

**Fix:** Reduce bandwidth or increase message rate in `topology_config.py`:
```python
LINK_BANDWIDTH_MBPS = 0.3  # Lower = more congestion
MSG_RATE = 100             # Higher = more congestion
```

### Publishers Not Starting

**Cause:** Broker IP mismatch

**Check:** Ensure `BROKER_IP=10.0.0.1` in topology_config.py (line 448)

### Queue Configuration Failed

**Cause:** Bandwidth too low (<100 Kbps causes HTB warnings)

**Fix:** Keep LINK_BANDWIDTH_MBPS >= 0.1 (100 Kbps minimum)

## Comparison with Other Scenarios

| Feature                  | Scenario 02    | Scenario 05    | **Scenario 06**   |
|--------------------------|----------------|----------------|-------------------|
| **Switches**             | 13             | 7              | **13**            |
| **Topology**             | 3-tier         | 3-tier         | **3-tier**        |
| **Publishers**           | 18             | 8              | **18**            |
| **QoS Method**           | IP-based       | DSCP-based     | **DSCP-based**    |
| **Priority Levels**      | 2              | 5              | **5**             |
| **MAC Learning**         | No             | No             | **No**            |
| **Scalability**          | Good           | Excellent      | **Excellent**     |
| **Network Depth**        | 3 hops         | 3 hops         | **3 hops**        |

**Scenario 06 = Best of Both Worlds:** Complex topology + Advanced QoS

## References

- **DSCP RFC:** RFC 2474 (Differentiated Services)
- **OpenFlow:** v1.3 specification
- **HTB Queueing:** Linux Hierarchical Token Bucket
- **MQTT:** v3.1.1 protocol

## Notes

- Currently uses only 2 priority levels (DSCP 46 and 0) for anomaly/normal traffic
- All 5 publisher templates are provided for future expansion
- Controller supports all 5 DSCP levels
- To add more priority levels, modify topology_config.py lines 448-449 to use other publishers
