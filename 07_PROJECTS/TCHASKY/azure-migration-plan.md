# Azure migration plan for Tchasky monorepo

## Recommended target architecture

- Frontend: Azure Static Web Apps for the React/Vite web app
- API: Azure Container Apps for the Node/Express API
- Workers/jobs: Azure Container Apps Jobs for BullMQ workers and scheduled jobs
- Database: Azure Database for PostgreSQL Flexible Server with PostGIS enabled
- Cache: Azure Cache for Redis
- File/media storage: Azure Blob Storage for uploads and generated assets
- Secrets: Azure Key Vault with managed identity
- Observability: Application Insights + Log Analytics + Azure Monitor
- Edge/security: Azure Front Door (optional for production) and private networking where needed

## Why this fits Tchasky

The documented monorepo uses a Node 20 + TypeScript API, React/Vite frontend, PostgreSQL/PostGIS, Redis, and background workers. This target architecture aligns closely with that stack while simplifying deployment and operations.

## Containerization plan

1. Add a production Dockerfile for the API image
   - Base image: Node 20 LTS
   - Install pnpm dependencies with workspace-aware install
   - Build the API bundle
   - Expose port 3001 and run the production server

2. Add a Dockerfile for worker jobs
   - Reuse the same image but start the worker entrypoint instead of the API
   - Support scheduled jobs and queue processors

3. Add a frontend build path
   - Build the Vite app into static assets
   - Deploy to Azure Static Web Apps or a containerized frontend if SSR is later required

4. Add health checks and non-root runtime settings
   - `/health` and `/health/ready` endpoints for readiness/liveness
   - Configure resource limits and autoscaling rules

## Azure services and configuration

- Azure Container Registry: store API and worker images
- Azure Container Apps Environment: host API and jobs with ingress and revision management
- Azure Database for PostgreSQL Flexible Server: primary relational data store with PostGIS extension
- Azure Cache for Redis: queue/cache layer for auth refresh and BullMQ state
- Azure Blob Storage: upload and media storage, replacing local/third-party file handling where needed
- Azure Key Vault: store DB, Redis, payment, email, Cloudinary, and Resend secrets
- Managed Identity: authenticate Container Apps to Key Vault and Azure Storage
- Application Insights: API/web telemetry, request traces, and failures

## Implementation tasks

1. Provision infrastructure
   - Create resource group, Container Apps environment, ACR, PostgreSQL, Redis, Storage, Key Vault, and Log Analytics
   - Use Bicep or Azure Developer CLI for repeatable deployment

2. Prepare the app for Azure
   - Externalize all environment variables to Azure App Settings or Key Vault references
   - Replace local-only assumptions with Azure-compatible connection settings
   - Ensure the API can connect to PostgreSQL and Redis over managed settings

3. Containerize and deploy the API
   - Build and push the API image to ACR
   - Deploy the API to Container Apps with ingress enabled
   - Add autoscaling and health probes

4. Deploy the frontend
   - Publish the Vite build to Azure Static Web Apps
   - Configure API base URL and auth flow for the production environment

5. Migrate data and background workers
   - Create PostgreSQL schema and run migrations against Azure PostgreSQL
   - Move queues/cache to Azure Redis and run workers from Container Apps Jobs
   - Configure scheduled jobs for cleanup and payment/escrow tasks

6. Add production hardening
   - Enable monitoring, alerts, and log retention
   - Add CI/CD from GitHub Actions or Azure DevOps
   - Configure staging and production environments with separate secrets and resource groups

## Concise summary

The recommended migration is a phased move to Azure Static Web Apps for the frontend, Azure Container Apps for the API and workers, Azure Database for PostgreSQL with PostGIS, Azure Cache for Redis, Azure Blob Storage, and Azure Key Vault for secrets. This approach preserves the monorepo architecture while giving the app a production-ready, scalable deployment model.

## Next action

Start with Phase 1: create the Azure infrastructure and containerization assets for the API and worker images, then validate the app locally against Azure-style environment variables before deploying the first staging environment.
