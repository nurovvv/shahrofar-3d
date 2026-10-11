"""Street level in front of the shop front and the ground playground (pool-deck render, render 2).

    promenade   grey cobble strip along the shop front, light paving out to the river-side and east
                roads, long lens-shaped planters (lawn, round shrubs, small trees) following the curve,
                white spherical bollards along the kerb
    playground  on the blue part of the ground playground (site.playground): deep blue rubber,
                a dark-brown hexagonal climbing pavilion (splayed legs, ring beam, pyramid roof, every
                face a triangular lattice), a timber play tower with a slide and a swing set; the
                generic site play towers that stood on the blue part are taken out

build(mats, col, rnd, roads) is called from site.build_site after the street furniture.
"""
import math
import random

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from .geom import MeshBuilder, biggest, get_collection, make_object

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
# as on the render seen from the river: the swing left of the pavilion, the play tower in front of it
PAVILION = (7.0, 203.0)              # hexagonal climbing pavilion: ~6.6 m across, ring beam +3.0, apex +5.0
PAV_R0, PAV_R1, PAV_H1, PAV_H2 = 2.6, 3.3, 3.0, 5.0
TOWER = (10.6, 209.8, math.pi / 2)   # x, y, rotation (the slide runs out along the rotated +x: north)
SWINGS = (13.4, 201.4, math.radians(88))
# site.playground's generic wooden play towers (x, y) standing on the blue part: replaced by the above
SITE_TOWERS_ON_BLUE = [(8.0, 214.0), (11.0, 205.0), (5.0, 208.0)]


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
    try:
        n = clear_site_towers()
        print(f'[street] playground: took {n} faces of site play towers off the blue area')
    except Exception as e:  # the site towers stay
        print('[street] playground: could not clear the site play towers:', e)


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
    pavilion(mb, *PAVILION, z)
    play_tower(mb, *TOWER, z)
    swing_set(mb, *SWINGS, z)


def clear_site_towers(half=1.47):
    """Delete the faces of site.playground's wooden play towers that stand on the blue part
    (every vertex inside the tower's 2.8 m square, above the play surface) from 'Site ground'."""
    import bmesh
    import bpy
    ob = bpy.data.objects.get('Site ground')
    if ob is None:
        return 0
    M = ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    kill = []
    for f in bm.faces:
        co = [M @ v.co for v in f.verts]
        if max(c.z for c in co) <= 0.2:
            continue
        for cx, cy in SITE_TOWERS_ON_BLUE:
            if all(abs(c.x - cx) <= half and abs(c.y - cy) <= half for c in co):
                kill.append(f)
                break
    if kill:
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bm.to_mesh(ob.data)
        ob.data.update()
    bm.free()
    return len(kill)


def strut(mb, p0, p1, r, mat, sides=4):
    """Open prism between two 3D points (no end caps: they meet at nodes)."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    if L < 1e-6:
        return
    d /= L
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(d, a)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    ring = [(math.cos(2 * math.pi * (k + 0.5) / sides), math.sin(2 * math.pi * (k + 0.5) / sides)) for k in range(sides)]
    b0 = [tuple(p0 + r * (c * u + s * v)) for c, s in ring]
    b1 = [tuple(p1 + r * (c * u + s * v)) for c, s in ring]
    for k in range(sides):
        j = (k + 1) % sides
        mb.face([b0[k], b0[j], b1[j], b1[k]], mat)


def tri_lattice(a, b, c, n):
    """Edges of triangle abc split into n x n small triangles (3 directions of struts)."""
    a, b, c = (np.array(x, float) for x in (a, b, c))
    P = {}
    for i in range(n + 1):
        for j in range(n + 1 - i):
            P[i, j] = a + (b - a) * (i / n) + (c - a) * (j / n)
    E = []
    for (i, j), p in P.items():
        for di, dj in ((1, 0), (0, 1), (-1, 1)):
            q = P.get((i + di, j + dj))
            if q is not None:
                E.append((p, q))
    return E


def pavilion(mb, x, y, z, mat='Dark lattice'):
    """Hexagonal climbing pavilion as on the render: six legs splay out from a ground hexagon to a
    ring beam, a six-sided pyramid roof rises to the apex, and every wall and roof face is filled
    with a triangular lattice; one wall is open below 2 m as the way in."""
    ang = [math.radians(30 + 60 * k) for k in range(6)]
    G = [np.array([x + PAV_R0 * math.cos(a), y + PAV_R0 * math.sin(a), z]) for a in ang]
    R = [np.array([x + PAV_R1 * math.cos(a), y + PAV_R1 * math.sin(a), z + PAV_H1]) for a in ang]
    A = np.array([x, y, z + PAV_H2])
    heavy = []
    for k in range(6):
        heavy += [(G[k], R[k]), (R[k], R[(k + 1) % 6]), (R[k], A)]
    edges = []
    door = 0                                   # the wall facing north-east (towards the play tower)
    for k in range(6):
        g0, g1, r0, r1 = G[k], G[(k + 1) % 6], R[k], R[(k + 1) % 6]
        if k == door:
            f = 2.0 / PAV_H1
            g0, g1 = g0 + (r0 - g0) * f, g1 + (r1 - g1) * f
            heavy.append((g0, g1))
            edges += tri_lattice(g0, g1, r1, 2) + tri_lattice(g0, r1, r0, 2)
        else:
            edges += tri_lattice(g0, g1, r1, 3) + tri_lattice(g0, r1, r0, 3)
        edges += tri_lattice(r0, r1, A, 4)
    seen = set()

    def key(p, q):
        a, b = tuple(np.round(p, 3)), tuple(np.round(q, 3))
        return (a, b) if a <= b else (b, a)
    for p, q in heavy:
        seen.add(key(p, q))
        strut(mb, p, q, 0.09, mat, sides=6)
    for p, q in edges:
        k = key(p, q)
        if k in seen:
            continue
        seen.add(k)
        # skip pieces lying on a heavy member (subdivided legs / ring / hips)
        on_heavy = False
        for h0, h1 in heavy:
            d = h1 - h0
            L2 = float(d @ d)
            t0 = float((p - h0) @ d) / L2
            t1 = float((q - h0) @ d) / L2
            if -1e-6 <= t0 <= 1 + 1e-6 and -1e-6 <= t1 <= 1 + 1e-6 and \
                    np.linalg.norm(h0 + d * t0 - p) < 1e-3 and np.linalg.norm(h0 + d * t1 - q) < 1e-3:
                on_heavy = True
                break
        if not on_heavy:
            strut(mb, p, q, 0.055, mat)
    # feet and apex cap
    for g in G:
        mb.box(g[0], g[1], z, 0.28, 0.28, 0.12, mat)
    mb.blob(A[0], A[1], A[2] + 0.05, 0.16, 0.16, 0.16, mat, subdiv=1)


def play_tower(mb, x, y, rot, z):
    """Timber play tower: four posts, a boarded den under a deck at 1.4 m, boarded sides and rails,
    a checkered pitched roof and a slide, all in dark red timber as on the render."""
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
        Q = [np.array(q) for q in quad]
        n = 3                                   # checkered roof (light / dark shingles), as on the render
        for i in range(n):
            for j in range(n):
                def at(fu, fv):
                    lo = Q[0] + (Q[1] - Q[0]) * fu
                    hi = Q[3] + (Q[2] - Q[3]) * fu
                    return tuple(lo + (hi - lo) * fv)
                cell = [at(i / n, j / n), at((i + 1) / n, j / n), at((i + 1) / n, (j + 1) / n), at(i / n, (j + 1) / n)]
                mat = 'Lounger' if (i + j) % 2 == 0 else 'Dark lattice'
                mb.face(cell, mat)
                mb.face(cell[::-1], mat)
    # boarded den under the deck and boarded sides on the deck (dark red timber)
    for v in (-half, half):
        for z0, z1 in ((0.0, h_deck), (h_deck + 0.1, h_deck + 0.85)):
            w = [(*L(-half, v), z + z0), (*L(half, v), z + z0), (*L(half, v), z + z1), (*L(-half, v), z + z1)]
            mb.face(w, 'Terracotta dark')
            mb.face(w[::-1], 'Terracotta dark')
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
        mb.face(p[::-1], 'Terracotta dark')
        mb.face(p, 'Terracotta dark')
        for v in (-0.32, 0.32):
            w = [(*L(u0, v), z + h0), (*L(u1, v), z + h1), (*L(u1, v), z + h1 + 0.22), (*L(u0, v), z + h0 + 0.22)]
            mb.face(w, 'Terracotta dark')
            mb.face(w[::-1], 'Terracotta dark')
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
