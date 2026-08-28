from __future__ import annotations

import re

from typing import Any

from .schema import (
    OfficialWritingInput,
    OfficialWritingLLMResponse,
    OfficialWritingType,
    OfficialWritingValidation,
)


# =========================================================
# DATE PATTERNS
# =========================================================

_DATE_PATTERNS = [
    r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
    r"\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b",
]


# =========================================================
# LEGAL REFERENCE PATTERNS
# =========================================================

_LEGAL_PATTERNS = [
    r"\b\d{4}\s+sayılı\b",
    r"\b(?:TCK|CMK|VUK)\b\s*(?:'?[ıninunün]+)?\s*\d{1,4}\b",
    r"\bMadde\s+\d{1,4}\b",
]


# =========================================================
# VALID WRITING TYPES
# =========================================================

_VALID_WRITING_TYPES = {
    "cevap_yazisi",
    "talep_yazisi",
    "bilgilendirme_yazisi",
    "basvuru_cevabi",
}


# =========================================================
# NORMALIZE
# =========================================================

def _normalize(text: str) -> str:
   

    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip().casefold()
   

# =========================================================
# FLATTEN VALUES
# =========================================================

def _flatten_values(value: Any) -> list[str]:
   

    if value is None:
        return []
    
    if isinstance(value, dict):
        result: list[str] = []

        for item in value.values():
            result.extend(
                _flatten_values(item)
            )

        return result
   
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []

        for item in value:
            result.extend(
                _flatten_values(item)
            )

        return result

    text = str(value).strip()

    return [text] if text else []
    
# =========================================================
# COLLECT SOURCE TEXT
# =========================================================

def _collect_source_text(data: OfficialWritingInput) -> str:
  

    values = [
        data.document_type,
        data.topic,
        data.purpose,
        data.intent,
        data.summary,
        data.entities,
        data.key_information,
        data.sayi,
        data.tarih,
        data.recipient,
        data.selected_department,
        data.rag,
    ]

    flattened: list[str] = []

    for value in values:
        flattened.extend(_flatten_values(value))

    return " ".join(flattened)

# =========================================================
# FIND DATES
# =========================================================

def _find_dates(text: str) -> set[str]:
   

    found: set[str] = set()

    for pattern in _DATE_PATTERNS:
        matches = re.findall(
            pattern,
            text or "",
            flags=re.IGNORECASE,
        )

        for match in matches:
            found.add(
                _normalize(match)
            )

    return found


# =========================================================
# FIND LEGAL REFERENCES
# =========================================================

def _find_legal_references(
    text: str,
) -> set[str]:
   

    found: set[str] = set()

    for pattern in _LEGAL_PATTERNS:
        matches = re.findall(
            pattern,
            text or "",
            flags=re.IGNORECASE,
        )

        for match in matches:
            found.add(
                _normalize(match)
            )

    return found


# =========================================================
# CHECK ADDED LEGAL REFERENCES
# =========================================================

def _check_added_legal_references(
    data: OfficialWritingInput,
    body: str,
) -> list[str]:
   

    source_text = _collect_source_text(data)

    source_legal = _find_legal_references(
        source_text
    )

    body_legal = _find_legal_references(
        body
    )

    added = body_legal - source_legal

    return [
        f"Context'te bulunmayan hukuki referans: {reference}"
        for reference in sorted(added)
    ]


# =========================================================
# CHECK ADDED DATES
# =========================================================

def _check_added_dates(
    data: OfficialWritingInput,
    body: str,
) -> list[str]:
   

    source_text = _collect_source_text(data)
    #نجمع البيانات الأصلية.

    source_dates = _find_dates(
        source_text
    )
    # نستخرج التواريخ الموجودة في الـContext.

    body_dates = _find_dates(
        body
    )
    # نستخرج التواريخ الموجودة في النص الذي كتبه الـLLM.

    added = body_dates - source_dates
    # أي تاريخ موجود بالـbody وغير موجود بالـContext
    # يعتبر تاريخاً جديداً أضافه الـLLM.

    return [
        f"Context'te bulunmayan tarih: {date}"
        for date in sorted(added)
    ]
    # نرجع الخطأ باللغة التركية.


# =========================================================
# CHECK PROHIBITED TEMPLATE CONTENT
# =========================================================

def _check_prohibited_template_content(
    body: str,
) -> list[str]:
    """
    يتأكد أن الـLLM لم يحاول إنشاء أجزاء الـTemplate.
    """

    issues: list[str] = []

    prohibited_patterns = [
        (r"^\s*T\.C\.", "T.C."),
        (r"\bSayı\s*:", "Sayı"),
        (r"\bKonu\s*:", "Konu"),
        (r"\bMuhatap\s*:", "Muhatap"),
    ]
    # هذه العناصر ليست من مسؤولية الـLLM.
    #
    # الـTemplate هو الذي يتعامل معها.
    #
    # لذلك نمنع الـLLM من إنتاجها داخل body.

    for pattern, label in prohibited_patterns:
        if re.search(
            pattern,
            body,
            flags=re.IGNORECASE | re.MULTILINE,
        ):
            issues.append(
                f"LLM çıktısı Template alanını içeriyor: {label}"
            )
            # إذا وجدنا أحد عناصر الـTemplate:
            # نسجل مخالفة.

    return issues


# =========================================================
# MAIN VALIDATOR
# =========================================================

def validate_official_writing(
    data: OfficialWritingInput,
    response: OfficialWritingLLMResponse,
    writing_type: OfficialWritingType,
) -> OfficialWritingValidation:
    """
    يتحقق من نتيجة الـLLM حسب عقد Resmî Yazı الجديد.

    الـLLM مسؤول فقط عن BODY/METİN.
    """

    issues: list[str] = []
    # هنا سنجمع كل المشاكل التي نكتشفها.


    # =====================================================
    # 1. BODY
    # =====================================================

    body = (
        response.body or ""
    ).strip()
    # نأخذ body فقط.
    #
    # ما عاد عندنا:
    # response.subject
    # response.text
    #
    # لأن التصميم الجديد يعتمد على body فقط.


    # =====================================================
    # 2. EMPTY BODY CHECK
    # =====================================================

    if not body:
        issues.append(
            "Üretilen resmî yazı body alanı boş."
        )
    # إذا الـLLM لم ينتج Body:
    # النتيجة غير صالحة.


    # =====================================================
    # 3. WRITING TYPE CHECK
    # =====================================================

    if writing_type not in _VALID_WRITING_TYPES:
        issues.append(
            "Geçersiz resmî yazı türü."
        )
    # نتأكد أن نوع الكتابة واحد من الأنواع الأربعة المسموحة.


    # =====================================================
    # 4. DATE CHECK
    # =====================================================

    issues.extend(
        _check_added_dates(
            data=data,
            body=body,
        )
    )
    # نتحقق أن الـLLM لم يخترع تاريخاً.


    # =====================================================
    # 5. LEGAL REFERENCE CHECK
    # =====================================================

    issues.extend(
        _check_added_legal_references(
            data=data,
            body=body,
        )
    )
    # نتحقق أن الـLLM لم يخترع قانوناً أو مادة قانونية.


    # =====================================================
    # 6. TEMPLATE CHECK
    # =====================================================

    issues.extend(
        _check_prohibited_template_content(
            body=body,
        )
    )
    # نتأكد أن الـLLM لم يعيد كتابة أجزاء الـTemplate.


    # =====================================================
    # 7. DETERMINE VALIDATION STATUS
    # =====================================================

    hard_error_keywords = (
        "boş",
        "Geçersiz",
        "bulunmayan hukuki referans",
        "bulunmayan tarih",
        "Template alanını içeriyor",
    )
    # هذه الأخطاء تعتبر أخطاء قوية تمنع اعتماد النتيجة.


    hard_errors = [
        issue
        for issue in issues
        if any(
            keyword.casefold()
            in issue.casefold()
            for keyword in hard_error_keywords
        )
    ]
    # نبحث داخل المشاكل عن الأخطاء القوية.


    if hard_errors:
        status = "rejected"
        # إذا وجدنا خطأ قوي:
        # النتيجة مرفوضة.

    elif issues:
        status = "warning"
        # إذا في مشاكل لكنها ليست hard errors:
        # النتيجة تحذير.

    else:
        status = "passed"
        # إذا ما في أي مشكلة:
        # النتيجة ناجحة.

    # =====================================================
    # 8. RETURN VALIDATION RESULT
    # =====================================================

    return OfficialWritingValidation(
        status=status,
        issues=issues,
    )
    # نرجع نتيجة الـValidator للـAgent.