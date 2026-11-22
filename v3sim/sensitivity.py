"""Barrido multifactorial V3.1, no calibración ni incertidumbre estadística externa.

Se varían PARAMETROS desconocidos, no solo la semilla. Las bandas resultantes
son de sensibilidad del escenario y no intervalos de confianza poblacionales.
"""
import argparse
import copy
import csv
import hashlib
import itertools
import json
from pathlib import Path
from statistics import mean, median
from .config import load_config
from .atlas import read_atlas_sales
from .engine import run

WEIGHT_PROFILES={
    'base':{'plan':0.18,'buyer_search':0.49,'authority_review':0.25,'legal_transfer':0.08},
    'preparacion_temprana':{'plan':0.35,'buyer_search':0.30,'authority_review':0.25,'legal_transfer':0.10},
    'busqueda_prolongada':{'plan':0.08,'buyer_search':0.60,'authority_review':0.22,'legal_transfer':0.10},
}


def sensitivity(base,observed_sales, strengths, scales, profiles, seeds):
    rows=[]
    for strength,scale,profile,seed in itertools.product(strengths,scales,profiles,seeds):
        c=copy.deepcopy(base)
        c['complexity_duration']['strength']=float(strength)
        c['operational_scale']=float(scale)
        c['atlas_sale_stage_weights']=WEIGHT_PROFILES[profile].copy()
        c['population']['seed']=int(seed)
        result=run(c,observed_sales,trace_limit=0)['summary']
        rows.append({'strength':float(strength),'operational_scale':float(scale),
                     'legal_stage_profile':profile,'seed':int(seed),
                     'mode':base['evidence_mode'],
                     'n':result['companies'],
                     'autonomy_by_initial':result['autonomy_by_initial'],
                     'autonomy_by_maximum':result['autonomy_by_maximum'],
                     'control_by_maximum':result['control_by_maximum'],
                     'verification_by_maximum':result['verification_by_maximum'],
                     'reference_60_met':int(result['target_achieved_in_this_hypothetical_run'])})
    return rows


def summarize(rows,target=0.6):
    groups={}
    for r in rows:
        key=(r['strength'],r['operational_scale'],r['legal_stage_profile'])
        groups.setdefault(key,[]).append(r['autonomy_by_maximum'])
    return [{'strength':k[0],'operational_scale':k[1],'legal_stage_profile':k[2],
             'replications':len(vals),'minimum':round(min(vals),6),
             'median':round(median(vals),6),'maximum':round(max(vals),6),
             'mean':round(mean(vals),6),
             'all_above_reference_60':int(min(vals)>=target),
             'all_below_reference_60':int(max(vals)<target),
             'straddles_reference_60':int(min(vals)<target<=max(vals))}
            for k,vals in sorted(groups.items())]


def to_csv(path,rows):
    if not rows:raise ValueError('Sin filas')
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys())
        writer.writeheader();writer.writerows(rows)


def main():
    ap=argparse.ArgumentParser(description='V3.1 barrido condicional; NO predicción')
    ap.add_argument('--config',default='escenario_atlas_ventas.json')
    ap.add_argument('--atlas',default='data/Atlas_63_D07_V311_Benchmark.sqlite')
    ap.add_argument('--out',default='output/sensibilidad')
    ap.add_argument('--strengths',nargs='+',type=float,default=[0.0,0.5,1.0])
    ap.add_argument('--scales',nargs='+',type=float,default=[0.75,1.0,1.25,1.5,2.0])
    ap.add_argument('--profiles',nargs='+',choices=list(WEIGHT_PROFILES),
                    default=list(WEIGHT_PROFILES))
    ap.add_argument('--seeds',nargs='+',type=int,default=[20261012,20261013,20261014,20261015])
    args=ap.parse_args()
    base=load_config(args.config)
    atlas=read_atlas_sales(args.atlas)
    sales=atlas.sale_months if base['evidence_mode']=='atlas_legal_sale_benchmark' else ()
    if base['evidence_mode']=='synthetic_only' and len(args.profiles)>1:
        raise ValueError('Los pesos de ventas no afectan el modo sintético. Selecciona --profiles base')
    result=sensitivity(base,sales,args.strengths,args.scales,args.profiles,args.seeds)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    to_csv(out/'corridas.csv',result)
    group=summarize(result,base['evaluation']['target_fraction'])
    to_csv(out/'resumen_sensibilidad.csv',group)
    manifest={
       'type':'BARRIDO_DE_SUPUESTOS_SIN_VALIDEZ_PREDICTIVA',
       'atlas_sha256':hashlib.sha256(Path(args.atlas).read_bytes()).hexdigest(),
       'eligible_sales':atlas.benchmark_observations,
       'operational_autonomy_pairs':atlas.operational_exact_pairs,
       'runs':len(result),'unique_assumption_cells':len(group),
       'straddling_cells':sum(g['straddles_reference_60'] for g in group),
       'all_above_cells':sum(g['all_above_reference_60'] for g in group),
       'all_below_cells':sum(g['all_below_reference_60'] for g in group),
       'uncertainty_note':'Los rangos reflejan exclusivamente supuestos y semillas elegidos; NO son intervalos de confianza poblacionales',
       'population_note':'Población sintética V3: 7 sectores iguales, puntuaciones U(0,100), cortes 35/65. No comparable directamente con V2 sin cohortes equivalentes',
       'P14_note':'La comparación usa autonomía simulada <= máximo de categoría; NO es una tasa legal',
    }
    (out/'manifiesto.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(manifest,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
