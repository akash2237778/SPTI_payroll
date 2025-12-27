from django.core.management.base import BaseCommand
from attendance.consumers import run_consumer
from attendance.scheduler import start_scheduler

class Command(BaseCommand):
    help = 'Runs the Kafka Consumer for Attendance Sync'

    def handle(self, *args, **options):
        # Start the scheduler in a background thread
        start_scheduler()
        
        # Run the consumer (blocking)
        run_consumer()
