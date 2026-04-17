from pathlib import Path
import difflib

a=Path(r"C:\Users\taci.ugraskan\source\repos\Data\cover\02050301 - Copy\xxmgt_out_hru89_extracted.txt")
b=Path(r"C:\Users\taci.ugraskan\source\repos\Data\cover\02050301 - Copy\mgt_out_hru89_extracted.txt")
out=Path(r"C:\Users\taci.ugraskan\source\repos\Data\cover\02050301 - Copy\HRU89_unified_diff.txt")

if not a.exists() or not b.exists():
    missing=[str(p) for p in (a,b) if not p.exists()]
    print('MISSING:', missing)
    raise SystemExit(1)

with a.open('r', encoding='utf8', errors='replace') as fa, b.open('r', encoding='utf8', errors='replace') as fb:
    al=fa.readlines()
    bl=fb.readlines()
    diff=list(difflib.unified_diff(al, bl, fromfile=a.name, tofile=b.name, lineterm=''))

with out.open('w', encoding='utf8') as fo:
    for line in diff:
        fo.write(line + '\n')

print(f'Saved unified diff to {out} ({len(diff)} lines)')
