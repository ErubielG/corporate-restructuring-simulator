"""Pruebas de itinerarios empresariales sobre V3.2 (SIN calibración).

Cada evento se programa EXPRESAMENTE en meses artificiales; los hitos I-03
solo justifican la clase de evento y NO su probabilidad ni duración.
No convierte una fecha regulatoria real en un reloj de autonomía.
"""
from __future__ import annotations
import copy,math,random
from pathlib import Path
from .dynamic_engine import DynamicRunner,EPS
from .dynamic_config import generation_config,validate_dynamic_config
from .engine import sample_company

EVENT_TYPES={
    'ASSET_TRANSFERRED','CONTRACT_TRANCHE_COMPLETED','CERTIFICATION_GRANTED',
    'TSA_EFFECTIVE_END','DEPENDENCY_RELEASED','TSA_PLANNED','OWNER_CHANGED',
    'REMEDY_SUBSTITUTED','SALE_CANCELLED','SHARE_TRANSFER_ONLY','ACTIVITY_CEASED',
    'BUYER_REJECTED','FOLLOWUP_NOTE'
}
TERMINAL={'REMEDY_SUBSTITUTED','SALE_CANCELLED','SHARE_TRANSFER_ONLY','ACTIVITY_CEASED'}
WITH_ITEM={'ASSET_TRANSFERRED','CONTRACT_TRANCHE_COMPLETED','CERTIFICATION_GRANTED'}

def validate_pathway(pathway):
    keys={'case_label','company_id','analogy_case','horizon_months','ordinary_supply',
          'required_assets','required_contract_tranches','required_certifications',
          'require_tsa_termination','require_dependency_release','events'}
    if set(pathway)-keys:raise ValueError(f'Claves desconocidas de itinerario: {set(pathway)-keys}')
    if not isinstance(pathway.get('company_id'),str) or not pathway['company_id'].startswith('SYNT-'):
        raise ValueError('Solo empresas sintéticas SYNT-*')
    horizon=pathway.get('horizon_months',240)
    if isinstance(horizon,bool) or not isinstance(horizon,(int,float)) or not 1<=horizon<=10000:
        raise ValueError('Horizonte artificial inválido')
    for k in ('ordinary_supply','require_tsa_termination','require_dependency_release'):
        if k in pathway and not isinstance(pathway[k],bool):raise ValueError(k+' debe ser bool')
    for k in ('required_assets','required_contract_tranches','required_certifications'):
        seq=pathway.get(k,[])
        if not isinstance(seq,list) or any(not isinstance(x,str) or not x for x in seq) or len(seq)!=len(set(seq)):
            raise ValueError(f'{k} debe ser lista sin duplicados')
    es=pathway.get('events',[])
    if not isinstance(es,list):raise ValueError('events debe ser lista')
    for e in es:
        if not isinstance(e,dict) or set(e)-{'month','type','item','note'} or not {'month','type'}<=set(e):
            raise ValueError(f'Evento inválido: {e}')
        if e['type'] not in EVENT_TYPES:raise ValueError('Tipo de evento no permitido '+str(e['type']))
        t=e['month']
        if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or t<0:
            raise ValueError('Mes inválido')
        if e['type'] in WITH_ITEM and (not isinstance(e.get('item'),str) or not e['item']):
            raise ValueError('Evento requiere item')
        for key,etype in (('required_assets','ASSET_TRANSFERRED'),
                          ('required_contract_tranches','CONTRACT_TRANCHE_COMPLETED'),
                          ('required_certifications','CERTIFICATION_GRANTED')):
            if e['type']==etype and e['item'] not in pathway.get(key,[]):
                raise ValueError(f'Hito no exigido: {e["item"]}')
    return True

class PathwayRunner(DynamicRunner):
    """Extensión optativa: hitos externos explícitos que habilitan/terminan fases.

    No añade probabilidades; no cambia los parámetros P09-P14.
    """
    def __init__(self,company,config,seed,pathway,capture=True):
        validate_pathway(pathway)
        if company.id!=pathway['company_id']:raise ValueError('ID de caso no corresponde')
        super().__init__(company,config,seed,capture)
        self.pathway=copy.deepcopy(pathway)
        self.horizon=float(pathway.get('horizon_months',self.horizon))
        if 'ordinary_supply' in pathway:self.commercial_supply=pathway['ordinary_supply']
        self.tasks['verification'].deps=('operational_cutover',) if self.commercial_supply else ('transitional_services',)
        self.completed_assets=set();self.completed_tranches=set();self.completed_certifications=set()
        self.tsa_effectively_terminated=False;self.critical_dependency_released=False
        self.terminal_outcome=None;self.autonomy_reached_at=None
        self.asset_last_at=None;self.control_reached_at=None
        for e in pathway.get('events',[]):
            self.push(e['month'],2,'EXTERNAL','scenario',0,e)

    def obligations_met(self):
        p=self.pathway
        return (set(p.get('required_assets',[]))<=self.completed_assets
                and set(p.get('required_contract_tranches',[]))<=self.completed_tranches
                and set(p.get('required_certifications',[]))<=self.completed_certifications
                and (not p.get('require_tsa_termination',False) or self.tsa_effectively_terminated)
                and (not p.get('require_dependency_release',False) or self.critical_dependency_released)
                and self.terminal_outcome is None)

    def log(self,kind,stage='',**details):
        if kind=='CONTROL_TRANSFERRED' and self.pathway.get('required_assets'):
            if set(self.pathway['required_assets'])-self.completed_assets:
                return super().log('BASE_LEGAL_TRANSFER_COMPLETED',stage,scope_incomplete=True)
        if kind=='AUTONOMY_REACHED':
            if self.autonomy_reached_at is not None or not self.obligations_met():return
            self.autonomy_reached_at=self.now
        super().log(kind,stage,**details)

    def deps_met(self,stage):
        if self.terminal_outcome:return False
        if stage=='verification' and not self.obligations_met():return False
        return super().deps_met(stage)

    def unlock(self):
        if self.terminal_outcome:return
        super().unlock()

    def _refresh(self):
        if self.terminal_outcome:return
        legal=self.tasks['legal_transfer']
        assets=set(self.pathway.get('required_assets',[]))
        if legal.status=='finished' and assets<=self.completed_assets and self.control_reached_at is None:
            self.control_reached_at=max(legal.finished_at,self.asset_last_at or 0)
            if assets:
                self.log('REMEDY_SCOPE_TRANSFERRED','assets',asset_count=len(assets))
                if legal.finished_at < self.now-EPS:
                    self.log('CONTROL_TRANSFERRED','assets',complete_scope=True)
        stage='operational_cutover' if self.commercial_supply else 'transitional_services'
        if self.autonomy_reached_at is None and self.tasks[stage].status=='finished' and self.obligations_met():
            self.log('AUTONOMY_REACHED',stage,meaning='Hitos artificiales cumplidos; NO evidencia empírica')
        self.unlock()

    def complete(self,stage,token):
        super().complete(stage,token)
        if stage in ('legal_transfer','operational_cutover','transitional_services'):
            self._refresh()

    def process_external_event(self,e):
        typ=e['type']; item=e.get('item','')
        self.log('SCENARIO_'+typ,'scenario',item=item,illustrative=True,
                 note=e.get('note',''),historical_fact=False)
        if self.terminal_outcome:return
        if typ in TERMINAL:
            self.terminal_outcome=typ
            for t in self.tasks.values():
                if t.status!='finished':
                    t.status='terminated';t.token+=1
            self.log('PATHWAY_TERMINATED','scenario',outcome=typ,not_a_completed_sale=True)
            self.queue.clear()  # desenlace terminal NO equivale a censura al horizonte
            return
        if typ=='ASSET_TRANSFERRED':
            self.completed_assets.add(item)
            self.asset_last_at=self.now if self.asset_last_at is None else max(self.now,self.asset_last_at)
        elif typ=='CONTRACT_TRANCHE_COMPLETED':self.completed_tranches.add(item)
        elif typ=='CERTIFICATION_GRANTED':self.completed_certifications.add(item)
        elif typ=='TSA_EFFECTIVE_END':self.tsa_effectively_terminated=True
        elif typ=='DEPENDENCY_RELEASED':self.critical_dependency_released=True
        elif typ=='BUYER_REJECTED':
            task=self.tasks['authority_review']
            if task.status!='running':
                self.log('BUYER_REJECTION_NOT_APPLICABLE','authority_review',reason='Revisión no iniciada; no se imputa reinicio')
            else:
                self.incident('authority_review',task.token,'buyer_withdrawal')
        # TSA_PLANNED, OWNER_CHANGED, FOLLOWUP_NOTE: informativos, sin alterar autonomía.
        self._refresh()

    def execute(self):
        row,trace=super().execute()
        base_sale=row['control_transfer_month']
        # Venta jurídica individual no equivale a completar TODOS los activos del remedio.
        control=self.control_reached_at
        if control is None and not self.pathway.get('required_assets') and self.terminal_outcome is None:
            control=base_sale
        assets=self.pathway.get('required_assets',[])
        if self.terminal_outcome:outcome=self.terminal_outcome
        elif control is None and self.completed_assets:outcome='PARTIAL_TRANSFER'
        elif control is None:outcome='NO_COMPLETE_TRANSFER'
        elif self.autonomy_reached_at is None:outcome='TRANSFERRED_AUTONOMY_PENDING'
        else:outcome='AUTONOMY_REACHED_HYPOTHETICAL'
        limits=self.c['policy']['categories'][row['category']]
        auto=self.autonomy_reached_at
        # no presentar terminación de tarea base como autonomía si falta un hito obligatorio.
        row.update({
            'pathway_label':self.pathway.get('case_label',''),
            'analogy_case_not_a_simulated_real_company':self.pathway.get('analogy_case',''),
            'pathway_outcome':outcome,'base_legal_transfer_month':base_sale,
            'control_transfer_month':round(control,5) if control is not None else None,
            'operational_autonomy_month':round(auto,5) if auto is not None else None,
            'control_by_initial':control is not None and control<=limits['initial_months'],
            'control_by_maximum':control is not None and control<=limits['max_months'],
            'autonomy_by_initial':auto is not None and auto<=limits['initial_months'],
            'autonomy_by_maximum':auto is not None and auto<=limits['max_months'],
            'autonomy_to_sale_ratio_simulated':round(auto/control,7) if auto is not None and control is not None and control>0 else None,
            'verification_by_maximum':row['verification_month'] is not None and auto is not None and row['verification_month']<=limits['max_months'],
            'simulation_complete':auto is not None and row['verification_month'] is not None,
            'requires_structural_review_at_max':(auto is None or auto>limits['max_months']) and self.terminal_outcome is None,
            'pending_assets':sorted(set(assets)-self.completed_assets),
            'pending_contract_tranches':sorted(set(self.pathway.get('required_contract_tranches',[]))-self.completed_tranches),
            'pending_certifications':sorted(set(self.pathway.get('required_certifications',[]))-self.completed_certifications),
            'pending_tsa_actual_end':self.pathway.get('require_tsa_termination',False) and not self.tsa_effectively_terminated,
            'pending_critical_dependency_release':self.pathway.get('require_dependency_release',False) and not self.critical_dependency_released,
            'terminated_with_substitution_or_other_non_sale':self.terminal_outcome is not None,
            'horizon_months':self.horizon,
            'censored_simulation_horizon':any(e['event']=='CENSORED_AT_HORIZON' for e in trace.events),
            'source_category':'EXPLICIT_SYNTHETIC_STRESS_SCENARIO_NOT_I03_DURATION',
        })
        return row,trace

def run_gallery(config,sales,profiles):
    """Comparación pareada de LOS MISMOS perfiles sintéticos; no da tasa poblacional."""
    validate_dynamic_config(config)
    ids={p['company_id']:p for p in profiles}
    if len(ids)!=len(profiles):raise ValueError('Duplicados de empresa en perfiles')
    for p in profiles:validate_pathway(p)
    if config['evidence_mode']=='atlas_legal_sale_benchmark' and not sales:raise ValueError('Falta benchmark')
    maximum=max(int(k.removeprefix('SYNT-')) for k in ids)
    rng=random.Random(config['population']['seed']);g=generation_config(config)
    rows=[];traces=[]
    for idx in range(1,maximum+1):
        comp=sample_company(idx,rng,g,sales)
        if comp.id not in ids:continue
        seed=1000003*config['population']['seed']+idx
        baseline_config=copy.deepcopy(config)
        baseline_config['dynamic_events']['max_simulation_months']=ids[comp.id].get('horizon_months',config['dynamic_events']['max_simulation_months'])
        baseline,_=DynamicRunner(copy.deepcopy(comp),baseline_config,seed,capture=False).execute()
        altered,trace=PathwayRunner(copy.deepcopy(comp),config,seed,ids[comp.id],capture=True).execute()
        rows.append({'company_id':comp.id,'category':comp.category,
                     'analogy_case':ids[comp.id].get('analogy_case',''),
                     'baseline_autonomy_month_simulated':baseline['operational_autonomy_month'],
                     'baseline_control_month_simulated':baseline['control_transfer_month'],
                     'scenario_autonomy_month_simulated':altered['operational_autonomy_month'],
                     'scenario_control_month_simulated':altered['control_transfer_month'],
                     'baseline_within_maximum_simulated':baseline['autonomy_by_maximum'],
                     'scenario_within_maximum_simulated':altered['autonomy_by_maximum'],
                     'pathway_outcome':altered['pathway_outcome'],
                     'horizon_months':altered['horizon_months'],
                     'censored_simulation_horizon':altered['censored_simulation_horizon'],
                     'pending_assets':'|'.join(altered['pending_assets']),
                     'pending_contract_tranches':'|'.join(altered['pending_contract_tranches']),
                     'pending_certifications':'|'.join(altered['pending_certifications']),
                     'pending_tsa_actual_end':altered['pending_tsa_actual_end'],
                     'pending_critical_dependency_release':altered['pending_critical_dependency_release'],
                     'interpretation':'ILLUSTRATIVE / NOT A POPULATION ESTIMATE / NOT I03 CALIBRATION'})
        traces.append({'company_id':comp.id,'events':trace.events})
    return {'results':rows,'traces':traces,'scenario_count':len(rows),
            'warning':'Casos sintéticos seleccionados a propósito. No sumar como frecuencia empírica.'}
