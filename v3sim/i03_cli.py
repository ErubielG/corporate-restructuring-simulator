"""CLI I-03: exportar mapeo y ejecutar galería de pruebas explícitas."""
import argparse,csv,hashlib,json
from pathlib import Path
from .dynamic_config import load_dynamic_config
from .i03_pathways import run_gallery
from .i03_bridge import export_proposals
from .atlas import read_atlas_sales

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='escenario_v32_atlas_ventas.json')
    p.add_argument('--atlas',default='data/Atlas_63_D07_V311_Benchmark.sqlite')
    p.add_argument('--source-atlas',default='data/Atlas_63_D07_I03.sqlite')
    p.add_argument('--transfer',required=True)
    p.add_argument('--profiles',default='escenarios_i03_prueba_mecanismos.json')
    p.add_argument('--out',required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    evidence=export_proposals(args.transfer,args.source_atlas,out)
    p_data=json.loads(Path(args.profiles).read_text(encoding='utf-8'))
    config=load_dynamic_config(args.config)
    atlas=read_atlas_sales(args.atlas)
    result=run_gallery(config,atlas.sale_months if config['evidence_mode']=='atlas_legal_sale_benchmark' else (),p_data['profiles'])
    with (out/'comparacion_pareada_escenarios.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result['results'][0]));w.writeheader();w.writerows(result['results'])
    (out/'trazas_escenarios_i03.json').write_text(json.dumps(result['traces'],ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'version':'V3.2.1-I03','type':'SOLO_EXPERIMENTAL',
      'scenario_gallery_no_frequency_inference':True,'not_new_D08':True,
      'proposals_inventory':evidence,'scenario_count':result['scenario_count'],
      'atlas_original_sha256':hashlib.sha256(Path(args.source_atlas).read_bytes()).hexdigest(),
      'scenario_config_sha256':hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
      'scenario_profiles_sha256':hashlib.sha256(Path(args.profiles).read_bytes()).hexdigest(),
      'warning':result['warning']}
    (out/'procedencia_i03.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':evidence,'cases':[{'id':r['company_id'],'outcome':r['pathway_outcome'],'auto':r['scenario_autonomy_month_simulated']} for r in result['results']]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
