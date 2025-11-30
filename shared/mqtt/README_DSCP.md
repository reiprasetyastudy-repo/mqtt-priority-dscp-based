# Modular DSCP Implementation

## Overview

This project uses a **modular, centralized approach** for DSCP (Differentiated Services Code Point) header configuration. All DSCP-related logic is centralized in shared modules to ensure:

- ✅ **Single source of truth** for DSCP configuration
- ✅ **Easy maintenance** - update once, apply everywhere
- ✅ **Consistent implementation** across all publishers
- ✅ **Clean code** - no duplication
- ✅ **GitHub-ready** - centralized logic for version control

## Architecture

```
/home/mqtt-sdn/
├── shared/
│   ├── utils/
│   │   └── dscp_utils.py          # ⭐ DSCP utility functions
│   └── mqtt/
│       └── dscp_config.py         # ⭐ DSCP constants & mappings
│
└── scenarios/
    ├── 05-dscp-qos-7switches/
    │   ├── publisher_dscp46_veryhigh.py    # Uses shared modules
    │   ├── publisher_dscp34_high.py        # Uses shared modules
    │   ├── publisher_dscp26_medium.py      # Uses shared modules
    │   ├── publisher_dscp10_low.py         # Uses shared modules
    │   └── publisher_dscp0_besteffort.py   # Uses shared modules
    │
    └── 06-dscp-qos-13switches/
        └── publisher_dscp*.py              # All use shared modules
```

## Core Modules

### 1. `shared/utils/dscp_utils.py`

**Purpose:** Utility functions for DSCP socket configuration

**Key Functions:**

```python
# Configure socket with DSCP value
configure_dscp_socket(sock, dscp_value)
# Returns: TOS value set (dscp_value << 2)

# Create MQTT callback for automatic DSCP configuration
create_dscp_callback(dscp_value, device_name=None, verbose=True)
# Returns: Callback function for client.on_socket_open

# Get human-readable DSCP name
get_dscp_name(dscp_value)
# Returns: "EF (Expedited Forwarding)"

# Validate DSCP value
validate_dscp_value(dscp_value)
# Raises: ValueError if invalid
```

**Constants:**
```python
DSCP_EF = 46      # Expedited Forwarding
DSCP_AF41 = 34    # Assured Forwarding 41
DSCP_AF31 = 26    # Assured Forwarding 31
DSCP_AF21 = 18    # Assured Forwarding 21
DSCP_AF11 = 10    # Assured Forwarding 11
DSCP_BE = 0       # Best Effort
```

### 2. `shared/mqtt/dscp_config.py`

**Purpose:** Centralized DSCP constants and priority mappings

**Constants:**
```python
# 5 Priority Levels (Primary)
DSCP_VERY_HIGH = 46     # EF - Critical/Anomaly
DSCP_HIGH = 34          # AF41 - Important
DSCP_MEDIUM = 26        # AF31 - Regular
DSCP_LOW = 10           # AF11 - Background
DSCP_BEST_EFFORT = 0    # BE - Non-critical
```

**Mappings:**
```python
# Priority name to DSCP value
PRIORITY_TO_DSCP = {
    "very_high": 46,
    "high": 34,
    "medium": 26,
    "low": 10,
    "best_effort": 0
}

# DSCP to OVS queue number
DSCP_TO_QUEUE = {
    46: 1,  # Queue 1 (60-80% bandwidth)
    34: 2,  # Queue 2 (45-60% bandwidth)
    26: 3,  # Queue 3 (30-45% bandwidth)
    10: 4,  # Queue 4 (15-30% bandwidth)
    0: 5    # Queue 5 (5-15% bandwidth)
}

# Queue bandwidth allocations
QUEUE_BANDWIDTH = {
    1: {"min": 60, "max": 80},  # Very High
    2: {"min": 45, "max": 60},  # High
    3: {"min": 30, "max": 45},  # Medium
    4: {"min": 15, "max": 30},  # Low
    5: {"min": 5, "max": 15}    # Best Effort
}
```

**Helper Functions:**
```python
get_queue_for_dscp(dscp_value)      # Returns queue number
get_priority_name(dscp_value)       # Returns priority name
get_description(dscp_value)         # Returns full description
get_use_case(dscp_value)            # Returns recommended use case
print_dscp_config()                 # Prints complete configuration
```

## Usage in Publishers

### Standard Pattern

All DSCP publishers follow this pattern:

```python
#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time, json, random, os, sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

# Import shared DSCP modules
from shared.utils.dscp_utils import create_dscp_callback
from shared.mqtt.dscp_config import DSCP_VERY_HIGH  # or DSCP_HIGH, etc.

# Configuration
BROKER = os.getenv("BROKER_IP", "10.0.0.1")
DEVICE = os.getenv("DEVICE", "sensor_name")
DSCP_VALUE = DSCP_VERY_HIGH  # Use shared constant

# Create MQTT client
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

# Configure DSCP using shared utility
client.on_socket_open = create_dscp_callback(
    dscp_value=DSCP_VALUE,
    device_name=DEVICE,
    verbose=True
)

# Connect and publish
client.connect(BROKER, 1883)
# ... rest of publisher logic
```

### Before Modularization

**Old approach (duplicated code):**

```python
import socket  # Needed for manual DSCP configuration

DSCP_VALUE = 46  # Hardcoded value

def on_socket_open(client, userdata, sock):
    """Duplicated in every publisher"""
    ip_tos = DSCP_VALUE << 2
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, ip_tos)
    print(f"[DSCP] Socket configured with TOS=0x{ip_tos:02x}")

client.on_socket_open = on_socket_open
```

**Problems:**
- ❌ Code duplicated in 10 publishers (5 per scenario)
- ❌ Bug fixes require updating all files
- ❌ No validation or error handling
- ❌ Hardcoded values
- ❌ Difficult to maintain

### After Modularization

**New approach (centralized):**

```python
# No socket import needed
from shared.utils.dscp_utils import create_dscp_callback
from shared.mqtt.dscp_config import DSCP_VERY_HIGH

DSCP_VALUE = DSCP_VERY_HIGH  # Shared constant

# One-line DSCP configuration
client.on_socket_open = create_dscp_callback(
    dscp_value=DSCP_VALUE,
    device_name=DEVICE,
    verbose=True
)
```

**Benefits:**
- ✅ Code in one place (shared/utils/dscp_utils.py)
- ✅ Update once, all publishers benefit
- ✅ Built-in validation and error handling
- ✅ Consistent constants across project
- ✅ Easy to maintain and test

## Creating New DSCP Publishers

To create a new DSCP publisher:

```python
#!/usr/bin/env python3
"""My Custom DSCP Publisher"""

import paho.mqtt.client as mqtt
import time, json, os, sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

# Import shared modules
from shared.utils.dscp_utils import create_dscp_callback
from shared.mqtt.dscp_config import (
    DSCP_VERY_HIGH,  # 46
    DSCP_HIGH,       # 34
    DSCP_MEDIUM,     # 26
    DSCP_LOW,        # 10
    DSCP_BEST_EFFORT # 0
)

# Choose your priority level
DSCP_VALUE = DSCP_HIGH  # Use High Priority (34)

# Environment configuration
BROKER = os.getenv("BROKER_IP", "10.0.0.1")
DEVICE = os.getenv("DEVICE", "my_sensor")

# Create MQTT client with DSCP
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_socket_open = create_dscp_callback(
    dscp_value=DSCP_VALUE,
    device_name=DEVICE,
    verbose=True
)

# Connect
client.connect(BROKER, 1883)
client.loop_start()

# Publish your data
while True:
    payload = {
        "device": DEVICE,
        "value": "your_data",
        "timestamp": time.time()
    }
    client.publish("iot/data", json.dumps(payload), qos=1)
    time.sleep(1)
```

## Testing the Modular Implementation

### Self-Test Utilities

```bash
# Test DSCP utilities
python3 /home/mqtt-sdn/shared/utils/dscp_utils.py

# Test DSCP configuration
python3 /home/mqtt-sdn/shared/mqtt/dscp_config.py
```

### Verify Imports

```python
import sys
sys.path.insert(0, '/home/mqtt-sdn')

from shared.utils.dscp_utils import create_dscp_callback
from shared.mqtt.dscp_config import DSCP_VERY_HIGH

print(f"DSCP_VERY_HIGH = {DSCP_VERY_HIGH}")  # Should print 46
```

### Test Publisher Syntax

```bash
cd /home/mqtt-sdn/scenarios/05-dscp-qos-7switches
python3 -c "import publisher_dscp46_veryhigh"  # Should not error
```

## Maintenance Guide

### Adding a New DSCP Value

1. **Add constant to `dscp_config.py`:**
```python
DSCP_CS5 = 40  # Class Selector 5 (Voice)
```

2. **Add to mappings:**
```python
DSCP_TO_QUEUE[40] = 2  # Map to appropriate queue
DSCP_DESCRIPTIONS[40] = "CS5 (Voice) - Voice Traffic"
```

3. **Use in publisher:**
```python
from shared.mqtt.dscp_config import DSCP_CS5
DSCP_VALUE = DSCP_CS5
```

### Updating DSCP Logic

To change how DSCP is set (e.g., add logging, error handling):

1. **Edit `shared/utils/dscp_utils.py`** only
2. All publishers automatically use the new implementation
3. No need to modify individual publisher files

### GitHub Best Practices

When pushing to GitHub:

```bash
git add shared/utils/dscp_utils.py
git add shared/mqtt/dscp_config.py
git add scenarios/*/publisher_dscp*.py

git commit -m "Centralize DSCP configuration in shared modules

- Created shared/utils/dscp_utils.py for DSCP utilities
- Created shared/mqtt/dscp_config.py for DSCP constants
- Updated all publishers to use shared modules
- Removed code duplication across 10 publishers"
```

## Troubleshooting

### Import Error: "No module named 'shared'"

**Problem:** Python can't find shared modules

**Solution:** Ensure `PROJECT_ROOT` is added to `sys.path`:
```python
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)
```

### DSCP Not Being Set

**Problem:** Traffic not prioritized

**Checklist:**
1. ✅ Using `create_dscp_callback()` correctly
2. ✅ Callback assigned to `client.on_socket_open`
3. ✅ DSCP value in valid range (0-63)
4. ✅ Controller has matching flow rules
5. ✅ OVS queues configured properly

**Debug:**
```python
# Enable verbose logging
client.on_socket_open = create_dscp_callback(
    dscp_value=DSCP_VALUE,
    device_name=DEVICE,
    verbose=True  # ← Shows DSCP configuration
)
```

### Wrong DSCP Value

**Problem:** Using wrong constant

**Solution:** Always use constants from `dscp_config.py`:
```python
# ✅ CORRECT
from shared.mqtt.dscp_config import DSCP_VERY_HIGH
DSCP_VALUE = DSCP_VERY_HIGH

# ❌ WRONG - hardcoded value
DSCP_VALUE = 46  # Don't do this!
```

## Benefits Summary

### For Development
- ✅ Write DSCP publisher in **5 lines** instead of 20
- ✅ No need to remember DSCP value calculations
- ✅ Built-in error handling and validation
- ✅ Self-documenting code with constants

### For Maintenance
- ✅ Fix bugs **once** instead of 10 times
- ✅ Add features to all publishers simultaneously
- ✅ Easy to add new DSCP values
- ✅ Consistent behavior across all publishers

### For Collaboration
- ✅ Clean, professional code structure
- ✅ GitHub-friendly (no duplication)
- ✅ Easy code review
- ✅ Clear separation of concerns

### For Research
- ✅ Focus on experiments, not infrastructure
- ✅ Quick to create new test scenarios
- ✅ Reliable, tested implementation
- ✅ Easy to explain in papers/thesis

## References

- **RFC 2474** - Definition of the Differentiated Services Field (DS Field) in the IPv4 and IPv6 Headers
- **RFC 2597** - Assured Forwarding PHB Group
- **RFC 3246** - An Expedited Forwarding PHB

## Version History

- **v1.0** - Initial modularization (2025-11-16)
  - Created `shared/utils/dscp_utils.py`
  - Created `shared/mqtt/dscp_config.py`
  - Updated 10 publishers (Scenarios 05 & 06)
  - Centralized DSCP configuration logic
