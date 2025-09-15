# Developer Experience

This example has been developed with the goal of simplifying the process of maintaining and updating the solution.

The following outlines the steps to set up a development environment, provide team members the ability to update the solution, and run the changes locally in order to test them. The focus is placed on the speed of the update->run->test cycle for the solution.

## Overview

![Development Experience Overview](llmdevex-rendering.png)

## Deployment and Development using Codespaces

We recommend using Codespaces for both deployment and development because all necessary and recommended tooling comes preinstalled.

If using codespaces to deploy Azure resources, you must use a [local VS Code instance](https://docs.github.com/en/codespaces/developing-in-codespaces/using-github-codespaces-in-visual-studio-code).

Running Codespaces through a local VS Code instance is required because you can then log in to the Azure CLI without using a device code.

Logging in with a device code is the only way to log in when using Codespaces through the browser.

When logging in with a device code, some commands (e.g., Active Directory calls) required to execute the setup scripts will not work due to conditional access policies.

### Deploy Required Resources

Provision the infrastructure by [running the deployment script](./infra/README.md) through the Command Line Interface (CLI).

### Adding sample data

To add an example index to Azure AI Search, you can run the following command:

```bash
make create-index-and-load-data
```

This will create an index, datasource, indexer and skillset that will populate some data into an index using the ```./search_index/data.json```

This process will also ensure that all the required environment variables are set first. If this is not the case, the process will stop with an error on the missing environment variable.

This performs 2 separate steps:

1. Creates the index, skillset, datasource and indexer within Azure AI Search. This can be performed separately using ```make create-index```
2. Loads the sample data into the index. This can be performed using  ```make load-json-data```

### Build and Run Docker Images

Running the following Docker Compose command will build the latest images and then run them with the required networking, secrets, services, and port forwarding. Open [docker-compose.yaml](./apps/docker-compose.yaml) for more info.

```bash
cd apps
docker compose up -w
```

## Remote Deployment

To deploy frontend and backend of application remotely, see the following READMEs.

- [Deploy Front End](../../apps/frontend/README.md)

- [Deploy Back End](../../apps/bot-service/Dockerfile)
