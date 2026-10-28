"""Local revision comparison commands; no workbench session or AI setup."""

from __future__ import annotations

from pathlib import Path

import typer


def _check_outputs(inputs: tuple[Path, ...], outputs: list[Path]) -> None:
    """Check all destinations before computing or creating either output."""
    resolved_inputs = {path.resolve() for path in inputs}
    destinations: set[Path] = set()
    for output in outputs:
        resolved = output.resolve()
        if resolved in resolved_inputs or (
            output.exists() and any(output.samefile(source) for source in inputs)
        ):
            raise ValueError(f"拒绝覆盖输入文件: {output}")
        if resolved in destinations:
            raise ValueError("HTML 与 JSON 输出路径必须不同。")
        destinations.add(resolved)
        if output.exists() or output.is_symlink():
            raise ValueError(f"输出已存在，拒绝覆盖: {output}")
        if not output.parent.is_dir():
            raise ValueError(f"输出父目录不存在或不是目录: {output.parent}")


def _write_outputs(payloads: list[tuple[Path, str]]) -> None:
    """Exclusive creation also protects destinations changed after preflight."""
    created: list[Path] = []
    try:
        for path, content in payloads:
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
    except OSError:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


def register_compare_commands(app: typer.Typer) -> None:
    """Register the deterministic before/after comparison workflow first."""

    @app.command(name="compare")
    def compare(
        before_netlist: Path = typer.Argument(
            ...,
            exists=True,
            dir_okay=True,
            readable=True,
            help="改版前 Telesis 网表或完整 PST 目录。",
        ),
        before_bom: Path = typer.Argument(
            ...,
            exists=True,
            dir_okay=False,
            readable=True,
            help="改版前 BOM (.csv/.tsv)。",
        ),
        after_netlist: Path = typer.Argument(
            ...,
            exists=True,
            dir_okay=True,
            readable=True,
            help="改版后 Telesis 网表或完整 PST 目录。",
        ),
        after_bom: Path = typer.Argument(
            ...,
            exists=True,
            dir_okay=False,
            readable=True,
            help="改版后 BOM (.csv/.tsv)。",
        ),
        output: Path = typer.Option(..., "--output", help="必选：新建离线 HTML 报告，不覆盖。"),
        json_output: Path | None = typer.Option(
            None,
            "--json-output",
            help="可选：同时新建完整比较 JSON，不覆盖。",
        ),
    ) -> None:
        """比较前后四份文件；仅源数据差异，无 AI、数据库或电气判定。"""
        inputs = (before_netlist, before_bom, after_netlist, after_bom)
        outputs = [output] + ([json_output] if json_output is not None else [])
        try:
            from hardwise.revision.netlist_source import netlist_files

            sources = (
                *netlist_files(before_netlist),
                before_bom,
                *netlist_files(after_netlist),
                after_bom,
            )
            _check_outputs(sources, outputs)
            if output.suffix.lower() not in {".html", ".htm"}:
                raise ValueError("--output 必须使用 .html 或 .htm 路径。")
            for path in (before_bom, after_bom):
                if path.suffix.lower() not in {".csv", ".tsv"}:
                    raise ValueError(f"不支持的 BOM 格式: {path.name}；仅 CSV/TSV。")
            for path in sources:
                if path.stat().st_size == 0:
                    raise ValueError(f"输入文件为空: {path.name}")
            from hardwise.revision.engine import compare_files
            from hardwise.revision.report import render_comparison_html

            result = compare_files(*inputs)
            payloads = [(output, render_comparison_html(result))]
            if json_output is not None:
                payloads.append((json_output, result.model_dump_json(indent=2) + "\n"))
            _write_outputs(payloads)
        except (OSError, ValueError) as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(1) from exc
        typer.echo(f"比较完成: {result.status}；HTML: {output}")
        if json_output is not None:
            typer.echo(f"JSON: {json_output}")

    @app.command(name="serve-compare")
    def serve_compare(
        port: int = typer.Option(18774, "--port", min=1, max=65535, help="本地比较界面端口。"),
        open_browser: bool = typer.Option(False, "--open", help="启动时在浏览器打开比较界面。"),
    ) -> None:
        """启动独立比较界面，仅监听 127.0.0.1；不创建评审会话。"""
        import uvicorn

        from hardwise.revision.server import create_compare_app

        url = f"http://127.0.0.1:{port}/compare"
        typer.echo(f"Hardwise 改版对比: {url}")
        if open_browser:
            import webbrowser

            webbrowser.open(url)
        uvicorn.run(create_compare_app(), host="127.0.0.1", port=port)
