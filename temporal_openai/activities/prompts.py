from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from temporalio import activity

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(loader=FileSystemLoader(_PROMPTS_DIR))


# Temporal best practice: Create a data structure to hold the request parameters.
@dataclass
class RenderPromptRequest:
    template: str
    context: dict[str, object] = field(default_factory=dict)


@activity.defn
async def render_prompt(request: RenderPromptRequest) -> str:
    template = _env.get_template(request.template)
    return template.render(**request.context)
