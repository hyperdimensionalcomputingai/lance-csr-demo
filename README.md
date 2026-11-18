# lance-csr-demo

Code for the blog post introducing lance-csr (coming soon).

The demo uses "Maker Night", a fictional community of 26 people (one per letter, A–Z) with
synthetic portraits, attributes and 44 friendships. Everything lives in two Lance tables,
`Person` and `FRIEND_OF`, and every question in the post is asked of those same tables.

## Layout

- `data/raw/`: hand-authored people and friendships (CSV).
- `data/portraits/`: synthetic 256×256 portraits, with [prompts](data/portraits/PROMPTS.md) and
  [source notes](data/portraits/SOURCE.md).
- `data/maker_night/`: the generated Lance tables (not committed).
- `src/`: the scripts below, plus `maker_night.py` for shared paths and the graph mapping.

## Run

Install the locked dependencies, then run the scripts in order from the repository root:

```bash
uv sync --locked
```

```bash
uv run python src/build_dataset.py      # Create the two canonical tables
uv run python src/encode_context.py     # Encode graph context, from paths of one to three hops
uv run python src/exact_match.py        # Robotics + hair + photographer friend, as exact conditions
uv run python src/multi_hop.py          # Maya to Pedro: two three-hop chains, with/without CSR
uv run python src/maya_finds_pedro.py    # Black hair, then robotics, then a photography friend
```

The search scripts and plan comparison assert the answers quoted in the post.
The three progressive shortlists are Xi/Pedro/Boris, Boris/Pedro/Xi, and Pedro/Boris/Leo. The mistaken
hair cue **replaces** black with dark brown (William/Elliott/Pedro); it is not an additional fourth cue. Gender stays
an exact filter in both query modes. Plan counts are pinned to lance-csr 0.12.0, not timings.
The encoder uses permutation to distinguish facts by hop count.
It summarizes facts by path length; it does not preserve exact topology or bind all
facts from a particular neighbour together. Multiple paths to a person contribute repeatedly.

## Compare hop encodings

Run `uv run python src/compare_hop_encodings.py` to compare permutation, role binding,
and plain bundling without changing the stored graph. See [the equations and results](HOP_ENCODING_COMPARISON.md).
