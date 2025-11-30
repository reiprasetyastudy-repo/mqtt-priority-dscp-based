# Scenario 03: MAC Learning + OVS Queue (FIXED)

## Overview
**FIXED VERSION** dengan proper MAC Learning Controller dan OVS Queue configuration yang memenuhi SEMUA 3 kondisi untuk priority mechanism work!

## ⚠️ CRITICAL FIXES dari Scenario 02

### Masalah di Scenario 02:
1. ❌ **SetQueue + OFPP_NORMAL** → Queue di-ignore!
2. ❌ **Utilization rendah** (32%) → Tidak ada congestion
3. ❌ **Queue tidak ter-attach** ke port

### Fix di Scenario 03:
1. ✅ **MAC Learning Controller** → Forward ke explicit port (NO OFPP_NORMAL!)
2. ✅ **High message rate** (50 msg/s) → 80% utilization → CONGESTION!
3. ✅ **Proper OVS queue config** → Queue ter-attach ke semua port

## 3 Conditions for Priority to Work

Priority mechanism **HANYA BEKERJA** jika 3 kondisi ini terpenuhi:

### Condition 1: Ada Congestion (✅ FIXED)
```
Current:  800 Kbps / 1000 Kbps = 80% utilization
Result:   Packets ANTRI → Priority visible!
```

### Condition 2: Queue Mechanism Works (✅ FIXED)
```
MAC Learning Controller:
- Track MAC → port mapping
- Install flow dengan EXPLICIT output port
- SetQueue action tidak di-bypass!
```

### Condition 3: Proper Classification (✅ Already OK)
```
Controller classify by IP:
- Odd IPs (.1, .3) → Queue 1 (High priority)
- Even IPs (.2, .4) → Queue 2 (Low priority)
```

## How to Run

```bash
cd /home/mqtt-sdn

# Run with auto-managed controller
sudo ./run_experiment.sh --scenario 03-tc-based-7switches --duration 5m
```

## Expected Results

```
ANOMALY:
  Avg Delay: 20-40 ms (LOW - High priority queue)
  Packet Loss: 0-5%

NORMAL:
  Avg Delay: 60-120 ms (HIGH - Low priority queue)
  Packet Loss: 10-20%

Difference: Normal 2-3x SLOWER ✅
```

## Technical Details

### Key Fix: MAC Learning Controller
```python
# BROKEN (Scenario 02):
actions = [OFPActionSetQueue(1), OFPActionOutput(OFPP_NORMAL)]
# OFPP_NORMAL bypass OpenFlow → Queue ignored!

# FIXED (Scenario 03):
actions = [OFPActionSetQueue(1), OFPActionOutput(learned_port)]
# Explicit port → Queue works!
```

### Network Load
```
8 publishers × 50 msg/s × 250 bytes × 8 bits = 800 Kbps
Bandwidth: 1 Mbps
Utilization: 80% → CONGESTION!
```

## Files
- `controller_v2.py` - MAC Learning Controller
- `topology_config.py` - 7-switch topology
- `run_scenario.sh` - Launcher

## Research Contribution

**Key Finding:** Priority mechanism HANYA terlihat saat:
1. Ada CONGESTION (utilization > 70%)
2. Queue mechanism properly configured
3. Controller tidak pakai OFPP_NORMAL
