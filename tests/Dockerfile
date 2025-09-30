FROM python:3.11-slim

LABEL maintainer="Wild Me <dev@wildme.org>"
LABEL description="Wildbook Functional Tests - Behave/Gherkin BDD"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /tests

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test files
COPY . .

# Create reports directory
RUN mkdir -p reports/junit reports/allure

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment defaults (overridden by docker-compose)
ENV WILDBOOK_URL=http://wildbook:8080
ENV WBIA_URL=http://wbia:5000
ENV OPENSEARCH_URL=http://opensearch:9200
ENV WILDBOOK_DB_URI=postgresql://wildbook:wildbook@db:5432/wildbook
ENV WBIA_DB_URI=postgresql://wbia:wbia@db:5432/wbia
ENV TEST_TIMEOUT=30
ENV TEST_LONG_TIMEOUT=120

# Use entrypoint to wait for services
ENTRYPOINT ["/entrypoint.sh"]

# Default command - run all tests
CMD ["behave", "--format", "pretty", "--junit", "--junit-directory", "reports/junit"]