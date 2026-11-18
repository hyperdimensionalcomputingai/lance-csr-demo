"""Build the Maker Night dataset: 26 fictional people, their portraits and friendships, in Lance.

The CSVs in `data/raw/` and the PNGs in `data/portraits/` are the hand-authored source. This
script validates them and writes two LanceDB tables, `Person` and `FRIEND_OF`, to
`data/maker_night/`. The table names are the graph label and relationship type, so lance-csr
finds them as `<dir>/<label>.lance`.

Each portrait's PNG bytes are stored in the `Person` row itself: the image is part of the
canonical record, next to the person's attributes. Hypervectors are derived data, added by
`encode_context.py` as a new column in a new table version.
"""

import io
import json

import lancedb
import polars as pl
import pyarrow as pa
from PIL import Image

from maker_night import DB_DIR, MANIFEST_PATH, PORTRAIT_DIR, RAW_DIR

PORTRAIT_SIZE = (256, 256)

PERSON_SCHEMA = pa.schema(
    [
        pa.field("person_id", pa.int64(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("gender", pa.string(), nullable=False),
        pa.field("age", pa.int32(), nullable=False),
        pa.field("hair_colour", pa.string(), nullable=False),
        pa.field("eye_colour", pa.string(), nullable=False),
        pa.field("interests", pa.list_(pa.string()), nullable=False),
        pa.field("portrait", pa.binary(), nullable=False),  # PNG bytes, unchanged from disk.
    ]
)

# Each friendship is stored once, with src_id < dst_id. FRIEND_OF is symmetric, so queries
# match it undirected (`-[:FRIEND_OF]-`); lance-csr's CSR indexes both directions.
FRIEND_OF_SCHEMA = pa.schema(
    [
        pa.field("friendship_id", pa.int64(), nullable=False),
        pa.field("src_id", pa.int64(), nullable=False),
        pa.field("dst_id", pa.int64(), nullable=False),
    ]
)


def load_portrait(person_id: int) -> bytes:
    data = (PORTRAIT_DIR / f"{person_id:02d}.png").read_bytes()
    image = Image.open(io.BytesIO(data))
    assert image.format == "PNG" and image.size == PORTRAIT_SIZE, (person_id, image.size)
    return data


def load_people() -> pa.Table:
    people = pl.read_csv(RAW_DIR / "people.csv").with_columns(pl.col("interests").str.split(";"))
    # One person per letter, with person_id equal to the letter's position (A=1 ... Z=26),
    # so diagrams can label nodes by initial and IDs stay readable in raw edge lists.
    initials = people["name"].str.slice(0, 1).to_list()
    assert initials == [chr(ord("A") + i) for i in range(26)], initials
    assert people["person_id"].to_list() == list(range(1, 27))
    people = people.with_columns(
        portrait=pl.Series([load_portrait(pid) for pid in people["person_id"]], dtype=pl.Binary)
    )
    return people.to_arrow().select(PERSON_SCHEMA.names).cast(PERSON_SCHEMA)


def load_friendships(person_ids: set[int]) -> pa.Table:
    friendships = pl.read_csv(RAW_DIR / "friendships.csv")
    assert friendships["friendship_id"].is_unique().all()
    assert (friendships["src_id"] < friendships["dst_id"]).all(), (
        "store each pair once, low id first"
    )
    assert friendships.select("src_id", "dst_id").is_unique().all(), "duplicate friendship"
    assert set(friendships["src_id"]) | set(friendships["dst_id"]) <= person_ids
    return friendships.to_arrow().cast(FRIEND_OF_SCHEMA)


def main() -> None:
    person = load_people()
    friend_of = load_friendships(set(person["person_id"].to_pylist()))

    db = lancedb.connect(DB_DIR)
    person_table = db.create_table("Person", person, schema=PERSON_SCHEMA, mode="overwrite")
    friend_table = db.create_table(
        "FRIEND_OF", friend_of, schema=FRIEND_OF_SCHEMA, mode="overwrite"
    )

    # Record what was written so derived data (hypervectors) can name its source.
    # `encode_context.py` adds its own entry.
    manifest = {
        "Person": {"rows": person_table.count_rows(), "version": person_table.version},
        "FRIEND_OF": {"rows": friend_table.count_rows(), "version": friend_table.version},
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
