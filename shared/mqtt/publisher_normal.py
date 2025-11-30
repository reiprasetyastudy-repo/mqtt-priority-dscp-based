import paho.mqtt.publish as publish
import time, json, random
import os

BROKER = os.getenv("BROKER_IP", "10.0.0.3")  # Default to 10.0.0.3 for backward compatibility
DEVICE = os.getenv("DEVICE", "sensor_normal")
MSG_RATE = float(os.getenv("MSG_RATE", "50"))  # Messages per second (default: 1 msg/s)

# Sequence number untuk tracking lost messages
sequence_number = 0

while True:
    payload = {
        "device": DEVICE,
        "type": "normal",
        "value": random.uniform(20, 30),
        "timestamp": time.time(),
        "seq": sequence_number  # Tambah sequence number
    }
    publish.single("iot/data", json.dumps(payload), hostname=BROKER)
    print(f"Published (normal) seq={sequence_number}: value={payload['value']:.2f}")

    sequence_number += 1
    time.sleep(1.0 / MSG_RATE)  # Sleep based on desired message rate
