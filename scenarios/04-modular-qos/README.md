# Scenario 04: Modular SDN-based QoS for IoT

## Overview

This is a **refactored and modularized** version of Scenario 03, implementing best practices for maintainability, reusability, and testability.

### Key Improvements over Scenario 03

✅ **Configuration-Driven:** Single YAML file for all settings
✅ **Modular Architecture:** Separated concerns into distinct modules
✅ **Type Safety:** Clear interfaces and data structures
✅ **Testable:** Unit tests for core components
✅ **Logging:** Structured logging across all modules
✅ **Error Handling:** Proper exception handling
✅ **Documentation:** Self-documenting code with clear naming

---

## Architecture

```
04-modular-qos/
├── config/
│   ├── scenario_config.yaml      # Single source of truth
│   └── config_loader.py          # Configuration loading & validation
│
├── core/
│   ├── topology.py               # Network topology builder
│   └── mqtt_manager.py           # MQTT lifecycle management
│
├── qos/
│   ├── classifier.py             # Traffic classification logic
│   └── queue_manager.py          # OVS queue configuration
│
├── controller/
│   ├── qos_controller.py         # Main Ryu controller
│   ├── mac_learning.py           # MAC learning table
│   └── flow_manager.py           # Flow rule management
│
├── utils/
│   ├── constants.py              # Named constants (no magic numbers)
│   └── logger.py                 # Structured logging
│
├── tests/
│   └── test_classifier.py        # Unit tests
│
├── main.py                        # Topology entry point
├── run_controller.py              # Controller entry point
└── run_scenario.sh                # Orchestration script
```

---

## Quick Start

### 1. Run Complete Scenario

```bash
# Run for 5 minutes
sudo ./run_scenario.sh 300

# Run with Mininet CLI
sudo ./run_scenario.sh
```

### 2. Manual Mode (for debugging)

**Terminal 1 - Start Controller:**
```bash
source /home/aldi/ryu39/bin/activate
ryu-manager run_controller.py ryu.app.ofctl_rest
```

**Terminal 2 - Start Topology:**
```bash
# Run for 5 minutes
sudo python3 main.py --duration 300

# Or with CLI
sudo python3 main.py --cli
```

---

## Configuration

All settings are in `config/scenario_config.yaml`:

```yaml
network:
  bandwidth_mbps: 1           # Easy to change
  topology:
    core_switches: [1]
    agg_switches: [2, 3]
    edge_switches: [4, 5, 6, 7]

mqtt:
  message_rate: 50            # Controls congestion

qos:
  queue_high:
    min_bandwidth_percent: 70
    max_bandwidth_percent: 100
  queue_low:
    min_bandwidth_percent: 30
    max_bandwidth_percent: 50
```

**To create a new scenario:** Just copy `scenario_config.yaml` and modify!

---

## Key Features

### 1. Automatic Validation

Configuration is validated on load:

```
⚠️  Network utilization (60%) is below minimum (70%).
    Priority mechanism may not be visible!
    Increase message_rate to at least 44
```

### 2. Structured Logging

Different event types:
```python
logger.network_event("Switch s1 connected")
logger.mqtt_event("Publisher started")
logger.qos_event("Queue configured")
```

### 3. Traffic Classification

Easily testable pure functions:

```python
queue_id, priority, type = TrafficClassifier.classify_by_ip_odd_even("10.0.1.1")
# Returns: (1, 20, "ANOMALY")
```

### 4. Queue Management

Clean interface for OVS queues:

```python
queue_manager = QueueManager(config)
queue_manager.configure_all_queues()
```

### 5. MQTT Lifecycle

Separated MQTT management:

```python
mqtt_manager = MQTTManager(config)
mqtt_manager.start_broker(broker_host)
mqtt_manager.start_publishers(publishers)
```

---

## Testing

### Run Unit Tests

```bash
# Manual test
python3 tests/test_classifier.py

# With pytest (if installed)
pytest tests/test_classifier.py -v
```

### Test Coverage

- ✅ Traffic classification (odd/even IPs)
- ✅ MQTT traffic detection
- ✅ Invalid input handling
- 🔄 Queue configuration (manual testing)
- 🔄 Full integration (via run_scenario.sh)

---

## Comparison with Scenario 03

| Aspect | Scenario 03 | Scenario 04 (This) |
|--------|-------------|-------------------|
| **Configuration** | Hardcoded in Python | YAML config file |
| **Structure** | Monolithic (2 files) | Modular (12+ files) |
| **Logging** | Mixed (`info()`, `print()`) | Structured logger |
| **Error Handling** | Silent failures | Proper exceptions |
| **Testability** | Requires full Mininet | Unit testable components |
| **Reusability** | Copy & modify | Config-driven |
| **Magic Numbers** | Many (`priority=20`) | Named constants |
| **Documentation** | Comments | Self-documenting |

---

## How to Create Scenario 05

Want to test with different settings? Easy!

```bash
# Copy scenario 04
cp -r 04-modular-qos 05-your-scenario

# Edit config
nano 05-your-scenario/config/scenario_config.yaml

# Change values:
network:
  bandwidth_mbps: 10    # 10x faster
mqtt:
  message_rate: 100     # More traffic

# Run it!
cd 05-your-scenario
sudo ./run_scenario.sh 300
```

No code changes needed! 🎉

---

## Expected Results

Same as Scenario 03 (proven working):

```
ANOMALY:
  Delay: ~12-15 ms (LOW)
  Jitter: ~2 ms

NORMAL:
  Delay: ~60-70 ms (HIGH)
  Jitter: ~7 ms

Conclusion: Normal traffic 5-6x SLOWER
✅ Priority mechanism works!
```

---

## Troubleshooting

### Configuration Warnings

```bash
# Test configuration without running
python3 -c "from config.config_loader import load_config; load_config('config/scenario_config.yaml')"
```

### Controller Not Starting

```bash
# Check Ryu logs
tail -f /home/mqtt-sdn/logs/ryu.log
```

### Network Issues

```bash
# Clean Mininet
sudo mn -c

# Verify OVS
sudo ovs-vsctl show
```

---

## Development

### Adding New Classification Method

1. Add method to `qos/classifier.py`:
```python
@staticmethod
def classify_by_your_method(ip_address: str) -> Tuple[int, int, str]:
    # Your logic here
    return (queue_id, priority, traffic_type)
```

2. Add to config YAML:
```yaml
qos:
  classification:
    method: "your_method"
```

3. Update controller to use it (automatic!)

### Adding New Queue Type

1. Update `config/scenario_config.yaml`:
```yaml
qos:
  queue_critical:
    id: 0
    min_bandwidth_percent: 90
    max_bandwidth_percent: 100
```

2. Update `qos/queue_manager.py` to configure it

---

## References

- **Original Implementation:** `/home/mqtt-sdn/scenarios/03-tc-based-7switches/`
- **Refactoring Proposal:** `/home/mqtt-sdn/scenarios/03-tc-based-7switches/REFACTORING_PROPOSAL.md`
- **Results Comparison:** Run both and compare metrics

---

## License & Credits

Part of MQTT-SDN research project.

Refactored for maintainability and reusability as the **standard template** for future scenarios.
