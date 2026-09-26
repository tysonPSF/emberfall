"""Builds Emberfall's creature models (rigged, animated, low-poly) and exports GLBs.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/creatures.py -- --out assets/creatures [--preview DIR] [--only rat,bog_leech]

Each creature is primitives rigidly skinned to a few bones. Clips are named after
the game's actions (idle, walk, run, attack, hit, death) so CharacterModel can use
them directly (`"rig": "own"` in data/models.json). Creatures face -Y in Blender,
which exports as glTF +Z like the KayKit characters.

Bone axes: every bone points forward (-Y) with its Z up, so a pose rotation of
(pitch, roll, yaw) in degrees means: +pitch raises what's in front of the pivot,
roll tips around the forward axis, yaw turns around vertical. Pose location
(x, y, z): y is forward, z is up.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

FPS = 30


# ---------------------------------------------------------------- scene helpers

def reset_scene():
	bpy.ops.wm.read_factory_settings(use_empty=True)
	bpy.context.scene.render.fps = FPS


def material(name, color, rough=0.8, emit=0.0):
	m = bpy.data.materials.new(name)
	m.use_nodes = True
	bsdf = m.node_tree.nodes["Principled BSDF"]
	rgba = tuple(int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)
	# hex colors are sRGB; Blender wants linear
	lin = tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgba[:3]) + (1.0,)
	bsdf.inputs["Base Color"].default_value = lin
	bsdf.inputs["Roughness"].default_value = rough
	if emit > 0.0:
		bsdf.inputs["Emission Color"].default_value = lin
		bsdf.inputs["Emission Strength"].default_value = emit
	m.diffuse_color = rgba  # workbench preview
	return m


class Builder:
	"""Collects mesh parts, each rigidly bound to one bone."""

	def __init__(self, name):
		self.name = name
		self.parts = []
		self.bones = []  # (name, head, parent)

	def bone(self, name, head, parent=None):
		self.bones.append((name, Vector(head), parent))

	def _add(self, bm, mat, bone):
		mesh = bpy.data.meshes.new(f"{self.name}_part")
		bm.to_mesh(mesh)
		bm.free()
		obj = bpy.data.objects.new(mesh.name, mesh)
		bpy.context.collection.objects.link(obj)
		obj.data.materials.append(mat)
		vg = obj.vertex_groups.new(name=bone)
		vg.add(range(len(mesh.vertices)), 1.0, "REPLACE")
		self.parts.append(obj)

	def blob(self, size, loc, mat, bone, rot=(0, 0, 0), segs=(10, 7)):
		"""Ellipsoid with the given full extents."""
		bm = bmesh.new()
		bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=0.5)
		m = Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot]), Vector(size))
		bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
		self._add(bm, mat, bone)

	def seg(self, a, b, r1, r2, mat, bone, sides=6):
		"""Tapered cylinder from point a to point b."""
		a, b = Vector(a), Vector(b)
		d = b - a
		bm = bmesh.new()
		bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r1, radius2=r2, depth=d.length)
		q = Vector((0, 0, 1)).rotation_difference(d.normalized())
		m = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
		bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
		self._add(bm, mat, bone)

	def build(self):
		arm_data = bpy.data.armatures.new(f"{self.name}_rig")
		arm = bpy.data.objects.new(self.name, arm_data)
		bpy.context.collection.objects.link(arm)
		bpy.context.view_layer.objects.active = arm
		bpy.ops.object.mode_set(mode="EDIT")
		for name, head, parent in self.bones:
			eb = arm_data.edit_bones.new(name)
			eb.head = head
			eb.tail = head + Vector((0, -0.1, 0))
			eb.align_roll((0, 0, 1))
			if parent:
				eb.parent = arm_data.edit_bones[parent]
		bpy.ops.object.mode_set(mode="OBJECT")
		for pb in arm.pose.bones:
			pb.rotation_mode = "XYZ"

		bpy.ops.object.select_all(action="DESELECT")
		for p in self.parts:
			p.select_set(True)
		bpy.context.view_layer.objects.active = self.parts[0]
		bpy.ops.object.join()
		body = self.parts[0]
		body.name = f"{self.name}_mesh"
		body.parent = arm
		mod = body.modifiers.new("Armature", "ARMATURE")
		mod.object = arm
		arm.animation_data_create()
		return arm

	def build_static(self):
		"""Joins the parts into one unrigged mesh (for bone attachments)."""
		bpy.ops.object.select_all(action="DESELECT")
		for p in self.parts:
			p.select_set(True)
		bpy.context.view_layer.objects.active = self.parts[0]
		bpy.ops.object.join()
		obj = self.parts[0]
		obj.name = self.name
		obj.vertex_groups.clear()
		return obj


# ---------------------------------------------------------------- animation helpers

def smooth(a, b, x):
	x = max(0.0, min(1.0, x))
	x = x * x * (3 - 2 * x)
	return a + (b - a) * x


def seq(t, points):
	"""Smoothstep through [(t, value)...]; values are numbers or tuples."""
	if t <= points[0][0]:
		return points[0][1]
	for (t0, v0), (t1, v1) in zip(points, points[1:]):
		if t <= t1:
			x = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
			if isinstance(v0, tuple):
				return tuple(smooth(p, q, x) for p, q in zip(v0, v1))
			return smooth(v0, v1, x)
	return points[-1][1]


def wave(t, cycles=1.0, phase=0.0):
	return math.sin(2 * math.pi * (t * cycles + phase))


def clip(arm, name, seconds, pose_fn, loop):
	"""Samples pose_fn(t in [0,1]) -> {bone: {"rot": (p, r, y), "loc": (x, y, z)}} into an action."""
	act = bpy.data.actions.new(name)
	act.use_fake_user = True
	arm.animation_data.action = act
	frames = max(2, round(seconds * FPS))
	for f in range(frames + 1):
		t = f / frames
		if loop and f == frames:
			t = 0.0
		pose = pose_fn(t)
		for pb in arm.pose.bones:
			p = pose.get(pb.name, {})
			pitch, roll, yaw = p.get("rot", (0, 0, 0))
			# bone local axes are X = -world X, Y = forward, Z = up, so +X rotation = +pitch
			pb.rotation_euler = (math.radians(pitch), math.radians(roll), math.radians(yaw))
			pb.location = p.get("loc", (0, 0, 0))
			pb.keyframe_insert("rotation_euler", frame=f + 1)
			pb.keyframe_insert("location", frame=f + 1)
	for fc in _fcurves(act):
		for kp in fc.keyframe_points:
			kp.interpolation = "LINEAR"
	return act


def _fcurves(act):
	if hasattr(act, "fcurves") and len(act.fcurves):
		return list(act.fcurves)
	out = []
	for layer in getattr(act, "layers", []):
		for strip in layer.strips:
			for bag in strip.channelbags:
				out.extend(bag.fcurves)
	return out


def merge(*poses):
	out = {}
	for p in poses:
		for bone, v in p.items():
			cur = out.setdefault(bone, {"rot": (0, 0, 0), "loc": (0, 0, 0)})
			for k in ("rot", "loc"):
				if k in v:
					cur[k] = tuple(a + b for a, b in zip(cur[k], v[k]))
	return out


# ---------------------------------------------------------------- rat

RAT_LEGS = {"leg_fl": (0.2, -0.3), "leg_fr": (-0.2, -0.3), "leg_bl": (0.21, 0.36), "leg_br": (-0.21, 0.36)}


def build_rat():
	fur = material("rat_fur", "6b5a4e")
	belly = material("rat_belly", "a8927c")
	pink = material("rat_pink", "d99a94", 0.6)
	eye = material("rat_eye", "141010", 0.2)
	b = Builder("rat")
	b.bone("root", (0, 0, 0.42))
	b.bone("body", (0, 0.05, 0.42), "root")
	b.bone("head", (0, -0.45, 0.5), "body")
	b.bone("tail1", (0, 0.6, 0.36), "body")
	b.bone("tail2", (0, 0.92, 0.3), "tail1")
	b.bone("tail3", (0, 1.22, 0.24), "tail2")

	b.blob((0.64, 1.15, 0.56), (0, 0.06, 0.43), fur, "body")
	b.blob((0.5, 0.9, 0.34), (0, 0.02, 0.3), belly, "body")
	b.blob((0.36, 0.5, 0.42), (0.19, 0.38, 0.36), fur, "body")   # haunches
	b.blob((0.36, 0.5, 0.42), (-0.19, 0.38, 0.36), fur, "body")
	b.blob((0.44, 0.46, 0.4), (0, -0.52, 0.52), fur, "head")
	b.seg((0, -0.6, 0.5), (0, -0.98, 0.45), 0.19, 0.05, fur, "head", sides=7)
	b.blob((0.1, 0.1, 0.09), (0, -0.99, 0.46), pink, "head")    # nose
	for s in (1, -1):
		b.blob((0.09, 0.08, 0.1), (0.14 * s, -0.7, 0.6), eye, "head")
		b.blob((0.22, 0.07, 0.24), (0.17 * s, -0.46, 0.76), fur, "head", rot=(0, 25 * s, 0))
		b.blob((0.15, 0.05, 0.17), (0.17 * s, -0.49, 0.76), pink, "head", rot=(0, 25 * s, 0))
	b.seg((0, 0.56, 0.37), (0, 0.94, 0.3), 0.07, 0.05, pink, "tail1")
	b.seg((0, 0.92, 0.3), (0, 1.24, 0.24), 0.05, 0.035, pink, "tail2")
	b.seg((0, 1.22, 0.24), (0, 1.55, 0.2), 0.035, 0.01, pink, "tail3")
	for name, (x, y) in RAT_LEGS.items():
		b.bone(name, (x, y, 0.3), "root")
		b.seg((x, y, 0.32), (x, y, 0.05), 0.075, 0.06, fur, name)
		b.blob((0.13, 0.18, 0.07), (x, y - 0.04, 0.035), pink, name)
	arm = b.build()

	def legs(fl, fr, bl, br):
		return {"leg_fl": {"rot": (fl, 0, 0)}, "leg_fr": {"rot": (fr, 0, 0)},
				"leg_bl": {"rot": (bl, 0, 0)}, "leg_br": {"rot": (br, 0, 0)}}

	def tail(t, amp, cycles=1.0):
		return {f"tail{i}": {"rot": (-4, 0, amp * wave(t, cycles, -0.12 * i))} for i in (1, 2, 3)}

	def idle(t):
		return merge(
			{"body": {"loc": (0, 0, 0.012 * wave(t))},
			 "head": {"rot": (4 * wave(t, 4) + 3, 0, 10 * wave(t, 1, 0.25))}},
			tail(t, 14))

	def walk(t):
		a = 28 * wave(t)
		return merge(legs(a, -a, -a, a), tail(t, 10),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t)))}, "head": {"rot": (3 * wave(t, 2), 0, 0)}})

	def run(t):
		f, k = 45 * wave(t), 45 * wave(t, 1, 0.5)
		return merge(legs(f, f * 0.85, k, k * 0.85), tail(t, 6),
					 {"root": {"loc": (0, 0, 0.06 * max(0, wave(t, 1, 0.25))), "rot": (7 * wave(t, 1, 0.1), 0, 0)}})

	def attack(t):
		lunge = seq(t, [(0, 0), (0.3, -0.1), (0.5, 0.28), (1, 0)])
		head = seq(t, [(0, 0), (0.3, 22), (0.5, -18), (1, 0)])
		pitch = seq(t, [(0, 0), (0.3, 10), (0.5, -6), (1, 0)])
		hind = seq(t, [(0, 0), (0.3, 15), (0.5, -25), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0), "rot": (pitch, 0, 0)}, "head": {"rot": (head, 0, 0)}},
					 legs(-hind * 0.6, -hind * 0.6, hind, hind), tail(t, 20, 1.5))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, 0.03 * k), "rot": (12 * k, 0, 0)},
					  "head": {"rot": (18 * k, 0, 0)}}, tail(t, 25 * k, 2))

	def death(t):
		rear = seq(t, [(0, 0), (0.25, 18), (0.6, 0)])
		roll = seq(t, [(0.2, 0), (0.65, 88), (0.78, 82), (0.9, 90)])
		drop = seq(t, [(0.2, 0), (0.65, -0.12)])
		curl = seq(t, [(0.3, 0), (0.8, 1)])
		twitch = 6 * wave(t, 5) * seq(t, [(0.6, 0), (0.75, 1), (1, 0)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (rear, roll, 0)},
					  "head": {"rot": (-10 * curl, 0, 15 * curl)}},
					 legs(35 * curl + twitch, 20 * curl, -30 * curl - twitch, -15 * curl),
					 {f"tail{i}": {"rot": (0, 0, 20 * curl)} for i in (1, 2, 3)})

	clip(arm, "idle", 2.0, idle, True)
	clip(arm, "walk", 0.8, walk, True)
	clip(arm, "run", 0.45, run, True)
	clip(arm, "attack", 0.6, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.1, death, False)
	return arm


# ---------------------------------------------------------------- fire beetle

BEETLE_LEGS = {}
for _i, _y in enumerate((-0.42, 0.02, 0.44)):
	BEETLE_LEGS[f"leg_l{_i + 1}"] = (0.42, _y)
	BEETLE_LEGS[f"leg_r{_i + 1}"] = (-0.42, _y)
TRIPOD_A = ("leg_l1", "leg_r2", "leg_l3")


def build_beetle():
	shell = material("beetle_shell", "c0442a", 0.35)
	thorax = material("beetle_thorax", "8e2a1a", 0.45)
	dark = material("beetle_dark", "2e1c18", 0.7)
	glow = material("beetle_eye", "ffae2a", 0.3, emit=4.0)
	b = Builder("fire_beetle")
	b.bone("root", (0, 0, 0.45))
	b.bone("body", (0, 0.05, 0.45), "root")
	b.bone("head", (0, -0.8, 0.45), "body")
	b.bone("mand_l", (0.12, -1.08, 0.33), "head")
	b.bone("mand_r", (-0.12, -1.08, 0.33), "head")

	b.blob((1.0, 1.35, 0.34), (0, 0.12, 0.3), dark, "body", segs=(12, 6))           # underside
	for s in (1, -1):                                                              # wing cases
		b.blob((0.6, 1.5, 0.74), (0.26 * s, 0.14, 0.5), shell, "body", rot=(0, -4 * s, 0), segs=(12, 8))
	b.blob((0.84, 0.52, 0.52), (0, -0.62, 0.48), thorax, "body", segs=(12, 7))
	b.blob((0.56, 0.42, 0.4), (0, -0.95, 0.42), dark, "head")
	for s in (1, -1):
		b.blob((0.18, 0.16, 0.18), (0.21 * s, -1.06, 0.5), glow, "head", segs=(8, 6))
		b.seg((0.14 * s, -1.08, 0.58), (0.36 * s, -1.4, 0.9), 0.025, 0.012, dark, "head", sides=4)
		side = "mand_l" if s > 0 else "mand_r"
		b.seg((0.12 * s, -1.06, 0.33), (0.05 * s, -1.34, 0.3), 0.06, 0.012, dark, side, sides=5)

	for name, (x, y) in BEETLE_LEGS.items():
		s = 1 if x > 0 else -1
		b.bone(name, (x, y, 0.36), "root")
		knee = (x + 0.36 * s, y, 0.46)
		foot = (x + 0.62 * s, y + 0.06 * (y / 0.44 if y else 0), 0.0)
		b.seg((x, y, 0.36), knee, 0.09, 0.07, dark, name, sides=5)
		b.blob((0.13, 0.13, 0.13), knee, dark, name, segs=(6, 4))
		b.seg(knee, foot, 0.07, 0.03, dark, name, sides=5)
	arm = b.build()

	def leg(name, swing, lift):
		s = 1 if BEETLE_LEGS[name][0] > 0 else -1
		return {name: {"rot": (0, lift * s, -swing * s)}}

	def mandibles(open_deg):
		return {"mand_l": {"rot": (0, 0, open_deg)}, "mand_r": {"rot": (0, 0, -open_deg)}}

	def gait(t, amp, lift):
		out = {}
		for name in BEETLE_LEGS:
			ph = 0.0 if name in TRIPOD_A else 0.5
			swing = amp * wave(t, 1, ph)
			up = lift * max(0.0, wave(t, 1, ph + 0.25))  # lifted while swinging forward
			out.update(leg(name, swing, up))
		return out

	def idle(t):
		chew = 12 * max(0.0, wave(t, 2))
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t))}, "head": {"rot": (0, 0, 5 * wave(t, 1, 0.3))}},
					 mandibles(chew), gait(t, 3, 0))

	def walk(t):
		return merge(gait(t, 20, 16), {"root": {"loc": (0, 0, 0.015 * abs(wave(t, 2)))},
									   "body": {"rot": (0, 2 * wave(t), 0)}}, mandibles(4))

	def run(t):
		return merge(gait(t, 28, 22), {"root": {"loc": (0, 0, 0.03 * abs(wave(t, 2)))},
									   "body": {"rot": (0, 3 * wave(t), 0)}})

	def attack(t):
		lunge = seq(t, [(0, 0), (0.35, -0.12), (0.55, 0.3), (1, 0)])
		pitch = seq(t, [(0, 0), (0.35, 12), (0.55, -8), (1, 0)])
		jaw = seq(t, [(0, 0), (0.35, 32), (0.55, -8), (0.75, 0)])
		brace = seq(t, [(0, 0), (0.35, 1), (0.55, -1), (1, 0)])
		out = merge({"root": {"loc": (0, lunge, 0), "rot": (pitch, 0, 0)}}, mandibles(jaw))
		for name in BEETLE_LEGS:
			out = merge(out, leg(name, 12 * brace, 0))
		return out

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		out = {"root": {"loc": (0, -0.14 * k, 0.04 * k), "rot": (10 * k, 6 * k, 0)}}
		return merge(out, mandibles(20 * k), gait(t, 10 * k, 10 * k))

	def death(t):
		roll = seq(t, [(0.1, 0), (0.55, 100), (0.7, 175), (0.8, 180)])
		lift = seq(t, [(0.1, 0), (0.45, 0.3), (0.8, -0.02)])
		curl = seq(t, [(0.35, 0), (0.85, 1)])
		twitch = seq(t, [(0.7, 0), (0.8, 1), (1, 0.2)])
		out = merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)}}, mandibles(25 * curl))
		for i, name in enumerate(BEETLE_LEGS):
			out = merge(out, leg(name, 10 * twitch * wave(t, 6, i * 0.17), -60 * curl))  # fold under the belly
		return out

	clip(arm, "idle", 2.0, idle, True)
	clip(arm, "walk", 0.9, walk, True)
	clip(arm, "run", 0.5, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


# ---------------------------------------------------------------- wolf

def _quad_legs(t_wave, amp):
	"""Diagonal pairs (trot): front-left with back-right."""
	a = amp * t_wave
	return {"leg_fl": {"rot": (a, 0, 0)}, "leg_br": {"rot": (a, 0, 0)},
			"leg_fr": {"rot": (-a, 0, 0)}, "leg_bl": {"rot": (-a, 0, 0)}}


def build_wolf(name="wolf", fur_hex="6f6a63", back_hex="4a4642", belly_hex="b8ae9f", eye_hex="e8c040"):
	fur = material(f"{name}_fur", fur_hex, 0.9)
	back = material(f"{name}_back", back_hex, 0.95)
	belly = material(f"{name}_belly", belly_hex, 0.9)
	dark = material(f"{name}_dark", "1c1a19", 0.5)
	eye = material(f"{name}_eye", eye_hex, 0.3, emit=1.2)
	b = Builder(name)
	legs = {"leg_fl": (0.2, -0.52), "leg_fr": (-0.2, -0.52), "leg_bl": (0.2, 0.46), "leg_br": (-0.2, 0.46)}
	b.bone("root", (0, 0, 0.72))
	b.bone("body", (0, 0.0, 0.78), "root")
	b.bone("head", (0, -0.78, 0.98), "body")
	b.bone("jaw", (0, -0.95, 0.9), "head")
	b.bone("tail1", (0, 0.72, 0.86), "body")
	b.bone("tail2", (0, 1.05, 0.72), "tail1")

	b.blob((0.62, 1.5, 0.62), (0, 0.0, 0.8), fur, "body", segs=(12, 8))
	b.blob((0.5, 1.2, 0.3), (0, 0.02, 0.62), belly, "body")
	b.blob((0.44, 1.1, 0.26), (0, 0.02, 1.07), back, "body")                           # darker saddle
	b.blob((0.74, 0.6, 0.72), (0, -0.52, 0.9), fur, "body", segs=(10, 8))            # ruff
	b.blob((0.46, 0.5, 0.44), (0, -0.84, 1.02), fur, "head")                          # skull
	b.seg((0, -0.95, 0.99), (0, -1.36, 0.9), 0.16, 0.08, fur, "head", sides=8)       # muzzle
	b.blob((0.1, 0.09, 0.08), (0, -1.38, 0.93), dark, "head")                         # nose
	b.seg((0, -0.95, 0.88), (0, -1.3, 0.82), 0.1, 0.05, belly, "jaw", sides=6)        # lower jaw
	for s in (1, -1):
		b.blob((0.08, 0.06, 0.06), (0.13 * s, -1.03, 1.1), eye, "head", segs=(6, 4))
		b.seg((0.15 * s, -0.78, 1.2), (0.19 * s, -0.74, 1.46), 0.09, 0.01, back, "head", sides=4)  # ears
		b.seg((0.06 * s, -1.24, 0.84), (0.06 * s, -1.25, 0.77), 0.02, 0.004, material(f"{name}_tooth", "efe6d0"), "jaw", sides=4)
	b.seg((0, 0.72, 0.9), (0, 1.1, 0.72), 0.11, 0.13, fur, "tail1", sides=7)
	b.blob((0.24, 0.5, 0.24), (0, 1.3, 0.56), back, "tail2")
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.66), "root")
		b.seg((x, y, 0.7), (x, y + 0.03, 0.3), 0.09, 0.07, fur, name_, sides=6)
		b.seg((x, y + 0.03, 0.3), (x, y - 0.02, 0.06), 0.065, 0.055, back, name_, sides=6)
		b.blob((0.13, 0.17, 0.08), (x, y - 0.05, 0.04), dark, name_)
	arm = b.build()

	def tail(t, amp):
		return {"tail1": {"rot": (4 * wave(t, 1, 0.2), 0, amp * wave(t))}, "tail2": {"rot": (0, 0, amp * wave(t, 1, -0.15))}}

	def idle(t):
		return merge({"body": {"loc": (0, 0, 0.012 * wave(t, 2))}, "head": {"rot": (4 * wave(t, 1, 0.3), 0, 8 * wave(t, 0.5))}},
					 tail(t, 8))

	def walk(t):
		return merge(_quad_legs(wave(t), 26), tail(t, 10), {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))},
															   "head": {"rot": (3 * wave(t, 2), 0, 0)}})

	def run(t):  # a bounding gallop: fronts together, backs together
		f, k = 42 * wave(t), 42 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.08 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)}},
					 tail(t, 5))

	def attack(t):
		lunge = seq(t, [(0, 0), (0.3, -0.12), (0.5, 0.35), (1, 0)])
		head = seq(t, [(0, 0), (0.3, 18), (0.5, -14), (1, 0)])
		jaw = seq(t, [(0, 0), (0.3, -30), (0.5, 4), (0.7, 0)])
		return merge({"root": {"loc": (0, lunge, 0.05 * max(0.0, lunge)), "rot": (seq(t, [(0, 0), (0.3, 8), (0.5, -8), (1, 0)]), 0, 0)},
					  "head": {"rot": (head, 0, 0)}, "jaw": {"rot": (jaw, 0, 0)}}, tail(t, 16))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.16 * k, 0.03 * k), "rot": (10 * k, 0, 0)}, "head": {"rot": (16 * k, 0, 10 * k)},
					  "jaw": {"rot": (-20 * k, 0, 0)}}, tail(t, 20 * k))

	def death(t):
		roll = seq(t, [(0.15, 0), (0.6, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.15, 0), (0.6, -0.34)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (-12 * curl, 0, 12 * curl)}, "jaw": {"rot": (-14 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (28 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
					  "leg_bl": {"rot": (-24 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					 {"tail1": {"rot": (-10 * curl, 0, 0)}})

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 0.8, walk, True)
	clip(arm, "run", 0.45, run, True)
	clip(arm, "attack", 0.6, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.1, death, False)
	return arm


def build_dire_wolf():
	return build_wolf("dire_wolf", "403c39", "26221f", "7a7068", "ff6a2a")


# ---------------------------------------------------------------- black bear

def build_bear():
	fur = material("bear_fur", "2f2622", 0.95)
	dark = material("bear_dark", "1a1513", 0.9)
	muzzle = material("bear_muzzle", "8a6a4e", 0.9)
	claw = material("bear_claw", "d8cfbc", 0.5)
	eye = material("bear_eye", "120c0a", 0.2)
	b = Builder("bear")
	legs = {"leg_fl": (0.36, -0.62), "leg_fr": (-0.36, -0.62), "leg_bl": (0.36, 0.62), "leg_br": (-0.36, 0.62)}
	b.bone("root", (0, 0, 0.85))
	b.bone("body", (0, 0.0, 0.95), "root")
	b.bone("head", (0, -1.05, 1.15), "body")
	b.blob((1.2, 2.1, 1.15), (0, 0.05, 1.0), fur, "body", segs=(14, 9))
	b.blob((1.25, 0.9, 1.1), (0, -0.55, 1.15), fur, "body", segs=(12, 8))         # shoulder hump
	b.blob((0.9, 0.9, 0.9), (0, 0.72, 0.95), fur, "body", segs=(12, 8))           # rump
	b.blob((0.66, 0.66, 0.62), (0, -1.12, 1.2), fur, "head", segs=(12, 8))
	b.seg((0, -1.3, 1.14), (0, -1.62, 1.06), 0.2, 0.13, muzzle, "head", sides=8)
	b.blob((0.16, 0.12, 0.12), (0, -1.64, 1.11), dark, "head")
	for s in (1, -1):
		b.blob((0.2, 0.12, 0.2), (0.25 * s, -1.05, 1.5), fur, "head", segs=(8, 6))   # round ears
		b.blob((0.07, 0.06, 0.07), (0.16 * s, -1.4, 1.28), eye, "head", segs=(6, 4))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.8), "root")
		b.seg((x, y, 0.85), (x, y, 0.1), 0.2, 0.16, fur, name_, sides=8)
		b.blob((0.3, 0.36, 0.14), (x, y - 0.06, 0.07), dark, name_)
		for k in (-1, 0, 1):
			b.seg((x + 0.08 * k, y - 0.22, 0.06), (x + 0.08 * k, y - 0.3, 0.02), 0.025, 0.008, claw, name_, sides=4)
	arm = b.build()

	def idle(t):
		return {"body": {"loc": (0, 0, 0.015 * wave(t))}, "head": {"rot": (-3 + 5 * wave(t, 1, 0.25), 0, 10 * wave(t, 0.5))}}

	def walk(t):  # a heavy, rolling amble
		return merge(_quad_legs(wave(t), 20), {"body": {"rot": (0, 4 * wave(t), 0)}, "root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))},
											   "head": {"rot": (4 * wave(t, 2), 0, 3 * wave(t))}})

	def run(t):
		f, k = 34 * wave(t), 34 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.07 * max(0.0, wave(t, 1, 0.25))), "rot": (5 * wave(t, 1, 0.1), 0, 0)}})

	def attack(t):  # rear up and swipe down with both forepaws
		rear = seq(t, [(0, 0), (0.35, 38), (0.55, -6), (1, 0)])
		paws = seq(t, [(0, 0), (0.35, 70), (0.55, -30), (1, 0)])
		return {"root": {"rot": (rear, 0, 0), "loc": (0, seq(t, [(0, 0), (0.35, 0.2), (0.55, -0.15), (1, 0)]), 0)},
				"leg_fl": {"rot": (paws, 0, 0)}, "leg_fr": {"rot": (paws * 0.9, 0, 0)},
				"leg_bl": {"rot": (-rear, 0, 0)}, "leg_br": {"rot": (-rear, 0, 0)},
				"head": {"rot": (seq(t, [(0, 0), (0.35, -20), (0.55, 10), (1, 0)]), 0, 0)}}

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return {"root": {"loc": (0, -0.12 * k, 0), "rot": (6 * k, 4 * k, 0)}, "head": {"rot": (14 * k, 0, -12 * k)}}

	def death(t):
		roll = seq(t, [(0.2, 0), (0.7, 84), (0.8, 80), (0.9, 86)])
		drop = seq(t, [(0.2, 0), (0.7, -0.42)])
		curl = seq(t, [(0.35, 0), (0.9, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (0, roll, 0)}, "head": {"rot": (-10 * curl, 0, 16 * curl)}},
					 {"leg_fl": {"rot": (22 * curl, 0, 0)}, "leg_fr": {"rot": (12 * curl, 0, 0)},
					  "leg_bl": {"rot": (-18 * curl, 0, 0)}, "leg_br": {"rot": (-8 * curl, 0, 0)}})

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 1.1, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.9, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- thornback spider

SPIDER_LEGS = {}
for _i, _y in enumerate((-0.42, -0.24, -0.06, 0.12)):
	SPIDER_LEGS[f"leg_l{_i + 1}"] = (0.26, _y)
	SPIDER_LEGS[f"leg_r{_i + 1}"] = (-0.26, _y)
SPIDER_SET_A = ("leg_l1", "leg_r2", "leg_l3", "leg_r4")


def build_spider():
	shell = material("spider_shell", "2e2724", 0.55)
	mark = material("spider_mark", "9a3424", 0.5)
	thorn = material("spider_thorn", "c9b58e", 0.5)
	leg_m = material("spider_leg", "231d1b", 0.6)
	glow = material("spider_eye", "ff3a22", 0.3, emit=3.0)
	b = Builder("spider")
	b.bone("root", (0, 0, 0.55))
	b.bone("body", (0, -0.15, 0.55), "root")
	b.bone("abdomen", (0, 0.25, 0.62), "body")
	b.bone("fang_l", (0.08, -0.62, 0.48), "body")
	b.bone("fang_r", (-0.08, -0.62, 0.48), "body")
	b.blob((0.7, 0.78, 0.46), (0, -0.2, 0.55), shell, "body", segs=(12, 8))              # cephalothorax
	b.blob((1.1, 1.25, 0.95), (0, 0.72, 0.78), shell, "abdomen", segs=(14, 10))          # abdomen
	b.blob((0.5, 0.7, 0.2), (0, 0.72, 1.2), mark, "abdomen", rot=(-10, 0, 0), segs=(10, 6))  # the red mark
	for k, (x, y, z) in enumerate(((0.28, 0.45, 1.12), (-0.28, 0.45, 1.12), (0.4, 0.8, 1.05), (-0.4, 0.8, 1.05), (0.0, 1.0, 1.2), (0.0, 0.55, 1.26))):
		b.seg((x, y, z - 0.05), (x * 1.3, y + 0.05, z + 0.28), 0.07, 0.0, thorn, "abdomen", sides=4)   # thorns
	for s in (1, -1):
		for ex, ez in ((0.1, 0.72), (0.2, 0.68), (0.06, 0.64)):
			b.blob((0.07, 0.06, 0.07), (ex * s, -0.55, ez), glow, "body", segs=(6, 4))
		side = "fang_l" if s > 0 else "fang_r"
		b.seg((0.08 * s, -0.58, 0.48), (0.06 * s, -0.7, 0.26), 0.06, 0.012, leg_m, side, sides=5)
	for name_, (x, y) in SPIDER_LEGS.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, 0.55), "body")
		spread = (y + 0.15) * 1.6
		knee = (x + 0.55 * s, y + spread * 0.5, 0.95)
		foot = (x + 1.05 * s, y + spread, 0.0)
		b.seg((x, y, 0.55), knee, 0.06, 0.05, leg_m, name_, sides=5)
		b.blob((0.1, 0.1, 0.1), knee, mark, name_, segs=(6, 4))
		b.seg(knee, foot, 0.05, 0.015, leg_m, name_, sides=5)
	arm = b.build()

	def leg(name_, swing, lift):
		s = 1 if SPIDER_LEGS[name_][0] > 0 else -1
		return {name_: {"rot": (0, lift * s, -swing * s)}}

	def fangs(open_deg):
		return {"fang_l": {"rot": (0, 0, open_deg)}, "fang_r": {"rot": (0, 0, -open_deg)}}

	def gait(t, amp, lift):
		out = {}
		for name_ in SPIDER_LEGS:
			ph = 0.0 if name_ in SPIDER_SET_A else 0.5
			out.update(leg(name_, amp * wave(t, 1, ph), lift * max(0.0, wave(t, 1, ph + 0.25))))
		return out

	def idle(t):
		return merge({"body": {"loc": (0, 0, 0.012 * wave(t))}, "abdomen": {"rot": (3 * wave(t, 1, 0.2), 0, 0)}},
					 fangs(6 * max(0.0, wave(t, 2))), gait(t, 2, 0))

	def walk(t):
		return merge(gait(t, 18, 14), {"root": {"loc": (0, 0, 0.015 * abs(wave(t, 2)))}, "abdomen": {"rot": (0, 0, 3 * wave(t))}})

	def run(t):
		return merge(gait(t, 26, 20), {"root": {"loc": (0, 0, 0.03 * abs(wave(t, 2)))}, "abdomen": {"rot": (0, 0, 4 * wave(t))}})

	def attack(t):  # rear the front legs, then strike down with the fangs
		rear = seq(t, [(0, 0), (0.35, 1), (0.55, -0.4), (1, 0)])
		out = merge({"root": {"rot": (14 * rear, 0, 0), "loc": (0, seq(t, [(0, 0), (0.35, -0.1), (0.55, 0.25), (1, 0)]), 0)}},
					fangs(seq(t, [(0, 0), (0.35, 28), (0.55, -10), (1, 0)])))
		for name_ in ("leg_l1", "leg_r1"):
			out = merge(out, leg(name_, 0, 45 * rear))
		return out

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.04 * k), "rot": (8 * k, 5 * k, 0)}}, fangs(18 * k), gait(t, 8 * k, 12 * k))

	def death(t):  # legs curl up underneath, as spiders do
		drop = seq(t, [(0.1, 0), (0.6, -0.3)])
		curl = seq(t, [(0.2, 0), (0.8, 1)])
		out = merge({"root": {"loc": (0, 0, drop), "rot": (0, seq(t, [(0.3, 0), (0.7, 18)]), 0)}}, fangs(20 * curl))
		for i, name_ in enumerate(SPIDER_LEGS):
			out = merge(out, leg(name_, 4 * wave(t, 5, i * 0.13) * (1 - curl), -65 * curl))  # folded under
		return out

	clip(arm, "idle", 2.0, idle, True)
	clip(arm, "walk", 0.7, walk, True)
	clip(arm, "run", 0.42, run, True)
	clip(arm, "attack", 0.65, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.2, death, False)
	return arm


# ---------------------------------------------------------------- export + preview

# ---------------------------------------------------------------- gnoll parts
# Bolt-ons for KayKit Rig_Medium bodies (see "attach" in data/models.json). They
# are authored in the KayKit mesh space (feet at the origin, head bone at z 1.24,
# chibi head about 1 unit wide) and CharacterModel pins them to a bone.

def gnoll_materials():
	return {
		"fur": material("gnoll_fur", "9a7442"),
		"muzzle": material("gnoll_muzzle", "c9a676"),
		"dark": material("gnoll_dark", "3a2a1c"),
		"mane": material("gnoll_mane", "5c4128", 0.95),
		"nose": material("gnoll_nose", "181210", 0.3),
		"eye": material("gnoll_eye", "f2c230", 0.3, emit=1.5),
		"tooth": material("gnoll_tooth", "efe6d0", 0.4),
	}


def build_gnoll_head():
	m = gnoll_materials()
	b = Builder("gnoll_head")
	b.blob((0.84, 0.8, 0.76), (0, 0.04, 1.6), m["fur"], "x", segs=(12, 8))            # skull
	b.blob((0.74, 0.62, 0.36), (0, -0.02, 1.3), m["muzzle"], "x", segs=(10, 6))       # cheek ruff
	b.seg((0, -0.22, 1.5), (0, -0.74, 1.44), 0.25, 0.16, m["muzzle"], "x", sides=8)  # snout
	b.blob((0.34, 0.48, 0.16), (0, -0.5, 1.3), m["dark"], "x")                          # lower jaw
	b.blob((0.2, 0.14, 0.14), (0, -0.77, 1.5), m["nose"], "x")
	for s in (1, -1):
		b.blob((0.14, 0.08, 0.11), (0.2 * s, -0.34, 1.7), m["eye"], "x", segs=(8, 5))
		b.blob((0.2, 0.08, 0.06), (0.2 * s, -0.36, 1.79), m["dark"], "x", rot=(0, -15 * s, 0))   # brow
		b.seg((0.3 * s, 0.06, 1.86), (0.46 * s, 0.12, 2.3), 0.16, 0.02, m["fur"], "x", sides=4)  # ear
		b.seg((0.31 * s, 0.0, 1.9), (0.44 * s, 0.05, 2.22), 0.08, 0.01, m["dark"], "x", sides=4)
		b.seg((0.1 * s, -0.62, 1.36), (0.1 * s, -0.63, 1.24), 0.035, 0.005, m["tooth"], "x", sides=4)
		for y, z in ((0.1, 1.72), (0.25, 1.55), (-0.05, 1.5)):                               # spots
			b.blob((0.06, 0.16, 0.14), (0.4 * s, y, z), m["dark"], "x", segs=(6, 4))
	b.blob((0.24, 0.7, 0.26), (0, 0.16, 1.96), m["mane"], "x", rot=(-28, 0, 0), segs=(8, 6))  # mane
	b.blob((0.34, 0.34, 0.62), (0, 0.36, 1.5), m["mane"], "x", rot=(12, 0, 0), segs=(8, 6))
	return b.build_static()


def build_gnoll_tail():
	m = gnoll_materials()
	b = Builder("gnoll_tail")
	b.seg((0, 0.22, 0.58), (0, 0.5, 0.46), 0.07, 0.11, m["fur"], "x", sides=6)
	b.blob((0.26, 0.5, 0.26), (0, 0.66, 0.36), m["fur"], "x", rot=(-20, 0, 0))
	b.blob((0.2, 0.26, 0.2), (0, 0.88, 0.28), m["dark"], "x")
	return b.build_static()


def build_orc_face():
	"""Bolt-on for a KayKit head (green-tinted): heavy brow, pointed ears and
	lower tusks. Authored in KayKit mesh space like the gnoll head."""
	skin = material("orc_skin", "6f8f4a", 0.85)
	dark = material("orc_dark", "3c4a28", 0.9)
	tusk = material("orc_tusk", "ece2c8", 0.4)
	eye = material("orc_eye", "f0d040", 0.3, emit=1.2)
	b = Builder("orc_face")
	b.blob((0.7, 0.22, 0.14), (0, -0.44, 1.78), dark, "x", segs=(10, 5))              # brow ridge
	for s in (1, -1):
		b.seg((0.46 * s, -0.02, 1.62), (0.8 * s, 0.1, 1.82), 0.13, 0.01, skin, "x", sides=5)   # ears
		b.seg((0.16 * s, -0.46, 1.32), (0.19 * s, -0.5, 1.56), 0.05, 0.012, tusk, "x", sides=5)  # tusks
		b.blob((0.1, 0.05, 0.07), (0.17 * s, -0.47, 1.68), eye, "x", segs=(6, 4))
	b.blob((0.36, 0.2, 0.16), (0, -0.46, 1.34), skin, "x", segs=(8, 5))                # jutting jaw
	return b.build_static()


# ---------------------------------------------------------------- mire toad (Hollowmere)

def build_toad():
	skin = material("toad_skin", "5d6632", 0.7)
	mottle = material("toad_mottle", "3a4020", 0.8)
	brown = material("toad_brown", "7a5e34", 0.8)
	wart = material("toad_wart", "8c8a48", 0.7)
	belly = material("toad_belly", "d6cda0", 0.8)
	mouth = material("toad_mouth", "b0585a", 0.5)
	eye = material("toad_eye", "d8a430", 0.3, emit=0.6)
	pupil = material("toad_pupil", "140f0a", 0.2)
	b = Builder("mire_toad")
	b.bone("root", (0, 0, 0.42))
	b.bone("body", (0, 0.1, 0.42), "root")
	b.bone("head", (0, -0.4, 0.5), "body")
	b.bone("jaw", (0, -0.3, 0.4), "head")
	b.bone("tongue", (0, -0.6, 0.44), "head")

	b.blob((1.2, 1.25, 0.72), (0, 0.14, 0.46), skin, "body", segs=(14, 9))
	b.blob((1.02, 1.05, 0.4), (0, 0.08, 0.27), belly, "body", segs=(12, 6))
	b.blob((1.14, 0.74, 0.46), (0, -0.52, 0.57), skin, "head", segs=(14, 8))
	b.blob((1.06, 0.66, 0.22), (0, -0.54, 0.38), belly, "jaw", segs=(12, 6))           # throat and lower jaw
	b.blob((0.9, 0.5, 0.1), (0, -0.58, 0.46), mouth, "jaw", segs=(10, 5))              # inside of the mouth
	b.seg((0, -0.4, 0.44), (0, -0.72, 0.44), 0.07, 0.06, mouth, "tongue", sides=6)     # tongue, hidden until it shoots
	b.blob((0.15, 0.13, 0.11), (0, -0.74, 0.44), mouth, "tongue")
	for s in (1, -1):
		b.blob((0.28, 0.28, 0.26), (0.3 * s, -0.6, 0.78), skin, "head", segs=(10, 7))   # eye turrets
		b.blob((0.2, 0.2, 0.2), (0.33 * s, -0.66, 0.84), eye, "head", segs=(8, 6))
		b.blob((0.11, 0.05, 0.05), (0.35 * s, -0.76, 0.85), pupil, "head", segs=(6, 4))
		b.blob((0.05, 0.04, 0.03), (0.08 * s, -0.88, 0.66), pupil, "head", segs=(5, 3))  # nostrils
		b.blob((0.2, 0.46, 0.14), (0.44 * s, -0.1, 0.72), wart, "body", rot=(0, 30 * s, 0))  # parotoid glands
	for x, y, z, w in ((0, 0.1, 0.83, 0.34), (0.26, 0.36, 0.76, 0.24), (-0.22, 0.42, 0.77, 0.26), (0.2, -0.16, 0.8, 0.2),
					   (-0.28, -0.1, 0.79, 0.22), (0, 0.54, 0.72, 0.22), (0.44, 0.24, 0.6, 0.18), (-0.46, 0.2, 0.6, 0.2),
					   (0.14, -0.62, 0.8, 0.14), (-0.16, -0.56, 0.81, 0.12)):
		b.blob((w, w * 1.2, 0.07), (x, y, z), mottle if w > 0.19 else brown, "head" if y < -0.4 else "body",
			   rot=(0, x * 40, 0), segs=(8, 4))
	for x, y, z in ((0.1, 0.3, 0.84), (-0.12, 0.22, 0.85), (0.34, 0.06, 0.74), (-0.36, 0.0, 0.74), (0.02, -0.16, 0.84),
					(0.22, 0.6, 0.66), (-0.2, 0.62, 0.66), (0.38, 0.44, 0.68), (-0.4, 0.46, 0.66), (0.0, 0.72, 0.58),
					(0.24, -0.4, 0.78), (-0.24, -0.38, 0.79)):
		b.blob((0.08, 0.08, 0.06), (x, y, z), wart, "head" if y < -0.4 else "body", segs=(6, 4))

	legs = {"leg_fl": (0.36, -0.4), "leg_fr": (-0.36, -0.4), "leg_bl": (0.44, 0.34), "leg_br": (-0.44, 0.34)}
	for name_, (x, y) in legs.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, 0.36), "root")
		if y < 0:   # front: short arms braced outward
			b.seg((x, y, 0.4), (x + 0.14 * s, y - 0.1, 0.06), 0.09, 0.07, skin, name_, sides=6)
			b.blob((0.24, 0.24, 0.06), (x + 0.16 * s, y - 0.18, 0.03), brown, name_)
			for k in (-1, 0, 1):
				b.seg((x + 0.16 * s, y - 0.2, 0.03), (x + (0.16 + 0.1 * k) * s, y - 0.34, 0.02), 0.03, 0.02, brown, name_, sides=4)
		else:       # back: big folded thighs, shins forward, long webbed feet
			b.blob((0.34, 0.62, 0.38), (x + 0.14 * s, y, 0.32), skin, name_, rot=(12, 0, 0), segs=(10, 7))
			b.blob((0.16, 0.34, 0.08), (x + 0.2 * s, y + 0.04, 0.5), mottle, name_, segs=(6, 4))
			b.seg((x + 0.22 * s, y + 0.2, 0.16), (x + 0.26 * s, y - 0.3, 0.1), 0.09, 0.07, skin, name_, sides=6)
			b.blob((0.34, 0.44, 0.06), (x + 0.28 * s, y - 0.44, 0.03), brown, name_)
			for k in (-1, 0, 1):
				b.seg((x + 0.28 * s, y - 0.5, 0.03), (x + (0.28 + 0.12 * k) * s, y - 0.72, 0.02), 0.035, 0.02, brown, name_, sides=4)
	arm = b.build()

	def legs_pose(front, back):
		return {"leg_fl": {"rot": (front, 0, 0)}, "leg_fr": {"rot": (front, 0, 0)},
				"leg_bl": {"rot": (back, 0, 0)}, "leg_br": {"rot": (back, 0, 0)}}

	def hop(t, height, reach):
		air = max(0.0, math.sin(math.pi * min(1.0, max(0.0, (t - 0.15) / 0.5))))
		kick = seq(t, [(0, 0), (0.12, 0.25), (0.3, -1), (0.6, 0), (1, 0)])
		pitch = seq(t, [(0, 0), (0.12, -3), (0.3, 12), (0.55, -8), (0.7, 0)])
		squash = seq(t, [(0, 0), (0.12, -0.04), (0.3, 0), (0.65, 0), (0.72, -0.05), (0.9, 0)])
		return merge({"root": {"loc": (0, 0, height * air + squash), "rot": (pitch, 0, 0)},
					  "head": {"rot": (-pitch * 0.4, 0, 0)}},
					 legs_pose(seq(t, [(0, 0), (0.3, -15), (0.55, reach), (0.7, 0)]), 55 * kick))

	def idle(t):
		gulp = max(0.0, wave(t, 2))
		return {"body": {"loc": (0, 0, 0.01 * wave(t))}, "jaw": {"loc": (0, 0, -0.025 * gulp)},
				"head": {"rot": (2 * wave(t, 1, 0.3), 0, 4 * wave(t, 0.5))}}

	def walk(t):
		return hop(t, 0.22, 25)

	def run(t):
		return hop(t, 0.38, 35)

	def attack(t):  # crouch, lunge, gape and shoot the tongue
		lunge = seq(t, [(0, 0), (0.3, -0.08), (0.45, 0.3), (1, 0)])
		pitch = seq(t, [(0, 0), (0.3, -6), (0.45, 12), (0.75, 0)])
		jaw = seq(t, [(0, 0), (0.3, -6), (0.42, -38), (0.62, -30), (0.78, 0)])
		tongue = seq(t, [(0, 0), (0.38, 0), (0.48, 0.7), (0.62, 0.6), (0.76, 0)])
		return merge({"root": {"loc": (0, lunge, 0.12 * max(0.0, lunge)), "rot": (pitch, 0, 0)},
					  "jaw": {"rot": (jaw, 0, 0)}, "tongue": {"loc": (0, tongue, -0.02 * tongue)},
					  "head": {"rot": (-jaw * 0.25, 0, 0)}},
					 legs_pose(seq(t, [(0, 0), (0.3, -10), (0.45, 25), (1, 0)]), seq(t, [(0, 0), (0.3, 12), (0.45, -45), (1, 0)])))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, -0.04 * k), "rot": (-8 * k, 5 * k, 0)},
					  "head": {"rot": (-10 * k, 0, 8 * k)}, "jaw": {"rot": (-14 * k, 0, 0)}}, legs_pose(10 * k, 10 * k))

	def death(t):  # flops over onto its back, legs in the air
		roll = seq(t, [(0.1, 0), (0.5, 100), (0.68, 176), (0.8, 180)])
		lift = seq(t, [(0.1, 0), (0.35, 0.3), (0.72, 0.1), (0.8, 0.12)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		twitch = 8 * wave(t, 6) * seq(t, [(0.75, 0), (0.85, 1), (1, 0)])
		return merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)}, "jaw": {"rot": (-18 * curl, 0, 0)},
					  "head": {"rot": (-10 * curl, 0, 0)}},
					 legs_pose(-20 * curl + twitch, -70 * curl - twitch))

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 0.9, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.2, death, False)
	return arm


# ---------------------------------------------------------------- snapping turtle (Hollowmere)

TURTLE_LEGS = {"leg_fl": (0.46, -0.46), "leg_fr": (-0.46, -0.46), "leg_bl": (0.46, 0.46), "leg_br": (-0.46, 0.46)}


def build_turtle():
	shell = material("turtle_shell", "3a3824", 0.75)
	rim = material("turtle_rim", "2c2a1c", 0.8)
	ridge = material("turtle_ridge", "25231a", 0.7)
	moss = material("turtle_moss", "55682c", 0.95)
	skin = material("turtle_skin", "5e5a40", 0.85)
	belly = material("turtle_belly", "a8965e", 0.85)
	beak = material("turtle_beak", "2a2620", 0.5)
	eye = material("turtle_eye", "d0822a", 0.3, emit=0.8)
	b = Builder("snapping_turtle")
	b.bone("root", (0, 0, 0.4))
	b.bone("body", (0, 0.0, 0.42), "root")
	b.bone("neck", (0, -0.6, 0.38), "body")
	b.bone("head", (0, -0.95, 0.42), "neck")
	b.bone("jaw", (0, -1.0, 0.36), "head")
	b.bone("tail", (0, 0.74, 0.32), "body")

	b.blob((1.3, 1.6, 0.66), (0, 0.02, 0.5), shell, "body", segs=(14, 9))              # carapace
	b.blob((1.44, 1.72, 0.2), (0, 0.02, 0.42), rim, "body", segs=(16, 6))               # marginal rim
	b.blob((1.04, 1.36, 0.22), (0, 0.02, 0.29), belly, "body", segs=(12, 6))            # plastron

	def shell_z(x, y):
		return 0.5 + 0.33 * math.sqrt(max(0.0, 1 - (x / 0.65) ** 2 - (y / 0.8) ** 2))
	for x in (-0.3, 0.0, 0.3):
		for y in (-0.5, -0.24, 0.02, 0.28, 0.52):
			if x and abs(y) > 0.5:
				continue
			z = shell_z(x, y)
			big = 1.0 if x == 0 else 0.75
			b.seg((x, y + 0.08, z - 0.05), (x * 1.04, y - 0.02, z + 0.1 * big), 0.1 * big, 0.02, ridge, "body", sides=4)
	for x, y, w, l in ((0.18, -0.36, 0.36, 0.3), (-0.26, 0.12, 0.34, 0.42), (0.3, 0.34, 0.26, 0.26), (-0.06, 0.5, 0.3, 0.2),
					   (0.36, -0.08, 0.2, 0.3), (-0.34, -0.3, 0.2, 0.22)):
		b.blob((w, l, 0.09), (x, y, shell_z(x, y) - 0.02), moss, "body", rot=(0, x * 50, 0), segs=(8, 4))
	for k in range(-3, 4):  # saw-toothed back edge of the shell
		a = math.radians(90 + k * 16)
		x, y = 0.7 * math.cos(a), 0.84 * math.sin(a)
		b.seg((x * 0.95, y * 0.95, 0.42), (x * 1.1, y * 1.08, 0.4), 0.07, 0.01, rim, "body", sides=4)

	b.seg((0, -0.5, 0.38), (0, -0.96, 0.44), 0.19, 0.16, skin, "neck", sides=8)
	b.blob((0.46, 0.52, 0.36), (0, -1.06, 0.47), skin, "head", segs=(10, 7))
	b.blob((0.3, 0.3, 0.1), (0, -1.06, 0.6), material("turtle_skin_dark", "4a4632", 0.8), "head", segs=(8, 5))  # skull plate
	b.seg((0, -1.2, 0.48), (0, -1.42, 0.36), 0.12, 0.02, beak, "head", sides=6)          # hooked upper beak
	b.blob((0.34, 0.4, 0.13), (0, -1.16, 0.34), skin, "jaw", segs=(8, 5))
	b.seg((0, -1.22, 0.34), (0, -1.38, 0.37), 0.08, 0.02, beak, "jaw", sides=5)          # lower beak
	for s in (1, -1):
		b.blob((0.09, 0.08, 0.08), (0.17 * s, -1.2, 0.54), eye, "head", segs=(6, 4))
		for y in (-0.62, -0.78, -0.92):                                                   # neck bumps
			b.blob((0.07, 0.07, 0.07), (0.16 * s, y, 0.44 + (y + 0.6) * -0.1), belly, "neck", segs=(5, 3))

	b.seg((0, 0.72, 0.34), (0, 1.36, 0.1), 0.13, 0.03, skin, "tail", sides=6)
	for k in range(4):
		y = 0.8 + k * 0.14
		z = 0.34 - (y - 0.72) * 0.375
		b.seg((0, y, z + 0.04), (0, y + 0.06, z + 0.16 - k * 0.025), 0.05, 0.005, ridge, "tail", sides=4)

	sink = Matrix.Translation((0, 0, -0.1))   # the shell rides low, on stubby legs
	for p in b.parts:
		p.data.transform(sink)
	b.bones = [(n, h + Vector((0, 0, -0.1)), par) for n, h, par in b.bones]
	for name_, (x, y) in TURTLE_LEGS.items():
		s = 1 if x > 0 else -1
		f = -1 if y < 0 else 1
		b.bone(name_, (x, y, 0.24), "root")
		b.seg((x, y, 0.26), (x + 0.2 * s, y + 0.05 * f, 0.07), 0.17, 0.14, skin, name_, sides=7)
		b.blob((0.3, 0.3, 0.1), (x + 0.22 * s, y + 0.02 * f, 0.05), skin, name_)
		for k in (-1, 0, 1):
			b.seg((x + (0.22 + 0.08 * k) * s, y - 0.1, 0.05), (x + (0.22 + 0.1 * k) * s, y - 0.22, 0.02), 0.035, 0.006, beak, name_, sides=4)
	arm = b.build()

	def leg(name_, swing, lift=0.0):
		s = 1 if TURTLE_LEGS[name_][0] > 0 else -1
		return {name_: {"rot": (0, lift * s, -swing * s)}}

	def gait(t, amp, lift):
		out = {}
		for name_ in TURTLE_LEGS:
			ph = 0.0 if name_ in ("leg_fl", "leg_br") else 0.5
			out.update(leg(name_, amp * wave(t, 1, ph), lift * max(0.0, wave(t, 1, ph + 0.25))))
		return out

	def idle(t):
		return merge({"body": {"loc": (0, 0, 0.008 * wave(t))},
					  "neck": {"rot": (3 * wave(t, 1, 0.2), 0, 6 * wave(t, 0.5)), "loc": (0, 0.03 * wave(t, 0.5, 0.1), 0)},
					  "jaw": {"rot": (-4 * max(0.0, wave(t, 2)), 0, 0)}, "tail": {"rot": (0, 0, 5 * wave(t, 0.5))}},
					 gait(t, 2, 0))

	def walk(t):
		return merge(gait(t, 22, 14), {"body": {"rot": (0, 3 * wave(t), 2 * wave(t, 2))}, "root": {"loc": (0, 0, 0.015 * abs(wave(t, 2)))},
									   "neck": {"rot": (3 * wave(t, 2), 0, -4 * wave(t))}, "tail": {"rot": (0, 0, 8 * wave(t))}})

	def run(t):
		return merge(gait(t, 30, 20), {"body": {"rot": (0, 4 * wave(t), 3 * wave(t, 2))}, "root": {"loc": (0, 0, 0.03 * abs(wave(t, 2)))},
									   "neck": {"loc": (0, 0.06, 0)}, "tail": {"rot": (0, 0, 12 * wave(t))}})

	def attack(t):  # draw back, then the neck shoots out and the beak snaps shut
		reach = seq(t, [(0, 0), (0.3, -0.12), (0.42, 0.38), (0.62, 0.3), (1, 0)])
		jaw = seq(t, [(0, 0), (0.3, -40), (0.42, -34), (0.48, 4), (0.7, 0)])
		pitch = seq(t, [(0, 0), (0.3, 14), (0.44, -10), (0.7, -4), (1, 0)])
		return merge({"neck": {"loc": (0, reach, 0.04 * max(0.0, reach)), "rot": (pitch * 0.5, 0, 0)},
					  "head": {"rot": (pitch, 0, 0)}, "jaw": {"rot": (jaw, 0, 0)},
					  "root": {"loc": (0, 0.4 * max(0.0, reach) * 0.3, 0), "rot": (seq(t, [(0, 0), (0.3, 4), (0.45, -3), (1, 0)]), 0, 0)}},
					 gait(0.0, 0, 0))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.02 * k), "rot": (6 * k, 5 * k, 0)},
					  "neck": {"loc": (0, -0.18 * k, 0), "rot": (10 * k, 0, 8 * k)}, "jaw": {"rot": (-20 * k, 0, 0)}},
					 gait(t, 6 * k, 8 * k))

	def death(t):  # rolls over onto its shell, head lolling, legs curled
		roll = seq(t, [(0.15, 0), (0.55, 95), (0.72, 176), (0.82, 180)])
		lift = seq(t, [(0.15, 0), (0.45, 0.35), (0.75, 0.0), (0.82, 0.03)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		out = merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)},
					 "neck": {"rot": (-24 * curl, 0, 18 * curl), "loc": (0, -0.08 * curl, 0)}, "jaw": {"rot": (-22 * curl, 0, 0)},
					 "tail": {"rot": (-15 * curl, 0, 0)}})
		for i, name_ in enumerate(TURTLE_LEGS):
			out = merge(out, leg(name_, 8 * wave(t, 5, i * 0.2) * seq(t, [(0.7, 0), (0.8, 1), (1, 0.3)]), -40 * curl))
		return out

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 1.2, walk, True)
	clip(arm, "run", 0.7, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- bog leech (Hollowmere)

LEECH_CHAIN = ("head", "front", "mid", "back", "rear", "tail")  # front to back


def build_leech():
	gloss = material("leech_skin", "2b1a30", 0.5)
	stripe = material("leech_stripe", "6a3a4c", 0.3)
	under = material("leech_under", "86677a", 0.45)
	mouth = material("leech_mouth", "b24a66", 0.4)
	dark = material("leech_dark", "0e070e", 0.3)
	tooth = material("leech_tooth", "e6d6c8", 0.4)
	b = Builder("bog_leech")
	b.bone("root", (0, 0, 0.22))
	b.bone("mid", (0, 0.04, 0.22), "root")
	b.bone("front", (0, -0.16, 0.22), "mid")
	b.bone("head", (0, -0.36, 0.22), "front")
	b.bone("back", (0, 0.26, 0.22), "mid")
	b.bone("rear", (0, 0.46, 0.2), "back")
	b.bone("tail", (0, 0.64, 0.18), "rear")
	body = ((-0.52, 0.32, 0.26, "head"), (-0.36, 0.4, 0.33, "head"), (-0.18, 0.47, 0.39, "front"),
			(0.0, 0.52, 0.42, "mid"), (0.17, 0.54, 0.43, "mid"), (0.34, 0.52, 0.41, "back"),
			(0.5, 0.47, 0.37, "rear"), (0.65, 0.4, 0.31, "tail"), (0.79, 0.3, 0.23, "tail"))
	for i, (y, w, h, bone) in enumerate(body):
		b.blob((w, 0.26, h), (0, y, h * 0.5 + 0.02), gloss, bone, segs=(12, 8))
		b.blob((w * 0.84, 0.24, h * 0.3), (0, y, 0.06), under, bone, segs=(10, 5))
		b.blob((w * 1.02, 0.05, h * 1.02), (0, y + 0.1, h * 0.5 + 0.02), dark, bone, segs=(12, 6))   # groove between rings
		if 0 < i < len(body) - 1:
			b.blob((0.07, 0.1, 0.03), (0, y, h + 0.02), stripe, bone, segs=(6, 3))                      # spots down the back
			for s in (1, -1):
				b.blob((0.05, 0.08, 0.05), (w * 0.4 * s, y, h * 0.75), stripe, bone, segs=(5, 3))
	b.blob((0.34, 0.1, 0.3), (0, -0.64, 0.16), mouth, "head", segs=(12, 6))            # sucker rim
	b.blob((0.18, 0.06, 0.16), (0, -0.68, 0.16), dark, "head", segs=(10, 5))
	for k in range(6):
		a = math.radians(k * 60 + 30)
		b.seg((0.1 * math.cos(a), -0.67, 0.16 + 0.09 * math.sin(a)), (0.05 * math.cos(a), -0.71, 0.16 + 0.045 * math.sin(a)),
			  0.02, 0.004, tooth, "head", sides=4)
	for s in (1, -1):
		b.blob((0.04, 0.04, 0.04), (0.06 * s, -0.56, 0.3), dark, "head", segs=(5, 3))
	b.blob((0.28, 0.24, 0.07), (0, 0.84, 0.04), under, "tail", segs=(10, 4))            # tail sucker
	arm = b.build()

	def chain(t, amp, cycles=1.0, yaw=0.0):
		out = {}
		for i, name_ in enumerate(LEECH_CHAIN):
			if name_ in ("mid",):
				continue
			sign = -1 if name_ in ("head", "front") else 1   # front bones turn their children the other way
			out[name_] = {"rot": (sign * amp * wave(t, cycles, -0.16 * i), 0, yaw * wave(t, cycles, -0.16 * i + 0.25))}
		return out

	def idle(t):
		return merge(chain(t, 3, 1), {"head": {"rot": (6 + 4 * wave(t, 1, 0.3), 0, 14 * wave(t, 0.5))},
									  "mid": {"loc": (0, 0, 0.01 * wave(t, 2))}})

	def walk(t):
		return merge(chain(t, 14, 1, 7), {"root": {"loc": (0, 0.03 * wave(t), 0.02 * max(0.0, wave(t, 1, 0.2)))}})

	def run(t):
		return merge(chain(t, 20, 1, 9), {"root": {"loc": (0, 0.05 * wave(t), 0.03 * max(0.0, wave(t, 1, 0.2)))}})

	def attack(t):  # rear up the front end, then strike down and latch
		rear = seq(t, [(0, 0), (0.35, 1), (0.52, -0.5), (0.75, -0.2), (1, 0)])
		return {"front": {"rot": (28 * rear, 0, 0)}, "head": {"rot": (24 * rear, 0, 0)},
				"root": {"loc": (0, seq(t, [(0, 0), (0.35, -0.06), (0.52, 0.22), (1, 0)]), 0)},
				"back": {"rot": (-6 * rear, 0, 0)}, "tail": {"rot": (8 * rear, 0, 0)}}

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0)}, "front": {"rot": (14 * k, 0, 12 * k)}, "head": {"rot": (12 * k, 0, 10 * k)},
					  "back": {"rot": (0, 0, -10 * k)}, "tail": {"rot": (-10 * k, 0, -12 * k)}})

	def death(t):  # writhes, curls into a C and rolls onto its side
		curl = seq(t, [(0.2, 0), (0.85, 1)])
		writhe = seq(t, [(0, 1), (0.7, 0)])
		out = merge(chain(t * 2, 18 * writhe, 1, 20 * writhe), {"root": {"rot": (0, seq(t, [(0.3, 0), (0.8, 24)]), 0),
																		 "loc": (0, 0, seq(t, [(0.3, 0), (0.8, -0.03)]))}})
		for name_ in ("front", "head", "back", "rear", "tail"):
			out = merge(out, {name_: {"rot": (-3 * curl, 0, 30 * curl * (1 if name_ in ("front", "head") else -1))}})
		return out

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 1.1, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- lizardfolk parts (Hollowmere)
# Bolt-ons for KayKit bodies, authored in KayKit mesh space like the gnoll head.

LIZARD_SKINS = {
	"lizard": {"scale": "5e8a3c", "dark": "35562a", "belly": "d2c68a", "spine": "8a3a2a"},
	"lizard_chief": {"scale": "3c5a30", "dark": "1f3320", "belly": "a89a64", "spine": "5a2a20"},
}


def lizard_materials(kind):
	c = LIZARD_SKINS[kind]
	return {
		"scale": material(f"{kind}_scale", c["scale"], 0.7),
		"dark": material(f"{kind}_dark", c["dark"], 0.75),
		"belly": material(f"{kind}_belly", c["belly"], 0.8),
		"spine": material(f"{kind}_spine", c["spine"], 0.6),
		"eye": material(f"{kind}_eye", "f4d02a", 0.3, emit=1.4),
		"pupil": material(f"{kind}_pupil", "120e08", 0.2),
		"tooth": material(f"{kind}_tooth", "efe6d0", 0.4),
		"bone": material(f"{kind}_bone", "e2d8bc", 0.6),
		"red": material(f"{kind}_feather_red", "b8322a", 0.8),
		"teal": material(f"{kind}_feather_teal", "2a8a86", 0.8),
		"gold": material(f"{kind}_feather_gold", "d8a430", 0.7),
	}


def _lizard_head(name, kind, crest):
	m = lizard_materials(kind)
	b = Builder(name)
	b.blob((0.78, 0.78, 0.66), (0, 0.08, 1.62), m["scale"], "x", segs=(12, 8))          # skull
	b.blob((0.6, 0.56, 0.36), (0, 0.06, 1.38), m["scale"], "x", segs=(10, 6))          # neck
	b.blob((0.4, 0.2, 0.26), (0, -0.16, 1.36), m["belly"], "x", segs=(8, 5))            # pale throat
	b.blob((0.52, 0.86, 0.3), (0, -0.44, 1.56), m["scale"], "x", segs=(10, 7))          # long flat snout
	b.blob((0.44, 0.7, 0.16), (0, -0.4, 1.38), m["belly"], "x", segs=(10, 5))           # lower jaw
	b.blob((0.4, 0.5, 0.08), (0, -0.46, 1.7), m["dark"], "x", segs=(8, 4))              # dark stripe down the snout
	for s in (1, -1):
		b.blob((0.2, 0.18, 0.16), (0.24 * s, -0.22, 1.76), m["scale"], "x", segs=(8, 5))   # brow bumps
		b.blob((0.12, 0.13, 0.12), (0.27 * s, -0.27, 1.73), m["eye"], "x", segs=(8, 5))
		b.blob((0.03, 0.05, 0.1), (0.31 * s, -0.31, 1.73), m["pupil"], "x", segs=(5, 3))  # slit pupil
		b.blob((0.04, 0.04, 0.03), (0.08 * s, -0.85, 1.62), m["pupil"], "x", segs=(5, 3))  # nostril
		for k, y in enumerate((-0.74, -0.58, -0.42, -0.26)):                                 # teeth
			b.seg((0.17 * s * (1 - 0.1 * (3 - k)), y, 1.46), (0.17 * s * (1 - 0.1 * (3 - k)), y - 0.01, 1.4), 0.025, 0.004,
				  m["tooth"], "x", sides=4)
		for y, z in ((0.0, 1.5), (0.2, 1.64), (-0.1, 1.62)):                                 # scale patches
			b.blob((0.06, 0.18, 0.14), (0.38 * s, y, z), m["dark"], "x", segs=(6, 4))
		# ear frills fanning back
		b.seg((0.34 * s, 0.14, 1.66), (0.56 * s, 0.34, 1.82), 0.1, 0.01, m["spine"], "x", sides=4)
		b.seg((0.34 * s, 0.18, 1.54), (0.58 * s, 0.4, 1.56), 0.09, 0.01, m["spine"], "x", sides=4)
		b.seg((0.1 * s, -0.8, 1.66), (0.12 * s, -0.84, 1.74), 0.035, 0.005, m["dark"], "x", sides=4)  # nose horns
	for k, (y, z) in enumerate(((0.0, 1.98), (0.22, 1.94), (0.4, 1.82), (0.52, 1.64))):     # spines down the back of the head
		b.seg((0, y, z - 0.08), (0, y + 0.1, z + 0.12 - k * 0.02), 0.07, 0.01, m["spine"], "x", sides=4)
	if crest == "feathers":
		b.seg((-0.3, 0.02, 1.9), (0.3, 0.02, 1.9), 0.07, 0.07, m["bone"], "x", sides=6)      # bone band
		for k, (x, col) in enumerate(((0.0, "red"), (0.14, "teal"), (-0.14, "teal"), (0.26, "gold"), (-0.26, "gold"))):
			tip = (x * 1.6, 0.26 + abs(x) * 0.4, 2.52 - abs(x) * 1.2)
			b.seg((x, 0.06, 1.92), tip, 0.07, 0.015, m[col], "x", sides=4)
			b.blob((0.03, 0.06, 0.06), tip, m["dark"], "x", segs=(4, 3))
		for s in (1, -1):
			b.blob((0.12, 0.12, 0.12), (0.3 * s, 0.02, 1.9), m["bone"], "x", segs=(6, 4))
	elif crest == "bone":
		b.blob((0.62, 0.5, 0.18), (0, 0.02, 2.0), m["bone"], "x", rot=(-10, 0, 0), segs=(10, 5))   # skull plate
		for s in (1, -1):
			b.seg((0.26 * s, 0.1, 1.98), (0.52 * s, 0.34, 2.36), 0.09, 0.012, m["bone"], "x", sides=5)   # horns
			b.seg((0.18 * s, -0.12, 2.02), (0.26 * s, -0.14, 2.22), 0.05, 0.008, m["bone"], "x", sides=4)
		b.seg((0, -0.16, 2.04), (0, -0.2, 2.3), 0.06, 0.01, m["bone"], "x", sides=4)
	grow = Matrix.Translation((0, 0, 1.3)) @ Matrix.Scale(1.18, 4) @ Matrix.Translation((0, 0, -1.3))
	for p in b.parts:   # sized to a KayKit chibi head
		p.data.transform(grow)
	return b.build_static()


def build_lizard_head():
	return _lizard_head("lizard_head", "lizard", "plain")


def build_lizard_head_shaman():
	return _lizard_head("lizard_head_shaman", "lizard", "feathers")


def build_lizard_head_chief():
	return _lizard_head("lizard_head_chief", "lizard_chief", "bone")


def _lizard_tail(name, kind):
	m = lizard_materials(kind)
	b = Builder(name)
	pts = ((0, 0.18, 0.62), (0, 0.5, 0.5), (0, 0.86, 0.3), (0, 1.2, 0.12), (0, 1.5, 0.04))
	radii = (0.15, 0.12, 0.085, 0.05, 0.015)
	for (a, ra), (c, rc) in zip(zip(pts, radii), zip(pts[1:], radii[1:])):
		b.seg(a, c, ra, rc, m["scale"], "x", sides=7)
		b.blob((ra * 1.6, 0.1, ra * 1.6), a, m["scale"], "x", segs=(7, 5))
		b.seg((0, a[1] + 0.02, a[2] - ra * 0.6), (0, c[1], c[2] - rc * 0.6), ra * 0.6, rc * 0.6, m["belly"], "x", sides=5)
	for k in range(6):
		y = 0.3 + k * 0.2
		z = 0.58 - (y - 0.18) * 0.43 if y < 0.86 else 0.3 - (y - 0.86) * 0.53
		r = 0.12 - k * 0.018
		b.seg((0, y, z + r * 0.7), (0, y + 0.06, z + r * 0.7 + 0.1 - k * 0.012), 0.045, 0.006, m["spine"], "x", sides=4)
	for y in (0.4, 0.75, 1.05):
		b.blob((0.24 - y * 0.12, 0.1, 0.03), (0, y, (0.6 - y * 0.43) + 0.11 - y * 0.03), m["dark"], "x", segs=(6, 3))
	return b.build_static()


def build_lizard_tail():
	return _lizard_tail("lizard_tail", "lizard")


def build_lizard_tail_chief():
	return _lizard_tail("lizard_tail_chief", "lizard_chief")


# ---------------------------------------------------------------- drowned parts (Hollowmere)
# Hanging weed and barnacles for KayKit skeletons, in their mesh space.

def drowned_materials():
	return {
		"kelp": material("drowned_kelp", "3e5a2a", 0.8),
		"weed": material("drowned_weed", "5e6e30", 0.85),
		"slime": material("drowned_slime", "2c4038", 0.5),
		"barnacle": material("drowned_barnacle", "c8c2b0", 0.7),
		"hole": material("drowned_hole", "3a3630", 0.8),
	}


def _kelp(b, top, length, mat, lean=(0.0, 0.0), width=0.05, parts=3):
	"""A strand hanging from `top`, kinking a little side to side as it falls."""
	x, y, z = top
	step = length / parts
	for k in range(parts):
		kink = 0.04 * (1 if k % 2 == 0 else -1)
		nx, ny, nz = x + lean[0] * step + kink, y + lean[1] * step, z - step
		b.seg((x, y, z), (nx, ny, nz), width * (1 - 0.25 * k), width * (1 - 0.25 * (k + 1)) + 0.005, mat, "x", sides=4)
		x, y, z = nx, ny, nz


def _barnacle(b, loc, normal, m, size=1.0):
	n = Vector(normal).normalized()
	base = Vector(loc)
	b.seg(tuple(base), tuple(base + n * 0.07 * size), 0.055 * size, 0.035 * size, m["barnacle"], "x", sides=6)
	b.blob((0.04 * size, 0.04 * size, 0.04 * size), tuple(base + n * 0.07 * size), m["hole"], "x", segs=(5, 3))


def build_drowned_head():
	m = drowned_materials()
	b = Builder("drowned_head")
	b.blob((0.5, 0.5, 0.1), (0.04, 0.06, 2.12), m["slime"], "x", rot=(0, 8, 0), segs=(8, 4))   # weed matted on the skull
	for x, y, ln in ((0.38, -0.1, 0.5), (0.42, 0.14, 0.62), (-0.4, 0.0, 0.56), (-0.36, 0.22, 0.44), (0.22, 0.36, 0.5),
					 (-0.16, 0.4, 0.58), (0.02, 0.44, 0.46)):
		_kelp(b, (x, y, 2.02), ln, m["kelp"] if ln > 0.5 else m["weed"], lean=(x * 0.3, 0.2 if y > 0.2 else 0.0), width=0.05)
	for loc, nrm, sz in (((0.3, -0.2, 1.98), (0.6, -0.4, 0.7), 1.0), ((-0.28, -0.1, 2.02), (-0.5, -0.2, 0.8), 0.8),
						 ((0.1, 0.3, 2.06), (0.1, 0.5, 0.8), 0.9), ((-0.4, 0.1, 1.74), (-1, 0.1, 0.1), 0.7)):
		_barnacle(b, loc, nrm, m, sz)
	return b.build_static()


def build_drowned_chest():
	m = drowned_materials()
	b = Builder("drowned_chest")
	for s in (1, -1):
		b.blob((0.34, 0.5, 0.08), (0.24 * s, 0.0, 1.3), m["slime"], "x", rot=(0, 18 * s, 0), segs=(8, 4))   # over the shoulders
		for y, ln in ((-0.2, 0.52), (0.0, 0.34), (0.2, 0.6)):
			_kelp(b, (0.3 * s, y, 1.3), ln, m["kelp"] if ln > 0.4 else m["weed"], lean=(0.1 * s, 0.1 * (1 if y > 0 else -1)), width=0.045)
	_kelp(b, (0.06, -0.3, 1.2), 0.46, m["weed"], lean=(0.0, -0.1), width=0.04)
	for loc, nrm, sz in (((0.18, -0.3, 1.1), (0.2, -1, 0.2), 1.1), ((-0.12, -0.33, 0.92), (0, -1, 0), 0.8),
						 ((0.28, 0.24, 1.18), (0.4, 1, 0.3), 0.9), ((-0.22, 0.28, 1.0), (-0.2, 1, 0), 1.0)):
		_barnacle(b, loc, nrm, m, sz)
	return b.build_static()


def build_drowned_hips():
	m = drowned_materials()
	b = Builder("drowned_hips")
	b.seg((0, 0, 0.62), (0, 0, 0.7), 0.36, 0.34, m["slime"], "x", sides=10)                     # a belt of rotted weed
	for k in range(10):
		a = math.radians(k * 36 + 10)
		x, y = 0.36 * math.cos(a), 0.34 * math.sin(a)
		if abs(x) < 0.12 and y < 0:   # leave the front open over the legs' stride
			continue
		_kelp(b, (x, y, 0.64), 0.3 + 0.12 * (k % 3), m["kelp"] if k % 2 else m["weed"], lean=(x * 0.15, y * 0.15), width=0.045, parts=2)
	return b.build_static()


ATTACHMENTS = {"gnoll_head": build_gnoll_head, "gnoll_tail": build_gnoll_tail, "orc_face": build_orc_face,
			   "lizard_head": build_lizard_head, "lizard_head_shaman": build_lizard_head_shaman,
			   "lizard_head_chief": build_lizard_head_chief, "lizard_tail": build_lizard_tail,
			   "lizard_tail_chief": build_lizard_tail_chief, "drowned_head": build_drowned_head,
			   "drowned_chest": build_drowned_chest, "drowned_hips": build_drowned_hips}
CREATURES = {"rat": build_rat, "fire_beetle": build_beetle, "wolf": build_wolf, "dire_wolf": build_dire_wolf,
			 "bear": build_bear, "spider": build_spider, "mire_toad": build_toad, "snapping_turtle": build_turtle,
			 "bog_leech": build_leech}
PREVIEW_FRAMES = {"idle": [0.0], "walk": [0.0, 0.25, 0.5], "run": [0.25], "attack": [0.3, 0.5],
				  "hit": [0.25], "death": [0.5, 1.0]}


def export(arm, path):
	arm.animation_data.action = None
	for pb in arm.pose.bones:
		pb.rotation_euler = (0, 0, 0)
		pb.location = (0, 0, 0)
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
							  export_animations=True, export_animation_mode="ACTIONS",
							  export_yup=True, export_apply=False)


def preview(arm, name, out_dir):
	scene = bpy.context.scene
	scene.render.engine = "BLENDER_WORKBENCH"
	scene.display.shading.color_type = "MATERIAL"
	scene.display.shading.light = "STUDIO"
	scene.render.resolution_x, scene.render.resolution_y = 480, 360
	cam_data = bpy.data.cameras.new("cam")
	cam = bpy.data.objects.new("cam", cam_data)
	bpy.context.collection.objects.link(cam)
	cam.location = (2.6, -2.8, 1.8)
	cam.rotation_euler = (math.radians(66), 0, math.radians(43))
	scene.camera = cam
	ground = bpy.data.meshes.new("ground")
	bm = bmesh.new()
	bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3)
	bm.to_mesh(ground)
	g = bpy.data.objects.new("ground", ground)
	g.data.materials.append(material("ground", "6f8f5a"))
	bpy.context.collection.objects.link(g)
	for act_name, ts in PREVIEW_FRAMES.items():
		act = bpy.data.actions[act_name] if act_name in bpy.data.actions else None
		if act is None:
			continue
		arm.animation_data.action = act
		start, end = act.frame_range
		for t in ts:
			scene.frame_set(int(round(start + (end - start) * t)))
			scene.render.filepath = os.path.join(out_dir, f"{name}_{act_name}_{int(t * 100):03d}.png")
			bpy.ops.render.render(write_still=True)
	bpy.data.objects.remove(cam)
	bpy.data.objects.remove(g)


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/creatures", "--preview": "", "--only": ""}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) - {""}  # comma list: rebuild just these
	for name, build in CREATURES.items():
		if only and name not in only:
			continue
		reset_scene()
		arm = build()
		if opts["--preview"]:
			os.makedirs(opts["--preview"], exist_ok=True)
			preview(arm, name, opts["--preview"])
		path = os.path.abspath(os.path.join(opts["--out"], f"{name}.glb"))
		export(arm, path)
		print(f"exported {path}")
	for name, build in ATTACHMENTS.items():
		if only and name not in only:
			continue
		reset_scene()
		build()
		path = os.path.abspath(os.path.join(opts["--out"], f"{name}.glb"))
		bpy.ops.object.select_all(action="SELECT")
		bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
								  export_animations=False, export_yup=True)
		print(f"exported {path}")


main()
