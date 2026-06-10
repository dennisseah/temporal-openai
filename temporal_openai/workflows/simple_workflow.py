from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal_openai.activities import openai_responses, prompts


@workflow.defn
class SimpleWorkflow:
    @workflow.run
    async def run(self, input: str) -> str:
        system_instructions = await workflow.execute_activity(
            prompts.render_prompt,
            prompts.RenderPromptRequest(template="simple.jinja2"),
            start_to_close_timeout=timedelta(seconds=30),
        )
        result = await workflow.execute_activity(
            openai_responses.create,
            openai_responses.OpenAIResponsesRequest(
                instructions=system_instructions,
                input=input,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )
        return result.output_text
