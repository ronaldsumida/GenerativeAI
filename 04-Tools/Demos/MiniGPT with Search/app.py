import uuid, json, os
from azure.storage.blob import BlobServiceClient, ContentSettings
from flask import Flask, render_template, request, Response, jsonify, stream_with_context
from helpers import get_chat, save_chat, run_streaming_chat
import tools as tools_module
from openai import OpenAI

app = Flask(__name__)
chats = {}  # Storage for per-user chats
MODEL = 'gpt-5.4-mini'

SYSTEM_PROMPT = '''
    You are a friendly assistant named Minnie. Do your
    best to answer questions submitted to you truthfully and
    accurately. Use markdown formatting in your responses.
    '''

SUPPORTED_IMAGE_TYPES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
AZURE_STORAGE_CONNECTION_STRING = os.environ['AZURE_STORAGE_CONNECTION_STRING']
AZURE_STORAGE_CONTAINER_NAME = os.environ.get('AZURE_STORAGE_CONTAINER_NAME')

blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)

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
        attachments = json.loads(request.form.get('attachments', '[]'))
        messages.append({ 'role': 'user', 'content': build_user_content(user_input, attachments) })

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

# REST method for preparing a file attachment. PDFs are uploaded to OpenAI's
# Files API. Images are uploaded to Azure Blob Storage and referenced by URL.
# Other files are read as text and returned to the browser so their contents
# can be included directly in the next prompt.
@app.route('/upload_file', methods=['POST'])
def upload_file():
    uploaded_file = request.files.get('file')

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({ 'error': 'No file was provided' }), 400

    filename = uploaded_file.filename
    mime_type = uploaded_file.mimetype or 'application/octet-stream'

    try:
        if mime_type in SUPPORTED_IMAGE_TYPES:
            image_url = upload_to_azure(
                uploaded_file.stream,
                filename,
                mime_type
            )

            return jsonify({
                'kind': 'image_url',
                'image_url': image_url,
                'filename': filename,
                'mime_type': mime_type
            })

        if mime_type.startswith('image/'):
            return jsonify({
                'error': 'Only PNG, JPEG, WEBP, and non-animated GIF images are supported'
            }), 400

        if mime_type == 'application/pdf':
            client = OpenAI()
            result = client.files.create(
                file=(filename, uploaded_file.stream, mime_type),
                purpose='user_data',
                expires_after={
                    'anchor': 'created_at',
                    'seconds': 86400,  # Delete file after 24 hours
                }
            )

            return jsonify({
                'kind': 'file_id',
                'file_id': result.id,
                'filename': filename,
                'mime_type': mime_type
            })

        file_bytes = uploaded_file.read()

        # A NUL byte is a strong indication that this is a binary file rather
        # than a text document. This avoids injecting binary data into a prompt.
        if b'\x00' in file_bytes:
            return jsonify({
                'error': 'Only PDF and text-based files are supported'
            }), 400

        # UTF-8 covers common text, JSON, Markdown, XML, CSV, source code, etc.
        # utf-8-sig also removes a UTF-8 byte-order mark when one is present.
        file_text = file_bytes.decode('utf-8-sig', errors='replace')

        return jsonify({
            'kind': 'text',
            'text': file_text,
            'filename': filename,
            'mime_type': mime_type
        })

    except Exception as e:
        return jsonify({ 'error': getattr(e, 'body', {}).get('message', str(e)) }), 500

# REST method for retrieving the cached conversation for a session
@app.route('/conversation/<session_id>', methods=['GET'])
def conversation(session_id):
    return jsonify(chats.get(session_id, []))

# Helper function for building the content of a user message. Each PDF
# attachment becomes its own { 'type': 'file' } content block, referenced by
# Files API ID. Each image attachment becomes its own { 'type': 'image_url' }
# content block, referenced by its Azure Blob Storage URL. Each text-file
# attachment's contents are appended directly into the prompt text.
def build_user_content(user_input, attachments):
    if not attachments:
        return user_input

    file_blocks = []
    text_parts = []

    for attachment in attachments:
        display_name = attachment.get('filename') or 'attached file'

        if attachment.get('kind') == 'file_id':
            file_blocks.append({ 'type': 'file', 'file': { 'file_id': attachment['file_id'] } })
        elif attachment.get('kind') == 'image_url':
            file_blocks.append({ 'type': 'image_url', 'image_url': { 'url': attachment['image_url'] } })
        elif attachment.get('kind') == 'text':
            text_parts.append(
                f'--- Begin contents of {display_name} ---\n'
                f'{attachment.get("text", "")}\n'
                f'--- End contents of {display_name} ---'
            )

    prompt_text = user_input

    if text_parts:
        prompt_text = user_input + '\n\n' + '\n\n'.join(text_parts)

    if file_blocks:
        return file_blocks + [{ 'type': 'text', 'text': prompt_text }]

    return prompt_text


# Helper function for uploading an image to Azure Blob Storage
def upload_to_azure(file_stream, filename, mime_type):
    blob_name = f'{uuid.uuid4()}-{filename}'

    blob_client = blob_service_client.get_blob_client(
        container=AZURE_STORAGE_CONTAINER_NAME,
        blob=blob_name
    )

    blob_client.upload_blob(
        file_stream,
        overwrite=False,
        content_settings=ContentSettings(content_type=mime_type)
    )

    return blob_client.url
