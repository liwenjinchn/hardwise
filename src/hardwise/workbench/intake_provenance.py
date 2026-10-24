"""Attach verified read provenance only after a complete context build succeeds."""

from functools import wraps
from hardwise.input_provenance import capture_input_reads


def record_intake_inputs(build):
    @wraps(build)
    def recorded(*args, **kwargs):
        context = None
        try:
            with capture_input_reads() as collector:
                context = build(*args, **kwargs)
                context.input_manifest = collector.finish()
            return context
        except Exception:
            if context is not None:
                context.session.close()
            raise

    return recorded
