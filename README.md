# External Secrets Reloader
External Secrets Reloader (ESR) allows you to have event-drive reloads of your External Secrets Operator's (ESO) `ExternalSecrets`. 

ESO is great but its setup requires you either to fully embrace immutability and declarative deployments OR to constantly Poll the external service for changes. Under certain circumstances, the infrastructure and work for declarative deployments or the CSP bill from the constant poll, is not feasible. So this project is meant to fill that gap. ESO had previously announced a project for creation an external secrets reloader, but it never seemed to come into fruition (or least not that I could fine). So ESR was born by my own need in my personal homelab.

Currently the project supports AWS Parameter Store as a source, but the intention is also to include AWS Secrets Manager and Azure Key Vault. 

Currently Supports Event Source:
- AWS Parameter Store
- AWS Secrets Manager

Planned Supported Event Sources:
- Azure KeyVault Secrets

# Setup



# Developer Notes

