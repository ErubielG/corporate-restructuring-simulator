"""Summarize an output CSV from the fully synthetic portfolio demo.

All rates are properties of configured synthetic scenarios; no forecast claims.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median


def aggregate(rows):
    groups=defaultdict(list)
    for row in rows:
        groups[row['category']].append(row)
    result=[]
    for category,values in sorted(groups.items()):
        n=len(values)
        within=sum(str(x['autonomy_by_maximum']).strip().lower() in ('1','true') for x in values)
        months=[float(x['operational_autonomy_month']) for x in values if x['operational_autonomy_month'] not in ('','None',None)]
        result.append({'category':category,'companies_synthetic':n,
            'autonomy_by_maximum_simulated_rate':round(within/n,4),
            'autonomy_median_months_simulated':round(median(months),3) if months else None})
    return result


def main():
    parser=argparse.ArgumentParser(description='Analyze synthetic simulation CSV; NOT an economic forecast')
    parser.add_argument('--input',default='output/demo/empresas_resultados.csv')
    parser.add_argument('--out',default='output/demo/category_summary.csv')
    args=parser.parse_args()
    with open(args.input,newline='',encoding='utf-8') as f:
        results=aggregate(list(csv.DictReader(f)))
    target=Path(args.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    with open(target,'w',newline='',encoding='utf-8') as f:
        wr=csv.DictWriter(f,fieldnames=['category','companies_synthetic','autonomy_by_maximum_simulated_rate','autonomy_median_months_simulated'])
        wr.writeheader()
        wr.writerows(results)
    print(json.dumps({'type':'SYNTHETIC_DESCRIPTIVE_STATISTICS_NOT_VALIDATED', 'results':results},indent=2))

if __name__=='__main__':main()
