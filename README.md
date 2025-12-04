# DSCP-Based QoS Framework for MQTT Traffic Prioritization in SDN

> **Final Project - Network-Based Computing Course**  
> Department of Informatics, Institut Teknologi Sepuluh Nopember

## Authors

- Reinaldi Prasetya (6025251043)
- Abdurrizqo Arrahman (6025251013)
- Ahmad Bilal (6025251040)

---

## Overview

This project implements a QoS framework that prioritizes MQTT traffic using DSCP (Differentiated Services Code Point) marking in Software-Defined Networks. The framework protects critical/anomaly data during network congestion by assigning higher priority queues.

**Key Insight**: Priority mechanism is only effective during **congestion**. Without congestion, all traffic performs similarly.

## How It Works

```
Publisher                    SDN Switch                     Broker
    │                            │                            │
    ├─ Anomaly data             │                            │
    │  (DSCP 46) ──────────────► Queue 1 (60-80% BW) ───────► Received
    │                            │                            │
    └─ Normal data              │                            │
       (DSCP 0)  ──────────────► Queue 5 (5-15% BW)  ───────► Delayed/Dropped
```

## Experiment Scenarios

| # | Scenario | Switches | Description |
|---|----------|----------|-------------|
| 01 | Baseline | 13 | Normal hierarchical topology |
| 02 | Lossy | 13 | Added packet loss (10% core, 5% edge) |
| 05 | Dual-Redundant | 17 | Full redundancy at all layers |
| 06 | Dist-Failure | 17 | Distribution layer failure at 4 min |

## Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Bandwidth | 0.2 Mbps | Per link (creates ~1.8x congestion) |
| Message Rate | 10 msg/s | Per publisher |
| Send Phase | 10 min | Publishers sending data |
| Drain Phase | 10 min | Waiting for queued messages |
| Repetitions | 3x | Per scenario |

## Evaluation Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| **Avg Delay** | `Σ(t_received - t_sent) / n` | Average end-to-end latency |
| **Min/Max Delay** | `min(delays)` / `max(delays)` | Best/worst case latency |
| **Std Dev Delay** | `√(Σ(delay - avg)² / n)` | Delay consistency |
| **Jitter** | `Σ|delay[i] - delay[i-1]| / (n-1)` | Delay variation between consecutive messages |
| **Packet Loss** | `(sent - received) / sent × 100%` | Percentage of lost messages |

## Quick Start

### Run Single Scenario
```bash
cd /home/mqtt-sdn/scenarios/01-baseline-13switches
sudo ./run_experiment.sh 600  # 10 min send + 10 min drain
```

### Run All Scenarios (Background)
```bash
cd /home/mqtt-sdn
nohup sudo ./run_all_experiments.sh > experiment_master.log 2>&1 &

# Monitor progress
tail -f experiment_master.log
```

### View Results
```bash
python3 generate_summary.py results/01-*/run_*/mqtt_metrics_log.csv
cat results/01-baseline-13switches/run_*/metrics_summary.txt
```

### Cleanup
```bash
sudo mn -c && sudo pkill -f ryu-manager && sudo pkill -f mosquitto
```

## Expected Results

| Traffic | Avg Delay | Packet Loss |
|---------|-----------|-------------|
| Anomaly (DSCP 46) | ~200 ms | 0% |
| Normal (DSCP 0) | ~237,000 ms | ~78% |

> The 1000x difference in delay proves priority mechanism works under congestion.

## Project Structure

```
mqtt-sdn/
├── scenarios/           # Experiment scenarios
│   ├── 01-baseline-13switches/
│   ├── 02-lossy-13switches/
│   ├── 05-dualredundant-17switches/
│   └── 06-distfailure-17switches/
├── shared/              # Shared modules
│   ├── sdn/controller.py
│   ├── mqtt/publisher_dscp.py
│   └── topology/base.py
├── results/             # Experiment outputs
├── docs/                # Documentation & LaTeX paper
├── run_all_experiments.sh
├── generate_summary.py
├── CONTEXT.md           # Full project context
└── README.md
```

## Requirements

- Ubuntu 20.04+ LTS
- Python 3.9+ (Ryu virtualenv)
- Mininet 2.3.0
- Open vSwitch 2.13+
- Mosquitto 2.0
- paho-mqtt 1.6

## Documentation

- [CONTEXT.md](CONTEXT.md) - Detailed project context for AI assistants
- [docs/PAPER_CONTEXT.md](docs/PAPER_CONTEXT.md) - LaTeX paper context

---

**Last Updated**: 2025-12-05
