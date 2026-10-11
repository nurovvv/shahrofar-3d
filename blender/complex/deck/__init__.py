"""Roof decks on the podium, detailed after the marketing render of the pool deck (render 2).

The east deck (+15.0, between the hotel and block B) is split into zones that each part of the
deck is built in; the west deck (+20.5, between blocks B and V) reuses the playground.

    pool    tan stone, pool with mosaic surround, sail umbrellas and loungers   (deck/pool.py)
    strip   diagonal raised planter with hedge, trees and a timber bench edge   (deck/edge.py)
    play    grey cobble, lattice pergolas, play frames, fitness, round planters (deck/play.py)
    edge    white rounded parapet and glass rail, lawn and hedge border, lamps   (deck/edge.py)

Each module has build(mb, ctx); a module that is missing or fails is skipped, so the scene still
builds while one part is being worked on.
"""
import importlib
import random
import traceback

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from ..geom import biggest


def tower_footprints():
    """Site outlines of blocks V and B (from the plans) and the hotel A, with their balconies."""
    from .. import drawn, towers
    plans = drawn.load_plans()
    out = {}
    for key in ('V', 'B'):
        info, bp = drawn.TOWERS[key], plans[key]
        p = Polygon(bp['slab'])
        c = p.centroid
        p = affinity.translate(p, -c.x, -c.y)
        p = affinity.rotate(p, drawn.SITE_ROT + bp['sheet_rot'], origin=(0, 0))
        out[key] = affinity.translate(p, *info['centre'])
    H = towers.TOWER_A
    hc = towers.hotel_core(H).buffer(H['balcony'] + 0.3)
    out['A'] = affinity.translate(affinity.rotate(hc, H['rot'], origin=(0, 0)), *H['origin'])
    return out


def make_context(podium_poly, outer_line, west_wing, z_east, z_west, split_x):
    """Zones of the decks, all in site metres (x east, y north)."""
    T = tower_footprints()
    towers_u = unary_union(list(T.values())).buffer(1.0)
    east = biggest(podium_poly.intersection(box(split_x - 0.5, 150, 200, 400)).difference(towers_u))
    edge_band = east.intersection(outer_line.buffer(2.6))
    inner = east.difference(edge_band)
    # the planter runs from the outer edge (east) diagonally back to the gap between the towers
    a, b = (68.0, 247.0), (30.5, 225.5)
    d = ((b[0] - a[0]), (b[1] - a[1]))
    long_line = LineString([(a[0] - d[0], a[1] - d[1]), (b[0] + d[0], b[1] + d[1])])
    strip = inner.intersection(long_line.buffer(1.4))
    strip_line = long_line.intersection(inner.buffer(0.5))
    if strip_line.geom_type != 'LineString':
        strip_line = max(strip_line.geoms, key=lambda g: g.length)
    rest = inner.difference(long_line.buffer(1.4))
    side = lambda g: (g.centroid.x - a[0]) * d[1] - (g.centroid.y - a[1]) * d[0]  # > 0: south-east of the line
    parts = [g for g in getattr(rest, 'geoms', [rest]) if g.area > 20]
    pool = max((g for g in parts if side(g) < 0), key=lambda g: g.area)
    play = max((g for g in parts if side(g) > 0), key=lambda g: g.area)
    west = biggest(west_wing.difference(towers_u))
    west_edge = west.intersection(outer_line.buffer(2.6))
    return dict(
        podium=podium_poly,        # whole podium outline (deck level +15.0 everywhere but the west wing)
        west_wing=west_wing,       # the raised west wing (+20.5)
        z=z_east,
        deck=east,                 # whole free east deck (paving goes everywhere the zones don't)
        outer_line=outer_line,     # the outer curve of the podium (shop front side), whole length
        edge_band=edge_band,       # 2.6 m band inside the outer edge: parapet, lawn, hedge
        strip_line=strip_line,     # centre line of the diagonal planter
        strip=strip,               # planter band, 2.8 m wide
        pool=pool,                 # south part, by the hotel
        play=play,                 # north part, by block B
        towers=T,                  # 'A', 'B', 'V' outlines (with balconies)
        west=dict(z=z_west, deck=west, play=west.difference(west_edge), edge_band=west_edge),
        rnd=random.Random(20261011),
    )


MODULES = ('pool', 'play', 'edge')


def build_all(mb, ctx):
    """Build every available part; returns the names of the parts that were built."""
    built = set()
    for name in MODULES:
        try:
            mod = importlib.import_module(f'{__name__}.{name}')
        except Exception:
            print(f'[deck] {name}: not available')
            traceback.print_exc()
            continue
        try:
            mod.build(mb, ctx)
            built.add(name)
        except Exception:
            print(f'[deck] {name}: failed')
            traceback.print_exc()
    return built


# Free spots on the decks where people can stand (filled by find_people_spots, used by site.py).
PEOPLE_SPOTS = []


def find_people_spots(mb, ctx, cell=0.6):
    """Cells of the deck zones not taken by anything built there (props, planters, the pool recess)."""
    import numpy as np
    PEOPLE_SPOTS.clear()
    for z, zones in ((ctx['z'], [ctx['pool'], ctx['play'], ctx['edge_band']]), (ctx['west']['z'], [ctx['west']['play']])):
        area = unary_union(zones)
        x0, y0, x1, y1 = area.bounds
        nx, ny = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
        taken = np.zeros((ny, nx), bool)
        V = np.array(mb.verts)
        for f in mb.faces:
            P = V[f]
            zs = P[:, 2]
            if not ((zs.max() > z + 0.12 and zs.min() < z + 2.5) or zs.min() < z - 0.05):
                continue
            if zs.max() < z - 3 or zs.min() > z + 3:
                continue  # another level
            i0, i1 = int((P[:, 1].min() - y0) / cell), int((P[:, 1].max() - y0) / cell)
            j0, j1 = int((P[:, 0].min() - x0) / cell), int((P[:, 0].max() - x0) / cell)
            taken[max(0, i0 - 1):min(ny, i1 + 2), max(0, j0 - 1):min(nx, j1 + 2)] = True
        for i in range(ny):
            for j in range(nx):
                x, y = x0 + (j + 0.5) * cell, y0 + (i + 0.5) * cell
                if not taken[i, j] and area.buffer(-0.8).contains(Point(x, y)):
                    PEOPLE_SPOTS.append((round(x, 2), round(y, 2), z + 0.06))
    print(f'[deck] {len(PEOPLE_SPOTS)} free spots for people')
