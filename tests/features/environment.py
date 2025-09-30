"""
Behave environment configuration
Hooks for setup/teardown at different levels
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def before_all(context):
    """
    Runs once before all features
    Setup global test configuration
    """
    # Service endpoints
    context.wildbook_url = os.getenv('WILDBOOK_URL', 'http://localhost:8080')
    context.wbia_url = os.getenv('WBIA_URL', 'http://localhost:5000')
    context.opensearch_url = os.getenv('OPENSEARCH_URL', 'http://localhost:9200')

    # Database connection
    context.db_uri = os.getenv('WILDBOOK_DB_URI', 'postgresql://wildbook:wildbook@localhost:5433/wildbook')
    context.wbia_db_uri = os.getenv('WBIA_DB_URI', 'postgresql://wbia:wbia@localhost:5433/wbia')

    # Test data paths
    context.test_data_dir = os.path.join(os.path.dirname(__file__), '..', 'test_data')

    # Timeouts
    context.timeout = int(os.getenv('TEST_TIMEOUT', '30'))
    context.long_timeout = int(os.getenv('TEST_LONG_TIMEOUT', '120'))

    # Session for HTTP requests
    context.session = requests.Session()
    context.session.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })

    print(f"Testing against:")
    print(f"  Wildbook: {context.wildbook_url}")
    print(f"  WBIA: {context.wbia_url}")
    print(f"  OpenSearch: {context.opensearch_url}")


def before_feature(context, feature):
    """
    Runs before each feature
    """
    context.feature_name = feature.name
    print(f"\n{'='*60}")
    print(f"Feature: {feature.name}")
    print(f"{'='*60}")


def before_scenario(context, scenario):
    """
    Runs before each scenario
    Setup scenario-specific state
    """
    context.scenario_name = scenario.name
    context.response = None
    context.status_code = None
    context.response_json = None
    context.created_resources = []  # Track resources for cleanup


def after_scenario(context, scenario):
    """
    Runs after each scenario
    Cleanup resources created during test
    """
    # Cleanup any created resources
    if hasattr(context, 'created_resources'):
        for resource in context.created_resources:
            try:
                # Resource cleanup logic here
                pass
            except Exception as e:
                print(f"Warning: Failed to cleanup {resource}: {e}")


def after_all(context):
    """
    Runs once after all features
    Global cleanup
    """
    if hasattr(context, 'session'):
        context.session.close()

    print("\n" + "="*60)
    print("Test run completed")
    print("="*60)