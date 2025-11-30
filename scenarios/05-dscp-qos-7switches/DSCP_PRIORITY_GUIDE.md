# DSCP Priority Guide - Scenario 05

## 📋 Overview

Scenario 05 mendukung **5 Level Priority** menggunakan DSCP tagging di IP header.
Anda bisa menggunakan publisher dengan priority level yang berbeda sesuai kebutuhan.

---

## 🎯 5 Priority Levels

| DSCP Value | Class | Priority | Queue | Bandwidth | Publisher File |
|------------|-------|----------|-------|-----------|----------------|
| **46** | EF (Expedited Forwarding) | **VERY HIGH** | Queue 1 | 60-80% | `publisher_dscp46_veryhigh.py` |
| **34** | AF41 (Assured Forwarding 41) | **HIGH** | Queue 2 | 45-60% | `publisher_dscp34_high.py` |
| **26** | AF31 (Assured Forwarding 31) | **MEDIUM** | Queue 3 | 30-45% | `publisher_dscp26_medium.py` |
| **10** | AF11 (Assured Forwarding 11) | **LOW** | Queue 4 | 15-30% | `publisher_dscp10_low.py` |
| **0** | BE (Best Effort) | **BEST EFFORT** | Queue 5 | 5-15% | `publisher_dscp0_besteffort.py` |

---

## 📝 Cara Menggunakan Publisher

### 1. Jalankan Publisher dengan Priority Tertentu

Pilih publisher sesuai priority yang diinginkan:

```bash
# VERY HIGH Priority (DSCP 46 - untuk data critical/emergency)
DEVICE=sensor_critical BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp46_veryhigh.py

# HIGH Priority (DSCP 34 - untuk data penting)
DEVICE=sensor_important BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp34_high.py

# MEDIUM Priority (DSCP 26 - untuk data warning/moderate)
DEVICE=sensor_warning BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp26_medium.py

# LOW Priority (DSCP 10 - untuk data monitoring)
DEVICE=sensor_monitor BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp10_low.py

# BEST EFFORT (DSCP 0 - untuk data routine/normal)
DEVICE=sensor_routine BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp0_besteffort.py
```

### 2. Environment Variables

Semua publisher support environment variables berikut:

- `BROKER_IP`: IP address MQTT broker (default: `10.0.0.1`)
- `DEVICE`: Nama device untuk identification (default: tergantung publisher)
- `MSG_RATE`: Message rate per second (default: `50`)

---

## 🔧 Cara Kerja

### Publisher Side

Publisher menggunakan **socket option `IP_TOS`** untuk set DSCP value di IP header:

```python
def on_socket_open(client, userdata, sock):
    ip_tos = DSCP_VALUE << 2  # Shift left 2 bits
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, ip_tos)
```

**DSCP to IP_TOS Conversion:**
- DSCP 46 → TOS 0xb8 (184)
- DSCP 34 → TOS 0x88 (136)
- DSCP 26 → TOS 0x68 (104)
- DSCP 10 → TOS 0x28 (40)
- DSCP 0  → TOS 0x00 (0)

### Controller Side

Controller **match DSCP field** di IP header dan **set queue**:

```python
# Flow rule untuk DSCP 46
match = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)
actions = [
    parser.OFPActionSetQueue(1),  # Queue 1 (highest bandwidth)
    parser.OFPActionOutput(ofproto.OFPP_NORMAL)
]
```

### Switch Side

OVS menggunakan **HTB queuing** dengan 5 queues:

```bash
# Queue 1: DSCP 46 - 60-80% bandwidth (300-400 Kbps pada link 0.5 Mbps)
# Queue 2: DSCP 34 - 45-60% bandwidth (225-300 Kbps)
# Queue 3: DSCP 26 - 30-45% bandwidth (150-225 Kbps)
# Queue 4: DSCP 10 - 15-30% bandwidth (75-150 Kbps)
# Queue 5: DSCP 0  - 5-15% bandwidth  (25-75 Kbps)
```

---

## 🎓 Use Cases

### Contoh 1: IoT Monitoring System

```
- VERY HIGH (DSCP 46): Fire alarm, gas leak, emergency alerts
- HIGH (DSCP 34): Security breach, abnormal sensor readings
- MEDIUM (DSCP 26): Temperature warnings, humidity alerts
- LOW (DSCP 10): Regular sensor monitoring (hourly)
- BEST EFFORT (DSCP 0): Device status, keep-alive messages
```

### Contoh 2: Industrial Automation

```
- VERY HIGH (DSCP 46): Machine fault, safety shutdown signals
- HIGH (DSCP 34): Production line control commands
- MEDIUM (DSCP 26): Quality control measurements
- LOW (DSCP 10): Inventory updates
- BEST EFFORT (DSCP 0): Logging, telemetry data
```

### Contoh 3: Smart City

```
- VERY HIGH (DSCP 46): Traffic accident alerts, emergency vehicle signals
- HIGH (DSCP 34): Traffic light control, accident detection
- MEDIUM (DSCP 26): Parking sensors, street lighting control
- LOW (DSCP 10): Air quality monitoring
- BEST EFFORT (DSCP 0): General city statistics
```

---

## 🧪 Testing Priority Differentiation

### Test dengan 2 Priority Levels

Jalankan 2 publishers dengan priority berbeda untuk lihat perbedaan:

```bash
# Terminal 1: VERY HIGH Priority
DEVICE=test_high BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp46_veryhigh.py

# Terminal 2: BEST EFFORT Priority
DEVICE=test_low BROKER_IP=10.0.0.1 MSG_RATE=50 \
python3 publisher_dscp0_besteffort.py
```

Expected results (dengan congestion):
- VERY HIGH delay: ~1-2 ms ⚡ FAST
- BEST EFFORT delay: ~100+ ms 🐌 SLOW

### Test dengan Semua 5 Levels

Jalankan full experiment dengan semua 5 priority levels untuk benchmark complete differentiation.

---

## 📊 Expected Performance

Dengan **high network congestion** (80-96% utilization):

```
VERY HIGH (DSCP 46):  ~1-2 ms    (fastest)
HIGH (DSCP 34):       ~10-20 ms
MEDIUM (DSCP 26):     ~40-60 ms
LOW (DSCP 10):        ~80-100 ms
BEST EFFORT (DSCP 0): ~100-150 ms (slowest)
```

---

## 🔍 Verification

### 1. Check Flow Rules

```bash
# Lihat flow table di switch s1
sudo ovs-ofctl dump-flows s1 -O OpenFlow13

# Expected output (excerpt):
# priority=60, ip,ip_dscp=46 actions=set_queue:1,NORMAL
# priority=55, ip,ip_dscp=34 actions=set_queue:2,NORMAL
# priority=50, ip,ip_dscp=26 actions=set_queue:3,NORMAL
# priority=45, ip,ip_dscp=10 actions=set_queue:4,NORMAL
# priority=40, ip,ip_dscp=0  actions=set_queue:5,NORMAL
```

### 2. Check Queue Configuration

```bash
# Lihat queue configuration
sudo ovs-vsctl list qos
sudo ovs-vsctl list queue

# Check queue attached to port
sudo ovs-vsctl get port s1-eth1 qos
```

### 3. Capture DSCP Values

```bash
# Capture packets dan verify DSCP value
sudo tcpdump -i any -n -v 'port 1883' | grep "tos"

# Expected output (examples):
# IP (tos 0xb8, ...) - DSCP 46 (VERY HIGH)
# IP (tos 0x88, ...) - DSCP 34 (HIGH)
# IP (tos 0x68, ...) - DSCP 26 (MEDIUM)
# IP (tos 0x28, ...) - DSCP 10 (LOW)
# IP (tos 0x0, ...)  - DSCP 0 (BEST EFFORT)
```

---

## 💡 Tips

1. **Gunakan priority sesuai importance data:**
   - VERY HIGH: Hanya untuk data yang benar-benar critical (< 1% traffic)
   - HIGH: Data penting yang perlu response cepat
   - MEDIUM: Data moderate yang bisa toleransi delay kecil
   - LOW: Data monitoring rutin
   - BEST EFFORT: Data yang tidak time-sensitive

2. **Avoid overload pada high priority:**
   - Jika semua publisher pakai VERY HIGH, tidak ada differentiation
   - Balance antara priority levels untuk optimal QoS

3. **Test dengan congestion:**
   - Priority differentiation hanya terlihat jelas saat network congested
   - Tanpa congestion, semua traffic akan cepat

---

## 📚 References

- **RFC 2474**: Definition of the Differentiated Services Field (DS Field)
- **RFC 2597**: Assured Forwarding PHB Group
- **RFC 3246**: An Expedited Forwarding PHB
- **DSCP Values**: [IANA DSCP Registry](https://www.iana.org/assignments/dscp-registry/dscp-registry.xhtml)

---

## 🆘 Troubleshooting

### Publisher tidak set DSCP?

**Check log publisher:**
```bash
tail -f /home/mqtt-sdn/logs/publisher_*.log
```

**Expected:** `[DSCP] Socket configured with TOS=0x...`

**Solution:** Pastikan paho-mqtt versi 2.x dan callback API version correct.

### Flow rules tidak match DSCP?

**Check flow table:**
```bash
sudo ovs-ofctl dump-flows s1 -O OpenFlow13 | grep dscp
```

**Solution:** Pastikan controller running dan install flows dengan `ip_dscp` field.

### Tidak ada priority differentiation?

**Possible causes:**
1. **Network tidak congested** - Priority hanya terlihat saat congestion
2. **Queue tidak configured** - Check `ovs-vsctl list qos`
3. **Semua traffic sama priority** - Check DSCP values di publisher

---

**Created:** 2025-11-13
**Scenario:** 05-dscp-qos
**Version:** 5-Level Priority Support
