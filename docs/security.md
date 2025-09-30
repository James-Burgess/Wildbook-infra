# Security Guide

**Date**: September 30, 2024
**Status**: Best Practices
**Target Audience**: DevOps Engineers, System Administrators

## Overview

This guide covers security best practices for deploying and operating Wildbook Infrastructure. Security is a shared responsibility between the Wildbook platform, operators, and users.

## Security Principles

1. **Defense in Depth** - Multiple layers of security controls
2. **Least Privilege** - Minimal permissions necessary
3. **Secure by Default** - Security enabled out of the box
4. **Regular Updates** - Keep dependencies current
5. **Audit & Monitor** - Track all security-relevant events

---

## Authentication & Authorization

### User Authentication

**Development**:
```bash
# Default credentials (CHANGE IN PRODUCTION)
TEST_USERNAME=test_user
TEST_PASSWORD=test_password
```

**Production**:
```bash
# Use strong passwords (32+ characters)
openssl rand -base64 32

# Password requirements
# - Minimum 12 characters
# - Mix of uppercase, lowercase, numbers, symbols
# - No common passwords
# - Rotate every 90 days
```

### Database Authentication

**PostgreSQL**:
```bash
# Generate strong database passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
WBIA_DB_PASSWORD=$(openssl rand -base64 32)
WILDBOOK_DB_PASSWORD=$(openssl rand -base64 32)

# Store in .env with restricted permissions
chmod 600 .env
```

**Connection Security**:
```bash
# Require SSL for database connections
WILDBOOK_DB_CONNECTION_URL=jdbc:postgresql://db:5432/wildbook?ssl=true&sslmode=require
WBIA_DB_URI=postgresql://wbia:password@db:5432/wbia?sslmode=require
```

### API Authentication

**WBIA API Keys**:
```python
# Generate API key
import secrets
api_key = secrets.token_urlsafe(32)

# Configure in WBIA
export WBIA_API_KEY=$api_key
```

**Wildbook Session**:
```bash
# Configure session timeout (minutes)
SESSION_TIMEOUT=30

# Use secure session cookies
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict
```

---

## SSL/TLS Configuration

### Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --standalone \
  -d wildbook.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# Auto-renewal
sudo systemctl enable certbot.timer
```

### Certificate Management

**Certificate locations**:
```
/etc/letsencrypt/live/wildbook.yourdomain.com/
├── fullchain.pem  # Certificate + intermediates
├── privkey.pem    # Private key
└── chain.pem      # Intermediate certificates
```

**Permissions**:
```bash
# Protect private keys
sudo chmod 600 /etc/letsencrypt/live/*/privkey.pem
sudo chown root:root /etc/letsencrypt/live/*/privkey.pem
```

**Renewal testing**:
```bash
# Dry run
sudo certbot renew --dry-run

# Check expiration
openssl x509 -in /etc/letsencrypt/live/wildbook.yourdomain.com/fullchain.pem \
  -noout -dates
```

### TLS Configuration

**Nginx (Strong Security)**:
```nginx
# TLS 1.2+ only
ssl_protocols TLSv1.2 TLSv1.3;

# Strong ciphers (Mozilla Modern)
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers on;

# HSTS (force HTTPS)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# Disable SSL session tickets
ssl_session_tickets off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
```

**Test TLS configuration**:
```bash
# Use SSL Labs
# https://www.ssllabs.com/ssltest/

# Or testssl.sh
testssl.sh https://wildbook.yourdomain.com
```

---

## Network Security

### Firewall Configuration

**UFW (Ubuntu)**:
```bash
# Default deny
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH (consider changing port)
sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Verify
sudo ufw status verbose
```

**iptables (Advanced)**:
```bash
# Drop invalid packets
iptables -A INPUT -m state --state INVALID -j DROP

# Rate limit SSH
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 -j DROP

# Rate limit HTTP
iptables -A INPUT -p tcp --dport 80 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
```

### Docker Network Isolation

```yaml
# docker-compose.yml
networks:
  wildbook-net:
    internal: true  # No external access
  public-net:
    internal: false  # Internet access

services:
  nginx:
    networks:
      - public-net
      - wildbook-net

  wildbook:
    networks:
      - wildbook-net  # No direct internet access

  db:
    networks:
      - wildbook-net  # Internal only
```

### Service Exposure

**Principle**: Only expose what's necessary.

```yaml
# BAD: Exposing everything
ports:
  - "5432:5432"  # PostgreSQL (NEVER expose)
  - "9200:9200"  # OpenSearch (NEVER expose)
  - "5000:5000"  # WBIA (expose via proxy only)

# GOOD: Only expose reverse proxy
ports:
  - "80:80"
  - "443:443"
```

---

## Database Security

### PostgreSQL Hardening

**Configuration** (`postgresql.conf`):
```conf
# Network
listen_addresses = 'localhost'  # Or specific IPs
ssl = on
ssl_ciphers = 'HIGH:!aNULL'

# Logging
log_connections = on
log_disconnections = on
log_duration = on
log_statement = 'ddl'  # Log schema changes

# Security
password_encryption = scram-sha-256
```

**Authentication** (`pg_hba.conf`):
```conf
# Require SSL
hostssl all all 0.0.0.0/0 scram-sha-256

# Reject non-SSL
hostnossl all all 0.0.0.0/0 reject
```

**User Permissions**:
```sql
-- Principle of least privilege
CREATE USER wbia WITH PASSWORD 'strong-password';
GRANT CONNECT ON DATABASE wbia TO wbia;
GRANT USAGE ON SCHEMA public TO wbia;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO wbia;

-- Revoke superuser
REVOKE ALL PRIVILEGES ON DATABASE postgres FROM PUBLIC;

-- Audit users
SELECT usename, usesuper, usecreatedb FROM pg_user;
```

**Backups**:
```bash
# Encrypt backups
pg_dump wildbook | gpg --encrypt --recipient admin@example.com > backup.sql.gpg

# Secure backup permissions
chmod 600 /backups/*.sql.gz
```

---

## Secrets Management

### Environment Variables

**Development**:
```bash
# .env file with restricted permissions
chmod 600 .env
echo ".env" >> .gitignore
```

**Production Options**:

1. **Docker Secrets** (Swarm):
```bash
# Create secret
echo "my-secret-password" | docker secret create db_password -

# Use in compose
secrets:
  db_password:
    external: true

services:
  db:
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
```

2. **External Secret Manager**:
```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id wildbook/db/password

# HashiCorp Vault
vault kv get secret/wildbook/database

# GCP Secret Manager
gcloud secrets versions access latest --secret="wildbook-db-password"
```

3. **Encrypted Files**:
```bash
# Encrypt with GPG
gpg --encrypt --recipient admin@example.com .env

# Decrypt on server
gpg --decrypt .env.gpg > .env
chmod 600 .env
```

### Secret Rotation

```bash
#!/bin/bash
# rotate-secrets.sh

# 1. Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Update database
docker-compose exec db psql -U postgres -c \
  "ALTER USER wildbook WITH PASSWORD '$NEW_PASSWORD';"

# 3. Update .env
sed -i "s/WILDBOOK_DB_PASSWORD=.*/WILDBOOK_DB_PASSWORD=$NEW_PASSWORD/" .env

# 4. Restart services
docker-compose restart wildbook

# 5. Verify
docker-compose logs wildbook | grep "Connected to database"
```

---

## Application Security

### Dependency Management

**Check for vulnerabilities**:
```bash
# Python (WBIA)
pip install safety
safety check -r requirements.txt

# Java (Wildbook)
mvn dependency-check:check

# Docker images
docker scan wildme/wildbook:latest
```

**Update dependencies**:
```bash
# Python
pip list --outdated
pip install --upgrade package-name

# Java
mvn versions:display-dependency-updates
```

### Security Headers

**Nginx configuration**:
```nginx
# Prevent clickjacking
add_header X-Frame-Options "SAMEORIGIN" always;

# XSS protection
add_header X-XSS-Protection "1; mode=block" always;

# Prevent MIME sniffing
add_header X-Content-Type-Options "nosniff" always;

# Referrer policy
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

# Permissions policy
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

### Input Validation

**File uploads**:
```python
# Validate file types
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Validate file size
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Scan for malware (optional)
import clamd
scanner = clamd.ClamdUnixSocket()
scanner.scan('/path/to/uploaded/file')
```

**API input**:
```python
from pydantic import BaseModel, validator

class EncounterInput(BaseModel):
    species: str
    location: str

    @validator('species')
    def validate_species(cls, v):
        allowed = ['zebra_plains', 'giraffe', 'elephant']
        if v not in allowed:
            raise ValueError('Invalid species')
        return v
```

### Rate Limiting

**Nginx**:
```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=uploads:10m rate=2r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# Apply limits
location /api/ {
    limit_req zone=api burst=20 nodelay;
}

location /api/upload/ {
    limit_req zone=uploads burst=5 nodelay;
}

location /api/auth/login {
    limit_req zone=login burst=3 nodelay;
}
```

---

## Docker Security

### Image Security

**Use specific tags**:
```yaml
# BAD
image: postgres:latest

# GOOD
image: postgres:13.12
```

**Scan images**:
```bash
# Trivy
trivy image wildme/wildbook:latest

# Snyk
snyk container test wildme/wildbook:latest
```

**Multi-stage builds**:
```dockerfile
# Build stage
FROM maven:3.9-eclipse-temurin-17 AS build
# ... build app ...

# Runtime stage (minimal)
FROM eclipse-temurin:17-jre-alpine
COPY --from=build /app/target/app.jar /app.jar
```

### Container Hardening

**Run as non-root**:
```dockerfile
# Create user
RUN groupadd -r wildbook && useradd -r -g wildbook wildbook

# Switch user
USER wildbook
```

```yaml
# docker-compose.yml
services:
  wildbook:
    user: "1000:1000"
```

**Read-only filesystem**:
```yaml
services:
  wildbook:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

**Drop capabilities**:
```yaml
services:
  wildbook:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed
```

**Resource limits**:
```yaml
services:
  wildbook:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
          pids: 100
```

---

## Monitoring & Auditing

### Security Logging

**Log security events**:
```bash
# Failed login attempts
docker-compose logs wildbook | grep "authentication failed"

# Database connections
docker-compose exec db psql -U postgres -c \
  "SELECT * FROM pg_stat_activity;"

# API access logs
docker-compose logs nginx | grep "401\|403"
```

**Centralized logging**:
```yaml
# docker-compose.yml
services:
  wildbook:
    logging:
      driver: "syslog"
      options:
        syslog-address: "tcp://logserver:514"
        tag: "wildbook"
```

### Intrusion Detection

**Fail2ban**:
```ini
# /etc/fail2ban/jail.local
[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 5
findtime = 3600
bantime = 86400
```

**OSSEC** (Host-based IDS):
```xml
<rule id="100001" level="10">
  <if_matched_sid>5710</if_matched_sid>
  <description>Multiple failed login attempts</description>
</rule>
```

### Security Scanning

**Regular scans**:
```bash
# Vulnerability scan
nmap -sV wildbook.yourdomain.com

# Web application scan
nikto -h https://wildbook.yourdomain.com

# SQL injection test
sqlmap -u "https://wildbook.yourdomain.com/api/encounters?id=1"
```

---

## Incident Response

### Security Incident Checklist

1. **Detect** - Identify the incident
2. **Contain** - Isolate affected systems
3. **Eradicate** - Remove the threat
4. **Recover** - Restore services
5. **Lessons Learned** - Document and improve

### Incident Response Procedure

**1. Contain the breach**:
```bash
# Take services offline
docker-compose down

# Block attacker IP
sudo ufw deny from <attacker-ip>

# Preserve evidence
docker-compose logs > incident-$(date +%Y%m%d).log
cp /var/log/nginx/access.log evidence/
```

**2. Assess damage**:
```bash
# Check for unauthorized access
docker-compose exec db psql -U postgres -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Check for data exfiltration
grep "SELECT.*FROM" /var/log/postgresql/postgresql.log

# Check file modifications
find /opt/wildbook -type f -mtime -1
```

**3. Rotate credentials**:
```bash
# Change all passwords
./scripts/rotate-secrets.sh

# Revoke API keys
docker-compose exec wbia python -c \
  "from wbia import revoke_api_key; revoke_api_key('compromised-key')"

# Regenerate certificates
sudo certbot renew --force-renewal
```

**4. Notify stakeholders**:
```bash
# Email template
cat > incident-notification.txt << EOF
Subject: Security Incident Notification

We have detected a security incident affecting Wildbook infrastructure.

What happened: [Description]
When: [Timestamp]
Impact: [Affected systems/data]
Actions taken: [Response steps]
Next steps: [Recovery plan]

Contact: security@example.org
EOF
```

---

## Compliance & Privacy

### GDPR Compliance

**Data Subject Rights**:
```bash
# Right to access
docker-compose exec db psql -U postgres -d wildbook -c \
  "SELECT * FROM users WHERE email = 'user@example.com';"

# Right to erasure
docker-compose exec db psql -U postgres -d wildbook -c \
  "DELETE FROM users WHERE email = 'user@example.com';"

# Data export
docker-compose exec db pg_dump -U postgres -d wildbook \
  --table=users --where="email='user@example.com'" \
  > user-data-export.sql
```

**Data minimization**:
```sql
-- Automatically delete old data
DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM logs WHERE created_at < NOW() - INTERVAL '90 days';
```

### Data Encryption

**At rest** (disk encryption):
```bash
# LUKS encryption
cryptsetup luksFormat /dev/sdb
cryptsetup open /dev/sdb wildbook-data
mkfs.ext4 /dev/mapper/wildbook-data
```

**In transit** (SSL/TLS):
- All connections use HTTPS/TLS
- Database connections use SSL
- Internal service mesh with mTLS (Kubernetes)

**Database encryption**:
```sql
-- Encrypt sensitive columns
CREATE EXTENSION pgcrypto;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT,
    password_hash BYTEA,
    encrypted_data BYTEA
);

-- Encrypt data
INSERT INTO users (encrypted_data) VALUES (
    pgp_sym_encrypt('sensitive data', 'encryption-key')
);

-- Decrypt data
SELECT pgp_sym_decrypt(encrypted_data, 'encryption-key') FROM users;
```

---

## Security Checklist

### Pre-Production

- [ ] Change all default passwords
- [ ] Configure SSL/TLS with valid certificates
- [ ] Enable firewall (only 80/443 public)
- [ ] Configure database SSL
- [ ] Set up automated backups (encrypted)
- [ ] Enable security headers (CSP, HSTS, etc.)
- [ ] Configure rate limiting
- [ ] Run vulnerability scans
- [ ] Test backup restoration
- [ ] Document incident response plan

### Post-Deployment

- [ ] Monitor logs for suspicious activity
- [ ] Review failed login attempts
- [ ] Check for unauthorized API access
- [ ] Verify SSL certificate validity
- [ ] Test rate limiting effectiveness
- [ ] Review user permissions
- [ ] Update dependencies
- [ ] Rotate credentials (quarterly)

### Ongoing

- [ ] Monthly security scans
- [ ] Quarterly penetration testing
- [ ] Review access logs weekly
- [ ] Update threat model annually
- [ ] Conduct security training
- [ ] Patch vulnerabilities within 7 days
- [ ] Test incident response annually

---

## Security Contacts

### Reporting Security Issues

**Email**: security@wildme.org (use PGP for sensitive issues)

**PGP Key**: Available at https://www.wildme.org/pgp-key.asc

**Responsible Disclosure**:
- Report vulnerabilities privately
- Allow 90 days for fixes
- Coordinate public disclosure

### Security Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CIS Docker Benchmark**: https://www.cisecurity.org/benchmark/docker
- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework

---

**Document Owner**: Security Team
**Last Updated**: September 30, 2024
**Next Review**: December 31, 2024