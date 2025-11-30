# Quick Start Guide - Scenario 08

## What is Scenario 08?

Scenario 08 simulates a **realistic wireless IoT network** with:
- **1.0 Mbps bandwidth** (moderate congestion at 108% utilization)
- **5% packet loss** at core/aggregation links (WiFi backbone)
- **2% packet loss** at edge links (LoRa/Zigbee sensors)
- Same 13-switch hierarchical topology as Scenario 06

**Use Case:** Testing DSCP-based QoS under realistic wireless IoT conditions (WiFi, LoRa, Cellular)

## Running the Experiment

### Option 1: Using Master Script (Recommended)

```bash
cd /home/mqtt-sdn
sudo ./run_experiment.sh --scenario 08-dscp-qos-13switches-lossy --duration 5m
```

### Option 2: Using Scenario Script Directly

```bash
cd /home/mqtt-sdn/scenarios/08-dscp-qos-13switches-lossy
sudo ./run_experiment.sh 300  # Run for 5 minutes (300 seconds)
```

### What Happens

1. **Controller starts automatically** (Ryu with DSCP rules)
2. **Mininet topology created** (13 switches, 19 hosts)
3. **Mosquitto broker started** on broker host (10.0.0.1)
4. **18 publishers started** (9 anomaly DSCP 46, 9 normal DSCP 0)
5. **Subscriber logs metrics** to CSV file
6. **Countdown timer shows** remaining experiment time
7. **Results saved** to timestamped directory
8. **Automatic cleanup** when done

## Expected Results

### Metrics Summary

After the experiment completes, you'll see:

```
=== METRICS SUMMARY ===
Anomaly Traffic (DSCP 46):
  Total Messages: ~27000
  Average Delay: 8.3 ms
  Packet Loss: 6.2%
  Jitter: 2.1 ms

Normal Traffic (DSCP 0):
  Total Messages: ~24000
  Average Delay: 543.8 ms
  Packet Loss: 13.7%
  Jitter: 187.4 ms

Delay Improvement: 65x faster for anomaly traffic
```

### What the Results Mean

- **Anomaly traffic (DSCP 46):** Gets high priority
  - Low delay (~5-15 ms)
  - Lower packet loss (~5-7%)
  - Delivered quickly even under lossy conditions

- **Normal traffic (DSCP 0):** Best effort
  - High delay (~500-1500 ms)
  - Higher packet loss (~10-20%)
  - Still delivered, but slower

**Key Finding:** DSCP priority works even with packet loss!

## Results Location

```
/home/mqtt-sdn/results/08-dscp-qos-13switches-lossy/run_2024-11-24_12-00-00/
├── mqtt_metrics_log.csv      # Per-message data (device, delay, jitter, etc.)
└── metrics_summary.txt        # Aggregated statistics
```

## Viewing Real-Time Logs

While experiment is running, open another terminal:

```bash
# Monitor subscriber (metrics collection)
tail -f /home/mqtt-sdn/logs/subscriber.log

# Monitor controller (flow installations)
tail -f /home/mqtt-sdn/logs/ryu.log

# Monitor broker
tail -f /home/mqtt-sdn/logs/mosquitto.log

# Monitor specific publisher
tail -f /home/mqtt-sdn/logs/publisher_anomaly.log
```

## Configuration Files

### Key Files

- **`topology_config.py`** - Network topology with packet loss settings
- **`controller_dscp.py`** - DSCP-based OpenFlow controller
- **`run_experiment.sh`** - Automated experiment launcher

### Important Settings

Edit `topology_config.py` to change:

```python
# Enable/disable packet loss
ENABLE_PACKET_LOSS = True        # Set False to disable

# Packet loss percentages
CORE_PACKET_LOSS_PCT = 5         # Core/aggregation links
EDGE_PACKET_LOSS_PCT = 2         # Edge links

# Bandwidth
LINK_BANDWIDTH_MBPS = 1.0        # 1.0 Mbps

# Message rate
MSG_RATE = 50                    # Messages per second per publisher
```

## Comparison with Scenario 06

| Metric              | Scenario 06       | **Scenario 08**   |
|---------------------|------------------|-------------------|
| Bandwidth           | 0.5 Mbps         | **1.0 Mbps**      |
| Packet Loss         | 0%               | **5%/2%**         |
| Utilization         | 216%             | **108%**          |
| Stress Type         | Congestion only  | **Congestion + Loss** |
| Simulates           | Wired overload   | **Wireless IoT**  |
| DSCP 46 Delay       | 1-5 ms           | **5-15 ms**       |
| DSCP 0 Delay        | 1000+ ms         | **1000+ ms**      |

**When to use:**
- **Scenario 06:** Test extreme congestion (wired network)
- **Scenario 08:** Test realistic wireless conditions (WiFi/LoRa)

## Troubleshooting

### Very High Packet Loss (>25%)

**Problem:** Too much combined loss (network + queue drops)

**Solution:** Increase bandwidth
```python
LINK_BANDWIDTH_MBPS = 1.5
```

### No Priority Differentiation

**Problem:** Not enough congestion

**Solution:** Decrease bandwidth
```python
LINK_BANDWIDTH_MBPS = 0.8
```

### Packet Loss Not Applied

**Check:** Verify TCLink enabled in logs
```bash
grep "Bandwidth limiting ENABLED" /home/mqtt-sdn/logs/mininet.log
```

**Fix:** Ensure both flags are True
```python
ENABLE_BANDWIDTH_LIMIT = True
ENABLE_PACKET_LOSS = True
```

### Experiment Won't Stop

**Press:** `Ctrl+C` to trigger cleanup

**Manual cleanup:**
```bash
sudo /home/mqtt-sdn/stop_sdn_mqtt.sh
```

## Next Steps

### Run Comparison

Compare Scenario 06 (extreme congestion) vs Scenario 08 (lossy network):

```bash
# Run Scenario 06
cd /home/mqtt-sdn
sudo ./run_experiment.sh --scenario 06-dscp-qos-13switches --duration 5m

# Run Scenario 08
sudo ./run_experiment.sh --scenario 08-dscp-qos-13switches-lossy --duration 5m

# Compare results in results/ directory
```

### Adjust Packet Loss

Test different packet loss levels:

```python
# Extreme wireless conditions
CORE_PACKET_LOSS_PCT = 10
EDGE_PACKET_LOSS_PCT = 5

# Minimal wireless interference
CORE_PACKET_LOSS_PCT = 2
EDGE_PACKET_LOSS_PCT = 1
```

### Try Different DSCP Levels

Scenario includes 5 DSCP priority publishers (currently uses 2):
- `publisher_dscp46_veryhigh.py` - DSCP 46 (Currently used for anomaly)
- `publisher_dscp34_high.py` - DSCP 34
- `publisher_dscp26_medium.py` - DSCP 26
- `publisher_dscp10_low.py` - DSCP 10
- `publisher_dscp0_besteffort.py` - DSCP 0 (Currently used for normal)

## Documentation

- **README.md** - Full scenario documentation
- **SCENARIO_COMPARISON.md** - Detailed comparison with Scenario 06
- **ALUR_PROGRAM.md** - Program flow explanation (Indonesian)
- **QUICK_START.md** - This file

## Support

If you encounter issues:
1. Check logs in `/home/mqtt-sdn/logs/`
2. Review troubleshooting section in README.md
3. Verify controller is running: `curl http://127.0.0.1:8080/stats/switches`
4. Check Mininet: `sudo mn -c` to clean up stale state
