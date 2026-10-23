"""Simple final-figure generator for ECSE Project #1.

Uses the REAL raw/bench_*.csv files made by build_and_run.ps1.
Produces exactly seven PNGs inside figures/final/ plus processed/final/
summary tables. No need to run the old plot_results.py first.

Run from project root: py scripts/plot_results.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
OUT = ROOT / 'processed' / 'final'
FIG = ROOT / 'figures' / 'final'
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

paths = sorted(RAW.glob('bench_*.csv'))
if not paths:
    raise SystemExit('No raw/bench_*.csv files. First run scripts/build_and_run.ps1 in this project folder.')
trials = pd.concat((pd.read_csv(path) for path in paths), ignore_index=True)
required = {'Mode','Build','Type','Kernel','N','Stride','Offset_bytes','Time_ms','Correct'}
missing = required - set(trials.columns)
if missing:
    raise SystemExit('Raw benchmark CSV missing fields: ' + ', '.join(sorted(missing)))
if trials.empty or not (trials.Correct == 'PASS').all() or (trials.Time_ms <= 0).any():
    raise SystemExit('One or more trials are missing, failed correctness, or have nonpositive times.')

key = ['Mode','Build','Type','Kernel','N','Stride','Offset_bytes']
summary = (trials.groupby(key, as_index=False)
           .agg(median_ms=('Time_ms','median'),
                q25_ms=('Time_ms',lambda v: float(np.quantile(v,.25))),
                q75_ms=('Time_ms',lambda v: float(np.quantile(v,.75))),
                trial_count=('Time_ms','size')))
byte_width = np.where(summary.Type == 'float64', 8, 4)
bytes_per_element = np.where(summary.Kernel == 'DotProduct', 2, 3) * byte_width
flops_per_element = np.where(summary.Kernel == 'Multiply', 1, 2)
summary['working_set_MiB'] = summary.N * summary.Stride * bytes_per_element / (2**20)
summary['GFLOP_s'] = summary.N * flops_per_element / (summary.median_ms / 1000) / 1e9
summary['logical_GiB_s'] = summary.N * bytes_per_element / (summary.median_ms / 1000) / (2**30)
summary['low_GFLOP_s'] = summary.N * flops_per_element / (summary.q75_ms / 1000) / 1e9
summary['high_GFLOP_s'] = summary.N * flops_per_element / (summary.q25_ms / 1000) / 1e9
if 'Thread_cycles_per_element' in trials:
    cy = (trials.groupby(key, as_index=False)
          .agg(cycles_per_element=('Thread_cycles_per_element','median')))
    summary = summary.merge(cy, on=key)
    summary.loc[summary.cycles_per_element <= 0, 'cycles_per_element'] = np.nan
else:
    summary['cycles_per_element'] = np.nan
join = ['Mode','Type','Kernel','N','Stride','Offset_bytes']
scalar = summary[summary.Build == 'scalar'][join + ['median_ms']].rename(columns={'median_ms':'scalar_ms'})
comparison = summary.merge(scalar, on=join, how='left')
comparison['speedup'] = comparison.scalar_ms / comparison.median_ms
summary.to_csv(OUT/'measurements.csv',index=False)
comparison.to_csv(OUT/'comparisons.csv',index=False)

KERNELS = ['SAXPY','Multiply','DotProduct']
BUILDS = ['scalar','default','native']
COLORS = {'scalar':'#64748b','default':'#0d9488','native':'#2563eb'}
KCOLORS = {'SAXPY':'#2563eb','Multiply':'#0d9488','DotProduct':'#d97706'}

def sub(mode, dtype='float32', kernel=None, build=None):
    x = comparison[(comparison.Mode==mode) & (comparison.Type==dtype)]
    if kernel is not None: x=x[x.Kernel==kernel]
    if build is not None: x=x[x.Build==build]
    return x

def publish(fig, filename):
    fig.savefig(FIG/filename,dpi=175,bbox_inches='tight')
    plt.close(fig)

def empty_panel(ax, message):
    ax.text(.5,.5,message,ha='center',va='center',transform=ax.transAxes,color='#64748b')
    ax.set_xticks([]);ax.set_yticks([])

plt.rcParams.update({'font.size':9, 'axes.titlesize':11, 'axes.labelsize':9,
                     'figure.facecolor':'white','axes.spines.top':False,
                     'axes.spines.right':False,'savefig.facecolor':'white'})

# FIGURE 1: Baseline SIMD speedup for each kernel / all three configurations.
fig, axs = plt.subplots(1,3,figsize=(13.0,3.7), sharey=True)
for ax,k in zip(axs,KERNELS):
    data=sub('baseline',kernel=k)
    for build in ['default','native']:
        r=data[data.Build==build].sort_values('N')
        if not r.empty: ax.plot(r.N,r.speedup,marker='o',ms=4,lw=1.7,color=COLORS[build],label=build)
    ax.axhline(1,ls=':',color='black',alpha=.55)
    ax.set_xscale('log');ax.set_title(k);ax.set_xlabel('Array elements (N)');ax.grid(alpha=.18)
axs[0].set_ylabel('Speedup vs scalar (×)')
axs[0].legend(title='GCC build',loc='best')
fig.suptitle('1. SIMD speedup across array sizes — float32',fontweight='bold')
fig.tight_layout();publish(fig,'01_speedup.png')

# FIGURE 2: Three kernels, all builds, native GFLOP/s and variability shading.
fig,axs=plt.subplots(1,3,figsize=(13.0,3.7), sharey=False)
for ax,k in zip(axs,KERNELS):
    data=sub('baseline',kernel=k)
    for build in BUILDS:
        r=data[data.Build==build].sort_values('N')
        if r.empty: continue
        ax.plot(r.N,r.GFLOP_s,marker='o',ms=3,lw=1.7,color=COLORS[build],label=build)
        ax.fill_between(r.N.to_numpy(dtype=float),r.low_GFLOP_s.to_numpy(dtype=float),r.high_GFLOP_s.to_numpy(dtype=float),color=COLORS[build],alpha=.12)
    ax.set_xscale('log');ax.set_xlabel('Array elements (N)');ax.set_title(k);ax.grid(alpha=.18)
    ax.set_ylabel('Achieved GFLOP/s')
axs[0].legend(title='Build',loc='best')
fig.suptitle('2. Throughput by kernel — shaded range = trial IQR, float32',fontweight='bold')
fig.tight_layout();publish(fig,'02_throughput.png')

# FIGURE 3: Locality sweep for ONE kernel, labeled approximate cache thresholds.
fig,ax=plt.subplots(figsize=(8.3,4.4))
data=sub('baseline',kernel='Multiply')
for build in ['default','native']:
    r=data[data.Build==build].sort_values('working_set_MiB')
    if not r.empty: ax.plot(r.working_set_MiB,r.speedup,marker='o',lw=2,ms=5,label=build,color=COLORS[build])
# These *illustrative* boundaries are not verified per-core cache measurements.
for val,name in [(48/1024,'L1?'),(1.25,'L2?'),(20,'L3 ≈20 MiB')]:
    ax.axvline(val,ls=':',lw=1,color='#64748b',alpha=.75)
    ax.text(val,0.98,name,ha='right',va='top',fontsize=8,rotation=90,transform=ax.get_xaxis_transform())
ax.axhline(1,ls='--',lw=.8,color='#64748b')
ax.set(xscale='log',xlabel='Total logical working set (MiB): x + y + z',ylabel='Speedup vs scalar (×)')
ax.set_title('3. Locality sweep — multiplication, float32')
ax.legend(title='Build');ax.grid(alpha=.18)
fig.text(.5,.005,'Cache boundary annotations are approximate; L1/L2 depend on core type and require verification.',ha='center',fontsize=8,color='#64748b')
fig.tight_layout(rect=[0,.045,1,1]);publish(fig,'03_locality.png')

# Tables for all three kernels and all alignment/tail sizes; one chart highlights representative cases.
al=sub('alignment',build='native')
penalties=[];tails=[]
for (kernel,n),g in al.groupby(['Kernel','N']):
    a=g[g.Offset_bytes==0]
    shifted=g[g.Offset_bytes>0]
    if len(a)==1 and len(shifted)==1:
        penalties.append({'Kernel':kernel,'N':int(n),
                          'aligned_ms':float(a.median_ms.iloc[0]),'shifted_ms':float(shifted.median_ms.iloc[0]),
                          'unaligned_over_aligned':float(shifted.median_ms.iloc[0]/a.median_ms.iloc[0])})
for kernel in KERNELS:
    for offset in [0,4]:
        g=al[(al.Kernel==kernel)&(al.Offset_bytes==offset)]
        for n in [16384,1048576,4194304]:
            a=g[g.N==n]; b=g[g.N==n+3]
            if len(a)==1 and len(b)==1:
                tails.append({'Kernel':kernel,'N':n,'Offset_bytes':offset,
                              'tail_over_no_tail_per_element':float((b.median_ms.iloc[0]/(n+3))/(a.median_ms.iloc[0]/n))})
pen=pd.DataFrame(penalties);tl=pd.DataFrame(tails)
if not pen.empty:pen.to_csv(OUT/'alignment_penalties.csv',index=False)
if not tl.empty:tl.to_csv(OUT/'tail_penalties.csv',index=False)
fig,axs=plt.subplots(1,2,figsize=(10.7,3.8))
def ratio_dots(ax, numbers, ylabel, title):
    y=np.asarray(numbers,dtype=float)
    positions=np.arange(len(KERNELS))
    ax.axhline(1,color='#475569',ls='--',lw=1)
    for idx,k in enumerate(KERNELS):
        if np.isfinite(y[idx]):
            ax.scatter(idx,y[idx],s=65,color=KCOLORS[k],zorder=3)
            ax.text(idx,y[idx],f' {y[idx]:.3f}×',va='bottom',ha='center',fontsize=8)
    valid=y[np.isfinite(y)]
    spread=max(.06, np.max(np.abs(valid-1))*1.45) if len(valid) else .1
    ax.set_ylim(max(0,1-spread),1+spread)
    ax.set_xlim(-.6,len(KERNELS)-.4)
    ax.set_xticks(positions,labels=KERNELS)
    ax.set(ylabel=ylabel,title=title)
    ax.grid(axis='y',alpha=.16)
if not pen.empty:
    r=pen[pen.N==1048576].set_index('Kernel').reindex(KERNELS)
    ratio_dots(axs[0],r.unaligned_over_aligned.to_numpy(),
               'Shifted / aligned time (×)','Shift by one float (4 bytes), N=1M')
else: empty_panel(axs[0],'Alignment data not found')
if not tl.empty:
    r=tl[(tl.N==16384)&(tl.Offset_bytes==0)].set_index('Kernel').reindex(KERNELS)
    ratio_dots(axs[1],r.tail_over_no_tail_per_element.to_numpy(),
               'Tail / no-tail time per element (×)','N=16,387 vs N=16,384 (aligned)')
else: empty_panel(axs[1],'Tail data not found')
fig.suptitle('4. Alignment and tail overhead — native, float32',fontweight='bold')
fig.tight_layout();publish(fig,'04_alignment_tails.png')

# FIGURE 5: Stride; each kernel / same N, speedup and logical bandwidth.
st=sub('stride',build='native')
fig,axs=plt.subplots(1,2,figsize=(10.8,3.8))
for k in KERNELS:
    r=st[(st.Kernel==k)&(st.N==1048576)].sort_values('Stride')
    if not r.empty:
        axs[0].plot(r.Stride,r.speedup,marker='o',lw=1.8,color=KCOLORS[k],label=k)
        axs[1].plot(r.Stride,r.logical_GiB_s,marker='o',lw=1.8,color=KCOLORS[k],label=k)
axs[0].axhline(1,ls='--',color='#475569',lw=1)
axs[0].set(ylabel='Native / scalar speedup (×)',title='SIMD benefit')
axs[1].set(ylabel='Effective logical GiB/s',title='Data-transfer efficiency')
for ax in axs:
    ax.set_xlabel('Stride (elements)');ax.set_xticks([1,2,4,8]);ax.grid(alpha=.18)
axs[1].legend(title='Kernel',loc='best')
fig.suptitle('5. Non-unit stride — 1,048,576 useful elements, float32',fontweight='bold')
fig.tight_layout();publish(fig,'05_stride.png')

# FIGURE 6: Data type comparison across baseline array sizes, all three kernels.
fig,axs=plt.subplots(1,3,figsize=(13,3.7))
for ax,k in zip(axs,KERNELS):
    for typ,c in [('float32','#2563eb'),('float64','#d97706')]:
        r=sub('baseline',dtype=typ,kernel=k,build='native').sort_values('N')
        if not r.empty:ax.plot(r.N,r.speedup,marker='o',ms=4,lw=1.8,color=c,label=typ)
    ax.axhline(1,ls=':',color='#64748b')
    ax.set(xscale='log',xlabel='Array elements (N)',ylabel='Native / scalar speedup (×)',title=k)
    ax.grid(alpha=.18)
axs[0].legend(title='Data type',loc='best')
fig.suptitle('6. Data type comparison — float32 versus float64',fontweight='bold')
fig.tight_layout();publish(fig,'06_float32_float64.png')

# FIGURE 7: preliminary measured-reference roofline; no invented measurements.
bw_file=RAW/'legacy_bandwidth_results.csv'
compute_file=RAW/'legacy_compute_results.csv'
if bw_file.is_file() and compute_file.is_file():
    bdf=pd.read_csv(bw_file);pdf=pd.read_csv(compute_file)
    bandwidth=float(bdf.GB_s.max()); compute=float(pdf.GFLOP_s.median())
    xx=np.logspace(-2,2,400)
    fig,ax=plt.subplots(figsize=(8.2,4.7))
    ax.plot(xx,np.minimum(compute,bandwidth*xx),lw=2.3,color='#2563eb',label='Estimated reference roofline')
    ax.axvline(1/12,color='#64748b',ls=':',lw=1)
    native=sub('baseline',kernel='Multiply',build='native').sort_values('N')
    for n,lab in [(1048576,'1M elements'),(16777216,'16M elements')]:
        p=native[native.N==n]
        if len(p)==1:
            ax.scatter(1/12,p.GFLOP_s.iloc[0],s=55,label=f'Multiply: {lab}',zorder=3)
    ax.set(xscale='log',yscale='log',xlabel='Arithmetic intensity (FLOP / logical byte)',ylabel='Achieved GFLOP/s',
           title='7. Roofline-style estimate — single-thread references')
    ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.text(.5,.005,f'Compute {compute:.1f} GFLOP/s; STREAM-style logical bandwidth {bandwidth:.1f} GB/s. Not a strict hardware bound.',ha='center',fontsize=8,color='#64748b')
    fig.tight_layout(rect=[0,.055,1,1]);publish(fig,'07_roofline.png')
else:
    print('Roofline reference files absent: copy legacy_bandwidth_results.csv and legacy_compute_results.csv into raw/.')

# One report-ready table, all kernels and all three builds at 3 representative Ns.
rows=[]
for k in KERNELS:
    for n in [16384,1048576,16777216]:
        t=sub('baseline',kernel=k)
        t=t[t.N==n]
        vals={b:t[t.Build==b].iloc[0] for b in BUILDS if len(t[t.Build==b])==1}
        if 'scalar' not in vals:continue
        row={'Kernel':k,'N':n}
        for b in BUILDS:
            if b in vals:
                row[f'{b}_ms']=round(float(vals[b].median_ms),5)
                row[f'{b}_GFLOP_s']=round(float(vals[b].GFLOP_s),3)
                row[f'{b}_speedup']=round(float(vals['scalar'].median_ms/vals[b].median_ms),3)
                row[f'{b}_cycles_per_element']=round(float(vals[b].cycles_per_element),3) if pd.notna(vals[b].cycles_per_element) else None
        rows.append(row)
report_table=pd.DataFrame(rows)
if not report_table.empty:
    report_table.to_csv(OUT/'report_numbers.csv',index=False)
    with open(OUT/'report_numbers.md','w',encoding='utf-8') as f:
        f.write('# Baseline comparisons for the final report (float32)\n\n')
        f.write('Median of raw trial times. Speedup >1 means faster than scalar.\n\n')
        cols=['Kernel','N','scalar_ms','default_ms','native_ms','default_speedup','native_speedup','native_GFLOP_s','native_cycles_per_element']
        for line in [ '| ' + ' | '.join(cols) + ' |', '|'+'|'.join(['---']*len(cols))+'|']:
            f.write(line+'\n')
        for _,r in report_table.iterrows():
            f.write('| '+' | '.join(('n/a' if pd.isna(r.get(col,np.nan)) else str(r.get(col))) for col in cols)+' |\n')
        f.write('\nSupplementary measurements (including thread cycles per element when available) are in `report_numbers.csv`.\n')
print(f'OK: analyzed {len(trials)} validated trials from {len(paths)} files.')
print(f'Created {len(list(FIG.glob("*.png")))} charts in figures/final/ and tables in processed/final/.')
