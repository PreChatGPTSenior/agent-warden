#!/usr/bin/env python3
"""Additional fail-closed source boundary; semantic behavior still requires ArchUnit/tests."""
import argparse,json,re
from pathlib import Path
from execution.core import Blocked,files

def check(root,stage):
 sources=[p for p in files(Path(root)/'stone-shelter-api/src/main/java') if p.suffix=='.java']
 text='\n'.join(p.read_text() for p in sources)
 forbidden=[r'<=>',r'/api/embeddings?',r'/api/embed']
 required=[r'org\.springframework\.ai\..*EmbeddingModel',r'org\.springframework\.ai\..*PgVectorStore']
 if stage in ['chat','rag']:
  forbidden += [r'["\']/api/(chat|generate)["\']']
  required += [r'org\.springframework\.ai\.chat\.client\.ChatClient']
 if stage=='rag':required += [r'org\.springframework\.ai\..*RetrievalAugmentationAdvisor']
 findings=[]
 for p in sources:
  for pattern in forbidden:
   if re.search(pattern,p.read_text()):findings.append({'file':str(p.relative_to(root)),'rule':'no-raw-inference-or-vector-sql','pattern':pattern})
 for pattern in required:
  if not re.search(pattern,text):findings.append({'rule':'required-spring-ai-boundary','pattern':pattern})
 if findings:raise Blocked(json.dumps(findings))
 return {'status':'PASS','stage':stage,'limitation':'Source boundary check, not proof that calls use correct admission or grounding; ArchUnit and focused tests remain required'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--stage',choices=['embedding','chat','rag'],required=True);a=p.parse_args()
 try:print(json.dumps(check(a.source,a.stage),indent=2))
 except Blocked as e:print(json.dumps({'status':'FAIL','reason':str(e)}));raise SystemExit(1)
