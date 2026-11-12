#!/usr/bin/env python3
"""Validate the published serving project without network access or a GPU."""
import csv
import hashlib
import io
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
NEW = '/projects/vllm-prefix-cache-bench/'
OLD = '/projects/linear-perf-lab/'

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs=[]; self.ids=[]; self.cards=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        if a.get('data-project')=='vllm-prefix-cache-bench': self.cards+=1
        for k in ('href','src'):
            if a.get(k): self.refs.append(a[k])

def require(ok, message):
    if not ok: raise ValueError(message)

def main():
    project=ROOT/'projects/vllm-prefix-cache-bench/index.html'
    text=project.read_text(encoding='utf-8')
    parser=Links(); parser.feed(text)
    require(len(parser.ids)==len(set(parser.ids)), 'Duplicate HTML ids')
    for name in ['index.html','projects/index.html']:
        p=Links(); t=(ROOT/name).read_text(encoding='utf-8');p.feed(t)
        require(p.cards==1,f'{name}: expected one featured serving project')
        require('Transformer Linear Layer Performance Predictor' not in t,f'{name}: old title remains')
        require(OLD not in t,f'{name}: old route is still linked')
    old=(ROOT/'projects/linear-perf-lab/index.html').read_text(encoding='utf-8')
    require('noindex' in old and 'temporarily unavailable' in old.lower(),'Old route is not withdrawn')
    require('Transformer Linear Layer Performance Predictor' not in old,'Old content is still public')
    require(not (ROOT/'assets/linear-perf').exists(),'Old data assets remain deployed')
    for name in ['assets/css/linear-perf.css','assets/js/linear-perf.js']:
        require(not (ROOT/name).exists(),f'Old asset remains deployed: {name}')
    for ref in parser.refs:
        u=urlsplit(ref)
        if u.scheme or u.netloc or ref.startswith(('mailto:','tel:','data:')): continue
        if not u.path:
            require(not u.fragment or u.fragment in parser.ids,f'Unknown anchor: {ref}');continue
        target=ROOT/unquote(u.path.lstrip('/')) if u.path.startswith('/') else project.parent/unquote(u.path)
        if target.is_dir(): target=target/'index.html'
        require(target.is_file(),f'Missing local target: {ref}')
    data=json.loads((ROOT/'assets/prefix-cache/reference-summary.json').read_text())
    require(data['schema_version']==1 and len(data['rows'])==6,'Unexpected data schema')
    require(data['scope']['reference_runs']==42 and data['scope']['reference_requests']==21000,'Wrong experiment scale')
    require(data['scope']['main_runs']+data['scope']['memory_pressure_runs']==42,'Run counts do not reconcile')
    require(data['source_commit']=='31bd3f27adc617a32b6c9756b2e1d219f037bd8c','Unexpected source revision')
    raw=(ROOT/'assets/prefix-cache/reference-summary.csv').read_text()
    rows=list(csv.DictReader(io.StringIO(raw)))
    require(len(rows)==6,'CSV row count mismatch')
    for a,b in zip(data['rows'],rows):
        for k,v in a.items(): require(float(b[k])==float(v),f'CSV/JSON differ for {k}')
    require([r['gain'] for r in data['rows']]==[1.0,1.0,1.07,2.79,5.52,8.57],'Reported ratio mismatch')
    marker='<script type="application/json" id="pc-data">'
    embedded=json.loads(text.split(marker,1)[1].split('</script>',1)[0])
    require(embedded==data,'Embedded chart data differs from downloadable data')
    for name in ['assets/css/prefix-cache.css','assets/js/prefix-cache.js']:
        require((ROOT/name).stat().st_size>100,'Empty interactive asset')
    sitemap=ROOT/'sitemap.xml'
    if sitemap.exists():
        require(OLD not in sitemap.read_text(), 'Withdrawn route still in sitemap')
        require(NEW in sitemap.read_text(), 'New route absent from sitemap')
    print('PASS: project cards, withdrawn route, local links, anchors, source revision, six-condition data, and sitemap.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
