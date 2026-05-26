"""End-to-end CLI tests for Allegro schematic netlist inspection."""

from __future__ import annotations

from typer.testing import CliRunner

from hardwise.cli import app


def test_inspect_allegro_netlist_telesis_fixture() -> None:
    result = CliRunner().invoke(
        app,
        [
            "inspect-allegro-netlist",
            "tests/fixtures/allegro/minimal_third_party.net",
            "--limit",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "type: Allegro/Telesis schematic netlist topology" in result.output
    assert "components: 4" in result.output
    assert "nets: 4" in result.output
    assert "scope: pre-Layout connectivity only" in result.output


def test_inspect_allegro_netlist_pst_fixture_directory_and_member_file() -> None:
    runner = CliRunner()

    for input_path in [
        "tests/fixtures/allegro/pst",
        "tests/fixtures/allegro/pst/pstxnet.dat",
    ]:
        result = runner.invoke(
            app,
            [
                "inspect-allegro-netlist",
                input_path,
                "--limit",
                "2",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "type: Cadence Capture/Allegro PST schematic netlist topology" in result.output
        assert "components: 3" in result.output
        assert "nets: 3" in result.output
        assert "properties: 9" in result.output
        assert "no .brd, boardview, or PCB geometry parsed" in result.output
