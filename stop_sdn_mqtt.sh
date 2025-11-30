#!/bin/bash
# ==========================================
# Script Stop MQTT-SDN Simulation
# ==========================================
# Script ini menghentikan semua komponen MQTT-SDN
# KECUALI Ryu Controller (biarkan running untuk restart cepat)

echo "=================================================="
echo "[STOP] Menghentikan MQTT-SDN Simulation..."
echo "=================================================="

# Warna untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function untuk cek dan kill proses (graceful shutdown)
kill_process() {
    local process_name=$1
    local display_name=$2
    local graceful_wait=${3:-2}  # Default 2 seconds wait

    if pgrep -f "$process_name" > /dev/null; then
        echo -e "${YELLOW}[STOPPING]${NC} $display_name..."

        # Try graceful shutdown first (SIGTERM)
        sudo pkill -TERM -f "$process_name"
        sleep "$graceful_wait"

        # Check if still running
        if pgrep -f "$process_name" > /dev/null; then
            echo -e "${YELLOW}[FORCE STOP]${NC} $display_name (graceful shutdown timeout)..."
            sudo pkill -9 -f "$process_name"
            sleep 0.5
        fi

        # Final verification
        if pgrep -f "$process_name" > /dev/null; then
            echo -e "${RED}[FAILED]${NC} $display_name masih running!"
        else
            echo -e "${GREEN}[STOPPED]${NC} $display_name"
        fi
    else
        echo -e "${YELLOW}[INFO]${NC} $display_name tidak running"
    fi
}

# 1. Stop MQTT Publishers
echo ""
echo "=== Stopping MQTT Publishers ==="
kill_process "publisher_normal.py" "Publisher Normal (h2)"
kill_process "publisher_anomaly.py" "Publisher Anomaly (h1)"

# 2. Stop MQTT Subscriber (with extended graceful period for cleanup)
echo ""
echo "=== Stopping MQTT Subscriber ==="
kill_process "subscriber_enhanced.py" "Enhanced Subscriber (h3)" 5
kill_process "subscriber_log.py" "Subscriber (h3)" 3
kill_process "subscriber.py" "Subscriber Alternative" 2

# 3. Stop Mosquitto Broker
echo ""
echo "=== Stopping MQTT Broker ==="
kill_process "mosquitto" "Mosquitto Broker (h3)"

# 4. Stop Mininet Topology
echo ""
echo "=== Stopping Mininet Topology ==="
kill_process "mininet_topology" "Mininet Topology"

# 5. Cleanup Mininet Network
echo ""
echo "=== Cleaning up Mininet Network ==="
sudo mn -c 2>&1 | grep -E "(Removing|Cleanup)" || echo -e "${GREEN}[OK]${NC} Mininet cleanup complete"

# 6. Cleanup stale processes (optional, aggressive)
echo ""
echo "=== Cleanup Stale Processes ==="
sudo pkill -f "mnexec" 2>/dev/null && echo -e "${GREEN}[CLEANED]${NC} mnexec processes" || echo -e "${YELLOW}[INFO]${NC} No mnexec processes"

# 7. Verifikasi semua sudah berhenti
echo ""
echo "=================================================="
echo "[VERIFICATION] Checking remaining processes..."
echo "=================================================="

check_running() {
    local process=$1
    local name=$2
    if pgrep -f "$process" > /dev/null; then
        echo -e "${RED}✗${NC} $name masih running (PID: $(pgrep -f "$process"))"
        return 1
    else
        echo -e "${GREEN}✓${NC} $name stopped"
        return 0
    fi
}

ALL_STOPPED=true

check_running "publisher_normal" "Publisher Normal" || ALL_STOPPED=false
check_running "publisher_anomaly" "Publisher Anomaly" || ALL_STOPPED=false
check_running "subscriber_enhanced" "Enhanced Subscriber" || ALL_STOPPED=false
check_running "subscriber_log" "Subscriber" || ALL_STOPPED=false
check_running "mosquitto" "Mosquitto" || ALL_STOPPED=false
check_running "mininet_topology" "Mininet" || ALL_STOPPED=false

# 8. Status Ryu Controller (tidak di-stop)
echo ""
echo "=== Ryu Controller Status ==="
if pgrep -f "ryu-manager" > /dev/null; then
    RYU_PID=$(pgrep -f "ryu-manager")
    echo -e "${GREEN}✓${NC} Ryu Controller masih running (PID: $RYU_PID)"
    echo -e "${YELLOW}[INFO]${NC} Ryu Controller TIDAK dihentikan (siap untuk restart cepat)"
    echo "      Untuk stop Ryu: pkill -9 -f ryu-manager"
else
    echo -e "${YELLOW}[INFO]${NC} Ryu Controller tidak running"
fi

# 9. Cek Open vSwitch
echo ""
echo "=== Open vSwitch Status ==="
if sudo ovs-vsctl list-br 2>/dev/null | grep -q "s1"; then
    echo -e "${YELLOW}[INFO]${NC} Switch s1 masih ada (normal jika Ryu running)"
else
    echo -e "${GREEN}✓${NC} Tidak ada switch terdaftar"
fi

# 10. Summary
echo ""
echo "=================================================="
if [ "$ALL_STOPPED" = true ]; then
    echo -e "${GREEN}[SUCCESS]${NC} Semua komponen MQTT-SDN telah dihentikan!"
else
    echo -e "${YELLOW}[WARNING]${NC} Beberapa proses masih running. Cek di atas."
fi
echo "=================================================="

# 11. Informasi file log (opsional cleanup)
echo ""
echo "=== Log Files ==="
echo "Log files tersimpan di /home/mqtt-sdn/logs/"
echo "Metrics files: mqtt_metrics_log.csv, metrics_summary.txt"
echo ""
read -p "Hapus semua log files dan metrics? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f /home/mqtt-sdn/logs/*.log
    rm -f /home/mqtt-sdn/mqtt_delay_log.csv
    rm -f /home/mqtt-sdn/mqtt_metrics_log.csv
    rm -f /home/mqtt-sdn/metrics_summary.txt
    echo -e "${GREEN}[CLEANED]${NC} Log files dan metrics dihapus"
else
    echo -e "${YELLOW}[KEPT]${NC} Log files dan metrics tetap tersimpan"
fi

echo ""
echo "=================================================="
echo "Untuk menjalankan ulang simulasi:"
echo "  1. Pastikan Ryu Controller running:"
echo "     ps aux | grep ryu-manager"
echo "  2. Jalankan: sudo ./run_sdn_mqtt.sh"
echo "=================================================="
