#!/usr/bin/env python3
"""Re-parse a STEP file and prove each solid is a watertight 2-manifold.

Independent of the generator: it reads the emitted text back, rebuilds the
topology from the entity graph, and checks

  1. no dangling entity references anywhere in the file;
  2. per solid, Euler-Poincare V - E + F = 2 (genus 0, single shell);
  3. every directed edge used exactly once, and every undirected edge used
     exactly twice in opposite directions (watertight and consistently
     oriented);
  4. every face loop is planar and non-degenerate.

Exit status 0 on PASS, 1 on FAIL.
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from typing import Dict, List, Sequence, Tuple

ENTITY = re.compile(r"#(\d+)\s*=\s*(.*?);", re.S)
REF = re.compile(r"#(\d+)")
NAME = re.compile(r"^\(?\s*([A-Z_0-9]+)\s*\(")

PLANARITY_TOL = 1e-6
MIN_EDGE = 1e-9


def parse(path: str) -> Dict[int, str]:
    with open(path, "r", encoding="ascii") as fh:
        text = fh.read()
    body = text[text.index("DATA;") + 5 : text.rindex("ENDSEC;")]
    return {int(m.group(1)): m.group(2).strip() for m in ENTITY.finditer(body)}


def kind(body: str) -> str:
    m = NAME.match(body)
    return m.group(1) if m else ""


def args_of(body: str) -> str:
    return body[body.index("(") + 1 : body.rindex(")")]


def refs(body: str) -> List[int]:
    return [int(x) for x in REF.findall(body)]


def check_dangling(ents: Dict[int, str]) -> List[str]:
    bad = []
    for eid, body in ents.items():
        for r in refs(body):
            if r not in ents:
                bad.append(f"#{eid} references missing #{r}")
    return bad


def point_of(ents: Dict[int, str], vid: int) -> Tuple[float, float, float]:
    pid = refs(ents[vid])[0]
    nums = re.findall(r"-?\d+\.\d*(?:E[+-]?\d+)?|-?\d+\.", ents[pid])
    return tuple(float(n) for n in nums[:3])  # type: ignore[return-value]


def loop_of(ents: Dict[int, str], face_id: int) -> List[Tuple[int, int]]:
    """Ordered (v_start, v_end) pairs of a face's outer bound."""
    bound = refs(ents[face_id])[0]
    eloop = refs(ents[bound])[0]
    pairs: List[Tuple[int, int]] = []
    for oe in refs(ents[eloop]):
        body = ents[oe]
        ec = refs(body)[0]
        sense = body.rstrip(")").rstrip().endswith(".T.")
        v0, v1 = refs(ents[ec])[:2]
        pairs.append((v0, v1) if sense else (v1, v0))
    return pairs


def planar(pts: Sequence[Tuple[float, float, float]]) -> bool:
    if len(pts) < 3:
        return False
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    mag = math.sqrt(nx * nx + ny * ny + nz * nz)
    if mag < MIN_EDGE:
        return False
    nx, ny, nz = nx / mag, ny / mag, nz / mag
    d = nx * pts[0][0] + ny * pts[0][1] + nz * pts[0][2]
    return all(abs(nx * p[0] + ny * p[1] + nz * p[2] - d) < PLANARITY_TOL for p in pts)


def main(path: str) -> int:
    ents = parse(path)
    problems: List[str] = []

    dangling = check_dangling(ents)
    problems.extend(dangling)

    breps = [e for e, b in ents.items() if kind(b) == "MANIFOLD_SOLID_BREP"]
    if not breps:
        problems.append("no MANIFOLD_SOLID_BREP found")

    total_faces = 0
    for brep in breps:
        name = re.match(r"MANIFOLD_SOLID_BREP\('([^']*)'", ents[brep])
        label = name.group(1) if name else f"#{brep}"
        shell = refs(ents[brep])[0]
        faces = refs(ents[shell])
        total_faces += len(faces)

        directed: Counter = Counter()
        verts = set()
        for f in faces:
            pairs = loop_of(ents, f)
            if len(pairs) < 3:
                problems.append(f"{label}: face #{f} has {len(pairs)} edges")
            pts = [point_of(ents, a) for a, _ in pairs]
            if not planar(pts):
                problems.append(f"{label}: face #{f} is non-planar or degenerate")
            for a, b in pairs:
                if a == b:
                    problems.append(f"{label}: face #{f} has a zero-length edge")
                directed[(a, b)] += 1
                verts.add(a)
                verts.add(b)

        for (a, b), c in directed.items():
            if c != 1:
                problems.append(f"{label}: directed edge {a}->{b} used {c}x (want 1)")
            if directed.get((b, a), 0) != 1:
                problems.append(
                    f"{label}: edge {a}-{b} lacks its opposite use (not watertight)"
                )

        v = len(verts)
        e = len(directed) // 2
        fcount = len(faces)
        if v - e + fcount != 2:
            problems.append(
                f"{label}: Euler V-E+F = {v}-{e}+{fcount} = {v - e + fcount} (want 2)"
            )

    print(f"file    : {path}")
    print(f"entities: {len(ents)}")
    print(f"solids  : {len(breps)}")
    print(f"faces   : {total_faces}")
    print(f"dangling: {len(dangling)}")

    if problems:
        print("\nFAIL")
        for p in problems[:40]:
            print(f"  - {p}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        return 1

    print("\nPASS - all solids watertight, 2-manifold, consistently oriented")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "LF19S-102-8A.step"
    sys.exit(main(target))
