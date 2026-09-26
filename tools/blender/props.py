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
	# the porch: posts at the front edge up to the roof, and a low rail with a gap
	n_posts = max(2, int(round(w / 3.0)) + 1)
	px = [-hw + 0.2 + k * (w - 0.4) / (n_posts - 1) for k in range(n_posts)]
	for x in px:
		p.seg((x, -hd + 0.2, 0), (x, -hd + 0.2, roof_z(x, -hd + 0.2) - 0.05), 0.12, 0.11, WOOD, sides=6, grad=(0.2, 1.0))
	for a, b in zip(px, px[1:]):
		if a < 0 < b or abs((a + b) / 2) < 1.2:
			continue
		p.box((b - a, 0.1, 0.1), ((a + b) / 2, -hd + 0.2, 0.85), WOOD_GRAY, grad=(0.2, 0.8))
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
