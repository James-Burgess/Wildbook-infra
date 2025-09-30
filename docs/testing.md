# Testing Guide

Complete guide to testing Wildbook Infrastructure.

## Overview

Wildbook uses **Behave** (Python implementation of Cucumber/Gherkin) for functional BDD tests. Tests are fully Dockerized and run against the complete stack.

## Quick Start

```bash
# Run all tests
docker-compose run --rm tests

# Or use helper script
./tests/run-tests.sh all
```

## Test Suites

### Health Checks

Verify all services are running and can communicate:

```bash
# Run health check tests
./tests/run-tests.sh health

# Or directly
docker-compose run --rm tests behave features/health_checks.feature
```

**Tests include:**
- PostgreSQL connectivity
- Database existence verification
- WBIA API health
- Wildbook web interface accessibility
- OpenSearch cluster health
- Service-to-service communication

### WBIA Tests

Test machine learning and detection functionality:

```bash
# Run WBIA tests
./tests/run-tests.sh wbia

# Or with tags
docker-compose run --rm tests behave --tags=wbia
```

**Tests include:**
- Image upload
- Animal detection
- Species classification
- Individual identification
- Match queries

### Wildbook Tests

Test platform workflows:

```bash
# Run Wildbook tests
./tests/run-tests.sh wildbook

# Or with tags
docker-compose run --rm tests behave --tags=wildbook
```

**Tests include:**
- Encounter creation
- Search functionality
- Individual profiles
- Complete workflows

### Integration Tests

Test full stack integration:

```bash
# Run integration tests
./tests/run-tests.sh integration

# Or with tags
docker-compose run --rm tests behave --tags=integration
```

## Running Tests

### Using Helper Script (Recommended)

```bash
# Run all tests
./tests/run-tests.sh all

# Health checks only
./tests/run-tests.sh health

# WBIA tests
./tests/run-tests.sh wbia

# Wildbook tests
./tests/run-tests.sh wildbook

# Integration tests
./tests/run-tests.sh integration

# Specific feature file
./tests/run-tests.sh feature features/health_checks.feature

# Rebuild before running
./tests/run-tests.sh all --build

# Stop services after tests
./tests/run-tests.sh all --stop

# Open debug shell
./tests/run-tests.sh shell
```

### Using Docker Compose Directly

```bash
# Run all tests
docker-compose run --rm tests

# Run with specific tags
docker-compose run --rm tests behave --tags=wbia
docker-compose run --rm tests behave --tags=detection

# Run specific feature
docker-compose run --rm tests behave features/health_checks.feature

# Run specific scenario (by line number)
docker-compose run --rm tests behave features/health_checks.feature:15

# Stop on first failure
docker-compose run --rm tests behave --stop

# Verbose output
docker-compose run --rm tests behave -v

# Open shell in test container
docker-compose run --rm tests bash
```

### Using Behave Directly (Local)

```bash
cd tests

# Install dependencies (once)
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Ensure services are running
cd .. && docker-compose up -d

# Run tests
cd tests
behave

# Run with tags
behave --tags=wbia

# Run specific feature
behave features/health_checks.feature
```

## Test Reports

### JUnit XML Reports

Automatically generated in `tests/reports/junit/`:

```bash
# View reports
ls tests/reports/junit/

# Reports are in JUnit XML format
# Can be consumed by CI/CD systems
cat tests/reports/junit/TESTS-*.xml
```

### Allure Reports

Generate pretty HTML reports:

```bash
# Install Allure formatter (already in requirements.txt)
pip install allure-behave

# Generate reports
cd tests
behave -f allure_behave.formatter:AllureFormatter -o reports/allure

# View reports
allure serve reports/allure
```

### Clean Up Reports

```bash
# Remove old reports
rm -rf tests/reports/
```

## Test Data

### Adding Test Images

Place test images in `tests/test_data/images/`:

```bash
# Copy test images
cp /path/to/zebra.jpg tests/test_data/images/
cp /path/to/elephant.jpg tests/test_data/images/
cp /path/to/giraffe.jpg tests/test_data/images/

# Images should be:
# - JPEG or PNG format
# - Contain clear animal subjects
# - Named descriptively
```

### Test Fixtures

Create JSON fixtures in `tests/test_data/fixtures/`:

```bash
# Example encounter fixture
cat > tests/test_data/fixtures/encounters.json << 'EOF'
{
  "encounters": [
    {
      "location": "Serengeti, Tanzania",
      "date": "2024-01-15",
      "species": "zebra",
      "photographer": "Test User"
    }
  ]
}
EOF
```

## Writing Tests

### Feature File Structure

Create `.feature` files in `tests/features/`:

```gherkin
Feature: Feature Name
  Description of what we're testing

  Background:
    Given common setup for all scenarios

  Scenario: Test scenario name
    Given a precondition
    When an action is performed
    Then verify the result

  @tag1 @tag2
  Scenario: Tagged scenario
    Given another precondition
    When something else happens
    Then verify different result

  Scenario Outline: Parameterized test
    Given I have <count> items
    When I add <more> items
    Then I should have <total> items

    Examples:
      | count | more | total |
      | 1     | 2    | 3     |
      | 5     | 5    | 10    |
```

### Step Definitions

Create step implementations in `tests/features/steps/`:

```python
# tests/features/steps/my_steps.py
from behave import given, when, then
from assertpy import assert_that

@given('I have {count:d} items')
def step_have_items(context, count):
    context.item_count = count

@when('I add {more:d} items')
def step_add_items(context, more):
    context.item_count += more

@then('I should have {total:d} items')
def step_verify_total(context, total):
    assert_that(context.item_count).is_equal_to(total)
```

### Using Tags

```gherkin
@wip
Scenario: Work in progress
  # Scenario under development

@slow
Scenario: Long-running test
  # Takes more than 1 minute

@integration
Scenario: Requires all services
  # Full stack test
```

Run specific tags:

```bash
# Run only WIP tests
behave --tags=wip

# Exclude WIP tests
behave --tags=~wip

# Run multiple tags (OR)
behave --tags=wbia,wildbook

# Run tag combination (AND)
behave --tags=wbia --tags=detection
```

## Debugging Tests

### Debug Mode

```bash
# Stop on first failure
docker-compose run --rm tests behave --stop

# Show captured stdout
docker-compose run --rm tests behave --no-capture

# Verbose output
docker-compose run --rm tests behave -v

# All debug options
docker-compose run --rm tests behave --stop --no-capture -v
```

### Interactive Debugging

```bash
# Open shell in test container
./tests/run-tests.sh shell

# Or
docker-compose run --rm tests bash

# Run tests interactively
behave --no-capture
```

### Adding Debug Output

```python
# In step definitions
@when('I perform an action')
def step_perform_action(context):
    print(f"Debug: Current state = {context.some_value}")
    # ... rest of step
```

### Inspecting Context

```python
# In step definitions
@then('something should happen')
def step_verify(context):
    # Print all context variables
    print(f"Context: {vars(context)}")

    # Print specific values
    print(f"Response: {context.response_json}")
```

## CI/CD Integration

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

### GitLab CI Example

```yaml
test:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker-compose --version
    - cp .env.example .env
  script:
    - docker-compose up -d db wbia wildbook opensearch
    - docker-compose run --rm tests
  after_script:
    - docker-compose down
  artifacts:
    when: always
    paths:
      - tests/reports/
    reports:
      junit: tests/reports/junit/*.xml
```

## Test Best Practices

### Writing Good Scenarios

✅ **Do:**
- Write scenarios from user perspective
- Use declarative language (what, not how)
- Keep scenarios independent
- Use descriptive names
- One assertion per Then step

❌ **Don't:**
- Couple scenarios together
- Use implementation details in steps
- Write overly long scenarios
- Mix different concerns
- Depend on test execution order

### Example: Good vs Bad

**Bad:**
```gherkin
Scenario: Test database
  Given I connect to PostgreSQL
  And I execute "CREATE TABLE test..."
  When I run "INSERT INTO test..."
  Then the query returns success
```

**Good:**
```gherkin
Scenario: Create encounter with image
  Given I have uploaded an image
  When I create an encounter for that image
  Then the encounter should be created successfully
  And the image should be associated with the encounter
```

### Step Reusability

```python
# Generic, reusable step
@then('the response status should be {status_code:d}')
def step_verify_status(context, status_code):
    assert_that(context.response.status_code).is_equal_to(status_code)

# Can be used in many scenarios:
# Then the response status should be 200
# Then the response status should be 404
```

## Troubleshooting Tests

### Tests Won't Start

```bash
# Ensure services are running
docker-compose ps

# Check test container can be built
docker-compose build tests

# View test container logs
docker-compose logs tests
```

### Services Not Ready

```bash
# The entrypoint script waits for services
# But you can also manually wait:

# Wait for WBIA
until curl -sf http://localhost:5000/api/core/db/info/ > /dev/null; do
  sleep 1
done

# Wait for Wildbook
until curl -sf http://localhost:8080 > /dev/null; do
  sleep 1
done
```

### Connection Refused Errors

```bash
# Make sure you're using service names, not localhost
# In test environment:
WBIA_URL=http://wbia:5000          # ✅ Correct
WBIA_URL=http://localhost:5000     # ❌ Wrong (from test container)
```

### Import Errors

```bash
# Rebuild test container
docker-compose build tests

# Or install dependencies locally
cd tests
pip install -r requirements.txt
```

### Flaky Tests

```bash
# Increase timeouts in .env
TEST_TIMEOUT=60
TEST_LONG_TIMEOUT=300

# Or in test code
context.timeout = 60
```

## Performance Testing

### Load Testing with Locust

```python
# tests/locustfile.py
from locust import HttpUser, task, between

class WildbookUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def view_homepage(self):
        self.client.get("/")

    @task(3)
    def upload_image(self):
        with open("test_data/images/zebra.jpg", "rb") as f:
            self.client.post("/api/upload/image/", files={"image": f})
```

```bash
# Run load test
pip install locust
locust -f tests/locustfile.py
# Open http://localhost:8089
```

## Additional Resources

- **Behave Documentation**: https://behave.readthedocs.io/
- **Gherkin Reference**: https://cucumber.io/docs/gherkin/reference/
- **AssertPy Documentation**: https://github.com/assertpy/assertpy
- **Test Directory README**: [../tests/README.md](../tests/README.md)