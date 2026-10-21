# Dayloom prototype r7

An interactive update of the supplied Dayloom Minimal Refined r5 prototype.
The prototype explores the agreed account, planning and manual-save flows, plus
activity-linked Nearby navigation within the existing two-column detail page. The original r5 stylesheets, page hierarchy and visual language
are preserved. This is a single design, not a set of alternative layouts.

## Open

Double-click `index.html`. Everything except Unsplash images works without a network
connection. When browser file-storage restrictions interfere with recovery, run the
following command from this directory and open the printed local address:

```sh
python -m http.server 8767 --bind 127.0.0.1
```

Use a sample email and any password with at least six characters. This prototype does
not authenticate real accounts, send passwords or store passwords. Each email identifies
a separate browser-local collection. Do not enter real credentials.

## Explore the agreed flows

- **Guest:** My trips contains the three r5 examples. Filling a travel brief is allowed;
  generation, draft saving, example copying and import ask for login. Returning from
  login restores context; generation requires another explicit click.
- **Account:** A new collection starts empty, with no example cards. Open the account
  through the avatar/name or mobile menu. Edit defaults, upload an avatar or restore
  initials. Defaults prefill new briefs without overwriting existing drafts.
- **Planning:** Pace and transport cards sit side by side on desktop and stack on
  mobile. Pace is single-select; transport supports one, several or no selected modes.
  Selected controls add visible preference sentences. Manually editing a controlled
  sentence detaches it and clears the corresponding selection.
- **Polishing:** Compare the original and suggested text; apply, dismiss or undo.
  The offline suggestion only tidies whitespace and line breaks, without a model call.
- **Tasks:** Generation takes about 22 seconds. Navigate elsewhere or reload; the task
  entry remains available. Only one simulated task runs per account. Another generation
  attempt suggests saving a draft. Input edits do not change the submitted snapshot.
- **Previews:** Completed and imported itineraries remain unsaved previews until saved
  or explicitly discarded. Open the recovery disclosure on the planning page. Saving
  puts the itinerary in My trips; another click does not duplicate that saved result.
- **Drafts:** Save multiple briefs, continue editing, update the same draft or save as
  a new draft. The card menu supports rename, copy and delete.
- **Import:** Paste a JSON file or choose `examples/sydney-itinerary.json`. Review the
  result before saving. Historical dates are allowed, with no new-generation date-window
  limit. Invalid dates, impossible activity intervals, duplicate activity identifiers
  and broken transfer endpoints are rejected with field locations. Missing weather,
  images, costs and original input remain missing. Replanning does not turn the old
  itinerary's activities into required visits.
- **Details:** Read daily timelines, free windows, application-provided transfers,
  weather and activity-linked Nearby references. The sidebar groups optional places by
  date and scheduled activity. Use maps, text/JSON export and copy summary. Nearby has
  no bookmark controls or separate collection.
- **Recovery scenarios:** About this prototype exposes the relevant state. While a task
  runs, it also provides explicit simulation actions for failure, clarification and
  immediate completion.

## Nearby interaction

Desktop retains the original two columns. Nearby groups default to expanded, with a
separate disclosure control. The activity's `Nearby · N` pill expands and locates its
sidebar group. Clicking the group title opens the day's timeline and locates the
activity. Both surfaces briefly highlight in the same green. Only explicit clicks and
day filters change the view; hovering and scrolling do not select a group.

All days shows date headings followed by activity groups. A selected day filters the
sidebar to that day's groups. Activities without references have no Nearby entry or
empty group. On screens up to 800px wide, references move into a collapsed section
inside the corresponding activity card, without a time or timeline marker.

Associations use `anchor_activity_id`, with `associated_day` when provided. Nested
activity references inherit their actual parent activity ID and day. No association
is inferred from a place name or prose. Unresolved, missing or ambiguous anchors stay
under **Other nearby references**; date-labelled references follow the day filter and
undated references remain visible. This section stays separate on mobile.

Try `examples/nearby-linking.json` through Import: the first The Rocks visit has two
references; a later visit to the same place has one different reference. Two unlinked
references stay separate even when their prose mentions a scheduled attraction. The
ordinary Sydney example also has a day without any Nearby references.

## Image sources

Destination covers, the home hero and authentication imagery use the existing Unsplash
URLs with illustration fallbacks. Activity and Nearby images reserve the Google Places
Photos surface, with illustration fallbacks and author-attribution space. They do not
substitute Unsplash atmosphere images for photographs of particular places.

No live Google Places Photos calls or API keys are included.

## Simulation boundaries

Profiles, uploads, drafts, previews and task snapshots live under the isolated
`dayloom_prototype_r7` local-storage key. They are not shared with the r5 or r6 prototypes.
Cross-device synchronization, genuine authentication, server workers, paid generation,
live weather/routes and live photo acquisition are not connected. Closed-page task
completion is calculated from its saved clock when the prototype is reopened.

The generated itinerary is an illustrative fixture, not a plan verified for actual
travel. Imported content retains its supplied facts and uncertainty. No production
frontend, backend, evaluation data or V0-V3 entrypoint is modified by this artifact.

## Source and build

- `source/original.css`, `source/refinements.css`: unchanged r5 visual baseline.
- `source/prototype.css`: agreed r6 layout additions.
- `source/nearby.js`, `source/nearby.css`: r7 grouping, explicit navigation and mobile disclosures.
- `source/data.js`, `source/icons.js`: English examples, illustration fallbacks and icons.
- `source/preferences.js`: editable preference ownership.
- `source/state.js`: browser-local accounts, snapshots, drafts and tasks.
- `source/pages.js`, `source/details.js`, `source/actions.js`: page and interaction code.
- `review/`: selected browser screenshots of this revision.

Rebuild the standalone file with the Python standard library:

```sh
python source/build.py --output index.html
```
