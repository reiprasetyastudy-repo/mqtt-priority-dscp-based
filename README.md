# MQTT-SDN Priority Simulation

DSCP-based QoS framework for prioritizing MQTT traffic in Software-Defined Networks.

## Quick Start

```bash
# Run experiment (60s send + 60s drain = 2 minutes total)
cd /home/mqtt-sdn/scenarios/09-dscp-qos-13switches-ring
sudo ./run_experiment.sh 60

# View results
cat results/09-dscp-qos-13switches-ring/run_*/metrics_summary.txt
```

## Scenarios

| Scenario | Description | Use Case |
|----------|-------------|----------|
| 06 | High congestion (0.5 Mbps) | Baseline QoS test |
| 07 | Core bottleneck | Bottleneck at core switch |
| 08 | Lossy network (5% loss) | Wireless IoT simulation |
| **09** | **Ring topology** | Redundancy test |
| **10** | **Link failure** | Failover test |

## Architecture

```
Publishers (DSCP tagging) → SDN Switches (Queue mapping) → Broker
         ↓                           ↓
    DSCP 46 (anomaly)          Queue 1 (60-80% BW)
    DSCP 0  (normal)           Queue 5 (5-15% BW)
```

## Topology (Scenarios 09-10)

```
                    ┌──────┐
                    │  s1  │ CORE (Broker)
                    └───┬──┘
          ┌─────────────┼─────────────┐
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │←───→│  s3   │←───→│  s4   │  RING
      └───┬───┘←─────────────────→└───┬───┘
          │             │             │
       s5-s7         s8-s10       s11-s13    EDGE
```

## Results

```
ANOMALY (DSCP 46):
  Avg Delay: ~4,000 ms
  Packet Loss: 0%

NORMAL (DSCP 0):
  Avg Delay: ~50,000 ms
  Packet Loss: 0%

QoS Improvement: ~90% lower delay for anomaly traffic
```

## Generate Summary

```bash
# For scenarios 06-09
python3 generate_summary_manual_v2.py results/09-*/run_*/mqtt_metrics_log.csv

# For scenario 10 (link failure)
python3 generate_summary_linkfailure.py results/10-*/run_*/mqtt_metrics_log.csv
```

## Requirements

- Ubuntu Linux
- Python 3.9+ with Ryu (`/home/aldi/ryu39`)
- Mininet, Open vSwitch, Mosquitto

## Files

```
scenarios/           # Experiment scenarios
results/             # Experiment results
shared/mqtt/         # Publisher & subscriber scripts
generate_summary_*.py   # Analysis scripts
```

---
**Last Updated**: 2025-12-01
