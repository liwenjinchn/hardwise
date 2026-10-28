"""Hand-authored synthetic before/after exports; no private project data."""

from pathlib import Path
from tempfile import TemporaryDirectory

from hardwise.revision.models import ComparisonResult

BEFORE_NETLIST = """$PACKAGES
 ! 'SOIC8' ! 'DEMO_CTRL' ; U1
 ! 'R0603' ! '10k' ; R1
 ! 'R0603' ! '1k' ; R2
 ! 'CONN2' ! 'HEADER' ; J1
$NETS
 'CTRL' ; U1.1, R1.1, J1.1
 'VCC' ; U1.8, R1.2, R2.1
 'GND' ; U1.2, U1.4, R2.2, J1.2
$END
"""
AFTER_NETLIST = """$PACKAGES
 ! 'SOIC8' ! 'DEMO_CTRL' ; U1
 ! 'R0603' ! '4.7k' ; R1
 ! 'R0603' ! '1k' ; R3
 ! 'CONN2' ! 'HEADER' ; J1
$NETS
 'ENABLE' ; U1.1, R1.1, J1.1
 'VCC' ; U1.8, U1.2, R1.2, R3.1
 'GND' ; U1.4, R3.2, J1.2
$END
"""
BEFORE_BOM = """RefDes,Value,Footprint
U1,DEMO_CTRL,SOIC8
R1,10k,R0603
R2,1k,R0603
J1,HEADER,CONN2
"""
AFTER_BOM = """RefDes,Value,Footprint
U1,DEMO_CTRL,SOIC8
R1,4.7k,R0603
R3,1k,R0603
J1,HEADER,CONN2
"""


def compare_demo_files() -> ComparisonResult:
    """Recompute the example from literal input files on every request."""
    from hardwise.revision.engine import compare_files

    with TemporaryDirectory(prefix="hardwise-compare-demo-") as temporary:
        paths = []
        for role, filename, content in (
            ("before_netlist", "synthetic.net", BEFORE_NETLIST),
            ("before_bom", "synthetic.csv", BEFORE_BOM),
            ("after_netlist", "synthetic.net", AFTER_NETLIST),
            ("after_bom", "synthetic.csv", AFTER_BOM),
        ):
            directory = Path(temporary) / role
            directory.mkdir()
            path = directory / filename
            path.write_text(content, encoding="utf-8")
            paths.append(path)
        return compare_files(*paths)
