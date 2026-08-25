from agno.agent import Agent
from agno.models.openai import OpenAIChat

MODEL="gpt-5.4-mini"

INSTRUCTIONS = """
    You are an on-call incident triage assistant for an e-commerce platform.
    At present, you lack access to the resources you need to solve problems.
    """

# Create an agent and bind it to a session
def create_agent(session_id, db):
    agent = Agent(
        model=OpenAIChat(id=MODEL),
        session_id=session_id,
        db=db,
        add_history_to_context=True,
        num_history_runs=12,
        instructions=INSTRUCTIONS,
        markdown=True
    )

    return agent
