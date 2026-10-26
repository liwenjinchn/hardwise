"""Expose approved field values with their original units and approval conditions."""

from hardwise.agent.claim_contract import ClaimBinding
from hardwise.validation.profile_approval import approval_reason


def profile_claim_bindings(profile, component, *, pointer=None, prefix=None):
    """Only the evidence-locator producer calls this on its actual selected profile.

    Do not reconstruct numeric fields from a hit's display text. Approval is
    checked against the current component and original field content first.
    """
    if approval_reason(component, profile) or profile.field_review is None:
        return ()
    review = profile.field_review
    bindings = []
    for field in review.fields:
        if not (
            (pointer is not None and field.pointer == pointer)
            or (prefix is not None and field.pointer.startswith(prefix))
        ):
            continue
        if not field.approved(review.identity):
            continue
        conditions = {
            "subject": field.subject,
            "role": field.role,
            "nature": field.nature,
            "identity": review.identity.model_dump(mode="json"),
            "applicability": [item.model_dump(mode="json") for item in field.conditions],
            "source": field.source.model_dump(mode="json"),
            "approval": field.decisions[-1].model_dump(mode="json"),
        }
        # A declaration describes the source's applicability; it does not assert
        # that this board satisfies that condition or receives a PASS.
        bindings.append(
            ClaimBinding(
                object_kind="component",
                object_id=component.refdes,
                property_key="profile" + field.pointer,
                kind="approved_parameter",
                value=field.value,
                unit=field.unit,
                conditions=conditions,
                conditions_status="explicit",
                source_tokens=(f"datasheet:{field.source.url}#p{field.source.page}",),
                rule_version=None,
            )
        )
    return tuple(bindings)
