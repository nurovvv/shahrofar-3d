"""Materials, matched to the colours of the Shahrofar marketing renders.

Names are kept stable on purpose: the web viewer looks materials up by name.
"""
import bpy


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# name: (hex colour, roughness, metallic, extra)
SPECS = {
    'Terracotta': ('#b88472', 0.85, 0.0, {}),
    'Terracotta dark': ('#6e3e30', 0.8, 0.0, {}),
    'White band': ('#efebe5', 0.45, 0.0, {}),
    'Roof': ('#d36a68', 0.9, 0.0, {}),
    'Plant room': ('#5a3a2f', 0.85, 0.0, {}),
    'Solar panel': ('#56627e', 0.3, 0.4, {}),
    'Window glass': ('#35524c', 0.08, 0.0, {'specular': 0.7}),
    'Curtain glass': ('#2f8070', 0.05, 0.0, {'specular': 0.6}),
    'Shop glass': ('#3a5559', 0.05, 0.0, {'specular': 0.8}),
    'Frame': ('#d9d2c6', 0.45, 0.0, {}),
    'Railing glass': ('#c9dbe2', 0.05, 0.0, {'alpha': 0.14}),
    'Copper screen': ('#9c5a3c', 0.45, 0.55, {}),
    'Sign': ('#f4efe6', 0.4, 0.0, {'emission': ('#ffffff', 0.6)}),
    'Stone fin': ('#d9cbb6', 0.7, 0.0, {}),
    'Paving': ('#c9bcab', 0.85, 0.0, {}),
    'Deck paving': ('#e6bb8c', 0.85, 0.0, {}),
    'Wood': ('#9b6a44', 0.7, 0.0, {}),
    'Pool water': ('#38b4dc', 0.03, 0.0, {}),
    'Play orange': ('#d0653a', 0.8, 0.0, {}),
    'Play blue': ('#0f8dc4', 0.8, 0.0, {}),
    'Grass': ('#5c6a06', 1.0, 0.0, {}),
    'Lawn': ('#647608', 1.0, 0.0, {}),
    'Shrub': ('#35521a', 0.9, 0.0, {}),
    'Leaves': ('#34501a', 0.9, 0.0, {}),
    'Leaves light': ('#4f6e1e', 0.9, 0.0, {}),
    'Trunk': ('#5a4030', 0.9, 0.0, {}),
    'Asphalt': ('#58585c', 0.9, 0.0, {}),
    'Road line': ('#f0efe8', 0.6, 0.0, {}),
    'Kerb': ('#c9c3b8', 0.8, 0.0, {}),
    'Sidewalk': ('#b9aaa2', 0.85, 0.0, {}),
    'Stained orange': ('#c8702f', 0.1, 0.0, {'emission': ('#e07a2e', 0.12)}),
    'Stained pink': ('#c25586', 0.1, 0.0, {'emission': ('#d9508a', 0.12)}),
    'Stained blue': ('#3c63b8', 0.1, 0.0, {'emission': ('#2f5fd8', 0.12)}),
    'Stained violet': ('#7f52b0', 0.1, 0.0, {'emission': ('#8a48c8', 0.12)}),
    'Embankment': ('#b5ab9c', 0.95, 0.0, {}),
    'River': ('#0d78b4', 0.25, 0.0, {'specular': 0.3}),
    'Foam': ('#e8f2f4', 0.6, 0.0, {}),
    'Bridge': ('#b9b6b0', 0.8, 0.0, {}),
    'Metal': ('#7d8288', 0.35, 0.8, {}),
    'Neighbour': ('#dfe8ee', 0.15, 0.0, {'alpha': 0.3}),
    'Neighbour solid': ('#e9e7e3', 0.7, 0.0, {}),
    'Car': ('#d8dade', 0.3, 0.5, {}),
    'Car dark': ('#2a2e33', 0.3, 0.5, {}),
    'Car red': ('#b02a2a', 0.3, 0.5, {}),
    # roof deck and promenade (render 2)
    'Cobble': ('#a9a7a3', 0.9, 0.0, {}),          # grey irregular stone paving
    'Deck stone': ('#d4a97c', 0.85, 0.0, {}),     # warm tan large-format stone around the pool
    'Pool mosaic': ('#6f8fa3', 0.4, 0.0, {}),     # blue-grey pebble mosaic pool surround
    'Pool tile': ('#8fd6ec', 0.2, 0.0, {}),       # light blue pool walls / floor
    'Lamp white': ('#f2f1ec', 0.35, 0.1, {}),
    'Lamp glow': ('#fff6dd', 0.4, 0.0, {'emission': ('#fff3d6', 1.5)}),
    'Umbrella': ('#9c6f47', 0.8, 0.0, {}),        # square brown sail umbrellas
    'Lounger': ('#e9e3d8', 0.6, 0.0, {}),
    'Lattice wood': ('#c8a77e', 0.7, 0.0, {}),    # light timber geodesic pergolas, decks
    'Dark lattice': ('#5b3a2c', 0.7, 0.0, {}),    # dark brown climbing dome
    'Rubber blue': ('#1f63b0', 0.95, 0.0, {}),    # play surface
    'Fitness green': ('#4f9a35', 0.5, 0.3, {}),
    'Fitness yellow': ('#e0bd35', 0.5, 0.3, {}),
    'Planter': ('#d7d2c8', 0.8, 0.0, {}),         # light concrete planter walls
    'Bollard': ('#f1f0eb', 0.5, 0.0, {}),
    'Promenade': ('#d6cdc2', 0.85, 0.0, {}),      # light street paving
}


def build_materials():
    mats = {}
    for name, (hexc, rough, metal, extra) in SPECS.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (*srgb(hexc), 1.0)
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = metal
        if 'specular' in extra:
            bsdf.inputs['Specular IOR Level'].default_value = extra['specular']
        if 'alpha' in extra:
            bsdf.inputs['Alpha'].default_value = extra['alpha']
            m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
            try:
                m.surface_render_method = 'BLENDED'
            except AttributeError:
                pass
        if 'emission' in extra:
            col, strength = extra['emission']
            bsdf.inputs['Emission Color'].default_value = (*srgb(col), 1.0)
            bsdf.inputs['Emission Strength'].default_value = strength
        m.diffuse_color = (*srgb(hexc), extra.get('alpha', 1.0))
        mats[name] = m
    return mats
