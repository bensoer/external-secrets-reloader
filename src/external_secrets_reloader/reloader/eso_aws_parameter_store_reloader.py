

from external_secrets_reloader.reloader.reloader import Reloader

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging
import sys
import time
import signal


class ESOAWSParameterStoreReloader(Reloader):

    GROUP = "external-secrets.io"
    VERSION = "v1"
    PLURAL = "externalsecrets"

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

        try:
            config.load_incluster_config()
            self._logger.debug("Loading K8s Configuration Successful")
        except Exception as e:
            self._logger.error("Exception Thrown Loading K8s In Cluster Configuration", exc_info=e)
            self._logger.error("Is External Secrets Reloader Running Inside Of A Kubernetes Cluster ?")
            signal.raise_signal(signal.SIGTERM)

        self.k8s_client = client.CustomObjectsApi()
        

    def _generate_patch_payload(self) -> dict:
        current_timestamp = str(int(time.time()))

        return {
            "metadata": {
                "annotations": {
                    "reconcile.external-secrets.io/force-sync": current_timestamp
                }
            }
        }

    def reload(self, key) -> bool:

        try:

            self._logger.debug("Finding All AWS ParamterStore Configured SecretStores")
            # Get the names of all the secret stores that use ParameterStore
            secret_store_results = self.k8s_client.list_cluster_custom_object(
                group = self.GROUP,
                version = self.VERSION,
                plural= "secretstores"
            )
            secret_stores = secret_store_results.get('items', [])
            parameter_store_ss_names = [ ss["metadata"]["name"] for ss in secret_stores if ss.get('spec', {}).get('provider', {}).get('aws', {}).get('service') == 'ParameterStore' ]

            self._logger.debug("Finding All AWS ParameterStore Configured ClusterSecretStores")
            # Get the names of all the Cluster Secret Stores that use ParameterStore
            cluster_secret_store_results = self.k8s_client.list_cluster_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                plural="clustersecretstores"
            )
            cluster_secret_stores = cluster_secret_store_results.get('items', [])
            parameter_store_css_names = [ css["metadata"]["name"] for css in cluster_secret_stores if css.get('spec', {}).get('provider', {}).get('aws', {}).get('service') == 'ParameterStore' ]

            all_parameter_store_names = parameter_store_ss_names + parameter_store_css_names


            self._logger.debug("Finding All ExternalSecrets that use the AWS ParameterStore SecretStores or ClusterSecretStores")
            # Get all of the ExternalSecret entries within the cluster
            external_secrets_result = self.k8s_client.list_cluster_custom_object(
                group = self.GROUP,
                version = self.VERSION,
                plural = self.PLURAL
            )
            external_secrets = external_secrets_result.get('items', [])
            
            # Filter to only the ExternalSecret that are part of the parameter store names
            parameter_store_es = [ es for es in external_secrets if es.get('spec', {}).get('secretStoreRef', {}).get('name') in all_parameter_store_names ]


            for ps_es in parameter_store_es:

                # Check if this ExternalSecret references the ParameterStore Key
                data = ps_es.get("spec", {}).get("data", [])
                key_matching_es = [ x for x in data if x.get("remoteRef", {}).get("key") == key]

                # Means there is more then 0 references to our Key
                if key_matching_es:

                    # So now we can update this ExternalSecret so that it will be reloaded by ESO
                    es_name = ps_es['metadata']['name']
                    es_namespace = ps_es['metadata']['namespace']

                    patch_payload = self._generate_patch_payload()

                    self._logger.info(f"Reloading AWS Parameter Store External Secret: {es_namespace}/{es_name}")
                    self.k8s_client.patch_namespaced_custom_object(
                        group = self.GROUP,
                        version = self.VERSION,
                        plural = self.PLURAL,
                        name = es_name,
                        namespace = es_namespace,
                        body = patch_payload
                    )

                    self._logger.debug(f"Applying Annotation To AWS Parameter Store External Secret: {es_namespace}/{es_name} Successful!")
                    return True

        except ApiException as apie:
            self._logger.error("Kubernetes API Exception Thrown!", exc_info=apie)

            if apie.status == 404:
                self._logger.error("\n**HINT:** A 404 error usually means the CRD ('externalsecrets.external-secrets.io') is not installed in the cluster.")

            return False

        except Exception as e:
            self._logger.error("Kubernetes API Exception", exc_info=e)

            return False


