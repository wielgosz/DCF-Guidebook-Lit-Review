#!/usr/bin/env python3
import argparse, re, uuid
from pathlib import Path
import pandas as pd

def read_text(path): return Path(path).read_text(encoding='utf-8', errors='ignore') if Path(path).exists() else ''
def page_of_pos(text, pos):
    head=text[:pos]
    return head.count('[[PRISMA_PAGE_BREAK]]')+head.count('[[PAGE ')+1

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--text-root', required=True)
    ap.add_argument('--patterns', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True, exist_ok=True)
    corpus=pd.read_csv(args.corpus)
    try:
        patterns=pd.read_csv(args.patterns)
        col='pattern' if 'pattern' in patterns.columns else patterns.columns[0]
        terms=patterns[col].dropna().astype(str).unique().tolist()
    except Exception:
        terms=['PRODES','DETER','MapBiomas','Global Forest Watch','GFW','Hansen','CAR','SICAR','IBAMA','INCRA','SIGEF','SNCI','FUNAI','WDPA','Landsat','Sentinel','MODIS','Planet','NICFI','Trase','SEI-PCS','GeoRSPO','Universal Mill List','dataset','database','satellite imagery','geospatial data','risk map']
    rows=[]
    for _,doc in corpus.iterrows():
        doc_id=str(doc['doc_id']); text=read_text(Path(args.text_root)/f'{doc_id}.txt')
        for term in terms:
            if not term: continue
            for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
                start=max(0,m.start()-300); end=min(len(text),m.end()+300)
                rows.append({'mention_id':str(uuid.uuid4()),'doc_id':doc_id,'document_title':doc.get('title',''),'year':doc.get('year',''),'authors_or_orgs':doc.get('authors_or_orgs',''),'file_name':doc.get('file_name',''),'page_number':page_of_pos(text,m.start()),'section_hint':'auto','trigger_type':'seed_term','trigger_term':term,'dataset_mention_original':m.group(0),'normalized_candidate_string':m.group(0).strip().lower(),'context_snippet':re.sub(r'\s+',' ',text[start:end]).strip(),'extraction_confidence':'candidate','notes':''})
    df=pd.DataFrame(rows)
    df.to_csv(out/'Dataset_Mentions_Raw.csv', index=False)
    if not df.empty:
        df.groupby('normalized_candidate_string').agg(raw_mention_rows=('mention_id','count'), documents=('doc_id','nunique')).reset_index().sort_values('raw_mention_rows',ascending=False).to_csv(out/'Candidate_String_Summary.csv', index=False)
if __name__=='__main__': main()
