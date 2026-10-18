#!/usr/bin/env python3
"""Runs actual Google Gemini evaluation; no generated/mock fallback."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
import uuid
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root/'server'))
from rescuemesh.ai import reassess

async def main(out):
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        result={'status':'BLOCKED','reason':'GOOGLE_CLOUD_PROJECT and ADC unavailable','real_model_calls':0,'cases_tested':0}
        Path(out).write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result)); return 2
    results=[]
    for line in (root/'evals/cases.jsonl').read_text().splitlines():
        case=json.loads(line); evidence=[]; passes=[]
        for phase in ['reports','additional_reports']:
            if phase not in case: continue
            for text in case[phase]:
                evidence.append({'event_id':str(uuid.uuid4()),'event_type':'observation','payload':{'incident_id':'eval-'+case['id'],'location_id':case['location_id'],'text':text,'claims':[]}})
            start=time.perf_counter()
            try:
                assessment,model=await reassess(evidence)
                passes.append({'phase':phase,'provider':'Google Gemini','model':model,'latency_ms':round((time.perf_counter()-start)*1000),'assessment':assessment.model_dump(mode='json'),'schema_and_citations':'PASS','question_theme_screen':any(t in assessment.next_question.lower() for t in case['question_themes']),'human_scores':None})
            except Exception as e:
                passes.append({'phase':phase,'status':'FAIL','error_type':type(e).__name__,'latency_ms':round((time.perf_counter()-start)*1000)})
        changed=len(passes)==2 and all('assessment' in p for p in passes) and passes[0]['assessment']['proposed_response']['action']!=passes[1]['assessment']['proposed_response']['action']
        results.append({'case_id':case['id'],'rubric':case['rubric'],'passes':passes,'proposal_text_changed':changed if 'additional_reports' in case else None})
    result={'status':'EXECUTED','provider':'Google Gemini','cases':results,'human_review':'required'}; Path(out).write_text(json.dumps(result,indent=2)+'\n'); print(f'Actual results saved to {out}')
    return 1 if any(p.get('status')=='FAIL' for c in results for p in c['passes']) else 0

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',default='artifacts/gemini-eval.json'); args=p.parse_args(); sys.exit(asyncio.run(main(args.out)))
