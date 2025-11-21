# External Secrets Reloader
A reloader app for External Secrets Operator (ESO)

ESO is great but its setup requires you to constantly Poll the external service for changes. With Azure Key Vaults and AWS Parameter store, this can add up if its running regularly AND in some regular interval in line with your changes. ESO had previously announced a project for creation an external secrets reloader, but it never seemed to come into fruition (or least not that I could fine). So ESR was born by my own need for event driven reloading of my `ExternalSecrets`

Currently the project supports AWS Parameter Store as a source, but the intention is also to include AWS Secrets Manager and Azure Key Vault. Documentation on how to set this all up is still to come!