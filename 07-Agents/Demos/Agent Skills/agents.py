from datetime import date
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.skills import Skills, LocalSkills
from agno.tools.websearch import WebSearchTools
from tools import list_outlook_folder, get_outlook_messages

MODEL = "gpt-5.4-mini"

INSTRUCTIONS = [
    "You are a travel assistant that helps users turn travel correspondence into a practical itinerary.",
    "Use the available skills when they match the user's request instead of improvising a workflow.",
    "Use web_search for visa/entry-requirement research only when the visa-entry-requirements skill calls for current Web research, or when the user explicitly asks you to search the Web.",
    "Never invent reservation details, confirmation numbers, times, addresses, bookings, visa requirements, or entry requirements.",
    "Keep ordinary chat responses concise and skimmable.",
    f"Today's date is {date.today().isoformat()}.",
]

def create_agent(session_id, db):
    agent = Agent(
        model=OpenAIChat(id=MODEL),
        session_id=session_id,
        db=db,
        add_history_to_context=True,
        num_history_runs=12,
        tools=[
            list_outlook_folder,
            get_outlook_messages,
            WebSearchTools(enable_news=False, fixed_max_results=6),
        ],
        skills=Skills(loaders=[LocalSkills("skills")]),
        tool_hooks=[function_hook],
        instructions=INSTRUCTIONS,
        markdown=True,
    )
    return agent


def function_hook(function_name, function_call, arguments):
    args_str = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
    print(f"\x1b[33mCalling {function_name}({args_str})\x1b[0m")
    return function_call(**arguments)
