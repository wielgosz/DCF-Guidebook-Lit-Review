#!/usr/bin/env python3
import argparse, math, textwrap, zipfile
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

N_DOCS = 0

def wrap(s,width): return '\n'.join(textwrap.wrap(str(s), width=width, break_long_words=False))

def make_chart(df, label, value, title, path, shared_max, top=None):
    d=df.head(top).copy() if top else df.copy()
    fig_h=max(5, 0.45*len(d)+1.8); fig_w=11.5
    fig,ax=plt.subplots(figsize=(fig_w,fig_h))
    y=range(len(d)); vals=d[value].tolist()
    ax.barh(list(y), vals, color='#F0B310', edgecolor='none', height=0.62)
    ax.set_yticks(list(y)); ax.set_yticklabels([wrap(x,34) for x in d[label]], fontsize=9)
    ax.invert_yaxis(); ax.set_xlim(0,shared_max)
    ax.set_xlabel('Number of corpus documents referencing dataset/source')
    ax.set_title(title, fontsize=14, pad=12)
    ax.xaxis.grid(True, linewidth=0.4, alpha=0.35); ax.set_axisbelow(True)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    for yi,v in enumerate(vals): ax.text(min(v+shared_max*.01, shared_max*.97), yi, str(int(v)), va='center', fontsize=9)
    fig.text(.01,.01,f'Supply Chain Data Review | corpus denominator = {N_DOCS} documents', fontsize=8)
    fig.tight_layout(rect=(.22,.03,.98,.96)); fig.savefig(path, format='svg'); plt.close(fig)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stageC', required=True, help='Dataset_by_Document.csv')
    ap.add_argument('--registry', required=False)
    ap.add_argument('--out', required=True)
    ap.add_argument('--n-docs', type=int, default=0, help='Number of documents in the corpus (denominator for percentages); default: documents with a mention.')
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True, exist_ok=True)
    dby=pd.read_csv(args.stageC)
    global N_DOCS
    N_DOCS=args.n_docs or int(dby['doc_id'].nunique())
    rank=(dby.groupby(['dataset_id','preferred_dataset_name','dataset_provider','dataset_type','geography','preferred_access_url','canonical_apa_reference'])
        .agg(documents_referencing=('doc_id','nunique'), doc_ids=('doc_id',lambda s:'; '.join(sorted(set(s)))), total_raw_mention_rows=('raw_mention_rows','sum'), total_page_occurrences=('total_page_occurrences','sum'))
        .reset_index().sort_values(['documents_referencing','total_page_occurrences'], ascending=[False,False]))
    rank.insert(0,'rank',range(1,len(rank)+1)); rank['percent_of_corpus_documents']=(rank['documents_referencing']/max(N_DOCS,1)*100).round(1)
    rank.to_csv(out/'Dataset_Summary_Ranking.csv', index=False)
    prov=dby.groupby('dataset_provider').agg(documents_referencing=('doc_id','nunique'), dataset_count=('dataset_id','nunique')).reset_index().sort_values('documents_referencing',ascending=False)
    prov.to_csv(out/'Dataset_Provider_Summary.csv', index=False)
    typ=dby.groupby('dataset_type').agg(documents_referencing=('doc_id','nunique'), dataset_count=('dataset_id','nunique')).reset_index().sort_values('documents_referencing',ascending=False)
    typ.to_csv(out/'Dataset_Type_Summary.csv', index=False)
    shared=int(math.ceil(max(rank.documents_referencing.max(), prov.documents_referencing.max(), typ.documents_referencing.max())/5)*5)
    make_chart(rank,'preferred_dataset_name','documents_referencing','Datasets most widely referenced',out/'01_datasets_most_widely_referenced.svg',shared)
    make_chart(rank,'preferred_dataset_name','documents_referencing','Top 20 datasets most widely referenced',out/'02_top20_datasets_most_widely_referenced.svg',shared,top=20)
    make_chart(prov,'dataset_provider','documents_referencing','Dataset providers most widely referenced',out/'03_dataset_providers_most_widely_referenced.svg',shared,top=15)
    make_chart(typ,'dataset_type','documents_referencing','Dataset/source types most widely referenced',out/'04_dataset_types_most_widely_referenced.svg',shared,top=15)
if __name__=='__main__': main()
