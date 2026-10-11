"""Street level in front of the shop front and the ground playground (pool-deck render, render 2).

    promenade   grey cobble strip along the shop front, light paving out to the river-side and east
                roads, long lens-shaped planters (lawn, round shrubs, small trees) following the curve,
                white spherical bollards along the kerb
    playground  on the blue part of the ground playground (site.playground): deep blue rubber,
                a dark-brown geodesic climbing dome, a timber play tower with a slide and a swing set

build(mats, col, rnd, roads) is called from site.build_site after the street furniture.
"""
import math
import random

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from .geom import MeshBuilder, biggest, get_collection, icosphere, make_object

Z0 = 0.0
PAVE_TOP = 0.15         # promenade surface (site plaza is at +0.10, sidewalks at +0.12)
COBBLE_W = 4.2          # cobble strip along the shop front
FRONT_W = 26.0          # how far out the promenade may reach (it stops at the roads)
BOLLARD_STEP = 5.0      # along the kerb (the render shows them ~5 m apart)
BOLLARD_R = 0.23

# lens planters: (centre arc length from the hotel end along the outer line, length, max width,
# distance of the planter axis from the shop front, number of trees)
# (the ends of the curve are too close to the roads for planters)
LENSES = [(44.0, 26.0, 3.8, 11.5, 3), (78.0, 22.0, 3.0, 9.0, 2), (106.0, 18.0, 3.0, 8.5, 2), (135.0, 22.0, 3.2, 8.5, 2),
          (166.0, 20.0, 3.0, 8.0, 2)]

# ground playground (blue part of site.playground)
BLUE = [(2.0, 222.6), (16.2, 219.3), (16.5, 205.0), (14.7, 196.1), (10.4, 193.2), (1.0, 199.0)]
PLAY_Z = 0.16
DOME = (10.3, 198.8, 2.45)           # x, y, radius (~4.9 m across, ~3.3 m high)
TOWER = (4.1, 203.6, -math.pi / 2)   # x, y, rotation (the slide runs out along the rotated +x: south)
SWINGS = (12.6, 210.6, math.radians(80))


def build(mats, col, rnd, roads):
    from .podium import OUTER, podium_polygon
    r = random.Random(20261012)
    mb = MeshBuilder()
    outer = LineString(OUTER)
    region = promenade_region(outer, podium_polygon(), roads)
    lenses = promenade(mb, outer, region, r)
    nb = bollards(mb, region, roads, lenses)
    print(f'[street] promenade {region.area:.0f} m2, {len(lenses)} lens planters, {nb} bollards')
    make_object('Promenade', mb.to_mesh('Promenade', mats), get_collection('Street', col))

    mb = MeshBuilder()
    playground(mb, r)
    make_object('Ground playground', mb.to_mesh('Ground playground', mats), get_collection('Street', col))


# ----------------------------------------------------------------------------------------------
# promenade
# ----------------------------------------------------------------------------------------------

def _pieces(g):
    return [x for x in getattr(g, 'geoms', [g]) if x.geom_type == 'Polygon' and not x.is_empty]


def promenade_region(outer, podium, roads):
    """Ground between the shop front and the roads (only the pieces that touch the shop front)."""
    from .deck import tower_footprints
    from .podium import HOTEL_WEDGE
    band = outer.buffer(FRONT_W, single_sided=True)
    if band.distance(Point(0.0, 300.0)) > 0.1:      # make sure we took the river side
        band = outer.buffer(-FRONT_W, single_sided=True)
    blocked = unary_union([podium.buffer(0.02), roads.buffer(0.3), Polygon(HOTEL_WEDGE).buffer(1.0)] +
                          [p.buffer(0.5) for p in tower_footprints().values()])
    rest = band.difference(blocked)
    keep = [g for g in _pieces(rest) if g.area > 30 and g.distance(outer) < 0.2]
    return unary_union(keep).buffer(0)


def at(outer, s, d):
    """Point d metres out from the shop front at arc length s from the hotel end, and the tangent."""
    L = outer.length
    u = min(max(L - s, 0.0), L)
    p = outer.interpolate(u)
    q = outer.interpolate(min(L, u + 0.6))
    o = outer.interpolate(max(0.0, u - 0.6))
    t = np.array([q.x - o.x, q.y - o.y])
    t /= (np.linalg.norm(t) + 1e-12)
    n = np.array([-t[1], t[0]])                 # left of the OUTER direction = outside
    return np.array([p.x, p.y]) + n * d, t


def lens_polygon(outer, s0, length, width, d):
    left, right = [], []
    k = max(8, int(length / 0.8))
    for i in range(k + 1):
        f = i / k
        hw = 0.5 * width * math.sin(math.pi * f) ** 0.75 + 0.18
        s = s0 - length / 2 + length * f
        p_out, _ = at(outer, s, d + hw)
        p_in, _ = at(outer, s, d - hw)
        left.append(tuple(p_out))
        right.append(tuple(p_in))
    return Polygon(left + right[::-1]).buffer(0.3).buffer(-0.3).simplify(0.03)


def promenade(mb, outer, region, rnd):
    from .deck.common import lawn
    cobble = region.intersection(outer.buffer(COBBLE_W, single_sided=True)).buffer(0)
    if cobble.distance(Point(0.0, 300.0)) > COBBLE_W + 0.5:
        cobble = region.intersection(outer.buffer(-COBBLE_W, single_sided=True)).buffer(0)
    paving = region.difference(cobble.buffer(0.01))
    for g in _pieces(cobble):
        mb.prism(g, Z0, PAVE_TOP - 0.01, 'Kerb', 'Cobble')
    cobble_stones(mb, outer, cobble, rnd, PAVE_TOP - 0.01)
    for g in _pieces(paving):
        mb.prism(g, Z0, PAVE_TOP, 'Kerb', 'Promenade')
    # light stone edge between the cobble strip and the paving
    edge = outer.offset_curve(COBBLE_W)
    if edge.distance(Point(0.0, 300.0)) > outer.distance(Point(0.0, 300.0)):
        edge = outer.offset_curve(-COBBLE_W)
    strip = edge.buffer(0.14, cap_style='flat').intersection(region)
    for g in _pieces(strip):
        mb.prism(g, PAVE_TOP - 0.01, PAVE_TOP + 0.015, 'Planter', 'Planter')

    lenses = []
    inner = paving.buffer(-1.6)
    for (sc, length, width, d, ntrees) in LENSES:
        poly = lens_polygon(outer, sc, length, width, d)
        poly = biggest(poly.intersection(inner))
        if poly.is_empty or poly.area < 12:
            continue
        lenses.append(poly)
        lawn(mb, poly, PAVE_TOP, kerb=0.2)
        z = PAVE_TOP + 0.18
        # trees spread along the axis, shrubs in between, a few columnar ones
        s_trees = [sc - length / 2 + length * (i + 0.5) / ntrees for i in range(ntrees)]
        for i, s in enumerate(s_trees):
            p, _ = at(outer, s + rnd.uniform(-1.0, 1.0), d + rnd.uniform(-0.3, 0.3))
            if poly.buffer(-0.4).contains(Point(*p)):
                street_tree(mb, p[0], p[1], z, rnd)
        k = int(length / 1.6)
        for i in range(k):
            s = sc - length / 2 + length * (i + 0.5) / k + rnd.uniform(-0.4, 0.4)
            if min(abs(s - st) for st in s_trees) < 1.6:
                continue
            p, _ = at(outer, s, d + rnd.uniform(-0.6, 0.6))
            if not poly.buffer(-0.5).contains(Point(*p)):
                continue
            rr = rnd.uniform(0.45, 0.8)
            if rnd.random() < 0.18:
                mb.blob(p[0], p[1], z + rr * 1.3, rr * 0.7, rr * 0.7, rr * 1.6, 'Leaves', subdiv=1, jitter=0.1, rnd=rnd)
            else:
                mat = 'Shrub' if rnd.random() < 0.6 else 'Leaves light'
                mb.blob(p[0], p[1], z + rr * 0.75, rr, rr, rr * 0.85, mat, subdiv=1, jitter=0.12, rnd=rnd)
    return lenses


def cobble_stones(mb, outer, zone, rnd, z):
    """Light irregular stones on the strip along the shop front: a jittered grid that follows the
    curve, each stone shrunk a little so the darker joints show."""
    from shapely.prepared import prep
    L = outer.length
    ds, dd = 0.62, 0.52
    ns, nd = int(L / ds) + 1, int(round(COBBLE_W / dd))
    G = np.zeros((ns + 1, nd + 1, 2))
    for i in range(ns + 1):
        for j in range(nd + 1):
            js = rnd.uniform(-0.17, 0.17) if 0 < j < nd else 0.0
            jd = rnd.uniform(-0.12, 0.12) if 0 < j < nd else 0.0
            G[i, j], _ = at(outer, i * ds + js * (1 if j % 2 else -1), 0.05 + j * (COBBLE_W - 0.1) / nd + jd)
    area = prep(zone.buffer(-0.08))
    mats = ['Planter', 'Kerb', 'Planter', 'Sidewalk', 'Kerb', 'Cobble', 'Planter']
    for i in range(ns):
        for j in range(nd):
            q = [G[i, j], G[i + 1, j], G[i + 1, j + 1], G[i, j + 1]]
            c = sum(q) / 4
            if not area.contains(Point(*c)):
                continue
            q = [c + (p - c) * 0.86 for p in q]
            a2 = sum(q[k][0] * q[k - 3][1] - q[k - 3][0] * q[k][1] for k in range(4))
            if a2 < 0:
                q = q[::-1]
            mb.face([(p[0], p[1], z + 0.012) for p in q], mats[rnd.randrange(len(mats))], uv=[(p[0], p[1]) for p in q])


def street_tree(mb, x, y, z, rnd):
    """Small promenade tree: slim trunk, a light crown of a few clumps."""
    from .deck.common import rod
    h = rnd.uniform(4.2, 5.4)
    r = rnd.uniform(1.3, 1.7)
    rod(mb, (x, y, z), (x, y, z + h * 0.5), 0.1, 'Trunk', sides=5)
    for k in range(3):
        a = k * 2.1 + rnd.uniform(-0.3, 0.3)
        rod(mb, (x, y, z + h * 0.42), (x + math.cos(a) * r * 0.45, y + math.sin(a) * r * 0.45, z + h * 0.66), 0.05, 'Trunk', sides=4)
    leaf = 'Leaves light' if rnd.random() < 0.6 else 'Leaves'
    for dx, dy, dz, rr in [(0, 0, 0.72, 1.0), (0.4, 0.22, 0.66, 0.68), (-0.36, -0.24, 0.68, 0.66), (0.08, -0.1, 0.9, 0.6)]:
        mb.blob(x + dx * r, y + dy * r, z + h * dz, r * rr, r * rr, r * rr * 0.85, leaf, subdiv=2, jitter=0.14, rnd=rnd)


def bollards(mb, region, roads, lenses):
    """White spheres along the kerb of the roads, ~0.45 m across."""
    near = roads.buffer(0.9)
    keep_out = unary_union(lenses).buffer(0.8) if lenses else Polygon()
    count = 0
    for g in _pieces(region):
        ring = g.exterior
        L = ring.length
        last = -1e9
        s = 0.0
        while s < L:
            p = ring.interpolate(s)
            if near.contains(p) and s - last >= BOLLARD_STEP:
                # step in from the kerb
                q = ring.interpolate(min(L, s + 0.3))
                o = ring.interpolate(max(0.0, s - 0.3))
                t = np.array([q.x - o.x, q.y - o.y])
                t /= (np.linalg.norm(t) + 1e-12)
                c = None
                for sgn in (1, -1):
                    cand = np.array([p.x, p.y]) + sgn * np.array([-t[1], t[0]]) * 0.55
                    if g.contains(Point(*cand)):
                        c = cand
                        break
                if c is not None and not keep_out.contains(Point(*c)):
                    mb.blob(c[0], c[1], PAVE_TOP + BOLLARD_R * 0.92, BOLLARD_R, BOLLARD_R, BOLLARD_R, 'Bollard', subdiv=1)
                    last = s
                    count += 1
            s += 0.5
    return count


# ----------------------------------------------------------------------------------------------
# ground playground
# ----------------------------------------------------------------------------------------------

def playground(mb, rnd):
    blue = Polygon(BLUE).buffer(1.5).buffer(-1.5)
    mb.prism(blue.buffer(-0.12), PLAY_Z, PLAY_Z + 0.01, 'Rubber blue', 'Rubber blue')
    z = PLAY_Z + 0.01
    geodesic_dome(mb, *DOME, z)
    play_tower(mb, *TOWER, z)
    swing_set(mb, *SWINGS, z)


def _rot_to_z(v):
    """Rotation matrix taking unit vector v onto +z."""
    v = np.array(v, float) / np.linalg.norm(v)
    zax = np.array([0, 0, 1.0])
    c = float(v @ zax)
    axis = np.cross(v, zax)
    s = np.linalg.norm(axis)
    if s < 1e-9:
        return np.eye(3)
    axis /= s
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + K * s + K @ K * (1 - c)


def geodesic_dome(mb, x, y, r, z, mat='Dark lattice', stretch=1.35):
    """2V geodesic half-dome of struts (a pentagon vertex on top, a 10-vertex ring on the ground)."""
    from .deck.common import rod
    verts, faces = icosphere(1)
    R = _rot_to_z(verts[5])                     # (0, 1, t) normalised: an original icosahedron vertex
    P = [R @ np.array(v) for v in verts]
    edges = set()
    for f in faces:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            edges.add((min(a, b), max(a, b)))
    for a, b in edges:
        if P[a][2] < -0.02 or P[b][2] < -0.02:
            continue
        pa = (x + P[a][0] * r, y + P[a][1] * r, z + max(P[a][2], 0.0) * r * stretch)
        pb = (x + P[b][0] * r, y + P[b][1] * r, z + max(P[b][2], 0.0) * r * stretch)
        rod(mb, pa, pb, 0.05, mat, sides=4)
    # hubs at the nodes
    for p in P:
        if p[2] >= -0.02:
            c = (x + p[0] * r, y + p[1] * r, z + max(p[2], 0.0) * r * stretch)
            mb.box(c[0], c[1], c[2] - 0.06, 0.13, 0.13, 0.12, mat)


def play_tower(mb, x, y, rot, z):
    """Timber play tower: four posts, a deck at 1.4 m, rails, a little pitched roof and a slide."""
    from .deck.common import rod
    c, s = math.cos(rot), math.sin(rot)
    L = lambda u, v: (x + c * u - s * v, y + s * u + c * v)
    h_deck, h_post, half = 1.4, 3.2, 0.8
    corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
    for u, v in corners:
        px, py = L(u, v)
        mb.box(px, py, z, 0.14, 0.14, h_post, 'Dark lattice', rot=rot)
    px, py = L(0, 0)
    mb.box(px, py, z + h_deck, 2 * half + 0.1, 2 * half + 0.1, 0.1, 'Wood', rot=rot)
    # rails on three sides (the slide leaves from the +u side)
    for (u0, v0), (u1, v1) in [((-half, -half), (-half, half)), ((-half, half), (half, half)), ((-half, -half), (half, -half))]:
        for hz in (0.5, 0.9):
            rod(mb, (*L(u0, v0), z + h_deck + hz), (*L(u1, v1), z + h_deck + hz), 0.03, 'Dark lattice', sides=4)
    # pitched roof (two planes) and gables
    ridge = z + h_post + 0.75
    e = half + 0.2
    a0, a1, b0, b1 = L(-e, -e), L(e, -e), L(e, e), L(-e, e)
    m0, m1 = L(-e, 0), L(e, 0)
    for quad in ([(*a0, z + h_post), (*a1, z + h_post), (*m1, ridge), (*m0, ridge)],
                 [(*b0, z + h_post), (*b1, z + h_post), (*m0, ridge), (*m1, ridge)]):
        mb.face(quad, 'Planter')
        mb.face(quad[::-1], 'Planter')
    # ladder on the -u side
    for v in (-0.3, 0.3):
        rod(mb, (*L(-half - 0.45, v), z), (*L(-half, v), z + h_deck), 0.03, 'Wood', sides=4)
    for k in range(1, 5):
        f = k / 5
        rod(mb, (*L(-half - 0.45 * (1 - f), -0.3), z + h_deck * f), (*L(-half - 0.45 * (1 - f), 0.3), z + h_deck * f), 0.025, 'Wood', sides=4)
    # slide: chute with low side walls from the deck edge down to the ground on the +u side
    run = 2.8
    pts = []
    for k in range(7):
        f = k / 6
        hh = h_deck * (1 - f) ** 1.2 * (1 - 0.15 * math.sin(math.pi * f)) + 0.25 * f * (1 - f)
        pts.append((half + run * f, max(hh, 0.18) if k == 6 else hh))
    for (u0, h0), (u1, h1) in zip(pts[:-1], pts[1:]):
        p = [(*L(u0, -0.3), z + h0), (*L(u1, -0.3), z + h1), (*L(u1, 0.3), z + h1), (*L(u0, 0.3), z + h0)]
        mb.face(p[::-1], 'Play orange')
        mb.face(p, 'Play orange')
        for v in (-0.32, 0.32):
            w = [(*L(u0, v), z + h0), (*L(u1, v), z + h1), (*L(u1, v), z + h1 + 0.22), (*L(u0, v), z + h0 + 0.22)]
            mb.face(w, 'Play orange')
            mb.face(w[::-1], 'Play orange')
    rod(mb, (*L(pts[-1][0] - 0.2, 0), z), (*L(pts[-1][0] - 0.2, 0), z + pts[-1][1]), 0.04, 'Metal', sides=4)


def swing_set(mb, x, y, rot, z):
    """A-frame swing: two splayed leg pairs, a top beam, two seats on chains."""
    from .deck.common import rod
    c, s = math.cos(rot), math.sin(rot)
    L = lambda u, v: (x + c * u - s * v, y + s * u + c * v)
    span, h, splay = 3.6, 2.5, 0.85
    for u in (-span / 2, span / 2):
        top = (*L(u, 0), z + h)
        for v in (-splay, splay):
            rod(mb, (*L(u, v), z), top, 0.06, 'Dark lattice', sides=5)
        rod(mb, (*L(u, -splay * 0.55), z + h * 0.35), (*L(u, splay * 0.55), z + h * 0.35), 0.04, 'Dark lattice', sides=4)
    rod(mb, (*L(-span / 2 - 0.15, 0), z + h), (*L(span / 2 + 0.15, 0), z + h), 0.07, 'Dark lattice', sides=5)
    for u in (-0.8, 0.8):
        for du in (-0.22, 0.22):
            rod(mb, (*L(u + du, 0), z + h), (*L(u + du, 0), z + 0.48), 0.012, 'Metal', sides=3)
        sx, sy = L(u, 0)
        mb.box(sx, sy, z + 0.42, 0.5, 0.2, 0.06, 'Shop frame', rot=rot)
