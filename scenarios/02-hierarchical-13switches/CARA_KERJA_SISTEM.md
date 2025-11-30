# 📚 Cara Kerja Sistem: Mekanisme Prioritas SDN untuk Data IoT

**Skenario:** 02-hierarchical-13switches
**Tujuan:** Mendemonstrasikan pengiriman data prioritas menggunakan Software Defined Networking (SDN)
**Terakhir Diperbarui:** 10 November 2025

---

## 📋 Daftar Isi

1. [Arsitektur Sistem](#1-arsitektur-sistem)
2. [Peran Komponen](#2-peran-komponen)
3. [Mekanisme Pembatasan Bandwidth](#3-mekanisme-pembatasan-bandwidth)
4. [Konfigurasi Queue (Antrian)](#4-konfigurasi-queue-antrian)
5. [Logika Keputusan Prioritas](#5-logika-keputusan-prioritas)
6. [Perjalanan Paket (End-to-End Flow)](#6-perjalanan-paket-end-to-end-flow)
7. [Mengapa Prioritas Bekerja](#7-mengapa-prioritas-bekerja)
8. [Parameter Konfigurasi](#8-parameter-konfigurasi)
9. [Validasi & Debugging](#9-validasi--debugging)

---

## 1. Arsitektur Sistem

### 1.1 Control Plane vs Data Plane

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTROL PLANE                                │
│  (Pengambilan Keputusan - TIDAK melewatkan traffic)            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │   RYU CONTROLLER                                      │     │
│  │   Proses: python3 ryu-manager                         │     │
│  │   Lokasi: 127.0.0.1:6633 (OpenFlow)                  │     │
│  │           127.0.0.1:8080 (REST API)                   │     │
│  │                                                        │     │
│  │   Aplikasi yang Berjalan:                            │     │
│  │   ├─ controller.py (Aplikasi SDN Kita)               │     │
│  │   └─ ryu.app.ofctl_rest (API Monitoring)             │     │
│  └───────────────────────────────────────────────────────┘     │
│                             │                                   │
│                             │ Protokol OpenFlow                 │
│                             │ (Install Flow Rules)              │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PLANE                                   │
│  (Eksekusi - Meneruskan traffic sesuai aturan)                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  OPEN vSWITCH (s1, s2, ..., s13)                    │       │
│  │  - Menerima flow rules dari controller              │       │
│  │  - Mencocokkan paket dengan flow table              │       │
│  │  - Mengeksekusi aksi (assign queue, forwarding)     │       │
│  │  - Menerapkan batasan bandwidth & QoS               │       │
│  └─────────────────────────────────────────────────────┘       │
│         │                  │                  │                 │
│    Port s5-eth0       Port s5-eth1       Port s5-eth2          │
│    (Ke s2)            (Ke f1r1a)         (Ke f1r1n)            │
│         │                  │                  │                 │
│    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐          │
│    │Queue 1  │        │Queue 1  │        │Queue 1  │          │
│    │70-100%  │        │70-100%  │        │70-100%  │          │
│    │Anomaly  │        │Anomaly  │        │Anomaly  │          │
│    ├─────────┤        ├─────────┤        ├─────────┤          │
│    │Queue 2  │        │Queue 2  │        │Queue 2  │          │
│    │30-50%   │        │30-50%   │        │30-50%   │          │
│    │Normal   │        │Normal   │        │Normal   │          │
│    └────┬────┘        └────┬────┘        └────┬────┘          │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                │
│                            │                                    │
│                   ┌────────▼────────┐                          │
│                   │  Port Fisik     │                          │
│                   │  Bandwidth:     │                          │
│                   │  0.05 atau 0.1  │                          │
│                   │  Mbps (Terbatas)│                          │
│                   └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Topologi Jaringan

```
                    ┌──────────────┐
                    │ RYU          │ Control Plane
                    │ CONTROLLER   │ (127.0.0.1:6633)
                    └──────┬───────┘
                           │ OpenFlow
                    ┌──────▼───────┐
                    │   s1 (CORE)  │ Data Plane
                    │  + Broker    │ (10.0.0.1)
                    └──────┬───────┘
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼────┐     ┌─────▼────┐     ┌────▼─────┐
    │s2 (AGG)  │     │s3 (AGG)  │     │s4 (AGG)  │
    │ Lantai 1 │     │ Lantai 2 │     │ Lantai 3 │
    └─────┬────┘     └─────┬────┘     └────┬─────┘
          │                │                │
    ┌─────┼────┐     ┌─────┼────┐     ┌────┼─────┐
    │     │    │     │     │    │     │    │     │
 ┌──▼─┬──▼─┬──▼──┐ ┌▼──┬──▼─┬──▼──┐ ┌▼──┬─▼──┬──▼──┐
 │s5  │s6  │s7   │ │s8 │s9  │s10  │ │s11│s12 │s13  │ EDGE
 │.1.x│.1.x│.1.x │ │.2.x│.2.x│.2.x │ │.3.x│.3.x│.3.x│
 └─┬──┴─┬──┴──┬──┘ └─┬─┴──┬─┴──┬──┘ └─┬─┴──┬─┴──┬──┘
   │    │     │      │    │    │      │    │    │
  h1   h2    h3     h4   h5   h6     h7   h8   h9    Publisher
 (a)  (n)   (a)    (n)  (a)  (n)    (a)  (n)  (a)    (18 total)

Keterangan:
  (a) = publisher anomaly (IP ganjil: .1, .3, .5) → Queue 1
  (n) = publisher normal (IP genap: .2, .4, .6) → Queue 2
```

---

## 2. Peran Komponen

### 2.1 Ryu Framework

**File:** Ryu terinstall di `/home/aldi/ryu39/`

**Peran:** Platform SDN Controller
- Menyediakan framework untuk membuat aplikasi SDN
- Mengelola komunikasi OpenFlow dengan switch
- Menangani event (koneksi switch, kedatangan paket, dll)
- Menyediakan REST API untuk monitoring

**Analogi:** Sistem operasi untuk aplikasi SDN

**Penting:** Ryu TIDAK memutuskan prioritas! Hanya platform saja.

---

### 2.2 Priority Controller (Aplikasi SDN Kita)

**File:** `controller.py`

**Peran:** Logika Keputusan Prioritas
- **Mendeteksi** saat switch terkoneksi ke controller
- **Memutuskan** traffic mana yang dapat prioritas
- **Menginstall** flow rules ke switch via OpenFlow
- **Menugaskan** paket ke Queue 1 atau Queue 2

**Fungsi Utama:**

```python
@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
def switch_features_handler(self, ev):
    """Dipicu saat switch terkoneksi ke controller"""
    # Identifikasi tipe switch (core, aggregation, edge)
    # Install flow rules yang sesuai
```

```python
def install_edge_flows(self, datapath, dpid):
    """Install flow rules untuk edge switches"""

    # Rule 1: Traffic anomaly → Queue 1
    for ip in [1, 3, 5]:  # IP Ganjil
        match = OFPMatch(ipv4_src=f"10.0.{floor}.{ip}", tcp_dst=1883)
        actions = [
            OFPActionSetQueue(1),  # Tugaskan ke Queue 1
            OFPActionOutput(NORMAL)
        ]
        add_flow(datapath, priority=20, match, actions)

    # Rule 2: Traffic normal → Queue 2
    for ip in [2, 4, 6]:  # IP Genap
        match = OFPMatch(ipv4_src=f"10.0.{floor}.{ip}", tcp_dst=1883)
        actions = [
            OFPActionSetQueue(2),  # Tugaskan ke Queue 2
            OFPActionOutput(NORMAL)
        ]
        add_flow(datapath, priority=15, match, actions)
```

**Analogi:** Polisi lalu lintas yang memberi instruksi

---

### 2.3 Open vSwitch (OVS)

**Peran:** Software Switch yang Dapat Diprogram (Data Plane)
- Menerima flow rules dari controller
- Menyimpan rules di flow table
- Mencocokkan paket yang masuk dengan flow table
- Mengeksekusi aksi (assign queue, forwarding)
- Menerapkan batasan bandwidth via Linux TC (Traffic Control)

**Contoh Flow Table (Switch s5):**

```
Priority | Kondisi Match                | Aksi
---------|------------------------------|-------------------------
100      | eth_type=ARP                 | OUTPUT(NORMAL)
90       | eth_type=IPv4, ip_proto=ICMP | OUTPUT(NORMAL)
20       | ip_src=10.0.1.1, tcp_dst=1883| SET_QUEUE(1), OUTPUT(NORMAL)
20       | ip_src=10.0.1.3, tcp_dst=1883| SET_QUEUE(1), OUTPUT(NORMAL)
20       | ip_src=10.0.1.5, tcp_dst=1883| SET_QUEUE(1), OUTPUT(NORMAL)
15       | ip_src=10.0.1.2, tcp_dst=1883| SET_QUEUE(2), OUTPUT(NORMAL)
15       | ip_src=10.0.1.4, tcp_dst=1883| SET_QUEUE(2), OUTPUT(NORMAL)
15       | ip_src=10.0.1.6, tcp_dst=1883| SET_QUEUE(2), OUTPUT(NORMAL)
12       | ip_src=10.0.0.1              | OUTPUT(NORMAL)
0        | * (semua)                    | DROP
```

**Analogi:** Lampu lalu lintas yang mengeksekusi instruksi

---

### 2.4 TC/HTB (Traffic Control / Hierarchical Token Bucket)

**Peran:** Manajemen Bandwidth Level Kernel
- Membatasi bandwidth di setiap port
- Mengimplementasikan queue (Queue 1, Queue 2)
- Menjadwalkan transmisi paket berdasarkan prioritas queue
- Menegakkan alokasi bandwidth (70-100% vs 30-50%)

**Lokasi:** Kernel Linux (di dalam namespace jaringan Mininet)

**Analogi:** Lebar jalan fisik dan manajemen jalur

---

### 2.5 Mininet TCLink

**File:** `topology_config.py`

**Peran:** Emulasi Jaringan dengan Batasan Bandwidth

```python
# Membuat link dengan batasan bandwidth
self.net.addLink(host1, switch1, bw=0.05)  # 0.05 Mbps = 50 Kbps
```

**Yang terjadi secara internal:**
```bash
# Mininet mengeksekusi perintah ini di namespace jaringan:
tc qdisc add dev s1-eth1 root handle 1: htb default 1
tc class add dev s1-eth1 parent 1: classid 1:1 htb rate 0.05mbit
```

**Hasil:** Port fisik `s1-eth1` dibatasi throughput maksimum 50 Kbps

---

## 3. Mekanisme Pembatasan Bandwidth

### 3.1 Dimana Bandwidth Dibatasi

**Jawaban: Di SETIAP PORT pada SETIAP SWITCH**

```
Contoh: Switch s5 punya 4 port, SEMUA dibatasi:

s5-eth0 (ke s2):    50 Kbps ← Link ke aggregation switch
s5-eth1 (ke f1r1a): 50 Kbps ← Link ke publisher anomaly
s5-eth2 (ke f1r1n): 50 Kbps ← Link ke publisher normal
s5-eth3 (ke f1r2a): 50 Kbps ← Link ke publisher anomaly
```

**Total:** 13 switch × ~3-4 port = ~40 link dengan batasan bandwidth

### 3.2 Bagaimana Batasan Bandwidth Diterapkan

**File:** `topology_config.py`, baris 56-59

```python
# Konfigurasi
ENABLE_BANDWIDTH_LIMIT = True
LINK_BANDWIDTH_MBPS = 0.05  # ← UBAH DI SINI untuk adjust bandwidth
ENABLE_QOS_QUEUES = True
```

**Proses:**

**Langkah 1: Pembuatan Link (Mininet)**
```python
# Baris ~96
self.net.addLink(h_broker, s1, bw=LINK_BANDWIDTH_MBPS)
```

**Langkah 2: Konfigurasi TC (Otomatis)**
```bash
# Mininet menjalankan secara internal:
tc qdisc add dev s1-eth1 root handle 1: htb default 1
tc class add dev s1-eth1 parent 1: classid 1:1 htb rate 50000  # 50 Kbps
```

**Langkah 3: Konfigurasi Queue OVS (Manual)**
```python
# Fungsi: configure_ovs_queues(), baris 261-315

max_rate = LINK_BANDWIDTH_MBPS * 1000000  # 0.05 × 1,000,000 = 50,000 bps

# Queue 1 (Anomaly): 70-100% bandwidth
queue1_min = int(max_rate * 0.7)  # 35,000 bps terjamin
queue1_max = max_rate              # 50,000 bps maksimum

# Queue 2 (Normal): 30-50% bandwidth
queue2_min = int(max_rate * 0.3)  # 15,000 bps terjamin
queue2_max = int(max_rate * 0.5)  # 25,000 bps maksimum

# Terapkan ke OVS
ovs-vsctl -- set port s5-eth0 qos=@newqos \
  -- --id=@newqos create qos type=linux-htb \
     other-config:max-rate=50000 \
     queues:1=@q1 queues:2=@q2 \
  -- --id=@q1 create queue \
     other-config:min-rate=35000 \
     other-config:max-rate=50000 \
  -- --id=@q2 create queue \
     other-config:min-rate=15000 \
     other-config:max-rate=25000
```

### 3.3 Distribusi Bandwidth

```
Total Bandwidth Port: 50 Kbps
│
├─ Queue 1 (Anomaly): 35-50 Kbps
│  ├─ Terjamin: 35 Kbps (70%)
│  └─ Maksimum: 50 Kbps (100% jika Queue 2 idle)
│
└─ Queue 2 (Normal): 15-25 Kbps
   ├─ Terjamin: 15 Kbps (30%)
   └─ Maksimum: 25 Kbps (50% meskipun bandwidth tersedia)
```

**Poin Penting:** Queue 2 TIDAK PERNAH dapat lebih dari 50% meskipun bandwidth tersedia!

---

## 4. Konfigurasi Queue (Antrian)

### 4.1 Logika Penugasan Queue

**Keputusan dibuat oleh:** SDN Controller (controller.py)

**Berdasarkan:** Alamat IP sumber (oktet terakhir)

```python
# Flow rules di edge switch:

# Publisher anomaly (IP ganjil: .1, .3, .5) → Queue 1
IP 10.0.1.1 → Queue 1 (Priority 20)
IP 10.0.1.3 → Queue 1 (Priority 20)
IP 10.0.1.5 → Queue 1 (Priority 20)

# Publisher normal (IP genap: .2, .4, .6) → Queue 2
IP 10.0.2.2 → Queue 2 (Priority 15)
IP 10.0.2.4 → Queue 2 (Priority 15)
IP 10.0.2.6 → Queue 2 (Priority 15)
```

### 4.2 Properti Queue

| Properti | Queue 1 (Anomaly) | Queue 2 (Normal) |
|----------|-------------------|------------------|
| **Min Bandwidth** | 70% (35 Kbps @ 0.05 Mbps) | 30% (15 Kbps @ 0.05 Mbps) |
| **Max Bandwidth** | 100% (50 Kbps @ 0.05 Mbps) | 50% (25 Kbps @ 0.05 Mbps) |
| **Prioritas** | Tinggi | Rendah |
| **Scheduler** | HTB (Hierarchical Token Bucket) | HTB |
| **Tipe Traffic** | MQTT dari IP ganjil | MQTT dari IP genap |

### 4.3 Perilaku Queue Saat Ada Beban

**Skenario 1: Beban Jaringan Rendah (< 30%)**
```
Total traffic: 10 Kbps
├─ Queue 1: Dapat sesuai kebutuhan (mis. 5 Kbps)
└─ Queue 2: Dapat sesuai kebutuhan (mis. 5 Kbps)

Hasil: Kedua queue lancar, tidak ada kongesti
```

**Skenario 2: Beban Sedang (30-70%)**
```
Total traffic: 40 Kbps (melebihi kapasitas total 50 Kbps)
├─ Queue 1: Dapat 35 Kbps (minimum terjamin)
└─ Queue 2: Dapat 15 Kbps (sisa bandwidth)

Hasil: Queue 1 diprioritaskan, Queue 2 mulai delay
```

**Skenario 3: Beban Tinggi (> 70%)**
```
Total traffic: 60 Kbps (kedua queue mau lebih dari tersedia)
├─ Queue 1: Dapat 35-50 Kbps (sampai 100% port)
└─ Queue 2: Dapat 0-15 Kbps (sisa saja)

Hasil: Queue 1 dapat prioritas, Queue 2 sangat terbatas
```

**Inilah mengapa pembatasan bandwidth DIPERLUKAN untuk melihat efek prioritas!**

---

## 5. Logika Keputusan Prioritas

### 5.1 Dua Tipe Prioritas

**Tipe 1: Flow Priority (OpenFlow)**
- Mengontrol flow rule mana yang dicek PERTAMA
- TIDAK mempengaruhi kecepatan forwarding
- Hanya menentukan urutan pencocokan di flow table

```python
priority=20  # Flow rule anomaly (dicek pertama)
priority=15  # Flow rule normal (dicek kedua)
priority=0   # Default drop (dicek terakhir)
```

**Tipe 2: Queue Priority (QoS)**
- Mengontrol alokasi bandwidth
- MEMPENGARUHI kecepatan forwarding
- Menentukan delay dan throughput

```python
SET_QUEUE(1)  # Queue prioritas tinggi (70-100% bandwidth)
SET_QUEUE(2)  # Queue prioritas rendah (30-50% bandwidth)
```

**Penting:** Queue priority yang membuat data anomaly lebih cepat!

### 5.2 Metode Klasifikasi

**Metode:** Klasifikasi berbasis IP

**Logika:**
```python
last_octet = int(ip_src.split('.')[-1])

if last_octet in [1, 3, 5]:
    # IP Ganjil → Anomaly
    queue = 1
    priority = 20
elif last_octet in [2, 4, 6]:
    # IP Genap → Normal
    queue = 2
    priority = 15
else:
    # Tidak dikenal → Drop
    queue = None
    priority = 0
```

**Alternatif:** Bisa menggunakan berbasis subnet, DSCP, VLAN, atau DPI (Deep Packet Inspection)

---

## 6. Perjalanan Paket (End-to-End Flow)

### 6.1 Alur Lengkap: Pesan Anomaly

**Skenario:** Publisher `f1r1a` (10.0.1.1) mengirim pesan MQTT ke broker (10.0.0.1)

```
┌─────────────────────────────────────────────────────────────────┐
│ LANGKAH 1: Publisher Mengirim Pesan                            │
└─────────────────────────────────────────────────────────────────┘

Host: f1r1a (10.0.1.1)
  ├─ Proses: publisher_anomaly.py
  ├─ Membuat paket MQTT:
  │    IP Sumber: 10.0.1.1
  │    IP Tujuan: 10.0.0.1
  │    Port Tujuan: 1883 (MQTT)
  │    Payload: {"device":"sensor_f1r1a","type":"anomaly","value":85,...}
  └─ Kirim via interface f1r1a-eth0
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LANGKAH 2: Edge Switch s5 Menerima Paket                       │
└─────────────────────────────────────────────────────────────────┘

Switch: s5 (EDGE)
Port: s5-eth1 (terhubung ke f1r1a)

Aksi: Paket Tiba
  ├─ Ekstrak header:
  │    eth_type: 0x0800 (IPv4)
  │    ip_src: 10.0.1.1
  │    ip_dst: 10.0.0.1
  │    ip_proto: 6 (TCP)
  │    tcp_dst: 1883
  │
  ├─ Cari di Flow Table (prioritas tertinggi dulu):
  │    Priority 100: ARP? TIDAK (eth_type=0x0800, bukan 0x0806)
  │    Priority 90: ICMP? TIDAK (ip_proto=6, bukan 1)
  │    Priority 20: ip_src=10.0.1.1, tcp_dst=1883? YA! ✅
  │
  └─ Eksekusi Aksi:
       ├─ SET_QUEUE(1) → Masukkan ke Queue 1
       └─ OUTPUT(NORMAL) → Forward ke tujuan (s2)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LANGKAH 3: Antrian di Port Output s5-eth0                      │
└─────────────────────────────────────────────────────────────────┘

Port: s5-eth0 (ke aggregation switch s2)
Bandwidth: 50 Kbps total

Queue:
  ├─ Queue 1: [PKT1, PKT2, PKT3, ...]  ← Paket kita masuk sini
  │    - Min: 35 Kbps
  │    - Max: 50 Kbps
  │    - Beban saat ini: 18 Kbps
  │
  └─ Queue 2: [PKT10, PKT11, ...]
       - Min: 15 Kbps
       - Max: 25 Kbps
       - Beban saat ini: 12 Kbps

HTB Scheduler:
  ├─ Cek Queue 1 dulu (prioritas tinggi)
  ├─ Ambil paket dari Queue 1
  ├─ Alokasikan bandwidth: 35 Kbps terjamin
  └─ Transmit paket
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LANGKAH 4: Aggregation Switch s2 Menerima Paket                │
└─────────────────────────────────────────────────────────────────┘

Switch: s2 (AGGREGATION - Lantai 1)
Port: s2-eth2 (dari s5)

Aksi: Cari di Flow Table
  ├─ Priority 20: MQTT ke broker? YA! ✅
  └─ Eksekusi Aksi:
       └─ OUTPUT(NORMAL) → Forward ke s1 (core)

Catatan: Tidak ada assign queue di sini (sudah di Queue 1 dari edge)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LANGKAH 5: Core Switch s1 Menerima Paket                       │
└─────────────────────────────────────────────────────────────────┘

Switch: s1 (CORE)
Port: s1-eth2 (dari s2)

Aksi: Cari di Flow Table
  ├─ Priority 20: MQTT ke broker (10.0.0.1)? YA! ✅
  └─ Eksekusi Aksi:
       └─ OUTPUT(1) → Forward ke host broker via s1-eth1
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LANGKAH 6: Broker Menerima Pesan                               │
└─────────────────────────────────────────────────────────────────┘

Host: broker (10.0.0.1)
Proses: mosquitto (MQTT broker)

Aksi: Terima & Forward ke Subscriber
  ├─ Broker menerima pesan MQTT PUBLISH
  ├─ Cari topik: "iot/data"
  ├─ Forward ke subscriber (host yang sama)
  └─ Subscriber hitung delay:
       publish_timestamp = 2025-11-10T15:30:00.000Z
       receive_timestamp = 2025-11-10T15:30:00.032Z
       delay = 32 ms ✅ (Delay rendah karena Queue 1!)
```

### 6.2 Perbandingan: Alur Pesan Normal

**Jalur sama, tapi queue berbeda:**

```
Host f1r1n (10.0.1.2) → s5 (Queue 2) → s2 → s1 → broker

Perbedaan Kunci di s5:
  ├─ Match: ip_src=10.0.1.2, tcp_dst=1883 (Priority 15)
  ├─ Aksi: SET_QUEUE(2) ← Masuk Queue 2!
  └─ Properti Queue 2:
       - Min: 15 Kbps (hanya 30% terjamin)
       - Max: 25 Kbps (dibatasi 50%)
       - Prioritas lebih rendah di scheduler

Hasil:
  └─ Delay: 35 ms ⚠️ (Delay lebih tinggi karena Queue 2)
```

---

## 7. Mengapa Prioritas Bekerja

### 7.1 Mekanisme Kunci

**Tanpa Kongesti (Traffic Rendah):**
```
Total traffic: 10 Kbps
Bandwidth tersedia: 50 Kbps

Queue 1 (Anomaly): 5 Kbps → Delay: 2 ms
Queue 2 (Normal):  5 Kbps → Delay: 2 ms

Hasil: TIDAK ADA PERBEDAAN (tidak ada kongesti, prioritas tidak diperlukan!)
```

**Dengan Kongesti (Traffic Tinggi):**
```
Total traffic: 40 Kbps
Bandwidth tersedia: 50 Kbps (kongesti 80%)

Queue 1 (Anomaly): Dapat 35 Kbps → Delay: 15 ms ✅
Queue 2 (Normal):  Dapat 15 Kbps → Delay: 22 ms ⚠️

Hasil: Selisih 7 ms (peningkatan 30%!)
```

**Inilah mengapa kita pakai bandwidth 0.05 Mbps:**
- Menciptakan kongesti (~37% beban jaringan)
- Memaksa scheduler memprioritaskan Queue 1
- Membuat efek prioritas terlihat di pengukuran

### 7.2 Model Matematis

**Perhitungan Delay (Disederhanakan):**

```
Delay = Transmission_Delay + Queueing_Delay + Propagation_Delay

Dimana:
  Transmission_Delay = Ukuran_Paket / Bandwidth
  Queueing_Delay = Panjang_Queue / Service_Rate
  Propagation_Delay ≈ 0 (jaringan virtual)
```

**Queue 1 (Prioritas Tinggi):**
```
Service_Rate = 35-50 Kbps (70-100%)
Rata-rata_Panjang_Queue = 2 paket (rendah karena prioritas)
Queueing_Delay = 2 × 128 bytes / 35000 bps ≈ 5.8 ms
```

**Queue 2 (Prioritas Rendah):**
```
Service_Rate = 15-25 Kbps (30-50%)
Rata-rata_Panjang_Queue = 5 paket (tinggi karena prioritas rendah)
Queueing_Delay = 5 × 128 bytes / 15000 bps ≈ 34 ms
```

**Hasil:** Queue 2 punya ~6x delay antrian lebih tinggi!

---

## 8. Parameter Konfigurasi

### 8.1 Konfigurasi Bandwidth

**File:** `topology_config.py`

**Baris 56-59:**
```python
ENABLE_BANDWIDTH_LIMIT = True   # Enable/disable batasan bandwidth
LINK_BANDWIDTH_MBPS = 0.05      # Bandwidth per link (Mbps)
ENABLE_QOS_QUEUES = True        # Enable/disable konfigurasi queue
```

**Untuk Mengubah Bandwidth:**
1. Edit nilai `LINK_BANDWIDTH_MBPS` (mis. 0.1, 0.5, 1.0)
2. Jalankan test: `sudo ./run_experiment.sh --scenario 02-hierarchical-13switches --duration 120`
3. Semua queue auto-adjust secara proporsional

### 8.2 Alokasi Bandwidth Queue

**File:** `topology_config.py`

**Baris ~290-295:**
```python
# Queue 1 (Anomaly)
queue1_min = int(max_rate * 0.7)  # 70% terjamin
queue1_max = max_rate              # 100% maksimum

# Queue 2 (Normal)
queue2_min = int(max_rate * 0.3)  # 30% terjamin
queue2_max = int(max_rate * 0.5)  # 50% maksimum
```

**Untuk Mengubah Alokasi:**
```python
# Contoh: Prioritas lebih agresif (pembagian 80/20)
queue1_min = int(max_rate * 0.8)  # 80% terjamin
queue2_min = int(max_rate * 0.2)  # 20% terjamin
```

### 8.3 Prioritas Flow Rules

**File:** `controller.py`

**Baris 138, 158:**
```python
# Traffic anomaly
self.add_flow(datapath, priority=20, match_anomaly, actions_anomaly)

# Traffic normal
self.add_flow(datapath, priority=15, match_normal, actions_normal)
```

**Untuk Mengubah Prioritas Flow:**
- Angka lebih tinggi = prioritas lebih tinggi
- Harus dijaga: Anomaly > Normal > Default (0)

---

## 9. Validasi & Debugging

### 9.1 Verifikasi Flow Rules Terinstall

```bash
# Cek flow table untuk switch s5
sudo ovs-ofctl -O OpenFlow13 dump-flows s5

# Output yang diharapkan:
# priority=100,arp actions=NORMAL
# priority=20,tcp,nw_src=10.0.1.1,tp_dst=1883 actions=set_queue:1,NORMAL
# priority=20,tcp,nw_src=10.0.1.3,tp_dst=1883 actions=set_queue:1,NORMAL
# priority=15,tcp,nw_src=10.0.1.2,tp_dst=1883 actions=set_queue:2,NORMAL
# priority=15,tcp,nw_src=10.0.1.4,tp_dst=1883 actions=set_queue:2,NORMAL
```

### 9.2 Verifikasi Konfigurasi Queue

```bash
# Cek konfigurasi QoS untuk port s5-eth0
sudo ovs-vsctl list qos

# Cek queues
sudo ovs-vsctl list queue

# Diharapkan: 2 queue per port dengan min-rate dan max-rate terkonfigurasi
```

### 9.3 Verifikasi Batasan Bandwidth

```bash
# Cek konfigurasi TC di port switch
sudo tc class show dev s5-eth0

# Output yang diharapkan:
# class htb 1:1 root rate 50Kbit ...
```

### 9.4 Monitor Penggunaan Queue (Real-time)

```bash
# Cek jumlah paket per flow rule
sudo ovs-ofctl -O OpenFlow13 dump-flows s5 | grep "set_queue"

# Contoh output:
# priority=20,tcp,nw_src=10.0.1.1,tp_dst=1883 actions=set_queue:1,NORMAL
#   n_packets=120, n_bytes=15360  ← 120 paket ke Queue 1
# priority=15,tcp,nw_src=10.0.1.2,tp_dst=1883 actions=set_queue:2,NORMAL
#   n_packets=118, n_bytes=15104  ← 118 paket ke Queue 2
```

### 9.5 Masalah Umum

**Masalah 1: Tidak ada efek prioritas terlihat**
- **Penyebab:** Bandwidth terlalu tinggi, tidak ada kongesti
- **Solusi:** Kurangi `LINK_BANDWIDTH_MBPS` ke 0.05 atau 0.1

**Masalah 2: Semua traffic masuk Queue 1**
- **Penyebab:** Flow rules untuk Queue 2 tidak ada
- **Solusi:** Cek log controller, verifikasi flow rules terinstall

**Masalah 3: Warning HTB quantum**
- **Penyebab:** Bandwidth sangat rendah (<0.1 Mbps)
- **Solusi:** Tambahkan `other-config:r2q=1` ke config QoS (opsional, kosmetik)

**Masalah 4: Tidak ada pesan diterima**
- **Penyebab:** Flow rules tidak terinstall atau broker tidak jalan
- **Solusi:** Cek log controller, verifikasi switch terkoneksi

---

## 📚 Referensi

- **Konfigurasi Topologi:** `topology_config.py`
- **SDN Controller:** `controller.py`
- **Script Publisher:** `../../shared/mqtt/publisher_*.py`
- **Script Subscriber:** `../../shared/mqtt/subscriber_enhanced.py`
- **Laporan Eksperimen:** `EXPERIMENT_REPORT.md`
- **Hasil:** `../../results/02-hierarchical-13switches/`

---

## 📝 Ringkasan

**Poin Kunci:**

1. **Control Plane (Ryu + controller.py)** memutuskan traffic mana yang dapat prioritas
2. **Data Plane (OVS + TC/HTB)** mengeksekusi prioritas via penugasan queue
3. **Pembatasan bandwidth** menciptakan kongesti untuk membuat prioritas terlihat
4. **Alokasi queue** (70-100% vs 30-50%) menentukan perbedaan kecepatan aktual
5. **Flow rules** diinstall di edge switch, mengklasifikasi traffic berdasarkan IP sumber
6. **Efek prioritas** hanya terlihat saat ada kongesti jaringan (>30% beban)

**Sistem ini mendemonstrasikan:**
> "Data IoT kritikal (anomaly) dapat dikirim lebih cepat dari data normal dengan menggunakan prioritas berbasis queue SDN, khususnya saat ada kongesti jaringan."

---

**Terakhir Diperbarui:** 10 November 2025
**Versi:** 2.2 (Setelah perbaikan bug controller)
