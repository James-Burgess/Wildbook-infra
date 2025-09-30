# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is **wildbook-infra**, a multi-repository workspace containing the Wildbook Image Analysis (WBIA) platform and its dependencies. The project uses git submodules to manage multiple interrelated Python packages for wildlife identification and conservation.

## Repository Structure

```
wildbook-infra/
├── wildbook-ia/          # Main WBIA application (Flask web server, ML pipeline)
├── wbia-utool/           # Utility toolkit (method injection, caching, helpers)
├── wbia-vtool/           # Computer vision toolkit (SIFT, OpenCV wrappers)
├── wbia-tpl-pyhesaff/    # Hessian-Affine keypoint detector
├── wbia-tpl-pydarknet/   # YOLO/Darknet detection wrapper
├── wbia-tpl-pyflann/     # FLANN approximate nearest neighbor
├── wbia-tpl-pyrf/        # Random forest detector
└── wildbook/             # Wildbook platform integration
```

Each directory is a git submodule pointing to its own repository under the WildMeOrg organization.

## Development Workflow

### Initial Setup

```bash
# Clone with submodules
git clone --recursive https://github.com/WildMeOrg/wildbook-infra.git

# Or initialize submodules after cloning
git submodule update --init --recursive

# Create virtual environment (recommended Python 3.7-3.12)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Installing Components

Install in development mode from the root directory:

```bash
# Install dependencies in order (important!)
pip install -e ./wbia-utool
pip install -e ./wbia-vtool
pip install -e ./wbia-tpl-pyhesaff
pip install -e ./wbia-tpl-pydarknet
pip install -e ./wbia-tpl-pyflann
pip install -e ./wbia-tpl-pyrf

# Install main application
pip install -e ./wildbook-ia
```

### Running the Application

```bash
# Command-line interface
python -m wbia

# Start with test database
python -m wbia --db testdb1

# Start web server
python -m wbia --web --port 5000

# Start with specific plugins
python -m wbia --web --cnn --finfindr

# Disable plugins
python -m wbia --web --no-cnn
```

### Testing

Testing is done per-submodule. Navigate to the specific submodule directory first.

```bash
# Run all tests (from wildbook-ia directory)
cd wildbook-ia
pytest

# Run specific test module
pytest wbia/tests/test_annots.py

# Run with web tests
pytest --web-tests

# Run doctests
pytest --xdoctest

# Run tests against PostgreSQL
pytest --with-postgres-uri="postgresql://user:pass@localhost/testdb"
```

### Code Quality

From the wildbook-ia directory:

```bash
# Format code with Brunette (Black fork)
brunette --config=setup.cfg .

# Sort imports
isort --settings-path setup.cfg .

# Lint code
flake8

# Run all pre-commit hooks
pre-commit run --all-files
```

## Architecture Overview

### WBIA Core Architecture

WBIA uses a **controller-based architecture** with **dynamic method injection**:

1. **IBEISController** (`wildbook-ia/wbia/control/IBEISControl.py`)
   - Central hub for all operations
   - Methods are injected from plugins at runtime via `utool`
   - All functionality accessed through this controller object

2. **Plugin System** (utool-based injection)
   - Plugins use `@register_ibs_method` decorator to inject methods into controller
   - Internal plugins auto-load from `wbia/control/`, `wbia/web/`, `wbia/other/`
   - External plugins (e.g., `wbia-plugin-cnn`) load conditionally via CLI flags

3. **Dual Database Architecture**
   - Main DB: SQLite/PostgreSQL for core entities (images, annotations, names)
   - Cache DB: Computed properties (chips, features, ML outputs) via DependencyCache

4. **Web Layer**
   - Flask application with REST API
   - Tornado WSGI server
   - Plugins can register both controller methods AND Flask routes

### Key Components

**wildbook-ia** (main application):
- `wbia/control/` - Controller and plugin registration
- `wbia/dtool/` - Database and caching infrastructure
- `wbia/algo/` - ML algorithms (HotSpotter, detection, graph algorithms)
- `wbia/web/` - Flask app, API endpoints, web routes
- `wbia/core_annots.py`, `wbia/core_images.py` - Object-oriented data interfaces

**wbia-utool** (utility toolkit):
- Method injection framework (`@register_ibs_method`)
- Caching utilities
- Filesystem and path helpers
- Meta-programming tools

**wbia-vtool** (computer vision):
- SIFT feature extraction
- Image transformation utilities
- OpenCV wrappers
- Geometry and spatial hash operations

## Development Patterns

### Adding a New Controller Method

```python
# In wildbook-ia/wbia/control/manual_*.py
from wbia.control import controller_inject

CLASS_INJECT_KEY, register_ibs_method = \
    controller_inject.make_ibs_register_decorator(__name__)

@register_ibs_method
def get_custom_property(ibs, aid_list):
    """Get custom property for annotations"""
    # Implementation
    return results
```

Register module in `wildbook-ia/wbia/control/IBEISControl.py`:
```python
AUTOLOAD_PLUGIN_MODNAMES = [
    # ... existing modules ...
    'wbia.control.manual_custom',
]
```

### Adding a Web API Endpoint

```python
# In wildbook-ia/wbia/web/apis_*.py
from wbia.control import controller_inject

CLASS_INJECT_KEY, register_ibs_method = \
    controller_inject.make_ibs_register_decorator(__name__)
register_api = controller_inject.get_wbia_flask_api(__name__)

@register_ibs_method
@register_api('/api/custom/endpoint/', methods=['GET'])
def api_custom_endpoint(ibs, param_list=None, **kwargs):
    """RESTful endpoint: GET /api/custom/endpoint/?param_list=[1,2,3]"""
    results = ibs.get_custom_property(param_list)
    return {'results': results}
```

### Working with Dependency Cache

```python
# In wildbook-ia/wbia/core_annots.py
from wbia.control.controller_inject import register_preprocs
from wbia import dtool

derived_attribute = register_preprocs['annot']

class CustomConfig(dtool.Config):
    def get_param_info_list(self):
        return [
            ut.ParamInfo('param1', 'default'),
        ]

@derived_attribute(
    tablename='custom_property',
    parents=['annotations'],
    colnames=['result', 'confidence'],
    coltypes=[str, float],
    configclass=CustomConfig,
    fname='custom',
)
def compute_custom_property(depc, aid_list, config=None):
    """Compute and cache expensive property"""
    ibs = depc.controller
    for aid in aid_list:
        result = expensive_computation(ibs, aid, config)
        yield result
```

## Submodule Management

### Updating Submodules

```bash
# Update all submodules to latest
git submodule update --remote --merge

# Update specific submodule
cd wildbook-ia
git pull origin main
cd ..
git add wildbook-ia
git commit -m "Update wildbook-ia submodule"

# Pull latest changes including submodule updates
git pull
git submodule update --init --recursive
```

### Working on Submodule Changes

```bash
# Make changes in a submodule
cd wildbook-ia
git checkout -b feature-branch
# ... make changes ...
git commit -m "Add feature"
git push origin feature-branch

# Update parent repo to point to new commit
cd ..
git add wildbook-ia
git commit -m "Update wildbook-ia to feature-branch"
```

## Docker Deployment

```bash
# Build from wildbook-ia/devops/
cd wildbook-ia/devops
./build.sh wbia-base wbia-provision wbia

# Or use Docker directly
docker build -t wildbook-ia wildbook-ia/

# Run container
docker run -p 5000:5000 -v /data:/data/db wildbook-ia

# Use published image
docker pull wildme/wbia:latest
docker run -p 84:5000 wildme/wbia:latest
```

## Important Notes

- Python 3.7+ required (migrating to 3.12)
- Uses scikit-build, CMake for C++ extensions in vtool/pyhesaff/pydarknet
- Method injection happens at import time - order matters
- Test database `testdb1` is commonly used for development
- PostgreSQL recommended for production; SQLite for development
- Plugin loading controlled by CLI flags (`--no-cnn`, `--finfindr`, etc.)

## Common Tasks

**Initialize test database:**
```bash
python -m wbia.cli.testdbs
```

**Run single test:**
```bash
cd wildbook-ia
pytest -xvs wbia/tests/test_annots.py::test_function_name
```

**Build documentation:**
```bash
cd wildbook-ia
./build_documentation.sh
# Output: docs/build/html/index.html
```

**Clean build artifacts:**
```bash
cd wildbook-ia
./clean.sh
```

## Python Style

- Follow PEP8 with specific exceptions (see wildbook-ia/setup.cfg)
- Use Brunette (Black fork) for formatting: line length 90, single quotes
- Use isort with black profile for imports
- Google-style docstrings with xdoctest support
- Variable naming: snake_case (not enforced via linting)

## References

- Main repo: https://github.com/WildMeOrg/wildbook-ia
- Documentation: https://wildmeorg.github.io/wildbook-ia/
- Organization: https://github.com/WildMeOrg/