import chromadb, os, logging
from sentence_transformers import CrossEncoder

# Suppress HuggingFace/transformers warnings
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)

# Load the vector database
client = chromadb.PersistentClient('chroma')
collection = client.get_collection(name='Electric_Vehicles')

# Load a cross encoder for reranking
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# Tool for querying the knowledge base
def query_knowledge_base(question: str) -> str:
    try:
        # Query the vector database for up to 10 chunks
        print('\033[92mQuerying the knowledge base\033[0m')

        results = collection.query(
            query_texts=[question],
            n_results=10
        )

        # Use the cross encoder to identify the 5 best matches and return them as context
        print('\033[92mReranking the results\033[0m')
        documents = results['documents'][0]
        ranked_documents = reranker.rank(question, documents, return_documents=True, top_k=5)

        # Combine the results into one string
        return '\n\n'.join(x['text'] for x in ranked_documents)

    except Exception as e:
        return f'Query knowledge base failed ({e})'

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

# Helper function that retrieves and reranks chunks, returning them as a list
def retrieve_chunks(question: str, n_results: int = 10, top_k: int = 5) -> list[str]:
    results = collection.query(query_texts=[question], n_results=n_results)
    documents = results['documents'][0]
    ranked_documents = reranker.rank(question, documents, return_documents=True, top_k=top_k)
    return [x['text'] for x in ranked_documents]
