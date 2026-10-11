"""Curved retail podium (shops, glass gallery, copper brand band) and its roof decks.

East part (hotel -> block B): 3 levels, pool deck at +15.0 m.
West wing (block B -> block V): one more glazed level, playground deck at +20.5 m.
"""
import math

import bpy
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box

from .geom import MeshBuilder, biggest, get_collection, make_object, ring_coords, simplify_ring

GF_TOP = 6.0       # shops
L2_TOP = 10.5      # glass gallery
DECK_E = 15.0      # copper band level, pool deck
DECK_W = 20.5      # west wing extra level, playground deck

def _chaikin(pts, rounds):
    """Corner-cutting smoothing that keeps both ends: each segment a->b becomes 0.75a+0.25b, 0.25a+0.75b."""
    for _ in range(rounds):
        out = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
            out += [(0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by), (0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by)]
        out.append(pts[-1])
        pts = out
    return pts


# Outline of the podium (site metres). Outer edge = the long shop front along the river road,
# smoothed so the shop front, parapet and promenade curve evenly instead of kinking at each point.
OUTER = _chaikin([(-61.0, 240.0), (-63.0, 252.0), (-60.5, 266.0), (-53.0, 279.0), (-40.0, 288.0), (-20.0, 292.5), (0.0, 293.5),
                  (20.0, 291.5), (38.0, 285.0), (53.0, 274.0), (63.0, 260.0), (68.5, 244.0), (69.5, 229.0), (66.0, 216.0)], 2)
INNER = [(64.0, 210.0), (52.0, 212.0), (30.0, 216.5), (22.0, 224.0), (24.0, 230.0), (14.0, 236.0), (4.5, 242.5),
         (-15.0, 243.0), (-17.0, 241.0), (-52.0, 241.0), (-58.0, 240.0)]

# Two-storey wedge in front of the hotel with a roof terrace (south-east of the hotel): its facade line,
# re-measured on render 1 at the terrace height (straight west side from the hotel's fin, round tip, east side
# clear of the inner east road up to the podium, rounded north-east corner). complex/wedge.py builds it from
# the exact lines and arcs (wedge.coarse_outline() prints this list); this coarse outline is for the neighbours
HOTEL_WEDGE = [(31.3, 190.0), (48.8, 165.9), (50.1, 164.8), (52.3, 164.0), (54.7, 163.9), (56.9, 164.6), (58.8, 165.9),
               (59.9, 167.3), (60.4, 168.4), (71.9, 207.8), (71.8, 208.8), (71.1, 209.5), (70.6, 209.6), (58.0, 209.6),
               (45.0, 197.0)]
WEDGE_TOP = 10.2   # the terrace meets the hotel at its first floor over the lobby (6.0 + 4.2)
SPLIT_X = 22.0     # west of this the podium has the extra level


def podium_polygon():
    return Polygon(OUTER + INNER).buffer(0)


def west_wing(poly):
    """Upper level of the west wing, set back from the shop front."""
    outer_line = LineString(OUTER)
    clip = box(-100, 200, SPLIT_X, 320)
    return biggest(poly.intersection(clip).difference(outer_line.buffer(4.5)))


def is_outer(a, b):
    line = LineString(OUTER)
    return line.distance(Point(a)) < 0.3 and line.distance(Point(b)) < 0.3


def build_podium(mats, root_col):
    col = get_collection('Podium', root_col)
    poly = podium_polygon()
    ww = west_wing(poly)
    mb = MeshBuilder()
    ring = simplify_ring(ring_coords(poly), tol=0.001)
    signs = []
    try:  # detailed shop front (perforated copper band, logos) when available
        from .facade import shop_front as front
    except Exception:
        front = shop_front
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if is_outer(a, b):
            front(mb, a, b, signs)
        else:
            land_side(mb, a, b, 0.0, DECK_E)
    # floors / deck slabs
    mb.prism(poly, DECK_E - 0.6, DECK_E, 'White band', 'Paving', None)
    mb.prism(poly.buffer(0.6, join_style='mitre').difference(poly.buffer(-0.01)), GF_TOP - 0.5, GF_TOP + 0.2, 'White band', 'White band', 'White band')
    mb.prism(poly.buffer(0.35, join_style='mitre').difference(poly.buffer(-0.01)), L2_TOP - 0.3, L2_TOP + 0.3, 'White band', 'White band', 'White band')

    # west wing extra level
    wr = simplify_ring(ring_coords(ww), tol=0.001)
    for a, b in zip(wr, wr[1:] + wr[:1]):
        if LineString(OUTER).distance(Point(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))) < 6.0:
            gallery(mb, a, b, DECK_E, DECK_W)
        else:
            land_side(mb, a, b, DECK_E, DECK_W)
    mb.prism(ww, DECK_W - 0.6, DECK_W, 'White band', 'Paving', None)
    mb.prism(ww.buffer(0.4, join_style='mitre').difference(ww.buffer(-0.01)), DECK_W - 0.6, DECK_W + 0.25, 'White band', 'White band', 'White band')
    ob = make_object('Podium', mb.to_mesh('Podium', mats), col)

    # brand signs as real text on the copper band
    for (p, ang, text) in signs:
        add_sign(text, p, ang, mats, col)
    build_decks(mats, col, poly, ww)
    hotel_wedge(mats, col)
    return ob


def hotel_wedge(mats, col):
    """Terrace wing in front of the hotel: the detailed wing of complex/wedge.py (copper band, coping
    and glass balustrade, stone terrace, planting), or the plain block below if that is not available."""
    try:
        from .wedge import build_wedge
        return build_wedge(mats, col)
    except Exception:
        import traceback
        print('[podium] hotel wedge: detailed wing failed, using the plain one')
        traceback.print_exc()
        for ob in [o for o in col.objects if o.name.startswith('Hotel terrace wing')]:
            bpy.data.objects.remove(ob)
    mb = MeshBuilder()
    w = Polygon(HOTEL_WEDGE).buffer(-3.0).buffer(3.0)
    ring = simplify_ring(ring_coords(w), tol=0.001)
    for a, b in zip(ring, ring[1:] + ring[:1]):
        a2, b2 = np.array(a), np.array(b)
        t = (b2 - a2) / (np.linalg.norm(b2 - a2) + 1e-9)
        n = np.array([t[1], -t[0]])
        # heights follow WEDGE_TOP so the plain wing closes up to its roof slab
        mb.quad_wall(a, b, 0.0, WEDGE_TOP - 4.8, 'Shop glass')
        mb.quad_wall(a, b, WEDGE_TOP - 4.8, WEDGE_TOP - 4.1, 'White band')
        mb.quad_wall(tuple(a2 + n * 0.15), tuple(b2 + n * 0.15), WEDGE_TOP - 4.1, WEDGE_TOP - 1.0, 'Terracotta')
    mb.prism(w.buffer(0.5), WEDGE_TOP - 1.0, WEDGE_TOP + 0.2, 'White band', None, 'White band')
    mb.polygon_face(w.buffer(-0.3), WEDGE_TOP + 0.21, 'Deck paving')
    deck_rail(mb, w.buffer(0.3), WEDGE_TOP + 0.2)
    for (x, y) in [(50.0, 182.0), (57.0, 170.0), (62.0, 185.0), (44.0, 190.0)]:
        tree(mb, x, y, WEDGE_TOP + 0.2, 4.0, 1.3, light=True)
    make_object('Hotel terrace wing', mb.to_mesh('Hotel terrace wing', mats), col)


BRANDS = ['ChristianDior', 'asics', 'adidas', 'MEXX', 'MOSCHINO', 'LC WAIKIKI', 'Levi\'s', 'ecco', 'Columbia', 'Bershka']


def shop_front(mb, a, b, signs):
    a, b = np.array(a, float), np.array(b, float)
    L = np.linalg.norm(b - a)
    t = (b - a) / L
    n = np.array([t[1], -t[0]])
    rot = math.atan2(t[1], t[0])
    # ground floor shop glass set back under a white canopy, stone pilasters
    mb.quad_wall(tuple(a - n * 1.2), tuple(b - n * 1.2), 0.0, GF_TOP - 0.5, 'Shop glass')
    k = max(1, int(round(L / 7.5)))
    for i in range(k + 1):
        q = a + t * (L * i / k) - n * 0.9
        mb.box(q[0], q[1], 0.0, 0.8, 0.8, GF_TOP - 0.5, 'Terracotta dark', rot=rot)
    # L2 glass gallery with mullions
    mb.quad_wall(tuple(a), tuple(b), GF_TOP + 0.2, L2_TOP - 0.3, 'Shop glass')
    k = max(1, int(round(L / 1.8)))
    for i in range(k):
        q = a + t * (L * i / k) + n * 0.03
        mb.box(q[0], q[1], GF_TOP + 0.2, 0.08, 0.12, L2_TOP - GF_TOP - 0.5, 'Frame', rot=rot)
    # L3 perforated copper band, slightly proud of the glass line
    mb.quad_wall(tuple(a), tuple(b), L2_TOP + 0.3, DECK_E - 0.6, 'Shop glass')
    mb.quad_wall(tuple(a + n * 0.25), tuple(b + n * 0.25), L2_TOP + 0.3, DECK_E - 0.6, 'Copper screen')
    k = max(1, int(round(L / 12.0)))
    for i in range(k):
        q = a + t * (L * (i + 0.5) / k) + n * 0.32
        signs.append(((q[0], q[1], (L2_TOP + DECK_E) / 2 - 0.2), rot, BRANDS[len(signs) % len(BRANDS)]))


def gallery(mb, a, b, z0, z1):
    a, b = np.array(a, float), np.array(b, float)
    L = np.linalg.norm(b - a)
    t = (b - a) / L
    rot = math.atan2(t[1], t[0])
    mb.quad_wall(tuple(a), tuple(b), z0, z1 - 0.6, 'Shop glass')
    k = max(1, int(round(L / 1.8)))
    for i in range(k):
        q = a + t * (L * i / k)
        mb.box(q[0], q[1], z0, 0.08, 0.12, z1 - z0 - 0.6, 'Frame', rot=rot)


def land_side(mb, a, b, z0, z1, step=4.1):
    """Back faces: terracotta with white bands and ribbon windows (as seen from the land side)."""
    a, b = np.array(a, float), np.array(b, float)
    L = np.linalg.norm(b - a)
    if L < 0.05:
        return
    t = (b - a) / L
    n = np.array([t[1], -t[0]])
    z = z0
    while z < z1 - 0.5:
        top = min(z + step, z1)
        mb.quad_wall(tuple(a), tuple(b), z, z + 1.3, 'Terracotta')
        mb.quad_wall(tuple(a), tuple(b), z + 1.3, top - 0.45, 'Window glass')
        mb.quad_wall(tuple(a + n * 0.25), tuple(b + n * 0.25), top - 0.45, top + 0.1, 'White band')
        z = top


def deck_rail(mb, poly, z, exclude=None, h=1.1):
    edge = poly.exterior
    if exclude is not None:
        edge = edge.difference(exclude.buffer(0.3))
    lines = [edge] if edge.geom_type in ('LineString', 'LinearRing') else list(edge.geoms)
    for l in lines:
        pts = list(l.coords)
        if len(pts) < 2:
            continue
        mb.ribbon(pts, z, z + h, 'Railing glass', double=True)


def add_sign(text, p, ang, mats, col, size=1.25, mat='Sign'):
    cu = bpy.data.curves.new('sign', 'FONT')
    cu.body = text
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.extrude = 0.04
    ob = bpy.data.objects.new('sign', cu)
    col.objects.link(ob)
    ob.location = p
    ob.rotation_euler = (math.pi / 2, 0, ang)
    ob.data.materials.append(mats[mat])
    # bake to a mesh so the GLB carries it
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.materials.clear()
    me.materials.append(mats[mat])
    mo = bpy.data.objects.new(f'Sign {text}', me)
    mo.matrix_world = ob.matrix_world
    col.objects.link(mo)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return mo


# ----------------------------------------------------------------------------
# Roof decks: pool deck (east) and playground deck (west wing)
# ----------------------------------------------------------------------------

def tree(mb, x, y, z, h=5.0, r=1.8, light=False):
    mb.prism(Point(x, y).buffer(0.18, quad_segs=2), z, z + h * 0.55, 'Trunk')
    leaf = 'Leaves light' if light else 'Leaves'
    mb.blob(x, y, z + h * 0.68, r, r, r * 0.9, leaf, subdiv=1)
    mb.blob(x + r * 0.3, y - r * 0.2, z + h * 0.9, r * 0.65, r * 0.65, r * 0.6, leaf, subdiv=1)


def gazebo(mb, x, y, z, r=2.6, h=3.0):
    """Wooden pergola: ring of posts and a slatted round top."""
    for k in range(8):
        a = k * math.pi / 4
        mb.box(x + r * math.cos(a), y + r * math.sin(a), z, 0.16, 0.16, h, 'Wood')
    ring = Point(x, y).buffer(r + 0.2, quad_segs=4).difference(Point(x, y).buffer(r - 0.2, quad_segs=4))
    mb.prism(ring, z + h, z + h + 0.2, 'Wood', 'Wood', 'Wood')
    for k in range(6):
        a = k * math.pi / 6
        mb.box(x, y, z + h + 0.2, 2 * r, 0.12, 0.12, 'Wood', rot=a)
    mb.prism(Point(x, y).buffer(0.8, quad_segs=3), z + h + 0.2, z + h + 1.3, 'Wood', 'Wood')


def build_decks(mats, col, poly, ww):
    """Roof decks: zones and parts in complex/deck/ (pool, playground, planters, parapet and rails)."""
    from . import deck
    mb = MeshBuilder()
    ctx = deck.make_context(poly, LineString(OUTER), ww, DECK_E, DECK_W, SPLIT_X)
    built = deck.build_all(mb, ctx)
    if 'edge' not in built:  # plain glass rails when the parapet part is missing
        deck_rail(mb, poly, DECK_E, exclude=ww)
        deck_rail(mb, ww, DECK_W)
    deck.find_people_spots(mb, ctx)
    make_object('Podium decks', mb.to_mesh('Podium decks', mats), col)
