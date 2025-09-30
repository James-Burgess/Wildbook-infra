# Getting Started

Complete guide to setting up and running Wildbook Infrastructure for the first time.

## Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Git**: For cloning repositories
- **8GB RAM minimum** (16GB recommended)
- **20GB free disk space** (for images and data)

### Verify Prerequisites

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Verify Docker is running
docker ps
```

## Installation

### 1. Clone the Repository

```bash
# Clone with submodules
git clone --recursive https://github.com/WildMeOrg/wildbook-infra.git
cd wildbook-infra
```

If you already cloned without `--recursive`:

```bash
git submodule update --init --recursive
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (optional for quick start)
nano .env  # or use your preferred editor
```

**Default configuration is fine for local development.**

### 3. Start Services

```bash
# Start all services in background
docker-compose up -d

# This will:
# - Pull necessary Docker images
# - Build WBIA and Wildbook images
# - Initialize databases
# - Start all services

# First start takes 10-15 minutes (building images)
```

### 4. Monitor Startup

```bash
# Check service status
docker-compose ps

# Watch logs
docker-compose logs -f

# Wait for services to be healthy
# Look for "healthy" status in docker-compose ps output
```

### 5. Verify Installation

```bash
# Check all services are running
docker-compose ps

# Should show:
# - wildbook-postgres (healthy)
# - wildbook-wbia (running)
# - wildbook-app (running)
# - wildbook-opensearch (healthy)
# - wildbook-autoheal (running)
```

## Accessing the Applications

### Wildbook Web Interface

Open http://localhost:8080 in your browser.

**First time setup:**
1. Create admin account (if prompted)
2. Configure site settings
3. Upload test images

### WBIA API

Test the API endpoint:

```bash
# Health check
curl http://localhost:5000/api/core/db/info/

# Should return JSON with database info
```

### PostgreSQL Database

Connect using any PostgreSQL client:

```bash
# Using psql
docker-compose exec db psql -U wildbook -d wildbook

# Connection details:
# Host: localhost
# Port: 5433
# Database: wildbook
# Username: wildbook
# Password: wildbook (from .env)
```

### OpenSearch

Check cluster health:

```bash
curl http://localhost:9200/_cluster/health

# Should return JSON with cluster status
```

## First Steps

### Upload Test Images

1. Navigate to Wildbook at http://localhost:8080
2. Go to **Submit** → **Report an Encounter**
3. Upload sample wildlife photos
4. Fill in encounter details
5. Submit for detection

### Run Detection

1. After uploading images, go to **Detection**
2. Select images to process
3. Click **Run Detection**
4. Wait for WBIA to detect animals
5. Review detected annotations

### Query for Matches

1. Select an annotation
2. Click **Identify**
3. WBIA will query database for matching individuals
4. Review match results with confidence scores

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (fresh start next time)
docker-compose down -v
```

## Next Steps

- **[Development Guide](development.md)** - Learn development workflows
- **[Testing Guide](testing.md)** - Run functional tests
- **[Configuration](configuration.md)** - Customize your setup
- **[Architecture](architecture.md)** - Understand the system design

## Common First-Time Issues

### Services Won't Start

**Problem**: Docker compose fails to start services

**Solution**:
```bash
# Check Docker daemon is running
docker ps

# Check for port conflicts
lsof -i :8080  # Wildbook
lsof -i :5000  # WBIA

# View error logs
docker-compose logs
```

### Out of Memory

**Problem**: Services crash or won't start

**Solution**:
```bash
# Increase Docker memory in Docker Desktop
# Settings → Resources → Memory → 8GB or more

# Or reduce service memory in docker-compose.yml
```

### Slow First Start

**Problem**: Takes very long to start

**Solution**:
- First start builds images (10-15 minutes)
- Subsequent starts are much faster (1-2 minutes)
- Be patient on first run

### Database Connection Errors

**Problem**: Services can't connect to database

**Solution**:
```bash
# Wait for database to be healthy
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

## Getting Help

- **Documentation**: Continue to other docs in `/docs`
- **Issues**: https://github.com/WildMeOrg/wildbook-infra/issues
- **Community**: https://community.wildbook.org
- **Email**: dev@wildme.org