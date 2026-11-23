"""Write a large synthetic follower graph as Lance tables, for the scale-up benchmark.

Person has `id` 0..N-1; FOLLOWS has `src` and `dst`. Sources are uniform, and destinations
are skewed towards low ids (dst = N * u**3 for uniform u), so the first rows are hubs with
many followers, as in real social graphs. Duplicate edges and self-loops are left in, as the
export removes them.

  uv run python algorithms/make_synthetic_graph.py [nodes] [edges]
Defaults to 4M nodes and 69M edges, written to algorithms/output/synthetic_graph.
"""

import sys
from pathlib import Path

import lance
import numpy as np
import pyarrow as pa

OUT = Path(__file__).resolve().parent / "output" / "synthetic_graph"
CHUNK = 10_000_000
SCHEMA = pa.schema([("src", pa.int64()), ("dst", pa.int64())])


def main() -> None:
    nodes = int(sys.argv[1]) if len(sys.argv) > 1 else 4_000_000
    edges = int(sys.argv[2]) if len(sys.argv) > 2 else 69_000_000
    rng = np.random.default_rng(42)
    OUT.mkdir(parents=True, exist_ok=True)
    lance.write_dataset(
        pa.table({"id": np.arange(nodes, dtype=np.int64)}), OUT / "Person.lance", mode="overwrite"
    )

    def batches():
        for start in range(0, edges, CHUNK):
            size = min(CHUNK, edges - start)
            src = rng.integers(0, nodes, size, dtype=np.int64)
            dst = (nodes * rng.random(size) ** 3).astype(np.int64)
            yield pa.record_batch([src, dst], schema=SCHEMA)

    reader = pa.RecordBatchReader.from_batches(SCHEMA, batches())
    lance.write_dataset(reader, OUT / "FOLLOWS.lance", mode="overwrite")
    print(f"{nodes:,} nodes, {edges:,} edges in {OUT}")


if __name__ == "__main__":
    main()
