"""Genera copia derivada de D07 con etiquetas de alcance. No modifica D07.

La inclusión de observaciones SIN CLASIFICACIÓN es PROVISIONAL y no demuestra
que todas representen remedios íntegramente completados.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,sqlite3
from contextlib import closing

def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def logical_sha256(path):
    """Huella del volcado lógico, independiente del encabezado SQLite físico.

    La huella no sustituye a una auditoría semántica del esquema ni de los datos.
    """
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as con:
        h=hashlib.sha256()
        for line in con.iterdump():
            h.update(line.encode('utf-8'));h.update(b'\n')
        return h.hexdigest()

def migrate(source,output):
    source=Path(source).resolve();output=Path(output).resolve()
    if source==output:raise ValueError('Prohibido sobrescribir la fuente')
    output.parent.mkdir(parents=True,exist_ok=True)
    original_hash=sha256(source)
    shutil.copyfile(source,output)
    conn=sqlite3.connect(output)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS v311_alcance_remedio (
            id_caso TEXT PRIMARY KEY REFERENCES casos(id),
            estado TEXT NOT NULL CHECK(estado IN ('PARCIAL_DOCUMENTADO','COMPLETO_DOCUMENTADO','NO_DETERMINADO')),
            documento_origen TEXT NOT NULL,
            nota TEXT NOT NULL
        );
        INSERT INTO v311_alcance_remedio(id_caso,estado,documento_origen,nota)
        VALUES('P16-019','PARCIAL_DOCUMENTADO',
           'Auditoría de imperfecciones de V3 (2026-10-12), punto 10',
           'Circle Bath vendido; obligación de Birmingham retirada en 2024. Excluido solo del benchmark de venta completa; requiere corroboración documental separada.');
        CREATE VIEW v311_ventas_benchmark AS
        SELECT v.*,
               COALESCE(a.estado,'NO_DETERMINADO') AS alcance_remedio,
               CASE WHEN a.estado='PARCIAL_DOCUMENTADO' THEN 0 ELSE 1 END AS apto_benchmark_provisional
        FROM v_i02_duraciones_venta v LEFT JOIN v311_alcance_remedio a ON a.id_caso=v.id_caso;
        ''')
        if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integridad SQLite fallida')
        if conn.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('FK inválidas')
        n=conn.execute('SELECT COUNT(*) FROM casos').fetchone()[0]
        if n!=63:raise ValueError('La copia no tiene 63 expedientes')
        source_count=sqlite3.connect(f'{source.as_uri()}?mode=ro',uri=True).execute('SELECT COUNT(*) FROM casos').fetchone()[0]
        if source_count!=n:raise ValueError('Número de casos cambió')
        conn.commit()
    except:
        conn.close();output.unlink(missing_ok=True);raise
    finally:
        try:conn.close()
        except:pass
    if sha256(source)!=original_hash:raise ValueError('El archivo fuente fue alterado')
    result={'original_sha256':original_hash,'derived_sha256':sha256(output),'derived_logical_sha256':logical_sha256(output),'cases':63,
            'partial_excluded':['P16-019'],'unknown_scope_still_provisionally_included':True,
            'warning':'NO es una revisión exhaustiva de remedios parciales; requiere auditoría documental del Atlas.'}
    output.with_suffix('.provenance.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default='data/Atlas_63_D07_I03.sqlite');p.add_argument('--out',default='data/Atlas_63_D07_V311_Benchmark.sqlite');a=p.parse_args()
    print(json.dumps(migrate(a.source,a.out),indent=2,ensure_ascii=False))
if __name__=='__main__':main()
