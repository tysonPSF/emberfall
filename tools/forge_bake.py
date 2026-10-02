"""Bake the Elephant Grove Forge's unique weapons into GLBs.

    python3 tools/forge_bake.py [--forge ../elephant-grove/forge] [--only drsword]

The Forge (elephant-grove/forge/forge.html) is the source of truth for every
weapon model in Elephant Grove, and it builds them in three.js at run time --
there is no file to copy. The art pipeline over there opens the page in a
headless browser and photographs it; this does the same thing but takes the
geometry instead of the pixels, and writes one GLB per weapon into
assets/forge_raw/.

What comes out is RAW: the Forge's own units (about 2.3x Emberfall's), its own
orientation, origin at the model root rather than at the grip, and its own
triangle count (5k-13k, against 200-3k for the weapons Emberfall ships).
tools/blender/creatures.py imports these, fixes all of that and exports the
real asset into assets/creatures/. Nothing here is shipped.

Two things worth knowing before you touch it:

- The page only builds 3D models once it is in Smooth 3D mode; in pixel mode
  R3 is null and there is nothing to read.
- A mesh's matrixWorld carries the viewer's turn, tilt and inventory pose, so
  it is taken relative to the model root. Bake the world matrix in and every
  weapon arrives tumbled.
- Tide-Horn has no 3D definition in the Forge (D3() throws for it), and
  selecting it leaves the previous weapon on screen, so it bakes as a silent
  duplicate. It is skipped, and the Forge's own check_forge.py does not catch
  this - a 14th check would.
"""
import argparse, collections, json, os, sys, http.server, threading, functools

DUMP_JS = r"""
(id) => {
  pickWeapon(id);
  if (!R3) return {error: 'not in Smooth 3D mode'};
  let d; try { d = D3(); } catch (e) { return {error: 'no 3D definition'}; }
  if (!d || !tiers.length || !d[tiers[Math.min(cur, tiers.length-1)].key])
    return {error: 'no 3D definition'};
  const tier = Math.min(cur, R3.swords.length - 1);
  rebuildSword(tier);
  const sw = R3.swords[tier];
  if (!sw) return {error: 'nothing built'};
  const byUuid = {};
  Object.entries(sw.mats || {}).forEach(([n, m]) => {
    (Array.isArray(m) ? m : [m]).forEach(x => { if (x && x.uuid) byUuid[x.uuid] = n; });
  });
  const root = sw.root;
  root.updateWorldMatrix(true, true);
  const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
  const parts = [];
  root.traverse(o => {
    if (!o.isMesh || !o.geometry || !o.geometry.attributes.position) return;
    const g = o.geometry, pos = g.attributes.position;
    const m = Array.isArray(o.material) ? o.material[0] : o.material;
    parts.push({
      matrix: new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld).elements.slice(),
      pos: Array.from(pos.array),
      idx: g.index ? Array.from(g.index.array)
                   : Array.from({length: pos.count}, (_, i) => i),
      colour: m && m.color ? m.color.getHex() : 0xcccccc,
      emissive: m && m.emissive ? m.emissive.getHex() : 0,
      emissiveIntensity: (m && m.emissiveIntensity) || 0,
      metalness: (m && m.metalness) || 0,
      roughness: m && m.roughness !== undefined ? m.roughness : 1,
      mat: (m && byUuid[m.uuid]) || 'part',
    });
  });
  return {id, tier, parts, matNames: Object.keys(sw.mats || {})};
}
"""

# the Forge's weapon id -> the Emberfall item that should wear it
MAP = {
    'drsword': 'dragonfang_sword', 'drdagger': 'dragontooth_dagger',
    'draxe': 'dragonclaw_axe', 'drmace': 'dragonmaw_mace',
    'drflail': 'dragontail_flail', 'drclaws': 'dragonclaw_fists',
    'drwand': 'dragoneye_wand', 'drgsword': 'dragonfang_greatsword',
    'drgaxe': 'dragonclaw_great_axe', 'drgmace': 'dragonmaw_great_mace',
    'drgflail': 'dragontail_great_flail', 'drspear': 'dragontongue_spear',
    'drstaff': 'dragonheart_staff', 'drbow': 'dragonwing_bow',
    'drarrow': 'dragonbone_arrow', 'uniq1h': 'sword_of_the_endless_nightmare',
    'uniq2h': 'greatsword_of_the_endless_nightmare',
}


def to_scene(dump):
    """One mesh per material, baked into the model's own space, material names
    kept so Blender can find "flame" and "blade" rather than "material_7"."""
    import numpy as np, trimesh
    groups = collections.defaultdict(lambda: {'v': [], 'f': [], 'm': None})
    for part in dump['parts']:
        M = np.array(part['matrix'], float).reshape(4, 4).T   # three.js is column-major
        v = np.array(part['pos'], float).reshape(-1, 3)
        v = (np.c_[v, np.ones(len(v))] @ M.T)[:, :3]
        f = np.array(part['idx'], int).reshape(-1, 3)
        g = groups[part['mat']]
        g['f'].append(f + sum(len(x) for x in g['v']))
        g['v'].append(v)
        g['m'] = g['m'] or part
    hexc = lambda n: [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]
    scene = trimesh.Scene()
    for name, g in groups.items():
        p = g['m']
        mesh = trimesh.Trimesh(vertices=np.vstack(g['v']), faces=np.vstack(g['f']),
                               process=False)
        mesh.visual = trimesh.visual.TextureVisuals(
            material=trimesh.visual.material.PBRMaterial(
                name=name, baseColorFactor=hexc(p['colour']) + [1.0],
                emissiveFactor=[min(1.0, c * max(0.0, p['emissiveIntensity']))
                                for c in hexc(p['emissive'])],
                metallicFactor=float(p['metalness']),
                roughnessFactor=float(p['roughness'])))
        scene.add_geometry(mesh, geom_name=name)
    return scene


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument('--forge', default=os.path.join(root, '..', 'elephant-grove', 'forge'))
    ap.add_argument('--out', default=os.path.join(root, 'assets', 'forge_raw'))
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    ids = [i for i in (a.only.split(',') if a.only else MAP) if i]
    os.makedirs(a.out, exist_ok=True)

    from playwright.sync_api import sync_playwright
    os.chdir(a.forge)
    srv = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 9140), functools.partial(http.server.SimpleHTTPRequestHandler))
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    manifest = {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
        pg = b.new_page(viewport={'width': 1400, 'height': 1000})
        pg.goto('http://127.0.0.1:9140/forge.html'); pg.wait_for_timeout(3000)
        pg.get_by_role('button', name='Smooth 3D', exact=True).click()
        pg.wait_for_timeout(3000)
        for i in ids:
            d = pg.evaluate(DUMP_JS, i)
            if 'error' in d:
                print(f'  -- {i}: {d["error"]}, skipped')
                continue
            sc = to_scene(d)
            sc.export(os.path.join(a.out, f'{i}.glb'))
            ex = (sc.bounds[1] - sc.bounds[0]).round(3).tolist()
            tris = int(sum(len(g.faces) for g in sc.geometry.values()))
            manifest[MAP.get(i, i)] = {
                'forge_id': i, 'raw': f'assets/forge_raw/{i}.glb',
                'materials': sorted(sc.geometry.keys()),
                'tris': tris, 'forge_extent': ex}
            print(f'  ok {i:10} {len(sc.geometry):2} materials  {tris:6} tris  {ex}')
        b.close()
    srv.shutdown()
    out = os.path.join(a.out, 'forge_bake.json')
    old = json.load(open(out)) if os.path.exists(out) else {}
    old.setdefault('_about', 'Raw Forge geometry. Inputs to the Blender step, not shipped.')
    old.setdefault('forge_units_to_emberfall', 0.44)
    old.setdefault('weapons', {}).update(manifest)
    json.dump(old, open(out, 'w'), indent=1)
    print(f'\n{len(manifest)} weapons -> {a.out}')


if __name__ == '__main__':
    main()
