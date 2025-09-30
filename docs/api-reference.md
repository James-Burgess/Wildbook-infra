# API Reference

**Date**: September 30, 2024
**Status**: Documentation
**Target Audience**: Developers integrating with Wildbook

## Overview

Wildbook Infrastructure exposes two main APIs:

1. **WBIA API** (Port 5000) - Machine learning services (detection, classification, identification)
2. **Wildbook API** (Port 8080) - Wildlife database and encounter management

## Authentication

### WBIA API

WBIA uses basic authentication or API keys.

```bash
# Using basic auth
curl -u username:password http://localhost:5000/api/core/db/info/

# Using API key (if configured)
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/core/db/info/
```

### Wildbook API

Wildbook uses session-based authentication with optional Houston OAuth integration.

```bash
# Login to get session cookie
curl -c cookies.txt -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}'

# Use session cookie for subsequent requests
curl -b cookies.txt http://localhost:8080/api/encounters
```

## WBIA API

### Base URL

```
http://localhost:5000/api
```

### Core Endpoints

#### Health Check

```http
GET /api/core/db/info/
```

Returns database and system information.

**Response**:
```json
{
  "dbname": "wbia",
  "uuid": "...",
  "num_annotations": 0,
  "num_images": 0,
  "num_names": 0
}
```

---

#### Upload Image

```http
POST /api/upload/image/
```

Upload an image for processing.

**Request**:
```bash
curl -X POST http://localhost:5000/api/upload/image/ \
  -F "image=@/path/to/image.jpg"
```

**Response**:
```json
{
  "status": "ok",
  "gid": 1,
  "uuid": "image-uuid-..."
}
```

---

#### Detect Animals

```http
POST /api/engine/detect/cnn/
```

Run detection model on images to find animals.

**Request**:
```json
{
  "gid_list": [1, 2, 3],
  "species": "zebra_plains"
}
```

**Example**:
```bash
curl -X POST http://localhost:5000/api/engine/detect/cnn/ \
  -H "Content-Type: application/json" \
  -d '{"gid_list": [1]}'
```

**Response**:
```json
{
  "status": "ok",
  "aid_list": [1, 2, 3],
  "annotations": [
    {
      "aid": 1,
      "gid": 1,
      "bbox": [100, 200, 300, 400],
      "theta": 0.0,
      "confidence": 0.95,
      "species": "zebra_plains"
    }
  ]
}
```

---

#### Extract Features (Embeddings)

```http
POST /api/engine/plugin/pie/
```

Extract feature embeddings for individual identification.

**Request**:
```json
{
  "aid_list": [1, 2, 3]
}
```

**Response**:
```json
{
  "status": "ok",
  "embeddings": [
    {
      "aid": 1,
      "vector": [0.123, 0.456, ...],
      "model": "miewid"
    }
  ]
}
```

---

#### Query/Match Individuals

```http
POST /api/engine/query/graph/
```

Find matching individuals using embeddings.

**Request**:
```json
{
  "qaid_list": [1],
  "daid_list": [2, 3, 4, 5]
}
```

**Response**:
```json
{
  "qaid": 1,
  "results": [
    {
      "daid": 3,
      "score": 0.92,
      "rank": 1
    },
    {
      "daid": 2,
      "score": 0.78,
      "rank": 2
    }
  ]
}
```

---

#### Get Annotations

```http
GET /api/annot/
GET /api/annot/<aid>/
```

Retrieve annotation details.

**Response**:
```json
{
  "aid": 1,
  "gid": 1,
  "bbox": [100, 200, 300, 400],
  "theta": 0.0,
  "species": "zebra_plains",
  "viewpoint": "left",
  "quality": "good",
  "name": "zebra-001"
}
```

---

### Complete ML Pipeline

For a full workflow (upload → detect → identify):

```bash
# 1. Upload image
gid=$(curl -X POST http://localhost:5000/api/upload/image/ \
  -F "image=@zebra.jpg" | jq -r '.gid')

# 2. Run detection
aid=$(curl -X POST http://localhost:5000/api/engine/detect/cnn/ \
  -H "Content-Type: application/json" \
  -d "{\"gid_list\": [$gid]}" | jq -r '.aid_list[0]')

# 3. Extract features
curl -X POST http://localhost:5000/api/engine/plugin/pie/ \
  -H "Content-Type: application/json" \
  -d "{\"aid_list\": [$aid]}"

# 4. Query for matches
curl -X POST http://localhost:5000/api/engine/query/graph/ \
  -H "Content-Type: application/json" \
  -d "{\"qaid_list\": [$aid]}"
```

---

## Wildbook API

### Base URL

```
http://localhost:8080/api
```

### Core Endpoints

#### List Encounters

```http
GET /api/encounters
```

Get all encounters in the system.

**Query Parameters**:
- `limit` - Number of results (default: 50)
- `offset` - Pagination offset (default: 0)
- `species` - Filter by species
- `location` - Filter by location

**Response**:
```json
{
  "encounters": [
    {
      "id": "enc-001",
      "species": "zebra_plains",
      "location": "Serengeti",
      "date": "2024-09-30",
      "individualId": "zebra-001",
      "images": [...]
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

---

#### Get Encounter

```http
GET /api/encounters/<id>
```

Get details for a specific encounter.

**Response**:
```json
{
  "id": "enc-001",
  "species": "zebra_plains",
  "sex": "female",
  "age": "adult",
  "location": {
    "name": "Serengeti",
    "lat": -2.333,
    "lng": 34.833
  },
  "date": "2024-09-30T10:30:00Z",
  "individualId": "zebra-001",
  "annotations": [...],
  "mediaAssets": [...]
}
```

---

#### Create Encounter

```http
POST /api/encounters
```

Create a new encounter.

**Request**:
```json
{
  "species": "zebra_plains",
  "location": "Serengeti",
  "date": "2024-09-30",
  "images": [
    {
      "url": "http://example.com/image.jpg"
    }
  ]
}
```

**Response**:
```json
{
  "id": "enc-002",
  "status": "created",
  "url": "/api/encounters/enc-002"
}
```

---

#### List Individuals

```http
GET /api/individuals
```

Get all individuals (named animals).

**Response**:
```json
{
  "individuals": [
    {
      "id": "zebra-001",
      "species": "zebra_plains",
      "sex": "female",
      "encounters": ["enc-001", "enc-005", "enc-012"],
      "firstSeen": "2022-03-15",
      "lastSeen": "2024-09-30"
    }
  ]
}
```

---

#### Submit to Identification

```http
POST /api/identify
```

Submit encounter for ML-based identification.

**Request**:
```json
{
  "encounterId": "enc-002",
  "algorithm": "pie"
}
```

**Response**:
```json
{
  "jobId": "job-123",
  "status": "queued",
  "estimatedTime": 120
}
```

---

#### Check Job Status

```http
GET /api/jobs/<jobId>
```

Check status of ML processing job.

**Response**:
```json
{
  "jobId": "job-123",
  "status": "completed",
  "results": {
    "matches": [
      {
        "individualId": "zebra-001",
        "confidence": 0.92
      }
    ]
  }
}
```

---

## Error Handling

### HTTP Status Codes

- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily down

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Image format not supported",
    "details": {
      "parameter": "image",
      "supported": ["jpg", "png", "gif"]
    }
  }
}
```

### Common Error Codes

**WBIA API**:
- `INVALID_IMAGE` - Image format or quality issues
- `MODEL_NOT_FOUND` - Requested ML model not available
- `DETECTION_FAILED` - Detection algorithm failed
- `DATABASE_ERROR` - Database operation failed

**Wildbook API**:
- `ENCOUNTER_NOT_FOUND` - Encounter ID doesn't exist
- `INVALID_SPECIES` - Species not recognized
- `AUTHENTICATION_REQUIRED` - Must authenticate first
- `PERMISSION_DENIED` - Insufficient permissions

---

## Rate Limiting

### WBIA API

- **Upload**: 10 requests/minute per IP
- **Detection**: 5 requests/minute (ML operations are expensive)
- **Query**: 20 requests/minute
- **Other endpoints**: 60 requests/minute

### Wildbook API

- **Authenticated**: 100 requests/minute per user
- **Unauthenticated**: 20 requests/minute per IP

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1696089600
```

When rate limited:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## Pagination

### Query Parameters

```http
GET /api/encounters?limit=50&offset=100
```

- `limit` - Results per page (max: 100, default: 50)
- `offset` - Number of results to skip

### Response Headers

```http
X-Total-Count: 1523
Link: </api/encounters?limit=50&offset=150>; rel="next",
      </api/encounters?limit=50&offset=50>; rel="prev"
```

---

## Webhooks

### Configuration

Configure webhooks in Wildbook settings or via API:

```http
POST /api/webhooks
```

**Request**:
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["encounter.created", "identification.completed"],
  "secret": "webhook-secret-key"
}
```

### Webhook Payload

```json
{
  "event": "identification.completed",
  "timestamp": "2024-09-30T12:00:00Z",
  "data": {
    "jobId": "job-123",
    "encounterId": "enc-002",
    "matches": [...]
  },
  "signature": "sha256=..."
}
```

Verify webhook signature:
```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## SDK Examples

### Python

```python
import requests

class WBIAClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url

    def upload_image(self, image_path):
        with open(image_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/api/upload/image/",
                files={'image': f}
            )
        return response.json()['gid']

    def detect(self, gid):
        response = requests.post(
            f"{self.base_url}/api/engine/detect/cnn/",
            json={'gid_list': [gid]}
        )
        return response.json()['aid_list']

    def identify(self, aid):
        response = requests.post(
            f"{self.base_url}/api/engine/query/graph/",
            json={'qaid_list': [aid]}
        )
        return response.json()

# Usage
client = WBIAClient()
gid = client.upload_image('zebra.jpg')
aids = client.detect(gid)
matches = client.identify(aids[0])
print(f"Found {len(matches['results'])} matches")
```

### JavaScript

```javascript
class WildbookClient {
  constructor(baseUrl = 'http://localhost:8080') {
    this.baseUrl = baseUrl;
  }

  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password })
    });
    return response.ok;
  }

  async getEncounters(limit = 50, offset = 0) {
    const response = await fetch(
      `${this.baseUrl}/api/encounters?limit=${limit}&offset=${offset}`,
      { credentials: 'include' }
    );
    return response.json();
  }

  async createEncounter(data) {
    const response = await fetch(`${this.baseUrl}/api/encounters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(data)
    });
    return response.json();
  }
}

// Usage
const client = new WildbookClient();
await client.login('user', 'pass');
const encounters = await client.getEncounters();
console.log(`Found ${encounters.total} encounters`);
```

---

## Testing APIs

### Using curl

```bash
# Test WBIA health
curl http://localhost:5000/api/core/db/info/

# Upload and detect
curl -X POST http://localhost:5000/api/upload/image/ \
  -F "image=@test.jpg" \
  | jq -r '.gid' \
  | xargs -I {} curl -X POST http://localhost:5000/api/engine/detect/cnn/ \
    -H "Content-Type: application/json" \
    -d '{"gid_list": [{}]}'
```

### Using Postman

1. Import OpenAPI spec: `http://localhost:5000/api/docs/swagger.json`
2. Set environment variables:
   - `WBIA_URL`: `http://localhost:5000`
   - `WILDBOOK_URL`: `http://localhost:8080`
3. Test endpoints from collection

### Using Python requests

```python
import requests

# WBIA
response = requests.get('http://localhost:5000/api/core/db/info/')
print(response.json())

# Wildbook (with auth)
session = requests.Session()
session.post('http://localhost:8080/api/auth/login',
             json={'username': 'user', 'password': 'pass'})
encounters = session.get('http://localhost:8080/api/encounters').json()
```

---

## API Versioning

Currently on **v1** (implicit in URLs).

Future versions will be explicitly versioned:
```
/api/v2/encounters
```

**Version Support**:
- v1: Current, maintained
- v2: Future (planned for ml-service integration)

**Deprecation Policy**:
- Deprecation announced 6 months in advance
- Old versions supported for 12 months after deprecation
- Breaking changes only in major versions

---

## Additional Resources

- **OpenAPI Spec**: http://localhost:5000/api/docs/swagger.json
- **Interactive Docs**: http://localhost:5000/docs (Swagger UI)
- **WBIA Documentation**: https://wildmeorg.github.io/wildbook-ia/
- **Community Forum**: https://community.wildbook.org
- **GitHub Issues**: https://github.com/WildMeOrg/wildbook-infra/issues

---

**Document Owner**: API Team
**Last Updated**: September 30, 2024
**Next Review**: December 31, 2024