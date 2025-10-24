# Deployment Guide

This guide covers deploying the OpenGovt application in production environments.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Application Deployment](#application-deployment)
- [Monitoring and Logging](#monitoring-and-logging)
- [Scaling](#scaling)
- [Security](#security)
- [Backup and Recovery](#backup-and-recovery)

## Architecture Overview

OpenGovt consists of several components:

```
┌─────────────────┐     ┌──────────────────┐
│   Frontend      │────▶│   API Server     │
│   (Next.js)     │     │   (Python/Flask) │
└─────────────────┘     └──────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  PostgreSQL  │
                        │   Database   │
                        └──────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│   Twitter    │    │  Analysis    │      │  Congress    │
│  Ingestion   │    │  Workers     │      │  Pipeline    │
│   Service    │    │  (NLP/ML)    │      │   Service    │
└──────────────┘    └──────────────┘      └──────────────┘
```

## Prerequisites

### System Requirements

**Minimum (Development):**
- 4 CPU cores
- 8 GB RAM
- 50 GB storage
- Ubuntu 20.04+ or similar Linux distribution

**Recommended (Production):**
- 8+ CPU cores
- 16+ GB RAM
- 200+ GB SSD storage
- Ubuntu 22.04 LTS

### Software Requirements

- Docker 24.0+
- Docker Compose 2.0+
- PostgreSQL 15+ (or use Docker)
- Python 3.12+
- Node.js 20+
- Nginx (for reverse proxy)
- Certbot (for SSL certificates)

## Environment Configuration

### 1. Create Environment Files

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Configure Production Settings

Edit `.env` with your production values:

```bash
# Production Environment
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING
SECRET_KEY=$(openssl rand -base64 32)

# Database
DATABASE_URL=postgresql://opengovt_user:secure_password@db:5432/opengovt
DATABASE_HOST=db
DATABASE_PORT=5432
DATABASE_NAME=opengovt
DATABASE_USER=opengovt_user
DATABASE_PASSWORD=$(openssl rand -base64 24)

# API Keys (from your accounts)
TWITTER_BEARER_TOKEN=your_actual_bearer_token
CONGRESS_API_KEY=your_actual_api_key
OPENSTATES_API_KEY=your_actual_api_key

# API Server
API_HOST=0.0.0.0
API_PORT=8080
API_WORKERS=4

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_SITE_NAME=OpenDiscourse.net

# Monitoring
SENTRY_DSN=your_sentry_dsn_for_error_tracking
SENTRY_ENVIRONMENT=production

# Feature Flags
ENABLE_TWITTER_INGESTION=true
ENABLE_SENTIMENT_ANALYSIS=true
ENABLE_TOXICITY_DETECTION=true
ENABLE_STATEMENT_EXTRACTION=true
```

### 3. Separate Deployment and User Settings

Create `settings_deployment.py` for deployment-specific configuration:

```python
"""
Deployment Settings

This file contains settings specific to the deployment infrastructure,
separate from user-facing application settings.
"""

# Deployment Configuration
DEPLOYMENT_ENV = 'production'
CONTAINER_REGISTRY = 'ghcr.io/yourusername'
IMAGE_TAG = 'latest'

# Database Pooling
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 40
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600

# Worker Configuration
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/1'
CELERY_WORKERS = 4
CELERY_CONCURRENCY = 2

# Cache Configuration
REDIS_URL = 'redis://redis:6379/2'
CACHE_TTL = 3600
CACHE_MAX_SIZE = 1000

# Backup Configuration
BACKUP_ENABLED = True
BACKUP_SCHEDULE = '0 2 * * *'  # Daily at 2 AM
BACKUP_RETENTION_DAYS = 30
BACKUP_S3_BUCKET = 'opengovt-backups'

# Monitoring
PROMETHEUS_PORT = 9090
GRAFANA_PORT = 3001
LOG_AGGREGATION = 'elasticsearch'
LOG_RETENTION_DAYS = 90

# Resource Limits
MAX_REQUEST_SIZE = '100MB'
MAX_UPLOAD_SIZE = '50MB'
RATE_LIMIT_PER_MINUTE = 60
```

Create `settings_user.py` for user-facing settings:

```python
"""
User Settings

This file contains user-configurable application settings.
"""

# Application Settings
SITE_NAME = 'OpenDiscourse.net'
SITE_DESCRIPTION = 'Comprehensive government transparency and legislative analysis'
SUPPORT_EMAIL = 'support@opendiscourse.net'

# Feature Toggles
FEATURES = {
    'social_media_analysis': True,
    'bill_similarity': True,
    'voting_consistency': True,
    'statement_extraction': True,
    'real_time_alerts': True,
}

# Display Settings
DEFAULT_TIMEZONE = 'America/New_York'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'

# Pagination
ITEMS_PER_PAGE = 25
MAX_ITEMS_PER_PAGE = 100

# Search Configuration
SEARCH_MIN_LENGTH = 3
SEARCH_MAX_RESULTS = 100
SEARCH_HIGHLIGHT = True

# Analysis Settings
SENTIMENT_CONFIDENCE_THRESHOLD = 0.5
TOXICITY_THRESHOLD = 0.6
STATEMENT_CONFIDENCE_THRESHOLD = 0.7
```

## Database Setup

### 1. Create Database

Using Docker Compose (recommended):

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: opengovt
      POSTGRES_USER: opengovt_user
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./app/db/migrations:/docker-entrypoint-initdb.d
    ports:
      - "127.0.0.1:5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U opengovt_user"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

Or manual setup:

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE opengovt;
CREATE USER opengovt_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE opengovt TO opengovt_user;
ALTER DATABASE opengovt OWNER TO opengovt_user;
EOF
```

### 2. Run Migrations

```bash
# Run all migrations in order
psql -U opengovt_user -d opengovt -f app/db/migrations/001_init.sql
psql -U opengovt_user -d opengovt -f app/db/migrations/002_analysis_tables.sql
psql -U opengovt_user -d opengovt -f app/db/migrations/003_social_media_tables.sql
```

### 3. Verify Database

```bash
psql -U opengovt_user -d opengovt -c "\dt"
```

## Application Deployment

### Option 1: Docker Deployment (Recommended)

#### 1. Build Images

```bash
# Build API server
docker build -t opengovt-api:latest -f Dockerfile .

# Build frontend
cd frontend-v2
docker build -t opengovt-frontend:latest .
cd ..
```

#### 2. Deploy with Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    # ... (database config from above)
  
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
  
  api:
    image: opengovt-api:latest
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env
    ports:
      - "127.0.0.1:8080:8080"
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./bulk_data:/app/bulk_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  frontend:
    image: opengovt-frontend:latest
    depends_on:
      - api
    environment:
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
    ports:
      - "127.0.0.1:3000:3000"
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    depends_on:
      - api
      - frontend
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./static:/usr/share/nginx/html/static:ro
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
  
  # Background workers
  twitter-ingestion:
    image: opengovt-api:latest
    depends_on:
      - db
      - redis
    env_file:
      - .env
    command: python scripts/twitter_ingestion.py --batch-config /app/config/twitter_batch.json
    restart: unless-stopped
  
  analysis-worker:
    image: opengovt-api:latest
    depends_on:
      - db
      - redis
    env_file:
      - .env
    command: python scripts/analyze_tweets.py --analyze-all --batch-size 500
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### 3. Start Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Systemd Services

#### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv /opt/opengovt/venv
source /opt/opengovt/venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-analysis.txt

# Install Node dependencies
cd frontend-v2
npm install
npm run build
cd ..
```

#### 2. Create Systemd Service Files

API Service (`/etc/systemd/system/opengovt-api.service`):

```ini
[Unit]
Description=OpenGovt API Server
After=network.target postgresql.service

[Service]
Type=simple
User=opengovt
Group=opengovt
WorkingDirectory=/opt/opengovt
Environment="PATH=/opt/opengovt/venv/bin"
EnvironmentFile=/opt/opengovt/.env
ExecStart=/opt/opengovt/venv/bin/gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/opengovt/access.log \
    --error-logfile /var/log/opengovt/error.log \
    cbw_http:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Frontend Service (`/etc/systemd/system/opengovt-frontend.service`):

```ini
[Unit]
Description=OpenGovt Frontend
After=network.target

[Service]
Type=simple
User=opengovt
Group=opengovt
WorkingDirectory=/opt/opengovt/frontend-v2
Environment="PATH=/usr/bin:/bin"
Environment="NODE_ENV=production"
EnvironmentFile=/opt/opengovt/.env
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable opengovt-api opengovt-frontend
sudo systemctl start opengovt-api opengovt-frontend
sudo systemctl status opengovt-api opengovt-frontend
```

### Nginx Configuration

Create `/etc/nginx/sites-available/opengovt`:

```nginx
# API Server
upstream api_backend {
    server 127.0.0.1:8080;
}

# Frontend Server
upstream frontend_backend {
    server 127.0.0.1:3000;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com api.yourdomain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Main website
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend
    location / {
        proxy_pass http://frontend_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static files
    location /static/ {
        alias /opt/opengovt/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

# API Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    # SSL configuration (same as above)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;
    limit_req zone=api_limit burst=20 nodelay;
    
    # API endpoints
    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (adjust as needed)
        add_header Access-Control-Allow-Origin "https://yourdomain.com" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://api_backend/health;
        access_log off;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/opengovt /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL Certificates

Using Let's Encrypt:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificates
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Auto-renewal is configured automatically
sudo systemctl status certbot.timer
```

## Monitoring and Logging

### Prometheus Metrics

The application exposes Prometheus metrics on port 8000:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'opengovt-api'
    static_configs:
      - targets: ['api:8000']
  
  - job_name: 'opengovt-workers'
    static_configs:
      - targets: ['twitter-ingestion:8000', 'analysis-worker:8000']
```

### Grafana Dashboards

Import pre-built dashboards or create custom ones to monitor:
- Request rates and latency
- Database query performance
- Tweet ingestion rates
- Analysis completion rates
- Error rates and types

### Application Logs

Configure log rotation in `/etc/logrotate.d/opengovt`:

```
/var/log/opengovt/*.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    create 0640 opengovt opengovt
    sharedscripts
    postrotate
        systemctl reload opengovt-api
    endscript
}
```

### Centralized Logging

Use Elasticsearch/Logstash/Kibana (ELK) or similar:

```yaml
# docker-compose.prod.yml additions
  logstash:
    image: logstash:8
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch
  
  elasticsearch:
    image: elasticsearch:8
    environment:
      - discovery.type=single-node
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
  
  kibana:
    image: kibana:8
    depends_on:
      - elasticsearch
    ports:
      - "127.0.0.1:5601:5601"
```

## Scaling

### Horizontal Scaling

#### Database Replication

Set up PostgreSQL streaming replication:

```yaml
# docker-compose.prod.yml
  db-primary:
    # ... primary database config
  
  db-replica-1:
    image: postgres:15-alpine
    environment:
      POSTGRES_PRIMARY_HOST: db-primary
      POSTGRES_REPLICATION_MODE: slave
    # ... replication config
```

#### API Server Scaling

Add more API server instances:

```yaml
  api-1:
    # ... api config
  
  api-2:
    # ... same api config
  
  api-3:
    # ... same api config
  
  api-load-balancer:
    image: nginx:alpine
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
```

### Vertical Scaling

Adjust resource limits in docker-compose:

```yaml
services:
  api:
    # ...
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
```

### Worker Scaling

Add more analysis workers for better throughput:

```yaml
  analysis-worker-1:
    # ... worker config
  analysis-worker-2:
    # ... worker config
  analysis-worker-3:
    # ... worker config
```

## Security

### Network Security

- Use firewall (ufw/iptables) to limit external access
- Only expose necessary ports (80, 443)
- Use VPN for administrative access
- Enable fail2ban for brute force protection

### Application Security

- Keep dependencies updated
- Use environment variables for secrets
- Enable HTTPS only
- Implement rate limiting
- Validate all inputs
- Use prepared statements (prevent SQL injection)
- Enable CSRF protection
- Set secure cookie flags

### Database Security

- Use strong passwords
- Limit network access
- Enable SSL connections
- Regular security updates
- Principle of least privilege for users

## Backup and Recovery

### Database Backups

Automated backup script:

```bash
#!/bin/bash
# /opt/opengovt/scripts/backup.sh

BACKUP_DIR=/backup/opengovt
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=opengovt

# Create backup
pg_dump -U opengovt_user $DB_NAME | gzip > $BACKUP_DIR/opengovt_$DATE.sql.gz

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/opengovt_$DATE.sql.gz s3://opengovt-backups/

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

Schedule with cron:

```bash
0 2 * * * /opt/opengovt/scripts/backup.sh
```

### Restore Procedure

```bash
# Stop services
sudo systemctl stop opengovt-api opengovt-frontend

# Restore database
gunzip < backup_file.sql.gz | psql -U opengovt_user opengovt

# Start services
sudo systemctl start opengovt-api opengovt-frontend
```

### Disaster Recovery Plan

1. Regular backups (daily minimum)
2. Off-site backup storage
3. Documented restore procedure
4. Tested recovery process
5. Monitoring and alerting
6. Incident response plan

## Maintenance

### Regular Tasks

- **Daily**: Monitor logs and metrics
- **Weekly**: Review security alerts, update dependencies
- **Monthly**: Database optimization, backup verification
- **Quarterly**: Security audit, disaster recovery test

### Update Procedure

```bash
# 1. Backup
/opt/opengovt/scripts/backup.sh

# 2. Pull latest code
cd /opt/opengovt
git pull

# 3. Update dependencies
source venv/bin/activate
pip install -r requirements.txt -U

# 4. Run migrations (if any)
psql -U opengovt_user -d opengovt -f app/db/migrations/new_migration.sql

# 5. Restart services
sudo systemctl restart opengovt-api opengovt-frontend

# 6. Verify
curl -f http://localhost:8080/health || echo "API health check failed"
```

## Troubleshooting

See detailed troubleshooting in `docs/TROUBLESHOOTING.md`.

Quick diagnostics:

```bash
# Check service status
sudo systemctl status opengovt-api opengovt-frontend

# View recent logs
sudo journalctl -u opengovt-api -n 100 --no-pager

# Check database connectivity
psql -U opengovt_user -d opengovt -c "SELECT version();"

# Test API endpoint
curl -v http://localhost:8080/health

# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
ps aux | grep opengovt
```

## Support

For deployment issues:
- Check logs in `/var/log/opengovt/`
- Review system metrics
- Consult documentation
- Open GitHub issue
