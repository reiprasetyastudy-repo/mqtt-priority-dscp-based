# CONTEXT.md - Project Context for AI Assistant

> **File ini berisi konteks proyek riset MQTT-SDN agar AI assistant dapat memahami dan melanjutkan pekerjaan.**

---

## 1. OVERVIEW RISET

### Judul
**"DSCP-Based QoS Framework untuk Prioritas Traffic MQTT pada Jaringan Software-Defined Networking"**

### Tujuan
Framework QoS yang memprioritaskan data MQTT **anomaly/kritis** (alarm kebakaran, gas leak) agar lebih cepat sampai dibanding data **normal/rutin**, menggunakan DSCP pada SDN.

### Solusi
1. **Publisher** menandai DSCP value di IP header (`IP_TOS`)
2. **SDN Controller (Ryu)** install flow rules: DSCP → Queue
3. **Switch OVS** dengan HTB scheduler memberikan bandwidth berbeda per queue
4. **Tidak modifikasi protokol MQTT** - transparan di layer IP

---

## 2. ARSITEKTUR

```
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                          │
│  Publisher (DSCP 46 Anomaly / DSCP 0 Normal) → Subscriber       │
└─────────────────────────────────────────────────────────────────┘
          │ IP_TOS socket option
┌─────────▼───────────────────────────────────────────────────────┐
│                      CONTROL LAYER (Ryu)                        │
│  Flow rules: match DSCP → set Queue                             │
└─────────────────────────────────────────────────────────────────┘
          │ OpenFlow 1.3
┌─────────▼───────────────────────────────────────────────────────┐
│                      DATA LAYER (OVS)                           │
│  Queue 1 (60-80%): DSCP 46 - Very High Priority                 │
│  Queue 5 (5-15%) : DSCP 0  - Best Effort                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. SKENARIO EKSPERIMEN

| # | Nama | Deskripsi | Topologi |
|---|------|-----------|----------|
| 01 | Baseline | Normal operation | 13 switches hierarchical |
| 02 | Lossy | Packet loss (10% core, 5% edge) | 13 switches |
| 03 | Dual-Core | 2 core switches for redundancy | 14 switches |
| 04 | Core Failure | Core 1 fails at 150s | 14 switches |
| 05 | Dual-Redundant | Full redundancy at all layers | 17 switches |
| 06 | Dist Failure | Distribution layer failure | 17 switches |

### Parameter Standard (Semua Skenario)
```python
LINK_BANDWIDTH_MBPS = 0.2    # 200 Kbps (creates ~1.8x congestion)
MSG_RATE = 10                # 10 msg/s per publisher (realistic IoT)
DURATION = 600               # 10 minutes send phase
DRAIN_RATIO = 1.0            # Drain time = Duration × 1.0

# Untuk skenario failure (06):
FAILURE_TIME = 240           # Failure di menit ke-4 (40% durasi)
```

### Hasil yang Diharapkan
```
ANOMALY (DSCP 46, High Priority):
  - Packet Loss: 0%
  - Avg Delay: ~200ms

NORMAL (DSCP 0, Best Effort):
  - Packet Loss: ~76%
  - Avg Delay: ~27,000ms (27 detik)
```

### Topologi

#### Skenario 01-02: 13 Switch Hierarchical
```
                    ┌──────┐
                    │  s1  │ CORE (Broker here)
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

#### Skenario 03-04: 14 Switch Dual-Core
```
                    MQTT Broker
                         │
                  ┌──────┴──────┐
              ┌───┴───┐     ┌───┴───┐
              │  s1   │     │  s2   │  CORE (2 switches)
              └───┬───┘     └───┬───┘
                  │╲           ╱│
                  │ ╲─────────╱ │
          ┌───────┼─────╳──────┼───────┐
          s3     s4           s5    DISTRIBUTION
        Floor 1  Floor 2    Floor 3
```

#### Skenario 05-06: 17 Switch Dual-Redundant
```
                        MQTT Broker
                             │
                      ┌──────┴──────┐
                   Core 1        Core 2
                   (s1)          (s2)
                      │╲    ╳    ╱│
                ┌─────┼──╳───╳──┼─────┐
              ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐
              │s3 │ │s4 │ │s5 │ │s6 │ │s7 │ │s8 │  DISTRIBUTION (2/floor)
              └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘
                ╲  ╳  ╱     ╲  ╳  ╱     ╲  ╳  ╱
               s9 s10 s11  s12 s13 s14  s15 s16 s17  EDGE (3/floor)
```

---

## 4. STRUKTUR PROYEK

```
/home/mqtt-sdn/
├── scenarios/
│   ├── 01-baseline-13switches/
│   │   ├── topology.py              # Main topology + experiment
│   │   ├── run_experiment.sh        # Runner script
│   │   ├── publisher_dscp0_besteffort.py
│   │   └── publisher_dscp46_veryhigh.py
│   ├── 02-lossy-13switches/
│   ├── 03-dualcore-14switches/
│   ├── 04-corefailure-14switches/
│   ├── 05-dualredundant-17switches/
│   └── 06-distfailure-17switches/
│
├── shared/
│   ├── config/
│   │   ├── defaults.py              # Default parameters
│   │   └── naming.py                # Sensor naming functions
│   ├── mqtt/
│   │   ├── dscp_config.py           # DSCP values
│   │   ├── publisher_dscp.py        # Generic publisher (flush=True)
│   │   └── subscriber_enhanced.py   # Enhanced subscriber
│   ├── sdn/
│   │   └── controller.py            # DSCP-based QoS controller
│   ├── topology/
│   │   ├── base.py                  # Base topology class
│   │   └── qos.py                   # QoS queue config
│   └── analysis/
│       ├── metrics.py               # Metrics calculation
│       ├── packet_loss.py           # Packet loss from publisher logs
│       └── export.py                # Export to TXT/CSV
│
├── results/                         # Experiment results
│   └── {scenario}/run_{timestamp}/
│       ├── mqtt_metrics_log.csv     # Raw data from subscriber
│       ├── metrics_summary.txt      # Summary report
│       ├── metrics_summary.csv      # Excel-compatible
│       └── logs/                    # Publisher logs
│
├── backup-old-results/              # Old results backup
├── analytics/                       # Jupyter notebooks
├── docs/                            # Documentation
│
├── generate_summary.py              # Main summary generator
├── CONTEXT.md                       # This file
└── README.md                        # Quick start
```

---

## 5. CARA MENJALANKAN

### Quick Test (1 menit)
```bash
cd /home/mqtt-sdn/scenarios/01-baseline-13switches
sudo ./run_experiment.sh 60
```

### Single Scenario (10 menit send + 10 menit drain)
```bash
cd /home/mqtt-sdn/scenarios/01-baseline-13switches
sudo ./run_experiment.sh 600
```

### Run All Scenarios Automatically (Background)
```bash
cd /home/mqtt-sdn
nohup sudo ./run_all_experiments.sh > experiment_master.log 2>&1 &

# Monitor progress
tail -f experiment_master.log
```

Automated run configuration:
- Scenarios: 01, 02, 03, 04, 05, 06 (all 6 scenarios)
- Runs per scenario: 3x
- Duration per run: ~23 minutes (10 send + 10 cleanup buffer + 10 drain)
- Delay between runs: 3 minutes
- **Total estimated time: ~7 hours**

### Generate Summary
```bash
python3 /home/mqtt-sdn/generate_summary.py results/01-*/run_*/mqtt_metrics_log.csv
```

### Verify All Results
```bash
python3 /home/mqtt-sdn/verify_results.py        # Check all results
python3 /home/mqtt-sdn/verify_results.py --fix  # Fix incorrect summaries
```

### Cleanup
```bash
sudo mn -c && sudo pkill -f ryu-manager && sudo pkill -f mosquitto
```

---

## 6. TIMING & GRACEFUL SHUTDOWN

### Graceful Shutdown (NEW - 2025-12-07)

Publishers now use internal timer instead of being killed by `pkill`. This ensures:
- TCP buffers are flushed before disconnect
- All retransmissions complete
- Accurate packet loss measurement (not inflated by connection reset)

```
OLD (pkill - problematic):
├── base.py sleeps for DURATION
├── pkill -f publisher  ← TCP connections reset!
└── Messages in buffer LOST

NEW (graceful - correct):
├── Publisher has DURATION env variable
├── Internal timer stops sending at exactly DURATION
├── TCP buffer flush (2s wait)
├── Graceful disconnect
└── All messages delivered properly
```

### Publisher Log Output
```
[START] Send phase started at 2025-12-07 10:00:01.234
[START] Expected end time: 10:10:01 (duration: 600s)
...
[TIMER] Duration 600s reached
[STOP] Send phase stopped at 2025-12-07 10:10:01.237
[STOP] Actual send duration: 600.003s

[CLEANUP] Flushing buffers and disconnecting...
[EXIT] Disconnected at 2025-12-07 10:10:04.240
[EXIT] Total messages sent: 6000
[EXIT] Send rate achieved: 10.00 msg/s
```

### Experiment Timing

```
EXPERIMENT TIMING (Graceful Shutdown Mode):
├── Send Phase     : DURATION seconds (publishers active)
├── Cleanup Buffer : 10 seconds (TCP flush)
├── Drain Phase    : DURATION × DRAIN_RATIO seconds
└── Total Time     : DURATION + 10 + (DURATION × DRAIN_RATIO)

Example with DURATION=600, DRAIN_RATIO=1.0:
├── Send Phase     : 600 seconds (0:00 - 10:00)
├── Cleanup Buffer : 10 seconds (10:00 - 10:10)
├── Drain Phase    : 600 seconds (10:10 - 20:10)
└── Total Time     : 1210 seconds (~20 minutes)
```

### Drain Phase Verification
```
*** [PHASE 2] Drain phase ended
    Messages during drain: 102    ← Harus > 0 jika drain berfungsi

  ✓ DRAIN OK: 102 messages received after publishers stopped
```

---

## 7. METRICS CALCULATION

### Packet Loss
```python
# Sent count: MAX of publisher log and CSV seq range
# (handles truncated logs due to process kill)
seq_range = max_seq - min_seq + 1
sent = max(log_count, seq_range)
received = len(unique_sequences)
loss = sent - received
loss_rate = (lost / sent) * 100
```

### Jitter
```python
# Calculated per-device, then aggregated
# (not across devices - that would be meaningless)
jitter = mean(abs(delay[i] - delay[i-1]) for consecutive messages)
```

### CRITICAL: File Sources

| File | Source | Use for Results? |
|------|--------|------------------|
| `metrics_summary.txt` | `generate_summary.py` | **YES - AUTHORITATIVE** |
| `metrics_summary.csv` | `generate_summary.py` | **YES - AUTHORITATIVE** |
| `subscriber_summary.txt` | `subscriber_enhanced.py` | NO - internal only |
| `subscriber.log` | subscriber console | NO - wrong packet loss |
| `mqtt_metrics_log.csv` | subscriber | YES - raw data |
| `logs/*.log` | publisher logs | YES - sent count |

**WARNING**: subscriber.log shows 0% packet loss for all traffic because it calculates
"Expected" from the received sequence range, not from actual sent count.
Always use `metrics_summary.txt` generated by `generate_summary.py` for correct results.

---

## 8. ENVIRONMENT

- OS: Ubuntu Linux
- Python: 3.12.3
- Virtual env Ryu: `/home/aldi/ryu39` (Python 3.9)
- Dependencies: Mininet, Open vSwitch, Mosquitto, paho-mqtt

---

## 9. CHANGELOG

### 2025-12-07: Graceful Shutdown & All Scenarios

**A. Graceful Shutdown Implementation**
- Publisher now uses internal timer (DURATION env variable)
- Timer starts AFTER connection (accurate send duration)
- TCP buffer flush before disconnect (2s wait)
- No more `pkill` - publishers exit gracefully
- Logs: [START], [TIMER], [STOP], [CLEANUP], [EXIT] with timestamps

**B. All 6 Scenarios Enabled**
- `run_all_experiments.sh` now runs all 6 scenarios (01-06)
- Added scenarios 03-dualcore-14switches and 04-corefailure-14switches
- Total estimated time: ~7 hours (18 runs)

**C. Files Modified**
- `shared/mqtt/publisher_dscp.py`: Added duration, graceful shutdown, logging
- `shared/topology/base.py`: Pass duration, wait_publishers_done(), updated timing
- `run_all_experiments.sh`: Added scenarios 03 and 04

### 2025-12-03: Major Refactoring

**A. Restructure Skenario**
- Hapus skenario lama (01-05, 07)
- Rename: 06→01, 08→02, 09→03, 10→04, 11→05, 12→06

**B. Modular Architecture**
- `shared/` modules untuk DRY principle
- `BaseTopology` class untuk common functionality
- Single `controller.py` untuk semua skenario

**C. Parameter Update**
- Bandwidth: 0.2 Mbps (realistic congestion ~1.8x)
- Msg Rate: 10 msg/s (same for all, fair comparison)
- Drain Time: 1:1 ratio

**D. Bug Fixes**
- Publisher log truncation: Added `flush=True`
- Packet loss calculation: Use `max(log_count, seq_range)`
- Jitter calculation: Per-device, then aggregate

**E. Verified Results**
```
Anomaly: 0% loss, 206ms delay
Normal: 76% loss, 27,000ms delay
QoS working correctly!
```

---

**Last Updated**: 2025-12-07
