"""CLI para escenarios hipotéticos V3.1, Atlas D07 siempre en solo lectura."""
import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from .config import load_config
from .atlas import read_atlas_sales
from .engine import run


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(65536),b''):h.update(chunk)
    return h.hexdigest()


def export_run(out_dir,config,atlas,atlas_path,output):
    out=Path(out_dir);out.mkdir(exist_ok=True,parents=True)
    rows=output['results']
    with (out/'empresas_resultados.csv').open('w',newline='',encoding='utf-8') as f:
        dw=csv.DictWriter(f,fieldnames=list(rows[0]))
        dw.writeheader()
        # Campos booleanos como 0/1, no cadenas True/False
        dw.writerows([{k:int(v) if isinstance(v,bool) else v for k,v in r.items()} for r in rows])
    timeline=[{'id':co.id,'category':co.category,'sector':co.sector,
         'duraciones_experimentales':co.durations,
         'eventos':[asdict(e) for e in co.events]} for co in output['companies']]
    (out/'ejemplos_eventos.json').write_text(json.dumps(timeline,indent=2,ensure_ascii=False),encoding='utf-8')
    manifest={
        'type':'EXPERIMENTO_NO_VALIDADO','simulator':'V3.1.1_sensibilidad_auditable',
        'origin_atlas':'D07_derivada_con_vista_alcance_solo_lectura','atlas_sha256':sha256(atlas_path),
        'config_sha256':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
        'case_count_reference':atlas.cases_total,'exact_sales_reference':atlas.sale_observations,
        'benchmark_eligible_sales':atlas.benchmark_observations,
        'excluded_partial_sale_ids':atlas.excluded_partial_ids,
        'atlas_start_type_counts':atlas.start_type_counts,
        'observed_operational_autonomy_pairs':atlas.operational_exact_pairs,
        'hypothetical_features':['poblacion','clasificación','efecto de complejidad sobre tareas',
            'etapas tecnológicas y operativas','perturbación operativa','pesos por fase jurídica',
            'plazos y umbral de evaluación','comportamiento sintético y multiplicadores sectoriales'],
        'sale_reference_limit':'23 ventas exactas en D07; un caso parcial etiquetado en vista SQLite derivada. Otras 22 inclusiones son provisionales; sesgo geográfico y orígenes heterogéneos',
        'compliance_warning':'autonomy_by_maximum es una métrica simulada, NO cumplimiento jurídico',
        'engine_limit':'DAG preplanificado; NO DES dinámica',
        'ratio_note':'La relación autonomía/venta es SIMULADA; no hay pares empíricos completos',
        'behavior_note':output['summary']['behavior_note'],
        'summary':output['summary'],
    }
    (out/'resumen_y_procedencia.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    return manifest


def main():
    ap=argparse.ArgumentParser(description='V3.1 exploratorio, sin predicción legal')
    ap.add_argument('--config',default='escenario_sintetico.json')
    ap.add_argument('--atlas',default='data/Atlas_63_D07_V311_Benchmark.sqlite')
    ap.add_argument('--out',default='output/ejemplo')
    args=ap.parse_args()
    config=load_config(args.config)
    atlas=read_atlas_sales(args.atlas)
    sales=atlas.sale_months if config['evidence_mode']=='atlas_legal_sale_benchmark' else ()
    output=run(config,sales)
    manifest=export_run(args.out,config,atlas,args.atlas,output)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
