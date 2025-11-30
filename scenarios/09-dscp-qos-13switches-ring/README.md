# Scenario 09: DSCP-Based QoS with Ring Topology

## Overview

This scenario implements a ring topology at the aggregation layer for redundancy.
All aggregation switches are connected to the core AND to each other forming a ring.

## Topology

```
                                    ┌──────────┐
                                    │  BROKER  │
                                    │ 10.0.0.1 │
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
       ┌────────┼────────┐      ┌────────┼────────┐      ┌────────┼────────┐
       │        │        │      │        │        │      │        │        │
      s5       s6       s7     s8       s9      s10    s11      s12      s13
     EDGE     EDGE     EDGE   EDGE     EDGE     EDGE   EDGE     EDGE     EDGE
       │        │        │      │        │        │      │        │        │
    [A][N]   [A][N]   [A][N]  [A][N]   [A][N]   [A][N]  [A][N]   [A][N]   [A][N]

    ═══════════════      ═══════════════════      ═══════════════════════
        FLOOR 1               FLOOR 2                    FLOOR 3
       10.0.1.x              10.0.2.x                   10.0.3.x
```

## Network Specifications

| Component | Count | Description |
|-----------|-------|-------------|
| **Core Switch** | 1 | s1 (broker connected) |
| **Aggregation Switches** | 3 | s2, s3, s4 (ring connected) |
| **Edge Switches** | 9 | s5-s13 (3 per floor) |
| **Publishers** | 18 | 9 anomaly + 9 normal |
| **Total Switches** | 13 | |
| **Total Links** | 15 | 3 core-agg + 3 ring + 9 agg-edge |

## Ring Links (Redundancy)

| Link | Description |
|------|-------------|
| s2 ↔ s3 | Floor 1 ↔ Floor 2 |
| s3 ↔ s4 | Floor 2 ↔ Floor 3 |
| s2 ↔ s4 | Floor 1 ↔ Floor 3 |

## Redundancy Example

If link **s2 ↔ s1** fails:
```
Traffic from Floor 1 can use:
  s5 → s2 → s3 → s1 → Broker  (via Floor 2)
  s5 → s2 → s4 → s1 → Broker  (via Floor 3)
```

## Running the Experiment

```bash
cd /home/mqtt-sdn/scenarios/09-dscp-qos-13switches-ring

# Run for 2 minutes
sudo ./run_experiment.sh 120

# Run for 5 minutes
sudo ./run_experiment.sh 300
```

## Results

Results are saved to:
```
/home/mqtt-sdn/results/09-dscp-qos-13switches-ring/run_YYYY-MM-DD_HH-MM-SS/
├── mqtt_metrics_log.csv      # Raw metrics data
└── metrics_summary.txt        # Summary statistics
```

## DSCP Priority Levels

| DSCP Value | Class | Queue | Bandwidth |
|------------|-------|-------|-----------|
| 46 | EF (Very High) | 1 | 60-80% |
| 34 | AF41 (High) | 2 | 45-60% |
| 26 | AF31 (Medium) | 3 | 30-45% |
| 10 | AF11 (Low) | 4 | 15-30% |
| 0 | BE (Best Effort) | 5 | 5-15% |

## Files

| File | Description |
|------|-------------|
| `topology_config.py` | Network topology with ring |
| `controller_dscp.py` | Ryu controller |
| `run_experiment.sh` | Experiment runner |
| `publisher_dscp46_veryhigh.py` | Anomaly publisher |
| `publisher_dscp0_besteffort.py` | Normal publisher |
