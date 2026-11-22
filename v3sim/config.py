"""V3.1: configuración experimental y validación estricta.

La configuración NO tiene fuerza normativa ni está calibrada empíricamente.
"""
import json
import math
from pathlib import Path

REQUIRED_STAGES = (
 'plan', 'buyer_search', 'authority_review','legal_transfer',
 'tech_preparation','staff_preparation','infrastructure_preparation',
 'operational_cutover','transitional_services','verification'
)
LEGAL_STAGES = ('plan','buyer_search','authority_review','legal_transfer')
COMPLEXITY_STAGES = (
 'tech_preparation','staff_preparation','infrastructure_preparation',
 'operational_cutover','transitional_services','verification'
)
SCORES = frozenset(('technical','dependencies','labor','service_continuity'))


def _exact_keys(mapping, expected, where):
    if not isinstance(mapping,dict) or set(mapping)!=set(expected):
        missing=set(expected)-(set(mapping) if isinstance(mapping,dict) else set())
        extra=(set(mapping) if isinstance(mapping,dict) else set())-set(expected)
        raise ValueError(f'Claves inválidas en {where}; faltan={sorted(missing)}, sobran={sorted(extra)}')


def _num(x, name, lo=None, hi=None):
    if isinstance(x, bool) or not isinstance(x,(float,int)) or not math.isfinite(x):
        raise ValueError(f'{name}: número finito requerido')
    if lo is not None and x<lo or hi is not None and x>hi:
        raise ValueError(f'{name}: fuera de intervalo [{lo},{hi}]')
    return float(x)


def load_config(path: str | Path) -> dict:
    with open(path,'r',encoding='utf-8') as f: c=json.load(f)
    validate_config(c)
    return c


def validate_config(c: dict) -> None:
    _exact_keys(c, {'schema_version','evidence_mode','population','policy',
        'behavior','operational_disruption','technical_sector_multiplier',
        'stage_durations','complexity_duration','atlas_sale_stage_weights',
        'operational_scale','transitional_services_scale','sector_multiplier_scale','evaluation'}, 'config')
    if c['schema_version']!='V3_1_1_experimental':
        raise ValueError('schema_version inválida')
    if c['evidence_mode'] not in ('synthetic_only','atlas_legal_sale_benchmark'):
        raise ValueError('evidence_mode desconocido')
    p=c['population'];_exact_keys(p,{'n','seed','sector_weights'},'population')
    if isinstance(p['n'],bool) or not isinstance(p['n'],int) or not 1<=p['n']<=500000:
        raise ValueError('n fuera de rango')
    if not isinstance(p['seed'],int) or isinstance(p['seed'],bool):
        raise ValueError('semilla inválida')
    sw=p['sector_weights']
    if not isinstance(sw,dict) or not sw:raise ValueError('Pesos de sectores vacíos')
    if any(_num(w,'sector_weight',0,1)<0 for w in sw.values()) or abs(sum(sw.values())-1)>1e-8:
        raise ValueError('Pesos de sectores inválidos')
    pol=c['policy'];_exact_keys(pol,{
        'score_weights','score_thresholds','critical_min_category','critical_service_threshold',
        'critical_labor_threshold','critical_dependency_threshold','critical_service_sectors',
        'hypothetical_urgent_harm_probability','global_maximum_months','categories'},'policy')
    _exact_keys(pol['score_weights'],SCORES,'score_weights')
    if any(_num(v,'score_weight',0,1)<0 for v in pol['score_weights'].values()) or abs(sum(pol['score_weights'].values())-1)>1e-8:
        raise ValueError('La puntuación debe sumar 1')
    if len(pol['score_thresholds'])!=2 or not 0<_num(pol['score_thresholds'][0],'threshold',0,100)<_num(pol['score_thresholds'][1],'threshold',0,100)<100:
        raise ValueError('Umbrales fuera de orden')
    _num(pol['global_maximum_months'],'global_maximum',0.001)
    _exact_keys(pol['categories'],{'I','II','III'},'categories')
    for label,vals in pol['categories'].items():
        _exact_keys(vals,{'initial_months','max_months'},f'categories.{label}')
        initial=_num(vals['initial_months'],'initial',0.001)
        maximum=_num(vals['max_months'],'maximum',initial)
        if maximum>pol['global_maximum_months']:raise ValueError('Excede tope global')
    if pol['critical_min_category'] not in ('I','II','III'):raise ValueError('Piso crítico inválido')
    for name in ['critical_service_threshold','critical_labor_threshold','critical_dependency_threshold']:
        _num(pol[name],name,0,100)
    if not isinstance(pol['critical_service_sectors'],list) or not set(pol['critical_service_sectors']).issubset(sw):
        raise ValueError('Sectores críticos inválidos')
    _num(pol['hypothetical_urgent_harm_probability'],'urgent',0,1)
    _exact_keys(c['stage_durations'],REQUIRED_STAGES,'stage_durations')
    for name,tri in c['stage_durations'].items():
        if not isinstance(tri,list) or len(tri)!=3:raise ValueError(f'Triangular incompleta: {name}')
        lo,mode,hi=(_num(v,f'{name}.duracion',0) for v in tri)
        if not lo<=mode<=hi:raise ValueError(f'Triangular desordenada: {name}')
    _exact_keys(c['behavior'],{'appeal_probability','appeal_extra_months','delay_probability','delay_months'},'behavior')
    for k in ['appeal_probability','delay_probability']:_num(c['behavior'][k],k,0,1)
    for k in ['appeal_extra_months','delay_months']:
        bounds=c['behavior'][k]
        if len(bounds)!=2 or _num(bounds[0],k,0)>_num(bounds[1],k,0):raise ValueError(f'Intervalo inválido: {k}')
    _exact_keys(c['operational_disruption'],{'probability','extra_months','target_stage'},'operational_disruption')
    if c['operational_disruption']['target_stage'] not in ('tech_preparation','staff_preparation','infrastructure_preparation','operational_cutover','transitional_services'):
        raise ValueError('Etapa de interrupción no permitida')
    _num(c['operational_disruption']['probability'],'disruption.probability',0,1)
    bounds=c['operational_disruption']['extra_months']
    if len(bounds)!=2 or _num(bounds[0],'disruption.extra_months',0)>_num(bounds[1],'disruption.extra_months',0):
        raise ValueError('Duración de interrupción inválida')
    sector_factors=c['technical_sector_multiplier']
    if not isinstance(sector_factors,dict) or not set(sector_factors).issubset(sw):raise ValueError('Sectores del multiplicador inválidos')
    for v in sector_factors.values():_num(v,'sector.factor',0.01,10)
    comp=c['complexity_duration'];_exact_keys(comp,{'strength','max_effect','stage_drivers'},'complexity_duration')
    _num(comp['strength'],'complexity.strength',0,1)
    _num(comp['max_effect'],'complexity.max_effect',0,0.95)
    _exact_keys(comp['stage_drivers'],COMPLEXITY_STAGES,'stage_drivers')
    for stage,drivers in comp['stage_drivers'].items():
        if not isinstance(drivers,dict) or not drivers or not set(drivers).issubset(SCORES):
            raise ValueError(f'Drivers inválidos: {stage}')
        for v in drivers.values():_num(v,f'{stage}.driver',0,1)
        if abs(sum(drivers.values())-1)>1e-8:raise ValueError(f'Drivers no suman 1: {stage}')
    _exact_keys(c['atlas_sale_stage_weights'],LEGAL_STAGES,'atlas_sale_stage_weights')
    for v in c['atlas_sale_stage_weights'].values():_num(v,'legal weight',0,1)
    if abs(sum(c['atlas_sale_stage_weights'].values())-1)>1e-8:raise ValueError('Pesos de fases jurídicas no suman 1')
    _num(c['operational_scale'],'operational_scale',0.01,10)
    _num(c['transitional_services_scale'],'transitional_services_scale',0,10)
    _num(c['sector_multiplier_scale'],'sector_multiplier_scale',0.1,10)
    _exact_keys(c['evaluation'],{'target_fraction','primary_metric'},'evaluation')
    _num(c['evaluation']['target_fraction'],'target_fraction',0,1)
    if c['evaluation']['primary_metric']!='autonomy_by_maximum':
        raise ValueError('Métrica principal V3.1 debe ser autonomy_by_maximum')
