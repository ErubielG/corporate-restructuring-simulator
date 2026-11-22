"""D07 inmutable: referencia de ventas, nunca de autonomía operativa.

Una observación documentada como venta parcial (ID histórico P16-019) se excluye
solo del benchmark principal; sigue presente en la base y en el conteo histórico.
"""
from pathlib import Path
import sqlite3
from dataclasses import dataclass
from contextlib import closing


@dataclass(frozen=True)
class AtlasSales:
    cases_total:int
    sale_observations:int
    benchmark_observations:int
    excluded_partial_ids:tuple[str,...]
    distinct_families:int
    sale_months:tuple[float,...]
    operational_exact_pairs:int
    start_type_counts:dict[str,int]
    uri:str


def connect_readonly(path:str|Path)->sqlite3.Connection:
    p=Path(path).expanduser().resolve(strict=True)
    conn=sqlite3.connect(f'{p.as_uri()}?mode=ro',uri=True)
    conn.execute('PRAGMA query_only=ON')
    return conn


def read_atlas_sales(path:str|Path)->AtlasSales:
    with closing(connect_readonly(path)) as con:
        integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity!='ok':raise ValueError(f'SQLite corrupta: {integrity}')
        cases=con.execute('SELECT COUNT(*) FROM casos').fetchone()[0]
        if con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name='v311_ventas_benchmark'").fetchone()[0]!=1:
            raise ValueError('Falta vista de alcance v311_ventas_benchmark. Ejecuta python -m v3sim.migrate_scope --source ... --out ...')
        rows=con.execute("""SELECT id_caso,familia_operacion,meses,alcance_remedio,apto_benchmark_provisional
                            FROM v311_ventas_benchmark WHERE tipo='EXACTA' AND meses IS NOT NULL AND meses>0""").fetchall()
        if len({r[1] for r in rows})!=len(rows):raise ValueError('Duplicados por familia')
        excluded=tuple(r[0] for r in rows if r[4]!=1)
        used=[r for r in rows if r[4]==1]
        pairs=con.execute('''SELECT COUNT(*) FROM v_i03_para_calibrar
              WHERE fecha_autonomia_exacta IS NOT NULL AND fecha_venta IS NOT NULL
              AND meses_postventa_operativa IS NOT NULL''').fetchone()[0]
        starts=dict(con.execute('''SELECT COALESCE(tipo_inicio_referencia,'NO_DETERMINADO'),COUNT(*)
                                   FROM casos GROUP BY COALESCE(tipo_inicio_referencia,'NO_DETERMINADO')''').fetchall())
    return AtlasSales(cases_total=cases,sale_observations=len(rows),
        benchmark_observations=len(used),excluded_partial_ids=excluded,
        distinct_families=len(rows),sale_months=tuple(float(r[2]) for r in used),
        operational_exact_pairs=pairs,start_type_counts=starts,uri=str(Path(path).resolve()))
