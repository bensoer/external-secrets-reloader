# External Secrets Reloader
[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/external-secrets-reloader)](https://artifacthub.io/packages/search?repo=external-secrets-reloader)

![Python Version](https://img.shields.io/badge/dynamic/regex?url=https%3A%2F%2Fraw.githubusercontent.com%2Fbensoer%2Fexternal-secrets-reloader%2Frefs%2Fheads%2Fmain%2F.python-version&search=.*&logo=python&logoColor=blue&label=python&color=yellow)
![Latest Container](https://img.shields.io/github/v/release/bensoer/external-secrets-reloader?sort=semver&filter=v*&logo=docker&label=Latest%20Container&color=blue)
![Latest Chart](https://img.shields.io/github/v/release/bensoer/external-secrets-reloader?sort=semver&filter=!v&logo=helm&label=Latest%20Chart&color=green&logoColor=green)


External Secrets Reloader (ESR) allows you to have event-drive reloads of your External Secrets Operator's (ESO) `ExternalSecrets`. 

ESO is great but its setup requires you either to fully embrace immutability and declarative deployments OR to constantly Poll the external service for changes. Under certain circumstances, the infrastructure and work for declarative deployments or the CSP bill from the constant poll, is not feasible. So this project is meant to fill that gap. ESO had previously announced a project for creation an external secrets reloader, but it never seemed to come into fruition (or least not that I could fine). So ESR was born by my own need in my personal homelab.

Currently the project supports AWS Parameter Store as a source, but the intention is also to include AWS Secrets Manager and Azure Key Vault. 

Currently Supports Event Source:
- AWS Parameter Store
- AWS Secrets Manager

Planned Supported Event Sources:
- Azure KeyVault Secrets

# Setup
ESR is easiest deployed using Helm, along with configuration to setup what you want it to listen for events from, and credentials to access AWS. For a full list of all the environment variables and settings, see the Configuration section

Below will walk you through a high level setup:

# 1) Add Configuration Secret To Your Cluster
To use ESR you will need to configure the `EVENT_SOURCE` and `EVENT_SERVICE` along with AWS Credentials to monitor the SQS Queue the events are coming from. The following minimum `values.yaml` should get you started

Create a secret called `esr-configuration-secret`:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: esr-configuration-secret
type: Opaque
stringData:
  EVENT_SOURCE: AWS
  EVENT_SERVICE: # If reloading ParameterStore secrets - set to "ParameterStore". If reloading SecretsManager secrets - set to "SecretsManager"
  SQS_QUEUE_URL: # URL of the SQS Queue Receiving events from changes occuring in your event service
```

Apply to your cluster
```bash
kubectl apply -f ./esr-configuration-secret
```

# 2) Add AWS Configuration Secret To Your Cluster
ESR uses `boto3` to access AWS' SQS Queue. If ESR is running inside of AKS, or a Kubernetes cluster already running inside AWS, you can get away with providing access via a ServicePrincipal. If you are not running within AWS, you will need to provide access credentials. 

Create another secret called `esr-aws-credentials`:
```yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: esr-configuration-secret
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: # AWS Access Key
  AWS_SECRET_ACCESS_KEY: # AWS Secret Access Key
  AWS_DEFAULT_REGION: # AWS Region Where the SQS Queue Is Located
```

Apply to your cluster
```bash
kubectl apply -f ./esr-aws-credentials
```

# 3) Create `values.yaml` file And Deploy The ESR Helm Chart

Create a `values.yaml` file and put the following within it:
```yaml
envFrom:
  - secretRef:
      name: esr-configuration-secret
  - secretRef:
      name: esr-aws-credentials
```

Install ESR into your Kubernetes cluster with Helm, passing the `values.yaml` file you created:
```bash
# Add The Repository
helm repo add external-secrets-reloader https://bensoer.github.io/external-secrets-reloader
# Install the chart
helm upgrade --install external-secrets-reloader/external-secrets-reloader --values=values.yaml
```

# 4) Check Logs In Case Of Any Connection Issues
If ESR Can't Connect or is running into issues, the logs are the best place to find out

```bash
# List out pods to find the name of the ESR pod
kubectl get pods
# Print the logs for the pod
kubectl logs <pod>
```


# Configuration
Below is a table covering all of the available configuration options

| Variable | Description | Required | Default Value / Possible Values |
| -------- | ----------- | -------- | ------------- |
| `EVENT_SOURCE` | Where events come from. Typically this is the name of the cloud | YES | `AWS` |
| `EVENT_SERVICE` | The Service events come from | YES | `ParameterStore` , `SecretsManager` |
| `SQS_QUEUE_URL` | The URL to the SQS Queue to poll for events | Required when `EVENT_SOURCE` is set to `AWS` | |
| `SQS_QUEUE_WAIT_TIME` | Set how long the client waits for events before timing out. AWS Enforces max of 20 seconds. Longer is cheaper cloud cost, but shorter means changes are picked up faster | FALSE | Default: 10 seconds. Valid Range: 1 - 20 seconds |
| `LOG_LEVEL` | Set log output level. `DEBUG` will output logs from dependency libraries and other services | FALSE | `INFO`, `DEBUG`, `WARNING`, `ERROR` |
| `HEALTH_CHECK_PORT` | Set the port to listen for health checks. You will need to update the Helm chart to match this value if changes | FALSE | 8080



# Developer Notes

