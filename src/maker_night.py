"""Shared paths, graph mapping and engine setup for the Maker Night scripts."""

import json
from pathlib import Path

import lancedb
from lance import LanceDataset
from lance_csr import CypherEngine, GraphConfig

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PORTRAIT_DIR = ROOT / "data" / "portraits"
DB_DIR = ROOT / "data" / "maker_night"
MANIFEST_PATH = DB_DIR / "manifest.json"

# Table names double as the graph label and relationship type, so lance-csr resolves them.
GRAPH = (
    GraphConfig.builder()
    .node_table("Person", "person_id")
    .rel_table("FRIEND_OF", "Person", "Person", "src_id", "dst_id")
    .build()
)


def open_datasets() -> dict[str, LanceDataset]:
    """The canonical tables at their latest versions, keyed by graph label."""
    db = lancedb.connect(DB_DIR)
    return {name: db.open_table(name).to_lance() for name in ("Person", "FRIEND_OF")}


def open_engine() -> CypherEngine:
    return CypherEngine(GRAPH, open_datasets(), use_csr=True)


def record_in_manifest(key: str, entry: dict) -> None:
    """Add or replace one entry in the manifest written by `build_dataset.py`."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    manifest[key] = entry
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
