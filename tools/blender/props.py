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
	p.box((1.5, 0.08, 0.34), (0.55, -0.06, 2.25), WOOD_GRAY, grad=(0.1, 0.6))
	p.seg((1.3, -0.06, 2.25), (1.55, -0.06, 2.25), 0.2, 0.0, WOOD_GRAY, sides=4, twist=45)
	p.box((1.3, 0.08, 0.32), (-0.45, 0.06, 1.75), WOOD_GRAY, grad=(0.1, 0.6))
	p.seg((-1.1, 0.06, 1.75), (-1.35, 0.06, 1.75), 0.19, 0.0, WOOD_GRAY, sides=4, twist=45)
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
	up +Z) in KayKit character units, which the game shows at 0.75 scale."""
	p = Prop("fishing_pole", 77)
	p.seg((0, 0, -0.35), (0, 0, 0.3), 0.045, 0.04, HIDE, sides=6, grad=(0.2, 0.9))  # cork grip
	p.seg((0, 0, 0.3), (0, 0, 2.9), 0.03, 0.008, WOOD, sides=5, grad=(0.1, 0.8))
	p.seg((-0.06, 0, 0.42), (0.06, 0, 0.42), 0.09, 0.09, IRON, sides=8)  # reel
	p.seg((0, 0, 0.42), (0.1, 0, 0.42), 0.012, 0.012, IRON, sides=4)
	for z in (0.9, 1.6, 2.3):
		p.seg((0, 0, z), (0.05, 0, z), 0.012, 0.012, IRON, sides=4)
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
