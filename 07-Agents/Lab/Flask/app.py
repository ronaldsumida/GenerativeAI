import os
import uuid
from flask import Flask, render_template, request, Response, stream_with_context, send_from_directory
from agno.db.in_memory import InMemoryDb
from agents import create_agent

app = Flask(__name__)
_memory = InMemoryDb()  # Shared memory for agent sessions

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Home page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Serves the raw log file for the left-hand view
@app.route('/api/log', methods=['GET'])
def get_log():
    return send_from_directory(DATA_DIR, 'app.log', mimetype='text/plain')

# REST method for invoking the triage agent
@app.route('/streaming_chat', methods=['POST'])
def streaming_chat():
    # Get the user input
    user_input = request.form.get('input')

    if not user_input or not user_input.strip():
        return Response('Input cannot be empty', status=400)

    try:
        # Create an agent bound to this session and shared memory, and run it
        session_id = request.headers.get('X-Session-ID') or str(uuid.uuid4())
        agent = create_agent(session_id, _memory)
        streaming_output = agent.run(user_input, stream=True)

        # Inline generator for streaming output
        def generate():
            try:
                for chunk in streaming_output:
                    if chunk.event == 'RunContent':
                        yield chunk.content
                    elif chunk.event == 'RunError':
                        yield f"\n\nError: {chunk.content}"
            except Exception as e:
                yield "\n\nI'm sorry, but something went wrong."

        response = Response(
            stream_with_context(generate()),
            mimetype='text/plain'
        )
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
