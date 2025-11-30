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

| Skenario | Deskripsi | Topologi |
|----------|-----------|----------|
| 06 | High congestion (0.5 Mbps) | 13 switches, 18 publishers |
| 07 | Core bottleneck | 13 switches, core 0.5 Mbps |
| 08 | Lossy network (packet loss) | 13 switches, 5% loss |
| **09** | **Ring topology + redundancy** | 13 switches, ring at aggregation |
| **10** | **Link failure test** | Same as 09, link s2-s1 disabled |

### Skenario 09 & 10: Ring Topology
```
                    ┌──────┐
                    │  s1  │ CORE (Broker)
                    └───┬──┘
          ┌─────────────┼─────────────┐
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │←───→│  s3   │←───→│  s4   │  AGGREGATION (RING)
      │Floor 1│     │Floor 2│     │Floor 3│
      └───┬───┘←─────────────────→└───┬───┘
          │             │             │
       s5-s7         s8-s10       s11-s13    EDGE (9 switches)
```

---

## 4. PERBAIKAN TERBARU (2025-12-01)

### A. Drain Time
- **Problem**: Message in-flight dihitung sebagai packet loss
- **Solution**: Tunggu `duration` seconds setelah publishers stop
- **Total time**: 2 × duration (send + drain)

### B. Per-Sensor Metrics
- Packet loss per sensor dengan range calculation: `max_seq - min_seq + 1`
- Per-floor summary dengan delay dan loss rate

### C. Experiment Logging
- Semua output disimpan ke `logs/experiment.log`
- Per-experiment folder: `results/scenario/run_YYYY-MM-DD_HH-MM-SS/logs/`

### D. Bug Fix: Packet Loss Calculation
- **Before**: `expected = max_seq + 1` (salah untuk per-phase)
- **After**: `expected = max_seq - min_seq + 1` (benar untuk range)

---

## 5. CARA MENJALANKAN

```bash
# Skenario 09 (Ring topology)
cd /home/mqtt-sdn/scenarios/09-dscp-qos-13switches-ring
sudo ./run_experiment.sh 60  # 60s send + 60s drain = 120s total

# Skenario 10 (Link failure)
cd /home/mqtt-sdn/scenarios/10-dscp-qos-13switches-linkfailure
sudo ./run_experiment.sh 120  # Phase 1: 30s, Phase 2: 90s, Drain: 120s

# Generate summary
cd /home/mqtt-sdn
python3 generate_summary_manual_v2.py results/09-*/run_*/mqtt_metrics_log.csv
python3 generate_summary_linkfailure.py results/10-*/run_*/mqtt_metrics_log.csv
```

---

## 6. STRUKTUR FILE

```
/home/mqtt-sdn/
├── scenarios/
│   ├── 06-dscp-qos-13switches/          # High congestion
│   ├── 07-dscp-qos-13switches-core-bottleneck/
│   ├── 08-dscp-qos-13switches-lossy/
│   ├── 09-dscp-qos-13switches-ring/     # Ring + redundancy
│   └── 10-dscp-qos-13switches-linkfailure/  # Link failure test
├── results/                             # Per-experiment results
├── shared/mqtt/                         # Publisher & subscriber scripts
├── generate_summary_manual_v2.py        # Summary for normal scenarios
├── generate_summary_linkfailure.py      # Summary for link failure
├── CONTEXT.md                           # This file
├── CLAUDE.md                            # Technical guidance
└── README.md                            # Quick start
```

---

## 7. ENVIRONMENT

- OS: Ubuntu Linux
- Python: 3.12.3
- Virtual env Ryu: `/home/aldi/ryu39`
- Dependencies: Mininet, Open vSwitch, Mosquitto, paho-mqtt

---

**Last Updated**: 2025-12-01
