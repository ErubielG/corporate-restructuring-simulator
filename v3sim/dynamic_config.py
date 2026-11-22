"""V3.2: contrato de configuración dinámico. Todos los eventos son hipotéticos."""
import copy
import json
from pathlib import Path
from .config import validate_config, _exact_keys, _num

EVENT_TYPES=('legal_appeal','regulatory_suspension','buyer_withdrawal',
             'remedy_revision','technical_failure')


def validate_dynamic_config(c):
    if not isinstance(c,dict) or c.get('schema_version')!='V3_2_experimental':
        raise ValueError('Se requiere schema_version V3_2_experimental')
    legacy=copy.deepcopy(c)
    dynamic=legacy.pop('dynamic_events',None)
    legacy['schema_version']='V3_1_1_experimental'
    validate_config(legacy)
    if dynamic is None:raise ValueError('Falta dynamic_events')
    _exact_keys(dynamic,set(EVENT_TYPES)|{
        'allow_counterfactual_legal_on_atlas','commercial_supply_probability',
        'max_simulation_months','max_events_per_company'},'dynamic_events')
    if not isinstance(dynamic['allow_counterfactual_legal_on_atlas'],bool):
        raise ValueError('allow_counterfactual_legal_on_atlas debe ser booleano')
    _num(dynamic['commercial_supply_probability'],'commercial_supply_probability',0,1)
    _num(dynamic['max_simulation_months'],'max_simulation_months',1,10000)
    n=dynamic['max_events_per_company']
    if not isinstance(n,int) or isinstance(n,bool) or not 20<=n<=10000:
        raise ValueError('max_events_per_company fuera de rango')
    specs={
        'legal_appeal':('duration_months',),
        'regulatory_suspension':('duration_months',),
        'buyer_withdrawal':('replacement_search_months',),
        'remedy_revision':('redesign_months','review_rework_months'),
        'technical_failure':('repair_months','rework_months'),
    }
    for event,fields in specs.items():
        opts=dynamic[event]
        _exact_keys(opts,{'probability',*fields},f'dynamic_events.{event}')
        _num(opts['probability'],f'{event}.probability',0,1)
        for field in fields:
            bounds=opts[field]
            if not isinstance(bounds,list) or len(bounds)!=2:
                raise ValueError(f'Intervalo {event}.{field} inválido')
            lo,hi=(_num(x,f'{event}.{field}',0,1000) for x in bounds)
            if lo>hi:raise ValueError(f'Intervalo invertido: {event}.{field}')
    return None


def load_dynamic_config(path):
    c=json.loads(Path(path).read_text(encoding='utf-8'))
    validate_dynamic_config(c)
    return c


def generation_config(c):
    """Desactivar las adiciones anticipadas V3.1: V3.2 resuelve incidentes al ocurrir."""
    old=copy.deepcopy(c)
    old.pop('dynamic_events')
    old['schema_version']='V3_1_1_experimental'
    old['behavior']['appeal_probability']=0
    old['behavior']['delay_probability']=0
    old['operational_disruption']['probability']=0
    validate_config(old)
    return old
