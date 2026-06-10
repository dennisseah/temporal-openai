from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal_openai.activities import a2a_client, openai_responses, prompts


@workflow.defn
class RoutingWorkflow:
    @workflow.run
    async def run(self, input: str) -> str:
        # 1. Classify the user's input as an HR or FAQ question.
        classify_instructions = await workflow.execute_activity(
            prompts.render_prompt,
            prompts.RenderPromptRequest(template="classify.jinja2"),
            start_to_close_timeout=timedelta(seconds=30),
        )
        classification = await workflow.execute_activity(
            openai_responses.create,
            openai_responses.OpenAIResponsesRequest(
                instructions=classify_instructions,
                input=input,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        agent = "HR" if "HR" in classification.output_text.upper() else "FAQ"

        # 2. Forward the question to the chosen agent over A2A.
        response = await workflow.execute_activity(
            a2a_client.call_agent,
            a2a_client.A2ACallRequest(agent=agent, message=input),
            start_to_close_timeout=timedelta(seconds=60),
        )

        return f"[routed to {agent}] {response}"
