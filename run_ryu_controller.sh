#!/bin/bash
# ==========================================
# Script Otomatis Menjalankan Ryu Controller
# ==========================================

# --- Konfigurasi path environment & log ---
VENV_PATH="$HOME/ryu39"
LOG_DIR="$HOME/ryu_logs"

# --- Aktifkan virtual environment ---
if [ ! -d "$VENV_PATH" ]; then
    echo "[ERROR] Virtual environment tidak ditemukan di $VENV_PATH"
    echo "Silakan buat dengan: python3 -m venv ~/ryu39"
    exit 1
fi

echo "[INFO] Mengaktifkan virtual environment..."
source "$VENV_PATH/bin/activate"

# --- Pastikan folder log ada ---
mkdir -p "$LOG_DIR"

# --- Cek versi Ryu ---
echo "[INFO] Mengecek versi Ryu..."
ryu-manager --version

if [ $? -ne 0 ]; then
    echo "[ERROR] Ryu tidak ditemukan di environment ini!"
    echo "Pastikan kamu sudah menginstalnya di venv dengan: pip install ryu"
    deactivate
    exit 1
fi

# --- Jalankan Ryu Controller ---
echo "[INFO] Menjalankan Ryu Controller..."

# Cek apakah priority_controller.py ada
CONTROLLER_PATH="/home/mqtt-sdn/priority_controller.py"
if [ ! -f "$CONTROLLER_PATH" ]; then
    echo "[ERROR] File priority_controller.py tidak ditemukan di $CONTROLLER_PATH"
    deactivate
    exit 1
fi

LOG_FILE="$LOG_DIR/ryu_$(date +%Y%m%d_%H%M%S).log"
nohup ryu-manager "$CONTROLLER_PATH" ryu.app.ofctl_rest > "$LOG_FILE" 2>&1 &

RYU_PID=$!
sleep 3

# Verifikasi Ryu benar-benar running
if ! ps -p $RYU_PID > /dev/null; then
    echo "[ERROR] Ryu Controller gagal start! Cek log:"
    echo "  tail -f $LOG_FILE"
    deactivate
    exit 1
fi

echo "=================================================="
echo "[SUCCESS] Ryu Controller sedang berjalan."
echo "  - PID: $RYU_PID"
echo "  - Log file: $LOG_FILE"
echo "  - Controller: priority_controller.py"
echo "  - REST API: http://127.0.0.1:8080"
echo "  - OpenFlow: 127.0.0.1:6633"
echo ""
echo "Flow rules yang akan diinstall:"
echo "  - Anomaly traffic (10.0.0.1 → port 1883): Queue 1, Priority 20"
echo "  - Normal traffic (10.0.0.2 → port 1883): Queue 2, Priority 10"
echo ""
echo "Tekan 'deactivate' untuk keluar dari venv."
echo "=================================================="

# --- Jaga agar environment tetap aktif ---
bash
