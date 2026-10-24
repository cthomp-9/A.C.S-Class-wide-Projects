import json
import csv
from pathlib import Path

root = Path(__file__).resolve().parent.parent
raw = root / "data" / "raw"
processed = root / "data" / "processed"
processed.mkdir(exist_ok=True)

rows = []
failed = []

for file in sorted(raw.glob("*.json")):
    if not file.stem.endswith(("trial1", "trial2", "trial3")):
        continue

    try:
        text = file.read_text(encoding="utf-8-sig")
        data = json.loads(text[text.index("{"):])
        job = data["jobs"][0]

        if job["error"] != 0:
            raise ValueError("FIO error")

        read = job["read"]
        write = job["write"]

        total_ios = read["total_ios"] + write["total_ios"]
        if total_ios == 0:
            raise ValueError("No completed I/O")

        iops = read["iops"] + write["iops"]
        bandwidth = (
            read["bw_bytes"] + write["bw_bytes"]
        ) / 1000000

        latencies = []
        for io in (read, write):
            if io["total_ios"] > 0:
                lat = io.get("lat_ns", {})
                clat = io.get("clat_ns", {})
                latencies.append((
                    io["total_ios"],
                    lat.get("mean", 0),
                    clat.get("percentile", {})
                ))

        avg_latency = sum(
            n * mean for n, mean, _ in latencies
        ) / total_ios / 1000000

        def percentile(p):
            # Mixed workloads have separate read/write distributions.
            # Do not combine their percentiles mathematically.
            if len(latencies) != 1:
                return ""
            values = latencies[0][2]
            return values.get(p, "")

        rows.append({
            "test": file.stem,
            "iops": round(iops, 2),
            "MBps": round(bandwidth, 2),
            "latency_ms": round(avg_latency, 5),
            "p50_ns": percentile("50.000000"),
            "p95_ns": percentile("95.000000"),
            "p99_ns": percentile("99.000000"),
            "p999_ns": percentile("99.900000"),
        })

    except Exception as e:
        failed.append((file.name, str(e)))

output = processed / "results.csv"

with output.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "test", "iops", "MBps", "latency_ms",
        "p50_ns", "p95_ns", "p99_ns", "p999_ns"
    ])
    writer.writeheader()
    writer.writerows(rows)

print("Valid results:", len(rows))
print("Failed results:", len(failed))
print("CSV saved:", output)

for name, error in failed:
    print("FAILED:", name, error)
