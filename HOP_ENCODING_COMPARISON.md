# Is permutation necessary?

Run `uv run python src/compare_hop_encodings.py`. Raw rankings, configuration and versions
are in `data/hop_encoding_comparison.json`. The script leaves the Lance tables unchanged.

## Same query, three encodings

Let $h_B = h_{hair} \otimes h_{Black}$, $h_R = h_{interest} \otimes h_{robotics}$,
and $h_P = h_{interest} \otimes h_{photography}$. The gender filter remains exact.

Permutation:

$$h_{query} = h_B \oplus h_R \oplus \rho(h_P)$$

Role binding, with an independently generated friend-role hypervector:

$$h_{query} = h_B \oplus h_R \oplus (h_{friend} \otimes h_P)$$

No marker:

$$h_{query} = h_B \oplus h_R \oplus h_P$$

Each method also encodes the stored graph context with its corresponding operation.
Changing only the query would not be a valid comparison. The three-hop binding variant
uses a different independent role for each hop. Repeated binding to the same bipolar
MAP role would cancel at hop two.

## Retrieval results

Same 26-person graph, 13 eligible men, 10,000 dimensions, seed 87, normalized blocks for
own facts and each of three hop lengths. Each method is rounded to float16, then scored
in float32, matching the blog's storage convention. The permutation reconstruction is
asserted identical to the existing stored hypervectors.

| Encoding | Black hair | Add robotics | Add photography friend |
| --- | --- | --- | --- |
| Permutation | Xi, Pedro, Boris | Boris, Pedro, Xi | Pedro, Boris, Leo |
| Role binding | Xi, Kenneth, Boris | Boris, Pedro, Xi | Pedro, Boris, Leo |
| No marker | Xi, Kenneth, Boris | Jonas, Elliott, William | Pedro, William, Leo |

All three return Pedro first for the full query. Recall@3 is 1 for each on this single
query, versus a random-ranking reference of 3/13 (23.1%). This result does not establish
that a marker is necessary to retrieve Pedro, or that one encoding is generally better.

## Does the encoding distinguish who has which attribute?

For this isolated check, let $h_R$ and $h_P$ represent interest=robotics and
interest=photography. Swap the person's interest and the friend's interest.

Without a marker, commutative bundling makes the two descriptions identical:

$$h_R \oplus h_P = h_P \oplus h_R$$

With role binding, the two descriptions are distinguishable:

$$h_R \oplus (h_{friend} \otimes h_P) \ne h_P \oplus (h_{friend} \otimes h_R)$$

With permutation, they are also distinguishable:

$$h_R \oplus \rho(h_P) \ne h_P \oplus \rho(h_R)$$

| Encoding | Identical after swapping roles? | Cosine similarity after swapping |
| --- | --- | --- |
| Permutation | No | -0.012 |
| Role binding | No | -0.013 |
| No marker | Yes | 1.000 |

Assertions verify the exact collision without marking and separation with both markers.
Permutation is optional. A marker such as permutation or role binding lets this bundled
representation distinguish own facts from friends' facts. Neither method here preserves
which individual friend supplied each fact. This is a fixed-seed mechanism check, not a
retrieval-quality benchmark across datasets or seeds.
