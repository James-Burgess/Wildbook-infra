#!/bin/bash
set -e

# Entrypoint script for test container
# Waits for services to be ready before running tests

echo "========================================"
echo "Wildbook Functional Test Runner"
echo "========================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1

    echo -n "Waiting for ${service_name} to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "${url}" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e " ${RED}✗${NC}"
    echo -e "${RED}ERROR: ${service_name} did not become ready in time${NC}"
    return 1
}

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL..."
until pg_isready -h db -p 5432 -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e " ${GREEN}✓${NC}"

# Wait for services
wait_for_service "WBIA" "${WBIA_URL}/api/core/db/info/" 60 || exit 1
wait_for_service "Wildbook" "${WILDBOOK_URL}" 60 || exit 1
wait_for_service "OpenSearch" "${OPENSEARCH_URL}/_cluster/health" 60 || exit 1

echo ""
echo -e "${GREEN}All services ready!${NC}"
echo ""
echo "Running tests..."
echo "========================================"
echo ""

# Execute the provided command (default: behave)
exec "$@"