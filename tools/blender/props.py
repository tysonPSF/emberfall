"""Builds Emberfall's world props in the KayKit Dungeon style and exports GLBs.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/props.py -- --out assets/props [--preview DIR] [--only pine_a]

KayKit models are colored by one shared palette texture: an 8x4 grid of vertical
gradients. Every face points its UVs into one swatch, and the height of each vertex
picks a spot along the gradient, so parts get the pack's soft top-light shading.
These props do the same with the Dungeon pack's texture, so they sit beside its
walls and barrels without looking foreign.

Props are authored in game meters (a character is about 1.65 m tall), face -Y,
and stand on the origin. Each prop is one mesh.
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ATLAS = os.path.join(ROOT, "assets/KayKit_Dungeon_Pack_1.1_FREE/Assets/gltf/dungeon_texture.png")

# Swatches on the atlas as (column, row), row 0 at the top.
STONE_DARK = (0, 0)
STONE_LIGHT = (1, 0)
CLAY = (2, 0)
WOOD = (4, 0)
STONE_WARM = (5, 0)
EMBER = (6, 0)
WOOD_GREY = (7, 0)
HIDE = (1, 1)
LEAF = (1, 2)
FLAME = (7, 2)
GOLD = (5, 2)
RUNE = (6, 2)
PINE = (4, 3)
BONE = (0, 3)


def reset_scene():
	bpy.ops.wm.read_factory_settings(use_empty=True)


_materials = {}


def atlas_material(glow=0.0):
	"""The shared palette material; glowing parts use a second copy with emission."""
	key = glow
	if key in _materials:
		return _materials[key]
	m = bpy.data.materials.new("dungeon_glow" if glow else "dungeon")
	m.use_nodes = True
	nodes = m.node_tree.nodes
	bsdf = nodes["Principled BSDF"]
	tex = nodes.new("ShaderNodeTexImage")
	tex.image = bpy.data.images.load(ATLAS, check_existing=True)
	tex.interpolation = "Closest"
	m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
	bsdf.inputs["Roughness"].default_value = 0.9
	if glow:
		m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
		bsdf.inputs["Emission Strength"].default_value = glow
	_materials[key] = m
	return m


class Prop:
	"""Collects parts; each part's UVs are painted into one atlas swatch."""

	def __init__(self, name, seed=1):
		self.name = name
		self.parts = []
		self.rng = random.Random(seed)

	def _add(self, bm, swatch, grad, glow, jitter):
		if jitter:
			for v in bm.verts:
				v.co += Vector([self.rng.uniform(-jitter, jitter) for _ in range(3)])
		mesh = bpy.data.meshes.new(f"{self.name}_part")
		bm.to_mesh(mesh)
		bm.free()
		self._paint(mesh, swatch, grad)
		obj = bpy.data.objects.new(mesh.name, mesh)
		bpy.context.collection.objects.link(obj)
		obj.data.materials.append(atlas_material(glow))
		self.parts.append(obj)
		return obj

	@staticmethod
	def _paint(mesh, swatch, grad):
		"""UV every vertex into the swatch: x in its solid strip, y by the vertex's height in the part."""
		col, row = swatch
		zs = [v.co.z for v in mesh.vertices]
		lo, hi = min(zs), max(zs)
		span = max(hi - lo, 1e-4)
		u = (col * 128 + 48) / 1024.0
		top, bottom = 1.0 - row * 0.25, 1.0 - (row + 1) * 0.25
		g0, g1 = grad  # 0 = top of the swatch (light), 1 = bottom (dark)
		uv = mesh.uv_layers.new(name="UVMap")
		for loop in mesh.loops:
			z = mesh.vertices[loop.vertex_index].co.z
			h = 1.0 - (z - lo) / span  # 0 at the part's top
			g = g0 + (g1 - g0) * h
			uv.data[loop.index].uv = (u, top + (bottom - top) * (0.02 + 0.96 * g))

	def blob(self, size, loc, swatch, rot=(0, 0, 0), segs=(8, 6), grad=(0.1, 0.8), glow=0.0, jitter=0.0):
		bm = bmesh.new()
		bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=0.5)
		self._xform(bm, loc, rot, size)
		return self._add(bm, swatch, grad, glow, jitter)

	def rock(self, size, loc, swatch, rot=(0, 0, 0), grad=(0.05, 0.85), jitter=0.08):
		bm = bmesh.new()
		bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.5)
		self._xform(bm, loc, rot, size)
		return self._add(bm, swatch, grad, 0.0, jitter * max(size))

	def box(self, size, loc, swatch, rot=(0, 0, 0), grad=(0.1, 0.8), glow=0.0, jitter=0.0):
		bm = bmesh.new()
		bmesh.ops.create_cube(bm, size=1.0)
		self._xform(bm, loc, rot, size)
		return self._add(bm, swatch, grad, glow, jitter)

	def seg(self, a, b, r1, r2, swatch, sides=6, grad=(0.1, 0.8), glow=0.0, jitter=0.0, twist=0.0):
		"""Tapered cylinder from a to b (r2 = 0 makes a cone)."""
		a, b = Vector(a), Vector(b)
		d = b - a
		bm = bmesh.new()
		bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r1, radius2=max(r2, 0.0),
							  depth=d.length)
		q = Vector((0, 0, 1)).rotation_difference(d.normalized())
		m = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(twist), 4, "Z")
		bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
		return self._add(bm, swatch, grad, glow, jitter)

	def poly(self, verts, faces, swatch, grad=(0.1, 0.8)):
		bm = bmesh.new()
		vs = [bm.verts.new(v) for v in verts]
		for f in faces:
			bm.faces.new([vs[i] for i in f])
		bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
		return self._add(bm, swatch, grad, 0.0, 0.0)

	@staticmethod
	def _xform(bm, loc, rot, size):
		m = Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot]), Vector(size))
		bmesh.ops.transform(bm, matrix=m, verts=bm.verts)

	def build(self):
		bpy.ops.object.select_all(action="DESELECT")
		for p in self.parts:
			p.select_set(True)
		bpy.context.view_layer.objects.active = self.parts[0]
		bpy.ops.object.join()
		obj = self.parts[0]
		obj.name = self.name
		return obj


# ---------------------------------------------------------------- nature

def pine(name, seed, tiers):
	p = Prop(name, seed)
	h = 0.0
	p.seg((0, 0, -0.2), (0, 0, 2.2), 0.28, 0.16, WOOD, sides=6, grad=(0.3, 0.9))
	base = 1.1
	for i, (radius, height) in enumerate(tiers):
		z = base + h
		p.seg((0, 0, z), (0, 0, z + height), radius, 0.0, PINE, sides=7, grad=(0.0, 0.75),
			  jitter=0.06, twist=p.rng.uniform(0, 50))
		h += height * 0.55
	return p.build()


def tree_round():
	p = Prop("tree_round", 7)
	p.seg((0, 0, -0.2), (0, 0, 2.4), 0.3, 0.2, WOOD, sides=6, grad=(0.3, 0.9))
	p.seg((0, 0, 1.7), (0.7, 0.1, 2.6), 0.12, 0.06, WOOD, sides=5)
	for loc, s in (((0, 0, 3.4), 2.6), ((0.8, 0.3, 2.9), 1.7), ((-0.7, -0.4, 3.0), 1.8), ((0.1, 0.6, 4.2), 1.6)):
		p.rock((s, s, s * 0.85), loc, LEAF, grad=(0.0, 0.7), jitter=0.05)
	return p.build()


def boulder(name, seed, parts):
	p = Prop(name, seed)
	for size, loc in parts:
		p.rock(size, loc, STONE_DARK, rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.0, 0.8), jitter=0.1)
	return p.build()


def standing_stone():
	p = Prop("standing_stone", 11)
	p.seg((0, 0, -0.3), (0, 0, 1.9), 0.42, 0.26, STONE_LIGHT, sides=5, grad=(0.1, 0.9), jitter=0.05, twist=18)
	p.rock((0.9, 0.9, 0.35), (0, 0, 0.0), STONE_DARK, jitter=0.06)
	return p.build()


# ---------------------------------------------------------------- landmarks

def obelisk():
	p = Prop("obelisk", 3)
	p.box((3.0, 3.0, 0.4), (0, 0, 0.2), STONE_DARK, grad=(0.2, 0.9))
	p.box((2.2, 2.2, 0.4), (0, 0, 0.6), STONE_DARK, grad=(0.1, 0.7))
	p.seg((0, 0, 0.8), (0, 0, 6.0), 0.85, 0.55, STONE_LIGHT, sides=4, grad=(0.0, 0.85), twist=45)
	p.seg((0, 0, 6.0), (0, 0, 7.0), 0.55, 0.0, STONE_LIGHT, sides=4, grad=(0.0, 0.5), twist=45)
	for k in range(4):  # glowing runes, one per face
		a = k * math.pi / 2
		for i, z in enumerate((2.0, 3.1, 4.2)):
			r = 0.8 - 0.3 * (z - 0.8) / 5.2 + 0.02
			w = 0.34 if i != 1 else 0.22
			p.box((w, 0.06, 0.34), (math.sin(a) * r, -math.cos(a) * r, z), RUNE,
				  rot=(0, 0, math.degrees(a)), grad=(0.3, 0.5), glow=1.2)
	p.blob((0.3, 0.3, 0.3), (0, 0, 7.25), RUNE, grad=(0.2, 0.4), glow=1.8)
	return p.build()


def tent():
	"""Gnoll hide tent: A-frame with lashed poles, open at the front (-Y)."""
	p = Prop("tent", 5)
	w, d, h = 3.6, 4.2, 2.8
	half = w / 2
	# hide: each side is two panels sagging at the middle, plus a back wall
	p.poly([(-half, -d / 2, 0), (0, -d / 2, h), (-0.1, 0, h - 0.15), (-half - 0.1, 0, 0.1)], [(0, 1, 2, 3)], HIDE, grad=(0.3, 1.0))
	p.poly([(-half - 0.1, 0, 0.1), (-0.1, 0, h - 0.15), (0, d / 2, h), (-half, d / 2, 0)], [(0, 1, 2, 3)], HIDE, grad=(0.3, 1.0))
	p.poly([(half, -d / 2, 0), (0, -d / 2, h), (0.1, 0, h - 0.15), (half + 0.1, 0, 0.1)], [(0, 1, 2, 3)], HIDE, grad=(0.4, 1.0))
	p.poly([(half + 0.1, 0, 0.1), (0.1, 0, h - 0.15), (0, d / 2, h), (half, d / 2, 0)], [(0, 1, 2, 3)], HIDE, grad=(0.4, 1.0))
	p.poly([(-half, d / 2, 0), (0, d / 2, h), (half, d / 2, 0)], [(0, 1, 2)], HIDE, grad=(0.3, 1.0))
	# thicken the panels by giving them a dark inner copy
	for obj in p.parts:
		mod = obj.modifiers.new("solid", "SOLIDIFY")
		mod.thickness = 0.06
	# poles cross above the ridge at both ends, plus the ridge pole
	for y in (-d / 2 - 0.05, d / 2 + 0.05):
		p.seg((-half - 0.2, y, -0.1), (0.35, y, h + 0.45), 0.07, 0.05, WOOD, sides=5)
		p.seg((half + 0.2, y, -0.1), (-0.35, y, h + 0.45), 0.07, 0.05, WOOD, sides=5)
	p.seg((0, -d / 2 - 0.3, h + 0.02), (0, d / 2 + 0.3, h + 0.02), 0.06, 0.06, WOOD, sides=5)
	# stitched patches and a bone charm on the ridge
	p.box((0.5, 0.04, 0.45), (-half * 0.55, d / 2 + 0.05, h * 0.3), WOOD_GREY)
	p.blob((0.14, 0.14, 0.3), (0, -d / 2 - 0.1, h - 0.35), BONE, grad=(0.0, 0.5))
	for s in (-1, 1):
		p.seg((0, -d / 2 - 0.1, h - 0.2), (0.15 * s, -d / 2 - 0.12, h - 0.02), 0.04, 0.02, BONE, sides=4)
	return p.build()


def campfire():
	p = Prop("campfire", 9)
	for k in range(9):
		a = k * math.tau / 9
		p.rock((0.42, 0.34, 0.3), (math.cos(a) * 0.85, math.sin(a) * 0.85, 0.1), STONE_DARK,
			   rot=(0, 0, math.degrees(a)), jitter=0.05)
	for k in range(4):
		a = k * math.tau / 4 + 0.4
		p.seg((math.cos(a) * 0.7, math.sin(a) * 0.7, 0.05), (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.55),
			  0.1, 0.08, WOOD, sides=5, grad=(0.4, 1.0))
	p.blob((1.1, 1.1, 0.12), (0, 0, 0.04), EMBER, grad=(0.6, 0.9), glow=0.8)
	for loc, r, hgt in (((0, 0, 0.1), 0.42, 1.2), ((0.22, 0.12, 0.1), 0.26, 0.85), ((-0.2, -0.1, 0.1), 0.24, 0.8),
						 ((0.05, -0.25, 0.1), 0.2, 0.6)):
		p.seg(loc, (loc[0], loc[1], loc[2] + hgt), r, 0.0, FLAME, sides=6, grad=(0.1, 0.95), glow=1.2,
			  twist=p.rng.uniform(0, 60))
	return p.build()


def torch_post():
	"""Post for a pack torch; the game sets torch_lit into the cup at 1.75 m."""
	p = Prop("torch_post", 13)
	p.seg((0, 0, -0.3), (0, 0, 1.7), 0.09, 0.07, WOOD, sides=6, grad=(0.2, 1.0))
	p.seg((0, 0, 1.55), (0, 0, 1.78), 0.13, 0.15, WOOD_GREY, sides=6)
	for s in (-1, 1):
		p.seg((0, 0, 1.35), (0.09 * s, 0, 1.6), 0.025, 0.02, WOOD_GREY, sides=4)
	return p.build()


def banner_pole():
	"""Pole with a crossbar; the game hangs a pack banner from it (bar at 3.1 m)."""
	p = Prop("banner_pole", 17)
	p.seg((0, 0, -0.3), (0, 0, 3.45), 0.1, 0.08, WOOD, sides=6, grad=(0.2, 1.0))
	p.seg((-0.7, 0, 3.12), (0.7, 0, 3.12), 0.05, 0.05, WOOD, sides=5)
	p.blob((0.22, 0.22, 0.32), (0, 0, 3.55), BONE, grad=(0.0, 0.5))           # skull-ish knob
	p.blob((0.06, 0.03, 0.06), (0.06, -0.1, 3.58), STONE_DARK)
	p.blob((0.06, 0.03, 0.06), (-0.06, -0.1, 3.58), STONE_DARK)
	return p.build()


def palisade():
	"""4 m run of sharpened logs lashed together, along X."""
	p = Prop("palisade", 21)
	n = 9
	for i in range(n):
		x = -2.0 + (i + 0.5) * 4.0 / n
		top = 2.2 + p.rng.uniform(-0.25, 0.25)
		r = 0.2 + p.rng.uniform(-0.02, 0.03)
		lean = p.rng.uniform(-0.05, 0.05)
		p.seg((x, 0, -0.3), (x + lean, 0, top), r, r * 0.92, WOOD, sides=6, grad=(0.25, 1.0))
		p.seg((x + lean, 0, top), (x + lean * 1.1, 0, top + 0.45), r * 0.92, 0.0, WOOD_GREY, sides=6, grad=(0.0, 0.6))
	for z in (0.6, 1.6):
		p.seg((-2.0, 0.2, z), (2.0, 0.2, z + 0.05), 0.05, 0.05, WOOD_GREY, sides=4)
	return p.build()


PROPS = {
	"pine_a": lambda: pine("pine_a", 1, [(1.9, 2.4), (1.5, 2.1), (1.05, 1.8), (0.6, 1.4)]),
	"pine_b": lambda: pine("pine_b", 2, [(1.6, 2.2), (1.15, 1.9), (0.7, 1.6)]),
	"tree_round": tree_round,
	"boulder_a": lambda: boulder("boulder_a", 4, [((1.8, 1.4, 1.1), (0, 0, 0.35)), ((0.9, 0.8, 0.7), (0.9, 0.3, 0.2))]),
	"boulder_b": lambda: boulder("boulder_b", 6, [((1.2, 1.0, 1.3), (0, 0, 0.5))]),
	"boulder_c": lambda: boulder("boulder_c", 8, [((2.4, 1.9, 1.4), (0, 0, 0.4)), ((1.2, 1.0, 1.1), (-0.9, 0.7, 0.9)),
												  ((0.7, 0.6, 0.5), (1.3, -0.6, 0.15))]),
	"standing_stone": standing_stone,
	"obelisk": obelisk,
	"tent": tent,
	"campfire": campfire,
	"torch_post": torch_post,
	"banner_pole": banner_pole,
	"palisade": palisade,
}


# ---------------------------------------------------------------- export + preview

def export(path):
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
							  export_animations=False, export_yup=True, export_apply=True)


def preview(obj, name, out_dir):
	scene = bpy.context.scene
	scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
	scene.render.resolution_x, scene.render.resolution_y = 400, 400
	world = bpy.data.worlds.new("w")
	world.use_nodes = True
	world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.7, 1)
	world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
	scene.world = world
	sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
	sun.data.energy = 3.0
	sun.rotation_euler = (math.radians(50), 0, math.radians(30))
	bpy.context.collection.objects.link(sun)
	dims = obj.dimensions
	r = max(dims.x, dims.y, dims.z)
	cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
	bpy.context.collection.objects.link(cam)
	cam.location = (r * 1.3, -r * 1.6, dims.z * 0.5 + r * 0.7)
	target = Vector((0, 0, dims.z * 0.45))
	cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
	scene.camera = cam
	scene.render.filepath = os.path.join(out_dir, f"{name}.png")
	bpy.ops.render.render(write_still=True)


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/props", "--preview": "", "--only": ""}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) if opts["--only"] else None
	for name, build in PROPS.items():
		if only and name not in only:
			continue
		reset_scene()
		_materials.clear()
		obj = build()
		export(os.path.abspath(os.path.join(opts["--out"], f"{name}.glb")))
		if opts["--preview"]:
			os.makedirs(opts["--preview"], exist_ok=True)
			preview(obj, name, opts["--preview"])
		print(f"exported {name}")


main()
