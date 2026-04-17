import re
from pathlib import Path
files=[Path(r"C:\Users\taci.ugraskan\source\repos\Data\cover\02050301 - Copy\xxmgt_out.txt"), Path(r"C:\Users\taci.ugraskan\source\repos\Data\cover\02050301 - Copy\mgt_out.txt")]
pat=re.compile(r'^\s*89\b')
for f in files:
    if not f.exists():
        print('MISSING', f)
        continue
    out=f.with_name(f.stem + '_hru89_extracted' + f.suffix)
    count=0
    with f.open('r', encoding='utf8', errors='replace') as fin, out.open('w', encoding='utf8') as fout:
        for line in fin:
            if pat.match(line):
                fout.write(line)
                count+=1
    print(f'WROTE {out} ({count} lines)')
