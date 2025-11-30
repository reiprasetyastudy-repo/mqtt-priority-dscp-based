# 📚 Dokumentasi Research - MQTT-SDN Project

Koleksi dokumentasi untuk penelitian dan pengembangan sistem MQTT-SDN

---

## 📂 Daftar Dokumentasi

### 1. **Filtering Methods Comparison** 📋
**File:** [`filtering_methods_comparison.md`](filtering_methods_comparison.md)

**Isi:**
- Perbandingan 7 metode filtering/prioritas traffic
- Pro & Cons masing-masing metode
- Complexity & Scalability analysis
- **Research Novelty** ranking untuk thesis/paper
- Implementasi detail untuk setiap metode

**Use Case:**
- Memilih metode prioritas yang tepat untuk sistem kompleks
- Evaluasi trade-off antar metode
- Menentukan approach untuk penelitian

**Key Highlights:**
- ⭐⭐⭐⭐⭐ **DPI (MQTT Topic/Payload)** - High novelty, content-aware
- ⭐⭐⭐⭐⭐ **Hybrid (Subnet + DPI)** - Best architecture untuk research
- ⭐⭐⭐⭐⭐ **Subnet-Based** - Production-ready, scalable

---

### 2. **Metrics Measurement** 📊
**File:** [`metrics_measurement.md`](metrics_measurement.md)

**Isi:**
- **5 metrik utama** yang bisa diukur:
  1. End-to-End Delay ✅ (sudah ada)
  2. Jitter ✅ (IMPLEMENTED!)
  3. Response Time ⭐ (perlu implementasi)
  4. Total Time ✅ (sudah bisa)
  5. Lost Message / Packet Loss ✅ (IMPLEMENTED!)
  6. Throughput ✅ (bonus)

- Implementasi code untuk setiap metrik
- Script analisis data comprehensive
- Visualisasi (histogram, box plot, CDF, time series)

**Use Case:**
- Evaluasi performa sistem
- Membandingkan hasil simulasi berbeda
- Membuat tabel/grafik untuk paper

**Key Tools:**
- `subscriber_enhanced.py` - Collect all metrics
- `analyze_metrics.py` - Comprehensive analysis
- Auto-generate plots untuk paper

---

## 🎯 Quick Navigation

### Untuk Memilih Metode Prioritas
→ Baca: [`filtering_methods_comparison.md`](filtering_methods_comparison.md)
- Section "Perbandingan & Rekomendasi"
- Section "Novelty untuk Penelitian"

### Untuk Mengukur Performa
→ Baca: [`metrics_measurement.md`](metrics_measurement.md)
- Section "End-to-End Delay" (sudah implemented)
- Section "Implementasi Pengukuran" (enhanced subscriber)
- Section "Analisis Data" (analysis script)

### Untuk Research Paper
→ Baca kedua dokumen:
1. **Filtering Methods** - pilih metode dengan novelty tinggi
2. **Metrics** - tentukan metrik evaluasi yang tepat

---

## 📖 Recommended Reading Order

### **Tahap 1: Pahami Current State**
1. Baca `/home/mqtt-sdn/DOKUMENTASI_SIMULASI.md` (sistem saat ini)
2. Baca `metrics_measurement.md` Section 1 (End-to-End Delay) - yang sudah ada

### **Tahap 2: Explore Future Options**
3. Baca `filtering_methods_comparison.md` - semua opsi metode
4. Tentukan metode mana yang cocok untuk tujuan kamu

### **Tahap 3: Plan Metrics**
5. Baca `metrics_measurement.md` - semua metrik yang bisa diukur
6. Pilih metrik mana yang relevan untuk research kamu

### **Tahap 4: Implementation**
7. Gunakan code example dari dokumentasi
8. Modify sesuai kebutuhan

---

## 💡 Quick Answers

### "Metode filtering mana yang paling scalable?"
→ **Subnet-Based** atau **VLAN-Based**
- 1 flow rule untuk ratusan device
- Production-ready

### "Metode mana yang novelty tinggi untuk paper?"
→ **DPI (MQTT Topic/Payload)** atau **Hybrid**
- Content-aware classification
- High research value
- Jarang ada di literatur

### "Metrik apa yang harus diukur untuk paper?"
→ **Essential:**
- End-to-End Delay (mean, min, max, std)
- Jitter (stability)
- Packet Loss Rate (reliability)
- Throughput

### "Bagaimana cara mengukur semua metrik sekaligus?"
→ Gunakan **subscriber_enhanced.py** dari `metrics_measurement.md`
- Automatic logging
- Real-time calculation
- Summary report saat selesai

---

## 🔧 Tools & Scripts

### Available Scripts (from documentation)

**1. Enhanced Subscriber** (`metrics_measurement.md`)
```python
# subscriber_enhanced.py
# Collect: delay, jitter, sequence numbers, throughput
```

**2. Analysis Script** (`metrics_measurement.md`)
```python
# analyze_metrics.py
# Analyze: statistical test, visualization, report generation
```

**3. Implementation Examples**
- Port-based filtering (simple)
- Subnet-based filtering (scalable)
- DPI implementation (advanced)
- Hybrid approach (sophisticated)

All available in respective documentation files.

---

## 📈 Research Workflow Example

### **Scenario: Thesis tentang SDN-QoS untuk IoT**

**Step 1: Define Problem**
- Problem: Device IoT banyak, perlu prioritas critical data
- Current: IP-based (tidak scalable)

**Step 2: Choose Method** (from `filtering_methods_comparison.md`)
- **Baseline:** IP-based (Chapter 1)
- **Improvement 1:** Subnet-based (Chapter 2)
- **Improvement 2:** DPI dengan MQTT Topic (Chapter 3) ← Main contribution

**Step 3: Define Metrics** (from `metrics_measurement.md`)
- End-to-End Delay
- Jitter
- Packet Loss
- Throughput

**Step 4: Implement**
- Use code examples dari dokumentasi
- Modify publisher untuk sequence number
- Use enhanced subscriber

**Step 5: Run Experiments**
```bash
# Baseline
sudo ./run_sdn_mqtt.sh 5m  # 5 minutes

# With improvements
# (after modify controller)
sudo ./run_sdn_mqtt.sh 5m
```

**Step 6: Analyze**
```bash
python3 analyze_metrics.py
```

**Step 7: Write Paper**
- Use comparison table dari dokumentasi
- Use plots generated by analysis script
- Show improvement percentage

---

### 3. **Lost Message Measurement** 📉 (NEW!)
**File:** [`lost_message_measurement.md`](lost_message_measurement.md)

**Isi:**
- ✅ Implementasi packet loss tracking dengan sequence number
- ✅ Enhanced subscriber (`subscriber_enhanced.py`)
- ✅ Real-time metrics display
- ✅ Comprehensive summary report
- ✅ **Ready to use** - sudah terintegrasi di `run_sdn_mqtt.sh`

**Use Case:**
- Measure packet loss rate
- Verify SDN reliability
- Get complete metrics for paper

**Quick Start:**
```bash
sudo ./run_sdn_mqtt.sh 60
# Ctrl+C to see full summary with packet loss stats
```

---

## 🆕 Future Documentation (Planned)

- [ ] **Implementation Guide: DPI Method**
- [ ] **Implementation Guide: Hybrid Approach**
- [ ] **Performance Tuning Guide**
- [ ] **Scalability Testing Guide**
- [ ] **Integration with Real IoT Devices**

---

## 📞 How to Use This Documentation

### For Developers
- Read implementation examples
- Copy-paste code snippets
- Modify for your use case

### For Researchers
- Read comparison & novelty sections
- Choose appropriate methods/metrics
- Use analysis scripts for data processing

### For Students (Thesis/TA)
- Follow research workflow example
- Use as reference for literature review
- Cite implementation details

---

## 📝 Contributing

Jika ada metode baru atau metrik tambahan yang ingin didokumentasikan:
1. Buat file baru di folder `/docs`
2. Update README ini
3. Ikuti format yang konsisten (problem, solution, implementation, evaluation)

---

## 📚 Related Documentation

- [`/home/mqtt-sdn/README.md`](../README.md) - Quick start guide
- [`/home/mqtt-sdn/DOKUMENTASI_SIMULASI.md`](../DOKUMENTASI_SIMULASI.md) - Tutorial lengkap
- [`/home/mqtt-sdn/CLAUDE.md`](../CLAUDE.md) - Technical reference

---

**Maintained by:** MQTT-SDN Research Project
**Last Updated:** 2025-11-09
**Version:** 1.0
