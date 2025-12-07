# Scenario 07: 5-Level DSCP Priority - Summary

## ✅ Scenario Created Successfully!

**Location**: `/home/mqtt-sdn/scenarios/07-5level-dscp-13switches/`

---

## 🎯 What's New in This Scenario?

Unlike Scenario 01 which only tests **2 priority levels** (DSCP 46 vs DSCP 0), Scenario 07 tests **all 5 DSCP priority levels** simultaneously:

| Priority | DSCP | Queue | Bandwidth | Expected Loss |
|----------|------|-------|-----------|---------------|
| Very High | 46 | 1 | 60-80% | **0%** |
| High | 34 | 2 | 45-60% | **~20%** |
| Medium | 26 | 3 | 30-45% | **~40%** |
| Low | 10 | 4 | 15-30% | **~60%** |
| Best Effort | 0 | 5 | 5-15% | **~80%** |

---

## 📊 Publisher Distribution

**Total: 15 Publishers** (5 DSCP levels × 3 floors)

```
Floor 1 (s5):        Floor 2 (s8):        Floor 3 (s11):
├─ DSCP 46          ├─ DSCP 46           ├─ DSCP 46
├─ DSCP 34          ├─ DSCP 34           ├─ DSCP 34
├─ DSCP 26          ├─ DSCP 26           ├─ DSCP 26
├─ DSCP 10          ├─ DSCP 10           ├─ DSCP 10
└─ DSCP 0           └─ DSCP 0            └─ DSCP 0
```

---

## 🚀 How to Run

### Quick Test (1 minute)
```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches
sudo ./run_experiment.sh 60
```

### Full Experiment (10 minutes send + 10 minutes drain)
```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches
sudo ./run_experiment.sh 600
```

### Custom Duration
```bash
# 5 minutes send + 5 minutes drain
sudo ./run_experiment.sh 300
```

---

## 📁 Files Created

```
07-5level-dscp-13switches/
├── topology.py                      # Main topology (15 publishers)
├── publisher_dscp46_veryhigh.py     # DSCP 46 - Very High Priority
├── publisher_dscp34_high.py         # DSCP 34 - High Priority
├── publisher_dscp26_medium.py       # DSCP 26 - Medium Priority
├── publisher_dscp10_low.py          # DSCP 10 - Low Priority
├── publisher_dscp0_besteffort.py    # DSCP 0 - Best Effort
├── run_experiment.sh                # Easy runner script
├── README.md                        # Complete documentation
└── SCENARIO_SUMMARY.md              # This file
```

✅ All files are executable and syntax-checked.

---

## 🔍 Expected Results

After running the experiment, you should see:

### Metrics Summary
```
DSCP 46 (Very High):
  - Avg Delay: ~200 ms
  - Packet Loss: 0%
  - Jitter: ~60 ms

DSCP 34 (High):
  - Avg Delay: ~50,000 ms (50s)
  - Packet Loss: ~20%
  - Jitter: ~100 ms

DSCP 26 (Medium):
  - Avg Delay: ~100,000 ms (100s)
  - Packet Loss: ~40%
  - Jitter: ~150 ms

DSCP 10 (Low):
  - Avg Delay: ~200,000 ms (200s)
  - Packet Loss: ~60%
  - Jitter: ~200 ms

DSCP 0 (Best Effort):
  - Avg Delay: ~250,000 ms (250s)
  - Packet Loss: ~80%
  - Jitter: ~250 ms
```

**Key Insight**: Results demonstrate **gradual performance degradation** based on DSCP priority level!

---

## 📊 View Results

```bash
# Find latest run
ls -lt results/07-5level-dscp-13switches/

# View summary
cat results/07-5level-dscp-13switches/run_*/metrics_summary.txt

# View CSV (for Excel/analysis)
cat results/07-5level-dscp-13switches/run_*/metrics_summary.csv

# View raw data
cat results/07-5level-dscp-13switches/run_*/mqtt_metrics_log.csv
```

---

## 🆚 Comparison with Scenario 01

| Aspect | Scenario 01 | Scenario 07 |
|--------|-------------|-------------|
| **DSCP Levels** | 2 (46, 0) | **5 (46, 34, 26, 10, 0)** |
| **Publishers** | 18 | 15 |
| **Traffic Types** | Anomaly vs Normal | **5-level priority spectrum** |
| **Use Case** | Binary differentiation | **Multi-class QoS** |
| **Best For** | Paper results | **Demo & production** |

**When to use Scenario 07?**
- Demonstrating full QoS capability
- Testing multi-level priority systems
- Production IoT with multiple traffic classes
- Presentations and demonstrations

**When to use Scenario 01?**
- Paper results (simpler to explain)
- Binary comparison (anomaly vs normal)
- Maximum contrast demonstration

---

## 🎓 Use Cases

### Industrial IoT
- **DSCP 46**: Emergency shutdown signals
- **DSCP 34**: Critical process alarms
- **DSCP 26**: Regular telemetry
- **DSCP 10**: Historical data logging
- **DSCP 0**: Diagnostics/debugging

### Smart Building
- **DSCP 46**: Fire/gas alarms
- **DSCP 34**: HVAC critical sensors
- **DSCP 26**: Energy monitoring
- **DSCP 10**: Occupancy tracking
- **DSCP 0**: Maintenance logs

### Healthcare
- **DSCP 46**: Patient vital signs (critical)
- **DSCP 34**: Medical equipment alerts
- **DSCP 26**: Environment monitoring
- **DSCP 10**: Asset tracking
- **DSCP 0**: System diagnostics

---

## 🧪 Testing Tips

1. **Start with Quick Test (60s)** to verify setup
2. **Check Controller** is running: `curl http://127.0.0.1:8080/stats/switches`
3. **Monitor Logs** during experiment: `tail -f results/*/logs/experiment.log`
4. **Compare Results** across DSCP levels
5. **Adjust Congestion** by changing bandwidth in topology.py

---

## 📝 Notes

- **Topology**: Same as Scenario 01 (13 switches, hierarchical)
- **Congestion**: ~1.8x capacity (150 msg/s total / 83.3 msg/s capacity)
- **Graceful Shutdown**: Publishers stop via internal timer
- **Drain Phase**: Ensures all in-flight messages are received

---

## ✅ Verification Checklist

Before running full experiment:

- [ ] Ryu controller starts without errors
- [ ] All 15 publishers appear in logs
- [ ] Subscriber receives messages from all DSCP levels
- [ ] Flow rules installed correctly (`ovs-ofctl dump-flows`)
- [ ] Queues configured properly (`ovs-vsctl list QoS`)

---

**Created**: 2025-12-07
**Status**: ✅ Ready to Run
**Tested**: Syntax validated, all scripts executable
