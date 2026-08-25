import uuid
from quart import Quart, render_template, request, Response
from agno.db.in_memory import InMemoryDb
from agno.tools.mcp import MCPTools
from agents import create_agent

app = Quart(__name__)
_memory = InMemoryDb()  # Shared memory for agents
_mcp_tools = None  # MCPTools instance

# Home page
@app.route('/', methods=['GET'])
async def index():
    return await render_template('index.html')

# REST method for chatting with an agent and generating a streaming response
@app.route('/streaming_chat', methods=['POST'])
async def streaming_chat():
    # Get the user input
    user_input = (await request.form).get('input')

    if not user_input or not user_input.strip():
        return Response('Input cannot be empty', status=400)

    session_id = request.headers.get('X-Session-ID') or str(uuid.uuid4())

    try:
        # Create an agent bound to this session and shared memory
        agent = create_agent(session_id, _memory, _mcp_tools)
        streaming_output = agent.arun(user_input, stream=True)

        # Async generator for streaming output
        async def generate():
            try:
                async for chunk in streaming_output:
                    if chunk.event == 'RunContent':
                        yield chunk.content
                    elif chunk.event == 'RunError':
                        yield f"\n\nError: {chunk.content}"
            except Exception:
                yield "\n\nI'm sorry, but something went wrong."

        response = Response(generate(), mimetype='text/plain')
        response.headers['X-Session-ID'] = session_id
        return response

    except Exception as e:
        response = Response(
            "\n\nI'm sorry, but something went wrong.",
            status=getattr(e, 'status_code', 500),
            mimetype='text/plain; charset=utf-8'
        )
        response.headers['X-Session-ID'] = session_id
        return response

# Startup function to open an MCP connection
@app.before_serving
async def startup():
    global _mcp_tools
    _mcp_tools = MCPTools(transport='streamable-http', url='https://docs.agno.com/mcp')
    await _mcp_tools.connect()

# Shutdown function to close an MCP connection
@app.after_serving
async def shutdown():
    if _mcp_tools:
        await _mcp_tools.close()