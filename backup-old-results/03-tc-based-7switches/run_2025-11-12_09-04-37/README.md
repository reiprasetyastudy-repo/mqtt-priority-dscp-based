# Dokumentasi Simulasi Prioritas Data IoT menggunakan SDN

## Ringkasan Hasil Simulasi

**Tanggal Simulasi:** 12 November 2025, 09:04:37

**Hasil:** ✅ **SUKSES - Mekanisme Prioritas Bekerja!**

- **Data Anomaly (Prioritas Tinggi):** Delay rata-rata 12.32 ms
- **Data Normal (Prioritas Rendah):** Delay rata-rata 68.78 ms
- **Perbedaan:** Data normal **5.6x lebih lambat** dari data anomaly

Ini membuktikan bahwa sistem SDN berhasil memprioritaskan data anomaly/kritis dibanding data normal pada kondisi jaringan yang penuh (congestion).

---

## Apa yang Disimulasikan?

Simulasi ini menguji sistem **Software Defined Networking (SDN)** untuk memprioritaskan data IoT berdasarkan tingkat kepentingannya:

### Skenario:
Bayangkan sebuah gedung 2 lantai dengan sensor IoT di setiap ruangan:
- **Sensor Anomaly:** Mendeteksi hal penting (kebakaran, intrusi, gas berbahaya) → **HARUS CEPAT SAMPAI**
- **Sensor Normal:** Mengukur suhu/kelembaban biasa → Boleh sedikit tertunda

Ketika jaringan penuh (banyak data), sistem SDN memastikan data anomaly tetap cepat sampai ke server pusat.

---

## File-File Penting dalam Folder Ini

```
run_2025-11-12_09-04-37/
├── README.md                  ← File ini (penjelasan umum)
├── TOPOLOGI.md                ← Penjelasan topologi jaringan
├── CARA_KERJA.md              ← Cara kerja sistem prioritas
├── HASIL_SIMULASI.md          ← Analisis detail hasil
├── metrics_summary.txt        ← Ringkasan metrik (delay, jitter, loss)
├── mqtt_metrics_log.csv       ← Data mentah semua pesan
└── topology.log               ← Log jalannya simulasi
```

---

## Cara Membaca Dokumentasi

**Untuk pemahaman bertahap, baca dalam urutan ini:**

1. **README.md** (file ini) - Overview dan hasil simulasi
2. **TOPOLOGI.md** - Lihat struktur jaringan dan komponen
3. **CARA_KERJA.md** - Pahami bagaimana sistem prioritas bekerja
4. **HASIL_SIMULASI.md** - Analisis detail hasil eksperimen

---

## Spesifikasi Simulasi

### Topologi Jaringan
- **Tipe:** Hierarchical 3-layer (Core - Aggregation - Edge)
- **Jumlah Switch:** 7 switch (1 core + 2 aggregation + 4 edge)
- **Jumlah Sensor:** 8 sensor (4 anomaly + 4 normal)
- **Bandwidth:** 1 Mbps per link
- **Utilization:** 80% (kondisi congestion)

### Durasi dan Traffic
- **Durasi Simulasi:** 301.94 detik (~5 menit)
- **Total Pesan:** 60,361 pesan
- **Throughput:** 199.91 pesan/detik
- **Message Rate:** 50 pesan/detik per sensor

### Konfigurasi Prioritas
- **Queue 1 (Anomaly):** 70-100% bandwidth (prioritas tinggi)
- **Queue 2 (Normal):** 30-50% bandwidth (prioritas rendah)

---

## Kesimpulan

Simulasi ini **berhasil membuktikan** bahwa:

1. ✅ SDN dapat membedakan data berdasarkan tingkat kepentingan
2. ✅ Data anomaly mendapat delay **82% lebih rendah** (12.32ms vs 68.78ms)
3. ✅ Mekanisme prioritas **hanya bekerja saat jaringan penuh** (80%+ utilization)
4. ✅ Tidak ada packet loss (0%) untuk kedua jenis traffic

**Implikasi Praktis:**
Sistem ini cocok untuk aplikasi IoT kritis seperti:
- Smart building dengan sensor kebakaran/keamanan
- Smart hospital dengan monitoring pasien kritis
- Smart city dengan deteksi anomaly lingkungan

---

## Teknologi yang Digunakan

- **Ryu Framework:** SDN controller (pengatur lalu lintas jaringan)
- **Mininet:** Emulator jaringan untuk simulasi
- **Open vSwitch:** Software switch dengan dukungan OpenFlow
- **MQTT:** Protocol komunikasi IoT (lightweight messaging)
- **OpenFlow 1.3:** Protocol antara controller dan switch

---

## Penulis & Referensi

Untuk detail teknis lebih lanjut, lihat:
- `TOPOLOGI.md` - Diagram dan penjelasan struktur jaringan
- `CARA_KERJA.md` - Alur kerja sistem prioritas step-by-step
- `HASIL_SIMULASI.md` - Analisis statistik dan grafik hasil

---

**Catatan:** Dokumentasi ini dibuat untuk memudahkan pemahaman bagi pembaca non-teknis. Untuk detail implementasi teknis, lihat source code di `/home/mqtt-sdn/scenarios/03-tc-based-7switches/`.
