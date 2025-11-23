import pytest
from unittest.mock import MagicMock, patch

# Import the class and enums from the original file (assuming it's named 'your_module')
# Replace 'your_module' with the actual name of your file (e.g., 'es_reloader')
# NOTE: Ensure the original class is importable
from external_secrets_reloader.reloader.eso_aws_provider_reloader import (
    ESOAWSProviderReloader, 
    ProviderType
)
from kubernetes.client.rest import ApiException


# --- Mock Data Fixtures ---

@pytest.fixture
def mock_k8s_client(mocker):
    """Fixture to mock the Kubernetes CustomObjectsApi client."""
    return mocker.MagicMock()

@pytest.fixture
def ss_results():
    """Mock result for SecretStores (SS)."""
    return {
        'items': [
            # Matching SecretStore (SecretsManager)
            {"metadata": {"name": "aws-secrets-ss-match"}, "spec": {"provider": {"aws": {"service": "SecretsManager"}}}},
            # Non-matching SecretStore (ParameterStore)
            {"metadata": {"name": "aws-ssm-ss-no-match"}, "spec": {"provider": {"aws": {"service": "ParameterStore"}}}},
            # Other/No provider specified
            {"metadata": {"name": "other-ss"}, "spec": {"provider": {"gcp": {}}}},
        ]
    }

@pytest.fixture
def css_results():
    """Mock result for ClusterSecretStores (CSS)."""
    return {
        'items': [
            # Matching ClusterSecretStore (SecretsManager)
            {"metadata": {"name": "aws-secrets-css-match"}, "spec": {"provider": {"aws": {"service": "SecretsManager"}}}},
            # Non-matching ClusterSecretStore (ParameterStore)
            {"metadata": {"name": "aws-ssm-css-no-match"}, "spec": {"provider": {"aws": {"service": "ParameterStore"}}}},
        ]
    }

@pytest.fixture
def es_results_matching_key():
    """Mock result for ExternalSecrets (ES) with a matching key in data."""
    return {
        'items': [
            # ExternalSecret that references a matching SecretStore AND a matching key
            {
                "metadata": {"name": "es-1", "namespace": "ns-1"},
                "spec": {
                    "secretStoreRef": {"name": "aws-secrets-ss-match"},
                    "data": [
                        {"remoteRef": {"key": "/aws/secretsmanager/my_secret_key"}},
                        {"remoteRef": {"key": "/aws/secretsmanager/other_key"}},
                    ],
                },
            },
            # ExternalSecret that references a matching ClusterSecretStore, but a non-matching key
            {
                "metadata": {"name": "es-2", "namespace": "ns-2"},
                "spec": {
                    "secretStoreRef": {"name": "aws-secrets-css-match"},
                    "data": [
                        {"remoteRef": {"key": "/aws/secretsmanager/another_key"}},
                    ],
                },
            },
            # ExternalSecret that references a non-matching SecretStore
            {
                "metadata": {"name": "es-3", "namespace": "ns-3"},
                "spec": {
                    "secretStoreRef": {"name": "aws-ssm-ss-no-match"},
                    "data": [
                        {"remoteRef": {"key": "/aws/secretsmanager/my_secret_key"}},
                    ],
                },
            },
        ]
    }

@pytest.fixture
def es_results_non_matching_key():
    """Mock result for ExternalSecrets (ES) with no matching key."""
    return {
        'items': [
            # ExternalSecret that references a matching SecretStore but NO matching key
            {
                "metadata": {"name": "es-1", "namespace": "ns-1"},
                "spec": {
                    "secretStoreRef": {"name": "aws-secrets-ss-match"},
                    "data": [
                        {"remoteRef": {"key": "/aws/secretsmanager/other_key"}},
                    ],
                },
            },
        ]
    }

# --- Fixture for the Reloader Instance ---

@pytest.fixture
def reloader_instance(mocker, mock_k8s_client):
    """Fixture to create a mocked ESOAWSProviderReloader instance."""
    # Mock 'config.load_incluster_config' to prevent actual K8s config loading
    mocker.patch('external_secrets_reloader.reloader.eso_aws_provider_reloader.config.load_incluster_config')
    
    # Mock the CustomObjectsApi client to return our MagicMock
    mocker.patch('external_secrets_reloader.reloader.eso_aws_provider_reloader.client.CustomObjectsApi', return_value=mock_k8s_client)
    
    # Create the instance for SecretsManager
    return ESOAWSProviderReloader(provider_type=ProviderType.SECRETS_MANAGER)


# --- Tests ---

## Test Initialization

def test_init_success(mocker):
    """Test successful initialization and K8s config loading."""
    mock_load_config = mocker.patch('external_secrets_reloader.reloader.eso_aws_provider_reloader.config.load_incluster_config')
    mock_custom_objects_api = mocker.patch('external_secrets_reloader.reloader.eso_aws_provider_reloader.client.CustomObjectsApi')
    
    reloader = ESOAWSProviderReloader(provider_type=ProviderType.PARAMETER_STORE)
    
    assert reloader.provider_type == "ParameterStore"
    mock_load_config.assert_called_once()
    mock_custom_objects_api.assert_called_once()
    
def test_init_failure_raises_exception(mocker):
    """Test initialization failure when K8s config loading fails."""
    # Mock config loading to raise a standard exception
    mocker.patch(
        'external_secrets_reloader.reloader.eso_aws_provider_reloader.config.load_incluster_config', 
        side_effect=Exception("No K8s Config Found")
    )
    
    with pytest.raises(Exception, match="No K8s Config Found"):
        ESOAWSProviderReloader(provider_type=ProviderType.SECRETS_MANAGER)

## Test Patch Payload Generation

def test_generate_patch_payload(reloader_instance, mocker):
    """Test the structure and dynamic content of the patch payload."""
    # Freeze time to control the timestamp
    mock_time = mocker.patch('external_secrets_reloader.reloader.eso_aws_provider_reloader.time.time', return_value=1678886400.0) 
    
    payload = reloader_instance._generate_patch_payload()
    
    # The time is frozen at 1678886400.0, so the int should be 1678886400
    expected_timestamp = "1678886400" 
    
    assert payload == {
        "metadata": {
            "annotations": {
                "reconcile.external-secrets.io/force-sync": expected_timestamp
            }
        }
    }
    mock_time.assert_called_once()

## Test Successful Reload

def test_reload_success(reloader_instance, mock_k8s_client, ss_results, css_results, es_results_matching_key):
    """
    Test a successful reload scenario:
    1. Finds matching SecretStore/ClusterSecretStore names.
    2. Finds an ExternalSecret matching the store name AND the remote key.
    3. Calls patch_namespaced_custom_object exactly once.
    4. Returns True.
    """
    # Configure the mock client to return our test data
    mock_k8s_client.list_cluster_custom_object.side_effect = [
        ss_results,             # list_cluster_custom_object for SECRET_STORE_PLURAL
        css_results,            # list_cluster_custom_object for CLUSTER_SECRET_STORE_PLURAL
        es_results_matching_key # list_cluster_custom_object for EXTERNAL_SECRET_PLURAL
    ]
    
    key_to_find = "/aws/secretsmanager/my_secret_key"
    
    result = reloader_instance.reload(key_to_find)
    
    # Assert successful reload
    assert result is True
    
    # Assert K8s object was patched
    mock_k8s_client.patch_namespaced_custom_object.assert_called_once()
    
    # Assert the correct ExternalSecret was patched
    call_kwargs = mock_k8s_client.patch_namespaced_custom_object.call_args[1]
    assert call_kwargs['name'] == 'es-1'
    assert call_kwargs['namespace'] == 'ns-1'
    assert call_kwargs['group'] == 'external-secrets.io'
    assert call_kwargs['plural'] == 'externalsecrets'

## Test Reload Failure (No Matching Key)

def test_reload_no_matching_key(reloader_instance, mock_k8s_client, ss_results, css_results, es_results_non_matching_key):
    """
    Test a scenario where the SecretStore/ClusterSecretStore is found, 
    but no ExternalSecret references the specified key. 
    1. Returns False.
    2. Patch function is never called.
    """
    mock_k8s_client.list_cluster_custom_object.side_effect = [
        ss_results, 
        css_results,
        es_results_non_matching_key # ES results contain stores but no matching key
    ]
    
    key_to_find = "/aws/secretsmanager/my_secret_key"
    
    result = reloader_instance.reload(key_to_find)
    
    # Finding nothing without errors to reload, is successful. So we should expect a return True
    assert result is True
    
    # Assert patch function was never called
    mock_k8s_client.patch_namespaced_custom_object.assert_not_called()

## Test API Exception Handling

def test_reload_api_exception(reloader_instance, mock_k8s_client, ss_results, css_results, es_results_matching_key):
    """Test handling of a general Kubernetes ApiException."""
    # Configure the mock client to raise an ApiException during the final patch call
    mock_k8s_client.list_cluster_custom_object.side_effect = [
        ss_results, 
        css_results,
        es_results_matching_key 
    ]
    
    mock_k8s_client.patch_namespaced_custom_object.side_effect = ApiException(status=500, reason="Internal Server Error")
    
    key_to_find = "/aws/secretsmanager/my_secret_key"
    
    result = reloader_instance.reload(key_to_find)
    
    assert result is False

def test_reload_api_exception_404(reloader_instance, mock_k8s_client, ss_results, css_results, es_results_matching_key):
    """Test handling of a specific 404 ApiException."""
    # Configure the mock client to raise a 404 ApiException during the final patch call
    mock_k8s_client.list_cluster_custom_object.side_effect = [
        ss_results, 
        css_results,
        es_results_matching_key 
    ]
    
    mock_k8s_client.patch_namespaced_custom_object.side_effect = ApiException(status=404, reason="Not Found")
    
    key_to_find = "/aws/secretsmanager/my_secret_key"
    
    # We can also check the logging output here to ensure the HINT is printed,
    # but for simplicity, we focus on the return value.
    result = reloader_instance.reload(key_to_find)
    
    assert result is False

## Test General Exception Handling

def test_reload_general_exception(reloader_instance, mock_k8s_client, ss_results, css_results):
    """Test handling of a non-API related exception (e.g., during list calls)."""
    # Configure a list call to raise a general exception
    mock_k8s_client.list_cluster_custom_object.side_effect = [
        ss_results, 
        Exception("Unexpected error during cluster store listing"), # Exception here
    ]
    
    key_to_find = "/aws/secretsmanager/my_secret_key"
    
    result = reloader_instance.reload(key_to_find)
    
    assert result is False