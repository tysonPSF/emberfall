"""Builds Emberfall's creature models (rigged, animated, low-poly) and exports GLBs.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/creatures.py -- --out assets/creatures [--preview DIR] [--only rat,bog_leech]

Each creature is primitives rigidly skinned to a few bones. Clips are named after
the game's actions (idle, walk, run, attack, hit, death) so CharacterModel can use
them directly (`"rig": "own"` in data/models.json). Creatures face -Y in Blender,
which exports as glTF +Z like the KayKit characters.

BODIES are KayKit character .glb copies with their palette texture repainted
(`repaint_kaykit`), for reskins a multiply tint can't reach (a purple robe
made saffron, a knight turned to stone); --only takes their names too.

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


# ---------------------------------------------------------------- wild boar (Harrowfield)

def build_boar():
	hide = material("boar_hide", "4e4038", 0.95)
	bristle = material("boar_bristle", "2a221e", 0.95)
	grizzle = material("boar_grizzle", "7a6a5c", 0.95)
	snout = material("boar_snout", "b89088", 0.7)
	dark = material("boar_dark", "1a1412", 0.5)
	tusk = material("boar_tusk", "e8dcc0", 0.4)
	eye = material("boar_eye", "c83a1a", 0.3, emit=0.8)
	b = Builder("boar")
	legs = {"leg_fl": (0.2, -0.42), "leg_fr": (-0.2, -0.42), "leg_bl": (0.19, 0.46), "leg_br": (-0.19, 0.46)}
	b.bone("root", (0, 0, 0.55))
	b.bone("body", (0, 0.0, 0.66), "root")
	b.bone("head", (0, -0.66, 0.74), "body")
	b.bone("jaw", (0, -0.9, 0.58), "head")
	b.bone("tail", (0, 0.78, 0.8), "body")

	b.blob((0.72, 1.45, 0.66), (0, 0.08, 0.66), hide, "body", segs=(14, 9))              # barrel
	b.blob((0.8, 0.74, 0.76), (0, -0.36, 0.76), hide, "body", segs=(12, 8))              # heavy shoulders
	b.blob((0.62, 0.6, 0.6), (0, 0.52, 0.68), hide, "body", segs=(10, 8))                # rump
	b.blob((0.5, 1.2, 0.26), (0, 0.02, 0.42), grizzle, "body", segs=(10, 6))             # paler belly
	b.blob((0.36, 1.1, 0.2), (0, -0.08, 1.03), bristle, "body", rot=(4, 0, 0), segs=(8, 6))  # dark spine stripe
	for k in range(9):   # the bristle ridge, tallest over the shoulders
		y = -0.62 + k * 0.14
		h = 0.2 - abs(y + 0.3) * 0.16
		z = 1.1 - max(0.0, y + 0.1) * 0.22
		for dx in (-0.05, 0.05):
			b.seg((dx, y, z - 0.08), (dx * 2.2, y + 0.1, z + h), 0.06, 0.008, bristle, "body", sides=4)
	b.blob((0.62, 0.56, 0.6), (0, -0.74, 0.78), hide, "head", segs=(12, 8))              # skull
	b.blob((0.52, 0.4, 0.24), (0, -0.66, 1.02), bristle, "head", segs=(8, 5))            # forelock
	b.seg((0, -0.9, 0.78), (0, -1.28, 0.62), 0.2, 0.13, hide, "head", sides=8)           # long snout
	b.seg((0, -1.27, 0.62), (0, -1.36, 0.6), 0.14, 0.14, snout, "head", sides=10)        # disc nose
	for s in (1, -1):
		b.blob((0.05, 0.03, 0.06), (0.05 * s, -1.37, 0.61), dark, "head", segs=(5, 3))    # nostrils
		b.blob((0.08, 0.06, 0.06), (0.2 * s, -0.94, 0.86), eye, "head", segs=(6, 4))
		b.blob((0.13, 0.07, 0.05), (0.2 * s, -0.95, 0.91), bristle, "head", rot=(0, -20 * s, 0))  # brow
		b.seg((0.2 * s, -0.66, 0.98), (0.3 * s, -0.6, 1.14), 0.08, 0.01, hide, "head", sides=4)  # small ears
		b.blob((0.2, 0.3, 0.3), (0.26 * s, -0.8, 0.66), grizzle, "head", segs=(8, 5))    # grizzled cheeks
		# curved tusks sweeping out and up from the lips
		b.seg((0.12 * s, -1.12, 0.52), (0.2 * s, -1.2, 0.62), 0.04, 0.035, tusk, "jaw", sides=5)
		b.seg((0.2 * s, -1.2, 0.62), (0.22 * s, -1.16, 0.76), 0.035, 0.008, tusk, "jaw", sides=5)
	b.seg((0, -0.86, 0.58), (0, -1.2, 0.5), 0.11, 0.06, grizzle, "jaw", sides=6)         # lower jaw
	b.seg((0, 0.78, 0.84), (0, 0.9, 0.62), 0.04, 0.025, hide, "tail", sides=5)          # short tail
	b.blob((0.08, 0.08, 0.14), (0, 0.92, 0.55), bristle, "tail", segs=(6, 4))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.58), "root")
		back = y > 0
		b.blob((0.26, 0.4 if back else 0.34, 0.42), (x * 1.05, y, 0.6), hide, name_, segs=(8, 6))   # ham / shoulder
		b.seg((x, y, 0.5), (x, y + (0.04 if back else 0.0), 0.22), 0.075, 0.05, hide, name_, sides=6)
		b.seg((x, y + (0.04 if back else 0.0), 0.22), (x, y - 0.01, 0.06), 0.045, 0.04, bristle, name_, sides=6)
		b.seg((x, y - 0.02, 0.07), (x, y - 0.04, 0.0), 0.055, 0.065, dark, name_, sides=6)   # hoof
	arm = b.build()

	def tail(t, amp, cycles=2.0):
		return {"tail": {"rot": (0, 0, amp * wave(t, cycles))}}

	def idle(t):  # snuffles at the ground now and then
		root = seq(t, [(0, 0), (0.35, 0), (0.5, 1), (0.7, 1), (0.85, 0)])
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))},
					  "head": {"rot": (-16 * root + 5 * root * wave(t, 8), 0, 6 * wave(t, 1, 0.1))},
					  "jaw": {"rot": (-4 * root * max(0.0, wave(t, 8)), 0, 0)}}, tail(t, 25, 3))

	def walk(t):
		return merge(_quad_legs(wave(t), 26), tail(t, 18), {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))},
															 "head": {"rot": (4 * wave(t, 2), 0, 3 * wave(t))}})

	def run(t):  # a stiff-legged charging gallop
		f, k = 38 * wave(t), 38 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.06 * max(0.0, wave(t, 1, 0.25))), "rot": (5 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-8, 0, 0)}}, tail(t, 10))

	def attack(t):  # head down, charge, then toss the tusks upward
		lunge = seq(t, [(0, 0), (0.25, -0.1), (0.45, 0.4), (0.62, 0.3), (1, 0)])
		head = seq(t, [(0, 0), (0.25, -22), (0.45, -26), (0.62, 30), (1, 0)])
		pitch = seq(t, [(0, 0), (0.25, -6), (0.45, -4), (0.62, 12), (1, 0)])
		hind = seq(t, [(0, 0), (0.25, 20), (0.45, -30), (0.62, -10), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0.06 * max(0.0, lunge)), "rot": (pitch, 0, 0)},
					  "head": {"rot": (head, 0, 0)}, "jaw": {"rot": (seq(t, [(0, 0), (0.5, 0), (0.62, -12), (0.9, 0)]), 0, 0)},
					  "leg_bl": {"rot": (hind, 0, 0)}, "leg_br": {"rot": (hind, 0, 0)},
					  "leg_fl": {"rot": (-hind * 0.6, 0, 0)}, "leg_fr": {"rot": (-hind * 0.5, 0, 0)}}, tail(t, 30, 3))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.03 * k), "rot": (8 * k, 4 * k, 0)},
					  "head": {"rot": (14 * k, 0, -12 * k)}, "jaw": {"rot": (-10 * k, 0, 0)}}, tail(t, 30 * k, 3))

	def death(t):  # a squealing stagger, then over onto its side
		roll = seq(t, [(0.2, 0), (0.62, 88), (0.74, 82), (0.86, 90)])
		drop = seq(t, [(0.2, 0), (0.62, -0.28)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		kick = 8 * wave(t, 4) * seq(t, [(0.6, 0), (0.72, 1), (1, 0)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.18, 12), (0.45, 0)]), roll, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.18, 20), (0.5, -8)]) * 1, 0, 14 * curl)},
					  "jaw": {"rot": (-12 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (26 * curl + kick, 0, 0)}, "leg_fr": {"rot": (12 * curl, 0, 0)},
					  "leg_bl": {"rot": (-22 * curl - kick, 0, 0)}, "leg_br": {"rot": (-10 * curl, 0, 0)}})

	clip(arm, "idle", 2.6, idle, True)
	clip(arm, "walk", 0.75, walk, True)
	clip(arm, "run", 0.42, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.2, death, False)
	return arm


# ---------------------------------------------------------------- brigands and scarecrows (Harrowfield)
# Bolt-ons for KayKit Rig_Medium bodies, in their mesh space like the gnoll's.

def _ring(b, center, radii, z_tilt, width, mat, sides=14, gap=None):
	"""A band of short segments round an ellipse, tipped `z_tilt` degrees about Y (roll) and X (pitch)."""
	cx, cy, cz = center
	rx, ry = radii
	roll, pitch = z_tilt
	rot = Euler((math.radians(pitch), math.radians(roll), 0)).to_matrix()
	pts = []
	for k in range(sides + 1):
		a = 2 * math.pi * k / sides
		p = rot @ Vector((rx * math.cos(a), ry * math.sin(a), 0))
		pts.append((cx + p.x, cy + p.y, cz + p.z))
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		if gap and gap[0] <= k < gap[1]:
			continue
		b.seg(p, q, width, width, mat, "x", sides=4)


def _tuft(b, root, direction, length, count, spread, mats, seed, width=0.022):
	"""A bristle of straw: thin cones fanning out of `root` along `direction`."""
	import random
	rng = random.Random(seed)
	d = Vector(direction).normalized()
	side = d.orthogonal().normalized()
	up = d.cross(side).normalized()
	for k in range(count):
		a = rng.uniform(0, 2 * math.pi)
		r = rng.uniform(0.2, 1.0) * spread
		v = (d + side * math.cos(a) * r + up * math.sin(a) * r).normalized()
		ln = length * rng.uniform(0.6, 1.15)
		start = Vector(root) + side * math.cos(a) * 0.03 + up * math.sin(a) * 0.03
		b.seg(tuple(start), tuple(start + v * ln), width, 0.003, mats[k % len(mats)], "x", sides=3)


def brigand_materials():
	return {
		"red": material("brigand_red", "8e2420", 0.85),
		"hood": material("brigand_hood", "4a3e34", 0.95),
		"hood_dark": material("brigand_hood_dark", "241c16", 0.95),
		"red_dark": material("brigand_red_dark", "5a1614", 0.9),
		"dot": material("brigand_dot", "c8b89a", 0.8),
		"leather": material("brigand_leather", "4a3424", 0.8),
		"leather_dark": material("brigand_leather_dark", "2c2018", 0.8),
		"buckle": material("brigand_buckle", "a08a5a", 0.4),
		"patch": material("brigand_patch", "141010", 0.5),
		"scar": material("brigand_scar", "a05a50", 0.7),
		"feather": material("brigand_feather", "2a2a2a", 0.8),
	}


def _shell(b, size, loc, mat, keep, segs=(16, 12)):
	"""An ellipsoid with the faces `keep(direction)` rejects cut away (a hood's face opening)."""
	bm = bmesh.new()
	bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=0.5)
	cut = [f for f in bm.faces if not keep(f.calc_center_median().normalized())]
	bmesh.ops.delete(bm, geom=cut, context="FACES")
	m = Matrix.LocRotScale(Vector(loc), None, Vector(size))
	bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
	edge = [(tuple(e.verts[0].co), tuple(e.verts[1].co)) for e in bm.edges if len(e.link_faces) == 1]
	b._add(bm, mat, "x")
	return edge  # the cut's rim


def _slab(b, pts, thick, mat):
	"""A flat plate of `thick` through the (convex, planar) polygon `pts`: kerchief points, torn cloth."""
	vs = [Vector(p) for p in pts]
	n = (vs[1] - vs[0]).cross(vs[2] - vs[0]).normalized() * (thick / 2)
	bm = bmesh.new()
	front = [bm.verts.new(v + n) for v in vs]
	back = [bm.verts.new(v - n) for v in vs]
	bm.faces.new(front)
	bm.faces.new(list(reversed(back)))
	for k in range(len(vs)):
		j = (k + 1) % len(vs)
		bm.faces.new((front[j], front[k], back[k], back[j]))
	b._add(bm, mat, "x")


def build_brigand_hood():
	"""A dirty hood and a red kerchief over the nose and mouth, for a KayKit ranger head."""
	m = brigand_materials()
	b = Builder("brigand_hood")
	# the hood: a shell round the head with an oval cut for the face, a point
	# falling behind and a ragged cowl over the shoulders
	opening = lambda d: not (d.y < -0.5 and -0.8 < d.z < 0.1 and abs(d.x) < 0.58)
	rim = _shell(b, (1.28, 1.38, 1.3), (0, -0.04, 1.8), m["hood"], opening, segs=(20, 14))
	for p, q in rim:   # a thick folded edge round the face
		if p[1] < -0.2:
			b.seg(p, q, 0.05, 0.05, m["hood"], "x", sides=5)
	_shell(b, (1.24, 1.34, 1.26), (0, -0.04, 1.8), m["hood_dark"], opening, segs=(20, 14))   # darker lining, seen round the face
	b.seg((0, 0.2, 2.3), (0, 0.62, 2.3), 0.3, 0.14, m["hood"], "x", sides=8)                 # the point falling behind
	b.seg((0, 0.62, 2.3), (0, 0.86, 2.0), 0.14, 0.02, m["hood"], "x", sides=8)
	b.blob((0.28, 0.28, 0.28), (0, 0.62, 2.3), m["hood"], "x", segs=(8, 5))
	_shell(b, (1.12, 1.02, 0.6), (0, 0.04, 1.12), m["hood"], lambda d: d.z > 0.0)          # cowl over the shoulders
	for k in range(14):
		a = 2 * math.pi * (k + 0.5) / 14
		x, y = 0.55 * math.cos(a), 0.04 + 0.5 * math.sin(a)
		if abs(x) < 0.2 and y < 0:
			continue
		out = Vector((x, y - 0.04, 0)).normalized()
		w = Vector((-out.y, out.x, 0)) * 0.13
		c = Vector((x, y, 1.13))
		tip = c + out * 0.05 + Vector((0, 0, -0.14 - 0.05 * (k % 2)))
		_slab(b, [tuple(c - w), tuple(c + w), tuple(tip)], 0.03, m["hood"])                   # ragged edge
	# the kerchief
	b.seg((0, -0.04, 1.26), (0, -0.04, 1.6), 0.46, 0.49, m["red"], "x", sides=14)
	_slab(b, [(-0.3, -0.5, 1.4), (0.3, -0.5, 1.4), (0.02, -0.6, 1.04)], 0.04, m["red"])     # the point hanging over the chin
	_ring(b, (0, -0.04, 1.595), (0.49, 0.49), (0, 0), 0.022, m["red_dark"], sides=14)       # hem
	for x, z in ((-0.26, 1.5), (0.02, 1.56), (0.28, 1.48), (-0.3, 1.34), (0.3, 1.34)):     # a few pale spots
		r = 0.46 + (z - 1.26) * 0.09 + 0.01
		b.blob((0.06, 0.03, 0.06), (x, -0.04 - math.sqrt(max(0.0, r * r - x * x)), z), m["dot"], "x", segs=(5, 3))
	b.blob((0.06, 0.03, 0.06), (0.0, -0.575, 1.24), m["dot"], "x", segs=(5, 3))
	return b.build_static()


def build_brigand_captain_hat():
	"""A broad slouch hat with a red band, an eye patch and a scar, for a KayKit barbarian head."""
	m = brigand_materials()
	b = Builder("brigand_captain_hat")
	b.seg((0, 0.02, 2.0), (0, 0.02, 2.06), 0.86, 0.84, m["leather"], "x", sides=16)       # brim
	b.blob((0.5, 1.1, 0.12), (0.62, 0.02, 2.16), m["leather"], "x", rot=(0, -58, 0), segs=(8, 5))   # brim turned up on the left
	b.seg((0, 0.02, 2.02), (0, 0.04, 2.44), 0.52, 0.42, m["leather_dark"], "x", sides=12)  # crown
	b.blob((0.84, 0.7, 0.2), (0, 0.04, 2.44), m["leather_dark"], "x", segs=(10, 5))
	b.blob((0.12, 0.6, 0.1), (0, 0.04, 2.52), m["leather"], "x", segs=(6, 4))             # dented top
	b.seg((0, 0.02, 2.05), (0, 0.025, 2.18), 0.535, 0.515, m["red"], "x", sides=12)        # red band
	b.blob((0.12, 0.1, 0.12), (0.5, -0.12, 2.12), m["buckle"], "x", segs=(6, 4))
	b.seg((0.52, -0.1, 2.14), (0.72, 0.26, 2.66), 0.05, 0.01, m["feather"], "x", sides=4)  # black feather
	b.seg((0.6, 0.06, 2.4), (0.72, 0.26, 2.66), 0.07, 0.01, m["red_dark"], "x", sides=4)
	# eye patch over the right eye, strap slanting up over the head
	b.blob((0.22, 0.08, 0.2), (-0.2, -0.5, 1.64), m["patch"], "x", segs=(8, 5))
	_ring(b, (0, -0.02, 1.8), (0.54, 0.51), (-24, 0), 0.022, m["patch"], sides=16, gap=(12, 16))
	def face(x, z):
		return (x, -0.02 - 0.5 * math.sqrt(max(0.0, 1 - (x / 0.56) ** 2)) - 0.01, z)
	pts = [face(0.26, 1.86), face(0.33, 1.72), face(0.38, 1.58), face(0.4, 1.46)]
	for p, q in zip(pts, pts[1:]):   # a long scar down the left cheek, with stitch marks
		b.seg(p, q, 0.022, 0.022, m["scar"], "x", sides=4)
	for x, z in ((0.3, 1.8), (0.355, 1.65), (0.39, 1.52)):
		b.seg(face(x - 0.05, z - 0.01), face(x + 0.05, z + 0.01), 0.012, 0.012, m["scar"], "x", sides=3)
	return b.build_static()


def scarecrow_materials():
	return {
		"sack": material("scarecrow_sack", "a38a62", 0.95),
		"sack_dark": material("scarecrow_sack_dark", "6e5a3c", 0.95),
		"stitch": material("scarecrow_stitch", "1e1712", 0.8),
		"straw": material("scarecrow_straw", "d9b858", 0.9),
		"straw_dark": material("scarecrow_straw_dark", "a4843a", 0.9),
		"hat": material("scarecrow_hat", "b89448", 0.95),
		"hat_dark": material("scarecrow_hat_dark", "7a5e2c", 0.95),
		"band": material("scarecrow_band", "3a2a22", 0.9),
		"rope": material("scarecrow_rope", "8a7248", 0.9),
		"patch_a": material("scarecrow_patch_a", "6a3a2e", 0.95),
		"patch_b": material("scarecrow_patch_b", "4e5a3a", 0.95),
		"patch_c": material("scarecrow_patch_c", "5e6a7a", 0.95),
		"glow": material("scarecrow_glow", "ff8a22", 0.3, emit=3.0),
		"crow": material("scarecrow_crow", "1c1a20", 0.6),
		"crow_sheen": material("scarecrow_crow_sheen", "2e3448", 0.5),
		"beak": material("scarecrow_beak", "3a3630", 0.5),
		"crow_eye": material("scarecrow_crow_eye", "e8e0c0", 0.3, emit=1.0),
	}


def _sack_head(b, m, tall=1.0, elder=False):
	"""A burlap sack pulled over the head and tied at the neck, with a stitched face."""
	cz = 1.66
	b.blob((0.98, 0.92, 1.0 * tall), (0, 0.0, cz), m["sack"], "x", segs=(12, 9))
	b.blob((0.5, 0.4, 0.3), (0.2, 0.12, cz + 0.42 * tall), m["sack"], "x", rot=(0, 20, 0), segs=(8, 5))   # lumpy crown
	b.seg((0, 0, 1.18), (0, 0, 1.3), 0.34, 0.3, m["sack"], "x", sides=10)                   # gathered neck
	b.seg((0, 0, 1.08), (0, 0, 1.18), 0.44, 0.34, m["sack_dark"], "x", sides=10)            # flared hem
	_ring(b, (0, 0, 1.27), (0.32, 0.32), (0, 0), 0.035, m["rope"], sides=12)                 # the tie
	b.seg((0.1, -0.3, 1.26), (0.16, -0.38, 1.08), 0.03, 0.02, m["rope"], "x", sides=4)
	b.seg((0.08, -0.3, 1.26), (0.02, -0.38, 1.1), 0.03, 0.02, m["rope"], "x", sides=4)
	face = -0.46
	for s in (1, -1):
		ex, ez = 0.21 * s, cz + 0.06
		if elder:   # hollow button eyes with an ember deep in them
			b.seg((ex, face + 0.03, ez), (ex, face - 0.02, ez), 0.11, 0.11, m["stitch"], "x", sides=10)
			b.blob((0.07, 0.04, 0.07), (ex, face - 0.03, ez), m["glow"], "x", segs=(6, 4))
			for a in (45, 135):
				c, d = math.cos(math.radians(a)) * 0.14, math.sin(math.radians(a)) * 0.14
				b.seg((ex - c, face + 0.02, ez - d), (ex + c, face + 0.02, ez + d), 0.012, 0.012, m["sack_dark"], "x", sides=3)
		else:       # stitched X eyes, a faint glow showing through the weave
			b.blob((0.2, 0.04, 0.18), (ex, face + 0.03, ez), m["glow"], "x", segs=(6, 4))
			for a in (45, 135):
				c, d = math.cos(math.radians(a)) * 0.11, math.sin(math.radians(a)) * 0.11
				b.seg((ex - c, face - 0.005, ez - d), (ex + c, face - 0.005, ez + d), 0.028, 0.028, m["stitch"], "x", sides=4)
	# a wide stitched grin: a curved seam with cross stitches
	pts = []
	for k in range(9):
		u = (k - 4) / 4.0
		x = 0.3 * u
		z = cz - 0.2 + 0.07 * u * u + (0.02 if k % 2 else 0.0) * (1 if elder else 0)
		y = face + 0.02 + 0.1 * u * u
		pts.append((x, y, z))
	for p, q in zip(pts, pts[1:]):
		b.seg(p, q, 0.018, 0.018, m["stitch"], "x", sides=4)
	for p in pts[1:-1]:
		b.seg((p[0], p[1] - 0.005, p[2] + 0.06), (p[0], p[1] - 0.005, p[2] - 0.06), 0.014, 0.014, m["stitch"], "x", sides=3)
	b.blob((0.2, 0.12, 0.08), (-0.24, face + 0.06, cz + 0.3), m["sack_dark"], "x", rot=(0, 20, 0), segs=(6, 4))  # a darned patch
	for x, z in ((-0.33, cz + 0.3), (-0.15, cz + 0.3)):
		b.seg((x, face + 0.04, z - 0.05), (x, face + 0.04, z + 0.05), 0.01, 0.01, m["stitch"], "x", sides=3)
	_tuft(b, (0, 0.04, 1.14), (0, 0, -1), 0.24, 22, 1.6, [m["straw"], m["straw_dark"]], 3)   # straw spilling from the neck


def build_scarecrow_head():
	m = scarecrow_materials()
	b = Builder("scarecrow_head")
	_sack_head(b, m)
	# floppy straw hat, tipped over one eye
	tilt = Matrix.Translation((0, 0, 2.02)) @ Euler((math.radians(-10), math.radians(8), 0)).to_matrix().to_4x4()
	hat = Builder("tmp")
	hat.seg((0, 0, 0.0), (0, 0, 0.05), 0.78, 0.74, m["hat"], "x", sides=14)                # brim
	hat.blob((0.5, 1.1, 0.14), (0.58, 0, -0.04), m["hat"], "x", rot=(0, 28, 0), segs=(8, 5))   # a drooping side of the brim
	hat.seg((0, 0, 0.02), (0.02, 0.02, 0.38), 0.44, 0.34, m["hat"], "x", sides=12)          # crown
	hat.blob((0.64, 0.6, 0.16), (0.02, 0.02, 0.38), m["hat_dark"], "x", segs=(8, 5))
	hat.seg((0, 0, 0.04), (0.005, 0.005, 0.13), 0.45, 0.43, m["band"], "x", sides=12)
	_tuft(hat, (0.1, -0.2, 0.4), (0.4, -0.3, 1), 0.16, 6, 0.6, [m["straw"], m["straw_dark"]], 9)  # straw poking through a hole
	for k in range(10):   # ragged brim ends
		a = 2 * math.pi * k / 10
		x, y = 0.74 * math.cos(a), 0.74 * math.sin(a)
		hat.seg((x, y, 0.02), (x * 1.12, y * 1.12, -0.04 - 0.03 * (k % 3)), 0.035, 0.005, m["hat_dark"], "x", sides=3)
	for p in hat.parts:
		p.data.transform(tilt)
	b.parts.extend(hat.parts)
	return b.build_static()


def build_scarecrow_head_elder():
	m = scarecrow_materials()
	b = Builder("scarecrow_head_elder")
	_sack_head(b, m, tall=1.08, elder=True)
	# a huge, tattered, crooked hat
	tilt = Matrix.Translation((0, 0.02, 2.06)) @ Euler((math.radians(-6), math.radians(-10), 0)).to_matrix().to_4x4()
	hat = Builder("tmp")
	hat.seg((0, 0, 0.0), (0, 0, 0.05), 0.98, 0.94, m["hat"], "x", sides=11)                # wide brim
	hat.blob((0.6, 1.3, 0.14), (0.72, 0, -0.08), m["hat"], "x", rot=(0, 30, 0), segs=(8, 5))   # a side sagging down
	for k in range(13):   # torn strips hanging off the brim
		a = 2 * math.pi * k / 13 + 0.2
		x, y = 0.93 * math.cos(a), 0.93 * math.sin(a)
		drop = 0.1 + 0.08 * ((k * 5) % 3)
		hat.seg((x, y, 0.02), (x * 1.1, y * 1.1, -drop), 0.07, 0.01, m["hat_dark"] if k % 2 else m["hat"], "x", sides=3)
	crown = [((0, 0, 0.0), 0.46), ((0.02, 0.02, 0.4), 0.36), ((0.12, 0.04, 0.7), 0.22), ((0.34, 0.06, 0.86), 0.11), ((0.56, 0.06, 0.74), 0.02)]
	for (p, r0), (q, r1) in zip(crown, crown[1:]):   # a tall crown, bent over at the tip
		hat.seg(p, q, r0, r1, m["hat"], "x", sides=10)
		hat.blob((r1 * 2, r1 * 2, r1 * 2), q, m["hat"], "x", segs=(8, 5))
	hat.seg((0, 0, 0.03), (0.005, 0.003, 0.14), 0.47, 0.45, m["band"], "x", sides=10)
	hat.blob((0.2, 0.12, 0.14), (-0.1, -0.4, 0.3), m["patch_a"], "x", rot=(-12, 0, 0), segs=(6, 4))  # patch on the crown
	_tuft(hat, (0.3, 0.25, 0.1), (0.5, 0.6, 0.6), 0.2, 6, 0.6, [m["straw"], m["straw_dark"]], 21)
	for p in hat.parts:
		p.data.transform(tilt)
	b.parts.extend(hat.parts)
	return b.build_static()


def build_scarecrow_chest():
	"""Straw bursting from the collar and patches sewn on a KayKit coat."""
	m = scarecrow_materials()
	b = Builder("scarecrow_chest")
	straw = [m["straw"], m["straw_dark"]]
	for k, (x, y) in enumerate(((0.2, -0.24), (-0.2, -0.24), (0.3, 0.1), (-0.3, 0.1), (0.0, 0.3), (0.0, -0.3))):
		_tuft(b, (x * 0.8, y * 0.8, 1.26), (x, y, 0.55), 0.22, 7, 0.7, straw, 40 + k)
	for loc, size, rot, mat in (((0.2, -0.4, 0.95), (0.22, 0.06, 0.2), (0, 0, 8), m["patch_a"]),
								((-0.18, -0.37, 0.7), (0.18, 0.06, 0.2), (0, 0, -12), m["patch_b"]),
								((-0.28, 0.36, 1.0), (0.24, 0.06, 0.22), (0, 0, 10), m["patch_c"])):
		b.blob(size, loc, mat, "x", rot=rot, segs=(6, 3))
	return b.build_static()


def build_scarecrow_hips():
	"""A rope belt with straw hanging out all round the waist."""
	m = scarecrow_materials()
	b = Builder("scarecrow_hips")
	_ring(b, (0, 0, 0.66), (0.47, 0.41), (0, 0), 0.04, m["rope"], sides=14)
	b.blob((0.1, 0.08, 0.1), (0.2, -0.43, 0.66), m["rope"], "x", segs=(6, 4))
	b.seg((0.2, -0.44, 0.64), (0.24, -0.46, 0.44), 0.03, 0.02, m["rope"], "x", sides=4)
	for k in range(10):
		a = math.radians(k * 36 + 18)
		x, y = 0.46 * math.cos(a), 0.4 * math.sin(a)
		if abs(x) < 0.16 and y < 0:   # keep the front clear over the legs' stride
			continue
		_tuft(b, (x, y, 0.62), (x * 0.8, y * 0.8, -1), 0.24, 5, 0.5, [m["straw"], m["straw_dark"]], 60 + k)
	return b.build_static()


def _cuff(side):
	m = scarecrow_materials()
	b = Builder(f"scarecrow_cuff_{side}")
	s = 1 if side == "l" else -1
	_tuft(b, (0.74 * s, 0, 1.1), (s, 0, -0.15), 0.2, 11, 1.2, [m["straw"], m["straw_dark"]], 80 if side == "l" else 81, width=0.025)
	return b.build_static()


def build_scarecrow_cuff_l():
	return _cuff("l")


def build_scarecrow_cuff_r():
	return _cuff("r")


def build_scarecrow_crow():
	"""A crow perched on the left shoulder."""
	m = scarecrow_materials()
	b = Builder("scarecrow_crow")
	x, y, z = 0.5, 0.06, 1.24
	b.blob((0.2, 0.34, 0.24), (x, y, z + 0.14), m["crow"], "x", rot=(-20, 0, 0), segs=(8, 6))     # body
	b.blob((0.18, 0.18, 0.18), (x, y - 0.16, z + 0.3), m["crow"], "x", segs=(8, 6))            # head
	b.seg((x, y - 0.24, z + 0.3), (x, y - 0.38, z + 0.27), 0.045, 0.005, m["beak"], "x", sides=4)
	for s in (1, -1):
		b.blob((0.06, 0.34, 0.16), (x + 0.1 * s, y + 0.04, z + 0.15), m["crow_sheen"], "x", rot=(-18, 0, 0), segs=(6, 4))   # folded wings
		b.blob((0.035, 0.03, 0.035), (x + 0.07 * s, y - 0.22, z + 0.33), m["crow_eye"], "x", segs=(5, 3))
		b.seg((x + 0.04 * s, y, z + 0.04), (x + 0.04 * s, y - 0.02, z - 0.04), 0.012, 0.01, m["beak"], "x", sides=3)   # legs
	b.seg((x, y + 0.14, z + 0.1), (x, y + 0.36, z - 0.02), 0.07, 0.02, m["crow"], "x", sides=4)   # tail
	return b.build_static()


# ---------------------------------------------------------------- mountain ram (Sunward Steps)

def _horn(b, s, mats, bone, base=(0.24, -0.6, 1.14), r=(0.19, 0.075), x=(0.13, 0.36), turns=1.05, thick=(0.085, 0.018)):
	"""A ram's horn: a ridged tube curling back, down and forward round the ear (s = side)."""
	cx, cy, cz = base
	n = 18
	pts = []
	for k in range(n + 1):
		u = k / n
		th = 2 * math.pi * turns * u
		rad = r[0] + (r[1] - r[0]) * u
		pts.append(((x[0] + (x[1] - x[0]) * u) * s, cy + rad * math.sin(th), cz + rad * math.cos(th)))
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		t0, t1 = thick[0] + (thick[1] - thick[0]) * k / n, thick[0] + (thick[1] - thick[0]) * (k + 1) / n
		b.seg(p, q, t0, t1, mats[k % 2], bone, sides=7)
		b.blob((t1 * 2.1, t1 * 2.1, t1 * 2.1), q, mats[k % 2], bone, segs=(7, 5))   # a ridge at every joint


def build_ram():
	fleece = material("ram_fleece", "e4d6b4", 0.95)
	shade = material("ram_fleece_shade", "c6b28c", 0.95)
	tan = material("ram_tan", "a88c64", 0.95)
	face = material("ram_face", "3e3229", 0.85)
	leg = material("ram_leg", "4a3c31", 0.9)
	hoof = material("ram_hoof", "1c1714", 0.5)
	horn = material("ram_horn", "cbb892", 0.6)
	horn_dark = material("ram_horn_dark", "8e7c5e", 0.7)
	nose = material("ram_nose", "1e1916", 0.4)
	eye = material("ram_eye", "d89a2a", 0.3, emit=0.8)
	b = Builder("mountain_ram")
	legs = {"leg_fl": (0.19, -0.44), "leg_fr": (-0.19, -0.44), "leg_bl": (0.18, 0.46), "leg_br": (-0.18, 0.46)}
	b.bone("root", (0, 0, 0.62))
	b.bone("body", (0, 0.0, 0.84), "root")
	b.bone("head", (0, -0.56, 1.0), "body")
	b.bone("tail", (0, 0.74, 0.96), "body")

	b.blob((0.74, 1.36, 0.66), (0, 0.04, 0.88), fleece, "body", segs=(14, 9))           # woolly barrel
	b.blob((0.6, 1.1, 0.3), (0, 0.04, 0.6), shade, "body", segs=(10, 6))               # shaded belly
	b.blob((0.7, 0.56, 0.7), (0, -0.4, 0.86), fleece, "body", segs=(10, 8))             # chest
	b.blob((0.52, 0.42, 0.52), (0, -0.52, 0.74), shade, "body", segs=(8, 6))           # chest ruff
	for k, (x, y, z) in enumerate(((0.18, -0.28, 1.12), (-0.18, -0.24, 1.13), (0.0, -0.04, 1.17), (0.22, 0.08, 1.1),
									(-0.22, 0.12, 1.11), (0.02, 0.3, 1.15), (0.22, 0.4, 1.04), (-0.2, 0.42, 1.05),
									(0.34, -0.14, 0.9), (-0.34, -0.1, 0.91), (0.35, 0.22, 0.88), (-0.35, 0.26, 0.87),
									(0.0, 0.56, 0.98), (0.3, -0.34, 0.72), (-0.3, -0.32, 0.72), (0.3, 0.46, 0.7),
									(-0.3, 0.44, 0.7), (0.34, 0.04, 0.68), (-0.34, 0.06, 0.68))):
		# shaggy locks of fleece, sunk into the barrel so they read as clumps rather than balls
		b.blob((0.3, 0.34, 0.2), (x, y, z), fleece if k % 3 else shade, "body", rot=(8 * (k % 3 - 1), 30 * x, k * 23), segs=(7, 4))
	for k in range(7):   # heavier locks hanging along the flanks
		y = -0.3 + k * 0.12
		for s in (1, -1):
			b.blob((0.12, 0.16, 0.26), (0.33 * s, y, 0.56 - 0.02 * (k % 2)), shade if (k + (s > 0)) % 2 else fleece, "body",
				   rot=(0, -8 * s, 0), segs=(6, 4))
	b.seg((0, -0.44, 0.94), (0, -0.66, 1.12), 0.22, 0.16, fleece, "head", sides=8)       # woolly neck
	b.blob((0.36, 0.42, 0.38), (0, -0.74, 1.16), face, "head", segs=(10, 7))            # skull
	b.blob((0.34, 0.3, 0.16), (0, -0.66, 1.34), fleece, "head", segs=(8, 5))             # wool cap between the horns
	b.seg((0, -0.84, 1.14), (0, -1.06, 1.0), 0.15, 0.1, face, "head", sides=8)           # long muzzle
	b.blob((0.18, 0.1, 0.12), (0, -1.07, 1.0), nose, "head", segs=(6, 4))
	b.seg((0, -0.86, 1.04), (0, -1.02, 0.94), 0.08, 0.05, face, "head", sides=6)         # chin
	for s in (1, -1):
		b.blob((0.07, 0.05, 0.05), (0.16 * s, -0.86, 1.2), eye, "head", segs=(6, 4))
		b.blob((0.12, 0.06, 0.04), (0.16 * s, -0.87, 1.24), face, "head", rot=(0, 18 * s, 0), segs=(6, 3))   # brow
		b.seg((0.16 * s, -0.66, 1.1), (0.32 * s, -0.66, 1.02), 0.06, 0.02, face, "head", sides=5)            # ears
		_horn(b, s, (horn, horn_dark), "head", base=(0.27, -0.6, 1.1), r=(0.26, 0.09), x=(0.12, 0.4), turns=1.1, thick=(0.11, 0.022))
	b.seg((0, 0.74, 0.98), (0, 0.84, 0.86), 0.09, 0.06, fleece, "tail", sides=6)         # stubby tail
	b.blob((0.16, 0.14, 0.18), (0, 0.86, 0.82), shade, "tail", segs=(6, 4))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.62), "root")
		back = y > 0
		b.blob((0.26, 0.36, 0.38), (x * 1.05, y, 0.64), fleece, name_, segs=(8, 6))        # woolly thigh / shoulder
		b.seg((x, y, 0.5), (x, y + (0.04 if back else 0.0), 0.28), 0.07, 0.055, leg, name_, sides=6)
		b.blob((0.11, 0.11, 0.1), (x, y + (0.04 if back else 0.0), 0.28), leg, name_, segs=(6, 4))     # knobbly knee
		b.seg((x, y + (0.04 if back else 0.0), 0.28), (x, y - 0.01, 0.08), 0.05, 0.042, leg, name_, sides=6)
		b.seg((x, y - 0.02, 0.09), (x, y - 0.04, 0.0), 0.05, 0.062, hoof, name_, sides=6)   # hoof
	arm = b.build()

	def tail(t, amp, cycles=2.0):
		return {"tail": {"rot": (0, 0, amp * wave(t, cycles))}}

	def idle(t):  # grazes, then lifts its head to look round
		graze = seq(t, [(0, 0), (0.2, 0), (0.32, 1), (0.62, 1), (0.74, 0)])
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))},
					  "head": {"rot": (-34 * graze + 3 * graze * wave(t, 6), 0, seq(t, [(0.74, 0), (0.84, 14), (0.95, 0)]))}},
					 tail(t, 18, 3))

	def walk(t):
		return merge(_quad_legs(wave(t), 26), tail(t, 12), {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))},
															 "head": {"rot": (4 * wave(t, 2), 0, 3 * wave(t))}})

	def run(t):  # a bounding mountain gallop
		f, k = 40 * wave(t), 40 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.08 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-6, 0, 0)}}, tail(t, 8))

	def attack(t):  # rears, drops its head and butts
		lunge = seq(t, [(0, 0), (0.28, -0.14), (0.46, 0.46), (0.6, 0.38), (1, 0)])
		pitch = seq(t, [(0, 0), (0.28, 14), (0.46, -8), (0.6, -4), (1, 0)])
		head = seq(t, [(0, 0), (0.28, 8), (0.46, -42), (0.6, -34), (0.78, 4), (1, 0)])
		hind = seq(t, [(0, 0), (0.28, 16), (0.46, -30), (0.6, -12), (1, 0)])
		front = seq(t, [(0, 0), (0.28, 30), (0.46, -18), (0.6, -8), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0.08 * max(0.0, pitch / 14)), "rot": (pitch, 0, 0)},
					  "head": {"rot": (head, 0, 0)},
					  "leg_bl": {"rot": (hind, 0, 0)}, "leg_br": {"rot": (hind, 0, 0)},
					  "leg_fl": {"rot": (front, 0, 0)}, "leg_fr": {"rot": (front * 0.8, 0, 0)}}, tail(t, 20, 3))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.03 * k), "rot": (8 * k, 4 * k, 0)},
					  "head": {"rot": (16 * k, 0, -12 * k)}}, tail(t, 24 * k, 3))

	def death(t):  # buckles at the knees and falls onto its side
		roll = seq(t, [(0.2, 0), (0.62, 88), (0.74, 82), (0.86, 90)])
		drop = seq(t, [(0.1, 0), (0.3, -0.1), (0.62, -0.3)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		kick = 8 * wave(t, 4) * seq(t, [(0.6, 0), (0.72, 1), (1, 0)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.25, -10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.2, 16), (0.6, -10)]), 0, 16 * curl)}},
					 {"leg_fl": {"rot": (seq(t, [(0, 0), (0.25, 40), (0.6, 24)]) + kick, 0, 0)},
					  "leg_fr": {"rot": (seq(t, [(0, 0), (0.25, 40), (0.6, 12)]), 0, 0)},
					  "leg_bl": {"rot": (-22 * curl - kick, 0, 0)}, "leg_br": {"rot": (-10 * curl, 0, 0)}})

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 0.8, walk, True)
	clip(arm, "run", 0.44, run, True)
	clip(arm, "attack", 0.75, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.2, death, False)
	return arm


# ---------------------------------------------------------------- sunhawk (Sunward Steps)
# A giant hawk that stalks and hops on the ground. Its wings are flat plates
# folded along its sides; a wing spreads by pitching up and yawing out, so the
# plate turns to face forward.

def build_sunhawk():
	gold = material("hawk_gold", "c88e3c", 0.85)
	brown = material("hawk_brown", "8a5a26", 0.9)
	dark = material("hawk_dark", "4e3218", 0.9)
	cream = material("hawk_cream", "ecd6a2", 0.9)
	streak = material("hawk_streak", "a8702e", 0.9)
	orange = material("hawk_orange", "e87a1c", 0.8)
	tip = material("hawk_tip", "f4b830", 0.7)
	cere = material("hawk_cere", "e8b42c", 0.6)
	beak = material("hawk_beak", "35302b", 0.4)
	eye = material("hawk_eye", "f4a818", 0.3, emit=1.0)
	pupil = material("hawk_pupil", "100c08", 0.2)
	b = Builder("sunhawk")
	b.bone("root", (0, 0, 0.72))
	b.bone("body", (0, 0.0, 0.84), "root")
	b.bone("neck", (0, -0.28, 1.22), "body")
	b.bone("head", (0, -0.36, 1.44), "neck")
	b.bone("tail", (0, 0.36, 0.8), "body")
	b.bone("leg_l", (0.18, 0.04, 0.7), "root")
	b.bone("leg_r", (-0.18, 0.04, 0.7), "root")
	b.bone("wing_l", (0.3, -0.2, 1.2), "body")
	b.bone("wing_r", (-0.3, -0.2, 1.2), "body")

	b.blob((0.8, 1.02, 0.86), (0, 0.04, 0.98), brown, "body", rot=(-40, 0, 0), segs=(14, 10))   # big body, chest up
	b.blob((0.62, 0.5, 0.72), (0, -0.2, 0.98), cream, "body", rot=(-24, 0, 0), segs=(12, 8))    # pale breast
	for k, (x, z) in enumerate(((0.1, 1.12), (-0.12, 1.04), (0.0, 0.92), (0.2, 0.9), (-0.2, 1.14), (0.04, 1.24),
								(-0.06, 0.8), (0.16, 0.78), (-0.2, 0.9))):   # teardrop streaks
		y = -0.44 - 0.04 * (1 - abs(x) / 0.25)
		b.blob((0.05, 0.03, 0.1), (x, y, z), streak, "body", segs=(5, 3))
	b.blob((0.62, 0.56, 0.4), (0, 0.1, 1.28), dark, "body", rot=(-32, 0, 0), segs=(10, 6))     # dark mantle
	b.blob((0.46, 0.46, 0.44), (0, -0.28, 1.34), gold, "neck", segs=(10, 7))                    # ruffed neck
	b.blob((0.5, 0.54, 0.46), (0, -0.4, 1.52), gold, "head", segs=(12, 8))                      # head
	b.blob((0.4, 0.46, 0.18), (0, -0.34, 1.72), streak, "head", segs=(8, 5))                   # darker crown
	b.seg((0, -0.62, 1.52), (0, -0.68, 1.51), 0.11, 0.095, cere, "head", sides=8)               # yellow cere
	b.seg((0, -0.68, 1.52), (0, -0.84, 1.49), 0.09, 0.055, beak, "head", sides=7)               # beak
	b.seg((0, -0.84, 1.49), (0, -0.89, 1.37), 0.055, 0.008, beak, "head", sides=6)              # the hook
	b.seg((0, -0.66, 1.45), (0, -0.8, 1.44), 0.05, 0.02, beak, "head", sides=5)                 # lower mandible
	for s in (1, -1):
		b.blob((0.11, 0.08, 0.11), (0.17 * s, -0.6, 1.57), eye, "head", segs=(8, 5))
		b.blob((0.05, 0.03, 0.06), (0.185 * s, -0.64, 1.57), pupil, "head", segs=(5, 3))
		b.blob((0.2, 0.1, 0.06), (0.16 * s, -0.62, 1.64), dark, "head", rot=(0, -22 * s, 0), segs=(6, 3))  # stern brow
		b.blob((0.1, 0.26, 0.1), (0.2 * s, -0.46, 1.48), dark, "head", segs=(6, 4))              # dark eye stripe
		w = f"wing_{'l' if s > 0 else 'r'}"
		x = 0.38 * s
		# a flat plate along the side: coverts, then long flight feathers sweeping back past the tail
		b.blob((0.14, 0.7, 0.62), (x, 0.04, 1.02), brown, w, rot=(-30, 0, 0), segs=(8, 6))
		b.blob((0.12, 0.42, 0.3), (x * 1.04, -0.12, 1.14), gold, w, rot=(-30, 0, 0), segs=(7, 5))
		for k in range(6):   # flight feathers, gold then orange toward the tips
			y0, z0 = 0.0 + k * 0.05, 0.98 - k * 0.06
			ln = 0.9 - k * 0.08
			ang = math.radians(36 + k * 5)
			d = Vector((0, math.cos(ang), -math.sin(ang)))
			a = Vector((x * (1.0 + 0.015 * k), y0, z0))
			m_ = a + d * ln * 0.55
			e = a + d * ln
			b.seg(tuple(a), tuple(m_), 0.085, 0.075, brown if k < 3 else dark, w, sides=4)
			b.seg(tuple(m_), tuple(e), 0.075, 0.015, orange if k % 2 else tip, w, sides=4)
	for k in range(7):   # a long tail fan, banded, with bright tips
		yaw = (k - 3) * 9
		d = Vector((math.sin(math.radians(yaw)), math.cos(math.radians(yaw)) * math.cos(math.radians(34)), -math.sin(math.radians(34))))
		a = Vector((0, 0.3, 0.84))
		b.seg(tuple(a), tuple(a + d * 0.46), 0.08, 0.08, brown, "tail", sides=4)
		b.seg(tuple(a + d * 0.46), tuple(a + d * 0.54), 0.08, 0.08, dark, "tail", sides=4)
		b.seg(tuple(a + d * 0.54), tuple(a + d * 0.76), 0.08, 0.02, orange if k % 2 else tip, "tail", sides=4)
	for s in (1, -1):
		leg = f"leg_{'l' if s > 0 else 'r'}"
		x = 0.18 * s
		b.blob((0.32, 0.36, 0.44), (x, 0.02, 0.66), gold, leg, segs=(8, 6))                       # feathered "trousers"
		b.blob((0.24, 0.26, 0.18), (x, 0.0, 0.46), streak, leg, segs=(7, 5))
		b.seg((x, 0.0, 0.44), (x, -0.02, 0.08), 0.065, 0.055, cere, leg, sides=6)                # thick scaly shank
		for dx, dy in ((0.0, -0.24), (0.11, -0.18), (-0.11, -0.18), (0.0, 0.15)):              # three toes forward, one back
			root = Vector((x, -0.03, 0.06))
			end = root + Vector((dx * s if dx else 0.0, dy, -0.03))
			b.seg(tuple(root), tuple(end), 0.045, 0.034, cere, leg, sides=5)
			d = (end - root).normalized()
			b.seg(tuple(end), tuple(end + d * 0.07 + Vector((0, 0, -0.04))), 0.032, 0.004, beak, leg, sides=4)  # talon
	arm = b.build()

	def folded(k=0.0):
		"""k=0 folded, 1 spread wide and raised."""
		return {"wing_l": {"rot": (-40 * k, 0, -88 * k)}, "wing_r": {"rot": (-40 * k, 0, 88 * k)}}

	def idle(t):  # sharp, jerky looks round, a ruffle now and then
		look = seq(t, [(0, 0), (0.16, 0), (0.2, 34), (0.44, 34), (0.48, -28), (0.72, -28), (0.76, 0)])
		cock = seq(t, [(0.44, 0), (0.48, 14), (0.72, 14), (0.76, 0)])
		ruffle = seq(t, [(0.8, 0), (0.86, 0.12), (0.92, 0)])
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))}, "head": {"rot": (0, cock, look)},
					  "tail": {"rot": (4 * wave(t, 3), 0, 0)}}, folded(ruffle))

	def walk(t):  # a stalking, head-bobbing strut
		lg = 30 * wave(t)
		return merge({"leg_l": {"rot": (lg, 0, 0)}, "leg_r": {"rot": (-lg, 0, 0)},
					  "root": {"loc": (0, 0, 0.03 * abs(wave(t, 2))), "rot": (0, 4 * wave(t), 0)},
					  "head": {"loc": (0, 0.04 * wave(t, 2), 0)}, "tail": {"rot": (3 * wave(t, 2), 0, 0)}}, folded(0.08))

	def run(t):  # two-footed bounding hops with big wingbeats
		hop = max(0.0, wave(t, 1, 0.0))
		lg = 38 * wave(t, 1, 0.25)
		flap = 0.5 + 0.5 * wave(t, 1, 0.1)
		return merge({"leg_l": {"rot": (lg, 0, 0)}, "leg_r": {"rot": (lg, 0, 0)},
					  "root": {"loc": (0, 0, 0.22 * hop), "rot": (-14 + 6 * wave(t), 0, 0)},
					  "head": {"rot": (10, 0, 0)}, "tail": {"rot": (8 * wave(t, 1, 0.3), 0, 0)}},
					 {"wing_l": {"rot": (-20 - 40 * flap, 0, -50 - 40 * flap)}, "wing_r": {"rot": (-20 - 40 * flap, 0, 50 + 40 * flap)}})

	def attack(t):  # wings up, rear back, then a lunging strike of the beak
		spread = seq(t, [(0, 0), (0.25, 1), (0.55, 0.9), (1, 0)])
		rear = seq(t, [(0, 0), (0.25, 16), (0.45, -26), (0.6, -22), (1, 0)])
		lunge = seq(t, [(0, 0), (0.25, -0.1), (0.45, 0.34), (0.6, 0.3), (1, 0)])
		neck = seq(t, [(0, 0), (0.25, 20), (0.45, -30), (0.6, -24), (1, 0)])
		head = seq(t, [(0, 0), (0.25, 10), (0.45, -24), (0.6, -20), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0.04 * spread), "rot": (rear, 0, 0)},
					  "neck": {"rot": (neck, 0, 0)}, "head": {"rot": (head, 0, 0)},
					  "leg_l": {"rot": (-rear * 0.8, 0, 0)}, "leg_r": {"rot": (-rear * 0.8, 0, 0)},
					  "tail": {"rot": (seq(t, [(0, 0), (0.25, -14), (0.45, 16), (1, 0)]), 0, 0)}}, folded(spread))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, 0.04 * k), "rot": (14 * k, 0, 6 * k)},
					  "neck": {"rot": (18 * k, 0, 0)}, "head": {"rot": (10 * k, 0, -20 * k)}}, folded(0.45 * k))

	def death(t):  # wings flare, then it keels over onto its side
		roll = seq(t, [(0.25, 0), (0.66, 84), (0.76, 78), (0.88, 86)])
		drop = seq(t, [(0.25, 0), (0.66, -0.42)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		flare = seq(t, [(0, 0), (0.2, 0.8), (0.55, 0.35), (0.85, 0.08)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 14), (0.55, -6)]), roll, 0)},
					  "neck": {"rot": (-26 * curl, 0, 10 * curl)}, "head": {"rot": (-20 * curl, 0, 20 * curl)},
					  "leg_l": {"rot": (40 * curl, 0, 0)}, "leg_r": {"rot": (24 * curl, 0, 0)},
					  "tail": {"rot": (-10 * curl, 0, 0)}}, folded(flare))

	clip(arm, "idle", 3.2, idle, True)
	clip(arm, "walk", 0.8, walk, True)
	clip(arm, "run", 0.5, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


# ---------------------------------------------------------------- sun temple parts (Sunward Steps)
# Bolt-ons for KayKit Rig_Medium bodies, in their mesh space like the gnoll's.

def _box(b, size, loc, mat, rot=(0, 0, 0), bone="x"):
	bm = bmesh.new()
	bmesh.ops.create_cube(bm, size=1.0)
	m = Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot]), Vector(size))
	bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
	b._add(bm, mat, bone)


def _basis(normal):
	n = Vector(normal).normalized()
	u = Vector((0, 0, 1)).cross(n)
	if u.length < 1e-4:
		u = Vector((1, 0, 0))
	u.normalize()
	return n, u, n.cross(u).normalized()


def _sun(b, center, normal, radius, disc, rays, ray_mat=None, count=12, ray_len=0.55, thick=0.05, arc=None, inner=None):
	"""A sun disc facing `normal` with `count` triangular rays (only over `arc` degrees from 'up' if given)."""
	n, u, v = _basis(normal)   # u sideways, v up in the disc's plane
	c = Vector(center)
	b.seg(tuple(c - n * thick / 2), tuple(c + n * thick / 2), radius, radius, disc, "x", sides=16)
	if inner:
		b.seg(tuple(c + n * thick / 2), tuple(c + n * thick), radius * 0.6, radius * 0.55, inner, "x", sides=14)
	for k in range(count):
		if arc:
			a = math.radians(-arc / 2 + arc * k / max(1, count - 1))
		else:
			a = 2 * math.pi * (k + 0.5) / count
		d = v * math.cos(a) + u * math.sin(a)
		side = n.cross(d).normalized()
		w = radius * (0.9 if arc else 1.8) * math.pi / count
		ln = ray_len * (1.0 if k % 2 == 0 or arc else 0.7)
		base = c + d * radius * 0.9
		_slab(b, [tuple(base - side * w), tuple(base + side * w), tuple(c + d * radius * (1 + ln))], thick * 0.8,
			  (ray_mat or rays) if k % 2 else rays)


def _wrap(b, center, radii, width, thick, mat, rot=(0, 0, 0), gap=None, sides=16):
	"""A strip of cloth wound once round an ellipse: a ribbon `width` tall, turned by `rot` (degrees),
	left open over the `gap` angle range (degrees; 270 is the front, -Y)."""
	rx, ry = radii
	m = Matrix.Translation(Vector(center)) @ Euler([math.radians(a) for a in rot]).to_matrix().to_4x4()
	if gap:
		a0, a1 = math.radians(gap[1]), math.radians(gap[0] + 360)
		angles = [a0 + (a1 - a0) * k / sides for k in range(sides + 1)]
	else:
		angles = [2 * math.pi * k / sides for k in range(sides)]
	bm = bmesh.new()
	rings = []
	for a in angles:
		c, s = math.cos(a), math.sin(a)
		rings.append([bm.verts.new(m @ Vector(((rx + dr) * c, (ry + dr) * s, h)))
					  for dr, h in ((0, -width / 2), (thick, -width / 2), (thick, width / 2), (0, width / 2))])
	pairs = list(zip(rings, rings[1:])) + ([] if gap else [(rings[-1], rings[0])])
	for p, q in pairs:
		for k in range(4):
			j = (k + 1) % 4
			bm.faces.new((p[k], p[j], q[j], q[k]))
	if gap:
		bm.faces.new(rings[0])
		bm.faces.new(list(reversed(rings[-1])))
	bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
	b._add(bm, mat, "x")


def stone_materials():
	return {
		"stone": material("temple_stone", "c2b08a", 0.95),
		"stone_light": material("temple_stone_light", "dccaa2", 0.95),
		"stone_dark": material("temple_stone_dark", "847660", 0.95),
		"crack": material("temple_crack", "3a3028", 0.95),
		"moss": material("temple_moss", "7a7a3e", 0.95),
		"gilt": material("temple_gilt", "c89a3a", 0.55),
		"gilt_dark": material("temple_gilt_dark", "8e6420", 0.6),
		"glow": material("temple_glow", "ffae2a", 0.3, emit=3.0),
	}


def _elephant_head(b, m, big=False):
	"""A carved stone elephant head for a KayKit knight's body (its own head hidden)."""
	st, lt, dk = m["stone"], m["stone_light"], m["stone_dark"]
	_box(b, (0.92, 0.86, 0.8), (0, 0.04, 1.72), st, rot=(0, 0, 0))                          # the carved block
	b.blob((1.0, 0.94, 0.9), (0, 0.04, 1.74), st, "x", segs=(8, 6))                                # softened by wear
	for s in (1, -1):
		b.blob((0.46, 0.6, 0.42), (0.2 * s, 0.0, 2.08), lt, "x", segs=(8, 5))                    # twin domes of the crown
	_box(b, (0.86, 0.1, 0.46), (0, -0.46, 1.8), lt)                                          # flat carved brow plate
	_box(b, (0.9, 0.12, 0.08), (0, -0.48, 2.04), dk)                                          # brow ledge
	for s in (1, -1):
		_box(b, (0.2, 0.08, 0.1), (0.2 * s, -0.53, 1.74), m["crack"])                          # deep eye sockets
		b.blob((0.13, 0.06, 0.07), (0.2 * s, -0.55, 1.74), m["glow"], "x", segs=(6, 4))            # amber eyes
		# great flat ears fanning out at the sides
		ear = [(0.46 * s, -0.2, 2.02), (0.86 * s, -0.02, 2.02), (0.98 * s, 0.14, 1.66), (0.8 * s, 0.16, 1.28),
			   (0.5 * s, 0.06, 1.34)]
		_slab(b, ear, 0.08, st)
		_slab(b, [(p[0] * 0.95 + 0.03 * s, p[1] + 0.04, p[2] * 0.99 + 0.02) for p in ear], 0.06, dk)
		# tusks from the cheeks, curving forward and up
		b.seg((0.2 * s, -0.46, 1.44), (0.3 * s, -0.72, 1.32), 0.07, 0.055, lt, "x", sides=6)
		b.seg((0.3 * s, -0.72, 1.32), (0.3 * s, -0.86, 1.44), 0.055, 0.012, lt, "x", sides=6)
	# the trunk: stacked carved rings down over the chest, curling out at the tip
	pts = [((0, -0.5, 1.6), 0.19), ((0, -0.6, 1.4), 0.16), ((0, -0.62, 1.2), 0.13), ((0, -0.58, 1.02), 0.11),
		   ((0, -0.64, 0.88), 0.09), ((0, -0.76, 0.84), 0.07)]
	for (p, r0), (q, r1) in zip(pts, pts[1:]):
		b.seg(p, q, r0, r1, st, "x", sides=8)
		b.seg(p, tuple(Vector(p) + (Vector(q) - Vector(p)) * 0.12), r0 * 1.12, r0 * 1.12, dk, "x", sides=8)   # ring grooves
	b.blob((0.12, 0.12, 0.1), (0, -0.8, 0.86), dk, "x", segs=(6, 4))
	for p, q in (((0.3, -0.44, 2.0), (0.2, -0.5, 1.9)), ((-0.36, -0.2, 2.0), (-0.42, -0.1, 1.8))):
		b.seg(p, q, 0.012, 0.012, m["crack"], "x", sides=3)                                          # weathering cracks
	b.blob((0.3, 0.3, 0.08), (-0.22, 0.2, 2.26), m["moss"], "x", rot=(0, -18, 0), segs=(6, 3))    # lichen on the crown
	# sun disc on the brow: a crest standing up off the forehead
	if big:
		_sun(b, (0, -0.3, 2.44), (0, -1, 0), 0.26, m["gilt"], m["gilt"], m["gilt_dark"], count=16, ray_len=0.62,
			 thick=0.07, inner=m["gilt_dark"])
		b.seg((0, -0.3, 2.06), (0, -0.3, 2.24), 0.12, 0.08, m["gilt_dark"], "x", sides=6)
	else:
		_sun(b, (0, -0.44, 2.2), (0, -1, 0), 0.17, m["gilt"], m["gilt"], m["gilt_dark"], count=12, ray_len=0.6,
			 thick=0.05, inner=m["gilt_dark"])


def build_stone_guardian_head():
	m = stone_materials()
	b = Builder("stone_guardian_head")
	_elephant_head(b, m)
	return b.build_static()


def build_stone_colossus_head():
	m = stone_materials()
	b = Builder("stone_colossus_head")
	_elephant_head(b, m, big=True)
	return b.build_static()


def build_stone_guardian_chest():
	"""Heavy carved shoulders and weathering cracks."""
	m = stone_materials()
	b = Builder("stone_guardian_chest")
	for s in (1, -1):
		b.blob((0.4, 0.48, 0.24), (0.38 * s, 0.0, 1.3), m["stone"], "x", rot=(0, 20 * s, 0), segs=(7, 4))   # shoulder blocks
		b.blob((0.26, 0.3, 0.1), (0.4 * s, 0.0, 1.4), m["stone_light"], "x", rot=(0, 24 * s, 0), segs=(7, 3))
		b.seg((0.3 * s, -0.37, 1.12), (0.24 * s, -0.4, 0.98), 0.014, 0.01, m["crack"], "x", sides=3)               # weathering cracks
		b.seg((0.24 * s, -0.4, 0.98), (0.27 * s, -0.4, 0.86), 0.012, 0.008, m["crack"], "x", sides=3)
	return b.build_static()


def linen_materials():
	return {
		"linen": material("mummy_linen", "e2d8bc", 0.95),
		"linen_b": material("mummy_linen_b", "cbbd98", 0.95),
		"linen_dirty": material("mummy_linen_dirty", "a89672", 0.95),
		"gap": material("mummy_gap", "2a2018", 0.95),
		"gold": material("mummy_gold", "d8a838", 0.5),
		"gold_dark": material("mummy_gold_dark", "94681e", 0.55),
		"lapis": material("mummy_lapis", "2c4a8a", 0.6),
		"red": material("mummy_red", "a8321e", 0.8),
		"glow": material("mummy_glow", "ffc040", 0.3, emit=2.5),
	}


def _wound(b, m, center, radii, z0, z1, rng, gap=None, gap_z=None, width=0.1, shape=None):
	"""Bandages wound round and round from z0 up to z1, each turn tipped a little differently."""
	mats = [m["linen"], m["linen_b"], m["linen"], m["linen_dirty"]]
	z = z0
	k = 0
	while z <= z1 + 1e-6:
		sx = shape(z) if shape else 1.0
		g = gap if (gap and gap_z and gap_z[0] <= z <= gap_z[1]) else None
		_wrap(b, (center[0], center[1], z), (radii[0] * sx, radii[1] * sx), width, 0.03, mats[k % len(mats)],
			  rot=(rng.uniform(-9, 9), rng.uniform(-9, 9), rng.uniform(0, 360) if not g else 0), gap=g, sides=14)
		z += width * 0.72
		k += 1


def _mummy_skull(b, m, rng):
	"""Wraps over a KayKit skeleton skull, with a slot left open for the glowing eyes."""
	shape = lambda z: max(0.35, math.sqrt(max(0.0, 1 - ((z - 1.74) / 0.5) ** 2)))
	_wound(b, m, (0, 0.0, 0), (0.46, 0.47), 1.34, 2.08, rng, gap=(235, 305), gap_z=(1.56, 1.72), shape=shape)
	b.blob((0.62, 0.62, 0.3), (0, 0.0, 2.1), m["linen_b"], "x", segs=(10, 5))                     # crown
	_box(b, (0.6, 0.12, 0.12), (0, -0.33, 1.64), m["gap"])                                   # the dark slot behind
	for s in (1, -1):
		b.blob((0.1, 0.05, 0.07), (0.15 * s, -0.4, 1.64), m["glow"], "x", segs=(6, 4))
	# a loose end trailing down the back
	_slab(b, [(-0.06, 0.44, 1.9), (0.06, 0.46, 1.88), (0.14, 0.52, 1.2), (0.02, 0.5, 1.18)], 0.025, m["linen_b"])


def build_mummy_head():
	b = Builder("mummy_head")
	import random
	_mummy_skull(b, linen_materials(), random.Random(7))
	return b.build_static()


def build_mummy_chest():
	import random
	m = linen_materials()
	rng = random.Random(11)
	b = Builder("mummy_chest")
	b.blob((0.6, 0.56, 0.7), (0, 0.0, 1.0), m["linen_dirty"], "x", segs=(10, 7))                 # packed linen under the wraps
	shape = lambda z: 0.86 + 0.2 * math.sin((z - 0.6) / 0.66 * math.pi)
	_wound(b, m, (0, 0.0, 0), (0.33, 0.31), 0.68, 1.3, rng, shape=shape)
	_slab(b, [(0.26, -0.3, 1.32), (0.36, -0.26, 1.28), (0.3, -0.36, 0.72), (0.22, -0.36, 0.76)], 0.025, m["linen"])  # a slipped strip
	_slab(b, [(-0.2, 0.3, 1.2), (-0.1, 0.34, 1.18), (-0.16, 0.42, 0.62), (-0.26, 0.4, 0.66)], 0.025, m["linen_b"])
	return b.build_static()


def build_mummy_hips():
	import random
	m = linen_materials()
	rng = random.Random(13)
	b = Builder("mummy_hips")
	_wound(b, m, (0, 0.0, 0), (0.35, 0.32), 0.46, 0.62, rng)
	for k, (x, y, ln) in enumerate(((0.3, -0.12, 0.34), (-0.32, -0.06, 0.28), (0.26, 0.24, 0.4), (-0.18, 0.3, 0.36),
									(0.04, 0.36, 0.44))):   # trailing strips, the front left clear for the stride
		n = Vector((x, y, 0)).normalized()
		side = Vector((-n.y, n.x, 0)) * 0.06
		top = Vector((x, y, 0.5)) + n * 0.04
		_slab(b, [tuple(top - side), tuple(top + side), tuple(top + side * 0.6 + n * 0.08 + Vector((0, 0, -ln))),
				  tuple(top - side * 0.8 + n * 0.08 + Vector((0, 0, -ln - 0.05)))], 0.025, m["linen"] if k % 2 else m["linen_dirty"])
	return b.build_static()


def _mummy_limb(name, bone_x, arm):
	"""Wraps for a forearm (round the X axis) or a shin (round Z), for one side."""
	import random
	m = linen_materials()
	rng = random.Random(len(name))
	b = Builder(name)
	s = 1 if bone_x > 0 else -1
	if arm:
		for k in range(4):
			x = (0.48 + k * 0.065) * s
			_wrap(b, (x, 0, 1.11), (0.085, 0.085), 0.07, 0.022, [m["linen"], m["linen_b"]][k % 2],
				  rot=(rng.uniform(-12, 12), 90, 0), sides=10)
		_slab(b, [(0.62 * s, -0.02, 1.04), (0.66 * s, 0.02, 1.04), (0.64 * s, 0.03, 0.84), (0.6 * s, 0.0, 0.86)], 0.02, m["linen_dirty"])
	else:
		for k in range(4):
			_wrap(b, (0.17 * s, 0.02, 0.12 + k * 0.065), (0.1, 0.11), 0.07, 0.022, [m["linen"], m["linen_b"]][k % 2],
				  rot=(rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(0, 360)), sides=10)
	return b.build_static()


def build_mummy_arm_l():
	return _mummy_limb("mummy_arm_l", 1, True)


def build_mummy_arm_r():
	return _mummy_limb("mummy_arm_r", -1, True)


def build_mummy_leg_l():
	return _mummy_limb("mummy_leg_l", 1, False)


def build_mummy_leg_r():
	return _mummy_limb("mummy_leg_r", -1, False)


def build_mummy_priest_head():
	"""Wrapped skull under a striped linen-and-gold headcloth and a tall sun crown."""
	import random
	m = linen_materials()
	b = Builder("mummy_priest_head")
	_mummy_skull(b, m, random.Random(17))
	cz, rx, ry, rz = 1.78, 0.6, 0.61, 0.56
	opening = lambda d: not (d.y < -0.42 and -0.78 < d.z < 0.3 and abs(d.x) < 0.7)
	rim = _shell(b, (rx * 2, ry * 2, rz * 2), (0, 0.02, cz), m["linen"], opening, segs=(20, 14))
	for p, q in rim:   # a gold edge round the face
		if p[1] < -0.2:
			b.seg(p, q, 0.035, 0.035, m["gold"], "x", sides=5)
	for z in (1.98, 2.12, 1.84, 1.7):   # gold stripes round the headcloth
		k = math.sqrt(max(0.0, 1 - ((z - cz) / rz) ** 2))
		_ring(b, (0, 0.02, z), (rx * k + 0.01, ry * k + 0.01), (0, 0), 0.022, m["gold"], sides=20, gap=(13, 18))
	for s in (1, -1):   # lappets: flat striped flaps falling in front of the shoulders
		for k in range(6):
			_box(b, (0.22, 0.05, 0.075), (0.4 * s, -0.16, 1.5 - k * 0.075), m["gold"] if k % 2 else m["linen"])
		_slab(b, [(0.5 * s, 0.1, 1.7), (0.56 * s, 0.4, 1.56), (0.44 * s, 0.42, 1.2), (0.44 * s, 0.1, 1.26)], 0.04, m["linen_b"])
	b.seg((0, 0.34, 1.7), (0, 0.5, 1.24), 0.24, 0.08, m["linen_b"], "x", sides=8)            # the tail of cloth behind
	# a tall white crown with a bulb top, a gold band and a sun disc at the front
	b.seg((0, 0.04, 2.18), (0, 0.04, 2.3), 0.36, 0.34, m["gold"], "x", sides=14)
	b.seg((0, 0.04, 2.3), (0, 0.06, 2.74), 0.34, 0.2, m["linen"], "x", sides=14)
	b.blob((0.36, 0.36, 0.3), (0, 0.06, 2.8), m["linen"], "x", segs=(12, 7))
	b.seg((0, 0.05, 2.46), (0, 0.05, 2.52), 0.3, 0.29, m["red"], "x", sides=14)
	_sun(b, (0, -0.36, 2.34), (0, -1, 0), 0.14, m["gold"], m["gold"], m["gold_dark"], count=12, ray_len=0.6,
		 thick=0.05, inner=m["glow"])
	for s in (1, -1):   # rearing sun serpents flanking it
		b.seg((0.22 * s, -0.3, 2.2), (0.22 * s, -0.36, 2.36), 0.045, 0.035, m["gold_dark"], "x", sides=6)
		b.blob((0.09, 0.11, 0.09), (0.22 * s, -0.38, 2.4), m["gold_dark"], "x", segs=(6, 4))
	return b.build_static()


def build_mummy_priest_chest():
	"""A broad collar of gold, lapis and red beads, with a sun pendant."""
	m = linen_materials()
	b = Builder("mummy_priest_chest")
	for k, mat in enumerate((m["gold"], m["lapis"], m["red"], m["gold"])):
		_wrap(b, (0, 0.02, 1.3 - k * 0.06), (0.36 + k * 0.05, 0.34 + k * 0.045), 0.065, 0.035, mat, rot=(-6, 0, 0), sides=18)
	b.seg((0, -0.5, 1.12), (0, -0.5, 1.04), 0.03, 0.03, m["gold_dark"], "x", sides=5)
	_sun(b, (0, -0.52, 0.92), (0, -1, 0), 0.1, m["gold"], m["gold"], m["gold_dark"], count=12, ray_len=0.7,
		 thick=0.04, inner=m["glow"])
	return b.build_static()


def cult_materials(leader=False):
	return {
		"hood": material("cult_hood_hi" if leader else "cult_hood", "6e1a12" if leader else "d88a26", 0.9),
		"hood_dark": material("cult_hood_dark_hi" if leader else "cult_hood_dark", "3a0c08" if leader else "8e4a12", 0.9),
		"trim": material("cult_trim_hi" if leader else "cult_trim", "e8b030" if leader else "a8321a", 0.6),
		"mask": material("cult_mask_hi" if leader else "cult_mask", "e0a028" if leader else "d4481a", 0.5),
		"ray": material("cult_ray_hi" if leader else "cult_ray", "f4c848" if leader else "f08a22", 0.5),
		"ray_b": material("cult_ray_b_hi" if leader else "cult_ray_b", "c04a14" if leader else "c8321a", 0.6),
		"hole": material("cult_hole", "140a06", 0.9),
		"glow": material("cult_glow_hi" if leader else "cult_glow", "ff7a1a", 0.3, emit=2.5),
		"gold": material("cult_gold", "e0b038", 0.4),
	}


def _cult_head(b, m, leader):
	"""A hood over a KayKit mage head (hat hidden) and a sun mask over the face."""
	opening = lambda d: not (d.y < -0.45 and -0.85 < d.z < 0.3 and abs(d.x) < 0.66)
	rim = _shell(b, (1.16, 1.2, 1.18), (0, 0.0, 1.62), m["hood"], opening, segs=(20, 14))
	for p, q in rim:
		if p[1] < -0.2:
			b.seg(p, q, 0.04, 0.04, m["trim"], "x", sides=5)
	_shell(b, (1.12, 1.16, 1.14), (0, 0.0, 1.62), m["hood_dark"], opening, segs=(20, 14))
	b.blob((0.9, 0.9, 0.96), (0, 0.04, 1.6), m["hole"], "x", segs=(12, 8))                     # shadow inside the hood
	b.seg((0, 0.24, 2.1), (0, 0.5, 2.0), 0.24, 0.09, m["hood"], "x", sides=8)                 # peak falling behind
	b.seg((0, 0.5, 2.0), (0, 0.62, 1.74), 0.09, 0.02, m["hood"], "x", sides=8)
	_shell(b, (1.16, 1.06, 0.62), (0, 0.02, 1.1), m["hood"], lambda d: d.z > 0.0)            # cowl over the shoulders
	_ring(b, (0, 0.02, 1.1), (0.58, 0.53), (0, 0), 0.03, m["trim"], sides=16)
	# the sun mask: a round face with rays, dark eye holes glowing deep inside
	c = Vector((0, -0.54, 1.58))
	_sun(b, tuple(c), (0, -1, 0.12), 0.28, m["mask"], m["ray"], m["ray_b"], count=14, ray_len=0.42, thick=0.06)
	for s in (1, -1):
		b.blob((0.14, 0.05, 0.07), (0.12 * s, -0.585, 1.64), m["hole"], "x", rot=(0, -10 * s, 0), segs=(8, 4))
		b.blob((0.06, 0.03, 0.035), (0.12 * s, -0.595, 1.64), m["glow"], "x", segs=(6, 4))
	b.blob((0.16, 0.04, 0.05), (0, -0.585, 1.45), m["hole"], "x", segs=(8, 3))                     # a thin, shut mouth
	b.seg((0, -0.565, 1.74), (0, -0.6, 1.53), 0.03, 0.035, m["ray_b"], "x", sides=4)         # nose ridge
	if leader:   # a tall crown of gold rays fanning up behind the head
		_ring(b, (0, 0.0, 2.0), (0.45, 0.47), (0, 0), 0.05, m["gold"], sides=16)
		_sun(b, (0, 0.18, 2.14), (0, -1, 0), 0.26, m["gold"], m["ray"], m["gold"], count=11, ray_len=2.6,
			 thick=0.06, arc=170)
		b.blob((0.16, 0.1, 0.16), (0, -0.46, 1.98), m["glow"], "x", segs=(8, 5))                  # a jewel on the brow


def build_cult_hood():
	m = cult_materials()
	b = Builder("cult_hood")
	_cult_head(b, m, False)
	return b.build_static()


def build_cult_hierophant_hood():
	m = cult_materials(True)
	b = Builder("cult_hierophant_hood")
	_cult_head(b, m, True)
	return b.build_static()


# ---------------------------------------------------------------- repainted KayKit bodies
# Tints only multiply a texture, so a purple robe can't turn saffron. These
# write a copy of a KayKit character .glb with its palette texture repainted
# cell by cell (8 x 4 swatches of vertical gradients); mesh, skin and rig are
# untouched, so KayKit animations, gear and grips still apply.

def _hex_rgb(h):
	return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def repaint_kaykit(src, dst, image_name, cells=None, every=None):
	"""cells: {(col, row): (light_hex, dark_hex)} maps each cell's gradient onto a new one
	(row 0 is the top). every: (light_hex, dark_hex) maps every cell by absolute brightness."""
	import json
	import struct
	import tempfile
	import numpy as np
	data = open(src, "rb").read()
	jlen = struct.unpack("<I", data[12:16])[0]
	gltf = json.loads(data[20:20 + jlen])
	bin_start = 20 + jlen + 8
	blob = bytearray(data[bin_start:bin_start + gltf["buffers"][0]["byteLength"]])
	img = gltf["images"][0]
	view = gltf["bufferViews"][img["bufferView"]]
	off, ln = view.get("byteOffset", 0), view["byteLength"]
	tmp = tempfile.mkdtemp()
	src_png = os.path.join(tmp, "in.png")
	open(src_png, "wb").write(bytes(blob[off:off + ln]))
	im = bpy.data.images.load(src_png)
	w, h = im.size
	px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)   # bottom row first
	lum = px[:, :, 0] * 0.3 + px[:, :, 1] * 0.59 + px[:, :, 2] * 0.11
	cw, ch = w // 8, h // 4
	if every:
		light, dark = np.array(_hex_rgb(every[0])), np.array(_hex_rgb(every[1]))
		t = np.clip(lum, 0, 1)[:, :, None]
		px[:, :, :3] = dark + (light - dark) * t
	for (col, row), (lt, dk) in (cells or {}).items():
		y0 = h - (row + 1) * ch   # rows count from the top; pixels from the bottom
		sl = (slice(y0, y0 + ch), slice(col * cw, (col + 1) * cw))
		cl = lum[sl]
		t = ((cl - cl.min()) / max(1e-4, cl.max() - cl.min()))[:, :, None]
		light, dark = np.array(_hex_rgb(lt)), np.array(_hex_rgb(dk))
		px[sl[0], sl[1], :3] = dark + (light - dark) * t
	im.pixels[:] = px.ravel()
	out_png = os.path.join(tmp, "out.png")
	im.filepath_raw = out_png
	im.file_format = "PNG"
	im.save()
	png = open(out_png, "rb").read()
	# splice the new PNG in, shifting every later buffer view
	pad = (-len(png)) % 4
	delta = len(png) + pad - ln
	blob[off:off + ln] = png + b"\0" * pad
	for v in gltf["bufferViews"]:
		if v is not view and v.get("byteOffset", 0) > off:
			v["byteOffset"] = v.get("byteOffset", 0) + delta
	view["byteLength"] = len(png)
	gltf["buffers"][0]["byteLength"] = len(blob)
	img["name"] = image_name
	blob += b"\0" * ((-len(blob)) % 4)
	js = json.dumps(gltf, separators=(",", ":")).encode()
	js += b" " * ((-len(js)) % 4)
	out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob))
	out += struct.pack("<I", len(js)) + b"JSON" + js + struct.pack("<I", len(blob)) + b"BIN\0" + bytes(blob)
	open(dst, "wb").write(out)


KAYKIT = "assets/KayKit_Adventurers_2.0_FREE/Characters/gltf/"
# name: (source, image name, cells, every)
BODIES = {
	"stone_knight": (KAYKIT + "Knight.glb", "stone_texture", None, ("f6ead0", "6a5e4c")),
	"sun_cultist_body": (KAYKIT + "Mage.glb", "sun_cultist_texture",
						 {(0, 1): ("f4b440", "a84e14"), (1, 1): ("f4b440", "a84e14"), (2, 1): ("e0521e", "7a1c0e"),
						  (3, 0): ("f2e4c4", "b8a47e"), (4, 0): ("f2e4c4", "b8a47e"), (2, 2): ("c8321e", "6a120a"),
						  (7, 1): ("6a4a2e", "2a1a10")}, None),
	"cult_hierophant_body": (KAYKIT + "Mage.glb", "cult_hierophant_texture",
							 {(0, 1): ("a82a1a", "3a0808"), (1, 1): ("a82a1a", "3a0808"), (2, 1): ("f4c848", "9a6414"),
							  (3, 0): ("f4d060", "a07018"), (4, 0): ("f4d060", "a07018"), (2, 2): ("f4c848", "9a6414"),
							  (7, 1): ("3a1410", "120404")}, None),
	"mummy_priest_body": ("assets/KayKit_Skeletons_1.1_FREE/characters/gltf/Skeleton_Mage.glb", "mummy_priest_texture",
						  {(2, 2): ("f2e8cc", "a8946c"), (1, 2): ("3a5ca0", "1a2a5a"), (5, 2): ("f0c450", "9a6a18"),
						   (3, 0): ("f0c450", "9a6a18")}, None),
}


ATTACHMENTS = {"gnoll_head": build_gnoll_head, "gnoll_tail": build_gnoll_tail, "orc_face": build_orc_face,
			   "lizard_head": build_lizard_head, "lizard_head_shaman": build_lizard_head_shaman,
			   "lizard_head_chief": build_lizard_head_chief, "lizard_tail": build_lizard_tail,
			   "lizard_tail_chief": build_lizard_tail_chief, "drowned_head": build_drowned_head,
			   "drowned_chest": build_drowned_chest, "drowned_hips": build_drowned_hips,
			   "brigand_hood": build_brigand_hood, "brigand_captain_hat": build_brigand_captain_hat,
			   "scarecrow_head": build_scarecrow_head, "scarecrow_head_elder": build_scarecrow_head_elder,
			   "scarecrow_chest": build_scarecrow_chest, "scarecrow_hips": build_scarecrow_hips,
			   "scarecrow_cuff_l": build_scarecrow_cuff_l, "scarecrow_cuff_r": build_scarecrow_cuff_r,
			   "scarecrow_crow": build_scarecrow_crow,
			   "stone_guardian_head": build_stone_guardian_head, "stone_colossus_head": build_stone_colossus_head,
			   "stone_guardian_chest": build_stone_guardian_chest, "mummy_head": build_mummy_head,
			   "mummy_chest": build_mummy_chest, "mummy_hips": build_mummy_hips, "mummy_arm_l": build_mummy_arm_l,
			   "mummy_arm_r": build_mummy_arm_r, "mummy_leg_l": build_mummy_leg_l, "mummy_leg_r": build_mummy_leg_r,
			   "mummy_priest_head": build_mummy_priest_head, "mummy_priest_chest": build_mummy_priest_chest,
			   "cult_hood": build_cult_hood, "cult_hierophant_hood": build_cult_hierophant_hood}
CREATURES = {"rat": build_rat, "fire_beetle": build_beetle, "wolf": build_wolf, "dire_wolf": build_dire_wolf,
			 "bear": build_bear, "spider": build_spider, "mire_toad": build_toad, "snapping_turtle": build_turtle,
			 "bog_leech": build_leech, "boar": build_boar, "mountain_ram": build_ram, "sunhawk": build_sunhawk}
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
	for name, (src, image, cells, every) in BODIES.items():
		if only and name not in only:
			continue
		path = os.path.abspath(os.path.join(opts["--out"], f"{name}.glb"))
		repaint_kaykit(os.path.abspath(src), path, image, cells, every)
		print(f"exported {path}")


main()
