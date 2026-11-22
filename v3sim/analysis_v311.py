"""V3.1.1: sensibilidad multifactorial y cruce numérico del 60%.

Solamente experimentos contrafactuales: no inferencia sobre empresas reales.
La relación autonomía/venta procede de las duraciones SIMULADAS, nunca de D07.
"""
import argparse,copy,csv,hashlib,itertools,json
from pathlib import Path
from statistics import mean,median
from .config import load_config,validate_config
from .atlas import read_atlas_sales
from .engine import run
from .sensitivity import WEIGHT_PROFILES

DEADLINE_PROFILES={
 'base':None,
 'uniform_30_36':{'I':(30,36),'II':(30,36),'III':(30,36)},
 'illustrative_18_30_48':{'I':(12,18),'II':(24,30),'III':(36,48)},
}

def scenario(base,*,scale=None,tsa=None,sector=None,max_effect=None,
             disruption=None,deadline=None,legal_profile=None,seed=None):
    c=copy.deepcopy(base)
    if scale is not None:c['operational_scale']=float(scale)
    if tsa is not None:c['transitional_services_scale']=float(tsa)
    if sector is not None:c['sector_multiplier_scale']=float(sector)
    if max_effect is not None:c['complexity_duration']['max_effect']=float(max_effect)
    if disruption is not None:c['operational_disruption']['probability']=float(disruption)
    if deadline is not None and deadline not in DEADLINE_PROFILES:raise ValueError(f'Perfil de plazos desconocido: {deadline}')
    if legal_profile is not None and legal_profile not in WEIGHT_PROFILES:raise ValueError('Perfil jurídico inválido')
    if deadline is not None and DEADLINE_PROFILES[deadline]:
        for cat,(initial,maximum) in DEADLINE_PROFILES[deadline].items():
            c['policy']['categories'][cat]={'initial_months':initial,'max_months':maximum}
    if legal_profile is not None:c['atlas_sale_stage_weights']=WEIGHT_PROFILES[legal_profile].copy()
    if seed is not None:c['population']['seed']=int(seed)
    validate_config(c)
    return c

def measure(c,sales):
    s=run(c,sales,trace_limit=0)['summary']
    out={'autonomy_by_maximum':s['autonomy_by_maximum'],
         'autonomy_by_initial':s['autonomy_by_initial'],
         'median_autonomy_to_sale_ratio_simulated':s['median_autonomy_to_sale_ratio_simulated'],
         'control_by_maximum':s['control_by_maximum'],
         'n':s['companies']}
    for cat in ('I','II','III'):
        v=s['by_category'].get(cat,{})
        out[f'category_{cat}_n']=v.get('n',0)
        out[f'category_{cat}_by_maximum']=v.get('autonomy_by_maximum',None)
        out[f'category_{cat}_median_months']=v.get('autonomy_median_months',None)
        out[f'category_{cat}_median_ratio_simulated']=v.get('median_autonomy_to_sale_ratio_simulated',None)
    return out

def grid(base,sales,scales,tsas,sectors,max_effects,disruptions,deadlines,legal_profiles,seeds):
    rows=[]
    for scale,tsa,sector,mxe,dis,deadline,legal,seed in itertools.product(scales,tsas,sectors,max_effects,disruptions,deadlines,legal_profiles,seeds):
        c=scenario(base,scale=scale,tsa=tsa,sector=sector,max_effect=mxe,
                   disruption=dis,deadline=deadline,legal_profile=legal,seed=seed)
        rows.append({'operational_scale_hypothetical':scale,'tsa_scale_hypothetical':tsa,
                     'sector_scale_hypothetical':sector,'complexity_max_effect_hypothetical':mxe,
                     'disruption_probability_hypothetical':dis,'deadline_profile_hypothetical':deadline,
                     'legal_profile_hypothetical':legal,'seed':seed,
                     **measure(c,sales)})
    return rows

def aggregate(rows,target):
    keys=('operational_scale_hypothetical','tsa_scale_hypothetical','sector_scale_hypothetical',
          'complexity_max_effect_hypothetical','disruption_probability_hypothetical',
          'deadline_profile_hypothetical','legal_profile_hypothetical')
    groups={}
    for r in rows:
        k=tuple(r[f] for f in keys);groups.setdefault(k,[]).append(r)
    out=[]
    for k,rr in sorted(groups.items(),key=lambda x:str(x[0])):
        values=[r['autonomy_by_maximum'] for r in rr]
        ratios=[r['median_autonomy_to_sale_ratio_simulated'] for r in rr]
        res=dict(zip(keys,k));res.update({'replications':len(rr),
                'by_maximum_median':round(median(values),6),'by_maximum_min':min(values),
                'by_maximum_max':max(values),'median_ratio_simulated':round(median(ratios),5),
                'fraction_of_seeds_meeting_target':round(mean(v>=target for v in values),5)})
        for cat in ('I','II','III'):
            values_cat=[r[f'category_{cat}_by_maximum'] for r in rr if r[f'category_{cat}_n']>0]
            res[f'category_{cat}_by_maximum_median']=round(median(values_cat),6) if values_cat else None
            res[f'category_{cat}_n_median']=median(r[f'category_{cat}_n'] for r in rr)
        out.append(res)
    return out

def crossing(base,sales,seeds,lo=0.5,hi=3.0,tolerance=0.002,max_iterations=22):
    """Cruce MONÓTONO CONDICIONAL por bisección, sin fijar el resultado.

    Mantiene cohortes y semillas fijas (números aleatorios comunes). Retorna
    ausencia de cruce si el intervalo no contiene el objetivo y avisa si
    la relación no es aproximadamente monótona en una rejilla de control.
    """
    target=base['evaluation']['target_fraction']
    cache={}
    def evaluate(scale):
        key=round(scale,12)
        if key not in cache:
            values=[measure(scenario(base,scale=scale,seed=seed),sales) for seed in seeds]
            cache[key]={'scale':scale,'rate_mean':mean(v['autonomy_by_maximum'] for v in values),
                'ratio_median_simulated':median(v['median_autonomy_to_sale_ratio_simulated'] for v in values),
                'rate_by_seed':[v['autonomy_by_maximum'] for v in values]}
        return cache[key]
    control=[evaluate(lo+(hi-lo)*i/10) for i in range(11)]
    monotone=all(control[i]['rate_mean']>=control[i+1]['rate_mean']-1e-9 for i in range(10))
    a=evaluate(lo);b=evaluate(hi)
    result={'target_reference':target,'lo':lo,'hi':hi,'monotone_at_11_checkpoints':monotone,
       'initial_lo':a,'initial_hi':b,'crn_fixed_seeds':list(seeds),
       'ratio_note':'Ratio basado en ambas fechas SIMULADAS; no es una observación del Atlas',
       'legal_note':'Cruce del indicador autonomía simulada por máximo, NO cumplimiento legal',
       'crossing_found':False}
    if a['rate_mean']<target or b['rate_mean']>=target:
        result['reason']='El objetivo no está encajonado en los límites escogidos';return result
    if not monotone:
        result['reason']='No se asume cruce único: falla control de monotonía';return result
    l=lo;h=hi
    for _ in range(max_iterations):
        if h-l<=tolerance:break
        middle=(h+l)/2;v=evaluate(middle)
        if v['rate_mean']>=target:l=middle
        else:h=middle
    result.update({'crossing_found':True,'scale_interval':[l,h],
                   'rate_at_lower':evaluate(l),'rate_at_upper':evaluate(h),
                   'iterations':len(cache),
                   'ratio_interval_simulated':[evaluate(l)['ratio_median_simulated'],evaluate(h)['ratio_median_simulated']]})
    return result

def write_csv(path,rows):
    if not rows:raise ValueError('Sin datos')
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser(description='V3.1.1 — Sensibilidad NO PREDICTIVA')
    ap.add_argument('--config',default='escenario_atlas_ventas.json')
    ap.add_argument('--atlas',default='data/Atlas_63_D07_V311_Benchmark.sqlite')
    ap.add_argument('--out',default='output/analisis_v311')
    ap.add_argument('--scales',nargs='+',type=float,default=[1.0,1.7])
    ap.add_argument('--tsas',nargs='+',type=float,default=[0.6,1.0])
    ap.add_argument('--sectors',nargs='+',type=float,default=[0.8,1.2])
    ap.add_argument('--max-effects',nargs='+',type=float,default=[0.3,0.6])
    ap.add_argument('--disruptions',nargs='+',type=float,default=[0.0,0.3])
    ap.add_argument('--deadline-profiles',nargs='+',choices=list(DEADLINE_PROFILES),default=['base','uniform_30_36'])
    ap.add_argument('--legal-profiles',nargs='+',choices=list(WEIGHT_PROFILES),default=['base'])
    ap.add_argument('--seeds',nargs='+',type=int,default=[20261012,20261013])
    ap.add_argument('--crossing-lo',type=float,default=0.5)
    ap.add_argument('--crossing-hi',type=float,default=3.0)
    args=ap.parse_args()
    c=load_config(args.config);atlas=read_atlas_sales(args.atlas)
    sales=atlas.sale_months if c['evidence_mode']=='atlas_legal_sale_benchmark' else ()
    if c['evidence_mode']=='synthetic_only' and args.legal_profiles!=['base']:
        raise ValueError('El perfil de fases Atlas no afecta el modo sintético')
    rows=grid(c,sales,args.scales,args.tsas,args.sectors,args.max_effects,args.disruptions,args.deadline_profiles,args.legal_profiles,args.seeds)
    summary=aggregate(rows,c['evaluation']['target_fraction'])
    cross=crossing(c,sales,args.seeds,args.crossing_lo,args.crossing_hi)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'corridas_multifactoriales.csv',rows)
    write_csv(out/'escenarios_resumidos.csv',summary)
    (out/'cruce_60_condicional.json').write_text(json.dumps(cross,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'version':'V3.1.1 experimental','n_runs':len(rows),'n_assumption_cells':len(summary),
       'atlas_sha256':hashlib.sha256(Path(args.atlas).read_bytes()).hexdigest(),
       'atlas_sales_original':atlas.sale_observations,'sale_benchmark_provisional':atlas.benchmark_observations,
       'autonomy_sale_observed_pairs':atlas.operational_exact_pairs,
       'warning':'Los plazos, ratios y demás resultados son SIMULADOS y NO pruebas de cumplimiento legal ni de la viabilidad de P14',
       'scope_warning':'La clasificación de remedios parciales no está auditada exhaustivamente; los no determinados continúan como provisionalmente elegibles',
       'behavior_note': 'En modo Atlas se omite conducta jurídica adicional para no contarla dos veces; se advierte explícitamente. El parámetro operational_disruption es una perturbación EXÓGENA y no mide intención estratégica.',
       'classification_note':'Categorías, scores, distribución de sectores y plazos experimentales no calibrados',
       'crossing_found':cross['crossing_found']}
    (out/'manifiesto.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
