---
version: alpha
name: "Warehouse Intelligence Twin"
description: "A daylight warehouse operations console centered on a playable picking floor."
colors:
  background: "#e8eef1"
  paper: "#f7f9f8"
  ink: "#183440"
  muted: "#607681"
  line: "#c8d5da"
  primary: "#274e5d"
  accent: "#bd741c"
  accent_light: "#f2bd62"
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

A daylight warehouse control desk: powder-coated steel, pale floor markings, stock labels, and amber safety paint. The floor itself is the memorable element. The surrounding interface stays quiet so a planner can change locations and read the result quickly.

### Product context and register

- **Audience and job:** A warehouse planner or hackathon evaluator compares shelf assignments against original and fast-mover layouts for one replayed order set.
- **Usage scene:** Desktop-first operational review; tablet and phone retain all actions through HTML controls.
- **Locale:** English UI. Data IDs stay as supplied by the API. Numbers use English grouping; unit labels remain explicit.
- **Register:** Product tool, with a compact introduction to explain the exercise.
- **Signature:** The lit 3D floor and amber returned route, supported by synchronized route and metric panels.
- **Anti-references:** Black neon command centers and decorative logistics maps would imply telemetry that this synthetic floor does not have.
- **Token ownership:** This file records the system; `frontend/src/style.css` is the runtime source through matching CSS custom properties. Three.js material colors use the same steel/amber roles. The file and CSS must change together.

## Colors

Pale steel-blue `background` frames white-green `paper` panels; `ink` and `muted` separate decision data from support text. `primary` marks the system and playback strip. `accent` is reserved for dock, route, changed slots, focused metric, and primary action. Error, offline, and selected states have text labels and borders in addition to color. The current product supports one light theme.

## Typography

Barlow Condensed supplies compressed, legible floor-planning headlines and large metric figures. DM Sans carries explanations, controls, and tables. IBM Plex Mono marks IDs, state labels, and measurements. Headline capitals identify product sections; controls use sentence case. CSS fallbacks preserve layout if external font hosting is unavailable.

## Layout

At wide widths, the floor gets the larger column and planning controls form a compact side rail. Comparison and inventory span the page below. Under 1050px the planning rail follows the floor; under 700px metrics stack and controls stay reachable. The canvas reserves its height before loading. The floor and inventory lists are independent scroll surfaces; the document remains the primary page scroll.

## Elevation & Depth

UI surfaces use tonal layers and hairline borders, with almost no shadow. Three.js lighting and shelf shadows create depth within the floor only. The HTML slot grid supplies exact labels for each rack.

## Shapes

Zero-radius panels and buttons echo warehouse equipment and labels. Rack posts, flat shelves, and cartons make storage locations recognizable from both camera presets. Darker steel marks products in the top quartile of the selected month's pick frequency. Picker geometry is deliberately simple so its aisle path reads first.

## Components

Buttons have visible default, hover, focus, disabled, and busy states. Chosen slots use an amber fill and `aria-pressed`; changed slots also have a stronger left rule. The HTML slot grid is the canonical accessible control for swaps, and scene clicks call the same action. The floor has a clear WebGL fallback. Offline mode explains that scoring is unavailable and offers retry. A comparison is cleared immediately after a swap, reset, or new data load; old responses cannot replace newer state.

The three metric cards always stay in fixed order: original, fast-mover baseline, player. Empty cards show an em dash, never an invented measurement. Server-returned values appear after all three requests succeed for the same snapshot. The active card selects which returned assignment and route is shown. Replay controls pause, restart, and reset without changing comparison results.

Motion communicates route progress. The picker is sampled from each returned cardinal segment at render time, so it never cuts across a rack corner; counters update at a readable rate. Playback runs at a labeled 6× rate. User reduced-motion settings prevent automatic replay and remove decorative CSS transitions. Canvas orbit remains user-controlled.

## Do's and Don'ts

- **Do:** Label synthetic fixtures and warehouse assumptions wherever results appear.
- **Do:** Keep equal order IDs, speed, and server scoring for every comparison policy.
- **Don't:** Show an estimated saving until the API has returned metrics.
- **Don't:** Depend on color or 3D picking alone for an essential action.
