from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowState:
    document_id: Optional[str] = None

    input_type: Optional[str] = None
    user_question: Optional[str] = None
    file_path: Optional[str] = None

    status: str = "created"
    current_step: str = "router"

    raw_text: Optional[str] = None

    analysis: Dict[str, Any] = field(default_factory=dict)

    missing_information: List[str] = field(default_factory=list)

    rag_result: Dict[str, Any] = field(default_factory=dict)

    official_letter: Dict[str, Any] = field(default_factory=dict)

    routing_result: Dict[str, Any] = field(default_factory=dict)

    errors: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)


def create_state(
    input_type: str,
    document_id: Optional[str] = None,
    user_question: Optional[str] = None,
    file_path: Optional[str] = None,
) -> WorkflowState:

    return WorkflowState(
        document_id=document_id,
        input_type=input_type,
        user_question=user_question,
        file_path=file_path,
    )


if __name__ == "__main__":

    state = create_state(
        input_type="document_question",
        document_id="doc_001",
        user_question="Bu evrak hangi suçla ilgili?",
        file_path="test.pdf",
    )

    print(state)