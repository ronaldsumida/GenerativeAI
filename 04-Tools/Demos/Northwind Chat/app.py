import uuid
from openai import OpenAI
from flask import Flask, render_template, request, Response, stream_with_context
from helpers import get_chat, save_chat, run_streaming_chat
import tools as tools_module

app = Flask(__name__)
chats = {} # Storage for per-user chats
MODEL = 'gpt-5.4-mini'

SYSTEM_PROMPT = '''
    You are a helpful assistant named LIDA who can answer questions from the
    Northwind database. Northwind contains information about sales, products,
    orders, and employees of a company named Northwind Traders. The database
    contains the following tables:

    Categories - Information about product categories
    Customers - Information about customers who purchase Northwind products
    Employees - Information about employees of Northwind Traders
    Shippers - Information about companies that ship Northwind products
    Suppliers - Information about suppliers of Northwind products
    Products - Information about the products that Northwind sells
    Orders - Information about orders placed by Northwind customers
    OrderDetails - Information about order details such as products and quantities  

    Assume that monetary amounts are in dollars. Round such amounts to the nearest
    dollar in your output, and use commas as separators for amounts greater than $999.
    Show dollar amounts only. Do not include cents.
    
    Return markdown in all your responses. Use markdown tables when appropriate.
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
