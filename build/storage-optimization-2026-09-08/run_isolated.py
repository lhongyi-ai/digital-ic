from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
kind,label,*args=sys.argv[1:]
if kind=="build":
    source=ROOT/"scripts/build_sensor.py"
    code=source.read_text().replace('out=ROOT/"build"/f"sensor_board_{a.rate}hz{suffix}"',f'out=ROOT/"build/storage-optimization-2026-09-08/{label}"')
elif kind=="sim":
    source=ROOT/"sim/run_sensor_system.py"
    code=source.read_text().replace('build=ROOT/"build"/f"sensor_system_{case}"',f'build=ROOT/"build/storage-optimization-2026-09-08/{label}"/f"sensor_system_{{case}}"')
else:raise ValueError(kind)
sys.argv=[str(source),*args]
exec(compile(code,str(source),"exec"),{"__file__":str(source),"__name__":"__main__"})
