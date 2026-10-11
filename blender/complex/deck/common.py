"""Shared props for the decks and the promenade: one look for trees, hedges, planters, benches
and lamps across all parts. Everything is in site metres; z is the surface the prop stands on.
"""
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon

PAVE_T = 0.06  # zone paving sits this much above the podium slab


def rod(mb, p0, p1, r, mat, sides=6):
    """Prism of radius r between two 3D points (any direction): poles, arms, lattice struts."""
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
    ring = [(math.cos(2 * math.pi * k / sides), math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    b0 = [tuple(p0 + r * (c * u + s * v)) for c, s in ring]
    b1 = [tuple(p1 + r * (c * u + s * v)) for c, s in ring]
    for k in range(sides):
        j = (k + 1) % sides
        mb.face([b0[k], b0[j], b1[j], b1[k]], mat)
    mb.face(b0[::-1], mat)
    mb.face(b1, mat)


def pave(mb, poly, z, mat, t=PAVE_T):
    """Paving layer over a zone (a thin slab, so its edge reads against neighbours)."""
    mb.prism(poly, z, z + t, mat, mat)


def tree(mb, x, y, z, h=5.0, r=1.8, leaf='Leaves', rnd=None, kind='round'):
    """Deck / street tree: trunk with a few branches and a crown of lumpy clumps."""
    import random
    rnd = rnd or random.Random(int(x * 13 + y * 7))
    rod(mb, (x, y, z), (x, y, z + h * 0.55), 0.13, 'Trunk')
    for k in range(3):
        a = k * 2.1 + rnd.uniform(-0.3, 0.3)
        rod(mb, (x, y, z + h * 0.45), (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z + h * 0.68), 0.06, 'Trunk')
    if kind == 'cone':
        for i, (zz, rr) in enumerate([(0.35, 1.0), (0.55, 0.78), (0.75, 0.52)]):
            mb.blob(x, y, z + h * zz + r * 0.3, r * rr * 0.75, r * rr * 0.75, r * rr * 0.9, leaf, subdiv=1, jitter=0.1, rnd=rnd)
        return
    for dx, dy, dz, rr in [(0, 0, 0.72, 1.0), (0.42, 0.2, 0.66, 0.72), (-0.38, -0.26, 0.68, 0.7), (0.1, -0.12, 0.92, 0.62),
                           (-0.25, 0.38, 0.8, 0.6)]:
        mb.blob(x + dx * r, y + dy * r, z + h * dz, r * rr, r * rr, r * rr * 0.85, leaf, subdiv=2, jitter=0.14, rnd=rnd)


def hedge(mb, shape, z, h=0.9, w=0.7):
    """Clipped hedge along a line (or filling a polygon), slightly rounded on top."""
    poly = shape.buffer(w / 2, cap_style='round') if shape.geom_type in ('LineString', 'MultiLineString') else shape
    for g in getattr(poly, 'geoms', [poly]):
        if g.area < 0.05:
            continue
        mb.prism(g, z, z + h * 0.85, 'Shrub', 'Shrub')
        mb.prism(g.buffer(-min(0.12, w / 4)), z + h * 0.85, z + h, 'Shrub', 'Shrub')


def lawn(mb, poly, z, kerb=0.12):
    """Lawn bed with a light kerb."""
    for g in getattr(poly, 'geoms', [poly]):
        if g.area < 0.2:
            continue
        mb.prism(g, z, z + kerb, 'Planter', None)
        mb.polygon_face(g.buffer(-0.1), z + kerb - 0.02, 'Lawn')


def planter(mb, poly, z, h=0.45):
    """Raised planter: light concrete walls, lawn inside."""
    for g in getattr(poly, 'geoms', [poly]):
        if g.area < 0.2:
            continue
        mb.prism(g.difference(g.buffer(-0.15)), z, z + h, 'Planter', 'Planter')
        mb.polygon_face(g.buffer(-0.15), z + h - 0.06, 'Lawn')


def round_planter(mb, x, y, z, r=1.4, tree_h=4.5, rnd=None):
    planter(mb, Point(x, y).buffer(r, quad_segs=8), z, 0.4)
    tree(mb, x, y, z + 0.34, tree_h, r * 1.25, 'Leaves light', rnd)


def bench(mb, x, y, z, rot=0.0, length=1.8, back=True):
    """Timber bench on two concrete feet; rot = direction of the seat's long side (radians)."""
    c, s = math.cos(rot), math.sin(rot)
    for k in (-0.4, 0.4):
        mb.box(x + c * k * length, y + s * k * length, z, 0.12, 0.5, 0.42, 'Planter', rot=rot)
    mb.box(x, y, z + 0.42, length, 0.5, 0.06, 'Wood', rot=rot)
    if back:
        mb.box(x - s * 0.24, y + c * 0.24, z + 0.48, length, 0.06, 0.4, 'Wood', rot=rot)


def lamp(mb, x, y, z, rot=0.0, h=4.2):
    """Swan-neck lamp as on the render: slim white pole, arm curving over, flat oval head."""
    rod(mb, (x, y, z), (x, y, z + h), 0.06, 'Lamp white', sides=8)
    c, s = math.cos(rot), math.sin(rot)
    pts = []
    for k in range(7):
        a = math.pi / 2 * k / 6
        pts.append((x + c * 0.55 * (1 - math.cos(a)), y + s * 0.55 * (1 - math.cos(a)), z + h + 0.35 * math.sin(a)))
    for p, q in zip(pts[:-1], pts[1:]):
        rod(mb, p, q, 0.045, 'Lamp white', sides=6)
    hx, hy, hz = pts[-1]
    hx, hy = hx + c * 0.25, hy + s * 0.25
    head = Polygon([(hx + c * u * 0.42 - s * v * 0.26, hy + s * u * 0.42 + c * v * 0.26)
                    for u, v in [(math.cos(t), math.sin(t)) for t in np.linspace(0, 2 * math.pi, 16)[:-1]]])
    mb.prism(head, hz - 0.08, hz + 0.02, 'Lamp white', 'Lamp white', 'Lamp glow')


def stool(mb, x, y, z, r=0.25, h=0.42, mat='Wood'):
    mb.prism(Point(x, y).buffer(r, quad_segs=4), z, z + h, mat, mat)
