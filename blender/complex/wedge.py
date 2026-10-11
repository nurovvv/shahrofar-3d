"""The hotel's terrace wing (block A), after the aerial render (render 1).

A two-storey wing in front of the hotel whose roof is a terrace at podium.WEDGE_TOP (+10.2, the hotel's
first floor above the lobby, so the terrace meets the hotel at a floor slab). Plan: a long straight west
side running diagonally away from the hotel's south-west fin, a large round tip (r ~7 m) at the south-east
end and an east side along the inner east road (clear of it) that runs up past the hotel's east end to the
podium. Section, with d = metres out from the facade line (the wing outline) and z above the street (same
language as the podium's shop front, complex/facade.py):

    0.1 - 6.1    ground floor: dark shop glazing with dark frames (sill, transom, mullions), set back
                 under the overhang by a set-back that runs smoothly from 5.2 m (west) to 2.6 m (east);
                 the hotel entrance on the drop-off lane, slim round white columns on the outline, a white
                 soffit with downlights
    6.1 - 6.8    thick white rounded band, 0.8 m proud (a 2 cm shadow reveal under the soffit)
    6.8 - 9.46   perforated copper screen folded as a sawtooth (1.5 m panels, 0.04 - 0.5 m proud), the
                 bottom edge cut up towards the folds so the ridges hang down as tips over the white band,
                 dark joints in the folds, dark wall behind; UVs as the podium's panels (joint rows, dots)
    9.4 - 11.07  the podium deck's soft white rounded coping (light inner face) with a dark tinted glass
                 balustrade and slim handrail
    terrace      grey cobble border along the parapet and wider along the hotel, warm tan stone slabs with
                 joints in the middle edged by a light stone kerb, three low multi-stem trees in round
                 planters with timber seat rings and mixed shrubs, swan-neck lamps in the border, a white
                 sill where the paving meets the hotel, a few people (TERRACE_PEOPLE, for site.py)
    street       a lawn bed with clipped round shrubs, a big tree and a small one on the west side, a bed
                 with shrubs at the tip, an asphalt drop-off lane running in under the west overhang

build_wedge(mats, col) is called from podium.hotel_wedge. Deterministic (seeded).
"""
import math
import random

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .geom import MeshBuilder, make_object

# ----------------------------------------------------------------------------------------------
# plan (site metres, x east / y north), measured on render 1
# ----------------------------------------------------------------------------------------------

# outer face of the white coping, back-projected with the render-1 camera at its top (z ~11.07), two points
# per straight side. The west side is pivoted about its lower point to meet the hotel's south-west fin; the
# east side is pivoted so the wing stays clear of the inner east road (site.ROADS[4]) while keeping a strip
# beside the hotel's east end
COPING_W = ((33.62, 185.91), (48.22, 165.66))     # west side, from the hotel's south-west fin
COPING_E = ((61.2, 169.3), (71.5, 204.7))         # east side, along the inner east road
TIP_R = 7.6                                       # coping radius at the tip
COPING_OUT = 0.47                                 # coping face beyond the facade line (edge.PARAPET)
GLASS_D = -0.56                                   # balustrade glass, just inside the coping's inner face (-0.50)
NORTH_Y = 209.6                                   # the east side runs up to the podium's corner
CORNER_R = 1.4                                    # rounded north-east corner

# section
GF_SET = (5.2, 3.6, 2.6)  # ground floor glazing set back under the overhang: west side, tip, east side + north
SOFFIT = 6.1              # underside of the overhang (the podium's ground floor is 6.0 tall)
BAND_TOP = 6.8            # top of the white rounded band
CU_VALLEY, CU_RIDGE = 0.04, 0.5
CU_TIP = 0.28
CU_PANEL = 1.5
CU_V = 11.6 - (BAND_TOP + 0.35)   # copper UV v = z + CU_V: materials.panel_joints' rows (v 11.6 / 13.8) inset
STREET = 0.1              # plaza level
GF_TRANSOM = 4.5

# white rounded band (d, z), counter-clockwise: underside outwards, up the nose, back over the top. Its flat
# underside sits 2 cm below the soffit (a shadow reveal, no coplanar faces)
BAND = [(-0.05, SOFFIT - 0.02), (0.50, SOFFIT - 0.02), (0.65, SOFFIT + 0.01), (0.74, SOFFIT + 0.10),
        (0.79, SOFFIT + 0.24), (0.79, BAND_TOP - 0.22), (0.74, BAND_TOP - 0.09), (0.65, BAND_TOP - 0.02),
        (0.50, BAND_TOP), (-0.05, BAND_TOP)]

# terrace
EDGE_W = (2.6, 2.0, 1.65)  # cobble border from the facade line (the parapet covers its outer 0.5 m): west, tip, east
HOTEL_W = (3.3, 2.2)       # cobble along the hotel: in front of its glass front / along its east end
HOTEL_SPLIT_X = 51.0
HOTEL_SILL = 0.27          # white sill along the hotel (over the hotel's floor band, 0.25 proud of its glass)
COBBLE = 0.53
SLAB = (0.9, 0.9)          # tan stone slabs, laid square to the west side
SLAB_JOINT = 0.018
# (x, y, height, crown radius): low multi-stem trees, two as on render 1
TREES = [(58.2, 179.4, 4.3, 1.9), (52.0, 175.0, 3.9, 1.75), (46.4, 177.8, 3.5, 1.6)]
PLANTER_R = 1.35
LAMPS_S = (6.0, 20.0, 44.0)    # lamps in the border, metres along the exposed outline from the fin
TERRACE_PEOPLE = []            # (x, y, z, clothes) filled by build_wedge, read by site.street_furniture
BUILT = False                  # True once build_wedge has run (site.py then leaves its own beds out here)

# street level
WEST_BED = [(24.2, 178.0), (29.0, 179.0), (35.0, 177.4), (40.0, 173.8), (44.4, 168.6), (45.4, 165.2), (42.0, 163.0),
            (36.8, 164.6), (31.0, 168.4), (26.4, 173.4)]
BIG_TREE = (32.4, 173.8)
SMALL_TREE = (38.6, 170.6)
TIP_BED = [(51.4, 160.2), (52.6, 156.6), (56.2, 155.6), (58.0, 157.8), (56.6, 160.8)]
DRIVE = [(46.8, 153.6), (51.6, 153.0), (51.8, 164.0), (47.0, 168.5)]   # in from the front road
DRIVE_D = (-1.35, -4.55)  # the lane under the west overhang, between the columns and the glazing


def _unit(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) + 1e-12)


def _left(t):
    return np.array([-t[1], t[0]])


def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


class Path:
    """The wing's outline (facade line) from the hotel's west fin, down the west side, round the tip,
    up the east side and round the north-east corner, as exact lines and counter-clockwise arcs.
    Outside is on the right of travel, so p(s, d) with d > 0 is outside the wing."""

    def __init__(self):
        dw = _unit(np.subtract(COPING_W[1], COPING_W[0]))
        de = _unit(np.subtract(COPING_E[1], COPING_E[0]))
        lw, le = _left(dw), _left(de)                      # inward normals
        pw = np.array(COPING_W[0]) + lw * COPING_OUT        # facade lines
        pe = np.array(COPING_E[0]) + le * COPING_OUT
        r = TIP_R - COPING_OUT
        # tip centre: r inside both facade lines
        A = np.array([lw, le])
        c = np.linalg.solve(A, np.array([lw @ pw + r, le @ pe + r]))
        t1, t2 = c - lw * r, c - le * r
        # north-east corner: CORNER_R inside the east line and below NORTH_Y
        dn = np.array([-1.0, 0.0])
        ln = _left(dn)                                       # (0, -1): inward from the north edge
        c2 = np.linalg.solve(np.array([le, ln]), np.array([le @ pe + CORNER_R, ln @ np.array([0.0, NORTH_Y]) + CORNER_R]))
        t3, t4 = c2 - le * CORNER_R, c2 - ln * CORNER_R
        # start on the west line well inside the hotel; end on the north edge inside the hotel / podium
        w0 = t1 + dw * ((190.0 - t1[1]) / dw[1])
        n1 = np.array([58.0, NORTH_Y])
        self.pieces = [('line', w0, t1), ('arc', c, r, *self._angles(c, t1, t2)), ('line', t2, t3),
                       ('arc', c2, CORNER_R, *self._angles(c2, t3, t4)), ('line', t4, n1)]
        self.tip_centre, self.tip_r = c, r
        self.lens = [self._len(p) for p in self.pieces]
        self.L = float(sum(self.lens))
        self.cum = np.concatenate([[0.0], np.cumsum(self.lens)])
        self.dw = dw

    @staticmethod
    def _angles(c, a, b):
        a0 = math.atan2(a[1] - c[1], a[0] - c[0])
        a1 = math.atan2(b[1] - c[1], b[0] - c[0])
        while a1 <= a0:
            a1 += 2 * math.pi
        return a0, a1

    @staticmethod
    def _len(p):
        if p[0] == 'line':
            return float(np.linalg.norm(p[2] - p[1]))
        return p[2] * (p[4] - p[3])

    def _at(self, s):
        s = min(max(s, 0.0), self.L)
        i = min(int(np.searchsorted(self.cum, s, side='right')) - 1, len(self.pieces) - 1)
        return self.pieces[i], s - self.cum[i]

    def p(self, s, d=0.0):
        pc, u = self._at(s)
        if pc[0] == 'line':
            t = _unit(pc[2] - pc[1])
            q = pc[1] + t * u
            n = np.array([t[1], -t[0]])
        else:
            c, r, a0, _ = pc[1:]
            a = a0 + u / r
            n = np.array([math.cos(a), math.sin(a)])
            q = c + n * r
        return q + n * d

    def n(self, s):
        return _unit(self.p(s, 1.0) - self.p(s, 0.0))

    def t(self, s):
        n = self.n(s)
        return np.array([-n[1], n[0]])

    def samples(self, s0, s1, step=0.5):
        """Arc lengths from s0 to s1: piece ends, plus every `step` metres on arcs."""
        out = [s0]
        for i, pc in enumerate(self.pieces):
            a, b = self.cum[i], self.cum[i + 1]
            if b <= s0 or a >= s1:
                continue
            if pc[0] == 'arc':
                k = max(1, int(math.ceil((min(b, s1) - max(a, s0)) / step)))
                out += list(np.linspace(max(a, s0), min(b, s1), k + 1)[1:])
            else:
                out.append(min(b, s1))
        out = sorted(set(round(float(x), 6) for x in out))
        return out

    def pts(self, s0, s1, d=0.0, step=0.5):
        return [tuple(map(float, self.p(s, d))) for s in self.samples(s0, s1, step)]

    def blend(self, s, west, tip, east):
        """A width that is `west` along the west side, `tip` round the tip and `east` up the east side and
        on, blended with a smoothstep across the piece joints (so offset lines have no steps or kinks)."""
        c1, c2 = self.cum[1], self.cum[2]
        w = west + (tip - west) * _smooth((s - (c1 - 2.0)) / 6.0)
        return w + (east - tip) * _smooth((s - (c2 - 3.0)) / 6.0)


def inner_region(path, width, north_w):
    """The wing shrunk by a width that varies along the outline (width(s) on the west side, tip and east
    side, north_w along the north end): the offset line, carried on to the north end's offset line (the
    north-east corner is tighter than the widths) and closed through the hotel."""
    yN = NORTH_Y - north_w
    pts = []
    for s in list(np.arange(0.0, path.cum[3], 0.25)) + [path.cum[3]]:
        q = path.p(s, -width(s))
        if s > path.cum[2] and q[1] > yN:
            break
        pts.append(q)
    t = _unit(pts[-1] - pts[-2])
    if abs(t[1]) > 1e-6:
        pts.append(pts[-1] + t * ((yN - pts[-1][1]) / t[1]))
    pts += [np.array([50.0, yN]), np.array([45.0, 197.0])]
    return Polygon([tuple(map(float, p)) for p in pts]).buffer(0)


# ----------------------------------------------------------------------------------------------
# context: the wing, the hotel and the podium next to it, the roads
# ----------------------------------------------------------------------------------------------

def hotel_base():
    """Outline of the hotel's lobby levels (its glazing line), in site metres."""
    from .geom import rounded_rect
    from .towers import TOWER_A, hotel_core
    H = TOWER_A
    x0, y0, x1, y1 = H['body']
    body = rounded_rect(x0, y0, x1, y1, H['r_west'], H['r_east'], H['r_east'], H['r_west'])
    full = unary_union([body.buffer(H['balcony'], quad_segs=12).intersection(box(-100, 0, 100, y1 + 1.2)), hotel_core(H)])
    g = full.buffer(-0.4)
    return affinity.translate(affinity.rotate(g, H['rot'], origin=(0, 0)), *H['origin'])


def hotel_fin():
    from .towers import TOWER_A
    H = TOWER_A
    gw = H['glass_w']
    fin = box(-gw / 2 - 0.9, -0.9, -gw / 2, 1.3)
    return affinity.translate(affinity.rotate(fin, H['rot'], origin=(0, 0)), *H['origin'])


def roads():
    from .site import ROADS
    polys = [LineString(pts).buffer(w / 2, cap_style='flat' if len(pts) == 2 else 'round', quad_segs=8) for pts, w in ROADS]
    return unary_union(polys)


def context():
    from .podium import WEDGE_TOP, podium_polygon
    path = Path()
    ring = path.pts(0.0, path.L, step=0.4)
    wing = Polygon(ring + [(45.0, 197.0)]).buffer(0)
    hotel = hotel_base()
    podium = podium_polygon()
    block = unary_union([hotel, podium, hotel_fin()])
    # the exposed outline: where the path runs outside the hotel and the podium
    ss = np.linspace(0.0, path.L, int(path.L / 0.05) + 1)
    free = [s for s in ss if not block.buffer(0.12).contains(Point(*path.p(s)))]
    s0, s1 = float(free[0]), float(free[-1])
    return dict(path=path, wing=wing, hotel=hotel, podium=podium, block=block, s0=s0, s1=s1, z=WEDGE_TOP,
                roads=roads())


def coarse_outline(step=0.6, tol=0.12):
    """The facade line as a short point list (podium.HOTEL_WEDGE), closed through the hotel."""
    path = Path()
    ring = Polygon(path.pts(0.0, path.L, step=step) + [(45.0, 197.0)]).simplify(tol)
    return [(round(x, 1), round(y, 1)) for x, y in list(ring.exterior.coords)[:-1]]


# ----------------------------------------------------------------------------------------------
# facade
# ----------------------------------------------------------------------------------------------

def _face_toward(mb, pts, want, mat, uv=None):
    from .deck.edge import _newell
    if _newell(pts) @ np.array(want, float) < 0:
        pts = pts[::-1]
        uv = uv[::-1] if uv else None
    mb.face(pts, mat, uv=uv)


def _cu_bottom(d):
    return BAND_TOP + CU_TIP * (CU_RIDGE - d) / (CU_RIDGE - CU_VALLEY)


def facade(mb, ctx):
    from .deck.edge import sweep
    path, s0, s1, z = ctx['path'], ctx['s0'], ctx['s1'], ctx['z']
    cu_top = z - 0.74
    pts = path.pts(s0, s1, step=0.5)
    # white rounded band, capped against the hotel
    sweep(mb, pts, 0.0, BAND, 'White band')
    # dark wall behind the copper
    sweep(mb, pts, 0.0, [(0.0, BAND_TOP - 0.01), (0.0, cu_top + 0.02)], 'Terracotta dark', caps=False)
    # folded copper panels with dark joints in the folds; UVs in metres like the podium's panels (u centred on
    # the panel, return faces at u >= 5, v = z + CU_V) so the joint rows, side lines and dots match
    n = max(1, int(round((s1 - s0 - 0.2) / CU_PANEL)))
    J = list(np.linspace(s0 + 0.1, s1 - 0.1, n + 1))
    for a, b in zip(J[:-1], J[1:]):
        pw = math.hypot(b - a, CU_RIDGE - CU_VALLEY)
        A, B = path.p(a, CU_VALLEY), path.p(b, CU_RIDGE)
        zA, zB = _cu_bottom(CU_VALLEY), _cu_bottom(CU_RIDGE)
        mb.face([(A[0], A[1], zA), (B[0], B[1], zB), (B[0], B[1], cu_top), (A[0], A[1], cu_top)], 'Copper screen',
                uv=[(-pw / 2, zA + CU_V), (pw / 2, zB + CU_V), (pw / 2, cu_top + CU_V), (-pw / 2, cu_top + CU_V)])
        P1, P2 = path.p(b, CU_RIDGE), path.p(b, CU_VALLEY)
        t = path.t(b)
        rw = CU_RIDGE - CU_VALLEY
        _face_toward(mb, [(P1[0], P1[1], zB), (P2[0], P2[1], zA), (P2[0], P2[1], cu_top), (P1[0], P1[1], cu_top)],
                     (t[0], t[1], 0.0), 'Copper screen',
                     uv=[(5.0, zB + CU_V), (5.0 + rw, zA + CU_V), (5.0 + rw, cu_top + CU_V), (5.0, cu_top + CU_V)])
        q = path.p(b, CU_VALLEY + 0.03)
        mb.box(float(q[0]), float(q[1]), zA, 0.08, 0.06, cu_top - zA, 'Terracotta dark', rot=math.atan2(t[1], t[0]))
    # top trim tucked under the coping
    trim = path.pts(s0, s1, d=0.25, step=0.5)
    mb.tube(trim, [cu_top - 0.06] * len(trim), [cu_top + 0.03] * len(trim), 0.5, 'Terracotta dark')
    parapet(mb, pts, z)
    return len(J) - 1


def parapet(mb, pts, z):
    """The podium deck's white rounded coping (deck/edge.PARAPET), white on its inner face too, with fine
    joints on its top, and a frameless tinted glass balustrade standing in a slim shoe on the paving just
    inside it, over the coping's height, with a slim handrail. Seen from the street the dark glass shows over
    the coping; from above, along the tip and the east side, it reads as the dark blue-grey band between the
    white coping and the paving that render 1 shows."""
    from .deck.edge import GLASS_Z1, PARAPET, RAIL_W, TOP, miter_normals, sweep
    sweep(mb, pts, z, PARAPET, 'White band')
    P = np.array(pts, float)
    N = miter_normals(P)
    ln = LineString(pts)
    k = int(ln.length // 4.5)
    for i in range(1, k + 1):
        s = ln.length * i / (k + 1)
        p = ln.interpolate(s)
        q = ln.interpolate(min(ln.length, s + 0.05))
        r = ln.interpolate(max(0.0, s - 0.05))
        t = _unit((q.x - r.x, q.y - r.y))
        n = np.array([t[1], -t[0]])
        a = np.array([p.x, p.y]) + n * 0.03
        b = np.array([p.x, p.y]) + n * -0.30
        w = t * 0.012
        zz = z + TOP + 0.003
        mb.face([(a[0] - w[0], a[1] - w[1], zz), (a[0] + w[0], a[1] + w[1], zz), (b[0] + w[0], b[1] + w[1], zz),
                 (b[0] - w[0], b[1] - w[1], zz)], 'Metal')
    gl = [(float(p[0] + n[0] * GLASS_D), float(p[1] + n[1] * GLASS_D)) for p, n in zip(P, N)]
    mb.ribbon(gl, z + 0.02, z + GLASS_Z1, _mat('Railing glass dark', 'Railing glass'), double=True)
    mb.tube(gl, [z + 0.02] * len(gl), [z + 0.12] * len(gl), 0.07, 'Shop frame')          # base shoe
    mb.tube(gl, [z + GLASS_Z1 - 0.01] * len(gl), [z + GLASS_Z1 + 0.045] * len(gl), RAIL_W, 'Metal')


def ground_floor(mb, ctx):
    """Glazing set back under the overhang, white soffit with downlights, round columns on the outline."""
    path, wing, hotel = ctx['path'], ctx['wing'], ctx['hotel']
    gf = inner_region(path, lambda s: path.blend(s, *GF_SET), GF_SET[2])
    gf = gf.intersection(wing).difference(hotel.buffer(0.02)).difference(ctx['podium'])
    # the set-back line runs into the hotel where the east side passes its east end (the hotel's own lobby
    # glazing is the wall under the overhang there): a main hall and a small room north of the hotel
    rooms = sorted([g for g in getattr(gf, 'geoms', [gf]) if g.area > 4.0], key=lambda g: -g.area)
    gf = unary_union(rooms)
    over = wing.difference(gf).difference(hotel.buffer(0.02)).difference(ctx['podium'])
    # soffit (faces down)
    mb.polygon_face(over, SOFFIT, 'White band', up=False)
    # ground floor glazing along the part of the set-back line outside the hotel: dark glass, as the
    # shaded glazing under the deep overhang reads on render 1
    from .deck.edge import _lines, miter_normals, orient_out
    line = unary_union([g.exterior for g in rooms]).difference(hotel.buffer(0.1)).difference(ctx['podium'].buffer(0.1))
    frame = _mat('Shop frame', 'Car dark')
    nwin = 0
    for l in _lines(line):
        if l.length < 0.6:
            continue
        pts = orient_out(l.simplify(0.01), gf)
        if not pts:
            continue
        P = np.array(pts, float)
        top = SOFFIT
        mb.ribbon(pts, STREET, top, 'Shop glass')
        # sill, transom and head rails (centred 6 cm in front of the glass)
        N = miter_normals(P)
        F = [tuple(map(float, p + n * 0.06)) for p, n in zip(P, N)]
        for z0, z1, w in [(STREET, STREET + 0.3, 0.14), (GF_TRANSOM, GF_TRANSOM + 0.1, 0.1), (top - 0.12, top, 0.12)]:
            mb.tube(F, [z0] * len(F), [z1] * len(F), w, frame)
        # mullions every ~1.75 m, a heavier post every fourth
        L = LineString(F)
        k = max(1, int(round(L.length / 1.75)))
        for i in range(k + 1):
            q = L.interpolate(L.length * i / k)
            r_ = L.interpolate(min(L.length, L.length * i / k + 0.05))
            o = L.interpolate(max(0.0, L.length * i / k - 0.05))
            ang = math.atan2(r_.y - o.y, r_.x - o.x)
            heavy = i % 4 == 0 or i == k
            mb.box(q.x, q.y, STREET + 0.3, 0.16 if heavy else 0.07, 0.12, top - STREET - 0.42, frame, rot=ang)
            nwin += 1
    entrance(mb, ctx, rooms[0], frame)
    # downlights in the soffit, along the middle of the overhang
    s0, s1 = ctx['s0'], ctx['s1']
    s = s0 + 2.0
    while s < s1 - 1.5:
        q = path.p(s, -0.45 * path.blend(s, *GF_SET))
        if over.buffer(-0.3).contains(Point(*q)):
            mb.polygon_face(Point(*q).buffer(0.16, quad_segs=3), SOFFIT - 0.01, 'Lamp glow', up=False)
        s += 3.0
    # slim round columns on the outline (none at the road side)
    clear = unary_union([ctx['roads'].buffer(1.6), hotel.buffer(1.2), ctx['podium'].buffer(1.0)])
    ncol = 0
    span = s1 - s0
    k = max(1, int(round(span / 7.6)))
    for i in range(1, k):
        s = s0 + span * i / k
        q = path.p(s, -0.75)
        if clear.contains(Point(*q)):
            continue
        _column(mb, q[0], q[1])
        ncol += 1
    return gf, over, nwin, ncol


def entrance(mb, ctx, gf, frame):
    """Hotel entrance on the drop-off lane: a pair of glazed sliding doors in a deep dark portal."""
    path = ctx['path']
    s = 0.5 * (ctx['s0'] + path.cum[1]) + 2.0
    from shapely.ops import nearest_points
    q = np.array(nearest_points(gf.exterior, Point(*path.p(s, -GF_SET[0])))[0].coords[0])
    t, n = path.t(s), path.n(s)
    rot = math.atan2(t[1], t[0])
    W, H, D = 3.4, 3.4, 0.32
    c = q + n * (D / 2 - 0.02)
    for u in (-W / 2, W / 2):                     # jambs
        p = c + t * u
        mb.box(float(p[0]), float(p[1]), STREET, 0.18, D, H, frame, rot=rot)
    mb.box(float(c[0]), float(c[1]), STREET + H, W + 0.18, D, 0.32, frame, rot=rot)   # head
    for k in (-1, 1):                             # two sliding leaves, slim frames, pull bars
        p = q + t * (k * W / 4) + n * 0.05
        mb.box(float(p[0]), float(p[1]), STREET + 0.02, W / 2 - 0.08, 0.04, H - 0.04, 'Shop glass', rot=rot)
        for z0, h in ((STREET + 0.02, 0.1), (STREET + H - 0.1, 0.1)):
            mb.box(float(p[0]), float(p[1]), z0, W / 2 - 0.08, 0.07, h, frame, rot=rot)
        for u in (-(W / 4 - 0.07), W / 4 - 0.07):
            e = p + t * u
            mb.box(float(e[0]), float(e[1]), STREET + 0.02, 0.07, 0.07, H - 0.04, frame, rot=rot)
        b = p + t * (-k * (W / 4 - 0.3)) + n * 0.08
        mb.box(float(b[0]), float(b[1]), STREET + 0.9, 0.05, 0.05, 1.1, 'Metal', rot=rot)
    return q


def _column(mb, x, y, r=0.26):
    from .deck.common import rod
    rod(mb, (x, y, STREET), (x, y, SOFFIT), r, 'White band', sides=10)
    mb.prism(Point(x, y).buffer(r + 0.08, quad_segs=3), STREET, STREET + 0.12, 'Shop frame', 'Shop frame')


def _mat(name, fallback):
    try:
        import bpy
        return name if bpy.data.materials.get(name) is not None else fallback
    except Exception:
        return fallback


# ----------------------------------------------------------------------------------------------
# terrace
# ----------------------------------------------------------------------------------------------

def slabs(mb, zone, z, size=SLAB, angle=0.0, joint=SLAB_JOINT):
    """Tan stone slabs: a joint layer 3 cm under the slab tops (so it does not flicker in the web viewer
    at a distance) and one face per slab, clipped to the zone. One stone colour, as on render 1 (the viewer
    textures 'Deck stone' with its own variation)."""
    from .deck.common import PAVE_T
    from .deck.edge import joint_mat
    zone = zone.buffer(0)
    if zone.is_empty:
        return 0
    zj = z + PAVE_T - 0.03
    mb.prism(zone, z, zj, 'Deck stone', None)
    mb.polygon_face(zone, zj, joint_mat())
    c = zone.centroid
    loc = affinity.rotate(zone, -angle, origin=c, use_radians=True)
    x0, y0, x1, y1 = loc.bounds
    a, b = size
    n = 0
    j = 0
    y = y0 - b
    while y < y1 + b:
        off = (j % 2) * a * 0.5 if abs(a - b) > 1e-6 else 0.0
        x = x0 - a + off
        while x < x1 + a:
            sq = box(x + joint / 2, y + joint / 2, x + a - joint / 2, y + b - joint / 2)
            sq = affinity.rotate(sq, angle, origin=c, use_radians=True)
            if zone.intersects(sq):
                g = sq if zone.contains(sq) else sq.intersection(zone)
                for q in getattr(g, 'geoms', [g]):
                    if q.geom_type == 'Polygon' and q.area > 0.01:
                        mb.polygon_face(q, z + PAVE_T, 'Deck stone')
                        n += 1
            x += a
        y += b
        j += 1
    return n


def cobble(mb, zone, z, rnd, size, angle):
    """deck/edge.cobble (the podium decks' grey cobble), with the stones lifted so they sit 3 cm over the
    joint layer instead of 8 mm (no flicker in the web viewer at a distance)."""
    from .deck.common import PAVE_T
    from .deck.edge import cobble as edge_cobble, joint_mat
    tmp = MeshBuilder()
    z0 = z - 0.03
    n = edge_cobble(tmp, zone, z0, rnd, size=size, angle=angle)
    zs = z0 + PAVE_T + 0.014
    jm = joint_mat()
    lift = set()
    for f, m in zip(tmp.faces, tmp.mats):
        if m != jm and all(abs(tmp.verts[i][2] - zs) < 1e-4 for i in f):
            lift.update(f)
    for i in lift:
        x, y, zz = tmp.verts[i]
        tmp.verts[i] = (x, y, zz + 0.03)
    mb.merge(tmp)
    return n


def full_tree(mb, x, y, z, h, r, rnd, leaves=('Leaves', 'Leaves light'), trunk=0.36, fine=False):
    """Big street tree: short trunk forking into limbs, a broad crown of overlapping clumps that starts
    low, two leaf greens mixed."""
    from .deck.common import rod
    zt = z + h * trunk
    rod(mb, (x, y, z), (x, y, zt), 0.06 + 0.012 * h, 'Trunk', sides=6)
    for k in range(4):
        a = k * math.pi / 2 + rnd.uniform(-0.5, 0.5)
        rod(mb, (x, y, zt - 0.2), (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z + h * 0.66), 0.03 + 0.006 * h,
            'Trunk', sides=5)
    vh = h * (1 - trunk) / 2                  # crown half height
    zc = zt + vh * 0.95
    mb.blob(x, y, zc, r * 0.82, r * 0.82, vh * 0.8, leaves[0], subdiv=2, jitter=0.12, rnd=rnd)
    mb.blob(x + rnd.uniform(-0.15, 0.15) * r, y + rnd.uniform(-0.15, 0.15) * r, zc + vh * 0.45, r * 0.6, r * 0.6, vh * 0.55,
            leaves[1], subdiv=2, jitter=0.12, rnd=rnd)
    n = 6
    for k in range(n):
        a = k * 2 * math.pi / n + rnd.uniform(-0.35, 0.35)
        dz = (-0.3 if k % 2 else 0.12) * vh
        rr = r * (0.62 if k % 2 else 0.54) * rnd.uniform(0.9, 1.1)
        mb.blob(x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, zc + dz, rr, rr, rr * 0.85, leaves[k % 2],
                subdiv=2 if fine else 1, jitter=0.14, rnd=rnd)


def bushy_tree(mb, x, y, z, h, r, rnd, leaves=('Leaves', 'Leaves light')):
    """Low multi-stem terrace tree as on render 1 (not a ball on a stick): a short trunk forking into
    2-3 leaning stems at about 0.6 m, and a lumpy crown wider than it is tall that starts about a metre
    over the planter, built from a core and 8-10 clumps of mixed size, offset sideways and up and down."""
    from .deck.common import rod
    zf = z + 0.6
    rod(mb, (x, y, z - 0.05), (x, y, zf), 0.1, 'Trunk', sides=6)
    a0 = rnd.uniform(0, 2 * math.pi)
    for k in range(rnd.choice((2, 3, 3))):
        a = a0 + k * 2.2 + rnd.uniform(-0.3, 0.3)
        lean = r * rnd.uniform(0.25, 0.42)
        top = (x + math.cos(a) * lean, y + math.sin(a) * lean, z + h * rnd.uniform(0.45, 0.6))
        rod(mb, (x, y, zf - 0.08), top, 0.06, 'Trunk', sides=5)
    zb = z + max(0.9, h * 0.22)                # crown bottom
    vh = (z + h - zb) / 2                      # crown half height
    zc = zb + vh
    mb.blob(x, y, zc, r * 0.7, r * 0.7, vh * 0.8, leaves[0], subdiv=2, jitter=0.14, rnd=rnd)
    n = rnd.choice((8, 9, 10))
    for k in range(n):
        a = a0 + k * 2 * math.pi / n + rnd.uniform(-0.3, 0.3)
        off = r * rnd.uniform(0.4, 0.75)
        rr = min(r * rnd.uniform(0.45, 0.9), r * 1.12 - off)
        rr = max(rr, 0.4 * r)
        rz = rr * rnd.uniform(0.7, 0.88)
        cz = zc + rnd.uniform(-0.4, 0.4) * vh
        cz = min(max(cz, zb + rz * 0.75), z + h - rz * 0.85)
        light = rnd.random() < (0.75 if cz > zc else 0.3)        # sunlit upper clumps lighter
        mb.blob(x + math.cos(a) * off, y + math.sin(a) * off, cz, rr, rr * rnd.uniform(0.85, 1.1), rz,
                leaves[1] if light else leaves[0], subdiv=2 if rr > 0.68 * r else 1, jitter=0.16, rnd=rnd)


def bush(mb, x, y, z, r, rnd, mat, subdiv=2, squash=0.86):
    """Round clipped shrub sitting on z."""
    mb.blob(x, y, z + r * 0.8 * squash / 0.86, r, r, r * squash, mat, subdiv=subdiv, jitter=0.1, rnd=rnd)


def planter_seat(mb, x, y, z, rnd, h, r):
    """Round planter with a timber seat ring on its wall, a few low shrubs of mixed size round the tree."""
    R = PLANTER_R
    wall = Point(x, y).buffer(R, quad_segs=7).difference(Point(x, y).buffer(R - 0.22, quad_segs=7))
    mb.prism(wall, z, z + 0.42, 'Planter', None)
    seat = Point(x, y).buffer(R + 0.06, quad_segs=7).difference(Point(x, y).buffer(R - 0.3, quad_segs=7))
    mb.prism(seat, z + 0.42, z + 0.48, 'Wood', 'Wood', 'Wood')
    mb.polygon_face(Point(x, y).buffer(R - 0.22, quad_segs=7), z + 0.36, 'Lawn')
    k = rnd.choice((2, 3, 4))
    a0 = rnd.uniform(0, 2 * math.pi)
    for i in range(k):
        a = a0 + i * 2 * math.pi / k + rnd.uniform(-0.4, 0.4)
        rr = rnd.uniform(0.22, 0.48)
        d = R - 0.25 - rr * 0.8
        bush(mb, x + math.cos(a) * d, y + math.sin(a) * d, z + 0.34, rr, rnd,
             rnd.choice(['Shrub', 'Leaves light', 'Leaves']), subdiv=1, squash=rnd.uniform(0.6, 0.85))
    bushy_tree(mb, x, y, z + 0.36, h, r, rnd, leaves=('Leaves light', 'Leaves light'))  # light yellow-green as on the render


def terrace(mb, ctx, rnd):
    from .deck.common import PAVE_T, lamp
    path, z = ctx['path'], ctx['z']
    s0, s1 = ctx['s0'], ctx['s1']
    hotel = ctx['hotel']
    wing = ctx['wing']
    # the paving stops at the hotel's floor band (0.25 m proud of its glass); a white sill covers the join
    deck = wing.difference(ctx['block'].buffer(0.02)).difference(hotel.buffer(HOTEL_SILL))
    deck = max(getattr(deck, 'geoms', [deck]), key=lambda g: g.area)
    sill = wing.intersection(hotel.buffer(HOTEL_SILL)).difference(hotel.buffer(0.01)).difference(
        ctx['block'].difference(hotel).buffer(0.02)).difference(LineString(path.pts(s0, s1)).buffer(0.45, cap_style='flat'))
    mb.prism(sill, z, z + 0.36, 'White band', 'White band')
    edge = LineString(path.pts(s0, s1, step=0.4))
    walk = deck.difference(edge.buffer(-GLASS_D + 0.04, cap_style='flat'))
    # slab under the paving (it shows only through gaps) and the tan stone middle
    mb.polygon_face(deck, z, 'Cobble')
    hb = unary_union([hotel.buffer(HOTEL_W[1], quad_segs=12),
                      hotel.intersection(box(0, 0, HOTEL_SPLIT_X, 400)).buffer(HOTEL_W[0], quad_segs=12)])
    zone = inner_region(path, lambda s: path.blend(s, *EDGE_W), EDGE_W[2])
    tan = deck.intersection(zone).difference(hb)
    tan = max(getattr(tan, 'geoms', [tan]), key=lambda g: g.area)
    tan = tan.buffer(-1.3, join_style='round').buffer(1.3, join_style='round').buffer(-0.01)
    kerb = tan.buffer(0.14, join_style='round', quad_segs=4).difference(tan).simplify(0.03)
    ang = math.atan2(path.dw[1], path.dw[0])
    keep = unary_union([Point(x, y).buffer(PLANTER_R + 0.02) for x, y, _, _ in TREES])
    n_slab = slabs(mb, tan.difference(keep), z, angle=ang)
    mb.prism(kerb, z, z + PAVE_T + 0.03, 'Kerb', 'Kerb')
    border = walk.difference(tan.buffer(0.14, join_style='round'))
    n_cob = cobble(mb, border, z, rnd, COBBLE, ang)
    for x, y, h, r in TREES:
        planter_seat(mb, x, y, z + PAVE_T, rnd, h, r)
    # swan-neck lamps in the border, leaning over the terrace
    n_lamp = 0
    lamps = []
    for d in LAMPS_S:
        s = s0 + d
        if not s0 + 2 < s < s1 - 2:
            continue
        q = path.p(s, -1.2)
        nn = path.n(s)
        if border.buffer(-0.2).contains(Point(*q)):
            lamp(mb, float(q[0]), float(q[1]), z + PAVE_T, rot=math.atan2(-nn[1], -nn[0]))
            lamps.append(Point(*q))
            n_lamp += 1
    # a few people on the tan stone (drawn by site.street_furniture with everyone else)
    prnd = random.Random(808)
    room = tan.buffer(-0.8)
    taken = [Point(x, y).buffer(PLANTER_R + 0.6) for x, y, _, _ in TREES] + [p.buffer(0.6) for p in lamps]
    people = []
    x0, y0, x1, y1 = tan.bounds
    for _ in range(400):
        if len(people) >= 7:
            break
        p = Point(prnd.uniform(x0, x1), prnd.uniform(y0, y1))
        if not room.contains(p) or any(t.contains(p) for t in taken) or any(p.distance(q) < 1.2 for q in people):
            continue
        people.append(p)
    TERRACE_PEOPLE[:] = [(round(p.x, 2), round(p.y, 2), round(z + PAVE_T + 0.02, 2), prnd.randrange(6)) for p in people]
    return deck, tan, n_slab, n_cob, n_lamp


# ----------------------------------------------------------------------------------------------
# street level round the wing
# ----------------------------------------------------------------------------------------------

def street(mb, ctx, rnd, gf):
    from .deck.common import lawn
    path, wing, rd, hotel = ctx['path'], ctx['wing'], ctx['roads'], ctx['hotel']
    clear = unary_union([rd.buffer(1.75), wing.buffer(0.35), hotel.buffer(0.5)])
    # drop-off lane: in from the front road and on under the west overhang to the hotel entrance,
    # between the columns and the ground floor glazing (thin asphalt on the plaza, as on render 1)
    sa, sb = ctx['s0'] + 1.5, path.cum[1] + 3.0
    lane = Polygon(path.pts(sa, sb, d=DRIVE_D[0]) + path.pts(sa, sb, d=DRIVE_D[1])[::-1])
    drive = unary_union([lane, Polygon(DRIVE)]).buffer(1.5, join_style='round').buffer(-1.5, join_style='round')
    drive = drive.difference(gf.buffer(0.3)).difference(hotel.buffer(0.6)).difference(rd.buffer(0.05))
    drive = max(getattr(drive, 'geoms', [drive]), key=lambda g: g.area)
    mb.prism(drive, STREET - 0.04, STREET + 0.012, 'Asphalt', 'Asphalt')
    # beds (site.lawns_and_beds leaves its own beds here out once the wing is built)
    beds = []
    wb = Polygon(WEST_BED).buffer(1.0, join_style='round').buffer(-1.0, join_style='round')
    wb = wb.difference(clear).difference(drive.buffer(0.6))
    tb = Polygon(TIP_BED).buffer(1.0, join_style='round').buffer(-0.6, join_style='round').difference(clear)
    tb = tb.difference(drive.buffer(0.6))
    for g in (wb, tb):
        g = max(getattr(g, 'geoms', [g]), key=lambda q: q.area) if not g.is_empty else g
        if g.is_empty or g.area < 3.0:
            continue
        g = g.buffer(-0.4, join_style='round').buffer(0.4, join_style='round')
        lawn(mb, g, STREET, kerb=0.3)
        beds.append(g)
    top = STREET + 0.28
    n_shrub = 0
    if beds:
        wb = beds[0]
        full_tree(mb, *BIG_TREE, top, 10.5, 3.6, rnd, leaves=('Leaves light', 'Leaves'), trunk=0.3)
        full_tree(mb, *SMALL_TREE, top, 5.0, 1.5, rnd, leaves=('Leaves', 'Leaves light'), trunk=0.4)
        # clipped round shrubs along the south edge of the west bed and in its east corner
        spots = [(27.0, 176.6), (29.6, 173.0), (33.2, 169.6), (36.6, 167.4), (40.0, 166.2), (42.8, 166.4), (41.4, 169.4),
                 (35.8, 170.4), (38.8, 173.0), (30.0, 176.8)]
        for x, y in spots:
            if wb.buffer(-0.6).contains(Point(x, y)) and Point(x, y).distance(Point(*BIG_TREE)) > 1.6 \
                    and Point(x, y).distance(Point(*SMALL_TREE)) > 1.0:
                bush(mb, x, y, top, rnd.uniform(0.55, 0.8), rnd, rnd.choice(['Shrub', 'Leaves', 'Leaves light']))
                n_shrub += 1
    for g in beds[1:]:
        x0, y0, x1, y1 = g.bounds
        for _ in range(30):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            if g.buffer(-0.55).contains(Point(x, y)) and n_shrub < 14:
                bush(mb, x, y, top, rnd.uniform(0.5, 0.72), rnd, rnd.choice(['Shrub', 'Leaves', 'Leaves light']))
                n_shrub += 1
    return beds, drive, n_shrub


# ----------------------------------------------------------------------------------------------

def build_wedge(mats, col):
    global BUILT
    BUILT = False
    TERRACE_PEOPLE.clear()
    rnd = random.Random(20261011)
    ctx = context()
    mb = MeshBuilder()
    n_cu = facade(mb, ctx)
    gf, over, n_mull, n_col = ground_floor(mb, ctx)
    deck, tan, n_slab, n_cob, n_lamp = terrace(mb, ctx, rnd)
    beds, drive, n_shrub = street(mb, ctx, rnd, gf)
    ob = make_object('Hotel terrace wing', mb.to_mesh('Hotel terrace wing', mats), col)
    BUILT = True
    tris = sum(len(f) - 2 for f in mb.faces)
    by = {}
    for f, m in zip(mb.faces, mb.mats):
        by[m] = by.get(m, 0) + len(f) - 2
    print('[wedge] triangles by material:', ', '.join(f'{m} {n}' for m, n in sorted(by.items(), key=lambda x: -x[1])[:14]))
    print(f'[wedge] outline {ctx["s1"] - ctx["s0"]:.1f} m exposed (tip r {ctx["path"].tip_r:.2f} m), deck {deck.area:.0f} m2, '
          f'tan {tan.area:.0f} m2, {n_cu} copper panels, {n_mull} mullions, {n_col} columns, {n_slab} slabs, {n_cob} cobbles, '
          f'{n_lamp} lamps, {len(beds)} beds, {n_shrub} shrubs, {len(TERRACE_PEOPLE)} people, ~{tris} triangles')
    return ob
