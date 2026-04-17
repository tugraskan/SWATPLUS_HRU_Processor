import difflib
from pathlib import Path
p=Path(r"C:\Users\taci.ugraskan\source\repos\Data\cover\02050301 - Copy")
f1=p / "xxmgt_out_89.txt"
f2=p / "mgt_out_89.txt"
out=p / "HRU89_diff.txt"
if not f1.exists() or not f2.exists():
    missing=[str(x) for x in (f1,f2) if not x.exists()]
    print('MISSING:', '\n'.join(missing))
    raise SystemExit(1)
lines1=f1.read_text(encoding='utf8').splitlines(keepends=True)
lines2=f2.read_text(encoding='utf8').splitlines(keepends=True)
diff=list(difflib.unified_diff(lines1, lines2, fromfile=str(f1.name), tofile=str(f2.name), lineterm=''))
out.write_text(''.join(line+"\n" for line in diff), encoding='utf8')
for i,line in enumerate(diff[:50],1):
    print(f"{i:03}: {line}")
print('\nSaved diff to', out)
