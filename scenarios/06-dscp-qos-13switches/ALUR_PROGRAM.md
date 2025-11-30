# Alur Program Scenario 06: DSCP QoS (13 Switches)

## 📋 Daftar Isi

1. [Gambaran Umum](#gambaran-umum)
2. [Alur Lengkap Program](#alur-lengkap-program)
3. [Fase 1: Inisialisasi & Cleanup](#fase-1-inisialisasi--cleanup)
4. [Fase 2: Start Ryu Controller](#fase-2-start-ryu-controller)
5. [Fase 3: Build Network Topology](#fase-3-build-network-topology)
6. [Fase 4: Configure DSCP QoS](#fase-4-configure-dscp-qos)
7. [Fase 5: Start MQTT Components](#fase-5-start-mqtt-components)
8. [Fase 6: Running Experiment](#fase-6-running-experiment)
9. [Fase 7: Cleanup & Shutdown](#fase-7-cleanup--shutdown)
10. [Flow Data MQTT](#flow-data-mqtt)

---

## Gambaran Umum

### Apa yang Terjadi Saat Menjalankan Experiment?

Ketika Anda menjalankan:
```bash
sudo ./run_experiment.sh 300
```

Program akan melakukan **7 fase utama**:

```
┌─────────────────────────────────────────────────────────────────┐
│  START: ./run_experiment.sh 300                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1: Inisialisasi & Cleanup                                 │
│  • Set variables (PROJECT_ROOT, RYU_ENV, DURATION)              │
│  • Kill proses lama (mosquitto, publisher, ryu)                 │
│  • Cleanup Mininet (sudo mn -c)                                 │
│  • Create timestamped results directory                         │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 2: Start Ryu Controller                                   │
│  • Activate Python virtual environment (/home/aldi/ryu39)       │
│  • Start ryu-manager dengan controller_dscp.py                  │
│  • Wait 3 detik sampai controller ready                         │
│  • Verify controller running (check PID)                        │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 3: Build Network Topology                                 │
│  • Run topology_config.py dengan sudo                           │
│  • Create 13 OpenFlow switches (s1-s13)                         │
│  • Create 19 hosts (1 broker + 18 publishers)                   │
│  • Connect switches sesuai hierarki 3-tier                      │
│  • Apply bandwidth limit (0.5 Mbps per link)                    │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 4: Configure DSCP QoS                                     │
│  • Switches connect ke controller (TCP 127.0.0.1:6633)          │
│  • Controller install flow rules (DSCP → Queue mapping)         │
│  • Configure OVS HTB queues (5 priority levels)                 │
│  • Verify QoS configuration                                     │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 5: Start MQTT Components                                  │
│  • Start Mosquitto broker on 'broker' host                      │
│  • Start subscriber_enhanced.py on 'broker' host                │
│  • Start 18 publishers (9 floors × 2 types each)                │
│  • Each publisher: Set DSCP → Connect → Publish loop            │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 6: Running Experiment                                     │
│  • Publishers send MQTT messages dengan DSCP tagging            │
│  • Switches forward berdasarkan DSCP priority                   │
│  • Subscriber collect metrics (delay, jitter, loss)             │
│  • Wait untuk DURATION detik (300 seconds = 5 minutes)          │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 7: Cleanup & Shutdown                                     │
│  • Stop all publishers (pkill -f publisher)                     │
│  • Stop subscriber (pkill -f subscriber)                        │
│  • Stop Mosquitto (pkill -f mosquitto)                          │
│  • Stop Mininet network                                         │
│  • Kill Ryu controller                                          │
│  • Generate metrics summary                                     │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  END: Results saved to run_YYYY-MM-DD_HH-MM-SS/                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Alur Lengkap Program

### Command yang Anda Jalankan:

```bash
cd /home/mqtt-sdn/scenarios/06-dscp-qos-13switches
sudo ./run_experiment.sh 300
```

**Penjelasan:**
- `sudo` → Diperlukan karena Mininet butuh root access
- `./run_experiment.sh` → Script utama untuk menjalankan experiment
- `300` → Durasi experiment dalam detik (5 menit)

---

## Fase 1: Inisialisasi & Cleanup

### File: `run_experiment.sh`

**Lokasi dalam code:**
```bash
# Lines 1-48 in run_experiment.sh
```

### Langkah-langkah:

#### 1.1. Set Environment Variables

```bash
SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Hasil: /home/mqtt-sdn/scenarios/06-dscp-qos-13switches

PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"
# Hasil: /home/mqtt-sdn

RYU_ENV="/home/aldi/ryu39"
# Virtual environment Python yang berisi Ryu framework

DURATION=${1:-300}
# Ambil argument pertama, default 300 detik jika tidak ada
```

**Mengapa ini penting?**
- `SCENARIO_DIR` → Tahu di mana scenario files berada
- `PROJECT_ROOT` → Akses shared modules dan hasil
- `RYU_ENV` → Python environment khusus untuk Ryu
- `DURATION` → Berapa lama experiment berjalan

#### 1.2. Setup Cleanup Function

```bash
cleanup() {
    echo "[CLEANUP] Stopping all components..."

    # Kill Ryu controller
    if [ ! -z "$RYU_PID" ]; then
        kill $RYU_PID 2>/dev/null || true
    fi

    # Kill MQTT components
    sudo pkill -f mosquitto 2>/dev/null || true
    sudo pkill -f publisher 2>/dev/null || true
    sudo pkill -f subscriber 2>/dev/null || true

    # Cleanup Mininet
    sudo mn -c > /dev/null 2>&1 || true
}

trap cleanup EXIT
```

**Apa yang terjadi?**
- `cleanup()` → Function untuk membersihkan semua proses
- `trap cleanup EXIT` → Otomatis jalankan cleanup saat script selesai/dibatalkan
- Membunuh semua proses MQTT dan Mininet yang masih jalan

**Mengapa perlu cleanup?**
- Experiment sebelumnya mungkin masih running
- Mininet virtual network bisa bentrok kalau tidak dibersihkan
- Port 6633 (OpenFlow) dan 1883 (MQTT) bisa masih terpakai

#### 1.3. Create Timestamped Results Directory

```bash
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
# Contoh: 2025-11-16_23-01-33

RUN_RESULTS_DIR="$PROJECT_ROOT/results/06-dscp-qos-13switches/run_$TIMESTAMP"
# Hasil: /home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-16_23-01-33

mkdir -p "$RUN_RESULTS_DIR"
cd "$RUN_RESULTS_DIR"
```

**Mengapa pakai timestamp?**
- Setiap experiment punya folder sendiri
- Tidak overwrite hasil experiment sebelumnya
- Mudah tracking hasil berdasarkan waktu

**Output di terminal:**
```
==============================================================
  SCENARIO 06: DSCP-Based QoS (13 Switches)
==============================================================

Topology: Hierarchical 3-Tier (13 switches, 19 hosts)
Duration: 300 seconds

Results will be saved to: /home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-16_23-01-33
```

---

## Fase 2: Start Ryu Controller

### File: `run_experiment.sh` (lines 50-69)

### Langkah-langkah:

#### 2.1. Activate Virtual Environment

```bash
source "$RYU_ENV/bin/activate"
# Activate Python virtual environment di /home/aldi/ryu39
```

**Mengapa butuh virtual environment?**
- Ryu framework butuh Python 3.9 dengan dependencies khusus
- Isolasi dari Python system agar tidak bentrok
- Virtual environment punya versi library yang tepat

#### 2.2. Start Ryu Manager

```bash
"$RYU_ENV/bin/python3.9" -u "$RYU_ENV/bin/ryu-manager" \
    "$SCENARIO_DIR/controller_dscp.py" \
    ryu.app.ofctl_rest \
    > "$PROJECT_ROOT/logs/ryu.log" 2>&1 &

RYU_PID=$!
```

**Breakdown perintah:**
- `python3.9 -u` → Jalankan Python dengan unbuffered output
- `ryu-manager` → Program utama Ryu controller
- `controller_dscp.py` → Controller kita (DSCP-based QoS)
- `ryu.app.ofctl_rest` → REST API untuk monitoring (port 8080)
- `> logs/ryu.log 2>&1` → Redirect output ke log file
- `&` → Run di background
- `$!` → Simpan Process ID

**Output di terminal:**
```
[1/2] Starting Ryu Controller...
  ✓ Controller started (PID: 123456)
```

#### 2.3. Wait for Controller Initialization

```bash
sleep 3
```

**Mengapa wait 3 detik?**
- Controller butuh waktu untuk bind ke port 6633
- Load Python modules dan initialize
- Siapkan OpenFlow listener

#### 2.4. Verify Controller Running

```bash
if ! ps -p $RYU_PID > /dev/null; then
    echo "[ERROR] Controller failed to start!"
    echo "Check: $PROJECT_ROOT/logs/ryu.log"
    exit 1
fi
```

**Apa yang dicek?**
- Apakah process dengan PID tersebut masih jalan?
- Jika sudah mati → controller gagal start → exit dengan error
- User diminta cek log file untuk detail error

**Isi controller_dscp.py yang berjalan:**

```python
# File: controller_dscp.py

class DSCPController(app_manager.RyuApp):

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Dipanggil saat switch connect ke controller"""

        # Install flow rules untuk 5 DSCP levels:
        # 1. DSCP 46 → Queue 1 (60-80% bandwidth)
        # 2. DSCP 34 → Queue 2 (45-60% bandwidth)
        # 3. DSCP 26 → Queue 3 (30-45% bandwidth)
        # 4. DSCP 10 → Queue 4 (15-30% bandwidth)
        # 5. DSCP 0  → Queue 5 (5-15% bandwidth)
```

**Flow rules yang di-install:**

| Priority | Match | Action | Purpose |
|----------|-------|--------|---------|
| 100 | ARP packets | NORMAL | IP resolution |
| 60 | IP, DSCP=46 | Queue 1 + NORMAL | Very High priority |
| 55 | IP, DSCP=34 | Queue 2 + NORMAL | High priority |
| 50 | IP, DSCP=26 | Queue 3 + NORMAL | Medium priority |
| 45 | IP, DSCP=10 | Queue 4 + NORMAL | Low priority |
| 40 | IP, DSCP=0 | Queue 5 + NORMAL | Best effort |
| 30 | Default | NORMAL | Catch-all |

**Catatan penting:**
- Controller BELUM melakukan apa-apa di fase ini
- Hanya listen di port 6633, menunggu switch connect
- Flow rules akan di-install saat switch connect (Fase 4)

---

## Fase 3: Build Network Topology

### File: `topology_config.py`

**Dipanggil oleh:**
```bash
sudo python3 "$SCENARIO_DIR/topology_config.py" --duration "$DURATION"
```

### Langkah-langkah:

#### 3.1. Initialize Mininet

**Lokasi dalam code:**
```python
# topology_config.py, lines 73-79

if ENABLE_BANDWIDTH_LIMIT:
    self.net = Mininet(controller=RemoteController, autoSetMacs=True, link=TCLink)
else:
    self.net = Mininet(controller=RemoteController, autoSetMacs=True)
```

**Apa yang terjadi?**
- Create Mininet network object
- `RemoteController` → Akan connect ke Ryu di 127.0.0.1:6633
- `autoSetMacs=True` → Auto-assign MAC addresses
- `TCLink` → Support traffic control (bandwidth limit)

**Output di terminal:**
```
*** Bandwidth limiting ENABLED: 0.5 Mbps per link
*** Building Hierarchical 3-Tier Topology with DSCP QoS (13 switches)
```

#### 3.2. Add Controller

```python
# Line 88-89
c0 = self.net.addController('c0', controller=RemoteController,
                             ip='127.0.0.1', port=6633)
```

**Apa yang terjadi?**
- Mininet tahu controller ada di 127.0.0.1:6633
- Semua switch nanti akan connect ke sini
- Ini BELUM actual connection, baru "rencana"

#### 3.3. Create Core Switch (Layer 1)

```python
# Lines 94-96
s1 = self.net.addSwitch('s1', protocols='OpenFlow13')
h_broker = self.net.addHost('broker', ip='10.0.0.1/16')
self.net.addLink(h_broker, s1, bw=LINK_BANDWIDTH_MBPS)  # 0.5 Mbps
```

**Topologi yang terbentuk:**
```
┌──────────┐
│  broker  │  10.0.0.1/16
│ (host)   │
└────┬─────┘
     │ 0.5 Mbps
┌────▼─────┐
│    s1    │  Core Switch
│ (switch) │
└──────────┘
```

**Penjelasan:**
- `s1` → Switch utama (core)
- `broker` → Host yang akan jalankan Mosquitto + Subscriber
- `/16` subnet → Bisa communicate dengan 10.0.x.x (semua floor)
- `bw=0.5` → Bandwidth limit 0.5 Mbps (create congestion!)

#### 3.4. Create Aggregation Switches (Layer 2)

```python
# Lines 109-121
s2 = self.net.addSwitch('s2', protocols='OpenFlow13')  # Floor 1
s3 = self.net.addSwitch('s3', protocols='OpenFlow13')  # Floor 2
s4 = self.net.addSwitch('s4', protocols='OpenFlow13')  # Floor 3

# Connect ke core
self.net.addLink(s2, s1, bw=0.5)
self.net.addLink(s3, s1, bw=0.5)
self.net.addLink(s4, s1, bw=0.5)
```

**Topologi yang terbentuk:**
```
                    ┌──────┐
                    │  s1  │ CORE
                    └───┬──┘
                        │
          ┌─────────────┼─────────────┐
          │ 0.5Mbps     │ 0.5Mbps     │ 0.5Mbps
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │     │  s3   │     │  s4   │  AGGREGATION
      │Floor 1│     │Floor 2│     │Floor 3│
      └───────┘     └───────┘     └───────┘
```

#### 3.5. Create Edge Switches (Layer 3)

```python
# Lines 129-156
# Floor 1: s5, s6, s7
for i in range(5, 8):
    sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
    self.net.addLink(sw, s2, bw=0.5)  # Connect to Floor 1 aggregation

# Floor 2: s8, s9, s10
for i in range(8, 11):
    sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
    self.net.addLink(sw, s3, bw=0.5)  # Connect to Floor 2 aggregation

# Floor 3: s11, s12, s13
for i in range(11, 14):
    sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
    self.net.addLink(sw, s4, bw=0.5)  # Connect to Floor 3 aggregation
```

**Topologi lengkap:**
```
                        ┌──────┐
                        │  s1  │ CORE
                        └───┬──┘
              ┌─────────────┼─────────────┐
          ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
          │  s2   │     │  s3   │     │  s4   │  AGGREGATION
          └───┬───┘     └───┬───┘     └───┬───┘
              │             │             │
      ┌───┬───┬───┐ ┌───┬───┬───┐ ┌───┬───┬───┐
      │   │   │   │ │   │   │   │ │   │   │   │
     s5  s6  s7   s8  s9 s10   s11 s12 s13  EDGE
```

**Output di terminal:**
```
*** Adding Core Switch
*** Adding Aggregation Switches
*** Adding Edge Switches and Publishers
```

#### 3.6. Add Publishers (18 hosts)

```python
# Lines 162-260
# Floor 1: 10.0.1.x/16
for idx, sw in enumerate([s5, s6, s7]):
    # Anomaly publisher
    h_anomaly = self.net.addHost(f'f1r{idx+1}a', ip=f'10.0.1.{host_id}/16')
    self.net.addLink(h_anomaly, sw, bw=0.5)

    # Normal publisher
    h_normal = self.net.addHost(f'f1r{idx+1}n', ip=f'10.0.1.{host_id+1}/16')
    self.net.addLink(h_normal, sw, bw=0.5)

# Floor 2: 10.0.2.x/16 (sama dengan Floor 1)
# Floor 3: 10.0.3.x/16 (sama dengan Floor 1)
```

**Penjelasan penamaan:**
- `f1r1a` → Floor 1, Room 1, Anomaly
- `f1r1n` → Floor 1, Room 1, Normal
- `f2r3a` → Floor 2, Room 3, Anomaly
- dll...

**Distribusi publishers:**

| Floor | Switch | Anomaly Publisher | Normal Publisher | Subnet |
|-------|--------|------------------|------------------|--------|
| 1 | s5 (Room 1) | f1r1a (10.0.1.1) | f1r1n (10.0.1.2) | 10.0.1.x/16 |
| 1 | s6 (Room 2) | f1r2a (10.0.1.3) | f1r2n (10.0.1.4) | 10.0.1.x/16 |
| 1 | s7 (Room 3) | f1r3a (10.0.1.5) | f1r3n (10.0.1.6) | 10.0.1.x/16 |
| 2 | s8 (Room 1) | f2r1a (10.0.2.1) | f2r1n (10.0.2.2) | 10.0.2.x/16 |
| 2 | s9 (Room 2) | f2r2a (10.0.2.3) | f2r2n (10.0.2.4) | 10.0.2.x/16 |
| 2 | s10 (Room 3) | f2r3a (10.0.2.5) | f2r3n (10.0.2.6) | 10.0.2.x/16 |
| 3 | s11 (Room 1) | f3r1a (10.0.3.1) | f3r1n (10.0.3.2) | 10.0.3.x/16 |
| 3 | s12 (Room 2) | f3r2a (10.0.3.3) | f3r2n (10.0.3.4) | 10.0.3.x/16 |
| 3 | s13 (Room 3) | f3r3a (10.0.3.5) | f3r3n (10.0.3.6) | 10.0.3.x/16 |

**Total:** 9 switches × 2 publishers = **18 publishers**

**Output di terminal:**
```
*** Topology built: 13 switches, 18 publishers
*** Configuring hosts
broker f1r1a f1r1n f1r2a f1r2n f1r3a f1r3n f2r1a f2r1n ...
```

#### 3.7. Start Network

```python
# Line 326
self.net.start()
```

**Apa yang terjadi di sini? (PENTING!)**

1. **Mininet creates virtual network:**
   - 13 virtual switches (menggunakan Open vSwitch)
   - 19 virtual hosts (menggunakan network namespaces)
   - Virtual links dengan bandwidth limit

2. **Switches connect ke controller:**
   - Semua 13 switches buka connection TCP ke 127.0.0.1:6633
   - Ryu controller detect connection baru
   - **Trigger `switch_features_handler` di controller**
   - Controller install flow rules ke setiap switch

3. **Network namespace isolation:**
   - Setiap host punya network stack sendiri
   - Publisher bisa bind ke IP berbeda (10.0.1.1, 10.0.1.2, dst)
   - Semua dalam satu mesin, tapi isolated

**Output di terminal:**
```
*** Starting controller
c0
*** Starting 13 switches
s1 (0.50Mbit) s2 (0.50Mbit) s3 (0.50Mbit) ... s13 (0.50Mbit) ...
*** Network started successfully
*** Total switches: 13 (1 core + 3 aggregation + 9 edge)
*** Total publishers: 18
*** Network depth: 3 hops (edge → agg → core)
```

#### 3.8. Wait for Network Stabilization

```python
# Line 333
time.sleep(5)
```

**Mengapa wait 5 detik?**
- Switches butuh waktu untuk connect ke controller
- OpenFlow handshake perlu beberapa detik
- Flow rules perlu di-install
- Network perlu stabil sebelum QoS configuration

---

## Fase 4: Configure DSCP QoS

### File: `topology_config.py` (lines 265-319)

### Langkah-langkah:

#### 4.1. Flow Rules Installation (Oleh Controller)

**Terjadi saat switches connect (otomatis):**

```python
# Dalam controller_dscp.py

def switch_features_handler(self, ev):
    """Dipanggil untuk SETIAP switch yang connect"""

    datapath = ev.msg.datapath  # Switch yang baru connect
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser

    # 1. Install ARP rule (priority 100)
    match_arp = parser.OFPMatch(eth_type=0x0806)
    actions_arp = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
    self.add_flow(datapath, 100, match_arp, actions_arp)

    # 2. Install DSCP 46 rule (priority 60)
    match_ef = parser.OFPMatch(eth_type=0x0800, ip_dscp=46)
    actions_ef = [
        parser.OFPActionSetQueue(1),  # ← Assign ke Queue 1
        parser.OFPActionOutput(ofproto.OFPP_NORMAL)
    ]
    self.add_flow(datapath, 60, match_ef, actions_ef)

    # 3. Install DSCP 34 rule (priority 55)
    match_af41 = parser.OFPMatch(eth_type=0x0800, ip_dscp=34)
    actions_af41 = [
        parser.OFPActionSetQueue(2),  # ← Assign ke Queue 2
        parser.OFPActionOutput(ofproto.OFPP_NORMAL)
    ]
    self.add_flow(datapath, 55, match_af41, actions_af41)

    # ... Lanjut untuk DSCP 26, 10, 0 (Queue 3, 4, 5)

    # 7. Default forwarding (priority 30)
    match_default = parser.OFPMatch()
    actions_default = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
    self.add_flow(datapath, 30, match_default, actions_default)
```

**Penjelasan:**
- Setiap switch yang connect → trigger handler ini
- Install 7 flow rules per switch
- Total: 13 switches × 7 rules = **91 flow rules**

**Flow table contoh di switch s1:**

```
cookie=0x0, duration=..., table=0, n_packets=..., n_bytes=...,
  priority=100, arp
  actions=NORMAL

cookie=0x0, duration=..., table=0, n_packets=..., n_bytes=...,
  priority=60, ip, nw_tos=184
  actions=set_queue:1, NORMAL

cookie=0x0, duration=..., table=0, n_packets=..., n_bytes=...,
  priority=55, ip, nw_tos=136
  actions=set_queue:2, NORMAL

...
```

**Catatan:**
- `nw_tos=184` → DSCP 46 dalam format TOS (46 << 2 = 184)
- `set_queue:1` → Assign packet ke queue 1
- `NORMAL` → Forward seperti L2 switch (MAC learning)

#### 4.2. OVS Queue Configuration

**Dipanggil di topology_config.py:**

```python
# Line 336-337
if ENABLE_BANDWIDTH_LIMIT:
    self.configure_ovs_queues()
```

**Apa yang dilakukan configure_ovs_queues()?**

```python
def configure_ovs_queues(self):
    # Untuk setiap switch (s1 sampai s13)
    for switch_name in ['s1', 's2', ..., 's13']:

        # Untuk setiap port di switch
        ports = ovs-vsctl list-ports switch_name

        for port in ports:
            # Hitung bandwidth allocation
            max_rate = 0.5 * 1000000  # 500,000 bps

            q1_min = int(max_rate * 0.60)  # 300,000 bps (60%)
            q1_max = int(max_rate * 0.80)  # 400,000 bps (80%)

            q2_min = int(max_rate * 0.45)  # 225,000 bps (45%)
            q2_max = int(max_rate * 0.60)  # 300,000 bps (60%)

            # ... untuk q3, q4, q5

            # Install QoS ke port
            ovs-vsctl -- set port PORT qos=@newqos \
                -- --id=@newqos create qos type=linux-htb \
                    other-config:max-rate=500000 \
                    queues:1=@q1 queues:2=@q2 queues:3=@q3 \
                    queues:4=@q4 queues:5=@q5 \
                -- --id=@q1 create queue \
                    other-config:min-rate=300000 \
                    other-config:max-rate=400000 \
                -- --id=@q2 create queue \
                    other-config:min-rate=225000 \
                    other-config:max-rate=300000 \
                # ... dst untuk q3, q4, q5
```

**Penjelasan HTB (Hierarchical Token Bucket):**

```
┌─────────────────────────────────────────────────────────┐
│  Link Capacity: 500 Kbps (0.5 Mbps)                    │
├─────────────────────────────────────────────────────────┤
│  Queue 1 (DSCP 46): 300-400 Kbps  [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓]   │
│  Queue 2 (DSCP 34): 225-300 Kbps  [▓▓▓▓▓▓▓▓▓▓▓▓]       │
│  Queue 3 (DSCP 26): 150-225 Kbps  [▓▓▓▓▓▓▓▓]           │
│  Queue 4 (DSCP 10):  75-150 Kbps  [▓▓▓▓]               │
│  Queue 5 (DSCP 0):   25-75  Kbps  [▓▓]                 │
└─────────────────────────────────────────────────────────┘
```

**Cara kerja:**
- **min-rate:** Bandwidth minimum guaranteed
- **max-rate:** Bandwidth maximum (bisa naik kalau ada unused bandwidth)
- **Saat congested:** Queue 1 dapat 60%, Queue 5 dapat 5%
- **Saat idle:** Queue bisa gunakan bandwidth lebih dari min-rate

**Output di terminal:**
```
*** Configuring OVS QoS Queues (5 priority levels)...
  ✓ s1:s1-eth1
      Q1 (DSCP 46): 300-400 Kbps
      Q2 (DSCP 34): 225-300 Kbps
      Q3 (DSCP 26): 150-225 Kbps
      Q4 (DSCP 10): 75-150 Kbps
      Q5 (DSCP 0):  25-75 Kbps
  ✓ s1:s1-eth2
      ...
  (Lanjut untuk semua switch dan port)
*** OVS QoS configuration complete (5 queues)
```

**Total konfigurasi:**
- 13 switches
- ~3-4 ports per switch (rata-rata)
- ~40 port total
- Semua port punya 5 queues
- Total: **~200 queue objects** di OVS

---

## Fase 5: Start MQTT Components

### File: `topology_config.py` (lines 395-455)

### Langkah-langkah:

#### 5.1. Start Mosquitto Broker

```python
# Line 407
h_broker = self.net.get('broker')
h_broker.cmd(f'mosquitto -c {CONFIG_DIR}/mosquitto.conf -d')
```

**Apa yang terjadi?**
- Jalankan Mosquitto MQTT broker di host 'broker' (IP 10.0.0.1)
- `-c mosquitto.conf` → Use config file (set port 1883, persistence, etc.)
- `-d` → Run as daemon (background)

**Mosquitto config (`mosquitto.conf`):**
```
port 1883
listener 1883 0.0.0.0
allow_anonymous true
persistence false
```

**Mengapa di host 'broker'?**
- Host 'broker' terhubung ke core switch (s1)
- Semua publisher bisa reach 10.0.0.1 (subnet /16)
- Centralized location untuk collect data

**Output di terminal:**
```
*** Starting MQTT Broker on Core Switch
```

**Cek Mosquitto running:**
```bash
# Dalam namespace 'broker'
ps aux | grep mosquitto
# mosquitto -c /home/mqtt-sdn/shared/config/mosquitto.conf -d
```

#### 5.2. Start Enhanced Subscriber

```python
# Lines 412-421
env_vars = (
    f'ENABLE_BANDWIDTH_LIMIT=True '
    f'LINK_BANDWIDTH_MBPS=0.5 '
    f'ENABLE_QOS_QUEUES=True '
    f'SCENARIO_NAME="06-dscp-qos-13switches" '
    f'TOPOLOGY_TYPE="DSCP Hierarchical 3-Tier (13 switches, 19 hosts)" '
    f'NUM_SWITCHES=13 '
    f'NUM_PUBLISHERS=18 '
)

h_broker.cmd(f'{env_vars}python3 {MQTT_DIR}/subscriber_enhanced.py > {LOG_DIR}/subscriber.log 2>&1 &')
```

**Apa yang dilakukan subscriber_enhanced.py?**

```python
# subscriber_enhanced.py (simplified)

import paho.mqtt.client as mqtt
import time
import csv

# Collect metrics
metrics = {
    'anomaly': [],  # List of (delay, jitter, seq)
    'normal': []
}

def on_message(client, userdata, msg):
    """Dipanggil setiap kali terima MQTT message"""

    # Parse message
    payload = json.loads(msg.payload)

    # Calculate delay
    send_time = payload['timestamp']
    receive_time = time.time()
    delay = (receive_time - send_time) * 1000  # ms

    # Calculate jitter
    if last_delay is not None:
        jitter = abs(delay - last_delay)

    # Save ke CSV
    writer.writerow([
        payload['device'],
        payload['type'],
        payload['dscp'],
        payload['seq'],
        delay,
        jitter,
        receive_time
    ])

    # Save to memory untuk summary
    metrics[payload['type']].append({
        'delay': delay,
        'jitter': jitter,
        'seq': payload['seq']
    })

# Subscribe to topic
client.connect('127.0.0.1', 1883)  # Localhost karena running di 'broker'
client.subscribe('iot/data')
client.on_message = on_message
client.loop_forever()
```

**Apa yang di-collect?**
- **End-to-End Delay:** Waktu dari publish sampai receive
- **Jitter:** Variasi delay antar message
- **Sequence Number:** Untuk detect packet loss
- **DSCP Value:** Untuk grouping by priority
- **Timestamp:** Untuk analysis

**Output files:**
- `mqtt_metrics_log.csv` → Detail per message
- `metrics_summary.txt` → Aggregated statistics (saat shutdown)

**Output di terminal:**
```
*** Starting Enhanced Subscriber on Core
```

#### 5.3. Start Publishers (18 publishers)

```python
# Lines 423-455
for idx, pub_info in enumerate(self.publishers):
    host = pub_info['host']      # Contoh: f1r1a
    pub_type = pub_info['type']  # 'anomaly' atau 'normal'
    floor = pub_info['floor']    # 1, 2, atau 3
    room = pub_info['room']      # 1, 2, atau 3

    device_name = f"sensor_f{floor}r{room}_{pub_type}"
    # Contoh: sensor_f1r1_anomaly

    # Pilih publisher script
    if pub_type == 'anomaly':
        script = f'{SCENARIO_DIR}/publisher_dscp46_veryhigh.py'
    else:
        script = f'{SCENARIO_DIR}/publisher_dscp0_besteffort.py'

    # Start publisher
    host.cmd(f'DEVICE={device_name} BROKER_IP=10.0.0.1 MSG_RATE=50 '
             f'python3 {script} > {LOG_DIR}/publisher_{device_name}.log 2>&1 &')

    # Stagger starts (avoid thundering herd)
    if idx % 3 == 0:
        time.sleep(1)
```

**Detail publisher startup:**

**Contoh untuk f1r1a (Floor 1, Room 1, Anomaly):**

1. **Environment variables:**
   ```bash
   DEVICE=sensor_f1r1_anomaly
   BROKER_IP=10.0.0.1
   MSG_RATE=50
   ```

2. **Script yang dijalankan:**
   ```bash
   python3 publisher_dscp46_veryhigh.py
   ```

3. **Apa yang dilakukan publisher?**

```python
# publisher_dscp46_veryhigh.py (thin wrapper)

from shared.mqtt.publisher_dscp import run_publisher
from shared.mqtt.dscp_config import DSCP_VERY_HIGH

run_publisher(
    dscp_value=DSCP_VERY_HIGH,  # 46
    traffic_type='anomaly'       # Value 50-100
)
```

4. **Dalam run_publisher() - Generic Publisher:**

```python
# shared/mqtt/publisher_dscp.py

def run_publisher(dscp_value, traffic_type):
    # 1. Create MQTT client
    client = mqtt.Client(callback_api_version=VERSION2)

    # 2. Configure DSCP on socket
    client.on_socket_open = create_dscp_callback(
        dscp_value=46,
        device_name='sensor_f1r1_anomaly'
    )

    # 3. Connect to broker
    client.connect('10.0.0.1', 1883)

    # 4. Publish loop
    while True:
        payload = {
            "device": "sensor_f1r1_anomaly",
            "type": "anomaly",
            "dscp": 46,
            "priority": "very_high",
            "value": random.uniform(50, 100),
            "timestamp": time.time(),
            "seq": sequence_number
        }

        client.publish("iot/data", json.dumps(payload), qos=1)
        sequence_number += 1
        time.sleep(1.0 / 50)  # 50 msg/s = sleep 0.02s
```

5. **DSCP Configuration (PENTING!):**

```python
# Dalam create_dscp_callback():

def on_socket_open(client, userdata, sock):
    # Convert DSCP to TOS
    ip_tos = 46 << 2  # 184 (0xb8)

    # Set socket option
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, ip_tos)

    print(f"[DSCP] Socket configured with DSCP 46")
```

**Apa artinya setsockopt?**
- Set IP header TOS byte = 184 (0xb8)
- TOS byte format: `[DSCP 6 bits][ECN 2 bits]`
- DSCP 46 (binary: 101110) → TOS 184 (binary: 10111000)
- **SEMUA packet dari socket ini akan punya DSCP 46**

**Publisher startup sequence:**

| Time | Publisher | Floor | Room | Type | DSCP | IP Address |
|------|-----------|-------|------|------|------|------------|
| 0s | f1r1a | 1 | 1 | anomaly | 46 | 10.0.1.1 |
| 0s | f1r1n | 1 | 1 | normal | 0 | 10.0.1.2 |
| 0s | f1r2a | 1 | 2 | anomaly | 46 | 10.0.1.3 |
| 1s | f1r2n | 1 | 2 | normal | 0 | 10.0.1.4 |
| ... | ... | ... | ... | ... | ... | ... |
| 6s | f3r3n | 3 | 3 | normal | 0 | 10.0.3.6 |

**Stagger explanation:**
- `if idx % 3 == 0: time.sleep(1)`
- Setiap 3 publishers → wait 1 detik
- Avoid semua 18 publishers connect bersamaan (thundering herd)
- Distribute load saat connection establishment

**Output di terminal:**
```
*** Starting 18 Publishers with DSCP tagging
*** All MQTT components started
```

**Cek publishers running:**
```bash
ps aux | grep publisher
# python3 publisher_dscp46_veryhigh.py (f1r1a)
# python3 publisher_dscp0_besteffort.py (f1r1n)
# ... (18 processes)
```

---

## Fase 6: Running Experiment

### File: `topology_config.py` (lines 457-462)

### Apa yang Terjadi:

```python
# Line 457-462
if duration:
    info(f'*** Running for {duration} seconds...\n')
    time.sleep(duration)  # Wait 300 seconds
    info('*** Stopping MQTT components\n')
    self.stop_mqtt()
```

**Selama 300 detik (5 menit):**

#### 6.1. Publishers Mengirim Messages

**Publisher anomaly (DSCP 46):**
```
[Floor 1, Room 1, Anomaly]
Sending at 50 msg/s:

  t=0.00s → {"device": "sensor_f1r1_anomaly", "dscp": 46, "value": 78.5, "seq": 0}
  t=0.02s → {"device": "sensor_f1r1_anomaly", "dscp": 46, "value": 92.1, "seq": 1}
  t=0.04s → {"device": "sensor_f1r1_anomaly", "dscp": 46, "value": 65.3, "seq": 2}
  ...

Total dalam 5 menit: 50 msg/s × 300s = 15,000 messages per publisher
```

**Publisher normal (DSCP 0):**
```
[Floor 1, Room 1, Normal]
Sending at 50 msg/s:

  t=0.00s → {"device": "sensor_f1r1_normal", "dscp": 0, "value": 25.2, "seq": 0}
  t=0.02s → {"device": "sensor_f1r1_normal", "dscp": 0, "value": 28.7, "seq": 1}
  ...
```

**Total traffic:**
- 18 publishers × 50 msg/s = **900 messages per second**
- Each message ~150 bytes
- Total: 900 × 150 = **135,000 bytes/s = 1,080,000 bps = 1.08 Mbps**

**Bandwidth bottleneck:**
- Link capacity: **0.5 Mbps (500 Kbps)**
- Total load: **1.08 Mbps**
- **Utilization: 216%** (highly congested!)

**Ini yang create priority differentiation!**

#### 6.2. Packet Flow Through Network

**Contoh: Message dari f1r1a (Floor 1, Room 1, Anomaly)**

**Step 1: Publisher creates packet**
```
┌─────────────────────────────────────────────────┐
│ f1r1a (10.0.1.1)                                │
│ ┌─────────────────────────────────────────────┐ │
│ │ IP Header:                                  │ │
│ │   src: 10.0.1.1                             │ │
│ │   dst: 10.0.0.1 (broker)                    │ │
│ │   TOS: 0xb8 (DSCP 46) ← Set by setsockopt  │ │
│ │ TCP Header:                                 │ │
│ │   dst_port: 1883 (MQTT)                     │ │
│ │ Payload:                                    │ │
│ │   {"device": "sensor_f1r1_anomaly", ...}    │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Step 2: Masuk ke switch s5 (Edge)**
```
┌─────────────────────────────────────────────────┐
│ s5 (Edge Switch - Floor 1, Room 1)              │
│                                                 │
│ 1. Packet masuk dari f1r1a                      │
│ 2. OpenFlow match flow rules:                   │
│    Priority 60: Match! (ip, nw_tos=184)         │
│ 3. Action: set_queue:1 + NORMAL                 │
│ 4. Assign to Queue 1 (300-400 Kbps)             │
│ 5. MAC learning: f1r1a di port 1                │
│ 6. Forward ke port menuju s2 (aggregation)      │
│                                                 │
│ Queue Status:                                   │
│ Queue 1 (DSCP 46): [▓▓▓▓▓] 5 packets waiting   │
│ Queue 2 (DSCP 34): [▓] 1 packet                 │
│ Queue 5 (DSCP 0):  [▓▓▓▓▓▓▓▓▓] 20 packets ← Congested!│
└─────────────────────────────────────────────────┘
```

**Step 3: Masuk ke switch s2 (Aggregation - Floor 1)**
```
┌─────────────────────────────────────────────────┐
│ s2 (Aggregation Switch - Floor 1)               │
│                                                 │
│ 1. Packet masuk dari s5                         │
│ 2. OpenFlow match: DSCP 46 → Queue 1            │
│ 3. MAC learning: Broker ada di uplink (s1)      │
│ 4. Forward ke port menuju s1 (core)             │
│                                                 │
│ Queue 1: Prioritized, short wait                │
└─────────────────────────────────────────────────┘
```

**Step 4: Masuk ke switch s1 (Core)**
```
┌─────────────────────────────────────────────────┐
│ s1 (Core Switch)                                │
│                                                 │
│ 1. Packet masuk dari s2                         │
│ 2. OpenFlow match: DSCP 46 → Queue 1            │
│ 3. MAC learning: Broker di port broker-eth0     │
│ 4. Forward langsung ke broker                   │
│                                                 │
│ Queue 1: Fast forwarding                        │
└─────────────────────────────────────────────────┘
```

**Step 5: Broker receives packet**
```
┌─────────────────────────────────────────────────┐
│ broker (10.0.0.1)                               │
│                                                 │
│ 1. Mosquitto receives MQTT packet               │
│ 2. Parse MQTT PUBLISH message                   │
│ 3. Forward to subscriber (localhost)            │
│ 4. Subscriber calculates delay:                 │
│    delay = receive_time - send_time             │
│    delay = 0.0035s = 3.5ms ← Low delay!         │
└─────────────────────────────────────────────────┘
```

**Comparison: Normal packet (DSCP 0) from f1r1n**

**Same path BUT:**
- Assigned to **Queue 5** (25-75 Kbps)
- Queue 5 congested dengan 50+ packets waiting
- Delay = 15,000ms = **15 seconds** ← High delay!

**Priority ratio: 15000ms / 3.5ms = ~4285x slower!**

#### 6.3. Subscriber Collects Metrics

**Setiap message yang diterima:**

```python
# subscriber_enhanced.py

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload)

    # Calculate delay
    send_time = payload['timestamp']  # From publisher
    receive_time = time.time()         # Now
    delay = (receive_time - send_time) * 1000  # Convert to ms

    # Calculate jitter
    if self.last_delay[payload['type']] is not None:
        last = self.last_delay[payload['type']]
        jitter = abs(delay - last)
    else:
        jitter = 0

    self.last_delay[payload['type']] = delay

    # Save to CSV
    self.writer.writerow([
        payload['device'],      # sensor_f1r1_anomaly
        payload['type'],        # anomaly
        payload['dscp'],        # 46
        payload['priority'],    # very_high
        payload['value'],       # 78.5
        payload['seq'],         # 123
        send_time,              # 1700000000.123
        receive_time,           # 1700000000.126
        delay,                  # 3.5
        jitter                  # 0.8
    ])

    # Track for summary
    self.metrics[payload['type']].append({
        'delay': delay,
        'jitter': jitter,
        'seq': payload['seq']
    })
```

**CSV output (mqtt_metrics_log.csv):**
```csv
device,type,dscp,priority,value,seq,send_time,receive_time,delay_ms,jitter_ms
sensor_f1r1_anomaly,anomaly,46,very_high,78.5,0,1700000000.000,1700000000.003,3.5,0.0
sensor_f1r1_anomaly,anomaly,46,very_high,92.1,1,1700000000.020,1700000000.024,4.0,0.5
sensor_f1r1_normal,normal,0,best_effort,25.2,0,1700000000.000,1700000015.123,15123.0,0.0
sensor_f1r1_normal,normal,0,best_effort,28.7,1,1700000000.020,1700000030.456,30436.0,15313.0
...
```

**Metrics accumulation:**
- Anomaly messages: ~135,000 messages (9 publishers × 15,000)
- Normal messages: ~135,000 messages (9 publishers × 15,000)
- Total: **~270,000 messages** dalam 5 menit

**Real-time stats (estimated):**

| Metric | Anomaly (DSCP 46) | Normal (DSCP 0) | Ratio |
|--------|------------------|-----------------|-------|
| Avg Delay | 3-5 ms | 10,000-15,000 ms | 3000x |
| Min Delay | 0.5 ms | 5 ms | 10x |
| Max Delay | 50 ms | 30,000 ms | 600x |
| Jitter | 1-2 ms | 5,000 ms | 2500x |
| Packet Loss | 0% | 0% | - |

**Output di terminal (from publishers):**
```
[ANOMALY/DSCP46] seq=00123 value= 78.50 ✓
[ANOMALY/DSCP46] seq=00124 value= 92.10 ✓
[NORMAL/DSCP0]   seq=00045 value= 25.20 ✓
[NORMAL/DSCP0]   seq=00046 value= 28.70 ✓
...
```

**Progress:**
```
*** Running for 300 seconds...
[Elapsed: 60s / 300s] ...
[Elapsed: 120s / 300s] ...
[Elapsed: 180s / 300s] ...
[Elapsed: 240s / 300s] ...
[Elapsed: 300s / 300s] Done!
```

---

## Fase 7: Cleanup & Shutdown

### File: Multiple locations

### Langkah-langkah:

#### 7.1. Stop MQTT Components

**Dipanggil oleh topology_config.py:**

```python
# Line 462
self.stop_mqtt()
```

**Apa yang dilakukan stop_mqtt()?**

```python
def stop_mqtt(self):
    # 1. Stop all publishers
    for pub_info in self.publishers:
        host = pub_info['host']
        host.cmd('pkill -f publisher')

    # 2. Stop subscriber
    h_broker = self.net.get('broker')
    h_broker.cmd('pkill -TERM -f subscriber_enhanced')
    time.sleep(3)  # Wait for graceful shutdown
    h_broker.cmd('pkill -f subscriber_enhanced')  # Force if still running

    # 3. Stop mosquitto
    h_broker.cmd('pkill -f mosquitto')

    time.sleep(2)
```

**Penjelasan:**
- `pkill -f publisher` → Kill semua proses yang ada "publisher" dalam command
- `-TERM` → Send SIGTERM (graceful shutdown)
- Wait 3 detik → Beri waktu untuk flush data
- Force kill jika masih running
- Stop mosquitto terakhir

**Output di terminal:**
```
*** Stopping MQTT components
```

**Subscriber shutdown sequence:**

1. **Receive SIGTERM signal**
   ```python
   # In subscriber_enhanced.py

   signal.signal(signal.SIGTERM, signal_handler)

   def signal_handler(sig, frame):
       print("\n[SHUTDOWN] Received termination signal")
       shutdown()
   ```

2. **Flush metrics to CSV**
   ```python
   def shutdown():
       # Close CSV file
       self.csv_file.close()

       # Generate summary
       generate_metrics_summary()

       # Disconnect MQTT
       self.client.disconnect()
   ```

3. **Generate metrics_summary.txt**
   ```python
   def generate_metrics_summary():
       # Calculate statistics
       anomaly_delays = [m['delay'] for m in metrics['anomaly']]
       normal_delays = [m['delay'] for m in metrics['normal']]

       # Write summary
       with open('metrics_summary.txt', 'w') as f:
           f.write("ANOMALY:\n")
           f.write(f"  Messages Received : {len(anomaly_delays)}\n")
           f.write(f"  Avg Delay         : {mean(anomaly_delays):.2f} ms\n")
           f.write(f"  Min Delay         : {min(anomaly_delays):.2f} ms\n")
           f.write(f"  Max Delay         : {max(anomaly_delays):.2f} ms\n")
           # ... more stats

           f.write("\nNORMAL:\n")
           # ... same for normal
   ```

**Generated files:**
```
/home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-16_23-01-33/
├── mqtt_metrics_log.csv       (~50 MB, 270,000 rows)
└── metrics_summary.txt         (~2 KB, aggregated stats)
```

#### 7.2. Stop Mininet Network

```python
# topology_config.py, line 481
if self.net:
    info('*** Stopping network\n')
    self.net.stop()
```

**Apa yang dilakukan net.stop()?**

```python
# Mininet internal

def stop():
    # 1. Stop all hosts
    for host in self.hosts:
        host.terminate()  # Kill all processes in namespace

    # 2. Stop all switches
    for switch in self.switches:
        switch.stop()  # Disconnect from controller, cleanup flows

    # 3. Delete links
    for link in self.links:
        link.delete()  # Remove virtual interfaces

    # 4. Cleanup network namespaces
    for host in self.hosts:
        delete_namespace(host.name)
```

**Output di terminal:**
```
*** Stopping network
*** Stopping 1 controllers
c0
*** Stopping 31 links
...............................
*** Stopping 13 switches
s1 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 s12 s13
*** Stopping 19 hosts
broker f1r1a f1r1n f1r2a f1r2n f1r3a f1r3n f2r1a f2r1n f2r2a f2r2n f2r3a f2r3n f3r1a f3r1n f3r2a f3r2n f3r3a f3r3n
*** Done
```

#### 7.3. Cleanup Function (from run_experiment.sh)

```bash
# Triggered by trap EXIT

cleanup() {
    # 1. Kill Ryu controller
    if [ ! -z "$RYU_PID" ]; then
        kill $RYU_PID 2>/dev/null || true
        echo "  ✓ Ryu controller stopped"
    fi

    # 2. Extra cleanup (in case Mininet missed something)
    sudo pkill -f mosquitto 2>/dev/null || true
    sudo pkill -f publisher 2>/dev/null || true
    sudo pkill -f subscriber 2>/dev/null || true
    sudo mn -c > /dev/null 2>&1 || true

    echo "  ✓ Cleanup complete"
}
```

**Output di terminal:**
```
[CLEANUP] Stopping all components...
  ✓ Ryu controller stopped
  ✓ Cleanup complete
```

#### 7.4. Display Results

**Script run_experiment.sh (lines 89-110):**

```bash
echo ""
echo "=============================================================="
echo "  EXPERIMENT COMPLETE!"
echo "=============================================================="
echo ""

# Display results location and summary
if [ -d "$RUN_RESULTS_DIR" ]; then
    echo "Results saved to: $RUN_RESULTS_DIR"
    echo ""

    if [ -f "$RUN_RESULTS_DIR/metrics_summary.txt" ]; then
        echo "=== METRICS SUMMARY ==="
        cat "$RUN_RESULTS_DIR/metrics_summary.txt"
        echo ""
    fi

    if [ -f "$RUN_RESULTS_DIR/mqtt_metrics_log.csv" ]; then
        echo "CSV data: mqtt_metrics_log.csv"
        echo "Total messages: $(wc -l < "$RUN_RESULTS_DIR/mqtt_metrics_log.csv")"
    fi
fi
```

**Output di terminal:**
```
==============================================================
  EXPERIMENT COMPLETE!
==============================================================

Results saved to: /home/mqtt-sdn/results/06-dscp-qos-13switches/run_2025-11-16_23-01-33

=== METRICS SUMMARY ===
======================================================================
                    SIMULATION SUMMARY
======================================================================

CONFIGURATION:
  Scenario          : 06-dscp-qos-13switches
  Topology          : DSCP Hierarchical 3-Tier (13 switches, 19 hosts)
  Switches          : 13
  Publishers        : 18
  Bandwidth Limit   : True
  Bandwidth         : 0.5 Mbps (500 Kbps)
  QoS Queues        : True

======================================================================

ANOMALY:
  Messages Received : 135,000
  Avg Delay         : 4.25 ms
  Min Delay         : 0.31 ms
  Max Delay         : 52.18 ms
  Std Dev Delay     : 2.15 ms
  Avg Jitter        : 1.34 ms

NORMAL:
  Messages Received : 135,000
  Avg Delay         : 12,588.24 ms
  Min Delay         : 2.65 ms
  Max Delay         : 28,475.27 ms
  Std Dev Delay     : 8,292.63 ms
  Avg Jitter        : 5,268.26 ms

TOTAL:
  Duration          : 300 s
  Total Messages    : 270,000
  Throughput        : 900 msg/s
  Priority Ratio    : 2,961x (Normal slower than Anomaly)

CSV data: mqtt_metrics_log.csv
Total messages: 270001

Controller log: /home/mqtt-sdn/logs/ryu.log
```

---

## Flow Data MQTT

### Detailed Packet Journey

Mari kita ikuti **satu message MQTT** dari publisher sampai subscriber:

#### Publisher: f3r2a (Floor 3, Room 2, Anomaly)

**Location:** Switch s12, IP 10.0.3.3, DSCP 46

**Step-by-step journey:**

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Publisher Creates Message                              │
├─────────────────────────────────────────────────────────────────┤
│ Host: f3r2a (10.0.3.3)                                          │
│ Process: python3 publisher_dscp46_veryhigh.py                   │
│                                                                 │
│ 1. Generate payload:                                            │
│    payload = {                                                  │
│      "device": "sensor_f3r2_anomaly",                           │
│      "type": "anomaly",                                         │
│      "dscp": 46,                                                │
│      "value": 87.3,                                             │
│      "timestamp": 1700000100.000,                               │
│      "seq": 5000                                                │
│    }                                                            │
│                                                                 │
│ 2. Publish to MQTT:                                             │
│    client.publish("iot/data", json.dumps(payload), qos=1)       │
│                                                                 │
│ 3. Socket creates TCP packet:                                   │
│    ┌───────────────────────────────────────┐                   │
│    │ Ethernet Header                       │                   │
│    │   src_mac: f3:r2:a1:00:00:03          │                   │
│    │   dst_mac: (broker MAC via ARP)       │                   │
│    ├───────────────────────────────────────┤                   │
│    │ IP Header                             │                   │
│    │   src_ip: 10.0.3.3                    │                   │
│    │   dst_ip: 10.0.0.1                    │                   │
│    │   TOS: 0xb8 (DSCP 46) ← Set by socket│                   │
│    │   protocol: TCP (6)                   │                   │
│    ├───────────────────────────────────────┤                   │
│    │ TCP Header                            │                   │
│    │   src_port: 54321                     │                   │
│    │   dst_port: 1883 (MQTT)               │                   │
│    ├───────────────────────────────────────┤                   │
│    │ MQTT Payload (150 bytes)              │                   │
│    │   {"device": "sensor_f3r2_anomaly"..} │                   │
│    └───────────────────────────────────────┘                   │
│                                                                 │
│ Time: t=0.000s                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Enter Switch s12 (Edge - Floor 3, Room 2)              │
├─────────────────────────────────────────────────────────────────┤
│ 1. Packet arrives at s12-eth2 (from f3r2a)                      │
│                                                                 │
│ 2. OpenFlow processing:                                         │
│    - Look up flow table                                         │
│    - Check priorities from high to low:                         │
│                                                                 │
│      Priority 100: ARP? No (eth_type=0x0800, not 0x0806)       │
│      Priority 60: DSCP 46? YES! ✓                              │
│                                                                 │
│    - Matching rule:                                             │
│      match: eth_type=0x0800, ip_dscp=46                         │
│      actions: set_queue(1), output(NORMAL)                      │
│                                                                 │
│ 3. Apply actions:                                               │
│    - Assign to Queue 1                                          │
│    - NORMAL = MAC learning + L2 forwarding                      │
│    - MAC learning: f3r2a is on port 2                           │
│    - Destination 10.0.0.1 not in MAC table                      │
│    - Flood to all ports except ingress                          │
│    - But uplink (to s4) is the path                             │
│                                                                 │
│ 4. Queue 1 processing:                                          │
│    Current queue state:                                         │
│    Queue 1: [▓▓▓] 3 packets (guaranteed 300 Kbps)              │
│    Queue 5: [▓▓▓▓▓▓▓▓▓▓▓▓] 45 packets (only 25 Kbps)           │
│                                                                 │
│    - Queue 1 has bandwidth available                            │
│    - Dequeue immediately (no wait)                              │
│    - Transmit to s4                                             │
│                                                                 │
│ Delay in s12: 0.5 ms                                            │
│ Time: t=0.0005s                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Enter Switch s4 (Aggregation - Floor 3)                │
├─────────────────────────────────────────────────────────────────┤
│ 1. Packet arrives at s4-eth4 (from s12)                         │
│                                                                 │
│ 2. OpenFlow processing:                                         │
│    - Match Priority 60: DSCP 46 → Queue 1 ✓                    │
│                                                                 │
│ 3. MAC learning:                                                │
│    - Broker (10.0.0.1) is on uplink to s1                       │
│    - Forward to s1                                              │
│                                                                 │
│ 4. Queue 1 processing:                                          │
│    - Aggregation level, more congestion                         │
│    - Queue 1: [▓▓▓▓▓] 5 packets waiting                         │
│    - But still prioritized over Queue 5 (80 packets!)           │
│    - Wait: 0.8 ms                                               │
│    - Transmit to s1                                             │
│                                                                 │
│ Delay in s4: 0.8 ms                                             │
│ Time: t=0.0013s                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Enter Switch s1 (Core)                                 │
├─────────────────────────────────────────────────────────────────┤
│ 1. Packet arrives at s1-eth4 (from s4)                          │
│                                                                 │
│ 2. OpenFlow processing:                                         │
│    - Match Priority 60: DSCP 46 → Queue 1 ✓                    │
│                                                                 │
│ 3. MAC learning:                                                │
│    - Broker is on s1-eth1 (direct connection)                   │
│    - Forward to broker                                          │
│                                                                 │
│ 4. Queue 1 processing:                                          │
│    - Core level, MOST congestion                                │
│    - All 18 publishers' traffic converge here                   │
│    - Queue 1: [▓▓▓▓▓▓▓▓] 8 packets                              │
│    - Queue 5: [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓] 120+ packets!                  │
│    - Queue 1 still gets 60-80% bandwidth                        │
│    - Wait: 1.2 ms                                               │
│    - Transmit to broker                                         │
│                                                                 │
│ Delay in s1: 1.2 ms                                             │
│ Time: t=0.0025s                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Arrive at Broker (10.0.0.1)                            │
├─────────────────────────────────────────────────────────────────┤
│ Host: broker                                                    │
│ Process: mosquitto                                              │
│                                                                 │
│ 1. Network stack receives packet                                │
│    - IP layer: Destination = 10.0.0.1 ✓                         │
│    - TCP layer: Port 1883 → mosquitto ✓                         │
│                                                                 │
│ 2. Mosquitto processes MQTT packet:                             │
│    - Parse MQTT PUBLISH                                         │
│    - Topic: "iot/data"                                          │
│    - Payload: {"device": "sensor_f3r2_anomaly", ...}            │
│    - QoS: 1 (send ACK back)                                     │
│                                                                 │
│ 3. Forward to subscriber:                                       │
│    - Subscriber listening on topic "iot/data"                   │
│    - Mosquitto forwards to subscriber (same host, localhost)    │
│                                                                 │
│ Processing time: 0.3 ms                                         │
│ Time: t=0.0028s                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Subscriber Receives Message                            │
├─────────────────────────────────────────────────────────────────┤
│ Host: broker (same as mosquitto)                               │
│ Process: python3 subscriber_enhanced.py                         │
│                                                                 │
│ 1. on_message() callback triggered:                             │
│    msg.topic = "iot/data"                                       │
│    msg.payload = '{"device": "sensor_f3r2_anomaly", ...}'       │
│                                                                 │
│ 2. Parse JSON:                                                  │
│    payload = json.loads(msg.payload)                            │
│                                                                 │
│ 3. Calculate delay:                                             │
│    send_time = payload['timestamp']  # 1700000100.000          │
│    receive_time = time.time()        # 1700000100.003          │
│    delay = (receive_time - send_time) * 1000                    │
│    delay = 3.0 ms ← TOTAL END-TO-END DELAY                      │
│                                                                 │
│ 4. Calculate jitter:                                            │
│    last_delay = 2.8 ms (from previous message)                  │
│    jitter = abs(3.0 - 2.8) = 0.2 ms                             │
│                                                                 │
│ 5. Save to CSV:                                                 │
│    writer.writerow([                                            │
│      "sensor_f3r2_anomaly",  # device                           │
│      "anomaly",              # type                             │
│      46,                     # dscp                             │
│      "very_high",            # priority                         │
│      87.3,                   # value                            │
│      5000,                   # seq                              │
│      1700000100.000,         # send_time                        │
│      1700000100.003,         # receive_time                     │
│      3.0,                    # delay_ms                         │
│      0.2                     # jitter_ms                        │
│    ])                                                           │
│                                                                 │
│ Time: t=0.0030s                                                 │
│ TOTAL DELAY: 3.0 ms ✓                                           │
└─────────────────────────────────────────────────────────────────┘
```

**Breakdown delay:**
- Switch s12: 0.5 ms (edge)
- Switch s4: 0.8 ms (aggregation)
- Switch s1: 1.2 ms (core - most congested)
- Broker processing: 0.3 ms
- Network propagation: 0.2 ms
- **Total: 3.0 ms** ✓

**Comparison dengan normal packet (DSCP 0):**

Sama path, TAPI:
- Queue 5 di s12: Wait **50 ms** (45 packets ahead)
- Queue 5 di s4: Wait **800 ms** (80 packets ahead)
- Queue 5 di s1: Wait **14,000 ms** (120+ packets, very slow drain)
- **Total: ~15,000 ms** (15 seconds!) ❌

**Priority ratio: 15,000 / 3 = 5,000x slower!**

---

## Ringkasan Timeline Lengkap

```
t=0s        → Script dimulai, cleanup old processes
t=1s        → Environment variables di-set
t=2s        → Ryu controller started (PID saved)
t=5s        → Controller ready, listening on port 6633
t=6s        → Mininet network creation begins
t=10s       → 13 switches created
t=15s       → 19 hosts created dengan IP addresses
t=20s       → All links created dengan bandwidth limit
t=25s       → Network started, switches connect to controller
t=26-28s    → Controller installs flow rules (91 rules total)
t=30s       → Network stabilized
t=35s       → OVS queues configuration starts
t=40-50s    → All queues configured (5 queues × 40 ports = 200 queues)
t=55s       → Mosquitto broker started
t=57s       → Subscriber started
t=58-65s    → 18 publishers started (staggered)
t=65s       → All components running
t=65-365s   → EXPERIMENT RUNNING (300 seconds)
              - Publishers send at 50 msg/s each
              - Switches forward based on DSCP
              - Subscriber collects metrics
              - ~900 msg/s total traffic
              - High congestion (216% utilization)
              - Clear priority differentiation
t=365s      → Time's up, stopping MQTT components
t=366s      → Publishers killed (pkill)
t=369s      → Subscriber receives SIGTERM
t=370s      → Subscriber flushes data, generates summary
t=372s      → Mosquitto stopped
t=375s      → Mininet network stopped
t=376s      → All network namespaces deleted
t=377s      → Ryu controller killed
t=378s      → Cleanup complete
t=380s      → Results displayed
            → Script exits
```

---

## File-File Penting

### Scripts

1. **run_experiment.sh**
   - Entry point
   - Mengelola lifecycle
   - Line 1-110

2. **topology_config.py**
   - Build network topology
   - Configure QoS
   - Start MQTT components
   - Line 1-520

3. **controller_dscp.py**
   - Install OpenFlow rules
   - DSCP → Queue mapping
   - Line 1-250

### Publishers

4. **publisher_dscp46_veryhigh.py** (dan 4 lainnya)
   - Thin wrapper
   - Call generic publisher
   - Line 1-26 (each)

5. **shared/mqtt/publisher_dscp.py**
   - Generic publisher implementation
   - DSCP socket configuration
   - MQTT publish loop
   - Line 1-370

### Subscriber

6. **shared/mqtt/subscriber_enhanced.py**
   - Metrics collection
   - Delay & jitter calculation
   - CSV writing
   - Summary generation
   - Line 1-500

### Configuration

7. **shared/mqtt/dscp_config.py**
   - DSCP constants
   - Priority mappings
   - Queue configurations
   - Line 1-300

8. **shared/utils/dscp_utils.py**
   - DSCP utility functions
   - Socket configuration
   - Callback creation
   - Line 1-200

---

## FAQ

### Q: Mengapa butuh cleanup di awal?
A: Experiment sebelumnya mungkin masih running, bentrok port & network namespace.

### Q: Mengapa wait 5 detik setelah network start?
A: Switches butuh waktu untuk connect ke controller dan install flow rules.

### Q: Mengapa bandwidth 0.5 Mbps saja?
A: Untuk create congestion! 18 publishers × 50 msg/s = 1.08 Mbps. Utilization 216%.

### Q: Bagaimana DSCP bisa di-set dari aplikasi?
A: Via `socket.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, dscp << 2)`

### Q: Apakah flow rules di-install per packet?
A: TIDAK! Sekali install saat switch connect, berlaku untuk semua packet.

### Q: Mengapa anomaly packet lebih cepat?
A: Assigned ke Queue 1 (60-80% bandwidth), normal ke Queue 5 (5-15% bandwidth).

### Q: Berapa total flow rules?
A: 13 switches × 7 rules = 91 flow rules.

### Q: Berapa total queues?
A: ~40 ports × 5 queues = ~200 queue objects.

### Q: Data disimpan di mana?
A: `/home/mqtt-sdn/results/06-dscp-qos-13switches/run_YYYY-MM-DD_HH-MM-SS/`

### Q: Bagaimana cara verify DSCP working?
A: Lihat metrics_summary.txt, anomaly delay harus jauh lebih kecil dari normal.

---

**Dokumentasi dibuat:** 2025-11-16
**Scenario:** 06-dscp-qos-13switches
**Versi:** 1.0
