from __future__ import annotations

import json
import os
import requests
from typing import Any, Mapping, Optional

from .context_builder import prepare_official_writing_input
from .prompt import SYSTEM_PROMPT, build_official_writing_prompt
from .schema import (
    OfficialWritingAgentResult,
    OfficialWritingInput,
    OfficialWritingLLMResponse,
    OfficialWritingPayload,
    OfficialWritingType,
)
from .validator import validate_official_writing


# =========================================================
# EVREN API
# =========================================================

DEFAULT_EVREN_API_KEY = os.getenv("EVREN_API_KEY")

DEFAULT_EVREN_BASE_URL = os.getenv(
    "EVREN_BASE_URL",
    "https://evren-llmapi.ssyz.org.tr/v1",
)


def call_evren_api_direct(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = "llm-large",
    temperature: float = 0.0,
) -> str:

    endpoint = (
        f"{DEFAULT_EVREN_BASE_URL.rstrip('/')}"
        "/chat/completions"
    )

    headers = {
        "Authorization": f"Bearer {DEFAULT_EVREN_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    try:

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=60,
        )

        response.raise_for_status()

        res_data = response.json()

        return (
            res_data["choices"][0]
            ["message"]["content"]
        )

    except Exception as error:

        raise RuntimeError(
            f"Evren API direct call failed: {error}"
        ) from error


# =========================================================
# LLM RESPONSE NORMALIZATION
# =========================================================

def _coerce_response(
    raw: Any,
) -> OfficialWritingLLMResponse:

    if isinstance(
        raw,
        OfficialWritingLLMResponse,
    ):
        return raw

    if hasattr(
        raw,
        "model_dump",
    ):
        return OfficialWritingLLMResponse.model_validate(
            raw.model_dump()
        )

    if isinstance(
        raw,
        Mapping,
    ):
        return OfficialWritingLLMResponse.model_validate(
            raw
        )

    if hasattr(
        raw,
        "content",
    ):
        raw = raw.content

    if isinstance(
        raw,
        str,
    ):

        text = raw.strip()

        if text.startswith(
            "```json"
        ):
            text = text[7:]

        if text.startswith(
            "```"
        ):
            text = text[3:]

        if text.endswith(
            "```"
        ):
            text = text[:-3]

        text = text.strip()

        try:

            parsed = json.loads(
                text
            )

            if (
                isinstance(parsed, dict)
                and "body" in parsed
            ):

                return OfficialWritingLLMResponse.model_validate(
                    parsed
                )

            return OfficialWritingLLMResponse(
                body=text
            )

        except Exception:

            return OfficialWritingLLMResponse(
                body=text
            )

    raise ValueError(
        "LLM yanıtı beklenen formatta değil."
    )


# =========================================================
# GENERATOR
# =========================================================

class OfficialWritingGenerator:

    def __init__(
        self,
        llm_client: Optional[Any] = None,
    ):
        self.llm_client = llm_client


    def generate(
        self,
        data: OfficialWritingInput,
        writing_type: OfficialWritingType,
    ) -> OfficialWritingLLMResponse:

        prompt = build_official_writing_prompt(
            data,
            writing_type,
        )

        # LangChain client varsa
        if (
            self.llm_client
            and hasattr(
                self.llm_client,
                "invoke",
            )
        ):

            from langchain_core.messages import (
                HumanMessage,
                SystemMessage,
            )

            response = self.llm_client.invoke(
                [
                    SystemMessage(
                        content=SYSTEM_PROMPT
                    ),
                    HumanMessage(
                        content=prompt
                    ),
                ]
            )

            return _coerce_response(
                response
            )

        # Direct Evren API
        raw_text = call_evren_api_direct(
            prompt=prompt
        )

        return _coerce_response(
            raw_text
        )


# =========================================================
# WRITING TYPE
# =========================================================

_TYPE_BY_INTENT = {

    "basvuru_cevabi":
        "basvuru_cevabi",

    "basvuru_cevap":
        "basvuru_cevabi",

    "cevap":
        "cevap_yazisi",

    "cevap_yazisi":
        "cevap_yazisi",

    "talep":
        "talep_yazisi",

    "talep_yazisi":
        "talep_yazisi",

    "izin_talebi":
        "talep_yazisi",

    "bilgilendirme":
        "bilgilendirme_yazisi",

    "bilgilendirme_yazisi":
        "bilgilendirme_yazisi",
}


def determine_writing_type(
    document_type: Optional[str],
    purpose: Optional[str],
    intent: Optional[str],
    selected_department: Optional[str],
) -> OfficialWritingType:

    normalized_intent = (
        intent or ""
    ).strip().casefold()

    if normalized_intent in _TYPE_BY_INTENT:

        return _TYPE_BY_INTENT[
            normalized_intent
        ]

    text = " ".join(
        part.casefold()
        for part in (
            document_type,
            purpose,
            intent,
            selected_department,
        )
        if part
    )

    if any(
        token in text
        for token in (
            "başvuru cev",
            "başvuruya cevap",
            "başvuru cevabı",
        )
    ):
        return "basvuru_cevabi"

    if any(
        token in text
        for token in (
            "cevap",
            "yanıt",
        )
    ):
        return "cevap_yazisi"

    if any(
        token in text
        for token in (
            "talep",
            "istem",
            "izin",
        )
    ):
        return "talep_yazisi"

    return "bilgilendirme_yazisi"


# =========================================================
# VALIDATION CONFIDENCE
# =========================================================

def _validation_confidence(
    status: str,
) -> float:

    if status == "rejected":
        return 0.0

    if status == "warning":
        return 0.75

    return 0.93


# =========================================================
# RESMI YAZI AGENT
# =========================================================

class ResmiYaziAgent:

    def __init__(
        self,
        llm_client: Optional[Any] = None,
    ):

        self.generator = OfficialWritingGenerator(
            llm_client
        )


    def generate(
        self,
        evrak_analysis: Mapping[str, Any] | Any,
        ocr_result: Mapping[str, Any] | Any | None = None,
        rag_result: Optional[Mapping[str, Any]] = None,
        routing_result: Optional[Mapping[str, Any]] = None,

        # Kullanıcı isterse bunları manuel seçebilir
        writing_type: Optional[
            OfficialWritingType
        ] = None,

        recipient: Optional[str] = None,

    ) -> OfficialWritingAgentResult:

        if evrak_analysis is None:

            raise ValueError(
                "evrak_analysis boş olamaz."
            )

        # -------------------------------------------------
        # Structured data oluştur
        # -------------------------------------------------

        data = prepare_official_writing_input(
            evrak_analysis=evrak_analysis,
            ocr_result=ocr_result,
            rag_result=rag_result,
            routing_result=routing_result,
        )

        # -------------------------------------------------
        # Kullanıcı Muhatap verdiyse mevcut değerin
        # üzerine yaz
        # -------------------------------------------------

        if (
            recipient
            and recipient.strip()
        ):

            data = data.model_copy(
                update={
                    "recipient":
                        recipient.strip()
                }
            )

        # -------------------------------------------------
        # Writing type
        #
        # Kullanıcı seçtiyse:
        #     onun seçimini kullan.
        #
        # Seçmediyse:
        #     eski otomatik sistem devam etsin.
        # -------------------------------------------------

        if writing_type:

            selected_writing_type = (
                writing_type
            )

        else:

            selected_writing_type = (
                determine_writing_type(
                    document_type=
                        data.document_type,

                    purpose=
                        data.purpose,

                    intent=
                        data.intent,

                    selected_department=
                        data.selected_department,
                )
            )

        # -------------------------------------------------
        # LLM BODY oluştur
        # -------------------------------------------------

        response = self.generator.generate(
            data=data,
            writing_type=
                selected_writing_type,
        )

        # -------------------------------------------------
        # Validation
        # -------------------------------------------------

        validation = (
            validate_official_writing(
                data=data,
                response=response,
                writing_type=
                    selected_writing_type,
            )
        )

        # -------------------------------------------------
        # Body
        # -------------------------------------------------

        body = (
            response.body.strip()
            if response.body
            else ""
        )

        # -------------------------------------------------
        # Subject
        # -------------------------------------------------

        subject = (
            getattr(
                data,
                "topic",
                None,
            )
            or "Resmi Yazı"
        )

        # -------------------------------------------------
        # Final Payload
        # -------------------------------------------------

        payload = OfficialWritingPayload(

            generated=(
                bool(body)
                and
                validation.status
                != "rejected"
            ),

            type=
                selected_writing_type,

            subject=
                subject,

            body=
                body or None,

            confidence=
                _validation_confidence(
                    validation.status
                ),

            validation=
                validation,
        )

        return OfficialWritingAgentResult(
            official_writing=payload
        )


# =========================================================
# PUBLIC HELPER
# =========================================================

def generate_official_writing(
    evrak_analysis: Mapping[str, Any] | Any,
    ocr_result: Mapping[str, Any] | Any | None = None,
    rag_result: Optional[Mapping[str, Any]] = None,
    routing_result: Optional[Mapping[str, Any]] = None,
    *,
    writing_type: Optional[
        OfficialWritingType
    ] = None,
    recipient: Optional[str] = None,
    llm_client: Optional[Any] = None,
) -> OfficialWritingAgentResult:

    return ResmiYaziAgent(
        llm_client=llm_client
    ).generate(

        evrak_analysis=
            evrak_analysis,

        ocr_result=
            ocr_result,

        rag_result=
            rag_result,

        routing_result=
            routing_result,

        writing_type=
            writing_type,

        recipient=
            recipient,
    )