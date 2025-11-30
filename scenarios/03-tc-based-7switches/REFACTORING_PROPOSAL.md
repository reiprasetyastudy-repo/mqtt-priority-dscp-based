# Refactoring Proposal - Scenario 03 (Standar untuk Scenario Berikutnya)

## Current Issues & Improvements

### 1. ❌ HARDCODED VALUES

**Current Problems:**
```python
# topology_config.py
LINK_BANDWIDTH_MBPS = 1
MSG_RATE = 50
PROJECT_ROOT = os.path.abspath(os.path.join(...))

# controller_v2.py
self.CORE_SWITCHES = [1]
self.AGG_SWITCHES = [2, 3]
MQTT_PORT = 1883 (implicit)
```

**✅ Solution: Configuration File**

Create `config/scenario_config.yaml`:
```yaml
network:
  bandwidth_mbps: 1
  topology:
    core_switches: [1]
    agg_switches: [2, 3]
    edge_switches: [4, 5, 6, 7]

mqtt:
  port: 1883
  broker_ip: "10.0.0.1"
  message_rate: 50
  message_size: 250

qos:
  queue_high:
    id: 1
    min_bw_percent: 70
    max_bw_percent: 100
  queue_low:
    id: 2
    min_bw_percent: 30
    max_bw_percent: 50

paths:
  project_root: "/home/mqtt-sdn"
  mqtt_dir: "shared/mqtt"
  log_dir: "logs"
  results_dir: "results/03-tc-based-7switches"
```

---

### 2. ❌ MONOLITHIC FILES

**Current Structure:**
```
topology_config.py (355 lines)
├─ Network configuration
├─ Topology building
├─ OVS queue configuration
├─ MQTT management
└─ Main execution

controller_v2.py (208 lines)
├─ Switch handling
├─ MAC learning
├─ Traffic classification
├─ Flow installation
└─ All logic in one class
```

**✅ Solution: Modular Structure**

```
scenarios/03-tc-based-7switches/
├── config/
│   ├── __init__.py
│   ├── scenario_config.yaml      # Configuration file
│   └── config_loader.py          # Load & validate config
│
├── core/
│   ├── __init__.py
│   ├── topology.py               # Topology builder (base class)
│   ├── network.py                # Network utilities
│   └── mqtt_manager.py           # MQTT lifecycle management
│
├── qos/
│   ├── __init__.py
│   ├── queue_manager.py          # OVS queue configuration
│   └── classifier.py             # Traffic classification logic
│
├── controller/
│   ├── __init__.py
│   ├── base_controller.py        # Base SDN controller
│   ├── mac_learning.py           # MAC learning mixin
│   ├── qos_controller.py         # QoS-specific logic
│   └── flow_manager.py           # Flow rule management
│
├── utils/
│   ├── __init__.py
│   ├── logger.py                 # Structured logging
│   ├── metrics.py                # Metrics calculation
│   └── validators.py             # Input validation
│
├── main.py                        # Entry point
├── run_controller.py              # Controller entry point
└── tests/
    ├── test_topology.py
    ├── test_classifier.py
    └── test_queue_manager.py
```

---

### 3. ❌ NO SEPARATION OF CONCERNS

**Current:**
- Topology class handles: network, MQTT, logging, OVS config
- Controller handles: MAC learning, classification, flow management

**✅ Solution: Single Responsibility Principle**

Each module has ONE job:
- `topology.py` → Build network structure
- `mqtt_manager.py` → Manage MQTT lifecycle
- `queue_manager.py` → Configure OVS queues
- `classifier.py` → Classify traffic
- `flow_manager.py` → Install flow rules

---

### 4. ❌ CODE DUPLICATION

**Current:**
```python
# Floor 1 publishers
for idx, sw in enumerate(edge_switches_f1):
    h_anomaly = self.net.addHost(...)
    # ... same code ...

# Floor 2 publishers
for idx, sw in enumerate(edge_switches_f2):
    h_anomaly = self.net.addHost(...)
    # ... DUPLICATE code ...
```

**✅ Solution: Helper Functions**

```python
def create_publisher_pair(network, switch, floor, room, base_ip):
    """Create anomaly + normal publisher pair"""
    anomaly = network.addHost(...)
    normal = network.addHost(...)
    return [anomaly, normal]
```

---

### 5. ❌ LIMITED ERROR HANDLING

**Current:**
```python
try:
    result = subprocess.run(cmd, ...)
    if result.returncode != 0:
        continue  # Silent failure
except Exception as e:
    info(f'Failed: {str(e)}')  # No recovery
```

**✅ Solution: Structured Error Handling**

```python
class QueueConfigurationError(Exception):
    pass

def configure_queue(switch, port):
    try:
        result = subprocess.run(...)
        if result.returncode != 0:
            raise QueueConfigurationError(
                f"Failed to configure {switch}:{port}"
                f"Reason: {result.stderr}"
            )
    except subprocess.TimeoutExpired:
        logger.error("OVS command timeout")
        raise
    except Exception as e:
        logger.exception("Unexpected error")
        raise
```

---

### 6. ❌ NO LOGGING STANDARD

**Current:**
```python
info('*** Building topology\n')
self.logger.info("[Ryu] Switch connected")
print(f"Error: {e}")  # Inconsistent!
```

**✅ Solution: Structured Logging**

```python
# utils/logger.py
import logging
from datetime import datetime

class ScenarioLogger:
    def __init__(self, name, log_dir):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # File handler
        fh = logging.FileHandler(
            f"{log_dir}/{name}_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(fh)

    def network_event(self, event, **kwargs):
        self.logger.info(f"[NETWORK] {event}", extra=kwargs)

    def mqtt_event(self, event, **kwargs):
        self.logger.info(f"[MQTT] {event}", extra=kwargs)

    def qos_event(self, event, **kwargs):
        self.logger.info(f"[QOS] {event}", extra=kwargs)
```

---

### 7. ❌ MAGIC NUMBERS

**Current:**
```python
if ip_last_octet % 2 == 1:
    queue_id = 1
    priority = 20
else:
    queue_id = 2
    priority = 15

time.sleep(5)  # Why 5?
time.sleep(2)  # Why 2?
```

**✅ Solution: Named Constants**

```python
# config/constants.py
class QoSPriority:
    ARP = 100
    ICMP = 90
    MQTT_ANOMALY = 20
    MQTT_NORMAL = 15
    TABLE_MISS = 0

class NetworkTiming:
    NETWORK_STABILIZATION = 5  # seconds
    BROKER_STARTUP = 2
    SUBSCRIBER_STARTUP = 2
    PUBLISHER_STAGGER = 0.5

class QueueID:
    HIGH_PRIORITY = 1  # Anomaly traffic
    LOW_PRIORITY = 2   # Normal traffic
```

---

### 8. ❌ NO VALIDATION

**Current:**
```python
MSG_RATE = 50  # What if someone sets 0 or -1?
LINK_BANDWIDTH_MBPS = 1  # What if 0?
```

**✅ Solution: Input Validation**

```python
# utils/validators.py
from typing import Any
from pydantic import BaseModel, validator, Field

class NetworkConfig(BaseModel):
    bandwidth_mbps: int = Field(gt=0, le=1000)
    message_rate: int = Field(gt=0, le=1000)

    @validator('bandwidth_mbps')
    def validate_bandwidth(cls, v):
        if v < 1:
            raise ValueError('Bandwidth must be at least 1 Mbps')
        return v

    @validator('message_rate')
    def check_congestion(cls, v, values):
        # Warn if utilization will be too low
        bandwidth = values.get('bandwidth_mbps', 1)
        # 8 sensors × rate × 250 bytes × 8 bits
        utilization = (8 * v * 250 * 8) / (bandwidth * 1_000_000)
        if utilization < 0.7:
            raise ValueError(
                f'Message rate {v} will only create {utilization:.0%} '
                f'utilization. Need >70% for priority to work!'
            )
        return v
```

---

### 9. ❌ TIGHT COUPLING

**Current:**
```python
class TCBasedTopology:
    def run_mqtt(self):
        # Directly calls subprocess
        h_broker.cmd('mosquitto ...')
        # Directly accesses global variables
        env_vars = f'LINK_BANDWIDTH_MBPS={LINK_BANDWIDTH_MBPS}'
```

**✅ Solution: Dependency Injection**

```python
class TopologyRunner:
    def __init__(self, config, mqtt_manager, logger):
        self.config = config
        self.mqtt = mqtt_manager
        self.logger = logger

    def run_mqtt(self):
        # Use injected dependencies
        self.mqtt.start_broker(self.config.mqtt.broker_ip)
        self.mqtt.start_subscriber(self.config)
        self.mqtt.start_publishers(self.publishers, self.config)
```

---

### 10. ❌ NO TESTABILITY

**Current:**
- Hard to test individual functions
- No unit tests
- Requires full Mininet environment

**✅ Solution: Make Code Testable**

```python
# qos/classifier.py
class TrafficClassifier:
    """Pure function - easy to test!"""

    @staticmethod
    def classify_by_ip(ip_address: str) -> tuple[int, int]:
        """
        Classify traffic based on IP address.

        Returns:
            (queue_id, priority)
        """
        last_octet = int(ip_address.split('.')[-1])

        if last_octet % 2 == 1:
            return (QueueID.HIGH_PRIORITY, QoSPriority.MQTT_ANOMALY)
        else:
            return (QueueID.LOW_PRIORITY, QoSPriority.MQTT_NORMAL)

# tests/test_classifier.py
def test_anomaly_classification():
    queue, priority = TrafficClassifier.classify_by_ip("10.0.1.1")
    assert queue == QueueID.HIGH_PRIORITY
    assert priority == QoSPriority.MQTT_ANOMALY

def test_normal_classification():
    queue, priority = TrafficClassifier.classify_by_ip("10.0.1.2")
    assert queue == QueueID.LOW_PRIORITY
    assert priority == QoSPriority.MQTT_NORMAL
```

---

## Proposed New Architecture

### Class Diagram

```
┌─────────────────────┐
│  ScenarioConfig     │ ← Load from YAML
└──────────┬──────────┘
           │
           ├──────────────────────────────────┐
           ▼                                  ▼
┌─────────────────────┐          ┌─────────────────────┐
│  TopologyBuilder    │          │  QoSController      │
├─────────────────────┤          ├─────────────────────┤
│ + build_network()   │          │ + classify_traffic()│
│ + add_switches()    │          │ + install_flows()   │
│ + add_hosts()       │          │                     │
└──────────┬──────────┘          └──────────┬──────────┘
           │                                │
           ▼                                ▼
┌─────────────────────┐          ┌─────────────────────┐
│  QueueManager       │          │  FlowManager        │
├─────────────────────┤          ├─────────────────────┤
│ + configure_queues()│          │ + add_flow()        │
│ + validate_queues() │          │ + delete_flow()     │
└─────────────────────┘          └─────────────────────┘
           │                                │
           ▼                                ▼
┌─────────────────────┐          ┌─────────────────────┐
│  MQTTManager        │          │  MACLearningTable   │
├─────────────────────┤          ├─────────────────────┤
│ + start_broker()    │          │ + learn()           │
│ + start_publishers()│          │ + lookup()          │
│ + start_subscriber()│          │ + get_port()        │
└─────────────────────┘          └─────────────────────┘
```

### Data Flow

```
1. Config Loading
   scenario_config.yaml → ConfigLoader → ScenarioConfig object

2. Network Setup
   ScenarioConfig → TopologyBuilder → Mininet Network
                  → QueueManager → OVS Queues Configured

3. Controller Setup
   ScenarioConfig → QoSController → Ryu Application
                  → FlowManager, MACLearningTable initialized

4. MQTT Setup
   ScenarioConfig → MQTTManager → Broker, Publishers, Subscriber started

5. Runtime
   Packet arrives → Controller.packet_in()
                  → MACLearningTable.learn()
                  → TrafficClassifier.classify()
                  → FlowManager.add_flow()
                  → Packet forwarded with QoS
```

---

## Migration Strategy

### Phase 1: Extract Configuration (Low Risk)
1. Create `config/scenario_config.yaml`
2. Create `config/config_loader.py`
3. Update `topology_config.py` to use config
4. Test: Run existing scenario with new config

### Phase 2: Extract Utilities (Low Risk)
1. Create `utils/logger.py`
2. Create `utils/validators.py`
3. Replace hardcoded values with constants
4. Test: Verify logging works

### Phase 3: Modularize Topology (Medium Risk)
1. Create `core/topology.py` (base class)
2. Create `core/mqtt_manager.py`
3. Create `qos/queue_manager.py`
4. Refactor `topology_config.py` to use modules
5. Test: Full scenario run

### Phase 4: Modularize Controller (Medium Risk)
1. Create `controller/base_controller.py`
2. Create `controller/mac_learning.py`
3. Create `qos/classifier.py`
4. Create `controller/flow_manager.py`
5. Refactor `controller_v2.py`
6. Test: Verify priority still works

### Phase 5: Add Tests (Low Risk)
1. Write unit tests for classifiers
2. Write unit tests for validators
3. Integration tests
4. CI/CD setup

---

## Benefits Summary

### Maintainability
✅ Easy to find and fix bugs
✅ Clear separation of concerns
✅ Self-documenting code structure

### Reusability
✅ Easy to create new scenarios (just change config)
✅ Modules can be reused across scenarios
✅ Controller can be extended for new QoS policies

### Testability
✅ Unit tests for each module
✅ Mock dependencies for isolated testing
✅ Automated regression tests

### Scalability
✅ Easy to add new switch types
✅ Easy to add new classification rules
✅ Easy to add new queue policies

### Documentation
✅ Code is self-documenting
✅ Config file explains all parameters
✅ Type hints improve IDE support

---

## Example: How Easy to Create Scenario 04?

**Before (Current):**
1. Copy entire `03-tc-based-7switches/` folder
2. Modify hardcoded values in multiple places
3. Pray nothing breaks

**After (Modular):**
1. Create `scenarios/04-new-scenario/config/scenario_config.yaml`
2. Change values:
   ```yaml
   network:
     bandwidth_mbps: 10  # 10x faster
     topology:
       edge_switches: [4, 5, 6, 7, 8, 9]  # More switches
   mqtt:
     message_rate: 100  # More traffic
   ```
3. Create `scenarios/04-new-scenario/main.py`:
   ```python
   from core.topology import TopologyBuilder
   from controller.qos_controller import QoSController
   from config.config_loader import load_config

   config = load_config('config/scenario_config.yaml')
   topology = TopologyBuilder(config)
   topology.build()
   topology.run(duration=300)
   ```
4. Done! 🎉

---

## Next Steps

1. **Review this proposal** - Diskusi mana yang prioritas
2. **Create proof-of-concept** - Implement Phase 1 dulu
3. **Test & validate** - Ensure scenario 3 still works
4. **Document changes** - Update README
5. **Apply to other scenarios** - Standardize!

---

**Question:** Apakah proposal ini terlalu kompleks? Atau ada bagian tertentu yang lebih prioritas?
