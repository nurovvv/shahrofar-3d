"""Playground decks: the east deck by block B (+15.0) and the west wing roof between blocks B and V
(+20.5), after the marketing render of the pool deck (render 2) and the first aerial render.

Grey irregular cobble paving; light-timber geodesic lattice pergolas over round timber decks with a
round seat; a timber play frame with a swing pair and a climbing net; a low rope climbing dome;
outdoor fitness bars (green and yellow); hexagonal stools; benches; round planters with grass and
trees, one big tree; swan-neck lamps. The west roof adds a play tower with a slide.
"""
import math
import random

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from . import common as C

TOWER_CLEAR = 1.25   # keep props this far from the tower outlines (with balconies)
STRUT = 0.085        # pergola strut radius
STONE_MATS = (('Cobble', 0.30), ('Bridge', 0.32), ('Kerb', 0.30), ('Sidewalk', 0.08))
JOINT = 'Cobble joint'   # mid grey, a little darker than the stones (not the near-black asphalt)
MARGIN = 1.5         # planted margin along the play side of the diagonal planter (beyond its 2.8 m)
STRIP_CROSSING = (31.0, 2.4)   # the planter's crossing (edge.CROSSING): distance from its outer end, width
STRIP_WALK = 1.15              # edge.WALK: cobble walkway inside the parapet, the planter stops there


# ----------------------------------------------------------------------------
# props
# ----------------------------------------------------------------------------

def lattice_dome(R, H, rise, rot=0.0):
    """Frequency-2 hexagonal geodesic cap: 19 nodes (centre, 6, 12 around the rim) and its 42 edges.

    The triangular lattice of a hexagon of side 2 is mapped onto a disc (ring k -> radius k/2 R) and
    lifted onto a spherical cap with its rim at H - rise and its apex at H. Nodes: (x, y, z, ring, angle)."""
    Rs = (R * R + rise * rise) / (2 * rise)
    idx, nodes = {}, []
    for q in range(-2, 3):
        for r in range(-2, 3):
            k = max(abs(q), abs(r), abs(q + r))
            if k > 2:
                continue
            ang = math.atan2(r * math.sqrt(3) / 2, q + 0.5 * r) + rot if k else 0.0
            rho = R * k / 2
            z = H - Rs + math.sqrt(max(Rs * Rs - rho * rho, 0.0))
            idx[(q, r)] = len(nodes)
            nodes.append((rho * math.cos(ang), rho * math.sin(ang), z, k, ang))
    edges = []
    for (q, r), i in idx.items():
        for dq, dr in ((1, 0), (0, 1), (-1, 1)):
            j = idx.get((q + dq, r + dr))
            if j is not None:
                edges.append((i, j))
    return nodes, edges


def pergola(mb, x, y, z, s=1.0, rot=0.0, mat='Lattice wood', deck='Lattice wood', dome=False):
    """Geodesic lattice pergola: a shallow timber dome (5.5 m across, 3.3 m high at s=1) on six forked
    legs over a round timber deck with a white round seat in the middle. dome=True gives a deeper
    half-dome on short legs (the gazebo of the west roof)."""
    R, deck_r = 2.75 * s, 2.9 * s
    rise, H = (0.7 * R, 0.7 * R + 1.5) if dome else (0.85 * s, 3.3 * s ** 0.5)
    disc = Point(x, y).buffer(deck_r, quad_segs=10)
    mb.prism(disc, z, z + 0.14, 'Wood', None)
    mb.polygon_face(disc.buffer(-0.12), z + 0.15, deck)
    mb.prism(disc.difference(disc.buffer(-0.12)), z + 0.14, z + 0.165, 'Wood', 'Wood')
    z0 = z + 0.15
    nodes, edges = lattice_dome(R, H, rise, rot=rot)
    P = [(x + px, y + py, z0 + pz) for px, py, pz, _, _ in nodes]
    for i, j in edges:
        C.rod(mb, P[i], P[j], STRUT, mat, sides=4)
    # six forked legs: a post from the deck, splitting into two arms to neighbouring rim nodes
    rim = sorted([(a % (2 * math.pi), i) for i, (_, _, _, k, a) in enumerate(nodes) if k == 2])
    for m in range(6):
        i0, i1 = rim[2 * m][1], rim[(2 * m + 1) % 12][1]
        a0, a1 = nodes[i0][4], nodes[i1][4]
        a = math.atan2(math.sin(a0) + math.sin(a1), math.cos(a0) + math.cos(a1))
        rr = R * 0.86
        foot = (x + rr * math.cos(a), y + rr * math.sin(a), z0)
        knee = (x + rr * math.cos(a), y + rr * math.sin(a), z0 + (H - rise) * 0.66)
        C.rod(mb, foot, knee, STRUT * 1.35, mat, sides=4)
        C.rod(mb, knee, P[i0], STRUT, mat, sides=4)
        C.rod(mb, knee, P[i1], STRUT, mat, sides=4)
    round_seat(mb, x, y, z0, r=0.85 * s ** 0.5)


def round_seat(mb, x, y, z, r=0.85):
    """White round seat around a little planter (the seat/table in the middle of each pergola)."""
    ring = Point(x, y).buffer(r, quad_segs=6)
    hole = Point(x, y).buffer(r - 0.38, quad_segs=6)
    mb.prism(ring.difference(hole), z, z + 0.42, 'Planter', 'Lamp white')
    mb.polygon_face(hole, z + 0.36, 'Shrub')
    mb.blob(x, y, z + 0.42, r - 0.42, r - 0.42, 0.22, 'Shrub', subdiv=1)


def rope_dome(mb, x, y, z, R=1.6, H=1.8, rot=0.0):
    """Low climbing dome of orange rope on timber feet."""
    nodes, edges = lattice_dome(R, H, rise=H * 0.95, rot=rot)
    P = [(x + px, y + py, z + pz) for px, py, pz, _, _ in nodes]
    for i, j in edges:
        C.rod(mb, P[i], P[j], 0.04, 'Play orange', sides=4)
    for i, (px, py, pz, k, a) in enumerate(nodes):
        if k == 2:
            C.rod(mb, (x + px, y + py, z), P[i], 0.06, 'Lattice wood', sides=4)


def hex_stool(mb, x, y, z, r=0.32, h=0.42, rot=0.0):
    """Hexagonal stool: white base, timber top."""
    hexa = Polygon([(x + r * math.cos(rot + k * math.pi / 3), y + r * math.sin(rot + k * math.pi / 3)) for k in range(6)])
    mb.prism(hexa.buffer(-0.03, join_style='mitre'), z, z + h - 0.07, 'Planter', None)
    mb.prism(hexa, z + h - 0.07, z + h, 'Wood', 'Wood')


def _local(x, y, z, rot):
    c, s = math.cos(rot), math.sin(rot)
    return lambda u, v, h=0.0: (x + c * u - s * v, y + s * u + c * v, z + h)


def play_frame(mb, x, y, z, rot=0.0, L=4.4, W=1.7, H=2.5):
    """Timber play frame: six posts and top beams; a swing pair in one bay, a deck with a climbing net
    and a ladder in the other, orange rope panels and post caps."""
    P = _local(x, y, z, rot)
    wood = 'Lattice wood'
    us = (-L / 2, 0.0, L / 2)
    for u in us:
        for v in (-W / 2, W / 2):
            C.rod(mb, P(u, v), P(u, v, H), 0.08, wood, sides=4)
            C.rod(mb, P(u, v, H), P(u, v, H + 0.14), 0.1, 'Play orange', sides=4)
    for v in (-W / 2, W / 2):
        C.rod(mb, P(-L / 2, v, H - 0.06), P(L / 2, v, H - 0.06), 0.065, wood, sides=4)
    for u in us:
        C.rod(mb, P(u, -W / 2, H - 0.06), P(u, W / 2, H - 0.06), 0.065, wood, sides=4)
    C.rod(mb, P(0, 0, H - 0.06), P(L / 2, 0, H - 0.06), 0.065, wood, sides=4)
    # swing pair
    for u in (L * 0.13, L * 0.37):
        for dv in (-0.22, 0.22):
            C.rod(mb, P(u, dv, H - 0.1), P(u, dv, 0.5), 0.015, 'Metal', sides=3)
        mb.box(*P(u, 0)[:2], z + 0.46, 0.22, 0.55, 0.05, 'Play orange', rot=rot)
    # deck bay: platform, rope net on the long side, rope rails on the far side, ladder at the end
    mb.box(*P(-L / 4, 0)[:2], z + 1.05, L / 2, W, 0.09, wood, rot=rot)
    for k in range(6):
        u = -L / 2 + 0.2 + k * (L / 2 - 0.4) / 5
        C.rod(mb, P(u, -W / 2 - 0.06, 0.05), P(u, -W / 2 - 0.06, H - 0.15), 0.03, 'Play orange', sides=3)
    for k in range(5):
        C.rod(mb, P(-L / 2, -W / 2 - 0.06, 0.3 + k * 0.45), P(0, -W / 2 - 0.06, 0.3 + k * 0.45), 0.03, 'Play orange', sides=3)
    for k in range(3):
        C.rod(mb, P(-L / 2, W / 2 + 0.06, 1.4 + k * 0.3), P(0, W / 2 + 0.06, 1.4 + k * 0.3), 0.03, 'Play orange', sides=3)
    for v in (-0.35, 0.35):
        C.rod(mb, P(-L / 2 - 0.08, v, 0), P(-L / 2 - 0.08, v, 1.1), 0.04, wood, sides=4)
    for k in range(5):
        C.rod(mb, P(-L / 2 - 0.08, -0.35, 0.22 + k * 0.2), P(-L / 2 - 0.08, 0.35, 0.22 + k * 0.2), 0.03, wood, sides=4)


def play_tower(mb, x, y, z, rot=0.0):
    """Timber play tower with an orange pyramid roof, an orange slide and a ladder (west roof)."""
    P = _local(x, y, z, rot)
    wood = 'Lattice wood'
    a, hp, H = 0.85, 1.3, 2.9
    for u in (-a, a):
        for v in (-a, a):
            C.rod(mb, P(u, v), P(u, v, H), 0.08, wood, sides=4)
    mb.box(*P(0, 0)[:2], z + hp - 0.1, 2 * a, 2 * a, 0.1, wood, rot=rot)
    for (u0, v0), (u1, v1) in [((-a, -a), (a, -a)), ((-a, a), (a, a)), ((-a, -a), (-a, a))]:
        for h in (hp + 0.45, hp + 0.85):
            C.rod(mb, P(u0, v0, h), P(u1, v1, h), 0.035, 'Play orange', sides=4)
    apex = P(0, 0, H + 0.9)
    eaves = [P(-a - 0.2, -a - 0.2, H), P(a + 0.2, -a - 0.2, H), P(a + 0.2, a + 0.2, H), P(-a - 0.2, a + 0.2, H)]
    for k in range(4):
        mb.face([eaves[k], eaves[(k + 1) % 4], apex], 'Play orange')
    # slide off the open side (+u), ladder on the opposite side
    w, L = 0.3, 2.6
    q = [P(a, -w, hp), P(a + L, -w, 0.3), P(a + L, w, 0.3), P(a, w, hp)]
    mb.face(q, 'Play orange')
    mb.face(q[::-1], 'Play orange')
    for v in (-w, w):
        C.rod(mb, P(a, v, hp + 0.25), P(a + L, v, 0.55), 0.04, 'Play orange', sides=4)
        C.rod(mb, P(a + L * 0.75, v, 0), P(a + L * 0.75, v, 0.6), 0.04, wood, sides=4)
    for k in range(5):
        C.rod(mb, P(-a - 0.1, -0.3, 0.25 + k * 0.22), P(-a - 0.1, 0.3, 0.25 + k * 0.22), 0.03, wood, sides=4)


def fitness(mb, x, y, z, rot=0.0):
    """Outdoor fitness station: pull-up bars, parallel bars, a twister and a sit-up bench."""
    P = _local(x, y, z, rot)
    G, Y = 'Fitness green', 'Fitness yellow'
    for u in (-2.2, -1.1, 0.0):
        C.rod(mb, P(u, 0), P(u, 0, 2.4), 0.065, G, sides=6)
    C.rod(mb, P(-2.2, 0, 2.2), P(-1.1, 0, 2.2), 0.035, Y, sides=6)
    C.rod(mb, P(-1.1, 0, 1.9), P(0.0, 0, 1.9), 0.035, Y, sides=6)
    for u in (0.9, 2.5):
        for v in (-0.3, 0.3):
            C.rod(mb, P(u, v), P(u, v, 1.15), 0.05, Y, sides=6)
    for v in (-0.3, 0.3):
        C.rod(mb, P(0.9, v, 1.15), P(2.5, v, 1.15), 0.04, G, sides=6)
    C.rod(mb, P(1.6, 1.6), P(1.6, 1.6, 1.4), 0.065, G, sides=6)
    C.rod(mb, P(1.25, 1.6, 1.3), P(1.95, 1.6, 1.3), 0.035, Y, sides=6)
    mb.prism(Point(*P(1.6, 1.15)[:2]).buffer(0.3, quad_segs=3), z, z + 0.12, Y, Y)
    C.rod(mb, P(-1.2, 1.5, 0.3), P(0.4, 1.5, 0.75), 0.17, 'Play orange', sides=4)
    for u, h in ((-1.1, 0.3), (0.3, 0.72)):
        C.rod(mb, P(u, 1.5), P(u, 1.5, h), 0.045, G, sides=4)


def deck_tree(mb, x, y, z, h, r, leaf, rnd):
    """Planter tree in the language of common.tree, lighter on triangles: one fine crown clump and
    three coarser ones around it."""
    C.rod(mb, (x, y, z), (x, y, z + h * 0.55), 0.12, 'Trunk', sides=5)
    a0 = rnd.uniform(0, 2 * math.pi)
    for k in range(3):
        a = a0 + k * 2.1
        C.rod(mb, (x, y, z + h * 0.45), (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z + h * 0.68), 0.055, 'Trunk', sides=4)
    mb.blob(x, y, z + h * 0.72, r, r, r * 0.85, leaf, subdiv=2, jitter=0.13, rnd=rnd)
    for k in range(3):
        a = a0 + 1.0 + k * 2.1
        rr = r * rnd.uniform(0.58, 0.72)
        mb.blob(x + math.cos(a) * r * 0.45, y + math.sin(a) * r * 0.45, z + h * rnd.uniform(0.66, 0.86), rr, rr, rr * 0.85,
                leaf, subdiv=1, jitter=0.16, rnd=rnd)


def planter_tree(mb, x, y, z, rnd, r=1.3, h=4.6, crown=2.0, leaf='Leaves light'):
    crown = max(crown, h * 0.42)
    C.planter(mb, Point(x, y).buffer(r, quad_segs=6), z, 0.42)
    deck_tree(mb, x, y, z + 0.36, h, crown, leaf, rnd)


def big_tree(mb, x, y, z, rnd, h=7.4, r=3.4):
    C.planter(mb, Point(x, y).buffer(1.5, quad_segs=8), z, 0.45)
    C.tree(mb, x, y, z + 0.38, h, r, 'Leaves light', rnd)


# ----------------------------------------------------------------------------
# paving
# ----------------------------------------------------------------------------

def joint_mat():
    """'Cobble joint' (a mid grey a little darker than the stones) when materials.py has it."""
    try:
        from ..materials import SPECS
    except Exception:
        return JOINT
    return JOINT if JOINT in SPECS else 'Bridge'


def cobble(mb, zone, z, rnd, keep_out, size=0.42, angle=0.0, joint=0.035, merge=0.10, split=0.27):
    """Grey cobble paving: the 'Cobble' slab, a mid-grey joint layer, and irregular stones over it (a
    jittered grid of quads, a few merged in pairs, some split into triangles) in a few close greys."""
    C.pave(mb, zone, z, 'Cobble')
    area = zone.buffer(-0.05, join_style='mitre').difference(keep_out)
    if area.is_empty:
        return 0
    zj, zs = z + C.PAVE_T + 0.006, z + C.PAVE_T + 0.014
    mb.polygon_face(area.simplify(0.05), zj, joint_mat())
    # stones are laid out in a frame turned by `angle` about the zone's centroid
    c = zone.centroid
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
            if r < merge and i + 1 < nx:   # long stone over two cells, a slight kink in its long edges
                polys.append([V(i, j), V(i + 1, j), V(i + 2, j), V(i + 2, j + 1), V(i + 1, j + 1), V(i, j + 1)])
                i += 2
                continue
            q = [V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)]
            if r < merge + split:          # split into two triangles
                d = rnd.random() < 0.5
                polys += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]] if d else [[q[0], q[1], q[3]], [q[1], q[2], q[3]]]
            else:
                polys.append(q)
            i += 1
    stones = shapely.polygons([shapely.linearrings(p) for p in polys])
    stones = shapely.buffer(stones, -joint / 2, join_style='mitre')
    stones = affinity_rotate_all(stones, angle, c)
    shapely.prepare(area)
    inside = shapely.contains(area, stones)
    touch = shapely.intersects(area, stones) & ~inside
    n = 0
    mats = [m for m, _ in STONE_MATS]
    w = np.cumsum([p for _, p in STONE_MATS])
    for st, ins, tch in zip(stones, inside, touch):
        if not (ins or tch) or st.is_empty:
            continue
        g = st if ins else st.intersection(area)
        if g.is_empty or g.area < 0.03:
            continue
        mat = mats[int(np.searchsorted(w, rnd.random() * w[-1]))]
        for p in getattr(g, 'geoms', [g]):
            if p.geom_type == 'Polygon' and p.area > 0.03:
                mb.polygon_face(p, zs, mat)
                n += 1
    return n


def affinity_rotate_all(geoms, angle, origin):
    if not angle:
        return geoms
    return np.array([affinity.rotate(g, angle, origin=origin, use_radians=True) for g in geoms])


# ----------------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------------

def _frame(ctx):
    """Frame along the planter strip: P(s, t) is s metres back from the front edge along the strip
    and t metres from its centre line towards block B; also the strip's and the normal's angles."""
    a, b = list(ctx['strip_line'].coords)[0], list(ctx['strip_line'].coords)[-1]
    F, K = (np.array(a), np.array(b)) if a[0] > b[0] else (np.array(b), np.array(a))
    u = (K - F) / np.linalg.norm(K - F)
    n = np.array([-u[1], u[0]])
    if (np.array(ctx['towers']['B'].centroid.coords[0]) - F) @ n < 0:
        n = -n

    def P(s, t):
        p = F + u * s + n * t
        return float(p[0]), float(p[1])
    return P, math.atan2(u[1], u[0]), math.atan2(n[1], n[0])


def east_items(ctx):
    P, au, an = _frame(ctx)
    it = []
    add = lambda kind, xy, r, **kw: it.append(dict(kind=kind, xy=xy, r=r, **kw))
    # two pergolas against the planted margin of the strip (it ends at t = 1.4 + MARGIN): one at the
    # back by block B's corner, one nearer the front
    add('pergola', P(25.3, 6.0), 2.9, rot=au)
    add('pergola', P(8.3, 6.0), 2.9, rot=au + 0.3)
    add('frame', (44.9, 242.7), 2.6, rot=au + 0.1)
    add('rope', (47.6, 251.0), 1.7, rot=0.2)
    add('big_tree', (52.4, 249.6), 1.5)
    add('fitness', (50.6, 260.4), 2.6, rot=math.radians(70))
    for xy in [(49.4, 241.2), (50.2, 241.9), (49.3, 242.4), (50.3, 245.0), (51.1, 245.4)]:
        add('stool', xy, 0.32, rot=0.3 * len(it))
    for xy, h in [((43.4, 248.6), 4.8), ((46.3, 256.5), 4.6), ((59.0, 254.0), 4.4), ((54.8, 263.0), 4.5),
                  ((44.8, 265.5), 5.0), ((33.5, 276.0), 4.8), ((25.0, 280.5), 4.6)]:
        add('planter', xy, 1.3, h=h)
    add('bench', (60.2, 249.8), 1.0, rot=math.radians(-71))
    add('bench', (52.5, 267.0), 1.0, rot=math.radians(-54))
    add('bench', (29.5, 282.0), 1.0, rot=math.radians(-20))
    add('bench', P(14.5, 3.45), 1.0, rot=au)          # back against the margin hedge
    add('lamp', P(12.3, 2.0), 0.3, rot=an, bed=True)  # in the margin's lawn, leaning over the cobble
    add('lamp', P(20.0, 2.0), 0.3, rot=an, bed=True)
    add('lamp', (57.0, 258.5), 0.3, rot=math.radians(200))
    add('lamp', (38.5, 275.0), 0.3, rot=math.radians(-110))
    return it


def west_items(ctx):
    it = []
    add = lambda kind, xy, r, **kw: it.append(dict(kind=kind, xy=xy, r=r, **kw))
    # between V and B (the playground of the first aerial render): a big pergola at the back (south),
    # the rope dome in the middle, the play tower, play frame and fitness towards the river side
    add('pergola', (-3.0, 250.0), 3.65, rot=0.2, s=1.25, deck='Wood', dome=True)
    add('rope', (-1.0, 266.5), 1.7, rot=0.0)
    add('tower', (-7.0, 281.5), 2.4, rot=0.0)
    add('frame', (1.5, 279.5), 2.6, rot=math.radians(90))
    add('fitness', (12.0, 280.0), 2.6, rot=0.0)
    for xy, h in [((-14.0, 257.5), 5.6), ((-11.0, 261.0), 5.0), ((-14.0, 246.5), 5.2), ((4.0, 247.5), 5.4),
                  ((-15.0, 279.5), 5.6), ((5.0, 270.0), 5.0), ((18.5, 279.5), 5.4), ((-8.0, 271.0), 4.8)]:
        add('planter', xy, 1.3, h=h, leaf='Leaves')
    for xy in [(-9.5, 254.5), (-8.7, 255.3), (-9.8, 255.7), (1.2, 259.3), (2.0, 260.0)]:
        add('stool', xy, 0.32, rot=0.4 * len(it))
    add('bench', (-14.5, 266.0), 1.0, rot=math.radians(90))
    add('bench', (3.2, 254.5), 1.0, rot=math.radians(80))
    add('bench', (8.0, 286.0), 1.0, rot=math.radians(-6))
    add('lamp', (-16.5, 252.0), 0.3, rot=0.0)
    add('lamp', (6.0, 262.5), 0.3, rot=math.pi)
    add('lamp', (-16.5, 272.0), 0.3, rot=0.0)
    add('lamp', (-2.0, 287.0), 0.3, rot=-math.pi / 2)
    # round the north and west sides of V: a second pergola, planters, benches, lamps
    add('pergola', (-28.5, 281.5), 2.9, rot=0.0, deck='Wood')
    for xy, h in [((-38.0, 279.5), 4.6), ((-53.8, 262.0), 4.4), ((-53.5, 248.0), 4.6)]:
        add('planter', xy, 1.3, h=h, leaf='Leaves')
    add('bench', (-33.5, 283.0), 1.0, rot=math.radians(15))
    add('bench', (-22.0, 285.0), 1.0, rot=math.radians(5))
    add('lamp', (-45.0, 278.0), 0.3, rot=-math.pi / 4)
    add('lamp', (-55.0, 255.0), 0.3, rot=0.0)
    return it


def check(items, zone, towers, label):
    """Props that fit: inside their zone and clear of the towers (others are left out, with a note,
    so a change of the zones never puts a prop into a facade)."""
    tw = unary_union(list(towers.values()))
    ok = []
    for d in items:
        fp = Point(d['xy']).buffer(d['r'])
        where = tuple(round(v, 1) for v in d['xy'])
        if not zone.buffer(0.05).contains(fp):
            print(f'[play] {label} {d["kind"]} at {where} sticks out of the zone: left out')
        elif fp.distance(tw) < TOWER_CLEAR - 0.05:
            print(f'[play] {label} {d["kind"]} at {where} is {fp.distance(tw):.2f} m from a tower: left out')
        else:
            ok.append(d)
    return ok


def plan(ctx):
    """2D footprints for checking the layout on a plan."""
    kinds = {'pergola': 'perg', 'big_tree': 'tree', 'planter': 'planter', 'lamp': 'lamp', 'bench': 'bench',
             'frame': 'frame', 'rope': 'frame', 'tower': 'frame', 'fitness': 'fit', 'stool': 'stool'}
    out = [(kinds[d['kind']], Point(d['xy']), d['r']) for d in east_items(ctx) + west_items(ctx)]
    out.append(('hedge', strip_margin(ctx)))
    out += [('misc', g) for g in tower_aprons(ctx).values()]
    return out


def build_items(mb, items, z, rnd):
    for d in items:
        (x, y), k, rot = d['xy'], d['kind'], d.get('rot', 0.0)
        if k == 'pergola':
            pergola(mb, x, y, z, s=d.get('s', 1.0), rot=rot, deck=d.get('deck', 'Lattice wood'), dome=d.get('dome', False))
        elif k == 'frame':
            play_frame(mb, x, y, z, rot=rot)
        elif k == 'tower':
            play_tower(mb, x, y, z, rot=rot)
        elif k == 'rope':
            rope_dome(mb, x, y, z, rot=rot)
        elif k == 'fitness':
            fitness(mb, x, y, z, rot=rot)
        elif k == 'big_tree':
            big_tree(mb, x, y, z, rnd)
        elif k == 'planter':
            planter_tree(mb, x, y, z, rnd, r=d['r'], h=d.get('h', 4.6), leaf=d.get('leaf', 'Leaves light'))
        elif k == 'stool':
            hex_stool(mb, x, y, z, rot=rot)
        elif k == 'bench':
            C.bench(mb, x, y, z, rot=rot)
        elif k == 'lamp':
            C.lamp(mb, x, y, z + (0.12 if d.get('bed') else 0.0), rot=rot)


def keep_out_of(items):
    return unary_union([Point(d['xy']).buffer(d['r'] + 0.05, quad_segs=4) for d in items
                        if d['kind'] in ('pergola', 'planter', 'big_tree')])


# ----------------------------------------------------------------------------
# cobble apron to the towers' glass, planted margin along the strip
# ----------------------------------------------------------------------------

def tower_aprons(ctx):
    """The podium slab between the playgrounds and the ground-floor glass of blocks B and V (under
    their balconies, outside every zone): {'east': +15.0 apron, 'west': +20.5 apron}. It is paved
    with the playground's cobble, so the stone runs right up to the glazing as on the render."""
    from .. import drawn
    plans = drawn.load_plans()
    east_base = ctx['podium'].difference(ctx['west_wing'])
    towers_u = unary_union(list(ctx['towers'].values())).buffer(1.0)
    # the +15.0 walkway in front of the west wing (edge.west_walk paves it)
    walk = east_base.difference(ctx['deck'].buffer(0.02)).difference(towers_u)
    levels = {
        'east': (east_base, ctx['play'], [ctx['pool'], ctx['strip'], ctx['edge_band'], walk]),
        'west': (ctx['west_wing'], ctx['west']['play'], [ctx['west']['edge_band']]),
    }
    out = {k: [] for k in levels}
    for key in ('B', 'V'):
        info, bp = drawn.TOWERS[key], plans[key]
        c = Polygon(bp['slab']).centroid           # as deck.tower_footprints places the 'slab'
        glass = drawn.P(bp['enclosure']).buffer(-0.3, join_style='mitre')   # the lobby glass line
        glass = affinity.translate(glass, -c.x, -c.y)
        glass = affinity.rotate(glass, drawn.SITE_ROT + bp['sheet_rot'], origin=(0, 0))
        glass = affinity.translate(glass, *info['centre'])
        ring = ctx['towers'][key].buffer(1.05).difference(glass.buffer(0.03))
        for lv, (base, play, others) in levels.items():
            ap = base.intersection(ring).difference(play)
            for g in others:
                if not g.is_empty:
                    ap = ap.difference(g.buffer(0.02))
            out[lv] += [g for g in getattr(ap, 'geoms', [ap]) if g.geom_type == 'Polygon' and g.area > 1.0]
    return {k: unary_union(v) if v else Polygon() for k, v in out.items()}


def strip_ends(ctx, P):
    """(outer end, inner end, crossing) of the diagonal planter along the frame's s axis, as the
    edge part lays it out: it runs into the edge band up to the walkway inside the parapet."""
    try:
        from . import edge
        crossing, walk = edge.CROSSING, edge.WALK
    except Exception:
        crossing, walk = STRIP_CROSSING, STRIP_WALK
    L = ctx['strip_line'].length
    room = ctx['deck'].difference(ctx['outer_line'].buffer(walk + 0.05))
    full = Polygon([P(-6, -1.4), P(L + 6, -1.4), P(L + 6, 1.4), P(-6, 1.4)]).intersection(room)
    F = np.array(P(0, 0))
    u = np.array(P(1, 0)) - F
    ss = [float((np.array(q) - F) @ u) for g in getattr(full, 'geoms', [full]) for q in g.exterior.coords]
    s_out, s_in = min(ss), max(ss)
    c0 = s_out + crossing[0]
    return s_out, s_in, (c0 - crossing[1] / 2, c0 + crossing[1] / 2)


def strip_margin(ctx):
    """Planted margin on the play side of the diagonal planter, MARGIN wide, so the strip reads as
    one broad green band with a clipped hedge along the cobble: from the edge band at the front to
    ~3 m short of the planter's inner end (the back passage stays open), broken at the crossing."""
    P, _, _ = _frame(ctx)
    s_out, s_in, (c0, c1) = strip_ends(ctx, P)
    t0, t1 = 1.3, 1.4 + MARGIN
    beds = []
    for s0, s1 in ((s_out - 6.0, c0 - 0.3), (c1 + 0.3, s_in - 3.0)):
        r = Polygon([P(s0, t0), P(s1, t0), P(s1, t1), P(s0, t1)])
        g = r.intersection(ctx['play']).difference(ctx['strip'].buffer(0.02))
        beds += [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon' and p.area > 1.0]
    return unary_union(beds) if beds else Polygon()


def margin_planting(mb, ctx, bed, items, z, rnd):
    """Lawn with a clipped hedge along its cobble side (and round its ends), shrubs and a few
    columnar trees between the hedge and the planter wall."""
    if bed.is_empty:
        return
    P, _, _ = _frame(ctx)
    F = np.array(P(0, 0))
    u, n = np.array(P(1, 0)) - F, np.array(P(0, 1)) - F
    C.lawn(mb, bed, z, kerb=0.14)
    zl = z + 0.12
    # hedge on every side but the planter's: the long side along the cobble and the ends
    strip_side = ctx['strip'].buffer(0.12)
    lamps = [np.array(d['xy']) for d in items if d['kind'] == 'lamp' and d.get('bed')]
    for g in getattr(bed, 'geoms', [bed]):
        edge = g.exterior.difference(strip_side)
        hd = g.intersection(edge.buffer(0.62, cap_style='flat', join_style='mitre')).buffer(-0.04, join_style='mitre')
        C.hedge(mb, hd, zl, h=0.72, w=0.6)
        # along the lawn between hedge and planter wall: shrubs, every fourth a columnar tree
        ss = [float((np.array(q) - F) @ u) for q in g.exterior.coords]
        s, k = min(ss) + 1.0, 0
        inner = g.buffer(-0.35)
        while s < max(ss) - 0.8:
            p = F + u * s + n * (1.4 + 0.45)
            if inner.contains(Point(*p)) and all(np.linalg.norm(p - q) > 0.9 for q in lamps):
                if k % 4 == 2:
                    C.tree(mb, p[0], p[1], zl, h=rnd.uniform(4.6, 5.4), r=rnd.uniform(0.95, 1.1),
                           leaf='Leaves light', rnd=rnd, kind='cone')
                else:
                    r = rnd.uniform(0.38, 0.5)
                    mb.blob(p[0], p[1], zl + r * 0.75, r, r, r * 0.85, rnd.choice(['Shrub', 'Leaves', 'Leaves light']),
                            subdiv=1, jitter=0.15, rnd=rnd)
                k += 1
            s += rnd.uniform(1.5, 1.9)


def check_bed(items, bed, label):
    """Props (other than the lamps meant for it) may not stand in the planted margin."""
    if bed.is_empty:
        return items
    ok = []
    for d in items:
        fp = Point(d['xy']).buffer(d['r'])
        if d['kind'] == 'bench':   # its seat and back, not the round clearance
            (x, y), rot = d['xy'], d.get('rot', 0.0)
            fp = affinity.rotate(Polygon([(x - 0.9, y - 0.25), (x + 0.9, y - 0.25), (x + 0.9, y + 0.3), (x - 0.9, y + 0.3)]),
                                 rot, origin=(x, y), use_radians=True)
        if not d.get('bed') and fp.intersects(bed) and fp.intersection(bed).area > 0.01:
            print(f'[play] {label} {d["kind"]} at {tuple(round(v, 1) for v in d["xy"])} stands in the strip margin: left out')
        else:
            ok.append(d)
    return ok


def build(mb, ctx):
    rnd = random.Random(7310)
    _, au, _ = _frame(ctx)
    try:
        aprons = tower_aprons(ctx)
    except Exception as e:  # the apron is a nicety; never lose the playground over it
        print(f'[play] no tower aprons ({e})')
        aprons = {}
    bed = strip_margin(ctx)
    n = 0
    for label, zone, z, items, size, ang, margin in [
            ('east', ctx['play'], ctx['z'], east_items(ctx), 0.42, au, bed),
            ('west', ctx['west']['play'], ctx['west']['z'], west_items(ctx), 0.55, 0.0, Polygon())]:
        items = check_bed(check(items, zone, ctx['towers'], label), margin, label)
        ap = aprons.get(label, Polygon())
        paved = zone if ap.is_empty else unary_union([zone, ap]).buffer(0.01, quad_segs=2).buffer(-0.01, quad_segs=2).simplify(0.02)
        keep = keep_out_of(items)
        if not margin.is_empty:
            keep = keep.union(margin.buffer(0.02))
        n += cobble(mb, paved, z, rnd, keep, size=size, angle=ang)
        build_items(mb, items, z + C.PAVE_T, rnd)
        margin_planting(mb, ctx, margin, items, z + C.PAVE_T, rnd)
    print(f'[play] built: {n} paving stones, aprons {aprons.get("east", Polygon()).area:.0f} + '
          f'{aprons.get("west", Polygon()).area:.0f} m², strip margin {bed.area:.0f} m²')
