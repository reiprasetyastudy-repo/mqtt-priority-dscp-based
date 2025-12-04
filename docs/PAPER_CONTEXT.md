# PAPER_CONTEXT.md - Konteks Paper LaTeX untuk AI Assistant

> **File ini berisi konteks paper LaTeX agar AI assistant dapat melanjutkan pekerjaan tanpa kehilangan informasi penting.**

---

## 1. OVERVIEW

### Lokasi File
```
/home/mqtt-sdn/docs/latex/
├── paper_full.tex      # Versi lengkap (6 halaman)
├── paper_short.tex     # Versi ringkas untuk conference (3 halaman + Results)
├── paper_full.pdf      # Output PDF
├── paper_short.pdf     # Output PDF
├── IEEEtran.cls        # IEEE template class
└── images/
    ├── Arsitektur-Sistem-DSCP-BasedQoS -MQTT.png
    ├── first-topology.png
    └── second-topology.png
```

### Judul Paper
**"DSCP-Based QoS Framework for MQTT Traffic Prioritization in Software-Defined Networks"**

### Penulis
1. Abdurrizqo Arrahman (6025251013@student.its.ac.id)
2. Ahmad Bilal (6025251040@student.its.ac.id)
3. Reinaldi Prasetya (6025251043@student.its.ac.id)

Afiliasi: Department of Informatics, Institut Teknologi Sepuluh Nopember, Surabaya

---

## 2. PARAMETER EKSPERIMEN (WAJIB KONSISTEN)

> **PENTING**: Parameter ini harus konsisten dengan `/home/mqtt-sdn/CONTEXT.md`

| Parameter | Nilai | Keterangan |
|-----------|-------|------------|
| Bandwidth | **0.2 Mbps** (200 Kbps) | Semua link |
| Msg Rate | **10 msg/s** | Per publisher |
| Payload | **~150 bytes** | JSON format |
| Total Load | **~360 Kbps** | 18 publisher + overhead |
| Congestion | **~1.8x** | Load/Bandwidth ratio |
| Send Phase | **10 menit** | Publisher aktif |
| Drain Phase | **10 menit** | Publisher stop, subscriber masih menerima |
| Total Duration | **20 menit** | Per run |
| Jeda antar Run | **3 menit** | Cleanup |
| Repetisi | **3 kali** | Per skenario |
| Skenario | **4** | 01, 02, 05, 06 |
| **Total Waktu** | **~4.5 jam** | Semua eksperimen |

### 4 Skenario Eksperimen (yang dijalankan)
| # | Nama | Topologi | Deskripsi |
|---|------|----------|-----------|
| 01 | Baseline | 13 switches (hierarchical) | Normal operation |
| 02 | Lossy | 13 switches (hierarchical) | Packet loss (10% core, 5% edge) |
| 05 | Dual-Redundant | 17 switches (dual-redundant) | Full redundancy at all layers |
| 06 | Dist Failure | 17 switches (dual-redundant) | Distribution layer failure |

### Topologi yang Digunakan
1. **Topologi 1**: Hierarchical 3-tier (13 switches) - untuk skenario 01 & 02
2. **Topologi 2**: Dual-Redundant (17 switches) - untuk skenario 05 & 06

> **CATATAN**: Skenario 03 (Dual-Core) dan 04 (Core Failure) TIDAK dijalankan.

### Hasil Eksperimen Aktual

#### Skenario 01: Baseline (3 Run, Rata-rata)
| Metric | Anomaly (DSCP 46) | Normal (DSCP 0) |
|--------|-------------------|-----------------|
| Messages Received | 53,635 | 11,716 |
| Avg Delay (ms) | **228.60** | 237,399.55 |
| Min Delay (ms) | 0.88 | 1.04 |
| Max Delay (ms) | 387.06 | 474,332.52 |
| Std Dev Delay (ms) | 46.72 | 136,208.63 |
| Avg Jitter (ms) | 68.01 | 530.88 |
| Packet Loss (%) | **0.00** | 78.18 |

**Lokasi Data**: `/home/mqtt-sdn/results/01-baseline-13switches/`
- `run_2025-12-04_22-43-19/`
- `run_2025-12-04_23-13-55/`
- `run_2025-12-04_23-38-02/`

#### Skenario Lainnya (Menunggu Eksperimen)
- [ ] Skenario 02: Lossy Network
- [ ] Skenario 05: Dual-Redundant
- [ ] Skenario 06: Distribution Failure

### Hasil yang Diharapkan (dari CONTEXT.md)
```
ANOMALY (DSCP 46, High Priority):
  - Packet Loss: 0%
  - Avg Delay: ~200ms

NORMAL (DSCP 0, Best Effort):
  - Packet Loss: ~76%
  - Avg Delay: ~27,000ms (27 detik)
```

**Status**: Hasil aktual baseline sesuai ekspektasi (delay ~228ms, loss 0%).

### PENTING: Penekanan Congestion

> **KUNCI PENELITIAN**: DSCP-based priority HANYA relevan dan terlihat efeknya pada kondisi **CONGESTION**.

| Kondisi | Tanpa Priority | Dengan Priority (DSCP) |
|---------|----------------|------------------------|
| **Tanpa Congestion** | Semua traffic bagus | Semua traffic bagus (tidak ada perbedaan) |
| **Dengan Congestion** | Semua traffic degradasi sama | Anomaly terlindungi, Normal terdegradasi |

**Mengapa eksperimen menggunakan congestion 1.8x:**
- Load: 360 Kbps (18 publisher × 10 msg/s × ~200 bytes dengan overhead)
- Kapasitas link: 200 Kbps
- Rasio: 1.8x → **Sengaja dibuat congestion untuk membuktikan efektivitas priority**

**Yang harus ditekankan di paper:**
1. Priority mechanism adalah **congestion protection** - melindungi traffic penting saat jaringan overload
2. Tanpa congestion, semua traffic akan perform sama (priority tidak terlihat efeknya)
3. Hasil eksperimen (anomaly 228ms vs normal 237s) membuktikan priority bekerja **karena ada congestion**
4. Framework ini solusi untuk skenario real-world dimana IoT network sering mengalami burst traffic

---

## 3. STRUKTUR PAPER

### Sections yang Sudah Selesai
- [x] Abstract (perlu update dengan hasil konkret)
- [x] Introduction (Pendahuluan)
- [x] Related Work (dengan Table I perbandingan)
- [x] Methodology (lengkap dengan algoritma dan formula)
- [x] Results - Skenario 01 Baseline (data lengkap dari 3 run)
- [x] Discussion - Draft awal dengan analisis baseline
- [x] Conclusion - Draft awal

### Sections yang Perlu Dilengkapi
- [ ] Results - Skenario 02, 05, 06 (menunggu eksperimen)
- [ ] Discussion - Analisis perbandingan antar skenario
- [ ] Conclusion - Kesimpulan lengkap dan future work
- [ ] Abstract - Update dengan hasil konkret semua skenario

### Perbedaan paper_full vs paper_short
| Aspek | paper_full.tex | paper_short.tex |
|-------|----------------|-----------------|
| Target | Arsip lengkap | Conference submission |
| Halaman | 6 (tanpa Results) | 3 (tanpa Results) |
| Introduction | Detail, 5 paragraf + enumerate | Ringkas, 4 paragraf inline |
| Related Work | 6 subsection detail | 5 paragraf ringkas |
| Methodology | 11 subsection | 7 subsection |
| Algorithm | 2 algoritma terpisah | 1 algoritma gabungan |

---

## 4. ELEMEN PENTING

### Table I: Comparison of MQTT Priority Approaches
Tabel perbandingan 9 pendekatan (termasuk Proposed) dengan 8 kriteria:
- Layer, MQTT Compat., Network QoS, DPI Req., Scalability, Complexity, SDN

### Algorithm
**paper_full.tex**: 2 algoritma terpisah
1. Algorithm 1: DSCP Tagging at Publisher
2. Algorithm 2: Traffic Differentiation and Queue Assignment

**paper_short.tex**: 1 algoritma gabungan
- Algorithm 1: DSCP-based Traffic Prioritization (Publisher + Switch Side)
- Menampilkan Queue 1 (DSCP 46), Queue 2-4 (DSCP 34/26/10), Queue 5 (DSCP 0)

### Figures
1. Fig. 1: Arsitektur Sistem DSCP-Based QoS untuk MQTT
2. Fig. 2: Topologi Hierarchical 3-Tier (13 Switches)
3. Fig. 3: Topologi Dual-Core (14 Switches)

### Metrics dengan Formula

| Metric | Formula | Sumber Data |
|--------|---------|-------------|
| **Avg Delay** | `Σ(t_recv - t_sent) / n` | timestamp di JSON payload vs waktu terima |
| **Min/Max Delay** | `min(delays)` / `max(delays)` | nilai ekstrem dari semua delay |
| **Std Dev Delay** | `√(Σ(delay - avg)² / n)` | variabilitas delay |
| **Jitter** | `Σ|delay[i] - delay[i-1]| / (n-1)` | variasi delay antar message berturutan |
| **Packet Loss** | `(sent - recv) / sent × 100%` | seq number dari publisher log vs CSV |
| **Throughput** | `total_messages / duration` | jumlah message per detik |

**Catatan Penting:**
- Delay dihitung per-message dari `timestamp` di JSON payload
- Packet loss dihitung dari `max(publisher_log_count, seq_range)` untuk handle truncated logs
- Jitter dihitung per-device lalu di-aggregate (bukan across devices)

---

## 5. REFERENSI YANG DIGUNAKAN

```bibtex
[b1] PrioMQTT - Patti et al. (UDP-based, tidak kompatibel MQTT standar)
[b2] RT-MQTT - Shahri et al. (SDN + middleware, kompleks)
[b3] p-MQTT - Kim et al. (Broker-level priority)
[b4] Kim - Priority field di MQTT header
[b5] Tachibana - Polling-based priority
[b6] Akshatha - RabbitMQ/AMQP based
[b7] PrioMQTT+TSN - Testa et al. (TSN integration)
[b8] Yaseen - DSCP untuk flow continuity (bukan MQTT)
```

---

## 6. MENJALANKAN EKSPERIMEN

### Otomatis (Semua Skenario)
```bash
cd /home/mqtt-sdn
nohup sudo ./run_all_experiments.sh > experiment_master.log 2>&1 &
tail -f experiment_master.log  # Monitor progress
```

### Manual (Single Scenario)
```bash
cd /home/mqtt-sdn/scenarios/01-baseline-13switches
sudo ./run_experiment.sh 600  # 10 menit send
```

---

## 7. CARA COMPILE PAPER

```bash
cd /home/mqtt-sdn/docs/latex

# Compile paper_full
pdflatex -interaction=nonstopmode paper_full.tex
pdflatex -interaction=nonstopmode paper_full.tex  # 2x untuk references

# Compile paper_short
pdflatex -interaction=nonstopmode paper_short.tex
pdflatex -interaction=nonstopmode paper_short.tex
```

### LaTeX Packages yang Digunakan
- IEEEtran (document class)
- cite, amsmath, amssymb, amsfonts
- algorithmic, algorithm
- graphicx, textcomp, xcolor
- booktabs, multirow, array

---

## 8. CHECKLIST SEBELUM SUBMIT

### Konsistensi Parameter
- [ ] Bandwidth = 0.2 Mbps (bukan 0.5 Mbps)
- [ ] Msg Rate = 10 msg/s (bukan 50 msg/s)
- [ ] Duration = 10 menit send + 10 menit drain
- [ ] Skenario = 4 (01, 02, 05, 06)
- [ ] Congestion = ~1.8x
- [ ] Failure Time (skenario 06) = menit ke-4 (40% durasi)

### Kelengkapan Konten
- [ ] Abstract dengan hasil konkret
- [ ] Results section dengan data eksperimen
- [ ] Discussion section
- [ ] Conclusion section

### Format IEEE
- [ ] Halaman maksimal sesuai conference requirement
- [ ] Semua gambar dan tabel ter-reference
- [ ] Bibliography lengkap

---

## 9. CATATAN PENTING

1. **Sumber Kebenaran**: `/home/mqtt-sdn/CONTEXT.md` adalah sumber utama parameter eksperimen. Jika ada konflik, ikuti CONTEXT.md.

2. **Draft Asli**: File draft ada di `/home/mqtt-sdn/docs/`:
   - draft_pendahuluan.txt
   - draft_related-work.txt
   - draft_methodology.txt
   
   Draft ini mungkin outdated, selalu cross-check dengan CONTEXT.md.

3. **Bahasa**: Paper ditulis dalam Bahasa Indonesia (bisa diterjemahkan ke English jika conference membutuhkan).

4. **Versi Ringkas**: paper_short.tex dirancang untuk IEEE conference 6-7 halaman. Setelah Results/Discussion/Conclusion ditambahkan, pastikan tidak melebihi limit.

---

**Last Updated**: 2025-12-05
