from agno.agent import Agent
from agno.models.openai import OpenAIChat
from tools import search_logs, get_deploys, get_commit, compute_latency_stats
from agno.skills import Skills, LocalSkills
from tools import search_logs, get_deploys, get_commit, compute_latency_stats

MODEL="gpt-5.4-mini"

INSTRUCTIONS = """
    You are an on-call incident assistant for an e-commerce platform.
    Keep chat answers concise and skimmable. The incident-report skill
    is the exception -- follow its structure instead.
    """

# Function to hook into tool calls
def function_hook(function_name, function_call, arguments):
    args_str = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
    print(f'\x1b[33mCalling {function_name}({args_str})\x1b[0m')
    return function_call(**arguments)

# Create an agent and bind it to a session
def create_agent(session_id, db):
    agent = Agent(
        model=OpenAIChat(id=MODEL),
        session_id=session_id,
        db=db,
        add_history_to_context=True,
        num_history_runs=12,
        tools=[
            search_logs,
            get_deploys,
            get_commit,
            compute_latency_stats
        ],
        skills=Skills(loaders=[LocalSkills("skills")]),
        tool_hooks=[function_hook],
        instructions=INSTRUCTIONS,
        markdown=True
    )

    return agent
