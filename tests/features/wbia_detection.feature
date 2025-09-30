Feature: WBIA Animal Detection
  As a wildlife researcher
  I want to detect animals in uploaded images
  So that I can identify and track wildlife

  Background:
    Given WBIA service is running
    And I have test images in the test data directory

  @wbia @detection
  Scenario: Upload an image to WBIA
    Given I have a test image "zebra.jpg"
    When I upload the image to WBIA
    Then the response status should be 200
    And the response should contain an image ID

  @wbia @detection
  Scenario: Detect animals in an uploaded image
    Given I have uploaded an image with ID "1"
    When I request detection on the image
    Then the response status should be 200
    And the response should contain detected annotations
    And each annotation should have a bounding box
    And each annotation should have a confidence score

  @wbia @ml
  Scenario: Identify species from annotation
    Given I have an annotation with ID "1"
    When I request species classification
    Then the response status should be 200
    And the response should contain a species name
    And the confidence score should be between 0 and 1

  @wbia @query
  Scenario: Query for matching individuals
    Given I have an annotation with ID "1"
    When I query for matching individuals
    Then the response status should be 200
    And the response should contain a ranked list of matches
    And each match should have a similarity score