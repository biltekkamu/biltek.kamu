from typing import List, Dict, Any
from models import ValidationIssue, IssueType, Severity

class RAGValidator:
    @staticmethod
    def validate(rag_block: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not isinstance(rag_block, dict):
            return issues

        answer = rag_block.get("answer")
        sources = rag_block.get("sources", [])

        if answer and (not sources or len(sources) == 0):
            issues.append(
                ValidationIssue(
                    field="rag.sources",
                    type=IssueType.MISSING_SOURCE,
                    severity=Severity.HIGH,
                    message="RAG cevabı üretildi ancak dayanak gösterilen kaynak listesi boş."
                )
            )

        return issues