# Scenario 07: 5-Level DSCP Priority Test

## Overview

This scenario tests all **5 DSCP priority levels** simultaneously on a hierarchical 13-switch topology to demonstrate the complete QoS differentiation capability of the DSCP-based framework.

## Topology

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
     s5  s6  s7    s8  s9 s10   s11 s12 s13  EDGE
```

- **Switches**: 13 (1 core, 3 aggregation, 9 edge)
- **Hosts**: 16 (1 broker + 15 publishers)
- **Publishers**: 15 (5 DSCP levels × 3 floors)

## DSCP Priority Levels

| DSCP | RFC Name | Priority | Queue | Bandwidth | Use Case |
|------|----------|----------|-------|-----------|----------|
| **46** | EF (Expedited Forwarding) | Very High | 1 | 60-80% | Critical alerts, anomaly detection |
| **34** | AF41 (Assured Forwarding 4.1) | High | 2 | 45-60% | Important sensor data |
| **26** | AF31 (Assured Forwarding 3.1) | Medium | 3 | 30-45% | Regular monitoring |
| **10** | AF11 (Assured Forwarding 1.1) | Low | 4 | 15-30% | Background data collection |
| **0** | BE (Best Effort) | Default | 5 | 5-15% | Non-critical traffic |

## Publishers Distribution

Each floor has **5 publishers** (one for each DSCP level):

### Floor 1 (Edge: s5)
- `h_f1_veryhigh` → DSCP 46 (Very High Priority)
- `h_f1_high` → DSCP 34 (High Priority)
- `h_f1_medium` → DSCP 26 (Medium Priority)
- `h_f1_low` → DSCP 10 (Low Priority)
- `h_f1_besteffort` → DSCP 0 (Best Effort)

### Floor 2 (Edge: s8)
- `h_f2_veryhigh` → DSCP 46
- `h_f2_high` → DSCP 34
- `h_f2_medium` → DSCP 26
- `h_f2_low` → DSCP 10
- `h_f2_besteffort` → DSCP 0

### Floor 3 (Edge: s11)
- `h_f3_veryhigh` → DSCP 46
- `h_f3_high` → DSCP 34
- `h_f3_medium` → DSCP 26
- `h_f3_low` → DSCP 10
- `h_f3_besteffort` → DSCP 0

## Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Bandwidth | 0.2 Mbps | Per link (creates ~1.8x congestion) |
| Message Rate | 10 msg/s | Per publisher |
| Publishers | 15 | 5 levels × 3 floors |
| Total Traffic | ~150 msg/s | 15 publishers × 10 msg/s |
| Send Duration | 600s | 10 minutes |
| Drain Duration | 600s | 10 minutes (1:1 ratio) |
| Total Time | ~23 min | Send + Cleanup + Drain |

## Expected Results

Based on congestion ratio of 1.8x and HTB queue allocation:

| DSCP | Priority | Avg Delay | Packet Loss | Jitter |
|------|----------|-----------|-------------|--------|
| 46 | Very High | ~200 ms | 0% | ~60 ms |
| 34 | High | ~50 s | ~20% | ~100 ms |
| 26 | Medium | ~100 s | ~40% | ~150 ms |
| 10 | Low | ~200 s | ~60% | ~200 ms |
| 0 | Best Effort | ~250 s | ~80% | ~250 ms |

**Key Observations:**
- **DSCP 46** gets maximum protection (0% loss, <300ms delay)
- **DSCP 34-10** show gradual degradation based on priority
- **DSCP 0** experiences highest loss and delay (best effort)

## Quick Start

### Run Experiment (10 minutes)
```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches
sudo ./run_experiment.sh 600
```

### Quick Test (1 minute)
```bash
sudo ./run_experiment.sh 60
```

### View Results
```bash
# Summary report
cat results/07-5level-dscp-13switches/run_*/metrics_summary.txt

# CSV format (for Excel)
cat results/07-5level-dscp-13switches/run_*/metrics_summary.csv

# Raw data
cat results/07-5level-dscp-13switches/run_*/mqtt_metrics_log.csv
```

## Running from Python

```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches

# Default (10 minutes)
sudo python3 topology.py

# Custom duration
sudo python3 topology.py --duration 120

# Custom drain ratio
sudo python3 topology.py --duration 600 --drain-ratio 1.5
```

## Files

```
07-5level-dscp-13switches/
├── topology.py                      # Topology definition
├── publisher_dscp46_veryhigh.py     # DSCP 46 publisher
├── publisher_dscp34_high.py         # DSCP 34 publisher
├── publisher_dscp26_medium.py       # DSCP 26 publisher
├── publisher_dscp10_low.py          # DSCP 10 publisher
├── publisher_dscp0_besteffort.py    # DSCP 0 publisher
├── run_experiment.sh                # Runner script
└── README.md                        # This file
```

## Metrics Analysis

### Delay
- Measures end-to-end latency from publisher to subscriber
- Lower DSCP values → higher delay due to lower queue priority
- Formula: `delay = t_received - t_sent`

### Jitter
- Measures delay variation between consecutive messages
- Indicates stability and predictability of delivery
- Formula: `jitter = |delay[i] - delay[i-1]|`

### Packet Loss
- Percentage of messages that don't reach subscriber
- Higher priority queues have lower loss rates
- Formula: `loss_rate = (sent - received) / sent × 100%`

### Throughput
- Messages successfully delivered per second
- Formula: `throughput = total_messages / duration`

## Comparison with Scenario 01

| Aspect | Scenario 01 | Scenario 07 |
|--------|-------------|-------------|
| DSCP Levels | 2 (46, 0) | **5 (46, 34, 26, 10, 0)** |
| Publishers | 18 | 15 |
| Focus | Binary priority | **Multi-level QoS** |
| Use Case | Anomaly vs Normal | **Complete priority spectrum** |

**Scenario 07 advantages:**
- Demonstrates full QoS differentiation capability
- Shows gradual performance degradation across priority levels
- More realistic for production IoT systems with multiple traffic classes

## Use Cases

1. **Industrial IoT**
   - DSCP 46: Emergency shutdowns, safety alerts
   - DSCP 34: Critical process monitoring
   - DSCP 26: Regular telemetry
   - DSCP 10: Historical data logging
   - DSCP 0: Debugging/diagnostics

2. **Smart Building**
   - DSCP 46: Fire alarms, gas leaks
   - DSCP 34: HVAC critical sensors
   - DSCP 26: Energy monitoring
   - DSCP 10: Occupancy sensors
   - DSCP 0: Maintenance logs

3. **Healthcare**
   - DSCP 46: Patient vital signs (critical)
   - DSCP 34: Medical equipment alerts
   - DSCP 26: Room environment monitoring
   - DSCP 10: Asset tracking
   - DSCP 0: System diagnostics

## Troubleshooting

### No Results Generated
```bash
# Check if experiment ran
ls -la results/07-5level-dscp-13switches/

# Check logs
cat results/07-5level-dscp-13switches/run_*/logs/experiment.log
```

### High Packet Loss for DSCP 46
```bash
# Verify controller is running
curl http://127.0.0.1:8080/stats/switches

# Check flow rules
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

### Publishers Not Starting
```bash
# Check publisher logs
cat results/07-5level-dscp-13switches/run_*/logs/publisher_*.log

# Verify broker is running
ps aux | grep mosquitto
```

## References

- RFC 2474: Definition of the Differentiated Services Field (DSCP)
- RFC 3246: An Expedited Forwarding PHB (DSCP 46)
- RFC 2597: Assured Forwarding PHB Group (DSCP 10, 26, 34)

## Next Steps

1. **Compare with Scenario 01**: Run both and compare binary vs multi-level QoS
2. **Adjust Congestion**: Try different bandwidth values (0.1, 0.3, 0.5 Mbps)
3. **Add Failures**: Introduce link failures to test resilience
4. **Scale Up**: Increase number of publishers per level

---

**Last Updated**: 2025-12-07

---

## Running 3x Repetitions (for Statistical Consistency)

For reproducible research results, run the experiment 3 times automatically:

### Run 3x Repetitions (10 minutes each)
```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches
sudo ./run_3x_experiments.sh 600
```

This will:
1. Run the experiment 3 times sequentially
2. Wait 3 minutes between runs (cleanup + cool-down)
3. Save all results to a timestamped batch directory
4. Generate logs for each run

### Time Breakdown (10-minute experiment)
```
Per Run:
  - Send Phase: 10 min (600s)
  - Cleanup: 10s
  - Drain Phase: 10 min (600s)
  Total: ~20 min per run

3 Runs Total:
  - Run 1: 20 min
  - Delay: 3 min
  - Run 2: 20 min
  - Delay: 3 min
  - Run 3: 20 min
  ─────────────────
  Total: ~66 minutes (~1 hour 6 min)
```

### Quick 3x Test (1 minute each)
```bash
sudo ./run_3x_experiments.sh 60
# Total time: ~10 minutes
```

### View Batch Results
```bash
# Find latest batch
ls -lt results/07-5level-dscp-13switches/batch_3x_*

# View all summaries
cat results/07-5level-dscp-13switches/batch_3x_*/run_*/metrics_summary.txt

# View batch log
cat results/07-5level-dscp-13switches/batch_3x_*/batch_experiment.log
```

### Results Directory Structure
```
results/07-5level-dscp-13switches/
└── batch_3x_2025-12-07_21-30-00/
    ├── batch_experiment.log          # Master log
    ├── run_1/
    │   ├── mqtt_metrics_log.csv
    │   ├── metrics_summary.txt
    │   ├── metrics_summary.csv
    │   └── logs/
    ├── run_2/
    │   └── ...
    └── run_3/
        └── ...
```

