"""Builds Emberfall's creature models (rigged, animated, low-poly) and exports GLBs.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/creatures.py -- --out assets/creatures [--preview DIR] [--only rat]

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


ATTACHMENTS = {"gnoll_head": build_gnoll_head, "gnoll_tail": build_gnoll_tail, "orc_face": build_orc_face}
CREATURES = {"rat": build_rat, "fire_beetle": build_beetle, "wolf": build_wolf, "dire_wolf": build_dire_wolf,
			 "bear": build_bear, "spider": build_spider}
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
	for name, build in CREATURES.items():
		if opts["--only"] and name != opts["--only"]:
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
		if opts["--only"] and name != opts["--only"]:
			continue
		reset_scene()
		build()
		path = os.path.abspath(os.path.join(opts["--out"], f"{name}.glb"))
		bpy.ops.object.select_all(action="SELECT")
		bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
								  export_animations=False, export_yup=True)
		print(f"exported {path}")


main()
