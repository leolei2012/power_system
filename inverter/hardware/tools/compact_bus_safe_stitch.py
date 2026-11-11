"""Scoped signal finish with native-checked vias in wide VBUS interiors.

Via centers must be >=1.8 mm from original VBUS polygon boundaries. Actual
pad/copper/drill/clearance and Kelvin checks still apply. Every candidate also
checks the filled-copper connectivity of all original main-power paths.
"""
from pathlib import Path
import json,sys
import compact_stitch_signals as stitch
import compact_wide_vbus_geometry as wide
import compact_verify_fixed as fixed
from compact_power_copper import audit_power_connectivity

if '--power-report' not in sys.argv:raise ValueError('A fixed power report is mandatory')
report=json.loads(Path(sys.argv[sys.argv.index('--power-report')+1]).read_text(encoding='utf-8'))
class Geometry(wide.WideVBUSGeometry):
    def __init__(self,board,args,project):
        super().__init__(board,args,project,report);self.mask_guard_mm=.002
stitch.Geometry=Geometry
original_verify=fixed.verify_geometry
def verify(board,records):
    objects,issues,counts=original_verify(board,records)
    try:audit_power_connectivity(board,records)
    except Exception as exc:issues.append({'check':'main_power_filled_connectivity','error':str(exc)})
    return objects,issues,counts
fixed.verify_geometry=verify
if __name__=='__main__':raise SystemExit(stitch.main())
