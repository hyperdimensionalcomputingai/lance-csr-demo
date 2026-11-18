"""The post's exact-match search: a man with black hair who's into robotics.

The same three conditions in SQL and in Cypher return the same people, and both become the
same physical plan: one Lance scan with the conditions pushed down. With the hair misremembered
as dark brown, Pedro is not in the result at all. Adding the photographer-friend condition
uses the same relational cues as `maya_finds_pedro.py`. Run `build_dataset.py` first.
"""

import re

from lance_csr import SqlEngine

from maker_night import open_engine

SQL = """
SELECT name
FROM person
WHERE gender = 'male'
  AND hair_colour = '{hair}'
  AND array_has(interests, 'robotics')
ORDER BY name
"""

CYPHER = """
MATCH (p:Person)
WHERE p.gender = 'male' AND p.hair_colour = '{hair}'
  AND 'robotics' IN p.interests
RETURN p.name AS name
ORDER BY name
"""


CONTEXT_QUERY = """
MATCH (p:Person)-[:FRIEND_OF]-(f:Person)
WHERE p.gender = 'male' AND p.hair_colour = $hair
  AND 'robotics' IN p.interests
  AND 'photography' IN f.interests
RETURN DISTINCT p.name AS name
ORDER BY name
"""


def physical_operators(explain: str) -> list[str]:
    """Operator names of the physical plan, top to bottom, from either engine's `explain()`."""
    physical = re.split(r"physical_plan|== Physical Plan ==", explain)[-1]
    return re.findall(r"^[\s|]*(\w+Exec|LanceRead)\b", physical, flags=re.MULTILINE)


def main() -> None:
    engine = open_engine()
    sql = SqlEngine.from_engine(engine)
    for hair, expected in (("Black", ["Boris", "Pedro"]), ("Dark brown", ["Elliott", "William"])):
        from_sql = [r["name"] for r in sql.execute(SQL.format(hair=hair)).to_pylist()]
        from_cypher = [r["name"] for r in engine.execute(CYPHER.format(hair=hair)).to_pylist()]
        assert from_sql == from_cypher == expected, (hair, from_sql, from_cypher)
        print(f"A man with {hair.lower()} hair, into robotics: {', '.join(from_sql)}")

    print("\nWith the photographer-friend condition:")
    for hair, expected in (("Black", ["Pedro"]), ("Dark brown", ["William"])):
        rows = engine.execute(CONTEXT_QUERY, {"hair": hair}).to_pylist()
        names = [row["name"] for row in rows]
        assert names == expected, (hair, names)
        print(f"  Robotics + {hair.lower()} hair + photographer friend: {names}")

    sql_plan = physical_operators(sql.explain(SQL.format(hair="Black")))
    cypher_plan = physical_operators(engine.explain(CYPHER.format(hair="Black")))
    assert sql_plan == cypher_plan and sql_plan.count("LanceRead") >= 1, (sql_plan, cypher_plan)
    print(f"\nSQL and Cypher share one physical plan: {' <- '.join(sql_plan)}")


if __name__ == "__main__":
    main()
