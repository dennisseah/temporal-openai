from temporal_openai.agents.server import run_agent


def main() -> None:
    run_agent(
        name="FAQ Agent",
        description="Answers general and frequently-asked questions.",
        prompt_template="faq_agent.jinja2",
        skill_id="faq",
        port=9102,
    )


if __name__ == "__main__":
    main()
