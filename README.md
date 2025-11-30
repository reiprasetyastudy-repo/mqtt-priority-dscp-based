# MQTT-SDN Priority Simulation

DSCP-based QoS framework untuk memprioritaskan traffic MQTT pada jaringan Software-Defined Networking (SDN).

## Fitur Utama

- **DSCP-based Priority**: Standar industri (RFC 2474) untuk prioritas paket
- **5 Level Prioritas**: DSCP 46 (Very High) sampai DSCP 0 (Best Effort)
- **Ring Topology**: Redundansi dengan failover otomatis
- **Link Failure Test**: Simulasi kegagalan link untuk uji redundansi
- **Metrics Collection**: Delay, Jitter, Packet Loss, Throughput

## Requirements

### System Requirements
- Ubuntu 20.04 / 22.04 LTS
- Python 3.9+
- RAM minimal 4GB
- Disk 10GB free space

### Software Dependencies
```bash
# Install system packages
sudo apt update
sudo apt install -y mininet openvswitch-switch mosquitto mosquitto-clients python3-pip python3-venv git
```

## Setup

### 1. Clone Repository
```bash
git clone https://github.com/reiprasetyastudy-repo/mqtt-priority-dscp-based.git
cd mqtt-priority-dscp-based
```

### 2. Create Virtual Environment (Recommended)
```bash
# Buat virtual environment
python3 -m venv venv

# Aktivasi virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Setup Ryu Controller
```bash
# Jika menggunakan venv terpisah untuk Ryu (Python 3.9)
python3.9 -m venv ryu-venv
source ryu-venv/bin/activate
pip install ryu
```

### 4. Verify Installation
```bash
# Cek Mininet
sudo mn --version

# Cek Open vSwitch
sudo ovs-vsctl --version

# Cek Mosquitto
mosquitto -h

# Cek Ryu (dalam venv)
ryu-manager --version
```

## Quick Start

### Menjalankan Skenario 09 (Ring Topology)
```bash
cd scenarios/09-dscp-qos-13switches-ring
sudo ./run_experiment.sh 60  # 60 detik kirim + 60 detik drain = 2 menit total
```

### Menjalankan Skenario 10 (Link Failure Test)
```bash
cd scenarios/10-dscp-qos-13switches-linkfailure
sudo ./run_experiment.sh 60  # Phase 1: 30s, Phase 2: 30s, Drain: 60s
```

### Lihat Hasil
```bash
# Summary otomatis
cat results/09-dscp-qos-13switches-ring/run_*/metrics_summary.txt

# Generate summary detail
python3 generate_summary_manual_v2.py results/09-*/run_*/mqtt_metrics_log.csv
```

## Skenario yang Tersedia

| Skenario | Deskripsi | Topologi |
|----------|-----------|----------|
| 06 | High congestion (0.5 Mbps) | 13 switches |
| 07 | Core bottleneck | 13 switches |
| 08 | Lossy network (5% loss) | 13 switches |
| **09** | **Ring topology + STP** | 13 switches (ring) |
| **10** | **Link failure test** | 13 switches (ring) |

## Arsitektur

```
Publishers (DSCP tagging) → SDN Switches (Queue mapping) → Broker
         ↓                           ↓
    DSCP 46 (anomaly)          Queue 1 (60-80% BW)
    DSCP 0  (normal)           Queue 5 (5-15% BW)
```

## Topologi Ring (Skenario 09-10)

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
      (Floor1)      (Floor2)      (Floor3)
```

## Hasil yang Diharapkan

```
ANOMALY (DSCP 46):
  Avg Delay: ~4,000 ms
  Packet Loss: 0%

NORMAL (DSCP 0):
  Avg Delay: ~10,000 ms
  Packet Loss: 0%

QoS Improvement: ~60% lower delay untuk anomaly
```

## Struktur Direktori

```
mqtt-priority-dscp-based/
├── scenarios/                    # Skenario eksperimen
│   ├── 06-dscp-qos-13switches/
│   ├── 07-dscp-qos-13switches-core-bottleneck/
│   ├── 08-dscp-qos-13switches-lossy/
│   ├── 09-dscp-qos-13switches-ring/
│   └── 10-dscp-qos-13switches-linkfailure/
├── shared/                       # Shared components
│   ├── mqtt/                     # Publisher & Subscriber
│   └── config/                   # Konfigurasi
├── docs/                         # Dokumentasi
│   └── SKENARIO_09_10_GUIDE.md  # Panduan lengkap
├── results/                      # Hasil eksperimen (gitignored)
├── generate_summary_*.py         # Script analisis
├── requirements.txt              # Python dependencies
└── README.md                     # File ini
```

## Dokumentasi

- **[SKENARIO_09_10_GUIDE.md](docs/SKENARIO_09_10_GUIDE.md)** - Panduan lengkap Skenario 09 dan 10
- **[CONTEXT.md](CONTEXT.md)** - Konteks proyek
- **[CLAUDE.md](CLAUDE.md)** - Panduan teknis

## Troubleshooting

### "No route to host"
```bash
# Tunggu STP convergence (35 detik)
# Atau cek flow rules:
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

### Hasil kosong
```bash
# Cleanup dan coba lagi
sudo mn -c
sudo pkill -f ryu-manager
```

### Permission denied
```bash
# Jalankan dengan sudo
sudo ./run_experiment.sh 60
```

## Cleanup

```bash
# Stop semua komponen
sudo ./stop_sdn_mqtt.sh

# Cleanup Mininet
sudo mn -c

# Kill controller
sudo pkill -f ryu-manager
```

## License

Research/Educational Project

---

**Last Updated**: 2025-12-01
