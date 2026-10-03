"""SQL analysis from normalized in-memory tables."""
import sqlite3


def analyze(case):
    with sqlite3.connect(":memory:") as db:
        db.executescript("""
        CREATE TABLE orders(id TEXT PRIMARY KEY, product TEXT, quantity INTEGER, priority INTEGER);
        CREATE TABLE bom(product TEXT, component TEXT, units INTEGER, PRIMARY KEY(product,component));
        CREATE TABLE offers(id TEXT PRIMARY KEY, supplier TEXT, component TEXT, approved INTEGER);
        CREATE TABLE stock(component TEXT PRIMARY KEY, units INTEGER);
        """)
        db.executemany("INSERT INTO orders VALUES(?,?,?,?)", [(o["id"], o["product"], o["quantity"],
                                                               o["priority"]) for o in case["orders"]])
        db.executemany("INSERT INTO bom VALUES(?,?,?)", [(b["product"], b["component"], b["units"])
                                                        for b in case["bom"]])
        db.executemany("INSERT INTO offers VALUES(?,?,?,?)", [(o["id"], o["supplier"], o["component"],
                                                              int(o["approved"])) for o in case["offers"]])
        db.executemany("INSERT INTO stock VALUES(?,?)", list(case["stock"].items()))
        rows = db.execute("""
          WITH demand AS (SELECT b.component, SUM(o.quantity*b.units) AS units
            FROM orders o JOIN bom b ON o.product=b.product GROUP BY b.component),
          sourcing AS (SELECT component, COUNT(DISTINCT supplier) AS suppliers
            FROM offers WHERE approved=1 GROUP BY component)
          SELECT s.component, COALESCE(d.units,0), s.units, COALESCE(q.suppliers,0)
            FROM stock s LEFT JOIN demand d ON s.component=d.component
            LEFT JOIN sourcing q ON s.component=q.component ORDER BY s.component
        """).fetchall()
        return [{"component": c, "demand": d, "opening_stock": s, "approved_suppliers": n,
                 "sole_source": n == 1} for c, d, s, n in rows]
