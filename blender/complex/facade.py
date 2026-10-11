"""Shop front of the curved podium, detailed after the pool-deck render (render 2).

Drop-in for podium.shop_front(mb, a, b, signs): one call per segment a->b of the podium's outer
edge (outward normal to the right of a->b). The section, with d = metres out from the podium
outline and z = height above the street:

    0.0 - 5.3    shops: light glazing set back 0.35 m between light stone piers (every ~12.5 m,
                 0.85 m deep), dark frames (sill, mullions every ~1.75 m, transom), a shop sign per bay
    5.3 - 6.5    thick white slab band with rounded nose, 0.8 m proud of the outline
    6.5 - 10.0   glazed gallery: dark mullions every ~1.9 m and a low transom, stone panels over the piers
    10.0 - 10.97 white rounded band, 0.8 m proud
    10.97 - 14.25 perforated copper screen: 1.5 m panels folded as a sawtooth (0.04 - 0.5 m proud), the
                 bottom edge cut up towards the folds so the ridges hang down as tips over the white band,
                 dark joints in the folds, white brand logos standing in front of the ridges
    (white rounded parapet and glass rail on top of the +15.0 deck: deck/edge.py)

Everything that repeats along the front (piers, shop bays, mullions, copper panels, logos) is laid
out by arc length along the whole outer line from the hotel end, not per segment, so the rhythm is
the same however finely podium.OUTER is sampled (a smooth, densely sampled curve works as well as
the 14-point polyline). Joints between segments are mitred with the neighbouring segments of
podium.OUTER, so the bands run round the curve without gaps; the bands are capped where the shop
front meets the land side. The logos and shop names are baked as low-resolution text meshes into
the podium mesh (the default text resolution would cost 1-4k triangles per logo), so `signs` is
left for other callers.
"""
import math

import numpy as np

GF_TOP = 6.0       # podium levels (as in podium.py)
L2_TOP = 10.5
DECK_E = 15.0

GF_GLASS = -0.35   # shop glazing line (behind the piers)
GF_Z1 = 5.3        # underside of the white slab band
L2_Z0, L2_Z1 = 6.5, 10.0
CU_Z0, CU_Z1 = 10.97, 14.25
CU_VALLEY, CU_RIDGE = 0.04, 0.5
CU_TIP = 0.28      # the copper's bottom edge rises this much from the ridges to the valleys
CU_PANEL = 1.5
PIER_STEP = 12.5
PIER_W, PIER_D0, PIER_D1 = 1.25, GF_GLASS, 0.5
PIER_MAT = 'Kerb'  # light warm grey stone, as the piers on the render
GF_MULLION = 1.75  # shop glazing module
L2_MULLION = 1.9   # gallery glazing module

# rounded band sections (d, z), counter-clockwise: soffit outwards, up the nose, back over the top
GF_BAND = [(GF_GLASS, GF_Z1), (0.50, GF_Z1), (0.65, 5.33), (0.74, 5.43), (0.79, 5.6), (0.79, 6.2), (0.74, 6.37),
           (0.65, 6.47), (0.50, 6.5), (-0.05, 6.5)]
L2_BAND = [(-0.05, L2_Z1), (0.50, L2_Z1), (0.67, 10.04), (0.77, 10.16), (0.80, 10.34), (0.80, 10.63), (0.77, 10.81),
           (0.67, 10.93), (0.50, CU_Z0), (0.0, CU_Z0)]

# copper band logos (from the hotel end, as on the render) and shop names in the ground-floor bays
LOGOS = ['MEXX', 'MOSCHINO', 'asics', 'adidas', 'MEXX', 'ChristianDior', 'asics', 'LC WAIKIKI', 'Columbia',
         'adidas', "Levi's", 'MOSCHINO', 'asics', 'ecco', 'MEXX', 'Bershka']
LOGO_STEP = 13.5
# logo proportions on the render: (width in metres, letter-height stretch) for Blender's font at size 1
LOGO_STYLE = {'MEXX': (3.0, 1.55), 'MOSCHINO': (3.8, 1.3), 'asics': (2.5, 1.7), 'adidas': (2.6, 1.35),
              'ChristianDior': (5.4, 1.45), 'LC WAIKIKI': (4.6, 1.4), 'Columbia': (3.6, 1.35), "Levi's": (2.6, 1.4),
              'ecco': (2.2, 1.9), 'Bershka': (3.4, 1.4)}
LOGO_MAT = {'LC WAIKIKI': 'Sign blue'}        # LC Waikiki is the one blue logo on the band
LOGO_FIRST = 9.0
SHOPS = [('LC WAIKIKI', 'Play blue'), ('Columbia', None), ('KFC', 'Car red'), ('Bershka', None), ('ecco', 'Stained blue'),
         ("Levi's", 'Car red'), ('MANGO', None), ('DeFacto', 'Stained blue'), ('Koton', None), ('Mavi', 'Play blue')]
EPS = 1e-6


# ----------------------------------------------------------------------------------------------
# the outer line and the layout along it (arc length from the hotel end)
# ----------------------------------------------------------------------------------------------

def _outer():
    from .podium import OUTER
    return OUTER


_CACHE = {}


def layout():
    """Positions (arc length from the hotel end) of everything that repeats along the shop front,
    cached per outline."""
    key = tuple((float(x), float(y)) for x, y in _outer())
    if key in _CACHE:
        return _CACHE[key]
    from shapely.geometry import LineString
    line = LineString(key)
    Lt = line.length
    n = max(1, int(round(Lt / PIER_STEP)))
    piers = [Lt * i / n for i in range(n + 1)]
    gf, l2 = [], []
    for p0, p1 in zip(piers[:-1], piers[1:]):
        span = p1 - p0 - PIER_W
        m = max(1, int(round(span / GF_MULLION)))
        gf += [(p0 + PIER_W / 2 + span * j / m, 0.16 if j in (0, m) else 0.08) for j in range(m + 1)]
        m2 = max(1, int(round(span / L2_MULLION)))
        l2 += [p0 + PIER_W / 2 + span * j / m2 for j in range(1, m2)]
    nc = max(1, int(round(Lt / CU_PANEL)))
    joints = [Lt * j / nc for j in range(nc + 1)]
    logos = []
    k = 0
    while LOGO_FIRST + LOGO_STEP * k < Lt - 4.0:
        s = LOGO_FIRST + LOGO_STEP * k
        j = min(range(1, nc), key=lambda i: abs(joints[i] - s)) if nc > 1 else 0
        logos.append((joints[j], LOGOS[k % len(LOGOS)]))      # centred on a ridge
        k += 1
    O = np.array(key)
    _CACHE[key] = dict(line=line, L=Lt, O=O, piers=piers, bays=list(zip(piers[:-1], piers[1:])), gf=gf, l2=l2,
                       joints=joints, logos=logos)
    return _CACHE[key]


def arc_from_hotel(p):
    from shapely.geometry import Point
    lay = layout()
    return lay['L'] - lay['line'].project(Point(float(p[0]), float(p[1])))


def _vertex(p):
    """(offset direction, is end of the shop front) at an outline vertex p."""
    O = layout()['O']
    dist = np.linalg.norm(O - p, axis=1)
    i = int(np.argmin(dist))
    if dist[i] > 0.05:
        return None, False
    if i == 0 or i == len(O) - 1:
        return None, True

    def out_normal(u, v):            # left of the OUTER direction is outside the podium
        t = (v - u) / np.linalg.norm(v - u)
        return np.array([-t[1], t[0]])
    n1, n2 = out_normal(O[i - 1], O[i]), out_normal(O[i], O[i + 1])
    m = n1 + n2
    m /= np.linalg.norm(m)
    return m / max(float(m @ n1), 0.5), False


class Seg:
    def __init__(self, a, b):
        self.a, self.b = np.array(a, float), np.array(b, float)
        self.L = float(np.linalg.norm(self.b - self.a))
        self.t = (self.b - self.a) / self.L
        self.n = np.array([self.t[1], -self.t[0]])
        self.rot = math.atan2(self.t[1], self.t[0])
        ma, self.a_end = _vertex(self.a)
        mb, self.b_end = _vertex(self.b)
        self.ma = self.n if ma is None else ma
        self.mb = self.n if mb is None else mb
        # arc length from the hotel end at both ends; u = sgn * (s - s_a)
        self.sa, self.sb = arc_from_hotel(self.a), arc_from_hotel(self.b)
        self.sgn = 1.0 if self.sb >= self.sa else -1.0
        self.lo, self.hi = min(self.sa, self.sb), max(self.sa, self.sb)
        self.last = abs(self.hi - layout()['L']) < 1e-3

    def p(self, u, d):
        """2D point u metres along the segment, d metres out (exact mitres at both ends)."""
        f = u / self.L
        return (self.a + self.ma * d) * (1 - f) + (self.b + self.mb * d) * f

    def p3(self, u, d, z):
        q = self.p(u, d)
        return (float(q[0]), float(q[1]), float(z))

    def q(self, u, d):
        """Point on the segment's own plane (no mitres; u may run past the ends)."""
        return self.a + self.t * u + self.n * d

    def u(self, s):
        return self.sgn * (s - self.sa)

    def owns(self, s):
        """Is arc position s on this segment (half-open, so shared vertices are counted once)?"""
        return self.lo - EPS <= s < self.hi - EPS or (self.last and abs(s - self.hi) <= 1e-3)

    def along(self):
        """Unit vector in the direction of growing arc length."""
        return self.t * self.sgn


# ----------------------------------------------------------------------------------------------
# primitives
# ----------------------------------------------------------------------------------------------

def _newell(pts):
    n = np.zeros(3)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
    return n


def _face_toward(mb, pts, want, mat, uv=None):
    if _newell(pts) @ np.array(want, float) < 0:
        pts = pts[::-1]
        uv = uv[::-1] if uv else None
    mb.face(pts, mat, uv=uv)


def sweep(mb, s, prof, mat):
    """Band of section `prof` along the segment; capped where the shop front ends."""
    for (d0, z0), (d1, z1) in zip(prof[:-1], prof[1:]):
        mb.face([s.p3(0, d0, z0), s.p3(s.L, d0, z0), s.p3(s.L, d1, z1), s.p3(0, d1, z1)], mat)
    if s.a_end:
        _face_toward(mb, [s.p3(0, d, z) for d, z in prof], (-s.t[0], -s.t[1], 0), mat)
    if s.b_end:
        _face_toward(mb, [s.p3(s.L, d, z) for d, z in prof], (s.t[0], s.t[1], 0), mat)


def rail(mb, s, d, z0, z1, depth, mat):
    """Horizontal frame member along the whole segment."""
    A, B = s.p(0, d), s.p(s.L, d)
    mb.tube([tuple(A), tuple(B)], [z0, z0], [z1, z1], depth, mat)


def post(mb, s, u, d, z0, z1, w, depth, mat):
    q = s.p(u, d)
    mb.box(float(q[0]), float(q[1]), z0, w, depth, z1 - z0, mat, rot=s.rot)


def wall(mb, s, d, z0, z1, mat):
    A, B = s.p(0, d), s.p(s.L, d)
    mb.face([(A[0], A[1], z0), (B[0], B[1], z0), (B[0], B[1], z1), (A[0], A[1], z1)], mat,
            uv=[(0, z0), (s.L, z0), (s.L, z1), (0, z1)])


# ----------------------------------------------------------------------------------------------
# text (logos, shop names) baked into the mesh
# ----------------------------------------------------------------------------------------------

_TEXT = {}


def _text_geo(text, size):
    """Vertices / polygons of a text mesh in the text's own plane (x along, y up, z out), cached."""
    key = (text, size)
    if key not in _TEXT:
        import bpy
        cu = bpy.data.curves.new('facade_sign', 'FONT')
        cu.body = text
        cu.size = size
        cu.align_x = 'CENTER'
        cu.align_y = 'CENTER'
        cu.extrude = 0.0          # flat letters: a fill only (~5x fewer triangles)
        cu.resolution_u = 3
        ob = bpy.data.objects.new('facade_sign', cu)
        bpy.context.scene.collection.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        verts = [tuple(v.co) for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        bpy.data.objects.remove(ob)
        bpy.data.curves.remove(cu)
        bpy.data.meshes.remove(me)
        xs = [v[0] for v in verts] or [0.0]
        _TEXT[key] = (verts, polys, max(xs) - min(xs))
    return _TEXT[key]


def text_width(text, size):
    try:
        return _text_geo(text, size)[2]
    except Exception:
        return 0.55 * size * len(text)


def put_text(mb, s, u, d, z, text, size, mat='Sign', bold=0.0, sx=1.0, sy=1.0):
    """Text standing on the segment's plane, centred at (u, d, z), facing out, stretched by sx / sy.
    bold > 0 adds two copies shifted sideways by that much (heavier strokes, as the logos)."""
    verts, polys, _ = _text_geo(text, size)
    t, n = s.t, s.n
    for du, dd in ([(0.0, 0.0)] + ([(-bold, 0.004), (bold, 0.004)] if bold > 0 else [])):
        q = s.q(u + du, d + dd)
        W = [(float(q[0] + t[0] * x * sx + n[0] * zz), float(q[1] + t[1] * x * sx + n[1] * zz), float(z + y * sy))
             for x, y, zz in verts]
        for poly in polys:
            mb.face([W[i] for i in poly], mat)


def _q3(s, u, d, z):
    q = s.q(u, d)
    return (float(q[0]), float(q[1]), float(z))


def adidas_mark(mb, s, u, d, z, h, mat='Sign'):
    """The three slanted bars above the adidas word."""
    for k, hh in enumerate((0.45, 0.72, 1.0)):
        u0 = u + (k - 1) * h * 0.42
        top, bot = z + h * hh * 0.9, z
        lean = h * 0.32 * hh
        pts = [_q3(s, u0 - h * 0.15, d, bot), _q3(s, u0 + h * 0.15, d, bot), _q3(s, u0 + h * 0.15 + lean, d, top),
               _q3(s, u0 - h * 0.15 + lean, d, top)]
        mb.face(pts, mat)


def asics_mark(mb, s, u, d, z, h, mat='Sign'):
    """The asics stripes: three swept bars rising to the right, left of the word."""
    for k in range(3):
        y0 = z - h * 0.42 + k * h * 0.3
        pts = [_q3(s, u - h * 0.55, d, y0), _q3(s, u + h * 0.45, d, y0 + h * 0.32),
               _q3(s, u + h * 0.45, d, y0 + h * 0.46), _q3(s, u - h * 0.55, d, y0 + h * 0.13)]
        mb.face(pts, mat)


# ----------------------------------------------------------------------------------------------
# the shop front
# ----------------------------------------------------------------------------------------------

FRAME = 'Shop frame'


def _mat(name, fallback):
    try:
        import bpy
        return name if bpy.data.materials.get(name) is not None else fallback
    except Exception:
        return fallback


def ground_floor(mb, s, lay):
    wall(mb, s, GF_GLASS, 0.0, GF_Z1, _mat('Shop window', 'Shop glass'))
    rail(mb, s, GF_GLASS + 0.05, 0.0, 0.32, 0.14, FRAME)         # sill
    rail(mb, s, GF_GLASS + 0.05, 4.5, 4.6, 0.12, FRAME)          # transom (shop signs below it)
    rail(mb, s, GF_GLASS + 0.05, GF_Z1 - 0.1, GF_Z1, 0.12, FRAME)
    for sp in lay['piers']:
        if s.owns(sp):
            u = s.u(sp)
            post(mb, s, u, (PIER_D0 + PIER_D1) / 2, 0.0, GF_Z1, PIER_W, PIER_D1 - PIER_D0, PIER_MAT)
            post(mb, s, u, PIER_D1 + 0.02, 0.0, 0.25, PIER_W + 0.1, 0.06, FRAME)   # dark plinth
    for sm, w in lay['gf']:
        if s.owns(sm):
            post(mb, s, s.u(sm), GF_GLASS + 0.05, 0.3, GF_Z1, w, 0.12, FRAME)  # heavier frame at the piers
    for k, (p0, p1) in enumerate(lay['bays']):
        mid = (p0 + p1) / 2
        if s.owns(mid):
            shop_sign(mb, s, s.u(mid), p1 - p0 - PIER_W, k)


def shop_sign(mb, s, u, span, k):
    text, box_mat = SHOPS[k % len(SHOPS)]
    size = 0.95
    w = min(text_width(text, size), span - 1.0)
    if w <= 0.5:
        return
    z, d = 4.05, GF_GLASS + 0.14
    if box_mat:
        uu = u - s.sgn * span * 0.18          # towards the hotel end of the bay
        q = s.q(uu, d)
        mb.box(float(q[0]), float(q[1]), z - 0.36, w + 0.7, 0.12, 0.72, box_mat, rot=s.rot)
        put_text(mb, s, uu, d + 0.07, z, text, size)
    else:
        put_text(mb, s, u, d, z, text, size)


def gallery(mb, s, lay):
    wall(mb, s, 0.0, L2_Z0, L2_Z1, _mat('Gallery glass', 'Shop glass'))
    rail(mb, s, 0.05, L2_Z0, L2_Z0 + 0.12, 0.1, FRAME)
    rail(mb, s, 0.05, 7.12, 7.2, 0.08, FRAME)
    rail(mb, s, 0.05, L2_Z1 - 0.1, L2_Z1, 0.1, FRAME)
    for sm in lay['l2']:
        if s.owns(sm):
            post(mb, s, s.u(sm), 0.05, L2_Z0, L2_Z1, 0.07, 0.1, FRAME)
    for sp in lay['piers']:   # stone panels over the piers
        if s.owns(sp):
            post(mb, s, s.u(sp), 0.12, L2_Z0, L2_Z1, PIER_W, 0.24, PIER_MAT)


def _cu_d(f):
    """Copper sheet offset at fraction f across a panel (valley at the start, ridge at the end)."""
    return CU_VALLEY + (CU_RIDGE - CU_VALLEY) * f


def _cu_bottom(d):
    """Bottom edge of the copper: on the band at the ridge, cut up towards the valley."""
    return CU_Z0 + CU_TIP * (CU_RIDGE - d) / (CU_RIDGE - CU_VALLEY)


def copper(mb, s, lay):
    """Perforated copper panels folded as a sawtooth: each 1.5 m panel turns out from the valley to
    the ridge and a short return closes it with a dark joint in the valley, so the band reads as a
    row of lit panels with dark folds. The bottom edge rises from each ridge to the next valley,
    so the folds hang down as tips over the white band, as on the render. UVs are metres (u centred
    on the panel, v = height) for the perforation / joint pattern of the material."""
    wall(mb, s, 0.0, CU_Z0, DECK_E - 0.6, 'Terracotta dark')
    J = lay['joints']
    along = s.along()
    for c0, c1 in zip(J[:-1], J[1:]):
        a0, a1 = max(c0, s.lo), min(c1, s.hi)
        if a1 - a0 > 1e-4:
            f0, f1 = (a0 - c0) / (c1 - c0), (a1 - c0) / (c1 - c0)
            pw = math.hypot(c1 - c0, CU_RIDGE - CU_VALLEY)
            ends = sorted([(s.u(a0), _cu_d(f0), (f0 - 0.5) * pw), (s.u(a1), _cu_d(f1), (f1 - 0.5) * pw)])
            (uA, dA, tA), (uB, dB, tB) = ends
            A, B = s.p(uA, dA), s.p(uB, dB)
            zA, zB = _cu_bottom(dA), _cu_bottom(dB)
            mb.face([(A[0], A[1], zA), (B[0], B[1], zB), (B[0], B[1], CU_Z1), (A[0], A[1], CU_Z1)],
                    'Copper screen', uv=[(tA, zA), (tB, zB), (tB, CU_Z1), (tA, CU_Z1)])
        if s.owns(c1):
            u1 = s.u(c1)
            P1, P2 = s.p(u1, CU_RIDGE), s.p(u1, CU_VALLEY)
            z1, z2 = _cu_bottom(CU_RIDGE), _cu_bottom(CU_VALLEY)
            rw = CU_RIDGE - CU_VALLEY
            _face_toward(mb, [(P1[0], P1[1], z1), (P2[0], P2[1], z2), (P2[0], P2[1], CU_Z1), (P1[0], P1[1], CU_Z1)],
                         (along[0], along[1], 0.0), 'Copper screen',
                         uv=[(5.0, z1), (5.0 + rw, z2), (5.0 + rw, CU_Z1), (5.0, CU_Z1)])
            post(mb, s, u1, CU_VALLEY + 0.03, z2, CU_Z1, 0.08, 0.06, 'Terracotta dark')   # joint in the fold
    # top edge trim tucked under the parapet
    rail(mb, s, 0.25, CU_Z1 - 0.06, CU_Z1 + 0.02, 0.5, 'Terracotta dark')


def logos(mb, s, lay):
    for sk, text in lay['logos']:
        if not s.owns(sk):
            continue
        tw, sy = LOGO_STYLE.get(text, (min(4.0, text_width(text, 1.0) * 1.1), 1.4))
        sx = tw / max(text_width(text, 1.0), 0.1)
        u = s.u(sk)
        z = (CU_Z0 + CU_Z1) / 2 - 0.05
        d = CU_RIDGE + 0.06
        mat = _mat(LOGO_MAT.get(text, 'Sign'), 'Sign')
        if text == 'adidas':
            put_text(mb, s, u, d, z - 0.62, text, 1.0, mat=mat, bold=0.025, sx=sx, sy=sy)
            adidas_mark(mb, s, u, d, z - 0.1, 1.25, mat=mat)
        elif text == 'asics':
            put_text(mb, s, u + 0.55, d, z, text, 1.0, mat=mat, bold=0.03, sx=sx, sy=sy)
            asics_mark(mb, s, u - tw / 2 - 0.1, d, z, 0.9, mat=mat)
        else:
            put_text(mb, s, u, d, z, text, 1.0, mat=mat, bold=0.03, sx=sx, sy=sy)


def shop_front(mb, a, b, signs):
    """One segment a->b of the outer edge (outward normal to the right). Built into a scratch mesh
    first: if anything fails the plain shop front of podium.py is used for this segment."""
    global FRAME
    from .geom import MeshBuilder
    try:
        FRAME = _mat('Shop frame', 'Car dark')
        if float(np.linalg.norm(np.array(b, float) - np.array(a, float))) < 0.05:
            return
        lay = layout()
        s = Seg(a, b)
        part = MeshBuilder()
        ground_floor(part, s, lay)
        sweep(part, s, GF_BAND, 'White band')
        gallery(part, s, lay)
        sweep(part, s, L2_BAND, 'White band')
        copper(part, s, lay)
        logos(part, s, lay)
    except Exception:
        import traceback
        print('[facade] shop_front: failed, using the plain shop front for this segment')
        traceback.print_exc()
        from . import podium
        podium.shop_front(mb, a, b, signs)
        return
    mb.merge(part)
