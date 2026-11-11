import sys
from pathlib import Path
b=Path(r'D:/workspace/power_system/inverter/hardware')
sys.path.insert(0,str(b/'tools'))
sys.path.insert(0,str(b/'review/compact_digital_seed'))
import digital_quick_native as own
import compact_fast_stitch as fast
own.Geometry.masks=fast.masks
own.Geometry.line_ok=fast.line_ok
own.Geometry.via_ok=fast.via_ok
raise SystemExit(own.main())
