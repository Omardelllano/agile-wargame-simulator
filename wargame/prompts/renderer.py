from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


class PromptRenderer:
    """Renders Jinja2 agent prompt templates."""

    def __init__(self):
        template_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, **kwargs) -> str:
        template = self._env.get_template(template_name)
        return template.render(**kwargs)
