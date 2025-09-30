Feature: System Health Checks
  As a system administrator
  I want to verify all services are running and healthy
  So that the platform is operational

  Background:
    Given the docker-compose stack is running

  Scenario: PostgreSQL database is healthy
    When I check the PostgreSQL health endpoint
    Then the database should be accepting connections
    And the "wildbook" database should exist
    And the "wbia" database should exist

  Scenario: WBIA service is healthy
    When I send a GET request to "/api/core/db/info/"
    Then the response status should be 200
    And the response should be valid JSON
    And the response should contain "dbname"

  Scenario: Wildbook web interface is accessible
    When I visit the Wildbook homepage
    Then the response status should be 200
    And the page should contain "Wildbook"

  Scenario: OpenSearch is healthy
    When I send a GET request to "/_cluster/health" on OpenSearch
    Then the response status should be 200
    And the cluster status should be "green" or "yellow"

  @integration
  Scenario: All services can communicate
    Given WBIA is connected to PostgreSQL
    And Wildbook is connected to PostgreSQL
    And Wildbook can reach WBIA
    Then the system should be fully operational