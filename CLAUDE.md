# CLAUDE.md - Technical Guide

## Project Overview

SDN-MQTT simulation with DSCP-based QoS priority. Publishers tag DSCP in IP header, SDN controller maps DSCP to queues, switches apply priority scheduling.

## Key Commands

```bash
# Run experiment (recommended scenarios: 09, 10)
cd /home/mqtt-sdn/scenarios/09-dscp-qos-13switches-ring
sudo ./run_experiment.sh 60  # Total: 120s (60s send + 60s drain)

# Generate summary
python3 generate_summary_manual_v2.py results/09-*/run_*/mqtt_metrics_log.csv
python3 generate_summary_linkfailure.py results/10-*/run_*/mqtt_metrics_log.csv

# Cleanup
sudo ./stop_sdn_mqtt.sh
sudo mn -c
```

## Code Structure

```
scenarios/
├── 06-dscp-qos-13switches/           # High congestion (0.5 Mbps)
├── 07-dscp-qos-13switches-core-bottleneck/
├── 08-dscp-qos-13switches-lossy/     # Packet loss simulation
├── 09-dscp-qos-13switches-ring/      # Ring topology + STP
└── 10-dscp-qos-13switches-linkfailure/  # Link failure test

shared/mqtt/
├── publisher_dscp.py                 # Generic DSCP publisher
└── subscriber_enhanced.py            # Metrics collection

generate_summary_manual_v2.py         # Normal scenario summary
generate_summary_linkfailure.py       # Link failure summary
```

## Important Technical Details

### Drain Time
- Duration parameter = publisher send time
- After publishers stop, wait same duration for in-flight messages
- Total experiment time = 2 × duration
- Prevents counting delayed messages as packet loss

### Packet Loss Calculation
```python
# Correct (per-phase range)
expected = max_seq - min_seq + 1
received = len(unique_sequences)
lost = expected - received

# Wrong (was using this before)
expected = max_seq + 1  # Includes sequences from previous phases
```

### STP (Spanning Tree Protocol)
- Required for ring topology to prevent broadcast storms
- Convergence time: 35 seconds
- Enabled on all switches in scenarios 09 and 10

### Log Organization
```
results/scenario/run_YYYY-MM-DD_HH-MM-SS/
├── mqtt_metrics_log.csv      # Raw message data
├── metrics_summary.txt       # Auto-generated summary
└── logs/
    ├── experiment.log        # Topology build, STP, MQTT
    ├── ryu_controller.log    # SDN controller
    ├── subscriber.log        # Subscriber output
    └── publisher_*.log       # Per-publisher logs
```

## Debugging

```bash
# Check controller
curl http://127.0.0.1:8080/stats/switches

# Check flow rules
sudo ovs-ofctl -O OpenFlow13 dump-flows s1

# Check queues
sudo ovs-vsctl list QoS

# View logs
tail -f results/*/run_*/logs/experiment.log
```

## Common Issues

1. **"No route to host"**: STP not converged, wait 35+ seconds
2. **Empty results**: Controller not running or flow rules not installed
3. **High packet loss**: Missing drain time, experiment stopped too early
4. **Broadcast storm**: STP not enabled on ring topology

## Environment

- Python venv: `/home/aldi/ryu39`
- Controller: Ryu (OpenFlow 1.3)
- Network: Mininet + Open vSwitch
- MQTT: Mosquitto broker + paho-mqtt

**Last Updated**: 2025-12-01
