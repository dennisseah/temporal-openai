import asyncio

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.contrib.pydantic import pydantic_data_converter

from temporal_openai.workflows.simple_workflow import SimpleWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    # Submit the simple workflow for execution
    result = await client.execute_workflow(
        SimpleWorkflow.run,
        "Good morning, what is the weather like today?",
        id="my-workflow-id",
        task_queue="simple-python-task-queue",
        id_conflict_policy=WorkflowIDConflictPolicy.TERMINATE_EXISTING,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
