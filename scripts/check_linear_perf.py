#!/usr/bin/env python3
"""Check the portfolio update and its recorded-results data using only the standard library."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import csv
import hashlib
import json
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.categories = []
        self.h1_count = 0
        self.footer_count = 0
        self.lang = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html': self.lang = attrs.get('lang')
        if tag == 'h1': self.h1_count += 1
        if tag == 'footer': self.footer_count += 1
        if attrs.get('id'): self.ids.append(attrs['id'])
        if attrs.get('data-category'): self.categories.append(attrs['data-category'])
        key = 'href' if tag in ('a', 'link') else 'src' if tag in ('img', 'script') else None
        if key and attrs.get(key): self.links.append(attrs[key])

def require(condition, message):
    if not condition: errors.append(message)

pages = {}
for path in sorted(ROOT.rglob('*.html')):
    text = path.read_text(encoding='utf-8')
    parsed = Page(); parsed.feed(text)
    pages[path.resolve()] = parsed
    require(parsed.lang == 'en', str(path.relative_to(ROOT)) + ': expected English HTML')
    require(parsed.h1_count == 1, str(path.relative_to(ROOT)) + ': expected exactly one H1')
    require(parsed.footer_count == 0, str(path.relative_to(ROOT)) + ': unexpected footer')
    require(len(parsed.ids) == len(set(parsed.ids)), str(path.relative_to(ROOT)) + ': duplicate HTML IDs')
    require(not re.search(r'coming\s+soon|InferScale|TraceGuard|School of General Studies', text, re.I),
            str(path.relative_to(ROOT)) + ': retired public content remains')
    require(not re.search(r'[\u3400-\u9fff]', text), str(path.relative_to(ROOT)) + ': non-English page content')

for path, parsed in pages.items():
    for url in parsed.links:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc: continue
        if not parts.path:
            target = path
        elif parts.path.startswith('/'):
            target = ROOT / unquote(parts.path).lstrip('/')
        else:
            target = path.parent / unquote(parts.path)
        if target.is_dir(): target = target / 'index.html'
        target = target.resolve()
        require(target.is_file(), str(path.relative_to(ROOT)) + ': missing target ' + url)
        if parts.fragment and target in pages:
            require(unquote(parts.fragment) in pages[target].ids,
                    str(path.relative_to(ROOT)) + ': missing anchor ' + url)

require((ROOT/'README.md').read_text().strip() == 'This is my portfolio website: https://ryan30402.github.io/', 'README differs from the requested single line.')
require(sorted(pages[(ROOT/'projects/index.html').resolve()].categories) == ['learning', 'systems'], 'Expected exactly the learning series and the GPU project.')
require('/projects/linear-perf-lab/' in (ROOT/'sitemap.xml').read_text(), 'New project is absent from the sitemap.')

asset = ROOT/'assets/linear-perf'
data = json.loads((asset/'results.json').read_text())
require(len(data['metrics']) == 90, 'Expected 90 model-metric rows.')
require(len(data['paired_latencies']) == 288, 'Expected 288 paired-latency rows.')
require(len({r['case_id'] for r in data['paired_latencies']}) == 96, 'Expected 96 distinct modeling/pool shapes.')
keys = [(r['session_id'], r['split'], r['model_id']) for r in data['metrics']]
require(len(keys) == len(set(keys)), 'Duplicate model-metric rows.')
for session in ('fp16_s01','fp16_s02','fp16_s03','bf16_s01','bf16_s02','bf16_s03'):
    for split in ('development', 'test', 'challenge'):
        group = [r for r in data['metrics'] if r['session_id'] == session and r['split'] == split]
        require(len(group) == 5, 'Expected five models: ' + session + ' ' + split)
        require(sum(bool(r['selected_by_development']) for r in group) == 1, 'Expected one frozen selection.')
        for row in group:
            require(row['n_shapes'] == (24 if split == 'test' else 12), 'Unexpected evaluation shape count.')
            require(all(math.isfinite(row[k]) and row[k] >= 0 for k in ('median_ape_pct','p90_ape_pct')), 'Invalid metric value.')

with (asset/'evidence/model_metrics.csv').open(newline='') as f:
    original = {(r['session_id'],r['split'],r['model_id']):r for r in csv.DictReader(f)}
for row in data['metrics']:
    source = original[(row['session_id'],row['split'],row['model_id'])]
    for key in ('median_ape_pct','p90_ape_pct'):
        require(abs(row[key]-float(source[key])) < 1e-10, 'UI metric differs from archived CSV.')
with (asset/'evidence/paired_dtype_latencies.csv').open(newline='') as f:
    original_pairs = {(r['case_id'],r['round']):r for r in csv.DictReader(f)}
for row in data['paired_latencies']:
    source = original_pairs[(row['case_id'],row['round'])]
    for key in ('fp16_latency_us','bf16_latency_us','fp16_time_over_bf16_time'):
        require(abs(row[key]-float(source[key])) < 1e-10, 'UI latency differs from archived CSV.')
    require(abs(row['fp16_latency_us']/row['bf16_latency_us']-row['fp16_time_over_bf16_time']) < 1e-10, 'Invalid paired ratio.')

manifest = json.loads((asset/'evidence/manifest.json').read_text())
for name, expected in manifest['files'].items():
    path = asset/'evidence'/name
    require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Evidence hash mismatch: ' + name)

if errors:
    print('FAILED:')
    for error in errors: print(' -',error)
    sys.exit(1)
print('PASS: six pages, routes/anchors, English content, retired-card removal, one-line README, 90 model rows, 288 paired rows, source equality, and evidence hashes.')
print('This checks the website and supplied result tables; it does not rerun GPU measurements.')
