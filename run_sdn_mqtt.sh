#!/bin/bash
# ==========================================
# SDN + MQTT Automation Script (Auto-cleanup & Start Mininet)
# ==========================================
# Usage: ./run_sdn_mqtt.sh [duration]
# Examples:
#   ./run_sdn_mqtt.sh          # Run until manually stopped
#   ./run_sdn_mqtt.sh 60       # Run for 60 seconds
#   ./run_sdn_mqtt.sh 5m       # Run for 5 minutes
#   ./run_sdn_mqtt.sh 1h       # Run for 1 hour

LOG_DIR="/home/mqtt-sdn/logs"
MQTT_DIR="/home/mqtt-sdn/minimap"
MININET_LOG="$LOG_DIR/mininet.log"

mkdir -p "$LOG_DIR"

# ==========================================
# PARSE PARAMETER WAKTU (DURATION)
# ==========================================
DURATION_SECONDS=0
AUTO_STOP=false

if [ $# -gt 0 ]; then
    DURATION_INPUT=$1

    # Parse format: 30, 60s, 5m, 1h
    if [[ "$DURATION_INPUT" =~ ^([0-9]+)s?$ ]]; then
        # Format: 30 atau 30s (detik)
        DURATION_SECONDS="${BASH_REMATCH[1]}"
    elif [[ "$DURATION_INPUT" =~ ^([0-9]+)m$ ]]; then
        # Format: 5m (menit)
        MINUTES="${BASH_REMATCH[1]}"
        DURATION_SECONDS=$((MINUTES * 60))
    elif [[ "$DURATION_INPUT" =~ ^([0-9]+)h$ ]]; then
        # Format: 1h (jam)
        HOURS="${BASH_REMATCH[1]}"
        DURATION_SECONDS=$((HOURS * 3600))
    else
        echo "[ERROR] Format waktu tidak valid: $DURATION_INPUT"
        echo ""
        echo "Format yang valid:"
        echo "  60 atau 60s  = 60 detik"
        echo "  5m           = 5 menit"
        echo "  1h           = 1 jam"
        exit 1
    fi

    AUTO_STOP=true
    echo "=================================================="
    echo "[AUTO-STOP] Simulasi akan berjalan selama: $DURATION_INPUT"
    echo "            ($DURATION_SECONDS detik)"
    echo "=================================================="
    sleep 2
fi

# ==========================================
# 1. CEK RYU CONTROLLER
# ==========================================
echo "=================================================="
echo "[PREREQUISITE] Mengecek Ryu Controller..."
echo "=================================================="

if ! curl -s http://127.0.0.1:8080/stats/switches > /dev/null 2>&1; then
    echo "[ERROR] Ryu Controller belum running!"
    echo ""
    echo "Silakan jalankan Ryu Controller dulu di terminal terpisah:"
    echo "  cd /home/mqtt-sdn"
    echo "  ./run_ryu_controller.sh"
    echo ""
    echo "Tunggu sampai muncul pesan:"
    echo "  [SUCCESS] Ryu Controller sedang berjalan."
    echo "  - REST API: http://127.0.0.1:8080"
    echo ""
    exit 1
fi

echo "[SUCCESS] Ryu Controller terdeteksi di http://127.0.0.1:8080"
sleep 1

# ==========================================
# 2. CLEANUP - Hapus proses dan network lama
# ==========================================
echo "=================================================="
echo "[CLEANUP] Membersihkan environment lama..."
echo "=================================================="

# Stop all existing MQTT processes (TIDAK touch Ryu!)
sudo pkill -f mosquitto 2>/dev/null
sudo pkill -f publisher 2>/dev/null
sudo pkill -f subscriber 2>/dev/null

# Stop Mininet Python process
sudo pkill -f mininet_topology 2>/dev/null

# Cleanup Mininet
sudo mn -c 2>/dev/null

# Remove old temporary scripts
rm -f /tmp/mininet_topology_*.py 2>/dev/null

echo "[INFO] Cleanup selesai."
sleep 1

# ==========================================
# 3. START MININET - Launch topology
# ==========================================
echo "=================================================="
echo "[MININET] Menjalankan Mininet topology..."
echo "=================================================="

# Buat temporary Python script untuk run Mininet tanpa CLI
MININET_SCRIPT="/tmp/mininet_topology_$$.py"
cat > "$MININET_SCRIPT" << PYTHON_SCRIPT
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
import time
import signal
import sys

MQTT_DIR = "$MQTT_DIR"
LOG_DIR = "$LOG_DIR"

def cleanup(net):
    info('*** Stopping MQTT components\\n')
    h1 = net.get('h1')
    h2 = net.get('h2')
    h3 = net.get('h3')

    h1.cmd('pkill -f publisher_anomaly')
    h2.cmd('pkill -f publisher_normal')
    h3.cmd('pkill -f subscriber_log')
    h3.cmd('pkill -f mosquitto')

    info('*** Stopping network\\n')
    net.stop()
    sys.exit(0)

setLogLevel('info')
net = Mininet(controller=RemoteController, autoSetMacs=True)

# Add controller
c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

# Add switch with OpenFlow 1.3
s1 = net.addSwitch('s1', protocols='OpenFlow13')

# Add hosts
h1 = net.addHost('h1', ip='10.0.0.1/24')
h2 = net.addHost('h2', ip='10.0.0.2/24')
h3 = net.addHost('h3', ip='10.0.0.3/24')

# Add links
net.addLink(h1, s1)
net.addLink(h2, s1)
net.addLink(h3, s1)

# Start network
net.start()
info('*** Network started successfully\\n')
info('*** Hosts: h1(10.0.0.1), h2(10.0.0.2), h3(10.0.0.3)\\n')

# Wait for network to stabilize
time.sleep(3)

# Start MQTT components
info('*** Starting MQTT Broker on h3\\n')
h3.cmd('mosquitto -v -c /home/mqtt-sdn/mosquitto.conf > {}/mosquitto.log 2>&1 &'.format(LOG_DIR))
time.sleep(2)

info('*** Starting Subscriber on h3\\n')
# Use enhanced subscriber for comprehensive metrics (delay, jitter, packet loss)
h3.cmd('python3 {}/subscriber_enhanced.py > {}/subscriber.log 2>&1 &'.format(MQTT_DIR, LOG_DIR))
time.sleep(2)

info('*** Starting Publisher Normal on h2\\n')
h2.cmd('python3 {}/publisher_normal.py > {}/publisher_normal.log 2>&1 &'.format(MQTT_DIR, LOG_DIR))
time.sleep(2)

info('*** Starting Publisher Anomaly on h1\\n')
h1.cmd('python3 {}/publisher_anomaly.py > {}/publisher_anomaly.log 2>&1 &'.format(MQTT_DIR, LOG_DIR))

info('*** All MQTT components started\\n')

# Setup signal handlers
signal.signal(signal.SIGTERM, lambda sig, frame: cleanup(net))
signal.signal(signal.SIGINT, lambda sig, frame: cleanup(net))

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    cleanup(net)
PYTHON_SCRIPT

# Start Mininet di background menggunakan Python script
nohup python3 "$MININET_SCRIPT" > "$MININET_LOG" 2>&1 &
MININET_PID=$!
echo "[INFO] Mininet PID: $MININET_PID"
echo "[INFO] Python script: $MININET_SCRIPT"

# ==========================================
# 4. WAIT - Tunggu Mininet hosts siap
# ==========================================
echo "[INFO] Menunggu Mininet hosts siap..."

MAX_WAIT=30
COUNT=0
HOSTS_READY=false

while [ $COUNT -lt $MAX_WAIT ]; do
    # Cek apakah process mininet:h1, h2, h3 sudah ada
    H1_RUNNING=$(ps aux | grep "mininet:h1" | grep -v grep | wc -l)
    H2_RUNNING=$(ps aux | grep "mininet:h2" | grep -v grep | wc -l)
    H3_RUNNING=$(ps aux | grep "mininet:h3" | grep -v grep | wc -l)

    if [ $H1_RUNNING -gt 0 ] && [ $H2_RUNNING -gt 0 ] && [ $H3_RUNNING -gt 0 ]; then
        HOSTS_READY=true
        break
    fi

    echo -n "."
    sleep 1
    COUNT=$((COUNT + 1))
done

echo ""

if [ "$HOSTS_READY" = false ]; then
    echo "[ERROR] Timeout menunggu Mininet hosts!"
    echo "[ERROR] Cek log di: $MININET_LOG"
    echo "[ERROR] Pastikan Ryu Controller sudah running di 127.0.0.1:6633"
    exit 1
fi

echo "[SUCCESS] Mininet hosts (h1, h2, h3) sudah siap!"

# Tunggu tambahan agar MQTT components siap (dijalankan dari Python script)
echo "[INFO] Menunggu MQTT components siap..."
sleep 8

# ==========================================
# 5. SUMMARY
# ==========================================
echo "=================================================="
echo "[SUCCESS] Semua komponen telah dijalankan!"
echo "=================================================="
echo "✓ Ryu Controller (running di terminal terpisah)"
echo "✓ Mininet topology: single,3 (h1, h2, h3)"
echo "✓ Switch s1: OpenFlow 1.3 → Controller @ 127.0.0.1:6633"
echo "✓ Broker MQTT di h3 (auto-started by Mininet)"
echo "✓ Subscriber di h3 (logging to CSV, auto-started)"
echo "✓ Publisher normal di h2 (Queue 2, Priority 10, auto-started)"
echo "✓ Publisher anomaly di h1 (Queue 1, Priority 20, auto-started)"
echo ""
echo "Log files:"
echo "  - Mininet    : $MININET_LOG"
echo "  - Mosquitto  : $LOG_DIR/mosquitto.log"
echo "  - Subscriber : $LOG_DIR/subscriber.log"
echo "  - Pub Normal : $LOG_DIR/publisher_normal.log"
echo "  - Pub Anomaly: $LOG_DIR/publisher_anomaly.log"
echo "  - CSV Data   : mqtt_delay_log.csv (di h3's working directory)"
echo ""
echo "Monitoring commands:"
echo "  tail -f $LOG_DIR/subscriber.log"
echo "  curl http://127.0.0.1:8080/stats/flow/1"
echo "  curl http://127.0.0.1:8080/stats/switches"
echo ""
echo "Untuk stop semua (TIDAK akan stop Ryu Controller):"
echo "  sudo pkill -f mininet_topology"
echo "  sudo mn -c"
echo "  sudo pkill -f mosquitto"
echo ""
echo "Atau jalankan ulang script ini (auto cleanup):"
echo "  sudo ./run_sdn_mqtt.sh [duration]"
echo "=================================================="

# ==========================================
# 6. AUTO-STOP (jika ada parameter waktu)
# ==========================================
if [ "$AUTO_STOP" = true ]; then
    echo ""
    echo "=================================================="
    echo "[AUTO-STOP] Simulasi berjalan untuk $DURATION_SECONDS detik..."
    echo "=================================================="

    # Countdown dengan progress bar
    ELAPSED=0
    while [ $ELAPSED -lt $DURATION_SECONDS ]; do
        # Calculate remaining time
        REMAINING=$((DURATION_SECONDS - ELAPSED))

        # Format waktu
        if [ $REMAINING -ge 3600 ]; then
            HOURS=$((REMAINING / 3600))
            MINS=$(( (REMAINING % 3600) / 60 ))
            SECS=$((REMAINING % 60))
            TIME_STR="${HOURS}h ${MINS}m ${SECS}s"
        elif [ $REMAINING -ge 60 ]; then
            MINS=$((REMAINING / 60))
            SECS=$((REMAINING % 60))
            TIME_STR="${MINS}m ${SECS}s"
        else
            TIME_STR="${REMAINING}s"
        fi

        # Progress bar
        PERCENT=$((ELAPSED * 100 / DURATION_SECONDS))
        BAR_LENGTH=40
        FILLED=$((PERCENT * BAR_LENGTH / 100))
        BAR=$(printf '%*s' "$FILLED" | tr ' ' '█')
        EMPTY=$(printf '%*s' $((BAR_LENGTH - FILLED)) | tr ' ' '░')

        # Print progress (overwrite line)
        printf "\r[%3d%%] [%s%s] Remaining: %s   " "$PERCENT" "$BAR" "$EMPTY" "$TIME_STR"

        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done

    echo ""
    echo ""
    echo "=================================================="
    echo "[AUTO-STOP] Waktu simulasi selesai!"
    echo "=================================================="

    # Collect final statistics
    echo "[INFO] Mengumpulkan statistik akhir..."

    # Count messages in CSV
    if [ -f "/home/mqtt-sdn/mqtt_delay_log.csv" ]; then
        MSG_COUNT=$(wc -l < /home/mqtt-sdn/mqtt_delay_log.csv)
        MSG_COUNT=$((MSG_COUNT - 1))  # Exclude header
        echo "  ✓ Total messages: $MSG_COUNT"
    fi

    # Get flow statistics
    if command -v curl &> /dev/null; then
        FLOW_STATS=$(curl -s http://127.0.0.1:8080/stats/flow/1 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "  ✓ Flow statistics saved"
        fi
    fi

    echo ""
    echo "[INFO] Menghentikan simulasi..."

    # Call stop script
    /home/mqtt-sdn/stop_sdn_mqtt.sh <<< "n"

    echo ""
    echo "=================================================="
    echo "[COMPLETE] Simulasi selesai!"
    echo "=================================================="
    echo "Data tersimpan di:"
    echo "  - CSV: /home/mqtt-sdn/mqtt_delay_log.csv"
    echo "  - Logs: /home/mqtt-sdn/logs/"
    echo ""
    echo "Untuk analisis data, gunakan:"
    echo "  cat /home/mqtt-sdn/mqtt_delay_log.csv"
    echo "  tail -50 /home/mqtt-sdn/mqtt_delay_log.csv"
    echo "=================================================="
else
    echo ""
    echo "[INFO] Simulasi berjalan (manual stop mode)"
    echo "[INFO] Untuk menghentikan, jalankan: sudo ./stop_sdn_mqtt.sh"
fi
