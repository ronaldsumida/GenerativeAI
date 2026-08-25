from agno.agent import Agent
from agno.models.openai import OpenAIChat

MODEL='gpt-5.4-mini'

# Function to hook into tool calls
async def function_hook(function_name, function_call, arguments):
    print(f'\x1b[33mCalling {function_name}\x1b[0m')
    return await function_call(**arguments)

# Function to create an agent
def create_agent(session_id, memory, mcp_tools):
    agent = Agent(
        name='Agno Agent',
        description='''
            You are a helpful assistant named Agnes who can answer questions
            about Agno. Use the MCP tools at your disposal to answer truthfully and
            accurately. If you can't get the answer through MCP, say "I don't know."
        ''',
        model=OpenAIChat(id=MODEL),
        tools=[mcp_tools],
        tool_hooks=[function_hook],
        add_history_to_context=True,
        num_history_runs=10,
        session_id=session_id,
        db=memory,
        markdown=True
    )

    return agent