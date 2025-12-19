@echo off
REM Run Consumer Locally (Windows Development)

echo ========================================
echo Running SPTI Consumer Locally
echo ========================================
echo.

REM Set environment variables for local development
set DB_ENGINE=django.db.backends.postgresql
set POSTGRES_DB=spti_db
set POSTGRES_USER=postgres
set POSTGRES_PASSWORD=password
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set KAFKA_BOOTSTRAP_SERVERS=localhost:9092
set DJANGO_DEBUG=True
set PYTHONUNBUFFERED=1

echo Environment configured:
echo   Database: localhost:5432/spti_db
echo   Kafka: localhost:9092
echo.

echo Starting consumer...
echo Press Ctrl+C to stop
echo.

python manage.py run_kafka_consumer
