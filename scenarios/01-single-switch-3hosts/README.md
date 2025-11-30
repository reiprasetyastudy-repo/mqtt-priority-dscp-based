# Scenario 01: Single Switch with 3 Hosts

## 📋 Overview

**Topology Type:** Simple Star Topology
**Number of Switches:** 1
**Number of Hosts:** 3
**Filtering Method:** IP-based

## 🏗️ Network Topology

```
    h1 (10.0.0.1)
         |
         |
        [s1] -------- h3 (10.0.0.3)
         |
         |
    h2 (10.0.0.2)
```

### Topology Details

| Component | Role | IP Address | Description |
|-----------|------|------------|-------------|
| **h1** | Publisher | 10.0.0.1 | Publishes anomaly data (critical traffic) |
| **h2** | Publisher | 10.0.0.2 | Publishes normal data (standard traffic) |
| **h3** | Broker + Subscriber | 10.0.0.3 | Runs Mosquitto broker and metrics subscriber |
| **s1** | OpenFlow Switch | - | Managed by Ryu controller with OpenFlow 1.3 |

### Controller Configuration

- **Location:** `controller.py`
- **Filtering:** IP-based matching
- **Priority Rules:**
  - **Anomaly traffic** (src=10.0.0.1, dst=port 1883) → Queue 1, Priority 20
  - **Normal traffic** (src=10.0.0.2, dst=port 1883) → Queue 2, Priority 10
  - **ARP traffic** → Priority 100 (allow all)
  - **Broker return traffic** (src=10.0.0.3) → Priority 15 (allow all)

## 🎯 Research Goals

This scenario is designed to test:

1. **Basic SDN-QoS functionality** - Does priority-based forwarding work?
2. **End-to-End Delay** - Is anomaly traffic faster than normal?
3. **Jitter** - Is anomaly traffic more stable?
4. **Packet Loss** - Does SDN introduce additional loss?
5. **Throughput** - Do both traffics get fair bandwidth?

## 🚀 How to Run

### Option 1: Using Scenario Script (Recommended)

```bash
# Terminal 1: Start Ryu Controller
cd /home/mqtt-sdn
./run_ryu_controller.sh

# Terminal 2: Run scenario
cd /home/mqtt-sdn/scenarios/01-single-switch-3hosts
sudo ./run_scenario.sh 60        # Run for 60 seconds
sudo ./run_scenario.sh 5m        # Run for 5 minutes
sudo ./run_scenario.sh           # Run until Ctrl+C
```

### Option 2: Using Master Script

```bash
cd /home/mqtt-sdn
./run_experiment.sh --scenario 01-single-switch-3hosts --duration 60
```

### Option 3: Manual Run

```bash
# Start controller first (separate terminal)
cd /home/mqtt-sdn
./run_ryu_controller.sh

# Run topology
cd /home/mqtt-sdn/scenarios/01-single-switch-3hosts
sudo python3 topology_config.py --duration 60
```

## 📊 Expected Results

### Ideal Outcome

| Metric | Anomaly (Queue 1) | Normal (Queue 2) | Expected Difference |
|--------|-------------------|------------------|---------------------|
| **Avg Delay** | ~2-3 ms | ~3-4 ms | 20-30% faster for anomaly |
| **Jitter** | ~0.5 ms | ~1-2 ms | More stable for anomaly |
| **Packet Loss** | 0% | 0% | Equal (no loss introduced) |
| **Throughput** | ~1 msg/s | ~1 msg/s | Equal (fairness maintained) |

### What Success Looks Like

✅ Anomaly traffic has **lower average delay**
✅ Anomaly traffic has **lower jitter** (more stable)
✅ **Zero packet loss** for both traffics
✅ **Equal throughput** (no starvation of normal traffic)

## 📁 Output Files

Results are saved to timestamped directories:

```
/home/mqtt-sdn/results/01-single-switch-3hosts/
└── run_2025-11-09_15-30-00/
    ├── mqtt_metrics_log.csv      # Raw metrics data
    ├── metrics_summary.txt        # Statistical analysis
    └── (future: flow_stats.json)
```

### CSV Format

```csv
device,type,value,seq,timestamp_sent,delay_ms
sensor_anomaly,anomaly,82.45,0,1762690000.12,2.15
sensor_normal,normal,25.67,0,1762690000.15,3.42
...
```

## 🔧 Customization

### Change IP Addresses

Edit `topology_config.py`:
```python
h1 = self.net.addHost('h1', ip='10.0.0.1/24')  # Change here
h2 = self.net.addHost('h2', ip='10.0.0.2/24')  # Change here
h3 = self.net.addHost('h3', ip='10.0.0.3/24')  # Change here
```

Also update `controller.py` to match:
```python
match_anomaly = parser.OFPMatch(
    eth_type=0x0800,
    ipv4_src="10.0.0.1",  # Must match h1 IP
    ip_proto=6,
    tcp_dst=1883
)
```

### Change Queue Priorities

Edit `controller.py`:
```python
actions_anomaly = [
    parser.OFPActionSetQueue(1),  # Change queue number
    # ...
]
self.add_flow(datapath, 20, match_anomaly, actions_anomaly)  # Change priority
```

## 📝 Notes

- This is the **baseline scenario** for comparison
- Simple topology, easy to understand and debug
- **Not scalable** - requires 1 flow rule per IP address
- See `/docs/filtering_methods_comparison.md` for more scalable approaches
- For multi-sensor deployments, consider Scenario 02 (subnet-based) or higher

## 🔗 Related Scenarios

- **Scenario 02:** Subnet-based filtering (scalable for many sensors)
- **Scenario 03:** Multi-sensor deployment (10+ hosts)
- **Scenario 04:** Multi-switch hierarchical topology

## 📖 References

- Main documentation: `/home/mqtt-sdn/DOKUMENTASI_SIMULASI.md`
- Research docs: `/home/mqtt-sdn/docs/`
- Filtering methods: `/home/mqtt-sdn/docs/filtering_methods_comparison.md`

---

**Created:** 2025-11-09
**Version:** 1.0
**Status:** ✅ Production Ready
