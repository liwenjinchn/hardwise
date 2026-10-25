"""Real parsed controller circuits retain only observations within declared scope."""

import csv
import json
import shutil
from pathlib import Path
import pytest
from hardwise.ir.profile import DatasheetProfile
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.task_projection import build_review_tasks
from hardwise.workbench.decision_fingerprints import review_fingerprints, review_project_key
from hardwise.workbench.review_decisions import ReviewDecisionStore, ReviewDecisionRequest

CASES = [
    ("stm32g030c8t6", "10", "mcu_nrst"),
    ("stm32g030c8t6", "44", "mcu_boot0"),
    ("pca9617a", "5", "i2c_repeater_enable"),
    ("74lv165", "15", "shift_register_clock_enable"),
]


@pytest.fixture(params=CASES)
def circuit(tmp_path, request):
    name, number, check = request.param
    (tmp_path / "profiles").mkdir()
    source = Path("data/datasheet_profiles") / (name + ".json")
    shutil.copy2(source, tmp_path / "profiles" / source.name)
    profile = DatasheetProfile.load(source)
    nets = {}
    for pin in profile.pins:
        net = (
            "CTRL"
            if pin.number == number
            else "RETURN"
            if pin.category == "ground"
            else "P" + pin.number
        )
        nets.setdefault(net, []).append("U1." + pin.number)
    nets["CTRL"].append("R1.1")
    nets["BIAS"] = ["R1.2"]
    nets["FAR"] = ["RFAR.1"]
    nets["FAR_RETURN"] = ["RFAR.2"]
    text = "$PACKAGES\n ! 'PUBLIC' ! PUBLIC_PART ; U1\n ! 'R0402' ! 10K ; R1 RFAR\n$NETS\n"
    text += "\n".join(f" '{net}' ; {', '.join(nodes)}" for net, nodes in nets.items()) + "\n$END\n"
    (tmp_path / "public.net").write_text(text)
    with (tmp_path / "public.csv").open("w", newline="") as stream:
        csv.writer(stream).writerows(
            [
                ["Reference", "Quantity", "Value", "MPN"],
                ["U1", 1, profile.part_number, profile.part_number],
                ["R1", 1, "10K", "PUBLIC_R"],
                ["RFAR", 1, "1K", "PUBLIC_R"],
            ]
        )
    (tmp_path / "facts.json").write_text(
        json.dumps({"schema_version": "hardwise.voltage_facts.v1", "facts": []})
    )
    return tmp_path, check


def _build(circuit):
    root, check = circuit
    context = build_workbench_context(
        netlist_path=root / "public.net",
        bom_path=root / "public.csv",
        profiles=root / "profiles",
        voltage_facts=root / "facts.json",
    )
    task = next(t for t in build_review_tasks(context) if t.refdes == "U1" and t.check == check)
    assert task.assessment.rule_version == "2"
    return context, task


def _change_value(root, refdes, value):
    path = root / "public.csv"
    with path.open() as stream:
        rows = list(csv.reader(stream))
    for row in rows[1:]:
        if row[0] == refdes:
            row[2] = value
    with path.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)


def _fingerprint(circuit):
    context, task = _build(circuit)
    try:
        return review_fingerprints(context, [task])[task.stable_key], task
    finally:
        close_workbench_context(context)


def test_unrelated_component_change_preserves_hash_and_actual_machine_observation(circuit):
    before, old = _fingerprint(circuit)
    _change_value(circuit[0], "RFAR", "2K")
    after, new = _fingerprint(circuit)
    assert old.model_dump() == new.model_dump()
    assert before == after


@pytest.mark.parametrize(
    "change",
    [
        "branch_value",
        "branch_other_net",
        "add_neighbor",
        "control_voltage",
        "bias_voltage",
        "profile_version",
    ],
)
def test_direct_neighborhood_or_profile_change_requires_new_fingerprint(circuit, change):
    root, _ = circuit
    before, _ = _fingerprint(circuit)
    if change == "branch_value":
        _change_value(root, "R1", "22K")
    elif change == "branch_other_net":
        path = root / "public.net"
        path.write_text(path.read_text().replace("'BIAS'", "'OTHER'"))
    elif change == "add_neighbor":
        path = root / "public.net"
        text = (
            path.read_text()
            .replace("10K ; R1 RFAR", "10K ; R1 RFAR RNEW")
            .replace("R1.1\n", "R1.1, RNEW.1\n")
            .replace("'BIAS' ; R1.2", "'BIAS' ; R1.2, RNEW.2")
        )
        path.write_text(text)
        with (root / "public.csv").open("a") as stream:
            stream.write("RNEW,1,10K,PUBLIC_R\n")
    elif change in {"control_voltage", "bias_voltage"}:
        fact = {
            "net": "CTRL" if change == "control_voltage" else "BIAS",
            "reference_net": "RETURN",
            "minimum": 3.3,
            "maximum": 3.3,
            "confirmed": True,
            "confirmed_by": "public author",
            "source": "synthetic declared input; not measured",
        }
        (root / "facts.json").write_text(
            json.dumps({"schema_version": "hardwise.voltage_facts.v1", "facts": [fact]})
        )
    else:
        path = next((root / "profiles").iterdir())
        data = json.loads(path.read_text())
        data["schema_version"] = "public changed profile revision"
        path.write_text(json.dumps(data))
    assert _fingerprint(circuit)[0] != before


def test_persisted_reason_survives_unrelated_change_and_becomes_review_needed_for_branch(circuit):
    root, _ = circuit
    reason = "公开控制连接复核理由"

    def begin():
        context, task = _build(circuit)
        store = ReviewDecisionStore(root / "review.sqlite")
        tasks = build_review_tasks(context)
        fps = review_fingerprints(context, tasks)
        project = review_project_key(context)
        store.begin_run(project, fps)
        return context, task, store, tasks, fps, project

    context, task, store, tasks, fps, project = begin()
    try:
        store.update(
            known_keys=[t.stable_key for t in tasks],
            request=ReviewDecisionRequest(
                stable_keys=[task.stable_key],
                status="accepted_risk",
                reason=reason,
                expected_run_id=store.summary([task.stable_key], project=project).run_id,
            ),
            fingerprints=fps,
        )
    finally:
        close_workbench_context(context)
    for refdes, status, count in [("RFAR", "accepted_risk", 1), ("R1", "needs_review", 2)]:
        _change_value(root, refdes, "22K")
        context, task, store, tasks, fps, project = begin()
        try:
            current = store.apply([task], fingerprints=fps, project=project)[0].review_decision
            assert current.status == status and current.reason == reason
            assert store.history_page()["total"] == count
        finally:
            close_workbench_context(context)


@pytest.mark.parametrize("future", ["new_check", "new_version"])
def test_unregistered_controls_still_use_conservative_project_fallback(circuit, future):
    context, task = _build(circuit)
    try:
        future_task = (
            task.model_copy(update={"check": task.check + "_future"})
            if future == "new_check"
            else task.model_copy(
                update={"assessment": task.assessment.model_copy(update={"rule_version": "next"})}
            )
        )
        before = review_fingerprints(context, [future_task])[future_task.stable_key]
    finally:
        close_workbench_context(context)
    _change_value(circuit[0], "RFAR", "2K")
    context, _ = _build(circuit)
    try:
        assert review_fingerprints(context, [future_task])[future_task.stable_key] != before
    finally:
        close_workbench_context(context)


def test_previous_project_scope_requires_one_review_and_preserves_reason(circuit, monkeypatch):
    from hardwise.workbench import decision_fingerprints as module

    root, _ = circuit
    context, task = _build(circuit)
    try:
        with monkeypatch.context() as old_scope:
            old_scope.setattr(module, "control_dependency_payload", lambda *args: None)
            legacy = review_fingerprints(context, [task])
        current = review_fingerprints(context, [task])
        assert legacy != current
        project = review_project_key(context)
        store = ReviewDecisionStore(root / "migration.sqlite")
        store.begin_run(project, legacy)
        store.update(
            known_keys=[task.stable_key],
            fingerprints=legacy,
            request=ReviewDecisionRequest(
                stable_keys=[task.stable_key],
                status="accepted_risk",
                reason="旧范围原始中文理由",
                expected_run_id=store.summary([task.stable_key], project=project).run_id,
            ),
        )
        store.begin_run(project, current)
        decision = store.apply([task], fingerprints=current, project=project)[0].review_decision
        assert decision.status == "needs_review" and decision.reason == "旧范围原始中文理由"
        assert decision.previous_status == "accepted_risk"
        assert store.history_page()["total"] == 2
        store.begin_run(project, current)
        assert store.history_page()["total"] == 2
    finally:
        close_workbench_context(context)


def test_voltage_fact_on_disconnected_circuit_does_not_clear_control_review(circuit):
    root, _ = circuit
    before, _ = _fingerprint(circuit)
    fact = {
        "net": "FAR",
        "reference_net": "FAR_RETURN",
        "minimum": 48,
        "maximum": 48,
        "confirmed": True,
        "confirmed_by": "public author",
        "source": "disconnected synthetic premise",
    }
    (root / "facts.json").write_text(
        json.dumps({"schema_version": "hardwise.voltage_facts.v1", "facts": [fact]})
    )
    assert _fingerprint(circuit)[0] == before


def test_same_control_network_node_order_is_not_a_changed_dependency(circuit):
    root, _ = circuit
    before, original = _fingerprint(circuit)
    path = root / "public.net"
    lines = path.read_text().splitlines()
    for index, line in enumerate(lines):
        if "'CTRL' ;" in line:
            left, right = line.split(";", 1)
            lines[index] = (
                left + "; " + ", ".join(reversed([part.strip() for part in right.split(",")]))
            )
    path.write_text("\n".join(lines) + "\n")
    after, current = _fingerprint(circuit)
    assert current.model_dump() == original.model_dump()
    assert after == before


def test_changed_observed_pin_alias_is_not_erased_by_pin_sorting(circuit):
    root, check = circuit
    number = next(number for _, number, name in CASES if name == check)
    profile_path = next((root / "profiles").iterdir())
    profile = json.loads(profile_path.read_text())
    for pin in profile["pins"]:
        if pin["number"] == number:
            pin["schematic_pin_aliases"] = ["A", "B"]
    profile_path.write_text(json.dumps(profile))
    path = root / "public.net"
    text = path.read_text().replace("U1." + number + ", R1.1", "U1.A, U1.B, R1.1")
    path.write_text(text)
    before, original = _fingerprint(circuit)
    path.write_text(text.replace("U1.A, U1.B, R1.1", "U1.B, U1.A, R1.1"))
    after, current = _fingerprint(circuit)
    assert original.assessment == current.assessment
    assert original.evidence_chain != current.evidence_chain
    assert after != before
