import json
from ddgs import DDGS

# Tools for online search
def web_search(query, max_results=5):
    with DDGS() as ddgs:
        results = ddgs.text(query=query, max_results=max_results)

    return json.dumps(results)

def news_search(query, max_results=5):
    with DDGS() as ddgs:
        results = ddgs.news(query=query, max_results=max_results)

    return json.dumps(results)

# Tool descriptions
web_search_tool = {
    'type': 'function',
    'function': {
        'name': 'web_search',
        'description': '''
            Searches the Web for answers to questions.
            ''',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The topic to search for.'
                },
                'max_results': {
                    'type': 'number',
                    'description': 'Maximum number of results to return (default=5).'
                }
            },
            'required': ['query']
        }
    }
}

news_search_tool = {
    'type': 'function',
    'function': {
        'name': 'news_search',
        'description': '''
            Searches the Web for the latest news.
            ''',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The topic of the news search.'
                },
                'max_results': {
                    'type': 'number',
                    'description': 'Maximum number of results to return (default=5).'
                }
            },
            'required': ['query']
        }
    }
}

tools=[
    web_search_tool,
    news_search_tool
]