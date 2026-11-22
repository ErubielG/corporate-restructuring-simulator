"""Motor de eventos discretos V3.2.

Las fechas NO se precalculan. Los eventos modifican estados y la cola futura.
Se usan tokens de generación para invalidar terminaciones antiguas al pausar,
reiniciar o modificar una etapa. Los eventos del pasado nunca se reescriben.
"""
from __future__ import annotations
import copy
import heapq
import itertools
import random
from collections import Counter
from dataclasses import dataclass, field
from statistics import mean,median
from typing import Any
from .config import LEGAL_STAGES
from .dynamic_config import validate_dynamic_config,generation_config
from .engine import DEPENDENCIES,sample_company

EPS=1e-8
INCIDENT_STAGES={
    'legal_appeal':'authority_review',
    'regulatory_suspension':'authority_review',
    'buyer_withdrawal':'authority_review',
    'remedy_revision':'authority_review',
    'technical_failure':'tech_preparation',
}
INCIDENT_FRACTIONS={
    'legal_appeal':.35,
    'buyer_withdrawal':.45,
    'regulatory_suspension':.55,
    'remedy_revision':.70,
    'technical_failure':.40,
    'operational_disruption':.50,
}

@dataclass
class Task:
    duration:float
    remaining:float
    deps:tuple[str,...]
    status:str='pending'
    token:int=0
    started_at:float|None=None
    finished_at:float|None=None
    attempts:int=0

@dataclass
class DynamicTrace:
    company_id:str
    category:str
    sector:str
    events:list[dict]=field(default_factory=list)
    finishes:dict[str,float]=field(default_factory=dict)
    incidents:dict[str,int]=field(default_factory=dict)

class DynamicRunner:
    def __init__(self,company,config,seed,capture=True):
        self.company=company
        self.c=config
        self.rng=random.Random(seed)
        self.capture=capture
        self.now=0.0
        self.seq=itertools.count()
        self.queue=[]
        self.logs=[]
        self.incidents=Counter()
        self.fired=set()
        self.tasks={name:Task(float(duration),float(duration),tuple(DEPENDENCIES[name]))
                    for name,duration in company.durations.items()}
        # Todas las dependencias vienen del DAG; no se permite agregar tareas sin reglas.
        self.tasks['verification'].deps=('transitional_services',)
        self.commercial_supply=(self.rng.random()<config['dynamic_events']['commercial_supply_probability'])
        if self.commercial_supply:
            self.tasks['verification'].deps=('operational_cutover',)
        self.chosen={}
        mode=config['evidence_mode']
        allow_legal=(mode=='synthetic_only' or config['dynamic_events']['allow_counterfactual_legal_on_atlas'])
        for ev,stage in INCIDENT_STAGES.items():
            probability=config['dynamic_events'][ev]['probability'] if allow_legal or stage not in LEGAL_STAGES else 0.0
            self.chosen[ev]=self.rng.random()<probability
        self.chosen['operational_disruption']=self.rng.random()<config['operational_disruption']['probability']
        self.incident_stage=dict(INCIDENT_STAGES)
        self.incident_stage['operational_disruption']=config['operational_disruption']['target_stage']
        self.horizon=config['dynamic_events']['max_simulation_months']
        self.max_events=config['dynamic_events']['max_events_per_company']
        self.processed=0

    def push(self,at,priority,kind,stage='',token=0,payload=None):
        if at < self.now-1e-7:raise RuntimeError('Intento de programar un evento en el pasado')
        heapq.heappush(self.queue,(float(at),priority,next(self.seq),kind,stage,token,payload))

    def log(self,kind,stage='',**details):
        self.incidents[kind]+=1
        if self.capture:
            self.logs.append({'month':round(self.now,7),'event':kind,'stage':stage,**details})

    def deps_met(self,stage):
        return all(self.tasks[d].status=='finished' for d in self.tasks[stage].deps)

    def start(self,stage):
        task=self.tasks[stage]
        if task.status not in ('pending','paused') or not self.deps_met(stage):return
        was_paused=task.status=='paused'
        task.status='running';task.started_at=self.now;task.attempts+=int(not was_paused)
        task.token+=1
        token=task.token
        self.log('TASK_RESUMED' if was_paused else 'TASK_STARTED',stage,attempt=task.attempts)
        self.push(self.now+task.remaining,20,'COMPLETE',stage,token)
        if task.remaining>EPS:
            for name,where in self.incident_stage.items():
                if where==stage and self.chosen.get(name) and name not in self.fired:
                    fraction=INCIDENT_FRACTIONS[name]
                    self.push(self.now+task.remaining*fraction,5,'INCIDENT',stage,token,name)

    def unlock(self):
        for stage,task in self.tasks.items():
            if task.status=='pending' and self.deps_met(stage):self.start(stage)

    def complete(self,stage,token):
        task=self.tasks[stage]
        if task.status!='running' or task.token!=token:return
        task.remaining=0.;task.status='finished';task.finished_at=self.now
        self.log('TASK_COMPLETED',stage)
        if stage=='legal_transfer':self.log('CONTROL_TRANSFERRED',stage)
        if stage=='operational_cutover' and self.commercial_supply:self.log('AUTONOMY_REACHED',stage,meaning='TSA posterior es suministro no crítico hipotético')
        if stage=='transitional_services' and not self.commercial_supply:self.log('AUTONOMY_REACHED',stage,meaning='Fin de dependencia crítica hipotética')
        self.unlock()

    def stop_running(self,stage):
        task=self.tasks[stage]
        if task.status!='running':return
        task.remaining=max(0.,task.remaining-(self.now-task.started_at))
        task.status='paused';task.token+=1
        task.started_at=None

    def pause(self,stage,delay,reason):
        self.stop_running(stage)
        self.log('TASK_PAUSED',stage,reason=reason,duration_months=round(delay,7))
        self.push(self.now+delay,8,'RESUME',stage,self.tasks[stage].token)

    def incident(self,stage,token,kind):
        task=self.tasks[stage]
        if task.status!='running' or task.token!=token or kind in self.fired:return
        self.fired.add(kind)
        opts=self.c['dynamic_events']
        self.log(kind.upper(),stage,experimental=True)
        def draw(bounds):return self.rng.uniform(*bounds)
        if kind=='buyer_withdrawal':
            self.stop_running('authority_review')
            review=self.tasks['authority_review']
            review.status='pending';review.remaining=review.duration
            oldbuyer=self.tasks['buyer_search']
            if oldbuyer.status!='finished':raise RuntimeError('No hay comprador previo')
            # Se deshace únicamente la habilitación futura: se conserva el hito histórico.
            oldbuyer.status='pending';oldbuyer.finished_at=None
            penalty=draw(opts[kind]['replacement_search_months'])
            oldbuyer.remaining=oldbuyer.duration+penalty
            self.log('BUYER_SEARCH_REOPENED','buyer_search',extra_months=round(penalty,7))
            self.unlock()
        elif kind=='remedy_revision':
            add_review=draw(opts[kind]['review_rework_months'])
            redesign=draw(opts[kind]['redesign_months'])
            self.stop_running(stage)
            task.remaining+=add_review
            extra='remedy_redesign'
            if extra not in self.tasks:
                self.tasks[extra]=Task(redesign,redesign,())
                # La fase de corte no puede empezar hasta terminar el nuevo requisito.
                self.tasks['operational_cutover'].deps+=('remedy_redesign',)
                self.log('TASK_ADDED',extra,duration_months=round(redesign,7))
                self.start(extra)
            self.push(self.now,8,'RESUME',stage,task.token)
        elif kind=='technical_failure':
            task.remaining+=draw(opts[kind]['rework_months'])
            self.pause(stage,draw(opts[kind]['repair_months']),kind)
        elif kind=='operational_disruption':
            duration=draw(self.c['operational_disruption']['extra_months'])
            self.pause(stage,duration,kind)
        elif kind in ('legal_appeal','regulatory_suspension'):
            self.pause(stage,draw(opts[kind]['duration_months']),kind)
        else:raise RuntimeError('Evento de incidente desconocido')

    def execute(self):
        self.push(self.c['policy']['categories'][self.company.category]['initial_months'],50,'DEADLINE','initial')
        self.push(self.c['policy']['categories'][self.company.category]['max_months'],60,'DEADLINE','maximum')
        if self.company.flag_urgent_harm:self.log('PROTECTIVE_REVIEW','critical',no_sanction=True)
        self.unlock()
        while self.queue:
            t,priority,seq,kind,stage,token,payload=heapq.heappop(self.queue)
            if t>self.horizon:
                self.now=self.horizon
                self.log('CENSORED_AT_HORIZON','simulation')
                break
            self.now=t
            self.processed+=1
            if self.processed>self.max_events:
                raise RuntimeError('Límite de eventos por empresa superado')
            if kind=='COMPLETE':self.complete(stage,token)
            elif kind=='INCIDENT':self.incident(stage,token,payload)
            elif kind=='RESUME':
                if self.tasks[stage].status=='paused' and self.tasks[stage].token==token:self.start(stage)
            elif kind=='DEADLINE' and t>0:self.log('DEADLINE_REACHED',stage,legal_finding=False)
            elif kind=='EXTERNAL' and callable(getattr(self,'process_external_event',None)):
                self.process_external_event(payload)  # extensión optativa I-03; sin efecto en V3.2 base
            else:raise RuntimeError(f'Evento desconocido {kind}')
        finishes={name:task.finished_at for name,task in self.tasks.items() if task.finished_at is not None}
        control=finishes.get('legal_transfer')
        autonomy_stage='operational_cutover' if self.commercial_supply else 'transitional_services'
        autonomy=finishes.get(autonomy_stage)
        verification=finishes.get('verification')
        category=self.company.category
        limits=self.c['policy']['categories'][category]
        initial,maxi=float(limits['initial_months']),float(limits['max_months'])
        score=self.company.complexity
        row={'company_id':self.company.id,'sector':self.company.sector,'category':category,
             'source_of_sale_time':self.company.origin_time,
             'initial_months':initial,'maximum_months':maxi,
             'control_transfer_month':round(control,5) if control is not None else None,
             'operational_autonomy_month':round(autonomy,5) if autonomy is not None else None,
             'verification_month':round(verification,5) if verification is not None else None,
             'tsa_end_month':round(finishes['transitional_services'],5) if 'transitional_services' in finishes else None,
             'commercial_supply_nonblocking_hypothetical':self.commercial_supply,
             'autonomy_to_sale_ratio_simulated':round(autonomy/control,7) if autonomy is not None and control is not None and control>0 else None,
             'control_by_initial':control is not None and control<=initial,
             'control_by_maximum':control is not None and control<=maxi,
             'autonomy_by_initial':autonomy is not None and autonomy<=initial,
             'autonomy_by_maximum':autonomy is not None and autonomy<=maxi,
             'verification_by_maximum':verification is not None and verification<=maxi,
             'requires_structural_review_at_max':autonomy is None or autonomy>maxi,
             'simulation_complete':autonomy is not None and verification is not None,
             'legal_compliance_established':False,'sanction_or_wrongdoing_established':False,
             'critical_service':self.company.flag_service_critical,
             'critical_labor':self.company.flag_labor_critical,
             'urgent_harm_hypothetical':self.company.flag_urgent_harm,
             'appeal_hypothetical':bool('legal_appeal' in self.fired),
             'buyer_withdrawal_hypothetical':bool('buyer_withdrawal' in self.fired),
             'regulatory_suspension_hypothetical':bool('regulatory_suspension' in self.fired),
             'remedy_revision_hypothetical':bool('remedy_revision' in self.fired),
             'technical_failure_hypothetical':bool('technical_failure' in self.fired),
             'operational_disruption_hypothetical':bool('operational_disruption' in self.fired),
             **{f'complexity_{k}':v for k,v in score.items()}}
        trace=DynamicTrace(self.company.id,category,self.company.sector,self.logs,finishes,dict(self.incidents))
        return row,trace


def run_dynamic(config,sales=(),trace_limit=5):
    validate_dynamic_config(config)
    if config['evidence_mode']=='atlas_legal_sale_benchmark' and not sales:
        raise ValueError('Faltan ventas observadas para la ruta jurídica')
    if not isinstance(trace_limit,int) or trace_limit<0:raise ValueError('trace_limit inválido')
    legacy=generation_config(config)
    rng=random.Random(config['population']['seed'])
    rows=[];traces=[];counters=Counter()
    for idx in range(1,config['population']['n']+1):
        company=sample_company(idx,rng,legacy,sales)
        runner=DynamicRunner(company,config,seed=1000003*config['population']['seed']+idx,capture=idx<=trace_limit)
        row,trace=runner.execute()
        rows.append(row)
        counters.update({name:n for name,n in trace.incidents.items() if name in ('LEGAL_APPEAL','BUYER_WITHDRAWAL','REGULATORY_SUSPENSION','REMEDY_REVISION','TECHNICAL_FAILURE','OPERATIONAL_DISRUPTION')})
        if idx<=trace_limit:traces.append(trace)
    metrics=('control_by_initial','control_by_maximum','autonomy_by_initial','autonomy_by_maximum','verification_by_maximum')
    summary={key:round(mean(r[key] for r in rows),6) for key in metrics}
    by_category={}
    for cat in ('I','II','III'):
        rr=[r for r in rows if r['category']==cat]
        if not rr:continue
        auto=[r['operational_autonomy_month'] for r in rr if r['operational_autonomy_month'] is not None]
        ratios=[r['autonomy_to_sale_ratio_simulated'] for r in rr if r['autonomy_to_sale_ratio_simulated'] is not None]
        by_category[cat]={'n':len(rr),'autonomy_by_maximum':round(mean(r['autonomy_by_maximum'] for r in rr),6),
            'autonomy_by_initial':round(mean(r['autonomy_by_initial'] for r in rr),6),
            'autonomy_median_months':round(median(auto),5) if auto else None,
            'median_autonomy_to_sale_ratio_simulated':round(median(ratios),5) if ratios else None}
    ratios=[r['autonomy_to_sale_ratio_simulated'] for r in rows if r['autonomy_to_sale_ratio_simulated'] is not None]
    target=config['evaluation']['target_fraction']
    summary.update({'companies':len(rows),'scenario_mode':config['evidence_mode'],
        'median_autonomy_to_sale_ratio_simulated':round(median(ratios),5) if ratios else None,
        'primary_metric':'autonomy_by_maximum','target_fraction_reference':target,
        'target_achieved_in_this_hypothetical_run':summary['autonomy_by_maximum']>=target,
        'by_category':by_category,'incident_counts':dict(counters),
        'censored_at_horizon':sum(not r['simulation_complete'] for r in rows),
        'counterfactual_legal_changes_on_atlas':config['evidence_mode']=='atlas_legal_sale_benchmark' and config['dynamic_events']['allow_counterfactual_legal_on_atlas'],
        'not_a_legal_compliance_rate':True,'not_a_validated_forecast':True})
    return {'summary':summary,'results':rows,'companies':traces}
