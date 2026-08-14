# Azure deployment migration plan for Tchasky

## Objective
Prepare the application workspace for Azure deployment with the minimum necessary changes: add containerization assets, runtime configuration placeholders, and deployment manifests that align with the existing migration guidance.

## Scope
- Work only inside the Tchasky application workspace.
- Avoid business-logic or unrelated application changes.
- Create deployment artifacts for the API service and a worker entrypoint.
- Add environment-variable-based configuration examples for Azure.

## Planned changes
1. Create a production Dockerfile for the Node/Express API.
2. Create a Dockerfile for a worker process entrypoint.
3. Add an Azure Container Apps-compatible deployment manifest.
4. Add an environment example file and a startup script for Azure-style configuration.
5. Validate that the generated artifacts are syntactically correct.

## Validation
- Confirm the Dockerfiles and manifests exist and reference the expected runtime files.
- Verify the app can be started with the provided environment-variable placeholders.
