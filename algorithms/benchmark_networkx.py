"""Benchmark lance-csr + icebug against networkx, from Lance tables to a results table.

Each run starts in a fresh process and records, after every stage, the elapsed time and the
process's peak resident memory so far (the kernel's high-water mark, not a sampled value).
The stage at which the peak jumps is the stage that allocated it, so the export's own
materialization shows up separately from the algorithm's.

Data: Person (100k nodes) and FOLLOWS (2.4M edges) from
https://github.com/prrao87/graph-benchmark, built with its `lance_csr/build_graph.py` and
expected in a sibling checkout (or pass the path). From the repository root:
  uv run --group bench python algorithms/benchmark_networkx.py [path/to/graph_lance]
For the scale-up, run make_synthetic_graph.py first, then:
  uv run --group bench python algorithms/benchmark_networkx.py \
    algorithms/output/synthetic_graph --icebug-only
On macOS icebug also needs `brew install libomp`.
"""

import json
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT.parent / "graph-benchmark" / "lance_csr" / "graph_lance"
OUT_DIR = ROOT / "algorithms" / "output"
ALGORITHMS = ["pagerank", "components", "louvain"]
LIBRARIES = ["networkx", "icebug"]
RUNS = 3  # measured runs per case, after one warm-up run


def peak_mib() -> float:
    # ru_maxrss is in bytes on macOS and in KiB on Linux.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 2**20 if sys.platform == "darwin" else rss / 2**10


class Stages:
    def __init__(self) -> None:
        self.rows: list[dict] = [{"stage": "imports", "seconds": 0.0, "peak_mib": peak_mib()}]
        self.start = time.perf_counter()

    def mark(self, stage: str) -> None:
        now = time.perf_counter()
        self.rows.append({"stage": stage, "seconds": now - self.start, "peak_mib": peak_mib()})
        self.start = now


def run_networkx(data: Path, algorithm: str) -> tuple[list[dict], dict]:
    import lance
    import networkx as nx
    import pyarrow as pa

    s = Stages()
    ids = lance.dataset(data / "Person.lance").to_table(columns=["id"])["id"].to_pylist()
    edges = lance.dataset(data / "FOLLOWS.lance").to_table(columns=["src", "dst"])
    s.mark("read Lance")
    # PageRank follows edge direction; components and Louvain treat follows as undirected.
    graph = nx.DiGraph() if algorithm == "pagerank" else nx.Graph()
    graph.add_nodes_from(ids)
    graph.add_edges_from(zip(edges["src"].to_pylist(), edges["dst"].to_pylist()))
    del edges
    s.mark("build graph")
    if algorithm == "pagerank":
        values = nx.pagerank(graph)
    elif algorithm == "components":
        values = {n: i for i, c in enumerate(nx.connected_components(graph)) for n in c}
    else:
        communities = nx.community.louvain_communities(graph, seed=42)
        values = {n: i for i, c in enumerate(communities) for n in c}
    s.mark("algorithm")
    table = pa.table({"id": list(values), "value": list(values.values())})
    s.mark("results table")
    extra = {}
    if algorithm == "louvain":
        extra["modularity"] = nx.community.modularity(graph, communities)
    return s.rows, {"table": table, **extra}


def run_icebug(data: Path, algorithm: str) -> tuple[list[dict], dict]:
    import icebug as ib
    import lance
    import pyarrow as pa
    from lance_csr import CypherEngine, GraphConfig

    s = Stages()
    config = (
        GraphConfig.builder()
        .node_table("Person", "id")
        .rel_table("FOLLOWS", "Person", "Person", "src", "dst")
        .build()
    )
    engine = CypherEngine(
        config,
        {name: lance.dataset(data / f"{name}.lance") for name in ("Person", "FOLLOWS")},
    )
    s.mark("open engine")
    g = engine.export_graph(directed=algorithm == "pagerank")
    s.mark("export_graph")
    if algorithm == "pagerank":
        graph = ib.Graph.fromCSR(
            g.num_nodes, True, g.out_indices, g.out_indptr, g.in_indices, g.in_indptr
        )
    else:
        graph = ib.Graph.fromCSR(g.num_nodes, False, g.out_indices, g.out_indptr)
    s.mark("fromCSR")
    if algorithm == "pagerank":
        sinks = ib.centrality.SinkHandling.DistributeSinks
        values = ib.centrality.PageRank(graph, distributeSinks=sinks).run().scores()
    elif algorithm == "components":
        partition = ib.components.ConnectedComponents(graph).run().getPartition()
        values = partition.getVector()
    else:
        ib.engineering.setSeed(42, False)
        partition = ib.community.PLM(graph, refine=True).run().getPartition()
        values = partition.getVector()
    s.mark("algorithm")
    table = pa.table({"id": g.node_keys, "value": values})
    s.mark("results table")
    extra = {}
    if algorithm == "louvain":
        extra["modularity"] = ib.community.Modularity().getQuality(partition, graph)
    return s.rows, {"table": table, **extra}


def child(library: str, algorithm: str, data: Path, save: bool) -> None:
    rows, result = (run_networkx if library == "networkx" else run_icebug)(data, algorithm)
    if save:  # numpy, not Parquet: pyarrow's filesystem clashes with Lance's in one process
        import numpy as np

        t = result["table"]
        np.savez(OUT_DIR / f"bench_{library}_{algorithm}.npz", id=t["id"], value=t["value"])
    print(json.dumps({"stages": rows, "modularity": result.get("modularity")}))


def run_case(library: str, algorithm: str, data: Path) -> list[dict]:
    runs = []
    for i in range(RUNS + 1):
        cmd = [sys.executable, __file__, "--child", library, algorithm, str(data)]
        if i == RUNS:
            cmd.append("--save")
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        if i > 0:  # the first run warms the file cache and is discarded
            runs.append(json.loads(out.strip().splitlines()[-1]))
    return runs


def check_results() -> None:
    import numpy as np

    def load(library: str, algorithm: str):
        f = np.load(OUT_DIR / f"bench_{library}_{algorithm}.npz")
        order = np.argsort(f["id"])
        return f["id"][order], f["value"][order]

    (nx_id, nx_pr), (ib_id, ib_pr) = load("networkx", "pagerank"), load("icebug", "pagerank")
    assert (nx_id == ib_id).all()
    print(f"PageRank max abs difference: {np.abs(nx_pr - ib_pr).max():.2e}")

    (_, nx_cc), (_, ib_cc) = load("networkx", "components"), load("icebug", "components")
    pairs = set(zip(nx_cc.tolist(), ib_cc.tolist()))
    same = len(pairs) == len(set(nx_cc.tolist())) == len(set(ib_cc.tolist()))
    print(f"Components: {len(set(nx_cc.tolist()))} components, same partition: {same}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data = Path(args[0]) if args else DEFAULT_DATA
    # --icebug-only: skip networkx, for graphs too large for it to fit in memory.
    libraries = ["icebug"] if "--icebug-only" in sys.argv else LIBRARIES
    OUT_DIR.mkdir(exist_ok=True)
    report = {}
    for algorithm in ALGORITHMS:
        for library in libraries:
            runs = run_case(library, algorithm, data)
            stages = [r["stage"] for r in runs[0]["stages"]]
            median = {
                stage: {
                    "seconds": statistics.median(r["stages"][i]["seconds"] for r in runs),
                    "peak_mib": statistics.median(r["stages"][i]["peak_mib"] for r in runs),
                }
                for i, stage in enumerate(stages)
            }
            total = sum(v["seconds"] for v in median.values())
            report[f"{library}/{algorithm}"] = {
                "stages": median,
                "total_seconds": total,
                "modularity": runs[0]["modularity"],
            }
            print(f"\n{library} {algorithm}: {total:.3f} s total")
            for stage, v in median.items():
                print(f"  {stage:<14} {v['seconds']:8.3f} s   peak so far {v['peak_mib']:8.0f} MiB")
            if runs[0]["modularity"] is not None:
                print(f"  modularity {runs[0]['modularity']:.3f}")
    (OUT_DIR / f"benchmark_{data.name}.json").write_text(json.dumps(report, indent=2))
    if libraries == LIBRARIES:
        print()
        check_results()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3], Path(sys.argv[4]), "--save" in sys.argv)
    else:
        main()
