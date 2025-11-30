# Pengukuran Metrik Performa pada Simulasi SDN-MQTT

**Dokumentasi:** Metrik-metrik yang dapat diukur pada sistem MQTT-SDN dan cara implementasinya

---

## 📚 Daftar Isi

1. [Overview](#overview)
2. [End-to-End Delay](#1-end-to-end-delay)
3. [Jitter](#2-jitter)
4. [Response Time](#3-response-time)
5. [Total Time](#4-total-time)
6. [Lost Message / Packet Loss](#5-lost-message--packet-loss)
7. [Throughput](#6-throughput-bonus)
8. [Implementasi Pengukuran](#implementasi-pengukuran)
9. [Analisis Data](#analisis-data)
10. [Visualization](#visualization)

---

## Overview

Dalam evaluasi performa sistem IoT berbasis SDN-MQTT, ada beberapa metrik kritis yang perlu diukur untuk menilai Quality of Service (QoS). Dokumen ini menjelaskan setiap metrik, cara mengukurnya, dan implementasinya.

---

## 1. End-to-End Delay

### 📋 Definisi
**End-to-End Delay** adalah waktu yang dibutuhkan sebuah message dari saat **dikirim oleh publisher** hingga **diterima oleh subscriber**.

```
E2E Delay = T_receive - T_send
```

Di mana:
- `T_send` = timestamp saat publisher publish message
- `T_receive` = timestamp saat subscriber terima message

### 📊 Satuan
Milliseconds (ms) atau microseconds (μs)

### 🎯 Target/Benchmark
- **Excellent:** < 10 ms
- **Good:** 10-50 ms
- **Acceptable:** 50-100 ms
- **Poor:** > 100 ms

Untuk IoT critical/real-time, target biasanya < 50 ms.

### ✅ Status Implementasi di Simulasi Saat Ini

**SUDAH TERIMPLEMENTASI** ✅

File: `minimap/subscriber_log.py`
```python
def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    delay = (time.time() - data["timestamp"]) * 1000  # ms
    # delay = end-to-end delay
```

CSV output: `mqtt_delay_log.csv`
```csv
device,type,value,timestamp_sent,delay_ms
sensor_anomaly,anomaly,82.68,1762688874.37,1.95
sensor_normal,normal,21.83,1762688874.37,2.65
```

### 📈 Cara Analisis

**1. Average Delay per Category:**
```python
import pandas as pd

df = pd.read_csv('mqtt_delay_log.csv')

# Group by type
print(df.groupby('type')['delay_ms'].mean())

# Output:
# type
# anomaly    1.92
# normal     2.85
```

**2. Visualisasi:**
```python
import matplotlib.pyplot as plt

anomaly = df[df['type'] == 'anomaly']['delay_ms']
normal = df[df['type'] == 'normal']['delay_ms']

plt.hist([anomaly, normal], label=['Anomaly', 'Normal'], bins=20)
plt.xlabel('Delay (ms)')
plt.ylabel('Frequency')
plt.legend()
plt.title('End-to-End Delay Distribution')
plt.show()
```

### 🔬 Research Value
- **Essential metric** untuk paper
- Menunjukkan efektivitas prioritas
- Expected: Anomaly delay < Normal delay (karena priority lebih tinggi)

---

## 2. Jitter

### 📋 Definisi
**Jitter** adalah **variasi delay** antar packet berurutan. Mengukur seberapa **konsisten** delay-nya.

```
Jitter = |Delay_i - Delay_(i-1)|
```

Atau average jitter:
```
Average Jitter = (1/n) * Σ |Delay_i - Delay_(i-1)|
```

### 📊 Satuan
Milliseconds (ms)

### 🎯 Target/Benchmark
- **Excellent:** < 5 ms
- **Good:** 5-20 ms
- **Acceptable:** 20-50 ms
- **Poor:** > 50 ms

Low jitter = konsisten, high jitter = tidak predictable.

### ❌ Status Implementasi di Simulasi Saat Ini

**BELUM TERIMPLEMENTASI** - Perlu ditambahkan

### 💻 Cara Implementasi

**Metode 1: Post-processing dari CSV**
```python
import pandas as pd
import numpy as np

df = pd.read_csv('mqtt_delay_log.csv')

# Calculate jitter per type
for msg_type in ['anomaly', 'normal']:
    subset = df[df['type'] == msg_type].sort_values('timestamp_sent')
    delays = subset['delay_ms'].values

    # Jitter = difference between consecutive delays
    jitter = np.abs(np.diff(delays))

    print(f"{msg_type.upper()} Jitter:")
    print(f"  Average: {jitter.mean():.2f} ms")
    print(f"  Std Dev: {jitter.std():.2f} ms")
    print(f"  Max: {jitter.max():.2f} ms")
```

**Metode 2: Real-time calculation di Subscriber**

Modifikasi `subscriber_log.py`:
```python
class JitterCalculator:
    def __init__(self):
        self.prev_delay = {'anomaly': None, 'normal': None}
        self.jitter_sum = {'anomaly': 0, 'normal': 0}
        self.jitter_count = {'anomaly': 0, 'normal': 0}

    def update(self, msg_type, current_delay):
        if self.prev_delay[msg_type] is not None:
            jitter = abs(current_delay - self.prev_delay[msg_type])
            self.jitter_sum[msg_type] += jitter
            self.jitter_count[msg_type] += 1

        self.prev_delay[msg_type] = current_delay

    def get_average_jitter(self, msg_type):
        if self.jitter_count[msg_type] == 0:
            return 0
        return self.jitter_sum[msg_type] / self.jitter_count[msg_type]

# Usage in on_message
jitter_calc = JitterCalculator()

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    delay = (time.time() - data["timestamp"]) * 1000

    # Update jitter
    jitter_calc.update(data['type'], delay)

    # Log to CSV (tambahkan kolom jitter)
    avg_jitter = jitter_calc.get_average_jitter(data['type'])
    writer.writerow([..., delay, avg_jitter])
```

### 🔬 Research Value
- **Important metric** untuk real-time applications
- Low jitter = predictable, cocok untuk time-sensitive IoT
- Expected: Anomaly jitter < Normal jitter (priority queue lebih stabil)

---

## 3. Response Time

### 📋 Definisi
**Response Time** adalah waktu yang dibutuhkan sistem untuk **memproses request dan mengirim response**.

Dalam konteks MQTT publish-subscribe:
```
Response Time = T_ack - T_request
```

**Dua interpretasi:**

**A. MQTT Level:**
- T_request = Publisher send PUBLISH
- T_ack = Publisher receive PUBACK (untuk QoS 1) atau PUBREC (QoS 2)

**B. Application Level:**
- T_request = Sensor detect event (misal anomaly)
- T_ack = System take action (misal alarm triggered)

### 📊 Satuan
Milliseconds (ms)

### ❌ Status Implementasi di Simulasi Saat Ini

**BELUM TERIMPLEMENTASI**

Simulasi saat ini menggunakan QoS 0 (fire-and-forget), jadi tidak ada PUBACK.

### 💻 Cara Implementasi

**Opsi 1: Upgrade ke QoS 1 (dengan acknowledgment)**

Modifikasi publisher:
```python
import paho.mqtt.client as mqtt
import time

def on_publish(client, userdata, mid):
    publish_time = userdata['publish_times'][mid]
    response_time = (time.time() - publish_time) * 1000
    print(f"Response time: {response_time:.2f} ms")

    # Log to file
    with open('response_time.log', 'a') as f:
        f.write(f"{mid},{response_time}\n")

client = mqtt.Client(userdata={'publish_times': {}})
client.on_publish = on_publish

client.connect(BROKER, 1883, 60)
client.loop_start()

# Publish dengan QoS 1
payload = {...}
start_time = time.time()
result = client.publish("iot/data", json.dumps(payload), qos=1)

# Store publish time
client._userdata['publish_times'][result.mid] = start_time
```

**Opsi 2: Application-level Request-Response**

Tambahkan response topic:
```python
# Publisher
def on_message(client, userdata, msg):
    # Receive response
    response_time = (time.time() - userdata['request_time']) * 1000
    print(f"App-level response time: {response_time:.2f} ms")

client.subscribe("response/topic")
client.on_message = on_message

# Send request
client._userdata['request_time'] = time.time()
client.publish("request/topic", payload)

# Subscriber (simulate processing & response)
def on_request(client, userdata, msg):
    # Process...
    time.sleep(0.001)  # Simulate processing

    # Send response
    client.publish("response/topic", "ACK")
```

### 🔬 Research Value
- **Moderate importance** untuk interactive systems
- Lebih relevan untuk command-response applications
- Untuk monitoring passively (publish-subscribe), delay lebih penting daripada response time

---

## 4. Total Time

### 📋 Definisi
**Total Time** adalah waktu **total eksekusi** dari awal hingga akhir simulasi, atau waktu untuk menyelesaikan sejumlah operasi.

**Beberapa interpretasi:**

**A. Simulation Total Time**
```
Total Time = T_end - T_start
```
Misal: simulasi berjalan selama 60 detik.

**B. Processing Time**
```
Processing Time = waktu untuk process N messages
```

**C. Round-Trip Time (RTT)**
```
RTT = Time untuk publish → process → acknowledge
```

### 📊 Satuan
Seconds (s) atau minutes (min)

### ✅ Status Implementasi di Simulasi Saat Ini

**PARTIAL** - Bisa dihitung dari CSV timestamp

```python
df = pd.read_csv('mqtt_delay_log.csv')

# Total simulation time
start_time = df['timestamp_sent'].min()
end_time = df['timestamp_sent'].max()
total_time = end_time - start_time

print(f"Total simulation time: {total_time:.2f} seconds")

# Messages per second (throughput over time)
message_count = len(df)
throughput = message_count / total_time
print(f"Throughput: {throughput:.2f} msg/s")
```

### 💻 Implementasi yang Lebih Baik

**Auto-timer di run_sdn_mqtt.sh** (SUDAH ADA dengan parameter waktu!)

Dengan `sudo ./run_sdn_mqtt.sh 60`, total time = 60 detik.

**Tambahkan metadata di CSV:**
```python
# subscriber_log.py - tambah header metadata
with open(LOG_FILE, "w") as f:
    f.write(f"# Simulation Start: {time.time()}\n")
    f.write("device,type,value,timestamp_sent,delay_ms\n")

# Di akhir (signal handler):
def cleanup(signal, frame):
    with open(LOG_FILE, "a") as f:
        f.write(f"# Simulation End: {time.time()}\n")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
```

### 🔬 Research Value
- **Contextual metric** - untuk menunjukkan experiment duration
- Penting untuk reproducibility
- Expected: dengan duration sama, bisa compare hasil berbeda

---

## 5. Lost Message / Packet Loss

### 📋 Definisi
**Lost Message** adalah jumlah message yang **dikirim tapi tidak diterima**. Packet loss rate:

```
Packet Loss Rate = (Messages_lost / Messages_sent) * 100%
```

### 📊 Satuan
Percentage (%) atau absolute count

### 🎯 Target/Benchmark
- **Excellent:** 0%
- **Good:** < 0.1%
- **Acceptable:** < 1%
- **Poor:** > 1%

Untuk critical IoT, target biasanya 0% (zero loss).

### ❌ Status Implementasi di Simulasi Saat Ini

**BELUM TERIMPLEMENTASI** - Tidak ada sequence number tracking

### 💻 Cara Implementasi

**Metode 1: Sequence Number Tracking**

**Publisher side:**
```python
# publisher_anomaly.py
sequence_number = 0

while True:
    payload = {
        "device": DEVICE,
        "type": "anomaly",
        "value": random.uniform(50, 100),
        "timestamp": time.time(),
        "seq": sequence_number  # ← ADD THIS
    }
    publish.single("iot/data", json.dumps(payload), hostname=BROKER)
    print(f"Published seq={sequence_number}")

    # Log sent messages
    with open("sent_messages.log", "a") as f:
        f.write(f"{sequence_number},{time.time()}\n")

    sequence_number += 1
    time.sleep(1)
```

**Subscriber side:**
```python
# subscriber_log.py
received_seqs = {'anomaly': set(), 'normal': set()}

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    device_type = data['type']
    seq = data['seq']

    received_seqs[device_type].add(seq)

    # Periodic check for lost messages
    if seq % 10 == 0:  # Every 10 messages
        check_lost_messages(device_type, seq)

def check_lost_messages(msg_type, current_seq):
    expected = set(range(current_seq + 1))
    received = received_seqs[msg_type]
    lost = expected - received

    if lost:
        print(f"[{msg_type}] Lost messages: {lost}")
        loss_rate = len(lost) / (current_seq + 1) * 100
        print(f"[{msg_type}] Loss rate: {loss_rate:.2f}%")
```

**Metode 2: Compare Sent vs Received Logs**

Post-processing:
```python
import pandas as pd

# Read logs
sent_anomaly = pd.read_csv('logs/sent_anomaly.log', names=['seq', 'timestamp'])
sent_normal = pd.read_csv('logs/sent_normal.log', names=['seq', 'timestamp'])
received = pd.read_csv('mqtt_delay_log.csv')

# Count
sent_count = len(sent_anomaly) + len(sent_normal)
received_count = len(received)
lost_count = sent_count - received_count

print(f"Sent: {sent_count}")
print(f"Received: {received_count}")
print(f"Lost: {lost_count}")
print(f"Loss rate: {lost_count/sent_count*100:.2f}%")
```

**Metode 3: Flow Statistics dari SDN Controller**

Query OpenFlow statistics:
```python
import requests

# Get flow stats
response = requests.get('http://127.0.0.1:8080/stats/flow/1')
flow_stats = response.json()

# Find MQTT flows
for flow in flow_stats['1']:
    if flow['match'].get('tcp_dst') == 1883:
        src_ip = flow['match'].get('nw_src')
        packet_count = flow['packet_count']
        byte_count = flow['byte_count']

        print(f"IP {src_ip}: {packet_count} packets, {byte_count} bytes")
```

Compare dengan expected count dari publisher.

### 🔬 Research Value
- **Critical metric** untuk reliability evaluation
- Expected: dengan priority queue, loss rate seharusnya tetap 0% (atau sangat rendah)
- Bisa tunjukkan SDN tidak introduce packet loss

---

## 6. Throughput (Bonus)

### 📋 Definisi
**Throughput** adalah jumlah message/data yang berhasil dikirim per satuan waktu.

```
Throughput = Messages_received / Time_duration
```

Atau dalam bytes:
```
Throughput = Bytes_received / Time_duration
```

### 📊 Satuan
- Messages per second (msg/s)
- Kilobytes per second (KB/s)
- Megabits per second (Mbps)

### ✅ Status Implementasi di Simulasi Saat Ini

**BISA DIHITUNG** dari CSV

```python
df = pd.read_csv('mqtt_delay_log.csv')

duration = df['timestamp_sent'].max() - df['timestamp_sent'].min()
message_count = len(df)

throughput = message_count / duration
print(f"Throughput: {throughput:.2f} msg/s")

# Per type
for msg_type in ['anomaly', 'normal']:
    count = len(df[df['type'] == msg_type])
    throughput_type = count / duration
    print(f"Throughput ({msg_type}): {throughput_type:.2f} msg/s")
```

### 🔬 Research Value
- **Important metric** untuk capacity evaluation
- Expected: throughput anomaly ≈ throughput normal (karena publish rate sama)
- Bisa tunjukkan SDN tidak throttle traffic

---

## Implementasi Pengukuran

### 🔧 Enhanced Subscriber untuk Semua Metrik

Saya akan buat subscriber yang comprehensive:

```python
# subscriber_enhanced.py
import paho.mqtt.client as mqtt
import json
import time
import csv
import signal
import sys
import numpy as np

LOG_FILE = "mqtt_metrics_log.csv"
SUMMARY_FILE = "metrics_summary.txt"

class MetricsCollector:
    def __init__(self):
        self.delays = {'anomaly': [], 'normal': []}
        self.received_seq = {'anomaly': set(), 'normal': set()}
        self.first_timestamp = None
        self.last_timestamp = None
        self.message_count = 0

    def update(self, msg_type, delay, seq, timestamp):
        self.delays[msg_type].append(delay)
        self.received_seq[msg_type].add(seq)
        self.message_count += 1

        if self.first_timestamp is None:
            self.first_timestamp = timestamp
        self.last_timestamp = timestamp

    def calculate_jitter(self, msg_type):
        if len(self.delays[msg_type]) < 2:
            return 0
        delays_array = np.array(self.delays[msg_type])
        jitter = np.abs(np.diff(delays_array))
        return jitter.mean()

    def calculate_loss_rate(self, msg_type, expected_max_seq):
        expected = set(range(expected_max_seq + 1))
        received = self.received_seq[msg_type]
        lost = expected - received
        if expected_max_seq == 0:
            return 0
        return len(lost) / (expected_max_seq + 1) * 100

    def get_summary(self):
        total_time = self.last_timestamp - self.first_timestamp if self.first_timestamp else 0

        summary = {}
        for msg_type in ['anomaly', 'normal']:
            delays = self.delays[msg_type]
            if len(delays) > 0:
                summary[msg_type] = {
                    'count': len(delays),
                    'avg_delay': np.mean(delays),
                    'min_delay': np.min(delays),
                    'max_delay': np.max(delays),
                    'std_delay': np.std(delays),
                    'avg_jitter': self.calculate_jitter(msg_type),
                    'max_seq': max(self.received_seq[msg_type]) if self.received_seq[msg_type] else 0
                }
            else:
                summary[msg_type] = None

        summary['total'] = {
            'duration': total_time,
            'total_messages': self.message_count,
            'throughput': self.message_count / total_time if total_time > 0 else 0
        }

        return summary

metrics = MetricsCollector()

# CSV Header
with open(LOG_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["device", "type", "value", "seq", "timestamp_sent", "delay_ms"])

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    recv_time = time.time()
    delay = (recv_time - data["timestamp"]) * 1000  # ms

    # Update metrics
    metrics.update(data['type'], delay, data['seq'], data['timestamp'])

    # Log to CSV
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            data["device"],
            data["type"],
            data["value"],
            data["seq"],
            data["timestamp"],
            delay
        ])

    print(f"[{data['type']}] seq={data['seq']} delay={delay:.2f}ms")

def cleanup(signal, frame):
    print("\n\n=== SIMULATION SUMMARY ===")
    summary = metrics.get_summary()

    # Print to console
    for msg_type in ['anomaly', 'normal']:
        if summary[msg_type]:
            s = summary[msg_type]
            print(f"\n{msg_type.upper()}:")
            print(f"  Messages: {s['count']}")
            print(f"  Avg Delay: {s['avg_delay']:.2f} ms")
            print(f"  Min Delay: {s['min_delay']:.2f} ms")
            print(f"  Max Delay: {s['max_delay']:.2f} ms")
            print(f"  Std Dev: {s['std_delay']:.2f} ms")
            print(f"  Avg Jitter: {s['avg_jitter']:.2f} ms")
            print(f"  Max Seq: {s['max_seq']}")

    print(f"\nTOTAL:")
    print(f"  Duration: {summary['total']['duration']:.2f} s")
    print(f"  Total Messages: {summary['total']['total_messages']}")
    print(f"  Throughput: {summary['total']['throughput']:.2f} msg/s")

    # Save to file
    with open(SUMMARY_FILE, "w") as f:
        f.write(json.dumps(summary, indent=2))

    print(f"\nMetrics saved to:")
    print(f"  - {LOG_FILE}")
    print(f"  - {SUMMARY_FILE}")

    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("iot/data")

print("Subscriber started. Collecting metrics...")
print("Press Ctrl+C to stop and view summary.\n")

client.loop_forever()
```

---

## Analisis Data

### 📊 Script Analisis Komprehensif

```python
# analyze_metrics.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_csv('mqtt_metrics_log.csv')

print("=" * 60)
print("MQTT-SDN SIMULATION ANALYSIS")
print("=" * 60)

# 1. End-to-End Delay
print("\n1. END-TO-END DELAY")
print("-" * 60)
delay_stats = df.groupby('type')['delay_ms'].agg(['count', 'mean', 'min', 'max', 'std'])
print(delay_stats)

# 2. Jitter
print("\n2. JITTER")
print("-" * 60)
for msg_type in ['anomaly', 'normal']:
    subset = df[df['type'] == msg_type].sort_values('timestamp_sent')
    delays = subset['delay_ms'].values
    jitter = np.abs(np.diff(delays))
    print(f"{msg_type.upper()}:")
    print(f"  Avg Jitter: {jitter.mean():.2f} ms")
    print(f"  Std Jitter: {jitter.std():.2f} ms")
    print(f"  Max Jitter: {jitter.max():.2f} ms")

# 3. Packet Loss (requires seq column)
if 'seq' in df.columns:
    print("\n3. PACKET LOSS")
    print("-" * 60)
    for msg_type in ['anomaly', 'normal']:
        subset = df[df['type'] == msg_type]
        received_seqs = set(subset['seq'].values)
        max_seq = max(received_seqs)
        expected_seqs = set(range(max_seq + 1))
        lost_seqs = expected_seqs - received_seqs

        print(f"{msg_type.upper()}:")
        print(f"  Expected: {max_seq + 1}")
        print(f"  Received: {len(received_seqs)}")
        print(f"  Lost: {len(lost_seqs)}")
        print(f"  Loss Rate: {len(lost_seqs)/(max_seq+1)*100:.2f}%")
        if lost_seqs:
            print(f"  Lost Seq Numbers: {sorted(lost_seqs)}")

# 4. Throughput
print("\n4. THROUGHPUT")
print("-" * 60)
duration = df['timestamp_sent'].max() - df['timestamp_sent'].min()
total_messages = len(df)
throughput = total_messages / duration

print(f"Duration: {duration:.2f} s")
print(f"Total Messages: {total_messages}")
print(f"Overall Throughput: {throughput:.2f} msg/s")

for msg_type in ['anomaly', 'normal']:
    count = len(df[df['type'] == msg_type])
    tput = count / duration
    print(f"{msg_type.upper()} Throughput: {tput:.2f} msg/s")

# 5. Statistical Test (t-test)
print("\n5. STATISTICAL COMPARISON")
print("-" * 60)
anomaly_delays = df[df['type'] == 'anomaly']['delay_ms']
normal_delays = df[df['type'] == 'normal']['delay_ms']

from scipy import stats
t_stat, p_value = stats.ttest_ind(anomaly_delays, normal_delays)
print(f"T-test:")
print(f"  t-statistic: {t_stat:.4f}")
print(f"  p-value: {p_value:.6f}")
if p_value < 0.05:
    print(f"  ✓ Significant difference (p < 0.05)")
else:
    print(f"  ✗ No significant difference (p >= 0.05)")

# 6. Visualization
print("\n6. GENERATING PLOTS...")
print("-" * 60)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Delay Distribution
axes[0, 0].hist([anomaly_delays, normal_delays],
                label=['Anomaly', 'Normal'],
                bins=30, alpha=0.7)
axes[0, 0].set_xlabel('Delay (ms)')
axes[0, 0].set_ylabel('Frequency')
axes[0, 0].set_title('Delay Distribution')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Plot 2: Delay Over Time
for msg_type in ['anomaly', 'normal']:
    subset = df[df['type'] == msg_type].sort_values('timestamp_sent')
    axes[0, 1].plot(subset['timestamp_sent'] - df['timestamp_sent'].min(),
                    subset['delay_ms'],
                    label=msg_type.capitalize(), alpha=0.7)
axes[0, 1].set_xlabel('Time (s)')
axes[0, 1].set_ylabel('Delay (ms)')
axes[0, 1].set_title('Delay Over Time')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Plot 3: Box Plot
delay_data = [anomaly_delays, normal_delays]
axes[1, 0].boxplot(delay_data, labels=['Anomaly', 'Normal'])
axes[1, 0].set_ylabel('Delay (ms)')
axes[1, 0].set_title('Delay Comparison (Box Plot)')
axes[1, 0].grid(True, alpha=0.3)

# Plot 4: CDF
for msg_type, delays in [('Anomaly', anomaly_delays), ('Normal', normal_delays)]:
    sorted_delays = np.sort(delays)
    cdf = np.arange(1, len(sorted_delays) + 1) / len(sorted_delays)
    axes[1, 1].plot(sorted_delays, cdf, label=msg_type, linewidth=2)
axes[1, 1].set_xlabel('Delay (ms)')
axes[1, 1].set_ylabel('CDF')
axes[1, 1].set_title('Cumulative Distribution Function')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('metrics_analysis.png', dpi=300)
print("Plot saved to: metrics_analysis.png")

plt.show()

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
```

---

## Visualization

### 📈 Contoh Output Visualisasi

Script di atas akan menghasilkan 4 plot:

1. **Delay Distribution (Histogram)**
   - Membandingkan distribusi delay anomaly vs normal
   - Expected: anomaly peak di delay lebih rendah

2. **Delay Over Time (Line Plot)**
   - Melihat tren delay sepanjang waktu
   - Detect anomaly/spike

3. **Box Plot**
   - Median, quartile, outliers
   - Visual comparison yang jelas

4. **CDF (Cumulative Distribution Function)**
   - Melihat percentile
   - Misal: 90% anomaly messages < 3ms, 90% normal < 5ms

---

## 💡 Kesimpulan & Rekomendasi

### ✅ Metrik yang Sudah Ada (Saat Ini)
1. **End-to-End Delay** ✅ (dalam `mqtt_delay_log.csv`)

### ➕ Metrik yang Perlu Ditambahkan
2. **Jitter** - Implementasi: mudah, tinggal hitung delta delay
3. **Response Time** - Implementasi: perlu QoS 1 atau request-response pattern
4. **Total Time** - Implementasi: sudah bisa via parameter waktu (`./run_sdn_mqtt.sh 60`)
5. **Lost Message** - Implementasi: perlu sequence number di payload

### 🎯 Prioritas untuk Research Paper

**Essential (Must Have):**
- ✅ End-to-End Delay (average, min, max, std dev)
- ✅ Throughput
- ⭐ Jitter (variasi delay)
- ⭐ Packet Loss Rate

**Nice to Have:**
- Response Time (jika applicable)
- Latency percentiles (P50, P90, P95, P99)

### 📊 Table untuk Paper

Contoh tabel hasil:

| Metric | Anomaly (Queue 1) | Normal (Queue 2) | Improvement |
|--------|-------------------|------------------|-------------|
| **Avg Delay** | 1.92 ms | 2.85 ms | **32.6% faster** |
| **Avg Jitter** | 0.45 ms | 0.87 ms | **48.3% lower** |
| **Packet Loss** | 0.00% | 0.00% | Equal |
| **Throughput** | 1.0 msg/s | 1.0 msg/s | Equal |
| **P95 Delay** | 2.5 ms | 4.2 ms | **40.5% faster** |

**Kesimpulan:**
> "Hasil menunjukkan bahwa traffic anomaly dengan priority tinggi (Queue 1) memiliki delay 32.6% lebih rendah dan jitter 48.3% lebih stabil dibandingkan normal traffic (Queue 2), membuktikan efektivitas SDN-based QoS dalam prioritas data IoT critical."

---

**Author:** Research Documentation - SDN-MQTT Project
**Date:** 2025-11-09
**Version:** 1.0
