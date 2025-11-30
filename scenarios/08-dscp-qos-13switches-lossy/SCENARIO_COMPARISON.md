# Scenario 06 vs Scenario 08: Comparison

## Quick Reference

| Feature                  | **Scenario 06**              | **Scenario 08 (This Scenario)** |
|--------------------------|-----------------------------|---------------------------------|
| **Name**                 | DSCP QoS - High Congestion  | DSCP QoS - Lossy Network        |
| **Topology**             | 13 switches (3-tier)        | 13 switches (3-tier)            |
| **Publishers**           | 18 (9 anomaly + 9 normal)   | 18 (9 anomaly + 9 normal)       |
| **Bandwidth**            | 0.5 Mbps                    | **1.0 Mbps** ⬆                  |
| **Packet Loss**          | None (0%)                   | **5% core, 2% edge** ⬆          |
| **Utilization**          | 216% (extreme)              | **108% (moderate)** ⬇           |
| **Stress Type**          | Congestion only             | **Congestion + Packet Loss**    |
| **Simulates**            | Wired network overload      | **Wireless IoT (WiFi/LoRa)**    |
| **Expected Delay (DSCP 46)** | 1-5 ms                  | **5-15 ms** ⬆                   |
| **Expected Loss (DSCP 46)**  | 0%                      | **5-7%** ⬆                      |
| **Expected Loss (DSCP 0)**   | High (queue drops)      | **10-15%** ⬆                    |

## When to Use Each Scenario

### Use Scenario 06 When:
- Testing **extreme bandwidth congestion** scenarios
- Evaluating QoS under **high network utilization** (200%+)
- Simulating **wired IoT networks** with limited bandwidth
- Focusing purely on **queuing behavior** and scheduling
- Testing **maximum differentiation** between priority levels

**Example Use Cases:**
- Industrial IoT with bandwidth-limited wired connections
- Legacy infrastructure with low-capacity links
- Stress testing queue management algorithms

### Use Scenario 08 When:
- Testing **realistic wireless IoT deployments**
- Evaluating QoS under **combined stress** (congestion + packet loss)
- Simulating **WiFi, LoRa, Zigbee, or Cellular IoT**
- Testing **application resilience** to packet loss
- Demonstrating QoS benefits in **real-world conditions**

**Example Use Cases:**
- Smart buildings with WiFi sensors
- Agricultural IoT with LoRa connectivity
- Smart city deployments with cellular backhaul
- Outdoor sensor networks with wireless mesh

## Network Configuration Details

### Scenario 06: Extreme Congestion (Wired)

```python
# Configuration
ENABLE_BANDWIDTH_LIMIT = True
ENABLE_PACKET_LOSS = False
LINK_BANDWIDTH_MBPS = 0.5
MSG_RATE = 50  # 50 msg/s per publisher

# Traffic Calculation
Total publishers: 18
Message rate: 50 msg/s × 18 = 900 msg/s
Payload size: ~60 Kbps per publisher
Total load: 18 × 60 Kbps = 1080 Kbps
Link capacity: 500 Kbps
Utilization: 1080 / 500 = 216%
```

**Result:** Extreme queuing delay, high packet drops for low-priority traffic

### Scenario 08: Moderate Congestion + Packet Loss (Wireless)

```python
# Configuration
ENABLE_BANDWIDTH_LIMIT = True
ENABLE_PACKET_LOSS = True
LINK_BANDWIDTH_MBPS = 1.0
CORE_PACKET_LOSS_PCT = 5
EDGE_PACKET_LOSS_PCT = 2
MSG_RATE = 50  # 50 msg/s per publisher

# Traffic Calculation
Total publishers: 18
Message rate: 50 msg/s × 18 = 900 msg/s
Payload size: ~60 Kbps per publisher
Total load: 18 × 60 Kbps = 1080 Kbps
Link capacity: 1000 Kbps
Utilization: 1080 / 1000 = 108%

# Packet Loss Calculation (3-hop path)
Hop 1 (edge → agg): 2% loss
Hop 2 (agg → core): 5% loss
Hop 3 (core → broker): 5% loss
End-to-end delivery: 0.98 × 0.95 × 0.95 = 88.4%
Total loss: ~11.6% (network) + queue drops
```

**Result:** Moderate queuing delay + realistic packet loss patterns

## Expected Metrics

### Scenario 06: Extreme Congestion

| DSCP | Delay (ms) | Jitter (ms) | Packet Loss |
|------|-----------|-------------|-------------|
| 46   | 1-5       | 0.1-1       | 0-1%        |
| 34   | 10-30     | 2-10        | 1-5%        |
| 26   | 50-100    | 10-30       | 5-10%       |
| 10   | 200-500   | 50-200      | 15-30%      |
| 0    | 1000+     | 200-500     | 40-70%      |

**Key Observation:** Massive delay differentiation (1000x between highest and lowest)

### Scenario 08: Lossy Network

| DSCP | Delay (ms) | Jitter (ms) | Packet Loss |
|------|-----------|-------------|-------------|
| 46   | 5-15      | 1-5         | 5-7%        |
| 34   | 20-50     | 5-15        | 5-8%        |
| 26   | 80-150    | 15-40       | 6-10%       |
| 10   | 300-600   | 50-250      | 8-15%       |
| 0    | 1000+     | 200-600     | 10-20%      |

**Key Observation:** Significant delay differentiation + realistic packet loss across all levels

## Experiment Recommendations

### Testing Progression

1. **Start with Scenario 06** to establish baseline QoS behavior
   - Verify DSCP priority works under congestion
   - Measure maximum differentiation possible
   - Validate queue configuration

2. **Move to Scenario 08** to test realistic conditions
   - Evaluate QoS under combined stress
   - Test application resilience to packet loss
   - Demonstrate real-world applicability

### Comparative Analysis

Run both scenarios and compare:

```bash
# Run Scenario 06 (extreme congestion)
cd /home/mqtt-sdn/scenarios/06-dscp-qos-13switches
sudo ./run_experiment.sh 300

# Run Scenario 08 (lossy network)
cd /home/mqtt-sdn/scenarios/08-dscp-qos-13switches-lossy
sudo ./run_experiment.sh 300

# Compare results
python3 /home/mqtt-sdn/analysis/compare_scenarios.py \
    results/06-dscp-qos-13switches/run_TIMESTAMP \
    results/08-dscp-qos-13switches-lossy/run_TIMESTAMP
```

**Expected Findings:**
- Scenario 06: Higher delay separation, lower total packet loss
- Scenario 08: More realistic delay values, higher total packet loss
- Both: DSCP priority provides significant benefits

## Research Paper Positioning

### For Methodology Section

**Scenario 06:**
> "To evaluate the maximum effectiveness of DSCP priority under extreme congestion, we configured a test scenario with 0.5 Mbps links resulting in 216% network utilization. This stress test demonstrates the upper bound of QoS differentiation achievable through DSCP-based prioritization."

**Scenario 08:**
> "To validate the framework under realistic wireless IoT conditions, we implemented a lossy network scenario with 1.0 Mbps links and packet loss rates of 5% at core links and 2% at edge links, representing typical WiFi and LoRa deployment characteristics. This scenario demonstrates QoS effectiveness in production environments."

### For Results Section

Present both scenarios:
- **Scenario 06:** Maximum differentiation capability
- **Scenario 08:** Real-world applicability

## File Locations

```
/home/mqtt-sdn/scenarios/
├── 06-dscp-qos-13switches/          # Extreme congestion scenario
│   ├── topology_config.py           # BW=0.5, Loss=0%
│   └── run_experiment.sh
└── 08-dscp-qos-13switches-lossy/    # Lossy network scenario
    ├── topology_config.py           # BW=1.0, Loss=5%/2%
    └── run_experiment.sh

/home/mqtt-sdn/results/
├── 06-dscp-qos-13switches/
└── 08-dscp-qos-13switches-lossy/
```

## Quick Switching Between Scenarios

### Disable Packet Loss in Scenario 08 (simulate Scenario 06)

Edit `topology_config.py`:
```python
ENABLE_PACKET_LOSS = False  # Disable
LINK_BANDWIDTH_MBPS = 0.5   # Match Scenario 06
```

### Enable Higher Packet Loss (simulate worse conditions)

```python
CORE_PACKET_LOSS_PCT = 10   # 10% core loss
EDGE_PACKET_LOSS_PCT = 5    # 5% edge loss
```

## References

- **Scenario 06:** `/home/mqtt-sdn/scenarios/06-dscp-qos-13switches/README.md`
- **Scenario 08:** `/home/mqtt-sdn/scenarios/08-dscp-qos-13switches-lossy/README.md`
- **Wireless IoT Packet Loss Studies:**
  - LoRaWAN: 2-8% typical packet loss outdoors
  - WiFi: 1-10% packet loss depending on interference
  - Cellular IoT: 5-15% packet loss in urban areas
