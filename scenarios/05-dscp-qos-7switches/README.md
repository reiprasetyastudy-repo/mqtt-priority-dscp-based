# Scenario 05: DSCP-Based QoS for IoT Priority

## 🎯 Apa itu Scenario 05?

Scenario 05 menggunakan **DSCP (Differentiated Services Code Point)** di IP header untuk membedakan prioritas traffic IoT.

### Perbedaan dengan Scenario 03:

| Aspek | Scenario 03 | Scenario 05 (Ini) |
|-------|-------------|-------------------|
| **Metode** | IP-based classification | **DSCP tagging** |
| **Publisher** | Set data biasa | **Set DSCP di socket** |
| **Controller** | Classify berdasarkan IP | **Match DSCP value** |
| **Kompleksitas** | Perlu MAC learning | **Lebih simple!** |
| **Processing** | Controller classify | **Switch match langsung** |

---

## 🏗️ Topologi

**SAMA dengan Scenario 03:**
- 7 switches (1 core + 2 agg + 4 edge)
- 8 publishers (4 anomaly + 4 normal)
- 1 broker di core
- Bandwidth: 1 Mbps per link
- Utilization: 80% (congestion)

```
                    [Broker 10.0.0.1]
                            │
                         [s1 Core]
                            │
                ┌───────────┴───────────┐
            [s2 Agg]               [s3 Agg]
                │                      │
        ┌───────┴──────┐       ┌───────┴──────┐
     [s4]          [s5]      [s6]          [s7]
      │ │           │ │       │ │           │ │
    A   N         A   N     A   N         A   N
```

---

## 🚦 DSCP Values

| Traffic Type | DSCP Value | IP_TOS | Priority | Queue |
|--------------|------------|--------|----------|-------|
| **Anomaly** | 46 | 0xb8 (184) | Expedited Forwarding | Queue 1 (70-100% BW) |
| **Normal** | 0 | 0x00 (0) | Best Effort | Queue 2 (30-50% BW) |

---

## 📝 Cara Kerja

### 1. Publisher Set DSCP di Socket

**Anomaly Publisher:**
```python
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xb8)  # DSCP 46
client.connect(BROKER, sock=sock)
```

**Normal Publisher:**
```python
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x00)  # DSCP 0
client.connect(BROKER, sock=sock)
```

### 2. Controller Match DSCP → Set Queue

**Flow Rules:**
```python
# DSCP 46 → Queue 1 (High Priority)
match = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)
actions = [OFPActionSetQueue(1), OFPActionOutput(OFPP_NORMAL)]

# DSCP 0 → Queue 2 (Low Priority)
match = parser.OFPMatch(eth_type=0x0800, ip_dscp=0)
actions = [OFPActionSetQueue(2), OFPActionOutput(OFPP_NORMAL)]
```

### 3. Switch Forward Berdasarkan Queue

- Queue 1: 70-100% bandwidth → Delay rendah
- Queue 2: 30-50% bandwidth → Delay tinggi

---

## 🚀 Cara Menjalankan

### Option 1: Full Experiment (Recommended)

```bash
cd /home/mqtt-sdn/scenarios/05-dscp-qos

# Run 5 minutes
sudo ./run_experiment.sh 300
```

Script ini akan:
1. Start Ryu controller dengan controller_dscp.py
2. Start topology dengan publisher DSCP
3. Auto stop setelah duration
4. Tampilkan metrics summary

### Option 2: Manual (2 Terminal)

**Terminal 1 - Controller:**
```bash
cd /home/mqtt-sdn/scenarios/05-dscp-qos
source /home/aldi/ryu39/bin/activate
ryu-manager controller_dscp.py ryu.app.ofctl_rest
```

**Terminal 2 - Topology:**
```bash
cd /home/mqtt-sdn/scenarios/05-dscp-qos
sudo ./run_scenario.sh 300
```

---

## 📊 Expected Results

### Target Metrics:

```
ANOMALY (DSCP 46 → Queue 1):
  Delay: ~12-15 ms  ⚡ FAST
  Jitter: ~2 ms

NORMAL (DSCP 0 → Queue 2):
  Delay: ~60-70 ms  🐌 SLOW
  Jitter: ~7 ms

Conclusion: Normal traffic 5-6x SLOWER than Anomaly
✅ Priority works via DSCP tagging!
```

---

## 🔍 Cara Verify DSCP

### 1. Check Flow Tables

```bash
# Lihat flow rules di switch
sudo ovs-ofctl dump-flows s1 -O OpenFlow13

# Expected output:
# priority=50, ip,ip_dscp=46 actions=set_queue:1,NORMAL
# priority=40, ip,ip_dscp=0  actions=set_queue:2,NORMAL
```

### 2. Capture Packets

```bash
# Capture MQTT traffic dan lihat DSCP
sudo tcpdump -i any -n -v 'port 1883' | grep "tos"

# Expected output:
# IP (tos 0xb8, ...) - Anomaly traffic
# IP (tos 0x0, ...)  - Normal traffic
```

### 3. Check Queue Stats

```bash
# Lihat queue configuration
sudo ovs-vsctl list qos
sudo ovs-vsctl list queue
```

---

## 📁 File Structure

```
05-dscp-qos/
├── publisher_anomaly_dscp.py   ← Set DSCP 46 di socket
├── publisher_normal_dscp.py    ← Set DSCP 0 di socket
├── controller_dscp.py           ← Match DSCP → Set Queue (SIMPLE!)
├── topology_config.py           ← Sama dengan Scenario 03
├── run_experiment.sh            ← Run controller + topology
├── run_scenario.sh              ← Run topology only (perlu controller sudah jalan)
└── README.md                    ← File ini
```

---

## 🎓 Keuntungan DSCP Approach

### ✅ Lebih Simple:
- Tidak perlu MAC learning di controller
- Tidak perlu packet-in classification
- Flow rules lebih sedikit

### ✅ Lebih Cepat:
- Switch langsung match DSCP (data plane)
- Tidak perlu tanya controller untuk classify
- Lower latency

### ✅ Standard Protocol:
- DSCP adalah standard IP (RFC 2474)
- Compatible dengan semua router/switch
- Bisa dipakai di real network

### ✅ Scalable:
- Tidak tergantung pada IP address
- Publisher sendiri yang set DSCP
- Controller tidak perlu tahu IP mapping

---

## 🔬 Research Novelty

**"Lightweight Priority Encoding for IoT-SDN Networks via DSCP Tagging"**

- IoT device set DSCP di application layer
- SDN controller match DSCP untuk QoS
- Anomaly-aware networking tanpa overhead kontrolNo need untuk deep packet inspection
- Processing di data plane (fast!)

---

## 🐛 Troubleshooting

### Publisher tidak set DSCP?

**Check:**
```bash
# Verify DSCP di packet
sudo tcpdump -i any -v -n 'port 1883 and host 10.0.1.1'
```

**Solution:**
- Pastikan paho-mqtt versi terbaru (`pip3 install --upgrade paho-mqtt`)
- Pastikan socket option di-set sebelum connect

### Flow rules tidak match DSCP?

**Check:**
```bash
sudo ovs-ofctl dump-flows s1 -O OpenFlow13 | grep dscp
```

**Solution:**
- Pastikan controller install flow dengan `ip_dscp` field
- Pastikan OpenFlow version = 1.3

### Queue tidak work?

**Check:**
```bash
sudo ovs-vsctl get port s1-eth1 qos
```

**Solution:**
- Pastikan queue di-attach ke port (bukan empty `[]`)
- Pastikan `configure_ovs_queues()` dipanggil di topology

---

## 📈 Compare dengan Scenario 03

Setelah run scenario 05, compare hasilnya:

```bash
# Scenario 03 results
cat /home/mqtt-sdn/results/03-tc-based-7switches/run_*/metrics_summary.txt

# Scenario 05 results
cat /home/mqtt-sdn/results/05-dscp-qos/run_*/metrics_summary.txt
```

**Expected:** Hasil delay pattern MIRIP (anomaly ~12ms, normal ~68ms)
**Why:** Topologi sama, queue config sama, hanya metode prioritas beda

---

## 📚 References

- RFC 2474: Definition of DSCP
- `/home/mqtt-sdn/2. DSCP Priority SDN MQTT.pdf` - Dokumentasi lengkap
- Scenario 03 - Base implementation (IP-based classification)

---

**Created:** 2025-11-13
**Author:** Scenario 05 Implementation Team
**Based on:** Scenario 03 (Proven Working)
