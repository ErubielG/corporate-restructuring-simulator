"""Create a demo-only SQLite interface with NO historical/business records.

The simulator's synthetic mode still expects a read-only SQLite connection
for schema and provenance. This fixture is synthetic and contains zero cases.
It must NEVER be represented as the research Atlas.
"""
import argparse
import sqlite3
from pathlib import Path

SQL = """
CREATE TABLE casos (
  id TEXT PRIMARY KEY,
  tipo_inicio_referencia TEXT
);
CREATE VIEW v311_ventas_benchmark AS
SELECT CAST(NULL AS TEXT) AS id_caso,
       CAST(NULL AS TEXT) AS familia_operacion,
       CAST(NULL AS REAL) AS meses,
       CAST(NULL AS TEXT) AS alcance_remedio,
       CAST(NULL AS INTEGER) AS apto_benchmark_provisional,
       CAST(NULL AS TEXT) AS tipo
WHERE 0;
CREATE VIEW v_i03_para_calibrar AS
SELECT CAST(NULL AS TEXT) AS fecha_autonomia_exacta,
       CAST(NULL AS TEXT) AS fecha_venta,
       CAST(NULL AS REAL) AS meses_postventa_operativa
WHERE 0;
"""

def create_demo_database(destination: str) -> Path:
    path = Path(destination)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as con:
        con.executescript(SQL)
        assert con.execute("SELECT count(*) FROM casos").fetchone()[0] == 0
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == 'ok'
    return path

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',default='data/synthetic_demo_fixture.sqlite')
    ns=ap.parse_args()
    print(create_demo_database(ns.out))
