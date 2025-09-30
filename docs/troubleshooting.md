# Troubleshooting Guide

Solutions to common issues when running Wildbook Infrastructure.

## Quick Diagnostics

### Check Service Status

```bash
# View all services
docker-compose ps

# Check specific service
docker-compose ps wbia
docker-compose ps wildbook

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f wbia
```

### Check Resource Usage

```bash
# View resource consumption
docker stats

# Check disk usage
docker system df

# Check Docker daemon
docker info
```

## Services Won't Start

### Docker Daemon Not Running

**Symptoms:**
- `Cannot connect to the Docker daemon`
- Services won't start

**Solution:**
```bash
# Start Docker daemon
# On Linux
sudo systemctl start docker

# On macOS/Windows
# Start Docker Desktop application

# Verify
docker ps
```

### Port Already in Use

**Symptoms:**
- `Bind for 0.0.0.0:8080 failed: port is already allocated`
- Services fail to start

**Solution:**
```bash
# Find what's using the port
lsof -i :8080  # Wildbook
lsof -i :5000  # WBIA
lsof -i :5433  # PostgreSQL
lsof -i :9200  # OpenSearch

# Kill the process or change ports in docker-compose.yml
ports:
  - "8081:8080"  # Use different host port
```

### Out of Memory

**Symptoms:**
- Services crash unexpectedly
- `OutOfMemoryError` in logs
- Container killed by OOM killer

**Solution:**
```bash
# Increase Docker memory
# Docker Desktop → Settings → Resources → Memory → 8GB+

# Or reduce memory in .env
JAVA_OPTS="-Xms2048m -Xmx2048m"

# Check memory usage
docker stats
```

### Disk Space Full

**Symptoms:**
- `no space left on device`
- Services won't start
- Database errors

**Solution:**
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Remove unused images
docker image prune -a

# Remove stopped containers
docker container prune

# Check disk usage
df -h
docker system df
```

## Database Issues

### PostgreSQL Won't Start

**Symptoms:**
- Database container exits immediately
- Connection refused errors

**Solution:**
```bash
# Check database logs
docker-compose logs db

# Remove corrupted data (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d db

# Verify database is healthy
docker-compose ps db
```

### Connection Refused

**Symptoms:**
- `could not connect to server: Connection refused`
- Services can't reach database

**Solution:**
```bash
# Wait for database to be fully started
docker-compose ps db  # Should show "healthy"

# Check database is accepting connections
docker-compose exec db pg_isready -U postgres

# Restart dependent services
docker-compose restart wbia wildbook
```

### Database Doesn't Exist

**Symptoms:**
- `database "wbia" does not exist`
- `database "wildbook" does not exist`

**Solution:**
```bash
# List databases
docker-compose exec db psql -U postgres -l

# Recreate databases (removes all data)
docker-compose down -v
docker-compose up -d db

# Or manually create
docker-compose exec db psql -U postgres -c "CREATE DATABASE wbia;"
docker-compose exec db psql -U postgres -c "CREATE DATABASE wildbook;"
```

### Permission Denied

**Symptoms:**
- `permission denied for database`
- `must be owner of database`

**Solution:**
```bash
# Grant permissions
docker-compose exec db psql -U postgres << 'EOF'
GRANT ALL PRIVILEGES ON DATABASE wbia TO wbia;
GRANT ALL PRIVILEGES ON DATABASE wildbook TO wildbook;
EOF

# Or recreate with correct permissions
docker-compose down -v
docker-compose up -d
```

## WBIA Issues

### WBIA Won't Start

**Symptoms:**
- WBIA container exits or restarts repeatedly
- API not accessible

**Solution:**
```bash
# Check WBIA logs
docker-compose logs -f wbia

# Common issues and fixes:

# 1. Database not ready
# Wait for db to be healthy first
docker-compose up -d db
docker-compose up -d wbia

# 2. Missing dependencies
# Rebuild image
docker-compose build --no-cache wbia
docker-compose up -d wbia

# 3. Port conflict
# Change port in docker-compose.yml
ports:
  - "5001:5000"
```

### WBIA API Not Responding

**Symptoms:**
- `Connection refused` or `timeout` when calling API
- 502/503 errors

**Solution:**
```bash
# Check WBIA is running
docker-compose ps wbia

# Test API directly
curl http://localhost:5000/api/core/db/info/

# Check inside container
docker-compose exec wbia curl http://localhost:5000/api/core/db/info/

# Restart WBIA
docker-compose restart wbia

# Check logs for errors
docker-compose logs -f wbia
```

### Import Errors

**Symptoms:**
- `ModuleNotFoundError: No module named 'wbia'`
- `ImportError: cannot import name`

**Solution:**
```bash
# Rebuild WBIA image
docker-compose build --no-cache wbia

# Verify dependencies installed
docker-compose exec wbia pip list | grep wbia

# Check Python path
docker-compose exec wbia python -c "import sys; print(sys.path)"
```

### Detection Not Working

**Symptoms:**
- Detection API returns errors
- No annotations created

**Solution:**
```bash
# Check WBIA logs
docker-compose logs -f wbia

# Verify model files exist
docker-compose exec wbia ls /cache/models

# Test detection endpoint
curl -X POST http://localhost:5000/api/engine/detect/cnn/ \
  -H "Content-Type: application/json" \
  -d '{"gid_list": [1]}'

# Restart WBIA
docker-compose restart wbia
```

## Wildbook Issues

### Wildbook Won't Start

**Symptoms:**
- Wildbook container exits
- Cannot access web interface

**Solution:**
```bash
# Check Wildbook logs
docker-compose logs -f wildbook

# Common issues:

# 1. Frontend build failed
# Rebuild with no cache
docker-compose build --no-cache wildbook

# 2. Database connection failed
# Verify database credentials in .env
# Restart wildbook after db is ready
docker-compose restart wildbook

# 3. Out of memory
# Increase heap size in .env
JAVA_OPTS="-Xms8192m -Xmx8192m"
```

### 404 Errors / Page Not Found

**Symptoms:**
- Blank page or 404 errors
- React app not loading

**Solution:**
```bash
# Check Tomcat logs
docker-compose exec wildbook tail -f /usr/local/tomcat/logs/catalina.out

# Verify WAR file deployed
docker-compose exec wildbook ls /usr/local/tomcat/webapps/
# Should see wildbook.war and wildbook/ directory

# Rebuild frontend
cd wildbook/frontend
npm install
npm run build
cd ../..
docker-compose build --no-cache wildbook
docker-compose up -d wildbook
```

### Can't Connect to WBIA

**Symptoms:**
- Detection/identification not working from Wildbook
- "WBIA service unavailable" errors

**Solution:**
```bash
# Verify WBIA is running
docker-compose ps wbia

# Test connection from Wildbook
docker-compose exec wildbook curl http://wbia:5000/api/core/db/info/

# Check network
docker network inspect wildbook-network

# Restart both services
docker-compose restart wbia wildbook
```

### Slow Performance

**Symptoms:**
- Pages load slowly
- Timeouts

**Solution:**
```bash
# Check resource usage
docker stats

# Increase memory
JAVA_OPTS="-Xms8192m -Xmx8192m"

# Check database performance
docker-compose exec db psql -U wildbook -d wildbook -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' ORDER BY duration DESC;
"

# Restart services
docker-compose restart
```

## OpenSearch Issues

### OpenSearch Won't Start

**Symptoms:**
- OpenSearch container exits
- Cluster health check fails

**Solution:**
```bash
# Check OpenSearch logs
docker-compose logs -f opensearch

# Common issues:

# 1. Insufficient memory
# Increase ES_JAVA_OPTS in docker-compose.yml
ES_JAVA_OPTS=-Xms1g -Xmx1g

# 2. vm.max_map_count too low (Linux)
sudo sysctl -w vm.max_map_count=262144

# 3. Permission issues
docker-compose down -v
docker-compose up -d opensearch
```

### Cluster Status Red/Yellow

**Symptoms:**
- Cluster health is red or yellow
- Search not working properly

**Solution:**
```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# Check nodes
curl http://localhost:9200/_cat/nodes?v

# Check indices
curl http://localhost:9200/_cat/indices?v

# Reset cluster (WARNING: deletes all search data)
docker-compose down
docker volume rm wildbook-opensearch-data
docker-compose up -d opensearch
```

## Network Issues

### Services Can't Communicate

**Symptoms:**
- Wildbook can't reach WBIA
- Connection refused between services

**Solution:**
```bash
# Verify all services on same network
docker network inspect wildbook-network

# Check service names resolve
docker-compose exec wildbook nslookup wbia
docker-compose exec wbia nslookup wildbook

# Recreate network
docker-compose down
docker network rm wildbook-network
docker-compose up -d
```

### DNS Resolution Fails

**Symptoms:**
- `Could not resolve host: wbia`
- Services can't find each other

**Solution:**
```bash
# Use service names, not localhost
# ✅ Correct:  http://wbia:5000
# ❌ Wrong:    http://localhost:5000

# Verify DNS
docker-compose exec wildbook cat /etc/hosts
docker-compose exec wildbook getent hosts wbia

# Restart Docker daemon (last resort)
sudo systemctl restart docker  # Linux
# Or restart Docker Desktop
```

## Test Issues

### Tests Won't Run

**Symptoms:**
- Test container fails to start
- Import errors in tests

**Solution:**
```bash
# Rebuild test container
docker-compose build tests

# Check test logs
docker-compose logs tests

# Verify services are running first
docker-compose ps

# Run tests manually
docker-compose run --rm tests bash
pip list
behave -v
```

### Tests Timeout

**Symptoms:**
- Tests fail with timeout errors
- Services not ready

**Solution:**
```bash
# Increase timeouts in .env
TEST_TIMEOUT=60
TEST_LONG_TIMEOUT=300

# Ensure services are healthy before tests
docker-compose ps

# Run health checks first
./tests/run-tests.sh health

# Then run other tests
./tests/run-tests.sh all
```

### Connection Refused in Tests

**Symptoms:**
- Tests can't connect to services
- `Connection refused` errors

**Solution:**
```bash
# Verify test container is on correct network
docker-compose run --rm tests bash
curl http://wbia:5000/api/core/db/info/

# Check environment variables
docker-compose config tests

# Services should use service names:
WBIA_URL=http://wbia:5000      # ✅ Correct
WBIA_URL=http://localhost:5000  # ❌ Wrong
```

## Build Issues

### Image Build Fails

**Symptoms:**
- `docker-compose build` fails
- Build timeout

**Solution:**
```bash
# Build without cache
docker-compose build --no-cache

# Build with verbose output
docker-compose build --progress=plain

# Increase Docker build memory
# Docker Desktop → Settings → Resources

# Check disk space
docker system df
df -h
```

### Submodule Issues

**Symptoms:**
- `fatal: No url found for submodule path`
- Submodules not initialized

**Solution:**
```bash
# Initialize submodules
git submodule update --init --recursive

# Reset submodules
git submodule deinit -f .
git submodule update --init --recursive

# Pull latest
git submodule update --remote --merge
```

## Performance Issues

### Slow Startup

**Symptoms:**
- Services take long time to start
- Timeouts during startup

**Solution:**
```bash
# First start is slow (building images)
# Subsequent starts are faster

# Start services one at a time
docker-compose up -d db
# Wait for healthy
docker-compose up -d wbia
# Wait for started
docker-compose up -d wildbook opensearch

# Reduce startup time
# Use pre-built images instead of building
```

### High CPU Usage

**Symptoms:**
- System becomes sluggish
- Fans spinning

**Solution:**
```bash
# Check which container is using CPU
docker stats

# Limit CPU usage in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'

# Stop unnecessary services
docker-compose stop mailhog autoheal
```

### High Memory Usage

**Symptoms:**
- System runs out of memory
- Swap usage high

**Solution:**
```bash
# Check memory usage
docker stats

# Reduce memory allocation
# In .env:
JAVA_OPTS="-Xms2048m -Xmx2048m"

# In docker-compose.yml:
ES_JAVA_OPTS=-Xms512m -Xmx512m

# Stop unused services
docker-compose stop opensearch  # If not using search
```

## Complete Reset

If all else fails, nuclear option:

```bash
# Stop everything
docker-compose down -v

# Remove all wildbook containers
docker ps -a | grep wildbook | awk '{print $1}' | xargs docker rm -f

# Remove all wildbook images
docker images | grep wildbook | awk '{print $3}' | xargs docker rmi -f

# Remove all volumes
docker volume prune -f

# Clean system
docker system prune -a --volumes

# Start fresh
git pull
git submodule update --init --recursive
cp .env.example .env
docker-compose up -d --build
```

## Getting Help

If you're still stuck:

1. **Check logs**: `docker-compose logs -f`
2. **Search issues**: https://github.com/WildMeOrg/wildbook-infra/issues
3. **Ask community**: https://community.wildbook.org
4. **File issue**: Include:
   - Output of `docker-compose ps`
   - Relevant logs
   - Docker version
   - OS/platform
   - Steps to reproduce

## Additional Resources

- **[Getting Started](getting-started.md)** - Setup instructions
- **[Development Guide](development.md)** - Development workflows
- **[Configuration](configuration.md)** - Configuration options
- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Documentation**: https://docs.docker.com/compose/