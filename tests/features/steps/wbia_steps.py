"""
Step definitions for WBIA detection and identification scenarios
"""
from behave import given, when, then
import requests
import os
from assertpy import assert_that


@given('WBIA service is running')
def step_verify_wbia_running(context):
    """Verify WBIA is accessible"""
    response = requests.get(f"{context.wbia_url}/api/core/db/info/", timeout=10)
    assert_that(response.status_code).is_equal_to(200)


@given('I have test images in the test data directory')
def step_verify_test_data_exists(context):
    """Verify test data directory exists"""
    assert_that(os.path.exists(context.test_data_dir)).is_true()


@given('I have a test image "{filename}"')
def step_load_test_image(context, filename):
    """Load a test image file"""
    image_path = os.path.join(context.test_data_dir, filename)
    assert_that(os.path.exists(image_path)).is_true()
    context.test_image_path = image_path
    context.test_image_filename = filename


@when('I upload the image to WBIA')
def step_upload_image_to_wbia(context):
    """Upload image to WBIA"""
    with open(context.test_image_path, 'rb') as f:
        files = {'image': (context.test_image_filename, f, 'image/jpeg')}
        response = context.session.post(
            f"{context.wbia_url}/api/upload/image/",
            files=files,
            timeout=context.timeout
        )
    context.response = response
    context.status_code = response.status_code
    try:
        context.response_json = response.json()
    except:
        context.response_json = None


@then('the response should contain an image ID')
def step_verify_image_id_in_response(context):
    """Verify response contains image ID"""
    assert_that(context.response_json).is_not_none()
    # WBIA typically returns gid (image ID)
    assert_that(context.response_json).contains_key('gid')
    context.uploaded_image_id = context.response_json['gid']


@given('I have uploaded an image with ID "{image_id}"')
def step_set_uploaded_image_id(context, image_id):
    """Set context image ID (assumes image was already uploaded)"""
    context.uploaded_image_id = int(image_id)


@when('I request detection on the image')
def step_request_detection(context):
    """Request animal detection on uploaded image"""
    payload = {
        'gid_list': [context.uploaded_image_id]
    }
    response = context.session.post(
        f"{context.wbia_url}/api/engine/detect/cnn/",
        json=payload,
        timeout=context.long_timeout
    )
    context.response = response
    context.status_code = response.status_code
    try:
        context.response_json = response.json()
    except:
        context.response_json = None


@then('the response should contain detected annotations')
def step_verify_annotations_in_response(context):
    """Verify detection returned annotations"""
    assert_that(context.response_json).is_not_none()
    assert_that(context.response_json).contains_key('annotations')
    context.annotations = context.response_json['annotations']
    assert_that(context.annotations).is_not_empty()


@then('each annotation should have a bounding box')
def step_verify_bounding_boxes(context):
    """Verify each annotation has bbox"""
    for annotation in context.annotations:
        assert_that(annotation).contains_key('bbox')
        bbox = annotation['bbox']
        assert_that(bbox).is_length(4)  # [x, y, w, h]


@then('each annotation should have a confidence score')
def step_verify_confidence_scores(context):
    """Verify each annotation has confidence"""
    for annotation in context.annotations:
        assert_that(annotation).contains_key('confidence')
        confidence = annotation['confidence']
        assert_that(confidence).is_between(0.0, 1.0)


@given('I have an annotation with ID "{annot_id}"')
def step_set_annotation_id(context, annot_id):
    """Set context annotation ID"""
    context.annotation_id = int(annot_id)


@when('I request species classification')
def step_request_species_classification(context):
    """Request species classification"""
    payload = {
        'aid_list': [context.annotation_id]
    }
    response = context.session.post(
        f"{context.wbia_url}/api/engine/classify/species/",
        json=payload,
        timeout=context.long_timeout
    )
    context.response = response
    context.status_code = response.status_code
    try:
        context.response_json = response.json()
    except:
        context.response_json = None


@then('the response should contain a species name')
def step_verify_species_name(context):
    """Verify species classification result"""
    assert_that(context.response_json).is_not_none()
    assert_that(context.response_json).contains_key('species')


@then('the confidence score should be between {min_val:f} and {max_val:f}')
def step_verify_confidence_range(context, min_val, max_val):
    """Verify confidence is in valid range"""
    confidence = context.response_json.get('confidence', 0)
    assert_that(confidence).is_between(min_val, max_val)


@when('I query for matching individuals')
def step_query_matching_individuals(context):
    """Query for matching individual animals"""
    payload = {
        'qaid_list': [context.annotation_id],
        'daid_list': None  # Query against entire database
    }
    response = context.session.post(
        f"{context.wbia_url}/api/engine/query/graph/",
        json=payload,
        timeout=context.long_timeout
    )
    context.response = response
    context.status_code = response.status_code
    try:
        context.response_json = response.json()
    except:
        context.response_json = None


@then('the response should contain a ranked list of matches')
def step_verify_ranked_matches(context):
    """Verify matching results"""
    assert_that(context.response_json).is_not_none()
    assert_that(context.response_json).contains_key('matches')
    context.matches = context.response_json['matches']
    assert_that(context.matches).is_instance_of(list)


@then('each match should have a similarity score')
def step_verify_similarity_scores(context):
    """Verify each match has a score"""
    for match in context.matches:
        assert_that(match).contains_key('score')
        score = match['score']
        assert_that(score).is_instance_of((int, float))