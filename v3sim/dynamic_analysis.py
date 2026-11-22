"""Sensibilidad V3.2 con umbrales condicionales por semilla y categoría."""
from __future__ import annotations
import argparse
import copy
import csv
import json
from pathlib import Path
from statistics import mean,median
from .atlas import read_atlas_sales
from .dynamic_config import load_dynamic_config,validate_dynamic_config
from .dynamic_engine import run_dynamic


def scenario(base,*,scale=None,tsa=None,sector=None,deadline=None,seed=None):
    c=copy.deepcopy(base)
    if scale is not None:c['operational_scale']=scale
    if tsa is not None:c['transitional_services_scale']=tsa
    if sector is not None:c['sector_multiplier_scale']=sector
    if deadline is not None:
        for category,pair in deadline.items():
            c['policy']['categories'][category]['initial_months'],c['policy']['categories'][category]['max_months']=pair
    if seed is not None:c['population']['seed']=int(seed)
    validate_dynamic_config(c)
    return c


def evaluate(c,sales):
    s=run_dynamic(c,sales,trace_limit=0)['summary']
    return {'rate':s['autonomy_by_maximum'],
            'median_simulated_ratio':s['median_autonomy_to_sale_ratio_simulated'],
            'by_category':s['by_category'],'incident_counts':s['incident_counts']}


def crossing(base,sales,seeds,lo=.4,hi=3.5,iterations=12):
    """Condicional: cruces separados por semilla; no intervalos de confianza."""
    if not seeds:raise ValueError('Se requiere al menos una semilla')
    target=base['evaluation']['target_fraction']
    rows=[]
    for seed in seeds:
        cache={}
        def ev(scale):
            key=round(scale,12)
            if key not in cache:
                cache[key]=evaluate(scenario(base,scale=scale,seed=seed),sales)
            return cache[key]
        left=ev(lo);right=ev(hi)
        monotone=all(ev(lo+(hi-lo)*i/10)['rate']>=ev(lo+(hi-lo)*(i+1)/10)['rate']-1e-9 for i in range(10))
        if not monotone or left['rate']<target or right['rate']>=target:
            rows.append({'seed':seed,'found':False,'reason':'Sin monotonía o sin cruce en intervalo','scale':None,'ratio':None})
            continue
        l,h=lo,hi
        for _ in range(iterations):
            middle=(l+h)/2
            if ev(middle)['rate']>=target:l=middle
            else:h=middle
        rows.append({'seed':seed,'found':True,'scale':round((l+h)/2,2),
                    'ratio':round(ev((l+h)/2)['median_simulated_ratio'],1),
                    'rate_low':ev(l)['rate'],'rate_high':ev(h)['rate']})
    good=[r for r in rows if r['found']]
    return {'metric':'autonomy_by_maximum','target_reference':target,
         'seeds':rows,'crude_range_simulated_ratio':[
            min(r['ratio'] for r in good),max(r['ratio'] for r in good)] if good else None,
         'warning':'Rango entre semillas y escenario fijo, NO IC estadístico, NO observación empírica'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='escenario_v32_atlas_ventas.json')
    p.add_argument('--atlas',default='data/Atlas_63_D07_V311_Benchmark.sqlite')
    p.add_argument('--out',default='output/v32_sensibilidad')
    p.add_argument('--scales',type=float,nargs='+',default=[0.8,1.0,1.4,1.8,2.2])
    p.add_argument('--seeds',type=int,nargs='+',default=[20261012,20261013,20261014,20261015])
    p.add_argument('--with-crossing',action='store_true')
    args=p.parse_args()
    base=load_dynamic_config(args.config)
    a=read_atlas_sales(args.atlas)
    sales=a.sale_months if base['evidence_mode']=='atlas_legal_sale_benchmark' else ()
    rows=[]
    for scale in args.scales:
        for seed in args.seeds:
            v=evaluate(scenario(base,scale=scale,seed=seed),sales)
            rows.append({'scale_hypothetical':scale,'seed':seed,'autonomy_by_maximum':v['rate'],
                  'median_ratio_simulated':v['median_simulated_ratio'],
                  **{f'category_{k}_rate':v['by_category'].get(k,{}).get('autonomy_by_maximum') for k in ('I','II','III')}})
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    with (out/'barrido_v32.csv').open('w',encoding='utf-8',newline='') as f:
        dw=csv.DictWriter(f,fieldnames=list(rows[0]));dw.writeheader();dw.writerows(rows)
    if args.with_crossing:
        result=crossing(base,sales,args.seeds)
        (out/'cruce_por_semilla.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'n_runs':len(rows),'n_scenarios':len(args.scales),
        'per_scale':[{'scale':x,'min_rate':min(r['autonomy_by_maximum'] for r in rows if r['scale_hypothetical']==x),
            'max_rate':max(r['autonomy_by_maximum'] for r in rows if r['scale_hypothetical']==x)} for x in args.scales],
        'warning':'Todas las duraciones operativas son hipotéticas. Las semillas no sustituyen incertidumbre epistemológica.'}
    (out/'resumen_barrido.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
