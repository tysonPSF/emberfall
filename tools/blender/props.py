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
WOOD_GRAY = (7, 0)
HIDE = (1, 1)
LEAF = (1, 2)
FLAME = (7, 2)
GOLD = (5, 2)
RUNE = (6, 2)
PINE = (4, 3)
BONE = (0, 3)
WATER = (2, 3)
CLOTH_RED = (3, 2)
CLOTH_WHITE = (0, 1)
IRON = (3, 0)
SHADE = (6, 3)  # white-to-black gradient: clutter the game tints per instance
PETAL_YELLOW = (7, 2)
PETAL_PURPLE = (3, 1)
PETAL_WHITE = (0, 1)
MUSHROOM = (3, 2)


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

	def build(self, bevel=0.0):
		"""Joins the parts into one object. `bevel` rounds every hard edge by
		that many meters, the way KayKit's own pieces are modeled."""
		bpy.ops.object.select_all(action="DESELECT")
		for p in self.parts:
			p.select_set(True)
		bpy.context.view_layer.objects.active = self.parts[0]
		bpy.ops.object.join()
		obj = self.parts[0]
		obj.name = self.name
		if bevel > 0.0:
			mod = obj.modifiers.new("bevel", "BEVEL")
			mod.width = bevel
			mod.segments = 2
			mod.limit_method = "ANGLE"
			mod.angle_limit = math.radians(40)
			mod.harden_normals = True
			bpy.ops.object.modifier_apply(modifier=mod.name)
		return obj


KAYKIT = os.path.join(ROOT, "assets/KayKit_Dungeon_Pack_1.1_FREE/Assets/gltf")


def kaykit(piece, loc, rot_z=0.0, scale=(0.75, 0.75, 0.75)):
	"""Imports a KayKit Dungeon piece, placed and scaled, with its transform
	baked in so it can join a prop: buildings made of the same walls as the
	houses match them exactly."""
	before = set(bpy.data.objects)
	bpy.ops.import_scene.gltf(filepath=os.path.join(KAYKIT, piece + ".gltf"))
	meshes = []
	for o in set(bpy.data.objects) - before:
		if o.type != "MESH":
			continue
		world = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Diagonal((*scale, 1.0)) @ o.matrix_world
		o.parent = None
		o.data.transform(world)
		o.matrix_world = Matrix.Identity(4)
		meshes.append(o)
	for o in set(bpy.data.objects) - before:
		if o.type != "MESH":
			bpy.data.objects.remove(o, do_unlink=True)
	return meshes


def join_into(obj, others):
	bpy.ops.object.select_all(action="DESELECT")
	for o in [obj] + others:
		o.select_set(True)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.join()
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
	p.box((0.5, 0.04, 0.45), (-half * 0.55, d / 2 + 0.05, h * 0.3), WOOD_GRAY)
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
	p.seg((0, 0, 1.55), (0, 0, 1.78), 0.13, 0.15, WOOD_GRAY, sides=6)
	for s in (-1, 1):
		p.seg((0, 0, 1.35), (0.09 * s, 0, 1.6), 0.025, 0.02, WOOD_GRAY, sides=4)
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
		p.seg((x + lean, 0, top), (x + lean * 1.1, 0, top + 0.45), r * 0.92, 0.0, WOOD_GRAY, sides=6, grad=(0.0, 0.6))
	for z in (0.6, 1.6):
		p.seg((-2.0, 0.2, z), (2.0, 0.2, z + 0.05), 0.05, 0.05, WOOD_GRAY, sides=4)
	return p.build()


def roof_gable():
	"""Gable roof for a 2x2 Dungeon-wall room (6 m square, walls 3 m tall).
	Sits on the wall tops; the ridge runs front to back so the gables face the door."""
	p = Prop("roof_gable", 23)
	w, d, h = 7.6, 7.8, 2.3
	half = w / 2
	slope = math.hypot(half, h)
	ang = math.atan2(h, half)
	rows = 5
	for s in (1, -1):
		down = Vector((math.cos(ang) * s, 0, -math.sin(ang)))
		out = Vector((math.sin(ang) * s, 0, math.cos(ang)))
		p.box((slope, d, 0.16), Vector((0, 0, h)) + down * slope / 2, WOOD_GRAY, rot=(0, math.degrees(ang) * s, 0))
		for i in range(rows):  # shingle courses, each its own gradient so they read as rows
			c = Vector((0, 0, h)) + down * slope * (i + 0.55) / rows + out * 0.13
			p.box((slope / rows * 1.12, d + 0.1, 0.12), c, CLAY, rot=(0, math.degrees(ang) * s, 0), grad=(0.0, 0.9))
	for y in (-d / 2 + 0.45, d / 2 - 0.45):  # gable ends: timber triangle
		t = 0.14
		tri = [(-half + 0.45, 0, 0), (half - 0.45, 0, 0), (0, 0, h - 0.2)]
		verts = [(x, y - t / 2, z) for x, _, z in tri] + [(x, y + t / 2, z) for x, _, z in tri]
		p.poly(verts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], WOOD, grad=(0.3, 1.0))
	p.seg((0, -d / 2 - 0.15, h + 0.12), (0, d / 2 + 0.15, h + 0.12), 0.13, 0.13, WOOD, sides=6)
	p.box((0.8, 0.8, 2.0), (1.7, 1.6, 1.6), STONE_DARK, grad=(0.1, 0.9))                       # chimney
	p.box((1.0, 1.0, 0.2), (1.7, 1.6, 2.65), STONE_LIGHT, grad=(0.2, 0.7))
	return p.build()


# ---------------------------------------------------------------- city (Emberhold)

def hearth():
	"""The eternal hearth of Emberhold: a stepped stone dais, an iron bowl and a tall fire."""
	p = Prop("hearth", 31)
	p.seg((0, 0, 0), (0, 0, 0.5), 3.4, 3.3, STONE_DARK, sides=8, grad=(0.3, 0.9), twist=22.5)
	p.seg((0, 0, 0.5), (0, 0, 0.9), 2.5, 2.4, STONE_LIGHT, sides=8, grad=(0.1, 0.7), twist=22.5)
	p.seg((0, 0, 0.9), (0, 0, 1.9), 0.55, 1.55, IRON, sides=10, grad=(0.3, 1.0))
	p.seg((0, 0, 1.85), (0, 0, 2.0), 1.6, 1.6, IRON, sides=10, grad=(0.0, 0.4))
	p.blob((2.6, 2.6, 0.35), (0, 0, 1.95), EMBER, grad=(0.5, 0.9), glow=1.0)
	for k, (r, hgt) in enumerate(((0.9, 3.4), (0.6, 2.6), (0.55, 2.4), (0.5, 2.2), (0.45, 1.9))):
		a = k * 1.9
		off = 0.0 if k == 0 else 0.55
		p.seg((math.cos(a) * off, math.sin(a) * off, 1.95), (math.cos(a) * off * 0.6, math.sin(a) * off * 0.6, 1.95 + hgt),
			  r, 0.0, FLAME, sides=6, grad=(0.05, 0.95), glow=1.3, twist=a * 20)
	for k in range(8):  # ring of short posts with ember caps
		a = k * math.tau / 8 + math.tau / 16
		x, y = math.cos(a) * 3.0, math.sin(a) * 3.0
		p.seg((x, y, 0.5), (x, y, 1.5), 0.2, 0.17, STONE_LIGHT, sides=6)
		p.blob((0.3, 0.3, 0.2), (x, y, 1.58), EMBER, glow=0.8)
	return p.build()


def city_wall():
	"""6 m run of curtain wall along X, 5 m tall, crenellated on both faces."""
	p = Prop("city_wall", 33)
	p.box((6.1, 2.0, 0.9), (0, 0, 0.35), STONE_DARK, grad=(0.3, 1.0))
	p.box((6.05, 1.6, 4.3), (0, 0, 2.95), STONE_LIGHT, grad=(0.05, 0.9))
	for k in range(6):  # a few darker courses of stone for texture
		x = -2.5 + k + p.rng.uniform(-0.2, 0.2)
		z = 1.3 + p.rng.uniform(0, 2.8)
		for side in (-1, 1):
			p.box((0.8, 0.06, 0.35), (x, side * 0.81, z), STONE_DARK, grad=(0.3, 0.6))
	for k in range(4):
		x = -2.25 + k * 1.5
		for side in (-1, 1):
			p.box((0.8, 0.35, 0.8), (x, side * 0.62, 5.5), STONE_LIGHT, grad=(0.0, 0.6))
	return p.build()


def city_tower():
	p = Prop("city_tower", 35)
	p.seg((0, 0, -0.2), (0, 0, 1.0), 3.1, 3.0, STONE_DARK, sides=8, grad=(0.3, 1.0), twist=22.5)
	p.seg((0, 0, 1.0), (0, 0, 7.4), 2.7, 2.5, STONE_LIGHT, sides=8, grad=(0.05, 0.9), twist=22.5)
	p.seg((0, 0, 7.4), (0, 0, 8.0), 3.0, 3.0, STONE_LIGHT, sides=8, grad=(0.1, 0.6), twist=22.5)
	p.seg((0, 0, 8.0), (0, 0, 11.6), 3.3, 0.0, CLAY, sides=8, grad=(0.0, 0.9), twist=22.5)
	p.seg((0, 0, 11.4), (0, 0, 12.6), 0.05, 0.04, IRON, sides=4)
	p.box((0.05, 0.9, 0.5), (0, 0.45, 12.3), CLOTH_RED, grad=(0.2, 0.6))
	for k in range(4):  # arrow slits
		a = k * math.pi / 2 + math.pi / 8
		p.box((0.18, 0.1, 0.9), (math.cos(a) * 2.62, math.sin(a) * 2.62, 4.6), IRON, rot=(0, 0, math.degrees(a) + 90))
	return p.build()


def city_gate():
	"""Gatehouse along X, 12 m wide: two towers and a 4.4 m passage with raised portcullis."""
	p = Prop("city_gate", 37)
	for s in (-1, 1):
		x = s * 4.2
		p.box((3.6, 5.0, 0.9), (x, 0, 0.35), STONE_DARK, grad=(0.3, 1.0))
		p.box((3.4, 4.8, 7.8), (x, 0, 4.2), STONE_LIGHT, grad=(0.05, 0.9))
		for k in range(3):
			for side in (-1, 1):
				p.box((0.75, 0.4, 0.8), (x - 1.2 + k * 1.2, side * 2.2, 8.5), STONE_LIGHT, grad=(0.0, 0.6))
		p.box((0.14, 0.9, 1.4), (x, -2.42, 5.0), IRON)  # arrow slit
		p.box((0.14, 0.9, 1.4), (x, 2.42, 5.0), IRON)
	p.box((5.0, 4.8, 2.6), (0, 0, 6.8), STONE_LIGHT, grad=(0.05, 0.9))          # span over the passage
	for s in (-1, 1):
		p.box((0.9, 4.8, 0.9), (s * 2.0, 0, 5.3), STONE_LIGHT, rot=(0, s * 45, 0))  # corbels
	for k in range(5):
		p.box((5.0, 0.4, 0.8), (0, -2.2 + k * 1.1, 8.5) if k in (0, 4) else (0, -2.2 + k * 1.1, 8.15), STONE_LIGHT, grad=(0.0, 0.6))
	for k in range(7):  # raised portcullis bars
		p.box((0.1, 0.1, 1.6), (-1.8 + k * 0.6, 1.6, 6.2), IRON)
	p.box((4.4, 0.12, 0.12), (0, 1.6, 5.5), IRON)
	for s in (-1, 1):  # open gate leaves against the passage walls
		p.box((0.2, 2.2, 4.6), (s * 2.3, -1.1, 2.3), WOOD, grad=(0.2, 1.0))
		for z in (1.0, 3.6):
			p.box((0.24, 2.25, 0.18), (s * 2.3, -1.1, z), IRON)
	p.box((4.4, 5.0, 0.12), (0, 0, 0.02), STONE_DARK, grad=(0.5, 0.9))
	return p.build()


def lamp_post():
	p = Prop("lamp_post", 39)
	p.seg((0, 0, -0.2), (0, 0, 0.4), 0.22, 0.18, STONE_DARK, sides=6)
	p.seg((0, 0, 0.4), (0, 0, 3.2), 0.08, 0.07, IRON, sides=6, grad=(0.2, 0.9))
	p.seg((0, 0, 3.05), (0, -0.55, 3.15), 0.04, 0.04, IRON, sides=4)
	p.box((0.34, 0.34, 0.08), (0, -0.62, 3.1), IRON)
	p.box((0.26, 0.26, 0.38), (0, -0.62, 2.86), GOLD, grad=(0.1, 0.5), glow=1.6)
	for dx in (-0.14, 0.14):
		for dy in (-0.14, 0.14):
			p.box((0.035, 0.035, 0.42), (dx, -0.62 + dy, 2.86), IRON)
	p.seg((0, -0.62, 3.14), (0, -0.62, 3.34), 0.2, 0.02, IRON, sides=4, twist=45)
	return p.build()


def market_stall():
	p = Prop("market_stall", 41)
	for x in (-1.3, 1.3):
		for y in (-0.8, 0.8):
			p.seg((x, y, -0.1), (x, y, 2.4 if y > 0 else 2.0), 0.07, 0.06, WOOD, sides=5)
	p.box((2.8, 1.0, 0.9), (0, -0.5, 0.45), WOOD, grad=(0.2, 1.0))
	p.box((3.0, 1.2, 0.08), (0, -0.5, 0.93), WOOD_GRAY)
	stripes = 6
	ang = math.degrees(math.atan2(0.4, 1.9))
	for k in range(stripes):
		x = -1.45 + (k + 0.5) * 2.9 / stripes
		p.box((2.9 / stripes, 2.1, 0.06), (x, 0, 2.22), CLOTH_RED if k % 2 == 0 else CLOTH_WHITE, rot=(-ang, 0, 0), grad=(0.1, 0.5))
	for k in range(7):  # goods on the counter
		sw = (LEAF, GOLD, CLOTH_RED, EMBER)[k % 4]
		p.blob((0.28, 0.28, 0.24), (-1.1 + k * 0.36, -0.55 + p.rng.uniform(-0.15, 0.15), 1.08), sw, grad=(0.1, 0.6))
	return p.build()


def well():
	p = Prop("well", 43)
	for k in range(10):
		a = k * math.tau / 10
		p.box((0.75, 0.35, 0.9), (math.cos(a) * 1.05, math.sin(a) * 1.05, 0.45), STONE_LIGHT,
			  rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.8), jitter=0.02)
	p.seg((0, 0, 0.3), (0, 0, 0.62), 0.95, 0.95, WATER, sides=10, grad=(0.2, 0.5))
	for s in (-1, 1):
		p.seg((s * 1.15, 0, 0), (s * 1.15, 0, 2.3), 0.09, 0.08, WOOD, sides=5)
	p.seg((-1.25, 0, 1.75), (1.25, 0, 1.75), 0.06, 0.06, WOOD_GRAY, sides=5)
	p.seg((0, 0, 1.75), (0, 0, 1.1), 0.015, 0.015, WOOD_GRAY, sides=3)
	p.seg((0, 0, 1.1), (0, 0, 0.8), 0.16, 0.14, WOOD, sides=6)
	p.box((3.0, 1.2, 0.08), (0, -0.5, 2.55), CLAY, rot=(-35, 0, 0))
	p.box((3.0, 1.2, 0.08), (0, 0.5, 2.55), CLAY, rot=(35, 0, 0))
	return p.build()


def tavern():
	"""The Ember and Anvil: Emberhold's inn, and the largest building in the city.

	Stone ground floor, a jettied timber-framed upper storey, a steep shingled
	roof with a cross-gable over the door, and a wrought bracket carrying the
	sign. Twice the footprint of a house and better than twice its height, so it
	reads as the landmark on the plaza rather than one more cottage.

	Built facing -Y, which export_yup turns into +Z in game - the same front the
	houses use, so a landmark "face" aims the door wherever you point it.
	"""
	p = Prop("tavern", 71)
	w, d = 15.0, 11.0
	hw, hd = w / 2, d / 2
	jut = 0.6                      # how far the upper storey oversails the stone
	uhw, uhd = hw + jut, hd + jut
	upper_top = 7.7

	# --- stone ground floor: KayKit walls, pillars and windows, joined after
	# build() below (same pieces as the houses, so the stone matches) ---------
	# a plinth course under them, so the taller walls sit on something
	p.box((w + 1.2, d + 1.2, 0.35), (0, 0, 0.17), STONE_DARK, grad=(0.3, 1.0))

	# --- jettied upper storey -------------------------------------------------
	p.box((w + jut * 2, d + jut * 2, 3.2), (0, 0, 6.1), BONE, grad=(0.25, 0.7))  # plaster, weathered: not stark white
	for x in (-5.6, -2.8, 0.0, 2.8, 5.6):   # brackets carrying the oversail
		p.box((0.36, 1.0, 0.95), (x, -(hd + 0.3), 4.2), WOOD, rot=(34, 0, 0), grad=(0.3, 1.0))

	# --- timber frame ---------------------------------------------------------
	for y in (-uhd, uhd):          # sill and top plate, front and back
		p.box((uhw * 2 + 0.12, 0.34, 0.34), (0, y, 4.62), WOOD, grad=(0.25, 0.95))
		p.box((uhw * 2 + 0.12, 0.34, 0.34), (0, y, 7.52), WOOD, grad=(0.25, 0.95))
	for x in (-uhw, uhw):          # and along the sides
		p.box((0.34, uhd * 2, 0.34), (x, 0, 4.62), WOOD, grad=(0.25, 0.95))
		p.box((0.34, uhd * 2, 0.34), (x, 0, 7.52), WOOD, grad=(0.25, 0.95))
	for x in (-uhw, uhw):          # corner posts
		for y in (-uhd, uhd):
			p.box((0.42, 0.42, 3.3), (x, y, 6.07), WOOD, grad=(0.2, 0.9))
	# Studs sit clear of the porch roof, which sweeps out to about x = 2.8.
	for x in (-5.45, -3.0, 3.0, 5.45):      # studs divide the facade into window bays
		for y in (-uhd, uhd):
			p.box((0.3, 0.26, 2.7), (x, y, 6.07), WOOD, grad=(0.3, 1.0))
	for y in (-4.0, 4.0):          # studs on the side walls, clear of their windows
		for x in (-uhw, uhw):
			p.box((0.26, 0.3, 2.7), (x, y, 6.07), WOOD, grad=(0.3, 1.0))

	# --- porch bay and its cross-gable ----------------------------------------
	bay_y = -(uhd + 1.25)
	bay_face = -(uhd + 2.45)
	p.box((5.2, 2.5, 3.3), (0, bay_y, 6.05), BONE, grad=(0.25, 0.7))
	# (the porch bay's stone walls are KayKit pieces too, added after build)
	for x in (-2.6, 2.6):          # bay corner posts
		p.box((0.4, 0.4, 3.4), (x, bay_y, 6.05), WOOD, grad=(0.2, 0.9))
	bay_h, bay_half = 2.0, 2.75
	bay_slope = math.hypot(bay_half, bay_h)
	bay_ang = math.atan2(bay_h, bay_half)
	# The bay roof runs from just past the gable back until its ridge meets the
	# main roof's slope, so the two roofs join (it starts at the ridge and
	# slopes down to the eaves either side).
	main_rise = 3.9 / (uhd + 0.75)          # the main roof's rise per meter, from its eaves
	bay_front = -(uhd + 2.45) - 0.25
	bay_back = -((upper_top + 3.9) - (7.75 + bay_h)) / main_rise - 0.3
	bay_len = bay_back - bay_front
	bay_mid = (bay_front + bay_back) / 2
	for s in (1, -1):              # bay roof slopes toward +/-X
		down = Vector((math.cos(bay_ang) * s, 0, -math.sin(bay_ang)))
		out = Vector((math.sin(bay_ang) * s, 0, math.cos(bay_ang)))
		base = Vector((0, bay_mid, 7.75 + bay_h))
		p.box((bay_slope + 0.3, bay_len, 0.16), base + down * (bay_slope + 0.3) / 2, WOOD_GRAY,
			  rot=(0, math.degrees(bay_ang) * s, 0), grad=(0.2, 0.8))
		for i in range(4):
			c = base + down * (bay_slope + 0.3) * (i + 0.55) / 4 + out * 0.13
			p.box(((bay_slope + 0.3) / 4 * 1.15, bay_len + 0.1, 0.12), c, CLAY,
				  rot=(0, math.degrees(bay_ang) * s, 0), grad=(0.0, 0.9))
	p.seg((0, bay_front, 7.75 + bay_h + 0.12), (0, bay_back, 7.75 + bay_h + 0.12), 0.14, 0.14, WOOD, sides=6)  # ridge beam
	for y, t in ((bay_face, 0.16),):   # front gable only: the main roof closes the back
		tri = [(-bay_half, 7.75), (bay_half, 7.75), (0, 7.75 + bay_h)]
		verts = [(x, y - t / 2, z) for x, z in tri] + [(x, y + t / 2, z) for x, z in tri]
		p.poly(verts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], BONE, grad=(0.02, 0.5))
	for s in (-1, 1):              # timber edging on the bay gable
		p.seg((s * bay_half, bay_face, 7.75), (0, bay_face, 7.75 + bay_h), 0.13, 0.13, WOOD, sides=4)
	p.box((bay_half * 2 + 0.4, 0.3, 0.3), (0, bay_face, 7.72), WOOD, grad=(0.25, 0.95))

	# --- main roof: ridge along X, framed gables at the ends -------------------
	ridge_h, span = 3.9, uhd + 0.75
	slope = math.hypot(span, ridge_h)
	ang = math.atan2(ridge_h, span)
	ridge_z = upper_top + ridge_h
	for s in (1, -1):              # slopes toward +/-Y
		down = Vector((0, math.cos(ang) * s, -math.sin(ang)))
		out = Vector((0, math.sin(ang) * s, math.cos(ang)))
		base = Vector((0, 0, ridge_z))
		p.box((w + 2.0, slope, 0.18), base + down * slope / 2, WOOD_GRAY,
			  rot=(-math.degrees(ang) * s, 0, 0), grad=(0.2, 0.8))
		for i in range(7):         # shingle courses, each its own gradient
			c = base + down * slope * (i + 0.55) / 7 + out * 0.14
			p.box((w + 2.1, slope / 7 * 1.14, 0.13), c, CLAY,
				  rot=(-math.degrees(ang) * s, 0, 0), grad=(0.0, 0.9))
	for x in (-(hw + 0.62), hw + 0.62):     # gable ends, framed and infilled
		t = 0.3
		tri = [(-span, upper_top), (span, upper_top), (0, ridge_z)]
		verts = [(x - t / 2, y, z) for y, z in tri] + [(x + t / 2, y, z) for y, z in tri]
		p.poly(verts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], BONE, grad=(0.02, 0.5))
		for s in (-1, 1):
			p.seg((x, s * span, upper_top), (x, 0, ridge_z), 0.15, 0.15, WOOD, sides=4)
		p.seg((x, 0, upper_top + 0.2), (x, 0, ridge_z - 0.3), 0.12, 0.12, WOOD, sides=4)
	p.seg((-hw - 1.05, 0, ridge_z + 0.13), (hw + 1.05, 0, ridge_z + 0.13), 0.17, 0.17, WOOD, sides=6)
	# Soffit and fascia close the eaves. The wall stops at 7.7 and the roof
	# starts there too, which left a slot you could see the attic through.
	for s in (-1, 1):
		p.box((w + 2.0, span - uhd + 0.1, 0.18), (0, s * (uhd + (span - uhd) / 2), upper_top - 0.02),
			  WOOD_GRAY, grad=(0.25, 0.85))
		p.box((w + 2.05, 0.2, 0.42), (0, s * (span + 0.05), upper_top + 0.06), WOOD, grad=(0.25, 0.95))

	# --- chimneys: the tall one is the kitchen hearth --------------------------
	p.box((2.0, 2.2, 11.4), (hw - 0.9, 2.6, 5.7), STONE_DARK, grad=(0.12, 0.88))
	p.box((2.4, 2.6, 0.45), (hw - 0.9, 2.6, 11.5), STONE_LIGHT, grad=(0.2, 0.7))
	p.box((1.3, 1.4, 9.6), (-hw + 1.0, -2.4, 4.8), STONE_DARK, grad=(0.12, 0.88))
	p.box((1.6, 1.7, 0.36), (-hw + 1.0, -2.4, 9.7), STONE_LIGHT, grad=(0.2, 0.7))

	# --- door, steps and lanterns ---------------------------------------------
	sill = 0.36                    # doors start at the porch deck, not at the grass
	p.box((3.9, 0.5, 4.2), (0, bay_face + 0.12, sill + 1.98), STONE_DARK, grad=(0.18, 0.9))
	for s in (-1, 1):              # double doors, banded
		p.box((1.25, 0.26, 2.7), (s * 0.68, bay_face - 0.06, sill + 1.35), WOOD, grad=(0.45, 1.0))
		for z in (0.7, 2.0):
			p.box((1.3, 0.2, 0.16), (s * 0.68, bay_face - 0.14, sill + z), IRON, grad=(0.2, 0.7))
		# Pull handles, on the meeting edges where you would actually grab them.
		p.seg((s * 0.26, bay_face - 0.28, sill + 0.95), (s * 0.26, bay_face - 0.28, sill + 1.75),
			  0.045, 0.045, IRON, sides=5, grad=(0.1, 0.6))
		for z in (1.0, 1.7):
			p.box((0.1, 0.26, 0.09), (s * 0.26, bay_face - 0.18, sill + z), IRON, grad=(0.15, 0.65))
	# Voussoirs shoulder to shoulder on a true semicircle, springing just above
	# the doors and sized to them, so it reads as an arch and not as rubble.
	arch_r, arch_z = 1.32, sill + 2.72
	for k in range(11):
		a = math.radians(180.0 * k / 10.0)
		p.box((0.46, 0.46, 0.54), (math.cos(a) * arch_r, bay_face + 0.04, arch_z + math.sin(a) * arch_r),
			  STONE_LIGHT, rot=(0, 90.0 - math.degrees(a), 0), grad=(0.15, 0.8))
	p.box((0.44, 0.5, 0.52), (0, bay_face + 0.02, arch_z + arch_r), STONE_DARK, grad=(0.1, 0.7))

	# --- porch deck: walkable, with a ramp up to it ---------------------------
	deck_back, deck_front = bay_face, bay_face - 2.4
	p.box((5.0, 2.4, sill), (0, (deck_back + deck_front) / 2, sill / 2), STONE_LIGHT, grad=(0.25, 0.9))
	for s in (-1, 1):              # kerbs down the sides, so the ramp is the way up
		p.box((0.44, 2.4, 0.52), (s * 2.28, (deck_back + deck_front) / 2, 0.26), STONE_DARK, grad=(0.25, 0.95))
	ry1, ry0, rw = deck_front, deck_front - 1.7, 1.75
	p.poly([(-rw, ry0, 0.0), (rw, ry0, 0.0), (rw, ry1, sill), (-rw, ry1, sill),
			(-rw, ry1, 0.0), (rw, ry1, 0.0)],
		   [(0, 1, 2, 3), (0, 4, 5, 1), (3, 2, 5, 4), (0, 3, 4), (1, 5, 2)],
		   STONE_DARK, grad=(0.3, 1.0))
	for s in (-1, 1):              # lanterns either side of the door
		p.seg((s * 2.3, bay_face + 0.1, 3.5), (s * 2.3, bay_face - 0.5, 3.5), 0.06, 0.05, IRON, sides=4)
		p.box((0.34, 0.34, 0.44), (s * 2.3, bay_face - 0.52, 3.25), EMBER, glow=3.2, grad=(0.1, 0.4))
		p.box((0.4, 0.4, 0.1), (s * 2.3, bay_face - 0.52, 3.5), IRON, grad=(0.2, 0.6))

	# --- windows: lit, because a tavern is where the light is ------------------
	def window(loc, size, glow):
		# The thinnest axis is the one through the wall. Grow the frame in the
		# other two and pull it back in that one, so the lit pane stands proud
		# of its frame instead of being swallowed by it.
		thin = min(range(3), key=lambda i: size[i])
		frame = tuple(size[i] + (-0.14 if i == thin else 0.34) for i in range(3))
		p.box(frame, loc, WOOD, grad=(0.3, 1.0))
		p.box(size, loc, EMBER, glow=glow, grad=(0.08, 0.38))
		# a cross of mullions in front of the glass, so it reads as panes
		out = [0.0, 0.0, 0.0]
		out[thin] = -0.2 if loc[thin] <= 0 else 0.2
		face = tuple(loc[i] + out[i] for i in range(3))
		bar_v = [0.1, 0.1, 0.1]
		bar_v[2] = size[2]
		bar_h = [size[i] if i != 2 and i != thin else 0.1 for i in range(3)]
		p.box(tuple(bar_v), face, WOOD, grad=(0.3, 1.0))
		p.box(tuple(bar_h), face, WOOD, grad=(0.3, 1.0))
	for x in (-6.7, -4.2, 4.2, 6.7):        # upper storey, centred in each bay
		window((x, -uhd - 0.06, 6.15), (1.2, 0.3, 1.35), 2.0)
	# One window under the porch gable, on the centreline. A pair either side of
	# it would sit where the gable roof sweeps down past z = 6.3 and the roof
	# would cut straight through the glass; only the middle is tall enough.
	window((0.0, bay_face - 0.04, 5.9), (1.3, 0.3, 1.5), 2.2)
	for y in (-2.6, 1.4):                   # side walls, upper storey
		window((-uhw - 0.06, y, 6.15), (0.3, 1.1, 1.3), 1.8)

	# a capstone ledge where the stone storey meets the jetty
	p.box((w + 0.9, d + 0.9, 0.36), (0, 0, 4.5), STONE_DARK, grad=(0.1, 0.7))

	# --- the sign, on a wrought bracket ---------------------------------------
	sx = hw - 2.2
	p.seg((sx, -hd - 0.05, 5.3), (sx, -hd - 2.5, 5.3), 0.09, 0.08, IRON, sides=5)
	p.seg((sx, -hd - 0.08, 6.45), (sx, -hd - 2.05, 5.38), 0.06, 0.05, IRON, sides=4)
	for y in (-hd - 1.0, -hd - 2.25):
		p.seg((sx, y, 5.26), (sx, y, 4.82), 0.035, 0.035, IRON, sides=4)
	p.box((0.18, 2.0, 1.5), (sx, -hd - 1.62, 4.05), WOOD, grad=(0.3, 1.0))
	for z in (4.83, 3.27):
		p.box((0.1, 2.16, 0.14), (sx, -hd - 1.62, z), IRON, grad=(0.2, 0.7))
	for s in (-1, 1):              # a foaming tankard, painted on both faces
		mx = sx + s * 0.11
		p.box((0.12, 0.52, 0.62), (mx, -hd - 1.72, 3.93), GOLD, grad=(0.1, 0.65))       # the ale
		p.box((0.11, 0.58, 0.07), (mx, -hd - 1.72, 3.6), WOOD, grad=(0.3, 0.9))         # base
		p.blob((0.13, 0.56, 0.26), (mx, -hd - 1.72, 4.29), CLOTH_WHITE, grad=(0.0, 0.35))  # head
		p.blob((0.1, 0.16, 0.14), (mx, -hd - 1.95, 4.42), CLOTH_WHITE, grad=(0.0, 0.3))    # a run of froth
		for y, z, h in ((-hd - 1.36, 4.12, 0.14), (-hd - 1.3, 3.93, 0.34), (-hd - 1.36, 3.74, 0.14)):
			p.box((0.1, 0.16 if h < 0.2 else 0.1, h), (mx, y, z), GOLD, grad=(0.15, 0.7))   # handle

	# --- the yard: barrels, a bench, a trough ----------------------------------
	for x, y, r in ((-5.4, -hd - 1.0, 0.44), (-4.4, -hd - 1.7, 0.4), (6.0, -hd - 1.2, 0.46)):
		p.seg((x, y, 0), (x, y, 0.95 if r > 0.42 else 0.85), r, r * 0.93, WOOD, sides=8, grad=(0.25, 1.0))
		p.seg((x, y, 0.3), (x, y, 0.42), r + 0.03, r + 0.03, IRON, sides=8, grad=(0.2, 0.7))
	p.box((3.0, 0.55, 0.2), (4.0, -hd - 1.9, 0.62), WOOD, grad=(0.3, 1.0))
	for x in (2.8, 5.2):
		p.box((0.24, 0.5, 0.62), (x, -hd - 1.9, 0.31), WOOD, grad=(0.35, 1.0))
	p.box((2.4, 0.9, 0.62), (-6.6, -hd - 2.4, 0.31), STONE_LIGHT, grad=(0.2, 0.9))
	p.box((2.0, 0.6, 0.2), (-6.6, -hd - 2.4, 0.5), WATER, grad=(0.25, 0.55))
	# Light behind every KayKit window: a glowing pane inside the wall, seen
	# only through the opening. Laid in the Prop before building so it bevels
	# and joins with the rest.
	sx_side = 11.0 / 4 / 4.0                 # side walls: four pieces across 11 m
	win_z = 2.35
	front = {-6.0: "wall_window_open", -3.0: "wall", 0.0: "wall", 3.0: "wall", 6.0: "wall_window_open"}
	back = {-6.0: "wall", -3.0: "wall_window_closed", 0.0: "wall", 3.0: "wall_window_closed", 6.0: "wall"}
	left = {-4.125: "wall", -1.375: "wall_window_open", 1.375: "wall_window_open", 4.125: "wall"}
	right = {-4.125: "wall_window_open", -1.375: "wall_window_open", 1.375: "wall", 4.125: "wall"}
	for x, piece in front.items():
		if piece == "wall_window_open":
			p.box((2.0, 0.08, 2.2), (x, -hd + 0.375, win_z), EMBER, glow=2.2, grad=(0.08, 0.38))
	for side, walls in ((-1, left), (1, right)):
		for y, piece in walls.items():
			if piece == "wall_window_open":
				p.box((0.08, 1.9, 2.2), (side * (hw - 0.375), y, win_z), EMBER, glow=2.0, grad=(0.08, 0.38))
	obj = p.build(bevel=0.06)
	tall = 4.4 / 4.0                         # the stone storey is 4.4 m; KayKit walls are 4
	pieces = []
	for x, piece in front.items():
		pieces += kaykit(piece, (x, -hd + 0.375, 0), 0.0, (0.75, 0.75, tall))
	for x, piece in back.items():
		pieces += kaykit(piece, (x, hd - 0.375, 0), math.pi, (0.75, 0.75, tall))
	for side, walls in ((-1, left), (1, right)):
		for y, piece in walls.items():
			pieces += kaykit(piece, (side * (hw - 0.375), y, 0), math.pi / 2 * -side, (sx_side, 0.75, tall))
	for x in (-hw, hw):
		for y in (-hd, hd):
			pieces += kaykit("pillar", (x, y, 0), 0.0, (0.75, 0.75, tall))
	# the porch bay: side walls from the facade out to the door, and a half
	# wall either side of the arch (the door frame covers the rest)
	bay_face = -(uhd + 2.45)
	run = bay_face + hd                    # negative: from the facade out to the porch front
	for sx in (-1, 1):
		pieces += kaykit("wall", (sx * 2.325, -hd + run / 2, 0), math.pi / 2, (abs(run) / 4.0, 0.75, tall))
		pieces += kaykit("wall_half", (sx * 2.7, bay_face + 0.375, 0), 0.0 if sx < 0 else math.pi, (1.38 / 2.0, 0.75, tall))
		pieces += kaykit("pillar", (sx * 2.7, bay_face + 0.2, 0), 0.0, (0.6, 0.6, tall))
	return join_into(obj, pieces)


def tavern_bar():
	"""The counter inside the Ember and Anvil: plank front, a worn top with a
	footrail, and shelves of bottles and mugs behind it.

	Front faces -Y, which is +Z in game, so it looks out at whoever is buying.
	"""
	p = Prop("tavern_bar", 83)
	w = 6.0
	hw = w / 2

	# --- the counter ----------------------------------------------------------
	p.box((w, 0.85, 1.02), (0, 0, 0.51), WOOD, grad=(0.3, 1.0))
	for k in range(9):             # plank lines down the front
		p.box((0.1, 0.1, 0.94), (-hw + 0.34 + k * 0.66, -0.46, 0.52), WOOD_GRAY, grad=(0.35, 1.0))
	p.box((w + 0.5, 1.16, 0.17), (0, -0.14, 1.09), WOOD_GRAY, grad=(0.12, 0.62))
	p.box((w + 0.5, 0.1, 0.1), (0, -0.7, 1.02), WOOD, grad=(0.25, 0.9))
	p.seg((-hw + 0.3, -0.52, 0.24), (hw - 0.3, -0.52, 0.24), 0.055, 0.055, IRON, sides=5, grad=(0.15, 0.6))
	for s in (-1, 1):              # footrail brackets
		p.box((0.12, 0.12, 0.3), (s * (hw - 0.45), -0.5, 0.14), IRON, grad=(0.15, 0.6))

	# --- what is standing on it -----------------------------------------------
	p.seg((hw - 0.75, 0.05, 1.18), (hw - 0.75, 0.05, 1.72), 0.3, 0.27, WOOD, sides=8, grad=(0.25, 1.0))
	p.seg((hw - 0.75, 0.05, 1.34), (hw - 0.75, 0.05, 1.46), 0.33, 0.33, IRON, sides=8, grad=(0.2, 0.7))
	p.seg((hw - 0.75, -0.3, 1.42), (hw - 0.75, -0.44, 1.42), 0.05, 0.04, IRON, sides=5)   # tap
	for k in range(4):             # mugs waiting to be filled
		p.seg((-hw + 0.7 + k * 0.5, -0.1, 1.18), (-hw + 0.7 + k * 0.5, -0.1, 1.42), 0.11, 0.1, GOLD, sides=6, grad=(0.15, 0.7))
	p.box((0.5, 0.36, 0.1), (0.6, -0.12, 1.23), WOOD_GRAY, grad=(0.2, 0.8))               # a board of cheese
	p.blob((0.3, 0.26, 0.16), (0.6, -0.12, 1.33), CLAY, grad=(0.1, 0.6))

	# --- the back shelves -----------------------------------------------------
	p.box((w, 0.32, 2.5), (0, 1.78, 1.25), WOOD, grad=(0.22, 0.95))
	# A duckboard for whoever is working: without it the counter hides them.
	p.box((w - 0.5, 1.1, 0.26), (0, 1.02, 0.13), WOOD_GRAY, grad=(0.3, 1.0))
	for z in (0.88, 1.56, 2.2):
		p.box((w - 0.3, 0.56, 0.11), (0, 1.53, z), WOOD_GRAY, grad=(0.18, 0.8))
		for k in range(11):        # bottles, jars and tankards
			x = -hw + 0.4 + k * 0.52 + p.rng.uniform(-0.05, 0.05)
			sw = (LEAF, WATER, GOLD, CLAY, BONE)[(k + int(z * 3)) % 5]
			h = p.rng.uniform(0.2, 0.34)
			p.seg((x, 1.53, z + 0.06), (x, 1.53, z + 0.06 + h), 0.075, 0.06, sw, sides=6, grad=(0.1, 0.65))
			if h > 0.3:
				p.seg((x, 1.53, z + 0.06 + h), (x, 1.53, z + 0.14 + h), 0.03, 0.03, sw, sides=5, grad=(0.1, 0.5))
	p.box((w + 0.3, 0.5, 0.16), (0, 1.63, 2.62), WOOD, grad=(0.2, 0.9))

	# --- barrels stacked at the ends ------------------------------------------
	for s in (-1, 1):
		p.seg((s * (hw + 0.55), 1.55, 0.0), (s * (hw + 0.55), 1.55, 0.92), 0.44, 0.41, WOOD, sides=8, grad=(0.25, 1.0))
		p.seg((s * (hw + 0.55), 1.55, 0.28), (s * (hw + 0.55), 1.55, 0.4), 0.47, 0.47, IRON, sides=8, grad=(0.2, 0.7))
		p.seg((s * (hw + 0.55), 1.55, 0.62), (s * (hw + 0.55), 1.55, 0.74), 0.47, 0.47, IRON, sides=8, grad=(0.2, 0.7))
	return p.build()


def signpost():
	"""Two arrow boards; the game writes the destinations on them."""
	p = Prop("signpost", 45)
	p.seg((0, 0, -0.3), (0, 0, 2.7), 0.1, 0.09, WOOD, sides=6, grad=(0.2, 1.0))
	p.box((2.1, 0.08, 0.34), (0.9, -0.06, 2.25), WOOD_GRAY, grad=(0.1, 0.6))  # room for a long place name
	p.seg((1.95, -0.06, 2.25), (2.2, -0.06, 2.25), 0.2, 0.0, WOOD_GRAY, sides=4, twist=45)
	p.box((2.0, 0.08, 0.32), (-0.85, 0.06, 1.75), WOOD_GRAY, grad=(0.1, 0.6))
	p.seg((-1.85, 0.06, 1.75), (-2.1, 0.06, 1.75), 0.19, 0.0, WOOD_GRAY, sides=4, twist=45)
	return p.build()


# ---------------------------------------------------------------- ground clutter
# Scattered by the thousand (zone.gd, MultiMesh) and never collide. Grass uses the
# neutral SHADE swatch so the game can tint each tuft to the ground beneath it.

def grass(name, seed, blades, height):
	p = Prop(name, seed)
	for k in range(blades):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.22)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = height * p.rng.uniform(0.6, 1.1)
		lean = p.rng.uniform(0.05, 0.22)
		la = p.rng.uniform(0, math.tau)
		w = p.rng.uniform(0.035, 0.06)
		side = (math.cos(a + 1.57) * w, math.sin(a + 1.57) * w)
		p.poly([(x - side[0], y - side[1], 0), (x + side[0], y + side[1], 0),
				(x + math.cos(la) * lean, y + math.sin(la) * lean, h)], [(0, 1, 2)], SHADE, grad=(0.0, 0.62))
	return p.build()


def flowers(name, seed, petal):
	p = Prop(name, seed)
	for k in range(5):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.3)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(0.18, 0.34)
		p.seg((x, y, 0), (x, y, h), 0.012, 0.01, LEAF, sides=3, grad=(0.3, 0.8))
		p.blob((0.1, 0.1, 0.05), (x, y, h), petal, segs=(5, 3), grad=(0.0, 0.3))
		p.blob((0.035, 0.035, 0.03), (x, y, h + 0.02), EMBER, segs=(4, 3))
	for k in range(4):  # a few leaves at the base
		a = k * 1.6
		p.poly([(0, 0, 0), (math.cos(a) * 0.18, math.sin(a) * 0.18, 0.06), (math.cos(a + 0.4) * 0.12, math.sin(a + 0.4) * 0.12, 0.1)],
			   [(0, 1, 2)], LEAF, grad=(0.3, 0.7))
	return p.build()


def fern():
	p = Prop("fern", 51)
	for k in range(7):
		a = k * math.tau / 7 + p.rng.uniform(-0.2, 0.2)
		length = p.rng.uniform(0.45, 0.65)
		d = Vector((math.cos(a), math.sin(a), 0))
		n = Vector((-math.sin(a), math.cos(a), 0))
		tip = d * length + Vector((0, 0, 0.35))
		mid = d * length * 0.5 + Vector((0, 0, 0.42))
		p.poly([(0, 0, 0.02), tuple(mid + n * 0.1), tuple(tip), tuple(mid - n * 0.1)], [(0, 1, 2, 3)], PINE, grad=(0.1, 0.7))
	return p.build()


def bush(name, seed, lobes):
	p = Prop(name, seed)
	for k in range(lobes):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.45)
		s = p.rng.uniform(0.6, 0.95)
		p.rock((s, s, s * 0.8), (math.cos(a) * r, math.sin(a) * r, s * 0.35), LEAF, grad=(0.1, 0.85), jitter=0.06)
	for k in range(3):
		p.blob((0.08, 0.08, 0.08), (p.rng.uniform(-0.4, 0.4), p.rng.uniform(-0.4, 0.4), p.rng.uniform(0.5, 0.75)), CLOTH_RED, segs=(4, 3))
	return p.build()


def mushrooms():
	p = Prop("mushrooms", 53)
	for k in range(4):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.22)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(0.1, 0.22)
		p.seg((x, y, 0), (x, y, h), 0.035, 0.03, BONE, sides=5, grad=(0.0, 0.5))
		p.blob((0.16 * h / 0.2, 0.16 * h / 0.2, 0.09), (x, y, h), MUSHROOM, segs=(6, 4), grad=(0.0, 0.5))
		for d in range(2):
			p.blob((0.02, 0.02, 0.01), (x + p.rng.uniform(-0.04, 0.04), y + p.rng.uniform(-0.04, 0.04), h + 0.04), PETAL_WHITE, segs=(3, 2))
	return p.build()


def pebbles():
	p = Prop("pebbles", 55)
	for k in range(5):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.4)
		s = p.rng.uniform(0.12, 0.3)
		p.rock((s, s * 0.9, s * 0.6), (math.cos(a) * r, math.sin(a) * r, s * 0.15), STONE_DARK, jitter=0.1)
	return p.build()


def log_fallen():
	p = Prop("log_fallen", 57)
	p.seg((-1.6, 0, 0.3), (1.6, 0.1, 0.26), 0.32, 0.27, WOOD, sides=7, grad=(0.1, 1.0))
	p.seg((1.6, 0.1, 0.26), (1.66, 0.1, 0.26), 0.25, 0.25, HIDE, sides=7)            # cut end
	p.seg((0.2, 0, 0.5), (0.5, -0.35, 0.95), 0.07, 0.03, WOOD, sides=4)               # broken branch
	for k in range(3):
		p.blob((0.3, 0.2, 0.08), (p.rng.uniform(-1.2, 1.0), 0.05, 0.58), LEAF, grad=(0.2, 0.6))  # moss
	return p.build()


def stump():
	p = Prop("stump", 59)
	p.seg((0, 0, -0.1), (0, 0, 0.45), 0.36, 0.3, WOOD, sides=7, grad=(0.2, 1.0))
	p.seg((0, 0, 0.45), (0, 0, 0.47), 0.29, 0.29, HIDE, sides=7)
	for k in range(4):
		a = k * math.tau / 4 + 0.4
		p.seg((0, 0, 0.1), (math.cos(a) * 0.55, math.sin(a) * 0.55, -0.05), 0.1, 0.05, WOOD, sides=4)
	p.blob((0.12, 0.12, 0.06), (0.25, 0.1, 0.3), MUSHROOM, segs=(5, 3))
	return p.build()


# ---------------------------------------------------------------- pond

def dock():
	"""Plank pier on posts: the back edge sits on the bank at the origin and the
	deck runs 7.5 m out over the water (-Y). Posts reach 2 m below the bank."""
	p = Prop("dock", 71)
	deck = 0.35
	length, width = 7.5, 1.8
	for x in (-0.6, 0.6):  # stringers under the planks
		p.box((0.14, length, 0.16), (x, -length / 2 + 0.2, deck - 0.14), WOOD, grad=(0.3, 1.0))
	n = 26
	for k in range(n):
		y = 0.2 - (k + 0.5) * length / n
		sw = WOOD_GRAY if p.rng.random() < 0.3 else WOOD
		p.box((width + p.rng.uniform(-0.1, 0.1), length / n - 0.035, 0.07), (p.rng.uniform(-0.04, 0.04), y, deck - 0.035),
			  sw, rot=(0, 0, p.rng.uniform(-1.5, 1.5)), grad=(0.1, 0.6))
	for y in (-0.3, -2.8, -5.3, -7.1):
		for x in (-0.82, 0.82):
			top = deck + (0.55 if y < -7 else 0.02)  # the far pair stands up as mooring posts
			p.seg((x, y, -2.0), (x, y, top), 0.1, 0.09, WOOD, sides=6, grad=(0.2, 1.0))
	p.seg((0.82, -7.1, deck + 0.3), (0.82, -7.1, deck + 0.42), 0.13, 0.13, HIDE, sides=6)  # rope coil
	return p.build()


def reeds():
	"""Cattails for the pond's edge: tall blades and a few brown heads."""
	p = Prop("reeds", 73)
	for k in range(10):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.35)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(0.9, 1.5)
		la = p.rng.uniform(0, math.tau)
		lean = p.rng.uniform(0.05, 0.25)
		w = 0.04
		p.poly([(x - w, y, 0), (x + w, y, 0), (x + math.cos(la) * lean, y + math.sin(la) * lean, h)], [(0, 1, 2)],
			   PINE, grad=(0.1, 0.8))
	for k in range(4):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.25)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(1.1, 1.6)
		p.seg((x, y, 0), (x, y, h), 0.012, 0.01, LEAF, sides=3)
		p.seg((x, y, h - 0.3), (x, y, h - 0.05), 0.035, 0.035, WOOD, sides=5, grad=(0.3, 0.9))
	return p.build()


def lily_pads():
	p = Prop("lily_pads", 75)
	for k in range(4):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.6)
		s = p.rng.uniform(0.35, 0.6)
		p.seg((math.cos(a) * r, math.sin(a) * r, 0), (math.cos(a) * r, math.sin(a) * r, 0.02), s, s, LEAF,
					sides=9, grad=(0.2, 0.5))
	p.blob((0.16, 0.16, 0.1), (0, 0, 0.06), PETAL_WHITE, segs=(6, 3), grad=(0.0, 0.3))
	p.blob((0.06, 0.06, 0.05), (0, 0, 0.1), PETAL_YELLOW, segs=(4, 3))
	return p.build()


def fishing_pole():
	"""Held item: authored like a KayKit weapon (grip at the origin, pointing
	up +Z) in KayKit character units, which the game shows at 0.75 scale.
	A jointed bamboo rod with a cork grip, a wooden reel, line guides and a
	short length of line off the tip toward +X (down, in the hand) with a
	red-and-white float."""
	p = Prop("fishing_pole", 77)
	p.seg((0, 0, -0.35), (0, 0, 0.3), 0.045, 0.042, HIDE, sides=6, grad=(0.2, 0.9))  # cork grip
	p.seg((0, 0, -0.38), (0, 0, -0.33), 0.052, 0.052, WOOD, sides=6)  # butt cap
	joints = [0.3, 0.85, 1.4, 1.95, 2.45, 2.9]
	for i, (a, b) in enumerate(zip(joints, joints[1:])):  # bamboo, a node at every joint
		ra = 0.032 - i * 0.005
		p.seg((0, 0, a), (0, 0, b), ra, ra - 0.004, (1, 3), sides=6, grad=(0.1, 0.8))
		p.seg((0, 0, a - 0.02), (0, 0, a + 0.02), ra + 0.007, ra + 0.007, (1, 3), sides=6, grad=(0.5, 0.9))
	p.seg((0, 0, 0.45), (0.07, 0, 0.45), 0.014, 0.014, WOOD, sides=4)  # the reel hangs under the rod
	p.seg((0.11, -0.035, 0.45), (0.11, 0.035, 0.45), 0.075, 0.075, WOOD, sides=10, grad=(0.2, 0.9))
	p.seg((0.11, -0.04, 0.45), (0.11, 0.04, 0.45), 0.03, 0.03, IRON, sides=6)
	p.seg((0.11, 0.035, 0.45), (0.16, 0.08, 0.45), 0.01, 0.01, IRON, sides=4)
	p.blob((0.03, 0.03, 0.03), (0.16, 0.09, 0.45), WOOD, segs=(5, 3))
	for z in (0.95, 1.5, 2.05, 2.55):  # line guides
		p.seg((0, 0, z), (0.045, 0, z), 0.01, 0.01, IRON, sides=4)
	_chain(p, [(0, 0, 2.9), (0.08, 0, 2.93), (0.25, 0, 2.93), (0.45, 0, 2.9)], 0.008, 0.008, CLOTH_WHITE, sides=3)  # line
	p.blob((0.05, 0.05, 0.05), (0.48, 0, 2.9), CLOTH_WHITE, segs=(6, 4))  # float
	p.blob((0.05, 0.05, 0.05), (0.53, 0, 2.9), CLOTH_RED, segs=(6, 4))
	p.seg((0.55, 0, 2.9), (0.62, 0, 2.9), 0.006, 0.006, IRON, sides=3)  # and hook
	return p.build()


def bridge_wood():
	"""A timber footbridge for a road over a river. Built along Y (the road runs
	along the prop's forward axis in game), origin at the middle of the span
	at bank height; the deck arches 1.3 m over 22 m, gentle enough to walk,
	with stone abutments at both ends, piers into the water and railings."""
	p = Prop("bridge_wood", 131)
	half_len, half_w, rise = 11.0, 2.1, 1.3

	def deck_z(y):
		return rise * (1.0 - (y / half_len) ** 2)

	n = 22
	for k in range(n):                                   # planks across the deck, following the arch
		y0 = -half_len + (k + 0.08) * 2 * half_len / n
		y1 = -half_len + (k + 0.92) * 2 * half_len / n
		ym = (y0 + y1) / 2
		tilt = math.degrees(math.atan2(deck_z(y1) - deck_z(y0), y1 - y0))
		sw = WOOD if k % 3 else WOOD_GRAY
		p.box((half_w * 2, y1 - y0, 0.16), (0, ym, deck_z(ym) - 0.08), sw, rot=(tilt, 0, 0), grad=(0.25, 0.9))
	for x in (-half_w + 0.25, half_w - 0.25):            # stringers under the planks
		prev = None
		for k in range(n + 1):
			y = -half_len + k * 2 * half_len / n
			pt = (x, y, deck_z(y) - 0.3)
			if prev:
				p.seg(prev, pt, 0.14, 0.14, WOOD_GRAY, sides=4)
			prev = pt
	for x in (-half_w, half_w):                          # railings: posts and a top rail
		prev = None
		for k in range(8):
			y = -half_len + 1.0 + k * (2 * half_len - 2.0) / 7
			base = (x, y, deck_z(y) - 0.1)
			top = (x, y, deck_z(y) + 1.0)
			p.box((0.18, 0.18, 1.1), (x, y, deck_z(y) + 0.45), WOOD, grad=(0.25, 1.0))
			if prev:
				p.seg(prev, top, 0.07, 0.07, WOOD, sides=5)
			prev = top
	for y in (-4.0, 4.0):                                # piers standing in the river
		for x in (-half_w + 0.3, half_w - 0.3):
			p.seg((x, y, deck_z(y) - 0.35), (x, y, -2.6), 0.16, 0.2, WOOD_GRAY, sides=6)
		p.box((half_w * 2, 0.22, 0.22), (0, y, deck_z(y) - 0.45), WOOD_GRAY, grad=(0.25, 0.9))
	for s in (-1, 1):                                    # stone abutments where it meets the banks
		y = s * (half_len - 0.6)
		p.box((half_w * 2 + 1.0, 1.6, 1.4), (0, y, -0.55), STONE_LIGHT, grad=(0.1, 0.8))
		p.box((half_w * 2 + 1.2, 0.5, 0.3), (0, s * (half_len - 1.3), 0.12), STONE_DARK, grad=(0.1, 0.8))
	return p.build(bevel=0.03)


def cobweb():
	"""A spider's web hung upright, 3.2 m across: spokes, a spiral, and anchor
	lines down to the ground so it doesn't float. Faces -Y."""
	p = Prop("cobweb", 141)
	c = Vector((0, 0, 1.9))
	spokes = 11
	ends = []
	for k in range(spokes):
		a = k * math.tau / spokes + p.rng.uniform(-0.1, 0.1)
		r = p.rng.uniform(1.3, 1.7)
		end = c + Vector((math.cos(a) * r, 0, math.sin(a) * r))
		ends.append((a, r))
		p.seg(c, end, 0.018, 0.012, CLOTH_WHITE, sides=3, grad=(0.0, 0.3))
	for turn in range(1, 7):                        # the spiral, spoke to spoke
		rr = turn * 0.22
		for k in range(spokes):
			a0, r0 = ends[k]
			a1, r1 = ends[(k + 1) % spokes]
			if rr > min(r0, r1):
				continue
			q0 = c + Vector((math.cos(a0) * rr, 0, math.sin(a0) * rr))
			q1 = c + Vector((math.cos(a1) * (rr + 0.03), 0, math.sin(a1) * (rr + 0.03)))
			p.seg(q0, q1, 0.012, 0.012, CLOTH_WHITE, sides=3, grad=(0.0, 0.3))
	for x in (-1.2, 1.3):                           # anchors to the ground
		p.seg(c + Vector((x * 0.9, 0, -0.9)), (x * 1.6, p.rng.uniform(-0.3, 0.3), 0.0), 0.015, 0.012, CLOTH_WHITE, sides=3)
	p.seg(c + Vector((0, 0, 1.4)), (0.4, 0.2, 3.9), 0.015, 0.012, CLOTH_WHITE, sides=3)   # and one up, to a branch
	return p.build()


def web_mound():
	"""A low tent of webbing over the ground, a nest's floor."""
	p = Prop("web_mound", 143)
	top = Vector((0, 0, 1.1))
	for k in range(14):
		a = k * math.tau / 14
		r = p.rng.uniform(1.6, 2.2)
		foot = Vector((math.cos(a) * r, math.sin(a) * r, 0.02))
		mid = top.lerp(foot, 0.5) + Vector((0, 0, 0.25))
		p.seg(top, mid, 0.02, 0.018, CLOTH_WHITE, sides=3)
		p.seg(mid, foot, 0.018, 0.015, CLOTH_WHITE, sides=3)
	p.blob((2.6, 2.6, 0.9), (0, 0, 0.3), CLOTH_WHITE, segs=(12, 6), grad=(0.0, 0.2))   # the gauzy sheet
	return p.build()


def egg_sacs():
	p = Prop("egg_sacs", 145)
	for k in range(7):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.55)
		size = p.rng.uniform(0.3, 0.46)
		p.blob((size, size, size * 1.2), (math.cos(a) * r, math.sin(a) * r, size * 0.55), CLOTH_WHITE, segs=(10, 7), grad=(0.0, 0.35))
	for k in range(6):                              # strands tying them down
		a = k * math.tau / 6
		p.seg((0, 0, 0.5), (math.cos(a) * 0.9, math.sin(a) * 0.9, 0.0), 0.012, 0.01, CLOTH_WHITE, sides=3)
	return p.build()


def drying_rack():
	"""Two posts and a pole with pelts hung over it: a hunter's camp. Faces -Y."""
	p = Prop("drying_rack", 147)
	for x in (-1.3, 1.3):
		p.seg((x, 0, 0), (x, 0, 1.9), 0.07, 0.06, WOOD, sides=6, grad=(0.2, 1.0))
		p.seg((x - 0.25, 0, 1.75), (x + 0.25, 0, 2.0), 0.05, 0.05, WOOD, sides=5)
	p.seg((-1.45, 0, 1.9), (1.45, 0, 1.9), 0.05, 0.05, WOOD_GRAY, sides=6)
	for x, sw, h in ((-0.75, WOOD_GRAY, 1.1), (0.0, HIDE, 1.3), (0.75, STONE_DARK, 1.0)):   # pelts, draped
		for s in (-1, 1):
			p.box((0.62, 0.05, h), (x, s * 0.05, 1.9 - h / 2), sw, rot=(s * 6, 0, 0), grad=(0.0, 0.6))
	return p.build(bevel=0.02)


def woodpile():
	p = Prop("woodpile", 149)
	for row, n in enumerate((5, 4, 3)):
		for k in range(n):
			x = (k - (n - 1) / 2) * 0.34
			p.seg((x, -0.9, 0.17 + row * 0.3), (x, 0.9, 0.17 + row * 0.3), 0.16, 0.16, WOOD, sides=7, grad=(0.3, 1.0))
			p.seg((x, -0.92, 0.17 + row * 0.3), (x, -0.9, 0.17 + row * 0.3), 0.13, 0.13, BONE, sides=7)   # cut ends
	p.box((0.12, 0.12, 0.9), (0.95, 0.5, 0.45), WOOD_GRAY, rot=(0, 0, 0))                                 # the axe handle
	p.box((0.25, 0.06, 0.18), (0.95, 0.5, 0.92), IRON)
	return p.build(bevel=0.02)


def cave_entrance():
	"""A cave mouth in a rocky hillside: the way into a dungeon. Built facing -Y
	(+Z in game) like the other buildings, so a landmark "face" aims the mouth.

	The tunnel is a lining seen from inside (an arch extruded 9 m back),
	darkening in steps to black, with mine timbers at the mouth. Rocks pile
	around it but never inside it, so the floor is walkable to the back wall,
	where a dungeon's zone line can go. Mouth: 4.4 m wide, 3.8 m high.
	"""
	p = Prop("cave_entrance", 97)
	half, wall_h, depth = 2.2, 1.6, 9.0

	def profile(steps=10):
		pts = [(-half, 0.0), (-half, wall_h)]
		for k in range(1, steps):
			a = math.pi - math.pi * k / steps
			pts.append((math.cos(a) * half, wall_h + math.sin(a) * half))
		pts += [(half, wall_h), (half, 0.0)]
		return pts

	def lining(y0, y1, swatch, grad):
		"""One stretch of tunnel, faces turned inward."""
		prof = profile()
		bm = bmesh.new()
		rings = []
		for y in (y0, y1):
			rings.append([bm.verts.new((x + p.rng.uniform(-0.08, 0.08) * (0 < i < len(prof) - 1), y, z))
						  for i, (x, z) in enumerate(prof)])
		for k in range(len(prof) - 1):
			a, b = rings[0][k], rings[0][k + 1]
			c, d = rings[1][k + 1], rings[1][k]
			bm.faces.new([a, d, c, b])  # wound so the normal points into the tunnel
		return p._add(bm, swatch, grad, 0.0, 0.0)

	# the tunnel, darker every few meters, ending in black
	stretches = [(-0.6, 2.4, STONE_DARK, (0.25, 0.85)), (2.4, 4.8, STONE_DARK, (0.6, 1.0)),
				 (4.8, 7.0, SHADE, (0.75, 0.92)), (7.0, depth, SHADE, (0.92, 1.0))]
	for y0, y1, sw, gr in stretches:
		lining(y0, y1, sw, gr)
		p.box((half * 2 + 0.2, y1 - y0, 0.2), (0, (y0 + y1) / 2, -0.1), sw, grad=(gr[1], gr[1]))  # floor, as dark as the walls get
	p.box((half * 2 + 0.4, 0.3, wall_h + half + 0.3), (0, depth, (wall_h + half) / 2), SHADE, grad=(1.0, 1.0))  # the dark

	# rocks along both sides and over the top, clear of the tunnel
	for sx in (-1, 1):
		for y, sz in ((-0.2, 3.4), (2.2, 3.0), (4.6, 3.2), (7.0, 3.0), (9.2, 3.2)):
			w = p.rng.uniform(2.6, 3.4)
			p.rock((w, sz, p.rng.uniform(3.6, 4.6)), (sx * (half + w / 2 + 0.05), y, 1.7), STONE_DARK, jitter=0.12)
		for y in (0.8, 4.4, 8.2):                       # an outer shoulder
			w = p.rng.uniform(3.2, 4.2)
			p.rock((w, 4.0, p.rng.uniform(2.6, 3.4)), (sx * (half + 3.0 + w / 2), y, 1.0), STONE_DARK, jitter=0.12)
			p.rock((w * 0.9, 3.6, 2.6), (sx * (half + 2.2), y + 0.8, 3.7), STONE_LIGHT, jitter=0.12)
	for y in (0.3, 2.8, 5.4, 8.0):                      # the roof of the cave
		h = p.rng.uniform(2.2, 2.8)
		p.rock((6.8, 3.2, h), (p.rng.uniform(-0.3, 0.3), y, wall_h + half + h / 2 + 0.05), STONE_LIGHT, jitter=0.12)
	for x, y, size in ((-2.2, 4.0, 4.2), (2.4, 6.0, 4.0), (0.0, 7.4, 3.6)):   # the hill's crown
		p.rock((size, size, size * 0.7), (x, y, wall_h + half + 2.6), STONE_DARK, jitter=0.14)

	# mine timbers: a braced frame at the mouth, and two more inside
	for y, sw in ((-0.35, WOOD), (3.0, WOOD_GRAY), (6.0, WOOD_GRAY)):
		for sx in (-1, 1):
			p.box((0.32, 0.32, 3.1), (sx * (half - 0.3), y, 1.55), sw, grad=(0.25, 1.0))
		p.box((half * 2 + 0.1, 0.36, 0.36), (0, y, 3.2), sw, grad=(0.2, 0.9))
		for sx in (-1, 1):                              # corner braces
			p.seg((sx * (half - 0.3), y, 2.5), (sx * (half - 1.0), y, 3.1), 0.08, 0.08, sw, sides=4)

	# what lies at the mouth: rubble, and a warning
	for x, y, size in ((-1.6, -1.4, 0.5), (1.9, -1.1, 0.4), (-0.4, -2.2, 0.3), (1.2, -2.6, 0.35), (-2.9, -2.0, 0.6)):
		p.rock((size * 1.3, size, size * 0.7), (x, y, size * 0.25), STONE_DARK, jitter=0.06)
	p.blob((0.34, 0.3, 0.3), (0.9, -1.8, 0.16), BONE, segs=(8, 6))                       # a skull
	p.blob((0.12, 0.08, 0.06), (0.83, -1.95, 0.2), SHADE, segs=(6, 4), grad=(1.0, 1.0))
	p.blob((0.12, 0.08, 0.06), (0.97, -1.95, 0.2), SHADE, segs=(6, 4), grad=(1.0, 1.0))
	for a, b in (((0.2, -1.5, 0.05), (0.7, -1.2, 0.05)), ((-0.6, -1.0, 0.05), (-0.1, -1.3, 0.05))):
		p.seg(a, b, 0.05, 0.05, BONE, sides=5)
	return p.build(bevel=0.04)


# ---------------------------------------------------------------- Hollowmere

def boardwalk():
	"""A 3 x 3 m section of plank walkway on stilts, for villages over water.
	The deck's top is the origin; posts run 3 m down into the water. Sections
	tile edge to edge along Y."""
	p = Prop("boardwalk", 91)
	n = 10
	for k in range(n):
		y = -1.5 + (k + 0.5) * 3.0 / n
		sw = WOOD_GRAY if p.rng.random() < 0.3 else WOOD
		p.box((3.0 + p.rng.uniform(-0.08, 0.08), 3.0 / n - 0.03, 0.08), (p.rng.uniform(-0.03, 0.03), y, -0.04),
			  sw, rot=(0, 0, p.rng.uniform(-1.2, 1.2)), grad=(0.1, 0.6))
	for x in (-1.2, 1.2):  # stringers
		p.box((0.16, 3.0, 0.18), (x, 0, -0.17), WOOD, grad=(0.3, 1.0))
	for x in (-1.35, 1.35):
		for y in (-1.2, 1.2):
			p.seg((x, y, -3.0), (x, y, -0.05), 0.11, 0.1, WOOD, sides=6, grad=(0.2, 1.0))
	return p.build(bevel=0.02)


def boardwalk_ramp():
	"""Planks sloping from a boardwalk's deck (origin) down 0.9 m over 3 m of
	shore toward -Y, so you can walk up onto the stilts."""
	p = Prop("boardwalk_ramp", 92)
	n = 10
	for k in range(n):
		t = (k + 0.5) / n
		y = -t * 3.0
		z = -t * 0.9
		p.box((2.4, 3.0 / n + 0.02, 0.08), (0, y, z - 0.04), WOOD if k % 3 else WOOD_GRAY, rot=(math.degrees(math.atan2(0.9, 3.0)), 0, 0), grad=(0.1, 0.6))
	for x in (-1.0, 1.0):
		p.seg((x, 0, -0.2), (x, -3.0, -1.1), 0.08, 0.08, WOOD, sides=5)
		p.seg((x, -0.2, -2.5), (x, -0.2, -0.1), 0.1, 0.09, WOOD, sides=6)
	return p.build(bevel=0.02)


def stilt_hut():
	"""A fisher's hut for the boardwalk: plank walls, a steep reed-thatch roof,
	a doorway at the front (-Y) and a shuttered window each side. Floor at the
	origin (set it on a boardwalk deck); about 4 x 4 m."""
	p = Prop("stilt_hut", 93)
	w, d, wall_h = 4.0, 4.0, 2.3
	hw, hd = w / 2, d / 2
	# walls of vertical planks, leaving a doorway in the front and windows at the sides
	def planks(x0, x1, y, along_x, skip=None):
		n = int(abs(x1 - x0) / 0.32)
		for k in range(n):
			c = x0 + (k + 0.5) * (x1 - x0) / n
			if skip and skip[0] < c < skip[1]:
				continue
			h = wall_h + p.rng.uniform(-0.08, 0.05)
			sw = WOOD_GRAY if p.rng.random() < 0.35 else WOOD
			if along_x:
				p.box((abs(x1 - x0) / n - 0.02, 0.1, h), (c, y, h / 2), sw, grad=(0.15, 0.9))
			else:
				p.box((0.1, abs(x1 - x0) / n - 0.02, h), (y, c, h / 2), sw, grad=(0.15, 0.9))
	planks(-hw, hw, -hd, True, skip=(-0.55, 0.55))  # front, with the door
	planks(-hw, hw, hd, True)
	planks(-hd, hd, -hw, False, skip=(-0.5, 0.5))  # sides, with windows
	planks(-hd, hd, hw, False, skip=(-0.5, 0.5))
	p.box((1.2, 0.12, 0.3), (0, -hd, 2.05), WOOD, grad=(0.3, 1.0))  # lintel
	for s in (-1, 1):
		p.box((0.12, 1.1, 0.95), (s * hw, 0, 0.5), WOOD_GRAY, grad=(0.2, 0.9))  # under the window
		p.box((0.12, 1.1, 0.35), (s * hw, 0, 2.1), WOOD, grad=(0.2, 0.9))  # over it
		p.box((0.06, 0.55, 0.9), (s * (hw + 0.05), -0.62, 1.45), WOOD_GRAY, rot=(0, 0, s * 25), grad=(0.1, 0.8))  # open shutter
	for x in (-hw, hw):
		for y in (-hd, hd):
			p.seg((x, y, 0), (x, y, wall_h + 0.1), 0.1, 0.09, WOOD, sides=6, grad=(0.2, 1.0))
	# thatch: two steep slopes of reed bundles overhanging the walls, and gable ends
	ridge = wall_h + 1.9
	for s in (-1, 1):
		p.poly([(s * (hw + 0.5), -hd - 0.45, wall_h - 0.2), (0, -hd - 0.45, ridge), (0, hd + 0.45, ridge), (s * (hw + 0.5), hd + 0.45, wall_h - 0.2)],
			   [(0, 1, 2, 3)], HIDE, grad=(0.0, 0.7))
		for k in range(6):  # bundle ridges across the slope
			t = (k + 0.5) / 6
			x = s * (hw + 0.5) * (1 - t)
			z = wall_h - 0.2 + (ridge - wall_h + 0.2) * t
			p.seg((x, -hd - 0.5, z + 0.04), (x, hd + 0.5, z + 0.04), 0.06, 0.06, HIDE, sides=4, grad=(0.1, 0.6))
	for y in (-hd, hd):
		p.poly([(-hw, y, wall_h), (0, y, ridge - 0.15), (hw, y, wall_h)], [(0, 1, 2)], WOOD_GRAY, grad=(0.2, 0.9))
	p.seg((0, -hd - 0.6, ridge + 0.05), (0, hd + 0.6, ridge + 0.05), 0.09, 0.09, WOOD, sides=6)
	# a net hung by the door and a lantern hook
	p.box((0.9, 0.05, 1.1), (1.3, -hd - 0.08, 1.2), CLOTH_WHITE, grad=(0.5, 1.0))
	p.seg((-0.9, -hd - 0.1, 2.1), (-0.9, -hd - 0.45, 2.1), 0.03, 0.03, IRON, sides=4)
	return p.build(bevel=0.02)


def rowboat():
	"""A small fishing boat to moor by the piers: about 3.2 m, bow toward -Y,
	floating with its waterline at the origin."""
	p = Prop("rowboat", 94)
	L, W = 3.2, 1.2
	# hull: a few stacked, narrowing plank rings
	rings = [(0.0, 0.55), (0.18, 0.9), (0.36, 1.0)]
	for z, f in rings:
		pts = []
		for k in range(12):
			a = k / 12 * math.tau
			x = math.cos(a) * W / 2 * f
			y = math.sin(a) * L / 2 * f
			if y < 0:
				x *= 1.0 + y / (L / 2) * 0.6  # the bow narrows to a point
			pts.append((x, y, z - 0.25))
		for k in range(12):
			a, b = pts[k], pts[(k + 1) % 12]
			p.poly([a, b, (b[0], b[1], b[2] + 0.2), (a[0], a[1], a[2] + 0.2)], [(0, 1, 2, 3)], WOOD, grad=(0.2, 0.9))
	p.box((W * 0.5, L * 0.6, 0.06), (0, 0.1, -0.22), WOOD_GRAY, grad=(0.3, 1.0))  # floor
	for y in (-0.3, 0.6):
		p.box((W * 0.85, 0.22, 0.05), (0, y, 0.05), WOOD, grad=(0.1, 0.6))  # thwarts
	p.seg((0.35, 0.1, 0.12), (1.3, 1.2, -0.1), 0.03, 0.03, WOOD, sides=4)  # an oar left out
	p.box((0.12, 0.35, 0.02), (1.32, 1.28, -0.12), WOOD, rot=(0, 0, 40))
	return p.build(bevel=0.01)


def reed_hut():
	"""Lizardfolk hut: a squat dome of bundled marsh reeds on a ring of bent
	poles, a low doorway at the front (-Y). About 3.6 m across."""
	p = Prop("reed_hut", 95)
	r, h = 1.8, 2.4
	n = 14
	for k in range(n):
		a = k / n * math.tau
		if abs(math.atan2(math.sin(a + math.pi / 2), math.cos(a + math.pi / 2))) < 0.35:
			continue  # the doorway faces -Y
		prev = None
		for j in range(6):
			t = j / 5
			rr = r * math.cos(t * math.pi / 2 * 0.95)
			z = h * math.sin(t * math.pi / 2)
			pt = (math.cos(a) * rr, math.sin(a) * rr, z)
			if prev:
				p.seg(prev, pt, 0.17, 0.15, HIDE, sides=5, grad=(0.0, 0.8))
			prev = pt
	for k in range(4):  # binding rings
		z = 0.4 + k * 0.5
		rr = r * math.cos(math.asin(min(z / h, 0.99))) + 0.1
		for j in range(n):
			a0, a1 = j / n * math.tau, (j + 1) / n * math.tau
			if abs(math.atan2(math.sin(a0 + math.pi / 2), math.cos(a0 + math.pi / 2))) < 0.5:
				continue
			p.seg((math.cos(a0) * rr, math.sin(a0) * rr, z), (math.cos(a1) * rr, math.sin(a1) * rr, z), 0.035, 0.035, WOOD, sides=4)
	p.blob((r * 1.9, r * 1.9, h * 1.95), (0, 0, 0), HIDE, segs=(14, 8), grad=(0.25, 1.0))  # the packed thatch under the bundles
	p.box((1.0, 0.3, 1.5), (0, -r + 0.05, 0.7), SHADE, grad=(0.95, 1.0))  # the dark doorway
	p.seg((0, 0, h - 0.1), (0, 0, h + 0.7), 0.2, 0.0, HIDE, sides=6, grad=(0.0, 0.6))  # topknot
	for s in (-1, 1):  # door poles with a skull
		p.seg((s * 0.55, -r - 0.05, 0), (s * 0.5, -r - 0.05, 1.6), 0.06, 0.05, WOOD, sides=5)
	p.blob((0.28, 0.24, 0.24), (0, -r - 0.1, 1.72), BONE, grad=(0.0, 0.5))
	return p.build(bevel=0.01)


def bone_totem():
	"""A lizardfolk totem: a crooked pole hung with a beast skull, bones and
	feathers. About 2.8 m."""
	p = Prop("bone_totem", 96)
	p.seg((0, 0, 0), (0.08, 0.04, 2.6), 0.12, 0.08, WOOD, sides=6, grad=(0.2, 1.0))
	p.blob((0.42, 0.5, 0.36), (0.08, -0.12, 2.45), BONE, grad=(0.0, 0.5))  # skull
	p.seg((0.08, -0.4, 2.42), (0.08, -0.75, 2.35), 0.1, 0.05, BONE, sides=5)  # snout
	for s in (-1, 1):
		p.seg((0.08 + s * 0.16, -0.05, 2.6), (0.08 + s * 0.45, 0.05, 2.95), 0.05, 0.01, BONE, sides=4)  # horns
		p.box((0.12, 0.12, 0.08), (0.08 + s * 0.12, -0.33, 2.5), EMBER, glow=0.4)  # eyes painted
	p.seg((-0.5, 0, 1.8), (0.6, 0.05, 1.8), 0.04, 0.04, WOOD, sides=4)  # crossbar
	for x in (-0.45, -0.15, 0.25, 0.55):
		p.seg((x, 0, 1.78), (x + p.rng.uniform(-0.05, 0.05), 0, 1.3), 0.02, 0.02, HIDE, sides=3)
		p.blob((0.1, 0.1, 0.16), (x, 0, 1.25), BONE if x < 0 else CLOTH_RED, grad=(0.0, 0.6))
	for k in range(3):
		p.box((0.05, 0.02, 0.35), (0.22, 0.05 * k, 2.1 - k * 0.1), CLOTH_RED, rot=(0, 20 - k * 15, 0))  # feathers
	return p.build(bevel=0.01)


# ---------------------------------------------------------------- Harrowfield

def windmill():
	"""A farm windmill: a round fieldstone tower (a door at the front, -Y) under
	a wooden cap. The sails are their own prop (windmill_sails), turned by the
	game at the hub 7.6 m up on the front."""
	p = Prop("windmill", 101)
	for k in range(7):  # the tower, narrowing in courses of fieldstone
		z = k * 0.95
		r = 2.4 - k * 0.14
		p.seg((0, 0, z), (0, 0, z + 0.95), r, r - 0.14, STONE_WARM, sides=12, grad=(0.05 + 0.04 * (k % 2), 0.8), jitter=0.03)
	p.seg((0, 0, 6.6), (0, 0, 7.0), 1.75, 1.7, WOOD, sides=12)  # a wooden band at the top
	p.seg((0, 0, 7.0), (0, 0, 9.0), 1.85, 0.25, WOOD_GRAY, sides=12, grad=(0.0, 0.8))  # the cap
	p.seg((0, -1.2, 7.6), (0, -2.0, 7.6), 0.28, 0.24, WOOD, sides=8)  # the axle out the front
	p.box((1.1, 0.3, 1.9), (0, -2.35, 0.95), WOOD_GRAY, grad=(0.3, 1.0))  # door
	p.box((1.4, 0.35, 0.2), (0, -2.35, 2.0), WOOD)
	for z, a in ((3.4, 40), (4.8, -30)):  # little windows
		p.box((0.5, 0.3, 0.7), (math.sin(math.radians(a)) * 2.05, -math.cos(math.radians(a)) * 2.05, z), SHADE, rot=(0, 0, a), grad=(0.9, 1.0))
	p.box((0.9, 0.6, 0.5), (1.6, -1.6, 0.25), WOOD, rot=(0, 0, 20))  # sacks and a crate at the door
	p.blob((0.7, 0.55, 0.8), (-1.5, -1.9, 0.4), CLOTH_WHITE, grad=(0.2, 0.8))
	return p.build(bevel=0.04)


def windmill_sails():
	"""Four lattice sails round a hub at the origin, in the X-Z plane, facing -Y."""
	p = Prop("windmill_sails", 102)
	p.blob((0.5, 0.4, 0.5), (0, 0, 0), WOOD, segs=(8, 6))
	for k in range(4):
		a = k * math.pi / 2 + math.radians(15)
		d = (math.cos(a), math.sin(a))
		tip = (d[0] * 5.2, 0, d[1] * 5.2)
		p.seg((0, -0.05, 0), tip, 0.12, 0.08, WOOD, sides=5)  # the whip
		side = (-d[1], d[0])
		for j in range(5):  # the lattice, with cloth on the outer part
			t = 1.4 + j * 0.9
			a0 = (d[0] * t, -0.08, d[1] * t)
			a1 = (d[0] * t + side[0] * 1.0, -0.08, d[1] * t + side[1] * 1.0)
			p.seg(a0, a1, 0.04, 0.04, WOOD, sides=4)
		c = (d[0] * 3.4 + side[0] * 0.5, -0.1, d[1] * 3.4 + side[1] * 0.5)
		p.box((0.9, 0.04, 3.6), c, CLOTH_WHITE, rot=(0, -math.degrees(a) + 90, 0), grad=(0.2, 0.7))
	return p.build()


def fence_wood():
	"""A 3 m run of split-rail fence along X, posts at both ends."""
	p = Prop("fence_wood", 103)
	for x in (-1.5, 1.5):
		p.seg((x, 0, 0), (x, 0, 1.25), 0.09, 0.08, WOOD, sides=5, grad=(0.2, 1.0))
	for z in (0.45, 0.95):
		p.seg((-1.6, 0, z + p.rng.uniform(-0.04, 0.04)), (1.6, 0, z + p.rng.uniform(-0.04, 0.04)), 0.06, 0.06, WOOD_GRAY, sides=5)
	return p.build(bevel=0.02)


def hay_bale():
	"""A tied square bale of hay."""
	p = Prop("hay_bale", 104)
	p.box((1.2, 0.8, 0.7), (0, 0, 0.35), GOLD, grad=(0.1, 0.8), jitter=0.02)
	for x in (-0.3, 0.3):
		p.box((0.05, 0.84, 0.74), (x, 0, 0.35), WOOD_GRAY)
	return p.build(bevel=0.05)


def haystack():
	"""A tall rounded stack of hay on a field."""
	p = Prop("haystack", 105)
	p.blob((3.0, 3.0, 3.4), (0, 0, 1.2), GOLD, segs=(12, 8), grad=(0.0, 0.9), jitter=0.06)
	p.seg((0, 0, 2.6), (0, 0, 3.4), 0.06, 0.04, WOOD, sides=4)
	return p.build()


def farm_cart():
	"""A two-wheeled farm cart, shafts to the front (-Y), loaded with sacks."""
	p = Prop("farm_cart", 106)
	p.box((1.6, 2.4, 0.12), (0, 0, 0.75), WOOD, grad=(0.2, 1.0))
	for x in (-0.8, 0.8):
		p.box((0.08, 2.4, 0.45), (x, 0, 1.0), WOOD_GRAY, grad=(0.2, 1.0))
		p.seg((x * 1.05, 0.1, 0.6), (x * 1.3, 0.1, 0.6), 0.08, 0.08, WOOD, sides=6)
		for k in range(10):  # the wheel rim
			a0, a1 = k * math.tau / 10, (k + 1) * math.tau / 10
			p.seg((x * 1.18, 0.1 + math.cos(a0) * 0.6, 0.6 + math.sin(a0) * 0.6), (x * 1.18, 0.1 + math.cos(a1) * 0.6, 0.6 + math.sin(a1) * 0.6), 0.06, 0.06, WOOD, sides=4)
		for k in range(4):
			a = k * math.pi / 4
			p.seg((x * 1.18, 0.1 - math.cos(a) * 0.55, 0.6 - math.sin(a) * 0.55), (x * 1.18, 0.1 + math.cos(a) * 0.55, 0.6 + math.sin(a) * 0.55), 0.03, 0.03, WOOD_GRAY, sides=4)
	for x in (-0.5, 0.5):
		p.seg((x, -1.2, 0.75), (x * 0.8, -2.6, 0.55), 0.05, 0.05, WOOD, sides=5)  # shafts
	for k in range(4):
		p.blob((0.6, 0.5, 0.55), (-0.35 + (k % 2) * 0.7, -0.5 + (k // 2) * 0.8, 1.05), CLOTH_WHITE, grad=(0.2, 0.8))
	return p.build(bevel=0.02)


def wheat():
	"""A clump of ripe wheat for the fields (drawn as clutter): golden stalks
	with seed heads."""
	p = Prop("wheat", 107)
	for k in range(9):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.2)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(0.8, 1.05)
		la = p.rng.uniform(0, math.tau)
		lean = p.rng.uniform(0.05, 0.18)
		top = (x + math.cos(la) * lean, y + math.sin(la) * lean, h)
		w = 0.02
		p.poly([(x - w, y, 0), (x + w, y, 0), (top[0], top[1], top[2] - 0.18)], [(0, 1, 2)], GOLD, grad=(0.35, 0.8))
		p.blob((0.06, 0.06, 0.2), (top[0], top[1], top[2] - 0.08), GOLD, segs=(4, 3), grad=(0.0, 0.4))
	return p.build()


def scarecrow_post():
	"""A scarecrow on its pole in a field: sack head, straw hat, arms out on a
	crossbar, a ragged coat. Faces -Y."""
	p = Prop("scarecrow_post", 108)
	p.seg((0, 0, 0), (0, 0, 2.3), 0.07, 0.06, WOOD, sides=5)
	p.seg((-1.0, 0, 1.75), (1.0, 0, 1.75), 0.05, 0.05, WOOD, sides=5)
	p.box((0.8, 0.38, 0.9), (0, 0, 1.45), CLOTH_RED, grad=(0.4, 1.0), jitter=0.03)  # the coat
	for s in (-1, 1):
		p.seg((s * 0.35, 0, 1.75), (s * 0.95, 0, 1.72), 0.13, 0.11, CLOTH_RED, sides=6, grad=(0.4, 1.0))  # sleeves
		p.seg((s * 0.95, 0, 1.72), (s * 1.12, -0.05, 1.62), 0.08, 0.0, GOLD, sides=5)  # straw hands
	p.seg((0, 0, 1.0), (0.05, 0, 0.8), 0.18, 0.0, GOLD, sides=6)  # straw below the coat
	p.blob((0.46, 0.42, 0.5), (0, 0, 2.15), HIDE, grad=(0.1, 0.6))  # sack head
	p.box((0.08, 0.05, 0.08), (-0.1, -0.21, 2.2), STONE_DARK)
	p.box((0.08, 0.05, 0.08), (0.1, -0.21, 2.2), STONE_DARK)
	p.box((0.22, 0.04, 0.03), (0, -0.21, 2.05), STONE_DARK)
	p.seg((0, 0, 2.36), (0, 0, 2.42), 0.5, 0.5, GOLD, sides=10)  # hat brim
	p.seg((0, 0, 2.4), (0, 0.02, 2.72), 0.25, 0.14, GOLD, sides=8)
	return p.build()


# ---------------------------------------------------------------- Sunward Steps

def elephant_statue():
	"""Prabhagaj the Dawn-Tusk: a stone elephant standing on a plinth, trunk
	raised to hold up a gilded sun disc. About 5 m tall, facing -Y."""
	p = Prop("elephant_statue", 111)
	p.box((3.2, 4.2, 1.0), (0, 0, 0.5), STONE_WARM, grad=(0.1, 0.9))           # plinth
	p.box((3.5, 4.5, 0.25), (0, 0, 1.1), STONE_LIGHT, grad=(0.1, 0.7))
	p.blob((2.1, 3.0, 1.9), (0, 0.2, 2.6), STONE_LIGHT, segs=(12, 8), grad=(0.05, 0.8))   # body
	for x in (-0.65, 0.65):
		for y in (-0.9, 1.2):
			p.seg((x, y, 1.2), (x, y, 2.3), 0.38, 0.4, STONE_LIGHT, sides=8, grad=(0.2, 0.9))   # legs
	p.blob((1.4, 1.3, 1.4), (0, -1.55, 3.2), STONE_LIGHT, segs=(10, 8), grad=(0.05, 0.8))   # head
	for x in (-1, 1):
		p.blob((0.2, 1.1, 1.2), (x * 0.85, -1.35, 3.25), STONE_WARM, segs=(8, 6), grad=(0.1, 0.8))   # ears
		p.seg((x * 0.35, -2.0, 2.85), (x * 0.5, -2.6, 2.6), 0.13, 0.05, BONE, sides=6)   # tusks
	pts = [(0, -2.1, 3.0), (0, -2.5, 3.5), (0, -2.55, 4.2), (0, -2.35, 4.8)]   # the trunk, raised
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.3 - i * 0.06, 0.26 - i * 0.06, STONE_LIGHT, sides=8, grad=(0.1, 0.8))
	p.seg((0, -2.35, 5.3), (0, -2.47, 5.3), 0.75, 0.75, GOLD, sides=16, glow=0.35)   # the sun disc
	for k in range(12):
		a = k * math.tau / 12
		p.seg((math.cos(a) * 0.72, -2.41, 5.3 + math.sin(a) * 0.72), (math.cos(a) * 1.05, -2.41, 5.3 + math.sin(a) * 1.05), 0.08, 0.0, GOLD, sides=4, glow=0.3)
	return p.build(bevel=0.04)


def sun_pillar():
	"""A tall carved pillar crowned with a gilded sun disc, for shrine approaches."""
	p = Prop("sun_pillar", 112)
	p.box((1.1, 1.1, 0.4), (0, 0, 0.2), STONE_WARM)
	p.seg((0, 0, 0.4), (0, 0, 4.2), 0.42, 0.36, STONE_LIGHT, sides=8, grad=(0.1, 0.9))
	for z in (1.2, 2.6, 3.8):
		p.seg((0, 0, z), (0, 0, z + 0.15), 0.46, 0.46, STONE_WARM, sides=8)
	p.seg((0, 0.05, 4.9), (0, -0.05, 4.9), 0.65, 0.65, GOLD, sides=16, glow=0.35)
	p.seg((0, 0, 4.2), (0, 0, 4.3), 0.2, 0.2, STONE_WARM, sides=8)
	return p.build(bevel=0.03)


def broken_column():
	"""A fallen temple's column, snapped partway up, a drum lying beside it."""
	p = Prop("broken_column", 113)
	p.box((1.3, 1.3, 0.35), (0, 0, 0.17), STONE_WARM)
	h = 1.6 + p.rng.uniform(0, 1.2)
	p.seg((0, 0, 0.35), (0, 0, h), 0.5, 0.48, STONE_LIGHT, sides=10, grad=(0.1, 0.9), jitter=0.02)
	p.seg((1.3, 0.6, 0.45), (2.3, 1.1, 0.45), 0.45, 0.45, STONE_LIGHT, sides=10, grad=(0.2, 0.9))
	return p.build(bevel=0.03)


def sun_banner():
	"""The false-sun cult's banner: an orange cloth with a red sun, on a pole."""
	p = Prop("sun_banner", 114)
	p.seg((0, 0, 0), (0, 0, 3.4), 0.06, 0.05, WOOD, sides=5)
	p.seg((-0.7, 0, 3.2), (0.7, 0, 3.2), 0.04, 0.04, WOOD, sides=4)
	p.box((1.3, 0.05, 1.9), (0, 0, 2.2), EMBER, grad=(0.1, 0.6))
	p.seg((0, -0.04, 2.45), (0, -0.08, 2.45), 0.38, 0.38, CLOTH_RED, sides=12)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.4, -0.06, 2.45 + math.sin(a) * 0.4), (math.cos(a) * 0.62, -0.06, 2.45 + math.sin(a) * 0.62), 0.05, 0.0, CLOTH_RED, sides=3)
	return p.build()


# ---------------------------------------------------------------- Lanternhold

def lantern_string():
	"""A string of paper lanterns slung between two posts across a street:
	9 m span, the rope sagging to 4 m, lanterns glowing gold. Spans along X."""
	p = Prop("lantern_string", 121)
	half = 4.5
	for x in (-half, half):
		p.seg((x, 0, 0), (x, 0, 4.9), 0.09, 0.08, WOOD, sides=6, grad=(0.2, 1.0))
		p.seg((x, 0, 4.9), (x, 0, 5.1), 0.13, 0.13, WOOD_GRAY, sides=6)
	n = 12
	prev = None
	for k in range(n + 1):
		t = k / n
		x = -half + t * 2 * half
		z = 4.8 - 0.9 * (1 - (2 * t - 1) ** 2)  # a sagging rope
		pt = (x, 0, z)
		if prev:
			p.seg(prev, pt, 0.02, 0.02, WOOD_GRAY, sides=3)
		prev = pt
		if 0 < k < n and k % 2 == 0:
			p.seg((x, 0, z), (x, 0, z - 0.25), 0.01, 0.01, WOOD_GRAY, sides=3)
			p.blob((0.34, 0.34, 0.42), (x, 0, z - 0.45), EMBER if k % 4 else GOLD, segs=(8, 6), glow=1.6)
	return p.build()


# ---------------------------------------------------------------- The Bleach

def titan_ribcage():
	"""The ribs of some ancient giant beast, arching out of the salt: a spine
	along Y and pairs of curved ribs, about 18 m long and 7 m high."""
	p = Prop("titan_ribcage", 131)
	for k in range(9):  # the spine, half buried
		y = -8.0 + k * 2.0
		p.blob((1.3, 1.6, 1.0), (0, y, 0.3), BONE, segs=(8, 6), grad=(0.0, 0.7))
	for k in range(7):  # ribs arching up and over
		y = -6.0 + k * 2.0
		h = 7.0 - abs(k - 3) * 0.7
		for s_ in (-1, 1):
			prev = None
			for j in range(6):
				t = j / 5
				pt = (s_ * (1.0 + math.sin(t * math.pi * 0.9) * 4.2), y, 0.3 + h * math.sin(t * math.pi * 0.55))
				if prev:
					p.seg(prev, pt, 0.34 - j * 0.03, 0.31 - j * 0.03, BONE, sides=7, grad=(0.0, 0.7))
				prev = pt
	return p.build(bevel=0.03)


def titan_skull():
	"""A great horned skull lying on its jaw in the salt, tusks out front (-Y): 8 m across."""
	p = Prop("titan_skull", 132)
	p.blob((5.0, 6.0, 3.8), (0, 0, 1.4), BONE, segs=(12, 8), grad=(0.0, 0.8))
	for s_ in (-1, 1):
		p.blob((1.3, 1.3, 1.1), (s_ * 1.4, -2.4, 2.0), STONE_DARK, segs=(8, 6))  # eye sockets
		pts = [(s_ * 1.8, -2.8, 0.9), (s_ * 2.4, -5.0, 0.8), (s_ * 2.2, -7.0, 1.6), (s_ * 1.5, -8.2, 2.8)]  # tusks
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.55 - i * 0.14, 0.45 - i * 0.14, BONE, sides=8, grad=(0.0, 0.6))
		hp = [(s_ * 2.3, 1.2, 3.0), (s_ * 3.8, 1.8, 4.6), (s_ * 4.2, 1.0, 6.2)]  # horns
		for i, (a, b) in enumerate(zip(hp, hp[1:])):
			p.seg(a, b, 0.5 - i * 0.18, 0.35 - i * 0.18, BONE, sides=7, grad=(0.0, 0.6))
	p.box((2.6, 2.4, 0.9), (0, -3.3, 0.45), BONE, grad=(0.1, 0.8))  # the jaw in the ground
	return p.build(bevel=0.04)


def mesa():
	"""A flat-topped butte of banded pale stone, wider than it is tall: about
	20 m across and 11 m high, its sides broken and uneven."""
	p = Prop("mesa", 133)
	for k in range(4):  # four thick bands, barely narrowing
		z = k * 2.8
		r = 10.0 - k * 0.45
		p.seg((0, 0, z), (0, 0, z + 2.9), r, r - 0.25, STONE_WARM if k % 2 else STONE_LIGHT, sides=11, grad=(0.1, 0.9), jitter=0.9)
	p.seg((0, 0, 11.2), (0, 0, 11.5), 8.4, 8.0, STONE_WARM, sides=11, jitter=0.4)  # the flat top
	for k in range(9):  # fallen blocks and a scree skirt at the foot
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(9.5, 11.5)
		s_ = p.rng.uniform(1.2, 2.4)
		p.rock((s_, s_ * 0.9, s_ * 0.7), (math.cos(a) * d, math.sin(a) * d, 0.3), STONE_LIGHT)
	return p.build()


def salt_crystals():
	"""A cluster of white salt crystals growing out of the flats, up to 1.6 m."""
	p = Prop("salt_crystals", 134)
	for k in range(9):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0, 0.6)
		h = p.rng.uniform(0.5, 1.6)
		lean = p.rng.uniform(-0.3, 0.3)
		p.seg((math.cos(a) * r, math.sin(a) * r, -0.1), (math.cos(a) * r + lean, math.sin(a) * r, h), 0.2, 0.0, CLOTH_WHITE, sides=5, grad=(0.0, 0.5), glow=0.15)
	return p.build()


def dead_palm():
	"""A dead palm at a dry oasis: a leaning grey trunk and a few broken, drooping fronds."""
	p = Prop("dead_palm", 135)
	pts = [(0, 0, 0), (0.3, 0, 2.0), (0.8, 0, 4.0), (1.5, 0, 5.8)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.32 - i * 0.06, 0.28 - i * 0.06, WOOD_GRAY, sides=7, grad=(0.1, 0.9))
	for k in range(5):
		a = k * math.tau / 5 + 0.3
		p.seg((1.5, 0, 5.8), (1.5 + math.cos(a) * 1.8, math.sin(a) * 1.8, 5.0), 0.08, 0.02, HIDE, sides=4)
	return p.build()


def caravan_wagon():
	"""A salt-trader's covered wagon: canvas hoops over a plank bed, big wheels, shafts to -Y."""
	p = Prop("caravan_wagon", 136)
	p.box((2.2, 4.2, 0.2), (0, 0, 1.0), WOOD, grad=(0.2, 1.0))
	for x in (-1.1, 1.1):
		p.box((0.1, 4.2, 0.5), (x, 0, 1.35), WOOD_GRAY)
		for y in (-1.4, 1.4):  # wheels
			for k in range(10):
				a0, a1 = k * math.tau / 10, (k + 1) * math.tau / 10
				p.seg((x * 1.12, y + math.cos(a0) * 0.75, 0.75 + math.sin(a0) * 0.75), (x * 1.12, y + math.cos(a1) * 0.75, 0.75 + math.sin(a1) * 0.75), 0.07, 0.07, WOOD, sides=4)
			p.seg((x * 1.12, y, 0.0), (x * 1.12, y, 1.5), 0.04, 0.04, WOOD_GRAY, sides=4)
	for k in range(5):  # the canvas hoops and cover
		y = -1.8 + k * 0.9
		prev = None
		for j in range(7):
			a = math.pi * j / 6
			pt = (math.cos(a) * 1.15, y, 1.6 + math.sin(a) * 1.3)
			if prev:
				p.seg(prev, pt, 0.04, 0.04, WOOD, sides=4)
			prev = pt
	p.blob((2.4, 4.0, 2.6), (0, 0, 1.6), CLOTH_WHITE, segs=(10, 6), grad=(0.1, 0.6))
	for s_ in (-1, 1):
		p.seg((s_ * 0.5, -2.1, 1.0), (s_ * 0.4, -4.0, 0.7), 0.05, 0.05, WOOD, sides=5)
	for k in range(3):
		p.blob((0.55, 0.45, 0.5), (-0.6 + k * 0.6, 2.4, 1.3), HIDE, grad=(0.2, 0.8))  # salt sacks at the back
	return p.build(bevel=0.02)


# ---------------------------------------------------------------- The Weeping Throat (rain jungle)

MOSS = (3, 3)      # teal-green: moss on old stone
BAMBOO = (1, 3)    # gold-brown: bamboo, palm thatch


def _fin(p, a, r0, h, reach, t, swatch=WOOD, grad=(0.3, 1.0), z0=-0.3):
	"""A buttress root: a thin slab in the radial plane at angle `a`, standing
	`h` high against the trunk and running out `reach` along the ground, its
	top edge curving in."""
	d = Vector((math.cos(a), math.sin(a), 0))
	n = Vector((-math.sin(a), math.cos(a), 0))
	prof = [(r0 * 0.5, z0), (reach, z0), (reach * 0.85, z0 + 0.25), (r0 + (reach - r0) * 0.3, z0 + h * 0.3), (r0 * 0.5, z0 + h)]
	verts = []
	for side, taper in ((-t / 2, 1.0), (t / 2, 1.0)):
		for i, (r, z) in enumerate(prof):
			k = taper if i < 2 else taper * 0.7
			v = d * r + n * side * k
			verts.append((v.x, v.y, z))
	k = len(prof)
	faces = [(0, i, i + 1) for i in range(1, k - 1)] + [(k, k + i + 1, k + i) for i in range(1, k - 1)]
	for i in range(k):
		j = (i + 1) % k
		faces.append((i, j, k + j, k + i))
	return p.poly(verts, faces, swatch, grad)


def _chain(p, pts, r1, r2, swatch, sides=6, grad=(0.1, 0.8), glow=0.0):
	"""Segments along a polyline, tapering from r1 to r2."""
	n = len(pts) - 1
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		ra = r1 + (r2 - r1) * i / n
		rb = r1 + (r2 - r1) * (i + 1) / n
		p.seg(a, b, ra, rb, swatch, sides=sides, grad=grad, glow=glow)


def _vine(p, top, length, rng, leaves=True, r=0.03):
	"""One vine hanging from `top`, wandering a little, with leaves along it."""
	x, y, z = top
	pts = [(x, y, z)]
	steps = max(2, int(length / 0.7))
	for k in range(steps):
		x += rng.uniform(-0.12, 0.12)
		y += rng.uniform(-0.08, 0.08)
		z -= length / steps
		pts.append((x, y, z))
	_chain(p, pts, r, r * 0.6, LEAF, sides=4, grad=(0.4, 1.0))
	if leaves:
		for k in range(1, len(pts)):
			for j in range(2):
				a, b = pts[k - 1], pts[k]
				t = (j + 0.5) / 2
				c = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
				side = 1 if (k + j) % 2 else -1
				p.blob((0.24, 0.07, 0.15), (c[0] + side * 0.1, c[1], c[2]), LEAF if rng.random() < 0.6 else PINE,
					   rot=(rng.uniform(-20, 20), 0, rng.uniform(0, 360)), segs=(5, 3), grad=(0.2, 0.9))
	return pts[-1]


def jungle_tree():
	"""A tall rainforest tree, about 16 m: a straight grey-brown trunk on flared
	buttress roots, a few big limbs high up and a broad, layered canopy of dark
	leaf masses. Its trunk stays slim near the ground, so a zone's "trunk"
	collider (0.3 m x 3 m) fits it."""
	p = Prop("jungle_tree", 141)
	trunk = [(0, 0, -0.3), (0.08, 0.02, 4.0), (0.02, 0.12, 8.0), (0.12, 0.04, 11.0)]
	_chain(p, trunk, 0.5, 0.3, WOOD_GRAY, sides=8, grad=(0.1, 0.9))
	for k in range(5):  # buttress roots
		a = k * math.tau / 5 + p.rng.uniform(-0.3, 0.3)
		_fin(p, a, 0.45, p.rng.uniform(1.8, 2.6), p.rng.uniform(1.4, 2.0), 0.2, WOOD_GRAY, grad=(0.2, 1.0))
	limbs = []
	for k in range(4):  # big limbs, each splitting once
		a = k * math.tau / 4 + p.rng.uniform(-0.4, 0.4)
		z0 = 9.0 + k * 0.6
		mid = (math.cos(a) * 1.8, math.sin(a) * 1.8, z0 + 1.6)
		tip = (math.cos(a) * 3.6, math.sin(a) * 3.6, z0 + 2.6)
		_chain(p, [(0.1, 0.05, z0), mid, tip], 0.24, 0.1, WOOD_GRAY, sides=6)
		b = a + 0.6
		p.seg(mid, (mid[0] + math.cos(b) * 1.4, mid[1] + math.sin(b) * 1.4, mid[2] + 1.5), 0.12, 0.06, WOOD_GRAY, sides=5)
		limbs.append(tip)
		limbs.append((mid[0] + math.cos(b) * 1.4, mid[1] + math.sin(b) * 1.4, mid[2] + 1.5))
	for i, (x, y, z) in enumerate(limbs):  # the lower canopy layer: masses at every limb's end
		s = 3.6 if i % 2 == 0 else 2.7
		p.rock((s, s, s * 0.55), (x, y, z + 0.5), LEAF if i % 3 else PINE, rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.5, 1.0), jitter=0.07)
		for j in range(2):
			a = p.rng.uniform(0, math.tau)
			t = s * 0.6
			p.rock((t, t, t * 0.6), (x + math.cos(a) * s * 0.4, y + math.sin(a) * s * 0.4, z + 0.2 + j * 0.6), PINE if (i + j) % 2 else LEAF,
				   rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.45, 1.0), jitter=0.07)
	p.rock((6.4, 6.2, 3.0), (0.2, 0.1, 14.4), PINE, grad=(0.3, 1.0), jitter=0.07)  # the crown
	p.rock((4.6, 4.4, 2.4), (0.6, -0.5, 15.6), LEAF, grad=(0.45, 1.0), jitter=0.07)
	for k in range(3):  # a few vines down from the limbs
		x, y, z = limbs[k * 2]
		_vine(p, (x * 0.8, y * 0.8, z - 0.2), p.rng.uniform(3.0, 5.5), p.rng, leaves=False, r=0.035)
	return p.build()


def jungle_tree_giant():
	"""A strangler fig, about 25 m: a trunk of roots wound round each other, 5 m
	across at the flare, great limbs with aerial roots dropping to the ground,
	and a canopy in two tiers. A landmark: collide it as a mesh or a box."""
	p = Prop("jungle_tree_giant", 142)
	p.seg((0, 0, -0.3), (0, 0, 17.0), 1.5, 1.0, WOOD_GRAY, sides=10, grad=(0.2, 1.0))  # the host trunk inside
	for k in range(7):  # strangling roots spiraling up round it
		a0 = k * math.tau / 7
		pts = []
		for j in range(9):
			t = j / 8
			a = a0 + t * 1.6
			r = 2.4 * (1 - t) ** 2 + 1.25
			pts.append((math.cos(a) * r, math.sin(a) * r, -0.3 + t * 17.0))
		_chain(p, pts, 0.6, 0.35, WOOD, sides=6, grad=(0.3, 1.0))
	for k in range(8):  # the flare
		a = k * math.tau / 8 + 0.2
		_fin(p, a, 1.3, p.rng.uniform(3.2, 4.4), p.rng.uniform(4.0, 5.2), 0.4, WOOD, grad=(0.3, 1.0))
	tips = []
	for k in range(6):  # great limbs
		a = k * math.tau / 6 + p.rng.uniform(-0.25, 0.25)
		z0 = 13.5 + (k % 3) * 1.2
		reach = p.rng.uniform(7.5, 9.5)
		pts = [(math.cos(a) * 1.0, math.sin(a) * 1.0, z0),
			   (math.cos(a) * reach * 0.45, math.sin(a) * reach * 0.45, z0 + 2.2),
			   (math.cos(a) * reach, math.sin(a) * reach, z0 + 3.4)]
		_chain(p, pts, 0.7, 0.25, WOOD_GRAY, sides=7)
		tips.append(pts[2])
		for t in ((0.55, 0.85) if k % 2 else (0.7,)):  # aerial roots dropping to the ground
			x = math.cos(a) * reach * t + p.rng.uniform(-0.4, 0.4)
			y = math.sin(a) * reach * t + p.rng.uniform(-0.4, 0.4)
			ztop = z0 + 2.2 * min(t / 0.45, 1) + (1.2 * (t - 0.45) / 0.55 if t > 0.45 else 0)
			drop = [(x, y, ztop)]
			for j in range(4):
				drop.append((x + p.rng.uniform(-0.25, 0.25), y + p.rng.uniform(-0.25, 0.25), ztop - (ztop + 0.3) * (j + 1) / 4))
			_chain(p, drop, 0.08, 0.15, WOOD, sides=5, grad=(0.2, 1.0))
	for i, (x, y, z) in enumerate(tips):  # lower canopy tier
		p.rock((6.5, 6.5, 3.4), (x * 0.85, y * 0.85, z + 0.6), LEAF if i % 2 else PINE, rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.5, 1.0), jitter=0.07)
		for j in range(2):
			a = p.rng.uniform(0, math.tau)
			p.rock((4.0, 4.0, 2.4), (x * 0.85 + math.cos(a) * 2.6, y * 0.85 + math.sin(a) * 2.6, z + 0.2 + j), PINE if (i + j) % 2 else LEAF,
				   rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.45, 1.0), jitter=0.07)
	p.rock((12.0, 11.0, 4.6), (0, 0, 21.0), PINE, grad=(0.3, 1.0), jitter=0.06)  # the crown
	p.rock((8.0, 7.5, 3.4), (1.0, -0.6, 23.0), LEAF, grad=(0.45, 1.0), jitter=0.06)
	for k in range(6):  # moss and ferns in the crotches of the roots
		a = p.rng.uniform(0, math.tau)
		p.blob((1.0, 1.0, 0.35), (math.cos(a) * 2.2, math.sin(a) * 2.2, p.rng.uniform(1.0, 8.0)), MOSS, grad=(0.2, 0.9))
	return p.build()


def hanging_vines():
	"""A curtain of vines about 3 m wide and up to 5 m long. The origin is the
	top, where they hang from: set it at a branch, a ruin's lintel or a cliff's
	edge. No collision."""
	p = Prop("hanging_vines", 143)
	for k in range(9):  # a leafy mat along the top
		x = -1.5 + k * 3.0 / 8
		p.blob((0.7, 0.45, 0.3), (x, p.rng.uniform(-0.1, 0.1), -0.05), LEAF if k % 2 else PINE, segs=(6, 4), grad=(0.2, 0.9))
	for k in range(14):
		x = -1.45 + k * 2.9 / 13 + p.rng.uniform(-0.08, 0.08)
		_vine(p, (x, p.rng.uniform(-0.1, 0.1), -0.1), p.rng.uniform(2.4, 5.0), p.rng)
	return p.build()


def fern_clump():
	"""A big jungle fern, about 1.2 m tall and 2.4 m across: long arching fronds
	with leaflets down both sides. No collision."""
	p = Prop("fern_clump", 144)
	for k in range(10):
		a = k * math.tau / 10 + p.rng.uniform(-0.2, 0.2)
		d = Vector((math.cos(a), math.sin(a), 0))
		n = Vector((-math.sin(a), math.cos(a), 0))
		length = p.rng.uniform(1.0, 1.3)
		lift = p.rng.uniform(0.8, 1.2)
		pts = []
		for j in range(6):
			t = j / 5
			pts.append(d * length * t + Vector((0, 0, lift * math.sin(t * math.pi * 0.8) + 0.05)))
		_chain(p, [tuple(v) for v in pts], 0.025, 0.01, PINE, sides=4, grad=(0.2, 0.8))
		for j in range(len(pts) - 1):  # leaflets: a quad either side, shorter toward the tip
			a_, b_ = pts[j], pts[j + 1]
			w = 0.22 * (1 - j / 6)
			for s in (-1, 1):
				p.poly([tuple(a_), tuple(b_), tuple((a_ + b_) / 2 + n * s * w + Vector((0, 0, -0.06)))], [(0, 1, 2)],
					   LEAF if j % 2 else PINE, grad=(0.1, 0.8))
	return p.build()


def taro_plant():
	"""Elephant ears: a clump of big heart-shaped leaves on long stalks, about
	1.5 m tall. No collision."""
	p = Prop("taro_plant", 145)
	for k in range(6):
		a = k * math.tau / 6 + p.rng.uniform(-0.3, 0.3)
		d = Vector((math.cos(a), math.sin(a), 0))
		n = Vector((-math.sin(a), math.cos(a), 0))
		reach = p.rng.uniform(0.25, 0.5)
		top = d * reach + Vector((0, 0, p.rng.uniform(0.9, 1.35)))
		p.seg((0, 0, 0), tuple(top), 0.04, 0.025, LEAF, sides=5, grad=(0.1, 0.9))
		# the leaf hangs out and down from the stalk's top: a heart with a midrib fold
		L = p.rng.uniform(0.7, 0.95)
		tip = top + d * L + Vector((0, 0, -0.45))
		mid = top + d * L * 0.45 + Vector((0, 0, -0.05))
		lobe_l = top + n * L * 0.42 + d * -0.05 + Vector((0, 0, -0.12))
		lobe_r = top - n * L * 0.42 + d * -0.05 + Vector((0, 0, -0.12))
		side_l = mid + n * L * 0.38 + Vector((0, 0, -0.14))
		side_r = mid - n * L * 0.38 + Vector((0, 0, -0.14))
		sw = LEAF if k % 2 else PINE
		p.poly([tuple(top), tuple(lobe_l), tuple(side_l), tuple(mid)], [(0, 1, 2, 3)], sw, grad=(0.05, 0.7))
		p.poly([tuple(mid), tuple(side_l), tuple(tip)], [(0, 1, 2)], sw, grad=(0.05, 0.7))
		p.poly([tuple(top), tuple(mid), tuple(side_r), tuple(lobe_r)], [(0, 1, 2, 3)], sw, grad=(0.05, 0.7))
		p.poly([tuple(mid), tuple(tip), tuple(side_r)], [(0, 1, 2)], sw, grad=(0.05, 0.7))
	return p.build()


def _elephant_head(p, c, s, swatch=STONE_LIGHT, trunk=None, tusks=(True, True)):
	"""A carved elephant head at `c` (center), `s` its size in meters, facing -Y.
	`trunk` is a list of points (relative to c, in units of s) or None."""
	cx, cy, cz = c
	p.blob((1.0 * s, 0.9 * s, 1.0 * s), (cx, cy, cz), swatch, segs=(10, 8), grad=(0.05, 0.85))
	p.blob((0.7 * s, 0.4 * s, 0.35 * s), (cx, cy - 0.28 * s, cz + 0.35 * s), swatch, segs=(8, 6), grad=(0.05, 0.6))  # brow
	for x in (-1, 1):
		p.blob((1.0 * s, 0.18 * s, 1.1 * s), (cx + x * 0.72 * s, cy + 0.1 * s, cz - 0.05 * s), swatch,
			   rot=(0, x * 12, x * -18), segs=(10, 6), grad=(0.1, 0.8))  # ears
		p.blob((0.12 * s, 0.08 * s, 0.1 * s), (cx + x * 0.26 * s, cy - 0.42 * s, cz + 0.15 * s), IRON, segs=(6, 4))  # eyes
	pts = trunk or [(0, -0.4, -0.1), (0, -0.52, -0.5), (0, -0.5, -0.95), (0, -0.62, -1.2)]
	_chain(p, [(cx + a * s, cy + b * s, cz + d * s) for a, b, d in pts], 0.22 * s, 0.12 * s, swatch, sides=8, grad=(0.1, 0.8))
	for x, keep in zip((-1, 1), tusks):
		if keep:
			p.seg((cx + x * 0.25 * s, cy - 0.35 * s, cz - 0.35 * s), (cx + x * 0.36 * s, cy - 0.85 * s, cz - 0.6 * s), 0.08 * s, 0.02 * s, BONE, sides=6)


def jungle_temple():
	"""A ruined stepped temple of Jalendra the Tide-Trunked, about 12 m tall and
	14 m square (its stair runs 7 m further out), facing -Y: four tiers of mossy stone, a steep stair up the
	front to a shrine room whose dark doorway has an elephant-head relief over
	it. Its back-right corner has fallen in; roots and vines crawl over it all.
	Collide it as a mesh (the stair's 0.4 m steps are for looking at, not climbing)."""
	p = Prop("jungle_temple", 146)
	tiers = []
	TH = 1.8  # tier height
	for i in range(4):
		hs = 7.0 - 1.35 * i
		z0 = TH * i
		cut = 0.0 if i == 0 else 2.0 + 0.5 * i  # the fallen corner (+X, +Y)
		tiers.append((hs, z0, cut))

		def ell(grow, zc, h, sw, grad):
			if cut == 0.0:
				p.box((2 * hs + grow, 2 * hs + grow, h), (0, 0, zc), sw, grad=grad)
			else:
				p.box((2 * hs + grow, 2 * hs - cut + grow / 2, h), (0, -cut / 2 - grow / 4, zc), sw, grad=grad)
				p.box((2 * hs - cut + grow / 2, cut + grow / 2, h), (-cut / 2 - grow / 4, hs - cut / 2 + grow / 4, zc), sw, grad=grad)

		ell(0.0, z0 + TH / 2, TH, STONE_WARM if i % 2 else STONE_LIGHT, (0.15, 0.95))
		ell(0.3, z0 + TH - 0.1, 0.25, STONE_LIGHT, (0.0, 0.6))  # cornice
		ell(0.2, z0 + 0.12, 0.25, STONE_DARK, (0.2, 0.8))  # plinth course
	top = tiers[3][0]
	# the stair, 3.2 m wide, eighteen steps of 0.4 m up to the top tier's face
	n, rise = 18, 0.4
	y_top = -top
	run = n * rise
	for k in range(n):
		if k in (6, 13) :  # broken steps: shorter, a chunk missing
			p.box((2.0, run - k * rise, rise), (-0.6, y_top - (run - k * rise) / 2, k * rise + rise / 2), STONE_LIGHT, grad=(0.1, 0.8))
			continue
		p.box((3.2, run - k * rise, rise), (0, y_top - (run - k * rise) / 2, k * rise + rise / 2), STONE_LIGHT if k % 2 else STONE_WARM, grad=(0.1, 0.8))
	zt = 4 * TH
	ang = math.degrees(math.atan2(zt, run))
	for s in (-1, 1):  # balustrades up both sides of the stair
		p.box((0.5, math.hypot(zt, run), 0.5), (s * 1.85, y_top - run / 2, zt / 2 + 0.25), STONE_DARK, rot=(ang, 0, 0), grad=(0.1, 0.8))
		p.box((0.9, 0.9, 1.1), (s * 1.85, y_top - run - 0.1, 0.55), STONE_DARK, grad=(0.1, 0.8))
	# the shrine room on top: 4.4 x 4 m, 3.4 m walls, a doorway facing the stair
	rw, rd, rh = 2.2, 2.0, 3.4
	fy = -rd + 0.3
	p.box((0.6, 2 * rd, rh), (-rw + 0.3, 0, zt + rh / 2), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((0.6, 2 * rd, rh - 0.9), (rw - 0.3, 0, zt + (rh - 0.9) / 2), STONE_LIGHT, grad=(0.1, 0.9))  # cracked down on the fallen side
	p.box((2 * rw, 0.6, rh), (0, rd - 0.3, zt + rh / 2), STONE_LIGHT, grad=(0.1, 0.9))
	dw, dh = 1.5, 2.2
	for s in (-1, 1):
		p.box(((2 * rw - dw) / 2, 0.6, rh), (s * (dw / 2 + (2 * rw - dw) / 4), fy, zt + rh / 2), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((dw, 0.6, rh - dh), (0, fy, zt + dh + (rh - dh) / 2), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((dw + 0.5, 0.75, 0.3), (0, fy - 0.05, zt + dh + 0.12), STONE_DARK, grad=(0.1, 0.7))  # lintel
	p.box((dw, 0.1, dh), (0, fy + 0.35, zt + dh / 2), IRON, grad=(0.6, 1.0))  # the dark within
	p.box((2 * rw - 0.6, 2 * rd - 0.6, 0.1), (0, 0, zt + 0.05), IRON, grad=(0.6, 1.0))
	p.box((2 * rw + 0.4, 2 * rd + 0.4, 0.35), (0, 0, zt + rh + 0.15), STONE_WARM, grad=(0.0, 0.7))  # roof slabs
	p.box((2 * rw - 0.6, 2 * rd - 0.8, 0.5), (-0.3, 0, zt + rh + 0.55), STONE_LIGHT, grad=(0.0, 0.7))
	_elephant_head(p, (0, fy - 0.3, zt + dh + 0.75), 0.75, STONE_WARM, trunk=[(0, -0.35, -0.2), (0, -0.45, -0.55), (0.1, -0.5, -0.75)])
	# the fallen corner: a slope of blocks down to the ground
	for k in range(16):
		t = p.rng.random()
		x = 7.0 - p.rng.uniform(0, 3.5) + t * 1.8
		y = 7.0 - p.rng.uniform(0, 3.5) + t * 1.8
		z = (1 - t) * 4.5 + 0.3
		s = p.rng.uniform(0.7, 1.4)
		p.box((s, s * 0.8, s * 0.6), (x, y, z), STONE_LIGHT if k % 2 else STONE_WARM, rot=(p.rng.uniform(-25, 25), p.rng.uniform(-25, 25), p.rng.uniform(0, 90)), grad=(0.1, 0.9))
	for k in range(6):
		a = p.rng.uniform(0, math.tau)
		p.box((0.8, 0.6, 0.5), (8.8 + math.cos(a) * 1.5, 8.8 + math.sin(a) * 1.5, 0.2), STONE_WARM, rot=(0, 0, p.rng.uniform(0, 90)), grad=(0.1, 0.9))
	# moss along the cornices and on the steps
	for k in range(26):
		i = p.rng.randrange(4)
		hs, z0, cut = tiers[i]
		side = p.rng.randrange(3)
		if side == 0:
			x, y = p.rng.uniform(-hs + 0.5, hs - 0.5), -hs
			if abs(x) < 2.4:
				x = math.copysign(2.9, x)
		elif side == 1:
			x, y = -hs, p.rng.uniform(-hs + 0.5, hs - 0.5)
		else:
			x, y = p.rng.uniform(-hs + 0.5, hs - cut - 0.5), hs
		p.blob((p.rng.uniform(1.0, 2.2), p.rng.uniform(0.6, 1.0), 0.35), (x, y, z0 + TH + 0.05), MOSS if k % 3 else LEAF,
			   rot=(0, 0, 0 if side != 1 else 90), segs=(8, 4), grad=(0.1, 0.8))
	for k in range(5):
		p.blob((1.0, 0.5, 0.18), (p.rng.uniform(-1.0, 1.0), y_top - run + 1.0 + k * 1.5, k * 0.6 + 0.9), MOSS, segs=(6, 4), grad=(0.1, 0.8))
	# roots: from a mound of growth on the roof, down over the tiers
	for k, (x, y, sx) in enumerate(((-1.2, 0.6, 2.0), (0.6, 0.9, 1.5), (-0.3, -0.8, 1.2))):
		p.blob((sx, sx * 0.9, 0.7), (x, y, zt + rh + 0.85), LEAF if k % 2 else PINE, segs=(8, 5), grad=(0.3, 1.0))
	p.seg((-1.2, 0.6, zt + rh + 0.6), (-1.5, 0.8, zt + rh + 1.6), 0.18, 0.08, WOOD, sides=6, grad=(0.2, 1.0))
	p.rock((1.8, 1.7, 1.1), (-1.5, 0.8, zt + rh + 1.9), PINE, grad=(0.3, 1.0))
	for side, (dx, dy) in enumerate(((-1, 0), (-1, 0), (0, 1), (-1, 0), (0, 1))):
		off = (-0.8, 1.2, -1.5, -2.6, 0.5)[side]
		pts = [(-1.2 + off * abs(dy), 0.6 + off * abs(dx), zt + rh + 0.4)]
		for i in (3, 2, 1, 0):
			hs, z0, _ = tiers[i]
			edge = hs + 0.15
			x = dx * edge if dx else max(-hs + 0.4, min(hs - 0.4, off * 1.6))
			y = dy * edge if dy else max(-hs + 0.4, min(hs - 0.4, off * 1.6))
			pts.append((x, y, z0 + TH + 0.15))
			pts.append((x + dx * 0.15, y + dy * 0.15, z0 + 0.3))
		pts.append((pts[-1][0] + dx * 1.4, pts[-1][1] + dy * 1.4, -0.2))
		_chain(p, pts, 0.24, 0.12, WOOD, sides=5, grad=(0.2, 1.0))
	for k in range(9):  # vines off the cornices
		i = p.rng.randrange(1, 4)
		hs, z0, cut = tiers[i]
		x = p.rng.uniform(-hs + 0.3, hs - cut - 0.3)
		if abs(x) < 2.4:
			x = -3.0
		_vine(p, (x, -hs - 0.2, z0 + TH - 0.1), p.rng.uniform(1.2, 2.4), p.rng, r=0.035)
	obj = p.build(bevel=0.06)
	pieces = []
	for s in (-1, 1):  # KayKit pillars flank the stair's foot
		pieces += kaykit("pillar", (s * 2.9, y_top - run - 0.4, 0), 0.0, (0.75, 0.75, 0.9))
	pieces += kaykit("rubble_large", (8.3, 6.5, 0), 0.6)
	pieces += kaykit("rubble_large", (-6.0, -8.2, 0), 2.1)
	pieces += kaykit("rubble_half", (5.5, 8.6, 0), 1.2)
	return join_into(obj, pieces)


def temple_arch_ruin():
	"""A broken stone archway, about 5 m tall and 5 m wide, facing -Y: two
	block piers, the arch standing on the left and fallen away on the right,
	its stones in the moss; a root wraps the left pier. Collide it as a mesh."""
	p = Prop("temple_arch_ruin", 147)
	for s in (-1, 1):
		x = s * 1.9
		p.box((1.3, 1.3, 0.35), (x, 0, 0.17), STONE_DARK, grad=(0.2, 0.9))
		for k in range(3):
			if s > 0 and k == 2:
				p.box((1.0, 1.0, 0.7), (x + 0.05, 0.02, 0.35 + k * 1.05 + 0.35), STONE_LIGHT, rot=(0, 0, 6), grad=(0.1, 0.9))
				continue
			p.box((1.05, 1.05, 1.0), (x + p.rng.uniform(-0.04, 0.04), 0, 0.35 + k * 1.05 + 0.5), STONE_WARM if k % 2 else STONE_LIGHT,
				  rot=(0, 0, p.rng.uniform(-3, 3)), grad=(0.1, 0.9))
		if s < 0:
			p.box((1.3, 1.3, 0.25), (x, 0, 3.55), STONE_DARK, grad=(0.1, 0.7))
	# the arch: voussoirs on a half circle from pier to pier, the right three fallen
	r, cz = 1.9, 3.7
	for k in range(7):
		a = math.pi - (k + 0.5) * math.pi / 7
		if k >= 4:
			continue
		x, z = math.cos(a) * r, cz + math.sin(a) * r
		p.box((0.62, 1.0, 0.8), (x, 0, z), STONE_LIGHT if k % 2 else STONE_WARM, rot=(0, -math.degrees(a) + 90, 0), grad=(0.05, 0.8))
	for k, (x, y, rz) in enumerate(((2.8, -1.4, 20), (3.6, 0.6, 70), (1.4, -2.2, 40))):  # the fallen ones
		p.box((0.62, 1.0, 0.8), (x, y, 0.3), STONE_LIGHT, rot=(p.rng.uniform(-15, 15), 90, rz), grad=(0.05, 0.8))
	for k in range(6):
		p.blob((p.rng.uniform(0.6, 1.1), p.rng.uniform(0.5, 0.9), 0.25), (p.rng.uniform(-2.5, 2.5), p.rng.uniform(-0.5, 0.5), [3.7, 5.2, 0.4, 0.4, 5.5, 3.6][k]),
			   MOSS if k % 2 else LEAF, segs=(6, 4), grad=(0.1, 0.8))
	pts = []  # a root spiraling down the left pier into the ground
	for j in range(9):
		t = j / 8
		a = t * math.tau * 1.2
		pts.append((-1.9 + math.cos(a) * 0.62, math.sin(a) * 0.62, 5.3 - t * 5.2))
	pts.append((-3.4, -0.9, -0.2))
	_chain(p, pts, 0.18, 0.12, WOOD, sides=5, grad=(0.2, 1.0))
	for k in range(4):
		_vine(p, (-1.4 + k * 0.5, 0.0, 5.0 - k * 0.3), p.rng.uniform(1.4, 2.8), p.rng, r=0.03)
	return p.build(bevel=0.06)


def jalendra_head_fallen():
	"""The head of a colossal statue of Jalendra, fallen and half sunk in the
	mud: about 4 m tall above the ground, 7 m from ear to ear, facing -Y, its
	left tusk whole, the right snapped off and lying beside it. Collide as a box
	or mesh."""
	p = Prop("jalendra_head_fallen", 148)
	s = 3.4
	p.blob((1.25 * s, 1.1 * s, 1.1 * s), (0, 0, 0.9), STONE_LIGHT, rot=(8, 14, 0), segs=(12, 8), grad=(0.05, 0.85))
	p.blob((0.95 * s, 0.4 * s, 0.4 * s), (0, -0.4 * s, 0.9 + 0.45 * s), STONE_LIGHT, rot=(8, 14, 0), segs=(10, 6), grad=(0.05, 0.6))  # brow
	for x, tilt in ((-1, -30), (1, 10)):
		p.blob((1.1 * s, 0.22 * s, 1.2 * s), (x * 0.95 * s, 0.1 * s, 0.9 + x * 0.35), STONE_WARM, rot=(0, tilt, x * -15), segs=(12, 6), grad=(0.1, 0.8))
		p.blob((0.18 * s, 0.1 * s, 0.13 * s), (x * 0.32 * s, -0.52 * s, 0.9 + 0.2 * s + x * 0.1), IRON, segs=(6, 4))
	# a headdress band of carved plates, gold worn to stone
	for k in range(7):
		a = math.radians(-60 + k * 20)
		p.box((0.6, 0.35, 0.5), (math.sin(a) * 0.62 * s, -math.cos(a) * 0.45 * s, 0.9 + 0.62 * s), GOLD if k == 3 else STONE_WARM,
			  rot=(20, 14, -math.degrees(a)), grad=(0.1, 0.7))
	trunk = [(0, -0.55 * s, 0.9), (0.1, -0.75 * s, 0.35), (0.3, -1.05 * s, 0.1), (0.9, -1.35 * s, 0.15), (1.4, -1.45 * s, 0.35), (1.6, -1.3 * s, 0.5)]
	_chain(p, trunk, 0.28 * s, 0.1 * s, STONE_LIGHT, sides=8, grad=(0.1, 0.8))
	_chain(p, [(-0.35 * s, -0.5 * s, 0.6), (-0.55 * s, -0.95 * s, 0.7), (-0.7 * s, -1.25 * s, 1.2), (-0.65 * s, -1.4 * s, 1.8)], 0.1 * s, 0.03 * s, BONE, sides=7)
	p.seg((0.35 * s, -0.5 * s, 0.6), (0.48 * s, -0.75 * s, 0.62), 0.1 * s, 0.085 * s, BONE, sides=7)  # the snapped tusk
	p.seg((0.48 * s, -0.75 * s, 0.62), (0.5 * s, -0.78 * s, 0.63), 0.085 * s, 0.04 * s, BONE, sides=7, jitter=0.05)
	_chain(p, [(2.6, -2.6, 0.2), (3.4, -3.8, 0.25), (3.7, -4.8, 0.4)], 0.28, 0.08, BONE, sides=7)  # its broken end in the mud
	for k in range(10):  # moss
		a = p.rng.uniform(-1.2, 1.2)
		p.blob((p.rng.uniform(0.9, 1.8), p.rng.uniform(0.7, 1.4), 0.3), (math.sin(a) * 0.5 * s, math.cos(a) * 0.35 * s, 0.9 + p.rng.uniform(0.5, 0.95) * s),
			   MOSS if k % 3 else LEAF, rot=(0, 0, p.rng.uniform(0, 180)), segs=(8, 4), grad=(0.1, 0.8))
	for k in range(4):
		p.blob((0.9, 0.7, 0.25), (p.rng.uniform(-0.3, 1.5), -0.8 * s - k * 0.5, 0.2 + k * 0.1), MOSS, segs=(6, 4))
	for k in range(8):  # the mud it sank into
		a = k * math.tau / 8
		p.blob((2.4, 1.8, 0.4), (math.cos(a) * 1.3 * s, math.sin(a) * 1.0 * s, -0.05), WOOD, rot=(0, 0, math.degrees(a)), segs=(8, 4), grad=(0.6, 1.0))
	return p.build(bevel=0.06)


def troll_hut():
	"""A river-troll's hut: bent poles lashed into a lumpy dome, hung with
	hides, banked with mud, a rib-bone arch over the doorway (-Y). About 4.3 m
	tall and 5.4 m across. Collide it as a box."""
	p = Prop("troll_hut", 149)
	n, R, H = 10, 2.7, 4.0
	levels = [(1.0, 0.0), (0.92, 1.4), (0.66, 2.7), (0.3, 3.6), (0.06, 4.0)]
	poles = []
	for k in range(n):
		a = -math.pi / 2 + (k + 0.5) * math.tau / n
		pts = [(math.cos(a) * R * f + p.rng.uniform(-0.1, 0.1), math.sin(a) * R * f + p.rng.uniform(-0.1, 0.1), z) for f, z in levels]
		poles.append(pts)
		tip = (-math.cos(a) * 0.35, -math.sin(a) * 0.35, 4.6)
		_chain(p, pts + [tip], 0.1, 0.06, WOOD, sides=5, grad=(0.2, 1.0))
	for k in range(n):  # hides between the poles; the door gap is between the last and first
		a_, b_ = poles[k], poles[(k + 1) % n]
		for j in range(len(levels) - 1):
			if k == n - 1 and j < 2:
				continue
			sw = HIDE if (k + j) % 3 else WOOD_GRAY
			sag = 0.12
			p.poly([a_[j], b_[j], b_[j + 1], a_[j + 1]], [(0, 1, 2, 3)], sw, grad=(0.3, 1.0))
			p.poly([tuple(Vector(a_[j]) * (1 - sag * 0.2)), tuple(Vector(b_[j]) * (1 - sag * 0.2)), tuple(Vector(b_[j + 1]) * (1 - sag * 0.2)), tuple(Vector(a_[j + 1]) * (1 - sag * 0.2))],
				   [(0, 1, 2, 3)], IRON, grad=(0.6, 1.0))  # dark inside
	for k in range(14):  # the mud bank round the foot
		a = k * math.tau / 14
		if abs(math.atan2(math.sin(a + math.pi / 2), math.cos(a + math.pi / 2))) < 0.35:
			continue
		p.blob((1.4, 0.9, 0.9), (math.cos(a) * R * 1.02, math.sin(a) * R * 1.02, 0.2), WOOD, rot=(0, 0, math.degrees(a) + 90), segs=(8, 5), grad=(0.3, 1.0))
	for s in (-1, 1):  # rib bones arched over the door
		_chain(p, [(s * 0.9, -R - 0.2, -0.1), (s * 1.0, -R - 0.35, 1.5), (s * 0.6, -R - 0.3, 2.5), (s * 0.05, -R - 0.2, 2.9)], 0.13, 0.07, BONE, sides=6, grad=(0.0, 0.6))
	p.blob((0.55, 0.6, 0.45), (0, -R - 0.35, 2.95), BONE, grad=(0.0, 0.6))  # a skull at the top
	for x in (-0.13, 0.13):
		p.blob((0.12, 0.08, 0.1), (x, -R - 0.63, 3.0), IRON, segs=(5, 3))
	for s in (-1, 1):  # lower tusks
		p.seg((s * 0.14, -R - 0.55, 2.8), (s * 0.2, -R - 0.7, 3.15), 0.05, 0.01, BONE, sides=4)
	p.seg((1.6, -R - 0.6, -0.2), (1.6, -R - 0.6, 2.0), 0.06, 0.05, WOOD, sides=5)  # a stake by the door, with a fish skull
	p.blob((0.3, 0.55, 0.22), (1.6, -R - 0.6, 2.1), BONE, grad=(0.0, 0.6))
	for k in range(3):
		p.seg((1.45 + k * 0.15, -R - 0.55, 2.1), (1.45 + k * 0.15, -R - 0.65, 1.7), 0.02, 0.01, BONE, sides=3)
	for k in range(5):  # bones strung on the side
		a = -0.3 + k * 0.18
		p.seg((math.cos(a) * R * 0.95, math.sin(a) * R * 0.95, 1.9), (math.cos(a) * R * 1.0, math.sin(a) * R * 1.0, 1.35), 0.05, 0.04, BONE, sides=4)
	return p.build(bevel=0.03)


def troll_totem():
	"""A river-troll totem: a thick pole of stacked skulls, a crossbar hung with
	bones and hide strips, on a heap of river stones. About 3.6 m, facing -Y."""
	p = Prop("troll_totem", 150)
	for k in range(7):
		a = k * math.tau / 7
		p.rock((0.6, 0.5, 0.4), (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.1), STONE_DARK, jitter=0.05)
	p.seg((0, 0, -0.2), (0.05, 0, 3.1), 0.2, 0.15, WOOD, sides=6, grad=(0.2, 1.0))
	p.seg((0, 0, 1.1), (0, 0, 1.35), 0.23, 0.23, CLOTH_RED, sides=6)  # a band of red paint
	for i, (z, s) in enumerate(((1.8, 0.55), (2.5, 0.6), (3.3, 0.8))):  # skulls, the troll's own on top
		p.blob((s, s * 0.95, s * 0.85), (0.04, -0.1, z), BONE, segs=(8, 6), grad=(0.0, 0.6))
		for x in (-1, 1):
			p.blob((s * 0.2, s * 0.1, s * 0.18), (0.04 + x * s * 0.2, -0.1 - s * 0.45, z + s * 0.08), IRON, segs=(5, 3))
		p.box((s * 0.6, s * 0.35, s * 0.2), (0.04, -0.1 - s * 0.3, z - s * 0.4), BONE, grad=(0.1, 0.7))  # jaw
		if i == 2:
			for x in (-1, 1):
				p.seg((0.04 + x * 0.22, -0.4, z - 0.35), (0.04 + x * 0.3, -0.55, z + 0.1), 0.06, 0.01, BONE, sides=5)  # tusks
				p.seg((0.04 + x * 0.3, 0.0, z + 0.25), (0.04 + x * 0.75, 0.1, z + 0.7), 0.07, 0.02, WOOD_GRAY, sides=4)  # antler-like horns
			p.box((0.5, 0.05, 0.08), (0.04, -0.52, z + 0.25), CLOTH_RED)  # war paint
	p.seg((-0.9, 0, 2.15), (0.95, 0, 2.2), 0.06, 0.06, WOOD, sides=5)
	for k, x in enumerate((-0.8, -0.45, 0.5, 0.85)):
		p.seg((x, 0, 2.15), (x + p.rng.uniform(-0.05, 0.05), 0, 1.5), 0.015, 0.015, HIDE, sides=3)
		if k % 2:
			p.seg((x, 0, 1.55), (x, 0, 1.15), 0.05, 0.04, BONE, sides=4)
		else:
			p.box((0.18, 0.03, 0.55), (x, 0, 1.3), HIDE, grad=(0.2, 0.9))
	return p.build(bevel=0.02)


def _waterfall(p, water):
	"""Shared layout of the waterfall: rock (water=False) or water (water=True)."""
	lip = 8.0
	if not water:
		for i, z in enumerate((0.8, 2.6, 4.4, 6.2, 7.6)):  # the cliff: rows of big rocks either side of the chute
			for x in (-5.0, -3.2, 3.2, 5.0, -1.6, 1.6):
				if abs(x) < 2 and z > 7:
					continue
				sx = p.rng.uniform(2.2, 3.0)
				y = 1.6 if abs(x) < 2 else 1.0 + p.rng.uniform(-0.3, 0.4)
				p.rock((sx, 2.8, 2.2), (x + p.rng.uniform(-0.2, 0.2), y, z), STONE_DARK if (i + int(x)) % 2 else STONE_LIGHT,
					   rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.05, 0.9))
		for x in (-1.6, 0.0, 1.6):  # the lip the water spills over
			p.box((1.9, 3.0, 0.8), (x, 1.2, lip - 0.4), STONE_DARK, rot=(0, 0, p.rng.uniform(-6, 6)), grad=(0.1, 0.8))
		for x in (-1.8, 1.8):  # banks of the stream above
			p.rock((1.6, 3.4, 1.0), (x, 1.8, lip + 0.2), STONE_LIGHT, grad=(0.05, 0.8))
		for k in range(12):  # moss on the rocks, ferns on the ledges
			x = p.rng.choice((-1, 1)) * p.rng.uniform(2.0, 5.5)
			p.blob((p.rng.uniform(1.0, 1.8), 1.2, 0.35), (x, p.rng.uniform(0.2, 0.9), p.rng.uniform(1.8, 8.6)), MOSS if k % 3 else LEAF, segs=(8, 4), grad=(0.1, 0.8))
		for k in range(11):  # the rim of the splash pool
			a = math.pi + k * math.pi / 10
			x, y = math.cos(a) * 3.4, -2.2 + math.sin(a) * 2.6
			p.rock((1.3, 1.0, 0.7), (x, y, 0.1), STONE_DARK if k % 2 else STONE_LIGHT, rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.05, 0.9))
		for k in range(5):
			_vine(p, (p.rng.choice((-1, 1)) * p.rng.uniform(1.4, 3.5), -0.5, lip - p.rng.uniform(0, 1.0)), p.rng.uniform(1.5, 3.2), p.rng, r=0.03)
		return
	# the falling sheet: a strip that leaves the lip, bows out and drops into the pool
	prof = [(0.0, -0.1, lip + 0.05), (0.1, -0.6, lip - 0.35), (0.25, -0.95, lip - 1.6), (0.5, -1.15, 4.0), (0.8, -1.25, 1.2), (1.0, -1.3, 0.1)]
	for (ta, ya, za), (tb, yb, zb) in zip(prof, prof[1:]):
		wa, wb = 1.1 + 0.4 * ta, 1.1 + 0.4 * tb
		p.poly([(-wa, ya, za), (wa, ya, za), (wb, yb, zb), (-wb, yb, zb)], [(0, 1, 2, 3)], WATER, grad=(0.0, 0.7))
	for k in range(6):  # foam streaks down the face
		x = -1.0 + k * 0.4 + p.rng.uniform(-0.1, 0.1)
		w = p.rng.uniform(0.05, 0.09)
		for (ta, ya, za), (tb, yb, zb) in zip(prof[1:], prof[2:]):
			xa, xb = x * (1.1 + 0.4 * ta) / 1.1, x * (1.1 + 0.4 * tb) / 1.1
			p.poly([(xa - w, ya - 0.03, za), (xa + w, ya - 0.03, za), (xb + w, yb - 0.03, zb), (xb - w, yb - 0.03, zb)], [(0, 1, 2, 3)], CLOTH_WHITE, grad=(0.0, 0.3))
	p.poly([(-1.1, -0.1, lip + 0.05), (1.1, -0.1, lip + 0.05), (1.1, 3.0, lip + 0.1), (-1.1, 3.0, lip + 0.1)], [(0, 1, 2, 3)], WATER, grad=(0.1, 0.5))  # the stream above
	p.seg((0, -2.2, 0.0), (0, -2.2, 0.15), 3.2, 3.2, WATER, sides=16, grad=(0.1, 0.6))  # the pool
	for k in range(9):  # spray where it lands
		p.blob((p.rng.uniform(0.5, 0.9), p.rng.uniform(0.4, 0.7), p.rng.uniform(0.25, 0.45)), (p.rng.uniform(-1.4, 1.4), -1.3 + p.rng.uniform(-0.5, 0.2), 0.2),
			   CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.4))


def waterfall():
	"""A small cascade in a cliff face, about 8.6 m tall and 11 m wide, facing
	-Y: the rock only (cliff, spill lip, splash pool rim). Place
	`waterfall_water` at the same spot for the water. Collide as a mesh."""
	p = Prop("waterfall", 151)
	_waterfall(p, False)
	return p.build()


def waterfall_water():
	"""The water for `waterfall` (same origin): the falling sheet with foam
	streaks, the stream above the lip and a 3.2 m splash pool. No collision."""
	p = Prop("waterfall_water", 151)
	_waterfall(p, True)
	return p.build()


# ---------------------------------------------------------------- Rainhold (stilt city)
# Walkable decks follow boardwalk's convention: the walking surface is the
# prop's origin (local height 0), pilings run 4 m down. Collide them as "mesh".

def _deck_planks(p, hx, hy, across_x=True, n=None):
	"""Planks covering x in [-hx, hx], y in [-hy, hy], tops exactly at 0."""
	long_, short = (2 * hx, 2 * hy) if across_x else (2 * hy, 2 * hx)
	n = n or int(short / 0.3)
	for k in range(n):
		c = -short / 2 + (k + 0.5) * short / n
		sw = WOOD_GRAY if p.rng.random() < 0.3 else WOOD
		length = long_ + p.rng.uniform(-0.05, 0.0)
		off = p.rng.uniform(-0.02, 0.02)
		if across_x:
			p.box((length, short / n - 0.03, 0.08), (off, c, -0.04), sw, rot=(0, 0, p.rng.uniform(-0.3, 0.3)), grad=(0.1, 0.6))
		else:
			p.box((short / n - 0.03, length, 0.08), (c, off, -0.04), sw, rot=(0, 0, p.rng.uniform(-0.3, 0.3)), grad=(0.1, 0.6))


def stilt_platform():
	"""A 9 x 9 m timber deck on pilings, for Rainhold. The deck's top is the
	origin (where you walk); an edge beam runs round it flush with the deck,
	pilings go 4 m down into the lagoon. Tiles edge to edge with itself,
	stilt_walkway and rope_bridge."""
	p = Prop("stilt_platform", 161)
	h = 4.5
	_deck_planks(p, h, h, True)
	for x in (-3.4, -1.1, 1.1, 3.4):  # joists under the planks
		p.box((0.16, 2 * h - 0.2, 0.22), (x, 0, -0.19), WOOD, grad=(0.3, 1.0))
	for s in (-1, 1):  # the edge beam, top flush with the deck
		p.box((2 * h, 0.2, 0.36), (0, s * (h - 0.1), -0.18), WOOD, grad=(0.2, 0.9))
		p.box((0.2, 2 * h, 0.36), (s * (h - 0.1), 0, -0.18), WOOD, grad=(0.2, 0.9))
	posts = (-4.2, -1.4, 1.4, 4.2)
	for x in posts:
		for y in posts:
			p.seg((x, y, -4.0), (x, y, -0.1), 0.15, 0.13, WOOD, sides=6, grad=(0.2, 1.0))
	for s in (-1, 1):  # cross bracing on the outer rows
		for i in range(3):
			a, b = posts[i], posts[i + 1]
			p.seg((a, s * 4.2, -0.5), (b, s * 4.2, -2.4), 0.06, 0.06, WOOD_GRAY, sides=4)
			p.seg((s * 4.2, a, -0.5), (s * 4.2, b, -2.4), 0.06, 0.06, WOOD_GRAY, sides=4)
	return p.build(bevel=0.02)


def _rope(p, a, b, sag, r=0.025, n=6, swatch=HIDE):
	"""A rope from a to b sagging `sag` meters at the middle."""
	a, b = Vector(a), Vector(b)
	pts = []
	for k in range(n + 1):
		t = k / n
		v = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
		pts.append(tuple(v))
	_chain(p, pts, r, r, swatch, sides=4, grad=(0.1, 0.7))


def stilt_walkway():
	"""A 3 x 9 m walkway on pilings, running along Y: planks across, posts and
	sagging rope rails along both long sides, both ends open. Deck top at the
	origin, like boardwalk; posts go 4 m down."""
	p = Prop("stilt_walkway", 162)
	hx, hy = 1.5, 4.5
	_deck_planks(p, hx, hy, True)
	for x in (-1.2, 1.2):
		p.box((0.16, 2 * hy, 0.2), (x, 0, -0.18), WOOD, grad=(0.3, 1.0))
	posts = (-4.25, -1.45, 1.45, 4.25)
	for s in (-1, 1):
		x = s * 1.38
		for y in posts:
			p.seg((x, y, -4.0), (x, y, 1.1), 0.1, 0.09, WOOD, sides=6, grad=(0.2, 1.0))
			p.seg((x, y, 1.1), (x, y, 1.18), 0.12, 0.12, WOOD_GRAY, sides=6)
		for a, b in zip(posts, posts[1:]):
			_rope(p, (x, a, 1.02), (x, b, 1.02), 0.12)
			_rope(p, (x, a, 0.55), (x, b, 0.55), 0.08)
	return p.build(bevel=0.02)


def rope_bridge():
	"""A 3 x 12 m rope bridge running along Y between two decks: planks on
	ropes, rope rails on four end posts. Its ends are at deck height (the
	origin) and it dips only 8 cm at the middle, so it walks like a floor.
	No pilings: it spans open water. Collide it as a mesh."""
	p = Prop("rope_bridge", 163)
	half, sag = 6.0, 0.08

	def dz(y):
		return -sag * (1.0 - (y / half) ** 2)

	n = 36
	for k in range(n):
		y0 = -half + k * 2 * half / n + 0.03
		y1 = -half + (k + 1) * 2 * half / n - 0.03
		ym = (y0 + y1) / 2
		tilt = math.degrees(math.atan2(dz(y1) - dz(y0), y1 - y0))
		w = 2.6 + p.rng.uniform(-0.12, 0.05)
		p.box((w, y1 - y0, 0.07), (p.rng.uniform(-0.04, 0.04), ym, dz(ym) - 0.035), WOOD_GRAY if k % 4 == 0 else WOOD,
			  rot=(tilt, 0, p.rng.uniform(-1.0, 1.0)), grad=(0.1, 0.6))
	for x in (-1.2, 1.2):  # the ropes the planks are tied onto
		pts = [(x, -half + k * half / 6, dz(-half + k * half / 6) - 0.09) for k in range(13)]
		_chain(p, pts, 0.04, 0.04, HIDE, sides=4)
	for sx in (-1, 1):
		x = sx * 1.45
		for sy in (-1, 1):
			y = sy * (half - 0.15)
			p.seg((x, y, -1.2), (x, y, 1.35), 0.13, 0.11, WOOD, sides=6, grad=(0.2, 1.0))
			p.seg((x, y, 1.35), (x, y, 1.45), 0.15, 0.15, WOOD_GRAY, sides=6)
			for z in (0.4, 0.9):
				p.seg((x - 0.1 * sx, y, z), (x + 0.1 * sx, y, z), 0.14, 0.14, HIDE, sides=6)  # lashing
		top = [(x, -half + 0.15 + k * (2 * half - 0.3) / 10, 0.0) for k in range(11)]
		top = [(tx, ty, 1.25 - 0.3 * (1 - (ty / half) ** 2)) for tx, ty, _ in top]
		_chain(p, top, 0.035, 0.035, HIDE, sides=4)
		for tx, ty, tz in top[1:-1]:  # suspenders from the rail down to the plank ropes
			p.seg((tx, ty, tz), (sx * 1.2, ty, dz(ty) - 0.09), 0.015, 0.015, HIDE, sides=3)
	return p.build(bevel=0.015)


def _longhouse(p, w, d, porch, wall_h, rise, sweep, door=(1.6, 2.4), windows=True):
	"""A Rainhold timber house: floor top at the origin (so it stands on a
	deck), vertical plank walls, an open porch at the front (-Y) under the
	front slope, and a steep thatched roof whose ridge and eaves sweep up at the
	ends into horned finials. Ridge along X."""
	hw, hd = w / 2, d / 2
	front = -hd + porch
	ovx, ov = 1.1, 0.7
	X = hw + ovx

	def lift(x):
		return (min(abs(x), X) / X) ** 2

	def roof_z(x, y):
		ridge = wall_h + rise + sweep * lift(x)
		wall_line = wall_h + sweep * 0.4 * lift(x)
		return ridge - (ridge - wall_line) * abs(y) / hd

	# floor and its pilings
	_deck_planks(p, hw, hd, True)
	for x in [-hw + 0.3 + k * (w - 0.6) / max(1, round(w / 3.0)) for k in range(int(round(w / 3.0)) + 1)]:
		for y in (-hd + 0.3, front, hd - 0.3):
			p.seg((x, y, -4.0), (x, y, -0.08), 0.13, 0.12, WOOD, sides=6, grad=(0.2, 1.0))
	for s in (-1, 1):
		p.box((w, 0.2, 0.3), (0, s * (hd - 0.1), -0.15), WOOD, grad=(0.2, 0.9))
		p.box((0.2, d, 0.3), (s * (hw - 0.1), 0, -0.15), WOOD, grad=(0.2, 0.9))

	def wall(x0, x1, fixed, along_x, openings=()):
		n = max(2, int(abs(x1 - x0) / 0.34))
		for k in range(n):
			c = x0 + (k + 0.5) * (x1 - x0) / n
			x, y = (c, fixed) if along_x else (fixed, c)
			top = roof_z(x, y) - 0.05
			sw = WOOD_GRAY if p.rng.random() < 0.3 else WOOD
			size = (abs(x1 - x0) / n - 0.02, 0.1) if along_x else (0.1, abs(x1 - x0) / n - 0.02)
			spans = [(0.0, top)]
			for o0, o1, z0, z1 in openings:
				if o0 < c < o1:
					spans = [(0.0, z0), (z1, top)] if z0 > 0 else [(z1, top)]
			for a, b in spans:
				if b - a > 0.02:
					p.box((size[0], size[1], b - a), (x, y, (a + b) / 2), sw, grad=(0.15, 0.9))

	dw, dh = door
	wall(-hw, hw, front, True, [(-dw / 2, dw / 2, 0.0, dh)] + ([(-hw * 0.6 - 0.5, -hw * 0.6 + 0.5, 1.0, 1.9), (hw * 0.6 - 0.5, hw * 0.6 + 0.5, 1.0, 1.9)] if windows and w > 8 else []))
	wall(-hw, hw, hd, True, [(-hw * 0.5 - 0.5, -hw * 0.5 + 0.5, 1.0, 1.9), (hw * 0.5 - 0.5, hw * 0.5 + 0.5, 1.0, 1.9)] if windows else [])
	for s in (-1, 1):
		wall(front, hd, s * hw, False, [((front + hd) / 2 - 0.5, (front + hd) / 2 + 0.5, 1.0, 1.9)] if windows else [])
	p.box((dw + 0.4, 0.16, 0.25), (0, front - 0.05, dh + 0.12), WOOD, grad=(0.3, 1.0))  # lintel
	for s in (-1, 1):
		p.box((0.18, 0.16, dh), (s * (dw / 2 + 0.09), front - 0.06, dh / 2), WOOD, grad=(0.3, 1.0))
	for x in (-hw, hw):  # corner posts
		for y in (front, hd):
			p.seg((x, y, 0), (x, y, roof_z(x, y)), 0.13, 0.12, WOOD, sides=6, grad=(0.2, 1.0))
	# the porch: posts at the front edge up to the roof, open between them (the
	# guildmasters and merchants stand on these porches: players walk straight up),
	# a low rail only at the two ends
	n_posts = max(2, int(round(w / 3.0)) + 1)
	px = [-hw + 0.2 + k * (w - 0.4) / (n_posts - 1) for k in range(n_posts)]
	for x in px:
		p.seg((x, -hd + 0.2, 0), (x, -hd + 0.2, roof_z(x, -hd + 0.2) - 0.05), 0.12, 0.11, WOOD, sides=6, grad=(0.2, 1.0))
	for s in (-1, 1):
		p.box((0.1, porch - 0.2, 0.1), (s * (hw - 0.0), -hd + porch / 2 + 0.1, 0.85), WOOD_GRAY, grad=(0.2, 0.8))
	# the roof: a sheet on each side, bundles of thatch in courses, the ridge beam and finials
	Y = hd + ov
	nx = 14
	xs = [-X + k * 2 * X / nx for k in range(nx + 1)]
	for s in (-1, 1):
		for a, b in zip(xs, xs[1:]):
			p.poly([(a, 0, roof_z(a, 0) + 0.02), (b, 0, roof_z(b, 0) + 0.02), (b, s * Y, roof_z(b, Y)), (a, s * Y, roof_z(a, Y))],
				   [(0, 1, 2, 3)], BAMBOO, grad=(0.2, 0.9))
		for j in range(7):
			t = (j + 0.5) / 7
			y = s * Y * t
			pts = [(x, y, roof_z(x, y) + 0.06) for x in xs]
			_chain(p, pts, 0.07, 0.07, HIDE if j % 2 else BAMBOO, sides=4, grad=(0.1, 0.6))
	ridge = [(x, 0, roof_z(x, 0) + 0.1) for x in xs]
	_chain(p, ridge, 0.14, 0.14, WOOD, sides=6)
	for s in (-1, 1):
		x0, _, z0 = ridge[-1] if s > 0 else ridge[0]
		_chain(p, [(x0, 0, z0), (x0 + s * 0.5, 0, z0 + 0.6), (x0 + s * 0.6, 0, z0 + 1.3)], 0.13, 0.04, WOOD, sides=6)
		p.blob((0.2, 0.2, 0.25), (x0 + s * 0.6, 0, z0 + 1.35), GOLD, grad=(0.0, 0.5))
		for y in (-hd * 0.5, hd * 0.5):  # gable-end braces under the swept eave
			p.seg((s * hw, y, roof_z(hw, y) - 0.4), (s * (X - 0.1), y, roof_z(X - 0.1, y) - 0.05), 0.06, 0.05, WOOD, sides=4)


def stilt_hall():
	"""Rainhold's great longhouse: 14 x 9 m, a 2.5 m open porch along the front
	(-Y), plank walls 3 m high with an open doorway, a steep thatch roof about
	8 m at the ridge sweeping up into horned ends (10 m with finials). Its floor
	top is the origin: stand it on a stilt_platform (or on its own pilings,
	which run 4 m down). Collide it as a mesh."""
	p = Prop("stilt_hall", 164)
	_longhouse(p, 14.0, 9.0, 2.5, 3.0, 4.3, 1.4)
	return p.build(bevel=0.03)


def stilt_house():
	"""A Rainhold home, 6 x 6 m with a 1.5 m porch at the front (-Y), the same
	swept thatch roof as the hall at a smaller scale (about 6 m to the ridge).
	Floor top at the origin, pilings 4 m down. Collide it as a mesh."""
	p = Prop("stilt_house", 165)
	_longhouse(p, 6.0, 6.0, 1.5, 2.5, 2.9, 0.8, door=(1.3, 2.2))
	return p.build(bevel=0.03)


def jalendra_shrine():
	"""Rainhold's bindstone: Jalendra the Tide-Trunked, a stone elephant about
	6 m to the top of the head, trunk raised high and pouring an arc of water
	into the round basin (9 m across) he stands in. Four short pillars on the
	rim hold bowls of glowing water. Faces -Y. Collide it as a mesh or a box."""
	p = Prop("jalendra_shrine", 166)
	R = 4.1  # the rim's outside edge is 4.5 m out: it fits one stilt_platform
	p.seg((0, 0, -0.2), (0, 0, 0.15), R + 0.2, R + 0.2, STONE_DARK, sides=20, grad=(0.3, 1.0))
	for k in range(20):  # the basin wall
		a = k * math.tau / 20
		p.box((1.5, 0.55, 0.85), (math.cos(a) * R, math.sin(a) * R, 0.42), STONE_LIGHT, rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.85))
		p.box((1.6, 0.75, 0.14), (math.cos(a) * R, math.sin(a) * R, 0.9), STONE_WARM, rot=(0, 0, math.degrees(a) + 90), grad=(0.0, 0.6))
	p.seg((0, 0, 0.15), (0, 0, 0.62), R - 0.2, R - 0.2, WATER, sides=20, grad=(0.1, 0.6))
	cy = 1.6  # the statue stands a little back, so the water lands in front of it
	p.seg((0, cy, 0.0), (0, cy, 1.3), 2.1, 2.0, STONE_WARM, sides=8, grad=(0.1, 0.9), twist=22.5)
	p.seg((0, cy, 1.3), (0, cy, 1.45), 2.2, 2.2, STONE_LIGHT, sides=8, grad=(0.0, 0.6), twist=22.5)
	p.blob((2.4, 3.6, 2.2), (0, cy + 0.3, 3.3), STONE_LIGHT, segs=(14, 10), grad=(0.05, 0.8))  # body
	for x in (-0.75, 0.75):
		for y in (-1.0, 1.4):
			p.seg((x, cy + y, 1.4), (x, cy + y, 2.8), 0.46, 0.5, STONE_LIGHT, sides=8, grad=(0.2, 0.9))
			p.seg((x, cy + y, 1.4), (x, cy + y, 1.55), 0.52, 0.52, STONE_WARM, sides=8)
	p.box((2.5, 1.8, 0.1), (0, cy + 0.4, 4.4), WATER, grad=(0.0, 0.5))  # a saddle-cloth of blue with a gold hem
	for s in (-1, 1):
		p.box((0.1, 1.8, 1.2), (s * 1.22, cy + 0.4, 3.85), WATER, grad=(0.0, 0.5))
		p.box((0.12, 1.85, 0.12), (s * 1.24, cy + 0.4, 3.25), GOLD, glow=0.2)
	p.seg((0, cy + 2.0, 3.6), (0.1, cy + 2.4, 2.5), 0.08, 0.04, STONE_LIGHT, sides=5)  # tail
	hc = (0, cy - 1.85, 4.85)
	trunk = [(0, -0.45, -0.3), (0, -0.75, -0.1), (0, -0.95, 0.4), (0, -1.1, 0.95), (0, -1.3, 1.35), (0, -1.55, 1.5), (0, -1.75, 1.45)]
	_elephant_head(p, hc, 1.7, STONE_LIGHT, trunk=trunk)
	p.seg((0, hc[1] + 0.2, hc[2] + 0.85), (0, hc[1] + 0.05, hc[2] + 1.05), 0.55, 0.3, GOLD, sides=8, glow=0.25)  # a crown
	# the water: from the trunk's tip, a short rise then a long fall into the basin
	sx, sy, sz = hc[0], hc[1] - 1.8 * 1.7, hc[2] + 1.42 * 1.7
	arc = []
	for k in range(11):
		t = k / 10
		arc.append((sx, sy - 0.4 * t, sz + 0.35 * t - (sz + 0.35 - 0.6) * t ** 2))
	_chain(p, arc, 0.14, 0.26, WATER, sides=7, grad=(0.0, 0.5), glow=0.15)
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.5, 0.5, 0.3), (arc[-1][0] + math.cos(a) * 0.4, arc[-1][1] + math.sin(a) * 0.4, 0.66), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.4))
	for k in range(4):  # pillars with bowls on the rim
		a = math.pi / 4 + k * math.pi / 2
		x, y = math.cos(a) * R, math.sin(a) * R
		p.seg((x, y, 0.95), (x, y, 2.0), 0.3, 0.26, STONE_WARM, sides=8, grad=(0.1, 0.9))
		p.seg((x, y, 2.0), (x, y, 2.3), 0.18, 0.45, STONE_LIGHT, sides=10, grad=(0.1, 0.8))
		p.seg((x, y, 2.22), (x, y, 2.29), 0.38, 0.38, RUNE, sides=10, glow=1.2)
	return p.build(bevel=0.04)


def canoe():
	"""A dugout canoe hollowed from one log, about 5.2 m, bow toward -Y, both
	ends rising a little; waterline at the origin like rowboat. A paddle lies
	across it. No collision."""
	p = Prop("canoe", 167)
	L, W, D = 2.6, 0.42, 0.36
	nsec, nu = 16, 8

	def section(y, shrink, lift):
		t = abs(y) / L
		w = W * max(0.02, (1 - t ** 2.2)) ** 0.7 * shrink
		g = 0.24 + 0.22 * t ** 3
		dep = D * max(0.05, (1 - t ** 2.5)) ** 0.6 * shrink
		return [(math.cos(math.pi * i / (nu - 1)) * w, y, g - math.sin(math.pi * i / (nu - 1)) * dep + lift) for i in range(nu)]

	ys = [-L + 2 * L * k / nsec for k in range(nsec + 1)]
	outer = [section(y, 1.0, 0.0) for y in ys]
	inner = [section(y * 0.94, 0.8, 0.02) for y in ys]
	for grid, sw, grad in ((outer, WOOD, (0.1, 0.9)), (inner, WOOD_GRAY, (0.4, 1.0))):
		verts, faces = [], []
		for sec in grid:
			verts += sec
		for k in range(nsec):
			for i in range(nu - 1):
				a = k * nu + i
				faces.append((a, a + 1, a + nu + 1, a + nu))
		p.poly(verts, faces, sw, grad)
	for k in range(nsec):  # the gunwales: strips joining the outer and inner rims
		for i in (0, nu - 1):
			p.poly([outer[k][i], outer[k + 1][i], inner[k + 1][i], inner[k][i]], [(0, 1, 2, 3)], WOOD, grad=(0.0, 0.4))
	p.seg((-0.5, 0.3, 0.3), (0.55, -1.2, 0.34), 0.025, 0.025, WOOD, sides=5)  # the paddle
	p.box((0.22, 0.5, 0.03), (0.63, -1.42, 0.35), WOOD, rot=(0, 0, 35), grad=(0.1, 0.6))
	for y in (-1.2, 1.0):
		p.box((0.62, 0.18, 0.05), (0, y, 0.2), WOOD_GRAY, grad=(0.1, 0.6))
	return p.build(bevel=0.02)


# ---------------------------------------------------------------- tradeskill stations (city crafting)
# Clicked to open the combine window; each faces -Y (where the player stands),
# stands on the origin and is compact enough to collide as a box.

COPPER = (2, 0)    # the clay swatch reads as polished copper
GLASS = ((6, 2), (1, 2), (3, 1), (4, 1), (5, 2))  # blue, green, purple, magenta, amber


def _hoops(p, c, r, zs, swatch=IRON, axis="z", w=0.05):
	"""Iron bands around a round body centred at c: rings at heights (or depths) zs."""
	for z in zs:
		if axis == "z":
			a, b = (c[0], c[1], z - w / 2), (c[0], c[1], z + w / 2)
		else:
			a, b = (c[0], z - w / 2, c[2]), (c[0], z + w / 2, c[2])
		p.seg(a, b, r, r, swatch, sides=12, grad=(0.0, 0.6))


def oven():
	"""A baker's bread oven: a clay dome on a stone plinth, 1.8 m wide and 1.6 m
	to the dome, a chimney stub behind, an arched mouth to -Y with the ember bed
	glowing inside, loaves cooling on the apron and a peel leaning on the side."""
	p = Prop("oven", 171)
	cy = 0.12  # the dome sits back, leaving an apron in front of the mouth
	p.blob((1.62, 1.52, 1.9), (0, cy, 0.62), CLAY, segs=(14, 10), grad=(0.05, 0.85))
	for k in range(7):  # a few stones set in the clay
		a = -0.3 + k * 0.95
		z = 0.85 + (k % 3) * 0.22
		rr = 0.8 * math.sqrt(max(0.0, 1 - ((z - 0.62) / 0.95) ** 2))
		p.rock((0.22, 0.12, 0.14), (math.cos(a) * rr, cy + math.sin(a) * rr * 0.94, z), STONE_WARM,
			   rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.7), jitter=0.04)
	p.seg((0.18, cy + 0.42, 1.25), (0.2, cy + 0.44, 1.78), 0.17, 0.15, STONE_DARK, sides=6, grad=(0.1, 0.8))  # chimney
	p.seg((0.2, cy + 0.44, 1.74), (0.2, cy + 0.44, 1.84), 0.21, 0.21, STONE_LIGHT, sides=6, grad=(0.0, 0.6))
	p.seg((0.2, cy + 0.44, 1.8), (0.2, cy + 0.44, 1.845), 0.11, 0.11, IRON, sides=6)
	# the mouth: a stone arch built out from the dome, dark inside, embers on its floor
	fy = -0.72
	p.box((0.96, 0.44, 0.5), (0, fy + 0.2, 0.85), STONE_LIGHT, grad=(0.05, 0.8))
	p.seg((0, fy - 0.02, 1.1), (0, fy + 0.42, 1.1), 0.48, 0.48, STONE_LIGHT, sides=14, grad=(0.0, 0.7))
	for k in range(7):  # voussoirs round the arch
		a = math.pi * k / 6
		p.box((0.16, 0.1, 0.13), (math.cos(a) * 0.4, fy - 0.03, 0.98 + math.sin(a) * 0.4), STONE_WARM,
			  rot=(0, -math.degrees(a) + 90, 0), grad=(0.0, 0.6))
	p.box((0.56, 0.06, 0.34), (0, fy - 0.03, 0.8), IRON, grad=(0.6, 1.0))
	p.seg((0, fy - 0.06, 0.98), (0, fy + 0.0, 0.98), 0.28, 0.28, IRON, sides=12, grad=(0.6, 1.0))
	p.blob((0.52, 0.22, 0.1), (0, fy - 0.06, 0.66), EMBER, grad=(0.4, 0.9), glow=1.3)
	for k in range(6):  # glowing coals heaped on the oven floor
		x = -0.2 + k * 0.08
		p.blob((0.11, 0.1, 0.08), (x, fy - 0.1 - (k % 2) * 0.03, 0.69 + (k % 3) * 0.02), EMBER, segs=(6, 4), grad=(0.0, 0.6), glow=1.8)
	p.blob((0.3, 0.06, 0.12), (0, fy - 0.08, 0.74), FLAME, segs=(8, 4), grad=(0.0, 0.9), glow=1.0)
	# plinth: coursed stone with a log store under the mouth
	p.box((1.84, 1.66, 0.62), (0, 0.02, 0.31), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((1.92, 1.74, 0.08), (0, 0.02, 0.62), STONE_WARM, grad=(0.0, 0.6))
	for k in range(5):
		x = -0.72 + k * 0.36
		p.box((0.3, 0.05, 0.16), (x + (0.1 if k % 2 else 0), -0.82, 0.18 + (k % 2) * 0.2), STONE_DARK, grad=(0.3, 0.7))
	p.box((0.64, 0.06, 0.34), (0.38, -0.81, 0.28), IRON, grad=(0.6, 1.0))
	for k, (x, z) in enumerate(((0.2, 0.2), (0.38, 0.2), (0.56, 0.2), (0.29, 0.36), (0.47, 0.36))):
		p.seg((x, -0.86, z), (x, -0.6, z), 0.08, 0.08, WOOD, sides=6, grad=(0.3, 1.0))
		p.seg((x, -0.87, z), (x, -0.86, z), 0.065, 0.065, HIDE, sides=6)
	# bread cooling on the apron, and a peel against the side
	for x, y, s in ((-0.62, -0.62, 1.0), (-0.72, -0.4, 0.9), (0.62, -0.62, 0.95)):
		p.blob((0.34 * s, 0.22 * s, 0.16 * s), (x, y, 0.71), BAMBOO, segs=(8, 6), grad=(0.0, 0.8))
		for d in (-0.07, 0.07):  # scored crust
			p.box((0.03, 0.12 * s, 0.02), (x + d * s, y, 0.78), HIDE, rot=(0, 0, 15))
	p.seg((0.99, -0.35, 0.05), (0.99, 0.35, 1.45), 0.025, 0.025, WOOD, sides=5)
	p.box((0.03, 0.34, 0.38), (0.99, -0.46, 0.12), WOOD, rot=(-27, 0, 0), grad=(0.1, 0.7))
	return p.build(bevel=0.06)


def loom():
	"""A weaver's floor loom, 2 m wide: side frames and a castle beam, the warp
	sloping from the back beam down to the breast beam, half of it woven into
	striped red cloth that rolls up underneath, a bench at the front (-Y) and a
	basket of yarn."""
	p = Prop("loom", 172)
	X = 0.92
	back_y, front_y = 0.45, -0.3
	top = (back_y, 1.45)     # warp beam (y, z)
	breast = (front_y, 0.9)  # breast beam
	for s in (-1, 1):  # side frames
		x = s * X
		p.box((0.1, 0.1, 1.8), (x, back_y + 0.05, 0.9), WOOD, grad=(0.2, 1.0))
		p.box((0.1, 0.1, 0.95), (x, front_y, 0.47), WOOD, grad=(0.2, 1.0))
		p.box((0.12, 0.95, 0.1), (x, 0.08, 0.1), WOOD, grad=(0.3, 1.0))
		p.box((0.1, 0.9, 0.08), (x, 0.08, 0.95), WOOD_GRAY)
	p.box((2 * X + 0.14, 0.14, 0.14), (0, back_y + 0.05, 1.8), WOOD, grad=(0.1, 0.8))  # the castle
	for y, z in (top, breast):
		p.seg((-X, y, z), (X, y, z), 0.065, 0.065, WOOD_GRAY, sides=8)
	p.seg((-X, front_y + 0.06, 0.5), (X, front_y + 0.06, 0.5), 0.14, 0.14, CLOTH_RED, sides=10, grad=(0.1, 0.8))  # the cloth roll
	p.seg((-X, front_y + 0.2, 0.25), (X, front_y + 0.2, 0.25), 0.05, 0.05, WOOD, sides=6)  # treadle bar
	for x in (-0.2, 0.2):
		p.box((0.08, 0.5, 0.03), (x, front_y + 0.05, 0.12), WOOD_GRAY, rot=(12, 0, 0))
	# warp: back beam to breast beam; the front 45% is woven
	a = Vector((0, top[0], top[1] + 0.06))
	b = Vector((0, breast[0], breast[1] + 0.06))
	fell = b + (a - b) * 0.45
	n = 26
	w = 0.78
	for k in range(n):
		x = -w + 2 * w * k / (n - 1)
		p.seg((x, fell.y, fell.z), (x, a.y, a.z), 0.009, 0.009, CLOTH_WHITE, sides=3, grad=(0.0, 0.4))
	d = a - b
	ang = math.degrees(math.atan2(d.z, -d.y))
	mid = (b + fell) / 2
	L = (fell - b).length
	stripes = ((CLOTH_RED, 0.3), (GOLD, 0.08), (CLOTH_RED, 0.2), (WATER, 0.1), (CLOTH_RED, 0.32))
	t0 = 0.0
	for sw, f in stripes:
		c = b + (fell - b) * (t0 + f / 2)
		p.box((2 * w + 0.04, L * f, 0.025), (0, c.y, c.z), sw, rot=(-ang, 0, 0), grad=(0.0, 0.5))
		t0 += f
	# beater (reed in its frame) at the fell, and heddles hung from the castle
	p.box((2 * w + 0.12, 0.05, 0.05), (0, fell.y - 0.03, fell.z + 0.05), WOOD, grad=(0.1, 0.6))
	for s in (-1, 1):
		p.seg((s * (w + 0.06), fell.y - 0.03, fell.z + 0.05), (s * (w + 0.06), fell.y + 0.25, 1.75), 0.022, 0.022, WOOD, sides=4)
	hy = fell.y + (a.y - fell.y) * 0.45
	hz = fell.z + (a.z - fell.z) * 0.45
	for k, off in enumerate((-0.05, 0.07)):
		p.box((2 * w + 0.1, 0.035, 0.1), (0, hy + off, hz + off * 0.6), WOOD_GRAY, grad=(0.1, 0.5))
		for s in (-1, 1):
			p.seg((s * (w - 0.05), hy + off, hz + 0.05), (s * (w - 0.05), back_y + 0.05, 1.73), 0.008, 0.008, HIDE, sides=3)
	p.box((0.5, 0.05, 0.04), (0.1, fell.y - 0.12, fell.z + 0.02), WOOD, rot=(-ang, 0, 0))  # shuttle resting on the cloth
	# bench
	p.box((1.2, 0.36, 0.07), (-0.15, -0.78, 0.5), WOOD, grad=(0.1, 0.7))
	for x in (-0.65, 0.35):
		p.box((0.08, 0.3, 0.47), (x, -0.78, 0.235), WOOD_GRAY, grad=(0.2, 0.9))
	p.box((0.95, 0.05, 0.06), (-0.15, -0.78, 0.18), WOOD_GRAY)
	# yarn basket at the bench's end
	bx, by = 0.73, -0.72
	p.seg((bx, by, 0.0), (bx, by, 0.3), 0.19, 0.25, BAMBOO, sides=10, grad=(0.1, 0.9))
	p.seg((bx, by, 0.28), (bx, by, 0.33), 0.265, 0.265, WOOD, sides=10)
	for k, sw in enumerate((CLOTH_RED, GOLD, WATER, PETAL_PURPLE, LEAF)):
		ang2 = k * math.tau / 5 + 0.3
		r = 0.0 if k == 4 else 0.12
		p.blob((0.17, 0.17, 0.16), (bx + math.cos(ang2) * r, by + math.sin(ang2) * r, 0.35 + (0.07 if k == 4 else 0)), sw, segs=(8, 6), grad=(0.0, 0.6))
	p.blob((0.15, 0.15, 0.14), (bx - 0.02, by - 0.3, 0.07), WATER, segs=(8, 6), grad=(0.0, 0.6))  # one rolled off
	return p.build(bevel=0.06)


def brew_barrel():
	"""A brewer's and alchemist's station, 2 m wide: a big cask on its cradle
	with a tap, a copper still over a little firebox whose pipe coils down into
	a cooling worm, and a table of bottles and jars, some glowing faintly."""
	p = Prop("brew_barrel", 173)
	# the still, right-back, over a stone firebox
	sx, sy = 0.24, 0.3
	p.box((0.62, 0.62, 0.34), (sx, sy, 0.17), STONE_DARK, grad=(0.1, 0.9))
	p.box((0.3, 0.05, 0.14), (sx, sy - 0.3, 0.13), IRON, grad=(0.6, 1.0))
	p.blob((0.24, 0.05, 0.06), (sx, sy - 0.32, 0.1), EMBER, glow=1.2)
	p.blob((0.72, 0.72, 0.66), (sx, sy, 0.62), COPPER, segs=(14, 8), grad=(0.0, 0.7))
	_hoops(p, (sx, sy), 0.345, (0.5,), COPPER, w=0.04)
	p.seg((sx, sy, 0.85), (sx, sy, 1.12), 0.2, 0.08, COPPER, sides=10, grad=(0.0, 0.6))
	p.seg((sx, sy, 1.1), (sx, sy, 1.22), 0.08, 0.1, COPPER, sides=10, grad=(0.0, 0.5))
	# swan neck over to the worm, then the coil
	wx, wy = 0.86, 0.3
	neck = [(sx, sy, 1.2), (sx + 0.1, sy, 1.3), (sx + 0.25, sy + 0.01, 1.28), (wx, wy, 1.05)]
	_chain(p, neck, 0.045, 0.03, COPPER, sides=6, grad=(0.0, 0.5))
	coil = []
	turns, z0, z1, rc = 3.5, 1.02, 0.42, 0.13
	for k in range(43):
		t = k / 42
		a = t * turns * math.tau
		coil.append((wx + math.cos(a) * rc - rc, wy + math.sin(a) * rc, z0 + (z1 - z0) * t))
	coil[0] = (wx, wy, 1.05)
	_chain(p, coil, 0.028, 0.028, COPPER, sides=5, grad=(0.0, 0.5))
	for k in range(3):  # a frame the coil hangs in
		a = k * math.tau / 3 + 0.5
		p.seg((wx - rc + math.cos(a) * 0.18, wy + math.sin(a) * 0.18, 0.0), (wx - rc + math.cos(a) * 0.18, wy + math.sin(a) * 0.18, 1.05),
			  0.02, 0.02, WOOD, sides=4)
	p.seg((wx - rc, wy, 0.0), (wx - rc, wy, 0.32), 0.16, 0.16, WOOD, sides=10, grad=(0.2, 0.9))  # drip bucket
	p.seg((wx - rc, wy, 0.26), (wx - rc, wy, 0.3), 0.14, 0.14, LEAF, sides=10, glow=0.5)
	p.seg((wx - rc + 0.13, wy, 0.42), (wx - rc + 0.02, wy, 0.36), 0.02, 0.015, COPPER, sides=5)
	# table of bottles and jars, right-front
	tx, ty, tz = 0.6, -0.38, 0.72
	p.box((0.72, 0.44, 0.06), (tx, ty, tz), WOOD, grad=(0.1, 0.7))
	for dx in (-0.3, 0.3):
		for dy in (-0.16, 0.16):
			p.box((0.06, 0.06, tz), (tx + dx, ty + dy, tz / 2), WOOD_GRAY, grad=(0.2, 0.9))
	p.box((0.6, 0.04, 0.05), (tx, ty + 0.16, 0.22), WOOD_GRAY)
	glass = [  # (dx, dy, kind, colour, glow)
		(-0.24, 0.1, "bottle", 0, 0.6), (-0.1, -0.1, "jar", 1, 0.0), (0.0, 0.1, "flask", 2, 0.7),
		(0.13, -0.08, "bottle", 3, 0.0), (0.26, 0.1, "jar", 4, 0.5), (0.27, -0.1, "bottle", 1, 0.8),
	]
	for dx, dy, kind, ci, glow in glass:
		x, y, z = tx + dx, ty + dy, tz + 0.03
		sw = GLASS[ci]
		if kind == "bottle":
			p.seg((x, y, z), (x, y, z + 0.17), 0.055, 0.055, sw, sides=8, grad=(0.0, 0.6), glow=glow)
			p.seg((x, y, z + 0.17), (x, y, z + 0.26), 0.05, 0.02, sw, sides=8, glow=glow)
			p.seg((x, y, z + 0.26), (x, y, z + 0.3), 0.022, 0.022, WOOD, sides=5)
		elif kind == "jar":
			p.seg((x, y, z), (x, y, z + 0.13), 0.075, 0.075, sw, sides=8, grad=(0.0, 0.6), glow=glow)
			p.seg((x, y, z + 0.13), (x, y, z + 0.16), 0.08, 0.08, HIDE, sides=8)
		else:
			p.blob((0.15, 0.15, 0.14), (x, y, z + 0.07), sw, segs=(8, 6), grad=(0.0, 0.6), glow=glow)
			p.seg((x, y, z + 0.12), (x, y, z + 0.24), 0.025, 0.02, sw, sides=6, glow=glow)
	p.seg((tx - 0.24, ty - 0.1, tz + 0.03), (tx - 0.24, ty - 0.1, tz + 0.1), 0.06, 0.08, STONE_LIGHT, sides=8)  # mortar
	p.seg((tx - 0.24, ty - 0.1, tz + 0.06), (tx - 0.2, ty - 0.08, tz + 0.18), 0.018, 0.022, STONE_WARM, sides=5)
	# a tap on the cask (placed below) and a mug under it
	p.seg((-0.55, -0.35, 0.4), (-0.55, -0.5, 0.4), 0.035, 0.03, WOOD_GRAY, sides=6)
	p.seg((-0.55, -0.5, 0.4), (-0.55, -0.5, 0.33), 0.025, 0.02, WOOD_GRAY, sides=6)
	p.seg((-0.55, -0.52, 0.0), (-0.55, -0.52, 0.2), 0.13, 0.12, WOOD, sides=10, grad=(0.2, 0.9))  # a pail under the tap
	_hoops(p, (-0.55, -0.52), 0.135, (0.04, 0.16), IRON, w=0.03)
	p.seg((-0.55, -0.52, 0.16), (-0.55, -0.52, 0.18), 0.11, 0.11, BAMBOO, sides=10, glow=0.2)
	obj = p.build(bevel=0.06)
	# the cask: KayKit's keg on its cradle, round end to the front
	return join_into(obj, kaykit("keg", (-0.55, 0.12, 0.0), 0.0, (0.48, 0.48, 0.48)))


def forge():
	"""A smithy forge, about 2.5 m wide: a brick hearth of glowing coals under a
	hood and chimney set against a back wall, bellows at its side, an anvil on a
	stump in front (-Y) with hammer and tongs, and a quench barrel of water."""
	p = Prop("forge", 174)
	hx, hy = -0.3, 0.4      # hearth centre
	hw, hd, hh = 1.5, 1.0, 0.78
	# coals in a stone-rimmed pan on top of the (KayKit brick) hearth
	for s in (-1, 1):
		p.box((0.14, hd - 0.1, 0.14), (hx + s * (hw / 2 - 0.1), hy, hh + 0.05), STONE_LIGHT, grad=(0.0, 0.6))
	p.box((hw - 0.1, 0.14, 0.14), (hx, hy - hd / 2 + 0.1, hh + 0.05), STONE_LIGHT, grad=(0.0, 0.6))
	p.box((hw - 0.3, hd - 0.3, 0.06), (hx, hy, hh), IRON, grad=(0.5, 1.0))
	p.blob((hw - 0.35, hd - 0.35, 0.16), (hx, hy, hh + 0.03), EMBER, segs=(10, 6), grad=(0.3, 0.9), glow=1.3)
	for k in range(16):
		x = hx + p.rng.uniform(-0.5, 0.5)
		y = hy + p.rng.uniform(-0.25, 0.25)
		sw, gl = (EMBER, 1.5) if k % 3 else (IRON, 0.0)
		p.rock((0.14, 0.12, 0.1), (x, y, hh + 0.1), sw, grad=(0.1, 0.8), jitter=0.05) if not gl else \
			p.blob((0.14, 0.12, 0.1), (x, y, hh + 0.1), sw, segs=(6, 4), grad=(0.0, 0.7), glow=gl)
	for x, hgt in ((-0.2, 0.34), (0.1, 0.26), (-0.45, 0.22)):
		p.seg((hx + x, hy, hh + 0.08), (hx + x * 0.9, hy + 0.02, hh + 0.08 + hgt), 0.08, 0.0, FLAME, sides=5,
			  grad=(0.1, 0.9), glow=1.5, twist=x * 90)
	p.seg((hx + 0.15, hy - 0.05, hh + 0.14), (hx + 0.55, hy - 0.42, hh + 0.2), 0.022, 0.022, IRON, sides=4)  # a bar heating
	p.box((0.22, 0.06, 0.05), (hx + 0.08, hy + 0.01, hh + 0.14), EMBER, rot=(0, 0, -43), glow=1.8)
	# hood on posts, chimney up through it
	wall_y = hy + hd / 2 - 0.12
	hz0, hz1 = 1.6, 2.2
	p.seg((hx, hy + 0.02, hz0), (hx, hy + 0.1, hz1), 0.86, 0.3, STONE_DARK, sides=4, grad=(0.1, 0.9), twist=45)
	p.seg((hx, hy + 0.02, hz0 - 0.08), (hx, hy + 0.02, hz0), 0.9, 0.9, IRON, sides=4, grad=(0.0, 0.5), twist=45)
	p.box((0.5, 0.5, 1.0), (hx, hy + 0.12, 2.6), STONE_LIGHT, grad=(0.05, 0.9))
	p.box((0.62, 0.62, 0.12), (hx, hy + 0.12, 3.12), STONE_WARM, grad=(0.0, 0.6))
	for s in (-1, 1):
		p.seg((hx + s * (hw / 2 - 0.1), hy - hd / 2 + 0.1, hh + 0.1), (hx + s * (hw / 2 - 0.12), hy - hd / 2 + 0.12, hz0 - 0.05), 0.04, 0.04, IRON, sides=6)
	# bellows on a trestle at the hearth's right side, nozzle into the fire
	bx, by = hx + hw / 2 + 0.33, hy - 0.05
	for dx in (-0.2, 0.2):
		p.box((0.07, 0.4, 0.07), (bx + dx, by, 0.5), WOOD_GRAY)
		for dy in (-0.15, 0.15):
			p.seg((bx + dx, by + dy, 0.0), (bx + dx, by + dy * 0.7, 0.5), 0.03, 0.03, WOOD_GRAY, sides=4)
	outline = [(bx - 0.3, by)] + [(bx + 0.08 + math.cos(t) * 0.22, by + math.sin(t) * 0.22)
								   for t in [math.radians(a_) for a_ in range(-120, 121, 30)]]
	n = len(outline)
	for z in (0.56, 0.74):
		verts = [(x, y, z) for x, y in outline] + [(x, y, z + 0.04) for x, y in outline]
		faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
		p.poly(verts, faces, WOOD, grad=(0.1, 0.8))
	p.blob((0.48, 0.4, 0.2), (bx + 0.06, by, 0.67), HIDE, segs=(10, 6), grad=(0.1, 0.9))
	p.seg((bx + 0.3, by, 0.78), (bx + 0.44, by, 0.98), 0.025, 0.025, WOOD_GRAY, sides=5)  # handle
	p.seg((bx - 0.28, by, 0.62), (hx + hw / 2 - 0.05, by, 0.7), 0.045, 0.03, IRON, sides=6)  # nozzle
	# anvil on its stump, in front
	ax, ay = 0.35, -0.6
	p.seg((ax, ay, 0.0), (ax, ay, 0.45), 0.3, 0.27, WOOD, sides=9, grad=(0.3, 1.0), jitter=0.01)
	p.seg((ax, ay, 0.44), (ax, ay, 0.46), 0.25, 0.25, HIDE, sides=9)
	p.box((0.4, 0.26, 0.1), (ax, ay, 0.51), IRON, grad=(0.2, 0.9))
	p.box((0.22, 0.16, 0.16), (ax, ay, 0.64), IRON, grad=(0.2, 0.9))
	p.box((0.5, 0.22, 0.12), (ax - 0.03, ay, 0.78), IRON, grad=(0.0, 0.6))
	p.seg((ax + 0.22, ay, 0.8), (ax + 0.5, ay, 0.8), 0.08, 0.0, IRON, sides=6, grad=(0.0, 0.6))
	p.box((0.12, 0.2, 0.09), (ax - 0.33, ay, 0.795), IRON, grad=(0.0, 0.6))
	# hammer on the anvil, tongs against the stump
	p.seg((ax - 0.05, ay - 0.02, 0.87), (ax + 0.2, ay - 0.2, 0.87), 0.018, 0.018, WOOD, sides=5)
	p.box((0.06, 0.16, 0.07), (ax - 0.07, ay + 0.02, 0.88), STONE_LIGHT, rot=(0, 0, 40), grad=(0.0, 0.6))
	for s in (-1, 1):
		p.seg((ax + 0.3 + s * 0.02, ay - 0.1, 0.02), (ax + 0.26 + s * 0.035, ay - 0.08, 0.62), 0.014, 0.014, IRON, sides=4)
	p.seg((ax + 0.26, ay - 0.08, 0.62), (ax + 0.24, ay - 0.08, 0.72), 0.02, 0.012, IRON, sides=4)
	# quench barrel, left front
	qx, qy = -1.0, -0.45
	p.seg((qx, qy, 0.0), (qx, qy, 0.62), 0.26, 0.26, WOOD, sides=12, grad=(0.2, 1.0))
	p.blob((0.62, 0.62, 0.3), (qx, qy, 0.32), WOOD, segs=(12, 6), grad=(0.2, 1.0))
	_hoops(p, (qx, qy), 0.315, (0.12, 0.5), IRON)
	p.seg((qx, qy, 0.54), (qx, qy, 0.6), 0.27, 0.27, WATER, sides=12, grad=(0.1, 0.5))
	p.seg((qx + 0.1, qy - 0.05, 0.6), (qx + 0.32, qy - 0.2, 0.9), 0.012, 0.012, IRON, sides=4)
	obj = p.build(bevel=0.06)
	# hearth and back wall: KayKit's brick wall, so it matches the city's stone
	pieces = kaykit("wall", (hx, hy - hd / 2 + 0.12, -0.6), 0.0, (hw / 4, 0.24, (hh + 0.6) / 4))
	for s in (-1, 1):
		pieces += kaykit("wall", (hx + s * (hw / 2 - 0.12), hy, -0.6), math.pi / 2, (hd / 4, 0.24, (hh + 0.6) / 4))
	pieces += kaykit("wall", (hx, wall_y, 0.0), 0.0, (hw / 4, 0.24, hz1 / 4))
	return join_into(obj, pieces)


# ---------------------------------------------------------------- the Necromancers' crypt (Emberhold)

def _skull(p, c, s=1.0, yaw=0.0, swatch=BONE):
	"""A skull sitting on c, looking along yaw (0 = toward -Y, like a prop's front)."""
	c = Vector(c)
	f = Vector((math.sin(yaw), -math.cos(yaw), 0))
	r = Vector((math.cos(yaw), math.sin(yaw), 0))
	up = Vector((0, 0, 1))
	deg = math.degrees(yaw)
	p.blob((0.2 * s, 0.24 * s, 0.2 * s), c + up * 0.11 * s - f * 0.02 * s, swatch, rot=(0, 0, deg), segs=(8, 6), grad=(0.0, 0.6))
	p.blob((0.15 * s, 0.1 * s, 0.11 * s), c + f * 0.08 * s + up * 0.06 * s, swatch, rot=(0, 0, deg), segs=(6, 4), grad=(0.1, 0.7))
	p.box((0.12 * s, 0.08 * s, 0.04 * s), c + f * 0.08 * s + up * 0.02 * s, swatch, rot=(0, 0, deg), grad=(0.2, 0.8))
	for side in (-1, 1):
		p.blob((0.055 * s, 0.03 * s, 0.05 * s), c + f * 0.125 * s + r * side * 0.045 * s + up * 0.11 * s, IRON,
			   rot=(0, 0, deg), segs=(5, 4), grad=(1.0, 1.0))
	p.blob((0.03 * s, 0.03 * s, 0.035 * s), c + f * 0.135 * s + up * 0.065 * s, IRON, rot=(0, 0, deg), segs=(4, 3), grad=(1.0, 1.0))


def _bone(p, a, b, r=0.022):
	"""A long bone: a shaft with a knuckle at each end."""
	a, b = Vector(a), Vector(b)
	p.seg(a, b, r, r * 0.85, BONE, sides=5, grad=(0.0, 0.6))
	for e in (a, b):
		p.blob((r * 3.2, r * 3.2, r * 2.6), e, BONE, segs=(5, 4), grad=(0.0, 0.5))


def _candle(p, base, h=0.18, r=0.035):
	"""A wax candle standing on base with a small lit flame; returns the flame's position."""
	base = Vector(base)
	top = base + Vector((0, 0, h))
	p.seg(base, top, r, r * 0.92, CLOTH_WHITE, sides=6, grad=(0.0, 0.45))
	p.blob((r * 2.6, r * 2.6, r * 0.9), base + Vector((0, 0, 0.012)), CLOTH_WHITE, segs=(6, 3), grad=(0.1, 0.5))  # a drip pool
	p.seg(top, top + Vector((0, 0, 0.1)), 0.022, 0.0, FLAME, sides=5, grad=(0.1, 0.9), glow=2.2)
	p.blob((0.03, 0.03, 0.04), top + Vector((0, 0, 0.025)), EMBER, segs=(5, 4), grad=(0.0, 0.3), glow=2.6)
	return top + Vector((0, 0, 0.05))


def _candle_stand(p, x, y, h=1.2):
	"""A wrought iron candle stand on three feet, one fat candle on its drip pan."""
	for k in range(3):
		a = k * math.tau / 3 + 0.3
		p.seg((x, y, 0.22), (x + math.cos(a) * 0.26, y + math.sin(a) * 0.26, 0.0), 0.02, 0.018, IRON, sides=4, grad=(0.1, 0.8))
	p.seg((x, y, 0.0), (x, y, h), 0.028, 0.024, IRON, sides=6, grad=(0.1, 0.8))
	p.seg((x, y, h - 0.02), (x, y, h + 0.03), 0.15, 0.13, IRON, sides=10, grad=(0.0, 0.6))
	return _candle(p, (x, y, h + 0.03), h=0.22, r=0.05)


def _corner_web(p, corner, d1, d2, down, r):
	"""Cobweb strung across a corner: strands from the corner to an arc through
	the two walls and down, laced with cross threads."""
	corner, d1, d2, down = Vector(corner), Vector(d1), Vector(d2), Vector(down)
	dirs = []
	for k in range(7):
		t = k / 6
		if t <= 0.5:
			d = d1.lerp(down, t * 2)
		else:
			d = down.lerp(d2, (t - 0.5) * 2)
		dirs.append(d.normalized() * r * p.rng.uniform(0.85, 1.05))
	for d in dirs:
		p.seg(corner, corner + d, 0.012, 0.008, CLOTH_WHITE, sides=3, grad=(0.0, 0.3))
	for frac in (0.3, 0.5, 0.7, 0.9):
		for a, b in zip(dirs, dirs[1:]):
			p.seg(corner + a * frac, corner + b * (frac + 0.02), 0.008, 0.008, CLOTH_WHITE, sides=3, grad=(0.0, 0.3))


def _bone_pile(p, x, y, radius):
	"""A heap of bones and skulls swept into a corner, low enough to see over."""
	p.blob((radius * 2.0, radius * 1.8, 0.3), (x, y, 0.0), STONE_DARK, segs=(10, 5), grad=(0.3, 0.9))
	for k in range(int(radius * 22)):
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(0, radius * 0.9)
		cx, cy = x + math.cos(a) * d, y + math.sin(a) * d
		z = 0.05 + (1 - d / radius) * 0.28
		b = p.rng.uniform(0, math.tau)
		ln = p.rng.uniform(0.18, 0.34)
		lift = p.rng.uniform(-0.08, 0.1)
		_bone(p, (cx - math.cos(b) * ln, cy - math.sin(b) * ln, z - lift), (cx + math.cos(b) * ln, cy + math.sin(b) * ln, z + lift),
			  r=p.rng.uniform(0.018, 0.026))
	for k in range(max(2, int(radius * 4))):
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(0, radius * 0.7)
		_skull(p, (x + math.cos(a) * d, y + math.sin(a) * d, 0.1 + (1 - d / radius) * 0.2), s=0.95,
			   yaw=p.rng.uniform(0, math.tau))


def _merge_materials(obj):
	"""Every KayKit piece imports its own copy of the pack's material; point
	them all at the first so a big joined prop draws in a few surfaces."""
	mats = obj.data.materials
	first = {}
	remap = {}
	for i, m in enumerate(mats):
		base = m.name.split(".")[0] if m else ""
		key = m.name if base.startswith("dungeon") else base   # glows differ in strength: keep those apart
		remap[i] = first.setdefault(key, i)
	for poly in obj.data.polygons:
		poly.material_index = remap[poly.material_index]
	bpy.ops.object.select_all(action="DESELECT")
	obj.select_set(True)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.material_slot_remove_unused()
	return obj


def crypt_entrance():
	"""The way down to Emberhold's hidden Necromancer guild: a small stone
	mausoleum, 4.5 m wide and 5.2 m deep (4.4 m of walls plus a pillared
	portico), 4.5 m to the ridge of its peaked stone roof. It stands on a
	0.45 m plinth with a ramp up to the portico at the front (-Y, +Z in game).

	The doorway is open, 1.5 m wide and 2.25 m tall, its sill at 0.45 m.
	Behind it a short landing drops by steps into a black stairwell under a
	ceiling that slopes down, so it reads as a stair going on down into the
	dark. The pit's black floor sits at 0.03 m: keep the ground under the
	building at or below the origin, or grass shows in it. A zone line goes in
	the doorway: centred on (0, 0.45, 1.6) in game, the opening spans x +/-0.75
	and z 1.3..1.9. A skull is carved in the pediment over the door and an iron
	lantern hangs either side of it (glow at about (+/-1.85, 2.2, 2.25) in game).
	"""
	p = Prop("crypt_entrance", 181)
	d = Prop("crypt_entrance_detail", 182)   # skulls and small bits: no bevel
	plinth = 0.45
	wall_top = plinth + 2.6
	# --- plinth, built around the stairwell pit (x +/-1.65, y -1.0..1.9) -------
	p.box((5.3, 5.8, 0.2), (0, 0.0, 0.1), STONE_DARK, grad=(0.4, 1.0))                 # footing course
	p.box((4.9, 1.7, plinth), (0, -1.85, plinth / 2), STONE_LIGHT, grad=(0.2, 0.9))    # portico + landing
	for s in (-1, 1):
		p.box((0.8, 3.7, plinth), (s * 2.05, 0.85, plinth / 2), STONE_LIGHT, grad=(0.2, 0.9))
	p.box((3.3, 0.8, plinth), (0, 2.3, plinth / 2), STONE_LIGHT, grad=(0.2, 0.9))
	# the ramp up to the portico, laid as four slabs so it reads as worn steps
	y_top, y_foot, rw = -2.7, -4.1, 1.1
	n = 4
	for k in range(n):
		ya = y_foot + (y_top - y_foot) * k / n
		yb = y_foot + (y_top - y_foot) * (k + 1) / n
		za, zb = plinth * k / n, plinth * (k + 1) / n
		p.poly([(-rw, ya, za), (rw, ya, za), (rw, yb, zb), (-rw, yb, zb), (-rw, ya, -0.05), (rw, ya, -0.05), (rw, yb, -0.05), (-rw, yb, -0.05)],
			   [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
			   STONE_LIGHT if k % 2 else STONE_WARM, grad=(0.1, 0.8))
	for s in (-1, 1):   # kerbs either side of the ramp
		p.box((0.35, 1.4, 0.3), (s * (rw + 0.18), (y_top + y_foot) / 2, 0.12), STONE_DARK, grad=(0.2, 0.9))
		p.box((0.4, 0.4, 0.25), (s * (rw + 0.18), y_foot + 0.2, 0.3), STONE_LIGHT, grad=(0.1, 0.7))
	# --- the stairwell: a landing, three steps down, then black ----------------
	for k, (y0, y1, z) in enumerate(((-1.0, -0.65, 0.34), (-0.65, -0.3, 0.23), (-0.3, 0.05, 0.12))):
		sw, gr = ((STONE_DARK, (0.4, 0.9)), (STONE_DARK, (0.8, 1.0)), (IRON, (0.6, 1.0)))[k]
		p.box((3.3, y1 - y0, z), (0, (y0 + y1) / 2, z / 2), sw, grad=gr)
	p.box((3.3, 1.9, 0.06), (0, 0.97, 0.0), IRON, grad=(1.0, 1.0))                     # the dark below
	for s in (-1, 1):   # the pit's walls, lined dark so the light dies inside
		p.box((0.06, 3.3, 3.0), (s * 1.6, 0.3, 1.5), IRON, grad=(0.55, 1.0))
	p.box((3.3, 0.06, 3.0), (0, 1.85, 1.5), IRON, grad=(0.7, 1.0))
	# a ceiling sloping down over the stair, as if it runs on underground
	ya, za, yb, zb = -1.3, plinth + 2.25, 1.9, 0.9
	ang = math.degrees(math.atan2(za - zb, yb - ya))
	p.box((3.3, math.hypot(yb - ya, za - zb) + 0.1, 0.12), (0, (ya + yb) / 2, (za + zb) / 2), IRON,
		  rot=(-ang, 0, 0), grad=(0.75, 1.0))
	# --- door frame, lintel and the portico ---------------------------------
	door_w, door_h = 1.5, 2.25
	for s in (-1, 1):
		p.box((0.22, 0.72, door_h), (s * (door_w / 2 + 0.11), -1.6, plinth + door_h / 2), STONE_LIGHT, grad=(0.1, 0.8))
	p.box((door_w + 0.7, 0.8, 0.42), (0, -1.6, plinth + door_h + 0.2), STONE_LIGHT, grad=(0.05, 0.7))
	p.box((door_w + 0.2, 0.2, 0.08), (0, -1.95, plinth + door_h - 0.02), STONE_DARK, grad=(0.3, 0.9))   # drip edge
	for s in (-1, 1):   # two short pillars carrying the pediment
		x, y = s * 1.3, -2.35
		p.box((0.5, 0.5, 0.2), (x, y, plinth + 0.1), STONE_DARK, grad=(0.1, 0.8))
		p.seg((x, y, plinth + 0.2), (x, y, wall_top - 0.3), 0.2, 0.17, STONE_LIGHT, sides=10, grad=(0.05, 0.85))
		p.seg((x, y, wall_top - 0.3), (x, y, wall_top - 0.15), 0.19, 0.27, STONE_LIGHT, sides=10, grad=(0.1, 0.7))
		p.box((0.58, 0.58, 0.16), (x, y, wall_top - 0.08), STONE_DARK, grad=(0.1, 0.7))
	# frieze: a stone course round the top of the walls and along the portico
	p.box((4.75, 4.65, 0.3), (0, 0.3, wall_top + 0.15), STONE_DARK, grad=(0.1, 0.8))
	p.box((4.95, 0.95, 0.3), (0, -2.33, wall_top + 0.15), STONE_DARK, grad=(0.1, 0.8))
	eave = wall_top + 0.3
	# --- peaked stone roof: ridge front to back, the pediment facing the door
	half, rise, y0r, y1r = 2.6, 1.0, -2.95, 2.75
	slope = math.hypot(half, rise)
	ang = math.atan2(rise, half)
	for s in (1, -1):
		dn = Vector((math.cos(ang) * s, 0, -math.sin(ang)))
		out = Vector((math.sin(ang) * s, 0, math.cos(ang)))
		base = Vector((0, (y0r + y1r) / 2, eave + rise))
		p.box((slope, y1r - y0r, 0.2), base + dn * slope / 2, STONE_DARK, rot=(0, math.degrees(ang) * s, 0), grad=(0.2, 0.9))
		for i in range(4):   # stone slab courses
			c = base + dn * slope * (i + 0.55) / 4 + out * 0.13
			p.box((slope / 4 * 1.12, y1r - y0r + 0.1, 0.1), c, STONE_LIGHT if i % 2 else STONE_WARM,
				  rot=(0, math.degrees(ang) * s, 0), grad=(0.0, 0.9))
	p.box((0.34, y1r - y0r + 0.25, 0.22), (0, (y0r + y1r) / 2, eave + rise + 0.12), STONE_DARK, grad=(0.1, 0.7))   # ridge cap
	for y, t in ((y0r + 0.15, 0.3), (y1r - 0.15, 0.3)):   # pediment front and gable back
		tri = [(-half + 0.1, eave), (half - 0.1, eave), (0, eave + rise - 0.05)]
		verts = [(x, y - t / 2, z) for x, z in tri] + [(x, y + t / 2, z) for x, z in tri]
		p.poly(verts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], STONE_LIGHT, grad=(0.05, 0.7))
	for s in (-1, 1):   # a raking cornice on the pediment
		p.seg((s * (half - 0.05), y0r - 0.02, eave + 0.02), (0, y0r - 0.02, eave + rise + 0.02), 0.09, 0.09, STONE_DARK, sides=4)
	p.box((half * 2, 0.22, 0.14), (0, y0r - 0.02, eave + 0.02), STONE_DARK, grad=(0.1, 0.7))
	p.blob((0.2, 0.2, 0.2), (0, y0r + 0.1, eave + rise + 0.12), STONE_DARK, segs=(8, 6))   # finial
	# --- the skull carved over the door, on crossed bones ---------------------
	sk = Vector((0, y0r - 0.02, eave + 0.3))
	for s in (-1, 1):
		d.seg(sk + Vector((-0.42 * s, -0.02, -0.2)), sk + Vector((0.42 * s, -0.02, 0.36)), 0.045, 0.045, BONE, sides=6, grad=(0.1, 0.7))
		for e in (Vector((-0.42 * s, -0.02, -0.2)), Vector((0.42 * s, -0.02, 0.36))):
			d.blob((0.13, 0.1, 0.11), sk + e, BONE, segs=(6, 4), grad=(0.1, 0.6))
	_skull(d, sk + Vector((0, -0.05, -0.12)), s=2.4, swatch=BONE)
	# --- iron lanterns either side of the door --------------------------------
	for s in (-1, 1):
		x, y, z = s * 1.85, -1.9, 2.55
		d.seg((x, y + 0.02, z + 0.25), (x, y - 0.38, z + 0.25), 0.03, 0.03, IRON, sides=4, grad=(0.1, 0.7))
		d.seg((x, y + 0.02, z + 0.02), (x, y - 0.2, z + 0.24), 0.02, 0.02, IRON, sides=4, grad=(0.1, 0.7))
		d.seg((x, y - 0.35, z + 0.25), (x, y - 0.35, z + 0.08), 0.012, 0.012, IRON, sides=4)
		lx, ly, lz = x, y - 0.35, z - 0.12
		d.seg((lx, ly, lz + 0.18), (lx, ly, lz + 0.3), 0.14, 0.03, IRON, sides=4, grad=(0.0, 0.6), twist=45)   # cap
		d.box((0.24, 0.24, 0.04), (lx, ly, lz + 0.17), IRON, grad=(0.1, 0.6))
		d.box((0.22, 0.22, 0.05), (lx, ly, lz - 0.17), IRON, grad=(0.1, 0.6))
		for cx in (-1, 1):
			for cy in (-1, 1):
				d.box((0.03, 0.03, 0.34), (lx + cx * 0.1, ly + cy * 0.1, lz), IRON, grad=(0.1, 0.7))
		d.box((0.17, 0.17, 0.3), (lx, ly, lz), EMBER, glow=3.0, grad=(0.1, 0.4))
	# --- a little dressing: urns on the kerbs, a bone at the door ---------------
	for s in (-1, 1):
		x, y = s * (rw + 0.18), y_foot + 0.2
		d.seg((x, y, 0.42), (x, y, 0.72), 0.12, 0.2, STONE_DARK, sides=8, grad=(0.1, 0.8))
		d.seg((x, y, 0.72), (x, y, 0.8), 0.2, 0.14, STONE_DARK, sides=8, grad=(0.0, 0.6))
		d.seg((x, y, 0.79), (x, y, 0.81), 0.13, 0.13, IRON, sides=8, grad=(1.0, 1.0))
	_bone(d, (0.7, -2.2, plinth + 0.03), (0.35, -2.45, plinth + 0.04), r=0.025)
	_skull(d, (-0.95, -2.5, plinth), s=0.9, yaw=0.4)
	obj = p.build(bevel=0.05)
	obj = join_into(obj, [d.build()])
	# --- walls: KayKit's own stone, as in the houses ---------------------------
	wall_h = wall_top - plinth
	zs = wall_h / 4.0
	pieces = []
	for s in (-1, 1):
		pieces += kaykit("wall", (s * 1.95, 0.3, plinth), math.pi / 2 * -s, (4.4 / 4.0, 0.6, zs))
		pieces += kaykit("wall", (s * 1.525, -1.6, plinth), 0.0, (1.45 / 4.0, 0.6, zs))
	pieces += kaykit("wall", (0, 2.2, plinth), math.pi, (4.5 / 4.0, 0.6, zs))
	for x in (-2.0, 2.0):
		for y in (-1.65, 2.25):
			pieces += kaykit("pillar", (x, y, plinth), 0.0, (0.42, 0.42, zs))
	return _merge_materials(join_into(obj, pieces))


def _niche_row(p, d, start, n, count, pitch, fills, h=0.46, depth=0.3):
	"""A row of burial niches (loculi) along a wall: a continuous stone sill and
	lintel with posts between, standing out from the wall around a black back,
	so each bay reads as a recess. start is the first bay's sill centre on the
	wall face, n the wall's inward normal; the row runs along n turned left
	(+90 degrees). fills names what lies in each bay. Returns the flames of the
	bays holding a candle."""
	start, n = Vector(start), Vector((n[0], n[1], 0)).normalized()
	t = Vector((-n.y, n.x, 0))
	rz = math.degrees(math.atan2(t.y, t.x))
	up = Vector((0, 0, 1))
	run = count * pitch
	mid = start + t * (run / 2 - pitch / 2)
	p.box((run + 0.12, depth, 0.1), mid + n * depth / 2 - up * 0.05, STONE_LIGHT, rot=(0, 0, rz), grad=(0.05, 0.7))
	p.box((run + 0.12, depth, 0.12), mid + n * depth / 2 + up * (h + 0.06), STONE_LIGHT, rot=(0, 0, rz), grad=(0.05, 0.7))
	p.box((run, 0.04, h), mid + n * 0.02 + up * h / 2, IRON, rot=(0, 0, rz), grad=(0.8, 1.0))
	for i in range(count + 1):
		p.box((0.12, depth, h), start + t * (i * pitch - pitch / 2) + n * depth / 2 + up * h / 2, STONE_WARM, rot=(0, 0, rz), grad=(0.1, 0.9))
	yaw = math.atan2(n.x, -n.y)   # skulls look out of the wall
	flames = []
	w = pitch - 0.12
	for i, fill in enumerate(fills[:count]):
		c = start + t * (i * pitch) + n * (depth * 0.5)
		if fill == "skull":
			_skull(d, c + t * d.rng.uniform(-0.2, 0.2), s=1.0, yaw=yaw + d.rng.uniform(-0.3, 0.3))
			_bone(d, c + t * 0.1 + n * 0.08 + up * 0.03, c + t * 0.42 - n * 0.02 + up * 0.03, r=0.02)
		elif fill == "skulls":
			for k, off in enumerate((-0.28, 0.0, 0.28)):
				_skull(d, c + t * off, s=0.85 if k != 1 else 0.95, yaw=yaw + d.rng.uniform(-0.4, 0.4))
		elif fill == "bones":
			for k in range(4):
				off = (k - 1.5) * 0.06
				_bone(d, c - t * (w / 2 - 0.08) + n * off + up * (0.03 + (k % 2) * 0.04),
					  c + t * (w / 2 - 0.08) + n * off + up * (0.03 + (k % 2) * 0.04), r=0.022)
			_skull(d, c + t * 0.2 + up * 0.08, s=0.8, yaw=yaw)
		elif fill == "shroud":   # one laid to rest whole, wrapped
			d.blob((w - 0.1, depth * 0.75, 0.2), c + up * 0.1, CLOTH_WHITE, rot=(0, 0, rz), segs=(10, 6), grad=(0.3, 0.9))
			d.blob((0.22, depth * 0.62, 0.18), c - t * (w / 2 - 0.16) + up * 0.14, CLOTH_WHITE, rot=(0, 0, rz), segs=(6, 4), grad=(0.3, 0.9))
		elif fill == "candle":
			_skull(d, c - t * 0.2, s=0.9, yaw=yaw)
			flames.append(_candle(d, c + t * 0.22 + n * 0.02, h=0.14, r=0.03))
			_candle(d, c + t * 0.34 - n * 0.04, h=0.08, r=0.025)
	return flames


def _sarcophagus(p, d, x, y, yaw_deg, ajar=False):
	"""A stone coffin with a carved effigy on its lid, long axis along yaw."""
	rot = (0, 0, yaw_deg)
	a = math.radians(yaw_deg)
	ax = Vector((math.cos(a), math.sin(a), 0))
	side = Vector((-math.sin(a), math.cos(a), 0))
	c = Vector((x, y, 0))
	up = Vector((0, 0, 1))
	p.box((2.35, 1.1, 0.14), c + up * 0.07, STONE_DARK, rot=rot, grad=(0.2, 0.9))
	p.box((2.15, 0.92, 0.66), c + up * 0.47, STONE_LIGHT, rot=rot, grad=(0.1, 0.9))
	for s in (-1, 1):   # carved panels on the long sides
		for k in (-1, 0, 1):
			p.box((0.5, 0.04, 0.32), c + ax * k * 0.62 + side * s * 0.47 + up * 0.46, STONE_WARM, rot=rot, grad=(0.1, 0.8))
	if ajar:
		p.box((1.9, 0.72, 0.04), c + up * 0.78, IRON, rot=rot, grad=(1.0, 1.0))   # the dark inside
		lid_c = c + ax * 0.25 + side * 0.28 + up * 0.88
		lrot = (0, 0, yaw_deg + 14)
	else:
		lid_c = c + up * 0.86
		lrot = rot
	p.box((2.3, 1.04, 0.16), lid_c, STONE_WARM, rot=lrot, grad=(0.0, 0.7))
	la = math.radians(lrot[2])
	lax = Vector((math.cos(la), math.sin(la), 0))
	# the effigy: a robed figure, head toward -ax, hands folded
	p.blob((1.45, 0.5, 0.22), lid_c + lax * 0.12 + up * 0.1, STONE_LIGHT, rot=lrot, segs=(10, 6), grad=(0.0, 0.7))
	p.blob((0.3, 0.3, 0.24), lid_c - lax * 0.78 + up * 0.14, STONE_LIGHT, rot=lrot, segs=(8, 6), grad=(0.0, 0.6))
	p.blob((0.22, 0.28, 0.14), lid_c - lax * 0.2 + up * 0.2, STONE_LIGHT, rot=lrot, segs=(6, 4), grad=(0.0, 0.6))


def crypt_room():
	"""The Necromancers' crypt under Emberhold, the whole interior in one piece.

	Walls on centrelines 21 m (x) by 16.5 m (y), so the clear floor is about
	20.2 x 15.7 m; ceiling at 4.5 m. The floor's walking surface is at 0
	everywhere and closed underneath; the walls are closed but for an open
	doorway (1.4 m wide, about 3 m tall) in the middle of the south wall (-Y,
	+Z in game), behind which a stair climbs away into the dark (the steps are
	0.22 m risers, not meant to be walked: the zone line goes in the doorway).

	In game coordinates (x, y, z) = (blender x, z, -blender y):
	  doorway, floor level ....... (0, 0, 8.25)
	  ritual circle centre ....... (0, 0, -2.6), radius 2.3
	  altar ...................... (0, 0, -6.7), 2 m wide
	Burial niches line the walls, stone coffins stand against the east and west
	walls, bones pile in the corners, candles burn on stands, in niches, on the
	altar and on the coffins, and cobwebs hang in the corners.
	"""
	p = Prop("crypt_room", 191)
	d = Prop("crypt_room_detail", 192)
	hw, hd = 10.5, 8.25          # wall centrelines
	fx, fy = hw - 0.375, hd - 0.375   # inner wall faces
	top = 4.5
	flames = {}

	# --- under the tiles: a slab, so the floor is closed whatever the seams ---
	p.box((hw * 2 + 0.8, hd * 2 + 0.8, 0.3), (0, 0, -0.2), STONE_DARK, grad=(0.6, 1.0))

	# --- the doorway: a stone frame, a lintel and a skull over it --------------
	door_w, door_h = 1.6, 2.8
	for sx in (-1, 1):
		p.box((0.24, 0.95, door_h), (sx * (door_w / 2 + 0.1), -hd, door_h / 2), STONE_LIGHT, grad=(0.1, 0.8))
		p.box((0.36, 1.0, 0.2), (sx * (door_w / 2 + 0.1), -hd, 0.1), STONE_DARK, grad=(0.2, 0.9))
	p.box((door_w + 0.7, 1.0, 0.36), (0, -hd, door_h + 0.18), STONE_LIGHT, grad=(0.05, 0.7))
	_skull(d, (0, -fy + 0.3, door_h + 0.44), s=1.6, yaw=math.pi)
	p.box((0.8, 0.5, 0.08), (0, -fy + 0.2, door_h + 0.4), STONE_DARK, grad=(0.1, 0.7))   # a ledge for it

	# --- the stair behind the doorway, climbing south into the dark ----------
	p.box((2.4, 1.2, 0.3), (0, -hd - 0.45, -0.15), STONE_DARK, grad=(0.3, 0.9))   # threshold
	rise, tread, steps = 0.22, 0.32, 14
	y_start = -hd - 0.7
	for k in range(steps):
		y1 = y_start - k * tread
		zt = rise * (k + 1)
		if k < 3:
			sw, gr = STONE_DARK, (0.2 + k * 0.2, 0.9)
		elif k < 7:
			sw, gr = IRON, (0.4 + (k - 3) * 0.12, 1.0)
		else:
			sw, gr = IRON, (1.0, 1.0)
		p.box((1.9, tread, zt + 0.2), (0, y1 - tread / 2, (zt - 0.2) / 2), sw, grad=gr)
		p.box((1.9, 0.06, 0.04), (0, y1 - 0.03, zt + 0.01), STONE_LIGHT if k < 3 else IRON, grad=(0.3, 0.9) if k < 3 else (1.0, 1.0))
	y_end = y_start - steps * tread
	stretches = [(-hd - 0.35, -hd - 1.6, STONE_DARK, (0.5, 1.0)), (-hd - 1.6, -hd - 3.0, IRON, (0.5, 1.0)),
				 (-hd - 3.0, y_end - 0.3, IRON, (1.0, 1.0))]
	for ya, yb, sw, gr in stretches:
		for s in (-1, 1):
			p.box((0.4, ya - yb, 7.8), (s * 1.15, (ya + yb) / 2, 3.7), sw, grad=gr)
	p.box((2.7, 0.4, 7.8), (0, y_end - 0.4, 3.7), IRON, grad=(1.0, 1.0))   # where it goes, you can't see
	# its ceiling climbs with the steps, 2.9 m above them
	ya, za = -hd - 0.35, 3.05
	yb, zb = y_end - 0.2, 3.05 + (ya - yb) * rise / tread
	ang = math.degrees(math.atan2(zb - za, ya - yb))
	p.box((2.7, math.hypot(ya - yb, zb - za) + 0.2, 0.3), (0, (ya + yb) / 2, (za + zb) / 2 + 0.15), IRON,
		  rot=(-ang, 0, 0), grad=(0.8, 1.0))

	# --- ritual circle near the north end ------------------------------------
	cx, cy, R = 0.0, 2.6, 2.3
	d.seg((cx, cy, -0.01), (cx, cy, 0.008), R + 0.25, R + 0.25, IRON, sides=40, grad=(0.6, 0.9))  # a dark inlay
	for rr, wdt in ((R, 0.09), (R - 0.45, 0.06)):
		nseg = 48
		for k in range(nseg):
			a0, a1 = k * math.tau / nseg, (k + 1) * math.tau / nseg
			am = (a0 + a1) / 2
			ln = rr * (a1 - a0) + 0.02
			d.box((ln, wdt, 0.016), (cx + math.cos(am) * rr, cy + math.sin(am) * rr, 0.012), PETAL_PURPLE,
				  rot=(0, 0, math.degrees(am) + 90), grad=(0.1, 0.4), glow=0.9)
	pts = [(cx + math.cos(math.radians(-90 + k * 72)) * (R - 0.45), cy + math.sin(math.radians(-90 + k * 72)) * (R - 0.45)) for k in range(5)]
	for k in range(5):   # the star, tip toward the door
		a, b = pts[k], pts[(k + 2) % 5]
		mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
		ln = math.hypot(b[0] - a[0], b[1] - a[1])
		d.box((ln, 0.05, 0.016), (mx, my, 0.014), PETAL_PURPLE, rot=(0, 0, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))),
			  grad=(0.1, 0.4), glow=0.9)
	for k in range(15):   # runes in the band between the rings
		a = k * math.tau / 15 + 0.1
		rx, ry = cx + math.cos(a) * (R - 0.225), cy + math.sin(a) * (R - 0.225)
		rz = math.degrees(a)
		d.box((0.2, 0.04, 0.016), (rx, ry, 0.014), PETAL_PURPLE, rot=(0, 0, rz), grad=(0.1, 0.4), glow=0.7)
		d.box((0.04, 0.16, 0.016), (rx, ry, 0.014), PETAL_PURPLE, rot=(0, 0, rz + (25 if k % 2 else -25)), grad=(0.1, 0.4), glow=0.7)
	_skull(d, (cx, cy, 0.02), s=1.3, yaw=0.0)                       # a skull at its heart
	for k in range(5):   # candle stands at the star's points, outside the ring
		a = math.radians(-90 + k * 72)
		flames[f"circle_{k}"] = _candle_stand(d, cx + math.cos(a) * (R + 0.7), cy + math.sin(a) * (R + 0.7), h=1.15)

	# --- the altar against the north wall ------------------------------------
	ay = fy - 1.2
	p.box((2.3, 1.1, 0.2), (0, ay, 0.1), STONE_DARK, grad=(0.2, 0.9))
	p.box((2.0, 0.85, 0.75), (0, ay, 0.575), STONE_DARK, grad=(0.1, 0.95))
	p.box((2.2, 1.0, 0.14), (0, ay, 1.02), STONE_LIGHT, grad=(0.0, 0.6))
	for s in (-1, 1):
		p.box((0.1, 0.04, 0.5), (s * 0.55, ay - 0.44, 0.58), PETAL_PURPLE, grad=(0.1, 0.5), glow=0.6)   # runes on its face
	d.box((0.5, 0.36, 0.08), (0.45, ay - 0.05, 1.13), CLOTH_RED, rot=(0, 0, 8), grad=(0.2, 0.9))          # a tome
	d.box((0.46, 0.32, 0.02), (0.45, ay - 0.05, 1.18), CLOTH_WHITE, rot=(0, 0, 8), grad=(0.1, 0.5))
	d.seg((-0.4, ay, 1.09), (-0.4, ay, 1.22), 0.12, 0.2, IRON, sides=10, grad=(0.1, 0.8))                # a bowl, glowing
	d.seg((-0.4, ay, 1.2), (-0.4, ay, 1.215), 0.17, 0.17, PETAL_PURPLE, sides=10, grad=(0.1, 0.3), glow=1.4)
	_skull(d, (0.0, ay + 0.15, 1.09), s=1.2, yaw=0.0)
	for k, x in enumerate((-0.9, 0.95)):
		flames[f"altar_{k}"] = _candle(d, (x, ay + 0.2, 1.09), h=0.26, r=0.045)
	flames["altar_2"] = _candle(d, (0.8, ay + 0.32, 1.09), h=0.16, r=0.04)
	for s in (-1, 1):
		flames[f"altar_stand_{0 if s < 0 else 1}"] = _candle_stand(d, s * 1.75, ay, h=1.35)

	# --- pillars' feet dressed with a skull or two, set later with the pillars
	pillars = [(-5.5, -3.0), (5.5, -3.0), (-5.5, 3.0), (5.5, 3.0)]
	# stone ribs along the ceiling over the pillar rows
	for x in (-5.5, 5.5):
		p.box((0.7, hd * 2 - 0.6, 0.35), (x, 0, top - 0.18), STONE_DARK, grad=(0.1, 0.8))
	p.box((hw * 2 - 0.6, 0.7, 0.35), (0, 3.0, top - 0.18), STONE_DARK, grad=(0.1, 0.8))
	p.box((hw * 2 - 0.6, 0.7, 0.35), (0, -3.0, top - 0.18), STONE_DARK, grad=(0.1, 0.8))

	# --- coffins against the east and west walls -----------------------------
	for s in (-1, 1):
		for k, y in enumerate((-4.9, -0.8, 3.4)):
			_sarcophagus(p, d, s * (fx - 1.3), y, 0.0 if s < 0 else 180.0, ajar=(k == 1 and s > 0) or (k == 2 and s < 0))
	# melted candles on two of the lids
	flames["coffin_w"] = _candle(d, (-(fx - 2.1), -4.9 + 0.3, 1.02), h=0.12, r=0.04)
	flames["coffin_e"] = _candle(d, (fx - 2.1, 3.4 - 0.3, 1.02), h=0.1, r=0.04)

	# --- burial niches: three rows on the long walls, two on the ends ---------
	cycle = ["skull", "bones", "shroud", "skulls", "skull", "shroud", "bones", "skull", "skulls", "shroud", "skull", "bones", "skull"]
	def fills(seed, count, candles):
		out = [cycle[(seed + k * 5) % len(cycle)] for k in range(count)]
		for k in candles:
			out[k] = "candle"
		return out
	niche_candles = []
	for s in (-1, 1):   # west and east (the west rows run north, the east rows south)
		for i, z in enumerate((1.4, 2.35, 3.3)):
			cand = ((5,), (2, 8), (4,))[i] if s < 0 else ((3, 9), (6,), (1,))[i]
			niche_candles += _niche_row(p, d, (s * fx, 5.75 * s, z), (-s, 0), 11, 1.15, fills(i * 3 + (s > 0), 11, cand))
	for i, z in enumerate((1.4, 2.35)):   # north wall, behind the altar: rows running outward from it
		niche_candles += _niche_row(p, d, (2.6, fy, z), (0, -1), 6, 1.15, fills(i * 4 + 1, 6, (2,) if i == 0 else ()))
		niche_candles += _niche_row(p, d, (-8.35, fy, z), (0, -1), 6, 1.15, fills(i * 4 + 7, 6, () if i == 0 else (3,)))
	for i, z in enumerate((1.4, 2.35)):   # south wall, either side of the door
		niche_candles += _niche_row(p, d, (-3.75, -fy, z), (0, 1), 5, 1.15, fills(i * 2 + 5, 5, (1,) if i == 0 else ()))
		niche_candles += _niche_row(p, d, (8.35, -fy, z), (0, 1), 5, 1.15, fills(i * 2 + 9, 5, () if i == 0 else (2,)))
	# a great arch-niche behind the altar, with an effigy skull in it
	p.box((1.9, 0.4, 0.14), (0, fy - 0.2, 1.33), STONE_LIGHT, grad=(0.05, 0.7))
	p.box((1.9, 0.4, 0.16), (0, fy - 0.2, 3.15), STONE_LIGHT, grad=(0.05, 0.7))
	for sx in (-1, 1):
		p.box((0.2, 0.4, 1.8), (sx * 0.85, fy - 0.2, 2.25), STONE_WARM, grad=(0.1, 0.9))
	p.box((1.5, 0.04, 1.7), (0, fy - 0.02, 2.25), IRON, grad=(0.8, 1.0))
	_skull(d, (0, fy - 0.2, 1.4), s=3.0, yaw=0.0)
	p.box((1.4, 0.06, 0.08), (0, fy - 0.03, 3.0), PETAL_PURPLE, grad=(0.1, 0.4), glow=0.8)

	# --- bone piles in the corners, one by the ajar coffin ---------------------
	for x, y, r in ((-(fx - 1.0), -(fy - 0.9), 0.9), (fx - 1.0, -(fy - 0.9), 0.8), (-(fx - 1.0), fy - 0.9, 0.85),
					(fx - 1.0, fy - 0.9, 0.95), (fx - 1.5, 1.35, 0.55)):
		_bone_pile(d, x, y, r)

	# --- cobwebs in the corners, high and low ------------------------------------
	for sx in (-1, 1):
		for sy in (-1, 1):
			corner = (sx * (fx - 0.55), sy * (fy - 0.55), top - 0.2)
			_corner_web(d, corner, (-sx, 0, 0), (0, -sy, 0), (0, 0, -1), 1.3)
	for x, y in pillars:   # webs strung from the pillar heads to the ceiling ribs
		sx = 1 if x > 0 else -1
		_corner_web(d, (x - sx * 0.6, y + (0.6 if y > 0 else -0.6), top - 0.35), (-sx, 0, 0), (0, 1 if y < 0 else -1, 0), (0, 0, -1), 0.9)

	# --- a few candles on the floor by the doorway, to light the way in -------
	for s in (-1, 1):
		flames[f"door_stand_{0 if s < 0 else 1}"] = _candle_stand(d, s * 1.9, -fy + 1.1, h=1.2)

	# report where the light comes from (blender -> game: x, z, -y)
	for name, f in flames.items():
		print(f"crypt_room flame {name}: game ({f.x:.2f}, {f.z:.2f}, {-f.y:.2f})")
	for f in niche_candles:
		print(f"crypt_room niche candle: game ({f.x:.2f}, {f.z:.2f}, {-f.y:.2f})")

	obj = p.build(bevel=0.04)
	obj = join_into(obj, [d.build()])

	# --- the shell: KayKit floor, walls, pillars and ceiling ---------------------
	pieces = []
	tall = top / 4.0
	sy_side = (hd * 2 / 6) / 4.0   # six wall pieces down each 16.5 m side
	for i in range(7):
		x = -9.0 + i * 3.0
		for j in range(6):
			y = -hd + 1.375 + j * 2.75
			pieces += kaykit("floor_tile_large", (x, y, -0.0375), 0.0, (0.75, 0.6875, 0.75))
			pieces += kaykit("ceiling_tile", (x, y, top + 0.02), 0.0, (0.75, 0.6875, 0.75))
		pieces += kaykit("wall", (x, hd, 0), math.pi, (0.75, 0.75, tall))
		if i != 3:
			pieces += kaykit("wall", (x, -hd, 0), 0.0, (0.75, 0.75, tall))
	# the doorway's bay: wall either side of the opening and over it (KayKit's
	# own doorway pieces carry a door, or side walls reaching 1.5 m into the room)
	for s in (-1, 1):
		pieces += kaykit("wall", (s * (door_w / 2 + 0.35), -hd, 0), 0.0, ((1.5 - door_w / 2) / 4.0, 0.75, tall))
	pieces += kaykit("wall", (0, -hd, door_h), 0.0, (door_w / 4.0, 0.75, (top - door_h) / 4.0))
	for j in range(6):
		y = -hd + 1.375 + j * 2.75
		for s in (-1, 1):
			pieces += kaykit("wall", (s * hw, y, 0), math.pi / 2 * -s, (sy_side, 0.75, tall))
	for x in (-hw, hw):
		for y in (-hd, hd):
			pieces += kaykit("pillar", (x, y, 0), 0.0, (0.75, 0.75, tall))
	for x, y in pillars:
		pieces += kaykit("pillar", (x, y, 0), 0.0, (0.6, 0.6, tall))
	return _merge_materials(join_into(obj, pieces))


# ---------------------------------------------------------------- shared shapes (High Terrace, Cinderpass)

FLAG_YELLOW = (4, 2)
FLAG_COLORS = (RUNE, CLOTH_WHITE, CLOTH_RED, LEAF, FLAG_YELLOW)   # blue, white, red, green, yellow


def _slab(p, top_a, top_b, thick, swatch, grad=(0.1, 0.8), glow=0.0):
	"""A closed slab under two matching polylines (top_a, top_b), `thick` deep:
	a strip of roof between two rings, with its edges and ends closed."""
	n = len(top_a)
	verts = list(top_a) + list(top_b)
	verts += [(x, y, z - thick) for x, y, z in top_a] + [(x, y, z - thick) for x, y, z in top_b]
	A, B, C, D = 0, n, 2 * n, 3 * n
	faces = []
	for k in range(n - 1):
		faces.append((A + k, A + k + 1, B + k + 1, B + k))          # top
		faces.append((C + k, D + k, D + k + 1, C + k + 1))          # underside
		faces.append((A + k, C + k, C + k + 1, A + k + 1))          # outer edge
		faces.append((B + k, B + k + 1, D + k + 1, D + k))          # inner edge
	faces.append((A, B, D, C))                                      # the two ends
	faces.append((A + n - 1, C + n - 1, D + n - 1, B + n - 1))
	obj = p.poly(verts, faces, swatch, grad)
	if glow:
		obj.data.materials[0] = atlas_material(glow)
	return obj


def _roof_ring(ax, ay, z, lift, n):
	"""Points round a rectangle (half extents ax, ay) at height z, as four sides
	(front -Y, right +X, back +Y, left -X), each n + 1 points corner to corner.
	The corners rise by `lift` and flare outward, the sides curving up to them:
	the upturned eaves of a Dawnstair roof."""
	sides = (((-1, -1), (1, -1), (0, -1)), ((1, -1), (1, 1), (1, 0)), ((1, 1), (-1, 1), (0, 1)), ((-1, 1), (-1, -1), (-1, 0)))
	out = []
	for (sx0, sy0), (sx1, sy1), (nx, ny) in sides:
		pts = []
		for k in range(n + 1):
			t = k / n
			u = 2 * t - 1
			x = (sx0 + (sx1 - sx0) * t) * ax
			y = (sy0 + (sy1 - sy0) * t) * ay
			c = abs(u) ** 3
			ex, ey = (sx1 - sx0) / 2, (sy1 - sy0) / 2          # along the side
			f = lift * 0.45 * c
			x += nx * f + ex * f * (1 if u > 0 else -1)
			y += ny * f + ey * f * (1 if u > 0 else -1)
			pts.append((x, y, z + lift * c))
		out.append(pts)
	return out


def _swept_roof(p, eave, top, lift, bands=4, thick=0.22, swatch=CLAY, n=8, hole=None, curve=1.6, hips=CLOTH_RED):
	"""A hip roof with upturned eaves: from `eave` (ax, ay, z) up to `top`
	(ax, ay, z); a small top ay closes it to a ridge. The pitch steepens toward
	the top. Laid in `bands` courses, each side of each course its own closed
	slab, so the palette gradient reads as rows of tiles. `hole` =
	(side, band, k0, k1) leaves a gap in one course (0 = front)."""
	(ax0, ay0, z0), (ax1, ay1, z1) = eave, top
	rings = []
	for b in range(bands + 1):
		t = b / bands
		rings.append(_roof_ring(ax0 + (ax1 - ax0) * t, ay0 + (ay1 - ay0) * t, z0 + (z1 - z0) * t ** curve, lift * (1 - t) ** 2, n))
	for b in range(bands):
		for s in range(4):
			a, c = rings[b][s], rings[b + 1][s]
			spans = [(0, n)]
			if hole and hole[0] == s and hole[1] == b:
				spans = [(0, hole[2]), (hole[3], n)]
			for k0, k1 in spans:
				if k1 > k0:
					_slab(p, a[k0:k1 + 1], c[k0:k1 + 1], thick, swatch, grad=(0.15, 1.0) if b % 2 == 0 else (0.3, 1.0))
	if hips:                                                    # a raised ridge down each hip, curling up at the eave
		r = thick * 0.45
		for s in range(4):
			pts = [tuple(Vector(rings[b][s][n]) + Vector((0, 0, r * 0.5))) for b in range(bands + 1)]
			_chain(p, pts, r * 1.2, r, hips, sides=6, grad=(0.1, 0.8))
	return rings


def _ridge(p, x, z, r=0.14, curl=0.6, swatch=CLOTH_RED, finial=True):
	"""A ridge beam along X at height z whose ends curl up, gold knobs on them."""
	pts = [(-x - 0.25, 0, z + curl), (-x, 0, z + r * 0.4), (x, 0, z + r * 0.4), (x + 0.25, 0, z + curl)]
	_chain(p, pts[:2], r * 0.7, r, swatch, sides=6)
	p.seg(pts[1], pts[2], r, r, swatch, sides=6, grad=(0.1, 0.7))
	_chain(p, pts[2:], r, r * 0.7, swatch, sides=6)
	if finial:
		for s in (-1, 1):
			p.blob((r * 1.6, r * 1.6, r * 2.0), (s * (x + 0.28), 0, z + curl + 0.1), GOLD, grad=(0.0, 0.5))


def _flag_line(p, a, b, sag, spacing=0.45, size=(0.3, 0.36), start=0, rope=0.015):
	"""A cord from a to b sagging `sag` at the middle, hung with prayer flags in
	the five colors, each turned a little by the wind."""
	a, b = Vector(a), Vector(b)

	def at(t):
		return a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))

	span = (b - a).length
	n = max(3, int(span / 0.9))
	pts = [tuple(at(k / n)) for k in range(n + 1)]
	_chain(p, pts, rope, rope, HIDE, sides=3, grad=(0.1, 0.7))
	count = max(1, int(span / spacing) - 1)
	w, h = size
	for k in range(count):
		t = (k + 1) / (count + 1)
		top = at(t)
		d = at(min(1.0, t + 0.01)) - at(max(0.0, t - 0.01))
		yaw = math.atan2(d.y, d.x)
		tilt = p.rng.uniform(-22, 22)
		rot = Euler((math.radians(tilt), 0, yaw))
		centre = top + rot.to_matrix() @ Vector((0, 0, -h / 2 - 0.01))
		p.box((w, 0.02, h), tuple(centre), FLAG_COLORS[(k + start) % 5], rot=(tilt, 0, math.degrees(yaw)), grad=(0.05, 0.45))


def _plate(p, outline, y, thick, swatch, grad=(0.1, 0.8), glow=0.0):
	"""A thin plate in the X-Z plane at depth y: `outline` [(x, z)] must be
	star-shaped round its centroid (it is fanned from there)."""
	cx = sum(x for x, _ in outline) / len(outline)
	cz = sum(z for _, z in outline) / len(outline)
	n = len(outline)
	verts = [(cx, y - thick / 2, cz)] + [(x, y - thick / 2, z) for x, z in outline]
	verts += [(cx, y + thick / 2, cz)] + [(x, y + thick / 2, z) for x, z in outline]
	faces = []
	for i in range(n):
		j = (i + 1) % n
		faces.append((0, 1 + i, 1 + j))
		faces.append((n + 1, n + 2 + j, n + 2 + i))
		faces.append((1 + i, n + 2 + i, n + 2 + j, 1 + j))
	obj = p.poly(verts, faces, swatch, grad)
	if glow:
		obj.data.materials[0] = atlas_material(glow)
	return obj


def _lathe(p, profile, sides, swatch, grad=(0.1, 0.8), glow=0.0, jitter=0.0, keep=0.0):
	"""A closed solid of revolution round Z from a closed (r, z) profile loop.
	`jitter` roughens it like rock, sparing points at z above `keep` if keep > 0."""
	verts = []
	for i in range(sides):
		a = i * math.tau / sides
		for r, z in profile:
			j = jitter if not keep or z < keep else jitter * 0.2
			rr = r + p.rng.uniform(-j, j)
			verts.append((math.cos(a) * rr, math.sin(a) * rr, z + p.rng.uniform(-j, j) * 0.6))
	m = len(profile)
	faces = []
	for i in range(sides):
		i2 = (i + 1) % sides
		for k in range(m):
			k2 = (k + 1) % m
			faces.append((i * m + k, i * m + k2, i2 * m + k2, i2 * m + k))
	obj = p.poly(verts, faces, swatch, grad)
	if glow:
		obj.data.materials[0] = atlas_material(glow)
	return obj


# ---------------------------------------------------------------- High Terrace (Dawnstair)

def monastery_hall():
	"""A ruined hall of the Dawn-Tusk's monastery: 12 x 8 m on a stone plinth
	(0.5 m, three steps up at the front, -Y), a room of KayKit walls (9 x 5.4 m,
	a doorway in the middle of the front) inside a colonnade of red pillars,
	under a sweeping two-tier tiled roof with upturned eaves, about 10 m to the
	ridge finials. Ruined but standing: a hole in the upper roof, a pillar
	snapped and fallen, tiles lying about. An altar with a gilded sun faces the
	door. Collide it as a mesh."""
	p = Prop("monastery_hall", 201)
	d = Prop("monastery_hall_detail", 202)       # small bits, no bevel
	P = 0.5                                      # plinth top
	p.box((12.8, 8.8, 0.22), (0, 0, 0.11), STONE_DARK, grad=(0.3, 1.0))
	p.box((12.2, 8.2, P - 0.1), (0, 0, 0.2 + (P - 0.2) / 2), STONE_WARM, grad=(0.1, 0.9))
	p.box((12.4, 8.4, 0.12), (0, 0, P - 0.04), STONE_LIGHT, grad=(0.1, 0.6))       # coping
	for k, (y, z) in enumerate(((-4.62, 0.34), (-4.98, 0.18))):                     # steps up the front
		p.box((4.2 + k * 0.4, 0.38, z), (0, y, z / 2), STONE_LIGHT if k % 2 else STONE_WARM, grad=(0.1, 0.8))
	for s in (-1, 1):                                                               # step cheeks with lotus knobs
		p.box((0.45, 0.8, 0.55), (s * 2.35, -4.72, 0.27), STONE_LIGHT, grad=(0.1, 0.8))
		p.blob((0.4, 0.4, 0.3), (s * 2.35, -4.72, 0.62), STONE_WARM, grad=(0.0, 0.6))
	# --- the colonnade: red lacquered pillars on stone drums, one snapped ------
	colx = 5.4
	coly = 3.55
	pillars = [(x, -coly) for x in (-colx, -3.3, -1.3, 1.3, 3.3, colx)]
	pillars += [(x, coly) for x in (-colx, -2.7, 0.0, 2.7, colx)]
	pillars += [(s * colx, y) for s in (-1, 1) for y in (-1.2, 1.2)]
	top = 3.95
	broken = (3.3, -coly)
	for x, y in pillars:
		p.seg((x, y, P), (x, y, P + 0.28), 0.32, 0.29, STONE_LIGHT, sides=10, grad=(0.1, 0.8))
		if (x, y) == broken:
			p.seg((x, y, P + 0.28), (x, y, 1.5), 0.2, 0.2, CLOTH_RED, sides=10, grad=(0.3, 1.0))
			p.rock((0.42, 0.42, 0.25), (x, y, 1.52), WOOD, jitter=0.1)                       # the splintered top
			p.seg((x + 0.6, y - 1.2, 0.2), (x + 2.6, y - 2.2, 0.35), 0.2, 0.2, CLOTH_RED, sides=10, grad=(0.3, 1.0))  # the rest, fallen
			p.seg((x, y, top - 0.2), (x, y, top), 0.2, 0.2, CLOTH_RED, sides=10)             # its head still hangs in the bracket
			continue
		p.seg((x, y, P + 0.28), (x, y, top), 0.2, 0.19, CLOTH_RED, sides=10, grad=(0.1, 0.95))
		p.box((0.5, 0.5, 0.22), (x, y, top + 0.1), WOOD, grad=(0.2, 0.9))                   # bracket block
		p.box((0.9, 0.24, 0.16), (x, y, top + 0.28), WOOD, grad=(0.2, 0.9))
		p.box((0.24, 0.9, 0.16), (x, y, top + 0.28), WOOD, grad=(0.2, 0.9))
	for y in (-coly, coly):                                                        # the beams the roof rests on
		p.box((2 * colx + 0.5, 0.3, 0.3), (0, y, top + 0.5), CLOTH_RED, grad=(0.1, 0.8))
		p.box((2 * colx + 0.5, 0.34, 0.08), (0, y, top + 0.32), GOLD, grad=(0.1, 0.5))
	for x in (-colx, colx):
		p.box((0.3, 2 * coly + 0.5, 0.3), (x, 0, top + 0.5), CLOTH_RED, grad=(0.1, 0.8))
		p.box((0.34, 2 * coly + 0.5, 0.08), (x, 0, top + 0.32), GOLD, grad=(0.1, 0.5))
	# --- inside: a plank floor, the altar and its sun -------------------------
	p.box((8.4, 4.8, 0.06), (0, 0.7, P + 0.03), WOOD, grad=(0.3, 0.9))
	p.box((2.2, 0.9, 1.0), (0, 2.6, P + 0.5), STONE_WARM, grad=(0.1, 0.8))
	p.box((2.5, 1.1, 0.12), (0, 2.6, P + 1.06), STONE_LIGHT, grad=(0.1, 0.6))
	p.seg((0, 2.75, P + 2.0), (0, 2.65, P + 2.0), 0.6, 0.6, GOLD, sides=16, glow=0.35)
	for k in range(12):
		a = k * math.tau / 12
		p.seg((math.cos(a) * 0.58, 2.7, P + 2.0 + math.sin(a) * 0.58), (math.cos(a) * 0.9, 2.7, P + 2.0 + math.sin(a) * 0.9), 0.07, 0.0, GOLD, sides=4, glow=0.3)
	p.seg((0, 2.7, P + 1.12), (0, 2.7, P + 1.4), 0.06, 0.06, GOLD, sides=6)
	# --- the lower roof, resting on the colonnade beams ------------------------
	z_eave = top + 0.25
	_swept_roof(p, (6.7, 4.85, z_eave), (4.85, 3.0, z_eave + 1.35), 0.75, bands=4, thick=0.24, swatch=CLAY)
	# the clerestory between the tiers: plaster panels in red posts
	cz0, cz1 = top + 1.3, top + 2.55
	p.box((9.5, 5.8, cz1 - cz0), (0, 0, (cz0 + cz1) / 2), BONE, grad=(0.15, 0.7))
	for x in (-4.75, -2.4, 0.0, 2.4, 4.75):
		for y in (-2.9, 2.9):
			p.box((0.22, 0.22, cz1 - cz0), (x, y, (cz0 + cz1) / 2), CLOTH_RED, grad=(0.1, 0.8))
	for y in (-1.45, 1.45):
		for x in (-4.75, 4.75):
			p.box((0.22, 0.22, cz1 - cz0), (x, y, (cz0 + cz1) / 2), CLOTH_RED, grad=(0.1, 0.8))
	p.box((9.7, 6.0, 0.2), (0, 0, cz1 - 0.05), CHAR, grad=(0.5, 1.0))          # the dark loft, seen through the hole
	# --- the upper roof, with a hole fallen through its front ------------------
	z_up = cz1 + 0.1
	ridge_z = z_up + 2.4
	_swept_roof(p, (5.6, 3.7, z_up), (2.7, 0.14, ridge_z), 0.6, bands=4, thick=0.22, swatch=CLAY, hole=(0, 1, 4, 7))
	_ridge(p, 2.75, ridge_z, r=0.17, curl=0.75)
	p.seg((0, 0.06, ridge_z + 0.95), (0, -0.06, ridge_z + 0.95), 0.42, 0.42, GOLD, sides=14, glow=0.3)   # the dawn sun on the ridge
	p.seg((0, 0, ridge_z + 0.1), (0, 0, ridge_z + 0.55), 0.09, 0.09, GOLD, sides=6)
	# rafters showing through the hole
	for x in (0.55, 1.35, 2.15):
		p.seg((x, -2.95, z_up + 0.35), (x * 0.8, -1.2, z_up + 1.35), 0.07, 0.07, WOOD, sides=5, grad=(0.3, 1.0))
	obj = p.build(bevel=0.05)
	# --- fallen tiles, on the lower roof and the ground ------------------------
	for x, y, z, yaw, tilt in ((1.4, -4.35, z_eave + 0.12, 20, 12), (2.1, -4.1, z_eave + 0.25, -30, 18), (4.4, -6.0, 0.06, 40, 4),
							   (3.6, -6.4, 0.06, -10, 8), (5.0, -5.3, 0.08, 70, 15), (2.7, -5.8, 0.05, 5, 0), (6.3, -4.9, 0.06, -40, 10)):
		d.box((0.5, 0.36, 0.08), (x, y, z), CLAY, rot=(tilt, 0, yaw), grad=(0.0, 0.7))
	for k in range(4):
		d.rock((0.35, 0.3, 0.2), (3.0 + k * 0.7, -5.2 - k * 0.35, 0.08), STONE_LIGHT)
	extra = d.build()
	# --- the room: KayKit walls and pillars, as in the houses -------------------
	tall = 0.8                                   # 3.2 m walls
	room_x, y0, y1 = 4.5, -2.0, 3.4
	side_scale = (y1 - y0) / 2 / 4.0
	pieces = []
	for x, piece in ((-3.0, "wall_window_open"), (0.0, "wall_doorway"), (3.0, "wall_cracked")):
		pieces += kaykit(piece, (x, y0 + 0.375, P), 0.0, (0.75, 0.75, tall))
	for x, piece in ((-3.0, "wall"), (0.0, "wall_broken"), (3.0, "wall")):
		pieces += kaykit(piece, (x, y1 - 0.375, P), math.pi, (0.75, 0.75, tall))
	for side in (-1, 1):
		for k, piece in enumerate(("wall", "wall_window_open" if side < 0 else "wall_cracked")):
			y = y0 + (y1 - y0) * (k + 0.5) / 2
			pieces += kaykit(piece, (side * (room_x - 0.375), y, P), math.pi / 2 * -side, (side_scale, 0.75, tall))
	for x in (-room_x, room_x):
		for y in (y0, y1):
			pieces += kaykit("pillar", (x, y, P), 0.0, (0.6, 0.6, tall))
	return _merge_materials(join_into(obj, [extra] + pieces))


def monastery_gate():
	"""The monastery's ceremonial gateway, facing -Y: two red pillars 5.4 m
	apart on stone bases (a 4.9 m clear opening), two tie beams with a gilded
	sun plaque between them, and a two-tier tiled roof with upturned eaves,
	about 7.9 m wide and 7.4 m to the finials. Walk-through: collide it as a
	mesh so only the pillars (and the roof overhead) are solid."""
	p = Prop("monastery_gate", 203)
	X = 2.7
	for s in (-1, 1):
		x = s * X
		p.box((1.0, 1.0, 0.55), (x, 0, 0.27), STONE_LIGHT, grad=(0.1, 0.8))
		p.box((1.15, 1.15, 0.14), (x, 0, 0.6), STONE_WARM, grad=(0.1, 0.6))
		for y in (-1, 1):                       # stone braces front and back
			p.poly([(x - 0.18, y * 0.5, 0), (x + 0.18, y * 0.5, 0), (x + 0.18, y * 1.15, 0), (x - 0.18, y * 1.15, 0),
					(x - 0.18, y * 0.5, 1.3), (x + 0.18, y * 0.5, 1.3)],
				   [(0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 2), (0, 3, 4), (3, 2, 5, 4)], STONE_LIGHT, grad=(0.1, 0.8))
		p.seg((x, 0, 0.67), (x, 0, 5.0), 0.26, 0.24, CLOTH_RED, sides=10, grad=(0.1, 0.95))
		p.seg((x, 0, 0.67), (x, 0, 0.9), 0.3, 0.3, GOLD, sides=10, grad=(0.1, 0.6))
	p.box((2 * X + 1.3, 0.34, 0.36), (0, 0, 3.6), CLOTH_RED, grad=(0.1, 0.8))       # lower tie beam
	p.box((2 * X + 1.9, 0.42, 0.42), (0, 0, 4.72), CLOTH_RED, grad=(0.1, 0.8))      # upper beam
	p.box((2 * X + 1.95, 0.46, 0.08), (0, 0, 4.5), GOLD, grad=(0.1, 0.5))
	for s in (-1, 1):
		p.box((0.18, 0.2, 0.8), (s * 0.75, 0, 4.15), CLOTH_RED, grad=(0.1, 0.8))
	p.box((1.3, 0.16, 0.74), (0, 0, 4.15), WOOD, grad=(0.3, 1.0))                  # the plaque
	p.seg((0, -0.09, 4.15), (0, -0.12, 4.15), 0.26, 0.26, GOLD, sides=14, glow=0.3)
	p.seg((0, 0.09, 4.15), (0, 0.12, 4.15), 0.26, 0.26, GOLD, sides=14, glow=0.3)
	for x in (-2.0, -1.2, 1.2, 2.0, -3.3, 3.3):                                     # brackets under the roof
		p.box((0.36, 0.6, 0.3), (x, 0, 5.05), WOOD, grad=(0.2, 0.9))
	_swept_roof(p, (4.0, 1.15, 5.3), (3.2, 0.12, 6.0), 0.45, bands=3, thick=0.2, swatch=CLAY, n=8)
	_ridge(p, 3.25, 6.0, r=0.12, curl=0.45, finial=False)
	p.box((1.9, 0.5, 0.75), (0, 0, 6.3), CLOTH_RED, grad=(0.1, 0.8))               # the upper tier's block
	p.box((1.3, 0.12, 0.45), (0, -0.27, 6.3), GOLD, grad=(0.1, 0.5))
	_swept_roof(p, (1.6, 0.85, 6.65), (1.0, 0.1, 7.15), 0.32, bands=2, thick=0.16, swatch=CLAY, n=6)
	_ridge(p, 1.0, 7.15, r=0.1, curl=0.35)
	return p.build(bevel=0.04)


def stupa():
	"""A whitewashed stupa of the Dawn-Tusk: a stepped square base, a dome, a
	painted harmika and a gold spire, about 5.2 m tall on a 4.4 m plinth, a
	gilded elephant head in a niche at the front (-Y) and prayer flags strung
	from the spire to the corners. Collide it as a box."""
	p = Prop("stupa", 204)
	p.box((4.4, 4.4, 0.35), (0, 0, 0.17), STONE_WARM, grad=(0.2, 0.9))
	for k, (w, z0, h) in enumerate(((3.8, 0.35, 0.45), (3.25, 0.8, 0.4), (2.8, 1.2, 0.35))):
		p.box((w, w, h), (0, 0, z0 + h / 2), CLOTH_WHITE, grad=(0.05, 0.6))
		p.box((w + 0.12, w + 0.12, 0.08), (0, 0, z0 + h), BONE, grad=(0.1, 0.5))
	p.seg((0, 0, 1.55), (0, 0, 1.8), 1.3, 1.25, CLOTH_WHITE, sides=18, grad=(0.1, 0.6))
	p.blob((2.4, 2.4, 2.1), (0, 0, 1.78), CLOTH_WHITE, segs=(18, 12), grad=(0.0, 0.55))       # the dome
	p.seg((0, 0, 2.45), (0, 0, 2.55), 1.13, 1.1, GOLD, sides=18, grad=(0.1, 0.5))             # gilt band
	p.box((0.85, 0.85, 0.5), (0, 0, 3.05), CLOTH_WHITE, grad=(0.05, 0.5))                    # harmika
	p.box((1.05, 1.05, 0.1), (0, 0, 3.33), GOLD, grad=(0.1, 0.5))
	for s in (-1, 1):                                                                          # painted eyes
		p.blob((0.2, 0.05, 0.08), (s * 0.18, -0.43, 3.1), IRON, segs=(6, 3))
		p.blob((0.1, 0.05, 0.05), (s * 0.16, -0.44, 3.1), RUNE, segs=(5, 3))
	for k in range(9):                                                                         # the rings of the spire
		z = 3.4 + k * 0.14
		r = 0.36 - k * 0.025
		p.seg((0, 0, z), (0, 0, z + 0.1), r, r - 0.03, GOLD, sides=12, grad=(0.25, 0.8), glow=0.15)
	p.seg((0, 0, 4.7), (0, 0, 4.78), 0.42, 0.3, GOLD, sides=12, grad=(0.0, 0.5), glow=0.15)   # parasol
	p.blob((0.2, 0.2, 0.26), (0, 0, 4.92), GOLD, grad=(0.0, 0.4), glow=0.2)
	p.seg((0, 0, 5.0), (0, 0, 5.3), 0.05, 0.0, GOLD, sides=6, glow=0.2)
	# the niche and its elephant
	p.box((1.05, 0.3, 1.2), (0, -1.45, 1.15), STONE_WARM, grad=(0.1, 0.8))
	p.box((0.8, 0.1, 0.9), (0, -1.6, 1.12), IRON, grad=(0.5, 0.9))
	p.seg((0, -1.45, 1.75), (0, -1.45, 1.95), 0.5, 0.0, STONE_WARM, sides=4, twist=45)
	obj = p.build(bevel=0.04)
	d = Prop("stupa_detail", 205)
	_elephant_head(d, (0, -1.72, 1.25), 0.34, swatch=GOLD, trunk=[(0, -0.4, -0.1), (0, -0.5, -0.45), (0, -0.45, -0.75), (0, -0.55, -0.95)])
	d.box((0.5, 0.25, 0.1), (0, -1.75, 0.66), STONE_LIGHT)                                   # offering ledge
	for x in (-0.15, 0.15):
		d.blob((0.1, 0.1, 0.08), (x, -1.78, 0.75), CLOTH_RED if x < 0 else FLAG_YELLOW, segs=(6, 4))
	for k, (cx, cy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
		_flag_line(d, (0, 0, 4.55), (cx * 2.1, cy * 2.1, 0.4), 0.35, spacing=0.36, size=(0.2, 0.26), start=k)
	return join_into(obj, [d.build()])


def _prayer_flags(name, span, height, sag):
	p = Prop(name, 206 if span > 5 else 207)
	half = span / 2
	for x in (-half, half):
		p.seg((x, 0, -0.2), (x, 0, height), 0.055, 0.045, WOOD, sides=6, grad=(0.2, 1.0))
		p.blob((0.12, 0.12, 0.16), (x, 0, height + 0.05), GOLD, grad=(0.0, 0.5))
		p.box((0.1, 0.02, 0.9), (x + (0.06 if x < 0 else -0.06), 0, height - 0.55), FLAG_COLORS[0 if x < 0 else 2], grad=(0.05, 0.45))
		p.rock((0.4, 0.35, 0.25), (x, 0, 0.02), STONE_DARK)
	_flag_line(p, (-half, 0, height - 0.15), (half, 0, height - 0.15), sag)
	_flag_line(p, (-half, 0, height - 0.5), (half, 0, height - 0.5), sag * 0.9, spacing=0.5, size=(0.26, 0.32), start=2)
	return p.build()


def prayer_wheel():
	"""A prayer wheel under a little tiled roof: a red and gold drum turning on
	an iron axle between two posts, waist high (0.5 to 1.15 m), about 2.5 m to
	the finials and 1.4 m wide. Collide it as a box."""
	p = Prop("prayer_wheel", 208)
	p.box((1.4, 1.1, 0.25), (0, 0, 0.12), STONE_LIGHT, grad=(0.1, 0.8))
	for s in (-1, 1):
		p.seg((s * 0.58, 0, 0.25), (s * 0.58, 0, 1.95), 0.075, 0.07, CLOTH_RED, sides=8, grad=(0.1, 0.9))
	p.box((1.4, 0.16, 0.14), (0, 0, 1.45), WOOD, grad=(0.2, 0.9))
	p.box((1.5, 0.2, 0.16), (0, 0, 1.97), CLOTH_RED, grad=(0.1, 0.8))
	p.seg((0, 0, 0.25), (0, 0, 1.45), 0.025, 0.025, IRON, sides=6)
	p.seg((0, 0, 0.5), (0, 0, 1.15), 0.3, 0.3, CLOTH_RED, sides=14, grad=(0.1, 0.8))
	for z in (0.5, 0.82, 1.15):
		p.seg((0, 0, z - 0.03), (0, 0, z + 0.03), 0.32, 0.32, GOLD, sides=14, grad=(0.1, 0.5))
	for k in range(10):                                         # gilt letters round the drum
		a = k * math.tau / 10
		for z in (0.66, 0.98):
			p.box((0.09, 0.03, 0.13), (math.cos(a) * 0.3, math.sin(a) * 0.3, z), GOLD, rot=(0, 0, math.degrees(a) + 90), grad=(0.0, 0.4))
	p.seg((0, 0, 1.15), (0, 0, 1.3), 0.3, 0.06, GOLD, sides=14, grad=(0.0, 0.5))
	p.seg((0.3, 0, 0.55), (0.42, 0, 0.55), 0.03, 0.03, WOOD, sides=5)        # the peg a pilgrim turns it by
	_swept_roof(p, (0.95, 0.68, 2.1), (0.4, 0.06, 2.5), 0.18, bands=2, thick=0.1, swatch=CLAY, n=6)
	_ridge(p, 0.42, 2.5, r=0.06, curl=0.18)
	return p.build(bevel=0.02)


def stone_lantern():
	"""A stone lantern for the monastery paths, about 1.65 m: a hexagonal foot
	and shaft, a fire box with a glowing window on every side, a hat with
	upturned corners and a jewel finial. Collide it as a box."""
	p = Prop("stone_lantern", 209)
	p.seg((0, 0, 0), (0, 0, 0.16), 0.38, 0.36, STONE_LIGHT, sides=6, grad=(0.2, 0.9))
	p.seg((0, 0, 0.16), (0, 0, 0.26), 0.26, 0.2, STONE_WARM, sides=6, grad=(0.1, 0.8))
	p.seg((0, 0, 0.26), (0, 0, 0.72), 0.13, 0.12, STONE_LIGHT, sides=6, grad=(0.1, 0.9))
	p.seg((0, 0, 0.72), (0, 0, 0.84), 0.18, 0.32, STONE_WARM, sides=6, grad=(0.1, 0.8))
	for k in range(4):                                           # the fire box: four corner posts
		a = k * math.tau / 4 + math.pi / 4
		p.box((0.09, 0.09, 0.34), (math.cos(a) * 0.23, math.sin(a) * 0.23, 1.01), STONE_LIGHT, grad=(0.1, 0.8))
	p.box((0.38, 0.38, 0.05), (0, 0, 0.865), STONE_LIGHT, grad=(0.2, 0.7))
	p.box((0.3, 0.3, 0.3), (0, 0, 1.02), EMBER, grad=(0.05, 0.35), glow=1.8)
	p.seg((0, 0, 1.18), (0, 0, 1.24), 0.3, 0.3, STONE_LIGHT, sides=4, twist=45)
	p.seg((0, 0, 1.24), (0, 0, 1.46), 0.5, 0.1, STONE_LIGHT, sides=4, twist=45, grad=(0.0, 0.8))   # the hat
	for k in range(4):
		a = k * math.tau / 4
		p.seg((math.cos(a) * 0.42, math.sin(a) * 0.42, 1.24), (math.cos(a) * 0.47, math.sin(a) * 0.47, 1.33), 0.05, 0.025, STONE_LIGHT, sides=4)
	p.seg((0, 0, 1.44), (0, 0, 1.5), 0.08, 0.08, STONE_WARM, sides=6)
	p.blob((0.16, 0.16, 0.2), (0, 0, 1.56), STONE_LIGHT, grad=(0.0, 0.6))
	p.seg((0, 0, 1.6), (0, 0, 1.68), 0.05, 0.0, STONE_LIGHT, sides=6)
	p.blob((0.26, 0.2, 0.05), (0.1, -0.08, 1.37), MOSS, rot=(0, -18, 30), grad=(0.1, 0.6))
	return p.build(bevel=0.015)


def tea_bush():
	"""A clipped tea shrub for the terraces: a low, dense rounded hedge about
	0.8 m tall and 1.1 m across, bright new leaves on top. One material (fine
	as clutter). Collide: none."""
	p = Prop("tea_bush", 210)
	p.blob((1.15, 1.0, 0.8), (0, 0, 0.38), LEAF, segs=(10, 6), grad=(0.5, 1.0), jitter=0.04)
	p.blob((0.7, 0.65, 0.5), (0.3, 0.2, 0.52), LEAF, segs=(8, 5), grad=(0.4, 0.9), jitter=0.03)
	p.blob((0.65, 0.6, 0.5), (-0.3, -0.15, 0.5), LEAF, segs=(8, 5), grad=(0.4, 0.9), jitter=0.03)
	for k in range(8):                                          # the bright flush of new leaves on top
		a = k * math.tau / 8 + 0.3
		r = 0.32 if k % 2 else 0.15
		p.blob((0.22, 0.2, 0.07), (math.cos(a) * r, math.sin(a) * r, 0.74 - r * 0.25), LEAF, segs=(6, 3), grad=(0.1, 0.3))
	return p.build()


def rice_shoots():
	"""A clump of young rice for flooded paddies, about 0.45 m: bright green
	blades fanning out from one root, each a thin wedge so it reads from both
	sides. Low poly, one material: made for clutter."""
	p = Prop("rice_shoots", 211)
	for k in range(13):
		a = k * math.tau / 13 + p.rng.uniform(-0.2, 0.2)
		r = p.rng.uniform(0.0, 0.06)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(0.3, 0.48)
		lean = p.rng.uniform(0.08, 0.2) * (h / 0.4)
		w = p.rng.uniform(0.018, 0.026)
		n = (-math.sin(a) * w, math.cos(a) * w)
		tip = (x + math.cos(a) * lean, y + math.sin(a) * lean, h)
		back = (x - math.cos(a) * 0.012, y - math.sin(a) * 0.012, 0.0)
		p.poly([(x - n[0], y - n[1], 0), (x + n[0], y + n[1], 0), tip, back], [(0, 1, 2), (1, 3, 2), (3, 0, 2), (0, 3, 1)],
			   LEAF, grad=(0.0, 0.55))
	return p.build()


def harpy_nest():
	"""A harpy's nest on a crag: a messy ring of sticks about 3 m across and
	0.9 m high round a bowl of down, three speckled eggs, bones and a skull
	among the sticks. Collide it as a box."""
	p = Prop("harpy_nest", 212)
	p.blob((2.7, 2.7, 0.5), (0, 0, 0.12), WOOD_GRAY, segs=(12, 6), grad=(0.3, 1.0), jitter=0.05)
	p.blob((1.9, 1.9, 0.32), (0, 0, 0.42), HIDE, segs=(12, 6), grad=(0.2, 0.8))              # the down in the bowl
	for layer, (R, z, n) in enumerate(((1.25, 0.3, 16), (1.2, 0.52, 14), (1.1, 0.72, 11))):
		for k in range(n):
			a = k * math.tau / n + p.rng.uniform(-0.2, 0.2) + layer * 0.3
			c = Vector((math.cos(a) * R, math.sin(a) * R, z + p.rng.uniform(-0.06, 0.06)))
			t = Vector((-math.sin(a), math.cos(a), 0)).lerp(Vector((math.cos(a), math.sin(a), 0)), p.rng.uniform(-0.5, 0.5))
			t.z = p.rng.uniform(-0.25, 0.25)
			L = p.rng.uniform(0.7, 1.4)
			r = p.rng.uniform(0.035, 0.06)
			p.seg(tuple(c - t * L / 2), tuple(c + t * L / 2), r, r * 0.7, WOOD if (k + layer) % 3 else WOOD_GRAY, sides=5, grad=(0.2, 1.0))
	for k in range(7):                                         # sticks poking out
		a = p.rng.uniform(0, math.tau)
		p.seg((math.cos(a) * 1.0, math.sin(a) * 1.0, 0.5), (math.cos(a) * 1.9, math.sin(a) * 1.9, p.rng.uniform(0.2, 0.9)), 0.035, 0.015, WOOD_GRAY, sides=4)
	for k, (x, y) in enumerate(((-0.18, 0.05), (0.2, 0.12), (0.02, -0.22))):
		p.blob((0.3, 0.3, 0.4), (x, y, 0.72), CLOTH_WHITE if k != 1 else BONE, segs=(8, 6), rot=(p.rng.uniform(-15, 15), p.rng.uniform(-15, 15), 0), grad=(0.0, 0.5))
		for j in range(3):
			a = p.rng.uniform(0, math.tau)
			p.blob((0.05, 0.05, 0.04), (x + math.cos(a) * 0.13, y + math.sin(a) * 0.13, 0.72 + p.rng.uniform(-0.05, 0.12)), WOOD, segs=(4, 3))
	for k in range(5):                                         # feathers
		a = p.rng.uniform(0, math.tau)
		p.blob((0.5, 0.1, 0.03), (math.cos(a) * 0.65, math.sin(a) * 0.65, 0.62), CLOTH_WHITE if k % 2 else WOOD_GRAY, rot=(0, 20, math.degrees(a)), segs=(6, 3))
	obj = p.build(bevel=0.0)
	d = Prop("harpy_nest_bones", 213)
	_skull(d, (0.95, -0.7, 0.72), s=1.3, yaw=-0.7)
	_bone(d, (-1.2, -0.4, 0.8), (-0.6, -1.1, 0.75), r=0.03)
	_bone(d, (-0.3, 1.25, 0.85), (0.5, 1.05, 0.78), r=0.03)
	_bone(d, (1.5, 0.6, 0.35), (1.1, 1.3, 0.45), r=0.028)
	return join_into(obj, [d.build()])


def broken_pillar():
	"""A carved temple pillar snapped off about 2.8 m up, its broken top rough
	but flat enough for a gargoyle to perch on, on a two-step base; the fallen
	upper drum and its capital lie beside it to +X. About 4.2 x 2.4 m. Collide
	it as a mesh (or a box round the standing part)."""
	p = Prop("broken_pillar", 214)
	p.box((1.6, 1.6, 0.4), (0, 0, 0.2), STONE_WARM, grad=(0.2, 0.9))
	p.box((1.25, 1.25, 0.25), (0, 0, 0.52), STONE_LIGHT, grad=(0.1, 0.7))
	p.seg((0, 0, 0.64), (0, 0, 2.62), 0.5, 0.46, STONE_LIGHT, sides=8, grad=(0.05, 0.9), twist=22.5)
	for z in (0.8, 1.95):
		p.seg((0, 0, z), (0, 0, z + 0.16), 0.55, 0.55, STONE_WARM, sides=8, grad=(0.1, 0.7), twist=22.5)
	for k in range(8):                                          # a carved band of sun rays
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.45, math.sin(a) * 0.45, 1.3), (math.cos(a) * 0.52, math.sin(a) * 0.52, 1.6), 0.08, 0.02, STONE_WARM, sides=4)
	for k in range(6):                                          # the snapped top
		a = k * math.tau / 6 + 0.3
		h = 2.62 + (0.22 if k in (1, 2) else 0.08) + p.rng.uniform(0, 0.08)
		p.rock((0.42, 0.36, 0.3), (math.cos(a) * 0.26, math.sin(a) * 0.26, h - 0.1), STONE_LIGHT, jitter=0.05)
	p.seg((0, 0, 2.6), (0, 0, 2.72), 0.44, 0.4, STONE_LIGHT, sides=8, twist=22.5, jitter=0.03)
	# the fallen section and its capital
	a, b = Vector((0.95, 0.45, 0.46)), Vector((3.0, 1.1, 0.46))
	p.seg(tuple(a), tuple(b), 0.46, 0.46, STONE_LIGHT, sides=8, grad=(0.1, 0.9), twist=10)
	p.seg(tuple(a.lerp(b, 0.5) - Vector((0.08, 0, 0))), tuple(a.lerp(b, 0.5) + Vector((0.08, 0.03, 0))), 0.51, 0.51, STONE_WARM, sides=8, twist=10)
	p.box((1.05, 1.05, 0.45), (3.35, 1.22, 0.5), STONE_WARM, rot=(0, 90, 18), grad=(0.1, 0.8))
	p.box((1.25, 1.25, 0.2), (3.63, 1.3, 0.62), STONE_LIGHT, rot=(0, 90, 18), grad=(0.1, 0.8))
	for k in range(5):
		p.rock((0.4, 0.35, 0.25), (p.rng.uniform(0.7, 2.2), p.rng.uniform(-0.6, -0.1), 0.06), STONE_LIGHT)
	p.blob((0.7, 0.5, 0.08), (-0.25, -0.1, 0.78), MOSS, grad=(0.1, 0.6))
	return p.build(bevel=0.03)


def pilgrim_shelter():
	"""A pilgrims' rest: an open-sided timber shelter 4 x 3 m on a low plank
	floor, a thatched gable roof (ridge along X, 3.2 m) with prayer flags along
	its front eave, two bedrolls, a pot and a bench inside. Faces -Y. Collide it
	as a mesh (the sides are open)."""
	p = Prop("pilgrim_shelter", 215)
	hw, hd = 2.0, 1.5
	p.box((2 * hw + 0.2, 2 * hd + 0.2, 0.22), (0, 0, 0.11), STONE_DARK, grad=(0.3, 1.0))
	for k in range(9):                                          # floor planks
		x = -hw + (k + 0.5) * 2 * hw / 9
		p.box((2 * hw / 9 - 0.03, 2 * hd, 0.08), (x, 0, 0.26), WOOD if k % 3 else WOOD_GRAY, grad=(0.2, 0.9))
	posts = [(x, y) for x in (-hw, 0.0, hw) for y in (-hd, hd)]
	eave = 2.15
	for x, y in posts:
		p.seg((x, y, 0.0), (x, y, eave), 0.1, 0.09, WOOD, sides=6, grad=(0.2, 1.0))
	for y in (-hd, hd):
		p.box((2 * hw + 0.3, 0.16, 0.18), (0, y, eave - 0.02), WOOD, grad=(0.2, 0.9))
	for x in (-hw, 0.0, hw):
		p.box((0.16, 2 * hd + 0.3, 0.18), (x, 0, eave - 0.02), WOOD, grad=(0.2, 0.9))
		p.seg((x, 0, eave), (x, 0, 3.05), 0.07, 0.07, WOOD, sides=5)
	# the roof: a board sheet each side under courses of thatch
	ridge = 3.15
	Y = hd + 0.55
	ang = math.atan2(ridge - (eave - 0.25), Y)
	slope = math.hypot(Y, ridge - (eave - 0.25))
	for s in (-1, 1):
		down = Vector((0, math.cos(ang) * s, -math.sin(ang)))
		out = Vector((0, math.sin(ang) * s, math.cos(ang)))
		base = Vector((0, 0, ridge))
		p.box((2 * hw + 1.0, slope, 0.1), base + down * slope / 2, WOOD_GRAY, rot=(-math.degrees(ang) * s, 0, 0), grad=(0.2, 0.8))
		for i in range(4):
			c = base + down * slope * (i + 0.55) / 4 + out * 0.14
			p.box((2 * hw + 1.1, slope / 4 * 1.2, 0.18), c, BAMBOO if i % 2 else HIDE, rot=(-math.degrees(ang) * s, 0, 0), grad=(0.0, 0.9))
	p.seg((-hw - 0.6, 0, ridge + 0.14), (hw + 0.6, 0, ridge + 0.14), 0.16, 0.16, BAMBOO, sides=6, grad=(0.1, 0.8))
	for s in (-1, 1):
		p.seg((s * (hw + 0.5), 0, ridge + 0.1), (s * (hw + 0.8), 0, ridge + 0.55), 0.07, 0.04, WOOD, sides=5)
	# inside: bedrolls, a bench, a pot on a trivet
	for x, sw in ((-1.2, CLOTH_RED), (-0.35, RUNE)):
		p.seg((x, -0.9, 0.42), (x, 0.9, 0.42), 0.14, 0.14, sw, sides=8, grad=(0.1, 0.8))
		p.seg((x, 0.85, 0.42), (x, 1.1, 0.42), 0.2, 0.2, HIDE, sides=8, grad=(0.1, 0.8))
	p.box((1.4, 0.4, 0.08), (1.1, 1.05, 0.72), WOOD, grad=(0.2, 0.9))
	for x in (0.5, 1.7):
		p.box((0.1, 0.34, 0.4), (x, 1.05, 0.5), WOOD, grad=(0.3, 1.0))
	p.seg((1.1, -0.7, 0.3), (1.1, -0.7, 0.62), 0.22, 0.26, IRON, sides=10, grad=(0.1, 0.8))
	p.seg((1.1, -0.7, 0.62), (1.1, -0.7, 0.66), 0.27, 0.27, IRON, sides=10)
	obj = p.build(bevel=0.03)
	d = Prop("pilgrim_shelter_flags", 216)
	_flag_line(d, (-hw, -hd - 0.12, 1.85), (hw, -hd - 0.12, 1.85), 0.25, spacing=0.36, size=(0.22, 0.28))
	return join_into(obj, [d.build()])


# ---------------------------------------------------------------- Cinderpass (the Ashfall)

CHAR = IRON     # burnt black wood and basalt: the pack's darkest swatch


def _glossy(obj, roughness):
	"""Give a built prop glassy materials (obsidian): copies of the palette
	material with low roughness."""
	for i, m in enumerate(obj.data.materials):
		g = m.copy()
		g.name = m.name + "_glass"
		g.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = roughness
		obj.data.materials[i] = g
	return obj


def _crack(p, pts, r=0.03, glow=1.4):
	"""A thin glowing ember crack along the points."""
	_chain(p, pts, r, r * 0.6, EMBER, sides=4, grad=(0.05, 0.4), glow=glow)


def _charred(name, seed, height, lean, branches, base_r):
	p = Prop(name, seed)
	rng = p.rng
	pts = []
	x = y = 0.0
	steps = 5
	for k in range(steps + 1):
		z = -0.3 + (height + 0.3) * k / steps
		pts.append((x, y, z))
		x += lean[0] / steps + rng.uniform(-0.12, 0.12)
		y += lean[1] / steps + rng.uniform(-0.12, 0.12)
	_chain(p, pts, base_r, base_r * 0.35, CHAR, sides=7, grad=(0.1, 0.8))
	top = Vector(pts[-1])
	p.rock((base_r * 1.2, base_r * 1.1, base_r * 0.9), tuple(top), CHAR, jitter=0.15)       # the splintered top
	for k in range(4):                                          # flared, burnt roots
		a = k * math.tau / 4 + rng.uniform(-0.3, 0.3)
		p.seg((0, 0, 0.6), (math.cos(a) * base_r * 2.4, math.sin(a) * base_r * 2.4, -0.15), base_r * 0.45, base_r * 0.2, CHAR, sides=5, grad=(0.2, 0.9))
	for z, a, L in branches:                                    # a few broken branches, pointing up and out
		t = (z + 0.3) / (height + 0.3)
		i = min(int(t * steps), steps - 1)
		base = Vector(pts[i]).lerp(Vector(pts[i + 1]), t * steps - i)
		d = Vector((math.cos(a), math.sin(a), 0.7)).normalized()
		mid = base + d * L * 0.55
		end = mid + Vector((math.cos(a + 0.4), math.sin(a + 0.4), 0.3)).normalized() * L * 0.45
		_chain(p, [tuple(base), tuple(mid), tuple(end)], base_r * 0.32, base_r * 0.1, CHAR, sides=5, grad=(0.1, 0.8))
	for k in range(3):                                          # ash-grey scorch where the bark burnt off
		a = rng.uniform(0, math.tau)
		z = rng.uniform(0.6, height * 0.6)
		t = (z + 0.3) / (height + 0.3)
		i = min(int(t * steps), steps - 1)
		c = Vector(pts[i]).lerp(Vector(pts[i + 1]), t * steps - i)
		r = base_r * (1 - 0.65 * t)
		p.blob((r * 0.9, r * 0.5, 0.5), (c.x + math.cos(a) * r * 0.75, c.y + math.sin(a) * r * 0.75, z), SHADE, rot=(0, 0, math.degrees(a) + 90), segs=(6, 4), grad=(0.55, 0.75))
	for k, (z0, a) in enumerate(((0.4, 0.8), (1.3, 3.3))):   # two glowing cracks near the foot
		pts_c = []
		for j in range(4):
			z = z0 + j * 0.35
			t = (z + 0.3) / (height + 0.3)
			i = min(int(t * steps), steps - 1)
			c = Vector(pts[i]).lerp(Vector(pts[i + 1]), t * steps - i)
			r = base_r * (1 - 0.65 * t) * 0.93
			aa = a + j * 0.12
			pts_c.append((c.x + math.cos(aa) * r, c.y + math.sin(aa) * r, z))
		_crack(p, pts_c, r=0.035)
	return p.build(bevel=0.0)


def charred_log():
	"""A fallen, burnt trunk about 3.6 m long along X, still smoldering: a
	glowing broken end and a crack along its top. Collide it as a box."""
	p = Prop("charred_log", 221)
	p.seg((-1.8, 0, 0.3), (1.8, 0.15, 0.25), 0.34, 0.27, CHAR, sides=7, grad=(0.1, 0.9))
	p.rock((0.55, 0.6, 0.55), (1.85, 0.15, 0.27), CHAR, jitter=0.12)                       # the splintered end
	p.seg((-1.83, 0, 0.3), (-1.86, 0, 0.3), 0.3, 0.3, EMBER, sides=7, grad=(0.1, 0.6), glow=1.1)   # the burnt-through end, glowing
	p.seg((-1.87, 0, 0.3), (-1.9, 0, 0.3), 0.18, 0.18, FLAME, sides=7, grad=(0.1, 0.5), glow=1.8)
	p.seg((0.2, 0.05, 0.5), (0.55, -0.35, 0.95), 0.08, 0.03, CHAR, sides=4)
	p.blob((0.7, 0.35, 0.12), (0.8, 0.1, 0.5), WOOD_GRAY, grad=(0.6, 1.0))
	_crack(p, [(-1.6, -0.02, 0.63), (-1.0, 0.03, 0.62), (-0.5, 0.0, 0.6)], r=0.03)
	return p.build()


def obsidian_spire():
	"""A cluster of jagged, glassy black obsidian shards, about 4.2 m tall and
	3 m across, a purple sheen on some faces. Glossy material. Collide it as a box."""
	p = Prop("obsidian_spire", 222)
	shards = [((0, 0), 4.2, 0.62, (0.05, 0.1)), ((0.75, 0.3), 2.8, 0.45, (0.35, 0.1)), ((-0.7, 0.25), 3.2, 0.5, (-0.3, 0.05)),
			  ((0.2, -0.75), 2.2, 0.4, (0.1, -0.35)), ((-0.35, 0.8), 1.9, 0.38, (-0.1, 0.3)), ((1.1, -0.5), 1.4, 0.32, (0.4, -0.2)),
			  ((-1.1, -0.45), 1.2, 0.3, (-0.4, -0.2)), ((0.6, 1.0), 1.1, 0.28, (0.2, 0.4))]
	for k, ((x, y), h, r, (lx, ly)) in enumerate(shards):
		sw = PETAL_PURPLE if k in (2, 5) else CHAR
		gr = (0.75, 1.0) if sw == PETAL_PURPLE else (0.0, 0.7)
		p.seg((x, y, -0.2), (x + lx * h * 0.35, y + ly * h * 0.35, h), r, 0.0, sw, sides=5, grad=gr, twist=k * 23)
	for k in range(7):
		a = k * math.tau / 7 + 0.2
		p.rock((0.55, 0.45, 0.35), (math.cos(a) * 1.25, math.sin(a) * 1.25, 0.05), CHAR, jitter=0.12)
	return _glossy(p.build(), 0.18)


def basalt_columns():
	"""A cluster of hexagonal basalt columns, 1.4 to 5 m tall, in a tight
	honeycomb about 3.5 m across, a few broken drums at the foot. Collide it
	as a box."""
	p = Prop("basalt_columns", 223)
	R = 0.42
	d = math.sqrt(3) * R + 0.02
	cells = [(0, 0)]
	for k in range(6):
		a = math.radians(30 + 60 * k)
		cells.append((math.cos(a) * d, math.sin(a) * d))
	for k in range(6):
		a = math.radians(60 * k)
		if k in (1, 2, 4):
			cells.append((math.cos(a) * d * math.sqrt(3), math.sin(a) * d * math.sqrt(3)))
	for k in range(6):
		a = math.radians(30 + 60 * k)
		if k in (0, 3):
			cells.append((math.cos(a) * d * 2, math.sin(a) * d * 2))
	for i, (x, y) in enumerate(cells):
		dist = math.hypot(x, y + 0.3)
		h = max(1.2, 5.0 - dist * 1.1 + p.rng.uniform(-0.5, 0.5))
		sw = STONE_DARK if i % 3 else CHAR
		gr = (0.3, 1.0) if sw == STONE_DARK else (0.0, 0.6)
		p.seg((x, y, -0.3), (x, y, h), R, R, sw, sides=6, grad=gr)
		p.seg((x, y, h), (x, y, h + 0.04), R * 0.92, R * 0.9, STONE_DARK, sides=6, grad=(0.1, 0.4))
	for (x, y, yaw) in ((1.9, -1.1, 20), (-1.6, -1.5, -35)):
		p.seg((x, y, 0.36), (x + math.cos(math.radians(yaw)) * 0.9, y + math.sin(math.radians(yaw)) * 0.9, 0.36), R, R, STONE_DARK, sides=6, grad=(0.3, 1.0))
	return p.build(bevel=0.04)


def lava_vent():
	"""A low cone of cracked black rock about 3.1 m across and 1.55 m tall,
	open at the top (the game adds smoke above it), molten rock glowing in its
	mouth and in a few cracks down its sides. Collide it as a box."""
	p = Prop("lava_vent", 224)
	prof = [(1.55, -0.1), (1.4, 0.3), (1.05, 0.85), (0.7, 1.38), (0.56, 1.52), (0.44, 1.48), (0.36, 1.2), (0.3, 0.85), (0.2, -0.1)]
	_lathe(p, prof, 11, CHAR, grad=(0.0, 0.8), jitter=0.13, keep=1.3)
	_lathe(p, [(0.33, 0.8), (0.33, 1.05), (0.2, 1.05), (0.2, 0.8)], 11, EMBER, grad=(0.0, 0.5), glow=1.6)
	p.seg((0, 0, 0.85), (0, 0, 0.98), 0.31, 0.3, EMBER, sides=11, grad=(0.1, 0.5), glow=2.0)   # the molten pool
	p.blob((0.4, 0.4, 0.14), (0, 0, 0.98), FLAME, segs=(8, 4), grad=(0.0, 0.4), glow=2.6)
	for k, a in enumerate((0.5, 2.3, 4.4)):                    # cracks running down the cone
		pts = []
		for j in range(4):
			t = j / 3
			r = 0.72 + (1.38 - 0.72) * t + 0.03
			z = 1.36 - (1.36 - 0.35) * t
			aa = a + math.sin(t * 3 + k) * 0.12
			pts.append((math.cos(aa) * r, math.sin(aa) * r, z))
		_crack(p, pts, r=0.045, glow=1.3)
	for k in range(9):
		a = k * math.tau / 9 + 0.3
		s = p.rng.uniform(0.35, 0.6)
		p.rock((s, s * 0.85, s * 0.6), (math.cos(a) * 1.6, math.sin(a) * 1.6, 0.05), STONE_DARK, grad=(0.4, 1.0))
	return p.build()


def ash_boulder(name, seed, parts):
	"""Dark volcanic rocks, pitted, with pale ash settled on their tops."""
	p = Prop(name, seed)
	for size, loc in parts:
		p.rock(size, loc, STONE_DARK, rot=(0, 0, p.rng.uniform(0, 360)), grad=(0.45, 1.0), jitter=0.11)
		sx, sy, sz = size
		p.blob((sx * 0.42, sy * 0.4, sz * 0.22), (loc[0], loc[1], loc[2] + sz * 0.3), SHADE, segs=(7, 4), grad=(0.35, 0.6), jitter=0.02)   # ash settled on top
	return p.build()


def cultist_brazier():
	"""An iron fire bowl on a tripod, rim at 1.45 m, spiked, full of glowing
	coals and flames rising to about 2.3 m. Collide it as a box."""
	p = Prop("cultist_brazier", 225)
	for k in range(3):
		a = k * math.tau / 3 + math.pi / 2
		foot = (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.0)
		knee = (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.6)
		_chain(p, [foot, knee, (math.cos(a) * 0.22, math.sin(a) * 0.22, 1.15)], 0.045, 0.035, IRON, sides=5, grad=(0.0, 0.7))
		p.blob((0.16, 0.16, 0.1), foot, IRON, segs=(6, 3))
		p.seg(knee, (math.cos(a + math.tau / 3) * 0.42, math.sin(a + math.tau / 3) * 0.42, 0.6), 0.025, 0.025, IRON, sides=4)
	p.seg((0, 0, 1.0), (0, 0, 1.12), 0.1, 0.2, IRON, sides=8)
	_lathe(p, [(0.18, 1.08), (0.5, 1.22), (0.62, 1.42), (0.64, 1.47), (0.56, 1.45), (0.46, 1.28), (0.16, 1.15)], 12, IRON, grad=(0.0, 0.7))
	for k in range(8):                                          # spikes round the rim
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.62, math.sin(a) * 0.62, 1.45), (math.cos(a) * 0.72, math.sin(a) * 0.72, 1.68), 0.04, 0.0, IRON, sides=4)
	p.blob((1.05, 1.05, 0.2), (0, 0, 1.38), EMBER, segs=(10, 4), grad=(0.3, 0.8), glow=1.2)
	for loc, r, h in (((0, 0, 1.4), 0.3, 0.9), ((0.2, 0.1, 1.4), 0.2, 0.6), ((-0.18, -0.08, 1.4), 0.2, 0.55), ((0.02, -0.22, 1.4), 0.16, 0.45)):
		p.seg(loc, (loc[0], loc[1], loc[2] + h), r, 0.0, FLAME, sides=6, grad=(0.1, 0.95), glow=1.4, twist=p.rng.uniform(0, 60))
	for k in range(3):                                          # a band of ember-red cloth on each leg
		a = k * math.tau / 3 + math.pi / 2
		p.seg((math.cos(a) * 0.33, math.sin(a) * 0.33, 0.85), (math.cos(a) * 0.31, math.sin(a) * 0.31, 0.95), 0.06, 0.06, CLOTH_RED, sides=5, grad=(0.4, 1.0))
	return p.build()


def ember_banner():
	"""The Ashfall cult's standard: a black banner with an ember-red border and
	a flame sigil (both faces), on a 5 m iron pole with a flame-tipped spike,
	the cloth's tail split in two. Faces -Y. Collide it as a trunk."""
	p = Prop("ember_banner", 226)
	p.seg((0, 0, -0.2), (0, 0, 4.8), 0.065, 0.05, IRON, sides=6, grad=(0.0, 0.8))
	p.seg((0, 0, 4.8), (0, 0, 5.3), 0.07, 0.0, IRON, sides=4)
	p.blob((0.14, 0.14, 0.2), (0, 0, 4.85), EMBER, grad=(0.1, 0.5), glow=0.8)
	p.seg((-0.78, 0, 4.5), (0.78, 0, 4.5), 0.045, 0.045, IRON, sides=5)
	for s in (-1, 1):
		p.blob((0.1, 0.1, 0.1), (s * 0.8, 0, 4.5), IRON, segs=(6, 4))
	top, bot, w = 4.42, 2.1, 1.3
	p.box((w, 0.04, top - bot), (0, -0.06, (top + bot) / 2), CHAR, grad=(0.1, 0.7))
	_plate(p, [(-w / 2, bot + 0.01), (-0.05, bot + 0.01), (-w / 4, bot - 0.65)], -0.06, 0.04, CHAR, grad=(0.3, 0.8))    # the split tail
	_plate(p, [(0.05, bot + 0.01), (w / 2, bot + 0.01), (w / 4, bot - 0.65)], -0.06, 0.04, CHAR, grad=(0.3, 0.8))
	for s in (-1, 1):
		y = -0.06 + s * 0.025
		p.box((0.1, 0.02, top - bot), (-w / 2 + 0.08, y, (top + bot) / 2), CLOTH_RED, grad=(0.3, 0.9))
		p.box((0.1, 0.02, top - bot), (w / 2 - 0.08, y, (top + bot) / 2), CLOTH_RED, grad=(0.3, 0.9))
		p.box((w, 0.02, 0.1), (0, y, top - 0.08), CLOTH_RED, grad=(0.3, 0.9))
		cz = 3.15
		flame = [(0.0, cz + 0.75), (0.12, cz + 0.4), (0.3, cz + 0.52), (0.36, cz + 0.05), (0.26, cz - 0.3), (0.0, cz - 0.42),
				 (-0.26, cz - 0.3), (-0.36, cz + 0.0), (-0.28, cz + 0.35), (-0.14, cz + 0.22)]
		_plate(p, flame, -0.06 + s * 0.032, 0.012, EMBER, grad=(0.0, 0.6), glow=0.7)
		inner = [(0.0, cz + 0.32), (0.13, cz + 0.02), (0.1, cz - 0.2), (0.0, cz - 0.27), (-0.1, cz - 0.2), (-0.13, cz + 0.0)]
		_plate(p, inner, -0.06 + s * 0.04, 0.012, FLAME, grad=(0.0, 0.5), glow=1.0)
	p.rock((0.6, 0.55, 0.3), (0, 0, 0.05), STONE_DARK)
	return p.build()


def scout_tent():
	"""A Forgehold scouts' campaign tent: iron-grey canvas walls 1.3 m high
	under a deep red fly sheet (ridge 2.6 m, pole tops 2.9 m), 3 x 4 m, its
	door at the front (-Y) with the flaps rolled back, guy ropes to pegs and a
	red pennant. Collide it as a box."""
	p = Prop("scout_tent", 227)
	hw, hd, wall, ridge = 1.5, 2.0, 1.3, 2.55
	sec = [(-hw, 0.0), (hw, 0.0), (hw, wall), (0.0, ridge), (-hw, wall)]
	verts = [(x, -hd, z) for x, z in sec] + [(x, hd, z) for x, z in sec]
	p.poly(verts, [(0, 1, 2, 3, 4), (9, 8, 7, 6, 5), (0, 5, 6, 1), (1, 6, 7, 2), (2, 7, 8, 3), (3, 8, 9, 4), (4, 9, 5, 0)], STONE_LIGHT, grad=(0.3, 1.0))
	# the fly: two red slabs over the roof, overhanging
	ang = math.atan2(ridge - wall, hw)
	slope = math.hypot(hw, ridge - wall) + 0.45
	for s in (-1, 1):
		down = Vector((math.cos(ang) * s, 0, -math.sin(ang)))
		c = Vector((0, 0, ridge + 0.07)) + down * slope / 2
		p.box((slope, 2 * hd + 0.5, 0.06), tuple(c), CLOTH_RED, rot=(0, math.degrees(ang) * s, 0), grad=(0.7, 1.0))
		edge = Vector((0, 0, ridge + 0.07)) + down * slope
		for k in range(9):                                      # scalloped valance
			y = -hd - 0.25 + (k + 0.5) * (2 * hd + 0.5) / 9
			p.box((0.04, (2 * hd + 0.5) / 9 - 0.04, 0.2), (edge.x, y, edge.z - 0.1), IRON if k % 2 else CLOTH_RED, grad=(0.3, 1.0))
		for y in (-hd - 0.2, hd + 0.2):                        # guy ropes and pegs
			peg = (s * (hw + 1.1), y, 0.0)
			p.seg(tuple(edge + Vector((0, y, 0))), peg, 0.012, 0.012, HIDE, sides=3)
			p.seg((peg[0], peg[1], -0.1), (peg[0], peg[1], 0.18), 0.03, 0.025, WOOD, sides=4)
	# door: a dark opening, the flaps rolled and tied either side
	p.box((1.0, 0.05, 1.75), (0, -hd - 0.02, 0.87), CHAR, grad=(0.6, 1.0))
	p.poly([(-0.5, -hd - 0.025, 1.75), (0.5, -hd - 0.025, 1.75), (0.0, -hd - 0.025, 2.3),
			(-0.5, -hd - 0.05, 1.75), (0.5, -hd - 0.05, 1.75), (0.0, -hd - 0.05, 2.3)],
		   [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], CHAR, grad=(0.6, 1.0))
	for s in (-1, 1):
		p.seg((s * 0.62, -hd - 0.1, 0.05), (s * 0.55, -hd - 0.1, 2.05), 0.1, 0.08, STONE_LIGHT, sides=6, grad=(0.2, 0.9))
		p.seg((s * 0.6, -hd - 0.1, 1.0), (s * 0.6, -hd - 0.1, 1.1), 0.12, 0.12, CLOTH_RED, sides=6)
	# poles, and a pennant on the front one
	for y in (-hd - 0.05, hd + 0.05):
		p.seg((0, y, 0.0), (0, y, 2.95), 0.05, 0.045, WOOD, sides=5, grad=(0.2, 1.0))
		p.blob((0.1, 0.1, 0.1), (0, y, 2.97), IRON, segs=(6, 4))
	_plate(p, [(0.03, 2.9), (0.6, 2.78), (0.03, 2.62)], -hd - 0.05, 0.02, CLOTH_RED, grad=(0.1, 0.8))
	p.box((0.6, 0.05, 0.28), (-0.9, -hd - 0.03, 0.9), IRON, grad=(0.3, 0.9))      # a painted anvil badge by the door
	p.box((0.3, 0.05, 0.22), (-0.9, -hd - 0.04, 0.72), IRON, grad=(0.3, 0.9))
	return p.build(bevel=0.02)


def weapon_rack():
	"""A scouts' weapon rack, 1.9 m wide: A-frame ends, a top bar and a slotted
	foot bar, three spears and two axes leaning in it. Faces -Y. Collide it as a box."""
	p = Prop("weapon_rack", 228)
	hw = 0.95
	for x in (-hw, hw):
		for y in (-1, 1):
			p.seg((x, y * 0.4, 0.0), (x, y * 0.06, 1.45), 0.05, 0.045, WOOD, sides=5, grad=(0.2, 1.0))
		p.box((0.1, 0.62, 0.08), (x, 0, 0.45), WOOD, grad=(0.2, 0.9))
	p.seg((-hw - 0.1, 0, 1.42), (hw + 0.1, 0, 1.42), 0.055, 0.055, WOOD, sides=6)
	p.box((2 * hw, 0.3, 0.1), (0, 0.25, 0.2), WOOD_GRAY, grad=(0.2, 0.9))
	for k, x in enumerate((-0.6, -0.15, 0.3)):                 # spears
		foot = (x, 0.3, 0.22)
		tip = (x + 0.05, -0.25, 2.1)
		p.seg(foot, tip, 0.028, 0.025, WOOD, sides=5, grad=(0.1, 0.9))
		p.seg(tip, (x + 0.058, -0.34, 2.4), 0.05, 0.0, IRON, sides=4, grad=(0.0, 0.5))
		p.seg((x + 0.05, -0.245, 2.08), (x + 0.05, -0.255, 2.12), 0.04, 0.04, CLOTH_RED, sides=5)
	for k, x in enumerate((0.62, 0.8)):                         # axes, heads up
		foot = (x, 0.18, 0.22)
		top = (x - 0.02, -0.08, 1.6)
		p.seg(foot, top, 0.03, 0.028, WOOD, sides=5, grad=(0.1, 0.9))
		s = 1 if k else -1
		_plate(p, [(x - 0.02, 1.62), (x - 0.02 + s * 0.18, 1.68), (x - 0.02 + s * 0.3, 1.75), (x - 0.02 + s * 0.3, 1.38), (x - 0.02 + s * 0.18, 1.45), (x - 0.02, 1.5)],
			   -0.08, 0.04, IRON, grad=(0.0, 0.6))
	return p.build(bevel=0.01)


# ---------------------------------------------------------------- Long Monsoon west: Reedmere
# The misty reed marsh of the lost village of Veyamar: its rotting stilt
# decks, the pondkin's mud huts, the witch's hut. Water there is about 1 m
# deep; props that stand in it have their origin on the bed.

SEA_STONE = (2, 1)      # blue-gray: stone the flood has worn smooth
TEAL = (5, 1)           # light teal: patina, naga scales, heron eggs
SLIME = (6, 1)          # yellow-green into teal: a witch's brew
SCALE_GREEN = (0, 2)    # teal-green
CORAL_PINK = (2, 2)
CORAL_ORANGE = (4, 2)
CORAL_MAGENTA = (4, 1)
SHELL_PEACH = (7, 1)


def _move_parts(p, start, m):
	"""Transforms every part added since `start` (an index into p.parts) by m:
	tilt or sink a whole assembly after building it upright."""
	for obj in p.parts[start:]:
		obj.data.transform(m)


def _post_weed(p, x, y, r, z):
	"""Slime and weed round a post of radius r where the water line (z) meets
	it, a strand or two trailing up the wood."""
	for k in range(5):
		a = k * math.tau / 5 + p.rng.uniform(-0.3, 0.3)
		p.blob((r * 1.5, r * 1.1, 0.2), (x + math.cos(a) * r * 0.8, y + math.sin(a) * r * 0.8, z + p.rng.uniform(-0.04, 0.08)),
			   MOSS if k % 2 else LEAF, rot=(0, 0, math.degrees(a)), segs=(6, 4), grad=(0.1, 0.9))
	a = p.rng.uniform(0, math.tau)
	top = (x + math.cos(a) * r * 1.05, y + math.sin(a) * r * 1.05, z + p.rng.uniform(0.35, 0.8))
	p.seg(top, (top[0] + math.cos(a) * 0.05, top[1] + math.sin(a) * 0.05, z), 0.045, 0.03, MOSS, sides=4, grad=(0.2, 0.9))


def _weed_hang(p, top, length, r=0.04):
	"""A strand of weed hanging off a beam, wandering a little."""
	x, y, z = top
	pts = [(x, y, z)]
	for k in range(3):
		x += p.rng.uniform(-0.06, 0.06)
		y += p.rng.uniform(-0.06, 0.06)
		z -= length / 3
		pts.append((x, y, z))
	_chain(p, pts, r, r * 0.4, MOSS if p.rng.random() < 0.6 else LEAF, sides=4, grad=(0.2, 0.9))


def _moss_patch(p, x, y, z, sx, sy):
	"""A flat, lumpy patch of moss lying on planks: only a centimeter proud of them."""
	for k in range(3):
		p.blob((sx * p.rng.uniform(0.5, 0.8), sy * p.rng.uniform(0.5, 0.8), 0.03), (x + p.rng.uniform(-0.25, 0.25) * sx, y + p.rng.uniform(-0.25, 0.25) * sy, z),
			   MOSS if k else PINE, rot=(0, 0, p.rng.uniform(0, 180)), segs=(7, 3), grad=(0.5, 1.0))


def stilt_platform_broken():
	"""A rotting 9 x 9 m stilt deck of lost Veyamar: stilt_platform's frame, its
	+X+Y corner rotted through (planks gone, ragged ends, a joist snapped into
	the water, its piling broken off), the -X edge sagging, weed and slime on
	the pilings at the water line (0.8 m under the deck, as Rainhold's decks
	stand). The deck's top is the origin and is flat wherever planks remain:
	walkable for x in [-3.5, 4.5] outside the hole (x > 2.1 and y > 2.2)."""
	p = Prop("stilt_platform_broken", 301)
	soft = Prop("stilt_platform_broken_soft", 301)  # weed, slime, barnacles and coral: left unbeveled
	h = 4.5
	water = -0.8
	n = 30
	for k in range(n):
		y = -h + (k + 0.5) * 2 * h / n
		w = 2 * h / n - 0.03
		sw = WOOD_GRAY if p.rng.random() < 0.45 else WOOD
		x1 = h + p.rng.uniform(-0.05, 0.0)
		if y > 2.2:  # the rotten corner: planks broken off short
			x1 = 2.2 + p.rng.uniform(-0.05, 0.5) - (y - 2.2) * 0.2
			if k in (n - 3, n - 6):
				x1 = 0.6 + p.rng.uniform(0.0, 0.8)  # rotted further back
		x0 = -3.5
		p.box((x1 - x0, w, 0.08), ((x0 + x1) / 2, y, -0.04), sw, rot=(0, 0, p.rng.uniform(-0.3, 0.3)), grad=(0.1, 0.6))
		t = max(0.0, min(1.0, (y + 2.0) / 6.0))  # the sag deepens toward +Y
		a = math.radians(3 + 16 * t)
		L = h - 3.5 + p.rng.uniform(-0.15, 0.0)
		p.box((L, w, 0.08), (x0 - L / 2 * math.cos(a), y, -0.04 - L / 2 * math.sin(a)), sw, rot=(0, -math.degrees(a), 0), grad=(0.1, 0.6))
	for x in (-1.1, 1.1):  # joists under the planks
		p.box((0.16, 2 * h - 0.2, 0.22), (x, 0, -0.19), WOOD, grad=(0.3, 1.0))
	p.box((0.16, 5.4, 0.22), (-3.4, -1.6, -0.19), WOOD, grad=(0.3, 1.0))
	p.box((0.16, 6.3, 0.22), (3.4, -1.05, -0.19), WOOD, grad=(0.3, 1.0))
	p.box((0.16, 2.2, 0.2), (3.55, 2.9, -0.62), WOOD_GRAY, rot=(-24, 6, 0), grad=(0.3, 1.0))  # snapped, dropped into the water
	# the edge beams: whole at -Y, broken at +X and +Y, sagging along -X
	p.box((2 * h, 0.2, 0.36), (0, -h + 0.1, -0.18), WOOD, grad=(0.2, 0.9))
	p.box((0.2, 6.5, 0.36), (h - 0.1, -1.25, -0.18), WOOD, grad=(0.2, 0.9))
	p.box((6.6, 0.2, 0.36), (-1.2, h - 0.1, -0.18), WOOD, grad=(0.2, 0.9))
	p.box((0.2, 1.6, 0.3), (h - 0.05, 2.55, -0.45), WOOD_GRAY, rot=(-18, 0, 4), grad=(0.2, 0.9))
	_chain(p, [(-h + 0.1, -h, -0.18), (-h + 0.1, -2.0, -0.2), (-h + 0.12, 1.0, -0.45), (-h + 0.14, h, -0.95)], 0.18, 0.16, WOOD, sides=4)
	posts = (-4.2, -1.4, 1.4, 4.2)
	for x in posts:
		for y in posts:
			if (x, y) == (4.2, 4.2):  # snapped off below the water
				p.seg((x, y, -4.0), (x, y, water - 0.3), 0.15, 0.14, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
				p.rock((0.34, 0.34, 0.25), (x, y, water - 0.25), WOOD_GRAY, jitter=0.06)
				continue
			top = -0.1
			if x < -4:  # the sagging side's pilings sank a little and lean
				top = -0.2 - 0.25 * (y + 4.2) / 8.4
			lean = (-0.25, 0.0) if (x < -4 and y > 0) else (0.0, 0.0)
			p.seg((x + lean[0], y + lean[1], -4.0), (x, y, top), 0.15, 0.13, WOOD, sides=6, grad=(0.2, 1.0))
			if abs(x) > 4 or abs(y) > 4:
				_post_weed(soft, x + lean[0] * 0.2, y, 0.15, water)
	for i in range(3):  # cross bracing, a couple of braces gone
		a, b = posts[i], posts[i + 1]
		p.seg((a, -4.2, -0.5), (b, -4.2, -2.4), 0.06, 0.06, WOOD_GRAY, sides=4)
		if i < 2:
			p.seg((4.2, a, -0.5), (4.2, b, -2.4), 0.06, 0.06, WOOD_GRAY, sides=4)
		if i != 1:
			p.seg((-4.2, a, -0.6), (-4.2, b, -2.5), 0.06, 0.06, WOOD_GRAY, sides=4)
	for k in range(9):  # weed trailing from the edge beams
		if k < 5:
			top = (p.rng.uniform(-4.0, 3.5), -h - 0.05, -0.3)
		else:
			top = (-h - 0.05, p.rng.uniform(-4.0, 2.0), -0.45)
		_weed_hang(soft, top, p.rng.uniform(0.4, 0.7))
	for x, y, sx, sy in ((-2.6, 3.4, 1.2, 0.8), (1.6, 1.3, 0.9, 0.6), (-1.0, -3.2, 0.7, 0.5), (3.6, -3.8, 0.8, 0.6)):
		_moss_patch(soft, x, y, 0.0, sx, sy)
	return join_into(p.build(bevel=0.02), [soft.build()])


def stilt_walkway_broken():
	"""A 3 x 9 m walkway of lost Veyamar, running along Y like stilt_walkway:
	its planks rotted out on the +X side for y in [0.4, 2.2] (the -X side of
	them still holds), a plank hanging into the water, the +X rail's middle
	post leaning out with its ropes slack, weed on the pilings. Deck top at the
	origin, flat wherever planks remain."""
	p = Prop("stilt_walkway_broken", 302)
	soft = Prop("stilt_walkway_broken_soft", 302)  # weed, slime, barnacles and coral: left unbeveled
	hx, hy = 1.5, 4.5
	n = 30
	for k in range(n):
		y = -hy + (k + 0.5) * 2 * hy / n
		w = 2 * hy / n - 0.03
		sw = WOOD_GRAY if p.rng.random() < 0.45 else WOOD
		x0, x1 = -hx + p.rng.uniform(0.0, 0.04), hx - p.rng.uniform(0.0, 0.05)
		if 0.4 < y < 2.2:
			x1 = -0.35 + p.rng.uniform(0.0, 0.45)
		p.box((x1 - x0, w, 0.08), ((x0 + x1) / 2, y, -0.04), sw, rot=(0, 0, p.rng.uniform(-0.3, 0.3)), grad=(0.1, 0.6))
	p.box((0.3, 1.5, 0.07), (1.62, 1.2, -0.6), WOOD_GRAY, rot=(0, 72, 8), grad=(0.1, 0.6))  # a plank hanging off the side
	p.box((0.16, 2 * hy, 0.2), (-1.2, 0, -0.18), WOOD, grad=(0.3, 1.0))
	p.box((0.16, 4.8, 0.2), (1.2, -2.1, -0.18), WOOD, grad=(0.3, 1.0))  # the +X stringer, snapped in the gap
	p.box((0.16, 2.3, 0.2), (1.2, 3.35, -0.18), WOOD, grad=(0.3, 1.0))
	p.box((0.16, 0.9, 0.2), (1.22, 0.62, -0.4), WOOD_GRAY, rot=(28, 0, 0), grad=(0.3, 1.0))
	posts = (-4.25, -1.45, 1.45, 4.25)
	for s in (-1, 1):
		x = s * 1.38
		tops = []
		for y in posts:
			top = (x, y, 1.1)
			if s > 0 and y == 1.45:
				top = (x + 0.55, y + 0.1, 0.95)  # leaning out over the water
			p.seg((x, y, -4.0), top, 0.1, 0.09, WOOD, sides=6, grad=(0.2, 1.0))
			p.seg(top, (top[0], top[1], top[2] + 0.08), 0.12, 0.12, WOOD_GRAY, sides=6)
			tops.append(top)
			_post_weed(soft, x, y, 0.1, -0.8)
		for i, (a, b) in enumerate(zip(tops, tops[1:])):
			slack = 0.35 if (s > 0 and i in (1, 2)) else 0.12
			_rope(p, (a[0], a[1], a[2] - 0.08), (b[0], b[1], b[2] - 0.08), slack)
			if s > 0 and i == 1:  # the lower rope snapped and trails in the water
				_rope(p, (a[0], a[1], 0.55), (a[0] + 0.1, a[1] + 1.0, -0.8), 0.1)
				continue
			_rope(p, (a[0], a[1], a[2] - 0.55 * (a[2] / 1.1)), (b[0], b[1], b[2] - 0.55 * (b[2] / 1.1)), slack * 0.7)
	for k in range(5):
		_weed_hang(soft, (p.rng.choice((-1.55, 1.55)), p.rng.uniform(-4.0, 4.0), -0.25), p.rng.uniform(0.35, 0.6))
	_moss_patch(soft, -0.8, -3.0, 0.0, 0.8, 0.5)
	_moss_patch(soft, 0.6, 3.6, 0.0, 0.6, 0.5)
	return join_into(p.build(bevel=0.02), [soft.build()])


def stilt_hut_sunken():
	"""A hut of lost Veyamar whose pilings gave way: its 5 x 5 m deck and the
	hut on it tilted and half sunk in the marsh (one corner under water, the
	other 1.7 m out), plank walls gapped, the roof's right slope fallen in round
	a snapped ridge. Origin on the bed; built for about 1 m of water. Scenery,
	not walkable: collide it as a box. About 4.3 m above the bed."""
	p = Prop("stilt_hut_sunken", 303)
	soft = Prop("stilt_hut_sunken_soft", 303)  # weed, slime, barnacles and coral: left unbeveled
	start = len(p.parts)
	hd = 2.5
	_deck_planks(p, hd, hd, True)
	for s in (-1, 1):
		p.box((2 * hd, 0.2, 0.3), (0, s * (hd - 0.1), -0.15), WOOD, grad=(0.2, 0.9))
		p.box((0.2, 2 * hd, 0.3), (s * (hd - 0.1), 0, -0.15), WOOD, grad=(0.2, 0.9))
	for x in (-2.2, 0.0, 2.2):
		for y in (-2.2, 2.2):
			p.seg((x, y, -2.6), (x, y, -0.08), 0.13, 0.12, WOOD, sides=6, grad=(0.2, 1.0))
	w, wall_h = 3.6, 2.2
	hw = w / 2

	def planks(x0, x1, fixed, along_x, skip=None, drop=()):
		n = int(abs(x1 - x0) / 0.32)
		for k in range(n):
			c = x0 + (k + 0.5) * (x1 - x0) / n
			if (skip and skip[0] < c < skip[1]) or k in drop:
				continue
			hgt = wall_h + p.rng.uniform(-0.1, 0.05)
			sw = WOOD_GRAY if p.rng.random() < 0.5 else WOOD
			if along_x:
				p.box((abs(x1 - x0) / n - 0.03, 0.1, hgt), (c, fixed, hgt / 2), sw, rot=(p.rng.uniform(-2, 2), 0, 0), grad=(0.15, 0.9))
			else:
				p.box((0.1, abs(x1 - x0) / n - 0.03, hgt), (fixed, c, hgt / 2), sw, rot=(0, p.rng.uniform(-2, 2), 0), grad=(0.15, 0.9))

	planks(-hw, hw, -hw, True, skip=(-0.5, 0.5), drop=(8,))
	planks(-hw, hw, hw, True, drop=(3,))
	planks(-hw, hw, -hw, False, skip=(-0.45, 0.45))
	planks(-hw, hw, hw, False, drop=(2, 7))
	p.box((1.1, 0.12, 0.26), (0, -hw, 2.0), WOOD, grad=(0.3, 1.0))
	for x in (-hw, hw):
		for y in (-hw, hw):
			p.seg((x, y, 0), (x, y, wall_h + 0.1), 0.1, 0.09, WOOD, sides=6, grad=(0.2, 1.0))
	ridge = wall_h + 1.7
	# left slope whole
	p.poly([(-(hw + 0.45), -hw - 0.4, wall_h - 0.2), (0, -hw - 0.4, ridge), (0, hw + 0.4, ridge - 0.7), (-(hw + 0.45), hw + 0.4, wall_h - 0.35)],
		   [(0, 1, 2, 3)], HIDE, grad=(0.0, 0.7))
	for k in range(5):
		t = (k + 0.5) / 5
		x = -(hw + 0.45) * (1 - t)
		z0 = wall_h - 0.2 + (ridge - wall_h + 0.2) * t
		z1 = wall_h - 0.35 + (ridge - 0.7 - wall_h + 0.35) * t
		p.seg((x, -hw - 0.45, z0 + 0.04), (x, hw + 0.45, z1 + 0.04), 0.06, 0.06, HIDE, sides=4, grad=(0.1, 0.6))
	# the ridge snapped: its back half sagging to the right wall
	p.seg((0, -hw - 0.55, ridge + 0.05), (0, 0.1, ridge - 0.25), 0.09, 0.09, WOOD, sides=6)
	p.seg((0.05, 0.1, ridge - 0.3), (0.5, hw + 0.5, wall_h - 0.15), 0.09, 0.08, WOOD_GRAY, sides=6)
	# right slope: a strip of thatch left at the front, bare rafters, the rest slumped inside
	p.poly([(hw + 0.45, -hw - 0.4, wall_h - 0.2), (0, -hw - 0.4, ridge), (0, -0.7, ridge - 0.15), (hw + 0.45, -0.9, wall_h - 0.25)],
		   [(0, 1, 2, 3)], HIDE, grad=(0.0, 0.7))
	for k in range(3):
		t = (k + 0.5) / 3
		x = (hw + 0.45) * (1 - t)
		z = wall_h - 0.2 + (ridge - wall_h + 0.2) * t
		p.seg((x, -hw - 0.45, z + 0.04), (x, -0.8, z - 0.04), 0.06, 0.06, HIDE, sides=4, grad=(0.1, 0.6))
	for y in (0.0, 0.9, 1.8):
		zr = ridge - 0.25 - (ridge - 0.25 - wall_h) * (y / (hw + 0.5)) * 0.9
		p.seg((0.1, y, zr), (hw + 0.3, y + 0.1, wall_h - 0.05), 0.05, 0.045, WOOD_GRAY, sides=4)
	p.seg((0.3, 0.4, ridge - 0.5), (hw - 0.1, 0.6, 0.6), 0.05, 0.04, WOOD_GRAY, sides=4)  # a rafter fallen in
	p.blob((2.4, 2.6, 0.9), (0.8, 1.0, 0.35), HIDE, rot=(0, 8, 10), segs=(8, 5), grad=(0.2, 1.0), jitter=0.05)  # the thatch that came down
	p.poly([(-hw, -hw, wall_h), (0, -hw, ridge - 0.12), (hw, -hw, wall_h)], [(0, 1, 2)], WOOD_GRAY, grad=(0.2, 0.9))
	p.box((0.06, 0.55, 0.9), (-hw - 0.05, -0.6, 1.35), WOOD_GRAY, rot=(0, 0, -30), grad=(0.1, 0.8))  # a shutter hanging
	_move_parts(p, start, Matrix.Translation((0, 0, 0.75)) @ Matrix.Rotation(math.radians(-15), 4, "Y") @ Matrix.Rotation(math.radians(9), 4, "X"))
	# what the water carried off, and weed where it meets the wreck
	for k in range(5):
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(3.0, 4.2)
		p.box((p.rng.uniform(1.2, 2.2), 0.28, 0.07), (math.cos(a) * d, math.sin(a) * d, 0.98), WOOD_GRAY, rot=(0, p.rng.uniform(-4, 4), p.rng.uniform(0, 180)), grad=(0.1, 0.6))
	for k in range(10):
		a = k * math.tau / 10
		p.blob((1.0, 0.6, 0.08), (math.cos(a) * 2.5, math.sin(a) * 2.5, 1.0), MOSS if k % 2 else PINE, rot=(0, 0, math.degrees(a) + 90), segs=(7, 3), grad=(0.4, 1.0))
	for k in range(6):
		_weed_hang(soft, (p.rng.uniform(-2.4, 2.4), -2.6, 1.3), p.rng.uniform(0.3, 0.5))
	return join_into(p.build(bevel=0.02), [soft.build()])


def pondkin_hut():
	"""A pondkin's hut: a lumpy dome of marsh mud about 3.5 m across and 2.3 m
	tall under a cap of bundled reeds, studded with shells, with a low round
	doorway (about 1 m high) through a short mud porch at the front (-Y).
	Collide it as a box."""
	p = Prop("pondkin_hut", 304)
	soft = Prop("pondkin_hut_soft", 304)  # weed, slime, barnacles and coral: left unbeveled
	R, H = 1.75, 1.95
	_lathe(p, [(0.02, -0.3), (R + 0.05, -0.3), (R + 0.05, 0.3), (R * 0.97, 0.8), (R * 0.82, 1.3), (R * 0.55, 1.75), (R * 0.2, 1.95), (0.02, 1.97)],
		   16, WOOD, grad=(0.25, 1.0), jitter=0.05)
	for k in range(14):  # the mud banked round its foot
		a = k * math.tau / 14
		soft.blob((1.1, 0.8, 0.7), (math.cos(a) * R * 0.98, math.sin(a) * R * 0.98, 0.1), WOOD_GRAY, rot=(0, 0, math.degrees(a) + 90), segs=(8, 5), grad=(0.3, 1.0), jitter=0.04)
	# the reed cap: a cone of thatch with bundles down it and a spray at the top
	p.seg((0, 0, 1.35), (0, 0, 2.55), 1.35, 0.1, BAMBOO, sides=12, grad=(0.1, 0.9), jitter=0.03)
	for k in range(12):
		a = k * math.tau / 12 + 0.13
		p.seg((math.cos(a) * 1.42, math.sin(a) * 1.42, 1.28), (math.cos(a) * 0.1, math.sin(a) * 0.1, 2.56), 0.08, 0.05, HIDE if k % 2 else BAMBOO, sides=4, grad=(0.1, 0.7))
	p.seg((0, 0, 1.55), (0, 0, 1.63), 1.18, 1.12, WOOD, sides=12)  # the binding cord
	for k in range(9):
		a = k * math.tau / 9
		p.seg((0, 0, 2.45), (math.cos(a) * 0.35, math.sin(a) * 0.35, 3.0 + p.rng.uniform(-0.1, 0.15)), 0.03, 0.005, BAMBOO, sides=3)
	# the porch and doorway
	p.seg((0, -1.1, 0.45), (0, -2.0, 0.45), 0.78, 0.72, WOOD, sides=10, grad=(0.2, 1.0), jitter=0.03)
	p.seg((0, -2.0, 0.45), (0, -2.06, 0.45), 0.6, 0.58, IRON, sides=12, grad=(0.6, 1.0))
	for k in range(9):  # shells round the door
		a = math.pi * (-0.1 + 1.2 * k / 8)
		soft.blob((0.2, 0.08, 0.17), (math.cos(a) * 0.72, -2.04, 0.45 + math.sin(a) * 0.72), (CLOTH_WHITE, SHELL_PEACH, CORAL_PINK)[k % 3],
			   rot=(90, 0, 0), segs=(7, 4), grad=(0.0, 0.5))
	for k in range(22):  # shells pressed into the dome
		a = p.rng.uniform(0, math.tau)
		if math.sin(a) < -0.85:
			continue
		e = p.rng.uniform(0.15, 0.62)
		n = Vector((math.cos(a) * math.cos(e) / R, math.sin(a) * math.cos(e) / R, math.sin(e) / H)).normalized()
		c = (math.cos(a) * math.cos(e) * R, math.sin(a) * math.cos(e) * R, math.sin(e) * H)
		q = Vector((0, 0, 1)).rotation_difference(n).to_euler()
		soft.blob((0.2, 0.17, 0.07), c, (CLOTH_WHITE, SHELL_PEACH, CORAL_PINK, BONE)[k % 4], rot=tuple(math.degrees(v) for v in q), segs=(7, 4), grad=(0.0, 0.5))
	# a drying rack of fish by the door and a clay pot
	for x in (1.25, 2.05):
		p.seg((x, -1.75, 0), (x, -1.75, 1.2), 0.04, 0.035, WOOD_GRAY, sides=4)
	p.seg((1.15, -1.75, 1.15), (2.15, -1.75, 1.15), 0.03, 0.03, WOOD_GRAY, sides=4)
	for k in range(3):
		x = 1.4 + k * 0.3
		p.blob((0.12, 0.05, 0.42), (x, -1.75, 0.9), SEA_STONE, segs=(6, 4), grad=(0.0, 0.8))
	_lathe(p, [(0.02, 0.0), (0.2, 0.03), (0.28, 0.2), (0.24, 0.42), (0.15, 0.5), (0.18, 0.55), (0.12, 0.55), (0.02, 0.45)], 10, CLAY, grad=(0.1, 0.9))
	p.parts[-1].data.transform(Matrix.Translation((-1.5, -1.6, 0)))
	return join_into(p.build(bevel=0.02), [soft.build()])


def pondkin_totem():
	"""A pondkin totem, about 3.6 m with its reed crest: a carved post topped with a grinning frog
	head painted green (bulging eyes, a yellow throat), a second frog face
	carved lower down, strings of shells and reed streamers hanging from a
	crossbar, on a mound of mud and shells. Faces -Y. Collide it as a box."""
	p = Prop("pondkin_totem", 305)
	soft = Prop("pondkin_totem_soft", 305)  # weed, slime, barnacles and coral: left unbeveled
	p.blob((1.4, 1.3, 0.5), (0, 0, 0.0), WOOD_GRAY, segs=(10, 5), grad=(0.3, 1.0), jitter=0.04)
	for k in range(7):
		a = k * math.tau / 7 + 0.2
		soft.blob((0.18, 0.15, 0.07), (math.cos(a) * 0.5, math.sin(a) * 0.45, 0.2), (CLOTH_WHITE, SHELL_PEACH)[k % 2], rot=(20, 0, math.degrees(a)), segs=(6, 4))
	p.seg((0, 0, -0.2), (0, 0.03, 2.45), 0.21, 0.18, WOOD, sides=8, grad=(0.2, 1.0))
	for z in (0.6, 1.95):
		p.seg((0, 0, z), (0, 0, z + 0.1), 0.23, 0.23, SCALE_GREEN, sides=8)  # painted bands
	# the lower face, carved in the wood
	p.blob((0.52, 0.4, 0.4), (0, -0.14, 1.3), WOOD, segs=(8, 6), grad=(0.1, 0.8))
	for s in (-1, 1):
		p.blob((0.16, 0.14, 0.16), (s * 0.15, -0.28, 1.46), WOOD, segs=(6, 5))
		p.blob((0.07, 0.04, 0.07), (s * 0.15, -0.35, 1.47), IRON, segs=(5, 4))
	p.box((0.36, 0.05, 0.04), (0, -0.33, 1.2), IRON, grad=(0.6, 1.0))
	# the crown: a frog head
	hz = 2.72
	p.blob((0.95, 0.85, 0.6), (0, -0.05, hz), LEAF, segs=(12, 8), grad=(0.05, 0.9))
	p.blob((0.7, 0.55, 0.32), (0, -0.12, hz - 0.3), PETAL_YELLOW, segs=(10, 6), grad=(0.0, 0.7))  # the throat
	grin = []  # the grin, following the head round the front
	for k in range(9):
		a = math.radians(200 + k * 140 / 8)
		grin.append((math.cos(a) * 0.475 * 0.97, -0.05 + math.sin(a) * 0.425 * 0.97, hz - 0.1 + 0.06 * abs(math.cos(a))))
	_chain(p, grin, 0.03, 0.03, IRON, sides=4, grad=(0.6, 1.0))
	for s in (-1, 1):
		p.blob((0.34, 0.32, 0.32), (s * 0.28, -0.12, hz + 0.26), LEAF, segs=(8, 6), grad=(0.0, 0.8))
		p.blob((0.24, 0.12, 0.24), (s * 0.29, -0.27, hz + 0.28), CLOTH_WHITE, segs=(8, 5), grad=(0.0, 0.3))
		p.blob((0.1, 0.05, 0.14), (s * 0.29, -0.33, hz + 0.28), IRON, segs=(6, 4))
		p.blob((0.05, 0.03, 0.05), (s * 0.08, -0.46, hz + 0.08), IRON, segs=(4, 3))  # nostrils
	for k in range(5):  # a crest of reeds behind the head
		a = math.radians(-50 + k * 25)
		p.seg((0, 0.15, hz + 0.2), (math.sin(a) * 0.5, 0.3, hz + 0.95 - abs(a) * 0.2), 0.035, 0.005, BAMBOO, sides=3)
	# crossbar with shell strings and reed streamers
	p.seg((-0.85, 0.02, 2.1), (0.85, 0.02, 2.12), 0.05, 0.05, WOOD_GRAY, sides=5)
	for k, x in enumerate((-0.78, -0.55, -0.32, 0.32, 0.55, 0.78)):
		if k % 3 == 1:
			for j in range(4):
				soft.blob((0.12, 0.05, 0.1), (x, 0.02, 1.95 - j * 0.16), (CLOTH_WHITE, SHELL_PEACH, CORAL_PINK)[(j + k) % 3], rot=(0, 0, 90), segs=(6, 4))
			p.seg((x, 0.02, 2.08), (x, 0.02, 1.4), 0.008, 0.008, HIDE, sides=3)
		else:
			ln = p.rng.uniform(0.9, 1.3)
			p.box((0.06, 0.015, ln), (x, 0.05, 2.08 - ln / 2), BAMBOO if k % 2 else PINE, rot=(0, p.rng.uniform(-6, 6), 0), grad=(0.1, 0.9))
			p.box((0.05, 0.015, ln * 0.8), (x + 0.07, 0.06, 2.08 - ln * 0.4), LEAF, rot=(0, p.rng.uniform(-6, 6), 0), grad=(0.1, 0.9))
	return join_into(p.build(bevel=0.015), [soft.build()])


def witch_hut():
	"""The marsh witch's hut: a crooked plank shack leaning on five crooked
	stilts, floor 1.7 m up, a steep reed-thatch roof with a bent tip (about 6.8 m
	to the top), a ladder up to the door (-Y), a lit window beside it and one
	at the side, bones, skulls and charms hung from the eaves. Origin on the
	ground or marsh bed. Collide it as a box."""
	p = Prop("witch_hut", 306)
	soft = Prop("witch_hut_soft", 306)  # weed, slime, barnacles and coral: left unbeveled
	fz = 1.7
	for (x, y) in ((-1.5, -1.5), (1.6, -1.4), (1.45, 1.55), (-1.55, 1.5), (0.1, 0.2)):
		mid = (x + p.rng.uniform(-0.4, 0.4), y + p.rng.uniform(-0.4, 0.4), 0.95)
		_chain(p, [(x * 1.18, y * 1.18, -0.4), mid, (x, y, fz - 0.05)], 0.13, 0.1, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
		_post_weed(soft, mid[0], mid[1], 0.13, 0.95)
	for a, b in (((-1.5, -1.5, 0.6), (1.6, -1.4, 1.3)), ((1.6, -1.4, 0.5), (1.45, 1.55, 1.35)), ((-1.55, 1.5, 0.7), (-1.5, -1.5, 1.4))):
		p.seg(a, b, 0.05, 0.05, WOOD, sides=4)
	start = len(p.parts)
	# the floor, a porch lip at the front
	for k in range(12):
		y = -1.95 + (k + 0.5) * 3.9 / 12
		p.box((3.6 + p.rng.uniform(-0.2, 0.1), 3.9 / 12 - 0.03, 0.08), (p.rng.uniform(-0.05, 0.05), y, fz - 0.04), WOOD_GRAY if k % 3 else WOOD,
			  rot=(0, 0, p.rng.uniform(-2, 2)), grad=(0.1, 0.6))
	for s in (-1, 1):
		p.box((3.7, 0.18, 0.25), (0, s * 1.8, fz - 0.18), WOOD, grad=(0.2, 0.9))
	# the shack: 2.8 x 2.6 m of plank walls, leaning (sheared) toward +X
	w, d, wh = 2.8, 2.6, 2.1
	hw, hd = w / 2, d / 2
	wstart = len(p.parts)

	def wall(x0, x1, fixed, along_x, gaps=()):
		n = int(abs(x1 - x0) / 0.3)
		for k in range(n):
			c = x0 + (k + 0.5) * (x1 - x0) / n
			top = wh + p.rng.uniform(-0.05, 0.12)
			spans = [(0.0, top)]
			for g0, g1, z0, z1 in gaps:
				if g0 < c < g1:
					spans = [(0.0, z0), (z1, top)] if z0 > 0 else [(z1, top)]
			for a, b in spans:
				sw = WOOD_GRAY if p.rng.random() < 0.5 else WOOD
				if along_x:
					p.box((abs(x1 - x0) / n - 0.02, 0.1, b - a), (c, fixed, fz + (a + b) / 2), sw, rot=(0, p.rng.uniform(-3, 3), 0), grad=(0.15, 0.95))
				else:
					p.box((0.1, abs(x1 - x0) / n - 0.02, b - a), (fixed, c, fz + (a + b) / 2), sw, rot=(p.rng.uniform(-3, 3), 0, 0), grad=(0.15, 0.95))

	wall(-hw, hw, -hd, True, [(-0.9, -0.1, 0.0, 1.75), (0.45, 1.05, 0.95, 1.5)])
	wall(-hw, hw, hd, True)
	wall(-hd, hd, -hw, False)
	wall(-hd, hd, hw, False, [(-0.3, 0.35, 0.9, 1.45)])
	for x, y in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)):
		p.seg((x, y, fz), (x, y, fz + wh + 0.1), 0.09, 0.08, WOOD, sides=5, grad=(0.2, 1.0))
	p.box((0.78, 0.08, 1.7), (-0.9 + 0.39 * math.cos(math.radians(-55)), -hd + 0.39 * math.sin(math.radians(-55)), fz + 0.86), WOOD, rot=(0, 0, -55), grad=(0.2, 0.9))  # the door, ajar
	p.box((0.9, 0.12, 0.16), (-0.5, -hd - 0.02, fz + 1.82), WOOD_GRAY, grad=(0.2, 0.9))  # lintel
	p.box((0.72, 0.1, 1.72), (-0.5, -hd + 0.2, fz + 0.86), IRON, grad=(0.6, 1.0))  # the dark inside
	for (x, y, sx, sy) in ((0.75, -hd + 0.02, 0.62, 0.06), (hw - 0.02, 0.02, 0.06, 0.66)):  # the lit windows, crossed with sticks
		p.box((sx, sy, 0.56), (x, y, fz + 1.22), FLAME, grad=(0.2, 0.6), glow=1.6)
		if sy < 0.1:
			p.seg((x - 0.33, y - 0.08, fz + 1.22), (x + 0.33, y - 0.08, fz + 1.22), 0.025, 0.025, WOOD_GRAY, sides=4)
			p.seg((x, y - 0.08, fz + 0.93), (x, y - 0.08, fz + 1.51), 0.025, 0.025, WOOD_GRAY, sides=4)
		else:
			p.seg((x + 0.08, y - 0.35, fz + 1.22), (x + 0.08, y + 0.35, fz + 1.22), 0.025, 0.025, WOOD_GRAY, sides=4)
			p.seg((x + 0.08, y, fz + 0.93), (x + 0.08, y, fz + 1.51), 0.025, 0.025, WOOD_GRAY, sides=4)
	# the roof: a crooked four-sided cone of reed thatch, the tip bent over
	ez, apex = fz + wh - 0.1, (0.6, 0.3, fz + wh + 2.2)
	rstart = len(p.parts)
	ov = 0.5
	eaves = [(-hw - ov, -hd - ov, ez - 0.1), (hw + ov, -hd - ov, ez + 0.05), (hw + ov, hd + ov, ez - 0.15), (-hw - ov, hd + ov, ez)]
	for i in range(4):
		a, b = eaves[i], eaves[(i + 1) % 4]
		p.poly([a, b, apex], [(0, 1, 2)], HIDE, grad=(0.0, 0.8))
		for k in range(4):  # courses of reed bundles
			t = (k + 0.4) / 4.5
			pa = Vector(a).lerp(Vector(apex), t)
			pb = Vector(b).lerp(Vector(apex), t)
			p.seg(tuple(pa + Vector((0, 0, 0.04))), tuple(pb + Vector((0, 0, 0.04))), 0.07, 0.07, BAMBOO if k % 2 else HIDE, sides=4, grad=(0.1, 0.7))
	_chain(p, [apex, (apex[0] + 0.15, apex[1] + 0.05, apex[2] + 0.6), (apex[0] + 0.55, apex[1] - 0.1, apex[2] + 0.85), (apex[0] + 0.85, apex[1] - 0.2, apex[2] + 0.65)],
		   0.3, 0.05, HIDE, sides=6, grad=(0.1, 0.8))
	_move_parts(p, rstart, Matrix.Rotation(math.radians(9), 4, "Z"))  # the roof sits askew
	p.seg((-0.9, 0.8, ez + 0.6), (-1.0, 0.95, ez + 1.9), 0.12, 0.1, IRON, sides=6)  # a crooked stovepipe
	p.seg((-1.0, 0.95, ez + 1.9), (-0.8, 1.05, ez + 2.15), 0.14, 0.14, IRON, sides=6)
	# charms: bones, skulls, a bottle and glowing trinkets hung from the eaves
	for k, (x, y) in enumerate(((-hw - 0.35, -hd - 0.35), (hw + 0.35, -hd - 0.35), (0.2, -hd - 0.4), (hw + 0.4, 0.8), (-1.0, -hd - 0.38), (1.0, -hd - 0.38))):
		top = (x, y, ez - 0.05)
		ln = p.rng.uniform(0.5, 0.9)
		p.seg(top, (x, y, top[2] - ln), 0.008, 0.008, HIDE, sides=3)
		end = (x, y, top[2] - ln)
		if k % 3 == 0:
			_skull(p, (end[0], end[1], end[2] - 0.2), s=0.9, yaw=p.rng.uniform(-0.4, 0.4))
		elif k % 3 == 1:
			_bone(p, (x - 0.1, y, end[2] + 0.1), (x + 0.1, y, end[2] - 0.2), r=0.02)
			_bone(p, (x + 0.08, y + 0.03, end[2] + 0.05), (x - 0.06, y - 0.02, end[2] - 0.25), r=0.018)
		else:
			p.blob((0.1, 0.1, 0.12), end, SLIME, segs=(6, 5), glow=1.3)
			for j in range(3):
				p.box((0.03, 0.01, 0.2), (x - 0.06 + j * 0.06, y, end[2] - 0.14), CLOTH_RED if j % 2 else BONE, rot=(0, (j - 1) * 20, 0))
	_skull(p, (1.2, -hd - 0.05, fz + 2.0), s=1.3)  # nailed over the window
	# the lean
	_move_parts(p, wstart, Matrix.Translation((0, 0, fz)) @ Matrix.Shear("XY", 4, (0.11, 0.04)) @ Matrix.Translation((0, 0, -fz)))
	_move_parts(p, start, Matrix.Translation((0, 0, fz)) @ Matrix.Rotation(math.radians(5), 4, "Y") @ Matrix.Rotation(math.radians(-3), 4, "X") @ Matrix.Translation((0, 0, -fz)))
	# the ladder up to the door
	for x in (-0.82, -0.18):
		p.seg((x, -2.6, -0.2), (x - 0.02, -1.85, fz + 0.5), 0.045, 0.04, WOOD_GRAY, sides=5)
	for k in range(5):
		t = (k + 0.7) / 6.0
		z = -0.2 + (fz + 0.7) * t
		y = -2.6 + 0.75 * t
		p.seg((-0.86, y, z), (-0.14, y, z), 0.03, 0.03, WOOD, sides=4)
	return join_into(p.build(bevel=0.015), [soft.build()])


def witch_cauldron():
	"""A big black cauldron (1.4 m across, rim at 1.3 m) on three stubby legs
	over a fire of gnarled roots and embers, full of a glowing green brew that
	bubbles and drips over the rim, a ladle stuck in it. Collide it as a box."""
	p = Prop("witch_cauldron", 307)
	soft = Prop("witch_cauldron_soft", 307)  # weed, slime, barnacles and coral: left unbeveled
	for k in range(7):  # roots for firewood
		a = k * math.tau / 7 + p.rng.uniform(-0.2, 0.2)
		pts = []
		for j in range(4):
			t = j / 3
			r = 1.15 - 0.85 * t
			pts.append((math.cos(a + t * 0.6) * r, math.sin(a + t * 0.6) * r, 0.08 + 0.1 * math.sin(t * math.pi) + p.rng.uniform(-0.03, 0.05)))
		_chain(p, pts, 0.1, 0.05, WOOD_GRAY, sides=5, grad=(0.3, 1.0))
		p.seg(pts[1], (pts[1][0] * 1.2, pts[1][1] * 1.2 + 0.1, 0.35), 0.04, 0.01, WOOD_GRAY, sides=4)
	soft.blob((1.5, 1.5, 0.16), (0, 0, 0.05), EMBER, segs=(10, 4), grad=(0.5, 0.9), glow=1.2)
	for k in range(7):
		a = k * math.tau / 7 + 0.3
		r = 0.35 + (k % 2) * 0.25
		soft.seg((math.cos(a) * r, math.sin(a) * r, 0.05), (math.cos(a) * r * 1.2, math.sin(a) * r * 1.2, 0.35 + (k % 3) * 0.12), 0.1, 0.0, FLAME, sides=5,
			  grad=(0.1, 0.9), glow=1.2, twist=p.rng.uniform(0, 60))
	for k in range(3):
		a = k * math.tau / 3 + 0.5
		p.seg((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.35), (math.cos(a) * 0.62, math.sin(a) * 0.62, -0.05), 0.1, 0.07, IRON, sides=5, grad=(0.0, 0.7))
	_lathe(p, [(0.05, 0.3), (0.42, 0.34), (0.66, 0.55), (0.72, 0.82), (0.66, 1.08), (0.56, 1.22), (0.64, 1.27), (0.62, 1.33), (0.52, 1.3), (0.5, 1.18), (0.05, 1.16)],
		   16, IRON, grad=(0.0, 0.8))
	for s in (-1, 1):  # ring handles
		pts = [(s * (0.66 + 0.18 * math.sin(t * math.pi)), 0.16 * math.cos(t * math.pi), 1.1 - 0.2 * math.sin(t * math.pi)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
		_chain(p, pts, 0.03, 0.03, IRON, sides=4)
	p.seg((0, 0, 1.18), (0, 0, 1.25), 0.53, 0.53, SLIME, sides=16, grad=(0.3, 0.5), glow=1.5)
	for k in range(6):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.4)
		b = p.rng.uniform(0.08, 0.16)
		soft.blob((b, b, b * 0.7), (math.cos(a) * r, math.sin(a) * r, 1.26), SLIME, segs=(6, 4), grad=(0.2, 0.45), glow=1.5)
	for a in (0.4, 2.3, 4.4):  # drips down the side
		p.seg((math.cos(a) * 0.6, math.sin(a) * 0.6, 1.31), (math.cos(a) * 0.71, math.sin(a) * 0.71, 0.95), 0.05, 0.02, SLIME, sides=4, grad=(0.3, 0.6), glow=1.5)
	p.seg((0.15, 0.1, 0.9), (-0.35, 0.3, 1.95), 0.035, 0.03, WOOD_GRAY, sides=5)  # the ladle
	return join_into(p.build(bevel=0.015), [soft.build()])


def heron_rookery_nest():
	"""A heron's rookery: a big nest of sticks (2.2 m across) in the fork of a
	dead, broken-topped stump, its rim about 2.5 m up, three pale blue eggs
	in it and droppings down the bark. Origin on the ground or marsh bed.
	Collide it as a trunk (or a box)."""
	p = Prop("heron_rookery_nest", 308)
	p.seg((0, 0, -0.4), (0.05, 0.02, 1.7), 0.42, 0.3, WOOD_GRAY, sides=7, grad=(0.2, 1.0), jitter=0.02)
	for k in range(5):  # roots
		a = k * math.tau / 5 + 0.3
		_chain(p, [(math.cos(a) * 0.3, math.sin(a) * 0.3, 0.5), (math.cos(a) * 0.7, math.sin(a) * 0.7, 0.1), (math.cos(a) * 1.0, math.sin(a) * 1.0, -0.3)],
			   0.16, 0.06, WOOD_GRAY, sides=5, grad=(0.2, 1.0))
	for k, a in enumerate((0.3, 2.4, 4.3)):  # the fork carrying the nest, one limb snapped short
		top = (math.cos(a) * 0.85, math.sin(a) * 0.85, 2.3 if k else 2.9)
		_chain(p, [(0.05, 0.02, 1.6), (math.cos(a) * 0.4, math.sin(a) * 0.4, 1.95), top], 0.24, 0.1 if k else 0.12, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
		if k == 0:
			p.rock((0.26, 0.26, 0.22), top, WOOD_GRAY, jitter=0.05)
	p.seg((0.2, -0.2, 1.2), (0.8, -0.9, 1.55), 0.08, 0.02, WOOD_GRAY, sides=4)  # a dead branch
	p.blob((2.0, 2.0, 0.45), (0, 0, 2.15), WOOD, segs=(12, 6), grad=(0.3, 1.0), jitter=0.04)
	p.blob((1.3, 1.3, 0.25), (0, 0, 2.38), HIDE, segs=(10, 5), grad=(0.2, 0.8))
	for layer, (R, z, n) in enumerate(((0.95, 2.2, 14), (0.9, 2.38, 12), (0.8, 2.52, 10))):
		for k in range(n):
			a = k * math.tau / n + p.rng.uniform(-0.2, 0.2) + layer * 0.3
			c = Vector((math.cos(a) * R, math.sin(a) * R, z + p.rng.uniform(-0.05, 0.05)))
			t = Vector((-math.sin(a), math.cos(a), 0)).lerp(Vector((math.cos(a), math.sin(a), 0)), p.rng.uniform(-0.5, 0.5))
			t.z = p.rng.uniform(-0.2, 0.2)
			L = p.rng.uniform(0.6, 1.1)
			p.seg(tuple(c - t * L / 2), tuple(c + t * L / 2), 0.035, 0.025, WOOD if (k + layer) % 3 else WOOD_GRAY, sides=4, grad=(0.2, 1.0))
	for k in range(8):  # sticks sagging over the edge
		a = p.rng.uniform(0, math.tau)
		p.seg((math.cos(a) * 0.8, math.sin(a) * 0.8, 2.35), (math.cos(a) * 1.45, math.sin(a) * 1.45, p.rng.uniform(1.8, 2.2)), 0.03, 0.012, WOOD_GRAY, sides=4)
	for x, y in ((-0.14, 0.05), (0.16, 0.1), (0.0, -0.16)):
		p.blob((0.17, 0.17, 0.22), (x, y, 2.55), TEAL, segs=(8, 6), rot=(p.rng.uniform(-20, 20), p.rng.uniform(-20, 20), 0), grad=(0.0, 0.35))
	for k in range(4):  # droppings streaked down the bark
		a = k * 1.6 + 0.4
		p.box((0.12, 0.03, p.rng.uniform(0.4, 0.8)), (math.cos(a) * 0.36, math.sin(a) * 0.36, 1.2 + k * 0.1), CLOTH_WHITE, rot=(0, 0, math.degrees(a) + 90), grad=(0.0, 0.3))
	for k in range(3):
		a = p.rng.uniform(0, math.tau)
		p.blob((0.45, 0.07, 0.03), (math.cos(a) * 0.7, math.sin(a) * 0.7, 2.62), CLOTH_WHITE if k else SEA_STONE, rot=(0, 15, math.degrees(a)), segs=(6, 3))
	return p.build(bevel=0.0)


def reeds_tall():
	"""A dense clump of tall reeds and bulrushes, 2 to 3 m, about 1 m across:
	blades and brown cattail heads, low-poly enough to scatter by the dozen
	(about 300 triangles). Origin on the ground or marsh bed. No collision."""
	p = Prop("reeds_tall", 309)
	for k in range(18):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.45)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(1.9, 3.0)
		la = a + p.rng.uniform(-0.6, 0.6)
		lean = p.rng.uniform(0.1, 0.5)
		w = p.rng.uniform(0.045, 0.07)
		bend = (x + math.cos(la) * lean * 0.35, y + math.sin(la) * lean * 0.35, h * 0.6)
		ox, oy = -math.sin(la) * w, math.cos(la) * w
		p.poly([(x - ox, y - oy, 0), (x + ox, y + oy, 0), (bend[0] + ox * 0.7, bend[1] + oy * 0.7, bend[2]), (bend[0] - ox * 0.7, bend[1] - oy * 0.7, bend[2]),
				(x + math.cos(la) * lean, y + math.sin(la) * lean, h)], [(0, 1, 2, 3), (3, 2, 4)], PINE if k % 3 else LEAF, grad=(0.1, 0.85))
	for k in range(6):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.3)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(2.1, 2.8)
		tx, ty = x + p.rng.uniform(-0.12, 0.12), y + p.rng.uniform(-0.12, 0.12)
		p.seg((x, y, 0), (tx, ty, h), 0.015, 0.01, LEAF, sides=3)
		f = (h - 0.42) / h
		p.seg((x + (tx - x) * f, y + (ty - y) * f, h - 0.42), (x + (tx - x) * 0.97, y + (ty - y) * 0.97, h - 0.08), 0.05, 0.045, WOOD, sides=5, grad=(0.3, 0.9))
	return p.build()


def mooring_post():
	"""A weathered mooring post, about 2.7 m from the bed (1.7 m above 1 m of
	water): rope wound round it with a loose end trailing in the water, an
	iron arm at the top hung with a lit lantern (its flame at x 0.62, height
	1.95 from the origin), slime at the water line. Collide it as a trunk."""
	p = Prop("mooring_post", 310)
	soft = Prop("mooring_post_soft", 310)  # weed, slime, barnacles and coral: left unbeveled
	p.seg((0, 0, -0.3), (0.04, 0.02, 2.55), 0.17, 0.14, WOOD_GRAY, sides=7, grad=(0.2, 1.0))
	for k in range(5):  # the split, weathered top
		a = k * math.tau / 5
		p.seg((0.04 + math.cos(a) * 0.06, 0.02 + math.sin(a) * 0.06, 2.5), (0.04 + math.cos(a) * 0.09, 0.02 + math.sin(a) * 0.09, 2.62 + p.rng.uniform(0, 0.08)),
			  0.07, 0.03, WOOD_GRAY, sides=4)
	for k in range(4):  # rope coils
		z = 1.55 + k * 0.08
		pts = [(0.02 + math.cos(j * math.tau / 10) * 0.19, 0.01 + math.sin(j * math.tau / 10) * 0.19, z + j * 0.008) for j in range(11)]
		_chain(p, pts, 0.035, 0.035, HIDE, sides=4)
	_chain(p, [(0.2, -0.05, 1.6), (0.35, -0.3, 1.3), (0.45, -0.6, 1.0), (0.6, -1.1, 0.98), (0.5, -1.7, 0.99)], 0.035, 0.03, HIDE, sides=4)
	p.seg((0.0, 0.02, 2.3), (0.66, 0.02, 2.38), 0.035, 0.03, IRON, sides=5)  # the lantern arm
	p.seg((0.0, 0.02, 2.0), (0.42, 0.02, 2.36), 0.025, 0.025, IRON, sides=4)
	p.seg((0.64, 0.02, 2.38), (0.64, 0.02, 2.2), 0.012, 0.012, IRON, sides=3)
	c = (0.64, 0.02, 1.98)
	p.seg((c[0], c[1], c[2] + 0.2), (c[0], c[1], c[2] + 0.3), 0.14, 0.02, IRON, sides=4, twist=45)
	p.box((0.22, 0.22, 0.04), (c[0], c[1], c[2] + 0.19), IRON, grad=(0.0, 0.6))
	p.box((0.22, 0.22, 0.04), (c[0], c[1], c[2] - 0.15), IRON, grad=(0.0, 0.6))
	for dx in (-0.1, 0.1):
		for dy in (-0.1, 0.1):
			p.seg((c[0] + dx, c[1] + dy, c[2] - 0.15), (c[0] + dx, c[1] + dy, c[2] + 0.19), 0.015, 0.015, IRON, sides=4)
	p.box((0.17, 0.17, 0.28), c, FLAME, grad=(0.1, 0.6), glow=1.8)
	_post_weed(soft, 0.02, 0.01, 0.17, 1.0)
	for k in range(6):
		a = p.rng.uniform(0, math.tau)
		p.seg((math.cos(a) * 0.16, math.sin(a) * 0.16, 0.85 + p.rng.uniform(0, 0.12)), (math.cos(a) * 0.22, math.sin(a) * 0.22, 0.9 + p.rng.uniform(0, 0.12)),
			  0.045, 0.02, BONE, sides=5)  # barnacles
	return join_into(p.build(bevel=0.01), [soft.build()])

# ---------------------------------------------------------------- Long Monsoon west: Drownfast
# The half-sunken citadel of the Tide Kings in a flooded valley, about 2 m
# of water over the old streets. Stone is KayKit's own walls where it can be,
# the rest the pack's stone swatches, weathered blue-gray, with weed at the
# water line, barnacles and coral.


def _algae_band(p, pts, z, size=(1.2, 0.22, 0.4)):
	"""Weed and slime hugging a wall at the water line: pts are (x, y, yaw_deg)
	on its face (yaw along the face)."""
	for k, (x, y, yaw) in enumerate(pts):
		s = p.rng.uniform(0.8, 1.2)
		p.blob((size[0] * s, size[1], size[2] * s), (x, y, z + p.rng.uniform(-0.08, 0.08)), MOSS if k % 3 else PINE, rot=(0, 0, yaw), segs=(7, 4), grad=(0.45, 1.0))


def _barnacles(p, c, n, spread, normal=(0, 0, 1)):
	"""A crust of barnacles round c, pointing out along normal."""
	nrm = Vector(normal).normalized()
	t1 = nrm.orthogonal().normalized()
	t2 = nrm.cross(t1)
	for k in range(n):
		off = t1 * p.rng.uniform(-spread, spread) + t2 * p.rng.uniform(-spread, spread)
		base = Vector(c) + off
		r = p.rng.uniform(0.04, 0.08)
		p.seg(tuple(base), tuple(base + nrm * r * 1.1), r, r * 0.45, BONE if k % 3 else CLOTH_WHITE, sides=6, grad=(0.0, 0.6))


def _coral_branch(p, base, d, length, r, swatch, depth):
	"""A branching coral stem from base along d, forking `depth` more times."""
	d = Vector(d).normalized()
	tip = Vector(base) + d * length
	p.seg(tuple(base), tuple(tip), r, r * 0.75, swatch, sides=5, grad=(0.0, 0.7))
	if depth <= 0:
		p.blob((r * 2.0, r * 2.0, r * 2.0), tuple(tip), swatch, segs=(5, 4), grad=(0.0, 0.4))
		return
	for k in range(2):
		nd = d + Vector((p.rng.uniform(-0.7, 0.7), p.rng.uniform(-0.7, 0.7), p.rng.uniform(0.0, 0.5)))
		_coral_branch(p, tuple(tip), nd, length * p.rng.uniform(0.6, 0.8), r * 0.75, swatch, depth - 1)


def _coral_cluster(p, c, scale=1.0, seed_kinds=(CORAL_PINK, CORAL_ORANGE, CLOTH_RED)):
	"""A small knot of coral for dressing stone: two branching stems and a
	brain coral lump, about 0.6 m across at scale 1."""
	x, y, z = c
	for k in range(2):
		a = p.rng.uniform(0, math.tau)
		_coral_branch(p, (x + math.cos(a) * 0.1 * scale, y + math.sin(a) * 0.1 * scale, z), (math.cos(a) * 0.3, math.sin(a) * 0.3, 1.0),
					  0.22 * scale, 0.045 * scale, seed_kinds[k % len(seed_kinds)], 2)
	p.blob((0.3 * scale, 0.28 * scale, 0.2 * scale), (x + 0.15 * scale, y - 0.12 * scale, z + 0.05 * scale), PETAL_YELLOW, segs=(8, 5), grad=(0.1, 0.8), jitter=0.015 * scale)


def citadel_tower():
	"""A drowned tower of the Tide Kings: an octagon of KayKit walls about 8.6 m
	across, five storeys of 3.2 m, the top one broken off to a jagged ring
	(about 16.6 m where it stands whole). A door at the foot (-Y, under the
	water), windows up the storeys, weed at the water line (2 m), barnacles,
	coral and fallen stones at its foot, a torn blue banner. Origin on the bed.
	Collide it as a mesh."""
	p = Prop("citadel_tower", 311)
	soft = Prop("citadel_tower_soft", 311)  # weed, slime, barnacles and coral: left unbeveled
	A, SH, base = 3.6, 3.2, 0.6
	cos8 = math.cos(math.pi / 8)
	p.seg((0, 0, -1.2), (0, 0, base), (A + 1.0) / cos8, (A + 0.8) / cos8, STONE_DARK, sides=8, grad=(0.3, 1.0), twist=22.5)
	p.seg((0, 0, base - 0.05), (0, 0, base + 0.3), (A + 0.62) / cos8, (A + 0.55) / cos8, SEA_STONE, sides=8, grad=(0.1, 0.8), twist=22.5)
	top_floor = base + 4 * SH
	p.seg((0, 0, top_floor - 0.35), (0, 0, top_floor), (A - 0.2) / cos8, (A - 0.2) / cos8, STONE_DARK, sides=8, grad=(0.2, 0.9), twist=22.5)
	for z in (base + SH, base + 3 * SH):  # string courses between storeys
		p.seg((0, 0, z - 0.12), (0, 0, z + 0.14), (A + 0.52) / cos8, (A + 0.52) / cos8, SEA_STONE, sides=8, grad=(0.0, 0.7), twist=22.5)
	# the broken top storey: which sides still stand (0 gone, else fraction of the storey)
	top = [1.0, 0.55, 0.0, 0.8, 1.0, 0.0, 0.35, 0.7]
	for j in range(8):  # pilasters at the corners, as high as the walls either side
		a = math.radians(22.5 + 45 * j)
		h = max(top[j], top[(j + 1) % 8])
		zt = top_floor + SH * h
		if h == 0.0:
			zt = top_floor + 0.4
		x, y = math.cos(a) * A / cos8, math.sin(a) * A / cos8
		p.seg((x, y, base), (x, y, zt), 0.55, 0.5, STONE_DARK, sides=8, grad=(0.0, 0.8), twist=22.5)
		if h == 1.0:
			p.seg((x, y, zt), (x, y, zt + 0.35), 0.7, 0.62, STONE_DARK, sides=8, grad=(0.0, 0.6), twist=22.5)
		else:
			p.rock((0.8, 0.8, 0.5), (x, y, zt), STONE_DARK, jitter=0.08)
	for j in range(8):  # broken walls finished in rough courses of block
		if 0.0 < top[j] < 1.0:
			a = math.radians(45 * j)
			n = Vector((math.cos(a), math.sin(a), 0))
			t = Vector((-math.sin(a), math.cos(a), 0))
			zt = top_floor + SH * top[j]
			for k in range(5):
				u = -1.2 + k * 0.6
				hk = p.rng.uniform(0.0, 0.55)
				c = n * A + t * u
				p.box((0.62, 0.8, 0.35 + hk), (c.x, c.y, zt + (0.35 + hk) / 2 - 0.05), STONE_DARK, rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.8), jitter=0.03)
	for k in range(8):  # stones fallen at its foot
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(A + 1.4, A + 3.2)
		s = p.rng.uniform(0.6, 1.2)
		p.box((s, s * 0.7, s * 0.55), (math.cos(a) * d, math.sin(a) * d, p.rng.uniform(-0.1, 0.3)), STONE_DARK if k % 2 else STONE_LIGHT,
			  rot=(p.rng.uniform(-20, 20), p.rng.uniform(-20, 20), p.rng.uniform(0, 90)), grad=(0.1, 0.9))
	water = 2.0
	pts = []
	for j in range(8):
		a = math.radians(45 * j)
		for u in (-1.0, 0.0, 1.0):
			pts.append((math.cos(a) * (A + 0.42) - math.sin(a) * u, math.sin(a) * (A + 0.42) + math.cos(a) * u, 45 * j + 90))
	_algae_band(soft, pts, water)
	for j in range(8):
		a = math.radians(22.5 + 45 * j)
		_barnacles(soft, (math.cos(a) * (A / cos8 + 0.55), math.sin(a) * (A / cos8 + 0.55), 1.2), 6, 0.3, normal=(math.cos(a), math.sin(a), 0.2))
	for j in (1, 4, 6):
		a = math.radians(45 * j + 12)
		_coral_cluster(soft, (math.cos(a) * (A + 1.2), math.sin(a) * (A + 1.2), base), 1.4)
	for j, z in ((0, base + 2 * SH + 0.4), (2, base + 2 * SH + 0.4), (6, base + SH + 0.35), (4, base + 2 * SH + 0.4)):
		a = math.radians(45 * j)
		for k in range(3):  # weed left hanging from the sills by old floods
			u = -0.5 + k * 0.5
			_weed_hang(soft, (math.cos(a) * (A + 0.42) - math.sin(a) * u, math.sin(a) * (A + 0.42) + math.cos(a) * u, z), p.rng.uniform(0.5, 1.2), r=0.05)
	obj = join_into(p.build(bevel=0.05), [soft.build()])
	# the walls: KayKit's own, storey on storey
	rows = [
		["wall", "wall", "wall_cracked", "wall", "wall", "wall", "wall_doorway", "wall"],
		["wall", "wall", "wall_window_open", "wall", "wall_cracked", "wall", "wall_window_open", "wall"],
		["wall_archedwindow_open", "wall", "wall_archedwindow_open", "wall", "wall_archedwindow_open", "wall_cracked", "wall_archedwindow_open", "wall"],
		["wall", "wall_archedwindow_open", "wall_cracked", "wall_archedwindow_open", "wall", "wall_archedwindow_open", "wall", "wall_archedwindow_open"],
	]
	sx = 2 * A * math.tan(math.pi / 8) / 4.0
	pieces = []
	for i, row in enumerate(rows + [["wall", "wall_broken", None, "wall", "wall_archedwindow_open", None, "wall", "wall_broken"]]):
		for j, piece in enumerate(row):
			if piece is None:
				continue
			a = math.radians(45 * j)
			hz = SH / 4.0
			if i == 4:
				if top[j] < 1.0:
					continue
			pieces += kaykit(piece, (math.cos(a) * A, math.sin(a) * A, base + i * SH), a - math.pi / 2, (sx, 0.75, hz))
	for j in range(8):  # the broken sides' lower courses, KayKit stone under the rough blocks
		if 0.0 < top[j] < 1.0:
			a = math.radians(45 * j)
			pieces += kaykit("wall_half" if j % 2 else "wall", (math.cos(a) * A, math.sin(a) * A, top_floor), a - math.pi / 2, (sx, 0.75, SH * top[j] / 4.0))
	pieces += kaykit("banner_patternA_blue", (math.cos(math.radians(-45)) * (A + 0.1), math.sin(math.radians(-45)) * (A + 0.1), base + 2 * SH + 0.4),
					 math.radians(-45) - math.pi / 2 + math.pi, (0.9, 0.9, 0.9))
	return _merge_materials(join_into(obj, pieces))


def citadel_wall_ruin():
	"""A broken run of the citadel's curtain wall along X, about 14 m, sunk a
	meter into the flood bed: a KayKit wall with a corner pillar at -X, a gate
	(wall_doorway_sides) with its rusted portcullis jammed up in the arch, and
	at +X a section tipping outward and sinking, its end fallen into rubble;
	merlons along the top (5.2 m above the bed), weed at the water line (2 m),
	barnacles and coral. Faces -Y. Origin on the bed. Collide it as a mesh
	(the gate is passable)."""
	p = Prop("citadel_wall_ruin", 312)
	soft = Prop("citadel_wall_ruin_soft", 312)  # weed, slime, barnacles and coral: left unbeveled
	z0, zs = -1.0, 1.3
	top = z0 + 4.0 * zs
	n = 5
	for k in range(n):  # merlons on both faces of the west wall
		x = -6.6 + (k + 0.5) * 4.0 / n
		for s in (-1, 1):
			if s > 0 and k == 1:
				continue
			p.box((0.5, 0.3, 0.75), (x, s * 0.45, top + 0.37), STONE_DARK, grad=(0.05, 0.8))
	# the portcullis, rusted fast in the top of the arch
	for k in range(7):
		x = -1.05 + k * 2.1 / 6
		p.seg((x, 0.0, top - 2.3), (x, 0.0, top - 0.6), 0.045, 0.045, IRON, sides=5, grad=(0.1, 0.8))
		p.seg((x, 0.0, top - 2.3), (x, 0.0, top - 2.55), 0.045, 0.0, IRON, sides=5)
	for z in (top - 2.2, top - 1.5, top - 0.8):
		p.box((2.3, 0.08, 0.1), (0, 0.0, z), IRON, grad=(0.2, 0.9))
	water = 2.0
	_algae_band(soft, [(x, -0.5, 0) for x in (-6.9, -5.6, -4.4, -3.2)] + [(x, 0.5, 0) for x in (-6.2, -5.0, -3.8)], water)
	_algae_band(soft, [(x, y, 90) for x in (-2.1, 2.1) for y in (-1.5, 1.5)], water, size=(0.9, 0.4, 0.45))
	for x in (-5.5, -3.5):
		_barnacles(soft, (x, -0.5, 0.9), 7, 0.4, normal=(0, -1, 0.1))
	for k in range(6):
		_weed_hang(soft, (p.rng.uniform(-1.0, 1.0), p.rng.uniform(-0.2, 0.2), top - 2.55), p.rng.uniform(0.4, 0.9), r=0.04)
	_coral_cluster(soft, (-4.4, -1.0, 0.0), 1.5)
	for k in range(12):  # the rubble where the east end fell
		a = p.rng.uniform(-1.4, 1.4)
		d = p.rng.uniform(0.3, 2.6)
		s = p.rng.uniform(0.5, 1.1)
		p.box((s, s * 0.8, s * 0.6), (7.2 + math.cos(a) * d, math.sin(a) * d, p.rng.uniform(-0.1, 0.4)), STONE_DARK if k % 2 else STONE_LIGHT,
			  rot=(p.rng.uniform(-25, 25), p.rng.uniform(-25, 25), p.rng.uniform(0, 90)), grad=(0.1, 0.9))
	obj = join_into(p.build(bevel=0.04), [soft.build()])
	# the tipping east section, built upright and then leaned out
	q = Prop("citadel_wall_ruin_east", 322)
	for k in range(4):
		x = 2.6 + (k + 0.5) * 3.6 / 4
		for s in (-1, 1):
			hk = (0.75, 0.6, 0.35, 0.0)[k] if s < 0 else (0.75, 0.0, 0.5, 0.25)[k]
			if hk:
				q.box((0.5, 0.3, hk), (x, s * 0.45, top * 0.93 + hk / 2), STONE_DARK, grad=(0.05, 0.8))
	for k in range(5):  # its broken end
		q.rock((0.7, 0.9, 0.6), (6.1, p.rng.uniform(-0.4, 0.4), top * 0.93 - k * 0.9), STONE_DARK, jitter=0.08)
	_algae_band(q, [(x, -0.5, 0) for x in (3.0, 4.2, 5.4)] + [(x, 0.5, 0) for x in (3.2, 4.6)], water)
	_barnacles(q, (3.6, -0.5, 0.9), 7, 0.4, normal=(0, -1, 0.1))
	east = q.build(bevel=0.04)
	tip = kaykit("wall", (4.4, 0, z0), 0.0, (0.9, 0.85, zs * 0.93))
	east = join_into(east, tip)
	east.data.transform(Matrix.Translation((2.6, 0, z0 - 0.35)) @ Matrix.Rotation(math.radians(4), 4, "Y") @ Matrix.Rotation(math.radians(6), 4, "X") @ Matrix.Translation((-2.6, 0, -z0)))
	pieces = [east]
	pieces += kaykit("wall", (-4.6, 0, z0), 0.0, (1.0, 0.85, zs))
	pieces += kaykit("wall_doorway_sides", (0, 0, z0), 0.0, (0.9, 0.62, zs))
	pieces += kaykit("pillar", (-6.9, 0, z0), 0.0, (0.7, 0.7, zs * 1.12))
	return _merge_materials(join_into(obj, pieces))


def _clip_y(poly, y0, y1):
	"""Sutherland-Hodgman clip of a (y, z) polygon to y0 <= y <= y1."""
	def clip(pts, keep, cut):
		out = []
		for i, a in enumerate(pts):
			b = pts[(i + 1) % len(pts)]
			ka, kb = keep(a), keep(b)
			if ka:
				out.append(a)
			if ka != kb:
				t = (cut - a[0]) / (b[0] - a[0])
				out.append((cut, a[1] + (b[1] - a[1]) * t))
		return out
	pts = clip(poly, lambda q: q[0] >= y0 - 1e-6, y0)
	return clip(pts, lambda q: q[0] <= y1 + 1e-6, y1)


def _extrude_yz(p, outline, x0, x1, swatch, grad=(0.1, 0.9)):
	"""A solid from a (y, z) outline (any simple polygon) run along X from x0 to x1."""
	n = len(outline)
	verts = [(x0, y, z) for y, z in outline] + [(x1, y, z) for y, z in outline]
	faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
	for i in range(n):
		j = (i + 1) % n
		faces.append((i, j, n + j, n + i))
	return p.poly(verts, faces, swatch, grad)


CAUSEWAY_DEEP = -6.0


def _causeway_outline():
	"""The causeway's side elevation (y, z): deck underside at -0.12, a main
	arch between piers at y = +-2.4..3.6, quarter arches at both ends that
	meet the next span's into a small arch."""
	pts = [(-4.5, -0.12), (4.5, -0.12), (4.5, -0.8)]
	for k in range(1, 7):
		a = math.pi / 2 + k * (math.pi / 2) / 6
		pts.append((4.5 + 0.9 * math.cos(a), -1.7 + 0.9 * math.sin(a)))
	pts += [(3.6, CAUSEWAY_DEEP), (2.4, CAUSEWAY_DEEP), (2.4, -3.2)]
	for k in range(1, 16):
		a = k * math.pi / 16
		pts.append((2.4 * math.cos(a), -3.2 + 2.4 * math.sin(a)))
	pts += [(-2.4, -3.2), (-2.4, CAUSEWAY_DEEP), (-3.6, CAUSEWAY_DEEP), (-3.6, -1.7)]
	for k in range(1, 6):
		a = k * (math.pi / 2) / 6
		pts.append((-4.5 + 0.9 * math.cos(a), -1.7 + 0.9 * math.sin(a)))
	pts.append((-4.5, -0.8))
	return pts


def _flagstones(p, x0, x1, y0, y1, rows, ragged=None, broken=()):
	"""Paving with every top exactly at 0: rows along Y, two or three stones
	across each (staggered). `ragged` = (x_edge, side) breaks the stones off
	near x_edge on that side; `broken` lists (row, col) stones cracked in
	shards."""
	L = (y1 - y0) / rows
	for r in range(rows):
		y = y0 + (r + 0.5) * L
		cuts = [x0, x0 + (x1 - x0) * (0.45 if r % 2 else 0.55), x1] if (x1 - x0) < 3.0 else [x0 + (x1 - x0) * t for t in ((0, 0.3, 0.65, 1.0) if r % 2 else (0, 0.4, 0.72, 1.0))]
		for c in range(len(cuts) - 1):
			a, b = cuts[c], cuts[c + 1]
			if ragged:
				edge, side = ragged
				e = edge + p.rng.uniform(-0.15, 0.1) * side
				if side < 0:
					b = min(b, e)
				else:
					a = max(a, e)
				if b - a < 0.15:
					continue
			sw = (STONE_LIGHT, SEA_STONE, STONE_WARM)[(r + c) % 3]
			if (r, c) in broken:
				m = (a + b) / 2 + p.rng.uniform(-0.15, 0.15)
				p.box((m - a - 0.07, L - 0.05, 0.12), ((a + m) / 2, y, -0.06), sw, rot=(0, 0, p.rng.uniform(-4, 4)), grad=(0.1, 0.7))
				p.box((b - m - 0.07, (L - 0.05) / 2 - 0.03, 0.12), ((m + b) / 2, y - L / 4, -0.06), sw, rot=(0, 0, p.rng.uniform(-6, 6)), grad=(0.1, 0.7))
				p.box((b - m - 0.07, (L - 0.05) / 2 - 0.03, 0.12), ((m + b) / 2, y + L / 4, -0.075), sw, rot=(0, 0, p.rng.uniform(-6, 6)), grad=(0.1, 0.7))
				continue
			p.box((b - a - 0.04, L - 0.04, 0.12), ((a + b) / 2, y, -0.06), sw, grad=(0.1, 0.7))


def _causeway(name, seed, broken):
	p = Prop(name, seed)
	soft = Prop(name + "_soft", seed)  # weed, slime, barnacles and coral: left unbeveled
	outline = _causeway_outline()
	if not broken:
		_extrude_yz(p, outline, -1.4, 1.4, STONE_LIGHT)
	else:
		for y0, y1 in ((-4.5, -1.3), (1.3, 4.5)):
			_extrude_yz(p, _clip_y(outline, y0, y1), -1.4, 1.4, STONE_LIGHT)
		_extrude_yz(p, _clip_y(outline, -1.3, 1.3), -1.4, -0.4, STONE_LIGHT)
		for k in range(12):  # the broken faces: jagged blocks
			y = p.rng.choice((-1.3, 1.3))
			p.rock((0.55, 0.45, 0.45), (p.rng.uniform(-0.2, 1.3), y + p.rng.uniform(-0.12, 0.12), p.rng.uniform(-1.6, -0.3)), STONE_LIGHT, jitter=0.08)
		for k in range(6):
			p.rock((0.4, 0.5, 0.45), (-0.35 + p.rng.uniform(-0.05, 0.1), p.rng.uniform(-1.2, 1.2), p.rng.uniform(-1.4, -0.35)), STONE_LIGHT, jitter=0.07)
		for k in range(12):  # what fell, heaped in the water under the gap
			s = p.rng.uniform(0.6, 1.2)
			p.box((s, s * 0.8, s * 0.6), (p.rng.uniform(-0.6, 2.2), p.rng.uniform(-1.6, 1.6), p.rng.uniform(-3.6, -2.4)), STONE_LIGHT if k % 2 else SEA_STONE,
				  rot=(p.rng.uniform(-30, 30), p.rng.uniform(-30, 30), p.rng.uniform(0, 90)), grad=(0.1, 0.9))
	for s in (-1, 1):
		for yc in (-3.0, 3.0):  # cutwaters on the piers, pointed against the current
			p.box((0.85, 0.85, CAUSEWAY_DEEP * -1 - 1.4), (s * 1.4, yc, (CAUSEWAY_DEEP - 1.6) / 2), SEA_STONE, rot=(0, 0, 45), grad=(0.1, 1.0))
			p.seg((s * 1.4, yc, -1.62), (s * 1.4, yc, -0.95), 0.62, 0.05, SEA_STONE, sides=4, grad=(0.0, 0.7))
			_barnacles(soft, (s * 1.85, yc, -1.3), 5, 0.25, normal=(s, 0, 0.1))
		for (yc, r, zc, a0, a1, n) in ((0.0, 2.4, -3.2, 0.0, math.pi, 9), (4.5, 0.9, -1.7, math.pi / 2, math.pi, 3), (-4.5, 0.9, -1.7, 0.0, math.pi / 2, 3)):
			for k in range(n):  # voussoirs standing proud round the arches
				a = a0 + (k + 0.5) * (a1 - a0) / n
				if broken and yc == 0.0 and s > 0 and 3 <= k <= 5:
					continue  # fell with the middle
				y, z = yc + (r + 0.18) * math.cos(a), zc + (r + 0.18) * math.sin(a)
				big = yc == 0.0 and k == n // 2
				p.box((0.12, 0.42 if not big else 0.6, 0.5 if not big else 0.8), (s * 1.44, y, z), STONE_WARM if not big else SEA_STONE,
					  rot=(math.degrees(a) - 90, 0, 0), grad=(0.1, 0.8))
		# the string course under the parapet and the parapet itself
		spans = [(-4.5, 4.5)]
		if broken:
			spans = [(-4.5, -1.3), (1.3, 4.5)] if s > 0 else [(-4.5, -0.9), (0.6, 4.5)]
		for y0, y1 in spans:
			p.box((0.26, y1 - y0, 0.22), (s * 1.44, (y0 + y1) / 2, -0.28), STONE_WARM, grad=(0.1, 0.7))
			n = max(1, round((y1 - y0) / 1.0))
			for k in range(n):
				ya = y0 + k * (y1 - y0) / n + 0.03
				yb = y0 + (k + 1) * (y1 - y0) / n - 0.03
				if not broken and s > 0 and k == 6:  # one block knocked off
					p.box((0.3, yb - ya, 0.22), (s * 1.32, (ya + yb) / 2, 0.11), STONE_LIGHT, grad=(0.1, 0.8))
					continue
				p.box((0.3, yb - ya, 0.42), (s * 1.32, (ya + yb) / 2, 0.21), STONE_LIGHT, grad=(0.1, 0.9))
				p.box((0.4, yb - ya + 0.02, 0.1), (s * 1.32, (ya + yb) / 2, 0.47), STONE_WARM, grad=(0.0, 0.6))
	if broken:
		_flagstones(p, -1.17, 1.17, -4.5, -1.3, 3, broken=((1, 1),))
		_flagstones(p, -1.17, 1.17, 1.3, 4.5, 3, broken=((2, 0),))
		_flagstones(p, -1.17, -0.45, -1.3, 1.3, 3, ragged=(-0.45, -1))
	else:
		_flagstones(p, -1.17, 1.17, -4.5, 4.5, 9, broken=((3, 1), (7, 0)))
	water = -1.0
	_algae_band(soft, [(s * 1.9, yc + u, 90) for s in (-1, 1) for yc in (-3.0, 3.0) for u in (-0.3, 0.3)], water, size=(0.7, 0.35, 0.4))
	for k in range(6):
		s = p.rng.choice((-1, 1))
		y = p.rng.uniform(-4.2, 4.2)
		if broken and abs(y) < 1.5:
			continue
		_weed_hang(soft, (s * 1.58, y, -0.38), p.rng.uniform(0.4, 0.8), r=0.04)
	return join_into(p.build(bevel=0.04), [soft.build()])


def causeway_span():
	"""A 3 x 9 m stretch of the Tide Kings' stone causeway, running along Y: a
	flagstone top (the origin, flat) between low parapets (0.52 m), a round
	arch between two cutwater piers that go 6 m down, and half arches at both
	ends that close into small arches with the next span's (or meet a
	citadel_platform's edge). Walkable x in [-1.15, 1.15], all of y. Weed and
	barnacles about 1 m under the deck (where the water stands if the deck is
	set a meter above it). Collide it as a mesh."""
	return _causeway("causeway_span", 313, False)


def causeway_broken():
	"""causeway_span with its middle fallen in: for y in [-1.3, 1.3] only a
	strip along the -X side still stands on what is left of the arch (flat,
	walkable for x in [-1.15, -0.5]), the rest a gap over a heap of fallen
	stone in the water. Both ends walkable full width (x in [-1.15, 1.15]).
	Collide it as a mesh."""
	return _causeway("causeway_broken", 314, True)


def citadel_platform():
	"""A 9 x 9 m stone plaza of the citadel on nine KayKit pillars running 6 m
	down, its top (the origin) paved flat, a few flagstones cracked; a cornice
	round the edge, weed and barnacles on the pillars about 1 m down. Tiles
	edge to edge with causeway_span on the stilt pieces' 9 m grid. Walkable
	over all of it. Collide it as a mesh."""
	p = Prop("citadel_platform", 315)
	soft = Prop("citadel_platform_soft", 315)  # weed, slime, barnacles and coral: left unbeveled
	h = 4.5
	p.box((2 * h, 2 * h, 0.7), (0, 0, -0.12 - 0.35), STONE_LIGHT, grad=(0.1, 0.9))
	for s in (-1, 1):  # the cornice
		p.box((2 * h + 0.3, 0.26, 0.24), (0, s * (h + 0.02), -0.5), STONE_WARM, grad=(0.0, 0.7))
		p.box((0.26, 2 * h + 0.3, 0.24), (s * (h + 0.02), 0, -0.5), STONE_WARM, grad=(0.0, 0.7))
		p.box((2 * h, 0.2, 0.12), (0, s * (h - 0.1), -0.06), STONE_WARM, grad=(0.0, 0.6))  # kerb, flush with the paving
		p.box((0.2, 2 * h - 0.4, 0.12), (s * (h - 0.1), 0, -0.06), STONE_WARM, grad=(0.0, 0.6))
	L = (2 * h - 0.4) / 8
	for r in range(8):
		for c in range(8):
			x0 = -h + 0.2 + c * L
			y0 = -h + 0.2 + r * L
			sw = (STONE_LIGHT, SEA_STONE, STONE_WARM)[(r * 3 + c * 2 + (r * c) % 2) % 3]
			if (r, c) in ((1, 5), (4, 2), (6, 6), (7, 1)):
				m = x0 + L * p.rng.uniform(0.35, 0.65)
				p.box((m - x0 - 0.06, L - 0.04, 0.12), ((x0 + m) / 2, y0 + L / 2, -0.06), sw, rot=(0, 0, p.rng.uniform(-4, 4)), grad=(0.1, 0.7))
				p.box((x0 + L - m - 0.06, L / 2 - 0.05, 0.12), ((m + x0 + L) / 2, y0 + L * 0.25, -0.07), sw, rot=(0, 0, p.rng.uniform(-6, 6)), grad=(0.1, 0.7))
				p.box((x0 + L - m - 0.06, L / 2 - 0.05, 0.12), ((m + x0 + L) / 2, y0 + L * 0.75, -0.065), sw, rot=(0, 0, p.rng.uniform(-6, 6)), grad=(0.1, 0.7))
				continue
			p.box((L - 0.04, L - 0.04, 0.12), (x0 + L / 2, y0 + L / 2, -0.06), sw, grad=(0.1, 0.7))
	for x, y, sx, sy in ((-3.1, 2.6, 0.9, 0.5), (2.2, -3.4, 0.7, 0.4), (3.8, 1.2, 0.5, 0.8)):
		_moss_patch(soft, x, y, 0.0, sx, sy)
	water = -1.0
	for i, x in enumerate((-3.4, 0.0, 3.4)):
		for j, y in enumerate((-3.4, 0.0, 3.4)):
			_algae_band(soft, [(x + math.cos(a) * 0.55, y + math.sin(a) * 0.55, math.degrees(a) + 90) for a in (0.3, 1.9, 3.5, 5.1)], water, size=(0.6, 0.3, 0.35))
			if (i + j) % 2 == 0:
				_barnacles(soft, (x + 0.52, y, water - 0.5), 5, 0.2, normal=(1, 0, 0))
	for k in range(8):
		s = p.rng.choice((-1, 1))
		u = p.rng.uniform(-4.2, 4.2)
		pos = (s * (h + 0.16), u, -0.6) if k % 2 else (u, s * (h + 0.16), -0.6)
		_weed_hang(soft, pos, p.rng.uniform(0.3, 0.7), r=0.04)
	obj = join_into(p.build(bevel=0.04), [soft.build()])
	pieces = []
	for x in (-3.4, 0.0, 3.4):
		for y in (-3.4, 0.0, 3.4):
			pieces += kaykit("pillar", (x, y, CAUSEWAY_DEEP), 0.0, (0.7, 0.7, (-0.8 - CAUSEWAY_DEEP) / 4.0))
	return _merge_materials(join_into(obj, pieces))


def sea_temple():
	"""The great sea temple of Jalendra at the heart of Drownfast: three stepped
	tiers of blue-gray stone (18 m square at the foot, sunk 1.2 m in the bed so
	the flood covers its first course), a grand stair up the front (-Y) to a
	shrine whose facade is Jalendra's elephant head, ears spread 7 m, trunk
	raised and pouring a glowing stream down the stair into the flood. A
	stepped roof and a spire carry a glowing pearl 19 m up, to be seen from
	across the valley. The stair (6 m further out) is for looking at. Origin
	on the bed. Collide it as a mesh."""
	p = Prop("sea_temple", 316)
	soft = Prop("sea_temple_soft", 316)  # weed, slime, barnacles and coral: left unbeveled
	tiers = [(9.0, -1.2, 3.2), (7.0, 3.2, 5.8), (5.2, 5.8, 8.2)]
	for i, (hs, z0, z1) in enumerate(tiers):
		p.box((2 * hs, 2 * hs, z1 - z0), (0, 0, (z0 + z1) / 2), SEA_STONE if i % 2 else STONE_LIGHT, grad=(0.1, 0.95))
		p.box((2 * hs + 0.4, 2 * hs + 0.4, 0.3), (0, 0, z1 - 0.12), STONE_WARM, grad=(0.0, 0.6))  # cornice
		p.box((2 * hs + 0.25, 2 * hs + 0.25, 0.35), (0, 0, max(z0, 0.0) + 0.3 if i else 0.3), STONE_DARK, grad=(0.2, 0.9))
		for s in (-1, 1):  # pilasters down the faces
			for u in [-hs + 0.9 + k * (2 * hs - 1.8) / 4 for k in range(5)]:
				if i < 2 and abs(u) < 2.4:
					continue
				for (x, y, sx, sy) in ((u, s * (hs + 0.12), 0.8, 0.3), (s * (hs + 0.12), u, 0.3, 0.8)):
					p.box((sx, sy, z1 - max(z0, 0.0) - 0.8), (x, y, (z1 + max(z0, 0.0)) / 2 - 0.1), STONE_LIGHT if i % 2 else SEA_STONE, grad=(0.05, 0.9))
		for k in range(int(2 * hs / 1.6)):  # the wave frieze under the cornice
			u = -hs + 0.8 + k * 1.6
			for (x, y, yaw) in ((u, -hs - 0.18, 0), (u, hs + 0.18, 0), (-hs - 0.18, u, 90), (hs + 0.18, u, 90)):
				p.blob((0.9, 0.18, 0.45), (x, y, z1 - 0.55), TEAL, rot=(0, 0, yaw), segs=(8, 4), grad=(0.0, 0.7))
	# the stair: 21 steps of 0.4 up to the top tier's face, balustrades with sea-serpent ends
	n, rise, tread = 21, 0.39, 0.45
	y_top = -tiers[2][0]
	run = n * tread
	for k in range(n):
		d = run - k * tread
		p.box((3.6, d, rise), (0, y_top - d / 2, k * rise + rise / 2), STONE_LIGHT if k % 2 else SEA_STONE, grad=(0.1, 0.8))
	zt = tiers[2][2]
	ang = math.degrees(math.atan2(zt, run))
	for s in (-1, 1):
		p.box((0.6, math.hypot(zt, run), 0.6), (s * 2.1, y_top - run / 2, zt / 2 + 0.3), STONE_DARK, rot=(ang, 0, 0), grad=(0.1, 0.8))
		p.box((1.1, 1.1, 1.6), (s * 2.1, y_top - run - 0.2, 0.8), STONE_DARK, grad=(0.1, 0.8))
		_chain(p, [(s * 2.1, y_top - run - 0.2, 1.5), (s * 2.1, y_top - run - 0.5, 2.3), (s * 2.1, y_top - run - 1.0, 2.6), (s * 2.1, y_top - run - 1.3, 2.3)],
			   0.4, 0.22, TEAL, sides=8, grad=(0.0, 0.7))  # a stone serpent rearing on the newel
		p.blob((0.6, 0.8, 0.45), (s * 2.1, y_top - run - 1.35, 2.25), TEAL, segs=(8, 6), grad=(0.0, 0.7))
		p.blob((0.12, 0.1, 0.1), (s * 2.1 + 0.18 * s, y_top - run - 1.65, 2.35), GOLD, segs=(5, 4), glow=0.2)
	# the shrine: 7.2 x 6 m, walls 3.6 m, the head its facade
	rw, rd, rh = 3.6, 3.0, 3.8
	fz = zt
	p.box((0.7, 2 * rd, rh), (-rw + 0.35, 0, fz + rh / 2), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((0.7, 2 * rd, rh), (rw - 0.35, 0, fz + rh / 2), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((2 * rw, 0.7, rh), (0, rd - 0.35, fz + rh / 2), STONE_LIGHT, grad=(0.1, 0.9))
	dw, dh = 2.2, 3.0
	fy = -rd + 0.35
	for s in (-1, 1):
		p.box(((2 * rw - dw) / 2, 0.7, rh), (s * (dw / 2 + (2 * rw - dw) / 4), fy, fz + rh / 2), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((dw, 0.7, rh - dh), (0, fy, fz + dh + (rh - dh) / 2), STONE_LIGHT, grad=(0.1, 0.9))
	p.box((dw, 0.1, dh), (0, fy + 0.3, fz + dh / 2), IRON, grad=(0.6, 1.0))
	p.box((2 * rw - 1.4, 2 * rd - 1.4, 0.1), (0, 0, fz + 0.05), IRON, grad=(0.6, 1.0))
	for s in (-1, 1):  # door jambs with gold bands
		p.box((0.4, 0.9, dh + 0.2), (s * (dw / 2 + 0.2), fy - 0.1, fz + (dh + 0.2) / 2), SEA_STONE, grad=(0.05, 0.8))
		for z in (0.6, 1.6, 2.6):
			p.box((0.44, 0.94, 0.1), (s * (dw / 2 + 0.2), fy - 0.1, fz + z), GOLD, grad=(0.0, 0.5), glow=0.2)
	# the roof: stepped slabs, a drum and the spire with its pearl
	rz = fz + rh
	for k, (ax, ay, th) in enumerate(((rw + 0.5, rd + 0.5, 0.45), (rw - 0.2, rd - 0.2, 0.7), (rw - 1.0, rd - 1.0, 0.7), (rw - 1.8, rd - 1.8, 0.6))):
		p.box((2 * ax, 2 * ay, th), (0, 0.3 * (k > 0), rz + th / 2), STONE_WARM if k % 2 else STONE_LIGHT, grad=(0.0, 0.8))
		rz += th
	p.seg((0, 0.3, rz), (0, 0.3, rz + 1.4), 1.1, 0.95, SEA_STONE, sides=8, grad=(0.0, 0.8))
	p.seg((0, 0.3, rz + 1.4), (0, 0.3, rz + 1.6), 1.2, 1.2, GOLD, sides=8, glow=0.2)
	p.seg((0, 0.3, rz + 1.6), (0, 0.3, rz + 4.2), 0.9, 0.15, STONE_LIGHT, sides=8, grad=(0.0, 0.8))
	for k in range(8):  # petals holding the pearl
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.15, 0.3 + math.sin(a) * 0.15, rz + 4.1), (math.cos(a) * 0.55, 0.3 + math.sin(a) * 0.55, rz + 4.6), 0.12, 0.03, GOLD, sides=4, glow=0.2)
	p.blob((0.9, 0.9, 0.9), (0, 0.3, rz + 4.75), RUNE, segs=(12, 8), grad=(0.0, 0.4), glow=2.2)
	for s in (-1, 1):  # pinnacles on the top tier's corners
		for t in (-1, 1):
			x, y = s * (tiers[2][0] - 0.7), t * (tiers[2][0] - 0.7)
			p.seg((x, y, zt), (x, y, zt + 1.6), 0.45, 0.38, SEA_STONE, sides=8, grad=(0.0, 0.8))
			p.seg((x, y, zt + 1.6), (x, y, zt + 2.8), 0.45, 0.0, STONE_LIGHT, sides=8, grad=(0.0, 0.7))
			p.blob((0.3, 0.3, 0.3), (x, y, zt + 2.85), RUNE, glow=1.2)
	# Jalendra's head over the door, trunk raised, pouring
	hs_ = 2.5
	hc = (0, fy - 1.0, fz + dh + 1.8)
	trunk = [(0, -0.45, -0.3), (0, -0.8, -0.35), (0, -1.15, -0.2), (0, -1.45, 0.05), (0, -1.7, 0.3), (0, -1.9, 0.42)]
	_elephant_head(p, hc, hs_, STONE_LIGHT, trunk=trunk)
	p.seg((0, hc[1] + 0.2, hc[2] + 0.85 * hs_ * 0.6), (0, hc[1] + 0.05, hc[2] + hs_ * 0.75), 0.55 * hs_ * 0.6, 0.3 * hs_ * 0.6, GOLD, sides=8, glow=0.2)
	for s in (-1, 1):
		p.blob((0.25, 0.1, 0.25), (s * 0.26 * hs_, hc[1] - 0.46 * hs_, hc[2] + 0.15 * hs_), RUNE, segs=(6, 4), glow=1.2)  # eyes of sea-glass
	sx, sy, sz = 0.0, hc[1] - 1.9 * hs_, hc[2] + 0.42 * hs_
	arc = []
	land_k = 12
	land_y = y_top - land_k * tread
	land_z = zt - land_k * rise
	for k in range(14):
		t = k / 13
		up = 1.6
		arc.append((sx, sy + (land_y - sy) * t ** 0.8, sz + 2 * up * t - (2 * up + sz - land_z) * t ** 2))
	_chain(p, arc, 0.2, 0.42, WATER, sides=8, grad=(0.0, 0.5), glow=0.2)
	# the stream running down the stair: a sheet over the steps' noses
	pts_a, pts_b = [], []
	for k in range(land_k, n + 1):
		y = y_top - k * tread
		z = zt - k * rise + 0.08
		pts_a.append((-0.8, y, z))
		pts_b.append((0.8, y, z))
	_slab(p, pts_a, pts_b, 0.1, WATER, grad=(0.0, 0.5), glow=0.2)
	for k in range(7):  # foam where it lands and where it meets the flood
		a = k * math.tau / 7
		p.blob((0.7, 0.7, 0.35), (math.cos(a) * 0.6, land_y + math.sin(a) * 0.5, land_z + 0.15), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.4))
		p.blob((0.9, 0.8, 0.3), (math.cos(a) * 0.9, y_top - run - 0.6 + math.sin(a) * 0.5, 2.0), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.4))
	# the flood's marks: weed at the water line, barnacles, coral, a tumbled corner
	water = 2.0
	pts = []
	for u in [-8.4 + k * 1.2 for k in range(15)]:
		if abs(u) < 2.6:
			continue
		pts += [(u, -9.15, 0), (u, 9.15, 0), (-9.15, u, 90), (9.15, u, 90)]
	_algae_band(soft, pts, water, size=(1.3, 0.4, 0.5))
	for (x, y, nx, ny) in ((-6, -9.2, 0, -1), (5, -9.2, 0, -1), (-9.2, 3, -1, 0), (9.2, -4, 1, 0), (2, 9.2, 0, 1)):
		_barnacles(soft, (x, y, 1.2), 9, 0.6, normal=(nx, ny, 0.1))
	for (x, y) in ((-7.5, -9.8), (6.8, -9.9), (-9.9, 6.0), (9.8, 2.5), (4.0, 9.9), (-3.4, -10.2)):
		_coral_cluster(soft, (x, y, 0.0), 1.6)
	for k in range(10):
		s = p.rng.uniform(0.8, 1.5)
		p.box((s, s * 0.8, s * 0.6), (8.6 + p.rng.uniform(-1.5, 2.5), 8.6 + p.rng.uniform(-1.5, 2.5), p.rng.uniform(0.0, 1.0)), STONE_LIGHT if k % 2 else SEA_STONE,
			  rot=(p.rng.uniform(-25, 25), p.rng.uniform(-25, 25), p.rng.uniform(0, 90)), grad=(0.1, 0.9))
	obj = join_into(p.build(bevel=0.06), [soft.build()])
	pieces = []
	for s in (-1, 1):  # KayKit pillars by the shrine door
		pieces += kaykit("pillar", (s * (rw + 0.2), -rd - 0.1, fz), 0.0, (0.6, 0.6, rh / 4.0))
		pieces += kaykit("banner_thin_blue", (s * 3.3, -tiers[1][0] - 0.05, 2.2), 0.0, (0.9, 0.9, 0.9))  # the Tide Kings' colors by the stair
	return _merge_materials(join_into(obj, pieces))


def tideking_throne():
	"""The throne of the last Tide King: a high-backed stone seat under a
	scallop-shell crest (about 3.9 m to its top), its arms ending in wave
	curls, on a two-step dais 3.6 x 3.2 m, crusted with coral and barnacles, a
	tarnished crown left on the seat and a trident against its arm. Faces -Y.
	Collide it as a box."""
	p = Prop("tideking_throne", 317)
	soft = Prop("tideking_throne_soft", 317)  # weed, slime, barnacles and coral: left unbeveled
	p.box((3.6, 3.2, 0.3), (0, 0.2, 0.15), SEA_STONE, grad=(0.2, 0.9))
	p.box((2.8, 2.4, 0.3), (0, 0.4, 0.45), STONE_LIGHT, grad=(0.1, 0.8))
	for s in (-1, 1):
		p.box((3.64, 0.1, 0.06), (0, -1.4, 0.28), GOLD, grad=(0.0, 0.5))
	fz = 0.6
	p.box((1.4, 1.0, 0.5), (0, 0.45, fz + 0.25), STONE_LIGHT, grad=(0.1, 0.9))  # seat
	p.box((1.5, 1.1, 0.12), (0, 0.42, fz + 0.54), STONE_WARM, grad=(0.0, 0.6))
	p.box((1.5, 0.4, 2.3), (0, 1.0, fz + 1.55), STONE_LIGHT, grad=(0.05, 0.9))  # back
	p.box((1.1, 0.1, 1.7), (0, 0.79, fz + 1.55), TEAL, grad=(0.0, 0.8))  # a patina panel
	p.box((0.12, 0.08, 1.5), (0, 0.74, fz + 1.5), GOLD, grad=(0.0, 0.5))
	for s in (-1, 1):  # arms ending in wave curls
		p.box((0.3, 1.1, 0.5), (s * 0.85, 0.45, fz + 0.65), STONE_LIGHT, grad=(0.05, 0.8))
		pts = [(s * 0.85, -0.1, fz + 0.9), (s * 0.85, -0.25, fz + 0.95), (s * 0.85, -0.35, fz + 0.8), (s * 0.85, -0.28, fz + 0.62), (s * 0.85, -0.14, fz + 0.66), (s * 0.85, -0.17, fz + 0.77)]
		_chain(p, pts, 0.17, 0.08, SEA_STONE, sides=8, grad=(0.0, 0.7))
		p.box((0.36, 0.42, 0.72), (s * 0.85, 0.0, fz + 0.36), STONE_LIGHT, grad=(0.05, 0.9))
	# the scallop crest: ribs fanned over a shell plate
	cz, cy = fz + 2.7, 1.05
	outline = [(math.cos(math.radians(a)) * 1.25, cz + math.sin(math.radians(a)) * 1.1) for a in range(0, 181, 15)] + [(-0.3, cz - 0.15), (0.3, cz - 0.15)]
	_plate(p, outline, cy, 0.3, SEA_STONE, grad=(0.0, 0.8))
	for k in range(9):
		a = math.radians(10 + k * 20)
		p.seg((0, cy - 0.12, cz - 0.05), (math.cos(a) * 1.2, cy - 0.16, cz + math.sin(a) * 1.05), 0.09, 0.07, STONE_LIGHT, sides=6, grad=(0.0, 0.7))
	p.blob((0.4, 0.3, 0.4), (0, cy - 0.2, cz), GOLD, segs=(8, 6), grad=(0.0, 0.5), glow=0.2)
	p.blob((0.28, 0.2, 0.28), (0, cy - 0.3, cz + 0.02), RUNE, segs=(8, 6), glow=1.4)  # a pearl set in it
	# coral and barnacles creeping over it all
	for c, sc in (((0.7, 1.25, fz + 1.2), 0.9), ((-0.8, 1.2, fz + 2.2), 0.8), ((1.3, -0.4, 0.6), 1.0), ((-1.4, 1.2, 0.6), 1.2), ((-1.2, -0.9, 0.3), 0.8)):
		_coral_cluster(soft, c, sc)
	_barnacles(soft, (-0.7, 0.2, fz + 0.9), 8, 0.15, normal=(0, 0, 1))
	_barnacles(soft, (0.6, 0.8, fz + 2.6), 7, 0.25, normal=(0, -1, 0.3))
	_barnacles(soft, (1.75, 0.8, 0.2), 8, 0.3, normal=(1, 0, 0.2))
	# the crown left on the seat and a trident leaning on the right arm
	cr = (0.2, 0.3, fz + 0.62)
	p.seg(cr, (cr[0], cr[1], cr[2] + 0.12), 0.16, 0.17, GOLD, sides=10, grad=(0.0, 0.6), glow=0.15)
	for k in range(5):
		a = k * math.tau / 5
		p.seg((cr[0] + math.cos(a) * 0.15, cr[1] + math.sin(a) * 0.15, cr[2] + 0.1), (cr[0] + math.cos(a) * 0.17, cr[1] + math.sin(a) * 0.17, cr[2] + 0.25), 0.04, 0.0, GOLD, sides=4, glow=0.15)
	p.seg((1.2, -0.6, 0.62), (1.05, 0.2, 3.0), 0.04, 0.035, IRON, sides=6)
	p.seg((0.95, 0.24, 2.95), (1.18, 0.21, 3.0), 0.03, 0.03, IRON, sides=4)
	for dx in (-0.12, 0.0, 0.12):
		p.seg((1.06 + dx, 0.22, 2.97), (1.06 + dx * 1.2, 0.26, 3.45 if dx == 0 else 3.3), 0.025, 0.0, IRON, sides=4)
	return join_into(p.build(bevel=0.03), [soft.build()])


def shipwreck():
	"""A wrecked two-masted ship lying on its side in the flood: the planked
	hull (about 11 m from the snapped bow to the stern, 4 m in the beam) rolled
	24 degrees and settled bow-down in the bed, ribs showing where the bow broke
	away and through a hole in its flank, the sterncastle still decked, a mast
	snapped off with a rag of sail, and the broken bow lying off to one side
	(about 15 m overall). Origin on the bed. Collide it as a mesh."""
	p = Prop("shipwreck", 318)
	soft = Prop("shipwreck_soft", 318)  # weed, slime, barnacles and coral: left unbeveled
	L0, L1 = -4.0, 7.0  # hull from the break to the stern
	W, D, nu = 2.0, 3.2, 9
	start = len(p.parts)

	def section(y, shrink=1.0, lift=0.0):
		t = (y - L0) / (L1 - L0)
		w = W * (0.62 + 0.38 * math.sin(min(1.0, 0.35 + t * 0.9) * math.pi * 0.95)) * shrink  # full amidships, narrowing to the stern
		g = D + 0.35 * max(0.0, t - 0.7) / 0.3  # the sheer rises at the stern
		dep = D * shrink
		return [(math.cos(math.pi * i / (nu - 1)) * w, y, g - math.sin(math.pi * i / (nu - 1)) * dep ** 1.0 * (0.55 + 0.45 * math.sin(math.pi * i / (nu - 1))) + lift) for i in range(nu)]

	nsec = 14
	ys = [L0 + (L1 - L0) * k / nsec for k in range(nsec + 1)]
	outer = [section(y) for y in ys]
	inner = [section(y, 0.9, 0.08) for y in ys]
	hole = {(k, i) for k in (6, 7) for i in (1, 2)} | {(0, i) for i in (0, 1, 7, 8)} | {(1, 0), (1, 8), (0, 2), (1, 1)}
	for grid, sw0, grad in ((outer, WOOD, (0.1, 0.9)), (inner, WOOD_GRAY, (0.4, 1.0))):
		for i in range(nu - 1):  # one strip per plank row, so the rows read
			for k in range(nsec):
				if (k, i) in hole:
					continue
				sw = sw0 if grid is inner else (WOOD if i % 2 else WOOD_GRAY)
				p.poly([grid[k][i], grid[k + 1][i], grid[k + 1][i + 1], grid[k][i + 1]], [(0, 1, 2, 3)], sw, grad)
	for k in range(nsec):  # gunwales
		for i in (0, nu - 1):
			if (k, i) in hole:
				continue
			p.poly([outer[k][i], outer[k + 1][i], inner[k + 1][i], inner[k][i]], [(0, 1, 2, 3)], WOOD, grad=(0.0, 0.4))
	for k in (0, 1, 2, 6, 7, 8):  # ribs where the planks are gone
		y = ys[k] + 0.3
		sec = section(y, 0.95, 0.0)
		_chain(p, sec, 0.09, 0.09, WOOD, sides=4, grad=(0.2, 0.9))
	# the transom and the sterncastle
	st = outer[-1]
	p.poly(list(st), [tuple(range(nu))], WOOD_GRAY, grad=(0.1, 0.9))
	p.box((2 * W * 0.8, 3.0, 0.12), (0, L1 - 1.6, D + 0.3), WOOD, grad=(0.1, 0.6))
	p.box((2 * W * 0.7, 0.14, 1.3), (0, L1 - 3.1, D + 0.95), WOOD_GRAY, grad=(0.2, 0.9))
	for x in (-0.8, 0.8):
		p.box((0.4, 0.05, 0.35), (x, L1 - 3.18, D + 1.1), IRON, grad=(0.6, 1.0))
	p.box((2 * W * 0.8 + 0.1, 3.1, 0.1), (0, L1 - 1.6, D + 1.6), WOOD, grad=(0.1, 0.6))
	for k in range(5):  # deck beams across the waist, a few planks left on them
		y = -2.0 + k * 1.5
		p.box((2 * W * 0.85, 0.2, 0.2), (0, y, D - 0.2), WOOD, grad=(0.2, 0.9))
		if k in (1, 3):
			p.box((1.2, 1.4, 0.07), (-0.8 + k * 0.3, y + 0.75, D - 0.07), WOOD_GRAY, grad=(0.1, 0.6))
	p.box((0.35, L1 - L0, 0.35), (0, (L0 + L1) / 2, 0.05), WOOD, grad=(0.3, 1.0))  # keel
	# masts: the main snapped at 5 m, the fore a stump, a rag of sail on the yard
	p.seg((0, 0.6, 0.2), (0, 0.6, 5.8), 0.2, 0.17, WOOD, sides=8, grad=(0.2, 1.0))
	p.rock((0.4, 0.4, 0.35), (0, 0.6, 5.8), WOOD, jitter=0.06)
	p.seg((-1.6, 0.7, 4.9), (1.8, 0.5, 5.1), 0.08, 0.07, WOOD, sides=6)
	p.poly([(-1.5, 0.75, 4.85), (0.4, 0.75, 4.9), (0.9, 0.9, 3.3), (-0.2, 1.0, 2.8), (-1.1, 0.9, 3.6)], [(0, 1, 2, 3, 4)], CLOTH_WHITE, grad=(0.3, 1.0))
	p.seg((0, -2.9, 0.2), (0, -2.9, 3.6), 0.17, 0.15, WOOD, sides=8, grad=(0.2, 1.0))
	p.rock((0.34, 0.34, 0.3), (0, -2.9, 3.6), WOOD, jitter=0.06)
	for k in range(3):  # rigging trailing off the stump
		_rope(p, (0, 0.6, 5.2 - k * 0.2), (W * 0.9, 2.2 + k * 1.2, D + 0.1), 0.4, r=0.02)
	# roll it onto its side and settle it bow-down into the bed
	for k in (3, 5, 9, 11):  # barnacles along the hull's flank, above the bilge
		v = Vector(outer[k][2])
		_barnacles(p, tuple(v), 7, 0.5, normal=(1, 0, -0.3))
	_move_parts(p, start, Matrix.Translation((0, 0, -0.35)) @ Matrix.Rotation(math.radians(7), 4, "X") @ Matrix.Rotation(math.radians(24), 4, "Y"))
	# the bow that broke away, lying on its side off the port bow
	bstart = len(p.parts)
	bys = [-3.0 + k * 0.5 for k in range(7)]

	def bow_sec(y):
		t = (y + 3.0) / 3.0  # 0 at the point, 1 at the break
		w = W * 0.85 * max(0.05, t) ** 0.7
		return [(math.cos(math.pi * i / (nu - 1)) * w, y, D + 0.4 * (1 - t) - math.sin(math.pi * i / (nu - 1)) * D * (0.4 + 0.6 * t) * (0.55 + 0.45 * math.sin(math.pi * i / (nu - 1)))) for i in range(nu)]

	bg = [bow_sec(y) for y in bys]
	bi = [[(v[0] * 0.88, v[1], v[2] + 0.08) for v in bow_sec(y)] for y in bys]
	for grid, sw0, grad in ((bg, WOOD, (0.1, 0.9)), (bi, WOOD_GRAY, (0.4, 1.0))):
		for i in range(nu - 1):
			for k in range(len(bys) - 1):
				if k == len(bys) - 2 and i in (0, 1, 6, 7):
					continue
				sw = sw0 if grid is bi else (WOOD if i % 2 else WOOD_GRAY)
				p.poly([grid[k][i], grid[k + 1][i], grid[k + 1][i + 1], grid[k][i + 1]], [(0, 1, 2, 3)], sw, grad)
	p.seg((0, -3.0, D + 0.4), (0, -5.0, D + 1.4), 0.12, 0.05, WOOD, sides=6)  # the bowsprit
	_chain(p, bow_sec(-0.2), 0.08, 0.08, WOOD, sides=4)
	_move_parts(p, bstart, Matrix.Translation((-3.6, -2.4, -0.6)) @ Matrix.Rotation(math.radians(-70), 4, "Y") @ Matrix.Rotation(math.radians(25), 4, "Z"))
	# weed at the water line, barnacles on the hull, planks and a barrel adrift
	water = 2.0
	for k in range(4):
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(4.0, 6.0)
		p.box((p.rng.uniform(1.4, 2.4), 0.26, 0.07), (math.cos(a) * d, 1.5 + math.sin(a) * d, water - 0.02), WOOD_GRAY, rot=(0, 0, p.rng.uniform(0, 180)), grad=(0.1, 0.6))
	_coral_cluster(soft, (3.2, -1.0, 0.0), 1.3)
	_coral_cluster(soft, (-2.6, 6.6, 0.0), 1.1)
	return join_into(p.build(bevel=0.02), [soft.build()])


def coral_growth():
	"""A clump of coral for dressing the drowned ruins, about 1.8 m across and
	1.3 m tall: branching stems in pink, orange and red, a sea fan, tube
	sponges, a brain coral and barnacles on a lump of stone. Origin on the bed
	(or on a ledge). No collision."""
	p = Prop("coral_growth", 319)
	p.rock((1.6, 1.3, 0.55), (0, 0, 0.05), STONE_DARK, jitter=0.07)
	p.rock((0.8, 0.7, 0.4), (0.7, 0.4, 0.05), STONE_DARK, jitter=0.06)
	for k, (x, y, sw) in enumerate(((-0.3, 0.1, CORAL_PINK), (0.25, -0.25, CORAL_ORANGE), (0.1, 0.35, CLOTH_RED), (-0.55, -0.35, CORAL_PINK))):
		a = p.rng.uniform(0, math.tau)
		_coral_branch(p, (x, y, 0.25), (math.cos(a) * 0.2, math.sin(a) * 0.2, 1.0), 0.32, 0.06, sw, 3)
	# a sea fan: a flat lattice plate
	fan = [(math.cos(math.radians(a)) * 0.55, 0.3 + math.sin(math.radians(a)) * 0.75) for a in range(0, 181, 20)] + [(0.0, 0.25)]
	fstart = len(p.parts)
	_plate(p, fan, 0.0, 0.03, PETAL_PURPLE, grad=(0.0, 0.8))
	for k in range(7):
		a = math.radians(15 + k * 25)
		p.seg((0, 0, 0.3), (math.cos(a) * 0.5, 0, 0.3 + math.sin(a) * 0.7), 0.025, 0.015, CORAL_MAGENTA, sides=4)
	_move_parts(p, fstart, Matrix.Translation((0.45, 0.35, 0.05)) @ Matrix.Rotation(math.radians(30), 4, "Z"))
	for k in range(4):  # tube sponges, dark in their mouths
		x, y = -0.6 + k * 0.13, 0.35 + (k % 2) * 0.15
		h = 0.35 + k * 0.08
		p.seg((x, y, 0.15), (x, y, 0.15 + h), 0.08, 0.1, CORAL_MAGENTA if k % 2 else PETAL_YELLOW, sides=7, grad=(0.0, 0.8))
		p.seg((x, y, 0.15 + h - 0.02), (x, y, 0.15 + h + 0.005), 0.075, 0.075, IRON, sides=7, grad=(0.6, 1.0))
	p.blob((0.55, 0.5, 0.38), (0.5, -0.45, 0.25), PETAL_YELLOW, segs=(10, 6), grad=(0.1, 0.8), jitter=0.02)  # brain coral
	for k in range(6):
		a = k * math.tau / 6
		p.seg((0.5 + math.cos(a) * 0.1, -0.45 + math.sin(a) * 0.1, 0.4), (0.5 + math.cos(a) * 0.22, -0.45 + math.sin(a) * 0.2, 0.45), 0.02, 0.02, CORAL_ORANGE, sides=3)
	for k in range(5):  # little anemones
		a = p.rng.uniform(0, math.tau)
		c = (math.cos(a) * 0.6, math.sin(a) * 0.45, 0.22)
		for j in range(5):
			b = j * math.tau / 5
			p.seg(c, (c[0] + math.cos(b) * 0.07, c[1] + math.sin(b) * 0.07, c[2] + 0.12), 0.02, 0.005, TEAL if k % 2 else CORAL_PINK, sides=3)
	_barnacles(p, (-0.2, -0.5, 0.2), 8, 0.25, normal=(0, -0.6, 1))
	return p.build(bevel=0.0)


def naga_shrine():
	"""A naga shrine: a carved pillar on a round two-step dais (3.6 m across),
	a stone serpent coiled up it, its hooded head reared over a lotus bowl that
	holds a great glowing blue pearl (about 5.5 m to the hood). Two offering
	bowls of glowing water on the dais. Faces -Y. Collide it as a box."""
	p = Prop("naga_shrine", 320)
	soft = Prop("naga_shrine_soft", 320)  # weed, slime, barnacles and coral: left unbeveled
	p.seg((0, 0, -0.2), (0, 0, 0.3), 1.8, 1.75, SEA_STONE, sides=16, grad=(0.2, 0.9))
	p.seg((0, 0, 0.3), (0, 0, 0.55), 1.3, 1.25, STONE_LIGHT, sides=16, grad=(0.1, 0.8))
	p.seg((0, 0, 0.55), (0, 0, 3.1), 0.4, 0.34, STONE_LIGHT, sides=8, grad=(0.05, 0.9), twist=22.5)
	for z in (0.7, 3.0):
		p.seg((0, 0, z - 0.08), (0, 0, z + 0.08), 0.5, 0.5, STONE_WARM, sides=8, twist=22.5)
	p.seg((0, 0, 3.1), (0, 0, 3.5), 0.36, 0.75, STONE_WARM, sides=12, grad=(0.0, 0.7))  # the lotus bowl
	for k in range(10):
		a = k * math.tau / 10
		p.blob((0.34, 0.12, 0.3), (math.cos(a) * 0.62, math.sin(a) * 0.62, 3.45), GOLD, rot=(0, 25, math.degrees(a)), segs=(6, 4), grad=(0.0, 0.6), glow=0.15)
	p.blob((0.8, 0.8, 0.8), (0, 0, 3.82), RUNE, segs=(14, 10), grad=(0.0, 0.4), glow=2.4)
	# the serpent: coils up the pillar, then the neck rises behind the pearl
	pts = []
	turns, z0, z1 = 2.4, 0.75, 2.95
	n = 40
	for k in range(n + 1):
		t = k / n
		a = -math.pi / 2 + t * turns * math.tau
		r = 0.52 - 0.05 * t
		pts.append((math.cos(a) * r, math.sin(a) * r, z0 + (z1 - z0) * t))
	tail = [(0.9, -1.0, 0.6), (0.45, -0.85, 0.62), (0.05, -0.62, 0.68)]
	body = tail + pts[1:]
	last = pts[-1]
	neck = [last, (last[0] * 1.2, last[1] * 1.2 + 0.2, 3.5), (0.0, 0.7, 4.1), (0.0, 0.6, 4.6), (0.0, 0.42, 4.95)]
	allp = body + neck[1:]
	m = len(allp) - 1
	for i, (a, b) in enumerate(zip(allp, allp[1:])):
		r0 = 0.06 + 0.12 * min(1.0, i / 6) - 0.02 * (i / m)
		r1 = 0.06 + 0.12 * min(1.0, (i + 1) / 6) - 0.02 * ((i + 1) / m)
		p.seg(a, b, r0, r1, SCALE_GREEN if (i // 3) % 2 else TEAL, sides=7, grad=(0.0, 0.8))
	hood_c = (0.0, 0.5, 4.95)
	p.blob((1.3, 0.24, 1.15), hood_c, SCALE_GREEN, rot=(-25, 0, 0), segs=(12, 6), grad=(0.0, 0.8))
	p.blob((0.85, 0.1, 0.8), (0.0, 0.37, 4.9), PETAL_YELLOW, rot=(-25, 0, 0), segs=(10, 5), grad=(0.0, 0.7))  # the hood's pale inside
	for k in range(3):  # its eye markings
		p.blob((0.12, 0.05, 0.12), ((k - 1) * 0.3, 0.33, 5.05 - abs(k - 1) * 0.1), TEAL, segs=(6, 4))
	p.blob((0.4, 0.6, 0.3), (0.0, 0.12, 5.02), TEAL, rot=(22, 0, 0), segs=(8, 6), grad=(0.0, 0.7))  # the head, bent over the pearl
	for s in (-1, 1):
		p.blob((0.07, 0.06, 0.06), (s * 0.14, -0.08, 5.02), EMBER, segs=(5, 4), glow=1.2)
	p.seg((0, -0.17, 4.9), (0, -0.33, 4.78), 0.012, 0.012, CLOTH_RED, sides=3)  # the tongue
	for s in (-1, 1):  # offering bowls of glowing water
		c = (s * 1.0, -0.75, 0.55)
		p.seg(c, (c[0], c[1], c[2] + 0.25), 0.16, 0.28, STONE_WARM, sides=10, grad=(0.0, 0.8))
		p.seg((c[0], c[1], c[2] + 0.18), (c[0], c[1], c[2] + 0.24), 0.24, 0.24, RUNE, sides=10, glow=1.2)
	for k in range(6):
		a = k * math.tau / 6 + 0.4
		p.blob((0.18, 0.08, 0.14), (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.33), (CLOTH_WHITE, SHELL_PEACH, CORAL_PINK)[k % 3], rot=(90, 0, math.degrees(a)), segs=(6, 4))
	_barnacles(soft, (1.3, 1.0, 0.1), 6, 0.25, normal=(1, 1, 0.3))
	_coral_cluster(soft, (-1.35, 0.9, 0.3), 0.8)
	return join_into(p.build(bevel=0.02), [soft.build()])


# ---------------------------------------------------------------- Dewstep (Dawnstair, levels 1-10)
# Lantern-lit tea gardens below Lanternhold: warm timber, clay tiles, paper
# lanterns in gold and rose; and the Dustpaw jackal-folk's ragged camps of
# hide and bamboo, sand and ochre.

OCHRE = FLAG_YELLOW     # orange-yellow: the Dustpaw's ochre paint and dyed hides


def _paper_lantern(p, x, y, z, swatch=GOLD, s=1.0):
	"""A round paper lantern hung from (x, y, z): a cord, a dark cap and foot,
	the glowing paper between. Returns the lantern's center."""
	p.seg((x, y, z), (x, y, z - 0.22 * s), 0.01, 0.01, WOOD_GRAY, sides=3)
	c = (x, y, z - 0.47 * s)
	p.seg((x, y, c[2] + 0.2 * s), (x, y, c[2] + 0.25 * s), 0.08 * s, 0.07 * s, IRON, sides=8, grad=(0.1, 0.6))
	p.blob((0.34 * s, 0.34 * s, 0.4 * s), c, swatch, segs=(10, 7), grad=(0.05, 0.45), glow=1.7)
	p.seg((x, y, c[2] - 0.25 * s), (x, y, c[2] - 0.2 * s), 0.07 * s, 0.08 * s, IRON, sides=8, grad=(0.1, 0.6))
	p.seg((x, y, c[2] - 0.25 * s), (x, y, c[2] - 0.4 * s), 0.012, 0.0, CLOTH_RED, sides=3)   # a red tassel
	return c


def _woven(p, r0, r1, z0, z1, bands, sides=12, swatches=(BAMBOO, HIDE), rim=None):
	"""A woven basket wall from radius r0 at z0 to r1 at z1, in alternating
	bands of the two weaves, a rim on top. Returns the top."""
	for k in range(bands):
		t0, t1 = k / bands, (k + 1) / bands
		p.seg((0, 0, z0 + (z1 - z0) * t0), (0, 0, z0 + (z1 - z0) * t1), r0 + (r1 - r0) * t0, r0 + (r1 - r0) * t1,
			  swatches[k % 2], sides=sides, grad=(0.1, 0.7) if k % 2 else (0.25, 0.9), twist=(k % 2) * 180 / sides)
	p.seg((0, 0, z1 - 0.01), (0, 0, z1 + 0.035), r1 + 0.02, r1 + 0.02, rim or WOOD, sides=sides, grad=(0.1, 0.6))


def tea_house():
	"""The tea-pickers' house: an open-sided timber pavilion 8 x 6 m on a stone
	plinth (0.45 m, steps up the front, -Y), a stone back wall with two windows
	(KayKit walls), knee rails on the sides, under a sweeping tiled roof with
	upturned eaves, about 5.6 m to the ridge finials. Three paper lanterns hang
	from the front beam; inside, a low tea table with cushions, a kettle on a
	brazier, tea chests and baskets. Collide it as a mesh (the front and sides
	are open)."""
	p = Prop("tea_house", 401)
	d = Prop("tea_house_detail", 402)            # small bits, no bevel
	P = 0.45                                     # plinth top
	hw, hd = 4.0, 3.0
	p.box((2 * hw + 0.6, 2 * hd + 0.6, 0.2), (0, 0, 0.1), STONE_DARK, grad=(0.3, 1.0))
	p.box((2 * hw + 0.3, 2 * hd + 0.3, P - 0.15), (0, 0, 0.2 + (P - 0.2) / 2 - 0.02), STONE_WARM, grad=(0.1, 0.9))
	p.box((2 * hw + 0.4, 2 * hd + 0.4, 0.1), (0, 0, P - 0.04), STONE_LIGHT, grad=(0.1, 0.6))     # coping
	for k, (y, z) in enumerate(((-hd - 0.38, 0.3), (-hd - 0.72, 0.15))):                        # steps up the front
		p.box((2.6 + k * 0.3, 0.36, z), (0, y, z / 2), STONE_LIGHT if k % 2 else STONE_WARM, grad=(0.1, 0.8))
	for s in (-1, 1):                                                                            # step cheeks with lotus knobs
		p.box((0.36, 0.72, 0.5), (s * 1.55, -hd - 0.45, 0.25), STONE_LIGHT, grad=(0.1, 0.8))
		p.blob((0.32, 0.32, 0.26), (s * 1.55, -hd - 0.45, 0.56), SHELL_PEACH, grad=(0.0, 0.6))
	for k in range(13):                                                                          # plank floor
		x = -hw + 0.1 + (k + 0.5) * (2 * hw - 0.2) / 13
		p.box(((2 * hw - 0.2) / 13 - 0.03, 2 * hd - 0.2, 0.06), (x, 0, P + 0.03), WOOD if k % 3 else WOOD_GRAY, grad=(0.25, 0.9))
	# --- timber frame: posts on stone drums, beams, brackets --------------------
	top = 2.85
	posts = [(x, -hd + 0.25) for x in (-hw + 0.25, -1.3, 1.3, hw - 0.25)]
	posts += [(x, hd - 0.25) for x in (-hw + 0.25, 0.0, hw - 0.25)]
	posts += [(s * (hw - 0.25), 0.0) for s in (-1, 1)]
	for x, y in posts:
		p.seg((x, y, P + 0.06), (x, y, P + 0.26), 0.2, 0.18, STONE_LIGHT, sides=8, grad=(0.1, 0.8))
		p.seg((x, y, P + 0.26), (x, y, top), 0.12, 0.11, WOOD, sides=8, grad=(0.15, 1.0))
		p.box((0.36, 0.36, 0.16), (x, y, top + 0.02), WOOD_GRAY, grad=(0.2, 0.9))
	for y in (-hd + 0.25, hd - 0.25):
		p.box((2 * hw + 0.3, 0.24, 0.26), (0, y, top + 0.2), CLOTH_RED, grad=(0.1, 0.8))
		p.box((2 * hw + 0.34, 0.27, 0.06), (0, y, top + 0.06), GOLD, grad=(0.1, 0.5))
	for x in (-hw + 0.25, hw - 0.25):
		p.box((0.24, 2 * hd + 0.3, 0.26), (x, 0, top + 0.2), CLOTH_RED, grad=(0.1, 0.8))
		p.box((0.27, 2 * hd + 0.34, 0.06), (x, 0, top + 0.06), GOLD, grad=(0.1, 0.5))
	for x in (-hw + 0.25, -1.3, 1.3, hw - 0.25):                                                 # carved brackets under the front beam
		for s in (-1, 1):
			if abs(x + s * 0.4) > hw:
				continue
			p.seg((x, -hd + 0.25, top - 0.45), (x + s * 0.45, -hd + 0.25, top + 0.06), 0.05, 0.05, WOOD, sides=5)
	# knee rails between the side posts (the front stays open)
	for s in (-1, 1):
		x = s * (hw - 0.25)
		for y0, y1 in ((-hd + 0.25, 0.0), (0.0, hd - 0.25)):
			p.box((0.1, y1 - y0, 0.1), (x, (y0 + y1) / 2, P + 0.75), WOOD, grad=(0.2, 0.9))
			p.box((0.08, y1 - y0, 0.08), (x, (y0 + y1) / 2, P + 0.3), WOOD_GRAY, grad=(0.2, 0.9))
			for k in range(1, 5):
				y = y0 + (y1 - y0) * k / 5
				p.box((0.05, 0.05, 0.45), (x, y, P + 0.52), BAMBOO, grad=(0.1, 0.8))
	# --- the roof ---------------------------------------------------------------
	z_eave = top + 0.34
	ridge_z = z_eave + 1.75
	_swept_roof(p, (hw + 0.95, hd + 0.9, z_eave), (2.3, 0.12, ridge_z), 0.62, bands=4, thick=0.22, swatch=CLAY)
	_ridge(p, 2.35, ridge_z, r=0.14, curl=0.55)
	p.seg((0, 0.05, ridge_z + 0.72), (0, -0.05, ridge_z + 0.72), 0.3, 0.3, GOLD, sides=14, glow=0.3)   # a small dawn sun on the ridge
	p.seg((0, 0, ridge_z + 0.1), (0, 0, ridge_z + 0.45), 0.07, 0.07, GOLD, sides=6)
	p.box((2 * hw + 1.2, 2 * hd + 1.0, 0.08), (0, 0, z_eave + 0.02), WOOD_GRAY, grad=(0.3, 0.9))       # the ceiling boards seen from under the eaves
	obj = p.build(bevel=0.05)
	# --- the sign, lanterns and things inside (no bevel) --------------------------
	d.box((1.5, 0.08, 0.5), (0, -hd + 0.1, top - 0.28), WOOD, grad=(0.2, 0.9))                      # the sign board under the beam
	d.box((1.62, 0.06, 0.6), (0, -hd + 0.14, top - 0.28), CLOTH_RED, grad=(0.1, 0.7))
	for k, x in enumerate((-0.45, -0.15, 0.15, 0.45)):                                            # gilt letters, a tea leaf in the middle
		d.box((0.12, 0.04, 0.28), (x, -hd + 0.05, top - 0.28), GOLD, rot=(0, (-1) ** k * 8, 0), grad=(0.0, 0.4))
	for k, x in enumerate((-2.65, 0.0, 2.65)):                                                   # the paper lanterns under the front eave
		_paper_lantern(d, x, -hd - 0.35, top + 0.2, GOLD if k != 1 else SHELL_PEACH, s=1.0)
		d.seg((x, -hd + 0.25, top + 0.2), (x, -hd - 0.35, top + 0.2), 0.02, 0.02, WOOD, sides=4)
	for x, y in ((-hw - 0.5, -hd - 0.5), (hw + 0.5, -hd - 0.5)):                                 # small lanterns at the roof's front corners
		_paper_lantern(d, x, y, z_eave + 0.35, SHELL_PEACH, s=0.7)
	# the tea table, cushions and a kettle
	tx, ty = -0.6, 0.2
	d.box((1.8, 1.0, 0.07), (tx, ty, P + 0.36), WOOD, grad=(0.1, 0.8))
	for sx in (-1, 1):
		for sy in (-1, 1):
			d.box((0.08, 0.08, 0.3), (tx + sx * 0.8, ty + sy * 0.4, P + 0.18), WOOD_GRAY, grad=(0.2, 0.9))
	for k, (x, y, sw) in enumerate(((tx - 1.25, ty, CLOTH_RED), (tx + 1.25, ty, CORAL_PINK), (tx - 0.45, ty - 0.85, SHELL_PEACH),
								   (tx + 0.45, ty - 0.85, CLOTH_RED), (tx, ty + 0.85, CORAL_PINK))):
		d.blob((0.6, 0.6, 0.14), (x, y, P + 0.08), sw, segs=(8, 4), grad=(0.1, 0.7))
	for k in range(5):                                                                            # cups round a pot
		a = k * math.tau / 5
		d.seg((tx + math.cos(a) * 0.35, ty + math.sin(a) * 0.25, P + 0.4), (tx + math.cos(a) * 0.35, ty + math.sin(a) * 0.25, P + 0.47), 0.04, 0.05, BONE, sides=6)
	d.blob((0.26, 0.26, 0.2), (tx, ty, P + 0.49), TEAL, segs=(8, 6), grad=(0.0, 0.6))
	d.seg((tx + 0.1, ty, P + 0.5), (tx + 0.22, ty, P + 0.57), 0.025, 0.015, TEAL, sides=4)
	# the brazier and kettle in the back corner
	bx, by = 2.6, 1.9
	d.seg((bx, by, P + 0.06), (bx, by, P + 0.45), 0.24, 0.3, CLAY, sides=10, grad=(0.1, 0.8))
	d.seg((bx, by, P + 0.45), (bx, by, P + 0.48), 0.27, 0.27, EMBER, sides=10, glow=0.9)
	d.blob((0.36, 0.36, 0.3), (bx, by, P + 0.62), IRON, segs=(10, 6), grad=(0.0, 0.7))
	d.seg((bx + 0.15, by, P + 0.64), (bx + 0.34, by, P + 0.76), 0.035, 0.02, IRON, sides=5)
	d.seg((bx - 0.14, by, P + 0.76), (bx + 0.14, by, P + 0.76), 0.012, 0.012, WOOD, sides=4)
	# tea chests and baskets against the back wall
	for k, (x, h) in enumerate(((-3.2, 0.5), (-2.6, 0.5), (-2.9, 0.42))):
		z = P + (h / 2 if k < 2 else 0.5 + h / 2)
		d.box((0.55, 0.5, h), (x, 2.35, z), WOOD if k % 2 else WOOD_GRAY, grad=(0.2, 0.9))
		d.box((0.3, 0.02, 0.18), (x, 2.09, z), CLOTH_RED if k != 1 else GOLD, grad=(0.1, 0.6))
	for k, x in enumerate((0.9, 1.45)):
		s = Prop("tea_house_basket_%d" % k, 403 + k)
		_woven(s, 0.2, 0.26, 0.0, 0.55, 5)
		s.blob((0.42, 0.42, 0.14), (0, 0, 0.56), LEAF, segs=(8, 4), grad=(0.1, 0.5), jitter=0.02)
		b = s.build()
		b.data.transform(Matrix.Translation((x, 2.3, P + 0.06)))
		d.parts.append(b)
	extra = d.build()
	# --- the back wall: KayKit stone, two windows, as in the houses --------------
	pieces = []
	for x in (-2.0, 2.0):
		pieces += kaykit("wall_window_open", (x, hd - 0.25 + 0.3, P), math.pi, (1.0, 0.6, 0.66))
	return _merge_materials(join_into(obj, [extra] + pieces))


def tea_drying_rack():
	"""Bamboo racks for drying tea: a frame 2.6 x 1.1 m and 1.9 m tall, lashed
	at the joints, holding three shelves of wide flat baskets heaped with
	leaves (green on top, withering brown below), a slanted reed sunshade on
	top. The long side faces -Y. Collide it as a box."""
	p = Prop("tea_drying_rack", 405)
	hx, hy = 1.3, 0.55
	for x in (-hx, 0.0, hx):
		for y in (-hy, hy):
			p.seg((x, y, 0.0), (x, y, 1.75 + (0.15 if y > 0 else 0.0)), 0.045, 0.04, BAMBOO, sides=6, grad=(0.1, 0.9))
			for z in (0.45, 1.0, 1.5):
				p.seg((x, y, z - 0.03), (x, y, z + 0.03), 0.055, 0.055, WOOD, sides=6)   # nodes
	levels = (0.35, 0.85, 1.35)
	for z in levels:
		for y in (-hy, hy):
			p.seg((-hx - 0.1, y, z), (hx + 0.1, y, z), 0.035, 0.035, BAMBOO, sides=6, grad=(0.1, 0.7))
		for x in (-hx, 0.0, hx):
			p.seg((x, -hy - 0.08, z - 0.02), (x, hy + 0.08, z - 0.02), 0.03, 0.03, BAMBOO, sides=6, grad=(0.1, 0.7))
			for y in (-hy, hy):
				p.blob((0.1, 0.1, 0.08), (x, y, z), HIDE, segs=(6, 4))                    # lashings
	for s in (-1, 1):                                                                    # cross braces at the ends
		p.seg((s * hx, -hy, 0.1), (s * hx, hy, 1.6), 0.025, 0.025, BAMBOO, sides=5)
	obj = p.build()
	d = Prop("tea_drying_rack_leaves", 406)
	for li, z in enumerate(levels):
		for x in (-0.65, 0.65):
			r = 0.56
			d.seg((x, 0, z + 0.03), (x, 0, z + 0.1), r, r + 0.04, BAMBOO, sides=14, grad=(0.05, 0.6) if li % 2 else (0.3, 0.9))
			d.seg((x, 0, z + 0.095), (x, 0, z + 0.125), r + 0.06, r + 0.06, WOOD, sides=14, grad=(0.1, 0.6))    # the rim
			leaves = ((PINE, MOSS), (PINE, LEAF), (LEAF, LEAF))[li]   # top baskets fresh, lower ones darkening as they dry
			for k in range(10):
				a = k * math.tau / 10 + d.rng.uniform(-0.3, 0.3)
				rr = d.rng.uniform(0.05, 0.4)
				d.blob((0.36, 0.3, 0.07), (x + math.cos(a) * rr, math.sin(a) * rr, z + 0.13), leaves[k % 2], rot=(0, 0, d.rng.uniform(0, 180)),
					   segs=(7, 3), grad=(0.1, 0.6), jitter=0.01)
	# the sunshade: a slanted reed mat on top
	for k in range(14):
		x = -hx - 0.2 + (k + 0.5) * (2 * hx + 0.4) / 14
		d.seg((x, -hy - 0.3, 1.72), (x, hy + 0.3, 1.95), 0.05, 0.05, BAMBOO if k % 2 else HIDE, sides=4, grad=(0.1, 0.7))
	d.seg((-hx - 0.2, -hy - 0.1, 1.76), (hx + 0.2, -hy - 0.1, 1.76), 0.03, 0.03, HIDE, sides=4)
	d.seg((-hx - 0.2, hy + 0.1, 1.9), (hx + 0.2, hy + 0.1, 1.9), 0.03, 0.03, HIDE, sides=4)
	return join_into(obj, [d.build()])


def picker_basket():
	"""A tea-picker's tall woven back basket, about 0.8 m: narrow at the foot,
	flaring to the mouth, bands of weave, two shoulder straps, a heap of fresh
	leaves on top. Small clutter; collide: none."""
	p = Prop("picker_basket", 407)
	p.seg((0, 0, 0.0), (0, 0, 0.05), 0.15, 0.17, WOOD, sides=10, grad=(0.2, 0.9))
	_woven(p, 0.17, 0.27, 0.04, 0.72, 6, sides=10)
	for k in range(4):                                             # ribs
		a = k * math.tau / 4 + math.pi / 4
		p.seg((math.cos(a) * 0.17, math.sin(a) * 0.17, 0.02), (math.cos(a) * 0.28, math.sin(a) * 0.28, 0.74), 0.018, 0.018, WOOD, sides=4)
	for s in (-1, 1):                                              # the straps, on the back (+Y)
		p.seg((s * 0.11, 0.24, 0.66), (s * 0.13, 0.32, 0.45), 0.02, 0.02, HIDE, sides=4)
		p.seg((s * 0.13, 0.32, 0.45), (s * 0.12, 0.22, 0.2), 0.02, 0.02, HIDE, sides=4)
	for k in range(6):                                             # the leaves
		a = k * math.tau / 6 + 0.3
		r = 0.08 if k % 2 else 0.14
		p.blob((0.2, 0.15, 0.1), (math.cos(a) * r, math.sin(a) * r, 0.78 + (0.04 if k % 2 else 0)), LEAF, rot=(0, 0, math.degrees(a)), segs=(6, 3), grad=(0.1, 0.5))
	return p.build()


def shrine_broken():
	"""A roadside shrine of the Dawn-Tusk fallen to ruin, facing -Y, about 5.4 x
	4.6 m: a two-step stone plinth cracked across, its right half sunk and
	tilted; the carved back stone (a sun in a niche) snapped, its top lying
	behind; the right pillar standing broken under a creeper, the left one
	fallen forward in drums; the shrine's elephant toppled off the front onto
	its side; offering bowls tipped and scattered, moss and weeds in the
	cracks. Collide it as a mesh."""
	p = Prop("shrine_broken", 408)
	for k, (w, dp, z0, h) in enumerate(((3.4, 2.6, 0.0, 0.3), (2.7, 2.0, 0.3, 0.28))):
		sw = STONE_WARM if k == 0 else STONE_LIGHT
		p.box((w / 2 - 0.05, dp, h), (-w / 4, 0, z0 + h / 2), sw, grad=(0.1, 0.9))
		p.box((w / 2 - 0.05, dp, h), (w / 4 + 0.06, 0.02, z0 + h / 2 - 0.08), sw, rot=(3, -5, 4), grad=(0.1, 0.9))
	p.box((1.2, 0.34, 0.16), (-0.3, -1.45, 0.08), STONE_LIGHT, grad=(0.1, 0.8))                # the step, split
	p.box((0.9, 0.34, 0.14), (0.75, -1.5, 0.05), STONE_WARM, rot=(0, 3, 12), grad=(0.1, 0.8))
	# the back stone: a carved stele, a niche with a sun in it, its top snapped off
	p.box((1.9, 0.5, 1.25), (-0.2, 0.7, 0.58 + 0.62), STONE_WARM, grad=(0.05, 0.9))
	p.box((2.05, 0.6, 0.18), (-0.2, 0.7, 0.67), STONE_LIGHT, grad=(0.1, 0.7))
	p.box((1.1, 0.12, 0.85), (-0.2, 0.43, 1.25), STONE_DARK, grad=(0.3, 1.0))                 # the niche
	p.seg((-0.2, 0.4, 1.3), (-0.2, 0.36, 1.3), 0.34, 0.34, GOLD, sides=14, grad=(0.35, 1.0))     # the sun, tarnished
	for j in range(8):
		a = j * math.tau / 8
		if j in (1, 2):
			continue                                                                      # rays broken off
		p.seg((-0.2 + math.cos(a) * 0.34, 0.38, 1.3 + math.sin(a) * 0.34), (-0.2 + math.cos(a) * 0.46, 0.38, 1.3 + math.sin(a) * 0.46), 0.05, 0.0, GOLD, sides=4, grad=(0.35, 1.0))
	for k in range(4):                                                                        # the broken top edge
		p.rock((0.55, 0.5, 0.3), (-0.9 + k * 0.46, 0.7, 1.82 + (0.15 if k == 1 else 0) - k * 0.06), STONE_WARM, jitter=0.05)
	p.box((1.9, 0.5, 1.0), (0.2, 1.95, 0.25), STONE_WARM, rot=(80, 0, 12), grad=(0.05, 0.9))      # the top, fallen behind
	p.seg((0.2, 1.6, 0.65), (0.2, 1.6, 0.8), 0.5, 0.0, STONE_WARM, sides=4, twist=45)            # its little roof
	# the right pillar, snapped
	p.seg((1.15, -0.7, 0.5), (1.15, -0.7, 0.66), 0.25, 0.25, STONE_WARM, sides=8)
	p.seg((1.15, -0.7, 0.66), (1.15, -0.7, 1.75), 0.18, 0.17, STONE_LIGHT, sides=8, grad=(0.1, 0.9), twist=22.5)
	p.rock((0.36, 0.36, 0.26), (1.15, -0.7, 1.8), STONE_LIGHT, jitter=0.06)
	# the left pillar, fallen forward in drums, its capital beyond
	p.seg((-1.2, -0.7, 0.58), (-1.2, -0.7, 0.8), 0.25, 0.25, STONE_WARM, sides=8)
	p.rock((0.34, 0.34, 0.2), (-1.2, -0.7, 0.84), STONE_LIGHT, jitter=0.05)
	p.seg((-1.45, -1.25, 0.2), (-1.85, -1.95, 0.18), 0.18, 0.17, STONE_LIGHT, sides=8, grad=(0.1, 0.9), twist=10)
	p.seg((-1.95, -2.15, 0.18), (-2.35, -2.7, 0.2), 0.17, 0.16, STONE_LIGHT, sides=8, grad=(0.1, 0.9), twist=40)
	p.box((0.5, 0.5, 0.2), (-2.6, -3.05, 0.1), STONE_WARM, rot=(0, 0, 38), grad=(0.1, 0.8))
	for k in range(6):                                                                        # rubble
		p.rock((p.rng.uniform(0.2, 0.4), p.rng.uniform(0.18, 0.34), 0.18), (p.rng.uniform(-2.2, 2.2), p.rng.uniform(-2.4, -1.4), 0.06), STONE_WARM if k % 2 else STONE_LIGHT)
	obj = p.build(bevel=0.04)
	# the elephant: built standing (about 1.1 m long, its own plinth broken
	# away), scaled up, laid on its side where it fell off the front
	e = Prop("shrine_broken_elephant", 409)
	e.blob((0.62, 0.95, 0.6), (0, 0.05, 0.62), STONE_LIGHT, segs=(10, 7), grad=(0.05, 0.8))
	for x in (-0.2, 0.2):
		for y in (-0.28, 0.35):
			e.seg((x, y, 0.18), (x, y, 0.5), 0.11, 0.12, STONE_LIGHT, sides=6, grad=(0.2, 0.9))
	_elephant_head(e, (0, -0.48, 0.86), 0.36, swatch=STONE_LIGHT, tusks=(True, False))
	e.box((0.5, 0.4, 0.05), (0, 0.05, 0.93), SHELL_PEACH, grad=(0.1, 0.6))                    # its painted saddle cloth, faded
	e.blob((0.16, 0.16, 0.16), (0, 0.05, 0.97), GOLD, grad=(0.0, 0.6))
	el = e.build(bevel=0.02)
	el.data.transform(Matrix.Translation((1.75, -2.35, 0.55)) @ Matrix.Rotation(math.radians(-35), 4, "Z") @ Matrix.Rotation(math.radians(-80), 4, "Y")
					  @ Matrix.Scale(1.45, 4) @ Matrix.Translation((0, 0, -0.45)))
	# offerings, moss, weeds, a creeper (no bevel)
	d = Prop("shrine_broken_detail", 410)
	for k, (x, y, z, tilt) in enumerate(((-0.6, -0.4, 0.6, 0), (0.45, -1.0, 0.1, 70), (-0.9, -1.9, 0.05, 85), (0.35, 0.2, 0.52, 20), (0.0, -2.5, 0.02, 90), (-0.2, 0.2, 0.6, 0))):
		sw = (GOLD, CLAY, CLAY, GOLD, CLAY, CLAY)[k]
		r = 0.15 if k % 2 else 0.19
		bowl = [(0.001, 0.0), (r * 0.55, 0.0), (r, r * 0.55), (r * 0.85, r * 0.55), (0.001, r * 0.12)]
		b0 = len(d.parts)
		_lathe(d, bowl, 10, sw, grad=(0.1, 0.7))
		_move_parts(d, b0, Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(k * 67), 4, "Z") @ Matrix.Rotation(math.radians(tilt), 4, "X"))
	for x, y in ((-0.55, -0.3), (-0.72, -0.5), (0.35, -1.2)):                                   # spilled marigolds, long dried
		d.blob((0.14, 0.14, 0.06), (x, y, 0.6 if y > -1 else 0.08), FLAG_YELLOW, segs=(6, 3))
	for x, y, z, sx, sy in ((-0.9, 0.0, 0.6, 0.9, 0.7), (0.9, -0.2, 0.5, 0.7, 0.8), (-0.3, 0.7, 1.92, 0.9, 0.4), (0.5, 1.95, 0.52, 0.9, 0.6), (-1.9, -2.0, 0.34, 0.5, 0.4)):
		_moss_patch(d, x, y, z, sx, sy)
	for k in range(10):                                                                       # weeds in the cracks and round the foot
		x, y = [(0.02, -0.3), (-1.75, 0.6), (1.8, 0.9), (-1.6, -1.2), (0.05, 0.9), (1.8, -1.3), (-0.9, 1.4), (2.3, -2.1), (-2.4, -0.4), (0.9, 1.2)][k]
		z = 0.58 if k in (0, 4) else 0.0
		for j in range(5):
			a = j * math.tau / 5 + d.rng.uniform(-0.3, 0.3)
			h = d.rng.uniform(0.25, 0.55)
			d.seg((x, y, z), (x + math.cos(a) * 0.18, y + math.sin(a) * 0.18, z + h), 0.04, 0.0, LEAF if j % 2 else MOSS, sides=3, grad=(0.1, 0.8))
	pts = [(1.15 + math.cos(t * 7) * 0.2, -0.7 + math.sin(t * 7) * 0.2, 1.85 - t * 1.85) for t in (i / 8 for i in range(9))]
	_chain(d, pts, 0.03, 0.025, LEAF, sides=4, grad=(0.3, 1.0))                               # a creeper up the standing pillar
	for q in pts[1::2]:
		d.blob((0.22, 0.09, 0.15), (q[0] + 0.08, q[1] - 0.05, q[2]), LEAF, rot=(0, 0, d.rng.uniform(0, 360)), segs=(5, 3))
	for k in range(3):
		_vine(d, (-0.9 + k * 0.5, 0.95, 1.85), d.rng.uniform(0.5, 1.1), d.rng, r=0.025)           # hanging off the back stone
	return join_into(obj, [el, d.build()])


def dustpaw_hut():
	"""A Dustpaw lean-to: a bamboo frame 3.6 m wide and 3 m deep, high at the
	open front (-Y, 2.5 m) and sloping to the ground behind, roofed with
	ragged patched hides in sand and ochre, a hide flap on each side, a sand
	bank round the back, a skull over the door, bedding and a pot inside.
	Collide it as a box."""
	p = Prop("dustpaw_hut", 411)
	hw, hd = 1.8, 1.5
	zf, zb = 2.45, 0.35
	for x in (-hw, 0.0, hw):
		p.seg((x, -hd, -0.1), (x + p.rng.uniform(-0.06, 0.06), -hd, zf + 0.25), 0.07, 0.055, BAMBOO, sides=6, grad=(0.1, 0.9))
		p.seg((x, hd, -0.1), (x, hd, zb + 0.1), 0.06, 0.05, BAMBOO, sides=6)
		p.seg((x, -hd - 0.15, zf + 0.1), (x, hd + 0.25, zb - 0.05), 0.045, 0.04, WOOD_GRAY, sides=5)   # rafters
	p.seg((-hw - 0.3, -hd, zf), (hw + 0.35, -hd, zf + 0.05), 0.06, 0.06, BAMBOO, sides=6)          # front beam, lashed
	for x in (-hw, 0.0, hw):
		p.blob((0.16, 0.16, 0.14), (x, -hd, zf), HIDE, segs=(6, 4))
		for z in (0.3, 0.85):                                                              # ochre-banded posts
			p.seg((x, -hd, z * zf), (x, -hd, z * zf + 0.12), 0.075, 0.075, OCHRE, sides=6)
	# the hides: overlapping courses, each patch a little skewed, some edges torn
	cols = (HIDE, OCHRE, HIDE, WOOD_GRAY, HIDE, CORAL_ORANGE)
	for row in range(4):
		t0, t1 = row / 4, (row + 1) / 4 + 0.06
		for c in range(3):
			x0 = -hw - 0.2 + c * (2 * hw + 0.4) / 3 + p.rng.uniform(-0.1, 0.05)
			x1 = x0 + (2 * hw + 0.4) / 3 + p.rng.uniform(0.05, 0.2)
			y0, y1 = -hd - 0.2 + t0 * (2 * hd + 0.4), -hd - 0.2 + t1 * (2 * hd + 0.4)
			z0, z1 = zf + 0.14 - t0 * (zf - zb), zf + 0.14 - t1 * (zf - zb)
			lift = row * 0.012 + c * 0.004
			v = [(x0, y0, z0 + lift + 0.05), (x1, y0 + p.rng.uniform(-0.1, 0.1), z0 + lift + 0.05), (x1, y1, z1 + lift + 0.05), (x0, y1, z1 + lift + 0.05)]
			v += [(x, y, z - 0.04) for x, y, z in v]
			p.poly(v, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
				   cols[(row * 3 + c * 2) % len(cols)], grad=(0.15, 0.9))
	for k in range(9):                                                                     # torn strips off the front edge
		x = -hw - 0.1 + k * (2 * hw + 0.2) / 8 + p.rng.uniform(-0.08, 0.08)
		L = p.rng.uniform(0.2, 0.6)
		p.box((p.rng.uniform(0.08, 0.16), 0.03, L), (x, -hd - 0.24, zf + 0.12 - L / 2), (HIDE, OCHRE, WOOD_GRAY)[k % 3], rot=(p.rng.uniform(-8, 8), 0, p.rng.uniform(-10, 10)), grad=(0.1, 0.8))
	for s in (-1, 1):                                                                      # side flaps, ragged, tied off
		x = s * (hw + 0.05)
		p.poly([(x, -hd + 0.15, zf - 0.05), (x, hd - 0.1, zb + 0.05), (x, hd - 0.1, 0.0), (x, -hd + 0.6, 0.0), (x, -hd + 0.2, 0.6)],
			   [(0, 1, 2, 3, 4)], HIDE if s < 0 else OCHRE, grad=(0.2, 0.9))
		p.poly([(x - s * 0.03, -hd + 0.15, zf - 0.05), (x - s * 0.03, hd - 0.1, zb + 0.05), (x - s * 0.03, hd - 0.1, 0.0), (x - s * 0.03, -hd + 0.6, 0.0), (x - s * 0.03, -hd + 0.2, 0.6)],
			   [(0, 4, 3, 2, 1)], HIDE, grad=(0.6, 1.0))
	for k in range(10):                                                                    # the sand bank round the back and sides
		a = math.pi * 0.1 + k * math.pi * 0.8 / 9
		p.blob((1.2, 0.8, 0.5), (math.cos(a) * hw * 1.1, math.sin(a) * hd * 0.9 + 0.3, 0.05), HIDE, rot=(0, 0, math.degrees(a)), segs=(8, 5), grad=(0.1, 0.8))
	obj = p.build(bevel=0.02)
	d = Prop("dustpaw_hut_detail", 412)
	_skull(d, (0.0, -hd - 0.1, zf + 0.12), s=1.4)                                           # a skull over the door
	for s in (-1, 1):
		for k in range(4):                                                                 # bead strings hanging by the door
			d.blob((0.06, 0.06, 0.06), (s * 0.55, -hd - 0.12, zf - 0.15 - k * 0.1), (TEAL, CORAL_ORANGE, BONE, CLOTH_RED)[k], segs=(5, 3))
		d.seg((s * 0.55, -hd - 0.12, zf), (s * 0.55, -hd - 0.12, zf - 0.45), 0.008, 0.008, HIDE, sides=3)
	for k in range(3):                                                                     # a feather
		d.box((0.05, 0.02, 0.3), (0.5 + k * 0.06, -hd - 0.14, zf - 0.25), (CLOTH_WHITE, OCHRE, CLOTH_RED)[k], rot=(0, 15 - k * 12, 0), grad=(0.0, 0.6))
	# inside: a bed of hides, a clay pot, a bundle of spears
	d.blob((1.3, 1.0, 0.18), (-0.8, 0.5, 0.05), HIDE, segs=(8, 4), grad=(0.1, 0.8))
	d.blob((1.0, 0.8, 0.14), (-0.7, 0.55, 0.15), OCHRE, segs=(8, 4), grad=(0.1, 0.8))
	d.seg((0.9, 0.3, 0.0), (0.9, 0.3, 0.35), 0.2, 0.25, CLAY, sides=10, grad=(0.1, 0.8))
	d.seg((0.9, 0.3, 0.35), (0.9, 0.3, 0.45), 0.25, 0.14, CLAY, sides=10)
	d.seg((0.9, 0.3, 0.45), (0.9, 0.3, 0.5), 0.15, 0.15, CLAY, sides=10)
	for k in range(3):
		d.seg((1.4 + k * 0.08, -0.4, 0.0), (1.2 + k * 0.12, -1.35, 2.0), 0.025, 0.02, WOOD, sides=4)
		d.seg((1.2 + k * 0.12, -1.35, 2.0), (1.18 + k * 0.12, -1.42, 2.22), 0.04, 0.0, IRON, sides=4)
	return join_into(obj, [d.build()])


def dustpaw_totem():
	"""A Dustpaw totem: a crooked pole about 3 m tall on a cairn, a jackal's
	skull on top (long narrow muzzle, hide ears stitched on), ochre bands,
	a crossbar hung with feathers and strings of clay and bone beads.
	Faces -Y. Collide it as a box (or not at all)."""
	p = Prop("dustpaw_totem", 413)
	for k in range(6):
		a = k * math.tau / 6
		p.rock((0.45, 0.4, 0.3), (math.cos(a) * 0.38, math.sin(a) * 0.38, 0.08), STONE_WARM, jitter=0.05)
	p.rock((0.4, 0.4, 0.3), (0.05, 0.1, 0.3), HIDE, jitter=0.04)
	_chain(p, [(0, 0, -0.1), (0.05, 0.02, 1.2), (-0.02, 0.0, 2.2), (0.04, 0.0, 2.75)], 0.1, 0.07, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
	for z in (0.9, 1.35, 1.95):
		p.seg((0.02, 0.01, z), (0.02, 0.01, z + 0.1), 0.105, 0.1, OCHRE if z != 1.35 else CLOTH_RED, sides=6)
	p.seg((-0.7, 0.0, 2.2), (0.72, 0.0, 2.25), 0.04, 0.04, WOOD, sides=5)                         # crossbar
	p.blob((0.12, 0.12, 0.12), (0.0, 0.0, 2.22), HIDE, segs=(6, 4))
	obj = p.build(bevel=0.015)
	d = Prop("dustpaw_totem_detail", 414)
	# the jackal skull: a narrow cranium and a long tapering muzzle, looking -Y
	c = Vector((0.04, 0.0, 2.9))
	d.blob((0.28, 0.34, 0.26), c, BONE, segs=(8, 6), grad=(0.0, 0.6))
	d.seg(tuple(c + Vector((0, -0.1, 0.0))), tuple(c + Vector((0, -0.52, -0.08))), 0.1, 0.045, BONE, sides=6, grad=(0.0, 0.6))
	d.seg(tuple(c + Vector((0, -0.12, -0.1))), tuple(c + Vector((0, -0.5, -0.14))), 0.05, 0.03, BONE, sides=5, grad=(0.1, 0.7))   # the jaw
	for s in (-1, 1):
		d.blob((0.07, 0.05, 0.06), tuple(c + Vector((s * 0.09, -0.15, 0.04))), IRON, segs=(5, 3))       # eye sockets
		d.seg(tuple(c + Vector((s * 0.05, -0.47, -0.1))), tuple(c + Vector((s * 0.055, -0.48, -0.16))), 0.012, 0.0, BONE, sides=3)  # fangs
		d.poly([tuple(c + Vector((s * 0.07, 0.02, 0.1))), tuple(c + Vector((s * 0.17, 0.05, 0.08))), tuple(c + Vector((s * 0.18, 0.02, 0.42)))],
			   [(0, 1, 2)], OCHRE, grad=(0.1, 0.8))                                                   # hide ears, big and pointed
		d.poly([tuple(c + Vector((s * 0.07, 0.035, 0.1))), tuple(c + Vector((s * 0.17, 0.065, 0.08))), tuple(c + Vector((s * 0.18, 0.035, 0.42)))],
			   [(0, 2, 1)], HIDE, grad=(0.1, 0.8))
	d.box((0.04, 0.3, 0.02), tuple(c + Vector((0, -0.25, 0.08))), CLOTH_RED, rot=(10, 0, 0))            # a red stripe down the muzzle
	# feathers and bead strings off the crossbar
	for k, x in enumerate((-0.62, -0.38, -0.14, 0.2, 0.44, 0.66)):
		L = 0.35 + (k % 3) * 0.12
		d.seg((x, 0.0, 2.2), (x, 0.0, 2.2 - L), 0.008, 0.008, HIDE, sides=3)
		if k % 2:
			for j in range(int(L / 0.08)):
				d.blob((0.055, 0.055, 0.05), (x, 0.0, 2.15 - j * 0.08), (TEAL, CORAL_ORANGE, BONE, CLOTH_RED, OCHRE)[(j + k) % 5], segs=(5, 3))
		else:
			for j in range(2):
				d.box((0.06, 0.015, 0.3), (x + j * 0.05 - 0.02, 0.0, 2.2 - L - 0.12), (CLOTH_WHITE, OCHRE, CLOTH_RED, WOOD_GRAY)[(k + j) % 4], rot=(0, (-1) ** j * 14, 0), grad=(0.0, 0.7))
	for k in range(3):                                                                            # feathers tucked behind the skull
		d.box((0.06, 0.02, 0.4), (0.04 + (k - 1) * 0.1, 0.18, 3.1), (CLOTH_WHITE, OCHRE, CLOTH_RED)[k], rot=(-20, (k - 1) * 25, 0), grad=(0.0, 0.6))
	_bone(d, (-0.3, -0.12, 1.55), (0.3, -0.12, 1.45), r=0.025)                                    # a bone lashed across the pole
	d.blob((0.1, 0.1, 0.1), (0.02, -0.1, 1.5), HIDE, segs=(5, 3))
	return join_into(obj, [d.build()])


def dustpaw_fire():
	"""The Dustpaw's fire pit: a ring of stones laid with bones and two small
	skulls, a heap of logs and embers, flames, and a spit on forked sticks with
	a roasting haunch. About 2.4 m across. Collide: none."""
	p = Prop("dustpaw_fire", 415)
	for k in range(10):
		a = k * math.tau / 10
		p.rock((0.38, 0.32, 0.26), (math.cos(a) * 0.9, math.sin(a) * 0.9, 0.08), STONE_WARM if k % 2 else STONE_DARK, rot=(0, 0, math.degrees(a)), jitter=0.05)
	p.blob((2.1, 2.1, 0.12), (0, 0, 0.0), HIDE, segs=(12, 4), grad=(0.3, 1.0))                   # trampled sand
	p.blob((1.2, 1.2, 0.1), (0, 0, 0.04), CHAR, segs=(10, 4), grad=(0.3, 1.0))
	for k in range(5):
		a = k * math.tau / 5 + 0.2
		p.seg((math.cos(a) * 0.62, math.sin(a) * 0.62, 0.06), (math.cos(a) * 0.08, math.sin(a) * 0.08, 0.45), 0.08, 0.06, WOOD_GRAY if k % 2 else WOOD, sides=5, grad=(0.4, 1.0))
	p.blob((0.9, 0.9, 0.12), (0, 0, 0.08), EMBER, grad=(0.5, 0.9), glow=0.9)
	for loc, r, h in (((0, 0, 0.1), 0.34, 1.0), ((0.18, 0.1, 0.1), 0.22, 0.72), ((-0.17, -0.08, 0.1), 0.2, 0.68), ((0.04, -0.2, 0.1), 0.16, 0.5)):
		p.seg(loc, (loc[0], loc[1], loc[2] + h), r, 0.0, FLAME, sides=6, grad=(0.1, 0.95), glow=1.2, twist=p.rng.uniform(0, 60))
	# the spit
	for s in (-1, 1):
		x = s * 1.05
		p.seg((x, 0, 0.0), (x, 0, 0.85), 0.035, 0.03, WOOD, sides=5)
		p.seg((x, 0, 0.8), (x - s * 0.1, 0.08, 1.0), 0.025, 0.02, WOOD, sides=4)
		p.seg((x, 0, 0.8), (x + s * 0.05, -0.08, 1.0), 0.025, 0.02, WOOD, sides=4)
	p.seg((-1.25, 0, 0.9), (1.2, 0, 0.9), 0.025, 0.025, WOOD_GRAY, sides=5)
	p.blob((0.55, 0.3, 0.28), (0.1, 0, 0.88), CLAY, segs=(8, 6), grad=(0.1, 0.9))                 # the haunch
	p.seg((0.36, 0, 0.88), (0.5, 0, 0.9), 0.05, 0.04, BONE, sides=5)
	obj = p.build(bevel=0.0)
	d = Prop("dustpaw_fire_bones", 416)
	for k in range(10):                                                                           # bones laid between the stones
		a = (k + 0.5) * math.tau / 10
		if k in (2, 7):
			_skull(d, (math.cos(a) * 0.95, math.sin(a) * 0.95, 0.12), s=1.1, yaw=a + math.pi / 2)
			continue
		t = Vector((-math.sin(a), math.cos(a), 0)) * 0.15
		cpt = Vector((math.cos(a) * 0.95, math.sin(a) * 0.95, 0.1))
		_bone(d, tuple(cpt - t), tuple(cpt + t + Vector((0, 0, 0.03))), r=0.022)
	_bone(d, (1.3, -0.6, 0.03), (1.6, -0.25, 0.05), r=0.028)                                     # gnawed and tossed aside
	_bone(d, (-1.4, 0.7, 0.03), (-1.2, 1.05, 0.04), r=0.024)
	return join_into(obj, [d.build()])


# ---------------------------------------------------------------- The Burn, Blackglass and Forgehold (the Ashfall)

BASALT = {(1, 0): STONE_DARK, (0, 0): IRON}   # KayKit's pale wall stone -> black basalt, its trim -> near black


def _restone(meshes, remap):
	"""Repaint imported KayKit pieces: UVs in one swatch move to another
	(pale wall stone to basalt), keeping their place in the gradient."""
	for o in meshes:
		for l in o.data.uv_layers.active.data:
			col, row = min(int(l.uv[0] * 8), 7), min(int((1.0 - l.uv[1]) * 4), 3)
			if (col, row) in remap:
				nc, nr = remap[(col, row)]
				l.uv[0] += (nc - col) / 8.0
				l.uv[1] -= (nr - row) / 4.0
	return meshes


def _translucent(obj, alpha, roughness=0.1):
	"""See-through copies of a built prop's materials (glTF exports alpha BLEND)."""
	for i, m in enumerate(obj.data.materials):
		g = m.copy()
		g.name = m.name + "_clear"
		b = g.node_tree.nodes["Principled BSDF"]
		b.inputs["Roughness"].default_value = roughness
		b.inputs["Alpha"].default_value = alpha
		if hasattr(g, "surface_render_method"):
			g.surface_render_method = "BLENDED"
		obj.data.materials[i] = g
	return obj


def _smoke(name, seed, base, height, r=0.18, alpha=0.4):
	"""A wisp of smoke rising from `base`: soft grey puffs drifting and
	widening as they climb. Built see-through, ready to join."""
	s = Prop(name, seed)
	x, y, z = base
	n = max(5, int(height / (r * 1.3)))
	for k in range(n):
		t = k / (n - 1)
		x += s.rng.uniform(-0.06, 0.1)
		y += s.rng.uniform(-0.06, 0.06)
		rr = r * (0.7 + 1.6 * t) * (1.0 - 0.45 * t * t)
		s.blob((rr * 2, rr * 2, rr * 1.6), (x, y, z + height * t), SHADE, segs=(7, 5), grad=(0.25, 0.45), jitter=rr * 0.12)
	return _translucent(s.build(), alpha, 0.9)


def _block(p, size, loc, swatch, yaw=0.0, rough=0.08, grad=(0.1, 0.9)):
	"""A rough-hewn stone block: a box with its corners knocked about."""
	return p.box(size, loc, swatch, rot=(p.rng.uniform(-2, 2), p.rng.uniform(-2, 2), yaw), grad=grad, jitter=rough * min(size))


def _beam(p, a, b, t, swatch=CHAR, grad=(0.1, 0.8)):
	"""A squared timber from a to b, `t` its half-width."""
	return p.seg(a, b, t * 1.41, t * 1.41, swatch, sides=4, grad=grad, twist=45)


def _anvil(p, c, s, swatch=IRON, yaw=0.0):
	"""An anvil standing at c, `s` = 1 about 0.62 m tall, horn toward +X (turned by yaw, radians)."""
	cx, cy, cz = c
	cs, sn = math.cos(yaw), math.sin(yaw)

	def at(x, y, z):
		return (cx + x * cs - y * sn, cy + x * sn + y * cs, cz + z)
	d = math.degrees(yaw)
	p.box((0.52 * s, 0.36 * s, 0.12 * s), at(0, 0, 0.06 * s), swatch, rot=(0, 0, d), grad=(0.2, 0.9))
	p.box((0.28 * s, 0.2 * s, 0.3 * s), at(0, 0, 0.27 * s), swatch, rot=(0, 0, d), grad=(0.2, 0.9))
	p.box((0.7 * s, 0.3 * s, 0.16 * s), at(-0.02 * s, 0, 0.5 * s), swatch, rot=(0, 0, d), grad=(0.0, 0.6))
	p.seg(at(0.33 * s, 0, 0.52 * s), at(0.72 * s, 0, 0.55 * s), 0.12 * s, 0.0, swatch, sides=6, grad=(0.0, 0.6))
	p.box((0.16 * s, 0.26 * s, 0.13 * s), at(-0.44 * s, 0, 0.515 * s), swatch, rot=(0, 0, d), grad=(0.0, 0.6))


def _coals(p, c, w, d, glow=1.3, flames=3, flame_h=0.35):
	"""A bed of glowing coals (w x d) at c, a few lumps and flames on it."""
	x, y, z = c
	p.blob((w, d, 0.16), (x, y, z), EMBER, segs=(10, 6), grad=(0.3, 0.9), glow=glow)
	for k in range(min(int(w * d * 14) + 4, 40)):
		p.blob((0.14, 0.12, 0.1), (x + p.rng.uniform(-w, w) * 0.4, y + p.rng.uniform(-d, d) * 0.4, z + 0.05), EMBER if k % 3 else FLAME,
			   segs=(6, 4), grad=(0.0, 0.7), glow=glow * 1.15)
	for k in range(flames):
		fx, fy = x + p.rng.uniform(-w, w) * 0.28, y + p.rng.uniform(-d, d) * 0.28
		h = flame_h * p.rng.uniform(0.6, 1.1)
		p.seg((fx, fy, z + 0.04), (fx, fy, z + 0.04 + h), 0.09 * flame_h / 0.35, 0.0, FLAME, sides=5, grad=(0.1, 0.9), glow=1.5, twist=p.rng.uniform(0, 60))


def _hearth_block(p, x, y, w, d, h, swatch=STONE_DARK):
	"""A smith's hearth: a stone block with a raised rim and a bed of coals on top."""
	_block(p, (w, d, h), (x, y, h / 2), swatch, rough=0.03)
	for s in (-1, 1):
		p.box((0.16, d, 0.16), (x + s * (w / 2 - 0.08), y, h + 0.06), STONE_LIGHT, grad=(0.0, 0.6))
		p.box((w, 0.16, 0.16), (x, y + s * (d / 2 - 0.08), h + 0.06), STONE_LIGHT, grad=(0.0, 0.6))
	_coals(p, (x, y, h + 0.02), w - 0.35, d - 0.35)


# ---- The Burn

def burned_cabin():
	"""A Forgehold logger's cabin burned down to its frame: the lower log
	courses and charred corner posts standing on a stone footing, a doorway in
	the front (-Y), the roof fallen in (a gable of rafters still up at the back,
	the ridge beam and a slab of planks down across the floor), ash and a few
	embers inside, and the fieldstone chimney on the right (+X) standing whole
	to 4.8 m. About 6.2 x 4.6 m. Collide it as a mesh: you can walk in."""
	p = Prop("burned_cabin", 431)
	rng = p.rng
	hw, hd, lr = 2.6, 2.0, 0.15
	for x0, y0, x1, y1 in ((-hw, -hd, hw, -hd), (hw, -hd, hw, hd), (hw, hd, -hw, hd), (-hw, hd, -hw, -hd)):   # stone footing
		L = math.hypot(x1 - x0, y1 - y0)
		n = int(L / 0.7)
		for k in range(n):
			t = (k + 0.5) / n
			p.rock((0.75, 0.5, 0.3), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0.08), STONE_DARK if k % 2 else STONE_LIGHT, rot=(0, 0, math.degrees(math.atan2(y1 - y0, x1 - x0))), grad=(0.4, 1.0), jitter=0.05)
	# log courses: each wall keeps a different, ragged height; the front has the door
	walls = [((-hw, -hd), (hw, -hd), 4, (-0.55, 0.55)), ((hw, -hd), (hw, hd), 3, None), ((hw, hd), (-hw, hd), 6, None), ((-hw, hd), (-hw, -hd), 5, None)]
	for (x0, y0), (x1, y1), courses, door in walls:
		L = math.hypot(x1 - x0, y1 - y0)
		ux, uy = (x1 - x0) / L, (y1 - y0) / L
		for k in range(courses):
			z = 0.32 + k * 0.29
			a = rng.uniform(0.0, 0.25) if k else 0.0            # higher courses burnt short at the ends
			b = L - (rng.uniform(0.0, 0.25) if k else 0.0)
			if k >= 2:                                          # and broken off along the wall
				b = a + (b - a) * rng.uniform(0.45, 0.95) if k % 2 else b
				a = a + (b - a) * rng.uniform(0.0, 0.4) * (k >= 3)
			spans = [(a, b)]
			if door:
				d0, d1 = L / 2 + door[0], L / 2 + door[1]
				spans = [(s0, min(s1, d0)) for s0, s1 in spans if s0 < d0] + [(max(s0, d1), s1) for s0, s1 in spans if s1 > d1]
			for s0, s1 in spans:
				if s1 - s0 < 0.3:
					continue
				pa = (x0 + ux * s0, y0 + uy * s0, z)
				pb = (x0 + ux * s1, y0 + uy * s1, z)
				p.seg(pa, pb, lr, lr * 0.92, CHAR, sides=6, grad=(0.05, 0.8))
				if rng.random() < 0.5:                           # a glowing burnt end
					p.seg(pb, (pb[0] + ux * 0.03, pb[1] + uy * 0.03, z), lr * 0.8, lr * 0.8, EMBER, sides=6, glow=1.2)
				if rng.random() < 0.35:
					_crack(p, [(pa[0] + ux * 0.3, pa[1] + uy * 0.3, z + lr * 0.9), (pa[0] + ux * 0.9, pa[1] + uy * 0.9, z + lr * 0.95)], r=0.025, glow=1.1)
	# corner posts, two of them snapped
	for (x, y), top in (((-hw, -hd), 2.5), ((hw, -hd), 1.7), ((hw, hd), 2.6), ((-hw, hd), 2.6)):
		_beam(p, (x, y, 0.0), (x, y, top), 0.14)
		p.rock((0.34, 0.34, 0.3), (x, y, top), CHAR, jitter=0.08)
	for s in (-1, 1):                                          # the door posts
		_beam(p, (s * 0.6, -hd, 0.0), (s * 0.6, -hd, 1.9 if s < 0 else 1.2), 0.1)
	_beam(p, (-hw, hd, 2.62), (hw, hd, 2.62), 0.12)            # the back wall plate
	_beam(p, (-hw, hd, 2.62), (-hw, -hd + 0.6, 2.55), 0.12)     # part of the left one
	for s in (-1, 1):                                          # the back gable, still standing
		_beam(p, (s * (hw + 0.2), hd, 2.55), (0, hd, 3.9), 0.1)
	_beam(p, (-0.9, hd, 3.2), (0.9, hd, 3.2), 0.08)
	p.rock((0.3, 0.3, 0.3), (0, hd, 3.9), CHAR, jitter=0.06)
	_beam(p, (0.1, hd - 0.1, 3.8), (-0.6, -hd + 0.4, 0.25), 0.13)   # the ridge, fallen from the gable to the floor
	for k, x in enumerate((-1.9, -0.9, 0.9, 1.8)):              # rafters: fallen in, or leaning off the left wall
		if k % 2:
			_beam(p, (x, -hd + 0.2, 0.15), (x + 0.5, 0.4, 1.4 + k * 0.2), 0.07)
		else:
			_beam(p, (-hw, x * 0.8, 2.3), (-0.4 + x * 0.2, x * 0.7, 0.15), 0.07)
	for k in range(7):                                         # a slab of roof planks collapsed on the floor, tilted
		y = -1.2 + k * 0.32
		p.box((2.4 - abs(k - 3) * 0.2, 0.28, 0.06), (0.9, y, 0.35 + k * 0.1), CHAR if k % 2 else WOOD_GRAY, rot=(-17, 6, rng.uniform(-6, 6)), grad=(0.2, 0.9))
	p.blob((4.8, 3.6, 0.18), (0, 0, 0.0), SHADE, segs=(12, 5), grad=(0.5, 0.75))       # ash on the floor
	for k in range(9):                                          # debris and embers in it
		x, y = rng.uniform(-hw + 0.5, hw - 0.5), rng.uniform(-hd + 0.4, hd - 0.4)
		if k % 3 == 0:
			p.blob((0.3, 0.25, 0.12), (x, y, 0.08), EMBER, segs=(6, 4), grad=(0.1, 0.6), glow=1.1)
		else:
			_beam(p, (x, y, 0.08), (x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.5, 0.5), 0.12), 0.05)
	# the fieldstone chimney, whole, on the right wall
	cx, cy = hw + 0.55, 0.4
	for k in range(15):
		z = 0.15 + k * 0.32
		w = 1.35 if z < 1.6 else (1.35 - (z - 1.6) * 0.5 if z < 2.2 else 0.95)
		for j in range(2):
			for i in range(2):
				p.rock((w / 2 + 0.12, w / 2 + 0.1, 0.36), (cx + (i - 0.5) * w / 2, cy + (j - 0.5) * w / 2, z), STONE_DARK if (i + j + k) % 3 else STONE_LIGHT,
					   grad=(0.3, 1.0), jitter=0.04)
	p.box((1.05, 1.05, 0.14), (cx, cy, 4.9), STONE_DARK, grad=(0.0, 0.6))
	p.box((0.55, 0.55, 0.1), (cx, cy, 4.98), IRON, grad=(0.8, 1.0))
	p.box((0.12, 0.8, 0.9), (cx - 0.62, cy, 0.62), IRON, grad=(0.8, 1.0))                 # the fireplace mouth, inside
	_coals(p, (cx - 0.8, cy, 0.1), 0.5, 0.6, glow=1.0, flames=0)
	return p.build(bevel=0.02)


def burned_sawmill():
	"""The Forgehold loggers' sawmill after the fire: a plank floor on a stone
	footing with charred posts and a scrap of boarded back wall, the saw frame
	standing in the middle (its blade still in it) over a carriage track with a
	half-sawn log, a broken water wheel on its axle at the right (+X) over a dry
	stone millrace, a stack of burnt logs out front (-Y) and the roof fallen in.
	About 10 x 8.5 m, 5.5 m tall at the wheel. Collide it as a mesh."""
	p = Prop("burned_sawmill", 432)
	rng = p.rng
	x0, x1, y0, y1 = -4.2, 2.0, -3.0, 3.0
	p.box((x1 - x0 + 0.3, y1 - y0 + 0.3, 0.3), ((x0 + x1) / 2, 0, 0.0), STONE_DARK, grad=(0.3, 1.0), jitter=0.04)   # footing
	for k in range(int((y1 - y0) / 0.4)):                      # floor planks, some burnt through
		y = y0 + 0.2 + k * 0.4
		if k in (4, 9):
			continue
		L = (x1 - x0) * (0.55 if k in (3, 10, 11) else 1.0)
		p.box((L, 0.37, 0.06), (x0 + L / 2, y, 0.18), WOOD_GRAY if k % 3 else CHAR, grad=(0.3, 0.9))
	posts = [(x0, y0, 3.4), (x0, 0, 1.9), (x0, y1, 3.6), (x1, y0, 2.4), (x1, y1, 3.8), (-1.1, y0, 1.4), (-1.1, y1, 3.7)]
	for x, y, top in posts:
		_beam(p, (x, y, 0.1), (x, y, top), 0.15)
		p.rock((0.36, 0.36, 0.3), (x, y, top), CHAR, jitter=0.07)
	_beam(p, (x0, y1, 3.5), (x1, y1, 3.6), 0.12)                # back plate
	_beam(p, (x1, y1, 3.6), (x1, 0.6, 3.5), 0.12)
	for k in range(14):                                        # scrap of boarded back wall
		x = x0 + 0.3 + k * 0.42
		h = 0.8 + 2.2 * abs(math.sin(k * 1.7)) * (1.0 if k < 9 else 0.4)
		p.box((0.38, 0.06, h), (x, y1 + 0.12, 0.15 + h / 2), CHAR if k % 2 else WOOD_GRAY, grad=(0.1, 0.9))
	# the carriage track and the saw frame
	for s in (-1, 1):
		p.box((x1 - x0 - 0.4, 0.12, 0.14), ((x0 + x1) / 2, s * 0.45, 0.62), CHAR, grad=(0.2, 0.9))
	for x in (-3.6, -2.2, -0.8, 0.6, 1.6):
		for s in (-1, 1):
			_beam(p, (x, s * 0.45, 0.2), (x, s * 0.45, 0.58), 0.07)
	p.seg((-3.3, 0, 0.98), (-1.0, 0, 0.98), 0.3, 0.28, CHAR, sides=7)       # a half-sawn log on the carriage
	p.seg((-1.0, 0, 0.98), (-0.62, 0, 0.98), 0.28, 0.28, WOOD, sides=7, grad=(0.3, 0.8))
	p.seg((-3.32, 0, 0.98), (-3.36, 0, 0.98), 0.26, 0.26, EMBER, sides=7, glow=1.0)
	sx = -0.3
	for s in (-1, 1):
		_beam(p, (sx, s * 0.95, 0.15), (sx, s * 0.95, 4.2), 0.16)
	_beam(p, (sx, -1.2, 4.1), (sx, 1.2, 4.1), 0.14)
	_beam(p, (sx, -0.95, 2.4), (sx, 0.95, 2.4), 0.1)
	p.box((0.05, 0.36, 2.0), (sx, 0, 1.5), IRON, grad=(0.0, 0.6))            # the blade, in its sash
	for k in range(10):
		p.seg((sx, -0.18, 0.55 + k * 0.2), (sx, -0.27, 0.62 + k * 0.2), 0.025, 0.0, IRON, sides=3)
	_beam(p, (sx, 0, 2.5), (sx, 0, 4.0), 0.05, IRON)
	# the water wheel on its axle, broken
	wx, wc, R = 3.5, 2.8, 2.35
	p.seg((x1, 0, wc), (wx + 1.1, 0, wc), 0.16, 0.16, CHAR, sides=8)
	for x in (wx - 0.9, wx + 1.0):                             # axle trestles
		for s in (-1, 1):
			_beam(p, (x, s * 1.2, 0.0), (x, s * 0.15, wc), 0.1)
	p.seg((wx, 0, wc), (wx + 0.4, 0, wc), 0.5, 0.5, CHAR, sides=8)
	for side in (-0.3, 0.3):
		for k in range(14):
			if k in (2, 3, 8):                                 # burnt away
				continue
			a0, a1 = k * math.tau / 14, (k + 1) * math.tau / 14
			pa = (wx + 0.2 + side, math.cos(a0) * R, wc + math.sin(a0) * R)
			pb = (wx + 0.2 + side, math.cos(a1) * R, wc + math.sin(a1) * R)
			_beam(p, pa, pb, 0.08)
	for k in range(7):
		if k == 2:
			continue
		a = k * math.tau / 7 + 0.3
		_beam(p, (wx + 0.2, 0, wc), (wx + 0.2, math.cos(a) * R, wc + math.sin(a) * R), 0.07)
	for k in range(14):
		if k in (2, 3, 8, 9):
			continue
		a = (k + 0.5) * math.tau / 14
		p.box((0.75, 0.08, 0.5), (wx + 0.2, math.cos(a) * (R + 0.1), wc + math.sin(a) * (R + 0.1)), CHAR if k % 2 else WOOD_GRAY,
			  rot=(math.degrees(a), 0, 0), grad=(0.2, 0.9))
	_beam(p, (wx + 0.2, -1.6, 0.1), (wx + 0.5, -0.2, 0.9), 0.07)   # a spoke fallen in the race
	for s in (-1, 1):                                          # the dry millrace under it
		p.box((0.45, 7.4, 0.8), (wx + 0.2 + s * 1.05, 0, 0.1), STONE_DARK, grad=(0.2, 1.0), jitter=0.04)
	p.box((1.7, 7.4, 0.1), (wx + 0.2, 0, -0.18), SHADE, grad=(0.55, 0.8))
	# a stack of burnt logs out front
	for row, n in enumerate((4, 3, 2)):
		for i in range(n):
			x = -2.4 + (i - (n - 1) / 2) * 0.62
			z = 0.3 + row * 0.52
			p.seg((x, -3.8, z), (x, -5.0, z), 0.3, 0.3, CHAR, sides=7, grad=(0.05, 0.9))
			if (i + row) % 2 == 0:
				p.seg((x, -5.0, z), (x, -5.03, z), 0.25, 0.25, EMBER, sides=7, glow=0.9)
	for s in (-1, 1):
		_beam(p, (-2.4 + s * 1.35, -4.4, 0.0), (-2.4 + s * 1.35, -4.4, 1.2), 0.07)
	# the roof, fallen in: rafters and a tilted slab of planks
	for k in range(6):
		y = -2.4 + k * 0.4
		p.box((3.0, 0.36, 0.07), (-2.8, y, 0.55 + k * 0.28), CHAR if k % 2 else WOOD_GRAY, rot=(-35, 0, rng.uniform(-5, 5)), grad=(0.2, 0.9))
	for x in (-3.8, -1.8, 1.2):
		_beam(p, (x, y1, 3.5), (x + 0.4, -1.0, 0.25), 0.08)
	p.blob((6.0, 5.4, 0.12), (x0 + 3.0, 0, 0.2), SHADE, segs=(12, 5), grad=(0.5, 0.75))
	return p.build(bevel=0.02)


def smoldering_stump():
	"""A burnt stump still smoldering: charred and split at the top, embers
	glowing in the hollow and in cracks down its sides, a thin wisp of smoke
	(see-through) rising about 1.8 m. About 1.4 m across. Collide: none (or a trunk)."""
	p = Prop("smoldering_stump", 433)
	p.seg((0, 0, -0.1), (0, 0, 0.62), 0.42, 0.36, CHAR, sides=8, grad=(0.05, 0.8), jitter=0.02)
	for k in range(6):                                          # the split, jagged rim
		a = k * math.tau / 6 + 0.3
		h = 0.2 + 0.25 * ((k * 7) % 3) / 2
		p.seg((math.cos(a) * 0.28, math.sin(a) * 0.28, 0.55), (math.cos(a) * 0.24, math.sin(a) * 0.24, 0.62 + h), 0.12, 0.02, CHAR, sides=4)
	for k in range(4):                                          # roots
		a = k * math.tau / 4 + 0.7
		p.seg((0, 0, 0.18), (math.cos(a) * 0.72, math.sin(a) * 0.72, -0.05), 0.13, 0.05, CHAR, sides=5, grad=(0.1, 0.9))
	p.blob((0.52, 0.52, 0.14), (0, 0, 0.6), EMBER, segs=(8, 5), grad=(0.1, 0.6), glow=1.6)    # the glowing heart
	p.blob((0.26, 0.26, 0.1), (0.04, -0.02, 0.64), FLAME, segs=(6, 4), grad=(0.0, 0.4), glow=2.0)
	for k, a in enumerate((0.4, 2.2, 4.1)):
		pts = [(math.cos(a + j * 0.1) * (0.4 - j * 0.02), math.sin(a + j * 0.1) * (0.4 - j * 0.02), 0.08 + j * 0.16) for j in range(4)]
		_crack(p, pts, r=0.03, glow=1.4)
	p.blob((1.3, 1.3, 0.1), (0, 0, 0.0), SHADE, segs=(10, 4), grad=(0.5, 0.75))              # ash round the foot
	obj = p.build()
	return join_into(obj, [_smoke("smoldering_stump_smoke", 434, (0.03, 0, 0.8), 1.7, r=0.1, alpha=0.35)])


def giant_anvil():
	"""An ember giant's smithy: an iron anvil about 3.2 m tall and 3.4 m long on
	a stone block, a hammer as long as a man leaning on it, and behind it (+Y) a
	stone forge block with a back wall and a bed of glowing coals. About 5 x 5 m.
	Collide it as a box."""
	p = Prop("giant_anvil", 435)
	_block(p, (1.9, 1.5, 1.1), (0, -0.6, 0.5), STONE_DARK, rough=0.05)
	_anvil(p, (0, -0.6, 1.02), 3.5, IRON)
	p.box((1.1, 0.6, 0.04), (-0.4, -0.6, 3.05), STONE_DARK, grad=(0.0, 0.3))             # a worn, brighter face
	p.box((0.7, 0.18, 0.08), (0.3, -0.6, 3.08), EMBER, glow=1.4)                         # a glowing bar on it
	# the hammer, head down, handle leaning on the anvil's face
	hx, hy = 1.5, -1.9
	p.box((0.8, 0.55, 0.55), (hx, hy, 0.28), IRON, rot=(0, 0, 25), grad=(0.1, 0.8))
	p.seg((hx - 0.1, hy + 0.05, 0.4), (0.5, -1.05, 2.9), 0.09, 0.08, WOOD, sides=6, grad=(0.2, 0.9))
	p.seg((0.62, -1.12, 2.75), (0.45, -1.0, 3.05), 0.11, 0.11, HIDE, sides=6)
	# the forge block behind
	fx, fy = 0.2, 1.7
	_hearth_block(p, fx, fy, 3.0, 1.8, 1.2)
	_block(p, (3.4, 0.6, 2.8), (fx, fy + 1.1, 1.4), STONE_DARK, rough=0.04)
	for s in (-1, 1):
		_block(p, (0.7, 0.7, 2.4), (fx + s * 1.5, fy + 0.8, 1.9), STONE_LIGHT, rough=0.05)
	_block(p, (3.8, 1.0, 0.5), (fx, fy + 0.8, 3.1), STONE_LIGHT, rough=0.05)
	for k in range(3):                                          # tongs and bars in the coals
		x = fx - 0.8 + k * 0.7
		p.seg((x, fy - 0.2, 1.35), (x + 0.3, fy - 1.3, 1.6), 0.05, 0.05, IRON, sides=4)
	p.box((0.8, 1.0, 0.6), (-2.0, 0.6, 0.3), WOOD, grad=(0.2, 1.0))                     # a quench trough
	p.box((0.62, 0.82, 0.05), (-2.0, 0.6, 0.58), WATER, grad=(0.1, 0.5))
	return p.build(bevel=0.04)


def giant_hall_ruin():
	"""The ruin of an ember giants' hall: walls of huge rough-hewn blocks round
	a 16 x 12 m floor, broken down to 2-6 m, open to the sky but for two great
	charred roof beams (one fallen), an entrance 4 m wide in the front (-Y)
	between two standing monoliths, and in the middle a great hearth pit ringed
	with boulders, its ash still glowing. Collide it as a mesh: walk in."""
	p = Prop("giant_hall_ruin", 436)
	rng = p.rng
	hw, hd, t = 8.0, 6.0, 1.6
	p.box((2 * hw, 2 * hd, 0.2), (0, 0, -0.05), STONE_DARK, grad=(0.5, 0.95))
	for k in range(22):                                        # a few great flagstones left
		x, y = rng.uniform(-hw + 2, hw - 2), rng.uniform(-hd + 2, hd - 2)
		if math.hypot(x, y) < 3.2:
			continue
		p.box((rng.uniform(1.4, 2.2), rng.uniform(1.2, 1.8), 0.2), (x, y, 0.06), STONE_LIGHT if k % 2 else STONE_WARM, rot=(0, 0, rng.uniform(-8, 8)), grad=(0.3, 0.9), jitter=0.05)

	def wall(ax, ay, bx, by, heights, gap=None):
		L = math.hypot(bx - ax, by - ay)
		ux, uy = (bx - ax) / L, (by - ay) / L
		yaw = math.degrees(math.atan2(uy, ux))
		n = len(heights)
		for i, h in enumerate(heights):
			s0, s1 = i * L / n, (i + 1) * L / n
			if gap and s1 > gap[0] and s0 < gap[1]:
				continue
			z = 0.0
			course = 0
			while z < h - 0.3:
				ch = min(rng.uniform(1.1, 1.6), h - z)
				m = (s0 + s1) / 2 + (0.3 if course % 2 else -0.3)
				length = (s1 - s0) + 0.2
				sw = (STONE_DARK, STONE_WARM, STONE_DARK, STONE_LIGHT)[(i + course) % 4]
				_block(p, (length, t * rng.uniform(0.92, 1.05), ch), (ax + ux * m, ay + uy * m, z + ch / 2), sw, yaw=yaw + rng.uniform(-3, 3), rough=0.1)
				z += ch
				course += 1
			if h > 2.5 and rng.random() < 0.5:                  # a block tumbled off the top, lying at the foot
				side = rng.choice((-1, 1))
				c = ((s0 + s1) / 2 + rng.uniform(-0.5, 0.5))
				nx, ny = -uy * side, ux * side
				_block(p, (1.8, 1.3, 1.1), (ax + ux * c + nx * 2.0, ay + uy * c + ny * 2.0, 0.5), STONE_LIGHT, yaw=rng.uniform(0, 90), rough=0.12)

	wall(-hw, -hd, hw, -hd, [3.2, 5.4, 4.0, 0, 0, 2.6, 4.6, 2.2], gap=(6.0, 10.0))
	wall(hw, -hd, hw, hd, [4.8, 3.0, 5.8, 5.2, 2.0, 3.6])
	wall(hw, hd, -hw, hd, [6.0, 5.4, 4.2, 6.2, 5.8, 3.0, 2.2, 4.4])
	wall(-hw, hd, -hw, -hd, [2.4, 4.6, 3.2, 1.6, 4.0, 5.0])
	for (x, y) in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)):   # corner blocks
		_block(p, (2.2, 2.2, 2.0), (x, y, 1.0), STONE_WARM, yaw=rng.uniform(-5, 5), rough=0.1)
	for s in (-1, 1):                                           # the monoliths either side of the door
		_block(p, (1.5, 1.9, 7.0), (s * 2.8, -hd, 3.5), STONE_LIGHT, yaw=s * 3, rough=0.06)
		_block(p, (1.8, 2.2, 0.6), (s * 2.8, -hd, 7.2), STONE_WARM, rough=0.06)
	_block(p, (6.4, 1.6, 1.3), (1.0, -hd - 2.4, 0.6), STONE_WARM, yaw=12, rough=0.08)   # the lintel, fallen outside
	# roof beams: one across, one fallen in
	_beam(p, (-5.5, -hd, 4.2), (-5.5, hd, 5.9), 0.35)
	_beam(p, (2.5, hd, 4.6), (1.2, -2.5, 0.35), 0.35)
	# the hearth pit
	for k in range(12):
		a = k * math.tau / 12
		p.rock((1.3, 1.0, 0.9), (math.cos(a) * 2.4, math.sin(a) * 2.4, 0.35), STONE_DARK, rot=(0, 0, math.degrees(a)), jitter=0.12)
	p.seg((0, 0, -0.05), (0, 0, 0.08), 2.1, 2.1, CHAR, sides=16, grad=(0.3, 0.9))
	p.blob((3.4, 3.4, 0.25), (0, 0, 0.08), SHADE, segs=(12, 5), grad=(0.5, 0.75))
	for k in range(6):
		a = k * math.tau / 6 + 0.4
		r = rng.uniform(0.3, 1.2)
		p.blob((0.7, 0.55, 0.16), (math.cos(a) * r, math.sin(a) * r, 0.16), EMBER, segs=(7, 4), grad=(0.1, 0.6), glow=1.0)
	for k in range(3):
		a = k * 2.1
		_beam(p, (math.cos(a) * 1.4, math.sin(a) * 1.4, 0.15), (math.cos(a + 2.6) * 0.8, math.sin(a + 2.6) * 0.8, 0.4), 0.18)
	# giant bones by the fire
	p.seg((4.0, 2.8, 0.25), (5.8, 3.6, 0.2), 0.16, 0.14, BONE, sides=6)
	p.blob((0.45, 0.45, 0.4), (4.0, 2.8, 0.25), BONE, segs=(6, 4))
	p.blob((0.45, 0.45, 0.4), (5.8, 3.6, 0.2), BONE, segs=(6, 4))
	return p.build(bevel=0.06)


def firebird_nest():
	"""A firebird's nest on top of a burned snag: a charred trunk about 7 m
	tall, its broken branches bare, crowned by a ring of blackened sticks about
	2.8 m across round a bowl of glowing embers, with two ember-gold eggs. The
	nest's rim is about 8.2 m up. Collide it as a trunk."""
	p = Prop("firebird_nest", 437)
	rng = p.rng
	pts = [(0, 0, -0.3), (0.1, 0.05, 1.8), (0.35, -0.05, 3.8), (0.4, 0.1, 5.6), (0.25, 0.15, 7.2)]
	_chain(p, pts, 0.55, 0.3, CHAR, sides=8, grad=(0.1, 0.8))
	for k in range(5):
		a = k * math.tau / 5 + 0.3
		p.seg((0, 0, 0.8), (math.cos(a) * 1.4, math.sin(a) * 1.4, -0.15), 0.26, 0.08, CHAR, sides=5, grad=(0.2, 0.9))
	for z, a, L in ((3.0, 0.6, 1.8), (4.4, 3.1, 1.5), (5.4, 1.8, 1.2), (2.2, 4.4, 1.1)):
		base = Vector((0.3, 0, z))
		d = Vector((math.cos(a), math.sin(a), 0.6)).normalized()
		_chain(p, [tuple(base), tuple(base + d * L * 0.6), tuple(base + d * L + Vector((0, 0, 0.3)))], 0.14, 0.04, CHAR, sides=5)
	_crack(p, [(0.5, -0.1, 1.2), (0.55, -0.05, 1.8), (0.6, 0.0, 2.3)], r=0.04, glow=1.2)
	# the nest
	top = 7.2
	for fork, a in ((0.9, 0.2), (0.8, 2.3), (0.85, 4.2)):         # the forks that hold it
		p.seg((0.25, 0.15, top - 0.8), (0.25 + math.cos(a) * fork, 0.15 + math.sin(a) * fork, top + 0.2), 0.14, 0.08, CHAR, sides=5)
	cx, cy = 0.25, 0.15
	p.blob((2.6, 2.6, 0.7), (cx, cy, top + 0.15), CHAR, segs=(12, 6), grad=(0.1, 0.9), jitter=0.05)
	for layer, (R, z, n) in enumerate(((1.3, top + 0.35, 16), (1.25, top + 0.6, 14), (1.15, top + 0.82, 12))):
		for k in range(n):
			a = k * math.tau / n + rng.uniform(-0.2, 0.2) + layer * 0.3
			c = Vector((cx + math.cos(a) * R, cy + math.sin(a) * R, z))
			tv = Vector((-math.sin(a), math.cos(a), 0)).lerp(Vector((math.cos(a), math.sin(a), 0)), rng.uniform(-0.5, 0.5))
			tv.z = rng.uniform(-0.25, 0.25)
			L = rng.uniform(0.8, 1.5)
			p.seg(tuple(c - tv * L / 2), tuple(c + tv * L / 2), 0.06, 0.04, CHAR if (k + layer) % 4 else WOOD_GRAY, sides=5, grad=(0.1, 0.9))
	for k in range(8):                                          # sticks poking out
		a = rng.uniform(0, math.tau)
		p.seg((cx + math.cos(a) * 1.0, cy + math.sin(a) * 1.0, top + 0.5), (cx + math.cos(a) * 2.0, cy + math.sin(a) * 2.0, top + rng.uniform(0.2, 1.1)), 0.04, 0.015, CHAR, sides=4)
	_coals(p, (cx, cy, top + 0.62), 1.9, 1.9, glow=1.5, flames=5, flame_h=0.45)
	for k, (x, y) in enumerate(((-0.25, 0.05), (0.3, 0.2))):     # eggs, glowing like hot metal
		p.blob((0.36, 0.36, 0.48), (cx + x, cy + y, top + 0.9), GOLD if k else FLAME, segs=(8, 6), rot=(rng.uniform(-15, 15), rng.uniform(-15, 15), 0), grad=(0.0, 0.5), glow=0.9)
	for k in range(4):                                          # a few red-gold feathers caught in the sticks
		a = rng.uniform(0, math.tau)
		p.blob((0.6, 0.12, 0.03), (cx + math.cos(a) * 1.35, cy + math.sin(a) * 1.35, top + 0.75), CLOTH_RED if k % 2 else GOLD, rot=(0, 25, math.degrees(a)), segs=(6, 3))
	return p.build()


# ---- Blackglass

def glass_shards():
	"""A cluster of sharp black volcanic glass, 1-2.8 m tall and about 3 m
	across: glossy shards leaning out from a common root, three of them
	smoky and see-through with a faint orange core. Collide it as a box."""
	p = Prop("glass_shards", 441)
	clear = Prop("glass_shards_clear", 442)
	core = Prop("glass_shards_core", 443)
	shards = [((0, 0), 2.8, 0.42, (0.05, 0.05)), ((0.6, 0.25), 1.9, 0.34, (0.45, 0.1)), ((-0.55, 0.3), 2.2, 0.36, (-0.4, 0.15)),
			  ((0.15, -0.6), 1.6, 0.3, (0.1, -0.45)), ((-0.3, 0.7), 1.3, 0.27, (-0.2, 0.4)), ((0.95, -0.45), 1.1, 0.24, (0.5, -0.3)),
			  ((-1.0, -0.35), 1.0, 0.24, (-0.55, -0.2)), ((0.55, 0.85), 0.8, 0.2, (0.3, 0.5)), ((-0.8, 0.9), 0.6, 0.18, (-0.4, 0.4))]
	for k, ((x, y), h, r, (lx, ly)) in enumerate(shards):
		top = (x + lx * h * 0.5, y + ly * h * 0.5, h)
		if k in (1, 3, 6):
			clear.seg((x, y, -0.2), top, r, 0.0, IRON, sides=4, grad=(0.0, 0.5), twist=k * 31)
			mid = (x + (top[0] - x) * 0.1, y + (top[1] - y) * 0.1, 0.0)
			core.seg(mid, (x + (top[0] - x) * 0.6, y + (top[1] - y) * 0.6, h * 0.6), r * 0.3, 0.0, EMBER, sides=4, grad=(0.1, 0.6), glow=0.9, twist=k * 31)
		else:
			p.seg((x, y, -0.2), top, r, 0.0, IRON, sides=4 if k % 2 else 5, grad=(0.0, 0.7), twist=k * 31)
	for k in range(9):                                          # glassy rubble round the foot
		a = k * math.tau / 9 + 0.3
		rr = p.rng.uniform(1.0, 1.45)
		p.seg((math.cos(a) * rr, math.sin(a) * rr, -0.1), (math.cos(a) * (rr + 0.2), math.sin(a) * (rr + 0.2), p.rng.uniform(0.15, 0.4)), 0.14, 0.0, IRON, sides=4, twist=k * 40)
	obj = _glossy(p.build(), 0.08)
	return join_into(obj, [_translucent(clear.build(), 0.62, 0.05), core.build()])


def glass_crack():
	"""A glowing crack in a black glass floor, about 4.2 m long along X, flat on
	the ground (under 6 cm tall): a jagged lip of dark glass either side of an
	orange seam, with two branching cracks. Collide: none."""
	p = Prop("glass_crack", 444)

	def strip(pts, w, z, swatch, glow=0.0, grad=(0.1, 0.6)):
		for (ax, ay), (bx, by) in zip(pts, pts[1:]):
			L = math.hypot(bx - ax, by - ay)
			p.box((L + w * 0.9, w, z), ((ax + bx) / 2, (ay + by) / 2, z / 2), swatch, rot=(0, 0, math.degrees(math.atan2(by - ay, bx - ax))), grad=grad, glow=glow)

	main = [(-2.1, 0.1), (-1.5, -0.1), (-0.9, 0.12), (-0.3, -0.05), (0.3, 0.1), (0.9, -0.12), (1.5, 0.05), (2.1, -0.1)]
	br1 = [(-0.3, -0.05), (-0.1, -0.5), (0.25, -0.85)]
	br2 = [(0.9, -0.12), (1.2, 0.35), (1.1, 0.8)]
	strip(main, 0.42, 0.04, IRON, grad=(0.0, 0.3))
	strip(br1, 0.26, 0.035, IRON, grad=(0.0, 0.3))
	strip(br2, 0.26, 0.035, IRON, grad=(0.0, 0.3))
	strip(main, 0.12, 0.055, EMBER, glow=1.8, grad=(0.1, 0.4))
	strip(br1, 0.07, 0.05, EMBER, glow=1.5, grad=(0.1, 0.4))
	strip(br2, 0.07, 0.05, EMBER, glow=1.5, grad=(0.1, 0.4))
	strip([(-0.9, 0.12), (-0.3, -0.05), (0.3, 0.1)], 0.05, 0.06, FLAME, glow=2.2, grad=(0.0, 0.3))
	return _glossy(p.build(), 0.12)


def glass_pool():
	"""A round pool of black glass that cooled mirror-still, 10 m across: a
	near-mirror dark surface a hand above the ground, inside a low, slightly
	raised lip of rougher glass (to 18 cm). Walk on it. Collide: none."""
	p = Prop("glass_pool", 445)
	_lathe(p, [(5.1, -0.05), (5.0, 0.08), (4.85, 0.18), (4.65, 0.16), (4.55, 0.08), (4.4, -0.05)], 32, STONE_DARK, grad=(0.1, 0.9), jitter=0.04)
	for k in range(14):
		a = k * math.tau / 14 + p.rng.uniform(-0.1, 0.1)
		p.seg((math.cos(a) * 4.9, math.sin(a) * 4.9, 0.0), (math.cos(a) * 5.1, math.sin(a) * 5.1, 0.28), 0.12, 0.0, IRON, sides=4, twist=k * 20)
	rim = _glossy(p.build(), 0.3)
	s = Prop("glass_pool_surface", 446)
	s.seg((0, 0, -0.05), (0, 0, 0.1), 4.62, 4.62, IRON, sides=32, grad=(0.0, 0.15))
	surf = s.build()
	for i, m in enumerate(surf.data.materials):
		g = m.copy()
		g.name = m.name + "_mirror"
		b = g.node_tree.nodes["Principled BSDF"]
		b.inputs["Roughness"].default_value = 0.02
		b.inputs["Metallic"].default_value = 0.35
		surf.data.materials[i] = g
	return join_into(rim, [surf])


def glass_entombed():
	"""A Forgehold soldier caught in the glass: a dim armored figure, one arm
	flung up before its face, sword down, standing inside a smoky, see-through
	block of black crystal about 2.3 m tall and 1.4 m across, on a foot of
	glass shards. Collide it as a box."""
	p = Prop("glass_entombed", 447)
	# the soldier, about 1.65 m, facing -Y
	for s in (-1, 1):
		p.seg((s * 0.12, 0.02, 0.1), (s * 0.13, 0.0, 0.52), 0.08, 0.07, IRON, sides=6)
		p.seg((s * 0.13, 0.0, 0.52), (s * 0.12, -0.03 if s < 0 else 0.08, 0.92), 0.09, 0.08, STONE_DARK, sides=6)
		p.box((0.14, 0.24, 0.1), (s * 0.12, -0.04, 0.12), IRON)
	p.box((0.42, 0.26, 0.5), (0, 0.0, 1.18), STONE_DARK, rot=(8, 0, 0), grad=(0.1, 0.8))       # breastplate
	p.box((0.46, 0.28, 0.16), (0, 0.0, 0.94), IRON)
	p.blob((0.24, 0.24, 0.27), (0.02, -0.05, 1.56), STONE_DARK, segs=(8, 6), rot=(-15, 0, 10))     # helmed head, turned away
	p.seg((0.02, -0.06, 1.6), (0.02, -0.07, 1.74), 0.14, 0.03, IRON, sides=6)
	for s in (-1, 1):
		p.blob((0.2, 0.2, 0.16), (s * 0.26, 0.0, 1.38), IRON, segs=(6, 4))
		p.box((0.03, 0.02, 0.02), (s * 0.05, -0.17, 1.57), EMBER, glow=0.5)
	_chain(p, [(-0.26, 0.0, 1.38), (-0.36, -0.2, 1.52), (-0.1, -0.3, 1.72)], 0.07, 0.06, STONE_DARK, sides=6)   # arm flung up
	_chain(p, [(0.26, 0.0, 1.38), (0.33, -0.05, 1.08), (0.36, -0.12, 0.86)], 0.07, 0.06, STONE_DARK, sides=6)
	p.box((0.05, 0.03, 0.9), (0.37, -0.14, 0.45), IRON, grad=(0.0, 0.5))                          # the sword, point down
	p.box((0.22, 0.05, 0.04), (0.37, -0.14, 0.88), IRON)
	obj = p.build()
	# the crystal: a leaning, faceted six-sided block
	c = Prop("glass_entombed_crystal", 448)
	_lathe(c, [(0.0, -0.1), (0.72, -0.1), (0.78, 0.6), (0.74, 1.6), (0.6, 2.05), (0.3, 2.35), (0.0, 2.4)], 6, IRON, grad=(0.0, 0.4), jitter=0.05)
	crystal = _translucent(c.build(), 0.55, 0.04)
	f = Prop("glass_entombed_foot", 449)
	for k in range(8):
		a = k * math.tau / 8 + 0.2
		r = f.rng.uniform(0.7, 0.95)
		h = f.rng.uniform(0.3, 0.9)
		f.seg((math.cos(a) * r, math.sin(a) * r, -0.1), (math.cos(a) * (r + 0.25), math.sin(a) * (r + 0.25), h), 0.2, 0.0, IRON, sides=4, twist=k * 37)
	foot = _glossy(f.build(), 0.08)
	return join_into(obj, [crystal, foot])


# ---- Forgehold

def _brazier_stand(p, x, y, h, r=0.6):
	"""A stone pillar holding an iron fire bowl, flames rising from it."""
	_block(p, (0.8, 0.8, h), (x, y, h / 2), STONE_DARK, rough=0.03)
	p.box((1.0, 1.0, 0.18), (x, y, h), STONE_LIGHT, grad=(0.0, 0.6))
	bowl = _lathe(p, [(0.2, h + 0.05), (r, h + 0.3), (r + 0.1, h + 0.55), (r - 0.06, h + 0.52), (0.18, h + 0.2)], 12, IRON, grad=(0.0, 0.7))
	bowl.data.transform(Matrix.Translation((x, y, 0)))
	_coals(p, (x, y, h + 0.45), r * 1.6, r * 1.6, glow=1.3, flames=0)
	for loc, rr, fh in (((0, 0), 0.34, 1.1), ((0.2, 0.1), 0.22, 0.75), ((-0.18, -0.1), 0.2, 0.7)):
		p.seg((x + loc[0], y + loc[1], h + 0.5), (x + loc[0], y + loc[1], h + 0.5 + fh), rr, 0.0, FLAME, sides=6, grad=(0.1, 0.95), glow=1.4, twist=fh * 50)


def forge_gate():
	"""Forgehold's gate, cut into the volcano's rock: a 6 x 8.5 m passage 4 m
	deep through carved basalt, its two great door leaves standing open against
	the passage walls (+Y side), a lintel carved with Agnavar's head, his tusks
	glowing like hot iron, and a brazier on a stone pillar either side of the
	mouth, rough rock at its shoulders. About 18.7 x 8 m, 12.5 m tall. Faces -Y. Collide it as a mesh: the
	passage is walkable."""
	p = Prop("forge_gate", 451)
	rng = p.rng
	hw, oh, dp = 3.0, 8.5, 4.0          # half the opening, its height, the passage depth
	for s in (-1, 1):
		_block(p, (4.6, dp + 1.0, 12.0), (s * (hw + 2.3), 0.3, 6.0), STONE_DARK, rough=0.02)       # the carved jambs
		p.box((1.0, 0.5, oh + 0.8), (s * (hw + 0.5), -dp / 2 - 0.3, (oh + 0.8) / 2), IRON, grad=(0.2, 0.9))  # pilasters framing the mouth
		p.box((1.3, 0.7, 0.6), (s * (hw + 0.5), -dp / 2 - 0.35, 0.3), STONE_LIGHT, grad=(0.1, 0.8))
		for k in range(4):                                     # rough rock round the carved face
			_block(p, (2.6, 3.5, 3.4), (s * (hw + 4.4), rng.uniform(0.5, 2.0), 1.5 + k * 2.8), STONE_DARK, yaw=rng.uniform(0, 25), rough=0.18)
		leaf_x = s * (hw - 0.3)
		p.box((0.45, 3.2, oh - 0.4), (leaf_x, dp / 2 - 1.8, (oh - 0.4) / 2), STONE_DARK, grad=(0.2, 1.0))
		for z in (1.2, 4.0, 6.8):
			p.box((0.5, 3.25, 0.28), (leaf_x, dp / 2 - 1.8, z), IRON, grad=(0.0, 0.6))
		for k in range(3):
			p.blob((0.16, 0.16, 0.16), (leaf_x - s * 0.26, dp / 2 - 2.8 + k * 1.0, 4.0), GOLD, segs=(6, 4))
		_brazier_stand(p, s * (hw + 1.5), -dp / 2 - 1.4, 2.3)
	_block(p, (2 * hw + 0.4, dp + 1.0, 12.0 - oh), (0, 0.3, oh + (12.0 - oh) / 2), STONE_DARK, rough=0.02)   # over the passage
	p.box((2 * hw + 2.6, 0.7, 1.0), (0, -dp / 2 - 0.35, oh + 0.3), IRON, grad=(0.1, 0.8))                        # the lintel
	p.box((2 * hw + 3.4, 0.9, 0.5), (0, -dp / 2 - 0.4, 12.1), STONE_LIGHT, grad=(0.0, 0.7))
	for k in range(9):                                        # a row of carved teeth under the cornice
		p.box((0.5, 0.3, 0.6), (-4.0 + k * 1.0, -dp / 2 - 0.55, 11.55), STONE_LIGHT, grad=(0.1, 0.8))
	p.box((6.6, 0.3, 3.4), (0, -dp / 2 - 0.2, 10.3), IRON, grad=(0.3, 1.0))                # the carved panel behind the head
	S = 2.0
	hc = (0, -dp / 2 - 0.4 - 0.45 * S, 10.4)
	_elephant_head(p, hc, S, STONE_DARK, trunk=[(0, -0.4, -0.1), (0, -0.55, -0.45), (0, -0.6, -0.72), (0, -0.78, -0.68)], tusks=(False, False))
	for x in (-1, 1):                                         # ember tusks
		a = (hc[0] + x * 0.25 * S, hc[1] - 0.35 * S, hc[2] - 0.35 * S)
		b = (hc[0] + x * 0.38 * S, hc[1] - 0.85 * S, hc[2] - 0.55 * S)
		c2 = (hc[0] + x * 0.3 * S, hc[1] - 1.15 * S, hc[2] - 0.25 * S)
		_chain(p, [a, b, c2], 0.09 * S, 0.02 * S, EMBER, sides=6, grad=(0.0, 0.5), glow=1.6)
	p.seg((0, hc[1] - 0.3 * S, hc[2] + 0.4 * S), (0, hc[1] - 0.32 * S, hc[2] + 0.85 * S), 0.15 * S, 0.0, FLAME, sides=6, glow=1.6)   # flame on the brow
	p.box((2 * hw, dp + 1.0, 0.1), (0, 0.3, 0.02), STONE_DARK, grad=(0.5, 0.9))          # the threshold
	return p.build(bevel=0.06)


def forge_hall():
	"""A great smithy of black basalt, 14 x 10 m: KayKit walls restoned to
	basalt at the back and sides, 5 m tall, the front (-Y) open between pillars
	under a stone beam, a dark slate gable roof, and a tall chimney at the back
	glowing at its crown (14 m). Inside: two hearths of coals against the back
	wall under hoods, three anvils, a quench trough and a rack of tools.
	Collide it as a mesh: walk in at the front."""
	p = Prop("forge_hall", 452)
	hw, hd, wh = 7.0, 5.0, 5.0
	p.box((2 * hw + 0.6, 2 * hd + 0.6, 0.2), (0, 0, 0.0), STONE_DARK, grad=(0.4, 0.95))      # the floor
	for x in (-3.5, 3.5):                                      # hearths and hoods on the back wall
		_hearth_block(p, x, hd - 1.2, 2.4, 1.4, 0.9)
		p.seg((x, hd - 1.1, 2.4), (x, hd - 0.7, 3.5), 1.5, 0.45, STONE_DARK, sides=4, grad=(0.1, 0.9), twist=45)
		p.seg((x, hd - 1.1, 2.32), (x, hd - 1.1, 2.42), 1.55, 1.55, IRON, sides=4, grad=(0.0, 0.5), twist=45)
		p.box((0.6, 0.6, wh - 3.4), (x, hd - 0.7, 3.4 + (wh - 3.4) / 2), STONE_DARK)
	for k, (x, y) in enumerate(((-3.5, 1.2), (0.2, 1.8), (3.6, 1.1))):
		p.seg((x, y, 0.1), (x, y, 0.7), 0.42, 0.38, WOOD, sides=9, grad=(0.3, 1.0))
		_anvil(p, (x, y, 0.7), 1.4, IRON, yaw=0.3 * (k - 1))
	p.box((0.3, 0.12, 0.05), (0.1, 1.8, 1.49), EMBER, glow=1.6)                           # hot iron on an anvil
	p.box((2.4, 0.9, 0.7), (-0.2, hd - 1.2, 0.45), STONE_DARK, grad=(0.2, 0.9))            # quench trough
	p.box((2.2, 0.7, 0.05), (-0.2, hd - 1.2, 0.78), WATER, grad=(0.1, 0.5))
	for k in range(5):                                         # a tool rack on the left wall
		p.seg((-hw + 0.55, -2.0 + k * 0.5, 0.2), (-hw + 0.5, -2.0 + k * 0.5 + 0.1, 1.8), 0.035, 0.035, WOOD, sides=5)
		p.box((0.16, 0.28, 0.2), (-hw + 0.52, -2.0 + k * 0.5 + 0.1, 1.85), IRON)
	p.box((0.2, 2.8, 0.12), (-hw + 0.45, -1.0, 1.5), WOOD)
	for s in (-1, 1):                                          # the front: stone beam on pillars
		_block(p, (1.1, 1.1, wh), (s * (hw - 0.3), -hd + 0.3, wh / 2), STONE_DARK, rough=0.02)
	for x in (-2.4, 2.4):
		_block(p, (0.8, 0.8, wh), (x, -hd + 0.3, wh / 2), STONE_DARK, rough=0.02)
		p.box((1.1, 1.1, 0.3), (x, -hd + 0.3, 0.15), STONE_LIGHT)
	p.box((2 * hw + 0.4, 1.0, 0.8), (0, -hd + 0.3, wh + 0.2), IRON, grad=(0.1, 0.9))
	p.box((2 * hw + 0.4, 1.0, 0.8), (0, hd - 0.3, wh + 0.2), IRON, grad=(0.1, 0.9))
	for s in (-1, 1):
		p.box((1.0, 2 * hd, 0.8), (s * (hw - 0.3), 0, wh + 0.2), IRON, grad=(0.1, 0.9))
	# the roof: a slate gable, ridge along X
	rise = 2.6
	ang = math.atan2(rise, hd)
	slope = math.hypot(hd, rise) + 0.7
	for s in (-1, 1):
		down = Vector((0, math.cos(ang) * s, -math.sin(ang)))
		c = Vector((0, 0, wh + 0.6 + rise)) + down * slope / 2
		p.box((2 * hw + 1.0, slope, 0.25), tuple(c), STONE_DARK, rot=(-math.degrees(ang) * s, 0, 0), grad=(0.1, 0.9))
		for i in range(5):
			cc = Vector((0, 0, wh + 0.6 + rise)) + down * slope * (i + 0.5) / 5 + Vector((0, math.sin(ang) * s, math.cos(ang))) * 0.16
			p.box((2 * hw + 1.1, slope / 5 * 1.05, 0.1), tuple(cc), IRON, rot=(-math.degrees(ang) * s, 0, 0), grad=(0.0, 0.8))
	for x in (-hw + 0.3, hw - 0.3):                           # gable ends
		t = 0.5
		tri = [(-hd, wh + 0.6), (hd, wh + 0.6), (0, wh + 0.6 + rise)]
		verts = [(x - t / 2, y, z) for y, z in tri] + [(x + t / 2, y, z) for y, z in tri]
		p.poly(verts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], STONE_DARK, grad=(0.1, 0.9))
	p.seg((-hw - 0.4, 0, wh + 0.65 + rise), (hw + 0.4, 0, wh + 0.65 + rise), 0.2, 0.2, IRON, sides=6)
	# the great chimney, glowing at the crown
	cx, cy = 0.0, hd + 0.3
	_block(p, (2.4, 2.0, 12.5), (cx, cy, 6.25), STONE_DARK, rough=0.02)
	for z in (4.0, 8.0, 11.5):
		p.box((2.6, 2.2, 0.3), (cx, cy, z), IRON, grad=(0.1, 0.8))
	p.box((2.8, 2.4, 0.4), (cx, cy, 12.7), STONE_LIGHT, grad=(0.0, 0.6))
	p.box((1.6, 1.2, 0.5), (cx, cy, 12.75), EMBER, glow=1.8, grad=(0.0, 0.4))
	for s in (-1, 1):
		p.box((0.12, 1.3, 0.5), (cx + s * 1.21, cy, 12.1), EMBER, glow=1.2, grad=(0.1, 0.5))
	obj = p.build(bevel=0.04)
	# the walls: KayKit's own, repainted basalt
	walls = []
	for k in range(4):                                         # back: 4 x 3.5 m, 5 m tall
		x = -hw + 1.75 + k * 3.5
		walls += kaykit("wall" if k in (0, 3) else "wall_cracked", (x, hd, 0.0), math.pi, (3.5 / 4, 0.75, wh / 4))
	for s in (-1, 1):
		for k in range(3):
			y = -hd + 5.0 / 3 + k * 10.0 / 3
			walls += kaykit("wall_window_open" if k == 1 else "wall", (s * hw, y, 0.0), -s * math.pi / 2, (10.0 / 3 / 4, 0.75, wh / 4))
	for x, y in ((-hw, hd), (hw, hd)):
		walls += kaykit("pillar", (x, y, 0.0), 0.0, (0.8, 0.8, wh / 4))
	return _merge_materials(join_into(obj, _restone(walls, BASALT)))


def smelter():
	"""A tall stone smelting furnace, about 5.6 m: a tapering round stack of
	dark stone bound with iron, a glowing arched mouth at its foot (-Y) with a
	stone chute running molten metal down into a mold trough, a bellows pipe
	at its side and a hopper ladder up the back. About 3.5 x 5 m. Collide it as a box."""
	p = Prop("smelter", 453)
	_lathe(p, [(0.0, 0.0), (1.4, 0.0), (1.45, 1.0), (1.2, 3.2), (0.95, 5.0), (0.75, 5.4), (0.55, 5.4), (0.0, 5.3)], 12, STONE_DARK, grad=(0.1, 0.9), jitter=0.03)
	_hoops(p, (0, 0), 1.46, (0.9,), IRON, w=0.16)
	_hoops(p, (0, 0), 1.3, (2.6,), IRON, w=0.16)
	_hoops(p, (0, 0), 1.03, (4.4,), IRON, w=0.16)
	p.seg((0, 0, 5.3), (0, 0, 5.46), 0.6, 0.6, EMBER, sides=12, glow=1.8)                      # the glowing top
	p.seg((0, 0, 5.4), (0, 0, 6.1), 0.35, 0.0, FLAME, sides=6, glow=1.4)
	# the mouth: an arch of blocks round a glowing opening
	p.box((1.0, 0.3, 1.0), (0, -1.38, 0.8), EMBER, glow=2.0, grad=(0.0, 0.5))
	p.box((0.6, 0.2, 0.5), (0, -1.46, 0.75), FLAME, glow=2.4, grad=(0.0, 0.4))
	for k in range(7):
		a = math.pi * k / 6
		p.box((0.36, 0.5, 0.36), (math.cos(a) * 0.7, -1.45, 1.2 + math.sin(a) * 0.6 - 0.2 * (k in (0, 6))), STONE_LIGHT, rot=(0, -math.degrees(a) + 90, 0), grad=(0.0, 0.7))
	# the chute and the mold trough, molten metal running in them
	p.box((0.6, 1.8, 0.2), (0, -2.2, 0.62), STONE_LIGHT, rot=(-15, 0, 0), grad=(0.0, 0.7))
	for s in (-1, 1):
		p.box((0.12, 1.8, 0.2), (s * 0.3, -2.2, 0.75), STONE_LIGHT, rot=(-15, 0, 0), grad=(0.0, 0.7))
	p.box((0.3, 1.8, 0.04), (0, -2.2, 0.73), EMBER, rot=(-15, 0, 0), glow=2.0)
	p.box((1.8, 0.9, 0.35), (0, -3.4, 0.18), STONE_DARK, grad=(0.1, 0.8))
	p.box((1.5, 0.6, 0.04), (0, -3.4, 0.36), EMBER, glow=1.5)
	for k in range(3):
		p.box((0.06, 0.62, 0.06), (-0.5 + k * 0.5, -3.4, 0.38), STONE_DARK)
	# bellows pipe on the right and a ladder up the back
	p.seg((1.4, -0.3, 0.7), (2.4, -0.4, 0.7), 0.14, 0.14, IRON, sides=6)
	p.box((0.9, 0.7, 0.4), (2.6, -0.4, 0.7), HIDE, grad=(0.1, 0.9))
	for s in (-1, 1):
		p.box((0.5, 0.1, 0.5), (2.6, -0.4 + s * 0.35, 0.7), WOOD)
	for s in (-1, 1):
		p.seg((s * 0.35, 1.9, 0.0), (s * 0.35, 1.1, 5.2), 0.05, 0.05, WOOD, sides=5)
	for k in range(9):
		z = 0.5 + k * 0.55
		y = 1.9 - (z / 5.2) * 0.8
		p.seg((-0.35, y, z), (0.35, y, z), 0.035, 0.035, WOOD, sides=4)
	p.box((0.6, 0.6, 0.5), (0.9, -1.6, 0.25), WOOD, grad=(0.2, 1.0))                          # a bin of ore
	for k in range(5):
		p.rock((0.25, 0.22, 0.2), (0.9 + p.rng.uniform(-0.18, 0.18), -1.6 + p.rng.uniform(-0.18, 0.18), 0.55), STONE_DARK if k % 2 else STONE_WARM, jitter=0.03)
	return p.build(bevel=0.03)


def ore_cart():
	"""A mine cart heaped with ore, about 1.7 x 1.1 m and 1.35 m tall, on a 3 m
	piece of track (along Y) on wooden sleepers. Collide it as a box."""
	p = Prop("ore_cart", 454)
	for k in range(6):
		p.box((1.5, 0.22, 0.1), (0, -1.25 + k * 0.5, 0.05), WOOD_GRAY, grad=(0.2, 0.9))
	for s in (-1, 1):
		p.box((0.07, 3.0, 0.1), (s * 0.5, 0, 0.14), IRON, grad=(0.0, 0.5))
	for sx in (-1, 1):
		for sy in (-1, 1):
			p.seg((sx * 0.5 - sx * 0.05, sy * 0.45, 0.38), (sx * 0.5 + sx * 0.03, sy * 0.45, 0.38), 0.19, 0.19, IRON, sides=10, grad=(0.1, 0.8))
	for s in (-1, 1):
		p.seg((-0.55, s * 0.45, 0.38), (0.55, s * 0.45, 0.38), 0.04, 0.04, IRON, sides=5)
	p.box((0.95, 1.55, 0.62), (0, 0, 0.84), WOOD, grad=(0.2, 1.0))                        # the tub
	p.box((1.03, 1.63, 0.08), (0, 0, 1.15), IRON, grad=(0.0, 0.5))
	for y in (-0.5, 0.5):
		p.box((1.0, 0.08, 0.64), (0, y, 0.84), IRON, grad=(0.0, 0.6))
	p.blob((0.95, 1.5, 0.55), (0, 0, 1.12), STONE_DARK, segs=(8, 5), grad=(0.3, 1.0), jitter=0.04)
	for k in range(12):
		x, y = p.rng.uniform(-0.35, 0.35), p.rng.uniform(-0.55, 0.55)
		sw = (STONE_WARM, STONE_DARK, GOLD, EMBER)[k % 4]
		p.rock((0.22, 0.2, 0.18), (x, y, 1.25 + p.rng.uniform(0, 0.1)), sw, jitter=0.03, grad=(0.1, 0.8))
	p.seg((0, -0.8, 0.9), (0, -1.0, 0.9), 0.03, 0.03, IRON, sides=4)
	p.seg((-0.25, -1.0, 0.9), (0.25, -1.0, 0.9), 0.03, 0.03, IRON, sides=4)
	return p.build(bevel=0.02)


def mine_entrance():
	"""A Forgehold mine's mouth in a rock face: a timbered tunnel 2.8 m wide and
	3 m high going dark a few meters back, rails running out of it, a lantern
	hung from the lintel and rock heaped round and over it. About 8 x 5.5 m,
	5.5 m tall. Faces -Y. Collide it as a mesh (the tunnel ends in a dark wall
	3 m in)."""
	p = Prop("mine_entrance", 455)
	rng = p.rng
	hw, h, dp = 1.4, 3.0, 3.2
	p.box((2 * hw, dp, 0.2), (0, dp / 2, -0.08), STONE_DARK, grad=(0.6, 1.0))
	for y0, y1, g in ((0.0, 1.2, (0.4, 0.8)), (1.2, 2.2, (0.7, 0.95)), (2.2, dp, (0.9, 1.0))):
		for s in (-1, 1):
			p.box((0.3, y1 - y0, h), (s * (hw + 0.15), (y0 + y1) / 2, h / 2), SHADE, grad=g)
		p.box((2 * hw + 0.6, y1 - y0, 0.3), (0, (y0 + y1) / 2, h + 0.15), SHADE, grad=g)
	p.box((2 * hw + 0.4, 0.3, h + 0.2), (0, dp, h / 2), SHADE, grad=(1.0, 1.0))
	for s in (-1, 1):                                         # rock either side and over the top
		for k, (y, z, sz) in enumerate(((0.3, 1.2, 2.8), (2.2, 1.4, 3.0), (0.8, 3.6, 2.4))):
			w = rng.uniform(2.2, 2.8)
			p.rock((w, sz, sz), (s * (hw + 0.3 + w / 2), y, z), STONE_DARK, jitter=0.12)
	for y in (0.2, 2.4):
		p.rock((5.4, 3.0, 2.4), (rng.uniform(-0.3, 0.3), y, h + 1.4), STONE_DARK, jitter=0.12)
	p.rock((3.5, 3.0, 2.0), (0.5, 1.6, h + 3.0), STONE_LIGHT, jitter=0.14)
	for y, sw in ((-0.25, WOOD), (1.6, WOOD_GRAY)):            # the timbers
		for s in (-1, 1):
			p.box((0.3, 0.3, h), (s * (hw - 0.1), y, h / 2), sw, grad=(0.25, 1.0))
		p.box((2 * hw + 0.5, 0.36, 0.36), (0, y, h + 0.05), sw, grad=(0.2, 0.9))
		for s in (-1, 1):
			p.seg((s * (hw - 0.1), y, h - 0.6), (s * (hw - 0.8), y, h - 0.05), 0.07, 0.07, sw, sides=4)
	# rails out of the dark
	for k in range(9):
		y = dp - 0.3 - k * 0.55
		p.box((1.4, 0.2, 0.08), (0, y, 0.04), WOOD_GRAY, grad=(0.3, 0.9))
	for s in (-1, 1):
		p.box((0.06, 4.9, 0.08), (s * 0.48, dp - 2.6, 0.12), IRON, grad=(0.0, 0.5))
	# the lantern on its hook
	lx, ly = 0.9, -0.5
	p.seg((lx, -0.25, h - 0.1), (lx, ly, h - 0.1), 0.025, 0.025, IRON, sides=4)
	p.seg((lx, ly, h - 0.1), (lx, ly, h - 0.35), 0.015, 0.015, IRON, sides=4)
	p.box((0.22, 0.22, 0.05), (lx, ly, h - 0.37), IRON)
	p.box((0.18, 0.18, 0.26), (lx, ly, h - 0.52), FLAME, glow=2.0, grad=(0.0, 0.4))
	for dx, dy in ((-0.1, -0.1), (0.1, -0.1), (-0.1, 0.1), (0.1, 0.1)):
		p.seg((lx + dx, ly + dy, h - 0.66), (lx + dx, ly + dy, h - 0.38), 0.015, 0.015, IRON, sides=4)
	p.box((0.24, 0.24, 0.05), (lx, ly, h - 0.67), IRON)
	for x, y, sz in ((-2.0, -1.2, 0.5), (1.9, -1.5, 0.35), (-1.3, -2.0, 0.3)):   # rubble at the mouth
		p.rock((sz * 1.3, sz, sz * 0.7), (x, y, sz * 0.25), STONE_DARK, jitter=0.06)
	return p.build(bevel=0.04)


def basalt_house():
	"""A squat Forgehold dwelling: a KayKit 2 x 2 room (6 m square, walls 3 m)
	repainted in black basalt, its door in the front (-Y) wall, a window glowing
	orange on each side, a flat stone roof with a low parapet, and a stone
	chimney smoking (see-through smoke) with embers at its crown. About 7.2 x
	7.2 m, 5.6 m to the chimney top. Collide it as a mesh."""
	p = Prop("basalt_house", 456)
	half = 3.0
	p.box((2 * half + 0.8, 2 * half + 0.8, 0.45), (0, 0, 3.2), STONE_DARK, grad=(0.1, 0.9))     # the flat roof
	for s in (-1, 1):                                          # the parapet
		p.box((2 * half + 0.8, 0.35, 0.4), (0, s * (half + 0.22), 3.62), IRON, grad=(0.1, 0.7))
		p.box((0.35, 2 * half + 0.8, 0.4), (s * (half + 0.22), 0, 3.62), IRON, grad=(0.1, 0.7))
	for x in (-2.1, 2.1):                                      # water spouts
		p.box((0.2, 0.6, 0.18), (x, -half - 0.6, 3.3), IRON)
	cx, cy = 1.6, 1.5
	_block(p, (1.0, 1.0, 1.9), (cx, cy, 4.3), STONE_DARK, rough=0.03)
	p.box((1.2, 1.2, 0.2), (cx, cy, 5.3), STONE_LIGHT, grad=(0.0, 0.6))
	p.box((0.5, 0.5, 0.12), (cx, cy, 5.38), EMBER, glow=1.4)
	# window glow: a warm pane inside each side window
	for s in (-1, 1):
		p.box((0.1, 1.7, 1.7), (s * (half - 0.2), -1.5, 1.6), EMBER, glow=1.4, grad=(0.1, 0.5))
	p.box((0.5, 0.15, 0.1), (0.2, -half - 0.45, 2.6), EMBER, glow=1.0)   # a little ember lamp by the door
	obj = p.build(bevel=0.04)
	pieces = []
	for i, x in enumerate((-1.5, 1.5)):
		pieces += kaykit("wall_doorway" if i == 1 else "wall", (x, -half, 0.0), 0.0)
		pieces += kaykit("wall", (x, half, 0.0), math.pi)
	for s in (-1, 1):
		for i, y in enumerate((-1.5, 1.5)):
			pieces += kaykit("wall_window_open" if i == 0 else "wall", (s * half, y, 0.0), -s * math.pi / 2)
	for x in (-half, half):
		for y in (-half, half):
			pieces += kaykit("pillar", (x, y, 0.0))
	for x in (-1.5, 1.5):
		for y in (-1.5, 1.5):
			pieces += kaykit("floor_tile_large", (x, y, -0.07))
	obj = _merge_materials(join_into(obj, _restone(pieces, {**BASALT, (5, 0): STONE_DARK})))
	return join_into(obj, [_smoke("basalt_house_smoke", 457, (cx, cy, 5.7), 2.4, r=0.22, alpha=0.35)])


def agnavar_shrine():
	"""Forgehold's bindstone: Agnavar the Ember-Tusked, a basalt elephant about
	8.4 m to the flame on his brow, his tusks glowing like iron in the forge,
	standing on a pedestal at the back of a three-stepped octagonal plinth
	(11 m across, 1.05 m high) over a wide bowl of eternal fire at its front
	(-Y). Gold trim; four ember lamps on the plinth's corners. Collide it as a
	mesh or a box."""
	p = Prop("agnavar_shrine", 458)
	for k, (r, z0, z1, sw) in enumerate(((5.6, -0.2, 0.35, STONE_DARK), (4.8, 0.35, 0.7, STONE_LIGHT), (4.0, 0.7, 1.05, STONE_DARK))):
		p.seg((0, 0, z0), (0, 0, z1), r, r - 0.05, sw, sides=8, grad=(0.1, 0.9), twist=22.5)
		p.seg((0, 0, z1 - 0.16), (0, 0, z1 - 0.07), r + 0.04, r + 0.04, GOLD if k == 2 else IRON, sides=8, grad=(0.5, 1.0), twist=22.5)
	P = 1.05
	cy = 1.3
	p.box((3.4, 5.0, 1.3), (0, cy + 0.3, P + 0.65), IRON, grad=(0.1, 0.9))           # the statue's pedestal
	p.box((3.7, 5.3, 0.2), (0, cy + 0.3, P + 1.35), STONE_DARK, grad=(0.0, 0.7))
	p.box((3.76, 5.36, 0.1), (0, cy + 0.3, P + 1.1), GOLD, grad=(0.5, 1.0))
	B = P + 1.45
	p.blob((2.6, 3.9, 2.4), (0, cy + 0.6, B + 2.3), STONE_DARK, segs=(14, 10), grad=(0.05, 0.8))     # body
	for x in (-0.8, 0.8):
		for y in (-1.0, 1.6):
			p.seg((x, cy + y, B), (x, cy + y, B + 1.7), 0.5, 0.55, STONE_DARK, sides=8, grad=(0.2, 0.9))
			p.seg((x, cy + y, B), (x, cy + y, B + 0.18), 0.58, 0.58, GOLD, sides=8, grad=(0.0, 0.6))
	p.blob((2.68, 2.1, 2.48), (0, cy + 0.6, B + 2.32), CLOTH_RED, segs=(14, 10), grad=(0.1, 0.8))   # a red caparison round his middle
	p.blob((2.72, 0.2, 2.52), (0, cy - 0.45, B + 2.32), GOLD, segs=(14, 10), grad=(0.4, 1.0))     # its gold hems
	p.blob((2.72, 0.2, 2.52), (0, cy + 1.65, B + 2.32), GOLD, segs=(14, 10), grad=(0.4, 1.0))
	p.seg((0, cy + 2.4, B + 2.8), (0.1, cy + 2.8, B + 1.6), 0.09, 0.04, STONE_DARK, sides=5)     # tail
	hc = (0, cy - 1.9, B + 3.55)
	trunk = [(0, -0.4, -0.2), (0, -0.55, -0.6), (0, -0.5, -1.0), (0, -0.62, -1.3), (0, -0.85, -1.4)]
	_elephant_head(p, hc, 1.8, STONE_DARK, trunk=trunk, tusks=(False, False))
	for x in (-1, 1):                                          # the ember tusks, curving up
		a = (hc[0] + x * 0.45, hc[1] - 0.6, hc[2] - 0.6)
		b = (hc[0] + x * 0.65, hc[1] - 1.5, hc[2] - 1.0)
		c = (hc[0] + x * 0.55, hc[1] - 2.2, hc[2] - 0.5)
		_chain(p, [a, b, c], 0.16, 0.04, EMBER, sides=7, grad=(0.0, 0.5), glow=1.8)
		p.seg(a, (a[0], a[1] + 0.12, a[2] + 0.02), 0.2, 0.2, GOLD, sides=7)
	p.seg((0, hc[1] + 0.15, hc[2] + 0.9), (0, hc[1] + 0.05, hc[2] + 1.05), 0.55, 0.35, GOLD, sides=8, glow=0.25)   # brow band
	for k, (dx, h, r) in enumerate(((0.0, 1.1, 0.3), (0.2, 0.7, 0.2), (-0.2, 0.75, 0.2))):     # the flame on his brow
		base = (dx, hc[1] - 0.25, hc[2] + 0.95)
		p.seg(base, (dx * 1.2, hc[1] - 0.35, hc[2] + 0.95 + h), r, 0.0, FLAME, sides=6, grad=(0.1, 0.9), glow=1.8, twist=k * 20)
	p.blob((0.4, 0.3, 0.3), (0, hc[1] - 0.25, hc[2] + 1.0), EMBER, glow=1.6)
	# the bowl of eternal fire in front
	fy = -2.2
	p.seg((0, fy, P), (0, fy, P + 0.8), 0.9, 0.7, STONE_DARK, sides=8, grad=(0.1, 0.9), twist=22.5)
	bowl = _lathe(p, [(0.5, P + 0.75), (1.7, P + 1.0), (2.0, P + 1.45), (1.85, P + 1.5), (1.5, P + 1.15), (0.4, P + 0.95)], 16, IRON, grad=(0.0, 0.7))
	bowl.data.transform(Matrix.Translation((0, fy, 0)))
	rim = _lathe(p, [(1.84, P + 1.42), (2.06, P + 1.42), (2.06, P + 1.53), (1.84, P + 1.53)], 16, GOLD, grad=(0.4, 1.0))
	rim.data.transform(Matrix.Translation((0, fy, 0)))
	obj_fire = Prop("agnavar_shrine_fire", 459)
	_coals(obj_fire, (0, fy, P + 1.3), 3.2, 3.2, glow=1.5, flames=0)
	for k, (dx, dy, r, h) in enumerate(((0, 0, 0.7, 2.6), (0.6, 0.3, 0.45, 1.8), (-0.6, 0.2, 0.45, 1.7), (0.3, -0.6, 0.4, 1.5), (-0.4, -0.5, 0.35, 1.4))):
		obj_fire.seg((dx, fy + dy, P + 1.3), (dx * 0.6, fy + dy * 0.6, P + 1.3 + h), r, 0.0, FLAME, sides=6, grad=(0.05, 0.95), glow=1.6, twist=k * 30)
	for k in range(4):                                         # ember lamps on the plinth corners
		a = math.pi / 4 + k * math.pi / 2
		x, y = math.cos(a) * 3.7, math.sin(a) * 3.7
		p.seg((x, y, P), (x, y, P + 1.2), 0.24, 0.2, STONE_DARK, sides=8)
		p.seg((x, y, P + 1.2), (x, y, P + 1.45), 0.18, 0.36, IRON, sides=8)
		p.blob((0.5, 0.5, 0.25), (x, y, P + 1.45), EMBER, glow=1.4)
	obj = p.build(bevel=0.04)
	return join_into(obj, [obj_fire.build()])


def great_anvil():
	"""The Great Anvil of Forgehold's square: a ceremonial anvil of dark iron
	about 3.4 m long and 2.3 m tall on a two-stepped octagonal stone base
	(4.4 m across), banded in gold, a glowing ingot on its face and a great
	hammer laid at its foot. Collide it as a box."""
	p = Prop("great_anvil", 461)
	p.seg((0, 0, -0.2), (0, 0, 0.3), 2.2, 2.15, STONE_DARK, sides=8, grad=(0.1, 0.9), twist=22.5)
	p.seg((0, 0, 0.3), (0, 0, 0.7), 1.6, 1.55, STONE_LIGHT, sides=8, grad=(0.1, 0.8), twist=22.5)
	p.seg((0, 0, 0.55), (0, 0, 0.63), 1.6, 1.6, GOLD, sides=8, grad=(0.5, 1.0), twist=22.5)
	_anvil(p, (0, 0, 0.7), 2.6, IRON)
	p.box((0.8, 0.6, 0.1), (0, 0, 0.7 + 0.27 * 2.6), GOLD, grad=(0.0, 0.5))        # a gold band round the waist
	p.box((0.8, 0.3, 0.2), (-0.1, 0, 0.7 + 0.58 * 2.6 + 0.1), EMBER, glow=1.8, grad=(0.0, 0.5))   # the ingot, glowing
	p.box((0.6, 0.2, 0.1), (-0.1, 0, 0.7 + 0.58 * 2.6 + 0.2), FLAME, glow=2.2)
	p.box((0.4, 0.8, 0.4), (0.3, -1.25, 0.9), IRON, rot=(0, 0, 10), grad=(0.1, 0.8))         # the hammer at its foot
	p.seg((0.25, -1.25, 0.9), (1.6, -1.05, 0.8), 0.07, 0.07, WOOD, sides=6)
	p.seg((1.45, -1.07, 0.81), (1.62, -1.05, 0.8), 0.09, 0.09, GOLD, sides=6)
	return p.build(bevel=0.03)


def lava_trough():
	"""A 6 m length of Forgehold's lava channel along X, open at both ends so
	lengths chain end to end: glowing lava 1.2 m wide in a stone bed between
	two low stone walls (0.55 m tall, 0.45 m thick), a crust of darker slag
	floating on it. 2.1 m wide overall. Collide it as a box (you can't wade it)."""
	p = Prop("lava_trough", 462)
	L, w = 6.0, 0.6
	p.box((L, 2 * w + 0.9, 0.3), (0, 0, -0.1), STONE_DARK, grad=(0.4, 1.0))
	for s in (-1, 1):
		for k in range(4):
			x = -L / 2 + 0.75 + k * 1.5
			p.box((1.5 - 0.04, 0.45, 0.5), (x, s * (w + 0.225), 0.25), STONE_DARK if k % 2 else STONE_LIGHT, grad=(0.1, 0.9))
		p.box((L, 0.55, 0.1), (0, s * (w + 0.225), 0.53), IRON, grad=(0.0, 0.6))
	p.box((L, 2 * w, 0.1), (0, 0, 0.25), EMBER, glow=1.8, grad=(0.2, 0.6))
	for k in range(9):                                         # brighter flows and dark slag crusts
		x = -L / 2 + 0.4 + k * 0.65
		p.box((0.9, 0.12, 0.03), (x, p.rng.uniform(-0.4, 0.4), 0.31), FLAME, glow=2.2, rot=(0, 0, p.rng.uniform(-8, 8)))
		if k % 2:
			p.blob((0.45, 0.3, 0.07), (x + 0.3, p.rng.uniform(-0.35, 0.35), 0.31), IRON, segs=(6, 3), grad=(0.3, 0.9))
	return p.build(bevel=0.03)


# ---- Dawnwatch (the Dawn-Tusk's fortress on the snowy ridge)

WARM_STONE = {(1, 0): STONE_WARM, (0, 0): WOOD_GRAY}   # KayKit's pale wall stone -> warm, its trim -> warm dark
SNOW = CLOTH_WHITE


def _kaykit_run(pieces, a, b, z0, rows, row_h, depth=0.75, kinds=None, size=3.0):
	"""KayKit wall pieces from a to b (x, y), `rows` courses of `row_h` meters
	from z0, each about `size` wide. Going round a building counterclockwise
	(seen from above) the pieces' fronts face out. `kinds(row, k)` picks each piece."""
	a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
	d = b - a
	n = max(1, round(d.length / size))
	w = d.length / n
	yaw = math.atan2(d.y, d.x)
	for r in range(rows):
		for k in range(n):
			c = a + d * ((k + 0.5) / n)
			pieces += kaykit(kinds(r, k) if kinds else "wall", (c.x, c.y, z0 + r * row_h), yaw, (w / 4, depth, row_h / 4))
	return pieces


def _kaykit_box(pieces, x0, y0, x1, y1, z0, rows, row_h, kinds=None, corners=True):
	"""KayKit walls round a rectangle, fronts out; `kinds(side, row, k)`,
	side 0 = front (-Y), 1 = right (+X), 2 = back, 3 = left. Pillars on the corners."""
	ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
	for s in range(4):
		_kaykit_run(pieces, ring[s], ring[(s + 1) % 4], z0, rows, row_h, kinds=(lambda r, k, s=s: kinds(s, r, k)) if kinds else None)
	if corners:
		for x, y in ring:
			for r in range(rows):
				pieces += kaykit("pillar", (x, y, z0 + r * row_h), 0.0, (0.62, 0.62, row_h / 4))
	return pieces


def _snowcap(p, size, loc, rot=(0, 0, 0)):
	"""A soft cushion of snow lying on a ledge (size = its footprint and depth)."""
	sx, sy, sz = size
	p.blob((sx * 1.04, sy * 1.06, sz * 2), loc, SNOW, rot=rot, segs=(10, 5), grad=(0.0, 0.35), jitter=0.02)


def _sun_disc(p, c, r, glow=0.35, rays=12, depth=0.08, face=-1):
	"""The Dawn-Tusk's gilded sun on a wall facing -Y (face -1) or +Y: a disc and its rays."""
	x, y, z = c
	p.seg((x, y, z), (x, y + face * depth, z), r, r, GOLD, sides=16, grad=(0.0, 0.5), glow=glow)
	p.seg((x, y + face * depth, z), (x, y + face * depth * 1.6, z), r * 0.55, r * 0.5, GOLD, sides=12, grad=(0.0, 0.4), glow=glow)
	for k in range(rays):
		a = k * math.tau / rays
		ln = 1.7 if k % 2 == 0 else 1.4
		p.seg((x + math.cos(a) * r * 0.95, y + face * depth * 0.5, z + math.sin(a) * r * 0.95),
			  (x + math.cos(a) * r * ln, y + face * depth * 0.5, z + math.sin(a) * r * ln), r * 0.16, 0.0, GOLD, sides=4, grad=(0.0, 0.5), glow=glow)


def _merlons(p, x0, x1, y, z, h=1.1, w=0.9, gap=0.7, depth=0.6, snow=True):
	"""A row of merlons along X at depth y on a parapet top z, snow on each."""
	n = max(1, int((x1 - x0 + gap) / (w + gap)))
	span = n * w + (n - 1) * gap
	start = (x0 + x1) / 2 - span / 2
	for k in range(n):
		x = start + k * (w + gap) + w / 2
		p.box((w, depth, h), (x, y, z + h / 2), STONE_WARM, grad=(0.0, 0.7))
		if snow:
			_snowcap(p, (w, depth, 0.1), (x, y, z + h + 0.02))


def _banner_hang(p, x, y, z, w, h, face=-1):
	"""A long white-and-gold banner of the Dawn-Tusk hung flat on a wall from z down."""
	p.seg((x - w / 2 - 0.15, y + face * 0.12, z), (x + w / 2 + 0.15, y + face * 0.12, z), 0.05, 0.05, WOOD, sides=5)
	p.box((w, 0.05, h), (x, y + face * 0.16, z - h / 2 - 0.05), CLOTH_WHITE, grad=(0.05, 0.5))
	p.box((w + 0.02, 0.06, 0.18), (x, y + face * 0.17, z - 0.2), GOLD, grad=(0.0, 0.5))
	p.poly([(x - w / 2, y + face * 0.16, z - h - 0.05), (x + w / 2, y + face * 0.16, z - h - 0.05), (x, y + face * 0.16, z - h - 0.55)],
		   [(0, 1, 2)], CLOTH_WHITE, grad=(0.3, 0.6))
	_sun_disc(p, (x, y + face * 0.18, z - h * 0.45), w * 0.26, glow=0.2, rays=8, depth=0.03, face=face)


def fortress_wall():
	"""A 12 m run of Dawnwatch's curtain wall along X, open at both ends so
	runs chain end to end: KayKit wall pieces (warm stone) in two 3 m courses
	on both faces over a battered stone footing, 3.6 m thick, the wall-walk at
	7.2 m, snow-capped merlons on the outer face (-Y) with arrow slits under
	them, a low parapet on the inner face, a gilded string course and a
	white-and-gold banner. 9.0 m to the merlon tops. Collide it as a box
	(12 x 3.6 x 8.3 m)."""
	p = Prop("fortress_wall", 481)
	L, hy, base = 12.0, 1.4, 1.2
	for s in (-1, 1):                                         # the battered footing
		verts = [(-L / 2, s * (hy + 0.9), 0), (L / 2, s * (hy + 0.9), 0), (L / 2, s * (hy + 0.35), base), (-L / 2, s * (hy + 0.35), base),
				 (-L / 2, 0, 0), (L / 2, 0, 0), (L / 2, 0, base), (-L / 2, 0, base)]
		p.poly(verts, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)], STONE_WARM, grad=(0.3, 1.0))
		for k in range(8):
			x = -L / 2 + 0.75 + k * 1.5
			p.box((1.4, 0.2, 0.28), (x + p.rng.uniform(-0.1, 0.1), s * (hy + 0.66), 0.55), WOOD_GRAY, rot=(s * 25, 0, 0), grad=(0.2, 0.8))
	p.box((L, 2 * hy, 6.0), (0, 0, base + 3.0), STONE_WARM, grad=(0.3, 1.0))  # the core
	top = base + 6.0
	p.box((L, 2 * hy + 1.0, 0.3), (0, 0, top + 0.15), STONE_DARK, grad=(0.3, 0.9))     # the wall-walk
	p.box((L, 0.25, 0.3), (0, -hy - 0.42, top - 0.9), GOLD, grad=(0.05, 0.5))          # gilded string course
	p.box((L, 0.7, 0.55), (0, -hy - 0.15, top + 0.57), STONE_WARM, grad=(0.1, 0.8))    # outer parapet
	_merlons(p, -L / 2, L / 2, -hy - 0.15, top + 0.85, h=1.1)
	for k in range(7):                                          # slits through the merlons
		x = -L / 2 + 0.95 + k * 1.6
		if abs(x) < L / 2 - 0.4:
			p.box((0.14, 0.2, 0.7), (x, -hy - 0.52, top + 1.35), IRON)
	p.box((L, 0.5, 0.9), (0, hy + 0.25, top + 0.6), STONE_WARM, grad=(0.1, 0.8))       # inner parapet
	_snowcap(p, (L, 0.5, 0.1), (0, hy + 0.25, top + 1.06))
	for k in range(6):                                          # snow drifted on the wall-walk
		_snowcap(p, (p.rng.uniform(1.2, 2.4), 0.9, 0.08), (-L / 2 + 1.1 + k * 2.0, p.rng.uniform(-0.6, 0.6), top + 0.3))
	for x in (-L / 2 + 0.3, L / 2 - 0.3):                       # pilaster buttresses at the joints, outside
		p.box((0.9, 0.7, top - 0.2), (x, -hy - 0.6, (top - 0.2) / 2 + 0.1), STONE_WARM, grad=(0.1, 0.9))
		_snowcap(p, (0.9, 0.7, 0.08), (x, -hy - 0.6, top))
	_banner_hang(p, 0, -hy - 0.38, top - 1.2, 1.3, 3.4)
	obj = p.build(bevel=0.05)
	walls = []
	_kaykit_run(walls, (-L / 2, -hy), (L / 2, -hy), base, 2, 3.0, )
	_kaykit_run(walls, (L / 2, hy), (-L / 2, hy), base, 2, 3.0)
	return _merge_materials(join_into(obj, _restone(walls, WARM_STONE)))


def _arch_ring(p, y0, y1, zc, r0, r1, n=9, swatches=(STONE_LIGHT, STONE_WARM)):
	"""A round arch of n voussoirs over x = 0 between depths y0 and y1:
	a half ring from radius r0 to r1 round (0, zc)."""
	for k in range(n):
		a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
		pts = [(math.cos(a0) * r0, math.sin(a0) * r0), (math.cos(a0) * r1, math.sin(a0) * r1),
			   (math.cos(a1) * r1, math.sin(a1) * r1), (math.cos(a1) * r0, math.sin(a1) * r0)]
		verts = [(x, y0, zc + z) for x, z in pts] + [(x, y1, zc + z) for x, z in pts]
		p.poly(verts, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
			   swatches[k % len(swatches)], grad=(0.05, 0.8))


def _vault(p, hw, zc, y0, y1, top, n=12, swatch=STONE_WARM):
	"""Fill above a round-arched passage (half-width hw, arch centre zc) up to
	`top`, between depths y0 and y1: the stone the arch is cut from."""
	for k in range(n):
		xa, xb = -hw + 2 * hw * k / n, -hw + 2 * hw * (k + 1) / n
		x = (xa + xb) / 2
		z = zc + math.sqrt(max(0.0, hw * hw - x * x))
		p.box((xb - xa + 0.02, y1 - y0, top - z), (x, (y0 + y1) / 2, z + (top - z) / 2), swatch, grad=(0.1, 0.9))


def fortress_gatehouse():
	"""Dawnwatch's gatehouse along X, 19.5 m wide and 7.6 m deep: a 6 m wide
	round-arched passage (5.8 m to the crown) through a stone span, square
	towers of KayKit wall pieces either side rising to 12.3 m at the merlons,
	the gold sun of the Dawn-Tusk over the arch, the gate leaves standing open
	against the passage walls, banners, snow on every ledge. fortress_wall runs
	meet its ends at x = +-9.5 (put a run's centre at x = +-15.5). Faces -Y.
	Collide it as a mesh: the passage is walkable."""
	p = Prop("fortress_gatehouse", 482)
	hw, T, hd = 3.0, 6.5, 3.8          # half the passage, tower width, half depth
	zc = 2.8                           # the arch's centre: crown at 5.8
	H, S = 11.0, 8.2                   # tower top, span top
	for s in (-1, 1):
		cx = s * (hw + T / 2)
		p.box((T - 0.8, 2 * hd - 0.8, H), (cx, 0, H / 2), STONE_WARM, grad=(0.3, 1.0))    # tower cores
		p.box((T + 0.8, 2 * hd + 0.8, 0.9), (cx, 0, 0.3), STONE_WARM, grad=(0.3, 1.0))    # plinths
		p.box((T + 0.5, 2 * hd + 0.5, 0.35), (cx, 0, H + 0.18), STONE_DARK, grad=(0.2, 0.9))
		for sy in (-1, 1):
			p.box((T + 0.55, 0.25, 0.3), (cx, sy * (hd + 0.28), H - 0.7), GOLD, grad=(0.05, 0.5))
			_merlons(p, cx - T / 2 - 0.1, cx + T / 2 + 0.1, sy * (hd + 0.02), H + 0.35, h=1.15, depth=0.55)
		for k in range(3):                                        # merlons along the tower sides
			for sx in (-1, 1):
				y = -hd + 1.9 + k * 1.9
				p.box((0.55, 0.9, 1.15), (cx + sx * (T / 2 + 0.02), y, H + 0.35 + 0.575), STONE_WARM, grad=(0.0, 0.7))
				_snowcap(p, (0.55, 0.9, 0.1), (cx + sx * (T / 2 + 0.02), y, H + 1.52))
		_snowcap(p, (T - 1.4, 2 * hd - 1.6, 0.14), (cx, 0, H + 0.36))
		for z in (3.6, 7.2):                                       # arrow slits
			p.box((0.16, 0.2, 1.1), (cx, -hd - 0.4, z), IRON)
		_banner_hang(p, cx, -hd - 0.4, H - 1.3, 1.4, 4.2)
	# the span over the passage, the arch cut through it
	_vault(p, hw, zc, -hd + 0.3, hd - 0.3, S)
	p.box((2 * hw + 0.2, 2 * hd + 0.2, 0.35), (0, 0, S + 0.18), STONE_DARK, grad=(0.2, 0.9))
	for sy in (-1, 1):
		p.box((2 * hw + 0.2, 0.55, 0.3), (0, sy * (hd - 0.18), S - 0.9), GOLD, grad=(0.05, 0.5))
		_merlons(p, -hw, hw, sy * (hd - 0.2), S + 0.35, h=0.95, depth=0.55)
		_arch_ring(p, sy * (hd - 0.3), sy * (hd + 0.15), zc, hw, hw + 0.75)
		p.box((0.9, 0.5, 0.9), (0, sy * (hd - 0.05), zc + hw + 0.4), GOLD, grad=(0.0, 0.5))   # the keystone
	for sy in (-1, 1):                                             # the span's face walls round the arch
		p.box((2 * hw, 0.3, S - zc - hw - 0.75 + 0.1), (0, sy * (hd - 0.45), (S + zc + hw + 0.75) / 2), STONE_WARM, grad=(0.1, 0.9))
	_snowcap(p, (2 * hw - 0.4, 2 * hd - 1.4, 0.12), (0, 0, S + 0.36))
	_sun_disc(p, (0, -hd - 0.1, zc + hw + 1.75), 0.75, glow=0.45)
	for k in range(7):                                             # the portcullis' teeth under the front arch
		x = -1.8 + k * 0.6
		z = zc + math.sqrt(hw * hw - x * x)
		p.seg((x, -hd + 0.6, z + 0.05), (x, -hd + 0.6, z - 0.55), 0.06, 0.0, IRON, sides=4)
	p.box((2 * hw, 0.12, 0.12), (0, -hd + 0.6, zc + hw - 0.1), IRON)
	for s in (-1, 1):                                              # the open gate leaves
		p.box((0.25, 2.8, 3.4), (s * (hw - 0.18), 0.9, 1.75), WOOD, grad=(0.2, 1.0))
		for z in (0.8, 2.6):
			p.box((0.3, 2.85, 0.2), (s * (hw - 0.18), 0.9, z), IRON)
		p.blob((0.22, 0.22, 0.22), (s * (hw - 0.36), 0.2, 1.7), GOLD, segs=(6, 4))
		_snowcap(p, (0.8, 1.4, 0.2), (s * (hw - 0.45), -hd - 0.2, 0.05))
	p.box((2 * hw, 2 * hd + 1.2, 0.1), (0, 0, 0.02), STONE_DARK, grad=(0.5, 0.9))        # threshold
	obj = p.build(bevel=0.05)
	walls = []
	for s in (-1, 1):
		cx = s * (hw + T / 2)
		_kaykit_box(walls, cx - T / 2, -hd, cx + T / 2, hd, 0.75, 3, 3.4,
					kinds=lambda side, r, k: "wall_window_open" if r == 2 and k == 1 and side != 0 else "wall")
	return _merge_materials(join_into(obj, _restone(walls, WARM_STONE)))


def fortress_keep():
	"""Dawnwatch's keep, 16 x 14 m: three courses of KayKit wall (warm stone,
	windows in the upper course, a doorway at the front with its oak door shut)
	to 10.4 m, battlements and a round snow-capped turret at each corner, and
	a 7 m square tower rising from the middle to 19.5 m, a gilded pyramid roof
	and a sun finial on it (25 m to the tip). A white-and-gold banner either
	side of the door, a stone stair up to it. Faces -Y. Collide it as a box
	(16 x 14 x 10.4, the tower 7 x 7 to 19.5)."""
	p = Prop("fortress_keep", 483)
	hx, hy, base, rows, rh = 8.0, 7.0, 0.8, 3, 3.2
	top = base + rows * rh
	p.box((2 * hx + 1.0, 2 * hy + 1.0, base + 0.2), (0, 0, base / 2 - 0.1), STONE_WARM, grad=(0.3, 1.0))   # plinth
	p.box((2 * hx - 0.8, 2 * hy - 0.8, top - base), (0, 0, (top + base) / 2), IRON, grad=(0.4, 1.0))     # dark core behind the windows
	p.box((2 * hx + 0.5, 2 * hy + 0.5, 0.35), (0, 0, top + 0.17), STONE_DARK, grad=(0.2, 0.9))
	for sy in (-1, 1):
		p.box((2 * hx + 0.55, 0.25, 0.3), (0, sy * (hy + 0.3), top - 0.6), GOLD, grad=(0.05, 0.5))
		_merlons(p, -hx + 1.3, hx - 1.3, sy * (hy + 0.02), top + 0.35, h=1.1, depth=0.55)
	for sx in (-1, 1):
		p.box((0.25, 2 * hy + 0.55, 0.3), (sx * (hx + 0.3), 0, top - 0.6), GOLD, grad=(0.05, 0.5))
		for k in range(5):
			y = -hy + 2.6 + k * 2.2
			p.box((0.55, 0.9, 1.1), (sx * (hx + 0.02), y, top + 0.9), STONE_WARM, grad=(0.0, 0.7))
			_snowcap(p, (0.55, 0.9, 0.1), (sx * (hx + 0.02), y, top + 1.47))
	_snowcap(p, (2 * hx - 1.6, 2 * hy - 1.6, 0.14), (0, 0, top + 0.36))
	for sx in (-1, 1):                                              # corner turrets
		for sy in (-1, 1):
			x, y = sx * hx, sy * hy
			p.seg((x, y, 0.0), (x, y, top + 1.2), 1.5, 1.4, STONE_WARM, sides=12, grad=(0.05, 0.9))
			for z in (base + rh, base + 2 * rh):
				p.seg((x, y, z - 0.12), (x, y, z + 0.12), 1.56, 1.56, WOOD_GRAY, sides=12, grad=(0.1, 0.6))
			p.seg((x, y, top + 1.2), (x, y, top + 1.6), 1.7, 1.7, STONE_WARM, sides=12, grad=(0.0, 0.6))
			for k in range(6):                                        # little merlons round the turret
				a = k * math.tau / 6 + 0.3
				p.box((0.55, 0.45, 0.8), (x + math.cos(a) * 1.45, y + math.sin(a) * 1.45, top + 2.0), STONE_WARM, rot=(0, 0, math.degrees(a)), grad=(0.0, 0.7))
				_snowcap(p, (0.55, 0.45, 0.08), (x + math.cos(a) * 1.45, y + math.sin(a) * 1.45, top + 2.42), rot=(0, 0, math.degrees(a)))
			p.seg((x, y, top + 1.6), (x, y, top + 4.2), 1.4, 0.0, CLAY, sides=12, grad=(0.0, 0.9))
			_snowcap(p, (1.9, 1.9, 0.25), (x, y, top + 2.1))
			p.box((0.14, 0.2, 1.0), (x + sx * 0.6, y - 1.4 if sy < 0 else y + 1.4, base + rh * 1.5), IRON)
	# the central tower
	tw, tt = 3.5, 19.5
	p.box((2 * tw - 0.6, 2 * tw - 0.6, tt - top), (0, 1.0, (tt + top) / 2), STONE_WARM, grad=(0.05, 0.9))
	for z in (top + 3.0, tt - 0.6):
		p.box((2 * tw + 0.1, 2 * tw + 0.1, 0.3), (0, 1.0, z), GOLD if z > top + 4 else WOOD_GRAY, grad=(0.05, 0.6))
	for sx, sy in ((0, -1), (0, 1), (-1, 0), (1, 0)):              # tall windows, dark inside
		p.box((0.9 if sy else 0.2, 0.2 if sy else 0.9, 2.2), (sx * (tw - 0.25), 1.0 + sy * (tw - 0.25), top + 5.2), IRON)
	for k in range(4):
		for s in (-1, 1):
			x = -tw + 0.9 + k * (2 * tw - 1.8) / 3
			p.box((0.8, 0.5, 0.9), (x, 1.0 + s * (tw - 0.05), tt + 0.45), STONE_WARM, grad=(0.0, 0.7))
			p.box((0.5, 0.8, 0.9), (s * (tw - 0.05), 1.0 - tw + 0.9 + k * (2 * tw - 1.8) / 3, tt + 0.45), STONE_WARM, grad=(0.0, 0.7))
	p.seg((0, 1.0, tt), (0, 1.0, tt + 4.3), (tw - 0.3) * 1.414, 0.0, GOLD, sides=4, grad=(0.0, 0.9), twist=45)   # gilded pyramid roof
	p.seg((0, 1.0, tt + 4.1), (0, 1.0, tt + 4.9), 0.08, 0.08, GOLD, sides=6)
	_sun_disc(p, (0, 1.0, tt + 5.3), 0.45, glow=0.5, rays=10, depth=0.06)
	_sun_disc(p, (0, 1.0 - tw - 0.15, top + 5.2 + 2.0), 0.8, glow=0.45)
	# the door, its stair and banners
	p.box((2.6, 0.3, 3.2), (0, -hy - 0.05, base + 1.6), WOOD, grad=(0.2, 1.0))
	for z in (base + 0.7, base + 2.4):
		p.box((2.7, 0.36, 0.18), (0, -hy - 0.07, z), IRON)
	p.blob((0.22, 0.2, 0.22), (0.7, -hy - 0.28, base + 1.5), GOLD, segs=(6, 4))
	for k in range(3):
		p.box((3.6 - k * 0.3, 0.7, 0.28), (0, -hy - 0.85 - (2 - k) * 0.7, 0.14 + k * 0.28), STONE_WARM, grad=(0.1, 0.8))
	for s in (-1, 1):
		_banner_hang(p, s * 3.4, -hy - 0.4, top - 0.9, 1.4, 4.6)
	obj = p.build(bevel=0.05)
	walls = []
	_kaykit_box(walls, -hx, -hy, hx, hy, base, rows, rh, corners=False,
				kinds=lambda side, r, k: ("wall_doorway" if side == 0 and r == 0 and k == 2 else
										  "wall_window_open" if r == 2 and k % 2 == 1 else "wall"))
	return _merge_materials(join_into(obj, _restone(walls, WARM_STONE)))


def dawn_beacon():
	"""Dawnwatch's great beacon: a square stone tower tapering from 4.4 m to
	3.4 m, bound with gilded bands, a gold sun on its face (-Y), a crenellated
	platform at 10.6 m and on it a huge iron fire basket heaped with burning
	logs, its flames reaching 14.8 m. Always lit. Collide it as a box (4.8 x
	4.8 x 12)."""
	p = Prop("dawn_beacon", 484)
	H = 10.2
	p.box((5.4, 5.4, 0.8), (0, 0, 0.3), STONE_WARM, grad=(0.3, 1.0))
	p.seg((0, 0, 0.6), (0, 0, H), 2.2 * 1.414, 1.7 * 1.414, STONE_WARM, sides=4, grad=(0.05, 0.9), twist=45)
	for k in range(9):                                             # courses of darker stone
		z = 1.2 + k * 1.0
		w = 2.2 - (z - 0.6) / (H - 0.6) * 0.5
		for s in (-1, 1):
			x = p.rng.uniform(-w + 0.6, w - 0.6)
			p.box((p.rng.uniform(0.6, 1.2), 0.08, 0.35), (x, s * (w + 0.01), z), WOOD_GRAY, grad=(0.3, 0.6))
			p.box((0.08, p.rng.uniform(0.6, 1.2), 0.35), (s * (w + 0.01), p.rng.uniform(-w + 0.6, w - 0.6), z + 0.5), WOOD_GRAY, grad=(0.3, 0.6))
	for z in (3.2, 6.8):
		w = 2.2 - (z - 0.6) / (H - 0.6) * 0.5
		p.seg((0, 0, z - 0.15), (0, 0, z + 0.15), (w + 0.1) * 1.414, (w + 0.1) * 1.414, GOLD, sides=4, grad=(0.05, 0.5), twist=45)
	_sun_disc(p, (0, -1.92, 5.0), 0.7, glow=0.45)
	p.box((0.7, 0.3, 1.9), (0, -2.12, 1.55), WOOD, grad=(0.2, 1.0))          # a small door at the foot
	p.box((0.9, 0.34, 0.2), (0, -2.14, 2.55), STONE_LIGHT)
	# the platform
	p.box((4.8, 4.8, 0.45), (0, 0, H + 0.2), STONE_DARK, grad=(0.2, 0.9))
	for s in (-1, 1):
		for k in range(4):
			c = -1.8 + k * 1.2
			p.box((0.7, 0.45, 0.8), (c, s * 2.18, H + 0.8), STONE_WARM, grad=(0.0, 0.7))
			p.box((0.45, 0.7, 0.8), (s * 2.18, c, H + 0.8), STONE_WARM, grad=(0.0, 0.7))
			_snowcap(p, (0.7, 0.45, 0.08), (c, s * 2.18, H + 1.21))
			_snowcap(p, (0.45, 0.7, 0.08), (s * 2.18, c, H + 1.21))
		p.box((4.9, 0.3, 0.25), (0, s * 2.35, H - 0.05), GOLD, grad=(0.05, 0.5))
	# the fire basket
	b0 = H + 0.4
	for k in range(4):                                             # iron legs
		a = k * math.tau / 4 + math.pi / 4
		p.seg((math.cos(a) * 1.3, math.sin(a) * 1.3, b0), (math.cos(a) * 0.9, math.sin(a) * 0.9, b0 + 0.9), 0.1, 0.09, IRON, sides=5)
	_lathe(p, [(0.03, b0 + 0.8), (0.9, b0 + 0.8), (1.55, b0 + 1.6), (1.7, b0 + 2.05), (1.55, b0 + 2.05), (0.8, b0 + 1.1), (0.03, b0 + 1.05)], 14, IRON, grad=(0.03, 0.7))
	for k in range(12):                                            # the cage's upright bars
		a = k * math.tau / 12
		p.seg((math.cos(a) * 1.55, math.sin(a) * 1.55, b0 + 1.6), (math.cos(a) * 1.72, math.sin(a) * 1.72, b0 + 2.45), 0.05, 0.05, IRON, sides=4)
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * 1.72, math.sin(a) * 1.72, b0 + 2.5), IRON, segs=(5, 4))
	_hoops(p, (0, 0, 0), 1.72, [b0 + 2.4], IRON, w=0.08)
	_coals(p, (0, 0, b0 + 1.9), 2.7, 2.7, glow=2.0, flames=0)
	for k in range(7):                                             # burning logs heaped in the basket
		a = k * math.tau / 7 + 0.2
		p.seg((math.cos(a) * 1.2, math.sin(a) * 1.2, b0 + 1.95), (math.cos(a + 2.4) * 0.5, math.sin(a + 2.4) * 0.5, b0 + 2.4), 0.14, 0.12, IRON, sides=5)
	for loc, rr, fh in (((0, 0), 1.1, 3.2), ((0.6, 0.35), 0.6, 2.2), ((-0.55, 0.4), 0.6, 2.0), ((0.2, -0.65), 0.55, 1.9),
						((-0.45, -0.45), 0.5, 1.7), ((0.75, -0.3), 0.4, 1.4), ((-0.8, 0.0), 0.4, 1.3)):
		z = b0 + 2.1
		p.seg((loc[0], loc[1], z), (loc[0] * 1.1, loc[1] * 1.1, z + fh), rr, 0.0, FLAME, sides=7, grad=(0.1, 0.95), glow=2.2, twist=fh * 40)
	p.seg((0, 0, b0 + 2.1), (0, 0, b0 + 2.1 + 2.0), 0.7, 0.0, PETAL_YELLOW, sides=6, grad=(0.0, 0.6), glow=3.0, twist=20)
	return p.build(bevel=0.04)


def _log(p, a, b, r, swatch=WOOD_GRAY, rough=0.02):
	"""A rough log from a to b, its bark knobbly, a pale cut at each end."""
	p.seg(a, b, r, r * 0.92, swatch, sides=7, grad=(0.2, 0.9), jitter=rough, twist=p.rng.uniform(0, 50))
	a, b = Vector(a), Vector(b)
	d = (b - a).normalized()
	for e, s in ((a, -1), (b, 1)):
		p.seg(e, e + d * s * 0.04, r * 0.85, r * 0.8, BAMBOO, sides=7, grad=(0.0, 0.5))


def _lashing(p, c, r, axis=(0, 0, 1), turns=3):
	"""A few turns of rope binding logs at c."""
	c, ax = Vector(c), Vector(axis).normalized()
	for k in range(turns):
		off = ax * (k - (turns - 1) / 2) * 0.06
		p.seg(c + off - ax * 0.02, c + off + ax * 0.02, r, r, HIDE, sides=8, grad=(0.1, 0.6))


def _wheel_log(p, x, y, z, r, w=0.35, swatch=WOOD):
	"""A crude solid wheel: a slice of a great log on an axle along X."""
	p.seg((x - w / 2, y, z), (x + w / 2, y, z), r, r, swatch, sides=10, grad=(0.2, 0.9), jitter=0.02)
	for s in (-1, 1):
		p.seg((x + s * w / 2, y, z), (x + s * (w / 2 + 0.03), y, z), r * 0.8, r * 0.75, BAMBOO, sides=10, grad=(0.0, 0.6))
	p.seg((x - w / 2 - 0.12, y, z), (x + w / 2 + 0.12, y, z), 0.1, 0.1, IRON, sides=6)


def siege_catapult():
	"""An ogre-built catapult of rough logs and rope, throwing toward -Y: a
	log frame 3.2 x 5 m on four crude slab wheels, an A-frame of logs lashed
	at the top, the throwing arm (a whole tree trunk) cocked back over the
	rear with a hide sling heaped with a boulder, a crossbar the arm strikes,
	rope skeins, a bear skull nailed to the front. About 3.6 x 6.2 m, 4.4 m
	tall. Collide it as a box."""
	p = Prop("siege_catapult", 485)
	hx, hy, zf = 1.4, 2.5, 0.95
	for x in (-hx, hx):                                            # the frame's side rails
		_log(p, (x, -hy - 0.3, zf), (x, hy + 0.3, zf), 0.24)
	for y in (-hy + 0.2, 0.2, hy - 0.2):                           # cross logs
		_log(p, (-hx - 0.35, y, zf + 0.3), (hx + 0.35, y, zf + 0.3), 0.2)
		for x in (-hx, hx):
			_lashing(p, (x, y, zf + 0.15), 0.3, axis=(0, 1, 0))
	for x in (-hx - 0.35, hx + 0.35):                              # wheels
		for y in (-hy + 0.6, hy - 0.6):
			_wheel_log(p, x * 1.2, y, 0.62, 0.62, 0.35)
	# the A-frame and the crossbar the arm strikes
	top = 3.7
	for x in (-hx, hx):
		_log(p, (x, -1.2, zf + 0.2), (x * 0.9, 0.0, top), 0.18)
		_log(p, (x, 1.2, zf + 0.2), (x * 0.9, 0.0, top), 0.18)
		_lashing(p, (x * 0.9, 0.0, top - 0.1), 0.24, axis=(1, 0, 0))
	_log(p, (-hx - 0.4, -0.05, top), (hx + 0.4, -0.05, top), 0.22)
	p.blob((1.6, 0.5, 0.4), (0, -0.25, top + 0.05), HIDE, segs=(8, 5), grad=(0.1, 0.7))     # a padded hide on the bar
	# the pivot, the rope skein and the cocked arm
	pz = zf + 0.55
	_log(p, (-hx - 0.2, 0.9, pz), (hx + 0.2, 0.9, pz), 0.16)
	for x in (-0.55, 0.55):
		p.seg((x, 0.9, pz - 0.25), (x, 0.9, pz + 0.25), 0.3, 0.3, HIDE, sides=10, grad=(0.1, 0.8))
	arm_end = Vector((0, 3.9, 1.9))
	_log(p, (0, 0.9, pz), tuple(arm_end), 0.2)
	sling = arm_end + Vector((0, 0.25, 0.25))
	_lathe(p, [(0.03, -0.1), (0.55, -0.02), (0.72, 0.3), (0.62, 0.32), (0.03, 0.08)], 10, HIDE, grad=(0.1, 0.8)).data.transform(Matrix.Translation(sling))
	p.rock((0.95, 0.9, 0.8), tuple(sling + Vector((0, 0, 0.55))), STONE_DARK)
	for s in (-1, 1):                                              # ropes holding the arm cocked
		_rope(p, (s * 0.15, 3.3, 1.8), (s * hx, hy + 0.1, zf + 0.2), 0.12, r=0.035)
	# bits of ogre work: a skull, spikes, a spare stone
	_skull(p, (0, -hy - 0.52, zf + 0.25), s=2.4)
	for x in (-hx, hx):
		p.seg((x, -hy - 0.3, zf), (x * 1.05, -hy - 1.0, zf + 0.35), 0.1, 0.0, WOOD_GRAY, sides=5)
	for k, (x, y) in enumerate(((1.9, 2.4), (2.2, 1.5), (1.6, 3.2))):
		p.rock((0.8, 0.75, 0.65), (x, y, 0.3), STONE_DARK)
	return p.build(bevel=0.03)


def siege_ram():
	"""A covered battering ram: a timber frame 2.8 x 7 m on six slab wheels
	under a steep roof of planks shingled with raw hides and pelts, the ram (a
	great log with an iron boar-head cap) slung from chains and poking 1.4 m
	out of the front (-Y). About 3.4 x 8.4 m, 3.9 m tall. Collide it as a box."""
	p = Prop("siege_ram", 486)
	hx, hy, zb = 1.4, 3.5, 0.9
	for x in (-hx, hx):
		_beam(p, (x, -hy, zb), (x, hy, zb), 0.16, WOOD)
		for y in (-hy + 0.2, 0.0, hy - 0.2):
			_beam(p, (x, y, zb), (x, y, 2.5), 0.13, WOOD)
			_wheel_log(p, x * 1.15, y * 0.85, 0.6, 0.6, 0.3)
		_beam(p, (x, -hy, 2.5), (x, hy, 2.5), 0.13, WOOD)
	for y in (-hy + 0.2, 0.0, hy - 0.2):
		_beam(p, (-hx, y, zb), (hx, y, zb), 0.13, WOOD)
	# the roof: planks from eave to ridge, hides over them
	rise = 1.3
	ang = math.degrees(math.atan2(rise, hx + 0.3))
	slope = math.hypot(hx + 0.3, rise)
	for s in (-1, 1):
		c = (s * (hx + 0.3) / 2, 0, 2.55 + rise / 2)
		p.box((slope + 0.2, 2 * hy + 0.3, 0.12), c, WOOD_GRAY, rot=(0, s * ang, 0), grad=(0.1, 0.9))
		for k in range(5):
			y = -hy + 0.7 + k * 1.4
			hc = (s * (hx + 0.3) / 2 + s * 0.05, y + p.rng.uniform(-0.2, 0.2), 2.62 + rise / 2)
			p.box((slope * p.rng.uniform(0.8, 1.05), p.rng.uniform(1.2, 1.7), 0.06), hc, HIDE if k % 2 else WOOD,
				  rot=(p.rng.uniform(-3, 3), s * ang, p.rng.uniform(-6, 6)), grad=(0.2, 0.8))
	_log(p, (0, -hy - 0.3, 2.55 + rise + 0.05), (0, hy + 0.3, 2.55 + rise + 0.05), 0.14)
	for y in (-hy, hy):                                             # gable ends: hide flaps
		p.poly([(-hx - 0.3, y, 2.5), (hx + 0.3, y, 2.5), (0, y, 2.5 + rise)], [(0, 1, 2)], HIDE, grad=(0.2, 0.8))
	# the ram on its chains
	rz = 1.55
	_log(p, (0, -hy - 1.0, rz), (0, hy - 0.2, rz), 0.3)
	_hoops(p, (0, 0, rz), 0.34, [-hy + 0.2, -1.5, 1.5], IRON, axis="y", w=0.1)
	head = Vector((0, -hy - 1.2, rz))
	p.seg(tuple(head + Vector((0, 0.3, 0))), tuple(head), 0.38, 0.34, IRON, sides=8, grad=(0.1, 0.8))
	p.seg(tuple(head), tuple(head + Vector((0, -0.45, -0.02))), 0.34, 0.14, IRON, sides=8, grad=(0.1, 0.8))
	for s in (-1, 1):                                               # its tusks and ears
		p.seg(tuple(head + Vector((s * 0.2, -0.3, -0.15))), tuple(head + Vector((s * 0.35, -0.6, 0.2))), 0.07, 0.0, BONE, sides=5)
		p.seg(tuple(head + Vector((s * 0.22, 0.1, 0.25))), tuple(head + Vector((s * 0.4, 0.25, 0.5))), 0.1, 0.0, IRON, sides=4)
		p.blob((0.08, 0.05, 0.06), tuple(head + Vector((s * 0.18, -0.22, 0.14))), EMBER, segs=(5, 4), glow=0.8)
	for y in (-2.2, 1.8):                                          # chains from the ridge
		for s in (-1, 1):
			_chain(p, [(s * 0.3, y, rz + 0.3), (s * 0.15, y, 2.2), (0, y, 3.8)], 0.035, 0.035, IRON, sides=4)
	_skull(p, (0, -hy - 0.1, 3.4), s=1.6)
	return p.build(bevel=0.03)


def ogre_war_camp_tent():
	"""A big crude ogre tent: a ridge log on two forked poles over a frame of
	leaning poles, patched hides lashed over it in a low A (8 x 6.4 m, 5.2 m
	tall), the door (-Y) held open on two spears, skulls of men and beasts on
	the ridge and poles, a great horned skull over the door, bones and a
	rack of hides beside it. Collide it as a box (7 x 6 m)."""
	p = Prop("ogre_war_camp_tent", 487)
	hx, hy, H = 3.6, 3.0, 4.6
	for y in (-hy - 0.3, hy + 0.3):                                 # forked poles and the ridge
		p.seg((0, y, 0), (0, y, H + 0.4), 0.2, 0.17, WOOD, sides=7, jitter=0.02)
		for s in (-1, 1):
			p.seg((0, y, H + 0.2), (s * 0.4, y, H + 1.0), 0.1, 0.06, WOOD, sides=5)
	_log(p, (0, -hy - 0.8, H), (0, hy + 0.8, H), 0.18)
	colors = (HIDE, WOOD, HIDE, BAMBOO, WOOD_GRAY)
	for s in (-1, 1):                                               # hide panels on each side, overlapping
		for k in range(5):
			y = -hy + 0.6 + k * 1.2
			w = hx * p.rng.uniform(1.0, 1.1)
			ang = math.degrees(math.atan2(H, hx))
			ln = math.hypot(hx, H)
			c = (s * w / 2, y + p.rng.uniform(-0.1, 0.1), H / 2)
			p.box((ln * 1.02, 1.5, 0.1), c, colors[(k + (s > 0)) % 5], rot=(p.rng.uniform(-2, 2), s * ang, p.rng.uniform(-3, 3)), grad=(0.1, 0.9), jitter=0.03)
			if k % 2 == 0:                                          # stitched seams
				for j in range(4):
					t = 0.2 + j * 0.2
					p.box((0.05, 0.3, 0.05), (s * hx * (1 - t), y + 0.6, H * t + 0.06), BONE, rot=(0, s * ang, 0))
		for k in range(4):                                          # leaning poles showing through
			y = -hy + 0.3 + k * 1.8
			p.seg((s * (hx + 0.3), y, -0.1), (s * -0.2, y, H + 0.6), 0.08, 0.06, WOOD, sides=5)
	# the back gable, closed; the front, its flaps pinned open on spears
	p.poly([(-hx, hy + 0.15, 0), (hx, hy + 0.15, 0), (0, hy + 0.15, H)], [(0, 1, 2)], HIDE, grad=(0.1, 0.9))
	for s in (-1, 1):
		p.poly([(s * hx, -hy, 0), (s * 1.2, -hy - 0.5, 0), (s * 0.4, -hy - 0.1, H * 0.7), (0, -hy, H)], [(0, 1, 2, 3)], WOOD, grad=(0.1, 0.9))
		p.seg((s * 1.4, -hy - 0.9, 0), (s * 1.3, -hy - 0.8, 2.6), 0.05, 0.05, WOOD, sides=5)
		p.seg((s * 1.3, -hy - 0.8, 2.6), (s * 1.3, -hy - 0.8, 3.0), 0.08, 0.0, IRON, sides=4)
		_rope(p, (s * 1.3, -hy - 0.8, 2.3), (s * 0.5, -hy - 0.15, 2.9), 0.1)
	p.box((1.8, 0.1, 2.6), (0, -hy + 0.3, 1.3), IRON, grad=(0.6, 1.0))              # dark inside
	# the great horned skull over the door and skulls on the ridge
	sk = Vector((0, -hy - 0.5, H - 0.2))
	p.blob((0.9, 1.0, 0.7), tuple(sk), BONE, segs=(10, 7), grad=(0.0, 0.7))
	p.blob((0.55, 0.6, 0.4), tuple(sk + Vector((0, -0.5, -0.25))), BONE, segs=(8, 5), grad=(0.1, 0.7))
	for s in (-1, 1):
		p.blob((0.2, 0.1, 0.18), tuple(sk + Vector((s * 0.22, -0.42, 0.05))), IRON, segs=(5, 4))
		_chain(p, [tuple(sk + Vector((s * 0.35, 0, 0.2))), tuple(sk + Vector((s * 0.9, -0.1, 0.5))), tuple(sk + Vector((s * 1.1, -0.3, 1.0))),
				   tuple(sk + Vector((s * 0.9, -0.5, 1.3)))], 0.14, 0.03, BONE, sides=6)
	for y in (-1.5, 0.5, 2.2):
		_skull(p, (0, y, H + 0.18), s=2.2, yaw=p.rng.uniform(-0.6, 0.6))
	for s in (-1, 1):                                               # skull poles either side of the door
		x = s * 2.4
		p.seg((x, -hy - 1.5, 0), (x, -hy - 1.5, 2.6), 0.07, 0.06, WOOD, sides=5)
		_skull(p, (x, -hy - 1.5, 2.6), s=2.4)
		p.seg((x - 0.3, -hy - 1.5, 2.1), (x + 0.3, -hy - 1.5, 2.1), 0.04, 0.04, WOOD, sides=4)
		for dx in (-0.28, 0.28):
			_bone(p, (x + dx, -hy - 1.5, 2.08), (x + dx, -hy - 1.5, 1.6), r=0.03)
	# a hide rack and a heap of bones to the side
	for y in (-1.0, 1.0):
		p.seg((hx + 1.6, y, 0), (hx + 1.6, y, 2.0), 0.06, 0.05, WOOD, sides=5)
	p.seg((hx + 1.6, -1.2, 1.9), (hx + 1.6, 1.2, 1.9), 0.05, 0.05, WOOD, sides=5)
	p.box((0.08, 1.7, 1.3), (hx + 1.62, 0, 1.2), HIDE, rot=(0, 4, 0), grad=(0.1, 0.8), jitter=0.04)
	for k in range(6):
		a, ln = p.rng.uniform(0, math.tau), p.rng.uniform(0.3, 0.55)
		cx, cy = -hx - 1.0 + p.rng.uniform(-0.5, 0.5), -1.8 + p.rng.uniform(-0.5, 0.5)
		_bone(p, (cx - math.cos(a) * ln, cy - math.sin(a) * ln, 0.06), (cx + math.cos(a) * ln, cy + math.sin(a) * ln, 0.12), r=0.04)
	_skull(p, (-hx - 1.1, -2.0, 0.1), s=2.0, yaw=0.8)
	return p.build(bevel=0.02)


def snow_drift():
	"""A low drift of wind-packed snow, about 4.2 x 2.6 m and 0.6 m high, its
	crest carved sharp on the lee side (+Y). Walk over it: no collision."""
	p = Prop("snow_drift", 488)
	p.blob((4.2, 2.4, 1.0), (0, 0, -0.1), SNOW, segs=(16, 8), grad=(0.0, 0.4), jitter=0.02)
	p.blob((3.0, 1.2, 0.9), (0.2, 0.35, 0.05), SNOW, rot=(0, 0, 6), segs=(14, 7), grad=(0.0, 0.35), jitter=0.02)
	p.blob((1.4, 1.0, 0.55), (-1.3, -0.2, 0.0), SNOW, segs=(10, 6), grad=(0.0, 0.4))
	p.blob((1.2, 0.8, 0.45), (1.6, -0.35, -0.02), SNOW, segs=(10, 6), grad=(0.0, 0.4))
	obj = p.build()
	# sink everything below the ground away: flatten the underside to z = 0
	for v in obj.data.vertices:
		v.co.z = max(v.co.z, 0.0)
	return obj


# ---- Mirror Flats (a salt flat under a thin sheet of water)

SALT = BONE               # white fading to warm beige
SALT_PINK = CORAL_PINK    # pale pink into rose: salt stained pink


def _ring_pts(p, r, n, wob, z=0.0, phase=0.0):
	"""An irregular closed ring of n points round the origin."""
	out = []
	for k in range(n):
		a = k * math.tau / n + phase
		rr = r * (1.0 + p.rng.uniform(-wob, wob) + 0.08 * math.sin(3 * a + 1.3))
		out.append((math.cos(a) * rr, math.sin(a) * rr, z))
	return out


def salt_crust_island():
	"""A low island of white salt crust rising out of the mirror water, about
	12 x 11 m and 0.32 m high, its rim a gentle slope 1 m wide you can walk up,
	the flat top cracked into hexagon plates with raised ridges between them.
	Origin at its foot (put it at the water line or just below). Collide it as
	a mesh, or leave it off: it is low enough to wade through."""
	p = Prop("salt_crust_island", 489)
	n = 28
	foot = _ring_pts(p, 6.0, n, 0.06, -0.15)
	rim = [(x * 0.88, y * 0.88, 0.28) for x, y, _ in foot]
	top = [(x * 0.85, y * 0.85, 0.32) for x, y, _ in foot]
	verts = foot + rim + top + [(0, 0, 0.33), (0, 0, -0.15)]
	C, B = 3 * n, 3 * n + 1
	faces = []
	for k in range(n):
		j = (k + 1) % n
		faces.append((k, j, n + j, n + k))                  # the sloping rim
		faces.append((n + k, n + j, 2 * n + j, 2 * n + k))  # the lip
		faces.append((2 * n + k, 2 * n + j, C))             # the top
		faces.append((j, k, B))                             # underside
	p.poly(verts, faces, SALT, grad=(0.55, 0.95))
	# the crust: hexagon plates, raised a little, beige cracks showing between them
	R = 0.72
	poly2 = [(x * 0.97, y * 0.97) for x, y, _ in top]

	def inside(x, y):
		c = False
		for i in range(len(poly2)):
			(x1, y1), (x2, y2) = poly2[i], poly2[i - 1]
			if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
				c = not c
		return c
	for q in range(-8, 9):
		for r in range(-9, 10):
			cx = R * 1.5 * q
			cy = R * math.sqrt(3) * (r + q / 2)
			corners = [(cx + math.cos(math.radians(60 * i)) * R, cy + math.sin(math.radians(60 * i)) * R) for i in range(6)]
			if not all(inside(*c) for c in corners):
				continue
			h = p.rng.uniform(0.05, 0.09)
			pink = p.rng.random() < 0.12
			p.seg((cx, cy, 0.3), (cx, cy, 0.32 + h), R * 0.92, R * 0.9, SALT_PINK if pink else CLOTH_WHITE, sides=6,
				  grad=(0.0, 0.08) if pink else (0.0, 0.2))
	for k in range(9):                                           # little salt crystals on the ridges
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(0.5, 4.2)
		p.rock((0.3, 0.25, 0.22), (math.cos(a) * d, math.sin(a) * d, 0.4), CLOTH_WHITE, grad=(0.0, 0.4), jitter=0.1)
	return p.build(bevel=0.02)


def salt_pillar():
	"""A hoodoo of eroded salt, 6.3 m tall: a spreading foot, a column pinched
	at two waists and banded white and pink where the old lake laid it down, a
	wider cap rock balanced on top, crystals crusting its base. About 3.2 m
	across at the foot. Collide it as a cylinder (r 1.3)."""
	p = Prop("salt_pillar", 490)
	prof = [(0.03, -0.2), (1.6, -0.2), (1.35, 0.4), (0.95, 1.2), (0.8, 2.0), (0.62, 2.8), (0.78, 3.4), (0.72, 4.1),
			(0.5, 4.8), (0.6, 5.2), (1.25, 5.45), (1.3, 5.8), (1.0, 6.2), (0.5, 6.35), (0.0, 6.35)]
	_lathe(p, prof, 12, SALT, grad=(0.03, 0.7), jitter=0.07)
	for z0, z1, r in ((0.7, 1.0, 1.12), (1.7, 1.85, 0.88), (3.15, 3.45, 0.8), (4.3, 4.5, 0.64)):   # pink strata
		_lathe(p, [(0.03, z0), (r, z0), (r * 1.02, (z0 + z1) / 2), (r * 0.97, z1), (0.03, z1)], 12, SALT_PINK, grad=(0.03, 0.4), jitter=0.03)
	_lathe(p, [(0.03, 5.6), (1.34, 5.6), (1.36, 5.72), (0.03, 5.72)], 12, SALT_PINK, grad=(0.1, 0.5), jitter=0.04)
	for k in range(14):                                            # crystals crusting the foot
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(1.3, 2.0)
		h = p.rng.uniform(0.25, 0.6)
		b = (math.cos(a) * d, math.sin(a) * d, -0.05)
		t = (b[0] * 1.08, b[1] * 1.08, h)
		p.seg(b, t, p.rng.uniform(0.08, 0.14), 0.0, CLOTH_WHITE if k % 3 else SALT_PINK, sides=4, grad=(0.0, 0.5), twist=p.rng.uniform(0, 90))
	for k in range(5):                                             # fallen chunks
		a = p.rng.uniform(0, math.tau)
		d = p.rng.uniform(1.8, 2.6)
		p.rock((0.55, 0.45, 0.35), (math.cos(a) * d, math.sin(a) * d, 0.1), SALT, grad=(0.0, 0.6))
	return p.build(bevel=0.02)


def sand_skiff():
	"""A nomad's salt skiff, bow toward -Y: a flat shallow hull of bleached
	planks 6 m long riding on two bone-white runners that curl up at the bow, a
	mast stepped forward carrying a tall lateen sail of patched cloth with a
	faded red stripe, a steering oar and a tiller at the stern, bundles lashed
	amidships. About 2.8 x 7 m, 6.4 m to the yard's tip. Collide it as a box
	(2.2 x 6.2 x 1.1)."""
	p = Prop("sand_skiff", 491)
	L, hw, zr = 3.0, 0.95, 0.35
	for s in (-1, 1):                                              # the runners, curled up at the bow
		pts = [(s * 0.8, L + 0.3, 0.12), (s * 0.8, 0.0, 0.1), (s * 0.8, -L + 0.4, 0.12), (s * 0.8, -L - 0.2, 0.3), (s * 0.8, -L - 0.5, 0.65), (s * 0.78, -L - 0.4, 0.95)]
		_chain(p, pts, 0.1, 0.07, BONE, sides=6, grad=(0.0, 0.6))
		for y in (-1.8, 0.0, 1.8):                                # struts up to the hull
			p.seg((s * 0.8, y, 0.12), (s * 0.7, y, zr + 0.05), 0.05, 0.05, WOOD_GRAY, sides=5)
	# the hull: a flat punt with raked ends and low sides
	bot = [(-hw, -L + 0.7, zr), (hw, -L + 0.7, zr), (hw, L - 0.3, zr), (-hw, L - 0.3, zr)]
	topr = [(-hw - 0.12, -L, zr + 0.7), (hw + 0.12, -L, zr + 0.7), (hw + 0.12, L, zr + 0.6), (-hw - 0.12, L, zr + 0.6)]
	verts = bot + topr
	p.poly(verts, [(0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], CLOTH_WHITE, grad=(0.2, 0.9))
	for k in range(3):                                             # plank seams along the sides
		z = zr + 0.18 + k * 0.17
		for s in (-1, 1):
			p.box((0.04, 2 * L - 0.5, 0.04), (s * (hw + 0.04 + k * 0.035), 0.05, z), WOOD_GRAY, grad=(0.2, 0.6))
	p.box((2 * hw + 0.3, 0.12, 0.1), (0, -L + 0.05, zr + 0.72), WOOD, grad=(0.1, 0.6))
	p.box((2 * hw + 0.3, 0.12, 0.1), (0, L - 0.05, zr + 0.62), WOOD, grad=(0.1, 0.6))
	for s in (-1, 1):
		p.box((0.1, 2 * L, 0.1), (s * (hw + 0.1), 0, zr + 0.66), WOOD, grad=(0.1, 0.6))
	p.box((2 * hw - 0.1, 2 * L - 1.4, 0.06), (0, 0.3, zr + 0.2), WOOD_GRAY, grad=(0.2, 0.8))      # floorboards
	for y in (-0.6, 1.4):                                          # thwarts
		p.box((2 * hw, 0.3, 0.08), (0, y, zr + 0.5), WOOD, grad=(0.1, 0.6))
	# mast, lateen yard and sail
	my = -1.1
	p.seg((0, my, zr + 0.2), (0, my, 4.6), 0.09, 0.07, WOOD, sides=6)
	ya, yb = Vector((0, my - 1.7, 1.5)), Vector((0, my + 2.9, 6.3))
	p.seg(tuple(ya), tuple(yb), 0.06, 0.04, WOOD, sides=5)
	foot = Vector((0.05, my + 2.8, 1.25))
	sail = [tuple(ya + Vector((0.04, 0.1, -0.05))), tuple(yb + Vector((0.04, -0.1, -0.1))), tuple(foot)]
	p.poly(sail, [(0, 1, 2)], CLOTH_WHITE, grad=(0.0, 0.5))
	off = Vector((0.07, 0, 0))
	band = [ya * (1 - v) + foot * v for v in (0.3, 0.42)] + [yb * (1 - v) + foot * v for v in (0.42, 0.3)]
	p.poly([tuple(v + off) for v in band], [(0, 3, 2, 1)], CLOTH_RED, grad=(0.3, 0.7))
	p.box((0.02, 0.5, 0.45), (0.07, my + 0.6, 2.4), BAMBOO, grad=(0.1, 0.5))                     # a patch
	_rope(p, tuple(foot), (0.3, L - 0.3, zr + 0.65), 0.1, r=0.02)
	_rope(p, (0, my, 4.5), (0, -L, zr + 0.75), 0.15, r=0.018)
	# stern: steering oar and tiller, bundles amidships
	p.seg((0.6, L - 0.1, zr + 0.7), (0.75, L + 1.1, 0.15), 0.05, 0.05, WOOD, sides=5)
	p.box((0.08, 0.4, 0.5), (0.77, L + 1.1, 0.25), WOOD, rot=(30, 0, 0))
	for k, (x, y) in enumerate(((-0.4, 0.4), (0.35, 0.6), (-0.1, 2.0), (0.4, 1.9))):
		p.blob((0.6, 0.55, 0.45), (x, y, zr + 0.45), (HIDE, CLOTH_WHITE, BAMBOO, CLOTH_RED)[k], segs=(8, 5), grad=(0.1, 0.8))
		if k < 2:
			_hoops(p, (x, y, 0), 0.26, [zr + 0.45], HIDE, w=0.04)
	return p.build(bevel=0.02)


def nomad_tent():
	"""A salt nomad's tall conical tent of bleached cloth, 5 m across and 6.3 m
	to its crossed pole tips: a band of red and ochre painted round its middle,
	the door flap at the front (-Y) tied back on a dark doorway, smoke flap
	vents at the crown, guy ropes to stakes and a rolled rug by the door.
	Collide it as a cylinder (r 2.4)."""
	p = Prop("nomad_tent", 492)
	R, H = 2.5, 5.2
	n = 16
	for k in range(n):                                             # the cloth cone in panels (a gap at the door)
		a0, a1 = k * math.tau / n, (k + 1) * math.tau / n
		mid = (a0 + a1) / 2
		if abs(math.atan2(math.sin(mid + math.pi / 2), math.cos(mid + math.pi / 2))) < 0.3:
			continue
		sag = 0.06
		v = [(math.cos(a0) * R, math.sin(a0) * R, 0.0), (math.cos(a1) * R, math.sin(a1) * R, 0.0),
			 (math.cos(a1) * 0.28, math.sin(a1) * 0.28, H - 0.6), (math.cos(a0) * 0.28, math.sin(a0) * 0.28, H - 0.6)]
		p.poly(v, [(0, 1, 2, 3)], CLOTH_WHITE, grad=(0.0, 0.55))
		for band, (z0, z1, sw) in enumerate(((1.35, 1.7, CLOTH_RED), (1.78, 1.92, FLAG_YELLOW), (3.3, 3.42, CLOTH_RED))):
			f0, f1 = 1 - z0 / (H - 0.6), 1 - z1 / (H - 0.6)
			r0, r1 = 0.28 + (R - 0.28) * f0 + 0.03, 0.28 + (R - 0.28) * f1 + 0.03
			p.poly([(math.cos(a0) * r0, math.sin(a0) * r0, z0), (math.cos(a1) * r0, math.sin(a1) * r0, z0),
					(math.cos(a1) * r1, math.sin(a1) * r1, z1), (math.cos(a0) * r1, math.sin(a0) * r1, z1)], [(0, 1, 2, 3)], sw, grad=(0.2, 0.6))
	for k in range(8):                                             # poles crossing at the crown
		a = k * math.tau / 8 + 0.2
		p.seg((math.cos(a) * (R - 0.2), math.sin(a) * (R - 0.2), 0.0), (-math.cos(a) * 0.69, -math.sin(a) * 0.69, H + 1.1), 0.05, 0.035, WOOD, sides=5)
	for s in (-1, 1):                                              # smoke flaps at the crown
		p.box((0.7, 0.05, 0.9), (s * 0.35, -0.15, H - 0.25), CLOTH_WHITE, rot=(20, s * 25, s * 15), grad=(0.1, 0.5))
	# the doorway: dark inside, the flaps tied back
	ang = -math.pi / 2
	p.poly([(math.cos(ang - 0.3) * (R - 0.1), math.sin(ang - 0.3) * (R - 0.1), 0.0), (math.cos(ang + 0.3) * (R - 0.1), math.sin(ang + 0.3) * (R - 0.1), 0.0),
			(0, -R * 0.45, 2.6)], [(0, 1, 2)], IRON, grad=(0.6, 1.0))
	for s in (-1, 1):
		a = ang + s * 0.34
		p.poly([(math.cos(a) * R, math.sin(a) * R, 0.0), (math.cos(a + s * 0.25) * (R + 0.05), math.sin(a + s * 0.25) * (R + 0.05), 0.2),
				(math.cos(a + s * 0.12) * (R * 0.55), math.sin(a + s * 0.12) * (R * 0.55), 2.6)], [(0, 1, 2)], CLOTH_WHITE, grad=(0.1, 0.6))
		p.seg((math.cos(a + s * 0.18) * R * 0.92, math.sin(a + s * 0.18) * R * 0.92, 1.1), (math.cos(a + s * 0.18) * R * 0.95, math.sin(a + s * 0.18) * R * 0.95, 1.2),
			  0.08, 0.08, HIDE, sides=6)
	for k in range(6):                                             # guy ropes and stakes
		a = k * math.tau / 6 + 0.5
		if abs(math.sin(a) + 1) < 0.3:
			continue
		top = (math.cos(a) * 1.0, math.sin(a) * 1.0, 3.3)
		st = (math.cos(a) * (R + 1.3), math.sin(a) * (R + 1.3), 0.0)
		_rope(p, top, (st[0], st[1], 0.25), 0.05, r=0.015)
		p.seg((st[0], st[1], -0.1), (st[0], st[1], 0.35), 0.04, 0.03, WOOD, sides=4)
	p.seg((-1.0, -R - 0.6, 0.18), (0.4, -R - 0.6, 0.18), 0.18, 0.18, CLOTH_RED, sides=8, grad=(0.1, 0.7))   # a rolled rug
	for x in (-0.5, 0.1):
		p.seg((x, -R - 0.6, 0.18), (x + 0.06, -R - 0.6, 0.18), 0.19, 0.19, FLAG_YELLOW, sides=8)
	return p.build(bevel=0.015)


def mirror_obelisk():
	"""An obelisk of polished mirror-stone, 7.6 m: a four-sided shaft tapering
	from 1.3 to 0.8 m under a pyramidion, so smooth it throws back the sky, on
	a stepped plinth of pale worn stone whose faces carry faintly glowing
	blue glyphs. About 3.4 m square at the foot. Collide it as a box (the plinth
	3.4 x 3.4, the shaft 1.4 x 1.4)."""
	p = Prop("mirror_obelisk", 493)
	for k, (w, z0, h) in enumerate(((3.4, -0.1, 0.45), (2.7, 0.35, 0.4), (2.1, 0.75, 0.35))):
		p.box((w, w, h), (0, 0, z0 + h / 2), STONE_LIGHT if k % 2 else STONE_WARM, grad=(0.1, 0.8), jitter=0.02)
	for s in (-1, 1):                                              # glyphs on the plinth's faces
		for k in range(4):
			x = -0.9 + k * 0.6
			for gx, gz, gw, gh in ((0, 0, 0.06, 0.24), (0.08, 0.08, 0.14, 0.05)):
				p.box((gw, 0.04, gh), (x + gx - 0.04, s * 1.36, 0.55 + gz), RUNE, grad=(0.0, 0.3), glow=1.2)
				p.box((0.04, gw, gh), (s * 1.36, x + gx - 0.04, 0.55 + gz), RUNE, grad=(0.0, 0.3), glow=1.2)
	obj = p.build(bevel=0.04)
	m = Prop("mirror_obelisk_shaft", 494)
	m.seg((0, 0, 1.1), (0, 0, 6.7), 0.65 * 1.414, 0.4 * 1.414, SEA_STONE, sides=4, grad=(0.0, 0.8), twist=45)
	m.seg((0, 0, 6.7), (0, 0, 7.6), 0.4 * 1.414, 0.0, SEA_STONE, sides=4, grad=(0.0, 0.5), twist=45)
	shaft = m.build()
	for i, mat in enumerate(shaft.data.materials):
		g = mat.copy()
		g.name = "dungeon_mirror"
		b = g.node_tree.nodes["Principled BSDF"]
		b.inputs["Roughness"].default_value = 0.04
		b.inputs["Metallic"].default_value = 0.85
		shaft.data.materials[i] = g
	e = Prop("mirror_obelisk_edges", 495)                         # a thin gold seam at the pyramidion's foot
	e.seg((0, 0, 6.66), (0, 0, 6.76), 0.43 * 1.414, 0.42 * 1.414, GOLD, sides=4, grad=(0.0, 0.5), twist=45)
	return join_into(obj, [shaft, e.build()])


# ---- Silted Reach (a river delta of mud and mangroves)

MUD = WOOD_GRAY           # brown-gray: wet silt
MANGROVE_LEAF = LEAF


def mangrove_tree():
	"""A mangrove, about 8.3 m tall: its trunk starts 1.6 m up on a tangle of
	arching stilt roots that spread 3.2 m and plunge into the mud or water
	(origin at the water line; the roots run 0.6 m below it), a few aerial
	roots hanging from the boughs, and a broad, low crown of dark glossy leaf
	7 m across. Use it like a tree. Collide it as a cylinder (r 0.9) round the
	root knot, or not at all."""
	p = Prop("mangrove_tree", 496)
	rng = p.rng
	knot = Vector((0, 0, 1.6))
	p.seg((0, 0, 1.3), (0.2, 0.1, 4.6), 0.32, 0.24, WOOD_GRAY, sides=8, grad=(0.1, 0.9), jitter=0.02)
	for k in range(11):                                            # the stilt roots
		a = k * math.tau / 11 + rng.uniform(-0.2, 0.2)
		reach = rng.uniform(2.2, 3.2)
		start = knot + Vector((math.cos(a) * 0.15, math.sin(a) * 0.15, rng.uniform(-0.2, 0.9)))
		mid = Vector((math.cos(a) * reach * 0.55, math.sin(a) * reach * 0.55, start.z + rng.uniform(0.2, 0.5)))
		end = Vector((math.cos(a) * reach, math.sin(a) * reach, -0.6))
		pts = [start, start.lerp(mid, 0.5) + Vector((0, 0, 0.25)), mid, mid.lerp(end, 0.5) + Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.2)), end]
		_chain(p, [tuple(v) for v in pts], 0.13, 0.08, WOOD_GRAY, sides=6, grad=(0.1, 0.9))
	boughs = []
	for k in range(5):                                             # boughs spreading low and wide
		a = k * math.tau / 5 + 0.4
		b0 = Vector((0.15, 0.08, rng.uniform(3.4, 4.4)))
		b1 = Vector((math.cos(a) * 2.6, math.sin(a) * 2.6, b0.z + rng.uniform(1.0, 1.8)))
		p.seg(tuple(b0), tuple(b1), 0.16, 0.08, WOOD_GRAY, sides=6, grad=(0.1, 0.8))
		boughs.append(b1)
		if k % 2 == 0:                                            # an aerial root dropping from it
			mid = b0.lerp(b1, 0.6)
			p.seg(tuple(mid), (mid.x * 1.05, mid.y * 1.05, -0.4), 0.05, 0.04, WOOD_GRAY, sides=5)
	canopy = [(0.2, 0.1, 6.4, 3.4)] + [(b.x, b.y, b.z + 0.4, 2.2) for b in boughs]
	for x, y, z, r in canopy:                                      # the crown: flattened clumps
		p.blob((r * 1.6, r * 1.6, r * 0.75), (x, y, z), MANGROVE_LEAF, segs=(10, 6), grad=(0.45, 1.0), jitter=0.12)
		for j in range(3):
			a = rng.uniform(0, math.tau)
			p.blob((r * 0.8, r * 0.8, r * 0.45), (x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.6, z + rng.uniform(-0.2, 0.4)),
				   SCALE_GREEN if j % 2 else MANGROVE_LEAF, segs=(8, 5), grad=(0.35, 1.0), jitter=0.08)
	return p.build()


def mud_dam():
	"""A mudfolk dam of sticks and packed mud along X, 10.4 m long, 3 m through
	and 1.5 m high: a long hump of wet silt bristling with branches, woven
	stakes along its face (-Y, the upstream side), reeds sprouting from its
	top. Collide it as a mesh
	(or a box 10 x 2.4 x 1.3)."""
	p = Prop("mud_dam", 497)
	rng = p.rng
	L = 10.0
	p.blob((L + 0.6, 2.9, 2.2), (0, 0.15, 0.1), MUD, segs=(20, 8), grad=(0.1, 0.9), jitter=0.06)          # the hump
	for k in range(11):                                            # heaped lumps along its back
		x = -L / 2 + 0.6 + k * (L - 1.2) / 10 + rng.uniform(-0.3, 0.3)
		p.blob((rng.uniform(1.4, 2.4), rng.uniform(1.4, 2.0), rng.uniform(0.8, 1.2)), (x, rng.uniform(-0.2, 0.5), rng.uniform(0.6, 0.8)), MUD,
			   segs=(9, 5), grad=(0.05, 0.8), jitter=0.1)
	for k in range(9):                                             # darker wet silt along the foot
		x = -L / 2 + 0.5 + k * (L - 1.0) / 8
		p.blob((1.8, 1.0, 0.6), (x + rng.uniform(-0.3, 0.3), -1.1 + rng.uniform(-0.1, 0.1), 0.05), MUD, segs=(8, 4), grad=(0.6, 1.0), jitter=0.05)
	for k in range(40):                                             # branches poking out every way
		x = rng.uniform(-L / 2 + 0.3, L / 2 - 0.3)
		a = rng.uniform(-0.6, 0.6) + (math.pi if rng.random() < 0.5 else 0)
		z = rng.uniform(0.4, 1.2)
		ln = rng.uniform(1.2, 2.4)
		d = Vector((math.cos(a) * 0.4, rng.uniform(-1, 1), rng.uniform(-0.1, 0.5))).normalized() * ln
		c = Vector((x, rng.uniform(-0.6, 0.8), z))
		p.seg(tuple(c - d * 0.5), tuple(c + d * 0.5), rng.uniform(0.04, 0.07), 0.03, WOOD if k % 3 else BAMBOO, sides=5)
	for k in range(18):                                            # woven stakes on the upstream face
		x = -L / 2 + 0.4 + k * (L - 0.8) / 17
		p.seg((x, -1.1, -0.3), (x + rng.uniform(-0.1, 0.1), -0.95, 1.1 + rng.uniform(-0.15, 0.2)), 0.05, 0.04, WOOD_GRAY, sides=5)
	for z in (0.35, 0.75):
		pts = [(-L / 2 + 0.3 + k * (L - 0.6) / 10, -1.08 + (0.06 if k % 2 else -0.06), z) for k in range(11)]
		_chain(p, pts, 0.03, 0.03, BAMBOO, sides=4)
	for k in range(14):                                            # reeds on top
		x = rng.uniform(-L / 2 + 0.6, L / 2 - 0.6)
		y = rng.uniform(-0.2, 0.7)
		h = rng.uniform(0.6, 1.2)
		p.seg((x, y, 1.0), (x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.2, 0.2), 1.0 + h), 0.03, 0.0, LEAF, sides=3, grad=(0.0, 0.7))
	obj = p.build(bevel=0.02)
	for v in obj.data.vertices:
		v.co.z = max(v.co.z, -0.3)
	return obj


def silt_mound():
	"""A mudfolk dwelling: a beehive of dried silt 4.6 m across and 3.7 m tall,
	built up in ridged courses, a low arched doorway (-Y, 1.1 x 1.5 m, dark
	inside) with a lintel of driftwood, reed thatch tufting its crown, a smoke
	hole, handprints and a shell string by the door. Collide it as a cylinder
	(r 2.2)."""
	p = Prop("silt_mound", 498)
	prof = [(0.03, -0.1), (2.3, -0.1), (2.3, 0.3), (2.15, 1.2), (1.85, 2.1), (1.35, 2.9), (0.75, 3.4), (0.35, 3.6), (0.03, 3.6)]
	_lathe(p, prof, 16, MUD, grad=(0.1, 0.9), jitter=0.05)
	for z in (0.6, 1.25, 1.9, 2.5, 3.05):                          # ridged courses
		r = 2.3
		for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
			if z0 <= z <= z1:
				r = r0 + (r1 - r0) * (z - z0) / max(z1 - z0, 1e-4)
		p.seg((0, 0, z - 0.07), (0, 0, z + 0.07), r + 0.06, r + 0.03, WOOD_GRAY, sides=16, grad=(0.2, 0.7), jitter=0.02)
	# the doorway: a dark arch set into the wall with a driftwood lintel
	d = -2.1
	p.box((1.1, 0.8, 1.2), (0, d, 0.6), IRON, grad=(0.6, 1.0))
	p.seg((0, d - 0.4, 1.2), (0, d + 0.4, 1.2), 0.55, 0.55, IRON, sides=12)
	for s in (-1, 1):
		p.blob((0.5, 0.9, 1.7), (s * 0.78, d - 0.1, 0.7), MUD, segs=(8, 6), grad=(0.1, 0.9))
	p.seg((-0.95, d - 0.45, 1.85), (0.95, d - 0.45, 1.8), 0.1, 0.09, WOOD_GRAY, sides=6, jitter=0.02)
	for k in range(3):                                              # white handprints
		p.box((0.16, 0.03, 0.18), (-1.3 + k * 0.25, d + 0.35 - k * 0.08, 1.4 + k * 0.1), CLOTH_WHITE, rot=(0, 0, -25 - k * 10), grad=(0.0, 0.3))
	for k in range(6):                                              # a string of shells by the door
		p.blob((0.1, 0.05, 0.1), (0.95, d - 0.45, 1.65 - k * 0.2), SHELL_PEACH, segs=(6, 4), grad=(0.0, 0.5))
	# thatch crown and smoke hole
	for k in range(22):
		a = k * math.tau / 22
		p.seg((math.cos(a) * 0.55, math.sin(a) * 0.55, 3.35), (math.cos(a) * 1.05, math.sin(a) * 1.05, 3.05 + p.rng.uniform(-0.1, 0.1)), 0.09, 0.02, BAMBOO, sides=3)
	p.seg((0, 0, 3.4), (0, 0, 3.9), 0.35, 0.22, BAMBOO, sides=10, grad=(0.1, 0.8))
	p.seg((0, 0, 3.85), (0, 0, 3.92), 0.16, 0.16, IRON, sides=8)
	return p.build(bevel=0.02)


def fishing_hut_stilts():
	"""A small delta fisher's hut on stilts: a 3.2 x 3 m plank deck 2 m up (the
	origin at the water or mud line) on six poles, a reed-walled hut with a
	thatch roof on the back of it, a ladder down at the front (-Y), nets hung to
	dry on a pole frame on the right, fish drying on a line, a creel and a
	lamp by the door. About 5 x 4.4 m, 5.6 m tall. Collide it as a mesh (or a
	box over the deck, the posts as cylinders)."""
	p = Prop("fishing_hut_stilts", 499)
	hx, hy, zd = 1.6, 1.5, 2.0
	for x in (-hx + 0.15, hx - 0.15):                            # stilts, with cross braces
		for y in (-hy + 0.15, 0.0, hy - 0.15):
			p.seg((x, y, -0.8), (x, y, zd), 0.1, 0.09, WOOD_GRAY, sides=6, jitter=0.01)
		p.seg((x, -hy + 0.15, 0.2), (x, hy - 0.15, 1.6), 0.04, 0.04, WOOD_GRAY, sides=4)
	for k in range(10):                                            # the deck
		y = -hy + (k + 0.5) * 2 * hy / 10
		p.box((2 * hx + 0.1 + p.rng.uniform(-0.06, 0.06), 2 * hy / 10 - 0.03, 0.08), (0, y, zd + 0.04), WOOD if k % 3 else WOOD_GRAY,
			  rot=(0, 0, p.rng.uniform(-1, 1)), grad=(0.1, 0.6))
	for s in (-1, 1):
		p.box((0.14, 2 * hy, 0.16), (s * (hx - 0.1), 0, zd - 0.08), WOOD, grad=(0.3, 1.0))
	# the hut: reed walls, a doorway facing the ladder, thatch
	x0, x1, y0, y1, wh = -hx + 0.1, 0.9, -0.5, hy - 0.05, 1.9
	for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
		ln = math.hypot(bx - ax, by - ay)
		n = int(ln / 0.1)
		for k in range(n):
			t = (k + 0.5) / n
			x, y = ax + (bx - ax) * t, ay + (by - ay) * t
			if ay == y0 and by == y0 and abs(x + 0.15) < 0.4:
				continue
			p.seg((x, y, zd + 0.08), (x, y, zd + wh + p.rng.uniform(-0.05, 0.05)), 0.05, 0.045, BAMBOO if k % 4 else HIDE, sides=4)
	for z in (zd + 0.6, zd + 1.4):
		for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
			p.seg((ax, ay, z), (bx, by, z), 0.03, 0.03, WOOD_GRAY, sides=4)
	p.box((0.8, 0.08, wh), (-0.15, y0 + 0.4, zd + wh / 2 + 0.05), IRON, grad=(0.6, 1.0))     # dark within the doorway
	cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
	_lathe(p, [(0.03, zd + wh - 0.2), (1.75, zd + wh - 0.2), (1.8, zd + wh - 0.05), (0.2, zd + wh + 1.55), (0.03, zd + wh + 1.6)], 10, BAMBOO, grad=(0.03, 0.9), jitter=0.04).data.transform(Matrix.Translation((cx, cy, 0)))
	p.seg((cx, cy, zd + wh + 1.45), (cx, cy, zd + wh + 1.8), 0.12, 0.0, BAMBOO, sides=6)
	# the ladder
	for x in (-0.35, 0.35):
		p.seg((x, -hy - 0.9, -0.5), (x, -hy - 0.05, zd + 0.7), 0.04, 0.04, WOOD_GRAY, sides=5)
	for k in range(7):
		t = (k + 0.5) / 7
		p.seg((-0.35, -hy - 0.9 + 0.85 * t, -0.5 + (zd + 1.2) * t), (0.35, -hy - 0.9 + 0.85 * t, -0.5 + (zd + 1.2) * t), 0.03, 0.03, WOOD, sides=4)
	# net frame on the open side
	nx = hx + 0.9
	for y in (-1.2, 1.2):
		p.seg((nx, y, -0.5), (nx, y, zd + 2.2), 0.06, 0.05, WOOD_GRAY, sides=5)
	p.seg((nx, -1.4, zd + 2.1), (nx, 1.4, zd + 2.1), 0.05, 0.05, WOOD_GRAY, sides=5)
	for k in range(9):                                             # the net: a sagging mesh of cords
		y = -1.1 + k * 0.275
		_rope(p, (nx, y, zd + 2.05), (nx, y + 0.02, 0.8 + 0.3 * math.sin(k)), 0.0, r=0.012, n=2)
	for k in range(6):
		z = zd + 1.8 - k * 0.3
		_rope(p, (nx + 0.01, -1.1, z), (nx + 0.01, 1.1, z), 0.12, r=0.012)
	for k in range(4):                                             # floats on the net's foot
		p.blob((0.14, 0.14, 0.12), (nx + 0.03, -0.9 + k * 0.6, 0.95), CORAL_ORANGE, segs=(6, 4))
	_rope(p, (x1 + 0.1, y0 - 0.2, zd + 1.8), (hx - 0.1, -hy + 0.1, zd + 1.5), 0.2, r=0.012)   # a drying line of fish
	for k in range(3):
		t = (k + 1) / 4
		fx, fy = x1 + 0.1 + (hx - 0.2 - x1) * t, y0 - 0.2 + (-hy + 0.3 - y0) * t
		p.blob((0.07, 0.04, 0.32), (fx, fy, zd + 1.45 - 0.08 * math.sin(t * math.pi)), SEA_STONE, segs=(6, 4), grad=(0.0, 0.7))
	p.seg((1.2, -0.9, zd + 0.08), (1.2, -0.9, zd + 0.5), 0.22, 0.28, BAMBOO, sides=10, grad=(0.1, 0.8))   # a creel
	p.seg((-0.7, -0.62, zd + 1.5), (-0.7, -0.8, zd + 1.5), 0.02, 0.02, IRON, sides=4)                    # a lamp by the door
	p.box((0.16, 0.16, 0.24), (-0.7, -0.86, zd + 1.38), FLAME, glow=1.6, grad=(0.1, 0.5))
	p.box((0.2, 0.2, 0.04), (-0.7, -0.86, zd + 1.52), IRON)
	return p.build(bevel=0.015)


def sunken_barge():
	"""A smugglers' barge settled half into the mud: a flat-bottomed hull 9.5 m
	long and 3.6 m in the beam, stern cabin and all, lying tilted 14 degrees
	with its bow (-Y) buried to the gunwale, crates and barrels (KayKit's)
	spilled from its hold across the mud, a snapped mast and a trailing rope.
	Origin at the mud line. About 7 x 11 m. Collide it as a mesh."""
	p = Prop("sunken_barge", 500)
	start = len(p.parts)
	L, hw, D = 4.75, 1.8, 1.4
	bot = [(-hw + 0.2, -L + 0.8, 0), (hw - 0.2, -L + 0.8, 0), (hw - 0.2, L - 0.6, 0), (-hw + 0.2, L - 0.6, 0)]
	top = [(-hw, -L, D), (hw, -L, D), (hw, L, D), (-hw, L, D)]
	inner_b = [(x * 0.9, y * 0.95, 0.15) for x, y, _ in bot]
	inner_t = [(x * 0.92, y * 0.97, D) for x, y, _ in top]
	verts = bot + top + inner_b + inner_t
	faces = [(0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
			 (8, 11, 10, 9), (8, 9, 13, 12), (9, 10, 14, 13), (10, 11, 15, 14), (11, 8, 12, 15),
			 (4, 12, 13, 5), (5, 13, 14, 6), (6, 14, 15, 7), (7, 15, 12, 4)]
	p.poly(verts, faces, WOOD, grad=(0.1, 0.9))
	for k in range(4):                                             # strakes along the sides
		z = 0.3 + k * 0.3
		for s in (-1, 1):
			f = z / D
			p.box((0.05, 2 * L - 1.2 * (1 - f), 0.07), (s * (hw - 0.2 + 0.2 * f + 0.03), 0.1 - 0.1 * f, z), WOOD_GRAY, grad=(0.2, 0.6))
	for y in (-2.5, -0.8, 0.9):                                    # deck beams across the open hold
		p.box((2 * hw, 0.2, 0.18), (0, y, D - 0.1), WOOD, grad=(0.2, 0.8))
	p.box((2 * hw - 0.2, 0.9, 0.06), (0.3, -1.6, D - 0.02), WOOD, rot=(0, 0, 4), grad=(0.1, 0.6))
	# the stern cabin
	p.box((2 * hw - 0.4, 2.6, 1.5), (0, L - 1.6, D + 0.75), WOOD, grad=(0.1, 0.9))
	p.box((2 * hw - 0.1, 2.9, 0.14), (0, L - 1.6, D + 1.57), WOOD_GRAY, grad=(0.1, 0.6))
	p.box((0.7, 0.08, 1.1), (0.5, L - 2.93, D + 0.6), IRON, grad=(0.6, 1.0))
	for x in (-0.9,):
		p.box((0.5, 0.08, 0.4), (x, L - 2.93, D + 0.95), IRON)
	p.seg((0.0, -2.0, 0.2), (0.0, -2.0, 3.6), 0.12, 0.1, WOOD, sides=7)            # the snapped mast
	p.rock((0.26, 0.26, 0.3), (0.0, -2.0, 3.6), WOOD, jitter=0.05)
	_rope(p, (0.0, -2.0, 3.3), (1.6, -4.4, D + 0.1), 0.3, r=0.02)
	_move_parts(p, start, Matrix.Translation((0, 0, -0.75)) @ Matrix.Rotation(math.radians(14), 4, "X") @ Matrix.Rotation(math.radians(6), 4, "Y"))
	for k in range(9):                                             # mud heaped round the buried bow
		a = p.rng.uniform(0, math.pi)
		p.blob((p.rng.uniform(1.2, 2.2), p.rng.uniform(0.9, 1.6), 0.6), (math.cos(a) * 2.2, -3.8 + math.sin(a) * -0.8 + p.rng.uniform(-0.5, 0.8), 0.0), MUD,
			   segs=(8, 5), grad=(0.2, 0.9), jitter=0.06)
	obj = p.build(bevel=0.02)
	for v in obj.data.vertices:                                   # nothing hangs below the mud
		v.co.z = max(v.co.z, -0.4)
	cargo = []
	for piece, loc, rot, sc in (("box_large", (2.9, -1.2, 0.0), 0.4, 0.55), ("box_large", (3.2, -0.2, 0.0), -0.2, 0.5),
								("box_large", (3.0, -0.8, 0.8), 0.9, 0.45), ("box_small", (2.2, 1.0, 0.0), 0.3, 0.6),
								("barrel_small", (-2.8, 0.6, 0.0), 0.0, 0.6), ("barrel_large", (-3.0, -1.0, 0.0), 0.5, 0.45),
								("crates_stacked", (0.3, -0.4, 0.55), 0.15, 0.4), ("box_small", (4.3, 0.9, 0.0), 1.2, 0.5)):
		cargo += kaykit(piece, loc, rot, (sc, sc, sc))
	lying = kaykit("barrel_small", (0, 0, 0), 0.0, (0.6, 0.6, 0.6))
	for o in lying:
		o.data.transform(Matrix.Translation((-2.2, 2.4, 0.35)) @ Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Rotation(0.7, 4, "X"))
	return _merge_materials(join_into(obj, cargo + lying))


# ---- Tidemouth (Rainhold's harbor outpost)

HARBOR_STONE = {(1, 0): SEA_STONE, (0, 0): STONE_DARK}   # KayKit wall stone -> sea-worn blue gray


def lighthouse():
	"""Tidemouth's lighthouse, 18.6 m: a round tapering tower of pale stone
	banded in red on a stepped sea-stone base (6 m across), a door at the foot
	(-Y) up three steps, small windows climbing it, a corbelled gallery with an
	iron railing at 13.4 m and the lantern room above it, its glass glowing gold
	round a great flame, under a teal copper dome and a weather vane. Collide it
	as a cylinder (r 2.7)."""
	p = Prop("lighthouse", 501)
	p.seg((0, 0, -0.2), (0, 0, 0.9), 3.0, 2.9, SEA_STONE, sides=12, grad=(0.2, 1.0))
	prof_r = lambda z: 2.5 - (z - 0.9) / (13.0 - 0.9) * 0.9
	bands = ((0.9, 3.9, CLOTH_WHITE), (3.9, 5.6, CLOTH_RED), (5.6, 8.6, CLOTH_WHITE), (8.6, 10.3, CLOTH_RED), (10.3, 13.0, CLOTH_WHITE))
	for z0, z1, sw in bands:
		p.seg((0, 0, z0), (0, 0, z1), prof_r(z0), prof_r(z1), sw, sides=16, grad=(0.05, 0.6))
	for k, z in enumerate((2.6, 5.0, 7.4, 9.8, 11.8)):              # windows spiralling up
		a = -math.pi / 2 + (k * 1.9)
		r = prof_r(z)
		p.box((0.45, 0.3, 0.8), (math.cos(a) * (r - 0.05), math.sin(a) * (r - 0.05), z), IRON, rot=(0, 0, math.degrees(a) + 90))
		p.box((0.6, 0.35, 0.12), (math.cos(a) * (r + 0.02), math.sin(a) * (r + 0.02), z + 0.46), STONE_LIGHT, rot=(0, 0, math.degrees(a) + 90))
	p.box((1.1, 0.5, 2.0), (0, -2.35, 1.9), WOOD, grad=(0.2, 1.0))                       # the door
	p.box((1.5, 0.6, 0.25), (0, -2.45, 3.0), STONE_LIGHT, grad=(0.1, 0.6))
	for k in range(3):
		p.box((1.8, 0.55, 0.3), (0, -3.6 + k * 0.4, 0.2 + k * 0.3), SEA_STONE, grad=(0.1, 0.8))
	# gallery: corbels, a platform and an iron railing
	zg = 13.0
	for k in range(16):
		a = k * math.tau / 16
		p.box((0.35, 0.6, 0.6), (math.cos(a) * 1.75, math.sin(a) * 1.75, zg - 0.2), STONE_LIGHT, rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.8))
	p.seg((0, 0, zg + 0.1), (0, 0, zg + 0.4), 2.4, 2.4, SEA_STONE, sides=16, grad=(0.1, 0.7))
	for k in range(20):
		a = k * math.tau / 20
		p.seg((math.cos(a) * 2.3, math.sin(a) * 2.3, zg + 0.4), (math.cos(a) * 2.3, math.sin(a) * 2.3, zg + 1.4), 0.03, 0.03, IRON, sides=4)
	_hoops(p, (0, 0, 0), 2.3, [zg + 1.4, zg + 0.9], IRON, w=0.05)
	# the lantern room: glowing panes between iron mullions, the flame inside, the dome
	zl = zg + 0.4
	p.seg((0, 0, zl), (0, 0, zl + 0.5), 1.5, 1.5, STONE_LIGHT, sides=8, grad=(0.1, 0.6), twist=22.5)
	p.seg((0, 0, zl + 0.5), (0, 0, zl + 2.5), 1.35, 1.35, GOLD, sides=8, grad=(0.0, 0.4), glow=2.2, twist=22.5)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 1.4, math.sin(a) * 1.4, zl + 0.5), (math.cos(a) * 1.4, math.sin(a) * 1.4, zl + 2.5), 0.07, 0.07, IRON, sides=4)
	p.seg((0, 0, zl + 0.6), (0, 0, zl + 2.3), 0.6, 0.0, FLAME, sides=7, grad=(0.1, 0.9), glow=2.6)
	p.seg((0, 0, zl + 2.5), (0, 0, zl + 2.7), 1.6, 1.6, IRON, sides=8, grad=(0.0, 0.6), twist=22.5)
	_lathe(p, [(0.03, zl + 2.7), (1.6, zl + 2.7), (1.4, zl + 3.3), (0.9, zl + 3.8), (0.35, zl + 4.05), (0.03, zl + 4.1)], 16, TEAL, grad=(0.03, 0.8))
	p.seg((0, 0, zl + 4.05), (0, 0, zl + 4.9), 0.05, 0.03, IRON, sides=5)
	p.blob((0.22, 0.22, 0.22), (0, 0, zl + 4.2), GOLD, segs=(8, 5))
	p.poly([(0.05, 0, zl + 4.75), (0.6, 0, zl + 4.6), (0.05, 0, zl + 4.45)], [(0, 1, 2)], IRON)
	# sea wrack round the foot
	for k in range(7):
		a = p.rng.uniform(0, math.tau)
		p.rock((0.9, 0.8, 0.6), (math.cos(a) * 3.2, math.sin(a) * 3.2, 0.1), SEA_STONE)
		if k % 2:
			_barnacles(p, (math.cos(a) * 3.0, math.sin(a) * 3.0, 0.4), 4, 0.3)
	return p.build(bevel=0.03)


def harbor_warehouse():
	"""A harbor warehouse, 14 x 9 m: a ground storey of KayKit wall (sea-worn
	stone, 3 m) with wide timber doors at the front (-Y), a timber-framed upper
	storey of weathered planks with posts and braces (2.6 m), a steep red-tiled
	gable roof (ridge along X, 9.2 m), a hoist beam and pulley jutting from the
	front gable with a crate slung on it, and crates and barrels stacked by
	the door. Collide it as a box (14 x 9 x 5.6, the roof above)."""
	p = Prop("harbor_warehouse", 502)
	hx, hy, g, u = 7.0, 4.5, 3.0, 2.6
	p.box((2 * hx + 0.4, 2 * hy + 0.4, 0.3), (0, 0, 0.0), STONE_DARK, grad=(0.3, 0.9))
	p.box((2 * hx - 0.8, 2 * hy - 0.8, g + u), (0, 0, (g + u) / 2), IRON, grad=(0.4, 1.0))
	# the doors: a wide timber pair in a heavy frame
	p.box((3.4, 0.4, 2.9), (0, -hy - 0.05, 1.45), WOOD_GRAY, grad=(0.2, 1.0))
	for s in (-1, 1):
		p.box((1.55, 0.2, 2.6), (s * 0.8, -hy - 0.3, 1.3), WOOD, grad=(0.2, 1.0))
		for z in (0.5, 2.1):
			p.box((1.4, 0.24, 0.14), (s * 0.8, -hy - 0.32, z), WOOD_GRAY, rot=(0, 0, 0))
		p.box((0.14, 0.24, 1.9), (s * 0.8, -hy - 0.32, 1.3), WOOD_GRAY, rot=(0, s * 38, 0))
		p.blob((0.12, 0.1, 0.12), (s * 0.15, -hy - 0.42, 1.3), IRON, segs=(6, 4))
	p.box((3.8, 0.5, 0.4), (0, -hy - 0.1, 3.0), WOOD_GRAY, grad=(0.1, 0.8))
	# the timber upper storey
	p.box((2 * hx + 0.3, 2 * hy + 0.3, 0.3), (0, 0, g + 0.15), WOOD, grad=(0.1, 0.8))
	for s, (ax, ay, bx, by) in enumerate(((-hx, -hy, hx, -hy), (hx, -hy, hx, hy), (hx, hy, -hx, hy), (-hx, hy, -hx, -hy))):
		ln = math.hypot(bx - ax, by - ay)
		yaw = math.degrees(math.atan2(by - ay, bx - ax))
		nx, ny = (by - ay) / ln, -(bx - ax) / ln
		mx, my = (ax + bx) / 2, (ay + by) / 2
		p.box((ln, 0.22, u), (mx + nx * 0.05, my + ny * 0.05, g + 0.3 + u / 2), WOOD_GRAY, rot=(0, 0, yaw), grad=(0.1, 0.9))
		n = int(ln / 2.3)
		for k in range(n + 1):                                    # posts and braces
			t = k / n
			x, y = ax + (bx - ax) * t, ay + (by - ay) * t
			p.box((0.24, 0.3, u), (x + nx * 0.15, y + ny * 0.15, g + 0.3 + u / 2), WOOD, rot=(0, 0, yaw), grad=(0.2, 0.9))
			if k < n:
				t2 = (k + 1) / n
				x2, y2 = ax + (bx - ax) * t2, ay + (by - ay) * t2
				c = ((x + x2) / 2 + nx * 0.15, (y + y2) / 2 + ny * 0.15, g + 0.3 + u / 2)
				ang = math.degrees(math.atan2(u, ln / n)) * (1 if k % 2 else -1)
				p.box((math.hypot(u, ln / n) - 0.2, 0.26, 0.18), c, WOOD, rot=(0, -ang, yaw), grad=(0.2, 0.9))
				if s in (0, 2) and k % 2 == 1:                        # small shuttered windows
					p.box((0.8, 0.34, 0.7), ((x + x2) / 2 + nx * 0.12, (y + y2) / 2 + ny * 0.12, g + 1.7), IRON, rot=(0, 0, yaw))
		p.box((ln + 0.3, 0.34, 0.2), (mx + nx * 0.15, my + ny * 0.15, g + 0.3 + u), WOOD, rot=(0, 0, yaw), grad=(0.1, 0.7))
	# the roof: a steep tiled gable, ridge along X, gable ends in planks
	top = g + 0.3 + u
	rise = 3.3
	ang = math.atan2(rise, hy + 0.5)
	slope = math.hypot(hy + 0.5, rise) + 0.3
	for s in (-1, 1):
		down = Vector((0, math.cos(ang) * s, -math.sin(ang)))
		for i in range(6):
			cc = Vector((0, 0, top + rise + 0.1)) + down * slope * (i + 0.5) / 6
			p.box((2 * hx + 1.0, slope / 6 * 1.08, 0.22), tuple(cc), CLAY if i % 2 else CLOTH_RED, rot=(-math.degrees(ang) * s, 0, 0), grad=(0.1, 0.9))
	for x in (-hx - 0.1, hx + 0.1):
		tri = [(-hy - 0.1, top), (hy + 0.1, top), (0, top + rise)]
		verts = [(x - 0.12, y, z) for y, z in tri] + [(x + 0.12, y, z) for y, z in tri]
		p.poly(verts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], WOOD_GRAY, grad=(0.1, 0.9))
	p.seg((-hx - 0.6, 0, top + rise + 0.2), (hx + 0.6, 0, top + rise + 0.2), 0.16, 0.16, CLOTH_RED, sides=6)
	# a loft door in the front roof under a hoist beam with its pulley and a crate
	p.box((1.4, 1.2, 1.5), (0, -hy + 0.2, top + 0.8), WOOD_GRAY, grad=(0.1, 0.9))
	p.box((1.0, 0.1, 1.1), (0, -hy - 0.42, top + 0.7), IRON)
	p.poly([(-0.8, -hy - 0.4, top + 1.55), (0.8, -hy - 0.4, top + 1.55), (0, -hy - 0.4, top + 2.2), (-0.8, hy * 0.2, top + 1.55), (0.8, hy * 0.2, top + 1.55), (0, hy * 0.2, top + 2.2)],
		   [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], CLAY, grad=(0.1, 0.8))
	_beam(p, (0, -hy + 0.4, top + 2.0), (0, -hy - 1.6, top + 2.0), 0.12, WOOD)
	p.seg((-0.12, -hy - 1.45, top + 1.75), (0.12, -hy - 1.45, top + 1.75), 0.2, 0.2, WOOD_GRAY, sides=10)
	p.seg((0, -hy - 1.45, top + 1.6), (0, -hy - 1.45, 2.4), 0.02, 0.02, HIDE, sides=4)
	obj = p.build(bevel=0.03)
	walls = []
	_kaykit_box(walls, -hx, -hy, hx, hy, 0.15, 1, g - 0.15,
				kinds=lambda side, r, k: "wall_window_open" if side in (1, 3) and k == 1 else "wall")
	walls = _restone(walls, HARBOR_STONE)
	cargo = []
	for piece, loc, rot, sc in (("box_large", (-3.2, -hy - 1.2, 0.0), 0.1, 0.6), ("box_large", (-3.1, -hy - 1.25, 0.9), -0.2, 0.5),
								("box_small", (-4.3, -hy - 1.0, 0.0), 0.5, 0.7), ("barrel_large", (3.4, -hy - 1.1, 0.0), 0.0, 0.5),
								("barrel_small", (4.4, -hy - 0.9, 0.0), 0.0, 0.6), ("barrel_small", (4.3, -hy - 1.8, 0.0), 0.4, 0.6),
								("box_small", (0.0, -hy - 1.45, 1.8), 0.3, 0.7)):
		cargo += kaykit(piece, loc, rot, (sc, sc, sc))
	return _merge_materials(join_into(obj, walls + cargo))


def harbor_pier():
	"""A 12 m length of harbor pier along Y, 4 m wide: heavy planks on stout
	pilings driven 4.5 m down (the deck's top is the origin, where you walk),
	a kerb beam along each edge with bollards and an iron mooring ring, a coil
	of rope, and a ladder down the right side. Chains end to end along Y.
	Collide it as a mesh (or a box 4 x 12 x 0.4 under the deck top)."""
	p = Prop("harbor_pier", 503)
	hx, hy = 2.0, 6.0
	n = 30
	for k in range(n):                                              # planks across
		y = -hy + (k + 0.5) * 2 * hy / n
		p.box((2 * hx - 0.1 + p.rng.uniform(-0.05, 0.05), 2 * hy / n - 0.035, 0.1), (p.rng.uniform(-0.03, 0.03), y, -0.05),
			  WOOD_GRAY if p.rng.random() < 0.35 else WOOD, rot=(0, 0, p.rng.uniform(-0.6, 0.6)), grad=(0.1, 0.6))
	for x in (-1.3, 0.0, 1.3):                                     # stringers
		p.box((0.24, 2 * hy, 0.3), (x, 0, -0.25), WOOD, grad=(0.3, 1.0))
	for s in (-1, 1):                                              # kerbs, pilings, bracing
		p.box((0.26, 2 * hy, 0.22), (s * (hx - 0.13), 0, 0.11), WOOD, grad=(0.1, 0.8))
		for y in (-hy + 0.6, -2.0, 2.0, hy - 0.6):
			p.seg((s * (hx - 0.15), y, -4.5), (s * (hx - 0.15), y, -0.1), 0.2, 0.18, WOOD_GRAY, sides=7, grad=(0.2, 1.0))
			p.seg((s * (hx - 0.15), y, -1.6), (s * (hx - 0.15), y, -1.0), 0.23, 0.22, MOSS, sides=7, grad=(0.1, 0.8))   # weed at the tide line
		for (ya, yb) in ((-hy + 0.6, -2.0), (2.0, hy - 0.6)):
			p.seg((s * (hx - 0.15), ya, -0.6), (s * (hx - 0.15), yb, -2.8), 0.07, 0.07, WOOD_GRAY, sides=4)
	for y in (-2.0, 2.0):
		p.seg((-hx + 0.15, y, -0.6), (hx - 0.15, y, -2.8), 0.07, 0.07, WOOD_GRAY, sides=4)
	for (x, y) in ((-hx + 0.3, -3.8), (hx - 0.3, 3.8)):              # bollards
		_lathe(p, [(0.03, 0.2), (0.26, 0.2), (0.22, 0.5), (0.2, 0.62), (0.32, 0.72), (0.3, 0.82), (0.03, 0.84)], 10, IRON, grad=(0.03, 0.7)).data.transform(Matrix.Translation((x, y, 0)))
	p.seg((hx - 0.05, -1.0, 0.0), (hx + 0.08, -1.0, 0.0), 0.2, 0.2, IRON, sides=10)                # a mooring ring
	p.seg((hx + 0.04, -1.0, -0.05), (hx + 0.04, -1.0, -0.35), 0.03, 0.03, IRON, sides=4)
	for k in range(4):                                              # a coil of rope
		p.seg((-1.0, 1.4, 0.03 + k * 0.05), (-1.0, 1.4, 0.07 + k * 0.05), 0.32 - k * 0.03, 0.32 - k * 0.03, HIDE, sides=12, grad=(0.1, 0.6))
	for y in (4.6, 5.2):                                           # a ladder down the right side
		p.seg((hx + 0.1, y, -2.6), (hx + 0.1, y, 0.5), 0.04, 0.04, WOOD_GRAY, sides=5)
	for k in range(6):
		z = -2.3 + k * 0.45
		p.seg((hx + 0.1, 4.6, z), (hx + 0.1, 5.2, z), 0.03, 0.03, WOOD, sides=4)
	return p.build(bevel=0.02)


def reaver_longship():
	"""A reaver longship drawn up on the beach, bow (-Y) up the sand: a clinker
	hull 14 m long and 3.6 m in the beam whose stem rises into a tall curling
	fin like a sea-beast's dorsal and whose stern post curls the other way,
	round shields in red, black and white along the gunwale, oars shipped
	across the thwarts, a mast with a red-and-white striped sail half furled
	on its yard, lying heeled 7 degrees. About 14 m long and 4.2 m across the
	shields (the oars reach out to 6.4 m), 9 m to the mast top. Origin on the sand. Collide it as a mesh (or a box over the hull)."""
	p = Prop("reaver_longship", 504)
	start = len(p.parts)
	L, W, D, nu = 6.4, 1.8, 1.5, 7

	def section(y, shrink=1.0, lift=0.0):
		t = abs(y) / L
		w = W * max(0.05, 1.0 - t ** 2.2) * shrink
		sheer = D + 0.9 * t ** 3                                  # the gunwale sweeps up at both ends
		keel = 0.25 + 0.9 * t ** 2.5
		pts = []
		for i in range(nu):
			a = math.pi * i / (nu - 1)
			x = math.cos(a) * w
			depth = (sheer - keel) * (0.6 + 0.4 * math.sin(a))
			pts.append((x, y, sheer - math.sin(a) * depth + lift if i not in (0, nu - 1) else sheer + lift))
		return pts

	nsec = 16
	ys = [-L + 2 * L * k / nsec for k in range(nsec + 1)]
	outer = [section(y) for y in ys]
	inner = [section(y, 0.9, 0.1) for y in ys]
	for grid, flip, sw0 in ((outer, False, WOOD), (inner, True, WOOD_GRAY)):
		for i in range(nu - 1):
			for k in range(nsec):
				sw = sw0 if grid is inner else (WOOD if i % 2 else WOOD_GRAY)
				q = [grid[k][i], grid[k + 1][i], grid[k + 1][i + 1], grid[k][i + 1]]
				p.poly(q, [(0, 1, 2, 3)], sw, grad=(0.1, 0.9) if grid is outer else (0.4, 1.0))
	for k in range(nsec):                                          # gunwales
		for i in (0, nu - 1):
			p.poly([outer[k][i], outer[k + 1][i], inner[k + 1][i], inner[k][i]], [(0, 1, 2, 3)], WOOD, grad=(0.0, 0.4))
	p.box((0.25, 2 * L * 0.9, 0.3), (0, 0, 0.12), WOOD, grad=(0.3, 1.0))              # keel
	# the fin prow and the curled stern post
	fin = [(0.0, -L + 0.1, D + 0.9), (0.0, -L - 0.5, D + 1.8), (0.0, -L - 0.7, D + 3.0), (0.0, -L - 0.3, D + 3.9), (0.0, -L + 0.4, D + 4.1), (0.0, -L + 0.3, D + 3.4), (0.0, -L + 0.2, D + 1.4)]
	verts = [(x - 0.1, y, z) for x, y, z in fin] + [(x + 0.1, y, z) for x, y, z in fin]
	m = len(fin)
	faces = [tuple(range(m)), tuple(range(2 * m - 1, m - 1, -1))] + [(i, (i + 1) % m, m + (i + 1) % m, m + i) for i in range(m)]
	p.poly(verts, faces, CLOTH_RED, grad=(0.1, 0.9))
	for k in range(4):                                             # ribs in the fin
		a = Vector(fin[1]).lerp(Vector(fin[6]), 0.1 + k * 0.25)
		b = Vector(fin[3]).lerp(Vector(fin[4]), k / 3)
		p.seg(tuple(a + Vector((0, 0, 0))), tuple(b), 0.13, 0.05, WOOD, sides=5)
	p.seg((0, -L - 0.1, D + 0.8), (0, -L - 0.35, D + 2.3), 0.16, 0.12, WOOD, sides=6)
	_chain(p, [(0, L - 0.2, D + 0.8), (0, L + 0.4, D + 1.8), (0, L + 0.5, D + 2.6), (0, L + 0.1, D + 3.0), (0, L - 0.2, D + 2.7)], 0.17, 0.08, WOOD, sides=6)
	p.blob((0.12, 0.06, 0.1), (0.1, -L - 0.35, D + 3.2), CLOTH_WHITE, segs=(6, 4))   # a painted eye
	# thwarts, shipped oars and shields
	for k in range(7):
		y = -4.2 + k * 1.4
		p.box((2 * W * 0.85, 0.3, 0.1), (0, y, D - 0.25), WOOD_GRAY, grad=(0.1, 0.6))
	for k in range(5):
		y = -3.5 + k * 1.6
		p.seg((-2.4, y + 0.3, D + 0.1), (2.6, y - 0.2, D + 0.15), 0.05, 0.05, WOOD, sides=5)
		p.box((0.08, 0.26, 0.6), (2.6, y - 0.2, D + 0.15), WOOD, rot=(90, 0, 0))
	cols = (CLOTH_RED, IRON, CLOTH_WHITE)
	for s in (-1, 1):
		for k in range(8):
			y = -4.3 + k * 1.2
			x = section(y)[0][0] if s > 0 else section(y)[-1][0]
			z = section(y)[0][2] - 0.3
			p.seg((x, y, z), (x + s * 0.08, y, z), 0.42, 0.42, cols[(k + (s > 0)) % 3], sides=12, grad=(0.1, 0.6))
			p.seg((x + s * 0.08, y, z), (x + s * 0.16, y, z), 0.12, 0.08, IRON, sides=8)
	# mast, yard and the furled striped sail
	p.seg((0, -0.4, 0.3), (0, -0.4, 9.2), 0.14, 0.1, WOOD, sides=8)
	p.seg((-3.2, -0.4, 7.6), (3.2, -0.4, 7.6), 0.09, 0.07, WOOD, sides=6)
	for k in range(6):
		x0 = -3.0 + k * 1.0
		p.box((1.0, 0.1, 2.0), (x0 + 0.5, -0.5, 6.5), CLOTH_RED if k % 2 == 0 else CLOTH_WHITE, rot=(8, 0, 0), grad=(0.1, 0.6))
	p.seg((-3.0, -0.6, 5.5), (3.0, -0.6, 5.5), 0.22, 0.22, CLOTH_WHITE, sides=8, grad=(0.1, 0.7))   # the furled foot
	for s in (-1, 1):
		_rope(p, (0, -0.4, 9.0), (s * 1.6, -0.4 + 0.2, D + 0.3), 0.2, r=0.02)
	_rope(p, (0, -0.4, 9.0), (0, -L + 0.3, D + 2.0), 0.5, r=0.02)
	_rope(p, (0, -0.4, 9.0), (0, L - 0.4, D + 1.5), 0.6, r=0.02)
	_move_parts(p, start, Matrix.Translation((0, 0, -0.1)) @ Matrix.Rotation(math.radians(-4), 4, "X") @ Matrix.Rotation(math.radians(7), 4, "Y"))
	return p.build(bevel=0.02)


def harbor_barricade():
	"""A barricade thrown across the harbor road, about 7 m along X and 2.2 m
	high: KayKit crates and barrels stacked behind an overturned cart, sacks
	heaped between them, and a row of sharpened stakes angled out toward the
	sea (-Y). Collide it as a box (7 x 2.4 x 2)."""
	p = Prop("harbor_barricade", 505)
	# the overturned cart, bed toward -Y, wheels in the air
	cx = 0.6
	p.box((3.0, 0.14, 1.5), (cx, -0.4, 0.8), WOOD, rot=(8, 0, 0), grad=(0.1, 0.9))
	for x in (cx - 1.45, cx + 1.45):
		p.box((0.12, 0.6, 1.5), (x, -0.15, 0.8), WOOD_GRAY, rot=(8, 0, 0))
	p.seg((cx - 1.6, 0.25, 1.35), (cx + 1.6, 0.25, 1.35), 0.07, 0.07, IRON, sides=6)
	for x in (cx - 1.5, cx + 1.5):                                  # its wheels, one broken
		for k in range(10 if x < cx else 7):
			a0, a1 = k * math.tau / 10, (k + 1) * math.tau / 10
			p.seg((x, 0.25 + math.cos(a0) * 0.6, 1.35 + math.sin(a0) * 0.6), (x, 0.25 + math.cos(a1) * 0.6, 1.35 + math.sin(a1) * 0.6), 0.06, 0.06, WOOD, sides=4)
		for k in range(4):
			a = k * math.tau / 8
			p.seg((x, 0.25 - math.cos(a) * 0.58, 1.35 - math.sin(a) * 0.58), (x, 0.25 + math.cos(a) * 0.58, 1.35 + math.sin(a) * 0.58), 0.03, 0.03, WOOD_GRAY, sides=4)
	p.seg((cx - 0.4, -0.4, 0.2), (cx - 0.6, -2.0, 0.05), 0.05, 0.05, WOOD, sides=5)   # a shaft
	# stakes toward the sea
	for k in range(9):
		x = -3.3 + k * 0.82
		d = Vector((p.rng.uniform(-0.1, 0.1), -1.0, 0.75)).normalized()
		base = Vector((x, -1.0, -0.2))
		p.seg(tuple(base), tuple(base + d * 1.8), 0.07, 0.06, WOOD_GRAY, sides=5)
		p.seg(tuple(base + d * 1.8), tuple(base + d * 2.2), 0.06, 0.0, BAMBOO, sides=5)
	_beam(p, (-3.5, -1.3, 0.25), (3.5, -1.3, 0.25), 0.08, WOOD)
	for k in range(5):                                              # sacks
		p.blob((0.7, 0.5, 0.45), (-1.4 + k * 0.35 + p.rng.uniform(-0.1, 0.1), 0.4 + p.rng.uniform(-0.2, 0.2), 0.22 + (k % 2) * 0.35), HIDE, rot=(0, 0, p.rng.uniform(-30, 30)), grad=(0.1, 0.8))
	obj = p.build(bevel=0.02)
	junk = []
	for piece, loc, rot, sc in (("crates_stacked", (-2.6, 0.5, 0.0), 0.2, 0.62), ("box_large", (2.9, 0.4, 0.0), -0.3, 0.7),
								("box_small", (2.8, 0.5, 1.05), 0.5, 0.7), ("barrel_large", (-0.9, 1.0, 0.0), 0.0, 0.5),
								("barrel_small", (3.5, -0.4, 0.0), 0.0, 0.6)):
		junk += kaykit(piece, loc, rot, (sc, sc, sc))
	return _merge_materials(join_into(obj, junk))


def storm_brazier():
	"""A harbor signal brazier: an iron fire bowl on a stout tarred post 3.1 m
	tall, braced by iron struts on a ring of sea stones, its fire burning in
	all weathers under a little iron rain cap. About 1.6 m across. Collide it
	as a cylinder (r 0.4)."""
	p = Prop("storm_brazier", 506)
	for k in range(8):                                              # a ring of stones round the foot
		a = k * math.tau / 8
		p.rock((0.55, 0.45, 0.4), (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.1), SEA_STONE)
	H = 3.1
	p.seg((0, 0, -0.2), (0, 0, H), 0.2, 0.17, CHAR, sides=8, grad=(0.1, 0.9))
	for z in (0.8, 2.0, H - 0.25):
		p.seg((0, 0, z - 0.06), (0, 0, z + 0.06), 0.22, 0.22, IRON, sides=8, grad=(0.0, 0.6))
	for k in range(3):                                              # iron struts up to the bowl
		a = k * math.tau / 3 + 0.4
		p.seg((math.cos(a) * 0.19, math.sin(a) * 0.19, H - 0.9), (math.cos(a) * 0.62, math.sin(a) * 0.62, H + 0.3), 0.035, 0.035, IRON, sides=4)
	_lathe(p, [(0.03, H), (0.25, H), (0.7, H + 0.35), (0.8, H + 0.6), (0.7, H + 0.58), (0.2, H + 0.25), (0.03, H + 0.22)], 12, IRON, grad=(0.03, 0.7))
	_coals(p, (0, 0, H + 0.48), 1.2, 1.2, glow=1.8, flames=0)
	for loc, rr, fh in (((0, 0), 0.38, 1.15), ((0.22, 0.1), 0.24, 0.8), ((-0.2, -0.08), 0.22, 0.75), ((0.05, -0.25), 0.2, 0.6)):
		p.seg((loc[0], loc[1], H + 0.5), (loc[0], loc[1], H + 0.5 + fh), rr, 0.0, FLAME, sides=6, grad=(0.1, 0.95), glow=2.0, twist=fh * 50)
	for k in range(3):                                              # the rain cap on its three rods
		a = k * math.tau / 3 + 1.2
		p.seg((math.cos(a) * 0.72, math.sin(a) * 0.72, H + 0.55), (math.cos(a) * 0.5, math.sin(a) * 0.5, H + 2.0), 0.025, 0.025, IRON, sides=4)
	p.seg((0, 0, H + 1.95), (0, 0, H + 2.35), 0.75, 0.08, IRON, sides=8, grad=(0.0, 0.6))
	return p.build(bevel=0.02)


# ---------------------------------------------------------------- The Standing Sky (Vayuketh)
# Galehold, Windbreak and the Long Grass. The wind always blows toward +X:
# banners, ribbons, horsetails and kites stream that way, so props placed
# with the same yaw agree with each other.

SKY = RUNE             # pale sky blue at the top of its gradient
OCHRE = FLAG_YELLOW    # warm ochre-orange
GALE_STONE = SEA_STONE  # wind-scoured blue-gray stone


def _streamer(p, root, length, width, swatch, waves=1.6, droop=0.25, taper=0.75, n=8, phase=None, ripple=0.12):
	"""A long banner or ribbon hanging from its top edge at `root` and
	streaming down-wind (+X), rippling side to side and drooping a little
	toward its tail; it narrows to `taper` of its width."""
	x0, y0, z0 = root
	ph = p.rng.uniform(0, math.tau) if phase is None else phase
	verts = []
	for i in range(n + 1):
		t = i / n
		x = x0 + length * t
		y = y0 + math.sin(t * waves * math.pi + ph) * ripple * length * t
		z = z0 - droop * t * t
		w = width * (1.0 - taper * t)
		verts += [(x, y, z), (x, y + 0.02 * t, z - w)]
	faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(n)]
	return p.poly(verts, faces, swatch, grad=(0.05, 0.45))


def _chime_cluster(p, top, r=0.2, n=6, length=(0.25, 0.55), swatch=GOLD):
	"""Wind chimes hanging from a little disc at `top`: tubes on strings in a
	ring round a clapper, and a sail below to catch the wind."""
	x, y, z = top
	p.seg((x, y, z), (x, y, z - 0.05), r + 0.05, r + 0.05, WOOD, sides=10, grad=(0.1, 0.8))
	for k in range(n):
		a = k * math.tau / n + p.rng.uniform(-0.15, 0.15)
		cx, cy = x + math.cos(a) * r, y + math.sin(a) * r
		L = p.rng.uniform(*length)
		p.seg((cx, cy, z - 0.05), (cx, cy, z - 0.14), 0.006, 0.006, HIDE, sides=3)
		p.seg((cx + 0.02, cy, z - 0.14), (cx + 0.05, cy, z - 0.14 - L), 0.022, 0.022, swatch, sides=6, grad=(0.0, 0.6))
	p.seg((x, y, z - 0.05), (x, y, z - 0.42), 0.006, 0.006, HIDE, sides=3)
	p.seg((x, y, z - 0.30), (x, y, z - 0.33), 0.08, 0.08, WOOD, sides=8)             # clapper
	p.box((0.02, 0.16, 0.2), (x + 0.02, y, z - 0.54), SKY, rot=(0, 12, 0), grad=(0.1, 0.5))   # the wind sail


def _gable_roof(p, w, d, h, z0, swatch, trim=WOOD):
	"""A steep gable roof over a w x d room whose walls top out at z0, ridge along Y."""
	half = w / 2
	slope = math.hypot(half, h)
	ang = math.atan2(h, half)
	rows = 6
	for s in (1, -1):
		down = Vector((math.cos(ang) * s, 0, -math.sin(ang)))
		out = Vector((math.sin(ang) * s, 0, math.cos(ang)))
		base = Vector((0, 0, z0 + h))
		p.box((slope, d, 0.16), base + down * slope / 2, WOOD_GRAY, rot=(0, math.degrees(ang) * s, 0))
		for i in range(rows):
			c = base + down * slope * (i + 0.55) / rows + out * 0.13
			p.box((slope / rows * 1.12, d + 0.1, 0.12), c, swatch, rot=(0, math.degrees(ang) * s, 0), grad=(0.0, 0.8))
	for y in (-d / 2 + 0.3, d / 2 - 0.3):
		t = 0.14
		tri = [(-half + 0.3, 0, z0), (half - 0.3, 0, z0), (0, 0, z0 + h - 0.2)]
		verts = [(x, y - t / 2, z) for x, _, z in tri] + [(x, y + t / 2, z) for x, _, z in tri]
		p.poly(verts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], WOOD, grad=(0.3, 1.0))
	p.seg((0, -d / 2 - 0.15, z0 + h + 0.12), (0, d / 2 + 0.15, z0 + h + 0.12), 0.13, 0.13, trim, sides=6)


# ---- Galehold

def galehold_gate():
	"""Galehold's gate: two square towers of wind-scoured blue-gray stone
	under pale blue pyramid roofs, a timber walkway between them, and above it
	a sail-wing arch (curved spars fanned with white and blue sail cloth, an
	ochre roundel at the apex, about 12.6 m up). The passage between the towers
	is 6 m wide (x -3..3) and 5 m clear; the whole gate is 12.4 x 4.4 m, facing
	-Y. Open gate leaves, two lanterns and chimes on the front. Collide it as a
	mesh (the passage is open)."""
	p = Prop("galehold_gate", 601)
	d = Prop("galehold_gate_detail", 602)
	TW, TD, TH = 3.2, 4.0, 7.6
	for s in (-1, 1):
		x = s * (3.0 + TW / 2)
		p.box((TW + 0.4, TD + 0.4, 0.8), (x, 0, 0.3), STONE_DARK, grad=(0.3, 1.0))
		p.box((TW, TD, TH - 0.7), (x, 0, 0.7 + (TH - 0.7) / 2), GALE_STONE, grad=(0.05, 0.9))
		for k in range(7):                                                   # darker courses in the stone
			zz = 1.4 + k * 0.85 + p.rng.uniform(-0.15, 0.15)
			for side in (-1, 1):
				p.box((p.rng.uniform(0.7, 1.4), 0.06, 0.32), (x + p.rng.uniform(-0.9, 0.9), side * (TD / 2 + 0.01), zz), STONE_DARK, grad=(0.3, 0.6))
		p.box((TW + 0.3, TD + 0.3, 0.3), (x, 0, TH - 0.2), STONE_LIGHT, grad=(0.1, 0.6))    # cornice
		for side in (-1, 1):                                                 # arrow slits front and back
			p.box((0.16, 0.12, 1.2), (x, side * (TD / 2 + 0.01), 4.6), IRON)
		for cx in (-1, 1):                                                   # the timber hoarding on top
			for cy in (-1, 1):
				p.seg((x + cx * 1.5, cy * 1.85, TH), (x + cx * 1.5, cy * 1.85, TH + 1.5), 0.1, 0.09, WOOD, sides=6)
		for side in (-1, 1):
			p.box((TW + 0.2, 0.1, 0.8), (x, side * 1.85, TH + 0.45), WOOD_GRAY, grad=(0.2, 0.9))
			p.box((0.1, TD - 0.2, 0.8), (x + side * 1.55, 0, TH + 0.45), WOOD_GRAY, grad=(0.2, 0.9))
		p.seg((x, 0, TH + 1.45), (x, 0, TH + 4.0), 2.95, 0.0, SKY, sides=4, grad=(0.0, 0.55), twist=45)   # pale blue roof
		p.seg((x, 0, TH + 1.35), (x, 0, TH + 1.5), 2.95, 2.95, WOOD, sides=4, twist=45)
		p.seg((x, 0, TH + 3.8), (x, 0, TH + 5.2), 0.05, 0.04, IRON, sides=4)
		p.blob((0.2, 0.2, 0.2), (x, 0, TH + 5.2), GOLD, grad=(0.0, 0.5))
		_streamer(d, (x, 0, TH + 5.1), 3.4, 0.5, SKY if s < 0 else CLOTH_WHITE, droop=0.5)
		_streamer(d, (x, 0, TH + 4.6), 2.6, 0.3, OCHRE, droop=0.5)
		# the open gate leaves against the passage walls, and a lantern on each front corner
		p.box((0.2, 2.1, 4.4), (s * 2.85, -0.9, 2.2), WOOD, grad=(0.2, 1.0))
		for zz in (0.9, 3.5):
			p.box((0.24, 2.15, 0.18), (s * 2.85, -0.9, zz), IRON)
		lx = s * 2.75
		d.box((0.08, 0.5, 0.08), (lx, -TD / 2 - 0.25, 3.5), IRON)
		d.seg((lx, -TD / 2 - 0.5, 3.45), (lx, -TD / 2 - 0.5, 3.2), 0.01, 0.01, IRON, sides=3)
		d.box((0.3, 0.3, 0.42), (lx, -TD / 2 - 0.5, 2.98), EMBER, glow=1.6, grad=(0.1, 0.6))
		d.seg((lx, -TD / 2 - 0.5, 3.19), (lx, -TD / 2 - 0.5, 3.29), 0.22, 0.05, IRON, sides=4, twist=45)
	# the walkway between the towers, 5 m clear under it
	p.box((6.2, TD - 0.4, 0.5), (0, 0, 5.3), WOOD, grad=(0.2, 1.0))
	for side in (-1, 1):
		p.box((6.4, 0.35, 0.55), (0, side * (TD / 2 - 0.3), 5.1), WOOD_GRAY, grad=(0.2, 0.9))
		for k in range(5):
			p.seg((-2.4 + k * 1.2, side * (TD / 2 - 0.3), 5.55), (-2.4 + k * 1.2, side * (TD / 2 - 0.3), 6.5), 0.07, 0.06, WOOD, sides=5)
		p.box((6.0, 0.12, 0.12), (0, side * (TD / 2 - 0.3), 6.45), WOOD)
	for s in (-1, 1):
		p.box((0.6, TD - 0.6, 0.6), (s * 2.7, 0, 4.85), WOOD, rot=(0, s * 40, 0))   # brackets under the walkway
	# the sail-wing arch over the walkway, front and back
	apex = 12.6
	for side in (-1, 1):
		y = side * 1.55
		for s in (-1, 1):
			pts = [(s * 3.0, y, 6.5), (s * 2.9, y, 8.8), (s * 2.2, y, 10.8), (s * 1.1, y, 12.0), (0, y, apex)]
			_chain(p, pts, 0.16, 0.11, WOOD, sides=6)
			for k in range(4):                                               # fan of sail panels, alternating colors
				a, b = pts[k], pts[k + 1]
				d.poly([(0, y - side * 0.05, 6.6), (a[0], y - side * 0.05, a[2]), (b[0], y - side * 0.05, b[2])], [(0, 1, 2)],
					   CLOTH_WHITE if (k + (s > 0)) % 2 else SKY, grad=(0.05, 0.5))
				d.seg((0, y - side * 0.08, 6.6), (b[0], y - side * 0.08, b[2]), 0.035, 0.03, WOOD_GRAY, sides=4)   # battens
		d.seg((0, y - side * 0.12, apex - 0.45), (0, y - side * 0.2, apex - 0.45), 0.62, 0.62, OCHRE, sides=14, grad=(0.1, 0.6))
		d.seg((0, y - side * 0.2, apex - 0.45), (0, y - side * 0.24, apex - 0.45), 0.4, 0.4, SKY, sides=14, grad=(0.0, 0.4))
	p.seg((0, -1.7, apex), (0, 1.7, apex), 0.15, 0.15, WOOD, sides=6)
	_chime_cluster(d, (0, -TD / 2 - 0.1, 5.0), r=0.24, n=7, length=(0.3, 0.6))
	p.box((6.0, TD + 0.4, 0.1), (0, 0, 0.03), STONE_DARK, grad=(0.5, 0.9))      # paving
	obj = p.build(bevel=0.05)
	return join_into(obj, [d.build()])


def sail_tower():
	"""A tall slender Galehold sail tower: a round blue-gray stone shaft
	(3.8 m across at the foot) with a timber gallery 8 m up, a timber head and a
	pale blue conical cap about 16 m to its finial, and an axle out the front
	(-Y). The rotor is its own prop, sail_tower_rotor, hung with its hub at
	(0, 13.3, 2.35) in Godot coordinates (Blender (0, -2.35, 13.3)) and turned
	on its local Z like windmill_sails. Collide it as a cylinder (r 1.8) or trunk."""
	p = Prop("sail_tower", 603)
	d = Prop("sail_tower_detail", 604)
	p.seg((0, 0, -0.3), (0, 0, 0.8), 1.95, 1.85, STONE_DARK, sides=12, grad=(0.3, 1.0))
	z, r = 0.8, 1.7
	for k in range(10):
		r2 = r - 0.045
		p.seg((0, 0, z), (0, 0, z + 1.2), r, r2, GALE_STONE if k % 2 == 0 else STONE_LIGHT, sides=12, grad=(0.05, 0.85), jitter=0.02)
		z += 1.2
		r = r2
	# z is now 12.8, r about 1.25
	p.seg((0, 0, 8.0), (0, 0, 8.25), 2.4, 2.4, WOOD, sides=12, grad=(0.2, 0.9))          # the gallery
	for k in range(12):
		a = k * math.tau / 12
		p.seg((math.cos(a) * 2.25, math.sin(a) * 2.25, 8.25), (math.cos(a) * 2.25, math.sin(a) * 2.25, 9.2), 0.05, 0.05, WOOD, sides=4)
		p.seg((math.cos(a) * 1.5, math.sin(a) * 1.5, 7.2), (math.cos(a) * 2.3, math.sin(a) * 2.3, 8.0), 0.06, 0.05, WOOD_GRAY, sides=4)   # struts
	p.seg((0, 0, 9.1), (0, 0, 9.2), 2.3, 2.3, WOOD, sides=12)
	p.seg((0, 0, 12.8), (0, 0, 14.0), 1.45, 1.5, WOOD_GRAY, sides=12, grad=(0.1, 0.9))    # the timber head
	p.seg((0, 0, 13.9), (0, 0, 14.1), 1.7, 1.7, WOOD, sides=12)
	p.seg((0, 0, 14.1), (0, 0, 16.0), 1.75, 0.15, SKY, sides=12, grad=(0.0, 0.6))          # the cap
	p.seg((0, 0, 15.8), (0, 0, 16.8), 0.04, 0.03, IRON, sides=4)
	p.blob((0.16, 0.16, 0.16), (0, 0, 16.8), GOLD)
	_streamer(d, (0, 0, 16.7), 3.0, 0.35, SKY, droop=0.4)
	_streamer(d, (0, 0, 16.35), 2.2, 0.22, OCHRE, droop=0.4)
	p.seg((0, -1.3, 13.3), (0, -2.25, 13.3), 0.24, 0.2, WOOD, sides=8)                    # the axle
	p.box((1.0, 0.3, 1.9), (0, -1.8, 0.95), WOOD_GRAY, grad=(0.3, 1.0))                   # door
	p.box((1.3, 0.35, 0.2), (0, -1.82, 2.0), WOOD)
	for zz, a in ((3.6, 35), (6.2, -40), (10.6, 20), (13.3, 90)):                          # windows
		ra = math.radians(a)
		rr = 1.7 - (zz - 0.8) / 1.2 * 0.045 + 0.02
		p.box((0.42, 0.3, 0.7), (math.sin(ra) * rr, -math.cos(ra) * rr, zz), SHADE, rot=(0, 0, a), grad=(0.9, 1.0))
	obj = p.build(bevel=0.04)
	return join_into(obj, [d.build()])


def sail_tower_rotor():
	"""The sail tower's rotor, hub at the origin, in the X-Z plane facing -Y:
	six spars 5 m long, each carrying a triangular jib sail (white and pale blue
	by turns) and joined at the tips by a rope ring. Turned on its local Z."""
	p = Prop("sail_tower_rotor", 605)
	p.blob((0.6, 0.5, 0.6), (0, 0, 0), WOOD, segs=(8, 6))
	p.seg((0, 0.1, 0), (0, -0.45, 0), 0.2, 0.12, OCHRE, sides=8)
	tips = []
	for k in range(6):
		a = k * math.tau / 6 + math.radians(8)
		dx, dz = math.cos(a), math.sin(a)
		sx, sz = -dz, dx
		tip = (dx * 5.0, -0.05, dz * 5.0)
		tips.append(tip)
		p.seg((0, -0.05, 0), tip, 0.1, 0.06, WOOD, sides=5)
		root = (dx * 0.8, -0.12, dz * 0.8)
		clew = (dx * 3.3 + sx * 1.5, -0.12, dz * 3.3 + sz * 1.5)
		mid = (dx * 2.2 + sx * 1.15, -0.13, dz * 2.2 + sz * 1.15)                          # a little belly in the sail
		p.poly([root, (tip[0], -0.12, tip[2]), clew, mid], [(0, 1, 2, 3)], CLOTH_WHITE if k % 2 else SKY, grad=(0.05, 0.4))
	ring = tips + [tips[0]]
	_chain(p, [(x, -0.05, z) for x, _, z in ring], 0.025, 0.025, HIDE, sides=4)
	for k in range(6):                                                                    # a ribbon off each tip
		x, _, z = tips[k]
		_streamer(p, (x, -0.05, z), 0.9, 0.08, OCHRE if k % 2 else CLOTH_WHITE, droop=0.1, n=4)
	return p.build()


def cliff_house():
	"""A tall narrow Galehold house leaning into the wind (its top about 0.5 m
	toward -X): a KayKit stone ground storey 3 x 6 m (walls 3 m, door in the
	front, -Y), a jettied timber upper storey with blue shutters, a steep pale
	blue slate roof ridged front to back, a chimney, and a small windmill vane
	on the back of the ridge (static). About 4.6 x 7.6 m, 10.3 m to the vane
	tip. Collide it as a mesh."""
	p = Prop("cliff_house", 606)
	hx, hy = 1.5, 3.0
	# the timber upper storey, jettied out 0.25 m over the stone
	U0, U1 = 3.0, 5.8
	p.box((2 * hx + 0.7, 2 * hy + 0.7, 0.25), (0, 0, U0 + 0.12), WOOD_GRAY, grad=(0.2, 0.9))
	p.box((2 * hx + 0.5, 2 * hy + 0.5, U1 - U0 - 0.25), (0, 0, (U0 + 0.25 + U1) / 2), CLOTH_WHITE, grad=(0.1, 0.5))   # limewashed panels
	for x in (-hx - 0.25, hx + 0.25):                                      # the frame on the long sides
		for y in (-hy - 0.25, -1.0, 1.0, hy + 0.25):
			p.box((0.18, 0.18, U1 - U0), (x, y, (U0 + U1) / 2), WOOD, grad=(0.2, 1.0))
		p.box((0.2, 2 * hy + 0.6, 0.18), (x, 0, U1 - 0.05), WOOD)
		for y0, y1 in ((-hy - 0.25, -1.0), (1.0, hy + 0.25)):              # braces
			p.seg((x, y0, U0 + 0.3), (x, y1, U1 - 0.2), 0.07, 0.07, WOOD, sides=4, twist=45)
		sgn = 1 if x > 0 else -1
		p.box((0.1, 0.8, 1.0), (x + sgn * 0.05, 0.0, U0 + 1.5), SHADE, grad=(0.9, 1.0))  # window
		for s in (-1, 1):
			p.box((0.08, 0.42, 1.05), (x + sgn * 0.08, s * 0.66, U0 + 1.5), SKY, grad=(0.1, 0.7))   # shutters
	for y in (-hy - 0.25, hy + 0.25):                                      # the frame on the gable ends
		for x in (-hx - 0.25, 0.0, hx + 0.25):
			p.box((0.18, 0.18, U1 - U0), (x, y, (U0 + U1) / 2), WOOD, grad=(0.2, 1.0))
		sgn = 1 if y > 0 else -1
		p.box((0.9, 0.1, 1.0), (-0.8, y + sgn * 0.05, U0 + 1.5), SHADE, grad=(0.9, 1.0))
		p.box((0.95, 0.12, 0.12), (-0.8, y + sgn * 0.07, U0 + 0.95), WOOD)
	p.box((0.8, 0.5, 0.18), (0.8, -hy - 0.55, U0 - 0.25), WOOD)            # a flower box under the front
	_gable_roof(p, 2 * hx + 1.4, 2 * hy + 1.3, 3.3, U1, SKY)
	p.box((0.7, 0.7, 2.4), (0.9, 1.6, U1 + 2.0), GALE_STONE, grad=(0.1, 0.9))   # chimney
	p.box((0.9, 0.9, 0.18), (0.9, 1.6, U1 + 3.25), STONE_LIGHT, grad=(0.2, 0.7))
	# the little windmill vane on the back of the ridge
	vz = U1 + 3.3 + 0.1
	vy = hy + 0.2
	p.seg((0, vy, vz), (0, vy, vz + 0.9), 0.05, 0.04, IRON, sides=5)
	p.seg((0, vy - 0.35, vz + 0.9), (0, vy + 0.7, vz + 0.9), 0.05, 0.04, WOOD, sides=5)
	p.box((0.04, 0.6, 0.45), (0, vy + 0.72, vz + 0.95), OCHRE, grad=(0.1, 0.5))     # tail fin
	for k in range(4):
		a = k * math.pi / 2 + 0.4
		c = (math.cos(a) * 0.35, vy - 0.4, vz + 0.9 + math.sin(a) * 0.35)
		p.box((0.62, 0.03, 0.22), c, CLOTH_WHITE if k % 2 else SKY, rot=(0, -math.degrees(a), 0), grad=(0.1, 0.5))
	p.blob((0.14, 0.12, 0.14), (0, vy - 0.4, vz + 0.9), OCHRE)
	obj = p.build(bevel=0.04)
	pieces = []
	pieces += kaykit("wall_doorway", (0, -hy, 0.0), 0.0)
	pieces += kaykit("wall", (0, hy, 0.0), math.pi)
	for s in (-1, 1):
		for i, y in enumerate((-1.5, 1.5)):
			pieces += kaykit("wall_window_open" if i == (0 if s < 0 else 1) else "wall", (s * hx, y, 0.0), -s * math.pi / 2)
	for x in (-hx, hx):
		for y in (-hy, hy):
			pieces += kaykit("pillar", (x, y, 0.0))
	for y in (-1.5, 1.5):
		pieces += kaykit("floor_tile_large", (0, y, -0.07))
	obj = _merge_materials(join_into(obj, _restone(pieces, {(1, 0): GALE_STONE})))
	lean = Matrix(((1, 0, -0.05, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
	obj.data.transform(lean)
	return obj


def wind_chimes():
	"""A post about 2.4 m tall under a little pale blue hat, hung with brass
	wind chimes and three ribbons streaming down-wind (+X). Clutter: no collision."""
	p = Prop("wind_chimes", 607)
	p.rock((0.4, 0.4, 0.2), (0, 0, 0.02), STONE_DARK)
	p.seg((0, 0, -0.1), (0, 0, 2.3), 0.06, 0.05, WOOD, sides=6, grad=(0.2, 1.0))
	p.seg((0, 0, 2.28), (0, 0, 2.55), 0.38, 0.0, SKY, sides=8, grad=(0.0, 0.5))
	p.seg((0, 0, 2.55), (0, 0, 2.7), 0.02, 0.02, IRON, sides=3)
	_chime_cluster(p, (0, 0, 2.27), r=0.2, n=7)
	for k, sw in enumerate((SKY, CLOTH_WHITE, OCHRE)):
		a = k * math.tau / 3 + 0.5
		_streamer(p, (math.cos(a) * 0.3, math.sin(a) * 0.3, 2.3), 0.6, 0.07, sw, droop=0.3, n=5, taper=0.5)
	return p.build()


def kite_pole():
	"""A 6 m pole on a stone foot with a reel of line at its base, flying a big
	diamond kite (3.6 m tall, sky blue and white panels round an ochre sun, a
	bowed tail) about 12 m up and 4.5 m down-wind (+X) on a taut line. Collide
	it as a trunk."""
	p = Prop("kite_pole", 608)
	p.box((0.8, 0.8, 0.5), (0, 0, 0.2), GALE_STONE, grad=(0.2, 0.9), jitter=0.03)
	p.seg((0, 0, 0.4), (0, 0, 6.0), 0.1, 0.07, WOOD, sides=6, grad=(0.2, 1.0))
	p.seg((0, 0, 5.9), (0, 0, 6.15), 0.12, 0.05, OCHRE, sides=6)
	for s in (-1, 1):                                                   # the reel
		p.seg((0.12, s * 0.15, 1.1), (0.4, s * 0.15, 1.1), 0.03, 0.03, WOOD, sides=4)
	p.seg((0.3, -0.18, 1.1), (0.3, 0.18, 1.1), 0.18, 0.18, WOOD_GRAY, sides=10)
	p.seg((0.3, -0.12, 1.1), (0.3, 0.12, 1.1), 0.2, 0.2, HIDE, sides=10)
	p.seg((0.3, 0.2, 1.1), (0.3, 0.35, 1.25), 0.02, 0.02, WOOD, sides=3)
	p.seg((0.3, 0.0, 1.3), (0.08, 0.0, 5.9), 0.008, 0.008, HIDE, sides=3)   # the line up the pole
	# the kite, built flat in X-Z then turned to face the wind
	k = Prop("kite_pole_kite", 609)
	C = (0, 0, 0.35)
	top, rt, bot, lt = (0, 0, 1.4), (1.0, 0, 0.35), (0, 0, -1.2), (-1.0, 0, 0.35)
	for i, (a, b) in enumerate(((top, rt), (rt, bot), (bot, lt), (lt, top))):
		k.poly([C, a, b], [(0, 1, 2)], SKY if i % 2 == 0 else CLOTH_WHITE, grad=(0.05, 0.4))
	k.seg((0, -0.03, 0.35), (0, -0.07, 0.35), 0.38, 0.38, OCHRE, sides=12, grad=(0.0, 0.5))
	for j in range(8):                                                   # the sun's rays
		a = j * math.tau / 8
		k.seg((math.cos(a) * 0.42, -0.05, 0.35 + math.sin(a) * 0.42), (math.cos(a) * 0.62, -0.05, 0.35 + math.sin(a) * 0.62), 0.05, 0.0, OCHRE, sides=3)
	k.seg((0, 0.04, 1.4), (0, 0.04, -1.2), 0.03, 0.03, WOOD, sides=4)
	k.seg((-1.0, 0.04, 0.35), (1.0, 0.04, 0.35), 0.03, 0.03, WOOD, sides=4)
	tail = [(0, 0, -1.2)]
	for j in range(1, 9):
		tail.append((0.28 * j, 0.1 * math.sin(j * 1.3), -1.2 - 0.32 * j + 0.012 * j * j))
	_chain(k, tail, 0.012, 0.012, HIDE, sides=3)
	for j, (x, y, z) in enumerate(tail[1:]):                           # bows on the tail
		for s in (-1, 1):
			k.box((0.2, 0.02, 0.1), (x + s * 0.1, y, z), OCHRE if j % 2 else SKY, rot=(0, s * 25, 0), grad=(0.1, 0.4))
	kite = k.build()
	kc = Vector((4.5, 0.8, 11.5))
	kite.data.transform(Matrix.Translation(kc) @ Euler((math.radians(-20), 0, math.radians(-15))).to_matrix().to_4x4() @ Matrix.Scale(1.4, 4))
	a, b = Vector((0, 0, 6.05)), kc + Vector((0, 0, 0.2))
	pts = [tuple(a.lerp(b, t / 10) - Vector((0, 0, 0.35 * math.sin(math.pi * t / 10)))) for t in range(11)]
	_chain(p, pts, 0.022, 0.022, HIDE, sides=3)
	obj = p.build(bevel=0.02)
	return join_into(obj, [kite])


def vayuketh_shrine():
	"""Galehold's bindstone: Vayuketh of the Standing Sky, a pale stone
	elephant whose ears spread like sails (painted sky blue inside, ribbed
	like battened sails), trunk raised high into a swirl of glowing wind, on a
	pedestal at the back of a two-stepped round plinth 11 m across (0.8 m
	high), facing -Y. Four banner poles on the plinth: the back two stream long
	banners down-wind (+X), the front two carry short pennants and chimes. About 9.5 m to the top of
	the wind swirl. Collide it as a mesh (or a cylinder r 5.5)."""
	p = Prop("vayuketh_shrine", 610)
	d = Prop("vayuketh_shrine_detail", 611)
	for k, (r, z0, z1, sw) in enumerate(((5.5, -0.2, 0.4, GALE_STONE), (4.6, 0.4, 0.8, STONE_LIGHT))):
		p.seg((0, 0, z0), (0, 0, z1), r, r - 0.05, sw, sides=24, grad=(0.1, 0.9))
		p.seg((0, 0, z1 - 0.14), (0, 0, z1 - 0.06), r + 0.04, r + 0.04, OCHRE if k else SKY, sides=24, grad=(0.3, 0.8))
	P = 0.8
	cy = 1.0
	p.box((3.2, 4.6, 1.1), (0, cy + 0.3, P + 0.55), GALE_STONE, grad=(0.1, 0.9))         # pedestal
	p.box((3.5, 4.9, 0.2), (0, cy + 0.3, P + 1.2), STONE_LIGHT, grad=(0.0, 0.7))
	p.box((3.56, 4.96, 0.1), (0, cy + 0.3, P + 0.95), OCHRE, grad=(0.3, 0.8))
	B = P + 1.3
	p.blob((2.5, 3.7, 2.3), (0, cy + 0.6, B + 2.2), STONE_LIGHT, segs=(14, 10), grad=(0.05, 0.8))     # body
	for x in (-0.78, 0.78):
		for y in (-0.9, 1.5):
			p.seg((x, cy + y, B), (x, cy + y, B + 1.6), 0.48, 0.52, STONE_LIGHT, sides=8, grad=(0.2, 0.9))
			p.seg((x, cy + y, B), (x, cy + y, B + 0.16), 0.55, 0.55, OCHRE, sides=8, grad=(0.1, 0.6))
	p.blob((2.58, 1.6, 2.38), (0, cy + 0.7, B + 2.22), SKY, segs=(14, 10), grad=(0.05, 0.5))       # a sky blue saddle cloth
	p.blob((2.62, 0.16, 2.42), (0, cy - 0.1, B + 2.22), CLOTH_WHITE, segs=(14, 10), grad=(0.1, 0.5))
	p.blob((2.62, 0.16, 2.42), (0, cy + 1.5, B + 2.22), CLOTH_WHITE, segs=(14, 10), grad=(0.1, 0.5))
	p.seg((0, cy + 2.3, B + 2.7), (0.35, cy + 2.7, B + 1.7), 0.09, 0.04, STONE_LIGHT, sides=5)     # tail, blown aside
	# the head
	hc = Vector((0, cy - 1.75, B + 3.4))
	s = 1.75
	p.blob((1.0 * s, 0.9 * s, 1.0 * s), tuple(hc), STONE_LIGHT, segs=(10, 8), grad=(0.05, 0.85))
	p.blob((0.7 * s, 0.4 * s, 0.35 * s), tuple(hc + Vector((0, -0.28 * s, 0.35 * s))), STONE_LIGHT, segs=(8, 6), grad=(0.05, 0.6))
	for x in (-1, 1):
		p.blob((0.12 * s, 0.08 * s, 0.1 * s), tuple(hc + Vector((x * 0.26 * s, -0.42 * s, 0.15 * s))), IRON, segs=(6, 4))
		p.seg(tuple(hc + Vector((x * 0.25 * s, -0.35 * s, -0.35 * s))), tuple(hc + Vector((x * 0.34 * s, -0.75 * s, -0.5 * s))), 0.08 * s, 0.02 * s, BONE, sides=6)
	p.blob((0.3, 0.12, 0.3), tuple(hc + Vector((0, -0.58 * s, 0.42 * s))), SKY, glow=1.2, segs=(8, 5))   # a pale blue stone on the brow
	# the ears, spread out like sails: a stone plate with a sky blue sail painted inside and battens
	ear = [(0.0, 0.7), (1.0, 1.4), (2.2, 1.55), (3.1, 1.0), (3.4, 0.0), (3.0, -1.1), (2.3, -2.3), (1.4, -1.9), (0.3, -0.8)]
	inner = [(0.35 + x * 0.82, z * 0.82) for x, z in ear]
	for side in (-1, 1):
		M = Matrix.Translation(hc + Vector((side * 0.62 * s, 0.25, 0.1))) @ Matrix.Rotation(math.radians(side * 24), 4, "Z") @ Matrix.Rotation(math.radians(-side * 6), 4, "Y")
		for outline, y, sw, th in ((ear, 0.0, STONE_LIGHT, 0.22), (inner, -0.13, SKY, 0.05)):
			o = _plate(p if sw == STONE_LIGHT else d, [(side * x, z) for x, z in outline], y, th, sw, grad=(0.05, 0.7))
			o.data.transform(M)
		for j, (x, z) in enumerate(((2.9, 1.0), (3.1, -0.1), (2.7, -1.3))):  # battens radiating from the root
			o = d.seg((side * 0.4, -0.17, 0.05), (side * x * 0.84, -0.17, z * 0.84), 0.045, 0.03, OCHRE, sides=4)
			o.data.transform(M)
	# the trunk, raised high
	trunk = [(0, -0.4, -0.15), (0, -0.62, -0.55), (0, -0.9, -0.55), (0, -1.12, -0.1), (0, -1.18, 0.5), (0, -1.05, 1.05), (0, -0.85, 1.45), (0, -0.9, 1.75)]
	_chain(p, [tuple(hc + Vector(v) * s) for v in trunk], 0.22 * s, 0.1 * s, STONE_LIGHT, sides=8, grad=(0.1, 0.8))
	tip = hc + Vector(trunk[-1]) * s
	# a swirl of glowing wind rising from the trunk
	for j, (r0, ph, sw) in enumerate(((0.55, 0.0, SKY), (0.4, 2.1, CLOTH_WHITE), (0.7, 4.2, SKY))):
		pts = []
		for i in range(13):
			t = i / 12
			a = ph + t * math.tau * 1.3
			rr = r0 * (0.4 + t)
			pts.append(tuple(tip + Vector((math.cos(a) * rr + t * 0.6, math.sin(a) * rr, 0.3 + t * 2.0))))
		_chain(d, pts, 0.07, 0.015, sw, sides=5, grad=(0.0, 0.4), glow=0.9)
	# banner poles on the plinth
	for k, (x, y) in enumerate(((-3.0, -3.3), (3.0, -3.3), (-3.0, 3.3), (3.0, 3.3))):
		p.seg((x, y, P - 0.05), (x, y, P + 0.35), 0.28, 0.24, GALE_STONE, sides=8)
		p.seg((x, y, P + 0.35), (x, y, P + 6.2), 0.08, 0.06, WOOD, sides=6, grad=(0.2, 1.0))
		p.seg((x - 0.6, y, P + 6.0), (x + 0.6, y, P + 6.0), 0.05, 0.05, WOOD, sides=5)
		p.blob((0.2, 0.2, 0.2), (x, y, P + 6.25), OCHRE)
		if y > 0:                                                    # long banners behind the statue
			_streamer(d, (x + 0.2, y, P + 6.0), 4.2, 0.7, (SKY, CLOTH_WHITE)[k % 2], droop=0.9, taper=0.8)
			_streamer(d, (x + 0.2, y, P + 5.5), 3.0, 0.3, OCHRE, droop=0.8)
		else:                                                        # short pennants and chimes before it
			_streamer(d, (x + 0.2, y, P + 6.0), 1.5, 0.4, (SKY, CLOTH_WHITE)[k % 2], droop=0.3, taper=0.8, n=5)
			_chime_cluster(d, (x - 0.55, y, P + 5.95), r=0.18, n=6)
	obj = p.build(bevel=0.04)
	return join_into(obj, [d.build()])


def cliff_edge_rail():
	"""An 8 m run of weathered timber railing along X for a cliff's edge (the
	drop in front, -Y): five posts on stone footings, a top and a mid rail,
	rope lashings, struts on the land side (+Y), a pennant and a chime.
	Collide it as a box (8 x 0.4 x 1.2)."""
	p = Prop("cliff_edge_rail", 612)
	xs = (-4.0, -2.0, 0.0, 2.0, 4.0)
	for i, x in enumerate(xs):
		x += p.rng.uniform(-0.08, 0.08)
		p.rock((0.5, 0.5, 0.3), (x, 0, 0.02), GALE_STONE)
		p.seg((x, 0, -0.2), (x, 0, 1.25), 0.09, 0.08, WOOD_GRAY, sides=6, grad=(0.1, 1.0))
		p.blob((0.22, 0.22, 0.14), (x, 0, 1.08), HIDE, segs=(6, 4))
		p.blob((0.2, 0.2, 0.12), (x, 0, 0.6), HIDE, segs=(6, 4))
		if i % 2 == 0:
			p.seg((x, 0.05, 0.9), (x, 0.9, -0.1), 0.06, 0.06, WOOD, sides=4)   # a strut on the land side
	p.seg((-4.15, 0, 1.1), (4.15, 0, 1.12), 0.07, 0.07, WOOD, sides=5, grad=(0.1, 0.9))
	p.seg((-4.1, 0.02, 0.6), (-0.1, 0.02, 0.63), 0.055, 0.055, WOOD, sides=5)
	p.seg((0.1, 0.02, 0.62), (4.1, 0.02, 0.57), 0.055, 0.055, WOOD, sides=5)
	_streamer(p, (0.0, 0, 1.25), 1.6, 0.22, SKY, droop=0.3, n=6)
	p.seg((-2.0, 0, 1.25), (-2.0, -0.35, 1.3), 0.03, 0.03, WOOD, sides=4)
	_chime_cluster(p, (-2.0, -0.4, 1.3), r=0.1, n=5, length=(0.15, 0.3))
	return p.build(bevel=0.02)


# ---- Windbreak

def kite_glider():
	"""A sky-bandit's kite-wing glider resting on the ground: a patched hide
	wing 7.2 m across and 4 m nose to tail on a pole frame, tipped over onto its
	left wingtip, nose (-Y) a little down, a control bar under the keel and a
	painted black claw mark. About 2.2 m high. Collide it as a box, or not at all."""
	p = Prop("kite_glider", 613)
	nose, tipL, tipR = (0, -1.9, 0), (-3.6, 1.1, 0), (3.6, 1.1, 0)
	trail = [(-2.5, 1.8, 0), (-1.3, 2.2, 0), (0, 1.9, 0), (1.3, 2.2, 0), (2.5, 1.8, 0)]
	outline = [tipL] + trail + [tipR]
	for i, (a, b) in enumerate(zip(outline, outline[1:])):                  # the wing cloth, a fan from the nose
		p.poly([(nose[0], nose[1], 0.02), (a[0], a[1], 0.02), (b[0], b[1], 0.02)], [(0, 1, 2)], (HIDE, WOOD_GRAY, HIDE, CLOTH_RED, HIDE, WOOD_GRAY)[i], grad=(0.3, 0.5))
	for c, sz, sw in (((-1.6, 0.6), (0.9, 0.7), CLOTH_RED), ((1.9, 0.9), (0.7, 0.9), WOOD_GRAY), ((0.5, 1.2), (0.6, 0.5), HIDE)):
		p.box((sz[0], sz[1], 0.02), (c[0], c[1], 0.05), sw, rot=(0, 0, p.rng.uniform(-20, 20)), grad=(0.2, 0.4))   # patches
	for k in range(3):                                                       # the claw mark
		p.box((0.12, 1.1, 0.02), (0.6 + k * 0.28, 0.5, 0.06), IRON, rot=(0, 0, -18 + k * 4), grad=(0.6, 0.8))
	p.seg((0, -2.0, 0.08), (0, 2.1, 0.08), 0.07, 0.05, WOOD, sides=5)        # keel
	for t in (tipL, tipR):
		p.seg((0, -1.95, 0.08), (t[0], t[1], 0.08), 0.06, 0.04, WOOD, sides=5)   # leading edges
	p.seg((-2.3, 0.4, 0.1), (2.3, 0.4, 0.1), 0.05, 0.05, WOOD, sides=5)      # cross spar
	for s in (-1, 1):                                                        # the control bar under the keel
		p.seg((0, 0.3, 0.05), (s * 0.7, 0.1, -0.95), 0.035, 0.035, WOOD, sides=4)
	p.seg((-0.75, 0.1, -0.95), (0.75, 0.1, -0.95), 0.04, 0.04, WOOD, sides=4)
	p.blob((0.5, 0.4, 0.2), (0, 0.9, -0.05), HIDE, segs=(6, 4))                # the harness, slung under
	for o in p.parts:                                                         # tip it onto its left wing
		o.data.transform(Matrix.Translation((0, 0, 1.12)) @ Matrix.Rotation(math.radians(13), 4, "Y") @ Matrix.Rotation(math.radians(-5), 4, "X"))
	p.rock((0.6, 0.5, 0.35), (2.4, 1.6, 0.1), STONE_WARM)
	return p.build()


def bandit_lookout():
	"""A rickety sky-bandit lookout: four splayed timber legs (3.8 m square at
	the foot) crossed with crooked braces, a plank platform 6 m up under a
	patched hide lean-to, a ladder up the front (-Y), a davit with a pulley
	and a hanging basket on the +X side, and a rope line anchored at the
	platform running 11 m down-wind to a stake in the ground at (11, 0).
	About 8.5 m tall. Collide it as a mesh (or a box 4 x 4 round the legs)."""
	p = Prop("bandit_lookout", 614)
	rng = p.rng
	top = 6.0
	legs = []
	for sx in (-1, 1):
		for sy in (-1, 1):
			a = (sx * 1.9 + rng.uniform(-0.1, 0.1), sy * 1.9 + rng.uniform(-0.1, 0.1), -0.3)
			b = (sx * 1.15, sy * 1.15, top + 1.1)
			legs.append((a, b))
			p.seg(a, b, 0.15, 0.11, WOOD_GRAY, sides=6, grad=(0.1, 1.0))
			p.rock((0.6, 0.6, 0.3), (a[0], a[1], 0.0), STONE_WARM)

	def leg_at(i, z):
		a, b = legs[i]
		t = (z - a[2]) / (b[2] - a[2])
		return Vector(a).lerp(Vector(b), t)

	faces = ((0, 1), (2, 3), (0, 2), (1, 3))
	for f, (i, j) in enumerate(faces):                                  # crooked X braces, one of them broken
		for lvl, (z0, z1) in enumerate(((0.6, 3.1), (3.1, 5.6))):
			a, b = leg_at(i, z0), leg_at(j, z1)
			c, e = leg_at(j, z0), leg_at(i, z1)
			p.seg(tuple(a), tuple(b), 0.06, 0.06, WOOD, sides=4)
			if (f, lvl) == (1, 0):
				p.seg(tuple(c), tuple(c.lerp(e, 0.45) + Vector((0, 0, -0.15))), 0.06, 0.05, WOOD, sides=4)
			else:
				p.seg(tuple(c), tuple(e), 0.06, 0.06, WOOD, sides=4)
			p.blob((0.18, 0.18, 0.18), tuple(a.lerp(b, 0.5)), HIDE, segs=(5, 4))
	for k in range(9):                                                   # the platform, one plank missing
		if k == 6:
			continue
		y = -1.5 + k * 0.375
		p.box((3.2 + rng.uniform(-0.2, 0.2), 0.34, 0.08), (rng.uniform(-0.1, 0.1), y, top), WOOD if k % 3 else WOOD_GRAY,
			  rot=(rng.uniform(-2, 2), 0, rng.uniform(-3, 3)), grad=(0.2, 0.8))
	for s in (-1, 1):
		p.box((0.14, 3.4, 0.16), (s * 1.3, 0, top - 0.12), WOOD_GRAY)
	corners = [(sx * 1.45, sy * 1.45) for sx in (-1, 1) for sy in (-1, 1)]
	for x, y in corners:
		h = 2.4 if y > 0 else 1.2
		p.seg((x, y, top), (x, y, top + h), 0.07, 0.06, WOOD_GRAY, sides=5)
	for (x0, y0), (x1, y1) in (((-1.45, -1.45), (1.45, -1.45)), ((-1.45, -1.45), (-1.45, 1.45)), ((1.45, -1.45), (1.45, 1.45))):
		if y0 == y1:                                                     # the front rail: rope, a gap for the ladder
			_rope(p, (x0, y0, top + 1.0), (-0.45, y0, top + 1.0), 0.12, r=0.02)
			_rope(p, (0.45, y0, top + 1.0), (x1, y1, top + 1.0), 0.12, r=0.02)
		else:
			p.box((0.08, 2.9, 0.18), (x0, 0, top + 0.95 + rng.uniform(-0.1, 0.1)), WOOD, rot=(rng.uniform(-3, 3), 0, 0))
	# the lean-to: patched hides on poles, high at the back
	for i, x in enumerate((-1.2, -0.4, 0.4, 1.2)):
		p.box((0.84, 3.4, 0.04), (x, 0.0, top + 1.8), (HIDE, CLOTH_RED, HIDE, WOOD_GRAY)[i], rot=(-10, 0, rng.uniform(-2, 2)), grad=(0.2, 0.6))
	for x in (-1.45, 1.45):
		p.seg((x, -1.6, top + 1.52), (x, 1.6, top + 2.1), 0.05, 0.05, WOOD, sides=4)
	# the ladder
	for x in (-0.35, 0.35):
		p.seg((x, -2.5, -0.1), (x, -1.45, top + 0.9), 0.05, 0.05, WOOD, sides=4)
	for k in range(14):
		t = (k + 0.5) / 14
		y = -2.5 + (1.05) * t
		z = -0.1 + (top + 1.0) * t
		if k != 9:
			p.seg((-0.37, y, z), (0.37, y, z), 0.03, 0.03, WOOD_GRAY, sides=4)
	# the davit and pulley on the +X side, a basket on the line
	p.seg((1.45, 1.45, top + 2.3), (3.0, 0.6, top + 2.5), 0.07, 0.06, WOOD, sides=5)
	p.seg((1.45, 1.45, top + 1.4), (2.3, 1.0, top + 2.4), 0.05, 0.05, WOOD, sides=4)
	p.seg((3.0, 0.52, top + 2.3), (3.0, 0.68, top + 2.3), 0.22, 0.22, IRON, sides=10)
	p.seg((3.0, 0.6, top + 2.1), (3.0, 0.6, 1.9), 0.018, 0.018, HIDE, sides=3)
	p.seg((2.78, 0.6, top + 2.3), (1.5, 1.3, top + 0.6), 0.018, 0.018, HIDE, sides=3)
	p.seg((3.0, 0.6, 1.0), (3.0, 0.6, 1.7), 0.45, 0.5, HIDE, sides=8, grad=(0.2, 0.9))
	for k in range(3):
		a = k * math.tau / 3
		p.seg((3.0 + math.cos(a) * 0.45, 0.6 + math.sin(a) * 0.45, 1.7), (3.0, 0.6, 1.95), 0.012, 0.012, HIDE, sides=3)
	# the rope line, anchored on the back +X post, running down-wind to a stake
	a, b = Vector((1.45, 1.45, top + 2.2)), Vector((11.0, 0.0, 0.7))
	_rope(p, tuple(a), tuple(b), 0.5, r=0.03, n=12)
	p.seg((11.0, 0.0, -0.3), (10.8, 0.0, 1.0), 0.14, 0.1, WOOD, sides=5)
	p.rock((0.9, 0.8, 0.5), (11.3, 0.3, 0.1), STONE_WARM)
	p.rock((0.7, 0.7, 0.4), (10.6, -0.4, 0.1), STONE_WARM)
	for z in (0.55, 0.7, 0.85):
		p.seg((10.7, 0.0, z), (11.0, 0.0, z), 0.15, 0.15, HIDE, sides=6)
	p.seg((1.35, 1.35, top + 2.05), (1.6, 1.6, top + 2.35), 0.1, 0.1, HIDE, sides=6)
	_streamer(p, (-1.45, 1.45, top + 2.4), 1.8, 0.3, CLOTH_RED, droop=0.3, n=6)
	return p.build(bevel=0.02)


def rope_anchor():
	"""A stone-and-timber anchor: a heavy post driven into a stone collar and
	banded in iron, a coil of rope at its foot, two tie-downs to stakes, and a
	slack line trailing off down-wind (+X) along the ground. About 1.7 m tall,
	3.5 m across. Clutter: no collision (or a trunk)."""
	p = Prop("rope_anchor", 615)
	for k in range(6):
		a = k * math.tau / 6 + p.rng.uniform(-0.2, 0.2)
		p.rock((0.5, 0.45, 0.4), (math.cos(a) * 0.45, math.sin(a) * 0.45, 0.12), STONE_WARM if k % 2 else STONE_LIGHT)
	p.seg((0, 0, -0.2), (0.05, 0.0, 1.7), 0.2, 0.17, WOOD_GRAY, sides=7, grad=(0.1, 1.0))
	for z in (0.7, 1.4):
		p.seg((0, 0, z), (0, 0, z + 0.1), 0.22, 0.22, IRON, sides=7)
	for z in (1.0, 1.12, 1.24):
		p.seg((0.02, 0, z), (0.02, 0, z + 0.1), 0.23, 0.23, HIDE, sides=8)
	for k in range(3):                                                 # the coil
		p.seg((0.62, -0.5, 0.05 + k * 0.07), (0.62, -0.5, 0.11 + k * 0.07), 0.38 - k * 0.03, 0.38 - k * 0.03, HIDE, sides=10)
	p.seg((0.62, -0.5, 0.0), (0.62, -0.5, 0.26), 0.18, 0.18, SHADE, sides=8, grad=(0.9, 1.0))
	for a in (2.2, 3.8):                                               # tie-downs
		st = (math.cos(a) * 1.8, math.sin(a) * 1.8)
		_rope(p, (0, 0, 1.2), (st[0], st[1], 0.3), 0.08, r=0.022)
		p.seg((st[0], st[1], -0.1), (st[0] * 1.05, st[1] * 1.05, 0.45), 0.05, 0.04, WOOD, sides=4)
	pts = [(0.15, 0.0, 1.15), (0.9, 0.1, 0.4), (1.5, 0.2, 0.05)]
	for k in range(5):
		pts.append((1.5 + 0.45 * (k + 1), 0.2 + 0.15 * math.sin(k * 1.4), 0.04))
	_chain(p, pts, 0.025, 0.02, HIDE, sides=4)
	return p.build(bevel=0.015)


def giant_cairn():
	"""A stone giants' cairn: great flat stones stacked about 6.3 m high on a
	ring of footing boulders (5 m across), a tall capstone on top, a faint
	blue rune on its face (-Y), smaller stones scattered round. Collide it as
	a box (or a cylinder r 2.4)."""
	p = Prop("giant_cairn", 616)
	for k in range(6):
		a = k * math.tau / 6 + p.rng.uniform(-0.2, 0.2)
		p.rock((1.9, 1.6, 1.1), (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.35), STONE_WARM if k % 2 else STONE_LIGHT, rot=(0, 0, math.degrees(a)))
	z = 0.9
	for k, (sx, sy, sz) in enumerate(((3.4, 3.0, 1.3), (2.9, 2.5, 1.2), (2.4, 2.1, 1.1), (1.9, 1.7, 1.0), (1.5, 1.3, 0.9))):
		off = (p.rng.uniform(-0.2, 0.2), p.rng.uniform(-0.2, 0.2))
		p.rock((sx, sy, sz), (off[0], off[1], z + sz * 0.4), STONE_LIGHT if k % 2 else STONE_WARM, rot=(p.rng.uniform(-5, 5), p.rng.uniform(-5, 5), p.rng.uniform(0, 360)), jitter=0.05)
		z += sz * 0.8
	p.seg((0, 0, z - 0.2), (0.1, 0.05, z + 1.6), 0.5, 0.32, STONE_LIGHT, sides=5, grad=(0.05, 0.85), jitter=0.04, twist=12)
	for (x0, z0), (x1, z1) in (((-0.35, 2.0), (0.0, 2.7)), ((0.0, 2.7), (0.35, 2.0)), ((0.0, 2.7), (0.0, 1.5)), ((-0.3, 1.8), (0.3, 1.8))):
		p.seg((x0, -1.12, z0), (x1, -1.12, z1), 0.05, 0.05, SKY, sides=4, glow=0.5)   # a giant's wind rune
	for k in range(7):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(2.6, 3.6)
		sz = p.rng.uniform(0.3, 0.7)
		p.rock((sz, sz * 0.9, sz * 0.6), (math.cos(a) * r, math.sin(a) * r, 0.05), STONE_LIGHT)
	return p.build()


def thunderbird_nest():
	"""A thunderbird's nest on a rock spire: stacked blue-gray rock about 5.8 m
	tall (3.6 m across at the foot) crowned by a ring of pale storm-bleached
	branches 3.2 m across, rim about 6.9 m up, holding two glowing blue eggs,
	with crackling blue sparks between the sticks and down the rock, and dark
	blue feathers caught in it. Collide it as a trunk (or cylinder r 1.6)."""
	p = Prop("thunderbird_nest", 617)
	rng = p.rng
	z = 0.0
	for k, (sx, sy, sz) in enumerate(((3.6, 3.2, 2.2), (2.8, 2.5, 2.0), (2.2, 2.0, 1.8), (1.8, 1.7, 1.4))):
		off = (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25))
		p.rock((sx, sy, sz), (off[0], off[1], z + sz * 0.45), GALE_STONE if k % 2 else STONE_DARK, rot=(0, 0, rng.uniform(0, 360)))
		z += sz * 0.75
	top = 5.8
	p.blob((2.8, 2.8, 0.7), (0, 0, top + 0.2), WOOD_GRAY, segs=(12, 6), grad=(0.1, 0.9), jitter=0.05)
	for layer, (R, zz, n) in enumerate(((1.45, top + 0.4, 16), (1.4, top + 0.65, 14), (1.3, top + 0.88, 12))):
		for k in range(n):
			a = k * math.tau / n + rng.uniform(-0.2, 0.2) + layer * 0.3
			c = Vector((math.cos(a) * R, math.sin(a) * R, zz))
			tv = Vector((-math.sin(a), math.cos(a), 0)).lerp(Vector((math.cos(a), math.sin(a), 0)), rng.uniform(-0.5, 0.5))
			tv.z = rng.uniform(-0.25, 0.25)
			L = rng.uniform(0.9, 1.6)
			p.seg(tuple(c - tv * L / 2), tuple(c + tv * L / 2), 0.065, 0.04, WOOD_GRAY if (k + layer) % 3 else BONE, sides=5, grad=(0.1, 0.9))
	for k in range(9):                                                  # sticks poking out
		a = rng.uniform(0, math.tau)
		p.seg((math.cos(a) * 1.1, math.sin(a) * 1.1, top + 0.55), (math.cos(a) * 2.2, math.sin(a) * 2.2, top + rng.uniform(0.2, 1.2)), 0.045, 0.015, WOOD_GRAY, sides=4)
	p.blob((2.2, 2.2, 0.3), (0, 0, top + 0.62), HIDE, segs=(10, 5), grad=(0.3, 0.8))  # the lining
	for k, (x, y) in enumerate(((-0.3, 0.05), (0.3, 0.2))):
		p.blob((0.42, 0.42, 0.56), (x, y, top + 0.95), SKY, segs=(8, 6), rot=(rng.uniform(-15, 15), rng.uniform(-15, 15), 0), grad=(0.0, 0.5), glow=0.8)
	for k in range(6):                                                  # feathers
		a = rng.uniform(0, math.tau)
		p.blob((0.8, 0.14, 0.03), (math.cos(a) * 1.45, math.sin(a) * 1.45, top + 0.8), WATER if k % 2 else CLOTH_WHITE, rot=(0, 25, math.degrees(a)), segs=(6, 3))
	# crackling sparks: jagged glowing lines
	for k in range(6):
		a = rng.uniform(0, math.tau)
		start = Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, top + rng.uniform(0.5, 1.0)))
		pts = [start]
		for j in range(4):
			pts.append(pts[-1] + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0.1, 0.3))))
		_chain(p, [tuple(v) for v in pts], 0.03, 0.012, SKY, sides=4, grad=(0.0, 0.2), glow=2.5)
	pts = [Vector((1.0, -0.6, top - 0.2))]
	for j in range(7):                                                  # one crackling down the rock
		pts.append(pts[-1] + Vector((rng.uniform(-0.05, 0.25), rng.uniform(-0.25, -0.05), -rng.uniform(0.35, 0.6))))
	_chain(p, [tuple(v) for v in pts], 0.035, 0.015, SKY, sides=4, grad=(0.0, 0.2), glow=2.5)
	return p.build()


# ---- The Long Grass

def tallgrass():
	"""A clump of head-high golden-green grass, 1.7-2.2 m, about 0.9 m across:
	bent two-part blades and a few seed heads. Colored (not tinted), light
	enough to scatter densely; use a sway of about 0.12. No collision."""
	p = Prop("tallgrass", 618)
	for k in range(13):
		a = p.rng.uniform(0, math.tau)
		r = p.rng.uniform(0.0, 0.3)
		x, y = math.cos(a) * r, math.sin(a) * r
		h = p.rng.uniform(1.6, 2.2)
		la = p.rng.uniform(0, math.tau)
		lean = p.rng.uniform(0.15, 0.55)
		w = p.rng.uniform(0.045, 0.07)
		sx, sy = math.cos(a + 1.57) * w, math.sin(a + 1.57) * w
		mx, my = x + math.cos(la) * lean * 0.3, y + math.sin(la) * lean * 0.3
		tx, ty = x + math.cos(la) * lean, y + math.sin(la) * lean
		sw = BAMBOO if k % 3 == 0 else LEAF
		p.poly([(x - sx, y - sy, 0), (x + sx, y + sy, 0), (mx + sx * 0.7, my + sy * 0.7, h * 0.55), (mx - sx * 0.7, my - sy * 0.7, h * 0.55), (tx, ty, h)],
			   [(0, 1, 2, 3), (3, 2, 4)], sw, grad=(0.0, 0.45) if sw == LEAF else (0.0, 0.35))
		if k % 4 == 1:                                                  # a seed head on its own stalk
			p.seg((x, y, 0), (tx * 0.6, ty * 0.6, h + 0.1), 0.01, 0.008, BAMBOO, sides=3, grad=(0.0, 0.4))
			p.blob((0.07, 0.07, 0.3), (tx * 0.6, ty * 0.6, h + 0.22), BAMBOO, segs=(4, 3), grad=(0.0, 0.3))
	return p.build()


def lone_tree():
	"""A broad flat-topped plains tree: a short leaning trunk forking into four
	limbs that spread a flat canopy about 11 m across, its top about 7 m up.
	Collide it as a trunk (r 0.5)."""
	p = Prop("lone_tree", 619)
	fork = (0.4, 0.1, 2.6)
	_chain(p, [(0, 0, -0.4), (0.15, 0.05, 1.3), fork], 0.5, 0.36, WOOD, sides=7, grad=(0.2, 0.9))
	for k in range(3):
		a = k * math.tau / 3 + 0.4
		p.seg((0, 0, 0.2), (math.cos(a) * 1.0, math.sin(a) * 1.0, -0.2), 0.3, 0.1, WOOD, sides=5)   # root flare
	ends = []
	for k, (a, L, zt) in enumerate(((0.3, 3.8, 5.5), (1.9, 3.4, 5.8), (3.3, 4.0, 5.4), (4.6, 3.2, 5.9))):
		end = (fork[0] + math.cos(a) * L, fork[1] + math.sin(a) * L, zt)
		mid = (fork[0] + math.cos(a) * L * 0.45, fork[1] + math.sin(a) * L * 0.45, (fork[2] + zt) / 2 + 0.6)
		_chain(p, [fork, mid, end], 0.3, 0.1, WOOD, sides=6, grad=(0.2, 0.9))
		ends.append(end)
		for j in range(2):
			b = a + (j - 0.5) * 0.9
			p.seg(end, (end[0] + math.cos(b) * 1.3, end[1] + math.sin(b) * 1.3, end[2] + 0.4), 0.09, 0.03, WOOD, sides=4)
	for k, e in enumerate(ends):                                         # the flat canopy
		p.blob((4.6, 4.0, 0.8), (e[0] * 0.9, e[1] * 0.9, 6.3), LEAF, segs=(10, 5), rot=(0, 0, p.rng.uniform(0, 180)), grad=(0.0, 0.75), jitter=0.12)
	p.blob((5.2, 5.0, 0.9), (fork[0], fork[1], 6.5), LEAF, segs=(10, 5), grad=(0.0, 0.7), jitter=0.12)
	return p.build()


def _horse_mark(p, a, R, z, size, swatch):
	"""A little painted horse on a round wall at angle a (radians), facing
	along the wall: body, neck, head, legs and tail as thin strokes."""
	t = Vector((-math.sin(a), math.cos(a), 0))
	n = Vector((math.cos(a), math.sin(a), 0))
	yaw = math.degrees(a) + 90
	base = n * R

	def at(u, v, off=0.0):
		c = base + t * u * size + n * off
		return (c.x, c.y, z + v * size)

	p.box((0.55 * size, 0.03, 0.2 * size), at(0, 0), swatch, rot=(0, 0, yaw), grad=(0.2, 0.5))           # body
	p.box((0.3 * size, 0.03, 0.1 * size), at(0.32, 0.14), swatch, rot=(0, -50, yaw), grad=(0.2, 0.5))     # neck
	p.box((0.2 * size, 0.03, 0.08 * size), at(0.45, 0.24), swatch, rot=(0, 20, yaw), grad=(0.2, 0.5))     # head
	for u, sw in ((-0.22, -20), (-0.12, 15), (0.16, -15), (0.24, 25)):                                    # legs mid-gallop
		p.box((0.05 * size, 0.03, 0.28 * size), at(u, -0.2), swatch, rot=(0, sw, yaw), grad=(0.2, 0.5))
	p.box((0.28 * size, 0.03, 0.06 * size), at(-0.38, 0.02), swatch, rot=(0, 30, yaw), grad=(0.2, 0.5))   # tail


def hoofborn_yurt():
	"""A horse-folk yurt: a round felt tent 6 m across, walls 1.8 m and a low
	conical roof to 3.6 m, a band of painted galloping horses round the wall,
	rope straps, a red and ochre door at the front (-Y), a crown ring with a
	horsetail pole, and weighted ropes over the roof. Collide it as a cylinder
	(r 3)."""
	p = Prop("hoofborn_yurt", 620)
	R, W, H = 3.0, 1.8, 3.6
	p.seg((0, 0, -0.1), (0, 0, W), R, R - 0.05, CLOTH_WHITE, sides=20, grad=(0.1, 0.6))
	for z in (0.35, 1.55):
		p.seg((0, 0, z), (0, 0, z + 0.07), R + 0.03, R + 0.03, HIDE, sides=20)
	p.seg((0, 0, 0.62), (0, 0, 0.66), R + 0.02, R + 0.02, OCHRE, sides=20)
	p.seg((0, 0, 1.3), (0, 0, 1.34), R + 0.02, R + 0.02, OCHRE, sides=20)
	for k in range(12):                                                 # the horses, galloping round (not over the door)
		a = -math.pi / 2 + (k + 0.5) * math.tau / 12
		if abs(math.sin(a) + 1) < 0.08:
			continue
		_horse_mark(p, a, R + 0.02, 1.0, 0.9, CLOTH_RED if k % 2 else IRON)
	p.seg((0, 0, W - 0.05), (0, 0, H - 0.1), R + 0.25, 0.55, HIDE, sides=20, grad=(0.0, 0.55))    # felt roof
	p.seg((0, 0, W - 0.08), (0, 0, W + 0.02), R + 0.28, R + 0.26, OCHRE, sides=20)
	p.seg((0, 0, H - 0.15), (0, 0, H + 0.05), 0.6, 0.55, WOOD, sides=12)                              # crown ring
	p.box((1.0, 0.8, 0.05), (0.2, 0.1, H + 0.1), CLOTH_WHITE, rot=(0, 12, 0), grad=(0.1, 0.5))       # smoke flap
	p.seg((0, 0.25, H), (0, 0.25, H + 1.4), 0.04, 0.03, WOOD, sides=4)                                # horsetail pole
	for j in range(5):
		pts = [(0, 0.25 + 0.02 * j, H + 1.35)]
		for i in range(1, 5):
			pts.append((0.28 * i, 0.25 + 0.03 * j + 0.05 * math.sin(i + j), H + 1.35 - 0.12 * i - 0.03 * j))
		_chain(p, pts, 0.03, 0.01, HIDE if j % 2 else WOOD_GRAY, sides=3)
	for k in range(4):                                                  # weighted ropes over the roof
		a = k * math.pi / 2 + math.pi / 4
		c, s = math.cos(a), math.sin(a)
		_chain(p, [(c * 0.6, s * 0.6, H - 0.05), (c * (R + 0.25), s * (R + 0.25), W + 0.05), (c * (R + 0.35), s * (R + 0.35), 0.6)], 0.022, 0.022, HIDE, sides=4)
		p.rock((0.4, 0.35, 0.35), (c * (R + 0.35), s * (R + 0.35), 0.4), STONE_WARM)
	# the door
	p.box((1.3, 0.3, 2.0), (0, -R + 0.05, 0.95), WOOD, grad=(0.2, 0.9))
	p.box((1.0, 0.2, 1.65), (0, -R - 0.05, 0.85), CLOTH_RED, grad=(0.1, 0.8))
	p.box((0.8, 0.05, 0.25), (0, -R - 0.16, 1.35), OCHRE, grad=(0.1, 0.5))
	p.box((0.8, 0.05, 0.25), (0, -R - 0.16, 0.45), OCHRE, grad=(0.1, 0.5))
	p.seg((0, -R - 0.2, 0.9), (0, -R - 0.3, 0.9), 0.12, 0.12, SKY, sides=8)
	p.box((0.9, 0.6, 0.2), (0, -R - 0.55, 0.05), HIDE, grad=(0.2, 0.7))                               # threshold mat
	return p.build(bevel=0.03)


def _horse_skull(p, c, s=1.0):
	"""A horse skull facing -Y at c: long face, eye sockets, a jaw."""
	c = Vector(c)
	p.blob((0.36 * s, 0.34 * s, 0.32 * s), tuple(c), BONE, segs=(8, 6), grad=(0.0, 0.6))
	p.seg(tuple(c + Vector((0, -0.12, -0.02)) * s), tuple(c + Vector((0, -0.62, -0.14)) * s), 0.15 * s, 0.08 * s, BONE, sides=6, grad=(0.0, 0.6))
	p.seg(tuple(c + Vector((0, -0.1, -0.16)) * s), tuple(c + Vector((0, -0.58, -0.24)) * s), 0.07 * s, 0.05 * s, BONE, sides=5, grad=(0.1, 0.6))
	for x in (-1, 1):
		p.blob((0.1 * s, 0.1 * s, 0.1 * s), tuple(c + Vector((x * 0.14, -0.12, 0.05)) * s), IRON, segs=(6, 4))
	p.blob((0.07 * s, 0.05 * s, 0.05 * s), tuple(c + Vector((0, -0.66, -0.13)) * s), IRON, segs=(5, 3))


def horse_totem():
	"""A horse-folk totem: a 5.5 m pole with ochre and blue painted bands, a
	crossbar, three horse skulls facing -Y and long horsetail streamers blowing
	down-wind (+X). Collide it as a trunk."""
	p = Prop("horse_totem", 621)
	p.rock((0.8, 0.8, 0.4), (0, 0, 0.1), STONE_WARM)
	p.seg((0, 0, -0.3), (0, 0, 5.5), 0.13, 0.1, WOOD, sides=7, grad=(0.2, 1.0))
	for z, sw in ((1.0, OCHRE), (1.2, SKY), (2.4, OCHRE), (4.8, SKY)):
		p.seg((0, 0, z), (0, 0, z + 0.12), 0.15, 0.15, sw, sides=7)
	p.seg((-1.0, 0, 3.8), (1.0, 0, 3.8), 0.07, 0.07, WOOD, sides=5)
	_horse_skull(p, (0, -0.2, 5.4), 1.1)
	for x in (-0.8, 0.8):
		_horse_skull(p, (x, -0.12, 3.65), 0.85)
	_horse_skull(p, (0, -0.18, 2.1), 0.9)
	for k, (x, z) in enumerate(((-1.0, 3.75), (1.0, 3.75), (0.1, 5.1), (0.1, 4.4), (0.1, 2.0))):   # horsetails
		for j in range(4):
			pts = [(x, 0.02 * j, z)]
			for i in range(1, 6):
				pts.append((x + 0.3 * i, 0.03 * j + 0.06 * math.sin(i * 1.3 + j + k), z - 0.2 * i - 0.04 * j))
			_chain(p, pts, 0.035, 0.008, (HIDE, WOOD_GRAY, CLOTH_WHITE, IRON)[(j + k) % 4], sides=3)
	return p.build()


def barrow_mound():
	"""An old barrow: a grassy dome 12 m across and 3 m high (slopes under
	35 degrees, walkable) with a dry-stone entrance cut into its front (-Y):
	retaining walls, two uprights and a lintel over a dark stone slab (closed),
	and a ring of nine standing stones (one fallen) about 14.5 m across with a
	gap before the door. Collide it as a mesh."""
	p = Prop("barrow_mound", 622)
	prof = [(0.0, -0.3), (6.3, -0.3), (6.0, 0.0), (5.0, 0.45), (4.0, 1.15), (3.0, 1.85), (2.0, 2.45), (1.0, 2.85), (0.0, 3.0)]
	mound = _lathe(p, prof, 24, LEAF, grad=(0.05, 0.6), jitter=0.1)
	for v in mound.data.vertices:                                      # a notch for the entrance
		if v.co.y < -2.6 and abs(v.co.x) < 1.9 and v.co.z > 0:
			v.co.z = 0.0
	# the entrance: a sunken way between dry-stone walls to a closed door
	for s in (-1, 1):
		for k in range(4):
			y = -2.9 - k * 0.9
			h = 2.2 - k * 0.45
			_block(p, (0.8, 0.95, h), (s * 1.45, y, h / 2 - 0.05), STONE_WARM if k % 2 else STONE_LIGHT, rough=0.04)
	p.box((3.8, 1.2, 1.2), (0, -2.4, 2.5), STONE_WARM, grad=(0.1, 0.9), jitter=0.04)     # stone over the door
	for x in (-0.85, 0.85):
		_block(p, (0.5, 0.55, 2.2), (x, -3.05, 1.05), STONE_LIGHT, rough=0.03)
	_block(p, (2.4, 0.7, 0.45), (0, -3.05, 2.3), STONE_LIGHT, rough=0.03)
	p.box((1.3, 0.25, 1.95), (0, -2.85, 1.0), IRON, grad=(0.3, 0.9))                        # the dark slab, closed
	for k in range(3):
		p.seg((-0.35 + k * 0.35, -3.0, 1.6), (-0.35 + k * 0.35 + 0.1, -3.0, 1.2), 0.03, 0.03, STONE_LIGHT, sides=3)   # worn carvings
	p.box((2.2, 3.6, 0.1), (0, -4.2, 0.02), STONE_DARK, grad=(0.5, 0.9))                    # the way in
	# the ring of standing stones
	for k in range(10):
		a = -math.pi / 2 + k * math.tau / 10
		if k == 0:
			continue                                                  # the gap before the door
		x, y = math.cos(a) * 7.2, math.sin(a) * 7.2
		h = p.rng.uniform(1.6, 2.6)
		if k == 6:
			p.seg((x, y, 0.25), (x + math.cos(a + 1.3) * h, y + math.sin(a + 1.3) * h, 0.3), 0.36, 0.26, STONE_LIGHT, sides=5, jitter=0.04)
			continue
		p.seg((x, y, -0.3), (x, y, h), 0.38, 0.26, STONE_LIGHT, sides=5, grad=(0.1, 0.9), jitter=0.04, twist=p.rng.uniform(0, 70))
		p.rock((0.9, 0.9, 0.3), (x, y, 0.0), STONE_DARK)
	return p.build()


def herd_bones():
	"""The bleached skeleton of a giant grazer sunk in the grass: a spine 5 m
	long, arching ribs (a few broken), a long horned skull at -X, the pelvis
	and scattered leg bones. About 6 x 3.4 m and 1.6 m high. Clutter: no
	collision (or a box)."""
	p = Prop("herd_bones", 623)
	rng = p.rng
	spine = [(-2.2 + 0.5 * i, 0.0, 0.55 + 0.25 * math.sin(i / 9 * math.pi) - 0.02 * i) for i in range(10)]
	_chain(p, spine, 0.1, 0.07, BONE, sides=6, grad=(0.0, 0.6))
	for x, y, z in spine:
		p.blob((0.2, 0.22, 0.24), (x, y, z + 0.05), BONE, segs=(6, 4), grad=(0.0, 0.5))
	for i in range(1, 7):                                              # ribs
		x, _, z = spine[i]
		for s in (-1, 1):
			if (i, s) in ((3, 1), (5, -1)):
				_chain(p, [(x, 0, z), (x + 0.05, s * 0.9, z + 0.35), (x + 0.1, s * 1.2, z + 0.05)], 0.06, 0.04, BONE, sides=5, grad=(0.0, 0.6))
				continue                                              # broken off
			_chain(p, [(x, 0, z), (x + 0.05, s * 0.9, z + 0.4), (x + 0.1, s * 1.5, z - 0.05), (x + 0.15, s * 1.6, -0.2)], 0.06, 0.04, BONE, sides=5, grad=(0.0, 0.6))
	p.blob((0.9, 1.2, 0.6), (2.4, 0, 0.4), BONE, segs=(8, 5), grad=(0.0, 0.6))          # pelvis
	for s in (-1, 1):
		p.seg((2.4, s * 0.5, 0.4), (2.9, s * 0.8, 0.1), 0.14, 0.1, BONE, sides=5)
	# the skull: long, low, with swept horns
	sc = Vector((-2.9, 0.1, 0.45))
	p.blob((0.9, 0.75, 0.6), tuple(sc), BONE, segs=(8, 6), grad=(0.0, 0.6), rot=(0, 0, 10))
	p.seg(tuple(sc + Vector((-0.3, 0, -0.05))), tuple(sc + Vector((-1.3, -0.15, -0.25))), 0.28, 0.16, BONE, sides=6, grad=(0.0, 0.6))
	for s in (-1, 1):
		p.blob((0.2, 0.18, 0.16), tuple(sc + Vector((-0.2, s * 0.3, 0.1))), IRON, segs=(6, 4))
		_chain(p, [tuple(sc + Vector((0.2, s * 0.3, 0.2))), tuple(sc + Vector((0.6, s * 0.9, 0.6))), tuple(sc + Vector((1.1, s * 1.1, 0.8))), tuple(sc + Vector((1.4, s * 0.95, 1.1)))],
			   0.13, 0.03, BONE, sides=6, grad=(0.2, 0.9))
	for k in range(4):                                                 # scattered leg bones
		a = (rng.uniform(-1.5, 2.5), rng.choice([-1, 1]) * rng.uniform(1.6, 2.2), 0.1)
		L = rng.uniform(0.9, 1.4)
		ang = rng.uniform(0, math.tau)
		b = (a[0] + math.cos(ang) * L, a[1] + math.sin(ang) * L, 0.12)
		_bone(p, a, b, r=0.07)
	return p.build()


# ---- Agnavar's Hearth (the caldera of the fire god's eternal fire)

def _plumes(name, seed, wisps, alpha=0.3):
	"""Several smoke wisps [(base, height, r)] as one see-through part, ready to join."""
	s = Prop(name, seed)
	for base, height, r in wisps:
		x, y, z = base
		n = max(5, int(height / (r * 1.3)))
		for k in range(n):
			t = k / (n - 1)
			x += s.rng.uniform(-0.06, 0.1) * r / 0.18
			y += s.rng.uniform(-0.06, 0.06) * r / 0.18
			rr = r * (0.7 + 1.6 * t) * (1.0 - 0.45 * t * t)
			s.blob((rr * 2, rr * 2, rr * 1.6), (x, y, z + height * t), SHADE, segs=(7, 5), grad=(0.25, 0.45), jitter=rr * 0.12)
	return _translucent(s.build(), alpha, 0.9)


def _flame_column(p, c, r, h, tongues=6, glow=2.0):
	"""A tall column of fire standing at c: a core of nested cones and tiers
	of twisted tongues climbing it, each tier narrower, so the silhouette
	flickers up like fire instead of reading as one spike."""
	x, y, z = c
	p.seg((x, y, z), (x, y, z + h * 0.8), r * 0.85, 0.0, EMBER, sides=8, grad=(0.0, 0.7), glow=glow, twist=10)
	p.seg((x, y, z), (x + 0.05 * r, y, z + h * 0.92), r * 0.6, 0.0, FLAME, sides=7, grad=(0.0, 0.8), glow=glow * 1.25, twist=37)
	p.seg((x, y, z), (x - 0.05 * r, y + 0.05 * r, z + h), r * 0.3, 0.0, PETAL_YELLOW, sides=6, grad=(0.0, 0.3), glow=glow * 1.25, twist=70)
	tiers = ((0.0, 1.0, 0.42, tongues), (0.22, 0.8, 0.42, max(3, tongues - 3)), (0.45, 0.6, 0.38, max(3, tongues - 5)), (0.66, 0.42, 0.3, 3))
	for L, (tz, tr, th, count) in enumerate(tiers):
		for k in range(count):
			a = (k + 0.5 * L) * math.tau / count + p.rng.uniform(-0.25, 0.25)
			d = r * tr * p.rng.uniform(0.5, 0.75)
			hh = h * th * p.rng.uniform(0.7, 1.15)
			lean = r * tr * 0.2
			z0 = z + h * tz
			p.seg((x + math.cos(a) * d, y + math.sin(a) * d, z0), (x + math.cos(a) * (d + lean), y + math.sin(a) * (d + lean), z0 + hh),
				  r * tr * p.rng.uniform(0.35, 0.5), 0.0, (FLAME, EMBER, PETAL_YELLOW)[(k + L) % 3], sides=6, grad=(0.0, 0.85), glow=glow, twist=k * 23 + L * 11)


def _ramp(p, x0, x1, y_foot, y_top, z0, z1, n, swatches=(STONE_DARK, STONE_LIGHT)):
	"""A walkable ramp up +Y from (y_foot, z0) to (y_top, z1), laid as n slabs so it reads as worn steps."""
	for k in range(n):
		ya = y_foot + (y_top - y_foot) * k / n
		yb = y_foot + (y_top - y_foot) * (k + 1) / n
		za, zb = z0 + (z1 - z0) * k / n, z0 + (z1 - z0) * (k + 1) / n
		p.poly([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb), (x0, ya, z0 - 0.3), (x1, ya, z0 - 0.3), (x1, yb, z0 - 0.3), (x0, yb, z0 - 0.3)],
			   [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
			   swatches[k % len(swatches)], grad=(0.1, 0.8))
		p.box((x1 - x0, 0.12, 0.05), ((x0 + x1) / 2, yb - 0.06, zb + 0.005), IRON, grad=(0.3, 0.8))   # a worn lip on each tread


def _column(p, x, y, z0, h, r=0.7, broken=False, sw=STONE_DARK):
	"""A basalt column: a square base, a hexagonal shaft in drums and a capital
	(or a snapped, jagged top when broken)."""
	p.box((r * 2.6, r * 2.6, 0.5), (x, y, z0 + 0.25), STONE_LIGHT, grad=(0.1, 0.8))
	p.box((r * 2.3, r * 2.3, 0.2), (x, y, z0 + 0.6), STONE_DARK, grad=(0.1, 0.6))
	drums = max(1, int(h / 1.8))
	for k in range(drums):
		za = z0 + 0.7 + (h - 0.7) * k / drums
		zb = z0 + 0.7 + (h - 0.7) * (k + 1) / drums - 0.04
		p.seg((x, y, za), (x, y, zb), r, r * 0.97, sw if k % 2 else STONE_DARK, sides=6, grad=(0.2, 1.0), twist=k * 4)
	top = z0 + h
	if broken:
		for k in range(4):
			a = k * math.tau / 4 + p.rng.uniform(0, 0.8)
			p.seg((x + math.cos(a) * r * 0.4, y + math.sin(a) * r * 0.4, top - 0.1), (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, top + p.rng.uniform(0.3, 0.8)),
				  r * 0.5, 0.05, STONE_DARK, sides=4, grad=(0.2, 1.0))
		_crack(p, [(x + r * 0.9, y - r * 0.3, top - 0.2), (x + r * 0.95, y - r * 0.4, top - 1.2), (x + r * 0.92, y - r * 0.2, top - 2.0)], r=0.05, glow=1.4)
	else:
		p.seg((x, y, top), (x, y, top + 0.4), r, r * 1.5, STONE_DARK, sides=6, grad=(0.1, 0.7))
		p.box((r * 3.0, r * 3.0, 0.45), (x, y, top + 0.62), STONE_LIGHT, grad=(0.0, 0.7))
		p.box((r * 3.04, r * 3.04, 0.12), (x, y, top + 0.45), GOLD, grad=(0.4, 1.0))
	return top


def eternal_forge():
	"""Agnavar's Eternal Forge, the colossal ruined forge-temple at the heart of
	the caldera: a basalt terrace 28 x 19 m (1.2 m high) with a broad ramp up at
	the front (-Y), a second dais at the back (2.4 m) with its own ramp, and on it
	the hearth altar where a column of eternal fire burns to about 14 m. Two
	great ivory tusks rise from gold-banded sockets either side and meet over
	the fire under Agnavar's basalt head (20 m up): the tusk arch. Broken
	colonnades run down both sides (a few columns whole under their lintels),
	the back wall stands in ragged blocks, fallen drums and glowing cracks on the
	floor, a brazier on a pillar either side of the ramp's foot. About 30 x 24 m.
	Faces -Y. Collide it as a mesh: the ramps and terraces are walkable."""
	p = Prop("eternal_forge", 701)
	rng = p.rng
	T1, T2 = 1.2, 2.4                     # the terrace and dais heights
	# the terrace, faced with a step moulding
	p.box((28.0, 19.0, T1 + 0.3), (0, 2.0, (T1 - 0.3) / 2), STONE_DARK, grad=(0.3, 1.0))
	p.box((28.5, 19.5, 0.3), (0, 2.0, 0.0), STONE_LIGHT, grad=(0.3, 1.0))
	p.box((28.2, 19.2, 0.14), (0, 2.0, T1 - 0.05), IRON, grad=(0.2, 0.8))
	for k in range(14):                                         # floor slabs, a few lighter or cracked
		x = -13.0 + k * 2.0 + rng.uniform(-0.3, 0.3)
		y = rng.uniform(-6.0, 9.0)
		p.box((rng.uniform(1.4, 2.2), rng.uniform(1.4, 2.2), 0.06), (x, y, T1 + 0.03), STONE_LIGHT if k % 3 else STONE_WARM, rot=(0, 0, rng.uniform(-6, 6)), grad=(0.3, 0.9))
	_ramp(p, -5.0, 5.0, -12.0, -7.5, 0.0, T1, 5)
	for s in (-1, 1):                                           # the ramp's cheeks
		p.box((0.9, 4.6, 0.7), (s * 5.45, -9.75, 0.35), STONE_LIGHT, grad=(0.1, 0.9))
		p.box((1.1, 1.1, 1.3), (s * 5.45, -12.0, 0.65), STONE_DARK, grad=(0.1, 0.9))
		p.box((1.2, 1.2, 0.16), (s * 5.45, -12.0, 1.35), GOLD, grad=(0.3, 1.0))
	# the dais at the back and its ramp
	p.box((17.0, 11.0, T2 - T1 + 0.2), (0, 4.5, T1 + (T2 - T1 - 0.2) / 2 + 0.1), STONE_DARK, grad=(0.2, 1.0))
	p.box((17.3, 11.3, 0.16), (0, 4.5, T2 - 0.06), GOLD, grad=(0.4, 1.0))
	p.box((17.1, 11.1, 0.1), (0, 4.5, T2 + 0.0), STONE_DARK, grad=(0.1, 0.7))
	_ramp(p, -3.5, 3.5, -4.5, -1.0, T1, T2 + 0.05, 4)
	# the hearth altar: two stepped blocks and an iron fire bowl, gold-rimmed
	ax, ay = 0.0, 4.0
	_block(p, (8.0, 7.0, 1.0), (ax, ay, T2 + 0.5), STONE_DARK, rough=0.02)
	_block(p, (6.4, 5.6, 0.8), (ax, ay, T2 + 1.4), STONE_LIGHT, rough=0.02)
	p.box((6.5, 5.7, 0.14), (ax, ay, T2 + 1.75), GOLD, grad=(0.3, 1.0))
	for s in (-1, 1):                                           # carved flame reliefs on the front
		for k in range(3):
			x = ax + s * (0.9 + k * 1.1)
			p.seg((x, ay - 3.52, T2 + 0.15), (x, ay - 3.52, T2 + 0.85), 0.24, 0.0, EMBER, sides=4, glow=1.2, grad=(0.1, 0.6))
	HZ = T2 + 1.8
	bowl = _lathe(p, [(1.2, HZ), (2.5, HZ + 0.3), (2.9, HZ + 1.0), (2.7, HZ + 1.05), (2.2, HZ + 0.55), (1.0, HZ + 0.4)], 16, IRON, grad=(0.0, 0.7))
	bowl.data.transform(Matrix.Translation((ax, ay, 0)))
	rim = _lathe(p, [(2.68, HZ + 0.96), (2.98, HZ + 0.96), (2.98, HZ + 1.1), (2.68, HZ + 1.1)], 16, GOLD, grad=(0.4, 1.0))
	rim.data.transform(Matrix.Translation((ax, ay, 0)))
	_coals(p, (ax, ay, HZ + 0.75), 4.6, 4.6, glow=1.6, flames=0)
	_flame_column(p, (ax, ay, HZ + 0.7), 2.1, 9.8, tongues=12, glow=2.0)
	for k in range(5):                                          # sparks flung up round it
		a = k * math.tau / 5 + 0.4
		p.blob((0.22, 0.22, 0.3), (ax + math.cos(a) * 1.4, ay + math.sin(a) * 1.4, HZ + 8 + k * 0.9), FLAME, segs=(5, 3), glow=2.4)
	# the tusk arch: ivory tusks from gold-banded basalt sockets, meeting under Agnavar's head
	for s in (-1, 1):
		bx = s * 6.8
		_block(p, (2.8, 2.8, 1.4), (bx, ay, T2 + 0.7), STONE_DARK, rough=0.02)
		p.seg((bx, ay, T2 + 1.4), (bx, ay, T2 + 1.9), 1.35, 1.2, IRON, sides=10)
		p.seg((bx, ay, T2 + 1.75), (bx, ay, T2 + 1.95), 1.28, 1.28, GOLD, sides=10, grad=(0.3, 1.0))
		pts = [(bx, ay, T2 + 1.8), (s * 7.6, ay, 7.5), (s * 7.4, ay, 11.2), (s * 5.8, ay, 14.6), (s * 3.4, ay, 16.9), (s * 0.9, ay - 0.2, 17.8)]
		_chain(p, pts, 1.05, 0.32, BONE, sides=10, grad=(0.0, 0.7))
		for k, t in enumerate((0.12, 0.45)):                   # gold bands up each tusk
			i = int(t * (len(pts) - 1))
			f = t * (len(pts) - 1) - i
			c = Vector(pts[i]).lerp(Vector(pts[i + 1]), f)
			d = (Vector(pts[i + 1]) - Vector(pts[i])).normalized()
			r = 1.05 - (1.05 - 0.32) * t + 0.07
			p.seg(tuple(c - d * 0.2), tuple(c + d * 0.2), r, r, GOLD, sides=10, grad=(0.3, 1.0))
		_crack(p, [(s * 7.95, ay - 0.3, 6.0), (s * 8.0, ay - 0.25, 8.5), (s * 7.75, ay - 0.3, 10.8)], r=0.06, glow=1.2)
	hc = (0.0, ay - 1.0, 19.2)
	_elephant_head(p, hc, 2.6, STONE_DARK, trunk=[(0, -0.4, -0.2), (0, -0.7, -0.55), (0, -0.9, -0.9), (0, -1.2, -1.0), (0, -1.4, -0.85)], tusks=(False, False))
	p.seg((0, hc[1] + 0.3, hc[2] + 1.15), (0, hc[1] + 0.2, hc[2] + 1.35), 1.0, 0.7, GOLD, sides=8, glow=0.25)       # brow band
	for k, (dx, h, r) in enumerate(((0.0, 1.6, 0.45), (0.35, 1.0, 0.3), (-0.35, 1.05, 0.3))):                       # the flame on his brow
		p.seg((dx, hc[1] - 0.3, hc[2] + 1.3), (dx * 1.2, hc[1] - 0.4, hc[2] + 1.3 + h), r, 0.0, FLAME, sides=6, grad=(0.1, 0.9), glow=1.8, twist=k * 20)
	for s in (-1, 1):                                           # ember eyes
		p.blob((0.34, 0.2, 0.26), (hc[0] + s * 0.68, hc[1] - 1.12, hc[2] + 0.4), EMBER, segs=(6, 4), glow=2.2)
	# the colonnades down both sides: whole columns under a lintel, broken ones between
	sides = {-1: [(-5.5, 9.0, False), (-1.5, 9.0, False), (2.5, 3.6, True), (6.5, 6.0, True)],
			 1: [(-5.5, 4.8, True), (-1.5, 9.0, False), (2.5, 9.0, False), (6.5, 9.0, False)]}
	for s in (-1, 1):
		x = s * 12.2
		tops = []
		for y, h, broken in sides[s]:
			tops.append((y, _column(p, x, y, T1, h, broken=broken), broken))
		for (ya, za, ba), (yb, zb, bb) in zip(tops, tops[1:]):
			if not ba and not bb:
				p.box((2.4, yb - ya + 2.4, 1.1), (x, (ya + yb) / 2, za + 1.4), STONE_DARK, grad=(0.1, 0.9))
				p.box((2.5, yb - ya + 2.5, 0.12), (x, (ya + yb) / 2, za + 0.9), GOLD, grad=(0.3, 1.0))
		for y, top, broken in tops:                             # a lintel fallen from a broken one, lying on the floor
			if broken and rng.random() < 0.7:
				yaw = rng.uniform(-30, 30)
				p.box((2.2, 3.6, 1.0), (x - s * 2.3, y + 1.0, T1 + 0.45), STONE_DARK, rot=(rng.uniform(-6, 6), rng.uniform(-8, 8), yaw), grad=(0.1, 0.9))
				_crack(p, [(x - s * 2.3 - 0.4, y - 0.4, T1 + 0.97), (x - s * 2.3 + 0.3, y + 1.2, T1 + 0.97)], r=0.04, glow=1.2)
	for x, y, yaw in ((-8.5, -3.5, 25), (8.8, 0.5, -60), (-9.5, 8.0, 80)):   # column drums rolled across the floor
		a = math.radians(yaw)
		p.seg((x, y, T1 + 0.68), (x + math.cos(a) * 1.7, y + math.sin(a) * 1.7, T1 + 0.68), 0.68, 0.68, STONE_DARK, sides=6, grad=(0.2, 1.0))
	# the back wall: great blocks standing to ragged heights, a gap in the middle
	for k in range(8):
		x = -12.25 + k * 3.5
		if k in (3, 4):
			h = 1.5 if k == 3 else 0.9
		else:
			h = (3.4, 7.8, 5.2, 0, 0, 6.6, 8.6, 4.0)[k]
		for j, z in enumerate([T1 + 2.2 * i for i in range(max(1, int(math.ceil(h / 2.2))))]):
			bh = min(2.2, T1 + h - z)
			if bh < 0.3:
				continue
			_block(p, (3.45, 1.8, bh - 0.05), (x + rng.uniform(-0.08, 0.08), 10.6, z + bh / 2), STONE_DARK if (j + k) % 2 else STONE_LIGHT, rough=0.03)
		if h > 5:
			p.box((3.5, 0.2, 0.3), (x, 9.65, T1 + 4.6), GOLD, grad=(0.3, 1.0))
	for k in range(6):                                          # rubble at the wall's foot
		p.rock((rng.uniform(1.0, 1.8), rng.uniform(0.9, 1.5), rng.uniform(0.6, 1.0)), (rng.uniform(-11, 11), rng.uniform(8.6, 9.3), T1 + 0.3), STONE_DARK, grad=(0.3, 1.0))
	# glowing cracks running out across the floor from the altar
	for k, a in enumerate((-2.6, -2.1, -1.1, -0.5, 0.0, 3.1)):
		pts = []
		r0 = 5.0
		for j in range(5):
			r = r0 + j * (1.3 if abs(math.sin(a)) > 0.5 else 1.5)
			aa = a + math.sin(j * 1.7 + k) * 0.08
			z = (T2 if r < 5.5 and -1 < ay + math.sin(aa) * r < 10 and abs(math.cos(aa) * r) < 8.5 else T1) + 0.05
			pts.append((ax + math.cos(aa) * r, ay + math.sin(aa) * r, z))
		_crack(p, pts, r=0.07, glow=1.5)
	for s in (-1, 1):                                           # braziers either side of the ramp's foot
		_brazier_stand(p, s * 7.5, -12.5, 2.2)
	for k in range(10):                                         # pilgrims' offerings along the dais edge: candles and little ingots
		x = -7.5 + k * 1.65
		if abs(x) < 3.8:
			continue
		if k % 2:
			_candle(p, (x, -0.75, T2 + 0.05), h=0.3, r=0.06)
		else:
			p.box((0.3, 0.14, 0.1), (x, -0.8, T2 + 0.1), GOLD, grad=(0.1, 0.7), rot=(0, 0, rng.uniform(-30, 30)))
	return p.build(bevel=0.06)


def colossal_anvil():
	"""An anvil as big as a house, left by the god's own smiths: dark iron about
	8.2 m long and 4.1 m tall on a stepped basalt footing (9.4 x 5 m), split by a
	great crack that glows from inside, a glowing ingot the size of a cart on its
	face and a hammer head fallen at its foot. Horn toward +X. Collide it as a box."""
	p = Prop("colossal_anvil", 703)
	p.box((9.4, 5.0, 0.6), (0.4, 0, 0.1), STONE_DARK, grad=(0.3, 1.0))
	p.box((8.4, 4.2, 0.4), (0.3, 0, 0.55), STONE_LIGHT, grad=(0.2, 0.9))
	p.box((8.5, 4.3, 0.1), (0.3, 0, 0.6), GOLD, grad=(0.4, 1.0))
	S = 6.6
	_anvil(p, (0, 0, 0.75), S, IRON)
	top = 0.75 + 0.58 * S
	# the crack: a wedge split down the waist, glowing from within
	for s in (-1, 1):
		y = s * (0.1 * S + 0.02)
		pts = [(-0.3, y, top), (0.05, y, top - 0.9), (-0.2, y, top - 1.8), (0.2, y, top - 2.6), (0.0, y, 1.5)]
		_chain(p, pts, 0.16, 0.08, EMBER, sides=4, grad=(0.0, 0.5), glow=1.8)
	for k, (x, z) in enumerate(((-0.3, top + 0.03), (0.3, top + 0.03))):
		p.box((0.3, 0.3 * S * 0.95, 0.08), (x - 0.05, 0, z), CHAR, grad=(0.8, 1.0))
	_crack(p, [(2.2, -0.15 * S, top - 0.2), (3.0, -0.15 * S, top - 0.35), (3.8, -0.1 * S, top - 0.3)], r=0.06, glow=1.4)
	# the ingot, glowing, and a scatter of scale on the face
	p.box((2.1, 0.9, 0.55), (-1.2, 0.1, top + 0.3), EMBER, glow=1.8, grad=(0.0, 0.6))
	p.box((1.7, 0.6, 0.2), (-1.2, 0.1, top + 0.62), FLAME, glow=2.2, grad=(0.0, 0.4))
	for k in range(6):
		p.blob((0.3, 0.22, 0.06), (p.rng.uniform(-2.8, 2.0), p.rng.uniform(-0.8, 0.8), top + 0.04), IRON if k % 2 else EMBER, segs=(5, 3), glow=0.0 if k % 2 else 1.2)
	# the hammer head, fallen at its foot, its broken haft
	p.box((1.6, 1.1, 1.1), (2.8, -2.9, 0.6), IRON, rot=(0, 0, 18), grad=(0.1, 0.8))
	p.box((1.7, 1.2, 0.14), (2.8, -2.9, 0.62), GOLD, rot=(0, 0, 18), grad=(0.3, 1.0))
	p.seg((2.4, -3.0, 0.7), (0.4, -3.6, 0.35), 0.18, 0.16, WOOD, sides=6, grad=(0.2, 0.9))
	p.rock((0.4, 0.4, 0.35), (0.35, -3.6, 0.35), CHAR, jitter=0.1)
	return p.build(bevel=0.05)


def pilgrim_brazier():
	"""A tall stone brazier on the pilgrims' path: a square basalt pillar 1.9 m
	tall, tapering, banded in gold, a carved tusk either side of its head, an
	iron bowl of embers on top with a low flame (to about 2.9 m), pilgrims'
	ribbons tied round its neck and offerings at its foot. About 1.4 m square.
	Collide it as a trunk or a box."""
	p = Prop("pilgrim_brazier", 705)
	p.box((1.3, 1.3, 0.35), (0, 0, 0.12), STONE_LIGHT, grad=(0.1, 0.9))
	p.seg((0, 0, 0.3), (0, 0, 1.75), 0.55, 0.4, STONE_DARK, sides=4, grad=(0.1, 0.9), twist=45)
	for z in (0.55, 1.5):
		p.seg((0, 0, z), (0, 0, z + 0.1), 0.56 - (z - 0.3) * 0.1 + 0.03, 0.56 - (z - 0.3) * 0.1 + 0.03, GOLD, sides=4, grad=(0.3, 1.0), twist=45)
	p.box((0.8, 0.8, 0.16), (0, 0, 1.8), STONE_LIGHT, grad=(0.0, 0.7))
	for s in (-1, 1):                                          # carved tusks curving up the sides of the head
		_chain(p, [(s * 0.35, -0.2, 1.3), (s * 0.55, -0.35, 1.6), (s * 0.55, -0.3, 1.95)], 0.08, 0.02, BONE, sides=6, grad=(0.0, 0.6))
	bowl = _lathe(p, [(0.15, 1.85), (0.5, 1.95), (0.62, 2.18), (0.56, 2.2), (0.44, 2.02), (0.12, 1.93)], 12, IRON, grad=(0.0, 0.7))
	_coals(p, (0, 0, 2.08), 0.95, 0.95, glow=1.4, flames=0)
	for loc, rr, fh in (((0, 0), 0.26, 0.8), ((0.15, 0.08), 0.16, 0.5), ((-0.14, -0.07), 0.15, 0.45)):
		p.seg((loc[0], loc[1], 2.1), (loc[0], loc[1], 2.1 + fh), rr, 0.0, FLAME, sides=6, grad=(0.1, 0.95), glow=1.5, twist=fh * 60)
	for k, (col, a) in enumerate(((CLOTH_RED, 0.3), (GOLD, 1.9), (CLOTH_RED, 3.4), (CLOTH_WHITE, 4.6))):   # ribbons
		r = 0.5
		x, y = math.cos(a) * r, math.sin(a) * r
		p.seg((x, y, 1.42), (x * 1.15, y * 1.15, 0.95 - k * 0.07), 0.035, 0.02, col, sides=4, grad=(0.2, 0.9))
	p.seg((0, 0, 1.38), (0, 0, 1.44), 0.49, 0.49, CLOTH_RED, sides=4, twist=45)
	for x, y in ((-0.5, -0.8), (0.45, -0.85)):                 # offerings at the foot
		p.seg((x, y, 0.0), (x, y, 0.08), 0.14, 0.18, CLAY, sides=8)
		p.blob((0.16, 0.16, 0.06), (x, y, 0.09), EMBER, segs=(6, 3), glow=1.2)
	_candle(p, (0.05, -0.8, 0.0), h=0.2, r=0.04)
	return p.build(bevel=0.03)


def salamander_idol():
	"""The salamander-kin's idol: a fire-lizard of black stone coiled three
	times round itself on an octagonal plinth (2.6 m across, 0.9 m high), its
	head raised in the middle to about 3.6 m, jaws open on a glowing throat,
	ember eyes and a ridge of spines, a glowing stripe down its belly; offerings
	of coals, ingots and bones round the plinth. Faces -Y. Collide it as a box."""
	p = Prop("salamander_idol", 707)
	rng = p.rng
	P = 0.9
	p.seg((0, 0, -0.2), (0, 0, 0.35), 1.3, 1.28, STONE_DARK, sides=8, grad=(0.1, 0.9), twist=22.5)
	p.seg((0, 0, 0.35), (0, 0, P), 1.1, 1.06, STONE_LIGHT, sides=8, grad=(0.1, 0.8), twist=22.5)
	p.seg((0, 0, P - 0.12), (0, 0, P - 0.04), 1.12, 1.12, GOLD, sides=8, grad=(0.3, 1.0), twist=22.5)
	# the coil: tail on the outside at the bottom, winding inward and up
	pts = []
	n = 30
	for k in range(n + 1):
		t = k / n
		a = -math.pi / 2 + math.pi * 0.6 - t * math.tau * 2.4
		r = 0.85 * (1 - t) + 0.1
		z = P + 0.1 + t * 1.3 + 0.08 * (1 - t)
		pts.append((math.cos(a) * r, math.sin(a) * r, z))
	neck = [pts[-1], (0.0, -0.15, P + 2.0), (0.0, -0.3, P + 2.45)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		t = i / n
		ra = 0.05 + 0.26 * t
		rb = 0.05 + 0.26 * (i + 1) / n
		p.seg(a, b, ra, rb, STONE_DARK, sides=8, grad=(0.1, 0.9))
		if i % 2 == 0 and 4 < i:                                # spines down the back
			c = Vector(a)
			p.seg(tuple(c + Vector((0, 0, ra * 0.6))), tuple(c + Vector((0, 0, ra * 0.6 + 0.12 + 0.12 * t))), 0.05 + 0.04 * t, 0.0, CHAR, sides=4)
		if i % 3 == 0 and i > 6:                                # the glowing belly stripe
			c = Vector(a)
			p.blob((ra * 0.6, ra * 0.6, 0.08), tuple(c - Vector((0, 0, ra * 0.7))), EMBER, segs=(5, 3), glow=1.3)
	_chain(p, neck, 0.31, 0.26, STONE_DARK, sides=8, grad=(0.1, 0.9))
	for k in range(3):
		c = Vector(neck[1]).lerp(Vector(neck[2]), k / 2)
		p.seg(tuple(c + Vector((0, 0.25, 0.1))), tuple(c + Vector((0, 0.42, 0.35))), 0.07, 0.0, CHAR, sides=4)
	# the head: a flat lizard skull, jaws parted on a glowing throat
	hc = Vector((0.0, -0.55, P + 2.55))
	p.blob((0.52, 0.8, 0.3), tuple(hc), STONE_DARK, segs=(8, 6), grad=(0.05, 0.8), rot=(-12, 0, 0))
	p.blob((0.45, 0.7, 0.14), tuple(hc + Vector((0, -0.08, -0.22))), STONE_DARK, segs=(8, 5), grad=(0.1, 0.9), rot=(10, 0, 0))   # lower jaw
	p.blob((0.3, 0.45, 0.1), tuple(hc + Vector((0, -0.12, -0.12))), EMBER, segs=(6, 4), glow=1.8)                                # the fire in its throat
	for s in (-1, 1):
		p.blob((0.12, 0.1, 0.1), tuple(hc + Vector((s * 0.2, -0.05, 0.13))), EMBER, segs=(6, 4), glow=2.2)
		p.seg(tuple(hc + Vector((s * 0.15, 0.25, 0.1))), tuple(hc + Vector((s * 0.35, 0.6, 0.35))), 0.06, 0.0, CHAR, sides=4)       # horns
	for s in (-1, 1):                                           # four stubby legs gripping the coil
		for k, i in enumerate((12, 22)):
			c = Vector(pts[i])
			out = Vector((c.x, c.y, 0)).normalized() if c.length > 0.1 else Vector((1, 0, 0))
			side = Vector((-out.y, out.x, 0)) * s
			foot = c + side * 0.35 + Vector((0, 0, -0.22))
			p.seg(tuple(c), tuple(foot), 0.08, 0.06, STONE_DARK, sides=5)
			for j in range(3):
				p.seg(tuple(foot), tuple(foot + side * 0.1 + out * (j - 1) * 0.08 + Vector((0, 0, -0.05))), 0.025, 0.0, CHAR, sides=3)
	# offerings on and round the plinth
	for k in range(8):
		a = k * math.tau / 8 + 0.2
		x, y = math.cos(a) * 1.35, math.sin(a) * 1.35
		kind = k % 4
		if kind == 0:
			p.seg((x, y, 0.0), (x, y, 0.1), 0.16, 0.2, CLAY, sides=8)
			p.blob((0.2, 0.2, 0.08), (x, y, 0.11), EMBER, segs=(6, 3), glow=1.3)
		elif kind == 1:
			p.box((0.28, 0.12, 0.08), (x, y, 0.04), GOLD, rot=(0, 0, math.degrees(a)), grad=(0.1, 0.7))
		elif kind == 2:
			_bone(p, (x - 0.15, y, 0.04), (x + 0.15, y + 0.05, 0.05), r=0.03)
		else:
			_candle(p, (x, y, 0.0), h=0.16, r=0.04)
	return p.build(bevel=0.02)


def salamander_den():
	"""A salamander-kin dwelling: a low mound of heaped basalt and glassy slag
	about 6 m across and 2.7 m tall, its entrance at the front (-Y) a dark hole
	1.5 m high framed in slag, lit by a glow from deep inside and a bed of coals
	at the threshold, glowing cracks in the mound and a vent at the top.
	Collide it as a box."""
	p = Prop("salamander_den", 709)
	rng = p.rng
	prof = [(3.1, -0.2), (3.0, 0.4), (2.6, 1.3), (1.9, 2.1), (1.0, 2.6), (0.5, 2.7), (0.35, 2.4), (0.0, 2.3)]
	_lathe(p, prof, 13, STONE_DARK, grad=(0.1, 0.95), jitter=0.22, keep=2.2)
	for k in range(16):                                         # heaped basalt blocks and slag lumps on the mound
		a = rng.uniform(0, math.tau)
		if abs(a - 3 * math.pi / 2) < 0.5:
			continue
		r = rng.uniform(1.6, 3.0)
		z = 2.6 * (1 - (r / 3.1) ** 2) + 0.1
		if rng.random() < 0.5:
			p.seg((math.cos(a) * r, math.sin(a) * r, z - 0.3), (math.cos(a) * r * 1.05, math.sin(a) * r * 1.05, z + rng.uniform(0.3, 0.8)), 0.3, 0.28, CHAR, sides=6, grad=(0.1, 0.9))
		else:
			p.rock((0.8, 0.7, 0.5), (math.cos(a) * r, math.sin(a) * r, z), IRON, grad=(0.0, 0.7), jitter=0.12)
	# the entrance: a frame of slag round a dark hole, the glow inside
	ey = -2.55
	p.box((1.3, 1.2, 1.5), (0, ey + 0.35, 0.75), CHAR, grad=(0.9, 1.0))
	p.box((0.9, 0.2, 1.1), (0, ey + 0.9, 0.55), EMBER, grad=(0.3, 0.9), glow=1.2)
	for s in (-1, 1):
		p.rock((0.6, 0.8, 1.7), (s * 0.9, ey + 0.1, 0.8), IRON, grad=(0.0, 0.6), jitter=0.08)
	p.rock((2.4, 0.9, 0.6), (0, ey + 0.1, 1.75), IRON, grad=(0.0, 0.6), jitter=0.08)
	_coals(p, (0, ey - 0.35, 0.02), 1.1, 0.7, glow=1.3, flames=2, flame_h=0.3)
	for k, a in enumerate((0.7, 2.4, 4.0, 5.4)):               # glowing cracks down the mound
		pts = []
		for j in range(4):
			t = j / 3
			r = 1.0 + t * 1.9
			z = 2.6 * (1 - (r / 3.1) ** 2) + 0.08
			aa = a + math.sin(t * 3 + k) * 0.12
			pts.append((math.cos(aa) * r, math.sin(aa) * r, z))
		_crack(p, pts, r=0.05, glow=1.4)
	p.seg((0, 0, 2.5), (0, 0, 2.62), 0.33, 0.3, EMBER, sides=9, glow=1.8)      # the vent at the top
	p.blob((0.4, 0.4, 0.12), (0, 0, 2.62), FLAME, segs=(7, 3), glow=2.2)
	for k in range(3):                                          # scorch marks and a bone or two at the door
		_bone(p, (rng.uniform(-1.4, 1.4), ey - rng.uniform(0.6, 1.2), 0.04), (rng.uniform(-1.4, 1.4), ey - rng.uniform(0.6, 1.4), 0.05), r=0.035)
	p.blob((3.2, 2.0, 0.08), (0, ey - 0.9, 0.0), SHADE, segs=(10, 4), grad=(0.6, 0.8))
	obj = p.build(bevel=0.03)
	return join_into(obj, [_plumes("salamander_den_smoke", 710, [((0.05, 0, 2.7), 2.4, 0.16)], alpha=0.3)])


def heretic_ruin():
	"""What's left of a heretics' encampment the faithful put to the torch: two
	collapsed, scorched tents (charred poles leaning, burnt canvas slumped on
	the ground), a broken cage-altar in the middle (a stone altar with an iron
	cage on it, bars bent and burst open, a chain hanging), a split crate, a
	toppled heretic banner and ash over everything, a few embers still glowing.
	About 9 x 7 m. Collide it as a mesh (or a box round the altar)."""
	p = Prop("heretic_ruin", 711)
	rng = p.rng
	p.blob((9.0, 7.0, 0.1), (0, 0, 0.0), SHADE, segs=(14, 5), grad=(0.55, 0.8))           # the ash
	# the cage-altar
	_block(p, (1.9, 1.3, 0.9), (0, 0.2, 0.45), STONE_DARK, rough=0.04)
	p.box((2.1, 1.5, 0.12), (0, 0.2, 0.92), IRON, grad=(0.1, 0.7))
	_crack(p, [(-0.9, -0.46, 0.2), (-0.6, -0.47, 0.5), (-0.7, -0.47, 0.85)], r=0.03, glow=1.2)
	cz = 0.98
	p.box((1.6, 1.1, 0.08), (0, 0.2, cz), IRON, grad=(0.2, 0.8))
	bars = 12
	for k in range(bars):
		a = k * math.tau / bars
		x, y = math.cos(a) * 0.72, 0.2 + math.sin(a) * 0.5
		if k in (8, 9, 10):                                    # the front bars burst outward
			out = Vector((math.cos(a), math.sin(a), 0))
			top = Vector((x, y, cz + 1.0)) + out * (0.35 + 0.1 * (k - 8))
			p.seg((x, y, cz), (x + out.x * 0.1, y + out.y * 0.1, cz + 0.6), 0.03, 0.03, IRON, sides=4)
			p.seg((x + out.x * 0.1, y + out.y * 0.1, cz + 0.6), tuple(top), 0.03, 0.03, IRON, sides=4)
			continue
		p.seg((x, y, cz), (x * 0.92, 0.2 + (y - 0.2) * 0.92, cz + 1.65), 0.03, 0.03, IRON, sides=4)
	ring = _lathe(p, [(0.62, cz + 1.62), (0.7, cz + 1.62), (0.7, cz + 1.7), (0.62, cz + 1.7)], 12, IRON, grad=(0.2, 0.8))
	ring.data.transform(Matrix.Diagonal((1.0, 0.72, 1.0, 1.0)))
	ring.data.transform(Matrix.Translation((0, 0.2, 0)))
	p.seg((0, 0.2, cz + 1.68), (0, 0.2, cz + 2.0), 0.05, 0.02, IRON, sides=5)
	links = [(0.35, 0.3, cz + 1.6), (0.4, 0.25, cz + 1.3), (0.38, 0.28, cz + 1.0), (0.3, 0.25, cz + 0.7)]
	for a, b in zip(links, links[1:]):
		p.seg(a, b, 0.03, 0.03, IRON, sides=4)
	p.box((0.6, 0.4, 0.04), (0.1, 0.25, cz + 0.06), CHAR, rot=(0, 0, 20))
	_bone(p, (-0.3, 0.1, cz + 0.08), (0.2, 0.35, cz + 0.09), r=0.03)
	# two collapsed tents
	for (tx, ty, yaw, s) in ((-3.0, 1.2, 15, 1.0), (2.9, 1.6, -25, 0.9)):
		a = math.radians(yaw)
		cs, sn = math.cos(a), math.sin(a)

		def at(x, y, z, tx=tx, ty=ty, cs=cs, sn=sn, s=s):
			return (tx + (x * cs - y * sn) * s, ty + (x * sn + y * cs) * s, z * s)
		_beam(p, at(-1.2, -1.3, 0.0), at(-0.3, -0.9, 2.0), 0.07)          # one pole still leaning up
		_beam(p, at(1.2, -1.2, 0.0), at(0.5, 0.6, 0.35), 0.07)            # the rest fallen
		_beam(p, at(-1.0, 1.4, 0.05), at(1.4, 1.1, 0.12), 0.07)
		_beam(p, at(-0.3, -0.9, 2.0), at(0.1, 1.2, 0.5), 0.06)            # the ridge, sagging to the ground
		# the canvas: burnt slumps over the fallen frame
		verts = [at(-1.5, -1.5, 0.05), at(0.0, -1.1, 0.9), at(1.4, -1.4, 0.05), at(1.5, 1.3, 0.05), at(0.1, 1.2, 0.55), at(-1.4, 1.5, 0.05), at(-0.3, -0.9, 1.9), at(0.0, 0.2, 0.9)]
		p.poly(verts, [(0, 1, 7, 4, 5), (1, 2, 3, 4, 7), (0, 6, 1), (6, 7, 1)], CHAR, grad=(0.2, 0.9))
		p.poly([(x, y, z + 0.03) for x, y, z in (at(-0.6, -0.4, 1.1), at(0.6, -0.5, 0.55), at(0.4, 0.8, 0.5), at(-0.5, 0.6, 0.7))], [(0, 1, 2, 3)], HIDE, grad=(0.5, 1.0))
		for k in range(4):                                       # glowing burnt edges
			x0, y0 = rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2)
			_crack(p, [at(x0, y0, 0.1), at(x0 + 0.4, y0 + 0.2, 0.12)], r=0.035, glow=1.2)
	# a split crate, a toppled banner, scattered debris
	for k, (x, y, yaw) in enumerate(((1.6, -2.2, 20), (2.3, -1.6, -40))):
		p.box((0.8, 0.8, 0.7 - k * 0.35), (x, y, (0.7 - k * 0.35) / 2), CHAR if k else WOOD_GRAY, rot=(0, 0, yaw), grad=(0.2, 0.9))
	p.seg((-2.4, -2.4, 0.1), (0.8, -2.9, 0.12), 0.05, 0.05, IRON, sides=5)
	p.poly([(-1.8, -2.5, 0.12), (-0.4, -2.72, 0.13), (-0.2, -1.6, 0.06), (-1.6, -1.4, 0.05)], [(0, 1, 2, 3)], PETAL_PURPLE, grad=(0.6, 1.0))   # the heretics' violet cloth
	p.poly([(-1.3, -2.3, 0.14), (-0.8, -2.4, 0.15), (-0.7, -1.9, 0.1), (-1.2, -1.8, 0.1)], [(0, 1, 2, 3)], CHAR, grad=(0.5, 1.0))
	for k in range(7):
		x, y = rng.uniform(-4, 4), rng.uniform(-3, 3)
		if abs(x) < 1.3 and abs(y - 0.2) < 1.0:
			continue
		if k % 3 == 0:
			p.blob((0.3, 0.25, 0.1), (x, y, 0.06), EMBER, segs=(6, 3), glow=1.2)
		else:
			_beam(p, (x, y, 0.07), (x + rng.uniform(-0.7, 0.7), y + rng.uniform(-0.5, 0.5), 0.1), 0.045)
	obj = p.build(bevel=0.02)
	return join_into(obj, [_plumes("heretic_ruin_smoke", 712, [((-2.6, 1.5, 0.3), 1.6, 0.1), ((3.1, 1.2, 0.2), 1.3, 0.09)], alpha=0.28)])


def magma_pool():
	"""A flat pool of bubbling magma about 8 m across: glowing lava (surface
	0.06 m over the ground) swirled with brighter flows, dark crusts floating
	on it, bubbles rising, inside a low rim of black rock (0.3-0.5 m). Scenery:
	no collision (the rim can take a few boxes if wanted)."""
	p = Prop("magma_pool", 713)
	rng = p.rng
	n = 18
	outline = []
	for k in range(n):
		a = k * math.tau / n
		r = 3.7 * (1 + 0.1 * math.sin(a * 3 + 0.5) + 0.06 * math.sin(a * 5 + 1.3))
		outline.append((math.cos(a) * r, math.sin(a) * r))
	verts = [(0, 0, 0.06)] + [(x, y, 0.06) for x, y in outline] + [(0, 0, -0.2)] + [(x, y, -0.2) for x, y in outline]
	faces = []
	for i in range(n):
		j = (i + 1) % n
		faces.append((0, 1 + i, 1 + j))
		faces.append((n + 1, n + 2 + j, n + 2 + i))
		faces.append((1 + i, n + 2 + i, n + 2 + j, 1 + j))
	pool = p.poly(verts, faces, EMBER, grad=(0.2, 0.6))
	pool.data.materials[0] = atlas_material(1.8)
	for k in range(7):                                          # brighter swirls
		a0 = rng.uniform(0, math.tau)
		r0 = rng.uniform(0.6, 2.4)
		pts = [(math.cos(a0 + j * 0.35) * (r0 + j * 0.15), math.sin(a0 + j * 0.35) * (r0 + j * 0.15), 0.08) for j in range(4)]
		_chain(p, pts, 0.14, 0.06, FLAME, sides=4, grad=(0.0, 0.5), glow=2.3)
	for k in range(6):                                          # dark crust floating
		a = rng.uniform(0, math.tau)
		r = rng.uniform(0.5, 2.8)
		p.blob((rng.uniform(0.5, 1.1), rng.uniform(0.4, 0.8), 0.1), (math.cos(a) * r, math.sin(a) * r, 0.07), IRON, rot=(0, 0, rng.uniform(0, 180)), segs=(6, 3), grad=(0.2, 0.9), jitter=0.04)
	for k in range(6):                                          # bubbles
		a = rng.uniform(0, math.tau)
		r = rng.uniform(0.2, 2.6)
		s = rng.uniform(0.18, 0.4)
		p.blob((s, s, s * 0.7), (math.cos(a) * r, math.sin(a) * r, 0.06), PETAL_YELLOW if k % 2 else FLAME, segs=(7, 4), grad=(0.0, 0.5), glow=2.4)
	for k in range(n + 6):                                      # the rim of black rock
		a = k * math.tau / (n + 6) + rng.uniform(-0.05, 0.05)
		i = int(a / math.tau * n) % n
		ox, oy = outline[i]
		r = math.hypot(ox, oy) + 0.35
		s = rng.uniform(0.6, 1.0)
		p.rock((s, s * 0.8, rng.uniform(0.35, 0.55)), (math.cos(a) * r, math.sin(a) * r, 0.1), STONE_DARK if k % 3 else IRON, rot=(0, 0, math.degrees(a)), grad=(0.3, 1.0))
	return p.build()


# ---- Smokewood (the living forest that never stops smoking)

BARK = WOOD_GRAY          # dark, sooty bark (drawn from the swatch's darker half)
LEAF_RED = CLOTH_RED      # crimson leaves
LEAF_ORANGE = EMBER       # rust-orange leaves (unlit: the ember swatch without glow)


def _smolder_crown(p, c, r, n, rng, flat=0.8):
	"""A crown of red and orange leaf masses round c."""
	x, y, z = c
	p.rock((r * 2.0, r * 2.0, r * 1.7 * flat), (x, y, z), LEAF_RED, grad=(0.35, 1.0), jitter=0.05)
	for k in range(n):
		a = k * math.tau / n + rng.uniform(-0.3, 0.3)
		d = r * rng.uniform(0.75, 1.05)
		s = r * rng.uniform(0.9, 1.25)
		sw, gr = (LEAF_ORANGE, (0.25, 0.9)) if k % 2 else (LEAF_RED, (0.2, 1.0))
		p.rock((s * 1.2, s * 1.2, s * flat), (x + math.cos(a) * d, y + math.sin(a) * d, z + rng.uniform(-0.5, 0.3) * r), sw, grad=gr, jitter=0.05)
	p.rock((r * 1.2, r * 1.2, r * 0.9 * flat), (x, y, z + r * 0.9 * flat), LEAF_ORANGE, grad=(0.2, 0.7), jitter=0.05)


def _smolder_trunk(p, pts, r0, r1, rng, cracks=3):
	"""A dark, sooty trunk along pts with thin glowing cracks in the bark."""
	_chain(p, pts, r0, r1, BARK, sides=7, grad=(0.7, 1.0))
	n = len(pts) - 1
	for k in range(cracks):
		a = k * math.tau / cracks + rng.uniform(0, 1.0)
		i = rng.randrange(0, max(1, n - 1))
		lo, hi = Vector(pts[i]), Vector(pts[i + 1])
		rr = (r0 + (r1 - r0) * (i + 0.5) / n) * 0.97
		c = []
		for j in range(4):
			t = 0.1 + 0.25 * j
			v = lo.lerp(hi, t)
			aa = a + math.sin(j * 1.3 + k) * 0.15
			c.append((v.x + math.cos(aa) * rr, v.y + math.sin(aa) * rr, v.z))
		_crack(p, c, r=0.03, glow=1.2)


def smoldering_tree():
	"""A tall living Smokewood tree, about 11 m: a straight dark trunk (sooty
	bark, thin cracks glowing ember-orange) on flared roots, boughs rising to a
	crown of crimson and rust-orange leaf, and a thin plume of see-through smoke
	curling up from the crown to about 14 m. Its trunk is slim near the ground:
	use it in a zone's tree_mix (the 0.3 m "trunk" collider fits)."""
	p = Prop("smoldering_tree", 721)
	rng = p.rng
	pts = [(0, 0, -0.3), (0.05, 0.02, 2.0), (0.15, -0.05, 4.2), (0.1, 0.0, 6.4), (0.2, 0.05, 8.0)]
	_smolder_trunk(p, pts, 0.36, 0.16, rng, cracks=3)
	for k in range(4):                                          # root flare
		a = k * math.tau / 4 + 0.5
		p.seg((0, 0, 0.5), (math.cos(a) * 0.9, math.sin(a) * 0.9, -0.2), 0.2, 0.06, BARK, sides=5, grad=(0.5, 1.0))
	crowns = [((0.2, 0.05, 8.8), 2.3)]
	for k, (z, a, L) in enumerate(((4.6, 0.3, 2.2), (5.4, 2.4, 2.0), (6.2, 4.3, 1.9), (7.0, 1.3, 1.5))):
		base = Vector((0.12, 0, z))
		end = base + Vector((math.cos(a) * L, math.sin(a) * L, L * 0.8))
		p.seg(tuple(base), tuple(end), 0.13, 0.05, BARK, sides=5, grad=(0.5, 1.0))
		crowns.append((tuple(end + Vector((0, 0, 0.4))), 1.6))
	for c, r in crowns:
		_smolder_crown(p, c, r, 5, rng)
	p.blob((0.3, 0.3, 0.2), (0.25, 0.1, 10.1), EMBER, segs=(6, 4), glow=1.3)      # an ember in the crown where the smoke leaves
	obj = p.build()
	return join_into(obj, [_plumes("smoldering_tree_smoke", 722, [((0.25, 0.1, 10.2), 3.8, 0.2)], alpha=0.28)])


def smoldering_tree_b():
	"""A broader, lower Smokewood tree, about 7.5 m: a short thick trunk forking
	low into three leaning limbs, cracks glowing in the bark and a glowing split
	at the fork, a wide crown of crimson and orange leaf about 8 m across, two
	thin plumes of smoke from it. Use it in a zone's tree_mix (trunk collider)."""
	p = Prop("smoldering_tree_b", 723)
	rng = p.rng
	fork = (0.1, 0.05, 2.2)
	_smolder_trunk(p, [(0, 0, -0.3), (0.05, 0.0, 1.2), fork], 0.45, 0.36, rng, cracks=3)
	for k in range(5):
		a = k * math.tau / 5 + 0.2
		p.seg((0, 0, 0.5), (math.cos(a) * 1.1, math.sin(a) * 1.1, -0.2), 0.24, 0.07, BARK, sides=5, grad=(0.5, 1.0))
	p.blob((0.45, 0.3, 0.35), (fork[0], fork[1] - 0.2, fork[2] + 0.05), EMBER, segs=(6, 4), glow=1.5)   # the glowing split at the fork
	ends = []
	for k, (a, L, zt) in enumerate(((0.4, 2.9, 5.3), (2.5, 2.7, 5.6), (4.4, 3.1, 5.1))):
		end = (fork[0] + math.cos(a) * L, fork[1] + math.sin(a) * L, zt)
		mid = (fork[0] + math.cos(a) * L * 0.45, fork[1] + math.sin(a) * L * 0.45, (fork[2] + zt) / 2 + 0.3)
		_smolder_trunk(p, [fork, mid, end], 0.3, 0.1, rng, cracks=1)
		ends.append(end)
	for e in ends:
		_smolder_crown(p, (e[0] * 0.95, e[1] * 0.95, e[2] + 0.6), 1.7, 4, rng, flat=0.6)
	_smolder_crown(p, (fork[0], fork[1], 6.2), 1.9, 3, rng, flat=0.55)
	obj = p.build()
	return join_into(obj, [_plumes("smoldering_tree_b_smoke", 724, [((ends[0][0], ends[0][1], 7.0), 3.0, 0.18), ((ends[2][0], ends[2][1], 6.8), 2.4, 0.15)], alpha=0.26)])


def glowing_roots():
	"""A patch of exposed roots creeping over the ground, about 2.4 x 1.8 m and
	0.25 m high: dark gnarled roots with ember-orange cracks glowing along
	their tops. Clutter-sized; as MultiMesh clutter the glow reads by color
	only (the clutter shader has no emission). No collision."""
	p = Prop("glowing_roots", 725)
	rng = p.rng
	for k in range(5):
		a = k * math.tau / 5 + rng.uniform(-0.3, 0.3)
		L = rng.uniform(0.8, 1.3)
		pts = [(0, 0, 0.12)]
		x, y = 0.0, 0.0
		for j in range(4):
			aa = a + rng.uniform(-0.35, 0.35)
			x += math.cos(aa) * L / 4 * (1.3 if abs(math.cos(a)) > 0.6 else 1.0)
			y += math.sin(aa) * L / 4
			pts.append((x, y, (0.2, 0.16, 0.06, -0.08)[j]))
		_chain(p, pts, 0.1, 0.03, BARK, sides=5, grad=(0.5, 1.0))
		_chain(p, [(px, py, pz + (0.1 - 0.07 * i / 4) * 0.85) for i, (px, py, pz) in enumerate(pts[:4])], 0.022, 0.012, EMBER, sides=4, grad=(0.0, 0.4), glow=1.6)
	p.blob((0.45, 0.4, 0.26), (0, 0, 0.08), BARK, segs=(7, 4), grad=(0.5, 1.0))
	p.blob((0.2, 0.16, 0.08), (0.04, -0.12, 0.2), EMBER, segs=(5, 3), glow=1.6)
	return p.build()


def charcoal_kiln():
	"""A charcoal-burner's kiln: a dome of turf and earth over stacked wood,
	about 4 m across and 2 m tall, smoking from a crown vent and three side
	vents (see-through smoke), a glowing stoking hole at the front (-Y) half
	stopped with sods, a ring of stakes round the foot; beside it (+X) a stack
	of split cordwood and a rake and shovel leaning on it. About 7 x 4.4 m.
	Collide it as a box."""
	p = Prop("charcoal_kiln", 727)
	rng = p.rng
	prof = [(2.1, -0.15), (2.05, 0.4), (1.75, 1.15), (1.2, 1.7), (0.5, 2.0), (0.22, 2.02), (0.18, 1.9), (0.0, 1.88)]
	_lathe(p, prof, 14, WOOD_GRAY, grad=(0.5, 1.0), jitter=0.08, keep=1.9)
	for k in range(14):                                         # sods laid over it
		a = k * math.tau / 14 + rng.uniform(-0.1, 0.1)
		for j, (r, z) in enumerate(((1.95, 0.55), (1.5, 1.35))):
			if j == 0 and abs(a - 3 * math.pi / 2) < 0.35:
				continue
			sw, gr = (LEAF, (0.9, 1.0)) if (k * 2 + j) % 7 == 0 else ((WOOD_GRAY, (0.75, 1.0)), (CHAR, (0.2, 0.9)), (WOOD_GRAY, (0.55, 0.85)))[(k + j) % 3]
			p.box((0.62, 0.3, 0.42), (math.cos(a) * r, math.sin(a) * r, z), sw, rot=(0, 35 + j * 15, math.degrees(a)), grad=gr)
	p.blob((4.4, 4.4, 0.25), (0, 0, 0.0), SHADE, segs=(12, 4), grad=(0.6, 0.85))            # soot round its foot
	p.seg((0, 0, 1.9), (0, 0, 2.05), 0.22, 0.18, EMBER, sides=8, glow=1.2)                  # crown vent
	vents = [(0.5, 0.9), (2.2, 0.9), (4.0, 0.9)]
	for a, z in vents:
		r = 1.9
		p.seg((math.cos(a) * (r - 0.05), math.sin(a) * (r - 0.05), z), (math.cos(a) * (r + 0.05), math.sin(a) * (r + 0.05), z), 0.1, 0.1, EMBER, sides=6, glow=1.0)
	# the stoking hole at the front
	p.box((0.7, 0.5, 0.6), (0, -1.95, 0.32), CHAR, grad=(0.8, 1.0))
	p.box((0.5, 0.1, 0.4), (0, -1.85, 0.3), EMBER, glow=1.4)
	p.blob((0.3, 0.25, 0.14), (0.05, -2.05, 0.1), FLAME, segs=(5, 3), glow=1.8)
	for s in (-1, 1):
		p.box((0.45, 0.35, 0.3), (s * 0.3, -2.25, 0.15), WOOD, rot=(0, 0, s * 12), grad=(0.8, 1.0))
	for k in range(16):                                         # stakes round the foot
		a = k * math.tau / 16
		if abs(a - 3 * math.pi / 2) < 0.3:
			continue
		p.seg((math.cos(a) * 2.25, math.sin(a) * 2.25, -0.1), (math.cos(a) * 2.25, math.sin(a) * 2.25, 0.5), 0.05, 0.03, BARK, sides=4, grad=(0.5, 1.0))
	# cordwood stacked beside it, between posts
	wx = 3.6
	for s in (-1, 1):
		p.seg((wx, s * 1.1, -0.1), (wx, s * 1.1, 1.35), 0.07, 0.06, BARK, sides=5)
		p.seg((wx + 0.55, s * 1.1, -0.1), (wx + 0.55, s * 1.1, 1.35), 0.07, 0.06, BARK, sides=5)
	for row in range(5):
		for i in range(7):
			y = -0.9 + i * 0.3 + (0.15 if row % 2 else 0)
			if y > 0.95:
				continue
			z = 0.12 + row * 0.24
			p.seg((wx - 0.05, y, z), (wx + 0.6, y + rng.uniform(-0.03, 0.03), z), 0.12, 0.12, WOOD if (i + row) % 3 else HIDE, sides=6, grad=(0.3, 1.0))
	p.seg((wx - 0.2, -1.4, 0.0), (wx - 0.1, -0.9, 1.5), 0.03, 0.03, WOOD, sides=4)            # rake
	p.box((0.5, 0.06, 0.06), (wx - 0.1, -0.88, 1.5), IRON)
	p.seg((wx - 0.25, 1.4, 0.2), (wx - 0.05, 0.9, 1.4), 0.03, 0.03, WOOD, sides=4)            # shovel
	p.box((0.26, 0.05, 0.34), (wx - 0.26, 1.42, 0.15), IRON, rot=(20, 0, 0))
	obj = p.build(bevel=0.02)
	wisps = [((0, 0, 2.05), 2.8, 0.18)] + [((math.cos(a) * 2.0, math.sin(a) * 2.0, z), 1.5, 0.09) for a, z in vents]
	return join_into(obj, [_plumes("charcoal_kiln_smoke", 728, wisps, alpha=0.3)])


def _soot_mask(p, c, s, face_y, swatch=WOOD_GRAY, paint=CLOTH_WHITE):
	"""A carved mask facing -Y at c: a flat oval face with dark eye slits and
	mouth, soot-blackened, a streak of pale paint down the brow."""
	x, y, z = c
	p.blob((0.62 * s, 0.24 * s, 0.78 * s), (x, y, z), swatch, segs=(8, 6), grad=(0.5, 1.0))
	for k in (-1, 1):
		p.blob((0.16 * s, 0.08 * s, 0.07 * s), (x + k * 0.14 * s, face_y - 0.08 * s, z + 0.1 * s), CHAR, segs=(6, 3), rot=(0, k * 15, 0))
		p.seg((x + k * 0.26 * s, face_y, z + 0.28 * s), (x + k * 0.34 * s, face_y + 0.02, z - 0.2 * s), 0.02 * s, 0.015 * s, paint, sides=4)
	p.box((0.26 * s, 0.06 * s, 0.07 * s), (x, face_y - 0.08 * s, z - 0.2 * s), CHAR)
	p.seg((x, face_y - 0.04 * s, z + 0.36 * s), (x, face_y - 0.05 * s, z + 0.02 * s), 0.035 * s, 0.03 * s, paint, sides=4)


def sootmask_totem():
	"""The soot-mask cult's pole: a smoke-blackened trunk about 4.6 m tall
	carved into four masks stacked one over another (facing -Y, the lower ones
	with pale paint half worn off), tattered hide strips and hanging charms,
	and an iron bowl of smoldering embers on top trailing a thin smoke.
	Collide it as a trunk."""
	p = Prop("sootmask_totem", 729)
	p.seg((0, 0, -0.3), (0, 0, 3.9), 0.32, 0.28, CHAR, sides=8, grad=(0.1, 0.9))
	for k in range(4):
		z = 0.75 + k * 0.85
		s = 1.2 - k * 0.08
		_soot_mask(p, (0, -0.28, z), s, -0.28 - 0.12 * s, swatch=(WOOD_GRAY, BONE, WOOD_GRAY, BONE)[k], paint=(CLOTH_WHITE, CHAR, EMBER, CHAR)[k])
		for side in (-1, 1):                                   # carved ears / flanges
			p.box((0.26 * s, 0.14, 0.42 * s), (side * 0.42 * s, -0.2, z + 0.05), CHAR, rot=(0, side * -15, 0), grad=(0.2, 0.9))
	p.box((1.1, 0.14, 0.16), (0, 0, 3.55), CHAR, grad=(0.1, 0.8))
	for s in (-1, 1):                                           # hide strips and bone charms off the crossbar
		p.seg((s * 0.52, 0, 3.5), (s * 0.55, -0.04, 2.7), 0.03, 0.02, HIDE, sides=4, grad=(0.5, 1.0))
		p.blob((0.08, 0.06, 0.12), (s * 0.55, -0.04, 2.65), BONE, segs=(5, 3))
	bowl = _lathe(p, [(0.12, 3.9), (0.42, 4.05), (0.5, 4.3), (0.44, 4.32), (0.34, 4.12), (0.1, 4.0)], 10, IRON, grad=(0.0, 0.7))
	p.blob((0.7, 0.7, 0.14), (0, 0, 4.2), EMBER, segs=(8, 4), grad=(0.3, 0.8), glow=1.2)
	for k in range(5):
		p.blob((0.12, 0.1, 0.08), (p.rng.uniform(-0.2, 0.2), p.rng.uniform(-0.2, 0.2), 4.25), FLAME if k % 2 else EMBER, segs=(5, 3), glow=1.5)
	for k in range(3):                                          # soot streaks up the pole
		a = 3.6 + k * 0.4
		p.blob((0.12, 0.05, 0.9), (math.cos(a) * 0.25, math.sin(a) * 0.25, 3.3), SHADE, segs=(5, 4), grad=(0.85, 1.0))
	p.rock((0.8, 0.8, 0.3), (0, 0, 0.0), STONE_DARK, grad=(0.3, 1.0))
	obj = p.build(bevel=0.02)
	return join_into(obj, [_plumes("sootmask_totem_smoke", 730, [((0, 0, 4.3), 2.2, 0.12)], alpha=0.3)])


def sootmask_hut():
	"""A soot-mask cultist's hut: a round frame of bent poles about 4.4 m across
	and 3.2 m tall under overlapping slabs of dark bark and smoke-stained hides,
	poles jutting from a smoke hole at the top (a thin smoke rising), a low
	door at the front (-Y) with a hide flap drawn aside and a soot-mask hung
	over it, stones weighting the skirt. Collide it as a box."""
	p = Prop("sootmask_hut", 731)
	rng = p.rng
	R, H = 2.2, 2.7
	n = 12
	for k in range(n):                                          # the covering: courses of bark and hide, skipping the door
		a0 = k * math.tau / n
		for row in range(3):
			z0 = row * 0.85
			r0 = R * (1 - (z0 / (H + 0.2)) ** 1.6)
			r1 = R * (1 - ((z0 + 1.05) / (H + 0.2)) ** 1.6)
			if row == 0 and abs(a0 + math.tau / n / 2 - 3 * math.pi / 2) < 0.4:
				continue
			sw, gr = (HIDE, (0.6, 1.0)) if (k + row) % 3 == 0 else ((BARK, (0.5, 1.0)) if (k + row) % 3 == 1 else (CHAR, (0.1, 0.8)))
			a1 = a0 + math.tau / n * 1.15
			verts = []
			for a in (a0, a1):
				verts += [(math.cos(a) * (r0 + 0.08), math.sin(a) * (r0 + 0.08), z0), (math.cos(a) * (r1 + 0.08), math.sin(a) * (r1 + 0.08), z0 + 1.05)]
			inner = [(x * 0.94, y * 0.94, z) for x, y, z in verts]
			p.poly(verts + inner, [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (1, 3, 7, 5), (0, 4, 6, 2)], sw, grad=gr)
	for k in range(7):                                          # poles jutting from the smoke hole
		a = k * math.tau / 7 + 0.2
		p.seg((math.cos(a) * R * 0.95, math.sin(a) * R * 0.95, 0.0), (-math.cos(a) * 0.3, -math.sin(a) * 0.3, H + 0.9), 0.05, 0.04, BARK, sides=5, grad=(0.5, 1.0))
	p.seg((0, 0, H - 0.1), (0, 0, H + 0.12), 0.42, 0.38, CHAR, sides=10)
	p.blob((0.55, 0.55, 0.1), (0, 0, H + 0.1), EMBER, segs=(8, 3), glow=0.9)
	# the door, its flap drawn aside, a mask hung above
	dy = -R * 0.98
	p.box((0.9, 0.3, 1.3), (0, dy + 0.1, 0.65), CHAR, grad=(0.85, 1.0))
	for s in (-1, 1):
		p.seg((s * 0.5, dy - 0.05, 0.0), (s * 0.42, dy + 0.05, 1.45), 0.06, 0.05, BARK, sides=5)
	p.seg((-0.55, dy - 0.05, 1.42), (0.55, dy - 0.05, 1.42), 0.05, 0.05, BARK, sides=5)
	p.poly([(0.45, dy - 0.1, 1.4), (0.9, dy - 0.05, 1.3), (0.85, dy - 0.1, 0.05), (0.5, dy - 0.15, 0.05)], [(0, 1, 2, 3)], HIDE, grad=(0.5, 1.0))
	_soot_mask(p, (0, dy - 0.2, 1.8), 0.6, dy - 0.3)
	for k in range(14):                                         # stones weighting the skirt
		a = k * math.tau / 14 + 0.1
		if abs(a - 3 * math.pi / 2) < 0.35:
			continue
		s = rng.uniform(0.28, 0.4)
		p.rock((s, s * 0.8, s * 0.6), (math.cos(a) * (R + 0.15), math.sin(a) * (R + 0.15), 0.06), STONE_DARK, grad=(0.3, 1.0))
	p.blob((5.0, 5.0, 0.1), (0, 0, 0.0), SHADE, segs=(12, 4), grad=(0.6, 0.85))
	obj = p.build(bevel=0.02)
	return join_into(obj, [_plumes("sootmask_hut_smoke", 732, [((0.05, 0, H + 0.2), 2.4, 0.15)], alpha=0.3)])


def giant_fungus():
	"""A cluster of giant ember-caps: five pale-stalked mushrooms 0.9 to 3.1 m
	tall with broad orange caps, their undersides and speckles glowing softly,
	about 3.6 m across. Collide it as a box (or a trunk for the tallest)."""
	p = Prop("giant_fungus", 733)
	rng = p.rng
	caps = [((0.0, 0.1), 3.1, 1.25, 0.2), ((1.1, -0.4), 2.1, 0.9, -0.3), ((-0.9, -0.5), 1.6, 0.75, 0.25), ((0.6, 0.9), 1.3, 0.6, 0.1), ((-0.5, 0.95), 0.9, 0.45, -0.2)]
	for k, ((x, y), h, r, lean) in enumerate(caps):
		top = (x + lean * 0.4, y - abs(lean) * 0.2, h)
		_chain(p, [(x, y, -0.1), (x + lean * 0.1, y, h * 0.5), top], r * 0.28, r * 0.2, BONE, sides=8, grad=(0.1, 0.8))
		p.blob((r * 0.62, r * 0.62, r * 0.15), (x, y, 0.05), BONE, segs=(8, 3), grad=(0.3, 0.9))
		p.seg((top[0], top[1], h - 0.02), (top[0], top[1], h + 0.06), r * 0.92, r * 0.92, PETAL_YELLOW, sides=12, grad=(0.1, 0.5), glow=1.1)   # glowing gills
		cap = _lathe(p, [(0.02, h + 0.05), (r * 1.0, h + 0.02), (r * 1.05, h + 0.12), (r * 0.85, h + 0.35), (r * 0.45, h + 0.52), (0.02, h + 0.56)], 12, CORAL_ORANGE, grad=(0.0, 0.8))
		cap.data.transform(Matrix.Translation((top[0], top[1], 0)))
		for j in range(int(4 + r * 5)):                         # glowing speckles
			a = rng.uniform(0, math.tau)
			d = rng.uniform(0.2, 0.8) * r
			zz = h + 0.56 - (d / r) ** 2 * 0.5
			p.blob((0.08 + r * 0.06, 0.08 + r * 0.06, 0.04), (top[0] + math.cos(a) * d, top[1] + math.sin(a) * d, zz), PETAL_YELLOW, segs=(5, 3), glow=1.4)
	for k in range(6):                                          # little ones at the foot
		a = rng.uniform(0, math.tau)
		d = rng.uniform(1.3, 1.8)
		x, y = math.cos(a) * d, math.sin(a) * d
		h = rng.uniform(0.15, 0.3)
		p.seg((x, y, 0), (x, y, h), 0.04, 0.035, BONE, sides=5)
		p.blob((0.2, 0.2, 0.1), (x, y, h), CORAL_ORANGE, segs=(6, 4), grad=(0.0, 0.6), glow=0.6)
	return p.build(bevel=0.02)


def moth_cocoon():
	"""A dead snag about 5.2 m tall, grey and leaning, its few bare limbs hung
	with glowing cocoons of the ember moths: a dozen pale silk pods on threads,
	some lit amber from within, wisps of silk strung between the limbs.
	Collide it as a trunk."""
	p = Prop("moth_cocoon", 735)
	rng = p.rng
	pts = [(0, 0, -0.3), (0.1, 0.05, 1.8), (0.35, 0.0, 3.4), (0.45, 0.1, 4.6), (0.4, 0.15, 5.2)]
	_chain(p, pts, 0.3, 0.08, BARK, sides=7, grad=(0.2, 0.9))
	for k in range(3):
		a = k * math.tau / 3 + 0.3
		p.seg((0, 0, 0.4), (math.cos(a) * 0.8, math.sin(a) * 0.8, -0.2), 0.16, 0.05, BARK, sides=5, grad=(0.2, 0.9))
	limbs = []
	for k, (z, a, L) in enumerate(((2.6, 0.2, 2.2), (3.3, 2.5, 1.9), (3.9, 4.2, 1.6), (4.5, 1.2, 1.3))):
		t = z / 5.2
		base = Vector((0.35 * t * 1.2, 0.05, z))
		mid = base + Vector((math.cos(a) * L * 0.55, math.sin(a) * L * 0.55, L * 0.25))
		end = mid + Vector((math.cos(a + 0.3) * L * 0.45, math.sin(a + 0.3) * L * 0.45, -L * 0.05))
		_chain(p, [tuple(base), tuple(mid), tuple(end)], 0.1, 0.03, BARK, sides=5, grad=(0.2, 0.9))
		limbs.append((base, mid, end))
	for k in range(12):
		base, mid, end = limbs[k % 4]
		f = rng.uniform(0.3, 1.0)
		top = mid.lerp(end, f) if f > 0.5 else base.lerp(mid, f * 2)
		L = rng.uniform(0.3, 0.9)
		pod = top - Vector((0, 0, L))
		p.seg(tuple(top), tuple(pod + Vector((0, 0, 0.3))), 0.008, 0.008, CLOTH_WHITE, sides=3)
		lit = k % 3 != 1
		s = rng.uniform(0.7, 1.1)
		p.blob((0.22 * s, 0.22 * s, 0.6 * s), tuple(pod), PETAL_YELLOW if lit else CLOTH_WHITE, segs=(7, 6), grad=(0.1, 0.6) if lit else (0.2, 0.8),
			   glow=1.4 if lit else 0.0, rot=(rng.uniform(-8, 8), rng.uniform(-8, 8), 0))
		for j in range(2):                                     # silk wrapping bands
			p.seg(tuple(pod + Vector((0, 0, -0.1 + j * 0.2))), tuple(pod + Vector((0, 0, -0.06 + j * 0.2))), 0.115 * s, 0.115 * s, CLOTH_WHITE, sides=7)
	for (b0, m0, e0), (b1, m1, e1) in zip(limbs, limbs[1:]):  # silk strung between limbs
		a, b = m0.lerp(e0, 0.5), m1.lerp(e1, 0.3)
		mid = (a + b) / 2 - Vector((0, 0, 0.3))
		_chain(p, [tuple(a), tuple(mid), tuple(b)], 0.015, 0.015, CLOTH_WHITE, sides=3)
	p.rock((1.0, 0.9, 0.35), (0, 0, 0.0), STONE_DARK, grad=(0.3, 1.0))
	return p.build()


def ember_treant_stump():
	"""The burned-out stump of a fallen treant: a hollow trunk 3.2 m across
	broken off jagged at 1.4-3 m, great roots gripping the ground, a knotted
	brow and two dark eye-hollows still in the bark at the front (-Y), and
	inside, through a split in the front, its heart-hollow glowing like a
	forge; ember cracks up the bark, a thin smoke from the hollow. About
	4.4 m across. Collide it as a box."""
	p = Prop("ember_treant_stump", 737)
	rng = p.rng
	R = 1.6
	n = 22
	split = 3 * math.pi / 2 + 0.75                              # the split, front right, where the heart shows
	for k in range(n):                                          # the wall: a thick hollow ring, its rim broken jagged
		a0, a1 = k * math.tau / n, (k + 1) * math.tau / n
		if abs((a0 + a1) / 2 - split) < 0.3:
			continue
		hs = []
		for a in (a0, a1):
			near = min(abs(a - split), 1.2) / 1.2
			hs.append(1.3 + 1.7 * near * (0.55 + 0.45 * abs(math.sin(a * 5.3 + 0.7))))
		verts = []
		for a, h in zip((a0, a1), hs):
			for rr in (R + 0.35, R - 0.3):
				verts += [(math.cos(a) * rr, math.sin(a) * rr, -0.2), (math.cos(a) * rr, math.sin(a) * rr, h - (0.25 if rr < R else 0.0))]
		# verts: a0 outer lo/hi (0,1), a0 inner lo/hi (2,3), a1 outer lo/hi (4,5), a1 inner lo/hi (6,7)
		p.poly(verts, [(0, 4, 5, 1), (2, 3, 7, 6), (1, 5, 7, 3), (0, 2, 6, 4), (0, 1, 3, 2), (4, 6, 7, 5)], BARK if k % 4 else CHAR, grad=(0.5, 1.0))
		if k % 2 == 0:                                         # bark ridges and a splinter off the rim
			am = (a0 + a1) / 2
			x, y = math.cos(am) * (R + 0.38), math.sin(am) * (R + 0.38)
			hm = min(hs)
			p.seg((x, y, -0.1), (x * 0.99, y * 0.99, hm * 0.85), 0.1, 0.07, BARK, sides=4, grad=(0.6, 1.0))
			p.seg((x * 0.93, y * 0.93, hm - 0.1), (x * 0.9, y * 0.9, hm + rng.uniform(0.25, 0.6)), 0.14, 0.03, CHAR, sides=4)
	for k in range(6):                                          # roots
		a = k * math.tau / 6 + 0.25
		d = Vector((math.cos(a), math.sin(a), 0))
		_chain(p, [tuple(d * R * 0.9 + Vector((0, 0, 0.8))), tuple(d * (R + 0.9) + Vector((0, 0, 0.3))), tuple(d * (R + 1.6) + Vector((0, 0, -0.2)))], 0.4, 0.12, BARK, sides=6, grad=(0.4, 1.0))
	# the face at the front: a knotted brow, two eye-hollows
	fy = -(R + 0.3)
	for s in (-1, 1):
		p.blob((0.5, 0.32, 0.3), (s * 0.45, fy - 0.1, 1.95), BARK, segs=(7, 5), grad=(0.5, 1.0))
		p.blob((0.32, 0.14, 0.24), (s * 0.45, fy - 0.14, 1.62), CHAR, segs=(6, 4))
		p.blob((0.11, 0.06, 0.09), (s * 0.45, fy - 0.2, 1.62), EMBER, segs=(5, 3), glow=1.6)
	p.blob((0.3, 0.3, 0.5), (0, fy - 0.15, 1.3), BARK, segs=(6, 5), grad=(0.5, 1.0))           # a knot of a nose
	p.blob((0.6, 0.12, 0.1), (0, fy - 0.05, 0.85), CHAR, segs=(6, 3))                          # a grim mouth-crack
	# the heart-hollow: a glowing heart of embers within
	p.seg((0, 0, -0.1), (0, 0, 0.5), R * 0.95, R * 0.95, CHAR, sides=12, grad=(0.8, 1.0))
	_coals(p, (0, 0, 0.5), 2.2, 2.2, glow=1.5, flames=3, flame_h=0.6)
	hx, hy = math.cos(split) * 0.45, math.sin(split) * 0.45
	p.blob((0.8, 0.6, 0.9), (hx, hy, 1.05), EMBER, segs=(8, 6), glow=1.8)
	p.blob((0.5, 0.4, 0.6), (hx * 1.15, hy * 1.15, 1.1), FLAME, segs=(7, 5), glow=2.2)
	for k, a in enumerate((0.3, 1.5, 2.6, 3.7, 5.6)):         # ember cracks up the bark
		x, y = math.cos(a) * (R + 0.4), math.sin(a) * (R + 0.4)
		_crack(p, [(x, y, 0.3), (x * 0.97, y * 0.97, 0.8), (x * 0.95, y * 0.95, 1.3)], r=0.05, glow=1.4)
	p.blob((4.4, 4.4, 0.1), (0, 0, 0.0), SHADE, segs=(12, 4), grad=(0.6, 0.85))
	obj = p.build(bevel=0.02)
	return join_into(obj, [_plumes("ember_treant_stump_smoke", 738, [((0, -0.1, 1.6), 3.0, 0.2)], alpha=0.28)])



# ===== The Standing Sky finished: Stonesail, Hollow Air, Vayuketh's Step

MOOR_STONE = GALE_STONE     # lichened blue-gray moor stone
HEATHER = PETAL_PURPLE      # heather bloom: lilac into deep purple
TURF = LEAF                 # turf roofs (drawn from the swatch's darker half)
BREW = SLIME                # a bog hag's green brew
CLOUD_STONE = CLOTH_WHITE   # the cloud giants' white stone, shading to pale blue-gray
SILVER = STONE_LIGHT        # silver trim: the palest gray
BRONZE = COPPER             # Vayuketh's bronze
EARTH = WOOD_GRAY           # raw earth under a floating isle's turf

# rune glyphs: strokes in a 0.5 x 1 cell, drawn by _rune
_GLYPHS = (
	(((0, 0), (0, 1)), ((0, 1), (0.5, 0.72)), ((0, 0.62), (0.5, 0.34))),
	(((0, 0), (0, 1)), ((0, 1), (0.45, 0.72)), ((0.45, 0.72), (0, 0.45)), ((0, 0.45), (0.45, 0))),
	(((0.25, 0), (0.25, 1)), ((0, 0.75), (0.25, 0.5)), ((0.5, 0.75), (0.25, 0.5))),
	(((0, 0), (0, 1)), ((0.5, 0), (0.5, 1)), ((0, 0.75), (0.5, 0.25))),
	(((0, 0.5), (0.25, 1)), ((0.25, 1), (0.5, 0.5)), ((0.5, 0.5), (0.25, 0)), ((0.25, 0), (0, 0.5))),
	(((0.25, 0), (0.25, 1)), ((0, 1), (0.25, 0.7)), ((0.5, 1), (0.25, 0.7)), ((0, 0.25), (0.5, 0.25))),
	(((0, 1), (0.5, 0)), ((0, 0), (0.5, 1)), ((0.25, 0.5), (0.25, 1))),
)


def _rune(p, c, s, k, glow=0.9, swatch=SKY):
	"""A carved rune (glyph k) s meters tall centered at c, on a face across X-Z:
	thin glowing strokes."""
	x, y, z = c
	r = max(0.018, s * 0.055)
	for a, b in _GLYPHS[k % len(_GLYPHS)]:
		p.seg((x + (a[0] - 0.25) * s, y, z + (a[1] - 0.5) * s), (x + (b[0] - 0.25) * s, y, z + (b[1] - 0.5) * s), r, r, swatch, sides=4, grad=(0.0, 0.3), glow=glow)


def _hewn(p, rings, swatch, tip=None, jit=0.04, grad=(0.05, 0.9)):
	"""A rough hewn stone: chamfered-rectangle rings [(z, w, d, ox, oy)] from the
	foot up, closed at the foot and drawn to a point at `tip` (else flat). The
	front face is the flat at y = oy - d/2."""
	shape = ((0.5, -0.3), (0.5, 0.3), (0.3, 0.5), (-0.3, 0.5), (-0.5, 0.3), (-0.5, -0.3), (-0.3, -0.5), (0.3, -0.5))
	n = len(shape)
	verts, faces = [], []
	for z, w, d, ox, oy in rings:
		for sx, sy in shape:
			verts.append((ox + sx * w + p.rng.uniform(-jit, jit), oy + sy * d + p.rng.uniform(-jit, jit) * 0.5, z + p.rng.uniform(-jit, jit)))
	m = len(rings)
	for r in range(m - 1):
		for i in range(n):
			i2 = (i + 1) % n
			faces.append((r * n + i, r * n + i2, (r + 1) * n + i2, (r + 1) * n + i))
	faces.append(tuple(range(n)))
	if tip:
		verts.append(tip)
		t = len(verts) - 1
		for i in range(n):
			faces.append(((m - 1) * n + i, (m - 1) * n + (i + 1) % n, t))
	else:
		faces.append(tuple((m - 1) * n + i for i in range(n)))
	return p.poly(verts, faces, swatch, grad)


def _ring_at(rings, z):
	"""(w, d, ox, oy) of _hewn rings interpolated at height z."""
	for (z0, w0, d0, x0, y0), (z1, w1, d1, x1, y1) in zip(rings, rings[1:]):
		if z <= z1 or (z1 == rings[-1][0]):
			t = min(max((z - z0) / (z1 - z0), 0.0), 1.0)
			return w0 + (w1 - w0) * t, d0 + (d1 - d0) * t, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
	return rings[-1][1:]


def _heather_tuft(p, c, s=1.0):
	"""A small clump of heather: a dark green cushion under lilac bloom."""
	x, y, z = c
	p.blob((0.55 * s, 0.5 * s, 0.26 * s), (x, y, z + 0.06 * s), PINE, segs=(6, 3), grad=(0.35, 1.0))
	for k in range(3):
		a = k * math.tau / 3 + p.rng.uniform(-0.3, 0.3)
		p.blob((0.26 * s, 0.24 * s, 0.2 * s), (x + math.cos(a) * 0.13 * s, y + math.sin(a) * 0.13 * s, z + 0.2 * s), HEATHER, segs=(5, 3), grad=(0.0, 0.5))


def _torus(p, c, u, v, R, r, swatch, stretch=1.0, seg=8, ring=4, grad=(0.1, 0.7)):
	"""A ring round c in the plane of the unit vectors u, v (stretched along u):
	a chain link."""
	c, u, v = Vector(c), Vector(u).normalized(), Vector(v).normalized()
	n = u.cross(v).normalized()
	verts, faces = [], []
	for i in range(seg):
		a = i * math.tau / seg
		out = u * math.cos(a) * stretch + v * math.sin(a)
		radial = (u * math.cos(a) + v * math.sin(a)).normalized()
		for j in range(ring):
			b = j * math.tau / ring
			verts.append(tuple(c + out * R + radial * math.cos(b) * r + n * math.sin(b) * r))
	for i in range(seg):
		for j in range(ring):
			i2, j2 = (i + 1) % seg, (j + 1) % ring
			faces.append((i * ring + j, i2 * ring + j, i2 * ring + j2, i * ring + j2))
	return p.poly(verts, faces, swatch, grad)


def _iron_chain(p, a, b, link=0.42, r=0.045):
	"""A heavy iron chain from a to b, its links turning a quarter each."""
	a, b = Vector(a), Vector(b)
	d = (b - a)
	n = max(2, int(d.length / (link * 0.78)))
	u = d.normalized()
	s1 = u.cross(Vector((0, 0, 1)))
	if s1.length < 0.1:
		s1 = u.cross(Vector((1, 0, 0)))
	s1.normalize()
	s2 = u.cross(s1).normalized()
	for k in range(n):
		c = a.lerp(b, (k + 0.5) / n)
		_torus(p, c, u, s1 if k % 2 else s2, link * 0.3, r, IRON, stretch=1.6, seg=8, ring=4)


def _stick_ring(p, c, R, layers, rng, swatches=(WOOD_GRAY, WOOD, BONE), r=0.06, length=(0.8, 1.5)):
	"""A nest's woven rim: layers of sticks laid round a ring."""
	x, y, z = c
	for layer in range(layers):
		n = int(R * 9) + 4
		for k in range(n):
			a = k * math.tau / n + rng.uniform(-0.2, 0.2) + layer * 0.3
			cc = Vector((x + math.cos(a) * R, y + math.sin(a) * R, z + layer * r * 3.2))
			tv = Vector((-math.sin(a), math.cos(a), 0)).lerp(Vector((math.cos(a), math.sin(a), 0)), rng.uniform(-0.5, 0.5))
			tv.z = rng.uniform(-0.25, 0.25)
			L = rng.uniform(*length)
			p.seg(tuple(cc - tv * L / 2), tuple(cc + tv * L / 2), r, r * 0.6, swatches[(k + layer) % len(swatches)], sides=5, grad=(0.1, 0.9))


# ---- Stonesail

def rune_menhir():
	"""A rune menhir of Stonesail: a rough blue-gray standing stone about 5.2 m
	tall (1.55 x 0.95 m at the foot, leaning a little down-wind, +X), carved on
	its face (-Y) with a column of pale blue glowing runes between two bands and
	on its back with three more; lichen on its flanks, heather and stones at its
	foot. Set in rings of 12. Collide it as a box."""
	p = Prop("rune_menhir", 740)
	d = Prop("rune_menhir_runes", 741)
	rings = [(-0.5, 1.55, 0.95, 0.0, 0.0), (1.4, 1.5, 0.92, 0.05, 0.0), (3.0, 1.3, 0.8, 0.12, 0.02), (4.45, 0.95, 0.6, 0.2, 0.04)]
	_hewn(p, rings, MOOR_STONE, tip=(0.34, 0.06, 5.25), jit=0.05)
	for k, (z, s) in enumerate(((1.0, 0.52), (1.72, 0.52), (2.44, 0.5), (3.14, 0.46), (3.8, 0.42))):
		w, dd, ox, oy = _ring_at(rings, z)
		_rune(d, (ox, oy - dd / 2 - 0.05, z), s, k * 2 + 1)
	for z in (0.52, 4.28):                                                # the bands above and below
		w, dd, ox, oy = _ring_at(rings, z)
		d.seg((ox - w * 0.28, oy - dd / 2 - 0.05, z), (ox + w * 0.28, oy - dd / 2 - 0.05, z), 0.03, 0.03, SKY, sides=4, grad=(0.0, 0.3), glow=0.9)
	for k, z in enumerate((1.5, 2.4, 3.3)):
		w, dd, ox, oy = _ring_at(rings, z)
		_rune(d, (ox, oy + dd / 2 + 0.05, z), 0.44, k * 3, glow=0.6)
	for side in (-1, 1):                                                  # lichen on the flanks
		for z in (0.8, 2.1, 3.4):
			w, dd, ox, oy = _ring_at(rings, z + side * 0.3)
			d.blob((0.1, 0.55, 0.5), (ox + side * w / 2, oy + p.rng.uniform(-0.1, 0.1), z + side * 0.3), LEAF, segs=(6, 4), grad=(0.0, 0.35))
	for k in range(4):
		a = k * math.tau / 4 + 0.7
		p.rock((0.5, 0.45, 0.3), (math.cos(a) * 1.1, math.sin(a) * 0.8, 0.02), STONE_DARK)
	for x, y in ((0.95, -0.6), (-0.9, 0.5), (0.4, 0.75)):
		_heather_tuft(d, (x, y, 0.0), 1.1)
	return join_into(p.build(bevel=0.06), [d.build()])


def singing_altar():
	"""The stone-singers' altar: a low slab table (2.4 x 1.3 m, 1 m high) on two
	blocks, set on flat paving stones, with three upright hum stones behind it
	(each pierced by a hole the wind sings through, runes glowing) and offerings
	on it: a bronze bowl, candles, heather, bread and coins. About 3.4 x 3 m,
	1.8 m tall. Faces -Y. Collide it as a box."""
	p = Prop("singing_altar", 742)
	d = Prop("singing_altar_detail", 743)
	for k in range(9):
		a = k * math.tau / 9 + p.rng.uniform(-0.2, 0.2)
		r = p.rng.uniform(0.9, 1.5)
		p.box((p.rng.uniform(0.7, 1.0), p.rng.uniform(0.6, 0.9), 0.14), (math.cos(a) * r, math.sin(a) * r * 0.85, 0.0), STONE_DARK, rot=(0, 0, p.rng.uniform(0, 90)), grad=(0.3, 0.9), jitter=0.03)
	for x in (-0.75, 0.75):
		_block(p, (0.5, 0.95, 0.85), (x, 0, 0.43), MOOR_STONE, rough=0.04)
	_block(p, (2.4, 1.3, 0.26), (0, 0, 0.98), STONE_LIGHT, rough=0.03, grad=(0.0, 0.8))
	for k in range(3):                                                     # a rune on the front of the slab
		_rune(d, (-0.6 + k * 0.6, -0.68, 0.98), 0.2, k + 2, glow=0.8)
	for k, (x, h) in enumerate(((-0.95, 1.5), (0.0, 1.85), (0.95, 1.4))):   # hum stones
		y = 0.95
		rings = [(-0.2, 0.46, 0.3, 0, y), (h * 0.6, 0.42, 0.28, 0.02, y), (h, 0.3, 0.22, 0.04, y)]
		_hewn(p, [(z, w, dd, ox + x, oy) for z, w, dd, ox, oy in rings], MOOR_STONE, tip=(x + 0.05, y, h + 0.18), jit=0.02)
		d.seg((x, y - 0.2, h * 0.62), (x, y + 0.2, h * 0.62), 0.07, 0.07, SHADE, sides=8, grad=(0.95, 1.0))   # the singing hole
		_rune(d, (x, y - 0.17, h * 0.33), 0.26, k + 4, glow=1.0)
	d.blob((0.26, 0.26, 0.14), (-0.55, -0.1, 1.15), BRONZE, segs=(10, 4), grad=(0.0, 0.7))            # the bowl
	d.seg((-0.55, -0.1, 1.2), (-0.55, -0.1, 1.23), 0.1, 0.1, WATER, sides=10, grad=(0.1, 0.4))
	for x, y in ((0.35, 0.3), (0.62, 0.35), (0.9, 0.25)):
		_candle(d, (x, y, 1.11), h=0.15 + 0.06 * (x > 0.5))
	_heather_tuft(d, (0.1, -0.2, 1.1), 0.6)
	d.blob((0.28, 0.2, 0.13), (0.55, -0.25, 1.16), HIDE, segs=(6, 4), grad=(0.0, 0.8))                # bread
	for k in range(4):
		d.seg((-0.1 + k * 0.08, 0.2, 1.11), (-0.1 + k * 0.08, 0.2, 1.13), 0.04, 0.04, GOLD, sides=8)
	return join_into(p.build(bevel=0.04), [d.build()])


def singer_hut():
	"""A stone-singer's hut: a round wall of stacked flat stones (5 m across,
	1.8 m high) with a doorway on the front (-Y) under a lintel, a low conical
	turf roof to about 3.6 m with heather growing on it and a smoke hole, two
	rune stones flanking the door. Collide it as a box."""
	p = Prop("singer_hut", 744)
	d = Prop("singer_hut_detail", 745)
	R, H = 2.4, 1.8
	door = math.radians(-90)
	for c in range(6):                                                     # the courses
		z = 0.15 + c * 0.3
		n = 16
		for k in range(n):
			a = k * math.tau / n + (c % 2) * math.pi / n
			da = (a - door + math.pi) % math.tau - math.pi
			if abs(da) < 0.26:
				continue
			p.box((0.95, 0.6, 0.3), (math.cos(a) * R, math.sin(a) * R, z), MOOR_STONE if (k + c) % 3 else STONE_WARM,
				  rot=(p.rng.uniform(-3, 3), p.rng.uniform(-3, 3), math.degrees(a) + 90), grad=(0.1, 0.9), jitter=0.04)
	d.seg((0, 0, 0.0), (0, 0, H), R - 0.3, R - 0.3, SHADE, sides=14, grad=(0.95, 1.0))   # the dark inside
	for s in (-1, 1):                                                     # door posts and lintel
		_block(p, (0.4, 0.55, 1.75), (s * 0.68, -R, 0.87), STONE_LIGHT, rough=0.03)
	_block(p, (1.9, 0.65, 0.32), (0, -R, 1.9), STONE_LIGHT, rough=0.03)
	p.seg((0, 0, H + 0.02), (0, 0, H + 1.7), R + 0.55, 0.45, TURF, sides=14, grad=(0.35, 1.0), jitter=0.05)   # turf roof
	p.seg((0, 0, H - 0.12), (0, 0, H + 0.12), R + 0.6, R + 0.5, EARTH, sides=14, grad=(0.3, 0.9))
	p.seg((0, 0, H + 1.6), (0, 0, H + 1.85), 0.5, 0.35, STONE_DARK, sides=8, grad=(0.3, 0.9))
	d.seg((0, 0, H + 1.8), (0, 0, H + 1.87), 0.28, 0.28, SHADE, sides=8, grad=(0.95, 1.0))
	for k in range(9):                                                     # heather in the turf
		a = k * math.tau / 9 + p.rng.uniform(-0.3, 0.3)
		t = p.rng.uniform(0.2, 0.75)
		rr = (R + 0.55) * (1 - t) + 0.45 * t
		_heather_tuft(d, (math.cos(a) * rr, math.sin(a) * rr, H + 1.7 * t - 0.08), 0.8)
	for k in range(5):                                                     # stones weighting the turf
		a = k * math.tau / 5 + 0.3
		p.rock((0.4, 0.35, 0.25), (math.cos(a) * (R + 0.3), math.sin(a) * (R + 0.3), H + 0.3), STONE_DARK)
	for s in (-1, 1):                                                     # rune stones beside the door
		x = s * 1.5
		rings = [(-0.2, 0.5, 0.35, x, -R - 0.9), (1.2, 0.42, 0.3, x, -R - 0.9), (1.7, 0.3, 0.24, x, -R - 0.9)]
		_hewn(p, rings, MOOR_STONE, tip=(x, -R - 0.9, 1.9), jit=0.02)
		_rune(d, (x, -R - 1.09, 0.95), 0.4, 2 + s, glow=0.9)
	p.seg((0, -R - 0.55, -0.1), (0, -R - 0.55, 0.08), 0.6, 0.55, STONE_DARK, sides=8, grad=(0.3, 0.9))   # doorstep
	return join_into(p.build(bevel=0.05), [d.build()])


def wyvern_nest():
	"""A moor wyvern's nest: a great rough ring of heather, sticks and bones
	(4.6 m across, rim about 1.9 m up) on a low flat rock, with three mottled
	eggs, a scatter of bones and a ribcage round it. Collide it as a box."""
	p = Prop("wyvern_nest", 746)
	rng = p.rng
	p.rock((5.0, 4.4, 1.4), (0, 0, 0.35), MOOR_STONE, grad=(0.1, 0.9))
	p.rock((2.2, 1.8, 1.0), (2.1, 1.2, 0.2), STONE_DARK)
	p.blob((3.8, 3.6, 0.6), (0, 0, 1.15), EARTH, segs=(12, 5), grad=(0.2, 0.9), jitter=0.05)
	_stick_ring(p, (0, 0, 1.25), 1.85, 3, rng, swatches=(WOOD_GRAY, WOOD, BONE, WOOD_GRAY))
	for k in range(14):                                                    # heather woven in the rim
		a = k * math.tau / 14 + rng.uniform(-0.2, 0.2)
		_heather_tuft(p, (math.cos(a) * 2.0, math.sin(a) * 2.0, 1.3 + rng.uniform(0, 0.3)), rng.uniform(0.8, 1.2))
	p.blob((2.8, 2.6, 0.3), (0, 0, 1.45), HIDE, segs=(10, 5), grad=(0.3, 0.8))     # the lining
	for k, (x, y) in enumerate(((-0.4, 0.0), (0.35, 0.3), (0.2, -0.45))):
		p.blob((0.5, 0.5, 0.66), (x, y, 1.78), (BONE, SHELL_PEACH, BONE)[k], segs=(8, 6), rot=(rng.uniform(-18, 18), rng.uniform(-18, 18), 0), grad=(0.0, 0.7))
		for j in range(3):                                                 # mottling
			a = rng.uniform(0, math.tau)
			p.blob((0.12, 0.1, 0.06), (x + math.cos(a) * 0.24, y + math.sin(a) * 0.24, 1.8 + rng.uniform(-0.1, 0.15)), WOOD_GRAY, segs=(4, 3))
	for k in range(8):                                                     # bones about it
		a = rng.uniform(0, math.tau)
		r = rng.uniform(2.2, 3.1)
		c = Vector((math.cos(a) * r, math.sin(a) * r, 0.08 if r > 2.6 else 1.0))
		t = rng.uniform(0, math.pi)
		_bone(p, tuple(c - Vector((math.cos(t), math.sin(t), 0)) * 0.35), tuple(c + Vector((math.cos(t), math.sin(t), 0)) * 0.35), r=0.04)
	for k in range(5):                                                     # a sheep's ribcage off to one side
		y = -2.9 + k * 0.22
		pts = [(-1.8 + 0.35 * math.cos(t * math.pi), y, 0.05 + 0.45 * math.sin(t * math.pi)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
		_chain(p, pts, 0.03, 0.02, BONE, sides=4)
	_skull(p, (-1.8, -3.3, 0.02), 1.3, yaw=0.5)
	return p.build()


def crag_rock():
	"""A tall jagged crag: a closed pile of blue-gray rock about 6 m across and
	8.2 m tall, split into two leaning fangs at the top, lichen and heather on
	its ledges. Collide it as a mesh (every piece is closed)."""
	p = Prop("crag_rock", 747)
	rng = p.rng
	p.rock((6.2, 5.2, 3.2), (0, 0, 0.9), MOOR_STONE, rot=(0, 0, 20), grad=(0.05, 0.9), jitter=0.06)
	p.rock((4.2, 3.8, 3.6), (0.3, 0.2, 3.2), STONE_DARK, rot=(0, 5, 70), jitter=0.07)
	p.rock((2.4, 2.2, 2.0), (-2.1, -0.9, 1.4), MOOR_STONE, rot=(0, 0, 10))
	p.seg((0.2, 0.3, 4.0), (-0.2, 0.6, 8.2), 1.5, 0.12, MOOR_STONE, sides=5, grad=(0.05, 0.9), jitter=0.12, twist=20)
	p.seg((1.2, -0.3, 3.8), (1.9, -0.6, 6.6), 1.1, 0.1, STONE_DARK, sides=5, grad=(0.05, 0.9), jitter=0.1, twist=40)
	p.seg((-1.0, -0.4, 3.4), (-1.7, -0.9, 5.3), 0.9, 0.08, MOOR_STONE, sides=5, jitter=0.08, twist=10)
	for k in range(7):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(3.0, 4.0)
		s = rng.uniform(0.5, 1.1)
		p.rock((s, s * 0.9, s * 0.7), (math.cos(a) * r, math.sin(a) * r, 0.1), STONE_DARK)
	for x, y, z in ((1.8, -1.5, 2.3), (-1.3, 1.5, 2.9), (2.3, 1.2, 1.7)):
		p.blob((1.0, 0.8, 0.25), (x, y, z), MOSS, segs=(6, 4), grad=(0.1, 0.8))
		_heather_tuft(p, (x, y, z + 0.08), 0.9)
	return p.build()


def hag_hut():
	"""A bog hag's hut: a crooked patched shack (3.6 x 3.2 m) on short stilts
	1.2 m over the mire, walls of mismatched planks, hide and moss, a sagging
	reed roof to about 5 m with a crooked stone chimney smoking on the right,
	a round window glowing green, steps up to the door (-Y), herbs, bones and a
	skull hung under the eaves. Leans to +X. Collide it as a box."""
	p = Prop("hag_hut", 748)
	d = Prop("hag_hut_detail", 749)
	rng = p.rng
	F = 1.25
	hx, hy = 1.8, 1.6
	for x in (-hx, 0.0, hx):                                               # crooked stilts
		for y in (-hy, hy):
			p.seg((x + rng.uniform(-0.15, 0.15), y + rng.uniform(-0.15, 0.15), -0.4), (x, y, F), 0.13, 0.1, WOOD_GRAY, sides=5, grad=(0.3, 1.0))
	p.box((2 * hx + 0.5, 2 * hy + 0.5, 0.2), (0, 0, F), WOOD_GRAY, rot=(1.5, -2, 0), grad=(0.2, 0.9))
	W = 2.3
	cols = (WOOD_GRAY, HIDE, WOOD, TURF, WOOD_GRAY, WOOD, HIDE)
	for side in (-1, 1):                                                   # long walls, panel by panel
		for k in range(5):
			x = -hx + 0.36 + k * 0.72
			if side < 0 and k == 2:
				continue                                                   # the door
			p.box((0.74, 0.14, W + rng.uniform(-0.1, 0.15)), (x, side * hy, F + W / 2), cols[(k + (side > 0) * 3) % 7],
				  rot=(0, rng.uniform(-4, 4), 0), grad=(0.1, 0.9))
	for side in (-1, 1):                                                   # end walls
		for k in range(4):
			y = -hy + 0.4 + k * 0.8
			p.box((0.14, 0.82, W + 0.5 - abs(y) * 0.2), (side * hx, y, F + W / 2 + 0.15), cols[(k * 2 + side) % 7], rot=(rng.uniform(-3, 3), 0, 0), grad=(0.1, 0.9))
	for x in (-hx, hx):
		for y in (-hy, hy):
			p.seg((x, y, F), (x, y, F + W + 0.2), 0.1, 0.09, WOOD, sides=5)
	d.box((0.72, 0.1, 1.75), (0, -hy + 0.02, F + 0.88), SHADE, grad=(0.95, 1.0))                  # doorway
	p.box((0.66, 0.08, 1.7), (-0.52, -hy - 0.28, F + 0.86), WOOD_GRAY, rot=(0, 0, 55), grad=(0.2, 1.0))   # the door, ajar
	d.seg((-hx - 0.09, 0.3, F + 1.45), (-hx - 0.02, 0.3, F + 1.45), 0.34, 0.34, BREW, sides=10, grad=(0.1, 0.5), glow=1.4)   # round window
	d.seg((-hx - 0.1, 0.3, F + 1.45), (-hx - 0.1, 0.3, F + 1.45 + 0.01), 0.36, 0.36, WOOD, sides=10)
	d.seg((-hx - 0.12, 0.3, F + 1.1), (-hx - 0.12, 0.3, F + 1.8), 0.03, 0.03, WOOD, sides=4)
	d.seg((-hx - 0.12, -0.05, F + 1.45), (-hx - 0.12, 0.65, F + 1.45), 0.03, 0.03, WOOD, sides=4)
	for k in range(4):                                                     # steps up to the door
		p.box((1.0, 0.36, 0.1), (0, -hy - 0.55 - k * 0.36, F - 0.3 - k * 0.3), WOOD, rot=(0, rng.uniform(-4, 4), 0))
	for s in (-1, 1):
		p.seg((s * 0.5, -hy - 0.3, F), (s * 0.5, -hy - 1.75, -0.2), 0.05, 0.05, WOOD_GRAY, sides=4)
	# the sagging reed roof, ridge along X
	top = F + W
	n = 7
	for side in (-1, 1):
		ridge = [(-hx - 0.7 + (2 * hx + 1.4) * i / (n - 1), 0.0, top + 1.55 - 0.4 * math.sin(math.pi * i / (n - 1))) for i in range(n)]
		eave = [(x, side * (hy + 0.75), top - 0.35 - 0.25 * math.sin(math.pi * i / (n - 1)) + rng.uniform(-0.08, 0.08)) for i, (x, _, _) in enumerate(ridge)]
		_slab(p, ridge, eave, 0.28, BAMBOO, grad=(0.1, 0.9))
		for i in range(10):                                                # ragged reed ends
			x = -hx - 0.6 + i * (2 * hx + 1.2) / 9
			d.seg((x, side * (hy + 0.7), top - 0.45), (x + rng.uniform(-0.1, 0.1), side * (hy + 0.95), top - 0.85 - rng.uniform(0, 0.3)), 0.07, 0.0, BAMBOO, sides=4, grad=(0.2, 0.9))
	p.seg((-hx - 0.8, 0, top + 1.55), (hx + 0.8, 0, top + 1.55), 0.12, 0.12, HIDE, sides=5)
	# the crooked chimney up the +X end
	z = F + 0.2
	x, y = hx + 0.3, 0.6
	for k in range(7):
		p.box((0.62 - k * 0.03, 0.62 - k * 0.03, 0.62), (x, y, z + 0.3), STONE_DARK if k % 2 else MOOR_STONE,
			  rot=(rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(-15, 15)), grad=(0.1, 0.9), jitter=0.03)
		z += 0.6
		x += 0.05 + 0.03 * k
		y += rng.uniform(-0.06, 0.06)
	p.box((0.7, 0.3, 0.1), (x - 0.05, y, z), STONE_DARK)
	# things hung under the eaves
	for k, (hx_, kind) in enumerate(((-1.4, "herb"), (-0.7, "bone"), (0.6, "herb"), (1.3, "skull"))):
		yy = -hy - 0.55
		zz = top - 0.3
		d.seg((hx_, yy, zz), (hx_, yy, zz - 0.45), 0.008, 0.008, HIDE, sides=3)
		if kind == "herb":
			d.seg((hx_, yy, zz - 0.4), (hx_, yy, zz - 0.8), 0.1, 0.02, LEAF if k else MOSS, sides=5, grad=(0.3, 0.9))
		elif kind == "bone":
			_bone(d, (hx_ - 0.12, yy, zz - 0.5), (hx_ + 0.12, yy, zz - 0.6), r=0.02)
		else:
			_skull(d, (hx_, yy, zz - 0.7), 0.9)
	_heather_tuft(d, (1.2, 0.2, top + 1.2), 0.8)                            # heather rooted in the roof
	obj = join_into(p.build(bevel=0.04), [d.build(), _plumes("hag_hut_smoke", 750, [((x - 0.05, y, z + 0.1), 2.6, 0.16)], alpha=0.3)])
	obj.data.transform(Matrix(((1, 0, 0.06, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))))
	return obj


def hag_cauldron():
	"""A bog hag's cauldron: a big black iron pot (1.6 m across, rim at 1.2 m)
	hung by a chain from a crooked tripod over a ring of stones and a fire of
	peat and roots, brimming with a glowing green brew that bubbles and slops
	over, a bone and a ladle in it. About 2.8 m tall. Collide it as a box."""
	p = Prop("hag_cauldron", 751)
	soft = Prop("hag_cauldron_soft", 752)
	rng = p.rng
	for k in range(10):                                                    # the fire ring
		a = k * math.tau / 10 + rng.uniform(-0.1, 0.1)
		p.rock((0.42, 0.36, 0.3), (math.cos(a) * 1.2, math.sin(a) * 1.2, 0.08), STONE_DARK if k % 2 else MOOR_STONE)
	_coals(soft, (0, 0, 0.05), 1.3, 1.3, glow=1.3, flames=5, flame_h=0.45)
	for k in range(5):
		a = k * math.tau / 5
		soft.seg((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.1), (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.25), 0.08, 0.06, WOOD_GRAY, sides=5, grad=(0.3, 1.0))
	pot = _lathe(p, [(0.05, 0.35), (0.45, 0.38), (0.74, 0.6), (0.8, 0.88), (0.72, 1.1), (0.64, 1.16), (0.7, 1.2), (0.68, 1.26), (0.58, 1.22), (0.56, 1.12), (0.05, 1.1)],
				 16, IRON, grad=(0.0, 0.8))
	for s in (-1, 1):                                                      # the bail
		p.seg((s * 0.72, 0, 1.05), (s * 0.3, 0, 2.05), 0.025, 0.025, IRON, sides=4)
	p.seg((-0.3, 0, 2.05), (0.3, 0, 2.05), 0.025, 0.025, IRON, sides=4)
	for k in range(3):                                                     # the tripod
		a = k * math.tau / 3 + 0.4
		p.seg((math.cos(a) * 1.7, math.sin(a) * 1.7, -0.2), (math.cos(a) * 0.1, math.sin(a) * 0.1, 2.85), 0.08, 0.06, WOOD_GRAY, sides=5, grad=(0.2, 1.0))
		p.seg((math.cos(a) * 0.1, math.sin(a) * 0.1, 2.85), (math.cos(a) * -0.25, math.sin(a) * -0.25, 3.1), 0.06, 0.03, WOOD_GRAY, sides=4)
	p.seg((0, 0, 2.7), (0, 0, 2.9), 0.14, 0.14, HIDE, sides=6)
	for k in range(5):
		_torus(soft, (0, 0, 2.62 - k * 0.12), (0, 0, 1), (1, 0, 0) if k % 2 else (0, 1, 0), 0.05, 0.015, IRON, stretch=1.5, seg=6, ring=3)
	soft.seg((0, 0, 1.13), (0, 0, 1.18), 0.6, 0.6, BREW, sides=16, grad=(0.3, 0.5), glow=1.6)
	for k in range(7):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(0.0, 0.45)
		b = rng.uniform(0.08, 0.18)
		soft.blob((b, b, b * 0.7), (math.cos(a) * r, math.sin(a) * r, 1.19), BREW, segs=(6, 4), grad=(0.2, 0.45), glow=1.6)
	for a in (0.5, 2.0, 3.9, 5.1):
		soft.seg((math.cos(a) * 0.68, math.sin(a) * 0.68, 1.26), (math.cos(a) * 0.8, math.sin(a) * 0.8, 0.85), 0.05, 0.015, BREW, sides=4, grad=(0.3, 0.6), glow=1.6)
	_bone(soft, (0.2, -0.1, 1.0), (0.45, -0.3, 1.55), r=0.035)
	soft.seg((-0.25, 0.2, 0.95), (-0.7, 0.45, 1.9), 0.035, 0.03, WOOD_GRAY, sides=5)   # the ladle
	_skull(soft, (1.05, -0.9, 0.0), 0.9, yaw=-0.5)
	return join_into(p.build(bevel=0.015), [soft.build(), _plumes("hag_cauldron_steam", 753, [((0.1, 0, 1.3), 1.8, 0.2)], alpha=0.22)])


def bog_totem():
	"""A bog hag's totem: a bundle of crooked sticks about 2.5 m tall, bound
	with hide, a skull on top, a crossbar hung with dangling charms (bones,
	stones, feathers, a little bell) and a ring of stones at its foot.
	Collide it as a box."""
	p = Prop("bog_totem", 754)
	rng = p.rng
	for k in range(7):                                                     # the bundle
		a = k * math.tau / 7
		r = 0.1
		top = (math.cos(a) * 0.14 + rng.uniform(-0.08, 0.08), math.sin(a) * 0.14 + rng.uniform(-0.08, 0.08), 2.1 + rng.uniform(-0.2, 0.4))
		_chain(p, [(math.cos(a) * 0.2, math.sin(a) * 0.2, -0.3), (math.cos(a) * r + rng.uniform(-0.05, 0.05), math.sin(a) * r, 1.1), top], 0.06, 0.03, WOOD_GRAY if k % 2 else WOOD, sides=5, grad=(0.2, 1.0))
	for z in (0.5, 1.2, 1.8):
		p.seg((0, 0, z), (0, 0, z + 0.14), 0.19, 0.18, HIDE, sides=7)
	_skull(p, (0, 0, 2.12), 1.5)
	for s in (-1, 1):                                                      # antlers behind the skull
		_chain(p, [(s * 0.1, 0.08, 2.3), (s * 0.35, 0.15, 2.55), (s * 0.45, 0.1, 2.8)], 0.03, 0.015, BONE, sides=4)
		p.seg((s * 0.35, 0.15, 2.55), (s * 0.5, 0.2, 2.62), 0.02, 0.01, BONE, sides=3)
	p.seg((-0.7, 0, 1.6), (0.7, 0.05, 1.68), 0.04, 0.035, WOOD_GRAY, sides=5)
	for k, x in enumerate((-0.6, -0.35, -0.1, 0.2, 0.45, 0.65)):         # the charms
		L = rng.uniform(0.35, 0.7)
		zt = 1.62 + x * 0.05
		p.seg((x, 0, zt), (x, 0, zt - L), 0.007, 0.007, HIDE, sides=3)
		e = (x, 0, zt - L)
		kind = k % 4
		if kind == 0:
			_bone(p, (x - 0.05, 0, e[2]), (x + 0.03, 0, e[2] - 0.2), r=0.018)
		elif kind == 1:
			p.rock((0.12, 0.1, 0.14), (x, 0, e[2] - 0.05), MOOR_STONE)
		elif kind == 2:
			p.blob((0.05, 0.02, 0.3), (x, 0, e[2] - 0.13), IRON, segs=(5, 3), rot=(0, 10, 0))   # a crow feather
		else:
			p.seg((x, 0, e[2]), (x, 0, e[2] - 0.12), 0.03, 0.07, BRONZE, sides=8, grad=(0.0, 0.6))
	for k in range(6):
		a = k * math.tau / 6 + 0.3
		p.rock((0.35, 0.3, 0.25), (math.cos(a) * 0.45, math.sin(a) * 0.45, 0.05), STONE_DARK if k % 2 else MOOR_STONE)
	p.blob((0.9, 0.9, 0.1), (0, 0, 0.0), MOSS, segs=(8, 3), grad=(0.3, 0.9))
	return p.build()


def wind_bent_tree():
	"""A gnarled moor tree bent hard by the wind: a knotted gray trunk (slim at
	the ground) leaning down-wind (+X), its dark crown swept flat into a long
	ragged mass off to the +X side, a few bare snags on the windward side.
	About 5 m tall, 6 m long. Use it in a zone's tree_mix (trunk collider)."""
	p = Prop("wind_bent_tree", 755)
	rng = p.rng
	trunk = [(0, 0, -0.3), (0.12, 0.02, 0.9), (0.45, -0.05, 1.8), (1.0, 0.05, 2.6), (1.8, 0.0, 3.2), (2.6, 0.08, 3.55)]
	_chain(p, trunk, 0.34, 0.12, WOOD_GRAY, sides=7, grad=(0.3, 1.0))
	for k in range(4):                                                     # root flare
		a = k * math.tau / 4 + 0.6
		p.seg((0, 0, 0.4), (math.cos(a) * 0.85, math.sin(a) * 0.85, -0.2), 0.18, 0.05, WOOD_GRAY, sides=5, grad=(0.4, 1.0))
	for c in ((0.1, 0.25, 1.0), (0.55, -0.25, 2.0), (1.1, 0.2, 2.7)):     # knots
		p.blob((0.3, 0.28, 0.3), c, WOOD_GRAY, segs=(6, 4), grad=(0.3, 1.0))
	limbs = []
	for k, (i, a, L, rise) in enumerate(((2, 1.2, 1.9, 1.0), (2, -1.1, 1.8, 0.8), (3, 0.6, 2.0, 0.7), (3, -0.5, 2.2, 0.6), (4, 0.2, 1.6, 0.4))):
		b = Vector(trunk[i])
		e = b + Vector((math.cos(a) * 0.5 + 1.0, math.sin(a) * 0.9, rise)).normalized() * L
		p.seg(tuple(b), tuple(e), 0.12, 0.04, WOOD_GRAY, sides=5, grad=(0.3, 1.0))
		limbs.append(e)
	for c, a in (((0.35, 0.0, 1.5), 2.8), ((0.8, 0.1, 2.3), 3.3)):         # bare snags to windward
		b = Vector(c)
		e = b + Vector((math.cos(a) * 0.9, math.sin(a) * 0.4, 0.5))
		p.seg(tuple(b), tuple(e), 0.06, 0.015, WOOD_GRAY, sides=4, grad=(0.2, 0.8))
	# the swept crown: long flat leaf masses streaming +X
	masses = [((2.2, 0.0, 4.0), (3.2, 2.4, 1.3)), ((3.4, 0.3, 3.7), (2.8, 2.0, 1.1)), ((1.4, -0.4, 3.9), (2.2, 2.0, 1.2)),
			  ((4.3, -0.2, 3.35), (2.0, 1.5, 0.8)), ((2.8, -0.9, 3.5), (2.0, 1.4, 0.9)), ((2.6, 1.1, 3.6), (2.2, 1.4, 0.9))]
	for k, (c, s) in enumerate(masses):
		p.rock(s, c, LEAF if k % 2 else PINE, rot=(0, -8, rng.uniform(-10, 10)), grad=(0.25, 1.0), jitter=0.05)
	for e in limbs[:2]:
		p.rock((1.4, 1.2, 0.7), tuple(e + Vector((0.4, 0, 0.1))), LEAF, grad=(0.25, 1.0), jitter=0.05)
	return p.build()


def heather():
	"""Clutter: a low tuft of heather, about 0.4 m tall and 0.6 m across: a
	dark green cushion with lilac-purple bloom. Very few faces; colored, not
	tinted. No collision."""
	p = Prop("heather", 756)
	p.blob((0.62, 0.55, 0.26), (0, 0, 0.07), PINE, segs=(6, 3), grad=(0.4, 1.0))
	for k in range(4):
		a = k * math.tau / 4 + p.rng.uniform(-0.3, 0.3)
		r = 0.12 if k else 0.0
		h = p.rng.uniform(0.24, 0.34)
		p.blob((0.26, 0.24, 0.18), (math.cos(a) * r, math.sin(a) * r, h), HEATHER, segs=(5, 3), grad=(0.0, 0.55))
	for k in range(3):                                                     # a few sprigs sticking up
		a = k * math.tau / 3 + 0.4
		p.seg((math.cos(a) * 0.12, math.sin(a) * 0.12, 0.15), (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.42), 0.045, 0.0, HEATHER, sides=3, grad=(0.0, 0.5))
	return p.build()


# ---- Hollow Air

def _isle_body(p, c, R, depth, sx=1.0, sy=0.85, rock=MOOR_STONE, rock2=STONE_DARK):
	"""A floating island's body round c (its turf top at c.z): a turf cap, a
	band of raw earth and a jagged rock cone tapering `depth` meters down to a
	point, squashed to sx by sy."""
	x, y, z = c
	j = R * 0.035
	m = Matrix.Translation((x, y, 0)) @ Matrix.Diagonal((sx, sy, 1, 1))
	parts = [
		_lathe(p, [(0.05, z + 0.4), (R * 0.55, z + 0.36), (R * 0.95, z + 0.1), (R * 1.03, z - 0.3), (R * 0.97, z - 0.6), (0.05, z - 0.6)], 16, LEAF, grad=(0.0, 0.8), jitter=j),
		_lathe(p, [(0.05, z - 0.4), (R * 0.99, z - 0.45), (R * 0.93, z - 1.5), (R * 0.8, z - 2.6), (0.05, z - 2.6)], 16, EARTH, grad=(0.2, 1.0), jitter=j * 1.4),
		_lathe(p, [(0.05, z - 2.3), (R * 0.84, z - 2.4), (R * 0.62, z - depth * 0.38), (R * 0.36, z - depth * 0.64), (R * 0.14, z - depth * 0.88), (0.05, z - depth)],
			   12, rock, grad=(0.05, 0.95), jitter=j * 2.0),
	]
	for o in parts:
		o.data.transform(m)
	rng = p.rng
	for k in range(int(R * 0.9)):                                          # rocks jutting from the cone
		a = rng.uniform(0, math.tau)
		t = rng.uniform(0.3, 0.7)
		rr = R * (0.84 - 0.7 * t) * 0.95
		s = R * rng.uniform(0.16, 0.26) * (1.1 - t)
		p.rock((s, s * 0.9, s * 1.3), (x + math.cos(a) * rr * sx, y + math.sin(a) * rr * sy, z - 2.4 - (depth - 2.4) * t), rock2 if k % 2 else rock, rot=(0, 0, math.degrees(a)))
	return parts


def _isle_roots(p, c, R, n, length, sx=1.0, sy=0.85):
	"""Roots hanging from under a floating island's turf, curling as they fall."""
	x, y, z = c
	rng = p.rng
	for k in range(n):
		a = k * math.tau / n + rng.uniform(-0.3, 0.3)
		r0 = R * rng.uniform(0.75, 0.92)
		pts = [(x + math.cos(a) * r0 * sx, y + math.sin(a) * r0 * sy, z - 1.2)]
		L = length * rng.uniform(0.6, 1.1)
		for j in range(1, 5):
			t = j / 4
			pts.append((pts[0][0] + math.cos(a) * 0.4 * t + rng.uniform(-0.3, 0.3), pts[0][1] + math.sin(a) * 0.4 * t + rng.uniform(-0.3, 0.3), z - 1.2 - L * t))
		_chain(p, pts, 0.16, 0.03, WOOD_GRAY, sides=5, grad=(0.3, 1.0))


def _isle_tree(p, c, h, kind):
	"""A small tree standing on a floating island: a pine or a round leafy one."""
	x, y, z = c
	if kind == "pine":
		p.seg((x, y, z - 0.3), (x, y, z + h * 0.4), h * 0.05, h * 0.035, WOOD, sides=6, grad=(0.3, 0.9))
		for k, (t, r) in enumerate(((0.22, 0.3), (0.42, 0.24), (0.6, 0.17), (0.76, 0.1))):
			p.seg((x, y, z + h * t), (x, y, z + h * (t + 0.3)), h * r, 0.0, PINE, sides=7, grad=(0.0, 0.75), jitter=0.04, twist=k * 23)
	else:
		p.seg((x, y, z - 0.3), (x, y, z + h * 0.55), h * 0.06, h * 0.04, WOOD, sides=6, grad=(0.3, 0.9))
		for (dx, dy, dz), s in (((0, 0, 0.72), 0.5), ((0.18, 0.08, 0.6), 0.34), ((-0.15, -0.1, 0.62), 0.36), ((0.02, 0.12, 0.88), 0.3)):
			p.rock((h * s, h * s, h * s * 0.85), (x + dx * h, y + dy * h, z + dz * h), LEAF, grad=(0.0, 0.7), jitter=0.05)


def _isle_debris(p, c, R, n, below):
	"""A few small rocks drifting under a floating island."""
	x, y, z = c
	for k in range(n):
		a = p.rng.uniform(0, math.tau)
		r = R * p.rng.uniform(0.2, 0.6)
		s = p.rng.uniform(0.6, 1.4)
		p.rock((s, s * 0.9, s * 1.2), (x + math.cos(a) * r, y + math.sin(a) * r, z - below * p.rng.uniform(0.9, 1.25)), MOOR_STONE if k % 2 else STONE_DARK, rot=(0, 0, p.rng.uniform(0, 360)))


def floating_isle():
	"""A floating island about 20 x 16 m: a turf top 29 m up over a band of
	earth and a jagged rock cone tapering to a point 18 m above the ground,
	with a pine and a leafy tree, boulders, a second lobe off to one side,
	roots trailing beneath and a few drifting rocks. Nothing reaches the
	ground. Collide it as none."""
	p = Prop("floating_isle", 760)
	top, depth = 29.0, 11.0
	_isle_body(p, (0, 0, top), 9.0, depth, 1.1, 0.85)
	_isle_body(p, (6.5, 3.0, top - 0.8), 4.2, 6.0, 1.0, 0.9, rock=STONE_DARK, rock2=MOOR_STONE)
	_isle_roots(p, (0, 0, top), 9.0, 9, 5.0, 1.1, 0.85)
	_isle_roots(p, (6.5, 3.0, top - 0.8), 4.2, 4, 3.0, 1.0, 0.9)
	_isle_tree(p, (-2.5, 1.0, top + 0.3), 7.0, "pine")
	_isle_tree(p, (2.0, -2.0, top + 0.3), 5.5, "round")
	for x, y, s in ((4.5, -3.0, 1.8), (-5.5, -2.0, 1.3), (6.8, 3.0, 1.5)):
		p.rock((s * 1.2, s, s * 0.8), (x, y, top + 0.2), MOOR_STONE, rot=(0, 0, p.rng.uniform(0, 360)))
	_isle_debris(p, (0, 0, top - depth), 9.0, 4, 3.0)
	return p.build()


def floating_isle_b():
	"""The biggest floating island, about 24 x 20 m: a turf top 38 m up and a
	deep rock cone to a point 24 m above the ground, three trees, the stump of a
	white stone column and fallen drums from some older sky-house, a long root
	curtain beneath and drifting rocks. Collide it as none."""
	p = Prop("floating_isle_b", 762)
	top, depth = 38.0, 14.0
	_isle_body(p, (0, 0, top), 11.0, depth, 1.0, 0.9)
	_isle_body(p, (-7.0, -5.0, top - 1.2), 4.5, 7.0, 1.0, 0.8, rock=STONE_DARK, rock2=MOOR_STONE)
	_isle_body(p, (8.0, 3.0, top - 0.5), 3.5, 5.0, 1.0, 1.0)
	_isle_roots(p, (0, 0, top), 11.0, 12, 7.0, 1.0, 0.9)
	_isle_roots(p, (-7.0, -5.0, top - 1.2), 4.5, 5, 4.0, 1.0, 0.8)
	_isle_tree(p, (-3.0, 3.5, top + 0.3), 8.0, "pine")
	_isle_tree(p, (-6.0, 0.5, top + 0.2), 6.0, "pine")
	_isle_tree(p, (4.0, 4.0, top + 0.3), 6.0, "round")
	p.box((2.4, 2.4, 0.6), (2.0, -3.0, top + 0.45), CLOUD_STONE, grad=(0.1, 0.8))       # a broken white column
	p.seg((2.0, -3.0, top + 0.7), (2.0, -3.0, top + 3.6), 0.75, 0.72, CLOUD_STONE, sides=10, grad=(0.05, 0.6))
	for k in range(3):
		a = k * math.tau / 3 + 0.4
		p.seg((2.0 + math.cos(a) * 0.35, -3.0 + math.sin(a) * 0.35, top + 3.5), (2.0 + math.cos(a) * 0.45, -3.0 + math.sin(a) * 0.45, top + 4.1 + 0.3 * k), 0.4, 0.05, CLOUD_STONE, sides=4)
	p.seg((4.0, -5.5, top + 0.75), (6.6, -4.2, top + 0.6), 0.72, 0.72, CLOUD_STONE, sides=10, grad=(0.05, 0.6))
	p.seg((-0.5, -6.0, top + 0.6), (-0.9, -7.6, top + 0.5), 0.7, 0.7, SILVER, sides=10, grad=(0.05, 0.6))
	for x, y, s in ((5.5, 0.0, 1.6), (-3.0, -3.5, 1.2), (8.5, 3.5, 1.4)):
		p.rock((s * 1.2, s, s * 0.8), (x, y, top + 0.2), MOOR_STONE, rot=(0, 0, p.rng.uniform(0, 360)))
	_isle_debris(p, (0, 0, top - depth), 11.0, 5, 3.5)
	return p.build()


def floating_isle_c():
	"""A small floating island about 16 x 12 m: a turf top 23 m up, a stubby
	cone to a point 14 m above the ground, one leafy tree leaning out over the
	edge with its roots hanging far down, a boulder, and drifting rocks.
	Collide it as none."""
	p = Prop("floating_isle_c", 764)
	top, depth = 23.0, 9.0
	_isle_body(p, (0, 0, top), 7.5, depth, 1.05, 0.8, rock=STONE_DARK, rock2=MOOR_STONE)
	_isle_roots(p, (0, 0, top), 7.5, 10, 6.0, 1.05, 0.8)
	p.seg((5.0, 1.0, top + 0.2), (7.4, 1.3, top + 2.4), 0.3, 0.2, WOOD, sides=6, grad=(0.3, 0.9))   # a tree leaning out
	for (x, y, z), s in (((7.8, 1.4, top + 3.2), 3.2), ((8.6, 0.6, top + 2.8), 2.2), ((7.2, 2.2, top + 3.0), 2.2)):
		p.rock((s, s, s * 0.85), (x, y, z), LEAF, grad=(0.0, 0.7), jitter=0.05)
	_chain(p, [(6.5, 1.0, top - 0.8), (7.0, 1.2, top - 3.0), (6.8, 0.9, top - 6.0), (7.1, 1.1, top - 8.5)], 0.14, 0.03, WOOD_GRAY, sides=5, grad=(0.3, 1.0))
	_isle_tree(p, (-2.5, -1.0, top + 0.3), 5.0, "pine")
	p.rock((2.2, 1.9, 1.5), (-1.0, 2.2, top + 0.3), MOOR_STONE)
	_isle_debris(p, (0, 0, top - depth), 7.5, 3, 2.5)
	return p.build()


def wind_rift():
	"""The torn heart of Hollow Air: a shallow crater 30 m across and no more
	than 0.45 m high: a dark scoured floor 18 m across ringed by broken, tilted
	paving and rubble, pale blue glowing cracks running out from the middle
	through the stone. Lies on the ground. Collide it as none."""
	p = Prop("wind_rift", 766)
	rng = p.rng
	_lathe(p, [(0.05, 0.03), (8.0, 0.05), (9.4, 0.0), (9.6, -0.5), (0.05, -0.5)], 24, STONE_DARK, grad=(0.3, 0.95), jitter=0.04)
	for k in range(38):                                                    # broken paving round the rim
		a = k * math.tau / 38 + rng.uniform(-0.06, 0.06)
		r = rng.uniform(9.0, 14.2)
		w, dd = rng.uniform(1.6, 3.0), rng.uniform(1.2, 2.2)
		tilt = 6 * (1 - (r - 9) / 5.5)
		p.box((w, dd, 0.35), (math.cos(a) * r, math.sin(a) * r, -0.08 + 0.1 * (1 - (r - 9) / 5.5)), (STONE_WARM, MOOR_STONE, STONE_LIGHT)[k % 3],
			  rot=(0, tilt, math.degrees(a) + rng.uniform(-15, 15)), grad=(0.1, 0.9), jitter=0.05)
	for k in range(22):                                                    # rubble
		a = rng.uniform(0, math.tau)
		r = rng.uniform(7.5, 14.5)
		s = rng.uniform(0.4, 0.9)
		p.rock((s, s * 0.9, s * 0.55), (math.cos(a) * r, math.sin(a) * r, 0.0), MOOR_STONE if k % 2 else STONE_DARK, rot=(0, 0, rng.uniform(0, 360)))
	d = Prop("wind_rift_cracks", 767)
	for k in range(11):                                                    # the glowing cracks
		a = k * math.tau / 11 + rng.uniform(-0.15, 0.15)
		pts, r, aa = [(math.cos(a) * 0.6, math.sin(a) * 0.6, 0.06)], 0.6, a
		L = rng.uniform(10.0, 14.8)
		while r < L:
			r += rng.uniform(1.0, 1.8)
			aa += rng.uniform(-0.18, 0.18)
			pts.append((math.cos(aa) * r, math.sin(aa) * r, 0.06 if r < 9.2 else 0.12))
			if rng.random() < 0.3:                                         # a branch
				ba = aa + rng.choice((-1, 1)) * rng.uniform(0.3, 0.6)
				bb = (pts[-1][0] + math.cos(ba) * 1.6, pts[-1][1] + math.sin(ba) * 1.6, pts[-1][2])
				d.seg(pts[-1], bb, 0.07, 0.02, SKY, sides=4, grad=(0.0, 0.3), glow=1.4)
		_chain(d, pts, 0.16, 0.03, SKY, sides=4, grad=(0.0, 0.3), glow=1.6)
	d.seg((0, 0, -0.1), (0, 0, 0.08), 1.2, 0.9, SKY, sides=10, grad=(0.0, 0.3), glow=2.0)   # the bright wound at the middle
	for k in range(6):
		a = k * math.tau / 6 + 0.3
		d.rock((0.7, 0.6, 0.5), (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.05), STONE_DARK, rot=(0, 0, math.degrees(a)))
	return join_into(p.build(), [d.build()])


def tethered_isle():
	"""A small floating island (about 10 x 8.5 m) held down by four iron chains
	to rune-carved stone anchor blocks on the ground 7.5 m out; its turf top is
	8.8 m up and its underside no lower than 5 m, so you can walk beneath it.
	A tree, rocks and hanging roots (none lower than about 4 m). Collide it as a
	mesh: only the anchors and chains come near the ground."""
	p = Prop("tethered_isle", 768)
	d = Prop("tethered_isle_chains", 769)
	top, depth = 8.8, 3.8
	_isle_body(p, (0, 0, top), 5.0, depth, 1.0, 0.85)
	_isle_roots(p, (0, 0, top), 5.0, 7, 2.6, 1.0, 0.85)
	_isle_tree(p, (-1.0, 0.6, top + 0.3), 5.5, "round")
	p.rock((1.6, 1.3, 1.1), (2.0, -1.2, top + 0.2), MOOR_STONE)
	for k in range(4):
		a = math.radians(45 + 90 * k)
		ax, ay = math.cos(a) * 7.5, math.sin(a) * 7.5
		_block(p, (1.4, 1.4, 1.2), (ax, ay, 0.45), STONE_DARK if k % 2 else MOOR_STONE, yaw=math.degrees(a), rough=0.05)
		p.box((1.6, 1.6, 0.25), (ax, ay, 0.0), STONE_DARK, rot=(0, 0, math.degrees(a)), grad=(0.3, 0.9))
		rs = len(d.parts)
		_rune(d, (0, -0.73, 0), 0.5, k + 1, glow=1.0)                        # a rune on the face toward the isle
		_move_parts(d, rs, Matrix.Translation((ax, ay, 0.5)) @ Matrix.Rotation(a - math.pi / 2, 4, "Z"))
		_torus(d, (ax, ay, 1.12), (0, 0, 1), (math.cos(a), math.sin(a), 0), 0.2, 0.05, IRON, stretch=1.0, seg=10, ring=4)
		hook = (math.cos(a) * 3.7, math.sin(a) * 3.7 * 0.85, top - 1.6)
		_iron_chain(d, (ax, ay, 1.3), hook)
		d.box((0.5, 0.5, 0.4), hook, IRON, rot=(0, 0, math.degrees(a)), grad=(0.1, 0.7))
	return join_into(p.build(), [d.build()])


def _cloud_column(p, x, y, z0, h, r=0.85):
	"""A white stone column with a silver-banded base and capital."""
	p.box((r * 2.6, r * 2.6, 0.5), (x, y, z0 + 0.25), CLOUD_STONE, grad=(0.1, 0.7))
	p.seg((x, y, z0 + 0.5), (x, y, z0 + 0.8), r * 1.2, r * 1.05, SILVER, sides=12, grad=(0.0, 0.6))
	p.seg((x, y, z0 + 0.8), (x, y, z0 + h - 0.9), r, r * 0.9, CLOUD_STONE, sides=12, grad=(0.0, 0.5))
	p.seg((x, y, z0 + h - 0.9), (x, y, z0 + h - 0.5), r * 0.92, r * 1.3, SILVER, sides=12, grad=(0.0, 0.6))
	p.box((r * 2.8, r * 2.8, 0.5), (x, y, z0 + h - 0.25), CLOUD_STONE, grad=(0.0, 0.6))


def cloud_hall():
	"""The cloud giants' hall: white stone and silver, 30 x 24 m and 15.6 m to
	the roof. A portico of six columns across the front (-Y) before a doorway
	7 m wide and 9 m tall; inside, a flat floor at ground level (top 0.05 m), two
	rows of columns, a great stone table and seat at the back under silver
	banners, and an open oculus in the roof. Walls are separate solid pieces.
	Collide it as a mesh."""
	p = Prop("cloud_hall", 770)
	d = Prop("cloud_hall_detail", 771)
	H = 14.0
	p.box((30.0, 24.0, 1.0), (0, 0, -0.45), CLOUD_STONE, grad=(0.05, 0.6))          # floor, top at 0.05
	for k in range(5):                                                   # silver inlay down the nave
		p.box((1.6, 0.18, 0.02), (0, -6.0 + k * 3.5, 0.055), SILVER, grad=(0.0, 0.4))
	# walls: back, sides and the front with its doorway
	p.box((30.0, 1.2, H), (0, 11.4, H / 2), CLOUD_STONE, grad=(0.0, 0.7))
	for s in (-1, 1):
		p.box((1.2, 20.6, H), (s * 14.4, 1.4, H / 2), CLOUD_STONE, grad=(0.0, 0.7))
		p.box((11.5, 1.2, H), (s * 9.25, -8.0, H / 2), CLOUD_STONE, grad=(0.0, 0.7))
		p.box((0.5, 1.5, 9.0), (s * 3.75, -8.0, 4.5), SILVER, grad=(0.0, 0.6))   # door jambs
		for k in range(3):                                               # tall window recesses on the sides
			d.box((0.12, 1.6, 6.0), (s * 15.02, -3.0 + k * 6.0, 7.0), SHADE, grad=(0.8, 1.0))
			d.box((0.16, 2.0, 0.3), (s * 15.04, -3.0 + k * 6.0, 10.15), SILVER, grad=(0.0, 0.5))
	p.box((7.0, 1.2, H - 9.0), (0, -8.0, 9.0 + (H - 9.0) / 2), CLOUD_STONE, grad=(0.0, 0.7))   # lintel
	p.box((8.0, 1.5, 0.5), (0, -8.0, 9.25), SILVER, grad=(0.0, 0.6))
	# roof with an oculus, a silver cornice round it
	RZ = H + 0.6
	for (x0, x1, y0, y1) in ((-15, 15, -12, -1.0), (-15, 15, 6.0, 12), (-15, -4.0, -1.0, 6.0), (4.0, 15, -1.0, 6.0)):
		p.box((x1 - x0, y1 - y0, 1.2), ((x0 + x1) / 2, (y0 + y1) / 2, RZ), CLOUD_STONE, grad=(0.0, 0.6))
	for (sx, sy, cx, cy) in ((30.6, 0.4, 0, -12.1), (30.6, 0.4, 0, 12.1), (0.4, 24.6, -15.1, 0), (0.4, 24.6, 15.1, 0)):
		p.box((sx, sy, 0.5), (cx, cy, H - 0.1), SILVER, grad=(0.0, 0.5))
	p.box((31.0, 3.0, 1.0), (0, -12.0, RZ + 1.0), CLOUD_STONE, grad=(0.0, 0.6))    # the attic over the portico
	d.seg((0, -13.52, RZ + 1.0), (0, -13.6, RZ + 1.0), 1.1, 1.1, SILVER, sides=16, grad=(0.0, 0.5))
	d.seg((0, -13.6, RZ + 1.0), (0, -13.68, RZ + 1.0), 0.7, 0.7, SKY, sides=16, grad=(0.0, 0.4), glow=0.6)
	# the portico and the inner columns
	for x in (-12.5, -8.5, -5.0, 5.0, 8.5, 12.5):
		_cloud_column(p, x, -10.6, 0.05, H - 0.05)
	for x in (-7.0, 7.0):
		for y in (-3.5, 1.5, 6.5):
			_cloud_column(p, x, y, 0.05, H - 0.05)
	# the giants' table and seat at the back
	p.box((8.0, 3.0, 0.5), (0, 5.5, 3.2), STONE_LIGHT, grad=(0.0, 0.6))
	for x in (-3.3, 3.3):
		p.box((1.0, 2.2, 3.0), (x, 5.5, 1.5), CLOUD_STONE, grad=(0.1, 0.7))
	p.box((6.0, 2.4, 1.8), (0, 9.2, 0.9), CLOUD_STONE, grad=(0.1, 0.7))
	p.box((6.4, 0.9, 7.0), (0, 10.4, 3.5), CLOUD_STONE, grad=(0.0, 0.6))
	p.box((6.6, 1.0, 0.4), (0, 10.4, 7.1), SILVER, grad=(0.0, 0.5))
	d.blob((0.9, 0.9, 1.0), (1.8, 5.2, 3.9), SILVER, segs=(10, 6), grad=(0.0, 0.6))      # a silver ewer, giant-sized
	d.seg((-1.5, 5.8, 3.45), (-1.5, 5.8, 3.6), 1.3, 1.3, SILVER, sides=14, grad=(0.0, 0.5))
	for k, x in enumerate((-9.5, -4.5, 4.5, 9.5)):                        # banners on the back wall
		d.box((2.2, 0.1, 6.0), (x, 10.75, 9.0), SKY if k % 2 else CLOTH_WHITE, grad=(0.0, 0.5))
		d.box((2.5, 0.2, 0.2), (x, 10.7, 12.05), SILVER)
		d.seg((x, 10.7, 7.0), (x, 10.7, 6.2), 0.9, 0.0, SKY if k % 2 else CLOTH_WHITE, sides=3, grad=(0.1, 0.6))
	# cloud wisps clinging to the roof
	w = Prop("cloud_hall_clouds", 772)
	for x, y, s in ((-13.5, 10.0, 4.0), (12.0, 9.0, 5.0), (14.0, -9.0, 3.5), (-12.0, -6.0, 3.0)):
		for k in range(4):
			w.blob((s * w.rng.uniform(0.8, 1.2), s * w.rng.uniform(0.6, 0.9), s * 0.45), (x + w.rng.uniform(-s, s) * 0.5, y + w.rng.uniform(-s, s) * 0.4, RZ + 0.8 + w.rng.uniform(0, 0.6)), CLOTH_WHITE, segs=(8, 5), grad=(0.0, 0.3))
	clouds = _translucent(w.build(), 0.55, 0.9)
	return join_into(p.build(bevel=0.06), [d.build(), clouds])


def cloud_pillar():
	"""A lone white stone column of the cloud giants, 10 m tall: a stepped
	plinth, a fluted shaft with silver bands, a silver capital and a silver cap
	with a pale blue stone at its crown. Collide it as a box."""
	p = Prop("cloud_pillar", 773)
	p.box((2.6, 2.6, 0.6), (0, 0, 0.1), CLOUD_STONE, grad=(0.1, 0.8))
	p.box((2.1, 2.1, 0.4), (0, 0, 0.6), STONE_LIGHT, grad=(0.1, 0.8))
	p.seg((0, 0, 0.8), (0, 0, 1.15), 0.95, 0.8, SILVER, sides=12, grad=(0.0, 0.6))
	p.seg((0, 0, 1.15), (0, 0, 8.3), 0.72, 0.64, CLOUD_STONE, sides=12, grad=(0.0, 0.5))
	for k in range(12):                                                   # fluting
		a = k * math.tau / 12 + math.pi / 12
		p.seg((math.cos(a) * 0.7, math.sin(a) * 0.7, 1.3), (math.cos(a) * 0.62, math.sin(a) * 0.62, 8.1), 0.05, 0.05, STONE_LIGHT, sides=4, grad=(0.2, 0.7))
	for z in (3.5, 6.0):
		p.seg((0, 0, z), (0, 0, z + 0.22), 0.76, 0.74, SILVER, sides=12, grad=(0.0, 0.5))
	p.seg((0, 0, 8.3), (0, 0, 8.8), 0.66, 1.0, SILVER, sides=12, grad=(0.0, 0.6))
	p.box((2.1, 2.1, 0.4), (0, 0, 9.0), CLOUD_STONE, grad=(0.0, 0.6))
	p.seg((0, 0, 9.2), (0, 0, 9.75), 0.95, 0.35, SILVER, sides=12, grad=(0.0, 0.6))
	p.blob((0.36, 0.36, 0.42), (0, 0, 9.9), SKY, segs=(8, 6), grad=(0.0, 0.4), glow=1.0)
	return p.build(bevel=0.05)


def wrecked_skyship():
	"""A crashed sky-bandit airship about 20 m long: a planked hull 14 m long
	lying rolled and nose-down in the ground with holes stove in, a stern cabin
	under a pale blue roof, its mast snapped and lying off the port side with a
	torn sail, one kite-wing still jutting broken from the hull and the other
	lying smashed on the ground, trailing ropes and spilled crates.
	Collide it as a mesh."""
	p = Prop("wrecked_skyship", 774)
	d = Prop("wrecked_skyship_detail", 775)
	rng = p.rng
	L0, L1, W, D, nu = -7.0, 7.0, 2.2, 3.0, 9
	start = len(p.parts)

	def section(y, shrink=1.0, lift=0.0):
		t = (y - L0) / (L1 - L0)
		w = W * max(0.12, math.sin(min(1.0, 0.06 + t * 0.9) * math.pi) ** 0.55) * shrink
		dep = D * shrink * (0.55 + 0.45 * math.sin(t * math.pi))
		g = D + 0.4 * (1 - t) ** 3
		return [(math.cos(math.pi * i / (nu - 1)) * w, y, g - math.sin(math.pi * i / (nu - 1)) * dep + lift) for i in range(nu)]

	nsec = 14
	ys = [L0 + (L1 - L0) * k / nsec for k in range(nsec + 1)]
	outer = [section(y) for y in ys]
	inner = [section(y, 0.9, 0.08) for y in ys]
	hole = {(k, i) for k in (5, 6) for i in (1, 2)} | {(9, 5), (9, 6), (10, 6)} | {(0, 3), (0, 4), (1, 4)}
	for grid, sw0, grad in ((outer, WOOD, (0.1, 0.9)), (inner, WOOD_GRAY, (0.4, 1.0))):
		for i in range(nu - 1):
			for k in range(nsec):
				if (k, i) in hole:
					continue
				sw = sw0 if grid is inner else (WOOD if i % 2 else WOOD_GRAY)
				p.poly([grid[k][i], grid[k + 1][i], grid[k + 1][i + 1], grid[k][i + 1]], [(0, 1, 2, 3)], sw, grad)
	for k in range(nsec):
		for i in (0, nu - 1):
			p.poly([outer[k][i], outer[k + 1][i], inner[k + 1][i], inner[k][i]], [(0, 1, 2, 3)], WOOD, grad=(0.0, 0.4))
	for k in (1, 5, 6, 9, 10):                                            # ribs showing through the holes
		_chain(p, section(ys[k] + 0.5, 0.95), 0.09, 0.09, WOOD, sides=4, grad=(0.2, 0.9))
	p.box((0.35, L1 - L0, 0.35), (0, 0, D - D * 0.98), WOOD, grad=(0.3, 1.0))   # keel
	p.poly(list(outer[-1]), [tuple(range(nu))], WOOD_GRAY, grad=(0.1, 0.9))      # transom
	for k in range(6):                                                   # the deck, planks missing
		y = -5.0 + k * 1.6
		if k in (2,):
			continue
		p.box((2 * W * 0.85, 1.5, 0.1), (0, y, D - 0.15), WOOD_GRAY if k % 2 else WOOD, rot=(0, 0, rng.uniform(-3, 3)), grad=(0.1, 0.6))
	p.box((3.0, 3.0, 2.0), (0, 5.2, D + 0.9), WOOD, grad=(0.2, 0.9))       # the stern cabin
	p.box((0.8, 0.1, 1.3), (0, 3.68, D + 0.75), SHADE, grad=(0.9, 1.0))
	for s in (-1, 1):
		p.box((0.1, 0.6, 0.5), (s * 1.52, 5.2, D + 1.2), SHADE, grad=(0.9, 1.0))
	rs = len(p.parts)
	_gable_roof(p, 3.4, 3.4, 1.1, D + 1.9, SKY)
	_move_parts(p, rs, Matrix.Translation((0, 5.2, 0)))
	p.seg((0, 7.2, D + 0.6), (0, 8.6, D + 1.4), 0.1, 0.05, WOOD, sides=5)  # the tiller
	p.seg((0, -7.0, D + 0.4), (0, -9.2, D + 1.6), 0.14, 0.05, WOOD, sides=6)   # the bowsprit
	p.seg((0, -1.0, D - 0.2), (0, -1.0, D + 2.4), 0.24, 0.2, WOOD, sides=8, grad=(0.2, 1.0))   # mast stump
	p.rock((0.45, 0.45, 0.4), (0, -1.0, D + 2.4), WOOD, jitter=0.08)
	# the broken kite-wing still jutting from the starboard side
	wing = [(W, -2.5, D - 0.2), (W + 4.2, -3.6, D + 1.6), (W + 5.6, -1.0, D + 2.1), (W + 3.2, 1.5, D + 1.0), (W, 0.8, D - 0.2)]
	for a, b in zip(wing, wing[1:]):
		p.seg(a, b, 0.08, 0.06, WOOD, sides=5)
	p.seg(wing[0], wing[2], 0.07, 0.05, WOOD, sides=5)
	for i, (a, b) in enumerate(zip(wing[:-1], wing[1:])):
		if i == 1:
			continue                                                      # a torn gap
		d.poly([(W + 0.4, -0.8, D + 0.2), a, b], [(0, 1, 2)], (HIDE, SKY, CLOTH_WHITE, HIDE)[i], grad=(0.2, 0.5))
	_move_parts(p, start, Matrix.Translation((0, 0, -1.0)) @ Matrix.Rotation(math.radians(8), 4, "X") @ Matrix.Rotation(math.radians(-20), 4, "Y"))
	for o in d.parts:
		o.data.transform(Matrix.Translation((0, 0, -1.0)) @ Matrix.Rotation(math.radians(8), 4, "X") @ Matrix.Rotation(math.radians(-20), 4, "Y"))
	# ploughed-up earth along the bow
	for k in range(7):
		p.rock((2.2, 1.4, 0.8), (rng.uniform(-3, 3), -7.5 + rng.uniform(-1.5, 1.5), 0.0), EARTH, rot=(0, 0, rng.uniform(0, 360)))
	# the mast lying off the port side with a torn sail
	p.seg((-4.5, -3.0, 0.3), (-6.5, 6.5, 0.25), 0.22, 0.16, WOOD, sides=8, grad=(0.2, 1.0))
	p.seg((-4.4, 3.0, 0.3), (-8.4, 2.4, 0.2), 0.1, 0.08, WOOD, sides=6)
	d.poly([(-4.6, -1.5, 0.35), (-5.6, 5.8, 0.28), (-8.0, 4.2, 0.1), (-7.6, 0.2, 0.08)], [(0, 1, 2, 3)], CLOTH_WHITE, grad=(0.3, 0.8))
	# the other kite-wing smashed on the ground to starboard
	for a, b in (((5.0, 3.0, 0.1), (9.5, 6.5, 0.15)), ((5.0, 3.0, 0.1), (8.2, 0.2, 0.1)), ((7.0, 1.5, 0.1), (7.8, 5.2, 0.15))):
		p.seg(a, b, 0.07, 0.05, WOOD, sides=5)
	d.poly([(5.1, 3.0, 0.14), (9.4, 6.4, 0.18), (7.9, 5.1, 0.18), (7.0, 1.6, 0.14)], [(0, 1, 2, 3)], SKY, grad=(0.2, 0.5))
	d.poly([(5.1, 3.0, 0.13), (7.0, 1.6, 0.13), (8.1, 0.3, 0.12)], [(0, 1, 2)], HIDE, grad=(0.2, 0.5))
	# ropes and spilled cargo
	for k in range(3):
		_rope(d, (-1.0 + k * 0.3, -1.0, D + 0.8 - k * 0.3), (-5.0 - k, 2.0 + k * 1.5, 0.1), 0.6, r=0.025)
	for x, y, s in ((-3.0, 7.5, 0.8), (-2.2, 8.4, 0.6), (4.0, 7.0, 0.7)):
		p.box((s, s, s), (x, y, s / 2 - 0.05), WOOD, rot=(0, 0, rng.uniform(0, 90)), grad=(0.2, 0.9))
	p.seg((3.0, 8.5, 0.35), (3.9, 8.9, 0.35), 0.35, 0.35, WOOD_GRAY, sides=10)   # a barrel on its side
	return join_into(p.build(bevel=0.02), [d.build()])


def serpent_roost():
	"""A wind serpents' roost: a spire of stacked blue-gray rock 10 m tall (5 m
	across at the foot), three ledges jutting from it at about 3.5, 6.2 and
	8.8 m each holding a woven nest with pale eggs, shed serpent skins draped
	down the rock, bones at its foot. Collide it as a mesh."""
	p = Prop("serpent_roost", 776)
	rng = p.rng
	z = 0.0
	for k, (sx, sy, sz) in enumerate(((5.0, 4.4, 2.6), (3.8, 3.4, 2.6), (3.0, 2.8, 2.4), (2.4, 2.2, 2.2), (1.8, 1.6, 2.0))):
		p.rock((sx, sy, sz), (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), z + sz * 0.45), MOOR_STONE if k % 2 else STONE_DARK, rot=(0, 0, rng.uniform(0, 360)))
		z += sz * 0.78
	p.seg((0, 0, z - 0.5), (0.2, 0.1, 10.2), 0.8, 0.1, MOOR_STONE, sides=5, jitter=0.06, twist=20)
	for k, (a, zz, reach) in enumerate(((-1.4, 3.5, 3.0), (1.0, 6.2, 2.4), (3.0, 8.8, 1.8))):
		dx, dy = math.cos(a), math.sin(a)
		c = (dx * reach, dy * reach, zz)
		p.rock((2.6, 2.2, 0.9), c, STONE_DARK if k % 2 else MOOR_STONE, rot=(0, 0, math.degrees(a)))
		p.rock((1.6, 1.4, 1.2), (dx * reach * 0.6, dy * reach * 0.6, zz - 0.6), MOOR_STONE)
		_stick_ring(p, (c[0], c[1], zz + 0.4), 0.8, 2, rng, r=0.05, length=(0.5, 0.9))
		p.blob((1.3, 1.3, 0.2), (c[0], c[1], zz + 0.45), HIDE, segs=(8, 4), grad=(0.3, 0.8))
		for j in range(2):
			p.blob((0.3, 0.3, 0.4), (c[0] + (j - 0.5) * 0.35, c[1], zz + 0.65), TEAL if (k + j) % 2 else BONE, segs=(7, 5), grad=(0.0, 0.6))
	for k in range(3):                                                    # shed skins draped down the rock
		a = k * 2.1 + 0.5
		pts = []
		for j in range(6):
			t = j / 5
			r = 1.4 + 1.2 * t + 0.25 * math.sin(t * 7)
			pts.append((math.cos(a + t * 0.8) * r, math.sin(a + t * 0.8) * r, 8.0 - k * 1.8 - t * 4.0))
		_chain(p, pts, 0.14, 0.06, SCALE_GREEN if k % 2 else BONE, sides=5, grad=(0.1, 0.7))
	for k in range(6):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(2.6, 3.8)
		c = Vector((math.cos(a) * r, math.sin(a) * r, 0.06))
		t = rng.uniform(0, math.pi)
		_bone(p, tuple(c - Vector((math.cos(t), math.sin(t), 0)) * 0.3), tuple(c + Vector((math.cos(t), math.sin(t), 0)) * 0.3), r=0.035)
	return p.build()


def fallen_isle():
	"""A floating island that fell: an earth-and-rock chunk about 12 m across
	crashed upside down and half buried, its rock point jutting up and over
	at about 8 m, roots clawing at the sky, a ring of thrown-up earth, turf
	and rocks round it. Collide it as a mesh."""
	p = Prop("fallen_isle", 778)
	start = len(p.parts)
	_isle_body(p, (0, 0, 0), 5.5, 8.5, 1.0, 0.9)
	_isle_roots(p, (0, 0, 0), 5.5, 8, 3.5, 1.0, 0.9)
	_move_parts(p, start, Matrix.Translation((0.5, 0, -0.6)) @ Matrix.Rotation(math.radians(20), 4, "Z") @ Matrix.Rotation(math.radians(148), 4, "X"))
	rng = p.rng
	for k in range(16):                                                   # the thrown-up earth
		a = k * math.tau / 16 + rng.uniform(-0.15, 0.15)
		r = rng.uniform(5.5, 7.0)
		p.rock((2.6, 1.8, 1.0), (math.cos(a) * r, math.sin(a) * r * 0.9, 0.0), EARTH if k % 3 else LEAF, rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.9))
	for k in range(6):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(6.5, 8.5)
		s = rng.uniform(0.6, 1.3)
		p.rock((s, s, s * 0.7), (math.cos(a) * r, math.sin(a) * r, 0.1), MOOR_STONE if k % 2 else STONE_DARK)
	p.seg((-5.0, -3.0, 0.3), (-8.5, -4.5, 1.1), 0.25, 0.12, WOOD, sides=6)   # a tree flung out of it
	p.rock((2.2, 2.0, 1.4), (-9.0, -4.8, 1.1), LEAF, grad=(0.0, 0.8))
	return p.build()


# ---- Vayuketh's Step

STAIR_RUN, STAIR_RISE = 13.0, 8.0


def _stair_h(y):
	"""The terrace slope under the summit stair: height at y meters up the climb."""
	t = min(max(y / STAIR_RUN, 0.0), 1.0)
	return STAIR_RISE * (3 * t * t - 2 * t ** 3)


def _stair_y(h):
	lo, hi = 0.0, STAIR_RUN
	for _ in range(50):
		mid = (lo + hi) / 2
		if _stair_h(mid) < h:
			lo = mid
		else:
			hi = mid
	return (lo + hi) / 2


def _ear_sail(p, d, root, side, S, yaw, swatch=BRONZE, inner=SKY, glow=0.0):
	"""An elephant-ear sail of Vayuketh: a bronze fan plate with a sky blue sail
	inside and battens, its root at `root`, spreading to one side (x * side),
	S times the shrine statue's ear, turned `yaw` degrees."""
	ear = [(0.0, 0.7), (1.0, 1.4), (2.2, 1.55), (3.1, 1.0), (3.4, 0.0), (3.0, -1.1), (2.3, -2.3), (1.4, -1.9), (0.3, -0.8)]
	inner_o = [(0.35 + x * 0.82, z * 0.82) for x, z in ear]
	M = Matrix.Translation(root) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Diagonal((S, S, S, 1))
	o = _plate(p, [(side * x, z) for x, z in ear], 0.0, 0.1, swatch, grad=(0.05, 0.8))
	o.data.transform(M)
	o = _plate(d, [(side * x, z) for x, z in inner_o], -0.07, 0.03, inner, grad=(0.05, 0.6), glow=glow)
	o.data.transform(M)
	for x, z in ((2.9, 1.0), (3.1, -0.1), (2.7, -1.3), (1.9, 1.3)):
		o = d.seg((side * 0.4, -0.1, 0.05), (side * x * 0.84, -0.1, z * 0.84), 0.035, 0.025, GOLD, sides=4)
		o.data.transform(M)


def summit_stair():
	"""The grand stair of Vayuketh's Step, built to lie exactly on one terrace
	slope. Origin at its bottom center on the ground; it climbs +Y in Blender
	(-Z, north, in Godot) 8 m over a 13 m run, the terrain's own curve
	h = 8 (3t^2 - 2t^3), t = run / 13. 27 steps of equal rise (0.286 m) each
	sit where the curve passes their height, so no tread is more than 0.143 m
	off the ground (the treads are long at the foot and head, short in the
	middle); each block runs 1.3 m below the curve. A flat landing at the foot
	(y -1..1, h 0) and the head (y 12.2..14.5, h 8). 7 m wide (x -3.5..3.5),
	balustrades along both sides on the step ends, and at the foot two short
	pillars with bronze ear-sails and wind chimes. Collide it as none (the
	terrain is the floor)."""
	p = Prop("summit_stair", 780)
	d = Prop("summit_stair_detail", 781)
	N = 28
	r = STAIR_RISE / N
	HW = 3.5
	fronts = [-1.0] + [_stair_y((k - 0.5) * r) for k in range(1, N + 1)]
	for k in range(N):                                                    # 0 = the foot landing, then the steps; N = the head landing
		y0, y1 = fronts[k], fronts[k + 1]
		top = k * r
		bottom = _stair_h(max(y0, 0.0)) - 1.3
		back = y1 + 0.3
		sw = (STONE_WARM, STONE_LIGHT)[k % 2]
		p.box((2 * HW, back - y0, top - bottom), (0, (y0 + back) / 2, (top + bottom) / 2), sw, grad=(0.0, 0.8))
	y0 = fronts[N]
	p.box((2 * HW, 14.5 - y0, 1.3 + r / 2), (0, (14.5 + y0) / 2, STAIR_RISE - (1.3 + r / 2) / 2), STONE_WARM, grad=(0.0, 0.8))
	# an ochre runner of inlaid stone up the middle of the head landing
	p.box((1.6, 14.5 - y0 - 0.6, 0.02), (0, (14.5 + y0) / 2, STAIR_RISE + 0.005), OCHRE, grad=(0.2, 0.6))
	# balustrades on the step ends, following the slope
	ys = [-1.0 + 15.5 * i / 40 for i in range(41)]
	for s in (-1, 1):
		x0, x1 = s * (HW - 0.5), s * HW
		for a, b in zip(ys, ys[1:]):
			ta, tb = _stair_h(a) + 0.9, _stair_h(b) + 0.9
			ba, bb = _stair_h(a) - 1.2, _stair_h(b) - 1.2
			p.poly([(x0, a, ba), (x1, a, ba), (x1, b, bb), (x0, b, bb), (x0, a, ta), (x1, a, ta), (x1, b, tb), (x0, b, tb)],
				   [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], MOOR_STONE, grad=(0.05, 0.9))
			cx0, cx1 = x0 - s * 0.08, x1 + s * 0.08
			p.poly([(cx0, a, ta - 0.02), (cx1, a, ta - 0.02), (cx1, b, tb - 0.02), (cx0, b, tb - 0.02), (cx0, a, ta + 0.14), (cx1, a, ta + 0.14), (cx1, b, tb + 0.14), (cx0, b, tb + 0.14)],
				   [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], STONE_LIGHT, grad=(0.0, 0.6))
		for y in (2.5, 5.2, 7.8, 10.4, 13.2):                             # posts along the rail
			h = _stair_h(y)
			p.box((0.7, 0.7, 1.6), (s * (HW - 0.25), y, h + 0.35), MOOR_STONE, grad=(0.05, 0.9))
			p.box((0.82, 0.82, 0.14), (s * (HW - 0.25), y, h + 1.2), STONE_LIGHT, grad=(0.0, 0.6))
			d.blob((0.3, 0.3, 0.34), (s * (HW - 0.25), y, h + 1.42), BRONZE, segs=(8, 5), grad=(0.0, 0.6))
		# the pillars at the foot: bronze ear-sails and chimes
		px = s * (HW - 0.3)
		p.box((1.0, 1.0, 0.3), (px, -0.55, 0.05), STONE_DARK, grad=(0.2, 0.9))
		p.box((0.8, 0.8, 2.3), (px, -0.55, 1.25), MOOR_STONE, grad=(0.05, 0.9))
		p.box((0.95, 0.95, 0.18), (px, -0.55, 2.45), STONE_LIGHT, grad=(0.0, 0.6))
		p.box((0.84, 0.05, 0.12), (px, -0.97, 1.9), OCHRE, grad=(0.1, 0.6))
		d.seg((px, -0.55, 2.54), (px, -0.55, 2.9), 0.22, 0.16, BRONZE, sides=8, grad=(0.0, 0.6))
		d.blob((0.34, 0.34, 0.34), (px, -0.55, 3.05), BRONZE, segs=(8, 6), grad=(0.0, 0.6))
		for side in (-1, 1):
			_ear_sail(p, d, (px + side * 0.12, -0.55, 3.0), side, 0.26, 0)
		d.seg((px, -0.55, 2.3), (px - s * 0.0, -1.35, 2.3), 0.04, 0.04, BRONZE, sides=5)   # chime bracket, out the front
		_chime_cluster(d, (px, -1.3, 2.28), r=0.14, n=6, length=(0.25, 0.45), swatch=GOLD)
	for s in (-1, 1):                                                     # small posts at the head
		px = s * (HW - 0.3)
		p.box((0.7, 0.7, 1.4), (px, 14.1, STAIR_RISE + 0.7), MOOR_STONE, grad=(0.05, 0.9))
		d.blob((0.34, 0.34, 0.4), (px, 14.1, STAIR_RISE + 1.6), BRONZE, segs=(8, 6), grad=(0.0, 0.6))
	return join_into(p.build(bevel=0.06), [d.build()])


def vayuketh_temple():
	"""Vayuketh's open-air summit temple, 26 m across: an octagonal stone
	platform (flat top 1.2 m up, apothem 12 m) with a ramp 6 m wide up its south
	face (-Y in Blender, +Z in Godot), a ring of eleven pillars 7 m tall (two
	snapped, one cracked, drums fallen on the paving), prayer flags strung
	between them, a stepped altar in the middle with a cold sky-stone, and
	behind it two great bronze ear-sails (about 8 m across, to 12 m up) on
	masts beside a wind-disc stele. Four lit braziers. Collide it as a mesh."""
	p = Prop("vayuketh_temple", 782)
	d = Prop("vayuketh_temple_detail", 783)
	rng = p.rng
	PT = 1.2
	c8 = math.cos(math.pi / 8)
	p.seg((0, 0, -0.8), (0, 0, 0.45), 12.6 / c8, 12.6 / c8, STONE_DARK, sides=8, grad=(0.2, 1.0), twist=22.5)
	p.seg((0, 0, 0.4), (0, 0, PT - 0.14), 12.0 / c8, 12.0 / c8, MOOR_STONE, sides=8, grad=(0.1, 0.9), twist=22.5)
	p.seg((0, 0, PT - 0.16), (0, 0, PT), 12.1 / c8, 12.1 / c8, STONE_LIGHT, sides=8, grad=(0.0, 0.6), twist=22.5)
	# the floor's inlaid rings round the altar
	p.seg((0, 0, PT - 0.05), (0, 0, PT + 0.008), 6.2, 6.2, OCHRE, sides=32, grad=(0.2, 0.6))
	p.seg((0, 0, PT - 0.05), (0, 0, PT + 0.012), 5.9, 5.9, STONE_WARM, sides=32, grad=(0.0, 0.5))
	p.seg((0, 0, PT - 0.05), (0, 0, PT + 0.016), 3.4, 3.4, SKY, sides=32, grad=(0.3, 0.7))
	p.seg((0, 0, PT - 0.05), (0, 0, PT + 0.02), 3.1, 3.1, STONE_LIGHT, sides=32, grad=(0.0, 0.5))
	# the ramp up the south face
	_ramp(p, -3.0, 3.0, -16.8, -11.7, 0.0, PT, 9, swatches=(STONE_LIGHT, STONE_WARM))
	for s in (-1, 1):
		p.poly([(s * 3.0, -16.8, -0.3), (s * 3.6, -16.8, -0.3), (s * 3.6, -11.7, -0.3), (s * 3.0, -11.7, -0.3),
				(s * 3.0, -16.8, 0.35), (s * 3.6, -16.8, 0.35), (s * 3.6, -11.7, PT + 0.5), (s * 3.0, -11.7, PT + 0.5)],
			   [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], MOOR_STONE, grad=(0.05, 0.9))
	# the pillars: 11 round the ring, a gap for the ramp
	angles = [-75 + 30 * k for k in range(12)]
	tops = []
	for k, deg in enumerate(angles):
		a = math.radians(deg)
		x, y = math.cos(a) * 10.2, math.sin(a) * 10.2
		p.box((1.5, 1.5, 0.5), (x, y, PT + 0.25), STONE_LIGHT, rot=(0, 0, deg), grad=(0.0, 0.7))
		if k in (3, 8):                                                   # snapped
			h = 2.6 + 0.8 * (k == 8)
			p.seg((x, y, PT + 0.5), (x, y, PT + h), 0.6, 0.57, MOOR_STONE, sides=10, grad=(0.05, 0.9))
			for j in range(4):
				b = j * math.tau / 4 + rng.uniform(0, 0.8)
				p.seg((x + math.cos(b) * 0.25, y + math.sin(b) * 0.25, PT + h - 0.1), (x + math.cos(b) * 0.3, y + math.sin(b) * 0.3, PT + h + rng.uniform(0.3, 0.7)), 0.3, 0.04, MOOR_STONE, sides=4)
			for j in range(2):                                            # its drums on the paving
				dx, dy = -math.cos(a) * (1.6 + j * 1.3), -math.sin(a) * (1.6 + j * 1.3)
				b = a + math.pi / 2 + rng.uniform(-0.4, 0.4)
				c = (x + dx, y + dy, PT + 0.55)
				p.seg((c[0] - math.cos(b) * 0.5, c[1] - math.sin(b) * 0.5, c[2]), (c[0] + math.cos(b) * 0.5, c[1] + math.sin(b) * 0.5, c[2]), 0.56, 0.56, MOOR_STONE, sides=10, grad=(0.05, 0.9))
			tops.append(None)
			continue
		p.seg((x, y, PT + 0.5), (x, y, PT + 6.4), 0.6, 0.54, MOOR_STONE, sides=10, grad=(0.05, 0.9))
		p.seg((x, y, PT + 6.4), (x, y, PT + 6.7), 0.56, 0.8, BRONZE, sides=10, grad=(0.0, 0.6))
		p.box((1.7, 1.7, 0.4), (x, y, PT + 6.9), STONE_LIGHT, rot=(0, 0, deg), grad=(0.0, 0.6))
		d.blob((0.3, 0.3, 0.36), (x, y, PT + 7.25), BRONZE, segs=(8, 5), grad=(0.0, 0.6))
		if k == 5:                                                        # a crack down this one
			_chain(d, [(x - math.cos(a) * 0.58, y - math.sin(a) * 0.58, PT + 6.2), (x - math.cos(a + 0.2) * 0.57, y - math.sin(a + 0.2) * 0.57, PT + 4.8),
					   (x - math.cos(a - 0.1) * 0.58, y - math.sin(a - 0.1) * 0.58, PT + 3.2), (x - math.cos(a + 0.15) * 0.6, y - math.sin(a + 0.15) * 0.6, PT + 1.4)], 0.05, 0.03, IRON, sides=4)
		tops.append((x, y, PT + 6.5))
	for k in range(12):                                                   # prayer flags between standing neighbors
		a, b = tops[k], tops[(k + 1) % 12]
		if a and b and not (angles[k] == 255):
			_flag_line(d, a, b, 1.0, spacing=0.55, size=(0.36, 0.44), start=k)
	# cracks across the paving
	for k in range(5):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(4.0, 7.0)
		pts = [(math.cos(a) * r, math.sin(a) * r, PT + 0.005)]
		for j in range(4):
			a += rng.uniform(-0.2, 0.2)
			r += rng.uniform(0.8, 1.2)
			pts.append((math.cos(a) * r, math.sin(a) * r, PT + 0.005))
		_chain(d, pts, 0.05, 0.02, IRON, sides=4, grad=(0.5, 1.0))
	# snow gathered at the platform's edge (it is cold up here now)
	for deg in (30, 85, 140, 195, 320):
		a = math.radians(deg)
		_snowcap(d, (1.6, 1.0, 0.12), (math.cos(a) * 11.3, math.sin(a) * 11.3, PT), rot=(0, 0, math.degrees(a)))
	# the altar
	p.box((3.6, 2.6, 0.3), (0, 0, PT + 0.15), STONE_LIGHT, grad=(0.0, 0.7))
	p.box((2.6, 1.7, 1.0), (0, 0, PT + 0.8), MOOR_STONE, grad=(0.05, 0.9))
	p.box((3.0, 2.1, 0.22), (0, 0, PT + 1.41), STONE_LIGHT, grad=(0.0, 0.6))
	p.box((3.04, 0.05, 0.14), (0, -1.07, PT + 1.2), OCHRE, grad=(0.1, 0.6))
	d.box((1.0, 2.24, 0.03), (0, 0, PT + 1.53), OCHRE, grad=(0.1, 0.6))      # an altar cloth
	d.box((1.0, 0.03, 0.5), (0, -1.12, PT + 1.3), OCHRE, grad=(0.1, 0.6))
	d.blob((0.7, 0.7, 0.85), (0, 0.2, PT + 1.95), SKY, segs=(10, 7), grad=(0.3, 0.9), glow=0.25)   # the cold sky-stone
	d.seg((0, 0.2, PT + 1.52), (0, 0.2, PT + 1.65), 0.5, 0.42, BRONZE, sides=10, grad=(0.0, 0.6))
	for x in (-1.1, 1.1):
		_candle(d, (x, -0.6, PT + 1.52), h=0.12)
	# the ear-sails on their masts and the wind-disc stele between them
	for s in (-1, 1):
		mx = s * 2.0
		p.box((1.1, 1.1, 0.6), (mx, 5.5, PT + 0.3), STONE_LIGHT, grad=(0.0, 0.7))
		p.seg((mx, 5.5, PT + 0.6), (mx, 5.5, PT + 10.8), 0.24, 0.18, BRONZE, sides=8, grad=(0.0, 0.8))
		d.blob((0.4, 0.4, 0.4), (mx, 5.5, PT + 10.95), GOLD, segs=(8, 6), grad=(0.0, 0.5))
		_ear_sail(p, d, (mx + s * 0.2, 5.4, PT + 7.4), s, 2.1, -s * 12, glow=0.15)
		_streamer(d, (mx, 5.5, PT + 10.7), 3.0, 0.4, (SKY, CLOTH_WHITE)[s > 0], droop=0.5)
	p.box((1.4, 0.6, 5.5), (0, 6.0, PT + 2.75), MOOR_STONE, grad=(0.05, 0.9))
	p.box((1.7, 0.8, 0.3), (0, 6.0, PT + 5.6), STONE_LIGHT, grad=(0.0, 0.6))
	d.seg((0, 5.66, PT + 4.2), (0, 5.6, PT + 4.2), 0.62, 0.62, BRONZE, sides=16, grad=(0.0, 0.6))
	d.seg((0, 5.6, PT + 4.2), (0, 5.55, PT + 4.2), 0.42, 0.42, SKY, sides=16, grad=(0.0, 0.5), glow=0.2)
	for j in range(8):
		b = j * math.tau / 8
		d.seg((math.cos(b) * 0.66, 5.62, PT + 4.2 + math.sin(b) * 0.66), (math.cos(b + 0.4) * 0.95, 5.62, PT + 4.2 + math.sin(b + 0.4) * 0.95), 0.05, 0.01, BRONZE, sides=4)
	# braziers: two by the altar, two at the head of the ramp
	for bx, by in ((-3.4, -1.5), (3.4, -1.5), (-4.9, -8.9), (4.9, -8.9)):
		start = len(d.parts)
		_brazier_stand(d, bx, by, 1.1, r=0.5)
		_move_parts(d, start, Matrix.Translation((0, 0, PT)))
	return join_into(p.build(bevel=0.06), [d.build()])


def guardian_statue():
	"""A stone temple guardian of Vayuketh on a plinth, about 4.4 m: a robed
	figure in a winged helm, both hands on a tall glaive standing at its right
	side, a short mantle, moss in the folds. Faces -Y. Collide it as a box."""
	p = Prop("guardian_statue", 784)
	d = Prop("guardian_statue_detail", 785)
	S = STONE_LIGHT
	p.box((1.6, 1.6, 0.25), (0, 0, 0.05), STONE_DARK, grad=(0.2, 0.9))
	p.box((1.3, 1.3, 0.75), (0, 0, 0.55), MOOR_STONE, grad=(0.05, 0.9))
	p.box((1.45, 1.45, 0.14), (0, 0, 0.98), STONE_LIGHT, grad=(0.0, 0.6))
	p.box((1.34, 0.04, 0.1), (0, -0.66, 0.8), OCHRE, grad=(0.1, 0.6))
	B = 1.05
	p.seg((0, 0, B), (0, 0, B + 1.25), 0.55, 0.36, S, sides=10, grad=(0.05, 0.85))       # robe
	p.blob((0.78, 0.6, 0.9), (0, 0, B + 1.45), S, segs=(10, 6), grad=(0.05, 0.8))      # chest
	p.blob((1.0, 0.55, 0.36), (0, 0.02, B + 1.78), S, segs=(10, 5), grad=(0.05, 0.7))   # shoulders
	p.seg((0, 0.12, B + 1.85), (0, 0.3, B + 0.3), 0.5, 0.62, MOOR_STONE, sides=8, grad=(0.1, 0.9))   # the mantle behind
	p.seg((0, 0, B + 1.8), (0, 0, B + 1.95), 0.13, 0.13, S, sides=6)
	p.blob((0.34, 0.36, 0.4), (0, -0.02, B + 2.12), S, segs=(8, 6), grad=(0.05, 0.7))  # head
	p.seg((0, 0, B + 2.1), (0, 0, B + 2.42), 0.22, 0.05, MOOR_STONE, sides=8, grad=(0.05, 0.8))    # helm
	p.blob((0.4, 0.42, 0.26), (0, 0, B + 2.2), MOOR_STONE, segs=(8, 5), grad=(0.05, 0.8))
	p.box((0.3, 0.06, 0.08), (0, -0.2, B + 2.12), IRON, grad=(0.6, 1.0))                # the visor slit
	for s in (-1, 1):                                                     # helm wings, swept back and up
		wing = [(0.0, 0.0), (0.2, 0.18), (0.42, 0.42), (0.55, 0.66), (0.4, 0.5), (0.28, 0.2), (0.08, -0.08)]
		o = _plate(p, [(s * x, z) for x, z in wing], 0.0, 0.05, S, grad=(0.0, 0.7))
		o.data.transform(Matrix.Translation((s * 0.18, 0.05, B + 2.2)) @ Matrix.Rotation(math.radians(s * 70), 4, "Z"))
	# arms, both hands on the glaive at the right side
	gx, gy = 0.55, -0.32
	for sh, hand in (((0.42, 0.0, B + 1.72), (gx, gy, B + 1.35)), ((-0.42, 0.0, B + 1.72), (gx - 0.08, gy, B + 1.7))):
		mid = ((sh[0] + hand[0]) / 2 + (0.1 if sh[0] > 0 else -0.05), (sh[1] + hand[1]) / 2, (sh[2] + hand[2]) / 2 - 0.15)
		_chain(p, [sh, mid, hand], 0.15, 0.11, S, sides=6, grad=(0.05, 0.8))
		p.blob((0.2, 0.2, 0.2), hand, S, segs=(6, 4))
	p.seg((gx, gy, B - 0.05), (gx, gy, B + 2.75), 0.055, 0.05, MOOR_STONE, sides=6, grad=(0.1, 0.8))   # the glaive
	p.seg((gx, gy, B + 2.7), (gx, gy, B + 2.82), 0.09, 0.09, BRONZE, sides=6)
	blade = [(0.0, 0.0), (0.12, 0.2), (0.16, 0.55), (0.1, 0.85), (0.0, 1.05), (-0.04, 0.6), (-0.06, 0.18)]
	o = _plate(p, blade, 0.0, 0.05, S, grad=(0.0, 0.5))
	o.data.transform(Matrix.Translation((gx, gy, B + 2.8)))
	for k in range(3):                                                    # moss in the folds
		d.blob((0.3, 0.2, 0.15), (0.3 * (k - 1), -0.35, B + 0.2 + k * 0.1), MOSS, segs=(6, 4), grad=(0.1, 0.8))
	d.blob((0.5, 0.4, 0.1), (-0.4, 0.4, 1.05), MOSS, segs=(6, 3), grad=(0.1, 0.8))
	return join_into(p.build(bevel=0.03), [d.build()])


def titan_throne():
	"""A storm titan's throne, about 6.3 m tall and 6 m wide: a rough stepped
	dais of great blocks, a seat 2.6 m up between two massive armrests, a tall
	jagged back slab carved with a glowing blue lightning rune, scorch marks
	and a great broken chain draped over one arm. Faces -Y. Collide it as a mesh."""
	p = Prop("titan_throne", 786)
	d = Prop("titan_throne_detail", 787)
	rng = p.rng
	_block(p, (6.2, 5.0, 0.7), (0, 0.3, 0.2), STONE_DARK, rough=0.08)
	_block(p, (5.0, 3.8, 0.6), (0, 0.6, 0.8), MOOR_STONE, rough=0.08)
	_block(p, (3.4, 2.6, 1.6), (0, 0.8, 1.9), MOOR_STONE, rough=0.06)          # the seat
	_block(p, (3.2, 2.4, 0.2), (0, 0.75, 2.75), STONE_LIGHT, rough=0.03)
	for s in (-1, 1):
		_block(p, (1.1, 3.0, 2.2), (s * 2.2, 0.8, 2.1), STONE_DARK, rough=0.07)
		p.rock((1.5, 1.3, 1.2), (s * 2.2, -0.75, 3.1), MOOR_STONE)
	rings = [(0.9, 4.4, 1.2, 0, 2.5), (3.5, 4.0, 1.1, 0, 2.55), (5.2, 3.2, 1.0, 0.1, 2.6)]
	_hewn(p, rings, MOOR_STONE, tip=(0.5, 2.6, 6.4), jit=0.12)
	for x, z, h in ((-1.6, 5.2, 0.9), (1.5, 5.0, 0.6), (-0.8, 5.6, 0.7)):      # jagged crown
		p.seg((x, 2.55, z - 0.2), (x + rng.uniform(-0.2, 0.2), 2.55, z + h), 0.45, 0.05, MOOR_STONE, sides=4, jitter=0.05)
	bolt = [(-0.3, 5.0), (0.35, 4.3), (-0.2, 3.9), (0.4, 3.1), (0.0, 2.9)]      # the lightning rune on the back
	pts = [(x, 1.84, z) for x, z in bolt]
	_chain(d, pts, 0.09, 0.07, SKY, sides=4, grad=(0.0, 0.3), glow=1.6)
	for k, z in enumerate((4.1, 3.3)):
		_rune(d, (-1.3 + 2.6 * k, 1.84, z), 0.55, k + 3, glow=1.2)
	for x, z in ((-1.2, 5.3), (1.3, 3.6), (0.9, 4.9)):                   # scorch marks on the back
		d.blob((0.8, 0.05, 0.6), (x, 1.83, z), IRON, segs=(6, 4), rot=(0, rng.uniform(0, 90), 0), grad=(0.6, 1.0))
	for x, y, z in ((-2.4, -1.7, 0.55), (1.9, -1.8, 0.55), (-1.4, -1.25, 1.1), (2.6, 1.4, 0.55)):   # and on the dais
		d.blob((1.0, 0.8, 0.04), (x, y, z), IRON, segs=(6, 3), rot=(0, 0, rng.uniform(0, 90)), grad=(0.6, 1.0))
	for k in range(7):                                                    # the broken chain over the left arm
		t = k / 6
		c = (-2.2 - 0.2 * math.sin(t * math.pi), -0.5 + 1.8 * t, 3.3 - 2.9 * t * t)
		_torus(d, c, (0, 1, -t), (1, 0, 0) if k % 2 else (0, 0, 1), 0.2, 0.07, IRON, stretch=1.5)
	for k in range(6):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(3.6, 4.6)
		s = rng.uniform(0.5, 1.1)
		p.rock((s, s, s * 0.7), (math.cos(a) * r, math.sin(a) * r, 0.1), STONE_DARK)
	return join_into(p.build(), [d.build()])


def drake_ledge():
	"""A drake's ledge: a rock outcrop about 8 m across and 7.5 m tall with a
	broad ledge jutting out to the front (-Y) at 3.6 m holding a nest of
	charred sticks and three eggs, black scorch marks over the rock, charred
	bones and rubble at its foot. Collide it as a mesh."""
	p = Prop("drake_ledge", 788)
	rng = p.rng
	p.rock((7.8, 5.6, 3.2), (0, 0.8, 1.0), MOOR_STONE, grad=(0.05, 0.9))
	p.rock((5.2, 4.2, 3.6), (0.3, 1.2, 3.6), STONE_DARK)
	p.seg((0.4, 1.5, 4.8), (0.9, 1.8, 7.6), 1.6, 0.15, MOOR_STONE, sides=5, jitter=0.1, twist=15)
	p.seg((-1.6, 1.0, 4.2), (-2.3, 1.2, 6.2), 1.0, 0.1, STONE_DARK, sides=5, jitter=0.08)
	p.rock((5.4, 4.0, 1.0), (-0.2, -1.6, 3.4), STONE_DARK, rot=(0, -4, 8))      # the ledge
	p.rock((3.0, 2.2, 1.8), (-0.4, -1.0, 2.4), MOOR_STONE)
	_stick_ring(p, (-0.4, -2.0, 3.95), 1.2, 2, rng, swatches=(IRON, WOOD_GRAY, CHAR), r=0.06, length=(0.7, 1.2))
	p.blob((1.9, 1.9, 0.25), (-0.4, -2.0, 4.0), HIDE, segs=(8, 4), grad=(0.4, 0.9))
	for k, (x, y) in enumerate(((-0.75, -2.0), (-0.1, -1.8), (-0.4, -2.45))):
		p.blob((0.38, 0.38, 0.52), (x, y, 4.3), (STONE_WARM, EMBER, STONE_WARM)[k], segs=(8, 6), rot=(rng.uniform(-15, 15), rng.uniform(-15, 15), 0), grad=(0.1, 0.9))
	for x, y, z, s in ((-2.0, -2.2, 3.9, 1.0), (1.4, -2.0, 3.9, 0.8), (-1.5, -4.2, 0.03, 1.6), (1.2, -4.6, 0.03, 1.3), (0.0, -3.4, 0.03, 1.1)):   # scorch marks
		p.blob((s * 1.2, s, 0.05), (x, y, z), IRON, segs=(7, 3), rot=(0, 0, rng.uniform(0, 90)), grad=(0.6, 1.0))
	for k in range(6):
		a = rng.uniform(math.pi, math.tau)
		r = rng.uniform(3.8, 5.0)
		c = Vector((math.cos(a) * r, math.sin(a) * r, 0.06))
		t = rng.uniform(0, math.pi)
		p.seg(tuple(c - Vector((math.cos(t), math.sin(t), 0)) * 0.35), tuple(c + Vector((math.cos(t), math.sin(t), 0)) * 0.35), 0.05, 0.04, CHAR if k % 2 else BONE, sides=5)
	_skull(p, (2.8, -3.6, 0.0), 1.4, yaw=0.4, swatch=BONE)
	for k in range(6):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(4.2, 5.5)
		s = rng.uniform(0.5, 1.0)
		p.rock((s, s, s * 0.7), (math.cos(a) * r, math.sin(a) * r, 0.1), STONE_DARK)
	return p.build()



# ===== The Boneyard, part 1: Fogfall, The Ivory Field, The Unlit, Barrowhold

YS_STONE = STONE_DARK       # Ysmoor's gray stone
YS_PALE = STONE_LIGHT       # its paler dressed stone
WISP = TEAL                 # pale blue-green will-o-light (the top of the teal swatch)
IVORY = BONE                # bleached bone and ivory: white fading to beige
NIGHT_BARK = IRON           # the Unlit's black bark
NIGHT_LEAF = CLOTH_WHITE    # glowing leaves: white shading to pale blue
VIOLET = PETAL_PURPLE       # Timiraj's violet: lilac into deep purple
OBSIDIAN = IRON             # black glass (made glossy)
BLOOD_GLASS = CLOTH_RED     # the Morvaines' red-lit windows
NIGHT_STONE = {(1, 0): STONE_DARK, (0, 0): IRON, (5, 0): STONE_DARK, (4, 0): WOOD_GRAY}   # KayKit wall stone -> dark stone, trim -> near black, wood -> gray-brown


def _lancet(p, c, w, h, yaw=0.0, pane=BLOOD_GLASS, glow=1.5, frame=IRON, bars=True):
	"""A tall pointed (lancet) window standing on c = (x, y, z of its sill),
	w wide and h tall, its glowing pane in a dark frame, facing -Y turned by
	yaw degrees (90 faces +X). Stands proud of a wall face at c."""
	start = len(p.parts)
	r = w / 2
	out = [(-r, 0.0), (r, 0.0), (r, h - w * 0.7), (r * 0.6, h - w * 0.25), (0.0, h), (-r * 0.6, h - w * 0.25), (-r, h - w * 0.7)]
	sx, sz = (w + 0.26) / w, (h + 0.22) / h
	_plate(p, [(x * sx, z * sz - 0.1) for x, z in out], 0.0, 0.12, frame, grad=(0.1, 0.8))
	_plate(p, out, -0.07, 0.04, pane, grad=(0.25, 0.7), glow=glow)
	if bars:
		p.seg((0, -0.1, 0.04), (0, -0.1, h - 0.12), 0.028, 0.028, frame, sides=4)
		for t in (0.33, 0.62):
			p.seg((-r, -0.1, h * t), (r, -0.1, h * t), 0.025, 0.025, frame, sides=4)
	_move_parts(p, start, Matrix.Translation(c) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))


def _steep_roof(p, c, w, d, z0, h, slate=IRON, wall=STONE_DARK, ridge_x=False, over=0.45, finials=True):
	"""A steep gable roof over a w x d block centered at c whose walls top out
	at z0: a solid gable of `wall` stone and two slate planes overhanging by
	`over`, a ridge cap with iron spikes at its ends. Ridge along Y (w across X),
	or along X when ridge_x (then w is still the span across the ridge)."""
	start = len(p.parts)
	hw = w / 2
	verts = [(-hw, -d / 2, z0), (hw, -d / 2, z0), (hw, d / 2, z0), (-hw, d / 2, z0), (0, -d / 2, z0 + h), (0, d / 2, z0 + h)]
	p.poly(verts, [(0, 3, 2, 1), (0, 1, 4), (2, 3, 5), (1, 2, 5, 4), (3, 0, 4, 5)], wall, grad=(0.1, 0.9))
	ang = math.atan2(h, hw)
	L = math.hypot(hw + over, h + over * h / hw)
	for s in (-1, 1):
		top = Vector((0, 0, z0 + h))
		eave = Vector((s * (hw + over), 0, z0 - over * h / hw))
		mid = (top + eave) / 2 + Vector((s * math.sin(ang), 0, math.cos(ang))) * 0.14
		p.box((L, d + 2 * over, 0.24), tuple(mid), slate, rot=(0, math.degrees(ang) * s, 0), grad=(0.0, 0.9))
	p.seg((0, -d / 2 - over, z0 + h + 0.2), (0, d / 2 + over, z0 + h + 0.2), 0.15, 0.15, slate, sides=6, grad=(0.0, 0.6))
	if finials:
		for y in (-d / 2 - over + 0.1, d / 2 + over - 0.1):
			p.seg((0, y, z0 + h + 0.2), (0, y, z0 + h + 1.4), 0.07, 0.0, IRON, sides=4)
			p.blob((0.2, 0.2, 0.2), (0, y, z0 + h + 0.55), IRON, segs=(6, 4))
	m = Matrix.Translation((c[0], c[1], 0))
	if ridge_x:
		m = m @ Matrix.Rotation(math.pi / 2, 4, "Z")
	_move_parts(p, start, m)


def _broken_top(p, x, y, z, r, swatch, n=4, rise=(0.3, 0.9)):
	"""Jagged stumps on a snapped shaft or pier top at z."""
	for k in range(n):
		a = k * math.tau / n + p.rng.uniform(0, 0.8)
		p.seg((x + math.cos(a) * r * 0.35, y + math.sin(a) * r * 0.35, z - 0.1), (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z + p.rng.uniform(*rise)),
			  r * 0.55, 0.05, swatch, sides=4, grad=(0.1, 0.9))


def _claw_marks(p, c, yaw, h=0.7, n=3, r=0.03):
	"""Three (n) raking claw gouges on a face at c, facing -Y turned by yaw
	degrees: dark grooves slanting down."""
	a = math.radians(yaw)
	right = Vector((math.cos(a), math.sin(a), 0))
	out = Vector((math.sin(a), -math.cos(a), 0))
	c = Vector(c)
	for k in range(n):
		o = c + right * (k - (n - 1) / 2) * 0.13 + out * 0.01
		p.seg(tuple(o + right * 0.1 + Vector((0, 0, h / 2))), tuple(o - right * 0.1 - Vector((0, 0, h / 2))), r, r * 0.4, IRON, sides=4, grad=(0.6, 1.0))


def _wisp(p, c, s=0.18, glow=2.2):
	"""A floating will-o-light: a pale blue-green orb in a fainter halo."""
	p.blob((s, s, s), c, WISP, segs=(8, 6), grad=(0.0, 0.2), glow=glow)
	p.blob((s * 0.45, s * 0.45, s * 0.45), c, CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.2), glow=glow * 1.2)


def _moon_globe(p, c, r=0.28, glow=2.2):
	"""A pale moon-white glass globe in a silver collar and crown."""
	x, y, z = c
	p.seg((x, y, z - r - 0.08), (x, y, z - r * 0.7), r * 0.55, r * 0.7, SILVER, sides=10, grad=(0.0, 0.6))
	p.blob((r * 2, r * 2, r * 2), (x, y, z), CLOTH_WHITE, segs=(12, 8), grad=(0.0, 0.3), glow=glow)
	p.seg((x, y, z + r * 0.8), (x, y, z + r + 0.08), r * 0.5, r * 0.3, SILVER, sides=10, grad=(0.0, 0.6))
	p.seg((x, y, z + r + 0.08), (x, y, z + r + 0.3), 0.04, 0.0, SILVER, sides=5)


def _crescent(p, c, R, yaw=0.0, swatch=SILVER, t=0.06, glow=0.0):
	"""A thin crescent moon standing upright at c (its outer radius R), open to +X
	(turned by yaw degrees)."""
	pts = []
	for k in range(9):
		a = math.radians(-130 + 260 * k / 8)
		pts.append((-math.cos(a) * R, math.sin(a) * R))
	inner = []
	for k in range(9):
		a = math.radians(-110 + 220 * k / 8)
		inner.append((-math.cos(a) * R * 0.72 + R * 0.28, math.sin(a) * R * 0.78))
	start = len(p.parts)
	verts, faces = [], []
	for (x0, z0), (x1, z1) in zip(pts, inner):
		verts += [(x0, -t, z0), (x1, -t, z1), (x0, t, z0), (x1, t, z1)]
	for k in range(8):
		a, b = k * 4, (k + 1) * 4
		faces += [(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2), (a, a + 2, b + 2, b), (a + 1, b + 1, b + 3, a + 3)]
	faces += [(0, 1, 3, 2), (32, 34, 35, 33)]
	o = p.poly(verts, faces, swatch, grad=(0.0, 0.6))
	if glow:
		o.data.materials[0] = atlas_material(glow)
	_move_parts(p, start, Matrix.Translation(c) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))


# ---- Fogfall

def _ruin_run(p, axis, fixed, piers, thick, z0, arch_top, outside, rng, swatch=YS_STONE):
	"""A ruined wall along `axis` ("x" or "y") at `fixed`, from a to b: piers
	[(pos, height)] 1.6 m wide with tall window openings between them (a sill
	1.2 m high); where both piers stand past the window head a pointed arch and
	wall close the bay up to `arch_top`. Broken piers end in jagged stumps and
	drop stones on the `outside` (+1 or -1) of the wall."""
	def at(t, off=0.0):
		return (t, fixed + off) if axis == "x" else (fixed + off, t)

	def box(size_t, size_n, h, t, z):
		sx, sy = (size_t, size_n) if axis == "x" else (size_n, size_t)
		x, y = at(t)
		p.box((sx, sy, h), (x, y, z + h / 2), swatch, grad=(0.05, 0.9), jitter=0.02)
	pw = 1.6
	for pos, h in piers:
		box(pw, thick, h, pos, z0)
		x, y = at(pos)
		if h >= arch_top - 0.1:
			box(pw + 0.2, thick + 0.2, 0.3, pos, z0 + h)                           # coping
		else:
			_broken_top(p, x, y, z0 + h, pw * 0.8, swatch, n=3)
			for k in range(2):                                                  # its fallen stones below
				fx, fy = at(pos + rng.uniform(-1.2, 1.2), outside * (thick / 2 + rng.uniform(1.4, 2.6)))
				s = rng.uniform(0.5, 0.9)
				p.rock((s * 1.3, s, s * 0.8), (fx, fy, s * 0.2), swatch)
	for (pa, ha), (pb, hb) in zip(piers, piers[1:]):
		g0, g1 = pa + pw / 2, pb - pw / 2
		span = g1 - g0
		if span <= 0.2:
			continue
		sill = 1.2 if rng.random() > 0.25 else rng.uniform(0.4, 0.8)
		box(span + 0.02, thick * 0.9, sill, (g0 + g1) / 2, z0)
		if min(ha, hb) >= arch_top - 0.1:
			head = arch_top - 2.6                                               # the window head
			mid = (g0 + g1) / 2
			for s in (-1, 1):                                                   # a pointed arch of two long voussoirs
				xa, ya = at(mid + s * span / 2)
				xb, yb = at(mid)
				ra = Vector((xa, ya, z0 + head))
				rb = Vector((xb, yb, z0 + head + span * 0.55))
				c = (ra + rb) / 2
				L = (rb - ra).length
				ang = math.degrees(math.atan2(span * 0.55, span / 2))
				if axis == "x":
					p.box((L + 0.3, thick, 0.5), tuple(c), YS_PALE, rot=(0, -s * ang, 0), grad=(0.0, 0.7))
				else:
					p.box((thick, L + 0.3, 0.5), tuple(c), YS_PALE, rot=(s * ang, 0, 0), grad=(0.0, 0.7))
			for s in (-1, 1):                                                   # spandrels up to the wall top
				box(span / 2 * 0.62, thick, arch_top - head - span * 0.25, mid + s * span * 0.33, z0 + head + span * 0.25)
			box(span * 0.2, thick, arch_top - head - span * 0.55, mid, z0 + head + span * 0.55)
			box(span + pw, thick + 0.2, 0.3, mid, z0 + arch_top)


def ysmoor_throne_hall():
	"""The ruined throne hall of Ysmoor, roofless: a raised floor of gray stone
	24 x 18 m (top 1 m up, flagged in paler stone down the nave) climbed by a
	worn stair 10 m wide in the middle of the south side (-Y), half-fallen walls
	on the other three sides, their piers standing 3 to 9.5 m between tall
	pointed windows (some still arched over), two rows of columns (four whole,
	two snapped, their drums on the floor), a two-step dais at the north end
	(+Y) with a high-backed stone throne under a faded banner, moss, rubble and
	two will-o-lights hanging by the throne. Only stubs of the south wall
	remain. Collide it as a mesh: the floor is walkable."""
	p = Prop("ysmoor_throne_hall", 800)
	d = Prop("ysmoor_throne_hall_detail", 801)
	rng = p.rng
	F = 1.0
	p.box((24.0, 18.0, F + 0.5), (0, 0, (F - 0.5) / 2), YS_STONE, grad=(0.05, 0.9))
	p.box((24.3, 18.3, 0.35), (0, 0, -0.2), STONE_DARK, grad=(0.4, 1.0))               # the footing
	for i in range(5):                                                         # paler flags down the nave
		for j in range(8):
			if (i + j) % 2 or rng.random() < 0.15:
				continue
			d.box((1.9, 1.9, 0.03), (-4.0 + i * 2.0, -7.6 + j * 2.0, F + 0.004), YS_PALE, rot=(0, 0, rng.uniform(-2, 2)), grad=(0.45, 0.95))
	_ramp(p, -5.0, 5.0, -12.6, -9.0, 0.0, F, 5, swatches=(YS_PALE, YS_STONE))
	for s in (-1, 1):                                                          # the stair's cheeks
		p.box((1.0, 3.8, F + 0.6), (s * 5.5, -10.8, (F + 0.3 - 0.3) / 2), YS_STONE, grad=(0.05, 0.9))
		p.box((1.2, 4.0, 0.2), (s * 5.5, -10.8, F + 0.35), YS_PALE, grad=(0.0, 0.6))
	# the walls: back (+Y) and the two sides, 1.2 m thick, standing on the floor
	T = 1.2
	_ruin_run(p, "x", 8.4, [(-11.4, 9.5), (-7.0, 6.2), (-2.5, 9.5), (2.5, 9.5), (7.0, 9.5), (11.4, 4.8)], T, F, 9.5, 1, rng)
	_ruin_run(p, "y", -11.4, [(-8.2, 3.4), (-4.2, 5.5), (0.0, 9.5), (4.2, 9.5), (8.2, 9.5)], T, F, 9.5, -1, rng)
	_ruin_run(p, "y", 11.4, [(-8.2, 7.0), (-4.2, 2.6), (0.0, 4.4), (4.2, 9.5), (8.2, 4.8)], T, F, 9.5, 1, rng)
	for x, h in ((-8.2, 2.2), (-5.4, 1.2), (7.0, 3.2)):                          # stubs of the south wall
		p.box((1.6 if h > 1.5 else 3.4, T, h), (x, -8.4, F + h / 2), YS_STONE, grad=(0.05, 0.9), jitter=0.03)
		_broken_top(p, x, -8.4, F + h, 1.3, YS_STONE, n=3)
	# columns down the nave
	for k, (x, y, h) in enumerate(((-6.0, -5.0, 8.4), (6.0, -5.0, 3.1), (-6.0, -0.5, 8.4), (6.0, -0.5, 8.4), (-6.0, 4.0, 4.6), (6.0, 4.0, 8.4))):
		p.box((1.6, 1.6, 0.5), (x, y, F + 0.25), YS_PALE, grad=(0.0, 0.7))
		p.seg((x, y, F + 0.5), (x, y, F + 0.8), 0.72, 0.6, YS_PALE, sides=12, grad=(0.0, 0.6))
		p.seg((x, y, F + 0.8), (x, y, F + h), 0.55, 0.5, YS_STONE, sides=12, grad=(0.05, 0.9))
		if h > 8:
			p.seg((x, y, F + h), (x, y, F + h + 0.4), 0.52, 0.8, YS_PALE, sides=12, grad=(0.0, 0.6))
			p.box((1.8, 1.8, 0.35), (x, y, F + h + 0.55), YS_PALE, grad=(0.0, 0.6))
		else:
			_broken_top(p, x, y, F + h, 0.55, YS_STONE)
			for j in range(2):                                                 # its drums on the floor
				dx = -x / abs(x) * (1.6 + j * 1.3)
				b = rng.uniform(-0.5, 0.5)
				c = (x + dx, y + rng.uniform(-0.8, 0.8), F + 0.52)
				p.seg((c[0] - math.sin(b) * 0.55, c[1] - math.cos(b) * 0.55, c[2]), (c[0] + math.sin(b) * 0.55, c[1] + math.cos(b) * 0.55, c[2]), 0.52, 0.52, YS_STONE, sides=12, grad=(0.05, 0.9))
	# the dais and the throne
	p.box((9.0, 4.4, 0.35), (0, 6.0, F + 0.175), YS_PALE, grad=(0.0, 0.8))
	p.box((6.4, 3.0, 0.35), (0, 6.5, F + 0.525), YS_STONE, grad=(0.0, 0.8))
	D = F + 0.7
	p.box((2.0, 1.5, 0.7), (0, 6.9, D + 0.35), YS_PALE, grad=(0.0, 0.8))          # seat
	back = [(-1.0, 0.0), (1.0, 0.0), (1.0, 2.6), (0.55, 3.3), (0.0, 3.9), (-0.55, 3.3), (-1.0, 2.6)]
	o = _plate(p, back, 0.0, 0.45, YS_PALE, grad=(0.0, 0.8))
	o.data.transform(Matrix.Translation((0, 7.6, D + 0.6)))
	for s in (-1, 1):
		p.box((0.35, 1.5, 0.55), (s * 1.12, 6.9, D + 0.95), YS_STONE, grad=(0.0, 0.7))
		p.blob((0.4, 0.4, 0.4), (s * 1.12, 6.2, D + 1.25), YS_PALE, segs=(8, 5))
	d.box((1.6, 1.2, 0.08), (0, 6.85, D + 0.74), SEA_STONE, grad=(0.2, 0.8))       # a faded cushion
	d.blob((1.2, 0.5, 0.12), (0.4, 6.4, D + 0.76), MOSS, segs=(6, 3), grad=(0.1, 0.8))
	d.seg((-0.6, 6.2, D + 0.72), (-0.35, 6.25, D + 0.72), 0.2, 0.2, GOLD, sides=8, grad=(0.0, 0.6))   # a tarnished crown, dropped
	for k in range(5):
		a = k * math.tau / 5
		d.seg((-0.47 + math.cos(a) * 0.17, 6.22 + math.sin(a) * 0.17, D + 0.8), (-0.47 + math.cos(a) * 0.19, 6.22 + math.sin(a) * 0.19, D + 0.98), 0.04, 0.0, GOLD, sides=4)
	d.box((3.2, 0.1, 5.5), (0, 7.75 + 0.02, D + 5.4), SEA_STONE, grad=(0.1, 0.7))   # the faded banner on the back wall (standing on the wall's face)
	d.seg((-1.9, 7.7, D + 8.2), (1.9, 7.7, D + 8.2), 0.06, 0.06, IRON, sides=5)
	d.poly([(-1.6, 7.72, D + 2.65), (1.6, 7.72, D + 2.65), (0.0, 7.72, D + 1.9)], [(0, 1, 2)], SEA_STONE, grad=(0.3, 0.9))
	_crescent(d, (0, 7.66, D + 6.2), 0.8, yaw=90, swatch=YS_PALE)
	for x, y, z in ((-2.1, 6.0, D + 2.4), (2.3, 6.4, D + 2.9)):
		_wisp(d, (x, y, z), 0.22)
	# rubble on the floor and moss in the cracks
	for k in range(14):
		x, y = rng.uniform(-10.5, 10.5), rng.uniform(-8.0, 7.0)
		if abs(x) < 4.0 and y < 3.0:
			continue
		s = rng.uniform(0.35, 0.8)
		p.rock((s * 1.3, s, s * 0.7), (x, y, F + s * 0.15), YS_STONE if k % 2 else YS_PALE)
	for k in range(9):
		d.blob((rng.uniform(1.0, 2.2), rng.uniform(0.8, 1.6), 0.08), (rng.uniform(-10, 10), rng.uniform(-8, 7), F + 0.01), MOSS, segs=(7, 3), grad=(0.1, 0.9))
	for k in range(10):                                                        # stones fallen outside the walls
		a = rng.uniform(0, math.tau)
		x, y = math.cos(a) * rng.uniform(13.0, 15.0), math.sin(a) * rng.uniform(10.0, 11.5)
		if y < -9.0 and abs(x) < 7:
			continue
		s = rng.uniform(0.6, 1.3)
		p.rock((s * 1.4, s, s * 0.8), (x, y, 0.1), YS_STONE)
	return join_into(p.build(bevel=0.06), [d.build()])


def fog_ruin_tower():
	"""A ruined round tower of Ysmoor, 6.4 m across: a hollow shell of gray
	stone staves standing 14 m at the back, broken away to 9 to 11 m round the
	front in a jagged line, a stringcourse at 5 m, arrow slits, a doorway 2.4 m
	wide on the front (-Y) under a lintel, a dark inside, and fallen stones and
	a toppled merlon heaped at its foot. Collide it as a mesh."""
	p = Prop("fog_ruin_tower", 802)
	d = Prop("fog_ruin_tower_detail", 803)
	rng = p.rng
	R, n = 3.2, 18
	w = math.tau * R / n * 1.12
	for k in range(n):
		a = -math.pi / 2 + (k + 0.5) * math.tau / n
		back = math.sin(a)                                                     # -1 front, 1 back
		h = 11.0 + 3.0 * max(0.0, back) + rng.uniform(-0.8, 0.6) if back > -0.2 else 9.0 + rng.uniform(-0.6, 1.4)
		h = min(h, 14.0)
		x, y = math.cos(a) * R, math.sin(a) * R
		door = abs(k - (n - 1) / 2) > n / 2 - 1.1 or k in (0, n - 1)
		z0 = 2.9 if door else -0.3
		p.box((w, 0.8, h - z0), (x, y, z0 + (h - z0) / 2), YS_STONE, rot=(0, 0, math.degrees(a) + 90), grad=(0.02, 0.9), jitter=0.03)
		if h < 13.0:
			_broken_top(p, x, y, h, 0.8, YS_STONE, n=2, rise=(0.1, 0.5))
	p.seg((0, 0, -0.3), (0, 0, 0.35), R + 0.6, R + 0.55, STONE_DARK, sides=n, grad=(0.3, 1.0))           # plinth
	p.seg((0, 0, 5.0), (0, 0, 5.35), R + 0.55, R + 0.5, YS_PALE, sides=n, grad=(0.0, 0.6))              # stringcourse (a solid band ring)
	d.seg((0, 0, 0.36), (0, 0, 5.0), R - 0.35, R - 0.35, SHADE, sides=n, grad=(0.95, 1.0))              # the dark inside
	p.box((3.2, 1.0, 0.45), (0, -R, 3.1), YS_PALE, grad=(0.0, 0.6))                                     # lintel
	for s in (-1, 1):
		p.box((0.35, 1.0, 2.8), (s * 1.35, -R, 1.4), YS_PALE, grad=(0.0, 0.7))
	for k, (deg, z) in enumerate(((-30, 3.6), (40, 6.4), (150, 7.2), (215, 4.2), (95, 9.6), (-150, 8.8))):
		a = math.radians(deg)
		d.box((0.2, 0.12, 1.1), (math.cos(a) * (R + 0.41), math.sin(a) * (R + 0.41), z), SHADE, rot=(0, 0, deg + 90), grad=(0.95, 1.0))
	for k in range(12):
		a = rng.uniform(-0.6, 1.9)
		r = rng.uniform(R + 0.8, R + 4.0)
		s = rng.uniform(0.5, 1.2)
		p.rock((s * 1.4, s, s * 0.8), (math.cos(a) * r, math.sin(a) * r, 0.1), YS_STONE if k % 2 else YS_PALE)
	p.box((1.1, 0.8, 1.0), (4.6, 1.8, 0.35), YS_PALE, rot=(12, 30, 25), grad=(0.0, 0.8))               # a toppled merlon
	return join_into(p.build(bevel=0.05), [d.build()])


def fog_ruin_wall():
	"""A ruined castle wall of Ysmoor along X, 12 m long, 1.6 m thick and 5 m
	to the wall-walk: crenellated on the left, a round arch 3.2 m wide in the
	middle (its right half fallen, voussoirs lying in the passage's edge), the
	right end broken down to a jagged 3 m, rubble at its feet. Faces -Y.
	Collide it as a mesh (the arch is walkable)."""
	p = Prop("fog_ruin_wall", 804)
	d = Prop("fog_ruin_wall_detail", 805)
	rng = p.rng
	T, H = 1.6, 5.0
	p.box((4.4, T, H), (-3.8, 0, H / 2), YS_STONE, grad=(0.05, 0.9), jitter=0.02)       # the left block, whole
	for k in range(3):
		p.box((0.8, T + 0.1, 0.9), (-5.5 + k * 1.45, 0, H + 0.45), YS_PALE, grad=(0.0, 0.7))
	p.box((4.6, T + 0.2, 0.25), (-3.8, 0, H + 0.02), YS_PALE, grad=(0.0, 0.6))
	p.box((4.6, T, 3.2), (3.7, 0, 1.6), YS_STONE, grad=(0.05, 0.9), jitter=0.02)        # the right block, broken down
	for x, h in ((1.9, 1.3), (3.2, 0.7), (4.6, 0.4), (5.7, 0.0)):
		p.box((1.2, T, h + 0.3), (x, 0, 3.2 + (h + 0.3) / 2 - 0.3), YS_STONE, rot=(0, rng.uniform(-6, 6), 0), grad=(0.05, 0.9), jitter=0.04)
	# the arch over the middle: jambs, then voussoirs from the left springing
	hw, zc = 1.6, 2.4
	for s in (-1, 1):
		p.box((0.5, T + 0.1, zc), (s * (hw + 0.25), 0, zc / 2), YS_PALE, grad=(0.0, 0.7))
	nv = 9
	for k in range(6):
		a0, a1 = math.pi - math.pi * k / nv, math.pi - math.pi * (k + 1) / nv
		pts = [(math.cos(a0) * hw, math.sin(a0) * hw), (math.cos(a0) * (hw + 0.6), math.sin(a0) * (hw + 0.6)),
			   (math.cos(a1) * (hw + 0.6), math.sin(a1) * (hw + 0.6)), (math.cos(a1) * hw, math.sin(a1) * hw)]
		verts = [(x, -T / 2 - 0.05, zc + z) for x, z in pts] + [(x, T / 2 + 0.05, zc + z) for x, z in pts]
		p.poly(verts, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], YS_PALE if k % 2 else YS_STONE, grad=(0.05, 0.8))
	p.box((1.0, T, H - zc - 0.4), (-hw - 0.1, 0, zc + 0.4 + (H - zc - 0.4) / 2), YS_STONE, grad=(0.05, 0.9))   # fill over the left haunch
	for k in range(3):                                                          # fallen voussoirs
		p.box((0.9, 0.7, 0.55), (hw + 0.9 + k * 0.4, -1.6 - k * 0.5, 0.25), YS_PALE, rot=(rng.uniform(-15, 15), rng.uniform(-15, 15), rng.uniform(0, 90)), grad=(0.05, 0.8))
	for k in range(9):
		x = rng.uniform(1.5, 6.5)
		s = rng.uniform(0.4, 0.9)
		p.rock((s * 1.3, s, s * 0.8), (x, rng.choice((-1, 1)) * rng.uniform(1.2, 2.6), 0.1), YS_STONE)
	d.box((0.18, 0.1, 0.9), (-4.4, -T / 2 - 0.03, 3.4), SHADE, grad=(0.95, 1.0))        # an arrow slit
	return join_into(p.build(bevel=0.05), [d.build()])


def gargoyle_perch():
	"""A gargoyle's empty perch: a square stone pillar about 5.3 m tall on a
	stepped base, its cap a plinth with the stumps of two stone feet (the
	gargoyle is gone), three sets of claw gouges down its faces, cracks and
	moss. Collide it as a box."""
	p = Prop("gargoyle_perch", 806)
	d = Prop("gargoyle_perch_detail", 807)
	p.box((1.8, 1.8, 0.4), (0, 0, 0.1), STONE_DARK, grad=(0.3, 1.0))
	p.box((1.4, 1.4, 0.35), (0, 0, 0.47), YS_PALE, grad=(0.0, 0.7))
	p.box((1.0, 1.0, 3.9), (0, 0, 2.6), YS_STONE, grad=(0.05, 0.9), jitter=0.02)
	p.box((1.3, 1.3, 0.3), (0, 0, 4.65), YS_PALE, grad=(0.0, 0.7))
	p.box((1.1, 1.1, 0.45), (0, 0, 5.0), YS_STONE, grad=(0.05, 0.8))
	for s in (-1, 1):                                                          # the feet it left behind
		p.blob((0.3, 0.42, 0.22), (s * 0.24, -0.1, 5.3), YS_STONE, segs=(6, 4))
		for k in range(3):
			p.seg((s * 0.24 + (k - 1) * 0.09, -0.25, 5.3), (s * 0.24 + (k - 1) * 0.11, -0.52, 5.22), 0.04, 0.0, YS_STONE, sides=4)
		p.seg((s * 0.24, -0.05, 5.35), (s * 0.24 + 0.05, 0.0, 5.62), 0.13, 0.08, YS_STONE, sides=5)
	_claw_marks(d, (0.0, -0.52, 3.2), 0, h=0.8)
	_claw_marks(d, (0.52, 0.1, 2.2), 90, h=0.6)
	_claw_marks(d, (-0.1, 0.52, 3.9), 180, h=0.5)
	_crack(d, [(-0.3, -0.51, 4.4), (-0.2, -0.51, 3.8), (-0.35, -0.51, 3.3)], r=0.02, glow=0.0)
	d.blob((0.9, 0.9, 0.12), (0.1, 0.1, 5.22), MOSS, segs=(6, 3), grad=(0.1, 0.8))
	d.blob((0.2, 0.9, 1.0), (-0.5, 0.1, 1.2), MOSS, segs=(5, 4), grad=(0.1, 0.8))
	return join_into(p.build(bevel=0.05), [d.build()])


def kennel_ruin():
	"""The ruined royal kennels of Ysmoor, about 14 x 9 m: a low stone wall
	1.3 m high round a yard (broken open in places, a gateway on the front,
	-Y), a row of four pens along the back under the stumps of their posts,
	divided by low walls with rusted iron bars, a collapsed roof beam lying
	across them, water bowls, a gnawed bone or two and a toppled trough.
	Collide it as a mesh."""
	p = Prop("kennel_ruin", 808)
	d = Prop("kennel_ruin_detail", 809)
	rng = p.rng
	W, D, H, T = 14.0, 9.0, 1.3, 0.6
	x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
	# outer walls in runs, gaps where they have fallen
	runs = [((x0, y0), (-1.4, y0)), ((1.4, y0), (4.5, y0)), ((6.0, y0), (x1, y0)),
			((x1, y0), (x1, 0.5)), ((x1, 2.0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, -1.0))]
	for (ax, ay), (bx, by) in runs:
		L = math.hypot(bx - ax, by - ay)
		yaw = math.degrees(math.atan2(by - ay, bx - ax))
		h = H * rng.uniform(0.75, 1.05)
		p.box((L + T, T, h), ((ax + bx) / 2, (ay + by) / 2, h / 2), YS_STONE, rot=(0, 0, yaw), grad=(0.05, 0.9), jitter=0.03)
		p.box((L + T + 0.1, T + 0.12, 0.14), ((ax + bx) / 2, (ay + by) / 2, h + 0.07), YS_PALE, rot=(0, 0, yaw), grad=(0.0, 0.6))
	for x in (-1.4, 1.4):                                                        # gateposts
		p.box((0.8, 0.8, 2.1), (x, y0, 1.05), YS_PALE, grad=(0.0, 0.8))
		p.blob((0.55, 0.55, 0.5), (x, y0, 2.3), YS_STONE, segs=(8, 5))
	d.box((1.4, 0.08, 1.6), (-0.9, y0 + 0.9, 0.8), IRON, rot=(0, 0, 70), grad=(0.3, 1.0))   # a gate leaf hanging open
	# pens along the back: partitions and barred fronts
	PY = 1.5
	for k in range(5):
		x = x0 + 0.3 + k * (W - 0.6) / 4
		p.box((0.45, y1 - PY, 1.0), (x, (PY + y1) / 2, 0.5), YS_STONE, grad=(0.05, 0.9), jitter=0.02)
		p.seg((x, y1 - 0.2, 0.0), (x, y1 - 0.2, 2.2 + rng.uniform(-0.8, 0.4)), 0.14, 0.12, WOOD_GRAY, sides=5)   # roof post stumps
	for k in range(4):
		xa = x0 + 0.3 + k * (W - 0.6) / 4 + 0.3
		xb = xa + (W - 0.6) / 4 - 0.6
		p.box((xb - xa, 0.3, 0.35), ((xa + xb) / 2, PY, 0.175), YS_PALE, grad=(0.0, 0.7))
		for j in range(int((xb - xa) / 0.28)):
			if (k, j) in ((1, 3), (1, 4), (1, 5), (3, 1), (3, 2)):
				continue                                                          # bent out
			bx = xa + 0.14 + j * 0.28
			d.seg((bx, PY, 0.35), (bx + rng.uniform(-0.05, 0.05), PY + rng.uniform(-0.05, 0.05), 1.35), 0.025, 0.025, IRON, sides=4, grad=(0.3, 1.0))
		d.seg((xa, PY, 1.35), (xb, PY, 1.35), 0.03, 0.03, IRON, sides=4)
		bx, by = (xa + xb) / 2, (PY + y1) / 2
		d.seg((bx, by, 0.0), (bx, by, 0.12), 0.2, 0.26, IRON, sides=10, grad=(0.1, 0.8))   # a water bowl in each pen
		d.seg((bx, by, 0.1), (bx, by, 0.11), 0.18, 0.18, WATER if k % 2 else STONE_DARK, sides=10, grad=(0.4, 0.8))
		d.box((1.2, 0.6, 0.1), (bx - 0.3, by + 1.0, 0.05), WOOD_GRAY if k % 2 else HIDE, rot=(0, 0, rng.uniform(-20, 20)), grad=(0.3, 0.9))   # old straw / a rag
	for k in range(4):                                                         # bent bars lying out
		d.seg((x0 + 3.5 + k * 0.2, PY - 0.2, 0.05), (x0 + 3.9 + k * 0.3, PY - 1.1, 0.05), 0.025, 0.025, IRON, sides=4)
	# the fallen roof: a long beam from a post stump to the ground, planks under it
	_beam(p, (x0 + 0.8, y1 - 0.3, 1.4), (x1 - 1.4, PY - 0.8, 0.12), 0.14, swatch=WOOD_GRAY)
	for k in range(5):
		x = x0 + 2.0 + k * 2.1
		d.box((1.9, 0.3, 0.06), (x, y1 - 1.0 - k * 0.25, 1.0 - k * 0.15), WOOD_GRAY, rot=(rng.uniform(-10, 10), -8, rng.uniform(-25, 25)), grad=(0.2, 0.9))
	# a toppled stone trough, bones
	p.box((2.0, 0.7, 0.55), (3.6, -1.8, 0.28), YS_PALE, rot=(0, 0, 18), grad=(0.0, 0.8))
	d.box((1.7, 0.45, 0.05), (3.6, -1.8, 0.56), SHADE, rot=(0, 0, 18), grad=(0.9, 1.0))
	for a, b in (((-3.0, -2.0, 0.05), (-2.6, -2.3, 0.05)), ((0.8, 0.4, 0.05), (1.2, 0.1, 0.07)), ((-4.8, 3.1, 0.05), (-4.5, 3.4, 0.05))):
		_bone(d, a, b, r=0.03)
	_skull(d, (5.5, 3.2, 0.0), 1.0, yaw=0.8)
	for k in range(6):
		s = rng.uniform(0.4, 0.8)
		p.rock((s * 1.3, s, s * 0.7), (rng.uniform(x0 - 1.2, x1 + 1.2), rng.choice((y0 - 1.0, y1 + 1.0)) + rng.uniform(-0.3, 0.3), 0.1), YS_STONE)
	for k in range(5):
		d.blob((rng.uniform(0.8, 1.6), 0.7, 0.12), (rng.uniform(x0, x1), rng.uniform(y0, y1), 0.02), MOSS, segs=(6, 3), grad=(0.2, 0.9))
	return join_into(p.build(bevel=0.05), [d.build()])


def dig_pit():
	"""An opened grave, no more than 0.2 m deep: a dark hollow (2.2 x 1.1 m)
	ringed by a raised rim of turned earth, a heap of spoil beside it (+X)
	with a spade stuck in it, a broken coffin lid lying cracked in two, a
	short ladder dropped across the rim, a lantern gone cold. About 5 x 3.4 m.
	Collide it as none."""
	p = Prop("dig_pit", 810)
	rng = p.rng
	EARTH_ = WOOD_GRAY
	for k in range(16):                                                        # the rim of turned earth
		a = k * math.tau / 16
		p.blob((0.75, 0.55, 0.22), (math.cos(a) * 1.35, math.sin(a) * 0.78, 0.04), EARTH_, rot=(0, 0, math.degrees(a) + 90), segs=(6, 3), grad=(0.3, 1.0))
	p.blob((2.4, 1.3, 0.1), (0, 0, 0.0), SHADE, segs=(10, 4), grad=(0.85, 1.0))     # the dark hollow
	p.blob((1.9, 1.0, 0.36), (0, 0, -0.2), SHADE, segs=(10, 4), grad=(0.95, 1.0))
	p.blob((2.2, 1.7, 1.0), (2.2, 0.2, 0.05), EARTH_, segs=(9, 5), grad=(0.25, 1.0), jitter=0.05)   # spoil heap
	p.blob((1.2, 1.0, 0.6), (2.9, -0.5, 0.0), EARTH_, segs=(7, 4), grad=(0.25, 1.0), jitter=0.04)
	for k in range(5):
		p.rock((0.18, 0.15, 0.12), (1.9 + rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.9), 0.1), STONE_DARK)
	# the spade stuck in the heap
	p.seg((2.25, 0.2, 0.25), (2.1, 0.35, 1.35), 0.035, 0.03, WOOD, sides=5)
	p.seg((2.08, 0.3, 1.35), (2.12, 0.4, 1.35), 0.11, 0.11, WOOD, sides=4)
	p.box((0.26, 0.04, 0.3), (2.26, 0.19, 0.3), IRON, rot=(0, -8, 0), grad=(0.0, 0.6))
	# the coffin lid, cracked in two, the halves lying flat and apart
	halves = (([(0.0, -0.95), (0.33, -0.55), (0.31, 0.05), (0.05, 0.12), (-0.3, 0.0), (-0.33, -0.55)], (-1.9, 0.9), 20),
			  ([(-0.3, 0.08), (0.02, 0.2), (0.31, 0.12), (0.28, 0.95), (-0.28, 0.95)], (-2.0, -0.2), -12))
	for outline, (ox, oy), yaw in halves:
		o = _plate(p, outline, 0.0, 0.07, WOOD_GRAY, grad=(0.2, 0.9))
		o.data.transform(Matrix.Translation((ox, oy, 0.06)) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(-90), 4, "X"))
	# the ladder across the rim
	for s in (-1, 1):
		p.seg((-0.4 + s * 0.22, -1.6, 0.06), (0.1 + s * 0.22, 0.6, 0.2), 0.035, 0.035, WOOD, sides=4)
	for k in range(6):
		t = (k + 0.5) / 6
		p.seg((-0.62 + 0.5 * t, -1.6 + 2.2 * t, 0.06 + 0.14 * t + 0.03), (-0.18 + 0.5 * t, -1.6 + 2.2 * t, 0.06 + 0.14 * t + 0.03), 0.025, 0.025, WOOD_GRAY, sides=4)
	# a cold lantern
	p.seg((-1.5, -1.0, 0.0), (-1.5, -1.0, 0.3), 0.1, 0.09, IRON, sides=6, grad=(0.1, 0.9))
	p.seg((-1.5, -1.0, 0.3), (-1.5, -1.0, 0.42), 0.1, 0.0, IRON, sides=6)
	return p.build(bevel=0.02)


def tombstone_cluster():
	"""A few old graves: four leaning round-topped tombstones on low mounds
	and a small stone cross, weathered and worn, one broken and lying on
	its back. About 3.6 x 2.6 m, 1.4 m tall. Collide it as a box."""
	p = Prop("tombstone_cluster", 812)
	d = Prop("tombstone_cluster_detail", 813)
	rng = p.rng
	for k, (x, y, h, tilt, yaw) in enumerate(((-1.2, 0.2, 1.1, 8, 5), (-0.1, 0.4, 1.25, -5, -3), (1.1, 0.1, 0.95, 12, 10))):
		start, dstart = len(p.parts), len(d.parts)
		sw = YS_PALE if k % 2 else YS_STONE
		p.box((0.62, 0.16, h - 0.3), (0, 0, (h - 0.3) / 2), sw, grad=(0.05, 0.9), jitter=0.01)
		p.seg((0, -0.08, h - 0.3), (0, 0.08, h - 0.3), 0.31, 0.31, sw, sides=12, grad=(0.05, 0.6))
		d.box((0.34, 0.02, 0.06), (0, -0.09, h - 0.45), IRON, grad=(0.5, 1.0))          # a worn inscription
		d.box((0.3, 0.02, 0.05), (0, -0.09, h - 0.6), IRON, grad=(0.5, 1.0))
		_move_parts(p, start, Matrix.Translation((x, y, -0.05)) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(tilt), 4, "Y"))
		_move_parts(d, dstart, Matrix.Translation((x, y, -0.05)) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(tilt), 4, "Y"))
		p.blob((0.8, 1.6, 0.3), (x, y - 1.0, 0.0), WOOD_GRAY, segs=(8, 4), grad=(0.3 + 0.2 * k, 1.0))   # its mound
	start = len(p.parts)                                                       # the cross
	p.box((0.16, 0.16, 1.3), (0, 0, 0.65), YS_PALE, grad=(0.05, 0.8))
	p.box((0.62, 0.15, 0.15), (0, 0, 0.98), YS_PALE, grad=(0.05, 0.8))
	p.box((0.4, 0.4, 0.2), (0, 0, 0.05), YS_STONE)
	_move_parts(p, start, Matrix.Translation((1.8, -0.8, 0)) @ Matrix.Rotation(math.radians(-7), 4, "X"))
	p.box((0.6, 0.9, 0.14), (-0.6, -1.3, 0.1), YS_STONE, rot=(3, 4, 20), grad=(0.1, 0.9))   # the fallen one
	p.seg((-0.6 - 0.15, -1.3 + 0.42, 0.1), (-0.6 - 0.1, -1.3 + 0.44, 0.24), 0.3, 0.3, YS_STONE, sides=10)
	for k in range(4):
		p.rock((0.3, 0.25, 0.2), (rng.uniform(-1.6, 1.8), rng.uniform(-1.2, 0.8), 0.05), YS_STONE)
	return join_into(p.build(bevel=0.03), [d.build()])


def fog_lantern():
	"""A crooked iron lamp post of old Ysmoor, about 3.2 m: a leaning, kinked
	post on a stone foot, a curled arm at the top and an iron lantern hanging
	from it on a hook, its glass glowing pale blue-green with will-o-light.
	Collide it as none."""
	p = Prop("fog_lantern", 814)
	d = Prop("fog_lantern_light", 815)
	p.rock((0.6, 0.55, 0.35), (0, 0, 0.05), YS_STONE)
	post = [(0, 0, 0.1), (0.05, 0.02, 1.1), (0.2, -0.02, 2.0), (0.22, 0.03, 2.7), (0.12, 0.0, 3.15)]
	_chain(p, post, 0.07, 0.045, IRON, sides=6, grad=(0.1, 0.9))
	arm = [(0.14, 0.0, 3.0), (0.45, 0.0, 3.2), (0.8, 0.0, 3.12), (0.95, 0.0, 2.95)]
	_chain(p, arm, 0.035, 0.03, IRON, sides=5)
	_chain(p, [(0.12, 0.0, 3.15), (0.02, 0.0, 3.3), (-0.08, 0.0, 3.22), (-0.04, 0.0, 3.1)], 0.03, 0.02, IRON, sides=4)   # a curl
	p.seg((0.18, 0, 2.55), (0.55, 0, 3.12), 0.02, 0.02, IRON, sides=4)          # brace
	p.seg((0.95, 0, 2.95), (0.95, 0, 2.72), 0.012, 0.012, IRON, sides=4)
	L = (0.95, 0.0, 2.4)                                                       # the lantern
	x, y, z = L
	p.seg((x, y, z + 0.28), (x, y, z + 0.42), 0.19, 0.03, IRON, sides=6, grad=(0.0, 0.7))
	p.seg((x, y, z - 0.24), (x, y, z - 0.18), 0.15, 0.15, IRON, sides=6)
	p.seg((x, y, z - 0.3), (x, y, z - 0.24), 0.05, 0.12, IRON, sides=6)
	for k in range(6):
		a = k * math.tau / 6
		p.seg((x + math.cos(a) * 0.15, y + math.sin(a) * 0.15, z - 0.2), (x + math.cos(a) * 0.17, y + math.sin(a) * 0.17, z + 0.28), 0.015, 0.015, IRON, sides=3)
	d.seg((x, y, z - 0.19), (x, y, z + 0.27), 0.13, 0.14, WISP, sides=6, grad=(0.0, 0.3), glow=1.6)
	d.blob((0.12, 0.12, 0.16), (x, y, z + 0.02), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.2), glow=2.4)
	return join_into(p.build(bevel=0.01), [d.build()])


# ---- The Ivory Field

def _tusk(p, base, direction, length, r, curl=0.35, up=(0, 0, 1), n=6, swatch=IVORY, sides=7, cut=False):
	"""An elephant tusk from base, heading along `direction` and curling
	toward `up` as it goes, tapering from r to a point (or a sawn flat end
	when cut). Returns its points."""
	base, dv, upv = Vector(base), Vector(direction).normalized(), Vector(up).normalized()
	pts, pos, h = [base], base.copy(), dv.copy()
	for k in range(n):
		h = (h + upv * curl / n * 2.2).normalized()
		pos = pos + h * length / n
		pts.append(pos.copy())
	_chain(p, [tuple(q) for q in pts], r, r * (0.55 if cut else 0.12), swatch, sides=sides, grad=(0.0, 0.7))
	if cut:
		e, e0 = pts[-1], pts[-2]
		dd = (e - e0).normalized()
		p.seg(tuple(e), tuple(e + dd * 0.012), r * 0.55, r * 0.55, SHELL_PEACH, sides=sides, grad=(0.0, 0.4))
	return pts


def giant_ribcage():
	"""The bones of a colossal elephant-like beast lying on its side, about
	27 m long: its spine and the knobs of its vertebrae half buried along the
	-X side, the spines of the vertebrae jutting sideways, eleven great ribs
	arching up over the plain to about 12 m and down to the +X side where their
	ends sink into the ground (two ribs snapped, their pieces lying in the
	dust), a tail of small vertebrae trailing off +Y, and a shoulder blade
	lying at the -Y end. The ground under the arches is open: walk between and
	under them. Collide it as a mesh."""
	p = Prop("giant_ribcage", 820)
	rng = p.rng
	SX = -6.5
	for k in range(15):                                                        # the spine
		y = -13.0 + k * 1.75
		s = 1.0 - abs(k - 6) * 0.03
		p.blob((1.9 * s, 1.5, 1.7 * s), (SX, y, 0.55 * s), IVORY, segs=(9, 6), grad=(0.0, 0.8), jitter=0.04)
		p.seg((SX - 0.4, y, 0.8 * s), (SX - 3.0 * s, y + 0.2, 1.1 + 0.5 * s), 0.35 * s, 0.1, IVORY, sides=6, grad=(0.0, 0.7))   # its spinous process, jutting sideways
		p.seg((SX, y, 1.2 * s), (SX + 0.2, y - 0.2, 2.0 * s), 0.2 * s, 0.08, IVORY, sides=5, grad=(0.0, 0.7))
	for k in range(9):                                                         # the tail
		y = 13.0 + k * 1.1
		s = 0.8 - k * 0.07
		p.blob((1.1 * s, 0.9 * s, 0.9 * s), (SX + k * 0.35, y, 0.25), IVORY, segs=(7, 5), grad=(0.0, 0.8))
	for k in range(11):
		y = -10.0 + k * 1.95
		f = 1.0 - 0.45 * ((k - 4) / 6) ** 2
		Rz = 12.0 * f
		Rx = 6.8 + 0.3 * f
		snap = k in (3, 8)
		pts = []
		N = 12
		for j in range(N + 1):
			t = j / N
			th = math.pi * t
			x = SX + 0.8 + Rx * (1 - math.cos(th)) * (1.0 + 0.04 * math.sin(th))
			z = 0.9 + Rz * math.sin(th) * (1.0 - 0.1 * t) - 1.4 * t * t
			yy = y + 0.9 * math.sin(th * 0.5) * (1 if k > 5 else -1) * 0.5 + 0.35 * t
			pts.append((x, yy, z))
			if snap and t >= 0.72:
				break
		_chain(p, pts, 0.55 * (0.8 + 0.2 * f), 0.26, IVORY, sides=7, grad=(0.0, 0.85))
		if snap:                                                               # the fallen piece of a snapped rib
			e = pts[-1]
			p.seg((e[0] + 1.8, y + 1.0, 0.25), (e[0] + 4.8, y - 0.2, 0.2), 0.3, 0.22, IVORY, sides=7, grad=(0.0, 0.8))
			_broken_top(p, e[0], e[1], e[2], 0.3, IVORY, n=2, rise=(0.05, 0.25))
		else:
			p.blob((1.2, 1.1, 0.35), (pts[-1][0], pts[-1][1], 0.0), WOOD_GRAY, segs=(7, 3), grad=(0.3, 1.0))   # earth heaped where it sank
	start = len(p.parts)                                                       # a shoulder blade
	_plate(p, [(-1.6, 0.0), (1.4, -0.2), (2.0, 1.2), (0.2, 2.6), (-1.4, 1.8)], 0.0, 0.3, IVORY, grad=(0.0, 0.7))
	_move_parts(p, start, Matrix.Translation((-1.0, -14.5, 0.3)) @ Matrix.Rotation(math.radians(20), 4, "Z") @ Matrix.Rotation(math.radians(-80), 4, "X"))
	for k in range(8):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(9.0, 15.0)
		c = Vector((math.cos(a) * r * 0.7, math.sin(a) * r, 0.1))
		t = rng.uniform(0, math.pi)
		_bone(p, tuple(c - Vector((math.cos(t), math.sin(t), 0)) * 0.6), tuple(c + Vector((math.cos(t), math.sin(t), 0)) * 0.6), r=0.07)
	return p.build(bevel=0.04)


def elephant_skull():
	"""A huge elephant skull half sunk in the pale earth, about 6.5 m from
	the back of the dome to the tusk tips: a bleached domed cranium (3.6 m
	across, 3.2 m high above ground), deep dark eye sockets and the great
	nasal hollow on its face (-Y), two long curving tusks sweeping forward and
	up (one chipped), earth heaped round it. Collide it as a mesh."""
	p = Prop("elephant_skull", 822)
	rng = p.rng
	p.blob((3.7, 4.4, 3.8), (0, 0.8, 1.1), IVORY, segs=(14, 10), grad=(0.0, 0.8), jitter=0.03)      # the dome
	p.blob((3.4, 2.4, 3.3), (0, -0.8, 1.4), IVORY, segs=(12, 8), grad=(0.0, 0.8))                    # the face
	p.blob((2.4, 1.6, 1.5), (0, -1.45, 0.45), IVORY, segs=(10, 6), grad=(0.1, 0.8))                  # the tusk sockets
	for s in (-1, 1):
		p.blob((1.2, 1.2, 1.1), (s * 0.95, -1.35, 0.5), IVORY, segs=(8, 6), grad=(0.1, 0.8))
		p.blob((0.5, 0.36, 0.45), (s * 1.45, -1.45, 1.75), SHADE, segs=(8, 6), grad=(0.95, 1.0))        # eye sockets, on the sides
		p.blob((0.8, 0.6, 0.35), (s * 1.4, -1.35, 2.05), IVORY, segs=(8, 5), grad=(0.0, 0.5))        # brow ridge
		p.blob((0.4, 1.8, 0.4), (s * 1.62, 0.1, 1.05), IVORY, rot=(0, s * 15, 0), segs=(8, 5), grad=(0.0, 0.7))   # cheek arch
		pts = _tusk(p, (s * 0.95, -1.9, 0.5), (s * 0.22, -1.0, -0.25), 4.2 if s < 0 else 3.0, 0.42, curl=0.55, up=(-s * 0.3, 0, 1), n=7)
		if s > 0:
			_broken_top(p, pts[-1][0], pts[-1][1], pts[-1][2], 0.25, IVORY, n=2, rise=(0.02, 0.1))
	p.blob((1.0, 0.5, 0.75), (0, -1.9, 2.2), SHADE, segs=(10, 6), grad=(0.95, 1.0))                  # the nasal hollow, high on the brow
	p.blob((1.2, 0.5, 0.3), (0, -1.75, 2.65), IVORY, segs=(8, 4), grad=(0.0, 0.5))
	for k in range(4):                                                         # cracks across the dome
		a = rng.uniform(-0.8, 0.8)
		_chain(p, [(math.sin(a) * 1.0, 0.6 + math.cos(a) * 0.5, 3.15), (math.sin(a) * 1.4, 0.8 + math.cos(a) * 1.0, 2.7), (math.sin(a) * 1.7, 1.1 + math.cos(a) * 1.3, 2.1)], 0.04, 0.02, WOOD_GRAY, sides=4, grad=(0.5, 1.0))
	for k in range(12):                                                        # earth heaped round it
		a = k * math.tau / 12
		p.blob((1.8, 1.2, 0.45), (math.cos(a) * 1.9, 0.3 + math.sin(a) * 2.1, 0.0), WOOD_GRAY, rot=(0, 0, math.degrees(a) + 90), segs=(7, 3), grad=(0.3, 1.0))
	return p.build(bevel=0.03)


def tusk_field():
	"""Old tusks thrust up out of the ground at angles: seven great curved
	tusks (the tallest about 4.2 m) and a few stubs, each rising from a little
	mound of earth, one old and yellowed. About 4.5 x 4 m. Collide it as a
	box."""
	p = Prop("tusk_field", 824)
	rng = p.rng
	for k, (x, y, L, lean, yaw, r) in enumerate(((0.0, 0.0, 4.4, 20, 0, 0.3), (-1.4, 0.8, 3.6, 28, 150, 0.26), (1.3, 0.6, 3.2, 32, 40, 0.24),
												 (0.6, -1.3, 2.8, 26, -70, 0.22), (-1.1, -1.0, 2.3, 35, -140, 0.2), (1.9, -0.6, 1.7, 22, 10, 0.17),
												 (-0.3, 1.7, 2.0, 18, 100, 0.18))):
		a, l = math.radians(yaw), math.radians(lean)
		dv = (math.sin(l) * math.cos(a), math.sin(l) * math.sin(a), math.cos(l))
		_tusk(p, (x, y, -0.4), dv, L, r, curl=0.5, up=(-math.cos(a), -math.sin(a), 0.5), n=6, swatch=IVORY if k != 3 else HIDE)
		p.blob((1.0, 0.9, 0.35), (x, y, 0.0), WOOD_GRAY, segs=(7, 3), grad=(0.3, 1.0))
	for x, y in ((1.8, 1.6), (-2.0, -0.1)):                                     # stubs
		p.seg((x, y, -0.1), (x + 0.1, y, 0.5), 0.18, 0.15, IVORY, sides=7, grad=(0.0, 0.7))
		p.seg((x + 0.1, y, 0.5), (x + 0.1, y, 0.52), 0.15, 0.15, SHELL_PEACH, sides=7)
	for k in range(5):
		p.rock((0.3, 0.25, 0.18), (rng.uniform(-2, 2), rng.uniform(-2, 2), 0.05), STONE_WARM)
	return p.build(bevel=0.02)


def _cart_wheel(p, c, r, w=0.12, spokes=8, broken=False):
	"""A spoked wooden wheel on an axle along X at c (a few spokes gone when broken)."""
	x, y, z = c
	start = len(p.parts)
	n = 14
	for k in range(n):
		if broken and k in (2, 3, 4, 9):
			continue
		a0, a1 = k * math.tau / n, (k + 1) * math.tau / n
		p.seg((0, math.cos(a0) * r, math.sin(a0) * r), (0, math.cos(a1) * r, math.sin(a1) * r), w * 0.6, w * 0.6, WOOD, sides=4, grad=(0.1, 0.8))
	p.seg((-w, 0, 0), (w, 0, 0), r * 0.18, r * 0.18, WOOD_GRAY, sides=8)
	for k in range(spokes):
		if broken and k in (1, 2):
			continue
		a = k * math.tau / spokes
		p.seg((0, 0, 0), (0, math.cos(a) * r, math.sin(a) * r), 0.035, 0.03, WOOD, sides=4)
	_move_parts(p, start, Matrix.Translation(c))


def poacher_wagon():
	"""An ivory poachers' wagon, about 5.4 x 2.4 m: a plank bed (3.6 x 1.8 m)
	with low sides on four spoked wheels, its front left wheel broken off and
	lying flat, so the bed sags to that corner; a load of sawn tusks piled on
	it under a torn, roped tarp, two more tusks lashed along the side, the
	tongue on the ground in front (-Y). Collide it as a mesh."""
	p = Prop("poacher_wagon", 826)
	d = Prop("poacher_wagon_load", 827)
	rng = p.rng
	start = len(p.parts)
	B = 0.95
	p.box((1.8, 3.6, 0.12), (0, 0, B), WOOD, grad=(0.1, 0.9))
	for s in (-1, 1):
		p.box((0.08, 3.6, 0.45), (s * 0.9, 0, B + 0.28), WOOD_GRAY, grad=(0.1, 0.9))
		p.box((1.8, 0.08, 0.45), (0, s * 1.8, B + 0.28), WOOD_GRAY, grad=(0.1, 0.9))
		for y in (-1.8, -0.6, 0.6, 1.8):
			p.box((0.1, 0.1, 0.62), (s * 0.93, y, B + 0.25), WOOD, grad=(0.1, 0.9))
	for y in (-1.2, 1.2):
		p.seg((-1.05, y, B - 0.35), (1.05, y, B - 0.35), 0.07, 0.07, WOOD_GRAY, sides=6)
		p.box((0.14, 0.14, 0.3), (-0.8, y, B - 0.2), WOOD_GRAY)
		p.box((0.14, 0.14, 0.3), (0.8, y, B - 0.2), WOOD_GRAY)
	# the load: sawn tusks stacked lengthwise
	for layer in range(3):
		for k in range(4 - layer):
			x = -0.55 + (k + layer * 0.5) * 0.36
			z = B + 0.22 + layer * 0.3
			y0 = -1.4 + rng.uniform(-0.2, 0.2)
			_tusk(d, (x, y0, z), (0, 1, 0.02), 2.2 + rng.uniform(-0.3, 0.3), 0.16, curl=0.25, up=(0, 0, 1), n=4, cut=True)
	# the torn tarp over the back half of the load
	tarp = [(-1.0, 0.1, B + 0.5), (1.0, 0.1, B + 0.5), (1.02, 1.9, B + 0.3), (-1.0, 1.9, B + 0.3)]
	peak = [(-0.3, 0.3, B + 1.25), (0.3, 1.2, B + 1.2)]
	for s in (-1, 1):
		d.poly([(s * 1.0, 0.1, B + 0.45), (s * 1.02, 1.9, B + 0.25), (s * 0.2, 1.3, B + 1.18), (s * 0.2, 0.3, B + 1.22)], [(0, 1, 2, 3)], HIDE, grad=(0.1, 0.8))
		d.poly([(s * 1.0, 0.1, B + 0.43), (s * 0.2, 0.3, B + 1.2), (s * 0.6, -0.5, B + 0.9)], [(0, 1, 2)], HIDE, grad=(0.2, 0.8))   # a torn flap
	d.poly([(-0.2, 0.3, B + 1.22), (0.2, 0.3, B + 1.22), (0.2, 1.3, B + 1.18), (-0.2, 1.3, B + 1.18)], [(0, 1, 2, 3)], HIDE, grad=(0.1, 0.6))
	for y in (0.4, 1.4):
		_rope(d, (-1.0, y, B + 0.5), (1.0, y, B + 0.5), -0.75, r=0.02)
	_tusk(d, (0.98, -1.4, B + 0.4), (0, 1, 0.08), 2.6, 0.13, curl=0.2, up=(0.3, 0, 1), n=4)
	for y in (-0.8, 0.6):
		p.seg((0.98, y, B + 0.25), (0.98, y, B + 0.62), 0.16, 0.16, HIDE, sides=6)
	for (x, y) in ((1.05, 1.3), (-1.05, 1.3), (1.05, -1.3)):
		_cart_wheel(p, (x, y, 0.6), 0.6)
	# sag toward the missing front left wheel
	_move_parts(p, start, Matrix.Translation((0, 0, -0.05)) @ Matrix.Rotation(math.radians(-6), 4, "Y") @ Matrix.Rotation(math.radians(-4), 4, "X"))
	_move_parts(d, 0, Matrix.Translation((0, 0, -0.05)) @ Matrix.Rotation(math.radians(-6), 4, "Y") @ Matrix.Rotation(math.radians(-4), 4, "X"))
	p.box((0.3, 0.3, 0.5), (-0.95, -1.3, 0.2), WOOD_GRAY, rot=(0, 20, 0))      # the axle end propped on a block
	wstart = len(p.parts)
	_cart_wheel(p, (0, 0, 0), 0.6, broken=True)
	_move_parts(p, wstart, Matrix.Translation((-2.0, -1.7, 0.12)) @ Matrix.Rotation(math.radians(80), 4, "Y"))
	for k in range(3):                                                         # its broken spokes
		p.seg((-1.4 + k * 0.2, -2.4 - k * 0.15, 0.04), (-1.1 + k * 0.25, -2.7 - k * 0.1, 0.04), 0.035, 0.03, WOOD, sides=4)
	p.seg((0, -1.9, 0.5), (0.2, -3.6, 0.08), 0.06, 0.05, WOOD, sides=6)        # the tongue
	p.seg((-0.35, -3.3, 0.1), (0.7, -3.4, 0.1), 0.05, 0.05, WOOD, sides=5)
	return join_into(p.build(bevel=0.02), [d.build()])


def ivory_pile():
	"""The poachers' ivory: sawn tusk pieces stacked crosswise in a pile
	about 2.8 x 2 m and 1.9 m high (four layers, the cut ends showing), bound
	with rope, three whole tusks leaning on it and a saw left on top.
	Collide it as a box."""
	p = Prop("ivory_pile", 828)
	rng = p.rng
	for layer in range(5):
		n = 7 - layer
		for k in range(n):
			z = 0.18 + layer * 0.32
			if layer % 2 == 0:
				x = (k - (n - 1) / 2) * 0.36
				_tusk(p, (x + rng.uniform(-0.04, 0.04), -0.95, z), (0, 1, 0), 1.9 + rng.uniform(-0.15, 0.1), 0.16, curl=0.2, up=(0, 0, 1), n=3, cut=True)
			else:
				y = (k - (n - 1) / 2) * 0.34 * 0.8
				_tusk(p, (-1.25, y + rng.uniform(-0.04, 0.04), z), (1, 0, 0), 2.4 + rng.uniform(-0.2, 0.1), 0.15, curl=0.2, up=(0, 0, 1), n=3, cut=True)
	for x in (-0.8, 0.8):
		_rope(p, (x, -1.1, 0.1), (x, 1.1, 0.1), -1.9, r=0.025)
	for k, (x, y, yaw) in enumerate(((1.6, -0.4, 200), (-1.7, 0.5, -20), (0.4, 1.3, 260))):
		a = math.radians(yaw)
		_tusk(p, (x, y, 0.0), (math.cos(a) * 0.6, math.sin(a) * 0.6, 1.0), 2.2, 0.17, curl=0.4, up=(math.cos(a), math.sin(a), 0.2), n=5)
	p.box((0.8, 0.03, 0.14), (0.1, 0.1, 1.72), IRON, rot=(0, 0, 25), grad=(0.0, 0.6))   # the saw
	p.box((0.1, 0.05, 0.2), (-0.28, -0.08, 1.75), WOOD, rot=(0, 0, 25))
	return p.build(bevel=0.02)


def vulture_perch():
	"""A dead tree the vultures own, about 6.5 m: a bleached gray trunk forking
	into bare crooked limbs, bones wedged in the forks, a skull on a snag, two
	big stick nests with pale eggs high in it, droppings down the bark and
	bones round the roots. About 4.6 m across. Collide it as a box."""
	p = Prop("vulture_perch", 830)
	rng = p.rng
	GRAY = WOOD_GRAY
	trunk = [(0, 0, -0.3), (0.1, 0.05, 1.4), (0.0, -0.05, 2.8), (0.15, 0.0, 3.6)]
	_chain(p, trunk, 0.36, 0.22, GRAY, sides=7, grad=(0.1, 0.9))
	for k in range(4):
		a = k * math.tau / 4 + 0.4
		p.seg((0, 0, 0.5), (math.cos(a) * 0.9, math.sin(a) * 0.9, -0.2), 0.2, 0.06, GRAY, sides=5, grad=(0.3, 1.0))
	limbs = []
	for k, (a, L, rise, r) in enumerate(((0.3, 2.3, 2.2, 0.16), (2.3, 2.1, 2.6, 0.15), (4.0, 2.0, 1.8, 0.14), (1.2, 1.6, 3.0, 0.12))):
		b = Vector(trunk[-1]) - Vector((0, 0, k * 0.25))
		m = b + Vector((math.cos(a) * L * 0.5, math.sin(a) * L * 0.5, rise * 0.6))
		e = b + Vector((math.cos(a + 0.3) * L, math.sin(a + 0.3) * L, rise))
		_chain(p, [tuple(b), tuple(m), tuple(e)], r, 0.04, GRAY, sides=5, grad=(0.1, 0.9))
		for j in range(2):                                                     # twigs
			aa = a + rng.uniform(-1.0, 1.0)
			p.seg(tuple(m), tuple(m + Vector((math.cos(aa) * 0.8, math.sin(aa) * 0.8, rng.uniform(0.2, 0.7)))), 0.04, 0.01, GRAY, sides=4)
		limbs.append((m, e))
	for (m, e), kind in zip(limbs, ("nest", "skull", "nest", "bone")):
		if kind == "nest":
			c = (m + e) / 2 + Vector((0, 0, 0.1))
			_stick_ring(p, tuple(c), 0.8, 3, rng, swatches=(GRAY, WOOD, BONE), r=0.05, length=(0.6, 1.1))
			p.blob((1.3, 1.3, 0.2), tuple(c + Vector((0, 0, 0.05))), HIDE, segs=(7, 4), grad=(0.3, 0.9))
			for j in range(2):
				p.blob((0.2, 0.2, 0.27), tuple(c + Vector(((j - 0.5) * 0.26, 0, 0.3))), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.5))
		elif kind == "skull":
			_skull(p, tuple(e + Vector((0, 0, -0.05))), 1.4, yaw=0.3)
		else:
			_bone(p, tuple(m + Vector((-0.3, 0, 0.05))), tuple(m + Vector((0.3, 0.1, 0.12))), r=0.035)
	_bone(p, (0.3, -0.25, 3.3), (-0.2, 0.3, 3.45), r=0.04)                    # wedged in the main fork
	for k in range(3):                                                         # droppings down the bark
		a = k * 2.1
		p.seg((math.cos(a) * 0.3, math.sin(a) * 0.3, 3.2 - k * 0.3), (math.cos(a) * 0.36, math.sin(a) * 0.36, 1.8 - k * 0.3), 0.06, 0.02, CLOTH_WHITE, sides=4, grad=(0.0, 0.4))
	for k in range(6):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(0.9, 1.9)
		c = Vector((math.cos(a) * r, math.sin(a) * r, 0.05))
		t = rng.uniform(0, math.pi)
		_bone(p, tuple(c - Vector((math.cos(t), math.sin(t), 0)) * 0.25), tuple(c + Vector((math.cos(t), math.sin(t), 0)) * 0.25), r=0.03)
	return p.build()


def spirit_cairn():
	"""A spirit cairn of the Ivory Field, about 2 m: flat stones and great
	bones stacked into a rough cone, an old elephant's jaw and a small skull
	at its crown, offerings round its foot (wild flowers, a bowl, candles, a
	little bronze bell hung from a bone post), and pale blue spirit-light
	glowing from its gaps and drifting over it. Collide it as a box."""
	p = Prop("spirit_cairn", 832)
	d = Prop("spirit_cairn_glow", 833)
	rng = p.rng
	z = 0.0
	for k, r in enumerate((1.0, 0.85, 0.7, 0.55, 0.42, 0.3)):                  # the courses
		n = 7 - k
		for j in range(n):
			a = j * math.tau / n + k * 0.4
			s = rng.uniform(0.9, 1.1)
			p.rock((0.55 * s, 0.45 * s, 0.26), (math.cos(a) * r * 0.75, math.sin(a) * r * 0.75, z + 0.12), STONE_WARM if (j + k) % 3 else STONE_LIGHT, rot=(0, 0, math.degrees(a)))
		if k in (1, 3):
			a = rng.uniform(0, math.tau)
			_bone(p, (math.cos(a) * r, math.sin(a) * r, z + 0.3), (-math.cos(a) * r, -math.sin(a) * r, z + 0.32), r=0.05)
		z += 0.26
	p.blob((0.9, 0.35, 0.3), (0, 0, z + 0.1), IVORY, segs=(8, 5), grad=(0.0, 0.6))           # a jawbone across the top
	_skull(p, (0, 0, z + 0.2), 1.6)
	for k in range(5):                                                         # spirit-light in the gaps
		a = k * math.tau / 5 + 0.3
		zz = 0.3 + k * 0.28
		r = 0.95 - k * 0.14
		d.blob((0.14, 0.14, 0.1), (math.cos(a) * r * 0.78, math.sin(a) * r * 0.78, zz), SKY, segs=(6, 4), grad=(0.0, 0.2), glow=2.0)
	for k, (x, y, zz) in enumerate(((0.5, -0.4, 2.1), (-0.4, 0.2, 2.4), (0.1, 0.5, 1.9))):
		d.blob((0.12, 0.12, 0.12), (x, y, zz), CLOTH_WHITE if k % 2 else SKY, segs=(6, 4), grad=(0.0, 0.2), glow=2.2)
	# offerings round the foot
	for k in range(6):
		a = -math.pi / 2 + (k - 2.5) * 0.35
		x, y = math.cos(a) * 1.2, math.sin(a) * 1.2
		if k in (1, 4):
			_candle(d, (x, y, 0.0), h=0.14)
		else:
			d.seg((x, y, 0.0), (x, y, 0.2), 0.008, 0.008, LEAF, sides=3)
			for j in range(4):
				b = j * math.tau / 4
				d.blob((0.07, 0.07, 0.03), (x + math.cos(b) * 0.04, y + math.sin(b) * 0.04, 0.2), PETAL_WHITE if k % 2 else PETAL_YELLOW, segs=(5, 3), grad=(0.0, 0.4))
	d.seg((0.0, -1.3, 0.0), (0.0, -1.3, 0.1), 0.14, 0.18, CLAY, sides=10, grad=(0.1, 0.7))    # a bowl of grain
	d.seg((0.0, -1.3, 0.08), (0.0, -1.3, 0.1), 0.15, 0.15, HIDE, sides=10)
	_bone(p, (1.15, -0.55, 0.0), (1.2, -0.6, 1.25), r=0.04)                   # a bone post with a bell
	p.seg((1.2, -0.6, 1.2), (1.2, -0.85, 1.22), 0.02, 0.02, BONE, sides=4)
	_lathe(d, [(0.01, 0.0), (0.08, 0.02), (0.07, 0.12), (0.03, 0.16), (0.01, 0.17)], 8, COPPER, grad=(0.0, 0.6)).data.transform(Matrix.Translation((1.2, -0.85, 0.98)))
	return join_into(p.build(bevel=0.02), [d.build()])


def bone_scatter():
	"""Clutter: a few small bleached bones in the grass (two long bones, a
	rib and a knuckle), about 1 m across and 0.1 m high. Very few faces;
	colored, not tinted. No collision."""
	p = Prop("bone_scatter", 834)
	for a, b, r in (((-0.35, -0.1, 0.04), (0.2, 0.05, 0.05), 0.035), ((0.05, 0.25, 0.035), (0.35, 0.4, 0.03), 0.028)):
		p.seg(a, b, r, r * 0.85, BONE, sides=4, grad=(0.0, 0.6))
		for e in (a, b):
			p.blob((r * 3, r * 3, r * 2.4), e, BONE, segs=(4, 3), grad=(0.0, 0.5))
	_chain(p, [(-0.2, 0.3, 0.02), (-0.28, 0.12, 0.07), (-0.2, -0.05, 0.09), (-0.05, -0.12, 0.05)], 0.022, 0.015, BONE, sides=3, grad=(0.0, 0.6))
	p.blob((0.09, 0.08, 0.06), (0.32, -0.2, 0.02), BONE, segs=(4, 3), grad=(0.0, 0.6))
	return p.build()


# ---- The Unlit

def _glow_moss(p, top, length, r=0.035, glow=1.0):
	"""A strand of pale glowing moss hanging from `top`, swaying a little."""
	x, y, z = top
	pts = [(x, y, z)]
	for k in range(1, 4):
		pts.append((x + p.rng.uniform(-0.08, 0.08), y + p.rng.uniform(-0.08, 0.08), z - length * k / 3))
	_chain(p, pts, r, r * 0.4, NIGHT_LEAF, sides=4, grad=(0.0, 0.5), glow=glow)


def _glow_crown(p, c, r, n, rng, flat=0.7, glow=0.7):
	"""A crown of pale blue-white glowing leaf clusters round c."""
	x, y, z = c
	for k in range(n):
		a = k * math.tau / n + rng.uniform(-0.3, 0.3)
		rr = r * rng.uniform(0.35, 0.7) if k else 0.0
		s = r * rng.uniform(0.7, 1.0)
		p.rock((s * 1.2, s * 1.2, s * flat), (x + math.cos(a) * rr, y + math.sin(a) * rr, z + rng.uniform(-0.2, 0.3) * r), NIGHT_LEAF if k % 3 else SKY,
			   rot=(0, 0, rng.uniform(0, 360)), grad=(0.0, 0.55), jitter=0.06)
	for o in p.parts[-n:]:
		o.data.materials[0] = atlas_material(glow)


def black_tree():
	"""A tall tree of the Unlit, about 10 m: a straight black trunk (slim at
	the ground, flared roots) with crooked black boughs holding round clusters
	of pale blue-white leaves that glow faintly, and strands of glowing moss
	hanging from the boughs. Use it in a zone's tree_mix (trunk collider)."""
	p = Prop("black_tree", 840)
	rng = p.rng
	trunk = [(0, 0, -0.3), (0.05, 0.03, 2.2), (-0.1, 0.0, 4.4), (0.05, -0.05, 6.4), (0.1, 0.0, 7.8)]
	_chain(p, trunk, 0.34, 0.14, NIGHT_BARK, sides=7, grad=(0.2, 1.0))
	for k in range(5):
		a = k * math.tau / 5 + 0.3
		p.seg((0, 0, 0.5), (math.cos(a) * 0.9, math.sin(a) * 0.9, -0.2), 0.2, 0.05, NIGHT_BARK, sides=5, grad=(0.4, 1.0))
	crowns = [((0.1, 0.0, 8.6), 2.0)]
	ends = []
	for k, (z, a, L) in enumerate(((3.8, 0.2, 2.6), (4.6, 2.3, 2.4), (5.5, 4.2, 2.3), (6.3, 1.2, 2.0), (7.0, 3.3, 1.6))):
		b = Vector((0, 0, z))
		m = b + Vector((math.cos(a) * L * 0.55, math.sin(a) * L * 0.55, L * 0.25))
		e = b + Vector((math.cos(a + 0.25) * L, math.sin(a + 0.25) * L, L * 0.75))
		_chain(p, [tuple(b), tuple(m), tuple(e)], 0.13, 0.04, NIGHT_BARK, sides=5, grad=(0.2, 1.0))
		crowns.append((tuple(e + Vector((0, 0, 0.3))), 1.5))
		ends.append((m, e))
	for c, r in crowns:
		_glow_crown(p, c, r, 5, rng)
	for m, e in ends:                                                          # glowing moss hanging from the boughs
		for t in (0.3, 0.7):
			q = m.lerp(e, t)
			_glow_moss(p, tuple(q), rng.uniform(1.0, 2.0))
	return p.build()


def black_tree_b():
	"""A weeping tree of the Unlit, about 7.5 m: a gnarled black trunk
	leaning a little and splitting into four long drooping black limbs, each
	trailing curtains of pale glowing moss nearly to the ground, small glowing
	leaf clusters along the limbs and a low crown. About 7 m across. Use it in
	a zone's tree_mix (trunk collider)."""
	p = Prop("black_tree_b", 842)
	rng = p.rng
	fork = (0.25, 0.1, 3.4)
	_chain(p, [(0, 0, -0.3), (0.05, 0.0, 1.2), (0.2, 0.05, 2.4), fork], 0.4, 0.3, NIGHT_BARK, sides=7, grad=(0.2, 1.0))
	for k in range(5):
		a = k * math.tau / 5 + 0.1
		p.seg((0, 0, 0.5), (math.cos(a) * 1.1, math.sin(a) * 1.1, -0.2), 0.22, 0.06, NIGHT_BARK, sides=5, grad=(0.4, 1.0))
	p.blob((0.7, 0.6, 0.5), fork, NIGHT_BARK, segs=(7, 5), grad=(0.2, 1.0))
	for k, a in enumerate((0.3, 1.9, 3.3, 4.8)):
		L = rng.uniform(3.0, 3.6)
		pts = [fork]
		for j in range(1, 6):
			t = j / 5
			pts.append((fork[0] + math.cos(a) * L * t, fork[1] + math.sin(a) * L * t, fork[2] + 2.6 * math.sin(t * math.pi * 0.8) - 0.6 * t))
		_chain(p, pts, 0.2, 0.05, NIGHT_BARK, sides=5, grad=(0.2, 1.0))
		for j in (2, 3, 4, 5):                                                 # moss curtains
			q = pts[j]
			if rng.random() < 0.8:
				_glow_moss(p, (q[0] + rng.uniform(-0.2, 0.2), q[1] + rng.uniform(-0.2, 0.2), q[2] - 0.05), rng.uniform(0.8, max(1.0, q[2] - 1.0)), r=0.045)
		for j in (2, 4):
			q = pts[j]
			_glow_crown(p, (q[0], q[1], q[2] + 0.35), 0.8, 3, rng, flat=0.6)
	_glow_crown(p, (fork[0], fork[1], fork[2] + 2.6), 1.5, 4, rng, flat=0.6)
	return p.build()


def star_lily():
	"""Clutter: a pale lily of the Unlit, about 0.4 m: two strap leaves and a
	stem bearing one white flower of five pointed star petals with a pale
	gold heart. Few faces; colored, not tinted (its pale petals read as a glow
	in the dark). No collision."""
	p = Prop("star_lily", 844)
	for a in (0.4, 3.0):
		p.poly([(0, 0, 0), (math.cos(a) * 0.18 - 0.03, math.sin(a) * 0.18, 0.1), (math.cos(a) * 0.2 + 0.03, math.sin(a) * 0.18 + 0.03, 0.08)], [(0, 1, 2)], PINE, grad=(0.3, 0.9))
	p.seg((0, 0, 0), (0.02, 0, 0.3), 0.012, 0.01, PINE, sides=3)
	c = Vector((0.02, 0, 0.32))
	verts = [tuple(c)]
	for k in range(10):
		a = k * math.tau / 10
		r = 0.17 if k % 2 == 0 else 0.05
		verts.append((c.x + math.cos(a) * r, c.y + math.sin(a) * r, c.z + (0.035 if k % 2 == 0 else 0.0)))
	p.poly(verts, [(0, 1 + k, 1 + (k + 1) % 10) for k in range(10)], NIGHT_LEAF, grad=(0.0, 0.3))
	p.blob((0.07, 0.07, 0.06), (c.x, c.y, c.z + 0.01), PETAL_YELLOW, segs=(4, 3), grad=(0.0, 0.3))
	return p.build()


def glowcap_cluster():
	"""Clutter: a small cluster of five pale glowing mushrooms, 0.1 to 0.35 m
	tall, on a little mossy mound. Few faces; colored, not tinted. No
	collision."""
	p = Prop("glowcap_cluster", 846)
	p.blob((0.4, 0.34, 0.08), (0, 0, 0.0), MOSS, segs=(6, 3), grad=(0.3, 0.9))
	for k, (x, y, h, r) in enumerate(((0.0, 0.0, 0.34, 0.11), (0.12, 0.08, 0.22, 0.08), (-0.1, 0.09, 0.18, 0.07), (0.08, -0.11, 0.14, 0.06), (-0.12, -0.06, 0.1, 0.05))):
		p.seg((x, y, 0.0), (x + 0.01, y, h), r * 0.3, r * 0.25, NIGHT_LEAF, sides=4, grad=(0.0, 0.4))
		p.seg((x + 0.01, y, h - r * 0.2), (x + 0.01, y, h + r * 0.5), r, r * 0.2, SKY if k % 2 else TEAL, sides=6, grad=(0.0, 0.3))
	return p.build()


def _pane_run(p, a, b, ks, swatch, glow, z=1.6, size=3.0):
	"""Glowing panes set 0.2 m in from the KayKit window openings `ks` of a
	_kaykit_run from a to b (same piece spacing)."""
	a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
	dd = b - a
	n = max(1, round(dd.length / size))
	yaw = math.atan2(dd.y, dd.x)
	inward = Vector((-math.sin(yaw), math.cos(yaw), 0))
	for k in ks:
		c = a + dd * ((k + 0.5) / n) + inward * 0.2
		p.box((1.7, 0.1, 1.7), (c.x, c.y, z), swatch, rot=(0, 0, math.degrees(yaw)), grad=(0.2, 0.6), glow=glow)


def morvaine_manor():
	"""The Morvaines' manor, a vampiric noble house of dark stone, about
	24 x 18 m: a main hall 24 x 9 m of three storeys (walls 9 m, KayKit stone
	repainted dark) under a steep slate roof to 15.5 m with two tall chimneys,
	two wings projecting 9 m toward the front (-Y) under steep front-gabled
	roofs, a round tower on the left wing's front corner with a conical
	spire to 23.6 m, and a pointed porch in the middle with a double door;
	tall lancet windows lit blood-red on every face, iron spikes on the ridges.
	The front door faces -Y. Collide it as a mesh (it is solid)."""
	p = Prop("morvaine_manor", 848)
	rng = p.rng
	pieces = []
	RH = 3.0

	# the hall: x -12..12, y 0..9, three courses; its front between the wings shows
	_kaykit_run(pieces, (-6.0, 0.0), (6.0, 0.0), 0.0, 3, RH, kinds=lambda r, k: "wall_window_open" if r == 0 and k in (0, 3) else "wall")
	for (a, b) in (((-12.0, 0.0), (-6.0, 0.0)), ((6.0, 0.0), (12.0, 0.0))):
		_kaykit_run(pieces, a, b, RH * 2, 1, RH)                                 # above the wing roofs' eaves
	_kaykit_run(pieces, (12.0, 0.0), (12.0, 9.0), 0.0, 3, RH, kinds=lambda r, k: "wall_window_open" if r == 0 and k == 1 else "wall")
	_kaykit_run(pieces, (12.0, 9.0), (-12.0, 9.0), 0.0, 3, RH, kinds=lambda r, k: "wall_window_open" if r == 0 and k % 3 == 1 else "wall")
	_kaykit_run(pieces, (-12.0, 9.0), (-12.0, 0.0), 0.0, 3, RH, kinds=lambda r, k: "wall_window_open" if r == 0 and k == 1 else "wall")
	# the wings: x 6..12 (and mirrored), y -9..0, two courses, three sides
	for s in (-1, 1):
		x0, x1 = sorted((s * 6.0, s * 12.0))
		win = 1 if s < 0 else 0                                               # the front window nearer the courtyard
		ring = [(x0, 0.0), (x0, -9.0), (x1, -9.0), (x1, 0.0)]
		for i, (a, b) in enumerate(zip(ring, ring[1:])):
			_kaykit_run(pieces, a, b, 0.0, 2, RH, kinds=lambda r, k, i=i: "wall_window_open" if r == 0 and k == (win if i == 1 else 1) else "wall")
			_pane_run(p, a, b, [win] if i == 1 else [1], BLOOD_GLASS, 1.5)
		for x, y in ring[:3]:
			for r in range(2):
				pieces += kaykit("pillar", (x, y, r * RH), 0.0, (0.62, 0.62, RH / 4))
	for x, y in ((-12.0, 9.0), (12.0, 9.0)):
		for r in range(3):
			pieces += kaykit("pillar", (x, y, r * RH), 0.0, (0.62, 0.62, RH / 4))
	# solid cores (the walls are one piece thick; the inside is filled for a clean collider)
	p.box((23.2, 8.2, 9.0), (0, 4.5, 4.5), STONE_DARK, grad=(0.3, 1.0))
	for s in (-1, 1):
		p.box((5.2, 8.6, 6.0), (s * 9.0, -4.5, 3.0), STONE_DARK, grad=(0.3, 1.0))
	# glowing panes in the hall's ground-floor windows
	_pane_run(p, (-6.0, 0.0), (6.0, 0.0), [0, 3], BLOOD_GLASS, 1.5)
	_pane_run(p, (12.0, 0.0), (12.0, 9.0), [1], BLOOD_GLASS, 1.5)
	_pane_run(p, (12.0, 9.0), (-12.0, 9.0), [1, 4, 7], BLOOD_GLASS, 1.5)
	_pane_run(p, (-12.0, 9.0), (-12.0, 0.0), [1], BLOOD_GLASS, 1.5)
	# tall lancets on the upper floors
	F = -0.4                                                                  # a wall's outer face, out from its line
	for x in (-4.5, 4.5):
		_lancet(p, (x, F, 3.5), 1.1, 4.2)
	for x in (-9.0, 9.0):
		_lancet(p, (x, -9.0 + F, 3.3), 1.2, 2.4)                              # wing fronts, upstairs
		_lancet(p, (x, -9.06, 6.6), 0.8, 3.0)                                 # in the gables
	for s in (-1, 1):
		for y in (-6.0, -3.0):
			_lancet(p, (s * (12.0 - F), y, 3.4), 0.9, 2.2, yaw=90 * s)
		for y in (3.0, 6.0):
			_lancet(p, (s * (12.0 - F), y, 3.5), 0.9, 4.0, yaw=90 * s)
	for x in (-9.0, -3.0, 3.0, 9.0):
		_lancet(p, (x, 9.0 - F, 3.5), 0.9, 4.0, yaw=180)
	# roofs
	_steep_roof(p, (0, 4.5), 9.0, 24.0, 9.0, 6.5, ridge_x=True)
	for s in (-1, 1):
		_steep_roof(p, (s * 9.0, -4.5), 6.0, 9.0, 6.0, 5.5, finials=True)
	for s in (-1, 1):                                                          # the chimneys
		cx = s * 7.5
		p.box((1.3, 1.1, 8.0), (cx, 6.2, 12.5), STONE_DARK, grad=(0.1, 0.9), jitter=0.02)
		p.box((1.6, 1.4, 0.3), (cx, 6.2, 16.5), IRON, grad=(0.0, 0.7))
		for j in range(2):
			p.seg((cx - 0.3 + j * 0.6, 6.2, 16.6), (cx - 0.3 + j * 0.6, 6.2, 17.2), 0.2, 0.18, CLAY, sides=6)
	# the tower on the hall's left front corner
	tx, ty, TR = -12.3, -9.3, 2.3
	p.seg((tx, ty, -0.2), (tx, ty, 0.6), TR + 0.4, TR + 0.35, STONE_DARK, sides=14, grad=(0.3, 1.0))
	p.seg((tx, ty, 0.6), (tx, ty, 14.0), TR, TR, STONE_DARK, sides=14, grad=(0.1, 0.95))
	for z in (5.0, 9.8):
		p.seg((tx, ty, z), (tx, ty, z + 0.3), TR + 0.14, TR + 0.14, IRON, sides=14, grad=(0.0, 0.6))
	p.seg((tx, ty, 13.8), (tx, ty, 14.5), TR + 0.5, TR + 0.5, IRON, sides=14, grad=(0.0, 0.6))
	p.seg((tx, ty, 14.5), (tx, ty, 22.3), TR + 0.55, 0.05, IRON, sides=14, grad=(0.0, 0.9))
	p.seg((tx, ty, 22.2), (tx, ty, 23.6), 0.06, 0.0, IRON, sides=4)
	p.blob((0.3, 0.3, 0.3), (tx, ty, 22.5), IRON, segs=(6, 4))
	for k, (deg, z) in enumerate(((-110, 6.2), (-150, 10.6), (-70, 10.6), (-130, 2.0), (170, 7.0))):
		a = math.radians(deg)
		_lancet(p, (tx + math.cos(a) * (TR + 0.02), ty + math.sin(a) * (TR + 0.02), z), 0.7, 2.2 if z > 3 else 1.6, yaw=deg + 90)
	# the porch and its double door
	PY = -2.4
	for s in (-1, 1):
		p.box((0.9, 2.6, 5.0), (s * 1.9, PY + 1.2, 2.5), STONE_DARK, grad=(0.05, 0.9))
		p.seg((s * 1.9, PY - 0.2, 5.0), (s * 1.9, PY - 0.2, 6.4), 0.3, 0.0, IRON, sides=4)
	arch = [(-2.35, 0.0), (2.35, 0.0), (2.35, 5.0), (1.2, 6.6), (0.0, 7.4), (-1.2, 6.6), (-2.35, 5.0)]
	o = _plate(p, arch, PY + 1.2, 2.6, STONE_DARK, grad=(0.05, 0.9))
	o.data.transform(Matrix.Translation((0, 0, 0.001)))
	p.box((4.8, 3.2, 0.3), (0, PY + 1.2, 0.0), STONE_LIGHT, grad=(0.1, 0.8))
	for k in range(2):
		p.box((3.2, 0.5, 0.18), (0, PY - 0.35 - k * 0.45, 0.09 - k * 0.06), STONE_LIGHT, grad=(0.1, 0.8))
	door = [(-0.95, 0.0), (0.95, 0.0), (0.95, 2.6), (0.5, 3.3), (0.0, 3.6), (-0.5, 3.3), (-0.95, 2.6)]
	_plate(p, [(x * 1.2, z * 1.08 - 0.05) for x, z in door], PY - 0.12, 0.1, IRON, grad=(0.1, 0.8))
	_plate(p, door, PY - 0.2, 0.08, WOOD, grad=(0.3, 1.0))
	p.seg((0, PY - 0.25, 0.05), (0, PY - 0.25, 3.55), 0.03, 0.03, IRON, sides=4)
	for z in (0.8, 2.2):
		p.seg((-0.9, PY - 0.25, z), (0.9, PY - 0.25, z), 0.035, 0.035, IRON, sides=4)
	for s in (-1, 1):
		_torus(p, (s * 0.25, PY - 0.28, 1.5), (1, 0, 0), (0, 0, 1), 0.1, 0.02, IRON, seg=8, ring=3)
	_lancet(p, (0, PY - 0.12, 4.1), 0.7, 1.9, bars=False)                    # the porch's red rose-light
	for s in (-1, 1):                                                          # red lamps by the door
		p.seg((s * 1.9, PY - 0.1, 3.2), (s * 1.9, PY - 0.9, 3.2), 0.04, 0.04, IRON, sides=4)
		p.seg((s * 1.9, PY - 0.9, 2.75), (s * 1.9, PY - 0.9, 3.1), 0.12, 0.13, BLOOD_GLASS, sides=6, grad=(0.1, 0.4), glow=2.0)
		p.seg((s * 1.9, PY - 0.9, 3.1), (s * 1.9, PY - 0.9, 3.3), 0.16, 0.02, IRON, sides=6)
	obj = p.build(bevel=0.04)
	return _merge_materials(join_into(obj, _restone(pieces, NIGHT_STONE)))


def _bat_finial(p, c, s=1.0):
	"""A stone ball on a cap with a pair of bat wings spread from it (facing -Y)."""
	x, y, z = c
	p.blob((0.5 * s, 0.5 * s, 0.5 * s), (x, y, z + 0.25 * s), STONE_DARK, segs=(10, 6), grad=(0.0, 0.8))
	p.blob((0.28 * s, 0.26 * s, 0.26 * s), (x, y - 0.12 * s, z + 0.62 * s), STONE_DARK, segs=(8, 5), grad=(0.0, 0.8))   # the bat's head
	for e in (-1, 1):
		p.seg((x + e * 0.08 * s, y - 0.18 * s, z + 0.75 * s), (x + e * 0.12 * s, y - 0.2 * s, z + 0.92 * s), 0.05 * s, 0.0, STONE_DARK, sides=4)
		wing = [(0.0, 0.0), (0.35, 0.35), (0.7, 0.55), (1.0, 0.45), (0.92, 0.18), (0.78, 0.26), (0.66, 0.02), (0.5, 0.12), (0.36, -0.1), (0.16, -0.05)]
		o = _plate(p, [(e * wx * s, wz * s) for wx, wz in wing], 0.0, 0.07 * s, IRON, grad=(0.1, 0.8))
		o.data.transform(Matrix.Translation((x + e * 0.2 * s, y + 0.02, z + 0.42 * s)) @ Matrix.Rotation(math.radians(e * 18), 4, "Z"))


def morvaine_gate():
	"""The Morvaine estate's gate: two dark stone pillars 4.6 m tall (1.3 m
	square) topped by stone balls with bat wings, an 8 m opening between them
	with two wrought-iron gate leaves (spear-tipped bars, scroll tops) standing
	open inward (+Y), and an iron overthrow arching 6.5 m over the way with a
	bat crest. About 11 x 5 m. Walk through it. Collide it as a mesh."""
	p = Prop("morvaine_gate", 850)
	HW = 4.0
	for s in (-1, 1):
		x = s * (HW + 0.65)
		p.box((1.7, 1.7, 0.45), (x, 0, 0.2), STONE_LIGHT, grad=(0.1, 0.8))
		p.box((1.3, 1.3, 3.8), (x, 0, 2.3), STONE_DARK, grad=(0.05, 0.95), jitter=0.02)
		for z in (1.2, 2.6):
			p.box((1.36, 1.36, 0.12), (x, 0, z), IRON, grad=(0.0, 0.8))
		p.box((1.6, 1.6, 0.3), (x, 0, 4.35), STONE_LIGHT, grad=(0.0, 0.7))
		_bat_finial(p, (x, 0, 4.5), 1.0)
		for z in (0.9, 3.0):                                                   # gate pins
			p.box((0.25, 0.2, 0.15), (s * HW + -s * 0.05, 0.3, z), IRON)
	# the leaves, swung open to the inside (+Y)
	for s in (-1, 1):
		start = len(p.parts)
		W = HW - 0.1
		n = 14
		for k in range(n + 1):
			u = 0.08 + (W - 0.16) * k / n
			top = 2.9 + 0.6 * math.sin(math.pi * u / W)
			p.seg((u, 0, 0.1), (u, 0, top), 0.025, 0.025, IRON, sides=4, grad=(0.1, 0.8))
			p.seg((u, 0, top), (u, 0, top + 0.22), 0.05, 0.0, IRON, sides=4)
		for z in (0.35, 1.6):
			p.seg((0.0, 0, z), (W, 0, z), 0.035, 0.035, IRON, sides=4)
		pts = [(u, 0, 2.7 + 0.55 * math.sin(math.pi * u / W)) for u in [W * j / 8 for j in range(9)]]
		_chain(p, pts, 0.035, 0.035, IRON, sides=4)
		for j in range(3):                                                     # scrolls
			_torus(p, (0.6 + j * 1.3, 0, 2.3 + 0.3 * math.sin(math.pi * (0.6 + j * 1.3) / W)), (1, 0, 0), (0, 0, 1), 0.22, 0.02, IRON, seg=10, ring=3)
		p.seg((0.02, 0, 0.1), (0.02, 0, 3.0), 0.05, 0.05, IRON, sides=4)
		m = Matrix.Translation((s * HW, 0.3, 0)) @ Matrix.Rotation(math.radians(100 if s > 0 else 80), 4, "Z")
		_move_parts(p, start, m)
	# the overthrow
	pts = [(x, 0, 5.0 + 1.5 * math.sin(math.pi * (x + HW) / (2 * HW))) for x in [-HW - 0.3 + (2 * HW + 0.6) * j / 12 for j in range(13)]]
	_chain(p, pts, 0.05, 0.05, IRON, sides=4)
	_chain(p, [(x, y, z - 0.45) for x, y, z in pts], 0.035, 0.035, IRON, sides=4)
	for x, _, z in pts[1:-1]:
		p.seg((x, 0, z - 0.45), (x, 0, z), 0.02, 0.02, IRON, sides=3)
	for s in (-1, 1):
		p.seg((s * (HW + 0.2), 0, 4.2), (s * (HW + 0.2), 0, 5.1), 0.04, 0.04, IRON, sides=4)
	_bat_finial(p, (0, 0, 6.2), 0.7)                                          # the crest
	_crescent(p, (0, -0.02, 5.75), 0.4, yaw=90, swatch=SILVER)
	return p.build(bevel=0.01)


def iron_fence():
	"""A 10 m run of wrought-iron fence along X on a low stone plinth: stone
	posts with caps at both ends and the middle (2.4 m), spear-tipped bars
	2.1 m tall between them on two rails. Faces -Y. Collide it as a box."""
	p = Prop("iron_fence", 852)
	L = 10.0
	p.box((L, 0.5, 0.45), (0, 0, 0.1), STONE_DARK, grad=(0.1, 0.9))
	p.box((L, 0.58, 0.08), (0, 0, 0.36), STONE_LIGHT, grad=(0.0, 0.7))
	for x in (-L / 2 + 0.3, 0.0, L / 2 - 0.3):
		p.box((0.6, 0.6, 2.3), (x, 0, 1.15), STONE_DARK, grad=(0.05, 0.9))
		p.box((0.74, 0.74, 0.16), (x, 0, 2.35), STONE_LIGHT, grad=(0.0, 0.7))
		p.seg((x, 0, 2.43), (x, 0, 2.85), 0.24, 0.0, STONE_DARK, sides=4, twist=45)
	for a, b in ((-L / 2 + 0.6, -0.3), (0.3, L / 2 - 0.6)):
		n = int((b - a) / 0.2)
		for k in range(n + 1):
			x = a + (b - a) * k / n
			p.seg((x, 0, 0.4), (x, 0, 2.05), 0.02, 0.02, IRON, sides=4, grad=(0.1, 0.8))
			p.seg((x, 0, 2.05), (x, 0, 2.22), 0.045, 0.0, IRON, sides=4)
		for z in (0.62, 1.85):
			p.box((b - a + 0.04, 0.06, 0.06), ((a + b) / 2, 0, z), IRON, grad=(0.1, 0.8))
		for k in range(0, n, 4):                                                # little rings under the top rail
			x = a + (b - a) * (k + 2) / n
			if x < b:
				_torus(p, (x, 0, 1.72), (1, 0, 0), (0, 0, 1), 0.08, 0.012, IRON, seg=8, ring=3)
	return p.build(bevel=0.01)


def shade_obelisk():
	"""A shade obelisk: a tapering four-sided spire of dark stone about 6.4 m
	tall on a stepped base, carved on every face with a column of faint violet
	runes and topped with a black pyramidion. Collide it as a box."""
	p = Prop("shade_obelisk", 854)
	d = Prop("shade_obelisk_runes", 855)
	p.box((2.2, 2.2, 0.4), (0, 0, 0.1), STONE_DARK, grad=(0.3, 1.0))
	p.box((1.7, 1.7, 0.35), (0, 0, 0.47), IRON, grad=(0.1, 0.8))
	p.seg((0, 0, 0.6), (0, 0, 5.6), 0.62 * 1.414, 0.36 * 1.414, STONE_DARK, sides=4, grad=(0.05, 0.95), twist=45)
	p.seg((0, 0, 5.6), (0, 0, 6.4), 0.36 * 1.414, 0.0, IRON, sides=4, grad=(0.0, 0.8), twist=45)
	for face in range(4):
		start = len(d.parts)
		for k, z in enumerate((1.4, 2.2, 3.0, 3.75, 4.45)):
			half = 0.62 + (0.36 - 0.62) * (z - 0.6) / 5.0
			_rune(d, (0, -half - 0.03, z), 0.42 - k * 0.04, k * 2 + face, glow=1.3, swatch=VIOLET)
		half = 0.62 + (0.36 - 0.62) * (5.2 - 0.6) / 5.0
		d.seg((-half * 0.7, -half - 0.03, 5.2), (half * 0.7, -half - 0.03, 5.2), 0.025, 0.025, VIOLET, sides=4, grad=(0.0, 0.3), glow=1.0)
		_move_parts(d, start, Matrix.Rotation(face * math.pi / 2, 4, "Z"))
	return join_into(p.build(bevel=0.04), [d.build()])


def moon_well():
	"""A moon well: a round well of pale stone 2.6 m across (rim 0.85 m high)
	brimming with glowing white-blue water, two stone posts carrying an iron
	arch over it with a silver crescent moon hung at its crown and a chained
	silver cup. About 3 m tall. Collide it as a box."""
	p = Prop("moon_well", 856)
	d = Prop("moon_well_water", 857)
	R = 1.3
	_lathe(p, [(R - 0.3, 0.0), (R + 0.05, 0.0), (R + 0.05, 0.7), (R + 0.15, 0.72), (R + 0.15, 0.86), (R - 0.35, 0.86), (R - 0.35, 0.5)], 16, STONE_LIGHT, grad=(0.0, 0.8))
	p.seg((0, 0, -0.1), (0, 0, 0.12), R + 0.4, R + 0.35, STONE_DARK, sides=16, grad=(0.3, 1.0))
	d.seg((0, 0, 0.3), (0, 0, 0.74), R - 0.34, R - 0.34, CLOTH_WHITE, sides=16, grad=(0.0, 0.35), glow=1.8)
	d.seg((0, 0, 0.74), (0, 0, 0.76), R - 0.6, R - 0.6, SKY, sides=16, grad=(0.0, 0.2), glow=2.2)
	for s in (-1, 1):
		p.box((0.4, 0.4, 2.2), (s * (R + 0.1), 0, 1.1), STONE_DARK, grad=(0.05, 0.9))
		p.box((0.5, 0.5, 0.15), (s * (R + 0.1), 0, 2.25), STONE_LIGHT, grad=(0.0, 0.6))
	pts = [(math.cos(math.pi * k / 10) * (R + 0.1), 0, 2.3 + math.sin(math.pi * k / 10) * 0.7) for k in range(11)]
	_chain(p, pts, 0.05, 0.05, IRON, sides=5)
	p.seg((0, 0, 3.0), (0, 0, 2.7), 0.012, 0.012, IRON, sides=3)
	_crescent(p, (0, 0, 2.45), 0.28, yaw=90, swatch=SILVER, glow=0.6)
	p.seg((0.8, -0.95, 0.86), (0.8, -0.95, 0.88), 0.05, 0.05, SILVER, sides=6)
	_lathe(p, [(0.01, 0.0), (0.05, 0.0), (0.07, 0.1), (0.06, 0.1), (0.01, 0.04)], 8, SILVER, grad=(0.0, 0.5)).data.transform(Matrix.Translation((0.95, -0.85, 0.86)))
	_rope(p, (0.8, -0.95, 0.86), (0.95, -0.85, 0.9), 0.05, r=0.01, swatch=SILVER)
	for k in range(5):
		a = k * math.tau / 5 + 0.4
		d.blob((0.07, 0.07, 0.07), (math.cos(a) * 0.5, math.sin(a) * 0.5, 1.1 + k * 0.12), CLOTH_WHITE, segs=(5, 4), grad=(0.0, 0.2), glow=2.0)
	return join_into(p.build(bevel=0.03), [d.build()])


def stalker_den():
	"""A night stalker's den: a heaped outcrop of dark blue-gray rock about
	8 x 6 m and 4.5 m tall with a low black den mouth (2.2 m wide) at its
	foot on the front (-Y), deep claw gouges raked across the rocks beside the
	mouth, a scatter of gnawed bones and a skull outside it, pale glowcaps in
	the cracks. Collide it as a mesh."""
	p = Prop("stalker_den", 858)
	d = Prop("stalker_den_detail", 859)
	rng = p.rng
	p.rock((7.6, 5.6, 3.4), (0, 0.8, 1.1), STONE_DARK, grad=(0.05, 0.9), jitter=0.06)
	p.rock((4.8, 4.0, 3.2), (-1.2, 1.3, 3.0), SEA_STONE, rot=(0, 0, 25))
	p.rock((3.4, 3.0, 2.6), (2.2, 1.0, 2.6), STONE_DARK, rot=(0, 0, -15))
	p.seg((-0.6, 1.5, 3.8), (-0.9, 1.8, 5.0), 1.2, 0.2, SEA_STONE, sides=5, jitter=0.08)
	for s in (-1, 1):                                                          # the shoulders of the mouth
		p.rock((2.4, 2.2, 2.4), (s * 2.1, -1.9, 1.0), SEA_STONE if s > 0 else STONE_DARK, rot=(0, 0, s * 20))
	p.rock((4.0, 1.8, 1.2), (0, -1.9, 2.5), STONE_DARK, rot=(0, 0, 5))          # the lintel rock
	d.blob((2.3, 1.2, 2.1), (0, -2.35, 0.8), SHADE, segs=(10, 6), grad=(0.97, 1.0))   # the black mouth
	d.blob((3.0, 1.2, 0.2), (0, -2.8, 0.02), WOOD_GRAY, segs=(8, 3), grad=(0.4, 1.0))  # trampled earth
	_claw_marks(d, (-1.5, -2.95, 1.6), -25, h=0.9, r=0.045)
	_claw_marks(d, (1.7, -2.95, 1.3), 25, h=0.8, r=0.045)
	_claw_marks(d, (-2.4, -1.9, 2.4), -50, h=0.7, r=0.04)
	for k in range(7):
		a = rng.uniform(-2.6, -0.5)
		r = rng.uniform(3.2, 4.5)
		c = Vector((math.cos(a) * r, math.sin(a) * r * 0.9, 0.05))
		t = rng.uniform(0, math.pi)
		_bone(d, tuple(c - Vector((math.cos(t), math.sin(t), 0)) * 0.3), tuple(c + Vector((math.cos(t), math.sin(t), 0)) * 0.3), r=0.035)
	_skull(d, (1.1, -3.6, 0.0), 1.3, yaw=-0.4)
	for x, y, z in ((2.9, -0.8, 2.2), (-2.8, 0.2, 2.7), (0.6, -1.6, 3.2)):
		for k in range(3):
			d.seg((x + k * 0.12, y, z), (x + k * 0.12, y, z + 0.12 + k * 0.04), 0.02, 0.02, NIGHT_LEAF, sides=4)
			d.seg((x + k * 0.12, y, z + 0.1 + k * 0.04), (x + k * 0.12, y, z + 0.16 + k * 0.04), 0.07, 0.01, SKY, sides=6, grad=(0.0, 0.3), glow=1.2)
	for k in range(6):
		a = rng.uniform(0, math.tau)
		r = rng.uniform(4.2, 5.2)
		s = rng.uniform(0.5, 1.0)
		p.rock((s, s, s * 0.7), (math.cos(a) * r, math.sin(a) * r * 0.9 + 0.5, 0.1), STONE_DARK)
	return join_into(p.build(), [d.build()])


def lampward_lamp():
	"""A Lampward lamppost, about 4.2 m: a stone foot, a tall iron post with
	collars, a scrolled bracket and a four-sided iron lantern of warm glowing
	glass on top, a little iron cap and ring. Collide it as a box."""
	p = Prop("lampward_lamp", 860)
	d = Prop("lampward_lamp_light", 861)
	p.box((0.7, 0.7, 0.4), (0, 0, 0.15), STONE_DARK, grad=(0.2, 0.9))
	p.box((0.55, 0.55, 0.1), (0, 0, 0.4), STONE_LIGHT, grad=(0.0, 0.6))
	p.seg((0, 0, 0.4), (0, 0, 0.9), 0.14, 0.08, IRON, sides=8, grad=(0.0, 0.8))
	p.seg((0, 0, 0.9), (0, 0, 3.4), 0.07, 0.06, IRON, sides=8, grad=(0.0, 0.8))
	for z in (1.0, 2.2, 3.35):
		p.seg((0, 0, z), (0, 0, z + 0.08), 0.1, 0.1, IRON, sides=8)
	for s in (-1, 1):                                                          # the scrolls under the lantern
		_chain(p, [(0, 0, 3.0), (s * 0.18, 0, 3.12), (s * 0.24, 0, 3.3), (s * 0.15, 0, 3.4)], 0.02, 0.018, IRON, sides=4)
	p.seg((0, 0, 3.42), (0, 0, 3.5), 0.2, 0.2, IRON, sides=4, twist=45)
	for k in range(4):
		a = k * math.tau / 4 + math.pi / 4
		p.seg((math.cos(a) * 0.2, math.sin(a) * 0.2, 3.5), (math.cos(a) * 0.24, math.sin(a) * 0.24, 4.0), 0.02, 0.02, IRON, sides=4)
	d.seg((0, 0, 3.5), (0, 0, 3.98), 0.25, 0.3, FLAME, sides=4, grad=(0.0, 0.5), glow=1.8, twist=45)
	p.seg((0, 0, 3.98), (0, 0, 4.2), 0.32, 0.05, IRON, sides=4, grad=(0.0, 0.7), twist=45)
	_torus(p, (0, 0, 4.3), (1, 0, 0), (0, 0, 1), 0.07, 0.015, IRON, seg=8, ring=3)
	return join_into(p.build(bevel=0.01), [d.build()])


# ---- Barrowhold

def barrowhold_gate():
	"""Barrowhold's gate, 18 m wide: two square towers of dark stone faced with
	glossy black obsidian (5 x 6 m, 13.5 m to their silver-capped merlons),
	a round arch 8 m wide and 8.5 m to its crown between them with a span to
	11 m above, silver bands and trim, Timiraj's eclipse (a black disc in a
	silver ring) over the arch, the black gate leaves standing open against
	the passage walls, and two silver moon-lamps on posts before it. Faces -Y.
	Collide it as a mesh: the passage is walkable."""
	p = Prop("barrowhold_gate", 870)
	o = Prop("barrowhold_gate_glass", 871)
	d = Prop("barrowhold_gate_detail", 872)
	hw, zc, TD = 4.0, 4.5, 6.0
	TH = 12.4
	for s in (-1, 1):
		x = s * (hw + 2.5)
		p.box((5.4, TD + 0.4, 0.8), (x, 0, 0.2), STONE_DARK, grad=(0.3, 1.0))
		p.box((5.0, TD, TH), (x, 0, TH / 2), STONE_DARK, grad=(0.05, 0.95))
		o.box((3.2, 0.2, 8.0), (x, -TD / 2 - 0.08, 5.2), OBSIDIAN, grad=(0.0, 0.7))     # the obsidian facing
		o.box((0.2, 3.6, 8.0), (s * (hw + 5.08), 0, 5.2), OBSIDIAN, grad=(0.0, 0.7))
		for z in (1.0, 9.6):
			d.box((5.3, TD + 0.3, 0.3), (x, 0, z), SILVER, grad=(0.0, 0.5))
		d.box((5.6, TD + 0.6, 0.4), (x, 0, TH + 0.2), STONE_LIGHT, grad=(0.0, 0.6))
		for k in range(3):                                                    # merlons, silver-capped
			for yy in (-TD / 2 + 0.3, TD / 2 - 0.3):
				mx = x - 1.9 + k * 1.9
				p.box((0.9, 0.6, 1.1), (mx, yy, TH + 0.95), STONE_DARK, grad=(0.0, 0.8))
				d.box((1.0, 0.7, 0.14), (mx, yy, TH + 1.55), SILVER, grad=(0.0, 0.5))
		d.box((0.3, 0.14, 2.2), (x, -TD / 2 - 0.2, 10.9), VIOLET, grad=(0.1, 0.5), glow=1.2)   # a violet-lit slit high on each tower
		p.box((0.25, 3.6, 7.2), (s * (hw - 0.14), 0.9, 3.6), IRON, grad=(0.1, 0.9))
		for z in (1.4, 3.6, 5.8):
			d.box((0.1, 3.7, 0.2), (s * (hw - 0.3), 0.9, z), SILVER, grad=(0.0, 0.5))
	# the arch and the span over it
	_arch_ring(p, -TD / 2, TD / 2, zc, hw, hw + 1.0, n=11, swatches=(STONE_DARK, IRON))
	_vault(p, hw + 1.0, zc, -TD / 2, TD / 2, 11.0, n=14, swatch=STONE_DARK)
	for s in (-1, 1):
		p.box((1.0, TD, zc), (s * (hw + 0.5), 0, zc / 2), STONE_DARK, grad=(0.05, 0.9))
	d.box((2 * hw + 2.2, TD + 0.3, 0.3), (0, 0, 11.0), SILVER, grad=(0.0, 0.5))
	for k in range(4):
		mx = -2.85 + k * 1.9
		for yy in (-TD / 2 + 0.3, TD / 2 - 0.3):
			p.box((0.9, 0.6, 1.0), (mx, yy, 11.65), STONE_DARK, grad=(0.0, 0.8))
			d.box((1.0, 0.7, 0.14), (mx, yy, 12.2), SILVER, grad=(0.0, 0.5))
	# silver trim round the arch's face
	for k in range(12):
		a0, a1 = math.pi * k / 12, math.pi * (k + 1) / 12
		r = hw + 1.05
		d.seg((math.cos(a0) * r, -TD / 2 - 0.08, zc + math.sin(a0) * r), (math.cos(a1) * r, -TD / 2 - 0.08, zc + math.sin(a1) * r), 0.09, 0.09, SILVER, sides=4)
	# the eclipse over the arch
	ez = 9.8
	d.seg((0, -TD / 2 - 0.02, ez), (0, -TD / 2 - 0.16, ez), 0.95, 0.95, SILVER, sides=20, grad=(0.0, 0.5), glow=0.5)
	d.seg((0, -TD / 2 - 0.16, ez), (0, -TD / 2 - 0.26, ez), 0.78, 0.78, OBSIDIAN, sides=20, grad=(0.6, 1.0))
	for k in range(12):
		a = k * math.tau / 12
		ln = 1.5 if k % 2 == 0 else 1.25
		d.seg((math.cos(a) * 0.9, -TD / 2 - 0.1, ez + math.sin(a) * 0.9), (math.cos(a) * ln, -TD / 2 - 0.1, ez + math.sin(a) * ln), 0.08, 0.0, VIOLET if k % 2 else GOLD, sides=4, grad=(0.0, 0.3), glow=1.4)
	# moon-lamps before the gate
	for s in (-1, 1):
		lx, ly = s * 5.2, -TD / 2 - 0.9
		p.box((0.6, 0.6, 0.3), (lx, ly, 0.15), STONE_LIGHT, grad=(0.0, 0.7))
		p.seg((lx, ly, 0.3), (lx, ly, 3.4), 0.1, 0.08, SILVER, sides=8, grad=(0.0, 0.6))
		_moon_globe(d, (lx, ly, 3.75), r=0.32)
	o = _glossy(o.build(bevel=0.02), 0.15)
	return _merge_materials(join_into(p.build(bevel=0.05), [o, d.build()]))


def _seated_god(p, d, c, S, stone=OBSIDIAN):
	"""Timiraj seated in meditation at c (the seat top), S = 1 about 2.6 m
	tall: an elephant-headed figure, legs crossed, hands resting in the lap,
	ears laid back, trunk curled down to the hands, eyes closed (silver lines),
	facing -Y."""
	x, y, z = c
	def at(u, v, w):
		return (x + u * S, y + v * S, z + w * S)
	p.blob((1.9 * S, 1.2 * S, 0.6 * S), at(0, 0, 0.22), stone, segs=(12, 6), grad=(0.0, 0.8))              # crossed legs
	for s in (-1, 1):
		p.blob((0.95 * S, 0.55 * S, 0.45 * S), at(s * 0.42, -0.35, 0.28), stone, rot=(0, 0, s * 25), segs=(10, 6), grad=(0.0, 0.8))
		p.blob((0.3 * S, 0.4 * S, 0.2 * S), at(s * 0.1, -0.52, 0.22), stone, segs=(6, 4))               # the feet on the knees
	p.blob((1.3 * S, 0.95 * S, 1.3 * S), at(0, 0.05, 1.0), stone, segs=(12, 8), grad=(0.0, 0.8))             # the belly and chest
	p.blob((1.5 * S, 0.9 * S, 0.5 * S), at(0, 0.08, 1.55), stone, segs=(12, 6), grad=(0.0, 0.7))             # shoulders
	for s in (-1, 1):
		_chain(p, [at(s * 0.68, 0.05, 1.5), at(s * 0.78, -0.05, 1.05), at(s * 0.45, -0.35, 0.72), at(s * 0.12, -0.45, 0.62)], 0.2 * S, 0.14 * S, stone, sides=7, grad=(0.0, 0.8))
	p.blob((0.55 * S, 0.4 * S, 0.22 * S), at(0, -0.45, 0.62), stone, segs=(8, 5))                          # the hands in the lap
	p.blob((0.95 * S, 0.9 * S, 0.95 * S), at(0, -0.05, 2.02), stone, segs=(12, 8), grad=(0.0, 0.7))          # the head
	p.blob((0.7 * S, 0.4 * S, 0.3 * S), at(0, -0.32, 2.3), stone, segs=(8, 5))                              # brow
	for s in (-1, 1):
		p.blob((0.9 * S, 0.16 * S, 1.05 * S), at(s * 0.62, 0.15, 1.95), stone, rot=(0, s * 10, s * -30), segs=(10, 6), grad=(0.0, 0.8))   # ears laid back
		d.seg(at(s * 0.3, -0.48, 2.12), at(s * 0.14, -0.49, 2.1), 0.022 * S, 0.018 * S, SILVER, sides=4, glow=0.4)                          # closed eyes
		p.seg(at(s * 0.22, -0.35, 1.8), at(s * 0.35, -0.6, 1.62), 0.07 * S, 0.02 * S, stone, sides=6)                                    # short tusks
	_chain(p, [at(0, -0.38, 1.9), at(0, -0.52, 1.5), at(0, -0.55, 1.1), at(0.05, -0.55, 0.8), at(0.18, -0.48, 0.72)], 0.2 * S, 0.08 * S, stone, sides=8, grad=(0.0, 0.8))
	d.blob((0.2 * S, 0.1 * S, 0.2 * S), at(0, -0.44, 2.36), SILVER, segs=(6, 4), glow=0.6)                    # a silver mark on the brow


def timiraj_shrine():
	"""Barrowhold's bindstone: Timiraj the Unlit, a black glossy stone elephant
	god seated calm in meditation, eyes closed, on a pedestal at the back of a
	two-stepped round dais 12 m across (0.8 m high), a great eclipse ring
	behind him (a black disc 7.6 m across in a glowing silver corona, its
	center 7.8 m up, on a stone stand), four silver moon-lamps on posts round
	the dais and a small bindstone plinth in front (-Y) with a black stone set
	in silver. About 12 m to the top of the corona. Collide it as a mesh."""
	p = Prop("timiraj_shrine", 874)
	g = Prop("timiraj_shrine_glass", 875)
	d = Prop("timiraj_shrine_detail", 876)
	for k, (r, z0, z1, sw) in enumerate(((6.0, -0.2, 0.4, STONE_DARK), (5.0, 0.4, 0.8, STONE_LIGHT))):
		p.seg((0, 0, z0), (0, 0, z1), r, r - 0.05, sw, sides=24, grad=(0.1, 0.9))
		d.seg((0, 0, z1 - 0.12), (0, 0, z1 - 0.04), r + 0.04, r + 0.04, VIOLET if k else SILVER, sides=24, grad=(0.1, 0.5), glow=0.5 if k else 0.0)
	P = 0.8
	for k in range(3):                                                        # silver rings inlaid in the floor
		d.seg((0, 0, P - 0.02), (0, 0, P + 0.006 + k * 0.004), 4.2 - k * 1.1, 4.2 - k * 1.1, (SILVER, STONE_DARK, SILVER)[k], sides=32, grad=(0.0, 0.6))
	# the pedestal and the god
	cy = 1.6
	p.box((4.0, 3.2, 1.1), (0, cy, P + 0.55), STONE_DARK, grad=(0.05, 0.9))
	p.box((4.3, 3.5, 0.2), (0, cy, P + 1.2), STONE_LIGHT, grad=(0.0, 0.6))
	d.box((4.02, 0.05, 0.14), (0, cy - 1.62, P + 0.8), SILVER, grad=(0.0, 0.5))
	p.seg((0, cy, P + 1.3), (0, cy, P + 1.55), 1.6, 1.5, STONE_DARK, sides=16, grad=(0.1, 0.8))       # the lotus cushion
	for k in range(12):
		a = k * math.tau / 12
		p.blob((0.7, 0.35, 0.3), (math.cos(a) * 1.45, cy + math.sin(a) * 1.3, P + 1.45), STONE_DARK, rot=(0, 0, math.degrees(a)), segs=(6, 4))
	_seated_god(g, d, (0, cy + 0.2, P + 1.55), 2.2)
	# the eclipse ring behind him
	EZ, ER, EY = 7.8, 3.8, cy + 2.6
	p.box((1.2, 1.0, EZ - ER + 0.4 - P), (0, EY + 0.3, (P + EZ - ER + 0.4) / 2), STONE_DARK, grad=(0.05, 0.9))
	p.box((2.6, 1.6, 0.6), (0, EY + 0.3, P + 0.3), STONE_LIGHT, grad=(0.0, 0.7))
	g.seg((0, EY, EZ), (0, EY + 0.5, EZ), ER, ER, OBSIDIAN, sides=36, grad=(0.5, 1.0))
	d.seg((0, EY + 0.1, EZ), (0, EY + 0.45, EZ), ER + 0.35, ER + 0.35, SILVER, sides=36, grad=(0.0, 0.4), glow=1.6)   # the corona's bright rim, showing round the disc's edge
	for k in range(24):                                                       # corona flames
		a = k * math.tau / 24
		ln = ER + (1.8 if k % 2 == 0 else 1.1) + (0.5 if k % 6 == 0 else 0.0)
		sw = (SILVER, VIOLET, GOLD)[k % 3]
		d.seg((math.cos(a) * (ER + 0.2), EY + 0.05, EZ + math.sin(a) * (ER + 0.2)), (math.cos(a + 0.05) * ln, EY + 0.05, EZ + math.sin(a + 0.05) * ln), 0.28 if k % 2 == 0 else 0.2, 0.0, sw, sides=4, grad=(0.0, 0.35), glow=1.5)
	# the silver lamps
	for k in range(4):
		a = math.radians(-135 + 90 * k)
		x, y = math.cos(a) * 4.3, math.sin(a) * 4.3
		p.box((0.55, 0.55, 0.25), (x, y, P + 0.12), STONE_LIGHT, grad=(0.0, 0.7))
		p.seg((x, y, P + 0.25), (x, y, P + 2.4), 0.08, 0.07, SILVER, sides=8, grad=(0.0, 0.6))
		_moon_globe(d, (x, y, P + 2.7), r=0.26)
	# the bindstone plinth in front
	by = -3.7
	p.box((1.2, 1.0, 0.9), (0, by, P + 0.45), STONE_DARK, grad=(0.05, 0.9))
	p.box((1.4, 1.2, 0.14), (0, by, P + 0.95), STONE_LIGHT, grad=(0.0, 0.6))
	d.seg((0, by, P + 1.0), (0, by, P + 1.1), 0.36, 0.3, SILVER, sides=12, grad=(0.0, 0.6))
	g.blob((0.5, 0.5, 0.42), (0, by, P + 1.3), OBSIDIAN, segs=(10, 6), grad=(0.3, 1.0))
	d.box((1.0, 0.04, 0.3), (0, by - 0.52, P + 0.55), VIOLET, grad=(0.1, 0.5), glow=0.8)
	p.box((3.0, 1.0, 0.4), (0, -6.3, 0.2), STONE_LIGHT, grad=(0.0, 0.7))
	g = _glossy(g.build(bevel=0.02), 0.12)
	return join_into(p.build(bevel=0.05), [g, d.build()])


def black_sun():
	"""The eclipse over Barrowhold: a black disc 40 m across hung 110 m up
	(its center over the prop's origin), tilted to face south (-Y in Blender,
	+Z in Godot) and 30 degrees down toward the streets, in a glowing corona:
	a pale gold rim, long violet and gold flames and a faint see-through halo.
	Nothing comes near the ground. Collide it as none."""
	p = Prop("black_sun", 878)
	d = Prop("black_sun_corona", 879)
	h = Prop("black_sun_halo", 880)
	rng = p.rng
	R = 20.0
	p.seg((0, 0.3, 0), (0, 1.2, 0), R, R, IRON, sides=48, grad=(0.95, 1.0))
	p.seg((0, -0.4, 0), (0, 0.3, 0), R - 0.2, R - 0.2, IRON, sides=48, grad=(0.95, 1.0))
	d.seg((0, 0.4, 0), (0, 0.9, 0), R + 0.9, R + 0.9, PETAL_YELLOW, sides=48, grad=(0.0, 0.2), glow=3.0)   # the bright rim, a ring showing round the disc
	d.seg((0, 0.9, 0), (0, 1.1, 0), R + 1.6, R + 1.6, VIOLET, sides=48, grad=(0.0, 0.3), glow=2.2)
	for k in range(40):
		a = k * math.tau / 40 + rng.uniform(-0.03, 0.03)
		ln = R + rng.uniform(3.0, 7.0) + (5.0 if k % 5 == 0 else 0.0)
		w = rng.uniform(1.2, 2.2)
		sw = VIOLET if k % 2 else GOLD
		b = a + rng.uniform(-0.06, 0.06)
		t = Vector((-math.sin(a), math.cos(a))) * w
		r0 = Vector((math.cos(a), math.sin(a))) * (R + 0.5)
		_plate(d, [tuple(r0 - t), tuple(r0 + t), (math.cos(b) * ln, math.sin(b) * ln)], 1.0, 0.2, sw, grad=(0.0, 0.4), glow=2.4)
	for k in range(3):                                                        # the faint halo
		r = R + 4.0 + k * 3.5
		h.seg((0, 1.4 + k * 0.2, 0), (0, 1.5 + k * 0.2, 0), r, r, VIOLET if k != 1 else CLOTH_WHITE, sides=48, grad=(0.0, 0.3), glow=1.2)
	halo = _translucent(h.build(), 0.18, 0.9)
	obj = join_into(p.build(), [d.build(), halo])
	obj.data.transform(Matrix.Translation((0, 0, 110.0)) @ Matrix.Rotation(math.radians(30), 4, "X"))
	return obj


def obsidian_tower():
	"""A slender tower of glossy black obsidian, about 23.5 m: an octagonal
	shaft 4 m across tapering upward on a dark stone plinth, silver bands,
	a door on the front (-Y) in a silver frame, narrow windows lit violet up
	its faces, a crenellated silver-capped gallery at 17 m and a silver spire
	to its tip. Collide it as a mesh."""
	p = Prop("obsidian_tower", 882)
	o = Prop("obsidian_tower_glass", 883)
	d = Prop("obsidian_tower_detail", 884)
	c8 = math.cos(math.pi / 8)
	p.seg((0, 0, -0.3), (0, 0, 0.8), 3.0 / c8, 2.9 / c8, STONE_DARK, sides=8, grad=(0.2, 1.0), twist=22.5)
	o.seg((0, 0, 0.8), (0, 0, 16.6), 2.1 / c8, 1.6 / c8, OBSIDIAN, sides=8, grad=(0.0, 0.9), twist=22.5)
	for z in (0.8, 6.0, 11.0):
		r = 2.1 + (1.6 - 2.1) * (z - 0.8) / 15.8
		d.seg((0, 0, z), (0, 0, z + 0.25), r / c8 + 0.08, r / c8 + 0.06, SILVER, sides=8, grad=(0.0, 0.5), twist=22.5)
	p.seg((0, 0, 16.4), (0, 0, 17.2), 1.7 / c8, 2.2 / c8, STONE_DARK, sides=8, grad=(0.0, 0.8), twist=22.5)   # the gallery's corbel
	p.seg((0, 0, 17.2), (0, 0, 17.5), 2.25 / c8, 2.25 / c8, STONE_DARK, sides=8, twist=22.5)
	for k in range(8):
		a = k * math.tau / 8
		p.box((0.7, 0.5, 0.9), (math.cos(a) * 1.95, math.sin(a) * 1.95, 17.95), STONE_DARK, rot=(0, 0, math.degrees(a) + 90), grad=(0.0, 0.8))
		d.box((0.8, 0.6, 0.12), (math.cos(a) * 1.95, math.sin(a) * 1.95, 18.45), SILVER, rot=(0, 0, math.degrees(a) + 90), grad=(0.0, 0.5))
	o.seg((0, 0, 17.5), (0, 0, 19.6), 1.3, 1.2, OBSIDIAN, sides=8, grad=(0.0, 0.8), twist=22.5)
	p.seg((0, 0, 19.6), (0, 0, 23.6), 1.35, 0.03, SILVER, sides=8, grad=(0.0, 0.7), twist=22.5)
	d.blob((0.3, 0.3, 0.3), (0, 0, 21.2), VIOLET, segs=(6, 4), glow=1.6)
	_crescent(d, (0, 0, 23.9), 0.4, yaw=90, swatch=SILVER)
	for k, (deg, z, h) in enumerate(((-90, 5.0, 1.8), (-45, 9.4, 1.8), (45, 7.2, 1.8), (135, 12.2, 1.8), (-135, 3.6, 1.6), (90, 13.8, 1.6), (-90, 14.2, 1.6), (180, 9.0, 1.8))):
		r = (2.1 + (1.6 - 2.1) * (z - 0.8) / 15.8)
		a = math.radians(deg)
		_lancet(d, (math.cos(a) * (r + 0.02), math.sin(a) * (r + 0.02), z), 0.5, h, yaw=deg + 90, pane=VIOLET, glow=1.4, frame=SILVER, bars=False)
	_lancet(d, (0, -2.12, 0.8), 1.4, 2.8, pane=IRON, glow=0.0, frame=SILVER, bars=False)   # the door
	d.seg((0.35, -2.2, 2.0), (0.35, -2.24, 2.0), 0.07, 0.07, SILVER, sides=6)
	p.box((2.4, 1.0, 0.3), (0, -3.2, 0.1), STONE_LIGHT, grad=(0.0, 0.7))
	o = _glossy(o.build(bevel=0.02), 0.12)
	return join_into(p.build(bevel=0.04), [o, d.build()])


def observatory():
	"""The astronomers' observatory: a round drum of dark stone 13 m across
	and 6.5 m tall (silver bands, buttresses, a door on the front, -Y) under
	a dome with its slit thrown open toward the front, and a great brass
	telescope inside tilted up through the slit toward the black sun (its
	mouth about 15.5 m up), its eyepiece and a gallery rail on the roof round
	the dome. About 16 m tall. Collide it as a mesh."""
	p = Prop("observatory", 886)
	d = Prop("observatory_detail", 887)
	R, H = 6.5, 6.5
	AP = R * math.cos(math.pi / 24)                                           # the drum's apothem
	p.seg((0, 0, -0.3), (0, 0, 0.5), R + 0.9, R + 0.8, STONE_DARK, sides=24, grad=(0.3, 1.0))
	p.seg((0, 0, 0.5), (0, 0, H), R, R, STONE_DARK, sides=24, grad=(0.05, 0.95))
	for z in (0.5, 3.4):
		d.seg((0, 0, z), (0, 0, z + 0.2), R + 0.06, R + 0.06, SILVER, sides=24, grad=(0.0, 0.5))
	p.seg((0, 0, H), (0, 0, H + 0.5), R + 0.5, R + 0.5, STONE_LIGHT, sides=24, grad=(0.0, 0.7))           # the roof cornice
	for k in range(8):                                                         # buttresses
		a = k * math.tau / 8 + math.pi / 8
		p.box((1.4, 0.9, H - 0.6), (math.cos(a) * (R + 0.4), math.sin(a) * (R + 0.4), (H - 0.6) / 2 + 0.4), STONE_DARK, rot=(0, 0, math.degrees(a)), grad=(0.05, 0.9))
		d.seg((math.cos(a) * (R + 0.4), math.sin(a) * (R + 0.4), H - 0.2), (math.cos(a) * (R + 0.4), math.sin(a) * (R + 0.4), H + 1.1), 0.08, 0.0, SILVER, sides=4)
	for k in range(6):                                                         # small violet windows
		a = math.radians((-45, 0, 45, 135, 180, 225)[k])
		_lancet(d, (math.cos(a) * (AP + 0.02), math.sin(a) * (AP + 0.02), 3.9), 0.7, 1.6, yaw=math.degrees(a) + 90, pane=VIOLET, glow=1.2, frame=SILVER, bars=False)
	_lancet(d, (0, -AP - 0.02, 0.5), 1.6, 3.0, pane=WOOD_GRAY, glow=0.0, frame=SILVER, bars=False)          # the door
	for k in range(3):
		p.box((3.0 - k * 0.3, 0.6, 0.2), (0, -R - 0.7 - (2 - k) * 0.5, 0.1 + k * 0.15 - 0.2), STONE_LIGHT, grad=(0.0, 0.7))
	# the dome: gores round Z, the two facing the front left open for the slit
	DR, DZ = R - 0.4, H + 0.5
	n = 20
	for i in range(n):
		a0, a1 = i * math.tau / n, (i + 1) * math.tau / n
		mid = (a0 + a1) / 2
		if abs(((mid + math.pi / 2 + math.pi) % math.tau) - math.pi) < math.tau / n * 1.05:
			continue
		ma = [(math.cos(a0) * DR * math.cos(ph), math.sin(a0) * DR * math.cos(ph), DZ + DR * math.sin(ph)) for ph in [math.pi / 2 * j / 6 for j in range(7)]]
		mb = [(math.cos(a1) * DR * math.cos(ph), math.sin(a1) * DR * math.cos(ph), DZ + DR * math.sin(ph)) for ph in [math.pi / 2 * j / 6 for j in range(7)]]
		_slab(p, ma, mb, 0.3, (SEA_STONE, STONE_LIGHT)[i % 2], grad=(0.0, 0.8))
	for s in (-1, 1):                                                          # the slit's shutters rolled aside
		a = -math.pi / 2 + s * math.tau / n * 1.05
		pts = [(math.cos(a) * (DR + 0.12) * math.cos(ph), math.sin(a) * (DR + 0.12) * math.cos(ph), DZ + (DR + 0.12) * math.sin(ph)) for ph in [math.pi / 2 * j / 6 for j in range(7)]]
		_chain(d, pts, 0.12, 0.12, SILVER, sides=5)
	d.seg((0, 0, DZ + DR - 0.2), (0, 0, DZ + DR + 0.5), 0.5, 0.15, SILVER, sides=8, grad=(0.0, 0.5))
	p.seg((0, 0, DZ - 0.2), (0, 0, DZ + 0.02), DR, DR, STONE_DARK, sides=24, grad=(0.3, 1.0))              # the floor under the dome
	# the telescope: pointing forward (-Y) and up through the slit
	piv = Vector((0, 0.6, DZ + 1.5))
	aim = Vector((0, -math.cos(math.radians(58)), math.sin(math.radians(58))))
	p.box((1.8, 1.8, 1.4), (0, 0.6, DZ + 0.5), STONE_DARK, grad=(0.1, 0.9))
	p.seg(tuple(piv - Vector((0, 0, 1.0))), tuple(piv), 0.4, 0.35, COPPER, sides=8, grad=(0.0, 0.7))
	for s in (-1, 1):
		p.box((0.2, 0.6, 1.3), (s * 0.75, 0.6, DZ + 1.6), COPPER, grad=(0.0, 0.7))
	back, mouth = piv - aim * 2.6, piv + aim * 7.4
	p.seg(tuple(back), tuple(piv), 0.5, 0.58, COPPER, sides=12, grad=(0.0, 0.7))
	p.seg(tuple(piv), tuple(mouth), 0.58, 0.72, COPPER, sides=12, grad=(0.0, 0.7))
	for t in (0.0, 0.35, 0.7, 1.0):
		q = piv.lerp(mouth, t)
		p.seg(tuple(q - aim * 0.12), tuple(q + aim * 0.12), 0.62 + 0.14 * t + 0.06, 0.62 + 0.14 * t + 0.06, GOLD, sides=12, grad=(0.0, 0.5))
	d.seg(tuple(mouth), tuple(mouth + aim * 0.05), 0.66, 0.66, SKY, sides=12, grad=(0.0, 0.3), glow=0.6)      # the lens catching the light
	d.seg(tuple(back), tuple(back - aim * 0.5), 0.12, 0.08, COPPER, sides=6)
	_chain(d, [tuple(piv + aim * 1.0 + Vector((0.55, 0, 0))), tuple(piv + aim * 2.2 + Vector((0.75, 0, 0.1)))], 0.14, 0.14, GOLD, sides=8)   # the finder scope
	# a rail round the roof
	for k in range(24):
		a0, a1 = k * math.tau / 24, (k + 1) * math.tau / 24
		d.seg((math.cos(a0) * (R + 0.35), math.sin(a0) * (R + 0.35), H + 1.4), (math.cos(a1) * (R + 0.35), math.sin(a1) * (R + 0.35), H + 1.4), 0.04, 0.04, SILVER, sides=4)
		d.seg((math.cos(a0) * (R + 0.35), math.sin(a0) * (R + 0.35), H + 0.5), (math.cos(a0) * (R + 0.35), math.sin(a0) * (R + 0.35), H + 1.4), 0.03, 0.03, SILVER, sides=4)
	return join_into(p.build(bevel=0.04), [d.build()])


def eclipse_house():
	"""A Barrowhold townhouse, 6 x 6 m: two storeys of KayKit stone repainted
	dark (walls 6 m), a silver band between the floors, lancet windows lit
	violet on every face, the door in the front (-Y) under a silver lintel, a
	steep dark slate roof ridged front to back (to 10.5 m) with a round window
	in its front gable holding a silver crescent, and a chimney. About
	7 x 7 m. Collide it as a mesh."""
	p = Prop("eclipse_house", 890)
	half, RH = 3.0, 3.0
	pieces = []
	kinds_ = {0: lambda r, k: ("wall_doorway" if k == 1 else "wall_window_open") if r == 0 else "wall",
			  1: lambda r, k: "wall_window_open" if (r == 0 and k == 0) else "wall",
			  2: lambda r, k: "wall",
			  3: lambda r, k: "wall_window_open" if (r == 0 and k == 0) else "wall"}
	_kaykit_box(pieces, -half, -half, half, half, 0.0, 2, RH, kinds=lambda s, r, k: kinds_[s](r, k))
	for x in (-1.5, 1.5):
		for y in (-1.5, 1.5):
			pieces += kaykit("floor_tile_large", (x, y, -0.07))
	p.box((2 * half - 0.6, 2 * half - 0.6, 6.0), (0, 0, 3.0), STONE_DARK, grad=(0.3, 1.0))                 # the solid core
	p.box((1.7, 0.1, 1.7), (-1.5, -half + 0.2, 1.6), VIOLET, grad=(0.2, 0.6), glow=1.4)                    # panes in the open windows
	p.box((0.1, 1.7, 1.7), (half - 0.2, -1.5, 1.6), VIOLET, grad=(0.2, 0.6), glow=1.4)
	p.box((0.1, 1.7, 1.7), (-half + 0.2, 1.5, 1.6), VIOLET, grad=(0.2, 0.6), glow=1.4)
	F = -0.42
	for x in (-1.5, 1.5):
		_lancet(p, (x, -half + F, 3.5), 0.8, 2.0, pane=VIOLET, glow=1.4, frame=SILVER)
		_lancet(p, (x, half - F, 3.5), 0.8, 2.0, yaw=180, pane=VIOLET, glow=1.4, frame=SILVER)
	for s in (-1, 1):
		_lancet(p, (s * (half - F), 1.5 * s, 3.5), 0.8, 2.0, yaw=90 * s, pane=VIOLET, glow=1.4, frame=SILVER)
	p.box((2 * half + 1.0, 2 * half + 1.0, 0.22), (0, 0, 3.0), SILVER, grad=(0.0, 0.5))                     # the band between floors
	p.box((2 * half + 1.1, 2 * half + 1.1, 0.25), (0, 0, 6.05), STONE_LIGHT, grad=(0.0, 0.6))
	p.box((1.9, 0.5, 0.22), (1.5, -half - 0.35, 2.85), SILVER, grad=(0.0, 0.5))                            # silver lintel over the door
	_steep_roof(p, (0, 0), 2 * half + 0.6, 2 * half + 0.6, 6.15, 4.4, slate=IRON, wall=STONE_DARK)
	GY = -half - 0.3
	p.seg((0, GY, 8.1), (0, GY - 0.1, 8.1), 0.62, 0.62, SILVER, sides=14, grad=(0.0, 0.5))                  # the round gable window
	p.seg((0, GY - 0.1, 8.1), (0, GY - 0.14, 8.1), 0.48, 0.48, VIOLET, sides=14, grad=(0.1, 0.5), glow=1.4)
	_crescent(p, (0, GY - 0.2, 8.1), 0.36, yaw=90, swatch=SILVER)
	cx, cy = 1.6, 1.6
	p.box((0.9, 0.9, 3.6), (cx, cy, 9.2), STONE_DARK, grad=(0.1, 0.9))
	p.box((1.1, 1.1, 0.2), (cx, cy, 11.05), SILVER, grad=(0.0, 0.5))
	p.seg((0.4, -half - 0.4, 2.2), (0.4, -half - 0.9, 2.2), 0.04, 0.04, SILVER, sides=4)
	_moon_globe(p, (0.4, -half - 0.9, 1.95), r=0.16, glow=1.8)
	obj = p.build(bevel=0.04)
	return _merge_materials(join_into(obj, _restone(pieces, NIGHT_STONE)))


def moon_lamp():
	"""A Barrowhold moon-lamp, about 4.2 m: a stepped stone foot, a fluted
	silver post with collars, a silver crescent moon on the post's neck and a
	pale moon-white glass globe on top. Collide it as a box."""
	p = Prop("moon_lamp", 892)
	d = Prop("moon_lamp_globe", 893)
	p.box((0.8, 0.8, 0.3), (0, 0, 0.1), STONE_DARK, grad=(0.2, 0.9))
	p.box((0.6, 0.6, 0.25), (0, 0, 0.35), STONE_LIGHT, grad=(0.0, 0.7))
	p.seg((0, 0, 0.45), (0, 0, 0.8), 0.18, 0.1, SILVER, sides=8, grad=(0.0, 0.6))
	p.seg((0, 0, 0.8), (0, 0, 3.4), 0.075, 0.065, SILVER, sides=8, grad=(0.0, 0.6))
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.07, math.sin(a) * 0.07, 0.9), (math.cos(a) * 0.063, math.sin(a) * 0.063, 3.3), 0.015, 0.015, STONE_LIGHT, sides=3)
	for z in (1.1, 2.3, 3.3):
		p.seg((0, 0, z), (0, 0, z + 0.08), 0.11, 0.11, IRON if z < 3 else SILVER, sides=8)
	_crescent(p, (0, 0, 3.05), 0.34, yaw=90, swatch=SILVER)
	_crescent(p, (0, 0, 3.05), 0.34, yaw=-90, swatch=SILVER)
	_moon_globe(d, (0, 0, 3.85), r=0.3)
	return join_into(p.build(bevel=0.01), [d.build()])


def eclipse_wall():
	"""A 10 m run of Barrowhold's city wall along X (x -5.05..5.05, so runs
	placed 10 m apart meet), 2.4 m thick and 6 m to the wall-walk: dark stone
	on a battered footing, a silver band, pilasters at its ends, a parapet of
	merlons capped in silver (to 7.2 m) and a violet-lit arrow slit on each
	side. Faces -Y (the same outside and in). Collide it as a box."""
	p = Prop("eclipse_wall", 894)
	d = Prop("eclipse_wall_detail", 895)
	L, T, H = 10.1, 2.4, 6.0
	p.box((L, T + 0.6, 1.0), (0, 0, 0.3), STONE_DARK, grad=(0.3, 1.0))
	p.box((L, T, H - 0.8), (0, 0, 0.8 + (H - 0.8) / 2), STONE_DARK, grad=(0.05, 0.95))
	for s in (-1, 1):
		d.box((L, 0.1, 0.22), (0, s * (T / 2 + 0.04), 3.6), SILVER, grad=(0.0, 0.5))
		d.box((L, 0.2, 0.26), (0, s * (T / 2 + 0.05), H - 0.05), STONE_LIGHT, grad=(0.0, 0.6))
		for x in (-L / 2 + 0.45, L / 2 - 0.45):
			p.box((0.9, 0.5, H - 0.4), (x, s * (T / 2 + 0.2), (H - 0.4) / 2 + 0.2), STONE_DARK, grad=(0.05, 0.9))
		d.box((0.2, 0.1, 1.2), (0, s * (T / 2 + 0.02), 2.2), VIOLET, grad=(0.1, 0.5), glow=1.0)
		for k in range(5):                                                     # merlons
			mx = -4.0 + k * 2.0
			p.box((1.1, 0.6, 1.0), (mx, s * (T / 2 - 0.3), H + 0.5), STONE_DARK, grad=(0.0, 0.8))
			d.box((1.2, 0.7, 0.14), (mx, s * (T / 2 - 0.3), H + 1.07), SILVER, grad=(0.0, 0.5))
	return join_into(p.build(bevel=0.04), [d.build()])


# ===== The Boneyard, part 2: Lastwalk, Timiraj's Table

WAR_STONE = STONE_WARM      # Lastwalk's petrified gray-brown stone
WAR_DARK = WOOD_GRAY        # its weathered, darker brown-gray
TARNISH = BAMBOO            # tarnished gold, browning toward the base
STARLIGHT = CLOTH_WHITE     # star-white shading to pale blue


def _frame(o, u, w):
	"""A matrix placing a part built along +Z at o, its X along u and its Z along w."""
	u, w = Vector(u).normalized(), Vector(w).normalized()
	u = (u - w * u.dot(w)).normalized()
	v = w.cross(u)
	m = Matrix((u, v, w)).transposed().to_4x4()
	return Matrix.Translation(Vector(o)) @ m


def _prism(p, sec0, z0, sec1, z1, swatch, grad=(0.1, 0.8), glow=0.0):
	"""A closed prism along Z from the cross-section sec0 [(x, y)] at z0 to sec1
	at z1 (sec1 None: it closes to a point on the axis, a blade's tip)."""
	n = len(sec0)
	verts = [(x, y, z0) for x, y in sec0]
	faces = [tuple(range(n))]
	if sec1 is None:
		verts.append((0.0, 0.0, z1))
		faces += [(i, (i + 1) % n, n) for i in range(n)]
	else:
		verts += [(x, y, z1) for x, y in sec1]
		faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
		faces.append(tuple(range(n, 2 * n)))
	obj = p.poly(verts, faces, swatch, grad)
	if glow:
		obj.data.materials[0] = atlas_material(glow)
	return obj


def _blade_sec(w, t, e=0.14):
	"""A flat hexagonal blade section, w wide and t thick, its edges beveled."""
	b = w * e
	return [(-w / 2, 0.0), (-w / 2 + b, -t / 2), (w / 2 - b, -t / 2), (w / 2, 0.0), (w / 2 - b, t / 2), (-w / 2 + b, t / 2)]


def _grid_solid(p, F, B, swatch, grad=(0.1, 0.8), glow=0.0):
	"""A closed shell between two matching grids of points (rows x cols): a
	front skin F and a back skin B with their four edges stitched shut."""
	R, C = len(F), len(F[0])
	verts = [v for row in F for v in row] + [v for row in B for v in row]
	off = R * C

	def ix(i, j):
		return i * C + j
	faces = []
	for i in range(R - 1):
		for j in range(C - 1):
			q = (ix(i, j), ix(i + 1, j), ix(i + 1, j + 1), ix(i, j + 1))
			faces.append(q)
			faces.append(tuple(off + k for k in reversed(q)))
	for i in range(R - 1):
		for j in (0, C - 1):
			faces.append((ix(i, j), off + ix(i, j), off + ix(i + 1, j), ix(i + 1, j)))
	for j in range(C - 1):
		for i in (0, R - 1):
			faces.append((ix(i, j), ix(i, j + 1), off + ix(i, j + 1), off + ix(i, j)))
	obj = p.poly(verts, faces, swatch, grad)
	if glow:
		obj.data.materials[0] = atlas_material(glow)
	return obj


def _ripple(objs, top, span, amp, fx=2.2, fz=0.7, phase=0.0):
	"""Waves hanging cloth in and out of its plane (Y), still at `top` and
	swinging most `span` meters below it."""
	for o in objs:
		for v in o.data.vertices:
			k = min(1.0, max(0.0, (top - v.co.z) / span))
			v.co.y += amp * k * math.sin(v.co.x * fx + v.co.z * fz + phase)


def _star_flame(p, c, r, h, tongues=6, glow=2.0):
	"""Timiraj's pale fire at c: a star-white core in lilac and pale blue
	tongues, climbing in tiers like _flame_column."""
	x, y, z = c
	p.seg((x, y, z), (x, y, z + h * 0.8), r * 0.85, 0.0, VIOLET, sides=8, grad=(0.0, 0.45), glow=glow, twist=10)
	p.seg((x, y, z), (x + 0.05 * r, y, z + h * 0.95), r * 0.6, 0.0, STARLIGHT, sides=7, grad=(0.0, 0.6), glow=glow * 1.3, twist=37)
	p.seg((x, y, z), (x, y + 0.05 * r, z + h), r * 0.28, 0.0, STARLIGHT, sides=6, grad=(0.0, 0.2), glow=glow * 1.5, twist=70)
	for L, (tz, tr, th, count) in enumerate(((0.0, 1.0, 0.45, tongues), (0.25, 0.75, 0.4, max(3, tongues - 2)), (0.5, 0.5, 0.35, 3))):
		for k in range(count):
			a = (k + 0.5 * L) * math.tau / count + p.rng.uniform(-0.25, 0.25)
			dd = r * tr * p.rng.uniform(0.5, 0.75)
			hh = h * th * p.rng.uniform(0.75, 1.15)
			z0 = z + h * tz
			p.seg((x + math.cos(a) * dd, y + math.sin(a) * dd, z0), (x + math.cos(a) * dd * 1.2, y + math.sin(a) * dd * 1.2, z0 + hh),
				  r * tr * p.rng.uniform(0.35, 0.5), 0.0, (VIOLET, STARLIGHT, SKY)[(k + L) % 3], sides=6, grad=(0.0, 0.6), glow=glow, twist=k * 23 + L * 11)


def _rubble(p, c, R, n, size, swatches=(WAR_STONE, WAR_DARK), z=0.0, flat=0.6):
	"""n loose stones scattered round c within R, half sunk at height z."""
	rng = p.rng
	for k in range(n):
		a = rng.uniform(0, math.tau)
		rr = R * math.sqrt(rng.uniform(0.05, 1.0))
		s = rng.uniform(*size)
		p.rock((s, s * rng.uniform(0.7, 1.0), s * flat), (c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr, z + s * flat * 0.15), swatches[k % len(swatches)],
			   rot=(0, 0, rng.uniform(0, 360)))


def petrified_giant():
	"""A colossal warrior of the god-war turned to stone mid-blow, about 15.5 m
	to the tip of his raised sword: striding forward (-Y) on his left foot, the
	right foot behind sunk to the ankle in a heap of earth, a round shield on
	his left forearm and a greatsword raised over his head in his right fist;
	helm, pauldrons, breastplate and a kilt of plates, the gray-brown stone
	cracked and weathered, lichen on the shoulders, rubble round the feet.
	Used at scales 0.9-1.3. Collide it as a mesh."""
	p = Prop("petrified_giant", 901)
	S = 5.4

	def at(x, y, z):
		return Vector((x * S, y * S, z * S))
	J = 0.01 * S
	ST, DK = WAR_STONE, WAR_DARK
	# the legs: the left forward, the right back with its foot sunk
	for hip, knee, ankle, foot in (((-0.11, 0.0, 0.96), (-0.16, -0.2, 0.52), (-0.17, -0.27, 0.1), (-0.17, -0.33, 0.045)),
								   ((0.11, 0.03, 0.96), (0.17, 0.19, 0.48), (0.2, 0.34, 0.03), (0.2, 0.39, -0.02))):
		hip, knee, ankle = at(*hip), at(*knee), at(*ankle)
		p.seg(hip, knee, 0.115 * S, 0.088 * S, ST, sides=9, jitter=J)
		p.blob((0.19 * S, 0.19 * S, 0.17 * S), knee, DK, segs=(8, 6), jitter=J)
		p.seg(knee, ankle, 0.088 * S, 0.062 * S, ST, sides=9, jitter=J)
		p.seg(knee.lerp(ankle, 0.18), knee.lerp(ankle, 0.85), 0.1 * S, 0.075 * S, DK, sides=7, grad=(0.1, 0.9))   # greaves
		p.blob((0.18 * S, 0.32 * S, 0.12 * S), at(*foot), DK, segs=(8, 5), jitter=J)
	p.rock((0.5 * S, 0.45 * S, 0.14 * S), at(0.2, 0.37, 0.0), WAR_DARK, jitter=0.1)                # the earth heaped over the sunk foot
	# the kilt of plates, the belt and the body
	p.seg(at(0, 0.01, 1.08), at(0, -0.01, 0.74), 0.19 * S, 0.25 * S, DK, sides=10, grad=(0.1, 0.9), jitter=J)
	for k in range(10):                                                      # the plates' seams
		a = k * math.tau / 10 + 0.3
		p.seg(at(math.cos(a) * 0.19, math.sin(a) * 0.19, 1.06), at(math.cos(a) * 0.255, math.sin(a) * 0.255, 0.76), 0.012 * S, 0.012 * S, IRON, sides=4, grad=(0.5, 1.0))
	p.seg(at(0, 0, 1.03), at(0, 0, 1.1), 0.2 * S, 0.2 * S, DK, sides=10)
	p.blob((0.36 * S, 0.26 * S, 0.34 * S), at(0, 0.0, 1.14), ST, segs=(10, 8), jitter=J)
	p.blob((0.48 * S, 0.32 * S, 0.42 * S), at(0, 0.0, 1.36), ST, rot=(-8, 0, 0), segs=(12, 8), jitter=J)
	p.blob((0.42 * S, 0.2 * S, 0.34 * S), at(0, -0.075, 1.35), DK, rot=(-8, 0, 0), segs=(12, 8), grad=(0.05, 0.85))   # the breastplate
	# neck, head, helm and beard
	p.seg(at(0, 0, 1.5), at(0, -0.02, 1.62), 0.066 * S, 0.06 * S, ST, sides=8)
	p.blob((0.2 * S, 0.22 * S, 0.24 * S), at(0, -0.035, 1.67), ST, segs=(10, 8))
	p.blob((0.23 * S, 0.25 * S, 0.19 * S), at(0, -0.005, 1.735), DK, segs=(10, 6), grad=(0.0, 0.8))
	p.box((0.035 * S, 0.03 * S, 0.1 * S), at(0, -0.145, 1.68), DK)
	p.box((0.035 * S, 0.27 * S, 0.07 * S), at(0, 0.0, 1.84), DK, grad=(0.0, 0.7))               # crest
	p.blob((0.15 * S, 0.1 * S, 0.13 * S), at(0, -0.125, 1.585), ST, segs=(8, 6), jitter=J)       # beard
	# the arms: the right raised over the head, the left bent before him with the shield
	for sh, el, hd in (((0.24, 0.0, 1.46), (0.31, 0.07, 1.72), (0.15, 0.05, 1.97)),
					   ((-0.24, 0.0, 1.46), (-0.32, -0.1, 1.22), (-0.22, -0.27, 1.2))):
		sh, el, hd = at(*sh), at(*el), at(*hd)
		p.seg(sh, el, 0.086 * S, 0.072 * S, ST, sides=8, jitter=J)
		p.blob((0.145 * S, 0.145 * S, 0.145 * S), el, ST, segs=(8, 6))
		p.seg(el, hd, 0.072 * S, 0.06 * S, ST, sides=8, jitter=J)
		p.seg(el.lerp(hd, 0.25), el.lerp(hd, 0.85), 0.082 * S, 0.072 * S, DK, sides=7)                 # bracers
		p.blob((0.14 * S, 0.14 * S, 0.14 * S), hd, ST, segs=(8, 6), jitter=J)
		s = 1 if sh.x > 0 else -1
		p.blob((0.22 * S, 0.22 * S, 0.15 * S), at(s * 0.25, 0.0, 1.5), DK, rot=(0, s * 22, 0), segs=(10, 6), grad=(0.0, 0.8), jitter=J)   # pauldrons
	# the shield on the left forearm, facing forward and out
	c, n = at(-0.3, -0.25, 1.21), Vector((-0.45, -1.0, 0.05)).normalized()
	p.seg(c - n * 0.012 * S, c + n * 0.03 * S, 0.27 * S, 0.27 * S, DK, sides=16)
	p.seg(c + n * 0.03 * S, c + n * 0.045 * S, 0.245 * S, 0.23 * S, ST, sides=16)
	p.blob((0.1 * S, 0.1 * S, 0.1 * S), c + n * 0.045 * S, DK, segs=(8, 6))
	# the greatsword in the right fist, raised back over his head
	hd, dv = at(0.15, 0.05, 1.97), Vector((-0.12, 0.38, 0.92)).normalized()
	p.seg(hd - dv * 0.1 * S, hd + dv * 0.1 * S, 0.034 * S, 0.034 * S, DK, sides=6)
	p.blob((0.075 * S, 0.075 * S, 0.075 * S), hd - dv * 0.12 * S, DK, segs=(8, 6))
	g = hd + dv * 0.115 * S
	side = Vector((1, 0, 0))
	side = (side - dv * side.dot(dv)).normalized()
	p.seg(g - side * 0.17 * S, g + side * 0.17 * S, 0.034 * S, 0.03 * S, DK, sides=6)
	start = len(p.parts)
	_prism(p, _blade_sec(0.13 * S, 0.034 * S), 0.0, _blade_sec(0.11 * S, 0.03 * S), 0.72 * S, ST, grad=(0.0, 0.9))
	_prism(p, _blade_sec(0.11 * S, 0.03 * S), 0.72 * S, None, 0.86 * S, ST, grad=(0.0, 0.6))
	_move_parts(p, start, _frame(g + dv * 0.01 * S, side, dv))
	# cracks across the stone and lichen on the high places
	for pts in (((-0.2, -0.17, 1.47), (-0.06, -0.18, 1.39), (0.07, -0.18, 1.31), (0.16, -0.15, 1.2)),
				((-0.17, -0.25, 0.8), (-0.19, -0.26, 0.68), (-0.16, -0.27, 0.58)),
				((0.08, -0.07, 1.2), (0.12, -0.08, 1.1), (0.1, -0.12, 1.02)),
				((0.29, -0.05, 1.63), (0.3, -0.02, 1.72), (0.26, 0.0, 1.82))):
		_chain(p, [at(*q) for q in pts], 0.014 * S, 0.008 * S, IRON, sides=4, grad=(0.6, 1.0))
	for q, sz in (((0.25, 0.0, 1.57), 0.12), ((-0.25, 0.0, 1.57), 0.1), ((0.0, 0.0, 1.83), 0.08), ((-0.34, -0.28, 1.46), 0.07), ((0.0, 0.0, 1.55), 0.1)):
		p.blob((sz * S, sz * S, 0.03 * S), at(*q), MOSS, segs=(8, 4), grad=(0.1, 0.7), jitter=0.05)
	_rubble(p, (0, 0), 3.4 * S * 0.3 + 2.0, 16, (0.4, 1.4))
	return p.build(bevel=0.06)


def shattered_divine_blade():
	"""A god's sword about 12 m long, snapped in two in the god-war: the hilt
	half driven into the ground by its broken end (it reads as stuck point
	first), leaning 24 degrees toward +X to about 8.4 m, its pale tarnished
	blade with a dark fuller and faint gold runes, a gold crossguard with
	down-curling bronze-gold ends round an amber sun-stone, a leather grip
	bound in gold and a gold pommel; the point half (4.6 m) lies in the dirt
	nearby (-Y), and the ground is heaped and cracked where the blade went in.
	Collide it as a mesh."""
	p = Prop("shattered_divine_blade", 903)
	d = Prop("shattered_divine_blade_detail", 904)
	W, T = 1.3, 0.34
	# the hilt half, built upright with its broken end buried
	_prism(p, _blade_sec(W, T), -2.5, _blade_sec(W * 0.97, T), 5.3, STONE_LIGHT, grad=(0.0, 0.9))
	for s in (-1, 1):
		p.box((0.26, 0.05, 7.2), (0, s * (T / 2 - 0.004), 1.5), IRON, grad=(0.3, 0.9))              # the fuller
		for k, z in enumerate((1.0, 1.9, 2.8, 3.7, 4.6)):
			_rune(d, (0.07, s * (T / 2 + 0.03), z), 0.5, k + (s > 0) * 5, glow=0.7, swatch=GOLD)
	p.seg((0, 0, 5.1), (0, 0, 5.3), 0.7, 0.72, TARNISH, sides=8)                                 # the collar under the guard
	p.box((3.5, 0.8, 0.55), (0, 0, 5.55), GOLD, grad=(0.0, 0.8))
	for s in (-1, 1):
		_chain(p, [(s * 1.6, 0, 5.55), (s * 2.1, 0, 5.45), (s * 2.45, 0, 5.1), (s * 2.5, 0, 4.7)], 0.3, 0.16, TARNISH, sides=7)
		p.blob((0.42, 0.42, 0.42), (s * 2.5, 0, 4.62), GOLD, segs=(8, 6))
	p.seg((0, -0.44, 5.55), (0, 0.44, 5.55), 0.6, 0.6, GOLD, sides=14, grad=(0.0, 0.7))            # the sun boss
	for s in (-1, 1):
		d.seg((0, s * 0.44, 5.55), (0, s * 0.5, 5.55), 0.32, 0.26, FLAME, sides=10, grad=(0.3, 0.8), glow=0.8)
		for k in range(8):
			a = k * math.tau / 8
			p.seg((math.cos(a) * 0.55, s * 0.42, 5.55 + math.sin(a) * 0.55), (math.cos(a) * 0.9, s * 0.38, 5.55 + math.sin(a) * 0.9), 0.1, 0.0, GOLD, sides=4)
	p.seg((0, 0, 5.8), (0, 0, 7.9), 0.28, 0.25, HIDE, sides=8, grad=(0.3, 1.0))                   # the grip
	for z in (6.2, 6.8, 7.4):
		p.seg((0, 0, z), (0, 0, z + 0.12), 0.31, 0.31, GOLD, sides=8)
	p.seg((0, 0, 7.85), (0, 0, 8.0), 0.3, 0.36, TARNISH, sides=8)
	p.blob((0.85, 0.65, 0.8), (0, 0, 8.3), GOLD, segs=(10, 8), grad=(0.0, 0.8))
	p.seg((0, 0, 8.65), (0, 0, 9.1), 0.18, 0.0, TARNISH, sides=6)
	tilt = Matrix.Rotation(math.radians(24), 4, "Y")
	_move_parts(p, 0, tilt)
	_move_parts(d, 0, tilt)
	# the cracked mound where it went in
	rng = p.rng
	for k in range(9):
		a = k * math.tau / 9 + rng.uniform(-0.2, 0.2)
		rr = rng.uniform(0.9, 1.6)
		s = rng.uniform(0.8, 1.4)
		p.rock((s, s * 0.8, s * 0.45), (math.cos(a) * rr - 0.2, math.sin(a) * rr, 0.05), (WAR_DARK, WAR_STONE)[k % 2], rot=(0, 0, math.degrees(a)))
	for k in range(7):
		a = k * math.tau / 7 + 0.3
		p.box((rng.uniform(1.4, 2.6), 0.16, 0.04), (math.cos(a) * 2.2, math.sin(a) * 2.2, 0.0), WAR_DARK, rot=(0, 0, math.degrees(a)), grad=(0.8, 1.0))
	# the point half, lying flat in the dirt
	start, ds = len(p.parts), len(d.parts)
	_prism(p, _blade_sec(W * 0.96, T), 0.0, _blade_sec(W * 0.9, T * 0.95), 3.0, STONE_LIGHT, grad=(0.0, 0.9))
	_prism(p, _blade_sec(W * 0.9, T * 0.95), 3.0, None, 4.6, STONE_LIGHT, grad=(0.0, 0.7))
	p.box((0.24, 0.05, 2.9), (0, T / 2 - 0.004, 1.5), IRON, grad=(0.3, 0.9))
	for k, z in enumerate((0.7, 1.6, 2.5)):
		_rune(d, (0.05, T / 2 + 0.03, z), 0.45, k + 3, glow=0.7, swatch=GOLD)
	for x, ln in ((-0.42, 0.35), (-0.1, 0.55), (0.2, 0.3), (0.48, 0.45)):                        # the jagged break
		p.seg((x, 0, 0.05), (x + 0.05, 0, -ln), 0.16, 0.0, STONE_LIGHT, sides=4, grad=(0.0, 0.8))
	m = Matrix.Translation((3.3, -3.9, 0.1)) @ Matrix.Rotation(math.radians(38), 4, "Z") @ Matrix.Rotation(math.radians(7), 4, "Y") @ Matrix.Rotation(math.radians(90), 4, "X")
	_move_parts(p, start, m)
	_move_parts(d, ds, m)
	_rubble(p, (3.3, -3.9), 2.6, 6, (0.3, 0.7), z=0.0)
	return join_into(p.build(bevel=0.06), [d.build()])


def divine_shield_fragment():
	"""A god's round bronze shield 8 m across, a quarter of it broken away,
	driven edge-first into the ground and leaning back 22 degrees so about
	half shows (to about 4.4 m): a domed face with a gold boss and an engraved
	twelve-rayed sun-star in tarnished gold, an inner ring, rivets and a heavy
	gold rim, cracks running in from the jagged break at the top right, and a
	heap of earth round its foot. The face looks -Y. Collide it as a mesh."""
	p = Prop("divine_shield_fragment", 905)
	R, DOME, TH = 4.0, 0.9, 0.45
	a0, a1 = math.radians(112), math.radians(380)                              # the kept arc; the top right is gone
	NA, radii = 30, (0.5, 1.3, 2.2, 3.1, R)
	rng = p.rng

	def front(r):
		return -DOME * (1 - (r / R) ** 2)
	F, B = [], []
	for i in range(NA + 1):
		rowF, rowB = [], []
		for j, r in enumerate(radii):
			a = a0 + (a1 - a0) * i / NA
			if i in (0, NA) and j > 0:
				jag = rng.uniform(0, 7) if j % 2 else rng.uniform(-2, 2)
				a += math.radians(-jag if i == 0 else jag)
			x, z = math.cos(a) * r, math.sin(a) * r
			rowF.append((x, front(r), z))
			rowB.append((x, front(r) + TH, z))
		F.append(rowF)
		B.append(rowB)
	_grid_solid(p, F, B, COPPER, grad=(0.15, 1.0))

	def on(a, r, lift=0.03):
		return (math.cos(a) * r, front(r) - lift, math.sin(a) * r)
	arc = [a0 + (a1 - a0) * i / NA for i in range(1, NA)]
	_chain(p, [(math.cos(a) * R, TH / 2, math.sin(a) * R) for a in arc], 0.3, 0.3, GOLD, sides=6, grad=(0.0, 0.7))
	_chain(p, [on(a, 2.7, 0.0) for a in arc[1:-1]], 0.08, 0.08, TARNISH, sides=4, grad=(0.0, 0.6))
	for a in arc[::2]:
		p.blob((0.2, 0.2, 0.2), on(a, 3.5, 0.0), GOLD, segs=(6, 4))
	for k in range(12):                                                        # the sun-star's rays
		a = math.radians(90 + k * 30)
		if not (a0 + 0.12 < (a if a >= a0 else a + math.tau) < a1 - 0.12):
			continue
		ln = 3.4 if k % 2 == 0 else 2.3
		_chain(p, [on(a, 0.5 + (ln - 0.5) * t / 4, 0.0) for t in range(5)], 0.24 if k % 2 == 0 else 0.17, 0.02, TARNISH, sides=4, grad=(0.0, 0.6))
	p.blob((1.4, 0.8, 1.4), (0, -DOME + 0.05, 0), GOLD, segs=(12, 8), grad=(0.0, 0.7))
	p.seg((0, -DOME + 0.2, 0), (0, -DOME + 0.05, 0), 0.9, 0.9, TARNISH, sides=14)
	for pts in (((-1.6, 0.0, 3.0), (-1.2, 0.0, 2.3), (-1.3, 0.0, 1.5)), ((3.3, 0.0, -0.8), (2.7, 0.0, -0.1), (2.1, 0.0, 0.4)), ((-2.3, 0.0, -1.9), (-1.8, 0.0, -1.2))):
		_chain(p, [(x, front(math.hypot(x, z)) - 0.02, z) for x, _, z in pts], 0.06, 0.03, IRON, sides=4, grad=(0.6, 1.0))
	_move_parts(p, 0, Matrix.Translation((0, 0, 0.9)) @ Matrix.Rotation(math.radians(-22), 4, "X") @ Matrix.Rotation(math.radians(8), 4, "Y"))
	for k in range(10):                                                        # the earth heaped round its foot
		x = -3.6 + 7.2 * k / 9 + rng.uniform(-0.3, 0.3)
		s = rng.uniform(1.0, 1.8)
		p.rock((s, s * 0.9, s * 0.4), (x, rng.uniform(-0.9, 0.4), 0.05), (WAR_DARK, WAR_STONE)[k % 2], rot=(0, 0, rng.uniform(0, 360)))
	_rubble(p, (0, -1.5), 4.5, 8, (0.3, 0.8))
	return p.build(bevel=0.06)


def war_crater():
	"""A crater of the god-war, 21 m across and no taller than 0.5 m, to lay
	flat on the ground: a scorched black blast mark in a gray ash floor, dark
	cracks raying out, a low ragged rim of thrown-up brown earth, rubble
	strewn on the rim and a few tarnished bronze shards in the ash. Collide
	it as none."""
	p = Prop("war_crater", 907)
	rng = p.rng
	p.seg((0, 0, -0.2), (0, 0, 0.03), 7.9, 7.9, STONE_DARK, sides=28, grad=(0.55, 1.0))
	p.seg((0, 0, -0.2), (0, 0, 0.05), 4.6, 4.2, IRON, sides=20, grad=(0.3, 1.0), jitter=0.05)
	rim = [(7.0, -0.2), (7.0, 0.04), (7.9, 0.26), (8.7, 0.36), (9.5, 0.26), (10.2, 0.08), (10.6, -0.2)]
	_lathe(p, rim, 36, WAR_DARK, grad=(0.05, 0.9), jitter=0.07)

	def rim_h(r):
		for (r0, z0), (r1, z1) in zip(rim[1:], rim[2:]):
			if r0 <= r <= r1:
				return z0 + (z1 - z0) * (r - r0) / (r1 - r0)
		return 0.03
	for k in range(14):                                                         # cracks raying out through the ash
		a = k * math.tau / 14 + rng.uniform(-0.15, 0.15)
		r0, r1 = rng.uniform(2.5, 4.0), rng.uniform(6.5, 8.6)
		pts = []
		for t in range(4):
			r = r0 + (r1 - r0) * t / 3
			aa = a + rng.uniform(-0.06, 0.06)
			pts.append((math.cos(aa) * r, math.sin(aa) * r, max(0.06, rim_h(r) + 0.02)))
		_chain(p, pts, 0.1, 0.04, IRON, sides=4, grad=(0.7, 1.0))
	for k in range(44):                                                         # rubble on the rim and in the ash
		a = rng.uniform(0, math.tau)
		r = rng.uniform(5.0, 10.4) if k % 4 else rng.uniform(1.0, 6.0)
		hz = rim_h(r) if r > 7.0 else 0.04
		s = rng.uniform(0.2, 0.7)
		sz = min(s * 0.6, 2 * (0.5 - hz) - 0.14)
		if sz < 0.08:
			continue
		p.rock((s, s * 0.8, sz), (math.cos(a) * r, math.sin(a) * r, hz), (WAR_STONE, WAR_DARK, STONE_DARK)[k % 3], rot=(0, 0, rng.uniform(0, 360)), jitter=0.04)
	for k in range(5):                                                          # bronze shards in the ash
		a, r = rng.uniform(0, math.tau), rng.uniform(2.0, 6.0)
		p.box((rng.uniform(0.5, 1.1), rng.uniform(0.3, 0.6), 0.06), (math.cos(a) * r, math.sin(a) * r, 0.07), (COPPER, TARNISH)[k % 2], rot=(rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(0, 360)), grad=(0.1, 0.8))
	return p.build(bevel=0.06)


def godwar_banner():
	"""A war banner of the gods left standing on the battlefield, about 8.3 m:
	a bronze-banded pole leaning a little and snapped off at the top, held in
	a cairn of rubble, a bronze crossbar (one gold finial left, the other end
	splintered) and a long tattered banner of faded crimson with a pale band
	along the top and a tarnished gold sun-star on a white disc, its foot torn
	into tongues. A broken spear leans in the cairn. The banner faces -Y.
	Collide it as a box."""
	p = Prop("godwar_banner", 909)
	rng = p.rng
	for k in range(8):                                                          # the cairn
		a = k * math.tau / 8 + rng.uniform(-0.3, 0.3)
		rr = rng.uniform(0.35, 0.8)
		s = rng.uniform(0.5, 0.85)
		p.rock((s, s * 0.9, s * 0.75), (math.cos(a) * rr, math.sin(a) * rr, 0.12), (WAR_STONE, WAR_DARK)[k % 2], rot=(0, 0, rng.uniform(0, 360)))
	lean = Vector((0.03, 0.015, 1.0)).normalized()

	def pole(z):
		return Vector((0, 0, -0.4)) + lean * ((z + 0.4) / lean.z)
	top = pole(7.9)
	p.seg(pole(-0.4), top, 0.16, 0.12, WAR_DARK, sides=8, grad=(0.2, 1.0))
	for z in (0.9, 3.2, 5.6):
		p.seg(pole(z), pole(z + 0.22), 0.19, 0.18, COPPER, sides=8, grad=(0.1, 0.7))
	_broken_top(p, top.x, top.y, top.z, 0.13, WAR_DARK, n=4, rise=(0.2, 0.55))
	c = pole(7.2)
	ya = c.y - 0.2
	L0, L1 = c + Vector((-1.5, -0.2, 0.16)), c + Vector((1.35, -0.2, -0.14))
	p.seg(L0, L1, 0.075, 0.075, COPPER, sides=6)
	p.blob((0.26, 0.26, 0.26), L0 - Vector((0.08, 0, 0)), GOLD, segs=(8, 6))
	p.seg(L0 - Vector((0.18, 0, 0)), L0 - Vector((0.6, 0, -0.04)), 0.09, 0.0, TARNISH, sides=5)
	for k in range(3):                                                          # the splintered end
		p.seg(L1 - Vector((0.05, 0, 0)), L1 + Vector((rng.uniform(0.1, 0.3), rng.uniform(-0.05, 0.05), rng.uniform(-0.06, 0.06))), 0.04, 0.0, COPPER, sides=4)
	for k in range(3):
		p.seg(c + Vector((-0.2, -0.05, 0.12 - k * 0.1)), c + Vector((0.2, -0.05, 0.1 - k * 0.1)), 0.035, 0.035, HIDE, sides=4)   # lashing

	# the banner: hangs from the bar in front of the pole
	xl, xr = c.x - 1.3, c.x + 1.15

	def zt(x):
		return L0.z + (L1.z - L0.z) * (x - L0.x) / (L1.x - L0.x) - 0.08
	ztop = zt(xl)
	bottom = ztop - 4.7
	outline = [(xl, zt(xl)), (xr, zt(xr)), (xr + 0.05, zt(xr) - 1.6), (xr - 0.3, zt(xr) - 2.0), (xr - 0.05, zt(xr) - 2.5), (xr, bottom + 0.9)]
	tongues = 7
	for k in range(tongues + 1):
		x = xr - (xr - xl) * k / tongues
		outline.append((x, bottom + (0.0 if k % 2 else 0.55) + rng.uniform(-0.2, 0.2) + (0.3 if k in (2, 3) else 0.0)))
	outline += [(xl - 0.05, bottom + 1.2), (xl + 0.15, bottom + 2.6), (xl, zt(xl) - 1.0)]
	cloth = len(p.parts)
	_plate(p, outline, ya, 0.05, CLOTH_RED, grad=(0.0, 0.45))
	mx = (xl + xr) / 2
	_plate(p, [(xl + 0.02, zt(xl) - 0.05), (xr - 0.02, zt(xr) - 0.05), (xr - 0.02, zt(xr) - 0.5), (xl + 0.02, zt(xl) - 0.5)], ya - 0.04, 0.03, CLOTH_WHITE, grad=(0.2, 0.7))
	ez = ztop - 1.9
	star = []
	for k in range(24):
		a = k * math.tau / 24
		r = (0.95 if k % 4 == 0 else 0.7) if k % 2 == 0 else 0.5
		star.append((mx + math.cos(a) * r, ez + math.sin(a) * r))
	_plate(p, star, ya - 0.04, 0.03, TARNISH, grad=(0.0, 0.5))
	_plate(p, [(mx + math.cos(k * math.tau / 14) * 0.38, ez + math.sin(k * math.tau / 14) * 0.38) for k in range(14)], ya - 0.07, 0.03, CLOTH_WHITE, grad=(0.1, 0.6))
	_plate(p, [(xl - 0.05, bottom + 1.9), (xl + 0.12, bottom + 1.9), (xl + 0.05, bottom + 0.3), (xl - 0.02, bottom + 0.2)], ya + 0.01, 0.03, CLOTH_RED, grad=(0.2, 0.6))   # a torn strip hanging loose
	_ripple(p.parts[cloth:], ztop, 3.5, 0.16)
	p.seg((0.6, -0.55, -0.2), (1.2, -0.95, 2.0), 0.05, 0.045, WAR_DARK, sides=5)             # a broken spear in the cairn
	_broken_top(p, 1.2, -0.95, 2.0, 0.05, WAR_DARK, n=3, rise=(0.05, 0.2))
	return p.build(bevel=0.06)


def construct_husk():
	"""A divine construct of the god-war lying in pieces, about 8 x 11 m and
	2 m high: its stone and bronze torso fallen on its back (head end +Y), the
	neck snapped and the dead core in its breastplate cracked (a last gold
	spark in it), the left arm flung out along the ground ending in a great
	stone fist, the right leg stretched out, the left snapped at the thigh with
	its shin stuck up out of the earth, the helm-head rolled away, and bronze
	plates, gears and stone rubble strewn round it. Collide it as a mesh."""
	p = Prop("construct_husk", 911)
	d = Prop("construct_husk_detail", 912)
	rng = p.rng
	ST, BR = WAR_STONE, COPPER
	# the torso, built upright and laid on its back
	start, ds = len(p.parts), len(d.parts)
	p.box((2.8, 1.8, 3.0), (0, 0, 0), ST, grad=(0.1, 0.9), jitter=0.05)
	p.box((2.3, 0.3, 2.3), (0, -0.95, 0.25), BR, grad=(0.0, 0.8))
	for s in (-1, 1):
		p.box((1.1, 1.6, 1.1), (s * 1.85, 0, 1.0), ST, jitter=0.04)
		p.blob((1.3, 1.7, 0.9), (s * 1.95, 0, 1.5), BR, segs=(10, 6), grad=(0.0, 0.8))
		for z in (-0.7, 0.3, 1.2):
			p.blob((0.16, 0.16, 0.16), (s * 1.0, -1.1, z), GOLD, segs=(6, 4))
	p.seg((0, -1.0, 0.35), (0, -1.28, 0.35), 0.62, 0.56, BR, sides=12)               # the core socket
	p.blob((0.8, 0.3, 0.8), (0, -1.26, 0.35), IRON, segs=(10, 6))
	for q in ((0.12, -1.4, 0.42), (-0.2, -1.38, 0.25)):
		d.blob((0.16, 0.08, 0.14), q, PETAL_YELLOW, segs=(6, 4), grad=(0.0, 0.3), glow=1.2)
	_chain(p, [(0.35, -1.4, 0.7), (0.2, -1.4, 0.45), (0.3, -1.4, 0.1), (0.15, -1.25, -0.4), (0.3, -1.12, -0.9)], 0.04, 0.03, IRON, sides=4, grad=(0.6, 1.0))
	p.box((2.0, 1.4, 0.6), (0, 0, -1.8), BR, grad=(0.1, 0.8))
	p.box((2.4, 1.6, 0.8), (0, 0, -2.4), ST, jitter=0.04)
	p.seg((0, 0, 1.45), (0, 0, 1.9), 0.5, 0.45, BR, sides=8)                          # the snapped neck
	_broken_top(p, 0, 0, 1.9, 0.45, ST, n=3, rise=(0.15, 0.4))
	p.seg((1.9, 0.2, 0.95), (2.5, 0.35, 0.95), 0.45, 0.4, ST, sides=8)               # the right arm's stump
	_broken_top(p, 2.5, 0.35, 0.95, 0.4, ST, n=3, rise=(0.1, 0.3))
	# the left arm flung out along the ground
	sh, el, wr = Vector((-2.3, 0.5, 1.0)), Vector((-3.9, 0.5, 1.8)), Vector((-5.2, 0.45, 1.0))
	p.seg(sh, el, 0.46, 0.42, ST, sides=8, jitter=0.03)
	p.blob((0.95, 0.9, 0.95), el, BR, segs=(10, 6))
	p.seg(el, wr, 0.42, 0.38, ST, sides=8, jitter=0.03)
	p.seg(el.lerp(wr, 0.3), el.lerp(wr, 0.8), 0.46, 0.44, BR, sides=8)
	p.box((1.1, 1.0, 1.1), (-5.75, 0.45, 0.72), ST, rot=(0, -30, 0), jitter=0.05)       # the fist
	for k in range(4):
		p.box((0.26, 0.9, 0.3), (-6.2 + k * 0.05, 0.45 - 0.33 + k * 0.22, 0.38 + k * 0.02), ST, rot=(0, -30, 0))
	lay = Matrix.Translation((0, 0.6, 0.86)) @ Matrix.Rotation(math.radians(7), 4, "Y") @ Matrix.Rotation(math.radians(-90), 4, "X")
	_move_parts(p, start, lay)
	_move_parts(d, ds, lay)
	# the legs
	p.seg((0.75, -2.3, 0.6), (1.0, -4.3, 0.55), 0.55, 0.5, ST, sides=8, jitter=0.03)
	p.blob((1.05, 1.05, 1.0), (1.0, -4.35, 0.55), BR, segs=(10, 6))
	p.seg((1.0, -4.4, 0.55), (1.3, -6.3, 0.5), 0.5, 0.44, ST, sides=8, jitter=0.03)
	p.seg((1.05, -4.9, 0.55), (1.25, -6.0, 0.5), 0.54, 0.5, BR, sides=8)
	p.box((1.2, 1.5, 1.0), (1.35, -6.9, 0.5), ST, rot=(0, 0, 8), jitter=0.04)
	p.seg((-0.75, -2.3, 0.6), (-1.0, -3.5, 0.55), 0.55, 0.5, ST, sides=8)
	_broken_top(p, -1.0, -3.5, 0.55, 0.45, ST, n=3, rise=(0.1, 0.3))
	p.seg((-2.1, -4.7, -0.5), (-2.9, -5.8, 1.3), 0.5, 0.45, ST, sides=8, jitter=0.03)  # the snapped shin, stuck up out of the earth
	p.blob((1.0, 1.0, 0.95), (-2.95, -5.85, 1.4), BR, segs=(10, 6))
	p.rock((1.8, 1.6, 0.5), (-2.1, -4.7, 0.0), WAR_DARK)
	# the head, rolled away on its side
	start = len(p.parts)
	p.box((1.2, 1.1, 1.2), (0, 0, 0), ST, jitter=0.04)
	p.box((1.0, 0.22, 0.95), (0, -0.6, 0), BR, grad=(0.0, 0.8))
	p.box((0.8, 0.06, 0.13), (0, -0.72, 0.12), IRON, grad=(0.8, 1.0))
	p.box((0.08, 0.06, 0.45), (0, -0.72, -0.2), IRON, grad=(0.8, 1.0))
	p.box((0.16, 1.3, 0.42), (0, 0.0, 0.75), BR, grad=(0.0, 0.7))
	_move_parts(p, start, Matrix.Translation((-2.4, 3.9, 0.55)) @ Matrix.Rotation(math.radians(35), 4, "Z") @ Matrix.Rotation(math.radians(-70), 4, "Y"))
	# plates, gears and rubble
	for k in range(7):
		a, r = rng.uniform(0, math.tau), rng.uniform(2.5, 5.5)
		p.box((rng.uniform(0.7, 1.3), rng.uniform(0.5, 0.9), 0.1), (math.cos(a) * r, math.sin(a) * r - 1.0, 0.06), (BR, TARNISH)[k % 2], rot=(rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(0, 360)), grad=(0.0, 0.8))
	for gx, gy, gr in ((2.8, 1.8, 0.7), (-3.6, -1.9, 0.5)):
		_torus(p, (gx, gy, 0.12), (1, 0, 0), (0, 1, 0), gr, 0.12, BR, seg=12)
		p.seg((gx, gy, 0.0), (gx, gy, 0.22), 0.2, 0.2, BR, sides=8)
		for k in range(10):
			a = k * math.tau / 10
			p.box((0.18, 0.14, 0.2), (gx + math.cos(a) * (gr + 0.14), gy + math.sin(a) * (gr + 0.14), 0.12), BR, rot=(0, 0, math.degrees(a)))
	_rubble(p, (0, -1.0), 6.0, 16, (0.3, 0.9))
	return join_into(p.build(bevel=0.06), [d.build()])


def relic_cart():
	"""A scavengers' two-wheeled handcart heaped with relics of the god-war,
	about 2 x 5 m and 2.6 m to the top of the heap: a plank bed with side
	boards on big spoked wheels, its shafts resting on the ground in front
	(-Y) and a prop stick behind; on it sacks, a dented golden helm, broken
	swords, a spear and an axe, bronze plates and a small tarnished statue of
	an elephant-headed god, with a bronze shield leaning on its side.
	Collide it as a mesh."""
	p = Prop("relic_cart", 913)
	rng = p.rng
	WY = 0.4
	p.box((1.9, 3.0, 0.14), (0, 0.3, 0.95), WOOD, grad=(0.1, 0.9))
	for s in (-1, 1):
		p.box((0.08, 3.0, 0.5), (s * 0.98, 0.3, 1.27), WOOD_GRAY, grad=(0.1, 0.9))
		p.box((0.14, 3.6, 0.16), (s * 0.62, 0.0, 0.82), WOOD_GRAY)
		p.box((0.3, 0.3, 0.26), (s * 0.78, WY, 0.72), WOOD_GRAY)
		_cart_wheel(p, (s * 1.12, WY, 0.62), 0.62)
		p.seg((s * 0.62, -1.5, 0.84), (s * 0.5, -3.3, 0.12), 0.07, 0.06, WOOD, sides=6)         # the shafts
		for y in (-1.15, 0.3, 1.75):
			p.seg((s * 0.98, y, 0.9), (s * 0.98, y, 1.62), 0.06, 0.05, WOOD, sides=5)
	p.seg((-1.2, WY, 0.62), (1.2, WY, 0.62), 0.07, 0.07, WOOD_GRAY, sides=6)
	p.seg((-0.5, -3.1, 0.18), (0.5, -3.1, 0.18), 0.05, 0.05, WOOD, sides=5)
	p.box((1.9, 0.08, 0.5), (0, 1.8, 1.27), WOOD_GRAY)
	p.box((1.9, 0.08, 0.36), (0, -1.2, 1.2), WOOD_GRAY)
	p.seg((0, 1.6, 0.86), (0.1, 1.85, -0.05), 0.05, 0.05, WOOD_GRAY, sides=5)               # the prop stick
	# the heap
	p.blob((1.7, 2.7, 0.7), (0, 0.3, 1.15), HIDE, segs=(10, 6), grad=(0.2, 0.9))
	for q, s in (((-0.45, 1.1, 1.35), (0.8, 0.7, 0.6)), ((0.45, 1.2, 1.3), (0.7, 0.8, 0.55)), ((0.1, -0.6, 1.3), (0.9, 0.7, 0.5))):
		p.blob(s, q, HIDE, segs=(8, 6), grad=(0.1, 0.8))
		p.seg((q[0], q[1], q[2] + s[2] * 0.4), (q[0], q[1], q[2] + s[2] * 0.62), 0.07, 0.05, HIDE, sides=5)
	for k in range(8):
		p.box((rng.uniform(0.3, 0.6), rng.uniform(0.2, 0.4), 0.05), (rng.uniform(-0.6, 0.6), rng.uniform(-0.7, 1.4), 1.48 + rng.uniform(0, 0.1)), (COPPER, TARNISH, GOLD)[k % 3],
			  rot=(rng.uniform(-25, 25), rng.uniform(-25, 25), rng.uniform(0, 360)), grad=(0.0, 0.8))
	# the golden helm
	start = len(p.parts)
	p.blob((0.62, 0.68, 0.6), (0, 0, 0.25), GOLD, segs=(12, 8), grad=(0.0, 0.8))
	p.box((0.07, 0.72, 0.24), (0, 0.02, 0.58), GOLD, grad=(0.0, 0.6))
	for s in (-1, 1):
		p.box((0.08, 0.28, 0.32), (s * 0.27, -0.16, 0.08), GOLD)
	p.box((0.4, 0.05, 0.07), (0, -0.33, 0.25), IRON, grad=(0.8, 1.0))
	p.seg((0, 0, 0.1), (0, 0, 0.18), 0.325, 0.325, TARNISH, sides=12)
	_move_parts(p, start, Matrix.Translation((0.35, -0.5, 1.55)) @ Matrix.Rotation(math.radians(30), 4, "Z") @ Matrix.Rotation(math.radians(18), 4, "X"))
	# broken swords, a spear and an axe
	for base, aim, ln in (((-0.3, 0.2, 1.3), (-0.4, -0.2, 1.0), 1.0), ((0.5, 0.5, 1.3), (0.5, 0.3, 0.8), 0.7), ((-0.1, 1.5, 1.35), (-0.2, 0.5, 0.7), 0.8)):
		start = len(p.parts)
		_prism(p, _blade_sec(0.14, 0.03), 0.0, _blade_sec(0.12, 0.03), ln, STONE_LIGHT, grad=(0.0, 0.8))
		p.seg((0, 0, ln), (0.03, 0, ln + 0.12), 0.05, 0.0, STONE_LIGHT, sides=4)
		p.box((0.42, 0.08, 0.07), (0, 0, -0.02), GOLD)
		p.seg((0, 0, -0.05), (0, 0, -0.32), 0.035, 0.035, HIDE, sides=6)
		p.blob((0.1, 0.1, 0.1), (0, 0, -0.35), GOLD, segs=(6, 4))
		_move_parts(p, start, _frame(base, (1, 0, 0), aim))
	p.seg((0.7, 1.6, 1.25), (-0.8, -1.3, 2.25), 0.04, 0.04, WOOD, sides=6)
	p.seg((-0.8, -1.3, 2.25), (-0.95, -1.58, 2.35), 0.07, 0.0, COPPER, sides=4)
	p.seg((0.6, -0.9, 1.3), (0.2, 0.2, 2.1), 0.04, 0.04, WOOD_GRAY, sides=6)
	p.box((0.08, 0.4, 0.35), (0.2, 0.22, 2.1), COPPER, rot=(0, 0, -20), grad=(0.0, 0.8))
	# the little statue of an elephant-headed god, leaning back in the heap
	start = len(p.parts)
	p.box((0.42, 0.42, 0.12), (0, 0, 0.06), TARNISH)
	p.seg((0, 0, 0.1), (0, 0, 0.62), 0.22, 0.15, TARNISH, sides=8)
	for s in (-1, 1):
		p.seg((s * 0.15, 0, 0.55), (s * 0.2, -0.12, 0.35), 0.05, 0.04, TARNISH, sides=5)
	_elephant_head(p, (0, 0, 0.8), 0.26, swatch=TARNISH)
	_move_parts(p, start, Matrix.Translation((-0.45, 0.95, 1.5)) @ Matrix.Rotation(math.radians(-15), 4, "Z") @ Matrix.Rotation(math.radians(35), 4, "X"))
	# a bronze shield leaning on the side
	c, n = Vector((1.12, -0.55, 0.75)), Vector((1.0, 0.0, 0.25)).normalized()
	p.seg(c, c + n * 0.06, 0.55, 0.55, COPPER, sides=14, grad=(0.0, 0.8))
	p.blob((0.22, 0.22, 0.22), c + n * 0.06, GOLD, segs=(8, 6))
	return p.build(bevel=0.06)


def _goblet(p, x, y, z, s=1.0, swatch=STONE_DARK):
	"""A great stone goblet standing on (x, y, z), about 1.6 m at s = 1, with a silver band under its lip."""
	prof = [(0.02, 0.0), (0.6, 0.0), (0.55, 0.14), (0.16, 0.3), (0.14, 0.85), (0.42, 1.0), (0.62, 1.6), (0.55, 1.62), (0.38, 1.12), (0.02, 1.06)]
	obj = _lathe(p, [(r * s, h * s) for r, h in prof], 12, swatch, grad=(0.0, 0.85))
	obj.data.transform(Matrix.Translation((x, y, z)))
	p.seg((x, y, z + 1.42 * s), (x, y, z + 1.52 * s), 0.585 * s, 0.61 * s, SILVER, sides=12, grad=(0.0, 0.5))
	p.seg((x, y, z + 0.02), (x, y, z + 0.1 * s), 0.61 * s, 0.58 * s, SILVER, sides=12, grad=(0.0, 0.5))


def _candelabrum(p, d, x, y, z, s=1.0):
	"""A silver three-branched candelabrum on (x, y, z), about 2.6 m at s = 1,
	its tall candles burning with pale violet-white flames."""
	p.seg((x, y, z), (x, y, z + 0.3 * s), 0.55 * s, 0.25 * s, SILVER, sides=10, grad=(0.0, 0.7))
	p.seg((x, y, z + 0.3 * s), (x, y, z + 1.6 * s), 0.1 * s, 0.08 * s, SILVER, sides=8, grad=(0.0, 0.6))
	p.blob((0.3 * s, 0.3 * s, 0.25 * s), (x, y, z + 0.95 * s), SILVER, segs=(8, 5))
	tops = [(x, y, z + 1.95 * s)]
	for sgn in (-1, 1):
		_chain(p, [(x, y, z + 1.45 * s), (x + sgn * 0.45 * s, y, z + 1.4 * s), (x + sgn * 0.7 * s, y, z + 1.55 * s), (x + sgn * 0.72 * s, y, z + 1.7 * s)], 0.07 * s, 0.06 * s, SILVER, sides=6)
		tops.append((x + sgn * 0.72 * s, y, z + 1.7 * s))
	p.seg((x, y, z + 1.6 * s), (x, y, z + 1.95 * s), 0.08 * s, 0.1 * s, SILVER, sides=8)
	for tx, ty, tz in tops:
		p.seg((tx, ty, tz - 0.05 * s), (tx, ty, tz + 0.04 * s), 0.17 * s, 0.19 * s, SILVER, sides=8)     # the drip cup
		p.seg((tx, ty, tz), (tx, ty, tz + 0.6 * s), 0.1 * s, 0.09 * s, CLOTH_WHITE, sides=8, grad=(0.0, 0.4))
		d.seg((tx, ty, tz + 0.6 * s), (tx, ty, tz + 0.9 * s), 0.075 * s, 0.0, STARLIGHT, sides=6, grad=(0.0, 0.3), glow=2.6)
		d.blob((0.2 * s, 0.2 * s, 0.26 * s), (tx, ty, tz + 0.7 * s), VIOLET, segs=(6, 4), grad=(0.0, 0.35), glow=1.8)


def long_table():
	"""Timiraj's feasting table at the top of the world: a colossal table of
	dark stone 60 m long (along Y, so north-south once placed) and 12 m wide,
	its polished black top 3 m high inlaid with a silver border and a glowing
	violet runner set with silver star-discs, on a solid carved base (nothing
	to walk under) with pilasters banded in silver. Along each side stand six
	giant stone seats (seat 1.8 m, backs 6 m, violet cushions, silver moons on
	their backs) with room to walk between them to the table. On the top:
	great stone goblets, silver platters of bread, grapes and pomegranates, and
	silver candelabra burning pale violet-white. About 20 x 60 m. Collide it as
	a mesh."""
	p = Prop("long_table", 915)
	g = Prop("long_table_top", 916)
	d = Prop("long_table_detail", 917)
	rng = p.rng
	L, W, H = 60.0, 12.0, 3.0
	hl, hw = L / 2, W / 2
	p.box((W - 1.2, L - 1.2, H - 0.5 + 0.3), (0, 0, (H - 0.5 - 0.3) / 2), STONE_DARK, grad=(0.25, 1.0))
	p.box((W - 0.4, L - 0.4, 0.5), (0, 0, -0.05), STONE_DARK, grad=(0.3, 1.0))                   # the plinth course
	for y in (-hl + 0.9, -18.0, -6.0, 6.0, 18.0, hl - 0.9):                                   # pilasters down the sides
		for s in (-1, 1):
			p.box((1.2, 1.8, H - 0.6), (s * (hw - 0.8), y, (H - 0.6) / 2), IRON, grad=(0.1, 0.9))
			d.box((0.08, 0.3, H - 1.2), (s * (hw - 0.19), y, (H - 0.6) / 2), SILVER, grad=(0.0, 0.6))
	for s in (-1, 1):
		for x in (-3.5, 0.0, 3.5):
			p.box((1.8, 1.2, H - 0.6), (x, s * (hl - 0.8), (H - 0.6) / 2), IRON, grad=(0.1, 0.9))
	p.box((W + 0.2, L + 0.2, 0.3), (0, 0, H - 0.75), STONE_DARK, grad=(0.1, 0.8))                # the apron under the top
	d.box((W + 0.26, L + 0.26, 0.08), (0, 0, H - 0.8), SILVER, grad=(0.0, 0.5))
	g.box((W, L, 0.6), (0, 0, H - 0.3), OBSIDIAN, grad=(0.0, 0.85))
	# the inlay on the top
	for s in (-1, 1):
		d.box((0.14, L - 1.4, 0.04), (s * (hw - 0.7), 0, H + 0.01), SILVER, grad=(0.0, 0.4))
		d.box((W - 1.4, 0.14, 0.04), (0, s * (hl - 0.7), H + 0.01), SILVER, grad=(0.0, 0.4))
	d.box((2.6, L - 5.0, 0.03), (0, 0, H + 0.005), VIOLET, grad=(0.15, 0.5), glow=0.7)
	for y in (-26.0, -14.0, 0.0, 14.0, 26.0):
		d.seg((0, y, H), (0, y, H + 0.05), 0.9, 0.9, SILVER, sides=16, grad=(0.0, 0.5))
		d.seg((0, y, H), (0, y, H + 0.07), 0.45, 0.45, STARLIGHT, sides=12, grad=(0.0, 0.3), glow=1.2)
	# the seats
	for y in (-25.0, -15.0, -5.0, 5.0, 15.0, 25.0):
		for s in (-1, 1):
			x0 = s * (hw + 0.2)
			p.box((3.6, 4.4, 1.8), (x0 + s * 1.8, y, 0.9), STONE_DARK, grad=(0.1, 0.9))
			p.box((3.8, 4.6, 0.25), (x0 + s * 1.8, y, 1.75), IRON, grad=(0.0, 0.7))
			p.box((3.0, 3.8, 0.35), (x0 + s * 1.75, y, 2.02), VIOLET, grad=(0.1, 0.6))
			p.box((1.0, 4.4, 4.4), (x0 + s * 3.4, y, 4.0), STONE_DARK, grad=(0.05, 0.9))
			p.box((1.2, 4.7, 0.3), (x0 + s * 3.4, y, 6.3), IRON, grad=(0.0, 0.7))
			d.box((1.24, 4.74, 0.08), (x0 + s * 3.4, y, 6.12), SILVER, grad=(0.0, 0.5))
			for e in (-1, 1):
				p.box((3.0, 0.5, 1.0), (x0 + s * 1.9, y + e * 2.0, 2.3), STONE_DARK, grad=(0.1, 0.8))
			fx = x0 + s * 2.88
			d.seg((fx, y, 4.3), (fx - s * 0.06, y, 4.3), 0.85, 0.85, SILVER, sides=18, grad=(0.0, 0.5))
			d.seg((fx - s * 0.06, y, 4.3), (fx - s * 0.1, y, 4.3), 0.6, 0.6, OBSIDIAN, sides=18, grad=(0.6, 1.0))
			d.seg((fx - s * 0.06, y + 0.22, 4.3), (fx - s * 0.12, y + 0.22, 4.3), 0.48, 0.48, VIOLET, sides=14, grad=(0.1, 0.5), glow=0.8)
	# the feast
	for y in (-25.0, -5.0, 15.0, -15.0, 5.0, 25.0):
		for s in (-1, 1):
			_goblet(p, s * 3.6, y + s * 1.2, H, 1.0)
	for y, sx in ((-20.0, -1), (-10.0, 1), (0.0, -1), (10.0, 1), (20.0, -1)):
		x = sx * 2.4
		p.seg((x, y, H), (x, y, H + 0.14), 1.3, 1.45, SILVER, sides=16, grad=(0.0, 0.6))
		for k in range(3):
			a = k * math.tau / 3 + rng.uniform(0, 1)
			p.blob((0.7, 0.45, 0.4), (x + math.cos(a) * 0.55, y + math.sin(a) * 0.55, H + 0.3), HIDE, rot=(0, 0, math.degrees(a)), segs=(8, 5), grad=(0.0, 0.8))
		for k in range(9):
			p.blob((0.2, 0.2, 0.2), (x + rng.uniform(-0.25, 0.25), y - 0.1 + rng.uniform(-0.25, 0.25), H + 0.28 + (k // 4) * 0.13), VIOLET, segs=(6, 4), grad=(0.0, 0.8))
		p.blob((0.34, 0.34, 0.3), (x + 0.3, y + 0.75, H + 0.3), CLOTH_RED, segs=(8, 5), grad=(0.3, 1.0))
	for y in (-22.5, -7.5, 7.5, 22.5):
		_candelabrum(p, d, 0.0, y, H, 1.0)
	for y in (-28.0, 28.0):
		for x in (-1.2, 0.0, 1.2):
			_candle(p, (x, y, H), h=0.9 - abs(x) * 0.3, r=0.12)
	g = _glossy(g.build(bevel=0.04), 0.15)
	return join_into(p.build(bevel=0.06), [g, d.build()])


def table_throne():
	"""Timiraj's throne at the head of his table, about 14 m tall: a dais of
	dark stone 18 x 13 m and 2.4 m high with a polished black walkable top
	edged in silver and six steps down its front (-Y, toward the table); on
	it a massive empty black throne (seat 6 m up) with a violet cushion,
	armrests ending in stone elephant heads, a tall pointed back with a violet
	line and a silver crescent, and behind it a great eclipse ring (a black
	disc 7.2 m across in a glowing silver corona) on a stone stand, flanked by
	two black pillars crowned with moon-globes. Collide it as a mesh."""
	p = Prop("table_throne", 919)
	g = Prop("table_throne_glass", 920)
	d = Prop("table_throne_detail", 921)
	DW, DD, DH = 18.0, 13.0, 2.4
	p.box((DW - 0.2, DD - 0.2, DH + 0.05), (0, 0, (DH - 0.35) / 2), STONE_DARK, grad=(0.2, 1.0))
	g.box((DW, DD, 0.3), (0, 0, DH - 0.15), OBSIDIAN, grad=(0.0, 0.8))
	for s in (-1, 1):
		d.box((DW + 0.06, 0.08, 0.1), (0, s * (DD / 2 + 0.01), DH - 0.22), SILVER, grad=(0.0, 0.5))
		d.box((0.08, DD + 0.06, 0.1), (s * (DW / 2 + 0.01), 0, DH - 0.22), SILVER, grad=(0.0, 0.5))
	SW = 11.0
	for i in range(1, 6):                                                          # the steps down the front
		top = DH - 0.4 * i
		depth = 0.9 * i
		p.box((SW, depth, top + 0.3), (0, -DD / 2 - depth / 2 + 0.05, (top - 0.3) / 2), (IRON, STONE_DARK)[i % 2], grad=(0.1, 0.9))
		d.box((SW, 0.1, 0.06), (0, -DD / 2 - depth + 0.1, top), SILVER, grad=(0.0, 0.5))
	d.box((2.4, DD - 1.0, 0.03), (0, -0.5, DH + 0.01), VIOLET, grad=(0.15, 0.5), glow=0.6)       # a violet path to the throne
	# the throne
	SEAT = DH + 3.6
	p.box((9.0, 7.5, 0.6), (0, 1.8, DH + 0.3), IRON, grad=(0.0, 0.8))
	p.box((6.4, 5.2, 3.0), (0, 2.2, DH + 2.1), STONE_DARK, grad=(0.1, 0.9))
	d.box((6.5, 5.3, 0.14), (0, 2.2, SEAT - 0.35), SILVER, grad=(0.0, 0.5))
	p.box((5.6, 4.4, 0.35), (0, 2.1, SEAT + 0.17), VIOLET, grad=(0.1, 0.6))
	for s in (-1, 1):
		p.box((1.3, 5.0, 1.8), (s * 3.85, 2.2, SEAT + 0.9), STONE_DARK, grad=(0.05, 0.9))
		d.box((1.42, 5.1, 0.14), (s * 3.85, 2.2, SEAT + 1.85), SILVER, grad=(0.0, 0.5))
		_elephant_head(p, (s * 3.85, -0.55, SEAT + 1.1), 1.05, swatch=STONE_DARK)
	BY = 4.3
	p.box((6.8, 1.4, 5.4), (0, BY, SEAT + 2.7), STONE_DARK, grad=(0.05, 0.9))
	z0, z1 = SEAT + 5.4, SEAT + 6.4
	p.poly([(-3.4, BY - 0.7, z0), (3.4, BY - 0.7, z0), (0, BY - 0.7, z1), (-3.4, BY + 0.7, z0), (3.4, BY + 0.7, z0), (0, BY + 0.7, z1)],
		   [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], IRON, grad=(0.0, 0.8))
	d.box((0.26, 0.06, 4.2), (0, BY - 0.72, SEAT + 2.2), VIOLET, grad=(0.1, 0.5), glow=1.2)
	_crescent(d, (0, BY - 0.8, SEAT + 4.6), 0.9, swatch=SILVER)
	# the eclipse ring behind it
	EZ, ER, EY = SEAT + 3.6, 3.6, 6.3
	p.box((1.8, 1.4, EZ - ER - DH + 0.4), (0, EY + 0.3, DH + (EZ - ER - DH + 0.4) / 2), STONE_DARK, grad=(0.05, 0.9))
	g.seg((0, EY - 0.3, EZ), (0, EY + 0.3, EZ), ER, ER, OBSIDIAN, sides=40, grad=(0.5, 1.0))
	d.seg((0, EY - 0.15, EZ), (0, EY + 0.25, EZ), ER + 0.4, ER + 0.4, SILVER, sides=40, grad=(0.0, 0.3), glow=1.8)
	for k in range(20):
		a = k * math.tau / 20
		ln = ER + (1.0 if k % 2 == 0 else 0.65)
		d.seg((math.cos(a) * (ER + 0.3), EY, EZ + math.sin(a) * (ER + 0.3)), (math.cos(a + 0.04) * ln, EY, EZ + math.sin(a + 0.04) * ln),
			  0.24 if k % 2 == 0 else 0.17, 0.0, (SILVER, VIOLET)[k % 2], sides=4, grad=(0.0, 0.35), glow=1.5)
	# the pillars with moon-globes
	for s in (-1, 1):
		x = s * 6.0
		p.box((1.5, 1.5, 0.5), (x, 4.6, DH + 0.25), STONE_DARK, grad=(0.1, 0.8))
		g.seg((x, 4.6, DH + 0.5), (x, 4.6, DH + 9.4), 0.5, 0.4, OBSIDIAN, sides=8, grad=(0.0, 0.9), twist=22.5)
		for z in (DH + 1.2, DH + 5.0, DH + 9.0):
			d.seg((x, 4.6, z), (x, 4.6, z + 0.2), 0.52 - (z - DH) * 0.011, 0.52 - (z - DH) * 0.011, SILVER, sides=8, twist=22.5)
		p.seg((x, 4.6, DH + 9.4), (x, 4.6, DH + 9.8), 0.4, 0.6, STONE_DARK, sides=8, twist=22.5)
		_moon_globe(d, (x, 4.6, DH + 10.3), r=0.45)
	g = _glossy(g.build(bevel=0.03), 0.15)
	return join_into(p.build(bevel=0.06), [g, d.build()])


def feast_brazier():
	"""A tall silver brazier of Timiraj's feast, about 5 m to the flame tips: a
	stepped dark stone foot, a fluted silver column with collars and a violet
	stone, three curled silver legs, a wide silver bowl of white coals and a
	pale violet-white fire. Collide it as a box."""
	p = Prop("feast_brazier", 923)
	d = Prop("feast_brazier_flame", 924)
	p.box((1.5, 1.5, 0.35), (0, 0, 0.1), STONE_DARK, grad=(0.2, 0.9))
	p.box((1.1, 1.1, 0.25), (0, 0, 0.38), IRON, grad=(0.0, 0.7))
	p.seg((0, 0, 0.5), (0, 0, 0.85), 0.35, 0.14, SILVER, sides=10, grad=(0.0, 0.7))
	p.seg((0, 0, 0.85), (0, 0, 2.9), 0.12, 0.1, SILVER, sides=8, grad=(0.0, 0.6))
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.11, math.sin(a) * 0.11, 0.95), (math.cos(a) * 0.095, math.sin(a) * 0.095, 2.8), 0.025, 0.02, STONE_LIGHT, sides=3)
	for z in (1.2, 2.2):
		p.seg((0, 0, z), (0, 0, z + 0.12), 0.18, 0.18, IRON, sides=8)
	d.blob((0.3, 0.3, 0.3), (0, -0.14, 1.7), VIOLET, segs=(6, 4), grad=(0.0, 0.5), glow=1.2)
	p.seg((0, 0, 1.6), (0, 0, 1.8), 0.16, 0.16, SILVER, sides=8)
	for k in range(3):
		a = k * math.tau / 3 + math.pi / 2
		ca, sa = math.cos(a), math.sin(a)
		_chain(p, [(ca * 0.1, sa * 0.1, 2.3), (ca * 0.45, sa * 0.45, 2.55), (ca * 0.6, sa * 0.6, 2.85), (ca * 0.5, sa * 0.5, 3.05)], 0.05, 0.035, SILVER, sides=5)
		_chain(p, [(ca * 0.2, sa * 0.2, 0.55), (ca * 0.5, sa * 0.5, 0.3), (ca * 0.62, sa * 0.62, 0.05)], 0.06, 0.05, SILVER, sides=5)
	_lathe(p, [(0.14, 2.85), (0.75, 3.05), (0.92, 3.4), (0.84, 3.44), (0.66, 3.12), (0.14, 3.0)], 14, SILVER, grad=(0.0, 0.7))
	d.blob((1.4, 1.4, 0.3), (0, 0, 3.28), STARLIGHT, segs=(10, 5), grad=(0.1, 0.5), glow=1.0)
	_star_flame(d, (0, 0, 3.25), 0.55, 1.7, tongues=6, glow=2.0)
	return join_into(p.build(bevel=0.02), [d.build()])


def star_pillar():
	"""A slender pillar of Timiraj's Table, about 9.9 m: a dark stone foot, a
	glossy black octagonal shaft banded in silver with small violet lights,
	a flared capital and four silver prongs cradling a glowing star-white orb
	with pale blue star-points. Collide it as a box."""
	p = Prop("star_pillar", 925)
	g = Prop("star_pillar_glass", 926)
	d = Prop("star_pillar_star", 927)
	p.box((1.6, 1.6, 0.45), (0, 0, 0.1), STONE_DARK, grad=(0.2, 0.9))
	p.box((1.2, 1.2, 0.3), (0, 0, 0.45), IRON, grad=(0.0, 0.7))
	g.seg((0, 0, 0.6), (0, 0, 8.0), 0.42, 0.3, OBSIDIAN, sides=8, grad=(0.0, 0.9), twist=22.5)
	for z in (0.6, 2.4, 4.8, 7.2):
		r = 0.42 - 0.12 * (z - 0.6) / 7.4
		d.seg((0, 0, z), (0, 0, z + 0.14), r + 0.04, r + 0.04, SILVER, sides=8, grad=(0.0, 0.5), twist=22.5)
	for k in range(4):
		a = k * math.pi / 2 + math.pi / 8 * (k % 2)
		z = 3.4 + k * 0.9
		r = 0.42 - 0.12 * (z - 0.6) / 7.4
		d.box((0.12, 0.06, 0.4), (math.cos(a) * r, math.sin(a) * r, z), VIOLET, rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.4), glow=1.4)
	p.seg((0, 0, 8.0), (0, 0, 8.35), 0.3, 0.58, STONE_DARK, sides=8, twist=22.5)
	d.seg((0, 0, 8.35), (0, 0, 8.45), 0.6, 0.6, SILVER, sides=8, twist=22.5)
	for k in range(4):
		a = k * math.pi / 2 + math.pi / 4
		ca, sa = math.cos(a), math.sin(a)
		_chain(p, [(ca * 0.45, sa * 0.45, 8.4), (ca * 0.7, sa * 0.7, 8.85), (ca * 0.62, sa * 0.62, 9.45), (ca * 0.3, sa * 0.3, 9.85)], 0.06, 0.03, SILVER, sides=5)
	d.blob((1.0, 1.0, 1.0), (0, 0, 9.2), STARLIGHT, segs=(12, 8), grad=(0.0, 0.3), glow=2.6)
	for k in range(8):
		a = k * math.tau / 8
		e = 0.45 if k % 2 else 0.0
		dv = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e) * (1 if k % 4 == 1 else -1)))
		d.seg(Vector((0, 0, 9.2)) + dv * 0.4, Vector((0, 0, 9.2)) + dv * (1.0 if k % 2 == 0 else 0.8), 0.12, 0.0, SKY, sides=4, grad=(0.0, 0.3), glow=2.2)
	d.seg((0, 0, 9.6), (0, 0, 10.3), 0.12, 0.0, SKY, sides=4, grad=(0.0, 0.3), glow=2.2)
	g = _glossy(g.build(bevel=0.02), 0.15)
	return join_into(p.build(bevel=0.03), [g, d.build()])


def fallen_star():
	"""A star fallen on Timiraj's Table: a crater 11 m across with a low
	scorched rim (0.45 m, to walk over), a black glassy floor cracked with
	blue-white light, and in it a jagged star-rock glowing blue-white (about
	3 m to the tips of its crystal spikes), with shards of it strewn round.
	Collide it as a mesh."""
	p = Prop("fallen_star", 929)
	d = Prop("fallen_star_glow", 930)
	rng = p.rng
	p.seg((0, 0, -0.25), (0, 0, 0.03), 3.3, 3.3, IRON, sides=24, grad=(0.5, 1.0))
	_lathe(p, [(3.0, -0.25), (3.0, 0.05), (3.8, 0.34), (4.4, 0.42), (5.0, 0.22), (5.5, -0.25)], 32, WOOD_GRAY, grad=(0.1, 1.0), jitter=0.07)
	for k in range(10):                                                          # glowing cracks in the floor and out past the rim
		a = k * math.tau / 10 + rng.uniform(-0.2, 0.2)
		pts = [(math.cos(a) * r, math.sin(a) * r, 0.05) for r in (1.2, 2.0, 2.9)]
		pts = [(x + rng.uniform(-0.12, 0.12), y + rng.uniform(-0.12, 0.12), z) for x, y, z in pts]
		_chain(d, pts, 0.07, 0.03, SKY, sides=4, grad=(0.0, 0.3), glow=1.6)
		if k % 2 == 0:
			_chain(d, [(math.cos(a) * r, math.sin(a) * r, 0.02) for r in (5.5, 6.2, 6.9)], 0.05, 0.02, SKY, sides=4, grad=(0.0, 0.3), glow=1.2)
	d.rock((2.6, 2.2, 2.2), (0, 0, 0.8), STARLIGHT, grad=(0.0, 0.5), jitter=0.12)
	for o in d.parts[-1:]:
		o.data.materials[0] = atlas_material(1.6)
	for k in range(5):                                                           # a dark crust clinging to its foot
		a = k * math.tau / 5 + 0.4
		p.rock((1.1, 0.9, 0.7), (math.cos(a) * 1.05, math.sin(a) * 1.0, 0.2), IRON, rot=(0, 0, math.degrees(a)))
	for k in range(7):                                                           # crystal spikes
		a = k * math.tau / 7 + rng.uniform(-0.2, 0.2)
		up = rng.uniform(0.6, 1.3)
		base = Vector((math.cos(a) * 0.4, math.sin(a) * 0.4, 1.1))
		dv = Vector((math.cos(a), math.sin(a), up)).normalized()
		d.seg(base, base + dv * rng.uniform(1.2, 2.0), rng.uniform(0.25, 0.4), 0.0, (SKY, STARLIGHT)[k % 2], sides=5, grad=(0.0, 0.4), glow=2.0)
	d.seg((0.1, 0.0, 1.6), (0.25, -0.1, 3.1), 0.4, 0.0, STARLIGHT, sides=5, grad=(0.0, 0.3), glow=2.2)
	for k in range(9):                                                           # shards strewn round
		a, r = rng.uniform(0, math.tau), rng.uniform(1.8, 4.6)
		b = Vector((math.cos(a) * r, math.sin(a) * r, 0.0 if r < 3.0 else 0.25))
		d.seg(b, b + Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0.3, 0.6))), rng.uniform(0.1, 0.18), 0.0, SKY, sides=4, grad=(0.0, 0.4), glow=1.8)
	_rubble(p, (0, 0), 5.2, 12, (0.2, 0.5), swatches=(IRON, WOOD_GRAY), z=0.1)
	return join_into(p.build(bevel=0.04), [d.build()])


def hound_kennel_stones():
	"""Where Timiraj's hounds lair, about 14 m across: a ring of nine leaning
	black standing stones (3-4.6 m) scored with claw marks, some carved with
	silver crescents, iron rings on their inner faces with heavy chains lying
	across the ground toward the middle (one ending in a broken collar), and in
	the middle a great stone water bowl, with gnawed bones and skulls strewn
	about. Collide it as a mesh."""
	p = Prop("hound_kennel_stones", 931)
	g = Prop("hound_kennel_stones_glass", 932)
	d = Prop("hound_kennel_stones_detail", 933)
	rng = p.rng
	R = 6.2
	for k in range(9):
		a = k * math.tau / 9 + rng.uniform(-0.08, 0.08)
		ca, sa = math.cos(a), math.sin(a)
		h = rng.uniform(3.0, 4.6)
		lean = rng.uniform(0.1, 0.4)
		b = Vector((ca * R, sa * R, -0.3))
		t = Vector((ca * (R + lean), sa * (R + lean), h))
		g.seg(b, t, rng.uniform(0.6, 0.7), rng.uniform(0.3, 0.42), OBSIDIAN, sides=5, grad=(0.05, 0.9), jitter=0.06, twist=rng.uniform(0, 60))
		p.rock((1.6, 1.4, 0.5), (ca * R, sa * R, 0.05), STONE_DARK, rot=(0, 0, rng.uniform(0, 360)))
		yaw = math.degrees(a) - 90                     # the inner face looks toward the middle
		inner = Vector((ca * (R - 0.62), sa * (R - 0.62), 1.4))
		if k % 3 == 1:
			_crescent(d, tuple(Vector((ca * (R - 0.5 + lean * 0.4), sa * (R - 0.5 + lean * 0.4), 2.6))), 0.45, yaw=yaw, swatch=SILVER)
		if k % 2 == 0:
			_claw_marks(p, tuple(Vector((ca * (R - 0.62), sa * (R - 0.62), 2.0))), yaw, h=0.9)
		if k % 9 in (0, 2, 4, 6, 7):
			_torus(p, inner, (ca, sa, 0), (0, 0, 1), 0.22, 0.05, IRON, seg=10)
			end = Vector((ca * (R - 3.0), sa * (R - 3.0), 0.05)) + Vector((-sa, ca, 0)) * rng.uniform(-0.8, 0.8)
			mid = inner.lerp(end, 0.35)
			mid.z = 0.08
			_iron_chain(p, inner - Vector((ca, sa, 0)) * 0.25, mid, link=0.42, r=0.05)
			_iron_chain(p, mid, end, link=0.42, r=0.05)
			if k == 4:
				_torus(p, end + Vector((0, 0, 0.06)), (1, 0, 0), (0, 1, 0), 0.4, 0.07, IRON, seg=12)   # a broken collar
	# the water bowl
	_lathe(p, [(0.3, -0.2), (1.3, -0.2), (1.6, 0.35), (1.7, 0.8), (1.52, 0.86), (1.3, 0.45), (0.3, 0.38)], 16, STONE_DARK, grad=(0.0, 0.9))
	p.seg((0, 0, 0.3), (0, 0, 0.66), 1.45, 1.5, WATER, sides=16, grad=(0.6, 1.0))
	d.seg((0, 0, 0.78), (0, 0, 0.88), 1.72, 1.72, SILVER, sides=16, grad=(0.0, 0.5))
	# bones and skulls
	for k in range(14):
		a, r = rng.uniform(0, math.tau), rng.uniform(2.2, 5.2)
		c = Vector((math.cos(a) * r, math.sin(a) * r, 0.06))
		dv = Vector((math.cos(rng.uniform(0, math.tau)), math.sin(rng.uniform(0, math.tau)), 0)).normalized() * rng.uniform(0.35, 0.7)
		_bone(p, c - dv, c + dv, r=0.06)
	for k in range(4):
		a, r = rng.uniform(0, math.tau), rng.uniform(2.5, 4.8)
		_skull(p, (math.cos(a) * r, math.sin(a) * r, 0.0), s=1.6, yaw=rng.uniform(0, math.tau))
	g = _glossy(g.build(bevel=0.04), 0.3)
	return join_into(p.build(bevel=0.06), [g, d.build()])


# ---------------------------------------------------------------- The Grove

GROVE_STONE = BONE         # pale worn ivory stone, warming to beige down the sides
GROVE_TRIM = HIDE          # warm sandstone trim: the carved rim, the step noses
GROVE_FOOT = STONE_WARM    # the warm gray footing course
LOTUS_PINK = CORAL_PINK    # pale pink into rose
LILY_GREEN = LEAF          # lotus pads: lime into deep green
DAWN_LEAF = LEAF           # the canopy's sunlit tops (the swatch's yellow-lime top)
DAWN_GOLD = SLIME          # sunlit gold-lime highlights on the crown (the top of the swatch)
GOD_COLORS = {             # (inlay swatch, its tone on the swatch's gradient, glow)
	"light": (GOLD, 0.6, 0.5),
	"water": (TEAL, 0.45, 0.5),
	"fire": (CLOTH_RED, 0.55, 0.6),
	"wind": (LEAF, 0.5, 0.45),
	"dark": (IRON, 0.7, 0.0),
}


def _flat_fill(p, outline, z0, z1, swatch, tone=0.3, glow=0.0):
	"""A flat inlay in the XY plane from z0 to z1: `outline` [(x, y)] must be
	star-shaped round its centroid (it is fanned from there). Its top face
	takes the swatch's color at `tone` along the gradient."""
	cx = sum(x for x, _ in outline) / len(outline)
	cy = sum(y for _, y in outline) / len(outline)
	n = len(outline)
	verts = [(cx, cy, z0)] + [(x, y, z0) for x, y in outline] + [(cx, cy, z1)] + [(x, y, z1) for x, y in outline]
	faces = []
	for i in range(n):
		j = (i + 1) % n
		faces.append((0, 1 + j, 1 + i))
		faces.append((n + 1, n + 2 + i, n + 2 + j))
		faces.append((1 + i, 1 + j, n + 2 + j, n + 2 + i))
	obj = p.poly(verts, faces, swatch, grad=(tone, tone + 0.25))
	if glow:
		obj.data.materials[0] = atlas_material(glow)
	return obj


def _ribbon(p, pts, w0, w1, z0, z1, swatch, tone=0.3, glow=0.0, closed=False):
	"""A flat strip along the 2D polyline `pts`, its width tapering w0 -> w1,
	from z0 to z1: strokes of an inlaid symbol (spirals, waves, rings)."""
	n = len(pts)
	left, right = [], []
	for i in range(n):
		a = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
		b = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
		tx, ty = b[0] - a[0], b[1] - a[1]
		ln = max(math.hypot(tx, ty), 1e-6)
		nx, ny = -ty / ln, tx / ln
		w = (w0 + (w1 - w0) * i / max(n - 1, 1)) / 2
		left.append((pts[i][0] + nx * w, pts[i][1] + ny * w))
		right.append((pts[i][0] - nx * w, pts[i][1] - ny * w))
	verts = [(x, y, z1) for x, y in left] + [(x, y, z1) for x, y in right]
	verts += [(x, y, z0) for x, y in left] + [(x, y, z0) for x, y in right]
	L, R, LB, RB = 0, n, 2 * n, 3 * n
	faces = []
	for i in range(n if closed else n - 1):
		j = (i + 1) % n
		faces.append((L + i, R + i, R + j, L + j))
		faces.append((LB + i, LB + j, RB + j, RB + i))
		faces.append((L + i, L + j, LB + j, LB + i))
		faces.append((R + i, RB + i, RB + j, R + j))
	if not closed:
		faces.append((L, LB, RB, R))
		faces.append((L + n - 1, R + n - 1, RB + n - 1, LB + n - 1))
	obj = p.poly(verts, faces, swatch, grad=(tone, tone + 0.25))
	if glow:
		obj.data.materials[0] = atlas_material(glow)
	return obj


def _circle(r, n=24, cx=0.0, cy=0.0, phase=0.0):
	return [(cx + math.cos(phase + k * math.tau / n) * r, cy + math.sin(phase + k * math.tau / n) * r) for k in range(n)]


def _petal(c, a, length, width, n=6):
	"""A pointed petal outline from c along angle a (a vesica)."""
	cx, cy = c
	ca, sa = math.cos(a), math.sin(a)
	pts = []
	for k in range(n + 1):
		t = k / n
		w = math.sin(math.pi * t) ** 0.8 * width / 2
		pts.append((t * length, w))
	for k in range(n - 1, 0, -1):
		t = k / n
		w = math.sin(math.pi * t) ** 0.8 * width / 2
		pts.append((t * length, -w))
	return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


def _flame_outline(c, h, w, lean=0.0, n=16):
	"""A candle-flame outline standing at c (its round bottom), `h` tall along
	+Y, `w` wide, the tip leaning by `lean` meters."""
	cx, cy = c
	pts = []
	for k in range(n):
		t = k / n * math.tau
		# a teardrop: round below, drawn up to a point, the point swept sideways
		s = math.sin(t)
		y = -math.cos(t)                     # -1 bottom .. 1 top
		u = (y + 1) / 2
		x = s * w / 2 * (1 - u ** 1.6) ** 0.9
		yy = (u ** 1.15) * h
		pts.append((cx + x + lean * u ** 2.5, cy + yy - h * 0.06))
	return pts


def _grove_symbol(d, g, god, z):
	"""The god's symbol inlaid in a dais top at height z, about 5.8 m across,
	its 'up' toward +Y (away from the steps, so it reads upright from them)."""
	sw, tone, glow = GOD_COLORS[god]
	z0, z1 = z - 0.03, z + 0.015
	if god == "light":                                                   # the sun: a disc, a ring and twelve rays
		_flat_fill(d, _circle(1.25, 28), z0, z1, sw, tone - 0.2, glow)
		_ribbon(d, _circle(1.6, 32), 0.16, 0.16, z0, z1, sw, tone, glow, closed=True)
		for k in range(12):
			a = k * math.tau / 12 + math.tau / 24
			ln = 2.9 if k % 2 == 0 else 2.35
			ca, sa = math.cos(a), math.sin(a)
			n_ = (-sa, ca)
			wd = 0.34 if k % 2 == 0 else 0.26
			_flat_fill(d, [(ca * 1.85 + n_[0] * wd, sa * 1.85 + n_[1] * wd), (ca * ln, sa * ln), (ca * 1.85 - n_[0] * wd, sa * 1.85 - n_[1] * wd)], z0, z1, sw, tone, glow)
	elif god == "water":                                                 # a lotus of eight petals in a ring of waves
		for k in range(8):
			a = math.pi / 2 + k * math.tau / 8
			_flat_fill(d, _petal((math.cos(a) * 0.35, math.sin(a) * 0.35), a, 1.55, 0.72), z0, z1, sw, tone - 0.15, glow)
		for k in range(8):
			a = math.pi / 2 + (k + 0.5) * math.tau / 8
			_flat_fill(d, _petal((math.cos(a) * 0.3, math.sin(a) * 0.3), a, 1.05, 0.5), z0, z1, sw, tone + 0.15, glow)
		_flat_fill(d, _circle(0.45, 16), z0, z1 + 0.004, sw, tone - 0.3, glow)
		wave = [((2.35 + 0.2 * math.sin(k * math.tau / 96 * 9)) * math.cos(k * math.tau / 96), (2.35 + 0.2 * math.sin(k * math.tau / 96 * 9)) * math.sin(k * math.tau / 96)) for k in range(96)]
		_ribbon(d, wave, 0.2, 0.2, z0, z1, sw, tone, glow, closed=True)
		for k in range(9):                                               # wave crests curling outward
			a = (k + 0.25) * math.tau / 9
			pts = []
			for j in range(7):
				t = j / 6
				r = 2.62 + 0.28 * t
				b = a + 0.32 * t
				pts.append((math.cos(b) * r, math.sin(b) * r))
			_ribbon(d, pts, 0.16, 0.05, z0, z1, sw, tone, glow)
	elif god == "fire":                                                  # a great flame with two tongues beside it
		_flat_fill(d, _flame_outline((0, -2.0), 4.6, 2.3, lean=0.35), z0, z1, sw, tone, glow)
		_flat_fill(d, _flame_outline((0.05, -1.7), 2.7, 1.2, lean=0.2), z0, z1 + 0.004, FLAME, 0.35, glow + 0.3)
		for s in (-1, 1):
			_flat_fill(d, _flame_outline((s * 1.55, -1.75), 2.2, 0.95, lean=-s * 0.45), z0, z1, sw, tone + 0.1, glow)
		_ribbon(d, [(-2.0, -2.25), (-1.0, -2.45), (0, -2.5), (1.0, -2.45), (2.0, -2.25)], 0.18, 0.18, z0, z1, EMBER, 0.3, glow)
	elif god == "wind":                                                  # a spiral with three gusts streaming from it
		pts = []
		for k in range(70):
			t = k / 69
			a = math.pi / 2 + t * math.tau * 2.4
			r = 0.12 + 1.75 * t
			pts.append((math.cos(a) * r, math.sin(a) * r))
		_ribbon(d, pts, 0.1, 0.34, z0, z1, sw, tone, glow)
		for k in range(3):
			a0 = math.pi / 2 + math.tau * 2.4 + 0.5 + k * math.tau / 3
			gust = []
			for j in range(14):
				t = j / 13
				a = a0 + t * 1.25
				r = 2.1 + t * 0.75 + 0.1 * math.sin(t * math.pi * 2)
				gust.append((math.cos(a) * r, math.sin(a) * r))
			_ribbon(d, gust, 0.3, 0.04, z0, z1, sw, tone + 0.1, glow)
	elif god == "dark":                                                  # the eclipse: a black sun in a silver corona
		g_ = _flat_fill(g, _circle(1.85, 32), z0, z1 + 0.004, OBSIDIAN, 0.75)
		_ribbon(d, _circle(1.98, 36), 0.26, 0.26, z0, z1, SILVER, 0.0, 0.9, closed=True)
		for k in range(16):
			a = k * math.tau / 16
			ln = 2.9 if k % 2 == 0 else 2.5
			ca, sa = math.cos(a), math.sin(a)
			wd = 0.16 if k % 2 == 0 else 0.11
			_flat_fill(d, [(ca * 2.1 - sa * wd, sa * 2.1 + ca * wd), (ca * ln, sa * ln), (ca * 2.1 + sa * wd, sa * 2.1 - ca * wd)], z0, z1, SILVER, 0.05, 0.6)
		_flat_fill(d, _circle(3.1, 40), z0 - 0.004, z1 - 0.006, STONE_DARK, 0.3)                       # a slate field so the silver shows


def grove_dais(god):
	"""A god's dais in the Grove: a broad round platform of pale worn stone,
	12 m across, its flat walkable top 0.8 m up, three low steps on the -Y
	side (toward the pond), a carved rim of warm sandstone with inlaid studs,
	and the god's symbol inlaid in the top in the god's color, glowing softly;
	a ring of the same color runs inside the rim and two lamps burn at the
	foot of the steps, so the empty dais still reads as waiting for its god.
	Base center at the origin. Collide it as a mesh (the steps are walkable)."""
	seed = 950 + ("light", "water", "fire", "wind", "dark").index(god) * 3
	p = Prop(f"grove_dais_{god}", seed)
	g = Prop(f"grove_dais_{god}_glass", seed + 1)
	d = Prop(f"grove_dais_{god}_inlay", seed + 2)
	sw, tone, glow = GOD_COLORS[god]
	accent_sw, accent_tone, accent_glow = (SILVER, 0.0, 0.8) if god == "dark" else (sw, tone, glow)
	TOP = 0.8
	p.seg((0, 0, -0.4), (0, 0, 0.14), 6.35, 6.25, GROVE_FOOT, sides=40, grad=(0.25, 1.0))              # the footing course
	p.seg((0, 0, 0.1), (0, 0, TOP - 0.16), 5.9, 5.85, GROVE_STONE, sides=40, grad=(0.25, 0.95))         # the drum
	_lathe(p, [(5.45, TOP - 0.2), (6.02, TOP - 0.2), (6.08, TOP - 0.1), (6.02, TOP), (5.45, TOP)], 40, GROVE_TRIM, grad=(0.05, 0.6))   # the carved rim
	p.seg((0, 0, TOP - 0.18), (0, 0, TOP), 5.5, 5.5, GROVE_STONE, sides=40, grad=(0.05, 0.5))          # the top
	for k in range(40):                                                   # carved dentils under the rim
		a = (k + 0.5) * math.tau / 40
		if abs(math.degrees(a) - 270) < 26:
			continue
		p.box((0.26, 0.14, 0.18), (math.cos(a) * 5.9, math.sin(a) * 5.9, TOP - 0.3), GROVE_TRIM, rot=(0, 0, math.degrees(a) + 90), grad=(0.1, 0.7))
	for k in range(10):                                                   # relief panels round the drum: lotus petals in low relief
		a = math.pi / 2 + k * math.tau / 10
		if abs(math.degrees(a % math.tau) - 270) < 30:
			continue
		ca, sa = math.cos(a), math.sin(a)
		for j in (-1, 0, 1):
			b = a + j * 0.075
			p.blob((0.34, 0.16, 0.34 if j else 0.4), (math.cos(b) * 5.9, math.sin(b) * 5.9, 0.38), GROVE_TRIM, rot=(0, j * 25, math.degrees(b) + 90), segs=(8, 5), grad=(0.1, 0.7))
		d.box((0.12, 0.06, 0.12), (ca * 5.93, sa * 5.93, 0.62), accent_sw, rot=(45, 0, math.degrees(a) + 90), grad=(accent_tone, accent_tone + 0.2), glow=accent_glow)
	for k in range(20):                                                   # studs of the god's color set into the rim
		a = (k + 0.5) * math.tau / 20
		_flat_fill(d, [(math.cos(a) * 5.62 + dx, math.sin(a) * 5.62 + dy) for dx, dy in
					  ((math.cos(a) * 0.16, math.sin(a) * 0.16), (-math.sin(a) * 0.1, math.cos(a) * 0.1), (-math.cos(a) * 0.16, -math.sin(a) * 0.16), (math.sin(a) * 0.1, -math.cos(a) * 0.1))],
				   TOP - 0.03, TOP + 0.012, accent_sw, accent_tone, accent_glow)
	_ribbon(d, _circle(5.1, 64), 0.16, 0.16, TOP - 0.03, TOP + 0.012, accent_sw, accent_tone, accent_glow, closed=True)   # a ring inside the rim
	_ribbon(d, _circle(3.35, 48), 0.07, 0.07, TOP - 0.03, TOP + 0.01, GROVE_TRIM, 0.3, closed=True)                         # a fine carved ring round the symbol
	for k in range(18):                                                   # the paving: radial joints between the rings
		a = (k + 0.5) * math.tau / 18
		_ribbon(d, [(math.cos(a) * 3.45, math.sin(a) * 3.45), (math.cos(a) * 5.0, math.sin(a) * 5.0)], 0.05, 0.05, TOP - 0.03, TOP + 0.006, GROVE_TRIM, 0.35)
	_ribbon(d, _circle(4.25, 48), 0.05, 0.05, TOP - 0.03, TOP + 0.006, GROVE_TRIM, 0.35, closed=True)
	for k in range(7):                                                    # moss where the footing meets the ground
		a = p.rng.uniform(0, math.tau)
		if abs(math.degrees(a) - 270) < 35:
			continue
		p.blob((1.2, 0.4, 0.24), (math.cos(a) * 6.22, math.sin(a) * 6.22, 0.0), MOSS, rot=(0, 0, math.degrees(a) + 90), segs=(7, 4), grad=(0.45, 1.0))
	_grove_symbol(d, g, god, TOP)
	for k, (w, y1, z) in enumerate(((5.0, -6.55, 0.6), (5.6, -7.05, 0.4), (6.2, -7.55, 0.2))):        # three steps down toward the pond
		p.box((w, -5.3 - y1, z + 0.4), (0, (y1 - 5.3) / 2, (z - 0.4) / 2), GROVE_STONE, grad=(0.1, 0.9))
		p.box((w + 0.08, 0.2, 0.08), (0, y1 + 0.08, z - 0.035), GROVE_TRIM, grad=(0.05, 0.5))
	for s in (-1, 1):                                                     # the step lamps: stone posts, a bowl of the god's light
		x, y = s * 3.6, -7.3
		p.box((0.7, 0.7, 0.3), (x, y, 0.05), GROVE_FOOT, grad=(0.1, 0.9))
		p.seg((x, y, 0.2), (x, y, 1.0), 0.2, 0.16, GROVE_STONE, sides=8, grad=(0.1, 0.9))
		_lathe(p, [(0.08, 0.95), (0.2, 1.0), (0.42, 1.18), (0.4, 1.24), (0.1, 1.14)], 12, GROVE_TRIM, grad=(0.05, 0.7)).data.transform(Matrix.Translation((x, y, 0)))
		if god == "dark":
			g.blob((0.34, 0.34, 0.3), (x, y, 1.28), OBSIDIAN, segs=(10, 6), grad=(0.3, 1.0))
			_ribbon(d, _circle(0.2, 10, x, y), 0.05, 0.05, 1.2, 1.24, SILVER, 0.0, 1.4, closed=True)
		elif god == "fire":
			_flame_column_small(d, (x, y, 1.14), 0.2, 0.55, glow=2.0)
		else:
			d.blob((0.36, 0.36, 0.3), (x, y, 1.26), sw, segs=(10, 6), grad=(0.0, 0.4), glow=glow + 1.2)
	if god == "dark":
		gobj = _glossy(g.build(bevel=0.0), 0.12)
		return join_into(p.build(bevel=0.05), [gobj, d.build()])
	return join_into(p.build(bevel=0.05), [d.build()])


def _flame_column_small(d, c, r, h, glow=2.0):
	x, y, z = c
	d.seg((x, y, z), (x, y, z + h), r, 0.0, FLAME, sides=6, grad=(0.0, 0.5), glow=glow)
	for k in range(3):
		a = k * math.tau / 3
		d.seg((x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z), (x + math.cos(a + 0.4) * r * 0.4, y + math.sin(a + 0.4) * r * 0.4, z + h * 0.65), r * 0.55, 0.0, EMBER, sides=5, grad=(0.0, 0.5), glow=glow)


def _banyan(name, seed, trunk_pts, trunk_r, limbs, crown, pillars, lean=(0.0, 0.0)):
	"""A colossal banyan. `trunk_pts` the main stem's spine, `trunk_r` its
	radius at the foot; fused stems wind round it and buttress roots flare at
	the ground. `limbs` [(angle, z0, reach, rise)] are great near-level
	branches, each with a few pillar roots dropping to the ground and thin
	aerial roots hanging part way. `crown` [(x, y, z, sx, sy, sz)] adds leaf
	masses over the middle; `pillars` how many pillar roots per limb."""
	p = Prop(name, seed)
	rng = p.rng
	_chain(p, trunk_pts, trunk_r, trunk_r * 0.62, WOOD_GRAY, sides=12, grad=(0.15, 1.0))
	top = trunk_pts[-1]
	for k in range(9):                                                    # fused stems wound round the trunk
		a0 = k * math.tau / 9 + rng.uniform(-0.15, 0.15)
		pts = []
		for j in range(8):
			t = j / 7
			sp = trunk_pts[min(int(t * (len(trunk_pts) - 1)), len(trunk_pts) - 2)]
			sp2 = trunk_pts[min(int(t * (len(trunk_pts) - 1)) + 1, len(trunk_pts) - 1)]
			f = t * (len(trunk_pts) - 1) - int(t * (len(trunk_pts) - 1))
			cx = sp[0] + (sp2[0] - sp[0]) * f
			cy = sp[1] + (sp2[1] - sp[1]) * f
			a = a0 + t * 0.9
			r = trunk_r * (0.95 - 0.35 * t) + (1.2 * (1 - t) ** 3)
			pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, -0.4 + t * (top[2] + 0.4) * 0.95))
		_chain(p, pts, trunk_r * 0.42, trunk_r * 0.22, WOOD, sides=7, grad=(0.25, 1.0))
	for k in range(10):                                                   # the flare of buttress roots
		a = k * math.tau / 10 + rng.uniform(-0.2, 0.2)
		_fin(p, a, trunk_r * 0.9, rng.uniform(2.2, 3.6), trunk_r + rng.uniform(1.8, 3.2), 0.5, WOOD_GRAY, grad=(0.3, 1.0), z0=-0.4)
	tips = []
	for (ang, z0, reach, rise) in limbs:
		a = math.radians(ang)
		ca, sa = math.cos(a), math.sin(a)
		ox, oy = top[0] * (z0 / top[2]), top[1] * (z0 / top[2])
		pts = [(ox + ca * trunk_r * 0.5, oy + sa * trunk_r * 0.5, z0)]
		for j in range(1, 5):
			t = j / 4
			pts.append((ox + ca * reach * t + rng.uniform(-0.4, 0.4), oy + sa * reach * t + rng.uniform(-0.4, 0.4), z0 + rise * math.sin(t * math.pi * 0.6) + rng.uniform(-0.3, 0.3)))
		_chain(p, pts, trunk_r * 0.32, 0.3, WOOD_GRAY, sides=8, grad=(0.15, 1.0))
		for j in (2, 3):                                                  # a side branch off the limb
			b = a + rng.choice((-1, 1)) * rng.uniform(0.5, 0.9)
			q = pts[j]
			e = (q[0] + math.cos(b) * reach * 0.35, q[1] + math.sin(b) * reach * 0.35, q[2] + rng.uniform(1.0, 2.5))
			_chain(p, [q, e], 0.45, 0.18, WOOD_GRAY, sides=6, grad=(0.15, 1.0))
			tips.append(e)
		tips.append(pts[-1])
		tips.append(pts[2])
		for j in range(pillars):                                          # pillar roots: thick, reaching the ground
			t = 0.45 + 0.4 * j / max(pillars - 1, 1) + rng.uniform(-0.05, 0.05)
			i = t * 4
			q0, q1 = pts[int(i)], pts[min(int(i) + 1, 4)]
			f = i - int(i)
			x, y, z = (q0[0] + (q1[0] - q0[0]) * f, q0[1] + (q1[1] - q0[1]) * f, q0[2] + (q1[2] - q0[2]) * f - 0.3)
			col = [(x, y, z)]
			for m in range(1, 5):
				col.append((x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), z - (z + 0.4) * m / 4))
			r = rng.uniform(0.4, 0.6)
			_chain(p, col, r * 0.6, r, WOOD, sides=7, grad=(0.2, 1.0))
			for m in range(3):                                            # where it has rooted: a small flare
				b = rng.uniform(0, math.tau)
				_fin(p, b, r * 0.8, rng.uniform(0.8, 1.4), r + rng.uniform(0.5, 0.9), 0.22, WOOD, grad=(0.3, 1.0), z0=-0.4)
				p.parts[-1].data.transform(Matrix.Translation((col[-1][0], col[-1][1], 0)))
		for j in range(rng.randint(4, 6)):                               # thin aerial roots hanging part way down
			t = rng.uniform(0.25, 0.95)
			i = t * 4
			q0, q1 = pts[int(i)], pts[min(int(i) + 1, 4)]
			f = i - int(i)
			x, y, z = (q0[0] + (q1[0] - q0[0]) * f + rng.uniform(-0.5, 0.5), q0[1] + (q1[1] - q0[1]) * f + rng.uniform(-0.5, 0.5), q0[2] + (q1[2] - q0[2]) * f - 0.2)
			ln = rng.uniform(0.3, 0.75) * z
			strand = [(x, y, z)]
			for m in range(1, 4):
				strand.append((x + rng.uniform(-0.15, 0.15), y + rng.uniform(-0.15, 0.15), z - ln * m / 3))
			_chain(p, strand, 0.09, 0.04, WOOD, sides=4, grad=(0.2, 0.9))
	for i, (x, y, z) in enumerate(tips):                                  # the canopy: broad flat masses, dark beneath, sunlit gold-green on top
		s = rng.uniform(8.5, 11.0)
		p.rock((s, s, s * 0.32), (x, y, z + 1.0), PINE, rot=(0, 0, rng.uniform(0, 360)), grad=(0.35, 1.0), jitter=0.06)
		p.rock((s * 0.78, s * 0.78, s * 0.3), (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), z + 2.1), DAWN_LEAF, rot=(0, 0, rng.uniform(0, 360)), grad=(0.0, 0.7), jitter=0.06)
		if i % 3 == 0:
			p.rock((s * 0.42, s * 0.42, s * 0.16), (x + rng.uniform(-1.5, 1.5), y + rng.uniform(-1.5, 1.5), z + 2.9), DAWN_GOLD, rot=(0, 0, rng.uniform(0, 360)), grad=(0.0, 0.3), jitter=0.06)
	for (x, y, z, sx, sy, sz) in crown:
		p.rock((sx, sy, sz), (x, y, z), PINE, rot=(0, 0, rng.uniform(0, 360)), grad=(0.3, 1.0), jitter=0.05)
		p.rock((sx * 0.75, sy * 0.75, sz * 0.75), (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), z + sz * 0.36), DAWN_LEAF, rot=(0, 0, rng.uniform(0, 360)), grad=(0.0, 0.7), jitter=0.05)
		p.rock((sx * 0.38, sy * 0.38, sz * 0.36), (x + rng.uniform(-2, 2), y + rng.uniform(-2, 2), z + sz * 0.62), DAWN_GOLD, rot=(0, 0, rng.uniform(0, 360)), grad=(0.0, 0.3), jitter=0.05)
	for k in range(8):                                                    # moss in the folds of the trunk
		a = rng.uniform(0, math.tau)
		zz = rng.uniform(1.0, top[2] * 0.6)
		p.blob((1.4, 1.4, 0.5), (top[0] * zz / top[2] + math.cos(a) * trunk_r * 0.95, top[1] * zz / top[2] + math.sin(a) * trunk_r * 0.95, zz), MOSS, rot=(0, 0, math.degrees(a)), segs=(6, 4), grad=(0.2, 0.9))
	return p.build()


def grove_tree_a():
	"""A colossal banyan for the Grove's rim, about 31 m: a trunk of fused
	stems 5 m across above a flare of buttress roots, six great near-level
	limbs reaching 12-14 m out, each propped on pillar roots with thin aerial
	roots hanging between, and a broad canopy about 34 m across, dark green
	below and sunlit gold-green on top. Collide it as a mesh (the trunk and
	the pillar roots stop players; the "trunk" collider is far too thin)."""
	limbs = [(10, 13.0, 13.5, 3.0), (72, 14.5, 12.0, 2.5), (135, 12.5, 14.0, 3.5), (195, 14.0, 12.5, 2.5), (255, 13.0, 13.0, 3.0), (315, 15.0, 11.5, 2.0)]
	crown = [(0, 0, 22.0, 22.0, 20.0, 6.5), (2.5, -1.5, 25.5, 13.0, 12.0, 5.0), (-4.5, 3.5, 23.5, 12.0, 11.0, 4.5)]
	return _banyan("grove_tree_a", 961, [(0, 0, -0.4), (0.2, 0.1, 7.0), (0.1, 0.4, 13.0), (0.4, 0.2, 20.0)], 2.5, limbs, crown, 2)


def grove_tree_b():
	"""The Grove's second banyan, about 28 m: a leaning, older tree whose
	trunk swells to 6 m across, its limbs all to one side (+X), low and long,
	so a wall of pillar roots stands under that side like columns, and a
	lopsided canopy. Collide it as a mesh."""
	limbs = [(-20, 11.0, 15.0, 2.0), (25, 12.0, 16.0, 2.5), (70, 10.0, 11.0, 3.0), (-70, 12.5, 11.0, 3.0), (160, 14.0, 8.5, 3.5), (215, 13.5, 8.0, 3.0)]
	crown = [(4.0, 0, 19.5, 22.0, 17.0, 6.0), (7.0, 2.0, 23.0, 12.0, 10.0, 4.8), (-1.0, -2.5, 21.5, 10.0, 9.0, 4.2)]
	return _banyan("grove_tree_b", 962, [(0, 0, -0.4), (0.4, 0.0, 6.0), (1.3, 0.3, 11.0), (2.0, 0.2, 17.0)], 3.0, limbs, crown, 3)


def _lotus_pad(p, c, r, yaw, z=0.0):
	"""A floating lotus pad at c: a disc with a notch cut to its middle, its
	top just clear of the water at z."""
	cx, cy = c
	notch = 0.5
	outline = [(cx, cy)]
	for k in range(15):
		a = math.radians(yaw) + notch / 2 + (math.tau - notch) * k / 14
		rr = r * (1 + 0.03 * math.sin(k * 2.3))
		outline.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
	n = len(outline)
	verts = [(x, y, z - 0.015) for x, y in outline] + [(x, y, z + 0.02 + (0.0 if i == 0 else 0.012)) for i, (x, y) in enumerate(outline)]
	faces = [(0, i + 1, i) for i in range(1, n - 1)] + [(n, n + i, n + i + 1) for i in range(1, n - 1)]
	for i in range(n):
		j = (i + 1) % n
		faces.append((i, j, n + j, n + i))
	obj = p.poly(verts, faces, LILY_GREEN, grad=(0.35, 0.7))
	for k in range(5):                                                    # veins from the middle
		a = math.radians(yaw) + 0.6 + k * (math.tau - 1.2) / 4
		_ribbon(p, [(cx, cy), (cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8)], 0.018, 0.006, z + 0.02, z + 0.034, LILY_GREEN, 0.25)
	return obj


def lotus_pad():
	"""A cluster of four lotus pads, about 1.5 m across overall, floating on
	the water at y = 0 (their undersides dip 1.5 cm in). No collision."""
	p = Prop("lotus_pad", 971)
	for (x, y, r, yaw) in ((0.0, 0.0, 0.42, 20), (0.5, 0.35, 0.3, 160), (-0.45, 0.3, 0.26, 250), (0.2, -0.5, 0.22, 80)):
		_lotus_pad(p, (x, y), r, yaw)
	return p.build()


def lotus_bloom():
	"""One lotus pad (0.9 m) with an open pink-white lotus flower on it, about
	0.35 m tall, a gold seed pod in its heart, and a closed bud beside it. Floats
	at y = 0. No collision."""
	p = Prop("lotus_bloom", 972)
	_lotus_pad(p, (0, 0), 0.45, 200)
	_lotus_pad(p, (0.55, -0.25), 0.2, 30)
	cz = 0.05
	for ring, (n, ln, wd, tilt, z, tone) in enumerate(((8, 0.3, 0.17, 14, 0.0, (0.25, 0.7)), (8, 0.27, 0.16, 42, 0.02, (0.05, 0.5)), (6, 0.21, 0.14, 68, 0.04, (0.0, 0.35)))):
		for k in range(n):
			a = k * math.tau / n + ring * math.pi / n
			# a petal: a thin cupped ellipsoid leaning out from the middle
			ca, sa = math.cos(a), math.sin(a)
			t = math.radians(tilt)
			dist = ln * 0.5 * math.cos(t)
			p.blob((ln, wd, 0.04), (ca * (0.04 + dist), sa * (0.04 + dist), cz + z + ln * 0.5 * math.sin(t)), LOTUS_PINK if ring < 2 else PETAL_WHITE,
				   rot=(0, -tilt, math.degrees(a)), segs=(8, 4), grad=tone)
	p.seg((0, 0, cz + 0.05), (0, 0, cz + 0.13), 0.055, 0.07, GOLD, sides=10, grad=(0.3, 0.7))            # the seed pod
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.07, math.sin(a) * 0.07, cz + 0.09), (math.cos(a) * 0.1, math.sin(a) * 0.1, cz + 0.15), 0.008, 0.008, PETAL_YELLOW, sides=3)
	p.seg((0.62, -0.28, 0.0), (0.66, -0.3, 0.22), 0.018, 0.016, LILY_GREEN, sides=5, grad=(0.3, 0.7))    # a bud on its stem
	p.blob((0.1, 0.1, 0.17), (0.66, -0.3, 0.29), LOTUS_PINK, segs=(8, 5), grad=(0.1, 0.6))
	p.seg((0.66, -0.3, 0.33), (0.665, -0.3, 0.4), 0.03, 0.0, LOTUS_PINK, sides=5, grad=(0.5, 0.7))
	return p.build(bevel=0.0)


def tusk_arch():
	"""The Grove's arrival gate: two colossal pale carved tusks rising from
	stone footings 5 m apart (inside), curving in to cross overhead at about
	6.2 m, bound there by a gold clasp set with five glowing gems (the five
	gods' colors), gold bands and carved rings along each tusk. They stand on
	a low stone threshold 8 x 3 m (0.2 m high, walkable) where players arrive.
	The opening faces -Y and +Y. Collide it as a mesh."""
	p = Prop("tusk_arch", 981)
	d = Prop("tusk_arch_gems", 982)
	p.box((8.4, 3.0, 0.5), (0, 0, -0.05), GROVE_FOOT, grad=(0.1, 0.9))                              # the threshold
	p.box((4.6, 2.8, 0.06), (0, 0, 0.2), GROVE_STONE, grad=(0.05, 0.4))
	_ribbon(p, _circle(0.95, 32), 0.1, 0.1, 0.2, 0.245, GROVE_TRIM, 0.2, closed=True)                   # where arrivals stand
	for k, god in enumerate(("light", "water", "fire", "wind", "dark")):
		sw, tone, glow = GOD_COLORS[god]
		a = math.pi / 2 + k * math.tau / 5
		_flat_fill(d, _circle(0.12, 10, math.cos(a) * 0.95, math.sin(a) * 0.95), 0.2, 0.25, SILVER if god == "dark" else sw, 0.0 if god == "dark" else tone, 0.8 if god == "dark" else glow)
	for s in (-1, 1):
		x = s * 3.2
		p.box((1.9, 2.2, 1.0), (x, 0, 0.5), GROVE_STONE, grad=(0.1, 0.9))                           # the footing
		p.box((2.1, 2.4, 0.18), (x, 0, 1.05), GROVE_TRIM, grad=(0.05, 0.6))
		p.seg((x, 0, 1.1), (x, 0, 1.45), 0.85, 0.72, GROVE_TRIM, sides=12, grad=(0.05, 0.7))       # the socket collar
		for k in range(6):                                                                         # carved petals round the collar
			a = k * math.tau / 6
			p.blob((0.4, 0.2, 0.5), (x + math.cos(a) * 0.82, math.sin(a) * 0.82, 1.3), GROVE_STONE, rot=(0, 20, math.degrees(a) + 90), segs=(6, 4), grad=(0.05, 0.6))
		for y in (-1, 1):                                                                          # carved panels on the footing's faces
			p.box((1.3, 0.06, 0.6), (x, y * 1.12, 0.5), GROVE_TRIM, grad=(0.1, 0.7))
			p.seg((x, y * 1.14, 0.5), (x, y * 1.19, 0.5), 0.2, 0.17, GOLD, sides=12, grad=(0.1, 0.5))
			for k in range(8):
				a = k * math.tau / 8
				p.seg((x + math.cos(a) * 0.19, y * 1.16, 0.5 + math.sin(a) * 0.19), (x + math.cos(a) * 0.3, y * 1.16, 0.5 + math.sin(a) * 0.3), 0.05, 0.0, GOLD, sides=4, grad=(0.1, 0.5))
		# the tusk: a curve from the socket up and in, crossing the middle
		pts = []                                                          # an elliptic sweep: straight up from the socket, bending in to cross past the middle
		for k in range(13):
			th = math.radians(66 * k / 12)
			pts.append(Vector((s * (-3.8 + 7.0 * math.cos(th)), -s * 0.3 * math.sin(th) ** 3, 1.25 + 5.66 * math.sin(th))))
		_chain(p, [tuple(q) for q in pts], 0.64, 0.1, IVORY, sides=10, grad=(0.0, 0.7))
		for k in (2, 5, 8):                                               # gold bands with carved rings between
			a, b = pts[k], pts[k + 1]
			dv = (b - a).normalized()
			r = 0.64 - 0.54 * k / 12
			p.seg(tuple(a - dv * 0.13), tuple(a + dv * 0.13), r + 0.06, r + 0.05, GOLD, sides=10, grad=(0.1, 0.6))
			m = a.lerp(b, 0.5)
			p.seg(tuple(m - dv * 0.04), tuple(m + dv * 0.04), r + 0.02, r + 0.015, BONE, sides=10, grad=(0.4, 0.8))
	# the clasp where the tusks cross: a gold band round both, five gems of the gods' colors on its underside
	cz = 6.0
	p.seg((-0.26, 0, cz), (0.26, 0, cz), 0.56, 0.56, GOLD, sides=14, grad=(0.15, 0.7))
	for x in (-0.27, 0.27):
		p.seg((x - 0.05, 0, cz), (x + 0.05, 0, cz), 0.62, 0.62, GOLD, sides=14, grad=(0.0, 0.5))
	for k, god in enumerate(("light", "water", "fire", "wind", "dark")):
		sw, tone, glow = GOD_COLORS[god]
		phi = math.radians(-90 + (k - 2) * 32)
		at = (0, math.cos(phi) * 0.6, cz + math.sin(phi) * 0.6)
		if god == "dark":
			d.blob((0.26, 0.26, 0.26), at, SILVER, segs=(8, 5), grad=(0.0, 0.3), glow=1.2)
			d.blob((0.2, 0.2, 0.2), (0, math.cos(phi) * 0.66, cz + math.sin(phi) * 0.66), OBSIDIAN, segs=(8, 5), grad=(0.6, 0.9))
		else:
			d.blob((0.24, 0.24, 0.24), at, sw, segs=(8, 5), grad=(max(tone - 0.25, 0.0), tone), glow=glow + 1.0)
	p.seg((0, 0, cz - 0.6), (0, 0, cz - 1.2), 0.05, 0.05, GOLD, sides=6)                        # a sun medallion hanging under it
	d.seg((0, -0.05, cz - 1.55), (0, 0.05, cz - 1.55), 0.34, 0.34, GOLD, sides=16, grad=(0.0, 0.5), glow=0.7)
	for k in range(8):
		a = k * math.tau / 8
		d.seg((math.cos(a) * 0.32, 0, cz - 1.55 + math.sin(a) * 0.32), (math.cos(a) * 0.52, 0, cz - 1.55 + math.sin(a) * 0.52), 0.07, 0.0, GOLD, sides=4, grad=(0.0, 0.5), glow=0.7)
	return join_into(p.build(bevel=0.04), [d.build()])


def grove_stepping_stone():
	"""A flat pale stepping stone about 1.2 m across, a little irregular, its
	walkable top 0.08 m above the ground and its foot sunk 0.14 m. No
	collision needed (players walk over it)."""
	p = Prop("grove_stepping_stone", 991)
	rng = p.rng
	n = 11
	rad = [0.58 + rng.uniform(-0.09, 0.05) for _ in range(n)]
	outline = [(math.cos(k * math.tau / n) * rad[k] * 1.05, math.sin(k * math.tau / n) * rad[k] * 0.9) for k in range(n)]
	top = [(x, y) for x, y in outline]
	_flat_fill(p, top, -0.14, 0.08, GROVE_STONE, 0.1)
	return p.build(bevel=0.04)


# ---------------------------------------------------------------- Murkhold (trolls and ogres)

MURK_MUD = WOOD_GRAY      # wet brown-gray bog mud
MURK_BLACK = IRON         # soot and black bog muck
REED = BAMBOO             # dry reed thatch, gold-brown
FUNGUS = SLIME            # bog-fungus glow: yellow-green at the top of the swatch
FUNGUS_TONE = (0.0, 0.3)


def _raw_mesh(p, verts, faces, swatch, grad=(0.1, 0.8), glow=0.0):
	"""Like Prop.poly, but keeps the faces wound as given (for open shells,
	where recalculating normals could turn them the wrong way)."""
	bm = bmesh.new()
	vs = [bm.verts.new(v) for v in verts]
	for f in faces:
		bm.faces.new([vs[i] for i in f])
	return p._add(bm, swatch, grad, glow, 0.0)


def _bezier(a, b, c, n):
	"""n + 1 points along a quadratic Bezier from a through control b to c."""
	a, b, c = Vector(a), Vector(b), Vector(c)
	return [tuple(a * (1 - t) ** 2 + b * 2 * t * (1 - t) + c * t * t) for t in (i / n for i in range(n + 1))]


def _tube(p, pts, radii, swatch, sides=10, flat=1.0, grad=(0.1, 0.8), up=(0, 1, 0)):
	"""One seamless tube swept along a polyline, radius per point, capped at
	both ends (rounded to a point where the radius is 0). `flat` squashes the
	section across `up` (ribs are flatter than they are wide)."""
	pts = [Vector(q) for q in pts]
	up = Vector(up)
	verts, faces = [], []
	n = len(pts)
	for i, c in enumerate(pts):
		t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
		side = t.cross(up)
		if side.length < 1e-4:
			side = t.cross(Vector((1, 0, 0)))
		side.normalize()
		nrm = side.cross(t).normalized()
		for k in range(sides):
			a = k * math.tau / sides
			verts.append(tuple(c + (side * math.cos(a) + nrm * math.sin(a) * flat) * radii[i]))
	for i in range(n - 1):
		for k in range(sides):
			k2 = (k + 1) % sides
			faces.append((i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k))
	faces.append(tuple(range(sides))[::-1])
	faces.append(tuple((n - 1) * sides + k for k in range(sides)))
	return p.poly(verts, faces, swatch, grad)


def _fungus_clump(p, c, s=1.0, glow=1.6, n=5):
	"""A clump of glowing bog-fungus: little pale stalks with yellow-green caps."""
	x, y, z = c
	for k in range(n):
		a = k * math.tau / n + p.rng.uniform(-0.4, 0.4)
		d = (0.0 if k == 0 else p.rng.uniform(0.08, 0.2)) * s
		h = p.rng.uniform(0.08, 0.2) * s * (1.4 if k == 0 else 1.0)
		px, py = x + math.cos(a) * d, y + math.sin(a) * d
		p.seg((px, py, z), (px, py, z + h), 0.025 * s, 0.02 * s, BONE, sides=4)
		r = p.rng.uniform(0.06, 0.1) * s * (1.4 if k == 0 else 1.0)
		p.blob((r * 2, r * 2, r * 0.9), (px, py, z + h), FUNGUS, segs=(6, 4), grad=FUNGUS_TONE, glow=glow)


def _beast_skull(p, c, s=1.0, yaw=0.0, horns=True, tusks=True):
	"""A great horned beast skull facing -Y (turned by yaw degrees)."""
	start = len(p.parts)
	p.blob((1.0 * s, 0.95 * s, 0.8 * s), (0, 0, 0), BONE, segs=(10, 7), grad=(0.0, 0.7))                 # cranium
	p.blob((0.62 * s, 0.9 * s, 0.5 * s), (0, -0.55 * s, -0.12 * s), BONE, segs=(8, 5), grad=(0.0, 0.7))   # snout
	p.blob((0.5 * s, 0.35 * s, 0.22 * s), (0, -0.62 * s, -0.4 * s), BONE, segs=(8, 4), grad=(0.1, 0.8))   # jaw
	for sx in (-1, 1):
		p.blob((0.24 * s, 0.14 * s, 0.22 * s), (sx * 0.24 * s, -0.4 * s, 0.1 * s), MURK_BLACK, segs=(6, 4))   # eye sockets
		p.blob((0.08 * s, 0.1 * s, 0.1 * s), (sx * 0.07 * s, -0.98 * s, -0.08 * s), MURK_BLACK, segs=(5, 3))  # nostrils
		if horns:
			_chain(p, [(sx * 0.4 * s, 0.05 * s, 0.25 * s), (sx * 0.85 * s, 0.1 * s, 0.4 * s), (sx * 1.1 * s, -0.05 * s, 0.75 * s), (sx * 1.05 * s, -0.25 * s, 1.0 * s)],
				   0.14 * s, 0.03 * s, BONE, sides=6, grad=(0.0, 0.6))
		if tusks:
			_chain(p, [(sx * 0.2 * s, -0.8 * s, -0.35 * s), (sx * 0.3 * s, -1.0 * s, -0.6 * s), (sx * 0.25 * s, -1.15 * s, -0.45 * s)], 0.07 * s, 0.015 * s, BONE, sides=5, grad=(0.0, 0.5))
	_move_parts(p, start, Matrix.Translation(c) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))


def murk_longhouse():
	"""Murkhold's great hall of the chieftains, 10 m across and 18 m long (Y),
	door at the -Y gable: battered mud-plastered walls with timber posts on a
	low mud platform (walkable top 0.6 m, 13 x 21 m, a mud ramp at the door),
	a steep reed roof (ridge 9.8 m) patched with hides, a great bone along the
	ridge and crossed ribs at both gables, rib rafters over the thatch. The
	doorway is 3.4 m wide and 4.8 m tall, framed in tusks under a beast skull,
	with glowing bog-fungus sconces either side. Collide it as a mesh."""
	p = Prop("murk_longhouse", 960)
	d = Prop("murk_longhouse_detail", 961)
	rng = p.rng
	P = 0.6
	hx, hy = 6.5, 10.5
	# the platform: a flat-topped mud block with battered sides, lumps round its foot
	b, t = 0.9, 0.0
	verts = [(-hx - b, -hy - b, -0.6), (hx + b, -hy - b, -0.6), (hx + b, hy + b, -0.6), (-hx - b, hy + b, -0.6),
			 (-hx, -hy, P), (hx, -hy, P), (hx, hy, P), (-hx, hy, P)]
	p.poly(verts, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], MURK_MUD, grad=(0.3, 1.0))
	for k in range(26):
		f = k / 26
		per = 2 * (2 * hx + 2 * hy)
		s = f * per
		if s < 2 * hx:
			x, y = -hx + s, -hy - 0.55
		elif s < 2 * hx + 2 * hy:
			x, y = hx + 0.55, -hy + (s - 2 * hx)
		elif s < 4 * hx + 2 * hy:
			x, y = hx - (s - 2 * hx - 2 * hy), hy + 0.55
		else:
			x, y = -hx - 0.55, hy - (s - 4 * hx - 2 * hy)
		if y < 0 and abs(x) < 3.0:
			continue                                                      # the ramp
		p.blob((rng.uniform(1.4, 2.2), rng.uniform(1.2, 1.8), 0.8), (x, y, -0.05), MURK_MUD, rot=(0, 0, rng.uniform(0, 180)), segs=(8, 5), grad=(0.4, 1.0), jitter=0.05)
	# the ramp up to the door, with half-sunk logs for footing
	rw, ry = 2.4, -hy - 3.2
	verts = [(-rw, -hy + 0.3, P), (rw, -hy + 0.3, P), (rw, ry, -0.15), (-rw, ry, -0.15),
			 (-rw, -hy + 0.3, -0.6), (rw, -hy + 0.3, -0.6), (rw, ry, -0.6), (-rw, ry, -0.6)]
	p.poly(verts, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], MURK_MUD, grad=(0.5, 1.0))
	for k in range(4):
		f = (k + 0.5) / 4
		y = -hy + 0.3 + (ry - (-hy + 0.3)) * f
		z = P + (-0.15 - P) * f
		p.seg((-rw + 0.2, y, z - 0.04), (rw - 0.2, y, z - 0.04), 0.13, 0.12, WOOD_GRAY, sides=6, grad=(0.3, 1.0))
	# the walls: battered mud, 10 x 18 at the foot
	wx, wy, WT = 5.0, 9.0, 4.4
	inset = 0.35
	verts = [(-wx, -wy, P - 0.1), (wx, -wy, P - 0.1), (wx, wy, P - 0.1), (-wx, wy, P - 0.1),
			 (-wx + inset, -wy + inset, WT), (wx - inset, -wy + inset, WT), (wx - inset, wy - inset, WT), (-wx + inset, wy - inset, WT)]
	p.poly(verts, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], MURK_MUD, grad=(0.15, 0.85))
	for k in range(14):                                                   # plaster patches, a shade lighter or darker
		side = rng.choice((-1, 1))
		y = rng.uniform(-wy + 1.0, wy - 1.0)
		z = rng.uniform(P + 0.6, WT - 0.8)
		x = side * (wx - inset * (z - P) / (WT - P) + 0.02)
		d.box((0.06, rng.uniform(0.8, 1.6), rng.uniform(0.5, 1.0)), (x, y, z), CLAY if k % 3 else MURK_BLACK, rot=(0, -side * 4.5, rng.uniform(-6, 6)), grad=(0.5, 0.9))
	for side in (-1, 1):                                                  # timber posts along the long walls
		for k in range(8):
			y = -wy + 0.9 + k * (2 * wy - 1.8) / 7
			p.seg((side * (wx + 0.1), y, P - 0.2), (side * (wx - inset + 0.12), y, WT + 0.2), 0.22, 0.19, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
			if k % 3 == 1:
				_beast_skull(d, (side * (wx + 0.2), y, WT - 0.9), s=0.45, yaw=90 * side, horns=True, tusks=False)
	for x in (-wx, wx):                                                   # corner posts
		for y in (-wy, wy):
			p.seg((x * 1.02, y * 1.01, P - 0.2), (x * 0.95, y * 0.97, WT + 0.5), 0.3, 0.26, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
	# gables: solid triangles of woven reed over the end walls
	RZ = WT + 5.4
	for y in (-wy + inset, wy - inset):
		gt = 0.5
		tri = [(-wx + inset, WT), (wx - inset, WT), (0, RZ)]
		vs = [(x, y - gt / 2, z) for x, z in tri] + [(x, y + gt / 2, z) for x, z in tri]
		p.poly(vs, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], HIDE, grad=(0.2, 1.0))
		for k in range(5):                                                 # wattle battens across the gable
			z = WT + 0.6 + k * 0.95
			w = (wx - inset) * (1 - (z - WT) / (RZ - WT)) - 0.25
			if w > 0.3:
				sy = -1 if y < 0 else 1
				d.seg((-w, y + sy * 0.3, z), (w, y + sy * 0.3, z), 0.07, 0.07, WOOD_GRAY, sides=5)
	# the roof: reed courses on each side, patched with hides
	ov, ovz = 1.3, 1.3
	span = wx - inset + ov
	ang = math.atan2(RZ - WT, wx - inset)
	slope = (span) / math.cos(ang)
	L = 2 * wy + 2.2
	rows = 6
	for s in (1, -1):
		down = Vector((math.cos(ang) * s, 0, -math.sin(ang)))
		out = Vector((math.sin(ang) * s, 0, math.cos(ang)))
		top = Vector((0, 0, RZ + 0.15))
		p.box((slope, L, 0.3), top + down * slope / 2, MURK_BLACK, rot=(0, math.degrees(ang) * s, 0), grad=(0.3, 1.0))
		for i in range(rows):
			c = top + down * slope * (i + 0.55) / rows + out * (0.2 + 0.03 * i)
			for j in range(4):                                             # each course in four uneven bundles
				y = -L / 2 - 0.1 + (j + 0.5) * (L + 0.2) / 4 + rng.uniform(-0.2, 0.2)
				sw, gr = rng.choice(((HIDE, (0.5, 1.0)), (HIDE, (0.6, 1.0)), (HIDE, (0.45, 0.95)), (WOOD_GRAY, (0.1, 0.7)), (WOOD_GRAY, (0.0, 0.6))))
				p.box((slope / rows * 1.22, (L + 0.2) / 4 + 0.35, 0.24), (c.x, y, c.z), sw, rot=(0, math.degrees(ang) * s + rng.uniform(-2.5, 2.5), rng.uniform(-1.5, 1.5)),
					  grad=gr, jitter=0.07)
		eave = top + down * slope * 0.99 + out * 0.15
		for k in range(34):                                                # a shaggy fringe of reed at the eave
			y = -L / 2 + (k + 0.5) * L / 34
			tip = eave + down * rng.uniform(0.35, 0.7) + Vector((0, rng.uniform(-0.1, 0.1), -0.25))
			d.seg((eave.x, y, eave.z), (tip.x, y + rng.uniform(-0.15, 0.15), tip.z), 0.2, 0.02, HIDE if k % 3 else WOOD_GRAY, sides=4, grad=(0.5, 1.0))
		for k in range(5):                                                 # hides laid over the thatch
			f = rng.uniform(0.2, 0.75)
			y = -wy + 1.5 + k * (2 * wy - 3.0) / 4 + rng.uniform(-0.8, 0.8)
			c = top + down * slope * f + out * 0.48
			d.box((rng.uniform(2.2, 3.2), rng.uniform(2.0, 2.8), 0.08), (c.x, y, c.z), HIDE, rot=(0, math.degrees(ang) * s, rng.uniform(-14, 14)), grad=(0.05, 0.55), jitter=0.06)
		for k in range(5):                                                 # rib-bone rafters over the thatch
			y = -wy + 1.6 + k * (2 * wy - 3.2) / 4
			a0 = top + out * 0.5
			a2 = top + down * slope * 0.92 + out * 0.45
			mid = (a0 + a2) / 2 + out * 0.6
			_chain(d, _bezier((a0.x, y, a0.z), (mid.x, y, mid.z), (a2.x, y, a2.z), 4), 0.16, 0.09, BONE, sides=6, grad=(0.0, 0.6))
	# the great bone along the ridge, knuckled at both ends, and crossed ribs over each gable
	d.seg((0, -wy - 1.6, RZ + 0.55), (0, wy + 1.6, RZ + 0.55), 0.38, 0.38, BONE, sides=8, grad=(0.0, 0.6))
	for y in (-wy - 1.7, wy + 1.7):
		for sx in (-1, 1):
			d.blob((0.7, 0.8, 0.7), (sx * 0.25, y, RZ + 0.55), BONE, segs=(8, 5), grad=(0.0, 0.6))
	for y in (-wy - 0.6, wy + 0.6):
		for sx in (-1, 1):
			_chain(d, _bezier((sx * 2.6, y, RZ - 2.3), (sx * 0.9, y, RZ + 0.2), (-sx * 1.3, y, RZ + 2.2), 5), 0.26, 0.08, BONE, sides=7, grad=(0.0, 0.6))
	_beast_skull(d, (0, -wy - 1.1, RZ + 0.6), s=0.9)
	# the doorway, tusk frame and lintel
	dw, dh = 1.7, P + 4.8
	d.box((2 * dw, 1.2, dh - P), (0, -wy + 0.5, (dh + P) / 2), SHADE, grad=(0.97, 1.0))
	for sx in (-1, 1):
		_chain(d, _bezier((sx * (dw + 0.35), -wy - 0.5, P - 0.2), (sx * (dw + 0.6), -wy - 0.9, dh - 0.5), (sx * 0.35, -wy - 0.9, dh + 1.1), 6), 0.36, 0.1, BONE, sides=8, grad=(0.0, 0.6))
		p.seg((sx * (dw + 0.1), -wy - 0.2, P - 0.2), (sx * (dw + 0.1), -wy - 0.2, dh + 0.2), 0.24, 0.22, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
	p.seg((-dw - 0.7, -wy - 0.3, dh + 0.1), (dw + 0.7, -wy - 0.3, dh + 0.1), 0.3, 0.3, WOOD_GRAY, sides=7, grad=(0.2, 1.0))
	_beast_skull(d, (0, -wy - 0.9, dh + 0.75), s=0.75)
	for k in range(7):                                                    # hide lashings round the tusk frame
		x = -dw - 0.6 + k * (2 * dw + 1.2) / 6
		d.seg((x - 0.1, -wy - 0.3, dh + 0.1), (x + 0.1, -wy - 0.3, dh + 0.1), 0.34, 0.34, HIDE, sides=7)
	# glowing fungus sconces either side of the door
	for sx in (-1, 1):
		x, y = sx * 3.2, -wy - 0.7
		p.seg((x, y, P - 0.2), (x, y, P + 2.1), 0.1, 0.08, WOOD_GRAY, sides=5, grad=(0.2, 1.0))
		p.seg((x, y, P + 2.0), (x, y, P + 2.15), 0.3, 0.34, WOOD, sides=7)
		_fungus_clump(d, (x, y, P + 2.15), s=2.2, n=6)
	# hides stretched on frames against the long walls
	for side, y in ((-1, -3.0), (1, 2.5), (1, -4.5)):
		x = side * (wx + 0.5)
		c = Vector((x, y, P + 1.6))
		for dz in (-1.0, 1.0):
			d.seg((x, y - 1.1, P + 1.6 + dz), (x, y + 1.1, P + 1.6 + dz), 0.06, 0.06, WOOD, sides=4)
		for dy in (-1.0, 1.0):
			d.seg((x, y + dy, P - 0.1), (x, y + dy, P + 2.8), 0.06, 0.06, WOOD, sides=4)
		d.box((0.06, 1.8, 1.8), tuple(c), HIDE, rot=(0, side * 8, 0), grad=(0.2, 0.9))
	# trophy stakes on the platform's front corners
	for sx in (-1, 1):
		x, y = sx * (hx - 0.8), -hy + 0.8
		p.seg((x, y, P - 0.2), (x, y, P + 3.2), 0.12, 0.08, WOOD_GRAY, sides=5, grad=(0.2, 1.0))
		_beast_skull(d, (x, y - 0.1, P + 3.3), s=0.55)
	obj = p.build(bevel=0.06)
	return join_into(obj, [d.build()])


def murk_hut():
	"""A Murkhold dwelling on stilts: a 7 x 7 m plank deck 1.4 m over the bog on
	nine crooked stilts in mud mounds, a low rail round it, a mud-and-wattle
	hut (5 x 4.6 m, walls 2.8 m) at the back with a hide-hung door, a lumpy
	hide roof on poles to about 7.5 m, a drying rack and a pot on the porch,
	and a log ramp from the front edge down to the ground 4 m out (-Y). Deck
	and ramp are walkable. Collide it as a mesh."""
	p = Prop("murk_hut", 962)
	d = Prop("murk_hut_detail", 963)
	rng = p.rng
	F, H = 1.4, 3.5
	for x in (-3.1, 0.0, 3.1):                                             # stilts, mud round their feet
		for y in (-3.1, 0.0, 3.1):
			fx, fy = x + rng.uniform(-0.25, 0.25), y + rng.uniform(-0.25, 0.25)
			p.seg((fx, fy, -0.8), (x, y, F - 0.1), 0.2, 0.17, WOOD_GRAY, sides=6, grad=(0.3, 1.0))
			p.blob((rng.uniform(1.0, 1.5), rng.uniform(1.0, 1.4), 0.7), (fx, fy, -0.05), MURK_MUD, rot=(0, 0, rng.uniform(0, 180)), segs=(7, 4), grad=(0.4, 1.0), jitter=0.04)
	for s in (-1, 1):                                                      # cross bracing on the sides
		p.seg((s * 3.1, -3.1, 0.1), (s * 3.1, 3.1, F - 0.3), 0.07, 0.07, WOOD_GRAY, sides=4)
		p.seg((-3.1, s * 3.1, F - 0.3), (3.1, s * 3.1, 0.1), 0.07, 0.07, WOOD_GRAY, sides=4)
	for y in (-3.1, 0.0, 3.1):                                             # beams under the deck
		p.seg((-H - 0.2, y, F - 0.3), (H + 0.2, y, F - 0.3), 0.16, 0.16, WOOD_GRAY, sides=6)
	for k in range(14):                                                    # the deck planks, top at F
		x = -H + 0.25 + k * 0.5
		p.box((0.48, 2 * H + rng.uniform(-0.05, 0.25), 0.16), (x, rng.uniform(-0.1, 0.1), F - 0.08), WOOD_GRAY, grad=(0.0, 0.5) if k % 3 else (0.3, 0.9))
	# the rail, open at the ramp
	posts = []
	for k in range(7):
		v = -H + 0.2 + k * (2 * H - 0.4) / 6
		posts += [(v, -H + 0.15), (H - 0.15, v), (-v, H - 0.15), (-H + 0.15, -v)]
	for x, y in posts:
		if y < -H + 0.5 and abs(x) < 1.2:
			continue
		p.seg((x, y, F - 0.1), (x + rng.uniform(-0.05, 0.05), y, F + 1.0 + rng.uniform(-0.1, 0.1)), 0.06, 0.05, WOOD_GRAY, sides=5)
	RT = F + 0.9
	for a, b in (((-H + 0.2, -H + 0.15), (-1.15, -H + 0.15)), ((1.15, -H + 0.15), (H - 0.15, -H + 0.15)), ((H - 0.15, -H + 0.2), (H - 0.15, H - 0.15)),
				 ((H - 0.15, H - 0.15), (-H + 0.15, H - 0.15)), ((-H + 0.15, H - 0.15), (-H + 0.15, -H + 0.2))):
		p.seg((a[0], a[1], RT), (b[0], b[1], RT + rng.uniform(-0.06, 0.06)), 0.05, 0.05, WOOD_GRAY, sides=4, grad=(0.1, 0.6))
	for x in (-1.25, 1.25):
		p.seg((x, -H + 0.15, F - 0.1), (x, -H + 0.15, F + 1.4), 0.09, 0.08, WOOD_GRAY, sides=5)
		_beast_skull(d, (x, -H + 0.1, F + 1.5), s=0.22, horns=True, tusks=False)
	# the hut: mud core, wattle stakes, lighter wattle where the mud has fallen off
	x0, x1, y0, y1, WH = -2.5, 2.5, -1.3, 3.3, 2.8
	p.box((x1 - x0, y1 - y0, WH), ((x0 + x1) / 2, (y0 + y1) / 2, F + WH / 2), MURK_MUD, grad=(0.15, 0.9), jitter=0.04)
	for x in (x0, x1):
		for y in (y0, y1):
			p.seg((x, y, F), (x, y, F + WH + 0.3), 0.14, 0.12, WOOD_GRAY, sides=5)
	for k in range(9):
		x = x0 + 0.5 + k * (x1 - x0 - 1.0) / 8
		if abs(x) < 0.9:
			continue
		p.seg((x, y0 - 0.02, F), (x, y0 - 0.02, F + WH), 0.05, 0.05, WOOD_GRAY, sides=4, grad=(0.0, 0.5))
	for (cx, cy, cz, rz) in ((-1.6, y0 - 0.03, F + 1.8, 0), (x1 + 0.03, 0.9, F + 1.2, 90), (x0 - 0.03, 2.1, F + 1.9, 90)):
		for j in range(4):
			d.seg((cx - 0.5 * (rz == 0), cy - 0.5 * (rz != 0), cz - 0.3 + j * 0.2), (cx + 0.5 * (rz == 0), cy + 0.5 * (rz != 0), cz - 0.3 + j * 0.2), 0.05, 0.05, WOOD, sides=4)
	d.box((1.4, 0.12, 2.3), (0, y0 - 0.02, F + 1.15), SHADE, grad=(0.95, 1.0))                              # doorway
	d.box((0.9, 0.08, 2.1), (-0.3, y0 - 0.1, F + 1.2), HIDE, rot=(0, 0, 4), grad=(0.2, 0.95))                # hide curtain, half drawn
	p.seg((-0.9, y0 - 0.12, F + 2.4), (0.9, y0 - 0.12, F + 2.4), 0.09, 0.09, WOOD_GRAY, sides=5)
	# the hide roof: a lumpy cone on poles
	cy, RZ0, RZ1 = (y0 + y1) / 2, F + WH - 0.15, F + 6.0
	p.seg((0, cy, RZ0), (0, cy, RZ1), 4.0, 0.25, HIDE, sides=9, grad=(0.65, 1.0), jitter=0.12)
	for k in range(7):                                                     # hides of other colors patched over it
		a = k * math.tau / 7 + rng.uniform(-0.2, 0.2)
		f0 = rng.uniform(0.1, 0.45)
		f1 = f0 + rng.uniform(0.18, 0.3)
		da = rng.uniform(0.18, 0.3)
		quad = []
		for f, aa in ((f0, a - da), (f0, a + da), (f1, a + da * 0.8), (f1, a - da * 0.8)):
			rr = 4.0 * (1 - f) + 0.25 * f + 0.08
			quad.append((math.cos(aa) * rr, cy + math.sin(aa) * rr, RZ0 + (RZ1 - RZ0) * f + 0.03))
		d.poly(quad, [(0, 1, 2, 3)], HIDE if k % 2 else WOOD_GRAY, grad=(0.0, 0.5) if k % 2 else (0.3, 0.9))
	p.seg((0, cy, RZ0 - 0.25), (0, cy, RZ0), 3.9, 3.95, WOOD_GRAY, sides=9, grad=(0.5, 1.0))
	for k in range(9):                                                     # seams and poles through the peak
		a = k * math.tau / 9 + 0.35
		d.seg((math.cos(a) * 3.95, cy + math.sin(a) * 3.95, RZ0 + 0.08), (math.cos(a) * 0.3, cy + math.sin(a) * 0.3, RZ1 + 0.05), 0.05, 0.04, WOOD_GRAY, sides=4)
	for k in range(5):
		a = k * math.tau / 5
		p.seg((math.cos(a) * 0.9, cy + math.sin(a) * 0.9, RZ1 - 0.9), (-math.cos(a) * 0.45, cy - math.sin(a) * 0.45, RZ1 + 1.2), 0.08, 0.05, WOOD_GRAY, sides=5)
	for k in range(6):                                                     # stones and bones weighting the hides
		a = k * math.tau / 6 + 0.2
		d.blob((0.35, 0.3, 0.22), (math.cos(a) * 3.1, cy + math.sin(a) * 3.1, RZ0 + 0.75), BONE if k % 2 else STONE_DARK, segs=(6, 4))
	# the porch: a drying rack of fish and a clay pot
	for x in (1.6, 3.0):
		p.seg((x, -2.9, F), (x, -2.9, F + 1.9), 0.05, 0.05, WOOD, sides=4)
	p.seg((1.5, -2.9, F + 1.85), (3.1, -2.9, F + 1.85), 0.04, 0.04, WOOD, sides=4)
	for k in range(4):
		x = 1.8 + k * 0.35
		d.seg((x, -2.9, F + 1.8), (x, -2.9, F + 1.45), 0.012, 0.012, HIDE, sides=3)
		d.blob((0.14, 0.05, 0.45), (x, -2.9, F + 1.2), SEA_STONE, segs=(6, 4))
	d.seg((-2.4, -2.5, F), (-2.4, -2.5, F + 0.7), 0.35, 0.28, CLAY, sides=8, grad=(0.2, 0.9))
	d.seg((-2.4, -2.5, F + 0.62), (-2.4, -2.5, F + 0.78), 0.3, 0.32, CLAY, sides=8)
	# the ramp: two stringers, a plank bed and cross logs, from the deck to the ground
	RY = -H - 4.0
	for x in (-0.85, 0.85):
		p.seg((x, -H + 0.1, F - 0.2), (x, RY, -0.3), 0.14, 0.14, WOOD_GRAY, sides=6)
	L = math.hypot(RY + H, F + 0.1)
	ang = math.degrees(math.atan2(F + 0.1, -(RY + H)))
	p.box((1.7, L + 0.3, 0.12), (0, (-H + RY) / 2, (F - 0.1) / 2 - 0.04), WOOD_GRAY, rot=(ang, 0, 0))
	for k in range(9):
		f = (k + 0.5) / 9
		y = -H + (RY + H) * f
		z = F - (F + 0.1) * f
		p.seg((-0.85, y, z), (0.85, y, z), 0.08, 0.08, WOOD_GRAY, sides=5, grad=(0.0, 0.6))
	return join_into(p.build(bevel=0.04), [d.build(bevel=0.02)])


def bone_palisade():
	"""An 8 m run (along X) of Murkhold's wall, about 4.2 m tall: sharpened
	logs with a giant rib or thigh bone every few, lashed with two bands of
	hide rope on a mud bank, a skull spiked on one stake. Ends at x = +-4 so
	runs tile. About 1.6 m thick. Collide it as a box."""
	p = Prop("bone_palisade", 964)
	d = Prop("bone_palisade_detail", 965)
	rng = p.rng
	n = 16
	for i in range(n):
		x = -4.0 + (i + 0.5) * 8.0 / n
		lean = rng.uniform(-0.06, 0.06)
		if i % 4 == 1:                                                     # a rib, curving out to -Y
			top = 4.2 + rng.uniform(-0.2, 0.3)
			_chain(p, _bezier((x, 0.05, -0.4), (x + lean, -0.1, top * 0.6), (x + lean * 2, -0.75, top), 5), 0.26, 0.09, BONE, sides=7, grad=(0.0, 0.7))
		elif i % 4 == 3:                                                   # a thigh bone, knuckle up
			top = 3.7 + rng.uniform(-0.2, 0.2)
			p.seg((x, 0, -0.4), (x + lean, 0, top), 0.2, 0.17, BONE, sides=7, grad=(0.0, 0.7))
			for sx in (-1, 1):
				p.blob((0.34, 0.36, 0.38), (x + lean + sx * 0.14, 0, top + 0.05), BONE, segs=(8, 5), grad=(0.0, 0.6))
		else:                                                              # a sharpened log
			top = 3.1 + rng.uniform(-0.3, 0.3)
			r = 0.21 + rng.uniform(-0.03, 0.03)
			p.seg((x, 0, -0.4), (x + lean, 0, top), r, r * 0.92, WOOD_GRAY, sides=6, grad=(0.25, 1.0))
			p.seg((x + lean, 0, top), (x + lean * 1.1, 0, top + 0.6), r * 0.92, 0.0, WOOD_GRAY, sides=6, grad=(0.0, 0.5))
	for z in (1.1, 2.5):                                                   # hide rope bands, both faces
		for y in (-0.24, 0.24):
			d.seg((-4.0, y, z + rng.uniform(-0.05, 0.05)), (4.0, y, z + rng.uniform(-0.05, 0.05)), 0.07, 0.07, HIDE, sides=5, grad=(0.5, 1.0))
		for k in range(n):
			x = -4.0 + (k + 0.5) * 8.0 / n
			d.seg((x, 0, z - 0.1), (x, 0, z + 0.12), 0.27, 0.27, HIDE, sides=6, grad=(0.5, 1.0))
	for k in range(7):                                                     # the mud bank
		x = -3.5 + k * (7.0 / 6)
		p.blob((1.9, 1.6, 0.9), (x, rng.uniform(-0.1, 0.1), -0.05), MURK_MUD, rot=(0, 0, rng.uniform(-20, 20)), segs=(8, 5), grad=(0.4, 1.0), jitter=0.05)
	_beast_skull(d, (-1.75, -0.35, 3.55), s=0.42, tusks=True)
	for k in range(3):                                                     # a string of small bones hung on the front
		x = 1.2 + k * 0.3
		d.seg((x, -0.3, 2.45), (x, -0.32, 2.0), 0.015, 0.015, HIDE, sides=3)
		d.seg((x, -0.33, 2.0), (x, -0.35, 1.7), 0.05, 0.035, BONE, sides=5)
	return join_into(p.build(bevel=0.03), [d.build()])


def bone_gate():
	"""Murkhold's gate: two colossal rib bones rising from mud mounds either
	side of an 8.3 m opening (along X, walked through along Y) and crossing
	at about 12 m, lashed with hide where they meet under a great horned
	skull (top about 14.5 m), smaller tusks and fetish strings at their feet
	and glowing bog-fungus on the mounds. About 13 m wide. Collide it as a
	mesh (a box would close the opening)."""
	p = Prop("bone_gate", 966)
	d = Prop("bone_gate_detail", 967)
	b = Prop("bone_gate_ribs", 968)
	rng = p.rng
	for sx in (-1, 1):
		yo = 0.3 * sx
		pts = _bezier((sx * 5.0, 0, -0.8), (sx * 6.4, 0, 7.4), (-sx * 0.9, yo, 12.6), 12)
		n = len(pts) - 1
		fine = _bezier((sx * 5.0, 0, -0.8), (sx * 6.4, 0, 7.4), (-sx * 0.9, yo, 12.6), 24)
		radii = [0.95 - 0.5 * (i / 24) + 0.12 * math.sin(i / 24 * math.pi) for i in range(25)]
		radii[-1] *= 0.6
		_tube(b, fine, radii, BONE, sides=12, flat=0.7, grad=(0.15, 0.9))
		p.blob((1.3, 1.3, 1.3), (sx * 5.0, 0, 0.1), BONE, segs=(10, 6), grad=(0.1, 0.7))   # the knuckle at its foot
		for k in range(8):                                                 # the mud mound, with stones
			a = k * math.tau / 8 + rng.uniform(-0.2, 0.2)
			rr = rng.uniform(1.0, 1.7)
			p.blob((rng.uniform(1.4, 2.0), rng.uniform(1.2, 1.7), rng.uniform(0.7, 1.1)), (sx * 5.0 + math.cos(a) * rr, math.sin(a) * rr, 0.0), MURK_MUD,
				   rot=(0, 0, math.degrees(a)), segs=(8, 5), grad=(0.4, 1.0), jitter=0.05)
		for k in range(3):
			a = rng.uniform(0, math.tau)
			p.rock((0.8, 0.7, 0.6), (sx * 5.0 + math.cos(a) * 2.0, math.sin(a) * 1.6, 0.15), STONE_DARK)
		for z in (1.6, 2.2):                                               # hide bindings round the foot
			q = Vector(pts[2]).lerp(Vector(pts[3]), (z - pts[2][2]) / max(pts[3][2] - pts[2][2], 0.1))
			d.seg((q.x, q.y, z - 0.18), (q.x, q.y, z + 0.18), 1.02, 1.02, HIDE, sides=9, grad=(0.3, 0.9))
		for sy in (-1, 1):                                                 # tusks leaning at its foot
			base = (sx * (5.0 + 1.3), sy * 1.4, -0.3)
			_chain(p, _bezier(base, (sx * 6.0, sy * 1.8, 2.2), (sx * 5.2, sy * 1.2, 3.4), 4), 0.28, 0.05, BONE, sides=7, grad=(0.0, 0.6))
		_fungus_clump(d, (sx * 3.9, -1.2, 0.35), s=2.4, n=6)
		_fungus_clump(d, (sx * 6.2, 1.0, 0.5), s=1.8, n=5)
		for k in range(3):                                                 # fetish strings hung from the rib
			q = pts[5 + k]
			top = Vector(q) + Vector((0, -0.75, -0.3))
			d.seg(tuple(top), tuple(top + Vector((0, 0, -1.4 - k * 0.3))), 0.02, 0.02, HIDE, sides=3)
			d.seg(tuple(top + Vector((0, 0, -1.4 - k * 0.3))), tuple(top + Vector((0, 0, -1.9 - k * 0.3))), 0.07, 0.04, BONE, sides=5)
			d.blob((0.16, 0.1, 0.18), tuple(top + Vector((0, 0, -0.8))), CLOTH_RED if k == 1 else BONE, segs=(5, 3))
	for k in range(4):                                                     # lashing where the ribs cross
		d.seg((-1.0, -0.1, 11.3 + k * 0.28), (1.0, 0.1, 11.3 + k * 0.28 + 0.1), 0.3, 0.3, HIDE, sides=7, grad=(0.2, 0.9))
	_beast_skull(d, (0, -0.6, 13.3), s=1.9, horns=True, tusks=True)
	ribs = b.build()
	bpy.ops.object.shade_smooth()
	return join_into(p.build(bevel=0.05), [ribs, d.build(bevel=0.02)])


def bog_lantern():
	"""A Murkhold street lamp, about 3.5 m: a crooked gray pole in a mud
	foot, bracket fungus on its side, a crooked arm holding a hanging cage of
	bone slats round a clump of glowing yellow-green bog-fungus (its center at
	0.9, 0, 2.55 in Blender, i.e. [0.9, 2.55, 0] in Godot). Collide it as a trunk."""
	p = Prop("bog_lantern", 968)
	d = Prop("bog_lantern_glow", 969)
	_chain(p, [(0, 0, -0.4), (0.1, 0.05, 1.1), (-0.08, 0.1, 2.3), (0.05, 0.0, 3.5)], 0.13, 0.07, WOOD_GRAY, sides=6, grad=(0.2, 1.0))
	p.blob((0.9, 0.9, 0.45), (0, 0, 0.0), MURK_MUD, segs=(8, 5), grad=(0.4, 1.0), jitter=0.04)
	_chain(p, [(0.0, 0.0, 3.15), (0.45, 0.0, 3.5), (0.95, 0.02, 3.35)], 0.07, 0.05, WOOD_GRAY, sides=5)
	p.seg((0.02, 0.0, 3.4), (-0.25, 0.0, 3.8), 0.05, 0.02, WOOD_GRAY, sides=4)          # a crooked twig on top
	p.seg((0.93, 0.0, 3.35), (0.9, 0.0, 3.0), 0.02, 0.02, HIDE, sides=3)               # the cord
	cx, cy, top, bot = 0.9, 0.0, 3.0, 1.95
	p.seg((cx, cy, top - 0.08), (cx, cy, top + 0.04), 0.28, 0.14, WOOD_GRAY, sides=8)      # cap
	p.seg((cx, cy, bot - 0.08), (cx, cy, bot + 0.04), 0.16, 0.3, WOOD_GRAY, sides=8)       # floor
	for k in range(7):                                                  # bone slats, bulging
		a = k * math.tau / 7
		pts = [(cx + math.cos(a) * r, cy + math.sin(a) * r, z) for r, z in ((0.25, top), (0.42, (top + bot) / 2), (0.28, bot))]
		_chain(p, pts, 0.04, 0.04, BONE if k % 2 else WOOD_GRAY, sides=4, grad=(0.1, 0.7))
	for k in range(9):                                                  # the fungus inside
		a = k * 2.4
		rr = 0.0 if k == 0 else 0.15
		z = bot + 0.12 + (k % 3) * 0.26
		s = 0.3 if k == 0 else 0.2
		d.blob((s, s, s * 0.8), (cx + math.cos(a) * rr, cy + math.sin(a) * rr, z + (0.25 if k == 0 else 0.0)), FUNGUS, segs=(7, 5), grad=FUNGUS_TONE, glow=2.2)
	for z, a in ((1.3, 0.5), (1.55, 2.2), (0.9, 4.0)):                  # shelf fungus up the pole, faintly lit
		d.blob((0.3, 0.3, 0.07), (math.cos(a) * 0.12, math.sin(a) * 0.12, z), FUNGUS, segs=(7, 3), grad=(0.1, 0.5), glow=0.8)
	return join_into(p.build(bevel=0.01), [d.build()])


def murk_cauldron():
	"""Murkhold's cooking pot: a huge soot-black cauldron (2.5 m across, rim at
	about 1.95 m) on three stones over a fire pit ringed with rocks (3.4 m
	across), logs and embers glowing under it, a brown stew with a bone and a
	great bone paddle sticking out. Collide it as a box."""
	p = Prop("murk_cauldron", 970)
	d = Prop("murk_cauldron_fire", 971)
	rng = p.rng
	for k in range(12):                                                 # the ring of stones
		a = k * math.tau / 12
		p.rock((0.6, 0.5, 0.42), (math.cos(a) * 1.45, math.sin(a) * 1.45, 0.12), STONE_DARK if k % 3 else MURK_BLACK, rot=(0, 0, math.degrees(a)), jitter=0.06)
	for k in range(3):                                                  # the stones it sits on
		a = k * math.tau / 3 + 0.5
		p.rock((0.55, 0.5, 0.6), (math.cos(a) * 0.72, math.sin(a) * 0.72, 0.2), STONE_DARK, jitter=0.05)
	for k in range(6):                                                  # logs under it
		a = k * math.tau / 6 + 0.25
		p.seg((math.cos(a) * 1.3, math.sin(a) * 1.3, 0.12), (math.cos(a) * 0.25, math.sin(a) * 0.25, 0.3), 0.12, 0.1, WOOD, sides=5, grad=(0.4, 1.0))
	d.blob((2.2, 2.2, 0.16), (0, 0, 0.06), EMBER, segs=(10, 4), grad=(0.5, 0.9), glow=1.0)
	for k in range(7):                                                  # flames licking round the pot
		a = k * math.tau / 7 + 0.3
		r = 1.02
		d.seg((math.cos(a) * r, math.sin(a) * r, 0.1), (math.cos(a) * (r + 0.1), math.sin(a) * (r + 0.1), 0.1 + rng.uniform(0.5, 0.85)),
			  0.17, 0.0, FLAME, sides=5, grad=(0.1, 0.95), glow=1.4, twist=rng.uniform(0, 60))
	pot = _lathe(p, [(0.02, 0.35), (0.6, 0.38), (1.05, 0.7), (1.26, 1.15), (1.18, 1.6), (1.05, 1.78), (1.22, 1.86), (1.2, 1.97), (1.04, 1.95), (1.0, 1.65), (0.02, 1.65)],
				 16, MURK_BLACK, grad=(0.2, 1.0))
	for sx in (-1, 1):                                                  # handles
		pts = [(sx * (1.18 + 0.28 * math.sin(t * math.pi)), 0.0, 1.72 - 0.4 * math.sin(t * math.pi) ) for t in (i / 6 for i in range(7))]
		pts = [(sx * 1.16, math.cos(t * math.pi) * 0.35, 1.72 - 0.35 * math.sin(t * math.pi)) for t in (i / 6 for i in range(7))]
		pts = [(x + sx * 0.12 * math.sin(i / 6 * math.pi), y, z) for i, (x, y, z) in enumerate(pts)]
		_chain(p, pts, 0.055, 0.055, IRON, sides=5)
	p.blob((2.02, 2.02, 0.16), (0, 0, 1.7), MURK_MUD, segs=(14, 4), grad=(0.3, 0.6))  # the stew
	for k in range(5):                                                  # bubbles and lumps
		a = rng.uniform(0, math.tau)
		rr = rng.uniform(0.1, 0.75)
		s = rng.uniform(0.12, 0.26)
		p.blob((s, s, s * 0.7), (math.cos(a) * rr, math.sin(a) * rr, 1.76), MURK_MUD if k % 2 else HIDE, segs=(6, 4), grad=(0.1, 0.5))
	p.seg((-0.35, 0.2, 1.6), (-0.6, 0.45, 2.4), 0.07, 0.07, BONE, sides=5)            # a bone in the stew
	p.blob((0.22, 0.24, 0.2), (-0.6, 0.45, 2.45), BONE, segs=(6, 4))
	_chain(p, [(0.4, -0.3, 1.5), (0.75, -0.55, 2.4), (1.1, -0.8, 3.1)], 0.07, 0.06, BONE, sides=6)   # the paddle, a shoulder blade on a bone
	p.blob((0.55, 0.12, 0.7), (0.32, -0.25, 1.55), BONE, rot=(0, -20, -35), segs=(8, 4))
	return join_into(p.build(bevel=0.02), [d.build()])


# ---------------------------------------------------------------- Duskhold (dark elves) and Duskwood

DUSK_STONE = IRON         # the dark elves' black stone
DUSK_TRIM = STONE_DARK    # its dressed gray trim
CAVE_STONE = STONE_WARM   # the cavern's warm gray rock (its darker half matches the mountain ring)
CAVE_TONE = (0.5, 1.0)
DUSK_LEAF = PETAL_PURPLE  # Duskwood's foliage: lilac into deep purple (use the dark half)


def cavern_dome():
	"""Duskhold's sky: the cavern's rock ceiling for a 224 m zone, a rough shell
	about 268 m across, 45 m over the zone's center, 14 m over its edge (112 m
	out) and sinking to -10 m at 134 m out, so the ring's mountains rise into
	it all round. Its faces point down (it is seen from below). Hung with
	stalactites (2-11 m) and specks of glowing violet crystal. Origin at the
	zone's center on the ground. No collision (collide none)."""
	p = Prop("cavern_dome", 972)
	d = Prop("cavern_dome_glow", 973)
	rng = p.rng
	RIM, TOP, R0 = 14.0, 45.0, 112.0

	def height(r, a):
		base = TOP - (TOP - RIM) * (min(r, R0) / R0) ** 1.8
		if r > R0:
			base -= (r - R0) * 0.5 + ((r - R0) / 22.0) ** 2 * 12.0
		wob = 2.6 * math.sin(3 * a + r * 0.05) + 1.8 * math.sin(5 * a - r * 0.08 + 1.3) + 1.4 * math.cos(r * 0.11 + 2 * a)
		return base + wob * min(1.0, r / 30.0 + 0.6)

	rings = [(0, 1), (6, 7), (13, 13), (21, 20), (30, 28), (39, 36), (48, 44), (57, 52), (66, 60), (75, 64), (84, 64), (92, 64), (100, 64),
			 (107, 64), (113, 64), (119, 64), (125, 64), (130, 64), (134, 64)]
	verts, starts = [], []
	for i, (r, n) in enumerate(rings):
		starts.append(len(verts))
		off = rng.uniform(0, math.tau / n)
		for k in range(n):
			a = k * math.tau / n + off
			rr = r + rng.uniform(-1.5, 1.5) * (0 < r < 130)
			z = height(rr, a) + rng.uniform(-0.8, 0.8) * (r < 130) + rng.uniform(-1.5, 1.5) * (r < 25)
			verts.append((math.cos(a) * rr, math.sin(a) * rr, z))
	faces = []
	for i in range(len(rings) - 1):                                   # zip each ring to the next; wound clockwise from above so normals point down
		ni, no = rings[i][1], rings[i + 1][1]
		si, so = starts[i], starts[i + 1]
		ang = lambda idx: math.atan2(verts[idx][1], verts[idx][0]) % math.tau
		inner = sorted(range(si, si + ni), key=ang)
		outer = sorted(range(so, so + no), key=ang)
		if ni == 1:
			for j in range(no):
				faces.append((inner[0], outer[(j + 1) % no], outer[j]))
			continue
		a, b = 0, 0
		# start the outer walk at the outer vertex nearest the first inner one
		first = ang(inner[0])
		b0 = min(range(no), key=lambda j: (ang(outer[j]) - first) % math.tau)
		outer = outer[b0:] + outer[:b0]
		base_i, base_o = ang(inner[0]), ang(outer[0])
		ui = [(ang(v) - base_i) % math.tau for v in inner] + [math.tau]
		uo = [(ang(v) - base_i) % math.tau for v in outer] + [math.tau + (ang(outer[0]) - base_i) % math.tau]
		while a < ni or b < no:
			if b >= no or (a < ni and ui[a + 1] <= uo[b + 1]):
				faces.append((inner[a % ni], inner[(a + 1) % ni], outer[b % no]))
				a += 1
			else:
				faces.append((inner[a % ni], outer[(b + 1) % no], outer[b % no]))
				b += 1
	_raw_mesh(p, verts, faces, CAVE_STONE, grad=(0.35, 1.0))
	for k in range(9):                                                # hanging rock bulges round the crown
		a = k * math.tau / 9 + rng.uniform(-0.3, 0.3)
		r = rng.uniform(0.0, 22.0) if k else 0.0
		s = rng.uniform(9.0, 15.0)
		p.rock((s, s * 0.9, s * 0.45), (math.cos(a) * r, math.sin(a) * r, height(r, a) - 0.5), CAVE_STONE, rot=(0, 0, rng.uniform(0, 180)), grad=(0.35, 1.0), jitter=0.1)
	# stalactites, thicker and longer toward the middle
	for k in range(220):
		r = math.sqrt(rng.random()) * 104.0
		a = rng.uniform(0, math.tau)
		x, y = math.cos(a) * r, math.sin(a) * r
		z = height(r, a) + 1.2
		L = rng.uniform(2.0, 7.0) * (1.0 + 0.6 * (1 - r / 104.0))
		rad = L * rng.uniform(0.14, 0.2)
		tip = (x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), z - L)
		p.seg((x, y, z), tip, rad, 0.0, CAVE_STONE if k % 4 else STONE_DARK, sides=5, grad=(0.1, 0.9), twist=rng.uniform(0, 70))
		if k % 3 == 0:                                                 # a smaller one beside it
			ox, oy = x + rng.uniform(-1.0, 1.0) * rad * 2, y + rng.uniform(-1.0, 1.0) * rad * 2
			l2 = L * rng.uniform(0.35, 0.6)
			p.seg((ox, oy, z), (ox, oy, z - l2), rad * 0.55, 0.0, CAVE_STONE, sides=4, grad=(0.1, 0.9))
	# glowing violet crystal specks in the rock, the cavern's stars
	for k in range(70):
		r = math.sqrt(rng.random()) * 108.0
		a = rng.uniform(0, math.tau)
		x, y = math.cos(a) * r, math.sin(a) * r
		z = height(r, a) + 0.4
		for j in range(3):
			l = rng.uniform(1.4, 3.4)
			d.seg((x + j * 0.6, y + (j % 2) * 0.6, z), (x + j * 0.6 + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8), z - l), 0.5, 0.0, VIOLET, sides=4, grad=(0.0, 0.4), glow=2.2)
	return join_into(p.build(), [d.build()])


def dusk_spire():
	"""A slender dark elf tower, about 24.3 m: a stepped octagonal plinth 6 m
	across, a black octagonal shaft tapering from 4.2 to 2.6 m with four thin
	buttress fins, gray bands, violet-lit lancet windows up its faces, a
	balcony with a spiked parapet and four pinnacles at 15.5 m, a narrow upper
	stage with tall violet windows and a black needle roof tipped with a violet orb.
	Door on the front (-Y) between two violet lamps. Collide it as a mesh."""
	p = Prop("dusk_spire", 974)
	o = Prop("dusk_spire_glass", 975)
	d = Prop("dusk_spire_detail", 976)
	c8 = math.cos(math.pi / 8)
	p.seg((0, 0, -0.3), (0, 0, 0.55), 3.0 / c8, 2.9 / c8, DUSK_TRIM, sides=8, grad=(0.2, 1.0), twist=22.5)
	p.seg((0, 0, 0.55), (0, 0, 1.0), 2.55 / c8, 2.45 / c8, DUSK_STONE, sides=8, grad=(0.1, 0.8), twist=22.5)

	def rad(z):
		return 2.1 + (1.3 - 2.1) * (z - 1.0) / 14.5

	o.seg((0, 0, 1.0), (0, 0, 15.5), 2.1 / c8, 1.3 / c8, DUSK_STONE, sides=8, grad=(0.0, 0.9), twist=22.5)
	for z in (1.0, 5.6, 10.6):
		r = rad(z)
		d.seg((0, 0, z), (0, 0, z + 0.22), r / c8 + 0.07, r / c8 + 0.06, DUSK_TRIM, sides=8, grad=(0.0, 0.6), twist=22.5)
	for k in range(4):                                                  # buttress fins on the diagonals
		a = math.radians(45 + k * 90)
		u = Vector((math.cos(a), math.sin(a), 0))
		t = Vector((-u.y, u.x, 0)) * 0.12
		prof = [(2.1 + 1.1, 0.0), (2.1 + 0.9, 3.0), (rad(9.0) + 0.45, 9.0), (rad(13.5) + 0.05, 13.5), (rad(1.0) - 0.2, 1.0), (rad(13.5) - 0.2, 13.5)]
		out = [prof[0], prof[1], prof[2], prof[3]]
		inn = [(rad(1.0) - 0.2, 0.0), (rad(3.0) - 0.2, 3.0), (rad(9.0) - 0.2, 9.0), (rad(13.5) - 0.2, 13.5)]
		vs = []
		for (ro, z) in out + inn:
			for s in (-1, 1):
				c = u * ro + t * s
				vs.append((c.x, c.y, z))
		# out i -> verts 2i, 2i+1; inner j -> 8 + 2j, 9 + 2j
		faces = []
		for i in range(3):
			faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))           # outer edge
			faces.append((8 + 2 * i, 9 + 2 * i, 11 + 2 * i, 10 + 2 * i))     # inner edge
			faces.append((2 * i, 8 + 2 * i, 10 + 2 * i, 2 * i + 2))          # one face
			faces.append((2 * i + 1, 2 * i + 3, 11 + 2 * i, 9 + 2 * i))      # the other
		faces.append((0, 1, 9, 8))
		faces.append((6, 14, 15, 7))
		p.poly(vs, faces, DUSK_STONE, grad=(0.0, 0.9))
		d.seg(tuple(u * (rad(13.5) + 0.05) + Vector((0, 0, 13.4))), tuple(u * (rad(13.5) - 0.1) + Vector((0, 0, 14.6))), 0.12, 0.0, DUSK_TRIM, sides=4)
	# lancet windows up the faces
	for deg, z, h in ((-90, 4.4, 1.7), (-90, 8.2, 1.8), (-90, 12.0, 1.6), (0, 3.0, 1.6), (0, 7.0, 1.8), (0, 11.2, 1.6), (90, 2.4, 1.4),
					  (90, 6.4, 1.8), (90, 10.4, 1.6), (180, 4.6, 1.7), (180, 8.8, 1.8), (180, 12.6, 1.5)):
		r = rad(z + h / 2) * 1.0
		a = math.radians(deg)
		_lancet(d, (math.cos(a) * (r + 0.02), math.sin(a) * (r + 0.02), z), 0.46, h, yaw=deg + 90, pane=VIOLET, glow=1.6, frame=DUSK_TRIM, bars=False)
	_lancet(d, (0, -rad(1.0) - 0.04, 1.0), 1.5, 2.9, pane=MURK_BLACK, glow=0.0, frame=DUSK_TRIM, bars=False)   # the door
	for sx in (-1, 1):                                                  # violet lamps by the door
		d.seg((sx * 1.25, -2.2, 2.7), (sx * 1.25, -2.65, 2.7), 0.035, 0.035, DUSK_TRIM, sides=4)
		d.seg((sx * 1.25, -2.65, 2.45), (sx * 1.25, -2.65, 2.55), 0.1, 0.12, DUSK_TRIM, sides=6)
		d.blob((0.26, 0.26, 0.34), (sx * 1.25, -2.65, 2.72), VIOLET, segs=(8, 5), grad=(0.0, 0.4), glow=2.4)
		d.seg((sx * 1.25, -2.65, 2.88), (sx * 1.25, -2.65, 3.15), 0.1, 0.0, DUSK_TRIM, sides=5)
	# the balcony
	p.seg((0, 0, 14.9), (0, 0, 15.6), 1.35 / c8, 2.0 / c8, DUSK_TRIM, sides=8, grad=(0.0, 0.8), twist=22.5)
	p.seg((0, 0, 15.6), (0, 0, 15.85), 2.05 / c8, 2.05 / c8, DUSK_STONE, sides=8, twist=22.5)
	for k in range(16):                                                 # spiked parapet
		a = k * math.tau / 16
		d.seg((math.cos(a) * 1.95, math.sin(a) * 1.95, 15.8), (math.cos(a) * 1.95, math.sin(a) * 1.95, 16.7 + 0.25 * (k % 2)), 0.06, 0.0, DUSK_TRIM, sides=4)
	d.seg((0, 0, 16.45), (0, 0, 16.52), 1.97 / c8, 1.97 / c8, DUSK_TRIM, sides=8, twist=22.5)
	for k in range(4):                                                  # pinnacles
		a = math.radians(45 + k * 90)
		x, y = math.cos(a) * 1.9, math.sin(a) * 1.9
		p.seg((x, y, 15.8), (x, y, 17.0), 0.16, 0.14, DUSK_STONE, sides=6)
		p.seg((x, y, 17.0), (x, y, 18.6), 0.16, 0.0, DUSK_STONE, sides=6)
	# the upper stage and the needle roof
	o.seg((0, 0, 15.85), (0, 0, 19.6), 1.1 / c8, 0.95 / c8, DUSK_STONE, sides=8, grad=(0.0, 0.8), twist=22.5)
	for k in range(4):
		deg = k * 90
		a = math.radians(deg)
		_lancet(d, (math.cos(a) * 1.0, math.sin(a) * 1.0, 16.4), 0.44, 2.4, yaw=deg + 90, pane=VIOLET, glow=1.8, frame=DUSK_TRIM, bars=False)
	d.seg((0, 0, 19.5), (0, 0, 19.75), 1.2 / c8, 1.2 / c8, DUSK_TRIM, sides=8, twist=22.5)
	p.seg((0, 0, 19.75), (0, 0, 23.5), 1.15 / c8, 0.05, DUSK_STONE, sides=8, grad=(0.0, 0.8), twist=22.5)
	d.seg((0, 0, 23.35), (0, 0, 23.55), 0.1, 0.16, DUSK_TRIM, sides=8)
	d.blob((0.34, 0.34, 0.4), (0, 0, 23.75), VIOLET, segs=(8, 6), grad=(0.0, 0.4), glow=2.4)
	d.seg((0, 0, 23.9), (0, 0, 24.5), 0.05, 0.0, DUSK_TRIM, sides=4)
	o = _glossy(o.build(bevel=0.02), 0.3)
	return join_into(p.build(bevel=0.04), [o, d.build()])


def dusk_house():
	"""A Duskhold house, 9 x 7 m: two storeys of KayKit stone repainted dark
	(walls 6 m), violet-lit windows on every face, the door on the front (-Y)
	under a steep cross gable with a round violet window, a steep black main
	roof ridged along X (to about 11.2 m), a slim round turret on the back
	right corner with a needle roof (to 14 m), and a violet lamp by the door.
	About 10 x 8.5 m. Collide it as a mesh."""
	p = Prop("dusk_house", 977)
	hx, hy, RH = 4.5, 3.5, 3.0
	pieces = []

	def kinds(s, r, k):
		if s == 0:
			if r == 0:
				return "wall_doorway" if k == 1 else "wall_window_open"
			return "wall_window_open" if k != 1 else "wall"
		if s == 2:
			return "wall_window_open" if (r == 1 and k == 1) else "wall"
		return "wall_window_open" if (r == 0 and k == 0) else "wall"

	_kaykit_box(pieces, -hx, -hy, hx, hy, 0.0, 2, RH, kinds=kinds)
	for x in (-3.0, 0.0, 3.0):
		for y in (-1.75, 1.75):
			pieces += kaykit("floor_tile_large", (x, y, -0.07))
	p.box((2 * hx - 0.6, 2 * hy - 0.6, 6.0), (0, 0, 3.0), DUSK_STONE, grad=(0.3, 1.0))              # the solid core
	for x in (-3.0, 3.0):                                                                            # panes in the open windows
		p.box((1.7, 0.1, 1.7), (x, -hy + 0.2, 1.6), VIOLET, grad=(0.2, 0.6), glow=1.5)
		p.box((1.7, 0.1, 1.7), (x, -hy + 0.2, 4.6), VIOLET, grad=(0.2, 0.6), glow=1.5)
	p.box((1.7, 0.1, 1.7), (0.0, hy - 0.2, 4.6), VIOLET, grad=(0.2, 0.6), glow=1.5)
	p.box((0.1, 1.7, 1.7), (hx - 0.2, -1.75, 1.6), VIOLET, grad=(0.2, 0.6), glow=1.5)
	p.box((0.1, 1.7, 1.7), (-hx + 0.2, 1.75, 1.6), VIOLET, grad=(0.2, 0.6), glow=1.5)
	p.box((2 * hx + 0.9, 2 * hy + 0.9, 0.22), (0, 0, 3.0), DUSK_TRIM, grad=(0.0, 0.5))                 # band between floors
	p.box((2 * hx + 1.0, 2 * hy + 1.0, 0.25), (0, 0, 6.05), DUSK_TRIM, grad=(0.0, 0.6))
	p.box((1.9, 0.5, 0.22), (0, -hy - 0.35, 2.85), DUSK_TRIM, grad=(0.0, 0.5))                        # lintel over the door
	_steep_roof(p, (0, 0), 2 * hy + 0.6, 2 * hx + 0.6, 6.15, 5.0, slate=DUSK_STONE, wall=DUSK_STONE, ridge_x=True)
	# the cross gable over the door, ridge running into the main roof
	_steep_roof(p, (0, -hy + 1.6), 3.8, 3.6, 6.15, 4.4, slate=DUSK_STONE, wall=DUSK_STONE, over=0.35)
	GY = -hy - 0.25
	p.seg((0, GY + 0.05, 8.0), (0, GY - 0.08, 8.0), 0.62, 0.62, DUSK_TRIM, sides=14, grad=(0.0, 0.5))
	p.seg((0, GY - 0.08, 8.0), (0, GY - 0.13, 8.0), 0.48, 0.48, VIOLET, sides=14, grad=(0.1, 0.5), glow=1.6)
	for k in range(4):                                                                                 # the window's tracery
		a = k * math.pi / 4
		p.seg((math.cos(a) * 0.48, GY - 0.15, 8.0 + math.sin(a) * 0.48), (-math.cos(a) * 0.48, GY - 0.15, 8.0 - math.sin(a) * 0.48), 0.03, 0.03, DUSK_TRIM, sides=4)
	# the turret on the back right corner
	tx, ty = hx - 0.1, hy - 0.1
	p.seg((tx, ty, -0.2), (tx, ty, 8.6), 1.25, 1.15, DUSK_STONE, sides=10, grad=(0.1, 0.9))
	for z in (3.0, 6.0, 8.5):
		p.seg((tx, ty, z), (tx, ty, z + 0.2), 1.32, 1.3, DUSK_TRIM, sides=10, grad=(0.0, 0.6))
	for deg, z in ((0, 3.7), (90, 6.7), (45, 1.2)):
		a = math.radians(deg)
		_lancet(p, (tx + math.cos(a) * 1.18, ty + math.sin(a) * 1.18, z), 0.36, 1.4, yaw=deg + 90, pane=VIOLET, glow=1.6, frame=DUSK_TRIM, bars=False)
	p.seg((tx, ty, 8.7), (tx, ty, 14.0), 1.55, 0.02, DUSK_STONE, sides=10, grad=(0.0, 0.8))
	p.seg((tx, ty, 13.6), (tx, ty, 14.6), 0.04, 0.0, DUSK_TRIM, sides=4)
	# a violet lamp by the door
	p.seg((1.3, -hy - 0.42, 2.45), (1.3, -hy - 0.85, 2.45), 0.035, 0.035, DUSK_TRIM, sides=4)
	p.seg((1.3, -hy - 0.85, 2.05), (1.3, -hy - 0.85, 2.15), 0.09, 0.11, DUSK_TRIM, sides=6)
	p.blob((0.24, 0.24, 0.32), (1.3, -hy - 0.85, 2.3), VIOLET, segs=(8, 5), grad=(0.0, 0.4), glow=2.2)
	p.seg((1.3, -hy - 0.85, 2.45), (1.3, -hy - 0.85, 2.7), 0.09, 0.0, DUSK_TRIM, sides=5)
	obj = p.build(bevel=0.04)
	return _merge_materials(join_into(obj, _restone(pieces, NIGHT_STONE)))


def dusk_bridge():
	"""An arched stone footbridge, 20 m long (along X) and 3 m wide: a smooth
	walkable deck rising from ground level at x = +-10 to 2.5 m at the middle,
	a slender arch under it springing from footings at +-7.5, thin iron
	railings with pointed finials and four slim lamp posts with violet globes
	at the ends. Collide it as a mesh."""
	p = Prop("dusk_bridge", 978)
	d = Prop("dusk_bridge_detail", 979)
	S, W, H, T = 10.0, 1.5, 2.5, 0.35

	def top(x):
		return H * (1 - (x / S) ** 2)

	N = 28
	xs = [-S + 2 * S * i / N for i in range(N + 1)]
	vs, faces = [], []
	for x in xs:                                                     # the deck: 4 verts per station
		zt = top(x)
		vs += [(x, -W, zt), (x, W, zt), (x, W, zt - T), (x, -W, zt - T)]
	for i in range(N):
		a, b = 4 * i, 4 * (i + 1)
		faces += [(a, b, b + 1, a + 1), (a + 3, a + 2, b + 2, b + 3), (a, a + 3, b + 3, b), (a + 1, b + 1, b + 2, a + 2)]
	faces += [(0, 1, 2, 3), (4 * N, 4 * N + 3, 4 * N + 2, 4 * N + 1)]
	p.poly(vs, faces, DUSK_TRIM, grad=(0.0, 0.6))
	# the arch body: between the deck's underside and the intrados
	SP, CR = 7.5, 1.35

	def intr(x):
		return -0.8 + (CR + 0.8) * (1 - (x / SP) ** 2)

	M = 24
	xs = [-S + 0.6 + (2 * S - 1.2) * i / M for i in range(M + 1)]
	vs, faces = [], []
	BW = W - 0.2
	for x in xs:
		up = top(x) - T + 0.02
		lo = min(intr(x), up - 0.25) if abs(x) < SP else -0.8
		vs += [(x, -BW, up), (x, BW, up), (x, BW, lo), (x, -BW, lo)]
	for i in range(M):
		a, b = 4 * i, 4 * (i + 1)
		faces += [(a, b, b + 1, a + 1), (a + 3, a + 2, b + 2, b + 3), (a, a + 3, b + 3, b), (a + 1, b + 1, b + 2, a + 2)]
	faces += [(0, 1, 2, 3), (4 * M, 4 * M + 3, 4 * M + 2, 4 * M + 1)]
	p.poly(vs, faces, DUSK_STONE, grad=(0.0, 0.9))
	for sy in (-1, 1):                                               # a molded rib along the arch's edge
		pts = [(x, sy * (BW + 0.02), intr(x) + 0.05) for x in (-SP + 2 * SP * i / 12 for i in range(13))]
		_chain(p, pts, 0.14, 0.14, DUSK_TRIM, sides=6)
		pts = [(x, sy * (W + 0.02), top(x) - T - 0.02) for x in (-S + 2 * S * i / 14 for i in range(15))]
		_chain(p, pts, 0.1, 0.1, DUSK_TRIM, sides=5)
	for sx in (-1, 1):                                               # footings where the arch springs
		p.box((1.6, 2 * W + 0.3, 1.4), (sx * (SP + 0.3), 0, -0.6), DUSK_TRIM, grad=(0.2, 1.0))
	# railings: thin posts with pointed finials and a rail following the deck
	RH = 1.0
	for sy in (-1, 1):
		y = sy * (W - 0.12)
		for i in range(11):
			x = -S + 1.0 + i * (2 * S - 2.0) / 10
			z = top(x)
			d.seg((x, y, z - 0.05), (x, y, z + RH), 0.04, 0.035, IRON, sides=4)
			d.seg((x, y, z + RH), (x, y, z + RH + 0.22), 0.05, 0.0, IRON, sides=4)
		pts = [(x, y, top(x) + RH - 0.05) for x in (-S + 1.0 + (2 * S - 2.0) * i / 16 for i in range(17))]
		_chain(d, pts, 0.03, 0.03, IRON, sides=4)
		pts = [(x, y, top(x) + 0.35) for x in (-S + 1.0 + (2 * S - 2.0) * i / 16 for i in range(17))]
		_chain(d, pts, 0.02, 0.02, IRON, sides=4)
		for sx in (-1, 1):                                            # lamp posts at the ends
			x = sx * (S - 0.45)
			z = top(x)
			d.seg((x, y, z - 0.2), (x, y, z + 0.25), 0.16, 0.1, DUSK_TRIM, sides=6)
			d.seg((x, y, z + 0.25), (x, y, z + 2.0), 0.05, 0.045, IRON, sides=6)
			d.seg((x, y, z + 1.95), (x, y, z + 2.05), 0.09, 0.11, IRON, sides=6)
			d.blob((0.24, 0.24, 0.3), (x, y, z + 2.2), VIOLET, segs=(8, 5), grad=(0.0, 0.4), glow=2.2)
			d.seg((x, y, z + 2.33), (x, y, z + 2.6), 0.08, 0.0, IRON, sides=5)
	return join_into(p.build(bevel=0.03), [d.build()])


def stalagmite_cluster():
	"""Four cave stalagmites 4.3 to 8 m tall in warm gray rock ringed with drip
	bands, leaning a little apart, with stubs and fallen rock at their feet.
	About 5.5 x 5 m. Collide it as a box (or mesh)."""
	p = Prop("stalagmite_cluster", 980)
	rng = p.rng
	spikes = [((0.0, 0.0), 8.0, 1.6, (0.1, 0.05)), ((1.9, 0.7), 5.6, 1.15, (0.35, 0.1)), ((-1.7, 0.9), 6.3, 1.25, (-0.3, 0.12)),
			  ((0.5, -1.8), 4.3, 1.0, (0.1, -0.3)), ((-1.4, -1.3), 2.0, 0.65, (-0.2, -0.2)), ((2.4, -1.0), 1.4, 0.5, (0.2, -0.1))]
	for k, ((x, y), h, r, (lx, ly)) in enumerate(spikes):
		prof = [(0.02, -0.4), (r * 1.15, -0.4)]
		n = 9
		for i in range(1, n):
			t = i / n
			rr = r * (1 - t ** 1.3) ** 0.9 * (1.0 + 0.13 * math.sin(i * 2.3 + k) + 0.08 * (i % 2))
			prof.append((max(rr, r * 0.16), h * t))
		prof += [(r * 0.1, h * 0.99), (0.02, h)]
		obj = _lathe(p, prof, 9, CAVE_STONE, grad=CAVE_TONE if k % 2 else (0.2, 0.95), jitter=r * 0.07)
		obj.data.transform(Matrix.Translation((x, y, 0)) @ Matrix.Shear("XY", 4, (lx / max(h, 1.0), ly / max(h, 1.0))))
	for k in range(9):
		a = rng.uniform(0, math.tau)
		rr = rng.uniform(1.8, 2.8)
		s = rng.uniform(0.4, 0.9)
		p.rock((s * 1.3, s, s * 0.6), (math.cos(a) * rr, math.sin(a) * rr, 0.05), CAVE_STONE, rot=(0, 0, rng.uniform(0, 180)), grad=CAVE_TONE)
	return p.build(bevel=0.03)


def glow_crystal():
	"""A cluster of seven glowing violet crystals, six-sided and pointed, 0.6 to
	2.4 m, leaning out of a dark rock bed about 2.4 m across, with loose shards
	round it. Glossy. Collide it as a box."""
	p = Prop("glow_crystal", 981)
	c = Prop("glow_crystal_glass", 982)
	rng = p.rng
	for k in range(6):
		a = k * math.tau / 6 + rng.uniform(-0.3, 0.3)
		p.rock((1.0, 0.9, 0.55), (math.cos(a) * 0.7, math.sin(a) * 0.7, 0.05), STONE_DARK, jitter=0.08)
	p.rock((1.3, 1.2, 0.6), (0, 0, 0.05), MURK_BLACK, jitter=0.08)
	xs = [((0.0, 0.0), 2.4, 0.3, (0.05, 0.02)), ((0.45, 0.25), 1.8, 0.22, (0.45, 0.15)), ((-0.4, 0.3), 2.0, 0.24, (-0.4, 0.2)),
		  ((0.1, -0.45), 1.5, 0.2, (0.1, -0.5)), ((-0.35, -0.3), 1.1, 0.16, (-0.45, -0.3)), ((0.55, -0.3), 0.9, 0.14, (0.55, -0.35)), ((-0.1, 0.55), 0.6, 0.12, (0.0, 0.6))]
	for k, ((x, y), h, r, (lx, ly)) in enumerate(xs):
		base = Vector((x, y, 0.0))
		dirv = Vector((lx, ly, 1.0)).normalized()
		shaft = base + dirv * h * 0.8
		tip = base + dirv * h
		tw = rng.uniform(0, 60)
		c.seg(tuple(base), tuple(shaft), r, r * 0.95, VIOLET, sides=6, grad=(0.0, 0.7), glow=1.6, twist=tw)
		c.seg(tuple(shaft), tuple(tip), r * 0.95, 0.0, VIOLET, sides=6, grad=(0.0, 0.35), glow=2.0, twist=tw)
	for k in range(6):
		a = rng.uniform(0, math.tau)
		rr = rng.uniform(1.0, 1.4)
		b = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.0))
		c.seg(tuple(b), tuple(b + Vector((math.cos(a) * 0.15, math.sin(a) * 0.15, rng.uniform(0.2, 0.4)))), 0.07, 0.0, VIOLET, sides=5, grad=(0.0, 0.5), glow=1.6)
	return join_into(p.build(bevel=0.02), [_glossy(c.build(), 0.15)])


def candle_stand():
	"""A tall wrought-iron candelabrum, about 2.45 m: three curled feet, a
	twisted stem with knops, six scrolled arms holding a crown of drip cups
	and candles (flames at about 2.25 m) round a taller center candle. Collide
	it as a trunk (or none)."""
	p = Prop("candle_stand", 983)
	f = Prop("candle_stand_flames", 984)
	rng = p.rng
	for k in range(3):                                               # curled feet
		a = k * math.tau / 3
		u = Vector((math.cos(a), math.sin(a), 0))
		pts = [tuple(u * r + Vector((0, 0, z))) for r, z in ((0.03, 0.42), (0.2, 0.22), (0.38, 0.04), (0.48, 0.05), (0.5, 0.14), (0.45, 0.2))]
		_chain(p, pts, 0.045, 0.03, IRON, sides=5)
	p.blob((0.2, 0.2, 0.16), (0, 0, 0.45), IRON, segs=(8, 5))
	for i in range(8):                                               # a twisted stem: two strands winding round a core
		z0, z1 = 0.5 + i * 0.17, 0.5 + (i + 1) * 0.17
		for s in (0, math.pi):
			a0, a1 = s + i * 0.9, s + (i + 1) * 0.9
			p.seg((math.cos(a0) * 0.035, math.sin(a0) * 0.035, z0), (math.cos(a1) * 0.035, math.sin(a1) * 0.035, z1), 0.022, 0.022, IRON, sides=4)
	p.seg((0, 0, 0.45), (0, 0, 1.9), 0.03, 0.028, IRON, sides=6)
	for z in (1.2, 1.9):
		p.blob((0.13, 0.13, 0.1), (0, 0, z), IRON, segs=(8, 4))
	tops = []
	for k in range(6):                                               # scrolled arms to the crown
		a = k * math.tau / 6
		u = Vector((math.cos(a), math.sin(a), 0))
		pts = [tuple(u * r + Vector((0, 0, z))) for r, z in ((0.04, 1.92), (0.22, 1.86), (0.38, 1.9), (0.45, 2.0))]
		_chain(p, pts, 0.028, 0.024, IRON, sides=5)
		p.seg(tuple(u * 0.3 + Vector((0, 0, 1.87))), tuple(u * 0.25 + Vector((0, 0, 1.75))), 0.02, 0.01, IRON, sides=4)   # the scroll's curl
		tops.append(tuple(u * 0.45 + Vector((0, 0, 2.0))))
	for k in range(6):                                               # the crown ring
		a0, a1 = k * math.tau / 6, (k + 1) * math.tau / 6
		p.seg((math.cos(a0) * 0.45, math.sin(a0) * 0.45, 1.98), (math.cos(a1) * 0.45, math.sin(a1) * 0.45, 1.98), 0.02, 0.02, IRON, sides=4)
	p.seg((0, 0, 1.9), (0, 0, 2.05), 0.03, 0.03, IRON, sides=5)
	tops.append((0.0, 0.0, 2.05))
	for i, (x, y, z) in enumerate(tops):
		h = 0.34 if i == 6 else rng.uniform(0.18, 0.3)
		p.seg((x, y, z - 0.02), (x, y, z + 0.04), 0.07, 0.085, IRON, sides=7)      # drip cup
		p.seg((x, y, z + 0.03), (x, y, z + h), 0.04, 0.038, CLOTH_WHITE, sides=6, grad=(0.0, 0.5))
		p.seg((x + 0.03, y, z + h - 0.02), (x + 0.042, y, z + h - 0.12), 0.012, 0.008, CLOTH_WHITE, sides=3)   # a wax drip
		f.seg((x, y, z + h + 0.005), (x, y, z + h + 0.14), 0.028, 0.0, FLAME, sides=5, grad=(0.0, 0.45), glow=2.6)
		f.blob((0.07, 0.07, 0.1), (x, y, z + h + 0.05), FLAME, segs=(5, 4), grad=(0.3, 0.6), glow=1.8)
	return join_into(p.build(), [f.build()])


def _arch_outline(half=5.0, spring=7.0, apex=12.5, n_arc=10, n_side=4):
	"""A pointed arch opening in the X-Z plane, from the bottom-left corner up
	over the apex and down to the bottom-right: [(x, z)]."""
	cx = ((apex - spring) ** 2 - half * half) / (2 * half)          # the left arc's center (cx, spring); the right is mirrored
	R = half + cx
	top = math.atan2(apex - spring, 0 - cx)
	left = [(-half, spring * i / n_side) for i in range(n_side)]
	arc = []
	for i in range(n_arc + 1):
		a = math.pi + (top - math.pi) * i / n_arc
		arc.append((cx + math.cos(a) * R, spring + math.sin(a) * R))
	right_arc = [(-x, z) for x, z in reversed(arc[:-1])]
	right = [(half, spring * (n_side - i) / n_side) for i in range(1, n_side + 1)]
	return left + arc + right_arc + right


def dusk_gate():
	"""The cavern entrance of Duskhold: a rough rock face 34 m wide and about
	24 m tall with a pointed arch 10 m wide and 12.5 m tall carved through it
	(its front faces -Y), a tunnel with a flat floor at ground level running
	12 m back into black darkness (walkable to about 11 m in; put the zone
	line there), a frame of dark dressed voussoirs with glowing violet runes, a
	keystone rune, and two slender pillars carrying violet lamps. Collide it
	as a mesh."""
	p = Prop("dusk_gate", 985)
	d = Prop("dusk_gate_detail", 986)
	rng = p.rng
	HW, SPR, APX, DEPTH = 5.0, 7.0, 12.5, 12.0
	outline = _arch_outline(HW, SPR, APX)
	# resample the outline by arc length
	segl = [math.dist(a, b) for a, b in zip(outline, outline[1:])]
	total = sum(segl)
	M = 40
	res = []
	for i in range(M + 1):
		s = total * i / M
		for j, L in enumerate(segl):
			if s <= L or j == len(segl) - 1:
				t = min(s / L, 1.0)
				a, b = outline[j], outline[j + 1]
				res.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
				break
			s -= L
	outline = res
	# the outer border (left side, top, right side) sampled at the same fractions
	OX, OZ = 17.0, 24.0
	per = [(-OX, 0.0), (-OX, OZ), (OX, OZ), (OX, 0.0)]
	pl = [math.dist(a, b) for a, b in zip(per, per[1:])]
	ptot = sum(pl)

	def outer(f):
		s = ptot * f
		for j, L in enumerate(pl):
			if s <= L or j == len(pl) - 1:
				t = min(s / L, 1.0)
				a, b = per[j], per[j + 1]
				return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
			s -= L

	K = 6
	rings = []
	for k in range(K + 1):
		t = (k / K) ** 1.5
		ring = []
		for i, (x, z) in enumerate(outline):
			ox, oz = outer(i / M)
			px, pz = x + (ox - x) * t, z + (oz - z) * t
			edge = i == 0 or i == M
			if k == 0:
				y = 0.0
			elif k == K:
				y = 0.0
			else:
				y = -1.6 * math.sin(math.pi * t) + rng.uniform(-0.7, 0.7)
				px += rng.uniform(-0.5, 0.5)
				if not edge:
					pz += rng.uniform(-0.5, 0.5)
			ring.append((px, y, pz if not edge else -0.6))
		rings.append(ring)
	vs, faces = [], []
	for ring in rings:
		vs += ring
	W = M + 1
	for k in range(K):                                                 # the front face, facing -Y
		for i in range(M):
			a, b = k * W + i, (k + 1) * W + i
			faces.append((a, b, b + 1, a + 1))
	back = len(vs)                                                     # the same outer border 12 m back, and the tunnel's mouth there
	vs += [(x, DEPTH, z) for x, _, z in rings[K]]
	vs += [(x, DEPTH, z) for x, _, z in rings[0]]
	for i in range(M):
		a, b = K * W + i, back + i
		faces.append((a, a + 1, b + 1, b))                             # top and sides of the block
		c = back + W + i
		faces.append((b, b + 1, c + 1, c))                             # the back face
	vs = [(x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.6, 0.6) * (0 < y < DEPTH), z + rng.uniform(-0.8, 0.8) * (z > 0)) if i >= back else (x, y, z) for i, (x, y, z) in enumerate(vs)]
	p.poly(vs, faces, CAVE_STONE, grad=CAVE_TONE)
	for k in range(26):                                                # boulders bedded in the face, clear of the arch
		for _ in range(20):
			x, z = rng.uniform(-OX + 1.5, OX - 1.5), rng.uniform(1.0, OZ - 1.5)
			if min(math.hypot(x - ox, z - oz) for ox, oz in outline) > 3.2 and not (abs(x) < HW + 2.5 and z < APX + 2.5):
				break
		s = rng.uniform(1.8, 4.0)
		p.rock((s * 1.4, s * 0.8, s), (x, rng.uniform(-1.4, -0.4), z), CAVE_STONE, rot=(rng.uniform(-20, 20), 0, rng.uniform(-30, 30)), grad=CAVE_TONE, jitter=0.12)
	for k in range(9):                                                 # boulders along the top edge
		x = -OX + 2 + k * (2 * OX - 4) / 8 + rng.uniform(-1, 1)
		s = rng.uniform(2.5, 4.0)
		p.rock((s * 1.4, s, s * 0.8), (x, rng.uniform(1.5, 6.0), OZ - 0.5), CAVE_STONE, rot=(0, 0, rng.uniform(0, 180)), grad=CAVE_TONE)
	for sx in (-1, 1):
		for k in range(3):
			s = rng.uniform(2.5, 3.5)
			p.rock((s, s * 1.2, s * 1.3), (sx * OX, rng.uniform(1.0, 9.0), 4 + k * 7), CAVE_STONE, rot=(0, 0, rng.uniform(0, 180)), grad=CAVE_TONE)
	# the tunnel: walls round the outline, flat floor, darkness at the back
	vs, faces = [], []
	STEPS = 4
	for sidx in range(STEPS + 1):
		y = DEPTH * sidx / STEPS
		for i, (x, z) in enumerate(outline):
			j = 0.0 if sidx in (0, STEPS) else 0.25
			vs.append((x * (1 + rng.uniform(-0.02, 0.03) * (sidx > 0)), y, z + (rng.uniform(-j, j) if 0 < i < M else -0.6)))
	for sidx in range(STEPS):
		for i in range(M):
			a, b = sidx * W + i, (sidx + 1) * W + i
			faces.append((a, a + 1, b + 1, b))
	_raw_mesh(p, vs, faces, MURK_BLACK, grad=(0.0, 0.9))
	p.box((2 * HW + 0.4, DEPTH, 0.3), (0, DEPTH / 2, -0.13), DUSK_TRIM, grad=(0.3, 0.9))     # the floor, top at ground level
	_plate(d, [(x * 0.99, z) for x, z in outline], DEPTH - 0.5, 0.2, SHADE, grad=(0.97, 1.0))
	# the carved frame: voussoirs round the arch, some with glowing runes
	frame = outline[3:-3]
	for i in range(0, len(frame) - 1):
		(x0, z0), (x1, z1) = frame[i], frame[i + 1]
		mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
		tx, tz = x1 - x0, z1 - z0
		L = math.hypot(tx, tz)
		nx, nz = -tz / L, tx / L                                       # outward normal (away from the opening)
		if nx * mx + nz * (mz - 6.0) < 0:
			nx, nz = -nx, -nz
		ang = math.degrees(math.atan2(tz, tx))
		c = (mx + nx * 0.45, -0.35, mz + nz * 0.45)
		p.box((L * 0.96, 0.9, 0.95), c, DUSK_TRIM if i % 2 else DUSK_STONE, rot=(0, -ang, 0), grad=(0.0, 0.8))
		if i % 3 == 1:
			d.box((L * 0.4, 0.06, 0.4), (c[0], -0.83, c[2]), VIOLET, rot=(0, -ang, 0), grad=(0.1, 0.4), glow=1.8)
	ax, az = 0.0, APX + 0.55
	p.box((1.4, 1.2, 1.7), (ax, -0.45, az), DUSK_TRIM, grad=(0.0, 0.7))                    # keystone
	_plate(d, [(-0.3, az - 0.5), (0.0, az - 0.62), (0.3, az - 0.5), (0.4, az), (0.0, az + 0.6), (-0.4, az)], -1.08, 0.06, VIOLET, glow=2.2)
	for sx in (-1, 1):                                                 # pillars with violet lamps
		x = sx * (HW + 1.6)
		p.box((1.3, 1.3, 0.6), (x, -1.1, 0.1), DUSK_TRIM, grad=(0.1, 0.9))
		p.seg((x, -1.1, 0.4), (x, -1.1, 8.2), 0.42, 0.34, DUSK_STONE, sides=8, grad=(0.0, 0.9))
		p.seg((x, -1.1, 8.2), (x, -1.1, 8.55), 0.55, 0.6, DUSK_TRIM, sides=8)
		p.seg((x, -1.1, 8.55), (x, -1.1, 8.7), 0.3, 0.3, DUSK_TRIM, sides=8)
		d.blob((0.62, 0.62, 0.75), (x, -1.1, 9.1), VIOLET, segs=(10, 6), grad=(0.0, 0.4), glow=2.4)
		for k in range(4):
			a = k * math.pi / 2 + math.pi / 4
			d.seg((x + math.cos(a) * 0.3, -1.1 + math.sin(a) * 0.3, 8.65), (x + math.cos(a) * 0.12, -1.1 + math.sin(a) * 0.12, 9.75), 0.03, 0.03, IRON, sides=4)
		d.seg((x, -1.1, 9.7), (x, -1.1, 10.4), 0.1, 0.0, IRON, sides=5)
	for k in range(10):                                                # fallen rock along the foot of the face
		x = rng.choice((-1, 1)) * rng.uniform(HW + 3.0, OX - 1.0)
		s = rng.uniform(0.8, 1.8)
		p.rock((s * 1.3, s, s * 0.8), (x, rng.uniform(-2.0, -0.8), 0.1), CAVE_STONE, rot=(0, 0, rng.uniform(0, 180)), grad=CAVE_TONE)
	return join_into(p.build(bevel=0.04), [d.build()])


def _dusk_crown(p, c, r, n, rng, flat=0.65):
	"""A crown of deep violet leaf clusters round c (the swatch's darker half,
	a few lighter lilac tops)."""
	x, y, z = c
	for k in range(n):
		a = k * math.tau / n + rng.uniform(-0.3, 0.3)
		rr = r * rng.uniform(0.35, 0.7) if k else 0.0
		s = r * rng.uniform(0.7, 1.0)
		p.rock((s * 1.25, s * 1.25, s * flat), (x + math.cos(a) * rr, y + math.sin(a) * rr, z + rng.uniform(-0.2, 0.3) * r), DUSK_LEAF,
			   rot=(0, 0, rng.uniform(0, 360)), grad=(0.5, 1.0) if k % 3 else (0.3, 0.95), jitter=0.07)


def dusk_tree():
	"""A broad Duskwood tree, about 16 m: a straight black trunk with flared
	roots, crooked black boughs spreading from 6 m, and heavy crowns of deep
	violet leaves. Use it in a zone's tree_mix (trunk collider)."""
	p = Prop("dusk_tree", 987)
	rng = p.rng
	trunk = [(0, 0, -0.3), (0.08, 0.05, 3.0), (-0.12, 0.0, 6.0), (0.06, -0.08, 9.0), (0.15, 0.0, 11.8)]
	_chain(p, trunk, 0.55, 0.22, NIGHT_BARK, sides=8, grad=(0.2, 1.0))
	for k in range(6):
		a = k * math.tau / 6 + 0.3
		p.seg((0, 0, 0.9), (math.cos(a) * 1.4, math.sin(a) * 1.4, -0.25), 0.3, 0.07, NIGHT_BARK, sides=5, grad=(0.4, 1.0))
	crowns = [((0.15, 0.0, 13.4), 3.4)]
	for k, (z, a, L) in enumerate(((5.8, 0.2, 4.2), (6.8, 2.3, 4.0), (7.8, 4.2, 3.8), (9.0, 1.2, 3.4), (10.0, 3.3, 3.0), (10.8, 5.3, 2.6))):
		b = Vector((0, 0, z))
		m = b + Vector((math.cos(a) * L * 0.55, math.sin(a) * L * 0.55, L * 0.25))
		e = b + Vector((math.cos(a + 0.25) * L, math.sin(a + 0.25) * L, L * 0.7))
		_chain(p, [tuple(b), tuple(m), tuple(e)], 0.2, 0.06, NIGHT_BARK, sides=5, grad=(0.2, 1.0))
		crowns.append((tuple(e + Vector((0, 0, 0.4))), 2.8))
	for c, r in crowns:
		_dusk_crown(p, c, r, 6, rng)
	return p.build()


def dusk_tree_b():
	"""A tall, narrow Duskwood tree, about 19 m: a slim black trunk climbing
	through drooping tiers of deep violet foliage that narrow to a spire,
	a few bare black twigs poking out. Use it in a zone's tree_mix (trunk collider)."""
	p = Prop("dusk_tree_b", 988)
	rng = p.rng
	_chain(p, [(0, 0, -0.3), (0.05, 0.0, 5.0), (-0.05, 0.05, 10.0), (0.05, 0.0, 15.0), (0.0, 0.0, 18.0)], 0.45, 0.12, NIGHT_BARK, sides=7, grad=(0.2, 1.0))
	for k in range(5):
		a = k * math.tau / 5 + 0.6
		p.seg((0, 0, 0.8), (math.cos(a) * 1.1, math.sin(a) * 1.1, -0.25), 0.26, 0.06, NIGHT_BARK, sides=5, grad=(0.4, 1.0))
	tiers = [(4.0, 3.4, 3.2), (6.6, 3.0, 3.0), (9.0, 2.6, 2.8), (11.3, 2.1, 2.6), (13.4, 1.6, 2.4), (15.3, 1.1, 2.2), (17.0, 0.6, 2.2)]
	for i, (z, r, h) in enumerate(tiers):
		# a drooping tier: a skirt that hangs down from the trunk, lumpy at its hem
		n = 9
		tw = rng.uniform(0, 40)
		p.seg((0, 0, z - h * 0.35), (0, 0, z + h * 0.65), r, 0.0, DUSK_LEAF, sides=n, grad=(0.45, 1.0), jitter=0.12, twist=tw)
		for k in range(n):
			a = math.radians(tw) + k * math.tau / n
			p.blob((r * 0.55, r * 0.55, h * 0.3), (math.cos(a) * r * 0.85, math.sin(a) * r * 0.85, z - h * 0.4), DUSK_LEAF, segs=(6, 4), grad=(0.65, 1.0), jitter=0.05)
	for k in range(4):                                                  # bare twigs
		a = rng.uniform(0, math.tau)
		z = rng.uniform(3.0, 12.0)
		p.seg((0, 0, z), (math.cos(a) * 2.6, math.sin(a) * 2.6, z + 1.0), 0.06, 0.01, NIGHT_BARK, sides=4)
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
	"cave_entrance": cave_entrance,
	"bridge_wood": bridge_wood,
	"cobweb": cobweb,
	"web_mound": web_mound,
	"egg_sacs": egg_sacs,
	"drying_rack": drying_rack,
	"woodpile": woodpile,
	"banner_pole": banner_pole,
	"palisade": palisade,
	"roof_gable": roof_gable,
	"hearth": hearth,
	"city_wall": city_wall,
	"city_tower": city_tower,
	"city_gate": city_gate,
	"lamp_post": lamp_post,
	"market_stall": market_stall,
	"well": well,
	"tavern": tavern,
	"tavern_bar": tavern_bar,
	"signpost": signpost,
	"grass_a": lambda: grass("grass_a", 61, 11, 0.42),
	"grass_b": lambda: grass("grass_b", 62, 7, 0.28),
	"flowers_yellow": lambda: flowers("flowers_yellow", 63, PETAL_YELLOW),
	"flowers_purple": lambda: flowers("flowers_purple", 64, PETAL_PURPLE),
	"flowers_white": lambda: flowers("flowers_white", 65, PETAL_WHITE),
	"fern": fern,
	"bush_a": lambda: bush("bush_a", 66, 4),
	"bush_b": lambda: bush("bush_b", 67, 6),
	"mushrooms": mushrooms,
	"pebbles": pebbles,
	"log_fallen": log_fallen,
	"stump": stump,
	"dock": dock,
	"reeds": reeds,
	"lily_pads": lily_pads,
	"fishing_pole": fishing_pole,
	"boardwalk": boardwalk,
	"boardwalk_ramp": boardwalk_ramp,
	"stilt_hut": stilt_hut,
	"rowboat": rowboat,
	"reed_hut": reed_hut,
	"bone_totem": bone_totem,
	"windmill": windmill,
	"windmill_sails": windmill_sails,
	"fence_wood": fence_wood,
	"hay_bale": hay_bale,
	"haystack": haystack,
	"farm_cart": farm_cart,
	"wheat": wheat,
	"scarecrow_post": scarecrow_post,
	"elephant_statue": elephant_statue,
	"sun_pillar": sun_pillar,
	"broken_column": broken_column,
	"sun_banner": sun_banner,
	"lantern_string": lantern_string,
	"titan_ribcage": titan_ribcage,
	"titan_skull": titan_skull,
	"mesa": mesa,
	"salt_crystals": salt_crystals,
	"dead_palm": dead_palm,
	"caravan_wagon": caravan_wagon,
	"jungle_tree": jungle_tree,
	"jungle_tree_giant": jungle_tree_giant,
	"hanging_vines": hanging_vines,
	"fern_clump": fern_clump,
	"taro_plant": taro_plant,
	"jungle_temple": jungle_temple,
	"temple_arch_ruin": temple_arch_ruin,
	"jalendra_head_fallen": jalendra_head_fallen,
	"troll_hut": troll_hut,
	"troll_totem": troll_totem,
	"waterfall": waterfall,
	"waterfall_water": waterfall_water,
	"stilt_platform": stilt_platform,
	"stilt_walkway": stilt_walkway,
	"rope_bridge": rope_bridge,
	"stilt_hall": stilt_hall,
	"stilt_house": stilt_house,
	"jalendra_shrine": jalendra_shrine,
	"canoe": canoe,
	"oven": oven,
	"loom": loom,
	"brew_barrel": brew_barrel,
	"forge": forge,
	"crypt_entrance": crypt_entrance,
	"crypt_room": crypt_room,
	"monastery_hall": monastery_hall,
	"monastery_gate": monastery_gate,
	"stupa": stupa,
	"prayer_flags": lambda: _prayer_flags("prayer_flags", 8.0, 4.2, 0.9),
	"prayer_flags_short": lambda: _prayer_flags("prayer_flags_short", 4.0, 3.2, 0.45),
	"prayer_wheel": prayer_wheel,
	"stone_lantern": stone_lantern,
	"tea_bush": tea_bush,
	"rice_shoots": rice_shoots,
	"harpy_nest": harpy_nest,
	"broken_pillar": broken_pillar,
	"pilgrim_shelter": pilgrim_shelter,
	"charred_tree": lambda: _charred("charred_tree", 217, 6.0, (0.4, 0.1), [(2.6, 0.6, 1.6), (3.6, 3.2, 1.3), (4.5, 1.8, 1.0), (1.9, 4.6, 0.7)], 0.36),
	"charred_tree_tall": lambda: _charred("charred_tree_tall", 218, 9.5, (-0.5, 0.3), [(5.2, 2.2, 1.8), (6.8, 5.4, 1.4), (3.5, 0.3, 0.9), (7.9, 1.0, 1.1), (4.4, 4.0, 1.2)], 0.42),
	"charred_log": charred_log,
	"obsidian_spire": obsidian_spire,
	"basalt_columns": basalt_columns,
	"lava_vent": lava_vent,
	"ash_boulder_a": lambda: ash_boulder("ash_boulder_a", 229, [((2.3, 1.9, 1.4), (0, 0, 0.45)), ((1.1, 1.0, 0.8), (1.1, 0.5, 0.25))]),
	"ash_boulder_b": lambda: ash_boulder("ash_boulder_b", 230, [((1.3, 1.2, 1.9), (0, 0, 0.8))]),
	"ash_boulder_c": lambda: ash_boulder("ash_boulder_c", 231, [((2.8, 2.2, 0.9), (0, 0, 0.25)), ((1.2, 1.0, 1.0), (-0.9, 0.6, 0.5)), ((0.7, 0.6, 0.5), (1.3, -0.7, 0.15))]),
	"cultist_brazier": cultist_brazier,
	"ember_banner": ember_banner,
	"scout_tent": scout_tent,
	"weapon_rack": weapon_rack,
	"stilt_platform_broken": stilt_platform_broken,
	"stilt_walkway_broken": stilt_walkway_broken,
	"stilt_hut_sunken": stilt_hut_sunken,
	"pondkin_hut": pondkin_hut,
	"pondkin_totem": pondkin_totem,
	"witch_hut": witch_hut,
	"witch_cauldron": witch_cauldron,
	"heron_rookery_nest": heron_rookery_nest,
	"reeds_tall": reeds_tall,
	"mooring_post": mooring_post,
	"citadel_tower": citadel_tower,
	"citadel_wall_ruin": citadel_wall_ruin,
	"causeway_span": causeway_span,
	"causeway_broken": causeway_broken,
	"citadel_platform": citadel_platform,
	"sea_temple": sea_temple,
	"tideking_throne": tideking_throne,
	"shipwreck": shipwreck,
	"coral_growth": coral_growth,
	"naga_shrine": naga_shrine,
	"tea_house": tea_house,
	"tea_drying_rack": tea_drying_rack,
	"picker_basket": picker_basket,
	"shrine_broken": shrine_broken,
	"dustpaw_hut": dustpaw_hut,
	"dustpaw_totem": dustpaw_totem,
	"dustpaw_fire": dustpaw_fire,
	"burned_cabin": burned_cabin,
	"burned_sawmill": burned_sawmill,
	"smoldering_stump": smoldering_stump,
	"giant_anvil": giant_anvil,
	"giant_hall_ruin": giant_hall_ruin,
	"firebird_nest": firebird_nest,
	"glass_shards": glass_shards,
	"glass_crack": glass_crack,
	"glass_pool": glass_pool,
	"glass_entombed": glass_entombed,
	"forge_gate": forge_gate,
	"forge_hall": forge_hall,
	"smelter": smelter,
	"ore_cart": ore_cart,
	"mine_entrance": mine_entrance,
	"basalt_house": basalt_house,
	"agnavar_shrine": agnavar_shrine,
	"great_anvil": great_anvil,
	"lava_trough": lava_trough,
	"fortress_wall": fortress_wall,
	"fortress_gatehouse": fortress_gatehouse,
	"fortress_keep": fortress_keep,
	"dawn_beacon": dawn_beacon,
	"siege_catapult": siege_catapult,
	"siege_ram": siege_ram,
	"ogre_war_camp_tent": ogre_war_camp_tent,
	"snow_drift": snow_drift,
	"salt_crust_island": salt_crust_island,
	"salt_pillar": salt_pillar,
	"sand_skiff": sand_skiff,
	"nomad_tent": nomad_tent,
	"mirror_obelisk": mirror_obelisk,
	"mangrove_tree": mangrove_tree,
	"mud_dam": mud_dam,
	"silt_mound": silt_mound,
	"fishing_hut_stilts": fishing_hut_stilts,
	"sunken_barge": sunken_barge,
	"lighthouse": lighthouse,
	"harbor_warehouse": harbor_warehouse,
	"harbor_pier": harbor_pier,
	"reaver_longship": reaver_longship,
	"harbor_barricade": harbor_barricade,
	"storm_brazier": storm_brazier,
	"galehold_gate": galehold_gate,
	"sail_tower": sail_tower,
	"sail_tower_rotor": sail_tower_rotor,
	"cliff_house": cliff_house,
	"wind_chimes": wind_chimes,
	"kite_pole": kite_pole,
	"vayuketh_shrine": vayuketh_shrine,
	"cliff_edge_rail": cliff_edge_rail,
	"kite_glider": kite_glider,
	"bandit_lookout": bandit_lookout,
	"rope_anchor": rope_anchor,
	"giant_cairn": giant_cairn,
	"thunderbird_nest": thunderbird_nest,
	"tallgrass": tallgrass,
	"lone_tree": lone_tree,
	"hoofborn_yurt": hoofborn_yurt,
	"horse_totem": horse_totem,
	"barrow_mound": barrow_mound,
	"herd_bones": herd_bones,
	"eternal_forge": eternal_forge,
	"colossal_anvil": colossal_anvil,
	"pilgrim_brazier": pilgrim_brazier,
	"salamander_idol": salamander_idol,
	"salamander_den": salamander_den,
	"heretic_ruin": heretic_ruin,
	"magma_pool": magma_pool,
	"smoldering_tree": smoldering_tree,
	"smoldering_tree_b": smoldering_tree_b,
	"glowing_roots": glowing_roots,
	"charcoal_kiln": charcoal_kiln,
	"sootmask_totem": sootmask_totem,
	"sootmask_hut": sootmask_hut,
	"giant_fungus": giant_fungus,
	"moth_cocoon": moth_cocoon,
	"ember_treant_stump": ember_treant_stump,
	"rune_menhir": rune_menhir,
	"singing_altar": singing_altar,
	"singer_hut": singer_hut,
	"wyvern_nest": wyvern_nest,
	"crag_rock": crag_rock,
	"hag_hut": hag_hut,
	"hag_cauldron": hag_cauldron,
	"bog_totem": bog_totem,
	"wind_bent_tree": wind_bent_tree,
	"heather": heather,
	"floating_isle": floating_isle,
	"floating_isle_b": floating_isle_b,
	"floating_isle_c": floating_isle_c,
	"wind_rift": wind_rift,
	"tethered_isle": tethered_isle,
	"cloud_hall": cloud_hall,
	"cloud_pillar": cloud_pillar,
	"wrecked_skyship": wrecked_skyship,
	"serpent_roost": serpent_roost,
	"fallen_isle": fallen_isle,
	"summit_stair": summit_stair,
	"vayuketh_temple": vayuketh_temple,
	"guardian_statue": guardian_statue,
	"titan_throne": titan_throne,
	"drake_ledge": drake_ledge,
	"ysmoor_throne_hall": ysmoor_throne_hall,
	"fog_ruin_tower": fog_ruin_tower,
	"fog_ruin_wall": fog_ruin_wall,
	"gargoyle_perch": gargoyle_perch,
	"kennel_ruin": kennel_ruin,
	"dig_pit": dig_pit,
	"tombstone_cluster": tombstone_cluster,
	"fog_lantern": fog_lantern,
	"giant_ribcage": giant_ribcage,
	"elephant_skull": elephant_skull,
	"tusk_field": tusk_field,
	"poacher_wagon": poacher_wagon,
	"ivory_pile": ivory_pile,
	"vulture_perch": vulture_perch,
	"spirit_cairn": spirit_cairn,
	"bone_scatter": bone_scatter,
	"black_tree": black_tree,
	"black_tree_b": black_tree_b,
	"star_lily": star_lily,
	"glowcap_cluster": glowcap_cluster,
	"morvaine_manor": morvaine_manor,
	"morvaine_gate": morvaine_gate,
	"iron_fence": iron_fence,
	"shade_obelisk": shade_obelisk,
	"moon_well": moon_well,
	"stalker_den": stalker_den,
	"lampward_lamp": lampward_lamp,
	"barrowhold_gate": barrowhold_gate,
	"timiraj_shrine": timiraj_shrine,
	"black_sun": black_sun,
	"obsidian_tower": obsidian_tower,
	"observatory": observatory,
	"eclipse_house": eclipse_house,
	"moon_lamp": moon_lamp,
	"eclipse_wall": eclipse_wall,
	"petrified_giant": petrified_giant,
	"shattered_divine_blade": shattered_divine_blade,
	"divine_shield_fragment": divine_shield_fragment,
	"war_crater": war_crater,
	"godwar_banner": godwar_banner,
	"construct_husk": construct_husk,
	"relic_cart": relic_cart,
	"long_table": long_table,
	"table_throne": table_throne,
	"feast_brazier": feast_brazier,
	"star_pillar": star_pillar,
	"fallen_star": fallen_star,
	"hound_kennel_stones": hound_kennel_stones,
	"grove_dais_light": lambda: grove_dais("light"),
	"grove_dais_water": lambda: grove_dais("water"),
	"grove_dais_fire": lambda: grove_dais("fire"),
	"grove_dais_wind": lambda: grove_dais("wind"),
	"grove_dais_dark": lambda: grove_dais("dark"),
	"grove_tree_a": grove_tree_a,
	"grove_tree_b": grove_tree_b,
	"lotus_pad": lotus_pad,
	"lotus_bloom": lotus_bloom,
	"tusk_arch": tusk_arch,
	"grove_stepping_stone": grove_stepping_stone,
	"murk_longhouse": murk_longhouse,
	"murk_hut": murk_hut,
	"bone_palisade": bone_palisade,
	"bone_gate": bone_gate,
	"bog_lantern": bog_lantern,
	"murk_cauldron": murk_cauldron,
	"cavern_dome": cavern_dome,
	"dusk_spire": dusk_spire,
	"dusk_house": dusk_house,
	"dusk_bridge": dusk_bridge,
	"stalagmite_cluster": stalagmite_cluster,
	"glow_crystal": glow_crystal,
	"candle_stand": candle_stand,
	"dusk_gate": dusk_gate,
	"dusk_tree": dusk_tree,
	"dusk_tree_b": dusk_tree_b,
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


if __name__ == "__main__":  # gear.py imports the helpers above without building props
	main()
