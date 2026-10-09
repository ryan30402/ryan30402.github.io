#!/usr/bin/env python3
"""Dependency-free checks for this static GitHub Pages website."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.h1_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h1': self.h1_count += 1
        attr = 'href' if tag in ('a','link') else ('src' if tag in ('img','script') else None)
        if attr and attrs.get(attr): self.targets.append((tag, attrs[attr]))

pages = sorted(ROOT.rglob('*.html'))
for page in pages:
    parser = Links()
    parser.feed(page.read_text(encoding='utf-8'))
    if parser.h1_count != 1:
        errors.append(f'{page.relative_to(ROOT)}: expected one H1; got {parser.h1_count}')
    for tag, url in parser.targets:
        if not url.startswith('/') or url.startswith('//'): continue
        clean = unquote(urlsplit(url).path).lstrip('/')
        target = ROOT / clean
        if not (target.is_file() or (target.is_dir() and (target/'index.html').is_file())):
            errors.append(f'{page.relative_to(ROOT)}: missing internal URL {url}')
    print('CHECKED', page.relative_to(ROOT))

book = ROOT / 'assets' / 'micrograd.ipynb'
try:
    notebook = json.loads(book.read_text(encoding='utf-8'))
    assert isinstance(notebook['cells'],list) and notebook['cells']
    print('CHECKED notebook:',len(notebook['cells']),'cells')
except Exception as e:
    errors.append('Invalid or missing notebook: '+str(e))

if errors:
    print('\nFAILED:')
    for issue in errors:print(' -',issue)
    sys.exit(1)
print('\nPASS: HTML routes/assets and notebook validated.')
