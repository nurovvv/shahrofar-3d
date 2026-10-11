"""Deck edges (render 2): white rounded parapet with a glass balustrade, the lawn / hedge border
inside the outer curve, the diagonal planter strip and the swan-neck lamps along the edge.

    parapet   thick white coping with a rounded outer edge, wrapping down over the slab edge, and a
              frameless glass balustrade with a slim handrail on top of its inner half; along every
              open edge of the +15.0 deck (shop front and land side) and around the +20.5 west wing
    band      grey cobble walkway just inside the parapet; by the pool lawn beds with a low clipped
              hedge on their inner side (the pool part plants its trees right behind them), by the
              playground lawn beds with round shrubs and a tree; full width cobble at the hotel end
    strip     long raised planter on the diagonal between pool and playground: dense hedge, a row
              of round and columnar trees, a long timber bench on the pool side, one crossing in the
              middle and a passage at the back
    lamps     swan-neck lamps every ~11 m along the band, three in the strip leaning over the bench
    west      the +15.0 walkway in front of the raised west wing gets the same cobble, shrub beds and lamps
"""
import math
import random

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, substring, unary_union

from .common import PAVE_T, hedge, lamp, lawn, tree

# parapet section: (offset outwards from the deck outline, height above the deck), from the underside
# tucked behind the shop front band, up the outer face, over the rounded top and down the inner face
PARAPET = [(0.18, -0.80), (0.38, -0.74), (0.46, -0.58), (0.49, -0.30), (0.49, 0.36), (0.47, 0.54), (0.42, 0.67),
           (0.33, 0.77), (0.20, 0.835), (0.04, 0.865), (-0.30, 0.865), (-0.42, 0.85), (-0.48, 0.81), (-0.50, 0.74),
           (-0.50, 0.0)]
TOP = 0.865
INNER_FACE = 'Terracotta'   # the upstand's inner face reads terracotta on the render, like the land side
GLASS_D, GLASS_Z0, GLASS_Z1 = -0.36, 0.84, 1.22   # balustrade on top of the coping's inner half
RAIL_W = 0.06                                     # slim handrail on the glass

WALK = 1.15        # cobble walkway between the parapet and the lawn beds (from the outer line)
BAND = 2.6         # edge band width (ctx['edge_band'])
HEDGE_D = 2.25     # hedge centre line (from the outer line), on the inner side of the lawn beds

# lawn beds along the outer line (arc length s along ctx['outer_line'], measured from its west end)
# kind: 'hedge' = lawn with a clipped hedge and trees (pool side), 'shrubs' = lawn with round shrubs
BEDS = [
    (127.5, 140.5, 'shrubs', [129.8, 133.6, 139.0], [136.2]),
    (162.0, 178.0, 'shrubs', [164.3, 168.4, 172.2, 175.9], []),
    (190.6, 201.6, 'hedge', [], []),          # the pool part has its trees right behind these beds
    (204.0, 211.0, 'hedge', [], []),
]
LAMP_STEP = 11.0
STONE_MATS = (('Cobble', 0.30), ('Bridge', 0.32), ('Kerb', 0.30), ('Sidewalk', 0.08))   # as the playground
JOINT = 'Cobble joint'   # mid-grey joints, as the playground (not the near-black asphalt)
COBBLE = 0.42            # stone size in the band and the strip crossings (fine, as the reference)
COBBLE_WEST = 0.55       # the walk in front of the west wing is seen from further away

STRIP_W = 2.8
BENCH_W = 0.80     # timber bench along the pool side of the strip
PLANTER_H = 0.52
CROSSING = (31.0, 2.4)   # (distance from the outer end, width) of the crossing through the strip
BACK_GAP = 2.4           # passage between the strip and the inner rail at the back


# ----------------------------------------------------------------------------------------------
# sweeps along polylines
# ----------------------------------------------------------------------------------------------

def _lines(g):
    if g.is_empty:
        return []
    if g.geom_type in ('LineString', 'LinearRing'):
        return [LineString(g.coords)]
    if g.geom_type == 'MultiLineString':
        merged = linemerge(g)
        return [LineString(x.coords) for x in getattr(merged, 'geoms', [merged])]
    if hasattr(g, 'geoms'):
        return [l for x in g.geoms for l in _lines(x)]
    return []


def _clean(pts, tol=0.05):
    out = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, out[-1]) > tol:
            out.append(p)
    return out


def miter_normals(P, closed=False):
    """Per-vertex offset directions (right of travel, scaled so offsets stay parallel)."""
    n = len(P)
    seg = []
    for i in range(n if closed else n - 1):
        d = P[(i + 1) % n] - P[i]
        d = d / (np.linalg.norm(d) + 1e-12)
        seg.append(np.array([d[1], -d[0]]))
    N = []
    for i in range(n):
        if closed:
            a, b = seg[i - 1], seg[i]
        else:
            a, b = seg[max(i - 1, 0)], seg[min(i, n - 2)]
        m = a + b
        m = m / (np.linalg.norm(m) + 1e-12)
        N.append(m / max(float(m @ a), 0.5))
    return N


def orient_out(line, region):
    """Point list of `line` running so that `region` (the deck) lies on its LEFT, outside on the right."""
    pts = _clean(list(line.coords))
    if len(pts) < 2:
        return None
    P = np.array(pts, float)
    N = miter_normals(P)
    k = max(range(len(P) - 1), key=lambda i: np.linalg.norm(P[i + 1] - P[i]))
    mid = (P[k] + P[k + 1]) / 2
    if region.contains(Point(*(mid + N[k] * 0.3))):
        pts = pts[::-1]
    return pts


def _newell(pts):
    n = np.zeros(3)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
    return n


def face_toward(mb, pts, want, mat):
    if _newell(pts) @ np.array(want, float) < 0:
        pts = pts[::-1]
    mb.face(pts, mat)


def sweep(mb, pts, z, profile, mat, caps=True, seg_mats=None):
    """Extrude a (d, h) section along an outward-oriented point list (outside on the right);
    seg_mats optionally gives a material per section segment."""
    P = np.array(pts, float)
    N = miter_normals(P)
    rings = [[(float(p[0] + n[0] * d), float(p[1] + n[1] * d), z + h) for d, h in profile] for p, n in zip(P, N)]
    for i in range(len(P) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for j in range(len(profile) - 1):
            mb.face([r0[j], r1[j], r1[j + 1], r0[j + 1]], seg_mats[j] if seg_mats else mat)
    if caps:
        t0 = P[1] - P[0]
        t1 = P[-1] - P[-2]
        face_toward(mb, list(rings[0]), (-t0[0], -t0[1], 0.0), mat)
        face_toward(mb, list(rings[-1]), (t1[0], t1[1], 0.0), mat)


# ----------------------------------------------------------------------------------------------
# parapet + balustrade
# ----------------------------------------------------------------------------------------------

def parapet(mb, pts, z):
    """White rounded coping, glass balustrade and handrail along an outward-oriented run."""
    if len(pts) < 2 or LineString(pts).length < 0.4:
        return
    sweep(mb, pts, z, PARAPET, 'White band', seg_mats=['White band'] * (len(PARAPET) - 2) + [INNER_FACE])
    # coping joints: a fine shadow groove every ~4.5 m on the top
    ln = LineString(pts)
    P = np.array(pts, float)
    N = miter_normals(P)
    k = int(ln.length // 4.5)
    for i in range(1, k + 1):
        s = ln.length * i / (k + 1)
        p = ln.interpolate(s)
        q = ln.interpolate(min(ln.length, s + 0.05))
        r = ln.interpolate(max(0.0, s - 0.05))
        t = np.array([q.x - r.x, q.y - r.y])
        t /= (np.linalg.norm(t) + 1e-12)
        n = np.array([t[1], -t[0]])
        a = np.array([p.x, p.y]) + n * 0.03
        b = np.array([p.x, p.y]) + n * -0.30
        w = t * 0.012
        zz = z + TOP + 0.003
        mb.face([(a[0] - w[0], a[1] - w[1], zz), (a[0] + w[0], a[1] + w[1], zz), (b[0] + w[0], b[1] + w[1], zz),
                 (b[0] - w[0], b[1] - w[1], zz)], 'Metal')
    # glass + handrail
    gl = [(float(p[0] + n[0] * GLASS_D), float(p[1] + n[1] * GLASS_D)) for p, n in zip(P, N)]
    mb.ribbon(gl, z + GLASS_Z0, z + GLASS_Z1, 'Railing glass', double=True)
    zs0 = [z + GLASS_Z1 - 0.01] * len(gl)
    zs1 = [z + GLASS_Z1 + 0.045] * len(gl)
    mb.tube(gl, zs0, zs1, RAIL_W, 'Metal')


def parapet_runs(boundary, region, cut):
    """Outward-oriented point lists along `boundary` minus `cut`."""
    g = boundary.difference(cut) if cut is not None else boundary
    out = []
    for l in _lines(g):
        if l.length < 0.5:
            continue
        pts = orient_out(l, region)
        if pts:
            out.append(pts)
    return out


# ----------------------------------------------------------------------------------------------
# band along the outer line
# ----------------------------------------------------------------------------------------------

def band_region(outer, inside, s0, s1, d0, d1):
    """Part of `inside` between d0 and d1 metres in from the outer line, for arc length s0..s1."""
    sub = substring(outer, max(0.0, s0), min(outer.length, s1))
    if sub.length < 0.1:
        return Polygon()
    ring = sub.buffer(d1, cap_style='flat').difference(sub.buffer(d0, cap_style='flat'))
    return ring.intersection(inside)


def inward_at(outer, s, d):
    """Point d metres in from the outer line at arc length s, and the inward direction (radians)."""
    p = outer.interpolate(s)
    q = outer.interpolate(min(outer.length, s + 0.5))
    r = outer.interpolate(max(0.0, s - 0.5))
    t = np.array([q.x - r.x, q.y - r.y])
    t /= (np.linalg.norm(t) + 1e-12)
    n = np.array([-t[1], t[0]])          # right of travel is inside: inward = (t_y, -t_x)
    n = -n
    return p.x + n[0] * d, p.y + n[1] * d, math.atan2(n[1], n[0])


def offset_line(outer, s0, s1, d):
    pts = [inward_at(outer, s, d)[:2] for s in np.linspace(s0, s1, max(2, int((s1 - s0) / 1.5) + 1))]
    return LineString(pts)


def shrub(mb, x, y, z, r, rnd, mat='Leaves light'):
    mb.blob(x, y, z + r * 0.8, r, r, r * 0.86, mat, subdiv=2, jitter=0.12, rnd=rnd)


def joint_mat():
    """'Cobble joint' (a mid grey a little darker than the stones, as the playground uses) when
    materials.py has it, else the light 'Bridge' grey: never the near-black asphalt."""
    try:
        from ..materials import SPECS
    except Exception:
        return JOINT
    return JOINT if JOINT in SPECS else 'Bridge'


def cobble(mb, zone, z, rnd, size=COBBLE, angle=0.0, joint=0.035, merge=0.10, split=0.27, keep_out=None):
    """Fine grey irregular cobble like the playground's: a slab, a mid-grey joint layer and jittered
    stones (a few long ones over two cells, some split in two) in a few close greys."""
    zone = zone.buffer(0)
    if zone.is_empty:
        return 0
    mb.prism(zone, z, z + PAVE_T, 'Cobble', 'Cobble')
    area = zone.buffer(-0.04, join_style='mitre')
    if keep_out is not None and not keep_out.is_empty:
        area = area.difference(keep_out)
    if area.is_empty or area.area < 0.2:
        return 0
    zj, zs = z + PAVE_T + 0.006, z + PAVE_T + 0.014
    mb.polygon_face(area.simplify(0.05), zj, joint_mat())
    c = area.centroid
    loc = affinity.rotate(area, -angle, origin=c, use_radians=True)
    x0, y0, x1, y1 = loc.bounds
    nx, ny = int((x1 - x0) / size) + 2, int((y1 - y0) / size) + 2
    jit = np.array([[(rnd.uniform(-0.27, 0.27), rnd.uniform(-0.27, 0.27)) for _ in range(ny + 1)] for _ in range(nx + 1)])
    V = lambda i, j: (x0 + (i + jit[i, j, 0]) * size, y0 + (j + jit[i, j, 1]) * size)
    polys = []
    for j in range(ny):
        i = 0
        while i < nx:
            r = rnd.random()
            if r < merge and i + 1 < nx:     # long stone over two cells
                polys.append([V(i, j), V(i + 1, j), V(i + 2, j), V(i + 2, j + 1), V(i + 1, j + 1), V(i, j + 1)])
                i += 2
                continue
            q = [V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)]
            if r < merge + split:            # split into two triangles
                polys += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]] if rnd.random() < 0.5 else [[q[0], q[1], q[3]], [q[1], q[2], q[3]]]
            else:
                polys.append(q)
            i += 1
    stones = shapely.polygons([shapely.linearrings(p) for p in polys])
    stones = shapely.buffer(stones, -joint / 2, join_style='mitre')
    if angle:
        stones = [affinity.rotate(g, angle, origin=c, use_radians=True) for g in stones]
    shapely.prepare(area)
    inside = shapely.contains(area, stones)
    touch = shapely.intersects(area, stones)
    mats = [m for m, _ in STONE_MATS]
    w = np.cumsum([p for _, p in STONE_MATS])
    n = 0
    for st, ins, tch in zip(stones, inside, touch):
        if not tch or st.is_empty:
            continue
        g = st if ins else st.intersection(area)
        if g.is_empty or g.area < 0.03:
            continue
        mat = mats[int(np.searchsorted(w, rnd.random() * w[-1]))]
        for q in getattr(g, 'geoms', [g]):
            if q.geom_type == 'Polygon' and q.area > 0.03:
                mb.polygon_face(q, zs, mat)
                n += 1
    return n


def stone_angle(ctx):
    """The playground lays its cobble square to the planter strip: do the same so they read as one."""
    (ax, ay), (bx, by) = ctx['strip_line'].coords[0], ctx['strip_line'].coords[-1]
    return math.atan2(by - ay, bx - ax)


def build_band(mb, ctx, rnd):
    z = ctx['z']
    zp = z + PAVE_T
    outer = ctx['outer_line']
    band = ctx['edge_band']
    # keep the beds clear of the diagonal planter where it runs into the band
    (ax, ay), (bx, by) = ctx['strip_line'].coords[0], ctx['strip_line'].coords[-1]
    strip_zone = LineString([(ax + (ax - bx), ay + (ay - by)), (bx, by)]).buffer(STRIP_W / 2 + 0.7)
    beds, bed_polys = [], []
    for s0, s1, kind, shrubs, trees in BEDS:
        d0 = WALK if kind == 'hedge' else WALK - 0.2
        bed = band_region(outer, band, s0, s1, d0, BAND + 0.5).intersection(band).difference(strip_zone)
        bed = bed.buffer(-0.5, join_style='round').buffer(0.5, join_style='round')
        if bed.is_empty or bed.area < 2.0:
            continue
        beds.append((s0, s1, kind))
        bed_polys.append(bed)
        lawn(mb, bed, zp, kerb=0.13)
        if kind == 'hedge':
            hl = offset_line(outer, s0 + 0.55, s1 - 0.55, HEDGE_D)
            hedge(mb, hl.intersection(band.buffer(-0.05)), zp + 0.11, h=0.66, w=0.56)
        for s in shrubs:
            x, y, _ = inward_at(outer, s, 1.85 + rnd.uniform(-0.1, 0.1))
            if not bed.contains(Point(x, y)):
                continue
            shrub(mb, x, y, zp + 0.09, rnd.uniform(0.7, 0.85), rnd, mat=rnd.choice(['Leaves light', 'Leaves light', 'Leaves']))
        for s in trees:
            x, y, _ = inward_at(outer, s, 1.85)
            if not bed.contains(Point(x, y)):
                continue
            tree(mb, x, y, zp + 0.11, h=rnd.uniform(4.8, 5.4), r=rnd.uniform(1.45, 1.7), rnd=rnd)
    # grey cobble everywhere else in the band (the parapet covers its outer half metre)
    keep = outer.buffer(0.45).union(unary_union(bed_polys).buffer(0.02) if bed_polys else Polygon())
    n = cobble(mb, band, z, rnd, size=COBBLE, angle=stone_angle(ctx), keep_out=keep)
    return beds, n


def lamps_along(mb, ctx, beds, strip_poly):
    z = ctx['z'] + PAVE_T
    outer = ctx['outer_line']
    band = ctx['edge_band']
    # east band: s from the split (x = 21.5) to the hotel end
    s_start = outer.project(Point(band.bounds[0] + 0.5, band.bounds[3] - 0.5))
    s = s_start + 3.0
    n = 0
    while s < outer.length - 2.0:
        for a, b_, kind in beds:          # lamps stand in the cobble beside a shrub bed, in the lawn of a hedge bed
            if kind == 'shrubs' and a - 0.6 < s < b_ + 0.6:
                s = a - 0.9 if s - a < b_ - s else b_ + 0.9
        in_bed = any(a - 0.3 < s < b_ + 0.3 for a, b_, _ in beds)
        d = 1.55 if in_bed else 2.1
        x, y, ang = inward_at(outer, s, d)
        if strip_poly.buffer(1.2).contains(Point(x, y)):
            s += 2.5
            continue
        if band.contains(Point(x, y)):
            lamp(mb, x, y, z + (0.11 if in_bed else 0.0), rot=ang)
            n += 1
        s += LAMP_STEP
    return s_start, n


def west_walk(mb, ctx, s_end, rnd):
    """+15.0 walkway between the shop front parapet and the raised west wing: cobble and lamps."""
    z = ctx['z']
    towers = unary_union(list(ctx['towers'].values())).buffer(1.0)
    walk = ctx['podium'].difference(ctx['west_wing']).difference(ctx['deck'].buffer(0.02)).difference(towers)
    parts = [g for g in getattr(walk, 'geoms', [walk]) if g.area > 8.0]
    outer = ctx['outer_line']
    n = 0
    zone = unary_union(parts)
    # lawn beds with round shrubs against the parapet, as along the playground, with gaps to walk out to it
    beds = []
    for s0 in np.arange(14.0, s_end - 14.0, 21.0):
        bed = band_region(outer, zone, s0, s0 + 11.0, 0.95, 2.45).intersection(zone)
        bed = bed.buffer(-0.5, join_style='round').buffer(0.5, join_style='round')
        if bed.area < 4.0:
            continue
        beds.append(bed)
        lawn(mb, bed, z + PAVE_T, kerb=0.13)
        for f in (0.2, 0.5, 0.8):
            x, y, _ = inward_at(outer, s0 + 11.0 * f + rnd.uniform(-0.6, 0.6), 1.7)
            if bed.contains(Point(x, y)):
                shrub(mb, x, y, z + PAVE_T + 0.09, rnd.uniform(0.6, 0.78), rnd, mat=rnd.choice(['Leaves light', 'Leaves']))
    keep = outer.buffer(0.45).union(unary_union(beds).buffer(0.02) if beds else Polygon())
    for g in parts:
        n += cobble(mb, g, z, rnd, size=COBBLE_WEST, angle=0.0, keep_out=keep)
    s = 7.0
    while s < s_end - 4.0:
        x, y, ang = inward_at(outer, s, 2.9)
        if any(g.buffer(-0.3).contains(Point(x, y)) for g in parts):
            lamp(mb, x, y, z + PAVE_T, rot=ang + math.pi)
        s += 14.0
    return n


# ----------------------------------------------------------------------------------------------
# diagonal planter strip
# ----------------------------------------------------------------------------------------------

class Frame:
    def __init__(self, o, u, v):
        self.o, self.u, self.v = np.array(o, float), np.array(u, float), np.array(v, float)

    def w(self, t, s):
        p = self.o + self.u * t + self.v * s
        return float(p[0]), float(p[1])

    def rect(self, t0, s0, t1, s1):
        return Polygon([self.w(t0, s0), self.w(t1, s0), self.w(t1, s1), self.w(t0, s1)])

    @property
    def ang(self):
        return math.atan2(self.u[1], self.u[0])


def build_strip(mb, ctx, rnd):
    z = ctx['z']
    zp = z + PAVE_T
    line = ctx['strip_line']
    a, b = np.array(line.coords[0]), np.array(line.coords[-1])
    if ctx['outer_line'].distance(Point(*a)) > ctx['outer_line'].distance(Point(*b)):
        a, b = b, a                       # a = outer end
    u = (b - a) / np.linalg.norm(b - a)
    v = np.array([-u[1], u[0]])
    mid = (a + b) / 2
    if ctx['play'].distance(Point(*(mid + v * 3.0))) < ctx['pool'].distance(Point(*(mid + v * 3.0))):
        v = -v                            # v points to the pool side
    F = Frame(a, u, v)
    W2 = STRIP_W / 2
    # the planter reaches into the edge band up to the cobble walkway, and stops short of the inner rail
    room = ctx['deck'].difference(ctx['outer_line'].buffer(WALK + 0.05))
    full = F.rect(-6.0, -W2, np.linalg.norm(b - a) + 6.0, W2).intersection(room)
    ts = [float((np.array(c) - a) @ u) for c in full.exterior.coords]
    t_out, t_in = min(ts), max(ts)
    t_back = t_in - BACK_GAP
    c0 = t_out + CROSSING[0]
    pieces = [(t_out, c0 - CROSSING[1] / 2), (c0 + CROSSING[1] / 2, t_back)]
    # crossing and back passage: cobble like the playground, so the path reads through the planting
    for t0, t1 in [(c0 - CROSSING[1] / 2, c0 + CROSSING[1] / 2), (t_back, t_in + 0.5)]:
        g = F.rect(t0, -W2, t1, W2).intersection(ctx['deck'])
        cobble(mb, g, z, rnd, size=COBBLE, angle=F.ang)
    # across the strip (v towards the pool): planter on the play side, timber bench on the pool side
    s_p0, s_p1 = -W2, W2 - BENCH_W - 0.04
    s_b0, s_b1 = W2 - BENCH_W, W2
    n_tree = 0
    kinds = ['round', 'cone', 'round', 'round', 'cone', 'round', 'cone', 'round', 'round']
    for t0, t1 in pieces:
        if t1 - t0 < 1.5:
            continue
        foot = F.rect(t0, -W2, t1, W2).intersection(room)
        mb.prism(foot.difference(ctx['edge_band']), z, zp, 'Cobble', 'Cobble')   # the band has its own slab
        # raised planter: light concrete walls ~0.5 m, lawn / soil inside
        pl = F.rect(t0, s_p0, t1, s_p1).intersection(room)
        pl = pl.buffer(-0.1, join_style='round').buffer(0.1, join_style='round')
        inner = pl.buffer(-0.15, join_style='mitre')
        mb.prism(pl.difference(inner), zp, zp + PLANTER_H, 'Planter', 'Planter')
        hz = zp + PLANTER_H - 0.08
        mb.polygon_face(inner, hz, 'Lawn')
        # dense clipped hedge along the play side, lumpy shrubs along the bench side
        hd = F.rect(t0 + 0.3, s_p0 + 0.2, t1 - 0.3, -0.12).intersection(inner.buffer(-0.02))
        hedge(mb, hd, hz, h=1.05, w=0.9)
        # timber bench: concrete plinth set back under two long timber boards with a shadow gap
        bl = F.rect(t0 + 0.05, s_b0 + 0.06, t1 - 0.05, s_b1 - 0.1).intersection(room)
        if not bl.is_empty:
            mb.prism(bl, zp, zp + 0.38, 'Planter', None)     # its top is hidden under the boards
            half = (s_b0 + s_b1) / 2
            for q0, q1 in [(s_b0 - 0.02, half - 0.02), (half + 0.02, s_b1)]:
                bd = F.rect(t0, q0, t1, q1).intersection(room)
                mb.prism(bd, zp + 0.38, zp + 0.46, 'Wood', 'Wood', 'Wood')
        # row of trees in the planter, shrubs filling the gaps on the bench side, a lamp in every other gap
        L = t1 - t0
        k = max(1, int(round(L / 5.6)))
        tts = [t0 + L * (i + 0.5) / k + rnd.uniform(-0.4, 0.4) for i in range(k)]
        for t in tts:
            kind = kinds[n_tree % len(kinds)]
            n_tree += 1
            x, y = F.w(t, -0.3)
            if kind == 'cone':
                tree(mb, x, y, hz, h=rnd.uniform(5.4, 6.2), r=rnd.uniform(1.0, 1.12), leaf='Leaves light', rnd=rnd, kind='cone')
            else:
                tree(mb, x, y, hz, h=rnd.uniform(4.8, 5.6), r=rnd.uniform(1.3, 1.5), rnd=rnd,
                     leaf='Leaves' if n_tree % 3 else 'Leaves light')
        lamps = [(tts[i] + tts[i + 1]) / 2 for i in range(0, k - 1, 2)]
        for t in lamps:
            x, y = F.w(t, s_p1 - 0.3)
            lamp(mb, x, y, hz, rot=math.atan2(v[1], v[0]))
        tb = t0 + 0.9
        while tb < t1 - 0.8:
            if all(abs(tb - t) > 0.9 for t in tts) and all(abs(tb - t) > 0.7 for t in lamps):
                x, y = F.w(tb, s_p1 - 0.5 + rnd.uniform(-0.08, 0.08))
                shrub(mb, x, y, hz, rnd.uniform(0.42, 0.55), rnd, mat=rnd.choice(['Shrub', 'Leaves light', 'Leaves']))
            tb += rnd.uniform(1.1, 1.5)
    return F.rect(t_out, -W2, t_in, W2), n_tree


# ----------------------------------------------------------------------------------------------

def build(mb, ctx):
    rnd = random.Random(7_150)
    z, zw = ctx['z'], ctx['west']['z']
    pod, ww = ctx['podium'], ctx['west_wing']
    towers = unary_union(list(ctx['towers'].values()))
    # +15.0: every open edge of the podium deck (shop front, land side), not where the west wing stands
    runs = parapet_runs(pod.exterior, pod, ww.buffer(0.3).union(towers.buffer(0.15)))
    # +20.5: round the west wing roof
    runs_w = parapet_runs(ww.exterior, ww, towers.buffer(0.15))
    for pts in runs:
        parapet(mb, pts, z)
    for pts in runs_w:
        parapet(mb, pts, zw)
    beds, n_band = build_band(mb, ctx, rnd)
    strip_poly, n_trees = build_strip(mb, ctx, rnd)
    s_start, n_lamps = lamps_along(mb, ctx, beds, strip_poly)
    n_west = west_walk(mb, ctx, s_start, rnd)
    L = sum(LineString(p).length for p in runs + runs_w)
    print(f'[deck] edge: parapet {L:.0f} m in {len(runs) + len(runs_w)} runs, {len(beds)} lawn beds, '
          f'{n_band + n_west} cobbles, strip {n_trees} trees, {n_lamps} lamps along the band')
