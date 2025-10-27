# Logging Architecture

This document outlines the logging strategy for the Agno Simple Knowledge system, from local development to cloud-scale deployment.

## Current State

The system currently uses Python's basic `logging` module configured in `python-backend/main.py`. Logs are:
- Output to console
- Not persisted to files
- Not easily queryable
- Lost when the process restarts

## Phase 1: Local Development (Recommended: Self-Hosted Grafana + Loki)

### Architecture

```
Python Backend (structlog)
       ↓
   JSON Logs
       ↓
  Loki (log storage)
       ↓
  Grafana (UI)
  http://localhost:3000
```

### Option A: Self-Hosted (Docker) - RECOMMENDED

**Pros:**
- Completely free
- Full control and privacy
- Local development
- Easy to scale to cloud later
- No external dependencies

**Cons:**
- Requires Docker
- Only accessible locally

**Setup:**

1. **Create `docker-compose.yml` in project root:**

```yaml
version: '3.8'

services:
  loki:
    image: grafana/loki:latest
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - logging

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - logging
    depends_on:
      - loki

volumes:
  loki-data:
  grafana-data:

networks:
  logging:
    driver: bridge
```

2. **Create `loki-config.yml` in project root:**

```yaml
auth_enabled: false

ingester:
  chunk_idle_period: 3m
  chunk_retain_period: 1m
  max_chunk_age: 1h
  chunk_encoding: png

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema:
        version: v11
        index:
          prefix: index_
          period: 24h

server:
  http_listen_port: 3100
  log_level: info

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

3. **Start services:**

```bash
docker-compose up -d
```

4. **Access Grafana:**
- URL: `http://localhost:3000`
- Username: `admin`
- Password: `admin`

5. **Configure Loki as data source in Grafana:**
- Settings → Data Sources → Add data source
- Select Loki
- URL: `http://loki:3100`
- Save

### Option B: Grafana Cloud Free Tier

**Pros:**
- Cloud-hosted (accessible from anywhere)
- 50GB free logs/month
- Managed service (no maintenance)
- Cloud-ready from the start

**Cons:**
- Requires account signup
- Limited to 50GB/month
- Less control

**Setup:**

1. Sign up at https://grafana.com/auth/sign-up
2. Create stack in Grafana Cloud
3. Get Loki endpoint and API token
4. Configure Python backend to send logs to cloud endpoint (see Phase 2)

---

## Phase 2: Cloud Deployment (Multiple Desktop Apps)

### Architecture

When you're ready to distribute your app to multiple users:

```
Desktop App 1 (User A)  ─┐
Desktop App 2 (User B)  ─┤─> Cloud Loki + Grafana
Desktop App 3 (User C)  ─┘
```

Each desktop app sends logs to a cloud Loki instance where you can aggregate, search, and monitor logs across all users.

### Configuration

**Python Backend Setup:**

1. **Add dependencies to `requirements.txt`:**

```
structlog>=24.1.0
python-logging-loki>=0.3.1
```

2. **Configure logging in `python-backend/main.py`:**

```python
import structlog
import logging_loki
from pythonjsonlogger import jsonlogger

# For local development (self-hosted Loki)
LOKI_URL = "http://localhost:3100/loki/api/v1/push"  # or cloud URL

# Configure structlog for JSON output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configure handler to send logs to Loki
loki_handler = logging_loki.LokiHandler(
    url=LOKI_URL,
    tags={
        "app": "agno-knowledge",
        "environment": "development",  # or "production"
        "version": "1.0.0",
        # For cloud deployment, add user ID:
        # "user_id": "<unique-user-id>",
    },
    version="1",
)

# Add handler to root logger
logging.getLogger().addHandler(loki_handler)
```

### Security Considerations

**For Cloud Deployment:**

1. **API Token Management:**
   - Store Loki API token securely (not in git)
   - Use environment variables: `LOKI_API_TOKEN`
   - Rotate tokens regularly
   - Use read-only tokens where possible

2. **HTTPS/TLS:**
   - Always use HTTPS for cloud endpoints
   - Verify SSL certificates
   - Never log sensitive data (passwords, API keys, tokens)

3. **Privacy Compliance:**
   - Don't log personally identifiable information (PII)
   - Anonymize user IDs if needed
   - Comply with GDPR, CCPA, and other privacy laws
   - Obtain user consent for telemetry logging
   - Clear privacy policy about what data is collected

4. **Rate Limiting:**
   - Batch logs before sending to avoid overwhelming Loki
   - Implement exponential backoff for retries
   - Set maximum log queue size

### Example: Cloud Deployment

When deploying to production with multiple users:

```python
import os

LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100/loki/api/v1/push")
LOKI_TOKEN = os.getenv("LOKI_API_TOKEN", "")  # For cloud
MACHINE_ID = get_unique_machine_id()  # Generate once per install
USER_ID = os.getenv("USER_ID", "anonymous")  # From app auth

loki_handler = logging_loki.LokiHandler(
    url=LOKI_URL,
    auth=("username", LOKI_TOKEN) if LOKI_TOKEN else None,
    tags={
        "app": "agno-knowledge",
        "version": APP_VERSION,
        "user_id": USER_ID,
        "machine_id": MACHINE_ID,
        "os": platform.system(),
    },
    version="1",
)
```

### Querying Logs

**LogQL Query Examples:**

```logql
# View all logs
{app="agno-knowledge"}

# Errors only
{app="agno-knowledge"} |= "error"

# Logs from specific user
{app="agno-knowledge", user_id="user-123"}

# Logs from last hour
{app="agno-knowledge"} | json | timestamp > "2024-01-01T00:00:00Z"

# Count errors by user
sum(count_over_time({app="agno-knowledge"} |= "error" [5m])) by (user_id)

# Performance: API response time
{app="agno-knowledge"} | json | duration > 1000
```

---

## Cost Estimates

### Self-Hosted (Docker)
- **Cost**: FREE
- **Storage**: Limited by disk space (~100GB on standard machine)
- **Best for**: Development and small deployments

### Grafana Cloud
- **Free Tier**: 50GB logs/month
- **Pro**: $19/month + $0.50/GB over 50GB
- **Enterprise**: Contact sales
- **Best for**: Scaling with multiple users

### Example Scenarios

**Scenario 1: 10 users, 1MB logs/day each**
- Total: 300MB/month
- Grafana Cloud Cost: FREE (under 50GB)

**Scenario 2: 100 users, 10MB logs/day each**
- Total: 30GB/month
- Grafana Cloud Cost: FREE (under 50GB)

**Scenario 3: 1000 users, 100MB logs/day each**
- Total: 3TB/month
- Grafana Cloud Cost: $0.50 × (3000 - 50) = $1,475/month
- Self-hosted: ~$50/month (compute + storage)

---

## Implementation Checklist

### Phase 1: Local Development
- [ ] Add structlog to `requirements.txt`
- [ ] Create `docker-compose.yml`
- [ ] Create `loki-config.yml`
- [ ] Update `python-backend/main.py` to use structlog
- [ ] Test logging locally: `docker-compose up -d`
- [ ] Verify logs appear in Grafana UI

### Phase 2: Cloud Deployment
- [ ] Sign up for Grafana Cloud (or prepare self-hosted)
- [ ] Get Loki endpoint and API token
- [ ] Update Python backend with cloud endpoint
- [ ] Add environment variable configuration
- [ ] Implement user ID tagging
- [ ] Add privacy notices to app
- [ ] Test cloud logging with test user
- [ ] Set up alerts in Grafana for errors

---

## References

- [Grafana Loki Documentation](https://grafana.com/docs/loki/)
- [Grafana Cloud Pricing](https://grafana.com/pricing/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/logql/)
- [Python JSON Logger](https://github.com/mdomke/python-json-logger)
- [Structlog Documentation](https://www.structlog.org/)

---

## Notes

- Logs are NOT encrypted at rest in self-hosted setup (add encryption for sensitive data)
- Consider log retention policies to manage storage
- Set up Grafana alerts for critical errors
- Monitor Loki performance if logs exceed 100GB
