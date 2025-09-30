# Configuration Guide

Complete reference for configuring Wildbook Infrastructure.

## Environment Variables

All configuration is managed through the `.env` file in the project root.

### Creating Configuration

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env  # or your preferred editor
```

## Core Configuration

### Docker Image Tags

```bash
# Docker image version to use
TAG=latest

# Options:
# - latest: Most recent build
# - nightly: Daily automated builds
# - v1.0.0: Specific release version
# - dev: Development builds
```

**Usage:**
```bash
TAG=v1.0.0 docker-compose up -d
```

## Database Configuration

### PostgreSQL

```bash
# PostgreSQL superuser password
POSTGRES_PASSWORD=postgres

# Should be strong in production
# Example: POSTGRES_PASSWORD=$(openssl rand -base64 32)
```

### WBIA Database

```bash
# Database name
WBIA_DB_NAME=wbia

# Database user
WBIA_DB_USER=wbia

# Database password
WBIA_DB_PASSWORD=wbia

# Full connection URI
WBIA_DB_URI=postgresql://wbia:wbia@db:5432/wbia
```

**Connection URI Format:**
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

### Wildbook Database

```bash
# Database name
WILDBOOK_DB_NAME=wildbook

# Database user
WILDBOOK_DB_USER=wildbook

# Database password
WILDBOOK_DB_PASSWORD=wildbook

# JDBC connection URL
WILDBOOK_DB_CONNECTION_URL=jdbc:postgresql://db:5432/wildbook
```

**JDBC URL Format:**
```
jdbc:postgresql://[host]:[port]/[database]
```

## Application Configuration

### Wildbook Settings

```bash
# Site name (shown in UI)
SITE_NAME=Wildbook

# Public URL path for React frontend
PUBLIC_URL=/react/

# Java heap memory settings
JAVA_OPTS="-Djava.awt.headless=true -Xms4096m -Xmx4096m"
```

**Memory Settings:**
- `-Xms`: Initial heap size
- `-Xmx`: Maximum heap size
- Recommended: 4GB minimum, 8GB for production
- Format: `-Xms4096m` (megabytes) or `-Xms4g` (gigabytes)

## Search Configuration

### OpenSearch

```bash
# Enable/disable disk threshold warnings
ES_THRESHOLD=true

# Admin password (required for OpenSearch 2.12+)
OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin123!

# Must meet requirements:
# - At least 8 characters
# - At least one uppercase letter
# - At least one lowercase letter
# - At least one digit
# - At least one special character
```

**Java Options:**
```bash
# In docker-compose.yml:
ES_JAVA_OPTS=-Xms512m -Xmx512m

# Adjust based on data volume:
# Small: -Xms512m -Xmx512m
# Medium: -Xms1g -Xmx1g
# Large: -Xms2g -Xmx2g
```

## Integration Configuration

### Houston (Authentication)

Optional integration with Wild Me's Houston authentication service.

```bash
# Houston OAuth client ID
HOUSTON_CLIENT_ID=

# Houston OAuth client secret
HOUSTON_CLIENT_SECRET=

# Leave empty if not using Houston
```

## Testing Configuration

### Test Timeouts

```bash
# Standard timeout for quick operations (seconds)
TEST_TIMEOUT=30

# Extended timeout for ML operations (seconds)
TEST_LONG_TIMEOUT=120
```

### Test Credentials

```bash
# Test user username
TEST_USERNAME=test_user

# Test user password
TEST_PASSWORD=test_password
```

## Advanced Configuration

### Service-Specific Settings

#### WBIA Additional Settings

Add to `docker-compose.yml` under `wbia` service:

```yaml
environment:
  # Python buffering
  PYTHONUNBUFFERED: "1"

  # WBIA work directory
  WBIA_WORKDIR: "/data/db"

  # Enable debug mode
  WBIA_DEBUG: "false"

  # ML model paths
  WBIA_MODEL_DIR: "/cache/models"
```

#### Wildbook Additional Settings

Add to `docker-compose.yml` under `wildbook` service:

```yaml
environment:
  # Tomcat settings
  CATALINA_OPTS: "-Dfile.encoding=UTF-8"

  # Database pool settings
  DB_POOL_MIN_SIZE: "5"
  DB_POOL_MAX_SIZE: "20"

  # Session timeout (minutes)
  SESSION_TIMEOUT: "30"
```

### Resource Limits

Add to `docker-compose.yml` under each service:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### Logging Configuration

Add to `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Environment-Specific Configurations

### Development

```bash
# .env.development
TAG=latest
POSTGRES_PASSWORD=postgres
WBIA_DB_PASSWORD=wbia
WILDBOOK_DB_PASSWORD=wildbook

# Relaxed settings for local dev
TEST_TIMEOUT=60
```

### Staging

```bash
# .env.staging
TAG=nightly
POSTGRES_PASSWORD=<strong-password>
WBIA_DB_PASSWORD=<strong-password>
WILDBOOK_DB_PASSWORD=<strong-password>

# Staging database
WILDBOOK_DB_CONNECTION_URL=jdbc:postgresql://staging-db.example.com:5432/wildbook
```

### Production

```bash
# .env.production
TAG=v1.0.0
POSTGRES_PASSWORD=<strong-password>
WBIA_DB_PASSWORD=<strong-password>
WILDBOOK_DB_PASSWORD=<strong-password>

# Production database with SSL
WILDBOOK_DB_CONNECTION_URL=jdbc:postgresql://prod-db.example.com:5432/wildbook?ssl=true&sslmode=require

# Increased memory
JAVA_OPTS="-Djava.awt.headless=true -Xms8192m -Xmx8192m"
```

### Using Different Environments

```bash
# Development
docker-compose --env-file .env.development up -d

# Staging
docker-compose --env-file .env.staging up -d

# Production
docker-compose --env-file .env.production up -d
```

## Security Best Practices

### Password Generation

```bash
# Generate strong passwords
openssl rand -base64 32

# Or use pwgen
pwgen -s 32 1

# Update .env file
POSTGRES_PASSWORD=$(openssl rand -base64 32)
WBIA_DB_PASSWORD=$(openssl rand -base64 32)
WILDBOOK_DB_PASSWORD=$(openssl rand -base64 32)
```

### Secrets Management

**Development:**
- Use `.env` file (gitignored)
- Keep `.env.example` with dummy values

**Production:**
- Use Docker secrets or Kubernetes secrets
- Never commit real credentials
- Rotate passwords regularly
- Use strong, unique passwords

### File Permissions

```bash
# Restrict .env file access
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw------- (owner read/write only)
```

## Configuration Files

### Wildbook Configuration Files

Located in `wildbook/devops/development/.dockerfiles/tomcat/`:

#### commonConfiguration.properties

```properties
# Database configuration
datanucleus.ConnectionURL=${WILDBOOK_DB_CONNECTION_URL}
datanucleus.ConnectionUserName=${WILDBOOK_DB_USER}
datanucleus.ConnectionPassword=${WILDBOOK_DB_PASSWORD}

# WBIA endpoint
wbiaURL=http://wbia:5000

# OpenSearch endpoint
elasticsearchURL=http://opensearch:9200
```

#### IA.properties

```properties
# WBIA integration settings
iaEnabled=true
iaUrl=http://wbia:5000/api/

# Detection settings
detectionEnabled=true
detectionConfidenceThreshold=0.5
```

### WBIA Configuration

WBIA is configured primarily through environment variables and command-line arguments.

**Command-line options:**
```bash
# See all options
docker-compose exec wbia python -m wbia.dev --help

# Common options:
--dbdir /data/db          # Database directory
--web                     # Enable web server
--port 5000              # Web server port
--containerized          # Run in container mode
--db-uri <uri>           # PostgreSQL URI
```

## Verification

### Check Current Configuration

```bash
# View current environment
docker-compose config

# View specific service config
docker-compose config wbia

# Check environment in running container
docker-compose exec wbia env
docker-compose exec wildbook env
```

### Test Configuration Changes

```bash
# Restart with new configuration
docker-compose down
docker-compose up -d

# Verify services start correctly
docker-compose ps

# Check logs for errors
docker-compose logs -f
```

## Troubleshooting Configuration

### Environment Variables Not Applied

```bash
# Recreate containers
docker-compose up -d --force-recreate

# Or remove and recreate
docker-compose down
docker-compose up -d
```

### Database Connection Issues

```bash
# Verify connection strings
echo $WBIA_DB_URI
echo $WILDBOOK_DB_CONNECTION_URL

# Test connection manually
docker-compose exec db psql $WBIA_DB_URI
```

### Memory Issues

```bash
# Check container memory usage
docker stats

# Increase memory in .env
JAVA_OPTS="-Xms8192m -Xmx8192m"

# Or in docker-compose.yml
```

## Configuration Templates

### Minimal Configuration

```bash
# .env.minimal - Bare minimum for local development
TAG=latest
POSTGRES_PASSWORD=postgres
```

### Full Configuration

```bash
# .env.full - All options configured
TAG=latest

# Database
POSTGRES_PASSWORD=postgres
WBIA_DB_NAME=wbia
WBIA_DB_USER=wbia
WBIA_DB_PASSWORD=wbia
WBIA_DB_URI=postgresql://wbia:wbia@db:5432/wbia
WILDBOOK_DB_NAME=wildbook
WILDBOOK_DB_USER=wildbook
WILDBOOK_DB_PASSWORD=wildbook
WILDBOOK_DB_CONNECTION_URL=jdbc:postgresql://db:5432/wildbook

# Application
SITE_NAME=Wildbook
PUBLIC_URL=/react/

# Search
ES_THRESHOLD=true
OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin123!

# Integration (optional)
HOUSTON_CLIENT_ID=
HOUSTON_CLIENT_SECRET=

# Testing
TEST_TIMEOUT=30
TEST_LONG_TIMEOUT=120
TEST_USERNAME=test_user
TEST_PASSWORD=test_password
```

## Additional Resources

- **[Getting Started](getting-started.md)** - Initial setup
- **[Development Guide](development.md)** - Development workflows
- **[Troubleshooting](troubleshooting.md)** - Common issues
- **Docker Compose Documentation**: https://docs.docker.com/compose/environment-variables/