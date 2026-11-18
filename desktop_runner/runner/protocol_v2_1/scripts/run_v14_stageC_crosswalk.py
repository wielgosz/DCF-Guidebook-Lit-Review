#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd

def join_unique(s, max_items=None):
    vals=[str(x) for x in s.dropna().unique() if str(x)!='nan']
    vals=vals[:max_items] if max_items else vals
    return '; '.join(vals)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stageB', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--n-docs', type=int, default=0, help='Number of documents in the corpus (denominator for percentages); default: documents with a mention.')
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True, exist_ok=True)
    m=pd.read_csv(args.stageB)
    m=m[m['dataset_id'].notna()].copy()
    dby=(m.groupby(['doc_id','document_title','year','authors_or_orgs','file_name','dataset_id','preferred_dataset_name','dataset_provider','dataset_type','geography','preferred_access_url','canonical_apa_reference'])
        .agg(raw_mention_rows=('mention_id','count'), total_page_occurrences=('page_number','count'), unique_original_mentions=('dataset_mention_original',lambda s: join_unique(s)), page_numbers=('page_number',lambda s: ', '.join(map(str, sorted(set(s.dropna()))))), section_hints=('section_hint',lambda s: join_unique(s)), evidence_snippet_examples=('context_snippet',lambda s: join_unique(s, 3)))
        .reset_index())
    dby.to_csv(out/'Dataset_by_Document.csv', index=False)
    doc=(dby.groupby(['doc_id','document_title']).agg(dataset_count=('dataset_id','nunique'), canonical_dataset_ids=('dataset_id',join_unique), datasets_referenced=('preferred_dataset_name',join_unique)).reset_index())
    doc.to_csv(out/'Document_by_Dataset.csv', index=False)
    ds=(dby.groupby(['dataset_id','preferred_dataset_name','dataset_provider','dataset_type','geography','preferred_access_url','canonical_apa_reference']).agg(documents_referencing=('doc_id','nunique'), doc_ids=('doc_id',join_unique), document_titles=('document_title',join_unique), total_raw_mention_rows=('raw_mention_rows','sum'), total_page_occurrences=('total_page_occurrences','sum'), original_names_observed_in_crosswalk=('unique_original_mentions',join_unique)).reset_index())
    n_docs=args.n_docs or int(m['doc_id'].nunique())
    ds['percent_of_corpus_documents']=(ds['documents_referencing']/max(n_docs,1)*100).round(1)
    ds.sort_values('documents_referencing', ascending=False).to_csv(out/'Documents_by_Dataset.csv', index=False)
if __name__=='__main__': main()
