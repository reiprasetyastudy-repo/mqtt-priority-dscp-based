# Topologi Jaringan Simulasi

## Gambaran Umum

Topologi jaringan ini meniru struktur jaringan gedung 2 lantai dengan sistem Smart Building IoT.

---

## Struktur Topologi (Diagram)

```
                         ┌──────────────────┐
                         │  SERVER PUSAT    │
                         │  (MQTT Broker)   │
                         │   IP: 10.0.0.1   │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │    CORE SWITCH (s1)       │
                    │  (Penghubung Utama)       │
                    └──────┬─────────────┬──────┘
                           │             │
            ┌──────────────┴──┐      ┌──┴──────────────┐
            │  AGG SWITCH s2  │      │  AGG SWITCH s3  │
            │   (Lantai 1)    │      │   (Lantai 2)    │
            └──┬───────────┬──┘      └──┬───────────┬──┘
               │           │            │           │
         ┌─────┴───┐  ┌────┴────┐  ┌───┴────┐  ┌───┴────┐
         │ EDGE s4 │  │ EDGE s5 │  │ EDGE s6│  │ EDGE s7│
         │ (Rm 1.1)│  │ (Rm 1.2)│  │ (Rm 2.1)│ │ (Rm 2.2)│
         └──┬───┬──┘  └──┬───┬──┘  └──┬───┬──┘ └──┬───┬──┘
            │   │        │   │        │   │       │   │
         ┌──▼┐ ┌▼──┐  ┌─▼┐ ┌▼──┐  ┌─▼┐ ┌▼──┐  ┌─▼┐ ┌▼──┐
         │A  │ │ N │  │A │ │ N │  │A │ │ N │  │A │ │ N │
         │N  │ │ O │  │N │ │ O │  │N │ │ O │  │N │ │ O │
         │O  │ │ R │  │O │ │ R │  │O │ │ R │  │O │ │ R │
         │M  │ │ M │  │M │ │ M │  │M │ │ M │  │M │ │ M │
         │A  │ │ A │  │A │ │ A │  │A │ │ A │  │A │ │ A │
         │L  │ │ L │  │L │ │ L │  │L │ │ L │  │L │ │ L │
         │Y  │ │   │  │Y │ │   │  │Y │ │   │  │Y │ │   │
         └───┘ └───┘  └──┘ └───┘  └──┘ └───┘  └──┘ └───┘
```

### Keterangan Singkat:
- **ANOMALY** = Sensor deteksi bahaya (kebakaran, intrusi, dll) - PRIORITAS TINGGI
- **NORMAL** = Sensor suhu/kelembaban biasa - Prioritas rendah

---

## Komponen Jaringan

### 1. Layer CORE (Pusat)
**Switch Core (s1):**
- Fungsi: Penghubung utama ke semua lantai
- Terhubung ke: Server MQTT Broker (10.0.0.1)
- Tugas: Meneruskan semua data dari/ke lantai 1 dan lantai 2

**Server Broker:**
- IP: 10.0.0.1
- Fungsi: Menerima semua data dari sensor
- Software: Mosquitto MQTT Broker

---

### 2. Layer AGGREGATION (Penghubung Lantai)

**Switch Aggregation s2 (Lantai 1):**
- Fungsi: Menghubungkan semua ruangan di lantai 1 ke core
- Terhubung ke: Edge switch s4 dan s5

**Switch Aggregation s3 (Lantai 2):**
- Fungsi: Menghubungkan semua ruangan di lantai 2 ke core
- Terhubung ke: Edge switch s6 dan s7

---

### 3. Layer EDGE (Ruangan)

Setiap ruangan memiliki 1 edge switch yang menghubungkan 2 sensor:

| Switch | Lantai | Ruangan | Sensor Anomaly IP | Sensor Normal IP |
|--------|--------|---------|-------------------|------------------|
| s4     | 1      | Room 1.1| 10.0.1.1         | 10.0.1.2        |
| s5     | 1      | Room 1.2| 10.0.1.3         | 10.0.1.4        |
| s6     | 2      | Room 2.1| 10.0.2.1         | 10.0.2.2        |
| s7     | 2      | Room 2.2| 10.0.2.3         | 10.0.2.4        |

**Total:** 8 sensor (4 anomaly + 4 normal)

---

## Skema Pengalamatan IP

### Subnet Design

```
10.0.0.0/16  - Jaringan Keseluruhan

├── 10.0.0.1      - Server Broker (Core)
├── 10.0.1.0/24   - Lantai 1
│   ├── 10.0.1.1  - Room 1.1 Anomaly
│   ├── 10.0.1.2  - Room 1.1 Normal
│   ├── 10.0.1.3  - Room 1.2 Anomaly
│   └── 10.0.1.4  - Room 1.2 Normal
└── 10.0.2.0/24   - Lantai 2
    ├── 10.0.2.1  - Room 2.1 Anomaly
    ├── 10.0.2.2  - Room 2.1 Normal
    ├── 10.0.2.3  - Room 2.2 Anomaly
    └── 10.0.2.4  - Room 2.2 Normal
```

### Aturan Klasifikasi:
- **IP Ganjil (.1, .3)** → Sensor ANOMALY → Prioritas Tinggi (Queue 1)
- **IP Genap (.2, .4)** → Sensor NORMAL → Prioritas Rendah (Queue 2)

---

## Spesifikasi Link

### Bandwidth Limitation
Setiap link dibatasi **1 Mbps** untuk menciptakan kondisi congestion:

```
Link Specification:
┌────────┬────────┬───────────┬──────────────┐
│ From   │ To     │ Bandwidth │ Technology   │
├────────┼────────┼───────────┼──────────────┤
│ Broker │ s1     │ 1 Mbps    │ TCLink       │
│ s1     │ s2     │ 1 Mbps    │ TCLink       │
│ s1     │ s3     │ 1 Mbps    │ TCLink       │
│ s2     │ s4     │ 1 Mbps    │ TCLink       │
│ s2     │ s5     │ 1 Mbps    │ TCLink       │
│ s3     │ s6     │ 1 Mbps    │ TCLink       │
│ s3     │ s7     │ 1 Mbps    │ TCLink       │
│ Sensor │ Edge   │ 1 Mbps    │ TCLink       │
└────────┴────────┴───────────┴──────────────┘
```

### Utilization Calculation
```
Traffic Load:
- 8 sensors × 50 msg/s × 250 bytes × 8 bits = 800,000 bps
- 800,000 bps / 1,000,000 bps = 80% utilization

✅ Kondisi CONGESTION tercapai (>70%)
```

---

## Jalur Data (Path)

### Contoh Jalur Data Anomaly dari Lantai 1 Room 1:

```
[Sensor f1r1a]  ──┐
   10.0.1.1       │ 1 Mbps
                  │
              [Switch s4] ──┐
               Edge         │ 1 Mbps
                            │
                      [Switch s2] ──┐
                       Agg Lantai 1  │ 1 Mbps
                                     │
                                [Switch s1] ──┐
                                 Core         │ 1 Mbps
                                              │
                                         [Broker]
                                         10.0.0.1

Total Hops: 4 (sensor → edge → agg → core → broker)
```

---

## Switch Configuration

### Protocol:
- **OpenFlow 1.3** - Semua switch mendukung OpenFlow 1.3
- **Controller:** Remote at 127.0.0.1:6633 (Ryu Controller)

### Queue Configuration per Port:

Setiap port switch memiliki 2 queue:

```
Queue 1 (High Priority - Anomaly):
├── Min Bandwidth: 700 Kbps (70% guaranteed)
└── Max Bandwidth: 1000 Kbps (100% max)

Queue 2 (Low Priority - Normal):
├── Min Bandwidth: 300 Kbps (30% guaranteed)
└── Max Bandwidth: 500 Kbps (50% max)
```

**Teknologi:** Linux HTB (Hierarchical Token Bucket) via OVS

---

## Mengapa Topologi Ini?

### Keuntungan Desain 3-Layer:

1. **Scalable:** Mudah menambah ruangan/lantai baru
2. **Realistic:** Mirip dengan jaringan gedung/kampus nyata
3. **Testable:** Bisa menguji prioritas di berbagai layer
4. **Isolasi:** Setiap lantai terpisah secara logis

### Kondisi yang Dibuat:

- ✅ **Congestion:** 80% utilization memastikan antrian paket
- ✅ **Multi-hop:** 4 hop path menguji prioritas di setiap switch
- ✅ **Mixed Traffic:** Anomaly dan normal traffic bercampur

---

## Ringkasan Topologi

```
┌─────────────────────────────────────────────┐
│ TOPOLOGI SUMMARY                            │
├─────────────────────────────────────────────┤
│ Total Switches    : 7                       │
│ ├─ Core           : 1 (s1)                  │
│ ├─ Aggregation    : 2 (s2, s3)             │
│ └─ Edge           : 4 (s4-s7)              │
│                                             │
│ Total Hosts       : 9                       │
│ ├─ Broker         : 1 (10.0.0.1)           │
│ ├─ Sensor Anomaly : 4 (IP ganjil)          │
│ └─ Sensor Normal  : 4 (IP genap)           │
│                                             │
│ Bandwidth         : 1 Mbps per link        │
│ Utilization       : 80% (congestion)       │
│ Network Depth     : 4 hops                 │
│ OpenFlow Version  : 1.3                    │
└─────────────────────────────────────────────┘
```

---

**Next:** Lihat `CARA_KERJA.md` untuk memahami bagaimana sistem prioritas bekerja di topologi ini.
