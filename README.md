# Dayloom public showcase

[Explore Dayloom](https://rplalala.github.io/Dayloom/)

The `prototype/dayloom` branch owns this website's generated files and its
self-contained [source](source/). Browse the home, Sydney and London example
itineraries, place details and credited photographs. The showcase has no backend,
account, generation or personal storage service. The complete application and
V0–V3 implementation are maintained separately on `main`.

## Build and preview

Requires Node.js 22.12 or later and npm. From this branch's checkout:

```bash
cd source
npm ci
npm test
npm run build
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4178
```

Open `http://127.0.0.1:4178/Dayloom/`. The complete output is in `source/dist/`,
including the images copied from this branch's tracked `dayloom/` directory.
Hash routes such as `#/examples/london-example` support shared links and refreshes
without server rewrites. Tests cover guest browsing, photo credits, image-path
fallbacks and saved-date sorting without application API requests.

The presentation was extracted from product implementation `92c2152`, retaining
only the guest UI and public example data. `source/data/examples.json` contains
public detail projections and saved dates; `source/data/media.json` supplies image
bindings and credits. No project backend, credentials or private fixture bindings
are required. Image credits and rights are preserved in
[the photograph catalog](dayloom/examples/README.md); the source-code license does
not replace them.

## Publish

GitHub Pages serves this branch's root with `.nojekyll`. After testing a future
change, copy the contents of `source/dist/` to the branch root, including hidden
`.nojekyll`, then commit and push `prototype/dayloom`. Build output is ignored until
explicitly copied for publication. Keep `source/`, `prototype/`, `r7/` and the
manifest intact; replace the root `index.html` and corresponding `assets/` and
`dayloom/` files together. Never publish from the complete product checkout or
push these website changes to `main`.

The source extraction does not replace the existing published build. Its root
HTML, scripts, styles and images retain their original bytes until an explicit
future website update. The old `/prototype/` entry redirects to this showcase.

## Historical prototype

The accepted r7 source, screenshots and content hashes remain unchanged in
[`r7/`](r7/) and [`r7-manifest.json`](r7-manifest.json).