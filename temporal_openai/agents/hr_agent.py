from temporal_openai.agents.server import run_agent


def main() -> None:
    run_agent(
        name="HR Agent",
        description="Answers human resources questions for employees.",
        prompt_template="hr_agent.jinja2",
        skill_id="hr",
        port=9101,
    )


if __name__ == "__main__":
    main()
