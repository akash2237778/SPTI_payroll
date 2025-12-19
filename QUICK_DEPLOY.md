# 🚀 Quick Deployment - TrueNAS SCALE

## Copy This to Dockge

```yaml
services:
  db:
    image: postgres:15
    container_name: spti_db
    environment:
      POSTGRES_DB: spti_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: spti_zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    restart: unless-stopped
    
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: spti_kafka
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper
    healthcheck:
      test: ["CMD-SHELL", "kafka-topics --bootstrap-server localhost:9092 --list"]
      interval: 10s
      timeout: 10s
      retries: 5
    restart: unless-stopped
    
  backend:
    image: akash7778/sptipayroll-backend:latest
    container_name: spti_backend
    command: bash -c "python manage.py migrate && gunicorn --bind 0.0.0.0:8000 --reload spti_payroll.wsgi:application"
    ports:
      - "8001:8000"
    environment:
      DB_ENGINE: django.db.backends.postgresql
      POSTGRES_DB: spti_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_HOST: db
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      DJANGO_DEBUG: "True"
      ALLOWED_HOSTS: "*"
      PYTHONUNBUFFERED: "1"
    depends_on:
      db:
        condition: service_healthy
      kafka:
        condition: service_healthy
    restart: unless-stopped
    
  consumer:
    image: akash7778/sptipayroll-consumer:latest
    container_name: spti_consumer
    command: python manage.py run_kafka_consumer
    network_mode: "host"
    environment:
      DB_ENGINE: django.db.backends.postgresql
      POSTGRES_DB: spti_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_HOST: localhost
      KAFKA_BOOTSTRAP_SERVERS: localhost:9092
      PYTHONUNBUFFERED: "1"
    restart: unless-stopped

volumes:
  postgres_data:
```

## ⚠️ IMPORTANT

1. **DO NOT add volume mounts** for `/app` - code is in the images
2. **Consumer uses `network_mode: host`** to access biometric device
3. **Consumer environment** uses `localhost` for DB and Kafka
4. **Backend environment** uses `db` and `kafka` service names

## 🎯 After Deployment

1. Access: `http://<truenas-ip>:8001`
2. Create admin: `docker exec -it spti_backend python manage.py createsuperuser`
3. Check logs: `docker logs spti_consumer`

## ✅ Expected Status

```
spti_db         Up (healthy)
spti_zookeeper  Up
spti_kafka      Up (healthy)
spti_backend    Up
spti_consumer   Up
```

## 🐛 If Errors

- **"No such file /app/manage.py"** → Remove volume mounts
- **"Connection refused"** → Check `POSTGRES_HOST` matches network mode
- **"Can't reach device"** → Ensure `network_mode: host` on consumer

---

See `TRUENAS_DEPLOY.md` for full documentation.
