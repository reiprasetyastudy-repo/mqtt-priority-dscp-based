# MQTT-SDN Priority Simulation

DSCP-based QoS framework untuk memprioritaskan traffic MQTT pada jaringan Software-Defined Networking (SDN).

## Fitur Utama

- **DSCP-based Priority**: Standar industri (RFC 2474) untuk prioritas paket
- **2 Level Prioritas**: DSCP 46 (Anomaly/Critical) dan DSCP 0 (Normal/Best Effort)
- **6 Skenario**: Baseline, Lossy, Dual-Core, Core Failure, Dual-Redundant, Dist Failure
- **Modular Architecture**: Shared modules untuk DRY principle
- **Accurate Metrics**: Delay, Jitter, Packet Loss dengan publisher log verification

## Quick Start

```bash
# 1. Run experiment (1 minute test)
cd /home/mqtt-sdn/scenarios/01-baseline-13switches
sudo ./run_experiment.sh 60

# 2. View results
cat results/01-baseline-13switches/run_*/metrics_summary.txt
```

## Skenario

| # | Nama | Deskripsi | Switches |
|---|------|-----------|----------|
| 01 | Baseline | Normal hierarchical topology | 13 |
| 02 | Lossy | Packet loss (10% core, 5% edge) | 13 |
| 03 | Dual-Core | 2 core switches with STP | 14 |
| 04 | Core Failure | Core 1 fails at 150s | 14 |
| 05 | Dual-Redundant | Full redundancy all layers | 17 |
| 06 | Dist Failure | Distribution layer failure | 17 |

## Parameter Standard

```python
LINK_BANDWIDTH_MBPS = 0.2    # 200 Kbps
MSG_RATE = 10                # 10 msg/s per publisher
DURATION = 300               # 5 minutes send
DRAIN_RATIO = 1.0            # 5 minutes drain
```

## Expected Results

```
ANOMALY (DSCP 46):
  Packet Loss: 0%
  Avg Delay:   ~200ms

NORMAL (DSCP 0):
  Packet Loss: ~76%
  Avg Delay:   ~27,000ms
```

## Project Structure

```
mqtt-sdn/
├── scenarios/
│   ├── 01-baseline-13switches/
│   ├── 02-lossy-13switches/
│   ├── 03-dualcore-14switches/
│   ├── 04-corefailure-14switches/
│   ├── 05-dualredundant-17switches/
│   └── 06-distfailure-17switches/
├── shared/
│   ├── config/      # defaults.py, naming.py
│   ├── mqtt/        # publisher_dscp.py, subscriber_enhanced.py
│   ├── sdn/         # controller.py
│   ├── topology/    # base.py, qos.py
│   └── analysis/    # metrics.py, packet_loss.py, export.py
├── results/         # Experiment results
├── generate_summary.py
├── CONTEXT.md       # Project context
└── README.md
```

## Running Experiments

### Single Scenario
```bash
cd /home/mqtt-sdn/scenarios/01-baseline-13switches
sudo ./run_experiment.sh 300  # 5 min send + 5 min drain
```

### Generate Summary
```bash
python3 generate_summary.py results/01-*/run_*/mqtt_metrics_log.csv
```

### Cleanup
```bash
sudo mn -c
sudo pkill -f ryu-manager
sudo pkill -f mosquitto
```

## Architecture

```
Publishers ──────────────────► SDN Switches ──────────────────► Broker
(DSCP tagging)                 (Queue mapping)                  (Subscriber)
    │                              │
    ├── DSCP 46 (anomaly) ────────► Queue 1 (60-80% BW)
    └── DSCP 0  (normal)  ────────► Queue 5 (5-15% BW)
```

## Requirements

- Ubuntu 20.04/22.04 LTS
- Python 3.9+ (Ryu), Python 3.12 (System)
- Mininet, Open vSwitch, Mosquitto
- Ryu Controller (in virtualenv)

## Documentation

- [CONTEXT.md](CONTEXT.md) - Full project context
- [docs/](docs/) - Additional documentation

---

**Last Updated**: 2025-12-03
