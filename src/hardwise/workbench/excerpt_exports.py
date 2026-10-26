"""Sharing is an export projection; never rewrite stored run receipts or profiles."""

import json

from hardwise.agent.claim_turn import render_explanation
from hardwise.guards.refdes import sanitize_text
from hardwise.ir.excerpt_sharing import sharing_status, source_content_hash
from hardwise.ir.shared_excerpts import has_withheld_excerpt, share_excerpt_projection


def withheld_sources(context):
    """An explicit current withholding also applies to identical historical sources.

    A current allow never backfills absent declarations into old records. A
    withholding wins if two current fields disagree about the same source.
    """
    return frozenset(
        source_content_hash(field.source)
        for profile in context.validation_targets.values()
        if profile.field_review is not None
        for field in profile.field_review.fields
        if sharing_status(field.source) == "withheld"
    )


def allowed_sources(context):
    # Old permissions cannot resurrect after a current field/declaration is
    # removed or changed. Historical sharing requires both old and current allow.
    return frozenset(
        source_content_hash(field.source)
        for profile in context.validation_targets.values()
        if profile.field_review is not None
        for field in profile.field_review.fields
        if sharing_status(field.source) == "allowed"
    )


def share_chat_response(response, context):
    review = response.explanation_review
    if review is None:
        return response
    blocked = withheld_sources(context)
    allowed = allowed_sources(context)
    facts = tuple(
        f
        for f in review.verified_facts
        if f.property_key != "datasheets.retrieved_hits"
        and not has_withheld_excerpt(f.model_dump(mode="json"), blocked, allowed)
    )
    omitted = len(review.verified_facts) - len(facts)
    if not omitted:
        return response
    # Do not redact a verified fact in-place and keep its content-bound ID.
    # Withhold it as a whole, then regenerate visible prose from retained facts.
    updated = review.model_copy(
        update={
            "verified_facts": facts,
            "notices": (
                *review.notices,
                f"分享报告省略 {omitted} 项含未获有效分享声明摘录或检索片段的绑定；本地原记录保留。",
            ),
        }
    )
    answer, kind = render_explanation(updated)
    answer, wrapped = sanitize_text(answer, context.registry)
    return response.model_copy(
        update={
            "answer": answer,
            "response_kind": kind,
            "explanation_review": updated,
            "wrapped_count": response.wrapped_count + wrapped,
        }
    )


def share_snapshot(snapshot, context):
    shared = share_excerpt_projection(snapshot, withheld_sources(context), allowed_sources(context))
    # These strings were serialized before projection; regenerate them from
    # projected structures, otherwise a nested download leaks the original.
    if "review_history" in shared:
        shared["exports"]["review_history"] = json.dumps(
            shared["review_history"], ensure_ascii=False, indent=2
        )
    shared["exports"]["json"] = json.dumps(shared["state"], ensure_ascii=False, indent=2)
    return shared
