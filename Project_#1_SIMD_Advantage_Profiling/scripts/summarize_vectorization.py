"""Produce a concise table from GCC's per-build optimization reports.
Run after build_and_run.ps1: py scripts/summarize_vectorization.py
"""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
source=(root/'src/simd_benchmark.c').read_text().splitlines()
reports=root/'reports'
reports.mkdir(exist_ok=True)
loops={}
for name in ('saxpy_kernel','multiply_kernel','dot_kernel'):
    start=next(i for i,line in enumerate(source) if re.search(r'\b'+name+r'\s*\(',line) and 'NOIPA' in line)
    loop=next(i+1 for i in range(start+1,len(source)) if 'for (size_t i=' in source[i])
    loops[name]=loop
lines=['# Concise compiler vectorization summary','',
       'The rows show compiler-reported vectorization of function loops. For runtime-variable stride, the compiler may create a vectorized unit-stride branch and a scalar nonunit-stride branch; this table alone does not prove every stride used packed SIMD.','',
       '| Build | Kernel | Source line | Vector widths reported | Interpretation |',
       '|---|---|---:|---|---|']
for p in sorted(reports.glob('*_vectorization.txt')):
    if p.name.startswith('legacy_'):continue
    raw=p.read_text(errors='replace')
    for name,line in loops.items():
        matched=[x for x in raw.splitlines() if re.search(rf':{line}:\d+:',x) and 'loop vectorized using' in x]
        widths=sorted(set(re.findall(r'using (\d+) byte vectors', '\n'.join(matched))))
        status='Reported optimized branch' if widths else ('Vectorization disabled by scalar flags' if 'scalar' in p.name else 'No optimized-loop evidence on this exact line; check full report')
        lines.append(f'| `{p.stem.replace("_vectorization","")}` | {name} | {line} | {", ".join(widths) if widths else "—"} | {status} |')
lines += ['', 'To support your actual runtime claims, retain the full report files in the repository, select short relevant excerpts in the report, and avoid presenting a vectorized loop version as proof that a particular stride took that branch.']
path=reports/'vectorization_summary.md'
path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'Saved {path}')
