"""V3.1: planificador DAG experimental con duraciones condicionadas por complejidad.

ATENCIÓN: las tareas siguen siendo preplanificadas. NO es un motor DES dinámico.
La señal de 'complejidad' es sintética y su efecto no está calibrado.
"""
import heapq
import itertools
import random
from statistics import mean, median
from typing import Any
from .model import Company, Event
from .config import validate_config, COMPLEXITY_STAGES, LEGAL_STAGES

DEPENDENCIES = {
 'plan': (),
 'buyer_search': ('plan',),
 'authority_review': ('buyer_search',),
 'legal_transfer': ('authority_review',),
 'tech_preparation': ('plan',),
 'staff_preparation': ('plan',),
 'infrastructure_preparation': ('plan',),
 'operational_cutover': ('legal_transfer','tech_preparation','staff_preparation','infrastructure_preparation'),
 'transitional_services': ('operational_cutover',),
 'verification': ('transitional_services',),
}
TECH_STAGES = frozenset(('tech_preparation','staff_preparation','infrastructure_preparation',
                           'operational_cutover','transitional_services'))


def classify(score:dict,flags:dict,policy:dict)->str:
    value=sum(score[k]*policy['score_weights'][k] for k in policy['score_weights'])
    a,b=policy['score_thresholds']
    cat='I' if value<a else ('II' if value<b else 'III')
    order={'I':0,'II':1,'III':2}
    if flags['service_critical'] or flags['labor_critical']:
        if order[cat]<order[policy['critical_min_category']]:cat=policy['critical_min_category']
    return cat


def stage_complexity_multiplier(stage:str,score:dict,c:dict)->float:
    """Efecto hipotético monotónico de los factores de complejidad, neutral con strength=0."""
    if stage not in COMPLEXITY_STAGES:
        return 1.0
    cfg=c['complexity_duration']
    component=sum(score[k]*weight for k,weight in cfg['stage_drivers'][stage].items())
    # score 0 -> factor (1 - strength*max_effect); score 100 -> (1 + strength*max_effect).
    return 1.0 + cfg['strength']*cfg['max_effect']*(component-50.0)/50.0


def sample_company(idx:int,rng:random.Random,c:dict,observed_sales:tuple[float,...])->Company:
    sw=c['population']['sector_weights']
    sector=rng.choices(list(sw),weights=list(sw.values()),k=1)[0]
    score={k:round(rng.uniform(0,100),2) for k in c['policy']['score_weights']}
    flags={
        'service_critical':score['service_continuity']>=c['policy']['critical_service_threshold'] and sector in c['policy']['critical_service_sectors'],
        'labor_critical':score['labor']>=c['policy']['critical_labor_threshold'] and score['dependencies']>=c['policy']['critical_dependency_threshold'],
    }
    urgent=rng.random()<c['policy']['hypothetical_urgent_harm_probability']
    category=classify(score,flags,c['policy'])
    mode=c['evidence_mode']
    appeal=False; strategic=False
    if mode=='atlas_legal_sale_benchmark':
        if not observed_sales:raise ValueError('Sin ventas del Atlas')
        sale_time=rng.choice(observed_sales)
        # Pesos explícitos: NO constituyen observaciones de distribución entre etapas.
        durations={k:sale_time*c['atlas_sale_stage_weights'][k] for k in LEGAL_STAGES}
        origin='ventas_atlas_D07_filtradas_solo_ruta_juridica'
    else:
        durations={k:rng.triangular(lo,hi,middle) for k,(lo,middle,hi) in c['stage_durations'].items()}
        appeal=rng.random()<c['behavior']['appeal_probability']
        strategic=rng.random()<c['behavior']['delay_probability']
        if appeal:
            lo,hi=c['behavior']['appeal_extra_months']
            durations['authority_review']+=rng.uniform(lo,hi)
        if strategic:
            lo,hi=c['behavior']['delay_months']
            durations['buyer_search']+=rng.uniform(lo,hi)
        origin='todos_los_tiempos_hipoteticos'
    if mode=='atlas_legal_sale_benchmark':
        for k in c['stage_durations']:
            if k not in durations:
                lo,mid,hi=c['stage_durations'][k]
                durations[k]=rng.triangular(lo,hi,mid)
    sector_factor=c['technical_sector_multiplier'].get(sector,1.0)
    for stage in COMPLEXITY_STAGES:
        durations[stage]*=stage_complexity_multiplier(stage,score,c)
        if stage in TECH_STAGES:
            durations[stage]*=sector_factor*c['sector_multiplier_scale']*c['operational_scale']
    durations['transitional_services']*=c['transitional_services_scale']
    # Una interrupción operativa exógena no se imputa a mala fe y puede darse en ambos modos.
    disruption=rng.random()<c['operational_disruption']['probability']
    if disruption:
        lo,hi=c['operational_disruption']['extra_months']
        durations[c['operational_disruption']['target_stage']]+=rng.uniform(lo,hi)
    return Company(
        id=f'SYNT-{idx:06d}',sector=sector,complexity=score,category=category,
        flag_service_critical=flags['service_critical'],flag_labor_critical=flags['labor_critical'],
        flag_urgent_harm=urgent,appeal_simulated=appeal,delay_intent_simulated=strategic,
        origin_time=origin,durations={k:round(v,7) for k,v in durations.items()},
        operational_disruption_hypothetical=disruption,
    )


def simulate_company(company:Company,c:dict,capture_events:bool=True)->Company:
    finish={};starts={}
    for task,deps in DEPENDENCIES.items():
        start=max((finish[d] for d in deps),default=0.0)
        starts[task]=start
        finish[task]=start+company.durations[task]
    company.finishes=finish
    if not capture_events:return company
    q=[];counter=itertools.count()
    def push(t,order,name,task,message=''):
        heapq.heappush(q,(t,order,next(counter),Event(round(t,7),order,name,task,message)))
    for task in DEPENDENCIES:
        push(starts[task],10,'TASK_STARTED',task)
        push(finish[task],20,'TASK_COMPLETED',task)
    if company.flag_urgent_harm:
        push(0,0,'PROTECTIVE_REVIEW','critical','Caso sintético, sin sanción ni culpabilidad')
    if company.operational_disruption_hypothetical:
        disruption_stage=c['operational_disruption']['target_stage']
        push(starts[disruption_stage],5,'OPERATIONAL_DISRUPTION_ASSUMED',disruption_stage,
             'Duración extra incorporada a priori: NO es un cambio dinámico de planificación')
    limits=c['policy']['categories'][company.category]
    push(limits['initial_months'],30,'INITIAL_DEADLINE','deadline')
    push(limits['max_months'],40,'CATEGORY_MAXIMUM','deadline','No prórroga automática')
    while q:
        company.events.append(heapq.heappop(q)[3])
    return company


def run(c:dict,sales:tuple[float,...]=(),trace_limit:int=5)->dict[str,Any]:
    validate_config(c)
    if c['evidence_mode']=='atlas_legal_sale_benchmark' and not sales:
        raise ValueError('El modo Atlas requiere datos exactos de ventas')
    if not isinstance(trace_limit,int) or trace_limit<0:raise ValueError('trace_limit inválido')
    rng=random.Random(c['population']['seed'])
    results=[]; traces=[]
    for i in range(1,c['population']['n']+1):
        traced=len(traces)<trace_limit
        x=simulate_company(sample_company(i,rng,c,sales),c,capture_events=traced)
        if traced:traces.append(x)
        results.append(x.result(c))
    numeric=('control_by_initial','control_by_maximum','autonomy_by_initial',
             'autonomy_by_maximum','verification_by_maximum')
    summary={k:round(mean(r[k] for r in results),6) for k in numeric}
    per_category={}
    for category in ('I','II','III'):
        rr=[r for r in results if r['category']==category]
        if rr:
            per_category[category]={
              'n':len(rr),
              'autonomy_median_months':round(median(r['operational_autonomy_month'] for r in rr),4),
              'control_median_months':round(median(r['control_transfer_month'] for r in rr),4),
              'autonomy_by_initial':round(mean(r['autonomy_by_initial'] for r in rr),6),
              'autonomy_by_maximum':round(mean(r['autonomy_by_maximum'] for r in rr),6),
              'median_autonomy_to_sale_ratio_simulated':round(median(r['autonomy_to_sale_ratio_simulated'] for r in rr),5),
            }
    key=c['evaluation']['primary_metric'];threshold=c['evaluation']['target_fraction']
    summary.update({
        'companies':len(results),'scenario_mode':c['evidence_mode'],
        'median_autonomy_to_sale_ratio_simulated':round(median(r['autonomy_to_sale_ratio_simulated'] for r in results),5),
        'behavior_config_ignored_for_atlas_sale_route':bool(c['evidence_mode']=='atlas_legal_sale_benchmark'),
        'behavior_note':('En modo Atlas se omiten appeal_probability y delay_probability para la ruta jurídica: la duración documental ya los puede incluir; solo se modela interrupción operativa exógena.' if c['evidence_mode']=='atlas_legal_sale_benchmark' else 'Conducta totalmente sintética, no imputada a empresas reales.'),
        'primary_metric':key,'target_fraction_reference':threshold,
        'target_achieved_in_this_hypothetical_run':summary[key]>=threshold,
        'by_category':per_category,
        'not_a_legal_compliance_rate':True,
        'not_a_validated_forecast':True,
    })
    return {'summary':summary,'results':results,'companies':traces}
