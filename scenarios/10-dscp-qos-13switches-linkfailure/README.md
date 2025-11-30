# Scenario 10: Link Failure Test

## Overview

This scenario uses the **same topology as Scenario 09** but includes a **link failure simulation** to prove that the ring topology provides redundancy.

## Topology

Same as Scenario 09:
```
                                    ┌──────────┐
                                    │  BROKER  │
                                    └────┬─────┘
                                         │
                                   ┌─────┴─────┐
                                   │    s1     │
                                   │   CORE    │
                                   └─────┬─────┘
                                         │
                ┌────────────────────────┼────────────────────────┐
                │                        │                        │
          ┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐
          │    s2     │◄══════════►│    s3     │◄══════════►│    s4     │
          │   AGG 1   │            │   AGG 2   │            │   AGG 3   │
          │  Floor 1  │◄══════════════════════════════════►│  Floor 3  │
          └─────┬─────┘            └─────┬─────┘            └─────┬─────┘
                │                        │                        │
                X (DISABLED)             │                        │
                │                        │                        │
            3 EDGE                    3 EDGE                   3 EDGE
```

## Experiment Phases

| Phase | Time | Link s2↔s1 | Description |
|-------|------|------------|-------------|
| **Phase 1** | 0-30s | ✅ UP | Normal operation |
| **Phase 2** | 30s+ | ❌ DOWN | Redundancy test |

## What Happens

### Phase 1: Normal Operation (0-30 seconds)
- All links active
- Floor 1 traffic: `s5 → s2 → s1 → Broker` (direct path)
- Baseline metrics collected

### Link Failure Event (at 30 seconds)
- Link `s2-eth1` (s2 ↔ s1) is disabled
- Multiple verification methods confirm link is down

### Phase 2: Redundancy Test (30+ seconds)
- Floor 1 traffic must use ring: 
  - `s5 → s2 → s3 → s1 → Broker` or
  - `s5 → s2 → s4 → s1 → Broker`
- Floor 2 & 3 traffic unaffected
- **Expected: 0% packet loss** (proves redundancy works!)

## Verification Methods

The experiment uses 3 methods to verify link is down:

1. **ip link show** - Check interface state
2. **operstate** - Check /sys/class/net/interface/operstate
3. **ovs-vsctl** - Check OVS switch status

## Expected Results

| Metric | Phase 1 (Normal) | Phase 2 (Link Down) |
|--------|------------------|---------------------|
| Floor 1 Path | 2 hops | 3 hops |
| Floor 1 Delay | Baseline | Higher (extra hop) |
| Packet Loss | 0% | **0%** ✓ |
| Floor 2 & 3 | Normal | Normal (unaffected) |

## Running the Experiment

```bash
cd /home/mqtt-sdn/scenarios/10-dscp-qos-13switches-linkfailure

# Run for 2 minutes (minimum recommended)
sudo ./run_experiment.sh 120

# Run for 5 minutes
sudo ./run_experiment.sh 300
```

## Output Files

```
/home/mqtt-sdn/results/10-dscp-qos-13switches-linkfailure/run_YYYY-MM-DD_HH-MM-SS/
├── mqtt_metrics_log.csv      # Raw metrics with phase info
├── metrics_summary.txt        # Summary statistics
└── link_failure_log.txt       # Link failure events & verification
```

## Analyzing Results

### 1. Check Link Failure Log
```bash
cat link_failure_log.txt
```

Shows:
- Exact time of link failure
- Verification results (3 methods)
- Phase transitions

### 2. Compare Delay Before/After
```bash
# Phase 1 (normal) - first 30 seconds
grep "phase1" mqtt_metrics_log.csv | ...

# Phase 2 (link down) - after 30 seconds
grep "phase2" mqtt_metrics_log.csv | ...
```

### 3. Check Packet Loss
- If 0% packet loss in Phase 2: **Redundancy WORKS!**
- If packet loss > 0%: Check ring links

## Files

| File | Description |
|------|-------------|
| `topology_config.py` | Topology with link failure logic |
| `controller_dscp.py` | Same as Scenario 09 |
| `run_experiment.sh` | Experiment runner |
| `publisher_dscp*.py` | Same as Scenario 09 |
