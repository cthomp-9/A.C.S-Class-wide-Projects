import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

root = Path(__file__).resolve().parent.parent
df = pd.read_csv(root / "data/processed/results.csv")
out = root / "figures"
out.mkdir(exist_ok=True)

def save(name):
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / name, dpi=150)
    plt.close()

# 1 and 2: Block-size throughput and latency
blocks = df[df.test.str.startswith("block_")].copy()
blocks[["bs", "pattern"]] = blocks.test.str.extract(
    r"block_(\d+k)_(randread|randwrite|read|write)_trial\d+"
)
blocks["size_kib"] = blocks.bs.str.replace("k", "").astype(int)

for metric, ylabel, filename in [
    ("MBps", "Throughput (MB/s)", "block_throughput.png"),
    ("latency_ms", "Average latency (ms)", "block_latency.png")
]:
    plt.figure()
    for pattern, group in blocks.groupby("pattern"):
        stats = group.groupby("size_kib")[metric].agg(["mean", "std"])
        plt.errorbar(stats.index, stats["mean"],
                     yerr=stats["std"], marker="o", capsize=3,
                     label=pattern)
    plt.xscale("log", base=2)
    plt.xlabel("Block size (KiB)")
    plt.ylabel(ylabel)
    plt.title("SSD Block-size Sweep (QD=1)")
    plt.legend()
    save(filename)

# 3: Read/write mix
mix = df[df.test.str.match(r"^mix_\d+_trial\d+$")].copy()
mix["read_pct"] = mix.test.str.extract(r"mix_(\d+)_").astype(int)
stats = mix.groupby("read_pct").MBps.agg(["mean", "std"]).sort_index()
plt.figure()
plt.bar(stats.index.astype(str), stats["mean"],
        yerr=stats["std"], capsize=4)
plt.xlabel("Read percentage (%)")
plt.ylabel("Throughput (MB/s)")
plt.title("4 KiB Random Read/Write Mix (QD=16)")
save("read_write_mix.png")

# 4 and 5: Queue-depth throughput and latency
qd = df[df.test.str.match(r"^qd_\d+_trial\d+$")].copy()
qd["depth"] = qd.test.str.extract(r"qd_(\d+)_").astype(int)

for metric, ylabel, filename in [
    ("iops", "IOPS", "qd_iops.png"),
    ("latency_ms", "Average latency (ms)", "qd_latency.png")
]:
    stats = qd.groupby("depth")[metric].agg(["mean", "std"])
    plt.figure()
    plt.errorbar(stats.index, stats["mean"],
                 yerr=stats["std"], marker="o", capsize=3)
    plt.xscale("log", base=2)
    plt.axvline(32, linestyle="--", label="Approximate knee: QD=32")
    plt.xlabel("Queue depth")
    plt.ylabel(ylabel)
    plt.title("4 KiB Random Read Queue-depth Sweep")
    plt.legend()
    save(filename)

# 6: Tail latency at QD=16 and QD=32
tail = qd[qd.depth.isin([16, 32])]
columns = ["p50_ns", "p95_ns", "p99_ns", "p999_ns"]
labels = ["p50", "p95", "p99", "p99.9"]

plt.figure()
for depth, group in tail.groupby("depth"):
    values = group[columns].mean().to_numpy() / 1000000
    plt.plot(labels, values, marker="o", label=f"QD={depth}")

plt.xlabel("Latency percentile")
plt.ylabel("Completion latency (ms)")
plt.title("SSD Tail Latency")
plt.legend()
save("tail_latency.png")

print("Created 6 graphs in:", out)
