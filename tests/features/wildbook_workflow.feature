Feature: Wildbook Complete Workflow
  As a wildlife researcher
  I want to perform a complete identification workflow
  From image upload to individual matching

  Background:
    Given Wildbook is running
    And WBIA is running
    And I am logged in as a researcher

  @workflow @end-to-end
  Scenario: Complete animal identification workflow
    Given I have a photo of a zebra
    When I upload the photo to Wildbook
    And I submit the encounter for processing
    And I wait for detection to complete
    Then the image should contain detected animals
    When I approve the annotations
    And I submit for identification
    And I wait for matching to complete
    Then I should see potential matching individuals
    And I should be able to view match confidence scores

  @workflow @encounter
  Scenario: Create a new encounter
    When I create a new encounter with:
      | field         | value                  |
      | location      | Serengeti, Tanzania    |
      | date          | 2024-09-30            |
      | species       | Zebra                  |
      | photographer  | Test User             |
    Then the encounter should be created successfully
    And the encounter should appear in my recent encounters

  @workflow @search
  Scenario: Search for encounters
    Given there are multiple encounters in the database
    When I search for encounters with species "Zebra"
    And I filter by location "Serengeti"
    Then I should see matching encounters
    And the results should be sorted by date

  @workflow @individual
  Scenario: Create and view an individual
    Given I have confirmed a unique animal identification
    When I create a new individual profile with name "Stripe_001"
    Then the individual should be created successfully
    And I should be able to view the individual's profile
    And the profile should show all associated encounters