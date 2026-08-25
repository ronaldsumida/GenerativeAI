import json, uuid
from pathlib import Path
from openai import OpenAI
from llm_sandbox import SandboxSession
from llm_sandbox.pool import create_pool_manager, PoolConfig

MODEL = 'gpt-5.4-mini'
CSV_FILE_NAME='nfl_player_weekly_stats_1999_2024.csv'
LOCAL_DATA_PATH = Path(__file__).resolve().parent / 'data' / CSV_FILE_NAME
SANDBOX_DATA_PATH = f'/sandbox/{CSV_FILE_NAME}'

_pool = create_pool_manager(
    backend='docker',
    config=PoolConfig(max_pool_size=3, min_pool_size=1),
    libraries=['matplotlib', 'pandas', 'numpy', 'scikit-learn'],
    lang='python'
)

# Tool function
def code_executor(user_input, image_dir):
    file_id = str(uuid.uuid4())
    filename = f'{file_id}.png'
    sandbox_image_path = f'/sandbox/{filename}'
    image_dir = Path(image_dir)
    local_path = image_dir / filename

    code = generate_code(user_input, SANDBOX_DATA_PATH, sandbox_image_path)
    image_file_id = None

    with SandboxSession(pool=_pool, lang='python') as session:
        session.copy_to_runtime(str(LOCAL_DATA_PATH), SANDBOX_DATA_PATH)
        result = session.run(code)

        try:
            session.copy_from_runtime(sandbox_image_path, str(local_path))
            if local_path.is_file() and local_path.stat().st_size > 0:
                image_file_id = file_id

        except Exception:
            if local_path.is_file():
                local_path.unlink(missing_ok=True)

        payload = {
            'stdout': result.stdout or result.stderr or '',
            'image_file_id': image_file_id,
            'python_code': code
        }

        return json.dumps(payload)

# Tool description
python_tool = {
    'type': 'function',
    'function': {
        'name': 'code_executor',
        'description': '''
            Responds to input by generating and executing Python code. Returns
            JSON with "stdout" for textual output, "image_file_id" (a UUID string
            if a chart was saved as PNG in the sandbox, or null if no image was
            generated), and "code" for the code that was generated.
            ''',
        'parameters': {
            'type': 'object',
            'properties': {
                'user_input': {
                    'type': 'string',
                    'description': 'Natural-language input describing the outcome.'
                }
            },
            'required': ['user_input']
        }
    }
}

# Helper function for generating code
def generate_code(input, sandbox_data_path, sandbox_image_path):
    prompt = f'''
        Generate Python code to respond to the following command:
        
        {input}

        The data is stored in this CSV file:

        {sandbox_data_path}

        Read that file with pandas when data is needed.        

        If you create a matplotlib figure, use a non-interactive backend
        first (e.g. import matplotlib; matplotlib.use("Agg")); then save
        ONLY to this exact path (do not change the path):
        
        {sandbox_image_path}
        
        Use plt.savefig(...) with that path, then plt.close(). If no
        chart is needed, do not call savefig. When creating charts, use
        a black background with light foreground labels and graphics unless
        directed to do otherwise. Make sure labels don't overlap each other.
        Minimum image width is 960px.

        Respond with the code only. Do not use markdown formatting.
        Do not generate code that could be harmful to the computer
        it's running on. If the request seems unsafe, respond with
        code that prints a warning message instead of performing
        the requested action.
        '''

    messages = [
        {
            'role': 'system',
            'content': 'You are an expert Python programmer.'
        },
        {
            'role': 'user',
            'content': prompt
        }
    ]

    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2
    )

    code = response.choices[0].message.content
    return code

tools=[
    python_tool
]
