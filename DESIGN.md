---
version: alpha
name: "Warehouse Intelligence Twin"
description: "A scene-first warehouse operations console for comparing slotting layouts."
colors:
  background: "#dfe8ea"
  paper: "#f8faf9"
  ink: "#213a45"
  muted: "#617783"
  line: "#cbd7db"
  primary: "#285465"
  accent: "#be792d"
  accent_light: "#f2af4b"
typography:
  display:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
  body:
    fontFamily: "DM Sans, system-ui, sans-serif"
  data:
    fontFamily: "IBM Plex Mono, monospace"
rounded:
  DEFAULT: "0px"
spacing:
  panel-gap: "16px"
  page-gutter: "4vw"
components:
  floor: {}
  rack: {}
  button: {}
  metric: {}
---

# Warehouse Intelligence Twin Design System

## Overview

### Creative North Star

A daylight warehouse control desk: powder-coated steel, pale floor markings, stock labels, and amber safety paint. The floor occupies most of the workspace. A narrow planner rail and compact result strip keep the operating context in view while slots change.

### Product context and register

- **Audience and job:** A warehouse planner or hackathon evaluator compares shelf assignments against original and fast-mover layouts for one replayed order set.
- **Usage scene:** Desktop-first operational review; tablet and phone retain all actions through HTML controls.
- **Locale:** English UI. Data IDs stay as supplied by the API. Numbers use English grouping; unit labels remain explicit.
- **Register:** Working operations tool with a compact product header and dataset status.
- **Signature:** The lit 3D floor, cyan returned route, amber dock, and a timeline synchronized to server metrics.
- **Anti-references:** Black neon command centers and decorative logistics maps would imply telemetry that this synthetic floor does not have.
- **Token ownership:** This file records the system; `frontend/src/style.css` is the runtime source through matching CSS custom properties. Three.js material colors use the same steel/amber roles. The file and CSS must change together.

## Colors

Pale steel-blue `background` frames near-white `paper` panels; `ink` and `muted` separate decision data from support text. `primary` anchors the toolbar and playback strip. Amber `accent` marks dock, changed slots, focused metric, and primary action. Cyan identifies the returned route and selected rack within the scene. Error, offline, and selected states have text labels and borders in addition to color. The current product supports one light theme.

## Typography

Barlow Condensed supplies compressed, legible floor-planning headlines and large metric figures. DM Sans carries explanations, controls, and tables. IBM Plex Mono marks IDs, state labels, and measurements. Headline capitals identify product sections; controls use sentence case. CSS fallbacks preserve layout if external font hosting is unavailable.

## Layout

The 64px toolbar leads into a short workspace title, a three-policy metric strip, then a two-column workspace. The floor receives the larger column and holds its camera controls, 3D canvas, and playback timeline. A 346px planning rail contains selected SKU detail, comparison action, searchable product slots, and order lines. Below 940px the rail follows the floor; below 650px metrics stack and controls remain reachable. The canvas reserves height before loading. The stock list scrolls within its panel, while the document remains the primary page scroll.

## Elevation & Depth

UI surfaces use tonal layers and hairline borders, with almost no shadow. Three.js lighting and shelf shadows create depth within the floor only. The HTML stock list supplies exact labels for each rack.

## Shapes

Zero-radius panels and buttons echo warehouse equipment and labels. The spatial view includes a concrete slab, painted walkable aisle cells, low front curbs, two tall boundary walls, an amber dock, and original rack geometry. Instanced rack posts, beams, shelves, and cartons keep 100 slots responsive. Darker steel marks products in the top quartile of the selected month's pick frequency. Picker geometry is deliberately simple so its aisle path reads first.

## Components

Buttons have visible default, hover, focus, disabled, and busy states. Chosen stock rows use an amber fill and `aria-pressed`; changed rows also have a stronger left rule. The searchable HTML stock list is the canonical accessible control for swaps, and scene clicks call the same action. The selected-location readout shows SKU and product name. The floor has a clear WebGL fallback. Offline mode labels the scene as an unscored preview and offers retry. If the API is unavailable, a validated `/demo.json` export containing real order data can populate the unscored floor. A comparison is cleared immediately after a swap, reset, or new data load; old responses cannot replace newer state.

The three metric cards always stay in fixed order: original, fast-mover baseline, player. Empty cards show an em dash, never an invented measurement. Server-returned values appear after all three requests succeed for the same immutable snapshot. The active card selects which returned assignment and route is shown. The bottom timeline seeks within the returned route time; replay controls pause, restart, and reset without changing comparison results.

Motion communicates route progress. The picker is sampled from each returned cardinal segment at render time, so it never cuts across a rack corner; counters update at a readable rate. Playback runs at a labeled 6× rate. User reduced-motion settings prevent automatic replay and remove decorative CSS transitions. Canvas orbit remains user-controlled.

## Do's and Don'ts

- **Do:** Label synthetic fixtures and warehouse assumptions wherever results appear.
- **Do:** Keep equal order IDs, speed, and server scoring for every comparison policy.
- **Don't:** Show an estimated saving until the API has returned metrics.
- **Don't:** Depend on color or 3D picking alone for an essential action.
