# Wildbook Infrastructure

Unified Docker orchestration for the Wildbook wildlife conservation platform.

## 🚀 Quick Start

```bash
# Clone repository with submodules
git clone --recursive https://github.com/WildMeOrg/wildbook-infra.git
cd wildbook-infra

# Set up environment
cp .env.example .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

**Access the applications:**
- **Wildbook**: http://localhost:8080
- **WBIA API**: http://localhost:5000
- **OpenSearch**: http://localhost:9200
- **PostgreSQL**: localhost:5433

## 📚 Documentation

### Getting Started
- **[Getting Started](docs/getting-started.md)** - Initial setup and first steps
- **[Configuration](docs/configuration.md)** - Environment variables and settings
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

### Development
- **[Development Guide](docs/development.md)** - Development workflow and building
- **[Testing Guide](docs/testing.md)** - Running and writing tests
- **[API Reference](docs/api-reference.md)** - WBIA and Wildbook API documentation
- **[Plugin System](docs/plugins.md)** - Available plugins and how to create your own
- **[Contributing](CONTRIBUTING.md)** - How to contribute to the project

### Operations
- **[Production Deployment](docs/production-deployment.md)** - Production setup and operations
- **[Security Guide](docs/security.md)** - Security best practices and hardening
- **[Upgrade Plans](docs/upgrade-plans.md)** - ml-service migration roadmap

### Architecture
- **[WBIA Architecture](docs/wbia-architecture.md)** - Technical deep-dive into WBIA

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Wildbook Platform                       │
│              (Java/Tomcat - Port 8080)                   │
└────────────┬──────────────────────────────┬─────────────┘
             │                              │
    ┌────────▼────────┐          ┌─────────▼──────────┐
    │   PostgreSQL    │          │   WBIA ML Service  │
    │   (Port 5433)   │          │   (Port 5000)      │
    │ ├─ wildbook DB  │          │ - Detection        │
    │ └─ wbia DB      │          │ - Classification   │
    └─────────────────┘          └────────────────────┘
```

See [Architecture Documentation](docs/architecture.md) for detailed diagrams.

## 🎯 Common Tasks

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start with logs visible
docker-compose up

# Start specific services
docker-compose up -d db wbia
```

### Running Tests

```bash
# Run all tests
docker-compose run --rm tests

# Or use helper script
./tests/run-tests.sh all

# Specific test suites
./tests/run-tests.sh health
./tests/run-tests.sh wbia
```

See [Testing Guide](docs/testing.md) for comprehensive testing documentation.

### Managing Services

```bash
# View logs
docker-compose logs -f

# Restart a service
docker-compose restart wbia

# Stop all services
docker-compose down
```

See [Development Guide](docs/development.md) for more commands.

## 🤝 Contributing

We welcome contributions! Please see our [Development Guide](docs/development.md) for:
- Setting up your development environment
- Working with submodules
- Code style guidelines
- Testing requirements
- Pull request process

## 📝 License

See LICENSE files in individual submodules:
- Wildbook: Apache License 2.0
- WBIA: Apache License 2.0

## 🙏 Support

- **Documentation**: https://docs.wildme.org
- **Issues**: https://github.com/WildMeOrg/wildbook-infra/issues
- **Community**: https://community.wildbook.org
- **Email**: dev@wildme.org

---

**Wild Me** - Supporting wildlife conservation through technology
https://www.wildme.org