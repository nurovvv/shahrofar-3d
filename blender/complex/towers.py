"""The three towers: V (tallest), B (middle) and A (the hotel).

Every tower is described in its own local frame: origin on the centre of the
south (land-side) face of the central bay, +y pointing north towards the river,
then rotated and moved onto the site.

Residential plan = a central bay ("bar", flat terracotta with four window
columns) running through a rounded body that is wrapped in curved balconies
with white slab edges and glass rails.
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .geom import (MeshBuilder, biggest, get_collection, make_object, place, resample, ring_coords, rounded_rect,
                   simplify_ring, transform2)

SLAB = 0.32        # slab top above floor level datum
SLAB_BELOW = 0.18  # band continues below floor level
RAIL = 1.05        # glass rail height
FASCIA = 0.42      # solid white upstand on the balcony edge, under the glass rail


# ----------------------------------------------------------------------------
# Tower definitions (metres, site frame of the reference camera)
# ----------------------------------------------------------------------------

TOWER_V = dict(
    key='V', label='Block V', origin=(-32.65, 233.6), rot=1.7,
    bar_w=13.1, body=(-16.0, 4.5, 15.1, 44.0), r_front=6.0, r_back=13.5, bar_back=2.0,
    balcony=2.1,
    base=[4.6, 3.8, 3.8, 3.8, 3.8],
    typical=18, typ_h=3.2,
    setbacks=[dict(front_l=1.6, front_r=1.6, back=0.0, h=3.2), dict(front_l=2.6, front_r=4.2, back=0.6, h=3.2, bar_front=0.0)],
    plant=dict(c=(2.0, 24.0), size=(15.5, 7.2), h=3.4),
    crown=dict(front=0.6, back=4.4, y_start=7.0),
    windows=4,
)

TOWER_B = dict(
    key='B', label='Block B', origin=(15.9, 232.2), rot=-25.0,
    bar_w=12.6, body=(-15.2, 4.2, 14.8, 42.5), r_front=6.0, r_back=13.0, bar_back=2.0,
    balcony=2.1,
    base=[4.4, 3.7, 3.7, 3.7, 3.7],
    typical=15, typ_h=3.13,
    setbacks=[dict(front_l=2.2, front_r=3.6, back=0.4, h=3.2)],
    plant=dict(c=(-2.0, 22.5), size=(15.0, 7.0), h=3.4),
    crown=dict(front=0.6, back=4.2, y_start=6.0),
    windows=4,
    # the colourful glazing on the lower part of B's front (orange / pink / blue / violet)
    stained={
        0: ['Window glass', 'Stained blue', 'Stained violet', 'Window glass'],
        1: ['Window glass', 'Stained blue', 'Stained pink', 'Window glass'],
        2: ['Stained violet', 'Stained pink', 'Stained pink', 'Window glass'],
        3: ['Stained orange', 'Stained orange', 'Stained pink', 'Window glass'],
        4: ['Stained orange', 'Stained orange', 'Stained orange', 'Window glass'],
        5: ['Window glass', 'Stained orange', 'Stained orange', 'Window glass'],
        6: ['Window glass', 'Stained orange', 'Window glass', 'Window glass'],
    },
)


# ----------------------------------------------------------------------------
# Plan helpers
# ----------------------------------------------------------------------------

def residential_plan(T, front_l=0.0, front_r=0.0, back=0.0, bar_front=0.0, shrink=0.0):
    """Core (enclosure) outline in local coordinates for a given setback."""
    bw = T['bar_w']
    x0, y0, x1, y1 = T['body']
    rf, rb = T['r_front'], T['r_back']
    # body split in a left and right half so each side can step back on its own
    left = rounded_rect(x0 + shrink, y0 + front_l, 0.5, y1 - back - shrink, rf, 0, 0, rb)
    right = rounded_rect(-0.5, y0 + front_r, x1 - shrink, y1 - back - shrink, 0, rf, rb, 0)
    bar = box(-bw / 2, bar_front, bw / 2, y1 + T['bar_back'] - back)
    return unary_union([left, right, bar]).buffer(0.01).buffer(-0.01)


def balcony_outline(T, core):
    """Slab outline with balconies: body offset outwards, never in front of the bar faces."""
    bw = T['bar_w']
    x0, y0, x1, y1 = T['body']
    d = T['balcony']
    body = rounded_rect(x0, y0, x1, y1, T['r_front'], T['r_front'], T['r_back'], T['r_back'])
    out = body.buffer(d, quad_segs=12)
    # clip at the bar's south and north faces so the bar ends stay flat
    clip = box(-100, 0.0, 100, y1 + T['bar_back'])
    return unary_union([out.intersection(clip), core])


def on_bar_face(T, a, b, y_south=0.0, tol=0.05):
    """Is the segment a->b lying on the bar's south or north face?"""
    bw = T['bar_w']
    y_north = T['body'][3] + T['bar_back']
    for yf in (y_south, y_north):
        if abs(a[1] - yf) < tol and abs(b[1] - yf) < tol and max(abs(a[0]), abs(b[0])) <= bw / 2 + tol:
            return 'south' if yf == y_south else 'north'
    return None


def on_bar_side(T, a, b, tol=0.05):
    bw = T['bar_w']
    return abs(abs(a[0]) - bw / 2) < tol and abs(abs(b[0]) - bw / 2) < tol and abs(a[0] - b[0]) < tol


# ----------------------------------------------------------------------------
# Facade pieces
# ----------------------------------------------------------------------------

def window_column(mb, a, b, z, h, n, sill=0.55, win_h=2.25, win_w=0.95, pair_gap=0.4, glass='Window glass', frame='Frame', offset=0.04):
    """n window bays evenly spread on the flat wall a->b, each a pair of tall narrow windows."""
    a, b = np.array(a, float), np.array(b, float)
    d = b - a
    L = np.linalg.norm(d)
    t = d / L
    nrm = np.array([t[1], -t[0]])
    rot = math.atan2(t[1], t[0])
    fw, fd = 0.06, 0.1
    for i in range(n):
        c = a + t * (L * (i + 0.5) / n)
        g = glass[i] if isinstance(glass, (list, tuple)) else glass
        for s in (-1, 1):
            cw = c + t * s * (pair_gap / 2 + win_w / 2)
            p0 = cw - t * win_w / 2 + nrm * offset
            p1 = cw + t * win_w / 2 + nrm * offset
            mb.quad_wall(tuple(p0), tuple(p1), z + sill, z + sill + win_h, g)
            for e in (-1, 1):
                q = cw + t * e * (win_w / 2 + fw / 2) + nrm * offset
                mb.box(q[0], q[1], z + sill - fw, fw, fd, win_h + 2 * fw, frame, rot=rot)
            q = cw + nrm * offset
            mb.box(q[0], q[1], z + sill + win_h, win_w + 2 * fw, fd, fw, frame, rot=rot)
            mb.box(q[0], q[1], z + sill - fw, win_w + 2 * fw, fd + 0.04, fw, frame, rot=rot)
            mb.box(q[0], q[1], z + sill + win_h * 0.72, win_w, fd * 0.8, 0.05, frame, rot=rot)


def glazed_wall(mb, a, b, z0, z1, glass='Window glass', frame='Frame', step=1.55):
    """Floor-to-ceiling glazing with slim mullions (behind balconies)."""
    mb.quad_wall(a, b, z0, z1, glass)
    a, b = np.array(a, float), np.array(b, float)
    L = np.linalg.norm(b - a)
    if L < 0.4:
        return
    t = (b - a) / L
    rot = math.atan2(t[1], t[0])
    n = max(1, int(round(L / step)))
    for i in range(n):
        q = a + t * (L * i / n)
        mb.box(q[0], q[1], z0, 0.07, 0.1, z1 - z0, frame, rot=rot)


def wall_ring(mb, T, core, z0, z1, windows=True, glass='Window glass', base=False, south_glass=None):
    pts = simplify_ring(ring_coords(core), tol=0.002)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        face = on_bar_face(T, a, b)
        if face or on_bar_side(T, a, b):
            mb.quad_wall(a, b, z0, z1, 'Terracotta')
            if face and windows and math.dist(a, b) > 6:
                g = south_glass if (face == 'south' and south_glass) else 'Window glass'
                window_column(mb, a, b, z0, z1 - z0, T['windows'], glass=g)
        elif base:
            mb.quad_wall(a, b, z0, z1, glass)
        else:
            glazed_wall(mb, a, b, z0, z1, glass)


def rail_segments(T, slab, exclude):
    """Parts of the slab edge that get a glass rail (everything except bar faces / walls)."""
    edge = slab.exterior
    keep = edge.difference(exclude.buffer(0.12))
    lines = [keep] if keep.geom_type == 'LineString' else list(getattr(keep, 'geoms', []))
    return [list(l.coords) for l in lines if l.length > 0.3]


def add_rails(mb, segs, z, h=RAIL, mat='Railing glass', post_step=None):
    for seg in segs:
        # solid white upstand, then glass
        if len(seg) > 1:
            mb.tube(seg, [z - 0.05] * len(seg), [z + FASCIA] * len(seg), 0.16, 'White band')
        mb.ribbon(seg, z + FASCIA, z + h, mat, double=True)
        # slim metal handrail
        zs0 = [z + h - 0.04] * len(seg)
        zs1 = [z + h + 0.02] * len(seg)
        if len(seg) > 1:
            mb.tube(seg, zs0, zs1, 0.06, 'Frame')


def slab_band(mb, slab, z, top='White band'):
    mb.prism(slab, z - SLAB_BELOW, z + SLAB, 'White band', top, 'White band')


# ----------------------------------------------------------------------------
# Residential tower
# ----------------------------------------------------------------------------

def level_heights(T):
    zs = [0.0]
    for h in T['base']:
        zs.append(zs[-1] + h)
    for _ in range(T['typical']):
        zs.append(zs[-1] + T['typ_h'])
    for s in T['setbacks']:
        zs.append(zs[-1] + s['h'])
    return zs  # floor levels incl. roof level as last entry


def build_residential(T, mats, root_col):
    col = get_collection(f"Tower {T['key']}", root_col)
    origin, rot = T['origin'], T['rot']
    zs = level_heights(T)
    nb, nt = len(T['base']), T['typical']
    core = residential_plan(T)
    slab = balcony_outline(T, core)
    objs = {}

    def finish(mb, name):
        me = mb.to_mesh(name, mats)
        ob = make_object(name, me, col)
        ob.location = (origin[0], origin[1], 0)
        ob.rotation_euler = (0, 0, math.radians(rot))
        return ob

    # --- base levels (lobby + podium floors inside the tower footprint) ------
    mb = MeshBuilder()
    base_poly = slab.buffer(-0.6)
    for i in range(nb):
        z0, z1 = zs[i], zs[i + 1]
        if i > 0:
            mb.prism(base_poly.buffer(0.25), z0 - 0.35, z0 + 0.35, 'White band', None, 'White band')
        # terracotta spandrel + ribbon glazing
        mb.prism(base_poly, z0 + 0.35, z0 + 1.1 if i else z0 + 0.35, 'Terracotta')
        ring = simplify_ring(ring_coords(base_poly), tol=0.002)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            glazed_wall(mb, a, b, (z0 + 1.1) if i else z0, z1 - 0.35, 'Shop glass' if i == 0 else 'Window glass', step=2.4)
    finish(mb, f"{T['key']} base")

    # --- residential floors: one slab object (slab edge, balconies, rails) and one walls object each,
    # so the web viewer can open a floor up for the cut-away view and the walk-through ---------------
    h = T['typ_h']
    rails = rail_segments(T, slab, core.exterior)

    def floor_objects(lvl, slab_me, walls_me):
        for part, me in (('slab', slab_me), ('walls', walls_me)):
            name = f"{T['key']} {'floor' if part == 'slab' else 'walls'} {lvl + 1:02d}"
            ob = make_object(name, me, col)
            ob.location = (origin[0], origin[1], zs[lvl])
            ob.rotation_euler = (0, 0, math.radians(rot))
            ob['tower'] = T['key']
            ob['floor'] = lvl + 1
            ob['part'] = part

    mb = MeshBuilder()
    slab_band(mb, slab, 0.0)
    add_rails(mb, rails, SLAB)
    slab_typ = mb.to_mesh(f"{T['key']} typical slab", mats)

    def walls_mesh(name, south_glass=None):
        mb = MeshBuilder()
        wall_ring(mb, T, core, SLAB, h - SLAB_BELOW, south_glass=south_glass)
        return mb.to_mesh(name, mats)

    walls_typ = walls_mesh(f"{T['key']} typical walls")
    stained = T.get('stained', {})
    plates = {}
    for k in range(nt):
        lvl = nb + k  # 0-based level index
        wm = walls_mesh(f"{T['key']} walls {k}", stained[k]) if k in stained else walls_typ
        floor_objects(lvl, slab_typ, wm)
        plates[lvl] = (slab, core, h)

    prev_core, prev_slab = core, slab
    for k, s in enumerate(T['setbacks']):
        lvl = nb + nt + k
        z0, z1 = zs[lvl], zs[lvl + 1]
        c = residential_plan(T, s.get('front_l', 0), s.get('front_r', 0), s.get('back', 0), s.get('bar_front', 0))
        fl = unary_union([prev_core.buffer(0.35, join_style='mitre'), c.buffer(0.35, join_style='mitre')]) if k else prev_slab
        fl = biggest(fl)
        mb = MeshBuilder()
        slab_band(mb, fl, 0.0, top='Paving')
        add_rails(mb, rail_segments(T, fl, c.exterior), SLAB)
        planters(mb, fl, c, SLAB)
        sm = mb.to_mesh(f"{T['key']} setback slab {k}", mats)
        mb = MeshBuilder()
        wall_ring(mb, T, c, SLAB, z1 - z0 - SLAB_BELOW)
        floor_objects(lvl, sm, mb.to_mesh(f"{T['key']} setback walls {k}", mats))
        plates[lvl] = (fl, c, z1 - z0)
        prev_core, prev_slab = c, fl
    mb = MeshBuilder()
    zr = zs[-1]
    roof = biggest(prev_core.buffer(0.45, join_style='mitre'))
    roof_and_crown(mb, T, roof, zr)
    top = finish(mb, f"{T['key']} roof")
    top['tower'] = T['key']
    top['part'] = 'roof'
    return describe_tower(T, zs, nb, plates, col)


# ----------------------------------------------------------------------------
# Apartments: four per residential floor, each a rectangle in the tower's frame.
# S/N: the large units behind the flat terracotta ends of the central bay,
# E/W: the small units on the straight part of the curved balcony sides.
# ----------------------------------------------------------------------------

UNIT_D = 6.65  # must match src/config.js
WALL_IN = 0.25


def unit_frames(T):
    bw = T['bar_w']
    x0, y0, x1, y1 = T['body']
    yn = y1 + T['bar_back']
    Wl = round(bw - 0.5, 2)
    Ws = 9.65
    yc = (y0 + T['r_front'] + y1 - T['r_back']) / 2
    D = UNIT_D
    return {
        'S': dict(type='large', W=Wl, o=(Wl / 2, WALL_IN + D), eu=(-1, 0), ev=(0, -1), view='South · city & park'),
        'E': dict(type='small', W=Ws, o=(x1 - WALL_IN - D, yc + Ws / 2), eu=(0, -1), ev=(1, 0), view='East · avenue & bridge'),
        'N': dict(type='large', W=Wl, o=(-Wl / 2, yn - WALL_IN - D), eu=(1, 0), ev=(0, 1), view='North · river'),
        'W': dict(type='small', W=Ws, o=(x0 + WALL_IN + D, yc - Ws / 2), eu=(0, 1), ev=(-1, 0), view='West · park'),
    }


def unit_zones(T, plate):
    """Split a floor plate in four zones, one per apartment (used to pick and highlight)."""
    D = UNIT_D
    y_s = WALL_IN + D + 1.2
    y_n = T['body'][3] + T['bar_back'] - (WALL_IN + D + 1.2)
    big = 200
    return {
        'S': plate.intersection(box(-big, -big, big, y_s)),
        'N': plate.intersection(box(-big, y_n, big, big)),
        'E': plate.intersection(box(0, y_s, big, y_n)),
        'W': plate.intersection(box(-big, y_s, 0, y_n)),
    }


def describe_tower(T, zs, nb, plates, col):
    pick_col = get_collection('Picking', col)
    frames = unit_frames(T)
    floors = []
    for lvl in sorted(plates):
        plate, core, h = plates[lvl]
        # slightly larger than the floor so the highlight wraps around the facade instead of z-fighting with it
        for key, zone in unit_zones(T, plate.buffer(0.3, join_style='mitre')).items():
            if zone.is_empty:
                continue
            mb = MeshBuilder()
            mb.prism(zone.simplify(0.15), -0.3, h - 0.1, 'Pick', 'Pick', 'Pick')
            name = f"pick {T['key']} {lvl + 1:02d} {key}"
            ob = make_object(name, mb.to_mesh(name, {'Pick': pick_material()}), pick_col)
            ob.location = (T['origin'][0], T['origin'][1], zs[lvl] + SLAB)
            ob.rotation_euler = (0, 0, math.radians(T['rot']))
            ob['tower'] = T['key']
            ob['floor'] = lvl + 1
            ob['unit'] = key
            ob['pick'] = 1
            ob.hide_render = True
        floors.append(dict(floor=lvl + 1, z=round(zs[lvl], 3), h=round(zs[lvl + 1] - zs[lvl], 3)))
    return dict(key=T['key'], label=T['label'], origin=list(T['origin']), rot=T['rot'], slab=SLAB,
                floors=floors, levels=len(zs) - 1, top=round(zs[-1], 3),
                units={k: dict(v, o=list(v['o']), eu=list(v['eu']), ev=list(v['ev'])) for k, v in frames.items()})


def pick_material():
    """Plain material for the invisible pick volumes (the viewer replaces it)."""
    import bpy
    m = bpy.data.materials.get('Pick')
    if m is None:
        m = bpy.data.materials.new('Pick')
        m.diffuse_color = (1, 1, 1, 0.2)
    return m


def planters(mb, terrace, core, z):
    """A few green planters on each terrace strip."""
    free = terrace.difference(core.buffer(0.3))
    for g in getattr(free, 'geoms', [free]):
        if g.area < 4:
            continue
        rp = g.representative_point()
        mb.box(rp.x, rp.y, z, 0.9, 0.9, 0.45, 'Frame')
        mb.prism(Point(rp.x, rp.y).buffer(0.55, quad_segs=3), z + 0.45, z + 1.25, 'Shrub', 'Shrub')


def roof_and_crown(mb, T, roof, zr):
    # roof slab with thick white edge, pink membrane on top
    mb.prism(roof, zr - SLAB_BELOW, zr + 0.55, 'White band', None, 'White band')
    mb.polygon_face(roof.buffer(-0.5), zr + 0.56, 'Roof')
    inner = roof.buffer(-0.5)
    mb.prism(roof.difference(inner), zr + 0.55, zr + 0.85, 'White band', 'White band')
    # plant room
    p = T['plant']
    (cx, cy), (sx, sy) = p['c'], p['size']
    mb.box(cx, cy, zr + 0.55, sx, sy, p['h'], 'Plant room', top=False)
    mb.polygon_face(box(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2), zr + 0.55 + p['h'], 'Roof')
    keep_out = box(cx - sx / 2 - 1.2, cy - sy / 2 - 1.2, cx + sx / 2 + 1.2, cy + sy / 2 + 1.2)
    solar_field(mb, roof.buffer(-2.2).difference(keep_out), zr + 0.56, angle=-32)
    crown(mb, T, roof, zr + 0.85)


def solar_field(mb, area, z, angle=-30, pw=1.0, pl=1.7, row=4.6, group=6, gap=3.6):
    """Strips of tilted PV panels; the field is rotated by `angle` degrees like on the renders."""
    if area.is_empty:
        return
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    minx, miny, maxx, maxy = area.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    R = max(maxx - minx, maxy - miny)
    tilt = math.radians(18)
    v = -R
    row_i = 0
    while v < R:
        u = -R + (row_i % 2) * 2.5
        while u < R:
            for k in range(group):
                uu = u + k * (pw + 0.04)
                x = cx + ca * uu - sa * v
                y = cy + sa * uu + ca * v
                corners = [(x + ca * du - sa * dv, y + sa * du + ca * dv)
                           for du, dv in [(-pw / 2, -pl / 2), (pw / 2, -pl / 2), (pw / 2, pl / 2), (-pw / 2, pl / 2)]]
                if not area.contains(Polygon(corners)):
                    continue
                for dv2 in (0.0, pl + 0.05):
                    cc = [(px - sa * dv2, py + ca * dv2) for px, py in corners]
                    if not area.contains(Polygon(cc)):
                        continue
                    zl = z + 0.3 + dv2 * math.sin(tilt) * 0.0
                    zh = zl + pl * math.sin(tilt)
                    c0, c1 = cc[:2], cc[2:]
                    mb.face([(*c0[0], zl), (*c0[1], zl), (*c1[0], zh), (*c1[1], zh)], 'Solar panel')
                    mb.face([(*c1[1], zh), (*c1[0], zh), (*c0[1], zl), (*c0[0], zl)], 'Frame')
            u += group * (pw + 0.04) + gap
        v += row
        row_i += 1


def longest_run(mask):
    """Indices of the longest cyclic run of True values in a boolean array."""
    n = len(mask)
    if mask.all():
        return list(range(n))
    if not mask.any():
        return []
    f = int(np.where(~mask)[0][0])
    runs, cur = [], []
    for i in np.roll(np.arange(n), -f):
        if mask[i]:
            cur.append(int(i))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return max(runs, key=len)


def crown(mb, T, roof, z):
    """White visor ring on slim posts, high over the north end and dipping to the roof at the front."""
    cr = T['crown']
    ring = roof.buffer(0.15, join_style='round')
    pts = ring_coords(ring)
    # keep the part north of y_start, ordered from the east front corner round the back to the west
    pts = np.array(resample(pts, 0.8))
    run = longest_run(pts[:, 1] > cr['y_start'])
    if not run:
        return
    P = pts[run]
    y0, y1 = cr['y_start'], P[:, 1].max()
    t = np.clip((P[:, 1] - y0) / max(y1 - y0, 1e-3), 0, 1)
    t = t * t * (3 - 2 * t)
    hz = z + cr['front'] + (cr['back'] - cr['front']) * t
    mb.tube([tuple(p) for p in P], list(hz - 0.42), list(hz), 0.95, 'White band')
    # posts
    for k in range(0, len(P), 1):
        x, y = P[k]
        mb.box(x, y, z, 0.12, 0.12, hz[k] - 0.42 - z, 'White band')


# ----------------------------------------------------------------------------
# Hotel (block A)
# ----------------------------------------------------------------------------

TOWER_A = dict(
    key='A', label='Block A (hotel)', origin=(40.75, 184.7), rot=-10.7,
    glass_w=12.9, body=(-15.0, 1.6, 21.5, 31.0), r_west=8.5, r_east=14.7, balcony=2.1,
    base=[4.0, 4.4, 4.4],
    floors=14, typ_h=3.0,
    west_glass_from=10,    # from this hotel floor up the west end is glazed, no balconies
    east_closed_from=13,   # top floors at the east end without balconies
    plant=dict(c=(4.0, 17.0), size=(14.0, 8.0), h=3.4),
)


def hotel_core(H):
    x0, y0, x1, y1 = H['body']
    body = rounded_rect(x0, y0, x1, y1, H['r_west'], H['r_east'], H['r_east'], H['r_west'])
    gw = H['glass_w']
    bar = box(-gw / 2, 0.0, gw / 2, y1 + 1.2)
    return unary_union([body, bar]).buffer(0.01).buffer(-0.01)


def build_hotel(H, mats, root_col):
    col = get_collection(f"Tower {H['key']}", root_col)
    origin, rot = H['origin'], H['rot']
    zs = [0.0]
    for h in H['base']:
        zs.append(zs[-1] + h)
    for _ in range(H['floors']):
        zs.append(zs[-1] + H['typ_h'])
    nb = len(H['base'])
    core = hotel_core(H)
    x0, y0, x1, y1 = H['body']
    gw = H['glass_w']
    body = rounded_rect(x0, y0, x1, y1, H['r_west'], H['r_east'], H['r_east'], H['r_west'])
    full_balc = unary_union([body.buffer(H['balcony'], quad_segs=12).intersection(box(-100, 0, 100, y1 + 1.2)), core])
    east_only = unary_union([full_balc.intersection(box(gw / 2, -100, 100, 100)), core])
    no_balc = core.buffer(0.3, join_style='mitre')

    def put(ob, z=0.0):
        ob.location = (origin[0], origin[1], z)
        ob.rotation_euler = (0, 0, math.radians(rot))
        return ob

    def is_glass_front(a, b):
        return (abs(a[1]) < 0.05 and abs(b[1]) < 0.05 and max(abs(a[0]), abs(b[0])) <= gw / 2 + 0.05) or \
               (abs(a[1] - (y1 + 1.2)) < 0.05 and abs(b[1] - (y1 + 1.2)) < 0.05 and max(abs(a[0]), abs(b[0])) <= gw / 2 + 0.05)

    # base (lobby levels)
    mb = MeshBuilder()
    bp = full_balc.buffer(-0.4)
    for i in range(nb):
        z0, z1 = zs[i], zs[i + 1]
        if i:
            mb.prism(bp.buffer(0.25), z0 - 0.35, z0 + 0.35, 'White band', None, 'White band')
        ring = simplify_ring(ring_coords(bp), tol=0.002)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            glazed_wall(mb, a, b, z0 + (0.35 if i else 0), z1 - 0.35, 'Shop glass', step=2.4)
    put(make_object('A base', mb.to_mesh('A base', mats), col))

    variants = {}
    for k in range(H['floors']):
        lvl = nb + k
        z0, z1 = zs[lvl], zs[lvl + 1]
        hf = k + 1
        if hf >= H['east_closed_from']:
            sl, var = no_balc, 'closed'
        elif hf >= H['west_glass_from']:
            sl, var = east_only, 'east'
        else:
            sl, var = full_balc, 'full'
        if var in variants:
            ob = put(make_object(f'A floor {lvl + 1:02d}', variants[var], col), z0)
            ob['floor'] = lvl + 1
            ob['tower'] = 'A'
            continue
        mb = MeshBuilder()
        slab_band(mb, sl, 0.0)
        hgt = z1 - z0
        ring = simplify_ring(ring_coords(core), tol=0.002)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if is_glass_front(a, b):
                curtain_wall(mb, a, b, 0.0, hgt)
            elif abs(abs(a[0]) - gw / 2) < 0.05 and abs(a[0] - b[0]) < 0.05:
                mb.quad_wall(a, b, SLAB, hgt - SLAB_BELOW, 'Terracotta')
            else:
                glazed_wall(mb, a, b, SLAB, hgt - SLAB_BELOW, 'Window glass')
        if sl is not no_balc:
            add_rails(mb, rail_segments(H, sl, core.exterior), SLAB)
        variants[var] = mb.to_mesh(f'A floor {var}', mats)
        ob = put(make_object(f'A floor {lvl + 1:02d}', variants[var], col), z0)
        ob['floor'] = lvl + 1
        ob['tower'] = 'A'

    # fins, roof, crown
    mb = MeshBuilder()
    zr = zs[-1]
    # white fin west of the south curtain wall; tall stone fin with HOTEL east of the north curtain wall
    mb.box(-gw / 2 - 0.45, 0.2, 0.0, 0.9, 2.2, zr + 4.5, 'White band')
    fin_x, fin_y = gw / 2 + 1.2, y1 + 1.6
    mb.box(fin_x, fin_y, zs[nb], 2.6, 1.4, zr - zs[nb] + 6.0, 'Stone fin')
    roof = core.buffer(0.45, join_style='mitre')
    mb.prism(roof, zr - SLAB_BELOW, zr + 0.55, 'White band', None, 'White band')
    mb.polygon_face(roof.buffer(-0.5), zr + 0.56, 'Roof')
    p = H['plant']
    (cx, cy), (sx, sy) = p['c'], p['size']
    mb.box(cx, cy, zr + 0.55, sx, sy, p['h'], 'Plant room', top=False)
    mb.polygon_face(box(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2), zr + 0.55 + p['h'], 'Roof')
    keep_out = box(cx - sx / 2 - 1.2, cy - sy / 2 - 1.2, cx + sx / 2 + 1.2, cy + sy / 2 + 1.2)
    solar_field(mb, roof.buffer(-2.4).difference(keep_out), zr + 0.56, angle=-35)
    hotel_crown(mb, H, roof, zr + 0.55)
    top = put(make_object('A roof', mb.to_mesh('A roof', mats), col))
    top['tower'] = 'A'
    top['part'] = 'roof'
    # one pick volume for the whole hotel
    mb = MeshBuilder()
    mb.prism(full_balc.simplify(0.2), 0.0, zr, 'Pick', 'Pick', 'Pick')
    pick = put(make_object('pick A hotel', mb.to_mesh('pick A hotel', {'Pick': pick_material()}), get_collection('Picking', col)))
    pick['tower'] = 'A'
    pick['pick'] = 1
    pick['hotel'] = 1
    pick.hide_render = True
    # vertical HOTEL lettering on the fin (baked to a mesh, parented to the fin's frame)
    from .podium import add_sign
    import mathutils
    letters = 'HOTEL'
    top = zr - 3.0
    for i, ch in enumerate(letters):
        z = top - i * 4.2
        p = mathutils.Matrix.Translation((origin[0], origin[1], 0)) @ mathutils.Matrix.Rotation(math.radians(rot), 4, 'Z') @ mathutils.Vector((fin_x, fin_y + 0.72, z, 1.0))
        add_sign(ch, p.xyz[:], math.radians(rot) + math.pi, mats, col, size=2.0, mat='Terracotta dark')
    return dict(key=H['key'], label=H['label'], origin=list(origin), rot=rot, levels=len(zs) - 1, top=round(zs[-1], 3), hotel=True)


def curtain_wall(mb, a, b, z0, z1, mull=1.6):
    """Green glass curtain wall with a terracotta frame and a central pier."""
    a, b = np.array(a, float), np.array(b, float)
    L = np.linalg.norm(b - a)
    t = (b - a) / L
    nrm = np.array([t[1], -t[0]])
    rot = math.atan2(t[1], t[0])
    o = nrm * 0.35
    mb.quad_wall(tuple(a + o), tuple(b + o), z0 - SLAB_BELOW, z1 - SLAB_BELOW, 'Curtain glass')
    # pier in the middle and at the ends
    for f, w in [(0.0, 0.7), (0.5, 0.9), (1.0, 0.7)]:
        q = a + t * L * f + nrm * 0.45
        mb.box(q[0], q[1], z0 - SLAB_BELOW, w, 0.5, z1 - z0, 'Terracotta', rot=rot)
    n = int(round(L / mull))
    for i in range(1, n):
        q = a + t * L * i / n + nrm * 0.4
        mb.box(q[0], q[1], z0 - SLAB_BELOW, 0.07, 0.12, z1 - z0, 'Frame', rot=rot)
    q = (a + b) / 2 + nrm * 0.4
    mb.box(q[0], q[1], z0 - SLAB_BELOW, L, 0.14, 0.12, 'Frame', rot=rot)


def hotel_crown(mb, H, roof, z):
    """Hotel crown: slatted terracotta screen under a white frame rising towards the east end."""
    ring = roof.buffer(0.1)
    pts = np.array(resample(ring_coords(ring), 0.7))
    x0, y0, x1, y1 = H['body']
    gw = H['glass_w']
    # whole ring except the south glass front
    mask = ~((pts[:, 1] < 0.6) & (np.abs(pts[:, 0]) < gw / 2 + 0.6))
    run = longest_run(mask)
    P = pts[run]
    t = np.clip((P[:, 0] - x0) / (x1 - x0), 0, 1)
    hz = z + 1.4 + 3.6 * t ** 1.5
    mb.tube([tuple(p) for p in P], list(hz - 0.45), list(hz), 0.9, 'White band')
    for k in range(len(P)):
        mb.box(P[k][0], P[k][1], z, 0.22, 0.22, hz[k] - 0.45 - z, 'Terracotta')
