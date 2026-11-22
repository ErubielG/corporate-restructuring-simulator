"""Ejecución V3.2; nunca escribe el Atlas."""
import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from .atlas import read_atlas_sales
from .dynamic_config import load_dynamic_config
from .dynamic_engine import run_dynamic
from .migrate_scope import logical_sha256


def _sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(131072),b''):
            h.update(chunk)
    return h.hexdigest()


def export(out_dir,c,atlas,atlas_path,result):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    rows=result['results']
    with (out/'empresas_resultados.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows([{k:int(v) if isinstance(v,bool) else v for k,v in r.items()} for r in rows])
    (out/'eventos_trazables.json').write_text(json.dumps([asdict(x) for x in result['companies']],ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={
        'version':'V3.2.0','type':'EXPERIMENTO_SINTETICO_NO_VALIDADO',
        'engine':'eventos_discretos_dinamicos_con_cancelacion_reprogramacion_y_requisitos_añadidos',
        'atlas_readonly':True,'atlas_sha256_physical':_sha(atlas_path),
        'atlas_sha256_logical':logical_sha256(atlas_path),
        'configuration_sha256':hashlib.sha256(json.dumps(c,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        'atlas_cases':atlas.cases_total,'exact_sale_observations':atlas.sale_observations,
        'sale_benchmark_provisional':atlas.benchmark_observations,
        'partial_remedies_excluded_provisionally':list(atlas.excluded_partial_ids),
        'autonomy_sale_exact_pairs':atlas.operational_exact_pairs,
        'legal_atlas_interventions_counterfactual':result['summary']['counterfactual_legal_changes_on_atlas'],
        'simulation_summary':result['summary'],
        'warnings':[
            'Todas las probabilidades y duraciones de incidencias dinámicas son hipotéticas.',
            'Las ventas Atlas solo informan la ruta jurídica, y su muestra no es representativa de México.',
            'Autonomía y plazo máximo son resultados simulados, no cumplimiento jurídico.',
            'Servicios comerciales no críticos se distinguen de los TSA críticos por una variable sintética.',
            'La proporción del 60% es un criterio de evaluación, nunca objetivo de calibración.',
            'Alcance de 22 ventas restantes no auditado exhaustivamente.',
        ]}
    (out/'resumen_y_procedencia.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest


def main():
    parser=argparse.ArgumentParser(description='Sistemas y Sociedad — motor dinámico V3.2 (no predictivo)')
    parser.add_argument('--config',default='escenario_v32_sintetico.json')
    parser.add_argument('--atlas',default='data/Atlas_63_D07_V311_Benchmark.sqlite')
    parser.add_argument('--out',default='output/v32_ejemplo')
    parser.add_argument('--trace-limit',type=int,default=5)
    args=parser.parse_args()
    config=load_dynamic_config(args.config)
    atlas=read_atlas_sales(args.atlas)
    sales=atlas.sale_months if config['evidence_mode']=='atlas_legal_sale_benchmark' else ()
    output=run_dynamic(config,sales,args.trace_limit)
    manifest=export(args.out,config,atlas,args.atlas,output)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
