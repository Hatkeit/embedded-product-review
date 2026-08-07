# LF19S-102-8A — 3D STEP model

Faceted STEP (AP214) model of the LF19S-102-8A vertical line filter, for
mechanical clearance checks and 3D PCB views.

| File | Purpose |
| --- | --- |
| `LF19S-102-8A.step` | The model. 37 solids, 254 planar faces. |
| `lf19_step_generator.py` | Generator. All dimensions are CLI parameters. |
| `validate_step.py` | Independent re-parse and manifold check. |
| `step_preview_svg.py` | Isometric wireframe preview as a standalone SVG. |
| `lf19_iso.svg` | Rendered preview. |

```sh
python3 lf19_step_generator.py          # writes LF19S-102-8A.step
python3 validate_step.py LF19S-102-8A.step
python3 step_preview_svg.py LF19S-102-8A.step lf19_iso.svg
```

## Coordinate system

Matches the Allegro symbol `LF19S-102-8A.dra`, so the model drops onto the
footprint with no transform:

* origin — centre of the 18.5 × 9.0 pin rectangle
* Z = 0 — mounting plane (PCB top surface), +Z away from the board
* X — the 18.5 mm pin-pitch direction

The symbol's `PLACE_BOUND` is 24 × 13 and its pins sit at (±9.25, ±4.5),
which agrees exactly with the datasheet Fig.1 body envelope and PCB layout.
That agreement is what fixes the origin.

## Dimensions

| Item | Value | Source |
| --- | --- | --- |
| Body | 24.0 (X) × 13.0 (Y) × 23.0 (Z) vertical ring | datasheet Fig.1 / `PLACE_BOUND` |
| Pin grid | 18.5 × 9.0 | datasheet PCB layout / `.dra` pins |
| Lead | Ø0.7 (hole Ø0.8) | datasheet |
| Lead extent | z = −3.4 up into the winding | datasheet protrusion |
| Overall height | 25.0 | body + standoff |
| Structure | 2 windings × 16 sectors + separator + 4 leads = 37 solids | — |

## Assumptions

Three values are not given on the datasheet. Each is a CLI parameter, so a
corrected value is one regeneration away.

1. **Standoff 2.0 mm** (`--standoff`). This is a base-less type with no
   specified seated height. The 15 mm leads are supplied long and cut after
   insertion, so the part is modelled fully seated.
2. **Bore Ø9.2 mm** (`--bore-dia`). The post-winding inner diameter is not
   published; estimated from the 19 Φ core. Does not affect the outer
   envelope.
3. **Winding profile.** Approximated as a 24 × 23 elliptical annulus in 16
   facets per winding. This is the maximum envelope — the real winding's
   rounded bulge is not modelled, so the part can only be smaller than what
   is shown here, never larger.

## Datasheet erratum

The front view of Fig.1 labels the leads `#1 #4 #3 #2`. That order
contradicts the bottom view, the connection diagram, the PCB layout, and the
nets on the existing `.dra` — the leads cross over in that projection. The
model follows the four agreeing sources:

* pins 1, 2 at X = −9.25; pins 3, 4 at X = +9.25
* pins 1, 4 at Y = +4.5; pins 2, 3 at Y = −4.5

## Validation

`validate_step.py` reads the emitted file back and rebuilds the topology from
the entity graph — it shares no geometry code with the generator. It checks:

* no dangling entity references;
* per solid, Euler–Poincaré V − E + F = 2;
* every directed edge used exactly once and every undirected edge used
  exactly twice in opposite directions (watertight, consistently oriented);
* every face loop planar and non-degenerate.

Current status: **PASS** — 37 solids, 254 faces, 0 dangling.

Solids are modelled as independent overlapping bodies (leads pass into the
winding) rather than booleaned into one. That is valid for a STEP shape
representation and keeps every solid a clean convex prism.
