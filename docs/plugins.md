# WBIA Plugin System

**Date**: September 30, 2024
**Status**: Reference Documentation
**Target Audience**: Developers, ML Engineers

## Overview

WBIA (Wildbook Image Analysis) uses a plugin architecture to extend its machine learning capabilities. Plugins provide specialized algorithms for detection, identification, and classification of different species.

**Key Concepts**:
- **Plugins are Python packages** - Distributed via PyPI or GitHub
- **Auto-registration** - Plugins register methods on the WBIA controller
- **REST API exposure** - Plugin methods automatically available via API
- **Species-specific** - Different algorithms optimized for different animals

---

## Available Plugins

### Primary Maintainers

WBIA plugins are maintained by two primary organizations:
- **WildMeOrg** - Original Wild Me organization
- **Tech-4-Conservation** - Active fork with continued development

Some plugins exist in both organizations, with Tech-4-Conservation often having more recent updates.

### Official Wild Me Plugins

| Plugin | Repository | Purpose | Species | Status |
|--------|-----------|---------|---------|--------|
| **wbia-plugin-cnn** | [WildMeOrg/wbia-plugin-cnn](https://github.com/WildMeOrg/wbia-plugin-cnn) | Detection & classification using CNNs | Multi-species | Active |
| **wbia-plugin-pie** | [WildMeOrg/wbia-plugin-pie](https://github.com/WildMeOrg/wbia-plugin-pie) | Pose-Invariant Embeddings for ID | Multi-species | Active |
| **wbia-plugin-pie-v2** | [WildMeOrg/wbia-plugin-pie-v2](https://github.com/WildMeOrg/wbia-plugin-pie-v2) | PIE v2 with improved accuracy | Multi-species | Active |
| **wbia-plugin-miew-id** | [WildMeOrg/wbia-plugin-miew-id](https://github.com/WildMeOrg/wbia-plugin-miew-id) | MiewID individual identification | Multi-species | Active |
| **wbia-plugin-flukematch** | [WildMeOrg/wbia-plugin-flukematch](https://github.com/WildMeOrg/wbia-plugin-flukematch) | Whale fluke matching | Whales | Active |
| **wbia-plugin-curvrank** | [WildMeOrg/wbia-plugin-curvrank](https://github.com/WildMeOrg/wbia-plugin-curvrank) | Dolphin dorsal fin ranking | Dolphins | Active |
| **wbia-plugin-finfindr** | [WildMeOrg/wbia-plugin-finfindr](https://github.com/WildMeOrg/wbia-plugin-finfindr) | Fin detection and identification | Sharks, Rays | Active |
| **wbia-plugin-deepsense** | [WildMeOrg/wbia-plugin-deepsense](https://github.com/WildMeOrg/wbia-plugin-deepsense) | Right whale callosity identification | Right Whales | Active |
| **wbia-plugin-kaggle7** | [WildMeOrg/wbia-plugin-kaggle7](https://github.com/WildMeOrg/wbia-plugin-kaggle7) | Humpback whale fluke ID | Humpback Whales | Active |
| **wbia-plugin-lca** | [WildMeOrg/wbia-plugin-lca](https://github.com/WildMeOrg/wbia-plugin-lca) | Lynx Cheetah Analysis | Big Cats | Active |
| **wbia-plugin-whaleridgefindr** | [WildMeOrg/wbia-plugin-whaleridgefindr](https://github.com/WildMeOrg/wbia-plugin-whaleridgefindr) | Whale ridge detection | Whales | Active |

### Utility Plugins

| Plugin | Repository | Purpose | Status |
|--------|-----------|---------|--------|
| **wbia-plugin-orientation** | [WildMeOrg/wbia-plugin-orientation](https://github.com/WildMeOrg/wbia-plugin-orientation) | Image orientation correction | Active |
| **wbia-plugin-2d-orientation** | [WildMeOrg/wbia-plugin-2d-orientation](https://github.com/WildMeOrg/wbia-plugin-2d-orientation) | 2D orientation estimation | Active |
| **wbia-plugin-segmentation** | [WildMeOrg/wbia-plugin-segmentation](https://github.com/WildMeOrg/wbia-plugin-segmentation) | Image segmentation | Active |
| **wbia-plugin-blend** | [WildMeOrg/wbia-plugin-blend](https://github.com/WildMeOrg/wbia-plugin-blend) | Model blending/ensemble | Active |

### Development & Templates

| Plugin | Repository | Purpose |
|--------|-----------|---------|
| **wbia-plugin-template** | [WildMeOrg/wbia-plugin-template](https://github.com/WildMeOrg/wbia-plugin-template) | Template for creating new plugins |
| **wbia-plugin-id-example** | [WildMeOrg/wbia-plugin-id-example](https://github.com/WildMeOrg/wbia-plugin-id-example) | Example identification plugin |
| **wbia-plugin-tbd** | [WildMeOrg/wbia-plugin-tbd](https://github.com/WildMeOrg/wbia-plugin-tbd) | Placeholder/experimental |

### Tech-4-Conservation Plugins

Many plugins also maintained by [Tech-4-Conservation](https://github.com/Tech-4-Conservation):

| Plugin | Repository | Notes |
|--------|-----------|-------|
| **wbia-plugin-cnn** | [Tech-4-Conservation/wbia-plugin-cnn](https://github.com/Tech-4-Conservation/wbia-plugin-cnn) | Fork with updates |
| **wbia-plugin-miew-id** | [Tech-4-Conservation/wbia-plugin-miew-id](https://github.com/Tech-4-Conservation/wbia-plugin-miew-id) | Active development |
| **wbia-plugin-pie-v2** | [Tech-4-Conservation/wbia-plugin-pie-v2](https://github.com/Tech-4-Conservation/wbia-plugin-pie-v2) | Active development |
| **wbia-plugin-orientation** | [Tech-4-Conservation/wbia-plugin-orientation](https://github.com/Tech-4-Conservation/wbia-plugin-orientation) | Fork with updates |
| **wbia-plugin-2d-orientation** | [Tech-4-Conservation/wbia-plugin-2d-orientation](https://github.com/Tech-4-Conservation/wbia-plugin-2d-orientation) | 2D orientation wrapper |
| **wbia-plugin-segmentation** | [Tech-4-Conservation/wbia-plugin-segmentation](https://github.com/Tech-4-Conservation/wbia-plugin-segmentation) | Instance segmentation |
| **ArgusWild-wbia** | [Tech-4-Conservation/ArgusWild-wbia](https://github.com/Tech-4-Conservation/ArgusWild-wbia) | Backend for ArgusWild |

### Key Contributors

Several individuals have made significant contributions to the WBIA ecosystem:

**Top Contributors to wildbook-ia**:
- **@Erotemic** (Jon Crall) - 5,448 commits - Core WBIA architecture
- **@bluemellophone** (Jason Parham, Ph.D., Kitware) - 3,040 commits - Most plugin development
- **@mmulich** - 410 commits
- **@hjweide** - 126 commits - CurvRank algorithm

**Notable Plugin Developer**: @bluemellophone maintains nearly all official plugins and has created comprehensive implementations including:
- All detection/classification plugins
- All identification plugins
- Plugin template and examples
- Build infrastructure (wbia-pypkg-build)

### Community Plugins

Community-contributed implementations and forks:

| Plugin/Project | Repository | Contributor | Notes |
|----------------|-----------|-------------|-------|
| **wbia-plugin-pie-v2** | [olgamoskvyak/wbia-plugin-pie-v2](https://github.com/olgamoskvyak/wbia-plugin-pie-v2) | @olgamoskvyak | 8 forks, active use |
| **wildlife-embeddings** | [alright-code/wildlife-embeddings](https://github.com/alright-code/wildlife-embeddings) | @alright-code | PyTorch Lightning reimplementation of PIE v2 |
| **wbia-plugin-finfindr** | [M-E-E-R-e-V/wbia-plugin-finfindr](https://github.com/M-E-E-R-e-V/wbia-plugin-finfindr) | @M-E-E-R-e-V | Shark/ray fin identification |
| **wbia-plugin-flukematch** | [M-E-E-R-e-V/wbia-plugin-flukematch](https://github.com/M-E-E-R-e-V/wbia-plugin-flukematch) | @M-E-E-R-e-V | Whale fluke matching |

---

## Installing Plugins

### From PyPI

```bash
# Install via pip
pip install wbia-plugin-cnn
pip install wbia-plugin-pie
pip install wbia-plugin-miew-id
```

### From GitHub (Development)

```bash
# Clone and install in development mode
git clone https://github.com/WildMeOrg/wbia-plugin-cnn.git
cd wbia-plugin-cnn
pip install -e .
```

### In Docker

Add to `wildbook-ia/Dockerfile`:

```dockerfile
# Install plugins
RUN pip install --no-cache-dir \
    wbia-plugin-cnn \
    wbia-plugin-pie \
    wbia-plugin-miew-id \
    wbia-plugin-flukematch
```

Or install at runtime:

```bash
docker-compose exec wbia pip install wbia-plugin-cnn
docker-compose restart wbia
```

---

## Using Plugins

### Python API

```python
import wbia

# Open database
ibs = wbia.opendb('testdb1')

# Upload image
gid = ibs.add_images(['zebra.jpg'])[0]

# Run detection (if plugin installed)
aid_list = ibs.detect_cnn_yolo_v2([gid])

# Extract embeddings (if PIE plugin installed)
embeddings = ibs.pie_embedding(aid_list)

# Query for matches
results = ibs.pie_predict_light(aid_list, aid_list)
```

### REST API

```bash
# Detection endpoint (wbia-plugin-cnn)
curl -X POST http://localhost:5000/api/plugin/cnn/detect/ \
  -H "Content-Type: application/json" \
  -d '{"gid_list": [1, 2, 3]}'

# PIE embedding extraction
curl -X POST http://localhost:5000/api/plugin/pie/embedding/ \
  -H "Content-Type: application/json" \
  -d '{"aid_list": [1, 2, 3]}'

# MiewID identification
curl -X POST http://localhost:5000/api/plugin/miewid/predict/ \
  -H "Content-Type: application/json" \
  -d '{"aid_list": [1, 2, 3]}'
```

### Check Installed Plugins

```python
import wbia

ibs = wbia.opendb('testdb1')

# List all available methods
methods = [m for m in dir(ibs) if not m.startswith('_')]
plugin_methods = [m for m in methods if 'plugin' in m or 'pie' in m or 'cnn' in m]

print(plugin_methods)
```

---

## Creating a Plugin

### Quick Start

```bash
# Clone template
git clone https://github.com/WildMeOrg/wbia-plugin-template.git
mv wbia-plugin-template wbia-plugin-mymodel
cd wbia-plugin-mymodel

# Update plugin name
# Edit setup.py, README, and wbia_mymodel/_plugin.py
```

### Plugin Structure

```
wbia-plugin-mymodel/
├── setup.py                    # Package configuration
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
├── wbia_mymodel/              # Main package (underscore!)
│   ├── __init__.py
│   ├── _plugin.py             # Plugin registration (required!)
│   ├── models.py              # Model implementations
│   └── utils.py               # Helper functions
└── tests/                     # Test suite
    └── test_plugin.py
```

### Minimal Plugin Example

**File: `wbia_mymodel/_plugin.py`**

```python
import wbia
from wbia.control import controller_inject
import utool as ut

# Class to hold plugin methods
CLASS_INJECT_KEY, register_ibs_method = controller_inject.make_ibs_register_decorator(__name__)

# Register as preproc (cached computation)
@register_ibs_method
@register_preprocs(
    tablename='MyModel',
    parents=['annotations'],
    colnames=['embedding'],
    coltypes=[np.ndarray],
    configclass=None,
    fname='mymodel',
    chunksize=128,
)
def compute_mymodel_embedding(ibs, aid_list, config=None):
    """
    Compute embeddings using MyModel.

    Args:
        ibs: IBEISController instance
        aid_list: List of annotation IDs
        config: Configuration (optional)

    Returns:
        List of embedding vectors
    """
    # Get annotation images
    chip_paths = ibs.get_annot_chip_fpath(aid_list)

    # Load model
    model = load_mymodel()

    # Run inference
    embeddings = []
    for chip_path in chip_paths:
        embedding = model.extract_features(chip_path)
        embeddings.append(embedding)

    return embeddings


# Register as API endpoint
@register_ibs_method
@register_api('/api/plugin/mymodel/embedding/', methods=['POST'])
def mymodel_embedding_api(ibs, aid_list=None, **kwargs):
    """
    RESTful API endpoint for MyModel embeddings.

    POST /api/plugin/mymodel/embedding/
    Body: {"aid_list": [1, 2, 3]}
    """
    embeddings = ibs.compute_mymodel_embedding(aid_list)
    return {
        'embeddings': [e.tolist() for e in embeddings],
        'success': True,
    }


# Register identification/matching method
@register_ibs_method
def mymodel_identify(ibs, qaid_list, daid_list=None, config=None):
    """
    Identify individuals using MyModel.

    Args:
        qaid_list: Query annotation IDs
        daid_list: Database annotation IDs (optional)
        config: Configuration (optional)

    Returns:
        List of match results for each query
    """
    if daid_list is None:
        daid_list = ibs.get_valid_aids()

    # Get embeddings
    query_embeddings = ibs.compute_mymodel_embedding(qaid_list)
    db_embeddings = ibs.compute_mymodel_embedding(daid_list)

    # Compute similarity scores
    results = []
    for qemb in query_embeddings:
        scores = compute_similarity(qemb, db_embeddings)
        ranked = rank_results(scores, daid_list)
        results.append(ranked)

    return results
```

**File: `setup.py`**

```python
from setuptools import setup, find_packages

setup(
    name='wbia-plugin-mymodel',
    version='1.0.0',
    description='WBIA Plugin: MyModel for animal identification',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/wbia-plugin-mymodel',
    license='Apache License 2.0',
    packages=find_packages(),
    install_requires=[
        'wbia',
        'numpy',
        'torch>=1.9.0',
        'torchvision>=0.10.0',
    ],
    python_requires='>=3.7',
    keywords='wbia wildlife identification conservation',
)
```

---

## Plugin Best Practices

### 1. Naming Conventions

```
Repository:  wbia-plugin-mymodel
Package:     wbia_mymodel (underscore!)
Module:      wbia_mymodel._plugin (must exist!)
```

### 2. Registration Patterns

**Simple method registration**:
```python
@register_ibs_method
def my_function(ibs, ...):
    """My function."""
    pass
```

**With API endpoint**:
```python
@register_ibs_method
@register_api('/api/plugin/mymodel/method/', methods=['POST'])
def my_api_method(ibs, param1=None, **kwargs):
    """API method with automatic endpoint."""
    return {'result': ...}
```

**With caching (preproc)**:
```python
@register_ibs_method
@register_preprocs(
    tablename='MyCache',
    parents=['annotations'],
    colnames=['result'],
    coltypes=[np.ndarray],
)
def compute_expensive_thing(ibs, aid_list, config=None):
    """Cached computation."""
    # Results automatically cached in database
    return results
```

### 3. Configuration

```python
from wbia.dtool import Config

class MyModelConfig(Config):
    """Configuration for MyModel."""
    _param_info_list = [
        ut.ParamInfo('threshold', 0.8, 'confidence threshold'),
        ut.ParamInfo('model_type', 'resnet50', 'model architecture'),
    ]

@register_ibs_method
def mymodel_identify(ibs, aid_list, config=None):
    if config is None:
        config = MyModelConfig()
    # Use config.threshold, config.model_type
    pass
```

### 4. Model Management

```python
import os
from pathlib import Path

def get_model_path():
    """Get path to model files."""
    # Models stored in WBIA cache directory
    cache_dir = Path.home() / '.cache' / 'wbia' / 'mymodel'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def load_model():
    """Load model (with lazy loading)."""
    global _MODEL
    if _MODEL is None:
        model_path = get_model_path() / 'model.pth'
        if not model_path.exists():
            download_model(model_path)
        _MODEL = torch.load(model_path)
    return _MODEL
```

### 5. Error Handling

```python
@register_ibs_method
def mymodel_identify(ibs, aid_list):
    try:
        model = load_model()
    except FileNotFoundError:
        raise Exception(
            'MyModel not found. Download with: '
            'python -m wbia_mymodel.download_models'
        )

    try:
        return model.predict(aid_list)
    except Exception as e:
        logger.error(f'MyModel prediction failed: {e}')
        return None  # Graceful degradation
```

### 6. Testing

```python
# tests/test_plugin.py
import wbia
import wbia_mymodel._plugin  # Import to register

def test_mymodel_embedding():
    """Test embedding extraction."""
    ibs = wbia.opendb('testdb1')

    # Get test annotations
    aid_list = ibs.get_valid_aids()[:5]

    # Test embedding
    embeddings = ibs.compute_mymodel_embedding(aid_list)

    assert len(embeddings) == len(aid_list)
    assert all(isinstance(e, np.ndarray) for e in embeddings)

def test_mymodel_api(wbia_client):
    """Test REST API endpoint."""
    response = wbia_client.post(
        '/api/plugin/mymodel/embedding/',
        json={'aid_list': [1, 2, 3]}
    )
    assert response.status_code == 200
    assert 'embeddings' in response.json
```

---

## Plugin Discovery

### Automatic Loading

WBIA can automatically load plugins if they follow the naming convention:

```python
# In wbia/control/IBEISControl.py
AUTOLOAD_PLUGIN_MODNAMES = [
    'wbia_cnn._plugin',
    'wbia_pie._plugin',
    'wbia_miewid._plugin',
]
```

### Manual Loading

```python
import wbia
import wbia_mymodel._plugin  # Import to register methods

ibs = wbia.opendb('testdb1')
# Now mymodel methods are available on ibs
```

### Plugin Flags

```bash
# Start WBIA with specific plugins
python -m wbia --db testdb1 --mymodel --flukematch

# Disable plugins
python -m wbia --db testdb1 --no-cnn --no-pie
```

---

## Publishing a Plugin

### 1. Prepare Repository

```bash
# Structure
wbia-plugin-mymodel/
├── .github/
│   └── workflows/
│       └── test.yml          # CI/CD
├── wbia_mymodel/
│   ├── __init__.py
│   ├── _plugin.py
│   └── ...
├── tests/
├── setup.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

### 2. Add Tests & CI

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: pip install -e .[dev]
      - run: pytest
```

### 3. Publish to PyPI

```bash
# Build package
python setup.py sdist bdist_wheel

# Test with TestPyPI first
twine upload --repository testpypi dist/*

# Publish to PyPI
twine upload dist/*
```

### 4. Register with Wild Me

Contact Wild Me team to:
- Add to official plugin list
- Include in Docker images
- Add to documentation

---

## Plugin Ecosystem

### Which Repository to Use?

When choosing a plugin, consider:

1. **Check Tech-4-Conservation first** - Often has more recent updates
2. **Fall back to WildMeOrg** - Original source, stable releases
3. **Community plugins** - Experimental or specialized use cases

**Installation tip**: You can install from specific repos:
```bash
# From Tech-4-Conservation
pip install git+https://github.com/Tech-4-Conservation/wbia-plugin-cnn.git

# From WildMeOrg
pip install git+https://github.com/WildMeOrg/wbia-plugin-cnn.git

# From PyPI (may be outdated)
pip install wbia-plugin-cnn
```

## Community Plugins

Anyone can create WBIA plugins! If you develop a plugin:

1. **Name it** `wbia-plugin-yourname`
2. **Open source** on GitHub
3. **Add tests** and documentation
4. **Share** on Wild Me community forum
5. **Consider contributing** to WildMeOrg

### Finding Community Plugins

Search GitHub for `wbia-plugin-*`:
```bash
# Search public repos
gh search repos wbia-plugin --limit 50
```

---

## Plugin Development Workflow

### 1. Start from Template

```bash
git clone https://github.com/WildMeOrg/wbia-plugin-template.git my-plugin
cd my-plugin
```

### 2. Rename Everything

```bash
# Update package name
mv wbia_template wbia_mymodel

# Update setup.py
sed -i 's/template/mymodel/g' setup.py

# Update imports in _plugin.py
```

### 3. Implement Your Algorithm

```python
# wbia_mymodel/_plugin.py
# Add your detection/identification logic
```

### 4. Add Tests

```python
# tests/test_plugin.py
def test_my_algorithm():
    # Test with testdb1
    pass
```

### 5. Test Locally

```bash
# Install in development mode
pip install -e .

# Test manually
python -c "import wbia; import wbia_mymodel._plugin; ibs = wbia.opendb('testdb1')"

# Run tests
pytest
```

### 6. Document

```markdown
# README.md
## Installation
pip install wbia-plugin-mymodel

## Usage
```python
import wbia
ibs = wbia.opendb('mydb')
results = ibs.mymodel_identify([1, 2, 3])
`` `
```

---

## Advanced Topics

### Plugin Dependencies

```python
# setup.py
setup(
    install_requires=[
        'wbia',
        'wbia-plugin-cnn',  # Depend on another plugin
        'torch>=1.9.0',
    ]
)
```

### Multi-Model Plugins

```python
@register_ibs_method
def mymodel_identify(ibs, aid_list, model='v1', **kwargs):
    """Support multiple model versions."""
    if model == 'v1':
        return identify_v1(ibs, aid_list)
    elif model == 'v2':
        return identify_v2(ibs, aid_list)
    else:
        raise ValueError(f'Unknown model: {model}')
```

### GPU Support

```python
import torch

def get_device():
    """Get compute device (GPU if available)."""
    return torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def load_model():
    """Load model on appropriate device."""
    device = get_device()
    model = MyModel().to(device)
    return model
```

### Batch Processing

```python
@register_ibs_method
def mymodel_identify_batch(ibs, aid_list, batch_size=32):
    """Process in batches for efficiency."""
    results = []
    for i in range(0, len(aid_list), batch_size):
        batch = aid_list[i:i + batch_size]
        batch_results = process_batch(ibs, batch)
        results.extend(batch_results)
    return results
```

---

## Troubleshooting

### Plugin Not Loading

```python
# Check if plugin installed
import pkg_resources
print([p.project_name for p in pkg_resources.working_set if 'wbia' in p.project_name])

# Manually import
import wbia_mymodel._plugin

# Check registration
import wbia
ibs = wbia.opendb('testdb1')
print('mymodel_identify' in dir(ibs))
```

### API Endpoint Not Found

```python
# Check registered endpoints
import wbia
ibs = wbia.opendb('testdb1')
from wbia.web.app import app
print([rule.rule for rule in app.url_map.iter_rules() if 'mymodel' in rule.rule])
```

### Model Download Issues

```python
# Download models separately
python -m wbia_mymodel.download_models

# Or set environment variable for model cache
export WBIA_CACHE_DIR=/path/to/cache
```

---

## Resources

- **Plugin Template**: https://github.com/WildMeOrg/wbia-plugin-template
- **Example Plugins**: Browse [WildMeOrg](https://github.com/WildMeOrg?q=wbia-plugin)
- **Architecture Doc**: See `wildbook-ia/Architecture.md` for plugin system details
- **Community Forum**: https://community.wildbook.org
- **Developer Chat**: Request Slack invite from dev@wildme.org

---

**Document Owner**: Plugin Development Team
**Last Updated**: September 30, 2024
**Next Review**: December 31, 2024