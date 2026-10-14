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
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from .geom import MeshBuilder, get_collection, make_object, resample, ring_coords, rounded_rect, simplify_ring

SLAB = 0.32        # slab top above floor level datum
SLAB_BELOW = 0.18  # band continues below floor level
RAIL = 1.05        # glass rail height
FASCIA = 0.42      # solid white upstand on the balcony edge, under the glass rail


# ----------------------------------------------------------------------------
# Tower definitions (metres, site frame of the reference camera)
# ----------------------------------------------------------------------------

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


def rail_segments(T, slab, exclude):
    """Parts of the slab edge that get a glass rail (everything except bar faces / walls)."""
    edge = slab.exterior
    keep = edge.difference(exclude.buffer(0.12))
    lines = [keep] if keep.geom_type == 'LineString' else list(getattr(keep, 'geoms', []))
    return [list(l.coords) for l in lines if l.length > 0.3]


def add_rails(mb, segs, z, h=RAIL, mat='Railing glass', post_step=1.2):
    for seg in segs:
        # solid white upstand, then glass
        if len(seg) > 1:
            mb.tube(seg, [z - 0.05] * len(seg), [z + FASCIA] * len(seg), 0.16, 'White band')
        mb.ribbon(seg, z + FASCIA, z + h, mat, double=True)
        # slim metal handrail on posts (glass held between them)
        zs0 = [z + h - 0.04] * len(seg)
        zs1 = [z + h + 0.02] * len(seg)
        if len(seg) > 1:
            mb.tube(seg, zs0, zs1, 0.06, 'Frame')
        if post_step and len(seg) > 1:
            P = np.array(seg, float)
            d = np.linalg.norm(np.diff(P, axis=0), axis=1)
            s = np.concatenate([[0.0], np.cumsum(d)])
            total = s[-1]
            for k in range(int(total // post_step) + 1):
                at = min(total, k * post_step + (total - post_step * int(total // post_step)) / 2)
                i = min(int(np.searchsorted(s, at, side='right')) - 1, len(d) - 1)
                f = (at - s[i]) / max(d[i], 1e-9)
                q = P[i] + (P[i + 1] - P[i]) * f
                t = (P[i + 1] - P[i]) / max(d[i], 1e-9)
                mb.box(q[0], q[1], z + FASCIA, 0.04, 0.05, h - FASCIA - 0.04, 'Metal', rot=math.atan2(t[1], t[0]))


def slab_band(mb, slab, z, top='White band'):
    mb.prism_chamfer(slab, z - SLAB_BELOW, z + SLAB, 'White band', top, 'White band', c=0.025)


# ----------------------------------------------------------------------------
# Residential tower
# ----------------------------------------------------------------------------

def pick_material():
    """Plain material for the invisible pick volumes (the viewer replaces it)."""
    import bpy
    m = bpy.data.materials.get('Pick')
    if m is None:
        m = bpy.data.materials.new('Pick')
        m.diffuse_color = (1, 1, 1, 0.2)
    return m


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


TOWER_A = dict(
    key='A', label='Block A (hotel)', origin=(40.75, 184.7), rot=-10.7,
    glass_w=12.9, body=(-15.0, 1.6, 21.5, 31.0), r_west=8.5, r_east=14.7, balcony=2.1,
    # levels from section 1-1: lobby 6.0 m, two podium floors of 4.2 m, then 3.6 m hotel floors
    # ("Гост. Эт_5".."Гост. Эт_16"), roof at +61.8
    base=[6.0, 4.2, 4.2, 4.2],
    floors=12, typ_h=3.6,
    west_glass_from=9,     # from this hotel floor up the west end is glazed, no balconies
    east_closed_from=11,   # top floors at the east end without balconies
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
