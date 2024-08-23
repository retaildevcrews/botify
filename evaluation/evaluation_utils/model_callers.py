from openai import AzureOpenAI
from promptflow.core import AzureOpenAIModelConfiguration


def get_azure_openai_completion(
    prompt: str,
    model_config: AzureOpenAIModelConfiguration,
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> str:
    """This method generates a response from the Azure OpenAI API

    Args:
        prompt: The prompt to send to the Azure OpenAI API
        temperature: The temperature parameter for sampling
        max_tokens (Optional[int], optional): Maximum number of tokens to generate. Defaults to None.
    """
    # Set the API key of Azure OpenAI
    client = AzureOpenAI(
        api_key=model_config.api_key,
        azure_endpoint=model_config.azure_endpoint,
        api_version=model_config.api_version,
    )
    deployment_name = model_config.azure_deployment

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    completion = response.choices[0]
    content = completion.message.content
    return content
