import asyncio
import sys

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.contrib.pydantic import pydantic_data_converter

from temporal_openai.workflows.routing_workflow import RoutingWorkflow


async def main():
    user_input = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "How many vacation days do I have left this year?"
    )

    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    result = await client.execute_workflow(
        RoutingWorkflow.run,
        user_input,
        id="routing-workflow-id",
        task_queue="simple-python-task-queue",
        id_conflict_policy=WorkflowIDConflictPolicy.TERMINATE_EXISTING,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
