# Wildbook Functional Tests

BDD-style functional tests using Behave (Python implementation of Cucumber/Gherkin).

## Quick Start (Docker - Recommended)

```bash
# From project root
cd wildbook-infra

# Start services and run all tests
docker-compose run --rm tests

# Or use the helper script
./tests/run-tests.sh all

# Run specific test suites
./tests/run-tests.sh health
./tests/run-tests.sh wbia
./tests/run-tests.sh integration

# Open shell in test container for debugging
./tests/run-tests.sh shell
```

## Local Setup (Alternative)

```bash
cd tests

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Make sure services are running
cd .. && docker-compose up -d
```

## Running Tests

### Docker (Recommended)

```bash
# All tests
docker-compose run --rm tests

# Specific feature
docker-compose run --rm tests behave features/health_checks.feature

# With tags
docker-compose run --rm tests behave --tags=wbia

# Rebuild and run
docker-compose run --rm tests --build

# Using helper script (from project root)
./tests/run-tests.sh all
./tests/run-tests.sh health --build
./tests/run-tests.sh wbia
```

### Local Python

```bash
# Run all tests
behave

# Run with verbose output
behave -v

# Run with specific formatter
behave -f pretty
```

### Specific Features

```bash
# Run single feature
behave features/health_checks.feature

# Run specific scenario
behave features/health_checks.feature:6  # Line number

# Run by scenario name
behave -n "PostgreSQL database is healthy"
```

### By Tags

```bash
# Run only integration tests
behave --tags=integration

# Run WBIA tests only
behave --tags=wbia

# Run detection and ML tests
behave --tags=detection,ml

# Exclude work-in-progress tests
behave --tags=~wip
```

### Parallel Execution

```bash
# Install parallel runner
pip install behave-parallel

# Run in parallel (4 processes)
behave-parallel features/ --processes 4
```

## Test Structure

```
tests/
├── features/
│   ├── environment.py              # Behave hooks and setup
│   ├── health_checks.feature       # Service health tests
│   ├── wbia_detection.feature      # WBIA ML tests
│   ├── wildbook_workflow.feature   # End-to-end workflows
│   └── steps/
│       ├── health_steps.py         # Health check step definitions
│       ├── wbia_steps.py           # WBIA step definitions
│       └── wildbook_steps.py       # Wildbook step definitions
├── test_data/                      # Test images and fixtures
├── reports/                        # Test reports (auto-generated)
├── behave.ini                      # Behave configuration
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Writing Tests

### Feature File Syntax

```gherkin
Feature: Feature Name
  Description of the feature

  Background:
    Given common setup steps

  Scenario: Scenario name
    Given a precondition
    When an action occurs
    Then verify the result
    And verify additional results

  @tag1 @tag2
  Scenario Outline: Parameterized scenario
    Given I have <count> items
    When I add <more> items
    Then I should have <total> items

    Examples:
      | count | more | total |
      | 1     | 2    | 3     |
      | 5     | 5    | 10    |
```

### Step Definition

```python
from behave import given, when, then
from assertpy import assert_that

@given('I have {count:d} items')
def step_set_item_count(context, count):
    context.item_count = count

@when('I add {more:d} items')
def step_add_items(context, more):
    context.item_count += more

@then('I should have {total:d} items')
def step_verify_total(context, total):
    assert_that(context.item_count).is_equal_to(total)
```

## Tags

Common tags used:

- `@wip` - Work in progress (typically excluded)
- `@skip` - Skip this test
- `@integration` - Integration test (requires all services)
- `@wbia` - WBIA-specific tests
- `@wildbook` - Wildbook-specific tests
- `@detection` - Animal detection tests
- `@ml` - Machine learning tests
- `@workflow` - End-to-end workflow tests
- `@slow` - Slow-running tests

## Test Data

Place test images and fixtures in `test_data/`:

```
test_data/
├── images/
│   ├── zebra.jpg
│   ├── elephant.jpg
│   └── giraffe.jpg
└── fixtures/
    ├── encounters.json
    └── individuals.json
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Functional Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive

      - name: Set up environment
        run: cp .env.example .env

      - name: Start services
        run: docker-compose up -d db wbia wildbook opensearch

      - name: Run tests
        run: docker-compose run --rm tests

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: tests/reports/

      - name: Stop services
        if: always()
        run: docker-compose down
```

## Reporting

### JUnit XML

```bash
# Generate JUnit reports
behave --junit --junit-directory reports/junit
```

### Allure Reports

```bash
# Generate Allure reports
behave -f allure_behave.formatter:AllureFormatter -o reports/allure

# View reports
allure serve reports/allure
```

### HTML Reports

```bash
# Install HTML formatter
pip install behave-html-formatter

# Generate HTML report
behave -f html -o reports/report.html
```

## Debugging

```bash
# Stop on first failure
behave --stop

# Run with Python debugger
behave --no-capture --no-capture-stderr

# Show captured stdout
behave --no-capture

# Increase verbosity
behave -v --logging-level=DEBUG
```

## Best Practices

1. **Keep scenarios independent** - Each scenario should set up and tear down its own state
2. **Use Background for common setup** - Avoid repetition across scenarios
3. **Write declarative steps** - Focus on WHAT, not HOW
4. **One assertion per Then** - Makes failures clearer
5. **Use tags for organization** - Group related tests
6. **Parameterize with Scenario Outline** - Test multiple inputs
7. **Clean up resources** - Use after_scenario hook for cleanup
8. **Use meaningful step names** - Should read like plain English

## Troubleshooting

### Services not available

```bash
# Check services are running
docker-compose ps

# View service logs
docker-compose logs wbia
docker-compose logs wildbook

# Restart services
docker-compose restart
```

### Import errors

```bash
# Verify dependencies
pip list

# Reinstall
pip install -r requirements.txt --force-reinstall
```

### Connection timeouts

```bash
# Increase timeouts in .env
TEST_TIMEOUT=60
TEST_LONG_TIMEOUT=300
```