"""Residential towers built from the architect's floor plans (blender/plans/plans.json).

The plans give, per tower, the slab outline (with the balconies), the facade line, the
windows and curved glazing, and the apartments. A tower is placed on the site by its
centre (from the aerial render) and its rotation (the plan sheet's, turned onto the site).
"""
import json
import math
import os

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from .geom import MeshBuilder, get_collection, make_object, resample, ring_coords
from .towers import SLAB, SLAB_BELOW, add_rails, longest_run, pick_material, slab_band, solar_field

PLANS = os.path.join(os.path.dirname(__file__), '..', 'plans', 'plans.json')

# Levels from section 1-1 (sheet 13): floor N sits at LEVELS[N - 1]
LEVELS = [0.0, 6.0, 10.2, 14.4, 18.6, 22.2, 25.5, 28.8, 32.1, 35.4, 38.7, 42.0, 45.3, 48.6, 51.9, 55.2,
          58.5, 61.8, 65.1, 68.4, 71.7, 75.0, 78.3, 81.6, 84.9, 88.2]

# Sheet -> site: the plan sheets are turned by SITE_ROT onto the site; each tower keeps the
# centre measured on the aerial render (the sheets and the render differ by a few metres).
SITE_ROT = 93.88
TOWERS = {
    'V': dict(label='Block V', centre=(-33.8, 256.6), first=5, last=24,
              plans={**{f: 'V' for f in range(5, 23)}, 23: 'V23', 24: 'V24'}),
    'B': dict(label='Block B', centre=(25.1, 252.4), first=5, last=20,
              plans={f: 'B' for f in range(5, 21)}, stained=range(5, 12)),
}

# The coloured glazing low on block B's land-side face (orange / pink / blue / violet), per floor
# from the bottom, per window from west to east.
STAINED = ['VBV.', 'VPB.', 'PPPV', 'OPPO', 'OOOO', '.OO.', '.O..']
STAIN_MATS = {'O': 'Stained orange', 'P': 'Stained pink', 'B': 'Stained blue', 'V': 'Stained violet'}


def stain_for(row, north):
    """Stained-glass picker for one floor: windows on the flat land-side face, by column."""
    south = np.array([-north[0], -north[1]])
    east = np.array([north[1], -north[0]])
    pattern = STAINED[row] if row < len(STAINED) else ''

    def pick(a, b):
        a, b = np.array(a), np.array(b)
        d = b - a
        n = np.array([d[1], -d[0]]) / (np.linalg.norm(d) + 1e-9)
        if n @ south < 0.9:
            return None
        m = (a + b) / 2
        col = int(np.floor((m @ east + 6.0) / 3.0))
        if 0 <= col < len(pattern) and pattern[col] in STAIN_MATS:
            return STAIN_MATS[pattern[col]]
        return None
    return pick


def load_plans():
    return json.load(open(PLANS))['towers']


def P(pts):
    return Polygon(pts).buffer(0)


def U(list_of_pts, grow=0.0):
    return unary_union([P(p).buffer(grow) for p in list_of_pts if len(p) >= 3])


# ----------------------------------------------------------------------------
# Facade
# ----------------------------------------------------------------------------

def facade(mb, enclosure, windows, glazing, z0, h, step=0.3, stain=None):
    """Walls along the facade line: terracotta, punched windows where the plan draws them,
    floor-to-ceiling glass along the curved glazing behind the balconies."""
    pts = resample(ring_coords(enclosure), step)
    n = len(pts)
    cls = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        m = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if glazing.distance(m) < 0.25:
            cls.append('glaze')
        elif windows.distance(m) < 0.25:
            cls.append('win')
        else:
            cls.append('wall')
    zt = z0 + h - SLAB_BELOW
    zb = z0 + SLAB
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        c = cls[i]
        if c == 'wall':
            mb.quad_wall(a, b, zb, zt, 'Terracotta')
        elif c == 'win':
            mb.quad_wall(a, b, zb, z0 + 0.85, 'Terracotta')
            mb.quad_wall(a, b, z0 + 0.85, zt - 0.35, (stain and stain(a, b)) or 'Window glass')
            mb.quad_wall(a, b, zt - 0.35, zt, 'Terracotta')
        else:
            mb.quad_wall(a, b, zb, zt, 'Window glass')
    # frames: jambs where a window run starts/ends, mullions inside runs, sill and head bars
    run_len = 0.0
    for i in range(n):
        a, b = np.array(pts[i]), np.array(pts[(i + 1) % n])
        d = b - a
        L = np.linalg.norm(d)
        if L < 1e-6:
            continue
        t = d / L
        nrm = np.array([t[1], -t[0]])
        rot = math.atan2(t[1], t[0])
        c, prev = cls[i], cls[i - 1]
        if c == 'wall':
            run_len = 0.0
            continue
        y0 = z0 + 0.85 if c == 'win' else zb
        y1 = zt - 0.35 if c == 'win' else zt
        q = a + nrm * 0.05
        if prev != c or run_len > (1.0 if c == 'win' else 1.5):
            mb.box(q[0], q[1], y0, 0.07, 0.1, y1 - y0, 'Frame', rot=rot)
            run_len = 0.0
        run_len += L
        if c == 'win':
            m = (a + b) / 2 + nrm * 0.06
            mb.box(m[0], m[1], y0 - 0.06, L + 0.02, 0.14, 0.06, 'Frame', rot=rot)
            mb.box(m[0], m[1], y1, L + 0.02, 0.1, 0.06, 'Frame', rot=rot)
        nxt = cls[(i + 1) % n]
        if nxt != c:
            q = b + nrm * 0.05
            mb.box(q[0], q[1], y0, 0.07, 0.1, y1 - y0, 'Frame', rot=rot)


def balcony_rails(slab, enclosure):
    """Rails along the slab edge wherever it stands clear of the facade (the balconies)."""
    edge = slab.exterior.difference(enclosure.buffer(0.35))
    lines = [edge] if edge.geom_type in ('LineString', 'LinearRing') else list(getattr(edge, 'geoms', []))
    return [list(l.coords) for l in lines if l.length > 0.4]


def floor_meshes(plan, z_h, mats, name, stain=None):
    """(slab mesh, walls mesh) of one floor, both with z = 0 at the floor level."""
    slab, enc = P(plan['slab']), P(plan['enclosure'])
    slab = unary_union([slab, enc.buffer(0.15, join_style='mitre')])
    windows, glazing = U(plan['windows'], 0.05), U(plan['glazing'], 0.05)
    mb = MeshBuilder()
    slab_band(mb, slab, 0.0)
    add_rails(mb, balcony_rails(slab, enc), SLAB)
    terrace = slab.difference(enc.buffer(0.3))
    for g in getattr(terrace, 'geoms', [terrace]):
        if g.geom_type == 'Polygon' and g.area > 18:  # roof terraces of the top floors: planters
            rp = g.representative_point()
            mb.box(rp.x, rp.y, SLAB, 1.2, 1.2, 0.5, 'Frame')
            mb.blob(rp.x, rp.y, SLAB + 1.2, 0.8, 0.8, 0.7, 'Shrub', subdiv=1)
    sm = mb.to_mesh(f'{name} slab', mats)
    mb = MeshBuilder()
    facade(mb, enc, windows, glazing, 0.0, z_h, stain=stain)
    return sm, mb.to_mesh(f'{name} walls', mats)


# ----------------------------------------------------------------------------
# Tower
# ----------------------------------------------------------------------------

def build_drawn_tower(key, mats, root_col):
    plans = load_plans()
    info = TOWERS[key]
    col = get_collection(f'Tower {key}', root_col)
    base_plan = plans[key]
    centre = Polygon(base_plan['slab']).centroid
    rot = SITE_ROT + base_plan['sheet_rot']
    a = math.radians(rot)
    # object transform: plan point p -> site C + R(rot) (p - c)
    cx, cy = centre.x, centre.y
    ox = info['centre'][0] - (math.cos(a) * cx - math.sin(a) * cy)
    oy = info['centre'][1] - (math.sin(a) * cx + math.cos(a) * cy)

    def put(ob, z=0.0):
        ob.location = (ox, oy, z)
        ob.rotation_euler = (0, 0, a)
        return ob

    # --- lobby / podium levels inside the tower footprint
    enc = P(base_plan['enclosure'])
    base = enc.buffer(-0.3, join_style='mitre')
    mb = MeshBuilder()
    for f in range(1, info['first']):
        z0, z1 = LEVELS[f - 1], LEVELS[f]
        if f > 1:
            mb.prism(base.buffer(0.25, join_style='mitre'), z0 - 0.35, z0 + 0.35, 'White band', None, 'White band')
        lo = z0 + (1.1 if f > 1 else 0.0)
        if f > 1:
            mb.prism(base, z0 + 0.35, lo, 'Terracotta')
        ring = resample(ring_coords(base), 2.4)
        for p, q in zip(ring, ring[1:] + ring[:1]):
            mb.quad_wall(p, q, lo, z1 - 0.35, 'Shop glass' if f == 1 else 'Window glass')
            mb.box(p[0], p[1], lo, 0.08, 0.08, z1 - 0.35 - lo, 'Frame')
    put(make_object(f'{key} base', mb.to_mesh(f'{key} base', mats), col))

    north = (math.sin(a), math.cos(a))  # site north in plan coordinates

    # --- apartment floors
    cache = {}
    floors = []
    pick_col = get_collection('Picking', col)
    for f in range(info['first'], info['last'] + 1):
        pk = info['plans'][f]
        z, h = LEVELS[f - 1], LEVELS[f] - LEVELS[f - 1]
        stained = f in info.get('stained', ())
        ck = (pk, round(h, 2), f if stained else None)
        if ck not in cache:
            stain = stain_for(f - info['first'], north) if stained else None
            cache[ck] = floor_meshes(plans[pk], h, mats, f'{key} {pk} h{h:.1f}' + (f' f{f}' if stained else ''), stain)
        sm, wm = cache[ck]
        for part, me in (('slab', sm), ('walls', wm)):
            ob = put(make_object(f"{key} {'floor' if part == 'slab' else 'walls'} {f:02d}", me, col), z)
            ob['tower'], ob['floor'], ob['part'] = key, f, part
        # one invisible pick volume per apartment
        for i, apt in enumerate(plans[pk]['apartments']):
            mb = MeshBuilder()
            mb.prism(P(apt['outline']).buffer(0.25, join_style='mitre').simplify(0.1), -0.2, h - 0.1, 'Pick', 'Pick', 'Pick')
            name = f'pick {key} {f:02d} {i}'
            ob = put(make_object(name, mb.to_mesh(name, {'Pick': pick_material()}), pick_col), z + SLAB)
            ob['tower'], ob['floor'], ob['unit'], ob['pick'] = key, f, i, 1
            ob.hide_render = True
        floors.append(dict(floor=f, z=round(z, 3), h=round(h, 3), plan=pk))

    # --- roof
    top = plans[info['plans'][info['last']]]
    zr = LEVELS[info['last']]
    mb = MeshBuilder()
    # the lift and stair core: the structural walls around the corridor in the middle of the plan
    mid = P(top['enclosure']).centroid
    core = unary_union([P(s) for s in top['struct'] if P(s).centroid.distance(mid) < 7.5 and P(s).area > 0.3])
    if core.is_empty:
        core = mid.buffer(5)
    roof(mb, P(top['enclosure']).buffer(0.3, join_style='mitre'), core, zr, north)
    ob = put(make_object(f'{key} roof', mb.to_mesh(f'{key} roof', mats), col))
    ob['tower'], ob['part'] = key, 'roof'

    return dict(key=key, label=info['label'], centre=list(info['centre']), rot=round(rot, 3),
                plan_centre=[round(cx, 3), round(cy, 3)], slab=SLAB, floors=floors,
                levels=info['last'], top=round(zr, 3))


def roof(mb, outline, core, zr, north):
    """Roof slab and parapet, pink membrane, plant room over the core, PV strips, white crown."""
    mb.prism(outline, zr - SLAB_BELOW, zr + 0.55, 'White band', None, 'White band')
    inner = outline.buffer(-0.5)
    mb.polygon_face(inner, zr + 0.56, 'Roof')
    mb.prism(outline.difference(inner), zr + 0.55, zr + 0.85, 'White band', 'White band')
    x0, y0, x1, y1 = core.bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, d = min(x1 - x0 + 1.2, 15.0), min(y1 - y0 + 1.2, 10.0)
    plant = box(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)
    mb.prism(plant, zr + 0.55, zr + 3.9, 'Plant room', None)
    mb.polygon_face(plant, zr + 3.9, 'Roof')
    solar_field(mb, inner.buffer(-1.8).difference(plant.buffer(1.2)), zr + 0.56, angle=-32)
    # crown: white visor on posts, high over the river (north) side, dipping towards the land side
    ring = np.array(resample(ring_coords(outline.buffer(0.15)), 0.8))
    proj = ring @ np.array(north)
    lo, hi = proj.min(), proj.max()
    start = lo + 0.35 * (hi - lo)
    run = longest_run(proj > start)
    if not run:
        return
    Pts = ring[run]
    t = np.clip((Pts @ np.array(north) - start) / (hi - start), 0, 1)
    t = t * t * (3 - 2 * t)
    hz = zr + 0.85 + 0.6 + 3.2 * t
    mb.tube([tuple(p) for p in Pts], list(hz - 0.42), list(hz), 0.95, 'White band')
    for k in range(len(Pts)):
        mb.box(Pts[k][0], Pts[k][1], zr + 0.85, 0.12, 0.12, hz[k] - 0.42 - zr - 0.85, 'White band')
