#!/bin/bash
set -e

# Helper script to run tests in different modes

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    echo "Usage: ./run-tests.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  all           Run all tests (default)"
    echo "  health        Run health check tests only"
    echo "  wbia          Run WBIA tests only"
    echo "  wildbook      Run Wildbook tests only"
    echo "  integration   Run integration tests only"
    echo "  feature FILE  Run specific feature file"
    echo "  shell         Open shell in test container"
    echo ""
    echo "Options:"
    echo "  --build       Rebuild test container first"
    echo "  --stop        Stop all services after tests"
    echo ""
    echo "Examples:"
    echo "  ./run-tests.sh all"
    echo "  ./run-tests.sh health --build"
    echo "  ./run-tests.sh wbia"
    echo "  ./run-tests.sh feature features/health_checks.feature"
    echo "  ./run-tests.sh shell"
}

# Parse options
BUILD=""
STOP=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --build) BUILD="--build"; shift ;;
        --stop) STOP="yes"; shift ;;
        *) break ;;
    esac
done

COMMAND="${1:-all}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Wildbook Functional Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Ensure services are running
echo -e "${YELLOW}Starting services...${NC}"
docker-compose up -d $BUILD db wbia wildbook opensearch

case "$COMMAND" in
    all)
        echo -e "${GREEN}Running all tests${NC}"
        docker-compose run --rm tests
        ;;
    health)
        echo -e "${GREEN}Running health check tests${NC}"
        docker-compose run --rm tests behave features/health_checks.feature
        ;;
    wbia)
        echo -e "${GREEN}Running WBIA tests${NC}"
        docker-compose run --rm tests behave --tags=wbia
        ;;
    wildbook)
        echo -e "${GREEN}Running Wildbook tests${NC}"
        docker-compose run --rm tests behave --tags=wildbook
        ;;
    integration)
        echo -e "${GREEN}Running integration tests${NC}"
        docker-compose run --rm tests behave --tags=integration
        ;;
    feature)
        if [ -z "$2" ]; then
            echo "Error: Feature file required"
            echo "Usage: ./run-tests.sh feature features/health_checks.feature"
            exit 1
        fi
        echo -e "${GREEN}Running feature: $2${NC}"
        docker-compose run --rm tests behave "$2"
        ;;
    shell)
        echo -e "${GREEN}Opening shell in test container${NC}"
        docker-compose run --rm tests bash
        ;;
    *)
        usage
        exit 1
        ;;
esac

EXIT_CODE=$?

if [ "$STOP" = "yes" ]; then
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    docker-compose down
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Tests completed successfully${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
fi

exit $EXIT_CODE