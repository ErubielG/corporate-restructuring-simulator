"""Datos de empresas sintéticas: las categorías son parámetros exploratorios."""
from dataclasses import dataclass, field
from typing import Any

STAGES=('plan','buyer_search','authority_review','legal_transfer',
        'tech_preparation','staff_preparation','infrastructure_preparation',
        'operational_cutover','transitional_services','verification')

@dataclass(frozen=True)
class Event:
    month:float
    priority:int
    name:str
    stage:str
    detail:str=''

@dataclass
class Company:
    id:str
    sector:str
    complexity:dict[str,float]
    category:str
    flag_service_critical:bool
    flag_labor_critical:bool
    flag_urgent_harm:bool
    appeal_simulated:bool
    delay_intent_simulated:bool
    origin_time:str
    durations:dict[str,float]
    operational_disruption_hypothetical:bool=False
    events:list[Event]=field(default_factory=list)
    finishes:dict[str,float]=field(default_factory=dict)

    def result(self,config:dict)->dict[str,Any]:
        limits=config['policy']['categories'][self.category]
        initial=float(limits['initial_months']);maximum=float(limits['max_months'])
        control=self.finishes['legal_transfer']
        autonomy=self.finishes['transitional_services']
        verified=self.finishes['verification']
        row={
            'company_id':self.id,'sector':self.sector,'category':self.category,
            'source_of_sale_time':self.origin_time,
            'initial_months':initial,'maximum_months':maximum,
            'control_transfer_month':round(control,5),
            'operational_autonomy_month':round(autonomy,5),
            'verification_month':round(verified,5),
            'autonomy_to_sale_ratio_simulated':round(autonomy/control,7) if control>0 else None,
            'control_by_initial':control<=initial,'control_by_maximum':control<=maximum,
            'autonomy_by_initial':autonomy<=initial,'autonomy_by_maximum':autonomy<=maximum,
            'verification_by_maximum':verified<=maximum,
            'requires_structural_review_at_max':autonomy>maximum,
            'critical_service':self.flag_service_critical,
            'critical_labor':self.flag_labor_critical,'urgent_harm_hypothetical':self.flag_urgent_harm,
            'appeal_hypothetical':self.appeal_simulated,
            'strategic_intent_latent_hypothetical':self.delay_intent_simulated,
            'operational_disruption_hypothetical':self.operational_disruption_hypothetical,
            'legal_compliance_established':False,'sanction_or_wrongdoing_established':False,
        }
        row.update({f'complexity_{k}':self.complexity[k] for k in self.complexity})
        return row
