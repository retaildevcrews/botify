# Backend Web Application - LangServe FastAPI

This bot has been created using [LangServe](https://python.langchain.com/docs/langserve)

## Create Azure bot host resources

Below are the steps to run the Bot API as an Azure Wep App, connected with the Azure Bot Service that will expose the bot to multiple channels including: Web Chat, MS Teams, Twilio, SMS, Email, Slack, etc..

1. In Azure Portal: In Azure Active Directory->App Registrations, Create an Multi-Tenant App Registration (Service Principal), create a Secret (and take note of the value)

2. Deploy the Bot Web App and the Bot Service by clicking the Button below and type the App Registration ID and Secret Value that you got in Step 1 along with all the other ENV variables you used.

3. [Deploy Backend Bot Service infrastructure using CLI](./infra/backend-Infrastructure-Az-CLI.md)

## Deploy Bot To Azure Web App

Below are the steps to run the LangServe Bot API as an Azure Wep App:

1. We don't need to deploy again the Azure infrastructure, we did that already
for the Bot Service API. We are going to use the same App Service
and just change the code.

2. Zip the code of the bot by executing the following command in the terminal
(**you have to be inside the apps/backend/langserve/ folder**):

    ```bash
    zip -r backend.zip common && zip -j backend.zip pyproject.toml && zip -j backend.zip runserver.sh && zip -j backend.zip app/*.py
    ```

3. Using the Azure CLI deploy the bot code to the Azure App Service created on
Step 2

    ```bash
    az login -i
    az webapp deployment source config-zip --resource-group "<resource-group-name>" --name "<name-of-backend-app-service>" --src "backend.zip"
    ```

4. **Wait around 5 minutes** and test your bot by running the next Notebook.

## (optional) Running in Docker

This project folder includes a Dockerfile that allows you to easily build and
host your LangServe app.

### Building the Image

To build the image, you simply:

```shell
docker build . -t my-langserve-app
```

If you tag your image with something other than `my-langserve-app`,
note it for use in the next step.

### Running the Image Locally

To run the image, you'll need to include any environment variables
necessary for your application.

In the below example, we inject the environment variables in `credentials.env`

We also expose port 8080 with the `-p 8080:8080` option.

```shell
docker run $(cat ../../../credentials.env | sed 's/^/-e /') -p 8080:8080 my-langserve-app

```
