
import re
from pathlib import Path
from statistics import mean, stdev
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

# Figure 1: Working-set size vs latency
file_path = RAW / "working_set_sweep.txt"
raw_bytes = file_path.read_bytes()

if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
    text = raw_bytes.decode("utf-16")
elif raw_bytes.count(b"\x00") > len(raw_bytes) // 10:
    text = raw_bytes.decode("utf-16-le")
else:
    text = raw_bytes.decode("utf-8-sig", errors="replace")

# Extract buffer sizes from the trial headings
sizes_found = re.findall(r"Buffer:\s*(\d+)\s*KiB", text)

# Extract latency values from the MLC output
latencies_found = re.findall(
    r"Each iteration took.*?\(\s*([\d.]+)\s+ns\s*\)",
    text
)

print("Buffer entries found:", len(sizes_found))
print("Latency entries found:", len(latencies_found))

if not sizes_found or len(sizes_found) != len(latencies_found):
    raise RuntimeError("Working-set data could not be parsed correctly.")

working_sets = {}

for size, latency in zip(sizes_found, latencies_found):
    working_sets.setdefault(int(size), []).append(float(latency))

sizes = sorted(working_sets)
latencies = [mean(working_sets[size]) for size in sizes]

plt.figure(figsize=(9, 5))
plt.plot(sizes, latencies, marker="o")
plt.xscale("log", base=2)
plt.xlabel("Working-set size (KiB)")
plt.ylabel("Average latency (ns)")
plt.title("Memory Latency vs Working-Set Size")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES / "working_set_latency.png", dpi=200)
plt.close()

# Figure 2: Bandwidth vs loaded latency
file_path = RAW / "loaded_latency_5trials.txt"
raw_bytes = file_path.read_bytes()

if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
    text = raw_bytes.decode("utf-16")
elif raw_bytes.count(b"\x00") > len(raw_bytes) // 10:
    text = raw_bytes.decode("utf-16-le")
else:
    text = raw_bytes.decode("utf-8-sig", errors="replace")

pattern = re.compile(
    r"^\s*(\d{5})\s+([\d.]+)\s+([\d.]+)\s*$",
    re.MULTILINE,
)

loaded = {}
for delay, latency, bandwidth in pattern.findall(text):
    loaded.setdefault(int(delay), []).append(
        (float(latency), float(bandwidth) / 1000)
    )

if not loaded:
    raise RuntimeError("No loaded-latency measurements found.")

points = [
    (
        mean(row[1] for row in trials),
        mean(row[0] for row in trials),
    )
    for trials in loaded.values()
]

points.sort()
bandwidths = [point[0] for point in points]
loaded_latencies = [point[1] for point in points]

plt.figure(figsize=(9, 5))
plt.plot(bandwidths, loaded_latencies, marker="o")
plt.xlabel("Bandwidth (GB/s)")
plt.ylabel("Average loaded latency (ns)")
plt.title("Loaded Latency vs Memory Bandwidth")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES / "throughput_latency.png", dpi=200)
plt.close()

print("Working-set sizes parsed:", len(sizes))
print("Loaded-latency injection delays parsed:", len(loaded))
print("Figures saved to:", FIGURES)


# Figures 3 and 4: Access pattern vs stride size

def read_mlc_file(filename):
    """Read PowerShell-generated files in UTF-8 or UTF-16."""
    raw_bytes = (RAW / filename).read_bytes()

    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw_bytes.decode("utf-16")
    elif raw_bytes.count(b"\x00") > len(raw_bytes) // 10:
        return raw_bytes.decode("utf-16-le")
    else:
        return raw_bytes.decode("utf-8-sig", errors="replace")


strides = [64, 256, 1024]
patterns = ["Sequential", "Random"]

bandwidth_results = {}
latency_results = {}

for access_pattern in patterns:
    bandwidth_results[access_pattern] = []
    latency_results[access_pattern] = []

    for stride in strides:

        # Read bandwidth measurements
        filename = f"bandwidth_{access_pattern}_{stride}B.txt"
        text = read_mlc_file(filename)

        # Extract injection-delay-zero bandwidth from each trial
        bw_values = re.findall(
            r"^\s*00000\s+[\d.]+\s+([\d.]+)\s*$",
            text,
            re.MULTILINE
        )

        if len(bw_values) != 3:
            raise RuntimeError(
                f"Expected 3 bandwidth trials in {filename}; "
                f"found {len(bw_values)}"
            )

        # Convert MB/s to GB/s
        bandwidth_results[access_pattern].append(
            mean(float(value) for value in bw_values) / 1000
        )

        # Read idle-latency measurements
        filename = f"latency_{access_pattern}_{stride}B.txt"
        text = read_mlc_file(filename)

        latency_values = re.findall(
            r"Each iteration took[^\n]*"
            r"\(\s*([\d.]+)\s+ns\s*\)",
            text
        )

        if len(latency_values) != 3:
            raise RuntimeError(
                f"Expected 3 latency trials in {filename}; "
                f"found {len(latency_values)}"
            )

        latency_results[access_pattern].append(
            mean(float(value) for value in latency_values)
        )


# Figure 3: Bandwidth comparison
plt.figure(figsize=(9, 5))

for access_pattern in patterns:
    plt.plot(
        strides,
        bandwidth_results[access_pattern],
        marker="o",
        label=access_pattern
    )

plt.xscale("log", base=2)
plt.xticks(strides, [str(s) for s in strides])
plt.xlabel("Stride size (bytes)")
plt.ylabel("Average bandwidth (GB/s)")
plt.title("Sequential vs Random Access: Bandwidth")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES / "access_pattern_bandwidth.png", dpi=200)
plt.close()


# Figure 4: Latency comparison
plt.figure(figsize=(9, 5))

for access_pattern in patterns:
    plt.plot(
        strides,
        latency_results[access_pattern],
        marker="o",
        label=access_pattern
    )

plt.xscale("log", base=2)
plt.xticks(strides, [str(s) for s in strides])
plt.xlabel("Stride size (bytes)")
plt.ylabel("Average latency (ns)")
plt.title("Sequential vs Random Access: Latency")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIGURES / "access_pattern_latency.png", dpi=200)
plt.close()


print("Access-pattern bandwidth results (GB/s):", bandwidth_results)
print("Access-pattern latency results (ns):", latency_results)
print("Access-pattern figures saved successfully.")


# Figure 5: Read/write bandwidth comparison

mix_files = {
    "100% Read": "mix_100_Read.txt",
    "100% Write (NT)": "mix_100_Write_NT.txt",
    "50% Read / 50% Write": "mix_50_Read_50_Write.txt",
}

mix_bandwidth = {}

for workload, filename in mix_files.items():
    text = read_mlc_file(filename)

    # Extract bandwidth at injection delay 00000 for each trial
    values = re.findall(
        r"^\s*00000\s+[\d.]+\s+([\d.]+)\s*$",
        text,
        re.MULTILINE
    )

    if len(values) != 5:
        raise RuntimeError(
            f"Expected 5 trials in {filename}, found {len(values)}"
        )

    # Convert MB/s to GB/s and average the trials
    mix_bandwidth[workload] = mean(float(v) for v in values) / 1000

plt.figure(figsize=(9, 5))

bars = plt.bar(
    list(mix_bandwidth.keys()),
    list(mix_bandwidth.values())
)

plt.ylabel("Average bandwidth (GB/s)")
plt.title("Read/Write Traffic Mix vs Memory Bandwidth")
plt.xticks(rotation=10)
plt.grid(axis="y", alpha=0.3)

for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:.2f}",
        ha="center",
        va="bottom"
    )

plt.tight_layout()
plt.savefig(FIGURES / "read_write_bandwidth.png", dpi=200)
plt.close()

print("Read/write bandwidth results (GB/s):", mix_bandwidth)
print("Read/write bandwidth figure saved successfully.")
