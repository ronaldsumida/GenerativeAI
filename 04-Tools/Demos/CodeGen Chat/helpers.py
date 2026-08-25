import json
import inspect

# Helper function for retrieving chats
def get_chat(chats, session_id, system_prompt):
    messages = chats.get(session_id, None)

    if not messages:
        messages = [{ 'role': 'system', 'content': system_prompt }]

    return messages

# Helper function for trimming chats
def save_chat(chats, messages, session_id, max_turns=10):
    system_msg = None

    if messages and messages[0].get('role') == 'system':
        system_msg = messages[0]
        messages = messages[1:]

    # Split into turns, each starting with a user message
    turns = []
    current_turn = []

    for msg in messages:
        if msg.get('role') == 'user' and current_turn:
            turns.append(current_turn)
            current_turn = []
        current_turn.append(msg)

    if current_turn:
        turns.append(current_turn)

    # Keep only the last max_turns turns
    trimmed = [msg for turn in turns[-max_turns:] for msg in turn]

    chats[session_id] = [system_msg] + trimmed if system_msg else trimmed

# Helper function for running a streaming chat with SSE. Yields ('text', chunk)
# for output text and ('image', file_id) for tool-generated images.
def run_streaming_chat_sse(client, model, messages, tools=None, tools_modules=None, image_dir=None, max_iterations=10):
    for _ in range(max_iterations):
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or [],
            stream=True
        )

        full_message = { 'role': 'assistant', 'content': '' }
        tool_calls = []

        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta

                if delta and delta.content:
                    full_message['content'] += delta.content
                    yield ('text', delta.content)

                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if len(tool_calls) <= tc_delta.index:
                            tool_calls.append(
                                {'type': 'function', 'function': {'arguments': '', 'name': ''}}
                            )

                        tc = tool_calls[tc_delta.index]

                        if tc_delta.function.name:
                            tc['function']['name'] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tc['function']['arguments'] += tc_delta.function.arguments
                        if tc_delta.id:
                            tc['id'] = tc_delta.id

        if tool_calls:
            full_message['tool_calls'] = tool_calls
            full_message['content'] = None
            messages.append(full_message)

            for tool_call in tool_calls:
                result = exec_tool_call(
                    tool_call['function']['name'],
                    tool_call['function']['arguments'],
                    tools_modules=tools_modules,
                    image_dir=image_dir
                )

                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, dict):
                        image_file_id = parsed.get('image_file_id')

                        # Send an SSE "image" event if an image was created
                        if image_file_id:
                            yield ('image', image_file_id)

                except (json.JSONDecodeError, TypeError):
                    pass

                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call['id'],
                    'content': result,
                })

            continue

        # No (more) tool calls requested. Return the final result.
        messages.append(full_message)
        return

    raise RuntimeError('max_iterations exceeded while processing tool calls')

# Helper function to format one SSE event
def format_sse(event, data):
    data = data.replace('\r\n', '\n').replace('\r', '\n')
    return ''.join(
        [f'event: {event}\n'] +
        [f'data: {line}\n' for line in data.split('\n')] +
        ['\n']
    )

# Helper function for executing tool calls
def exec_tool_call(function_name, function_args, tools_modules, image_dir=None):
    try:
        if isinstance(function_args, str):
            function_args = json.loads(function_args)

        func = None
        for module in (tools_modules or []):
            func = getattr(module, function_name, None)
            if func:
                break

        if not func:
            return f'Unknown function: {function_name}'

        formatted_args = ', '.join(f'{k}={repr(v)}' for k, v in function_args.items())
        print(f'\033[93mCalling {function_name}({formatted_args})\033[0m')

        # image_dir is application configuration, not an LLM-visible argument
        if 'image_dir' in inspect.signature(func).parameters:
            function_args['image_dir'] = image_dir

        result = func(**function_args)

        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'Error executing {function_name}: {str(e)}'
