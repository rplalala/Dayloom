# Dayloom design prototypes

The `prototype/dayloom` branch captures the standalone Dayloom design prototypes separately from the
production application. The product implementation and research code remain on their
own branches.

## r7

- [Open the online prototype](https://dingzh.cc/Dayloom/prototype/)
- [GitHub Pages default address](https://rplalala.github.io/Dayloom/prototype/)
- [Read the prototype source and build instructions](r7/README.md)
- [View desktop Nearby](r7/review/desktop-nearby.jpg) and [mobile Nearby](r7/review/mobile-nearby.jpg)
- [Unified Product specification #198](https://github.com/rplalala/Dayloom/issues/198)
- [Content hashes](r7-manifest.json)

The r7 visual and interaction baseline was provisionally accepted on 21 October 2026.
It preserves the r5 visual language and explores accounts, editable preference text,
multiple drafts, account task recovery, recoverable previews, manual saving and imports.
Nearby uses activity-linked desktop groups and mobile inline disclosures. This answers
whether the agreed Product lifecycle fits the supplied page design; real backend
implementation is specified separately in #198.

The accepted standalone HTML is captured byte-for-byte. Its SHA-256 is
`7b69c4bf0d93e56e2b3fc5bbd1914f2e9696d21fded8c877c4f4a326932e09aa`.
The issue links to the exact source commit. Keep published version directories intact;
future design revisions use a new version directory instead of replacing r7.

Accounts, tasks and persistence are browser-local simulations. Use sample credentials;
no password is sent or stored. Google Places Photos and the production backend are not
connected. Place photos use labelled illustration fallbacks; atmosphere imagery uses
Unsplash. Never enter real credentials or private itinerary data into this public demo.

GitHub Pages publishes this branch's root with `.nojekyll`. The root opens `/prototype/`,
which currently serves the byte-identical r7 HTML. The `/r7/` archive remains intact.
This branch is a prototype archive and preview source, not a production merge target.
