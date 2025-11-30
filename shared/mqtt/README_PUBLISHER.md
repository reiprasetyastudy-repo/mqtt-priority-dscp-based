# Modular Publisher Implementation

## Overview

All DSCP publishers have been modularized into a **single generic implementation** with thin wrapper scripts for each priority level. This eliminates code duplication and centralizes publisher logic.

## Architecture

### Before Modularization

```
scenarios/05-dscp-qos-7switches/
├── publisher_dscp46_veryhigh.py    (~100 lines, duplicated logic)
├── publisher_dscp34_high.py        (~100 lines, duplicated logic)
├── publisher_dscp26_medium.py      (~100 lines, duplicated logic)
├── publisher_dscp10_low.py         (~100 lines, duplicated logic)
└── publisher_dscp0_besteffort.py   (~100 lines, duplicated logic)

scenarios/06-dscp-qos-13switches/   (5 more duplicates!)
└── (same 5 files...)

Total: 10 files × ~100 lines = ~1000 lines of duplicated code ❌
```

### After Modularization

```
shared/mqtt/
└── publisher_dscp.py               (★ 370 lines, generic implementation)

scenarios/05-dscp-qos-7switches/
├── publisher_dscp46_veryhigh.py    (26 lines, thin wrapper)
├── publisher_dscp34_high.py        (26 lines, thin wrapper)
├── publisher_dscp26_medium.py      (26 lines, thin wrapper)
├── publisher_dscp10_low.py         (26 lines, thin wrapper)
└── publisher_dscp0_besteffort.py   (26 lines, thin wrapper)

scenarios/06-dscp-qos-13switches/   (5 thin wrappers)
└── (same structure...)

Total: 1 generic (370 lines) + 10 wrappers (260 lines) = 630 lines ✅
Code Reduction: 37% fewer lines, 90% less duplication!
```

## Generic Publisher Features

### `shared/mqtt/publisher_dscp.py`

**Capabilities:**
- ✅ Supports all 5 DSCP priority levels (46, 34, 26, 10, 0)
- ✅ 7 traffic types (anomaly, very_high, high, medium, low, normal, best_effort)
- ✅ Automatic value range selection based on traffic type
- ✅ CLI arguments OR environment variables
- ✅ Flexible configuration (device, broker, rate, topic)
- ✅ DSCP socket configuration using shared utilities
- ✅ Self-documenting with help message
- ✅ Production-ready error handling

**Traffic Types & Value Ranges:**
| Type | DSCP | Value Range | Use Case |
|------|------|-------------|----------|
| anomaly / very_high | 46 | 50-100 | Critical alerts |
| high | 34 | 70-90 | Important data |
| medium | 26 | 40-70 | Regular monitoring |
| low | 10 | 20-50 | Background collection |
| normal / best_effort | 0 | 20-30 | Non-critical traffic |

## Usage Examples

### 1. Direct Usage (CLI)

```bash
cd /home/mqtt-sdn

# Anomaly traffic with DSCP 46
python3 shared/mqtt/publisher_dscp.py --dscp 46 --type anomaly

# High priority with custom device
python3 shared/mqtt/publisher_dscp.py --dscp 34 --type high --device sensor_temp_01

# Medium priority with custom broker
python3 shared/mqtt/publisher_dscp.py --dscp 26 --type medium --broker 10.0.1.1
```

### 2. Environment Variables

```bash
# Current style (backward compatible)
DSCP=46 DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 shared/mqtt/publisher_dscp.py

# Mix CLI and env vars
export BROKER_IP=10.0.0.1
python3 shared/mqtt/publisher_dscp.py --dscp 34 --device my_sensor
```

### 3. Thin Wrappers (Scenario Usage)

```bash
# Scenario 05 - Use existing wrappers
cd /home/mqtt-sdn/scenarios/05-dscp-qos-7switches

# Very high priority (DSCP 46)
DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp46_veryhigh.py

# High priority (DSCP 34)
DEVICE=sensor2 BROKER_IP=10.0.0.1 python3 publisher_dscp34_high.py

# Medium priority (DSCP 26)
DEVICE=sensor3 BROKER_IP=10.0.0.1 python3 publisher_dscp26_medium.py
```

### 4. From Python Code

```python
from shared.mqtt.publisher_dscp import run_publisher
from shared.mqtt.dscp_config import DSCP_VERY_HIGH

# Run publisher programmatically
run_publisher(
    dscp_value=DSCP_VERY_HIGH,
    traffic_type='anomaly',
    device_name='sensor_critical_01',
    broker_ip='10.0.0.1',
    msg_rate=100  # 100 msg/s
)
```

## Thin Wrapper Structure

Each scenario publisher is now a tiny wrapper (~26 lines):

```python
#!/usr/bin/env python3
"""
DSCP 46 (Very High Priority) Publisher - Thin Wrapper

This is a thin wrapper around the generic DSCP publisher.
Uses DSCP 46 (EF - Expedited Forwarding) for critical/anomaly traffic.

Usage:
    DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp46_veryhigh.py
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import run_publisher
from shared.mqtt.dscp_config import DSCP_VERY_HIGH

if __name__ == '__main__':
    run_publisher(
        dscp_value=DSCP_VERY_HIGH,  # 46
        traffic_type='anomaly'       # High values (50-100)
    )
```

**Advantages:**
- ✅ Self-contained (can be run directly)
- ✅ Backward compatible (same interface as before)
- ✅ Clear documentation
- ✅ Easy to understand
- ✅ No duplicated logic

## Creating New Publishers

### Option 1: Use Generic Publisher Directly

```bash
# Just specify DSCP and type
python3 shared/mqtt/publisher_dscp.py --dscp 40 --type high --device sensor_cs5
```

### Option 2: Create New Thin Wrapper

```python
#!/usr/bin/env python3
"""Custom Priority Publisher"""
import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import run_publisher

if __name__ == '__main__':
    run_publisher(
        dscp_value=40,       # Your custom DSCP
        traffic_type='high'  # Your traffic type
    )
```

### Option 3: Extend DSCPPublisher Class

```python
from shared.mqtt.publisher_dscp import DSCPPublisher

class MyCustomPublisher(DSCPPublisher):
    def generate_payload(self):
        # Custom payload generation
        payload = super().generate_payload()
        payload['custom_field'] = 'custom_value'
        return payload

publisher = MyCustomPublisher(dscp_value=46, traffic_type='anomaly')
publisher.run()
```

## Testing

### Syntax Check

```bash
# Test all thin wrappers
cd /home/mqtt-sdn
python3 -c "import scenarios.05-dscp-qos-7switches.publisher_dscp46_veryhigh"
python3 -c "import scenarios.05-dscp-qos-7switches.publisher_dscp34_high"
# ... etc
```

### Import Test

```bash
python3 << 'EOF'
from shared.mqtt.publisher_dscp import DSCPPublisher, run_publisher
from shared.mqtt.dscp_config import DSCP_VERY_HIGH
print("✓ All imports successful!")
