from dataclasses import dataclass

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI
from openai.types.responses import Response
from pydantic_settings import BaseSettings, SettingsConfigDict
from temporalio import activity


# Temporal best practice: Create a data structure to hold the request parameters.
@dataclass
class OpenAIResponsesRequest:
    instructions: str
    input: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_openai_endpoint: str
    azure_openai_api_version: str
    azure_openai_deployed_model_name: str


@activity.defn
async def create(request: OpenAIResponsesRequest) -> Response:
    settings = Settings()  # type: ignore
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        azure_ad_token_provider=token_provider,
        max_retries=0,
    )

    resp = await client.responses.create(
        model=settings.azure_openai_deployed_model_name,
        instructions=request.instructions,
        input=request.input,
        timeout=15,
    )

    return resp
