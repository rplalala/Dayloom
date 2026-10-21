"""Build the standalone prototype: python source/build.py --output index.html."""
from pathlib import Path
import argparse

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=root.parent / 'index.html')
args = parser.parse_args()
css = '\n'.join((root / name).read_text(encoding='utf-8') for name in
                ['original.css', 'refinements.css', 'prototype.css', 'nearby.css'])
js = '\n'.join((root / name).read_text(encoding='utf-8') for name in
               ['data.js', 'icons.js', 'preferences.js', 'state.js', 'pages.js', 'nearby.js', 'details.js', 'actions.js'])
html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="description" content="Dayloom: thoughtful city itineraries, made yours.">
<title>Dayloom</title><style>''' + css + '''</style></head><body><div id="app"></div>
<noscript>Please enable JavaScript to explore this prototype.</noscript><script>(()=>{'use strict';
''' + js.replace('</script', '<\\/script') + '\n})();</script></body></html>'
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(html, encoding='utf-8')
print(f'Built {args.output.resolve()} ({len(html.encode()):,} bytes)')
