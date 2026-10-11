"""Pool area on the east deck, by the hotel (render 2).

Warm tan large-format stone paving with a grey irregular cobble walkway along the hotel facade;
a rounded rectangular pool cut as a recess with a raised blue-grey mosaic surround; square sail
umbrellas over pairs of white loungers; lawn beds with round trees and low clipped hedges at the
zone edges; swan-neck lamps around the pool.

Everything stays inside ctx['pool'] (the strip and the edge band belong to deck/edge.py).
"""
import math
import random

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import nearest_points, unary_union
from shapely.prepared import prep

from .common import PAVE_T, hedge, lamp, lawn, rod, tree

POOL_L, POOL_W, POOL_R = 13.0, 6.5, 1.7    # water outline (m) and corner radius
RIM = 0.6                                  # mosaic surround width
DEPTH = 1.2                                # pool depth below the deck slab
POOL_TURN = -16.0                          # pool axis relative to the strip line (deg): parallel to the hotel front
WALK_W = 2.5                               # cobble walkway along the hotel
TILE = 1.2                                 # stone paving module
TILE_MIX = 0.3                             # share of slabs in the lighter stone
CANOPY = 3.0                               # sail umbrella canopy (square)
try:                                       # light ochre canvas (plain 'Umbrella' if the material is missing)
    from ..materials import SPECS as _SPECS
    CANVAS = 'Umbrella sand' if 'Umbrella sand' in _SPECS else 'Umbrella'
except ImportError:
    CANVAS = 'Umbrella'
N_SETS = 3                                 # umbrellas (each over two loungers) between the pool and the deck edge
N_WEST = True                              # and one more beyond the pool's west end
N_LAMPS = 4
WALK_TO_FACADE = True                      # carry the cobble on under the hotel balconies up to its glass front

# rounded rim profile: (offset outwards from the water outline, height above the paving)
RIM_PROFILE = [(0.0, 0.10), (0.05, 0.17), (0.15, 0.205), (0.45, 0.205), (0.55, 0.17), (0.60, 0.09), (0.62, 0.0)]
SPECKLES = 900                             # pebbles on the surround


# ----------------------------------------------------------------------------------------------
# small geometry helpers
# ----------------------------------------------------------------------------------------------

class Frame:
    """Local frame: u along `ang` (radians), v to its left (to its right with flip)."""

    def __init__(self, ox, oy, ang, flip=False):
        self.o = np.array([ox, oy], float)
        self.ang = ang
        self.eu = np.array([math.cos(ang), math.sin(ang)])
        self.ev = np.array([-math.sin(ang), math.cos(ang)]) * (-1 if flip else 1)

    def w(self, u, v):
        p = self.o + self.eu * u + self.ev * v
        return float(p[0]), float(p[1])

    def l(self, x, y):
        d = np.array([x, y], float) - self.o
        return float(d @ self.eu), float(d @ self.ev)

    def poly(self, pts):
        return Polygon([self.w(u, v) for u, v in pts])

    def rect(self, u0, v0, u1, v1):
        return self.poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def rrect_pts(L, W, R, n=6):
    """Rounded rectangle centred at 0 (CCW), a fixed number of points so offsets match point for point."""
    pts = []
    for cx, cy, a0 in [(L / 2 - R, -W / 2 + R, -90), (L / 2 - R, W / 2 - R, 0), (-L / 2 + R, W / 2 - R, 90),
                       (-L / 2 + R, -W / 2 + R, 180)]:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts


def rr_point(L, W, R, f):
    """Point at fraction f (0..1) of the way round a rounded rectangle centred at 0."""
    a, b = L / 2, W / 2
    segs = [('l', (-a + R, -b), (a - R, -b)), ('c', (a - R, -b + R), -90), ('l', (a, -b + R), (a, b - R)),
            ('c', (a - R, b - R), 0), ('l', (a - R, b), (-a + R, b)), ('c', (-a + R, b - R), 90),
            ('l', (-a, b - R), (-a, -b + R)), ('c', (-a + R, -b + R), 180)]
    lens = [math.dist(s[1], s[2]) if s[0] == 'l' else math.pi * R / 2 for s in segs]
    t = f * sum(lens)
    for sg, Ls in zip(segs, lens):
        if t <= Ls or sg is segs[-1]:
            q = min(t / Ls, 1.0) if Ls > 0 else 0.0
            if sg[0] == 'l':
                return sg[1][0] + (sg[2][0] - sg[1][0]) * q, sg[1][1] + (sg[2][1] - sg[1][1]) * q
            ang = math.radians(sg[2] + 90 * q)
            return sg[1][0] + R * math.cos(ang), sg[1][1] + R * math.sin(ang)
        t -= Ls


def obox(mb, c, ex, ey, ez, mat):
    """Box from a centre and three half-extent vectors (any orientation)."""
    c, ex, ey, ez = (np.array(a, float) for a in (c, ex, ey, ez))
    P = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                P[i, j, k] = tuple(c + i * ex + j * ey + k * ez)
    quads = [[(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)], [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
             [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)], [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)],
             [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)], [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)]]
    # keep faces outward whatever the handedness of (ex, ey, ez)
    flip = np.dot(np.cross(ex, ey), ez) < 0
    for q in quads:
        pts = [P[t] for t in q]
        mb.face(pts[::-1] if flip else pts, mat)


def parts(g, min_area=0.05):
    if g.is_empty:
        return []
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type == 'Polygon' and p.area >= min_area:
            out.append(p)
        elif p.geom_type in ('MultiPolygon', 'GeometryCollection'):
            out += parts(p, min_area)
    return out


# ----------------------------------------------------------------------------------------------
# paving
# ----------------------------------------------------------------------------------------------

def stone_tiles(mb, area, fr, z, tile=TILE, joint=0.025, rnd=None):
    """Large-format stone: one top face per slab (the light joints are the podium slab below); a share
    of the slabs in the lighter terrace stone so the paving looks like natural stone, not a flat colour."""
    if area.is_empty:
        return
    rnd = rnd or random.Random(5)
    lu = [fr.l(x, y) for g in parts(area) for x, y in g.exterior.coords]
    u0, u1 = min(p[0] for p in lu), max(p[0] for p in lu)
    v0, v1 = min(p[1] for p in lu), max(p[1] for p in lu)
    pa = prep(area)
    i0, i1 = int(math.floor(u0 / tile)), int(math.ceil(u1 / tile))
    j0, j1 = int(math.floor(v0 / tile)), int(math.ceil(v1 / tile))
    for i in range(i0, i1):
        for j in range(j0, j1):
            sq = fr.rect(i * tile + joint / 2, j * tile + joint / 2, (i + 1) * tile - joint / 2, (j + 1) * tile - joint / 2)
            if not pa.intersects(sq):
                continue
            mat = 'Deck paving' if rnd.random() < TILE_MIX else 'Deck stone'
            if pa.contains(sq):
                mb.polygon_face(sq, z, mat)
                continue
            for g in parts(sq.intersection(area), 0.01):
                mb.polygon_face(g, z, mat)
    for g in parts(area):  # thin edge so the paving reads against the neighbours
        mb.prism(g, z - PAVE_T, z, 'Deck stone', None)


def cobbles(mb, area, z, rnd, size=0.5, joint=0.07):
    """Irregular grey stones (Voronoi cells) with light joints."""
    if area.is_empty:
        return
    x0, y0, x1, y1 = area.bounds
    pts = []
    y = y0
    row = 0
    while y < y1 + size:
        x = x0 + (size / 2 if row % 2 else 0)
        while x < x1 + size:
            pts.append((x + rnd.uniform(-0.3, 0.3) * size, y + rnd.uniform(-0.3, 0.3) * size))
            x += size * rnd.uniform(0.85, 1.25)
        y += size * 0.87
        row += 1
    cells = shapely.voronoi_polygons(MultiPoint(pts), extend_to=area.buffer(2.0))
    pa = prep(area)
    for c in cells.geoms:
        if not pa.intersects(c):
            continue
        c = c.buffer(-joint / 2, join_style='mitre')
        if c.is_empty:
            continue
        cc = c if pa.contains(c) else c.intersection(area)
        for g in parts(cc, 0.004):
            g = g.simplify(0.01)
            # each stone slightly tilted so the walkway shows a stony shimmer
            cx, cy = g.centroid.x, g.centroid.y
            ax, ay = rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05)
            z0 = z - rnd.uniform(0.0, 0.012)
            pts = [(x, y, z0 + ax * (x - cx) + ay * (y - cy)) for x, y in list(shapely.geometry.polygon.orient(g, 1.0).exterior.coords)[:-1]]
            mb.face(pts, 'Cobble')
    for g in parts(area):
        mb.prism(g, z - PAVE_T, z - 0.012, 'Cobble', None)


# ----------------------------------------------------------------------------------------------
# pool
# ----------------------------------------------------------------------------------------------

def pool(mb, fr, zs, zp):
    """Pool cut into the deck: tile walls and floor, water, rounded mosaic surround, ladders."""
    rings = []
    for d, h in RIM_PROFILE:
        rings.append(([fr.w(u, v) for u, v in rrect_pts(POOL_L + 2 * d, POOL_W + 2 * d, POOL_R + d)], zp + h))
    n = len(rings[0][0])
    # surround: rings joined into a rounded band (inner lip in light tile, the rest mosaic)
    for k in range(len(rings) - 1):
        (ra, za), (rb, zb) = rings[k], rings[k + 1]
        mat = 'Pool tile' if k == 0 else 'Pool mosaic'
        for i in range(n):
            j = (i + 1) % n
            mb.face([(*ra[i], za), (*ra[j], za), (*rb[j], zb), (*rb[i], zb)][::-1], mat)
    outer = rings[-1][0]
    for i in range(n):  # outer skirt down to the slab
        j = (i + 1) % n
        mb.face([(*outer[i], zs), (*outer[j], zs), (*outer[j], zp), (*outer[i], zp)], 'Pool mosaic')
    # tile walls down to the floor (water sits ~0.15 m below the coping)
    inner, ztop = rings[0]
    zf = zs - DEPTH
    for i in range(n):
        j = (i + 1) % n
        mb.face([(*inner[i], zf), (*inner[j], zf), (*inner[j], ztop), (*inner[i], ztop)][::-1], 'Pool tile')
    water = Polygon(inner)
    mb.polygon_face(water, zf, 'Pool tile')
    zw = zp + RIM_PROFILE[2][1] - 0.15
    mb.polygon_face(water, zw, 'Pool water')
    # pebble mosaic: white, light-blue and blue pebbles over the top of the rounded surround
    rnd = random.Random(7)
    pd = [d for d, h in RIM_PROFILE]
    ph = [h for d, h in RIM_PROFILE]
    for k in range(SPECKLES):
        d = rnd.uniform(0.05, RIM - 0.07)
        u, v = rr_point(POOL_L + 2 * d, POOL_W + 2 * d, POOL_R + d, rnd.random())
        zt = zp + float(np.interp(d, pd, ph)) + 0.02
        r = rnd.uniform(0.04, 0.075)
        a = rnd.uniform(0, math.pi)
        sq = [fr.w(u + r * math.cos(a + q), v + r * math.sin(a + q)) for q in (0, math.pi / 2, math.pi, 1.5 * math.pi)]
        c = rnd.random()
        mb.face([(x, y, zt) for x, y in sq], 'Lamp white' if c < 0.5 else 'Pool tile' if c < 0.82 else 'Play blue')
    # foam over the jet in the middle of the pool, with a couple of wisps: wobbly star-shaped patches,
    # a light-blue halo with a white core so the edge reads soft
    for cu, cv, sx, sy, rot in [(-1.0, -0.2, 1.1, 0.4, 0.3), (0.5, 0.4, 0.6, 0.15, -0.2), (-2.4, 0.5, 0.45, 0.12, 0.5),
                                (1.3, -0.5, 0.35, 0.09, 0.1)]:
        ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
        for scale, dz, mat in [(1.35, 0.015, 'Pool tile'), (0.8, 0.03, 'Foam')]:
            pts = []
            for t in np.linspace(0, 2 * math.pi, 23)[:-1]:
                r = scale * (1 + 0.3 * math.sin(2 * t + ph[0]) + 0.22 * math.sin(3 * t + ph[1]) + 0.12 * math.sin(5 * t + ph[2]))
                pu, pv = math.cos(t) * sx * r, math.sin(t) * sy * r
                pts.append((cu + pu * math.cos(rot) - pv * math.sin(rot), cv + pu * math.sin(rot) + pv * math.cos(rot)))
            g = Polygon(pts).buffer(0)
            if g.is_empty:
                continue
            if mat == 'Foam' and g.area > 0.5:
                g = g.difference(affinity.scale(g, 0.45, 0.4).buffer(0))  # the clear centre of the boil
            for q in parts(g, 0.02):
                mb.polygon_face(Polygon([fr.w(x, y) for x, y in q.exterior.coords][:-1],
                                        [[fr.w(x, y) for x, y in r.coords][:-1] for r in q.interiors]), zw + dz, mat)
    # ladders: chrome rails curving over the coping on both long sides
    for su, sv in [(POOL_L / 2 - 2.2, -1), (-POOL_L / 2 + 2.2, 1)]:
        for du in (-0.28, 0.28):
            pts = []
            for k in range(8):
                a = math.pi * k / 7
                vv = sv * (POOL_W / 2 + RIM + 0.25) - sv * (RIM + 0.6) * (1 - math.cos(a)) / 2
                zz = zp + 0.75 + 0.25 * math.sin(a)
                pts.append((*fr.w(su + du, vv), zz))
            pts = [(*fr.w(su + du, sv * (POOL_W / 2 + RIM + 0.25)), zp)] + pts + [(*fr.w(su + du, sv * (POOL_W / 2 - 0.35)), zw - 0.6)]
            for p, q in zip(pts[:-1], pts[1:]):
                rod(mb, p, q, 0.025, 'Metal', sides=5)


# ----------------------------------------------------------------------------------------------
# furniture
# ----------------------------------------------------------------------------------------------

def umbrella(mb, x, y, z, ang, size=CANOPY, h=2.45, rise=0.42):
    """Square sail umbrella: centre pole, low pyramid canopy with a short valance."""
    c, s = math.cos(ang), math.sin(ang)
    mb.box(x, y, z, 0.4, 0.4, 0.08, 'Metal', rot=ang)
    rod(mb, (x, y, z), (x, y, z + h + rise + 0.12), 0.04, 'Wood', sides=6)
    hs = size / 2
    cs = [(x + c * a - s * b, y + s * a + c * b) for a, b in [(-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)]]
    apex = (x, y, z + h + rise)
    for i in range(4):
        a, b = cs[i], cs[(i + 1) % 4]
        mb.face([(*a, z + h), (*b, z + h), apex], CANVAS)
        mb.face([(*b, z + h - 0.04), (*a, z + h - 0.04), (x, y, z + h + rise - 0.04)], CANVAS)
        mb.quad_wall(a, b, z + h - 0.13, z + h, CANVAS)
        mb.quad_wall(a, b, z + h - 0.13, z + h, CANVAS, flip=True)
        # ribs from the pole to the corners, just under the canopy
        rod(mb, (x, y, z + h - 0.25), (a[0], a[1], z + h - 0.03), 0.018, 'Wood', sides=4)
    mb.box(x, y, z + h + rise - 0.02, 0.16, 0.16, 0.14, CANVAS, rot=ang)
    for a in cs:  # light seams along the ridges
        rod(mb, (x, y, z + h + rise + 0.015), (a[0], a[1], z + h + 0.015), 0.03, 'Lattice wood', sides=3)


def flower_box(mb, x, y, z, ang, rnd):
    """Small square timber planter with a flowering shrub (next to the umbrellas on the render)."""
    mb.box(x, y, z, 0.55, 0.55, 0.42, 'Wood', rot=ang)
    mb.blob(x, y, z + 0.55, 0.3, 0.3, 0.2, 'Leaves light', subdiv=1, jitter=0.15, rnd=rnd)
    for k in range(3):
        a = ang + k * 2.1 + rnd.uniform(-0.4, 0.4)
        mb.blob(x + 0.14 * math.cos(a), y + 0.14 * math.sin(a), z + 0.66, 0.11, 0.11, 0.07, 'Fitness yellow', subdiv=0)


def lounger(mb, x, y, z, ang, L=1.95, W=0.7):
    """White sun lounger on a timber frame; the backrest end points along -ang."""
    eu = np.array([math.cos(ang), math.sin(ang), 0.0])
    ev = np.array([-math.sin(ang), math.cos(ang), 0.0])
    ez = np.array([0, 0, 1.0])
    o = np.array([x, y, z])
    # timber frame and legs
    for sv in (-1, 1):
        obox(mb, o + ev * sv * (W / 2 - 0.04) + ez * 0.25, eu * L / 2, ev * 0.035, ez * 0.04, 'Wood')
        for su in (-1, 1):
            obox(mb, o + eu * su * (L / 2 - 0.1) + ev * sv * (W / 2 - 0.04) + ez * 0.13, eu * 0.035, ev * 0.035, ez * 0.13, 'Wood')
    # cushion: flat part and a raised backrest at the -u end
    flat = L - 0.62
    obox(mb, o + eu * (L / 2 - flat / 2) + ez * 0.34, eu * flat / 2, ev * (W / 2 - 0.02), ez * 0.05, 'Lounger')
    a = math.radians(38)
    d = eu * (-math.cos(a)) + ez * math.sin(a)
    base = o + eu * (L / 2 - flat) + ez * 0.34
    n = np.cross(d, ev)
    obox(mb, base + d * 0.33, d * 0.33, ev * (W / 2 - 0.02), n * 0.05, 'Lounger')


def side_table(mb, x, y, z, ang):
    mb.box(x, y, z, 0.08, 0.08, 0.42, 'Wood', rot=ang)
    mb.box(x, y, z, 0.32, 0.32, 0.04, 'Wood', rot=ang)
    mb.box(x, y, z + 0.42, 0.44, 0.44, 0.04, 'Lounger', rot=ang)


def sun_set(mb, fr, u, v, z, face, ok=None, rnd=None):
    """Umbrella over two loungers facing the pool (face: unit axis (du, dv) of the pool frame pointing
    to the pool), a side table between their backrests and a flower box beside the canopy."""
    fu, fv = face
    su, sv = -fv, fu  # across the loungers
    x, y = fr.w(u, v)
    umbrella(mb, x, y, z, fr.ang)
    ang = fr.ang + math.atan2(fv, fu)  # lounger u-axis points to the pool, backrest away from it
    for k in (-0.62, 0.62):
        lx, ly = fr.w(u + su * k + fu * 0.05, v + sv * k + fv * 0.05)
        lounger(mb, lx, ly, z, ang)
    tx, ty = fr.w(u - fu * 0.7, v - fv * 0.7)
    side_table(mb, tx, ty, z, fr.ang)
    for a, b in [(1, -1), (-1, -1), (1, 1), (-1, 1)]:
        du = su * a * (CANOPY / 2 + 0.5) + fu * b * 1.0
        dv = sv * a * (CANOPY / 2 + 0.5) + fv * b * 1.0
        bx, by = fr.w(u + du, v + dv)
        if ok is None or ok(bx, by):
            flower_box(mb, bx, by, z, fr.ang, rnd or random.Random(3))
            break


# ----------------------------------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------------------------------

def strip_frame(ctx, zone):
    """Frame along the strip line from its west end (between the towers) to the deck edge,
    v pointing into the pool zone."""
    sl = ctx['strip_line']
    (x0, y0), (x1, y1) = sl.coords[0], sl.coords[-1]
    if x1 < x0:
        x0, y0, x1, y1 = x1, y1, x0, y0
    fr = Frame(x0, y0, math.atan2(y1 - y0, x1 - x0))
    if fr.l(zone.centroid.x, zone.centroid.y)[1] < 0:
        fr = Frame(x0, y0, fr.ang, flip=True)
    return fr


def hotel_apron(ctx, zone, walk):
    """The slab between the walkway and the hotel's glass front (under its balconies, outside the zones)."""
    from .. import towers
    H = towers.TOWER_A
    core = affinity.translate(affinity.rotate(towers.hotel_core(H), H['rot'], origin=(0, 0)), *H['origin'])
    A = ctx['towers']['A']
    band = ctx['podium'].intersection(A.buffer(zone.distance(A) + 0.02)).difference(core.buffer(0.03))
    for other in ('edge_band', 'strip', 'play'):
        band = band.difference(ctx[other].buffer(0.05))
    band = band.difference(ctx['west_wing']).difference(zone)
    band = band.intersection(walk.buffer(zone.distance(A) + H['balcony'] + 0.8))
    return unary_union(parts(band.buffer(0.05).buffer(-0.05), 0.5))


def place_pool(zone, walk, fr_s, ang, c_zone=1.4, c_walk=1.2):
    """Pool centre: clear of the walkway and the zone edge, as close to the strip as that allows."""
    shape0 = Polygon(rrect_pts(POOL_L + 2 * RIM, POOL_W + 2 * RIM, POOL_R + RIM, 3))
    shape0 = affinity.rotate(shape0, ang, origin=(0, 0), use_radians=True)
    ring = zone.exterior
    best = None
    x0, y0, x1, y1 = zone.bounds
    cands = []
    for x in np.arange(x0 + 4, x1 - 4, 0.4):
        for y in np.arange(y0 + 3, y1 - 3, 0.4):
            cands.append((x, y))
    polys = [affinity.translate(shape0, x, y) for x, y in cands]
    inside = shapely.contains(zone.buffer(-c_zone), polys)
    dwalk = shapely.distance(walk, polys)
    for (x, y), p, ok, dw in zip(cands, polys, inside, dwalk):
        if not ok or dw < c_walk:
            continue
        dz = ring.distance(p)
        clear = min(dw - c_walk, dz - c_zone)
        u, v = fr_s.l(x, y)
        score = min(clear, 0.6) - 0.08 * v - 0.02 * u  # near the strip, then towards the hotel's glass front (west)
        if best is None or score > best[0]:
            best = (score, x, y, dw, dz)
    return best


def build(mb, ctx):
    rnd = random.Random(20261011 + 1)
    zs = ctx['z']
    zp = zs + PAVE_T
    zone = ctx['pool'].buffer(0)
    A = ctx['towers']['A']
    fr_s = strip_frame(ctx, zone)

    # walkway along the hotel (the zone edge closest to tower A)
    walk = zone.intersection(A.buffer(zone.distance(A) + WALK_W, quad_segs=6))
    walk = unary_union(parts(walk.buffer(0.3).buffer(-0.3).intersection(zone), 1.0))

    # pool
    ang = fr_s.ang + math.radians(POOL_TURN)
    for cz, cw in [(1.4, 1.2), (0.8, 0.6), (0.2, 0.0)]:  # relax the clearances if the zone ever gets tighter
        best = place_pool(zone, walk, fr_s, ang, cz, cw)
        if best:
            break
    if not best:
        c = zone.buffer(-POOL_W / 2 - RIM).representative_point() if not zone.buffer(-POOL_W / 2 - RIM).is_empty else zone.representative_point()
        best = (0, c.x, c.y, 0, 0)
    px, py = best[1], best[2]
    fr = Frame(px, py, ang)
    print(f'[deck] pool: pool centre ({px:.2f}, {py:.2f}) axis {math.degrees(ang):.1f} deg, walk clearance {best[3]:.2f}, edge clearance {best[4]:.2f}')
    pool_outer = fr.poly(rrect_pts(POOL_L + 2 * RIM + 0.04, POOL_W + 2 * RIM + 0.04, POOL_R + RIM + 0.02, 6))

    # ---- lawn beds with trees and hedges at the zone edges ----
    beds = []
    trees = []
    # strip side: a narrow lawn bed along the planter, with gaps
    # zone boundary on the strip side lies on v = v_edge
    v_edge = min(fr_s.l(x, y)[1] for x, y in zone.exterior.coords if abs(fr_s.l(x, y)[1]) < 3.0)
    u_lo = min(fr_s.l(x, y)[0] for x, y in zone.exterior.coords)
    u_hi = max(fr_s.l(x, y)[0] for x, y in zone.exterior.coords)
    keep = pool_outer.buffer(1.3).union(walk.buffer(1.0))
    for a, b in [(u_lo + 5.0, u_lo + 12.0), (u_lo + 14.0, u_lo + 19.5)]:
        bed = zone.intersection(fr_s.rect(a, v_edge - 1, b, v_edge + 1.6)).difference(keep)
        for g in parts(bed, 2.0):
            beds.append(g)
    # the narrow tip where the strip meets the deck edge
    tip = zone.intersection(fr_s.rect(u_hi - 4.5, -50, u_hi + 5, 50)).difference(walk.buffer(1.0))
    beds += parts(tip, 3.0)

    bed_u = unary_union(beds) if beds else Polygon()
    # stone area
    stone = zone.difference(walk).difference(pool_outer).difference(bed_u)

    # ---- sun sets: umbrellas between the pool and the deck edge ----
    edge_line = ctx['outer_line']
    room = zone.buffer(-0.4).difference(walk.buffer(0.4)).difference(pool_outer.buffer(1.0)).difference(bed_u.buffer(0.4))
    prep_room = prep(room)
    sets = []
    taken = Polygon()
    cand = []
    for u in np.arange(-25, 25, 0.25):
        for v in np.arange(-20, 20, 0.25):
            x, y = fr.w(u, v)
            de = edge_line.distance(Point(x, y))
            if de > 8.0:
                continue
            sq = fr.rect(u - CANOPY / 2, v - CANOPY / 2, u + CANOPY / 2, v + CANOPY / 2)
            if prep_room.contains(sq):
                cand.append((pool_outer.distance(Point(x, y)) + 0.5 * de, u, v, sq))
    cand.sort(key=lambda t: t[0])
    squares = []
    for sc, u, v, sq in cand:
        if len(sets) >= N_SETS:
            break
        if taken.intersects(sq):
            continue
        sets.append((u, v))
        squares.append(sq)
        # the first two side by side, then a tree's width before the next one (as on the render)
        gap = 1.0 if len(sets) < 2 else 3.4
        taken = unary_union([q.buffer(gap, join_style='mitre') for q in squares])
    # one more beyond the pool's far (west) end, in the long stone band by the hotel's glass front
    if N_WEST:
        wc = []
        for u in np.arange(-25, -(POOL_L / 2 + RIM + 1.0 + CANOPY / 2) + 0.01, 0.25):
            for v in np.arange(-6, 6, 0.25):
                sq = fr.rect(u - CANOPY / 2, v - CANOPY / 2, u + CANOPY / 2, v + CANOPY / 2)
                if prep_room.contains(sq) and not taken.intersects(sq):
                    wc.append((abs(u + POOL_L / 2 + RIM + 2.6) + 0.5 * abs(v), u, v, sq))
        if wc:
            sc, u, v, sq = min(wc, key=lambda t: t[0])
            sets.append((u, v))
            squares.append(sq)
            taken = taken.union(sq.buffer(1.0, join_style='mitre'))
    # trees standing in the paving among the umbrellas (small round beds)
    free = room.difference(unary_union([q.buffer(0.3) for q in squares]) if squares else Polygon())
    paving_trees = []
    pf = prep(free)
    tc = []
    centres = [Point(fr.w(u, v)) for u, v in sets]
    for u in np.arange(-25, 25, 0.5):
        for v in np.arange(-20, 20, 0.5):
            p = Point(fr.w(u, v))
            if pf.contains(p.buffer(1.0)):
                du = min((p.distance(c) for c in centres), default=3.0)
                if du < 2.6:
                    continue
                tc.append((edge_line.distance(p) + 2.0 * abs(du - 3.0) + 0.2 * pool_outer.distance(p), p))
    tc.sort(key=lambda t: t[0])
    for sc, p in tc:
        if len(paving_trees) >= 1:
            break
        if all(p.distance(q) > 5.0 for q in paving_trees):
            paving_trees.append(p)
    # and one right by the pool, between its end and the umbrellas (as on the render)
    tc = []
    for u in np.arange(-25, 25, 0.5):
        for v in np.arange(-20, 20, 0.5):
            p = Point(fr.w(u, v))
            dp = pool_outer.distance(p)
            if 1.2 < dp < 2.6 and pf.contains(p.buffer(0.9)) and all(p.distance(q) > 4.0 for q in paving_trees):
                du = min((p.distance(c) for c in centres), default=3.0)
                if du > 2.6:
                    tc.append((du + 0.5 * edge_line.distance(p), p))
    if tc:
        paving_trees.append(min(tc, key=lambda t: t[0])[1])
    print(f'[deck] pool: {len(sets)} sun sets at', [tuple(round(c, 1) for c in fr.w(u, v)) for u, v in sets],
          'paving trees at', [(round(p.x, 1), round(p.y, 1)) for p in paving_trees])

    # ---- build ----
    pits = [p.buffer(0.75, quad_segs=4) for p in paving_trees]
    if pits:
        stone = stone.difference(unary_union(pits))
    stone_tiles(mb, stone, fr, zp, rnd=random.Random(5))
    for g, p in zip(pits, paving_trees):
        lawn(mb, g, zs, 0.14)
        trees.append((p.x, p.y, zs + 0.12))
    cobbles(mb, walk, zp, rnd)
    if WALK_TO_FACADE:
        try:
            cobbles(mb, hotel_apron(ctx, zone, walk), zp, rnd)
        except Exception as e:  # the apron is a nicety; never lose the pool area over it
            print(f'[deck] pool: no hotel apron ({e})')
    pool(mb, fr, zs, zp)
    for g in beds:
        lawn(mb, g, zs, 0.14)
        # low clipped hedge on the stone side of each bed
        edge_to_stone = g.exterior.intersection(stone.buffer(0.05))
        if not edge_to_stone.is_empty:
            hedge(mb, g.intersection(edge_to_stone.buffer(0.55)).buffer(-0.05), zs + 0.12, h=0.75)
    stone_in = prep(stone.buffer(-0.45))
    for u, v in sets:
        # face the nearest side of the pool
        ex_u = max(abs(u) - (POOL_L / 2 + RIM), 0.0)
        ex_v = max(abs(v) - (POOL_W / 2 + RIM), 0.0)
        face = (-math.copysign(1, u), 0) if ex_u > ex_v else (0, -math.copysign(1, v))
        sun_set(mb, fr, u, v, zp, face, ok=lambda x, y: stone_in.contains(Point(x, y)), rnd=rnd)

    # trees in the beds, spaced evenly along each bed's long axis
    for g in beds:
        cen = g.buffer(-0.55)
        if cen.is_empty:
            cen = g
        mrr = list(g.minimum_rotated_rectangle.exterior.coords)[:4]
        e1, e2 = math.dist(mrr[0], mrr[1]), math.dist(mrr[1], mrr[2])
        a0, a1 = (mrr[0], mrr[1]) if e1 >= e2 else (mrr[1], mrr[2])
        off = np.array(mrr[2] if e1 >= e2 else mrr[3]) - np.array(a1)
        Lb = max(e1, e2)
        n = max(1, int(round(Lb / 4.2)))
        for k in range(n):
            t = (k + 0.5) / n
            q = np.array(a0) + (np.array(a1) - np.array(a0)) * t + off * 0.5
            p = Point(*q)
            if not cen.contains(p):
                p = nearest_points(cen, p)[0]
            trees.append((p.x, p.y, zs + 0.12))
    for x, y, zz in trees:
        tree(mb, x, y, zz, h=rnd.uniform(4.2, 5.6), r=rnd.uniform(1.4, 1.9), leaf=rnd.choice(['Leaves', 'Leaves light']), rnd=rnd)

    # swan-neck lamps around the pool, ~1 m off the surround, spread out and clear of canopies and trees
    ok_lamp = prep(stone.buffer(-0.3).difference(unary_union([q.buffer(0.7) for q in squares]) if squares else Polygon()))
    lc = []
    for k in range(40):
        u, v = rr_point(POOL_L + 2 * (RIM + 1.0), POOL_W + 2 * (RIM + 1.0), POOL_R + RIM + 1.0, k / 40)
        p = Point(fr.w(u, v))
        if ok_lamp.contains(p) and all(p.distance(Point(t[0], t[1])) > 1.6 for t in trees):
            lc.append(p)
    lamps = []
    if lc:
        lamps.append(min(lc, key=lambda p: walk.distance(p)))  # one by the walkway
        while len(lamps) < N_LAMPS:
            far = max(lc, key=lambda p: min(p.distance(q) for q in lamps))
            if min(far.distance(q) for q in lamps) < 5.0:
                break
            lamps.append(far)
    tx, ty = fr.w(0, 0)
    for p in lamps:
        # the arm reaches across towards the pool, so the head hangs over the edge of the water
        lamp(mb, p.x, p.y, zp, rot=math.atan2(ty - p.y, tx - p.x), h=4.2)
    print(f'[deck] pool: {len(lamps)} lamps, {len(trees)} trees, {len(beds)} lawn beds')
