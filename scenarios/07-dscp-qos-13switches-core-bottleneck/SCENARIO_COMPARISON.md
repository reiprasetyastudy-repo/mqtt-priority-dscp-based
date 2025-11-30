# Perbandingan Scenario 06 vs Scenario 07

## Ringkasan Perbedaan

| Aspek | Scenario 06 | Scenario 07 |
|-------|-------------|-------------|
| **Topologi** | 13 switches hierarchical | 13 switches hierarchical (sama) |
| **Jumlah Host** | 19 (1 broker + 18 publishers) | 19 (1 broker + 18 publishers) |
| **QoS Method** | DSCP (5 priority levels) | DSCP (5 priority levels) |
| **Bandwidth Core (s1)** | 0.5 Mbps | **0.5 Mbps** ✅ |
| **Bandwidth Aggregation** | 0.5 Mbps | **10 Mbps** ⬆️ |
| **Bandwidth Edge** | 0.5 Mbps | **10 Mbps** ⬆️ |
| **Bandwidth Host-Edge** | 0.5 Mbps | **10 Mbps** ⬆️ |
| **Bottleneck Location** | Semua link | **Hanya di core** 🎯 |
| **Core Utilization** | 216% (congested) | 216% (congested) |
| **Edge Utilization** | 216% (congested) | **10.8%** (no congestion) |

## Visualisasi Bandwidth

### Scenario 06 (Uniform Bandwidth Limit)
```
                    ┌──────┐
                    │  s1  │ CORE
                    └───┬──┘
                   0.5 Mbps (216%)
          ┌─────────────┼─────────────┐
          │             │             │
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │     │  s3   │     │  s4   │  AGGREGATION
      └───┬───┘     └───┬───┘     └───┬───┘
     0.5 Mbps    0.5 Mbps    0.5 Mbps
      (216%)      (216%)      (216%)
         ↓           ↓           ↓
     Edge (s5-s13) - 0.5 Mbps each (216%)
         ↓
    Publishers - 0.5 Mbps each (216%)

❌ Congestion di SEMUA layer!
```

### Scenario 07 (Core Bottleneck)
```
                    ┌──────┐
                    │  s1  │ CORE
                    └───┬──┘
                   0.5 Mbps (216%) 🔴 BOTTLENECK
          ┌─────────────┼─────────────┐
          │             │             │
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │     │  s3   │     │  s4   │  AGGREGATION
      └───┬───┘     └───┬───┘     └───┬───┘
      10 Mbps      10 Mbps      10 Mbps
      (10.8%)      (10.8%)      (10.8%)
         ↓           ↓           ↓
     Edge (s5-s13) - 10 Mbps each (10.8%)
         ↓
    Publishers - 10 Mbps each (10.8%)

✅ Congestion HANYA di core! Edge network lancar.
```

## Alasan Scenario 07 Lebih Realistis

### 1. **Enterprise Network Reality**
- **Office Building:** Edge switches (per-floor) biasanya 1 Gbps
- **Internet Gateway:** Uplink ke internet hanya 100 Mbps
- **Result:** Bottleneck di gateway/core, bukan di edge

### 2. **IoT Cloud Architecture**
- **Local Network:** Sensor ke gateway = fast (WiFi 54 Mbps)
- **Cloud Uplink:** Gateway ke cloud = limited (4G: 10-50 Mbps)
- **Result:** Prioritization penting di uplink, bukan di local

### 3. **Smart Building Deployment**
- **Floor 1-3:** Masing-masing punya 1 Gbps switch
- **Building Gateway:** Koneksi ke NOC hanya 10 Mbps
- **Result:** Traffic dari 3 lantai compete di gateway

## Kapan Menggunakan Masing-Masing?

### Gunakan Scenario 06 Jika:
- Testing extreme congestion di semua layer
- Ingin melihat impact QoS di every hop
- Simulating poor network infrastructure
- Academic research tentang multi-layer QoS

### Gunakan Scenario 07 Jika: ✅ (Recommended)
- Simulating realistic enterprise network
- Testing backbone/gateway bottleneck
- IoT cloud connectivity scenario
- Real-world deployment planning

## Load Calculation

### Total Traffic Generated
- **Publishers:** 18 devices
- **Message Rate:** 50 msg/s per publisher
- **Message Size:** ~150 bytes (JSON payload)
- **Total Traffic:** 18 × 50 × 150 × 8 = 1,080,000 bps = **1.08 Mbps**

### Utilization per Layer

#### Scenario 06
```
Core:        1.08 Mbps / 0.5 Mbps  = 216% ❌
Aggregation: 1.08 Mbps / 0.5 Mbps  = 216% ❌
Edge:        1.08 Mbps / 0.5 Mbps  = 216% ❌
```

#### Scenario 07
```
Core:        1.08 Mbps / 0.5 Mbps  = 216% ❌ BOTTLENECK HERE!
Aggregation: 1.08 Mbps / 10 Mbps   = 10.8% ✅
Edge:        1.08 Mbps / 10 Mbps   = 10.8% ✅
```

## Expected Results

### Scenario 06
- Delay akan tinggi di **semua hop**
- DSCP priority akan terlihat di **setiap layer**
- Packet loss bisa terjadi di **multiple points**

### Scenario 07
- Delay akan tinggi **hanya di core**
- DSCP priority **paling terlihat di core switch**
- Edge network akan smooth, bottleneck jelas di core
- **Lebih mudah menganalisa** karena bottleneck terlokalisir

## Cara Menjalankan

### Scenario 06
```bash
cd /home/mqtt-sdn/scenarios/06-dscp-qos-13switches
sudo ./run_experiment.sh 300
```

### Scenario 07
```bash
cd /home/mqtt-sdn/scenarios/07-dscp-qos-13switches-core-bottleneck
sudo ./run_experiment.sh 300
```

## Kesimpulan

**Scenario 07 adalah pilihan yang lebih baik untuk:**
1. ✅ Realistic network simulation
2. ✅ Enterprise/IoT deployment planning
3. ✅ Clear bottleneck identification
4. ✅ Easier result analysis

**Scenario 06 tetap berguna untuk:**
1. Academic research
2. Extreme stress testing
3. Multi-layer QoS validation
4. Worst-case scenario analysis

---

**Rekomendasi:** Gunakan **Scenario 07** untuk penelitian yang ingin mensimulasikan real-world network dengan backbone bottleneck. 🎯
