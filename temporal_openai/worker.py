import asyncio

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from temporal_openai.activities import a2a_client, openai_responses, prompts
from temporal_openai.workflows.routing_workflow import RoutingWorkflow
from temporal_openai.workflows.simple_workflow import SimpleWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    worker = Worker(
        client,
        task_queue="simple-python-task-queue",
        workflows=[SimpleWorkflow, RoutingWorkflow],
        activities=[
            openai_responses.create,
            prompts.render_prompt,
            a2a_client.call_agent,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
