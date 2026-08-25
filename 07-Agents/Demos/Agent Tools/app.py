import uuid
from flask import Flask, render_template, request, Response, stream_with_context
from agno.db.in_memory import InMemoryDb
from agents import create_agent

app = Flask(__name__)
_memory = InMemoryDb() # Shared memory for agents
_pending_runs = {} # Paused HITL runs keyed by session ID

# Home page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# REST method for chatting with an agent and generating a streaming SSE response
@app.route('/streaming_chat', methods=['POST'])
def streaming_chat():
    try:
        # Get the user input
        user_input = request.form.get('input')

        if not user_input or not user_input.strip():
            return Response('Input cannot be empty', status=400)

        # Create an agent bound to this session and shared memory
        session_id = request.headers.get('X-Session-ID') or str(uuid.uuid4())
        agent = create_agent(session_id, _memory)

        # If the previous agent run paused for human confirmation, treat this
        # chat message as the user's decision instead of starting a new run
        pending = _pending_runs.get(session_id)

        if pending is not None:
            decision = { 'yes': True, 'no': False }.get(user_input.strip().lower())

            if decision is None:
                body = sse('text', 'Please answer **yes** to approve the pending action or **no** to reject it.')
                response = Response(body, mimetype='text/event-stream')
                response.headers['X-Session-ID'] = session_id
                response.headers['Cache-Control'] = 'no-cache'
                response.headers['X-Accel-Buffering'] = 'no'
                return response

            # Resolve every confirmation requirement in this paused run
            for requirement in pending['requirements']:
                if not requirement.needs_confirmation:
                    continue
                if decision:
                    requirement.confirm()
                else:
                    requirement.reject(note='The user rejected this action in the chat.')

            # The decision has been captured, so the pending state can be removed
            _pending_runs.pop(session_id, None)

            # Resume the run that Agno paused. The approved tool executes only
            # after continue_run() is called. If rejected, Agno resumes without it.
            streaming_output = agent.continue_run(
                run_id=pending['run_id'],
                requirements=pending['requirements'],
                stream=True
            )
        else:
            # Ordinary chat turn
            streaming_output = agent.run(user_input, stream=True)

        # Inline generator for streaming SSE output
        def generate():
            paused = False

            try:
                for chunk in streaming_output:
                    if getattr(chunk, 'is_paused', False):
                        # Keep the paused run so the next HTTP request can approve/reject
                        # the exact tool call and continue the exact Agno run
                        _pending_runs[session_id] = {
                            'run_id': chunk.run_id,
                            'requirements': chunk.requirements,
                        }
                        yield sse('confirm', 'This action requires your approval. Do you want me to continue? **Yes or no?**')
                        # Don't `return`/`break` here: abandoning the loop
                        # early would close streaming_output early, raising
                        # GeneratorExit inside it. Agno's async run path
                        # treats that as a client disconnect and would
                        # re-persist the run as *cancelled* -- the sync path
                        # this demo uses doesn't do that today, but draining
                        # to the generator's own natural end costs nothing
                        # and doesn't depend on that staying true.
                        paused = True
                        continue

                    if paused:
                        continue

                    if chunk.event == 'RunContent' and chunk.content:
                        yield sse('text', chunk.content)
                    elif chunk.event == 'RunError':
                        yield sse('text', f'\n\nError: {chunk.content}')

            except Exception:
                yield sse('text', "\n\nI'm sorry, but something went wrong.")

        response = Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )
        response.headers['X-Session-ID'] = session_id
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

    except Exception as e:
        body = sse('text', "\n\nI'm sorry, but something went wrong.")
        response = Response(body, mimetype='text/event-stream')
        response.headers['X-Session-ID'] = session_id
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

# Helper function for formatting SSE events
def sse(event, data):
    encoded = (data or '').replace('\n', '\\n')
    return f'event: {event}\ndata: {encoded}\n\n'
