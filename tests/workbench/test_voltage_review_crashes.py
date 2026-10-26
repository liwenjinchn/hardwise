"""Real process exits around voltage catalog/run commit retain a recoverable version."""

import json
from pathlib import Path
import shutil

import pytest

from hardwise.workbench.managed_projects import ManagedProjects
from tests.workbench.test_voltage_review_intake import inputs
from tests.workbench.test_voltage_review_routes import rows


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_process_exit_at_publication_recovers_only_a_complete_saved_version(tmp_path, phase):
    import os
    import subprocess
    import sys

    files = inputs.__wrapped__(tmp_path)
    original = files[1].read_bytes()
    script = tmp_path / "crash.py"
    script.write_text("""
from pathlib import Path
import os,json,sys
from fastapi.testclient import TestClient
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.server import create_workbench_app
from tests.workbench.test_voltage_review_intake import build,NoChat
from tests.workbench.test_voltage_review_routes import request_for,rows
root=Path(sys.argv[1]);phase=sys.argv[2];journal=root/'crash.sqlite'
context=build((root/'source',root/'source/review.json',None))
app=create_workbench_app(context,NoChat(),review_db=journal,auto_datasheet_candidates=False)
with TestClient(app) as client:
 request=request_for(client)
 client.post('/api/workbench/projects/save',params={'expected_run_id':request['expected_run_id']}).raise_for_status()
 (root/'before-rows.json').write_text(json.dumps(rows(journal)))
 if phase=='before_commit':
  original=ManagedProjects.publish
  def crash(self,*args,**kwargs):
   original(self,*args,**kwargs)
   os._exit(81)
  ManagedProjects.publish=crash
 else:
  def crash(*args,**kwargs):os._exit(82)
  app.state.workbench_context.swap=crash
 client.post('/api/workbench/voltage-review/confirm',json=request)
 raise RuntimeError('Crash point was not reached')
""")
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path), phase],
        env={
            **os.environ,
            "PYTHONPATH": str(Path.cwd() / "src") + os.pathsep + str(Path.cwd()),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == ({"before_commit": 81, "after_commit": 82}[phase]), (
        result.stdout + result.stderr
    )
    journal = tmp_path / "crash.sqlite"
    before = json.loads((tmp_path / "before-rows.json").read_text())
    after = json.loads(json.dumps(rows(journal)))
    catalog = ManagedProjects(journal).list()
    assert len(catalog) == 1
    opened, directory = ManagedProjects(journal).open(catalog[0]["id"])
    try:
        if phase == "before_commit":
            assert after == before
            assert len(opened.design.voltage_review.confirmations) == 2
        else:
            assert all(row in after["review_runs"] for row in before["review_runs"])
            assert len(after["review_runs"]) == len(before["review_runs"]) + 1
            assert len(opened.design.voltage_review.confirmations) == 3
            assert opened.design.voltage_facts.facts[0].confirmed
        assert files[1].read_bytes() == original
    finally:
        from hardwise.workbench.context import close_workbench_context

        close_workbench_context(opened)
        shutil.rmtree(directory)
