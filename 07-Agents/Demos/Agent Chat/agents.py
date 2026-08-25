from agno.agent import Agent
from agno.models.openai import OpenAIChat

MODEL='gpt-5.4-mini'

def create_agent(session_id, memory):
    agent = Agent(
        name='Chat Agent',
        instructions='You are a helpful assistant named LISA.',
        model=OpenAIChat(id=MODEL),
        add_history_to_context=True,
        num_history_runs=10,
        session_id=session_id,
        db=memory,
        markdown=True
    )

    return agent