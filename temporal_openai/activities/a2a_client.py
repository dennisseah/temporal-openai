"""Temporal activity that calls a remote agent over the A2A protocol.

The protobuf request/response objects from the a2a-sdk are not
pydantic-serializable, so they must never cross the Temporal activity boundary.
This activity therefore builds the request, performs the call, and extracts a
plain ``str`` reply entirely on the inside.
"""

from dataclasses import dataclass
from uuid import uuid4

import httpx
from a2a.client import ClientConfig, create_client
from a2a.types import a2a_pb2 as pb
from pydantic_settings import BaseSettings, SettingsConfigDict
from temporalio import activity


# Temporal best practice: Create a data structure to hold the request parameters.
@dataclass
class A2ACallRequest:
    agent: str  # "HR" or "FAQ"
    message: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hr_agent_url: str = "http://localhost:9101"
    faq_agent_url: str = "http://localhost:9102"


def _extract_text(response: object) -> str:
    """Pull any text content out of an A2A StreamResponse event."""
    parts: list[str] = []

    message = getattr(response, "message", None)
    if message is not None and message.parts:
        parts.extend(p.text for p in message.parts if p.text)

    artifact_update = getattr(response, "artifact_update", None)
    if artifact_update is not None and artifact_update.artifact.parts:
        parts.extend(p.text for p in artifact_update.artifact.parts if p.text)

    task = getattr(response, "task", None)
    if task is not None:
        for artifact in task.artifacts:
            parts.extend(p.text for p in artifact.parts if p.text)

    return "".join(parts)


@activity.defn
async def call_agent(request: A2ACallRequest) -> str:
    settings = Settings()

    url = (
        settings.hr_agent_url
        if request.agent.upper() == "HR"
        else settings.faq_agent_url
    )

    client = await create_client(
        url,
        client_config=ClientConfig(
            httpx_client=httpx.AsyncClient(timeout=httpx.Timeout(60.0)),
        ),
    )

    send_request = pb.SendMessageRequest(
        message=pb.Message(
            message_id=str(uuid4()),
            role=pb.Role.ROLE_USER,
            parts=[pb.Part(text=request.message)],
        )
    )

    chunks: list[str] = []
    async for response in client.send_message(send_request):
        text = _extract_text(response)
        if text:
            chunks.append(text)

    return "".join(chunks)
