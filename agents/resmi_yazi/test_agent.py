import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from agents.resmi_yazi.agent import generate_official_writing

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MOCK_FILE = BASE_DIR / "tests" / "mock_data" / "test.json"


def main():
    # 1. قراءة بيانات الاختبار
    with open(MOCK_FILE, "r", encoding="utf-8") as f:
        mock = json.load(f)

    # 2. إنشاء LLM السحابي (Evren llm-large)
    llm = ChatOpenAI(
        model="llm-large",
        api_key=os.getenv("EVREN_API_KEY", "sk-evren-team03-6409be56daaf89d55f82a4a9f12b10f1"),
        base_url=os.getenv("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1"),
        temperature=0.0,
        timeout=60.0,
    )

    # 3. تشغيل Resmî Yazı Agent
    result = generate_official_writing(
        evrak_analysis=mock["evrak_analysis"],
        rag_result=mock.get("rag"),
        routing_result=mock.get("routing"),
        llm_client=llm,
    )

    # 4. طباعة النتيجة
    print("\n========== RESULT ==========")

    print("TYPE:")
    print(result.official_writing.type)

    print("\nBODY:")
    print(result.official_writing.body)

    print("\nVALIDATION:")
    print(result.official_writing.validation.model_dump())

    print("\nCONFIDENCE:")
    print(result.official_writing.confidence)


if __name__ == "__main__":
    main()