"""Curved retail podium (shops, glass gallery, copper brand band) and its roof decks.

East part (hotel -> block B): 3 levels, pool deck at +15.0 m.
West wing (block B -> block V): one more glazed level, playground deck at +20.5 m.
"""
import math

import bpy
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .geom import MeshBuilder, biggest, get_collection, make_object, resample, ring_coords, simplify_ring

GF_TOP = 6.0       # shops
L2_TOP = 10.5      # glass gallery
DECK_E = 15.0      # copper band level, pool deck
DECK_W = 20.5      # west wing extra level, playground deck

# Outline of the podium (site metres). Outer edge = the long shop front along the river road.
OUTER = [(-61.0, 240.0), (-63.0, 252.0), (-60.5, 266.0), (-53.0, 279.0), (-40.0, 288.0), (-20.0, 292.5), (0.0, 293.5),
         (20.0, 291.5), (38.0, 285.0), (53.0, 274.0), (63.0, 260.0), (68.5, 244.0), (69.5, 229.0), (66.0, 216.0)]
INNER = [(64.0, 210.0), (52.0, 212.0), (30.0, 216.5), (22.0, 224.0), (24.0, 230.0), (14.0, 236.0), (4.5, 242.5),
         (-15.0, 243.0), (-17.0, 241.0), (-52.0, 241.0), (-58.0, 240.0)]

# Two-storey wedge in front of the hotel with a roof terrace (south-east of the hotel)
HOTEL_WEDGE = [(33.0, 188.5), (55.0, 160.0), (61.0, 161.0), (63.5, 167.0), (72.0, 201.0), (52.0, 206.0)]
WEDGE_TOP = 8.4
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
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if is_outer(a, b):
            shop_front(mb, a, b, signs)
        else:
            land_side(mb, a, b, 0.0, DECK_E)
    # floors / deck slabs
    mb.prism(poly, DECK_E - 0.6, DECK_E, 'White band', 'Paving', None)
    mb.prism(poly.buffer(0.6, join_style='mitre').difference(poly.buffer(-0.01)), GF_TOP - 0.5, GF_TOP + 0.2, 'White band', 'White band', 'White band')
    mb.prism(poly.buffer(0.35, join_style='mitre').difference(poly.buffer(-0.01)), L2_TOP - 0.3, L2_TOP + 0.3, 'White band', 'White band', 'White band')
    deck_rail(mb, poly, DECK_E, exclude=ww)

    # west wing extra level
    wr = simplify_ring(ring_coords(ww), tol=0.001)
    for a, b in zip(wr, wr[1:] + wr[:1]):
        if LineString(OUTER).distance(Point(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))) < 6.0:
            gallery(mb, a, b, DECK_E, DECK_W)
        else:
            land_side(mb, a, b, DECK_E, DECK_W)
    mb.prism(ww, DECK_W - 0.6, DECK_W, 'White band', 'Paving', None)
    mb.prism(ww.buffer(0.4, join_style='mitre').difference(ww.buffer(-0.01)), DECK_W - 0.6, DECK_W + 0.25, 'White band', 'White band', 'White band')
    deck_rail(mb, ww, DECK_W)
    ob = make_object('Podium', mb.to_mesh('Podium', mats), col)

    # brand signs as real text on the copper band
    for (p, ang, text) in signs:
        add_sign(text, p, ang, mats, col)
    build_decks(mats, col, poly, ww)
    hotel_wedge(mats, col)
    return ob


def hotel_wedge(mats, col):
    mb = MeshBuilder()
    w = Polygon(HOTEL_WEDGE).buffer(-3.0).buffer(3.0)
    ring = simplify_ring(ring_coords(w), tol=0.001)
    for a, b in zip(ring, ring[1:] + ring[:1]):
        a2, b2 = np.array(a), np.array(b)
        t = (b2 - a2) / (np.linalg.norm(b2 - a2) + 1e-9)
        n = np.array([t[1], -t[0]])
        mb.quad_wall(a, b, 0.0, 3.6, 'Shop glass')
        mb.quad_wall(a, b, 3.6, 4.3, 'White band')
        mb.quad_wall(tuple(a2 + n * 0.15), tuple(b2 + n * 0.15), 4.3, 7.4, 'Terracotta')
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
    mb = MeshBuilder()
    # --- pool deck in front of the hotel -------------------------------------
    zE = DECK_E
    pool = Point(0, 0).buffer(1.0)
    pool_poly = Polygon([(-7.0, -3.4), (7.0, -3.4), (7.0, 3.4), (-7.0, 3.4)]).buffer(1.0, join_style='round').buffer(-1.0)
    from shapely import affinity
    pool_poly = affinity.translate(affinity.rotate(pool_poly, 28, origin=(0, 0)), 45.0, 247.0)
    deck = pool_poly.buffer(5.0, join_style='mitre')
    mb.prism(deck.intersection(poly.buffer(-1.0)), zE, zE + 0.08, 'Deck paving', 'Deck paving')
    mb.prism(pool_poly.buffer(0.4).difference(pool_poly), zE, zE + 0.3, 'White band', 'White band')
    mb.polygon_face(pool_poly, zE + 0.15, 'Pool water')
    for k in range(5):
        x, y = 35.0 + k * 2.4, 238.5 - k * 0.9
        mb.box(x, y, zE + 0.08, 0.7, 1.9, 0.35, 'Wood', rot=math.radians(28))
    for (x, y) in [(36.0, 254.0), (54.0, 240.0), (30.0, 245.0)]:
        mb.box(x, y, zE + 0.08, 0.1, 0.1, 2.4, 'Metal')
        mb.prism(Point(x, y).buffer(1.6, quad_segs=2), zE + 2.4, zE + 2.6, 'Wood', 'Wood', 'Wood')
    # garden strip with hedges and gazebos between the hotel and block B
    for (x, y) in [(28.0, 268.0), (14.0, 280.0)]:
        gazebo(mb, x, y, zE)
    hedge = LineString([(56.0, 260.0), (40.0, 272.0), (24.0, 280.0), (8.0, 286.0)])
    mb.prism(hedge.buffer(0.6), zE, zE + 1.0, 'Shrub', 'Shrub')
    for (x, y, h) in [(50.0, 264.0, 6.0), (34.0, 276.0, 7.0), (20.0, 285.0, 6.0), (60.0, 250.0, 5.0), (40.0, 258.0, 5.5),
                      (24.0, 262.0, 6.5), (58.0, 232.0, 5.0)]:
        if poly.buffer(-1.5).contains(Point(x, y)):
            tree(mb, x, y, zE, h, 2.0, light=(x > 40))
    # --- playground deck between blocks B and V: grey paving, red play kit, lattice dome, trees
    zW = DECK_W
    gazebo(mb, -3.0, 254.0, zW, r=2.3, h=2.6)
    for (x, y) in [(-12.0, 266.0), (-2.0, 270.0), (-14.0, 256.0)]:
        mb.box(x, y, zW, 0.9, 0.9, 1.8, 'Play orange')
        mb.box(x, y, zW + 1.8, 1.5, 1.5, 0.15, 'Play orange')
        mb.box(x + 1.0, y, zW, 0.12, 0.12, 2.2, 'Metal')
    for (x, y, h) in [(-16.0, 272.0, 5.0), (6.0, 272.0, 5.5), (-9.0, 250.0, 4.5), (8.0, 262.0, 5.0), (-22.0, 262.0, 5.0),
                      (-6.0, 262.0, 4.0)]:
        if ww.buffer(-1.0).contains(Point(x, y)):
            tree(mb, x, y, zW, h, 1.7)
    make_object('Podium decks', mb.to_mesh('Podium decks', mats), col)
