"""Shared helpers for building Azure OpenAI-backed A2A agent servers.

These servers are standalone HTTP processes that the Temporal routing workflow
talks to over the A2A protocol. They are intentionally kept separate from the
Temporal worker so that each agent can be developed, scaled, and deployed on
its own.
"""

from pathlib import Path
from uuid import uuid4

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import a2a_pb2 as pb
from a2a.utils import DEFAULT_RPC_URL, TransportProtocol
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from jinja2 import Environment, FileSystemLoader
from openai import AsyncAzureOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.applications import Starlette

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(loader=FileSystemLoader(_PROMPTS_DIR))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_openai_endpoint: str
    azure_openai_api_version: str
    azure_openai_deployed_model_name: str


async def _generate_reply(instructions: str, user_input: str) -> str:
    settings = Settings()  # type: ignore[call-arg]
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
        instructions=instructions,
        input=user_input,
        timeout=30,
    )
    return resp.output_text


class OpenAIAgentExecutor(AgentExecutor):
    """An A2A agent executor that answers using Azure OpenAI."""

    def __init__(self, prompt_template: str) -> None:
        self._instructions = _env.get_template(prompt_template).render()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()

        task_id = context.task_id or str(uuid4())
        context_id = context.context_id or str(uuid4())

        if context.current_task is None:
            await event_queue.enqueue_event(
                pb.Task(
                    id=task_id,
                    context_id=context_id,
                    status=pb.TaskStatus(state=pb.TaskState.TASK_STATE_SUBMITTED),
                )
            )

        updater = TaskUpdater(event_queue, task_id, context_id)
        await updater.start_work()

        reply = await _generate_reply(self._instructions, user_input)

        await updater.add_artifact([pb.Part(text=reply)], name="response")
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported")


def build_agent_card(
    *, name: str, description: str, url: str, skill_id: str
) -> pb.AgentCard:
    return pb.AgentCard(
        name=name,
        description=description,
        version="1.0.0",
        supported_interfaces=[
            pb.AgentInterface(
                url=url,
                protocol_binding=TransportProtocol.JSONRPC.value,
                protocol_version="0.3.0",
            )
        ],
        capabilities=pb.AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            pb.AgentSkill(
                id=skill_id,
                name=name,
                description=description,
                tags=[skill_id],
            )
        ],
    )


def run_agent(
    *,
    name: str,
    description: str,
    prompt_template: str,
    skill_id: str,
    host: str = "localhost",
    port: int,
) -> None:
    """Build and serve an Azure OpenAI-backed A2A agent over HTTP (JSON-RPC)."""
    card = build_agent_card(
        name=name,
        description=description,
        url=f"http://{host}:{port}{DEFAULT_RPC_URL}",
        skill_id=skill_id,
    )

    handler = DefaultRequestHandler(
        agent_executor=OpenAIAgentExecutor(prompt_template),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    routes = create_agent_card_routes(card) + create_jsonrpc_routes(
        handler, DEFAULT_RPC_URL, enable_v0_3_compat=True
    )
    app = Starlette(routes=routes)

    uvicorn.run(app, host=host, port=port)
