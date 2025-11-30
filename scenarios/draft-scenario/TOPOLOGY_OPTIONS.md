# Draft Topology Options for Scenario 09+

Dokumen ini berisi draft topology untuk penelitian DSCP-based QoS pada MQTT dengan SDN. Topology dirancang untuk menunjukkan **skalabilitas** dan **efektivitas** framework pada deployment yang lebih kompleks dari Scenario 06.

---

## OPSI 1: Multi-Building Campus Network (Wide & Distributed)

### **Use Case:** Smart Campus IoT dengan Multiple Buildings

**Karakteristik:**
- ✅ **40 switches** - Menunjukkan skalabilitas horizontal
- ✅ **4-tier hierarchy** - Core → Building → Floor → Room
- ✅ **54 publishers** (3x dari Scenario 06)
- ✅ **Multiple congestion points** di berbagai layer
- ✅ **Realistic bandwidth allocation** per layer
- ✅ **Subnet-based classification** untuk 9 zones

### **Topology Structure:**

```
                            ┌──────────┐
                            │    s1    │ CORE LAYER
                            │  (Core)  │ Campus Gateway
                            │  Broker  │ 10.0.0.1
                            └────┬─────┘
                                 │ 10 Mbps
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
    ┌───▼───┐                ┌───▼───┐              ┌───▼───┐
    │  s2   │                │  s3   │              │  s4   │   AGGREGATION LAYER
    │Build 1│ 5 Mbps         │Build 2│ 5 Mbps       │Build 3│   Building Switches
    └───┬───┘                └───┬───┘              └───┬───┘
        │                        │                        │
   ┌────┼────┐              ┌────┼────┐              ┌────┼────┐
   │    │    │              │    │    │              │    │    │
  s5   s6   s7             s8   s9  s10            s11  s12  s13  DISTRIBUTION LAYER
Floor1 F2  F3            Floor1 F2  F3            Floor1 F2  F3   Floor Switches
 2Mbps 2M  2M             2Mbps 2M  2M             2Mbps 2M  2M
   │    │    │              │    │    │              │    │    │
┌──┼──┬─┼─┬──┼──┐      ┌──┼──┬─┼─┬──┼──┐      ┌──┼──┬─┼─┬──┼──┐
│  │  │ │ │  │  │      │  │  │ │ │  │  │      │  │  │ │ │  │  │
s14 s15 s16 s17 s18...  s23 s24 s25 s26 s27...  s32 s33 s34 s35 s36...  ACCESS LAYER
R1  R2  R3  R1  R2...   R1  R2  R3  R1  R2...   R1  R2  R3  R1  R2...   Room/Zone Switches
1M  1M  1M  1M  1M...   1M  1M  1M  1M  1M...   1M  1M  1M  1M  1M...
│   │   │   │   │       │   │   │   │   │       │   │   │   │   │
2IoT 2IoT...            2IoT 2IoT...            2IoT 2IoT...
(A+N)                   (A+N)                   (A+N)

A = Anomaly Publisher (DSCP 46)
N = Normal Publisher (DSCP 0)
```

### **Network Details:**

| Component | Count | Description |
|-----------|-------|-------------|
| **Switches Total** | 40 | 1 core + 3 building + 9 floor + 27 room |
| **Publishers** | 54 | 2 per room (1 anomaly + 1 normal) |
| **Hosts Total** | 56 | 54 publishers + 1 broker + 1 subscriber |
| **Max Hops** | 4 | IoT → Room → Floor → Building → Core |
| **Subnets** | 9 | 3 buildings × 3 floors |
| **Total Traffic** | 3.24 Mbps | 54 publishers × 60 Kbps |

### **Bandwidth Configuration:**

```
Layer                          Bandwidth    Total Load    Utilization
───────────────────────────────────────────────────────────────────────
Core ↔ Aggregation (3 links)   10 Mbps      3.24 Mbps     32.4%
Aggregation ↔ Distribution     5 Mbps       1.08 Mbps     21.6%
Distribution ↔ Access          2 Mbps       0.36 Mbps     18%
Access ↔ IoT Devices           1 Mbps       0.12 Mbps     12%
```

**Notes:**
- Core tidak congested (32% utilization) - bottleneck di access layer
- Access layer paling congested (realistic untuk IoT edge)
- Gradual bandwidth reduction sesuai hierarchy

### **Subnet Allocation:**

```
Core/Broker:     10.0.0.1/16

Building 1:
  Floor 1:       10.0.11.x/24  (s14, s15, s16 - 6 publishers)
  Floor 2:       10.0.12.x/24  (s17, s18, s19 - 6 publishers)
  Floor 3:       10.0.13.x/24  (s20, s21, s22 - 6 publishers)

Building 2:
  Floor 1:       10.0.21.x/24  (s23, s24, s25 - 6 publishers)
  Floor 2:       10.0.22.x/24  (s26, s27, s28 - 6 publishers)
  Floor 3:       10.0.23.x/24  (s29, s30, s31 - 6 publishers)

Building 3:
  Floor 1:       10.0.31.x/24  (s32, s33, s34 - 6 publishers)
  Floor 2:       10.0.32.x/24  (s35, s36, s37 - 6 publishers)
  Floor 3:       10.0.33.x/24  (s38, s39, s40 - 6 publishers)
```

### **Expected Results:**

| Metric | Scenario 06 | **Opsi 1** | Improvement |
|--------|-------------|------------|-------------|
| Switches | 13 | **40** | 3.1x |
| Publishers | 18 | **54** | 3x |
| Max Hops | 3 | **4** | +33% |
| Avg Delay (DSCP 46) | 1-5 ms | **3-10 ms** | Scalable |
| Avg Delay (DSCP 0) | 1000+ ms | **800+ ms** | Less congestion |
| Total Messages (10min) | ~180k | **~540k** | 3x data |
| Skalabilitas | Good | **Excellent** | Wide network |

**Keunggulan:**
- ✅ Menunjukkan skalabilitas **horizontal** (wide network)
- ✅ Realistic campus/enterprise deployment
- ✅ Multiple congestion points untuk testing
- ✅ Clear subnet hierarchy untuk DSCP classification

---

## OPSI 2: Deep Hierarchical Network (Long Path & High Latency)

### **Use Case:** Hierarchical Industrial IoT atau Multi-Tier Data Center

**Karakteristik:**
- ✅ **7-tier hierarchy** - Menunjukkan skalabilitas vertikal
- ✅ **Deep forwarding path** (8-9 hops)
- ✅ **Cumulative latency test** - QoS effectiveness pada path panjang
- ✅ **Gradual bandwidth reduction** - Bottleneck cascade
- ✅ **30-40 switches** tergantung fan-out

### **Topology Structure (Linear Hierarchy):**

```
LAYER 1: CORE
┌────────────────────────────────────────┐
│            s1 (Core)                   │  Bandwidth: 20 Mbps
│         Broker: 10.0.0.1               │  Congestion: Low (16%)
└──────────────────┬─────────────────────┘
                   │ 20 Mbps
                   ▼
LAYER 2: AGGREGATION (Inter-Region)
┌──────────────────┴─────────────────────┐
│     s2               s3                │  Bandwidth: 10 Mbps
│  Region 1         Region 2             │  Congestion: Low (32%)
└─────┬──────────────────┬───────────────┘
      │ 10M              │ 10M
      ▼                  ▼
LAYER 3: DISTRIBUTION (Zone)
┌─────┴──────┐     ┌─────┴──────┐
│ s4      s5 │     │ s6      s7 │         Bandwidth: 5 Mbps
│Zone1  Zone2│     │Zone3  Zone4│         Congestion: Moderate (64%)
└──┬────┬────┘     └──┬────┬────┘
   │5M  │5M          │5M  │5M
   ▼    ▼            ▼    ▼
LAYER 4: ACCESS (Cluster)
┌──┴─┬──┴─┐      ┌──┴─┬──┴─┐
│s8  │s9  │...   │s14 │s15 │...        Bandwidth: 2 Mbps
│Cl1 │Cl2 │      │Cl7 │Cl8 │           Congestion: High (150%)
└─┬──┴─┬──┘      └─┬──┴─┬──┘
  │2M  │2M         │2M  │2M
  ▼    ▼           ▼    ▼
LAYER 5: EDGE (Section)
┌─┴─┬──┴─┐      ┌─┴─┬──┴─┐
│s16│s17 │...   │s28│s29 │...          Bandwidth: 1 Mbps
│Sc1│Sc2 │      │Sc13 Sc14             Congestion: Very High (180%)
└─┬─┴──┬─┘      └─┬─┴──┬─┘
  │1M  │1M        │1M  │1M
  ▼    ▼          ▼    ▼
LAYER 6: AGGREGATION-EDGE (Sub-Section)
┌─┴─┬──┴─┐      ┌─┴─┬──┴─┐
│s30│s31 │...   │s58│s59 │...          Bandwidth: 0.5 Mbps
└─┬─┴──┬─┘      └─┬─┴──┬─┘             Congestion: Extreme (240%)
  │0.5M│0.5M      │0.5M│0.5M
  ▼    ▼          ▼    ▼
LAYER 7: DEVICE EDGE (Endpoint)
┌─┴─┬──┴─┐      ┌─┴─┬──┴─┐
│s60│s61 │...   │sX │sY  │...          Bandwidth: 0.3 Mbps
└─┬─┴──┬─┘      └─┬─┴──┬─┘             Congestion: Critical (300%)
  │    │          │    │
  IoT  IoT        IoT  IoT
 (2dev)(2dev)    (2dev)(2dev)

Total Path: IoT → s60 → s30 → s16 → s8 → s4 → s2 → s1 (8 hops)
```

### **Simplified View (Fanout 2 per Layer):**

```
Layer 1: Core                1 switch   (s1)
Layer 2: Aggregation         2 switches (s2-s3)
Layer 3: Distribution        4 switches (s4-s7)
Layer 4: Access              8 switches (s8-s15)
Layer 5: Edge               16 switches (s16-s31)
Layer 6: Aggregation-Edge   32 switches (s32-s63)  ← TOO MANY!
Layer 7: Device Edge        64 switches (s64-...)  ← TOO MANY!
```

**Problem:** Fanout 2 menghasilkan 127 switches (terlalu banyak!)

### **Optimized: Linear Chain (1 fanout per layer):**

```
Layer 1: Core            s1  ────┐
Layer 2: Aggregation     s2  ────┤  20 Mbps
Layer 3: Distribution    s3  ────┤  10 Mbps
Layer 4: Access          s4  ────┤   5 Mbps
Layer 5: Edge            s5  ────┤   2 Mbps
Layer 6: Agg-Edge        s6  ────┤   1 Mbps
Layer 7: Device-Edge     s7  ────┤   0.5 Mbps
Layer 8: Endpoint        s8  ────┘   0.3 Mbps
                          │
                        18 IoT
                    (9A + 9N)

Total: 8 switches, 18 publishers
Max Hops: 8 (very deep!)
```

**Problem:** Hanya 18 publishers (sama dengan Scenario 06)

### **Balanced Design: Hybrid Deep Network (4-5 branches per layer):**

```
                    s1 (Core - Broker)
                    │  20 Mbps
        ┌───────────┼───────────┐
        │           │           │
       s2          s3          s4     (Aggregation - 3 switches) 10 Mbps
        │           │           │
    ┌───┼───┐   ┌───┼───┐   ┌───┼───┐
   s5  s6  s7  s8  s9 s10 s11 s12 s13  (Distribution - 9 switches) 5 Mbps
    │   │   │   │   │   │   │   │   │
   s14 s15 s16 s17 s18 s19 s20 s21 s22 (Access - 9 switches) 2 Mbps
    │   │   │   │   │   │   │   │   │
   s23 s24 s25 s26 s27 s28 s29 s30 s31 (Edge - 9 switches) 1 Mbps
    │   │   │   │   │   │   │   │   │
   s32 s33 s34 s35 s36 s37 s38 s39 s40 (Device-Edge - 9 switches) 0.5 Mbps
    │   │   │   │   │   │   │   │   │
  2IoT 2IoT... (18 publishers per edge switch = 18×9 = 162 publishers!!!)

Total: 40 switches (1+3+9+9+9+9), 162 publishers
Max Hops: 6 (Deep enough!)
```

**Problem:** 162 publishers terlalu banyak! (9x Scenario 06)

### **FINAL OPTIMIZED: Deep Network with Moderate Scale:**

```
                        s1 (Core - Broker)
                        │  10 Mbps
              ┌─────────┼─────────┐
              │         │         │
             s2        s3        s4     (Aggregation - 3 switches) 5 Mbps
              │         │         │
          ┌───┼───┐ ┌───┼───┐ ┌───┼───┐
         s5  s6  s7 s8  s9 s10 s11 s12 s13  (Distribution - 9 switches) 2 Mbps
          │   │   │  │   │   │   │   │   │
         s14 s15 s16 s17 s18 s19 s20 s21 s22 (Access - 9 switches) 1 Mbps
          │   │   │  │   │   │   │   │   │
         s23 s24 s25 s26 s27 s28 s29 s30 s31 (Edge - 9 switches) 0.5 Mbps
          │   │   │  │   │   │   │   │   │
         2IoT...    2IoT...    2IoT...         (2 per edge = 18 publishers)

Total: 31 switches (1+3+9+9+9), 18 publishers
Max Hops: 6 (s23 → s14 → s5 → s2 → s1)
Path: IoT → Edge → Access → Distribution → Aggregation → Core
```

### **Network Details (Opsi 2 - Final):**

| Component | Count | Description |
|-----------|-------|-------------|
| **Switches Total** | 31 | 1 core + 3 agg + 9 dist + 9 access + 9 edge |
| **Publishers** | 18 | 2 per edge zone (1 anomaly + 1 normal) |
| **Hosts Total** | 20 | 18 publishers + 1 broker + 1 subscriber |
| **Max Hops** | **6** | Very deep forwarding path |
| **Layers** | **6** | Core → Agg → Dist → Access → Edge → IoT |
| **Total Traffic** | 1.08 Mbps | 18 publishers × 60 Kbps |

### **Bandwidth Configuration:**

```
Layer                              Bandwidth    Total Load    Utilization
─────────────────────────────────────────────────────────────────────────────
Core ↔ Aggregation (3 links)       10 Mbps      1.08 Mbps     10.8%
Aggregation ↔ Distribution         5 Mbps       0.36 Mbps     7.2%
Distribution ↔ Access              2 Mbps       0.12 Mbps     6%
Access ↔ Edge                      1 Mbps       0.12 Mbps     12%
Edge ↔ IoT Devices                 0.5 Mbps     0.12 Mbps     24%

BOTTLENECK: Edge layer (24% utilization, tapi bisa dinaikkan ke 240%!)
```

**Adjustment untuk Congestion:**
- Reduce edge bandwidth to **0.05 Mbps** → 240% utilization (extreme congestion!)
- Keep core at 10 Mbps → low utilization
- **Test QoS effectiveness pada deep path dengan extreme congestion di edge**

### **Expected Results:**

| Metric | Scenario 06 | **Opsi 2** | Key Difference |
|--------|-------------|------------|----------------|
| Switches | 13 | **31** | 2.4x |
| Publishers | 18 | **18** | Same (fair comparison) |
| Max Hops | 3 | **6** | **2x deeper!** |
| Avg Delay (DSCP 46) | 1-5 ms | **5-20 ms** | Cumulative latency |
| Avg Delay (DSCP 0) | 1000+ ms | **3000+ ms** | Much worse |
| Delay Difference | 200x | **150-200x** | QoS still effective! |
| Edge Congestion | N/A | **240%** | Extreme test |

**Keunggulan:**
- ✅ Menunjukkan skalabilitas **vertikal** (deep hierarchy)
- ✅ Test QoS effectiveness pada **long forwarding paths**
- ✅ Extreme congestion di edge layer
- ✅ Cumulative latency dari multi-hop
- ✅ Industrial/data center realistic deployment

---

## COMPARISON: Opsi 1 vs Opsi 2

| Feature | **Opsi 1: Wide Network** | **Opsi 2: Deep Network** |
|---------|--------------------------|--------------------------|
| **Design Philosophy** | Horizontal scaling | Vertical scaling |
| **Switches** | 40 | 31 |
| **Publishers** | 54 | 18 |
| **Max Hops** | 4 | **6** |
| **Hierarchy Layers** | 4 | **6** |
| **Congestion Type** | Distributed (multiple points) | **Concentrated (edge layer)** |
| **Bandwidth Range** | 10M → 1M (10x reduction) | 10M → 0.05M **(200x reduction)** |
| **Primary Test** | Wide deployment scalability | **Deep path + extreme congestion** |
| **Realistic Scenario** | Smart campus/city | Industrial IoT / Data center |
| **Implementation Complexity** | Medium | Low (linear branches) |
| **Expected Runtime (10min)** | ~540k messages | ~180k messages |
| **Key Metric** | Horizontal scalability | **Cumulative latency** |

---

## REKOMENDASI

### **Untuk Paper:**

**Jika ingin menunjukkan:**

1. **Skalabilitas horizontal (wide deployment):**
   - Pilih **OPSI 1** (Multi-Building Campus)
   - Highlight: "Framework efektif pada 40 switches, 54 publishers, 9 subnets"
   - Story: Smart campus dengan multiple buildings

2. **Efektivitas pada path panjang (deep forwarding):**
   - Pilih **OPSI 2** (Deep Hierarchical)
   - Highlight: "DSCP priority tetap efektif pada 6-hop path dengan 200x bandwidth reduction"
   - Story: Industrial IoT dengan multi-tier aggregation

3. **Keduanya (comprehensive evaluation):**
   - Implement **OPSI 1** sebagai Scenario 09
   - Implement **OPSI 2** sebagai Scenario 10
   - Paper menunjukkan framework works untuk **wide AND deep** deployments

### **Estimasi Effort:**

| Task | Opsi 1 | Opsi 2 |
|------|--------|--------|
| **Code complexity** | Medium | Low |
| **Testing time** | Higher (more devices) | Lower (same as S06) |
| **Results analysis** | 3x data volume | Same as S06 |
| **Paper contribution** | Horizontal scalability | Vertical scalability |

### **Saran Saya:**

**Untuk Topologi 2 di paper:**
- Gunakan **OPSI 2 (Deep Network)** karena:
  1. ✅ More **distinctive** dari Scenario 06 (6 hops vs 3 hops)
  2. ✅ **Easier to implement** (hanya 18 publishers)
  3. ✅ **Clearer contribution**: "QoS effectiveness pada long forwarding paths"
  4. ✅ **Better story**: Extreme edge congestion (240%) + deep path = worst case
  5. ✅ **Fair comparison**: Same publishers as S06, tapi path lebih panjang

**Di paper bisa tulis:**
> "Untuk mengevaluasi efektivitas framework pada deployment dengan forwarding path yang lebih panjang, kami mengimplementasikan topologi hierarkis 6-layer dengan 31 switch. Topologi ini mensimulasikan industrial IoT atau data center dengan aggregation bertingkat, menghasilkan worst-case scenario: 6-hop forwarding path dengan extreme congestion (240%) di edge layer..."

---

## NEXT STEPS

Pilih salah satu opsi:
1. **Opsi 1** - Wide network (40 switches, 54 publishers)
2. **Opsi 2** - Deep network (31 switches, 18 publishers, 6 hops)
3. **Both** - Implement kedua-duanya

Saya siap generate code untuk opsi yang Anda pilih! 🚀
