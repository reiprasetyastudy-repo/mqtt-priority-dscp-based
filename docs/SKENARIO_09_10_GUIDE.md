# Panduan Lengkap Skenario 09 dan 10

## Daftar Isi
1. [Pendahuluan](#1-pendahuluan)
2. [Topologi Ring](#2-topologi-ring)
3. [Skenario 09: Ring Topology](#3-skenario-09-ring-topology)
4. [Skenario 10: Link Failure Test](#4-skenario-10-link-failure-test)
5. [Alur Kerja Eksperimen](#5-alur-kerja-eksperimen)
6. [Metrik dan Perhitungan](#6-metrik-dan-perhitungan)
7. [Cara Menjalankan](#7-cara-menjalankan)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Pendahuluan

### Apa yang Dilakukan Skenario Ini?

**Skenario 09 dan 10** menguji sistem QoS (Quality of Service) berbasis DSCP pada jaringan SDN dengan **topologi ring** yang memiliki **redundansi**.

**Tujuan:**
- Membuktikan bahwa traffic MQTT dengan prioritas tinggi (anomaly) dikirim lebih cepat dari traffic biasa (normal)
- Menguji bahwa jaringan tetap berfungsi saat salah satu link mati (failover)

### Kenapa Pakai DSCP?

**DSCP (Differentiated Services Code Point)** adalah cara standar industri untuk menandai prioritas paket di jaringan.

```
Publisher menandai paket → Switch membaca tanda → Switch prioritaskan paket
```

| DSCP Value | Prioritas | Bandwidth | Contoh |
|------------|-----------|-----------|--------|
| 46 | Very High | 60-80% | Alarm kebakaran, gas leak |
| 0 | Best Effort | 5-15% | Data sensor rutin |

---

## 2. Topologi Ring

### Struktur Jaringan

```
                        ┌──────────────────┐
                        │       s1         │  CORE SWITCH
                        │    (Broker)      │  (MQTT Broker di sini)
                        └────────┬─────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
      ┌─────────┐           ┌─────────┐           ┌─────────┐
      │   s2    │◄─────────►│   s3    │◄─────────►│   s4    │
      │ Floor 1 │           │ Floor 2 │           │ Floor 3 │
      └────┬────┘◄──────────────────────────────►└────┬────┘
           │           RING (redundansi)              │
     ┌─────┼─────┐                              ┌─────┼─────┐
     │     │     │                              │     │     │
    s5    s6    s7                             s11   s12   s13
    (r1)  (r2)  (r3)                           (r1)  (r2)  (r3)
     │     │     │                              │     │     │
   2 pub 2 pub 2 pub                          2 pub 2 pub 2 pub
```

### Komponen:
- **1 Core Switch (s1)**: Lokasi broker MQTT
- **3 Aggregation Switch (s2, s3, s4)**: Terhubung dalam RING
- **9 Edge Switch (s5-s13)**: Masing-masing melayani 1 ruangan
- **18 Publisher**: 9 anomaly (DSCP 46) + 9 normal (DSCP 0)
- **1 Subscriber**: Di broker, mengumpulkan metrik

### Apa itu Ring?

Ring adalah koneksi **melingkar** antara switch aggregation:
```
s2 ↔ s3 ↔ s4 ↔ s2
```

**Keuntungan Ring:**
- Jika link s2-s1 mati, traffic masih bisa lewat s2→s3→s1 atau s2→s4→s1
- Jaringan tetap berfungsi meski ada kegagalan link

### STP (Spanning Tree Protocol)

**Masalah:** Ring bisa menyebabkan **broadcast storm** (paket berputar-putar tanpa henti).

**Solusi:** STP memblokir salah satu link untuk mencegah loop, tapi siap mengaktifkannya jika link lain mati.

```
Kondisi Normal:          Saat Link s2-s1 Mati:
    s1                        s1
   /│\                       / \
  / │ \                     /   \
s2  s3  s4                s2     s3─s4
│╲  │  ╱│                 ╲     ╱
│ ╲─┼─╱ │                  ╲   ╱
│BLOCKED│                  AKTIF!
```

---

## 3. Skenario 09: Ring Topology

### Tujuan
Menguji efektivitas QoS DSCP pada topologi ring dalam kondisi **normal** (semua link aktif).

### Apa yang Diukur?
1. **Delay**: Waktu dari publisher kirim → subscriber terima
2. **Jitter**: Variasi delay antar pesan
3. **Packet Loss**: Persentase pesan yang hilang
4. **Throughput**: Jumlah pesan per detik

### Hasil yang Diharapkan
- Traffic DSCP 46 (anomaly) punya delay **lebih rendah** dari DSCP 0 (normal)
- Packet loss **0%** (karena TCP reliable)
- Semua message sampai sebelum eksperimen selesai

### Contoh Output
```
ANOMALY (DSCP 46):
  Avg Delay: 4,073.90 ms
  Packet Loss: 0.00%

NORMAL (DSCP 0):
  Avg Delay: 10,600.17 ms
  Packet Loss: 0.00%

QoS Improvement: 61.6% lower delay for anomaly
```

---

## 4. Skenario 10: Link Failure Test

### Tujuan
Menguji apakah jaringan tetap berfungsi saat **link s2-s1 diputus** (simulasi kegagalan).

### Fase Eksperimen

```
Timeline:
0s ─────────────────── 30s ──────────────────────── duration ─────── drain
│                       │                               │              │
│      PHASE 1          │           PHASE 2             │   DRAIN      │
│   (Link Normal)       │      (Link s2-s1 DOWN)        │   TIME       │
│                       │                               │              │
└───────────────────────┴───────────────────────────────┴──────────────┘
```

**Phase 1 (0-30 detik):**
- Semua link aktif
- Traffic menggunakan jalur langsung

**Phase 2 (30 detik - selesai):**
- Link s2-s1 diputus
- Traffic Floor 1 harus lewat ring: s2→s3→s1 atau s2→s4→s1

### Apa yang Dibuktikan?

1. **Redundansi Bekerja**: Traffic masih sampai meski link mati
2. **Delay Meningkat**: Traffic Floor 1 delay lebih tinggi (jalur lebih panjang)
3. **QoS Tetap Efektif**: Anomaly tetap lebih cepat dari normal

### Contoh Output
```
PHASE 1 (Normal):
  Anomaly Delay: 4,073.90 ms
  Normal Delay: 10,600.17 ms

PHASE 2 (Link Down):
  Anomaly Delay: 28,331.32 ms (+595% ↑)
  Normal Delay: 66,132.60 ms (+524% ↑)

✓ REDUNDANCY WORKS!
  Traffic Floor 1 berhasil lewat ring s2→s3→s1
```

---

## 5. Alur Kerja Eksperimen

### Tahapan Lengkap

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. INITIALIZATION                                                   │
├─────────────────────────────────────────────────────────────────────┤
│  • Cleanup proses sebelumnya (mn -c, pkill)                         │
│  • Buat folder hasil: results/scenario/run_YYYY-MM-DD_HH-MM-SS/     │
│  • Start Ryu Controller                                              │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. BUILD TOPOLOGY (35 detik)                                        │
├─────────────────────────────────────────────────────────────────────┤
│  • Buat 13 switch dengan Mininet                                     │
│  • Hubungkan switch sesuai topologi ring                             │
│  • Enable STP di semua switch                                        │
│  • Tunggu STP convergence (35 detik)                                 │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. CONFIGURE QoS (2 detik)                                          │
├─────────────────────────────────────────────────────────────────────┤
│  • Buat 5 queue di setiap port switch                                │
│  • Queue 1: DSCP 46 (60-80% bandwidth)                               │
│  • Queue 5: DSCP 0 (5-15% bandwidth)                                 │
│  • Install flow rules: match DSCP → set queue                        │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. START MQTT (5 detik)                                             │
├─────────────────────────────────────────────────────────────────────┤
│  • Start Mosquitto broker di host broker                             │
│  • Start subscriber (mengumpulkan metrik)                            │
│  • Start 18 publisher (9 anomaly + 9 normal)                         │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. SEND DATA (duration detik)                                       │
├─────────────────────────────────────────────────────────────────────┤
│  • Publisher kirim 50 msg/detik masing-masing                        │
│  • Total: 18 × 50 = 900 msg/detik                                    │
│  • Subscriber catat: timestamp_sent, timestamp_recv, delay           │
│                                                                      │
│  [Skenario 10 saja]                                                  │
│  • Setelah 30 detik, putus link s2-s1                                │
│  • Traffic Floor 1 dialihkan via ring                                │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  6. DRAIN TIME (duration detik)                                      │
├─────────────────────────────────────────────────────────────────────┤
│  • Stop semua publisher                                              │
│  • Tunggu message yang masih di perjalanan (in-flight)               │
│  • Ini mencegah message dengan delay tinggi dianggap "hilang"        │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  7. COLLECT RESULTS                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  • Stop subscriber                                                   │
│  • Generate metrics_summary.txt                                      │
│  • Simpan mqtt_metrics_log.csv                                       │
│  • Simpan semua log ke folder logs/                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Total Waktu Eksperimen

```
Jika duration = 60 detik:

Tahap                  Waktu
──────────────────────────────
Initialization         ~5s
Build Topology         ~10s
STP Convergence        35s
QoS Config             ~2s
MQTT Start             ~5s
Send Data              60s
Drain Time             60s
Cleanup                ~30s
──────────────────────────────
TOTAL                  ~207s (3.5 menit)
```

---

## 6. Metrik dan Perhitungan

### A. Delay (Latensi)

**Definisi:** Waktu yang dibutuhkan pesan dari publisher sampai ke subscriber.

**Rumus:**
```
Delay = timestamp_received - timestamp_sent
```

**Contoh:**
```
Publisher kirim:  1701388800.123  (Unix timestamp)
Subscriber terima: 1701388804.567
Delay = 4.444 detik = 4444 ms
```

**Kenapa Delay Tinggi?**
- Bandwidth terbatas (0.5 Mbps)
- Banyak publisher (18 × 50 = 900 msg/detik)
- Antrian di switch (queue)

### B. Jitter

**Definisi:** Variasi delay antar pesan berurutan.

**Rumus:**
```
Jitter = |delay_pesan_N - delay_pesan_N-1|
```

**Contoh:**
```
Delay pesan 1: 100 ms
Delay pesan 2: 150 ms
Delay pesan 3: 120 ms

Jitter 1→2 = |150 - 100| = 50 ms
Jitter 2→3 = |120 - 150| = 30 ms
Avg Jitter = (50 + 30) / 2 = 40 ms
```

### C. Packet Loss

**Definisi:** Persentase pesan yang tidak sampai.

**Rumus BENAR (per-phase):**
```
Expected = max_sequence - min_sequence + 1
Received = jumlah sequence unik yang diterima
Lost = Expected - Received
Loss Rate = (Lost / Expected) × 100%
```

**Contoh:**
```
Phase 2:
  Sequence dikirim: 100, 101, 102, ..., 200
  min_seq = 100, max_seq = 200
  Expected = 200 - 100 + 1 = 101
  Received = 98
  Lost = 101 - 98 = 3
  Loss Rate = 3/101 × 100% = 2.97%
```

**Kenapa Bukan max_seq + 1?**
```
SALAH (akan menghitung Phase 1 sebagai lost):
  Expected = 200 + 1 = 201  ← Termasuk 0-99 dari Phase 1!
  Lost = 201 - 98 = 103     ← SALAH BESAR!

BENAR (hanya Phase 2):
  Expected = 200 - 100 + 1 = 101  ← Hanya range Phase 2
  Lost = 101 - 98 = 3              ← BENAR
```

### D. Throughput

**Definisi:** Jumlah pesan yang berhasil dikirim per detik.

**Rumus:**
```
Throughput = Total_Messages / Duration
```

**Contoh:**
```
Total Messages = 38,851
Duration = 17.4 detik
Throughput = 38851 / 17.4 = 2,232 msg/s
```

### E. QoS Improvement

**Definisi:** Seberapa efektif QoS membedakan prioritas.

**Rumus:**
```
Improvement = (Normal_Delay - Anomaly_Delay) / Normal_Delay × 100%
```

**Contoh:**
```
Anomaly Delay = 4,073 ms
Normal Delay = 10,600 ms
Improvement = (10600 - 4073) / 10600 × 100% = 61.6%

Artinya: Anomaly 61.6% lebih cepat dari Normal
```

---

## 7. Cara Menjalankan

### Skenario 09 (Ring Topology)

```bash
# 1. Masuk ke folder skenario
cd /home/mqtt-sdn/scenarios/09-dscp-qos-13switches-ring

# 2. Jalankan eksperimen (60 detik kirim + 60 detik drain = 2 menit)
sudo ./run_experiment.sh 60

# 3. Lihat hasil
cat /home/mqtt-sdn/results/09-dscp-qos-13switches-ring/run_*/metrics_summary.txt

# 4. Generate summary detail
cd /home/mqtt-sdn
python3 generate_summary_manual_v2.py results/09-*/run_*/mqtt_metrics_log.csv
```

### Skenario 10 (Link Failure)

```bash
# 1. Masuk ke folder skenario
cd /home/mqtt-sdn/scenarios/10-dscp-qos-13switches-linkfailure

# 2. Jalankan eksperimen (minimal 60 detik: 30s phase1 + 30s phase2)
sudo ./run_experiment.sh 60

# 3. Lihat hasil
cat /home/mqtt-sdn/results/10-dscp-qos-13switches-linkfailure/run_*/metrics_summary.txt

# 4. Generate summary detail
cd /home/mqtt-sdn
python3 generate_summary_linkfailure.py results/10-*/run_*/mqtt_metrics_log.csv
```

### Output Files

```
results/scenario/run_YYYY-MM-DD_HH-MM-SS/
├── mqtt_metrics_log.csv     # Data mentah setiap pesan
├── metrics_summary.txt      # Ringkasan statistik
└── logs/
    ├── experiment.log       # Log build topology, STP, dll
    ├── ryu_controller.log   # Log SDN controller
    ├── subscriber.log       # Log subscriber
    └── publisher_*.log      # Log setiap publisher
```

---

## 8. Troubleshooting

### Hasil Kosong (0 messages)

**Penyebab:** STP belum konvergen, network loop menyebabkan broadcast storm.

**Solusi:**
1. Pastikan tunggu 35 detik untuk STP convergence
2. Cek log: `cat logs/experiment.log | grep STP`

### "No route to host" Error

**Penyebab:** Publisher tidak bisa reach broker.

**Solusi:**
1. Cek flow rules sudah terinstall: `sudo ovs-ofctl -O OpenFlow13 dump-flows s1`
2. Cek STP status: `sudo ovs-vsctl get Bridge s1 stp_enable`

### Packet Loss Tinggi Palsu

**Penyebab:** Eksperimen stop sebelum message sampai.

**Solusi:** Drain time sudah diimplementasi. Pastikan durasi cukup.

### Delay Sangat Tinggi (>100 detik)

**Penyebab:** Bandwidth sangat terbatas (0.5 Mbps) dengan 18 publisher.

**Ini Normal!** Congestion sengaja dibuat tinggi untuk menguji QoS.

---

## Pertanyaan yang Mungkin Ditanyakan Dosen

### Q: Kenapa pakai DSCP, bukan metode lain?

**A:** DSCP adalah standar industri (RFC 2474) yang:
- Diproses di data plane (tidak membebani controller)
- Didukung hardware acceleration di switch produksi
- Scalable untuk banyak flow

### Q: Bagaimana membuktikan QoS bekerja?

**A:** Lihat perbedaan delay:
- Anomaly (DSCP 46): ~4,000 ms
- Normal (DSCP 0): ~10,600 ms
- QoS improvement: **61.6%**

### Q: Kenapa pakai ring topology?

**A:** Untuk redundansi. Jika satu link mati, traffic masih bisa lewat jalur alternatif.

### Q: Bagaimana membuktikan redundansi bekerja?

**A:** Skenario 10 memutus link s2-s1:
- Phase 1: Traffic langsung
- Phase 2: Traffic lewat ring (delay naik tapi tetap sampai)
- **Bukti:** Message count Phase 2 > 0

### Q: Kenapa packet loss 0% padahal ada congestion?

**A:** MQTT pakai TCP yang menjamin pengiriman dengan retransmission. Yang terjadi bukan packet loss, tapi delay tinggi.

### Q: Apa itu drain time?

**A:** Waktu tunggu setelah publisher stop untuk menangkap message yang masih dalam perjalanan. Tanpa ini, message dengan delay tinggi akan salah dihitung sebagai "lost".

---

## Referensi

- DSCP: RFC 2474
- OpenFlow: Version 1.3
- MQTT: Version 3.1.1
- Mininet: Network Emulator
- Ryu: SDN Controller Framework

---

**Dokumen ini dibuat untuk membantu memahami Skenario 09 dan 10 pada proyek MQTT-SDN Priority.**

*Last Updated: 2025-12-01*
