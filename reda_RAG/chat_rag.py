import sys
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="RAG AI Web API")

class QueryModel(BaseModel):
    question: str


DB_DIR = "chroma_db"
SERVER_IP = "" 

print("Vektör modeli yükleniyor")
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

chroma_client = chromadb.PersistentClient(path=DB_DIR)
collection = chroma_client.get_collection(name="project_laws")

client = OpenAI(
    base_url=f"http://{SERVER_IP}:8080/v1",
    api_key="no-key-required"
)

print("\n RAG Web API Sistemi Hazır!")
print("--------------------------------------------------")

@app.post("/query")
def query_rag(item: QueryModel):
    query = item.question
    

    query_vector = embedding_model.encode(query).tolist()
    results = collection.query(query_embeddings=[query_vector], n_results=3)
    
    context = "\n\n".join(results['documents'][0])
    
    system_prompt = (
        "Sen yardımcı bir asistansın. Aşağıdaki belgelere dayanarak kullanıcının sorusuna Türkçe cevap ver. "
        "Cevabın net olsun ve belgede olmayan bilgileri ekleme.\n\n"
        f"--- BELGELER ---\n{context}\n----------------"
    )
    
    try:
        response = client.chat.completions.create(
            model="google_gemma-3-4b-it-Q8_0.gguf",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2
        )
     
        return {"answer": response.choices[0].message.content}
        
    except Exception as e:
        print(f"\n Sunucu Bağlantı Hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Sunucu Bağlantı Hatası: {str(e)}")

if __name__ == "__main__":
   
    uvicorn.run(app, host="0.0.0.0", port=8000)