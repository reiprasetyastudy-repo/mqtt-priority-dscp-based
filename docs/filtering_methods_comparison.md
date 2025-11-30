# Perbandingan Metode Filtering/Prioritas untuk SDN-MQTT

**Dokumentasi Research:** Analisis berbagai metode klasifikasi dan prioritas traffic untuk sistem IoT berbasis SDN

---

## 📚 Daftar Isi

1. [Overview](#overview)
2. [Metode 1: IP-Based Filtering](#metode-1-ip-based-filtering)
3. [Metode 2: Subnet-Based Filtering](#metode-2-subnet-based-filtering)
4. [Metode 3: Deep Packet Inspection (DPI) - MQTT Topic/Payload](#metode-3-deep-packet-inspection-dpi)
5. [Metode 4: DSCP/ToS Pre-Marking](#metode-4-dscptos-pre-marking)
6. [Metode 5: Port-Based Filtering](#metode-5-port-based-filtering)
7. [Metode 6: VLAN-Based Filtering](#metode-6-vlan-based-filtering)
8. [Metode 7: Hybrid Approach](#metode-7-hybrid-approach)
9. [Perbandingan & Rekomendasi](#perbandingan--rekomendasi)
10. [Novelty untuk Penelitian](#novelty-untuk-penelitian)

---

## Overview

Dalam sistem IoT berbasis SDN, klasifikasi dan prioritas traffic adalah kunci untuk memastikan data critical/anomaly mendapat layanan yang lebih baik. Dokumen ini menganalisis 7 metode filtering yang dapat diimplementasikan.

---

## Metode 1: IP-Based Filtering

### 📋 Deskripsi
Klasifikasi berdasarkan **IP address source** dari setiap device.

```python
# Flow rule untuk setiap IP
match_anomaly_1 = parser.OFPMatch(ipv4_src="10.0.0.1", tcp_dst=1883)  # Device 1
match_anomaly_2 = parser.OFPMatch(ipv4_src="10.0.0.10", tcp_dst=1883) # Device 2
match_normal_1 = parser.OFPMatch(ipv4_src="10.0.0.2", tcp_dst=1883)   # Device 3
```

### ✅ Kelebihan (Pros)
- **Simple & straightforward** - mudah dipahami dan diimplementasikan
- **Granular control** - kontrol per-device sangat detail
- **No overhead** - matching di hardware (switch ASIC), super cepat
- **Deterministik** - pasti tau device mana yang high/low priority

### ❌ Kekurangan (Cons)
- **Tidak scalable** - butuh 1 flow rule per device
- **Static configuration** - device tidak bisa ganti priority secara dinamis
- **Flow table bloat** - dengan 1000 device = 1000+ flow rules
- **Maintenance nightmare** - tambah/hapus device perlu update controller
- **IP planning dependency** - device harus punya IP tetap/predictable

### 🎯 Use Case
- **Proof of concept** / demo awal
- Network kecil (< 50 device)
- Device dengan IP static dan tidak sering berubah

### 📊 Complexity
- **Implementation:** ⭐ (Very Easy)
- **Scalability:** ⭐ (Poor)
- **Performance:** ⭐⭐⭐⭐⭐ (Excellent - hardware matching)
- **Flexibility:** ⭐ (Very Low)

### 🔬 Research Novelty
**LOW** - Metode standard, sudah banyak digunakan di literatur SDN

---

## Metode 2: Subnet-Based Filtering

### 📋 Deskripsi
Klasifikasi berdasarkan **subnet/network range**. Device dikelompokkan ke subnet berbeda berdasarkan kategori.

```
Network Design:
- Anomaly devices: 10.0.1.0/24 (10.0.1.1 - 10.0.1.254)
- Normal devices:  10.0.2.0/24 (10.0.2.1 - 10.0.2.254)
- Critical:        10.0.3.0/24 (10.0.3.1 - 10.0.3.254)
```

**Flow rules (hanya 3 rules untuk ratusan device!):**
```python
# Match berdasarkan subnet prefix
match_anomaly = parser.OFPMatch(eth_type=0x0800,
                                ipv4_src="10.0.1.0",
                                ipv4_src_mask="255.255.255.0")
match_normal = parser.OFPMatch(eth_type=0x0800,
                               ipv4_src="10.0.2.0",
                               ipv4_src_mask="255.255.255.0")
```

### ✅ Kelebihan (Pros)
- **Highly scalable** - 1 flow rule untuk 254 device!
- **Simple flow table** - hanya beberapa rules untuk ribuan device
- **Good network segmentation** - clear separation antar kategori
- **Easy to manage** - tambah device cukup assign IP di subnet yang tepat
- **Industry standard** - sesuai best practice network design

### ❌ Kekurangan (Cons)
- **Requires network planning** - perlu IP addressing scheme yang baik
- **Still static** - device tidak bisa pindah kategori tanpa ganti IP
- **Subnet size limitation** - /24 = max 254 device per kategori
- **Not content-aware** - tidak bisa klasifikasi based on message content

### 🎯 Use Case
- **Production deployment** - real-world IoT network
- Large-scale IoT (100-1000+ devices)
- Multi-tier architecture (critical/normal/low priority)

### 📊 Complexity
- **Implementation:** ⭐⭐ (Easy)
- **Scalability:** ⭐⭐⭐⭐⭐ (Excellent)
- **Performance:** ⭐⭐⭐⭐⭐ (Excellent - hardware matching)
- **Flexibility:** ⭐⭐ (Medium-Low)

### 🔬 Research Novelty
**LOW-MEDIUM** - Improvement dari IP-based, tetapi masih standard approach

---

## Metode 3: Deep Packet Inspection (DPI) - MQTT Topic/Payload

### 📋 Deskripsi
Klasifikasi berdasarkan **isi message MQTT** (topic atau payload). Controller melakukan inspection pada layer aplikasi.

```
Packet flow:
1. First packet → packet-in to controller
2. Controller parse MQTT protocol
3. Extract topic atau payload
4. Classify berdasarkan content
5. Install flow rule untuk session tersebut

Contoh:
Topic "iot/critical" atau "iot/anomaly" → Queue 1 (high priority)
Topic "iot/normal" → Queue 2 (low priority)

Atau inspect payload JSON:
{"type": "anomaly", "value": 95} → Queue 1
{"type": "normal", "value": 25} → Queue 2
```

### ✅ Kelebihan (Pros)
- **Content-aware** - klasifikasi based on actual message content! ⭐⭐⭐
- **Highly flexible** - device bisa kirim berbagai jenis message dengan priority berbeda
- **Dynamic classification** - priority bisa berubah per-message
- **Application-layer intelligence** - SDN jadi "smart" dan context-aware
- **HIGH RESEARCH NOVELTY** - jarang ada yang implement di SDN-IoT
- **Real anomaly detection** - bisa detect anomaly dari data, bukan cuma IP

### ❌ Kekurangan (Cons)
- **Complex implementation** - perlu parse MQTT protocol (bukan trivial)
- **Performance overhead** - packet-in ke controller (latency tambahan)
- **Scalability concern** - controller bisa bottleneck jika banyak flow baru
- **Stateful inspection** - perlu track MQTT session state
- **CPU intensive** - controller perlu decode packet
- **First packet delay** - packet pertama kena delay karena packet-in

### 🎯 Use Case
- **Research projects** - thesis/paper dengan novelty tinggi
- Smart classification - classify berdasarkan content, bukan network layer
- Heterogeneous IoT - device yang publish berbagai tipe data
- **Real anomaly detection** - detect anomaly dari sensor reading

### 📊 Complexity
- **Implementation:** ⭐⭐⭐⭐ (Hard)
- **Scalability:** ⭐⭐⭐ (Medium - depends on flow arrival rate)
- **Performance:** ⭐⭐⭐ (Medium - packet-in overhead)
- **Flexibility:** ⭐⭐⭐⭐⭐ (Excellent)

### 🔬 Research Novelty
**VERY HIGH** ⭐⭐⭐⭐⭐
- Jarang ada implementasi DPI untuk MQTT di SDN
- Application-aware SDN adalah topik hot di research
- Bisa publish di conference/journal tier 1-2
- Kontribusi: menunjukkan SDN bisa intelligent di layer aplikasi

### 📝 Implementation Approach

**Tahap 1: MQTT Protocol Parsing**
```python
@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
def packet_in_handler(self, ev):
    pkt = packet.Packet(ev.msg.data)
    tcp_pkt = pkt.get_protocol(tcp.tcp)

    if tcp_pkt and tcp_pkt.dst_port == 1883:
        # Parse MQTT payload
        mqtt_data = extract_mqtt_from_tcp(tcp_pkt.data)

        if mqtt_data.msg_type == MQTT_PUBLISH:
            topic = mqtt_data.topic

            # Classify based on topic
            if "critical" in topic or "anomaly" in topic:
                queue = 1  # High priority
            else:
                queue = 2  # Normal

            # Install flow for this 5-tuple
            self.install_flow_for_session(...)
```

**Tahap 2: Caching untuk Performance**
- Cache classification result per session
- Subsequent packets tidak perlu packet-in

---

## Metode 4: DSCP/ToS Pre-Marking

### 📋 Deskripsi
Publisher sendiri yang **marking traffic** dengan set DSCP (Differentiated Services Code Point) di IP header. Controller cukup match DSCP value.

```python
# Di publisher_anomaly.py (marking)
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8)  # DSCP 46 (EF)

# Di controller (matching)
match_high = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)  # → Queue 1
match_low = parser.OFPMatch(eth_type=0x0800, ip_dscp=0)    # → Queue 2
```

### ✅ Kelebihan (Pros)
- **Industry standard** - DSCP adalah QoS standard (RFC 2474)
- **Simple controller** - cuma match DSCP, tidak perlu DPI
- **Scalable** - berapa pun jumlah device, cuma perlu ~6 flow rules (DSCP classes)
- **Interoperable** - compatible dengan router/switch traditional
- **Fast** - hardware matching, no packet-in
- **End-to-end QoS** - bisa di-honor sepanjang network path

### ❌ Kekurangan (Cons)
- **Trust issue** - device bisa "cheat" dan mark semua traffic as high priority
- **Requires publisher modification** - perlu ubah code publisher
- **Not dynamic from controller** - controller tidak bisa reclassify
- **Limited classes** - DSCP cuma 64 nilai, praktis ~6-8 kelas QoS
- **May be overwritten** - intermediate router bisa overwrite DSCP

### 🎯 Use Case
- **Production network** - enterprise IoT deployment
- **Multi-domain QoS** - traffic melewati multiple networks
- **Trusted devices** - device yang di-control penuh (tidak public)
- **Integration with existing infrastructure**

### 📊 Complexity
- **Implementation:** ⭐⭐ (Easy - publisher & controller)
- **Scalability:** ⭐⭐⭐⭐⭐ (Excellent)
- **Performance:** ⭐⭐⭐⭐⭐ (Excellent - hardware matching)
- **Flexibility:** ⭐⭐⭐ (Medium)

### 🔬 Research Novelty
**LOW** - Standard QoS mechanism, bukan novelty

**Bisa ditingkatkan novelty-nya dengan:**
- Combine dengan anomaly detection: controller detect anomaly lalu push DSCP remarking via REST API
- Dynamic DSCP marking berdasarkan network condition

---

## Metode 5: Port-Based Filtering

### 📋 Deskripsi
Klasifikasi berdasarkan **TCP/UDP destination port**. Beda priority = beda port.

```
Network design:
- MQTT Critical: port 1884 → Queue 1
- MQTT Normal:   port 1883 → Queue 2
- MQTT Low:      port 1882 → Queue 3
```

```python
match_critical = parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=1884)
match_normal = parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=1883)
```

### ✅ Kelebihan (Pros)
- **Extremely simple** - trivial implementation
- **Fast** - hardware matching
- **Scalable** - berapa pun jumlah device, cuma 3-4 flow rules
- **No device modification** - cukup ubah config port

### ❌ Kekurangan (Cons)
- **Requires multiple broker instances** - atau broker dengan multi-port listener
- **Not flexible** - device tidak bisa dynamic switch priority
- **Port exhaustion** - limited port numbers
- **Non-standard** - MQTT standard di port 1883

### 🎯 Use Case
- **Quick prototype** - demo cepat
- **Testing/lab environment**
- Aplikasi dengan service class yang tetap

### 📊 Complexity
- **Implementation:** ⭐ (Very Easy)
- **Scalability:** ⭐⭐⭐⭐ (Good)
- **Performance:** ⭐⭐⭐⭐⭐ (Excellent)
- **Flexibility:** ⭐⭐ (Low)

### 🔬 Research Novelty
**VERY LOW** - Terlalu simple untuk paper

---

## Metode 6: VLAN-Based Filtering

### 📋 Deskripsi
Klasifikasi berdasarkan **VLAN tag** (802.1Q). Device di-assign ke VLAN berbeda per priority class.

```
Network design:
- VLAN 10: Critical devices
- VLAN 20: Normal devices
- VLAN 30: Low priority devices
```

```python
match_critical = parser.OFPMatch(eth_type=0x0800, vlan_vid=10)
match_normal = parser.OFPMatch(eth_type=0x0800, vlan_vid=20)
```

### ✅ Kelebihan (Pros)
- **Enterprise-grade** - VLAN adalah standard enterprise network
- **Strong isolation** - VLAN provides layer-2 segmentation
- **Scalable** - 4096 VLANs available (praktis ~100 VLAN)
- **Security benefit** - isolation antar tier
- **Works with existing infrastructure** - compatible dengan managed switch

### ❌ Kekurangan (Cons)
- **Requires VLAN-capable devices** - IoT device perlu support 802.1Q tagging
- **Switch dependency** - switch perlu support VLAN
- **Complex setup** - VLAN configuration bisa rumit
- **Not dynamic** - device tidak bisa pindah VLAN secara programmatic (butuh re-tagging)

### 🎯 Use Case
- **Enterprise IoT** - corporate building automation, smart city
- **Large-scale deployment** - ratusan hingga ribuan device
- **Multi-tier architecture** - critical/operational/monitoring

### 📊 Complexity
- **Implementation:** ⭐⭐⭐ (Medium)
- **Scalability:** ⭐⭐⭐⭐⭐ (Excellent)
- **Performance:** ⭐⭐⭐⭐⭐ (Excellent)
- **Flexibility:** ⭐⭐ (Medium-Low)

### 🔬 Research Novelty
**LOW-MEDIUM** - Standard approach, tetapi bisa ditingkatkan dengan dynamic VLAN assignment

---

## Metode 7: Hybrid Approach

### 📋 Deskripsi
Kombinasi multiple metode untuk **best of both worlds**. Biasanya: **fast path + slow path**.

```
Hybrid Design (Subnet + DPI):

Fast Path (majority traffic):
- Match subnet → instant classification
- 10.0.1.0/24 → Queue 1
- 10.0.2.0/24 → Queue 2

Slow Path (unknown/special cases):
- IP tidak match subnet → packet-in
- Controller parse MQTT topic/payload
- Dynamic classification
- Install flow untuk session ini
```

### ✅ Kelebihan (Pros)
- **Best of both worlds** - fast untuk common case, smart untuk edge case
- **Highly flexible** - combine simplicity & intelligence
- **Graceful degradation** - fallback mechanism jika satu metode gagal
- **Adaptive** - bisa dynamic adjust classification
- **HIGH research value** - menunjukkan advanced SDN programming

### ❌ Kekurangan (Cons)
- **Complex implementation** - perlu integrate multiple methods
- **Harder to debug** - multiple code paths
- **Requires careful design** - priority antar metode perlu jelas

### 🎯 Use Case
- **Research projects** - thesis/dissertation dengan kontribusi signifikan
- **Production with smart features** - scalable tapi tetap intelligent
- **Heterogeneous network** - mix of device types

### 📊 Complexity
- **Implementation:** ⭐⭐⭐⭐⭐ (Very Hard)
- **Scalability:** ⭐⭐⭐⭐ (Very Good)
- **Performance:** ⭐⭐⭐⭐ (Very Good - optimized paths)
- **Flexibility:** ⭐⭐⭐⭐⭐ (Excellent)

### 🔬 Research Novelty
**VERY HIGH** ⭐⭐⭐⭐⭐
- Menunjukkan sophisticated SDN architecture
- Combine efficiency & intelligence
- Bisa publish high-tier conference/journal

### 📝 Implementation Example

```python
def classify_traffic(self, pkt, in_port):
    ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
    src_ip = ipv4_pkt.src

    # Fast path: Check subnet first
    if self.is_in_subnet(src_ip, "10.0.1.0/24"):
        return QUEUE_HIGH  # Anomaly subnet
    elif self.is_in_subnet(src_ip, "10.0.2.0/24"):
        return QUEUE_LOW   # Normal subnet

    # Slow path: DPI for unknown IPs
    else:
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        if tcp_pkt and tcp_pkt.dst_port == 1883:
            # Parse MQTT
            mqtt_data = self.parse_mqtt(tcp_pkt.data)

            if "critical" in mqtt_data.topic:
                return QUEUE_HIGH
            else:
                return QUEUE_LOW

        return QUEUE_DEFAULT
```

---

## Perbandingan & Rekomendasi

### 📊 Comparison Matrix

| Metode | Scalability | Performance | Flexibility | Complexity | Research Novelty | Production Ready |
|--------|-------------|-------------|-------------|------------|------------------|------------------|
| **IP-Based** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ✅ (small scale) |
| **Subnet-Based** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ✅ |
| **DPI (MQTT)** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⚠️ (needs optimization) |
| **DSCP Marking** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ✅ |
| **Port-Based** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ✅ (simple use case) |
| **VLAN-Based** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ✅ |
| **Hybrid** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⚠️ (complex) |

---

### 🎯 Rekomendasi Berdasarkan Tujuan

#### **Untuk Proof of Concept / Demo Cepat:**
→ **IP-Based** atau **Port-Based**

#### **Untuk Production Deployment:**
→ **Subnet-Based** atau **DSCP Marking**

#### **Untuk Thesis / Research Paper:**
→ **DPI (MQTT Topic/Payload)** atau **Hybrid**

#### **Untuk Enterprise/Large Scale:**
→ **VLAN-Based** atau **Subnet-Based**

---

## Novelty untuk Penelitian

### 🔬 Ranking Novelty untuk Paper/Thesis

**Tier 1 (Highly Novel - Target: Conference/Journal Tier 1-2)**
1. **DPI dengan MQTT Topic/Payload Inspection** ⭐⭐⭐⭐⭐
   - **Why:** Application-aware SDN, jarang ada di literatur
   - **Contribution:** Menunjukkan SDN bisa intelligent di layer aplikasi
   - **Keywords:** Deep Packet Inspection, Application-aware SDN, MQTT-aware QoS

2. **Hybrid: Subnet + DPI** ⭐⭐⭐⭐⭐
   - **Why:** Sophisticated architecture, balance performance & intelligence
   - **Contribution:** Multi-tier classification dengan adaptive behavior
   - **Keywords:** Hybrid SDN Architecture, Adaptive QoS, Smart Routing

**Tier 2 (Medium Novel - Target: Conference/Journal Tier 2-3)**
3. **VLAN-Based dengan Dynamic VLAN Assignment**
   - Tambahkan: Controller bisa dynamically assign device ke VLAN berdasarkan behavior
   - **Contribution:** Programmable network segmentation

4. **DSCP Marking dengan Dynamic Remarking**
   - Tambahkan: Controller monitor network, bisa push remarking command ke device
   - **Contribution:** Closed-loop QoS adaptation

**Tier 3 (Low Novel - Improvement/Optimization Paper)**
5. **Subnet-Based**
   - Bisa paper jika ditambah optimization algorithm (subnet planning)

6. **IP-Based, Port-Based**
   - Terlalu standard untuk paper utama, bisa jadi baseline comparison

---

### 📝 Research Framework untuk DPI Method

**Problem Statement:**
"Bagaimana SDN dapat melakukan prioritas traffic IoT berdasarkan konten message (content-aware), bukan hanya berdasarkan network layer information?"

**Proposed Solution:**
Deep Packet Inspection pada MQTT protocol untuk klasifikasi real-time berdasarkan topic atau payload.

**Contributions:**
1. **DPI module** untuk parse MQTT protocol di SDN controller
2. **Hybrid classification** - fast path (subnet) + slow path (DPI)
3. **Performance evaluation** - latency overhead, scalability limit
4. **Real-world use case** - anomaly detection untuk smart city/healthcare

**Evaluation Metrics:**
- Classification accuracy
- Latency overhead (DPI vs non-DPI)
- Controller CPU usage
- Scalability (max devices before bottleneck)
- Flow table size

**Expected Results:**
- DPI latency: +5-10ms untuk first packet
- Subsequent packets: 0 overhead (cached flow)
- Support 1000+ devices dengan proper caching

---

## 💡 Kesimpulan

**Untuk sistem yang kompleks kedepan:**

**Jangka Pendek (Quick Win):**
- Start dengan **Subnet-Based** - simple, scalable, production-ready

**Jangka Menengah (Research Value):**
- Implement **DPI dengan MQTT Topic Inspection** - high novelty

**Jangka Panjang (Advanced):**
- Build **Hybrid: Subnet + DPI** - best architecture

**Key Insight:**
> "Tidak ada one-size-fits-all solution. Pilih metode based on:
> - Scale (10 vs 1000 devices?)
> - Flexibility needs (static vs dynamic?)
> - Research goals (novelty vs production?)"

---

**Author:** Research Documentation - SDN-MQTT Project
**Date:** 2025-11-09
**Version:** 1.0
