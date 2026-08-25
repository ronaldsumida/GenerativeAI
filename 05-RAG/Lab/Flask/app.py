import uuid
from openai import OpenAI
from flask import Flask, render_template, request, Response, stream_with_context
from helpers import get_chat, save_chat, run_streaming_chat
import tools as tools_module

app = Flask(__name__)
chats = {} # Storage for per-user chats
MODEL = 'gpt-5.4-mini'

SYSTEM_PROMPT = '''
    You are an expert on electric vehicles (EVs) named EVE.
    Use the knowledge-base tool to answer questions about electric
    vehicles and any technologies related to EVs such as regenerative
    braking. Answer ONLY based on what the tool returns. If the tool
    returns nothing relevant to the question, tell the user you don't
    have information on that topic. Do not hallucinate answers.
    Do not mention the tool or the knowledge base. Use markdown
    formatting in your responses.
    '''

# Home page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# REST method for chatting with an LLM and generating a streaming response
@app.route('/streaming_chat', methods=['POST'])
def streaming_chat():
    # Get the input from the user
    user_input = request.form.get('input')

    if not user_input or not user_input.strip():
        return Response('Input cannot be empty', status=400)

    try:
        session_id = request.headers.get('X-Session-ID') or str(uuid.uuid4())
        messages = get_chat(chats, session_id, SYSTEM_PROMPT).copy()
        messages.append({ 'role': 'user', 'content': user_input })

        # Generate a streaming response
        client = OpenAI()

        streaming_output = run_streaming_chat(
            client,
            MODEL,
            messages,
            tools=tools_module.tools,
            tools_modules=[tools_module]
        )

        # Inline generator for streaming output
        def generate():
            try:
                # Stream each chunk of text to the client
                for chunk in streaming_output:
                    if chunk.choices:
                        delta = chunk.choices[0].delta

                        if delta.content:
                            yield delta.content

                # When streaming is complete, save the updated chat
                save_chat(chats, messages, session_id)

            except Exception:
                yield "\n\nI'm sorry, but something went wrong."
            
        response = Response(
            stream_with_context(generate()),
            mimetype='text/plain; charset=utf-8'
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
