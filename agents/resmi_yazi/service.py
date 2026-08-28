from __future__ import annotations  

import json 
import os
from typing import Any, Mapping, Optional 

from .prompt import SYSTEM_PROMPT, build_official_writing_prompt 
from .schema import ( 
    OfficialWritingInput, 
    OfficialWritingLLMResponse, 
    OfficialWritingType,  
)

DEFAULT_EVREN_API_KEY = os.getenv("EVREN_API_KEY")
DEFAULT_EVREN_BASE_URL = os.getenv("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1")


def get_evren_llm_client(
    model_name: str = "llm-large",
    api_key: str = DEFAULT_EVREN_API_KEY,
    base_url: str = DEFAULT_EVREN_BASE_URL,
    temperature: float = 0.0,
) -> Any:
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            timeout=60.0,
        )
    except ImportError:
        raise ImportError(
        )


def _message_payload(system_prompt: str, human_prompt: str):
    try:
        from langchain_core.messages import HumanMessage, SystemMessage  

        return [
            SystemMessage(content=system_prompt), 
            HumanMessage(content=human_prompt), 
        ]
    except ImportError:
        return human_prompt  


def _coerce_response(raw: Any) -> OfficialWritingLLMResponse:

    if isinstance(raw, OfficialWritingLLMResponse):
        return raw 

    if hasattr(raw, "model_dump"):
        return OfficialWritingLLMResponse.model_validate(
            raw.model_dump() 
        )

    if isinstance(raw, Mapping):
        return OfficialWritingLLMResponse.model_validate(raw)  

    if hasattr(raw, "content"):
        raw = raw.content  

    if isinstance(raw, str):
        text = raw.strip() 

        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return OfficialWritingLLMResponse.model_validate(
                json.loads(text)  
            )
        except Exception as exc:
            raise ValueError(
                "LLM yanıtı geçerli JSON/structured output değil."
            ) from exc 

    raise ValueError(
        "LLM yanıtı beklenen formatta değil."
    ) 


class OfficialWritingGenerator:

    def __init__(self, llm_client: Optional[Any] = None):
        if llm_client is None:
            llm_client = get_evren_llm_client()

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

        if hasattr(self.llm_client, "with_structured_output"):

            structured_llm = self.llm_client.with_structured_output(
                OfficialWritingLLMResponse
            )  

            response = structured_llm.invoke(
                _message_payload(
                    SYSTEM_PROMPT,  
                    prompt, 
                )
            )  

        else:
            response = self.llm_client.invoke(
                _message_payload(SYSTEM_PROMPT, prompt)
            )

        return _coerce_response(response) 


def generate_official_writing(
    input_data: OfficialWritingInput, 
    writing_type: OfficialWritingType, 
    llm_client: Optional[Any] = None,  
) -> OfficialWritingLLMResponse:

    return OfficialWritingGenerator(llm_client).generate(
        input_data,
        writing_type,
    )  