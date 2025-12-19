import json
import time
import logging
from kafka import KafkaConsumer
from django.conf import settings
from .services import BiometricService

logger = logging.getLogger(__name__)

def run_consumer():
    """
    Main blocking loop for the Kafka Consumer.
    """
    print("Initializing Kafka Consumer...")
    consumer = None

    # Retry logic to wait for Kafka to be ready
    while not consumer:
        try:
            consumer = KafkaConsumer(
                settings.KAFKA_ATTENDANCE_TOPIC,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                group_id='attendance_workers',
                auto_offset_reset='earliest'
            )
            print("Successfully connected to Kafka.")
        except Exception as e:
            print(f"Waiting for Kafka broker... ({e})")
            time.sleep(5)

    service = BiometricService()
    print(f"Listening on topic: {settings.KAFKA_ATTENDANCE_TOPIC}")

    # Initial Sync on Startup
    try:
        print(f"Attempting initial sync with {settings.ZK_DEVICE_IP}...")
        service.sync_device(settings.ZK_DEVICE_IP)
        print("Initial startup sync completed successfully.")
    except Exception as e:
        print(f"Initial startup sync failed: {e}")

    try:
        for message in consumer:
            data = message.value
            print(f"Received message: {data}")
            
            if data.get('action') == 'sync_attendance':
                ip = data.get('device_ip')
                if ip:
                    print(f"Starting sync for device {ip}...")
                    try:
                        # 1. Sync
                        service.sync_device(ip)
                        
                        # 2. optional: Process Summaries
                        # service.process_daily_summaries() 
                        
                        print(f"Sync for {ip} Finished.")
                    except Exception as e:
                        print(f"Error executing sync for {ip}: {e}")
                else:
                    print(f"Invalid message format: {data}")
    except KeyboardInterrupt:
        print("Consumer stopping...")
    finally:
        if consumer:
            consumer.close()
