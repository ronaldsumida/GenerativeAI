import chromadb, uuid
from pypdf import PdfReader

# Create a persistent ChromaDB database in the "chroma" subdirectory
client = chromadb.PersistentClient('chroma')
collection = client.create_collection(name='Electric_Vehicles')

# How many words to take from neighboring pages
OVERLAP_WORDS = 25

# Extract text from the PDFs and add them to the database
file_names = [
    'electric_vehicles.pdf',
    'pev_consumer_handbook.pdf',
    'department-for-transport-ev-guide.pdf'
]

for file in file_names:
    print(f'Processing {file}')
    reader = PdfReader(file)

    # Extract all pages up front so we can reference neighbors
    pages = [page.extract_text() or '' for page in reader.pages]

    for i, text in enumerate(pages):
        # Take the last OVERLAP_WORDS words from the preceding page
        prefix = ' '.join(pages[i - 1].split()[-OVERLAP_WORDS:]) if i > 0 else ''

        # Take the first OVERLAP_WORDS words from the succeeding page
        suffix = ' '.join(pages[i + 1].split()[:OVERLAP_WORDS]) if i < len(pages) - 1 else ''

        chunk = f'{prefix} {text} {suffix}'.strip()

        collection.add(
            documents=[chunk],
            metadatas=[{ 'file': file, 'page': i }],
            ids=[uuid.uuid4().hex]
        )