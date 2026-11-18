from __future__ import annotations
# يسمح باستخدام type hints الحديثة مثل list[str] و set[str] بشكل آمن.

import re
# مكتبة Regular Expressions لفحص التواريخ والمراجع القانونية
# والتأكد من عدم ظهور أجزاء من الـTemplate داخل الـbody.

from typing import Any
# Any تسمح للدوال بالتعامل مع قيم من أنواع مختلفة.

from .schema import (
    OfficialWritingInput,
    OfficialWritingLLMResponse,
    OfficialWritingType,
    OfficialWritingValidation,
)
# نستورد الـSchemas الخاصة بالـResmi Yazı:
# OfficialWritingInput = البيانات الداخلة للـAgent.
# OfficialWritingLLMResponse = النتيجة التي يرجعها الـLLM.
# OfficialWritingType = أنواع الكتابات الرسمية المسموحة.
# OfficialWritingValidation = نتيجة عملية التحقق.


# =========================================================
# DATE PATTERNS
# =========================================================

_DATE_PATTERNS = [
    r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
    r"\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b",
]
# هذه الأنماط تبحث عن التواريخ داخل النص.
#
# أمثلة:
# 25.08.2026
# 25/08/2026
# 25-08-2026
# 2026-08-25
#
# الهدف:
# التأكد أن الـLLM لم يخترع تاريخاً غير موجود في الـContext.


# =========================================================
# LEGAL REFERENCE PATTERNS
# =========================================================

_LEGAL_PATTERNS = [
    r"\b\d{4}\s+sayılı\b",
    r"\b(?:TCK|CMK|VUK)\b\s*(?:'?[ıninunün]+)?\s*\d{1,4}\b",
    r"\bMadde\s+\d{1,4}\b",
]
# هذه الأنماط تبحث عن المراجع القانونية.
#
# أمثلة:
# 657 sayılı
# TCK 123
# CMK 100
# VUK 213
# Madde 10
#
# الهدف:
# إذا الـLLM أضاف قانوناً أو مادة غير موجودة بالـRAG/Context
# نعتبر ذلك اختراعاً للمعلومة القانونية.


# =========================================================
# VALID WRITING TYPES
# =========================================================

_VALID_WRITING_TYPES = {
    "cevap_yazisi",
    "talep_yazisi",
    "bilgilendirme_yazisi",
    "basvuru_cevabi",
}
# هذه هي أنواع الكتابة الرسمية المسموحة فقط.
#
# الـAgent لا يستطيع إنشاء نوع جديد من عنده.


# =========================================================
# NORMALIZE
# =========================================================

def _normalize(text: str) -> str:
    """
    يوحّد النص حتى تصبح المقارنة بين النصوص أسهل.
    """

    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip().casefold()
    # يحوّل المسافات المتعددة إلى مسافة واحدة.
    # يحذف الفراغات من البداية والنهاية.
    # casefold يجعل المقارنة غير حساسة لحالة الأحرف.


# =========================================================
# FLATTEN VALUES
# =========================================================

def _flatten_values(value: Any) -> list[str]:
    """
    يحوّل القيم المتداخلة داخل dict/list إلى قائمة نصوص بسيطة.
    """

    if value is None:
        return []
    # إذا القيمة غير موجودة، نرجع قائمة فارغة.

    if isinstance(value, dict):
        result: list[str] = []

        for item in value.values():
            result.extend(
                _flatten_values(item)
            )

        return result
    # إذا كانت القيمة Dictionary:
    # ندخل إلى القيم الموجودة بداخله ونستخرجها بشكل recursive.

    if isinstance(value, (list, tuple, set)):
        result: list[str] = []

        for item in value:
            result.extend(
                _flatten_values(item)
            )

        return result
    # نفس الشيء إذا كانت القيمة List أو Tuple أو Set.

    text = str(value).strip()

    return [text] if text else []
    # أي قيمة عادية نحولها إلى String.
    # وإذا كانت فارغة لا نضيفها.


# =========================================================
# COLLECT SOURCE TEXT
# =========================================================

def _collect_source_text(data: OfficialWritingInput) -> str:
    """
    يجمع كل المعلومات الموجودة في Structured Data وRAG
    ضمن نص واحد حتى يستخدمها الـvalidator للمقارنة.
    """

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
    """
    يستخرج جميع التواريخ الموجودة داخل النص.
    """

    found: set[str] = set()

    for pattern in _DATE_PATTERNS:
        matches = re.findall(
            pattern,
            text or "",
            flags=re.IGNORECASE,
        )
        # نبحث عن التواريخ باستخدام الأنماط السابقة.

        for match in matches:
            found.add(
                _normalize(match)
            )
            # نضيف التاريخ بعد توحيد شكله.

    return found


# =========================================================
# FIND LEGAL REFERENCES
# =========================================================

def _find_legal_references(
    text: str,
) -> set[str]:
    """
    يستخرج المراجع القانونية الموجودة في النص.
    """

    found: set[str] = set()

    for pattern in _LEGAL_PATTERNS:
        matches = re.findall(
            pattern,
            text or "",
            flags=re.IGNORECASE,
        )
        # نبحث عن كل نوع من المراجع القانونية.

        for match in matches:
            found.add(
                _normalize(match)
            )
            # نضيف المرجع القانوني بعد توحيده.

    return found


# =========================================================
# CHECK ADDED LEGAL REFERENCES
# =========================================================

def _check_added_legal_references(
    data: OfficialWritingInput,
    body: str,
) -> list[str]:
    """
    يتأكد أن الـLLM لم يخترع أساساً قانونياً جديداً.
    """

    source_text = _collect_source_text(data)
    # نحصل على كل المعلومات الأصلية التي يحق للـLLM استخدامها.

    source_legal = _find_legal_references(
        source_text
    )
    # نستخرج القوانين والمراجع القانونية الموجودة في الـContext.

    body_legal = _find_legal_references(
        body
    )
    # نستخرج القوانين والمراجع القانونية التي كتبها الـLLM.

    added = body_legal - source_legal
    # إذا ظهر مرجع في body لكنه غير موجود في الـContext:
    # هذا يعني أن الـLLM أضاف مرجعاً قانونياً من عنده.

    return [
        f"Context'te bulunmayan hukuki referans: {reference}"
        for reference in sorted(added)
    ]
    # نرجع قائمة بالأخطاء.


# =========================================================
# CHECK ADDED DATES
# =========================================================

def _check_added_dates(
    data: OfficialWritingInput,
    body: str,
) -> list[str]:
    """
    يتأكد أن الـLLM لم يخترع تاريخاً جديداً.
    """

    source_text = _collect_source_text(data)
    # نجمع البيانات الأصلية.

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