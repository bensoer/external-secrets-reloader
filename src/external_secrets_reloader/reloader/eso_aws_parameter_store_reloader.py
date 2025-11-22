

from external_secrets_reloader.reloader.reloader import Reloader

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging
import sys
import time


class ESOAWSParameterStoreReloader(Reloader):

    GROUP = "external-secrets.io"
    VERSION = "v1"
    PLURAL = "externalsecrets"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        try:
            config.load_incluster_config()
            self.logger.debug("Loading K8s Configuration Successful")
        except Exception as e:
            self.logger.error("Exception Thrown Loading K8s In Cluster Configuration", exc_info=e)
            self.logger.error("Is External Secrets Reloader Running Inside Of A Kubernetes Cluster ?")
            sys.exit(1)

        self.k8s_client = client.CustomObjectsApi()
        

    def _generate_patch_payload() -> dict:
        current_timestamp = str(int(time.time()))

        return {
            "metadata": {
                "annotations": {
                    "reconcile.external-secrets.io/force-sync": current_timestamp
                }
            }
        }

    def reload(self, key):

        try:

            # Get all of the ExternalSecret entries within the cluster
            external_secrets_result = self.k8s_client.list_cluster_custom_object(
                group = self.GROUP,
                version = self.VERSION,
                plural = self.PLURAL
            )
            external_secrets = external_secrets_result.get('items', [])
            
            # Filter to only the ExternalSecret entries of type AWS ParameterStore
            parameter_store_es = [ es for es in external_secrets if es.get('spec', {}).get('provider', {}).get('aws', {}).get('service') == 'ParameterStore' ]


            for ps_es in parameter_store_es:

                # Check if this ExternalSecret references the ParameterStore Key
                data = ps_es.get("spec", {}).get("data", [])
                key_matching_es = [ x for x in data if data.get("remoteRef", {}).get("key") == key]

                # Means there is more then 0 references to our Key
                if key_matching_es:

                    # So now we can update this ExternalSecret so that it will be reloaded by ESO
                    es_name = ps_es['metadata']['name']
                    es_namespace = ps_es['metadata']['namespace']

                    patch_payload = self._generate_patch_payload()

                    self.logger.info(f"Reloading AWS Parameter Store External Secret: {es_namespace}/{es_name}")
                    self.k8s_client.patch_namespaced_custom_object(
                        group = self.GROUP,
                        version = self.VERSION,
                        plural = self.PLURAL,
                        name = es_name,
                        namespace = es_namespace,
                        body = patch_payload
                    )

                    self.logger.debug(f"Applying Annotation To AWS Parameter Store External Secret: {es_namespace}/{es_name} Successful!")

        except ApiException as apie:
            self.logger.error("Kubernetes API Exception Thrown!", exec_info=apie)

            if apie.status == 404:
                self.logger.error("\n**HINT:** A 404 error usually means the CRD ('externalsecrets.external-secrets.io') is not installed in the cluster.")

            sys.exit(1)
        except Exception as e:
            self.logger.error("Kubernetes API Exception", exec_info=e)
            sys.exit(1)


        


