"""The post's multi-hop question: how can Maya get introduced to Pedro?

They are three friendships apart, through two shortest chains. The same Cypher query is planned with the
CSR index off and on, and the physical plans are compared: a pair of hash joins per hop without
the CSR, one `CsrExpandExec` per hop with it. Run `build_dataset.py` first.
"""

from lance_csr import CypherEngine

from maker_night import GRAPH, open_datasets

DISTANCE_QUERY = """
MATCH path = shortestPath((m:Person {name: 'Maya'})-[:FRIEND_OF*]-(p:Person {name: 'Pedro'}))
RETURN length(path) AS introductions
"""

# Fixed at three hops, the distance found above. Every chain is returned, not just one.
CHAINS_QUERY = """
MATCH (m:Person {name: 'Maya'})-[:FRIEND_OF]-(a:Person)-[:FRIEND_OF]-(b:Person)
      -[:FRIEND_OF]-(p:Person {name: 'Pedro'})
RETURN a.name AS ask_first, b.name AS who_knows_pedro
ORDER BY ask_first
"""

OPERATORS = ("HashJoinExec", "CsrExpandExec", "LanceRead")


def plan_counts(engine: CypherEngine) -> dict[str, int]:
    physical = engine.explain(CHAINS_QUERY).split("physical_plan")[-1]
    return {op: physical.count(f"{op}:") for op in OPERATORS}


def main() -> None:
    with_csr = CypherEngine(GRAPH, open_datasets(), use_csr=True)
    without_csr = CypherEngine(GRAPH, open_datasets(), use_csr=False)

    hops = with_csr.execute(DISTANCE_QUERY).to_pylist()[0]["introductions"]
    chains = [list(r.values()) for r in with_csr.execute(CHAINS_QUERY).to_pylist()]
    assert chains == [list(r.values()) for r in without_csr.execute(CHAINS_QUERY).to_pylist()]
    assert hops == 3 and chains == [["Leo", "Abby"], ["Nina", "Omar"]], (hops, chains)
    print(f"Maya and Pedro are {hops} friendships apart:")
    for chain in chains:
        print(f"  Maya → {' → '.join(chain)} → Pedro")

    off, on = plan_counts(without_csr), plan_counts(with_csr)
    assert off == {"HashJoinExec": 6, "CsrExpandExec": 0, "LanceRead": 10}, off
    assert on == {"HashJoinExec": 1, "CsrExpandExec": 3, "LanceRead": 2}, on
    assert with_csr.csr_stats()["FRIEND_OF"]["edges"] == 44  # Followed both ways: edges=88.
    print("\nPhysical plan     hash joins  CSR lookups  read operators")
    for label, c in (("Without the CSR", off), ("With the CSR", on)):
        print(f"{label:17s} {c['HashJoinExec']:10d} {c['CsrExpandExec']:12d} {c['LanceRead']:12d}")


if __name__ == "__main__":
    main()
