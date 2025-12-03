# Cara Kerja Sistem Prioritas Data IoT

## Konsep Dasar

Bayangkan jalan raya dengan **2 jalur:**
- **Jalur Cepat (Fast Lane):** Untuk ambulance, pemadam kebakaran → Data Anomaly
- **Jalur Biasa (Regular Lane):** Untuk mobil pribadi → Data Normal

Sistem SDN berfungsi seperti **polisi lalu lintas** yang mengatur traffic agar kendaraan penting dapat lewat lebih cepat.

---

## Komponen Utama Sistem

### 1. MQTT (Messaging Protocol)

**Apa itu MQTT?**
- Protocol untuk perangkat IoT berkomunikasi
- Seperti "WhatsApp untuk sensor"
- Ringan dan efisien untuk perangkat kecil

**Cara Kerja:**
```
[Sensor] --publish--> [Broker] --subscribe--> [Server/Aplikasi]
```

**Dalam Simulasi Ini:**
- **Publisher:** 8 sensor (4 anomaly + 4 normal) mengirim data
- **Broker:** Server pusat (10.0.0.1) menerima semua data
- **Subscriber:** Aplikasi yang mencatat metrik (delay, jitter, loss)
- **Topic:** "iot/data" (semua sensor publish ke topic yang sama)

---

### 2. SDN Controller (Ryu)

**Apa itu SDN Controller?**
- "Otak" dari jaringan
- Mengatur semua switch dalam jaringan
- Membuat keputusan: data mana yang diprioritaskan

**Tugas Controller dalam Simulasi:**
1. Memonitor koneksi switch
2. Mendeteksi traffic MQTT (port 1883)
3. Mengklasifikasi data (anomaly vs normal)
4. Memasang flow rule dengan prioritas berbeda
5. Mengalokasikan ke queue yang sesuai

**Lokasi Controller:**
- IP: 127.0.0.1 (localhost)
- Port: 6633 (OpenFlow control port)

---

### 3. OpenFlow Switch

**Apa itu OpenFlow?**
- Protocol standar antara controller dan switch
- Memungkinkan controller "memerintah" switch

**Cara Kerja Switch:**
1. Paket data masuk ke switch
2. Switch cek **flow table** (tabel aturan)
3. Jika ada aturan yang cocok → eksekusi action
4. Jika tidak ada → tanya controller (Packet-In)
5. Controller install flow rule baru

---

## Alur Kerja Step-by-Step

### Tahap 1: Inisialisasi Jaringan

```
┌──────────────────────────────────────────┐
│ 1. Start Ryu Controller                 │
│    → Menunggu switch connect            │
└──────────────────────────────────────────┘
                ↓
┌──────────────────────────────────────────┐
│ 2. Start Mininet Topology               │
│    → 7 switches connect ke controller   │
└──────────────────────────────────────────┘
                ↓
┌──────────────────────────────────────────┐
│ 3. Controller Install Base Flows        │
│    → ARP (priority 100)                 │
│    → ICMP (priority 90)                 │
│    → Table-miss (priority 0)            │
└──────────────────────────────────────────┘
                ↓
┌──────────────────────────────────────────┐
│ 4. Configure OVS Queues                 │
│    → Queue 1: 70-100% BW (Anomaly)      │
│    → Queue 2: 30-50% BW (Normal)        │
└──────────────────────────────────────────┘
```

---

### Tahap 2: Start MQTT Components

```
┌──────────────────────────────────────────┐
│ 1. Start MQTT Broker                    │
│    → Broker running di 10.0.0.1:1883    │
└──────────────────────────────────────────┘
                ↓
┌──────────────────────────────────────────┐
│ 2. Start Subscriber                     │
│    → Subscribe ke "iot/data"            │
│    → Record timestamp penerimaan        │
└──────────────────────────────────────────┘
                ↓
┌──────────────────────────────────────────┐
│ 3. Start 8 Publishers                   │
│    → 4 Anomaly (IP ganjil)              │
│    → 4 Normal (IP genap)                │
│    → Publish 50 msg/s per sensor        │
└──────────────────────────────────────────┘
```

---

### Tahap 3: Traffic Classification & MAC Learning

Ketika paket pertama dari sensor masuk ke switch:

```
[Packet arrives at switch]
        ↓
[Switch checks flow table]
        ↓
    ┌───────┐
    │No match│ → Send to controller (Packet-In)
    └───────┘
        ↓
┌─────────────────────────────────────────┐
│ CONTROLLER LOGIC:                       │
│                                         │
│ 1. Learn MAC address                   │
│    mac_to_port[dpid][src_mac] = in_port│
│                                         │
│ 2. Check packet type                   │
│    → Is it MQTT? (TCP port 1883)       │
│                                         │
│ 3. Classify by IP                      │
│    ip_last_octet = IP.split('.')[-1]   │
│    if odd → ANOMALY (Queue 1)          │
│    if even → NORMAL (Queue 2)          │
│                                         │
│ 4. Install flow rule                   │
│    Match: src_ip, dst_ip, tcp_dst=1883 │
│    Action: SetQueue(queue_id) +        │
│            Output(learned_port)        │
│    Priority: 20 (anomaly) / 15 (normal)│
└─────────────────────────────────────────┘
        ↓
[Flow installed in switch]
        ↓
[Subsequent packets match flow → fast path]
```

---

### Tahap 4: Prioritas Bekerja (Saat Congestion)

**Kondisi Normal (No Congestion):**
```
Link: ┌─────────────────────────────┐
      │░░░░░░░░░░░░                 │ 40% full
      └─────────────────────────────┘
      ↑ Semua paket lewat langsung
      ✗ PRIORITAS TIDAK TERLIHAT
```

**Kondisi Congestion (80% Utilization):**
```
Link: ┌─────────────────────────────┐
      │████████████████████░░░░░░░░│ 80% full
      └─────────────────────────────┘
      ↑ Paket ANTRI di queue

Queue 1 (Anomaly): ┌──┬──┬──┐        ← Lebih banyak bandwidth
   70-100% BW      │A │A │A │          (700-1000 Kbps)
                   └──┴──┴──┘          Cepat diproses!

Queue 2 (Normal):  ┌──┬──┬──┬──┬──┐  ← Bandwidth terbatas
   30-50% BW       │N │N │N │N │N │    (300-500 Kbps)
                   └──┴──┴──┴──┴──┘    Lebih lama antri!

✅ PRIORITAS TERLIHAT!
   Anomaly: 12.32 ms delay
   Normal:  68.78 ms delay
```

---

## Setting dan Konfigurasi

### 1. Network Settings

**File:** `topology_config.py`

```python
# Bandwidth Limitation
LINK_BANDWIDTH_MBPS = 1      # 1 Mbps per link

# Message Rate (CREATE CONGESTION!)
MSG_RATE = 50                # 50 pesan/detik per sensor

# Calculation:
# 8 sensors × 50 msg/s × 250 bytes × 8 bits = 800 Kbps
# 800 Kbps / 1000 Kbps = 80% utilization ✅
```

**Mengapa 1 Mbps?**
- Cukup rendah untuk menciptakan congestion
- Tidak terlalu rendah (menghindari quantum warning HTB)
- Realistis untuk simulasi IoT

**Mengapa 50 msg/s?**
- 8 × 50 = 400 msg/s total → 800 Kbps
- 80% utilization → paket ANTRI
- Jika 20 msg/s → hanya 32% → prioritas tidak terlihat!

---

### 2. Queue Settings

**File:** `topology_config.py` function `configure_ovs_queues()`

```python
# Queue 1 - High Priority (Anomaly)
queue1_min = 700,000 bps    # 70% guaranteed bandwidth
queue1_max = 1,000,000 bps  # 100% max bandwidth

# Queue 2 - Low Priority (Normal)
queue2_min = 300,000 bps    # 30% guaranteed bandwidth
queue2_max = 500,000 bps    # 50% max bandwidth
```

**Command yang Dijalankan:**
```bash
ovs-vsctl -- set port s1-eth1 qos=@newqos \
-- --id=@newqos create qos type=linux-htb \
   other-config:max-rate=1000000 \
   queues:1=@q1 queues:2=@q2 \
-- --id=@q1 create queue \
   other-config:min-rate=700000 \
   other-config:max-rate=1000000 \
-- --id=@q2 create queue \
   other-config:min-rate=300000 \
   other-config:max-rate=500000
```

**Penjelasan:**
- `type=linux-htb` → Hierarchical Token Bucket (Linux traffic control)
- `min-rate` → Bandwidth minimum dijamin (guaranteed)
- `max-rate` → Bandwidth maksimum (jika ada sisa bandwidth)

---

### 3. Controller Flow Rules

**File:** `controller_v2.py`

```python
# Priority Levels:
priority = 100  # ARP (required for network)
priority = 90   # ICMP (ping)
priority = 20   # MQTT Anomaly
priority = 15   # MQTT Normal
priority = 0    # Table-miss (send to controller)

# Classification Logic:
ip_last_octet = int(ip_src.split('.')[-1])
if ip_last_octet % 2 == 1:
    queue_id = 1      # Anomaly
    priority = 20
else:
    queue_id = 2      # Normal
    priority = 15

# Action:
actions = [
    OFPActionSetQueue(queue_id),    # Assign to queue
    OFPActionOutput(learned_port)   # Forward to specific port
]
```

**CRITICAL: Mengapa TIDAK Pakai OFPP_NORMAL?**

```python
# ❌ BROKEN (Queue tidak work):
actions = [
    OFPActionSetQueue(1),
    OFPActionOutput(OFPP_NORMAL)  # Bypass OpenFlow pipeline!
]

# ✅ WORKING (Queue applied):
actions = [
    OFPActionSetQueue(1),
    OFPActionOutput(3)            # Explicit port dari MAC learning
]
```

**Penjelasan:**
- `OFPP_NORMAL` = L2 learning mode OVS (bypass OpenFlow)
- Ketika bypass, SetQueue action diabaikan
- Solusi: MAC Learning Controller dengan explicit port forwarding

---

## 3 Syarat Agar Prioritas Bekerja

### ✅ Syarat 1: Ada Congestion (>70% Utilization)

```
Low Traffic (32%):          High Traffic (80%):
┌─────────────────────┐     ┌─────────────────────┐
│░░░░░░░              │     │████████████████░░░░│
└─────────────────────┘     └─────────────────────┘
Paket langsung lewat        Paket ANTRI di queue
❌ Prioritas tidak terlihat  ✅ Prioritas terlihat
```

**Setting:** MSG_RATE = 50 (bukan 20!)

---

### ✅ Syarat 2: Queue Mechanism Bekerja

```
Controller dengan OFPP_NORMAL:
[Switch] --NORMAL mode--> [L2 Learning]
                          ↑ Queue diabaikan!

Controller dengan MAC Learning:
[Switch] --OpenFlow--> [Flow Table with Queue]
                       ↑ Queue diterapkan!
```

**Setting:** Gunakan `controller_v2.py` (MAC Learning)

---

### ✅ Syarat 3: Proper Classification

```
Classification Logic:
┌──────────────┬────────────┬──────────┐
│ Source IP    │ Last Octet │ Queue    │
├──────────────┼────────────┼──────────┤
│ 10.0.1.1     │ 1 (odd)    │ Queue 1  │
│ 10.0.1.2     │ 2 (even)   │ Queue 2  │
│ 10.0.1.3     │ 3 (odd)    │ Queue 1  │
│ 10.0.1.4     │ 4 (even)   │ Queue 2  │
└──────────────┴────────────┴──────────┘
```

**Setting:** Sudah benar di `controller_v2.py`

---

## Alur Data Lengkap (End-to-End)

### Contoh: Sensor Anomaly f1r1a (10.0.1.1) mengirim data

```
Step 1: Publisher Generate Message
┌────────────────────────────────────────┐
│ Sensor f1r1a (10.0.1.1)               │
│ ├─ Generate data: {"value": 85}       │
│ ├─ Add timestamp: 1699785876.123      │
│ └─ Publish ke "iot/data"              │
└────────────────────────────────────────┘
        ↓ MQTT packet (TCP port 1883)

Step 2: Edge Switch (s4)
┌────────────────────────────────────────┐
│ Switch s4                              │
│ ├─ Packet-In to controller            │
│ ├─ Controller classify: IP .1 = odd   │
│ ├─ Install flow: Queue 1, Priority 20 │
│ └─ Forward to s2 via Queue 1          │
└────────────────────────────────────────┘
        ↓ Via Queue 1 (high priority)

Step 3: Aggregation Switch (s2)
┌────────────────────────────────────────┐
│ Switch s2                              │
│ ├─ Match flow: MQTT, src=10.0.1.1     │
│ ├─ SetQueue(1) → High priority        │
│ └─ Forward to s1 via Queue 1          │
└────────────────────────────────────────┘
        ↓ Via Queue 1 (high priority)

Step 4: Core Switch (s1)
┌────────────────────────────────────────┐
│ Switch s1                              │
│ ├─ Match flow: MQTT, src=10.0.1.1     │
│ ├─ SetQueue(1) → High priority        │
│ └─ Forward to broker via Queue 1      │
└────────────────────────────────────────┘
        ↓ Via Queue 1 (high priority)

Step 5: Broker Receive
┌────────────────────────────────────────┐
│ Broker (10.0.0.1)                     │
│ └─ Receive MQTT packet                │
└────────────────────────────────────────┘
        ↓

Step 6: Subscriber Process
┌────────────────────────────────────────┐
│ Subscriber                             │
│ ├─ Receive message                    │
│ ├─ Calculate delay:                   │
│ │   delay = now - timestamp_sent      │
│ │   delay = 12.32 ms ✅ (LOW!)        │
│ └─ Save to CSV                        │
└────────────────────────────────────────┘
```

**Bandingkan dengan Sensor Normal (10.0.1.2):**
- Sama sampai step 2
- Di step 2: Queue 2 (low priority) → delay 68.78 ms ❌ (HIGH!)

---

## Timeline Simulasi

```
T+0s:   Start Ryu Controller
T+3s:   Start Mininet topology
T+8s:   Configure OVS queues
T+10s:  Start MQTT Broker
T+12s:  Start Subscriber
T+14s:  Start 8 Publishers
T+15s:  ┌────────────────────────────────────┐
        │ TRAFFIC STARTS                     │
        │ - 8 sensors × 50 msg/s = 400 msg/s│
        │ - 80% utilization                  │
        │ - Congestion active                │
        │ - Priority mechanism engaged       │
        └────────────────────────────────────┘
        ↓
        ... (300 seconds) ...
        ↓
T+315s: Stop publishers
T+317s: Stop subscriber (trigger summary)
T+320s: Stop broker, network cleanup
T+325s: ✅ Simulation complete!
```

**Total Duration:** 301.94 seconds (~5 minutes)

---

## Metrik yang Dikumpulkan

### Subscriber Enhanced

**File:** `subscriber_enhanced.py`

**Data yang dicatat untuk setiap pesan:**
1. **timestamp_sent** - Waktu sensor kirim (dari payload)
2. **timestamp_received** - Waktu subscriber terima
3. **delay_ms** - Selisih waktu (ms)
4. **seq** - Sequence number pesan
5. **device** - Nama sensor
6. **type** - anomaly atau normal

**Metrik yang dihitung:**
- Average Delay
- Min/Max Delay
- Standard Deviation
- Jitter (variasi delay)
- Packet Loss Rate

---

## Kesimpulan Cara Kerja

### Analogi Sederhana:

Sistem ini seperti **sistem antrian rumah sakit**:

1. **Pasien datang** (Data dari sensor)
2. **Petugas cek kondisi** (Controller classify traffic)
3. **Pasien kritis → Ruang Emergency (Queue 1)**
   - Langsung dilayani
   - Delay rendah (12.32 ms)
4. **Pasien non-kritis → Ruang Tunggu Biasa (Queue 2)**
   - Antri lebih lama
   - Delay tinggi (68.78 ms)

**Kunci Sukses:**
✅ Ruang tunggu penuh (congestion 80%)
✅ Ada 2 jalur terpisah (Queue 1 & 2)
✅ Petugas bisa bedakan pasien (classification benar)

---

**Next:** Lihat `HASIL_SIMULASI.md` untuk analisis detail hasil eksperimen.
