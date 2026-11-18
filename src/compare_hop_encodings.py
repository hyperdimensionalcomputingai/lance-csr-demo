"""Compare permutation, hop-role binding, and no hop marker on the same graph.

Run: uv run python src/compare_hop_encodings.py
Rebuilds representations in memory, leaving the existing Lance tables untouched.
All methods use the existing seed, facts, path multiplicities, normalization and male filter.
Binding uses independent roles per hop: repeated MAP binding to one role would cancel at hop 2.
"""

import json
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

import torch
import torchhd

from encode_context import (
    HV_DIM,
    MAX_HOPS,
    PATHS_QUERY,
    PEOPLE_QUERY,
    SEED,
    bundle,
    fact,
    facts,
    symbol,
    unit,
)
from maker_night import open_engine
from maya_finds_pedro import CANDIDATES_QUERY, CUES

METHODS = ("permutation", "role_binding", "no_marker")
ROLES = {hop: symbol(f"hop_role={hop}") for hop in range(1, MAX_HOPS + 1)}
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "hop_encoding_comparison.json"


def mark(vector, hop, method):
    """Apply the identical hop marker to stored facts and query cues."""
    if hop == 0 or method == "no_marker":
        return vector
    if method == "permutation":
        return torchhd.permute(vector, shifts=hop)
    return torchhd.bind(ROLES[hop], vector)


def swap_check():
    """Can we distinguish own robotics/friend photography from the reversed assignment?"""
    robotics = fact("interest", "robotics")
    photography = fact("interest", "photography")
    rows = []
    for method in METHODS:
        desired = bundle([robotics, mark(photography, 1, method)])
        reversed_roles = bundle([photography, mark(robotics, 1, method)])
        same = torch.equal(desired, reversed_roles)
        cross_similarity = float(torchhd.cosine_similarity(desired, reversed_roles))
        assert same == (method == "no_marker"), method
        if method != "no_marker":
            assert abs(cross_similarity) < 0.05, (method, cross_similarity)
        rows.append(
            {"method": method, "identical_after_swap": same, "cosine_after_swap": cross_similarity}
        )
    return rows


def main():
    engine = open_engine()
    people = {r["person_id"]: r for r in engine.execute(PEOPLE_QUERY).to_pylist()}
    own = {pid: facts(p) for pid, p in people.items()}
    reached = defaultdict(lambda: defaultdict(list))
    for hop in range(1, MAX_HOPS + 1):
        for row in engine.execute(PATHS_QUERY.format(hops=hop)).to_pylist():
            reached[row["person_id"]][hop].append(row["reached"])
    candidates = sorted(engine.execute(CANDIDATES_QUERY).to_pylist(), key=lambda p: p["id"])
    # Use the same float16 rounding as the blog's stored column for every method.
    stored = torch.tensor([p["p.context_hv"] for p in candidates], dtype=torch.float32)
    blocks = {}
    for p in candidates:
        pid = p["id"]
        blocks[pid] = [unit(own[pid])] + [
            unit(bundle([own[x] for x in reached[pid][hop]])) for hop in range(1, MAX_HOPS + 1)
        ]
    results = []
    for method in METHODS:
        encoded = (
            torch.stack(
                [
                    bundle([mark(block, hop, method) for hop, block in enumerate(blocks[p["id"]])])
                    for p in candidates
                ]
            )
            .half()
            .float()
        )
        if method == "permutation":
            torch.testing.assert_close(encoded, stored, rtol=0, atol=0)
        for count in range(1, len(CUES) + 1):
            query = bundle(
                [mark(fact(key, value), hop, method) for _, key, value, hop in CUES[:count]]
            )
            scores = torchhd.cosine_similarity(query, encoded).flatten()
            order = scores.argsort(descending=True).tolist()
            ranking = [{"name": candidates[i]["name"], "score": float(scores[i])} for i in order]
            rank = next(i + 1 for i, row in enumerate(ranking) if row["name"] == "Pedro")
            results.append(
                {
                    "method": method,
                    "cue_count": count,
                    "ranking": ranking,
                    "pedro_rank": rank,
                    "recall_at_3": int(rank <= 3),
                }
            )
    output = {
        "dim": HV_DIM,
        "seed": SEED,
        "max_hops": MAX_HOPS,
        "candidate_count": len(candidates),
        "random_recall_at_3": 3 / len(candidates),
        "versions": {p: version(p) for p in ("torch", "torch-hd", "lance-csr")},
        "swap_check": swap_check(),
        "retrieval": results,
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print("| Encoding | Cues | Top three | Pedro rank |")
    print("| --- | --- | --- | --- |")
    for row in results:
        top = ", ".join(f"{r['name']} ({r['score']:.3f})" for r in row["ranking"][:3])
        print(f"| {row['method']} | {row['cue_count']} | {top} | {row['pedro_rank']} |")
    print("\nSwapping own/friend facts:", json.dumps(output["swap_check"], indent=2))
    print(f"\nCandidate pool: {len(candidates)}. Random Recall@3: {3 / len(candidates):.3f}.")
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
