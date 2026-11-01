# Dayloom public showcase

[Explore Dayloom](https://rplalala.github.io/Dayloom/)

This branch publishes the static visitor showcase built from the existing product
frontend. Browse the home, Sydney and London example itineraries, place details
and credited photographs. Account, generation and personal storage services belong
to the separately installed application.

Source implementation revision: `92c2152ef6a60b7924afae8f7236f1f303caba1e`.
The source commits are retained locally; this branch contains the generated site.
From that source checkout, install frontend dependencies and run:

```bash
npm --prefix frontend run build:pages
```

Publish the contents of `frontend/dist-pages/` at this branch's root, including
`.nojekyll`. Hash routes keep shared links and page refreshes working without a
backend. The old `/prototype/` entry redirects to the showcase. The normal
frontend build continues to serve the complete application separately.

## Historical prototype

The accepted r7 source, screenshots and content hashes remain unchanged in
[`r7/`](r7/) and [`r7-manifest.json`](r7-manifest.json). They describe the historical
design prototype rather than the current showcase.