# Production Deployment Guide

**Date**: September 30, 2024
**Status**: Draft
**Target Audience**: DevOps Engineers, System Administrators

## Overview

This guide covers three production deployment options for Wildbook Infrastructure. Choose based on your team's expertise, scale requirements, and infrastructure preferences.

**Configuration Files**:
- [Docker Compose Production Setup](docker-production-configuration.md) - Complete Docker Compose configs
- [AWS ECS Configuration](aws-ecs-configuration.md) - AWS-specific setup
- [GCP Cloud Run Configuration](gcp-cloudrun-configuration.md) - GCP-specific setup
- [Kubernetes Manifests](kubernetes-configuration.md) - K8s deployment files

## Deployment Options

### Option 1: Docker Compose (Recommended for Small-Medium)

Best for: Single-server deployments, small to medium installations (< 10,000 encounters)

**Pros**:
- Simple setup and maintenance
- All services on one host
- Easy backups and recovery
- Low complexity

**Cons**:
- Single point of failure (Data Loss)
- Limited horizontal scaling
- Manual updates required

### Option 2: Cloud Native (Recommended for Modern Cloud)

Best for: Cloud-first deployments, teams with cloud expertise, variable workloads

Using managed services like AWS ECS/Lambda, GCP Cloud Run/Cloud Functions, Azure Container Instances with managed databases (RDS, Cloud SQL, Azure Database for PostgreSQL).

**Pros**:
- Fully managed infrastructure
- Auto-scaling based on demand
- Pay-per-use pricing
- No server management
- Built-in monitoring and logging
- High availability by default
- Managed database backups

**Cons**:
- Vendor lock-in
- Cold start latency (serverless)
- More complex networking
- Higher cost at constant high load
- Requires cloud-specific knowledge


### Option 3: Kubernetes (Recommended for Large Scale)

Best for: Large deployments (> 50,000 encounters), multi-region

**Pros**:
- Industry standard
- Extensive ecosystem
- Auto-scaling
- Self-healing
- Managed options (EKS, GKE, AKS)

**Cons**:
- Complex setup
- Steep learning curve
- Higher operational overhead
- Overkill for smaller deployments

---

## Option 1: Docker Compose Production Setup

**Best for**: Small to medium deployments (< 10,000 encounters), teams familiar with Docker

### Architecture

Single server running all services via Docker Compose with Nginx reverse proxy for SSL termination.

```
Internet → Nginx (443) → Wildbook (8080)
                      → WBIA (5000)
                      → PostgreSQL (5432)
                      → OpenSearch (9200)
```

### Requirements

- **Server**: Ubuntu 22.04 LTS, 8+ cores, 32GB+ RAM, 500GB+ SSD
- **Network**: Static IP, domain name, SSL certificate
- **Software**: Docker Engine 24.0+, Docker Compose v2.20+

### Key Steps

1. **Server Setup** - Install Docker and dependencies
2. **Clone Repository** - Get wildbook-infra with submodules
3. **Configure Environment** - Set passwords, memory limits, SSL certs
4. **Deploy Services** - Start all containers with production overrides
5. **Setup Backups** - Automated database and volume backups
6. **Configure Monitoring** - Health checks and alerting

**Estimated Setup Time**: 2-4 hours

**Monthly Cost**: $80-300 depending on server size

### Detailed Guide

See [Docker Compose Production Configuration](docker-production-configuration.md) for complete setup instructions including:
- Step-by-step installation
- Production docker-compose.yml overrides
- Nginx configuration with SSL
- Backup and restore procedures
- Monitoring and alerting setup
- Update and maintenance procedures

---

## Option 2: Cloud Native Deployment

**Best for**: Cloud-first teams, variable workloads, teams wanting managed infrastructure

### Architecture

Managed services with auto-scaling containers and managed databases.

**AWS**:
```
Internet → ALB → ECS Fargate → RDS PostgreSQL
                              → S3 (backups)
```

**GCP**:
```
Internet → Cloud Run → Cloud SQL PostgreSQL
                    → Cloud Storage (backups)
```

**Azure**:
```
Internet → Container Instances → Azure Database for PostgreSQL
                               → Blob Storage (backups)
```

### Requirements

- **Cloud Account**: AWS, GCP, or Azure with billing enabled
- **CLI Tools**: aws-cli, gcloud, or azure-cli installed and configured
- **Permissions**: IAM permissions to create resources
- **Domain**: Custom domain for production (optional)

### Key Steps

1. **Create Managed Database** - RDS, Cloud SQL, or Azure Database
2. **Build & Push Images** - Upload to ECR, GCR, or ACR
3. **Deploy Containers** - ECS, Cloud Run, or Container Instances
4. **Configure Load Balancer** - ALB, Cloud Load Balancer, or App Gateway
5. **Setup Auto-Scaling** - Based on CPU/memory metrics
6. **Enable Monitoring** - CloudWatch, Cloud Monitoring, or Azure Monitor

**Estimated Setup Time**: 1-2 days

**Monthly Cost**: $200-1000+ depending on scale and services

### Cloud-Specific Guides

- **AWS**: [AWS ECS Configuration](aws-ecs-configuration.md) - ECS Fargate, RDS, ALB setup
- **GCP**: [GCP Cloud Run Configuration](gcp-cloudrun-configuration.md) - Cloud Run, Cloud SQL setup
- **Azure**: [Azure Configuration](azure-configuration.md) - Container Instances, Azure Database setup

### Advantages

- **Fully Managed**: No server management, automatic backups
- **Auto-Scaling**: Scales with demand automatically
- **High Availability**: Multi-AZ/region by default
- **Built-in Monitoring**: Native cloud monitoring and logging
- **Pay-per-use**: Only pay for what you use

### Considerations

- **Vendor Lock-in**: Harder to migrate between clouds
- **Cost**: Can be expensive at constant high load
- **Complexity**: Requires cloud-specific knowledge
- **Cold Starts**: Serverless options may have latency

---

## Option 3: Kubernetes Deployment

**Best for**: Large-scale deployments (> 50,000 encounters), multi-region, teams with K8s expertise

### Architecture

Container orchestration with auto-scaling, self-healing, and high availability.

```
Internet → Ingress (SSL) → Wildbook Pods (2+)
                        → WBIA Pods (2+)
                        → PostgreSQL StatefulSet
                        → OpenSearch StatefulSet
```

### Requirements

- **Kubernetes Cluster**: EKS, GKE, AKS, or self-hosted (1.24+)
- **Tools**: kubectl, Helm 3+
- **Add-ons**: Ingress controller (nginx), cert-manager (SSL)
- **Resources**: 16+ cores, 64GB+ RAM across nodes

### Key Steps

1. **Cluster Setup** - Create K8s cluster on cloud or self-hosted
2. **Install Add-ons** - Ingress controller, cert-manager, monitoring
3. **Deploy Secrets** - Database passwords, registry credentials
4. **Deploy Stateful Sets** - PostgreSQL, OpenSearch with persistent volumes
5. **Deploy Applications** - WBIA and Wildbook with replicas
6. **Configure Ingress** - SSL termination, routing
7. **Setup Auto-scaling** - HPA for pods, cluster autoscaler for nodes
8. **Enable Monitoring** - Prometheus, Grafana dashboards

**Estimated Setup Time**: 1-2 weeks

**Monthly Cost**: $300-800+ for managed K8s cluster

### Detailed Guide

See [Kubernetes Configuration](kubernetes-configuration.md) for complete setup including:
- Kubernetes manifests (Deployments, Services, StatefulSets)
- Ingress and SSL configuration
- Horizontal Pod Autoscaler (HPA) setup
- Persistent volume claims
- Backup CronJobs
- Prometheus and Grafana monitoring
- Helm charts (optional)

### Advantages

- **Highly Scalable**: Auto-scales pods and nodes
- **Self-Healing**: Automatic restarts and rescheduling
- **Rolling Updates**: Zero-downtime deployments
- **Multi-Region**: Can span multiple availability zones
- **Industry Standard**: Portable across clouds
- **Extensive Ecosystem**: Helm, operators, monitoring tools

### Considerations

- **Complexity**: Steep learning curve, requires K8s expertise
- **Overhead**: Operational burden of cluster management
- **Cost**: Managed K8s adds overhead, especially at small scale
- **Overkill**: Too complex for smaller deployments

---

## Comparison Summary

| Feature | Docker Compose | Cloud Native | Kubernetes |
|---------|---------------|--------------|------------|
| **Complexity** | Low | Medium | High |
| **Setup Time** | Hours | Days | Weeks |
| **Scaling** | Manual/Vertical | Automatic | Automatic |
| **Cost (small)** | $50-100/mo | $100-200/mo | $200-400/mo |
| **Cost (large)** | Limited | $500-1000/mo | $300-800/mo |
| **High Availability** | No | Yes | Yes |
| **Maintenance** | Manual | Managed | Active |
| **Best For** | < 10k encounters | Variable load | > 50k encounters |

## Getting Help

- **Documentation**: https://docs.wildme.org
- **Issues**: https://github.com/WildMeOrg/wildbook-infra/issues
- **Community**: https://community.wildbook.org

