#!/bin/bash
# Quick Test Script - Scenario 03 dengan All Fixes
# 
# This script will:
# 1. Start controller_v2.py (MAC Learning)
# 2. Run 5-minute test
# 3. Generate summary
# 4. Show if priority works!

set -e

SCENARIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"

echo "=========================================="
echo "  Scenario 03 - Priority Test (FIXED)"
echo "=========================================="
echo ""
echo "Fixes Applied:"
echo "  ✅ Condition 1: High message rate (80% utilization)"
echo "  ✅ Condition 2: MAC Learning Controller (no OFPP_NORMAL)"
echo "  ✅ Condition 3: OVS queues properly configured"
echo ""
echo "Expected Result:"
echo "  - Anomaly delay: 20-40ms (Low)"
echo "  - Normal delay: 60-120ms (High)"
echo "  - Difference: Normal 2-3x slower!"
echo ""
echo "=========================================="
echo ""

# Check if controller already running
if pgrep -f "ryu-manager.*controller_v2.py" > /dev/null; then
    echo "[INFO] Controller already running"
else
    echo "[1/3] Starting MAC Learning Controller..."
    source /home/aldi/ryu39/bin/activate
    /home/aldi/ryu39/bin/python3.9 -u /home/aldi/ryu39/bin/ryu-manager \
        "$SCENARIO_DIR/controller_v2.py" \
        ryu.app.ofctl_rest > "$PROJECT_ROOT/logs/ryu.log" 2>&1 &
    
    # Wait for controller
    sleep 3
    echo "  ✓ Controller ready"
fi

echo ""
echo "[2/3] Running 5-minute test..."
echo ""

cd "$PROJECT_ROOT"
sudo ./run_experiment.sh --scenario 03-tc-based-7switches --duration 5m

echo ""
echo "[3/3] Check results..."
echo ""

# Find latest result
LATEST_RESULT=$(ls -td results/03-tc-based-7switches/run_* 2>/dev/null | head -1)

if [ -f "$LATEST_RESULT/metrics_summary.txt" ]; then
    cat "$LATEST_RESULT/metrics_summary.txt"
    
    echo ""
    echo "=========================================="
    echo "  ANALYSIS"
    echo "=========================================="
    echo ""
    
    # Extract delays
    ANOMALY_DELAY=$(grep "Avg Delay" "$LATEST_RESULT/metrics_summary.txt" | head -1 | awk '{print $4}')
    NORMAL_DELAY=$(grep "Avg Delay" "$LATEST_RESULT/metrics_summary.txt" | tail -1 | awk '{print $4}')
    
    echo "Anomaly Delay: $ANOMALY_DELAY"
    echo "Normal Delay:  $NORMAL_DELAY"
    echo ""
    
    # Compare
    python3 << EOF
anomaly = float("$ANOMALY_DELAY")
normal = float("$NORMAL_DELAY")
diff = normal - anomaly
diff_pct = (diff / anomaly) * 100 if anomaly > 0 else 0

print(f"Difference: {diff:.2f}ms ({diff_pct:.1f}% slower)")
print()

if diff_pct > 50:
    print("✅ PRIORITY WORKS! Normal significantly slower than Anomaly")
    print("   The fix is SUCCESSFUL!")
elif diff_pct > 20:
    print("⚠️  PARTIAL SUCCESS. Some priority effect visible.")
    print("   May need more congestion or verification.")
elif diff_pct > -5 and diff_pct < 5:
    print("❌ NO PRIORITY EFFECT. Still same issue.")
    print("   Need to debug further:")
    print("   1. Check if queues attached: sudo ovs-vsctl get port s4-eth1 qos")
    print("   2. Check utilization in test")
    print("   3. Verify controller using controller_v2.py")
else:
    print("❌ REVERSED! Anomaly slower than Normal!")
    print("   Something is wrong with classification.")
EOF
    
else
    echo "No summary found. Check if test completed successfully."
fi

echo ""
echo "=========================================="
