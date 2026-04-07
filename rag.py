from transformers import AutoTokenizer, pipeline
from sentence_transformers import SentenceTransformer
import chromadb
import uuid

tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en")
model = SentenceTransformer("BAAI/bge-small-en")

session_collections = {}

def extract_text(file_name):
    with open(file_name, "r", encoding="utf-8") as file:
        text = file.read()
    return text


def chunk_text(file_name, chunk_size=250, overlap=50):
    text = extract_text(file_name)

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            chunks.append(current_chunk)
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def get_collection(session_id):
    if session_id not in session_collections:
        client = chromadb.Client()
        session_collections[session_id] = client.create_collection(
            name=f"text_chunks_{session_id}"
        )
    return session_collections[session_id]


def reset_session(session_id):
    if session_id in session_collections:
        del session_collections[session_id]


def add_collection(file_name, session_id):
    chunks = chunk_text(file_name)
    embeddings = model.encode(chunks, normalize_embeddings=True)

    collection = get_collection(session_id)

    ids = [f"id_{i}" for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks
    )


def search(file_name, query, session_id, top_k=3, threshold=0.6):

    collection = get_collection(session_id)

    if collection.count() == 0:
        add_collection(file_name, session_id)

    embed_query = model.encode(query, normalize_embeddings=True)

    results = collection.query(
        query_embeddings=[embed_query],
        n_results=top_k,
        include=["documents", "distances"]
    )

    filtered_docs = []

    for doc, dist in zip(
        results["documents"][0],
        results["distances"][0]
    ):
        similarity = 1 - dist

        if similarity >= threshold:
            filtered_docs.append(doc)

    return filtered_docs