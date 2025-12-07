# Quick Start Guide - Scenario 07

## 🚀 Running 3x Experiments (Recommended)

For **statistically valid results**, run 3 repetitions:

### 10-Minute Experiment (3x)
```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches
sudo ./run_3x_experiments.sh 600
```

**Total Time:** ~66 minutes (1 hour 6 min)
- Run 1: 20 min
- Delay: 3 min
- Run 2: 20 min
- Delay: 3 min
- Run 3: 20 min

### Quick Test (1 minute, 3x)
```bash
sudo ./run_3x_experiments.sh 60
```

**Total Time:** ~10 minutes

---

## 📊 What You Get

After 3x runs complete, you'll have:

```
results/07-5level-dscp-13switches/
└── batch_3x_2025-12-07_21-30-00/
    ├── batch_experiment.log      # Master log with timestamps
    ├── run_1/
    │   ├── metrics_summary.txt   # Detailed metrics
    │   ├── metrics_summary.csv   # Excel-compatible
    │   └── mqtt_metrics_log.csv  # Raw data
    ├── run_2/
    │   └── ... (same structure)
    └── run_3/
        └── ... (same structure)
```

---

## 📈 Expected Results Per Run

Each run should show gradual performance degradation:

| DSCP | Priority | Avg Delay | Packet Loss |
|------|----------|-----------|-------------|
| 46 | Very High | ~200 ms | 0% |
| 34 | High | ~50 s | ~20% |
| 26 | Medium | ~100 s | ~40% |
| 10 | Low | ~200 s | ~60% |
| 0 | Best Effort | ~250 s | ~80% |

---

## 🔍 View Results

```bash
# View all 3 summaries
cat results/07-5level-dscp-13switches/batch_3x_*/run_*/metrics_summary.txt

# View specific run
cat results/07-5level-dscp-13switches/batch_3x_*/run_1/metrics_summary.txt

# View batch log (with timestamps)
cat results/07-5level-dscp-13switches/batch_3x_*/batch_experiment.log

# Check for failures
grep -i "error\|fail" results/07-5level-dscp-13switches/batch_3x_*/batch_experiment.log
```

---

## ⚡ Single Run (Not Recommended for Research)

If you just want to test the setup:

```bash
# Single 10-minute run
sudo ./run_experiment.sh 600

# Single 1-minute test
sudo ./run_experiment.sh 60
```

**Note:** For research/paper results, always use 3x repetitions!

---

## ✅ Verification Checklist

Before running full experiment, do a quick test:

```bash
# 1. Quick test (60 seconds)
sudo ./run_3x_experiments.sh 60

# 2. Check results
ls -la results/07-5level-dscp-13switches/batch_3x_*/run_*/

# 3. Verify all 3 runs completed
cat results/07-5level-dscp-13switches/batch_3x_*/batch_experiment.log | grep "completed successfully"

# Expected output:
# Run 1 completed successfully in XXXs
# Run 2 completed successfully in XXXs
# Run 3 completed successfully in XXXs
```

If all 3 runs complete successfully, you're ready for the full experiment!

---

## 🎯 When to Use What?

| Use Case | Command | Duration | Repetitions | Total Time |
|----------|---------|----------|-------------|------------|
| **Research/Paper** | `./run_3x_experiments.sh 600` | 10 min | 3x | ~66 min |
| **Demo/Presentation** | `./run_experiment.sh 600` | 10 min | 1x | ~20 min |
| **Quick Test** | `./run_3x_experiments.sh 60` | 1 min | 3x | ~10 min |
| **Setup Verification** | `./run_experiment.sh 60` | 1 min | 1x | ~2 min |

---

## 🆘 Troubleshooting

### Script Stops During Execution
```bash
# Check what's running
ps aux | grep -E "ryu|mininet|mosquitto"

# Kill all and restart
sudo mn -c
sudo pkill -f ryu-manager
sudo pkill -f mosquitto
```

### Missing Results
```bash
# Check if experiment ran
cat results/07-5level-dscp-13switches/batch_3x_*/batch_experiment.log

# Check individual run logs
cat results/07-5level-dscp-13switches/batch_3x_*/run_1/logs/experiment.log
```

### Controller Not Starting
```bash
# Activate Ryu environment manually
cd /home/mqtt-sdn
source ryu39/bin/activate
ryu-manager shared/sdn/controller.py

# In another terminal, run experiment
cd scenarios/07-5level-dscp-13switches
sudo python3 topology.py --duration 60
```

---

## 📝 Tips

1. **Always use 3x for research**: Ensures statistical validity
2. **Monitor first run**: Watch the log to catch errors early
3. **Check batch log**: Review timestamps and any warnings
4. **Verify all DSCP levels**: Ensure all 5 levels have data
5. **Compare across runs**: Results should be consistent (< 5% variance)

---

**Ready to run? Start with the quick test:**

```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches
sudo ./run_3x_experiments.sh 60
```

Good luck! 🚀

---

## 🔄 Running in Background (Safe for Disconnection)

If you want to disconnect from terminal while experiment runs:

### Run 3x in Background (10 minutes each)
```bash
cd /home/mqtt-sdn/scenarios/07-5level-dscp-13switches
sudo ./run_3x_background.sh 600
```

This will:
- Start experiment in background using `nohup`
- Save all output to log file
- Allow you to disconnect safely
- Continue running even if terminal closes

### Monitor Progress
```bash
# Follow the log in real-time
tail -f results/07-5level-dscp-13switches/background_*/nohup_output.log

# Check if still running
ps aux | grep run_3x_experiments

# View current status
cat results/07-5level-dscp-13switches/background_*/nohup_output.log | tail -50
```

### Stop Background Experiment
```bash
# Find the process
ps aux | grep run_3x_experiments

# Kill it (use PID from above)
sudo kill <PID>

# Force kill if needed
sudo kill -9 <PID>

# Cleanup
sudo mn -c
sudo pkill -f ryu-manager
sudo pkill -f mosquitto
```

### Quick Test in Background (1 minute, 3x)
```bash
sudo ./run_3x_background.sh 60
# You can disconnect immediately after this command
# Total time: ~10 minutes
```

---

## 📊 Background Logs Structure

```
results/07-5level-dscp-13switches/
└── background_2025-12-07_21-45-00/
    ├── nohup_output.log              # All experiment output
    ├── process.pid                   # PID (deleted when done)
    └── batch_3x_*/                   # Results directory
        ├── batch_experiment.log
        ├── run_1/
        ├── run_2/
        └── run_3/
```

---
