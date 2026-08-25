# Tool for querying the knowledge base
def query_knowledge_base(question: str) -> str:
    response = '''
        Electric vehicles (EVs) use electricity as their primary fuel
        or to improve  the efficiency of conventional vehicle designs.
        EVs include all-electric vehicles, also referred to as battery
        electric vehicles (BEVs), and plug-in hybrid electric vehicles
        (PHEVs). In colloquial references, these vehicles are called
        electric cars, or simply EVs, even though some of these vehicles
        still use liquid fuels in conjunction with electricity.
        '''

    return response

# Tool description
knowledge_base_tool = {
    'type': 'function',
    'function': {
        'name': 'query_knowledge_base',
        'description': '''
            Searches a knowledge base and returns relevant context about electric vehicles.
            Always call this tool before answering any question about electric vehicles.
            ''',
        'parameters': {
            'type': 'object',
            'properties': {
                'question': {
                    'type': 'string',
                    'description': 'Natural-language input from the user.'
                }
            },
            'required': ['question']
        }
    }
}

tools = [
    knowledge_base_tool
]
