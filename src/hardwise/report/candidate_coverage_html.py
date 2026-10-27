"""Render the same backend summary in the legacy static workbench."""

from html import escape


def render_candidate_coverage(summary):
    if summary is None:
        return '<section aria-label="候选范围未记录"><p>该记录未保存目录候选快照，不从已生成结果推算历史分母。</p></section>'
    c = summary.counts
    return (
        '<section class="scope-note" aria-label="目录候选检查范围">'
        f'<strong>目录候选检查 {c.candidate_count} 项</strong>'
        f'<p>完成 {c.completed_count}，未知 {c.unknown_count}，不适用 {c.not_applicable_count}；'
        f'未知中未执行 {c.unexecuted_count}；未支持范围 {c.unsupported_scope_count}。</p>'
        f'<p>{escape(summary.boundary)}</p><p>目录：{escape(summary.catalog_version)}</p></section>'
    )
