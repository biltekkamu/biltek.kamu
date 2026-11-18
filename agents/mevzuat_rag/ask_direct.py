import chromadb
from sentence_transformers import SentenceTransformer
from ollama import Client

# تهيئة
embedder    = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
chroma      = chromadb.PersistentClient(path="chroma_db")
collection  = chroma.get_collection("project_laws")
ollama      = Client(host="http://127.0.0.1:11434")

SYSTEM = """Sen Türk kamu mevzuatı konusunda uzman bir hukuki asistansın.
Yalnızca verilen kaynaklardaki bilgileri kullan.
Kaynaklarda bulunmayan bilgi üretme."""

print(f"✅ Hazır — {collection.count()} chunk yüklendi\n")

while True:
    soru = input("Soru (q=çıkış): ").strip()
    if soru.lower() in ["q", "quit", "exit"]:
        break

    # Retrieval
    vec     = embedder.encode(soru, normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=[vec], n_results=5)
    context = "\n\n---\n\n".join(results["documents"][0])

    # Generation
    response = ollama.chat(
        model="gemma3:4b",
        messages=[
            {"role": "system", "content": f"{SYSTEM}\n\nKAYNAKLAR:\n{context}"},
            {"role": "user",   "content": soru},
        ]
    )

    print(f"\nCevap: {response.message.content}\n")