"""User-facing Chinese labels for validator UI terms."""

from __future__ import annotations

STATUS_LABELS = {
    "matched": "已匹配",
    "no_result": "无本地档案",
    "manual_needed": "需人工确认",
    "ambiguous": "多候选",
    "not_requested": "未配置资料索引",
    "not_validated": "未验证",
    "generic_passive": "通用被动件检查",
}

IDENTITY_KIND_LABELS = {
    "part_number": "料号",
    "part_like_value": "型号值",
    "passive_value": "参数值",
    "connector_or_mechanical": "连接/结构件",
    "missing": "缺失",
}

FAMILY_LABELS = {
    "capacitor": "电容",
    "connector": "连接器",
    "diode": "二极管",
    "ferrite": "磁珠",
    "ic": "IC",
    "inductor": "电感",
    "mechanical": "结构件",
    "resistor": "电阻",
    "test_point": "测试点",
    "transistor": "晶体管",
    "unknown": "未知",
}

REASON_LABELS = {
    "No local profile part_number matched this BOM identity.": "本地还没有匹配这个 BOM 身份的器件档案。",
    "BOM item has no MPN or part-like value for profile matching.": "BOM 行缺少可用于匹配器件档案的 MPN/型号。",
    "No document index was provided.": "未提供本地资料索引。",
    "BOM item has no MPN or part-like value for document matching.": "BOM 行缺少可用于匹配资料的 MPN/型号。",
    "No local document-index row matched this BOM identity.": "本地资料索引里没有匹配这个 BOM 身份的条目。",
    "Multiple local document-index rows match this BOM identity.": "本地资料索引里有多个候选，需要人工确认。",
    "Exactly one local document-index row matched this BOM identity.": "本地资料索引已匹配到唯一条目。",
    "Generic passive validation ran from BOM value/package; no per-MPN datasheet profile is required.": (
        "已按 BOM 参数/封装执行通用被动件检查，不需要逐个阻容值建立器件档案。"
    ),
}


def status_label(status: str) -> str:
    """Return a user-facing label for coverage/document status strings."""

    return STATUS_LABELS.get(status, status)


def identity_kind_label(kind: str) -> str:
    """Return a user-facing label for normalized BOM identity kinds."""

    return IDENTITY_KIND_LABELS.get(kind, kind)


def family_label(family: str) -> str:
    """Return a user-facing label for suggested component families."""

    return FAMILY_LABELS.get(family, family)


def reason_label(reason: str) -> str:
    """Return a localized reason while preserving unknown diagnostic text."""

    return REASON_LABELS.get(reason, reason)
