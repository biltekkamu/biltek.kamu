from __future__ import annotations 

from typing import Any, Mapping, Optional 

from .schema import OfficialWritingInput 


def _clean(value: Any) -> Any:

    if value is None:
        return None  

    if isinstance(value, str):
        value = value.strip()  
        return value or None  

    if isinstance(value, Mapping):
        cleaned = {} 

        for key, item in value.items():
            cleaned_value = _clean(item) 

            if cleaned_value is not None:
                cleaned[str(key)] = cleaned_value  

        return cleaned 

    if isinstance(value, (list, tuple)):
        return [
            cleaned_value
            for item in value
            if (cleaned_value := _clean(item)) is not None
        ]  

    return value 


def _compact_rag(
    rag_result: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:

    if not rag_result:
        return None 

    answer = _clean(rag_result.get("answer")) 

    sources = rag_result.get("sources") or []  

    compact_sources = []  

    for source in sources:
        

        if not isinstance(source, Mapping):
            continue 

        item = {
            key: _clean(source.get(key))
            for key in (
                "document_name",
                "law_number",
                "madde",
            )
            if _clean(source.get(key)) is not None
        }  

        if item:
            compact_sources.append(item) 

    if answer is None and not compact_sources:
        return None 

    return {
        "answer": answer,
        "sources": compact_sources,
    } 


def prepare_official_writing_input(
    evrak_analysis: Mapping[str, Any] | Any,
    rag_result: Optional[Mapping[str, Any]] = None,
    routing_result: Optional[Mapping[str, Any]] = None,
    ocr_result: Optional[Mapping[str, Any]] = None,
) -> OfficialWritingInput:
    

    analysis = (
        evrak_analysis.model_dump()
        if hasattr(evrak_analysis, "model_dump")
        else dict(evrak_analysis or {})
    ) 

    routing = (
        routing_result.model_dump()
        if hasattr(routing_result, "model_dump")
        else dict(routing_result or {})
    ) 

    ocr = (
        ocr_result.model_dump()
        if hasattr(ocr_result, "model_dump")
        else dict(ocr_result or {})
    ) 

    ocr_input = ocr.get("input") or {}
    metadata = ocr_input.get("metadata") or {}

    document_type = analysis.get("document_type") 

    if isinstance(document_type, Mapping):
        document_type = document_type.get("label")  

    selected_department = routing.get("selected_department")  

    if selected_department is None:
        selected_department = routing.get("recommended_unit")  

    data = {
        # =========================
        # Evrak Analysis
        # =========================

        "document_type": _clean(document_type), 

        "topic": _clean(
            analysis.get("topic")
            or analysis.get("subject")
            or metadata.get("konu")
        ), 

        "purpose": _clean(
            analysis.get("purpose")
        ), 

        "intent": _clean(
            analysis.get("intent")
        ), 

        "summary": _clean(
            analysis.get("summary")
        ), 

        "entities": _clean(
            analysis.get("entities") or {}
        ), 

        "key_information": _clean(
            analysis.get("key_information") or {}
        ),  

        # =========================
        # OCR Metadata
        # =========================

        "sayi": _clean(metadata.get("sayi") or analysis.get("entities", {}).get("sayi")),
        "tarih": _clean(metadata.get("tarih") or analysis.get("entities", {}).get("tarih")),
        "recipient": _clean(metadata.get("muhatap") or analysis.get("entities", {}).get("muhatap")),

        # =========================
        # Routing
        # =========================

        "selected_department": _clean(
            selected_department
        ), 

        # =========================
        # RAG
        # =========================

        "rag": _compact_rag(
            rag_result
        ), 
    }

   
    return OfficialWritingInput(
        **data
    )  


def render_context(
    data: OfficialWritingInput,
) -> str:

    labels = {
        "document_type": "Belge Türü",  
        "topic": "Konu",  
        "purpose": "Amaç",  
        "intent": "Intent",  
        "summary": "Özet",  
        "entities": "Varlıklar", 
        "key_information": "Önemli Bilgiler", 
        "sayi": "Sayı", 
        "tarih": "Tarih", 
        "recipient": "Muhatap",  
        "selected_department": "Yönlendirilen Birim",
        "rag": "RAG Legal Basis", 
    }

    lines = [
        "### RESMÎ YAZI İÇİN YAPILANDIRILMIŞ BAĞLAM ###"
    ]  

    for key, label in labels.items():

        value = getattr(data, key, None) 

        if value is not None and value != {}:
            lines.append(
                f"- {label}: {value}"
            ) 

    lines.append(
        "### KULLANIM KURALLARI ###"
    )  

    lines.append(
        "Yalnızca yukarıdaki Structured Data ve mevcut RAG bilgilerini kullan."
    )  

    lines.append(
        "Context'te bulunmayan Sayı, Tarih, Kurum, Birim, kişi veya hukuki referans üretme."
    ) 

    lines.append(
        "RAG mevcutsa yalnızca verilen hukuki dayanağı kullan."
    )  

    lines.append(
        "Template'in sabit bölümlerini oluşturma veya değiştirme."
    )  

    lines.append(
        "Yalnızca Template içinde kullanılacak BODY/METİN içeriğini üret."
    ) 

    return "\n".join(lines) 