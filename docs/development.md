# Development Guide

Guide for developers working on Wildbook Infrastructure.

## Development Environment Setup

### Prerequisites

- Docker and Docker Compose installed
- Git configured
- Python 3.11+ (for local testing)
- Node.js 18+ (for Wildbook frontend)
- Maven 3.9+ (for Wildbook backend)

### Initial Setup

```bash
# Clone with submodules
git clone --recursive https://github.com/WildMeOrg/wildbook-infra.git
cd wildbook-infra

# Set up environment
cp .env.example .env
```

## Working with Services

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start with build (after code changes)
docker-compose up -d --build

# Start specific services
docker-compose up -d db wbia

# Start in foreground (see logs)
docker-compose up

# Start with development tools (MailHog)
docker-compose --profile dev up -d
```

### Managing Services

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f wbia
docker-compose logs -f wildbook

# Restart a service
docker-compose restart wbia

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

### Accessing Containers

```bash
# Open shell in running container
docker-compose exec wbia bash
docker-compose exec wildbook bash

# Run one-off command
docker-compose exec wbia python -c "import wbia; print(wbia.__version__)"

# Access database
docker-compose exec db psql -U postgres -d wildbook
docker-compose exec db psql -U wbia -d wbia
```

## Working with Submodules

### Understanding Submodules

This repository uses Git submodules for:
- `wildbook-ia/` - WBIA machine learning service
- `wildbook/` - Main Wildbook platform

### Updating Submodules

```bash
# Update all submodules to latest
git submodule update --remote --merge

# Update specific submodule
cd wildbook-ia
git pull origin main
cd ..
git add wildbook-ia
git commit -m "Update wildbook-ia"
```

### Making Changes in Submodules

```bash
# Navigate to submodule
cd wildbook-ia  # or wildbook

# Create feature branch
git checkout -b feature/my-feature

# Make changes
# ... edit files ...

# Commit in submodule
git add .
git commit -m "Add new feature"
git push origin feature/my-feature

# Go back to parent repo
cd ..

# Update parent to point to new commit
git add wildbook-ia
git commit -m "Update wildbook-ia with new feature"
git push
```

### Syncing Submodules

```bash
# If someone else updated submodules
git pull
git submodule update --init --recursive

# Or in one command
git pull --recurse-submodules
```

## Building Images

### Build Specific Service

```bash
# Build WBIA
docker-compose build wbia

# Build Wildbook
docker-compose build wildbook

# Build without cache (clean build)
docker-compose build --no-cache wbia
```

### Build with Specific Tag

```bash
# Build and tag
TAG=v1.0.0 docker-compose build

# Images will be tagged as:
# wildme/wbia:v1.0.0
# wildme/wildbook:v1.0.0
```

### Build for Multiple Architectures

```bash
# For production multi-arch builds
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t wildme/wbia:latest ./wildbook-ia
```

## Development Workflows

### WBIA Development

```bash
# Edit code in wildbook-ia/
cd wildbook-ia
# ... make changes ...

# Rebuild and restart
cd ..
docker-compose up -d --build wbia

# View logs
docker-compose logs -f wbia

# Run tests
docker-compose exec wbia pytest

# Or run functional tests
./tests/run-tests.sh wbia
```

### Wildbook Development

```bash
# Edit code in wildbook/
cd wildbook
# ... make changes ...

# Rebuild and restart
cd ..
docker-compose up -d --build wildbook

# View logs
docker-compose logs -f wildbook

# Run Maven tests (if available)
docker-compose exec wildbook bash -c "cd /app && mvn test"
```

### Frontend Development (Wildbook)

```bash
# Work on frontend locally
cd wildbook/frontend

# Install dependencies
npm install

# Start dev server (with hot reload)
npm start

# Build production bundle
npm run build

# Rebuild Docker image with new frontend
cd ../..
docker-compose build --no-cache wildbook
docker-compose up -d wildbook
```

### Database Migrations

```bash
# Connect to database
docker-compose exec db psql -U postgres

# Backup database
docker-compose exec db pg_dump -U wildbook wildbook > backup.sql

# Restore database
docker-compose exec -T db psql -U wildbook wildbook < backup.sql

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

## Code Style and Quality

### Python (WBIA)

```bash
# Format code
cd wildbook-ia
brunette --config=setup.cfg .

# Sort imports
isort --settings-path setup.cfg .

# Lint
flake8

# Run pre-commit hooks
pre-commit run --all-files
```

### Java (Wildbook)

```bash
# Format code
cd wildbook
mvn formatter:format

# Run checkstyle
mvn checkstyle:check

# Run tests
mvn test
```

### JavaScript (Wildbook Frontend)

```bash
cd wildbook/frontend

# Lint
npm run lint

# Format
npm run format

# Type check
npm run type-check
```

## Testing During Development

### Quick Test Runs

```bash
# Test your changes
./tests/run-tests.sh all

# Test specific component
./tests/run-tests.sh wbia
./tests/run-tests.sh wildbook

# Debug tests
./tests/run-tests.sh shell
behave --stop --no-capture
```

See [Testing Guide](testing.md) for comprehensive testing documentation.

## Debugging

### Debugging WBIA

```bash
# Open Python shell in container
docker-compose exec wbia python

# Run with debugger
docker-compose exec wbia python -m pdb -m wbia.dev --dbdir /data/db

# Check logs
docker-compose logs -f wbia

# Inspect database
docker-compose exec db psql -U wbia -d wbia
\dt  # List tables
SELECT * FROM images LIMIT 10;
```

### Debugging Wildbook

```bash
# Open bash shell
docker-compose exec wildbook bash

# Check Tomcat logs
docker-compose exec wildbook tail -f /usr/local/tomcat/logs/catalina.out

# Check application logs
docker-compose exec wildbook tail -f /usr/local/tomcat/logs/wildbook.log

# Inspect database
docker-compose exec db psql -U wildbook -d wildbook
```

### Debugging Network Issues

```bash
# Test connectivity between containers
docker-compose exec wildbook curl http://wbia:5000/api/core/db/info/
docker-compose exec wbia curl http://wildbook:8080

# Inspect network
docker network inspect wildbook-network

# Check DNS resolution
docker-compose exec wildbook nslookup wbia
docker-compose exec wbia nslookup wildbook
```

## Performance Profiling

### WBIA Profiling

```bash
# Profile Python code
docker-compose exec wbia python -m cProfile -o output.prof -m wbia.dev

# Analyze profile
docker-compose exec wbia python -m pstats output.prof
```

### Wildbook Profiling

```bash
# Enable JMX monitoring
# Add to docker-compose.yml under wildbook environment:
# JAVA_OPTS: "-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.port=9010"

# Connect with JConsole or VisualVM
jconsole localhost:9010
```

## Contributing

### Before Submitting PR

1. **Run tests**: `./tests/run-tests.sh all`
2. **Check code style**: Run formatters and linters
3. **Update documentation**: If changing behavior
4. **Write tests**: For new features
5. **Update CHANGELOG**: Describe changes

### Pull Request Guidelines

- Create feature branch in submodule first
- Write clear commit messages
- Include tests for new features
- Update documentation as needed
- Reference related issues
- Keep PRs focused and small

### Code Review Process

1. Submit PR to submodule repository
2. Address reviewer feedback
3. Ensure CI passes
4. Wait for approval
5. Merge to submodule
6. Update parent repo with new commit

## Environment-Specific Configuration

### Development

```bash
# Use local .env
cp .env.example .env

# Use SQLite for faster iteration
# (default in WBIA)
```

### Staging

```bash
# Use staging environment file
cp .env.staging .env

# Use staging database
WILDBOOK_DB_CONNECTION_URL=jdbc:postgresql://staging-db:5432/wildbook
```

### Production

```bash
# Use production environment file
cp .env.production .env

# Use production database with replication
WILDBOOK_DB_CONNECTION_URL=jdbc:postgresql://prod-db-primary:5432/wildbook
```

## Additional Resources

- **[Testing Guide](testing.md)** - Comprehensive testing documentation
- **[Configuration](configuration.md)** - All configuration options
- **[Architecture](architecture.md)** - System design and patterns
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions