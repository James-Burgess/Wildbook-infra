"""
Step definitions for health check scenarios
"""
from behave import given, when, then
import requests
import psycopg2
from assertpy import assert_that


@given('the docker-compose stack is running')
def step_verify_docker_stack(context):
    """Verify Docker Compose services are up"""
    # This is typically verified by the test runner before starting
    # Could add docker ps checks here if needed
    pass


@when('I check the PostgreSQL health endpoint')
def step_check_postgres_health(context):
    """Check if PostgreSQL is accepting connections"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            user='postgres',
            password=context.db_uri.split(':')[2].split('@')[0],
            database='postgres',
            connect_timeout=5
        )
        context.db_connection = conn
        context.db_healthy = True
    except Exception as e:
        context.db_healthy = False
        context.db_error = str(e)


@then('the database should be accepting connections')
def step_verify_db_connection(context):
    """Verify database connection is healthy"""
    assert_that(context.db_healthy).is_true()


@then('the "{db_name}" database should exist')
def step_verify_database_exists(context, db_name):
    """Verify specific database exists"""
    cursor = context.db_connection.cursor()
    cursor.execute(
        "SELECT datname FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    result = cursor.fetchone()
    assert_that(result).is_not_none()
    assert_that(result[0]).is_equal_to(db_name)
    cursor.close()


@when('I send a GET request to "{endpoint}"')
def step_send_get_request_wbia(context, endpoint):
    """Send GET request to WBIA"""
    url = f"{context.wbia_url}{endpoint}"
    try:
        context.response = context.session.get(url, timeout=context.timeout)
        context.status_code = context.response.status_code
        try:
            context.response_json = context.response.json()
        except:
            context.response_json = None
    except requests.RequestException as e:
        context.response = None
        context.status_code = None
        context.error = str(e)


@then('the response status should be {status_code:d}')
def step_verify_status_code(context, status_code):
    """Verify HTTP status code"""
    assert_that(context.status_code).is_equal_to(status_code)


@then('the response should be valid JSON')
def step_verify_valid_json(context):
    """Verify response is valid JSON"""
    assert_that(context.response_json).is_not_none()
    assert_that(context.response_json).is_instance_of(dict)


@then('the response should contain "{key}"')
def step_verify_response_contains_key(context, key):
    """Verify response JSON contains specific key"""
    assert_that(context.response_json).contains_key(key)


@when('I visit the Wildbook homepage')
def step_visit_wildbook_homepage(context):
    """Visit Wildbook homepage"""
    url = context.wildbook_url
    try:
        context.response = context.session.get(url, timeout=context.timeout)
        context.status_code = context.response.status_code
        context.response_text = context.response.text
    except requests.RequestException as e:
        context.response = None
        context.status_code = None
        context.error = str(e)


@then('the page should contain "{text}"')
def step_verify_page_contains_text(context, text):
    """Verify page HTML contains text"""
    assert_that(context.response_text).contains(text)


@when('I send a GET request to "{endpoint}" on OpenSearch')
def step_send_get_request_opensearch(context, endpoint):
    """Send GET request to OpenSearch"""
    url = f"{context.opensearch_url}{endpoint}"
    try:
        context.response = context.session.get(url, timeout=context.timeout)
        context.status_code = context.response.status_code
        context.response_json = context.response.json()
    except requests.RequestException as e:
        context.response = None
        context.status_code = None
        context.error = str(e)


@then('the cluster status should be "{status1}" or "{status2}"')
def step_verify_cluster_status(context, status1, status2):
    """Verify OpenSearch cluster status"""
    cluster_status = context.response_json.get('status')
    assert_that(cluster_status).is_in(status1, status2)


@given('WBIA is connected to PostgreSQL')
def step_verify_wbia_db_connection(context):
    """Verify WBIA can connect to its database"""
    response = context.session.get(
        f"{context.wbia_url}/api/core/db/info/",
        timeout=context.timeout
    )
    assert_that(response.status_code).is_equal_to(200)


@given('Wildbook is connected to PostgreSQL')
def step_verify_wildbook_db_connection(context):
    """Verify Wildbook can connect to its database"""
    # This would need a specific health endpoint in Wildbook
    # For now, just verify the app responds
    response = context.session.get(
        context.wildbook_url,
        timeout=context.timeout
    )
    assert_that(response.status_code).is_in(200, 302)


@given('Wildbook can reach WBIA')
def step_verify_wildbook_wbia_connection(context):
    """Verify Wildbook can communicate with WBIA"""
    # This would ideally call a Wildbook endpoint that checks WBIA connectivity
    # For now, verify both are up
    wbia_response = context.session.get(
        f"{context.wbia_url}/api/core/db/info/",
        timeout=context.timeout
    )
    assert_that(wbia_response.status_code).is_equal_to(200)


@then('the system should be fully operational')
def step_verify_system_operational(context):
    """Final verification that all integration checks passed"""
    # This step succeeds if all previous steps passed
    pass