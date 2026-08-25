import uuid
from pathlib import Path
from openai import OpenAI
from flask import Flask, render_template, request, Response, stream_with_context
from helpers import get_chat, save_chat, run_streaming_chat_sse, format_sse
import tools as tools_module

app = Flask(__name__)
chats = {} # Storage for per-user chats
MODEL = 'gpt-5.4-mini'
CHARTS_DIR = Path(__file__).resolve().parent / 'static' / 'charts'
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = f'''
    You are a sports data analyst Named LISA with access to a CSV containing a
    weekly NFL player stats dataset (1999-2024) from nflverse. Use the Python
    tool to generate and execute code when appropriate -- for example, to
    perform calculations, generate charts and graphs, or retrieve or manipulate
    data. Don't attempt to do math yourself. Use the Python tool instead. Don't
    show code unless you're asked to.
    
    Answer in markdown. Do not wrap JSON around your reply. Use markdown
    tables when appropriate.

    When the Python tool returns an image file ID, the UI will show
    the chart. Do NOT include images in your markdown. Do NOT include an
    image, a markdown image tag (![...](...)), or any file path (e.g.,
    sandbox:/..., /mnt/data/...) in your reply. These paths are internal to
    the sandbox and are not reachable by the user's browser. Only describe
    the chart in prose.    

    ABOUT THE DATASET:
    Grain: one row = one player's stats in one game (regular season or postseason).

    Key columns:
    - Identity: player_id, player_name/player_display_name, position (QB/RB/WR/TE/etc.), position_group
    - Context: recent_team, opponent_team, season, week, season_type (REG or POST)
    - Passing: completions, attempts, passing_yards, passing_tds, interceptions, sacks, passing_epa, dakota, etc.
    - Rushing: carries, rushing_yards, rushing_tds, rushing_epa, etc.
    - Receiving: receptions, targets, receiving_yards, receiving_tds, target_share, air_yards_share, wopr, etc.
    - Fantasy: fantasy_points, fantasy_points_ppr

    Stat columns are 0 (not NaN) when a player didn't attempt that activity
    (e.g., a RB has passing_yards=0). Advanced efficiency metrics (*_epa, pacr,
    dakota, racr) can be null when the denominator is 0 or undefined. Exclude nulls
    rather than treating them as 0.

    When answering questions:
    - Aggregate across weeks (e.g., "season passing yards") by summing/grouping over season + player_id, not just filtering one row.
    - Filter by position before ranking within a position group.
    - Use player_display_name for labeling charts/tables.
    - Default to REG season unless the user asks about playoffs.
    - For "top N" or ranking questions, sort descending and show the ranking metric plus 2-3 relevant supporting stats.
    - Always plot when the user asks to "plot," "chart," "graph," or "visualize."

    If the user asks to see the code behind a previous result, include it in
    your reply as a fenced Python code block (```python ... ```). The tool
    result's "python_code" field is safe to show as-is.

    If a follow-up request asks to modify, adjust, or iterate on a previous
    chart or analysis, include the relevant prior code (from the tool
    result's "python_code" field) in your Python tool call, along with the
    requested change, so the code can be edited rather than regenerated from
    scratch.
	'''

# Home page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# REST method for chatting with an LLM and generating a streaming SSE response
@app.route('/streaming_chat', methods=['POST'])
def streaming_chat():
    user_input = request.form.get('input')

    if not user_input or not user_input.strip():
        return Response('Input cannot be empty', status=400)

    try:
        session_id = request.headers.get('X-Session-ID') or str(uuid.uuid4())
        messages = get_chat(chats, session_id, SYSTEM_PROMPT).copy()
        messages.append({'role': 'user', 'content': user_input})

        # Generate a streaming response
        client = OpenAI()

        streaming_output = run_streaming_chat_sse(
            client,
            MODEL,
            messages,
            tools=tools_module.tools,
            tools_modules=[tools_module],
            image_dir=CHARTS_DIR
        )

        # Inline generator for streaming SSE events
        def generate():
            try:
                # Stream each chunk to the client
                for kind, payload in streaming_output:
                    if kind == 'text':
                        yield format_sse('text', payload)
                    elif kind == 'image':
                        yield format_sse('image', payload)

                # When streaming is complete, save the updated chat
                save_chat(chats, messages, session_id)

            except Exception:
                yield format_sse('text', "\n\nI'm sorry, but something went wrong.")

        response = Response(
            stream_with_context(generate()),
            mimetype='text/plain; charset=utf-8'
        )

        response.headers['X-Session-ID'] = session_id
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

    except Exception as e:
        body = format_sse('text', "\n\nI'm sorry, but something went wrong.")
        response = Response(body, mimetype='text/event-stream')
        response.headers['X-Session-ID'] = session_id
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response
    
# REST method to download an image given its ID
@app.route('/get_image')
def get_image():
    file_id = request.args.get('file_id', '').strip()

    try:
        path = CHARTS_DIR / f'{uuid.UUID(Path(file_id).stem)}.png'
    except ValueError:
        return Response(status=404)
    if not path.is_file():
        return Response(status=404)

    image_bytes = path.read_bytes()
    path.unlink() # Clean up by deleting the image file
    return Response(image_bytes, mimetype='image/png')
