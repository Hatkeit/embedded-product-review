#!/usr/bin/env python3
"""STEP (AP214) generator for the LF19S-102-8A vertical line filter.

Emits a faceted, watertight, 2-manifold B-rep: one MANIFOLD_SOLID_BREP per
solid, every face planar. 37 solids total:

    32  winding sectors   (2 windings x 16 angular sectors, elliptical annulus)
     1  centre separator  (insulating barrier between the two windings)
     4  leads             (through-hole pins)

Coordinate system matches the Allegro symbol LF19S-102-8A.dra:
  * origin  = centre of the 18.5 x 9.0 pin rectangle
  * Z = 0   = mounting plane (PCB top surface); +Z is up, away from the board
  * X       = the 18.5 mm pin pitch direction

Run with no arguments to write LF19S-102-8A.step next to this script.
"""

from __future__ import annotations

import argparse
import math
import os
from typing import Dict, List, Sequence, Tuple

Vec = Tuple[float, float, float]

# --------------------------------------------------------------------------
# Parameters. Every dimension below is either taken from the datasheet Fig.1
# or cross-checked against the Allegro symbol; ASSUMED entries are noted.
# --------------------------------------------------------------------------

DEFAULTS = dict(
    body_x=24.0,        # datasheet: max width across the ring
    body_y=13.0,        # datasheet: max depth (PLACE_BOUND 24 x 13)
    body_z=23.0,        # datasheet: ring height
    standoff=2.0,       # ASSUMED: no seated height is specified for this
                        #          base-less type; leads are supplied long
                        #          and cut after insertion.
    bore_dia=9.2,       # ASSUMED: wound inner diameter, estimated from the
                        #          19 mm core. Does not affect the envelope.
    pin_pitch_x=18.5,   # datasheet PCB layout, = Allegro pins at x = +-9.25
    pin_pitch_y=9.0,    # datasheet PCB layout, = Allegro pins at y = +-4.5
    lead_dia=0.7,       # datasheet lead diameter (hole 0.8)
    lead_bottom=-3.4,   # datasheet: protrusion below the mounting plane
    lead_top=8.0,       # lead terminates inside the winding
    sectors=16,         # angular facets per winding
    winding_gap_deg=4.0,  # angular gap at top and bottom for the separator
    separator_x=1.0,    # separator plate thickness
    lead_facets=12,     # polygonal approximation of the round lead
)


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------


def newell_normal(poly: Sequence[Vec]) -> Vec:
    """Newell's method - robust polygon normal, works for non-convex loops."""
    nx = ny = nz = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0, z0 = poly[i]
        x1, y1, z1 = poly[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return (nx, ny, nz)


def normalize(v: Vec) -> Vec:
    m = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if m == 0.0:
        raise ValueError("degenerate normal")
    return (v[0] / m, v[1] / m, v[2] / m)


def perpendicular(n: Vec) -> Vec:
    """Any unit vector perpendicular to n, for the PLANE ref_direction."""
    a = (0.0, 0.0, 1.0) if abs(n[0]) > 0.5 or abs(n[1]) > 0.5 else (1.0, 0.0, 0.0)
    c = (
        n[1] * a[2] - n[2] * a[1],
        n[2] * a[0] - n[0] * a[2],
        n[0] * a[1] - n[1] * a[0],
    )
    return normalize(c)


def signed_volume(faces: Sequence[Sequence[Vec]]) -> float:
    """Divergence-theorem volume; positive when all normals point outward."""
    total = 0.0
    for f in faces:
        p0 = f[0]
        for i in range(1, len(f) - 1):
            p1, p2 = f[i], f[i + 1]
            a = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            b = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            cx = a[1] * b[2] - a[2] * b[1]
            cy = a[2] * b[0] - a[0] * b[2]
            cz = a[0] * b[1] - a[1] * b[0]
            total += p0[0] * cx + p0[1] * cy + p0[2] * cz
    return total / 6.0


def prism(base: Sequence[Vec], extrude: Vec) -> List[List[Vec]]:
    """Extrude a planar polygon into a closed prism with outward normals.

    Returns n+2 faces (bottom cap, top cap, n sides). Orientation is fixed up
    afterwards from the signed volume, so the caller need not care which way
    round the base polygon was written.
    """
    n = len(base)
    top = [(p[0] + extrude[0], p[1] + extrude[1], p[2] + extrude[2]) for p in base]

    # The caps must run opposite to the side walls that share their edges,
    # so the bottom loop is reversed and the top loop keeps the base order.
    faces: List[List[Vec]] = []
    faces.append(list(reversed(base)))       # bottom cap
    faces.append(list(top))                  # top cap
    for i in range(n):
        j = (i + 1) % n
        faces.append([base[i], base[j], top[j], top[i]])

    if signed_volume(faces) < 0.0:
        faces = [list(reversed(f)) for f in faces]
    return faces


# --------------------------------------------------------------------------
# The part
# --------------------------------------------------------------------------


def build_solids(p: Dict[str, float]) -> List[Tuple[str, List[List[Vec]]]]:
    solids: List[Tuple[str, List[List[Vec]]]] = []

    z0 = p["standoff"]                 # bottom of the ring
    z1 = z0 + p["body_z"]              # top of the ring
    zc = 0.5 * (z0 + z1)               # ring centre height
    a = 0.5 * p["body_x"]              # outer semi-axis, X
    b = 0.5 * p["body_z"]              # outer semi-axis, Z
    rb = 0.5 * p["bore_dia"]           # bore radius
    y0 = -0.5 * p["body_y"]
    depth = (0.0, p["body_y"], 0.0)

    def outer(theta: float) -> Tuple[float, float]:
        return a * math.cos(theta), zc + b * math.sin(theta)

    def inner(theta: float) -> Tuple[float, float]:
        return rb * math.cos(theta), zc + rb * math.sin(theta)

    # Two half-ring windings, separated by a gap at top and bottom.
    gap = math.radians(p["winding_gap_deg"])
    nsec = int(p["sectors"])
    span = math.pi - gap
    for w, start in enumerate((-0.5 * span, math.pi - 0.5 * span)):
        for i in range(nsec):
            t0 = start + span * i / nsec
            t1 = start + span * (i + 1) / nsec
            xo0, zo0 = outer(t0)
            xo1, zo1 = outer(t1)
            xi1, zi1 = inner(t1)
            xi0, zi0 = inner(t0)
            base = [
                (xo0, y0, zo0),
                (xo1, y0, zo1),
                (xi1, y0, zi1),
                (xi0, y0, zi0),
            ]
            solids.append((f"winding{w + 1}_sector{i + 1:02d}", prism(base, depth)))

    # Centre separator: thin plate in the YZ plane, filling the winding gap.
    sx = 0.5 * p["separator_x"]
    solids.append(
        (
            "separator",
            prism(
                [(-sx, y0, z0), (sx, y0, z0), (sx, y0, z1), (-sx, y0, z1)],
                depth,
            ),
        )
    )

    # Four leads.
    r = 0.5 * p["lead_dia"]
    nf = int(p["lead_facets"])
    height = (0.0, 0.0, p["lead_top"] - p["lead_bottom"])
    px = 0.5 * p["pin_pitch_x"]
    py = 0.5 * p["pin_pitch_y"]
    # Pin numbering follows the bottom view / connection diagram / .dra nets,
    # not the front view of Fig.1 (whose lead labels are transposed).
    pins = [(-px, py), (-px, -py), (px, -py), (px, py)]
    for idx, (cx, cy) in enumerate(pins, start=1):
        base = [
            (
                cx + r * math.cos(2.0 * math.pi * k / nf),
                cy + r * math.sin(2.0 * math.pi * k / nf),
                p["lead_bottom"],
            )
            for k in range(nf)
        ]
        solids.append((f"lead{idx}", prism(base, height)))

    return solids


# --------------------------------------------------------------------------
# STEP writer
# --------------------------------------------------------------------------


class StepWriter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.lines: List[str] = []
        self.next_id = 1
        self._points: Dict[Tuple[int, int, int], int] = {}
        self._verts: Dict[int, int] = {}
        self._dirs: Dict[Tuple[int, int, int], int] = {}
        self._edges: Dict[Tuple[int, int], int] = {}

    # -- primitives --------------------------------------------------------

    def _emit(self, body: str) -> int:
        eid = self.next_id
        self.next_id += 1
        self.lines.append(f"#{eid}={body};")
        return eid

    @staticmethod
    def _r(v: float) -> str:
        v = round(v + 0.0, 9)
        if v == 0.0:
            v = 0.0
        s = repr(v)
        if "e" in s or "E" in s:
            return s.upper().replace("E", "E")
        return s if "." in s else s + "."

    @staticmethod
    def _key(v: Vec) -> Tuple[int, int, int]:
        return tuple(int(round(c * 1e6)) for c in v)  # type: ignore[return-value]

    def point(self, v: Vec) -> int:
        k = self._key(v)
        if k not in self._points:
            c = ",".join(self._r(x) for x in v)
            self._points[k] = self._emit(f"CARTESIAN_POINT('',({c}))")
        return self._points[k]

    def vertex(self, v: Vec) -> int:
        pid = self.point(v)
        if pid not in self._verts:
            self._verts[pid] = self._emit(f"VERTEX_POINT('',#{pid})")
        return self._verts[pid]

    def direction(self, v: Vec) -> int:
        k = self._key(v)
        if k not in self._dirs:
            c = ",".join(self._r(x) for x in v)
            self._dirs[k] = self._emit(f"DIRECTION('',({c}))")
        return self._dirs[k]

    def edge(self, v0: Vec, v1: Vec) -> Tuple[int, bool]:
        """Shared EDGE_CURVE for the unordered vertex pair, plus its sense."""
        a, b = self.vertex(v0), self.vertex(v1)
        forward = a <= b
        key = (a, b) if forward else (b, a)
        if key not in self._edges:
            p0 = self.point(v0 if forward else v1)
            p1 = self.point(v1 if forward else v0)
            # LINE needs a direction vector between the two vertices.
            d = tuple((y - x) for x, y in zip(v0, v1)) if forward else tuple(
                (x - y) for x, y in zip(v0, v1)
            )
            did = self.direction(normalize(d))  # type: ignore[arg-type]
            vec = self._emit(f"VECTOR('',#{did},1.)")
            line = self._emit(f"LINE('',#{p0},#{vec})")
            self._edges[key] = self._emit(
                f"EDGE_CURVE('',#{key[0]},#{key[1]},#{line},.T.)"
            )
            _ = p1
        return self._edges[key], forward

    def face(self, loop: Sequence[Vec]) -> int:
        oriented: List[str] = []
        n = len(loop)
        for i in range(n):
            eid, forward = self.edge(loop[i], loop[(i + 1) % n])
            sense = "T" if forward else "F"
            oid = self._emit(f"ORIENTED_EDGE(*,*,#{eid},.{sense}.)")
            oriented.append(f"#{oid}")
        eloop = self._emit(f"EDGE_LOOP('',({','.join(oriented)}))")
        bound = self._emit(f"FACE_OUTER_BOUND('',#{eloop},.T.)")

        nrm = normalize(newell_normal(loop))
        ref = perpendicular(nrm)
        org = self.point(loop[0])
        ax = self.direction(nrm)
        rd = self.direction(ref)
        place = self._emit(f"AXIS2_PLACEMENT_3D('',#{org},#{ax},#{rd})")
        plane = self._emit(f"PLANE('',#{place})")
        return self._emit(f"ADVANCED_FACE('',(#{bound}),#{plane},.T.)")

    def solid(self, name: str, faces: Sequence[Sequence[Vec]]) -> int:
        fids = [f"#{self.face(f)}" for f in faces]
        shell = self._emit(f"CLOSED_SHELL('',({','.join(fids)}))")
        return self._emit(f"MANIFOLD_SOLID_BREP('{name}',#{shell})")

    # -- document ----------------------------------------------------------

    def render(self, solids: Sequence[Tuple[str, List[List[Vec]]]]) -> str:
        origin = self.point((0.0, 0.0, 0.0))
        zdir = self.direction((0.0, 0.0, 1.0))
        xdir = self.direction((1.0, 0.0, 0.0))
        root = self._emit(f"AXIS2_PLACEMENT_3D('',#{origin},#{zdir},#{xdir})")

        breps = [f"#{self.solid(n, f)}" for n, f in solids]

        ctx = self._emit("APPLICATION_CONTEXT('automotive design')")
        self._emit(
            "APPLICATION_PROTOCOL_DEFINITION('international standard',"
            f"'automotive_design',2000,#{ctx})"
        )
        pctx = self._emit(f"PRODUCT_CONTEXT('',#{ctx},'mechanical')")
        prod = self._emit(f"PRODUCT('{self.name}','{self.name}','',(#{pctx}))")
        pdf = self._emit(f"PRODUCT_DEFINITION_FORMATION('','',#{prod})")
        pdc = self._emit(f"PRODUCT_DEFINITION_CONTEXT('part definition',#{ctx},'design')")
        pd = self._emit(f"PRODUCT_DEFINITION('','',#{pdf},#{pdc})")
        pds = self._emit(f"PRODUCT_DEFINITION_SHAPE('','',#{pd})")

        lu = self._emit("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.))")
        au = self._emit("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
        su = self._emit("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT())")
        unc = self._emit(
            f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#{lu},"
            "'distance_accuracy_value','')"
        )
        gctx = self._emit(
            f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)"
            f"GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{unc}))"
            f"GLOBAL_UNIT_ASSIGNED_CONTEXT((#{lu},#{au},#{su}))"
            f"REPRESENTATION_CONTEXT('',''))"
        )
        absr = self._emit(
            "ADVANCED_BREP_SHAPE_REPRESENTATION('"
            f"{self.name}',(#{root},{','.join(breps)}),#{gctx})"
        )
        self._emit(f"SHAPE_DEFINITION_REPRESENTATION(#{pds},#{absr})")

        head = "\n".join(
            [
                "ISO-10303-21;",
                "HEADER;",
                f"FILE_DESCRIPTION(('{self.name} line filter, faceted B-rep'),'2;1');",
                f"FILE_NAME('{self.name}.step','',(''),(''),"
                "'lf19_step_generator.py','','');",
                "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
                "ENDSEC;",
                "DATA;",
            ]
        )
        tail = "\n".join(["ENDSEC;", "END-ISO-10303-21;", ""])
        return head + "\n" + "\n".join(self.lines) + "\n" + tail


# --------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    for key, val in DEFAULTS.items():
        ap.add_argument(f"--{key.replace('_', '-')}", type=float, default=val)
    ap.add_argument(
        "-o",
        "--output",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "LF19S-102-8A.step"),
    )
    args = ap.parse_args()
    params = {k: getattr(args, k) for k in DEFAULTS}

    solids = build_solids(params)
    writer = StepWriter("LF19S-102-8A")
    text = writer.render(solids)

    with open(args.output, "w", encoding="ascii", newline="\n") as fh:
        fh.write(text)

    pts = [v for _, faces in solids for f in faces for v in f]
    ext = [
        (min(v[i] for v in pts), max(v[i] for v in pts)) for i in range(3)
    ]
    print(f"wrote {args.output}")
    print(f"  solids : {len(solids)}")
    print(f"  faces  : {sum(len(f) for _, f in solids)}")
    for axis, (lo, hi) in zip("XYZ", ext):
        print(f"  {axis}      : {lo:8.3f} .. {hi:8.3f}   ({hi - lo:6.3f})")


if __name__ == "__main__":
    main()
