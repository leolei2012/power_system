"""Native exact short/45-degree/via finish pass; same DRC and fixed checks."""
import compact_quick_native as own
import compact_fast_stitch as fast
own.Geometry.masks=fast.masks
own.Geometry.line_ok=fast.line_ok
own.Geometry.via_ok=fast.via_ok
if __name__=="__main__":raise SystemExit(own.main())
