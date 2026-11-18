"""Encode what is known about each person and the people around them as one hypervector.

Each person's vector holds their own facts, their friends' facts, and the facts of people two
and three introductions away:

    h_p = n(facts(p)) ⊕ ρ(n(⨁ facts at 1 hop))
          ⊕ ρ²(n(⨁ facts at 2 hops)) ⊕ ρ³(n(⨁ facts at 3 hops))

    facts(x) = (h_name ⊗ h_name=x) ⊕ (h_hair ⊗ h_hair=…) ⊕ (h_eyes ⊗ h_eyes=…)
               ⊕ ⨁ (h_interest ⊗ h_interest=…)

⊗ is binding (element-wise product for MAP vectors), ⊕ is bundling (computed as an element-wise
sum). The permutation ρ is applied once per hop to mark how far away a fact is.
n(·) scales a bundle to unit length.

`FRIEND_OF` stores only single friendships. lance-csr composes them into paths of one, two and
three hops on the CSR, and the facts at the end of each path are bundled here. A query is built
from the same pieces (see `clue`), so a question can grow one remembered fact at a time.

The vectors are merged into `Person` as `context_hv`, a new Lance version; the canonical columns
are not rewritten.
"""

import zlib
from collections import defaultdict

import lancedb
import pyarrow as pa
import torch
import torchhd

from maker_night import DB_DIR, open_engine, record_in_manifest

# Design choices for this run, not tuned values.
HV_DIM = 10_000  # Conventional HDC size; leaves ample room for ~100 bundled facts per person.
SEED = 87
MAX_HOPS = 3  # multi_hop.py shows Maya and Pedro are three introductions apart.

PEOPLE_QUERY = """
MATCH (p:Person)
RETURN p.person_id AS person_id, p.name AS name, p.hair_colour AS hair, p.eye_colour AS eyes,
       p.interests AS interests
"""

# Trails of exactly k friendships (no friendship reused), excluding paths that return to p.
# A person can be reached by several paths, and at several distances; each path counts once.
PATHS_QUERY = """
MATCH (p:Person)-[:FRIEND_OF*{hops}]-(x:Person)
WHERE x.person_id <> p.person_id
RETURN p.person_id AS person_id, x.person_id AS reached
"""


def symbol(name: str) -> torch.Tensor:
    """A random ±1 vector for one symbol, seeded by its name so every script gets the same one."""
    generator = torch.Generator().manual_seed((SEED << 32) | zlib.crc32(name.encode()))
    return torchhd.random(1, HV_DIM, "MAP", generator=generator, dtype=torch.float32)[0]


def fact(key: str, value: str) -> torch.Tensor:
    """One fact, such as hair = Black: h_key ⊗ h_key=value."""
    return torchhd.bind(symbol(key), symbol(f"{key}={value}"))


def clue(key: str, value: str, hops: int = 0) -> torch.Tensor:
    """Apply the stored hop permutation to a remembered fact."""
    return torchhd.permute(fact(key, value), shifts=hops)


def bundle(vectors: list[torch.Tensor]) -> torch.Tensor:
    return torchhd.multiset(torch.stack(vectors))


def unit(vector: torch.Tensor) -> torch.Tensor:
    return vector / vector.norm()


def facts(person: dict) -> torch.Tensor:
    terms = [
        fact("name", person["name"]),
        fact("hair", person["hair"]),
        fact("eyes", person["eyes"]),
    ]
    terms += [fact("interest", interest) for interest in person["interests"]]
    return bundle(terms)


def encode_people(engine) -> dict[int, torch.Tensor]:
    """Return h_p for every person, from Cypher queries on the CSR."""
    people = {r["person_id"]: r for r in engine.execute(PEOPLE_QUERY).to_pylist()}
    person_facts = {pid: facts(p) for pid, p in people.items()}
    reached: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for hops in range(1, MAX_HOPS + 1):
        for r in engine.execute(PATHS_QUERY.format(hops=hops)).to_pylist():
            reached[r["person_id"]][hops].append(r["reached"])

    vectors = {}
    for pid in people:
        # Each hop is scaled to unit length so it weighs the same however many people it holds.
        blocks = [unit(person_facts[pid])]
        for hops in range(1, MAX_HOPS + 1):
            at_hop = reached[pid][hops]
            assert at_hop, (people[pid]["name"], hops)  # Holds for this connected graph.
            ring = unit(bundle([person_facts[x] for x in at_hop]))
            blocks.append(torchhd.permute(ring, shifts=hops))
        vectors[pid] = bundle(blocks)
    return vectors


def main() -> None:
    db = lancedb.connect(DB_DIR)
    person = db.open_table("Person")
    if "context_hv" in person.schema.names:  # Rerun: replace the derived column, keep the rows.
        person.drop_columns(["context_hv"])

    engine = open_engine()
    vectors = encode_people(engine)
    person_ids = sorted(vectors)
    stacked = torch.stack([vectors[pid] for pid in person_ids])

    # float16 is the storage format only. Check it keeps every person's ranking against a few
    # people's own vectors identical, so quantisation can't change a reported result.
    as_half = stacked.to(torch.float16).to(torch.float32)
    for probe in range(0, len(person_ids), 5):
        exact = torchhd.cosine_similarity(stacked[probe], stacked).argsort(descending=True)
        stored = torchhd.cosine_similarity(as_half[probe], as_half).argsort(descending=True)
        assert torch.equal(exact[:5], stored[:5]), person_ids[probe]

    context_hv = pa.FixedSizeListArray.from_arrays(
        pa.array(stacked.to(torch.float16).flatten().tolist(), pa.float16()), HV_DIM
    )
    person.to_lance().merge(
        pa.table({"person_id": pa.array(person_ids, pa.int64()), "context_hv": context_hv}),
        left_on="person_id",
    )
    entry = {
        "person_version": db.open_table("Person").version,
        "friend_of_version": engine.dataset_versions()["FRIEND_OF"],
        "dim": HV_DIM,
        "seed": SEED,
        "vsa": "MAP",
        "max_hops": MAX_HOPS,
        "hop_weighting": "each hop scaled to unit length",
        "hop_encoding": "permutation",
    }
    record_in_manifest("context_hv", entry)
    print(entry)


if __name__ == "__main__":
    main()
