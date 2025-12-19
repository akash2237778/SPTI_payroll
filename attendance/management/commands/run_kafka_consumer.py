from django.core.management.base import BaseCommand
from attendance.consumers import run_consumer

class Command(BaseCommand):
    help = 'Runs the Kafka Consumer for Attendance Sync'

    def handle(self, *args, **options):
        run_consumer()
