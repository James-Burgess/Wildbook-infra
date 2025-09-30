# Upgrade Plans - ml-service Migration

**Date**: September 30, 2024
**Status**: Planning
**Priority**: Medium (Monitor & Prepare)

## Executive Summary

Wild Me is developing **ml-service**, a modern FastAPI-based replacement for WBIA (wildbook-ia). While still in active development, it shows significant progress with a complete ML pipeline added in September 2024. This document outlines our analysis and migration plan.

## ml-service Analysis

### What is ml-service?

Repository: https://github.com/WildMeOrg/ml-service

**Description**: Fast API-based Machine Learning Services for Wildbook and Friends

**Status**:
- Created: July 2024
- Last Updated: September 24, 2024
- Active development (multiple commits per month)
- Contributors: LashaO, vkirkl, jmcdonald27 (Wild Me team)
- License: MIT
- Stars: 0, Forks: 0 (internal project)

### Architecture Comparison

| Aspect | WBIA (wildbook-ia) | ml-service |
|--------|-------------------|------------|
| **Framework** | Flask + Tornado | FastAPI (async) |
| **Python** | 3.7-3.12 | 3.11+ |
| **Architecture** | Monolithic with plugins | Microservice |
| **Database** | Dual DB (main + cache) | Stateless (no DB) |
| **API Design** | flask-restx + custom decorators | FastAPI + OpenAPI |
| **Models** | Plugin injection (utool) | Config-driven handlers |
| **Created** | ~2015 (IBEIS fork) | July 2024 |
| **Tech Debt** | High (legacy patterns) | Low (clean slate) |

### Key Features (as of Sept 2024)

✅ **Core ML Pipeline** (Added Sept 23, 2024):
1. Detection - YOLO, MegaDetector
2. Classification - EfficientNet
3. Embeddings - MiewID (for individual ID)

✅ **API Endpoints**:
- `/predict` - Object detection
- `/classify` - Image classification
- `/extract` - Embeddings extraction
- `/explain` - Model visualization
- `/pipeline` - End-to-end workflow

✅ **Modern Stack**:
- FastAPI with auto-generated Swagger docs
- Async/await support
- Type hints + Pydantic validation
- JSON config-driven models

### What ml-service Does Better

**Architecture**:
- Clean, modern codebase
- No complex method injection
- Microservice-ready
- Better separation of concerns

**Developer Experience**:
- `/docs` automatic interactive API
- Simpler to extend
- Better error handling
- Less boilerplate

**Operations**:
- Stateless (horizontally scalable)
- No database complexity
- Docker-native
- FastAPI performance benefits

### What's Missing (vs WBIA)

❌ **Data Persistence**:
- No database layer (by design)
- No encounter tracking
- No name database
- No historical data

❌ **Additional Features**:
- No HotSpotter integration
- No query/matching logic (embeddings only)
- No annotation management
- No image set operations

❌ **Production Maturity**:
- Brand new (3 months old)
- No production deployments yet
- No migration guide
- Limited documentation vs WBIA

### New Architecture Pattern

**Old (Current)**:
```
Wildbook → WBIA (monolith) → WBIA Database → Results
                ↓
        Manages all data + ML
```

**New (Future)**:
```
Wildbook → ml-service (stateless) → ML Results
    ↓
Wildbook Database (owns all data)
```

**Key Change**: Wildbook becomes responsible for data persistence, ml-service only does inference.

## Migration Timeline

### Phase 1: Monitoring (Now - December 2024)

**Goal**: Track ml-service development and Wild Me's plans

**Actions**:
- [ ] Monitor ml-service commit activity
- [ ] Watch for Wildbook integration PRs
- [ ] Join Wild Me community discussions
- [ ] Contact Wild Me team about timeline
- [ ] Subscribe to ml-service releases

**Questions for Wild Me**:
1. When will Wildbook officially integrate ml-service?
2. What's the migration path from WBIA?
3. What features are still planned?
4. Is there a deprecation timeline for WBIA?
5. How does Wildbook handle persistence without WBIA's DB?

### Phase 2: Parallel Testing (January - March 2025)

**Goal**: Run ml-service alongside WBIA for evaluation

**Actions**:
- [ ] Add ml-service as submodule
- [ ] Create parallel docker-compose config
- [ ] Set up test environment
- [ ] Compare API responses
- [ ] Benchmark performance
- [ ] Test with real wildlife images
- [ ] Evaluate accuracy vs WBIA
- [ ] Document gaps and issues

**Success Criteria**:
- ml-service produces comparable detection results
- Classification accuracy matches or exceeds WBIA
- Performance is acceptable (< 2x WBIA latency)
- API is stable and well-documented

### Phase 3: Integration (April - June 2025)

**Goal**: Integrate ml-service into Wildbook stack

**Actions**:
- [ ] Update Wildbook to use ml-service APIs
- [ ] Migrate data persistence logic to Wildbook
- [ ] Update tests to cover ml-service
- [ ] Create fallback mechanism (if needed)
- [ ] Update documentation
- [ ] Train team on new architecture

**Deliverables**:
- Updated docker-compose with ml-service
- Modified Wildbook integration code
- Comprehensive test coverage
- Migration documentation

### Phase 4: Production Migration (July 2025+)

**Goal**: Replace WBIA with ml-service in production

**Actions**:
- [ ] Deploy to staging environment
- [ ] Run parallel deployment (WBIA + ml-service)
- [ ] Gradual traffic shift
- [ ] Monitor metrics and errors
- [ ] Full cutover when stable
- [ ] Deprecate WBIA

**Rollback Plan**:
- Keep WBIA images available
- Quick rollback via docker-compose
- Database backups before migration

## Parallel Testing Plan

### Step 1: Add ml-service Submodule

```bash
cd wildbook-infra

# Add ml-service as submodule
git submodule add https://github.com/WildMeOrg/ml-service.git ml-service

# Initialize
git submodule update --init --recursive

# Commit
git add .gitmodules ml-service
git commit -m "Add ml-service submodule for parallel testing"
```

### Step 2: Create Test Docker Compose

**File**: `docker-compose.ml-test.yml`

```yaml
version: '3.8'

# Parallel testing environment for ml-service
# Run with: docker-compose -f docker-compose.yml -f docker-compose.ml-test.yml up

services:
  # New: ml-service
  ml-service:
    build:
      context: ./ml-service
      dockerfile: docker/Dockerfile
    image: wildme/ml-service:${TAG:-latest}
    container_name: wildbook-ml-service
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ml-service-models:/models
      - ml-service-cache:/cache
    networks:
      - wildbook-net
    ports:
      - "8000:8000"  # Different port from WBIA
    environment:
      DEVICE: "cuda"
      HOST: "0.0.0.0"
      PORT: "8000"
      DB_DIR: "/cache"
    restart: unless-stopped

  # Existing: WBIA (keep for comparison)
  wbia:
    # ... existing config unchanged ...
    ports:
      - "5000:5000"

  # Test comparison service
  ml-comparison-tests:
    build:
      context: ./tests
      dockerfile: Dockerfile.ml-comparison
    container_name: wildbook-ml-comparison
    depends_on:
      - wbia
      - ml-service
    volumes:
      - ./tests/ml-comparison:/tests
      - ./tests/test_data:/test_data
      - ./tests/reports/ml-comparison:/reports
    networks:
      - wildbook-net
    environment:
      WBIA_URL: "http://wbia:5000"
      ML_SERVICE_URL: "http://ml-service:8000"
    profiles:
      - ml-test

volumes:
  ml-service-models:
    name: wildbook-ml-service-models
  ml-service-cache:
    name: wildbook-ml-service-cache
```

### Step 3: Create Comparison Tests

**File**: `tests/ml-comparison/compare_services.py`

```python
"""
Compare WBIA and ml-service responses
"""
import requests
import json
from pathlib import Path

WBIA_URL = "http://wbia:5000"
ML_SERVICE_URL = "http://ml-service:8000"

def compare_detection(image_path):
    """Compare detection results from both services"""

    # WBIA detection
    with open(image_path, 'rb') as f:
        wbia_response = requests.post(
            f"{WBIA_URL}/api/upload/image/",
            files={'image': f}
        )
    wbia_gid = wbia_response.json()['gid']

    wbia_detect = requests.post(
        f"{WBIA_URL}/api/engine/detect/cnn/",
        json={'gid_list': [wbia_gid]}
    )

    # ml-service detection
    with open(image_path, 'rb') as f:
        ml_response = requests.post(
            f"{ML_SERVICE_URL}/predict",
            files={'file': f},
            data={'model_id': 'yolov5x'}
        )

    # Compare results
    wbia_boxes = wbia_detect.json()['annotations']
    ml_boxes = ml_response.json()['predictions']

    return {
        'image': image_path.name,
        'wbia_count': len(wbia_boxes),
        'ml_service_count': len(ml_boxes),
        'wbia_boxes': wbia_boxes,
        'ml_boxes': ml_boxes
    }

def compare_pipeline(image_path):
    """Compare full pipeline results"""

    # ml-service pipeline
    with open(image_path, 'rb') as f:
        ml_pipeline = requests.post(
            f"{ML_SERVICE_URL}/pipeline",
            files={'file': f},
            data={
                'predict_model_id': 'yolov5x',
                'classify_model_id': 'efficientnet',
                'extract_model_id': 'miewid'
            }
        )

    # WBIA pipeline (would need to chain multiple calls)
    # ... implement WBIA pipeline equivalent ...

    return ml_pipeline.json()

if __name__ == '__main__':
    test_images = Path('/test_data/images').glob('*.jpg')

    results = []
    for image in test_images:
        result = compare_detection(image)
        results.append(result)
        print(f"Tested {image.name}: WBIA={result['wbia_count']}, ml-service={result['ml_service_count']}")

    # Save results
    with open('/reports/comparison_results.json', 'w') as f:
        json.dump(results, f, indent=2)
```

### Step 4: Run Comparison Tests

```bash
# Start both services
docker-compose -f docker-compose.yml -f docker-compose.ml-test.yml up -d

# Wait for services to be ready
docker-compose ps

# Run comparison tests
docker-compose -f docker-compose.yml -f docker-compose.ml-test.yml \
  --profile ml-test run --rm ml-comparison-tests python compare_services.py

# View results
cat tests/reports/ml-comparison/comparison_results.json

# Stop test environment
docker-compose -f docker-compose.yml -f docker-compose.ml-test.yml down
```

### Step 5: Evaluate Results

**Metrics to Compare**:

1. **Detection Accuracy**
   - Bounding box precision
   - Number of false positives/negatives
   - Confidence scores

2. **Classification Accuracy**
   - Species identification correctness
   - Confidence distributions

3. **Performance**
   - Response times
   - Memory usage
   - GPU utilization

4. **API Quality**
   - Ease of use
   - Documentation completeness
   - Error handling

**Decision Criteria**:
- ✅ Proceed if ml-service >= 95% WBIA accuracy
- ✅ Proceed if ml-service latency < 2x WBIA
- ✅ Proceed if ml-service API is stable
- ⚠️  Wait if major features missing
- ❌ Abort if accuracy significantly worse

## Risks and Mitigations

### Risk 1: ml-service Not Production Ready

**Likelihood**: Medium
**Impact**: High

**Mitigation**:
- Keep WBIA as fallback
- Gradual migration with rollback plan
- Extensive testing before production

### Risk 2: Missing Features

**Likelihood**: High
**Impact**: Medium

**Mitigation**:
- Document required features upfront
- Engage with Wild Me team early
- Consider contributing features

### Risk 3: Performance Degradation

**Likelihood**: Low
**Impact**: Medium

**Mitigation**:
- Comprehensive benchmarking
- Load testing before migration
- Performance monitoring in production

### Risk 4: Integration Complexity

**Likelihood**: Medium
**Impact**: Medium

**Mitigation**:
- Start with parallel deployment
- Maintain API compatibility layer
- Phased migration approach

## Success Metrics

### Technical Metrics
- [ ] ml-service detection accuracy >= 95% of WBIA
- [ ] Response time < 2x WBIA baseline
- [ ] Zero critical bugs in 1 month testing
- [ ] All functional tests pass
- [ ] Documentation complete

### Business Metrics
- [ ] Reduced infrastructure complexity
- [ ] Easier to maintain
- [ ] Faster feature development
- [ ] Better developer experience
- [ ] Cost savings (if any)

## Communication Plan

### Internal Team
- Monthly updates on ml-service progress
- Quarterly decision points
- Test results shared weekly during testing phase

### Wild Me Team
- Reach out Q4 2024 for roadmap discussion
- Monthly check-ins during testing phase
- Share feedback and issues
- Contribute to documentation

## Resources

### Documentation
- ml-service README: https://github.com/WildMeOrg/ml-service/blob/main/README.md
- WBIA Docs: https://wildmeorg.github.io/wildbook-ia/

### Contacts
- Wild Me GitHub: https://github.com/WildMeOrg
- Community Forum: https://community.wildbook.org
- Email: dev@wildme.org

### Key Commits
- Pipeline Feature: https://github.com/WildMeOrg/ml-service/commit/32cd5f1673c357661fde9b3f7d23023a1cdb9388
- Repository: https://github.com/WildMeOrg/ml-service

## Next Steps

### Immediate (This Week)
1. [ ] Contact Wild Me about ml-service timeline
2. [ ] Add ml-service as submodule
3. [ ] Create comparison test framework
4. [ ] Document current WBIA API usage in Wildbook

### Short Term (Next Month)
1. [ ] Set up parallel testing environment
2. [ ] Run initial accuracy comparisons
3. [ ] Benchmark performance
4. [ ] Identify feature gaps

### Medium Term (Q1 2025)
1. [ ] Regular testing with production data
2. [ ] Contribute to ml-service if needed
3. [ ] Plan Wildbook integration changes
4. [ ] Update architecture documentation

## Appendix: API Comparison

### Detection Endpoint

**WBIA**:
```bash
POST /api/engine/detect/cnn/
{
  "gid_list": [1, 2, 3]
}
```

**ml-service**:
```bash
POST /predict
{
  "image_uri": "http://example.com/image.jpg",
  "model_id": "yolov5x"
}
```

### Pipeline Endpoint

**WBIA**: Multiple chained calls required
```bash
1. Upload image
2. Detect annotations
3. Extract features
4. Classify species
```

**ml-service**: Single pipeline call
```bash
POST /pipeline
{
  "image_uri": "http://example.com/image.jpg",
  "predict_model_id": "yolov5x",
  "classify_model_id": "efficientnet",
  "extract_model_id": "miewid"
}
```

---

**Document Owner**: Infrastructure Team
**Last Updated**: September 30, 2024
**Next Review**: December 31, 2024