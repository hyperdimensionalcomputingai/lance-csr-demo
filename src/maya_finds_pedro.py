"""The post's hypervector search: Maya half-remembers a man she saw at Maker Night.

She is sure he's a man, so that stays an exact Cypher filter. Everything else is a cue in a
query hypervector (see `encode_context.clue`), and lance-csr ranks the filtered rows by cosine
similarity to it with `execute_with_vector_rerank`:

    q = hair ⊕ robotics ⊕ ρ(a friend in photography)

The shortlist is person IDs, so two Cypher queries then check each candidate in the graph: their
hair and friends, and the shortest chain of friendships from Maya. With the hair misremembered
as dark brown, Pedro stays on the shortlist and the graph shows which cue was off.
Run `build_dataset.py` and `encode_context.py` first.
"""

from lance_csr import CypherEngine, DistanceMetric, VectorSearch

from encode_context import bundle, clue
from maker_night import open_engine

TOP_K = 3

# Each cue: what Maya would say, then (key, value, hops from the man she's looking for).
CUES = [
    ("Black hair", "hair", "Black", 0),
    ("Into robotics", "interest", "robotics", 0),
    ("A friend into photography", "interest", "photography", 1),
]
MISREMEMBERED = [("Dark brown hair", "hair", "Dark brown", 0), CUES[1], CUES[2]]

CANDIDATES_QUERY = """
MATCH (p:Person) WHERE p.gender = 'male'
RETURN p.person_id AS id, p.name AS name, p.context_hv
"""

FRIENDS_QUERY = """
MATCH (p:Person)-[:FRIEND_OF]-(f:Person)
WHERE p.person_id IN $ids
RETURN p.name AS name, p.hair_colour AS hair, f.name AS friend, f.interests AS friend_interests
ORDER BY name, friend
"""

CHAIN_TO_MAYA_QUERY = """
MATCH path = shortestPath((m:Person {name: 'Maya'})-[:FRIEND_OF*]-(p:Person))
WHERE p.person_id IN $ids
RETURN p.name AS name, [n IN nodes(path) | n.name] AS chain
"""


def propose(engine: CypherEngine, cues: list[tuple]) -> list[dict]:
    """The men whose context hypervector is most similar to the cues."""
    q = bundle([clue(key, value, hops) for _, key, value, hops in cues])
    search = (
        VectorSearch("p.context_hv")
        .query_vector(q.tolist())
        .metric(DistanceMetric.Cosine)
        .top_k(TOP_K)
        .include_distance(True)
    )
    rows = engine.execute_with_vector_rerank(CANDIDATES_QUERY, search).to_pylist()
    return [{"id": r["id"], "name": r["name"], "score": 1 - r["_distance"]} for r in rows]


def check(engine: CypherEngine, shortlist: list[dict]) -> dict[str, dict]:
    """What the graph says about each proposed person: hair, friends, and the chain from Maya."""
    ids = {"ids": [p["id"] for p in shortlist]}
    facts = {p["name"]: {"friends": []} for p in shortlist}
    for r in engine.execute(FRIENDS_QUERY, ids).to_pylist():
        facts[r["name"]]["hair"] = r["hair"]
        facts[r["name"]]["friends"].append((r["friend"], r["friend_interests"]))
    for r in engine.execute(CHAIN_TO_MAYA_QUERY, ids).to_pylist():
        facts[r["name"]]["chain"] = r["chain"]
    return facts


def names(shortlist: list[dict]) -> list[str]:
    return [p["name"] for p in shortlist]


def main() -> None:
    engine = open_engine()
    steps = [propose(engine, CUES[:i]) for i in range(1, len(CUES) + 1)]
    wrong = propose(engine, MISREMEMBERED)
    facts = check(engine, wrong)

    print("Hypervectors propose, one more cue each time:\n")
    for i, ((cue, *_), rows) in enumerate(zip(CUES, steps)):
        shown = ", ".join(f"{r['name']} {r['score']:.2f}" for r in rows)
        print(f"  {'+ ' if i else '  '}{cue:26s} -> {shown}")
    shown = ", ".join(f"{r['name']} {r['score']:.2f}" for r in wrong)
    print(f"\n  With dark brown hair (mistaken) -> {shown}")

    print("\nThe graph checks the mistaken shortlist:\n")
    for name, f in facts.items():
        friends = ", ".join(f"{friend} ({'/'.join(i)})" for friend, i in f["friends"])
        print(f"  {name}: {f['hair'].lower()} hair; friends: {friends}")
        print(f"    from Maya: {' – '.join(f['chain'])}")

    # Verified shortlists shown in the post, in descending cosine similarity.
    assert names(steps[0]) == ["Xi", "Pedro", "Boris"], steps[0]
    assert names(steps[1]) == ["Boris", "Pedro", "Xi"], steps[1]
    assert names(steps[2]) == ["Pedro", "Boris", "Leo"], steps[2]
    assert names(wrong) == ["William", "Elliott", "Pedro"], wrong
    photographers = {n: [f for f, i in facts[n]["friends"] if "photography" in i] for n in facts}
    assert photographers == {"William": ["Pedro"], "Elliott": [], "Pedro": ["Carla", "Omar"]}, (
        photographers
    )
    assert facts["Pedro"]["hair"] == "Black"
    assert facts["Pedro"]["chain"] == ["Maya", "Nina", "Omar", "Pedro"], facts["Pedro"]["chain"]
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
