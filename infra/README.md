# Create botify Infrastructure using CLI

The intent of your document to guide users in deploying the necessary Azure resources for hosting the backend application service. These resources include:

1. Azure AI Search
2. Cognitive Services
3. CosmosDB
4. Storage account
5. Azure Open AI
6. Azure AI Content Safety

---

## What does `general_deployment.sh` do?

The `general_deployment.sh` script is responsible for provisioning all the core Azure cloud resources required for the botify backend infrastructure. It automates the following steps:

- **Creates an Azure resource group** in your chosen region.
- **Deploys all required Azure resources** using the `azuredeploy.bicep` template and `main.parameters.json` for configuration. This includes:
  - Azure AI Search
  - Azure Cognitive Services
  - Azure OpenAI Service (with model deployments)
  - Azure Content Safety
  - Azure CosmosDB (with database and container)
  - Azure Blob Storage (with containers)
  - Azure Log Analytics Workspace
  - Azure Application Insights
  - Azure Managed Identity
  - *Optional*: Azure Container Registry (ACR)
  - *Optional*: Azure Container Apps Environment
- **Retrieves connection strings, keys, and endpoints** for the deployed resources.
- **Generates an environment file** (`credentials.env`) with all necessary secrets and configuration values for the application services.

This script ensures that all foundational cloud resources are created and configured before deploying application services. The script will prompt whether you would like to deploy botify on a Azure Container App environment. It is **highly recommended** that you **do NOT** proceed with the container app deployment and run the Botify solution **locally**.

In order to run this script, you need to have the Azure CLI installed and be logged in to your Azure account and run the following command:

```bash
cd infra
bash general_deployment.sh
```

After this deployment, the core Azure resources have been deployed to run and a `credentials.env` file should be populated with the necessary values to run Botify locally. Follow these [remaining steps](../docs/developer_experience/README.md#adding-sample-data) to boot up Botify.

## Optionally deploy Application Services with `services_deployment.sh`

If you chose to deploy the container app endpoint in `general_deployment.sh`, then continue with this section in setting up the application services. The `services_deployment.sh` script automates the process of building, pushing, and deploying the main application services to Azure Container Apps. It is designed to work after the core Azure infrastructure (such as databases and AI services) has been provisioned.

### What Does `services_deployment.sh` Do?

- **Builds Docker images** for each service in the `apps` directory:
  - `bot-service`
  - `collector`
  - `frontend`
  - `tokenservice`
- **Pushes** these images to the specified Azure Container Registry (ACR).
- **Deploys** each service as an Azure Container App in the designated resource group and environment.
  - The `frontend` service is exposed externally on port 8000.
  - Other services are deployed with default settings.

### Services Deployed

- **bot-service**: The main backend bot logic.
- **collector**: Likely handles data collection or telemetry.
- **frontend**: The user-facing web application.
- **tokenservice**: Manages authentication tokens or related security.

### How to Deploy the Services

1. **Ensure prerequisites**:
   - Azure CLI is installed and logged in.
   - Docker is installed and running.
   - You have access to the Azure Container Registry.

2. **Run the script**:
   ```bash
   cd infra
   bash services_deployment.sh
   ```

   The script will:
   - Log in to the Azure Container Registry.
   - Build and push Docker images for each service.
   - Deploy each service as an Azure Container App.

3. **Access the frontend**:
   - After deployment, the frontend will be accessible via the external endpoint provided by Azure Container Apps.

For any troubleshooting or advanced configuration, refer to the comments and logic within `services_deployment.sh` itself.
