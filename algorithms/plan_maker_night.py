"""Plan the next Maker Night with graph algorithms over the same Lance tables.

Maya wants a table for each social group, and one host per table: the person whose friendships
most often link the groups. Louvain finds the groups and betweenness centrality finds the
hosts, both computed by icebug from the CSR arrays that `export_graph` builds. The results go
back into `Person` as columns, so one Cypher query returns each host's name and portrait.

Run `uv run python src/build_dataset.py` first, then from the repository root:
  uv run python algorithms/plan_maker_night.py
On macOS icebug also needs `brew install libomp`.
"""

import io
import sys
from pathlib import Path

import icebug as ib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from maker_night import open_engine

OUT_DIR = ROOT / "algorithms" / "output"


def main() -> None:
    engine = open_engine()

    # Friendships have no direction: the undirected export lists each one both ways.
    g = engine.export_graph(directed=False)
    graph = ib.Graph.fromCSR(g.num_nodes, False, g.out_indices, g.out_indptr)
    print(f"{g.num_nodes} people, {graph.numberOfEdges()} friendships")

    ib.engineering.setSeed(42, False)  # Louvain breaks ties randomly; fix them for the post.
    partition = ib.community.PLM(graph, refine=True).run().getPartition()
    groups = partition.getVector()
    betweenness = ib.centrality.Betweenness(graph, normalized=True).run().scores()
    print(
        f"{partition.numberOfSubsets()} groups, modularity {ib.community.Modularity().getQuality(partition, graph):.3f}"
    )

    engine.write_node_column(g, "table_group", groups, overwrite=True)
    engine.write_node_column(g, "betweenness", betweenness, overwrite=True)

    # The algorithm results are now ordinary columns, next to names, interests and portraits.
    members = engine.execute(
        "MATCH (p:Person) RETURN p.table_group AS table_group, p.name AS name, "
        "p.interests AS interests, p.betweenness AS betweenness "
        "ORDER BY table_group, betweenness DESC"
    ).to_pylist()
    for row in members:
        print(
            f"table {row['table_group']}  {row['name']:<10} {row['betweenness']:.3f}  "
            f"{', '.join(row['interests'])}"
        )

    # One fetch: each table's host, with the portrait bytes stored in the same row.
    hosts = engine.execute(
        "MATCH (p:Person) WITH p.table_group AS table_group, max(p.betweenness) AS top "
        "MATCH (h:Person) WHERE h.table_group = table_group AND h.betweenness = top "
        "RETURN table_group, h.name AS name, h.portrait AS portrait ORDER BY table_group"
    ).to_pylist()
    # The answer quoted in the post (seed 42, icebug 13.6).
    assert [h["name"] for h in hosts] == ["Elliott", "Ines", "Pedro", "Kenneth"], hosts

    OUT_DIR.mkdir(exist_ok=True)
    sheet = Image.new("RGB", (256 * len(hosts), 256), "white")
    for i, host in enumerate(hosts):
        print(f"host of table {host['table_group']}: {host['name']}")
        sheet.paste(Image.open(io.BytesIO(host["portrait"])), (256 * i, 0))
    sheet.save(OUT_DIR / "table_hosts.png")


if __name__ == "__main__":
    main()
