"""Puente de SOLO LECTURA: propuestas I-03 a candidatos de eventos V3.2.
No migra D07 a D08 y no produce calibración empírica.
"""
from __future__ import annotations
import csv,hashlib,json,sqlite3
from pathlib import Path
from collections import Counter
from contextlib import closing

SOURCES={
'I03_Hitos_Verificados_Propuesta_D08.csv':('id_atlas','tipo_hito','fecha','precision','hecho','url','localizador','limitacion'),
'I03_Lote_Casos_Extremos_Hitos_20261013.csv':('ID Atlas','Acontecimiento','Fecha / período','Precisión','Lo que demuestra','URL','Documento / sección','Límite documental / cautela'),
'I03_Tres_Investigaciones_Cierre_Hitos_20261013.csv':('Grupo/ID','Evento / afirmación','Fecha inicio','Precisión temporal','Qué prueba','URL original','Fuente / sección','Qué NO prueba'),
}
def event_type(label):
    s=label.casefold()
    for typ,patterns in (
       ('REMEDY_REPLACED',('sustituci','remedio alternativo')),
       ('OBLIGATION_MODIFIED',('exención','imposibilidad jurídica','remedio retirado')),
       ('DEADLINE_CHANGED',('prórroga','ampliación','extensión','modificación del plazo')),
       ('JUDICIAL_EVENT',('tribunal','sentencia','appeal','apelación','fallo','court','cat remite','litigi')),
       ('REGULATORY_DECISION',('compromisos','resolución','informe final','orden definitiva','decisión condicionada')),
       ('CONTRACT_TRANSITION',('contrato','handover','entrega de contratos','tres etapas','tres tramos')),
       ('POST_SALE_DEPENDENCY_OR_SUPPLY',('fabricación','suministro','servicio residual','apoyo transitorio','tsa')),
       ('SALE_OR_ASSET_CHANGE',('venta','adquisición','traspaso','desinversión','divestiture','compra')),
       ('FOLLOWUP',('cierre','último seguimiento','evaluación retrospectiva'))):
        if any(x in s for x in patterns):return typ
    return 'OTHER_DOCUMENTED_EVENT'

def load_proposals(transfer_dir,atlas_path):
    transfer_dir=Path(transfer_dir)
    with closing(sqlite3.connect(Path(atlas_path).resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        conn.execute('PRAGMA query_only=ON')
        atlas_ids={r[0] for r in conn.execute('SELECT id FROM casos')}
        n_cases=conn.execute('SELECT COUNT(*) FROM casos').fetchone()[0]
    seen=set(); rows=[]; repeats=[]; types=Counter()
    for filename,columns in SOURCES.items():
        file=transfer_dir/filename; sha=hashlib.sha256(file.read_bytes()).hexdigest()
        with file.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            missing=[x for x in columns if x not in reader.fieldnames]
            if missing:raise ValueError(f'{filename}: faltan columnas {missing}')
            for n,raw in enumerate(reader,start=2):
                ident,label,date,precision,meaning,url,locator,limits=(raw[x].strip() for x in columns)
                row={'id_atlas_or_candidate':ident,'atlas_member':ident in atlas_ids,
                     'external_candidate':ident not in atlas_ids,'label':label,
                     'event_kind_candidate':event_type(label),'date_text':date,'date_precision_text':precision,
                     'evidence_claim':meaning,'source_url':url,'source_locator':locator,'limits':limits,
                     'status':'I03_PROPOSAL_NOT_IN_D08','observed_full_autonomy_date':False,
                     'eligible_for_statistical_calibration':False,'provenance_file':filename,
                     'provenance_row':n,'source_file_sha256':sha}
                key=(ident,label,date,url)
                if key in seen:repeats.append(row)
                else:seen.add(key);rows.append(row);types[row['event_kind_candidate']]+=1
    return {'atlas_case_count':n_cases,'candidate_rows':len(rows),
            'exact_duplicate_rows':len(repeats),'atlas_member_rows':sum(r['atlas_member'] for r in rows),
            'external_candidate_rows':sum(r['external_candidate'] for r in rows),
            'category_counts':dict(sorted(types.items())),
            'warning':'Propuestas documentales, no son D08 consolidado ni nuevas probabilidades.',
            'rows':rows,'exact_duplicates':repeats}
def export_proposals(transfer_dir,atlas_path,out_dir):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    data=load_proposals(transfer_dir,atlas_path)
    (out/'i03_mapeo_candidato.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'i03_mapeo_candidato.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data['rows'][0]));w.writeheader();w.writerows(data['rows'])
    return {k:v for k,v in data.items() if k not in ('rows','exact_duplicates')}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--transfer',required=True);p.add_argument('--atlas',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(export_proposals(a.transfer,a.atlas,a.out),ensure_ascii=False,indent=2))
