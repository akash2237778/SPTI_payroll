import time
import threading
import logging
import json
from datetime import datetime
from django.conf import settings
from kafka import KafkaProducer
from .models import DeviceSettings

logger = logging.getLogger(__name__)

class AttendanceScheduler(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.stop_event = threading.Event()
        self.last_sync_time = 0

    def run(self):
        logger.info("Scheduler started.")
        # Initial sleep to let the system settle
        time.sleep(5)
        
        while not self.stop_event.is_set():
            try:
                self.check_schedule()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            # Check every minute
            # We loop faster to catch stop_event but check logic less frequently
            for _ in range(60):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def check_schedule(self):
        # Fresh settings every time
        try:
            device_settings = DeviceSettings.get_settings()
        except Exception:
            # DB might not be ready
            return

        now = datetime.now()
        current_time = now.time()
        
        # Determine interval based on current time
        interval = device_settings.sync_interval_mins # default 30
        
        # Morning Rush
        if device_settings.morning_start_time <= current_time <= device_settings.morning_end_time:
            interval = device_settings.morning_interval_mins # 5
            
        # Evening Rush
        elif device_settings.evening_start_time <= current_time <= device_settings.evening_end_time:
            interval = device_settings.evening_interval_mins # 5

        # Check if due
        # Logic: If last run was > interval ago, run.
        elapsed_mins = (time.time() - self.last_sync_time) / 60
        
        if elapsed_mins >= interval:
            logger.info(f"Scheduled Sync Triggered (Interval: {interval}m)")
            self.trigger_sync(device_settings.device_ip)
            self.last_sync_time = time.time()

    def trigger_sync(self, ip):
        try:
            producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            message = {
                "action": "sync_attendance", 
                "device_ip": ip,
                "source": "scheduler"
            }
            producer.send(settings.KAFKA_ATTENDANCE_TOPIC, message)
            producer.flush()
            producer.close()
            logger.info("Sent sync message to Kafka")
        except Exception as e:
            logger.error(f"Failed to trigger sync from scheduler: {e}")

def start_scheduler():
    scheduler = AttendanceScheduler()
    scheduler.start()
    return scheduler
