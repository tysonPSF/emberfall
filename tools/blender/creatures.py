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


def build_rat(name="rat", fur_hex="6b5a4e", belly_hex="a8927c", pink_hex="d99a94"):
	fur = material(f"{name}_fur", fur_hex)
	belly = material(f"{name}_belly", belly_hex)
	pink = material(f"{name}_pink", pink_hex, 0.6)
	eye = material(f"{name}_eye", "141010", 0.2)
	b = Builder(name)
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


def build_beetle(name="fire_beetle", shell_hex="c0442a", thorax_hex="8e2a1a", dark_hex="2e1c18",
				 eye_hex="ffae2a", eye_emit=4.0, metallic=0.0):
	pre = "beetle" if name == "fire_beetle" else name
	shell = material(f"{pre}_shell", shell_hex, 0.35)
	thorax = material(f"{pre}_thorax", thorax_hex, 0.45)
	if metallic:   # a bronze sheen on the wing cases
		for m in (shell, thorax):
			m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = metallic
	dark = material(f"{pre}_dark", dark_hex, 0.7)
	glow = material(f"{pre}_eye", eye_hex, 0.3, emit=eye_emit)
	b = Builder(name)
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


def build_wolf(name="wolf", fur_hex="6f6a63", back_hex="4a4642", belly_hex="b8ae9f", eye_hex="e8c040", glow=0.0,
			   ear=1.0, slim=1.0, snout=1.0):
	"""ear, slim and snout (1 = the wolf) reshape it: the jackal is slimmer, longer-nosed and big-eared."""
	fur = material(f"{name}_fur", fur_hex, 0.9, emit=glow)
	back = material(f"{name}_back", back_hex, 0.95, emit=glow)
	belly = material(f"{name}_belly", belly_hex, 0.9, emit=glow)
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

	b.blob((0.62 * slim, 1.5, 0.62 * (0.5 + 0.5 * slim)), (0, 0.0, 0.8), fur, "body", segs=(12, 8))
	b.blob((0.5 * slim, 1.2, 0.3), (0, 0.02, 0.62), belly, "body")
	b.blob((0.44 * slim, 1.1, 0.26), (0, 0.02, 1.07), back, "body")                           # darker saddle
	b.blob((0.74 * slim, 0.6, 0.72 * (0.5 + 0.5 * slim)), (0, -0.52, 0.9), fur, "body", segs=(10, 8))   # ruff
	b.blob((0.46 * (0.6 + 0.4 * slim), 0.5, 0.44), (0, -0.84, 1.02), fur, "head")          # skull
	tip = -0.95 - 0.41 * snout
	b.seg((0, -0.95, 0.99), (0, tip, 0.9), 0.16 * (0.7 + 0.3 * slim), 0.08 * (0.8 + 0.2 * slim), fur, "head", sides=8)   # muzzle
	b.blob((0.1, 0.09, 0.08), (0, tip - 0.02, 0.93), dark, "head")                         # nose
	b.seg((0, -0.95, 0.88), (0, tip + 0.06, 0.82), 0.1, 0.05, belly, "jaw", sides=6)        # lower jaw
	for s in (1, -1):
		b.blob((0.08, 0.06, 0.06), (0.13 * s * (0.7 + 0.3 * slim), -1.03, 1.1), eye, "head", segs=(6, 4))
		b.seg((0.15 * s, -0.78, 1.2), (0.19 * s * (1 + 0.3 * (ear - 1)), -0.74, 1.2 + 0.26 * ear), 0.09 * (1 + 0.45 * (ear - 1)), 0.01, back, "head", sides=4)  # ears
		if ear > 1:   # the pale inside of a big ear
			b.seg((0.155 * s, -0.8, 1.22), (0.185 * s * (1 + 0.3 * (ear - 1)), -0.78, 1.14 + 0.24 * ear), 0.055 * ear, 0.006, belly, "head", sides=4)
		b.seg((0.06 * s, tip + 0.12, 0.84), (0.06 * s, tip + 0.11, 0.77), 0.02, 0.004, material(f"{name}_tooth", "efe6d0"), "jaw", sides=4)
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


def build_spirit_wolf():
	"""The shaman's pet: a pale blue wolf that glows faintly, eyes like ice."""
	return build_wolf("spirit_wolf", "a8d4f0", "6a9ec8", "e4f4ff", "e8ffff", glow=0.35)


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

SUNHAWK_COLORS = {"gold": "c88e3c", "brown": "8a5a26", "dark": "4e3218", "cream": "ecd6a2", "streak": "a8702e",
				  "orange": "e87a1c", "tip": "f4b830", "cere": "e8b42c", "beak": "35302b", "eye": "f4a818"}
# the Ranger's companion: a red-tailed forest hawk, brown above, white below, a rust-red tail
FOREST_HAWK_COLORS = {"gold": "9a6a3e", "brown": "6a4424", "dark": "3a2614", "cream": "f4efe4", "streak": "7a5634",
					  "orange": "b04e22", "tip": "e8dcc4", "cere": "e8c040", "beak": "2e2a26", "eye": "e89a18"}


def build_sunhawk(name="sunhawk", colors=None):
	c = colors or SUNHAWK_COLORS
	p = "hawk" if name == "sunhawk" else name
	gold = material(f"{p}_gold", c["gold"], 0.85)
	brown = material(f"{p}_brown", c["brown"], 0.9)
	dark = material(f"{p}_dark", c["dark"], 0.9)
	cream = material(f"{p}_cream", c["cream"], 0.9)
	streak = material(f"{p}_streak", c["streak"], 0.9)
	orange = material(f"{p}_orange", c["orange"], 0.8)
	tip = material(f"{p}_tip", c["tip"], 0.7)
	cere = material(f"{p}_cere", c["cere"], 0.6)
	beak = material(f"{p}_beak", c["beak"], 0.4)
	eye = material(f"{p}_eye", c["eye"], 0.3, emit=1.0)
	pupil = material(f"{p}_pupil", "100c08", 0.2)
	b = Builder(name)
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


def _elephant_head(b, m, big=False, mossy=False):
	"""A carved stone elephant head for a KayKit knight's body (its own head hidden).
	mossy: the High Terrace's weathered kind, its sun disc long fallen, grown over with moss, a tusk broken."""
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
		if mossy and s < 0:   # snapped off short, the break pale and sharp
			b.seg((0.3 * s, -0.72, 1.32), (0.31 * s, -0.76, 1.35), 0.055, 0.045, m["stone_light"], "x", sides=6)
		else:
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
	if mossy:
		_mossy_overgrowth(b, m, big)
		return
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


# ---------------------------------------------------------------- scorpions and basilisks (The Bleach)

def _scaled(b, k):
	"""Scales everything built so far (parts and bones) about the origin, like the turtle's sink."""
	m = Matrix.Scale(k, 4)
	for p in b.parts:
		p.data.transform(m)
	b.bones = [(n, h * k, par) for n, h, par in b.bones]


def _crystal(b, base, direction, length, radius, mat, bone, tip_mat=None):
	"""A six-sided salt crystal: a prism with a pointed cap, growing out of `base` along `direction`."""
	d = Vector(direction).normalized()
	a = Vector(base)
	mid = a + d * length * 0.72
	b.seg(tuple(a - d * 0.04), tuple(mid), radius, radius * 0.92, mat, bone, sides=6)
	b.seg(tuple(mid), tuple(a + d * length), radius * 0.92, 0.0, tip_mat or mat, bone, sides=6)


SCORPION_LEGS = {}
for _i, _y in enumerate((-0.5, -0.36, -0.2, -0.04)):
	SCORPION_LEGS[f"leg_l{_i + 1}"] = (0.24, _y, _i)
	SCORPION_LEGS[f"leg_r{_i + 1}"] = (-0.24, _y, _i)
SCORPION_SET_A = ("leg_l1", "leg_r2", "leg_l3", "leg_r4")
SCORPION_TAIL = ("tail1", "tail2", "tail3", "tail4", "tail5", "sting")


def build_scorpion(name="giant_scorpion", plate_hex="d8c49a", light_hex="efe2c0", joint_hex="8c7352",
				   dark_hex="4a3a2a", sting_hex="2a1c16", eye_hex="1c1410", eye_glow=0.0, queen=False):
	plate = material(f"{name}_plate", plate_hex, 0.6)
	light = material(f"{name}_plate_light", light_hex, 0.55)
	joint = material(f"{name}_joint", joint_hex, 0.75)
	dark = material(f"{name}_dark", dark_hex, 0.7)
	sting = material(f"{name}_sting", sting_hex, 0.35)
	eye = material(f"{name}_eye", eye_hex, 0.2, emit=eye_glow)
	b = Builder(name)
	b.bone("root", (0, 0, 0.42))
	b.bone("body", (0, -0.1, 0.44), "root")
	b.bone("abdomen", (0, 0.05, 0.46), "body")

	# the head and carapace (prosoma)
	b.blob((0.62, 0.72, 0.3), (0, -0.36, 0.45), plate, "body", segs=(12, 8))
	b.blob((0.54, 0.62, 0.12), (0, -0.38, 0.58), light, "body", segs=(12, 6))
	b.blob((0.44, 0.22, 0.2), (0, -0.7, 0.44), plate, "body", segs=(10, 6))
	b.blob((0.5, 0.7, 0.14), (0, -0.34, 0.31), joint, "body", segs=(10, 5))                   # underside
	b.seg((0, -0.66, 0.6), (0, -0.12, 0.62), 0.03, 0.03, joint, "body", sides=4)              # the midline groove
	for s in (1, -1):
		b.blob((0.09, 0.09, 0.08), (0.07 * s, -0.52, 0.63), eye, "body", segs=(6, 4))            # the median eyes
		for k in range(3):
			b.blob((0.05, 0.05, 0.05), ((0.2 + 0.02 * k) * s, -0.68 + 0.05 * k, 0.53), eye, "body", segs=(5, 3))
		b.seg((0.07 * s, -0.78, 0.42), (0.06 * s, -0.9, 0.38), 0.05, 0.02, dark, "body", sides=5)  # little chelicerae
	# the plated back (mesosoma): seven overlapping plates, widest in the middle
	for k in range(7):
		y = -0.02 + k * 0.14
		w = 0.62 + 0.14 * math.sin(k / 6 * math.pi) - 0.05 * max(0, k - 4)
		z = 0.47 - 0.01 * k
		b.blob((w * 0.96, 0.2, 0.3), (0, y, z), joint, "abdomen", segs=(10, 6))
		b.blob((w, 0.19, 0.2), (0, y - 0.02, z + 0.06), plate, "abdomen", rot=(-8, 0, 0), segs=(12, 6))
		b.blob((w * 0.84, 0.13, 0.08), (0, y - 0.03, z + 0.15), light, "abdomen", rot=(-8, 0, 0), segs=(10, 4))
		if queen:   # the queen's back is set with ridge spikes
			b.seg((0, y, z + 0.14), (0, y + 0.08, z + 0.34 + 0.06 * math.sin(k / 6 * math.pi)), 0.06, 0.0, dark, "abdomen", sides=4)
	b.blob((0.62, 0.9, 0.16), (0, 0.4, 0.33), joint, "abdomen", segs=(10, 5))

	# the tail (metasoma): five bulging segments arching up over the back, then the stinger
	pts = [(0, 0.94, 0.5), (0, 1.16, 0.74), (0, 1.26, 1.04), (0, 1.2, 1.34), (0, 1.0, 1.56), (0, 0.74, 1.64)]
	radii = [0.16, 0.15, 0.14, 0.13, 0.12, 0.11]
	for k, bone in enumerate(SCORPION_TAIL[:-1]):
		b.bone(bone, pts[k], SCORPION_TAIL[k - 1] if k else "abdomen")
		p, q = Vector(pts[k]), Vector(pts[k + 1])
		d = (q - p).normalized()
		r0, r1 = radii[k], radii[k + 1]
		b.seg(tuple(p + d * 0.02), tuple(q - d * 0.03), r0 * 1.12, r1 * 1.0, plate, bone, sides=8)
		b.blob((r0 * 2.3, r0 * 2.3, r0 * 2.3), tuple(p + d * 0.08), plate, bone, segs=(8, 6))       # the bulging joint
		b.blob((r0 * 1.9, r0 * 1.9, r0 * 1.9), tuple(p), joint, bone, segs=(8, 5))
	b.bone("sting", pts[5], "tail5")
	b.blob((0.3, 0.36, 0.28), (0, 0.64, 1.6), plate, "sting", segs=(10, 7))                      # the venom bulb
	b.blob((0.18, 0.22, 0.16), (0, 0.62, 1.56), light, "sting", segs=(8, 5))
	b.seg((0, 0.52, 1.58), (0, 0.4, 1.5), 0.075, 0.05, sting, "sting", sides=6)                   # the barb, hooked down and forward
	b.seg((0, 0.4, 1.5), (0, 0.34, 1.34), 0.05, 0.0, sting, "sting", sides=6)

	# the pincers
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"arm_{side}", (0.2 * s, -0.66, 0.44), "body")
		b.bone(f"claw_{side}", (0.46 * s, -1.08, 0.46), f"arm_{side}")
		b.bone(f"finger_{side}", (0.52 * s, -1.44, 0.46), f"claw_{side}")
		b.seg((0.2 * s, -0.66, 0.44), (0.52 * s, -0.82, 0.5), 0.08, 0.075, plate, f"arm_{side}", sides=7)
		b.blob((0.18, 0.18, 0.18), (0.52 * s, -0.82, 0.5), joint, f"arm_{side}", segs=(7, 5))
		b.seg((0.52 * s, -0.82, 0.5), (0.46 * s, -1.08, 0.46), 0.08, 0.09, plate, f"arm_{side}", sides=7)
		b.blob((0.16, 0.16, 0.16), (0.46 * s, -1.08, 0.46), joint, f"arm_{side}", segs=(7, 5))
		big = 1.2 if queen else 1.0
		b.blob((0.3 * big, 0.44 * big, 0.24 * big), (0.44 * s, -1.26, 0.46), plate, f"claw_{side}", segs=(12, 8))   # the swollen hand
		b.blob((0.2 * big, 0.3 * big, 0.08), (0.44 * s, -1.26, 0.57), light, f"claw_{side}", segs=(8, 4))
		b.seg((0.4 * s, -1.4, 0.46), (0.33 * s, -1.62, 0.45), 0.075 * big, 0.04, plate, f"claw_{side}", sides=6)     # fixed finger
		b.seg((0.33 * s, -1.62, 0.45), (0.3 * s, -1.74, 0.44), 0.04, 0.0, dark, f"claw_{side}", sides=6)
		b.seg((0.52 * s, -1.44, 0.46), (0.5 * s, -1.66, 0.46), 0.07 * big, 0.04, plate, f"finger_{side}", sides=6)  # moving finger
		b.seg((0.5 * s, -1.66, 0.46), (0.43 * s, -1.76, 0.46), 0.04, 0.0, dark, f"finger_{side}", sides=6)
		for k in range(3):   # teeth along the inner edges
			b.seg((0.37 * s, -1.46 - k * 0.07, 0.46), (0.43 * s, -1.49 - k * 0.07, 0.46), 0.016, 0.0, dark, f"claw_{side}", sides=3)
	# eight walking legs, knees high like a crab's
	for name_, (x, y, i) in SCORPION_LEGS.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, 0.42), "body")
		spread = (i - 1.5) * 0.16
		knee = (x + 0.32 * s, y + spread * 0.5, 0.64)
		ankle = (x + 0.48 * s, y + spread * 1.0, 0.16)
		foot = (x + 0.58 * s, y + spread * 1.2, 0.0)
		b.seg((x, y, 0.42), knee, 0.075, 0.065, plate, name_, sides=6)
		b.blob((0.13, 0.13, 0.13), knee, joint, name_, segs=(6, 4))
		b.seg(knee, ankle, 0.065, 0.05, plate, name_, sides=6)
		b.blob((0.1, 0.1, 0.1), ankle, joint, name_, segs=(6, 4))
		b.seg(ankle, foot, 0.045, 0.012, dark, name_, sides=5)
	_scaled(b, 0.95)
	arm = b.build()

	def leg(name_, swing, lift):
		s = 1 if SCORPION_LEGS[name_][0] > 0 else -1
		return {name_: {"rot": (0, lift * s, -swing * s)}}

	def pincers(open_deg, raise_deg=0.0, spread=0.0):
		out = {}
		for s, side in ((1, "l"), (-1, "r")):
			out[f"arm_{side}"] = {"rot": (raise_deg, 0, spread * s)}
			out[f"claw_{side}"] = {"rot": (raise_deg * 0.4, 0, -spread * 0.6 * s)}
			out[f"finger_{side}"] = {"rot": (0, 0, open_deg * s)}
		return out

	def tail(pitches, yaw=0.0):
		return {bone: {"rot": (p, 0, yaw)} for bone, p in zip(SCORPION_TAIL, pitches)}

	def gait(t, amp, lift):
		out = {}
		for name_ in SCORPION_LEGS:
			ph = 0.0 if name_ in SCORPION_SET_A else 0.5
			out.update(leg(name_, amp * wave(t, 1, ph), lift * max(0.0, wave(t, 1, ph + 0.25))))
		return out

	def idle(t):
		sway = wave(t)
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))}},
					 tail((2 * sway, 2 * sway, 3 * sway, 3 * sway, 4 * sway, 6 * wave(t, 2)), 3 * wave(t, 1, 0.3)),
					 pincers(10 * max(0.0, wave(t, 2, 0.1)), 3 * sway, 3 * wave(t, 1, 0.5)), gait(t, 2, 0))

	def walk(t):
		return merge(gait(t, 16, 12), {"root": {"loc": (0, 0, 0.012 * abs(wave(t, 2)))}},
					 tail((3 * wave(t, 2), 0, 3 * wave(t, 2, 0.2), 0, 4 * wave(t, 2, 0.4), 0), 4 * wave(t)),
					 pincers(6, 6 + 4 * wave(t, 2), 4 * wave(t)))

	def run(t):
		return merge(gait(t, 24, 18), {"root": {"loc": (0, 0, 0.025 * abs(wave(t, 2)))}},
					 tail((6, 4 * wave(t, 2), 0, 4 * wave(t, 2, 0.3), 0, 0), 6 * wave(t)), pincers(4, 10, -6))

	def attack(t):  # pincers spread and open, then the tail whips the sting forward over the body
		cock = seq(t, [(0, 0), (0.25, 1), (0.4, -1), (0.55, -1), (1, 0)])
		pull = max(0.0, cock)
		stab = max(0.0, -cock)
		open_ = seq(t, [(0, 0), (0.2, 46), (0.42, 50), (0.52, -6), (0.75, 0)])
		lunge = seq(t, [(0, 0), (0.25, -0.06), (0.42, 0.14), (0.6, 0.1), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0), "rot": (seq(t, [(0, 0), (0.25, 4), (0.42, -4), (1, 0)]), 0, 0)}},
					 tail((10 * pull - 48 * stab, 8 * pull - 16 * stab, 4 * pull - 4 * stab, 4 * pull, 6 * pull + 6 * stab,
						   14 * pull - 32 * stab)),
					 pincers(open_, 16 * pull + 8 * stab, 14 * pull - 6 * stab),
					 {"leg_l1": {"rot": (0, 10 * pull, 0)}, "leg_r1": {"rot": (0, -10 * pull, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.03 * k), "rot": (6 * k, 5 * k, 0)}},
					 tail((10 * k, 8 * k, 6 * k, 4 * k, 4 * k, 10 * k)), pincers(20 * k, -8 * k, 10 * k), gait(t, 6 * k, 10 * k))

	def death(t):  # a thrash, then it flips onto its back and the legs and tail curl in
		roll = seq(t, [(0.2, 0), (0.55, 100), (0.72, 176), (0.82, 180)])
		lift = seq(t, [(0.2, 0), (0.45, 0.42), (0.74, 0.02), (0.82, 0.06)])
		curl = seq(t, [(0.3, 0), (0.9, 1)])
		thrash = seq(t, [(0, 0), (0.12, 1), (0.25, 0)])
		out = merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)}},
					tail((20 * thrash + 10 * curl, 14 * curl, 18 * curl, 18 * curl, 16 * curl, 20 * curl), 10 * thrash),
					pincers(30 * thrash + 16 * curl, -20 * curl, -24 * curl))
		for i, name_ in enumerate(SCORPION_LEGS):
			out = merge(out, leg(name_, 6 * wave(t, 5, i * 0.13) * seq(t, [(0.6, 0), (0.8, 1), (1, 0.2)]), -60 * curl))
		return out

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 0.75, walk, True)
	clip(arm, "run", 0.45, run, True)
	clip(arm, "attack", 0.75, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_scorpion_queen():
	return build_scorpion("scorpion_queen", plate_hex="9a4632", light_hex="bf6a4a", joint_hex="4e1c12", dark_hex="24100a",
						  sting_hex="140806", eye_hex="ff4a1a", eye_glow=2.0, queen=True)


BASILISK_LEGS = {"leg_fl": (0.34, -0.42), "leg_fr": (-0.34, -0.42), "leg_bl": (0.32, 0.46), "leg_br": (-0.32, 0.46)}


def build_basilisk():
	import random
	rng = random.Random(21)
	scale = material("basilisk_scale", "b4b0a6", 0.85)
	band = material("basilisk_band", "7c786f", 0.85)
	belly = material("basilisk_belly", "e0dace", 0.9)
	crust = material("basilisk_crust", "f6f4ee", 1.0)
	crystal = material("basilisk_crystal", "e4f2f6", 0.2, emit=0.12)
	crystal_b = material("basilisk_crystal_b", "ffffff", 0.2, emit=0.2)
	dark = material("basilisk_dark", "3e3a36", 0.7)
	mouth = material("basilisk_mouth", "6a3e3a", 0.7)
	tooth = material("basilisk_tooth", "f2ecd8", 0.4)
	eye = material("basilisk_eye", "d8fff2", 0.2, emit=3.0)
	b = Builder("salt_basilisk")
	b.bone("root", (0, 0, 0.42))
	b.bone("body", (0, 0.0, 0.44), "root")
	b.bone("neck", (0, -0.62, 0.46), "body")
	b.bone("head", (0, -0.9, 0.5), "neck")
	b.bone("jaw", (0, -0.94, 0.42), "head")
	b.bone("tail1", (0, 0.72, 0.42), "body")
	b.bone("tail2", (0, 1.14, 0.34), "tail1")
	b.bone("tail3", (0, 1.52, 0.26), "tail2")

	# a squat, heavy barrel of a body
	b.blob((0.96, 1.36, 0.5), (0, 0.04, 0.46), scale, "body", segs=(14, 9))
	b.blob((0.9, 0.62, 0.52), (0, -0.4, 0.48), scale, "body", segs=(12, 8))
	b.blob((0.84, 0.6, 0.48), (0, 0.5, 0.44), scale, "body", segs=(12, 8))
	b.blob((0.76, 1.44, 0.22), (0, 0.04, 0.27), belly, "body", segs=(12, 6))
	for y in (-0.36, -0.08, 0.2, 0.48):   # darker bands across the back
		b.blob((0.9, 0.12, 0.3), (0, y, 0.6), band, "body", segs=(12, 5))
	# salt crusted along the spine, with crystal clusters breaking out of it
	for y, w in ((-0.5, 0.44), (-0.2, 0.52), (0.1, 0.56), (0.4, 0.5), (0.66, 0.36)):
		b.blob((w, 0.34, 0.14), (rng.uniform(-0.03, 0.03), y, 0.7 - abs(y) * 0.05), crust, "body", rot=(0, rng.uniform(-8, 8), 0), segs=(8, 5))
	for k, (y, n_) in enumerate(((-0.52, 2), (-0.3, 3), (-0.06, 4), (0.18, 3), (0.42, 3), (0.64, 2))):
		for j in range(n_):
			x = (j - (n_ - 1) / 2) * 0.11 + rng.uniform(-0.03, 0.03)
			d = (x * 2.2 + rng.uniform(-0.15, 0.15), rng.uniform(0.05, 0.35), 1.0)
			ln = (0.3 if abs(x) < 0.06 else 0.2) * (1.25 - abs(y) * 0.5) * rng.uniform(0.8, 1.15)
			_crystal(b, (x, y + rng.uniform(-0.04, 0.04), 0.68 - abs(y) * 0.05), d, ln, 0.045 + 0.02 * (ln > 0.25),
					 crystal if (j + k) % 3 else crystal_b, "body", tip_mat=crystal_b)
	# neck and a broad, blunt head
	b.seg((0, -0.56, 0.48), (0, -0.92, 0.52), 0.25, 0.22, scale, "neck", sides=10)
	b.blob((0.42, 0.3, 0.12), (0, -0.74, 0.7), crust, "neck", segs=(8, 5))
	b.blob((0.54, 0.52, 0.32), (0, -1.02, 0.56), scale, "head", segs=(12, 8))
	b.blob((0.46, 0.46, 0.2), (0, -1.28, 0.52), scale, "head", segs=(10, 6))                  # upper snout
	b.blob((0.38, 0.4, 0.08), (0, -1.12, 0.7), band, "head", segs=(8, 4))                     # skull plate
	b.blob((0.4, 0.5, 0.06), (0, -1.14, 0.4), mouth, "head", segs=(8, 4))                     # mouth lining
	for s in (1, -1):
		b.blob((0.16, 0.14, 0.1), (0.19 * s, -1.08, 0.66), dark, "head", segs=(8, 5))            # sockets
		b.blob((0.11, 0.09, 0.08), (0.2 * s, -1.11, 0.67), eye, "head", segs=(8, 5))             # glowing pale eyes
		b.blob((0.2, 0.12, 0.06), (0.19 * s, -1.08, 0.72), crust, "head", rot=(0, -16 * s, 0), segs=(8, 4))  # crusted brow
		_crystal(b, (0.16 * s, -0.96, 0.7), (0.5 * s, 0.9, 0.7), 0.26, 0.045, crystal, "head", tip_mat=crystal_b)  # brow horns
		_crystal(b, (0.24 * s, -0.9, 0.62), (0.7 * s, 0.8, 0.6), 0.12, 0.035, crystal_b, "head")
		b.blob((0.04, 0.03, 0.03), (0.07 * s, -1.5, 0.56), dark, "head", segs=(5, 3))              # nostrils
		for k in range(4):   # upper teeth
			y = -1.44 + k * 0.1
			b.seg((0.17 * s - 0.02 * s * (3 - k), y, 0.44), (0.17 * s - 0.02 * s * (3 - k), y, 0.37), 0.022, 0.0, tooth, "head", sides=4)
	b.blob((0.46, 0.6, 0.14), (0, -1.2, 0.36), scale, "jaw", segs=(10, 6))
	b.blob((0.38, 0.5, 0.08), (0, -1.2, 0.3), belly, "jaw", segs=(8, 4))
	for s in (1, -1):
		for k in range(3):
			y = -1.38 + k * 0.12
			b.seg((0.16 * s, y, 0.4), (0.16 * s, y, 0.47), 0.022, 0.0, tooth, "jaw", sides=4)
	# a thick tail tapering out behind, crusted on top
	b.seg((0, 0.64, 0.44), (0, 1.14, 0.35), 0.24, 0.18, scale, "tail1", sides=10)
	b.seg((0, 1.12, 0.35), (0, 1.54, 0.27), 0.18, 0.12, scale, "tail2", sides=9)
	b.seg((0, 1.52, 0.27), (0, 2.0, 0.16), 0.12, 0.02, scale, "tail3", sides=8)
	b.blob((0.24, 0.4, 0.1), (0, 0.9, 0.6), crust, "tail1", segs=(8, 4))
	for bone, y, z, ln in (("tail1", 0.86, 0.6, 0.18), ("tail1", 1.02, 0.56, 0.14), ("tail2", 1.26, 0.48, 0.12), ("tail2", 1.44, 0.42, 0.09)):
		_crystal(b, (0, y, z - 0.03), (rng.uniform(-0.3, 0.3), 0.4, 1), ln, 0.035, crystal, bone, tip_mat=crystal_b)
	for bone, y in (("tail1", 0.96), ("tail2", 1.34), ("tail3", 1.7)):
		b.blob((0.34 - (y - 0.9) * 0.2, 0.08, 0.3 - (y - 0.9) * 0.14), (0, y, 0.34 - (y - 0.9) * 0.2), band, bone, segs=(8, 4))
	# four stubby, splayed legs
	for name_, (x, y) in BASILISK_LEGS.items():
		s = 1 if x > 0 else -1
		f = -1 if y < 0 else 1
		b.bone(name_, (x, y, 0.4), "root")
		elbow = (x + 0.3 * s, y + 0.04 * f, 0.34)
		foot = (x + 0.36 * s, y - 0.02, 0.06)
		b.blob((0.34, 0.36, 0.34), (x + 0.06 * s, y, 0.4), scale, name_, segs=(8, 6))            # shoulder / thigh
		b.seg((x, y, 0.4), elbow, 0.13, 0.11, scale, name_, sides=8)
		b.blob((0.2, 0.2, 0.2), elbow, band, name_, segs=(7, 5))
		b.seg(elbow, foot, 0.1, 0.08, scale, name_, sides=8)
		b.blob((0.24, 0.26, 0.1), (foot[0], foot[1] - 0.04, 0.05), scale, name_, segs=(8, 5))
		for k in (-1, 0, 1):
			b.seg((foot[0] + 0.07 * k, foot[1] - 0.14, 0.05), (foot[0] + 0.09 * k, foot[1] - 0.24, 0.01), 0.03, 0.0, dark, name_, sides=4)
	arm = b.build()

	def leg(name_, swing, lift=0.0):
		s = 1 if BASILISK_LEGS[name_][0] > 0 else -1
		return {name_: {"rot": (0, lift * s, -swing * s)}}

	def gait(t, amp, lift):
		out = {}
		for name_ in BASILISK_LEGS:
			ph = 0.0 if name_ in ("leg_fl", "leg_br") else 0.5
			out.update(leg(name_, amp * wave(t, 1, ph), lift * max(0.0, wave(t, 1, ph + 0.25))))
		return out

	def tail(t, amp, cycles=1.0, pitch=0.0):
		return {"tail1": {"rot": (pitch, 0, amp * wave(t, cycles))}, "tail2": {"rot": (pitch * 0.5, 0, amp * wave(t, cycles, -0.12))},
				"tail3": {"rot": (0, 0, amp * 1.2 * wave(t, cycles, -0.24))}}

	def idle(t):  # breathes slowly; the tongue-less mouth parts and closes, tasting the air
		taste = seq(t, [(0, 0), (0.55, 0), (0.62, 1), (0.72, 1), (0.8, 0)])
		return merge({"body": {"loc": (0, 0, 0.012 * wave(t)), "rot": (0, 0, 0)},
					  "neck": {"rot": (2 * wave(t, 1, 0.2), 0, 8 * wave(t, 0.5))}, "jaw": {"rot": (-10 * taste, 0, 0)}},
					 tail(t, 6, 0.5), gait(t, 1, 0))

	def walk(t):  # the lizard sway: the spine bends side to side with each stride
		return merge(gait(t, 26, 16), tail(t, 14),
					 {"body": {"rot": (0, 2 * wave(t, 2), 6 * wave(t, 1, 0.25))}, "root": {"loc": (0, 0, 0.012 * abs(wave(t, 2)))},
					  "neck": {"rot": (2 * wave(t, 2), 0, -7 * wave(t, 1, 0.25))}})

	def run(t):
		return merge(gait(t, 36, 22), tail(t, 20),
					 {"body": {"rot": (0, 3 * wave(t, 2), 9 * wave(t, 1, 0.25))}, "root": {"loc": (0, 0, 0.03 * abs(wave(t, 2)))},
					  "neck": {"rot": (-4, 0, -10 * wave(t, 1, 0.25))}})

	def attack(t):  # rear back with the jaws wide, then a lunging snap
		lunge = seq(t, [(0, 0), (0.25, -0.12), (0.42, 0.34), (0.6, 0.28), (1, 0)])
		head = seq(t, [(0, 0), (0.25, 18), (0.42, -12), (0.6, -6), (1, 0)])
		jaw = seq(t, [(0, 0), (0.25, -38), (0.4, -42), (0.46, 2), (0.7, 0)])
		return merge({"root": {"loc": (0, lunge * 0.5, 0.03 * max(0.0, lunge)), "rot": (seq(t, [(0, 0), (0.25, 5), (0.42, -4), (1, 0)]), 0, 0)},
					  "neck": {"loc": (0, lunge * 0.5, 0), "rot": (head * 0.5, 0, 0)}, "head": {"rot": (head, 0, 0)},
					  "jaw": {"rot": (jaw, 0, 0)}},
					 {"leg_bl": {"rot": (0, 0, 0)}}, tail(t, 12, 1.5, pitch=seq(t, [(0, 0), (0.25, 6), (0.42, -4), (1, 0)])))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.02 * k), "rot": (6 * k, 4 * k, 0)},
					  "neck": {"rot": (12 * k, 0, 10 * k)}, "jaw": {"rot": (-24 * k, 0, 0)}}, tail(t, 16 * k, 2), gait(t, 6 * k, 8 * k))

	def death(t):  # thrashes, then rolls over onto its back, legs up
		roll = seq(t, [(0.2, 0), (0.55, 95), (0.72, 176), (0.82, 180)])
		lift = seq(t, [(0.2, 0), (0.45, 0.34), (0.74, 0.02), (0.82, 0.05)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		out = merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)},
					 "neck": {"rot": (-20 * curl, 0, 16 * curl)}, "jaw": {"rot": (-26 * curl, 0, 0)}},
					tail(t, 18 * seq(t, [(0, 1), (0.4, 0)]), 3, pitch=-10 * curl))
		for i, name_ in enumerate(BASILISK_LEGS):
			out = merge(out, leg(name_, 8 * wave(t, 5, i * 0.2) * seq(t, [(0.7, 0), (0.8, 1), (1, 0.3)]), -35 * curl))
		return out

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 0.95, walk, True)
	clip(arm, "run", 0.55, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- bone giants and salt raiders (The Bleach)
# Bolt-ons for KayKit Rig_Medium bodies, in their mesh space like the gnoll's.

def bone_materials(titan=False):
	return {
		"bone": material("giant_bone", "f2ead4", 0.7),
		"bone_b": material("giant_bone_b", "ded2b4", 0.75),
		"bone_dark": material("giant_bone_dark", "a89a7a", 0.8),
		"crack": material("giant_crack", "4a4034", 0.9),
		"glow": material("titan_glow" if titan else "giant_glow", "9af0ff", 0.3, emit=2.5),
	}


def _bone_horn(b, pts, r0, r1, mats, ridges=True):
	"""A tapering horn or tusk along `pts`, ridged at every joint."""
	n = len(pts) - 1
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		a, c = r0 + (r1 - r0) * k / n, r0 + (r1 - r0) * (k + 1) / n
		b.seg(p, q, a, c, mats[k % len(mats)], "x", sides=7)
		if ridges and k < n - 1:
			b.blob((c * 2.2, c * 2.2, c * 2.2), q, mats[(k + 1) % len(mats)], "x", segs=(7, 5))


def _giant_skull(b, m, titan):
	"""Horns, tusks, a heavy brow and a spiked crest for a KayKit skeleton skull (helmet hidden)."""
	big = 1.1 if titan else 1.0
	bone, bone_b, dark = m["bone"], m["bone_b"], m["bone_dark"]
	for s in (1, -1):
		b.blob((0.4, 0.22, 0.16), (0.17 * s, -0.37, 1.8), bone_b, "x", rot=(0, 14 * s, 0), segs=(10, 6))   # heavy brow
		b.blob((0.13, 0.05, 0.1), (0.13 * s, -0.31, 1.64), m["glow"], "x", segs=(8, 5))                  # cold eyes
		# great horns sweeping out, up and forward from the temples
		pts = [(0.34 * s, 0.02, 1.9), (0.56 * s, 0.06, 2.02), (0.76 * s, 0.0, 2.2), (0.86 * s, -0.14, 2.42),
			   (0.84 * s, -0.34, 2.58)]
		pts = [(x * big, y * big, 1.9 + (z - 1.9) * big) for x, y, z in pts]
		_bone_horn(b, pts, 0.13 * big, 0.02, [bone, bone_b])
		b.seg(pts[-2], pts[-1], 0.05 * big, 0.015, dark, "x", sides=7)
		# tusks jutting up out of the jaw
		_bone_horn(b, [(0.15 * s, -0.36, 1.28), (0.26 * s, -0.54, 1.36), (0.32 * s, -0.62, 1.56), (0.3 * s, -0.6, 1.72)],
				   0.07 * big, 0.0, [bone, bone_b], ridges=False)
	# a crest of bone spikes down the middle of the skull
	for k, (y, h) in enumerate(((-0.24, 0.3), (-0.06, 0.42), (0.14, 0.38), (0.32, 0.28), (0.46, 0.18))):
		z = 2.16 - max(0.0, y) * 0.5 - (0.05 if y < -0.1 else 0)
		b.seg((0, y, z - 0.1), (0, y + 0.14, z + h * big), 0.09, 0.0, bone if k % 2 else bone_b, "x", sides=5)
	b.seg((0, -0.3, 2.1), (0, 0.5, 1.92), 0.06, 0.06, dark, "x", sides=5)                    # the ridge they grow from
	b.seg((0.12, -0.34, 2.05), (0.2, -0.1, 1.94), 0.012, 0.01, m["crack"], "x", sides=3)      # age cracks
	b.seg((-0.3, -0.2, 1.98), (-0.36, 0.06, 1.86), 0.012, 0.01, m["crack"], "x", sides=3)
	if titan:   # a crown of broken tusks
		_ring(b, (0, 0.02, 2.02), (0.44, 0.46), (0, 0), 0.06, dark, sides=16)
		for k in range(9):
			a = 2 * math.pi * (k + 0.5) / 9 - math.pi / 2
			base = Vector((0.44 * math.cos(a), 0.02 + 0.46 * math.sin(a), 2.02))
			out = Vector((math.cos(a), math.sin(a), 0))
			tall = (0.62, 0.3, 0.5, 0.24, 0.66, 0.28, 0.46, 0.32, 0.56)[k]
			tip = base + out * 0.12 + Vector((0, 0, tall))
			broken = k % 2 == 1
			b.seg(tuple(base), tuple(tip), 0.08, 0.05 if broken else 0.0, bone_b if k % 2 else bone, "x", sides=6)
			if broken:   # a jagged snapped end
				b.seg(tuple(tip), tuple(tip + out * 0.03 + Vector((0, 0, 0.07))), 0.045, 0.0, dark, "x", sides=4)
		b.blob((0.16, 0.1, 0.16), (0, -0.44, 2.04), m["glow"], "x", segs=(8, 5))                  # a pale gem at the front


def build_bone_giant_head():
	b = Builder("bone_giant_head")
	_giant_skull(b, bone_materials(), False)
	return b.build_static()


def build_bone_titan_head():
	b = Builder("bone_titan_head")
	_giant_skull(b, bone_materials(True), True)
	return b.build_static()


def build_bone_giant_chest():
	"""Shoulder plates bristling with bone spikes, and spikes down the spine."""
	m = bone_materials()
	b = Builder("bone_giant_chest")
	for s in (1, -1):
		b.blob((0.44, 0.5, 0.26), (0.36 * s, 0.0, 1.22), m["bone_b"], "x", rot=(0, 22 * s, 0), segs=(9, 6))   # scapula plates
		b.blob((0.32, 0.36, 0.12), (0.38 * s, 0.0, 1.32), m["bone"], "x", rot=(0, 24 * s, 0), segs=(8, 4))
		for d, ln in (((0.45, 0.1, 1.0), 0.46), ((0.9, -0.2, 0.55), 0.34), ((0.7, 0.4, 0.7), 0.32), ((0.3, -0.35, 0.9), 0.26)):
			base = Vector((0.4 * s, 0.0, 1.28))
			v = Vector((d[0] * s, d[1], d[2])).normalized()
			b.seg(tuple(base), tuple(base + v * ln), 0.07, 0.0, m["bone"], "x", sides=5)
	for k, z in enumerate((1.22, 1.06, 0.9)):   # vertebra spikes down the back
		b.seg((0, 0.26, z), (0, 0.5 + 0.02 * k, z + 0.16), 0.07, 0.0, m["bone_b"], "x", sides=5)
	return b.build_static()


def _bone_bracer(name, s):
	"""Rings of bone round a forearm with a spike jutting from them (s = side)."""
	m = bone_materials()
	b = Builder(name)
	for k in range(3):
		_wrap(b, ((0.5 + k * 0.07) * s, 0, 1.11), (0.1, 0.1), 0.06, 0.03, [m["bone"], m["bone_b"]][k % 2], rot=(0, 90, 0), sides=10)
	for d in ((0.2, 0, 1), (0.2, 0.9, 0.3), (0.2, -0.9, 0.3)):
		v = Vector((d[0] * s, d[1], d[2])).normalized()
		base = Vector((0.57 * s, 0, 1.11)) + v * 0.1
		b.seg(tuple(base), tuple(base + v * 0.2), 0.045, 0.0, m["bone"], "x", sides=5)
	return b.build_static()


def build_bone_bracer_l():
	return _bone_bracer("bone_bracer_l", 1)


def build_bone_bracer_r():
	return _bone_bracer("bone_bracer_r", -1)


def raider_materials(chief=False):
	return {
		"linen": material("raider_cloth", "dcc89c", 0.95),
		"linen_b": material("raider_cloth_b", "c4aa7c", 0.95),
		"linen_dirty": material("raider_cloth_dirty", "a88e64", 0.95),
		"gap": material("raider_gap", "1a1410", 0.95),
		"red": material("raider_red", "b02a1c", 0.85),
		"red_dark": material("raider_red_dark", "6a140c", 0.85),
		"brass": material("raider_brass", "c09448", 0.4),
		"lens": material("raider_lens", "3a2a18", 0.1),
		"glint": material("raider_glint", "f0d8a0", 0.1, emit=0.6),
		"bone": material("raider_bone", "eee4c8", 0.6),
		"bone_dark": material("raider_bone_dark", "3a3028", 0.8),
		"cord": material("raider_cord", "4a3424", 0.9),
	}


def build_raider_wrap():
	"""A sand-colored head wrap with a veil over the face and brass goggles over the eye slit (Rogue head hidden)."""
	import random
	m = raider_materials()
	rng = random.Random(31)
	b = Builder("raider_wrap")
	shape = lambda z: max(0.4, math.sqrt(max(0.0, 1 - ((z - 1.66) / 0.54) ** 2)))
	b.blob((0.96, 0.96, 0.96), (0, 0.02, 1.66), m["linen_b"], "x", segs=(14, 10))
	_wound(b, m, (0, 0.02, 0), (0.5, 0.5), 1.2, 2.1, rng, gap=(240, 300), gap_z=(1.6, 1.76), width=0.12, shape=shape)
	b.blob((0.6, 0.6, 0.26), (0, 0.04, 2.14), m["linen"], "x", segs=(10, 5))                   # crown
	_box(b, (0.56, 0.12, 0.14), (0, -0.44, 1.68), m["gap"])                                 # the eye slit
	for s in (1, -1):   # brass goggles
		c = (0.17 * s, -0.5, 1.69)
		b.seg((c[0], -0.46, c[2]), (c[0], -0.54, c[2]), 0.12, 0.13, m["brass"], "x", sides=12)
		b.seg((c[0], -0.52, c[2]), (c[0], -0.555, c[2]), 0.09, 0.09, m["lens"], "x", sides=12)
		b.blob((0.04, 0.02, 0.04), (c[0] + 0.03 * s, -0.56, c[2] + 0.04), m["glint"], "x", segs=(5, 3))
	b.seg((-0.06, -0.54, 1.69), (0.06, -0.54, 1.69), 0.03, 0.03, m["brass"], "x", sides=5)   # the bridge
	_ring(b, (0, 0.02, 1.7), (0.53, 0.53), (0, 0), 0.025, m["cord"], sides=18, gap=(12, 16))  # strap
	# the veil: a cloth hung from the slit down over the mouth and chin
	for s in (1, -1):   # folded down the middle so it hangs in a point
		_slab(b, [(0.0, -0.56, 1.6), (0.42 * s, -0.46, 1.6), (0.32 * s, -0.5, 1.22), (0.0, -0.62, 1.02)], 0.04, m["linen"])
	b.seg((0.0, -0.57, 1.58), (0.0, -0.62, 1.05), 0.02, 0.02, m["linen_b"], "x", sides=4)
	_ring(b, (0, 0.02, 1.58), (0.53, 0.53), (0, 0), 0.03, m["linen_dirty"], sides=18)
	_shell(b, (1.12, 1.04, 0.6), (0, 0.04, 1.12), m["linen_b"], lambda d: d.z > 0.0)        # a scarf round the shoulders
	# a tail of cloth hanging down the back
	_slab(b, [(-0.12, 0.46, 1.9), (0.12, 0.47, 1.88), (0.18, 0.6, 1.1), (0.0, 0.6, 1.02)], 0.035, m["linen_dirty"])
	return b.build_static()


def build_raider_chief_turban():
	"""A tall wrapped turban with a red band, a brooch and a trailing red tail, for a KayKit barbarian head."""
	import random
	m = raider_materials(True)
	rng = random.Random(37)
	b = Builder("raider_chief_turban")
	b.blob((1.06, 1.0, 0.7), (0, -0.02, 2.08), m["linen_b"], "x", segs=(14, 9))
	shape = lambda z: 1.0 - max(0.0, z - 2.1) * 0.55
	_wound(b, m, (0, -0.02, 0), (0.56, 0.52), 1.9, 2.6, rng, width=0.13, shape=shape)
	b.blob((0.7, 0.66, 0.46), (0, 0.0, 2.66), m["linen"], "x", segs=(12, 7))                   # the tall dome
	b.blob((0.34, 0.32, 0.3), (0, 0.02, 2.88), m["linen_b"], "x", segs=(8, 5))
	_wrap(b, (0, -0.02, 1.98), (0.58, 0.54), 0.12, 0.04, m["red"], rot=(-4, 0, 0), sides=18)   # red band
	_wrap(b, (0, -0.02, 2.36), (0.52, 0.48), 0.07, 0.04, m["red_dark"], rot=(6, 4, 0), sides=18)
	b.blob((0.2, 0.08, 0.2), (0, -0.58, 2.0), m["brass"], "x", segs=(8, 5))                    # brooch
	b.blob((0.1, 0.05, 0.1), (0, -0.62, 2.0), m["red"], "x", segs=(6, 4))
	b.seg((0.02, -0.56, 2.08), (0.1, -0.5, 2.62), 0.05, 0.0, m["bone"], "x", sides=5)           # a bone plume
	_slab(b, [(0.2, 0.46, 2.0), (0.36, 0.38, 2.0), (0.36, 0.5, 1.3), (0.22, 0.54, 1.24)], 0.04, m["red"])   # trailing tail
	return b.build_static()


def build_raider_chief_chest():
	"""A red sash across the chest and round the waist, and a necklace of bone trophies."""
	m = raider_materials(True)
	b = Builder("raider_chief_chest")
	_wrap(b, (0, 0.0, 0.94), (0.46, 0.4), 0.16, 0.04, m["red"], rot=(0, 38, 0), sides=18)    # over the shoulder
	_wrap(b, (0, 0.0, 0.6), (0.46, 0.4), 0.14, 0.04, m["red"], sides=18)                    # round the waist
	_slab(b, [(0.26, -0.36, 0.62), (0.38, -0.3, 0.62), (0.42, -0.34, 0.26), (0.3, -0.4, 0.3)], 0.03, m["red_dark"])
	_slab(b, [(0.36, -0.3, 0.6), (0.44, -0.2, 0.6), (0.5, -0.26, 0.34), (0.42, -0.34, 0.36)], 0.03, m["red"])
	# the necklace: a cord of teeth and claws round the neck, a small skull at the front
	pts = []
	for k in range(15):
		a = math.pi + math.pi * k / 14
		pts.append((0.42 * math.cos(a), 0.4 * math.sin(a) - 0.02, 1.2 + 0.14 * math.sin(a)))
	for p, q in zip(pts, pts[1:]):
		b.seg(p, q, 0.018, 0.018, m["cord"], "x", sides=4)
	for k, p in enumerate(pts[1:-1]):
		if k == 6:
			continue
		ln = 0.14 if k % 2 else 0.1
		b.seg(p, (p[0] * 1.04, p[1] - 0.03, p[2] - ln), 0.03, 0.0, m["bone"], "x", sides=4)
	sk = (0.0, -0.46, 1.0)
	b.blob((0.18, 0.14, 0.17), sk, m["bone"], "x", segs=(8, 6))
	for s in (1, -1):
		b.blob((0.05, 0.03, 0.05), (0.04 * s, -0.53, 1.02), m["bone_dark"], "x", segs=(5, 3))
	b.blob((0.1, 0.06, 0.05), (0, -0.5, 0.93), m["bone"], "x", segs=(6, 4))
	return b.build_static()


# ---------------------------------------------------------------- river trolls (The Weeping Throat)
# Bolt-ons for a repainted KayKit barbarian (its head hidden), in its mesh space
# like the gnoll's: a low, forward-thrust troll head, a mossy hump on the back
# to hunch it, a loincloth, and big clawed fists round the hands.

def troll_materials(chief=False, mountain=False):
	if mountain:
		return mountain_troll_materials()
	p = "troll_chief" if chief else "troll"
	return {
		"skin": material(f"{p}_skin", "5c7a48" if chief else "7e9470", 0.85),
		"skin_dark": material(f"{p}_skin_dark", "33472a" if chief else "4e5e44", 0.9),
		"moss": material(f"{p}_moss", "46682a", 0.95),
		"moss_b": material(f"{p}_moss_b", "6e8434", 0.95),
		"hair": material(f"{p}_hair", "22261c", 0.95),
		"tusk": material(f"{p}_tusk", "e6dcc0", 0.5),
		"eye": material(f"{p}_eye", "ff8a1e" if chief else "f0d040", 0.3, emit=1.6 if chief else 1.2),
		"socket": material(f"{p}_socket", "161c12", 0.9),
		"mouth": material(f"{p}_mouth", "2a1614", 0.9),
		"claw": material(f"{p}_claw", "3a3226", 0.6),
		"bone": material(f"{p}_bone", "e8dec4", 0.6),
		"cord": material(f"{p}_cord", "3e2e1e", 0.9),
		"hide": material(f"{p}_hide", "6a5238", 0.95),
		"hide_dark": material(f"{p}_hide_dark", "3e2e20", 0.95),
		"red": material(f"{p}_paint_red", "b02a1a", 0.8),
		"white": material(f"{p}_paint_white", "ece4d0", 0.8),
		"antler": material(f"{p}_antler", "d8c8a0", 0.6),
		"stone": material(f"{p}_stone", "7a8a8e", 0.5),
		"stone_b": material(f"{p}_stone_b", "4e6066", 0.5),
		"fur": material(f"{p}_fur", "5e4632", 0.95),
		"fur_b": material(f"{p}_fur_b", "3a2c20", 0.95),
		"fur_light": material(f"{p}_fur_light", "8e7658", 0.95),
	}


def mountain_troll_materials():
	"""The river troll's keys in High Terrace colors: blue-gray hide, the moss become white fur and hair."""
	p = "mtroll"
	return {
		"skin": material(f"{p}_skin", "8a9cac", 0.85),
		"skin_dark": material(f"{p}_skin_dark", "56667a", 0.9),
		"moss": material(f"{p}_moss", "eceeee", 0.95),
		"moss_b": material(f"{p}_moss_b", "c2c8ce", 0.95),
		"hair": material(f"{p}_hair", "f6f8f8", 0.95),
		"tusk": material(f"{p}_tusk", "f0e8d0", 0.5),
		"eye": material(f"{p}_eye", "8ae0ff", 0.3, emit=1.8),
		"socket": material(f"{p}_socket", "1a2230", 0.9),
		"mouth": material(f"{p}_mouth", "2a1a24", 0.9),
		"claw": material(f"{p}_claw", "2e2e36", 0.6),
		"bone": material(f"{p}_bone", "e8dec4", 0.6),
		"cord": material(f"{p}_cord", "3e2e1e", 0.9),
		"hide": material(f"{p}_hide", "7a6a5a", 0.95),
		"hide_dark": material(f"{p}_hide_dark", "46382c", 0.95),
		"red": material(f"{p}_paint_red", "2a6ab0", 0.8),
		"white": material(f"{p}_paint_white", "ece4d0", 0.8),
		"antler": material(f"{p}_antler", "d8c8a0", 0.6),
		"stone": material(f"{p}_stone", "b8d8e8", 0.3),
		"stone_b": material(f"{p}_stone_b", "6a8a9e", 0.4),
		"fur": material(f"{p}_fur", "e6e8e8", 0.95),
		"fur_b": material(f"{p}_fur_b", "a8b0b8", 0.95),
		"fur_light": material(f"{p}_fur_light", "ffffff", 0.95),
	}


def _troll_head(b, m, chief):
	sk, dk = m["skin"], m["skin_dark"]
	b.blob((0.8, 0.78, 0.64), (0, 0.06, 1.68), sk, "x", segs=(12, 9))                         # low, sloping cranium
	b.blob((0.74, 0.54, 0.5), (0, -0.26, 1.5), sk, "x", segs=(12, 8))                          # the face, thrust forward
	b.blob((0.82, 0.28, 0.18), (0, -0.46, 1.7), dk, "x", rot=(-10, 0, 0), segs=(10, 6))          # heavy brow
	b.blob((0.72, 0.5, 0.28), (0, -0.34, 1.18), sk, "x", segs=(10, 6))                          # underslung jaw
	b.blob((0.52, 0.1, 0.07), (0, -0.56, 1.3), m["mouth"], "x", segs=(10, 4))                   # a wide lipless mouth
	for s in (1, -1):
		b.blob((0.18, 0.08, 0.13), (0.16 * s, -0.5, 1.6), m["socket"], "x", segs=(8, 5))           # deep-set eyes
		b.blob((0.09, 0.05, 0.07), (0.16 * s, -0.535, 1.6), m["eye"], "x", segs=(6, 4))
		b.blob((0.22, 0.2, 0.18), (0.28 * s, -0.4, 1.42), sk, "x", segs=(8, 5))                    # heavy cheeks
		b.seg((0.36 * s, -0.04, 1.62), (0.8 * s, 0.08, 1.46), 0.13, 0.015, sk, "x", sides=5)      # long drooping ears
		b.seg((0.4 * s, -0.08, 1.62), (0.72 * s, 0.02, 1.49), 0.06, 0.01, dk, "x", sides=4)
		b.seg((0.2 * s, -0.6, 1.2), (0.24 * s, -0.66, 1.44), 0.055, 0.012, m["tusk"], "x", sides=5)   # small tusks up out of the jaw
	# the long hooked nose, drooping down over the mouth
	b.seg((0, -0.5, 1.66), (0, -0.8, 1.52), 0.1, 0.085, sk, "x", sides=8)
	b.seg((0, -0.8, 1.52), (0, -0.84, 1.3), 0.085, 0.055, sk, "x", sides=8)
	b.blob((0.14, 0.14, 0.16), (0, -0.82, 1.3), dk, "x", segs=(8, 6))
	b.blob((0.07, 0.06, 0.06), (0.07, -0.68, 1.6), dk, "x", segs=(5, 4))                        # a wart
	for x, y, z in ((0.24, -0.3, 1.86), (-0.3, -0.1, 1.9), (0.12, 0.24, 1.96)):
		b.blob((0.08, 0.08, 0.06), (x, y, z), dk, "x", segs=(5, 4))
	# stringy hair and river moss hanging from the scalp
	b.blob((0.5, 0.56, 0.14), (0, 0.12, 1.98), m["moss"], "x", rot=(14, 0, 0), segs=(10, 6))     # matted moss on the crown
	b.blob((0.24, 0.3, 0.1), (0.12, -0.1, 2.0), m["moss_b"], "x", rot=(-8, 10, 0), segs=(8, 5))
	strands = ((0.3, -0.1, 1.88, 0.5), (0.36, 0.12, 1.82, 0.7), (0.24, 0.3, 1.86, 0.8), (0.08, 0.38, 1.84, 0.9),
			   (-0.08, 0.36, 1.86, 0.75), (-0.24, 0.3, 1.86, 0.85), (-0.36, 0.1, 1.82, 0.6), (-0.3, -0.12, 1.88, 0.45),
			   (0.16, -0.24, 1.96, 0.35), (-0.14, -0.22, 1.97, 0.3))
	for k, (x, y, z, ln) in enumerate(strands):
		mat = m["hair"] if k % 3 else m["moss_b"]
		_kelp(b, (x, y, z), ln, mat, lean=(x * 0.25, 0.3 if y > 0 else -0.1), width=0.05)
	if chief:
		# war paint: red slashes down the cheeks, a white bar across the brow
		for s in (1, -1):
			for k in range(3):
				x = (0.22 + 0.07 * k) * s
				b.seg((x, -0.5 + 0.05 * k, 1.56), (x * 1.05, -0.46 + 0.05 * k, 1.36), 0.022, 0.018, m["red"], "x", sides=4)
			b.blob((0.24, 0.05, 0.06), (0.2 * s, -0.575, 1.72), m["white"], "x", rot=(0, 0, 10 * s), segs=(8, 4))
		b.seg((0, -0.58, 1.54), (0, -0.84, 1.44), 0.02, 0.02, m["red"], "x", sides=4)
		# a crown of river stones bound round the brow, antlers rising from it
		_ring(b, (0, 0.04, 1.9), (0.44, 0.42), (0, -8), 0.035, m["cord"], sides=18)
		for k in range(10):
			a = 2 * math.pi * k / 10 - math.pi / 2
			p = Vector((0.44 * math.cos(a), 0.04 + 0.42 * math.sin(a), 1.9 - 0.06 * math.sin(a)))
			sz = 0.16 if k == 0 else 0.12
			b.blob((sz, sz * 0.8, sz), tuple(p), m["stone"] if k % 2 else m["stone_b"], "x", segs=(7, 5))
		for s in (1, -1):
			beam = [(0.32 * s, 0.02, 1.96), (0.52 * s, 0.06, 2.24), (0.66 * s, 0.02, 2.54), (0.7 * s, -0.12, 2.78)]
			for k, (p, q) in enumerate(zip(beam, beam[1:])):
				b.seg(p, q, 0.06 - 0.015 * k, 0.045 - 0.015 * k, m["antler"], "x", sides=6)
			for base, tip in (((0.52 * s, 0.06, 2.24), (0.46 * s, -0.2, 2.44)), ((0.64 * s, 0.03, 2.48), (0.86 * s, -0.06, 2.66)),
							  ((0.66 * s, 0.02, 2.54), (0.56 * s, -0.16, 2.74))):
				b.seg(base, tip, 0.035, 0.008, m["antler"], "x", sides=5)
		b.blob((0.2, 0.14, 0.18), (0, -0.4, 2.0), m["bone"], "x", segs=(8, 6))                  # a small skull at the brow
		for s in (1, -1):
			b.blob((0.05, 0.03, 0.05), (0.045 * s, -0.47, 2.01), m["hair"], "x", segs=(5, 3))


def build_troll_head():
	b = Builder("troll_head")
	_troll_head(b, troll_materials(), False)
	return b.build_static()


def build_troll_chief_head():
	b = Builder("troll_chief_head")
	_troll_head(b, troll_materials(True), True)
	return b.build_static()


def _troll_back(b, m, chief):
	"""A great hump of muscle over the shoulders so the head hangs forward, grown over with moss."""
	sk = m["skin"]
	b.blob((0.84, 0.56, 0.54), (0, 0.22, 1.2), sk, "x", segs=(12, 8))
	for s in (1, -1):
		b.blob((0.46, 0.5, 0.42), (0.3 * s, 0.06, 1.24), sk, "x", segs=(10, 7))                 # bulging trapezius
	b.blob((0.7, 0.44, 0.2), (0, 0.3, 1.42), m["moss"], "x", rot=(-20, 0, 0), segs=(10, 6))
	b.blob((0.36, 0.3, 0.12), (0.18, 0.4, 1.3), m["moss_b"], "x", rot=(-40, 0, 0), segs=(8, 5))
	for x, y, z, ln in ((0.28, 0.44, 1.32, 0.34), (0.08, 0.5, 1.3, 0.5), (-0.14, 0.5, 1.3, 0.42), (-0.32, 0.4, 1.3, 0.3),
						(0.4, 0.2, 1.36, 0.26), (-0.42, 0.18, 1.36, 0.3)):
		_kelp(b, (x, y, z), ln, m["moss"] if ln > 0.33 else m["moss_b"], lean=(0.0, 0.2), width=0.045, parts=2)
	# a necklace of bones round the neck, a jawbone hanging at the front
	pts = []
	for k in range(15):
		a = math.pi + math.pi * k / 14
		pts.append((0.42 * math.cos(a), 0.42 * math.sin(a) - 0.02, 1.28 + 0.26 * math.sin(a)))
	for p, q in zip(pts, pts[1:]):
		b.seg(p, q, 0.018, 0.018, m["cord"], "x", sides=4)
	for k in (3, 5, 9, 11):   # a few teeth and claws strung on it
		p = pts[k]
		b.seg(p, (p[0] * 1.02, p[1] - 0.04, p[2] - (0.12 if k in (5, 9) else 0.08)), 0.03, 0.005, m["bone"], "x", sides=4)
	if chief:   # a skull
		b.blob((0.2, 0.16, 0.19), (0, -0.48, 0.92), m["bone"], "x", segs=(8, 6))
		for s in (1, -1):
			b.blob((0.05, 0.03, 0.05), (0.045 * s, -0.56, 0.94), m["hair"], "x", segs=(5, 3))
	else:       # a smooth river stone with a hole worn through it
		b.blob((0.18, 0.08, 0.16), (0, -0.47, 0.96), m["stone"], "x", segs=(8, 5))
		b.blob((0.06, 0.03, 0.06), (0, -0.51, 0.97), m["hair"], "x", segs=(5, 3))
	if chief:   # a fur mantle heaped over the shoulders
		_shell(b, (1.2, 1.1, 0.9), (0, 0.06, 1.2), m["fur"], lambda d: d.z > -0.05 and not (d.y < -0.55 and abs(d.x) < 0.5))
		for s in (1, -1):
			b.blob((0.5, 0.64, 0.34), (0.42 * s, 0.06, 1.3), m["fur"], "x", rot=(0, 18 * s, 0), segs=(10, 7))
			b.blob((0.34, 0.5, 0.18), (0.46 * s, 0.06, 1.44), m["fur_light"], "x", rot=(0, 22 * s, 0), segs=(8, 5))
		for k in range(9):   # ragged edge
			a = math.radians(-10 + k * 25)
			p = (0.6 * math.cos(a), 0.06 + 0.56 * math.sin(a), 1.16)
			_tuft(b, p, (math.cos(a) * 0.3, math.sin(a) * 0.3, -1), 0.2, 4, 0.3, [m["fur"], m["fur_b"]], 300 + k, width=0.04)
		b.blob((0.12, 0.1, 0.12), (0.34, -0.36, 1.2), m["bone"], "x", segs=(6, 4))             # the clasp: a knuckle bone


def build_troll_back():
	b = Builder("troll_back")
	_troll_back(b, troll_materials(), False)
	return b.build_static()


def build_troll_chief_back():
	b = Builder("troll_chief_back")
	_troll_back(b, troll_materials(True), True)
	return b.build_static()


def _troll_loincloth(b, m, chief):
	_wrap(b, (0, 0.0, 0.62), (0.47, 0.41), 0.1, 0.04, m["cord"] if not chief else m["fur_b"], sides=18)
	cloth, dark = (m["fur"], m["fur_b"]) if chief else (m["hide"], m["hide_dark"])
	_slab(b, [(-0.2, -0.44, 0.64), (0.2, -0.44, 0.64), (0.16, -0.47, 0.22), (0.0, -0.49, 0.16), (-0.16, -0.47, 0.22)], 0.04, cloth)
	_slab(b, [(-0.24, 0.42, 0.64), (0.24, 0.42, 0.64), (0.2, 0.46, 0.2), (-0.2, 0.46, 0.2)], 0.04, dark)
	for s in (1, -1):   # a strip hanging at each hip
		_slab(b, [(0.44 * s, -0.1, 0.62), (0.46 * s, 0.1, 0.62), (0.47 * s, 0.08, 0.38), (0.45 * s, -0.08, 0.4)], 0.03, dark)
	_kelp(b, (0.3, -0.34, 0.6), 0.3, m["moss_b"], width=0.035, parts=2)
	_kelp(b, (-0.1, 0.44, 0.6), 0.36, m["moss"], width=0.035, parts=2)
	if chief:
		b.blob((0.16, 0.1, 0.16), (0, -0.48, 0.62), m["stone"], "x", segs=(7, 5))


def build_troll_loincloth():
	b = Builder("troll_loincloth")
	_troll_loincloth(b, troll_materials(), False)
	return b.build_static()


def build_troll_chief_loincloth():
	b = Builder("troll_chief_loincloth")
	_troll_loincloth(b, troll_materials(True), True)
	return b.build_static()


def _troll_fist(name, s, chief, mountain=False):
	"""A knobbly fist with long dark claws round the KayKit hand (s = side), so the arms read long."""
	m = troll_materials(chief, mountain)
	b = Builder(name)
	b.blob((0.3, 0.3, 0.28), (0.86 * s, -0.02, 1.08), m["skin"], "x", segs=(10, 7))
	b.blob((0.2, 0.24, 0.24), (0.74 * s, 0.0, 1.1), m["skin"], "x", segs=(8, 6))                 # thick wrist
	for k, (y, z) in enumerate(((-0.13, 1.04), (-0.05, 1.0), (0.04, 1.0), (0.12, 1.04))):
		b.seg((0.96 * s, y, z), (1.1 * s, y * 1.2, z - 0.1), 0.035, 0.005, m["claw"], "x", sides=5)
	b.seg((0.8 * s, -0.16, 1.06), (0.84 * s, -0.28, 0.98), 0.035, 0.005, m["claw"], "x", sides=5)   # thumb claw
	for y in (-0.06, 0.06):
		b.blob((0.07, 0.07, 0.05), (0.9 * s, y, 1.2), m["skin_dark"], "x", segs=(5, 4))            # knuckles
	return b.build_static()


def build_troll_fist_l():
	return _troll_fist("troll_fist_l", 1, False)


def build_troll_fist_r():
	return _troll_fist("troll_fist_r", -1, False)


def build_troll_chief_fist_l():
	return _troll_fist("troll_chief_fist_l", 1, True)


def build_troll_chief_fist_r():
	return _troll_fist("troll_chief_fist_r", -1, True)


# ---------------------------------------------------------------- water and storm elementals (The Weeping Throat)

def clip_scaled(arm, name, seconds, pose_fn, loop):
	"""clip() that also keys each bone's scale: poses may carry "scale": (x, y, z) (the elementals collapse)."""
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
			pb.rotation_euler = (math.radians(pitch), math.radians(roll), math.radians(yaw))
			pb.location = p.get("loc", (0, 0, 0))
			pb.scale = p.get("scale", (1, 1, 1))
			for key in ("rotation_euler", "location", "scale"):
				pb.keyframe_insert(key, frame=f + 1)
	for fc in _fcurves(act):
		for kp in fc.keyframe_points:
			kp.interpolation = "LINEAR"
	return act


def merge_scaled(*poses):
	"""merge() that keeps "scale" too, multiplying where poses overlap."""
	out = merge(*poses)
	for p in poses:
		for bone, v in p.items():
			if "scale" in v:
				cur = out[bone].get("scale", (1, 1, 1))
				out[bone]["scale"] = tuple(a * b for a, b in zip(cur, v["scale"]))
	return out


def _zigzag(b, pts, r, mat, bone):
	for p, q in zip(pts, pts[1:]):
		b.seg(p, q, r, r * 0.8, mat, bone, sides=4)


def build_elemental(name="water_elemental", storm=False):
	"""A column of living water rising out of a pool: a swirl of currents spins round its trunk,
	a curling wave for a crest, two heavy arms. The storm spirit is the same shape in cloud and lightning."""
	import random
	rng = random.Random(53 if storm else 47)
	if storm:
		deep = material(f"{name}_deep", "2c3340", 0.5)
		mid = material(f"{name}_mid", "4a5668", 0.45)
		light = material(f"{name}_light", "8a98b0", 0.4, emit=0.15)
		foam = material(f"{name}_foam", "c8d0dc", 0.5, emit=0.1)
		eye = material(f"{name}_eye", "fff0a0", 0.2, emit=3.0)
		bolt = material(f"{name}_bolt", "ffd84a", 0.2, emit=1.6)
		cloud = material(f"{name}_cloud", "9aa4b4", 0.9)
		cloud_b = material(f"{name}_cloud_b", "c4cad4", 0.9)
	else:
		deep = material(f"{name}_deep", "1c5e80", 0.15)
		mid = material(f"{name}_mid", "3290b4", 0.12)
		light = material(f"{name}_light", "86d4e4", 0.1, emit=0.25)
		foam = material(f"{name}_foam", "e0f6fa", 0.3, emit=0.25)
		eye = material(f"{name}_eye", "e8ffff", 0.1, emit=4.0)
		bolt = None
	b = Builder(name)
	b.bone("root", (0, 0, 0.05))
	b.bone("pool", (0, 0, 0.05), "root")
	b.bone("low", (0, 0, 0.3), "root")
	b.bone("swirl", (0, 0, 0.3), "low")
	b.bone("mid", (0, 0, 0.95), "low")
	b.bone("chest", (0, 0, 1.45), "mid")
	b.bone("head", (0, -0.04, 1.92), "chest")

	# the pool it rises from: a flat swirl of water ringed with breaking wavelets
	b.blob((1.7, 1.7, 0.12), (0, 0, 0.05), deep, "pool", segs=(16, 6))
	b.blob((1.3, 1.3, 0.16), (0, 0, 0.08), mid, "pool", segs=(16, 6))
	for k in range(11):
		a = 2 * math.pi * k / 11
		r = 0.72 + 0.06 * (k % 2)
		c = Vector((r * math.cos(a), r * math.sin(a), 0.1))
		tang = Vector((-math.sin(a), math.cos(a), 0))
		b.blob((0.3, 0.3, 0.2), tuple(c), mid, "pool", rot=(0, 0, math.degrees(a)), segs=(8, 5))
		b.seg(tuple(c + Vector((0, 0, 0.06))), tuple(c + tang * 0.18 + Vector((0, 0, 0.16))), 0.07, 0.0, foam if k % 2 else light, "pool", sides=5)
	# the trunk: a column narrowing to the waist, then swelling into the chest
	b.seg((0, 0, 0.08), (0, 0, 0.98), 0.5, 0.3, deep, "low", sides=14)
	b.seg((0, 0, 0.1), (0, 0, 0.7), 0.56, 0.34, mid, "low", sides=14)
	b.seg((0, 0, 0.92), (0, 0, 1.45), 0.3, 0.42, deep, "mid", sides=14)
	b.blob((0.98, 0.72, 0.72), (0, 0, 1.6), mid, "chest", segs=(14, 9))
	b.blob((0.7, 0.4, 0.5), (0, -0.2, 1.62), light if not storm else mid, "chest", segs=(12, 7))   # the brighter breast
	for s in (1, -1):
		b.blob((0.42, 0.42, 0.42), (0.44 * s, 0.0, 1.76), mid, "chest", segs=(10, 7))
		b.blob((0.24, 0.24, 0.1), (0.46 * s, -0.02, 1.96), foam, "chest", segs=(8, 5))            # spray off the shoulders
	# currents: three streams spiral up round the trunk (three-fold, so a third of a turn loops)
	for h in range(3):
		pts = []
		for k in range(25):
			u = k / 24
			a = 2 * math.pi * (h / 3 + u * 1.25)
			r = 0.58 - 0.22 * u + 0.03 * math.sin(u * 9)
			pts.append(Vector((r * math.cos(a), r * math.sin(a), 0.14 + u * 1.12)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			w = 0.085 - 0.05 * k / 24
			b.seg(tuple(p), tuple(q), w, w * 0.94, light if (k // 3 + h) % 4 else foam, "swirl", sides=6)
		if storm:   # lightning runs along one of the streams
			for k in range(2, 22, 7):
				p = pts[k]
				_zigzag(b, [tuple(p), tuple(p + Vector((0.06, 0.02, 0.12))), tuple(p + Vector((-0.03, 0.0, 0.2))),
							tuple(p + Vector((0.04, -0.02, 0.32)))], 0.025, bolt, "swirl")
	for k in range(16):   # bubbles and flecks of foam on the trunk
		z = rng.uniform(0.3, 1.5)
		a = rng.uniform(0, 2 * math.pi)
		r = (0.46 - 0.16 * min(1.0, z / 0.95)) if z < 0.95 else (0.3 + 0.12 * (z - 0.95) / 0.5)
		bone = "low" if z < 0.95 else "mid"
		sz = rng.uniform(0.07, 0.13)
		b.blob((sz, sz, sz), (r * math.cos(a), r * math.sin(a), z), foam if k % 3 == 0 else light, bone, segs=(6, 4))
	# the head: a smooth dome with a breaking wave curling back off it for a crest
	b.blob((0.5, 0.48, 0.54), (0, -0.06, 2.04), mid, "head", segs=(12, 9))
	b.blob((0.36, 0.2, 0.3), (0, -0.24, 1.98), light if not storm else mid, "head", segs=(10, 6))
	for s in (1, -1):
		b.blob((0.13, 0.05, 0.07), (0.11 * s, -0.3, 2.07), eye, "head", rot=(0, 0, -12 * s), segs=(8, 5))
	crest = [(0, -0.22, 2.22), (0, -0.08, 2.42), (0, 0.14, 2.56), (0, 0.36, 2.54), (0, 0.5, 2.4), (0, 0.46, 2.26), (0, 0.34, 2.24)]
	for k, (p, q) in enumerate(zip(crest, crest[1:])):
		r0, r1 = 0.2 - 0.028 * k, 0.2 - 0.028 * (k + 1)
		b.seg(p, q, r0, r1, mid if k < 3 else light, "head", sides=8)
	for s in (1, -1):   # smaller wavelets along the sides of the crest
		side = [(0.16 * s, -0.12, 2.2), (0.24 * s, 0.04, 2.36), (0.28 * s, 0.24, 2.4), (0.3 * s, 0.4, 2.3), (0.26 * s, 0.4, 2.18)]
		for k, (p, q) in enumerate(zip(side, side[1:])):
			b.seg(p, q, 0.11 - 0.022 * k, 0.11 - 0.022 * (k + 1) + 0.005, light, "head", sides=6)
	b.blob((0.16, 0.16, 0.14), (0, 0.4, 2.2), foam, "head", segs=(8, 5))
	if storm:   # billowing thunderhead on the shoulders and behind the head
		for s in (1, -1):
			for k, (x, y, z, r) in enumerate(((0.46, 0.06, 2.0, 0.34), (0.62, 0.1, 1.86, 0.26), (0.32, 0.2, 2.06, 0.28), (0.5, -0.12, 1.98, 0.22))):
				b.blob((r, r, r * 0.8), (x * s, y, z), cloud if k % 2 else cloud_b, "chest", segs=(9, 6))
		for k, (x, y, z, r) in enumerate(((0, 0.26, 2.1, 0.44), (0.2, 0.3, 1.96, 0.3), (-0.2, 0.3, 1.96, 0.3), (0, 0.36, 1.84, 0.34))):
			b.blob((r, r, r * 0.8), (x, y, z), cloud_b if k % 2 else cloud, "chest", segs=(9, 6))
		for k in range(8):
			a = 2 * math.pi * (k + 0.3) / 8
			b.blob((0.34, 0.34, 0.22), (0.62 * math.cos(a), 0.62 * math.sin(a), 0.2), cloud if k % 2 else cloud_b, "pool", segs=(8, 5))
	if storm:   # a crown of jagged lightning
		for k in range(5):
			a = math.radians(-60 + 30 * k)
			base = Vector((0.2 * math.sin(a), -0.06 - 0.16 * math.cos(a), 2.22))
			tall = 0.44 if k == 2 else 0.32
			out = Vector((math.sin(a) * 0.3, -math.cos(a) * 0.2, 1)).normalized()
			side = Vector((math.cos(a), math.sin(a), 0)) * 0.06
			_zigzag(b, [tuple(base), tuple(base + out * tall * 0.4 + side), tuple(base + out * tall * 0.6 - side),
						tuple(base + out * tall)], 0.035, bolt, "head")
		for pts in (((0.2, -0.32, 1.7), (0.26, -0.36, 1.54), (0.18, -0.38, 1.44), (0.24, -0.34, 1.26)),
					((-0.24, -0.3, 1.64), (-0.14, -0.36, 1.52), (-0.2, -0.36, 1.4)),
					((0.34, 0.1, 0.9), (0.28, 0.2, 0.72), (0.4, 0.2, 0.58), (0.36, 0.26, 0.4)),
					((-0.36, 0.14, 0.76), (-0.44, 0.0, 0.58), (-0.38, 0.06, 0.4))):
			_zigzag(b, list(pts), 0.03, bolt, "chest" if pts[0][2] > 1.2 else "low")
	# two heavy arms of water hanging to the knees, fists like breakers
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"arm_{side}", (0.48 * s, 0, 1.76), "chest")
		b.bone(f"hand_{side}", (0.7 * s, -0.06, 1.3), f"arm_{side}")
		b.seg((0.48 * s, 0, 1.76), (0.7 * s, -0.06, 1.3), 0.19, 0.14, mid, f"arm_{side}", sides=10)
		b.blob((0.24, 0.24, 0.24), (0.7 * s, -0.06, 1.3), deep, f"hand_{side}", segs=(8, 6))
		b.seg((0.7 * s, -0.06, 1.3), (0.76 * s, -0.12, 0.94), 0.13, 0.19, mid, f"hand_{side}", sides=10)
		b.blob((0.42, 0.42, 0.44), (0.78 * s, -0.14, 0.82), deep, f"hand_{side}", segs=(10, 8))
		b.blob((0.3, 0.3, 0.2), (0.8 * s, -0.18, 0.92), light, f"hand_{side}", segs=(8, 5))
		for k, (dx, dy, dz, sz) in enumerate(((0.02, -0.04, 0.56, 0.12), (-0.08, 0.06, 0.52, 0.08), (0.1, 0.04, 0.58, 0.07))):
			b.blob((sz, sz, sz * 1.4), (0.78 * s + dx * s, -0.14 + dy, dz), foam if k else light, f"hand_{side}", segs=(6, 4))   # drips
		if storm:
			_zigzag(b, [(0.52 * s, -0.12, 1.7), (0.62 * s, -0.18, 1.52), (0.58 * s, -0.16, 1.4), (0.7 * s, -0.2, 1.3)], 0.025, bolt, f"arm_{side}")
			_zigzag(b, [(0.74 * s, -0.3, 1.1), (0.82 * s, -0.34, 0.96), (0.76 * s, -0.36, 0.86), (0.86 * s, -0.3, 0.72)], 0.025, bolt, f"hand_{side}")
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, 0, 0), "loc": (0, 0, 0)}, "arm_r": {"rot": (r, 0, 0)},
				"hand_l": {"rot": (bend, spread, 0)}, "hand_r": {"rot": (bend, -spread, 0)}}

	def body(t, lean, sway, spin):
		return {"low": {"rot": (lean + 2 * wave(t, 1, 0.25), sway * wave(t), 0)},
				"mid": {"rot": (lean * 0.4 + 2 * wave(t, 1, 0.5), -sway * 0.6 * wave(t, 1, 0.1), 3 * wave(t))},
				"chest": {"rot": (lean * 0.2, -sway * 0.4 * wave(t, 1, 0.2), -3 * wave(t, 1, 0.3))},
				"head": {"rot": (-lean * 0.5 + 3 * wave(t, 1, 0.6), 0, 5 * wave(t, 1, 0.1))},
				"swirl": {"rot": (0, 0, spin * t)}}

	def ripple(t, cycles=2):
		k = 1 + 0.05 * wave(t, cycles)
		return {"pool": {"rot": (0, 0, -360 / 11 * t), "scale": (k, k, 1 + 0.2 * wave(t, cycles, 0.25))}}

	def idle(t):
		return merge_scaled(body(t, 0, 3, 120), ripple(t), arms(6 * wave(t, 1, 0.1), 6 * wave(t, 1, 0.6), 4, 5 + 4 * wave(t)))

	def walk(t):   # glides forward, leaning into it, the arms swinging
		return merge_scaled(body(t, -8, 4, 240), ripple(t, 2), arms(18 * wave(t), -18 * wave(t), 4, 10))

	def run(t):
		return merge_scaled(body(t, -18, 5, 360), ripple(t, 3), arms(-30 + 10 * wave(t, 2), -30 - 10 * wave(t, 2), 8, 20))

	def attack(t):   # both arms heave up overhead and crash down like a wave
		up = seq(t, [(0, 0), (0.35, 165), (0.48, 175), (0.6, 55), (0.75, 45), (1, 0)])
		lean = seq(t, [(0, 0), (0.35, 10), (0.48, 12), (0.6, -22), (0.75, -18), (1, 0)])
		bend = seq(t, [(0, 0), (0.35, 30), (0.5, 20), (0.6, -10), (1, 0)])
		surge = seq(t, [(0, 0), (0.48, -0.05), (0.6, 0.3), (0.8, 0.22), (1, 0)])
		splash = seq(t, [(0.55, 1.0), (0.62, 1.25), (0.9, 1.0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "low": {"rot": (lean * 0.5, 0, 0)}, "mid": {"rot": (lean * 0.4, 0, 0)},
					  "chest": {"rot": (lean * 0.3, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
					  "swirl": {"rot": (0, 0, 240 * t)}, "pool": {"scale": (splash, splash, 1.0)}},
					 arms(up, up, 10, bend))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"low": {"rot": (10 * k, 6 * k, 0)}, "mid": {"rot": (8 * k, 0, 0)}, "head": {"rot": (12 * k, 0, 10 * k)},
					  "swirl": {"rot": (0, 0, 60 * t)}, "pool": {"scale": (1 + 0.1 * k, 1 + 0.1 * k, 1)}},
					 arms(-25 * k, -20 * k, 15 * k, -10 * k))

	def death(t):   # reels, then pours down into its own pool and spreads flat
		reel = seq(t, [(0, 0), (0.25, 14), (0.4, -10), (0.55, 0)])
		fall = seq(t, [(0.3, 0), (0.85, 1)])
		shrink = 1 - 0.9 * fall
		spread = 1 + 0.7 * seq(t, [(0.4, 0), (0.95, 1)])
		return merge_scaled({"low": {"rot": (reel, reel * 0.4, 0), "loc": (0, 0, -0.26 * fall), "scale": (1 + 0.3 * fall, 1 + 0.3 * fall, max(0.05, shrink))},
					  "mid": {"rot": (-reel * 0.6, 0, 0), "scale": (shrink, shrink, shrink)},
					  "head": {"rot": (reel, 0, 20 * fall)}, "swirl": {"rot": (0, 0, 200 * t), "scale": (1, 1, max(0.1, 1 - fall))},
					  "pool": {"scale": (spread, spread, 1 + 0.6 * fall)}},
					 arms(-40 * fall + reel, -30 * fall - reel, 30 * fall, 0))

	# the loops keep turning: t = 1 lands a whole third of a turn on, which looks the same as t = 0,
	# so they're sampled to t = 1 (loop False) instead of snapping back
	clip_scaled(arm, "idle", 3.0, idle, False)
	clip_scaled(arm, "walk", 1.2, walk, False)
	clip_scaled(arm, "run", 0.8, run, False)
	clip_scaled(arm, "attack", 1.0, attack, False)
	clip_scaled(arm, "hit", 0.45, hit, False)
	clip_scaled(arm, "death", 1.6, death, False)
	return arm


def build_storm_elemental():
	return build_elemental("storm_elemental", storm=True)


# ---------------------------------------------------------------- summoned elementals (the Magician's pets)
# Earth, fire and air, built on the water elemental's frame: a trunk of bones
# root > low > mid > chest > head with two arms (arm > hand), heads at the
# same heights so the four stand about as tall. Clips use clip_scaled so a
# death can shrink, spread or scatter the pieces.

def _on_bone(b, start, bone):
	"""Rebinds every part added since len(b.parts) was `start` to `bone` (the shared helpers bind to "x")."""
	for p in b.parts[start:]:
		p.vertex_groups[0].name = bone


def _rock(b, size, loc, mat, bone, rng, rot=(0, 0, 0), jitter=0.16, subdiv=1):
	"""A faceted boulder: an icosphere with its corners pushed in and out, then sized to `size`."""
	bm = bmesh.new()
	bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=0.5)
	for v in bm.verts:
		v.co *= 1 + rng.uniform(-jitter, jitter)
	m = Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot]), Vector(size))
	bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
	b._add(bm, mat, bone)


def _flame(b, base, direction, length, radius, mat, bone, bend=(0, 0, 0), sides=6, parts=3):
	"""A licking tongue of flame: a teardrop in `parts` pieces (swelling, then drawn to a point),
	each piece turned a little further by `bend`."""
	p = Vector(base)
	d = Vector(direction).normalized()
	bend = Vector(bend)
	for k in range(parts):
		q = p + d * (length / parts)
		r0 = radius * math.sin(math.pi * (0.25 + 0.75 * k / parts))
		r1 = radius * max(0.0, math.sin(math.pi * (0.25 + 0.75 * (k + 1) / parts)))
		b.seg(tuple(p), tuple(q), r0, r1, mat, bone, sides=sides)
		p = q
		d = (d + bend).normalized()


def build_earth_elemental():
	"""A hulking rock golem: a boulder for a torso, stone slabs for shoulders, a low head sunk between
	them, fists like millstones, moss in the cracks and an amber fire glowing out of its seams."""
	import random
	rng = random.Random(61)
	stone = material("earth_stone", "857c70", 0.95)
	stone_d = material("earth_stone_dark", "57504a", 0.95)
	stone_l = material("earth_stone_light", "a89e8c", 0.9)
	soil = material("earth_soil", "6e5236", 0.95)
	moss = material("earth_moss", "5a7032", 0.95)
	moss_b = material("earth_moss_b", "7c8a3a", 0.95)
	glow = material("earth_glow", "f07818", 0.4, emit=1.6)
	eye = material("earth_eye", "ffd46a", 0.2, emit=4.0)
	b = Builder("earth_elemental")
	b.bone("root", (0, 0, 0.05))
	b.bone("hips", (0, 0, 0.88), "root")
	b.bone("chest", (0, 0, 1.3), "hips")
	b.bone("head", (0, -0.2, 1.98), "chest")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"leg_{side}", (0.34 * s, 0, 0.86), "hips")
		b.bone(f"shoulder_{side}", (0.64 * s, 0, 2.0), "chest")
		b.bone(f"arm_{side}", (0.74 * s, 0, 1.86), "chest")
		b.bone(f"hand_{side}", (0.92 * s, -0.04, 1.36), f"arm_{side}")

	# stumpy legs: a thigh stone on a broad flat foot
	for s in (1, -1):
		leg = f"leg_{'l' if s > 0 else 'r'}"
		_rock(b, (0.5, 0.5, 0.56), (0.36 * s, 0.0, 0.6), stone, leg, rng)
		_rock(b, (0.56, 0.72, 0.34), (0.38 * s, -0.1, 0.19), stone_d, leg, rng, rot=(0, 0, 8 * s))
		_rock(b, (0.26, 0.24, 0.18), (0.42 * s, -0.4, 0.14), stone, leg, rng)   # a toe stone
		b.blob((0.3, 0.3, 0.1), (0.36 * s, 0.02, 0.87), soil, leg, segs=(8, 4))
	# the pelvis: a squat stone packed round with earth
	_rock(b, (1.0, 0.74, 0.52), (0, 0.02, 0.94), stone_d, "hips", rng)
	b.blob((1.06, 0.8, 0.3), (0, 0.02, 1.08), soil, "hips", segs=(12, 6))
	for k in range(5):
		a = 2 * math.pi * k / 5 + 0.4
		_rock(b, (0.2, 0.2, 0.16), (0.5 * math.cos(a), 0.36 * math.sin(a), 1.1), moss if k % 2 else moss_b, "hips", rng)
	# the torso: one great boulder, a lighter breastplate stone split by glowing seams, a hump behind
	_rock(b, (1.36, 1.0, 1.06), (0, 0.06, 1.58), stone, "chest", rng, jitter=0.1)
	_rock(b, (0.96, 0.42, 0.74), (0, -0.32, 1.52), stone_l, "chest", rng, jitter=0.08)
	_rock(b, (0.96, 0.66, 0.62), (0, 0.36, 1.84), stone_d, "chest", rng)
	_rock(b, (0.5, 0.4, 0.44), (0.4, 0.3, 1.36), stone_d, "chest", rng)
	_rock(b, (0.46, 0.4, 0.4), (-0.42, 0.26, 1.34), stone, "chest", rng)
	b.blob((0.18, 0.08, 0.2), (0, -0.52, 1.56), glow, "chest", segs=(8, 5))                   # the molten heart
	for pts in (((0, -0.54, 1.84), (0.06, -0.55, 1.72), (-0.02, -0.56, 1.62)),
				((0.02, -0.55, 1.46), (-0.06, -0.54, 1.36), (0.02, -0.52, 1.22)),
				((0.12, -0.54, 1.6), (0.22, -0.52, 1.66), (0.3, -0.5, 1.58), (0.38, -0.44, 1.64)),
				((-0.12, -0.54, 1.52), (-0.24, -0.52, 1.46), (-0.34, -0.48, 1.5)),
				((0.5, -0.24, 1.7), (0.56, -0.18, 1.56), (0.58, -0.14, 1.46))):
		_zigzag(b, list(pts), 0.028, glow, "chest")
	for k in range(9):   # moss and pebbles caught on the boulder
		a = rng.uniform(0.2, 2.9)
		z = rng.uniform(1.35, 1.95)
		loc = (0.62 * math.cos(a) * (1 if k % 2 else -1), 0.1 + 0.4 * math.sin(a), z)
		sz = rng.uniform(0.14, 0.24)
		if k % 3:
			b.blob((sz * 1.4, sz * 1.2, sz * 0.4), loc, moss if k % 2 else moss_b, "chest", segs=(7, 4))
		else:
			_rock(b, (sz, sz, sz * 0.8), loc, stone_l, "chest", rng)
	# stone slab shoulders, sloping off the boulder, moss grown over the top
	for s in (1, -1):
		sh = f"shoulder_{'l' if s > 0 else 'r'}"
		_rock(b, (0.8, 0.74, 0.32), (0.66 * s, 0.04, 2.02), stone_l, sh, rng, rot=(0, 16 * s, 0), jitter=0.08)
		_rock(b, (0.6, 0.6, 0.24), (0.7 * s, 0.1, 2.14), stone, sh, rng, rot=(0, 20 * s, 0))
		b.blob((0.5, 0.48, 0.12), (0.62 * s, 0.08, 2.24), moss, sh, rot=(0, 18 * s, 0), segs=(9, 5))
		b.blob((0.24, 0.24, 0.08), (0.84 * s, -0.14, 2.14), moss_b, sh, segs=(7, 4))
		_zigzag(b, [(0.52 * s, -0.3, 2.04), (0.66 * s, -0.33, 2.0), (0.78 * s, -0.3, 1.98)], 0.022, glow, sh)
	# the head: a blunt stone sunk low between the shoulders, a heavy brow over burning eyes
	_rock(b, (0.52, 0.5, 0.44), (0, -0.24, 2.02), stone, "head", rng, jitter=0.1)
	_rock(b, (0.58, 0.22, 0.16), (0, -0.44, 2.12), stone_d, "head", rng, jitter=0.08)
	_rock(b, (0.36, 0.2, 0.18), (0, -0.44, 1.86), stone_d, "head", rng)                      # the jaw
	for s in (1, -1):
		b.blob((0.12, 0.05, 0.07), (0.12 * s, -0.5, 2.03), eye, "head", rot=(0, 0, -10 * s), segs=(8, 5))
	b.blob((0.34, 0.3, 0.1), (0, -0.2, 2.24), moss_b, "head", segs=(8, 5))
	_zigzag(b, [(0, -0.47, 1.95), (0.03, -0.48, 1.9)], 0.02, glow, "head")                   # a glowing mouth crack
	# arms: stacked stones down to fists like millstones
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		_rock(b, (0.46, 0.44, 0.52), (0.82 * s, 0.0, 1.66), stone, arm, rng)
		_rock(b, (0.3, 0.3, 0.3), (0.76 * s, 0.02, 1.86), stone_d, arm, rng)
		_rock(b, (0.38, 0.38, 0.34), (0.92 * s, -0.04, 1.38), stone_d, hand, rng)          # elbow
		_rock(b, (0.54, 0.52, 0.56), (0.96 * s, -0.06, 1.1), stone, hand, rng)
		_rock(b, (0.7, 0.66, 0.54), (0.98 * s, -0.1, 0.8), stone_d, hand, rng, jitter=0.1)  # the fist
		for k in range(3):
			_rock(b, (0.18, 0.18, 0.16), ((0.84 + 0.14 * k) * s, -0.4, 0.74), stone_l, hand, rng)   # knuckles
		_zigzag(b, [(1.2 * s, -0.12, 1.2), (1.22 * s, -0.08, 1.06), (1.2 * s, -0.14, 0.96)], 0.022, glow, hand)
		b.blob((0.26, 0.24, 0.08), (0.84 * s, 0.02, 1.9), moss, arm, segs=(7, 4))
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, 0, 0)}, "hand_r": {"rot": (bend, 0, 0)}}

	def breathe(t):
		return {"chest": {"rot": (1.5 * wave(t), 0, 0)}, "head": {"rot": (-1.5 * wave(t), 0, 5 * wave(t, 1, 0.3))},
				"shoulder_l": {"rot": (0, 1.2 * wave(t), 0)}, "shoulder_r": {"rot": (0, -1.2 * wave(t), 0)}}

	def idle(t):
		return merge_scaled(breathe(t), {"hips": {"loc": (0, 0, -0.015 * (1 + wave(t)))}},
							arms(3 * wave(t, 1, 0.1), 3 * wave(t, 1, 0.6), 4, 6))

	def stride(t, swing, lean, bob):
		# a heavy stomp: the weight rolls onto each foot and everything drops as it lands
		drop = -bob * (0.5 + 0.5 * wave(t, 2, 0.25))
		return merge_scaled({"leg_l": {"rot": (swing * wave(t), 0, 0)}, "leg_r": {"rot": (-swing * wave(t), 0, 0)},
							 "hips": {"rot": (0, 5 * wave(t), 0), "loc": (0, 0, drop)},
							 "chest": {"rot": (lean, -3 * wave(t), -6 * wave(t))},
							 "head": {"rot": (-lean * 0.5, 0, 4 * wave(t))}},
							arms(-swing * 0.8 * wave(t), swing * 0.8 * wave(t), 5, 10))

	def walk(t):
		return stride(t, 20, -6, 0.07)

	def run(t):
		return stride(t, 32, -14, 0.1)

	def attack(t):   # both fists heave up overhead and come down together like a rockfall
		up = seq(t, [(0, 0), (0.42, 150), (0.52, 158), (0.64, 35), (0.8, 30), (1, 0)])
		lean = seq(t, [(0, 0), (0.42, 10), (0.52, 12), (0.64, -26), (0.8, -22), (1, 0)])
		sink = seq(t, [(0, 0), (0.42, 0.04), (0.64, -0.14), (0.85, -0.1), (1, 0)])
		surge = seq(t, [(0, 0), (0.52, -0.05), (0.64, 0.22), (0.85, 0.18), (1, 0)])
		bend = seq(t, [(0, 0), (0.42, 20), (0.6, -10), (1, 0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "hips": {"loc": (0, 0, sink), "rot": (lean * 0.3, 0, 0)},
							 "chest": {"rot": (lean * 0.7, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
							 "leg_l": {"rot": (-lean * 0.3 + 6, 0, 0)}, "leg_r": {"rot": (-lean * 0.3 - 6, 0, 0)}},
							arms(up, up, 8, bend))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"chest": {"rot": (9 * k, 5 * k, 6 * k)}, "head": {"rot": (8 * k, 0, 8 * k)},
							 "hips": {"loc": (0, -0.06 * k, 0)}}, arms(-14 * k, -10 * k, 8 * k, -8 * k))

	def death(t):   # staggers, then comes apart: legs buckle, the boulder drops, head and slabs tumble off
		reel = seq(t, [(0, 0), (0.15, 10), (0.3, -8), (0.4, 0)])
		f = seq(t, [(0.3, 0), (0.72, 1)])
		g = seq(t, [(0.42, 0), (0.88, 1)])
		pose = {"hips": {"loc": (0, 0, -0.76 * f), "rot": (0, 6 * f, 0)},
				"chest": {"rot": (reel - 14 * f, 4 * f, 0), "loc": (0, 0.06 * f, -0.44 * f),
						  "scale": (1 + 0.15 * f, 1 + 0.15 * f, 1 - 0.3 * f)},
				"head": {"rot": (-50 * g, 20 * g, 30 * g), "loc": (0.1 * g, 0.45 * g, -0.88 * g)}}
		for s, side in ((1, "l"), (-1, "r")):
			pose[f"leg_{side}"] = {"rot": (-8 * f, 60 * s * f, 0), "scale": (1, 1, 1 - 0.3 * f)}
			pose[f"shoulder_{side}"] = {"rot": (15 * g, -50 * s * g, 0), "loc": (-0.35 * s * g, -0.1 * g, -0.55 * g)}
			pose[f"arm_{side}"] = {"rot": (10 * g + reel, -75 * s * g, 0), "loc": (0, 0, -0.25 * g)}
			pose[f"hand_{side}"] = {"rot": (0, -20 * s * g, 0)}
		return merge_scaled(pose)

	clip_scaled(arm, "idle", 3.0, idle, True)
	clip_scaled(arm, "walk", 1.6, walk, True)
	clip_scaled(arm, "run", 1.0, run, True)
	clip_scaled(arm, "attack", 1.4, attack, False)
	clip_scaled(arm, "hit", 0.5, hit, False)
	clip_scaled(arm, "death", 2.0, death, False)
	return arm


def build_fire_elemental():
	"""A column of living flame rising out of a bed of coals: tongues of fire lick up its trunk and
	shoulders, a flickering crest of flame for hair, arms of fire ending in white-hot fists."""
	import random
	rng = random.Random(71)
	coal = material("fire_coal", "2a1812", 0.9)
	ember = material("fire_ember", "a8280a", 0.6, emit=0.9)
	red = material("fire_red", "d8321a", 0.5, emit=0.6)
	orange = material("fire_orange", "f86e14", 0.4, emit=0.9)
	yellow = material("fire_yellow", "ffc038", 0.3, emit=1.3)
	white = material("fire_white", "fff0b0", 0.2, emit=2.2)
	eye = material("fire_eye", "fffbe8", 0.1, emit=5.0)
	b = Builder("fire_elemental")
	b.bone("root", (0, 0, 0.05))
	b.bone("base", (0, 0, 0.05), "root")
	b.bone("flames", (0, 0, 0.1), "base")
	b.bone("low", (0, 0, 0.3), "root")
	b.bone("swirl", (0, 0, 0.3), "low")
	b.bone("mid", (0, 0, 0.95), "low")
	b.bone("chest", (0, 0, 1.45), "mid")
	b.bone("tongues", (0, 0.1, 1.7), "chest")
	b.bone("head", (0, -0.04, 1.92), "chest")
	b.bone("crest", (0, -0.04, 2.2), "head")

	# the bed of coals it burns out of (it stays, glowing, when the fire gutters)
	for k in range(20):
		a = 2 * math.pi * k / 20 + rng.uniform(-0.1, 0.1)
		r = rng.uniform(0.3, 0.78)
		sz = rng.uniform(0.18, 0.3)
		_rock(b, (sz, sz, sz * 0.6), (r * math.cos(a), r * math.sin(a), 0.07), coal if k % 3 else ember, "base", rng, jitter=0.2)
	b.blob((1.2, 1.2, 0.1), (0, 0, 0.04), ember, "base", segs=(14, 5))
	# a ring of low flames round the base
	for k in range(12):
		a = 2 * math.pi * (k + 0.5) / 12
		c = Vector((0.62 * math.cos(a), 0.62 * math.sin(a), 0.08))
		inward = Vector((-math.cos(a), -math.sin(a), 0))
		ln = 0.34 + 0.16 * (k % 3 == 0)
		_flame(b, tuple(c), tuple(Vector((0, 0, 1)) + inward * 0.35), ln, 0.12, red if k % 2 else orange, "flames", bend=tuple(inward * 0.3))
	# the trunk: flame widening down into the coals, swelling again into the chest
	b.seg((0, 0, 0.06), (0, 0, 0.8), 0.6, 0.34, red, "low", sides=14)
	b.seg((0, 0, 0.3), (0, 0, 1.02), 0.46, 0.3, orange, "low", sides=14)
	b.seg((0, 0, 0.92), (0, 0, 1.45), 0.3, 0.42, orange, "mid", sides=14)
	for k in range(10):   # tongues licking up off the trunk
		a = 2 * math.pi * k / 10
		z = 0.22 + 0.06 * (k % 3)
		r = 0.54 - 0.3 * (z - 0.06) / 0.74
		out = Vector((math.cos(a), math.sin(a), 0))
		_flame(b, tuple(out * r + Vector((0, 0, z))), tuple(Vector((0, 0, 1)) + out * 0.5), 0.46, 0.13,
			   red if k % 2 else orange, "low", bend=tuple(-out * 0.35))
	# the chest: an orange swell with a white-hot breast
	b.blob((0.98, 0.72, 0.72), (0, 0, 1.6), red, "chest", segs=(14, 9))
	b.blob((0.66, 0.4, 0.48), (0, -0.2, 1.62), orange, "chest", segs=(12, 7))
	b.blob((0.36, 0.2, 0.26), (0, -0.33, 1.64), white, "chest", segs=(10, 6))
	for s in (1, -1):
		b.blob((0.42, 0.42, 0.42), (0.44 * s, 0.0, 1.76), orange, "chest", segs=(10, 7))
	# spirals of brighter flame winding up the trunk (three-fold like the water's currents)
	for h in range(3):
		pts = []
		for k in range(25):
			u = k / 24
			a = 2 * math.pi * (h / 3 + u * 1.25)
			r = 0.56 - 0.22 * u + 0.03 * math.sin(u * 9)
			pts.append(Vector((r * math.cos(a), r * math.sin(a), 0.16 + u * 1.1)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			w = 0.08 - 0.05 * k / 24
			b.seg(tuple(p), tuple(q), w, w * 0.9, yellow if (k // 3 + h) % 4 else white, "swirl", sides=6)
	# tongues streaming up off the shoulders and back
	for s in (1, -1):
		for k, (dx, dy, ln) in enumerate(((0.0, 0.0, 0.52), (0.14, 0.12, 0.4), (-0.12, 0.14, 0.36))):
			base = (0.44 * s + dx * s, dy, 1.9)
			_flame(b, base, (0.25 * s, 0.35, 1), ln, 0.14, red if k else orange, "tongues", bend=(0, 0.2, 0))
			_flame(b, (base[0], base[1] - 0.02, base[2] + 0.02), (0.25 * s, 0.35, 1), ln * 0.6, 0.08, yellow, "tongues", bend=(0, 0.2, 0))
	for k, (x, z, ln) in enumerate(((0, 1.62, 0.6), (0.2, 1.5, 0.44), (-0.2, 1.5, 0.44))):
		_flame(b, (x, 0.3, z), (x, 1, 0.9), ln, 0.16, red, "tongues", bend=(0, 0.1, 0.3))
	# the head: a flame-dome with a white-hot face
	b.blob((0.48, 0.46, 0.52), (0, -0.06, 2.04), orange, "head", segs=(12, 9))
	b.blob((0.34, 0.2, 0.3), (0, -0.24, 1.98), yellow, "head", segs=(10, 6))
	for s in (1, -1):
		b.blob((0.12, 0.05, 0.07), (0.11 * s, -0.33, 2.05), eye, "head", rot=(0, 0, -14 * s), segs=(8, 5))
		b.blob((0.16, 0.08, 0.04), (0.12 * s, -0.34, 2.11), red, "head", rot=(0, -20 * s, 0), segs=(6, 4))   # scowling brows
	# the crest: a crown of flame tongues streaming up and back, tallest in the middle
	for k in range(7):
		x = (k - 3) * 0.075
		tall = 0.9 - 0.12 * abs(k - 3)
		base = (x, -0.12 + 0.04 * abs(k - 3), 2.16)
		direction = (x * 1.2, 0.35, 1)
		_flame(b, base, direction, tall, 0.13, red if k % 2 else orange, "crest", bend=(x * 0.3, 0.25, 0), sides=6, parts=4)
		_flame(b, (base[0], base[1] - 0.03, base[2] + 0.02), direction, tall * 0.55, 0.075, yellow, "crest", bend=(x * 0.3, 0.25, 0))
	# arms of fire: tongues trail up off the forearms, the fists burn white
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		b.bone(arm, (0.48 * s, 0, 1.76), "chest")
		b.bone(hand, (0.7 * s, -0.06, 1.3), arm)
		b.seg((0.48 * s, 0, 1.76), (0.7 * s, -0.06, 1.3), 0.19, 0.14, orange, arm, sides=10)
		b.blob((0.24, 0.24, 0.24), (0.7 * s, -0.06, 1.3), red, hand, segs=(8, 6))
		b.seg((0.7 * s, -0.06, 1.3), (0.76 * s, -0.12, 0.94), 0.13, 0.18, orange, hand, sides=10)
		b.blob((0.4, 0.4, 0.42), (0.78 * s, -0.14, 0.82), yellow, hand, segs=(10, 8))
		b.blob((0.26, 0.26, 0.26), (0.79 * s, -0.2, 0.82), white, hand, segs=(8, 6))
		for k, (z, ln) in enumerate(((1.5, 0.36), (1.2, 0.34), (0.98, 0.3))):
			base = (0.64 * s + 0.1 * s * k / 2, 0.08 + 0.02 * k, z)
			_flame(b, base, (0.4 * s, 0.6, 1), ln, 0.1, red, hand if z < 1.3 else arm, bend=(0, 0.2, 0.1))
		for k in range(4):   # flames rising off the fist
			a = 2 * math.pi * k / 4 + 0.4
			base = (0.78 * s + 0.14 * math.cos(a), -0.14 + 0.14 * math.sin(a), 0.92)
			_flame(b, base, (0.15 * math.cos(a), 0.15 * math.sin(a), 1), 0.28, 0.08, orange if k % 2 else red, hand)
	arm = b.build()

	def flick(t, n, phase, amp=0.1):
		return 1 + amp * wave(t, n, phase)

	def fire(t, n, spin):
		# everything flickers: crest, trunk tongues and the ring at the base stretch and shrink out of step
		c = flick(t, n, 0.0, 0.14)
		g = flick(t, n + 1, 0.3, 0.12)
		return {"crest": {"rot": (4 * wave(t, n, 0.2), 0, 3 * wave(t, n + 1)), "scale": (2 - c, 2 - c, c)},
				"tongues": {"scale": (1, 1, g), "rot": (5 * wave(t, n, 0.6), 0, 0)},
				"flames": {"rot": (0, 0, 360 / 12 * t), "scale": (1, 1, flick(t, n + 2, 0.5, 0.18))},
				"swirl": {"rot": (0, 0, spin * t), "scale": (1, 1, flick(t, n, 0.7, 0.05))},
				"low": {"scale": (flick(t, n + 1, 0.1, 0.04), flick(t, n + 1, 0.1, 0.04), 1)}}

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, 0, 0)}, "arm_r": {"rot": (r, 0, 0)},
				"hand_l": {"rot": (bend, spread, 0)}, "hand_r": {"rot": (bend, -spread, 0)}}

	def body(t, lean, sway):
		return {"low": {"rot": (lean + 2 * wave(t, 1, 0.25), sway * wave(t), 0)},
				"mid": {"rot": (lean * 0.4 + 2 * wave(t, 1, 0.5), -sway * 0.6 * wave(t, 1, 0.1), 3 * wave(t))},
				"chest": {"rot": (lean * 0.2, -sway * 0.4 * wave(t, 1, 0.2), -3 * wave(t, 1, 0.3))},
				"head": {"rot": (-lean * 0.5 + 3 * wave(t, 1, 0.6), 0, 5 * wave(t, 1, 0.1))}}

	def idle(t):
		return merge_scaled(body(t, 0, 3), fire(t, 9, 120), arms(6 * wave(t, 1, 0.1), 6 * wave(t, 1, 0.6), 4, 5 + 4 * wave(t)))

	def walk(t):
		return merge_scaled(body(t, -8, 4), fire(t, 4, 240), arms(18 * wave(t), -18 * wave(t), 4, 10))

	def run(t):
		return merge_scaled(body(t, -18, 5), fire(t, 3, 360), arms(-30 + 10 * wave(t, 2), -30 - 10 * wave(t, 2), 8, 20))

	def attack(t):   # both arms swing up and back, then lash down and across like whips, the hands snapping last
		up = seq(t, [(0, 0), (0.35, 140), (0.45, 150), (0.58, 30), (0.72, 15), (1, 0)])
		spread = seq(t, [(0, 0), (0.35, 40), (0.45, 45), (0.58, -30), (0.72, -25), (1, 0)])
		snap = seq(t, [(0, 0), (0.35, 50), (0.5, 60), (0.62, -45), (0.75, -20), (1, 0)])
		lean = seq(t, [(0, 0), (0.35, 10), (0.58, -20), (0.75, -16), (1, 0)])
		surge = seq(t, [(0, 0), (0.45, -0.05), (0.6, 0.25), (0.8, 0.2), (1, 0)])
		flare = seq(t, [(0.45, 1.0), (0.6, 1.35), (0.9, 1.0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "low": {"rot": (lean * 0.5, 0, 0)}, "mid": {"rot": (lean * 0.4, 0, 0)},
							 "chest": {"rot": (lean * 0.3, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
							 "crest": {"scale": (1, 1, flare)}, "tongues": {"scale": (1, 1, flare)}, "swirl": {"rot": (0, 0, 240 * t)},
							 "arm_l": {"rot": (up, spread, 0)}, "arm_r": {"rot": (up, -spread, 0)},
							 "hand_l": {"rot": (snap, 0, 0)}, "hand_r": {"rot": (snap, 0, 0)}}, fire(t, 4, 0))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"low": {"rot": (10 * k, 6 * k, 0)}, "mid": {"rot": (8 * k, 0, 0)}, "head": {"rot": (12 * k, 0, 10 * k)},
							 "crest": {"scale": (1, 1, 1 - 0.3 * k)}, "swirl": {"rot": (0, 0, 60 * t)}},
							arms(-25 * k, -20 * k, 15 * k, -10 * k))

	def death(t):   # flares, sways, then sinks and gutters out into the coals
		reel = seq(t, [(0, 0), (0.2, 12), (0.35, -8), (0.5, 0)])
		fall = seq(t, [(0.25, 0), (0.85, 1)])
		shrink = max(0.03, 1 - 0.97 * fall)
		flare = seq(t, [(0, 1.0), (0.15, 1.3), (0.3, 1.0), (0.7, 0.3), (0.95, 0.02)])
		n = 6
		return merge_scaled({"low": {"rot": (reel, reel * 0.4, 0), "loc": (0, 0, -0.25 * fall),
									 "scale": (1 + 0.2 * fall, 1 + 0.2 * fall, max(0.03, 1 - 0.95 * fall))},
							 "mid": {"rot": (-reel * 0.6, 0, 0), "scale": (shrink, shrink, shrink)},
							 "head": {"rot": (reel, 0, 20 * fall)},
							 "crest": {"scale": (1, 1, flare * flick(t, n, 0, 0.15))},
							 "tongues": {"scale": (1, 1, flare)},
							 "swirl": {"rot": (0, 0, 200 * t), "scale": (1, 1, max(0.05, 1 - fall))},
							 "flames": {"scale": (1, 1, max(0.05, flare * flick(t, n + 1, 0.4, 0.2)))}},
							arms(-40 * fall + reel, -30 * fall - reel, 30 * fall, 0))

	clip_scaled(arm, "idle", 3.0, idle, False)
	clip_scaled(arm, "walk", 1.2, walk, False)
	clip_scaled(arm, "run", 0.8, run, False)
	clip_scaled(arm, "attack", 1.0, attack, False)
	clip_scaled(arm, "hit", 0.45, hit, False)
	clip_scaled(arm, "death", 1.6, death, False)
	return arm


def build_air_elemental():
	"""A whirlwind with a will: a little tornado for legs, bands of wind whirling round a body of cloud,
	a cloudy head with pale blue eyes and wispy arms trailing streamers."""
	import random
	rng = random.Random(83)
	white = material("air_white", "eef3f8", 0.9, emit=0.05)
	pale = material("air_pale", "bccbdc", 0.85)
	blue = material("air_blue", "8aa2bc", 0.8)
	deep = material("air_deep", "5e7490", 0.8)
	eye = material("air_eye", "c8f0ff", 0.1, emit=4.0)
	b = Builder("air_elemental")
	b.bone("root", (0, 0, 0.05))
	b.bone("funnel", (0, 0, 0.05), "root")
	b.bone("low", (0, 0, 0.3), "root")
	b.bone("band_a", (0, 0, 0.8), "low")
	b.bone("mid", (0, 0, 0.95), "low")
	b.bone("band_b", (0, 0, 1.25), "mid")
	b.bone("chest", (0, 0, 1.45), "mid")
	b.bone("band_c", (0, 0, 1.62), "chest")
	b.bone("head", (0, -0.04, 1.92), "chest")

	# the tornado it rides on: rings widening upward, a streak of dust spiraling round them
	for k in range(9):
		z = 0.06 + k * 0.1
		r = 0.1 + 0.035 * k + 0.004 * k * k
		start = len(b.parts)
		_wrap(b, (0.03 * math.sin(k * 1.7), 0.03 * math.cos(k * 1.7), z), (r, r * 0.94), 0.07, 0.035,
			  [white, pale, blue][k % 3], rot=(6 * math.sin(k), 6 * math.cos(k), 0), sides=14)
		_on_bone(b, start, "funnel")
	for h in range(4):
		pts = []
		for k in range(19):
			u = k / 18
			a = 2 * math.pi * (h / 4 + u * 1.5)
			r = 0.12 + 0.44 * u * u + 0.02
			pts.append(Vector((r * math.cos(a), r * math.sin(a), 0.05 + u * 0.86)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			w = 0.02 + 0.03 * k / 18
			b.seg(tuple(p), tuple(q), w, w, deep if h % 2 else blue, "funnel", sides=4)
	# the body: a column of pale air thickening into a chest of cloud
	b.seg((0, 0, 0.3), (0, 0, 1.0), 0.14, 0.34, pale, "low", sides=12)
	b.seg((0, 0, 0.92), (0, 0, 1.45), 0.3, 0.42, pale, "mid", sides=14)
	b.blob((0.98, 0.72, 0.72), (0, 0, 1.6), white, "chest", segs=(14, 9))
	for k, (x, y, z, r) in enumerate(((0.44, 0.0, 1.78, 0.46), (-0.44, 0.0, 1.78, 0.46), (0.26, -0.18, 1.5, 0.36),
									  (-0.26, -0.18, 1.5, 0.36), (0, 0.24, 1.76, 0.5), (0.3, 0.22, 1.48, 0.34),
									  (-0.3, 0.22, 1.48, 0.34), (0, -0.2, 1.72, 0.32))):
		b.blob((r, r, r * 0.84), (x, y, z), white if k % 3 else pale, "chest", segs=(10, 7))
	# bands of wind whirling round the body, each tipped its own way
	for bone, z, rad, tilt, mats in (("band_a", 0.78, 0.44, (14, -8, 0), (white, blue)),
									  ("band_b", 1.24, 0.5, (-12, 10, 0), (pale, white)),
									  ("band_c", 1.62, 0.66, (10, 14, 0), (white, blue))):
		start = len(b.parts)
		_wrap(b, (0, 0, z), (rad, rad * 0.94), 0.09, 0.04, mats[0], rot=tilt, gap=(20, 110), sides=18)
		_wrap(b, (0, 0, z + 0.06), (rad * 0.92, rad * 0.88), 0.05, 0.03, mats[1], rot=tilt, gap=(200, 300), sides=16)
		_on_bone(b, start, bone)
		for k in range(3):   # wisps flying off the band
			a = 2 * math.pi * k / 3 + 0.5
			p = Vector((rad * math.cos(a), rad * math.sin(a), z))
			tang = Vector((-math.sin(a), math.cos(a), 0))
			b.seg(tuple(p), tuple(p + tang * 0.3 + Vector((math.cos(a), math.sin(a), 0.08)) * 0.1), 0.04, 0.0, mats[k % 2], bone, sides=4)
	# the head: a knot of cloud with a darker hollow for a face, pale blue eyes
	b.blob((0.5, 0.48, 0.52), (0, -0.04, 2.04), white, "head", segs=(12, 9))
	b.blob((0.34, 0.18, 0.28), (0, -0.23, 1.99), blue, "head", segs=(10, 6))
	for s in (1, -1):
		b.blob((0.12, 0.05, 0.06), (0.1 * s, -0.31, 2.03), eye, "head", rot=(0, 0, -12 * s), segs=(8, 5))
	for k, (x, y, z, r) in enumerate(((0.2, 0.04, 2.2, 0.28), (-0.2, 0.04, 2.22, 0.3), (0.0, 0.14, 2.3, 0.32),
									  (0.26, 0.12, 2.02, 0.24), (-0.26, 0.12, 2.02, 0.24), (0, 0.26, 2.12, 0.3))):
		b.blob((r, r, r * 0.84), (x, y, z), pale if k % 2 else white, "head", segs=(9, 6))
	for k in range(3):   # a wisp curling up off the crown
		a = (k - 1) * 0.5
		_flame(b, (0.08 * (k - 1), 0.16, 2.36), (math.sin(a) * 0.5, 0.6, 1), 0.46 - 0.08 * abs(k - 1), 0.06, pale, "head",
			   bend=(0, 0.5, -0.2), sides=5, parts=4)
	# wispy arms: thin streams of air ending in whirling fists, streamers trailing behind
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		b.bone(arm, (0.48 * s, 0, 1.76), "chest")
		b.bone(hand, (0.7 * s, -0.06, 1.3), arm)
		b.seg((0.48 * s, 0, 1.76), (0.7 * s, -0.06, 1.3), 0.16, 0.1, pale, arm, sides=10)
		b.blob((0.2, 0.2, 0.2), (0.7 * s, -0.06, 1.3), white, hand, segs=(8, 6))
		b.seg((0.7 * s, -0.06, 1.3), (0.76 * s, -0.12, 0.96), 0.1, 0.15, pale, hand, sides=10)
		b.blob((0.34, 0.34, 0.36), (0.78 * s, -0.14, 0.84), white, hand, segs=(10, 8))
		for k, (rad, z, tilt) in enumerate(((0.24, 0.84, (20, 10 * s, 0)), (0.2, 0.9, (-25, -15 * s, 0)))):
			start = len(b.parts)
			_wrap(b, (0.78 * s, -0.14, z), (rad, rad), 0.05, 0.03, blue if k else pale, rot=tilt, gap=(60, 150), sides=14)
			_on_bone(b, start, hand)
		for k, (dz, ln) in enumerate(((0.0, 0.5), (0.1, 0.4), (-0.08, 0.36))):   # streamers blown back off the fist
			_flame(b, (0.8 * s, -0.02, 0.84 + dz), (0.3 * s, 1, 0.3 + dz), ln, 0.06, [pale, white, blue][k], hand,
				   bend=(0.1 * s, 0.1, 0.3), sides=5, parts=4)
		for k in range(2):
			_flame(b, (0.56 * s, 0.1, 1.64 - 0.14 * k), (0.2 * s, 1, 0.2), 0.34, 0.05, [white, blue][k], arm, bend=(0, 0, 0.3), sides=5)
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, 0, 0)}, "arm_r": {"rot": (r, 0, 0)},
				"hand_l": {"rot": (bend, spread, 0)}, "hand_r": {"rot": (bend, -spread, 0)}}

	def wind(t, turns):
		# the funnel and bands whirl whole turns per clip (so every loop meets itself), bands at their own pace
		return {"funnel": {"rot": (0, 0, 360 * turns * t)},
				"band_a": {"rot": (4 * wave(t), 0, 360 * turns * t)},
				"band_b": {"rot": (0, 4 * wave(t, 1, 0.3), -360 * max(1, turns // 2) * t)},
				"band_c": {"rot": (3 * wave(t, 1, 0.6), 0, 360 * max(1, turns // 2) * t)}}

	def body(t, lean, sway, bob=0.04, cycles=1):
		return {"low": {"rot": (lean + 3 * wave(t, cycles, 0.25), sway * wave(t, cycles), 0), "loc": (0, 0, bob * wave(t, cycles * 2))},
				"mid": {"rot": (lean * 0.4 + 3 * wave(t, cycles, 0.5), -sway * 0.6 * wave(t, cycles, 0.1), 5 * wave(t, cycles))},
				"chest": {"rot": (lean * 0.2, -sway * 0.4 * wave(t, cycles, 0.2), -5 * wave(t, cycles, 0.3))},
				"head": {"rot": (-lean * 0.5 + 4 * wave(t, cycles, 0.6), 0, 8 * wave(t, cycles, 0.1))}}

	def idle(t):
		return merge_scaled(body(t, 0, 4, 0.05, 2), wind(t, 4), arms(8 * wave(t, 2, 0.1), 8 * wave(t, 2, 0.6), 6, 8 + 6 * wave(t, 2)))

	def walk(t):   # darts along, leaning well in
		return merge_scaled(body(t, -14, 5, 0.04), wind(t, 2), arms(-10 + 20 * wave(t), -10 - 20 * wave(t), 8, 14))

	def run(t):
		return merge_scaled(body(t, -26, 6, 0.05), wind(t, 2), arms(-50 + 8 * wave(t, 2), -50 - 8 * wave(t, 2), 14, 24))

	def attack(t):   # draws both arms back and up, then drives them forward in a gust
		up = seq(t, [(0, 0), (0.3, 120), (0.4, 128), (0.52, 70), (0.7, 62), (1, 0)])
		spread = seq(t, [(0, 0), (0.3, 30), (0.4, 34), (0.52, -12), (0.7, -8), (1, 0)])
		lean = seq(t, [(0, 0), (0.3, 14), (0.4, 16), (0.52, -24), (0.72, -20), (1, 0)])
		surge = seq(t, [(0, 0), (0.4, -0.08), (0.52, 0.36), (0.75, 0.3), (1, 0)])
		gust = seq(t, [(0.4, 1.0), (0.52, 1.4), (0.85, 1.0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "low": {"rot": (lean * 0.5, 0, 0)}, "mid": {"rot": (lean * 0.4, 0, 0)},
							 "chest": {"rot": (lean * 0.3, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
							 "band_a": {"scale": (gust, gust, 1)}, "band_b": {"scale": (gust, gust, 1)}, "band_c": {"scale": (gust, gust, 1)},
							 "arm_l": {"rot": (up, spread, 0)}, "arm_r": {"rot": (up, -spread, 0)},
							 "hand_l": {"rot": (-10, 0, 0)}, "hand_r": {"rot": (-10, 0, 0)}}, wind(t, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"low": {"rot": (12 * k, 8 * k, 0)}, "mid": {"rot": (10 * k, 0, 0)}, "head": {"rot": (14 * k, 0, 12 * k)},
							 "band_c": {"scale": (1 + 0.2 * k, 1 + 0.2 * k, 1)}}, wind(t, 1), arms(-30 * k, -24 * k, 18 * k, -12 * k))

	def death(t):   # spins apart: the bands fly out and thin to wisps, the cloud thins and drifts away
		reel = seq(t, [(0, 0), (0.2, 14), (0.35, -8), (0.5, 0)])
		d = seq(t, [(0.2, 0), (0.95, 1)])
		thin = max(0.05, 1 - 0.95 * d)
		wide = 1 + 1.6 * d
		spin = 720 * seq(t, [(0, 0), (1, 1)])
		return merge_scaled({"funnel": {"rot": (0, 0, spin), "scale": (1 + 0.6 * d, 1 + 0.6 * d, thin)},
							 "low": {"rot": (reel, reel * 0.4, 0), "loc": (0, 0, -0.2 * d), "scale": (1 - 0.7 * d, 1 - 0.7 * d, max(0.3, 1 - 0.6 * d))},
							 "mid": {"rot": (-reel * 0.6, 0, 0), "scale": (thin, thin, thin)},
							 "band_a": {"rot": (6 * d, 0, spin), "scale": ((1 + 0.8 * d) / (1 - 0.7 * d), (1 + 0.8 * d) / (1 - 0.7 * d), thin), "loc": (0, 0, 0.3 * d)},
							 "band_b": {"rot": (-15 * d, 10 * d, -spin), "scale": (wide * 1.2, wide * 1.2, thin), "loc": (0, 0, 0.8 * d)},
							 "band_c": {"rot": (10 * d, -20 * d, spin), "scale": (wide * 1.4, wide * 1.4, thin), "loc": (0, 0, 1.2 * d)},
							 "head": {"rot": (reel, 0, 40 * d), "loc": (0, 0, 0.4 * d)}},
							arms(-40 * d + reel, -30 * d - reel, 40 * d, 0))

	clip_scaled(arm, "idle", 2.0, idle, False)
	clip_scaled(arm, "walk", 1.0, walk, False)
	clip_scaled(arm, "run", 0.6, run, False)
	clip_scaled(arm, "attack", 0.8, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.6, death, False)
	return arm


# ---------------------------------------------------------------- giant poison frog (The Weeping Throat)

def build_frog():
	back = material("frog_back", "f4cc1c", 0.3)
	back_b = material("frog_back_b", "ff9a12", 0.3)
	spot = material("frog_spot", "121212", 0.3)
	leg = material("frog_leg", "2a6ee0", 0.3)
	leg_dark = material("frog_leg_dark", "163e96", 0.35)
	belly = material("frog_belly", "4a86e8", 0.4)
	mouth = material("frog_mouth", "d2566a", 0.5)
	eye = material("frog_eye", "0c0c0e", 0.05)
	glint = material("frog_glint", "ffffff", 0.1, emit=0.8)
	b = Builder("giant_frog")
	b.bone("root", (0, 0, 0.36))
	b.bone("body", (0, 0.1, 0.36), "root")
	b.bone("head", (0, -0.3, 0.46), "body")
	b.bone("jaw", (0, -0.26, 0.38), "head")
	b.bone("tongue", (0, -0.5, 0.4), "head")

	# a sleek body sitting up at the front, glossy yellow with black blotches
	b.blob((0.84, 1.0, 0.56), (0, 0.12, 0.42), back, "body", rot=(-14, 0, 0), segs=(14, 9))
	b.blob((0.74, 0.86, 0.3), (0, 0.08, 0.28), belly, "body", rot=(-14, 0, 0), segs=(12, 6))
	b.blob((0.94, 0.62, 0.44), (0, -0.44, 0.54), back, "head", segs=(14, 8))
	b.blob((0.9, 0.56, 0.18), (0, -0.46, 0.38), belly, "jaw", segs=(12, 6))                   # throat and lower jaw
	b.blob((0.8, 0.46, 0.08), (0, -0.5, 0.45), mouth, "jaw", segs=(10, 5))                   # inside of the mouth
	b.seg((-0.38, -0.66, 0.47), (0.38, -0.66, 0.47), 0.018, 0.018, spot, "head", sides=4)    # the long mouth line
	b.seg((0, -0.3, 0.42), (0, -0.66, 0.42), 0.07, 0.06, mouth, "tongue", sides=6)           # tongue, hidden until it shoots
	b.blob((0.16, 0.14, 0.12), (0, -0.66, 0.42), mouth, "tongue", segs=(8, 5))
	for s in (1, -1):
		b.blob((0.3, 0.3, 0.3), (0.3 * s, -0.5, 0.72), back_b, "head", segs=(10, 7))             # eye bulges
		b.blob((0.27, 0.27, 0.27), (0.32 * s, -0.54, 0.76), eye, "head", segs=(12, 8))           # big glossy black eyes
		b.blob((0.07, 0.04, 0.06), (0.36 * s, -0.66, 0.84), glint, "head", segs=(5, 3))
		b.blob((0.04, 0.03, 0.03), (0.07 * s, -0.72, 0.58), spot, "head", segs=(5, 3))            # nostrils
		b.blob((0.2, 0.7, 0.2), (0.4 * s, 0.1, 0.46), back_b, "body", rot=(-14, 0, 12 * s), segs=(8, 6))  # orange flank stripes
	for x, y, z, w in ((0, 0.04, 0.72, 0.28), (0.22, 0.3, 0.62, 0.2), (-0.2, 0.36, 0.6, 0.22), (0.16, -0.14, 0.72, 0.16),
					   (-0.2, -0.1, 0.72, 0.18), (0, 0.5, 0.48, 0.2), (0.34, 0.0, 0.58, 0.14), (-0.34, 0.12, 0.56, 0.16),
					   (0.0, -0.4, 0.77, 0.16), (0.22, -0.34, 0.72, 0.1), (-0.2, -0.3, 0.73, 0.1)):
		b.blob((w, w * 1.3, 0.06), (x, y, z), spot, "head" if y < -0.25 else "body", rot=(-14, x * 40, 0), segs=(8, 4))

	legs = {"leg_fl": (0.28, -0.36), "leg_fr": (-0.28, -0.36), "leg_bl": (0.36, 0.34), "leg_br": (-0.36, 0.34)}
	for name_, (x, y) in legs.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, 0.32), "root")
		if y < 0:   # front: slim arms straight down, round toe pads
			b.seg((x, y, 0.36), (x + 0.1 * s, y - 0.06, 0.05), 0.07, 0.05, leg, name_, sides=6)
			for k in (-1, 0, 1):
				tip = (x + (0.12 + 0.08 * k) * s, y - 0.2, 0.03)
				b.seg((x + 0.1 * s, y - 0.08, 0.04), tip, 0.025, 0.02, leg_dark, name_, sides=4)
				b.blob((0.07, 0.07, 0.05), tip, leg, name_, segs=(6, 4))
		else:       # back: long folded thighs, shins forward, long toes
			b.blob((0.28, 0.6, 0.3), (x + 0.1 * s, y + 0.02, 0.28), leg, name_, rot=(16, 0, 0), segs=(10, 7))
			b.blob((0.12, 0.26, 0.06), (x + 0.14 * s, y + 0.06, 0.42), spot, name_, segs=(6, 4))
			b.seg((x + 0.16 * s, y + 0.24, 0.14), (x + 0.22 * s, y - 0.26, 0.08), 0.07, 0.05, leg, name_, sides=6)
			b.seg((x + 0.22 * s, y - 0.26, 0.08), (x + 0.26 * s, y - 0.36, 0.03), 0.05, 0.04, leg_dark, name_, sides=5)
			for k in (-1, 0, 1):
				tip = (x + (0.26 + 0.12 * k) * s, y - 0.56, 0.03)
				b.seg((x + 0.26 * s, y - 0.36, 0.03), tip, 0.028, 0.02, leg_dark, name_, sides=4)
				b.blob((0.07, 0.07, 0.05), tip, leg, name_, segs=(6, 4))
	arm = b.build()

	def legs_pose(front, back):
		return {"leg_fl": {"rot": (front, 0, 0)}, "leg_fr": {"rot": (front, 0, 0)},
				"leg_bl": {"rot": (back, 0, 0)}, "leg_br": {"rot": (back, 0, 0)}}

	def hop(t, height, reach, forward):
		air = max(0.0, math.sin(math.pi * min(1.0, max(0.0, (t - 0.15) / 0.5))))
		kick = seq(t, [(0, 0), (0.12, 0.25), (0.3, -1), (0.6, 0), (1, 0)])
		pitch = seq(t, [(0, 0), (0.12, -4), (0.3, 14), (0.55, -10), (0.7, 0)])
		squash = seq(t, [(0, 0), (0.12, -0.05), (0.3, 0), (0.65, 0), (0.72, -0.06), (0.9, 0)])
		drift = forward * (seq(t, [(0.15, 0), (0.65, 1)]) - 0.5)   # surges ahead in the air, drifts back on the ground
		return merge({"root": {"loc": (0, drift, height * air + squash), "rot": (pitch, 0, 0)},
					  "head": {"rot": (-pitch * 0.4, 0, 0)}},
					 legs_pose(seq(t, [(0, 0), (0.3, -20), (0.55, reach), (0.7, 0)]), 65 * kick))

	def idle(t):   # the throat pumps; now and then it blinks its body down and up
		gulp = max(0.0, wave(t, 3))
		return {"body": {"loc": (0, 0, 0.01 * wave(t))}, "jaw": {"loc": (0, 0, -0.03 * gulp)},
				"head": {"rot": (3 * wave(t, 1, 0.3), 0, 6 * wave(t, 0.5))}}

	def walk(t):
		return hop(t, 0.3, 28, 0.18)

	def run(t):
		return hop(t, 0.5, 38, 0.3)

	def attack(t):   # crouch, lunge with the mouth gaping, the tongue lashing out and snapping back
		lunge = seq(t, [(0, 0), (0.28, -0.08), (0.42, 0.38), (0.7, 0.3), (1, 0)])
		pitch = seq(t, [(0, 0), (0.28, -8), (0.42, 14), (0.7, 4), (1, 0)])
		jaw = seq(t, [(0, 0), (0.3, -8), (0.4, -42), (0.6, -36), (0.7, 2), (0.8, 0)])
		tongue = seq(t, [(0, 0), (0.36, 0), (0.46, 1.0), (0.54, 0.95), (0.66, 0)])
		return merge({"root": {"loc": (0, lunge, 0.16 * max(0.0, lunge)), "rot": (pitch, 0, 0)},
					  "jaw": {"rot": (jaw, 0, 0)}, "tongue": {"loc": (0, tongue, -0.04 * tongue)},
					  "head": {"rot": (-jaw * 0.3, 0, 0)}},
					 legs_pose(seq(t, [(0, 0), (0.28, -12), (0.42, 30), (1, 0)]), seq(t, [(0, 0), (0.28, 14), (0.42, -55), (1, 0)])))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, -0.04 * k), "rot": (-8 * k, 6 * k, 0)},
					  "head": {"rot": (-10 * k, 0, 8 * k)}, "jaw": {"rot": (-16 * k, 0, 0)}}, legs_pose(10 * k, 10 * k))

	def death(t):   # a last leap that ends on its back, legs twitching
		roll = seq(t, [(0.1, 0), (0.5, 100), (0.68, 176), (0.8, 180)])
		lift = seq(t, [(0.1, 0), (0.35, 0.36), (0.72, 0.1), (0.8, 0.12)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		twitch = 10 * wave(t, 6) * seq(t, [(0.75, 0), (0.85, 1), (1, 0)])
		return merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)}, "jaw": {"rot": (-20 * curl, 0, 0)},
					  "head": {"rot": (-10 * curl, 0, 0)}, "tongue": {"loc": (0, 0.3 * curl, 0)}},
					 legs_pose(-20 * curl + twitch, -70 * curl - twitch))

	clip(arm, "idle", 2.2, idle, True)
	clip(arm, "walk", 0.8, walk, True)
	clip(arm, "run", 0.55, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.2, death, False)
	return arm


# ---------------------------------------------------------------- river crocodiles (The Weeping Throat)

CROC_LEGS = {"leg_fl": (0.3, -0.42), "leg_fr": (-0.3, -0.42), "leg_bl": (0.32, 0.36), "leg_br": (-0.32, 0.36)}
CROC_TAIL = ("tail1", "tail2", "tail3")


def build_croc(name="river_croc", ancient=False):
	"""Long and low, about 3 m snout to tail. The ancient one is the same beast grown old:
	pale scarred hide under moss and barnacles, broken teeth, eyes that burn."""
	import random
	rng = random.Random(61 if ancient else 59)
	if ancient:
		hide = material(f"{name}_hide", "5e6448", 0.9)
		dark = material(f"{name}_dark", "3e422e", 0.9)
		scute = material(f"{name}_scute", "4a4c36", 0.85)
		belly = material(f"{name}_belly", "c8c0a0", 0.9)
		eye = material(f"{name}_eye", "ffd21e", 0.2, emit=3.5)
	else:
		hide = material(f"{name}_hide", "4a5430", 0.75)
		dark = material(f"{name}_dark", "2c341c", 0.8)
		scute = material(f"{name}_scute", "3a4224", 0.75)
		belly = material(f"{name}_belly", "cdc596", 0.85)
		eye = material(f"{name}_eye", "d8c040", 0.2, emit=0.8)
	mouth = material(f"{name}_mouth", "b86a5a", 0.6)
	tooth = material(f"{name}_tooth", "d8d0b0" if ancient else "eee8d0", 0.4)
	claw = material(f"{name}_claw", "241c14", 0.6)
	pupil = material(f"{name}_pupil", "0c0a06", 0.2)
	if ancient:
		scar = material(f"{name}_scar", "b8b494", 0.9)
		moss = material(f"{name}_moss", "4a6a26", 0.95)
		moss_b = material(f"{name}_moss_b", "6e8034", 0.95)
		drowned = drowned_materials()
	b = Builder(name)
	b.bone("root", (0, 0, 0.3))
	b.bone("body", (0, 0.0, 0.3), "root")
	b.bone("head", (0, -0.66, 0.32), "body")
	b.bone("jaw", (0, -0.74, 0.25), "head")
	b.bone("tail1", (0, 0.5, 0.28), "body")
	b.bone("tail2", (0, 0.88, 0.24), "tail1")
	b.bone("tail3", (0, 1.24, 0.19), "tail2")

	# the long, flat body
	b.blob((0.7, 1.3, 0.34), (0, -0.02, 0.3), hide, "body", segs=(14, 9))
	b.blob((0.62, 1.2, 0.14), (0, -0.02, 0.19), belly, "body", segs=(12, 6))
	b.blob((0.5, 0.4, 0.28), (0, -0.62, 0.3), hide, "body", segs=(10, 7))                      # the neck
	for k in range(7):   # bands of back armor with twin rows of scutes
		y = -0.5 + k * 0.16
		w = 0.56 - 0.06 * abs(k - 3) / 3
		b.blob((w, 0.13, 0.12), (0, y, 0.43), scute, "body", segs=(10, 4))
		for x in (-0.16, -0.06, 0.06, 0.16):
			h = 0.08 if abs(x) > 0.1 else 0.06
			b.seg((x, y, 0.44), (x, y + 0.02, 0.44 + h), 0.045, 0.0, dark, "body", sides=4)
	for s in (1, -1):   # flank scales
		for k in range(5):
			b.blob((0.08, 0.16, 0.06), (0.33 * s, -0.4 + k * 0.2, 0.34), scute, "body", rot=(0, 30 * s, 0), segs=(6, 4))
	# the head: a flat skull tapering into a long snout, eyes and nostrils riding on top
	b.blob((0.44, 0.34, 0.2), (0, -0.8, 0.34), hide, "head", segs=(12, 7))
	b.blob((0.3, 0.64, 0.12), (0, -1.12, 0.32), hide, "head", segs=(12, 6))
	b.blob((0.22, 0.16, 0.12), (0, -1.42, 0.33), hide, "head", segs=(10, 6))                    # the knobbed snout tip
	b.blob((0.26, 0.9, 0.05), (0, -1.06, 0.27), mouth, "head", segs=(10, 4))                   # roof of the mouth
	for s in (1, -1):
		b.blob((0.13, 0.14, 0.1), (0.11 * s, -0.78, 0.44), hide, "head", segs=(8, 5))               # eye bumps
		b.blob((0.09, 0.08, 0.07), (0.12 * s, -0.8, 0.47), eye, "head", segs=(8, 5))
		b.blob((0.015, 0.06, 0.06), (0.12 * s, -0.84, 0.47), pupil, "head", segs=(4, 3))
		b.blob((0.04, 0.04, 0.03), (0.05 * s, -1.44, 0.39), dark, "head", segs=(5, 3))              # nostrils
		for k in range(8):   # upper teeth down both sides, jutting out and down
			y = -0.8 - k * 0.08
			x = (0.16 - 0.08 * k / 7) * s
			if ancient and k in (2, 5):
				continue   # knocked out
			ln = 0.07 if k in (1, 4, 7) else 0.05
			if ancient and k in (3, 6):
				ln *= 0.45   # broken off
			b.seg((x, y, 0.29), (x * 1.08, y, 0.29 - ln), 0.02, 0.0 if not (ancient and k in (3, 6)) else 0.012, tooth, "head", sides=4)
	b.blob((0.34, 0.14, 0.12), (0, -0.72, 0.25), hide, "jaw", segs=(8, 5))
	b.blob((0.28, 0.72, 0.08), (0, -1.08, 0.22), belly, "jaw", segs=(10, 5))                     # lower jaw
	b.blob((0.26, 0.66, 0.06), (0, -1.08, 0.25), mouth, "jaw", segs=(10, 4))
	for s in (1, -1):
		b.seg((0.13 * s, -0.76, 0.24), (0.1 * s, -1.4, 0.23), 0.05, 0.04, hide, "jaw", sides=6)
		for k in range(7):
			y = -0.84 - k * 0.08
			x = (0.13 - 0.06 * k / 6) * s
			if ancient and k == 3:
				continue
			ln = 0.06 if k % 2 else 0.045
			b.seg((x, y, 0.25), (x * 1.06, y, 0.25 + ln), 0.018, 0.0, tooth, "jaw", sides=4)
	# the tail: tall and flattened, a double crest merging into one toward the tip
	tail = [(0, 0.46, 0.29), (0, 0.9, 0.25), (0, 1.26, 0.2), (0, 1.66, 0.14)]
	radii = [0.22, 0.16, 0.1, 0.02]
	for k, bone in enumerate(CROC_TAIL):
		p, q = Vector(tail[k]), Vector(tail[k + 1])
		b.seg(tuple(p), tuple(q), radii[k], radii[k + 1], hide, bone, sides=8)
		b.seg(tuple(p - Vector((0, 0, 0.06))), tuple(q - Vector((0, 0, 0.04))), radii[k] * 0.8, radii[k + 1] * 0.8, belly, bone, sides=6)
		for j in range(3):
			u = (j + 0.5) / 3
			c = p + (q - p) * u
			r = radii[k] + (radii[k + 1] - radii[k]) * u
			xs = (-0.07, 0.07) if k < 2 else (0.0,)
			for x in xs:
				b.seg((x, c.y, c.z + r * 0.8), (x, c.y + 0.03, c.z + r * 0.8 + 0.08 - 0.015 * k), 0.04, 0.0, dark, bone, sides=4)
	# four short sprawling legs
	for name_, (x, y) in CROC_LEGS.items():
		s = 1 if x > 0 else -1
		f = -1 if y < 0 else 1
		b.bone(name_, (x, y, 0.28), "root")
		elbow = (x + 0.3 * s, y + 0.04 * f, 0.26)
		foot = (x + 0.36 * s, y - 0.04, 0.04)
		b.blob((0.3, 0.3, 0.22), (x + 0.06 * s, y, 0.27), hide, name_, segs=(8, 6))
		b.seg((x, y, 0.28), elbow, 0.09, 0.08, hide, name_, sides=7)
		b.seg(elbow, foot, 0.08, 0.06, hide, name_, sides=7)
		b.blob((0.2, 0.22, 0.06), (foot[0], foot[1] - 0.04, 0.03), dark, name_, segs=(8, 5))
		for k in (-1, 0, 1):
			b.seg((foot[0] + 0.06 * k, foot[1] - 0.12, 0.03), (foot[0] + 0.08 * k, foot[1] - 0.2, 0.01), 0.022, 0.0, claw, name_, sides=4)
	if ancient:
		# old scars raked across the hide, moss on the back, barnacle lumps
		for p, q in (((0.26, -0.3, 0.38), (0.12, -0.02, 0.46)), ((-0.3, 0.1, 0.36), (-0.1, 0.34, 0.45)),
					 ((0.2, -0.86, 0.4), (0.06, -1.1, 0.38)), ((0.3, 0.3, 0.34), (0.22, 0.5, 0.4))):
			b.seg(p, q, 0.02, 0.02, scar, "head" if p[1] < -0.7 else "body", sides=4)
		for x, y, w in ((0.08, -0.36, 0.3), (-0.12, 0.0, 0.34), (0.1, 0.3, 0.26), (-0.04, 0.48, 0.2)):
			b.blob((w, w * 1.3, 0.08), (x, y, 0.47), moss if w > 0.25 else moss_b, "body", segs=(8, 4))
		for x, y in ((0.2, -0.2), (-0.22, 0.2), (0.18, 0.44), (-0.14, -0.5)):
			_kelp(b, (x, y, 0.44), 0.18, moss, lean=(x * 0.8, 0.0), width=0.03, parts=2)
		for k in range(12):
			bone = "body"
			y = rng.uniform(-0.55, 0.55)
			sx = rng.choice((1, -1))
			loc = (sx * rng.uniform(0.18, 0.3), y, rng.uniform(0.36, 0.42))
			if k >= 9:
				bone, loc = "head", (sx * rng.uniform(0.06, 0.16), rng.uniform(-1.3, -0.9), 0.36)
			nrm = (loc[0], 0.0, 1.0)
			n = Vector(nrm).normalized()
			base = Vector(loc)
			sz = rng.uniform(0.7, 1.1)
			b.seg(tuple(base), tuple(base + n * 0.07 * sz), 0.055 * sz, 0.035 * sz, drowned["barnacle"], bone, sides=6)
			b.blob((0.04 * sz, 0.04 * sz, 0.04 * sz), tuple(base + n * 0.07 * sz), drowned["hole"], bone, segs=(5, 3))
	arm = b.build()

	def leg(name_, swing, lift=0.0):
		s = 1 if CROC_LEGS[name_][0] > 0 else -1
		return {name_: {"rot": (0, lift * s, -swing * s)}}

	def gait(t, amp, lift):
		out = {}
		for name_ in CROC_LEGS:
			ph = 0.0 if name_ in ("leg_fl", "leg_br") else 0.5
			out.update(leg(name_, amp * wave(t, 1, ph), lift * max(0.0, wave(t, 1, ph + 0.25))))
		return out

	def tail(t, amp, cycles=1.0, pitch=0.0):
		return {"tail1": {"rot": (pitch, 0, amp * wave(t, cycles))}, "tail2": {"rot": (pitch * 0.5, 0, amp * wave(t, cycles, -0.12))},
				"tail3": {"rot": (0, 0, amp * 1.3 * wave(t, cycles, -0.24))}}

	def idle(t):   # lies still; the tail sways, the jaws hang a little open now and then
		gape = seq(t, [(0, 0), (0.4, 0), (0.5, 1), (0.8, 1), (0.9, 0)])
		return merge({"body": {"loc": (0, 0, 0.008 * wave(t))}, "head": {"rot": (1 * wave(t), 0, 3 * wave(t, 0.5))},
					  "jaw": {"rot": (-10 * gape, 0, 0)}}, tail(t, 7, 0.5), gait(t, 0.5, 0))

	def walk(t):   # the sprawling waddle: the spine bends side to side
		return merge(gait(t, 24, 14), tail(t, 14),
					 {"body": {"rot": (0, 2 * wave(t, 2), 7 * wave(t, 1, 0.25))}, "root": {"loc": (0, 0, 0.01 * abs(wave(t, 2)))},
					  "head": {"rot": (0, 0, -8 * wave(t, 1, 0.25))}})

	def run(t):   # the high walk, belly off the ground
		return merge(gait(t, 34, 22), tail(t, 20),
					 {"body": {"rot": (0, 3 * wave(t, 2), 10 * wave(t, 1, 0.25))}, "root": {"loc": (0, 0, 0.05 + 0.02 * abs(wave(t, 2)))},
					  "head": {"rot": (-3, 0, -10 * wave(t, 1, 0.25))}})

	def attack(t):   # swings the head aside with the jaws wide, then whips it back across in a snap
		swing = seq(t, [(0, 0), (0.3, 30), (0.42, -12), (0.55, -18), (1, 0)])
		jaw = seq(t, [(0, 0), (0.28, -36), (0.38, -40), (0.44, 2), (0.7, 0)])
		lift = seq(t, [(0, 0), (0.28, 22), (0.38, 24), (0.44, 2), (1, 0)])
		lunge = seq(t, [(0, 0), (0.3, -0.06), (0.44, 0.3), (0.6, 0.24), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0.02 * max(0.0, lunge))},
					  "body": {"rot": (0, swing * 0.1, swing * 0.35)}, "head": {"rot": (lift, -swing * 0.2, swing * 0.8)},
					  "jaw": {"rot": (jaw, 0, 0)}},
					 tail(t, 0, 1), {"tail1": {"rot": (0, 0, -swing * 0.5)}, "tail2": {"rot": (0, 0, -swing * 0.4)}},
					 leg("leg_fl", -seq(t, [(0, 0), (0.44, 18), (1, 0)])), leg("leg_fr", seq(t, [(0, 0), (0.44, 18), (1, 0)])))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.02 * k), "rot": (4 * k, 5 * k, 0)},
					  "head": {"rot": (10 * k, 0, 12 * k)}, "jaw": {"rot": (-28 * k, 0, 0)}}, tail(t, 18 * k, 2), gait(t, 6 * k, 8 * k))

	def death(t):   # thrashes, then death-rolls over onto its back, pale belly up
		roll = seq(t, [(0.2, 0), (0.55, 95), (0.72, 176), (0.82, 180)])
		lift = seq(t, [(0.2, 0), (0.45, 0.26), (0.74, 0.02), (0.82, 0.04)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		out = merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)},
					 "head": {"rot": (-12 * curl, 0, 14 * curl)}, "jaw": {"rot": (-30 * curl, 0, 0)}},
					tail(t, 22 * seq(t, [(0, 1), (0.4, 0)]), 3, pitch=-8 * curl))
		for i, name_ in enumerate(CROC_LEGS):
			out = merge(out, leg(name_, 8 * wave(t, 5, i * 0.2) * seq(t, [(0.7, 0), (0.8, 1), (1, 0.3)]), -35 * curl))
		return out

	clip(arm, "idle", 3.2, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.85, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.5, death, False)
	return arm


def build_ancient_croc():
	return build_croc("ancient_croc", ancient=True)


# ---------------------------------------------------------------- pet class trappings (Magician, Necromancer)
# Small bolt-ons for the repainted Mage bodies below, in KayKit mesh space. They
# sit where worn chest gear leaves them showing (the collar, the shoulder), since
# players take off the Mage hat and wear whatever they've equipped.

def build_magician_amulet():
	"""A gold pendant on a short chain at the collar, set with a burning elemental stone."""
	gold = material("magician_gold", "e8b440", 0.35)
	gold_d = material("magician_gold_dark", "9a6a1a", 0.4)
	stone = material("magician_stone", "ff6a1c", 0.2, emit=2.2)
	core = material("magician_stone_core", "ffd060", 0.1, emit=3.5)
	b = Builder("magician_amulet")
	c = Vector((0, -0.335, 1.0))
	for s in (1, -1):   # the chain, up to the collar either side
		b.seg((0.05 * s, -0.33, 1.08), (0.16 * s, -0.3, 1.17), 0.012, 0.012, gold_d, "x", sides=4)
		b.seg((0.05 * s, -0.33, 1.08), tuple(c + Vector((0.02 * s, 0, 0.06))), 0.012, 0.012, gold_d, "x", sides=4)
	b.blob((0.18, 0.05, 0.2), tuple(c), gold, "x", segs=(10, 6))                                  # the setting
	b.seg(tuple(c + Vector((0, -0.02, 0))), tuple(c + Vector((0, -0.05, 0))), 0.065, 0.05, stone, "x", sides=6)   # the stone
	b.seg(tuple(c + Vector((0, -0.05, 0))), tuple(c + Vector((0, -0.07, 0))), 0.05, 0.0, core, "x", sides=6)
	for k in range(4):   # prongs
		a = math.pi / 4 + k * math.pi / 2
		p = c + Vector((0.075 * math.cos(a), -0.03, 0.085 * math.sin(a)))
		b.seg(tuple(p), tuple(p + Vector((-0.02 * math.cos(a), -0.03, -0.02 * math.sin(a)))), 0.014, 0.006, gold, "x", sides=4)
	b.seg(tuple(c + Vector((0, 0, -0.1))), tuple(c + Vector((0, -0.01, -0.16))), 0.025, 0.0, gold, "x", sides=5)   # a drop below
	return b.build_static()


def shaman_materials():
	return {
		"fur": material("shaman_fur", "7a6a58", 0.95),
		"fur_d": material("shaman_fur_dark", "4a3e32", 0.95),
		"fur_l": material("shaman_fur_light", "c8baa2", 0.9),
		"cord": material("shaman_cord", "5a3a22", 0.8),
		"bone": material("shaman_bone", "ece2c6", 0.6),
		"teal": material("shaman_teal", "2aa88a", 0.4, emit=0.6),
		"red": material("shaman_red", "b83a2a", 0.7),
		"feather": material("shaman_feather", "e8e0d0", 0.8),
		"tip": material("shaman_tip", "2a2a30", 0.8),
	}


def build_shaman_mantle():
	"""A wolf pelt over the shoulders (pinned to the chest): a shaggy ring of fur
	with the wolf's head resting on the right shoulder and its ears up."""
	m = shaman_materials()
	b = Builder("shaman_mantle")
	for k in range(18):   # a soft collar of fur lying on the shoulders, sloping down to them at the sides
		a = k * math.tau / 18
		x, y = 0.34 * math.sin(a), 0.25 * math.cos(a)
		side = abs(math.sin(a))
		b.blob((0.13 + 0.05 * side, 0.12, 0.08), (x, y, 1.02 - 0.07 * side), (m["fur"], m["fur_l"], m["fur_d"])[k % 3], "x", segs=(7, 5))
	h = Vector((-0.34, -0.02, 1.02))   # the wolf's head riding the right shoulder, looking forward
	b.blob((0.16, 0.19, 0.14), tuple(h), m["fur"], "x", segs=(8, 6))
	b.blob((0.12, 0.12, 0.1), tuple(h + Vector((0, 0.1, -0.02))), m["fur_d"], "x", segs=(7, 5))   # its neck, into the collar
	b.seg(tuple(h + Vector((0, -0.13, -0.02))), tuple(h + Vector((0, -0.28, -0.05))), 0.07, 0.035, m["fur_l"], "x", sides=6)   # muzzle
	b.blob((0.035, 0.03, 0.028), tuple(h + Vector((0, -0.29, -0.03))), m["tip"], "x", segs=(5, 3))
	for s in (1, -1):
		b.seg(tuple(h + Vector((0.06 * s, 0.03, 0.09))), tuple(h + Vector((0.08 * s, 0.05, 0.21))), 0.04, 0.0, m["fur_d"], "x", sides=4)   # ears
		b.blob((0.024, 0.016, 0.018), tuple(h + Vector((0.055 * s, -0.13, 0.04))), m["teal"], "x", segs=(4, 3))   # eyes glint
	return b.build_static()


def build_shaman_totem():
	"""A totem necklace at the collar: a carved bone charm with a teal spirit-stone,
	two feathers and a red bead either side."""
	m = shaman_materials()
	b = Builder("shaman_totem")
	c = Vector((0, -0.335, 1.0))
	for s in (1, -1):   # the cord up to the collar
		b.seg((0.05 * s, -0.33, 1.08), (0.16 * s, -0.3, 1.17), 0.012, 0.012, m["cord"], "x", sides=4)
		b.seg((0.05 * s, -0.33, 1.08), tuple(c + Vector((0.02 * s, 0, 0.06))), 0.012, 0.012, m["cord"], "x", sides=4)
		b.blob((0.022, 0.022, 0.022), (0.1 * s, -0.33, 1.12), m["red"], "x", segs=(5, 4))
	b.seg(tuple(c + Vector((0, 0, 0.05))), tuple(c + Vector((0, -0.01, -0.12))), 0.05, 0.035, m["bone"], "x", sides=6)   # the charm
	b.blob((0.035, 0.02, 0.035), tuple(c + Vector((0, -0.045, -0.02))), m["teal"], "x", segs=(6, 4))
	for s in (1, -1):   # feathers hanging from it
		top = c + Vector((0.035 * s, -0.01, -0.04))
		b.seg(tuple(top), tuple(top + Vector((0.04 * s, -0.01, -0.16))), 0.02, 0.012, m["feather"], "x", sides=4)
		b.seg(tuple(top + Vector((0.04 * s, -0.01, -0.16))), tuple(top + Vector((0.05 * s, -0.01, -0.2))), 0.012, 0.0, m["tip"], "x", sides=4)
	return b.build_static()


def necro_materials():
	return {
		"bone": material("necro_bone", "ece2c6", 0.6),
		"bone_b": material("necro_bone_b", "c8baa0", 0.7),
		"socket": material("necro_socket", "1a1418", 0.9),
		"iron": material("necro_iron", "3a3440", 0.5),
		"glow": material("necro_glow", "9aff6a", 0.2, emit=3.0),
	}


def build_necromancer_clasp():
	"""A little skull clasping the robe at the collar, green witch-light in its eyes, chained to either shoulder."""
	m = necro_materials()
	b = Builder("necromancer_clasp")
	sk = Vector((0, -0.34, 1.03))
	for s in (1, -1):
		b.seg(tuple(sk + Vector((0.05 * s, 0.01, 0.02))), (0.2 * s, -0.28, 1.16), 0.014, 0.014, m["iron"], "x", sides=4)
		b.blob((0.04, 0.03, 0.04), (0.2 * s, -0.28, 1.16), m["iron"], "x", segs=(5, 3))
	b.blob((0.15, 0.11, 0.14), tuple(sk), m["bone"], "x", segs=(10, 7))                        # cranium
	b.blob((0.1, 0.07, 0.06), tuple(sk + Vector((0, -0.02, -0.07))), m["bone_b"], "x", segs=(8, 5))   # jaw
	for s in (1, -1):
		b.blob((0.045, 0.03, 0.04), tuple(sk + Vector((0.035 * s, -0.045, 0.0))), m["socket"], "x", segs=(6, 4))
		b.blob((0.018, 0.012, 0.018), tuple(sk + Vector((0.035 * s, -0.058, 0.0))), m["glow"], "x", segs=(5, 3))
	b.blob((0.02, 0.02, 0.02), tuple(sk + Vector((0, -0.058, -0.035))), m["socket"], "x", segs=(4, 3))  # nose
	for k in range(4):   # teeth
		b.blob((0.016, 0.01, 0.02), tuple(sk + Vector((-0.027 + 0.018 * k, -0.058, -0.065))), m["bone"], "x", segs=(4, 3))
	return b.build_static()


def build_necromancer_pauldron():
	"""A pauldron of bone on the left shoulder (pinned to the chest, so it stays put as the arm swings):
	a curved plate ribbed with smaller bones and two short spikes."""
	m = necro_materials()
	b = Builder("necromancer_pauldron")
	c = Vector((0.44, 0.0, 1.13))
	b.blob((0.36, 0.42, 0.16), tuple(c), m["bone_b"], "x", rot=(0, 38, 0), segs=(10, 6))
	b.blob((0.3, 0.36, 0.12), tuple(c + Vector((0.01, 0, 0.04))), m["bone"], "x", rot=(0, 38, 0), segs=(10, 6))
	for k in range(3):   # ribs across the plate
		y = -0.12 + 0.12 * k
		b.seg((0.34, y, 1.22), (0.56, y, 1.05), 0.022, 0.022, m["bone_b"], "x", sides=5)
	for y in (-0.08, 0.1):   # two spikes jutting up and out
		base = Vector((0.47, y, 1.17))
		b.seg(tuple(base), tuple(base + Vector((0.14, 0.0, 0.14))), 0.04, 0.0, m["bone"], "x", sides=5)
	b.blob((0.05, 0.05, 0.05), (0.52, -0.14, 1.06), m["iron"], "x", segs=(6, 4))   # a rivet
	return b.build_static()


# ---------------------------------------------------------------- shared shapes for the High Terrace and Cinderpass

def _oblob(b, size, center, fwd, up, mat, bone, segs=(8, 5)):
	"""An ellipsoid `size` (side, along, across) laid along `fwd` with its third axis toward `up`:
	a feather, a flat scale or a plate that isn't axis-aligned."""
	y = Vector(fwd).normalized()
	z = Vector(up)
	z = (z - y * z.dot(y)).normalized()
	x = y.cross(z)
	bm = bmesh.new()
	bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=0.5)
	rot = Matrix((x, y, z)).transposed().to_4x4()
	m = Matrix.Translation(Vector(center)) @ rot @ Matrix.Diagonal(Vector(size)).to_4x4()
	bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
	b._add(bm, mat, bone)


def _wing_fold(b, s, shoulder, mats, bone, length=1.0, drop=0.25, width=1.0, count=6):
	"""A bird's wing folded along the side/back (s = side): a rounded covert plate at the shoulder and
	flight feathers laid back and slightly down, each a flat blob. mats = (covert, covert_b, feather, tip)."""
	sx, sy, sz = shoulder
	out = Vector((s, 0, 0.35)).normalized()
	_oblob(b, (0.1 * width, 0.62 * length, 0.42 * width), (sx, sy + 0.2 * length, sz - 0.04), (0, 1, -0.25), out, mats[0], bone, segs=(10, 6))
	_oblob(b, (0.1 * width, 0.36 * length, 0.26 * width), (sx + 0.02 * s, sy + 0.06 * length, sz + 0.06), (0, 1, -0.1), out, mats[1], bone)
	for k in range(count):
		u = k / max(1, count - 1)
		ln = (0.62 + 0.5 * u) * length
		a = Vector((sx + 0.01 * s * k, sy + (0.18 + 0.22 * u) * length, sz - (0.08 + drop * 0.35 * u) * width))
		d = Vector((0.02 * s, 1.0, -(0.1 + drop * u))).normalized()
		_oblob(b, (0.06 * width, ln, 0.17 * width), tuple(a + d * ln * 0.5), d, out, mats[2] if k % 2 else mats[0], bone, segs=(8, 4))
		_oblob(b, (0.05 * width, ln * 0.34, 0.15 * width), tuple(a + d * ln * 0.86 + out * 0.02), d, out, mats[3], bone, segs=(6, 4))


# ---------------------------------------------------------------- griffon (High Terrace)
# An eagle's head, breast and taloned forelegs on a lion's hindquarters, wings folded
# along the back. The matriarch is the same beast larger, darker, with a gold crest.

def build_griffon(name="griffon", matriarch=False):
	if matriarch:
		coat = material(f"{name}_coat", "8a5e32", 0.9)
		coat_d = material(f"{name}_coat_dark", "5a3a1e", 0.9)
		belly = material(f"{name}_belly", "c8a878", 0.9)
		white = material(f"{name}_white", "e8dcc4", 0.9)
		white_d = material(f"{name}_white_dark", "b8a888", 0.9)
		wing = material(f"{name}_wing", "4a3220", 0.9)
		wing_b = material(f"{name}_wing_b", "6e4a2a", 0.9)
		tip = material(f"{name}_tip", "2a1c12", 0.9)
		crest = material(f"{name}_crest", "e8b83a", 0.45)
		eye = material(f"{name}_eye", "ffb020", 0.2, emit=2.4)
	else:
		coat = material(f"{name}_coat", "c8964e", 0.9)
		coat_d = material(f"{name}_coat_dark", "9a6a34", 0.9)
		belly = material(f"{name}_belly", "ead2a0", 0.9)
		white = material(f"{name}_white", "f2e8d2", 0.9)
		white_d = material(f"{name}_white_dark", "d2c2a0", 0.9)
		wing = material(f"{name}_wing", "7a5230", 0.9)
		wing_b = material(f"{name}_wing_b", "a8783e", 0.9)
		tip = material(f"{name}_tip", "3e2a1a", 0.9)
		crest = material(f"{name}_crest", "8a5a2a", 0.9)
		eye = material(f"{name}_eye", "f4a818", 0.3, emit=1.0)
	beak = material(f"{name}_beak", "e8b43a", 0.45)
	beak_d = material(f"{name}_beak_dark", "3a2e24", 0.4)
	scale = material(f"{name}_scale", "d8a43a", 0.6)
	talon = material(f"{name}_talon", "241c16", 0.4)
	pupil = material(f"{name}_pupil", "100c08", 0.2)
	b = Builder(name)
	b.bone("root", (0, 0, 0.95))
	b.bone("body", (0, 0.0, 1.0), "root")
	b.bone("neck", (0, -0.62, 1.34), "body")
	b.bone("head", (0, -0.86, 1.72), "neck")
	b.bone("beak", (0, -1.16, 1.66), "head")
	b.bone("tail1", (0, 0.86, 1.12), "body")
	b.bone("tail2", (0, 1.34, 0.8), "tail1")
	b.bone("wing_l", (0.34, -0.38, 1.46), "body")
	b.bone("wing_r", (-0.34, -0.38, 1.46), "body")

	# the lion half: a long tawny barrel, heavy haunches, a pale belly
	b.blob((0.78, 1.6, 0.74), (0, 0.12, 1.02), coat, "body", segs=(14, 9))
	b.blob((0.84, 0.74, 0.82), (0, 0.5, 1.02), coat, "body", segs=(12, 8))                  # haunches
	b.blob((0.62, 1.2, 0.3), (0, 0.1, 0.74), belly, "body", segs=(12, 6))
	b.blob((0.5, 1.0, 0.24), (0, 0.24, 1.36), coat_d, "body", segs=(10, 6))                  # darker spine
	# the eagle half: a deep white breast of layered feathers, spilling down into a ruff
	b.blob((0.86, 0.82, 0.92), (0, -0.5, 1.12), white, "body", segs=(12, 9))
	for k in range(4):   # rows of rounded breast feathers overlapping downward
		z = 1.3 - k * 0.15
		for j in range(-2, 3):
			x = j * 0.13 * (1 - 0.1 * k)
			y = -0.88 + 0.06 * abs(j) + 0.03 * k
			_oblob(b, (0.16, 0.24, 0.07), (x, y, z), (0, -0.25, -1), (x, -1, 0.2), white_d if (j + k) % 2 else white, "body", segs=(6, 4))
	# the neck: feathered, rising from the breast
	b.seg((0, -0.6, 1.26), (0, -0.84, 1.66), 0.3, 0.22, white, "neck", sides=10)
	for k in range(7):   # a ruff where feathers meet fur
		a = math.pi * (0.15 + 0.7 * k / 6)
		p = (0.36 * math.cos(a), -0.3 + 0.06 * math.sin(a), 1.2 + 0.22 * math.sin(a))
		_oblob(b, (0.2, 0.34, 0.08), p, (math.cos(a) * 0.3, 0.9, -0.3), (math.cos(a), 0, math.sin(a)), white_d, "body", segs=(6, 4))
	# the head: a white eagle's head, a hooked golden beak, fierce brows and ear tufts
	b.blob((0.46, 0.56, 0.48), (0, -0.92, 1.76), white, "head", segs=(12, 8))
	b.blob((0.36, 0.44, 0.16), (0, -0.86, 1.96), crest if matriarch else white_d, "head", segs=(8, 5))   # crown
	b.seg((0, -1.12, 1.76), (0, -1.18, 1.75), 0.12, 0.105, beak, "head", sides=8)            # cere
	b.seg((0, -1.18, 1.76), (0, -1.38, 1.72), 0.1, 0.06, beak, "head", sides=7)              # upper beak
	b.seg((0, -1.38, 1.72), (0, -1.43, 1.58), 0.06, 0.01, beak_d, "head", sides=6)           # the hook
	b.seg((0, -1.16, 1.66), (0, -1.33, 1.65), 0.055, 0.022, beak, "beak", sides=5)           # lower mandible
	for s in (1, -1):
		b.blob((0.12, 0.08, 0.12), (0.17 * s, -1.06, 1.82), eye, "head", segs=(8, 5))
		b.blob((0.05, 0.03, 0.06), (0.19 * s, -1.1, 1.82), pupil, "head", segs=(5, 3))
		_oblob(b, (0.2, 0.1, 0.06), (0.16 * s, -1.07, 1.9), (s, -0.3, 0), (0, 0, 1), coat_d if not matriarch else tip, "head", segs=(6, 3))
		for j in range(3):   # swept-back ear tufts
			_oblob(b, (0.06, 0.34 - 0.06 * j, 0.1), (0.15 * s + 0.03 * j * s, -0.68 + 0.04 * j, 1.96 - 0.05 * j),
				   (0.25 * s, 1, 0.55 - 0.15 * j), (s, 0, 0.3), crest if (matriarch or j == 0) else white_d, "head", segs=(6, 4))
	if matriarch:   # a crest of long gold plumes down the back of the head
		for j in range(5):
			x = (j - 2) * 0.06
			_oblob(b, (0.06, 0.5 - 0.05 * abs(j - 2), 0.11), (x, -0.66 - 0.04 * abs(j - 2), 2.0), (x * 0.8, 1, 0.5), (0, -0.4, 1),
				   crest, "head", segs=(6, 4))
		_ring(b, (0, -0.63, 1.46), (0.22, 0.2), (0, -30), 0.035, crest, sides=14)
		_on_bone(b, len(b.parts) - 14, "neck")
	# the wings, folded along the back
	for s in (1, -1):
		w = f"wing_{'l' if s > 0 else 'r'}"
		_wing_fold(b, s, (0.38 * s, -0.4, 1.44), (wing, wing_b, coat_d if not matriarch else wing_b, tip), w, length=1.02, drop=0.3, width=1.1, count=6)
	# the lion's tail, a dark tuft at the end
	b.seg((0, 0.84, 1.14), (0, 1.12, 1.02), 0.08, 0.07, coat, "tail1", sides=7)
	b.seg((0, 1.12, 1.02), (0, 1.34, 0.8), 0.07, 0.06, coat, "tail1", sides=7)
	b.seg((0, 1.34, 0.8), (0, 1.5, 0.58), 0.06, 0.05, coat, "tail2", sides=7)
	b.blob((0.18, 0.2, 0.3), (0, 1.54, 0.46), tip, "tail2", segs=(8, 6))
	# forelegs of an eagle: feathered thighs, scaly yellow shanks, black talons
	legs = {"leg_fl": (0.24, -0.56), "leg_fr": (-0.24, -0.56), "leg_bl": (0.26, 0.56), "leg_br": (-0.26, 0.56)}
	for name_, (x, y) in legs.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, 0.92), "root")
		if y < 0:
			b.blob((0.3, 0.36, 0.5), (x * 1.04, y + 0.02, 0.84), white, name_, segs=(8, 6))
			b.blob((0.22, 0.26, 0.2), (x, y, 0.56), white_d, name_, segs=(7, 5))                  # feathered "trousers"
			b.seg((x, y, 0.52), (x, y - 0.02, 0.1), 0.07, 0.06, scale, name_, sides=6)
			for dx, dy in ((0.0, -0.2), (0.09, -0.15), (-0.09, -0.15), (0.0, 0.12)):
				root = Vector((x, y - 0.03, 0.07))
				end = root + Vector((dx * s, dy, -0.03))
				b.seg(tuple(root), tuple(end), 0.045, 0.034, scale, name_, sides=5)
				d = (end - root).normalized()
				b.seg(tuple(end), tuple(end + d * 0.08 + Vector((0, 0, -0.04))), 0.034, 0.004, talon, name_, sides=4)
		else:
			b.blob((0.34, 0.52, 0.62), (x * 1.06, y + 0.04, 0.86), coat, name_, segs=(10, 7))      # the lion's thigh
			b.seg((x, y + 0.12, 0.6), (x, y + 0.14, 0.26), 0.1, 0.075, coat, name_, sides=7)
			b.seg((x, y + 0.14, 0.26), (x, y + 0.04, 0.08), 0.075, 0.07, coat, name_, sides=7)
			b.blob((0.2, 0.26, 0.12), (x, y - 0.02, 0.06), coat_d, name_, segs=(8, 5))          # the paw
			for k in (-1, 0, 1):
				b.blob((0.07, 0.08, 0.07), (x + 0.06 * k, y - 0.13, 0.05), coat, name_, segs=(5, 4))
	if matriarch:
		_scaled(b, 1.18)
	arm = b.build()

	def wings(k=0.0, flap=0.0):
		"""k=0 folded, 1 spread wide and raised; flap lifts and drops them on top of that."""
		return {"wing_l": {"rot": (-38 * k - flap, 4 * flap, -86 * k)}, "wing_r": {"rot": (-38 * k - flap, -4 * flap, 86 * k)}}

	def tail(t, amp, cycles=1.0):
		return {"tail1": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))}, "tail2": {"rot": (0, 0, amp * 1.3 * wave(t, cycles, -0.15))}}

	def idle(t):   # sharp looks round, a lazy tail, now and then it rouses its wings
		look = seq(t, [(0, 0), (0.15, 0), (0.2, 28), (0.4, 28), (0.45, -22), (0.6, -22), (0.65, 0)])
		cock = seq(t, [(0.4, 0), (0.45, 12), (0.6, 12), (0.65, 0)])
		rouse = seq(t, [(0.7, 0), (0.76, 0.28), (0.8, 0.12), (0.84, 0.3), (0.9, 0)])
		return merge({"body": {"loc": (0, 0, 0.012 * wave(t, 2))}, "head": {"rot": (3 * wave(t, 1, 0.3), cock, look)},
					  "neck": {"rot": (2 * wave(t), 0, 0)}}, wings(rouse, 3 * wave(t, 2)), tail(t, 10))

	def walk(t):
		return merge(_quad_legs(wave(t), 24), tail(t, 12), wings(0.03, 2 * wave(t, 2)),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "neck": {"rot": (3 * wave(t, 2), 0, 0)},
					  "head": {"loc": (0, 0.03 * wave(t, 2), 0)}})

	def run(t):   # a bounding gallop with half-opened wings beating for balance
		f, k = 40 * wave(t), 40 * wave(t, 1, 0.5)
		flap = 0.5 + 0.5 * wave(t, 1, 0.1)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.1 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)},
					  "neck": {"rot": (-8, 0, 0)}}, wings(0.25 + 0.25 * flap, 16 * flap), tail(t, 6))

	def attack(t):   # rears on its haunches with wings flung wide, rakes with the talons, stabs with the beak
		spread = seq(t, [(0, 0), (0.25, 1), (0.6, 0.9), (1, 0)])
		rear = seq(t, [(0, 0), (0.28, 26), (0.48, -6), (0.62, -4), (1, 0)])
		rake = seq(t, [(0, 0), (0.28, 60), (0.48, -24), (0.62, -12), (1, 0)])
		neck = seq(t, [(0, 0), (0.28, 16), (0.48, -26), (0.62, -20), (1, 0)])
		beak = seq(t, [(0, 0), (0.24, -30), (0.46, -6), (0.6, 0)])
		lunge = seq(t, [(0, 0), (0.28, -0.08), (0.48, 0.34), (0.62, 0.28), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0.24 * max(0.0, rear) / 26), "rot": (rear, 0, 0)},
					  "leg_fl": {"rot": (rake, 0, 0)}, "leg_fr": {"rot": (rake * 0.85, 0, 0)},
					  "leg_bl": {"rot": (-rear, 0, 0)}, "leg_br": {"rot": (-rear, 0, 0)},
					  "neck": {"rot": (neck, 0, 0)}, "head": {"rot": (neck * 0.4, 0, 0)}, "beak": {"rot": (beak, 0, 0)}},
					 wings(spread, 20 * seq(t, [(0.2, 0), (0.35, 1), (0.5, -0.5), (0.7, 0)])), tail(t, 18, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, 0.04 * k), "rot": (8 * k, 5 * k, 0)},
					  "neck": {"rot": (16 * k, 0, 0)}, "head": {"rot": (8 * k, 0, -18 * k)}, "beak": {"rot": (-24 * k, 0, 0)}},
					 wings(0.4 * k), tail(t, 20 * k, 2))

	def death(t):   # wings flare, then it keels over onto its side
		roll = seq(t, [(0.2, 0), (0.64, 86), (0.74, 80), (0.86, 88)])
		drop = seq(t, [(0.2, 0), (0.64, -0.46)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		flare = seq(t, [(0, 0), (0.2, 0.7), (0.55, 0.3), (0.85, 0.1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 12), (0.5, 0)]), roll, 0)},
					  "neck": {"rot": (-20 * curl, 0, 14 * curl)}, "head": {"rot": (-14 * curl, 0, 16 * curl)},
					  "beak": {"rot": (-16 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (30 * curl, 0, 0)}, "leg_fr": {"rot": (16 * curl, 0, 0)},
					  "leg_bl": {"rot": (-24 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					 wings(flare), {"tail1": {"rot": (-10 * curl, 0, 0)}})

	clip(arm, "idle", 3.2, idle, True)
	clip(arm, "walk", 0.9, walk, True)
	clip(arm, "run", 0.5, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_forest_hawk():
	return build_sunhawk("forest_hawk", FOREST_HAWK_COLORS)


def build_griffon_matriarch():
	return build_griffon("griffon_matriarch", matriarch=True)


# ---------------------------------------------------------------- magma golem (Cinderpass)
# The earth elemental's frame in black basalt: plates of cooled rock over a molten body
# that shows through every gap, lava seams, white-hot eyes. Heavy, slow, stamping.

def build_magma_golem(name="magma_golem", colossus=False):
	import random
	rng = random.Random(113 if colossus else 111)
	rock = material(f"{name}_basalt", "302a27", 0.95)
	rock_l = material(f"{name}_basalt_light", "4a423c", 0.9)
	rock_d = material(f"{name}_basalt_dark", "1c1816", 0.95)
	ash = material(f"{name}_ash", "6a625c", 0.95)
	magma = material(f"{name}_magma", "b82a0a", 0.5, emit=1.6)
	lava = material(f"{name}_lava", "ff6a14", 0.4, emit=3.2)
	hot = material(f"{name}_hot", "ffc050", 0.3, emit=4.5)
	eye = material(f"{name}_eye", "fff0b0", 0.1, emit=6.0)
	obsidian = material(f"{name}_obsidian", "15121a", 0.15)
	b = Builder(name)
	b.bone("root", (0, 0, 0.05))
	b.bone("hips", (0, 0, 0.9), "root")
	b.bone("chest", (0, 0, 1.35), "hips")
	b.bone("head", (0, -0.24, 2.02), "chest")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"leg_{side}", (0.36 * s, 0, 0.88), "hips")
		b.bone(f"shoulder_{side}", (0.68 * s, 0, 2.02), "chest")
		b.bone(f"arm_{side}", (0.8 * s, 0, 1.88), "chest")
		b.bone(f"hand_{side}", (0.98 * s, -0.04, 1.36), f"arm_{side}")

	# legs: a molten core in each, cased in basalt, broad feet
	for s in (1, -1):
		leg = f"leg_{'l' if s > 0 else 'r'}"
		b.seg((0.36 * s, 0.0, 0.9), (0.38 * s, -0.02, 0.2), 0.15, 0.15, magma, leg, sides=8)
		_rock(b, (0.56, 0.54, 0.46), (0.37 * s, 0.02, 0.66), rock, leg, rng)
		_rock(b, (0.46, 0.44, 0.3), (0.4 * s, -0.02, 0.38), rock_l, leg, rng)
		_rock(b, (0.62, 0.8, 0.3), (0.4 * s, -0.12, 0.15), rock_d, leg, rng, rot=(0, 0, 8 * s))
		_rock(b, (0.26, 0.24, 0.18), (0.46 * s, -0.46, 0.12), rock, leg, rng)
		_zigzag(b, [(0.6 * s, -0.1, 0.72), (0.63 * s, -0.08, 0.6), (0.6 * s, -0.12, 0.5)], 0.028, lava, leg)
	# the pelvis
	b.blob((0.8, 0.56, 0.36), (0, 0.02, 0.98), magma, "hips", segs=(12, 7))
	_rock(b, (1.04, 0.72, 0.46), (0, 0.04, 0.92), rock_d, "hips", rng)
	for k in range(5):
		a = 2 * math.pi * k / 5 + 0.3
		_rock(b, (0.3, 0.28, 0.24), (0.5 * math.cos(a), 0.34 * math.sin(a), 1.12), rock if k % 2 else rock_l, "hips", rng)
	# the torso: a molten body, cased in great plates with gaps that glow
	b.blob((1.0, 0.7, 0.86), (0, 0.06, 1.6), magma, "chest", segs=(14, 10))
	b.blob((0.2, 0.12, 0.22), (0, -0.3, 1.52), hot, "chest", segs=(10, 7))                      # the white-hot heart, glimpsed between plates
	for size, loc, mat in (((0.66, 0.44, 0.62), (0.3, -0.24, 1.72), rock), ((0.64, 0.44, 0.6), (-0.3, -0.24, 1.74), rock_l),
						   ((0.7, 0.4, 0.46), (0.24, -0.26, 1.28), rock_d), ((0.66, 0.42, 0.46), (-0.28, -0.24, 1.3), rock),
						   ((1.1, 0.56, 0.7), (0, 0.34, 1.64), rock_d), ((0.64, 0.5, 0.56), (0.46, 0.16, 1.4), rock),
						   ((0.62, 0.5, 0.56), (-0.46, 0.14, 1.42), rock_l), ((0.9, 0.5, 0.36), (0, 0.24, 2.04), rock)):
		_rock(b, size, loc, mat, "chest", rng, jitter=0.12)
	for pts in (((0.02, -0.46, 1.96), (-0.03, -0.47, 1.84), (0.02, -0.46, 1.74)),
				((0.5, -0.26, 1.64), (0.56, -0.2, 1.5), (0.6, -0.14, 1.36)),
				((-0.14, -0.48, 1.14), (-0.08, -0.46, 1.04), (-0.14, -0.42, 0.98))):
		_zigzag(b, list(pts), 0.03, lava, "chest")
	for k in range(7):   # ash and cinders caught on the plates
		a = rng.uniform(0.3, 2.8)
		loc = (0.56 * math.cos(a) * (1 if k % 2 else -1), 0.12 + 0.3 * math.sin(a), rng.uniform(1.5, 2.05))
		b.blob((0.2, 0.18, 0.06), loc, ash, "chest", rot=(rng.uniform(-20, 20), rng.uniform(-30, 30), 0), segs=(6, 4))
	# shoulders: slabs of basalt, lava welling up between them
	for s in (1, -1):
		sh = f"shoulder_{'l' if s > 0 else 'r'}"
		b.blob((0.46, 0.42, 0.22), (0.66 * s, 0.04, 2.0), lava, sh, segs=(10, 6))
		_rock(b, (0.84, 0.76, 0.34), (0.7 * s, 0.04, 2.08), rock, sh, rng, rot=(0, 16 * s, 0), jitter=0.1)
		_rock(b, (0.5, 0.5, 0.26), (0.76 * s, 0.12, 2.24), rock_l, sh, rng, rot=(0, 22 * s, 0))
		_crystal(b, (0.72 * s, 0.14, 2.3), (0.3 * s, 0.2, 1), 0.34 if colossus else 0.22, 0.07, obsidian, sh)   # obsidian spikes
		_crystal(b, (0.56 * s, 0.26, 2.22), (0.2 * s, 0.4, 1), 0.26 if colossus else 0.16, 0.06, obsidian, sh)
	# the head: a blunt block sunk between the shoulders, burning eyes and a molten mouth
	b.blob((0.4, 0.4, 0.34), (0, -0.26, 2.0), magma, "head", segs=(10, 7))
	_rock(b, (0.54, 0.5, 0.44), (0, -0.24, 2.06), rock, "head", rng, jitter=0.1)
	_rock(b, (0.6, 0.24, 0.16), (0, -0.46, 2.16), rock_d, "head", rng, jitter=0.08)             # the brow ledge
	_rock(b, (0.4, 0.24, 0.16), (0, -0.44, 1.86), rock_d, "head", rng)                          # the jaw
	for s in (1, -1):
		b.blob((0.13, 0.05, 0.07), (0.12 * s, -0.52, 2.06), eye, "head", rot=(0, 0, -12 * s), segs=(8, 5))
	b.blob((0.24, 0.05, 0.05), (0, -0.54, 1.95), hot, "head", segs=(8, 4))                         # a molten grin
	if colossus:   # obsidian horns and a crown of flames
		for s in (1, -1):
			pts = [(0.2 * s, -0.3, 2.24), (0.36 * s, -0.24, 2.4), (0.44 * s, -0.12, 2.62), (0.4 * s, 0.0, 2.8)]
			for k, (p, q) in enumerate(zip(pts, pts[1:])):
				b.seg(p, q, 0.09 - 0.028 * k, 0.062 - 0.028 * k if k < 2 else 0.0, obsidian, "head", sides=7)
		for k in range(5):
			x = (k - 2) * 0.1
			_flame(b, (x, -0.18, 2.24), (x * 0.4, 0.1, 1), 0.34 - 0.06 * abs(k - 2), 0.07, lava if k % 2 else hot, "head", bend=(0, 0.1, 0))
	# arms: stacked basalt round molten cores, fists like anvils
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		b.seg((0.82 * s, 0.0, 1.9), (0.96 * s, -0.04, 1.36), 0.14, 0.12, magma, arm, sides=8)
		_rock(b, (0.5, 0.48, 0.52), (0.86 * s, 0.0, 1.66), rock, arm, rng)
		_rock(b, (0.32, 0.3, 0.3), (0.8 * s, 0.02, 1.88), rock_d, arm, rng)
		b.seg((0.96 * s, -0.04, 1.36), (1.0 * s, -0.08, 0.84), 0.13, 0.15, magma, hand, sides=8)
		_rock(b, (0.4, 0.4, 0.34), (0.96 * s, -0.04, 1.38), rock_d, hand, rng)
		_rock(b, (0.56, 0.52, 0.5), (1.0 * s, -0.06, 1.1), rock, hand, rng)
		_rock(b, (0.76, 0.7, 0.58), (1.02 * s, -0.1, 0.76), rock_l, hand, rng, jitter=0.1)       # the fist
		for k in range(3):
			b.blob((0.16, 0.12, 0.12), ((0.88 + 0.14 * k) * s, -0.44, 0.74), lava, hand, segs=(6, 4))   # glowing knuckles
			_rock(b, (0.18, 0.16, 0.16), ((0.88 + 0.14 * k) * s, -0.42, 0.84), rock_d, hand, rng)
		b.seg((1.06 * s, -0.2, 0.5), (1.08 * s, -0.22, 0.38), 0.05, 0.0, lava, hand, sides=6)          # a drip
		_zigzag(b, [(1.26 * s, -0.12, 1.2), (1.28 * s, -0.08, 1.04), (1.26 * s, -0.14, 0.92)], 0.026, lava, hand)
	if colossus:
		_scaled(b, 1.28)
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, 0, 0)}, "hand_r": {"rot": (bend, 0, 0)}}

	def idle(t):   # a slow heave of breath; the head turns a little
		return merge_scaled({"chest": {"rot": (2 * wave(t), 0, 0)}, "head": {"rot": (-2 * wave(t), 0, 6 * wave(t, 1, 0.3))},
							 "shoulder_l": {"rot": (0, 1.5 * wave(t), 0)}, "shoulder_r": {"rot": (0, -1.5 * wave(t), 0)},
							 "hips": {"loc": (0, 0, -0.02 * (1 + wave(t)))}},
							arms(3 * wave(t, 1, 0.1), 3 * wave(t, 1, 0.6), 5, 8))

	def stride(t, swing, lean, bob):
		drop = -bob * (0.5 + 0.5 * wave(t, 2, 0.25))
		return merge_scaled({"leg_l": {"rot": (swing * wave(t), 0, 0)}, "leg_r": {"rot": (-swing * wave(t), 0, 0)},
							 "hips": {"rot": (0, 6 * wave(t), 0), "loc": (0, 0, drop)},
							 "chest": {"rot": (lean, -4 * wave(t), -7 * wave(t))}, "head": {"rot": (-lean * 0.5, 0, 4 * wave(t))}},
							arms(-swing * 0.7 * wave(t), swing * 0.7 * wave(t), 6, 12))

	def walk(t):
		return stride(t, 18, -5, 0.09)

	def run(t):
		return stride(t, 28, -12, 0.12)

	def attack(t):   # both fists heave up and slam down, the whole body behind them
		up = seq(t, [(0, 0), (0.45, 150), (0.55, 156), (0.66, 30), (0.82, 26), (1, 0)])
		lean = seq(t, [(0, 0), (0.45, 10), (0.55, 12), (0.66, -28), (0.82, -24), (1, 0)])
		sink = seq(t, [(0, 0), (0.45, 0.04), (0.66, -0.16), (0.86, -0.12), (1, 0)])
		surge = seq(t, [(0, 0), (0.55, -0.05), (0.66, 0.22), (0.86, 0.18), (1, 0)])
		bend = seq(t, [(0, 0), (0.45, 20), (0.62, -10), (1, 0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "hips": {"loc": (0, 0, sink), "rot": (lean * 0.3, 0, 0)},
							 "chest": {"rot": (lean * 0.7, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
							 "leg_l": {"rot": (-lean * 0.3 + 6, 0, 0)}, "leg_r": {"rot": (-lean * 0.3 - 6, 0, 0)}},
							arms(up, up, 8, bend))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"chest": {"rot": (8 * k, 5 * k, 6 * k)}, "head": {"rot": (8 * k, 0, 8 * k)},
							 "hips": {"loc": (0, -0.06 * k, 0)}}, arms(-12 * k, -8 * k, 8 * k, -8 * k))

	def death(t):   # it cracks apart and slumps into a heap, the fire dimming as it sinks
		reel = seq(t, [(0, 0), (0.15, 10), (0.3, -8), (0.4, 0)])
		f = seq(t, [(0.3, 0), (0.72, 1)])
		g = seq(t, [(0.42, 0), (0.88, 1)])
		pose = {"hips": {"loc": (0, 0, -0.78 * f), "rot": (0, 6 * f, 0)},
				"chest": {"rot": (reel - 16 * f, 4 * f, 0), "loc": (0, 0.06 * f, -0.46 * f),
						  "scale": (1 + 0.14 * f, 1 + 0.14 * f, 1 - 0.3 * f)},
				"head": {"rot": (-44 * g, 20 * g, 30 * g), "loc": (0.1 * g, 0.4 * g, -0.86 * g)}}
		for s, side in ((1, "l"), (-1, "r")):
			pose[f"leg_{side}"] = {"rot": (-8 * f, 60 * s * f, 0), "scale": (1, 1, 1 - 0.3 * f)}
			pose[f"shoulder_{side}"] = {"rot": (15 * g, -50 * s * g, 0), "loc": (-0.35 * s * g, -0.1 * g, -0.55 * g)}
			pose[f"arm_{side}"] = {"rot": (10 * g + reel, -75 * s * g, 0), "loc": (0, 0, -0.25 * g)}
			pose[f"hand_{side}"] = {"rot": (0, -20 * s * g, 0)}
		return merge_scaled(pose)

	clip_scaled(arm, "idle", 3.4, idle, True)
	clip_scaled(arm, "walk", 1.9, walk, True)
	clip_scaled(arm, "run", 1.2, run, True)
	clip_scaled(arm, "attack", 1.6, attack, False)
	clip_scaled(arm, "hit", 0.55, hit, False)
	clip_scaled(arm, "death", 2.2, death, False)
	return arm


def build_magma_colossus():
	return build_magma_golem("magma_colossus", colossus=True)


# ---------------------------------------------------------------- ash drake (Cinderpass)
# A young fire drake on four legs: charcoal scales, an ember-lit belly and throat, swept
# horns, small bat wings folded at the shoulders, a tail ending in a smoldering tip.
# The cinder drake is a grown one: bigger, heavier horned, with wings it spreads to strike.

DRAKE_TAIL = ("tail1", "tail2", "tail3")


def build_ash_drake(name="ash_drake", big=False):
	scale_m = material(f"{name}_scale", "3a3432" if not big else "2a2220", 0.7)
	scale_l = material(f"{name}_scale_light", "5a524c" if not big else "4a3a32", 0.7)
	scale_d = material(f"{name}_scale_dark", "1e1a1a", 0.7)
	belly = material(f"{name}_belly", "d8601c" if not big else "e8702a", 0.5, emit=0.9 if not big else 1.4)
	belly_d = material(f"{name}_belly_dark", "8e3414", 0.6, emit=0.4)
	horn = material(f"{name}_horn", "c8b8a0" if not big else "2a2420", 0.5 if not big else 0.2)
	horn_d = material(f"{name}_horn_dark", "6a5a4a" if not big else "8a2a14", 0.5)
	membrane = material(f"{name}_membrane", "5a2a1e" if not big else "7a2414", 0.8, emit=0.1 if not big else 0.3)
	claw = material(f"{name}_claw", "1a1616", 0.4)
	eye = material(f"{name}_eye", "ffd040", 0.2, emit=4.0)
	ember = material(f"{name}_ember", "ff8a24", 0.3, emit=3.0)
	tooth = material(f"{name}_tooth", "eee4c8", 0.4)
	b = Builder(name)
	b.bone("root", (0, 0, 0.6))
	b.bone("body", (0, 0.0, 0.66), "root")
	b.bone("neck", (0, -0.52, 0.76), "body")
	b.bone("head", (0, -0.86, 1.1), "neck")
	b.bone("jaw", (0, -1.0, 1.02), "head")
	b.bone("tail1", (0, 0.58, 0.68), "body")
	b.bone("tail2", (0, 1.08, 0.54), "tail1")
	b.bone("tail3", (0, 1.56, 0.4), "tail2")
	b.bone("wing_l", (0.24, -0.3, 0.9), "body")
	b.bone("wing_r", (-0.24, -0.3, 0.9), "body")

	b.blob((0.66, 1.34, 0.54), (0, 0.02, 0.68), scale_m, "body", segs=(14, 9))
	b.blob((0.52, 1.1, 0.24), (0, 0.0, 0.47), belly, "body", segs=(12, 6))
	for k in range(6):   # belly plates
		b.blob((0.44 - 0.04 * abs(k - 2.5), 0.14, 0.08), (0, -0.4 + k * 0.16, 0.39), belly_d, "body", segs=(8, 4))
	b.blob((0.7, 0.6, 0.6), (0, -0.4, 0.74), scale_m, "body", segs=(10, 8))                      # shoulders
	b.blob((0.62, 0.56, 0.56), (0, 0.42, 0.7), scale_m, "body", segs=(10, 8))                    # haunches
	for k in range(7):   # back plates and a row of spines
		y = -0.5 + k * 0.17
		b.blob((0.36, 0.2, 0.1), (0, y, 0.95 - 0.02 * abs(k - 3)), scale_l, "body", segs=(8, 4))
		b.seg((0, y, 0.98), (0, y + 0.08, 1.14 - 0.02 * abs(k - 3)), 0.05, 0.0, horn_d, "body", sides=4)
	for s in (1, -1):   # flank scutes
		for k in range(4):
			b.blob((0.08, 0.2, 0.12), (0.3 * s, -0.3 + k * 0.22, 0.72), scale_d, "body", rot=(0, 26 * s, 0), segs=(6, 4))
	# the neck, rising, lit from within down the throat
	b.seg((0, -0.46, 0.74), (0, -0.84, 1.04), 0.22, 0.16, scale_m, "neck", sides=9)
	b.seg((0, -0.54, 0.62), (0, -0.88, 0.94), 0.12, 0.09, belly, "neck", sides=7)
	for k in range(3):
		b.seg((0, -0.58 - 0.1 * k, 0.9 + 0.1 * k), (0, -0.54 - 0.1 * k, 1.04 + 0.1 * k), 0.04, 0.0, horn_d, "neck", sides=4)
	# the head: a long wedge, a heavy brow, horns swept back, a jaw of teeth
	b.blob((0.36, 0.46, 0.3), (0, -0.96, 1.12), scale_m, "head", segs=(10, 7))
	b.seg((0, -1.06, 1.12), (0, -1.36, 1.06), 0.14, 0.085, scale_m, "head", sides=8)
	b.blob((0.4, 0.2, 0.12), (0, -1.06, 1.24), scale_d, "head", rot=(-8, 0, 0), segs=(8, 4))      # brow
	b.seg((0, -1.0, 1.0), (0, -1.32, 0.98), 0.1, 0.06, scale_l, "jaw", sides=7)                   # lower jaw
	b.seg((0, -1.02, 1.03), (0, -1.3, 1.02), 0.08, 0.05, belly, "jaw", sides=6)                   # the fire in its mouth
	for s in (1, -1):
		b.blob((0.09, 0.07, 0.06), (0.13 * s, -1.1, 1.19), eye, "head", rot=(0, 0, 12 * s), segs=(6, 4))
		b.blob((0.04, 0.03, 0.03), (0.05 * s, -1.37, 1.09), ember, "head", segs=(4, 3))              # smoking nostrils
		for k in range(4):
			y = -1.14 - k * 0.06
			b.seg((0.08 * s, y, 1.03), (0.085 * s, y, 0.98), 0.018, 0.0, tooth, "head", sides=4)
		pts = [(0.1 * s, -0.96, 1.26), (0.16 * s, -0.84, 1.34), (0.2 * s, -0.66, 1.4), (0.2 * s, -0.5, 1.38)]
		if big:
			pts = [(0.1 * s, -0.96, 1.26), (0.2 * s, -0.84, 1.38), (0.26 * s, -0.64, 1.5), (0.26 * s, -0.44, 1.52), (0.22 * s, -0.3, 1.46)]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			r0, r1 = 0.06 * (1 - k / len(pts)), 0.06 * (1 - (k + 1) / len(pts))
			b.seg(p, q, r0, r1, horn if k < 2 else horn_d, "head", sides=6)
		b.seg((0.16 * s, -0.94, 1.08), (0.3 * s, -0.84, 1.12), 0.04, 0.0, horn_d, "head", sides=4)   # cheek spikes
		b.seg((0.14 * s, -0.86, 1.06), (0.28 * s, -0.72, 1.06), 0.035, 0.0, horn_d, "head", sides=4)
		if big:
			b.seg((0.06 * s, -1.22, 1.14), (0.08 * s, -1.2, 1.24), 0.03, 0.0, horn, "head", sides=4)   # snout horns
		_bat_wing(b, s, (0.24 * s, -0.3, 0.9), (scale_d, membrane, claw), f"wing_{'l' if s > 0 else 'r'}",
				  scale=0.9 if big else 0.62)
	# the tail: tapering, spined, a smoldering tip
	pts = [(0, 0.56, 0.7), (0, 1.08, 0.54), (0, 1.56, 0.4), (0, 1.96, 0.3)]
	radii = [0.2, 0.14, 0.08, 0.03]
	for k, bone in enumerate(DRAKE_TAIL):
		b.seg(pts[k], pts[k + 1], radii[k], radii[k + 1], scale_m, bone, sides=8)
		b.seg((0, pts[k][1], pts[k][2] - radii[k] * 0.5), (0, pts[k + 1][1], pts[k + 1][2] - radii[k + 1] * 0.5),
			  radii[k] * 0.6, radii[k + 1] * 0.6, belly_d, bone, sides=6)
		mid = ((pts[k][1] + pts[k + 1][1]) / 2, (pts[k][2] + pts[k + 1][2]) / 2)
		b.seg((0, mid[0], mid[1] + radii[k] * 0.8), (0, mid[0] + 0.06, mid[1] + radii[k] * 0.8 + 0.1), 0.04, 0.0, horn_d, bone, sides=4)
	_flame(b, (0, 1.94, 0.3), (0, 1, 0.6), 0.3, 0.07, ember, "tail3", bend=(0, 0, 0.2))
	# four legs under it, clawed
	legs = {"leg_fl": (0.26, -0.42), "leg_fr": (-0.26, -0.42), "leg_bl": (0.27, 0.44), "leg_br": (-0.27, 0.44)}
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.62), "root")
		back = y > 0
		b.blob((0.26, 0.38 if back else 0.3, 0.44), (x * 1.08, y + (0.04 if back else 0.0), 0.6), scale_m, name_, segs=(8, 6))
		b.seg((x, y + (0.08 if back else 0.02), 0.44), (x, y + (0.1 if back else 0.04), 0.2), 0.085, 0.07, scale_m, name_, sides=7)
		b.seg((x, y + (0.1 if back else 0.04), 0.2), (x, y - 0.02, 0.06), 0.07, 0.065, scale_d, name_, sides=7)
		b.blob((0.18, 0.22, 0.1), (x, y - 0.04, 0.05), scale_d, name_, segs=(8, 5))
		for k in (-1, 0, 1):
			root = Vector((x + 0.06 * k, y - 0.14, 0.05))
			b.seg(tuple(root), tuple(root + Vector((0.01 * k, -0.08, -0.04))), 0.025, 0.0, claw, name_, sides=4)
	if big:
		_scaled(b, 1.36)
	arm = b.build()

	def wings(k=0.0, flap=0.0):
		return {"wing_l": {"rot": (-10 * k - flap, -70 * k, -40 * k)}, "wing_r": {"rot": (-10 * k - flap, 70 * k, 40 * k)}}

	def tail(t, amp, cycles=1.0):
		return {"tail1": {"rot": (3 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (0, 0, amp * wave(t, cycles, -0.15))}, "tail3": {"rot": (0, 0, amp * 1.3 * wave(t, cycles, -0.3))}}

	def idle(t):   # sways its head like a snake, jaw working, smoke from its nostrils
		return merge({"body": {"loc": (0, 0, 0.012 * wave(t, 2))}, "neck": {"rot": (4 * wave(t, 1, 0.2), 0, 8 * wave(t))},
					  "head": {"rot": (-3 * wave(t, 1, 0.2), 0, -6 * wave(t))},
					  "jaw": {"rot": (-8 * max(0.0, wave(t, 2, 0.1)), 0, 0)}}, wings(0.05 * max(0.0, wave(t, 1, 0.6))), tail(t, 10))

	def walk(t):
		return merge(_quad_legs(wave(t), 24), tail(t, 14), wings(0.03),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 5 * wave(t, 1, 0.25))},
					  "neck": {"rot": (0, 0, -6 * wave(t, 1, 0.25))}})

	def run(t):
		f, k = 40 * wave(t), 40 * wave(t, 1, 0.5)
		flap = 0.5 + 0.5 * wave(t, 1, 0.1)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.08 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)},
					  "neck": {"rot": (-10, 0, 0)}}, wings(0.2 + (0.25 if big else 0.1) * flap, 10 * flap), tail(t, 8))

	def attack(t):   # rears its neck back, wings up, then lunges to bite
		rear = seq(t, [(0, 0), (0.3, 1), (0.46, -0.6), (0.62, -0.4), (1, 0)])
		jaw = seq(t, [(0, 0), (0.3, -36), (0.44, -40), (0.52, 2), (0.7, 0)])
		lunge = seq(t, [(0, 0), (0.3, -0.1), (0.46, 0.36), (0.62, 0.3), (1, 0)])
		spread = seq(t, [(0, 0), (0.25, 1), (0.6, 0.8), (1, 0)]) * (1.0 if big else 0.5)
		return merge({"root": {"loc": (0, lunge, 0.04 * max(0.0, rear)), "rot": (6 * rear, 0, 0)},
					  "neck": {"rot": (30 * rear, 0, 0)}, "head": {"rot": (-12 * rear, 0, 0)}, "jaw": {"rot": (jaw, 0, 0)},
					  "leg_fl": {"rot": (20 * max(0.0, rear), 0, 0)}}, wings(spread, 12 * spread), tail(t, 16, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.03 * k), "rot": (6 * k, 5 * k, 0)},
					  "neck": {"rot": (16 * k, 0, 12 * k)}, "head": {"rot": (8 * k, 0, 10 * k)}, "jaw": {"rot": (-24 * k, 0, 0)}},
					 wings(0.3 * k), tail(t, 20 * k, 2))

	def death(t):   # the neck whips back, it rolls onto its side, the fire in it dying
		roll = seq(t, [(0.2, 0), (0.62, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.2, 0), (0.62, -0.34)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
					  "neck": {"rot": (seq(t, [(0, 0), (0.2, 30), (0.7, -16)]), 0, 20 * curl)}, "head": {"rot": (-10 * curl, 0, 12 * curl)},
					  "jaw": {"rot": (-24 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (30 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
					  "leg_bl": {"rot": (-24 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					 wings(0.4 * curl), {"tail1": {"rot": (-6 * curl, 0, 20 * curl)}, "tail2": {"rot": (0, 0, 20 * curl)}})

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 0.95, walk, True)
	clip(arm, "run", 0.5, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_cinder_drake():
	return build_ash_drake("cinder_drake", big=True)


# ---------------------------------------------------------------- lava salamander (Cinderpass)
# Long and low like the croc, but slick black with glowing orange bands, a broad flat head
# and frills of flame behind it.

SALAMANDER_LEGS = {"leg_fl": (0.24, -0.36), "leg_fr": (-0.24, -0.36), "leg_bl": (0.26, 0.34), "leg_br": (-0.26, 0.34)}
SALAMANDER_TAIL = ("tail1", "tail2", "tail3")


def build_salamander():
	skin = material("salamander_skin", "241e1c", 0.35)
	skin_l = material("salamander_skin_light", "3e3430", 0.4)
	band = material("salamander_band", "ff6a18", 0.4, emit=2.6)
	band_d = material("salamander_band_dark", "c83a10", 0.5, emit=1.4)
	belly = material("salamander_belly", "8a3a1a", 0.6, emit=0.4)
	eye = material("salamander_eye", "ffe060", 0.1, emit=4.0)
	pupil = material("salamander_pupil", "0c0806", 0.2)
	mouth = material("salamander_mouth", "ff9a3a", 0.3, emit=2.0)
	b = Builder("lava_salamander")
	b.bone("root", (0, 0, 0.26))
	b.bone("body", (0, 0.0, 0.28), "root")
	b.bone("head", (0, -0.6, 0.3), "body")
	b.bone("jaw", (0, -0.7, 0.24), "head")
	b.bone("tail1", (0, 0.48, 0.28), "body")
	b.bone("tail2", (0, 0.94, 0.24), "tail1")
	b.bone("tail3", (0, 1.38, 0.2), "tail2")

	b.blob((0.58, 1.2, 0.3), (0, 0.0, 0.3), skin, "body", segs=(14, 8))
	b.blob((0.5, 1.1, 0.12), (0, 0.0, 0.18), belly, "body", segs=(12, 5))
	b.blob((0.34, 1.0, 0.1), (0, 0.0, 0.42), skin_l, "body", segs=(10, 4))
	for k in range(6):   # glowing bands across the back, with a bright stripe down the spine
		y = -0.46 + k * 0.18
		_oblob(b, (0.52 - 0.04 * abs(k - 2.5), 0.08, 0.28), (0, y, 0.34), (1, 0, 0), (0, 0, 1), band if k % 2 else band_d, "body", segs=(10, 5))
	for k in range(5):
		b.blob((0.1, 0.14, 0.06), (0, -0.38 + k * 0.2, 0.44), band, "body", segs=(6, 3))
	# the head: broad and flat, a wide glowing mouth, bulging eyes on top
	b.blob((0.36, 0.26, 0.2), (0, -0.56, 0.3), skin, "body", segs=(10, 6))                         # neck
	b.blob((0.5, 0.46, 0.18), (0, -0.78, 0.31), skin, "head", segs=(12, 7))
	b.blob((0.4, 0.2, 0.14), (0, -0.98, 0.3), skin, "head", segs=(10, 6))
	b.blob((0.44, 0.34, 0.03), (0, -0.84, 0.24), mouth, "head", segs=(10, 4))
	b.blob((0.44, 0.4, 0.1), (0, -0.82, 0.21), skin_l, "jaw", segs=(10, 5))
	for s in (1, -1):
		b.blob((0.12, 0.12, 0.1), (0.15 * s, -0.78, 0.4), skin, "head", segs=(8, 5))
		b.blob((0.09, 0.09, 0.08), (0.16 * s, -0.8, 0.42), eye, "head", segs=(8, 5))
		b.blob((0.015, 0.05, 0.06), (0.17 * s, -0.83, 0.42), pupil, "head", segs=(4, 3))
		b.blob((0.08, 0.1, 0.04), (0.16 * s, -0.66, 0.38), band, "head", segs=(6, 3))                 # a stripe over each eye
		for k in range(3):   # frills of flame fanning back from behind the jaw
			_flame(b, (0.2 * s, -0.6 + 0.06 * k, 0.32 + 0.04 * k), (s * 0.8, 0.6, 0.3 + 0.25 * k), 0.26 - 0.04 * k, 0.05,
				   band if k % 2 else band_d, "head", bend=(0, 0.15, 0.1))
	# the tail: long, banded, ending thin
	pts = [(0, 0.44, 0.3), (0, 0.94, 0.25), (0, 1.38, 0.2), (0, 1.86, 0.14)]
	radii = [0.18, 0.12, 0.07, 0.015]
	for k, bone in enumerate(SALAMANDER_TAIL):
		p, q = Vector(pts[k]), Vector(pts[k + 1])
		b.seg(tuple(p), tuple(q), radii[k], radii[k + 1], skin, bone, sides=8)
		for j in (0.3, 0.75):
			c = p + (q - p) * j
			r = radii[k] + (radii[k + 1] - radii[k]) * j
			_oblob(b, (r * 2.12, 0.07, r * 2.12), tuple(c), (1, 0, 0), (0, 0, 1), band if j < 0.5 else band_d, bone, segs=(10, 4))
	for name_, (x, y) in SALAMANDER_LEGS.items():
		s = 1 if x > 0 else -1
		f = -1 if y < 0 else 1
		b.bone(name_, (x, y, 0.26), "root")
		elbow = (x + 0.24 * s, y + 0.03 * f, 0.24)
		foot = (x + 0.3 * s, y - 0.04, 0.04)
		b.blob((0.24, 0.24, 0.18), (x + 0.04 * s, y, 0.26), skin, name_, segs=(8, 6))
		b.seg((x, y, 0.26), elbow, 0.075, 0.065, skin, name_, sides=7)
		b.blob((0.06, 0.06, 0.05), (elbow[0], elbow[1], elbow[2] + 0.05), band, name_, segs=(5, 3))
		b.seg(elbow, foot, 0.065, 0.05, skin, name_, sides=7)
		b.blob((0.18, 0.18, 0.05), (foot[0], foot[1] - 0.03, 0.03), skin_l, name_, segs=(8, 5))
		for k in (-1, 0, 1):   # fat round toes
			b.blob((0.06, 0.07, 0.04), (foot[0] + 0.06 * k, foot[1] - 0.12, 0.025), band_d, name_, segs=(5, 3))
	arm = b.build()

	def leg(name_, swing, lift=0.0):
		s = 1 if SALAMANDER_LEGS[name_][0] > 0 else -1
		return {name_: {"rot": (0, lift * s, -swing * s)}}

	def gait(t, amp, lift):
		out = {}
		for name_ in SALAMANDER_LEGS:
			ph = 0.0 if name_ in ("leg_fl", "leg_br") else 0.5
			out.update(leg(name_, amp * wave(t, 1, ph), lift * max(0.0, wave(t, 1, ph + 0.25))))
		return out

	def tail(t, amp, cycles=1.0):
		return {"tail1": {"rot": (0, 0, amp * wave(t, cycles))}, "tail2": {"rot": (0, 0, amp * wave(t, cycles, -0.12))},
				"tail3": {"rot": (0, 0, amp * 1.4 * wave(t, cycles, -0.24))}}

	def idle(t):   # breathes, the tail curling, the throat pulsing
		return merge({"body": {"loc": (0, 0, 0.008 * wave(t, 2))}, "head": {"rot": (3 * wave(t, 1, 0.3), 0, 6 * wave(t, 0.5))},
					  "jaw": {"rot": (-4 * max(0.0, wave(t, 3)), 0, 0)}}, tail(t, 10, 0.5))

	def walk(t):   # a sinuous waddle, the whole spine waving
		return merge(gait(t, 26, 14), tail(t, 18),
					 {"body": {"rot": (0, 2 * wave(t, 2), 9 * wave(t, 1, 0.25))}, "head": {"rot": (0, 0, -10 * wave(t, 1, 0.25))},
					  "root": {"loc": (0, 0, 0.01 * abs(wave(t, 2)))}})

	def run(t):
		return merge(gait(t, 36, 22), tail(t, 24),
					 {"body": {"rot": (0, 3 * wave(t, 2), 12 * wave(t, 1, 0.25))}, "head": {"rot": (-4, 0, -12 * wave(t, 1, 0.25))},
					  "root": {"loc": (0, 0, 0.04 + 0.02 * abs(wave(t, 2)))}})

	def attack(t):   # rears its head and snaps down with a mouthful of fire
		lift = seq(t, [(0, 0), (0.3, 26), (0.46, -8), (0.6, -4), (1, 0)])
		jaw = seq(t, [(0, 0), (0.28, -40), (0.44, -42), (0.5, 0), (0.7, 0)])
		lunge = seq(t, [(0, 0), (0.3, -0.06), (0.46, 0.3), (0.62, 0.24), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0)}, "body": {"rot": (lift * 0.2, 0, 0)}, "head": {"rot": (lift, 0, 0)},
					  "jaw": {"rot": (jaw, 0, 0)}}, tail(t, 20, 2), leg("leg_fl", -seq(t, [(0, 0), (0.46, 16), (1, 0)])),
					 leg("leg_fr", seq(t, [(0, 0), (0.46, 16), (1, 0)])))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.02 * k), "rot": (4 * k, 6 * k, 0)},
					  "head": {"rot": (12 * k, 0, 14 * k)}, "jaw": {"rot": (-24 * k, 0, 0)}}, tail(t, 20 * k, 2), gait(t, 6 * k, 8 * k))

	def death(t):   # writhes, rolls over belly-up
		roll = seq(t, [(0.2, 0), (0.55, 95), (0.72, 176), (0.82, 180)])
		lift = seq(t, [(0.2, 0), (0.45, 0.2), (0.74, 0.02), (0.82, 0.03)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		out = merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)}, "head": {"rot": (-10 * curl, 0, 16 * curl)},
					 "jaw": {"rot": (-26 * curl, 0, 0)}}, tail(t, 24 * seq(t, [(0, 1), (0.4, 0)]), 3))
		for i, name_ in enumerate(SALAMANDER_LEGS):
			out = merge(out, leg(name_, 8 * wave(t, 5, i * 0.2) * seq(t, [(0.7, 0), (0.8, 1), (1, 0.3)]), -35 * curl))
		return out

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 0.9, walk, True)
	clip(arm, "run", 0.55, run, True)
	clip(arm, "attack", 0.75, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- snow leopard (High Terrace)
# The wolf's frame made feline: a long low body, a round head with a short muzzle
# and small round ears, heavy paws, and a tail nearly as long as the body.

def _spots(b, center, radii, count, mat, bone, rng, zmin=-0.2, ymax=1.0, size=0.1, rosette=True):
	"""Dark spots scattered over the upper surface of everything built so far: rays from outside an
	ellipsoid round `center` find the outermost skin; rosettes are rings of three or four dots."""
	from mathutils.bvhtree import BVHTree
	bm = bmesh.new()
	for p in b.parts:
		bm.from_mesh(p.data)
	tree = BVHTree.FromBMesh(bm)
	c, r = Vector(center), Vector(radii)
	placed = tries = 0
	while placed < count and tries < count * 20:
		tries += 1
		u = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
		if u.z < zmin or u.y > ymax:
			continue
		aim = c + Vector((u.x * r.x, u.y * r.y, u.z * r.z))
		hit, n, _, _ = tree.ray_cast(aim + u * 2.0, -u)
		if hit is None:
			continue
		if n.dot(u) < 0:
			n = -n
		t = n.orthogonal().normalized()
		if rosette and placed % 3:
			k = rng.choice((3, 4))
			for j in range(k):
				a = 2 * math.pi * j / k + rng.uniform(-0.3, 0.3)
				q = hit + (t * math.cos(a) + n.cross(t) * math.sin(a)) * size * 0.62
				_oblob(b, (size * 0.5, size * 0.72, size * 0.24), tuple(q), n.cross(t) * math.cos(a) - t * math.sin(a), n, mat, bone, segs=(6, 3))
		else:
			_oblob(b, (size * 0.8, size * 0.9, size * 0.26), tuple(hit), t, n, mat, bone, segs=(6, 3))
		placed += 1
	bm.free()


CAT_TAIL = ("tail1", "tail2", "tail3")


def build_snow_leopard(name="snow_leopard", ghost=False):
	import random
	rng = random.Random(83 if ghost else 81)
	if ghost:
		fur = material(f"{name}_fur", "e2e8f0", 0.85, emit=0.05)
		back = material(f"{name}_back", "c4d0e0", 0.85, emit=0.05)
		belly = material(f"{name}_belly", "f4f8fc", 0.85, emit=0.05)
		spot = material(f"{name}_spot", "7e9cc4", 0.8, emit=0.35)
		eye = material(f"{name}_eye", "a8e4ff", 0.2, emit=3.0)
		nose = material(f"{name}_nose", "8aa0bc", 0.5)
	else:
		fur = material(f"{name}_fur", "d6d2c6", 0.9)
		back = material(f"{name}_back", "bdb8aa", 0.9)
		belly = material(f"{name}_belly", "f2efe6", 0.9)
		spot = material(f"{name}_spot", "3e3a36", 0.85)
		eye = material(f"{name}_eye", "b8d06a", 0.25, emit=1.0)
		nose = material(f"{name}_nose", "8a6a64", 0.5)
	dark = material(f"{name}_dark", "2a2624", 0.6)
	pupil = material(f"{name}_pupil", "0e0c0a", 0.2)
	tooth = material(f"{name}_tooth", "f2ecd8", 0.4)
	b = Builder(name)
	legs = {"leg_fl": (0.2, -0.5), "leg_fr": (-0.2, -0.5), "leg_bl": (0.21, 0.5), "leg_br": (-0.21, 0.5)}
	b.bone("root", (0, 0, 0.66))
	b.bone("body", (0, 0.0, 0.7), "root")
	b.bone("head", (0, -0.78, 0.9), "body")
	b.bone("jaw", (0, -0.92, 0.82), "head")
	b.bone("tail1", (0, 0.8, 0.78), "body")
	b.bone("tail2", (0, 1.24, 0.56), "tail1")
	b.bone("tail3", (0, 1.7, 0.42), "tail2")

	b.blob((0.6, 1.6, 0.56), (0, 0.02, 0.74), fur, "body", segs=(14, 9))                    # long, low body
	b.blob((0.66, 0.62, 0.6), (0, -0.46, 0.78), fur, "body", segs=(12, 8))                  # deep chest and shoulders
	b.blob((0.62, 0.6, 0.56), (0, 0.5, 0.74), fur, "body", segs=(12, 8))                    # haunches
	b.blob((0.5, 1.3, 0.26), (0, 0.02, 0.54), belly, "body", segs=(12, 6))
	b.blob((0.42, 1.2, 0.2), (0, 0.06, 1.0), back, "body", segs=(10, 6))
	_spots(b, (0, 0.02, 0.76), (0.31, 0.8, 0.29), 28, spot, "body", rng, zmin=-0.25, size=0.11)
	# the head: round and broad, a short muzzle, small round ears set wide
	b.seg((0, -0.5, 0.86), (0, -0.74, 0.92), 0.22, 0.2, fur, "head", sides=10)               # thick neck
	b.blob((0.54, 0.5, 0.46), (0, -0.84, 0.96), fur, "head", segs=(12, 9))
	b.blob((0.34, 0.26, 0.2), (0, -1.06, 0.88), belly, "head", segs=(10, 7))                  # muzzle
	b.blob((0.4, 0.24, 0.12), (0, -0.98, 0.8), belly, "head", segs=(8, 5))                     # chin and cheeks
	b.blob((0.1, 0.06, 0.06), (0, -1.19, 0.92), nose, "head", segs=(6, 4))
	b.seg((0, -1.14, 0.84), (0, -1.18, 0.9), 0.012, 0.012, dark, "head", sides=3)
	b.blob((0.22, 0.16, 0.08), (0, -0.98, 0.78), belly, "jaw", segs=(8, 5))                    # lower jaw
	for s in (1, -1):
		b.blob((0.11, 0.07, 0.07), (0.12 * s, -1.03, 1.02), eye, "head", segs=(8, 5))
		b.blob((0.03, 0.03, 0.06), (0.125 * s, -1.06, 1.02), pupil, "head", segs=(4, 3))
		b.seg((0.16 * s, -1.06, 0.98), (0.2 * s, -1.02, 0.9), 0.012, 0.01, dark, "head", sides=3)     # tear line
		b.seg((0.2 * s, -0.8, 1.14), (0.24 * s, -0.78, 1.24), 0.08, 0.055, fur, "head", sides=8)      # round ears
		b.blob((0.12, 0.05, 0.1), (0.235 * s, -0.8, 1.24), dark, "head", segs=(8, 5))
		b.blob((0.08, 0.03, 0.06), (0.235 * s, -0.83, 1.23), belly, "head", segs=(6, 4))
		b.seg((0.05 * s, -1.12, 0.8), (0.05 * s, -1.13, 0.73), 0.02, 0.004, tooth, "jaw", sides=4)  # fangs
		for k in range(3):   # whisker pads and a few spots on the brow
			b.blob((0.03, 0.02, 0.03), ((0.05 + 0.03 * k) * s, -1.16, 0.87 - 0.02 * k), dark, "head", segs=(4, 3))
		for x, y, z in ((0.1, -0.94, 1.14), (0.18, -0.88, 1.1), (0.06, -0.86, 1.18)):
			b.blob((0.05, 0.04, 0.03), (x * s, y, z), spot, "head", segs=(5, 3))
	# the tail: long and thick all the way, ringed with dark bands, the tip curling up
	pts = [(0, 0.78, 0.8), (0, 1.24, 0.56), (0, 1.7, 0.42), (0, 2.02, 0.5), (0, 2.14, 0.7)]
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		bone = CAT_TAIL[min(k, 2)]
		b.seg(p, q, 0.12, 0.12 if k < 3 else 0.1, fur, bone, sides=9)
		b.blob((0.25, 0.25, 0.25), q, fur, bone, segs=(8, 6))
		mid = tuple((Vector(p) + Vector(q)) / 2)
		d = (Vector(q) - Vector(p)).normalized()
		_oblob(b, (0.265, 0.08, 0.265), mid, d, (0, 0, 1), spot, bone, segs=(9, 3))
	b.blob((0.24, 0.24, 0.26), (0, 2.16, 0.74), spot, "tail3", segs=(8, 6))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.62), "root")
		back_leg = y > 0
		b.blob((0.26, 0.4 if back_leg else 0.32, 0.48), (x * 1.08, y + (0.04 if back_leg else 0), 0.62), fur, name_, segs=(8, 6))
		b.seg((x, y, 0.5), (x, y + (0.05 if back_leg else 0.02), 0.2), 0.09, 0.075, fur, name_, sides=7)
		b.seg((x, y + (0.05 if back_leg else 0.02), 0.2), (x, y - 0.01, 0.07), 0.075, 0.08, fur, name_, sides=7)
		b.blob((0.2, 0.24, 0.12), (x, y - 0.04, 0.06), belly, name_, segs=(8, 5))              # big snowshoe paws
		for k in (-1, 0, 1):
			b.blob((0.06, 0.07, 0.06), (x + 0.06 * k, y - 0.15, 0.05), fur, name_, segs=(5, 4))
		b.blob((0.05, 0.05, 0.03), (x * 1.3, y + 0.02, 0.4), spot, name_, segs=(5, 3))
	if ghost:
		_scaled(b, 1.2)
	arm = b.build()

	def tail(t, amp, cycles=1.0, flick=0.0):
		return {"tail1": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (0, 0, amp * wave(t, cycles, -0.15))},
				"tail3": {"rot": (flick, 0, amp * 1.4 * wave(t, cycles, -0.3))}}

	def idle(t):   # slow breaths, a watchful look round, the tail tip flicking
		look = seq(t, [(0, 0), (0.3, 0), (0.4, 24), (0.62, 24), (0.72, 0)])
		return merge({"body": {"loc": (0, 0, 0.012 * wave(t, 2))}, "head": {"rot": (3 * wave(t, 1, 0.3), 0, look)}},
					 tail(t, 6, 1.0, 12 * wave(t, 3)))

	def walk(t):   # a low, prowling walk, shoulders rolling
		return merge(_quad_legs(wave(t), 24), tail(t, 8),
					 {"root": {"loc": (0, 0, -0.03 + 0.015 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 0)},
					  "head": {"rot": (-4, 0, -3 * wave(t))}})

	def run(t):   # a bounding sprint, the spine flexing
		f, k = 46 * wave(t), 46 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.85, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.85, 0, 0)},
					  "root": {"loc": (0, 0, 0.09 * max(0.0, wave(t, 1, 0.25))), "rot": (8 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-6 * wave(t, 1, 0.1), 0, 0)}}, tail(t, 4, 1.0, -10))

	def attack(t):   # crouches, pounces with a raking forepaw and a bite
		crouch = seq(t, [(0, 0), (0.25, 1), (0.4, 0), (1, 0)])
		lunge = seq(t, [(0, 0), (0.25, -0.1), (0.45, 0.42), (0.6, 0.34), (1, 0)])
		rear = seq(t, [(0, 0), (0.25, -6), (0.42, 14), (0.6, 4), (1, 0)])
		paw = seq(t, [(0, 0), (0.3, 20), (0.42, 70), (0.55, -10), (1, 0)])
		jaw = seq(t, [(0, 0), (0.35, -34), (0.5, 4), (0.7, 0)])
		return merge({"root": {"loc": (0, lunge, -0.1 * crouch + 0.1 * max(0.0, rear) / 14), "rot": (rear, 0, 0)},
					  "leg_fl": {"rot": (paw, 0, 0)}, "leg_fr": {"rot": (paw * 0.3, 0, 0)},
					  "leg_bl": {"rot": (-rear, 0, 0)}, "leg_br": {"rot": (-rear, 0, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.3, 12), (0.5, -10), (1, 0)]), 0, 0)}, "jaw": {"rot": (jaw, 0, 0)}},
					 tail(t, 14, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, 0.03 * k), "rot": (8 * k, 0, 0)}, "head": {"rot": (14 * k, 0, 12 * k)},
					  "jaw": {"rot": (-24 * k, 0, 0)}}, tail(t, 18 * k, 2))

	def death(t):
		roll = seq(t, [(0.15, 0), (0.6, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.15, 0), (0.6, -0.32)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (-12 * curl, 0, 14 * curl)}, "jaw": {"rot": (-12 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (30 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
					  "leg_bl": {"rot": (-26 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					 {"tail1": {"rot": (-8 * curl, 0, 20 * curl)}, "tail2": {"rot": (0, 0, 24 * curl)}, "tail3": {"rot": (0, 0, 20 * curl)}})

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 0.9, walk, True)
	clip(arm, "run", 0.44, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.2, death, False)
	return arm


def build_ghost_leopard():
	"""The named one: a leopard pale as snow-light, faint blue rosettes, ice-blue eyes."""
	return build_snow_leopard("ghost_leopard", ghost=True)


# ---------------------------------------------------------------- mountain yak (High Terrace)

def build_yak():
	fur = material("yak_fur", "4a3426", 0.95)
	fur_d = material("yak_fur_dark", "2e2018", 0.95)
	fur_l = material("yak_fur_light", "6a4c36", 0.95)
	face = material("yak_face", "3a2a20", 0.9)
	muzzle = material("yak_muzzle", "8a7a6a", 0.85)
	horn = material("yak_horn", "e2d6b8", 0.55)
	horn_d = material("yak_horn_dark", "5a5044", 0.55)
	hoof = material("yak_hoof", "1a1512", 0.5)
	nose = material("yak_nose", "221c18", 0.4)
	eye = material("yak_eye", "1a120c", 0.2)
	glint = material("yak_glint", "f0e0b0", 0.2, emit=0.8)
	b = Builder("mountain_yak")
	legs = {"leg_fl": (0.24, -0.5), "leg_fr": (-0.24, -0.5), "leg_bl": (0.24, 0.52), "leg_br": (-0.24, 0.52)}
	b.bone("root", (0, 0, 0.64))
	b.bone("body", (0, 0.0, 0.9), "root")
	b.bone("head", (0, -0.78, 0.98), "body")
	b.bone("tail", (0, 0.84, 1.04), "body")
	b.bone("skirt", (0, 0.0, 0.7), "body")

	b.blob((0.9, 1.62, 0.8), (0, 0.06, 0.98), fur, "body", segs=(14, 10))                   # the barrel
	b.blob((0.84, 0.84, 0.86), (0, -0.4, 1.14), fur, "body", segs=(12, 9))                  # the great hump over the shoulders
	for k in range(12):   # shaggy locks over the hump and back
		y = -0.62 + k * 0.12
		top = 1.56 if y < -0.1 else 1.56 - (y + 0.1) * 0.24
		x = 0.12 * (1 if k % 2 else -1)
		b.blob((0.34, 0.3, 0.2), (x, y, top - 0.08), (fur_l, fur, fur_d)[k % 3], "body", rot=(0, 24 * (1 if k % 2 else -1), k * 17), segs=(7, 4))
	# the long skirt of hair hanging from the flanks and chest nearly to the knees: overlapping strands, flaring out
	import random
	rng = random.Random(87)
	for k in range(16):
		y = -0.72 + k * 0.096
		for s in (1, -1):
			ln = rng.uniform(0.5, 0.64) - (0.08 if abs(y) > 0.6 else 0.0)
			x = (0.44 if abs(y) < 0.5 else 0.4) * s
			mat = (fur_d, fur, fur_l, fur)[(k + (s > 0)) % 4]
			_oblob(b, (0.1, 0.2, ln), (x, y, 0.92 - ln * 0.5), (0, 1, 0), (-0.22 * s, rng.uniform(-0.1, 0.1), 1), mat, "skirt", segs=(6, 4))
	for k in range(5):   # the beard of the chest
		x = (k - 2) * 0.13
		_oblob(b, (0.16, 0.14, 0.56), (x, -0.76 + 0.04 * abs(k - 2), 0.68), (0, 1, 0), (0, 0.3, 1), (fur_d, fur)[k % 2], "skirt", segs=(6, 4))
	# the head: low and broad, a pale muzzle, the forelock hanging over the eyes
	b.seg((0, -0.64, 1.02), (0, -0.84, 0.94), 0.26, 0.22, fur, "head", sides=9)
	b.blob((0.46, 0.46, 0.46), (0, -0.92, 0.92), face, "head", segs=(10, 8))
	b.blob((0.36, 0.3, 0.3), (0, -1.14, 0.8), muzzle, "head", segs=(10, 7))
	b.blob((0.22, 0.08, 0.12), (0, -1.28, 0.8), nose, "head", segs=(8, 4))
	b.blob((0.5, 0.3, 0.26), (0, -0.96, 1.16), fur_l, "head", segs=(10, 6))                  # shaggy forelock
	for k in range(5):
		x = (k - 2) * 0.08
		_oblob(b, (0.08, 0.06, 0.2), (x, -1.08, 1.06), (0, 1, 0), (0, 0, 1), fur_l if k % 2 else fur, "head", segs=(5, 3))
	for s in (1, -1):
		b.blob((0.07, 0.05, 0.06), (0.17 * s, -1.08, 0.98), eye, "head", segs=(6, 4))
		b.blob((0.025, 0.02, 0.025), (0.18 * s, -1.11, 0.99), glint, "head", segs=(4, 3))
		b.seg((0.22 * s, -0.86, 1.0), (0.38 * s, -0.84, 0.92), 0.07, 0.03, face, "head", sides=5)         # ears, drooping
		b.blob((0.2, 0.26, 0.4), (0.2 * s, -0.88, 0.76), fur, "head", segs=(7, 5))                       # hairy cheeks
		# horns: out sideways from the brow, then sweeping up and forward
		pts = [(0.18 * s, -0.86, 1.16), (0.4 * s, -0.84, 1.18), (0.56 * s, -0.86, 1.28), (0.62 * s, -0.94, 1.44), (0.58 * s, -1.04, 1.56)]
		radii = [0.085, 0.07, 0.055, 0.04, 0.02, 0.004]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(p, q, radii[k], radii[k + 1], horn if k < 3 else horn_d, "head", sides=8)
			b.blob((radii[k + 1] * 2.1,) * 3, q, horn if k < 3 else horn_d, "head", segs=(6, 4))
	b.seg((0, 0.84, 1.08), (0, 0.96, 0.8), 0.07, 0.05, fur, "tail", sides=6)                  # the tail, a long tassel
	b.blob((0.16, 0.14, 0.42), (0, 1.0, 0.56), fur_d, "tail", segs=(7, 5))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.64), "root")
		b.blob((0.3, 0.36, 0.44), (x, y, 0.62), fur, name_, segs=(8, 6))
		b.seg((x, y, 0.5), (x, y, 0.14), 0.1, 0.085, fur_d, name_, sides=7)
		b.blob((0.2, 0.2, 0.2), (x, y, 0.2), fur_d, name_, segs=(7, 5))                          # hairy fetlock
		b.seg((x, y - 0.02, 0.1), (x, y - 0.04, 0.0), 0.08, 0.095, hoof, name_, sides=7)
	arm = b.build()

	def skirt(t, amp, cycles=2.0, phase=0.0):
		return {"skirt": {"rot": (amp * wave(t, cycles, phase), amp * 0.5 * wave(t, cycles, phase + 0.25), 0)}}

	def tail(t, amp, cycles=2.0):
		return {"tail": {"rot": (0, 0, amp * wave(t, cycles))}}

	def idle(t):   # grazes, chewing, then looks up and snorts
		graze = seq(t, [(0, 0), (0.15, 0), (0.28, 1), (0.64, 1), (0.76, 0)])
		snort = seq(t, [(0.82, 0), (0.86, 1), (0.92, 0)])
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))},
					  "head": {"rot": (-30 * graze + 3 * graze * wave(t, 7) + 8 * snort, 0, 10 * snort * wave(t, 8))}},
					 tail(t, 16, 3), skirt(t, 2, 1))

	def walk(t):   # a slow, heavy plod; the skirt of hair swings
		return merge(_quad_legs(wave(t), 22), tail(t, 10), skirt(t, 5, 2, 0.1),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 0)},
					  "head": {"rot": (4 * wave(t, 2), 0, 4 * wave(t))}})

	def run(t):   # a lumbering gallop
		f, k = 34 * wave(t), 34 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.07 * max(0.0, wave(t, 1, 0.25))), "rot": (5 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-8, 0, 0)}}, tail(t, 8), skirt(t, 10, 1, 0.3))

	def attack(t):   # lowers its head and hooks upward with the horns
		lunge = seq(t, [(0, 0), (0.3, -0.12), (0.5, 0.4), (0.62, 0.32), (1, 0)])
		head = seq(t, [(0, 0), (0.3, -26), (0.48, -30), (0.58, 18), (0.72, 10), (1, 0)])
		yaw = seq(t, [(0, 0), (0.48, -6), (0.58, 16), (1, 0)])
		pitch = seq(t, [(0, 0), (0.3, -4), (0.58, 6), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0), "rot": (pitch, 0, 0)}, "head": {"rot": (head, 0, yaw)},
					  "leg_bl": {"rot": (seq(t, [(0, 0), (0.45, -24), (0.7, 0)]), 0, 0)},
					  "leg_br": {"rot": (seq(t, [(0, 0), (0.45, -20), (0.7, 0)]), 0, 0)}}, tail(t, 20, 3), skirt(t, 8, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.02 * k), "rot": (6 * k, 4 * k, 0)},
					  "head": {"rot": (14 * k, 0, -12 * k)}}, tail(t, 22 * k, 3), skirt(t, 8 * k, 2))

	def death(t):   # knees buckle, then it rolls onto its side
		roll = seq(t, [(0.25, 0), (0.66, 86), (0.76, 80), (0.88, 88)])
		drop = seq(t, [(0.1, 0), (0.3, -0.14), (0.66, -0.4)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.25, -10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.2, 14), (0.6, -8)]), 0, 14 * curl)},
					  "skirt": {"rot": (0, -20 * curl, 0)}},
					 {"leg_fl": {"rot": (seq(t, [(0, 0), (0.25, 40), (0.6, 20)]), 0, 0)},
					  "leg_fr": {"rot": (seq(t, [(0, 0), (0.25, 40), (0.6, 10)]), 0, 0)},
					  "leg_bl": {"rot": (-20 * curl, 0, 0)}, "leg_br": {"rot": (-8 * curl, 0, 0)}})

	clip(arm, "idle", 3.6, idle, True)
	clip(arm, "walk", 1.1, walk, True)
	clip(arm, "run", 0.55, run, True)
	clip(arm, "attack", 0.9, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- gargoyle (High Terrace)
# A weathered stone gargoyle off the monastery roofs: hunched on digitigrade legs, knuckles
# on the ground, bat wings folded up behind its shoulders, horns, a long barbed tail, moss in its cracks.

def _bat_wing(b, s, root, mats, bone, scale=1.0):
	"""A folded bat wing rising behind the shoulder (s = side): an arm spar up to the wrist,
	three fingers raking down and back, membrane stretched between them. mats = (bone, membrane, claw)."""
	r = Vector(root)
	k = scale
	wrist = r + Vector((0.26 * s, 0.14, 0.56)) * k
	tips = [r + Vector((0.56 * s, 0.34, 0.3)) * k, r + Vector((0.5 * s, 0.46, -0.1)) * k, r + Vector((0.32 * s, 0.44, -0.44)) * k]
	body = r + Vector((0.06 * s, 0.2, -0.5)) * k
	b.seg(tuple(r), tuple(wrist), 0.07 * k, 0.05 * k, mats[0], bone, sides=6)
	b.blob((0.11 * k,) * 3, tuple(wrist), mats[0], bone, segs=(6, 4))
	b.seg(tuple(wrist), tuple(wrist + Vector((0.02 * s, -0.08, 0.18)) * k), 0.04 * k, 0.0, mats[2], bone, sides=5)   # thumb claw
	for tip in tips:
		mid = wrist + (tip - wrist) * 0.55 + Vector((0.04 * s, 0, 0.03)) * k
		b.seg(tuple(wrist), tuple(mid), 0.035 * k, 0.03 * k, mats[0], bone, sides=5)
		b.seg(tuple(mid), tuple(tip), 0.03 * k, 0.012 * k, mats[0], bone, sides=5)
	ring = [r, wrist] + tips + [body]
	start = len(b.parts)
	for p, q in zip(ring[1:], ring[2:]):   # membrane: triangles fanned from the root, scalloped between the fingers
		mid = (p + q) / 2
		inner = mid + (r - mid) * 0.14
		_slab(b, [tuple(r), tuple(p), tuple(inner)], 0.025 * k, mats[1])
		_slab(b, [tuple(r), tuple(inner), tuple(q)], 0.025 * k, mats[1])
		_slab(b, [tuple(p), tuple(q), tuple(inner)], 0.025 * k, mats[1])
	_on_bone(b, start, bone)
	return wrist, tips


def build_gargoyle():
	import random
	rng = random.Random(97)
	stone = material("gargoyle_stone", "8e8c86", 0.95)
	stone_d = material("gargoyle_stone_dark", "605e59", 0.95)
	stone_l = material("gargoyle_stone_light", "b4b1a8", 0.95)
	wing_m = material("gargoyle_membrane", "4e4c48", 0.95)
	crack = material("gargoyle_crack", "2c2a28", 0.95)
	moss = material("gargoyle_moss", "5c7432", 0.95)
	moss_b = material("gargoyle_moss_b", "8c9844", 0.95)
	claw = material("gargoyle_claw", "3c3a36", 0.7)
	eye = material("gargoyle_eye", "ff8a2a", 0.2, emit=3.0)
	b = Builder("gargoyle")
	b.bone("root", (0, 0, 0.78))
	b.bone("hips", (0, 0.06, 0.8), "root")
	b.bone("chest", (0, -0.04, 1.04), "hips")
	b.bone("head", (0, -0.42, 1.46), "chest")
	b.bone("jaw", (0, -0.6, 1.4), "head")
	b.bone("tail1", (0, 0.36, 0.72), "hips")
	b.bone("tail2", (0, 0.8, 0.44), "tail1")
	b.bone("tail3", (0, 1.2, 0.3), "tail2")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"leg_{side}", (0.24 * s, 0.04, 0.78), "hips")
		b.bone(f"arm_{side}", (0.42 * s, -0.2, 1.34), "chest")
		b.bone(f"hand_{side}", (0.62 * s, -0.24, 0.92), f"arm_{side}")
		b.bone(f"wing_{side}", (0.22 * s, 0.2, 1.44), "chest")

	# hips and a hunched, forward-leaning torso of carved stone
	b.blob((0.6, 0.5, 0.44), (0, 0.08, 0.82), stone, "hips", segs=(10, 7))
	b.blob((0.84, 0.64, 0.82), (0, -0.1, 1.18), stone, "chest", rot=(28, 0, 0), segs=(12, 8))
	b.blob((0.58, 0.3, 0.6), (0, -0.36, 1.1), stone_l, "chest", rot=(20, 0, 0), segs=(10, 7))       # breast plate
	for k in range(3):   # carved belly ridges
		b.blob((0.44 - 0.06 * k, 0.12, 0.1), (0, -0.44 + 0.03 * k, 1.02 - 0.12 * k), stone_d, "chest", segs=(8, 4))
	b.blob((0.62, 0.5, 0.36), (0, 0.12, 1.44), stone_d, "chest", rot=(34, 0, 0), segs=(10, 6))       # the hunch
	for x, y, z in ((0.0, 0.26, 1.34), (0.0, 0.34, 1.14), (0.0, 0.34, 0.94)):   # spine knobs
		b.blob((0.12, 0.12, 0.12), (x, y, z), stone_l, "chest", segs=(6, 4))
	# the head: low and forward, a heavy brow, glowing eyes, fangs, horns sweeping back
	b.blob((0.44, 0.46, 0.42), (0, -0.5, 1.52), stone, "head", segs=(10, 8))
	b.seg((0, -0.64, 1.5), (0, -0.84, 1.44), 0.15, 0.11, stone, "head", sides=8)               # snout
	b.blob((0.2, 0.1, 0.1), (0, -0.86, 1.46), stone_d, "head", segs=(6, 4))
	b.blob((0.5, 0.14, 0.12), (0, -0.68, 1.62), stone_d, "head", rot=(-10, 0, 0), segs=(8, 4))       # brow
	b.blob((0.3, 0.3, 0.12), (0, -0.68, 1.36), stone_l, "jaw", segs=(8, 5))
	for s in (1, -1):
		b.blob((0.1, 0.05, 0.06), (0.11 * s, -0.72, 1.55), eye, "head", rot=(0, 0, 14 * s), segs=(6, 4))
		b.blob((0.03, 0.03, 0.03), (0.05 * s, -0.9, 1.47), crack, "head", segs=(4, 3))            # nostrils
		b.seg((0.08 * s, -0.8, 1.41), (0.09 * s, -0.82, 1.33), 0.025, 0.0, stone_l, "head", sides=4)   # upper fangs
		b.seg((0.1 * s, -0.78, 1.36), (0.11 * s, -0.8, 1.46), 0.022, 0.0, stone_l, "jaw", sides=4)     # lower tusks
		b.seg((0.2 * s, -0.46, 1.58), (0.42 * s, -0.36, 1.7), 0.07, 0.0, stone, "head", sides=5)        # pointed ears
		pts = [(0.13 * s, -0.54, 1.68), (0.2 * s, -0.46, 1.82), (0.26 * s, -0.3, 1.94), (0.28 * s, -0.12, 1.96), (0.26 * s, 0.02, 1.88)]
		radii = [0.075, 0.062, 0.048, 0.032, 0.016, 0.0]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(p, q, radii[k], radii[k + 1], stone_d if k % 2 else stone, "head", sides=6)
	b.blob((0.24, 0.2, 0.08), (0.1, -0.44, 1.73), moss, "head", segs=(7, 4))
	# long arms: the fists planted on the ground like a knuckle-walker, black claws curling under
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		b.blob((0.38, 0.38, 0.34), (0.42 * s, -0.18, 1.38), stone, arm, segs=(9, 6))               # shoulder
		b.blob((0.24, 0.22, 0.1), (0.44 * s, -0.16, 1.55), moss if s > 0 else moss_b, arm, segs=(7, 4))
		b.seg((0.44 * s, -0.2, 1.32), (0.62 * s, -0.24, 0.92), 0.17, 0.13, stone, arm, sides=8)
		b.blob((0.3, 0.3, 0.34), (0.54 * s, -0.24, 1.14), stone, arm, segs=(8, 6))                   # bulging upper arm
		b.blob((0.24, 0.24, 0.24), (0.62 * s, -0.24, 0.92), stone_d, hand, segs=(7, 5))              # elbow
		b.seg((0.62 * s, -0.26, 0.92), (0.6 * s, -0.5, 0.24), 0.14, 0.1, stone, hand, sides=8)
		b.blob((0.26, 0.28, 0.4), (0.62 * s, -0.34, 0.7), stone, hand, rot=(-18, 0, 0), segs=(8, 6))   # heavy forearm
		b.blob((0.3, 0.32, 0.24), (0.6 * s, -0.54, 0.14), stone_d, hand, segs=(8, 6))               # the fist
		for k in (-1, 0, 1):
			root = Vector((0.6 * s + 0.08 * k, -0.66, 0.13))
			b.seg(tuple(root), tuple(root + Vector((0.01 * k, -0.1, -0.11))), 0.035, 0.0, claw, hand, sides=4)
		# digitigrade legs: thick thigh, the shin raking back to a high heel, a clawed foot
		leg = f"leg_{side}"
		b.blob((0.3, 0.46, 0.34), (0.26 * s, -0.06, 0.66), stone, leg, rot=(30, 0, 0), segs=(9, 6))
		b.seg((0.28 * s, -0.2, 0.52), (0.28 * s, 0.1, 0.2), 0.1, 0.075, stone, leg, sides=7)
		b.blob((0.14, 0.14, 0.14), (0.28 * s, 0.1, 0.2), stone_d, leg, segs=(6, 4))
		b.seg((0.28 * s, 0.1, 0.2), (0.28 * s, -0.08, 0.06), 0.075, 0.08, stone, leg, sides=7)
		b.blob((0.22, 0.26, 0.1), (0.28 * s, -0.12, 0.05), stone_d, leg, segs=(8, 5))
		for k in (-1, 0, 1):
			root = Vector((0.28 * s + 0.07 * k, -0.24, 0.05))
			b.seg(tuple(root), tuple(root + Vector((0.02 * k, -0.1, -0.04))), 0.03, 0.0, claw, leg, sides=4)
		_bat_wing(b, s, (0.22 * s, 0.2, 1.44), (stone_d, wing_m, claw), f"wing_{side}", scale=1.15)
	# the tail: thin and long, ending in a barbed stone spade
	pts = [(0, 0.3, 0.76), (0, 0.8, 0.44), (0, 1.2, 0.3), (0, 1.56, 0.26)]
	for k, bone in enumerate(("tail1", "tail2", "tail3")):
		b.seg(pts[k], pts[k + 1], 0.1 - 0.025 * k, 0.075 - 0.025 * k, stone if k % 2 else stone_d, bone, sides=6)
	start = len(b.parts)
	_slab(b, [(0, 1.52, 0.26), (0.16, 1.62, 0.26), (0, 1.84, 0.24), (-0.16, 1.62, 0.26)], 0.05, stone_d)
	_on_bone(b, start, "tail3")
	# weathering: cracks and moss
	for p, q, bone in (((0.2, -0.46, 1.3), (0.12, -0.5, 1.12), "chest"), ((-0.24, -0.4, 1.34), (-0.3, -0.36, 1.18), "chest"),
					   ((0.12, -0.6, 1.66), (0.18, -0.66, 1.58), "head")):
		b.seg(p, q, 0.014, 0.01, crack, bone, sides=3)
	for k in range(6):
		a = rng.uniform(0, math.pi)
		loc = (0.3 * math.cos(a), 0.1 + 0.18 * math.sin(a), 1.46 + rng.uniform(-0.1, 0.05))
		b.blob((0.2, 0.18, 0.07), loc, moss if k % 2 else moss_b, "chest", rot=(20, rng.uniform(-20, 20), 0), segs=(6, 4))
	arm = b.build()

	def wings(k=0.0, flap=0.0):
		"""k=0 folded, 1 flung open to the sides."""
		return {"wing_l": {"rot": (-10 * k - flap, -70 * k, -40 * k)}, "wing_r": {"rot": (-10 * k - flap, 70 * k, 40 * k)}}

	def arms(l, r, bend=0.0, spread=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, 0, 0)}, "hand_r": {"rot": (bend, 0, 0)}}

	def tail(t, amp, cycles=1.0):
		return {"tail1": {"rot": (3 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (0, 0, amp * wave(t, cycles, -0.15))}, "tail3": {"rot": (0, 0, amp * 1.3 * wave(t, cycles, -0.3))}}

	def idle(t):   # perched and still as its own statue; it breathes, the head twitches round, a wing shifts
		look = seq(t, [(0, 0), (0.3, 0), (0.33, 30), (0.55, 30), (0.58, -10), (0.8, -10), (0.83, 0)])
		shift = seq(t, [(0.6, 0), (0.66, 0.16), (0.74, 0)])
		return merge({"chest": {"rot": (1.5 * wave(t), 0, 0)}, "head": {"rot": (-2 * wave(t), 0, look)},
					  "hips": {"loc": (0, 0, -0.01 * (1 + wave(t)))}}, wings(shift), tail(t, 6, 0.5), arms(0, 0))

	def walk(t):   # a knuckle-walking prowl: fists and feet in turn
		a = 22 * wave(t)
		return merge({"leg_l": {"rot": (a, 0, 0)}, "leg_r": {"rot": (-a, 0, 0)}, "hips": {"rot": (0, 3 * wave(t), 0),
					  "loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "chest": {"rot": (0, -3 * wave(t), 4 * wave(t))},
					  "head": {"rot": (3 * wave(t, 2), 0, -3 * wave(t))}}, arms(-a * 0.9, a * 0.9), wings(0.04), tail(t, 12))

	def run(t):   # bounds on all fours with the wings half open
		f, k = 36 * wave(t), 36 * wave(t, 1, 0.5)
		flap = 0.5 + 0.5 * wave(t, 1, 0.1)
		return merge({"leg_l": {"rot": (k, 0, 0)}, "leg_r": {"rot": (k * 0.85, 0, 0)},
					  "root": {"loc": (0, 0, 0.1 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (6, 0, 0)}}, arms(f, f * 0.85), wings(0.3 + 0.25 * flap, 14 * flap), tail(t, 8))

	def attack(t):   # rears up with wings flung wide, then rakes down with both claws
		rise = seq(t, [(0, 0), (0.35, 1), (0.52, 0.2), (0.7, 0.1), (1, 0)])
		claws = seq(t, [(0, 0), (0.35, 120), (0.5, -10), (0.66, 0), (1, 0)])
		lunge = seq(t, [(0, 0), (0.35, -0.04), (0.5, 0.36), (0.66, 0.3), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0.12 * rise)}, "hips": {"rot": (14 * rise, 0, 0)}, "chest": {"rot": (24 * rise, 0, 0)},
					  "head": {"rot": (-18 * rise + seq(t, [(0.4, 0), (0.5, -10), (0.7, 0)]), 0, 0)},
					  "jaw": {"rot": (seq(t, [(0, 0), (0.35, -28), (0.5, -20), (0.7, 0)]), 0, 0)},
					  "leg_l": {"rot": (-14 * rise, 0, 0)}, "leg_r": {"rot": (-14 * rise, 0, 0)}},
					 arms(claws, claws * 0.9, seq(t, [(0, 0), (0.35, 30), (0.5, -10), (1, 0)]), 12 * rise),
					 wings(seq(t, [(0, 0), (0.3, 1), (0.6, 0.8), (1, 0)])), tail(t, 16, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"chest": {"rot": (10 * k, 6 * k, 8 * k)}, "head": {"rot": (14 * k, 0, 16 * k)}, "jaw": {"rot": (-20 * k, 0, 0)},
					  "hips": {"loc": (0, -0.08 * k, 0)}}, arms(-18 * k, -10 * k), wings(0.35 * k), tail(t, 18 * k, 2))

	def death(t):   # the light goes out of it; it slumps forward onto its face, wings sagging open
		f = seq(t, [(0.15, 0), (0.7, 1)])
		g = seq(t, [(0.4, 0), (0.9, 1)])
		return merge({"root": {"loc": (0, -0.3 * f, -0.46 * f), "rot": (-18 * f, 0, 0)},
					  "hips": {"rot": (-20 * f, 8 * g, 0)}, "chest": {"rot": (-32 * f, 0, 6 * g)},
					  "head": {"rot": (-10 * f, 0, 24 * g)}, "jaw": {"rot": (-16 * g, 0, 0)},
					  "leg_l": {"rot": (-40 * f, 0, 0)}, "leg_r": {"rot": (-50 * f, 0, 0)}},
					 arms(40 * f, 56 * f, -30 * f, 20 * g), wings(0.55 * g, -20 * g), {"tail1": {"rot": (-10 * f, 0, 18 * g)}})

	clip(arm, "idle", 4.0, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.55, run, True)
	clip(arm, "attack", 0.9, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- High Terrace bolt-ons (KayKit mesh space)
# Harpies (a repainted Rogue), fallen monks and their abbot (a repainted Mage with the
# Barbarian's bald head), the mossy terrace golems (the stone knight) and mountain trolls.

def harpy_materials(matriarch=False):
	p = "harpy_m" if matriarch else "harpy"
	return {
		"feather": material(f"{p}_feather", "5e3a2c" if matriarch else "8a7058", 0.9),
		"feather_d": material(f"{p}_feather_dark", "2e1c16" if matriarch else "4a3a2c", 0.9),
		"feather_l": material(f"{p}_feather_light", "8a5a44" if matriarch else "b8a488", 0.9),
		"band": material(f"{p}_band", "3a2620" if matriarch else "6a5440", 0.9),
		"tip": material(f"{p}_tip", "a82a1e" if matriarch else "e8dcc8", 0.85),
		"beak": material(f"{p}_beak", "d8a840", 0.5),
		"beak_d": material(f"{p}_beak_dark", "3a3028", 0.4),
		"talon": material(f"{p}_talon", "1e1814", 0.4),
		"scale": material(f"{p}_scale", "c89a3a", 0.6),
		"plume": material(f"{p}_plume", "c8302a", 0.8),
		"plume_b": material(f"{p}_plume_b", "f0e6d4", 0.8),
		"bone": material(f"{p}_bone", "e8dec4", 0.6),
		"gold": material(f"{p}_gold", "e0b038", 0.4),
		"glow": material(f"{p}_glow", "ffcc40", 0.2, emit=2.4),
	}


def _feather(b, base, direction, length, width, mat, normal, tip_mat=None, thick=0.035):
	"""A flat, rounded feather from `base` along `direction`, its face toward `normal`; a pale or dark tip."""
	d = Vector(direction).normalized()
	a = Vector(base)
	_oblob(b, (width, length, thick), tuple(a + d * length * 0.5), d, normal, mat, "x", segs=(8, 4))
	if tip_mat:
		_oblob(b, (width * 0.9, length * 0.3, thick * 1.15), tuple(a + d * length * 0.86), d, normal, tip_mat, "x", segs=(6, 4))


def _harpy_head(b, m, matriarch):
	"""Over the Rogue's own head (hair repainted to feathers): a hooked beak over the nose, feathered brows,
	tufts over the ears and a crest; the matriarch's crest is a crown of long red and white plumes."""
	# the beak: from between the eyes, hooking down over the mouth
	b.seg((0, -0.46, 1.66), (0, -0.62, 1.56), 0.075, 0.055, m["beak"], "x", sides=8)
	b.seg((0, -0.62, 1.56), (0, -0.66, 1.44), 0.055, 0.008, m["beak_d"], "x", sides=7)
	b.blob((0.2, 0.08, 0.08), (0, -0.48, 1.68), m["beak"], "x", segs=(8, 4))                    # the cere
	for s in (1, -1):
		for k in range(3):   # swept-up brow feathers
			_feather(b, (0.08 * s + 0.07 * k * s, -0.5 + 0.03 * k, 1.72 + 0.01 * k), (0.8 * s, 0.2, 0.55), 0.18 - 0.02 * k, 0.07,
					 m["feather_d"], (0, -1, 0.3))
		for k in range(4):   # tufts sweeping back over the ears
			_feather(b, (0.46 * s, -0.08 + 0.06 * k, 1.78 - 0.06 * k), (0.6 * s, 0.8, 0.35 - 0.1 * k), 0.34 - 0.03 * k, 0.1,
					 (m["feather"], m["feather_l"])[k % 2], (s, -0.3, 0.4), m["band"])
	if not matriarch:   # a ragged crest from brow to nape
		for k in range(7):
			j = k - 3
			base = (0.06 * j, -0.2 + 0.08 * k, 2.12 - 0.012 * j * j)
			_feather(b, base, (0.25 * j, 0.7 + 0.1 * k, 0.9 - 0.08 * k), 0.46 - 0.035 * abs(j), 0.12, (m["feather"], m["feather_l"])[k % 2],
					 (1, 0, 0.1 * j), m["tip"])
	else:   # a crown of long plumes fanning up and back, bound by a bone circlet with a gold stone
		for k in range(9):
			j = k - 4
			base = (0.07 * j, -0.12 + 0.02 * abs(j), 2.1 - 0.012 * j * j)
			d = (0.3 * j, 0.25 + 0.08 * abs(j), 1.0)
			_feather(b, base, d, 0.82 - 0.06 * abs(j), 0.13, (m["plume"], m["plume_b"])[k % 2], (1, 0, 0.12 * j), m["feather_d"])
		for k in range(5):
			j = k - 2
			_feather(b, (0.1 * j, 0.24, 2.02), (0.2 * j, 1.0, 0.5), 0.5, 0.12, m["feather_d"], (1, 0, 0.1 * j), m["plume"])
		_ring(b, (0, 0.0, 1.96), (0.5, 0.5), (0, -6), 0.035, m["bone"], sides=18)
		for k in range(8):   # little bone spikes round the circlet
			a = -math.pi / 2 + (k - 3.5) * 0.36
			p = Vector((0.5 * math.cos(a), 0.5 * math.sin(a), 1.96 - 0.05 * math.sin(a)))
			b.seg(tuple(p), tuple(p + Vector((0.02 * math.cos(a), 0.02 * math.sin(a), 0.12))), 0.03, 0.0, m["bone"], "x", sides=4)
		b.blob((0.12, 0.07, 0.12), (0, -0.52, 2.0), m["gold"], "x", segs=(8, 5))
		b.blob((0.07, 0.05, 0.07), (0, -0.56, 2.0), m["glow"], "x", segs=(6, 4))


def build_harpy_head():
	b = Builder("harpy_head")
	_harpy_head(b, harpy_materials(), False)
	return b.build_static()


def build_harpy_matriarch_head():
	b = Builder("harpy_matriarch_head")
	_harpy_head(b, harpy_materials(True), True)
	return b.build_static()


def _harpy_wings(b, m, big):
	"""Two feathered wings half-spread from the upper back, and a ruff of feathers round the neck."""
	k = 1.12 if big else 1.0
	for j in range(16):   # the ruff
		a = 2 * math.pi * j / 16
		p = Vector((0.36 * math.sin(a), 0.3 * math.cos(a), 1.26))
		out = Vector((math.sin(a), math.cos(a), 0))
		_feather(b, tuple(p), tuple(out * 0.5 + Vector((0, 0, -1))), 0.26, 0.14, (m["feather"], m["feather_l"], m["feather_d"])[j % 3],
				 tuple(out + Vector((0, 0, 0.4))))
	for s in (1, -1):
		root = Vector((0.14 * s, 0.34, 1.2))
		elbow = Vector((0.5 * s, 0.56, 1.44)) * k + Vector((0, 0, 1.2 * (1 - k)))
		wrist = Vector((0.86 * s, 0.64, 1.5)) * k + Vector((0, 0, 1.2 * (1 - k)))
		back = Vector((0.12 * s, 1.0, 0.18))   # the face of the wing looks back and a little out
		b.seg(tuple(root), tuple(elbow), 0.07, 0.06, m["feather_d"], "x", sides=6)
		b.seg(tuple(elbow), tuple(wrist), 0.06, 0.045, m["feather_d"], "x", sides=6)
		for j in range(6):   # primaries fanning from the wrist, out and down
			a = math.radians(-20 - 17 * j)
			d = Vector((math.cos(a) * s, 0.12, math.sin(a)))
			_feather(b, tuple(wrist + Vector((0, 0.02 * j, 0))), tuple(d), (0.78 - 0.04 * j) * k, 0.17,
					 (m["feather"], m["band"])[j % 2], tuple(back), m["tip"])
		for j in range(6):   # secondaries hanging from the arm
			u = j / 5
			p = root + (wrist - root) * (0.2 + 0.75 * u)
			d = Vector((0.12 * s * u, 0.06, -1))
			_feather(b, tuple(p + Vector((0, 0.03, 0))), tuple(d), (0.4 + 0.2 * u) * k, 0.17, (m["feather_l"], m["feather"])[j % 2],
					 tuple(back), m["tip"])
		for j in range(5):   # coverts over the arm
			u = (j + 0.5) / 5
			p = root + (wrist - root) * u + Vector((0, 0.05, 0.02))
			_feather(b, tuple(p), (0.1 * s, 0.1, -1), 0.22 * k, 0.16, m["feather_d"] if j % 2 else m["band"], tuple(back))


def build_harpy_wings():
	b = Builder("harpy_wings")
	_harpy_wings(b, harpy_materials(), False)
	return b.build_static()


def build_harpy_matriarch_wings():
	b = Builder("harpy_matriarch_wings")
	_harpy_wings(b, harpy_materials(True), True)
	return b.build_static()


def _harpy_talon(name, s, matriarch=False):
	"""Scaly bird toes and black talons over the (repainted) boot, pinned to the foot bone."""
	m = harpy_materials(matriarch)
	b = Builder(name)
	x = 0.17 * s
	b.blob((0.2, 0.26, 0.12), (x, -0.08, 0.07), m["scale"], "x", segs=(8, 5))
	for dx, dy in ((0.0, -0.22), (0.08, -0.17), (-0.08, -0.17), (0.0, 0.14)):
		root = Vector((x, -0.1, 0.05))
		end = root + Vector((dx * s if dx else 0.0, dy, -0.02))
		b.seg(tuple(root), tuple(end), 0.04, 0.03, m["scale"], "x", sides=5)
		d = (end - root).normalized()
		b.seg(tuple(end), tuple(end + d * 0.08 + Vector((0, 0, -0.04))), 0.03, 0.004, m["talon"], "x", sides=4)
	return b.build_static()


def build_harpy_talon_l():
	return _harpy_talon("harpy_talon_l", 1)


def build_harpy_talon_r():
	return _harpy_talon("harpy_talon_r", -1)


# --- fallen monks: a KayKit head as a bolt-on (the Barbarian's is bald), prayer beads, the abbot's hat

def _repaint_image(im, cells, name):
	"""A copy of a KayKit palette image repainted cell by cell (see repaint_kaykit), saved to a temp PNG."""
	import tempfile
	import numpy as np
	w, h = im.size
	px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
	lum = px[:, :, 0] * 0.3 + px[:, :, 1] * 0.59 + px[:, :, 2] * 0.11
	cw, ch = w // 8, h // 4
	for (col, row), (lt, dk) in cells.items():
		y0 = h - (row + 1) * ch
		sl = (slice(y0, y0 + ch), slice(col * cw, (col + 1) * cw))
		cl = lum[sl]
		t = ((cl - cl.min()) / max(1e-4, cl.max() - cl.min()))[:, :, None]
		light, dark = np.array(_hex_rgb(lt)), np.array(_hex_rgb(dk))
		px[sl[0], sl[1], :3] = dark + (light - dark) * t
	# a fresh image saved to disk, so the exporter can't fall back on the packed original
	out = bpy.data.images.new(name, w, h, alpha=True)
	out.pixels[:] = px.ravel()
	out.filepath_raw = os.path.join(tempfile.mkdtemp(), f"{name}.png")
	out.file_format = "PNG"
	out.save()
	return out


def _kaykit_part(src, part, name, cells=None):
	"""Imports a KayKit character and keeps one mesh part as a static object in mesh space (its skin and
	rig dropped), its palette optionally repainted: a bald head for a hooded body, say."""
	bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
	keep = bpy.data.objects[part]
	mw = keep.matrix_world.copy()
	for o in list(bpy.data.objects):
		if o is not keep:
			bpy.data.objects.remove(o, do_unlink=True)
	keep.parent = None
	for mod in list(keep.modifiers):
		keep.modifiers.remove(mod)
	keep.vertex_groups.clear()
	keep.data.transform(mw)
	keep.matrix_world = Matrix.Identity(4)
	keep.name = name
	if cells:
		for slot in keep.material_slots:
			for node in slot.material.node_tree.nodes:
				if node.type == "TEX_IMAGE" and node.image:
					node.image = _repaint_image(node.image, cells, f"{name}_texture")
	return keep


def build_monk_head():
	"""The Barbarian's bald head for the fallen monks, his gray beard gone ash-dark."""
	return _kaykit_part(KAYKIT + "Barbarian.glb", "Barbarian_Head", "monk_head", {(1, 0): ("6a5a50", "2a2220")})


def build_abbot_head():
	return _kaykit_part(KAYKIT + "Barbarian.glb", "Barbarian_Head", "abbot_head", {(1, 0): ("f4f0e8", "a8a098")})


def monk_materials(abbot=False):
	p = "abbot" if abbot else "monk"
	return {
		"bead": material(f"{p}_bead", "5a3420", 0.5),
		"bead_b": material(f"{p}_bead_b", "8a5430", 0.5),
		"amber": material(f"{p}_amber", "f0a030", 0.3, emit=0.6),
		"cord": material(f"{p}_cord", "8a2a1e", 0.8),
		"gold": material(f"{p}_gold", "e6b43c", 0.35),
		"gold_d": material(f"{p}_gold_dark", "9a6a1a", 0.4),
		"crimson": material(f"{p}_crimson", "8e1a18", 0.8),
		"crimson_d": material(f"{p}_crimson_dark", "4a0a0a", 0.85),
		"jewel": material(f"{p}_jewel", "ff5a2a", 0.2, emit=2.0),
		"ivory": material(f"{p}_ivory", "f2ead4", 0.5),
	}


def build_prayer_beads():
	"""A long string of big wooden prayer beads over the robe, an amber bead every ninth and a
	tusked pendant of the Dawn-Tusk hanging at the bottom."""
	m = monk_materials()
	b = Builder("prayer_beads")
	pts = []
	n = 34
	for k in range(n + 1):
		a = 2 * math.pi * k / n   # 0 at the back of the neck, pi at the bottom in front
		front = (1 - math.cos(a)) / 2
		x = 0.33 * math.sin(a) * (1 - 0.35 * front ** 2)
		y = 0.26 * math.cos(a) - 0.1 * front - 0.02
		z = 1.26 - 0.36 * front ** 1.6
		if y < -0.2:
			y = -0.2 - 0.16 * front ** 2   # the front of the loop drapes over the chest
		pts.append(Vector((x, y, z)))
	for k, p in enumerate(pts[:-1]):
		big = k % 9 == 4
		r = 0.085 if big else 0.062
		b.blob((r, r, r), tuple(p), m["amber"] if big else (m["bead"], m["bead_b"])[k % 2], "x", segs=(8, 6))
	bottom = pts[n // 2]
	b.seg(tuple(bottom), tuple(bottom + Vector((0, -0.01, -0.12))), 0.012, 0.012, m["cord"], "x", sides=4)
	c = bottom + Vector((0, -0.02, -0.2))
	b.blob((0.13, 0.05, 0.14), tuple(c), m["gold"], "x", segs=(10, 6))                          # the pendant: a gold elephant's face
	for s in (1, -1):
		b.blob((0.07, 0.03, 0.09), tuple(c + Vector((0.07 * s, 0.0, 0.01))), m["gold_d"], "x", segs=(6, 4))   # ears
		b.seg(tuple(c + Vector((0.03 * s, -0.03, -0.03))), tuple(c + Vector((0.05 * s, -0.05, 0.02))), 0.01, 0.003, m["ivory"], "x", sides=4)
	b.seg(tuple(c + Vector((0, -0.03, -0.02))), tuple(c + Vector((0, -0.04, -0.11))), 0.02, 0.012, m["gold_d"], "x", sides=5)   # trunk
	return b.build_static()


def build_abbot_hat():
	"""A tall crimson and gold mitre over the abbot's bald head: banded, a gold sun of the Dawn-Tusk
	at the front, gilt tusks curling up the sides and a jewelled finial."""
	m = monk_materials(True)
	b = Builder("abbot_hat")
	b.seg((0, 0.0, 1.9), (0, 0.0, 2.06), 0.5, 0.5, m["gold"], "x", sides=18)                     # the gold band
	_ring(b, (0, 0.0, 1.92), (0.5, 0.5), (0, 0), 0.03, m["gold_d"], sides=18)
	b.seg((0, 0.0, 2.06), (0, 0.02, 2.62), 0.48, 0.3, m["crimson"], "x", sides=18)              # the tall body
	b.seg((0, 0.02, 2.62), (0, 0.03, 2.86), 0.3, 0.1, m["crimson"], "x", sides=18)
	for z, r in ((2.28, 0.425), (2.5, 0.35)):
		b.seg((0, 0.01, z - 0.03), (0, 0.01, z + 0.03), r, r - 0.01, m["gold"], "x", sides=18)
	for s in (1, -1):
		pts = [(0.44 * s, -0.12, 1.98), (0.54 * s, -0.16, 2.14), (0.52 * s, -0.12, 2.34), (0.42 * s, -0.04, 2.48)]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):   # gilt tusks
			b.seg(p, q, 0.05 - 0.014 * k, 0.036 - 0.014 * k if k < 2 else 0.0, m["ivory"] if k < 2 else m["gold"], "x", sides=6)
	_sun(b, (0, -0.44, 2.28), (0, -1, 0.3), 0.15, m["gold"], m["gold"], m["gold_d"], count=12, ray_len=0.55, thick=0.04, inner=m["jewel"])
	b.blob((0.14, 0.14, 0.16), (0, 0.03, 2.92), m["gold"], "x", segs=(8, 6))
	b.blob((0.08, 0.08, 0.1), (0, 0.03, 3.02), m["jewel"], "x", segs=(6, 4))
	return b.build_static()


# --- terrace golems: the stone guardian grown old on the High Terrace

def terrace_materials(colossus=False):
	p = "terrace_colossus" if colossus else "terrace"
	return {
		"stone": material(f"{p}_stone", "9aa08a", 0.95),
		"stone_light": material(f"{p}_stone_light", "b8bca4", 0.95),
		"stone_dark": material(f"{p}_stone_dark", "646a58", 0.95),
		"crack": material(f"{p}_crack", "2a2e24", 0.95),
		"moss": material(f"{p}_moss", "4e7428", 0.95),
		"moss_b": material(f"{p}_moss_b", "7a9438", 0.95),
		"lichen": material(f"{p}_lichen", "c8b85a", 0.95),
		"gilt": material(f"{p}_gilt", "b89a4a", 0.6),
		"gilt_dark": material(f"{p}_gilt_dark", "7a6028", 0.6),
		"glow": material(f"{p}_glow", "7affc8" if colossus else "9affb0", 0.2, emit=4.0 if colossus else 2.6),
		"flag": material(f"{p}_flag", "c83a24", 0.9),
		"flag_b": material(f"{p}_flag_b", "e8b830", 0.9),
		"flag_c": material(f"{p}_flag_c", "2a6aa8", 0.9),
	}


def _mossy_overgrowth(b, m, big):
	"""Moss heaped on the crown and ears, strands of it hanging, lichen; the colossus wears a faded
	string of prayer flags from ear to ear and a jade stone where its sun disc was."""
	b.blob((0.76, 0.62, 0.2), (0, 0.06, 2.24), m["moss"], "x", rot=(8, 0, 0), segs=(10, 6))
	b.blob((0.36, 0.3, 0.12), (0.2, -0.16, 2.2), m["moss_b"], "x", segs=(8, 5))
	for s in (1, -1):
		b.blob((0.3, 0.34, 0.12), (0.74 * s, 0.02, 1.98), m["moss"], "x", rot=(0, 30 * s, 0), segs=(8, 5))
		for k in range(3):
			_kelp(b, (0.8 * s - 0.1 * k * s, 0.08, 1.92 - 0.1 * k), 0.34 - 0.06 * k, m["moss"] if k % 2 else m["moss_b"],
				  lean=(0.1 * s, 0.1), width=0.045, parts=3)
	for x, y, ln in ((0.3, -0.36, 0.4), (-0.24, -0.4, 0.3), (0.0, -0.44, 0.22), (-0.4, -0.3, 0.34)):
		_kelp(b, (x, y, 2.1), ln, m["moss_b"], lean=(0.0, -0.1), width=0.04, parts=3)
	for x, z in ((0.3, 1.68), (-0.36, 1.86), (0.1, 1.5)):
		b.blob((0.16, 0.06, 0.12), (x, -0.5, z), m["lichen"], "x", segs=(6, 3))
	if big:
		b.blob((0.2, 0.1, 0.2), (0, -0.5, 2.06), m["gilt_dark"], "x", segs=(8, 5))
		b.blob((0.13, 0.08, 0.13), (0, -0.54, 2.06), m["glow"], "x", segs=(8, 5))
		pts = []
		for k in range(11):
			u = k / 10
			pts.append(Vector((-0.9 + 1.8 * u, -0.3 - 0.08 * math.sin(math.pi * u), 2.08 - 0.26 * math.sin(math.pi * u))))
		for p, q in zip(pts, pts[1:]):
			b.seg(tuple(p), tuple(q), 0.012, 0.012, m["crack"], "x", sides=4)
		for k, p in enumerate(pts[1:-1]):
			mat = (m["flag"], m["flag_b"], m["flag_c"])[k % 3]
			_slab(b, [tuple(p + Vector((-0.07, -0.01, 0))), tuple(p + Vector((0.07, -0.01, 0))),
					  tuple(p + Vector((0.07, -0.02, -0.16))), tuple(p + Vector((-0.07, -0.02, -0.16)))], 0.015, mat)


def build_terrace_golem_head():
	b = Builder("terrace_golem_head")
	_elephant_head(b, terrace_materials(), mossy=True)
	return b.build_static()


def build_terrace_colossus_head():
	b = Builder("terrace_colossus_head")
	_elephant_head(b, terrace_materials(True), big=True, mossy=True)
	return b.build_static()


def build_terrace_golem_chest():
	"""Mossy stone shoulders, cracks, vines trailing down the chest."""
	m = terrace_materials()
	b = Builder("terrace_golem_chest")
	for s in (1, -1):
		b.blob((0.4, 0.48, 0.24), (0.38 * s, 0.0, 1.3), m["stone"], "x", rot=(0, 20 * s, 0), segs=(7, 4))
		b.blob((0.34, 0.4, 0.12), (0.4 * s, 0.0, 1.42), m["moss"], "x", rot=(0, 24 * s, 0), segs=(8, 4))
		b.seg((0.3 * s, -0.37, 1.12), (0.24 * s, -0.4, 0.98), 0.014, 0.01, m["crack"], "x", sides=3)
		b.seg((0.24 * s, -0.4, 0.98), (0.27 * s, -0.4, 0.86), 0.012, 0.008, m["crack"], "x", sides=3)
		_kelp(b, (0.46 * s, -0.12, 1.36), 0.4, m["moss_b"], lean=(0.05 * s, -0.1), width=0.04, parts=3)
		_kelp(b, (0.3 * s, 0.3, 1.34), 0.5, m["moss"], lean=(0.0, 0.1), width=0.045, parts=3)
	for x, z in ((0.14, 1.08), (-0.2, 0.92)):
		b.blob((0.14, 0.05, 0.1), (x, -0.4, z), m["lichen"], "x", segs=(6, 3))
	return b.build_static()


# --- mountain trolls: the river troll's bolt-ons in snow colors

def build_mountain_troll_head():
	b = Builder("mountain_troll_head")
	_troll_head(b, troll_materials(mountain=True), False)
	return b.build_static()


def build_mountain_troll_back():
	b = Builder("mountain_troll_back")
	_troll_back(b, troll_materials(mountain=True), True)   # the chief's fur mantle, in white
	return b.build_static()


def build_mountain_troll_loincloth():
	b = Builder("mountain_troll_loincloth")
	_troll_loincloth(b, troll_materials(mountain=True), False)
	return b.build_static()


def build_mountain_troll_fist_l():
	return _troll_fist("mountain_troll_fist_l", 1, False, True)


def build_mountain_troll_fist_r():
	return _troll_fist("mountain_troll_fist_r", -1, False, True)


# ---------------------------------------------------------------- Cinderpass bolt-ons (KayKit mesh space)

def ember_materials(leader=False):
	p = "pyromancer" if leader else "ember"
	return {
		"hood": material(f"{p}_hood", "7a1410" if leader else "2a2424", 0.9),
		"hood_dark": material(f"{p}_hood_dark", "3a0606" if leader else "121010", 0.9),
		"trim": material(f"{p}_trim", "e8b030" if leader else "c8401a", 0.6),
		"mask": material(f"{p}_mask", "1e1a1a", 0.5),
		"mask_b": material(f"{p}_mask_b", "3e3634", 0.6),
		"hole": material(f"{p}_hole", "0a0606", 0.9),
		"glow": material(f"{p}_glow", "ffb030" if leader else "ff6a1a", 0.3, emit=3.0),
		"flame": material(f"{p}_flame", "ff7a1a", 0.4, emit=2.4),
		"flame_b": material(f"{p}_flame_b", "ffc040", 0.3, emit=3.0),
		"horn": material(f"{p}_horn", "1a1416", 0.2),
		"horn_b": material(f"{p}_horn_b", "5a1a10", 0.4),
		"gold": material(f"{p}_gold", "e0b038", 0.4),
	}


def _ember_head(b, m, leader):
	"""A hood over a KayKit mage head (hat hidden), a soot-black mask with ember eyes and a crown of
	flames licking up its brow; the high pyromancer's hood rises into a tall peak between two horns."""
	opening = lambda d: not (d.y < -0.45 and -0.85 < d.z < 0.3 and abs(d.x) < 0.66)
	rim = _shell(b, (1.16, 1.2, 1.18), (0, 0.0, 1.62), m["hood"], opening, segs=(20, 14))
	for p, q in rim:
		if p[1] < -0.2:
			b.seg(p, q, 0.04, 0.04, m["trim"], "x", sides=5)
	_shell(b, (1.12, 1.16, 1.14), (0, 0.0, 1.62), m["hood_dark"], opening, segs=(20, 14))
	b.blob((0.9, 0.9, 0.96), (0, 0.04, 1.6), m["hole"], "x", segs=(12, 8))
	if leader:   # a tall peak standing up, not falling behind
		b.seg((0, 0.04, 2.1), (0, 0.1, 2.5), 0.3, 0.16, m["hood"], "x", sides=10)
		b.seg((0, 0.1, 2.5), (0, 0.2, 2.86), 0.16, 0.01, m["hood"], "x", sides=10)
		_ring(b, (0, 0.05, 2.2), (0.3, 0.3), (0, 0), 0.03, m["trim"], sides=14)
	else:
		b.seg((0, 0.24, 2.1), (0, 0.5, 2.0), 0.24, 0.09, m["hood"], "x", sides=8)
		b.seg((0, 0.5, 2.0), (0, 0.62, 1.74), 0.09, 0.02, m["hood"], "x", sides=8)
	_shell(b, (1.16, 1.06, 0.62), (0, 0.02, 1.1), m["hood"], lambda d: d.z > 0.0)
	_ring(b, (0, 0.02, 1.1), (0.58, 0.53), (0, 0), 0.03, m["trim"], sides=16)
	# the mask: a smooth charred plate, cracked, ember light in the eye slits
	b.blob((0.56, 0.14, 0.62), (0, -0.52, 1.58), m["mask"], "x", segs=(12, 8))
	for s in (1, -1):
		b.blob((0.16, 0.05, 0.06), (0.12 * s, -0.585, 1.64), m["hole"], "x", rot=(0, 14 * s, 0), segs=(8, 4))
		b.blob((0.09, 0.03, 0.03), (0.12 * s, -0.6, 1.64), m["glow"], "x", rot=(0, 14 * s, 0), segs=(6, 4))
		_zigzag(b, [(0.1 * s, -0.59, 1.52), (0.14 * s, -0.59, 1.44), (0.12 * s, -0.58, 1.36)], 0.012, m["glow"], "x")   # glowing cracks
	b.blob((0.12, 0.04, 0.03), (0, -0.59, 1.43), m["glow"], "x", segs=(6, 3))
	for k in range(5):   # flames licking up from the brow of the mask
		j = k - 2
		_flame(b, (0.09 * j, -0.56, 1.8 - 0.02 * abs(j)), (0.15 * j, -0.1, 1), 0.24 - 0.04 * abs(j), 0.05,
			   m["flame"] if k % 2 else m["flame_b"], "x", bend=(0.04 * j, 0.05, 0))
	if leader:
		for s in (1, -1):   # black horns curling up out of the hood
			pts = [(0.4 * s, -0.1, 1.9), (0.56 * s, -0.1, 2.06), (0.64 * s, -0.04, 2.3), (0.58 * s, 0.02, 2.52), (0.46 * s, 0.0, 2.62)]
			for k, (p, q) in enumerate(zip(pts, pts[1:])):
				b.seg(p, q, 0.08 - 0.018 * k, 0.062 - 0.018 * k if k < 3 else 0.0, m["horn"] if k % 2 else m["horn_b"], "x", sides=7)
		b.blob((0.16, 0.1, 0.16), (0, -0.5, 1.98), m["gold"], "x", segs=(8, 5))
		b.blob((0.1, 0.06, 0.1), (0, -0.55, 1.98), m["glow"], "x", segs=(6, 4))


def build_ember_hood():
	b = Builder("ember_hood")
	_ember_head(b, ember_materials(), False)
	return b.build_static()


def build_high_pyromancer_hood():
	b = Builder("high_pyromancer_hood")
	_ember_head(b, ember_materials(True), True)
	return b.build_static()


def ash_materials(lord=False):
	p = "ash_lord" if lord else "ash"
	return {
		"ash": material(f"{p}_ash", "6a6460" if not lord else "3a3432", 0.95),
		"ash_d": material(f"{p}_ash_dark", "3a3634" if not lord else "1e1a1a", 0.95),
		"ash_l": material(f"{p}_ash_light", "9a948e" if not lord else "5a5250", 0.95),
		"smoke": material(f"{p}_smoke", "8a8682" if not lord else "4a4442", 0.95, emit=0.05),
		"ember": material(f"{p}_ember", "ff6a1a", 0.3, emit=3.0),
		"ember_b": material(f"{p}_ember_b", "ffb040", 0.3, emit=3.5),
		"iron": material(f"{p}_iron", "2a2626", 0.4),
		"iron_b": material(f"{p}_iron_b", "4a4240", 0.4),
		"coal": material(f"{p}_coal", "1a1212", 0.9),
	}


def build_charred_embers():
	"""Still smoldering: holes burnt through the breastplate glowing like coals, embers caught on the
	shoulders and a thread of smoke rising off each."""
	import random
	rng = random.Random(131)
	m = ash_materials()
	b = Builder("charred_embers")
	for x, z, r in ((0.12, 1.08, 0.1), (-0.14, 0.96, 0.08), (0.02, 0.86, 0.07), (-0.06, 1.16, 0.06), (0.2, 0.9, 0.05)):
		y = -0.345 - 0.02 * (1 - abs(x) / 0.3)
		_oblob(b, (r * 1.6, r * 1.3, 0.05), (x, y, z), (0, 0, 1), (0, -1, 0), m["coal"], "x", segs=(8, 4))      # a charred rim
		_oblob(b, (r, r * 0.8, 0.05), (x, y - 0.012, z), (0, 0, 1), (0, -1, 0), m["ember"] if r > 0.06 else m["ember_b"], "x", segs=(8, 4))
	for s in (1, -1):
		for k in range(4):
			_rock(b, (0.06, 0.06, 0.05), (0.3 * s + rng.uniform(-0.08, 0.08), rng.uniform(-0.12, 0.12), 1.28), m["ember_b"] if k % 2 else m["ember"], "x", rng)
		for k in range(3):   # smoke rising off the shoulder
			r = 0.08 + 0.03 * k
			_smoke_puff(b, (0.32 * s + 0.03 * k * s, 0.04 * k, 1.42 + 0.16 * k), r, (m["smoke"], m["ash_l"]), rng)
	return b.build_static()


def _smoke_puff(b, loc, r, mats, rng):
	"""A cluster of three soft balls, a smoke puff."""
	for k in range(3):
		off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.5, 0.5))) * r * 0.5
		sz = r * rng.uniform(0.8, 1.2)
		b.blob((sz, sz, sz * 0.9), tuple(Vector(loc) + off), mats[k % len(mats)], "x", segs=(8, 6))


def _ash_tail(b, m, lord):
	"""Where the wraith's legs were: its robe trails off into a column of smoke and cinders, narrowing to the ground."""
	import random
	rng = random.Random(137 if lord else 139)
	for k in range(7):
		u = k / 6
		z = 0.5 - 0.44 * u
		r = 0.42 * (1 - 0.7 * u) * (1.15 if lord else 1.0)
		a = u * 4.0
		c = (0.06 * math.sin(a), 0.08 * math.cos(a) + 0.04 * u, z)
		_smoke_puff(b, c, r, (m["smoke"], m["ash"], m["ash_l"]), rng)
	for k in range(8):   # cinders drifting in it
		a = rng.uniform(0, 2 * math.pi)
		z = rng.uniform(0.1, 0.55)
		rr = 0.22 * (0.4 + z)
		b.blob((0.035, 0.035, 0.035), (rr * math.cos(a), rr * math.sin(a), z), m["ember"], "x", segs=(4, 3))


def build_ash_tail():
	b = Builder("ash_tail")
	_ash_tail(b, ash_materials(), False)
	return b.build_static()


def build_ash_lord_tail():
	b = Builder("ash_lord_tail")
	_ash_tail(b, ash_materials(True), True)
	return b.build_static()


def _ash_shroud(b, m, lord):
	"""Tattered strips of ash-gray shroud hanging from the shoulders, smoke curling off them."""
	import random
	rng = random.Random(149 if lord else 151)
	for k in range(14):
		a = 2 * math.pi * (k + 0.5) / 14
		x, y = 0.46 * math.sin(a), 0.4 * math.cos(a)
		if abs(x) < 0.2 and y < 0:
			continue   # leave the chest open
		out = Vector((math.sin(a), math.cos(a), 0))
		w = Vector((-out.y, out.x, 0)) * 0.1
		c = Vector((x, y, 1.26))
		ln = rng.uniform(0.4, 0.7) * (1.2 if lord else 1.0)
		tip = c + out * 0.12 + Vector((0, 0, -ln))
		_slab(b, [tuple(c - w), tuple(c + w), tuple(tip + w * 0.3), tuple(tip - w * 0.3)], 0.025, (m["ash"], m["ash_d"])[k % 2])
	for k in range(5):
		a = rng.uniform(0, 2 * math.pi)
		_smoke_puff(b, (0.4 * math.sin(a), 0.36 * math.cos(a), 1.36 + rng.uniform(0, 0.1)), 0.12, (m["smoke"], m["ash_l"]), rng)
	if lord:   # a mantle of blackened iron plates
		for s in (1, -1):
			b.blob((0.36, 0.42, 0.14), (0.36 * s, 0.0, 1.3), m["iron"], "x", rot=(0, 26 * s, 0), segs=(8, 5))
			b.seg((0.46 * s, -0.1, 1.34), (0.62 * s, -0.1, 1.5), 0.04, 0.0, m["iron_b"], "x", sides=5)
			b.seg((0.44 * s, 0.1, 1.34), (0.6 * s, 0.12, 1.5), 0.04, 0.0, m["iron_b"], "x", sides=5)


def build_ash_shroud():
	b = Builder("ash_shroud")
	_ash_shroud(b, ash_materials(), False)
	return b.build_static()


def build_ash_lord_shroud():
	b = Builder("ash_lord_shroud")
	_ash_shroud(b, ash_materials(True), True)
	return b.build_static()


def build_ash_lord_crown():
	"""A crown of blackened iron spikes on the skull, embers set in it."""
	m = ash_materials(True)
	b = Builder("ash_lord_crown")
	_ring(b, (0, 0.0, 1.98), (0.44, 0.44), (0, -4), 0.05, m["iron"], sides=18)
	for k in range(9):
		a = -math.pi / 2 + (k - 4) * 0.62
		p = Vector((0.44 * math.cos(a), 0.44 * math.sin(a), 1.99 - 0.02 * math.sin(a)))
		h = 0.34 if k == 4 else (0.24 if k % 2 == 0 else 0.16)
		b.seg(tuple(p), tuple(p + Vector((0.06 * math.cos(a), 0.06 * math.sin(a), h))), 0.05, 0.0, m["iron_b"] if k % 2 else m["iron"], "x", sides=5)
		if k % 2 == 0:
			b.blob((0.06, 0.04, 0.06), tuple(p + Vector((0.02 * math.cos(a), 0.02 * math.sin(a), 0.03))), m["ember_b"], "x", segs=(6, 4))
	return b.build_static()


# ---------------------------------------------------------------- the Ranger (player class)

def build_ranger_mantle():
	"""A forest-green hood worn down, bunched round the neck and lying on the back, pinned at the
	collar with a bronze leaf brooch. Sits where chest gear leaves it showing."""
	hood = material("ranger_hood", "3a6030", 0.9)
	hood_d = material("ranger_hood_dark", "1e3418", 0.9)
	bronze = material("ranger_bronze", "c89a4a", 0.35)
	bronze_d = material("ranger_bronze_dark", "7a5a22", 0.4)
	b = Builder("ranger_mantle")
	for k in range(20):   # a thick fold of cloth round the neck
		a = 2 * math.pi * k / 20
		x, y = 0.33 * math.sin(a), 0.27 * math.cos(a)
		side = abs(math.sin(a))
		b.blob((0.16, 0.14, 0.1), (x, y, 1.24 - 0.06 * side), hood if k % 2 else hood_d, "x", rot=(0, 0, -math.degrees(a)), segs=(8, 5))
	# the hood itself lying down the back, its point tucked under
	b.blob((0.44, 0.24, 0.38), (0, 0.36, 1.12), hood, "x", rot=(-12, 0, 0), segs=(10, 7))
	b.blob((0.34, 0.14, 0.26), (0, 0.44, 1.1), hood_d, "x", rot=(-12, 0, 0), segs=(8, 5))
	b.seg((0, 0.42, 0.96), (0, 0.4, 0.8), 0.1, 0.02, hood, "x", sides=6)
	# the brooch: a bronze leaf at the collar
	c = Vector((0.16, -0.34, 1.16))
	_oblob(b, (0.1, 0.18, 0.03), tuple(c), (0.5, 0, 1), (0, -1, 0), bronze, "x", segs=(8, 4))
	b.seg(tuple(c + Vector((-0.04, -0.018, -0.08))), tuple(c + Vector((0.04, -0.018, 0.08))), 0.008, 0.006, bronze_d, "x", sides=4)
	return b.build_static()


# ---------------------------------------------------------------- playable races
# Bolt-ons for the player races (data/races.json "attach", models.json "race_parts"),
# pinned to the head bone and authored in KayKit character mesh space: every KayKit
# head is the same shape under its hair, its own little ears at x = +-0.54, y = 0,
# z 1.39-1.67, the face's front at y = -0.52, eyes near z 1.62, mouth near z 1.43,
# chin at z 1.22. Parts marked "skin" are modeled near white; the game multiplies
# them by the race's light skin tone. Beards are the Barbarian's own beard lifted
# off his head, so they fit every KayKit face, then grown and restyled.

def race_skin_materials(p):
	return {"skin": material(f"{p}_skin", "f4e8de", 0.8), "inner": material(f"{p}_skin_inner", "d8b8a8", 0.85)}


def _smooth_static(b):
	obj = b.build_static()
	for poly in obj.data.polygons:
		poly.use_smooth = True
	return obj


def _leaf(b, root, tip, width, thick, normal, mat, bulge=0.6, rings=9, sides=10, droop=0.0, lift=0.0):
	"""A flat, lens-shaped lobe from root to tip (an ear): its width follows a rounded
	profile, widest at `bulge` of the way out, lying in the plane whose normal is `normal`.
	`droop` sags its middle that far (world z); `lift` curls its edges toward the normal,
	cupping it like an ear."""
	root, tip = Vector(root), Vector(tip)
	d = tip - root
	n = Vector(normal).normalized()
	wv = d.cross(n).normalized()
	nv = wv.cross(d).normalized()
	bm = bmesh.new()
	loops = []
	for k in range(rings + 1):
		t = k / rings
		if t < bulge:
			prof = math.sin(0.5 * math.pi * t / bulge)
		else:
			prof = math.cos(0.5 * math.pi * (t - bulge) / (1 - bulge))
		prof = prof ** 0.7
		w = max(0.004, width * 0.5 * prof)
		h = max(0.003, thick * 0.5 * prof)
		c = root + d * t + Vector((0, 0, -droop * math.sin(math.pi * t)))
		ring = []
		for j in range(sides):
			a = 2 * math.pi * j / sides
			cw = math.cos(a)
			ring.append(bm.verts.new(c + wv * (w * cw) + nv * (h * math.sin(a) + lift * prof * cw * cw)))
		loops.append(ring)
	for r0, r1 in zip(loops, loops[1:]):
		for j in range(sides):
			bm.faces.new((r0[j], r0[(j + 1) % sides], r1[(j + 1) % sides], r1[j]))
	bm.faces.new(list(reversed(loops[0])))
	bm.faces.new(loops[-1])
	bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
	b._add(bm, mat, "x")


def build_race_ears_elf():
	"""Long pointed elf ears sweeping up and back from the side of the head, out past the hair."""
	m = race_skin_materials("elf_ear")
	b = Builder("race_ears_elf")
	for s in (1, -1):
		nrm = (0.3 * s, -1.0, 0.15)
		_leaf(b, (0.46 * s, 0.03, 1.5), (0.9 * s, 0.18, 1.88), 0.24, 0.06, nrm, m["skin"], bulge=0.3, lift=0.03)
		_leaf(b, (0.56 * s, 0.0, 1.55), (0.82 * s, 0.1, 1.8), 0.11, 0.03, nrm, m["inner"], bulge=0.3)   # its hollow
	return _smooth_static(b)


def build_race_ears_gnome():
	"""Big round, droopy gnome ears and a big round nose."""
	m = race_skin_materials("gnome")
	b = Builder("race_ears_gnome")
	for s in (1, -1):
		nrm = (0.2 * s, -1.0, 0.0)
		_leaf(b, (0.46 * s, 0.03, 1.56), (0.9 * s, 0.14, 1.44), 0.42, 0.08, nrm, m["skin"], bulge=0.55, droop=0.04, lift=0.04)
		_leaf(b, (0.56 * s, 0.0, 1.56), (0.84 * s, 0.09, 1.46), 0.22, 0.04, nrm, m["inner"], bulge=0.55, droop=0.04)
	b.blob((0.24, 0.2, 0.22), (0, -0.6, 1.5), m["skin"], "x", segs=(14, 10))                    # the nose
	b.blob((0.12, 0.1, 0.1), (0, -0.53, 1.58), m["skin"], "x", segs=(10, 7))                     # its bridge
	return _smooth_static(b)


def build_race_troll_face():
	"""The troll's skin-tinted features: a long drooping nose and big pointed ears."""
	m = race_skin_materials("troll_face")
	b = Builder("race_troll_face")
	b.seg((0, -0.48, 1.6), (0, -0.64, 1.46), 0.075, 0.07, m["skin"], "x", sides=10)             # the nose
	b.blob((0.16, 0.18, 0.18), (0, -0.66, 1.42), m["skin"], "x", segs=(12, 8))                   # its bulb, hanging
	b.blob((0.12, 0.1, 0.1), (0, -0.5, 1.6), m["skin"], "x", segs=(10, 6))
	for s in (1, -1):
		b.blob((0.045, 0.04, 0.035), (0.045 * s, -0.7, 1.35), m["inner"], "x", segs=(6, 4))     # nostrils
		nrm = (0.15 * s, -1.0, 0.25)
		_leaf(b, (0.47 * s, 0.04, 1.54), (0.98 * s, 0.26, 1.72), 0.3, 0.07, nrm, m["skin"], bulge=0.3, lift=0.03)
		_leaf(b, (0.56 * s, 0.02, 1.56), (0.9 * s, 0.2, 1.69), 0.14, 0.04, nrm, m["inner"], bulge=0.3)
	return _smooth_static(b)


def build_race_tusks_troll():
	"""Two lower tusks curving up out of the jaw past the corners of the mouth."""
	ivory = material("troll_tusk", "efe4c6", 0.45)
	b = Builder("race_tusks_troll")
	for s in (1, -1):
		b.seg((0.2 * s, -0.44, 1.24), (0.22 * s, -0.54, 1.33), 0.05, 0.04, ivory, "x", sides=8)
		b.seg((0.22 * s, -0.54, 1.33), (0.26 * s, -0.59, 1.45), 0.04, 0.004, ivory, "x", sides=8)
	return _smooth_static(b)


def build_race_ogre_face():
	"""The ogre's heavy brow over the eyes, flat broad nose and underslung jaw (skin-tinted)."""
	m = race_skin_materials("ogre_face")
	b = Builder("race_ogre_face")
	for s in (1, -1):
		b.blob((0.36, 0.2, 0.13), (0.15 * s, -0.47, 1.73), m["skin"], "x", rot=(0, 8 * s, 0), segs=(12, 7))   # brows
	b.blob((0.2, 0.14, 0.14), (0, -0.56, 1.52), m["skin"], "x", segs=(10, 7))                    # nose
	b.blob((0.6, 0.26, 0.2), (0, -0.46, 1.29), m["skin"], "x", segs=(14, 8))                     # the jaw, jutting
	b.blob((0.44, 0.1, 0.07), (0, -0.585, 1.37), m["inner"], "x", segs=(12, 5))                  # the lower lip
	return _smooth_static(b)


def build_race_tusks_ogre():
	"""Two short, thick tusks standing up from the underbite."""
	ivory = material("ogre_tusk", "e8dcbc", 0.5)
	b = Builder("race_tusks_ogre")
	for s in (1, -1):
		b.seg((0.15 * s, -0.56, 1.33), (0.17 * s, -0.6, 1.49), 0.055, 0.012, ivory, "x", sides=8)
	return _smooth_static(b)


def _kaykit_beard(name, mat, grow, forward, widen=1.0):
	"""The Barbarian's beard and mustache (his head's hair cell, below the brows) as a
	static part in `mat`, puffed a little off the face so it covers another beard,
	its lower half grown `grow` times longer and pushed `forward`."""
	keep = _kaykit_part(KAYKIT + "Barbarian.glb", "Barbarian_Head", name)
	bm = bmesh.new()
	bm.from_mesh(keep.data)
	uv = bm.loops.layers.uv.active
	drop = []
	for f in bm.faces:
		u = sum(l[uv].uv.x for l in f.loops) / len(f.loops)
		v = sum(l[uv].uv.y for l in f.loops) / len(f.loops)
		if (int(u * 8), int((1 - v) * 4)) != (1, 0) or f.calc_center_median().z > 1.56:
			drop.append(f)
	bmesh.ops.delete(bm, geom=drop, context="FACES")
	bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
	center = Vector((0, -0.05, 1.6))
	for v in bm.verts:
		p = v.co
		p = center + (p - center) * 1.05          # off the face
		p.x *= widen
		if p.z < 1.36:                            # grow the lower half down and out
			k = 1.36 - p.z
			p.z = 1.36 - k * grow
			p.y -= forward * k * grow
			p.x *= 1.0 - 0.18 * min(1.0, k * grow / 0.5)
		v.co = p
	bm.to_mesh(keep.data)
	bm.free()
	keep.data.materials.clear()
	keep.data.materials.append(mat)
	return keep


def _braid(b, top, length, r, mats, links=5, lean=(0.0, 0.0)):
	"""A braid hanging from `top`: a chain of alternating blobs, tapering."""
	top = Vector(top)
	step = Vector((lean[0], lean[1], -1.0)).normalized() * (length / links)
	for k in range(links):
		rr = r * (1 - 0.1 * k)
		b.blob((rr * 2, rr * 1.8, length / links * 1.35), tuple(top + step * (k + 0.5)), mats[k % 2], "x", segs=(10, 6))
	return top + step * links


def build_race_beard_dwarf():
	"""A big, full dwarf beard from the jaw down over the chest, ending in a braid with an iron bead."""
	m = {"hair": material("dwarf_beard", "7a4222", 0.9), "hair_d": material("dwarf_beard_dark", "542c14", 0.9),
		 "iron": material("dwarf_bead", "a8b0b4", 0.35)}
	beard = _kaykit_beard("race_beard_dwarf", m["hair"], 2.3, 0.18, 1.06)
	b = Builder("race_beard_dwarf")
	b.parts.append(beard)
	b.blob((0.5, 0.3, 0.42), (0, -0.52, 0.98), m["hair"], "x", segs=(14, 9))                     # the full beard's belly
	end = _braid(b, (0, -0.58, 0.84), 0.26, 0.065, (m["hair"], m["hair_d"]), links=4, lean=(0, -0.1))
	b.seg(tuple(end + Vector((0, 0, 0.04))), tuple(end + Vector((0, 0, -0.06))), 0.055, 0.055, m["iron"], "x", sides=10)
	b.blob((0.1, 0.08, 0.14), tuple(end + Vector((0, 0, -0.13))), m["hair_d"], "x", segs=(8, 6))  # the tuft below
	return _smooth_static(b)


def build_race_beard_barbarian():
	"""A shorter, wild beard with two braids hanging from the chin."""
	m = {"hair": material("barb_beard", "b87a40", 0.9), "hair_d": material("barb_beard_dark", "8a5226", 0.9),
		 "band": material("barb_band", "4a3a30", 0.7)}
	beard = _kaykit_beard("race_beard_barbarian", m["hair"], 1.4, 0.1, 1.05)
	b = Builder("race_beard_barbarian")
	b.parts.append(beard)
	for s in (1, -1):
		end = _braid(b, (0.13 * s, -0.56, 1.14), 0.28, 0.045, (m["hair"], m["hair_d"]), links=4, lean=(0.05 * s, -0.08))
		b.seg(tuple(end + Vector((0, 0, 0.06))), tuple(end + Vector((0, 0, 0.0))), 0.042, 0.042, m["band"], "x", sides=8)
	return _smooth_static(b)


# ---------------------------------------------------------------- repainted KayKit bodies
# Tints only multiply a texture, so a purple robe can't turn saffron. These
# write a copy of a KayKit character .glb with its palette texture repainted
# cell by cell (8 x 4 swatches of vertical gradients); mesh, skin and rig are
# untouched, so KayKit animations, gear and grips still apply.

# ---------------------------------------------------------------- Reedmere (the Long Monsoon): pondkin, the sunken, the sedge coven
# Bolt-ons for KayKit Rig_Medium bodies, in their mesh space (head bone at z 1.24, the head
# roughly a ball of radius 0.55 round (0, 0, 1.62), T-posed hands at x 0.8-0.97, z 1.11).

def _arc(b, center, radii, a0, a1, width, mat, sides=12, lift=0.0, bone="x"):
	"""Segments along part of an ellipse from a0 to a1 degrees (270 is the front, -Y); `lift` bows the middle up."""
	cx, cy, cz = center
	pts = []
	for k in range(sides + 1):
		u = k / sides
		a = math.radians(a0 + (a1 - a0) * u)
		pts.append((cx + radii[0] * math.cos(a), cy + radii[1] * math.sin(a), cz + lift * math.sin(math.pi * u)))
	for p, q in zip(pts, pts[1:]):
		b.seg(p, q, width, width, mat, bone, sides=5)
	return pts


def _on_dome(center, radii, x, y, lift=0.0):
	"""The point on top of an ellipsoid above (x, y), and the surface's normal there."""
	cx, cy, cz = center
	rx, ry, rz = radii
	u, v = (x - cx) / rx, (y - cy) / ry
	w = math.sqrt(max(0.0, 1 - u * u - v * v))
	p = Vector((x, y, cz + rz * w))
	n = Vector((u / rx, v / ry, w / rz)).normalized()
	return p + n * lift, n


POND_SKINS = {
	"pondkin": {"skin": "6e8e3e", "dark": "3e5a22", "spot": "2c4216", "belly": "e2d69c", "belly_d": "b8aa6a", "eye": "e8c030"},
	"mudcaller": {"skin": "4e6838", "dark": "2a3a1c", "spot": "1a2610", "belly": "c4b888", "belly_d": "948858", "eye": "f09a20"},
	"bloatking": {"skin": "8e9646", "dark": "515c26", "spot": "3a4418", "belly": "eedea2", "belly_d": "c2ac6a", "eye": "ff7a1a"},
}


def pond_materials(kind):
	c = POND_SKINS[kind]
	p = f"pond_{kind}"
	return {
		"skin": material(f"{p}_skin", c["skin"], 0.5),
		"dark": material(f"{p}_dark", c["dark"], 0.55),
		"spot": material(f"{p}_spot", c["spot"], 0.55),
		"belly": material(f"{p}_belly", c["belly"], 0.7),
		"belly_d": material(f"{p}_belly_d", c["belly_d"], 0.75),
		"eye": material(f"{p}_eye", c["eye"], 0.2, emit=0.6),
		"pupil": material(f"{p}_pupil", "0e0c08", 0.1),
		"glint": material(f"{p}_glint", "ffffff", 0.1, emit=0.8),
		"mouth": material(f"{p}_mouth", "2e1614", 0.8),
		"shell": material(f"{p}_shell", "efe4cc", 0.5),
		"shell_p": material(f"{p}_shell_pink", "e2a88e", 0.5),
		"reed": material(f"{p}_reed", "b4a452", 0.85),
		"reed_d": material(f"{p}_reed_dark", "6e6a2c", 0.85),
		"cattail": material(f"{p}_cattail", "5a3a1e", 0.95),
		"cord": material(f"{p}_cord", "4a3a22", 0.9),
		"mud": material(f"{p}_mud", "5e4a32", 0.95),
		"clay": material(f"{p}_clay", "d8c89a", 0.9),
		"bone": material(f"{p}_bone", "e6dcc0", 0.6),
		"rust": material(f"{p}_rust", "a0582a", 0.7),
		"rust_d": material(f"{p}_rust_dark", "4e2812", 0.75),
		"pearl": material(f"{p}_pearl", "f4f0e8", 0.2, emit=0.3),
		"wart": material(f"{p}_wart", "6a7430", 0.6),
	}


POND_DOME = ((0, 0.02, 1.58), (0.62, 0.52, 0.32))


def _shell_charm(b, loc, m, size=1.0, pink=False):
	"""A little scallop shell hanging face-out: a fan of ribs on a flat disc."""
	x, y, z = loc
	s = size
	_oblob(b, (0.13 * s, 0.12 * s, 0.03), (x, y, z), (0, 0, 1), (0, -1, 0), m["shell_p"] if pink else m["shell"], "x", segs=(8, 4))
	for k in range(5):
		a = math.radians(-50 + 25 * k)
		b.seg((x, y - 0.016, z - 0.045 * s), (x + 0.07 * s * math.sin(a), y - 0.018, z - 0.045 * s + 0.08 * s * math.cos(a)),
			  0.008 * s, 0.006 * s, m["shell"] if pink else m["shell_p"], "x", sides=3)


def _pond_head(b, m, kind):
	"""A wide, flat frog head sunk straight into the shoulders: big lidded eyes on top, a mouth
	that runs from ear to ear, a pale throat pouch, eardrums and mottling."""
	import random
	rng = random.Random({"pondkin": 211, "mudcaller": 213, "bloatking": 217}[kind])
	king = kind == "bloatking"
	sk = m["skin"]
	(dc, dr) = POND_DOME
	b.blob(tuple(r * 2 for r in dr), dc, sk, "x", segs=(18, 11))                            # the flat skull
	b.blob((1.14, 0.64, 0.42), (0, -0.3, 1.5), sk, "x", segs=(16, 9))                         # the broad, blunt snout
	b.blob((1.1, 0.88, 0.34), (0, -0.12, 1.34), sk, "x", segs=(16, 9))                         # the lower jaw
	b.blob((0.72, 0.56, 0.26), (0, -0.2, 1.24), m["belly"], "x", segs=(14, 8))                # a pale throat under it
	pouch = (0.64, 0.5, 0.4) if king else (0.46, 0.34, 0.26)
	b.blob(pouch, (0, -0.28, 1.18 if not king else 1.12), m["belly_d"], "x", segs=(12, 8))    # the throat pouch
	_arc(b, (0, -0.12, 1.41), (0.57, 0.48), 188, 352, 0.026, m["mouth"], sides=16)            # the mouth, ear to ear
	for s in (1, -1):
		b.blob((0.12, 0.1, 0.07), (0.54 * s, -0.2, 1.41), m["mouth"], "x", segs=(6, 4))           # the corners turn down
		b.blob((0.38, 0.38, 0.32), (0.33 * s, -0.22, 1.84), sk, "x", segs=(12, 8))                # eye bulges
		b.blob((0.3, 0.3, 0.28), (0.35 * s, -0.27, 1.9), m["eye"], "x", segs=(12, 8))
		b.blob((0.2, 0.05, 0.075), (0.37 * s, -0.41, 1.9), m["pupil"], "x", segs=(8, 4))         # a flat, sideways pupil
		b.blob((0.05, 0.03, 0.04), (0.3 * s, -0.4, 1.97), m["glint"], "x", segs=(5, 3))
		b.blob((0.38, 0.34, 0.14), (0.34 * s, -0.2, 2.0), m["dark"], "x", rot=(-14, 10 * s, 0), segs=(10, 6))  # heavy lids
		_oblob(b, (0.22, 0.24, 0.04), (0.6 * s, 0.06, 1.6), (0, 0, 1), (s, 0.1, 0), m["dark"], "x", segs=(10, 4))  # eardrums
		b.blob((0.05, 0.04, 0.04), (0.09 * s, -0.6, 1.6), m["pupil"], "x", segs=(5, 3))            # nostrils
		b.blob((0.2, 0.44, 0.16), (0.48 * s, -0.02, 1.52), m["dark"], "x", segs=(8, 5))            # a dark stripe behind the eye
	# mottling over the crown and snout
	for k in range(14 if not king else 10):
		x, y = rng.uniform(-0.48, 0.48), rng.uniform(-0.4, 0.4)
		if abs(abs(x) - 0.34) < 0.17 and -0.4 < y < -0.04:
			continue   # not on the eyes
		p, n = _on_dome(dc, dr, x, y, 0.005)
		w = rng.uniform(0.08, 0.16)
		_oblob(b, (w, w * rng.uniform(1.0, 1.5), 0.04), tuple(p), (rng.uniform(-1, 1), 1, 0), tuple(n), m["spot"], "x", segs=(8, 4))
	if king:   # warts all over, and heavy jowls
		for k in range(26):
			x, y = rng.uniform(-0.55, 0.55), rng.uniform(-0.46, 0.46)
			if abs(abs(x) - 0.34) < 0.18 and -0.42 < y < -0.02:
				continue
			p, n = _on_dome(dc, dr, x, y, 0.0)
			r = rng.uniform(0.04, 0.08)
			b.blob((r, r, r * 0.8), tuple(p), m["wart"], "x", segs=(6, 4))
		for s in (1, -1):
			b.blob((0.36, 0.5, 0.4), (0.4 * s, -0.1, 1.26), sk, "x", segs=(10, 7))
	return rng


def build_pondkin_head():
	m = pond_materials("pondkin")
	b = Builder("pondkin_head")
	_pond_head(b, m, "pondkin")
	# a reed cord round the crown with a shell at the brow and two tucked-in reeds
	_arc(b, (0, 0.14, 1.83), (0.34, 0.3), 0, 360, 0.03, m["cord"], sides=18)
	_shell_charm(b, (0, -0.16, 1.92), m, 1.1)
	for s in (1, -1):
		b.seg((0.28 * s, 0.24, 1.84), (0.44 * s, 0.56, 2.24), 0.02, 0.008, m["reed"], "x", sides=4)
	b.seg((0.2, 0.3, 1.84), (0.24, 0.62, 2.1), 0.03, 0.03, m["cattail"], "x", sides=5)
	return b.build_static()


def build_pondkin_mudcaller_head():
	"""Clay-daubed, with a headdress of reeds and cattails fanning up behind and fish-bone beads."""
	m = pond_materials("mudcaller")
	b = Builder("pondkin_mudcaller_head")
	_pond_head(b, m, "mudcaller")
	(dc, dr) = POND_DOME
	for x0, x1, y in ((-0.2, 0.2, -0.36), (-0.24, 0.24, -0.16), (-0.18, 0.18, 0.08)):   # clay bars across the crown
		pts = [_on_dome(dc, dr, x0 + (x1 - x0) * k / 5, y, 0.01)[0] for k in range(6)]
		for p, q in zip(pts, pts[1:]):
			b.seg(tuple(p), tuple(q), 0.035, 0.035, m["clay"], "x", sides=5)
	for s in (1, -1):
		for k in range(3):   # clay drips down the cheeks
			x = (0.4 + 0.06 * k) * s
			b.seg((x, -0.36 + 0.06 * k, 1.56), (x * 1.02, -0.4 + 0.06 * k, 1.36), 0.028, 0.02, m["clay"], "x", sides=4)
	_arc(b, (0, 0.18, 1.8), (0.4, 0.3), 0, 360, 0.045, m["cord"], sides=18)
	for k in range(9):   # the fan of reeds
		j = k - 4
		base = Vector((0.08 * j, 0.3 - 0.01 * abs(j), 1.84))
		tip = base + Vector((0.16 * j, 0.24 + 0.03 * abs(j), 0.9 - 0.07 * abs(j)))
		b.seg(tuple(base), tuple(tip), 0.028, 0.008, (m["reed"], m["reed_d"])[k % 2], "x", sides=4)
		if k % 2 == 0:   # cattail heads on every other one
			d = (tip - base).normalized()
			b.seg(tuple(base + (tip - base) * 0.62), tuple(base + (tip - base) * 0.84), 0.055, 0.05, m["cattail"], "x", sides=6)
		else:
			_oblob(b, (0.06, 0.32, 0.02), tuple(base + (tip - base) * 0.5 + Vector((0.05 * (1 if j > 0 else -1), 0, 0))),
				   tuple(tip - base), (1, 0, 0), m["reed_d"], "x", segs=(6, 3))   # a blade leaf
	for s in (1, -1):   # strings of fish-bone beads down the sides
		for k in range(4):
			b.blob((0.06, 0.06, 0.07), (0.44 * s, 0.26, 1.74 - 0.1 * k), m["bone"] if k % 2 else m["clay"], "x", segs=(6, 4))
		b.seg((0.44 * s, 0.26, 1.46), (0.46 * s, 0.24, 1.36), 0.03, 0.0, m["bone"], "x", sides=4)
	return b.build_static()


def build_pondkin_bloatking_head():
	"""Warty and jowled, a crown of rusted iron and river shells perched on the back of the head."""
	m = pond_materials("bloatking")
	b = Builder("pondkin_bloatking_head")
	_pond_head(b, m, "bloatking")
	c = (0, 0.16, 1.86)
	_arc(b, c, (0.36, 0.3), 0, 360, 0.06, m["rust_d"], sides=20)
	_arc(b, (c[0], c[1], c[2] + 0.08), (0.36, 0.3), 0, 360, 0.045, m["rust"], sides=20)
	for k in range(9):
		a = math.radians(-90 + 40 * k)
		p = Vector((0.36 * math.cos(a), c[1] + 0.3 * math.sin(a), c[2] + 0.06))
		h = 0.5 if k == 0 else (0.36 if k % 2 == 0 else 0.24)
		lean = Vector((0.08 * math.cos(a), 0.08 * math.sin(a), h))
		b.seg(tuple(p), tuple(p + lean), 0.06, 0.012, (m["rust"], m["rust_d"])[k % 2], "x", sides=5)   # bent iron spikes
		if k % 2 == 1:
			_shell_charm(b, tuple(p + Vector((0.03 * math.cos(a), 0.03 * math.sin(a), 0.04))), m, 0.9, pink=k % 4 == 1)
	b.blob((0.12, 0.1, 0.12), (0, c[1] - 0.3, c[2] + 0.16), m["pearl"], "x", segs=(10, 7))          # a great pearl at the front
	b.blob((0.18, 0.08, 0.16), (0, c[1] - 0.26, c[2] + 0.14), m["rust_d"], "x", segs=(8, 5))
	for s in (1, -1):   # a string of shells and pearls hanging off each side
		for k in range(3):
			b.blob((0.07, 0.07, 0.07), (0.34 * s, c[1] + 0.02, c[2] - 0.06 - 0.1 * k), m["pearl"] if k % 2 else m["shell_p"], "x", segs=(6, 4))
	return b.build_static()


def _pond_chest(b, m, kind):
	"""On the chest bone: mottling down the back, a necklace, and the kind's gear."""
	import random
	rng = random.Random(223)
	for k in range(10):   # spots down the back and shoulders
		x, z = rng.uniform(-0.34, 0.34), rng.uniform(0.9, 1.3)
		w = rng.uniform(0.09, 0.15)
		_oblob(b, (w, w * 1.3, 0.04), (x, 0.35 + 0.02 * (1 - abs(x) / 0.4), z), (0, 0, 1), (x * 0.8, 1, 0), m["spot"], "x", segs=(8, 4))
	# the necklace: a reed cord round the neck with shells, the king's heavier with pearls
	pts = _arc(b, (0, 0.0, 1.3), (0.4, 0.4), 180, 360, 0.022, m["cord"], sides=14, lift=0.0)
	for k, p in enumerate(pts):
		if 2 <= k <= 12 and k % 2 == 0:
			x, y, z = p
			drop = 0.08 + 0.05 * math.sin(math.pi * (k - 2) / 10)
			b.seg((x, y, z), (x, y - 0.01, z - drop), 0.01, 0.01, m["cord"], "x", sides=3)
			_shell_charm(b, (x, y - 0.03, z - drop - 0.04), m, 0.95 if kind != "bloatking" else 1.2, pink=k % 4 == 0)
	if kind == "pondkin":   # a pauldron of woven reed on the left shoulder, tied on
		_oblob(b, (0.44, 0.5, 0.12), (0.42, 0.0, 1.3), (0, 1, 0), (0.6, 0, 1), m["reed"], "x", segs=(10, 6))
		for k in range(4):
			_oblob(b, (0.46, 0.05, 0.13), (0.42, -0.18 + 0.12 * k, 1.31), (1, 0, -0.6), (0.6, 0, 1), m["reed_d"], "x", segs=(8, 3))
		b.seg((0.2, -0.3, 1.2), (0.5, -0.2, 1.36), 0.02, 0.02, m["cord"], "x", sides=4)
		b.seg((0.2, 0.3, 1.2), (0.5, 0.2, 1.36), 0.02, 0.02, m["cord"], "x", sides=4)
	elif kind == "mudcaller":   # a fish skull on the breast, and clay handprints
		b.blob((0.22, 0.14, 0.14), (0, -0.44, 1.02), m["bone"], "x", segs=(10, 6))
		b.seg((0, -0.46, 1.02), (0, -0.58, 0.98), 0.07, 0.03, m["bone"], "x", sides=6)
		for s in (1, -1):
			b.blob((0.05, 0.03, 0.05), (0.05 * s, -0.51, 1.05), m["pupil"], "x", segs=(5, 3))
		for s, z in ((1, 1.12), (-1, 0.96)):
			_oblob(b, (0.16, 0.18, 0.02), (0.2 * s, -0.37, z), (0, 0, 1), (0.3 * s, -1, 0), m["clay"], "x", segs=(8, 4))
			for f in range(4):
				a = math.radians(-40 + 27 * f)
				b.seg((0.2 * s, -0.375, z + 0.06), (0.2 * s + 0.09 * math.sin(a), -0.375, z + 0.06 + 0.1 * math.cos(a)), 0.018, 0.014,
					  m["clay"], "x", sides=3)
	else:   # a mantle of woven reeds and a rusted iron gorget
		_shell(b, (1.1, 1.0, 0.7), (0, 0.04, 1.24), m["reed"], lambda d: d.z > 0.0 and not (d.y < -0.5 and abs(d.x) < 0.55))
		for k in range(11):
			a = math.radians(-10 + k * 20)
			p = (0.55 * math.cos(a), 0.04 + 0.5 * math.sin(a), 1.24)
			_tuft(b, p, (math.cos(a) * 0.2, math.sin(a) * 0.2, -1), 0.3, 4, 0.2, [m["reed"], m["reed_d"]], 400 + k, width=0.03)
		_arc(b, (0, -0.02, 1.34), (0.38, 0.36), 200, 340, 0.05, m["rust"], sides=10)


def build_pondkin_chest():
	b = Builder("pondkin_chest")
	_pond_chest(b, pond_materials("pondkin"), "pondkin")
	return b.build_static()


def build_pondkin_mudcaller_chest():
	b = Builder("pondkin_mudcaller_chest")
	_pond_chest(b, pond_materials("mudcaller"), "mudcaller")
	return b.build_static()


def build_pondkin_bloatking_chest():
	b = Builder("pondkin_bloatking_chest")
	_pond_chest(b, pond_materials("bloatking"), "bloatking")
	return b.build_static()


def _pond_belly(name, kind):
	"""A round pale belly pushed out in front (spine bone): the pondkin are squat and potbellied."""
	m = pond_materials(kind)
	b = Builder(name)
	if kind == "bloatking":
		b.blob((1.08, 0.86, 0.92), (0, -0.22, 0.8), m["skin"], "x", segs=(16, 11))
		b.blob((0.92, 0.5, 0.8), (0, -0.4, 0.78), m["belly"], "x", segs=(16, 10))
		b.blob((0.2, 0.06, 0.14), (0, -0.66, 0.74), m["belly_d"], "x", segs=(8, 4))              # the navel
		_arc(b, (0, -0.2, 0.56), (0.52, 0.46), 0, 360, 0.05, m["cord"], sides=20)                  # a reed belt under it
	else:
		b.blob((0.84, 0.62, 0.7), (0, -0.14, 0.8), m["skin"], "x", segs=(14, 10))
		b.blob((0.7, 0.36, 0.6), (0, -0.28, 0.8), m["belly"], "x", segs=(14, 9))
	return b.build_static()


def _pond_skirt(name, kind):
	"""A skirt of reed strips on a cord round the hips, open over the stride."""
	m = pond_materials(kind)
	b = Builder(name)
	rx, ry = (0.52, 0.46) if kind == "bloatking" else (0.44, 0.38)
	_arc(b, (0, 0, 0.62), (rx, ry), 0, 360, 0.04, m["cord"], sides=20)
	for k in range(22):
		a = 2 * math.pi * k / 22
		x, y = rx * math.cos(a), ry * math.sin(a)
		if abs(x) < 0.16 and y < 0:
			continue
		ln = 0.3 + 0.08 * ((k * 7) % 3)
		top = Vector((x, y, 0.64))
		out = Vector((x, y, 0)).normalized()
		b.seg(tuple(top), tuple(top + out * 0.1 + Vector((0, 0, -ln))), 0.035, 0.012, (m["reed"], m["reed_d"], m["reed"])[k % 3], "x", sides=4)
	if kind == "mudcaller":
		for k in range(3):
			b.blob((0.08, 0.06, 0.1), (0.3 - 0.06 * k, -0.36, 0.52 - 0.12 * k), m["bone"], "x", segs=(6, 4))
	return b.build_static()


def _pond_hand(name, s, kind):
	"""A webbed hand round the KayKit fist (s = side): three long fingers with round pads, webbing between."""
	m = pond_materials(kind)
	b = Builder(name)
	k = 1.2 if kind == "bloatking" else 1.0
	palm = Vector((0.86 * s, -0.02, 1.08))
	b.blob((0.28 * k, 0.3 * k, 0.22 * k), tuple(palm), m["skin"], "x", segs=(10, 7))
	tips = []
	for j, a in enumerate((-38, 0, 38)):
		d = Vector((math.cos(math.radians(a)) * s, math.sin(math.radians(a)) * -1, -0.25)).normalized()
		tip = palm + d * 0.3 * k
		b.seg(tuple(palm + d * 0.08), tuple(tip), 0.045 * k, 0.035 * k, m["skin"], "x", sides=6)
		b.blob((0.09 * k, 0.09 * k, 0.07 * k), tuple(tip), m["belly_d"], "x", segs=(7, 5))   # toe pads
		tips.append(tip)
	for p, q in zip(tips, tips[1:]):   # webbing
		_slab(b, [tuple(palm), tuple(palm + (p - palm) * 0.8), tuple(palm + (q - palm) * 0.8)], 0.02, m["dark"])
	thumb = palm + Vector((0.02 * s, -0.16, 0.06)) * k
	b.seg(tuple(palm), tuple(thumb), 0.04 * k, 0.035 * k, m["skin"], "x", sides=5)
	b.blob((0.08 * k, 0.08 * k, 0.07 * k), tuple(thumb), m["belly_d"], "x", segs=(6, 4))
	return b.build_static()


def _pond_foot(name, s, kind):
	"""A broad webbed foot over the KayKit boot (s = side), three long toes splayed forward."""
	m = pond_materials(kind)
	b = Builder(name)
	k = 1.15 if kind == "bloatking" else 1.0
	x = 0.17 * s
	b.blob((0.26 * k, 0.34 * k, 0.16), (x, -0.08, 0.08), m["skin"], "x", segs=(10, 6))
	root = Vector((x, -0.18, 0.04))
	tips = []
	for dx in (-0.13, 0.0, 0.13):
		tip = root + Vector((dx * s * k, -0.26 * k, -0.02))
		b.seg(tuple(root), tuple(tip), 0.045, 0.035, m["skin"], "x", sides=5)
		b.blob((0.1, 0.1, 0.06), tuple(tip), m["belly_d"], "x", segs=(7, 4))
		tips.append(tip)
	for p, q in zip(tips, tips[1:]):
		_slab(b, [tuple(root + Vector((0, 0.02, 0))), tuple(root + (p - root) * 0.85), tuple(root + (q - root) * 0.85)], 0.02, m["dark"])
	return b.build_static()


# --- the sunken of Veyamar: drowned villagers and their headwoman

def sunken_materials():
	return {
		"kelp": material("sunken_kelp", "3a5030", 0.8),
		"weed": material("sunken_weed", "7e7a3a", 0.85),     # dead, yellowed weed
		"slime": material("sunken_slime", "30423a", 0.5),
		"barnacle": material("sunken_barnacle", "c4c0ac", 0.7),
		"hole": material("sunken_hole", "36322c", 0.8),
		"lily": material("sunken_lily", "4e7a36", 0.6),
		"lily_d": material("sunken_lily_dark", "2a4a20", 0.6),
		"rag": material("sunken_rag", "7a745a", 0.95),
		"rag_d": material("sunken_rag_dark", "4a4636", 0.95),
		"reed": material("sunken_reed", "a89a58", 0.85),
		"snail": material("sunken_snail", "8a6a4a", 0.5),
		"lotus": material("sunken_lotus", "b8948a", 0.9),       # dead lotus, faded pink-brown
		"lotus_d": material("sunken_lotus_dark", "6a4c44", 0.9),
		"lotus_c": material("sunken_lotus_center", "9a8a4a", 0.8),
		"glow": material("sunken_glow", "7affe8", 0.2, emit=3.5),
		"gold": material("sunken_gold", "a8904a", 0.4),
		"bead": material("sunken_bead", "3a8a7a", 0.4),
		"shawl": material("sunken_shawl", "6a8a84", 0.9),
		"shawl_d": material("sunken_shawl_dark", "3a524e", 0.9),
		"pearl": material("sunken_pearl", "e8f0ec", 0.2, emit=0.4),
	}


def _lily_pad(b, loc, normal, r, m):
	n = Vector(normal).normalized()
	_oblob(b, (r * 2, r * 2, 0.025), tuple(loc), n.orthogonal(), tuple(n), m["lily"], "x", segs=(12, 4))
	_oblob(b, (r * 1.6, r * 1.6, 0.03), tuple(Vector(loc) + n * 0.004), n.orthogonal(), tuple(n), m["lily_d"], "x", segs=(10, 3))


def build_sunken_head():
	"""Weed matted into the hair and hanging round the face, a lily pad stuck on top, a snail on the temple."""
	m = sunken_materials()
	b = Builder("sunken_head")
	b.blob((0.9, 0.9, 0.2), (0.02, 0.06, 2.08), m["slime"], "x", rot=(0, 6, 0), segs=(12, 5))
	for x, y, z, ln in ((0.5, -0.2, 1.9, 0.6), (0.54, 0.08, 1.9, 0.72), (0.4, 0.34, 1.94, 0.66), (0.14, 0.5, 1.96, 0.74),
						(-0.14, 0.5, 1.96, 0.62), (-0.42, 0.32, 1.94, 0.7), (-0.54, 0.04, 1.9, 0.76), (-0.5, -0.24, 1.88, 0.5),
						(0.3, -0.44, 1.98, 0.36), (-0.22, -0.46, 2.0, 0.3)):
		_kelp(b, (x, y, z), ln, m["kelp"] if ln > 0.55 else m["weed"], lean=(x * 0.2, 0.25 if y > 0.2 else -0.05), width=0.055)
	_lily_pad(b, (-0.12, 0.08, 2.19), (-0.2, 0.1, 1), 0.2, m)
	b.blob((0.12, 0.14, 0.12), (0.52, -0.1, 1.72), m["snail"], "x", segs=(8, 6))
	b.blob((0.07, 0.12, 0.05), (0.54, -0.2, 1.66), m["rag"], "x", segs=(6, 4))
	for loc, nrm, sz in (((0.36, -0.3, 1.98), (0.6, -0.5, 0.6), 0.9), ((-0.44, 0.1, 1.96), (-0.7, 0.2, 0.6), 0.8)):
		_barnacle(b, loc, nrm, m, sz)
	return b.build_static()


def build_sunken_chest():
	"""Rotted rags over the shoulders, weed and reed caught round them, barnacles crusting the tunic."""
	m = sunken_materials()
	b = Builder("sunken_chest")
	for s in (1, -1):
		b.blob((0.36, 0.56, 0.1), (0.26 * s, 0.0, 1.26), m["slime"], "x", rot=(0, 18 * s, 0), segs=(10, 5))
		for y, ln in ((-0.24, 0.5), (0.02, 0.36), (0.24, 0.58)):
			_kelp(b, (0.36 * s, y, 1.24), ln, m["kelp"] if ln > 0.4 else m["weed"], lean=(0.1 * s, 0.1 * (1 if y > 0 else -1)), width=0.05)
		# torn rag flaps hanging off the shoulders
		_slab(b, [(0.2 * s, -0.34, 1.24), (0.44 * s, -0.3, 1.2), (0.46 * s, -0.34, 0.86), (0.36 * s, -0.37, 0.8), (0.24 * s, -0.38, 0.9)],
			  0.03, m["rag_d"] if s > 0 else m["rag"])
	b.seg((-0.3, -0.36, 1.18), (0.12, -0.4, 0.86), 0.018, 0.012, m["reed"], "x", sides=4)
	for loc, nrm, sz in (((0.16, -0.36, 1.08), (0.2, -1, 0.2), 1.1), ((-0.14, -0.38, 0.9), (0, -1, 0), 0.8),
						 ((0.26, 0.3, 1.1), (0.4, 1, 0.3), 0.9), ((-0.2, 0.33, 0.96), (-0.2, 1, 0), 1.0),
						 ((0.05, -0.39, 0.74), (0, -1, -0.2), 0.7)):
		_barnacle(b, loc, nrm, m, sz)
	return b.build_static()


def build_sunken_hips():
	"""A belt of rotted rope with rag strips and weed hanging off it, open in front."""
	m = sunken_materials()
	b = Builder("sunken_hips")
	b.seg((0, 0, 0.6), (0, 0, 0.68), 0.43, 0.41, m["slime"], "x", sides=12)
	for k in range(11):
		a = math.radians(k * 33 + 8)
		x, y = 0.43 * math.cos(a), 0.38 * math.sin(a)
		if abs(x) < 0.14 and y < 0:
			continue
		if k % 3 == 0:
			w = Vector((-math.sin(a), math.cos(a), 0)) * 0.07
			top = Vector((x, y, 0.62))
			tip = top + Vector((x, y, 0)) * 0.12 + Vector((0, 0, -0.34))
			_slab(b, [tuple(top - w), tuple(top + w), tuple(tip + w * 0.4), tuple(tip - w * 0.6)], 0.025, m["rag"])
		else:
			_kelp(b, (x, y, 0.62), 0.28 + 0.1 * (k % 3), m["kelp"] if k % 2 else m["weed"], lean=(x * 0.15, y * 0.15), width=0.045, parts=2)
	return b.build_static()


def _lotus(b, loc, up, m, size=1.0, wilt=0.0):
	"""A dead lotus: a seed-head center and a cup of curling petals, drooping by `wilt`."""
	c = Vector(loc)
	u = Vector(up).normalized()
	side = u.orthogonal().normalized()
	fwd = u.cross(side)
	b.seg(tuple(c), tuple(c + u * 0.05 * size), 0.05 * size, 0.06 * size, m["lotus_c"], "x", sides=8)
	for k in range(7):
		a = 2 * math.pi * k / 7
		out = side * math.cos(a) + fwd * math.sin(a)
		droop = wilt * (0.6 if k % 3 == 0 else 0.2)
		d = (out * (0.6 + droop) + u * (0.8 - 1.4 * droop)).normalized()
		_oblob(b, (0.08 * size, 0.16 * size, 0.025), tuple(c + d * 0.08 * size), d, tuple(out * 0.3 + u), (m["lotus"], m["lotus_d"])[k % 2], "x", segs=(6, 4))


def build_sunken_headwoman_crown():
	"""A crown of dead lotus flowers on a woven reed band, weed hanging from it, and a pale glow in the eyes."""
	m = sunken_materials()
	b = Builder("sunken_headwoman_crown")
	c = (0, 0.02, 1.96)
	_arc(b, c, (0.5, 0.48), 0, 360, 0.045, m["reed"], sides=22)
	_arc(b, (c[0], c[1], c[2] - 0.06), (0.51, 0.49), 0, 360, 0.03, m["gold"], sides=22)
	for k in range(9):
		a = math.radians(-90 + 40 * k)
		p = Vector((0.5 * math.cos(a), c[1] + 0.48 * math.sin(a), c[2] + 0.03))
		out = Vector((math.cos(a), math.sin(a), 0))
		big = 1.35 if k == 0 else (1.0 if k in (1, 8) else 0.85)
		_lotus(b, p + out * 0.02 + Vector((0, 0, 0.04)), out * 0.35 + Vector((0, 0, 1)), m, big * 1.35, wilt=0.3 + 0.4 * (k % 3 == 1))
	for x, y, ln in ((0.52, 0.0, 0.7), (0.44, 0.28, 0.8), (0.18, 0.46, 0.86), (-0.18, 0.46, 0.8), (-0.44, 0.28, 0.76), (-0.52, 0.0, 0.66)):
		_kelp(b, (x, y, 1.92), ln, m["kelp"] if ln > 0.75 else m["weed"], lean=(x * 0.15, 0.2), width=0.05)
	for s in (1, -1):   # a cold glow in the eyes
		b.blob((0.12, 0.04, 0.14), (0.19 * s, -0.535, 1.57), m["glow"], "x", segs=(8, 5))
	return b.build_static()


def build_sunken_headwoman_shawl():
	"""A tattered ceremonial shawl over the shoulders, fringe hanging in strips, strings of beads and a
	pearl pendant; weed tangled in it."""
	import random
	rng = random.Random(233)
	m = sunken_materials()
	b = Builder("sunken_headwoman_shawl")
	_shell(b, (1.12, 1.02, 0.62), (0, 0.04, 1.24), m["shawl"], lambda d: d.z > -0.05 and not (d.y < -0.45 and abs(d.x) < 0.5))
	_arc(b, (0, 0.04, 1.22), (0.57, 0.52), -55, 235, 0.035, m["gold"], sides=22)
	for k in range(20):
		a = 2 * math.pi * (k + 0.5) / 20
		x, y = 0.56 * math.cos(a), 0.04 + 0.5 * math.sin(a)
		if abs(x) < 0.24 and y < 0:
			continue
		out = Vector((math.cos(a), math.sin(a), 0))
		w = Vector((-out.y, out.x, 0)) * 0.07
		top = Vector((x, y, 1.2))
		ln = rng.uniform(0.2, 0.5) * (1.4 if y > 0.2 else 1.0)
		tip = top + out * 0.06 + Vector((0, 0, -ln))
		_slab(b, [tuple(top - w), tuple(top + w), tuple(tip + w * 0.3), tuple(tip - w * 0.5)], 0.022, (m["shawl"], m["shawl_d"])[k % 2])
	for s in (1, -1):   # bead strings looping down the front to the pendant
		pts = [(0.3 * s, -0.36, 1.2), (0.22 * s, -0.42, 1.06), (0.1 * s, -0.44, 0.96), (0.0, -0.45, 0.92)]
		for p, q in zip(pts, pts[1:]):
			for k in range(3):
				u = k / 3
				b.blob((0.05, 0.05, 0.05), tuple(Vector(p) + (Vector(q) - Vector(p)) * u), m["bead"] if k % 2 else m["gold"], "x", segs=(6, 4))
	b.blob((0.14, 0.08, 0.18), (0, -0.46, 0.86), m["gold"], "x", segs=(8, 6))
	b.blob((0.1, 0.06, 0.1), (0, -0.5, 0.86), m["pearl"], "x", segs=(8, 5))
	for x, y, ln in ((0.4, -0.2, 0.4), (-0.36, -0.26, 0.5), (0.3, 0.4, 0.6)):
		_kelp(b, (x, y, 1.2), ln, m["kelp"], lean=(0, 0.1), width=0.045)
	return b.build_static()


# --- the sedge coven: swamp witches over the Mage's own head, and their mother

def sedge_materials(mother=False):
	p = "marrowroot" if mother else "sedge"
	return {
		"skin": material(f"{p}_skin", "a4ac78" if not mother else "8e9a74", 0.8),
		"skin_d": material(f"{p}_skin_dark", "6e7a48" if not mother else "5a6648", 0.8),
		"wart": material(f"{p}_wart", "7a7a42", 0.7),
		"hair": material(f"{p}_hair", "6a7058" if not mother else "c8ccc0", 0.95),
		"hair_d": material(f"{p}_hair_dark", "3e4432" if not mother else "8e948a", 0.95),
		"reed": material(f"{p}_reed", "a8985a", 0.85),
		"reed_d": material(f"{p}_reed_dark", "6a5e30", 0.85),
		"reed_l": material(f"{p}_reed_light", "c8b878", 0.85),
		"cattail": material(f"{p}_cattail", "5a3a1e", 0.95),
		"moss": material(f"{p}_moss", "5a6e2e", 0.95),
		"moss_b": material(f"{p}_moss_b", "7c8a3a", 0.95),
		"root": material(f"{p}_root", "5a4430", 0.9),
		"root_d": material(f"{p}_root_dark", "3a2a1c", 0.9),
		"bone": material(f"{p}_bone", "e2d8bc", 0.6),
		"cord": material(f"{p}_cord", "3e2e1e", 0.9),
		"eye": material(f"{p}_eye", "c8ff5a", 0.2, emit=2.5),
		"dark": material(f"{p}_dark", "1a140e", 0.8),
	}


def _hag_face(b, m, mother):
	"""A long hooked nose, warts, a jutting chin and stringy hair, over the Mage's own face."""
	sk = m["skin"]
	k = 1.15 if mother else 1.0
	nose = [(0, -0.5, 1.6), (0, -0.66, 1.56), (0, -0.8 * k, 1.47), (0, -0.84 * k, 1.36)]
	radii = (0.085, 0.075, 0.06, 0.045, 0.02)
	for j, (p, q) in enumerate(zip(nose, nose[1:])):
		b.seg(p, q, radii[j], radii[j + 1], sk, "x", sides=8)
	b.blob((0.1, 0.1, 0.1), nose[-1], sk, "x", segs=(7, 5))
	b.blob((0.07, 0.06, 0.06), (0.05, -0.74 * k, 1.53), m["wart"], "x", segs=(6, 4))            # warts on the nose
	b.blob((0.05, 0.05, 0.05), (-0.04, -0.62, 1.6), m["wart"], "x", segs=(5, 3))
	b.blob((0.08, 0.06, 0.07), (0.3, -0.46, 1.4), m["wart"], "x", segs=(6, 4))                   # and the cheek
	b.seg((0.31, -0.49, 1.44), (0.34, -0.54, 1.5), 0.008, 0.004, m["hair_d"], "x", sides=3)       # a hair out of it
	b.seg((0, -0.44, 1.2), (0, -0.56 * k, 1.1), 0.1, 0.04, sk, "x", sides=8)                       # the jutting chin
	b.blob((0.06, 0.05, 0.05), (0.03, -0.55 * k, 1.12), m["wart"], "x", segs=(5, 3))
	for s in (1, -1):
		b.blob((0.2, 0.08, 0.06), (0.18 * s, -0.5, 1.74), m["skin_d"], "x", rot=(0, 16 * s, 0), segs=(8, 4))  # a scowling brow
		b.blob((0.07, 0.03, 0.07), (0.19 * s, -0.53, 1.6), m["eye"], "x", segs=(6, 4))            # a sickly green gleam
	# stringy hair from under the hat brim (or the crown), with reeds tangled in
	strands = ((0.5, -0.22, 1.9, 0.62), (0.56, 0.02, 1.9, 0.84), (0.46, 0.3, 1.92, 0.92), (0.2, 0.48, 1.94, 1.0),
			   (-0.06, 0.5, 1.94, 0.96), (-0.3, 0.42, 1.92, 0.9), (-0.52, 0.16, 1.9, 0.86), (-0.54, -0.16, 1.9, 0.66),
			   (0.36, -0.38, 1.94, 0.44), (-0.4, -0.36, 1.94, 0.5))
	for j, (x, y, z, ln) in enumerate(strands):
		ln *= 1.2 if mother else 1.0
		_kelp(b, (x, y, z), ln, m["hair"] if j % 3 else m["hair_d"], lean=(x * 0.25, 0.25 if y > 0.1 else -0.02), width=0.05)
	for x, y in ((0.52, 0.1), (-0.4, 0.34), (0.3, 0.42)):
		b.seg((x, y, 1.9), (x * 1.2, y * 1.1, 1.3), 0.018, 0.01, m["reed_l"], "x", sides=4)


def build_sedge_sister_head():
	"""The hag's face and hair under a crooked, broad-brimmed hat of woven reeds with a cattail in the band."""
	m = sedge_materials()
	b = Builder("sedge_sister_head")
	_hag_face(b, m, False)
	brim_z = 2.0
	_oblob(b, (1.56, 1.46, 0.06), (0, 0.04, brim_z), (0, 1, 0), (0.08, 0.04, 1), m["reed"], "x", segs=(20, 5))
	for k in range(14):   # a ragged edge of reed ends
		a = 2 * math.pi * k / 14
		p = Vector((0.74 * math.cos(a), 0.04 + 0.69 * math.sin(a), brim_z - 0.08 * 0.74 * math.cos(a) - 0.04 * 0.69 * math.sin(a)))
		d = Vector((math.cos(a), math.sin(a), -0.15))
		b.seg(tuple(p), tuple(p + d * 0.12), 0.03, 0.006, m["reed_d"] if k % 2 else m["reed_l"], "x", sides=3)
	cone = [(0, 0.06, brim_z), (0, 0.1, 2.36), (0.06, 0.18, 2.66), (0.22, 0.3, 2.86), (0.4, 0.34, 2.84), (0.5, 0.3, 2.72)]
	radii = (0.44, 0.3, 0.18, 0.09, 0.05, 0.02)
	for j, (p, q) in enumerate(zip(cone, cone[1:])):
		b.seg(p, q, radii[j], radii[j + 1], m["reed"] if j % 2 == 0 else m["reed_d"], "x", sides=12)
		b.blob((radii[j] * 2.02, radii[j] * 2.02, 0.06), p, m["reed_d"] if j % 2 == 0 else m["reed_l"], "x", segs=(12, 3))  # woven bands
	_arc(b, (0, 0.06, brim_z + 0.06), (0.43, 0.43), 0, 360, 0.04, m["cord"], sides=18)
	b.seg((0.3, -0.26, 2.06), (0.52, -0.1, 2.56), 0.02, 0.012, m["reed_d"], "x", sides=4)
	b.seg((0.46, -0.14, 2.42), (0.5, -0.11, 2.6), 0.045, 0.045, m["cattail"], "x", sides=6)
	for x, y, z in ((-0.3, 0.3, 2.1), (-0.36, -0.1, 2.08)):
		b.seg((x, y, z), (x * 1.5, y * 1.5 + 0.05, z + 0.3), 0.014, 0.004, m["reed_l"], "x", sides=3)
	return b.build_static()


def build_mother_marrowroot_head():
	"""The coven mother: a longer nose, white hair to the waist, and a crown of gnarled roots branching up
	like antlers, hung with little bones."""
	m = sedge_materials(True)
	b = Builder("mother_marrowroot_head")
	_hag_face(b, m, True)
	_arc(b, (0, 0.02, 1.96), (0.5, 0.48), 0, 360, 0.06, m["root_d"], sides=20)
	for k in range(8):
		a = math.radians(-90 + 45 * k)
		p = (0.5 * math.cos(a), 0.02 + 0.48 * math.sin(a), 1.98)
		b.blob((0.16, 0.16, 0.1), p, m["moss"] if k % 2 else m["moss_b"], "x", segs=(7, 4))
	for s in (1, -1):
		beam = [(0.3 * s, 0.1, 2.0), (0.44 * s, 0.14, 2.3), (0.58 * s, 0.08, 2.6), (0.62 * s, -0.08, 2.84), (0.56 * s, -0.16, 3.0)]
		for j, (p, q) in enumerate(zip(beam, beam[1:])):
			b.seg(p, q, 0.075 - 0.014 * j, 0.06 - 0.014 * j, m["root"], "x", sides=6)
		for base, tip in (((0.44 * s, 0.14, 2.3), (0.7 * s, 0.26, 2.46)), ((0.58 * s, 0.08, 2.6), (0.44 * s, -0.12, 2.76)),
						  ((0.6 * s, 0.02, 2.72), (0.84 * s, 0.0, 2.9)), ((0.3 * s, 0.1, 2.0), (0.16 * s, 0.28, 2.3))):
			b.seg(base, tip, 0.04, 0.01, m["root_d"], "x", sides=5)
		for loc in ((0.7 * s, 0.26, 2.44), (0.84 * s, 0.0, 2.88)):   # bones dangling off the tines
			b.seg(loc, (loc[0], loc[1], loc[2] - 0.16), 0.008, 0.008, m["cord"], "x", sides=3)
			b.seg((loc[0], loc[1], loc[2] - 0.16), (loc[0], loc[1], loc[2] - 0.28), 0.025, 0.02, m["bone"], "x", sides=5)
		_kelp(b, (0.5 * s, 0.1, 2.5), 0.3, m["moss_b"], width=0.03, parts=2)
	b.blob((0.18, 0.12, 0.16), (0, -0.46, 2.06), m["bone"], "x", segs=(8, 6))    # a bird skull at the brow
	b.seg((0, -0.5, 2.04), (0, -0.66, 1.98), 0.04, 0.005, m["bone"], "x", sides=5)
	return b.build_static()


def _sedge_chest(b, m, mother):
	"""A mossy shawl over the shoulders with charms of bone and reed; the mother's hunched back and bone necklace."""
	import random
	rng = random.Random(241 if mother else 239)
	_shell(b, (1.06, 0.98, 0.56), (0, 0.04, 1.24), m["moss"], lambda d: d.z > 0.0 and not (d.y < -0.4 and abs(d.x) < 0.5))
	for k in range(16):
		a = 2 * math.pi * (k + 0.5) / 16
		x, y = 0.53 * math.cos(a), 0.04 + 0.49 * math.sin(a)
		if abs(x) < 0.24 and y < 0:
			continue
		_tuft(b, (x, y, 1.22), (math.cos(a) * 0.2, math.sin(a) * 0.2, -1), 0.22, 3, 0.25, [m["moss"], m["moss_b"]], 500 + k, width=0.035)
	if mother:
		b.blob((0.7, 0.5, 0.5), (0, 0.3, 1.24), m["skin_d"], "x", segs=(12, 8))                 # a hunched back
		b.blob((0.72, 0.46, 0.34), (0, 0.34, 1.36), m["moss"], "x", rot=(-24, 0, 0), segs=(10, 6))
		pts = _arc(b, (0, -0.02, 1.26), (0.42, 0.42), 190, 350, 0.02, m["cord"], sides=14, lift=0.0)
		for j, p in enumerate(pts[1:-1]):
			x, y, z = p
			drop = 0.06 + 0.1 * math.sin(math.pi * (j + 1) / 14)
			if j % 2 == 0:
				b.seg((x, y, z), (x * 1.02, y - 0.03, z - drop), 0.03, 0.012, m["bone"], "x", sides=4)   # finger bones and teeth
			else:
				b.blob((0.06, 0.06, 0.07), (x, y - 0.02, z - 0.04), m["bone"], "x", segs=(6, 4))
		b.blob((0.2, 0.16, 0.2), (0, -0.46, 1.0), m["bone"], "x", segs=(8, 6))                   # a skull at the center
		for s in (1, -1):
			b.blob((0.05, 0.03, 0.05), (0.05 * s, -0.53, 1.02), m["dark"], "x", segs=(5, 3))
	else:
		for x, z in ((0.22, 1.06), (-0.18, 1.0)):   # a reed doll and a bundle of bones on cords
			b.seg((x, -0.38, 1.24), (x, -0.4, z + 0.12), 0.008, 0.008, m["cord"], "x", sides=3)
		b.seg((0.22, -0.4, 1.12), (0.22, -0.42, 0.9), 0.04, 0.03, m["reed"], "x", sides=5)
		b.seg((0.12, -0.41, 1.04), (0.32, -0.41, 1.04), 0.02, 0.02, m["reed"], "x", sides=4)
		b.blob((0.08, 0.07, 0.08), (0.22, -0.41, 1.16), m["reed_l"], "x", segs=(6, 4))
		for k in range(3):
			b.seg((-0.18 - 0.04 * k, -0.4, 1.1), (-0.14 - 0.06 * k, -0.42, 0.92), 0.018, 0.012, m["bone"], "x", sides=4)


def build_sedge_sister_chest():
	b = Builder("sedge_sister_chest")
	_sedge_chest(b, sedge_materials(), False)
	return b.build_static()


def build_mother_marrowroot_chest():
	b = Builder("mother_marrowroot_chest")
	_sedge_chest(b, sedge_materials(True), True)
	return b.build_static()


# the pondkin: the Barbarian's skin (0,0) (1,3) (3,1) marsh green, the trousers (7,1) bare legs, the boots (3,2)
# webbed feet, the vest (7,0) woven reed, fur trim (2,1) reed, leather (6,0) (6,1) (5,1) dark hide, metal (3,0) shell
PONDKIN_CELLS = {(0, 0): ("7e9e4a", "3a5220"), (1, 3): ("7e9e4a", "3a5220"), (3, 1): ("7a9a48", "36501e"),
				 (7, 1): ("7a9a48", "36501e"), (3, 2): ("5e7e36", "24361a"), (7, 0): ("c0ac60", "5e5024"),
				 (2, 1): ("a8984e", "54481e"), (6, 0): ("5a4a30", "261c10"), (6, 1): ("5a4a30", "261c10"),
				 (5, 1): ("5a4a30", "261c10"), (3, 0): ("efe4cc", "a09274")}
MUDCALLER_CELLS = {(0, 0): ("5a7842", "22321a"), (1, 3): ("5a7842", "22321a"), (3, 1): ("587640", "20301a"),
				   (7, 1): ("587640", "20301a"), (3, 2): ("46602e", "182412"), (7, 0): ("6e5a3e", "2a2012"),
				   (2, 1): ("8a7a4a", "3a3018"), (6, 0): ("4a3a26", "1a120a"), (6, 1): ("4a3a26", "1a120a"),
				   (5, 1): ("4a3a26", "1a120a"), (3, 0): ("e6dcc0", "8e8266")}
BLOATKING_CELLS = {(0, 0): ("9ea452", "545c24"), (1, 3): ("9ea452", "545c24"), (3, 1): ("9aa04e", "505822"),
				   (7, 1): ("9aa04e", "505822"), (3, 2): ("78803a", "383e18"), (7, 0): ("8a3a26", "3a120a"),
				   (2, 1): ("c0ac60", "5e5024"), (6, 0): ("6a4a2a", "2a1a0c"), (6, 1): ("6a4a2a", "2a1a0c"),
				   (5, 1): ("6a4a2a", "2a1a0c"), (3, 0): ("a0582a", "4e2812")}
# the sunken: the Rogue waterlogged: skin (0,0) green-gray, hair (1,0) weed, eyes (2,0) milky, tunic (0,1) and
# cape (1,1) rotted linen, belt (5,0) and buckles (3,0) (6,0) blackened, trousers (7,1) mud, boots (3,2) bare feet
SUNKEN_CELLS = {(0, 0): ("a8b8a2", "5a6c60"), (1, 0): ("4a5a34", "182412"), (2, 0): ("d8e4dc", "8a9e98"),
				(0, 1): ("8a8468", "3a3828"), (1, 1): ("6a7050", "262c1c"), (5, 0): ("4a4232", "181410"),
				(3, 0): ("6a6a5a", "2a2a22"), (6, 0): ("5a5040", "221c14"), (7, 1): ("6a6452", "262420"),
				(3, 2): ("8a9a88", "3e4a40"), (7, 2): ("9aaa96", "4e5e54")}
# the headwoman: the Mage in faded sea-teal, a tarnished ochre cape, pale green-gray skin
SUNKEN_HEADWOMAN_CELLS = {(0, 1): ("6e8e88", "1e302e"), (1, 1): ("6e8e88", "1e302e"), (2, 1): ("a8904a", "3e3014"),
						  (3, 0): ("b8a060", "5a4418"), (4, 0): ("b8a060", "5a4418"), (5, 0): ("5a4a30", "1e160c"),
						  (2, 2): ("6a8a70", "24382a"), (7, 1): ("3e4e46", "121a16"), (0, 2): ("c8c0a0", "7a7258"),
						  (3, 2): ("5a6a5a", "1e261e"), (0, 0): ("b0c0ae", "62746a"), (7, 2): ("b0c0ae", "62746a"),
						  (1, 0): ("4a5a34", "182412")}
# the sedge sisters: the Mage in bog brown and moss, sallow green skin; the mother darker still
SEDGE_CELLS = {(0, 1): ("6e5636", "22180c"), (1, 1): ("6e5636", "22180c"), (2, 1): ("5e7230", "1e2a0e"),
			   (3, 0): ("8a8a4a", "3a3a18"), (4, 0): ("8a8a4a", "3a3a18"), (5, 0): ("3e2e1e", "140c06"),
			   (2, 2): ("6a4a2a", "2a1a0c"), (7, 1): ("4a3e26", "18120a"), (0, 2): ("8a7a50", "3a3018"),
			   (3, 2): ("3a2e1e", "120c06"), (0, 0): ("b0b884", "6a7442"), (7, 2): ("b0b884", "6a7442"),
			   (1, 0): ("4a4a36", "1a1a10")}
MARROWROOT_CELLS = {(0, 1): ("4e3e2a", "140e08"), (1, 1): ("4e3e2a", "140e08"), (2, 1): ("3e4e22", "121a08"),
					(3, 0): ("d8ceb0", "8a8062"), (4, 0): ("d8ceb0", "8a8062"), (5, 0): ("2e2218", "0c0804"),
					(2, 2): ("5a3a22", "1e1008"), (7, 1): ("362a1c", "0e0a06"), (0, 2): ("d8ceb0", "8a8062"),
					(3, 2): ("2e241a", "0c0806"), (0, 0): ("98a47c", "56623e"), (7, 2): ("98a47c", "56623e"),
					(1, 0): ("c8ccc0", "7e847a")}


# --- Reedmere beasts: the reedstalker heron, the marsh eel, the bogwing, the bog lurker

def glass_material(name, color, alpha, rough=0.2, emit=0.0):
	"""A see-through material (dragonfly wings): glTF exports it as alpha BLEND."""
	m = material(name, color, rough, emit)
	bsdf = m.node_tree.nodes["Principled BSDF"]
	bsdf.inputs["Alpha"].default_value = alpha
	if hasattr(m, "surface_render_method"):
		m.surface_render_method = "BLENDED"
	if hasattr(m, "blend_method"):
		try:
			m.blend_method = "BLEND"
		except (AttributeError, TypeError):
			pass
	m.diffuse_color = m.diffuse_color[:3] + (alpha,)
	return m


def metal_material(name, color, rough=0.35, metallic=0.6, emit=0.0):
	m = material(name, color, rough, emit)
	m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = metallic
	return m


HERON_COLORS = {"slate": "5c7090", "slate_d": "3a4a64", "slate_l": "8a9cb4", "white": "eef0ee", "cream": "d8d8d0",
				"black": "1e222a", "beak": "e0a830", "beak_d": "8a5a1a", "leg": "a89a5a", "leg_d": "5e5630", "eye": "f4d020"}
OLD_HERON_COLORS = {"slate": "c4c8cc", "slate_d": "8a9098", "slate_l": "e4e6e6", "white": "f6f6f2", "cream": "dcd8cc",
					"black": "4a4c52", "beak": "c8a060", "beak_d": "6a4a24", "leg": "8a8466", "leg_d": "4a4636", "eye": "e8e0c0"}


def build_reedstalker(name="reedstalker", old=False):
	"""A giant marsh heron on stilt legs: a slate-blue body, white neck in an S-curve, a black crest
	streaming back and a dagger bill. The wings lie folded along the sides and open wide to strike.
	The old one is the same bird gone white and ragged, feathers torn and scarred."""
	import random
	rng = random.Random(307 if old else 301)
	c = OLD_HERON_COLORS if old else HERON_COLORS
	mat = {k: material(f"{name}_{k}", v, 0.85 if k not in ("beak", "beak_d", "eye") else 0.35, emit=0.8 if k == "eye" else 0.0)
		   for k, v in c.items()}
	pupil = material(f"{name}_pupil", "0e0c08" if not old else "6a7076", 0.2)
	scar = material(f"{name}_scar", "8a5a50", 0.8)
	b = Builder(name)
	b.bone("root", (0, 0, 1.2))
	b.bone("body", (0, 0.02, 1.26), "root")
	b.bone("neck1", (0, -0.36, 1.48), "body")
	b.bone("neck2", (0, -0.36, 1.86), "neck1")
	b.bone("head", (0, -0.42, 2.18), "neck2")
	b.bone("bill_lo", (0, -0.56, 2.19), "head")
	b.bone("tail", (0, 0.5, 1.2), "body")
	b.bone("wing_l", (0.22, -0.2, 1.44), "body")
	b.bone("wing_r", (-0.22, -0.2, 1.44), "body")

	# the body: a long teardrop, tipped up at the breast
	b.blob((0.54, 1.04, 0.56), (0, 0.06, 1.3), mat["slate"], "body", rot=(-16, 0, 0), segs=(14, 10))
	b.blob((0.46, 0.6, 0.44), (0, -0.2, 1.3), mat["white"] if old else mat["slate_l"], "body", rot=(-30, 0, 0), segs=(12, 8))  # the breast
	b.blob((0.4, 0.7, 0.2), (0, 0.1, 1.08), mat["cream"], "body", segs=(10, 6))                                          # the belly
	for k in range(9):   # breast plumes hanging off the lower neck
		x = (k - 4) * 0.035
		ln = 0.34 + 0.06 * (1 - abs(k - 4) / 4) + (rng.uniform(-0.08, 0.04) if old else 0.0)
		b.seg((x, -0.38, 1.46), (x * 1.4, -0.46, 1.46 - ln), 0.03, 0.006, mat["white"] if k % 2 else mat["cream"], "body", sides=4)
	# the neck: an S of segments, white down the front with a streak of black
	neck = [(0, -0.3, 1.42, 0.13), (0, -0.42, 1.6, 0.1), (0, -0.4, 1.78, 0.085), (0, -0.32, 1.92, 0.08), (0, -0.34, 2.06, 0.075),
			(0, -0.42, 2.18, 0.08)]
	for k, ((x0, y0, z0, r0), (x1, y1, z1, r1)) in enumerate(zip(neck, neck[1:])):
		bone = "neck1" if k < 2 else "neck2"
		b.seg((x0, y0, z0), (x1, y1, z1), r0, r1, mat["slate_l"] if not old else mat["white"], bone, sides=10)
		b.seg((x0, y0 - r0 * 0.5, z0), (x1, y1 - r1 * 0.5, z1), r0 * 0.62, r1 * 0.62, mat["white"], bone, sides=8)
		b.blob((r1 * 2, r1 * 2, r1 * 2), (x1, y1, z1), mat["slate_l"] if not old else mat["white"], bone, segs=(8, 6))
		if 1 <= k <= 3:
			b.seg((0, y0 - r0 * 0.94, z0), (0, y1 - r1 * 0.94, z1), 0.018, 0.018, mat["black"], bone, sides=4)
	# the head and bill
	b.blob((0.22, 0.36, 0.22), (0, -0.48, 2.22), mat["white"], "head", segs=(12, 8))
	b.blob((0.24, 0.3, 0.1), (0, -0.46, 2.32), mat["black"], "head", segs=(10, 5))                       # the black crown
	for s in (1, -1):
		b.blob((0.07, 0.07, 0.07), (0.09 * s, -0.56, 2.25), mat["eye"], "head", segs=(8, 5))
		b.blob((0.03, 0.02, 0.04), (0.115 * s, -0.575, 2.25), pupil, "head", segs=(5, 3))
		b.seg((0.1 * s, -0.5, 2.3), (0.11 * s, -0.36, 2.28), 0.02, 0.01, mat["black"], "head", sides=4)   # the black brow stripe
	for k, (dx, dz, ln) in enumerate(((0.0, 0.0, 0.5), (0.03, -0.03, 0.42), (-0.03, -0.02, 0.38))):   # the crest streaming back
		b.seg((dx, -0.4, 2.32 + dz), (dx * 2, -0.4 + ln, 2.28 + dz - ln * 0.2), 0.03, 0.004, mat["black"], "head", sides=4)
	b.seg((0, -0.6, 2.24), (0, -1.16, 2.19), 0.055, 0.004, mat["beak"], "head", sides=7)                 # upper bill
	b.seg((0, -0.6, 2.26), (0, -0.94, 2.23), 0.03, 0.01, mat["beak_d"], "head", sides=5)                  # its dark ridge
	b.seg((0, -0.58, 2.19), (0, -1.1, 2.17), 0.045, 0.004, mat["beak"], "bill_lo", sides=7)              # lower bill
	# folded wings: covert plates along the sides, long dark primaries laid back past the tail
	for s in (1, -1):
		w = f"wing_{'l' if s > 0 else 'r'}"
		x = 0.27 * s
		_oblob(b, (0.12, 0.84, 0.5), (x, 0.08, 1.34), (0, 1, -0.28), (s, 0, 0.3), mat["slate"], w, segs=(10, 6))
		_oblob(b, (0.1, 0.44, 0.28), (x * 1.04, -0.08, 1.44), (0, 1, -0.12), (s, 0, 0.3), mat["slate_l"], w)
		for k in range(7):
			u = k / 6
			ln = 0.72 + 0.26 * u
			if old and k in (2, 5):
				ln *= 0.62   # torn off short
			a = Vector((x + 0.01 * s * k, 0.0 + 0.1 * u, 1.36 - 0.06 * u))
			d = Vector((0.03 * s, 1.0, -0.22 - 0.12 * u)).normalized()
			_oblob(b, (0.05, ln, 0.18), tuple(a + d * ln * 0.5), d, (s, 0, 0.3), mat["slate_d"] if k % 2 else mat["slate"], w, segs=(8, 4))
			_oblob(b, (0.045, ln * 0.36, 0.16), tuple(a + d * ln * 0.84 + Vector((0.02 * s, 0, 0))), d, (s, 0, 0.3),
				   mat["black"], w, segs=(6, 4))
		if old:   # a scar across the coverts, and ragged feathers sticking out
			b.seg((x * 1.18, -0.12, 1.5), (x * 1.18, 0.22, 1.26), 0.018, 0.018, scar, w, sides=4)
			for k in range(4):
				p = Vector((x * 1.1, rng.uniform(-0.1, 0.4), rng.uniform(1.2, 1.46)))
				b.seg(tuple(p), tuple(p + Vector((0.12 * s, rng.uniform(0.0, 0.14), rng.uniform(-0.1, 0.1)))), 0.03, 0.004, mat["cream"], w, sides=3)
	for k in range(7):   # a short tail
		yaw = (k - 3) * 10
		d = Vector((math.sin(math.radians(yaw)), math.cos(math.radians(yaw)), -0.5)).normalized()
		a = Vector((0, 0.5, 1.2))
		ln = 0.36 if not (old and k % 3 == 0) else 0.22
		b.seg(tuple(a), tuple(a + d * ln), 0.06, 0.02, mat["slate_d"] if k % 2 else mat["slate"], "tail", sides=4)
	# the long legs: thigh feathers, a bare shank to the backward-bending joint, then the foot
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		x = 0.13 * s
		b.bone(f"leg_{side}", (x, 0.04, 1.12), "root")
		b.bone(f"shin_{side}", (x, 0.1, 0.56), f"leg_{side}")
		b.blob((0.18, 0.24, 0.26), (x, 0.04, 1.04), mat["cream"], f"leg_{side}", segs=(8, 6))
		b.seg((x, 0.04, 1.0), (x, 0.1, 0.56), 0.045, 0.036, mat["leg"], f"leg_{side}", sides=6)
		b.blob((0.08, 0.08, 0.08), (x, 0.1, 0.56), mat["leg_d"], f"shin_{side}", segs=(6, 4))
		b.seg((x, 0.1, 0.56), (x, 0.02, 0.05), 0.036, 0.03, mat["leg"], f"shin_{side}", sides=6)
		for dx, dy in ((0.0, -0.3), (0.13, -0.22), (-0.13, -0.22), (0.0, 0.16)):   # three long toes forward, one back
			root = Vector((x, 0.02, 0.04))
			end = root + Vector((dx * s, dy, -0.02))
			b.seg(tuple(root), tuple(end), 0.026, 0.016, mat["leg_d"], f"shin_{side}", sides=4)
	arm = b.build()

	def folded(k=0.0):
		"""k=0 folded, 1 spread wide and raised."""
		return {"wing_l": {"rot": (-30 * k, -20 * k, -95 * k)}, "wing_r": {"rot": (-30 * k, 20 * k, 95 * k)}}

	def legs(l, r, fold_l=0.0, fold_r=0.0):
		return {"leg_l": {"rot": (l, 0, 0)}, "leg_r": {"rot": (r, 0, 0)},
				"shin_l": {"rot": (-fold_l, 0, 0)}, "shin_r": {"rot": (-fold_r, 0, 0)}}

	def idle(t):   # stands still as a reed, the neck swaying, a slow look round and a ruffle
		look = seq(t, [(0, 0), (0.3, 0), (0.38, 26), (0.6, 26), (0.68, 0)])
		ruffle = seq(t, [(0.8, 0), (0.86, 0.1), (0.92, 0)])
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))}, "neck1": {"rot": (3 * wave(t), 0, 0)},
					  "neck2": {"rot": (-3 * wave(t), 0, look * 0.4)}, "head": {"rot": (2 * wave(t, 1, 0.3), 0, look * 0.6)},
					  "tail": {"rot": (3 * wave(t, 2), 0, 0)}}, folded(ruffle))

	def stride(t, swing, fold, bob, lean):
		lift_l = max(0.0, wave(t, 1, 0.25))
		lift_r = max(0.0, wave(t, 1, 0.75))
		pump = wave(t, 2, 0.1)   # the head pumps forward and back with each step
		return merge(legs(swing * wave(t), -swing * wave(t), fold * lift_l, fold * lift_r),
					 {"root": {"loc": (0, 0, bob * abs(wave(t, 2))), "rot": (lean, 3 * wave(t), 0)},
					  "neck1": {"rot": (-6 * pump - lean * 0.5, 0, 0)}, "neck2": {"rot": (8 * pump, 0, 0)},
					  "head": {"rot": (-2 * pump, 0, 0)}, "tail": {"rot": (4 * wave(t, 2), 0, 0)}}, folded(0.04))

	def walk(t):   # a slow, stately, high-stepping wade
		return stride(t, 24, 50, 0.03, 0)

	def run(t):   # long loping strides, wings half open
		return merge(stride(t, 36, 70, 0.08, -10), folded(0.35 + 0.1 * wave(t, 2)))

	def attack(t):   # the neck coils back, wings flare, then the bill spears forward
		coil = seq(t, [(0, 0), (0.35, 1), (0.48, -1), (0.62, -0.9), (1, 0)])
		pull, stab = max(0.0, coil), max(0.0, -coil)
		spread = seq(t, [(0, 0), (0.3, 1), (0.6, 0.9), (1, 0)])
		gape = seq(t, [(0, 0), (0.3, 16), (0.46, 20), (0.52, 0), (1, 0)])
		return merge({"root": {"loc": (0, 0.3 * stab - 0.06 * pull, 0), "rot": (-12 * stab + 6 * pull, 0, 0)},
					  "neck1": {"rot": (26 * pull - 34 * stab, 0, 0)}, "neck2": {"rot": (-40 * pull + 22 * stab, 0, 0)},
					  "head": {"rot": (14 * pull - 8 * stab, 0, 0)}, "bill_lo": {"rot": (-gape, 0, 0)}},
					 legs(-10 * stab, 14 * stab), folded(spread))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.02 * k), "rot": (10 * k, 6 * k, 0)},
					  "neck1": {"rot": (18 * k, 0, 10 * k)}, "neck2": {"rot": (-10 * k, 0, 0)}, "head": {"rot": (10 * k, 0, -18 * k)}},
					 folded(0.5 * k))

	def death(t):   # the wings flail, the legs buckle and it topples onto its side, the neck flung out
		flare = seq(t, [(0, 0), (0.2, 0.9), (0.5, 0.4), (0.85, 0.15)])
		fold = seq(t, [(0.15, 0), (0.55, 1)])
		roll = seq(t, [(0.3, 0), (0.75, 82), (0.84, 76), (0.92, 80)])
		drop = seq(t, [(0.15, 0), (0.55, -0.5), (0.8, -0.98)])
		curl = seq(t, [(0.4, 0), (0.9, 1)])
		return merge({"root": {"loc": (0, 0.1 * fold, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.6, -4)]), roll, 0)},
					  "neck1": {"rot": (-40 * curl, 0, 20 * curl)}, "neck2": {"rot": (30 * curl, 0, 20 * curl)},
					  "head": {"rot": (-20 * curl, 0, 10 * curl)}, "bill_lo": {"rot": (-10 * curl, 0, 0)}},
					 legs(50 * fold, 30 * fold, 110 * fold, 90 * fold), folded(flare))

	clip(arm, "idle", 3.6, idle, True)
	clip(arm, "walk", 1.3, walk, True)
	clip(arm, "run", 0.7, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.5, death, False)
	return arm


def build_old_stilt_legs():
	return build_reedstalker("old_stilt_legs", old=True)


EEL_SEGS = 9


def build_marsh_eel():
	"""A thick marsh eel, three meters of olive muscle with a yellow belly, a fin running down its back
	and a jaw full of needle teeth. Each body segment rides its own bone off the root, so a traveling
	wave through them draws clean S-curves as it slithers."""
	import random
	rng = random.Random(311)
	olive = material("eel_olive", "6a6a2a", 0.45)
	olive_d = material("eel_olive_dark", "3c3c16", 0.5)
	belly = material("eel_belly", "dcc254", 0.5)
	fin = material("eel_fin", "8a7a34", 0.6)
	mouth = material("eel_mouth", "a8484a", 0.6)
	tooth = material("eel_tooth", "f2ead6", 0.3)
	eye = material("eel_eye", "f0d030", 0.2, emit=0.8)
	pupil = material("eel_pupil", "0c0a06", 0.2)
	b = Builder("marsh_eel")
	b.bone("root", (0, 0, 0.2))
	# segments from the neck (i = 0) to the tail tip, each on its own bone
	ys = [-0.9 + 0.36 * i for i in range(EEL_SEGS)]
	radii = [0.21, 0.22, 0.22, 0.21, 0.19, 0.16, 0.13, 0.09, 0.05]
	for i, (y, r) in enumerate(zip(ys, radii)):
		bone = f"seg{i}"
		b.bone(bone, (0, y, r), "root")
		ny = y + 0.36
		nr = radii[i + 1] if i + 1 < len(radii) else 0.02
		b.seg((0, y, r), (0, ny, nr), r, nr, olive, bone, sides=12)
		b.blob((r * 2.05, r * 2.05, r * 1.9), (0, y, r), olive, bone, segs=(12, 8))
		b.seg((0, y, r * 0.55), (0, ny, nr * 0.55), r * 0.8, nr * 0.8, belly, bone, sides=10)        # the yellow belly
		# the fin down the back: a thin strip standing on the ridge
		_slab(b, [(0, y, r * 1.9), (0, ny, nr * 1.9), (0, ny, nr * 2.0 + 0.05 * (nr / 0.22)), (0, y, r * 2.0 + 0.05 * (r / 0.22))], 0.02, fin)
		_on_bone(b, len(b.parts) - 1, bone)
		for k in range(2):   # dark mottles
			a = rng.uniform(-1.2, 1.2)
			p = Vector((r * 0.9 * math.sin(a), y + rng.uniform(0.05, 0.3), r + r * 0.9 * math.cos(a)))
			_oblob(b, (r * 0.5, r * 0.8, 0.03), tuple(p), (0, 1, 0), (math.sin(a), 0, math.cos(a)), olive_d, bone, segs=(8, 4))
	# the tail tip: a paddle of fin
	yt = ys[-1] + 0.36
	_slab(b, [(0, yt - 0.3, 0.06), (0, yt + 0.3, 0.1), (0, yt + 0.34, 0.2), (0, yt - 0.2, 0.2)], 0.025, fin)
	_on_bone(b, len(b.parts) - 1, f"seg{EEL_SEGS - 1}")
	# the head: a blunt wedge with a gaping jaw, low and forward
	b.bone("head", (0, -1.0, 0.22), "root")
	b.bone("jaw", (0, -1.12, 0.16), "head")
	b.blob((0.44, 0.5, 0.34), (0, -1.14, 0.26), olive, "head", segs=(12, 8))
	b.blob((0.36, 0.44, 0.2), (0, -1.42, 0.25), olive, "head", segs=(12, 7))                   # the snout
	b.blob((0.3, 0.4, 0.1), (0, -1.42, 0.18), mouth, "head", segs=(10, 5))                      # the roof of the mouth
	b.blob((0.36, 0.56, 0.16), (0, -1.3, 0.12), belly, "jaw", segs=(12, 6))                     # the lower jaw
	b.blob((0.28, 0.44, 0.06), (0, -1.34, 0.18), mouth, "jaw", segs=(10, 4))
	for s in (1, -1):
		b.blob((0.1, 0.1, 0.08), (0.15 * s, -1.28, 0.36), eye, "head", segs=(8, 5))
		b.blob((0.03, 0.04, 0.06), (0.19 * s, -1.3, 0.36), pupil, "head", segs=(5, 3))
		b.blob((0.03, 0.03, 0.02), (0.07 * s, -1.62, 0.3), pupil, "head", segs=(5, 3))            # nostrils
		for k in range(6):   # needle teeth, down from the upper jaw and up from the lower
			y = -1.58 + 0.07 * k
			x = (0.11 + 0.01 * k) * s
			b.seg((x, y, 0.2), (x, y - 0.01, 0.13), 0.02, 0.002, tooth, "head", sides=4)
			b.seg((x * 0.95, y + 0.03, 0.17), (x * 0.95, y + 0.02, 0.24), 0.018, 0.002, tooth, "jaw", sides=4)
		_oblob(b, (0.2, 0.14, 0.02), (0.2 * s, -0.92, 0.24), (0, 1, -0.4), (s, 0, 0), fin, "head", segs=(8, 4))   # gill fins
	b.blob((0.4, 0.3, 0.36), (0, -0.92, 0.22), olive, "head", segs=(10, 7))                    # the neck joins the body
	arm = b.build()

	def body(t, amp, cycles, wavelength=2.4, lift=0.0):
		"""A wave traveling down the body: each segment is set sideways and turned along the curve."""
		out = {}
		pts = ys + [ys[-1] + 0.36]

		def xat(i, y):
			grow = 0.35 + 0.65 * min(1.0, (i + 1) / 3)   # the front swings less than the tail
			return amp * grow * math.sin(2 * math.pi * (t * cycles - y / wavelength))
		xs = [xat(i, y) for i, y in enumerate(pts)]
		for i in range(EEL_SEGS):
			yaw = -math.degrees(math.atan2(xs[i + 1] - xs[i], 0.36))
			out[f"seg{i}"] = {"loc": (-xs[i], 0, lift * max(0.0, 1 - i / 3)), "rot": (0, 0, yaw)}
		hx = xat(0, -1.0)
		out["head"] = {"loc": (-hx, 0, lift), "rot": (0, 0, -math.degrees(math.atan2(xs[0] - hx, 0.1)) * 0.5)}
		return out

	def idle(t):
		return merge(body(t, 0.05, 1), {"head": {"rot": (4 + 3 * wave(t, 1, 0.2), 0, 0)}, "jaw": {"rot": (-4 * max(0.0, wave(t, 2)), 0, 0)}})

	def walk(t):
		return body(t, 0.2, 1)

	def run(t):
		return merge(body(t, 0.24, 1, 2.8), {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}})

	def attack(t):   # the head rears back and up, then lunges and snaps
		rear = seq(t, [(0, 0), (0.3, 1), (0.45, -0.4), (0.62, -0.3), (1, 0)])
		up, lunge = max(0.0, rear), max(0.0, -rear)
		gape = seq(t, [(0, 0), (0.3, 30), (0.44, 44), (0.52, 0), (0.6, 18), (0.66, 0)])
		pose = merge(body(t, 0.04, 1), {"head": {"loc": (0, 0.14 * up - 0.5 * lunge, 0.3 * up + 0.05 * lunge), "rot": (28 * up - 6 * lunge, 0, 0)},
										"jaw": {"rot": (-gape, 0, 0)},
										"seg0": {"loc": (0, 0.06 * up - 0.3 * lunge, 0.14 * up), "rot": (14 * up, 0, 0)},
										"seg1": {"loc": (0, -0.14 * lunge, 0.05 * up), "rot": (6 * up, 0, 0)}})
		return pose

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge(body(t, 0.1 * k, 2), {"head": {"loc": (0, 0.12 * k, 0.05 * k), "rot": (14 * k, 0, 16 * k)}, "jaw": {"rot": (-20 * k, 0, 0)}})

	def death(t):   # thrashes, then rolls belly-up and goes still
		thrash = seq(t, [(0, 1), (0.6, 0.2), (0.85, 0)])
		roll = seq(t, [(0.25, 0), (0.7, 170), (0.8, 180)])
		gape = seq(t, [(0.3, 0), (0.8, 30)])
		pose = merge(body(t * 2, 0.22 * thrash, 1), {"root": {"rot": (0, roll, 0), "loc": (0, 0, seq(t, [(0.3, 0), (0.6, 0.1), (0.8, 0.02)]))},
													  "jaw": {"rot": (-gape, 0, 0)}})
		return pose

	clip(arm, "idle", 2.6, idle, True)
	clip(arm, "walk", 1.2, walk, True)
	clip(arm, "run", 0.7, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


def build_bogwing():
	"""A giant dragonfly: huge compound eyes, a thorax of iridescent teal, a long banded tail and four
	clear, veined wings that never stop buzzing while it hovers at head height."""
	teal = metal_material("bogwing_teal", "1e9a92", 0.3, 0.55)
	teal_d = metal_material("bogwing_teal_dark", "0e4a52", 0.35, 0.5)
	blue = metal_material("bogwing_blue", "2a6ad0", 0.3, 0.5)
	gold = metal_material("bogwing_gold", "c8b040", 0.35, 0.5)
	black = material("bogwing_black", "10141a", 0.5)
	eye = material("bogwing_eye", "3ad8a8", 0.15, emit=0.4)
	eye_d = material("bogwing_eye_dark", "147a6a", 0.2, emit=0.2)
	wing = glass_material("bogwing_wing", "dcf4f4", 0.38, 0.1, emit=0.1)
	vein = glass_material("bogwing_vein", "5a7a82", 0.7, 0.4)
	spot = material("bogwing_spot", "2a3236", 0.5)
	b = Builder("bogwing")
	z0 = 1.3
	b.bone("root", (0, 0, z0))
	b.bone("body", (0, 0, z0), "root")
	b.bone("head", (0, -0.34, z0 + 0.02), "body")
	b.bone("tail1", (0, 0.3, z0), "body")
	b.bone("tail2", (0, 0.74, z0 - 0.02), "tail1")
	# the thorax, humped, with gold shoulder stripes
	b.blob((0.34, 0.5, 0.36), (0, -0.04, z0 + 0.02), teal, "body", segs=(12, 8))
	b.blob((0.3, 0.3, 0.2), (0, -0.04, z0 + 0.14), teal_d, "body", segs=(10, 6))
	for s in (1, -1):
		b.seg((0.12 * s, -0.24, z0 + 0.08), (0.14 * s, 0.14, z0 + 0.14), 0.025, 0.025, gold, "body", sides=5)
	# the head: two great eyes wrapping round, a face and jaws below
	for s in (1, -1):
		b.blob((0.26, 0.26, 0.26), (0.1 * s, -0.4, z0 + 0.07), eye, "head", segs=(14, 10))
		b.blob((0.12, 0.08, 0.14), (0.17 * s, -0.5, z0 + 0.1), eye_d, "head", segs=(8, 5))
		b.seg((0.04 * s, -0.5, z0 - 0.08), (0.08 * s, -0.56, z0 - 0.16), 0.035, 0.006, black, "head", sides=5)   # mandibles
	b.blob((0.2, 0.12, 0.2), (0, -0.5, z0 - 0.04), teal_d, "head", segs=(10, 6))
	b.blob((0.14, 0.06, 0.08), (0, -0.55, z0 + 0.02), gold, "head", segs=(8, 4))
	# the tail: ten banded segments, a blue tip and claspers
	pts = [(0, 0.22 + 0.13 * k, z0 - 0.01 - 0.012 * k) for k in range(11)]
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		bone = "tail1" if k < 4 else "tail2"
		r = 0.075 - 0.003 * k
		b.seg(p, q, r, r * 0.95, (blue if k >= 8 else teal), bone, sides=8)
		b.blob((r * 2.1, 0.05, r * 2.1), q, black if k < 8 else teal_d, bone, segs=(8, 4))
	for s in (1, -1):
		b.seg(pts[-1], (0.05 * s, pts[-1][1] + 0.12, pts[-1][2] - 0.02), 0.02, 0.004, black, "tail2", sides=4)
	# six legs folded up under the thorax like a basket
	for k, y in enumerate((-0.16, -0.04, 0.08)):
		for s in (1, -1):
			knee = (0.16 * s, y - 0.06, z0 - 0.2)
			b.seg((0.06 * s, y, z0 - 0.12), knee, 0.022, 0.018, black, "body", sides=4)
			b.seg(knee, (0.08 * s, y - 0.18, z0 - 0.3), 0.018, 0.008, black, "body", sides=4)
	# the wings: long, clear, a dark vein along the leading edge and a spot near the tip
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		for fb, (y, ln, wd) in (("f", (-0.1, 1.02, 0.24)), ("b", (0.08, 0.96, 0.28))):
			bone = f"wing_{fb}{side}"
			root = Vector((0.08 * s, y, z0 + 0.16))
			b.bone(bone, tuple(root), "body")
			sweep = -0.1 if fb == "f" else 0.14
			d = Vector((s, sweep, 0.04)).normalized()
			c = root + d * ln * 0.52
			_oblob(b, (wd, ln, 0.012), tuple(c + Vector((0, 0.04, 0))), d, (0, 0, 1), wing, bone, segs=(16, 4))
			b.seg(tuple(root), tuple(root + d * ln), 0.012, 0.006, vein, bone, sides=4)                   # the leading edge
			b.seg(tuple(root + Vector((0, 0.05, 0))), tuple(root + d * ln * 0.8 + Vector((0, 0.1, 0))), 0.007, 0.004, vein, bone, sides=3)
			_oblob(b, (0.06, 0.1, 0.02), tuple(root + d * ln * 0.88 + Vector((0, 0.02, 0.005))), d, (0, 0, 1), spot, bone, segs=(6, 3))
	arm = b.build()

	def wings(t, beat, amp, cycles, sweep=0.0):
		"""Front and back pairs beat out of phase; roll lifts and drops the wingtips."""
		out = {}
		for fb, ph in (("f", 0.0), ("b", 0.5)):
			r = amp * wave(t, cycles, ph) + beat
			out[f"wing_{fb}l"] = {"rot": (0, r, sweep)}
			out[f"wing_{fb}r"] = {"rot": (0, -r, -sweep)}
		return out

	def idle(t):   # hovers, bobbing and drifting, wings a blur
		return merge(wings(t, 4, 30, 12), {"root": {"loc": (0.03 * wave(t, 1, 0.3), 0, 0.06 * wave(t, 2))},
										  "body": {"rot": (3 * wave(t, 1), 2 * wave(t, 2, 0.2), 0)}, "tail1": {"rot": (-3 * wave(t, 2), 0, 2 * wave(t))},
										  "tail2": {"rot": (-4 * wave(t, 2, 0.2), 0, 3 * wave(t, 1, 0.3))}, "head": {"rot": (0, 0, 6 * wave(t, 1, 0.6))}})

	def walk(t):   # flies forward nose-down
		return merge(wings(t, 2, 34, 8), {"root": {"loc": (0, 0, 0.05 * wave(t, 2)), "rot": (-8, 0, 0)},
										 "tail1": {"rot": (6 + 3 * wave(t, 2), 0, 0)}, "tail2": {"rot": (4 * wave(t, 2, 0.2), 0, 0)}})

	def run(t):
		return merge(wings(t, 0, 38, 6), {"root": {"loc": (0, 0, 0.04 * wave(t, 2)), "rot": (-16, 0, 0)},
										 "tail1": {"rot": (10, 0, 0)}, "tail2": {"rot": (6, 0, 0)}})

	def attack(t):   # darts in, jaws snapping, the tail curling under to stab
		dart = seq(t, [(0, 0), (0.25, -0.12), (0.45, 0.42), (0.7, 0.32), (1, 0)])
		curl = seq(t, [(0, 0), (0.3, 0.2), (0.5, 1), (0.75, 0.6), (1, 0)])
		return merge(wings(t, 0, 38, 7), {"root": {"loc": (0, dart, -0.1 * curl), "rot": (-14 * curl, 0, 0)},
										 "tail1": {"rot": (30 * curl, 0, 0)}, "tail2": {"rot": (46 * curl, 0, 0)},
										 "head": {"rot": (-10 * curl, 0, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge(wings(t, 10 * k, 30, 5), {"root": {"loc": (0, -0.16 * k, 0.06 * k), "rot": (14 * k, 18 * k, 0)},
											  "tail1": {"rot": (14 * k, 0, 10 * k)}})

	def death(t):   # the wings falter and it spirals down, landing on its side
		k = seq(t, [(0.1, 0), (0.8, 1)])
		beat = 1 - seq(t, [(0.2, 0), (0.7, 1)])
		return merge(wings(t, 10 - 30 * k, 34 * beat, 6), {"root": {"loc": (0, 0, -1.14 * k + 0.1 * math.sin(math.pi * k)), "rot": (-6 * k, 84 * k, 200 * k)},
															"tail1": {"rot": (-10 * k, 0, 12 * k)}, "tail2": {"rot": (-16 * k, 0, 10 * k)}})

	clip(arm, "idle", 1.5, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.75, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_bog_lurker():
	"""A hulk of mud, roots and reeds raised out of the bog by the coven: a heaving back sprouting
	cattails, arms that drag near the ground ending in root claws, and two green lights for eyes."""
	import random
	rng = random.Random(317)
	mud = material("lurker_mud", "4e3e2a", 0.6)
	mud_d = material("lurker_mud_dark", "30261a", 0.55)
	mud_w = material("lurker_mud_wet", "5e4c34", 0.3)
	root = material("lurker_root", "6a5034", 0.9)
	root_d = material("lurker_root_dark", "3e2e1e", 0.9)
	moss = material("lurker_moss", "56702e", 0.95)
	moss_b = material("lurker_moss_b", "7c8a3a", 0.95)
	reed = material("lurker_reed", "a89a58", 0.85)
	reed_g = material("lurker_reed_green", "6a7a34", 0.85)
	cattail = material("lurker_cattail", "5a3a1e", 0.95)
	lily = material("lurker_lily", "4e7a36", 0.6)
	eye = material("lurker_eye", "9aff4a", 0.2, emit=4.0)
	maw = material("lurker_maw", "140e08", 0.9)
	glow = material("lurker_glow", "6ae040", 0.4, emit=1.4)
	b = Builder("bog_lurker")
	b.bone("root", (0, 0, 0.05))
	b.bone("hips", (0, 0.04, 0.84), "root")
	b.bone("chest", (0, 0.0, 1.36), "hips")
	b.bone("head", (0, -0.4, 1.86), "chest")

	def lumps(center, radii, n, mats, bone, size=(0.3, 0.5)):
		for k in range(n):
			a, e = rng.uniform(0, 2 * math.pi), rng.uniform(-0.6, 1.0)
			d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
			p = Vector(center) + Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])) * 0.9
			r = rng.uniform(*size)
			b.blob((r, r, r * 0.85), tuple(p), mats[k % len(mats)], bone, segs=(9, 6))

	# the hips and a heaving, hunched torso
	b.blob((0.9, 0.74, 0.62), (0, 0.04, 0.9), mud, "hips", segs=(14, 9))
	lumps((0, 0.04, 0.9), (0.44, 0.36, 0.3), 7, (mud, mud_d), "hips")
	b.blob((1.3, 1.0, 0.96), (0, 0.06, 1.46), mud, "chest", segs=(16, 11))
	b.blob((1.1, 0.8, 0.7), (0, 0.22, 1.76), mud_w, "chest", segs=(14, 9))                    # the hump of the back
	lumps((0, 0.1, 1.5), (0.64, 0.5, 0.48), 12, (mud, mud_d, mud_w), "chest", (0.26, 0.44))
	for k in range(6):   # moss and a lily pad slumped on the shoulders and back
		p = (rng.uniform(-0.5, 0.5), rng.uniform(0.0, 0.46), rng.uniform(1.72, 1.96))
		b.blob((rng.uniform(0.2, 0.34), rng.uniform(0.2, 0.3), 0.1), p, moss if k % 2 else moss_b, "chest", segs=(8, 5))
	_oblob(b, (0.36, 0.36, 0.03), (0.44, 0.12, 1.94), (0, 1, 0), (0.4, 0, 1), lily, "chest", segs=(12, 3))
	def vine(center, radii, z, a0, span, bone, width=0.04, climb=0.3):
		"""A root creeping over the surface: a wandering line hugging an ellipse, rising as it goes."""
		pts = []
		for k in range(9):
			a = math.radians(a0 + span * k / 8)
			r = 1.0 + rng.uniform(-0.04, 0.06)
			pts.append((center[0] + radii[0] * r * math.cos(a), center[1] + radii[1] * r * math.sin(a),
						z + climb * k / 8 + rng.uniform(-0.04, 0.04)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(p, q, width * (1 - 0.06 * k), width * (1 - 0.06 * (k + 1)), root if k % 3 else root_d, bone, sides=5)

	# roots creeping over the torso and hips
	for k in range(6):
		vine((0, 0.06, 0), (0.64, 0.52), 1.0 + 0.14 * k, rng.uniform(0, 360), rng.uniform(80, 150), "chest",
			 climb=rng.uniform(-0.3, 0.3))
	for k in range(2):
		vine((0, 0.04, 0), (0.46, 0.38), 0.78 + 0.1 * k, rng.uniform(0, 360), 120, "hips", climb=0.1)
	# reeds and cattails sprouting from the back
	for k in range(16):
		x, y = rng.uniform(-0.46, 0.46), rng.uniform(0.1, 0.5)
		base = Vector((x, y, 1.8 + 0.1 * (1 - abs(x))))
		tip = base + Vector((x * 0.6 + rng.uniform(-0.1, 0.1), 0.2 + y * 0.4, rng.uniform(0.5, 0.95)))
		b.seg(tuple(base), tuple(tip), 0.03, 0.006, reed if k % 3 else reed_g, "chest", sides=4)
		if k % 3 == 0:
			d = tip - base
			b.seg(tuple(base + d * 0.6), tuple(base + d * 0.82), 0.05, 0.045, cattail, "chest", sides=6)
	# the head: a low, sunken lump with a dark maw of root teeth and two green eyes
	b.blob((0.62, 0.56, 0.5), (0, -0.44, 1.86), mud, "head", segs=(12, 8))
	b.blob((0.7, 0.3, 0.2), (0, -0.56, 2.02), mud_d, "head", rot=(-12, 0, 0), segs=(10, 6))    # a heavy brow
	b.blob((0.4, 0.16, 0.2), (0, -0.7, 1.72), maw, "head", segs=(10, 6))
	for k in range(6):
		x = -0.15 + 0.06 * k
		top = k % 2 == 0
		b.seg((x, -0.74, 1.8 if top else 1.64), (x * 1.1, -0.76, 1.72 if top else 1.72), 0.025, 0.004, root_d, "head", sides=4)
	for s in (1, -1):
		b.blob((0.16, 0.08, 0.12), (0.15 * s, -0.7, 1.92), maw, "head", segs=(8, 5))
		b.blob((0.1, 0.06, 0.08), (0.15 * s, -0.73, 1.92), eye, "head", segs=(8, 5))
	for k in range(5):   # mossy strands hanging off the brow
		x = -0.24 + 0.12 * k
		_kelp(b, (x, -0.62, 2.0), 0.24 + 0.08 * (k % 2), moss if k % 2 else moss_b, lean=(0, -0.2), width=0.04, parts=2)
		_on_bone(b, len(b.parts) - 2, "head")
	# a green glow seeping from cracks in the chest
	for pts in (((0.18, -0.46, 1.58), (0.24, -0.47, 1.44), (0.16, -0.46, 1.32)), ((-0.22, -0.44, 1.5), (-0.14, -0.46, 1.36))):
		_zigzag(b, list(pts), 0.03, glow, "chest")
	# arms hanging almost to the ground, root claws
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"arm_{side}", (0.62 * s, 0.0, 1.74), "chest")
		b.bone(f"hand_{side}", (0.86 * s, -0.08, 0.9), f"arm_{side}")
		b.blob((0.56, 0.6, 0.54), (0.64 * s, 0.02, 1.72), mud_w, f"arm_{side}", segs=(10, 8))   # shoulder
		for k in range(4):   # the arm: a sagging chain of mud lumps
			u = k / 3
			p = (s * (0.68 + 0.16 * u), -0.06 * u, 1.6 - 0.62 * u)
			r = 0.44 - 0.06 * u
			b.blob((r, r * 0.95, r * 1.1), p, (mud, mud_w, mud_d, mud)[k], f"arm_{side}", segs=(10, 8))
		lumps((0.76 * s, -0.03, 1.32), (0.18, 0.18, 0.3), 4, (mud_d, mud), f"arm_{side}", (0.16, 0.24))
		vine((0.76 * s, -0.03, 0), (0.22, 0.22), 1.1, 0, 200, f"arm_{side}", width=0.035, climb=0.4)
		_kelp(b, (0.84 * s, -0.2, 1.3), 0.34, moss, lean=(0, -0.1), width=0.035, parts=2)
		_on_bone(b, len(b.parts) - 2, f"arm_{side}")
		b.blob((0.46, 0.46, 0.44), (0.88 * s, -0.1, 0.78), mud_d, f"hand_{side}", segs=(10, 7))
		for k in range(4):   # root claws
			a = math.radians(-60 + 40 * k)
			base = Vector((0.88 * s, -0.1, 0.62)) + Vector((0.14 * math.sin(a) * s, -0.14 * math.cos(a), 0))
			mid = base + Vector((0.1 * math.sin(a) * s, -0.14 * math.cos(a), -0.18))
			tip = mid + Vector((0.04 * math.sin(a) * s, -0.12, -0.04))
			b.seg(tuple(base), tuple(mid), 0.05, 0.035, root, f"hand_{side}", sides=5)
			b.seg(tuple(mid), tuple(tip), 0.035, 0.006, root_d, f"hand_{side}", sides=5)
		# stumpy legs with root toes
		b.bone(f"leg_{side}", (0.3 * s, 0.04, 0.78), "hips")
		b.blob((0.46, 0.46, 0.52), (0.31 * s, 0.03, 0.6), mud, f"leg_{side}", segs=(10, 8))
		b.blob((0.5, 0.5, 0.46), (0.33 * s, 0.01, 0.32), mud_w, f"leg_{side}", segs=(10, 8))
		b.blob((0.52, 0.62, 0.3), (0.34 * s, -0.08, 0.14), mud_d, f"leg_{side}", segs=(10, 6))
		for k in range(3):
			a = math.radians(-30 + 30 * k)
			base = Vector((0.34 * s + 0.14 * math.sin(a), -0.3, 0.1))
			b.seg(tuple(base), tuple(base + Vector((0.06 * math.sin(a), -0.18, -0.08))), 0.05, 0.01, root_d, f"leg_{side}", sides=5)
		_kelp(b, (0.46 * s, 0.1, 0.62), 0.4, reed_g, lean=(0.1 * s, 0.1), width=0.035, parts=2)
		_on_bone(b, len(b.parts) - 2, f"leg_{side}")
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, 0, 0)}, "hand_r": {"rot": (bend, 0, 0)}}

	def idle(t):   # a slow, wet heave of the back, the head swinging low
		heave = wave(t)
		return merge_scaled({"chest": {"rot": (2 * heave, 0, 2 * wave(t, 1, 0.3)), "scale": (1 + 0.02 * heave, 1 + 0.02 * heave, 1)},
							 "head": {"rot": (-2 * heave, 0, 8 * wave(t, 0.5))}, "hips": {"loc": (0, 0, -0.01 * (1 + heave))}},
							arms(4 * wave(t, 1, 0.1), 4 * wave(t, 1, 0.6), 3, 6))

	def stride(t, swing, lean, bob):
		drop = -bob * (0.5 + 0.5 * wave(t, 2, 0.25))
		return merge_scaled({"leg_l": {"rot": (swing * wave(t), 0, 0)}, "leg_r": {"rot": (-swing * wave(t), 0, 0)},
							 "hips": {"rot": (0, 6 * wave(t), 0), "loc": (0, 0, drop)},
							 "chest": {"rot": (lean, -4 * wave(t), -7 * wave(t))}, "head": {"rot": (-lean * 0.4, 0, 5 * wave(t))}},
							arms(-swing * 0.9 * wave(t), swing * 0.9 * wave(t), 6, 12))

	def walk(t):   # a heavy, dragging lurch
		return stride(t, 18, -10, 0.08)

	def run(t):
		return stride(t, 28, -18, 0.12)

	def attack(t):   # rears up, then brings both arms down in a crushing slam
		up = seq(t, [(0, 0), (0.45, 150), (0.55, 158), (0.68, 30), (0.84, 26), (1, 0)])
		lean = seq(t, [(0, 0), (0.45, 12), (0.55, 14), (0.68, -28), (0.84, -24), (1, 0)])
		sink = seq(t, [(0, 0), (0.45, 0.06), (0.68, -0.16), (0.86, -0.12), (1, 0)])
		surge = seq(t, [(0, 0), (0.55, -0.06), (0.68, 0.24), (0.86, 0.2), (1, 0)])
		splat = seq(t, [(0.64, 1.0), (0.7, 1.12), (0.9, 1.0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "hips": {"loc": (0, 0, sink), "rot": (lean * 0.3, 0, 0)},
							 "chest": {"rot": (lean * 0.7, 0, 0), "scale": (splat, splat, 2 - splat)}, "head": {"rot": (-lean * 0.4, 0, 0)}},
							arms(up, up, 10, seq(t, [(0, 0), (0.45, 20), (0.65, -12), (1, 0)])))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"chest": {"rot": (10 * k, 6 * k, 8 * k), "scale": (1 - 0.05 * k, 1 - 0.05 * k, 1 + 0.04 * k)},
							 "head": {"rot": (10 * k, 0, 10 * k)}, "hips": {"loc": (0, -0.06 * k, 0)}}, arms(-16 * k, -10 * k, 8 * k, -8 * k))

	def death(t):   # sags and slumps into a heap of mud
		reel = seq(t, [(0, 0), (0.15, 10), (0.3, -6), (0.4, 0)])
		f = seq(t, [(0.25, 0), (0.85, 1)])
		return merge_scaled({"hips": {"loc": (0, 0, -0.6 * f), "scale": (1 + 0.4 * f, 1 + 0.4 * f, 1 - 0.5 * f)},
							 "chest": {"rot": (reel - 30 * f, 0, 8 * f), "loc": (0, 0.1 * f, -0.3 * f), "scale": (1 + 0.2 * f, 1 + 0.2 * f, 1 - 0.4 * f)},
							 "head": {"rot": (-30 * f, 0, 20 * f)},
							 "leg_l": {"rot": (0, 50 * f, 0), "scale": (1, 1, 1 - 0.5 * f)}, "leg_r": {"rot": (0, -50 * f, 0), "scale": (1, 1, 1 - 0.5 * f)}},
							arms(-30 * f + reel, -20 * f - reel, 22 * f, 0))

	clip_scaled(arm, "idle", 3.4, idle, True)
	clip_scaled(arm, "walk", 1.8, walk, True)
	clip_scaled(arm, "run", 1.1, run, True)
	clip_scaled(arm, "attack", 1.5, attack, False)
	clip_scaled(arm, "hit", 0.55, hit, False)
	clip_scaled(arm, "death", 2.0, death, False)
	return arm


# ---------------------------------------------------------------- Drownfast (the Long Monsoon): the drowned garrison of the Tide Kings, the naga

def tide_materials(kind="tidesworn"):
	p = kind
	return {
		"kelp": material(f"{p}_kelp", "2e5a3a", 0.8),
		"weed": material(f"{p}_weed", "5a7a3a", 0.85),
		"slime": material(f"{p}_slime", "24403a", 0.5),
		"barnacle": material(f"{p}_barnacle", "d0cab4", 0.7),
		"hole": material(f"{p}_hole", "2e2a26", 0.8),
		"star": material(f"{p}_star", "d8642a", 0.7),
		"star_d": material(f"{p}_star_dark", "a03a1a", 0.7),
		"bronze": metal_material(f"{p}_bronze", "8a6a34", 0.45, 0.6),
		"verdi": material(f"{p}_verdigris", "6aa890", 0.7),
		"cloak": material(f"{p}_cloak", "2e5a8a", 0.9),
		"cloak_d": material(f"{p}_cloak_dark", "163258", 0.9),
		"gold": metal_material(f"{p}_gold", "d8b04a", 0.3, 0.7),
		"glow": material(f"{p}_glow", "6ae8ff", 0.2, emit=4.0),
		"coral": material(f"{p}_coral", "e8584a", 0.7),
		"coral_o": material(f"{p}_coral_orange", "f0983a", 0.7),
		"coral_p": material(f"{p}_coral_pink", "e89ab0", 0.7),
		"pearl": material(f"{p}_pearl", "f4f2ea", 0.2, emit=0.4),
		"gem": material(f"{p}_gem", "2ad8c8", 0.1, emit=1.6),
	}


def _starfish(b, loc, normal, r, m):
	n = Vector(normal).normalized()
	side = n.orthogonal().normalized()
	up = n.cross(side)
	c = Vector(loc)
	b.blob((r * 0.7, r * 0.7, r * 0.35), tuple(c), m["star"], "x", segs=(8, 4))
	for k in range(5):
		a = 2 * math.pi * k / 5
		d = side * math.cos(a) + up * math.sin(a)
		b.seg(tuple(c), tuple(c + d * r * 1.3 + n * 0.01), r * 0.32, r * 0.08, m["star"] if k % 2 else m["star_d"], "x", sides=5)


def _coral(b, base, direction, length, m, rng, mat=None, depth=2):
	"""A branching sprig of coral: a stubby trunk that forks twice, knobby tips."""
	d = Vector(direction).normalized()
	a = Vector(base)
	mat = mat or m["coral"]
	tip = a + d * length
	b.seg(tuple(a), tuple(tip), 0.035 * (length / 0.2) ** 0.5, 0.025, mat, "x", sides=5)
	b.blob((0.05, 0.05, 0.05), tuple(tip), mat, "x", segs=(5, 4))
	if depth > 0:
		for s in (1, -1):
			nd = (d + d.orthogonal().normalized() * 0.7 * s + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.3))).normalized()
			_coral(b, tip, nd, length * 0.66, m, rng, mat, depth - 1)


def _tide_barnacles(b, m, rng, spots, size=(0.7, 1.2)):
	for loc, nrm in spots:
		_barnacle(b, loc, nrm, m, rng.uniform(*size))


def _tide_glow_eyes(b, m, z=1.61):
	for s in (1, -1):
		b.blob((0.11, 0.03, 0.13), (0.19 * s, -0.53, z), m["glow"], "x", segs=(8, 5))


def _helm_crust(b, m, rng, weed=True):
	"""Barnacles on the Knight helmet's dome and cheeks, weed trailing off its back rim."""
	c, r = Vector((0, -0.02, 1.76)), Vector((0.58, 0.58, 0.66))
	for k in range(9):
		a, e = rng.uniform(0, 2 * math.pi), rng.uniform(-0.2, 0.9)
		if math.sin(a) < -0.5 and e < 0.5:
			continue   # keep the face clear
		d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
		p = c + Vector((d.x * r.x, d.y * r.y, d.z * r.z))
		_barnacle(b, tuple(p), tuple(d), m, rng.uniform(0.7, 1.2))
	if weed:
		for x, y, ln in ((0.5, 0.2, 0.5), (0.3, 0.46, 0.7), (0.0, 0.54, 0.62), (-0.32, 0.44, 0.74), (-0.52, 0.16, 0.46)):
			_kelp(b, (x, y, 1.42), ln, m["kelp"] if ln > 0.55 else m["weed"], lean=(x * 0.2, 0.2), width=0.05)


def build_tidesworn_helm():
	import random
	rng = random.Random(401)
	m = tide_materials()
	b = Builder("tidesworn_helm")
	_helm_crust(b, m, rng)
	_tide_glow_eyes(b, m)
	return b.build_static()


def build_tidesworn_chest():
	"""Barnacles crusting the breastplate and pauldrons, weed hanging off, a starfish clinging on."""
	import random
	rng = random.Random(403)
	m = tide_materials()
	b = Builder("tidesworn_chest")
	_tide_barnacles(b, m, rng, [((0.2, -0.38, 1.08), (0.2, -1, 0.1)), ((-0.14, -0.4, 0.92), (0, -1, 0)), ((0.46, 0.0, 1.3), (0.6, 0, 0.8)),
								((0.5, 0.12, 1.26), (0.8, 0.3, 0.5)), ((-0.48, -0.06, 1.3), (-0.6, 0, 0.8)), ((0.26, 0.38, 1.1), (0.3, 1, 0.2)),
								((-0.2, 0.4, 0.96), (-0.2, 1, 0)), ((0.06, -0.41, 0.78), (0, -1, -0.2))])
	_starfish(b, (-0.16, -0.39, 1.12), (-0.1, -1, 0.1), 0.1, m)
	for s in (1, -1):
		b.blob((0.34, 0.5, 0.1), (0.36 * s, 0.0, 1.34), m["slime"], "x", rot=(0, 24 * s, 0), segs=(8, 4))
		for y, ln in ((-0.2, 0.44), (0.06, 0.3), (0.26, 0.56)):
			_kelp(b, (0.46 * s, y, 1.3), ln, m["kelp"] if ln > 0.4 else m["weed"], lean=(0.1 * s, 0.1), width=0.045)
	return b.build_static()


def build_tidesworn_hips():
	import random
	rng = random.Random(405)
	m = tide_materials()
	b = Builder("tidesworn_hips")
	for k in range(12):
		a = math.radians(k * 30 + 12)
		x, y = 0.42 * math.cos(a), 0.4 * math.sin(a)
		if abs(x) < 0.16 and y < 0:
			continue
		_kelp(b, (x, y, 0.58), 0.26 + 0.1 * (k % 3), m["kelp"] if k % 2 else m["weed"], lean=(x * 0.15, y * 0.15), width=0.045, parts=2)
	_tide_barnacles(b, m, rng, [((0.36, -0.2, 0.54), (0.8, -0.5, 0)), ((-0.4, 0.1, 0.52), (-1, 0.2, 0))])
	return b.build_static()


def build_tide_knight_helm():
	"""A crest like a fish's dorsal fin raised over the helmet, bronze spines webbed with verdigris,
	a plume of weed streaming back from it, and the drowned glow in the eyes."""
	import random
	rng = random.Random(407)
	m = tide_materials("tide_knight")
	b = Builder("tide_knight_helm")
	_helm_crust(b, m, rng, weed=False)
	spines = []
	for k in range(8):
		u = k / 7
		base = Vector((0, -0.44 + 0.84 * u, 2.3 + 0.2 * math.sin(math.pi * u) - 0.1 * u))
		h = 0.26 + 0.34 * math.sin(math.pi * (0.2 + 0.7 * u))
		tip = base + Vector((0, 0.18 + 0.1 * u, h))
		b.seg(tuple(base), tuple(tip), 0.03, 0.006, m["bronze"], "x", sides=5)
		spines.append((base, tip))
	for (a0, t0), (a1, t1) in zip(spines, spines[1:]):   # the web between the spines, scalloped
		_slab(b, [tuple(a0), tuple(a1), tuple(a1 + (t1 - a1) * 0.8), tuple(a0 + (t0 - a0) * 0.92)], 0.02, m["verdi"])
	b.seg((0, -0.5, 2.26), (0, 0.44, 2.2), 0.06, 0.05, m["bronze"], "x", sides=6)   # the crest's base rail
	for k, (dx, ln) in enumerate(((0.0, 1.0), (0.06, 0.8), (-0.06, 0.9))):
		_kelp(b, (dx, 0.42, 2.2), ln, m["kelp"] if k else m["weed"], lean=(dx, 0.5), width=0.05, parts=4)
	_tide_glow_eyes(b, m)
	return b.build_static()


def build_tide_knight_cloak():
	"""A tattered sea-blue cloak falling from the pauldrons nearly to the ground, torn into strips."""
	import random
	rng = random.Random(409)
	m = tide_materials("tide_knight")
	b = Builder("tide_knight_cloak")
	for s in (1, -1):
		b.blob((0.4, 0.46, 0.14), (0.38 * s, 0.06, 1.34), m["cloak_d"], "x", rot=(0, 24 * s, 0), segs=(10, 5))
	b.seg((-0.46, 0.2, 1.3), (0.46, 0.2, 1.3), 0.05, 0.05, m["gold"], "x", sides=6)
	for k in range(9):
		u = (k + 0.5) / 9
		x0 = -0.5 + 1.0 * u
		w = 0.06
		ln = rng.uniform(0.85, 1.12)
		top = Vector((x0, 0.26 + 0.1 * (1 - abs(x0) * 2) ** 2 * 0.3, 1.3))
		tip = top + Vector((x0 * 0.25, 0.14, -ln))
		_slab(b, [tuple(top + Vector((-w, 0, 0))), tuple(top + Vector((w, 0, 0))), tuple(tip + Vector((w * 0.6, 0, 0))),
				  tuple(tip + Vector((-w * 0.8, 0, 0.05)))], 0.03, (m["cloak"], m["cloak_d"])[k % 2])
	for k in range(4):
		_kelp(b, (rng.uniform(-0.4, 0.4), 0.34, 1.0), rng.uniform(0.2, 0.4), m["kelp"], width=0.04, parts=2)
	return b.build_static()


def build_tideking_crown():
	"""A tall crown of gold overgrown with coral branching red, orange and pink, pearls set among it;
	weed for hair, a beard of kelp and the sea-blue glow of the last Tide King's eyes."""
	import random
	rng = random.Random(411)
	m = tide_materials("tideking")
	b = Builder("tideking_crown")
	c = (0, -0.02, 1.98)
	_arc(b, c, (0.52, 0.5), 0, 360, 0.065, m["gold"], sides=22)
	_arc(b, (c[0], c[1], c[2] + 0.1), (0.53, 0.51), 0, 360, 0.045, m["gold"], sides=22)
	for k in range(8):   # gold points, with coral grown over them
		a = math.radians(-90 + 45 * k)
		p = Vector((0.53 * math.cos(a), c[1] + 0.51 * math.sin(a), c[2] + 0.08))
		h = 0.44 if k == 0 else (0.32 if k % 2 == 0 else 0.24)
		tip = p + Vector((0.06 * math.cos(a), 0.06 * math.sin(a), h))
		b.seg(tuple(p), tuple(tip), 0.06, 0.012, m["gold"], "x", sides=5)
		if k % 2 == 0:
			b.blob((0.08, 0.06, 0.08), tuple(p + Vector((0.03 * math.cos(a), 0.03 * math.sin(a), 0.06))), m["gem"] if k == 0 else m["pearl"], "x", segs=(8, 5))
		out = Vector((math.cos(a), math.sin(a), 0))
		_coral(b, p + out * 0.02 + Vector((0, 0, 0.02)), out * 0.6 + Vector((rng.uniform(-0.3, 0.3), 0, 1)), rng.uniform(0.14, 0.22), m, rng,
			   (m["coral"], m["coral_o"], m["coral_p"])[k % 3], depth=1 + (k % 2))
	for k in range(6):
		a = rng.uniform(0, 2 * math.pi)
		_barnacle(b, (0.53 * math.cos(a), c[1] + 0.51 * math.sin(a), c[2] - 0.03), (math.cos(a), math.sin(a), 0.2), m, 0.8)
	for x, y, ln in ((0.5, -0.1, 0.62), (0.5, 0.16, 0.8), (0.34, 0.4, 0.9), (0.08, 0.5, 0.96), (-0.2, 0.46, 0.9), (-0.44, 0.26, 0.84),
					 (-0.52, -0.02, 0.66)):
		_kelp(b, (x, y, 1.98), ln, m["kelp"] if ln > 0.8 else m["weed"], lean=(x * 0.15, 0.2), width=0.055)
	for x in (-0.16, -0.06, 0.06, 0.16):   # a beard of kelp
		_kelp(b, (x, -0.46, 1.4), 0.34 + 0.06 * (1 - abs(x) * 4), m["kelp"], lean=(x * 0.2, -0.1), width=0.05, parts=3)
	_tide_glow_eyes(b, m)
	return b.build_static()


def build_tideking_mantle():
	"""A royal mantle: a high collar of sea-blue and gold, a long cloak to the heels, coral grown over the
	shoulders and a gold chain with a pearl medallion."""
	import random
	rng = random.Random(413)
	m = tide_materials("tideking")
	b = Builder("tideking_mantle")
	_shell(b, (1.2, 1.1, 0.44), (0, 0.06, 1.22), m["cloak"], lambda d: d.z > -0.05 and not (d.y < -0.4 and abs(d.x) < 0.6))
	_arc(b, (0, 0.06, 1.21), (0.6, 0.55), -40, 220, 0.04, m["gold"], sides=22)
	for s in (1, -1):   # the high collar standing up behind the head
		_slab(b, [(0.12 * s, 0.34, 1.34), (0.46 * s, 0.24, 1.36), (0.62 * s, 0.3, 1.8), (0.2 * s, 0.44, 1.76)], 0.04, m["cloak_d"])
		b.seg((0.46 * s, 0.24, 1.36), (0.62 * s, 0.3, 1.8), 0.025, 0.02, m["gold"], "x", sides=4)
		for k in range(3):
			_coral(b, (0.42 * s, rng.uniform(-0.12, 0.2), 1.42), (0.5 * s, rng.uniform(-0.3, 0.3), 1), 0.14, m, rng,
				   (m["coral"], m["coral_o"], m["coral_p"])[k], depth=1)
	for k in range(9):   # the long cloak, falling in folds to the heels
		u = (k + 0.5) / 9
		x0 = -0.54 + 1.08 * u
		w = 0.07
		ln = 1.18 + 0.04 * math.sin(k * 2.1)
		top = Vector((x0, 0.32 + 0.04 * (k % 2), 1.3))
		tip = top + Vector((x0 * 0.3, 0.26, -ln))
		_slab(b, [tuple(top + Vector((-w, 0, 0))), tuple(top + Vector((w, 0, 0))), tuple(tip + Vector((w, 0, 0))), tuple(tip + Vector((-w, 0, 0)))],
			  0.035, (m["cloak"], m["cloak_d"])[k % 2])
	b.seg((-0.62, 0.52, 0.14), (0.62, 0.52, 0.14), 0.035, 0.035, m["gold"], "x", sides=5)   # its gold hem
	pts = _arc(b, (0, -0.02, 1.26), (0.38, 0.4), 200, 340, 0.022, m["gold"], sides=10, lift=0.0)
	b.blob((0.2, 0.08, 0.2), (0, -0.44, 1.02), m["gold"], "x", segs=(10, 6))
	b.blob((0.12, 0.06, 0.12), (0, -0.48, 1.02), m["pearl"], "x", segs=(8, 5))
	for s in (1, -1):
		b.seg((0.3 * s, -0.36, 1.2), (0.05 * s, -0.44, 1.08), 0.02, 0.02, m["gold"], "x", sides=4)
	return b.build_static()


# --- the naga: the Rogue's upper body on a serpent's tail, a snake's head in a hood

NAGA_SKINS = {
	"naga": {"skin": "4e9e82", "dark": "1e4e40", "belly": "d8d2a0", "pattern": "2a6a54", "hood_in": "9ccaa8", "eye": "f4d02a"},
	"naga_tidecaller": {"skin": "3a5ea8", "dark": "142a5a", "belly": "c8d8e8", "pattern": "1a2e6a", "hood_in": "9ab4e4", "eye": "ffe070"},
	"naga_queen": {"skin": "3aa892", "dark": "145a4e", "belly": "f0e4b0", "pattern": "1e6a5a", "hood_in": "b8e0c8", "eye": "ffb830"},
}


def naga_materials(kind):
	c = NAGA_SKINS[kind]
	return {
		"skin": material(f"{kind}_skin", c["skin"], 0.45),
		"dark": material(f"{kind}_dark", c["dark"], 0.5),
		"belly": material(f"{kind}_belly", c["belly"], 0.6),
		"pattern": material(f"{kind}_pattern", c["pattern"], 0.5),
		"hood_in": material(f"{kind}_hood_in", c["hood_in"], 0.6),
		"eye": material(f"{kind}_eye", c["eye"], 0.2, emit=1.2),
		"pupil": material(f"{kind}_pupil", "0a0806", 0.2),
		"mouth": material(f"{kind}_mouth", "3a1216", 0.8),
		"tongue": material(f"{kind}_tongue", "c8303a", 0.5),
		"fang": material(f"{kind}_fang", "f4eee0", 0.3),
		"gold": metal_material(f"{kind}_gold", "e0b440", 0.3, 0.7),
		"gem": material(f"{kind}_gem", "e83a5a" if kind == "naga_queen" else "2ad8c8", 0.1, emit=1.6),
		"pearl": material(f"{kind}_pearl", "f4f2ea", 0.2, emit=0.3),
		"bronze": metal_material(f"{kind}_bronze", "9a7236", 0.4, 0.6),
	}


def _naga_head(b, m, kind):
	"""A snake's head on a thick neck, a hood spread behind it: narrow for the warriors, a broad cobra's
	for the tidecallers, broadest for the queen."""
	hood_w = {"naga": 0.92, "naga_tidecaller": 1.2, "naga_queen": 1.3}[kind]
	hood_h = {"naga": 0.96, "naga_tidecaller": 1.04, "naga_queen": 1.1}[kind]
	b.seg((0, 0.04, 1.16), (0, -0.06, 1.56), 0.21, 0.18, m["skin"], "x", sides=12)                      # the neck
	b.seg((0, -0.1, 1.16), (0, -0.18, 1.5), 0.13, 0.11, m["belly"], "x", sides=10)                        # its pale throat
	# the hood: dark behind, pale and patterned in front, the head in front of it
	hc = Vector((0, 0.08, 1.52))
	_oblob(b, (hood_w, hood_h, 0.1), tuple(hc), (0, 0.25, 1), (0, -1, 0.25), m["skin"], "x", segs=(16, 8))
	_oblob(b, (hood_w * 0.86, hood_h * 0.84, 0.06), tuple(hc + Vector((0, -0.045, -0.02))), (0, 0.25, 1), (0, -1, 0.25), m["hood_in"], "x", segs=(14, 6))
	for k in range(9):   # dark scale bands round the hood's rim
		a = math.radians(-80 + 160 * k / 8)
		d = Vector((math.sin(a) * hood_w * 0.42, 0.02, math.cos(a) * hood_h * 0.4))
		base = hc + Vector((0, -0.07, -0.04))
		b.seg(tuple(base + d * 0.62), tuple(base + d), 0.02, 0.012, m["pattern"], "x", sides=4)
	if kind != "naga":   # a cobra's spectacle marks
		for s in (1, -1):
			_oblob(b, (0.2, 0.2, 0.02), tuple(hc + Vector((0.3 * s * hood_w, -0.08, 0.08))), (0, 0.25, 1), (0, -1, 0.25), m["dark"], "x", segs=(10, 4))
			_oblob(b, (0.1, 0.1, 0.025), tuple(hc + Vector((0.3 * s * hood_w, -0.09, 0.08))), (0, 0.25, 1), (0, -1, 0.25), m["hood_in"], "x", segs=(8, 3))
	# the head
	b.blob((0.52, 0.62, 0.36), (0, -0.2, 1.66), m["skin"], "x", segs=(14, 9))
	b.blob((0.4, 0.44, 0.26), (0, -0.46, 1.62), m["skin"], "x", segs=(12, 8))                          # the snout
	b.blob((0.4, 0.58, 0.14), (0, -0.32, 1.5), m["belly"], "x", segs=(12, 6))                          # the lower jaw
	_arc(b, (0, -0.26, 1.54), (0.25, 0.42), 200, 340, 0.018, m["mouth"], sides=12)
	for s in (1, -1):
		b.blob((0.2, 0.14, 0.1), (0.18 * s, -0.36, 1.8), m["skin"], "x", rot=(0, 14 * s, 0), segs=(8, 5))   # brow ridges
		b.blob((0.13, 0.12, 0.12), (0.21 * s, -0.38, 1.73), m["eye"], "x", segs=(8, 6))
		b.blob((0.025, 0.05, 0.1), (0.26 * s, -0.4, 1.73), m["pupil"], "x", segs=(5, 3))                  # slit pupils
		b.blob((0.03, 0.03, 0.02), (0.07 * s, -0.66, 1.64), m["pupil"], "x", segs=(5, 3))                 # nostrils
		b.seg((0.1 * s, -0.58, 1.54), (0.1 * s, -0.6, 1.4), 0.03, 0.003, m["fang"], "x", sides=5)        # fangs
	for k, (x, y) in enumerate(((0, -0.32), (0, -0.12), (0.14, -0.22), (-0.14, -0.22), (0, 0.06))):   # scale plates on the crown
		p, n = _on_dome((0, -0.2, 1.66), (0.26, 0.31, 0.18), x, y, 0.005)
		_oblob(b, (0.13, 0.13, 0.03), tuple(p), (0, 1, 0), tuple(n), m["pattern"], "x", segs=(6, 4))
	b.seg((0, -0.6, 1.5), (0, -0.78, 1.46), 0.018, 0.014, m["tongue"], "x", sides=4)                   # the forked tongue
	for s in (1, -1):
		b.seg((0, -0.78, 1.46), (0.04 * s, -0.86, 1.44), 0.014, 0.004, m["tongue"], "x", sides=4)
	if kind == "naga":   # a bronze band on the brow
		_arc(b, (0, -0.16, 1.76), (0.27, 0.3), 190, 350, 0.03, m["bronze"], sides=10)
	elif kind == "naga_tidecaller":   # gold drops hanging off the hood's rim
		for k in range(9):
			a = math.radians(-80 + 160 * k / 8)
			p = hc + Vector((math.sin(a) * hood_w * 0.48, 0.02, math.cos(a) * hood_h * 0.46))
			b.seg(tuple(p), tuple(p + Vector((0, -0.02, -0.08))), 0.01, 0.01, m["gold"], "x", sides=3)
			b.blob((0.05, 0.04, 0.07), tuple(p + Vector((0, -0.02, -0.1))), m["gold"] if k % 2 else m["gem"], "x", segs=(6, 4))
		b.blob((0.1, 0.05, 0.12), (0, -0.44, 1.84), m["gem"], "x", segs=(8, 5))
		_arc(b, (0, -0.2, 1.8), (0.25, 0.28), 200, 340, 0.022, m["gold"], sides=10)
	else:   # a jeweled crown over the head and a gold rim to the hood
		start_pts = []
		for k in range(15):
			a = math.radians(-84 + 168 * k / 14)
			start_pts.append(tuple(hc + Vector((math.sin(a) * hood_w * 0.5, 0.0, math.cos(a) * hood_h * 0.5))))
		for p, q in zip(start_pts, start_pts[1:]):
			b.seg(p, q, 0.028, 0.028, m["gold"], "x", sides=5)
		c = (0, -0.18, 1.8)
		_arc(b, c, (0.24, 0.28), 0, 360, 0.035, m["gold"], sides=18)
		for k in range(7):
			a = math.radians(-90 + 51.4 * k)
			p = Vector((0.24 * math.cos(a), c[1] + 0.28 * math.sin(a), c[2]))
			h = 0.34 if k == 0 else (0.22 if k in (1, 6) else 0.16)
			b.seg(tuple(p), tuple(p + Vector((0.03 * math.cos(a), 0.03 * math.sin(a), h))), 0.04, 0.006, m["gold"], "x", sides=5)
			b.blob((0.06, 0.05, 0.06), tuple(p + Vector((0, 0, 0.04))), m["gem"] if k % 2 == 0 else m["pearl"], "x", segs=(6, 4))
		b.blob((0.12, 0.08, 0.14), (0, -0.46, 1.96), m["gem"], "x", segs=(8, 6))
		for s in (1, -1):   # pearl strands along the hood
			for k in range(5):
				b.blob((0.05, 0.05, 0.05), tuple(hc + Vector((0.36 * s * hood_w * (1 - 0.1 * k), -0.1, 0.3 - 0.14 * k))), m["pearl"], "x", segs=(6, 4))


def _naga_build_head(kind):
	b = Builder(f"{kind}_head")
	_naga_head(b, naga_materials(kind), kind)
	return b.build_static()


def _naga_tail(kind):
	"""The serpent half, from the hips (legs hidden) down to the ground and round behind in a loose coil."""
	m = naga_materials(kind)
	b = Builder(f"{kind}_tail")
	k = 1.15 if kind == "naga_queen" else 1.0
	pts = [(0, 0.0, 0.5, 0.31), (0, -0.06, 0.3, 0.29), (0.08, 0.0, 0.25, 0.25), (0.34, 0.24, 0.22, 0.22), (0.44, 0.58, 0.19, 0.19),
		   (0.26, 0.9, 0.16, 0.16), (-0.1, 1.02, 0.13, 0.13), (-0.4, 0.84, 0.1, 0.1), (-0.46, 0.54, 0.07, 0.07), (-0.34, 0.36, 0.1, 0.045),
		   (-0.2, 0.32, 0.2, 0.02)]
	pts = [(x * k, y * k, z if i < 2 else r * k, r * k) for i, (x, y, z, r) in enumerate(pts)]
	b.blob((0.74 * k, 0.64 * k, 0.4), (0, 0.0, 0.5), m["skin"], "x", segs=(14, 9))
	for i, ((x0, y0, z0, r0), (x1, y1, z1, r1)) in enumerate(zip(pts, pts[1:])):
		b.seg((x0, y0, z0), (x1, y1, z1), r0, r1, m["skin"], "x", sides=12)
		b.blob((r1 * 2, r1 * 2, r1 * 2), (x1, y1, z1), m["skin"], "x", segs=(12, 8))
		# a pale belly band along the inner side, dark diamonds down the back
		mid = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
		rm = (r0 + r1) / 2
		if i >= 1:
			d = Vector((x1 - x0, y1 - y0, 0)).normalized()
			_oblob(b, (rm * 0.9, (Vector((x1, y1, z1)) - Vector((x0, y0, z0))).length * 0.8, 0.04), tuple(mid + Vector((0, 0, rm * 0.96))),
				   tuple(d), (0, 0, 1), m["pattern"], "x", segs=(4, 3))
			side = Vector((-d.y, d.x, 0))
			_oblob(b, (rm * 0.9, (Vector((x1, y1, z1)) - Vector((x0, y0, z0))).length * 0.9, 0.04), tuple(mid + side * rm * 0.92 - Vector((0, 0, rm * 0.2))),
				   tuple(d), tuple(side), m["belly"], "x", segs=(6, 3))
	# a skirt of overlapping scales where the torso meets the tail
	for j in range(14):
		a = 2 * math.pi * j / 14
		out = Vector((math.cos(a), math.sin(a), 0))
		p = Vector((0.4 * k * math.cos(a), 0.34 * k * math.sin(a), 0.6))
		_oblob(b, (0.18, 0.22, 0.04), tuple(p + out * 0.02), (0, 0, -1), tuple(out + Vector((0, 0, 0.3))), m["dark"] if j % 2 else m["pattern"], "x", segs=(6, 4))
	if kind != "naga":   # gold rings round the tail
		for i in (3, 5, 7):
			x, y, z, r = pts[i]
			nx, ny = pts[i + 1][0] - x, pts[i + 1][1] - y
			ang = math.degrees(math.atan2(ny, nx))
			start = len(b.parts)
			_ring(b, (0, 0, 0), (r * 1.02, r * 1.02), (0, 0), 0.025, m["gold"], sides=12)
			rot = Matrix.Translation((x, y, z)) @ Euler((0, math.radians(90), math.radians(ang))).to_matrix().to_4x4()
			for p in b.parts[start:]:
				p.data.transform(rot)
	return b.build_static()


def _naga_armband(kind, s):
	m = naga_materials(kind)
	b = Builder(f"{kind}_armband_{'l' if s > 0 else 'r'}")
	for dx in (0.34, 0.4):
		start = len(b.parts)
		_ring(b, (0, 0, 0), (0.13, 0.13), (0, 0), 0.022, m["gold"], sides=12)
		rot = Matrix.Translation((dx * s, 0, 1.11)) @ Euler((0, math.radians(90), 0)).to_matrix().to_4x4()
		for p in b.parts[start:]:
			p.data.transform(rot)
	b.blob((0.06, 0.08, 0.08), (0.37 * s, -0.12, 1.11), m["gem"], "x", segs=(6, 4))
	return b.build_static()


def _naga_jewels(kind):
	"""A broad gold collar of plates and gems over the chest."""
	m = naga_materials(kind)
	b = Builder(f"{kind}_jewels")
	queen = kind == "naga_queen"
	for k in range(13):
		a = math.radians(200 + 140 * k / 12)
		p = Vector((0.38 * math.cos(a), 0.36 * math.sin(a), 1.24))
		out = Vector((math.cos(a), math.sin(a), 0))
		_oblob(b, (0.12, 0.18 if not queen else 0.22, 0.03), tuple(p + out * 0.04 + Vector((0, 0, -0.07))), (0, 0, 1), tuple(out + Vector((0, 0, 0.8))),
			   m["gold"], "x", segs=(6, 4))
		if k % 2 == 0:
			b.blob((0.06, 0.04, 0.06), tuple(p + out * 0.09 + Vector((0, 0, -0.12 if not queen else -0.15))), m["gem"], "x", segs=(6, 4))
	b.blob((0.14, 0.06, 0.16), (0, -0.44, 1.02 if not queen else 0.96), m["gold"], "x", segs=(8, 5))
	b.blob((0.09, 0.05, 0.1), (0, -0.47, 1.02 if not queen else 0.96), m["gem"], "x", segs=(8, 5))
	return b.build_static()


# the tidesworn: the Knight in corroded, verdigrised bronze; armor (3,0) (7,0) (2,1) (3,1) (1,2) (4,2) (5,2), darks (4,0) (7,1),
# whites (1,1) (0,2), cape (0,1) (2,2), gold (4,1), leathers (5,0) (6,0) (5,1) (6,1) (3,2), skin (0,0), hair (1,0), eyes (2,0)
def _tide_cells(armor, dark, cape, gold, skin=("98aa98", "48584e")):
	cells = {c: armor for c in ((3, 0), (7, 0), (2, 1), (3, 1), (1, 2), (4, 2), (5, 2))}
	cells.update({c: dark for c in ((4, 0), (7, 1))})
	cells.update({c: cape for c in ((0, 1), (2, 2))})
	cells.update({c: ("c8d8c4", "7a8a78") for c in ((1, 1), (0, 2))})
	cells.update({c: ("4a3a2a", "141008") for c in ((5, 0), (6, 0), (5, 1), (6, 1), (3, 2))})
	cells[(4, 1)] = gold
	cells[(0, 0)] = skin
	cells[(1, 0)] = ("3a4a2a", "101808")
	cells[(2, 0)] = ("d0f4ff", "5a8a9a")
	return cells


TIDESWORN_CELLS = _tide_cells(("9cbc9a", "4a3a1c"), ("3e5a4a", "101a14"), ("3e6a60", "0e2420"), ("b0983e", "4a3a10"))
TIDE_KNIGHT_CELLS = _tide_cells(("8aa088", "2e2410"), ("2a3e38", "0a1210"), ("3a6aa8", "0e1a3a"), ("c8a848", "5a4010"))
TIDEKING_CELLS = _tide_cells(("e0c878", "6a4a18"), ("3a4a5a", "0e141c"), ("2e56a0", "0a1432"), ("f4d468", "9a6a14"),
							 skin=("a8bcb4", "54665e"))
# the naga: the Rogue in scales: skin (0,0) and gloves (7,2), tunic (0,1), belt and bracers (5,0), buckles (3,0) (6,0), trousers (7,1)
NAGA_CELLS = {(0, 0): ("5aae90", "1e4e40"), (7, 2): ("5aae90", "1e4e40"), (0, 1): ("c09a50", "4a3214"), (5, 0): ("8a6a34", "3a2810"),
			  (3, 0): ("e0b848", "7a5210"), (6, 0): ("e0b848", "7a5210"), (7, 1): ("4e9e82", "1e4e40"), (1, 0): ("2a6a54", "0e2a20")}
NAGA_TIDECALLER_CELLS = {(0, 0): ("4a70bc", "142a5a"), (7, 2): ("4a70bc", "142a5a"), (0, 1): ("3a3a7a", "10102a"), (5, 0): ("e0b440", "7a5210"),
						 (3, 0): ("e0b440", "7a5210"), (6, 0): ("e0b440", "7a5210"), (7, 1): ("3a5ea8", "142a5a"), (1, 0): ("1a2e6a", "0a1230")}
NAGA_QUEEN_CELLS = {(0, 0): ("4abca2", "145a4e"), (7, 2): ("4abca2", "145a4e"), (0, 1): ("1e7a6a", "062420"), (5, 0): ("f0c850", "8a5a10"),
					(3, 0): ("f0c850", "8a5a10"), (6, 0): ("f0c850", "8a5a10"), (7, 1): ("3aa892", "145a4e"), (1, 0): ("1e6a5a", "08241e")}


# --- Drownfast beasts: tempest spirits and their bound warden, causeway crabs, the shellback

def build_tempest_spirit(name="tempest_spirit", warden=False):
	"""A storm spirit: a column of dark cloud turning on itself, tapering to a funnel above the ground,
	a white-hot lightning core burning through the gaps in its chest, arms of cloud crackling with bolts
	that fork into claws. The stormbound warden is the same spirit wearing the broken bronze of the Tide
	Kings' wardens, chained at the wrists and waist."""
	import random
	rng = random.Random(503 if warden else 501)
	dark = material(f"{name}_cloud_dark", "353b4a", 0.9)
	mid = material(f"{name}_cloud", "535b6c", 0.9)
	light = material(f"{name}_cloud_light", "7e889c", 0.9, emit=0.1)
	core = material(f"{name}_core", "e8f4ff", 0.2, emit=6.0)
	core_b = material(f"{name}_core_blue", "7ac8ff", 0.2, emit=3.5)
	bolt = material(f"{name}_bolt", "b8e4ff", 0.2, emit=4.0)
	eye = material(f"{name}_eye", "f0faff", 0.1, emit=6.0)
	b = Builder(name)
	b.bone("root", (0, 0, 0.1))
	b.bone("low", (0, 0, 0.3), "root")
	b.bone("swirl", (0, 0, 0.3), "low")
	b.bone("mid", (0, 0, 0.95), "low")
	b.bone("core", (0, -0.04, 1.4), "mid")
	b.bone("chest", (0, 0, 1.5), "mid")
	b.bone("head", (0, -0.06, 2.0), "chest")

	def puff(loc, r, bone, mats=(dark, mid, light), n=3):
		for k in range(n):
			off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 0.6))) * r * 0.45
			sz = r * rng.uniform(0.75, 1.15)
			b.blob((sz, sz, sz * 0.85), tuple(Vector(loc) + off), mats[(k + int(r * 10)) % len(mats)], bone, segs=(9, 6))

	# the funnel: two helices of cloud puffs narrowing to a point just off the ground (on the swirl bone)
	for h in range(2):
		for k in range(11):
			u = k / 10
			a = 2 * math.pi * (h / 2 + u * 1.5)
			rr = 0.08 + 0.3 * u
			z = 0.24 + 0.9 * u
			puff((rr * math.cos(a), rr * math.sin(a), z), 0.14 + 0.26 * u, "swirl", n=2)
	b.seg((0, 0, 0.12), (0, 0, 1.0), 0.02, 0.3, dark, "low", sides=10)                               # the funnel's dark heart
	for k in range(3):   # bolts licking down the funnel
		a = 2 * math.pi * k / 3
		p = Vector((0.2 * math.cos(a), 0.2 * math.sin(a), 0.9))
		_zigzag(b, [tuple(p), tuple(p + Vector((0.06, 0.04, -0.2))), tuple(p + Vector((-0.04, 0.0, -0.36))), tuple(p * 0.4 + Vector((0, 0, 0.35)))], 0.022, bolt, "swirl")
	# the core: a white-hot heart in the chest with bolts branching out of it
	b.blob((0.4, 0.36, 0.5), (0, -0.04, 1.42), core, "core", segs=(12, 9))
	b.blob((0.56, 0.5, 0.7), (0, -0.02, 1.4), core_b, "core", segs=(12, 9))
	for k in range(6):
		a = 2 * math.pi * k / 6 + 0.3
		d = Vector((math.cos(a), math.sin(a) * 0.8, rng.uniform(-0.5, 0.6))).normalized()
		p = Vector((0, -0.04, 1.42))
		_zigzag(b, [tuple(p + d * 0.2), tuple(p + d * 0.36 + Vector((0.04, 0, 0.06))), tuple(p + d * 0.52 - Vector((0.03, 0, 0.04))),
					tuple(p + d * 0.64)], 0.025, bolt, "core")
	# the chest: a ring of heavy cloud round the core, open in front so it shows
	for k in range(14):
		a = 2 * math.pi * (k + 0.5) / 14
		for z in (1.22, 1.52, 1.78):
			rr = 0.46 if z < 1.7 else 0.4
			if math.sin(a) < -0.75 and z < 1.7:
				continue   # the window onto the core
			puff((rr * math.cos(a), rr * 0.85 * math.sin(a), z), 0.3 if z < 1.7 else 0.26, "chest" if z > 1.3 else "mid", n=2)
	for s in (1, -1):   # thunderhead shoulders
		puff((0.56 * s, 0.02, 1.84), 0.38, "chest")
		puff((0.44 * s, 0.16, 1.98), 0.3, "chest")
	# the head: a hooded billow with two white eyes and a crown of sparks
	puff((0, 0.04, 2.08), 0.46, "head", n=4)
	puff((0, 0.16, 2.26), 0.34, "head")
	b.blob((0.4, 0.2, 0.3), (0, -0.2, 2.02), dark, "head", segs=(10, 6))                             # the shadowed face
	for s in (1, -1):
		b.blob((0.12, 0.05, 0.07), (0.1 * s, -0.3, 2.06), eye, "head", rot=(0, 0, -14 * s), segs=(8, 5))
	for k in range(5):
		a = math.radians(-60 + 30 * k)
		base = Vector((0.24 * math.sin(a), -0.02 - 0.2 * math.cos(a), 2.3))
		out = Vector((math.sin(a) * 0.3, -math.cos(a) * 0.2, 1)).normalized()
		tall = 0.36 if k == 2 else 0.24
		side = Vector((math.cos(a), math.sin(a), 0)) * 0.05
		_zigzag(b, [tuple(base), tuple(base + out * tall * 0.4 + side), tuple(base + out * tall * 0.6 - side), tuple(base + out * tall)], 0.03, bolt, "head")
	# arms of cloud with bolts running down them, hands forking into lightning claws
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"arm_{side}", (0.56 * s, 0, 1.78), "chest")
		b.bone(f"hand_{side}", (0.78 * s, -0.08, 1.18), f"arm_{side}")
		for k in range(4):
			u = k / 3
			puff((s * (0.6 + 0.16 * u), -0.08 * u, 1.72 - 0.5 * u), 0.3 - 0.06 * u, f"arm_{side}", n=2)
		_zigzag(b, [(0.62 * s, -0.2, 1.7), (0.7 * s, -0.24, 1.52), (0.64 * s, -0.22, 1.42), (0.76 * s, -0.24, 1.26)], 0.028, bolt, f"arm_{side}")
		puff((0.8 * s, -0.1, 1.06), 0.28, f"hand_{side}", n=3)
		for k in range(4):   # forked lightning claws
			a = math.radians(-50 + 33 * k)
			root = Vector((0.8 * s, -0.16, 0.96))
			d = Vector((0.3 * math.sin(a) * s, -0.5 * math.cos(a), -0.8)).normalized()
			pts = [root, root + d * 0.14 + Vector((0.04 * s, 0, 0)), root + d * 0.26 - Vector((0.03 * s, 0, 0)), root + d * 0.4]
			_zigzag(b, [tuple(p) for p in pts], 0.03, bolt, f"hand_{side}")
			b.blob((0.06, 0.06, 0.06), tuple(pts[-1]), core, f"hand_{side}", segs=(6, 4))
	if warden:
		bronze = metal_material(f"{name}_bronze", "9a7434", 0.45, 0.6)
		verdi = material(f"{name}_verdigris", "5e9a84", 0.7)
		iron = metal_material(f"{name}_iron", "4a4a50", 0.5, 0.6)
		# a cracked breastplate hanging over the core, half of it gone
		_oblob(b, (0.62, 0.7, 0.1), (0.1, -0.46, 1.62), (0, 0, 1), (0, -1, 0.1), bronze, "chest", segs=(12, 6))
		_oblob(b, (0.3, 0.36, 0.11), (0.24, -0.47, 1.66), (0, 0, 1), (0.2, -1, 0.1), verdi, "chest", segs=(8, 5))
		_zigzag(b, [(-0.16, -0.52, 1.9), (-0.06, -0.53, 1.74), (-0.14, -0.53, 1.6), (-0.04, -0.52, 1.36)], 0.02, core_b, "chest")   # the break
		for s in (1, -1):   # pauldrons, the left one broken off short
			sz = (0.58, 0.62, 0.3) if s > 0 else (0.42, 0.46, 0.26)
			_oblob(b, sz, (0.62 * s, 0.0, 2.06), (0, 1, 0), (0.5 * s, 0, 1), bronze, "chest", segs=(12, 7))
			_oblob(b, (sz[0] * 0.7, sz[1] * 0.3, 0.1), (0.66 * s, -0.12, 2.16), (0, 1, 0), (0.5 * s, 0, 1), verdi, "chest", segs=(8, 4))
			b.seg((0.7 * s, 0.0, 2.2), (0.9 * s, 0.04, 2.5), 0.07, 0.0, bronze, "chest", sides=5)
		# a horned helm fragment on the brow
		_arc(b, (0, 0.02, 2.14), (0.34, 0.34), 190, 350, 0.06, bronze, sides=10, bone="head")
		for s in (1, -1):
			horn = [(0.3 * s, -0.1, 2.2), (0.46 * s, -0.06, 2.4), (0.52 * s, 0.06, 2.6)]
			b.seg(horn[0], horn[1], 0.07, 0.05, bronze, "head", sides=6)
			if s > 0:
				b.seg(horn[1], horn[2], 0.05, 0.0, bronze, "head", sides=6)
		for s in (1, -1):   # bronze manacles and broken chains hanging from the wrists
			side = "l" if s > 0 else "r"
			start = len(b.parts)
			_ring(b, (0, 0, 0), (0.2, 0.2), (0, 0), 0.05, bronze, sides=12)
			for p in b.parts[start:]:
				p.data.transform(Matrix.Translation((0.8 * s, -0.1, 1.16)))
			_on_bone(b, start, f"hand_{side}")
			for k in range(5):
				start = len(b.parts)
				_ring(b, (0, 0, 0), (0.06, 0.035), (0, 0), 0.016, iron, sides=8)
				rot = Euler((math.radians(90), 0, math.radians(90 * (k % 2)))).to_matrix().to_4x4()
				for p in b.parts[start:]:
					p.data.transform(Matrix.Translation((0.86 * s, -0.02, 1.08 - 0.09 * k)) @ rot)
				_on_bone(b, start, f"hand_{side}")
		for k in range(16):   # a chain wound round the funnel's waist
			a = 2 * math.pi * k / 16
			start = len(b.parts)
			_ring(b, (0, 0, 0), (0.07, 0.04), (0, 0), 0.018, iron, sides=8)
			rot = Euler((0, math.radians(90 * (k % 2)), a + math.pi / 2)).to_matrix().to_4x4()
			for p in b.parts[start:]:
				p.data.transform(Matrix.Translation((0.44 * math.cos(a), 0.4 * math.sin(a), 1.02 - 0.06 * math.sin(a))) @ rot)
			_on_bone(b, start, "mid")
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, spread * 0.5, 0)}, "hand_r": {"rot": (bend, -spread * 0.5, 0)}}

	def body(t, lean, sway, spin, flicker=0.06):
		f = 1 + flicker * wave(t, 7) * wave(t, 3, 0.2)
		return {"low": {"rot": (lean + 2 * wave(t, 1, 0.25), sway * wave(t), 0)},
				"mid": {"rot": (lean * 0.4, -sway * 0.6 * wave(t, 1, 0.1), 3 * wave(t))},
				"chest": {"rot": (lean * 0.2, -sway * 0.4 * wave(t, 1, 0.2), -3 * wave(t, 1, 0.3))},
				"head": {"rot": (-lean * 0.5 + 3 * wave(t, 1, 0.6), 0, 5 * wave(t, 1, 0.1))},
				"swirl": {"rot": (0, 0, spin * t)}, "core": {"scale": (f, f, f)},
				"root": {"loc": (0, 0, 0.06 * wave(t, 2))}}

	def idle(t):
		return merge_scaled(body(t, 0, 3, 240), arms(6 * wave(t, 1, 0.1), 6 * wave(t, 1, 0.6), 6, 8 + 4 * wave(t)))

	def walk(t):
		return merge_scaled(body(t, -10, 4, 360), arms(14 * wave(t), -14 * wave(t), 6, 12))

	def run(t):
		return merge_scaled(body(t, -20, 5, 480), arms(-34 + 8 * wave(t, 2), -34 - 8 * wave(t, 2), 10, 20))

	def attack(t):   # draws both arms back, the core flaring, then thrusts the lightning claws forward
		thrust = seq(t, [(0, 0), (0.35, -1), (0.5, 1), (0.7, 0.8), (1, 0)])
		back, fwd = max(0.0, -thrust), max(0.0, thrust)
		flare = 1 + 0.35 * seq(t, [(0.3, 0), (0.45, 1), (0.7, 0.4), (1, 0)])
		lean = 10 * back - 18 * fwd
		return merge_scaled({"root": {"loc": (0, 0.26 * fwd - 0.06 * back, 0.05)}, "low": {"rot": (lean * 0.4, 0, 0)},
							 "mid": {"rot": (lean * 0.4, 0, 0)}, "chest": {"rot": (lean * 0.4, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
							 "swirl": {"rot": (0, 0, 480 * t)}, "core": {"scale": (flare, flare, flare)}},
							arms(-30 * back + 88 * fwd, -30 * back + 88 * fwd, 18 * back - 6 * fwd, -14 * fwd))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		f = 1 + 0.3 * k * wave(t, 4)
		return merge_scaled({"low": {"rot": (10 * k, 6 * k, 0)}, "mid": {"rot": (8 * k, 0, 0)}, "head": {"rot": (12 * k, 0, 10 * k)},
							 "swirl": {"rot": (0, 0, 100 * t)}, "core": {"scale": (f, f, f)}, "root": {"loc": (0, -0.1 * k, 0)}},
							arms(-24 * k, -18 * k, 16 * k, -10 * k))

	def death(t):   # the core gutters out and the cloud unravels into a low, spreading mist
		reel = seq(t, [(0, 0), (0.2, 14), (0.35, -10), (0.5, 0)])
		f = seq(t, [(0.25, 0), (0.9, 1)])
		c = max(0.02, 1 + 0.4 * seq(t, [(0, 0), (0.15, 1), (0.3, 0)]) - seq(t, [(0.3, 0), (0.7, 1)]))
		spread = 1 + 0.9 * f
		return merge_scaled({"low": {"rot": (reel, reel * 0.4, 0), "loc": (0, 0, -0.2 * f), "scale": (spread, spread, max(0.1, 1 - 0.8 * f))},
							 "mid": {"rot": (-reel * 0.6, 0, 0), "scale": (1 + 0.3 * f, 1 + 0.3 * f, max(0.2, 1 - 0.7 * f))},
							 "chest": {"scale": (1 + 0.2 * f, 1 + 0.2 * f, max(0.3, 1 - 0.5 * f))},
							 "head": {"rot": (reel + 20 * f, 0, 20 * f), "scale": (1 + 0.3 * f, 1 + 0.3 * f, max(0.3, 1 - 0.6 * f))},
							 "swirl": {"rot": (0, 0, 300 * t)}, "core": {"scale": (c, c, c)}, "root": {"loc": (0, 0, -0.1 * f)}},
							arms(-50 * f + reel, -40 * f - reel, 40 * f, 0))

	clip_scaled(arm, "idle", 3.0, idle, False)
	clip_scaled(arm, "walk", 1.5, walk, False)
	clip_scaled(arm, "run", 0.75, run, False)
	clip_scaled(arm, "attack", 0.9, attack, False)
	clip_scaled(arm, "hit", 0.45, hit, False)
	clip_scaled(arm, "death", 1.6, death, False)
	return arm


def build_stormbound_warden():
	return build_tempest_spirit("stormbound_warden", warden=True)


CRAB_LEGS = {}
for _i, _y in enumerate((-0.3, -0.1, 0.1, 0.28)):
	CRAB_LEGS[f"leg_l{_i + 1}"] = (0.5, _y, _i)
	CRAB_LEGS[f"leg_r{_i + 1}"] = (-0.5, _y, _i)
CRAB_SET_A = ("leg_l1", "leg_r2", "leg_l3", "leg_r4")


def build_causeway_crab(name="causeway_crab", old=False):
	"""A giant crab of the drowned causeway, about as tall as a man's chest: a broad mottled red-brown
	shell crusted with barnacles, eyes on stalks, two heavy claws and eight spiky legs. It scuttles
	half sideways. Old Chitterjaw is the same crab grown colossal: scarred, coral-grown, and still
	carrying the spears of everyone who failed to kill it."""
	import random
	rng = random.Random(521 if old else 511)
	shell = material(f"{name}_shell", "7e3a24" if not old else "6a3a2a", 0.55)
	shell_d = material(f"{name}_shell_dark", "4e1e12" if not old else "3a2018", 0.6)
	shell_l = material(f"{name}_shell_light", "c06a44" if not old else "a0765a", 0.55)
	under = material(f"{name}_under", "dcc4a2", 0.7)
	claw_tip = material(f"{name}_claw_tip", "2a1812", 0.4)
	eye = material(f"{name}_eye", "141010", 0.1)
	glint = material(f"{name}_glint", "ffffff", 0.1, emit=0.8)
	m = {"barnacle": material(f"{name}_barnacle", "d8d2bc", 0.7), "hole": material(f"{name}_hole", "2e2a26", 0.8),
		 "coral": material(f"{name}_coral", "e8584a", 0.7), "coral_o": material(f"{name}_coral_o", "f0983a", 0.7),
		 "coral_p": material(f"{name}_coral_p", "e89ab0", 0.7)}
	b = Builder(name)
	z0 = 0.66
	b.bone("root", (0, 0, z0))
	b.bone("body", (0, 0, z0), "root")
	sc = (0, 0.02, z0 + 0.1)
	sr = (0.72, 0.56, 0.3)
	b.blob((1.52, 1.16, 0.62), sc, shell, "body", segs=(18, 11))                            # the carapace
	b.blob((1.3, 1.0, 0.36), (0, 0.02, z0 - 0.1), under, "body", segs=(16, 8))               # the pale underside
	b.blob((1.5, 1.16, 0.14), (0, 0.02, z0 + 0.02), shell_d, "body", segs=(18, 6))            # the shell's rim
	for k in range(7):   # spines along the front rim
		a = math.radians(210 + 20 * k)
		p = Vector((0.74 * math.cos(a), 0.02 + 0.58 * math.sin(a), z0 + 0.04))
		b.seg(tuple(p), tuple(p + Vector((0.12 * math.cos(a), 0.1 * math.sin(a), 0.04))), 0.04, 0.0, shell_d, "body", sides=4)
	for k in range(16 if not old else 10):   # mottling
		x, y = rng.uniform(-0.56, 0.56), rng.uniform(-0.42, 0.44)
		p, n = _on_dome(sc, sr, x, y, 0.004)
		w = rng.uniform(0.07, 0.16)
		_oblob(b, (w, w * 1.3, 0.03), tuple(p), (rng.uniform(-1, 1), 1, 0), tuple(n), shell_l if k % 3 else shell_d, "body", segs=(8, 4))
	b.seg((0, -0.36, z0 + 0.36), (0, 0.4, z0 + 0.34), 0.03, 0.03, shell_d, "body", sides=4)    # the ridge
	for k in range(7 if not old else 14):   # barnacles
		x, y = rng.uniform(-0.5, 0.5), rng.uniform(-0.1, 0.46)
		p, n = _on_dome(sc, sr, x, y, 0.0)
		_barnacle(b, tuple(p), tuple(n), m, rng.uniform(0.9, 1.4) * (1.2 if old else 1.0))
	_on_bone(b, len(b.parts) - 2 * (7 if not old else 14), "body")
	# eyes on stalks, feelers, mouthparts
	for s in (1, -1):
		b.seg((0.14 * s, -0.46, z0 + 0.14), (0.18 * s, -0.54, z0 + 0.46), 0.04, 0.035, shell, "body", sides=6)
		b.blob((0.12, 0.12, 0.13), (0.18 * s, -0.55, z0 + 0.5), eye, "body", segs=(10, 7))
		b.blob((0.04, 0.03, 0.03), (0.16 * s, -0.6, z0 + 0.54), glint, "body", segs=(5, 3))
		b.seg((0.06 * s, -0.54, z0 + 0.04), (0.2 * s, -0.9, z0 + 0.2), 0.012, 0.004, shell_d, "body", sides=3)
	b.bone("mouth", (0, -0.52, z0 - 0.02), "body")
	b.blob((0.3, 0.12, 0.2), (0, -0.54, z0 - 0.02), shell_d, "mouth", segs=(8, 5))
	for s in (1, -1):
		b.seg((0.06 * s, -0.58, z0), (0.05 * s, -0.62, z0 - 0.14), 0.035, 0.01, shell_l, "mouth", sides=4)
	if old:   # scars, coral grown over the shell and old spears stuck in it
		scar = material(f"{name}_scar", "d8b8a0", 0.8)
		wood = material(f"{name}_wood", "6a5034", 0.9)
		iron = metal_material(f"{name}_iron", "5a5650", 0.6, 0.5)
		for pts in (((-0.4, -0.2), (-0.2, 0.0), (0.0, 0.1)), ((0.3, -0.3), (0.42, 0.0)), ((0.1, 0.3), (0.3, 0.36), (0.44, 0.24))):
			ps = [_on_dome(sc, sr, x, y, 0.006)[0] for x, y in pts]
			for p, q in zip(ps, ps[1:]):
				b.seg(tuple(p), tuple(q), 0.022, 0.022, scar, "body", sides=4)
		start = len(b.parts)
		for k, (x, y) in enumerate(((0.36, 0.16), (-0.3, 0.3), (-0.5, -0.1), (0.1, 0.4))):
			p, n = _on_dome(sc, sr, x, y, 0.0)
			_coral(b, p, n + Vector((0, 0, 0.5)), 0.16, m, rng, (m["coral"], m["coral_o"], m["coral_p"])[k % 3], depth=2)
		for k, (x, y, d, ln, broken) in enumerate(((-0.2, 0.2, (-0.4, 0.5, 1), 1.1, False), (0.24, -0.1, (0.5, -0.2, 1), 0.7, True),
												   (0.44, 0.34, (0.6, 0.6, 0.7), 0.9, False))):
			p, n = _on_dome(sc, sr, x, y, 0.0)
			dv = Vector(d).normalized()
			b.seg(tuple(p - dv * 0.14), tuple(p + dv * ln), 0.028, 0.024, wood, "x", sides=6)
			if broken:
				b.seg(tuple(p + dv * ln), tuple(p + dv * (ln + 0.06) + Vector((0.03, 0, 0))), 0.024, 0.01, wood, "x", sides=4)
			else:
				b.seg(tuple(p + dv * (ln - 0.02)), tuple(p + dv * (ln + 0.08)), 0.03, 0.02, wood, "x", sides=6)   # a lashing
				_barnacle(b, tuple(p + dv * 0.1), tuple(n), m, 0.7)
		_on_bone(b, start, "body")
	# the claws
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		big = 1.12 if (s < 0 and old) else 1.0
		b.bone(f"arm_{side}", (0.34 * s, -0.46, z0 - 0.02), "body")
		b.bone(f"claw_{side}", (0.62 * s, -0.86, z0 + 0.12), f"arm_{side}")
		b.bone(f"finger_{side}", (0.66 * s, -1.26, z0 + 0.16), f"claw_{side}")
		b.seg((0.34 * s, -0.46, z0 - 0.02), (0.72 * s, -0.6, z0 + 0.1), 0.09, 0.085, shell, f"arm_{side}", sides=8)
		b.blob((0.2, 0.2, 0.2), (0.72 * s, -0.6, z0 + 0.1), shell_d, f"arm_{side}", segs=(8, 6))
		b.seg((0.72 * s, -0.6, z0 + 0.1), (0.62 * s, -0.86, z0 + 0.12), 0.09, 0.1, shell, f"arm_{side}", sides=8)
		for k in range(3):
			p = Vector((0.72 * s, -0.66 - 0.06 * k, z0 + 0.18))
			b.seg(tuple(p), tuple(p + Vector((0.04 * s, 0, 0.08))), 0.025, 0.0, shell_d, f"arm_{side}", sides=4)
		b.blob((0.36 * big, 0.54 * big, 0.36 * big), (0.64 * s, -1.06, z0 + 0.14), shell, f"claw_{side}", segs=(12, 9))   # the hand
		b.blob((0.24 * big, 0.36 * big, 0.12), (0.66 * s, -1.06, z0 + 0.28), shell_l, f"claw_{side}", segs=(10, 5))
		b.seg((0.58 * s, -1.24, z0 + 0.1), (0.52 * s, -1.56, z0 + 0.06), 0.1 * big, 0.04, shell, f"claw_{side}", sides=7)   # fixed finger
		b.seg((0.52 * s, -1.56, z0 + 0.06), (0.49 * s, -1.66, z0 + 0.08), 0.04, 0.0, claw_tip, f"claw_{side}", sides=6)
		b.seg((0.66 * s, -1.26, z0 + 0.16), (0.62 * s, -1.56, z0 + 0.24), 0.085 * big, 0.035, shell, f"finger_{side}", sides=7)   # moving finger
		b.seg((0.62 * s, -1.56, z0 + 0.24), (0.56 * s, -1.66, z0 + 0.2), 0.035, 0.0, claw_tip, f"finger_{side}", sides=6)
		for k in range(3):   # knobbly teeth on the inner edges
			b.blob((0.05, 0.05, 0.05), (0.56 * s, -1.34 - 0.08 * k, z0 + 0.12), under, f"claw_{side}", segs=(5, 3))
	# eight legs: up to a high knee, then down to a point
	for name_, (x, y, i) in CRAB_LEGS.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, z0 - 0.02), "body")
		spread = (i - 1.5) * 0.22
		knee = (x + 0.3 * s, y + spread * 0.6, z0 + 0.16)
		ankle = (x + 0.56 * s, y + spread * 1.0, z0 - 0.12)
		foot = (x + 0.64 * s, y + spread * 1.2, 0.0)
		b.seg((x, y, z0 - 0.02), knee, 0.1, 0.085, shell, name_, sides=7)
		b.blob((0.17, 0.17, 0.17), knee, shell_d, name_, segs=(7, 5))
		b.seg(knee, ankle, 0.085, 0.065, shell, name_, sides=7)
		b.blob((0.13, 0.13, 0.13), ankle, shell_d, name_, segs=(7, 5))
		b.seg(ankle, foot, 0.065, 0.01, claw_tip, name_, sides=6)
		for k in range(2):
			p = Vector(knee) + (Vector(ankle) - Vector(knee)) * (0.3 + 0.3 * k)
			b.seg(tuple(p), tuple(p + Vector((0.02 * s, 0, 0.06))), 0.018, 0.0, shell_d, name_, sides=3)
	_scaled(b, 1.12)
	arm = b.build()

	def leg(name_, swing, lift):
		s = 1 if CRAB_LEGS[name_][0] > 0 else -1
		return {name_: {"rot": (0, lift * s, -swing * s)}}

	def claws(open_deg, raise_l=0.0, raise_r=0.0, spread=0.0, open_r=None):
		out = {}
		for s, side, rz in ((1, "l", raise_l), (-1, "r", raise_r)):
			o = open_deg if (side == "l" or open_r is None) else open_r
			out[f"arm_{side}"] = {"rot": (rz, 0, spread * s)}
			out[f"claw_{side}"] = {"rot": (rz * 0.6, 0, -spread * 0.5 * s)}
			out[f"finger_{side}"] = {"rot": (o, 0, 0)}
		return out

	def gait(t, amp, lift, cycles=1):
		out = {}
		for name_ in CRAB_LEGS:
			ph = 0.0 if name_ in CRAB_SET_A else 0.5
			out.update(leg(name_, amp * wave(t, cycles, ph), lift * max(0.0, wave(t, cycles, ph + 0.25))))
		return out

	def idle(t):   # eyes twitching, mouthparts working, claws flexing
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2)), "rot": (0, 1.5 * wave(t), 0)}, "mouth": {"rot": (6 * wave(t, 4), 0, 0)}},
					 claws(10 * max(0.0, wave(t, 2, 0.1)), 6 + 4 * wave(t), 6 + 4 * wave(t, 1, 0.5), 3 * wave(t, 1, 0.5)), gait(t, 2, 0))

	def scuttle(t, amp, lift, yaw, sway):
		# half sideways: the shell is turned off the line of travel and rocks from side to side
		return merge(gait(t, amp, lift, 2), {"root": {"rot": (0, 3 * wave(t, 2), yaw), "loc": (sway * wave(t, 2), 0, 0.02 * abs(wave(t, 2)))}},
					 claws(6, 12 + 4 * wave(t, 2), 12 + 4 * wave(t, 2, 0.5), 6))

	def walk(t):
		return scuttle(t, 18, 22, 28, 0.04)

	def run(t):
		return scuttle(t, 26, 30, 34, 0.06)

	def attack(t):   # rears up on its back legs, claws high and open, and snaps them shut one after the other
		rear = seq(t, [(0, 0), (0.3, 1), (0.7, 0.8), (1, 0)])
		open_l = seq(t, [(0, 0), (0.25, 40), (0.45, 44), (0.52, -4), (0.7, 0)])
		open_r = seq(t, [(0, 0), (0.25, 40), (0.55, 44), (0.62, -4), (0.8, 0)])
		lunge = seq(t, [(0, 0), (0.3, -0.04), (0.5, 0.2), (0.75, 0.14), (1, 0)])
		chop_l = seq(t, [(0.3, 0), (0.45, 28), (0.52, -8), (0.8, 0)])
		chop_r = seq(t, [(0.4, 0), (0.55, 28), (0.62, -8), (0.9, 0)])
		return merge({"root": {"loc": (0, lunge, 0.08 * rear), "rot": (14 * rear, 0, 0)}},
					 claws(open_l, 30 * rear - chop_l, 30 * rear - chop_r, 10 * rear, open_r),
					 {"leg_l1": {"rot": (0, 14 * rear, 0)}, "leg_r1": {"rot": (0, -14 * rear, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.03 * k), "rot": (-6 * k, 6 * k, 0)}}, claws(24 * k, -10 * k, -6 * k, 14 * k),
					 gait(t, 8 * k, 12 * k))

	def death(t):   # a last snap of the claws, then it flips onto its back and the legs curl in
		roll = seq(t, [(0.2, 0), (0.55, 100), (0.72, 176), (0.82, 180)])
		lift = seq(t, [(0.2, 0), (0.45, 0.4), (0.74, -0.34), (0.82, -0.3)])
		curl = seq(t, [(0.3, 0), (0.9, 1)])
		snap = seq(t, [(0, 0), (0.1, 36), (0.2, 0)])
		out = merge({"root": {"loc": (0, 0, lift), "rot": (0, roll, 0)}}, claws(snap + 14 * curl, -26 * curl, -26 * curl, -20 * curl))
		for i, name_ in enumerate(CRAB_LEGS):
			out = merge(out, leg(name_, 6 * wave(t, 5, i * 0.13) * seq(t, [(0.6, 0), (0.8, 1), (1, 0.2)]), -56 * curl))
		return out

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.85, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_old_chitterjaw():
	return build_causeway_crab("old_chitterjaw", old=True)


SHELLBACK_LEGS = {"leg_l1": (0.42, -0.64), "leg_r1": (-0.42, -0.64), "leg_l2": (0.46, -0.36), "leg_r2": (-0.46, -0.36)}


def build_shellback():
	"""A great hermit beast that has made its shell of a fallen column drum from the citadel: fluted
	stone lying on its side, broken at both ends, moss and barnacles over it. Out of its mouth come a
	blue-plated head on eye stalks, a crushing claw bigger than the other and four heavy legs."""
	import random
	rng = random.Random(531)
	stone = material("shellback_stone", "b4ac9a", 0.9)
	stone_d = material("shellback_stone_dark", "7a7466", 0.9)
	stone_l = material("shellback_stone_light", "d0c8b4", 0.85)
	moss = material("shellback_moss", "5e7a36", 0.95)
	moss_b = material("shellback_moss_b", "7e8a3e", 0.95)
	plate = material("shellback_plate", "4e5e76", 0.5)
	plate_d = material("shellback_plate_dark", "2a3446", 0.55)
	joint = material("shellback_joint", "d0884a", 0.6)
	tip = material("shellback_tip", "1e1a18", 0.4)
	eye = material("shellback_eye", "f0c040", 0.2, emit=1.2)
	pupil = material("shellback_pupil", "0e0c0a", 0.2)
	m = {"barnacle": material("shellback_barnacle", "d8d2bc", 0.7), "hole": material("shellback_hole", "2e2a26", 0.8)}
	b = Builder("shellback")
	b.bone("root", (0, 0, 0.8))
	b.bone("shell", (0, 0.4, 0.9), "root")
	b.bone("body", (0, -0.5, 0.72), "root")
	b.bone("head", (0, -0.86, 0.9), "body")
	# the column drum: a fluted stone cylinder lying along the body, its ends broken ragged
	R, L, cy, cz = 0.74, 1.7, 0.42, 0.96
	b.seg((0, cy - L / 2, cz), (0, cy + L / 2, cz), R, R * 0.97, stone, "shell", sides=20)
	for k in range(20):   # the flutes: shallow grooves along its length
		a = 2 * math.pi * (k + 0.5) / 20
		p0 = Vector((R * 1.0 * math.cos(a), cy - L / 2 + 0.06, cz + R * 1.0 * math.sin(a)))
		p1 = Vector((R * 0.97 * math.cos(a), cy + L / 2 - 0.06, cz + R * 0.97 * math.sin(a)))
		b.seg(tuple(p0), tuple(p1), 0.03, 0.03, stone_d, "shell", sides=4)
	for end, sgn in ((cy - L / 2, -1), (cy + L / 2, 1)):   # jagged broken rims
		for k in range(14):
			a = 2 * math.pi * k / 14
			p = Vector((R * math.cos(a), end, cz + R * math.sin(a)))
			h = rng.uniform(0.04, 0.2)
			_rock(b, (0.22, h + 0.08, 0.2), tuple(p + Vector((0, sgn * h * 0.4, 0))), stone_l if k % 3 else stone, "shell", rng, jitter=0.25)
	b.blob((R * 1.7, 0.1, R * 1.7), (0, cy + L / 2 - 0.02, cz), stone_d, "shell", segs=(16, 8))   # the back is stopped with rubble
	# a chunk of the capital still on top, and a broken capital volute
	_rock(b, (0.9, 0.62, 0.3), (0.06, 0.66, cz + R + 0.1), stone_l, "shell", rng, jitter=0.12)
	for s in (1, -1):
		start = len(b.parts)
		_ring(b, (0, 0, 0), (0.14, 0.14), (0, 0), 0.05, stone_l, sides=12)
		for p in b.parts[start:]:
			p.data.transform(Matrix.Translation((0.4 * s, 0.66, cz + R + 0.14)) @ Euler((0, math.radians(90), 0)).to_matrix().to_4x4())
		_on_bone(b, start, "shell")
	for k in range(9):   # moss and weed
		a = rng.uniform(math.radians(20), math.radians(160))
		y = rng.uniform(cy - L / 2 + 0.2, cy + L / 2 - 0.2)
		p = (R * 1.0 * math.cos(a), y, cz + R * 1.0 * math.sin(a))
		b.blob((rng.uniform(0.24, 0.4), rng.uniform(0.26, 0.44), 0.1), p, moss if k % 2 else moss_b, "shell", segs=(8, 5))
	start = len(b.parts)
	for k in range(10):   # barnacles on the lower flanks
		a = rng.uniform(math.radians(-40), math.radians(40)) + (0 if k % 2 else math.pi)
		y = rng.uniform(cy - L / 2 + 0.1, cy + L / 2 - 0.1)
		n = Vector((math.cos(a), 0, math.sin(a)))
		_barnacle(b, (R * math.cos(a), y, cz + R * math.sin(a)), tuple(n), m, rng.uniform(1.0, 1.6))
	for k in range(4):
		x = rng.uniform(-0.5, 0.5)
		_kelp(b, (x, rng.uniform(0, 0.8), cz + math.sqrt(max(0.0, R * R - x * x)) - 0.02), 0.5, moss, lean=(x * 0.4, 0), width=0.045)
	_on_bone(b, start, "shell")
	# the beast in the mouth of the drum: a plated head with eye stalks and feelers
	b.blob((0.86, 0.5, 0.62), (0, -0.46, 0.74), plate_d, "body", segs=(14, 9))                 # the bulk inside the opening
	b.blob((0.6, 0.44, 0.36), (0, -0.8, 0.9), plate, "head", segs=(12, 8))
	b.blob((0.52, 0.2, 0.14), (0, -0.82, 1.08), plate_d, "head", segs=(10, 5))
	for s in (1, -1):
		b.seg((0.12 * s, -0.86, 1.04), (0.16 * s, -0.96, 1.34), 0.045, 0.04, plate, "head", sides=6)
		b.blob((0.13, 0.13, 0.13), (0.16 * s, -0.98, 1.38), eye, "head", segs=(10, 7))
		b.blob((0.05, 0.03, 0.08), (0.17 * s, -1.04, 1.38), pupil, "head", segs=(5, 3))
		b.seg((0.08 * s, -1.0, 0.94), (0.4 * s, -1.6, 1.2), 0.018, 0.004, joint, "head", sides=4)   # feelers
		b.seg((0.04 * s, -1.02, 0.8), (0.07 * s, -1.08, 0.62), 0.04, 0.01, joint, "head", sides=4)   # mouthparts
	# the claws: a small picking claw and a huge crusher
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		big = 1.5 if s < 0 else 1.0
		b.bone(f"arm_{side}", (0.3 * s, -0.7, 0.66), "body")
		b.bone(f"claw_{side}", (0.46 * s, -1.08, 0.62), f"arm_{side}")
		b.bone(f"finger_{side}", (0.48 * s, -1.4 - 0.12 * (big - 1), 0.66), f"claw_{side}")
		b.seg((0.3 * s, -0.7, 0.66), (0.5 * s, -0.9, 0.5), 0.1 * big, 0.09 * big, plate, f"arm_{side}", sides=8)
		b.blob((0.2 * big, 0.2 * big, 0.2 * big), (0.5 * s, -0.9, 0.5), joint, f"arm_{side}", segs=(8, 6))
		b.seg((0.5 * s, -0.9, 0.5), (0.46 * s, -1.08, 0.62), 0.09 * big, 0.1 * big, plate, f"arm_{side}", sides=8)
		b.blob((0.36 * big, 0.5 * big, 0.36 * big), (0.46 * s, -1.24 - 0.06 * (big - 1), 0.62), plate, f"claw_{side}", segs=(12, 9))
		for k in range(3):
			b.blob((0.09 * big, 0.09 * big, 0.07 * big), (0.46 * s + 0.08 * (k - 1), -1.2 - 0.06 * (big - 1), 0.62 + 0.16 * big), plate_d, f"claw_{side}", segs=(6, 4))
		fy = -1.4 - 0.12 * (big - 1)
		b.seg((0.4 * s, fy, 0.56), (0.38 * s, fy - 0.3 * big, 0.54), 0.1 * big, 0.04, plate, f"claw_{side}", sides=7)
		b.seg((0.38 * s, fy - 0.3 * big, 0.54), (0.37 * s, fy - 0.38 * big, 0.58), 0.04, 0.0, tip, f"claw_{side}", sides=6)
		b.seg((0.48 * s, fy, 0.66), (0.46 * s, fy - 0.28 * big, 0.74), 0.09 * big, 0.035, plate, f"finger_{side}", sides=7)
		b.seg((0.46 * s, fy - 0.28 * big, 0.74), (0.44 * s, fy - 0.36 * big, 0.68), 0.035, 0.0, tip, f"finger_{side}", sides=6)
	for name_, (x, y) in SHELLBACK_LEGS.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, 0.6), "root")
		knee = (x + 0.36 * s, y - 0.06, 0.82)
		foot = (x + 0.62 * s, y - 0.1, 0.0)
		b.seg((x, y, 0.6), knee, 0.1, 0.09, plate, name_, sides=7)
		b.blob((0.18, 0.18, 0.18), knee, joint, name_, segs=(7, 5))
		b.seg(knee, foot, 0.09, 0.03, plate, name_, sides=7)
		b.seg((foot[0], foot[1], 0.12), foot, 0.035, 0.005, tip, name_, sides=5)
	arm = b.build()

	def legs(swing_a, swing_b, lift_a=0.0, lift_b=0.0):
		out = {}
		for name_ in SHELLBACK_LEGS:
			s = 1 if SHELLBACK_LEGS[name_][0] > 0 else -1
			a = name_ in ("leg_l1", "leg_r2")
			sw, li = (swing_a, lift_a) if a else (swing_b, lift_b)
			out[name_] = {"rot": (0, li * s, -sw * s)}
		return out

	def claws(open_deg, raise_l=0.0, raise_r=0.0, open_r=None):
		out = {}
		for s, side, rz in ((1, "l", raise_l), (-1, "r", raise_r)):
			o = open_deg if (side == "l" or open_r is None) else open_r
			out[f"arm_{side}"] = {"rot": (rz, 0, 0)}
			out[f"claw_{side}"] = {"rot": (rz * 0.5, 0, 0)}
			out[f"finger_{side}"] = {"rot": (o, 0, 0)}
		return out

	def idle(t):
		return merge({"body": {"loc": (0, -0.02 * max(0.0, wave(t)), 0)}, "head": {"rot": (3 * wave(t, 1, 0.3), 0, 8 * wave(t, 0.5))},
					  "shell": {"rot": (1 * wave(t), 0, 0)}}, claws(8 * max(0.0, wave(t, 2)), 4 * wave(t), 2 * wave(t, 1, 0.4)))

	def walk(t):   # heaves the drum along a step at a time, rocking it
		lift_a, lift_b = max(0.0, wave(t, 1, 0.25)), max(0.0, wave(t, 1, 0.75))
		return merge(legs(18 * wave(t), -18 * wave(t), 20 * lift_a, 20 * lift_b),
					 {"shell": {"rot": (2 * wave(t, 2), 3 * wave(t), 0), "loc": (0, 0, 0.02 * abs(wave(t, 2)))},
					  "root": {"loc": (0, 0, 0.03 * abs(wave(t, 2)))}, "body": {"loc": (0, 0.03 * wave(t, 2), 0)}},
					 claws(4, 6 + 3 * wave(t), 6 - 3 * wave(t)))

	def run(t):
		lift_a, lift_b = max(0.0, wave(t, 1, 0.25)), max(0.0, wave(t, 1, 0.75))
		return merge(legs(26 * wave(t), -26 * wave(t), 26 * lift_a, 26 * lift_b),
					 {"shell": {"rot": (3 * wave(t, 2), 5 * wave(t), 0)}, "root": {"loc": (0, 0, 0.05 * abs(wave(t, 2))), "rot": (-4, 0, 0)}},
					 claws(4, 10, 10))

	def attack(t):   # the crusher rises high and open and slams down shut
		up = seq(t, [(0, 0), (0.4, 1), (0.52, 1), (0.62, -0.3), (0.8, -0.2), (1, 0)])
		open_r = seq(t, [(0, 0), (0.35, 46), (0.55, 48), (0.62, -4), (0.8, 0)])
		surge = seq(t, [(0, 0), (0.45, -0.06), (0.62, 0.16), (0.85, 0.1), (1, 0)])
		return merge({"body": {"loc": (0, surge, 0)}, "root": {"rot": (4 * up, 0, 0)}, "head": {"rot": (8 * up, 0, 0)}},
					 claws(10 * max(0.0, up), 10 * up, 50 * up, open_r))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"body": {"loc": (0, 0.14 * k, -0.02 * k)}, "head": {"rot": (10 * k, 0, 10 * k)}, "shell": {"rot": (-3 * k, 3 * k, 0)}},
					 claws(20 * k, -14 * k, -10 * k))

	def death(t):   # pulls back into the drum, legs folding, and the drum settles over on its side
		f = seq(t, [(0.1, 0), (0.6, 1)])
		g = seq(t, [(0.45, 0), (0.85, 1)])
		return merge({"body": {"loc": (0, 0.3 * f, -0.14 * f)}, "head": {"rot": (-20 * f, 0, 0), "loc": (0, 0.1 * f, 0)},
					  "root": {"loc": (0, 0, -0.18 * g), "rot": (0, 22 * g, 0)}},
					 claws(10 * f, -30 * f, -26 * f), legs(10 * f, 10 * f, -50 * f, -50 * f))

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 1.6, walk, True)
	clip(arm, "run", 1.0, run, True)
	clip(arm, "attack", 1.2, attack, False)
	clip(arm, "hit", 0.5, hit, False)
	clip(arm, "death", 1.8, death, False)
	return arm


# ---------------------------------------------------------------- Dewstep (levels 1-10, below Lanternhold)
# Lantern moths and wisps, rice beetles and paddy rats, temple monkeys and their king,
# jackals, cobras and tigers; the Dustpaw jackal-folk; hungry ghosts and the Lantern Widow.

def build_paddy_rat():
	"""A paddy rat: the rat caked in rice-field mud, a darker brown with a muddy belly."""
	return build_rat("paddy_rat", "5a4430", "8a7456", "c48a80")


def build_rice_beetle():
	"""A rice beetle: the fire beetle's frame in a green-bronze shell with dull amber eyes (models.json
	scales it down to knee height)."""
	return build_beetle("rice_beetle", "5e8a34", "8a6e2a", "26261a", "e8c860", 0.6, metallic=0.45)


def build_jackal():
	"""A golden jackal: the wolf made lean and long-legged-looking, big upright ears, a long narrow nose."""
	return build_wolf("jackal", "c49a5a", "7a624a", "ecdcbc", "e8b040", ear=1.3, slim=0.78, snout=1.2)


def build_lantern_moth():
	"""A big soft moth the size of a dog: pale cream wings with an eye spot on each, a fuzzy thorax and a
	glowing lantern-orange abdomen, feathery antennae. It hovers at waist height, wings slowly beating."""
	fuzz = material("lantern_moth_fuzz", "e8dcc2", 0.95)
	fuzz_d = material("lantern_moth_fuzz_dark", "a8967a", 0.95)
	wing = material("lantern_moth_wing", "f2eadc", 0.9, emit=0.05)
	wing_edge = material("lantern_moth_wing_edge", "c8b89a", 0.9)
	ring_d = material("lantern_moth_spot_dark", "4a3222", 0.8)
	ring_o = material("lantern_moth_spot_orange", "e89a3a", 0.7, emit=0.3)
	spot_c = material("lantern_moth_spot_center", "1a1210", 0.4)
	glow = material("lantern_moth_glow", "ffa040", 0.4, emit=2.5)
	glow_b = material("lantern_moth_glow_band", "c86a20", 0.5, emit=1.0)
	eye = material("lantern_moth_eye", "1a1614", 0.2)
	b = Builder("lantern_moth")
	z0 = 1.0
	b.bone("root", (0, 0, z0))
	b.bone("body", (0, 0, z0), "root")
	b.bone("head", (0, -0.22, z0 + 0.02), "body")
	b.bone("abdomen", (0, 0.12, z0 - 0.02), "body")
	# the thorax: a fuzzy ball with a collar
	b.blob((0.3, 0.34, 0.3), (0, -0.04, z0), fuzz, "body", segs=(12, 8))
	b.blob((0.34, 0.14, 0.3), (0, -0.18, z0), fuzz_d, "body", segs=(10, 6))
	# the head: round, big dark eyes, feathery antennae
	b.blob((0.2, 0.18, 0.2), (0, -0.28, z0 + 0.02), fuzz, "head", segs=(10, 7))
	for s in (1, -1):
		b.blob((0.1, 0.1, 0.11), (0.08 * s, -0.33, z0 + 0.04), eye, "head", segs=(8, 6))
		base = Vector((0.04 * s, -0.33, z0 + 0.1))
		tip = base + Vector((0.2 * s, -0.24, 0.26))
		b.seg(tuple(base), tuple(tip), 0.012, 0.006, fuzz_d, "head", sides=4)
		for k in range(1, 6):   # the plumes along it
			p = base + (tip - base) * (k / 6)
			_oblob(b, (0.1 * (1 - k / 9), 0.04, 0.012), tuple(p), (tip - base), (0, 0.3, 1), fuzz_d, "head", segs=(6, 3))
	# the abdomen: a glowing lantern, banded
	for k in range(5):
		y = 0.14 + 0.1 * k
		r = 0.2 - 0.028 * k
		b.blob((r, 0.14, r), (0, y, z0 - 0.03 - 0.02 * k), glow, "abdomen", segs=(10, 6))
		b.blob((r * 1.04, 0.03, r * 1.04), (0, y + 0.06, z0 - 0.03 - 0.02 * k), glow_b, "abdomen", segs=(10, 3))
	b.blob((0.07, 0.08, 0.07), (0, 0.62, z0 - 0.12), glow_b, "abdomen", segs=(6, 4))
	# six little legs tucked under
	for y in (-0.12, -0.04, 0.04):
		for s in (1, -1):
			knee = (0.1 * s, y - 0.02, z0 - 0.16)
			b.seg((0.04 * s, y, z0 - 0.08), knee, 0.016, 0.012, fuzz_d, "body", sides=4)
			b.seg(knee, (0.06 * s, y - 0.04, z0 - 0.26), 0.012, 0.005, fuzz_d, "body", sides=4)
	# the wings: a broad forewing swept a little back, a rounder hindwing, each with an eye spot top and bottom
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		for fb, (y, ln, wd, sweep, spot) in (("f", (-0.1, 0.82, 0.42, -0.08, 0.14)), ("b", (0.04, 0.6, 0.44, 0.5, 0.1))):
			bone = f"wing_{fb}{side}"
			root = Vector((0.1 * s, y, z0 + 0.06))
			b.bone(bone, tuple(root), "body")
			d = Vector((s, sweep, 0.05)).normalized()
			c = root + d * ln * 0.5
			_oblob(b, (wd * 1.06, ln * 1.02, 0.012), tuple(c + Vector((0, 0.01, -0.004))), d, (0, 0, 1), wing_edge, bone, segs=(16, 4))
			_oblob(b, (wd, ln, 0.02), tuple(c), d, (0, 0, 1), wing, bone, segs=(16, 4))
			sc = root + d * ln * 0.62 + Vector((0, 0.03 if fb == "f" else 0.0, 0))
			for z in (1, -1):   # the eye spot: dark ring, orange ring, dark pupil with a pale glint
				for size, mat, lift in ((spot, ring_d, 0.012), (spot * 0.72, ring_o, 0.016), (spot * 0.38, spot_c, 0.02)):
					b.blob((size, size, 0.01), tuple(sc + Vector((0, 0, lift * z))), mat, bone, segs=(10, 3))
				b.blob((spot * 0.14, spot * 0.14, 0.008), tuple(sc + Vector((0.02 * s, -0.02, 0.024 * z))), wing, bone, segs=(6, 3))
			b.seg(tuple(root), tuple(root + d * ln * 0.9), 0.012, 0.005, wing_edge, bone, sides=4)   # the leading vein
	arm = b.build()

	def wings(t, beat, amp, cycles):
		out = {}
		for fb, ph in (("f", 0.0), ("b", 0.06)):
			r = amp * wave(t, cycles, ph) + beat
			out[f"wing_{fb}l"] = {"rot": (0, r, 0)}
			out[f"wing_{fb}r"] = {"rot": (0, -r, 0)}
		return out

	def idle(t):   # soft, slow beats, bobbing up on each downstroke
		return merge(wings(t, 12, 38, 3), {"root": {"loc": (0.03 * wave(t, 1, 0.3), 0, 0.07 * wave(t, 3, 0.25))},
										   "body": {"rot": (3 * wave(t, 1), 0, 4 * wave(t, 1, 0.5))},
										   "abdomen": {"rot": (-4 * wave(t, 3, 0.1), 0, 0)}, "head": {"rot": (0, 0, 6 * wave(t, 1, 0.6))}})

	def walk(t):   # drifts forward, nose a little down
		return merge(wings(t, 10, 40, 3), {"root": {"loc": (0, 0, 0.08 * wave(t, 3, 0.25)), "rot": (-6, 0, 0)},
										   "abdomen": {"rot": (-5 * wave(t, 3, 0.1), 0, 0)}})

	def run(t):
		return merge(wings(t, 6, 44, 3), {"root": {"loc": (0, 0, 0.06 * wave(t, 3, 0.25)), "rot": (-12, 0, 0)},
										  "abdomen": {"rot": (4, 0, 0)}})

	def attack(t):   # a flurry of wingbeats as it batters into you
		dart = seq(t, [(0, 0), (0.3, -0.1), (0.5, 0.36), (0.75, 0.2), (1, 0)])
		dip = seq(t, [(0, 0), (0.3, 0.1), (0.5, -0.16), (1, 0)])
		return merge(wings(t, 0, 50, 4), {"root": {"loc": (0, dart, dip), "rot": (seq(t, [(0, 0), (0.3, 10), (0.5, -16), (1, 0)]), 0, 0)},
										  "abdomen": {"rot": (seq(t, [(0, 0), (0.5, 18), (1, 0)]), 0, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge(wings(t, 20 * k, 30, 2), {"root": {"loc": (0, -0.14 * k, 0.08 * k), "rot": (12 * k, 16 * k, 0)}})

	def death(t):   # the wings falter and it flutters down, landing flat with its wings spread
		k = seq(t, [(0.05, 0), (0.75, 1)])
		beat = 1 - seq(t, [(0.2, 0), (0.7, 1)])
		return merge(wings(t, 10 - 18 * k, 40 * beat, 3), {"root": {"loc": (0, 0, -(z0 - 0.08) * k + 0.08 * math.sin(math.pi * k)),
																   "rot": (0, 10 * math.sin(math.pi * k), 40 * k)},
														   "abdomen": {"rot": (-4 * k, 0, 0)}})

	clip(arm, "idle", 1.5, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.75, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_lantern_wisp():
	"""A lantern wisp: a small floating orb of pale gold light in a soft halo, two dark little eyes,
	and a faint tail of fading glow trailing behind and below it."""
	core = material("lantern_wisp_core", "fff2c0", 0.2, emit=5.0)
	inner = material("lantern_wisp_inner", "ffd870", 0.3, emit=3.0)
	halo = glass_material("lantern_wisp_halo", "ffe8a0", 0.3, 0.2, emit=1.5)
	tail = glass_material("lantern_wisp_tail", "ffd87a", 0.35, 0.2, emit=1.8)
	tail_b = glass_material("lantern_wisp_tail_faint", "ffe8b0", 0.18, 0.2, emit=1.2)
	eye = material("lantern_wisp_eye", "4a3010", 0.3)
	b = Builder("lantern_wisp")
	z0 = 1.2
	b.bone("root", (0, 0, z0))
	b.bone("orb", (0, 0, z0), "root")
	b.bone("tail1", (0, 0.14, z0 - 0.04), "orb")
	b.bone("tail2", (0, 0.38, z0 - 0.14), "tail1")
	b.blob((0.3, 0.3, 0.3), (0, 0, z0), inner, "orb", segs=(14, 10))
	b.blob((0.2, 0.2, 0.2), (0, -0.04, z0 + 0.02), core, "orb", segs=(12, 8))
	b.blob((0.46, 0.46, 0.46), (0, 0, z0), halo, "orb", segs=(14, 10))
	for s in (1, -1):
		b.blob((0.04, 0.03, 0.06), (0.055 * s, -0.145, z0 + 0.02), eye, "orb", segs=(6, 4))
	# the tail: overlapping, fading puffs in two bones, curling a little
	for k in range(4):
		u = k / 3
		b.blob((0.24 - 0.05 * k, 0.2, 0.22 - 0.05 * k), (0.02 * math.sin(u * 3), 0.16 + 0.07 * k, z0 - 0.04 - 0.03 * k), tail, "tail1", segs=(10, 6))
	for k in range(4):
		u = k / 3
		r = 0.12 - 0.025 * k
		b.blob((r, r * 1.4, r), (-0.03 * math.sin(u * 3), 0.42 + 0.08 * k, z0 - 0.16 - 0.04 * k), tail_b, "tail2", segs=(8, 5))
	for k in range(5):   # motes drifting in it
		a = 1.3 * k
		b.blob((0.03, 0.03, 0.03), (0.08 * math.cos(a), 0.22 + 0.08 * k, z0 - 0.06 - 0.04 * k + 0.05 * math.sin(a)), core, "tail1" if k < 3 else "tail2", segs=(4, 3))
	arm = b.build()

	def trail(t, amp, cycles=1.0):
		return {"tail1": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (6 * wave(t, cycles, 0.4), 0, amp * 1.5 * wave(t, cycles, -0.2))}}

	def idle(t):
		return merge(trail(t, 14), {"root": {"loc": (0.04 * wave(t, 1, 0.3), 0, 0.08 * wave(t, 2))},
									"orb": {"rot": (0, 6 * wave(t, 1), 10 * wave(t, 1, 0.25))}})

	def walk(t):
		return merge(trail(t, 18, 2), {"root": {"loc": (0.03 * wave(t, 2), 0, 0.05 * wave(t, 2, 0.25)), "rot": (-6, 0, 0)}})

	def run(t):
		return merge(trail(t, 10, 2), {"root": {"loc": (0, 0, 0.04 * wave(t, 2, 0.25)), "rot": (-12, 0, 0)},
									   "tail1": {"rot": (10, 0, 0)}})

	def attack(t):   # darts in and flares
		dart = seq(t, [(0, 0), (0.3, -0.14), (0.5, 0.4), (0.7, 0.3), (1, 0)])
		return merge(trail(t, 24, 2), {"root": {"loc": (0, dart, seq(t, [(0, 0), (0.3, 0.1), (0.5, -0.1), (1, 0)]))},
									   "orb": {"rot": (seq(t, [(0, 0), (0.5, -30), (1, 0)]), 0, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge(trail(t, 30 * k, 2), {"root": {"loc": (0, -0.18 * k, 0.1 * k)}, "orb": {"rot": (20 * k, 0, 20 * k)}})

	def death(t):   # gutters, sinks to the ground and goes out
		k = seq(t, [(0.05, 0), (0.8, 1)])
		shrink = 1 - 0.75 * seq(t, [(0.4, 0), (1, 1)])
		return merge_scaled(trail(t, 20 * (1 - k), 3), {"root": {"loc": (0, 0, -(z0 - 0.12) * k + 0.05 * wave(t, 4) * (1 - k))},
														"orb": {"scale": (shrink, shrink, shrink)},
														"tail1": {"rot": (-30 * k, 0, 0), "scale": (shrink, shrink, shrink)}})

	clip(arm, "idle", 2.0, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.6, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.3, death, False)
	return arm


MONKEY_TAIL = ("tail1", "tail2", "tail3")


def build_monkey(name="temple_monkey", king=False):
	"""A temple langur: slim and long-limbed, gray with a pale belly, a black face in a ruff of pale fur,
	black hands and feet, and a long tail carried in a high arch. The troop king is bigger, silver-maned,
	wearing a stolen gold circlet and a bangle on his wrist."""
	import random
	rng = random.Random(611 if king else 607)
	fur = material(f"{name}_fur", "8e8a84" if king else "a8a49c", 0.95)
	fur_d = material(f"{name}_fur_dark", "6a6660" if king else "86827c", 0.95)
	pale = material(f"{name}_pale", "e6e2d8" if king else "d8d2c4", 0.95)
	dark = material(f"{name}_skin", "1e1c1c", 0.6)
	eye = material(f"{name}_eye", "d8a040", 0.25, emit=0.6)
	pupil = material(f"{name}_pupil", "0c0a08", 0.2)
	tooth = material(f"{name}_tooth", "f2ecd8", 0.4)
	b = Builder(name)
	b.bone("root", (0, 0, 0.55))
	b.bone("body", (0, 0.05, 0.58), "root")
	b.bone("head", (0, -0.42, 0.8), "body")
	b.bone("jaw", (0, -0.62, 0.78), "head")
	b.bone("tail1", (0, 0.4, 0.6), "body")
	b.bone("tail2", (0, 0.84, 1.06), "tail1")
	b.bone("tail3", (0, 1.34, 0.98), "tail2")
	# the body: deep chest, slim waist, rump a little lower
	b.blob((0.36, 0.76, 0.36), (0, 0.04, 0.58), fur, "body", rot=(-7, 0, 0), segs=(12, 8))
	b.blob((0.42, 0.42, 0.44), (0, -0.2, 0.64), fur, "body", segs=(12, 8))
	b.blob((0.36, 0.36, 0.36), (0, 0.28, 0.54), fur, "body", segs=(10, 7))
	b.blob((0.26, 0.6, 0.18), (0, -0.02, 0.44), pale, "body", segs=(10, 6))                 # pale belly
	b.blob((0.28, 0.66, 0.14), (0, 0.04, 0.75), fur_d, "body", rot=(-7, 0, 0), segs=(10, 6))   # darker back
	# the head: a round gray skull, a pale ruff framing a black face, a peaked crest
	b.seg((0, -0.3, 0.68), (0, -0.46, 0.8), 0.1, 0.1, fur, "head", sides=8)
	b.blob((0.32, 0.3, 0.32), (0, -0.5, 0.86), fur, "head", segs=(12, 8))
	b.blob((0.4, 0.12, 0.38), (0, -0.6, 0.83), pale, "head", segs=(12, 6))                   # the ruff
	b.blob((0.22, 0.1, 0.26), (0, -0.655, 0.83), dark, "head", segs=(10, 6))                 # the black face
	b.blob((0.13, 0.1, 0.09), (0, -0.7, 0.77), dark, "head", segs=(8, 5))                    # muzzle
	b.blob((0.22, 0.06, 0.05), (0, -0.7, 0.9), dark, "head", segs=(8, 4))                    # brow ridge
	_oblob(b, (0.12, 0.26, 0.1), (0, -0.46, 1.02), (0, 1, 0.4), (0, -0.2, 1), fur_d, "head", segs=(8, 5))   # crest
	b.blob((0.1, 0.07, 0.05), (0, -0.66, 0.73), dark, "jaw", segs=(6, 4))                    # chin
	for s in (1, -1):
		b.blob((0.055, 0.04, 0.05), (0.052 * s, -0.7, 0.86), eye, "head", segs=(6, 4))
		b.blob((0.024, 0.02, 0.03), (0.052 * s, -0.72, 0.86), pupil, "head", segs=(4, 3))
		b.blob((0.05, 0.07, 0.08), (0.165 * s, -0.52, 0.87), dark, "head", segs=(6, 4))      # small black ears
		b.seg((0.025 * s, -0.72, 0.75), (0.025 * s, -0.72, 0.71), 0.012, 0.003, tooth, "head", sides=3)
	# arms (long) and legs, black hands and feet
	for name_, (x, y) in {"leg_fl": (0.16, -0.26), "leg_fr": (-0.16, -0.26)}.items():
		b.bone(name_, (x, y, 0.66), "root")
		b.blob((0.15, 0.17, 0.18), (x * 1.05, y, 0.64), fur, name_, segs=(8, 6))
		b.seg((x * 1.05, y, 0.64), (x * 1.08, y - 0.03, 0.34), 0.06, 0.05, fur, name_, sides=7)
		b.seg((x * 1.08, y - 0.03, 0.34), (x, y - 0.02, 0.07), 0.05, 0.042, fur, name_, sides=7)
		b.blob((0.1, 0.15, 0.06), (x, y - 0.06, 0.03), dark, name_, segs=(7, 4))
	for name_, (x, y) in {"leg_bl": (0.14, 0.3), "leg_br": (-0.14, 0.3)}.items():
		b.bone(name_, (x, y, 0.52), "root")
		b.blob((0.16, 0.26, 0.28), (x * 1.08, y, 0.44), fur, name_, segs=(8, 6))
		b.seg((x * 1.08, y - 0.04, 0.4), (x * 1.06, y - 0.1, 0.22), 0.06, 0.05, fur, name_, sides=7)
		b.seg((x * 1.06, y - 0.1, 0.22), (x, y + 0.02, 0.06), 0.05, 0.04, fur, name_, sides=7)
		b.blob((0.1, 0.22, 0.06), (x, y - 0.04, 0.03), dark, name_, segs=(7, 4))
	# the tail: long, carried up in an arch and falling behind
	pts = [(0, 0.38, 0.58), (0, 0.6, 0.86), (0, 0.84, 1.06), (0, 1.1, 1.1), (0, 1.34, 0.98), (0, 1.5, 0.76), (0, 1.56, 0.52)]
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		bone = MONKEY_TAIL[min(k // 2, 2)]
		r = 0.05 - 0.004 * k
		b.seg(p, q, r, r - 0.004, fur_d if k >= 4 else fur, bone, sides=7)
		b.blob((r * 2, r * 2, r * 2), q, fur_d if k >= 3 else fur, bone, segs=(6, 5))
	if king:
		gold = metal_material(f"{name}_gold", "e8b838", 0.3, 0.8)
		gem = material(f"{name}_gem", "c81e2a", 0.2, emit=0.4)
		silver = material(f"{name}_silver", "eceef0", 0.9)
		silver_d = material(f"{name}_silver_dark", "b8bcc0", 0.9)
		# the silver mane: a shaggy cape over the shoulders and round the face
		start = len(b.parts)
		b.blob((0.56, 0.5, 0.48), (0, -0.2, 0.72), silver, "x", segs=(12, 8))
		b.blob((0.5, 0.18, 0.5), (0, -0.56, 0.84), silver, "x", segs=(12, 6))
		for k in range(14):
			a = 2 * math.pi * k / 14
			root = Vector((0.2 * math.cos(a), -0.2 + 0.18 * math.sin(a), 0.78))
			_tuft(b, tuple(root), (math.cos(a), 0.4 + 0.3 * math.sin(a), -0.8), 0.24, 3, 0.3, (silver, silver_d), 700 + k, width=0.04)
		_on_bone(b, start, "body")
		start = len(b.parts)
		for k in range(10):   # ruff round the face, whiter
			a = 2 * math.pi * k / 10
			_tuft(b, (0.14 * math.cos(a), -0.58, 0.84 + 0.14 * math.sin(a)), (math.cos(a), 0.3, math.sin(a)), 0.14, 2, 0.3, (silver,), 720 + k, width=0.035)
		# the stolen circlet, a bit too big and tipped over one ear
		_ring(b, (0.02, -0.5, 1.0), (0.2, 0.18), (10, -8), 0.025, gold, sides=16)
		for k in range(5):
			a = -math.pi / 2 + (k - 2) * 0.5
			p = Vector((0.02 + 0.2 * math.cos(a), -0.5 + 0.18 * math.sin(a), 1.0 + 0.035 * math.cos(a)))
			b.seg(tuple(p), tuple(p + Vector((0, 0, 0.09 if k == 2 else 0.06))), 0.03, 0.0, gold, "x", sides=4)
		b.blob((0.05, 0.03, 0.05), (0.02, -0.69, 1.02), gem, "x", segs=(6, 4))
		_on_bone(b, start, "head")
		start = len(b.parts)
		_ring(b, (0.168, -0.29, 0.22), (0.065, 0.065), (0, 0), 0.02, gold, sides=12)            # a bangle on the left wrist
		_ring(b, (0.168, -0.29, 0.27), (0.062, 0.062), (0, 0), 0.016, gold, sides=12)
		_on_bone(b, start, "leg_fl")
		_scaled(b, 1.4)
	arm = b.build()

	def tail(t, amp, cycles=1.0):
		return {"tail1": {"rot": (3 * wave(t, cycles, 0.2), 0, amp * 0.5 * wave(t, cycles))},
				"tail2": {"rot": (4 * wave(t, cycles, 0.1), 0, amp * wave(t, cycles, -0.15))},
				"tail3": {"rot": (6 * wave(t, cycles, 0.0), 0, amp * 1.3 * wave(t, cycles, -0.3))}}

	def idle(t):   # sits up a little on its haunches, glances round, scratches
		look = seq(t, [(0, 0), (0.2, 0), (0.28, 30), (0.45, 30), (0.52, -20), (0.7, -20), (0.78, 0)])
		scratch = 8 * wave(t, 8) * seq(t, [(0.8, 0), (0.84, 1), (0.95, 1), (0.98, 0)])
		return merge({"root": {"rot": (8, 0, 0), "loc": (0, 0.02, -0.03)},
					  "body": {"loc": (0, 0, 0.01 * wave(t, 3))},
					  "head": {"rot": (-6 + 4 * wave(t, 1, 0.3), 0, look)},
					  "leg_bl": {"rot": (-8, 0, 0)}, "leg_br": {"rot": (-8 + scratch, 0, 0)},
					  "leg_fl": {"rot": (-8, 0, 0)}, "leg_fr": {"rot": (-8, 0, 0)}}, tail(t, 6))

	def walk(t):   # a quick four-legged walk
		return merge(_quad_legs(wave(t), 30), tail(t, 8, 1), {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))},
															  "body": {"rot": (0, 3 * wave(t), 0)}, "head": {"rot": (3 * wave(t, 2), 0, 0)}})

	def run(t):   # bounding: arms together, then legs
		f, k = 50 * wave(t), 50 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.85, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.85, 0, 0)},
					  "root": {"loc": (0, 0, 0.1 * max(0.0, wave(t, 1, 0.25))), "rot": (9 * wave(t, 1, 0.1), 0, 0)}}, tail(t, 5))

	def attack(t):   # rears up on its legs, bares its fangs and slaps down with both hands
		rear = seq(t, [(0, 0), (0.35, 40), (0.55, -4), (1, 0)])
		arms = seq(t, [(0, 0), (0.35, 90), (0.55, -30), (1, 0)])
		gape = seq(t, [(0, 0), (0.3, -28), (0.55, -10), (0.8, 0)])
		return merge({"root": {"rot": (rear, 0, 0), "loc": (0, seq(t, [(0, 0), (0.35, 0.12), (0.55, -0.2), (1, 0)]), 0.1 * rear / 40)},
					  "leg_fl": {"rot": (arms, 0, 0)}, "leg_fr": {"rot": (arms * 0.9, 0, 0)},
					  "leg_bl": {"rot": (-rear, 0, 0)}, "leg_br": {"rot": (-rear, 0, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.35, -24), (0.55, 10), (1, 0)]), 0, 0)}, "jaw": {"rot": (gape, 0, 0)}},
					 tail(t, 18, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, 0.04 * k), "rot": (12 * k, 0, 0)}, "head": {"rot": (16 * k, 0, 14 * k)},
					  "jaw": {"rot": (-20 * k, 0, 0)}}, tail(t, 22 * k, 2))

	def death(t):
		roll = seq(t, [(0.15, 0), (0.6, 88), (0.72, 82), (0.85, 90)])
		drop = seq(t, [(0.15, 0), (0.6, -0.3)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 12), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (-10 * curl, 0, 14 * curl)}, "jaw": {"rot": (-14 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (34 * curl, 0, 0)}, "leg_fr": {"rot": (16 * curl, 0, 0)},
					  "leg_bl": {"rot": (-28 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					 {"tail1": {"rot": (-30 * curl, 0, 10 * curl)}, "tail2": {"rot": (-30 * curl, 0, 20 * curl)}, "tail3": {"rot": (-20 * curl, 0, 20 * curl)}})

	clip(arm, "idle", 3.0, idle, True)
	clip(arm, "walk", 0.6, walk, True)
	clip(arm, "run", 0.36, run, True)
	clip(arm, "attack", 0.6, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.1, death, False)
	return arm


def build_monkey_troop_king():
	return build_monkey("monkey_troop_king", king=True)


COBRA_SEGS = 8


def build_cobra():
	"""A banded cobra: the body lies in coils on the ground behind a raised neck, the hood spread wide
	with a pale spectacle mark on its back. Each ground segment rides its own bone (like the marsh eel),
	so it slithers in S-curves; the neck is a chain that rears back and strikes."""
	scale = material("cobra_scale", "5a4a2a", 0.5)
	band = material("cobra_band", "d8c07a", 0.5)
	belly = material("cobra_belly", "e8d8a8", 0.55)
	hood_in = material("cobra_hood_inner", "d4bc80", 0.6)
	mark = material("cobra_mark", "efe2b8", 0.5)
	dark = material("cobra_dark", "2a2216", 0.5)
	eye = material("cobra_eye", "e8b020", 0.2, emit=0.8)
	pupil = material("cobra_pupil", "0c0a06", 0.2)
	tongue = material("cobra_tongue", "b8303a", 0.5)
	b = Builder("cobra")
	b.bone("root", (0, 0, 0.1))
	seg_len = 0.24
	ys = [0.0 + seg_len * i for i in range(COBRA_SEGS)]
	radii = [0.085, 0.09, 0.09, 0.085, 0.078, 0.066, 0.05, 0.032]
	for i, (y, r) in enumerate(zip(ys, radii)):
		bone = f"seg{i}"
		b.bone(bone, (0, y, r), "root")
		ny = y + seg_len
		nr = radii[i + 1] if i + 1 < len(radii) else 0.01
		b.seg((0, y, r), (0, ny, nr), r, nr, scale, bone, sides=10)
		b.blob((r * 2.05, r * 2.05, r * 1.95), (0, y, r), band if i % 2 else scale, bone, segs=(10, 6))
		b.seg((0, y, r * 0.5), (0, ny, nr * 0.5), r * 0.75, nr * 0.75, belly, bone, sides=8)
		b.seg((0, y + seg_len * 0.45, r * 0.98), (0, y + seg_len * 0.62, r * 0.98), r * 1.04, r * 1.04, band, bone, sides=10)   # a pale band
	# the raised neck: a chain from the ground up, the hood spread on the upper part
	b.bone("neck1", (0, -0.02, 0.1), "root")
	b.bone("neck2", (0, -0.1, 0.4), "neck1")
	b.bone("head", (0, -0.16, 0.74), "neck2")
	b.bone("jaw", (0, -0.28, 0.73), "head")
	neck = [(0, 0.02, 0.09), (0, -0.06, 0.24), (0, -0.1, 0.42), (0, -0.13, 0.6), (0, -0.16, 0.74)]
	for k, (p, q) in enumerate(zip(neck, neck[1:])):
		bone = "neck1" if k < 2 else "neck2"
		r = 0.085 - 0.01 * k
		b.seg(p, q, r, r - 0.01, scale, bone, sides=10)
		b.blob((r * 2, r * 2, r * 2), q, band if k % 2 == 0 else scale, bone, segs=(10, 6))
		b.seg(tuple(Vector(p) + Vector((0, -r * 0.5, 0))), tuple(Vector(q) + Vector((0, -(r - 0.01) * 0.5, 0))), r * 0.7, (r - 0.01) * 0.7, belly, bone, sides=8)
	# the hood: a wide flat shield behind the head, pale belly scales in front, a spectacle mark behind
	_oblob(b, (0.4, 0.46, 0.06), (0, -0.1, 0.56), (0, 0.12, 1), (0, -1, 0), scale, "neck2", segs=(14, 6))
	_oblob(b, (0.3, 0.38, 0.03), (0, -0.14, 0.55), (0, 0.12, 1), (0, -1, 0), hood_in, "neck2", segs=(12, 4))
	for s in (1, -1):
		_oblob(b, (0.1, 0.1, 0.02), (0.07 * s, -0.06, 0.6), (0, 0.12, 1), (0, 1, 0), mark, "neck2", segs=(10, 3))
		_oblob(b, (0.05, 0.05, 0.02), (0.07 * s, -0.052, 0.6), (0, 0.12, 1), (0, 1, 0), dark, "neck2", segs=(8, 3))
	b.seg((-0.07, -0.058, 0.56), (0.07, -0.058, 0.56), 0.015, 0.015, mark, "neck2", sides=4)
	for k in range(3):   # dark bars across the throat
		b.blob((0.13, 0.03, 0.03), (0, -0.155, 0.46 + 0.07 * k), dark, "neck2", segs=(8, 3))
	# the head: a broad flat wedge, gold eyes, a flicking forked tongue
	b.blob((0.2, 0.26, 0.12), (0, -0.26, 0.76), scale, "head", segs=(10, 7))
	b.blob((0.16, 0.12, 0.08), (0, -0.37, 0.75), scale, "head", segs=(8, 5))
	b.blob((0.14, 0.2, 0.05), (0, -0.28, 0.705), belly, "jaw", segs=(8, 4))
	for s in (1, -1):
		b.blob((0.045, 0.045, 0.04), (0.075 * s, -0.31, 0.79), eye, "head", segs=(6, 4))
		b.blob((0.012, 0.02, 0.035), (0.09 * s, -0.315, 0.79), pupil, "head", segs=(4, 3))
		b.seg((0, -0.42, 0.72), (0.025 * s, -0.52, 0.72), 0.008, 0.003, tongue, "jaw", sides=3)
	b.seg((0, -0.36, 0.72), (0, -0.43, 0.72), 0.012, 0.009, tongue, "jaw", sides=3)
	arm = b.build()

	def body(t, amp, cycles, wavelength=1.6, rest=0.0):
		"""A wave traveling down the body; `rest` lays a standing S-curve (the coil) under it."""
		out = {}
		pts = ys + [ys[-1] + seg_len]

		def xat(i, y):
			grow = 0.3 + 0.7 * min(1.0, (i + 1) / 3)
			return amp * grow * math.sin(2 * math.pi * (t * cycles - y / wavelength)) + rest * math.sin(2 * math.pi * y / 1.3) * grow
		xs = [xat(i, y) for i, y in enumerate(pts)]
		for i in range(COBRA_SEGS):
			yaw = -math.degrees(math.atan2(xs[i + 1] - xs[i], seg_len))
			out[f"seg{i}"] = {"loc": (-xs[i], 0, 0), "rot": (0, 0, yaw)}
		out["neck1"] = {"loc": (-xs[0], 0, 0), "rot": (0, 0, 0)}
		return out

	def idle(t):   # swaying, hood up, tongue flicking
		flick = seq(t % 0.5 * 2, [(0, 0), (0.1, 1), (0.2, 0)])
		return merge(body(t, 0.02, 1, rest=0.14), {"neck1": {"rot": (0, 3 * wave(t, 1, 0.25), 5 * wave(t))},
												   "neck2": {"rot": (4 * wave(t, 1, 0.1), 0, 7 * wave(t, 1, -0.1))},
												   "head": {"rot": (-3 * wave(t, 1, 0.1), 0, -6 * wave(t, 1, -0.1))},
												   "jaw": {"rot": (-6 * flick, 0, 0)}})

	def walk(t):   # slithers, neck held up and steady
		return merge(body(t, 0.14, 1), {"neck2": {"rot": (-6, 0, 3 * wave(t))}, "head": {"rot": (6, 0, 0)}})

	def run(t):
		return merge(body(t, 0.18, 1, 2.0), {"neck1": {"rot": (-10, 0, 0)}, "neck2": {"rot": (-10, 0, 0)}, "head": {"rot": (14, 0, 0)}})

	def attack(t):   # draws back, then strikes forward and down, fangs bared
		back = seq(t, [(0, 0), (0.35, 1), (0.48, -1), (0.65, -0.8), (1, 0)])
		up, strike = max(0.0, back), max(0.0, -back)
		gape = seq(t, [(0, 0), (0.3, 20), (0.46, 40), (0.56, 0), (1, 0)])
		return merge(body(t, 0.02, 1, rest=0.14), {"neck1": {"rot": (14 * up - 34 * strike, 0, 0), "loc": (0, -0.1 * strike, 0)},
												   "neck2": {"rot": (16 * up - 30 * strike, 0, 0)},
												   "head": {"rot": (-14 * up + 26 * strike, 0, 0)}, "jaw": {"rot": (-gape, 0, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge(body(t, 0.05 * k, 2, rest=0.14), {"neck1": {"rot": (16 * k, 0, 10 * k)}, "neck2": {"rot": (10 * k, 0, 0)},
													  "head": {"rot": (-8 * k, 0, 14 * k)}, "jaw": {"rot": (-20 * k, 0, 0)}})

	def death(t):   # the neck collapses sideways and the coils go slack
		k = seq(t, [(0.1, 0), (0.6, 1)])
		thrash = seq(t, [(0, 1), (0.5, 0.2), (0.8, 0)])
		return merge(body(t * 2, 0.1 * thrash, 1, rest=0.14), {"neck1": {"rot": (-40 * k, 80 * k, 0)}, "neck2": {"rot": (-30 * k, 0, 10 * k)},
															   "head": {"rot": (20 * k, 0, 0)}, "jaw": {"rot": (-24 * k, 0, 0)}})

	clip(arm, "idle", 2.0, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.7, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.2, death, False)
	return arm


def _stripes(b, center, y0, y1, count, radius, mat, bone, rng, a0=8, a1=110, width=0.06, thick=0.03, slant=0.08):
	"""Tiger stripes: for each of `count` rings along Y, a tapering dash down each side from near the spine,
	laid on the outermost skin (rays toward the body's axis) of everything built so far."""
	from mathutils.bvhtree import BVHTree
	bm = bmesh.new()
	for p in b.parts:
		bm.from_mesh(p.data)
	tree = BVHTree.FromBMesh(bm)
	cx, cz = center
	for i in range(count):
		y = y0 + (y1 - y0) * (i + 0.5) / count + rng.uniform(-0.03, 0.03)
		for s in (1, -1):
			start = a0 + rng.uniform(0, 22)
			end = a1 - rng.uniform(0, 34)
			pts = []
			a = start
			wob = 0.0
			while a <= end:
				r = math.radians(a)
				d = Vector((s * math.sin(r), 0, math.cos(r)))
				wob += rng.uniform(-0.025, 0.025)
				yy = y + slant * (a - start) / 100.0 + wob
				o = Vector((cx, yy, cz))
				hit, n, _, _ = tree.ray_cast(o + d * radius * 3, -d)
				if hit is not None:
					pts.append((hit, n if n.dot(d) > 0 else -n))
				a += 6
			gap = rng.randrange(1, max(2, len(pts) - 1)) if rng.random() < 0.35 else -1   # a broken stripe
			for k, ((p, n), (q, _)) in enumerate(zip(pts, pts[1:])):
				if k == gap:
					continue
				u = k / max(1, len(pts) - 1)
				w = width * (1.0 - 0.6 * u) * rng.uniform(0.85, 1.15)
				_oblob(b, (w, (q - p).length * 2.2, thick), tuple((p + q) / 2), q - p, n, mat, bone, segs=(8, 3))
	bm.free()


def build_tiger(name="tiger", old=False):
	"""A young tiger: the snow leopard's frame made heavier, orange with black stripes, white cheeks and
	belly, a banded tail with a black tip. Amberstripe, the old tigress, is bigger and a deeper amber,
	gray about the muzzle, clawed scars across her face and flank and a torn left ear."""
	import random
	rng = random.Random(919 if old else 917)
	fur = material(f"{name}_fur", "b85a14" if old else "e07a26", 0.9)
	back = material(f"{name}_back", "9a4a10" if old else "c8661c", 0.9)
	white = material(f"{name}_white", "e8e0d0" if old else "f4ecdc", 0.9)
	stripe = material(f"{name}_stripe", "1a120e", 0.85)
	eye = material(f"{name}_eye", "e8c040", 0.25, emit=1.0)
	nose = material(f"{name}_nose", "c07a70", 0.5)
	dark = material(f"{name}_dark", "2a2420", 0.6)
	pupil = material(f"{name}_pupil", "0e0c0a", 0.2)
	tooth = material(f"{name}_tooth", "f2ecd8", 0.4)
	scar = material(f"{name}_scar", "d8a494", 0.7)
	gray = material(f"{name}_gray", "b8b0a4", 0.9)
	b = Builder(name)
	legs = {"leg_fl": (0.22, -0.52), "leg_fr": (-0.22, -0.52), "leg_bl": (0.23, 0.52), "leg_br": (-0.23, 0.52)}
	b.bone("root", (0, 0, 0.68))
	b.bone("body", (0, 0.0, 0.72), "root")
	b.bone("head", (0, -0.8, 0.94), "body")
	b.bone("jaw", (0, -0.98, 0.84), "head")
	b.bone("tail1", (0, 0.84, 0.8), "body")
	b.bone("tail2", (0, 1.28, 0.58), "tail1")
	b.bone("tail3", (0, 1.72, 0.4), "tail2")

	b.blob((0.7, 1.7, 0.64), (0, 0.02, 0.76), fur, "body", segs=(14, 9))                     # long, heavy body
	b.blob((0.78, 0.66, 0.7), (0, -0.48, 0.8), fur, "body", segs=(12, 8))                     # deep chest and shoulders
	b.blob((0.72, 0.64, 0.64), (0, 0.52, 0.76), fur, "body", segs=(12, 8))                    # haunches
	b.blob((0.56, 1.36, 0.28), (0, 0.02, 0.52), white, "body", segs=(12, 6))                  # pale belly
	b.blob((0.46, 1.3, 0.2), (0, 0.06, 1.06), back, "body", segs=(10, 6))
	b.blob((0.44, 0.3, 0.42), (0, -0.74, 0.7), white, "body", segs=(10, 7))                   # white throat
	_stripes(b, (0, 0.72), -0.62, 0.86, 12, 0.5, stripe, "body", rng, width=0.1, thick=0.035, slant=0.12)
	if old:   # three clawed scars raked down the left flank, laid on the skin
		from mathutils.bvhtree import BVHTree
		bm = bmesh.new()
		for part in b.parts:
			bm.from_mesh(part.data)
		tree = BVHTree.FromBMesh(bm)
		for k in range(3):
			line = []
			for u in (0, 0.25, 0.5, 0.75, 1.0):
				hit, n, _, _ = tree.ray_cast(Vector((2.0, -0.1 + 0.1 * k + 0.2 * u, 0.98 - 0.3 * u)), Vector((-1, 0, 0)))
				if hit is not None:
					line.append(hit + Vector((0.006, 0, 0)))
			for p, q in zip(line, line[1:]):
				_oblob(b, (0.03, (q - p).length * 1.4, 0.014), tuple((p + q) / 2), q - p, (1, 0, 0), scar, "body", segs=(5, 3))
		bm.free()
	# the head: broad, a heavier muzzle than the leopard's, white cheek ruffs, round ears
	b.seg((0, -0.5, 0.88), (0, -0.76, 0.94), 0.26, 0.24, fur, "head", sides=10)               # thick neck
	b.blob((0.6, 0.54, 0.5), (0, -0.88, 0.98), fur, "head", segs=(12, 9))
	b.blob((0.4, 0.3, 0.24), (0, -1.12, 0.9), white, "head", segs=(10, 7))                    # muzzle
	b.blob((0.46, 0.28, 0.14), (0, -1.02, 0.8), white, "head", segs=(8, 5))                   # chin
	b.blob((0.13, 0.07, 0.07), (0, -1.27, 0.95), nose, "head", segs=(6, 4))
	b.seg((0, -1.22, 0.86), (0, -1.26, 0.92), 0.012, 0.012, dark, "head", sides=3)
	b.blob((0.26, 0.18, 0.09), (0, -1.04, 0.79), white, "jaw", segs=(8, 5))                   # lower jaw
	for s in (1, -1):
		for k in range(3):   # the white cheek ruff, flaring out and back
			_oblob(b, (0.08, 0.2, 0.06), (0.27 * s, -0.86 + 0.05 * k, 0.98 - 0.05 * k), (s * 0.6, 0.8, -0.2), (s, 0, 0.2), gray if old else white, "head", segs=(6, 4))
		b.blob((0.16, 0.08, 0.06), (0.14 * s, -1.08, 1.08), white, "head", segs=(8, 4))      # pale brow patches
		b.blob((0.11, 0.07, 0.07), (0.13 * s, -1.09, 1.03), eye, "head", segs=(8, 5))
		b.blob((0.03, 0.03, 0.06), (0.135 * s, -1.12, 1.03), pupil, "head", segs=(4, 3))
		torn = old and s > 0
		if torn:   # the torn ear: split in two with a notch between
			for dx in (-0.035, 0.035):
				b.seg((0.22 * s + dx, -0.84, 1.18), (0.25 * s + dx * 1.5, -0.82, 1.27), 0.04, 0.025, fur, "head", sides=6)
			b.blob((0.12, 0.05, 0.06), (0.235 * s, -0.84, 1.24), dark, "head", segs=(8, 5))
		else:
			b.seg((0.22 * s, -0.84, 1.18), (0.26 * s, -0.82, 1.3), 0.09, 0.06, fur, "head", sides=8)       # round ears
			b.blob((0.13, 0.05, 0.11), (0.255 * s, -0.84, 1.3), dark, "head", segs=(8, 5))
			b.blob((0.07, 0.03, 0.05), (0.255 * s, -0.87, 1.29), white, "head", segs=(6, 4))
		b.seg((0.05 * s, -1.2, 0.82), (0.05 * s, -1.205, 0.775), 0.016, 0.004, tooth, "jaw", sides=4)   # fangs
		for k in range(3):   # whisker pads
			b.blob((0.03, 0.02, 0.03), ((0.05 + 0.03 * k) * s, -1.25, 0.9 - 0.02 * k), gray if old else dark, "head", segs=(4, 3))
		# stripes on the brow and cheeks
		for x, y, z, ln in ((0.1, -1.0, 1.18, 0.1), (0.2, -0.94, 1.12, 0.1), (0.05, -0.92, 1.22, 0.1)):
			_oblob(b, (0.03, ln, 0.02), (x * s, y, z), (0, 1, -0.3), (x * s, -0.4, 1), stripe, "head", segs=(5, 3))
		for k in range(2):
			_oblob(b, (0.03, 0.14, 0.02), (0.27 * s, -0.9 + 0.08 * k, 0.94), (0, 0.4, -1), (s, 0, 0), stripe, "head", segs=(5, 3))
	if old:   # three claw scars raked across the right eye (laid on the skull's surface), a grizzled muzzle
		def face(x, z):
			k2 = 1 - (x / 0.3) ** 2 - ((z - 0.98) / 0.25) ** 2
			return Vector((x, -0.88 - 0.27 * math.sqrt(max(0.0, k2)) - 0.004, z))
		for k in range(3):
			line = [face(-0.05 - 0.045 * k - 0.04 * u, 1.17 - 0.2 * u) for u in (0, 0.25, 0.5, 0.75, 1.0)]
			for p, q in zip(line, line[1:]):
				_oblob(b, (0.022, (q - p).length * 1.4, 0.012), tuple((p + q) / 2), q - p, (0, -1, 0.2), scar, "head", segs=(5, 3))
		b.blob((0.3, 0.18, 0.14), (0, -1.16, 0.94), gray, "head", segs=(8, 5))
	# the tail: long, black bands, black tip
	pts = [(0, 0.82, 0.82), (0, 1.28, 0.58), (0, 1.72, 0.42), (0, 2.02, 0.42), (0, 2.18, 0.56)]
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		bone = CAT_TAIL[min(k, 2)]
		b.seg(p, q, 0.1, 0.09 if k < 3 else 0.08, fur, bone, sides=9)
		b.blob((0.19, 0.19, 0.19), q, fur, bone, segs=(8, 6))
		for f in (0.3, 0.7):
			c = Vector(p) + (Vector(q) - Vector(p)) * f
			_oblob(b, (0.215, 0.07, 0.215), tuple(c), Vector(q) - Vector(p), (0, 0, 1), stripe, bone, segs=(9, 3))
	b.blob((0.2, 0.22, 0.22), (0, 2.2, 0.6), stripe, "tail3", segs=(8, 6))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.62), "root")
		back_leg = y > 0
		b.blob((0.3, 0.44 if back_leg else 0.36, 0.52), (x * 1.08, y + (0.04 if back_leg else 0), 0.62), fur, name_, segs=(8, 6))
		b.seg((x, y, 0.52), (x, y + (0.05 if back_leg else 0.02), 0.2), 0.11, 0.09, fur, name_, sides=8)
		b.seg((x, y + (0.05 if back_leg else 0.02), 0.2), (x, y - 0.01, 0.07), 0.09, 0.09, fur, name_, sides=8)
		b.blob((0.22, 0.26, 0.12), (x, y - 0.04, 0.06), white, name_, segs=(8, 5))              # big paws
		for k in (-1, 0, 1):
			b.blob((0.065, 0.075, 0.06), (x + 0.065 * k, y - 0.16, 0.05), white, name_, segs=(5, 4))
		for k in range(2):   # stripes round the upper leg
			_oblob(b, (0.05, 0.16, 0.02), (x * 1.5, y, 0.42 - 0.1 * k), (0, 0.5, -1), (x, 0, 0), stripe, name_, segs=(5, 3))
	_scaled(b, 1.4 if old else 1.2)
	arm = b.build()

	def tail(t, amp, cycles=1.0, flick=0.0):
		return {"tail1": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (0, 0, amp * wave(t, cycles, -0.15))},
				"tail3": {"rot": (flick, 0, amp * 1.4 * wave(t, cycles, -0.3))}}

	def idle(t):
		look = seq(t, [(0, 0), (0.3, 0), (0.4, -22), (0.62, -22), (0.72, 0)])
		return merge({"body": {"loc": (0, 0, 0.014 * wave(t, 2))}, "head": {"rot": (3 * wave(t, 1, 0.3), 0, look)}},
					 tail(t, 6, 1.0, 12 * wave(t, 3)))

	def walk(t):   # a heavy, rolling prowl
		return merge(_quad_legs(wave(t), 22), tail(t, 8),
					 {"root": {"loc": (0, 0, -0.02 + 0.015 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 0)},
					  "head": {"rot": (-4, 0, -3 * wave(t))}})

	def run(t):
		f, k = 42 * wave(t), 42 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.85, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.85, 0, 0)},
					  "root": {"loc": (0, 0, 0.08 * max(0.0, wave(t, 1, 0.25))), "rot": (7 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-6 * wave(t, 1, 0.1), 0, 0)}}, tail(t, 4, 1.0, -10))

	def attack(t):   # rears and rakes down with a forepaw, then bites
		lunge = seq(t, [(0, 0), (0.25, -0.1), (0.45, 0.4), (0.6, 0.3), (1, 0)])
		rear = seq(t, [(0, 0), (0.25, 8), (0.42, 20), (0.6, 2), (1, 0)])
		paw = seq(t, [(0, 0), (0.3, 30), (0.42, 80), (0.55, -10), (1, 0)])
		jaw = seq(t, [(0, 0), (0.35, -36), (0.5, 4), (0.7, 0)])
		return merge({"root": {"loc": (0, lunge, 0.12 * rear / 20), "rot": (rear, 0, 0)},
					  "leg_fl": {"rot": (paw, 0, 0)}, "leg_fr": {"rot": (paw * 0.3, 0, 0)},
					  "leg_bl": {"rot": (-rear, 0, 0)}, "leg_br": {"rot": (-rear, 0, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.3, 12), (0.5, -10), (1, 0)]), 0, 0)}, "jaw": {"rot": (jaw, 0, 0)}},
					 tail(t, 14, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.03 * k), "rot": (7 * k, 0, 0)}, "head": {"rot": (14 * k, 0, 12 * k)},
					  "jaw": {"rot": (-26 * k, 0, 0)}}, tail(t, 18 * k, 2))

	def death(t):
		roll = seq(t, [(0.15, 0), (0.6, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.15, 0), (0.6, -0.38)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (-12 * curl, 0, 14 * curl)}, "jaw": {"rot": (-12 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (30 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
					  "leg_bl": {"rot": (-26 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					 {"tail1": {"rot": (-8 * curl, 0, 20 * curl)}, "tail2": {"rot": (0, 0, 24 * curl)}, "tail3": {"rot": (0, 0, 20 * curl)}})

	clip(arm, "idle", 3.2, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.5, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_tigress():
	return build_tiger("tigress", old=True)


# --- the Dustpaw: jackal-folk on KayKit bodies (bolt-ons in KayKit mesh space, like the gnoll's)

def dustpaw_materials(kind="dustpaw"):
	pre = "dustpaw" if kind == "dustpaw" else f"dustpaw_{kind}"
	return {
		"fur": material(f"{pre}_fur", {"dustpaw": "c8a064", "shaman": "bc9a66", "chief": "b88a50"}[kind], 0.95),
		"fur_d": material(f"{pre}_fur_dark", {"dustpaw": "8a6a40", "shaman": "7e6444", "chief": "6e4e2c"}[kind], 0.95),
		"cream": material(f"{pre}_cream", "eadcbc", 0.95),
		"muzzle": material(f"{pre}_muzzle", "3a2c22", 0.8),
		"nose": material(f"{pre}_nose", "141010", 0.3),
		"inner": material(f"{pre}_ear_inner", "9a6a50", 0.9),
		"eye": material(f"{pre}_eye", "f0b830", 0.3, emit=1.2),
		"tooth": material(f"{pre}_tooth", "efe6d0", 0.4),
		"bone": material(f"{pre}_bone", "ece2c6", 0.6),
		"red": material(f"{pre}_ochre", "b83a1e", 0.9),
		"white": material(f"{pre}_paint", "f2ece0", 0.9),
		"bead_t": material(f"{pre}_bead_turquoise", "3aa89a", 0.4),
		"bead_r": material(f"{pre}_bead_red", "b82a20", 0.4),
		"cord": material(f"{pre}_cord", "5a4028", 0.9),
		"feather": material(f"{pre}_feather", "3a3028", 0.9),
		"gold": metal_material(f"{pre}_gold", "d8a838", 0.35, 0.7),
	}


def _jackal_head(b, m, kind):
	"""A jackal's head on the KayKit neck: a narrow skull, a long thin snout with a dark muzzle, cream
	cheeks and throat, and tall pointed ears standing straight up."""
	b.blob((0.7, 0.72, 0.7), (0, 0.06, 1.6), m["fur"], "x", segs=(12, 8))                    # skull
	b.blob((0.62, 0.5, 0.38), (0, -0.06, 1.34), m["cream"], "x", segs=(10, 6))                # cheeks and throat
	b.seg((0, -0.18, 1.52), (0, -0.84, 1.42), 0.22, 0.1, m["fur"], "x", sides=8)            # the long snout
	b.seg((0, -0.5, 1.47), (0, -0.88, 1.42), 0.14, 0.1, m["muzzle"], "x", sides=8)          # the dark muzzle
	b.blob((0.3, 0.5, 0.14), (0, -0.46, 1.3), m["cream"], "x", segs=(8, 5))                  # lower jaw
	b.blob((0.16, 0.12, 0.12), (0, -0.9, 1.45), m["nose"], "x", segs=(6, 4))
	for s in (1, -1):
		b.blob((0.13, 0.08, 0.1), (0.19 * s, -0.3, 1.7), m["eye"], "x", segs=(8, 5))
		b.blob((0.05, 0.03, 0.08), (0.2 * s, -0.34, 1.7), m["nose"], "x", segs=(4, 3))
		b.blob((0.2, 0.08, 0.05), (0.19 * s, -0.32, 1.79), m["fur_d"], "x", rot=(0, -15 * s, 0), segs=(6, 4))   # brow
		b.seg((0.12 * s, -0.3, 1.62), (0.06 * s, -0.7, 1.46), 0.025, 0.02, m["fur_d"], "x", sides=4)             # dark tear line
		# tall ears, broad at the base, standing straight up
		b.seg((0.24 * s, 0.08, 1.82), (0.34 * s, 0.14, 2.46), 0.2, 0.01, m["fur"], "x", sides=4)
		b.seg((0.25 * s, 0.02, 1.86), (0.33 * s, 0.08, 2.36), 0.13, 0.006, m["inner"], "x", sides=4)
		b.seg((0.34 * s, 0.14, 2.3), (0.345 * s, 0.145, 2.48), 0.05, 0.004, m["fur_d"], "x", sides=4)            # dark tips
		b.seg((0.1 * s, -0.66, 1.36), (0.1 * s, -0.67, 1.26), 0.03, 0.005, m["tooth"], "x", sides=4)
	b.blob((0.3, 0.5, 0.3), (0, 0.3, 1.46), m["fur_d"], "x", rot=(14, 0, 0), segs=(8, 6))    # the scruff
	if kind == "shaman":   # a bone-and-bead headdress: a brow band, bones and feathers standing up, bead strands
		_ring(b, (0, 0.04, 1.84), (0.37, 0.38), (0, -8), 0.035, m["cord"], sides=18)
		for k in range(9):
			a = -math.pi / 2 + (k - 4) * 0.34
			p = Vector((0.37 * math.cos(a), 0.04 + 0.38 * math.sin(a), 1.84 - 0.05 * math.sin(a)))
			b.blob((0.07, 0.07, 0.07), tuple(p), (m["bone"], m["bead_t"], m["bead_r"])[k % 3], "x", segs=(6, 4))
		for x, lean, mat in ((0.0, 0.0, "bone"), (0.12, 0.08, "feather"), (-0.12, -0.08, "feather"), (0.2, 0.16, "bone"), (-0.2, -0.16, "bone")):
			base = Vector((x, -0.3, 1.88))
			tip = base + Vector((lean, 0.06, 0.34 if mat == "bone" else 0.46))
			b.seg(tuple(base), tuple(tip), 0.03 if mat == "bone" else 0.05, 0.012, m[mat], "x", sides=4 if mat == "feather" else 5)
			if mat == "bone":
				b.blob((0.06, 0.05, 0.06), tuple(tip), m["bone"], "x", segs=(6, 4))
		b.blob((0.18, 0.12, 0.16), (0, -0.32, 1.86), m["bone"], "x", segs=(8, 6))            # a bird skull on the brow
		for s in (1, -1):   # bead strands hanging by the cheeks
			top = Vector((0.36 * s, -0.08, 1.8))
			for k in range(6):
				b.blob((0.055, 0.055, 0.055), tuple(top + Vector((0.01 * s * k, 0, -0.07 * k))), (m["bead_t"], m["bone"], m["bead_r"])[k % 3], "x", segs=(6, 4))
			for z in (1.62, 1.54):   # white paint stripes on the snout
				b.seg((0.08 * s, -0.4, z + 0.02), (0.1 * s, -0.62, z - 0.04), 0.018, 0.018, m["white"], "x", sides=4)
	if kind == "chief":   # a painted mane: shaggy, ochre-banded, down the back of the neck
		for k in range(8):
			a = math.pi * (k / 7)
			root = Vector((0.32 * math.cos(a), 0.2 + 0.06 * math.sin(a), 1.62 + 0.2 * math.sin(a)))
			_tuft(b, tuple(root), (math.cos(a) * 0.8, 0.8, -0.5), 0.34, 4, 0.3, (m["fur_d"], m["red"], m["fur_d"]), 800 + k, width=0.06)
		b.blob((0.62, 0.4, 0.62), (0, 0.3, 1.5), m["fur_d"], "x", segs=(10, 7))
		for k in range(3):   # ochre bands painted across the mane
			_ring(b, (0, 0.34, 1.34 + 0.14 * k), (0.3 - 0.02 * k, 0.2), (0, 20), 0.03, m["red"], sides=12, gap=(8, 12))
		for s in (1, -1):   # war paint: an ochre streak from each eye down the snout
			b.seg((0.18 * s, -0.36, 1.66), (0.09 * s, -0.62, 1.52), 0.03, 0.022, m["red"], "x", sides=4)
			b.seg((0.26 * s, -0.2, 1.62), (0.28 * s, -0.24, 1.42), 0.025, 0.02, m["red"], "x", sides=4)
		_ring(b, (0.3, 0.12, 2.1), (0.06, 0.06), (0, 70), 0.02, m["gold"], sides=10)             # a gold ring in one ear


def build_dustpaw_head():
	b = Builder("dustpaw_head")
	_jackal_head(b, dustpaw_materials("dustpaw"), "dustpaw")
	return b.build_static()


def build_dustpaw_shaman_head():
	b = Builder("dustpaw_shaman_head")
	_jackal_head(b, dustpaw_materials("shaman"), "shaman")
	return b.build_static()


def build_dustpaw_chief_head():
	b = Builder("dustpaw_chief_head")
	_jackal_head(b, dustpaw_materials("chief"), "chief")
	return b.build_static()


def _dustpaw_tail(name, kind):
	m = dustpaw_materials(kind)
	b = Builder(name)
	k = 1.2 if kind == "chief" else 1.0
	b.seg((0, 0.22, 0.58), (0, 0.46, 0.44), 0.07 * k, 0.1 * k, m["fur"], "x", sides=6)
	b.blob((0.24 * k, 0.52 * k, 0.24 * k), (0, 0.62, 0.3), m["fur"], "x", rot=(-28, 0, 0))
	b.blob((0.18 * k, 0.24 * k, 0.18 * k), (0, 0.84, 0.18), m["muzzle"], "x", rot=(-28, 0, 0))   # black tip
	return b.build_static()


def build_dustpaw_chief_trophies():
	"""The chief's trophy necklace: a thong round the neck strung with teeth, claws, a monkey's skull
	and a tiger's fang the size of a knife."""
	m = dustpaw_materials("chief")
	b = Builder("dustpaw_chief_trophies")
	n = 22
	pts = []
	for k in range(n + 1):
		a = 2 * math.pi * k / n
		front = (1 - math.cos(a)) / 2
		pts.append(Vector((0.4 * math.sin(a), 0.3 * math.cos(a) - 0.12 * front, 1.3 - 0.22 * front ** 1.5)))
	for p, q in zip(pts, pts[1:]):
		b.seg(tuple(p), tuple(q), 0.022, 0.022, m["cord"], "x", sides=4)
	for k in range(5, n - 4):
		p = pts[k]
		if k == n // 2:   # the monkey skull at the front
			b.blob((0.16, 0.12, 0.16), tuple(p + Vector((0, -0.06, -0.08))), m["bone"], "x", segs=(8, 6))
			for s in (1, -1):
				b.blob((0.04, 0.02, 0.04), tuple(p + Vector((0.035 * s, -0.12, -0.07))), m["muzzle"], "x", segs=(4, 3))
			continue
		if k in (n // 2 - 2, n // 2 + 2):   # the tiger's fangs
			b.seg(tuple(p), tuple(p + Vector((0, -0.04, -0.22))), 0.04, 0.005, m["bone"], "x", sides=5)
			continue
		b.seg(tuple(p), tuple(p + Vector((0, -0.02, -0.1))), 0.022, 0.004, m["bone"] if k % 2 else m["fur_d"], "x", sides=4)
		b.blob((0.045, 0.045, 0.045), tuple(p), (m["bead_t"], m["bead_r"])[k % 2], "x", segs=(6, 4))
	return b.build_static()


# the Rogue as a Dustpaw: sandy fur for skin, a ragged ochre tunic, dusty cape and trousers, dark paws
DUSTPAW_CELLS = {(0, 0): ("d6aa6a", "7a5a2e"), (0, 1): ("c8943e", "5e3e16"), (1, 1): ("b49a6c", "5a4a2c"),
				 (5, 0): ("6a4a2e", "2a1a0e"), (3, 0): ("e0d4b0", "8a7a5a"), (6, 0): ("e0d4b0", "8a7a5a"),
				 (7, 1): ("8a6a3a", "3a2a14"), (3, 2): ("a88458", "4a3620"), (7, 2): ("4a3a2a", "1a120a")}
# the Mage as a Dustpaw shaman: an ochre-red robe, a hide cape, bone trim, turquoise beads at the collar
DUSTPAW_SHAMAN_CELLS = {(0, 1): ("b86a30", "4a220c"), (1, 1): ("b86a30", "4a220c"), (2, 1): ("c8a878", "5e4a2a"),
						(3, 0): ("ece0c0", "8a7c5c"), (4, 0): ("ece0c0", "8a7c5c"), (5, 0): ("6a4a2e", "2a1a0e"),
						(2, 2): ("c8a878", "5e4a2a"), (7, 1): ("5a3a1e", "22140a"), (0, 2): ("4ab0a2", "1a4a44"),
						(3, 2): ("a88458", "4a3620"), (0, 0): ("ccaa70", "76582e"), (7, 2): ("ccaa70", "76582e")}
# the Barbarian as the Dustpaw chief: darker fur, ochre-red painted loincloth, a hide vest with black fur trim
DUSTPAW_CHIEF_CELLS = {(0, 0): ("c49a5a", "6a4a22"), (1, 3): ("c49a5a", "6a4a22"), (3, 1): ("be945a", "664620"),
					   (7, 1): ("a8482a", "4a1a0c"), (3, 2): ("8a6a44", "3a2a16"), (7, 0): ("9a7444", "46301a"),
					   (2, 1): ("4a3a2a", "18100a"), (6, 0): ("5a3e24", "22140a"), (6, 1): ("5a3e24", "22140a"),
					   (5, 1): ("5a3e24", "22140a"), (3, 0): ("c8983a", "6a4a14")}


# --- hungry ghosts and the Lantern Widow

def ghost_materials(kind="hungry"):
	if kind == "hungry":
		return {
			"skin": material("hungry_ghost_skin", "c4dcb0", 0.8, emit=0.15),
			"skin_d": material("hungry_ghost_skin_dark", "7e9a74", 0.85, emit=0.1),
			"hollow": material("hungry_ghost_hollow", "1a2a1e", 0.6),
			"glow": material("hungry_ghost_eye", "c8ff9a", 0.2, emit=3.0),
			"hair": material("hungry_ghost_hair", "3a4a3a", 0.9),
			"rag": material("hungry_ghost_rag", "8aa088", 0.95, emit=0.08),
			"rag_d": material("hungry_ghost_rag_dark", "56705a", 0.95, emit=0.05),
			"mist": glass_material("hungry_ghost_mist", "b8e0b0", 0.4, 0.3, emit=0.6),
			"mist_b": glass_material("hungry_ghost_mist_faint", "d0f0c8", 0.22, 0.3, emit=0.4),
		}
	return {
		"veil": glass_material("widow_veil", "e8f0ff", 0.3, 0.3, emit=0.3),
		"skin": material("widow_skin", "eef2fa", 0.8, emit=0.25),
		"hair": material("widow_hair", "1e2230", 0.8),
		"lid": material("widow_lid", "6a7894", 0.7),
		"veil_d": glass_material("widow_veil_edge", "b8c8e8", 0.7, 0.4, emit=0.2),
		"robe": material("widow_robe", "dce6f6", 0.9, emit=0.12),
		"robe_d": material("widow_robe_dark", "9aaccc", 0.9, emit=0.08),
		"mist": glass_material("widow_mist", "c8dcff", 0.4, 0.3, emit=0.6),
		"mist_b": glass_material("widow_mist_faint", "e0ecff", 0.22, 0.3, emit=0.4),
		"paper": material("widow_lantern_paper", "ffd890", 0.6, emit=2.2),
		"paper_d": material("widow_lantern_rib", "a8481e", 0.6, emit=0.4),
		"wood": material("widow_lantern_wood", "3a2a1e", 0.7),
		"tassel": material("widow_lantern_tassel", "c82a2a", 0.8),
		"flower": material("widow_flower", "f4f0ff", 0.7, emit=0.3),
	}


def build_hungry_ghost_head():
	"""A hungry ghost's head raised on a long thin neck: a gaunt, long face with hollow cheeks, deep
	sockets with pinpoint green eyes, a tiny puckered mouth and lank strands of hair."""
	m = ghost_materials("hungry")
	b = Builder("hungry_ghost_head")
	b.seg((0, 0.04, 1.14), (0, 0.0, 1.62), 0.075, 0.06, m["skin_d"], "x", sides=8)          # the thin neck
	for k in range(4):   # its knobbed rings
		b.blob((0.15, 0.15, 0.05), (0, 0.035 - 0.01 * k, 1.24 + 0.1 * k), m["skin"], "x", segs=(8, 3))
	b.blob((0.56, 0.58, 0.72), (0, 0.02, 1.9), m["skin"], "x", segs=(12, 9))                 # a long skull
	b.blob((0.4, 0.34, 0.34), (0, -0.14, 1.66), m["skin"], "x", segs=(10, 7))                # the narrow jaw
	for s in (1, -1):
		b.blob((0.16, 0.1, 0.18), (0.13 * s, -0.25, 1.94), m["hollow"], "x", segs=(8, 6))    # deep sockets
		b.blob((0.05, 0.04, 0.05), (0.13 * s, -0.28, 1.93), m["glow"], "x", segs=(6, 4))
		b.blob((0.1, 0.16, 0.2), (0.22 * s, -0.14, 1.7), m["skin_d"], "x", segs=(8, 5))     # hollow cheeks
		for k in range(3):   # lank hair hanging from the crown down the back
			x = (0.08 + 0.08 * k) * s
			b.seg((x, 0.14 + 0.03 * k, 2.14 - 0.05 * k), (x * 1.15, 0.3 + 0.02 * k, 1.5 - 0.06 * k), 0.035, 0.012, m["hair"], "x", sides=4)
	b.blob((0.07, 0.05, 0.05), (0, -0.3, 1.64), m["hollow"], "x", segs=(6, 4))               # the tiny mouth
	b.blob((0.06, 0.08, 0.1), (0, -0.3, 1.8), m["skin_d"], "x", segs=(6, 4))                 # a thin nose
	b.blob((0.4, 0.26, 0.16), (0, 0.04, 2.24), m["hair"], "x", segs=(10, 5))                 # thin hair on the crown
	return b.build_static()


def build_hungry_ghost_rags():
	"""Tattered pale-green rags hanging from the shoulders, and a mist rising off them."""
	import random
	rng = random.Random(1201)
	m = ghost_materials("hungry")
	b = Builder("hungry_ghost_rags")
	for k in range(16):
		a = 2 * math.pi * (k + 0.5) / 16
		x, y = 0.44 * math.sin(a), 0.38 * math.cos(a)
		if abs(x) < 0.16 and y < 0:
			continue
		out = Vector((math.sin(a), math.cos(a), 0))
		w = Vector((-out.y, out.x, 0)) * 0.1
		c = Vector((x, y, 1.22))
		ln = rng.uniform(0.4, 0.75)
		tip = c + out * 0.1 + Vector((0, 0, -ln))
		_slab(b, [tuple(c - w), tuple(c + w), tuple(tip + w * 0.4), tuple(tip - w * 0.2)], 0.025, (m["rag"], m["rag_d"])[k % 2])
	for k in range(4):
		a = rng.uniform(0, 2 * math.pi)
		_smoke_puff(b, (0.36 * math.sin(a), 0.32 * math.cos(a), 1.3), 0.1, (m["mist"], m["mist_b"]), rng)
	return b.build_static()


def _spirit_tail(b, m, rng, widow=False):
	"""Where the legs were: a robe falling in torn strips that fade into a trailing column of mist."""
	for k in range(14):
		a = 2 * math.pi * (k + 0.5) / 14
		out = Vector((math.sin(a), math.cos(a), 0))
		w = Vector((-out.y, out.x, 0)) * (0.13 if widow else 0.11)
		c = Vector((0.34 * math.sin(a), 0.3 * math.cos(a), 0.66))
		trail = max(0.0, math.cos(a)) * (0.3 if widow else 0.12)       # the back strips trail out behind
		ln = rng.uniform(0.34, 0.5) + trail
		tip = c + out * 0.14 + Vector((0, trail, -ln))
		mat = (m["robe"], m["robe_d"]) if widow else (m["rag"], m["rag_d"])
		_slab(b, [tuple(c - w), tuple(c + w), tuple(tip + w * 0.3), tuple(tip - w * 0.3)], 0.025, mat[k % 2])
	for k in range(6):
		u = k / 5
		r = 0.4 * (1 - 0.6 * u)
		c = (0.04 * math.sin(u * 4), (0.06 + 0.26 * u) if widow else 0.08 * u, 0.44 - 0.34 * u)
		_smoke_puff(b, c, r, (m["mist"], m["mist_b"]), rng)


def build_hungry_ghost_tail():
	import random
	b = Builder("hungry_ghost_tail")
	_spirit_tail(b, ghost_materials("hungry"), random.Random(1203))
	return b.build_static()


def build_lantern_widow_veil():
	"""Her own head (the Mage's is hidden): a pale oval face with closed eyes, long black hair down her
	back, all under a sheer bell of veil falling to the shoulders, a white funeral flower at the crown."""
	m = ghost_materials("widow")
	b = Builder("lantern_widow_veil")
	b.blob((0.66, 0.66, 0.8), (0, -0.04, 1.64), m["skin"], "x", segs=(14, 10))                # the face
	b.blob((0.8, 0.76, 0.66), (0, 0.06, 1.8), m["hair"], "x", segs=(14, 10))                  # hair over the crown, parted
	b.blob((0.7, 0.3, 0.9), (0, 0.3, 1.36), m["hair"], "x", segs=(12, 8))                     # falling down her back
	for s_ in (1, -1):
		b.blob((0.18, 0.4, 0.8), (0.34 * s_, 0.0, 1.46), m["hair"], "x", segs=(8, 6))          # long locks framing the face
		lid = [(0.15 * s_ + 0.07 * math.cos(a), -0.36, 1.66 - 0.025 * math.sin(a)) for a in (0.2, 1.0, 2.1, 2.94)]
		for p_, q_ in zip(lid, lid[1:]):   # closed eyes, curved down
			b.seg(p_, q_, 0.014, 0.014, m["lid"], "x", sides=4)
	b.blob((0.06, 0.03, 0.03), (0, -0.37, 1.46), m["lid"], "x", segs=(6, 3))                  # small mouth
	# the veil: a cap close over the head, then a sheer drape flaring out to below the shoulders
	_shell(b, (0.96, 0.94, 0.9), (0, 0.04, 1.72), m["veil"], lambda d: d.z > 0.0, segs=(18, 12))
	bm = bmesh.new()
	ring_top, ring_low = [], []
	n = 20
	for k in range(n):
		a = 2 * math.pi * k / n
		wob = 0.03 * math.sin(5 * a)
		ring_top.append(bm.verts.new((0.48 * math.cos(a), 0.04 + 0.47 * math.sin(a), 1.72)))
		ring_low.append(bm.verts.new(((0.6 + wob) * math.cos(a), 0.1 + (0.58 + wob) * math.sin(a), 1.02 + 0.12 * max(0.0, -math.sin(a)))))
	for k in range(n):
		j = (k + 1) % n
		bm.faces.new((ring_top[k], ring_top[j], ring_low[j], ring_low[k]))
	b._add(bm, m["veil"], "x")
	for k in range(n):   # its hem
		a, c = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
		p_ = [((0.6 + 0.03 * math.sin(5 * x)) * math.cos(x), 0.1 + (0.58 + 0.03 * math.sin(5 * x)) * math.sin(x), 1.02 + 0.12 * max(0.0, -math.sin(x))) for x in (a, c)]
		b.seg(p_[0], p_[1], 0.018, 0.018, m["veil_d"], "x", sides=4)
	for k in range(5):   # the flower
		a = 2 * math.pi * k / 5
		_oblob(b, (0.1, 0.16, 0.03), (0.2 + 0.07 * math.cos(a), -0.06 + 0.07 * math.sin(a), 2.24), (math.cos(a), math.sin(a), 0.3), (0, 0, 1), m["flower"], "x", segs=(6, 3))
	b.blob((0.06, 0.06, 0.05), (0.2, -0.06, 2.26), m["paper"], "x", segs=(6, 4))
	return b.build_static()


def build_lantern_widow_train():
	import random
	b = Builder("lantern_widow_train")
	_spirit_tail(b, ghost_materials("widow"), random.Random(1207), widow=True)
	return b.build_static()


def build_lantern_widow_lantern():
	"""A round paper lantern on a short black stick, held out from the left fist: glowing warm through
	its ribs, a red tassel beneath. Authored at the KayKit left hand (T pose)."""
	m = ghost_materials("widow")
	b = Builder("lantern_widow_lantern")
	# "down" here is +X: the arm hangs at her side in every clip, turning the T pose's outward into down
	hand = Vector((0.86, -0.02, 1.08))
	tip = hand + Vector((-0.06, -0.36, 0.0))
	b.seg(tuple(hand + Vector((0, 0.06, 0))), tuple(tip), 0.022, 0.018, m["wood"], "x", sides=5)
	c = tip + Vector((0.26, -0.02, 0))
	b.seg(tuple(tip), tuple(c - Vector((0.18, 0, 0))), 0.008, 0.008, m["wood"], "x", sides=3)
	b.blob((0.34, 0.3, 0.3), tuple(c), m["paper"], "x", segs=(14, 10))
	for x in (-0.1, 0.0, 0.1):
		r = 0.15 * math.sqrt(max(0.0, 1 - (x / 0.17) ** 2))
		_ring(b, tuple(c + Vector((x, 0, 0))), (r + 0.004, r + 0.004), (90, 0), 0.008, m["paper_d"], sides=14)
	for x in (0.17, -0.17):
		b.blob((0.04, 0.12, 0.12), tuple(c + Vector((x, 0, 0))), m["wood"], "x", segs=(10, 4))
	b.seg(tuple(c + Vector((0.18, 0, 0))), tuple(c + Vector((0.34, 0, 0))), 0.03, 0.012, m["tassel"], "x", sides=5)
	return b.build_static()


# the Skeleton Mage as a hungry ghost: pale green bones, a gray-green shroud
HUNGRY_GHOST_CELLS = {(1, 1): ("d8f0c8", "6a9a6a"), (2, 2): ("9ab494", "3e5a44"), (1, 2): ("7a9a7a", "2e4a34"),
					  (5, 2): ("7a9a7a", "2e4a34"), (3, 0): ("8aa088", "3e5040"), (4, 0): ("8aa088", "3e5040"),
					  (6, 0): ("56705a", "1e2e22"), (7, 0): ("56705a", "1e2e22"), (7, 3): ("e0ffc0", "8aff6a")}
# the Mage as the Lantern Widow: pale blue-white robes and skin
LANTERN_WIDOW_CELLS = {(0, 1): ("eef4ff", "8a9ab8"), (1, 1): ("eef4ff", "8a9ab8"), (2, 1): ("c8d8f0", "5a6a88"),
					   (3, 0): ("f4f8ff", "a8b8d0"), (4, 0): ("f4f8ff", "a8b8d0"), (5, 0): ("aabcd8", "4a5a78"),
					   (2, 2): ("c8d8f0", "5a6a88"), (7, 1): ("b8c8e0", "4a5a78"), (0, 2): ("f4f8ff", "a8b8d0"),
					   (3, 2): ("c8d8f0", "5a6a88"), (0, 0): ("eef2fa", "98a6c0"), (7, 2): ("eef2fa", "98a6c0")}


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
	# BODY_FINISH (by image name, defined with the bodies that use it) changes the glTF material
	# itself: a ghost's transparency and glow, a mirror's chrome
	for mat in gltf.get("materials", []) if image_name in globals().get("BODY_FINISH", {}) else []:
		fin = BODY_FINISH[image_name]
		pbr = mat.setdefault("pbrMetallicRoughness", {})
		for k in ("metallicFactor", "roughnessFactor", "baseColorFactor"):
			if k in fin:
				pbr[k] = fin[k]
		if "alpha" in fin:
			pbr["baseColorFactor"] = pbr.get("baseColorFactor", [1, 1, 1, 1])[:3] + [fin["alpha"]]
			mat["alphaMode"] = "BLEND"
		if "emissive" in fin:
			mat["emissiveFactor"] = fin["emissive"]
			if "baseColorTexture" in pbr:
				mat["emissiveTexture"] = dict(pbr["baseColorTexture"])
	blob += b"\0" * ((-len(blob)) % 4)
	js = json.dumps(gltf, separators=(",", ":")).encode()
	js += b" " * ((-len(js)) % 4)
	out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob))
	out += struct.pack("<I", len(js)) + b"JSON" + js + struct.pack("<I", len(blob)) + b"BIN\0" + bytes(blob)
	open(dst, "wb").write(out)


KAYKIT = "assets/KayKit_Adventurers_2.0_FREE/Characters/gltf/"
# the barbarian as a troll: skin (0,0 and 1,3) mossy green-gray, trousers (7,1) bare
# legs, boots (3,2) calloused feet, fur trim (2,1) and vest (7,0) shaggy moss, leather grimy
TROLL_CELLS = {(0, 0): ("98ac86", "4e6044"), (1, 3): ("98ac86", "4e6044"), (3, 1): ("8ea27c", "4a5a40"),
			   (7, 1): ("8ea27c", "4a5a40"), (3, 2): ("6e7e5e", "343e2c"), (7, 0): ("5e7434", "2a3618"),
			   (2, 1): ("6a8438", "2e3e1c"), (6, 0): ("6a5a40", "32281a"), (6, 1): ("6a5a40", "32281a"),
			   (3, 0): ("7a7a6a", "3a3a30"), (5, 1): ("6a5a40", "32281a")}
TROLL_CHIEF_CELLS = {(0, 0): ("6e8e56", "2c3e22"), (1, 3): ("6e8e56", "2c3e22"), (3, 1): ("668450", "2a3a20"),
					 (7, 1): ("668450", "2a3a20"), (3, 2): ("4e5e40", "20281a"), (7, 0): ("5e4632", "2a1c12"),
					 (2, 1): ("8e7658", "3a2c20"), (6, 0): ("5a4430", "261a10"), (6, 1): ("5a4430", "261a10"),
					 (3, 0): ("8a8474", "3e3a30"), (5, 1): ("8a2a1c", "3a100a")}
# Mage cells: robe (0,1), hat (1,1), cape (2,1), trim and cuffs (3,0) (4,0), belt and hat band (5,0),
# spellbook (2,2), under-robe (7,1), collar (0,2), boots (3,2), skin (0,0) (7,2)
MAGICIAN_CELLS = {(0, 1): ("b82a2c", "3e0a10"), (1, 1): ("b82a2c", "3e0a10"), (2, 1): ("ff9a30", "a8340c"),
				  (3, 0): ("f8da78", "9a6a1a"), (4, 0): ("f8da78", "9a6a1a"), (5, 0): ("e8a038", "7a3a10"),
				  (2, 2): ("ffb040", "b8400c"), (7, 1): ("6a1a14", "220606"), (0, 2): ("fff0c4", "d8a850"),
				  (3, 2): ("8a4a2a", "3a180c")}
# the shaman: the Mage in deep spirit-teal, a wolf-gray cape, bone trim, leather belt and boots
SHAMAN_CELLS = {(0, 1): ("2e7a6a", "0c2a24"), (1, 1): ("2e7a6a", "0c2a24"), (2, 1): ("8a7a66", "3a3024"),
				(3, 0): ("e6dcc0", "8e8266"), (4, 0): ("e6dcc0", "8e8266"), (5, 0): ("8a5a34", "3a2210"),
				(2, 2): ("b08a5a", "5a3e20"), (7, 1): ("3a2a1c", "140c06"), (0, 2): ("efe4c8", "a89a78"),
				(3, 2): ("7a5232", "2e1c0e")}
NECROMANCER_CELLS = {(0, 1): ("48424e", "0e0c12"), (1, 1): ("48424e", "0e0c12"), (2, 1): ("7e44a0", "240c34"),
					 (3, 0): ("efe6cc", "8e8468"), (4, 0): ("efe6cc", "8e8468"), (5, 0): ("5a4a62", "1a1220"),
					 (2, 2): ("a8e070", "2a5a24"), (7, 1): ("4a2a62", "140a20"), (0, 2): ("f2ead4", "b8ac90"),
					 (3, 2): ("4e4652", "18141c"), (0, 0): ("e2dcd4", "a49a94"), (7, 2): ("e2dcd4", "a49a94")}
SKELETONS = "assets/KayKit_Skeletons_1.1_FREE/characters/gltf/"
# Rogue cells: tunic (0,1), collar and cape (1,1), bracers and belt (5,0), buckles (3,0) (6,0), trousers (7,1),
# boots (3,2), gloves (7,2), skin (0,0), hair (1,0). The harpy: feathered browns, yellow scaly legs, dark talons
HARPY_CELLS = {(0, 1): ("8a6e54", "3e2e20"), (1, 1): ("5a4636", "22180e"), (5, 0): ("6a4a30", "281a0e"),
			   (6, 0): ("e0d4b8", "8a7a5c"), (3, 0): ("e0d4b8", "8a7a5c"), (7, 1): ("7a6650", "2e241a"),
			   (3, 2): ("dcae44", "7a5418"), (7, 2): ("4a3a30", "16100c"), (0, 0): ("e6d6ca", "a08a7c"),
			   (1, 0): ("9a8a78", "3a3028")}
HARPY_MATRIARCH_CELLS = {(0, 1): ("8a3024", "2e0a08"), (1, 1): ("5a1a14", "1a0606"), (5, 0): ("3a2a22", "120a08"),
						 (6, 0): ("f0e4c8", "9a8a6a"), (3, 0): ("e8b840", "8a5a10"), (7, 1): ("5a3428", "1e0e0a"),
						 (3, 2): ("dcae44", "7a5418"), (7, 2): ("2a201c", "0a0806"), (0, 0): ("dccac0", "907a70"),
						 (1, 0): ("4a3a34", "140e0c")}
# the fallen monks: the Mage in saffron robes and a maroon shawl; the abbot in crimson and gold
FALLEN_MONK_CELLS = {(0, 1): ("f0a432", "a8500e"), (1, 1): ("f0a432", "a8500e"), (2, 1): ("8e2a22", "360a0a"),
					 (3, 0): ("8e2a22", "3a0c0a"), (4, 0): ("8e2a22", "3a0c0a"), (5, 0): ("7a2418", "2e0a06"),
					 (2, 2): ("8a4a24", "3a1a0a"), (7, 1): ("7a1e18", "2a0806"), (0, 2): ("f6c050", "b86a14"),
					 (3, 2): ("8a6a4a", "3a2a1a")}
FALLEN_ABBOT_CELLS = {(0, 1): ("a01e1a", "3a0606"), (1, 1): ("a01e1a", "3a0606"), (2, 1): ("f0c048", "8a5a10"),
					  (3, 0): ("f4d060", "9a6a14"), (4, 0): ("f4d060", "9a6a14"), (5, 0): ("f0c048", "8a5a10"),
					  (2, 2): ("f0c048", "8a5a10"), (7, 1): ("5a0a0a", "1e0202"), (0, 2): ("fff0c0", "d8a850"),
					  (3, 2): ("4a2a1e", "1a0c08")}
# the barbarian as a mountain troll: blue-gray hide, the fur gone white
MOUNTAIN_TROLL_CELLS = {(0, 0): ("a4b4c2", "56667a"), (1, 3): ("a4b4c2", "56667a"), (3, 1): ("9aaab8", "526274"),
						(7, 1): ("9aaab8", "526274"), (3, 2): ("6e7a86", "2a323c"), (7, 0): ("f6f8f8", "a8b0b8"),
						(2, 1): ("e8ecee", "9aa2aa"), (6, 0): ("6a5a4a", "2a2018"), (6, 1): ("6a5a4a", "2a2018"),
						(3, 0): ("8a929a", "3a4048"), (5, 1): ("6a5a4a", "2a2018")}
# the ember cult: the Mage in soot-black and ember red; the high pyromancer in crimson and gold
EMBER_CULTIST_CELLS = {(0, 1): ("3e3636", "0e0a0a"), (1, 1): ("3e3636", "0e0a0a"), (2, 1): ("c8321a", "4a0806"),
					   (3, 0): ("e8602a", "7a200c"), (4, 0): ("e8602a", "7a200c"), (5, 0): ("6a1a10", "200604"),
					   (2, 2): ("ff8a2a", "a8300c"), (7, 1): ("2a2222", "0a0606"), (0, 2): ("5a2a20", "1e0a08"),
					   (3, 2): ("2e2826", "0c0a0a")}
HIGH_PYROMANCER_CELLS = {(0, 1): ("a81e14", "3a0404"), (1, 1): ("a81e14", "3a0404"), (2, 1): ("f4c848", "9a6414"),
						 (3, 0): ("f4d060", "a07018"), (4, 0): ("f4d060", "a07018"), (5, 0): ("3a0a06", "120202"),
						 (2, 2): ("ff9a30", "b8400c"), (7, 1): ("3a1410", "120404"), (0, 2): ("f4d060", "a07018"),
						 (3, 2): ("2e2020", "0c0606")}
# Skeleton cells: bone (1,1), iron (3,0) (4,0), leather (6,0) (7,0), cloak and robe (2,2), trims (1,2) (5,2), eyes (7,3)
CHARRED_CELLS = {(1, 1): ("5e4c42", "140e0c"), (3, 0): ("4a4442", "141212"), (4, 0): ("4a4442", "141212"),
				 (7, 0): ("3a2a22", "100a08"), (6, 0): ("3a2a22", "100a08"), (2, 2): ("d8481a", "3a0a04"),
				 (6, 2): ("5a3a2a", "1a0e08"), (2, 0): ("3a2a22", "100a08"), (7, 3): ("ffd070", "ff6a1a")}
ASH_WRAITH_CELLS = {(2, 2): ("aaa49e", "3a3634"), (1, 1): ("dedad2", "7a766e"), (7, 0): ("6a6460", "2a2624"),
					(3, 0): ("8a847e", "3a3634"), (5, 2): ("ff8a2a", "a8300c"), (1, 2): ("5a5450", "1e1a18"),
					(6, 0): ("5a5450", "1e1a18"), (3, 2): ("8a847e", "3a3634"), (7, 3): ("ffe0a0", "ff7a2a")}
ASH_LORD_CELLS = {(2, 2): ("4a4240", "141010"), (1, 1): ("bcb6ae", "5a5450"), (7, 0): ("3a3432", "121010"),
				  (3, 0): ("5a5250", "1e1a1a"), (5, 2): ("e8501a", "5a0c04"), (1, 2): ("c83a1a", "4a0a04"),
				  (6, 0): ("3a3432", "121010"), (3, 2): ("4a4240", "141010"), (7, 3): ("fff0a0", "ff8a2a")}
# Ranger cells: shirt (3,0), jerkin and bracers (7,0), scarf and cape (0,1), sleeves (6,0), belt (5,0),
# trousers (7,1), boots (3,2), quiver (6,1)
RANGER_CLASS_CELLS = {(3, 0): ("9ab468", "46602c"), (7, 0): ("6a4a2e", "2a1c10"), (0, 1): ("3e6a36", "12260e"),
					  (6, 0): ("7a6a42", "342a18"), (7, 1): ("5a4632", "221810"), (3, 2): ("5a3e28", "1e140a"),
					  (6, 1): ("7a5232", "2e1c0e"), (5, 0): ("4a3220", "1a1008")}
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
	"bone_giant_body": ("assets/KayKit_Skeletons_1.1_FREE/characters/gltf/Skeleton_Warrior.glb", "bone_giant_texture",
						{(1, 1): ("fffaec", "c8b894"), (3, 0): ("ece2c8", "9a8a6a"), (6, 0): ("a8987a", "5a4c3a"),
						 (7, 0): ("a8987a", "5a4c3a"), (7, 3): ("eaffff", "6ad8ec")}, None),
	"salt_raider_body": (KAYKIT + "Rogue.glb", "salt_raider_texture",
						 {(0, 1): ("dcc89c", "8a7450"), (1, 1): ("c4a882", "6e5838"), (3, 2): ("cfbc98", "7e6a4c")}, None),
	"raider_chief_body": (KAYKIT + "Barbarian.glb", "raider_chief_texture",
						  {(7, 0): ("d6c296", "7e6a48"), (3, 2): ("cfbc98", "7a6446"), (1, 3): ("c83a2a", "6a1410")}, None),
	"river_troll_body": (KAYKIT + "Barbarian.glb", "river_troll_texture", TROLL_CELLS, None),
	"troll_chieftain_body": (KAYKIT + "Barbarian.glb", "troll_chieftain_texture", TROLL_CHIEF_CELLS, None),
	# the pet classes: the Mage in crimson, ember-orange cape and gold trim; and in black, bone and grave-purple
	"magician_body": (KAYKIT + "Mage.glb", "magician_texture", MAGICIAN_CELLS, None),
	"necromancer_body": (KAYKIT + "Mage.glb", "necromancer_texture", NECROMANCER_CELLS, None),
	"shaman_body": (KAYKIT + "Mage.glb", "shaman_texture", SHAMAN_CELLS, None),
	# High Terrace
	"harpy_body": (KAYKIT + "Rogue.glb", "harpy_texture", HARPY_CELLS, None),
	"harpy_matriarch_body": (KAYKIT + "Rogue.glb", "harpy_matriarch_texture", HARPY_MATRIARCH_CELLS, None),
	"fallen_monk_body": (KAYKIT + "Mage.glb", "fallen_monk_texture", FALLEN_MONK_CELLS, None),
	"fallen_abbot_body": (KAYKIT + "Mage.glb", "fallen_abbot_texture", FALLEN_ABBOT_CELLS, None),
	"terrace_golem_body": (KAYKIT + "Knight.glb", "terrace_golem_texture", None, ("c8ccb2", "444a3a")),
	"mountain_troll_body": (KAYKIT + "Barbarian.glb", "mountain_troll_texture", MOUNTAIN_TROLL_CELLS, None),
	# Cinderpass
	"ember_cultist_body": (KAYKIT + "Mage.glb", "ember_cultist_texture", EMBER_CULTIST_CELLS, None),
	"high_pyromancer_body": (KAYKIT + "Mage.glb", "high_pyromancer_texture", HIGH_PYROMANCER_CELLS, None),
	"charred_dead_body": (SKELETONS + "Skeleton_Warrior.glb", "charred_dead_texture", CHARRED_CELLS, None),
	"ash_wraith_body": (SKELETONS + "Skeleton_Mage.glb", "ash_wraith_texture", ASH_WRAITH_CELLS, None),
	"ash_wraith_lord_body": (SKELETONS + "Skeleton_Mage.glb", "ash_wraith_lord_texture", ASH_LORD_CELLS, None),
	# the Ranger class: the stock Ranger (Elowen's) in forest greens and browns
	"ranger_class_body": (KAYKIT + "Ranger.glb", "ranger_class_texture", RANGER_CLASS_CELLS, None),
	# Reedmere
	"pondkin_body": (KAYKIT + "Barbarian.glb", "pondkin_texture", PONDKIN_CELLS, None),
	"pondkin_mudcaller_body": (KAYKIT + "Barbarian.glb", "pondkin_mudcaller_texture", MUDCALLER_CELLS, None),
	"pondkin_bloatking_body": (KAYKIT + "Barbarian.glb", "pondkin_bloatking_texture", BLOATKING_CELLS, None),
	"sunken_villager_body": (KAYKIT + "Rogue.glb", "sunken_villager_texture", SUNKEN_CELLS, None),
	"sunken_headwoman_body": (KAYKIT + "Mage.glb", "sunken_headwoman_texture", SUNKEN_HEADWOMAN_CELLS, None),
	"sedge_sister_body": (KAYKIT + "Mage.glb", "sedge_sister_texture", SEDGE_CELLS, None),
	"mother_marrowroot_body": (KAYKIT + "Mage.glb", "mother_marrowroot_texture", MARROWROOT_CELLS, None),
	# Drownfast
	"tidesworn_body": (KAYKIT + "Knight.glb", "tidesworn_texture", TIDESWORN_CELLS, None),
	"tide_knight_body": (KAYKIT + "Knight.glb", "tide_knight_texture", TIDE_KNIGHT_CELLS, None),
	"tideking_body": (KAYKIT + "Knight.glb", "tideking_texture", TIDEKING_CELLS, None),
	"naga_body": (KAYKIT + "Rogue.glb", "naga_texture", NAGA_CELLS, None),
	"naga_tidecaller_body": (KAYKIT + "Rogue.glb", "naga_tidecaller_texture", NAGA_TIDECALLER_CELLS, None),
	"naga_queen_body": (KAYKIT + "Rogue.glb", "naga_queen_texture", NAGA_QUEEN_CELLS, None),
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
			   "cult_hood": build_cult_hood, "cult_hierophant_hood": build_cult_hierophant_hood,
			   "bone_giant_head": build_bone_giant_head, "bone_titan_head": build_bone_titan_head,
			   "bone_giant_chest": build_bone_giant_chest, "bone_bracer_l": build_bone_bracer_l,
			   "bone_bracer_r": build_bone_bracer_r,
			   "raider_wrap": build_raider_wrap, "raider_chief_turban": build_raider_chief_turban,
			   "raider_chief_chest": build_raider_chief_chest,
			   "troll_head": build_troll_head, "troll_chief_head": build_troll_chief_head, "troll_back": build_troll_back,
			   "troll_chief_back": build_troll_chief_back, "troll_loincloth": build_troll_loincloth,
			   "troll_chief_loincloth": build_troll_chief_loincloth, "troll_fist_l": build_troll_fist_l,
			   "troll_fist_r": build_troll_fist_r, "troll_chief_fist_l": build_troll_chief_fist_l,
			   "troll_chief_fist_r": build_troll_chief_fist_r, "magician_amulet": build_magician_amulet,
			   "necromancer_clasp": build_necromancer_clasp, "necromancer_pauldron": build_necromancer_pauldron,
			   "shaman_mantle": build_shaman_mantle, "shaman_totem": build_shaman_totem,
			   "harpy_head": build_harpy_head, "harpy_matriarch_head": build_harpy_matriarch_head,
			   "harpy_wings": build_harpy_wings, "harpy_matriarch_wings": build_harpy_matriarch_wings,
			   "harpy_talon_l": build_harpy_talon_l, "harpy_talon_r": build_harpy_talon_r,
			   "monk_head": build_monk_head, "abbot_head": build_abbot_head, "prayer_beads": build_prayer_beads,
			   "abbot_hat": build_abbot_hat, "terrace_golem_head": build_terrace_golem_head,
			   "terrace_colossus_head": build_terrace_colossus_head, "terrace_golem_chest": build_terrace_golem_chest,
			   "mountain_troll_head": build_mountain_troll_head, "mountain_troll_back": build_mountain_troll_back,
			   "mountain_troll_loincloth": build_mountain_troll_loincloth,
			   "mountain_troll_fist_l": build_mountain_troll_fist_l, "mountain_troll_fist_r": build_mountain_troll_fist_r,
			   "ember_hood": build_ember_hood, "high_pyromancer_hood": build_high_pyromancer_hood,
			   "charred_embers": build_charred_embers, "ash_tail": build_ash_tail, "ash_lord_tail": build_ash_lord_tail,
			   "ash_shroud": build_ash_shroud, "ash_lord_shroud": build_ash_lord_shroud, "ash_lord_crown": build_ash_lord_crown,
			   "ranger_mantle": build_ranger_mantle,
			   "race_ears_elf": build_race_ears_elf, "race_ears_gnome": build_race_ears_gnome,
			   "race_beard_dwarf": build_race_beard_dwarf, "race_beard_barbarian": build_race_beard_barbarian,
			   "race_tusks_troll": build_race_tusks_troll, "race_troll_face": build_race_troll_face,
			   "race_tusks_ogre": build_race_tusks_ogre, "race_ogre_face": build_race_ogre_face,
			   # Reedmere
			   "pondkin_head": build_pondkin_head, "pondkin_mudcaller_head": build_pondkin_mudcaller_head,
			   "pondkin_bloatking_head": build_pondkin_bloatking_head, "pondkin_chest": build_pondkin_chest,
			   "pondkin_mudcaller_chest": build_pondkin_mudcaller_chest, "pondkin_bloatking_chest": build_pondkin_bloatking_chest,
			   "pondkin_belly": lambda: _pond_belly("pondkin_belly", "pondkin"),
			   "pondkin_mudcaller_belly": lambda: _pond_belly("pondkin_mudcaller_belly", "mudcaller"),
			   "pondkin_bloatking_belly": lambda: _pond_belly("pondkin_bloatking_belly", "bloatking"),
			   "pondkin_skirt": lambda: _pond_skirt("pondkin_skirt", "pondkin"),
			   "pondkin_mudcaller_skirt": lambda: _pond_skirt("pondkin_mudcaller_skirt", "mudcaller"),
			   "pondkin_bloatking_skirt": lambda: _pond_skirt("pondkin_bloatking_skirt", "bloatking"),
			   "sunken_head": build_sunken_head, "sunken_chest": build_sunken_chest, "sunken_hips": build_sunken_hips,
			   "sunken_headwoman_crown": build_sunken_headwoman_crown, "sunken_headwoman_shawl": build_sunken_headwoman_shawl,
			   "sedge_sister_head": build_sedge_sister_head, "sedge_sister_chest": build_sedge_sister_chest,
			   "mother_marrowroot_head": build_mother_marrowroot_head, "mother_marrowroot_chest": build_mother_marrowroot_chest}
for _kind, _pre in (("pondkin", "pondkin"), ("mudcaller", "pondkin_mudcaller"), ("bloatking", "pondkin_bloatking")):
	for _s, _side in ((1, "l"), (-1, "r")):
		ATTACHMENTS[f"{_pre}_hand_{_side}"] = (lambda n, s, k: lambda: _pond_hand(n, s, k))(f"{_pre}_hand_{_side}", _s, _kind)
		ATTACHMENTS[f"{_pre}_foot_{_side}"] = (lambda n, s, k: lambda: _pond_foot(n, s, k))(f"{_pre}_foot_{_side}", _s, _kind)
# Drownfast
ATTACHMENTS.update({"tidesworn_helm": build_tidesworn_helm, "tidesworn_chest": build_tidesworn_chest,
					"tidesworn_hips": build_tidesworn_hips, "tide_knight_helm": build_tide_knight_helm,
					"tide_knight_cloak": build_tide_knight_cloak, "tideking_crown": build_tideking_crown,
					"tideking_mantle": build_tideking_mantle})
for _kind in ("naga", "naga_tidecaller", "naga_queen"):
	ATTACHMENTS[f"{_kind}_head"] = (lambda k: lambda: _naga_build_head(k))(_kind)
	ATTACHMENTS[f"{_kind}_tail"] = (lambda k: lambda: _naga_tail(k))(_kind)
	if _kind != "naga":
		ATTACHMENTS[f"{_kind}_jewels"] = (lambda k: lambda: _naga_jewels(k))(_kind)
		ATTACHMENTS[f"{_kind}_armband_l"] = (lambda k: lambda: _naga_armband(k, 1))(_kind)
		ATTACHMENTS[f"{_kind}_armband_r"] = (lambda k: lambda: _naga_armband(k, -1))(_kind)
CREATURES = {"rat": build_rat, "fire_beetle": build_beetle, "wolf": build_wolf, "dire_wolf": build_dire_wolf,
			 "bear": build_bear, "spider": build_spider, "mire_toad": build_toad, "snapping_turtle": build_turtle,
			 "bog_leech": build_leech, "boar": build_boar, "mountain_ram": build_ram, "sunhawk": build_sunhawk,
			 "giant_scorpion": build_scorpion, "scorpion_queen": build_scorpion_queen, "salt_basilisk": build_basilisk,
			 "water_elemental": build_elemental, "storm_elemental": build_storm_elemental, "giant_frog": build_frog,
			 "river_croc": build_croc, "ancient_croc": build_ancient_croc, "earth_elemental": build_earth_elemental,
			 "fire_elemental": build_fire_elemental, "air_elemental": build_air_elemental, "spirit_wolf": build_spirit_wolf,
			 "griffon": build_griffon, "griffon_matriarch": build_griffon_matriarch,
			 "snow_leopard": build_snow_leopard, "ghost_leopard": build_ghost_leopard, "mountain_yak": build_yak,
			 "gargoyle": build_gargoyle,
			 "magma_golem": build_magma_golem, "magma_colossus": build_magma_colossus,
			 "ash_drake": build_ash_drake, "cinder_drake": build_cinder_drake, "lava_salamander": build_salamander,
			 "forest_hawk": build_forest_hawk,
			 # Reedmere
			 "reedstalker": build_reedstalker, "old_stilt_legs": build_old_stilt_legs, "marsh_eel": build_marsh_eel,
			 "bogwing": build_bogwing, "bog_lurker": build_bog_lurker,
			 # Drownfast
			 "tempest_spirit": build_tempest_spirit, "stormbound_warden": build_stormbound_warden,
			 "causeway_crab": build_causeway_crab, "old_chitterjaw": build_old_chitterjaw, "shellback": build_shellback}
# Dewstep
CREATURES.update({"lantern_moth": build_lantern_moth, "rice_beetle": build_rice_beetle, "paddy_rat": build_paddy_rat,
				  "temple_monkey": build_monkey, "monkey_troop_king": build_monkey_troop_king, "jackal": build_jackal,
				  "cobra": build_cobra, "tiger": build_tiger, "tigress": build_tigress, "lantern_wisp": build_lantern_wisp})
ATTACHMENTS.update({"dustpaw_head": build_dustpaw_head, "dustpaw_shaman_head": build_dustpaw_shaman_head,
					"dustpaw_chief_head": build_dustpaw_chief_head, "dustpaw_chief_trophies": build_dustpaw_chief_trophies,
					"dustpaw_tail": lambda: _dustpaw_tail("dustpaw_tail", "dustpaw"),
					"dustpaw_chief_tail": lambda: _dustpaw_tail("dustpaw_chief_tail", "chief"),
					"hungry_ghost_head": build_hungry_ghost_head, "hungry_ghost_rags": build_hungry_ghost_rags,
					"hungry_ghost_tail": build_hungry_ghost_tail, "lantern_widow_veil": build_lantern_widow_veil,
					"lantern_widow_train": build_lantern_widow_train, "lantern_widow_lantern": build_lantern_widow_lantern})
BODIES.update({"dustpaw_body": (KAYKIT + "Rogue.glb", "dustpaw_texture", DUSTPAW_CELLS, None),
			   "dustpaw_shaman_body": (KAYKIT + "Mage.glb", "dustpaw_shaman_texture", DUSTPAW_SHAMAN_CELLS, None),
			   "dustpaw_chief_body": (KAYKIT + "Barbarian.glb", "dustpaw_chief_texture", DUSTPAW_CHIEF_CELLS, None),
			   "hungry_ghost_body": (SKELETONS + "Skeleton_Mage.glb", "hungry_ghost_texture", HUNGRY_GHOST_CELLS, None),
			   "lantern_widow_body": (KAYKIT + "Mage.glb", "lantern_widow_texture", LANTERN_WIDOW_CELLS, None)})
# ================================================================ Blackglass (the Ashfall, 31-35)
# Plains of black volcanic glass with orange cracks glowing in them. Everything here is
# glossy black obsidian with fire (or, for the dead, pale blue ghost-light) showing through
# its seams: the glass golem and its colossus, the obsidian drake and the named wyrm, glass
# spiders and their brood queen (own rigs), and the glassbound dead (KayKit skeleton reskins
# with glass shard bolt-ons). Everything below belongs to Blackglass; other zones' creatures
# go elsewhere.

def blackglass_materials(p):
	def gloss(n, hexc, rough, metallic):
		m = material(f"{p}_{n}", hexc, rough)
		m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = metallic
		return m
	return {
		"glass": gloss("glass", "26242f", 0.12, 0.35),
		"glass_l": gloss("glass_light", "4a4660", 0.1, 0.45),
		"glass_d": gloss("glass_dark", "121118", 0.12, 0.25),
		"sheen": gloss("sheen", "8a84aa", 0.06, 0.6),        # faces catching the light
		"seam": material(f"{p}_seam", "d8400c", 0.5, emit=2.0),
		"hot": material(f"{p}_hot", "ff5a14", 0.35, emit=2.4),
		"core": material(f"{p}_core", "ffb860", 0.2, emit=4.0),
		"eye": material(f"{p}_eye", "ffa040", 0.1, emit=3.0),
		"ghost": material(f"{p}_ghost", "9ae4ff", 0.2, emit=2.4),
		"ghost_b": material(f"{p}_ghost_b", "4ab4ff", 0.3, emit=1.8),
	}


def _shard(b, base, direction, length, width, mat, bone, flat=0.45, twist=0.0, sides=4, collar=0.28):
	"""A blade of glass: a short flattened prism (the collar) drawn out to a sharp point along
	`direction`; `flat` thins it, `twist` turns the blade about its own axis."""
	d = Vector(direction).normalized()
	ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
	x = ref.cross(d).normalized()
	x = Matrix.Rotation(math.radians(twist), 3, d) @ x
	y = d.cross(x)
	frame = Matrix((x, y, d)).transposed().to_4x4()
	m = Matrix.Translation(Vector(base)) @ frame @ Matrix.Diagonal(Vector((width, width * flat, length, 1.0)))
	bm = bmesh.new()
	c1 = bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=0.4, radius2=0.5, depth=collar)
	bmesh.ops.translate(bm, vec=(0, 0, collar / 2), verts=c1["verts"])
	c2 = bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=0.5, radius2=0.0, depth=1 - collar)
	bmesh.ops.translate(bm, vec=(0, 0, collar + (1 - collar) / 2), verts=c2["verts"])
	bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
	b._add(bm, mat, bone)


def _glass_plate(b, size, loc, mat, bone, rng, rot=(0, 0, 0), jitter=0.1):
	"""A slab of obsidian: a box with its corners knocked askew, so its faces catch the light unevenly."""
	bm = bmesh.new()
	bmesh.ops.create_cube(bm, size=1.0)
	bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges), offset=0.12, segments=1, affect="EDGES")   # chamfers catch the light
	for v in bm.verts:
		v.co += Vector((rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)))
	m = Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot]), Vector(size))
	bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
	b._add(bm, mat, bone)


def _glass_scale(b, center, normal, w, h, thick, mat, bone, rng):
	"""A faceted chip of glass lying on a surface: an icosphere flattened along `normal`."""
	z = Vector(normal).normalized()
	ref = Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((0, 1, 0))
	x = ref.cross(z).normalized()
	y = z.cross(x)
	bm = bmesh.new()
	bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.5)
	for v in bm.verts:
		v.co *= 1 + rng.uniform(-0.12, 0.12)
	frame = Matrix((x, y, z)).transposed().to_4x4()
	m = Matrix.Translation(Vector(center)) @ frame @ Matrix.Diagonal(Vector((w, h, thick, 1.0)))
	bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
	b._add(bm, mat, bone)


def _shard_cluster(b, base, direction, count, length, width, mats, bone, rng, spread=0.45):
	"""A clump of shards growing out of one spot, the longest in the middle."""
	d = Vector(direction).normalized()
	for k in range(count):
		v = (d + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * spread * (0 if k == 0 else 1)).normalized()
		ln = length * (1.0 if k == 0 else rng.uniform(0.45, 0.8))
		off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * width * 0.6 * (0 if k == 0 else 1)
		_shard(b, tuple(Vector(base) + off - v * ln * 0.08), tuple(v), ln, width * (1.0 if k == 0 else 0.75),
			   mats[k % len(mats)], bone, twist=rng.uniform(0, 180))


# ---------------------------------------------------------------- glass golem and the glass colossus

def build_glass_golem(name="glass_golem", colossus=False):
	"""A hulking construct of black obsidian slabs over a molten core that glows through every gap;
	shard blades at the thighs, forearms and back. The colossus is far bigger, its chest broken
	open on the core and spires of glass growing from its shoulders."""
	import random
	rng = random.Random(311 if colossus else 307)
	m = blackglass_materials(name)
	g, gl, gd, sh, seam, hot = m["glass"], m["glass_l"], m["glass_d"], m["sheen"], m["seam"], m["hot"]
	b = Builder(name)
	b.bone("root", (0, 0, 0.05))
	b.bone("hips", (0, 0, 0.9), "root")
	b.bone("chest", (0, 0, 1.35), "hips")
	b.bone("head", (0, -0.24, 2.02), "chest")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"leg_{side}", (0.36 * s, 0, 0.88), "hips")
		b.bone(f"shoulder_{side}", (0.68 * s, 0, 2.02), "chest")
		b.bone(f"arm_{side}", (0.8 * s, 0, 1.88), "chest")
		b.bone(f"hand_{side}", (0.98 * s, -0.04, 1.36), f"arm_{side}")

	# legs: a molten core in each, cased in slabs of glass
	for s in (1, -1):
		leg = f"leg_{'l' if s > 0 else 'r'}"
		b.seg((0.36 * s, 0.0, 0.9), (0.38 * s, -0.02, 0.2), 0.16, 0.16, seam, leg, sides=8)
		_glass_plate(b, (0.5, 0.48, 0.4), (0.37 * s, 0.02, 0.7), g, leg, rng, rot=(4, 0, 8 * s))
		_glass_plate(b, (0.42, 0.42, 0.26), (0.39 * s, -0.02, 0.38), gl, leg, rng, rot=(-6, 0, -10 * s))
		_glass_plate(b, (0.56, 0.78, 0.22), (0.4 * s, -0.12, 0.12), gd, leg, rng)
		_shard(b, (0.54 * s, 0.02, 0.66), (0.9 * s, 0.25, 0.55), 0.44, 0.15, sh, leg, twist=30)
		_shard(b, (0.52 * s, -0.08, 0.36), (0.9 * s, -0.2, 0.2), 0.22, 0.1, gl, leg, twist=60)
		for k in (-1, 0, 1):   # toe blades
			_shard(b, (0.4 * s + 0.14 * k, -0.46, 0.1), (0.1 * k, -1, 0.15), 0.16, 0.09, gd, leg)
		_zigzag(b, [(0.3 * s, -0.25, 0.84), (0.38 * s, -0.26, 0.7), (0.33 * s, -0.25, 0.56)], 0.03, seam, leg)
	# the pelvis
	b.blob((0.84, 0.6, 0.4), (0, 0.02, 0.98), seam, "hips", segs=(12, 7))
	_glass_plate(b, (0.98, 0.66, 0.36), (0, 0.04, 0.9), gd, "hips", rng)
	for k in range(5):
		a = 2 * math.pi * k / 5 + 0.3
		_glass_plate(b, (0.3, 0.26, 0.2), (0.5 * math.cos(a), 0.34 * math.sin(a), 1.12), g if k % 2 else gl, "hips", rng,
					 rot=(0, 0, math.degrees(a)))
	# the torso: a molten body, cased in great slabs with glowing gaps
	b.blob((1.0, 0.72, 0.88), (0, 0.06, 1.6), seam, "chest", segs=(14, 10))
	if colossus:   # the chest broken open on a white-hot core, a cage of shards round it
		b.blob((0.7, 0.34, 0.8), (0, -0.2, 1.56), seam, "chest", segs=(12, 8))
		b.blob((0.5, 0.3, 0.58), (0, -0.24, 1.56), hot, "chest", segs=(12, 8))
		b.blob((0.24, 0.2, 0.28), (0, -0.33, 1.58), m["core"], "chest", segs=(10, 7))
		for k in range(6):   # cracks running out from the wound across the slabs
			a = 2 * math.pi * (k + 0.3) / 6
			c, d = math.cos(a), math.sin(a)
			_zigzag(b, [(0.3 * c, -0.44, 1.56 + 0.34 * d), (0.4 * c + 0.03, -0.45, 1.56 + 0.44 * d),
						(0.52 * c, -0.44, 1.56 + 0.52 * d - 0.03)], 0.028, seam, "chest")
		plates = (((0.46, 0.44, 0.62), (0.4, -0.2, 1.72), g), ((0.44, 0.44, 0.6), (-0.4, -0.2, 1.74), gl),
				  ((0.5, 0.4, 0.34), (0.34, -0.24, 1.26), gd), ((0.5, 0.4, 0.34), (-0.36, -0.22, 1.28), g))
		for k in range(9):
			a = 2 * math.pi * k / 9
			base = Vector((0.34 * math.cos(a), -0.36, 1.56 + 0.4 * math.sin(a)))
			out = Vector((math.cos(a) * 0.5, -1.0, math.sin(a) * 0.5))
			_shard(b, tuple(base), tuple(out), 0.42 if k % 2 else 0.3, 0.13, sh if k % 2 else gl, "chest", twist=math.degrees(a))
	else:
		b.blob((0.2, 0.12, 0.22), (0, -0.32, 1.52), m["core"], "chest", segs=(10, 7))   # the heart, glimpsed between slabs
		plates = (((0.64, 0.44, 0.6), (0.3, -0.24, 1.72), g), ((0.62, 0.44, 0.58), (-0.3, -0.24, 1.74), gl),
				  ((0.68, 0.4, 0.44), (0.24, -0.26, 1.28), gd), ((0.64, 0.42, 0.44), (-0.28, -0.24, 1.3), g))
	plates += (((1.08, 0.56, 0.68), (0, 0.34, 1.64), gd), ((0.6, 0.5, 0.54), (0.48, 0.14, 1.42), g),
			   ((0.58, 0.5, 0.54), (-0.48, 0.12, 1.44), gl), ((0.88, 0.5, 0.34), (0, 0.24, 2.04), g))
	for k, (size, loc, mat) in enumerate(plates):
		_glass_plate(b, size, loc, mat, "chest", rng, rot=(rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(-8, 8)))
	if not colossus:
		for pts in (((0.02, -0.47, 1.98), (-0.03, -0.48, 1.84), (0.02, -0.47, 1.72)),
					((-0.12, -0.48, 1.14), (-0.06, -0.47, 1.04), (-0.12, -0.44, 0.98)),
					((0.36, -0.47, 1.86), (0.3, -0.48, 1.74), (0.38, -0.47, 1.62)),
					((-0.4, -0.47, 1.9), (-0.34, -0.48, 1.8), (-0.42, -0.47, 1.66), (-0.36, -0.46, 1.56))):
			_zigzag(b, list(pts), 0.034, seam, "chest")
	for k in range(5):   # blades of glass along the spine
		z = 1.3 + k * 0.17
		_shard(b, (0.0, 0.52, z), (0, 1, 0.6 + 0.2 * k), 0.36 + 0.06 * (2 - abs(k - 2)), 0.14, sh if k % 2 else g, "chest", twist=90)
	# shoulders: slabs with shards; the colossus has spires of glass
	for s in (1, -1):
		sh_b = f"shoulder_{'l' if s > 0 else 'r'}"
		b.blob((0.46, 0.42, 0.22), (0.66 * s, 0.04, 2.0), hot, sh_b, segs=(10, 6))
		_glass_plate(b, (0.8, 0.72, 0.3), (0.7 * s, 0.04, 2.1), g, sh_b, rng, rot=(0, 16 * s, 0))
		_glass_plate(b, (0.48, 0.48, 0.24), (0.78 * s, 0.1, 2.26), gl, sh_b, rng, rot=(0, 22 * s, 0))
		if colossus:
			for d, ln, w, mat in (((0.2 * s, 0.1, 1), 1.05, 0.2, g), ((0.5 * s, 0.25, 1), 0.78, 0.16, sh),
								  ((0.1 * s, 0.5, 1), 0.66, 0.15, gl), ((0.6 * s, -0.3, 1), 0.5, 0.12, g),
								  ((-0.1 * s, 0.3, 1), 0.46, 0.12, sh)):
				_shard(b, (0.74 * s, 0.1, 2.28), d, ln, w, mat, sh_b, twist=rng.uniform(0, 90))
			_zigzag(b, [(0.72 * s, -0.33, 2.14), (0.8 * s, -0.33, 2.06), (0.74 * s, -0.33, 1.98)], 0.03, seam, sh_b)
		else:
			_shard(b, (0.74 * s, 0.14, 2.3), (0.3 * s, 0.2, 1), 0.56, 0.17, sh, sh_b, twist=20)
			_shard(b, (0.58 * s, 0.26, 2.24), (0.2 * s, 0.5, 1), 0.4, 0.14, gl, sh_b, twist=70)
			_shard(b, (0.9 * s, 0.0, 2.2), (0.9 * s, -0.1, 0.6), 0.34, 0.12, g, sh_b, twist=40)
	# the head: a faceted block sunk between the shoulders, burning eye slits and a molten mouth
	b.blob((0.4, 0.4, 0.34), (0, -0.26, 2.0), seam, "head", segs=(10, 7))
	_glass_plate(b, (0.52, 0.48, 0.42), (0, -0.24, 2.06), g, "head", rng, jitter=0.07)
	_glass_plate(b, (0.6, 0.22, 0.14), (0, -0.46, 2.18), gl, "head", rng, rot=(-10, 0, 0), jitter=0.05)   # the brow ledge
	_glass_plate(b, (0.4, 0.22, 0.14), (0, -0.42, 1.86), gd, "head", rng)                               # the jaw
	for s in (1, -1):
		_oblob(b, (0.14, 0.05, 0.05), (0.12 * s, -0.505, 2.06), (s, 0, -0.25 * s), (0, -1, 0), m["eye"], "head", segs=(8, 4))
	b.blob((0.24, 0.05, 0.05), (0, -0.54, 1.94), hot, "head", segs=(8, 4))
	for k in range(3):   # a crest of shards
		_shard(b, (0.0, -0.2 + 0.1 * k, 2.24), (0, 0.4 + 0.3 * k, 1), 0.26 - 0.04 * k, 0.1, sh if k == 0 else g, "head", twist=90)
	if colossus:   # a crown of shards
		for k in range(7):
			a = math.pi * (k + 0.5) / 7
			base = (0.22 * math.cos(a), -0.24 - 0.14 * math.sin(a), 2.22)
			_shard(b, base, (0.5 * math.cos(a), -0.3 * math.sin(a), 1), 0.44 - 0.1 * abs(k - 3) / 3, 0.1, sh if k % 2 else gl, "head", twist=math.degrees(a))
	# arms: stacked slabs round molten cores; fists of raw glass with shard knuckles
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		b.seg((0.82 * s, 0.0, 1.9), (0.96 * s, -0.04, 1.36), 0.14, 0.12, seam, arm, sides=8)
		_glass_plate(b, (0.46, 0.46, 0.5), (0.86 * s, 0.0, 1.66), g, arm, rng, rot=(0, -8 * s, 6))
		_glass_plate(b, (0.3, 0.3, 0.26), (0.8 * s, 0.02, 1.9), gd, arm, rng)
		b.seg((0.96 * s, -0.04, 1.36), (1.0 * s, -0.08, 0.84), 0.13, 0.15, seam, hand, sides=8)
		_glass_plate(b, (0.38, 0.38, 0.3), (0.96 * s, -0.04, 1.38), gd, hand, rng)
		_glass_plate(b, (0.52, 0.5, 0.48), (1.0 * s, -0.06, 1.1), gl, hand, rng, rot=(0, 6 * s, 0))
		_rock(b, (0.72, 0.68, 0.56), (1.02 * s, -0.1, 0.76), g, hand, rng, jitter=0.12)       # the fist
		_shard(b, (1.2 * s, 0.1, 1.12), (0.5 * s, 0.6, 0.5), 0.62, 0.17, sh, hand, twist=90)  # a blade off the forearm
		_shard(b, (1.18 * s, -0.1, 0.9), (0.8 * s, 0.2, -0.2), 0.3, 0.1, gl, hand, twist=30)
		for k in range(3):
			_shard(b, ((0.88 + 0.14 * k) * s, -0.38, 0.76), (0.15 * (k - 1) * s, -1, -0.3), 0.22, 0.1, sh if k == 1 else gl, hand)
		_zigzag(b, [(1.24 * s, -0.14, 1.2), (1.27 * s, -0.1, 1.04), (1.25 * s, -0.16, 0.92)], 0.03, seam, hand)
		_zigzag(b, [(0.9 * s, -0.44, 0.9), (1.0 * s, -0.46, 0.8), (0.94 * s, -0.45, 0.68)], 0.028, seam, hand)
	_scaled(b, 1.3 if colossus else 1.04)
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, 0, 0)}, "hand_r": {"rot": (bend, 0, 0)}}

	def idle(t):   # the core breathes; the head turns, slow and heavy
		return merge_scaled({"chest": {"rot": (2 * wave(t), 0, 0)}, "head": {"rot": (-2 * wave(t), 0, 7 * wave(t, 1, 0.3))},
							 "shoulder_l": {"rot": (0, 1.5 * wave(t), 0)}, "shoulder_r": {"rot": (0, -1.5 * wave(t), 0)},
							 "hips": {"loc": (0, 0, -0.02 * (1 + wave(t)))}},
							arms(3 * wave(t, 1, 0.1), 3 * wave(t, 1, 0.6), 5, 8))

	def stride(t, swing, lean, bob):
		drop = -bob * (0.5 + 0.5 * wave(t, 2, 0.25))
		return merge_scaled({"leg_l": {"rot": (swing * wave(t), 0, 0)}, "leg_r": {"rot": (-swing * wave(t), 0, 0)},
							 "hips": {"rot": (0, 6 * wave(t), 0), "loc": (0, 0, drop)},
							 "chest": {"rot": (lean, -4 * wave(t), -7 * wave(t))}, "head": {"rot": (-lean * 0.5, 0, 4 * wave(t))}},
							arms(-swing * 0.7 * wave(t), swing * 0.7 * wave(t), 6, 12))

	def walk(t):
		return stride(t, 18, -5, 0.09)

	def run(t):
		return stride(t, 28, -12, 0.12)

	def attack(t):   # a backhand sweep of the bladed right arm, then the left fist follows through
		r = seq(t, [(0, 0), (0.35, 70), (0.55, 20), (0.8, 10), (1, 0)])
		ry = seq(t, [(0, 0), (0.35, -40), (0.55, 55), (0.8, 40), (1, 0)])
		twist = seq(t, [(0, 0), (0.35, 22), (0.55, -26), (0.8, -18), (1, 0)])
		l = seq(t, [(0, 0), (0.45, 0), (0.62, 60), (0.8, 40), (1, 0)])
		surge = seq(t, [(0, 0), (0.35, -0.04), (0.55, 0.18), (0.85, 0.12), (1, 0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "chest": {"rot": (-8 * (surge > 0.05), 0, twist)},
							 "hips": {"rot": (0, 0, twist * 0.3)}, "head": {"rot": (0, 0, -twist * 0.5)},
							 "arm_r": {"rot": (r, -10, ry)}, "hand_r": {"rot": (-10, 0, 0)},
							 "arm_l": {"rot": (l, 10, 0)}, "hand_l": {"rot": (8, 0, 0)},
							 "leg_l": {"rot": (-6, 0, 0)}, "leg_r": {"rot": (6, 0, 0)}})

	def slam(t):   # the colossus heaves both fists up and brings them down
		up = seq(t, [(0, 0), (0.45, 150), (0.55, 156), (0.66, 30), (0.82, 26), (1, 0)])
		lean = seq(t, [(0, 0), (0.45, 10), (0.55, 12), (0.66, -28), (0.82, -24), (1, 0)])
		sink = seq(t, [(0, 0), (0.45, 0.04), (0.66, -0.16), (0.86, -0.12), (1, 0)])
		surge = seq(t, [(0, 0), (0.55, -0.05), (0.66, 0.22), (0.86, 0.18), (1, 0)])
		bend = seq(t, [(0, 0), (0.45, 20), (0.62, -10), (1, 0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "hips": {"loc": (0, 0, sink), "rot": (lean * 0.3, 0, 0)},
							 "chest": {"rot": (lean * 0.7, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
							 "leg_l": {"rot": (-lean * 0.3 + 6, 0, 0)}, "leg_r": {"rot": (-lean * 0.3 - 6, 0, 0)}},
							arms(up, up, 8, bend))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"chest": {"rot": (8 * k, 5 * k, 6 * k)}, "head": {"rot": (8 * k, 0, 8 * k)},
							 "hips": {"loc": (0, -0.06 * k, 0)}}, arms(-12 * k, -8 * k, 8 * k, -8 * k))

	def death(t):   # the glass cracks through and it falls apart into a heap of slabs
		reel = seq(t, [(0, 0), (0.15, 10), (0.3, -8), (0.4, 0)])
		f = seq(t, [(0.3, 0), (0.7, 1)])
		g_ = seq(t, [(0.4, 0), (0.85, 1)])
		pose = {"hips": {"loc": (0, 0, -0.8 * f), "rot": (0, 8 * f, 0)},
				"chest": {"rot": (reel - 22 * f, 6 * f, 10 * f), "loc": (0, 0.1 * f, -0.5 * f),
						  "scale": (1 + 0.1 * f, 1 + 0.1 * f, 1 - 0.28 * f)},
				"head": {"rot": (-60 * g_, 30 * g_, 40 * g_), "loc": (0.2 * g_, 0.5 * g_, -0.9 * g_)}}
		for s, side in ((1, "l"), (-1, "r")):
			pose[f"leg_{side}"] = {"rot": (-8 * f, 60 * s * f, 0), "scale": (1, 1, 1 - 0.3 * f)}
			pose[f"shoulder_{side}"] = {"rot": (25 * g_, -60 * s * g_, 10 * s * g_), "loc": (0.45 * s * g_, 0.1 * g_, -0.6 * g_)}
			pose[f"arm_{side}"] = {"rot": (10 * g_ + reel, -80 * s * g_, 0), "loc": (0, 0, -0.25 * g_)}
			pose[f"hand_{side}"] = {"rot": (0, -25 * s * g_, 0)}
		return merge_scaled(pose)

	clip_scaled(arm, "idle", 3.6 if colossus else 3.2, idle, True)
	clip_scaled(arm, "walk", 2.1 if colossus else 1.8, walk, True)
	clip_scaled(arm, "run", 1.3 if colossus else 1.1, run, True)
	clip_scaled(arm, "attack", 1.7 if colossus else 1.3, slam if colossus else attack, False)
	clip_scaled(arm, "hit", 0.55, hit, False)
	clip_scaled(arm, "death", 2.3, death, False)
	return arm


def build_glass_colossus():
	return build_glass_golem("glass_colossus", colossus=True)


# ---------------------------------------------------------------- obsidian drake and the obsidian wyrm
# A four-legged drake of black glass: glassy spines, a throat lit from within, smoked-glass wings
# it beats to hover a moment while it waits. The wyrm is the named one: much bigger, a long
# serpentine neck and tail, a crest of shards, and cracks glowing all along its body.

def build_obsidian_drake(name="obsidian_drake", wyrm=False):
	import random
	rng = random.Random(331 if wyrm else 329)
	m = blackglass_materials(name)
	g, gl, gd, sh, seam, hot = m["glass"], m["glass_l"], m["glass_d"], m["sheen"], m["seam"], m["hot"]
	membrane = glass_material(f"{name}_membrane", "3a2026", 0.82, rough=0.12, emit=0.15)
	tooth = material(f"{name}_tooth", "e8dccc", 0.4)
	b = Builder(name)
	b.bone("root", (0, 0, 0.6))
	b.bone("body", (0, 0.0, 0.66), "root")
	if wyrm:
		neck_pts = [(0, -0.46, 0.76), (0, -0.84, 1.0), (0, -1.1, 1.36), (0, -1.22, 1.74)]
		tail_pts = [(0, 0.56, 0.7), (0, 1.06, 0.56), (0, 1.54, 0.44), (0, 2.0, 0.34), (0, 2.44, 0.26), (0, 2.86, 0.2)]
		tail_r = [0.24, 0.19, 0.15, 0.11, 0.07, 0.02]
		neck_r = [0.25, 0.22, 0.19, 0.16]
	else:
		neck_pts = [(0, -0.46, 0.74), (0, -0.7, 0.9), (0, -0.84, 1.06)]
		tail_pts = [(0, 0.56, 0.7), (0, 1.08, 0.54), (0, 1.56, 0.4), (0, 1.96, 0.3)]
		tail_r = [0.2, 0.14, 0.08, 0.03]
		neck_r = [0.22, 0.19, 0.16]
	necks = [f"neck{k + 1}" for k in range(len(neck_pts) - 1)]
	tails = [f"tail{k + 1}" for k in range(len(tail_pts) - 1)]
	parent = "body"
	for k, bone in enumerate(necks):
		b.bone(bone, neck_pts[k], parent)
		parent = bone
	H = Vector(neck_pts[-1]) + Vector((0, -0.02, 0.04))
	b.bone("head", tuple(H), parent)
	b.bone("jaw", tuple(H + Vector((0, -0.14, -0.08))), "head")
	parent = "body"
	for k, bone in enumerate(tails):
		b.bone(bone, tail_pts[k], parent)
		parent = bone
	b.bone("wing_l", (0.24, -0.3, 0.9), "body")
	b.bone("wing_r", (-0.24, -0.3, 0.9), "body")

	def P(x, y, z):
		return tuple(H + Vector((x, y, z)))

	# the body: black glass, the belly plated over a glow that shows between the plates
	b.blob((0.68, 1.36, 0.56), (0, 0.02, 0.68), g, "body", segs=(14, 9))
	b.blob((0.5, 1.08, 0.24), (0, 0.0, 0.47), seam, "body", segs=(12, 6))
	for k in range(6):
		_glass_plate(b, (0.42 - 0.04 * abs(k - 2.5), 0.13, 0.08), (0, -0.4 + k * 0.16, 0.39), gd, "body", rng, jitter=0.04)
	b.blob((0.72, 0.62, 0.62), (0, -0.4, 0.74), g, "body", segs=(10, 8))                      # shoulders
	b.blob((0.64, 0.58, 0.58), (0, 0.42, 0.7), g, "body", segs=(10, 8))                       # haunches
	for k in range(7):   # glass spines down the back
		y = -0.5 + k * 0.17
		ln = (0.3 if not wyrm else 0.42) - 0.03 * abs(k - 3)
		_shard(b, (0, y, 0.9 - 0.02 * abs(k - 3)), (0, 0.45, 1), ln, 0.14, sh if k % 2 else gl, "body", twist=90, flat=0.35)
	for s in (1, -1):   # flank scutes of polished glass
		for k in range(4):
			_glass_plate(b, (0.06, 0.2, 0.14), (0.31 * s, -0.3 + k * 0.22, 0.72 + 0.02 * (k % 2)), gl, "body", rng,
						 rot=(0, 26 * s, 0), jitter=0.05)
		if wyrm:   # cracks glowing along its flanks
			_zigzag(b, [(0.33 * s, -0.5, 0.62), (0.35 * s, -0.3, 0.7), (0.34 * s, -0.1, 0.6), (0.35 * s, 0.12, 0.68),
						(0.33 * s, 0.34, 0.58), (0.32 * s, 0.5, 0.64)], 0.026, hot, "body")
	# the neck: a glowing throat under the glass
	for k, bone in enumerate(necks):
		p, q = neck_pts[k], neck_pts[k + 1]
		b.seg(p, q, neck_r[k], neck_r[k + 1], g, bone, sides=9)
		down = lambda v, r: (v[0], v[1] - r * 0.3, v[2] - r * 0.55)
		b.seg(down(p, neck_r[k]), down(q, neck_r[k + 1]), neck_r[k] * 0.55, neck_r[k + 1] * 0.55, hot, bone, sides=7)
		mid = ((p[1] + q[1]) / 2, (p[2] + q[2]) / 2)
		r = (neck_r[k] + neck_r[k + 1]) / 2
		_shard(b, (0, mid[0] + 0.06, mid[1] + r * 0.7), (0, 0.6, 1), (0.22 if not wyrm else 0.34), 0.12, sh if k % 2 else gl,
			   bone, twist=90, flat=0.35)
		if wyrm:
			for s in (1, -1):
				_zigzag(b, [(r * 0.9 * s, p[1] + 0.02, p[2] + 0.02), (r * 0.95 * s, mid[0], mid[1] + 0.05),
							(r * 0.9 * s, q[1] - 0.02, q[2])], 0.02, hot, bone)
	# the head: a long wedge of glass, a heavy brow, shard horns swept back, a jaw of teeth
	b.blob((0.36, 0.46, 0.3), P(0, -0.1, 0.02), g, "head", segs=(10, 7))
	b.seg(P(0, -0.2, 0.02), P(0, -0.5, -0.04), 0.14, 0.085, g, "head", sides=8)
	_glass_plate(b, (0.4, 0.2, 0.1), P(0, -0.2, 0.14), gl, "head", rng, rot=(-8, 0, 0), jitter=0.04)   # brow
	b.seg(P(0, -0.14, -0.1), P(0, -0.46, -0.12), 0.1, 0.06, gd, "jaw", sides=7)                      # lower jaw
	b.seg(P(0, -0.16, -0.07), P(0, -0.44, -0.08), 0.08, 0.05, hot, "jaw", sides=6)                   # the fire in its mouth
	for s in (1, -1):
		b.blob((0.09, 0.07, 0.06), P(0.13 * s, -0.24, 0.09), m["eye"], "head", rot=(0, 0, 12 * s), segs=(6, 4))
		b.blob((0.04, 0.03, 0.03), P(0.05 * s, -0.51, -0.01), hot, "head", segs=(4, 3))
		for k in range(4):
			y = -0.28 - k * 0.06
			b.seg(P(0.08 * s, y, -0.07), P(0.085 * s, y, -0.12), 0.018, 0.0, tooth, "head", sides=4)
		_shard(b, P(0.1 * s, -0.1, 0.16), (0.35 * s, 1, 0.45), 0.5 if not wyrm else 0.62, 0.11, sh, "head", twist=30 * s)
		_shard(b, P(0.16 * s, -0.08, 0.0), (0.8 * s, 0.8, 0.1), 0.24, 0.07, gl, "head", twist=90)          # cheek blades
	if wyrm:   # a crest of shards down the middle of its skull
		for k in range(5):
			_shard(b, P(0, -0.3 + 0.1 * k, 0.16 - 0.01 * k), (0, 0.8, 1), 0.18 + 0.07 * k, 0.12, sh if k % 2 else gl,
				   "head", twist=90, flat=0.3)
		_shard(b, P(0, -0.44, 0.02), (0, -0.3, 1), 0.16, 0.07, gl, "head")                               # a snout horn
	for s in (1, -1):
		_bat_wing(b, s, (0.24 * s, -0.3, 0.9), (gl, membrane, sh), f"wing_{'l' if s > 0 else 'r'}",
				  scale=1.05 if wyrm else 0.78)
	# the tail: tapering, spined, a glass blade at the end
	for k, bone in enumerate(tails):
		p, q = tail_pts[k], tail_pts[k + 1]
		b.seg(p, q, tail_r[k], tail_r[k + 1], g, bone, sides=8)
		b.seg((0, p[1], p[2] - tail_r[k] * 0.5), (0, q[1], q[2] - tail_r[k + 1] * 0.5), tail_r[k] * 0.6, tail_r[k + 1] * 0.6,
			  seam, bone, sides=6)
		mid = ((p[1] + q[1]) / 2, (p[2] + q[2]) / 2)
		r = (tail_r[k] + tail_r[k + 1]) / 2
		_shard(b, (0, mid[0], mid[1] + r * 0.7), (0, 0.6, 1), 0.08 + r * 1.2, 0.1, sh if k % 2 else gl, bone, twist=90, flat=0.35)
		if wyrm and k < len(tails) - 1:
			_zigzag(b, [(r * 0.85, p[1] + 0.04, p[2]), (r * 0.95, mid[0], mid[1] + 0.03), (r * 0.8, q[1] - 0.04, q[2])], 0.02, hot, bone)
	tip = Vector(tail_pts[-1])
	_shard(b, tuple(tip - Vector((0, 0.06, 0))), (0, 1, 0.1), 0.5 if wyrm else 0.36, 0.2, sh, tails[-1], twist=90, flat=0.25)
	_shard(b, tuple(tip - Vector((0, 0.1, 0))), (0.5, 1, 0.3), 0.24, 0.1, gl, tails[-1], twist=60)
	_shard(b, tuple(tip - Vector((0, 0.1, 0))), (-0.5, 1, 0.3), 0.24, 0.1, gl, tails[-1], twist=-60)
	# four legs, glass claws
	legs = {"leg_fl": (0.26, -0.42), "leg_fr": (-0.26, -0.42), "leg_bl": (0.27, 0.44), "leg_br": (-0.27, 0.44)}
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.62), "root")
		back = y > 0
		b.blob((0.26, 0.38 if back else 0.3, 0.44), (x * 1.08, y + (0.04 if back else 0.0), 0.6), g, name_, segs=(8, 6))
		b.seg((x, y + (0.08 if back else 0.02), 0.44), (x, y + (0.1 if back else 0.04), 0.2), 0.085, 0.07, g, name_, sides=7)
		b.seg((x, y + (0.1 if back else 0.04), 0.2), (x, y - 0.02, 0.06), 0.07, 0.065, gd, name_, sides=7)
		b.blob((0.18, 0.22, 0.1), (x, y - 0.04, 0.05), gd, name_, segs=(8, 5))
		_shard(b, (x * 1.2, y + 0.06, 0.62), (x, 0.6, 0.6), 0.2, 0.08, sh, name_, twist=90)   # a spur at the elbow
		for k in (-1, 0, 1):
			root = Vector((x + 0.06 * k, y - 0.12, 0.05))
			_shard(b, tuple(root), (0.1 * k, -1, -0.4), 0.11, 0.05, sh, name_)
	_scaled(b, 1.6 if wyrm else 1.2)
	arm = b.build()
	n_neck, n_tail = len(necks), len(tails)

	def wings(k=0.0, beat=0.0):
		# k spreads them out to the side; beat swings the spread wings down (+) and up (-)
		return {"wing_l": {"rot": (-10 * k, -70 * k + beat * k, -40 * k)}, "wing_r": {"rot": (-10 * k, 70 * k - beat * k, 40 * k)}}

	def tail(t, amp, cycles=1.0, pitch=0.0):
		return {bone: {"rot": (pitch / n_tail + (3 * wave(t, cycles, 0.2) if k == 0 else 0), 0,
							   amp * (1 + 0.15 * k) * wave(t, cycles, -0.15 * k) * (3.0 / n_tail))}
				for k, bone in enumerate(tails)}

	def neck(pitch=0.0, yaw=0.0, snake=0.0, t=0.0):
		# pitch and yaw shared along the neck; snake winds it side to side (the wyrm's weave)
		return {bone: {"rot": (pitch / n_neck, 0, yaw / n_neck + snake * wave(t, 1, -0.2 * k) * (1 if k % 2 == 0 else -0.6))}
				for k, bone in enumerate(necks)}

	lift_h = 0.34 if wyrm else 0.28

	def idle(t):   # sways its neck; now and then beats its wings and hovers a moment
		f = seq(t, [(0, 0), (0.42, 0), (0.52, 1), (0.84, 1), (0.94, 0), (1, 0)])
		beat = 34 * wave(t, 10 if not wyrm else 7)
		lift = lift_h * seq(t, [(0, 0), (0.46, 0), (0.56, 1), (0.84, 1), (0.95, 0), (1, 0)])
		lift += 0.05 * f * wave(t, 10 if not wyrm else 7, 0.25)
		dangle = 22 * seq(t, [(0.46, 0), (0.56, 1), (0.84, 1), (0.95, 0)])
		return merge({"root": {"loc": (0, 0, lift + 0.012 * wave(t, 2)), "rot": (-4 * f, 0, 0)},
					  "head": {"rot": (-3 * wave(t, 1, 0.2) + 4 * f, 0, -6 * wave(t))},
					  "jaw": {"rot": (-8 * max(0.0, wave(t, 2, 0.1)), 0, 0)},
					  "leg_fl": {"rot": (-dangle, 0, 0)}, "leg_fr": {"rot": (-dangle, 0, 0)},
					  "leg_bl": {"rot": (dangle, 0, 0)}, "leg_br": {"rot": (dangle, 0, 0)}},
					 neck(4 * wave(t, 1, 0.2) - 6 * f, 8 * wave(t), 5 if wyrm else 0, t),
					 wings(0.06 + 0.94 * f, beat), tail(t, 10, 1, -8 * f))

	def walk(t):
		return merge(_quad_legs(wave(t), 24), tail(t, 14), wings(0.04),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 5 * wave(t, 1, 0.25))}},
					 neck(0, -6 * wave(t, 1, 0.25), 6 if wyrm else 0, t))

	def run(t):
		f, k = 40 * wave(t), 40 * wave(t, 1, 0.5)
		flap = 0.5 + 0.5 * wave(t, 1, 0.1)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.08 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)}},
					 neck(-12, 0, 4 if wyrm else 0, t), wings(0.3 + 0.2 * flap, 20 * wave(t, 1, 0.1)), tail(t, 8))

	def attack(t):   # rears its neck back, wings up, then lunges to bite
		rear = seq(t, [(0, 0), (0.3, 1), (0.46, -0.6), (0.62, -0.4), (1, 0)])
		jaw = seq(t, [(0, 0), (0.3, -36), (0.44, -40), (0.52, 2), (0.7, 0)])
		lunge = seq(t, [(0, 0), (0.3, -0.1), (0.46, 0.36), (0.62, 0.3), (1, 0)])
		spread = seq(t, [(0, 0), (0.25, 1), (0.6, 0.8), (1, 0)]) * (1.0 if wyrm else 0.6)
		return merge({"root": {"loc": (0, lunge, 0.04 * max(0.0, rear)), "rot": (6 * rear, 0, 0)},
					  "head": {"rot": (-12 * rear, 0, 0)}, "jaw": {"rot": (jaw, 0, 0)},
					  "leg_fl": {"rot": (20 * max(0.0, rear), 0, 0)}},
					 neck(30 * rear + (10 * rear if wyrm else 0)), wings(spread, -10 * spread), tail(t, 16, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.03 * k), "rot": (6 * k, 5 * k, 0)},
					  "head": {"rot": (8 * k, 0, 10 * k)}, "jaw": {"rot": (-24 * k, 0, 0)}},
					 neck(16 * k, 12 * k), wings(0.3 * k), tail(t, 20 * k, 2))

	def death(t):   # the neck whips back, it rolls onto its side, the glow in it dying
		roll = seq(t, [(0.2, 0), (0.62, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.2, 0), (0.62, -0.34)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		out = merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
					 "head": {"rot": (-10 * curl, 0, 12 * curl)}, "jaw": {"rot": (-24 * curl, 0, 0)},
					 "leg_fl": {"rot": (30 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
					 "leg_bl": {"rot": (-24 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					neck(seq(t, [(0, 0), (0.2, 30), (0.7, -16)]), 20 * curl), wings(0.4 * curl))
		for k, bone in enumerate(tails):
			out = merge(out, {bone: {"rot": (-6 * curl if k == 0 else 0, 0, 60 * curl / n_tail)}})
		return out

	clip(arm, "idle", 5.0 if wyrm else 4.0, idle, True)
	clip(arm, "walk", 1.15 if wyrm else 1.0, walk, True)
	clip(arm, "run", 0.62 if wyrm else 0.52, run, True)
	clip(arm, "attack", 1.0 if wyrm else 0.8, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.6 if wyrm else 1.3, death, False)
	return arm


def build_obsidian_wyrm():
	return build_obsidian_drake("obsidian_wyrm", wyrm=True)


# ---------------------------------------------------------------- glass spider and the glass brood queen
# The spider's shape (SPIDER_LEGS) in black glass: a smoky crystal abdomen with fire glowing
# inside it and shards growing from it, legs like splinters. The brood queen is huge, crowned
# with shards, her abdomen swollen with glowing eggs that pulse.

def build_glass_spider(name="glass_spider", queen=False):
	import random
	rng = random.Random(353 if queen else 349)
	m = blackglass_materials(name)
	g, gl, gd, sh, hot = m["glass"], m["glass_l"], m["glass_d"], m["sheen"], m["hot"]
	egg = material(f"{name}_egg", "f08a3a", 0.3, emit=1.3)
	egg_b = material(f"{name}_egg_bright", "ffb050", 0.3, emit=1.8)
	ember = material(f"{name}_ember", "b8300a", 0.5, emit=1.2)   # the faint fire inside
	b = Builder(name)
	b.bone("root", (0, 0, 0.55))
	b.bone("body", (0, -0.15, 0.55), "root")
	b.bone("abdomen", (0, 0.25, 0.62), "body")
	b.bone("fang_l", (0.08, -0.62, 0.48), "body")
	b.bone("fang_r", (-0.08, -0.62, 0.48), "body")
	b.blob((0.7, 0.78, 0.46), (0, -0.2, 0.55), g, "body", segs=(12, 8))                       # cephalothorax
	for k, (x, y) in enumerate(((0.16, -0.1), (-0.16, -0.12), (0.0, 0.08), (0.12, -0.34), (-0.12, -0.32))):
		_glass_plate(b, (0.2, 0.22, 0.1), (x, y - 0.1, 0.77), sh if k % 2 else gl, "body", rng, rot=(0, 20 * x / 0.16, 0), jitter=0.05)
	ab_c, ab_s = ((0, 0.9, 0.9), (1.5, 1.7, 1.28)) if queen else ((0, 0.72, 0.78), (1.1, 1.25, 0.95))
	# the abdomen: a geode of black glass facets, fire (or her eggs) glowing through the gaps
	b.blob(tuple(v * 0.94 for v in ab_s), ab_c, ember, "abdomen", segs=(14, 10))
	n = 26 if queen else 22
	for k in range(n):   # facets spread evenly over the shell (a Fibonacci sphere)
		zf = 1 - 2 * (k + 0.5) / n
		a = k * 2.39996
		nrm = Vector((math.sqrt(1 - zf * zf) * math.cos(a), math.sqrt(1 - zf * zf) * math.sin(a), zf))
		if queen and nrm.z < -0.15 and nrm.y > 0.05:
			continue   # leave room underneath and behind where the egg sacs bulge out
		surf = Vector((nrm.x * ab_s[0] / 2, nrm.y * ab_s[1] / 2, nrm.z * ab_s[2] / 2))
		w = 0.5 * (ab_s[0] + ab_s[1]) / 2
		_glass_scale(b, tuple(Vector(ab_c) + surf * 0.97), tuple(nrm), w * rng.uniform(0.9, 1.05), w * rng.uniform(0.8, 0.95),
					 0.2 * w, (g, gl, gd, sh)[k % 4] if k % 4 != 3 else g, "abdomen", rng)
	if queen:   # a clutch of glowing eggs bursting out of the shell underneath and behind
		n_egg = 70
		for k in range(n_egg):
			zf = 1 - 2 * (k + 0.5) / n_egg
			a = k * 2.39996
			nrm = Vector((math.sqrt(1 - zf * zf) * math.cos(a), math.sqrt(1 - zf * zf) * math.sin(a), zf))
			if not (nrm.z < -0.15 and nrm.y > 0.05) and not (k % 5 == 0 and nrm.z < 0.3):
				continue
			surf = Vector((nrm.x * ab_s[0] / 2, nrm.y * ab_s[1] / 2, nrm.z * ab_s[2] / 2))
			r = rng.uniform(0.24, 0.38)
			b.blob((r, r, r * 0.9), tuple(Vector(ab_c) + surf * 0.93), egg if k % 3 else egg_b, "abdomen", segs=(10, 7))
	for k in range(9 if queen else 7):   # shards growing out of the crystal
		a = 2 * math.pi * k / (9 if queen else 7) + 0.3
		up = 0.6 + 0.4 * (k % 2)
		d = Vector((math.cos(a) * 0.7, math.sin(a) * 0.7, up))
		base = Vector(ab_c) + Vector((d.x * ab_s[0] * 0.35, d.y * ab_s[1] * 0.35, ab_s[2] * 0.36))
		_shard(b, tuple(base), tuple(d), (0.36 if queen else 0.26) * (1.3 if k % 3 == 0 else 1.0), 0.12 if queen else 0.09,
			   (sh, g, gl)[k % 3], "abdomen", twist=math.degrees(a))
	_shard(b, (0, ab_c[1] + ab_s[1] * 0.46, ab_c[2] + 0.1), (0, 1, 0.3), 0.3 if queen else 0.2, 0.12, g, "abdomen")  # spinneret blade
	# eyes and fangs
	for s in (1, -1):
		for ex, ez in ((0.1, 0.72), (0.2, 0.68), (0.06, 0.64)):
			b.blob((0.07, 0.06, 0.07), (ex * s, -0.55, ez), m["eye"], "body", segs=(6, 4))
		side = "fang_l" if s > 0 else "fang_r"
		_shard(b, (0.08 * s, -0.58, 0.5), (-0.1 * s, -0.4, -1), 0.26, 0.09, gd, side, twist=90 * s)
	if queen:   # a crown of shards on her brow
		for k in range(7):
			a = math.pi * (k + 0.5) / 7
			base = (0.28 * math.cos(a), -0.28 - 0.18 * math.sin(a) + 0.1, 0.72)
			_shard(b, base, (0.45 * math.cos(a), -0.2 * math.sin(a) + 0.2, 1), 0.42 + 0.24 * (1 - abs(k - 3) / 3), 0.12,
				   sh if k % 2 else gl, "body", twist=math.degrees(a))
	# legs like splinters of glass
	for name_, (x, y) in SPIDER_LEGS.items():
		s = 1 if x > 0 else -1
		b.bone(name_, (x, y, 0.55), "body")
		spread = (y + 0.15) * 1.6
		knee = Vector((x + 0.55 * s, y + spread * 0.5, 0.95))
		foot = Vector((x + 1.05 * s, y + spread, 0.0))
		hip = Vector((x, y, 0.55))
		b.seg(tuple(hip), tuple(knee), 0.07, 0.05, g, name_, sides=4)
		b.blob((0.09, 0.09, 0.09), tuple(knee), m["seam"], name_, segs=(6, 4))   # a faint glow at each joint
		_shard(b, tuple(knee - (knee - hip).normalized() * 0.04), tuple(foot - knee), (foot - knee).length * 1.02, 0.11, gl, name_,
			   twist=90, flat=0.55, sides=3, collar=0.12)
		_shard(b, tuple(knee), (0.3 * s, 0, 1), 0.16, 0.06, sh, name_)   # a spur at the knee
	_scaled(b, 1.9 if queen else 1.15)
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

	def pulse(t, amt):
		k = 1 + amt * max(0.0, wave(t, 2 if queen else 1))
		return {"abdomen": {"scale": (k, k, k)}}

	def idle(t):
		return merge_scaled({"body": {"loc": (0, 0, 0.012 * wave(t))}, "abdomen": {"rot": (3 * wave(t, 1, 0.2), 0, 0)}},
							fangs(6 * max(0.0, wave(t, 2))), gait(t, 2, 0), pulse(t, 0.06 if queen else 0.025))

	def walk(t):
		return merge_scaled(gait(t, 18, 14), {"root": {"loc": (0, 0, 0.015 * abs(wave(t, 2)))}, "abdomen": {"rot": (0, 0, 3 * wave(t))}})

	def run(t):
		return merge_scaled(gait(t, 26, 20), {"root": {"loc": (0, 0, 0.03 * abs(wave(t, 2)))}, "abdomen": {"rot": (0, 0, 4 * wave(t))}})

	def attack(t):  # rear the front legs, then strike down with the glass fangs
		rear = seq(t, [(0, 0), (0.35, 1), (0.55, -0.4), (1, 0)])
		out = merge({"root": {"rot": (14 * rear, 0, 0), "loc": (0, seq(t, [(0, 0), (0.35, -0.1), (0.55, 0.25), (1, 0)]), 0)}},
					fangs(seq(t, [(0, 0), (0.35, 28), (0.55, -10), (1, 0)])))
		for name_ in ("leg_l1", "leg_r1"):
			out = merge(out, leg(name_, 0, 45 * rear))
		return merge_scaled(out)

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"root": {"loc": (0, -0.12 * k, 0.04 * k), "rot": (8 * k, 5 * k, 0)}}, fangs(18 * k), gait(t, 8 * k, 12 * k))

	def death(t):  # legs curl up underneath; the glow inside fades as the abdomen sags
		drop = seq(t, [(0.1, 0), (0.6, -0.3)])
		curl = seq(t, [(0.2, 0), (0.8, 1)])
		out = merge({"root": {"loc": (0, 0, drop), "rot": (0, seq(t, [(0.3, 0), (0.7, 18)]), 0)}}, fangs(20 * curl))
		for i, name_ in enumerate(SPIDER_LEGS):
			out = merge(out, leg(name_, 4 * wave(t, 5, i * 0.13) * (1 - curl), -65 * curl))
		out["abdomen"] = dict(out.get("abdomen", {}), scale=(1 + 0.05 * curl, 1, 1 - 0.12 * curl))
		return merge_scaled(out)

	clip_scaled(arm, "idle", 2.4 if queen else 2.0, idle, True)
	clip_scaled(arm, "walk", 0.8 if queen else 0.7, walk, True)
	clip_scaled(arm, "run", 0.5 if queen else 0.42, run, True)
	clip_scaled(arm, "attack", 0.8 if queen else 0.65, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.4 if queen else 1.2, death, False)
	return arm


def build_glass_brood_queen():
	return build_glass_spider("glass_brood_queen", queen=True)


# ---------------------------------------------------------------- the glassbound dead and their captain
# Skeleton_Warrior repainted ash-pale with black-glass iron and blue ghost-light in the eyes;
# shards of black glass grow over one shoulder, half the skull and one shin, pale blue light
# in their cracks. The captain wears glass-encrusted pauldrons, a crown of glass and a broken
# banner on his back.

GLASSBOUND_CELLS = {(1, 1): ("d4d8e0", "5a606c"), (3, 0): ("7a7e8a", "262830"), (4, 0): ("7a7e8a", "262830"),
					(6, 0): ("5a4e46", "1e1814"), (7, 0): ("5a4e46", "1e1814"), (2, 2): ("3a3e50", "10121a"),
					(1, 2): ("5a6a7a", "1e2630"), (5, 2): ("5a6a7a", "1e2630"), (2, 0): ("5a4e46", "1e1814"),
					(7, 3): ("f0ffff", "7ae0ff")}
GLASSBOUND_CAPTAIN_CELLS = {(1, 1): ("b8c0cc", "444a56"), (3, 0): ("6a6680", "1e1c2a"), (4, 0): ("6a6680", "1e1c2a"),
							(6, 0): ("3e3840", "121014"), (7, 0): ("3e3840", "121014"), (2, 2): ("3a3068", "0e0a20"),
							(1, 2): ("a88a50", "3a2c14"), (5, 2): ("a88a50", "3a2c14"), (2, 0): ("3e3840", "121014"),
							(7, 3): ("f0ffff", "7ae0ff")}


def _glass_lump(b, m, size, loc, rng, rot=(0, 0, 0), light=None):
	"""A lump of smoky, see-through glass with pale blue ghost-light caught inside it."""
	_rock(b, size, loc, m["glass"], "x", rng, rot=rot, jitter=0.12)
	for k in range(3):   # thin slivers of light where it's cracked
		a = rng.uniform(0, 2 * math.pi)
		nrm = Vector((math.cos(a), math.sin(a), rng.uniform(-0.3, 0.5))).normalized()
		if k == 0 and light:
			nrm = (Vector(light) - Vector(loc)).normalized()
		surf = Vector(loc) + Vector((nrm.x * size[0], nrm.y * size[1], nrm.z * size[2])) * 0.46
		along = nrm.cross(Vector((0, 0, 1))).normalized() if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
		along = (along + Vector((0, 0, rng.uniform(-0.8, 0.8)))).normalized()
		_oblob(b, (0.035, 0.34 * max(size), 0.14), tuple(surf), tuple(along), tuple(nrm), m["ghost"] if k == 0 else m["ghost_b"], "x", segs=(6, 4))


def glassbound_materials(p):
	m = blackglass_materials(p)
	return m


def _ghost_eyes(b, m):
	"""Pale blue lights in the sockets (the KayKit eyes are hidden: their glow is a fixed yellow)."""
	for s in (1, -1):
		b.blob((0.13, 0.06, 0.1), (0.155 * s, -0.27, 1.645), m["ghost"], "x", segs=(8, 5))


def build_glassbound_crust():
	"""Black glass grown over the right shoulder and down the ribs, blue light caught in it."""
	import random
	rng = random.Random(367)
	m = glassbound_materials("glassbound")
	b = Builder("glassbound_crust")
	_glass_lump(b, m, (0.46, 0.5, 0.4), (-0.34, 0.0, 1.22), rng, light=(-0.36, -0.1, 1.24))
	_glass_lump(b, m, (0.34, 0.3, 0.36), (-0.24, -0.2, 1.0), rng)
	_rock(b, (0.3, 0.3, 0.26), (-0.34, 0.16, 1.06), m["glass"], "x", rng)
	_shard_cluster(b, (-0.4, 0.02, 1.36), (-0.35, 0.1, 1), 5, 0.5, 0.13, (m["glass"], m["sheen"], m["glass_l"]), "x", rng)
	_shard_cluster(b, (-0.24, 0.24, 1.2), (-0.2, 0.8, 0.6), 3, 0.36, 0.11, (m["glass_l"], m["glass"]), "x", rng)
	_shard_cluster(b, (-0.3, -0.28, 0.98), (-0.5, -0.8, 0.1), 3, 0.28, 0.09, (m["sheen"], m["glass"]), "x", rng)
	_shard(b, (0.26, 0.14, 1.0), (0.6, 0.6, 0.6), 0.26, 0.09, m["glass"], "x", twist=40)      # a splinter in the left side
	_shard(b, (0.18, -0.3, 0.84), (0.5, -0.7, -0.2), 0.2, 0.08, m["glass_l"], "x", twist=20)
	return b.build_static()


def build_glassbound_skull():
	"""Glass grown over the left half of the skull, shards jutting up out of it; ghost-light in the eyes."""
	import random
	rng = random.Random(373)
	m = glassbound_materials("glassbound")
	b = Builder("glassbound_skull")
	_glass_lump(b, m, (0.36, 0.7, 0.56), (0.36, 0.04, 1.86), rng, rot=(0, -20, 0), light=(0.36, -0.12, 1.8))
	_shard_cluster(b, (0.38, 0.0, 2.06), (0.45, 0.1, 1), 5, 0.46, 0.12, (m["glass"], m["sheen"], m["glass_l"]), "x", rng)
	_shard(b, (0.22, 0.26, 2.0), (0.2, 0.8, 0.8), 0.3, 0.1, m["glass_l"], "x", twist=60)
	_ghost_eyes(b, m)
	return b.build_static()


def build_glassbound_shin():
	"""A lump of glass encasing the left shin, as if it had waded out of the flow as it cooled."""
	import random
	rng = random.Random(379)
	m = glassbound_materials("glassbound")
	b = Builder("glassbound_shin")
	_glass_lump(b, m, (0.44, 0.5, 0.4), (0.15, -0.06, 0.24), rng, light=(0.2, -0.2, 0.26))
	_shard(b, (0.3, -0.06, 0.34), (0.8, -0.3, 0.6), 0.28, 0.09, m["sheen"], "x", twist=30)
	_shard(b, (0.12, 0.12, 0.36), (-0.2, 0.7, 0.8), 0.22, 0.08, m["glass_l"], "x", twist=80)
	_shard(b, (0.1, -0.3, 0.3), (-0.1, -1, 0.5), 0.2, 0.08, m["glass"], "x", twist=10)
	return b.build_static()


def build_glassbound_crown():
	"""The captain's crown: a band of black glass with shards rising from it, a blue light set in front,
	and the ghost-light in his eyes."""
	m = glassbound_materials("glassbound_captain")
	b = Builder("glassbound_crown")
	_ring(b, (0, 0.0, 2.0), (0.42, 0.42), (0, -4), 0.045, m["glass_l"], sides=18)
	for k in range(11):
		a = -math.pi / 2 + (k - 5) * 0.56
		p = Vector((0.42 * math.cos(a), 0.42 * math.sin(a), 2.0))
		h = 0.5 if k == 5 else (0.36 if k % 2 == 0 else 0.24)
		_shard(b, tuple(p), (0.25 * math.cos(a), 0.25 * math.sin(a), 1), h, 0.12, m["sheen"] if k % 2 else m["glass_l"], "x",
			   twist=math.degrees(a) + 90, flat=0.5)
	b.blob((0.12, 0.07, 0.14), (0, -0.44, 2.04), m["ghost"], "x", segs=(8, 5))
	_ghost_eyes(b, m)
	return b.build_static()


def build_glassbound_mantle():
	"""Pauldrons of raw glass on both shoulders, a breastplate of shards, and a broken banner on his back."""
	import random
	rng = random.Random(383)
	m = glassbound_materials("glassbound_captain")
	cloth = material("glassbound_banner", "3a3068", 0.95)
	cloth_d = material("glassbound_banner_dark", "221c40", 0.95)
	trim = material("glassbound_banner_trim", "a88a50", 0.7)
	pole = material("glassbound_pole", "4a3a2e", 0.9)
	b = Builder("glassbound_mantle")
	for s in (1, -1):
		_glass_lump(b, m, (0.46, 0.5, 0.34), (0.38 * s, 0.0, 1.26), rng, rot=(0, 24 * s, 0), light=(0.42 * s, -0.12, 1.28))
		_glass_plate(b, (0.36, 0.44, 0.1), (0.42 * s, 0.0, 1.4), m["glass_l"], "x", rng, rot=(0, 26 * s, 0), jitter=0.04)
		_shard_cluster(b, (0.46 * s, 0.0, 1.42), (0.6 * s, 0.1, 1), 5, 0.46, 0.12, (m["sheen"], m["glass"], m["glass_l"]), "x", rng)
	for k, (x, z) in enumerate(((0.12, 1.12), (-0.1, 1.04), (0.0, 0.94), (0.2, 0.96))):   # glass grown over the breastplate
		_shard(b, (x, -0.3, z), (x * 2, -1, 0.5), 0.2, 0.09, m["glass"] if k % 2 else m["sheen"], "x", twist=30 * k)
	# the broken banner: a snapped pole across the back, a torn standard hanging off it
	top = Vector((-0.28, 0.42, 2.3))
	b.seg((0.22, 0.34, 0.5), tuple(top), 0.035, 0.03, pole, "x", sides=6)
	b.seg(tuple(top), tuple(top + Vector((0.02, 0.0, 0.1))), 0.03, 0.0, pole, "x", sides=4)            # the splintered end
	b.seg(tuple(top + Vector((0.02, 0, -0.14))), tuple(top + Vector((0.46, 0.02, -0.08))), 0.02, 0.02, pole, "x", sides=5)   # the crossbar
	a = top + Vector((0.0, 0.03, -0.16))
	c = top + Vector((0.46, 0.05, -0.1))
	_slab(b, [tuple(a), tuple(c), tuple(c + Vector((0.08, 0.03, -0.46))), tuple(a + Vector((0.2, 0.03, -0.72))),
			  tuple(a + Vector((0.02, 0.03, -0.62)))], 0.02, cloth)
	_slab(b, [tuple(c + Vector((0.08, 0.03, -0.46))), tuple(c + Vector((-0.02, 0.03, -0.52))),
			  tuple(a + Vector((0.2, 0.03, -0.72)))], 0.02, cloth_d)
	_slab(b, [tuple(a + Vector((0.02, 0.0, -0.02))), tuple(c + Vector((0, 0.0, -0.02))), tuple(c + Vector((0, 0.0, -0.08))),
			  tuple(a + Vector((0.02, 0.0, -0.08)))], 0.03, trim)
	_shard_cluster(b, (0.0, 0.3, 1.1), (0.1, 1, 0.5), 3, 0.3, 0.1, (m["glass"], m["glass_l"]), "x", rng)
	return b.build_static()


CREATURES.update({"glass_golem": build_glass_golem, "glass_colossus": build_glass_colossus,
				  "obsidian_drake": build_obsidian_drake, "obsidian_wyrm": build_obsidian_wyrm,
				  "glass_spider": build_glass_spider, "glass_brood_queen": build_glass_brood_queen})
ATTACHMENTS.update({"glassbound_crust": build_glassbound_crust, "glassbound_skull": build_glassbound_skull,
					"glassbound_shin": build_glassbound_shin, "glassbound_crown": build_glassbound_crown,
					"glassbound_mantle": build_glassbound_mantle})
BODIES.update({"glassbound_dead_body": (SKELETONS + "Skeleton_Warrior.glb", "glassbound_dead_texture", GLASSBOUND_CELLS, None),
			   "glassbound_captain_body": (SKELETONS + "Skeleton_Warrior.glb", "glassbound_captain_texture",
										   GLASSBOUND_CAPTAIN_CELLS, None)})
# ================================================================ end of Blackglass


# ================================================================ The Burn (the Ashfall, 29-33)
# A great forest burned to black trunks under Agnavar the Ember-Tusked. Ember giants are a repainted
# KayKit barbarian (head hidden) with bolt-ons in its mesh space and a hammer of their own in
# models.json "weapons"; the rest are own-rig creatures: firehounds and the ash wolf on one hound frame,
# fire imps, the smoke spirit (the air elemental's frame in smoke) and the firebird / phoenix.

# the barbarian as an ember giant: skin (0,0) (1,3) (3,1) charcoal with a red undertone, trousers (7,1)
# scorched leather, boots (3,2) blackened iron, vest (7,0) and fur trim (2,1) soot, leather (6,0) (6,1) (5,1),
# hand wraps (7,2) sooty leather
EMBER_GIANT_CELLS = {(0, 0): ("6a4038", "241412"), (1, 3): ("6a4038", "241412"), (3, 1): ("5e3a32", "20120e"),
					 (7, 1): ("5a3e2a", "1e140c"), (3, 2): ("3e3836", "121010"), (7, 0): ("4a3a30", "18100c"),
					 (2, 1): ("3a302a", "120e0c"), (6, 0): ("6a4a30", "26180e"), (6, 1): ("6a4a30", "26180e"),
					 (3, 0): ("5a5652", "1e1c1a"), (5, 1): ("6a4a30", "26180e"), (7, 2): ("5a4636", "1e140e")}
EMBER_THANE_CELLS = {(0, 0): ("5a302a", "1a0c0a"), (1, 3): ("5a302a", "1a0c0a"), (3, 1): ("4e2c26", "180a08"),
					 (7, 1): ("3a2a22", "120a08"), (3, 2): ("2e2a2a", "0c0a0a"), (7, 0): ("7a2418", "2a0a06"),
					 (2, 1): ("2a2220", "0a0808"), (6, 0): ("5a3a24", "1e1008"), (6, 1): ("5a3a24", "1e1008"),
					 (3, 0): ("c8943a", "6a4410"), (5, 1): ("7a2418", "2a0a06"), (7, 2): ("4a3026", "180c08")}


def burn_materials(p="burn", bright=1.0):
	return {
		"skin": material(f"{p}_skin", "4a2e28", 0.9),
		"skin_d": material(f"{p}_skin_dark", "261614", 0.9),
		"skin_l": material(f"{p}_skin_light", "6a4038", 0.85),
		"crack": material(f"{p}_crack", "ff6a1a", 0.3, emit=2.6 * bright),
		"crack_b": material(f"{p}_crack_b", "ffb040", 0.3, emit=3.2 * bright),
		"eye": material(f"{p}_eye", "fff0b0", 0.1, emit=5.0 * bright),
		"iron": material(f"{p}_iron", "3a3634", 0.45),
		"iron_d": material(f"{p}_iron_dark", "1e1c1c", 0.5),
		"iron_l": material(f"{p}_iron_light", "6a6460", 0.4),
		"leather": material(f"{p}_leather", "6a4428", 0.85),
		"leather_d": material(f"{p}_leather_dark", "3a2414", 0.9),
		"soot": material(f"{p}_soot", "1a1412", 0.95),
		"ash": material(f"{p}_ash", "7a7470", 0.95),
		"red": material(f"{p}_red", "d8321a", 0.5, emit=0.8 * bright),
		"orange": material(f"{p}_orange", "f86e14", 0.4, emit=1.2 * bright),
		"yellow": material(f"{p}_yellow", "ffc038", 0.3, emit=1.6 * bright),
		"white": material(f"{p}_white", "fff0b0", 0.2, emit=2.4 * bright),
		"gold": material(f"{p}_gold", "d8a038", 0.35),
	}


def _cracks(b, rng, center, radii, count, mats, bone="x", arc=(0, 360), elev=(-60, 60), length=0.14, width=0.014):
	"""Glowing fissures over an ellipsoid's face: short zigzags lying on the surface, `arc` (degrees,
	270 = the front, -Y) and `elev` limiting where they run."""
	c = Vector(center)
	rx, ry, rz = radii
	for k in range(count):
		a = math.radians(rng.uniform(*arc))
		e = math.radians(rng.uniform(*elev))
		d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
		p = c + Vector((rx * d.x, ry * d.y, rz * d.z)) * 1.01
		n = Vector((d.x / rx, d.y / ry, d.z / rz)).normalized()
		t = n.orthogonal().normalized()
		t = (t * math.cos(rng.uniform(0, math.pi)) + n.cross(t) * math.sin(rng.uniform(0, math.pi))).normalized()
		pts = [p]
		for j in range(rng.choice((2, 3))):
			step = t * length * rng.uniform(0.5, 0.9)
			jog = n.cross(t) * length * rng.uniform(-0.35, 0.35)
			pts.append(pts[-1] + step + jog)
		for j, (p0, p1) in enumerate(zip(pts, pts[1:])):
			w = width * (1.0 - 0.3 * j)
			b.seg(tuple(p0), tuple(p1), w, w * 0.7, mats[(k + j) % len(mats)], bone, sides=4)


# ---- ember giants (KayKit mesh space)

def _ember_giant_head(b, m, thane, rng):
	sk, dk = m["skin"], m["skin_d"]
	b.blob((0.56, 0.56, 0.6), (0, -0.02, 1.62), sk, "x", segs=(12, 9))                        # a heavy, square skull
	b.blob((0.62, 0.22, 0.16), (0, -0.26, 1.72), dk, "x", rot=(-8, 0, 0), segs=(10, 6))         # beetling brow
	b.blob((0.56, 0.46, 0.3), (0, -0.1, 1.42), sk, "x", segs=(10, 7))                          # the jaw, wide as the neck
	b.seg((0, -0.3, 1.68), (0, -0.4, 1.56), 0.07, 0.085, m["skin_l"], "x", sides=6)               # a broken nose
	b.blob((0.34, 0.06, 0.05), (0, -0.33, 1.46), m["crack_b"], "x", segs=(8, 4))                 # the mouth glows like a forge mouth
	for s in (1, -1):
		b.blob((0.16, 0.07, 0.1), (0.13 * s, -0.3, 1.64), m["soot"], "x", segs=(8, 5))           # sunken eyes
		b.blob((0.09, 0.04, 0.05), (0.13 * s, -0.33, 1.645), m["eye"], "x", segs=(6, 4))
		b.blob((0.12, 0.16, 0.18), (0.29 * s, -0.04, 1.6), sk, "x", segs=(6, 5))                   # small ears
		b.blob((0.2, 0.2, 0.18), (0.22 * s, -0.22, 1.5), sk, "x", segs=(8, 5))                     # heavy cheeks
	_cracks(b, rng, (0, -0.02, 1.62), (0.28, 0.28, 0.3), 9, (m["crack"], m["crack_b"]), elev=(-10, 70), length=0.1, width=0.012)
	_cracks(b, rng, (0, -0.1, 1.42), (0.28, 0.23, 0.15), 3, (m["crack"],), arc=(200, 340), elev=(-40, 20), length=0.08, width=0.011)
	if not thane:
		# a sooty topknot bound in an iron ring, and a short braided beard beaded with embers
		b.blob((0.2, 0.2, 0.16), (0, 0.12, 1.92), m["soot"], "x", segs=(8, 6))
		_wrap(b, (0, 0.12, 1.98), (0.08, 0.08), 0.06, 0.02, m["iron_l"], sides=10)
		b.seg((0, 0.14, 2.0), (0, 0.24, 2.14), 0.07, 0.03, m["soot"], "x", sides=6)
		b.blob((0.44, 0.2, 0.22), (0, -0.28, 1.34), m["soot"], "x", segs=(10, 6))
		for x in (-0.12, 0.0, 0.12):
			b.seg((x, -0.32, 1.28), (x * 0.8, -0.34, 1.08), 0.05, 0.03, m["soot"], "x", sides=5)
			b.blob((0.06, 0.06, 0.06), (x * 0.8, -0.34, 1.08), m["crack"], "x", segs=(5, 4))
		return
	# the thane: a molten beard running down over the chest, and a crown of iron points each burning
	b.blob((0.46, 0.18, 0.16), (0, -0.28, 1.36), m["red"], "x", segs=(10, 6))
	xs = (-0.21, -0.15, -0.09, -0.03, 0.03, 0.09, 0.15, 0.21)
	for k, x in enumerate(xs):
		ln = (0.46 if k % 2 else 0.34) - 0.14 * abs(x) / 0.21
		top = (x, -0.3 - 0.04 * (1 - abs(x) / 0.21), 1.42)
		mid = (x * 1.05 + 0.02 * (1 if k % 2 else -1), -0.37, 1.42 - ln * 0.5)
		end = (x * 0.8, -0.35, 1.42 - ln)
		mat = [m["red"], m["orange"], m["yellow"], m["orange"]][k % 4]
		b.seg(top, mid, 0.045, 0.035, mat, "x", sides=6)
		b.seg(mid, end, 0.035, 0.004, m["orange"] if mat is m["yellow"] else m["yellow"], "x", sides=6)
		if k % 3 == 0:
			b.blob((0.035, 0.035, 0.05), (end[0], end[1], end[2] - 0.04), m["white"], "x", segs=(5, 4))   # a molten drip
	for s in (1, -1):   # the moustache, pouring out of the mouth corners
		b.seg((0.1 * s, -0.36, 1.46), (0.2 * s, -0.36, 1.36), 0.04, 0.03, m["orange"], "x", sides=5)
	_wrap(b, (0, -0.02, 1.84), (0.3, 0.3), 0.1, 0.04, m["iron"], sides=18)
	_wrap(b, (0, -0.02, 1.8), (0.305, 0.305), 0.025, 0.045, m["iron_l"], sides=18)
	for k in range(9):
		a = 2 * math.pi * k / 9 - math.pi / 2
		p = Vector((0.3 * math.cos(a), -0.02 + 0.3 * math.sin(a), 1.86))
		out = Vector((math.cos(a), math.sin(a), 0))
		tall = 0.2 if k == 0 else 0.14
		b.seg(tuple(p), tuple(p + out * 0.04 + Vector((0, 0, tall))), 0.05, 0.01, m["iron"], "x", sides=4)
		_flame(b, tuple(p + out * 0.04 + Vector((0, 0, tall - 0.02))), (out.x * 0.2, out.y * 0.2, 1), 0.2 + 0.1 * (k == 0),
			   0.06, m["orange"] if k % 2 else m["yellow"], "x", sides=5)
	b.blob((0.09, 0.05, 0.09), (0, -0.33, 1.9), m["crack_b"], "x", segs=(6, 4))                   # an ember set in the brow


def _ember_giant_chest(b, m, thane, rng):
	sk = m["skin"]
	b.seg((0, 0.0, 1.22), (0, -0.04, 1.44), 0.2, 0.18, sk, "x", sides=10)                        # a bull neck
	b.blob((0.9, 0.58, 0.46), (0, -0.09, 1.16), sk, "x", segs=(12, 8))                          # great slabs of chest
	b.blob((0.84, 0.5, 0.52), (0, 0.12, 1.2), sk, "x", segs=(12, 8))                            # the back
	for s in (1, -1):
		b.blob((0.44, 0.46, 0.4), (0.36 * s, 0.02, 1.28), sk, "x", segs=(10, 7))                 # shoulders
		b.blob((0.34, 0.14, 0.26), (0.18 * s, -0.33, 1.14), m["skin_l"], "x", segs=(8, 5))        # pectorals
	_cracks(b, rng, (0, -0.02, 1.18), (0.46, 0.34, 0.26), 14, (m["crack"], m["crack_b"]), elev=(-30, 70), length=0.14, width=0.016)
	for s in (1, -1):
		_cracks(b, rng, (0.36 * s, 0.02, 1.28), (0.22, 0.23, 0.2), 4, (m["crack"],), elev=(0, 70), length=0.1, width=0.014)
	# the apron's bib, strapped over the shoulders
	lt, dk = m["leather"], m["leather_d"]
	_shell(b, (0.98, 0.72, 0.56), (0, -0.09, 1.16), lt, lambda d: d.y < -0.55 and abs(d.x) < 0.42 and d.z < 0.5)
	for s in (1, -1):
		b.seg((0.17 * s, -0.37, 1.24), (0.3 * s, -0.2, 1.46), 0.03, 0.03, dk, "x", sides=4)
		b.seg((0.3 * s, -0.2, 1.46), (0.26 * s, 0.3, 1.36), 0.03, 0.03, dk, "x", sides=4)
		b.seg((0.26 * s, 0.3, 1.36), (0.0, 0.4, 1.0), 0.03, 0.03, dk, "x", sides=4)
		b.blob((0.06, 0.03, 0.06), (0.17 * s, -0.38, 1.24), m["iron_l"], "x", segs=(6, 4))
	for x, z, r in ((0.08, 1.06, 0.04), (-0.12, 1.0, 0.03), (0.14, 1.14, 0.025)):   # burn holes
		y = -0.09 - 0.36 * math.sqrt(max(0.0, 1 - (x / 0.49) ** 2 - ((z - 1.16) / 0.28) ** 2)) - 0.012
		b.blob((r * 2, 0.03, r * 1.6), (x, y, z), m["soot"], "x", segs=(6, 4))
		b.blob((r, 0.03, r * 0.8), (x, y - 0.006, z), m["crack"], "x", segs=(6, 4))
	if thane:   # iron pauldrons and a gorget, rivets glowing
		for s in (1, -1):
			_shell(b, (0.5, 0.52, 0.36), (0.4 * s, 0.02, 1.36), m["iron"], lambda d: d.z > -0.05)
			_shell(b, (0.42, 0.46, 0.3), (0.47 * s, 0.02, 1.3), m["iron_d"], lambda d: d.z > 0.05 and d.x * s > 0.3)
			for k in range(4):
				a = math.radians(200 + 45 * k)
				b.blob((0.05, 0.05, 0.05), (0.4 * s + 0.27 * math.cos(a) * s, 0.02 + 0.27 * math.sin(a), 1.38), m["crack_b"], "x", segs=(5, 4))
		_wrap(b, (0, -0.02, 1.36), (0.3, 0.28), 0.08, 0.04, m["iron"], sides=16)
		b.blob((0.2, 0.06, 0.16), (0, -0.33, 1.34), m["gold"], "x", segs=(8, 5))
		b.blob((0.1, 0.04, 0.08), (0, -0.36, 1.34), m["crack_b"], "x", segs=(6, 4))


def _ember_giant_apron(b, m, thane):
	lt, dk = (m["leather"], m["leather_d"])
	_wrap(b, (0, 0.0, 0.7), (0.47, 0.4), 0.1, 0.04, dk, sides=18)                              # the belt
	b.blob((0.14, 0.05, 0.12), (0, -0.43, 0.7), m["iron_l"] if not thane else m["gold"], "x", segs=(6, 4))
	# the skirt of the apron, curved round the belly (an ellipsoid's front, tall so it hangs nearly straight)
	_shell(b, (0.98, 0.86, 2.2), (0, 0.0, 0.8), lt, lambda d: d.y < -0.6 and -0.5 < d.z < -0.04, segs=(18, 24))
	_slab(b, [(-0.13, -0.44, 0.6), (0.13, -0.44, 0.6), (0.12, -0.44, 0.47), (-0.12, -0.44, 0.47)], 0.02, dk)   # a pocket
	b.seg((0.05, -0.45, 0.52), (0.08, -0.46, 0.7), 0.016, 0.012, m["iron"], "x", sides=4)          # tongs in it
	b.seg((0.09, -0.45, 0.52), (0.12, -0.46, 0.69), 0.016, 0.012, m["iron"], "x", sides=4)
	for x, z, r in ((-0.15, 0.4, 0.035), (0.17, 0.66, 0.025), (0.04, 0.34, 0.025)):
		y = -0.43 * math.sqrt(max(0.0, 1 - (x / 0.49) ** 2 - ((z - 0.8) / 1.1) ** 2)) - 0.02
		b.blob((r * 2, 0.03, r * 1.6), (x, y, z), m["soot"], "x", segs=(6, 4))
		b.blob((r, 0.03, r * 0.8), (x, y - 0.006, z), m["crack"], "x", segs=(6, 4))
	for s in (1, -1):   # a hammer-loop and a strip of chain at the hips
		b.seg((0.46 * s, -0.1, 0.66), (0.47 * s, -0.08, 0.46), 0.025, 0.025, m["iron"], "x", sides=4)
	if thane:
		_shell(b, (0.98, 0.86, 2.2), (0, 0.0, 0.8), m["leather_d"], lambda d: d.y > 0.65 and -0.4 < d.z < -0.04, segs=(18, 24))


def _ember_giant_arm(name, s, thane):
	import random
	rng = random.Random(211 + (s > 0) + 7 * thane)
	m = burn_materials("ember_thane" if thane else "ember_giant", 1.2 if thane else 1.0)
	b = Builder(name)
	b.seg((0.2 * s, 0.0, 1.12), (0.47 * s, 0.01, 1.1), 0.17, 0.14, m["skin"], "x", sides=10)     # a thick upper arm
	b.blob((0.24, 0.26, 0.26), (0.33 * s, -0.02, 1.15), m["skin_l"], "x", segs=(9, 6))           # biceps
	_cracks(b, rng, (0.33 * s, 0.0, 1.12), (0.14, 0.16, 0.16), 5, (m["crack"], m["crack_b"]), length=0.08, width=0.012)
	return b.build_static()


def _ember_giant_bracer(name, s, thane):
	m = burn_materials("ember_thane" if thane else "ember_giant", 1.2 if thane else 1.0)
	b = Builder(name)
	b.seg((0.46 * s, 0.01, 1.1), (0.7 * s, 0.0, 1.1), 0.15, 0.14, m["iron"], "x", sides=10)
	for x in (0.48, 0.68):
		b.seg((x * s, 0.0, 1.1), ((x + 0.03) * s, 0.0, 1.1), 0.165, 0.165, m["iron_l"] if not thane else m["gold"], "x", sides=10)
	for k in range(6):
		a = 2 * math.pi * k / 6
		b.blob((0.035, 0.035, 0.035), (0.58 * s, 0.155 * math.cos(a), 1.1 + 0.155 * math.sin(a)), m["iron_l"], "x", segs=(4, 3))
	if thane:   # a glowing rune on the back of the bracer
		b.seg((0.54 * s, -0.155, 1.06), (0.62 * s, -0.155, 1.14), 0.015, 0.015, m["crack_b"], "x", sides=4)
		b.seg((0.62 * s, -0.155, 1.06), (0.54 * s, -0.155, 1.14), 0.015, 0.015, m["crack_b"], "x", sides=4)
	return b.build_static()


def build_ember_giant_head():
	import random
	b = Builder("ember_giant_head")
	_ember_giant_head(b, burn_materials("ember_giant"), False, random.Random(201))
	return b.build_static()


def build_ember_thane_head():
	import random
	b = Builder("ember_thane_head")
	_ember_giant_head(b, burn_materials("ember_thane", 1.2), True, random.Random(203))
	return b.build_static()


def build_ember_giant_chest():
	import random
	b = Builder("ember_giant_chest")
	_ember_giant_chest(b, burn_materials("ember_giant"), False, random.Random(205))
	return b.build_static()


def build_ember_thane_chest():
	import random
	b = Builder("ember_thane_chest")
	_ember_giant_chest(b, burn_materials("ember_thane", 1.2), True, random.Random(207))
	return b.build_static()


def build_ember_giant_apron():
	b = Builder("ember_giant_apron")
	_ember_giant_apron(b, burn_materials("ember_giant"), False)
	return b.build_static()


def build_ember_thane_apron():
	b = Builder("ember_thane_apron")
	_ember_giant_apron(b, burn_materials("ember_thane", 1.2), True)
	return b.build_static()


def _ember_hammer(name, great):
	"""A smith's hammer for a giant's hand, in the KayKit weapons' frame: the grip at the origin, the
	haft up +Z, the head across X. The thane's is a great two-handed maul with molten runes."""
	m = burn_materials(name, 1.3 if great else 1.0)
	b = Builder(name)
	top = 0.85 if great else 0.6
	low = -0.2 if great else -0.14
	b.seg((0, 0, low), (0, 0, top), 0.035, 0.032, m["leather_d"], "x", sides=8)                       # the haft
	b.seg((0, 0, -0.1), (0, 0, 0.14), 0.042, 0.042, m["leather"], "x", sides=8)                       # grip binding
	for z in (-0.1, 0.02, 0.14):
		b.seg((0, 0, z - 0.01), (0, 0, z + 0.01), 0.047, 0.047, m["iron_d"], "x", sides=8)
	b.blob((0.09, 0.09, 0.07), (0, 0, low), m["iron"], "x", segs=(8, 5))                                # pommel
	hw, hh = (0.2, 0.15) if great else (0.14, 0.11)
	z = top - hh * 0.4
	b.seg((-hw, 0, z), (hw, 0, z), hh * 0.62, hh * 0.62, m["iron"], "x", sides=8)                    # the head
	for s in (1, -1):
		b.seg((hw * s, 0, z), ((hw + 0.05) * s, 0, z), hh * 0.7, hh * 0.66, m["iron_l"], "x", sides=8)  # striking faces
		b.seg((hw * 0.45 * s, 0, z), (hw * 0.55 * s, 0, z), hh * 0.68, hh * 0.68, m["iron_d"], "x", sides=8)
	b.seg((0, 0, z - hh * 0.62), (0, 0, z + hh * 0.7), 0.075, 0.06, m["iron_d"], "x", sides=6)        # the socket
	# the face still glows from the forge; seams of fire run through the head
	for s in (1, -1):
		b.blob((0.03, hh * 0.9, hh * 0.9), ((hw + 0.055) * s, 0, z), m["crack"], "x", segs=(8, 6))
	b.seg((-hw * 0.4, -hh * 0.63, z), (hw * 0.4, -hh * 0.63, z), 0.018, 0.018, m["crack_b"], "x", sides=4)
	b.seg((-hw * 0.4, hh * 0.63, z), (hw * 0.4, hh * 0.63, z), 0.018, 0.018, m["crack_b"], "x", sides=4)
	if great:   # runes down the haft and a spike on top
		for k in range(3):
			zz = 0.26 + 0.12 * k
			b.seg((0, -0.035, zz), (0, -0.035, zz + 0.06), 0.011, 0.011, m["crack_b"], "x", sides=4)
			b.seg((-0.022, -0.035, zz + 0.015), (0.022, -0.035, zz + 0.045), 0.009, 0.009, m["crack_b"], "x", sides=4)
		b.seg((0, 0, top + 0.04), (0, 0, top + 0.2), 0.05, 0.0, m["iron_l"], "x", sides=6)
	return b.build_static()


def build_ember_hammer():
	return _ember_hammer("ember_hammer", False)


def build_ember_greathammer():
	return _ember_hammer("ember_greathammer", True)


# ---- firehounds and the ash wolf: one lean hound frame. The firehound is charcoal with a mane and a
# tail of flame (bones "mane" and "blaze" flicker by scale); the alpha is the same, bigger (models.json),
# brighter, scarred and notch-eared; the ash wolf is heavier, shaggy and gray, embers caught in its coat.

def build_hound(name="firehound", kind="fire"):
	import random
	rng = random.Random({"fire": 221, "alpha": 223, "ash": 227}[kind])
	ash = kind == "ash"
	alpha = kind == "alpha"
	if ash:
		fur = material(f"{name}_fur", "8a8580", 0.95)
		dark = material(f"{name}_dark", "4e4a47", 0.95)
		light = material(f"{name}_light", "bab4ac", 0.95)
	else:
		fur = material(f"{name}_fur", "2e2624" if not alpha else "241c1a", 0.9)
		dark = material(f"{name}_dark", "181210" if not alpha else "100a08", 0.9)
		light = material(f"{name}_light", "4a3a34" if not alpha else "3e2e28", 0.85)
	nose = material(f"{name}_nose", "100c0a", 0.4)
	tooth = material(f"{name}_tooth", "efe6d0", 0.5)
	eye = material(f"{name}_eye", "ff8a2a" if ash else ("ffffff" if alpha else "fff0a0"), 0.1, emit=4.0 if alpha else 3.0)
	crack = material(f"{name}_crack", "ff6a1a", 0.3, emit=2.6 if not alpha else 3.2)
	crack_b = material(f"{name}_crack_b", "ffb040", 0.3, emit=3.2)
	maw = material(f"{name}_maw", "ff7a1a" if not ash else "8a2a14", 0.3, emit=2.5 if not ash else 0.6)
	red = material(f"{name}_red", "e0381a" if not alpha else "f05a1a", 0.5, emit=1.0 if not alpha else 1.6)
	orange = material(f"{name}_orange", "f87a18" if not alpha else "ffa028", 0.4, emit=1.4 if not alpha else 2.0)
	yellow = material(f"{name}_yellow", "ffc038" if not alpha else "ffe070", 0.3, emit=1.8 if not alpha else 2.6)
	white = material(f"{name}_white", "fff0b0", 0.2, emit=3.0)
	scar = material(f"{name}_scar", "8a7a72", 0.8)
	b = Builder(name)
	w = 1.25 if ash else 1.0     # the ash wolf is broader in the chest and heavier in the head
	b.bone("root", (0, 0, 0.74))
	b.bone("body", (0, 0, 0.82), "root")
	b.bone("neck", (0, -0.5, 0.96), "body")
	b.bone("head", (0, -0.76, 1.1), "neck")
	b.bone("jaw", (0, -0.9, 1.02), "head")
	b.bone("mane", (0, -0.5, 1.04), "neck")
	b.bone("tail1", (0, 0.56, 0.9), "body")
	b.bone("tail2", (0, 0.9, 0.84), "tail1")
	b.bone("blaze", (0, 1.12, 0.84), "tail2")

	# a deep chest, a waist tucked up like a greyhound's, lean haunches
	b.blob((0.5 * w, 0.72, 0.6 * (1.05 if ash else 1.0)), (0, -0.3, 0.86), fur, "body", segs=(12, 8))
	b.seg((0, -0.08, 0.88), (0, 0.42, 0.9), 0.21 * w, 0.18 * w, fur, "body", sides=10)
	b.blob((0.42 * w, 0.5, 0.46), (0, 0.4, 0.9), fur, "body", segs=(10, 7))
	b.blob((0.34 * w, 0.52, 0.22), (0, -0.3, 0.6), light if ash else dark, "body", segs=(10, 6))        # the brisket
	b.blob((0.3 * w, 0.9, 0.16), (0, 0.06, 1.1), dark, "body", segs=(10, 6))                            # a darker back
	# neck and head: a long wedge of a skull, a narrow muzzle, ears laid back
	b.seg((0, -0.46, 0.94), (0, -0.74, 1.08), 0.18 * w, 0.14 * w, fur, "neck", sides=10)
	b.blob((0.34 * w, 0.4, 0.32), (0, -0.84, 1.12), fur, "head", segs=(10, 8))
	b.seg((0, -0.98, 1.1), (0, -1.3, 1.02), 0.11 * w, 0.065 * w, fur, "head", sides=8)                 # muzzle
	b.blob((0.09, 0.08, 0.07), (0, -1.31, 1.04), nose, "head", segs=(6, 4))
	b.blob((0.16 * w, 0.26, 0.05), (0, -1.1, 0.99), maw, "head", segs=(8, 4))                          # the glowing mouth
	b.seg((0, -0.95, 0.98), (0, -1.26, 0.95), 0.08 * w, 0.045, dark, "jaw", sides=6)                   # lower jaw
	b.blob((0.12 * w, 0.2, 0.03), (0, -1.08, 0.995), maw, "jaw", segs=(8, 4))
	for s in (1, -1):
		b.blob((0.08, 0.05, 0.045), (0.1 * s * w, -1.0, 1.17), eye, "head", rot=(0, 0, -18 * s), segs=(6, 4))
		b.blob((0.1, 0.08, 0.04), (0.1 * s * w, -0.99, 1.21), dark, "head", rot=(0, -16 * s, 0), segs=(6, 3))   # brows
		notch = alpha and s > 0
		tip = (0.2 * s * w, -0.6, 1.36 if not notch else 1.28)
		b.seg((0.12 * s * w, -0.78, 1.22), tip, 0.07, 0.01, dark, "head", sides=4)                   # ears
		for k in range(2):   # fangs
			b.seg((0.045 * s, -1.22 + 0.06 * k, 1.0), (0.05 * s, -1.22 + 0.06 * k, 0.94), 0.017, 0.003, tooth, "head", sides=4)
	# legs: straight forelegs, the hind legs bent at the hock; the pads glow where they touch
	legs = {"leg_fl": (0.16 * w, -0.44), "leg_fr": (-0.16 * w, -0.44), "leg_bl": (0.16 * w, 0.44), "leg_br": (-0.16 * w, 0.44)}
	for bone, (x, y) in legs.items():
		b.bone(bone, (x, y, 0.8), "root")
		if y < 0:
			b.seg((x, y, 0.84), (x, y + 0.02, 0.38), 0.085 * w, 0.06 * w, fur, bone, sides=6)
			b.seg((x, y + 0.02, 0.38), (x, y - 0.01, 0.07), 0.055 * w, 0.045 * w, dark, bone, sides=6)
			paw = (x, y - 0.05, 0.05)
		else:
			b.seg((x, y - 0.06, 0.88), (x, y + 0.06, 0.5), 0.12 * w, 0.075 * w, fur, bone, sides=7)
			b.seg((x, y + 0.06, 0.5), (x, y + 0.14, 0.24), 0.07 * w, 0.05, fur, bone, sides=6)
			b.seg((x, y + 0.14, 0.24), (x, y + 0.1, 0.07), 0.05, 0.045, dark, bone, sides=6)
			paw = (x, y + 0.06, 0.05)
		b.blob((0.12 * w, 0.16, 0.08), paw, dark, bone, segs=(8, 4))
		b.blob((0.08 * w, 0.1, 0.03), (paw[0], paw[1], 0.015), crack if not ash else dark, bone, segs=(6, 3))
	if ash:
		# a shaggy ruff and a ridge of ash-gray fur down the spine, embers caught in it, sooty socks
		for k in range(12):
			a = math.radians(-50 + 280 * k / 11)
			out = Vector((math.cos(a), 0, math.sin(a)))
			root_ = Vector((0.19 * w * math.cos(a), -0.56, 1.0 + 0.17 * math.sin(a)))
			d = (out * 0.5 + Vector((0, 1, -0.15))).normalized()
			_oblob(b, (0.13, 0.34, 0.05), tuple(root_ + d * 0.14), d, out, [fur, light, dark][k % 3], "mane", segs=(6, 4))
		for k in range(9):
			y = -0.4 + 0.11 * k
			for s in (1, -1, 0):
				out = Vector((0.6 * s, 0, 1)).normalized()
				d = Vector((0.2 * s, 1, 0.25)).normalized()
				root_ = Vector((0.1 * s * w, y, 1.12 - 0.02 * k - 0.03 * abs(s)))
				_oblob(b, (0.1, 0.24, 0.04), tuple(root_ + d * 0.1), d, out, dark if (k + s) % 2 else fur, "body", segs=(6, 4))
		for k in range(14):   # embers smoldering in the coat
			y = rng.uniform(-0.6, 0.5)
			a = math.radians(rng.uniform(20, 160))
			r = 0.22 * w
			b.blob((0.04, 0.04, 0.03), (r * math.cos(a), y, 0.92 + 0.2 * math.sin(a)), crack if k % 3 else crack_b, "body", segs=(4, 3))
		b.seg((0, 0.56, 0.92), (0, 0.9, 0.82), 0.1, 0.12, fur, "tail1", sides=7)
		b.blob((0.26, 0.5, 0.26), (0, 1.1, 0.72), fur, "tail2", rot=(20, 0, 0), segs=(8, 6))
		b.blob((0.16, 0.24, 0.16), (0, 1.3, 0.62), dark, "blaze", segs=(6, 5))                          # a sooty brush
		b.blob((0.05, 0.05, 0.04), (0.06, 1.22, 0.7), crack, "blaze", segs=(4, 3))
	else:
		# glowing seams in the charcoal hide, over the ribs and haunch
		_cracks(b, rng, (0, -0.3, 0.86), (0.25 * w, 0.36, 0.3), 10 if alpha else 8, (crack, crack_b), "body", arc=(-80, 80), elev=(-30, 50), length=0.12)
		_cracks(b, rng, (0, -0.3, 0.86), (0.25 * w, 0.36, 0.3), 10 if alpha else 8, (crack, crack_b), "body", arc=(100, 260), elev=(-30, 50), length=0.12)
		_cracks(b, rng, (0, 0.4, 0.9), (0.21 * w, 0.25, 0.23), 6, (crack,), "body", elev=(-20, 60), length=0.1)
		# the mane: tongues of fire along the neck ridge and over the shoulders, blown back
		n = 11 if alpha else 9
		tall = 1.35 if alpha else 1.0
		for k in range(n):
			u = k / (n - 1)
			y = -0.86 + 0.66 * u
			z = 1.24 - 0.2 * u + 0.08 * math.sin(math.pi * u)
			ln = (0.28 + 0.2 * math.sin(math.pi * min(1.0, u * 1.4))) * tall
			_flame(b, (0, y, z - 0.04), (0, 0.7, 1), ln, 0.11, red if k % 2 else orange, "mane", bend=(0, 0.25, 0))
			_flame(b, (0, y - 0.02, z), (0, 0.7, 1), ln * 0.6, 0.065, yellow if not alpha or k % 3 else white, "mane", bend=(0, 0.25, 0))
			for s in (1, -1):
				if k % 2 == 0 and 0.1 < u < 0.9:
					_flame(b, (0.12 * s, y + 0.02, z - 0.1), (0.7 * s, 0.6, 0.8), ln * 0.7, 0.08, orange if k % 4 else red, "mane", bend=(0, 0.2, 0.1))
		# the tail: a thin whip ending in a plume of flame
		b.seg((0, 0.56, 0.92), (0, 0.9, 0.86), 0.06, 0.045, fur, "tail1", sides=6)
		b.seg((0, 0.9, 0.86), (0, 1.14, 0.84), 0.045, 0.035, dark, "tail2", sides=6)
		for k, (dx, dz, ln) in enumerate(((0.0, 0.0, 0.62), (0.08, 0.04, 0.44), (-0.08, 0.04, 0.44), (0.0, -0.06, 0.4))):
			ln *= tall
			_flame(b, (dx * 0.5, 1.1, 0.84 + dz), (dx, 1, 0.55 + dz), ln, 0.12 if k == 0 else 0.09, red if k else orange, "blaze", bend=(0, 0, 0.12))
		_flame(b, (0, 1.12, 0.85), (0, 1, 0.55), 0.34 * tall, 0.06, yellow if not alpha else white, "blaze", bend=(0, 0, 0.12))
		if alpha:
			# raking claw scars down the right flank, one burning; a scar through the left eye
			for k in range(3):
				y0 = -0.46 + 0.1 * k
				p0 = Vector((-0.255, y0, 1.02))
				p1 = Vector((-0.27, y0 + 0.22, 0.76))
				b.seg(tuple(p0), tuple(p1), 0.018, 0.012, crack_b if k == 1 else scar, "body", sides=4)
			b.seg((0.13, -0.96, 1.26), (0.16, -1.06, 1.08), 0.014, 0.01, scar, "head", sides=4)
			b.seg((-0.08, -1.2, 1.1), (-0.1, -1.12, 1.14), 0.012, 0.01, scar, "head", sides=4)
			for s in (1, -1):   # a spiked iron collar, won off a hunter
				b.blob((0.05, 0.05, 0.05), (0.19 * s, -0.62, 0.9), crack_b, "neck", segs=(4, 3))
			start = len(b.parts)
			_wrap(b, (0, -0.6, 0.98), (0.2, 0.16), 0.06, 0.03, material(f"{name}_iron", "3a3634", 0.45), rot=(-60, 0, 0), sides=14)
			_on_bone(b, start, "neck")
	arm = b.build()

	def fire(t, n):
		if ash:
			return {}
		return {"mane": {"scale": (1, 1 + 0.08 * wave(t, n, 0.3), 1 + 0.14 * wave(t, n))},
				"blaze": {"scale": (1 + 0.06 * wave(t, n + 1, 0.5), 1 + 0.18 * wave(t, n + 1), 1 + 0.1 * wave(t, n, 0.2))}}

	def tail(t, amp, cycles=1):
		return {"tail1": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (0, 0, amp * wave(t, cycles, -0.15))}, "blaze": {"rot": (0, 0, amp * 0.8 * wave(t, cycles, -0.3))}}

	def idle(t):   # panting, head turning, the fire never still
		return merge_scaled({"body": {"loc": (0, 0, 0.012 * wave(t, 4))}, "head": {"rot": (4 * wave(t, 1, 0.3), 0, 10 * wave(t, 1))},
							 "jaw": {"rot": (-6 - 4 * wave(t, 8), 0, 0)}, "neck": {"rot": (2 * wave(t, 1, 0.6), 0, 0)}},
							tail(t, 8), fire(t, 8))

	def walk(t):
		return merge_scaled(_quad_legs(wave(t), 28), tail(t, 10), fire(t, 4),
							{"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "head": {"rot": (3 * wave(t, 2), 0, 0)}})

	def run(t):   # a double-suspension gallop, the mane streaming
		f, k = 46 * wave(t), 46 * wave(t, 1, 0.5)
		return merge_scaled({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
							 "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
							 "root": {"loc": (0, 0, 0.09 * max(0.0, wave(t, 1, 0.25))), "rot": (7 * wave(t, 1, 0.1), 0, 0)},
							 "neck": {"rot": (-8, 0, 0)}, "mane": {"rot": (-10, 0, 0)}}, tail(t, 5), fire(t, 3))

	def attack(t):
		lunge = seq(t, [(0, 0), (0.3, -0.12), (0.5, 0.38), (1, 0)])
		head = seq(t, [(0, 0), (0.3, 18), (0.5, -14), (1, 0)])
		jaw = seq(t, [(0, 0), (0.3, -34), (0.5, 4), (0.7, 0)])
		flare = seq(t, [(0.3, 1.0), (0.5, 1.35), (0.8, 1.0)])
		out = merge_scaled({"root": {"loc": (0, lunge, 0.05 * max(0.0, lunge)), "rot": (seq(t, [(0, 0), (0.3, 8), (0.5, -8), (1, 0)]), 0, 0)},
							"head": {"rot": (head, 0, 0)}, "jaw": {"rot": (jaw, 0, 0)}}, tail(t, 16))
		if not ash:
			out = merge_scaled(out, {"mane": {"scale": (1, 1, flare)}, "blaze": {"scale": (flare, flare, flare)}})
		return out

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"root": {"loc": (0, -0.16 * k, 0.03 * k), "rot": (10 * k, 0, 0)}, "head": {"rot": (16 * k, 0, 10 * k)},
							 "jaw": {"rot": (-20 * k, 0, 0)}}, tail(t, 20 * k), fire(t, 3))

	def death(t):   # topples onto its side; the fire gutters to embers
		roll = seq(t, [(0.15, 0), (0.6, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.15, 0), (0.6, -0.36)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		gutter = max(0.2, 1 - 0.8 * seq(t, [(0.3, 0), (1, 1)]))
		out = merge_scaled({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
							"head": {"rot": (-12 * curl, 0, 12 * curl)}, "jaw": {"rot": (-14 * curl, 0, 0)}},
						   {"leg_fl": {"rot": (28 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
							"leg_bl": {"rot": (-24 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
						   {"tail1": {"rot": (-10 * curl, 0, 0)}})
		if not ash:
			out = merge_scaled(out, {"mane": {"scale": (gutter, gutter, gutter)}, "blaze": {"scale": (gutter, gutter, gutter)}})
		return out

	clip_scaled(arm, "idle", 2.4, idle, True)
	clip_scaled(arm, "walk", 0.8, walk, True)
	clip_scaled(arm, "run", 0.45, run, True)
	clip_scaled(arm, "attack", 0.6, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.1, death, False)
	return arm


def build_firehound():
	return build_hound("firehound", "fire")


def build_firehound_alpha():
	return build_hound("firehound_alpha", "alpha")


def build_ash_wolf():
	return build_hound("ash_wolf", "ash")


# ---- fire imps: a pot-bellied little devil hovering on bat wings, grinning, a flame on its tail's tip.
# The imp lord is the same frame (bigger in models.json), crimson and gold, a crown of flame on its brow
# and a horned staff with a burning coal in its claw.

def build_imp(name="fire_imp", lord=False):
	import random
	rng = random.Random(233 if lord else 229)
	skin = material(f"{name}_skin", "a8281a" if lord else "e0501e", 0.7)
	skin_d = material(f"{name}_skin_dark", "5a0e0a" if lord else "9a2a12", 0.75)
	belly = material(f"{name}_belly", "d8582a" if lord else "f8923a", 0.7)
	horn = material(f"{name}_horn", "1e1412", 0.45)
	membrane = material(f"{name}_membrane", "6a1410" if lord else "a82c14", 0.8)
	claw = material(f"{name}_claw", "1a1210", 0.4)
	tooth = material(f"{name}_tooth", "fff4d8", 0.4)
	mouth = material(f"{name}_mouth", "3a0806", 0.8)
	eye = material(f"{name}_eye", "fff4a0", 0.1, emit=4.5)
	red = material(f"{name}_red", "e0381a", 0.5, emit=1.2)
	orange = material(f"{name}_orange", "f87a18", 0.4, emit=1.8)
	yellow = material(f"{name}_yellow", "ffd050", 0.3, emit=2.4)
	white = material(f"{name}_white", "fff0b0", 0.2, emit=3.2)
	gold = material(f"{name}_gold", "e0a83a", 0.3)
	cloth = material(f"{name}_cloth", "2a1414", 0.9)
	wood = material(f"{name}_wood", "2e1c14", 0.8)
	b = Builder(name)
	b.bone("root", (0, 0, 0.8))
	b.bone("hips", (0, 0.02, 0.74), "root")
	b.bone("chest", (0, 0.0, 0.9), "hips")
	b.bone("head", (0, -0.04, 1.12), "chest")
	b.bone("jaw", (0, -0.16, 1.1), "head")
	b.bone("tail1", (0, 0.12, 0.7), "hips")
	b.bone("tail2", (0, 0.4, 0.56), "tail1")
	b.bone("tail3", (0, 0.66, 0.62), "tail2")
	b.bone("flame", (0, 0.8, 0.74), "tail3")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"arm_{side}", (0.18 * s, -0.02, 1.02), "chest")
		b.bone(f"hand_{side}", (0.26 * s, -0.08, 0.82), f"arm_{side}")
		b.bone(f"leg_{side}", (0.1 * s, 0.02, 0.68), "hips")
		b.bone(f"wing_{side}", (0.08 * s, 0.12, 1.02), "chest")

	# the body: a round belly, narrow shoulders
	b.blob((0.34, 0.32, 0.34), (0, -0.02, 0.76), skin, "hips", segs=(10, 8))
	b.blob((0.28, 0.2, 0.26), (0, -0.1, 0.76), belly, "hips", segs=(10, 6))
	b.blob((0.34, 0.26, 0.26), (0, 0.0, 0.96), skin, "chest", segs=(10, 7))
	# the head: big for the body, a pointed chin, a grin from ear to ear
	b.blob((0.36, 0.34, 0.32), (0, -0.06, 1.2), skin, "head", segs=(12, 9))
	b.blob((0.2, 0.16, 0.14), (0, -0.14, 1.07), skin, "jaw", segs=(8, 6))
	b.seg((0, -0.18, 1.06), (0, -0.24, 0.98), 0.05, 0.005, skin_d, "jaw", sides=5)               # the pointed chin
	b.blob((0.26, 0.06, 0.07), (0, -0.21, 1.12), mouth, "head", segs=(10, 4))                      # the grin
	for k in range(5):
		x = (k - 2) * 0.045
		b.seg((x, -0.225, 1.14), (x, -0.235, 1.11), 0.012, 0.0, tooth, "head", sides=4)
	for x in (-0.05, 0.05):
		b.seg((x, -0.2, 1.09), (x, -0.215, 1.12), 0.012, 0.0, tooth, "jaw", sides=4)
	b.seg((0, -0.2, 1.22), (0, -0.28, 1.17), 0.035, 0.012, skin_d, "head", sides=5)                # a hooked nose
	for s in (1, -1):
		b.blob((0.09, 0.05, 0.065), (0.075 * s, -0.2, 1.25), eye, "head", rot=(0, 0, -12 * s), segs=(6, 4))
		b.blob((0.03, 0.02, 0.035), (0.075 * s, -0.225, 1.25), horn, "head", segs=(4, 3))            # slit pupils
		b.blob((0.12, 0.05, 0.04), (0.075 * s, -0.2, 1.3), skin_d, "head", rot=(0, 24 * s, 0), segs=(6, 3))   # wicked brows
		b.seg((0.16 * s, -0.04, 1.22), (0.36 * s, 0.04, 1.3), 0.05, 0.004, skin, "head", sides=4)    # long pointed ears
		b.seg((0.17 * s, -0.05, 1.22), (0.32 * s, 0.02, 1.28), 0.025, 0.004, skin_d, "head", sides=4)
		pts = [(0.08 * s, -0.1, 1.32), (0.12 * s, -0.06, 1.44), (0.13 * s, 0.04, 1.52), (0.1 * s, 0.14, 1.55)]   # horns sweeping back
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(p, q, 0.04 - 0.012 * k, 0.028 - 0.012 * k, horn, "head", sides=5)
	# skinny arms with clawed hands
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		b.blob((0.1, 0.1, 0.1), (0.18 * s, -0.02, 1.02), skin, arm, segs=(6, 5))
		b.seg((0.18 * s, -0.02, 1.02), (0.26 * s, -0.08, 0.82), 0.04, 0.03, skin, arm, sides=6)
		b.seg((0.26 * s, -0.08, 0.82), (0.28 * s, -0.16, 0.66), 0.03, 0.035, skin, hand, sides=6)
		b.blob((0.08, 0.08, 0.07), (0.28 * s, -0.17, 0.64), skin_d, hand, segs=(6, 4))
		for k in (-1, 0, 1):
			root_ = Vector((0.28 * s + 0.025 * k, -0.19, 0.61))
			b.seg(tuple(root_), tuple(root_ + Vector((0.01 * k, -0.04, -0.06))), 0.012, 0.0, claw, hand, sides=4)
		if lord:
			start = len(b.parts)
			_wrap(b, (0.27 * s, -0.12, 0.74), (0.04, 0.04), 0.04, 0.012, gold, rot=(20, 0, 0), sides=10)
			_on_bone(b, start, hand)
	# legs dangling under it, digitigrade, clawed toes pointing down
	for s in (1, -1):
		leg = f"leg_{'l' if s > 0 else 'r'}"
		b.seg((0.1 * s, 0.0, 0.7), (0.12 * s, -0.08, 0.54), 0.055, 0.04, skin, leg, sides=6)
		b.seg((0.12 * s, -0.08, 0.54), (0.12 * s, 0.02, 0.38), 0.04, 0.028, skin, leg, sides=6)
		b.seg((0.12 * s, 0.02, 0.38), (0.12 * s, -0.04, 0.3), 0.028, 0.022, skin_d, leg, sides=5)
		for k in (-1, 0, 1):
			root_ = Vector((0.12 * s + 0.02 * k, -0.05, 0.3))
			b.seg(tuple(root_), tuple(root_ + Vector((0.01 * k, -0.05, -0.04))), 0.012, 0.0, claw, leg, sides=4)
	# bat wings, spread for hovering
	for s in (1, -1):
		_bat_wing(b, s, (0.08 * s, 0.12, 1.02), (skin_d, membrane, claw), f"wing_{'l' if s > 0 else 'r'}", scale=0.8 if not lord else 0.9)
	# the tail: a thin whip curling up at the end, a flame burning on its tip
	pts = [(0, 0.1, 0.7), (0, 0.4, 0.56), (0, 0.66, 0.62), (0, 0.8, 0.74)]
	for k, bone in enumerate(("tail1", "tail2", "tail3")):
		b.seg(pts[k], pts[k + 1], 0.035 - 0.008 * k, 0.028 - 0.008 * k, skin if k % 2 else skin_d, bone, sides=5)
	_flame(b, (0, 0.8, 0.72), (0, 0.2, 1), 0.3, 0.09, red, "flame", bend=(0, 0.15, 0))
	_flame(b, (0, 0.79, 0.73), (0, 0.2, 1), 0.2, 0.06, orange, "flame", bend=(0, 0.15, 0))
	_flame(b, (0, 0.78, 0.74), (0, 0.2, 1), 0.12, 0.035, yellow, "flame", bend=(0, 0.15, 0))
	if lord:
		# a loincloth, a gold collar, a crown of flame on a gold circlet
		start = len(b.parts)
		_slab(b, [(-0.1, -0.15, 0.68), (0.1, -0.15, 0.68), (0.07, -0.13, 0.5), (0, -0.12, 0.46), (-0.07, -0.13, 0.5)], 0.02, cloth)
		_on_bone(b, start, "hips")
		start = len(b.parts)
		_wrap(b, (0, 0.0, 1.06), (0.12, 0.1), 0.04, 0.02, gold, sides=12)
		_on_bone(b, start, "chest")
		b.blob((0.05, 0.03, 0.05), (0, -0.12, 1.02), orange, "chest", segs=(5, 4))
		start = len(b.parts)
		_wrap(b, (0, -0.05, 1.32), (0.15, 0.14), 0.04, 0.02, gold, rot=(-10, 0, 0), sides=14)
		_on_bone(b, start, "head")
		for k in range(7):
			a = 2 * math.pi * k / 7 - math.pi / 2
			base = (0.15 * math.cos(a), -0.05 + 0.14 * math.sin(a), 1.33 - 0.025 * math.sin(a))
			tall = 0.26 if k == 0 else 0.18
			_flame(b, base, (0.2 * math.cos(a), 0.15 + 0.2 * math.sin(a), 1), tall, 0.06, orange if k % 2 else red, "head", bend=(0, 0.1, 0))
			_flame(b, base, (0.2 * math.cos(a), 0.15 + 0.2 * math.sin(a), 1), tall * 0.6, 0.035, yellow, "head", bend=(0, 0.1, 0))
		b.blob((0.05, 0.03, 0.05), (0, -0.2, 1.34), white, "head", segs=(5, 4))                      # a gem of fire in the circlet
		# the staff, upright in the right claw: a horned head holding a burning coal
		x, y = -0.29, -0.2
		b.seg((x, y, 0.2), (x, y, 1.3), 0.022, 0.02, wood, "hand_r", sides=6)
		for z in (0.62, 0.7):
			b.seg((x, y, z), (x, y, z + 0.02), 0.03, 0.03, gold, "hand_r", sides=6)
		for s in (1, -1):
			b.seg((x, y, 1.28), (x + 0.07 * s, y, 1.38), 0.02, 0.014, horn, "hand_r", sides=5)
			b.seg((x + 0.07 * s, y, 1.38), (x + 0.05 * s, y, 1.5), 0.014, 0.0, horn, "hand_r", sides=5)
		b.blob((0.1, 0.1, 0.1), (x, y, 1.4), yellow, "hand_r", segs=(8, 6))
		b.blob((0.06, 0.06, 0.06), (x, y - 0.02, 1.4), white, "hand_r", segs=(6, 4))
		_flame(b, (x, y, 1.42), (0, 0.1, 1), 0.22, 0.06, orange, "hand_r", bend=(0, 0.1, 0))
	arm = b.build()

	def wings(t, cycles, amp=38, open_=1.0):
		"""Spread and beating: pitched back a little and rolled so the membranes flap up and down."""
		f = amp * wave(t, cycles)
		return {"wing_l": {"rot": (-12 * open_, -40 * open_ - f, -34 * open_)}, "wing_r": {"rot": (-12 * open_, 40 * open_ + f, 34 * open_)}}

	def tail(t, amp, cycles=1):
		return {"tail1": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (6 * wave(t, cycles, 0.4), 0, amp * wave(t, cycles, -0.15))},
				"tail3": {"rot": (0, 0, amp * 1.2 * wave(t, cycles, -0.3))},
				"flame": {"scale": (1 + 0.1 * wave(t, 6, 0.2), 1 + 0.1 * wave(t, 6, 0.2), 1 + 0.25 * wave(t, 6))}}

	def arms(l, r, bend=0.0, spread=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, 0, 0)}, "hand_r": {"rot": (bend, 0, 0)}}

	def idle(t):   # bobs on its beating wings and cackles now and then, shoulders shaking
		laugh = seq(t, [(0.45, 0), (0.5, 1), (0.8, 1), (0.86, 0)])
		shake = laugh * wave(t, 12)
		return merge_scaled({"root": {"loc": (0, 0, 0.06 * wave(t, 4))}, "chest": {"rot": (-8 * laugh, 0, 0), "loc": (0, 0, 0.02 * shake)},
							 "head": {"rot": (-14 * laugh + 4 * wave(t, 2), 0, 8 * wave(t, 1))},
							 "jaw": {"rot": (-8 - 16 * laugh * (0.5 + 0.5 * wave(t, 12)), 0, 0)},
							 "leg_l": {"rot": (6 * wave(t, 4, 0.2), 0, 0)}, "leg_r": {"rot": (6 * wave(t, 4, 0.4), 0, 0)}},
							wings(t, 8), tail(t, 12), arms(10 + 6 * wave(t, 4), 10 + 6 * wave(t, 4, 0.3), -20, 10 + 12 * laugh))

	def walk(t):   # flits forward, leaning in, legs trailing
		return merge_scaled({"root": {"loc": (0, 0, 0.05 * wave(t, 2)), "rot": (-16, 0, 0)}, "head": {"rot": (12, 0, 0)},
							 "leg_l": {"rot": (-24, 0, 0)}, "leg_r": {"rot": (-30, 0, 0)}}, wings(t, 6), tail(t, 10), arms(-10, 16 if lord else -10, -20, 6),
							{"hand_r": {"rot": (20 if lord else 0, 0, 0)}})

	def run(t):
		return merge_scaled({"root": {"loc": (0, 0, 0.04 * wave(t, 2)), "rot": (-30, 0, 0)}, "head": {"rot": (22, 0, 0)},
							 "leg_l": {"rot": (-40, 0, 0)}, "leg_r": {"rot": (-46, 0, 0)}}, wings(t, 4, 44), tail(t, 6), arms(-40, 30 if lord else -40, -10, 10),
							{"hand_r": {"rot": (10 if lord else 0, 0, 0)}})

	def attack(t):
		if lord:   # raises the staff overhead and thrusts the burning head forward
			up = seq(t, [(0, 0), (0.35, 150), (0.5, 60), (0.7, 60), (1, 0)])
			lean = seq(t, [(0, 0), (0.35, 10), (0.5, -16), (0.7, -12), (1, 0)])
			return merge_scaled({"root": {"loc": (0, seq(t, [(0, 0), (0.5, 0.24), (1, 0)]), 0)}, "chest": {"rot": (lean, 0, 0)},
								 "head": {"rot": (-lean, 0, 0)}, "jaw": {"rot": (seq(t, [(0.3, 0), (0.5, -26), (0.8, 0)]), 0, 0)},
								 "arm_r": {"rot": (up, 0, 0)}, "hand_r": {"rot": (seq(t, [(0, 0), (0.35, 20), (0.5, -30), (1, 0)]), 0, 0)},
								 "arm_l": {"rot": (seq(t, [(0, 10), (0.35, 50), (0.5, -10), (1, 10)]), 20, 0)}}, wings(t, 6), tail(t, 14))
		# darts in and rakes with both claws, cackling
		dart = seq(t, [(0, 0), (0.3, -0.1), (0.5, 0.4), (0.75, 0.3), (1, 0)])
		claws = seq(t, [(0, 0), (0.3, 150), (0.5, 20), (0.7, 0), (1, 0)])
		return merge_scaled({"root": {"loc": (0, dart, 0.08 * seq(t, [(0, 0), (0.3, 1), (0.6, 0)])), "rot": (seq(t, [(0, 0), (0.3, 10), (0.5, -24), (1, 0)]), 0, 0)},
							 "jaw": {"rot": (seq(t, [(0.2, 0), (0.45, -30), (0.8, 0)]), 0, 0)}},
							arms(claws, claws * 0.9, seq(t, [(0, 0), (0.3, 30), (0.5, -20), (1, 0)]), 16), wings(t, 7, 44), tail(t, 16))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"root": {"loc": (0, -0.18 * k, 0.06 * k), "rot": (18 * k, 10 * k, 0)}, "head": {"rot": (14 * k, 0, 16 * k)},
							 "jaw": {"rot": (-24 * k, 0, 0)}}, arms(-30 * k, -24 * k, 0, 20 * k), wings(t, 6), tail(t, 20 * k + 4))

	def death(t):   # the wings falter and it drops to the ground in a heap, the tail flame snuffed
		f = seq(t, [(0.1, 0), (0.6, 1)])
		g = seq(t, [(0.5, 0), (0.9, 1)])
		beat = 1 - seq(t, [(0.1, 0), (0.5, 1)])
		out = merge_scaled({"root": {"loc": (0, -0.1 * f, -0.56 * f), "rot": (-10 * f, 0, 0)},
							"hips": {"rot": (-70 * g, 70 * g, 0)}, "head": {"rot": (-10 * g, 0, 30 * g)}, "jaw": {"rot": (-20 * g, 0, 0)},
							"leg_l": {"rot": (60 * f, 0, 0)}, "leg_r": {"rot": (40 * f, 0, 0)},
							"flame": {"scale": (max(0.05, 1 - g),) * 3}},
						   arms(30 * g, 60 * g, -30 * g, 30 * g), wings(t, 6, 38 * beat, 1 - 0.6 * g))
		return out

	clip_scaled(arm, "idle", 3.0, idle, True)
	clip_scaled(arm, "walk", 0.75, walk, True)
	clip_scaled(arm, "run", 0.5, run, True)
	clip_scaled(arm, "attack", 0.8 if lord else 0.6, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.2, death, False)
	return arm


def build_fire_imp():
	return build_imp("fire_imp", False)


def build_imp_lord():
	return build_imp("imp_lord", True)


# ---- smoke spirit: the air elemental's frame (trunk root > low > mid > chest > head, arm > hand) made of
# the Burn's smoke. A column of dark smoke trailing to a wisp above the ground, billowing up into
# shoulders and a hooded head with ember eyes; wisping arms end in smoky fingers tipped with sparks,
# and glints of fire drift inside it.

def build_smoke_spirit():
	import random
	rng = random.Random(239)
	smoke = material("smoke_spirit_smoke", "4a4644", 0.95)
	smoke_d = material("smoke_spirit_dark", "2a2624", 0.95)
	smoke_l = material("smoke_spirit_light", "6e6864", 0.95)
	soot = material("smoke_spirit_soot", "141010", 0.95)
	ember = material("smoke_spirit_ember", "ff6a1a", 0.3, emit=3.0)
	ember_b = material("smoke_spirit_ember_b", "ffb040", 0.3, emit=3.6)
	glow = material("smoke_spirit_glow", "c83a10", 0.5, emit=1.4)
	eye = material("smoke_spirit_eye", "ffd070", 0.1, emit=6.0)
	b = Builder("smoke_spirit")
	b.bone("root", (0, 0, 0.05))
	b.bone("trail", (0, 0, 0.1), "root")
	b.bone("low", (0, 0, 0.35), "root")
	b.bone("mid", (0, 0, 0.95), "low")
	b.bone("chest", (0, 0, 1.45), "mid")
	b.bone("billow", (0, 0, 1.55), "chest")
	b.bone("head", (0, -0.04, 1.95), "chest")
	b.bone("sparks", (0, 0, 1.0), "root")

	def puffs(center, r, count, mats, bone, spread=1.0, squash=0.85):
		start = len(b.parts)
		for k in range(count):
			off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 0.6))) * r * 0.55 * spread
			sz = r * rng.uniform(0.75, 1.2)
			b.blob((sz, sz, sz * squash), tuple(Vector(center) + off), mats[k % len(mats)], "x", segs=(8, 6))
		_on_bone(b, start, bone)

	# the trailing column: puffs narrowing and twisting down to a wisp just off the ground
	for k in range(8):
		u = k / 7
		z = 0.2 + 0.7 * u
		r = 0.12 + 0.34 * u * u
		a = u * 5.0
		puffs((0.06 * math.sin(a), 0.08 * math.cos(a) + 0.06 * (1 - u), z), r, 3, (smoke_d, smoke, soot), "trail" if u < 0.5 else "low")
	_flame(b, (0.02, 0.1, 0.24), (0.1, 0.4, -1), 0.24, 0.07, smoke_d, "trail", bend=(0.1, 0.2, 0), sides=5)
	# the body: a heaving mass of smoke, the fire inside it showing through the gaps
	b.blob((0.34, 0.3, 0.44), (0, -0.04, 1.2), glow, "mid", segs=(10, 8))
	puffs((0, 0, 1.1), 0.44, 6, (smoke, smoke_d, smoke_l), "mid", spread=0.9)
	b.blob((0.42, 0.34, 0.36), (0, -0.04, 1.6), glow, "chest", segs=(10, 8))
	puffs((0, 0.02, 1.58), 0.5, 7, (smoke, smoke_l, smoke_d), "chest", spread=1.1)
	for s in (1, -1):   # rolling shoulders
		puffs((0.4 * s, 0.02, 1.74), 0.34, 3, (smoke_l, smoke), "billow")
	puffs((0, 0.24, 1.8), 0.38, 3, (smoke, smoke_d), "billow")
	for k in range(10):   # glints of fire in the smoke
		a = rng.uniform(0, 2 * math.pi)
		z = rng.uniform(0.7, 1.85)
		rr = 0.24 + 0.2 * min(1.0, (z - 0.6) / 0.8)
		b.blob((0.045, 0.045, 0.045), (rr * math.cos(a), rr * math.sin(a), z), ember if k % 3 else ember_b, "mid" if z < 1.3 else "chest", segs=(4, 3))
	# the head: a hood of smoke round a black hollow, two ember eyes, a smoldering brow
	puffs((0, 0.04, 2.02), 0.36, 5, (smoke, smoke_l, smoke_d), "head")
	b.blob((0.34, 0.2, 0.3), (0, -0.2, 1.98), soot, "head", segs=(10, 7))
	for s in (1, -1):
		b.blob((0.13, 0.05, 0.07), (0.085 * s, -0.305, 2.0), eye, "head", rot=(0, 18 * s, -14 * s), segs=(6, 4))
	b.blob((0.2, 0.03, 0.03), (0, -0.305, 1.9), ember, "head", segs=(6, 3))
	for k in range(3):   # a wisp curling up off the crown
		_flame(b, (0.06 * (k - 1), 0.1, 2.14), (0.4 * (k - 1), 0.6, 1), 0.5 - 0.1 * abs(k - 1), 0.08, smoke_l if k != 1 else smoke, "head",
			   bend=(0, 0.5, -0.2), sides=5, parts=4)
	# wisping arms: streams of smoke to long smoky fingers, sparks at their tips
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, hand = f"arm_{side}", f"hand_{side}"
		b.bone(arm, (0.46 * s, 0, 1.74), "chest")
		b.bone(hand, (0.7 * s, -0.06, 1.28), arm)
		b.seg((0.46 * s, 0, 1.74), (0.7 * s, -0.06, 1.28), 0.09, 0.06, smoke_d, arm, sides=6)
		for k in range(4):
			u = (k + 0.3) / 4
			puffs((0.46 * s + 0.24 * s * u, -0.06 * u, 1.74 - 0.46 * u), 0.2 - 0.025 * k, 2, (smoke_l, smoke), arm)
		b.seg((0.7 * s, -0.06, 1.28), (0.76 * s, -0.12, 0.98), 0.06, 0.08, smoke_d, hand, sides=6)
		for k in range(2):
			puffs((0.72 * s, -0.08 - 0.03 * k, 1.2 - 0.14 * k), 0.15, 2, (smoke, smoke_l), hand)
		puffs((0.76 * s, -0.12, 0.96), 0.2, 3, (smoke, smoke_d), hand)
		for k in range(4):   # fingers of smoke reaching down and forward, a spark at each tip
			a = math.radians(-40 + 27 * k)
			d = Vector((0.35 * s * math.cos(a), -0.6 + 0.3 * math.sin(a), -1)).normalized()
			base = Vector((0.78 * s, -0.16, 0.9))
			ln = 0.36 - 0.05 * abs(k - 1.5)
			_flame(b, tuple(base), tuple(d), ln, 0.06, smoke_d if k % 2 else smoke, hand, bend=(0, -0.15, 0.25), sides=5, parts=4)
			b.blob((0.035, 0.035, 0.035), tuple(base + d * ln * 0.95 + Vector((0, 0, 0.05))), ember_b, hand, segs=(4, 3))
		for k in range(2):   # streamers trailing off the forearm
			_flame(b, (0.62 * s, 0.1, 1.5 - 0.2 * k), (0.3 * s, 1, 0.3), 0.4, 0.07, smoke_l if k else smoke_d, arm, bend=(0, 0, 0.3), sides=5)
	# loose cinders swirling round it
	for k in range(9):
		a = 2 * math.pi * k / 9
		r = 0.62 + 0.1 * (k % 2)
		z = 0.5 + 0.12 * k
		b.blob((0.04, 0.04, 0.04), (r * math.cos(a), r * math.sin(a), z - 1.0 + 1.0), ember if k % 2 else ember_b, "sparks", segs=(4, 3))
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, 0, 0)}, "arm_r": {"rot": (r, 0, 0)},
				"hand_l": {"rot": (bend, spread, 0)}, "hand_r": {"rot": (bend, -spread, 0)}}

	def smoke_(t, n, spin):
		# the smoke heaves: each bone's puffs swell and shrink out of step; the cinders circle
		return {"trail": {"rot": (0, 0, spin * t), "scale": (1 + 0.08 * wave(t, n), 1 + 0.08 * wave(t, n), 1 + 0.06 * wave(t, n, 0.3))},
				"billow": {"scale": (1 + 0.07 * wave(t, n, 0.4), 1 + 0.07 * wave(t, n, 0.4), 1 + 0.1 * wave(t, n, 0.1))},
				"mid": {"scale": (1 + 0.04 * wave(t, n, 0.7), 1 + 0.04 * wave(t, n, 0.7), 1)},
				"sparks": {"rot": (0, 0, spin * 1.5 * t), "loc": (0, 0, 0.05 * wave(t, n))}}

	def body(t, lean, sway, cycles=1):
		return {"low": {"rot": (lean + 3 * wave(t, cycles, 0.25), sway * wave(t, cycles), 0), "loc": (0, 0, 0.05 * wave(t, cycles * 2))},
				"mid": {"rot": (lean * 0.4 + 3 * wave(t, cycles, 0.5), -sway * 0.6 * wave(t, cycles, 0.1), 5 * wave(t, cycles))},
				"chest": {"rot": (lean * 0.2, -sway * 0.4 * wave(t, cycles, 0.2), -5 * wave(t, cycles, 0.3))},
				"head": {"rot": (-lean * 0.5 + 4 * wave(t, cycles, 0.6), 0, 8 * wave(t, cycles, 0.1))}}

	def idle(t):
		return merge_scaled(body(t, 0, 4, 1), smoke_(t, 3, 360), arms(8 * wave(t, 1, 0.1), 8 * wave(t, 1, 0.6), 6, 8 + 6 * wave(t, 2)))

	def walk(t):   # drifts along, leaning in, the column streaming back
		return merge_scaled(body(t, -12, 5), smoke_(t, 2, 360), arms(-8 + 16 * wave(t), -8 - 16 * wave(t), 8, 12),
							{"trail": {"rot": (20, 0, 0)}})

	def run(t):
		return merge_scaled(body(t, -24, 6), smoke_(t, 2, 360), arms(-44 + 8 * wave(t, 2), -44 - 8 * wave(t, 2), 12, 22),
							{"trail": {"rot": (36, 0, 0)}})

	def attack(t):   # rears up and lashes both arms down, the smoke and sparks flaring
		up = seq(t, [(0, 0), (0.35, 140), (0.45, 150), (0.58, 30), (0.72, 15), (1, 0)])
		spread = seq(t, [(0, 0), (0.35, 40), (0.45, 45), (0.58, -30), (0.72, -25), (1, 0)])
		snap = seq(t, [(0, 0), (0.35, 50), (0.5, 60), (0.62, -45), (0.75, -20), (1, 0)])
		lean = seq(t, [(0, 0), (0.35, 10), (0.58, -20), (0.75, -16), (1, 0)])
		surge = seq(t, [(0, 0), (0.45, -0.05), (0.6, 0.3), (0.8, 0.24), (1, 0)])
		flare = seq(t, [(0.45, 1.0), (0.6, 1.3), (0.9, 1.0)])
		return merge_scaled({"root": {"loc": (0, surge, 0)}, "low": {"rot": (lean * 0.5, 0, 0)}, "mid": {"rot": (lean * 0.4, 0, 0)},
							 "chest": {"rot": (lean * 0.3, 0, 0)}, "head": {"rot": (-lean * 0.4, 0, 0)},
							 "billow": {"scale": (flare, flare, flare)}, "sparks": {"scale": (flare, flare, flare), "rot": (0, 0, 300 * t)},
							 "arm_l": {"rot": (up, spread, 0)}, "arm_r": {"rot": (up, -spread, 0)},
							 "hand_l": {"rot": (snap, 0, 0)}, "hand_r": {"rot": (snap, 0, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"low": {"rot": (12 * k, 8 * k, 0)}, "mid": {"rot": (10 * k, 0, 0)}, "head": {"rot": (14 * k, 0, 12 * k)},
							 "billow": {"scale": (1 + 0.25 * k, 1 + 0.25 * k, 1 - 0.2 * k)}}, smoke_(t, 1, 120), arms(-30 * k, -24 * k, 18 * k, -12 * k))

	def death(t):   # it comes apart: the smoke spreads wide and thin and sinks, the embers winking out low
		reel = seq(t, [(0, 0), (0.2, 14), (0.35, -8), (0.5, 0)])
		d = seq(t, [(0.2, 0), (0.95, 1)])
		thin = max(0.22, 1 - 0.78 * d)
		wide = 1 + 0.6 * d
		return merge_scaled({"trail": {"rot": (0, 0, 300 * t), "scale": (wide, wide, thin)},
							 "low": {"rot": (reel, reel * 0.4, 0), "loc": (0, 0, -0.25 * d), "scale": (1 + 0.5 * d, 1 + 0.5 * d, max(0.2, 1 - 0.8 * d))},
							 "mid": {"rot": (-reel * 0.6, 0, 0), "scale": (1 + 0.4 * d, 1 + 0.4 * d, thin)},
							 "billow": {"scale": (wide, wide, thin)},
							 "head": {"rot": (reel, 0, 30 * d), "scale": (1 + 0.3 * d, 1 + 0.3 * d, thin)},
							 "sparks": {"loc": (0, 0, -0.8 * d), "scale": (1 + d, 1 + d, max(0.1, 1 - d))}},
							arms(-40 * d + reel, -30 * d - reel, 40 * d, 0))

	clip_scaled(arm, "idle", 3.0, idle, False)
	clip_scaled(arm, "walk", 1.2, walk, False)
	clip_scaled(arm, "run", 0.8, run, False)
	clip_scaled(arm, "attack", 0.9, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.8, death, False)
	return arm


# ---- firebird and phoenix: a blazing bird hovering at head height on outspread wings (wing > tip bones
# beat by roll, the tips lagging), flame feathers graded red to gold, a long tail of plumes. The phoenix
# is the same frame (bigger in models.json) burning gold-white, with a taller crest and long trailing
# tail plumes ending in flame eyes.

def build_firebird(name="firebird", phoenix=False):
	g = 1.25 if phoenix else 1.0   # glow
	if phoenix:
		body_c, back_c, breast_c = "ffb838", "f8862a", "fff0b8"
		feather = ["f86a1a", "ffa030", "ffd060", "fff4c8"]
	else:
		body_c, back_c, breast_c = "f07020", "c8321a", "ffb040"
		feather = ["a8200e", "e0441a", "f88a24", "ffc848"]
	body = material(f"{name}_body", body_c, 0.5, emit=0.5 * g)
	back = material(f"{name}_back", back_c, 0.5, emit=0.4 * g)
	breast = material(f"{name}_breast", breast_c, 0.4, emit=0.8 * g)
	fm = [material(f"{name}_feather_{k}", c, 0.45, emit=(0.5 + 0.35 * k) * g) for k, c in enumerate(feather)]
	white = material(f"{name}_white", "fff8e0", 0.2, emit=3.0 * g)
	beak = material(f"{name}_beak", "e8b030" if not phoenix else "f8e090", 0.3)
	beak_d = material(f"{name}_beak_dark", "3a1a0a", 0.4)
	eye = material(f"{name}_eye", "fffbe8", 0.1, emit=6.0)
	talon = material(f"{name}_talon", "2a1a10", 0.4)
	b = Builder(name)
	H = 1.7   # hover height of the body
	b.bone("root", (0, 0, H))
	b.bone("body", (0, 0, H), "root")
	b.bone("neck", (0, -0.26, H + 0.1), "body")
	b.bone("head", (0, -0.4, H + 0.3), "neck")
	b.bone("tail1", (0, 0.32, H - 0.04), "body")
	b.bone("tail2", (0, 0.9 if not phoenix else 1.0, H - 0.2), "tail1")
	b.bone("legs", (0, 0.06, H - 0.18), "body")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"wing_{side}", (0.16 * s, -0.06, H + 0.1), "body")
		b.bone(f"tip_{side}", (0.86 * s, 0.0, H + 0.12), f"wing_{side}")

	# the body: a teardrop leaning forward, a pale breast, darker back
	b.blob((0.44, 0.8, 0.46), (0, 0.02, H), body, "body", rot=(-12, 0, 0), segs=(12, 9))
	b.blob((0.36, 0.42, 0.38), (0, -0.2, H - 0.04), breast, "body", rot=(-20, 0, 0), segs=(10, 7))
	b.blob((0.34, 0.6, 0.18), (0, 0.08, H + 0.18), back, "body", rot=(-8, 0, 0), segs=(10, 6))
	for k in range(6):   # breast feathers like scales of flame
		x = (k % 3 - 1) * 0.1
		z = H - 0.02 - 0.1 * (k // 3)
		_oblob(b, (0.1, 0.16, 0.03), (x, -0.36 + 0.03 * (k // 3), z), (0, 0.3, -1), (0, -1, 0.2), fm[2], "body", segs=(6, 4))
	# neck and head: a slender neck, a hooked golden beak, white-hot eyes, a crest of flame feathers
	b.seg((0, -0.18, H + 0.06), (0, -0.4, H + 0.3), 0.14, 0.1, body, "neck", sides=8)
	b.blob((0.24, 0.3, 0.24), (0, -0.44, H + 0.34), body, "head", segs=(10, 8))
	b.blob((0.18, 0.14, 0.14), (0, -0.52, H + 0.28), breast, "head", segs=(8, 5))
	b.seg((0, -0.56, H + 0.34), (0, -0.72, H + 0.3), 0.06, 0.03, beak, "head", sides=6)
	b.seg((0, -0.72, H + 0.3), (0, -0.75, H + 0.23), 0.03, 0.004, beak_d, "head", sides=5)
	for s in (1, -1):
		b.blob((0.06, 0.05, 0.05), (0.09 * s, -0.53, H + 0.37), eye, "head", segs=(6, 4))
		b.blob((0.12, 0.08, 0.04), (0.08 * s, -0.52, H + 0.41), back, "head", rot=(0, -20 * s, 0), segs=(6, 3))
	crest = 7 if phoenix else 5
	for k in range(crest):
		x = (k - (crest - 1) / 2) * 0.05
		ln = (0.36 if not phoenix else 0.56) * (1 - 0.12 * abs(k - (crest - 1) / 2))
		_flame(b, (x, -0.42, H + 0.44), (x * 1.5, 0.7, 1), ln, 0.06, fm[k % 2 + 1], "head", bend=(0, 0.3, -0.1), sides=5, parts=4)
		_flame(b, (x, -0.43, H + 0.45), (x * 1.5, 0.7, 1), ln * 0.55, 0.035, fm[3] if not phoenix else white, "head", bend=(0, 0.3, -0.1), sides=5)
	# the wings, spread: coverts along the arm, long primaries fanning off the tip, each burning at its end
	span = 1.25 if phoenix else 1.0
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		wing, tip = f"wing_{side}", f"tip_{side}"
		up = (0, 0, 1)
		b.seg((0.14 * s, -0.06, H + 0.1), (0.86 * s, 0.0, H + 0.12), 0.07, 0.05, body, wing, sides=6)   # the leading edge
		for k in range(6):   # inner flight feathers
			x = (0.2 + 0.12 * k) * s
			ln = 0.46 + 0.04 * k
			d = Vector((0.1 * s, 1, -0.05)).normalized()
			_oblob(b, (0.13, ln, 0.03), (x, -0.02 + ln * 0.5, H + 0.1), d, up, fm[k % 2], wing, segs=(6, 4))
			_oblob(b, (0.11, ln * 0.35, 0.035), (x, -0.02 + ln * 0.88, H + 0.09), d, up, fm[2 + k % 2], wing, segs=(6, 4))
		for k in range(4):   # coverts over them
			x = (0.24 + 0.16 * k) * s
			_oblob(b, (0.16, 0.26, 0.04), (x, 0.06, H + 0.14), (0.1 * s, 1, 0), up, back if k % 2 else body, wing, segs=(6, 4))
		for k in range(6):   # primaries fanning from the wrist
			a = math.radians(-12 + 17 * k)
			d = Vector((math.cos(a) * s, math.sin(a), -0.03)).normalized()
			ln = (0.62 + 0.08 * (k < 3)) * span
			base = Vector((0.86 * s, 0.02, H + 0.12))
			_oblob(b, (0.14, ln, 0.03), tuple(base + d * ln * 0.5), d, up, fm[1 + k % 2], tip, segs=(6, 4))
			_flame(b, tuple(base + d * ln * 0.78), tuple(d + Vector((0, 0.3, 0.1))), ln * 0.45, 0.06, fm[3] if k % 2 else fm[2], tip,
				   bend=(0, 0.1, 0.1), sides=5)
		_oblob(b, (0.18, 0.3, 0.05), (0.9 * s, 0.06, H + 0.14), (s, 0.3, 0), up, body, tip, segs=(6, 4))
	# the tail: long streaming plumes, flame at their ends
	plumes = 5 if phoenix else 3
	length = 2.0 if phoenix else 1.2
	for k in range(plumes):
		c = k - (plumes - 1) / 2
		yaw = math.radians(c * 11)
		d = Vector((math.sin(yaw), math.cos(yaw), -0.3 - 0.06 * abs(c))).normalized()
		a = Vector((0, 0.32, H - 0.04))
		split = 0.58 if not phoenix else 0.68
		mid = a + d * split
		end = a + d * length * (1 - 0.1 * abs(c))
		b.seg(tuple(a), tuple(mid), 0.05, 0.04, fm[1], "tail1", sides=5)
		_oblob(b, (0.14, split, 0.03), tuple(a + d * split * 0.5), d, (0, 0, 1), fm[k % 2], "tail1", segs=(6, 4))
		b.seg(tuple(mid), tuple(end), 0.035, 0.02, fm[2], "tail2", sides=5)
		_oblob(b, (0.1, (end - mid).length, 0.025), tuple((mid + end) / 2), d, (0, 0, 1), fm[1 + k % 2], "tail2", segs=(6, 4))
		_flame(b, tuple(end - d * 0.1), tuple(d + Vector((0, 0, 0.35))), 0.34 if not phoenix else 0.46, 0.08, fm[3], "tail2", bend=(0, 0, 0.2), sides=5)
		if phoenix:   # a flame eye at each plume's end
			b.blob((0.12, 0.12, 0.1), tuple(end), white, "tail2", segs=(6, 4))
	# talons tucked under
	for s in (1, -1):
		b.seg((0.08 * s, 0.04, H - 0.16), (0.08 * s, 0.12, H - 0.36), 0.035, 0.025, beak, "legs", sides=5)
		for k in (-1, 0, 1):
			root_ = Vector((0.08 * s + 0.03 * k, 0.12, H - 0.36))
			b.seg(tuple(root_), tuple(root_ + Vector((0.01 * k, -0.08, -0.04))), 0.018, 0.0, talon, "legs", sides=4)
	arm = b.build()

	def beat(t, cycles, amp=38, lift=0.0):
		"""Wings beat by roll, the tips lagging behind the arms."""
		f = amp * wave(t, cycles) + lift
		g = amp * 0.6 * wave(t, cycles, -0.12) + lift * 0.4
		return {"wing_l": {"rot": (0, f, 0)}, "wing_r": {"rot": (0, -f, 0)}, "tip_l": {"rot": (0, g, 0)}, "tip_r": {"rot": (0, -g, 0)}}

	def tail(t, cycles, amp=6):
		return {"tail1": {"rot": (amp * wave(t, cycles, 0.2), 0, 3 * wave(t, 1))}, "tail2": {"rot": (amp * 1.3 * wave(t, cycles, 0.05), 0, 4 * wave(t, 1, -0.2))}}

	def idle(t):   # hangs in the air on slow, deep beats, bobbing with each
		return merge({"root": {"loc": (0, 0, -0.08 * wave(t, 3, 0.1))}, "body": {"rot": (4 * wave(t, 3, 0.3), 0, 0)},
					  "head": {"rot": (-4 * wave(t, 3, 0.3), 0, 12 * wave(t, 1))}, "legs": {"rot": (6 * wave(t, 3), 0, 0)}},
					 beat(t, 3, 40, 6), tail(t, 3))

	def walk(t):   # flies forward nose-down
		return merge({"root": {"loc": (0, 0, -0.06 * wave(t, 2, 0.1)), "rot": (-12, 0, 0)}, "head": {"rot": (10, 0, 0)},
					  "legs": {"rot": (-30, 0, 0)}}, beat(t, 2, 34, 4), tail(t, 2, 4))

	def run(t):
		return merge({"root": {"loc": (0, 0, -0.05 * wave(t, 2, 0.1)), "rot": (-22, 0, 0)}, "head": {"rot": (18, 0, 0)},
					  "legs": {"rot": (-50, 0, 0)}}, beat(t, 2, 44, 0), tail(t, 2, 3))

	def attack(t):   # rears up with wings high, then dives in raking with its talons
		rear = seq(t, [(0, 0), (0.35, 1), (0.55, -0.6), (0.75, -0.4), (1, 0)])
		dive = seq(t, [(0, 0), (0.35, -0.12), (0.55, 0.5), (0.75, 0.4), (1, 0)])
		wings = seq(t, [(0, 0), (0.35, 50), (0.55, -40), (0.75, -20), (1, 0)])
		return merge({"root": {"loc": (0, dive, 0.12 * rear - 0.25 * max(0.0, -rear)), "rot": (28 * rear, 0, 0)},
					  "head": {"rot": (-20 * rear + seq(t, [(0.45, 0), (0.6, -16), (0.8, 0)]), 0, 0)},
					  "legs": {"rot": (seq(t, [(0, 0), (0.35, 20), (0.55, 80), (0.75, 60), (1, 0)]), 0, 0)},
					  "wing_l": {"rot": (0, wings, 0)}, "wing_r": {"rot": (0, -wings, 0)},
					  "tip_l": {"rot": (0, wings * 0.5, 0)}, "tip_r": {"rot": (0, -wings * 0.5, 0)}}, tail(t, 1, 14))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.2 * k, 0.1 * k), "rot": (20 * k, 14 * k, 0)}, "head": {"rot": (16 * k, 0, 20 * k)}},
					 beat(t, 2, 30, 30 * k), tail(t, 2, 10))

	def death(t):   # the wings fail; it tumbles to the ground and lies with one wing spread
		f = seq(t, [(0.1, 0), (0.7, 1)])
		g = seq(t, [(0.5, 0), (0.95, 1)])
		flap = 1 - seq(t, [(0.1, 0), (0.5, 1)])
		return merge({"root": {"loc": (0, 0.1 * f, -(H - 0.28) * f + 0.08 * math.sin(math.pi * f)), "rot": (-20 * f, 70 * g, 0)},
					  "neck": {"rot": (-30 * g, 0, 20 * g)}, "head": {"rot": (-20 * g, 0, 30 * g)}, "legs": {"rot": (50 * g, 0, 0)},
					  "wing_l": {"rot": (0, 30 * flap * wave(t, 3) - 55 * g, 0)}, "wing_r": {"rot": (0, -30 * flap * wave(t, 3) - 65 * g, 0)},
					  "tip_l": {"rot": (0, -15 * g, 0)}, "tip_r": {"rot": (0, -8 * g, 0)},
					  "tail1": {"rot": (10 * g, 0, 20 * g)}, "tail2": {"rot": (6 * g, 0, 14 * g)}})

	clip(arm, "idle", 2.0, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_phoenix():
	return build_firebird("phoenix", True)


# The Burn: registered here, beside its builders
BODIES.update({"ember_giant_body": (KAYKIT + "Barbarian.glb", "ember_giant_texture", EMBER_GIANT_CELLS, None),
			   "ember_thane_body": (KAYKIT + "Barbarian.glb", "ember_thane_texture", EMBER_THANE_CELLS, None)})
ATTACHMENTS.update({"ember_giant_head": build_ember_giant_head, "ember_thane_head": build_ember_thane_head,
					"ember_giant_chest": build_ember_giant_chest, "ember_thane_chest": build_ember_thane_chest,
					"ember_giant_apron": build_ember_giant_apron, "ember_thane_apron": build_ember_thane_apron,
					"ember_hammer": build_ember_hammer, "ember_greathammer": build_ember_greathammer})
for _pre, _thane in (("ember_giant", False), ("ember_thane", True)):
	for _s, _side in ((1, "l"), (-1, "r")):
		ATTACHMENTS[f"{_pre}_arm_{_side}"] = (lambda n, s, t: lambda: _ember_giant_arm(n, s, t))(f"{_pre}_arm_{_side}", _s, _thane)
		ATTACHMENTS[f"{_pre}_bracer_{_side}"] = (lambda n, s, t: lambda: _ember_giant_bracer(n, s, t))(f"{_pre}_bracer_{_side}", _s, _thane)
CREATURES.update({"firehound": build_firehound, "firehound_alpha": build_firehound_alpha, "ash_wolf": build_ash_wolf,
				  "fire_imp": build_fire_imp, "imp_lord": build_imp_lord, "smoke_spirit": build_smoke_spirit,
				  "firebird": build_firebird, "phoenix": build_phoenix})
# ================================================================ end of The Burn


# ================================================================ Dawnwatch / Mirror Flats (the Dawnstair, 20-24)
# Dawnwatch, the Dawn-Tusk's besieged fortress on a snowy ridge: the Stonebrow ogres (a repainted KayKit
# barbarian, head hidden, with bolt-ons in its mesh space), rocs, wyverns, snow and storm spirits, the
# avalanche elemental and the fortress's ghostly garrison (a repainted Knight made see-through and aglow by
# BODY_FINISH). Mirror Flats, a salt flat under a sheet of water: mirror images (a chrome Rogue), the
# Reflection, mirage wisps, salt crabs, brine swarms, the Duneskiff nomads, salt waders and sky rays.
# Several are older frames recolored (`_dw_recolor`) and given parts of their own (`_dw_extend`).

def _dw_set(m, hex_, rough=None, emit=None):
	"""Repaints one Blender material in place (base color, preview color and, when lit, its glow)."""
	rgb = tuple(int(hex_[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
	lin = tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb) + (1.0,)
	bsdf = m.node_tree.nodes["Principled BSDF"]
	bsdf.inputs["Base Color"].default_value = lin
	m.diffuse_color = rgb + (m.diffuse_color[3],)
	if rough is not None:
		bsdf.inputs["Roughness"].default_value = rough
	if emit is not None:
		bsdf.inputs["Emission Color"].default_value = lin
		bsdf.inputs["Emission Strength"].default_value = emit
	elif bsdf.inputs["Emission Strength"].default_value > 0.0:
		bsdf.inputs["Emission Color"].default_value = lin


def _dw_recolor(arm, old, new, colors):
	"""Renames an older builder's rig and materials (`old`_x -> `new`_x) and repaints the ones listed:
	{suffix: hex | (hex, rough, emit)}."""
	for m in list(bpy.data.materials):
		if not m.name.startswith(old + "_"):
			continue
		suf = m.name[len(old) + 1:]
		c = colors.get(suf)
		if c is not None:
			_dw_set(m, *(c if isinstance(c, tuple) else (c,)))
		m.name = f"{new}_{suf}"
	arm.name = new
	for ch in arm.children:
		ch.name = f"{new}_mesh"
	return arm


def _dw_extend(arm, fn):
	"""Adds parts to a finished creature: fn(b) fills a Builder (parts bound to the rig's bone names),
	then they're joined into its mesh so the armature carries them."""
	b = Builder(arm.name + "_extra")
	fn(b)
	if not b.parts:
		return arm
	body = arm.children[0]
	bpy.ops.object.select_all(action="DESELECT")
	for p in b.parts:
		p.select_set(True)
	body.select_set(True)
	bpy.context.view_layer.objects.active = body
	bpy.ops.object.join()
	return arm


def _dw_mat(name, hex_, rough=0.8, emit=0.0, metal=0.0, alpha=1.0):
	if alpha < 1.0:
		return glass_material(name, hex_, alpha, rough, emit)
	if metal > 0.0:
		return metal_material(name, hex_, rough, metal, emit)
	return material(name, hex_, rough, emit)


# ---------------------------------------------------------------- the Stonebrow ogres (KayKit mesh space)

# the barbarian as a Stonebrow ogre: skin (0,0) (1,3) (3,1) gray-green, trousers (7,1) and vest (7,0) hide,
# fur trim (2,1), boots (3,2) dark iron, leather (6,0) (6,1) (5,1), iron (3,0), hand wraps (7,2)
def _stonebrow_cells(skin, vest, trim, iron=("7a7c7e", "2e3032")):
	cells = {c: skin for c in ((0, 0), (1, 3), (3, 1))}
	cells.update({(7, 1): ("7a6248", "30241a"), (3, 2): ("5a5c5e", "1e2022"), (7, 0): vest, (2, 1): trim,
				  (6, 0): ("5a4632", "22180e"), (6, 1): ("5a4632", "22180e"), (5, 1): ("5a4632", "22180e"),
				  (3, 0): iron, (7, 2): ("6a5a44", "2a2016")})
	return cells


STONEBROW_CELLS = _stonebrow_cells(("8e9c7a", "3e4a34"), ("8a7a5e", "3a3022"), ("a09070", "4a4030"))
STONEBROW_SHAMAN_CELLS = _stonebrow_cells(("8a9a80", "3a4838"), ("d0c4a4", "6a5e46"), ("4a3e30", "1a140e"))
STONEBROW_WARLORD_CELLS = _stonebrow_cells(("74866a", "2a3624"), ("6a2a1e", "240a06"), ("3a3430", "121010"),
										   iron=("5a5c60", "1a1c1e"))


def ogre_materials(kind="ogre"):
	skin = {"ogre": ("8e9c7a", "6e7c5c", "a8b492"), "shaman": ("8a9a80", "6a7a60", "a4b29a"),
			"warlord": ("74866a", "56684c", "8e9e82")}[kind]
	return {
		"skin": material(f"sb_{kind}_skin", skin[0], 0.9),
		"skin_d": material(f"sb_{kind}_skin_dark", skin[1], 0.9),
		"skin_l": material(f"sb_{kind}_skin_light", skin[2], 0.85),
		"brow": material(f"sb_{kind}_brow", "8a8a80", 0.95),       # the stony brow the warband is named for
		"brow_d": material(f"sb_{kind}_brow_dark", "5e5e56", 0.95),
		"eye": material(f"sb_{kind}_eye", "f0c040", 0.3, emit=1.2),
		"dark": material(f"sb_{kind}_dark", "1a1612", 0.9),
		"tusk": material(f"sb_{kind}_tusk", "e8dcbc", 0.5),
		"paint": material(f"sb_{kind}_paint", "b8321e", 0.8),       # war paint, red ochre
		"paint_w": material(f"sb_{kind}_paint_white", "e8e4d8", 0.8),
		"hair": material(f"sb_{kind}_hair", "2a2420", 0.95),
		"iron": metal_material(f"sb_{kind}_iron", "5a5a5c", 0.55, 0.5),
		"iron_d": metal_material(f"sb_{kind}_iron_dark", "34343a", 0.6, 0.5),
		"iron_l": metal_material(f"sb_{kind}_iron_light", "8a8a8e", 0.45, 0.5),
		"rust": material(f"sb_{kind}_rust", "7a4a2a", 0.9),
		"hide": material(f"sb_{kind}_hide", "8a6a48", 0.9),
		"hide_d": material(f"sb_{kind}_hide_dark", "5a4430", 0.9),
		"fur": material(f"sb_{kind}_fur", "6a5a48", 0.95),
		"fur_l": material(f"sb_{kind}_fur_light", "b0a48a", 0.95),
		"leather": material(f"sb_{kind}_leather", "4a3424", 0.9),
		"bone": material(f"sb_{kind}_bone", "e6dcc0", 0.6),
		"bone_d": material(f"sb_{kind}_bone_dark", "a89878", 0.7),
		"feather": material(f"sb_{kind}_feather", "3a2a22", 0.9),
		"feather_r": material(f"sb_{kind}_feather_red", "a8321e", 0.9),
		"cloth": material(f"sb_{kind}_cloth", "8a2418", 0.9),
		"cloth_d": material(f"sb_{kind}_cloth_dark", "4a120c", 0.9),
		"glow": material(f"sb_{kind}_glow", "8ae0ff", 0.3, emit=2.5),
	}


def _ogre_face(b, m, kind):
	"""A big bald ogre head: a heavy skull, a brow like a stone shelf, little deep eyes, a flat nose, an
	underbite with two tusks, ears like cabbage leaves, and war paint across the eyes."""
	sk, dk = m["skin"], m["skin_d"]
	b.blob((0.54, 0.54, 0.56), (0, -0.0, 1.6), sk, "x", segs=(12, 9))                            # the skull
	b.blob((0.62, 0.52, 0.34), (0, -0.1, 1.4), sk, "x", segs=(12, 7))                            # jowls
	b.blob((0.6, 0.42, 0.26), (0, -0.16, 1.34), m["skin_l"], "x", segs=(10, 7))                   # the underbite jaw
	b.blob((0.44, 0.1, 0.08), (0, -0.36, 1.4), dk, "x", segs=(8, 4))                             # a thick lower lip
	# the stone brow: a heavy shelf with slabs of gray stone grown into it
	b.blob((0.66, 0.26, 0.18), (0, -0.24, 1.7), m["brow"], "x", rot=(-8, 0, 0), segs=(10, 6))
	for x, z, w in ((-0.18, 1.74, 0.16), (0.02, 1.76, 0.2), (0.2, 1.73, 0.15)):
		_box(b, (w, 0.1, 0.08), (x, -0.34, z), m["brow_d"], rot=(-12, (x * 60), 0))
	b.seg((0, -0.3, 1.64), (0, -0.4, 1.5), 0.06, 0.09, dk, "x", sides=6)                           # a flat, broken nose
	for s in (1, -1):
		b.blob((0.07, 0.06, 0.05), (0.05 * s, -0.42, 1.5), m["dark"], "x", segs=(6, 4))             # nostrils
		b.blob((0.13, 0.06, 0.08), (0.14 * s, -0.3, 1.62), m["dark"], "x", segs=(8, 5))             # sunken sockets
		b.blob((0.05, 0.03, 0.04), (0.14 * s, -0.33, 1.625), m["eye"], "x", segs=(6, 4))
		b.seg((0.15 * s, -0.36, 1.4), (0.19 * s, -0.4, 1.58), 0.045, 0.012, m["tusk"], "x", sides=6)   # tusks
		b.blob((0.1, 0.2, 0.24), (0.3 * s, 0.0, 1.58), sk, "x", rot=(0, 20 * s, 0), segs=(8, 6))    # ears
		b.blob((0.05, 0.12, 0.14), (0.33 * s, -0.02, 1.58), dk, "x", rot=(0, 20 * s, 0), segs=(6, 4))
		b.blob((0.18, 0.16, 0.16), (0.2 * s, -0.24, 1.46), sk, "x", segs=(8, 5))                  # heavy cheeks
		# war paint: a band of red across the eyes and three white stripes down each cheek
		_box(b, (0.2, 0.04, 0.06), (0.15 * s, -0.33, 1.575), m["paint"], rot=(0, 0, 18 * s))
		for k in range(2 if kind != "shaman" else 3):
			b.seg((0.18 * s + 0.04 * k * s, -0.31 + 0.02 * k, 1.52), (0.2 * s + 0.04 * k * s, -0.28 + 0.02 * k, 1.4),
				  0.012, 0.012, m["paint_w"], "x", sides=4)
	if kind == "ogre":   # a topknot tied with a strip of hide
		b.blob((0.18, 0.18, 0.12), (0, 0.1, 1.9), m["hair"], "x", segs=(8, 5))
		b.seg((0, 0.12, 1.92), (0, 0.24, 1.98), 0.07, 0.04, m["hair"], "x", sides=6)
		b.seg((0, 0.24, 1.98), (0, 0.36, 1.82), 0.04, 0.02, m["hair"], "x", sides=5)
		_wrap(b, (0, 0.14, 1.95), (0.06, 0.06), 0.05, 0.02, m["hide_d"], sides=8)


def _horned_helm(b, m):
	"""The warlord's horned iron helm: a riveted dome, a nose guard, cheek plates and two great horns."""
	_shell(b, (0.62, 0.62, 0.62), (0, 0.0, 1.66), m["iron"], lambda d: d.z > -0.05 or (d.y > -0.3 and d.z > -0.5))
	_wrap(b, (0, 0.0, 1.66), (0.315, 0.315), 0.07, 0.03, m["iron_d"], sides=18)
	b.seg((0, -0.28, 1.95), (0, -0.33, 1.64), 0.02, 0.02, m["iron_l"], "x", sides=4)                 # the crest ridge
	_box(b, (0.07, 0.05, 0.22), (0, -0.37, 1.56), m["iron_d"])                                    # the nose guard
	for k in range(10):
		a = 2 * math.pi * k / 10
		b.blob((0.035, 0.035, 0.035), (0.32 * math.cos(a), 0.32 * math.sin(a), 1.66), m["iron_l"], "x", segs=(4, 3))
	for s in (1, -1):
		_slab(b, [(0.26 * s, -0.2, 1.6), (0.3 * s, 0.02, 1.62), (0.3 * s, 0.0, 1.38), (0.22 * s, -0.2, 1.42)], 0.03, m["iron_d"])
		# a horn: sweeping out, up and forward from the helm's side
		pts = [Vector((0.3 * s, -0.02, 1.8)), Vector((0.5 * s, 0.02, 1.9)), Vector((0.62 * s, -0.02, 2.1)),
			   Vector((0.62 * s, -0.12, 2.3)), Vector((0.55 * s, -0.2, 2.42))]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			r0, r1 = 0.09 * (1 - k / 4) + 0.01, 0.09 * (1 - (k + 1) / 4) + 0.005
			b.seg(tuple(p), tuple(q), r0, r1, m["bone"] if k < 3 else m["bone_d"], "x", sides=8)
			b.blob((r0 * 2.1, r0 * 2.1, r0 * 2.1), tuple(p), m["bone"], "x", segs=(6, 4))
		b.seg((0.28 * s, -0.02, 1.8), (0.4 * s, 0.0, 1.85), 0.11, 0.1, m["iron_d"], "x", sides=8)    # the horn's iron socket


def _skull_headdress(b, m):
	"""The shaman's headdress: the skull of some horned beast worn as a cap, its horns curling back,
	feathers and bone beads hanging round it."""
	b.blob((0.6, 0.62, 0.36), (0, -0.04, 1.84), m["bone"], "x", segs=(12, 8))                       # the cranium, worn like a cap
	b.blob((0.36, 0.32, 0.16), (0, -0.34, 1.86), m["bone"], "x", rot=(-20, 0, 0), segs=(10, 6))     # the snout, over the brow
	b.seg((0, -0.44, 1.84), (0, -0.56, 1.76), 0.1, 0.06, m["bone_d"], "x", sides=6)
	for s in (1, -1):
		b.blob((0.1, 0.06, 0.08), (0.11 * s, -0.4, 1.9), m["dark"], "x", segs=(6, 4))                # empty sockets
		b.blob((0.04, 0.02, 0.04), (0.11 * s, -0.43, 1.9), m["glow"], "x", segs=(5, 3))              # a spirit-light in each
		pts = [Vector((0.24 * s, -0.08, 1.94)), Vector((0.38 * s, 0.06, 2.06)), Vector((0.42 * s, 0.26, 2.0)),
			   Vector((0.36 * s, 0.34, 1.84)), Vector((0.3 * s, 0.24, 1.76))]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(tuple(p), tuple(q), 0.07 * (1 - k / 5) + 0.01, 0.07 * (1 - (k + 1) / 5) + 0.008, m["bone_d"], "x", sides=7)
		for k in range(3):   # feathers and bead strings off the sides
			base = Vector((0.3 * s, 0.1 - 0.12 * k, 1.8))
			b.seg(tuple(base), tuple(base + Vector((0.06 * s, 0.04, -0.3 - 0.06 * k))), 0.012, 0.01, m["leather"], "x", sides=4)
			tip = base + Vector((0.06 * s, 0.04, -0.3 - 0.06 * k))
			_oblob(b, (0.05, 0.26, 0.015), tuple(tip + Vector((0, 0, -0.1))), (0, 0.1, -1), (s, 0, 0),
				   m["feather_r"] if k == 1 else m["feather"], "x", segs=(6, 4))
			b.blob((0.05, 0.05, 0.05), tuple(base + Vector((0.03 * s, 0.02, -0.14))), m["bone"], "x", segs=(5, 4))


def _ogre_head(name, kind):
	b = Builder(name)
	m = ogre_materials(kind)
	_ogre_face(b, m, kind)
	if kind == "warlord":
		_horned_helm(b, m)
	elif kind == "shaman":
		_skull_headdress(b, m)
	return b.build_static()


def _ogre_chest(name, kind):
	"""Ogre bulk and armor on the chest bone. The soldier: a crude riveted iron breastplate on hide straps
	and a fur mantle. The shaman: a fur mantle and a necklace of bones, teeth and pouches. The warlord:
	a heavy plate with spiked pauldrons and a gorget, and a trophy banner on a pole across his back."""
	import random
	rng = random.Random({"ogre": 601, "shaman": 603, "warlord": 605}[kind])
	m = ogre_materials(kind)
	b = Builder(name)
	sk = m["skin"]
	b.seg((0, 0.0, 1.22), (0, -0.04, 1.42), 0.2, 0.18, sk, "x", sides=10)                         # a bull neck
	b.blob((0.86, 0.56, 0.46), (0, -0.07, 1.16), sk, "x", segs=(12, 8))                           # great slabs of chest
	b.blob((0.82, 0.5, 0.52), (0, 0.12, 1.2), sk, "x", segs=(12, 8))                              # a hunched back
	for s in (1, -1):
		b.blob((0.42, 0.44, 0.38), (0.35 * s, 0.02, 1.28), sk, "x", segs=(10, 7))                 # shoulders
	fur = (m["fur"], m["fur_l"])
	if kind in ("ogre", "shaman"):   # a mantle of shaggy hide over the shoulders
		_shell(b, (1.02, 0.78, 0.6), (0, 0.04, 1.26), m["fur"], lambda d: d.z > 0.1)
		for k in range(16):
			a = 2 * math.pi * k / 16
			p = Vector((0.5 * math.cos(a), 0.04 + 0.38 * math.sin(a), 1.3))
			b.seg(tuple(p), tuple(p + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), -0.14 - 0.06 * (k % 3)))), 0.05, 0.01,
				  fur[k % 2], "x", sides=4)
	if kind == "ogre":
		# a crude breastplate: two hammered plates riveted together, lashed on with hide straps
		_shell(b, (0.94, 0.7, 0.54), (0, -0.07, 1.14), m["iron"], lambda d: d.y < -0.5 and abs(d.x) < 0.5 and d.z < 0.55)
		b.seg((0, -0.43, 0.96), (0, -0.43, 1.36), 0.018, 0.018, m["iron_d"], "x", sides=4)             # the seam
		for z in (1.0, 1.12, 1.24):
			for x in (-0.05, 0.05):
				b.blob((0.035, 0.03, 0.035), (x, -0.43, z), m["iron_l"], "x", segs=(4, 3))
		for x, z, r in ((-0.2, 1.06, 0.04), (0.18, 1.22, 0.035)):   # rust and dents
			b.blob((r * 2.4, 0.03, r * 1.8), (x, -0.41, z), m["rust"], "x", segs=(6, 4))
		for s in (1, -1):
			b.seg((0.2 * s, -0.4, 1.3), (0.3 * s, -0.2, 1.46), 0.03, 0.03, m["hide_d"], "x", sides=4)
			b.seg((0.3 * s, -0.2, 1.46), (0.28 * s, 0.3, 1.34), 0.03, 0.03, m["hide_d"], "x", sides=4)
			_box(b, (0.08, 0.04, 0.06), (0.2 * s, -0.42, 1.3), m["iron_l"])
		b.blob((0.14, 0.04, 0.12), (0, -0.44, 1.2), m["paint"], "x", segs=(6, 4))                    # a painted handprint
	elif kind == "shaman":
		# a necklace of bones, fangs and small skulls, and pouches hanging on thongs
		for k in range(11):
			a = math.radians(200 + 14 * k)
			p = Vector((0.36 * math.cos(a), -0.02 + 0.36 * math.sin(a) * 1.05, 1.36 - 0.12 * math.sin(math.pi * k / 10)))
			if k % 5 == 2:
				b.blob((0.1, 0.1, 0.1), tuple(p + Vector((0, -0.02, -0.06))), m["bone"], "x", segs=(8, 6))
				for s in (1, -1):
					b.blob((0.025, 0.02, 0.025), tuple(p + Vector((0.025 * s, -0.07, -0.05))), m["dark"], "x", segs=(4, 3))
			else:
				b.seg(tuple(p), tuple(p + Vector((0, -0.02, -0.14 - 0.04 * (k % 2)))), 0.025, 0.006, m["bone"] if k % 2 else m["tusk"], "x", sides=5)
		for s in (1, -1):
			b.blob((0.14, 0.12, 0.16), (0.3 * s, -0.3, 0.92), m["hide"], "x", segs=(8, 6))
			b.seg((0.3 * s, -0.3, 1.0), (0.26 * s, -0.36, 1.22), 0.012, 0.012, m["leather"], "x", sides=4)
		b.seg((-0.38, -0.3, 1.36), (0.38, -0.3, 1.36), 0.01, 0.01, m["leather"], "x", sides=4)
	else:   # the warlord
		_shell(b, (0.98, 0.74, 0.6), (0, -0.05, 1.14), m["iron_d"], lambda d: d.y < -0.35 and d.z < 0.6)
		_shell(b, (0.92, 0.66, 0.5), (0, -0.07, 1.1), m["iron"], lambda d: d.y < -0.55 and abs(d.x) < 0.45 and d.z < 0.4)
		b.blob((0.2, 0.06, 0.2), (0, -0.44, 1.18), m["bone"], "x", segs=(8, 6))                      # a skull boss
		for s in (1, -1):
			b.blob((0.05, 0.02, 0.05), (0.04 * s, -0.47, 1.2), m["dark"], "x", segs=(4, 3))
		_wrap(b, (0, -0.02, 1.36), (0.28, 0.26), 0.1, 0.04, m["iron"], sides=16)                     # the gorget
		for s in (1, -1):   # pauldrons in overlapping plates, each with spikes
			_shell(b, (0.56, 0.58, 0.4), (0.42 * s, 0.02, 1.36), m["iron"], lambda d: d.z > -0.1)
			_shell(b, (0.5, 0.52, 0.34), (0.5 * s, 0.02, 1.28), m["iron_d"], lambda d: d.z > 0.0 and d.x * s > 0.3)
			for k in range(3):
				p = Vector((0.42 * s + 0.06 * s * k, -0.12 + 0.12 * k, 1.56 - 0.04 * k))
				b.seg(tuple(p), tuple(p + Vector((0.1 * s, 0.0, 0.2))), 0.05, 0.0, m["iron_l"], "x", sides=5)
			b.seg((0.3 * s, -0.38, 1.3), (0.3 * s, 0.34, 1.3), 0.03, 0.03, m["hide_d"], "x", sides=4)
		# the trophy banner: a pole slung across the back, a crossbar, a hide banner painted red with a
		# hand, skulls and a scalp of feathers on top
		pole = m["leather"]
		start = len(b.parts)
		b.seg((0.18, 0.36, 0.7), (0.24, 0.36, 2.7), 0.035, 0.03, pole, "x", sides=6)
		b.seg((-0.2, 0.37, 2.52), (0.66, 0.37, 2.52), 0.025, 0.025, pole, "x", sides=5)
		top = Vector((0.24, 0.37, 2.7))
		b.blob((0.18, 0.18, 0.2), tuple(top + Vector((0, -0.02, 0.08))), m["bone"], "x", segs=(8, 6))  # a skull on the tip
		for s in (1, -1):
			b.blob((0.045, 0.03, 0.04), tuple(top + Vector((0.04 * s, -0.1, 0.1))), m["dark"], "x", segs=(4, 3))
			b.seg(tuple(top + Vector((0.08 * s, 0, 0.12))), tuple(top + Vector((0.2 * s, 0.02, 0.28))), 0.03, 0.005, m["bone_d"], "x", sides=5)
		cloth = m["cloth"]
		pts = [(-0.18, 0.38, 2.5), (0.64, 0.38, 2.5), (0.6, 0.38, 1.9), (0.44, 0.38, 1.98), (0.3, 0.38, 1.76),
			   (0.1, 0.38, 1.96), (-0.14, 0.38, 1.84)]
		_slab(b, [pts[0], pts[1], pts[2], pts[3]], 0.03, m["hide"])
		_slab(b, [pts[0], pts[3], pts[4], pts[5]], 0.03, m["hide"])
		_slab(b, [pts[0], pts[5], pts[6]], 0.03, m["hide"])
		b.blob((0.26, 0.03, 0.3), (0.22, 0.4, 2.2), cloth, "x", segs=(8, 6))                          # a red hand painted on it
		for k, x in enumerate((0.12, 0.19, 0.26, 0.33)):
			b.seg((x, 0.405, 2.3), (x + 0.01 * (k - 1.5), 0.405, 2.44), 0.025, 0.02, cloth, "x", sides=4)
		for k, x in enumerate((-0.12, 0.08, 0.34, 0.56)):   # trophies hung from the crossbar
			ln = 0.2 + 0.1 * (k % 2)
			b.seg((x, 0.34, 2.5), (x, 0.34, 2.5 - ln), 0.01, 0.01, pole, "x", sides=4)
			if k % 2:
				b.blob((0.1, 0.1, 0.1), (x, 0.33, 2.44 - ln), m["bone"], "x", segs=(6, 5))
			else:
				b.seg((x, 0.33, 2.5 - ln), (x, 0.33, 2.3 - ln), 0.04, 0.005, m["tusk"], "x", sides=5)
		for k in range(5):
			b.seg((0.24, 0.37, 2.62), (0.24 + 0.08 * (k - 2), 0.44, 2.46 - 0.04 * abs(k - 2)), 0.02, 0.006,
				  m["feather_r"] if k % 2 else m["feather"], "x", sides=4)
		for p in b.parts[start:]:   # all of it a little lower, so it clears the helm's horns without towering
			p.data.transform(Matrix.Translation((0, 0.02, -0.28)))
	return b.build_static()


def _ogre_belly(name, kind):
	"""A pot belly hanging over the belt, a wide hide belt with a buckle, and flaps of hide over the hips."""
	m = ogre_materials(kind)
	b = Builder(name)
	b.blob((0.8, 0.66, 0.54), (0, -0.1, 0.84), m["skin"], "x", segs=(12, 9))
	b.blob((0.5, 0.2, 0.36), (0, -0.37, 0.86), m["skin_l"], "x", segs=(10, 6))
	b.blob((0.05, 0.03, 0.05), (0, -0.46, 0.84), m["skin_d"], "x", segs=(5, 3))
	_wrap(b, (0, -0.04, 0.66), (0.44, 0.4), 0.14, 0.04, m["leather"], sides=18)
	if kind == "warlord":
		b.blob((0.24, 0.06, 0.18), (0, -0.46, 0.66), m["bone"], "x", segs=(8, 5))
		for s in (1, -1):
			b.seg((0.04 * s, -0.5, 0.66), (0.1 * s, -0.52, 0.6), 0.02, 0.004, m["tusk"], "x", sides=4)
	else:
		_box(b, (0.16, 0.05, 0.14), (0, -0.46, 0.66), m["iron_l"])
	for k in range(6):
		a = math.radians(210 + 24 * k) if k < 3 else math.radians(30 + 24 * (k - 3) + 90)
		c = Vector((0.46 * math.cos(a), -0.04 + 0.42 * math.sin(a), 0.6))
		w = 0.12
		t = Vector((-math.sin(a), math.cos(a), 0)) * w
		_slab(b, [tuple(c + t), tuple(c - t), tuple(c - t * 0.8 + Vector((0, 0, -0.34))), tuple(c + t * 0.6 + Vector((0, 0, -0.3)))],
			  0.03, m["hide"] if k % 2 else m["hide_d"])
	return b.build_static()


def _ogre_arm(name, s, kind):
	"""A thick upper arm (upperarm bone), with a spiked iron band on the warlord."""
	m = ogre_materials(kind)
	b = Builder(name)
	b.seg((0.2 * s, 0.0, 1.12), (0.47 * s, 0.01, 1.1), 0.16, 0.13, m["skin"], "x", sides=10)
	b.blob((0.24, 0.24, 0.24), (0.33 * s, -0.02, 1.14), m["skin_l"], "x", segs=(9, 6))
	if kind == "warlord":
		b.seg((0.36 * s, 0.01, 1.1), (0.44 * s, 0.01, 1.1), 0.16, 0.15, m["iron_d"], "x", sides=10)
		for k in range(4):
			a = 2 * math.pi * k / 4 + 0.4
			p = Vector((0.4 * s, 0.155 * math.cos(a), 1.1 + 0.155 * math.sin(a)))
			b.seg(tuple(p), tuple(p + Vector((0, 0.1 * math.cos(a), 0.1 * math.sin(a)))), 0.03, 0.0, m["iron_l"], "x", sides=4)
	else:
		b.seg((0.36 * s, 0.01, 1.1), (0.4 * s, 0.01, 1.1), 0.16, 0.16, m["hide_d"], "x", sides=10)   # a hide armband
	return b.build_static()


def _ogre_bracer(name, s, kind):
	"""A bracer of hide and iron on the forearm (lowerarm bone)."""
	m = ogre_materials(kind)
	b = Builder(name)
	b.seg((0.47 * s, 0.01, 1.1), (0.68 * s, 0.0, 1.1), 0.14, 0.13, m["hide"] if kind != "warlord" else m["iron"], "x", sides=10)
	for x in (0.5, 0.64):
		b.seg((x * s, 0.0, 1.1), ((x + 0.025) * s, 0.0, 1.1), 0.15, 0.15, m["leather"] if kind != "warlord" else m["iron_d"], "x", sides=10)
	if kind == "shaman":
		for k in range(3):
			b.blob((0.05, 0.05, 0.05), ((0.54 + 0.04 * k) * s, -0.14, 1.1), m["bone"], "x", segs=(5, 4))
	return b.build_static()


def _stonebrow_club(name, kind):
	"""Weapons in the KayKit weapons' frame (grip at the origin, up +Z). The club: a knotty log with
	stones and iron spikes driven into its head. The skull staff: a gnarled staff topped with a horned
	skull, feathers and a glowing charm."""
	b = Builder(name)
	m = ogre_materials("shaman" if kind == "staff" else "ogre")
	wood = material(f"{name}_wood", "6a4a2e", 0.9)
	wood_d = material(f"{name}_wood_dark", "3e2a1a", 0.9)
	if kind == "club":
		b.seg((0, 0, -0.14), (0, 0, 0.2), 0.04, 0.05, wood_d, "x", sides=7)
		b.seg((0, 0, -0.08), (0, 0, 0.14), 0.05, 0.05, m["leather"], "x", sides=7)
		b.seg((0, 0, 0.2), (0.02, 0, 0.78), 0.06, 0.12, wood, "x", sides=8)
		b.blob((0.26, 0.26, 0.24), (0.02, 0, 0.78), wood, "x", segs=(9, 7))
		import random
		rng = random.Random(611)
		for k in range(7):
			a = 2 * math.pi * k / 7
			z = 0.52 + 0.3 * (k % 3) / 2
			p = Vector((0.02 + 0.11 * math.cos(a), 0.11 * math.sin(a), z))
			out = Vector((math.cos(a), math.sin(a), 0.2)).normalized()
			if k % 2:
				b.seg(tuple(p), tuple(p + out * 0.12), 0.025, 0.0, m["iron_l"], "x", sides=4)
			else:
				_rock(b, (0.1, 0.1, 0.08), tuple(p + out * 0.02), m["brow"], "x", rng)
		return b.build_static()
	b.seg((0, 0, -0.5), (0.02, 0, 0.3), 0.03, 0.035, wood_d, "x", sides=6)
	b.seg((0.02, 0, 0.3), (-0.02, 0, 0.95), 0.035, 0.04, wood, "x", sides=6)
	b.blob((0.1, 0.1, 0.12), (0.0, 0, 0.44), wood_d, "x", segs=(6, 5))                              # a knot
	b.seg((0, 0, -0.1), (0, 0, 0.14), 0.045, 0.045, m["leather"], "x", sides=6)
	sc = Vector((-0.02, 0, 1.08))   # the skull, facing forward (-Y)
	b.blob((0.22, 0.24, 0.2), tuple(sc), m["bone"], "x", segs=(10, 7))
	b.blob((0.14, 0.16, 0.1), tuple(sc + Vector((0, -0.14, -0.04))), m["bone"], "x", segs=(8, 5))
	for s in (1, -1):
		b.blob((0.05, 0.04, 0.05), tuple(sc + Vector((0.05 * s, -0.11, 0.03))), m["glow"], "x", segs=(5, 4))
		pts = [sc + Vector((0.08 * s, 0.02, 0.08)), sc + Vector((0.2 * s, 0.06, 0.16)), sc + Vector((0.26 * s, 0.0, 0.3)),
			   sc + Vector((0.2 * s, -0.06, 0.38))]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(tuple(p), tuple(q), 0.035 - 0.009 * k, 0.03 - 0.009 * k, m["bone_d"], "x", sides=6)
		for k in range(2):
			base = sc + Vector((0.1 * s, 0.04, -0.08))
			b.seg(tuple(base), tuple(base + Vector((0.03 * s, 0.0, -0.18 - 0.08 * k))), 0.008, 0.008, m["leather"], "x", sides=4)
			_oblob(b, (0.04, 0.2, 0.012), tuple(base + Vector((0.04 * s, 0, -0.3 - 0.08 * k))), (0, 0, -1), (s, 0, 0),
				   m["feather_r"] if k else m["feather"], "x", segs=(6, 4))
	return b.build_static()


# ---------------------------------------------------------------- Dawnwatch's fallen garrison (Knight bodies)

# the Knight in pale gold and white, see-through and aglow (BODY_FINISH); the commander brighter gold
BODY_FINISH = {
	"fallen_sentinel_texture": {"alpha": 0.62, "emissive": [0.42, 0.36, 0.2]},
	"knight_commander_texture": {"alpha": 0.7, "emissive": [0.5, 0.4, 0.18]},
	# Mirror Flats: chrome, and glass that's nearly chrome
	"mirror_image_texture": {"metallicFactor": 0.55, "roughnessFactor": 0.14, "emissive": [0.16, 0.18, 0.22]},
	"the_reflection_texture": {"metallicFactor": 0.5, "roughnessFactor": 0.08, "alpha": 0.82, "emissive": [0.2, 0.24, 0.3]},
}


def sentinel_materials(commander=False):
	p = "knight_commander" if commander else "fallen_sentinel"
	return {
		"cloth": glass_material(f"{p}_tabard", "f4ecd4", 0.62, 0.8, emit=0.5),
		"cloth_d": glass_material(f"{p}_tabard_dark", "d8c490", 0.62, 0.8, emit=0.4),
		"sun": glass_material(f"{p}_sun", "ffc848", 0.8, 0.4, emit=1.6),
		"saffron": glass_material(f"{p}_saffron", "f4a030", 0.7, 0.7, emit=0.9),
		"gold": glass_material(f"{p}_gold", "e8c060", 0.75, 0.3, emit=0.8),
		"eye": material(f"{p}_eye", "fff4c0", 0.1, emit=6.0),
		"pole": glass_material(f"{p}_pole", "c8b080", 0.7, 0.6, emit=0.4),
	}


def _sun_disc(b, center, normal, radius, m):
	_sun(b, center, normal, radius, m["sun"], m["gold"], count=10, ray_len=radius * 0.8, thick=0.03)


def build_sentinel_tabard():
	"""A ghostly tabard over the knight's armor: pale gold cloth torn at the hem, the Dawn-Tusk's sun on
	the chest."""
	import random
	rng = random.Random(621)
	m = sentinel_materials()
	b = Builder("sentinel_tabard")
	for side, y in ((-1, -0.36), (1, 0.34)):
		for k in range(5):
			x0 = -0.3 + 0.15 * k
			ln = rng.uniform(0.62, 0.86)
			_slab(b, [(x0, y + 0.01 * side, 1.34), (x0 + 0.15, y + 0.01 * side, 1.34), (x0 + 0.14, y + 0.08 * side, 1.34 - ln),
					  (x0 + 0.02, y + 0.08 * side, 1.34 - ln + rng.uniform(0.0, 0.1))], 0.02, m["cloth"] if k % 2 else m["cloth_d"])
	_sun_disc(b, (0, -0.4, 1.14), (0, -1, 0), 0.1, m)
	return b.build_static()


def build_sentinel_eyes():
	"""Two eyes burning in the empty helm (the Knight's head is hidden: the armor is hollow)."""
	m = sentinel_materials()
	b = Builder("sentinel_eyes")
	for s in (1, -1):
		b.blob((0.1, 0.03, 0.05), (0.13 * s, -0.5, 1.66), m["eye"], "x", segs=(8, 5))
		b.blob((0.16, 0.02, 0.08), (0.13 * s, -0.48, 1.66), m["sun"], "x", segs=(8, 5))
	return b.build_static()


def build_commander_helm():
	"""The knight-commander's tall plumed helm: a sun crest over the brow and a long plume of saffron and
	gold feathers sweeping up and back; eyes burning in the visor."""
	m = sentinel_materials(True)
	b = Builder("commander_helm")
	_sun_disc(b, (0, -0.5, 2.1), (0, -1, 0.3), 0.13, m)
	b.seg((0, -0.3, 2.18), (0, 0.1, 2.3), 0.05, 0.04, m["gold"], "x", sides=6)                     # the crest rail
	for k in range(9):   # the plume, rising from the crest in a tall arc
		u = k / 8
		base = Vector((0, -0.24 + 0.4 * u, 2.22 + 0.06 * math.sin(math.pi * u)))
		d = Vector((0, 0.3 + 0.9 * u, 1.0 - 0.8 * u)).normalized()
		ln = 0.5 + 0.35 * math.sin(math.pi * (0.25 + 0.6 * u))
		_oblob(b, (0.1, ln, 0.05), tuple(base + d * ln * 0.5), d, (1, 0, 0), m["saffron"] if k % 2 else m["gold"], "x", segs=(8, 4))
		_oblob(b, (0.08, ln * 0.35, 0.055), tuple(base + d * ln * 0.85), d, (1, 0, 0), m["cloth"], "x", segs=(6, 4))
	for s in (1, -1):
		b.blob((0.1, 0.03, 0.05), (0.13 * s, -0.53, 1.66), m["eye"], "x", segs=(8, 5))
	return b.build_static()


def build_commander_banner():
	"""The commander's banner on a pole strapped to his back: the Dawn-Tusk's sun on tattered white and
	gold cloth, rising well above his head."""
	import random
	rng = random.Random(623)
	m = sentinel_materials(True)
	b = Builder("commander_banner")
	b.seg((-0.12, 0.34, 0.6), (-0.2, 0.36, 3.0), 0.03, 0.028, m["pole"], "x", sides=6)
	b.seg((-0.2, 0.36, 3.0), (-0.2, 0.36, 3.08), 0.05, 0.0, m["gold"], "x", sides=6)
	b.seg((-0.2, 0.38, 2.9), (0.6, 0.38, 2.9), 0.02, 0.02, m["pole"], "x", sides=5)
	for s in (1, -1):
		b.seg((0.26 * s, 0.24, 1.36), (-0.14, 0.34, 1.2), 0.02, 0.02, m["gold"], "x", sides=4)
	# the cloth hangs in strips, torn to different lengths
	for k in range(6):
		x0 = -0.18 + 0.13 * k
		ln = rng.uniform(0.7, 1.15) if k not in (2, 3) else 1.2
		_slab(b, [(x0, 0.39, 2.88), (x0 + 0.13, 0.39, 2.88), (x0 + 0.12, 0.4, 2.88 - ln), (x0 + 0.02, 0.4, 2.88 - ln + rng.uniform(0.02, 0.14))],
			  0.02, m["cloth"] if k % 2 else m["cloth_d"])
	_slab(b, [(-0.18, 0.37, 2.88), (0.6, 0.37, 2.88), (0.6, 0.37, 2.76), (-0.18, 0.37, 2.76)], 0.03, m["saffron"])
	_sun_disc(b, (0.21, 0.42, 2.36), (0, 1, 0), 0.16, m)
	_sun_disc(b, (0.21, 0.36, 2.36), (0, -1, 0), 0.16, m)
	return b.build_static()


# ---------------------------------------------------------------- Mirror Flats folk (Rogue bodies)

# the Rogue as a Duneskiff nomad: sun-bleached wraps (0,1) (1,1) (7,1), a brass-buckled belt (5,0) (3,0) (6,0),
# boots (3,2), gloves (7,2), skin (0,0) weathered tan, hair (1,0)
DUNESKIFF_CELLS = {(0, 1): ("f2ecdc", "a49c86"), (1, 1): ("d8e4e8", "82949c"), (7, 1): ("e6dcc4", "968a6e"),
				   (5, 0): ("8a7050", "3a2c1c"), (3, 0): ("d8b060", "7a5a20"), (6, 0): ("d8b060", "7a5a20"),
				   (3, 2): ("b8a078", "5e4c30"), (7, 2): ("c8b898", "6a5a40"), (0, 0): ("c89a72", "7a5238"),
				   (1, 0): ("3a2a20", "140c08")}
NOMAD_QUEEN_CELLS = {(0, 1): ("f6f2e8", "b0a88e"), (1, 1): ("2e4a7a", "0e1a34"), (7, 1): ("f0e8d4", "a0947a"),
					 (5, 0): ("c89a3a", "6a4a12"), (3, 0): ("f4d468", "9a6a14"), (6, 0): ("f4d468", "9a6a14"),
					 (3, 2): ("8a6a4a", "3a2a1a"), (7, 2): ("e8dcc4", "8a7c64"), (0, 0): ("b88a64", "6a4428"),
					 (1, 0): ("1e1612", "080604")}


def nomad_materials(queen=False):
	p = "nomad_queen" if queen else "duneskiff"
	return {
		"linen": material(f"{p}_linen", "f2ecdc", 0.95),
		"linen_b": material(f"{p}_linen_b", "e2dac4", 0.95),
		"linen_dirty": material(f"{p}_linen_dirty", "c8bea4", 0.95),
		"veil": material(f"{p}_veil", "d8e4e8" if not queen else "2e4a7a", 0.9),
		"veil_d": material(f"{p}_veil_dark", "9aacb4" if not queen else "1a2c50", 0.9),
		"turq": material(f"{p}_turquoise", "3ab0a8", 0.5),
		"brass": metal_material(f"{p}_brass", "c8a050", 0.35, 0.8),
		"mirror": metal_material(f"{p}_mirror", "e4f0f8", 0.08, 0.5, emit=0.45),
		"gap": material(f"{p}_gap", "1a1410", 0.95),
		"salt": material(f"{p}_salt", "fbfaf6", 0.3, emit=0.15),
		"salt_p": material(f"{p}_salt_pink", "f4d0d4", 0.3, emit=0.1),
		"feather": material(f"{p}_feather", "f4f0e8", 0.9),
		"feather_p": material(f"{p}_feather_pink", "e89aa8", 0.9),
		"feather_d": material(f"{p}_feather_dark", "2a2a30", 0.9),
		"gold": metal_material(f"{p}_gold", "f0c850", 0.3, 0.9),
		"cord": material(f"{p}_cord", "5a4030", 0.9),
	}


def _nomad_wrap(b, m, rng, queen):
	"""The head wrapped against sun and salt glare (Rogue head hidden): a wound hood, a veil over nose and
	mouth, and mirror-lensed goggles; a tail of cloth down the back."""
	shape = lambda z: max(0.4, math.sqrt(max(0.0, 1 - ((z - 1.66) / 0.54) ** 2)))
	b.blob((0.96, 0.96, 0.96), (0, 0.02, 1.66), m["linen_b"], "x", segs=(14, 10))
	_wound(b, m, (0, 0.02, 0), (0.5, 0.5), 1.24, 2.08, rng, gap=(240, 300), gap_z=(1.6, 1.76), width=0.12, shape=shape)
	_box(b, (0.56, 0.12, 0.14), (0, -0.44, 1.68), m["gap"])
	for s in (1, -1):   # goggles with round mirrored lenses that throw back the sky
		c = (0.17 * s, -0.5, 1.69)
		b.seg((c[0], -0.46, c[2]), (c[0], -0.54, c[2]), 0.12, 0.13, m["brass"], "x", sides=12)
		b.seg((c[0], -0.52, c[2]), (c[0], -0.56, c[2]), 0.1, 0.1, m["mirror"], "x", sides=12)
	b.seg((-0.06, -0.54, 1.69), (0.06, -0.54, 1.69), 0.03, 0.03, m["brass"], "x", sides=5)
	_ring(b, (0, 0.02, 1.7), (0.53, 0.53), (0, 0), 0.025, m["cord"], sides=18, gap=(12, 16))
	for s in (1, -1):   # the veil, folded to a point, with turquoise beads along its edge
		_slab(b, [(0.0, -0.56, 1.6), (0.42 * s, -0.46, 1.6), (0.32 * s, -0.5, 1.24), (0.0, -0.62, 1.06)], 0.04, m["veil"])
		for k in range(3):
			u = (k + 1) / 4
			p = Vector((0.32 * s, -0.5, 1.24)) * (1 - u) + Vector((0.0, -0.62, 1.06)) * u
			b.blob((0.04, 0.04, 0.04), tuple(p + Vector((0, -0.03, -0.02))), m["turq"], "x", segs=(5, 4))
	b.seg((0.0, -0.57, 1.58), (0.0, -0.62, 1.08), 0.02, 0.02, m["veil_d"], "x", sides=4)
	_shell(b, (1.12, 1.04, 0.6), (0, 0.04, 1.12), m["linen_dirty"] if not queen else m["veil"], lambda d: d.z > 0.0)
	_slab(b, [(-0.12, 0.46, 1.9), (0.12, 0.47, 1.88), (0.18, 0.6, 1.1), (0.0, 0.6, 1.02)], 0.035, m["linen_dirty"])
	for x, z in ((0.3, 1.2), (-0.26, 1.24), (0.1, 1.3)):   # a crust of salt dried on the scarf
		b.blob((0.08, 0.04, 0.05), (x, -0.4, z), m["salt"], "x", segs=(5, 3))


def build_duneskiff_wrap():
	import random
	b = Builder("duneskiff_wrap")
	_nomad_wrap(b, nomad_materials(), random.Random(631), False)
	return b.build_static()


def build_nomad_queen_headdress():
	"""The raider queen's headdress: the same wrapped hood in white and indigo under a tall crown of salt
	crystals fanned with white, pink and black feathers, gold chains hanging at the temples."""
	import random
	rng = random.Random(633)
	m = nomad_materials(True)
	b = Builder("nomad_queen_headdress")
	_nomad_wrap(b, m, rng, True)
	_wrap(b, (0, 0.02, 2.0), (0.46, 0.46), 0.1, 0.04, m["gold"], sides=18)                         # a gold circlet
	for k in range(11):   # crystals rising from the circlet, tallest at the front
		a = math.radians(200 + 14 * k)
		p = Vector((0.44 * math.cos(a), 0.02 + 0.44 * math.sin(a), 2.02))
		front = 1 - abs(k - 5) / 5
		d = Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 1.0))
		_crystal(b, tuple(p), tuple(d), 0.2 + 0.36 * front, 0.05 + 0.02 * front, m["salt"] if k % 2 else m["salt_p"], "x")
	for k in range(9):   # feathers fanned behind the crystals
		a = math.radians(200 + 17.5 * k)
		p = Vector((0.4 * math.cos(a), 0.12 + 0.4 * math.sin(a) * 0.3, 2.06))
		d = Vector((math.cos(a) * 0.5, 0.35, 1.0)).normalized()
		ln = 0.5 + 0.2 * (1 - abs(k - 4) / 4)
		_feather(b, tuple(p), tuple(d), ln, 0.1, [m["feather"], m["feather_p"], m["feather"]][k % 3], (0, 1, 0),
				 tip_mat=m["feather_d"], thick=0.03)
	b.blob((0.12, 0.05, 0.14), (0, -0.46, 2.02), m["gold"], "x", segs=(8, 6))                       # a gold boss on the brow
	b.blob((0.07, 0.04, 0.08), (0, -0.49, 2.02), m["turq"], "x", segs=(6, 4))
	for s in (1, -1):   # chains of gold at the temples
		for k in range(4):
			b.blob((0.035, 0.035, 0.035), (0.45 * s, -0.12, 1.94 - 0.08 * k), m["gold"], "x", segs=(5, 4))
		b.blob((0.05, 0.05, 0.06), (0.45 * s, -0.12, 1.6), m["turq"], "x", segs=(5, 4))
	return b.build_static()


def build_salt_scimitar():
	"""The raider queen's curved blade (KayKit weapons' frame: grip at the origin, blade up +Z), steel
	with a salt-white edge and a gold guard."""
	m = nomad_materials(True)
	steel = metal_material("salt_scimitar_steel", "d8e0e4", 0.25, 0.55)
	edge = material("salt_scimitar_edge", "fbfaf6", 0.2, emit=0.2)
	b = Builder("salt_scimitar")
	b.seg((0, 0, -0.14), (0, 0, 0.12), 0.03, 0.03, m["cord"], "x", sides=6)
	b.blob((0.07, 0.07, 0.07), (0, 0, -0.16), m["gold"], "x", segs=(6, 5))
	b.seg((-0.1, 0, 0.13), (0.1, 0, 0.13), 0.025, 0.025, m["gold"], "x", sides=6)
	for s in (1, -1):
		b.blob((0.05, 0.04, 0.05), (0.11 * s, 0, 0.13), m["gold"], "x", segs=(5, 4))
	# the blade: a curve of flat slabs, widening toward the tip then sweeping to a point
	pts = []
	for k in range(9):
		u = k / 8
		pts.append((Vector((0.28 * u * u, 0, 0.15 + 0.78 * u)), 0.045 + 0.03 * math.sin(math.pi * u * 0.85)))
	for (p, w), (q, w2) in zip(pts, pts[1:]):
		n = Vector((1, 0, 0))
		_slab(b, [tuple(p - n * w * 0.3), tuple(p + n * w), tuple(q + n * w2), tuple(q - n * w2 * 0.3)], 0.018, steel)
		_slab(b, [tuple(p + n * w), tuple(p + n * (w + 0.015)), tuple(q + n * (w2 + 0.015)), tuple(q + n * w2)], 0.01, edge)
	tip, w = pts[-1]
	_slab(b, [tuple(tip - Vector((0.014, 0, 0))), tuple(tip + Vector((w + 0.015, 0, 0))), tuple(tip + Vector((0.12, 0, 0.12)))], 0.016, edge)
	return b.build_static()


def build_reflection_face():
	"""The Reflection's head (Rogue head hidden): an oval of mirror glass for a face, cracked from one
	point, a shard missing, and a crown of glass splinters; a collar of shards at the neck."""
	import random
	rng = random.Random(641)
	mirror = metal_material("reflection_mirror", "eef4fa", 0.06, 0.5, emit=0.35)
	frame = metal_material("reflection_frame", "c4d0dc", 0.15, 0.5, emit=0.12)
	crack = material("reflection_crack", "1a2230", 0.4)
	glint = material("reflection_glint", "ffffff", 0.1, emit=3.0)
	shard = glass_material("reflection_shard", "d8ecff", 0.55, 0.05, emit=0.4)
	b = Builder("reflection_face")
	b.blob((0.8, 0.8, 0.94), (0, 0.04, 1.68), frame, "x", segs=(14, 10))                            # the head, a smooth glass egg
	b.blob((0.66, 0.2, 0.84), (0, -0.28, 1.68), mirror, "x", segs=(14, 10))                         # the mirror face
	# the cracks: from a point off-center, jagged lines running out across the glass
	o = Vector((0.1, -0.385, 1.76))
	for k in range(8):
		a = 2 * math.pi * k / 8 + rng.uniform(-0.2, 0.2)
		p = o.copy()
		for j in range(3):
			ln = rng.uniform(0.07, 0.13)
			q = p + Vector((math.cos(a) * ln, 0, math.sin(a) * ln))
			a += rng.uniform(-0.5, 0.5)
			# keep the crack on the face's curve
			for v in (q,):
				x, z = v.x / 0.33, (v.z - 1.68) / 0.42
				v.y = -0.28 - 0.1 * math.sqrt(max(0.0, 1 - x * x - z * z)) - 0.008
			b.seg(tuple(p), tuple(q), 0.008, 0.006, crack, "x", sides=4)
			p = q
			if abs(p.x) > 0.3 or abs(p.z - 1.68) > 0.38:
				break
	_slab(b, [(0.12, -0.39, 1.8), (0.2, -0.38, 1.86), (0.24, -0.37, 1.74)], 0.02, crack)             # a shard fallen out
	b.blob((0.03, 0.02, 0.03), (-0.14, -0.39, 1.9), glint, "x", segs=(5, 3))
	b.blob((0.02, 0.02, 0.02), (-0.18, -0.385, 1.84), glint, "x", segs=(4, 3))
	for k in range(9):   # a crown of splinters
		a = math.radians(200 + 17.5 * k)
		p = Vector((0.28 * math.cos(a), 0.04 + 0.3 * math.sin(a), 2.0))
		_crystal(b, tuple(p), (math.cos(a) * 0.25, math.sin(a) * 0.25, 1), 0.14 + 0.16 * (1 - abs(k - 4) / 4), 0.035, shard, "x")
	for k in range(10):   # a collar of shards
		a = 2 * math.pi * k / 10
		p = Vector((0.26 * math.cos(a), 0.02 + 0.24 * math.sin(a), 1.3))
		_crystal(b, tuple(p), (math.cos(a), math.sin(a), 0.8), 0.14 + 0.06 * (k % 2), 0.04, shard, "x")
	return b.build_static()


# ---------------------------------------------------------------- recolored beasts and spirits

def build_roc():
	"""The roc: the firebird's frame (hovering on outspread wings) as a great brown-gold eagle."""
	arm = build_firebird("roc_src", False)
	_dw_recolor(arm, "roc_src", "roc", {
		"back": ("5a3a1e", 0.9, 0.0), "body": ("8a5a2a", 0.9, 0.0), "breast": ("d8b070", 0.9, 0.0),
		"feather_0": ("3e2814", 0.9, 0.0), "feather_1": ("6a4422", 0.9, 0.0), "feather_2": ("9a6a2e", 0.9, 0.0),
		"feather_3": ("d8a848", 0.85, 0.0), "beak": ("e0b838", 0.4, 0.0), "beak_dark": "3a2a1a",
		"eye": ("ffd040", 0.3, 1.2), "talon": "2a2018", "white": ("f0e2c0", 0.9, 0.0)})
	return arm


def build_great_roc():
	"""The great roc: the phoenix's frame (bigger, longer plumes) in white and gold."""
	arm = build_firebird("great_roc_src", True)
	_dw_recolor(arm, "great_roc_src", "great_roc", {
		"back": ("e0d2b0", 0.85, 0.0), "body": ("f2ead6", 0.85, 0.0), "breast": ("fffaf0", 0.85, 0.0),
		"feather_0": ("b88a38", 0.7, 0.0), "feather_1": ("dcb454", 0.7, 0.0), "feather_2": ("f0dca0", 0.8, 0.0),
		"feather_3": ("fffaf0", 0.8, 0.1), "beak": ("f0c040", 0.35, 0.0), "beak_dark": "4a3a1a",
		"eye": ("ffe070", 0.2, 2.0), "talon": "2a2018", "white": ("f8d860", 0.4, 0.8)})
	return arm


def build_snow_spirit():
	"""A whirlwind of snow and wind: the air elemental in pale ice-blue, shards of ice riding its
	bands and a crown of icicles."""
	import random
	rng = random.Random(651)
	arm = build_air_elemental()
	_dw_recolor(arm, "air", "snow_spirit", {"white": ("f6fbff", 0.7, 0.35), "pale": ("d4eaf8", 0.7, 0.1),
											"blue": ("a2cce8", 0.6, 0.0), "deep": ("6ea4d0", 0.6, 0.0), "eye": ("a8f4ff", 0.1, 5.0)})
	ice = glass_material("snow_spirit_ice", "c8ecff", 0.75, 0.1, emit=0.5)
	ice_w = material("snow_spirit_frost", "ffffff", 0.4, emit=0.6)

	def more(b):
		for bone, z, r, n in (("band_a", 0.8, 0.46, 6), ("band_b", 1.25, 0.5, 7), ("band_c", 1.62, 0.44, 6)):
			for k in range(n):
				a = 2 * math.pi * k / n + rng.uniform(0, 0.4)
				p = Vector((r * math.cos(a), r * math.sin(a), z + rng.uniform(-0.06, 0.06)))
				_crystal(b, tuple(p), (math.cos(a + 1.2), math.sin(a + 1.2), rng.uniform(-0.3, 0.3)), rng.uniform(0.12, 0.22), 0.035, ice, bone, tip_mat=ice_w)
		for k in range(7):   # an icicle crown
			a = math.radians(200 + 20 * k)
			p = Vector((0.18 * math.cos(a), -0.04 + 0.18 * math.sin(a), 2.06))
			_crystal(b, tuple(p), (math.cos(a) * 0.3, math.sin(a) * 0.3, 1), 0.14 + 0.1 * (1 - abs(k - 3) / 3), 0.03, ice, "head", tip_mat=ice_w)
		for k in range(14):   # snowflakes caught in the funnel
			a = rng.uniform(0, 2 * math.pi)
			z = rng.uniform(0.2, 1.0)
			r = 0.14 + 0.4 * z * z + 0.06
			b.blob((0.05, 0.05, 0.05), (r * math.cos(a), r * math.sin(a), z), ice_w, "funnel", segs=(4, 3))
	return _dw_extend(arm, more)


def build_avalanche_elemental():
	"""Packed snow, ice and rock: the earth elemental's hulk in blue-gray stone under caps of snow, ice
	in its seams in place of moss, a cold blue light in the cracks, icicles hanging off its arms."""
	import random
	rng = random.Random(653)
	arm = build_earth_elemental()
	_dw_recolor(arm, "earth", "avalanche_elemental", {
		"stone": ("8c96a2", 0.9, None), "stone_dark": ("5a6470", 0.9, None), "stone_light": ("eef4f8", 0.8, None),
		"soil": ("e4ecf2", 0.8, None), "moss": ("9cd4ee", 0.3, None), "moss_b": ("c8e8f6", 0.3, None),
		"glow": ("78d0ff", 0.3, 2.0), "eye": ("e0f8ff", 0.1, 5.0)})
	snow = material("avalanche_elemental_snow", "f6fafc", 0.85)
	snow_b = material("avalanche_elemental_snow_b", "dfe9f0", 0.85)
	ice = glass_material("avalanche_elemental_ice", "b8e4fa", 0.8, 0.1, emit=0.3)

	def more(b):
		for s in (1, -1):
			side = "l" if s > 0 else "r"
			_rock(b, (0.6, 0.62, 0.26), (0.66 * s, 0.0, 2.2), snow, f"shoulder_{side}", rng, jitter=0.1)     # snowcaps
			_rock(b, (0.36, 0.4, 0.18), (0.8 * s, -0.08, 2.14), snow_b, f"shoulder_{side}", rng, jitter=0.1)
			for k in range(4):   # icicles under the arms
				p = Vector((0.82 * s + 0.06 * k * s, -0.1 + 0.08 * k, 1.66 - 0.06 * k))
				_crystal(b, tuple(p), (0, 0, -1), 0.18 + 0.06 * (k % 2), 0.035, ice, f"arm_{side}")
			_rock(b, (0.36, 0.36, 0.14), (0.36 * s, -0.08, 0.42), snow_b, f"leg_{side}", rng)
		_rock(b, (0.9, 0.7, 0.26), (0, 0.16, 2.08), snow, "chest", rng, jitter=0.1)                   # snow drifted on its back
		_rock(b, (0.4, 0.36, 0.14), (0, -0.2, 2.2), snow_b, "head", rng)
		for k in range(6):   # ice crystals thrusting out of the hump
			a = math.radians(40 + 20 * k)
			p = Vector((0.4 * math.cos(a), 0.34, 1.7 + 0.1 * math.sin(a)))
			_crystal(b, tuple(p), (math.cos(a) * 0.5, 1, 0.8), 0.26 + 0.1 * (k % 2), 0.06, ice, "chest")
	return _dw_extend(arm, more)


def build_storm_crowned_spirit():
	"""The Storm-Crowned: the tempest spirit gone pale as a winter sky, robed in streaming bands of wind,
	a crown of dark storm cloud on its head with lightning forking up out of it."""
	import random
	rng = random.Random(655)
	arm = build_tempest_spirit("storm_crowned_src", False)
	_dw_recolor(arm, "storm_crowned_src", "storm_crowned_spirit", {
		"cloud_dark": ("7890b0", 0.9, None), "cloud": ("a8c4dc", 0.9, None), "cloud_light": ("dcecf6", 0.85, 0.2),
		"core": ("f0fbff", 0.2, 6.0), "core_blue": ("8adcff", 0.2, 3.5), "bolt": ("d8f4ff", 0.2, 4.0)})
	storm = material("storm_crowned_spirit_storm", "3a4254", 0.9)
	storm_d = material("storm_crowned_spirit_storm_dark", "262a36", 0.9)
	bolt = material("storm_crowned_spirit_crown_bolt", "fff4c0", 0.2, emit=6.0)
	wind = glass_material("storm_crowned_spirit_wind", "d8f0ff", 0.6, 0.3, emit=0.4)
	wind_b = glass_material("storm_crowned_spirit_wind_b", "a8d8f4", 0.55, 0.3, emit=0.3)

	def more(b):
		c = Vector((0, -0.06, 2.34))
		for k in range(9):   # the crown: storm puffs round the brow
			a = 2 * math.pi * k / 9
			p = c + Vector((0.26 * math.cos(a), 0.26 * math.sin(a), 0.04 * math.sin(3 * a)))
			r = rng.uniform(0.18, 0.26)
			b.blob((r, r, r * 0.8), tuple(p), storm if k % 2 else storm_d, "head", segs=(8, 6))
		for k in range(5):   # lightning forking up out of it
			a = 2 * math.pi * k / 5 + 0.3
			p = c + Vector((0.22 * math.cos(a), 0.22 * math.sin(a), 0.1))
			pts = [p]
			for j in range(3):
				pts.append(pts[-1] + Vector((0.08 * math.cos(a) + rng.uniform(-0.06, 0.06), 0.08 * math.sin(a) + rng.uniform(-0.06, 0.06), 0.13)))
			start = len(b.parts)
			_zigzag(b, [tuple(q) for q in pts], 0.022, bolt, "head")
		# robes of wind: ribbons streaming round the body, tipped this way and that, trailing tails
		for bone, z, r, tilt in (("low", 0.55, 0.32, 14), ("low", 0.85, 0.4, -10), ("mid", 1.15, 0.5, 12), ("mid", 1.35, 0.52, -16),
								 ("chest", 1.6, 0.5, 10)):
			start = len(b.parts)
			_wrap(b, (0, 0, z), (r, r * 0.92), 0.08, 0.02, wind if z < 1.2 else wind_b, rot=(tilt, tilt * 0.6, 0), gap=(100, 160), sides=18)
			_on_bone(b, start, bone)
			a = math.radians(100)
			p = Vector((r * math.cos(a), r * math.sin(a), z))
			b.seg(tuple(p), tuple(p + Vector((0.1, 0.36, -0.2))), 0.035, 0.005, wind, bone, sides=4)
	return _dw_extend(arm, more)


def build_mirage_wisp():
	"""A shimmer of light and heat haze: the lantern wisp pale and white-hot, ringed by prismatic motes,
	and a haze of glassy streaks hanging under it."""
	arm = build_lantern_wisp()
	_dw_recolor(arm, "lantern_wisp", "mirage_wisp", {
		"core": ("ffffff", 0.2, 5.0), "inner": ("d8f4ff", 0.3, 3.0), "halo": ("f0e4ff", 0.3, 1.6),
		"tail": ("ffe4f4", 0.35, 1.6), "tail_faint": ("e0fcff", 0.2, 1.2), "eye": ("5a4a7a", 0.3, None)})
	colors = ("ff5a5a", "ffa040", "fff060", "60f080", "50b8ff", "b070ff")
	motes = [material(f"mirage_wisp_prism_{k}", c, 0.2, emit=3.0) for k, c in enumerate(colors)]
	haze = glass_material("mirage_wisp_haze", "fff8e8", 0.18, 0.1, emit=0.6)

	def more(b):
		z0 = 1.2
		for k in range(12):   # a tilted ring of prismatic motes
			a = 2 * math.pi * k / 12
			p = Vector((0.36 * math.cos(a), 0.36 * math.sin(a) * 0.8, z0 + 0.12 * math.sin(a)))
			_oblob(b, (0.05, 0.12, 0.05), tuple(p), (-math.sin(a), math.cos(a), 0), (0, 0, 1), motes[k % 6], "orb", segs=(6, 4))
		for k in range(5):   # heat haze: tall glassy ripples hanging under it
			x = (k - 2) * 0.09
			_oblob(b, (0.03, 0.08, 0.5), (x, 0.02 * k, z0 - 0.42), (0, 1, 0), (0, 0, 1), haze, "orb", segs=(6, 6))
	return _dw_extend(arm, more)


def _salt_crust(b, rng, sc, sr, count, mats, bone, size=1.0):
	for k in range(count):
		x, y = rng.uniform(-0.55, 0.55), rng.uniform(-0.3, 0.46)
		p, n = _on_dome(sc, sr, x, y, 0.0)
		for j in range(rng.choice((2, 3))):
			d = Vector(n) + Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0))
			_crystal(b, tuple(p), tuple(d), rng.uniform(0.1, 0.22) * size, rng.uniform(0.03, 0.05) * size, mats[(k + j) % len(mats)], bone)


def _salt_crab(src, name, old):
	import random
	rng = random.Random(661 if old else 663)
	arm = build_causeway_crab(src, old)
	_dw_recolor(arm, src, name, {
		"shell": ("e4ded2", 0.7, None), "shell_dark": ("b4a898", 0.7, None), "shell_light": ("faf8f2", 0.6, None),
		"under": ("f2d6cc", 0.7, None), "claw_tip": ("6a5048", 0.4, None), "barnacle": ("fffcf4", 0.5, None),
		"hole": ("c8bcb0", 0.8, None), "coral": ("fcfaf4", 0.4, None), "coral_o": ("f4e4e8", 0.4, None),
		"coral_p": ("f4c4cc", 0.4, None), "scar": ("c89a8a", 0.8, None)})
	salt = material(f"{name}_salt", "fbfaf6", 0.25, emit=0.1)
	salt_p = material(f"{name}_salt_pink", "f6d4d8", 0.25, emit=0.08)

	def more(b):
		z0 = 0.66
		_salt_crust(b, rng, (0, 0.02, z0 + 0.1), (0.72, 0.56, 0.3), 12 if not old else 18, (salt, salt, salt_p), "body",
					size=1.0 if not old else 1.3)
	return _dw_extend(arm, more)


def build_salt_crab():
	return _salt_crab("salt_crab_src", "salt_crab", False)


def build_old_saltclaw():
	return _salt_crab("old_saltclaw_src", "old_saltclaw", True)


def build_salt_wader():
	"""A tall wading bird of the salt flats: the reedstalker's frame in white and flamingo pink, dark wing
	tips, a pale bill with a black tip and pink legs."""
	arm = build_reedstalker("salt_wader_src", False)
	return _dw_recolor(arm, "salt_wader_src", "salt_wader", {
		"slate": "f2b0bc", "slate_d": "d8808e", "slate_l": "fcd4da", "white": "fbf6f2", "cream": "fce2e6",
		"black": "2a2226", "beak": ("ece2d0", 0.4, None), "beak_d": ("1e1a1c", 0.4, None), "leg": "e88c9c",
		"leg_d": "a85a6a", "eye": ("ffe890", 0.35, 0.8)})


# ---------------------------------------------------------------- wyvern

def build_wyvern():
	"""A two-legged winged drake the size of a horse: blue-gray scales, a pale belly, bat wings for
	forelimbs folded high over its back, a horned wedge of a head on a long neck, and a long tail ending
	in a barbed spade. It walks on its hind legs, body tipped up."""
	sc = material("wyvern_scale", "5c6c80", 0.7)
	sc_d = material("wyvern_scale_dark", "38445a", 0.7)
	sc_l = material("wyvern_scale_light", "8a9aae", 0.7)
	belly = material("wyvern_belly", "c8ccc0", 0.8)
	belly_d = material("wyvern_belly_dark", "9ea294", 0.8)
	membrane = material("wyvern_membrane", "7a8aa8", 0.8)
	horn = material("wyvern_horn", "e4dcc8", 0.5)
	claw = material("wyvern_claw", "1e2028", 0.4)
	barb = material("wyvern_barb", "2a2e3a", 0.4)
	eye = material("wyvern_eye", "ffcc30", 0.2, emit=3.0)
	tooth = material("wyvern_tooth", "f0ead8", 0.4)
	mouth = material("wyvern_mouth", "7a2a30", 0.7)
	b = Builder("wyvern")
	b.bone("root", (0, 0, 1.1))
	b.bone("body", (0, 0.1, 1.2), "root")
	b.bone("neck", (0, -0.6, 1.62), "body")
	b.bone("head", (0, -0.98, 2.24), "neck")
	b.bone("jaw", (0, -1.12, 2.18), "head")
	b.bone("tail1", (0, 0.72, 1.08), "body")
	b.bone("tail2", (0, 1.46, 0.84), "tail1")
	b.bone("tail3", (0, 2.16, 0.66), "tail2")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"wing_{side}", (0.3 * s, -0.36, 1.66), "body")
		b.bone(f"leg_{side}", (0.34 * s, 0.34, 1.1), "root")
		b.bone(f"shin_{side}", (0.4 * s, 0.06, 0.62), f"leg_{side}")

	# the body: a deep chest tipped up, lean hips
	b.blob((0.8, 1.4, 0.78), (0, 0.06, 1.28), sc, "body", rot=(22, 0, 0), segs=(14, 10))
	b.blob((0.6, 1.1, 0.4), (0, -0.06, 1.08), belly, "body", rot=(22, 0, 0), segs=(12, 7))
	for k in range(6):   # belly plates
		y = -0.5 + 0.18 * k
		z = 1.12 - 0.07 * k - 0.08
		b.blob((0.46 - 0.03 * k, 0.16, 0.1), (0, y, z - 0.1 + 0.02 * k), belly_d, "body", rot=(22, 0, 0), segs=(8, 4))
	b.blob((0.72, 0.6, 0.64), (0, -0.38, 1.5), sc, "body", segs=(10, 8))                            # the shoulders
	b.blob((0.66, 0.56, 0.56), (0, 0.4, 1.12), sc, "body", segs=(10, 8))                            # the haunches
	for k in range(7):   # a row of back spines
		y = -0.48 + 0.18 * k
		z = 1.78 - 0.13 * k
		b.seg((0, y, z - 0.08), (0, y + 0.1, z + 0.12 - 0.01 * k), 0.05, 0.0, sc_d, "body", sides=4)
	for s in (1, -1):
		for k in range(4):   # flank scutes
			b.blob((0.08, 0.2, 0.14), (0.36 * s, -0.3 + 0.2 * k, 1.36 - 0.07 * k), sc_d, "body", rot=(22, 22 * s, 0), segs=(6, 4))
	# the neck, arching forward and up
	neck = [(0, -0.5, 1.6, 0.22), (0, -0.72, 1.86, 0.17), (0, -0.84, 2.08, 0.14), (0, -0.96, 2.24, 0.13)]
	for (x0, y0, z0, r0), (x1, y1, z1, r1) in zip(neck, neck[1:]):
		b.seg((x0, y0, z0), (x1, y1, z1), r0, r1, sc, "neck", sides=9)
		b.seg((x0, y0 - r0 * 0.4, z0 - r0 * 0.3), (x1, y1 - r1 * 0.4, z1 - r1 * 0.3), r0 * 0.7, r1 * 0.7, belly, "neck", sides=7)
		b.blob((r1 * 2, r1 * 2, r1 * 2), (x1, y1, z1), sc, "neck", segs=(8, 6))
		b.seg((0, y0 + 0.02, z0 + r0 * 0.9), (0, y0 + 0.08, z0 + r0 * 0.9 + 0.1), 0.035, 0.0, sc_d, "neck", sides=4)
	# the head: a wedge with a heavy brow, horns swept back, a lower jaw on its own bone
	b.blob((0.34, 0.42, 0.28), (0, -1.02, 2.3), sc, "head", segs=(10, 8))
	b.seg((0, -1.12, 2.32), (0, -1.5, 2.24), 0.14, 0.07, sc, "head", sides=8)                       # the snout
	b.blob((0.32, 0.18, 0.1), (0, -1.1, 2.42), sc_d, "head", rot=(-10, 0, 0), segs=(8, 5))         # the brow ridge
	for s in (1, -1):
		b.blob((0.08, 0.06, 0.06), (0.13 * s, -1.14, 2.37), eye, "head", segs=(6, 4))
		b.seg((0.1 * s, -0.98, 2.42), (0.2 * s, -0.66, 2.54), 0.05, 0.01, horn, "head", sides=6)     # main horns
		b.seg((0.14 * s, -0.94, 2.32), (0.26 * s, -0.74, 2.3), 0.03, 0.005, horn, "head", sides=5)   # cheek horns
		b.blob((0.04, 0.03, 0.03), (0.05 * s, -1.49, 2.27), claw, "head", segs=(4, 3))               # nostrils
		for k in range(4):
			b.seg((0.07 * s, -1.2 - 0.07 * k, 2.2), (0.07 * s, -1.2 - 0.07 * k, 2.15), 0.014, 0.0, tooth, "head", sides=4)
	b.blob((0.18, 0.36, 0.05), (0, -1.28, 2.2), mouth, "head", segs=(8, 4))
	b.seg((0, -1.1, 2.16), (0, -1.46, 2.13), 0.09, 0.05, sc_l, "jaw", sides=7)                      # the lower jaw
	for s in (1, -1):
		for k in range(3):
			b.seg((0.05 * s, -1.22 - 0.07 * k, 2.17), (0.05 * s, -1.22 - 0.07 * k, 2.22), 0.012, 0.0, tooth, "jaw", sides=4)
	# the tail, tapering, spined, ending in a barbed spade
	tail = [(0, 0.66, 1.1, 0.2, "tail1"), (0, 1.1, 0.96, 0.15, "tail1"), (0, 1.46, 0.84, 0.12, "tail2"),
			(0, 1.84, 0.74, 0.09, "tail2"), (0, 2.16, 0.66, 0.07, "tail3"), (0, 2.56, 0.58, 0.045, "tail3")]
	for (x0, y0, z0, r0, bone), (x1, y1, z1, r1, _) in zip(tail, tail[1:]):
		b.seg((x0, y0, z0), (x1, y1, z1), r0, r1, sc, bone, sides=8)
		b.blob((r1 * 2, r1 * 2, r1 * 2), (x1, y1, z1), sc, bone, segs=(8, 5))
		b.seg((0, (y0 + y1) / 2, (z0 + z1) / 2 + r0 * 0.9), (0, (y0 + y1) / 2 + 0.08, (z0 + z1) / 2 + r0 * 0.9 + 0.09), 0.03, 0.0, sc_d, bone, sides=4)
	tip = Vector((0, 2.56, 0.58))
	_slab(b, [tuple(tip + Vector((0, -0.04, 0))), tuple(tip + Vector((0.2, 0.12, 0))), tuple(tip + Vector((0, 0.46, 0))),
			  tuple(tip + Vector((-0.2, 0.12, 0)))], 0.05, barb)
	start = len(b.parts)
	_on_bone(b, start - 1, "tail3")
	for s in (1, -1):   # barbs raking back off the spade
		b.seg(tuple(tip + Vector((0.18 * s, 0.1, 0))), tuple(tip + Vector((0.3 * s, 0.02, 0.02))), 0.03, 0.0, horn, "tail3", sides=4)
		b.seg(tuple(tip + Vector((0.1 * s, 0.28, 0))), tuple(tip + Vector((0.2 * s, 0.24, 0.02))), 0.025, 0.0, horn, "tail3", sides=4)
	b.seg(tuple(tip + Vector((0, 0.44, 0))), tuple(tip + Vector((0, 0.58, 0.03))), 0.03, 0.0, horn, "tail3", sides=4)
	# the legs: a heavy thigh, a shin angled back, a long foot with three clawed toes and a dewclaw
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.blob((0.34, 0.5, 0.56), (0.36 * s, 0.24, 0.9), sc, f"leg_{side}", rot=(30, 0, 0), segs=(10, 7))
		b.seg((0.36 * s, 0.34, 1.08), (0.4 * s, 0.06, 0.62), 0.15, 0.1, sc, f"leg_{side}", sides=8)
		b.seg((0.4 * s, 0.06, 0.62), (0.4 * s, 0.3, 0.16), 0.09, 0.06, sc_l, f"shin_{side}", sides=7)
		b.blob((0.16, 0.16, 0.16), (0.4 * s, 0.06, 0.62), sc, f"shin_{side}", segs=(8, 5))
		b.seg((0.4 * s, 0.3, 0.16), (0.4 * s, 0.1, 0.07), 0.06, 0.05, sc_l, f"shin_{side}", sides=6)
		for k in (-1, 0, 1):
			a = Vector((0.4 * s + 0.06 * k, 0.1, 0.07))
			d = a + Vector((0.08 * k, -0.24, -0.02))
			b.seg(tuple(a), tuple(d), 0.04, 0.03, sc_l, f"shin_{side}", sides=5)
			b.seg(tuple(d), tuple(d + Vector((0.01 * k, -0.08, -0.04))), 0.03, 0.0, claw, f"shin_{side}", sides=4)
		b.seg((0.4 * s, 0.28, 0.14), (0.4 * s, 0.4, 0.06), 0.03, 0.0, claw, f"shin_{side}", sides=4)
	# the wings: bat wings rising over the back from the shoulders
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.blob((0.24, 0.3, 0.26), (0.3 * s, -0.36, 1.66), sc, f"wing_{side}", segs=(8, 6))
		_bat_wing(b, s, (0.3 * s, -0.36, 1.66), (sc_d, membrane, claw), f"wing_{side}", scale=1.55)
	arm = b.build()

	def fold(t, amp=4, cycles=1):
		return {"wing_l": {"rot": (0, amp * wave(t, cycles), 0)}, "wing_r": {"rot": (0, -amp * wave(t, cycles), 0)}}

	def tailw(t, cycles, amp=8):
		return {"tail1": {"rot": (2 * wave(t, cycles, 0.3), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (3 * wave(t, cycles, 0.1), 0, amp * 1.3 * wave(t, cycles, -0.15))},
				"tail3": {"rot": (4 * wave(t, cycles, 0.0), 0, amp * 1.6 * wave(t, cycles, -0.3))}}

	def stride(t, amp, bob):
		sw = wave(t, 1)
		return {"leg_l": {"rot": (amp * sw, 0, 0)}, "leg_r": {"rot": (-amp * sw, 0, 0)},
				"shin_l": {"rot": (-amp * 0.6 * max(0.0, -sw), 0, 0)}, "shin_r": {"rot": (-amp * 0.6 * max(0.0, sw), 0, 0)},
				"root": {"loc": (0, 0, bob * abs(wave(t, 2)) - bob * 0.5)}}

	def idle(t):
		return merge({"body": {"rot": (1.5 * wave(t, 1), 0, 0)}, "neck": {"rot": (3 * wave(t, 1, 0.2), 0, 6 * wave(t, 0.5))},
					  "head": {"rot": (-3 * wave(t, 1, 0.2), 0, 8 * wave(t, 1, 0.4))}, "jaw": {"rot": (-4 * max(0.0, wave(t, 1, 0.6)), 0, 0)}},
					 fold(t), tailw(t, 1))

	def walk(t):
		return merge(stride(t, 26, 0.06), {"body": {"rot": (-6, 2 * wave(t, 1), 0)}, "neck": {"rot": (4 * wave(t, 2), 0, 0)},
										   "head": {"rot": (6 - 4 * wave(t, 2), 0, 0)}}, fold(t, 6, 2), tailw(t, 1, 10))

	def run(t):
		return merge(stride(t, 40, 0.12), {"body": {"rot": (-14, 3 * wave(t, 1), 0)}, "neck": {"rot": (-6 + 5 * wave(t, 2), 0, 0)},
										   "head": {"rot": (14 - 5 * wave(t, 2), 0, 0)}}, fold(t, 16, 2), tailw(t, 1, 12))

	def attack(t):   # rears, wings flaring open, and strikes down with its jaws
		rear = seq(t, [(0, 0), (0.35, 1), (0.55, -0.5), (0.8, -0.3), (1, 0)])
		wings = seq(t, [(0, 0), (0.35, 40), (0.55, -10), (1, 0)])
		bite = seq(t, [(0, 0), (0.3, 1), (0.5, 0), (1, 0)])
		return merge({"body": {"rot": (16 * rear, 0, 0)}, "root": {"loc": (0, -0.3 * max(0.0, -rear), 0.1 * max(0.0, rear))},
					  "neck": {"rot": (20 * rear, 0, 0)}, "head": {"rot": (-10 * rear, 0, 0)}, "jaw": {"rot": (-30 * bite, 0, 0)},
					  "wing_l": {"rot": (0, wings, 0)}, "wing_r": {"rot": (0, -wings, 0)}}, tailw(t, 1, 18))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"body": {"rot": (10 * k, 6 * k, 0)}, "neck": {"rot": (14 * k, 0, 12 * k)}, "head": {"rot": (10 * k, 0, 10 * k)},
					  "root": {"loc": (0, 0.12 * k, 0)}, "wing_l": {"rot": (0, 20 * k, 0)}, "wing_r": {"rot": (0, -20 * k, 0)},
					  "jaw": {"rot": (-20 * k, 0, 0)}}, tailw(t, 1, 12))

	def death(t):   # staggers, the legs buckle, and it topples onto its side, one wing spread
		f = seq(t, [(0.1, 0), (0.7, 1)])
		g = seq(t, [(0.4, 0), (0.9, 1)])
		return {"root": {"loc": (0, 0.1 * f, -0.66 * f), "rot": (-8 * f, 70 * g, 0)},
				"leg_l": {"rot": (40 * f, 0, 0)}, "leg_r": {"rot": (50 * f, 0, 0)}, "shin_l": {"rot": (-50 * f, 0, 0)},
				"shin_r": {"rot": (-60 * f, 0, 0)}, "body": {"rot": (-10 * f, 0, 0)}, "neck": {"rot": (-30 * g, 0, 30 * g)},
				"head": {"rot": (-20 * g, 0, 20 * g)}, "jaw": {"rot": (-14 * g, 0, 0)},
				"wing_l": {"rot": (0, -40 * g, 0)}, "wing_r": {"rot": (0, -60 * g, 0)},
				"tail1": {"rot": (0, 0, 20 * g)}, "tail2": {"rot": (0, 0, 16 * g)}, "tail3": {"rot": (0, 0, 10 * g)}}

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 1.1, walk, True)
	clip(arm, "run", 0.7, run, True)
	clip(arm, "attack", 0.9, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# ---------------------------------------------------------------- sky ray and the great sky ray

def build_sky_ray(name="sky_ray", great=False):
	"""A manta gliding low over the flats: a broad pale diamond on slow-beating wing fins, a mirrored
	belly that throws back the sky and the water, curled horn-fins at the mouth, a long whip of a tail.
	The great one is the same ray grown huge (models.json), with a line of glowing blue spots and a
	scarred, sun-bleached back."""
	import random
	rng = random.Random(673 if great else 671)
	top = material(f"{name}_top", "c4ccd0" if not great else "e8ecee", 0.6)
	top_d = material(f"{name}_top_dark", "8a969e" if not great else "a8b4bc", 0.6)
	top_l = material(f"{name}_top_light", "e0e6e8" if not great else "fafcfc", 0.6)
	belly = metal_material(f"{name}_belly", "eef4f8", 0.1, 0.55, emit=0.25)
	rim = material(f"{name}_rim", "5a6a78", 0.6)
	mouth = material(f"{name}_mouth", "1e2226", 0.8)
	eye = material(f"{name}_eye", "101418", 0.2)
	glint = material(f"{name}_glint", "ffffff", 0.1, emit=1.0)
	spot = material(f"{name}_spot", "8ad8ff", 0.3, emit=2.5 if great else 0.0)
	scar = material(f"{name}_scar", "f4f0ea", 0.8)
	H = 1.1
	b = Builder(name)
	b.bone("root", (0, 0, H))
	b.bone("body", (0, 0, H), "root")
	b.bone("head", (0, -0.6, H), "body")
	b.bone("tail1", (0, 0.66, H), "body")
	b.bone("tail2", (0, 1.4, H - 0.04), "tail1")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"wing_{side}", (0.4 * s, 0.0, H), "body")
		b.bone(f"tip_{side}", (1.0 * s, 0.14, H), f"wing_{side}")

	# the body: a flattened, domed diamond
	b.blob((0.9, 1.36, 0.3), (0, 0.0, H + 0.02), top, "body", segs=(14, 8))
	b.blob((0.86, 1.3, 0.2), (0, 0.0, H - 0.04), belly, "body", segs=(14, 6))
	b.blob((0.5, 0.8, 0.14), (0, 0.06, H + 0.14), top_l, "body", segs=(10, 6))
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		# the wing fins: an inner panel and a swept tip, pale above, mirror below, a dark rim at the edge
		inner = [(0.3 * s, -0.55), (1.0 * s, -0.28), (1.05 * s, 0.32), (0.35 * s, 0.6)]
		outer = [(1.0 * s, -0.28), (1.8 * s, 0.18), (1.34 * s, 0.34), (1.05 * s, 0.32)]
		for pts, bone in ((inner, f"wing_{side}"), (outer, f"tip_{side}")):
			start = len(b.parts)
			up = [(x, y, H + 0.03) for x, y in pts]
			dn = [(x, y, H - 0.02) for x, y in pts]
			if s < 0:
				up, dn = list(reversed(up)), list(reversed(dn))
			_slab(b, up, 0.04, top)
			_slab(b, dn, 0.03, belly)
			_on_bone(b, start, bone)
		b.seg((1.0 * s, -0.28, H + 0.01), (1.8 * s, 0.18, H + 0.01), 0.022, 0.01, rim, f"tip_{side}", sides=4)
		b.seg((0.3 * s, -0.55, H + 0.01), (1.0 * s, -0.28, H + 0.01), 0.025, 0.022, rim, f"wing_{side}", sides=4)
		b.blob((0.36, 0.5, 0.06), (0.62 * s, 0.1, H + 0.05), top_d, f"wing_{side}", segs=(8, 4))
		# the cephalic fins: curled lobes either side of the mouth
		b.seg((0.2 * s, -0.62, H), (0.26 * s, -0.92, H - 0.02), 0.07, 0.05, top_d, "head", sides=6)
		b.seg((0.26 * s, -0.92, H - 0.02), (0.2 * s, -1.0, H - 0.1), 0.05, 0.02, top_d, "head", sides=6)
		b.blob((0.08, 0.06, 0.08), (0.34 * s, -0.56, H + 0.04), eye, "head", segs=(6, 4))
		b.blob((0.03, 0.02, 0.03), (0.35 * s, -0.59, H + 0.06), glint, "head", segs=(4, 3))
	b.blob((0.44, 0.3, 0.16), (0, -0.62, H), top, "head", segs=(10, 6))
	b.blob((0.34, 0.08, 0.06), (0, -0.76, H - 0.02), mouth, "head", segs=(8, 4))
	for k in range(5):   # gill slits underneath
		for s in (1, -1):
			b.seg((0.14 * s + 0.03 * k * s, -0.34 + 0.07 * k, H - 0.1), (0.2 * s + 0.03 * k * s, -0.32 + 0.07 * k, H - 0.1), 0.01, 0.01, rim, "body", sides=4)
	# the tail
	b.seg((0, 0.6, H), (0, 1.4, H - 0.04), 0.05, 0.03, top_d, "tail1", sides=6)
	b.seg((0, 1.4, H - 0.04), (0, 2.4, H - 0.08), 0.03, 0.006, top_d, "tail2", sides=5)
	if great:
		for s in (1, -1):   # a line of glowing spots along each wing, and old scars
			for k in range(4):
				b.blob((0.07, 0.07, 0.03), ((0.4 + 0.3 * k) * s, 0.02 + 0.06 * k, H + 0.05), spot, f"wing_{side_(s)}" if k < 3 else f"tip_{side_(s)}", segs=(6, 3))
		for k in range(3):
			x = rng.uniform(-0.3, 0.3)
			b.seg((x, -0.2 + 0.2 * k, H + 0.16), (x + 0.2, -0.1 + 0.2 * k, H + 0.15), 0.015, 0.015, scar, "body", sides=4)
		for k in range(6):
			b.blob((0.06, 0.06, 0.03), (0, -0.3 + 0.14 * k, H + 0.17), spot, "body", segs=(6, 3))
	arm = b.build()

	def fins(t, cycles, amp, lift=0.0):
		f = amp * wave(t, cycles) + lift
		g = amp * 1.1 * wave(t, cycles, -0.15) + lift * 0.6
		return {"wing_l": {"rot": (0, f, 0)}, "wing_r": {"rot": (0, -f, 0)}, "tip_l": {"rot": (0, g, 0)}, "tip_r": {"rot": (0, -g, 0)}}

	def tail(t, cycles, amp=6):
		return {"tail1": {"rot": (2 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))}, "tail2": {"rot": (3 * wave(t, cycles, 0.05), 0, amp * 1.6 * wave(t, cycles, -0.2))}}

	def idle(t):   # hangs in the air, rising and falling on slow beats
		return merge({"root": {"loc": (0, 0, 0.1 * wave(t, 1, 0.1))}, "body": {"rot": (3 * wave(t, 1, 0.3), 2 * wave(t, 1), 0)},
					  "head": {"rot": (-3 * wave(t, 1, 0.3), 0, 0)}}, fins(t, 1, 14), tail(t, 1))

	def walk(t):
		return merge({"root": {"loc": (0, 0, 0.08 * wave(t, 1, 0.1)), "rot": (-6, 0, 0)}}, fins(t, 1, 18), tail(t, 1, 8))

	def run(t):
		return merge({"root": {"loc": (0, 0, 0.06 * wave(t, 2, 0.1)), "rot": (-10, 0, 0)}}, fins(t, 2, 20), tail(t, 2, 6))

	def attack(t):   # lifts its head and wings, then slams down on its prey, wings sweeping
		rear = seq(t, [(0, 0), (0.35, 1), (0.55, -0.7), (0.8, -0.4), (1, 0)])
		w = seq(t, [(0, 0), (0.35, 40), (0.55, -36), (0.8, -20), (1, 0)])
		return merge({"root": {"loc": (0, -0.4 * max(0.0, -rear), 0.2 * rear - 0.3 * max(0.0, -rear)), "rot": (22 * rear, 0, 0)},
					  "head": {"rot": (-10 * rear, 0, 0)},
					  "wing_l": {"rot": (0, w, 0)}, "wing_r": {"rot": (0, -w, 0)}, "tip_l": {"rot": (0, w * 0.6, 0)}, "tip_r": {"rot": (0, -w * 0.6, 0)}},
					 tail(t, 1, 16))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, 0.2 * k, 0.1 * k), "rot": (14 * k, 16 * k, 0)}}, fins(t, 2, 20, 20 * k), tail(t, 2, 12))

	def death(t):   # the fins fold and fail and it falls flat on the salt, a last ripple through the wings
		f = seq(t, [(0.05, 0), (0.65, 1)])
		g = seq(t, [(0.55, 0), (0.9, 1)])
		flap = (1 - seq(t, [(0.1, 0), (0.6, 1)])) * 30 * wave(t, 3)
		return merge({"root": {"loc": (0, 0.1 * f, -(H - 0.14) * f), "rot": (-8 * f + 10 * g, 24 * f - 18 * g, 0)}},
					 {"wing_l": {"rot": (0, flap - 10 * g, 0)}, "wing_r": {"rot": (0, -flap - 12 * g, 0)},
					  "tip_l": {"rot": (0, -8 * g, 0)}, "tip_r": {"rot": (0, -6 * g, 0)},
					  "tail1": {"rot": (0, 0, 14 * g)}, "tail2": {"rot": (0, 0, 24 * g)}})

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 1.6, walk, True)
	clip(arm, "run", 1.0, run, True)
	clip(arm, "attack", 0.9, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


def side_(s):
	return "l" if s > 0 else "r"


def build_great_sky_ray():
	return build_sky_ray("great_sky_ray", True)


# ---------------------------------------------------------------- brine swarm

def build_brine_swarm():
	"""A cloud of pink brine shrimp risen out of the flats' water: some seventy little curled bodies
	whirling round on three orbits about a haze of pink, each orbit turning its own way."""
	import random
	rng = random.Random(681)
	pinks = [material("brine_swarm_pink", "f4909c", 0.5), material("brine_swarm_pink_d", "d86070", 0.5),
			 material("brine_swarm_pink_l", "ffc0c8", 0.5)]
	eye = material("brine_swarm_eye", "1a1012", 0.3)
	haze = glass_material("brine_swarm_haze", "ff9aa8", 0.16, 0.3, emit=0.3)
	Z = 1.0
	b = Builder("brine_swarm")
	b.bone("root", (0, 0, Z))
	b.bone("cloud", (0, 0, Z), "root")
	for k in range(3):
		b.bone(f"orbit_{k}", (0, 0, Z), "cloud")

	def shrimp(p, heading, size, bone):
		fwd = Vector((math.cos(heading), math.sin(heading), rng.uniform(-0.3, 0.3))).normalized()
		up = Vector((0, 0, 1))
		side = fwd.cross(up).normalized()
		pts = [p + fwd * size * 0.5, p + fwd * size * 0.1 + up * size * 0.12, p - fwd * size * 0.3 + up * size * 0.06,
			   p - fwd * size * 0.5 - up * size * 0.14]
		mat = pinks[rng.randrange(3)]
		for j, (a, c) in enumerate(zip(pts, pts[1:])):
			r = size * (0.16 - 0.04 * j)
			b.seg(tuple(a), tuple(c), r, r * 0.8, mat, bone, sides=5)
		tail = pts[-1]
		_slab(b, [tuple(tail), tuple(tail - fwd * size * 0.14 + side * size * 0.12 - up * size * 0.06),
				  tuple(tail - fwd * size * 0.14 - side * size * 0.12 - up * size * 0.06)], size * 0.03, mat)
		_on_bone(b, len(b.parts) - 1, bone)
		b.blob((size * 0.08,) * 3, tuple(pts[0] + side * size * 0.06), eye, bone, segs=(4, 3))
		for s in (1, -1):   # antennae
			b.seg(tuple(pts[0]), tuple(pts[0] + fwd * size * 0.4 + side * s * size * 0.2 + up * size * 0.1), size * 0.015, 0.0, mat, bone, sides=3)

	n = 0
	while n < 72:
		p = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
		if p.length > 1.0:
			continue
		p = Vector((p.x * 0.8, p.y * 0.8, p.z * 0.5 + 0.05))
		k = n % 3
		heading = math.atan2(p.y, p.x) + (math.pi / 2 if k != 1 else -math.pi / 2)   # swimming along its orbit
		shrimp(Vector((0, 0, Z)) + p, heading, rng.uniform(0.09, 0.14), f"orbit_{k}")
		n += 1
	for k in range(5):   # a haze of pink water hanging in the middle
		p = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), Z + rng.uniform(-0.15, 0.15)))
		r = rng.uniform(0.5, 0.8)
		b.blob((r, r, r * 0.7), tuple(p), haze, "cloud", segs=(10, 6))
	arm = b.build()

	def spin(t, turns, amp_z=0.0):
		# whole turns per clip (these clips export without the loop's closing key, so a spin is seamless)
		return {"orbit_0": {"rot": (6 * wave(t, 1), 0, 360 * turns * t)},
				"orbit_1": {"rot": (0, 8 * wave(t, 1, 0.3), -360 * turns * t)},
				"orbit_2": {"rot": (-6 * wave(t, 1, 0.5), 0, 360 * turns * t), "loc": (0, 0, amp_z * wave(t, 2))}}

	def idle(t):
		return merge(spin(t, 1, 0.08), {"cloud": {"loc": (0.05 * wave(t, 1), 0.05 * wave(t, 1, 0.25), 0.1 * wave(t, 2))}})

	def walk(t):
		return merge(spin(t, 1, 0.06), {"cloud": {"loc": (0, 0, 0.08 * wave(t, 2)), "rot": (-8, 0, 0)}})

	def run(t):
		return merge(spin(t, 1, 0.04), {"cloud": {"loc": (0, 0, 0.06 * wave(t, 2)), "rot": (-14, 0, 0)}})

	def attack(t):   # the swarm surges forward over its prey and draws back
		k = seq(t, [(0, 0), (0.3, -0.3), (0.55, 1), (1, 0)])
		return merge(spin(t, 1), {"cloud": {"loc": (0, -0.7 * max(0.0, k) + 0.2 * max(0.0, -k), -0.2 * max(0.0, k))}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge(spin(t, 1), {"cloud": {"loc": (0, 0.2 * k, 0.1 * k), "rot": (10 * k, 20 * k, 0)}})

	def death(t):   # the whirl slows and the shrimp rain down onto the salt
		f = seq(t, [(0.0, 0), (0.8, 1)])
		return {"cloud": {"loc": (0, 0, -(Z - 0.12) * f), "rot": (0, 0, 0)},
				"orbit_0": {"rot": (0, 0, 120 * f)}, "orbit_1": {"rot": (0, 0, -100 * f), "loc": (0, 0, 0.3 * f * (1 - f))},
				"orbit_2": {"rot": (0, 0, 80 * f)}, "root": {"loc": (0, 0, 0)}}

	# the spinning clips go without the loop's closing key (loop=False), so the last frame is a whole
	# turn on and the game's looping (CharacterModel.LOOPING) carries on from it without a backward spin
	clip(arm, "idle", 3.0, idle, False)
	clip(arm, "walk", 2.0, walk, False)
	clip(arm, "run", 1.4, run, False)
	clip(arm, "attack", 0.9, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4, death, False)
	return arm


# Dawnwatch / Mirror Flats: registered here, beside their builders
BODIES.update({"stonebrow_ogre_body": (KAYKIT + "Barbarian.glb", "stonebrow_ogre_texture", STONEBROW_CELLS, None),
			   "stonebrow_shaman_body": (KAYKIT + "Barbarian.glb", "stonebrow_shaman_texture", STONEBROW_SHAMAN_CELLS, None),
			   "stonebrow_warlord_body": (KAYKIT + "Barbarian.glb", "stonebrow_warlord_texture", STONEBROW_WARLORD_CELLS, None),
			   "fallen_sentinel_body": (KAYKIT + "Knight.glb", "fallen_sentinel_texture", None, ("fff6dc", "8a7a58")),
			   "knight_commander_body": (KAYKIT + "Knight.glb", "knight_commander_texture", None, ("fff2c4", "9a7a3a")),
			   "mirror_image_body": (KAYKIT + "Rogue.glb", "mirror_image_texture", None, ("ffffff", "7a8694")),
			   "the_reflection_body": (KAYKIT + "Rogue.glb", "the_reflection_texture", None, ("f4faff", "6a7e98")),
			   "duneskiff_body": (KAYKIT + "Rogue.glb", "duneskiff_texture", DUNESKIFF_CELLS, None),
			   "nomad_queen_body": (KAYKIT + "Rogue.glb", "nomad_queen_texture", NOMAD_QUEEN_CELLS, None)})
ATTACHMENTS.update({"sentinel_tabard": build_sentinel_tabard, "sentinel_eyes": build_sentinel_eyes, "commander_helm": build_commander_helm,
					"commander_banner": build_commander_banner, "duneskiff_wrap": build_duneskiff_wrap,
					"nomad_queen_headdress": build_nomad_queen_headdress, "salt_scimitar": build_salt_scimitar,
					"reflection_face": build_reflection_face,
					"stonebrow_club": lambda: _stonebrow_club("stonebrow_club", "club"),
					"stonebrow_skull_staff": lambda: _stonebrow_club("stonebrow_skull_staff", "staff")})
for _kind, _pre in (("ogre", "stonebrow"), ("shaman", "stonebrow_shaman"), ("warlord", "stonebrow_warlord")):
	ATTACHMENTS[f"{_pre}_head"] = (lambda n, k: lambda: _ogre_head(n, k))(f"{_pre}_head", _kind)
	ATTACHMENTS[f"{_pre}_chest"] = (lambda n, k: lambda: _ogre_chest(n, k))(f"{_pre}_chest", _kind)
	ATTACHMENTS[f"{_pre}_belly"] = (lambda n, k: lambda: _ogre_belly(n, k))(f"{_pre}_belly", _kind)
	for _s, _side in ((1, "l"), (-1, "r")):
		ATTACHMENTS[f"{_pre}_arm_{_side}"] = (lambda n, s, k: lambda: _ogre_arm(n, s, k))(f"{_pre}_arm_{_side}", _s, _kind)
		ATTACHMENTS[f"{_pre}_bracer_{_side}"] = (lambda n, s, k: lambda: _ogre_bracer(n, s, k))(f"{_pre}_bracer_{_side}", _s, _kind)
CREATURES.update({"roc": build_roc, "great_roc": build_great_roc, "wyvern": build_wyvern, "snow_spirit": build_snow_spirit,
				  "avalanche_elemental": build_avalanche_elemental, "storm_crowned_spirit": build_storm_crowned_spirit,
				  "mirage_wisp": build_mirage_wisp, "salt_crab": build_salt_crab, "old_saltclaw": build_old_saltclaw,
				  "brine_swarm": build_brine_swarm, "salt_wader": build_salt_wader, "sky_ray": build_sky_ray,
				  "great_sky_ray": build_great_sky_ray})
# ================================================================ end of Dawnwatch / Mirror Flats


# ================================================================ Silted Reach / Tidemouth (the Long Monsoon, 24-30)
# Jalendra's river delta and Rainhold's harbor at its mouth. The folk are repainted KayKit bodies with
# bolt-ons in their mesh space: whiskerfolk (catfish-headed river giants) and their river king, mudfolk and
# their mud-shaman, drowned smugglers and their captain, saltreavers (sea raiders) and their king, clawfolk
# (crab-men). Their weapons (trident, driftwood staff, cutlass, whalebone axe) are models.json "weapons".
# The beasts are own-rig: the river hippo, four serpents on one frame, the biting swarm, the deep horror,
# the giant gull, the sea lion and the tempest lord.

def _rmats(p, spec):
	"""Materials from {key: (hex, roughness[, emission])}, named `p`_key."""
	return {k: material(f"{p}_{k}", v[0], v[1], v[2] if len(v) > 2 else 0.0) for k, v in spec.items()}


def _chain(b, pts, r0, r1, mat, bone="x", sides=6):
	"""Tapered segments through `pts`, from radius r0 at the first point to r1 at the last."""
	n = len(pts) - 1
	for k in range(n):
		a = r0 + (r1 - r0) * k / n
		c = r0 + (r1 - r0) * (k + 1) / n
		b.seg(tuple(pts[k]), tuple(pts[k + 1]), a, c, mat, bone, sides=sides)


def _lift(a, th):
	"""(pitch, roll, 0) that raises a limb pointing along angle `a` (radians, in the ground plane) by `th` degrees."""
	return (-th * math.sin(a), th * math.cos(a), 0)


# ---- whiskerfolk and the river king (the barbarian: slick gray-green hide, catfish heads)

# barbarian cells: skin (0,0) (1,3) (3,1), trousers (7,1) bare legs, boots (3,2) webbed feet, vest (7,0) netting,
# fur trim (2,1) reed, leather (6,0) (6,1) (5,1), metal (3,0), hand wraps (7,2)
WHISKERFOLK_CELLS = {(0, 0): ("8ea294", "3c4c46"), (1, 3): ("8ea294", "3c4c46"), (3, 1): ("8a9e90", "3a4a44"),
					 (7, 1): ("7e9284", "34423c"), (3, 2): ("5e6e66", "26302c"), (7, 0): ("7a6a48", "2e2616"),
					 (2, 1): ("b0a262", "5a4e26"), (6, 0): ("5e4c34", "221a10"), (6, 1): ("5e4c34", "221a10"),
					 (5, 1): ("5e4c34", "221a10"), (3, 0): ("8a9a90", "3a443e"), (7, 2): ("8ea294", "3c4c46")}
RIVER_KING_CELLS = {(0, 0): ("6e8478", "26342e"), (1, 3): ("6e8478", "26342e"), (3, 1): ("6a8074", "24322c"),
					(7, 1): ("5e7468", "202c26"), (3, 2): ("4a5a52", "1a2420"), (7, 0): ("3e8a80", "123a36"),
					(2, 1): ("c8b060", "6a5420"), (6, 0): ("4a3e2a", "1a140a"), (6, 1): ("4a3e2a", "1a140a"),
					(5, 1): ("3e8a80", "123a36"), (3, 0): ("e8eee8", "8a9a94"), (7, 2): ("6e8478", "26342e")}


def whisker_materials(king=False):
	p = "river_king" if king else "whiskerfolk"
	return _rmats(p, {"skin": ("6e8478" if king else "8ea294", 0.3), "skin_d": ("3e5048" if king else "5a6e62", 0.35),
					  "belly": ("b4c2ae" if king else "c0ccb8", 0.4), "mouth": ("2a1e22", 0.6), "lip": ("b8b8a0", 0.35),
					  "eye": ("e8c848", 0.2, 0.6), "pupil": ("0a0a08", 0.2), "barbel": ("4e6258" if king else "6a7e72", 0.35),
					  "spot": ("4a5a50" if king else "6a7e70", 0.35), "fin": ("5e7a6a", 0.5), "fin_d": ("34463c", 0.6),
					  "net": ("8a7a52", 0.9), "cord": ("6a5a3a", 0.9), "float": ("c89a5a", 0.8), "reed": ("c8b464", 0.8),
					  "reed_g": ("6e8a3a", 0.8), "cattail": ("5a3a22", 0.9), "pearl": ("f4f6ee", 0.15, 0.4),
					  "pearl_t": ("7ae8d8", 0.15, 1.6), "shell": ("e8d4c0", 0.5), "shell_d": ("a88a70", 0.6),
					  "kelp": ("3e5a2a", 0.8), "fish": ("a8b4a8", 0.35), "fish_d": ("5a6458", 0.45),
					  "barnacle": ("c8c2b0", 0.7), "hole": ("3a3630", 0.8)})


def _whisker_head(b, m, king):
	import random
	rng = random.Random(611 + king)
	sk, dk = m["skin"], m["skin_d"]
	b.seg((0, 0.02, 1.2), (0, -0.04, 1.42), 0.32, 0.36, sk, "x", sides=10)                       # a thick neck
	b.blob((1.02, 0.88, 0.5), (0, 0.02, 1.56), sk, "x", segs=(14, 9))                           # a broad, flat skull
	b.blob((0.9, 0.72, 0.2), (0, 0.08, 1.76), dk, "x", segs=(12, 6))                            # the dark back of the head
	b.blob((0.98, 0.42, 0.3), (0, -0.3, 1.5), sk, "x", segs=(12, 7))                            # the wide, blunt snout
	b.blob((0.9, 0.64, 0.26), (0, -0.14, 1.32), m["belly"], "x", segs=(12, 7))                  # pale throat
	b.blob((0.86, 0.12, 0.09), (0, -0.5, 1.41), m["mouth"], "x", segs=(12, 4))                  # the mouth, the width of the face
	b.blob((0.92, 0.14, 0.07), (0, -0.49, 1.46), m["lip"], "x", segs=(12, 4))
	b.blob((0.84, 0.14, 0.07), (0, -0.47, 1.35), m["lip"], "x", segs=(12, 4))
	for s in (1, -1):
		b.blob((0.14, 0.11, 0.13), (0.4 * s, -0.3, 1.62), m["eye"], "x", segs=(8, 5))            # small eyes, far apart
		b.blob((0.05, 0.05, 0.09), (0.44 * s, -0.33, 1.62), m["pupil"], "x", segs=(5, 3))
		b.blob((0.09, 0.07, 0.05), (0.14 * s, -0.47, 1.57), m["hole"], "x", segs=(5, 3))          # nostrils
		for k in range(3):   # gill slits
			b.seg((0.47 * s, -0.08 + 0.08 * k, 1.46), (0.45 * s, -0.04 + 0.08 * k, 1.3), 0.018, 0.012, dk, "x", sides=4)
		# the long barbels from the corners of the mouth, and short ones by the nostrils and under the chin
		ln = 1.3 if king else 1.0
		pts = [Vector((0.42 * s, -0.49, 1.45)), Vector((0.64 * s, -0.6, 1.45)), Vector((0.8 * s, -0.62, 1.3))]
		pts += [pts[-1] + Vector((0.04 * s, 0.05, -0.24 * ln)), pts[-1] + Vector((0.0, 0.1, -0.46 * ln))]
		_chain(b, pts, 0.05, 0.012, m["barbel"], sides=6)
		if king:   # pearls threaded on the king's barbels
			b.blob((0.09, 0.09, 0.09), tuple(pts[-1]), m["pearl"], "x", segs=(8, 6))
			b.blob((0.07, 0.07, 0.07), tuple(pts[-2]), m["pearl"], "x", segs=(8, 6))
		_chain(b, [(0.15 * s, -0.5, 1.58), (0.24 * s, -0.66, 1.68), (0.32 * s, -0.76, 1.64)], 0.03, 0.008, m["barbel"], sides=5)
		for x in (0.1, 0.24):
			_chain(b, [(x * s, -0.42, 1.24), (x * 1.1 * s, -0.48, 1.06), (x * 1.25 * s, -0.44, 0.9)], 0.028, 0.008, m["barbel"], sides=5)
	for k in range(9):   # mottles over the crown
		a = rng.uniform(0, 2 * math.pi)
		r = rng.uniform(0.1, 0.4)
		p, n = _on_dome((0, 0.02, 1.56), (0.51, 0.44, 0.25), r * math.cos(a), 0.02 + r * math.sin(a) * 0.9)
		_oblob(b, (0.1, 0.13, 0.02), tuple(p), n.orthogonal(), tuple(n), m["spot"], "x", segs=(6, 3))
	if not king:
		return
	# the king's crown: a band of braided kelp, reeds and cattails standing round it, river pearls between
	_wrap(b, (0, 0.06, 1.8), (0.47, 0.39), 0.08, 0.04, m["kelp"], sides=18)
	for k in range(12):
		a = 2 * math.pi * k / 12 - math.pi / 2
		base = Vector((0.49 * math.cos(a), 0.06 + 0.41 * math.sin(a), 1.8))
		out = Vector((math.cos(a), math.sin(a), 0))
		if k % 2 == 0:
			tall = 0.62 if k == 0 else 0.44 + 0.06 * rng.uniform(-1, 1)
			tip = base + out * 0.12 + Vector((0, 0, tall))
			b.seg(tuple(base), tuple(tip), 0.025, 0.012, m["reed_g"] if k % 4 else m["reed"], "x", sides=5)
			if k % 4 == 0:
				b.blob((0.07, 0.07, 0.16), tuple(tip - out * 0.01 + Vector((0, 0, -0.06))), m["cattail"], "x", segs=(6, 5))
		else:
			b.blob((0.1, 0.1, 0.1), tuple(base + out * 0.03 + Vector((0, 0, 0.04))), m["pearl"], "x", segs=(8, 6))
	b.blob((0.2, 0.08, 0.16), (0, -0.4, 1.82), m["shell"], "x", segs=(10, 6))                  # a teal pearl in a clam shell
	b.blob((0.13, 0.12, 0.13), (0, -0.44, 1.84), m["pearl_t"], "x", segs=(10, 7))


def _whisker_chest(b, m, king):
	sk = m["skin"]
	b.blob((0.86, 0.42, 0.5), (0, 0.18, 1.2), sk, "x", segs=(12, 8))                              # a hump of muscle
	b.blob((0.66, 0.16, 0.5), (0, -0.31, 0.9), m["belly"], "x", segs=(12, 8))                    # the pale belly
	# the dorsal fin down the back, spines through a web
	_slab(b, [(0, 0.3, 1.44), (0, 0.56, 1.4), (0, 0.66, 1.06), (0, 0.44, 0.84)], 0.03, m["fin"])
	for k in range(5):
		u = k / 4
		base = (0, 0.34 + 0.08 * u, 1.42 - 0.56 * u)
		tip = (0, 0.6 + 0.08 * math.sin(math.pi * u), 1.44 - 0.56 * u)
		b.seg(base, tip, 0.03, 0.008, m["fin_d"], "x", sides=4)
	if not king:
		# a fishing net slung from the left shoulder to the right hip, cork floats knotted on it
		for dx in (0.0, 0.08):
			b.seg((0.34 - dx, -0.36, 1.34), (-0.34 - dx, -0.42, 0.72), 0.02, 0.02, m["net"], "x", sides=4)
			b.seg((0.34 - dx, 0.36, 1.34), (-0.34 - dx, 0.4, 0.72), 0.02, 0.02, m["net"], "x", sides=4)
		for k in range(6):
			u = k / 5
			p = Vector((0.3 - 0.64 * u, -0.38 - 0.04 * u, 1.3 - 0.58 * u))
			b.seg(tuple(p), tuple(p + Vector((0.1, -0.01, 0.0))), 0.012, 0.012, m["cord"], "x", sides=4)
			if k % 2:
				b.blob((0.1, 0.07, 0.07), tuple(p + Vector((0.04, -0.04, 0))), m["float"], "x", segs=(6, 4))
		b.seg((0.34, -0.36, 1.34), (0.4, 0.0, 1.4), 0.03, 0.03, m["net"], "x", sides=4)
		b.seg((0.4, 0.0, 1.4), (0.34, 0.36, 1.34), 0.03, 0.03, m["net"], "x", sides=4)
		_barnacle(b, (0.36, 0.1, 1.38), (0.6, 0.2, 1), m, 0.9)
		return
	# the king: a mantle of woven reeds over the shoulders, shells sewn on it, a rope of pearls at the throat
	_shell(b, (1.22, 1.02, 0.9), (0, 0.06, 1.18), m["reed"], lambda d: d.z > -0.05 and not (d.y < -0.5 and abs(d.x) < 0.55))
	for k in range(13):   # the woven rows
		a = math.radians(20 + k * 11)
		for z, r in ((1.3, 0.56), (1.42, 0.46)):
			p = (r * math.cos(a) * 1.1, 0.06 + r * math.sin(a), z)
			b.blob((0.1, 0.1, 0.03), p, m["reed_g"], "x", segs=(5, 3))
	for s in (1, -1):
		for y, z in ((-0.1, 1.44), (0.2, 1.4), (0.36, 1.22)):
			_oblob(b, (0.16, 0.14, 0.04), (0.5 * s, y, z), (0, 0, 1), (s, 0, 0.4), m["shell"], "x", segs=(8, 4))
	for k in range(15):
		a = math.pi + math.pi * k / 14
		b.blob((0.075, 0.075, 0.075), (0.4 * math.cos(a), 0.4 * math.sin(a) - 0.02, 1.32 + 0.18 * math.sin(a)), m["pearl"], "x", segs=(6, 4))
	b.blob((0.16, 0.14, 0.16), (0, -0.46, 1.1), m["pearl_t"], "x", segs=(10, 7))


def _whisker_hips(b, m, king):
	_wrap(b, (0, 0.0, 0.66), (0.47, 0.41), 0.08, 0.04, m["cord"] if not king else m["kelp"], sides=18)
	if not king:
		_slab(b, [(-0.24, -0.44, 0.66), (0.24, -0.44, 0.66), (0.18, -0.47, 0.3), (-0.18, -0.47, 0.3)], 0.03, m["net"])
		for x in (-0.12, 0.0, 0.12):
			b.seg((x, -0.47, 0.64), (x * 0.8, -0.49, 0.3), 0.012, 0.012, m["cord"], "x", sides=4)
		# a fish hung at the hip by its gills
		b.seg((0.46, -0.1, 0.66), (0.48, -0.12, 0.54), 0.012, 0.012, m["cord"], "x", sides=4)
		b.blob((0.07, 0.12, 0.3), (0.5, -0.12, 0.4), m["fish"], "x", segs=(8, 6))
		b.blob((0.05, 0.1, 0.16), (0.5, -0.1, 0.46), m["fish_d"], "x", segs=(6, 4))
		_slab(b, [(0.5, -0.12, 0.26), (0.5, -0.2, 0.16), (0.5, -0.04, 0.16)], 0.02, m["fish_d"])
	else:
		for k in range(14):   # a skirt of kelp strands and reeds
			a = math.radians(k * 360 / 14 + 5)
			top = (0.49 * math.cos(a), 0.43 * math.sin(a), 0.64)
			_kelp(b, top, 0.4 if k % 2 else 0.32, m["kelp"] if k % 3 else m["reed_g"], lean=(0.08 * math.cos(a), 0.08 * math.sin(a)), width=0.03)
		b.blob((0.22, 0.08, 0.18), (0, -0.46, 0.66), m["shell"], "x", segs=(10, 6))
		b.blob((0.1, 0.06, 0.1), (0, -0.5, 0.66), m["pearl"], "x", segs=(6, 4))
	for s in (1, -1):
		_kelp(b, (0.3 * s, 0.36, 0.64), 0.26, m["kelp"], width=0.035, parts=2)


def _whisker_part(name, fn, king):
	b = Builder(name)
	fn(b, whisker_materials(king), king)
	return b.build_static()


def build_river_trident():
	"""The river king's trident, in the KayKit weapons' frame (grip at the origin, up +Z, prongs across X):
	a verdigris bronze head on a driftwood haft, pearls set at the fork, a kelp streamer."""
	m = _rmats("river_trident", {"wood": ("7a6a52", 0.9), "wood_d": ("4a3e2e", 0.9), "bronze": ("5aa08a", 0.45),
								  "bronze_d": ("2e6a5a", 0.5), "gold": ("c8a860", 0.35), "pearl": ("f4f6ee", 0.15, 0.4),
								  "pearl_t": ("7ae8d8", 0.15, 1.6), "kelp": ("3e5a2a", 0.8)})
	b = Builder("river_trident")
	_chain(b, [(0, 0, -0.9), (0.01, 0, -0.3), (-0.01, 0, 0.4), (0, 0, 1.3)], 0.045, 0.04, m["wood"], sides=8)
	for z in (-0.16, 0.1, 0.9):
		b.seg((0, 0, z), (0, 0, z + 0.12), 0.05, 0.05, m["wood_d"], "x", sides=8)
	b.seg((0, 0, 1.26), (0, 0, 1.42), 0.07, 0.06, m["bronze_d"], "x", sides=8)                       # the socket
	b.seg((-0.3, 0, 1.44), (0.3, 0, 1.44), 0.05, 0.05, m["bronze"], "x", sides=8)                    # the crossbar
	b.seg((0, 0, 1.4), (0, 0, 2.0), 0.05, 0.0, m["bronze"], "x", sides=6)                            # the middle prong
	for s in (1, -1):
		_chain(b, [(0.3 * s, 0, 1.42), (0.33 * s, 0, 1.62), (0.3 * s, 0, 1.86)], 0.045, 0.0, m["bronze"], sides=6)
		b.seg((0.31 * s, 0, 1.72), (0.22 * s, 0, 1.62), 0.025, 0.0, m["bronze_d"], "x", sides=4)       # barbs
		b.blob((0.07, 0.07, 0.07), (0.16 * s, -0.03, 1.46), m["pearl"], "x", segs=(6, 4))
	b.seg((0, 0, 1.78), (0.09, 0, 1.7), 0.025, 0.0, m["bronze_d"], "x", sides=4)
	b.blob((0.12, 0.1, 0.12), (0, -0.04, 1.46), m["pearl_t"], "x", segs=(8, 6))
	b.blob((0.18, 0.08, 0.1), (0, 0, 1.46), m["gold"], "x", segs=(8, 5))
	_kelp(b, (0.05, 0, 1.3), 0.5, m["kelp"], lean=(0.2, 0.0), width=0.035)
	return b.build_static()


# ---- mudfolk and the mud-shaman (the barbarian, squat and mud-caked, masks of stick and mud)

MUDFOLK_CELLS = {(0, 0): ("8a6a4a", "3a2818"), (1, 3): ("8a6a4a", "3a2818"), (3, 1): ("866646", "362616"),
				 (7, 1): ("7a5c40", "302214"), (3, 2): ("5a4230", "20160c"), (7, 0): ("a8906a", "54402a"),
				 (2, 1): ("b09a5a", "5a4a24"), (6, 0): ("5a4430", "1e140a"), (6, 1): ("5a4430", "1e140a"),
				 (5, 1): ("5a4430", "1e140a"), (3, 0): ("6a5a48", "2a2018"), (7, 2): ("7a5a3e", "2a1c10")}
MUD_SHAMAN_CELLS = {(0, 0): ("6e6a48", "2a2814"), (1, 3): ("6e6a48", "2a2814"), (3, 1): ("6a6644", "282612"),
					(7, 1): ("5e5a3c", "222010"), (3, 2): ("4a4430", "1a160c"), (7, 0): ("8a7a44", "3a3218"),
					(2, 1): ("4a9a8a", "1a3a34"), (6, 0): ("4a3a2a", "1a120a"), (6, 1): ("4a3a2a", "1a120a"),
					(5, 1): ("4a9a8a", "1a3a34"), (3, 0): ("e8dcc0", "8a7e64"), (7, 2): ("6e6a48", "2a2814")}


def mud_materials(shaman=False):
	p = "mud_shaman" if shaman else "mudfolk"
	return _rmats(p, {"mud": ("6e6a48" if shaman else "7a5a3c", 0.95), "mud_d": ("46402a" if shaman else "4a3422", 0.95),
					  "mud_l": ("a8906a", 0.95), "mud_wet": ("4a3826", 0.35), "stick": ("8a6a44", 0.9), "stick_d": ("5a4028", 0.9),
					  "twine": ("b09a5a", 0.9), "hole": ("140c06", 0.9), "eye": ("f0b030", 0.3, 2.2),
					  "reed": ("b0a060", 0.85), "reed_g": ("6a8038", 0.85), "shell": ("f0e4d4", 0.45), "shell_p": ("e8b8a8", 0.45),
					  "shell_d": ("a88a70", 0.6), "bone": ("e8dcc0", 0.7), "feather": ("dcdcd4", 0.8), "feather_d": ("4a4a50", 0.8),
					  "teal": ("3aa898", 0.6), "glow": ("6affe0", 0.2, 3.0)})


def _mud_head(b, m, shaman):
	import random
	rng = random.Random(631 + shaman)
	b.seg((0, 0.0, 1.16), (0, -0.02, 1.4), 0.27, 0.3, m["mud"], "x", sides=10)
	b.blob((0.8, 0.76, 0.72), (0, 0.02, 1.64), m["mud"], "x", segs=(12, 9))                       # a round, lumpy head
	for k in range(8):   # caked clods
		a = rng.uniform(math.radians(-30), math.radians(210))
		e = rng.uniform(-0.2, 0.9)
		d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e) + 0.2, math.sin(e)))
		_rock(b, (0.2, 0.2, 0.14), tuple(Vector((0, 0.02, 1.64)) + Vector((0.38 * d.x, 0.36 * d.y, 0.34 * d.z))),
			  m["mud_d"] if k % 2 else m["mud_l"], "x", rng)
	for s in (1, -1):
		b.blob((0.14, 0.16, 0.2), (0.4 * s, 0.02, 1.62), m["mud"], "x", segs=(6, 5))              # stubby ears
	# the mask: a slab of dried mud over the face, cracked, with holes for the eyes and mouth
	_oblob(b, (0.66, 0.8, 0.12), (0, -0.37, 1.62), (0, 0, 1), (0, -1, 0), m["mud_l"], "x", segs=(12, 8))
	for p, q in (((-0.2, -0.43, 1.94), (-0.1, -0.44, 1.82)), ((0.24, -0.43, 1.4), (0.16, -0.44, 1.5)),
				 ((0.26, -0.43, 1.86), (0.3, -0.42, 1.74))):
		b.seg(p, q, 0.01, 0.008, m["mud_d"], "x", sides=4)
	for s in (1, -1):
		b.blob((0.16, 0.06, 0.13), (0.14 * s, -0.42, 1.7), m["hole"], "x", segs=(8, 5))
		b.blob((0.06, 0.03, 0.05), (0.14 * s, -0.445, 1.7), m["eye"], "x", segs=(6, 4))
	b.blob((0.22, 0.05, 0.07), (0, -0.425, 1.44), m["hole"], "x", segs=(8, 4))
	if not shaman:
		# sticks lashed across it: a brow bar and two cheek bars, a fan of twigs rising behind like a dam
		b.seg((-0.46, -0.46, 1.84), (0.46, -0.46, 1.84), 0.03, 0.028, m["stick"], "x", sides=5)
		for s in (1, -1):
			b.seg((0.3 * s, -0.47, 1.98), (0.28 * s, -0.47, 1.3), 0.026, 0.022, m["stick_d"], "x", sides=5)
			b.blob((0.07, 0.05, 0.07), (0.29 * s, -0.49, 1.84), m["twine"], "x", segs=(5, 4))
		for k in range(7):
			x = (k - 3) * 0.1
			base = (x, -0.12, 1.9)
			tip = (x * 2.2, 0.0 + 0.04 * (k % 2), 2.32 - 0.05 * abs(k - 3))
			b.seg(base, tip, 0.024, 0.012, m["stick"] if k % 2 else m["stick_d"], "x", sides=4)
		b.seg((-0.5, -0.04, 2.14), (0.5, -0.04, 2.14), 0.018, 0.016, m["stick_d"], "x", sides=4)
		b.blob((0.3, 0.2, 0.12), (0.1, -0.1, 1.98), m["mud_wet"], "x", segs=(8, 5))
		return
	# the mud-shaman's mask is shingled with shells, cowries round the eyes, a reed beard beneath,
	# heron feathers and a bird's skull above
	for row, (z, xs) in enumerate(((1.92, (-0.2, 0.0, 0.2)), (1.82, (-0.28, 0.0, 0.28)), (1.56, (-0.26, -0.13, 0.13, 0.26)),
									(1.48, (-0.22, 0.22)), (1.34, (-0.14, 0.0, 0.14)))):
		for k, x in enumerate(xs):
			y = -0.44 + 0.02 * abs(x) / 0.3
			mat = m["shell_p"] if (row + k) % 3 == 0 else m["shell"]
			_oblob(b, (0.15, 0.13, 0.035), (x, y, z), (0, 0.2, 1), (0, -1, 0.1), mat, "x", segs=(8, 4))
			b.seg((x, y - 0.02, z - 0.05), (x, y - 0.02, z + 0.05), 0.012, 0.012, m["shell_d"], "x", sides=4)
	for s in (1, -1):
		for k in range(6):
			a = 2 * math.pi * k / 6
			b.blob((0.045, 0.03, 0.035), (0.14 * s + 0.11 * math.cos(a), -0.45, 1.7 + 0.09 * math.sin(a)), m["shell"], "x", segs=(5, 3))
		b.blob((0.08, 0.04, 0.07), (0.14 * s, -0.445, 1.7), m["glow"], "x", segs=(6, 4))
	for k in range(9):
		x = (k - 4) * 0.055
		_kelp(b, (x, -0.42, 1.3), 0.34 - 0.03 * abs(k - 4), m["reed"] if k % 2 else m["reed_g"], lean=(x * 0.3, -0.1), width=0.022)
	for k in range(5):
		a = math.radians(-50 + 25 * k)
		base = Vector((0.2 * math.sin(a), 0.06, 1.94))
		d = Vector((math.sin(a) * 0.5, 0.3, 1)).normalized()
		ln = 0.62 - 0.08 * abs(k - 2)
		_oblob(b, (0.08, ln, 0.02), tuple(base + d * ln * 0.5), tuple(d), (0, -1, 0), m["feather"] if k % 2 else m["feather_d"], "x", segs=(6, 3))
		b.seg(tuple(base), tuple(base + d * ln), 0.008, 0.004, m["bone"], "x", sides=3)
	b.blob((0.16, 0.2, 0.14), (0, -0.28, 2.02), m["bone"], "x", segs=(8, 6))                    # a heron's skull at the brow
	b.seg((0, -0.36, 2.0), (0, -0.62, 1.94), 0.035, 0.0, m["bone"], "x", sides=5)
	for s in (1, -1):
		b.blob((0.05, 0.03, 0.05), (0.05 * s, -0.36, 2.04), m["hole"], "x", segs=(5, 3))
	b.blob((0.44, 0.1, 0.1), (0, -0.4, 1.99), m["teal"], "x", segs=(8, 4))                      # a band of teal paint


def _mud_chest(b, m, shaman):
	import random
	rng = random.Random(641 + shaman)
	for s in (1, -1):   # clods of mud on the shoulders and drips down the chest
		for k in range(3):
			_rock(b, (0.22, 0.24, 0.14), (0.3 * s + rng.uniform(-0.06, 0.06), rng.uniform(-0.2, 0.2), 1.34), m["mud_d"], "x", rng)
	for x, z, ln in ((0.18, 1.24, 0.3), (-0.08, 1.2, 0.22), (0.3, 1.16, 0.18), (-0.24, 1.22, 0.26)):
		b.blob((0.07, 0.05, ln), (x, -0.385, z - ln / 2), m["mud_wet"], "x", segs=(6, 5))
		b.blob((0.08, 0.06, 0.08), (x, -0.39, z - ln), m["mud_wet"], "x", segs=(6, 4))
	if not shaman:
		# a bundle of sticks for the dam, tied on the back
		for k in range(7):
			dx = (k - 3) * 0.045
			b.seg((0.3 + dx, 0.44 + 0.02 * (k % 2), 1.36 - dx), (-0.36 + dx, 0.44 + 0.02 * (k % 2), 0.72 - dx), 0.028, 0.024,
				  m["stick"] if k % 2 else m["stick_d"], "x", sides=5)
		for u in (0.3, 0.7):
			p = Vector((0.3, 0.44, 1.36)).lerp(Vector((-0.36, 0.44, 0.72)), u)
			b.blob((0.12, 0.16, 0.12), tuple(p), m["twine"], "x", segs=(6, 4))
		b.seg((0.3, 0.44, 1.3), (0.34, -0.3, 1.3), 0.018, 0.018, m["twine"], "x", sides=4)      # the carrying cord
		b.seg((0.34, -0.3, 1.3), (-0.28, -0.4, 0.82), 0.018, 0.018, m["twine"], "x", sides=4)
		return
	# a cloak of woven reeds on the back and a shell necklace
	_shell(b, (1.04, 0.96, 1.6), (0, 0.1, 0.9), m["reed"], lambda d: d.y > 0.15 and -0.3 < d.z < 0.55, segs=(16, 14))
	for k in range(7):
		a = math.radians(40 + k * 16.6)
		b.seg((0.5 * math.cos(a), 0.1 + 0.46 * math.sin(a), 1.25), (0.54 * math.cos(a), 0.12 + 0.5 * math.sin(a), 0.68), 0.012, 0.012,
			  m["reed_g"], "x", sides=4)
	pts = []
	for k in range(13):
		a = math.pi + math.pi * k / 12
		pts.append((0.38 * math.cos(a), 0.38 * math.sin(a) - 0.02, 1.3 + 0.2 * math.sin(a)))
	for p, q in zip(pts, pts[1:]):
		b.seg(p, q, 0.014, 0.014, m["twine"], "x", sides=4)
	for k in (2, 4, 6, 8, 10):
		p = pts[k]
		_oblob(b, (0.1, 0.12, 0.03), (p[0], p[1] - 0.03, p[2] - 0.06), (0, 0, -1), (0, -1, 0), m["shell_p"] if k == 6 else m["shell"], "x", segs=(6, 4))
	b.blob((0.1, 0.08, 0.1), (0, -0.44, 1.02), m["glow"], "x", segs=(6, 4))
	b.blob((0.12, 0.06, 0.12), (0, -0.42, 1.02), m["bone"], "x", segs=(6, 4))


def _mud_hips(b, m, shaman):
	_wrap(b, (0, 0.0, 0.66), (0.47, 0.41), 0.06, 0.03, m["twine"], sides=18)
	for k in range(16):   # a skirt of reeds and grass
		a = math.radians(k * 22.5 + 8)
		root = (0.48 * math.cos(a), 0.42 * math.sin(a), 0.66)
		_tuft(b, root, (0.25 * math.cos(a), 0.25 * math.sin(a), -1), 0.34, 4, 0.18, [m["reed"], m["reed_g"]], 650 + k, width=0.03)
	b.blob((0.16, 0.12, 0.18), (0.4, -0.22, 0.54), m["mud_d"], "x", segs=(8, 6))                 # a mud pouch
	if shaman:
		for x in (-0.16, 0.0, 0.16):
			_oblob(b, (0.1, 0.12, 0.03), (x, -0.46, 0.6), (0, 0, -1), (0, -1, 0), m["shell"], "x", segs=(6, 4))
		b.blob((0.1, 0.06, 0.1), (0.16, -0.48, 0.48), m["bone"], "x", segs=(6, 4))


def _mud_part(name, fn, shaman):
	b = Builder(name)
	fn(b, mud_materials(shaman), shaman)
	return b.build_static()


def build_driftwood_staff():
	"""The mud-shaman's staff: gnarled silver driftwood forking at the top round a glowing teal stone,
	a fish skull and a string of vertebrae hung from the fork, shells on cords (KayKit weapons' frame)."""
	m = _rmats("driftwood_staff", {"wood": ("b8b0a0", 0.9), "wood_d": ("7a7468", 0.9), "twine": ("b09a5a", 0.9),
									"bone": ("e8dcc0", 0.7), "hole": ("1a140e", 0.9), "shell": ("f0e4d4", 0.45),
									"glow": ("6affe0", 0.2, 3.5), "teal": ("3aa898", 0.6)})
	b = Builder("driftwood_staff")
	_chain(b, [(0, 0, -0.9), (0.04, 0.01, -0.4), (-0.03, 0, 0.2), (0.04, -0.02, 0.72), (0.0, 0, 1.08)], 0.05, 0.042, m["wood"], sides=7)
	for p in ((0.04, 0.01, -0.4), (0.04, -0.02, 0.72)):   # knots
		b.blob((0.12, 0.11, 0.1), p, m["wood_d"], "x", segs=(6, 4))
	for s in (1, -1):   # the fork
		_chain(b, [(0, 0, 1.06), (0.1 * s, 0, 1.24), (0.12 * s, 0.01, 1.44), (0.08 * s, 0, 1.56)], 0.04, 0.012, m["wood"], sides=6)
	b.blob((0.16, 0.14, 0.2), (0, 0, 1.3), m["glow"], "x", segs=(8, 6))
	for z in (1.2, 1.38):
		b.seg((-0.11, 0, z), (0.11, 0, z + 0.02), 0.014, 0.014, m["twine"], "x", sides=4)
	b.seg((0, 0, -0.02), (0, 0, 0.16), 0.056, 0.056, m["twine"], "x", sides=7)                     # the grip binding
	# a fish skull and vertebrae hung from the left tine, shells from the right
	b.seg((0.12, 0, 1.4), (0.2, 0, 1.2), 0.008, 0.008, m["twine"], "x", sides=3)
	b.blob((0.1, 0.16, 0.12), (0.21, 0, 1.12), m["bone"], "x", segs=(8, 6))
	b.seg((0.21, -0.07, 1.1), (0.21, -0.14, 1.06), 0.03, 0.0, m["bone"], "x", sides=4)
	b.blob((0.03, 0.03, 0.03), (0.25, -0.04, 1.15), m["hole"], "x", segs=(4, 3))
	for k in range(5):
		b.blob((0.05, 0.05, 0.035), (0.21, 0, 1.02 - 0.05 * k), m["bone"], "x", segs=(6, 3))
	for k, dz in enumerate((0.14, 0.24)):
		p = (-0.12, 0.01 * k, 1.42 - dz)
		b.seg((-0.12, 0, 1.42), p, 0.007, 0.007, m["twine"], "x", sides=3)
		_oblob(b, (0.07, 0.08, 0.02), p, (0, 0, -1), (0, -1, 0), m["shell"], "x", segs=(6, 3))
	b.seg((-0.04, -0.045, 0.4), (0.04, -0.045, 0.6), 0.012, 0.012, m["teal"], "x", sides=4)         # painted marks
	b.seg((0.04, -0.045, 0.4), (-0.04, -0.045, 0.6), 0.012, 0.012, m["teal"], "x", sides=4)
	return b.build_static()


# ---- drowned smugglers and their captain (the rogue, gone pale teal under the water)

# rogue cells: tunic (0,1), collar and cape (1,1), bracers and belt (5,0), buckles (3,0) (6,0), trousers (7,1),
# boots (3,2), gloves (7,2), skin (0,0), hair (1,0)
SMUGGLER_CELLS = {(0, 0): ("b4dcd0", "4a7a72"), (1, 0): ("2e4440", "0e1a18"), (0, 1): ("8aa8a0", "3a524c"),
				  (1, 1): ("5e7a74", "243632"), (5, 0): ("4a4a3a", "1a1a12"), (3, 0): ("a8a47a", "4a4a30"),
				  (6, 0): ("a8a47a", "4a4a30"), (7, 1): ("6a7e7a", "283432"), (3, 2): ("3e4e4a", "141c1a"),
				  (7, 2): ("5a6a66", "202a28")}
SMUGGLER_CAPTAIN_CELLS = {(0, 0): ("a8d4cc", "40706a"), (1, 0): ("1e2e2c", "080e0e"), (0, 1): ("2e5652", "0c201e"),
						  (1, 1): ("2e5652", "0c201e"), (5, 0): ("3a2e2a", "140e0c"), (3, 0): ("d8c078", "7a6428"),
						  (6, 0): ("d8c078", "7a6428"), (7, 1): ("4a5452", "182020"), (3, 2): ("2a2e2e", "0a0c0c"),
						  (7, 2): ("3a3634", "121010")}


def smuggler_materials(captain=False):
	p = "smuggler_captain" if captain else "drowned_smuggler"
	return _rmats(p, {"band": ("9a5a52", 0.9), "band_d": ("5e3632", 0.9), "rag": ("7a8e86", 0.95), "rag_d": ("4a5a54", 0.95),
					  "kelp": ("3e5a2a", 0.8), "weed": ("5e6e30", 0.85), "barnacle": ("c8c2b0", 0.7), "hole": ("3a3630", 0.8),
					  "gold": ("c8a860", 0.35), "rope": ("9a8a66", 0.9), "leather": ("4a4038", 0.8), "iron": ("6a7472", 0.5),
					  "coat": ("2e5652", 0.8), "coat_d": ("1a3230", 0.85),
					  "brass": ("d8c078", 0.35), "hat": ("343a3c", 0.85), "hat_d": ("1e2426", 0.9),
					  "feather": ("e8ece8", 0.8), "feather_d": ("8a9490", 0.8), "wine": ("6a3a3e", 0.85)})


def build_smuggler_bandana():
	"""A sodden bandana knotted over the hair, its tails hanging behind, weed caught in it, a gold earring."""
	m = smuggler_materials()
	b = Builder("smuggler_bandana")
	_shell(b, (1.2, 1.2, 1.12), (0, 0.02, 1.66), m["band"], lambda d: d.z > 0.3, segs=(16, 12))
	_wrap(b, (0, 0.02, 1.84), (0.57, 0.57), 0.06, 0.02, m["band_d"], sides=18)
	b.blob((0.2, 0.14, 0.16), (0, 0.6, 1.86), m["band_d"], "x", segs=(8, 5))                         # the knot
	for s in (1, -1):
		_slab(b, [(0.03 * s, 0.62, 1.84), (0.12 * s, 0.64, 1.82), (0.2 * s, 0.7, 1.48), (0.1 * s, 0.68, 1.46)], 0.03, m["band"])
	for x, y, ln in ((0.5, -0.24, 0.4), (-0.46, 0.1, 0.5), (0.36, 0.42, 0.44)):
		_kelp(b, (x, y, 1.9), ln, m["kelp"], lean=(x * 0.2, 0.1), width=0.04)
	start = len(b.parts)
	_ring(b, (0, 0, 0), (0.06, 0.06), (0, 90), 0.014, m["gold"], sides=10)
	for p in b.parts[start:]:
		p.data.transform(Matrix.Translation((0.6, 0.0, 1.46)))
	return b.build_static()


def build_smuggler_rags():
	"""Rotted rags over the shoulders, a baldric with a knife sheath, barnacles and weed."""
	m = smuggler_materials()
	b = Builder("smuggler_rags")
	for s in (1, -1):
		b.blob((0.36, 0.56, 0.1), (0.26 * s, 0.0, 1.26), m["rag_d"], "x", rot=(0, 18 * s, 0), segs=(10, 5))
		_slab(b, [(0.2 * s, -0.34, 1.24), (0.44 * s, -0.3, 1.2), (0.46 * s, -0.34, 0.86), (0.36 * s, -0.37, 0.8), (0.24 * s, -0.38, 0.9)],
			  0.03, m["rag"] if s > 0 else m["rag_d"])
		_kelp(b, (0.38 * s, 0.1, 1.24), 0.46, m["weed"], lean=(0.1 * s, 0.1), width=0.045)
	b.seg((0.3, -0.37, 1.3), (-0.3, -0.41, 0.72), 0.03, 0.03, m["leather"], "x", sides=4)               # the baldric
	b.seg((0.3, 0.37, 1.3), (-0.3, 0.4, 0.72), 0.03, 0.03, m["leather"], "x", sides=4)
	b.blob((0.08, 0.04, 0.08), (0.0, -0.4, 1.02), m["gold"], "x", segs=(6, 4))
	b.seg((-0.2, -0.41, 0.9), (-0.08, -0.43, 0.66), 0.045, 0.03, m["leather"], "x", sides=5)              # a knife sheath
	for loc, nrm, sz in (((0.16, -0.36, 1.1), (0.2, -1, 0.2), 1.0), ((0.26, 0.3, 1.1), (0.4, 1, 0.3), 0.9),
						 ((-0.2, 0.33, 0.96), (-0.2, 1, 0), 1.0)):
		_barnacle(b, loc, nrm, m, sz)
	return b.build_static()


def build_smuggler_sash():
	"""A faded sash knotted at the hip, its ends in tatters, a coin pouch."""
	m = smuggler_materials()
	b = Builder("smuggler_sash")
	_wrap(b, (0, 0.0, 0.66), (0.44, 0.39), 0.12, 0.03, m["band"], sides=18)
	b.blob((0.14, 0.12, 0.14), (0.38, -0.2, 0.66), m["band_d"], "x", segs=(8, 5))
	for k, (dx, ln) in enumerate(((0.0, 0.36), (0.07, 0.28))):
		_slab(b, [(0.4 + dx, -0.22, 0.62), (0.46 + dx, -0.16, 0.62), (0.47 + dx, -0.12, 0.62 - ln), (0.41 + dx, -0.2, 0.62 - ln * 0.8)],
			  0.025, m["band"] if k else m["band_d"])
	b.blob((0.14, 0.1, 0.16), (-0.36, -0.24, 0.52), m["leather"], "x", segs=(8, 6))
	b.blob((0.05, 0.04, 0.05), (-0.36, -0.3, 0.58), m["gold"], "x", segs=(5, 4))
	_kelp(b, (-0.2, 0.38, 0.62), 0.3, m["kelp"], width=0.035, parts=2)
	return b.build_static()


def build_smuggler_captain_hat():
	"""A wide-brimmed hat gone soft with seawater, a gull's feather in the band, weed hanging off the brim."""
	m = smuggler_materials(True)
	b = Builder("smuggler_captain_hat")
	b.blob((1.78, 1.7, 0.07), (0, 0.0, 2.0), m["hat_d"], "x", rot=(-4, 5, 0), segs=(20, 5))          # the brim
	b.seg((0, 0.0, 1.98), (0, 0.02, 2.34), 0.48, 0.42, m["hat"], "x", sides=16)                     # the crown
	b.blob((0.84, 0.8, 0.18), (0, 0.02, 2.34), m["hat"], "x", segs=(14, 6))
	b.blob((0.5, 0.2, 0.08), (0, 0.02, 2.42), m["hat_d"], "x", segs=(8, 4))                          # a dent
	_wrap(b, (0, 0.0, 2.08), (0.485, 0.485), 0.08, 0.02, m["wine"], sides=18)
	b.blob((0.12, 0.05, 0.1), (0, -0.5, 2.08), m["brass"], "x", segs=(6, 4))                          # the buckle
	base = Vector((0.4, 0.26, 2.1))
	d = Vector((0.4, 0.8, 0.5)).normalized()
	_oblob(b, (0.14, 0.8, 0.02), tuple(base + d * 0.4), tuple(d), (0.6, -0.4, 0.3), m["feather"], "x", segs=(8, 3))
	_oblob(b, (0.1, 0.3, 0.025), tuple(base + d * 0.66), tuple(d), (0.6, -0.4, 0.3), m["feather_d"], "x", segs=(6, 3))
	for x, y, ln in ((-0.7, -0.3, 0.3), (-0.3, -0.78, 0.22), (0.1, 0.84, 0.34), (-0.8, 0.3, 0.26)):
		_kelp(b, (x, y, 1.98), ln, m["kelp"], width=0.03, parts=2)
	return b.build_static()


def build_smuggler_captain_coat():
	"""The long coat's high collar, lapels with brass buttons over a wine waistcoat, epaulettes, barnacles."""
	m = smuggler_materials(True)
	b = Builder("smuggler_captain_coat")
	_wrap(b, (0, 0.04, 1.36), (0.36, 0.32), 0.18, 0.05, m["coat_d"], rot=(-12, 0, 0), gap=(245, 295), sides=18)
	_slab(b, [(-0.1, -0.39, 1.26), (0.1, -0.39, 1.26), (0.12, -0.4, 0.74), (-0.12, -0.4, 0.74)], 0.02, m["wine"])
	for s in (1, -1):
		_slab(b, [(0.1 * s, -0.4, 1.3), (0.28 * s, -0.37, 1.3), (0.2 * s, -0.4, 1.02), (0.13 * s, -0.41, 0.98)], 0.03, m["coat_d"])
		for k in range(4):
			b.blob((0.05, 0.03, 0.05), (0.16 * s, -0.415, 1.12 - 0.12 * k), m["brass"], "x", segs=(6, 4))
		b.blob((0.34, 0.34, 0.1), (0.4 * s, 0.0, 1.27), m["brass"], "x", rot=(0, 16 * s, 0), segs=(10, 5))   # epaulettes
		for k in range(6):
			a = math.radians(-70 + 28 * k)
			p = (0.4 * s + 0.16 * s * math.cos(a) * 0.3 + 0.13 * s, 0.16 * math.sin(a), 1.24)
			b.seg(p, (p[0] + 0.02 * s, p[1], 1.12), 0.014, 0.01, m["brass"], "x", sides=4)
	for loc, nrm, sz in (((-0.24, -0.35, 1.0), (-0.3, -1, 0), 0.9), ((0.28, 0.3, 1.14), (0.4, 1, 0.3), 1.0)):
		_barnacle(b, loc, nrm, m, sz)
	_kelp(b, (-0.36, 0.1, 1.26), 0.42, m["kelp"], lean=(-0.1, 0.1), width=0.04)
	return b.build_static()


def build_smuggler_captain_tails():
	"""The coat's skirts to the shins, open in front and torn at the hem, a wine sash and brass buckle."""
	m = smuggler_materials(True)
	b = Builder("smuggler_captain_tails")
	_shell(b, (1.0, 0.92, 1.9), (0, 0.02, 0.74), m["coat"], lambda d: d.y > -0.45 and -0.74 < d.z < -0.02, segs=(18, 18))
	_shell(b, (1.02, 0.94, 1.9), (0, 0.02, 0.74), m["coat_d"], lambda d: d.y > -0.45 and -0.74 < d.z < -0.66, segs=(18, 18))   # the hem
	for a in (200, 250, 300, 340):   # ragged tears in the hem
		r = math.radians(a + 90)
		p = (0.44 * math.cos(r), 0.02 + 0.41 * math.sin(r), 0.14)
		b.blob((0.12, 0.12, 0.14), p, m["hat_d"], "x", segs=(6, 4))
	_wrap(b, (0, 0.0, 0.68), (0.45, 0.4), 0.14, 0.03, m["wine"], sides=18)
	_wrap(b, (0, 0.0, 0.74), (0.46, 0.41), 0.05, 0.03, m["leather"], sides=18)
	b.blob((0.14, 0.05, 0.1), (0, -0.44, 0.74), m["brass"], "x", segs=(6, 4))
	_barnacle(b, (0.3, 0.34, 0.4), (0.5, 1, 0), m, 1.0)
	return b.build_static()


def build_smuggler_cutlass():
	"""A heavy cutlass with a brass basket hilt, its blade curving toward the edge (KayKit weapons' frame:
	grip at the origin, blade up +Z, flat across X), gone green-black and dripping in the water."""
	m = _rmats("smuggler_cutlass", {"steel": ("8aa8a4", 0.3), "steel_d": ("4a6462", 0.35), "edge": ("c8f4ec", 0.25, 0.6),
									 "brass": ("c8a860", 0.35), "grip": ("3a2e28", 0.8), "wire": ("a89a6a", 0.4)})
	b = Builder("smuggler_cutlass")
	b.seg((0, 0, -0.2), (0, 0, 0.12), 0.045, 0.045, m["grip"], "x", sides=8)
	for k in range(5):
		z = -0.16 + 0.065 * k
		b.seg((0, 0, z), (0, 0, z + 0.015), 0.049, 0.049, m["wire"], "x", sides=8)
	b.blob((0.1, 0.09, 0.1), (0, 0, -0.24), m["brass"], "x", segs=(8, 6))                       # pommel
	_shell(b, (0.36, 0.26, 0.2), (0, 0, 0.14), m["brass"], lambda d: d.z < 0.2 and d.x > -0.5)    # the cup
	b.seg((-0.16, 0, 0.15), (0.16, 0, 0.15), 0.03, 0.025, m["brass"], "x", sides=6)             # quillons
	_chain(b, [(0.15, 0, 0.14), (0.14, 0, -0.04), (0.06, 0, -0.2)], 0.02, 0.018, m["brass"], sides=5)   # the knuckle bow
	# the blade: quads between the back line and the edge line, swelling toward the tip, then the point
	back, edge = [], []
	for k in range(8):
		u = k / 7
		cx = 0.2 * u * u
		z = 0.18 + 1.0 * u
		w = 0.1 + 0.05 * math.sin(math.pi * u * 0.9)
		back.append(Vector((cx - w * 0.45, 0, z - 0.02 * u)))
		edge.append(Vector((cx + w * 0.55, 0, z - 0.06 * u)))
	for k in range(7):
		_slab(b, [tuple(back[k]), tuple(edge[k]), tuple(edge[k + 1]), tuple(back[k + 1])], 0.03, m["steel"])
		b.seg(tuple(edge[k]), tuple(edge[k + 1]), 0.012, 0.012, m["edge"], "x", sides=4)
	tip = back[-1] + Vector((0.2, 0, 0.12))
	_slab(b, [tuple(back[-1]), tuple(edge[-1]), tuple(tip)], 0.03, m["steel"])
	b.seg(tuple(edge[-1]), tuple(tip), 0.012, 0.0, m["edge"], "x", sides=4)
	b.seg(tuple(back[0] + Vector((0.02, 0, 0))), tuple(back[5] + Vector((0.02, 0, 0))), 0.012, 0.012, m["steel_d"], "x", sides=4)   # fuller
	return b.build_static()


# ---- saltreavers and their king (the barbarian: weathered skin, sea-worn furs, scale mail, finned helms)

SALTREAVER_CELLS = {(0, 0): ("d8a888", "7a4a38"), (1, 3): ("d8a888", "7a4a38"), (3, 1): ("d0a080", "724434"),
					(7, 1): ("5a5048", "1e1a16"), (3, 2): ("4a3e34", "16120e"), (7, 0): ("8a9a98", "2e3a3a"),
					(2, 1): ("a8a49a", "4a4640"), (6, 0): ("6a4a34", "241810"), (6, 1): ("6a4a34", "241810"),
					(5, 1): ("6a4a34", "241810"), (3, 0): ("9aa4a4", "3a4242"), (7, 2): ("7a6a58", "2a2218")}
SALTREAVER_KING_CELLS = {(0, 0): ("e0b89a", "84543e"), (1, 3): ("e0b89a", "84543e"), (3, 1): ("d8b094", "7c4e3a"),
						 (7, 1): ("3a3632", "121010"), (3, 2): ("2e2824", "0e0a08"), (7, 0): ("5a7a7a", "1a2e30"),
						 (2, 1): ("ecead8", "8a887a"), (6, 0): ("4a3428", "1a100a"), (6, 1): ("4a3428", "1a100a"),
						 (5, 1): ("8a2e24", "2e0c08"), (3, 0): ("c8a048", "6a4a14"), (7, 2): ("5a4a3e", "1e1610")}


def reaver_materials(king=False):
	p = "saltreaver_king" if king else "saltreaver"
	return _rmats(p, {"iron": ("7a8686", 0.45), "iron_d": ("3e4848", 0.5), "iron_l": ("aab4b2", 0.35), "fin": ("4a7a7a", 0.6),
					  "fin_d": ("2a4a4c", 0.7), "horn": ("e8dcc0", 0.6), "horn_d": ("a8987a", 0.7), "fur": ("8a8478", 0.95),
					  "fur_d": ("5a564e", 0.95), "fur_l": ("d8d4c4", 0.95), "scale": ("6e8a88", 0.35), "scale_d": ("3a5250", 0.45),
					  "leather": ("5a4030", 0.85), "leather_d": ("2e2018", 0.9), "tattoo": ("2a5a7a", 0.7), "tooth": ("f0e8d4", 0.5),
					  "rope": ("9a8a66", 0.9), "bone": ("ece2c8", 0.65), "bone_d": ("a8987c", 0.8), "barnacle": ("c8c2b0", 0.7),
					  "hole": ("3a3630", 0.8), "kelp": ("3e5a2a", 0.8), "gold": ("c8a048", 0.35), "red": ("8a2e24", 0.8)})


def build_saltreaver_helm():
	"""An iron cap with a nasal, a fish's dorsal fin for a crest and two bone horns curving up out of it."""
	m = reaver_materials()
	b = Builder("saltreaver_helm")
	_shell(b, (1.14, 1.08, 1.02), (0, -0.02, 1.74), m["iron"], lambda d: d.z > 0.16, segs=(18, 12))
	_wrap(b, (0, -0.02, 1.83), (0.57, 0.54), 0.08, 0.03, m["iron_d"], sides=20)
	for k in range(10):   # rivets round the rim
		a = 2 * math.pi * k / 10
		b.blob((0.04, 0.04, 0.04), (0.6 * math.cos(a), -0.02 + 0.57 * math.sin(a), 1.83), m["iron_l"], "x", segs=(5, 3))
	b.seg((0, -0.58, 1.9), (0, -0.6, 1.62), 0.045, 0.03, m["iron_d"], "x", sides=5)                 # the nasal
	_slab(b, [(0, -0.44, 2.08), (0, -0.2, 2.5), (0, 0.24, 2.46), (0, 0.5, 2.08)], 0.03, m["fin"])
	for k in range(6):
		u = k / 5
		base = (0, -0.4 + 0.86 * u, 2.1 + 0.08 * math.sin(math.pi * u))
		tip = (0, -0.3 + 0.7 * u, 2.4 + 0.18 * math.sin(math.pi * (0.3 + 0.7 * u)) - 0.12 * u)
		b.seg(base, tip, 0.028, 0.006, m["fin_d"], "x", sides=4)
	for s in (1, -1):
		_chain(b, [(0.5 * s, -0.08, 1.96), (0.72 * s, -0.1, 2.06), (0.84 * s, -0.12, 2.3), (0.8 * s, -0.2, 2.5)], 0.09, 0.0, m["horn"], sides=7)
		for k in range(3):
			p = Vector((0.5 * s, -0.08, 1.96)).lerp(Vector((0.72 * s, -0.1, 2.06)), 0.3 + 0.35 * k)
			b.seg(tuple(p - Vector((0.02 * s, 0, 0))), tuple(p + Vector((0.02 * s, 0, 0))), 0.095, 0.095, m["horn_d"], "x", sides=7)
	_barnacle(b, (0.34, 0.3, 2.1), (0.5, 0.5, 1), m, 0.8)
	return b.build_static()


def _reaver_chest(b, m, king):
	# scale mail over the chest: overlapping rows hanging down, steel and sea-green
	for row in range(5):
		z = 1.18 - 0.1 * row
		n = 7 if row < 4 else 6
		for k in range(n):
			x = (k - (n - 1) / 2) * 0.1
			y = -0.37 - 0.02 * (1 - abs(x) / 0.35) - 0.005 * row
			_oblob(b, (0.11, 0.14, 0.03), (x, y, z), (0, 0.15, -1), (0, -1, 0), m["scale"] if (row + k) % 3 else m["scale_d"], "x", segs=(6, 4))
	if not king:
		# a mantle of sea-worn fur over the shoulders, open at the throat
		_shell(b, (1.16, 1.0, 0.8), (0, 0.04, 1.24), m["fur"], lambda d: d.z > -0.05 and not (d.y < -0.3 and abs(d.x) < 0.5), segs=(16, 10))
		for s in (1, -1):
			b.blob((0.46, 0.5, 0.3), (0.4 * s, 0.04, 1.34), m["fur"], "x", rot=(0, 20 * s, 0), segs=(10, 6))
		for k in range(10):
			a = math.radians(-20 + k * 24)
			p = (0.58 * math.cos(a), 0.04 + 0.5 * math.sin(a), 1.22)
			_tuft(b, p, (math.cos(a) * 0.3, math.sin(a) * 0.3, -1), 0.18, 4, 0.3, [m["fur"], m["fur_d"]], 670 + k, width=0.035)
		# a shark-tooth necklace
		for k in range(9):
			a = math.pi + math.pi * (k + 0.5) / 9
			p = (0.34 * math.cos(a), 0.34 * math.sin(a) - 0.04, 1.34 + 0.14 * math.sin(a))
			b.seg(p, (p[0], p[1] - 0.02, p[2] - 0.1), 0.025, 0.0, m["tooth"], "x", sides=4)
		return
	# the king: a great cloak of white bear fur, clasped with bone at the chest
	_shell(b, (1.3, 1.14, 0.96), (0, 0.06, 1.24), m["fur_l"], lambda d: d.z > -0.1 and not (d.y < -0.3 and abs(d.x) < 0.5), segs=(16, 10))
	_shell(b, (1.2, 1.12, 2.1), (0, 0.14, 0.86), m["fur_l"], lambda d: d.y > 0.1 and -0.5 < d.z < 0.45, segs=(16, 16))
	for s in (1, -1):
		b.blob((0.56, 0.6, 0.36), (0.44 * s, 0.04, 1.36), m["fur_l"], "x", rot=(0, 20 * s, 0), segs=(10, 6))
		b.blob((0.14, 0.1, 0.14), (0.26 * s, -0.42, 1.26), m["bone"], "x", segs=(8, 5))
	b.seg((-0.26, -0.44, 1.26), (0.26, -0.44, 1.26), 0.02, 0.02, m["gold"], "x", sides=4)
	for k in range(9):
		a = math.radians(10 + k * 20)
		p = (0.62 * math.cos(a), 0.14 + 0.58 * math.sin(a), 0.4)
		_tuft(b, p, (math.cos(a) * 0.2, math.sin(a) * 0.2, -1), 0.16, 4, 0.3, [m["fur_l"], m["fur"]], 690 + k, width=0.04)


def _reaver_kilt(b, m, king):
	_wrap(b, (0, 0.0, 0.66), (0.47, 0.41), 0.1, 0.04, m["leather_d"], sides=18)
	b.blob((0.18, 0.06, 0.14), (0, -0.44, 0.66), m["gold"] if king else m["iron_l"], "x", segs=(8, 5))
	for k in range(12):   # strips of hide and fur
		a = math.radians(k * 30 + 15)
		c, s_ = math.cos(a), math.sin(a)
		top = Vector((0.49 * c, 0.43 * s_, 0.62))
		side = Vector((-s_, c, 0)) * 0.1
		bot = top + Vector((0.06 * c, 0.06 * s_, -0.3 - 0.04 * (k % 2)))
		_slab(b, [tuple(top - side), tuple(top + side), tuple(bot + side * 0.8), tuple(bot - side * 0.8)], 0.03,
			  (m["fur"] if not king else m["red"]) if k % 2 else m["leather"])
	b.seg((0.46, -0.12, 0.62), (0.48, -0.14, 0.5), 0.01, 0.01, m["rope"], "x", sides=3)
	b.seg((0.48, -0.14, 0.5), (0.49, -0.18, 0.38), 0.04, 0.0, m["tooth"], "x", sides=5)           # a whale's tooth charm


def _reaver_part(name, fn, king):
	b = Builder(name)
	fn(b, reaver_materials(king), king)
	return b.build_static()


def _reaver_arm(name, s):
	"""Sea-blue tattoos round the upper arm: two bands and a run of waves between."""
	m = reaver_materials()
	b = Builder(name)
	for x in (0.26, 0.42):
		start = len(b.parts)
		_wrap(b, (0, 0, 0), (0.142, 0.142), 0.026, 0.006, m["tattoo"], sides=14)
		for p in b.parts[start:]:
			p.data.transform(Matrix.Translation((x * s, 0, 1.11)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
	for k in range(4):
		x0 = (0.28 + 0.035 * k) * s
		for sgn in (1, -1):
			y = -0.14 * sgn
			b.seg((x0, y, 1.12), (x0 + 0.018 * s, y * 0.98, 1.16), 0.011, 0.011, m["tattoo"], "x", sides=3)
			b.seg((x0 + 0.018 * s, y * 0.98, 1.16), (x0 + 0.035 * s, y, 1.12), 0.011, 0.011, m["tattoo"], "x", sides=3)
	return b.build_static()


def _reaver_bracer(name, s):
	m = reaver_materials()
	b = Builder(name)
	b.seg((0.47 * s, 0.0, 1.11), (0.66 * s, 0.0, 1.11), 0.148, 0.145, m["leather"], "x", sides=10)
	for x in (0.5, 0.6):
		b.blob((0.04, 0.04, 0.04), (x * s, -0.145, 1.11), m["iron_l"], "x", segs=(5, 3))
	return b.build_static()


def build_saltreaver_king_crown():
	"""A crown of whale bone: ribs curving up and out of a bone band, the tallest at the front, a whale's
	vertebra set over the brow, barnacles grown on it."""
	import random
	rng = random.Random(701)
	m = reaver_materials(True)
	b = Builder("saltreaver_king_crown")
	_wrap(b, (0, -0.02, 1.9), (0.52, 0.49), 0.1, 0.05, m["bone"], sides=20)
	_wrap(b, (0, -0.02, 1.86), (0.535, 0.505), 0.025, 0.05, m["bone_d"], sides=20)
	for k in range(9):
		a = 2 * math.pi * k / 9 - math.pi / 2
		out = Vector((math.cos(a), math.sin(a), 0))
		base = Vector((0.52 * math.cos(a), -0.02 + 0.49 * math.sin(a), 1.92))
		tall = 0.62 if k == 0 else (0.48 if k in (1, 8) else 0.36)
		pts = [base, base + out * 0.08 + Vector((0, 0, tall * 0.45)), base + out * 0.2 + Vector((0, 0, tall * 0.8)), base + out * 0.34 + Vector((0, 0, tall))]
		_chain(b, pts, 0.05, 0.012, m["bone"], sides=6)
	# the vertebra over the brow: a disc and its wings
	b.blob((0.3, 0.12, 0.26), (0, -0.56, 2.06), m["bone"], "x", segs=(10, 6))
	b.blob((0.14, 0.06, 0.12), (0, -0.62, 2.06), m["bone_d"], "x", segs=(8, 5))
	for s in (1, -1):
		b.seg((0.1 * s, -0.56, 2.08), (0.3 * s, -0.54, 2.2), 0.04, 0.015, m["bone"], "x", sides=5)
	for k in range(4):
		a = rng.uniform(0, 2 * math.pi)
		_barnacle(b, (0.53 * math.cos(a), -0.02 + 0.5 * math.sin(a), 1.92), (math.cos(a), math.sin(a), 0.3), m, 0.7)
	return b.build_static()


def build_whalebone_axe():
	"""The reaver king's axe: a great bearded iron blade on a haft of whale rib, bound with rope, a whale
	tooth at the butt (KayKit weapons' frame: grip at the origin, haft up +Z, the blade out along +X)."""
	m = _rmats("whalebone_axe", {"bone": ("ece2c8", 0.65), "bone_d": ("a8987c", 0.8), "iron": ("6e7a7a", 0.4),
								  "iron_d": ("363e3e", 0.5), "edge": ("d0dada", 0.25), "rope": ("9a8a66", 0.9),
								  "leather": ("4a3428", 0.85), "tooth": ("f4ecd8", 0.45)})
	b = Builder("whalebone_axe")
	_chain(b, [(0, 0, -0.44), (0.02, 0, 0.3), (0, 0, 1.3)], 0.055, 0.048, m["bone"], sides=8)
	for z in (-0.3, 0.5, 0.74, 0.98):
		b.seg((0, 0, z), (0, 0, z + 0.03), 0.06, 0.06, m["bone_d"], "x", sides=8)
	b.seg((0, 0, -0.12), (0, 0, 0.2), 0.062, 0.062, m["leather"], "x", sides=8)
	b.seg((0, 0, -0.44), (0, 0, -0.62), 0.05, 0.0, m["tooth"], "x", sides=6)
	blade = [(0.04, 0, 1.24), (0.04, 0, 0.9), (0.26, 0, 0.72), (0.56, 0, 0.72), (0.7, 0, 0.98), (0.66, 0, 1.3), (0.4, 0, 1.36)]
	_slab(b, blade, 0.05, m["iron"])
	_chain(b, [(0.56, 0, 0.72), (0.7, 0, 0.98), (0.66, 0, 1.3), (0.4, 0, 1.36)], 0.03, 0.02, m["edge"], sides=4)
	_slab(b, [(0.04, 0, 1.2), (0.04, 0, 0.94), (0.2, 0, 0.9), (0.22, 0, 1.2)], 0.07, m["iron_d"])
	b.seg((0, 0, 1.08), (-0.34, 0, 1.02), 0.07, 0.0, m["iron_d"], "x", sides=6)                     # a back spike
	for z in (0.88, 1.28):
		b.seg((0, 0, z), (0, 0, z + 0.04), 0.07, 0.07, m["rope"], "x", sides=8)
	b.seg((0, 0, 1.3), (0, 0, 1.46), 0.05, 0.0, m["bone"], "x", sides=6)
	return b.build_static()


# ---- clawfolk (the barbarian in crab shell: a carapace head on eyestalks, one great crushing claw)

CLAWFOLK_CELLS = {(0, 0): ("d8663a", "6a1e0e"), (1, 3): ("d8663a", "6a1e0e"), (3, 1): ("d06036", "621c0c"),
				  (7, 1): ("c85a34", "5a1a0c"), (3, 2): ("8a2a14", "2e0a04"), (7, 0): ("f0c8a0", "a8704a"),
				  (2, 1): ("c8c0b0", "6a645a"), (6, 0): ("7a2a16", "2a0a06"), (6, 1): ("7a2a16", "2a0a06"),
				  (5, 1): ("7a2a16", "2a0a06"), (3, 0): ("e0a070", "7a3a1a"), (7, 2): ("b84a26", "4a1408")}


def claw_materials():
	return _rmats("clawfolk", {"shell": ("c8502a", 0.3), "shell_d": ("7a2410", 0.4), "shell_l": ("e8844a", 0.3),
								"belly": ("f0d0a8", 0.45), "tip": ("2a1a18", 0.3), "eye": ("0e0a0c", 0.08), "shine": ("f8f0e8", 0.1, 1.0),
								"stalk": ("d86a3a", 0.35), "mouth": ("5a1a14", 0.6), "spike": ("f0b080", 0.35),
								"barnacle": ("c8c2b0", 0.7), "hole": ("3a3630", 0.8), "kelp": ("3e5a2a", 0.8)})


def build_clawfolk_head():
	import random
	rng = random.Random(721)
	m = claw_materials()
	b = Builder("clawfolk_head")
	b.seg((0, 0.02, 1.18), (0, 0.0, 1.44), 0.3, 0.32, m["shell_d"], "x", sides=10)
	b.blob((1.02, 0.9, 0.46), (0, 0.04, 1.58), m["shell"], "x", segs=(16, 9))                     # the carapace
	b.blob((0.8, 0.66, 0.2), (0, 0.08, 1.76), m["shell_d"], "x", segs=(12, 6))
	b.blob((0.7, 0.3, 0.3), (0, -0.28, 1.44), m["belly"], "x", segs=(12, 7))                       # the face beneath the rim
	for k in range(9):   # the serrated front rim
		a = math.radians(200 + k * 17.5)
		p = Vector((0.5 * math.cos(a), 0.04 + 0.45 * math.sin(a), 1.58))
		out = Vector((math.cos(a), math.sin(a), 0.1))
		b.seg(tuple(p), tuple(p + out * 0.12), 0.045, 0.0, m["spike"], "x", sides=5)
	for s in (1, -1):
		for k in range(3):   # side spines
			a = math.radians(-30 + 30 * k) if s > 0 else math.radians(210 - 30 * k)
			p = Vector((0.5 * math.cos(a), 0.04 + 0.45 * math.sin(a), 1.58))
			b.seg(tuple(p), tuple(p + Vector((math.cos(a), math.sin(a), 0.2)) * 0.16), 0.05, 0.0, m["shell_l"], "x", sides=5)
		# eyestalks with glossy black eyes, a pair of short antennae, mouthparts
		b.seg((0.16 * s, -0.34, 1.7), (0.24 * s, -0.5, 2.02), 0.05, 0.035, m["stalk"], "x", sides=6)
		b.blob((0.14, 0.14, 0.16), (0.24 * s, -0.52, 2.06), m["eye"], "x", segs=(10, 7))
		b.blob((0.04, 0.03, 0.04), (0.26 * s, -0.58, 2.1), m["shine"], "x", segs=(5, 3))
		_chain(b, [(0.07 * s, -0.46, 1.6), (0.14 * s, -0.74, 1.78), (0.2 * s, -0.9, 1.74)], 0.02, 0.004, m["stalk"], sides=4)
		b.seg((0.12 * s, -0.4, 1.4), (0.06 * s, -0.54, 1.3), 0.05, 0.02, m["shell_d"], "x", sides=5)   # mandibles
	for k in range(3):
		b.blob((0.34 - 0.06 * k, 0.06, 0.1), (0, -0.44 - 0.01 * k, 1.44 - 0.08 * k), m["mouth"], "x", segs=(8, 4))
	for k in range(4):
		a = rng.uniform(0, 2 * math.pi)
		r = rng.uniform(0.1, 0.3)
		p, n = _on_dome((0, 0.04, 1.58), (0.51, 0.45, 0.23), r * math.cos(a), 0.04 + r * math.sin(a))
		_barnacle(b, tuple(p), tuple(n), m, 0.8)
	return b.build_static()


def build_clawfolk_shell():
	"""A carapace over the back with spikes down its edges, spiny shoulders, banded belly plates in front."""
	m = claw_materials()
	b = Builder("clawfolk_shell")
	_shell(b, (1.16, 1.02, 1.1), (0, 0.06, 1.02), m["shell"], lambda d: d.y > -0.05 and d.z > -0.6, segs=(18, 12))
	_shell(b, (1.0, 0.9, 0.9), (0, 0.12, 1.1), m["shell_d"], lambda d: d.y > 0.5 and d.z > -0.4, segs=(14, 10))
	for k in range(7):
		z = 1.46 - 0.14 * k
		b.seg((0, 0.56 - 0.01 * abs(k - 3), z), (0, 0.72 - 0.01 * abs(k - 3), z + 0.06), 0.05, 0.0, m["spike"], "x", sides=5)
	for s in (1, -1):
		b.blob((0.44, 0.48, 0.34), (0.42 * s, 0.0, 1.3), m["shell"], "x", segs=(10, 7))
		for k in range(3):
			a = math.radians(-40 + 40 * k)
			p = Vector((0.5 * s, 0.2 * math.sin(a), 1.36 + 0.06 * math.cos(a)))
			b.seg(tuple(p), tuple(p + Vector((0.18 * s, 0.06 * math.sin(a), 0.14))), 0.05, 0.0, m["spike"], "x", sides=5)
	for k in range(5):   # belly plates
		z = 1.22 - 0.13 * k
		b.blob((0.7 - 0.04 * k, 0.12, 0.14), (0, -0.36, z), m["belly"], "x", segs=(10, 5))
		b.blob((0.72 - 0.04 * k, 0.1, 0.03), (0, -0.37, z - 0.07), m["shell_d"], "x", segs=(10, 3))
	_barnacle(b, (0.2, 0.56, 1.2), (0.3, 1, 0.3), m, 1.0)
	_kelp(b, (-0.3, 0.5, 1.3), 0.4, m["kelp"], width=0.04)
	return b.build_static()


def _clawfolk_claw(name, s, big):
	"""A crab's claw over the KayKit hand: a swollen palm, a fixed finger and an open movable one,
	toothed inside and dark at the tips. Built along +X for the left hand (s = 1), mirrored for the right."""
	m = claw_materials()
	b = Builder(name)
	k = 1.0 if big else 0.6
	x0 = 0.8
	b.seg((0.72 * s, 0, 1.1), ((x0 + 0.08) * s, 0, 1.1), 0.17 * max(k, 0.9), 0.19 * max(k, 0.9), m["shell_d"], "x", sides=10)
	b.blob((0.62 * k, 0.46 * k, 0.52 * k), ((x0 + 0.26 * k) * s, -0.02, 1.1), m["shell"], "x", segs=(12, 8))
	b.blob((0.5 * k, 0.3 * k, 0.24 * k), ((x0 + 0.28 * k) * s, -0.04, 0.98), m["shell_l"], "x", segs=(10, 6))
	for j in range(3):   # knobs along the top
		b.seg(((x0 + 0.12 * k + 0.12 * k * j) * s, -0.02, 1.1 + 0.25 * k), ((x0 + 0.14 * k + 0.12 * k * j) * s, -0.04, 1.1 + 0.33 * k),
			  0.04 * k, 0.0, m["spike"], "x", sides=5)
	xp = x0 + 0.5 * k
	fixed = [Vector((xp * s, -0.04, 1.02)), Vector(((xp + 0.3 * k) * s, -0.08, 1.02)), Vector(((xp + 0.5 * k) * s, -0.1, 1.1))]
	moving = [Vector((xp * s, -0.04, 1.2)), Vector(((xp + 0.28 * k) * s, -0.08, 1.3)), Vector(((xp + 0.5 * k) * s, -0.1, 1.2))]
	for pts in (fixed, moving):
		_chain(b, pts, 0.14 * k, 0.05 * k, m["shell"], sides=8)
		tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.12 * k
		b.seg(tuple(pts[-1]), tuple(tip), 0.05 * k, 0.0, m["tip"], "x", sides=6)
	for j in range(4):   # teeth on the inner edges
		u = 0.2 + 0.2 * j
		p = fixed[0].lerp(fixed[1], u * 1.4) if u < 0.7 else fixed[1].lerp(fixed[2], (u - 0.7) * 3)
		b.seg(tuple(p), tuple(p + Vector((0, 0, 0.1 * k))), 0.035 * k, 0.0, m["belly"], "x", sides=4)
		q = moving[0].lerp(moving[1], u * 1.4) if u < 0.7 else moving[1].lerp(moving[2], (u - 0.7) * 3)
		b.seg(tuple(q), tuple(q + Vector((0, 0, -0.1 * k))), 0.035 * k, 0.0, m["belly"], "x", sides=4)
	if big:
		_barnacle(b, ((x0 + 0.3) * s, 0.16, 1.26), (0, 0.6, 1), m, 1.0)
		_barnacle(b, ((x0 + 0.44) * s, -0.2, 1.2), (0, -0.6, 1), m, 0.8)
	return b.build_static()


def _clawfolk_arm(name, s):
	m = claw_materials()
	b = Builder(name)
	b.seg((0.46 * s, 0.01, 1.1), (0.76 * s, 0.0, 1.1), 0.16, 0.17, m["shell"], "x", sides=10)
	for x in (0.52, 0.64):
		b.seg((x * s, 0.0, 1.1), ((x + 0.03) * s, 0.0, 1.1), 0.175, 0.175, m["shell_d"], "x", sides=10)
	for x in (0.56, 0.7):
		b.seg((x * s, 0.0, 1.26), ((x + 0.03) * s, 0.02, 1.38), 0.04, 0.0, m["spike"], "x", sides=5)
	return b.build_static()


# ---- the river hippo: a barrel of gray-pink hide on four stumps, a head that is mostly mouth

HIPPO_LEGS = {"leg_fl": (0.46, -0.62, 0.0), "leg_fr": (-0.46, -0.62, 0.5), "leg_bl": (0.46, 0.74, 0.5), "leg_br": (-0.46, 0.74, 0.0)}


def build_river_hippo():
	import random
	rng = random.Random(731)
	m = _rmats("river_hippo", {"hide": ("8a7a82", 0.5), "hide_d": ("5e5058", 0.55), "hide_l": ("aa989c", 0.5),
								"pink": ("d89a98", 0.5), "pink_d": ("b0706e", 0.55), "mouth": ("c86a70", 0.5),
								"tusk": ("efe6cc", 0.4), "eye": ("2a1a10", 0.2), "nail": ("d8cfc0", 0.6), "mud": ("5a4a36", 0.9),
								"hole": ("2a1a1a", 0.8), "scar": ("c0a8aa", 0.6)})
	b = Builder("river_hippo")
	b.bone("root", (0, 0, 0.95))
	b.bone("body", (0, 0, 1.0), "root")
	b.bone("head", (0, -1.05, 1.15), "body")
	b.bone("jaw", (0, -1.3, 0.92), "head")
	b.bone("tail", (0, 1.35, 1.05), "body")
	for s, side in ((1, "l"), (-1, "r")):
		b.bone(f"ear_{side}", (0.3 * s, -1.12, 1.62), "head")
	for name, (x, y, _ph) in HIPPO_LEGS.items():
		b.bone(name, (x, y, 0.86), "root")
	hide = m["hide"]
	b.blob((1.58, 2.6, 1.24), (0, 0.05, 1.02), hide, "body", segs=(16, 11))                       # the barrel
	b.blob((1.4, 2.2, 0.62), (0, 0.05, 0.62), m["hide_l"], "body", segs=(14, 8))                  # belly
	b.blob((1.48, 1.0, 1.2), (0, -0.62, 1.06), hide, "body", segs=(14, 9))                          # shoulders
	b.blob((1.42, 0.96, 1.16), (0, 0.84, 1.0), hide, "body", segs=(14, 9))                          # rump
	b.blob((1.2, 2.1, 0.42), (0, 0.1, 1.5), m["hide_d"], "body", segs=(14, 7))                      # the dark back
	b.blob((1.22, 0.7, 1.0), (0, -1.0, 1.1), hide, "body", segs=(12, 8))                           # the neck
	for k in range(7):   # mud caked on the flanks, pink where the skin is thin
		s = 1 if k % 2 else -1
		y = rng.uniform(-0.5, 0.6)
		z = rng.uniform(0.75, 1.15)
		mat = m["mud"] if k < 4 else m["pink"]
		x = 0.79 * math.sqrt(max(0.1, 1 - ((z - 1.02) / 0.62) ** 2 - ((y - 0.05) / 1.3) ** 2)) - 0.01
		_oblob(b, (0.34, 0.46, 0.03), (x * s, y, z), (0, 1, 0.2), (s, 0, 0), mat, "body", segs=(8, 4))
	for k in range(3):   # old scars
		y = -0.4 + 0.4 * k
		b.seg((0.78, y, 1.18), (0.8, y + 0.26, 1.0), 0.02, 0.015, m["scar"], "body", sides=4)
	# the head: a skull with eyes and ears on top, a huge blunt muzzle, the upper mouth
	b.blob((1.0, 0.8, 0.78), (0, -1.3, 1.26), hide, "head", segs=(12, 9))
	b.blob((1.18, 0.86, 0.66), (0, -1.82, 1.12), hide, "head", segs=(14, 9))
	b.blob((1.06, 0.62, 0.3), (0, -1.9, 1.34), m["hide_l"], "head", segs=(12, 6))
	b.blob((1.12, 0.3, 0.2), (0, -2.1, 0.96), m["pink"], "head", segs=(12, 6))                     # the lip
	b.blob((0.92, 0.78, 0.12), (0, -1.8, 0.84), m["mouth"], "head", segs=(12, 6))                  # palate
	for s in (1, -1):
		b.blob((0.44, 0.52, 0.48), (0.46 * s, -1.62, 1.02), hide, "head", segs=(10, 7))              # cheeks
		b.blob((0.22, 0.22, 0.16), (0.2 * s, -2.08, 1.4), hide, "head", segs=(8, 5))                  # nostril mounds
		b.blob((0.09, 0.07, 0.05), (0.2 * s, -2.14, 1.47), m["hole"], "head", segs=(6, 4))
		b.blob((0.22, 0.24, 0.2), (0.32 * s, -1.36, 1.58), hide, "head", segs=(8, 6))                 # eye mounds
		b.blob((0.14, 0.08, 0.11), (0.37 * s, -1.45, 1.61), m["pink_d"], "head", segs=(8, 5))
		b.blob((0.09, 0.06, 0.08), (0.38 * s, -1.47, 1.62), m["eye"], "head", segs=(6, 4))
		ear = f"ear_{'l' if s > 0 else 'r'}"
		b.blob((0.12, 0.08, 0.18), (0.3 * s, -1.12, 1.7), m["hide_d"], ear, segs=(6, 5))
		b.blob((0.07, 0.05, 0.11), (0.3 * s, -1.15, 1.7), m["pink_d"], ear, segs=(5, 4))
		b.seg((0.3 * s, -2.1, 0.9), (0.31 * s, -2.14, 0.8), 0.035, 0.0, m["tusk"], "head", sides=5)    # upper teeth
	# the lower jaw, its great tusks and forward-pointing teeth
	b.blob((1.08, 0.98, 0.4), (0, -1.78, 0.74), m["hide_l"], "jaw", segs=(12, 7))
	b.blob((0.92, 0.82, 0.1), (0, -1.8, 0.9), m["mouth"], "jaw", segs=(12, 6))
	b.blob((0.84, 0.3, 0.2), (0, -2.12, 0.74), m["pink"], "jaw", segs=(10, 6))
	for s in (1, -1):
		_chain(b, [(0.38 * s, -2.02, 0.84), (0.41 * s, -2.1, 1.02), (0.37 * s, -2.06, 1.18)], 0.075, 0.012, m["tusk"], "jaw", sides=7)
		b.seg((0.1 * s, -2.16, 0.82), (0.12 * s, -2.34, 0.86), 0.04, 0.018, m["tusk"], "jaw", sides=5)
	for name, (x, y, _ph) in HIPPO_LEGS.items():
		b.blob((0.52, 0.62, 0.62), (x, y, 0.76), hide, name, segs=(10, 7))
		b.seg((x, y, 0.8), (x, y, 0.14), 0.26, 0.22, hide, name, sides=10)
		b.blob((0.48, 0.52, 0.2), (x, y - 0.04, 0.1), m["hide_d"], name, segs=(10, 6))
		for dx in (-0.12, -0.04, 0.04, 0.12):
			b.blob((0.09, 0.07, 0.07), (x + dx, y - 0.28, 0.07), m["nail"], name, segs=(5, 3))
	b.seg((0, 1.34, 1.12), (0, 1.52, 0.86), 0.08, 0.05, m["hide_d"], "tail", sides=6)
	_oblob(b, (0.12, 0.16, 0.03), (0, 1.56, 0.78), (0, 0.3, -1), (0, 1, 0), m["hide_d"], "tail", segs=(6, 4))
	arm = b.build()

	def legs(t, amp, lift=0.05):
		out = {}
		for name, (_x, _y, ph) in HIPPO_LEGS.items():
			out[name] = {"rot": (amp * wave(t, 1, ph), 0, 0), "loc": (0, 0, lift * max(0.0, wave(t, 1, ph + 0.25)))}
		return out

	def ears(t, k=1.0):
		return {"ear_l": {"rot": (0, 0, 20 * k * max(0.0, wave(t, 2, 0.1)) ** 8)}, "ear_r": {"rot": (0, 0, -20 * k * max(0.0, wave(t, 2, 0.6)) ** 8)}}

	def idle(t):
		yawn = seq(t, [(0.55, 0), (0.7, 1), (0.85, 1), (0.95, 0)])
		return merge({"body": {"loc": (0, 0, 0.015 * wave(t, 2))}, "head": {"rot": (4 * wave(t, 1, 0.3) + 16 * yawn, 0, 6 * wave(t, 1))},
					  "jaw": {"rot": (-40 * yawn, 0, 0)}, "tail": {"rot": (0, 0, 20 * wave(t, 3))}}, ears(t))

	def walk(t):
		return merge(legs(t, 18), {"root": {"loc": (0, 0, 0.03 * abs(wave(t, 2)))}, "body": {"rot": (0, 2.5 * wave(t), 0)},
								   "head": {"rot": (3 * wave(t, 2), 0, 3 * wave(t))}, "tail": {"rot": (0, 0, 14 * wave(t))}}, ears(t, 0.5))

	def run(t):
		return merge(legs(t, 32, 0.12), {"root": {"loc": (0, 0, 0.08 * abs(wave(t, 2)))}, "body": {"rot": (3 * wave(t, 2), 3 * wave(t), 0)},
										 "head": {"rot": (-6 + 5 * wave(t, 2, 0.2), 0, 0)}, "tail": {"rot": (0, 0, 20 * wave(t))}})

	def attack(t):   # the head comes up and the jaws gape wide, then it slams down and forward
		up = seq(t, [(0, 0), (0.35, 1), (0.48, 1), (0.58, -0.4), (0.75, -0.3), (1, 0)])
		gape = seq(t, [(0, 0), (0.35, 62), (0.48, 66), (0.58, 4), (0.7, 10), (1, 0)])
		lunge = seq(t, [(0, 0), (0.35, -0.08), (0.58, 0.4), (0.75, 0.34), (1, 0)])
		return merge({"root": {"loc": (0, -lunge, 0.04 * max(0.0, up)), "rot": (6 * up, 0, 0)},
					  "head": {"rot": (24 * up, 0, 0)}, "jaw": {"rot": (-gape, 0, 0)},
					  "leg_fl": {"rot": (-14 * max(0.0, up), 0, 0)}, "leg_fr": {"rot": (-14 * max(0.0, up), 0, 0)}}, ears(t, 0.3))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return {"root": {"loc": (0, 0.12 * k, 0), "rot": (4 * k, 3 * k, 0)}, "head": {"rot": (14 * k, 0, -10 * k)}, "jaw": {"rot": (-18 * k, 0, 0)}}

	def death(t):   # sinks to its knees and rolls onto its side
		k = seq(t, [(0.1, 0), (0.7, 1)])
		g = seq(t, [(0.5, 0), (0.9, 1)])
		return merge({"root": {"loc": (0, 0, -0.22 * k), "rot": (0, 84 * g, 0)}, "head": {"rot": (-8 * g, 0, 10 * g)},
					  "jaw": {"rot": (-24 * g, 0, 0)}, "tail": {"rot": (-30 * g, 0, 0)}},
					 {n: {"rot": (-24 * k if "f" in n[-2:] else 24 * k, 0, 0)} for n in HIPPO_LEGS})

	clip(arm, "idle", 4.0, idle, True)
	clip(arm, "walk", 1.4, walk, True)
	clip(arm, "run", 0.7, run, True)
	clip(arm, "attack", 1.0, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.6, death, False)
	return arm


# ---- serpents: the delta serpents (banded water snakes; the great one frilled) and the sea serpents
# (blue-green, a fin crest, the neck reared up). One frame: every body segment rides its own bone off the
# root and a traveling wave draws the S-curve, like the marsh eel; built at unit size, then scaled by `k`.

SERPENTS = {
	"delta_serpent": dict(k=1.0, n=10, body="5e6a36", dark="3e3220", belly="d8c890", fin="7a6a3a", eye="f0d030", rise=0.1),
	"great_delta_serpent": dict(k=1.9, n=11, body="4e5a2a", dark="34281a", belly="e0c888", fin="c8642a", eye="ff9a2a", rise=0.3,
								frill=True),
	"sea_serpent": dict(k=1.5, n=11, body="2a7a78", dark="17485a", belly="cfe0c4", fin="3ab0a0", eye="e8f06a", rise=0.72, crest=0.2),
	"great_sea_serpent": dict(k=2.3, n=12, body="226e74", dark="12384e", belly="d8e8cc", fin="48c8b4", eye="aaffea", rise=0.9,
							  crest=0.3, horns=True),
}


def build_serpent(name="delta_serpent"):
	import random
	c = SERPENTS[name]
	rng = random.Random(741 + len(name))
	k, n = c["k"], c["n"]
	sea = "crest" in c
	m = _rmats(name, {"body": (c["body"], 0.35), "dark": (c["dark"], 0.4), "belly": (c["belly"], 0.45), "fin": (c["fin"], 0.5),
					  "spine": (c["dark"], 0.5), "mouth": ("a8484a", 0.6), "tooth": ("f2ead6", 0.3), "eye": (c["eye"], 0.2, 1.0),
					  "pupil": ("0c0a06", 0.2), "light": ("9ae8d8" if sea else "a8a060", 0.4), "barnacle": ("c8c2b0", 0.7),
					  "hole": ("3a3630", 0.8), "horn": ("e8e0cc", 0.5)})
	b = Builder(name)
	b.bone("root", (0, 0, 0.2))
	step = 0.34
	ys = [-0.9 + step * i for i in range(n)]
	radii = [0.2 * (1 - 0.82 * (i / n) ** 1.5) + 0.02 for i in range(n)]
	rise = c["rise"]
	zs = [r + rise * max(0.0, 1 - i / 3) ** 1.5 for i, r in enumerate(radii)]
	for i in range(n):
		bone = f"seg{i}"
		y, r, z = ys[i], radii[i], zs[i]
		ny = y + step
		nr = radii[i + 1] if i + 1 < n else 0.02
		nz = zs[i + 1] if i + 1 < n else nr
		b.bone(bone, (0, y, z), "root")
		b.seg((0, y, z), (0, ny, nz), r, nr, m["body"], bone, sides=12)
		b.blob((r * 2.05, r * 2.05, r * 1.95), (0, y, z), m["body"], bone, segs=(12, 8))
		b.seg((0, y, z - r * 0.45), (0, ny, nz - nr * 0.45), r * 0.8, nr * 0.8, m["belly"], bone, sides=10)
		if not sea:   # dark bands, and a low fin ridge
			b.seg((0, y + 0.1, z + (nz - z) * 0.3), (0, y + 0.22, z + (nz - z) * 0.65), r * 1.04, r * 1.02, m["dark"], bone, sides=12)
			_slab(b, [(0, y, z + r * 0.92), (0, ny, nz + nr * 0.92), (0, ny, nz + nr * 1.05 + 0.03), (0, y, z + r * 1.05 + 0.03)], 0.02, m["fin"])
			_on_bone(b, len(b.parts) - 1, bone)
		else:         # a crest of spines webbed with fin down the back, pale scale flecks
			h = c["crest"] * (1 - 0.6 * i / n) * (r / 0.2) ** 0.5
			_slab(b, [(0, y, z + r * 0.9), (0, ny, nz + nr * 0.9), (0, ny - 0.06, nz + nr + h * 0.7), (0, y + 0.06, z + r + h)], 0.025, m["fin"])
			_on_bone(b, len(b.parts) - 1, bone)
			b.seg((0, y + 0.06, z + r * 0.9), (0, y + 0.08, z + r + h * 1.12), 0.022, 0.004, m["spine"], bone, sides=4)
			for j in range(2):
				a = rng.uniform(-1.3, 1.3)
				p = Vector((r * 0.95 * math.sin(a), y + rng.uniform(0.05, 0.3), z + r * 0.95 * math.cos(a)))
				_oblob(b, (r * 0.35, r * 0.5, 0.02), tuple(p), (0, 1, 0), (math.sin(a), 0, math.cos(a)), m["light"], bone, segs=(6, 3))
	yt = ys[-1] + step
	_slab(b, [(0, yt - 0.3, 0.05), (0, yt + 0.34, 0.08), (0, yt + 0.38, 0.22 if sea else 0.16), (0, yt - 0.2, 0.2)], 0.025, m["fin"])
	_on_bone(b, len(b.parts) - 1, f"seg{n - 1}")
	# the head: a blunt wedge, slitted eyes, a gaping jaw of fangs
	H = Vector((0, ys[0] - 0.1, zs[0] + 0.02))
	b.bone("head", tuple(H), "root")
	b.bone("jaw", tuple(H + Vector((0, -0.12, -0.06))), "head")

	def at(x, y, z):
		return tuple(H + Vector((x, y, z)))
	b.blob((0.44, 0.52, 0.34), at(0, -0.14, 0.04), m["body"], "head", segs=(12, 8))
	b.blob((0.36, 0.44, 0.2), at(0, -0.42, 0.03), m["body"], "head", segs=(12, 7))
	b.blob((0.4, 0.3, 0.14), at(0, -0.16, 0.16), m["dark"], "head", segs=(10, 5))
	b.blob((0.3, 0.4, 0.1), at(0, -0.42, -0.04), m["mouth"], "head", segs=(10, 5))
	b.blob((0.36, 0.56, 0.16), at(0, -0.3, -0.1), m["belly"], "jaw", segs=(12, 6))
	b.blob((0.28, 0.44, 0.06), at(0, -0.34, -0.04), m["mouth"], "jaw", segs=(10, 4))
	for s in (1, -1):
		b.blob((0.1, 0.1, 0.08), at(0.15 * s, -0.28, 0.14), m["eye"], "head", segs=(8, 5))
		b.blob((0.025, 0.04, 0.07), at(0.19 * s, -0.3, 0.14), m["pupil"], "head", segs=(5, 3))
		b.blob((0.03, 0.03, 0.02), at(0.07 * s, -0.62, 0.08), m["pupil"], "head", segs=(5, 3))
		for j in range(5):
			y = -0.58 + 0.07 * j
			x = (0.11 + 0.01 * j) * s
			b.seg(at(x, y, -0.02), at(x, y - 0.01, -0.1 - 0.03 * (j == 0)), 0.022, 0.002, m["tooth"], "head", sides=4)
			b.seg(at(x * 0.95, y + 0.03, -0.05), at(x * 0.95, y + 0.02, 0.02), 0.018, 0.002, m["tooth"], "jaw", sides=4)
		fin = m["fin"] if sea else m["dark"]
		_oblob(b, (0.24 if sea else 0.18, 0.16, 0.02), at(0.21 * s, 0.06, 0.04), (0, 1, -0.3), (s, 0, 0.2), fin, "head", segs=(8, 4))
		if c.get("horns"):
			_chain(b, [at(0.12 * s, -0.08, 0.2), at(0.2 * s, 0.1, 0.34), at(0.24 * s, 0.34, 0.4)], 0.06, 0.0, m["horn"], "head", sides=6)
	b.blob((0.4, 0.3, 0.36), at(0, 0.08, 0.0), m["body"], "head", segs=(10, 7))
	if sea:   # the crest runs up over the head
		_slab(b, [at(0, -0.3, 0.16), at(0, 0.1, 0.18), at(0, 0.14, 0.18 + c["crest"] * 1.3), at(0, -0.1, 0.18 + c["crest"] * 0.9)], 0.025, m["fin"])
		_on_bone(b, len(b.parts) - 1, "head")
		for j in range(3):
			b.seg(at(0, -0.2 + 0.12 * j, 0.16), at(0, -0.14 + 0.13 * j, 0.2 + c["crest"] * (1.0 + 0.2 * j)), 0.02, 0.004, m["spine"], "head", sides=4)
	if c.get("frill"):   # a frill of spines fanned round the back of the head, webbed orange
		base = Vector(at(0, 0.04, 0.06))
		tips = []
		for j in range(9):
			phi = math.radians(-100 + 25 * j)
			d = Vector((math.sin(phi), 0.3, math.cos(phi))).normalized()
			tips.append(base + d * (0.5 - 0.12 * abs(j - 4) / 4))
		for j in range(8):
			_slab(b, [tuple(base), tuple(tips[j]), tuple(tips[j + 1])], 0.02, m["fin"])
			_on_bone(b, len(b.parts) - 1, "head")
		for t_ in tips:
			b.seg(tuple(base), tuple(t_ + (t_ - base).normalized() * 0.05), 0.025, 0.004, m["dark"], "head", sides=4)
	if name.startswith("great"):
		for j in range(4):
			i = 2 + 2 * j
			if i < n:
				a = rng.uniform(-1.0, 1.0)
				r = radii[i]
				p = (r * math.sin(a), ys[i] + 0.1, zs[i] + r * math.cos(a))
				_barnacle(b, p, (math.sin(a), 0, math.cos(a)), m, 0.9)
				_on_bone(b, len(b.parts) - 2, f"seg{i}")
	_scaled(b, k)
	arm = b.build()
	pts = ys + [ys[-1] + step]

	def body(t, amp, cycles, wavelength=2.4, lift=0.0):
		out = {}

		def xat(i, y):
			grow = 0.35 + 0.65 * min(1.0, (i + 1) / 3)
			return amp * grow * math.sin(2 * math.pi * (t * cycles - y / wavelength))
		xs = [xat(i, y) for i, y in enumerate(pts)]
		for i in range(n):
			yaw = -math.degrees(math.atan2(xs[i + 1] - xs[i], step))
			out[f"seg{i}"] = {"loc": (-xs[i] * k, 0, lift * k * max(0.0, 1 - i / 3)), "rot": (0, 0, yaw)}
		hx = xat(0, ys[0] - 0.1)
		out["head"] = {"loc": (-hx * k, 0, lift * k), "rot": (0, 0, -math.degrees(math.atan2(xs[0] - hx, 0.1)) * 0.5)}
		return out

	def kl(pose):   # pose locations were written at unit size
		for v in pose.values():
			if "loc" in v:
				v["loc"] = tuple(a * k for a in v["loc"])
		return pose

	neck = ("seg0", "seg1", "seg2")

	def idle(t):
		sway = {"head": {"rot": (4 + 3 * wave(t, 1, 0.2), 0, 8 * wave(t, 1) if sea else 0), "loc": (0, 0, 0)},
				"jaw": {"rot": (-4 * max(0.0, wave(t, 2)), 0, 0)}}
		if sea:
			sway["seg0"] = {"rot": (0, 0, 0), "loc": (0.04 * k * wave(t), 0, 0.03 * k * wave(t, 1, 0.3))}
		return merge(body(t, 0.05, 1), sway)

	def walk(t):
		return body(t, 0.2, 1)

	def run(t):
		return merge(body(t, 0.24, 1, 2.8), {"root": {"loc": (0, 0, 0.02 * k * abs(wave(t, 2)))}})

	def attack(t):
		rear = seq(t, [(0, 0), (0.3, 1), (0.45, -0.4), (0.62, -0.3), (1, 0)])
		up, lunge = max(0.0, rear), max(0.0, -rear)
		gape = seq(t, [(0, 0), (0.3, 32), (0.44, 46), (0.52, 0), (0.6, 18), (0.66, 0)])
		dive = 1.0 + rise   # a reared neck strikes further down and out
		return merge(body(t, 0.04, 1), kl({"head": {"loc": (0, 0.14 * up - 0.5 * lunge * dive, 0.3 * up - 0.2 * lunge * rise), "rot": (28 * up - 10 * lunge, 0, 0)},
											"jaw": {"rot": (-gape, 0, 0)},
											"seg0": {"loc": (0, 0.06 * up - 0.3 * lunge * dive, 0.14 * up - 0.14 * lunge * rise), "rot": (14 * up, 0, 0)},
											"seg1": {"loc": (0, -0.14 * lunge, 0.05 * up), "rot": (6 * up, 0, 0)}}))

	def hit(t):
		q = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge(body(t, 0.1 * q, 2), kl({"head": {"loc": (0, 0.12 * q, 0.05 * q), "rot": (14 * q, 0, 16 * q)}, "jaw": {"rot": (-20 * q, 0, 0)}}))

	def death(t):   # the neck comes down, it thrashes, then rolls belly-up
		thrash = seq(t, [(0, 1), (0.6, 0.2), (0.85, 0)])
		roll = seq(t, [(0.3, 0), (0.72, 170), (0.82, 180)])
		gape = seq(t, [(0.3, 0), (0.8, 30)])
		drop = seq(t, [(0.05, 0), (0.35, 1)])
		pose = kl({"root": {"rot": (0, roll, 0), "loc": (0, 0, seq(t, [(0.3, 0), (0.6, 0.1), (0.8, 0.02)]))}, "jaw": {"rot": (-gape, 0, 0)}})
		for i, bn in enumerate(neck):
			pose[bn] = {"loc": (0, 0, -(zs[i] - radii[i]) * k * drop)}
		pose["head"] = {"loc": (0, 0, -(zs[0] - radii[0]) * k * drop)}
		return merge(body(t * 2, 0.22 * thrash, 1), pose)

	clip(arm, "idle", 2.6, idle, True)
	clip(arm, "walk", 1.2 * k ** 0.5, walk, True)
	clip(arm, "run", 0.7 * k ** 0.5, run, True)
	clip(arm, "attack", 0.8 + 0.15 * (k - 1), attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4 + 0.2 * (k - 1), death, False)
	return arm


# ---- the biting swarm: a cloud of midges wheeling round each other, a few fat mosquitoes on the edges

def build_biting_swarm():
	import random
	rng = random.Random(751)
	m = _rmats("biting_swarm", {"midge": ("2a2620", 0.6), "midge_l": ("4a4234", 0.6), "belly": ("a8242a", 0.4, 0.4),
								 "leg": ("1a1612", 0.6), "eye": ("d83a2a", 0.3, 1.2)})
	wing = glass_material("biting_swarm_wing", "dfe8ee", 0.45, 0.2)
	haze = glass_material("biting_swarm_haze", "4a4a3a", 0.14, 0.9)
	b = Builder("biting_swarm")
	H = 1.3
	b.bone("root", (0, 0, H))
	clusters = 6
	for c in range(clusters):
		b.bone(f"c{c}", (0, 0, H), "root")
	for c in range(clusters):
		bone = f"c{c}"
		off = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)))
		for j in range(34):
			d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 0.8))).normalized()
			p = Vector((0, 0, H)) + off + d * rng.uniform(0.1, 0.72)
			fw = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.3, 0.3))).normalized()
			_oblob(b, (0.035, 0.08, 0.035), tuple(p), tuple(fw), (0, 0, 1), m["midge"] if j % 3 else m["midge_l"], bone, segs=(5, 3))
			if j % 2 == 0:
				side = fw.cross(Vector((0, 0, 1))).normalized()
				_oblob(b, (0.06, 0.05, 0.005), tuple(p + side * 0.03 + Vector((0, 0, 0.015))), tuple(side), (0, 0, 1), wing, bone, segs=(5, 2))
	# the mosquitoes: thin bodies, a blood-full belly, long legs and a proboscis
	for j in range(6):
		bone = f"c{j % clusters}"
		a = 2 * math.pi * j / 6 + 0.3
		p = Vector((0.62 * math.cos(a), 0.62 * math.sin(a), H + rng.uniform(-0.3, 0.3)))
		fw = Vector((-math.sin(a), math.cos(a), 0))
		side = fw.cross(Vector((0, 0, 1)))
		b.blob((0.06, 0.06, 0.06), tuple(p + fw * 0.06), m["midge"], bone, segs=(6, 4))
		b.blob((0.03, 0.03, 0.03), tuple(p + fw * 0.09 + Vector((0, 0, 0.02))), m["eye"], bone, segs=(4, 3))
		b.seg(tuple(p + fw * 0.09), tuple(p + fw * 0.2 - Vector((0, 0, 0.03))), 0.008, 0.002, m["leg"], bone, sides=3)
		_oblob(b, (0.06, 0.16, 0.06), tuple(p - fw * 0.06), tuple(fw), (0, 0, 1), m["belly"], bone, segs=(6, 4))
		for s in (1, -1):
			_oblob(b, (0.1, 0.18, 0.006), tuple(p + side * s * 0.08 + Vector((0, 0, 0.03))), tuple(side * s + fw * 0.4), (0, 0, 1), wing, bone, segs=(6, 2))
			for q in (-0.03, 0.02, 0.06):
				root_ = p + fw * q
				b.seg(tuple(root_), tuple(root_ + side * s * 0.12 - Vector((0, 0, 0.12))), 0.006, 0.003, m["leg"], bone, sides=3)
	for j in range(3):   # a faint haze so the cloud reads at a distance
		b.blob((1.1 - 0.2 * j, 1.1 - 0.2 * j, 0.9 - 0.15 * j), (0.1 * (j - 1), 0.05 * j, H + 0.05 * j), haze, f"c{j}", segs=(10, 7))
	arm = b.build()
	rates = [1, -2, 1, -1, 2, -1]
	tilts = [(14, 0), (-10, 12), (0, -16), (18, 8), (-12, -10), (6, 16)]

	def wheel(t, speed=1.0, spread=1.0, drop=0.0):
		out = {"root": {"loc": (0, 0, 0.08 * wave(t, 2) - drop)}}
		for c in range(clusters):
			p, r = tilts[c]
			f = spread * (1 + 0.08 * wave(t, 3, c / clusters))
			out[f"c{c}"] = {"rot": (p * wave(t, 1, c * 0.17), r * wave(t, 1, 0.3 + c * 0.11), 360 * rates[c] * speed * t),
							"loc": (0.05 * wave(t, 2, c * 0.2), 0.05 * wave(t, 2, 0.25 + c * 0.2), 0.04 * wave(t, 3, c * 0.3)),
							"scale": (f, f, f)}
		return out

	def idle(t):
		return wheel(t)

	def walk(t):
		return merge_scaled(wheel(t, 2), {"root": {"rot": (-8, 0, 0)}})

	def run(t):
		return merge_scaled(wheel(t, 2), {"root": {"rot": (-14, 0, 0)}})

	def attack(t):   # the cloud draws in, then boils forward over its target
		k = seq(t, [(0, 0), (0.3, 1), (0.5, -1), (0.75, -0.6), (1, 0)])
		tight, burst = max(0.0, k), max(0.0, -k)
		f = 1 - 0.35 * tight + 0.3 * burst
		return merge_scaled(wheel(t, 2, f), {"root": {"loc": (0, -0.1 * tight - 0.6 * burst, -0.15 * burst)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled(wheel(t, 1, 1 + 0.45 * k), {"root": {"loc": (0, 0.2 * k, 0.1 * k)}})

	def death(t):   # the swarm breaks up and rains down into a dead scatter on the ground
		k = seq(t, [(0, 0), (0.7, 1)])
		pose = wheel(t * (1 - 0.5 * k), 1, 1 + 0.6 * k, 1.15 * k)
		for c in range(clusters):
			v = pose[f"c{c}"]
			v["scale"] = (1 + 0.6 * k, 1 + 0.6 * k, max(0.08, 1 - 0.9 * k))
			v["loc"] = (v["loc"][0], v["loc"][1], v["loc"][2] - 0.1 * k)
		return pose

	clip_scaled(arm, "idle", 3.0, idle, False)
	clip_scaled(arm, "walk", 1.5, walk, False)
	clip_scaled(arm, "run", 1.0, run, False)
	clip_scaled(arm, "attack", 0.8, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.2, death, False)
	return arm


# ---- the deep horror: a mantle of dark flesh on eight tentacles, a ring of teeth, a cluster of
# glowing eyes, anglerfish lures hanging over its face, two long grasping arms in front

def build_deep_horror():
	import random
	rng = random.Random(761)
	m = _rmats("deep_horror", {"flesh": ("2e2a4a", 0.3), "flesh_d": ("1a1630", 0.35), "flesh_l": ("5a4a74", 0.35),
								"under": ("8a6a8a", 0.4), "sucker": ("d8b8c8", 0.4), "mouth": ("0a0610", 0.6),
								"tooth": ("e8e0cc", 0.35), "eye": ("d8ff6a", 0.1, 4.0), "pupil": ("0a0a06", 0.1),
								"lid": ("3e3458", 0.4), "spot": ("4affd8", 0.2, 3.0), "lure": ("aafff0", 0.1, 6.0),
								"stalk": ("241e3a", 0.4), "barnacle": ("b8b2a8", 0.7), "hole": ("2a2630", 0.8)})
	glow = glass_material("deep_horror_lure_glass", "6ae8ff", 0.35, 0.1, 2.0)
	b = Builder("deep_horror")
	C = Vector((0, 0, 2.2))
	b.bone("root", (0, 0, 1.4))
	b.bone("body", (0, 0, 1.8), "root")
	b.bone("eyes", (0, -0.9, 2.3), "body")
	# the mantle: a great soft bulb, a paler underside, warts and glowing spots
	b.blob((2.3, 2.1, 2.3), tuple(C), m["flesh"], "body", segs=(18, 14))
	b.blob((2.1, 1.9, 0.9), (0, 0.0, 1.3), m["under"], "body", segs=(16, 9))
	for x in (-0.3, 0.0, 0.3):   # ridges over the crown
		b.blob((0.22, 1.6, 0.3), (x, 0.2, 3.12 - 0.1 * abs(x) / 0.3), m["flesh_d"], "body", rot=(-20, 0, 0), segs=(8, 8))
	for j in range(26):
		a = rng.uniform(0, 2 * math.pi)
		e = rng.uniform(-0.3, 1.2)
		d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
		p = C + Vector((1.15 * d.x, 1.05 * d.y, 1.15 * d.z))
		if j % 3 == 0:
			b.blob((0.09, 0.09, 0.09), tuple(p), m["spot"], "body", segs=(6, 4))
		else:
			b.blob((0.2, 0.2, 0.16), tuple(p), m["flesh_l"] if j % 2 else m["flesh_d"], "body", segs=(6, 4))
	for j in range(4):
		a = rng.uniform(0.3, 2.8)
		d = Vector((math.cos(a), math.sin(a), rng.uniform(0.2, 0.8))).normalized()
		_barnacle(b, tuple(C + Vector((1.15 * d.x, 1.05 * d.y, 1.15 * d.z))), tuple(d), m, 1.3)
		_on_bone(b, len(b.parts) - 2, "body")
	# the mouth: a ring of hooked teeth low on the front
	M = Vector((0, -1.02, 1.62))
	_oblob(b, (0.9, 0.7, 0.24), tuple(M), (0, 0, 1), (0, -1, 0), m["mouth"], "body", segs=(12, 8))
	_oblob(b, (1.06, 0.86, 0.14), tuple(M + Vector((0, 0.06, 0))), (0, 0, 1), (0, -1, 0), m["flesh_l"], "body", segs=(12, 6))
	for j in range(14):
		a = 2 * math.pi * j / 14
		p = M + Vector((0.46 * math.cos(a), -0.04, 0.36 * math.sin(a)))
		b.seg(tuple(p), tuple(M + Vector((0.3 * math.cos(a), -0.2, 0.22 * math.sin(a)))), 0.05, 0.0, m["tooth"], "body", sides=5)
	# the eyes: a cluster over the mouth, all sizes, lids of flesh
	eyes = [((0, 2.34), 0.36), ((-0.44, 2.22), 0.24), ((0.46, 2.26), 0.26), ((-0.28, 2.66), 0.18), ((0.3, 2.64), 0.2),
			((-0.7, 2.5), 0.14), ((0.72, 2.52), 0.13), ((0.04, 2.84), 0.12), ((-0.62, 1.98), 0.12), ((0.64, 1.98), 0.11)]
	for (x, z), r in eyes:
		u = x / 1.15
		v = (z - C.z) / 1.15
		y = -1.05 * math.sqrt(max(0.05, 1 - u * u - v * v))
		n_ = Vector((u, y / 1.05, v)).normalized()
		p = Vector((x, y, z))
		b.blob((r * 1.3, r * 1.3, r * 1.3), tuple(p + n_ * r * 0.05), m["lid"], "eyes", segs=(10, 7))
		b.blob((r, r, r), tuple(p + n_ * r * 0.42), m["eye"], "eyes", segs=(10, 7))
		_oblob(b, (r * 0.22, r * 0.7, r * 0.2), tuple(p + n_ * r * 0.86), (0, 0, 1), tuple(n_), m["pupil"], "eyes", segs=(6, 4))
	# lures: stalks arching over the head and hanging glowing bulbs in front of the eyes
	for j, x in enumerate((-0.5, 0.1, 0.62)):
		bn = f"lure{j}"
		base = Vector((x, 0.1, 3.3 - 0.1 * abs(x)))
		b.bone(bn, tuple(base), "body")
		tip = Vector((x * 1.4, -1.6 - 0.2 * (j == 1), 2.8 + 0.3 * (j == 1)))
		mid = Vector((x * 1.2, -0.9, 3.8 + 0.2 * (j == 1)))
		pts = [base + (mid - base) * u * 0.5 + Vector((0, 0, 0.2 * math.sin(math.pi * u))) for u in (0, 0.5, 1)]
		pts += [mid, mid + (tip - mid) * 0.5 + Vector((0, -0.1, 0.1)), tip]
		_chain(b, pts, 0.07, 0.025, m["stalk"], bn, sides=6)
		b.blob((0.2, 0.2, 0.24), tuple(tip - Vector((0, 0, 0.12))), m["lure"], bn, segs=(10, 7))
		b.blob((0.34, 0.34, 0.38), tuple(tip - Vector((0, 0, 0.12))), glow, bn, segs=(10, 7))
		b.seg(tuple(tip), tuple(tip - Vector((0, 0, 0.36))), 0.02, 0.0, m["lure"], bn, sides=4)
	# eight tentacles round the rim of the mantle down to the ground, their tips curled; suckers beneath
	for j in range(8):
		a = 2 * math.pi * (j + 0.5) / 8
		c_, s_ = math.cos(a), math.sin(a)
		out = Vector((c_, s_, 0))
		base = Vector((0.85 * c_, 0.8 * s_, 1.3))
		p1 = base + out * 0.55 + Vector((0, 0, -0.5))
		p2 = base + out * 1.1 + Vector((0, 0, -1.05))
		p3 = base + out * 1.6 + Vector((0, 0, -1.2))
		p4 = base + out * 1.9 + Vector((0, 0, -1.1))
		names = [f"t{j}a", f"t{j}b", f"t{j}c"]
		b.bone(names[0], tuple(base), "root")
		b.bone(names[1], tuple(p1), names[0])
		b.bone(names[2], tuple(p2), names[1])
		for bn, (p, q, r0, r1) in zip(names, ((base, p1, 0.34, 0.26), (p1, p2, 0.26, 0.17), (p2, p3, 0.17, 0.09))):
			b.seg(tuple(p), tuple(q), r0, r1, m["flesh"], bn, sides=10)
			b.blob((r0 * 2, r0 * 2, r0 * 2), tuple(p), m["flesh"], bn, segs=(8, 6))
			for u in (0.3, 0.7):
				sp = p.lerp(q, u) + Vector((0, 0, -(r0 + (r1 - r0) * u) * 0.8))
				b.blob((0.09, 0.09, 0.05), tuple(sp), m["sucker"], bn, segs=(6, 3))
		_chain(b, [p3, p4, p4 + Vector((0, 0, 0.14)) - out * 0.1], 0.09, 0.02, m["flesh_l"], names[2], sides=8)
	# two long grasping arms hanging in front, beside the mouth
	for s, side in ((1, "l"), (-1, "r")):
		base = Vector((0.66 * s, -0.86, 1.5))
		pts = [base, base + Vector((0.1 * s, -0.4, -0.5)), base + Vector((0.14 * s, -0.7, -1.0)), base + Vector((0.08 * s, -1.0, -1.34))]
		names = [f"grab_{side}{k}" for k in range(3)]
		b.bone(names[0], tuple(pts[0]), "body")
		b.bone(names[1], tuple(pts[1]), names[0])
		b.bone(names[2], tuple(pts[2]), names[1])
		for k_, bn in enumerate(names):
			r0, r1 = 0.2 - 0.05 * k_, 0.15 - 0.05 * k_
			b.seg(tuple(pts[k_]), tuple(pts[k_ + 1]), r0, max(0.04, r1), m["flesh_d"], bn, sides=8)
			b.blob((r0 * 2, r0 * 2, r0 * 2), tuple(pts[k_]), m["flesh_d"], bn, segs=(8, 6))
		club = pts[3] + Vector((0, -0.1, -0.05))
		b.blob((0.24, 0.34, 0.2), tuple(club), m["flesh_d"], names[2], segs=(8, 6))
		for k_ in range(4):
			b.blob((0.06, 0.06, 0.04), tuple(club + Vector((0.06 * (k_ % 2 * 2 - 1), -0.1 + 0.07 * k_, -0.1))), m["sucker"], names[2], segs=(5, 3))
	arm = b.build()

	def tents(t, amp, cycles=1, lift=0.0):
		out = {}
		for j in range(8):
			a = 2 * math.pi * (j + 0.5) / 8
			ph = j / 8 if cycles else 0
			w = wave(t, max(1, cycles), ph)
			up = lift * max(0.0, wave(t, max(1, cycles), ph + 0.25))
			out[f"t{j}a"] = {"rot": _lift(a, amp * w * 0.5 + up)}
			out[f"t{j}b"] = {"rot": _lift(a, amp * wave(t, max(1, cycles), ph - 0.15) * 0.6 - up * 0.5)}
			out[f"t{j}c"] = {"rot": _lift(a, amp * wave(t, max(1, cycles), ph - 0.3) + 8)}
		return out

	def arms(t, lash=0.0, reach=0.0):
		out = {}
		for s, side in ((1, "l"), (-1, "r")):
			ph = 0 if s > 0 else 0.5
			out[f"grab_{side}0"] = {"rot": (6 * wave(t, 1, ph) + 50 * reach, 0, 6 * s * wave(t, 1, ph + 0.2))}
			out[f"grab_{side}1"] = {"rot": (10 * wave(t, 1, ph - 0.2) + 30 * reach - 40 * lash, 0, 0)}
			out[f"grab_{side}2"] = {"rot": (14 * wave(t, 1, ph - 0.4) + 20 * reach - 50 * lash, 0, 0)}
		return out

	def lures(t, amp=6, flare=0.0):
		return {f"lure{j}": {"rot": (amp * wave(t, 1, j * 0.3) + flare, 0, amp * 0.6 * wave(t, 1, j * 0.3 + 0.25))} for j in range(3)}

	def breathe(t, k=0.03):
		f = 1 + k * wave(t)
		return {"body": {"scale": (f, f, 1 + k * 0.6 * wave(t, 1, 0.1))}, "eyes": {"scale": (1, 1, 1)}}

	def idle(t):
		return merge_scaled(tents(t, 6), arms(t), lures(t), breathe(t), {"root": {"loc": (0, 0, 0.04 * wave(t))}})

	def walk(t):
		return merge_scaled(tents(t, 14, 1, 18), arms(t), lures(t, 10), {"root": {"loc": (0, 0, 0.1 * abs(wave(t, 2))), "rot": (-4, 3 * wave(t), 0)}})

	def run(t):
		return merge_scaled(tents(t, 20, 2, 24), arms(t, 0, 0.3), lures(t, 14), {"root": {"loc": (0, 0, 0.14 * abs(wave(t, 2))), "rot": (-8, 4 * wave(t), 0)}})

	def attack(t):   # rears back, lures flaring, then the grasping arms whip forward and down
		r = seq(t, [(0, 0), (0.35, 1), (0.5, -1), (0.7, -0.8), (1, 0)])
		back, fwd = max(0.0, r), max(0.0, -r)
		return merge_scaled(tents(t, 6), arms(t, fwd, back * 0.6 + fwd * 1.1), lures(t, 4, -20 * back + 10 * fwd),
							{"root": {"loc": (0, 0.2 * back - 0.4 * fwd, 0.15 * back), "rot": (12 * back - 12 * fwd, 0, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled(tents(t, 10 * k + 4, 2), arms(t, 0, -0.3 * k), lures(t, 6, 20 * k),
							{"root": {"loc": (0, 0.25 * k, 0), "rot": (10 * k, 6 * k, 0)}})

	def death(t):   # the lights go out of it; it slumps and spreads on the ground
		k = seq(t, [(0.1, 0), (0.8, 1)])
		out = merge_scaled(tents(t * (1 - k), 10 * (1 - k)), arms(t, 0, -0.6 * k), lures(t, 0, 40 * k),
						   {"root": {"loc": (0, 0, -1.0 * k), "rot": (8 * k, 5 * k, 0)},
							"body": {"scale": (1 + 0.15 * k, 1 + 0.15 * k, 1 - 0.25 * k)}})
		for j in range(8):
			a = 2 * math.pi * (j + 0.5) / 8
			out[f"t{j}a"] = {"rot": _lift(a, 30 * k)}
			out[f"t{j}b"] = {"rot": _lift(a, -10 * k)}
			out[f"t{j}c"] = {"rot": _lift(a, -12 * k)}
		return out

	clip_scaled(arm, "idle", 3.2, idle, True)
	clip_scaled(arm, "walk", 1.8, walk, True)
	clip_scaled(arm, "run", 1.0, run, True)
	clip_scaled(arm, "attack", 1.1, attack, False)
	clip_scaled(arm, "hit", 0.5, hit, False)
	clip_scaled(arm, "death", 1.8, death, False)
	return arm


# ---- the giant gull: white and gray on long black-tipped wings, hanging in the wind over the harbor

def build_giant_gull():
	m = _rmats("giant_gull", {"white": ("f2f2ee", 0.8), "gray": ("a8b0b8", 0.8), "gray_d": ("7a8490", 0.8),
							   "black": ("1e1e22", 0.7), "beak": ("f0c030", 0.4), "red": ("d83a2a", 0.4), "leg": ("e8a878", 0.6),
							   "eye": ("f4ecb0", 0.2, 0.6), "pupil": ("0c0a08", 0.2), "ring": ("d84a2a", 0.4)})
	b = Builder("giant_gull")
	H = 1.9
	b.bone("root", (0, 0, H))
	b.bone("body", (0, 0, H), "root")
	b.bone("neck", (0, -0.26, H + 0.08), "body")
	b.bone("head", (0, -0.42, H + 0.26), "neck")
	b.bone("tail", (0, 0.36, H - 0.02), "body")
	b.bone("legs", (0, 0.08, H - 0.18), "body")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"wing_{side}", (0.16 * s, -0.06, H + 0.08), "body")
		b.bone(f"tip_{side}", (0.92 * s, 0.02, H + 0.1), f"wing_{side}")
	b.blob((0.5, 0.96, 0.48), (0, 0.04, H), m["white"], "body", rot=(-8, 0, 0), segs=(12, 9))
	b.blob((0.42, 0.74, 0.2), (0, 0.12, H + 0.16), m["gray"], "body", rot=(-6, 0, 0), segs=(10, 6))
	b.seg((0, -0.2, H + 0.06), (0, -0.42, H + 0.26), 0.16, 0.13, m["white"], "neck", sides=8)
	b.blob((0.3, 0.38, 0.3), (0, -0.48, H + 0.3), m["white"], "head", segs=(10, 8))
	b.seg((0, -0.64, H + 0.3), (0, -0.88, H + 0.26), 0.055, 0.03, m["beak"], "head", sides=6)
	b.seg((0, -0.88, H + 0.26), (0, -0.92, H + 0.2), 0.03, 0.004, m["beak"], "head", sides=5)
	b.seg((0, -0.64, H + 0.24), (0, -0.84, H + 0.22), 0.035, 0.02, m["beak"], "head", sides=5)
	b.blob((0.04, 0.04, 0.045), (0, -0.82, H + 0.21), m["red"], "head", segs=(5, 4))
	for s in (1, -1):
		b.blob((0.075, 0.05, 0.065), (0.11 * s, -0.56, H + 0.35), m["ring"], "head", segs=(6, 4))
		b.blob((0.065, 0.05, 0.055), (0.12 * s, -0.565, H + 0.35), m["eye"], "head", segs=(6, 4))
		b.blob((0.03, 0.02, 0.03), (0.135 * s, -0.58, H + 0.35), m["pupil"], "head", segs=(5, 3))
		b.blob((0.1, 0.12, 0.04), (0.1 * s, -0.54, H + 0.41), m["white"], "head", rot=(0, -18 * s, 0), segs=(6, 3))   # the stern brow
		side = "l" if s > 0 else "r"
		wing, tip = f"wing_{side}", f"tip_{side}"
		b.seg((0.14 * s, -0.06, H + 0.08), (0.92 * s, 0.02, H + 0.1), 0.065, 0.045, m["white"], wing, sides=6)
		for k in range(7):   # the gray arm of the wing, a white trailing edge
			x = (0.2 + 0.11 * k) * s
			_oblob(b, (0.13, 0.46, 0.03), (x, 0.2, H + 0.08), (0.05 * s, 1, -0.05), (0, 0, 1), m["gray"] if k % 2 else m["gray_d"], wing, segs=(6, 4))
			_oblob(b, (0.12, 0.14, 0.03), (x, 0.44, H + 0.07), (0.05 * s, 1, -0.05), (0, 0, 1), m["white"], wing, segs=(6, 4))
		for k in range(4):
			x = (0.24 + 0.18 * k) * s
			_oblob(b, (0.18, 0.24, 0.04), (x, 0.04, H + 0.12), (0.05 * s, 1, 0), (0, 0, 1), m["gray"], wing, segs=(6, 4))
		for k in range(7):   # the long primaries, black with white mirrors near the tips
			a = math.radians(-8 + 9 * k)
			d = Vector((math.cos(a) * s, math.sin(a), -0.02)).normalized()
			ln = 0.9 - 0.06 * k
			base = Vector((0.92 * s, 0.03, H + 0.1))
			_oblob(b, (0.13, ln, 0.03), tuple(base + d * ln * 0.5), tuple(d), (0, 0, 1), m["gray"] if k > 4 else m["black"], tip, segs=(6, 4))
			if k < 3:
				_oblob(b, (0.08, 0.12, 0.035), tuple(base + d * ln * 0.8), tuple(d), (0, 0, 1), m["white"], tip, segs=(5, 3))
		_oblob(b, (0.2, 0.34, 0.05), (0.96 * s, 0.1, H + 0.12), (s, 0.4, 0), (0, 0, 1), m["gray"], tip, segs=(6, 4))
	for k in range(5):
		yaw = math.radians((k - 2) * 12)
		d = Vector((math.sin(yaw), math.cos(yaw), -0.12)).normalized()
		_oblob(b, (0.12, 0.44, 0.03), tuple(Vector((0, 0.34, H - 0.02)) + d * 0.24), tuple(d), (0, 0, 1), m["white"], "tail", segs=(6, 4))
	for s in (1, -1):   # legs trailing, webbed feet
		b.seg((0.08 * s, 0.08, H - 0.16), (0.08 * s, 0.24, H - 0.42), 0.03, 0.022, m["leg"], "legs", sides=5)
		_oblob(b, (0.16, 0.18, 0.02), (0.08 * s, 0.32, H - 0.46), (0, 1, -0.6), (0, 0.6, 1), m["leg"], "legs", segs=(6, 3))
	arm = b.build()

	def beat(t, cycles, amp=30, lift=0.0):
		f = amp * wave(t, cycles) + lift
		g = amp * 0.6 * wave(t, cycles, -0.12) + lift * 0.4
		return {"wing_l": {"rot": (0, f, 0)}, "wing_r": {"rot": (0, -f, 0)}, "tip_l": {"rot": (0, g, 0)}, "tip_r": {"rot": (0, -g, 0)}}

	def idle(t):   # hangs on the wind: slow shallow beats, the head turning to look
		return merge({"root": {"loc": (0, 0, -0.06 * wave(t, 2, 0.1))}, "body": {"rot": (3 * wave(t, 2, 0.3), 3 * wave(t), 0)},
					  "head": {"rot": (-3 * wave(t, 2, 0.3), 0, seq(t, [(0, 0), (0.3, 30), (0.5, 30), (0.6, -24), (0.85, -24), (1, 0)]))},
					  "legs": {"rot": (-20, 0, 0)}, "tail": {"rot": (4 * wave(t, 2), 0, 0)}}, beat(t, 2, 22, 6))

	def walk(t):
		return merge({"root": {"loc": (0, 0, -0.05 * wave(t, 2, 0.1)), "rot": (-10, 0, 0)}, "head": {"rot": (8, 0, 0)},
					  "legs": {"rot": (-40, 0, 0)}}, beat(t, 2, 30, 4))

	def run(t):
		return merge({"root": {"loc": (0, 0, -0.04 * wave(t, 2, 0.1)), "rot": (-18, 0, 0)}, "head": {"rot": (14, 0, 0)},
					  "legs": {"rot": (-55, 0, 0)}}, beat(t, 3, 36, 0))

	def attack(t):   # up on high wings, then a plunge and a stab of the beak
		rear = seq(t, [(0, 0), (0.35, 1), (0.55, -0.6), (0.75, -0.4), (1, 0)])
		dive = seq(t, [(0, 0), (0.35, -0.1), (0.55, 0.5), (0.75, 0.4), (1, 0)])
		wings = seq(t, [(0, 0), (0.35, 55), (0.55, -30), (0.75, -16), (1, 0)])
		stab = seq(t, [(0.4, 0), (0.55, -30), (0.7, -26), (0.85, 0)])
		return merge({"root": {"loc": (0, dive, 0.12 * rear - 0.3 * max(0.0, -rear)), "rot": (26 * rear, 0, 0)},
					  "neck": {"rot": (stab * 0.5, 0, 0), "loc": (0, -0.1 * max(0.0, -rear), 0)}, "head": {"rot": (-18 * rear + stab * 0.5, 0, 0)},
					  "legs": {"rot": (seq(t, [(0, -20), (0.35, 10), (0.55, 40), (1, -20)]), 0, 0)},
					  "wing_l": {"rot": (0, wings, 0)}, "wing_r": {"rot": (0, -wings, 0)},
					  "tip_l": {"rot": (0, wings * 0.5, 0)}, "tip_r": {"rot": (0, -wings * 0.5, 0)}})

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.2 * k, 0.1 * k), "rot": (18 * k, 14 * k, 0)}, "head": {"rot": (14 * k, 0, 20 * k)}},
					 beat(t, 2, 26, 26 * k))

	def death(t):   # the wings fold wrong; it tumbles down and lies with a wing spread
		f = seq(t, [(0.1, 0), (0.7, 1)])
		g = seq(t, [(0.5, 0), (0.95, 1)])
		flap = 1 - seq(t, [(0.1, 0), (0.5, 1)])
		return merge({"root": {"loc": (0, 0.1 * f, -(H - 0.26) * f + 0.08 * math.sin(math.pi * f)), "rot": (-16 * f, 72 * g, 0)},
					  "neck": {"rot": (-30 * g, 0, 20 * g)}, "head": {"rot": (-20 * g, 0, 30 * g)}, "legs": {"rot": (40 * g, 0, 0)},
					  "wing_l": {"rot": (0, 30 * flap * wave(t, 3) - 58 * g, 0)}, "wing_r": {"rot": (0, -30 * flap * wave(t, 3) - 66 * g, 0)},
					  "tip_l": {"rot": (0, -14 * g, 0)}, "tip_r": {"rot": (0, -8 * g, 0)}, "tail": {"rot": (10 * g, 0, 20 * g)}})

	clip(arm, "idle", 2.4, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


# ---- the sea lion: a heavy bull propped up on its fore flippers, thick-necked, whiskered, bellowing

def build_sea_lion():
	m = _rmats("sea_lion", {"hide": ("7a6a58", 0.4), "hide_d": ("54483c", 0.45), "hide_l": ("a08c72", 0.45),
							 "flip": ("3e342c", 0.45), "nose": ("1e1814", 0.35), "eye": ("0e0a08", 0.08), "shine": ("f0f0f0", 0.1, 0.8),
							 "whisker": ("ece4d4", 0.5), "mouth": ("9a4a48", 0.6), "tooth": ("efe6d0", 0.4), "scar": ("b09a88", 0.6)})
	b = Builder("sea_lion")
	b.bone("root", (0, 0, 0.5))
	b.bone("chest", (0, -0.2, 0.62), "root")
	b.bone("neck", (0, -0.62, 0.95), "chest")
	b.bone("head", (0, -0.8, 1.32), "neck")
	b.bone("jaw", (0, -1.0, 1.26), "head")
	b.bone("hind", (0, 0.3, 0.45), "root")
	for s, side in ((1, "l"), (-1, "r")):
		b.bone(f"flip_f{side}", (0.36 * s, -0.5, 0.6), "chest")
		b.bone(f"flip_b{side}", (0.2 * s, 1.25, 0.18), "hind")
	b.blob((0.98, 1.1, 0.96), (0, -0.3, 0.68), m["hide"], "chest", segs=(14, 10))
	b.blob((0.78, 0.6, 0.72), (0, -0.56, 0.66), m["hide_l"], "chest", segs=(12, 8))
	b.blob((0.86, 1.0, 0.66), (0, 0.4, 0.44), m["hide"], "hind", segs=(14, 9))
	b.blob((0.62, 0.72, 0.44), (0, 0.95, 0.3), m["hide"], "hind", segs=(12, 8))
	b.blob((0.36, 0.42, 0.24), (0, 1.28, 0.2), m["hide_d"], "hind", segs=(10, 6))
	b.blob((0.7, 1.2, 0.3), (0, 0.2, 0.74), m["hide_d"], "hind", segs=(12, 6))
	b.seg((0, -0.5, 0.82), (0, -0.78, 1.22), 0.37, 0.27, m["hide"], "neck", sides=12)
	b.blob((0.7, 0.54, 0.62), (0, -0.6, 1.02), m["hide_d"], "neck", segs=(12, 8))                  # the bull's heavy mane
	for k in range(3):
		b.seg((0.3 - 0.1 * k, -0.7, 1.1), (0.34 - 0.1 * k, -0.62, 0.9), 0.015, 0.012, m["scar"], "neck", sides=4)
	b.blob((0.46, 0.54, 0.44), (0, -0.86, 1.38), m["hide"], "head", segs=(12, 9))
	b.blob((0.3, 0.34, 0.26), (0, -1.1, 1.32), m["hide_l"], "head", segs=(10, 7))
	b.blob((0.13, 0.07, 0.08), (0, -1.26, 1.36), m["nose"], "head", segs=(8, 5))
	b.blob((0.26, 0.14, 0.16), (0, -0.96, 1.52), m["hide_d"], "head", segs=(8, 5))                  # the domed brow
	for s in (1, -1):
		b.blob((0.11, 0.09, 0.11), (0.15 * s, -1.02, 1.46), m["eye"], "head", segs=(8, 5))
		b.blob((0.03, 0.02, 0.03), (0.17 * s, -1.06, 1.48), m["shine"], "head", segs=(4, 3))
		b.seg((0.2 * s, -0.84, 1.5), (0.25 * s, -0.78, 1.52), 0.025, 0.008, m["hide_d"], "head", sides=4)
		for k in range(4):
			b.seg((0.1 * s, -1.2, 1.32 - 0.02 * k), (0.36 * s, -1.26 - 0.02 * k, 1.34 - 0.04 * k), 0.008, 0.003, m["whisker"], "head", sides=3)
	b.blob((0.24, 0.3, 0.12), (0, -1.08, 1.2), m["hide_l"], "jaw", segs=(10, 6))
	b.blob((0.2, 0.26, 0.05), (0, -1.1, 1.25), m["mouth"], "jaw", segs=(8, 4))
	for s in (1, -1):
		b.seg((0.07 * s, -1.2, 1.24), (0.07 * s, -1.2, 1.32), 0.02, 0.0, m["tooth"], "jaw", sides=4)
		fl, bl = f"flip_f{'l' if s > 0 else 'r'}", f"flip_b{'l' if s > 0 else 'r'}"
		b.blob((0.26, 0.32, 0.42), (0.4 * s, -0.5, 0.5), m["hide"], fl, segs=(8, 6))
		_oblob(b, (0.2, 0.62, 0.05), (0.52 * s, -0.66, 0.26), (0.3 * s, -0.4, -1), (s, 0, 0), m["flip"], fl, segs=(8, 4))
		_oblob(b, (0.36, 0.52, 0.04), (0.24 * s, 1.5, 0.06), (0.35 * s, 1, 0), (0, 0, 1), m["flip"], bl, segs=(8, 4))
	arm = b.build()

	def idle(t):   # looks about, then throws its head back and bellows
		bell = seq(t, [(0.5, 0), (0.6, 1), (0.8, 1), (0.9, 0)])
		return {"chest": {"rot": (2 * wave(t, 2) + 6 * bell, 0, 0)}, "neck": {"rot": (14 * bell, 0, 10 * wave(t) * (1 - bell))},
				"head": {"rot": (16 * bell + 3 * wave(t, 4) * bell, 0, 8 * wave(t, 1, 0.2) * (1 - bell))}, "jaw": {"rot": (-30 * bell, 0, 0)},
				"flip_bl": {"rot": (0, 0, 6 * wave(t, 2))}, "flip_br": {"rot": (0, 0, -6 * wave(t, 2))}}

	def gallop(t, amp, lift):
		return {"chest": {"rot": (6 * amp * wave(t), 0, 0), "loc": (0, 0, lift * max(0.0, wave(t)))},
				"hind": {"rot": (-5 * amp * wave(t, 1, 0.35), 0, 0), "loc": (0, 0, lift * 0.6 * max(0.0, wave(t, 1, 0.4)))},
				"flip_fl": {"rot": (22 * amp * wave(t, 1, 0.1), 0, 0)}, "flip_fr": {"rot": (22 * amp * wave(t, 1, 0.6), 0, 0)},
				"flip_bl": {"rot": (0, 0, 10 * amp * wave(t, 1, 0.4))}, "flip_br": {"rot": (0, 0, -10 * amp * wave(t, 1, 0.4))},
				"neck": {"rot": (-6 * amp * wave(t, 1, 0.1), 0, 0)}, "head": {"rot": (4 * amp * wave(t, 1, 0.2), 0, 0)}}

	def walk(t):
		return gallop(t, 1.0, 0.06)

	def run(t):
		return gallop(t, 1.6, 0.14)

	def attack(t):   # rears up on its flippers, then lunges down with a bite
		r = seq(t, [(0, 0), (0.35, 1), (0.52, -0.8), (0.7, -0.6), (1, 0)])
		up, fwd = max(0.0, r), max(0.0, -r)
		gape = seq(t, [(0, 0), (0.35, 34), (0.5, 40), (0.56, 0), (1, 0)])
		return {"root": {"loc": (0, -0.3 * fwd, 0)}, "chest": {"rot": (16 * up - 8 * fwd, 0, 0), "loc": (0, 0, 0.1 * up)},
				"neck": {"rot": (16 * up - 26 * fwd, 0, 0)}, "head": {"rot": (10 * up - 12 * fwd, 0, 0)}, "jaw": {"rot": (-gape, 0, 0)},
				"flip_fl": {"rot": (-20 * up, 0, 0)}, "flip_fr": {"rot": (-20 * up, 0, 0)}}

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return {"chest": {"rot": (8 * k, 6 * k, 0)}, "neck": {"rot": (14 * k, 0, 12 * k)}, "head": {"rot": (10 * k, 0, 10 * k)}, "jaw": {"rot": (-20 * k, 0, 0)}}

	def death(t):   # flops onto its side, the head coming down last
		k = seq(t, [(0.1, 0), (0.6, 1)])
		g = seq(t, [(0.45, 0), (0.9, 1)])
		return {"root": {"loc": (0, 0, -0.14 * k), "rot": (0, 78 * k, 0)}, "chest": {"rot": (-8 * k, 0, 0)},
				"neck": {"rot": (-30 * g, 0, 16 * g)}, "head": {"rot": (-16 * g, 0, 10 * g)}, "jaw": {"rot": (-14 * g, 0, 0)},
				"flip_fl": {"rot": (30 * k, 0, 0)}, "flip_fr": {"rot": (-20 * k, 0, 0)}}

	clip(arm, "idle", 4.0, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.9, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


# ---- the tempest lord: a towering thunderhead with a man's shoulders, standing on curtains of rain,
# a crown of storm turning over its head (a ring of cloud, lightning tines and hailstones), a spear of
# forked lightning in its right hand; Jalendra's teal in its lightning, not the storm spirits' white

def build_tempest_lord():
	import random
	rng = random.Random(771)
	dark = material("tempest_lord_cloud_dark", "262a40", 0.9)
	mid = material("tempest_lord_cloud", "3a405c", 0.9)
	light = material("tempest_lord_cloud_light", "646e90", 0.9, emit=0.1)
	core = material("tempest_lord_core", "e8fffa", 0.2, emit=7.0)
	core_t = material("tempest_lord_core_teal", "5affe0", 0.2, emit=4.0)
	bolt = material("tempest_lord_bolt", "9afff0", 0.2, emit=5.0)
	eye = material("tempest_lord_eye", "f0fffc", 0.1, emit=7.0)
	hail = material("tempest_lord_hail", "dff4ff", 0.2, emit=0.6)
	rain = glass_material("tempest_lord_rain", "bfeaf0", 0.4, 0.1, 0.4)
	b = Builder("tempest_lord")
	b.bone("root", (0, 0, 0.1))
	b.bone("low", (0, 0, 0.4), "root")
	b.bone("swirl", (0, 0, 0.4), "low")
	b.bone("mid", (0, 0, 1.7), "low")
	b.bone("core", (0, -0.1, 2.5), "mid")
	b.bone("chest", (0, 0, 2.6), "mid")
	b.bone("head", (0, -0.12, 3.5), "chest")
	b.bone("crown", (0, -0.06, 4.2), "head")
	b.bone("cape", (0, 0.5, 3.2), "chest")

	def puff(loc, r, bone, mats=(dark, mid, light), n=3):
		for k in range(n):
			off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 0.6))) * r * 0.45
			sz = r * rng.uniform(0.75, 1.15)
			b.blob((sz, sz, sz * 0.85), tuple(Vector(loc) + off), mats[(k + int(r * 10)) % len(mats)], bone, segs=(9, 6))

	# the rain: sheets of streaks falling from a skirt of cloud, spreading as they fall (on the swirl bone)
	for k in range(56):
		a = 2 * math.pi * k / 56 + rng.uniform(-0.05, 0.05)
		r0 = rng.uniform(0.35, 0.95)
		top = Vector((r0 * math.cos(a), r0 * math.sin(a), rng.uniform(1.5, 1.9)))
		bot = Vector((r0 * 1.35 * math.cos(a), r0 * 1.35 * math.sin(a), rng.uniform(0.05, 0.4)))
		b.seg(tuple(top), tuple(bot), 0.022, 0.012, rain, "swirl", sides=4)
	for k in range(3):   # bolts walking down through the rain
		a = 2 * math.pi * k / 3 + 0.4
		p = Vector((0.6 * math.cos(a), 0.6 * math.sin(a), 1.6))
		_zigzag(b, [tuple(p), tuple(p + Vector((0.12, 0.05, -0.5))), tuple(p + Vector((-0.06, 0.1, -0.9))), tuple(p * 1.3 + Vector((0, 0, -1.4)))], 0.03, bolt, "swirl")
	for k in range(16):   # the skirt of cloud
		a = 2 * math.pi * (k + 0.5) / 16
		puff((0.82 * math.cos(a), 0.78 * math.sin(a), 1.8 + 0.1 * wave(k / 16, 3)), 0.46, "mid", n=2)
	b.seg((0, 0, 0.8), (0, 0, 2.0), 0.1, 0.7, dark, "mid", sides=12)
	# the core: a teal-white heart seen through a rent in the chest, lightning branching from it
	b.blob((0.5, 0.44, 0.62), (0, -0.12, 2.5), core, "core", segs=(12, 9))
	b.blob((0.74, 0.64, 0.9), (0, -0.08, 2.5), core_t, "core", segs=(12, 9))
	for k in range(7):
		a = 2 * math.pi * k / 7 + 0.2
		d = Vector((math.cos(a), math.sin(a) * 0.7, rng.uniform(-0.4, 0.7))).normalized()
		p = Vector((0, -0.1, 2.5))
		_zigzag(b, [tuple(p + d * 0.26), tuple(p + d * 0.46 + Vector((0.05, 0, 0.08))), tuple(p + d * 0.66 - Vector((0.04, 0, 0.05))),
					tuple(p + d * 0.84)], 0.032, bolt, "core")
	# the chest: a towering thunderhead with broad shoulders, open over the heart
	for k in range(16):
		a = 2 * math.pi * (k + 0.5) / 16
		for z in (2.2, 2.6, 2.95):
			rr = 0.7 if z < 2.9 else 0.62
			if math.sin(a) < -0.72 and z < 2.9:
				continue
			puff((rr * math.cos(a), rr * 0.85 * math.sin(a), z), 0.44 if z < 2.9 else 0.4, "chest" if z > 2.3 else "mid", n=2)
	for s in (1, -1):
		puff((0.92 * s, 0.02, 3.12), 0.58, "chest")
		puff((0.7 * s, 0.22, 3.34), 0.44, "chest")
		for k in range(2):   # lightning veins over the shoulders
			p = Vector((0.6 * s, -0.4, 3.2 - 0.2 * k))
			_zigzag(b, [tuple(p), tuple(p + Vector((0.14 * s, -0.08, -0.18))), tuple(p + Vector((0.08 * s, -0.12, -0.36))), tuple(p + Vector((0.24 * s, -0.1, -0.5)))], 0.026, bolt, "chest")
	# the cape: a mantle of cloud streaming behind
	for k in range(9):
		u = k / 8
		x = (u - 0.5) * 1.4
		puff((x, 0.6 + 0.2 * u * (1 - u), 3.1 - 0.9 * abs(x) * 0.4), 0.42, "cape", mats=(dark, mid), n=2)
		puff((x * 1.1, 0.74, 2.4), 0.36, "cape", mats=(dark, mid), n=2)
	# the head: a hooded billow, a face of shadow, two blazing eyes, a beard of rain
	puff((0, 0.06, 3.62), 0.6, "head", n=4)
	puff((0, 0.2, 3.86), 0.44, "head")
	b.blob((0.54, 0.26, 0.4), (0, -0.3, 3.56), dark, "head", segs=(10, 6))
	for s in (1, -1):
		b.blob((0.16, 0.06, 0.08), (0.13 * s, -0.43, 3.62), eye, "head", rot=(0, 0, -16 * s), segs=(8, 5))
	for k in range(9):
		x = (k - 4) * 0.06
		b.seg((x, -0.38, 3.4), (x * 1.3, -0.44, 2.9 - 0.06 * (k % 3)), 0.018, 0.008, rain, "head", sides=4)
	# the crown of storm: a ring of cloud floating over the brow, lightning tines, hailstones riding it,
	# a teal halo under it
	for k in range(12):
		a = 2 * math.pi * k / 12
		puff((0.44 * math.cos(a), -0.06 + 0.44 * math.sin(a), 4.2), 0.2, "crown", mats=(mid, light), n=2)
	for k in range(7):
		a = 2 * math.pi * k / 7 - math.pi / 2
		base = Vector((0.44 * math.cos(a), -0.06 + 0.44 * math.sin(a), 4.28))
		out = Vector((math.cos(a), math.sin(a), 0)) * 0.1
		tall = 0.66 if k == 0 else 0.44
		_zigzag(b, [tuple(base), tuple(base + out + Vector((0.05, 0, tall * 0.35))), tuple(base + out * 1.4 - Vector((0.05, 0, 0)) + Vector((0, 0, tall * 0.65))),
					tuple(base + out * 2 + Vector((0, 0, tall)))], 0.04, bolt, "crown")
		b.blob((0.1, 0.1, 0.1), tuple(base + out * 2 + Vector((0, 0, tall))), core, "crown", segs=(6, 4))
	start = len(b.parts)
	_ring(b, (0, -0.06, 4.12), (0.54, 0.54), (0, 0), 0.03, core_t, sides=20)
	_on_bone(b, start, "crown")
	for k in range(10):
		a = 2 * math.pi * (k + 0.5) / 10
		_rock(b, (0.12, 0.12, 0.12), (0.64 * math.cos(a), -0.06 + 0.64 * math.sin(a), 4.2 + 0.08 * math.sin(3 * a)), hail, "crown", rng)
	# arms of cloud; the right hand holds a spear of forked lightning, the left crackles open
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"arm_{side}", (0.92 * s, 0, 3.1), "chest")
		b.bone(f"hand_{side}", (1.24 * s, -0.12, 2.1), f"arm_{side}")
		for k in range(5):
			u = k / 4
			puff((s * (0.98 + 0.26 * u), -0.12 * u, 3.0 - 0.9 * u), 0.44 - 0.1 * u, f"arm_{side}", n=2)
		_zigzag(b, [(1.0 * s, -0.3, 3.0), (1.12 * s, -0.36, 2.7), (1.04 * s, -0.34, 2.5), (1.2 * s, -0.36, 2.26)], 0.03, bolt, f"arm_{side}")
		puff((1.26 * s, -0.14, 1.96), 0.38, f"hand_{side}", n=3)
		if s > 0:
			for k in range(4):
				a = math.radians(-50 + 33 * k)
				root_ = Vector((1.26, -0.24, 1.84))
				d = Vector((0.3 * math.sin(a), -0.5 * math.cos(a), -0.8)).normalized()
				pts = [root_, root_ + d * 0.18 + Vector((0.05, 0, 0)), root_ + d * 0.32 - Vector((0.04, 0, 0)), root_ + d * 0.48]
				_zigzag(b, [tuple(p) for p in pts], 0.035, bolt, "hand_l")
				b.blob((0.08, 0.08, 0.08), tuple(pts[-1]), core, "hand_l", segs=(6, 4))
		else:   # the spear: a jagged shaft of lightning, a forked head, held upright
			g = Vector((-1.3, -0.26, 1.96))
			shaft = [g + Vector((0, 0, -1.3)), g + Vector((0.06, 0, -0.6)), g + Vector((-0.05, 0, 0.1)), g + Vector((0.05, 0, 0.8)), g + Vector((0, 0, 1.5))]
			_zigzag(b, [tuple(p) for p in shaft], 0.085, bolt, "hand_r")
			_zigzag(b, [tuple(p) for p in shaft], 0.045, core, "hand_r")
			top = shaft[-1]
			for dx in (-0.2, 0.0, 0.2):
				_zigzag(b, [tuple(top), tuple(top + Vector((dx * 0.6, 0, 0.2))), tuple(top + Vector((dx * 0.9 + 0.04, 0, 0.36))), tuple(top + Vector((dx, 0, 0.58)))], 0.04, bolt, "hand_r")
			b.blob((0.16, 0.16, 0.16), tuple(top), core, "hand_r", segs=(8, 6))
	arm = b.build()

	def arms(l, r, spread=0.0, bend=0.0):
		return {"arm_l": {"rot": (l, spread, 0)}, "arm_r": {"rot": (r, -spread, 0)},
				"hand_l": {"rot": (bend, spread * 0.5, 0)}, "hand_r": {"rot": (bend * 0.4, -spread * 0.5, 0)}}

	def body(t, lean, sway, turns=1, flicker=0.07):
		f = 1 + flicker * wave(t, 7) * wave(t, 3, 0.2)
		return {"low": {"rot": (lean + 2 * wave(t, 1, 0.25), sway * wave(t), 0)},
				"mid": {"rot": (lean * 0.4, -sway * 0.6 * wave(t, 1, 0.1), 3 * wave(t))},
				"chest": {"rot": (lean * 0.2, -sway * 0.4 * wave(t, 1, 0.2), -3 * wave(t, 1, 0.3))},
				"head": {"rot": (-lean * 0.5 + 3 * wave(t, 1, 0.6), 0, 5 * wave(t, 1, 0.1))},
				"swirl": {"rot": (0, 0, 360 * turns * t)}, "core": {"scale": (f, f, f)},
				"crown": {"rot": (3 * wave(t, 1, 0.2), 3 * wave(t, 1, 0.45), -360 * t), "loc": (0, 0, 0.05 * wave(t, 2))},
				"cape": {"rot": (-6 + 5 * wave(t, 2), 0, 4 * wave(t, 1, 0.3))},
				"root": {"loc": (0, 0, 0.06 * wave(t, 2))}}

	def idle(t):
		return merge_scaled(body(t, 0, 3), arms(6 * wave(t, 1, 0.1), 4 * wave(t, 1, 0.6), 6, 8 + 4 * wave(t)))

	def walk(t):
		return merge_scaled(body(t, -8, 4, 2), arms(12 * wave(t), -8 * wave(t), 6, 10))

	def run(t):
		return merge_scaled(body(t, -16, 5, 2), arms(-30 + 8 * wave(t, 2), -20 - 6 * wave(t, 2), 10, 16))

	def attack(t):   # raises the spear high, the crown blazing, and drives it down
		k = seq(t, [(0, 0), (0.4, -1), (0.55, 1), (0.75, 0.8), (1, 0)])
		up, down = max(0.0, -k), max(0.0, k)
		flare = 1 + 0.4 * seq(t, [(0.3, 0), (0.5, 1), (0.8, 0.3), (1, 0)])
		pose = merge_scaled(body(t, 10 * up - 16 * down, 2), arms(20 * up + 40 * down, 110 * up - 30 * down, 10 * up, -10 * down),
							{"core": {"scale": (flare, flare, flare)}, "crown": {"scale": (flare, flare, flare)},
							 "root": {"loc": (0, 0.3 * down, 0.1 * up)}})
		return pose

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		f = 1 + 0.3 * k * wave(t, 4)
		return merge_scaled(body(t, 10 * k, 3), arms(-20 * k, -16 * k, 14 * k, -10 * k),
							{"core": {"scale": (f, f, f)}, "root": {"loc": (0, -0.12 * k, 0)}, "head": {"rot": (12 * k, 0, 10 * k)}})

	def death(t):   # the heart gutters, the crown breaks up and falls, the storm spreads out and thins to rain
		reel = seq(t, [(0, 0), (0.2, 12), (0.35, -8), (0.5, 0)])
		f = seq(t, [(0.25, 0), (0.9, 1)])
		c = max(0.02, 1 + 0.4 * seq(t, [(0, 0), (0.15, 1), (0.3, 0)]) - seq(t, [(0.3, 0), (0.7, 1)]))
		spread = 1 + 0.8 * f
		return merge_scaled(body(t, 0, 2, 1, 0.0),
							{"low": {"rot": (reel, reel * 0.4, 0), "loc": (0, 0, -0.3 * f), "scale": (spread, spread, max(0.12, 1 - 0.8 * f))},
							 "mid": {"rot": (-reel * 0.6, 0, 0), "scale": (1 + 0.3 * f, 1 + 0.3 * f, max(0.2, 1 - 0.7 * f))},
							 "chest": {"scale": (1 + 0.2 * f, 1 + 0.2 * f, max(0.3, 1 - 0.5 * f))},
							 "head": {"rot": (reel + 20 * f, 0, 20 * f), "scale": (1 + 0.3 * f, 1 + 0.3 * f, max(0.3, 1 - 0.6 * f))},
							 "crown": {"loc": (0.3 * f, -0.4 * f, -1.2 * f), "scale": (max(0.05, 1 - f),) * 3}, "core": {"scale": (c, c, c)}},
							arms(-50 * f + reel, -40 * f - reel, 40 * f, 0))

	clip_scaled(arm, "idle", 3.0, idle, False)
	clip_scaled(arm, "walk", 1.5, walk, False)
	clip_scaled(arm, "run", 1.0, run, False)
	clip_scaled(arm, "attack", 1.1, attack, False)
	clip_scaled(arm, "hit", 0.45, hit, False)
	clip_scaled(arm, "death", 1.8, death, False)
	return arm


# Silted Reach / Tidemouth: registered here, beside their builders
BODIES.update({"whiskerfolk_body": (KAYKIT + "Barbarian.glb", "whiskerfolk_texture", WHISKERFOLK_CELLS, None),
			   "river_king_body": (KAYKIT + "Barbarian.glb", "river_king_texture", RIVER_KING_CELLS, None),
			   "mudfolk_body": (KAYKIT + "Barbarian.glb", "mudfolk_texture", MUDFOLK_CELLS, None),
			   "mud_shaman_body": (KAYKIT + "Barbarian.glb", "mud_shaman_texture", MUD_SHAMAN_CELLS, None),
			   "drowned_smuggler_body": (KAYKIT + "Rogue.glb", "drowned_smuggler_texture", SMUGGLER_CELLS, None),
			   "smuggler_captain_body": (KAYKIT + "Rogue.glb", "smuggler_captain_texture", SMUGGLER_CAPTAIN_CELLS, None),
			   "saltreaver_body": (KAYKIT + "Barbarian.glb", "saltreaver_texture", SALTREAVER_CELLS, None),
			   "saltreaver_king_body": (KAYKIT + "Barbarian.glb", "saltreaver_king_texture", SALTREAVER_KING_CELLS, None),
			   "clawfolk_body": (KAYKIT + "Barbarian.glb", "clawfolk_texture", CLAWFOLK_CELLS, None)})
for _pre, _king in (("whiskerfolk", False), ("river_king", True)):
	for _part, _fn in (("head", _whisker_head), ("chest", _whisker_chest), ("hips", _whisker_hips)):
		ATTACHMENTS[f"{_pre}_{_part}"] = (lambda n, f, k: lambda: _whisker_part(n, f, k))(f"{_pre}_{_part}", _fn, _king)
for _pre, _sh in (("mudfolk", False), ("mud_shaman", True)):
	for _part, _fn in (("head", _mud_head), ("chest", _mud_chest), ("hips", _mud_hips)):
		ATTACHMENTS[f"{_pre}_{_part}"] = (lambda n, f, k: lambda: _mud_part(n, f, k))(f"{_pre}_{_part}", _fn, _sh)
for _pre, _king in (("saltreaver", False), ("saltreaver_king", True)):
	for _part, _fn in (("chest", _reaver_chest), ("kilt", _reaver_kilt)):
		ATTACHMENTS[f"{_pre}_{_part}"] = (lambda n, f, k: lambda: _reaver_part(n, f, k))(f"{_pre}_{_part}", _fn, _king)
for _s, _side in ((1, "l"), (-1, "r")):
	ATTACHMENTS[f"saltreaver_arm_{_side}"] = (lambda n, s: lambda: _reaver_arm(n, s))(f"saltreaver_arm_{_side}", _s)
	ATTACHMENTS[f"saltreaver_bracer_{_side}"] = (lambda n, s: lambda: _reaver_bracer(n, s))(f"saltreaver_bracer_{_side}", _s)
	ATTACHMENTS[f"clawfolk_arm_{_side}"] = (lambda n, s: lambda: _clawfolk_arm(n, s))(f"clawfolk_arm_{_side}", _s)
ATTACHMENTS.update({"river_trident": build_river_trident, "driftwood_staff": build_driftwood_staff,
					"smuggler_bandana": build_smuggler_bandana, "smuggler_rags": build_smuggler_rags, "smuggler_sash": build_smuggler_sash,
					"smuggler_captain_hat": build_smuggler_captain_hat, "smuggler_captain_coat": build_smuggler_captain_coat,
					"smuggler_captain_tails": build_smuggler_captain_tails, "smuggler_cutlass": build_smuggler_cutlass,
					"saltreaver_helm": build_saltreaver_helm, "saltreaver_king_crown": build_saltreaver_king_crown,
					"whalebone_axe": build_whalebone_axe, "clawfolk_head": build_clawfolk_head, "clawfolk_shell": build_clawfolk_shell,
					"clawfolk_claw_l": lambda: _clawfolk_claw("clawfolk_claw_l", 1, False),
					"clawfolk_claw_r": lambda: _clawfolk_claw("clawfolk_claw_r", -1, True)})
CREATURES.update({"river_hippo": build_river_hippo, "biting_swarm": build_biting_swarm, "deep_horror": build_deep_horror,
				  "giant_gull": build_giant_gull, "sea_lion": build_sea_lion, "tempest_lord": build_tempest_lord})
for _name in SERPENTS:
	CREATURES[_name] = (lambda n: lambda: build_serpent(n))(_name)
# ================================================================ end of Silted Reach / Tidemouth


# ================================================================ Windbreak (the Standing Sky, 32-36)
# A high plateau broken into red-ochre mesas by the winds of Vayuketh, He Who Breathes the Plains.
# Own rigs: the gale spirit (a hovering figure of wind streams and ribbons, legs trailing, not the air
# elemental's tornado or the tempest's thundercloud), the dust devil (an ochre funnel of dust and
# pebbles) and the named storm-eye (a towering cyclone with a glaring eye in a wheel of cloud at its
# middle); one soaring-bird frame (`build_sky_bird`: three-jointed wings with fingered primaries) for
# the giant eagle, the thunderbird and Skarrow the named thunderbird (built 1.45x); the cliff drake is
# the ash drake recolored rust-red and frilled. The Kitewing bandits are repainted KayKit Rogues with a
# folded kite rig on the back (their chief a spread, painted sail, a feathered hat and a long coat); the
# stone giants are repainted Barbarians, head hidden, with bolt-ons in their mesh space like the ember
# giants', and slabs of standing stone for weapons (models.json "weapons").

def _wb_ribbon(b, pts, width, mat, bone, up=(0, 0, 1), thick=0.016, taper=0.35):
	"""A flat ribbon of slabs through `pts`, its face toward `up`, narrowing to `taper` of its width."""
	pts = [Vector(p) for p in pts]
	n = len(pts) - 1
	start = len(b.parts)
	for k in range(n):
		p, q = pts[k], pts[k + 1]
		side = (q - p).cross(Vector(up))
		if side.length < 1e-5:
			side = Vector((1, 0, 0))
		side.normalize()
		w0 = width * (1 - (1 - taper) * k / n) / 2
		w1 = width * (1 - (1 - taper) * (k + 1) / n) / 2
		_slab(b, [tuple(p - side * w0), tuple(p + side * w0), tuple(q + side * w1), tuple(q - side * w1)], thick, mat)
	_on_bone(b, start, bone)


def _wb_coil(b, a, c, r0, r1, turns, phase, width, mat, bone, n=16):
	"""A thin strand wound `turns` times round the axis a -> c, its radius going r0 -> r1."""
	a, c = Vector(a), Vector(c)
	ax = (c - a).normalized()
	u = ax.orthogonal().normalized()
	v = ax.cross(u).normalized()
	pts = []
	for k in range(n + 1):
		f = k / n
		ang = 2 * math.pi * (phase + turns * f)
		r = r0 + (r1 - r0) * f
		pts.append(a + (c - a) * f + (u * math.cos(ang) + v * math.sin(ang)) * r)
	for p, q in zip(pts, pts[1:]):
		b.seg(tuple(p), tuple(q), width, width, mat, bone, sides=4)


def _wb_bolt(b, a, c, rng, r, mat, bone, steps=4, jag=0.08):
	"""A jagged bolt of lightning from a to c."""
	a, c = Vector(a), Vector(c)
	pts = [a]
	for k in range(1, steps):
		p = a + (c - a) * (k / steps)
		pts.append(p + Vector((rng.uniform(-jag, jag), rng.uniform(-jag, jag), rng.uniform(-jag, jag))))
	pts.append(c)
	_zigzag(b, [tuple(p) for p in pts], r, mat, bone)
	return pts


# ---------------------------------------------------------------- gale spirit

def build_gale_spirit():
	"""A spirit of the wind: a slender figure of pale glassy air hovering with its legs trailing behind
	it, strands of white and sky-blue wind winding round its limbs and body, a smooth white mask of a
	face with slit eyes, wind streaming back off its crown, and long ribbons blown out behind it from its
	wrists, its crown and a pale gold sash. A loop of wind orbits it."""
	import random
	rng = random.Random(3201)
	m = _rmats("gale_spirit", {"white": ("f4f9ff", 0.6, 0.35), "pale": ("cfe6f8", 0.6, 0.2), "sky": ("8cc6f0", 0.55, 0.2),
							   "deep": ("5a9ad0", 0.6, 0.15), "gold": ("f2dc9a", 0.5, 0.35), "eye": ("e8fbff", 0.1, 6.0),
							   "mask": ("eef4fa", 0.35, 0.3), "slit": ("30507a", 0.4)})
	core = glass_material("gale_spirit_core", "bfe2fa", 0.55, 0.2, emit=0.5)
	core_b = glass_material("gale_spirit_core_b", "e6f4ff", 0.45, 0.2, emit=0.6)
	b = Builder("gale_spirit")
	b.bone("root", (0, 0, 0))
	b.bone("hips", (0, 0, 0.98), "root")
	b.bone("swirl", (0, 0, 1.0), "hips")
	b.bone("orbit", (0, 0, 1.2), "hips")
	b.bone("chest", (0, 0, 1.36), "hips")
	b.bone("head", (0, -0.02, 1.8), "chest")
	b.bone("hair1", (0, 0.14, 2.0), "head")
	b.bone("hair2", (0, 0.62, 1.84), "hair1")
	b.bone("sash1", (0, 0.2, 0.98), "hips")
	b.bone("sash2", (0, 0.66, 0.84), "sash1")

	# the body: glassy air, narrow at the waist, strands of wind winding up round it
	b.blob((0.34, 0.26, 0.3), (0, 0.0, 1.0), core, "hips", segs=(10, 7))
	b.seg((0, 0, 0.98), (0, 0, 1.36), 0.12, 0.17, core, "hips", sides=10)
	b.blob((0.52, 0.32, 0.36), (0, 0.0, 1.5), core, "chest", segs=(12, 8))
	for s in (1, -1):
		b.blob((0.18, 0.18, 0.16), (0.23 * s, 0.0, 1.6), core_b, "chest", segs=(8, 6))
	b.seg((0, 0, 1.6), (0, -0.02, 1.78), 0.06, 0.05, core, "chest", sides=8)
	for h, mat in enumerate((m["white"], m["pale"], m["sky"], m["white"])):
		pts = []
		for k in range(25):
			f = k / 24
			z = 0.86 + 0.86 * f
			r = 0.16 + 0.1 * math.sin(math.pi * min(1.0, f * 1.15)) + 0.03
			a = 2 * math.pi * (h / 4 + 1.6 * f)
			pts.append(Vector((r * math.cos(a) * 1.25, r * math.sin(a) * 0.9, z)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			w = 0.014 + 0.014 * math.sin(math.pi * k / 24)
			b.seg(tuple(p), tuple(q), w, w, mat, "swirl", sides=4)
	_wrap(b, (0, 0, 1.0), (0.2, 0.15), 0.07, 0.02, m["gold"], rot=(-6, 0, 0), sides=16)   # a pale gold girdle
	_on_bone(b, len(b.parts) - 1, "hips")
	b.blob((0.1, 0.06, 0.1), (0, 0.16, 0.99), m["gold"], "hips", segs=(6, 4))            # its knot, behind
	# the sash: two ribbons streaming back from the knot
	for s, mat in ((1, m["gold"]), (-1, m["white"])):
		pts = [Vector((0.03 * s, 0.18, 0.98)), Vector((0.08 * s, 0.4, 0.9)), Vector((0.06 * s, 0.66, 0.84))]
		_wb_ribbon(b, pts, 0.08, mat, "sash1", taper=0.9)
		pts = [pts[-1], Vector((0.1 * s, 0.9, 0.82)), Vector((0.05 * s, 1.14, 0.72)), Vector((0.1 * s, 1.36, 0.7))]
		_wb_ribbon(b, pts, 0.072, mat, "sash2", taper=0.2)
	# the loop of wind orbiting it, tipped, open in two places, wisps flying off
	for rad, z, tilt, mat, gap in ((0.62, 1.12, (16, -10, 0), m["white"], (60, 130)), (0.56, 1.3, (-12, 14, 0), m["sky"], (220, 300))):
		start = len(b.parts)
		_wrap(b, (0, 0, z), (rad, rad * 0.9), 0.05, 0.016, mat, rot=tilt, gap=gap, sides=20)
		_on_bone(b, start, "orbit")
		for k in range(2):
			a = math.radians(gap[0] - 6 - 150 * k)
			p = Vector((rad * math.cos(a), rad * 0.9 * math.sin(a), z))
			tang = Vector((math.sin(a), -math.cos(a), 0))
			_flame(b, tuple(p), tuple(tang + Vector((0, 0, 0.1))), 0.3, 0.035, mat, "orbit", bend=(0, 0, 0.1), sides=4)

	# the head: a smooth white mask, slit eyes, wind streaming back off the crown
	b.blob((0.3, 0.32, 0.4), (0, -0.02, 1.92), m["mask"], "head", segs=(12, 10))
	b.blob((0.24, 0.1, 0.26), (0, -0.14, 1.9), m["mask"], "head", segs=(10, 6))       # the face's plane
	b.blob((0.03, 0.03, 0.12), (0, -0.19, 1.9), m["pale"], "head", segs=(5, 4))       # the ridge of a nose
	for s in (1, -1):
		b.blob((0.12, 0.04, 0.045), (0.07 * s, -0.175, 1.95), m["slit"], "head", rot=(0, 10 * s, -14 * s), segs=(8, 4))
		b.blob((0.1, 0.03, 0.022), (0.07 * s, -0.19, 1.95), m["eye"], "head", rot=(0, 10 * s, -14 * s), segs=(8, 4))
	for k in range(7):
		x = (k - 3) * 0.045
		ln = 0.46 + 0.14 * (1 - abs(k - 3) / 3)
		_flame(b, (x, 0.0, 2.08 - 0.02 * abs(k - 3)), (x * 1.6, 1.0, 0.45), ln, 0.05, [m["white"], m["pale"], m["sky"]][k % 3],
			   "head", bend=(0, 0.1, -0.22), sides=5, parts=4)
	pts = [Vector((0, 0.14, 2.0)), Vector((0.02, 0.36, 1.98)), Vector((-0.02, 0.62, 1.84))]   # the crown's ribbon
	_wb_ribbon(b, pts, 0.1, m["sky"], "hair1", up=(1, 0, 0.2), taper=0.9)
	pts = [pts[-1], Vector((0.04, 0.86, 1.76)), Vector((-0.02, 1.12, 1.74)), Vector((0.02, 1.4, 1.62))]
	_wb_ribbon(b, pts, 0.09, m["sky"], "hair2", up=(1, 0, 0.2), taper=0.2)

	# arms: slender streams of air wound with wind, wispy hands, ribbons trailing from the wrists
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, fore, hand, rib1, rib2 = f"arm_{side}", f"fore_{side}", f"hand_{side}", f"rib1_{side}", f"rib2_{side}"
		sh, el, wr = Vector((0.25 * s, 0, 1.62)), Vector((0.34 * s, -0.04, 1.28)), Vector((0.4 * s, -0.08, 0.98))
		b.bone(arm, tuple(sh), "chest")
		b.bone(fore, tuple(el), arm)
		b.bone(hand, tuple(wr), fore)
		b.bone(rib1, tuple(wr + Vector((0.02 * s, 0.04, 0))), fore)
		b.bone(rib2, (0.5 * s, 0.5, 0.92), rib1)
		b.seg(tuple(sh), tuple(el), 0.07, 0.055, core, arm, sides=8)
		b.seg(tuple(el), tuple(wr), 0.055, 0.045, core, fore, sides=8)
		_wb_coil(b, sh, el, 0.08, 0.07, 1.5, 0.1, 0.012, m["white"], arm)
		_wb_coil(b, el, wr, 0.07, 0.06, 1.5, 0.6, 0.012, m["pale"], fore)
		b.blob((0.1, 0.08, 0.12), tuple(wr + Vector((0, 0, -0.06))), core_b, hand, segs=(8, 6))
		for k in range(3):   # fingers of wind
			d = Vector(((k - 1) * 0.3 * s + 0.2 * s, -0.3, -1))
			_flame(b, tuple(wr + Vector(((k - 1) * 0.03 * s, -0.02, -0.1))), tuple(d), 0.2, 0.03, [m["white"], m["pale"]][k % 2], hand,
				   bend=(0.05 * s, 0.1, 0), sides=4)
		_wrap(b, tuple(wr + Vector((0, 0, 0.04))), (0.07, 0.07), 0.05, 0.015, m["gold"], sides=10)   # a band at the wrist
		_on_bone(b, len(b.parts) - 1, fore)
		pts = [wr + Vector((0.02 * s, 0.04, 0.04)), Vector((0.46 * s, 0.26, 0.98)), Vector((0.5 * s, 0.5, 0.92))]
		_wb_ribbon(b, pts, 0.07, m["white"], rib1, up=(0.3 * s, 0, 1), taper=0.9)
		pts = [pts[-1], Vector((0.58 * s, 0.76, 0.94)), Vector((0.54 * s, 1.0, 0.84)), Vector((0.62 * s, 1.24, 0.82))]
		_wb_ribbon(b, pts, 0.063, m["white"], rib2, up=(0.3 * s, 0, 1), taper=0.2)

	# legs: streams trailing back and down, wound with wind, thinning to ribbons of air
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		leg, shin = f"leg_{side}", f"shin_{side}"
		hip, knee, end = Vector((0.1 * s, 0.0, 0.92)), Vector((0.13 * s, 0.1, 0.56)), Vector((0.1 * s, 0.42, 0.24))
		b.bone(leg, tuple(hip), "hips")
		b.bone(shin, tuple(knee), leg)
		b.seg(tuple(hip), tuple(knee), 0.085, 0.06, core, leg, sides=8)
		b.seg(tuple(knee), tuple(end), 0.06, 0.012, core, shin, sides=8)
		_wb_coil(b, hip, knee, 0.095, 0.075, 1.25, 0.3 if s > 0 else 0.8, 0.013, m["white"], leg)
		_wb_coil(b, knee, end, 0.075, 0.02, 1.5, 0.1, 0.012, m["sky"], shin)
		for k in range(3):
			_flame(b, tuple(end + Vector(((k - 1) * 0.04, -0.06, 0.02))), ((k - 1) * 0.3, 1, -0.2), 0.34, 0.035,
				   [m["white"], m["pale"], m["sky"]][k], shin, bend=(0, 0.05, 0.12), sides=4)
	arm = b.build()

	def ribbons(t, cycles, amp, lift=0.0):
		out = {}
		for k, (a, c) in enumerate((("rib1_l", "rib2_l"), ("rib1_r", "rib2_r"), ("hair1", "hair2"), ("sash1", "sash2"))):
			ph = 0.17 * k
			out[a] = {"rot": (lift + amp * wave(t, cycles, ph), 0, amp * 0.7 * wave(t, cycles, ph + 0.25))}
			out[c] = {"rot": (amp * 1.4 * wave(t, cycles, ph - 0.15), 0, amp * wave(t, cycles, ph + 0.1))}
		return out

	def wind(t, turns):
		return {"swirl": {"rot": (0, 0, 360 * turns * t)}, "orbit": {"rot": (0, 0, -360 * max(1, turns // 2) * t)}}

	def limbs(t, arm_p, spread, fore, leg_p, cycles=1):
		return {"arm_l": {"rot": (arm_p + 5 * wave(t, cycles, 0.1), spread + 4 * wave(t, cycles), 0)},
				"arm_r": {"rot": (arm_p + 5 * wave(t, cycles, 0.6), -spread - 4 * wave(t, cycles, 0.5), 0)},
				"fore_l": {"rot": (fore, 0, 0)}, "fore_r": {"rot": (fore, 0, 0)},
				"leg_l": {"rot": (leg_p + 6 * wave(t, cycles, 0.2), 3, 0)}, "leg_r": {"rot": (leg_p + 6 * wave(t, cycles, 0.7), -3, 0)},
				"shin_l": {"rot": (-10 + 8 * wave(t, cycles, 0.35), 0, 0)}, "shin_r": {"rot": (-10 + 8 * wave(t, cycles, 0.85), 0, 0)}}

	def body(t, lean, bob, cycles=1):
		return {"root": {"loc": (0, 0, 0.3 + bob * wave(t, cycles * 2))},
				"hips": {"rot": (lean + 3 * wave(t, cycles, 0.2), 3 * wave(t, cycles), 4 * wave(t, cycles, 0.4))},
				"chest": {"rot": (lean * 0.3 + 2 * wave(t, cycles, 0.4), 0, -4 * wave(t, cycles, 0.5))},
				"head": {"rot": (-lean * 0.5 + 3 * wave(t, cycles, 0.6), 0, 6 * wave(t, cycles, 0.1))}}

	def idle(t):
		return merge_scaled(body(t, 0, 0.06, 1), wind(t, 2), limbs(t, 8, 14, 16, -12), ribbons(t, 2, 12))

	def walk(t):   # glides forward, leaning in, legs streaming out behind
		return merge_scaled(body(t, -18, 0.04, 1), wind(t, 2), limbs(t, -18, 10, 12, -34), ribbons(t, 2, 16, -6))

	def run(t):
		return merge_scaled(body(t, -30, 0.05, 1), wind(t, 2), limbs(t, -46, 14, 10, -50), ribbons(t, 3, 18, -10))

	def attack(t):   # draws its right arm up and back, then slashes a gust across, the left pushing out
		up = seq(t, [(0, 0), (0.3, 150), (0.42, 156), (0.55, 40), (0.75, 30), (1, 0)])
		cross = seq(t, [(0, 0), (0.3, -40), (0.42, -44), (0.55, 30), (0.75, 24), (1, 0)])
		push = seq(t, [(0, 0), (0.35, 20), (0.5, 90), (0.75, 80), (1, 0)])
		twist = seq(t, [(0, 0), (0.3, 24), (0.5, -26), (0.75, -20), (1, 0)])
		surge = seq(t, [(0, 0), (0.35, -0.06), (0.52, 0.3), (0.75, 0.24), (1, 0)])
		gust = seq(t, [(0.4, 1.0), (0.55, 1.5), (0.9, 1.0)])
		return merge_scaled({"root": {"loc": (0, surge, 0.3)}, "hips": {"rot": (-10, 0, twist * 0.5)}, "chest": {"rot": (-4, 0, twist)},
							 "arm_r": {"rot": (up, -12 + cross, 0)}, "fore_r": {"rot": (seq(t, [(0, 16), (0.3, 30), (0.55, 4), (1, 16)]), 0, 0)},
							 "arm_l": {"rot": (push, 14, 0)}, "fore_l": {"rot": (8, 0, 0)},
							 "orbit": {"scale": (gust, gust, 1)}, "leg_l": {"rot": (-24, 3, 0)}, "leg_r": {"rot": (-30, -3, 0)}},
							wind(t, 2), ribbons(t, 2, 20, -8))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"root": {"loc": (0, -0.14 * k, 0.3 + 0.04 * k)}, "hips": {"rot": (16 * k, 6 * k, 0)},
							 "chest": {"rot": (8 * k, 0, 10 * k)}, "head": {"rot": (14 * k, 0, -14 * k)},
							 "orbit": {"scale": (1 + 0.3 * k, 1 + 0.3 * k, 1)}},
							wind(t, 1), limbs(t, -20 * k, 20 + 20 * k, 20, -12 + 20 * k), ribbons(t, 2, 18))

	def death(t):   # comes apart: the wind unwinds and blows away, the body thins to a last knot of air
		d = seq(t, [(0.15, 0), (0.95, 1)])
		reel = seq(t, [(0, 0), (0.18, 16), (0.35, -6), (0.5, 0)])
		thin = max(0.18, 1 - 0.82 * d)
		wide = 1 + 1.8 * d
		return merge_scaled({"root": {"loc": (0, 0, 0.3 - 0.62 * d)},
							 "hips": {"rot": (reel, 0, 200 * d), "scale": (thin, thin, thin)},
							 "swirl": {"rot": (0, 0, 540 * d), "scale": (wide, wide, 1)},
							 "orbit": {"rot": (20 * d, 0, -400 * d), "scale": (wide * 1.3, wide * 1.3, max(0.1, 1 - d)), "loc": (0, 0, 0.5 * d)},
							 "head": {"rot": (-20 * d, 0, 0)}},
							limbs(t, 30 * d, 14 + 40 * d, 16, -12 - 30 * d), ribbons(t, 2, 20 + 20 * d, 20 * d))

	clip_scaled(arm, "idle", 2.4, idle, True)
	clip_scaled(arm, "walk", 1.0, walk, True)
	clip_scaled(arm, "run", 0.6, run, True)
	clip_scaled(arm, "attack", 0.8, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.6, death, False)
	return arm


# ---------------------------------------------------------------- dust devil

def build_dust_devil():
	"""A spinning funnel of red-ochre dust, narrow at the ground and flaring at the top: bands of dust at
	their own speeds, dark streaks spiraling up it, pebbles and twigs whirling round it, a skirt of dust
	at its foot and two dim amber slits for eyes in the murk."""
	import random
	rng = random.Random(3211)
	m = _rmats("dust_devil", {"ochre": ("c8843e", 0.95), "ochre_l": ("e2b070", 0.95), "sand": ("d8bc88", 0.95),
							  "rust": ("a4582a", 0.95), "brown": ("6e4424", 0.95), "stone": ("8a7a68", 0.9),
							  "stone_d": ("5a4a3c", 0.9), "stone_r": ("a8603a", 0.9), "twig": ("4a3424", 0.9),
							  "eye": ("ffb448", 0.2, 3.0), "socket": ("4a2a14", 0.95)})
	haze = glass_material("dust_devil_haze", "c89456", 0.55, 0.9, emit=0.05)
	b = Builder("dust_devil")
	b.bone("root", (0, 0, 0))
	b.bone("skirt", (0, 0, 0.02), "root")
	b.bone("low", (0, 0, 0.05), "root")
	b.bone("mid", (0, 0, 1.0), "low")
	b.bone("top", (0, 0, 1.8), "mid")
	b.bone("ring_a", (0, 0, 0.05), "low")
	b.bone("ring_b", (0, 0, 1.0), "mid")
	b.bone("ring_c", (0, 0, 1.8), "top")
	b.bone("debris_a", (0, 0, 0.05), "low")
	b.bone("debris_b", (0, 0, 1.0), "mid")
	b.bone("face", (0, 0, 1.5), "mid")

	def rad(z):
		return 0.07 + 0.62 * (max(0.0, z) / 2.5) ** 1.5

	def part(z, names):
		return names[0] if z < 1.0 else names[1] if z < 1.8 else names[2]

	# the murk inside: a cone of dusty haze
	for z0, z1, bone in ((0.02, 1.0, "low"), (1.0, 1.8, "mid"), (1.8, 2.5, "top")):
		b.seg((0, 0, z0), (0, 0, z1), rad(z0) * 0.85, rad(z1) * 0.85, haze, bone, sides=14)
	mats = (m["ochre"], m["sand"], m["rust"], m["ochre_l"])
	for k in range(15):   # bands of whirling dust, each open somewhere
		z = 0.08 + k * 0.166
		r = rad(z)
		start = len(b.parts)
		g0 = rng.uniform(0, 300)
		_wrap(b, (0.02 * math.sin(k * 1.9), 0.02 * math.cos(k * 1.9), z), (r, r * 0.95), 0.1 + 0.04 * (z / 2.5), 0.045, mats[k % 4],
			  rot=(rng.uniform(-6, 6), rng.uniform(-6, 6), 0), gap=(g0, g0 + rng.uniform(40, 90)), sides=16)
		_on_bone(b, start, part(z, ("ring_a", "ring_b", "ring_c")))
	for h in range(5):   # dark streaks spiraling up the funnel
		pts = []
		for k in range(31):
			f = k / 30
			z = 0.04 + 2.44 * f
			a = 2 * math.pi * (h / 5 + 1.4 * f)
			r = rad(z) + 0.035
			pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			w = 0.018 + 0.03 * k / 30
			b.seg(tuple(p), tuple(q), w, w, m["brown"] if h % 2 else m["rust"], part((p.z + q.z) / 2, ("ring_a", "ring_b", "ring_c")), sides=4)
	for k in range(12):   # the lip: dust spilling over the top
		a = 2 * math.pi * k / 12
		r = rad(2.5)
		b.blob((0.3, 0.3, 0.2), (r * math.cos(a), r * math.sin(a), 2.5 + 0.04 * math.sin(3 * a)), mats[k % 4], "ring_c", segs=(8, 5))
	for k in range(10):   # the skirt of dust at its foot
		a = 2 * math.pi * k / 10 + rng.uniform(-0.2, 0.2)
		r = rng.uniform(0.26, 0.42)
		b.blob((0.34, 0.3, 0.14), (r * math.cos(a), r * math.sin(a), 0.07), mats[k % 4], "skirt", rot=(0, 0, math.degrees(a)), segs=(8, 5))
	# pebbles, stones and twigs whirling round it
	for k in range(28):
		z = rng.uniform(0.15, 2.35)
		a = rng.uniform(0, 2 * math.pi)
		r = rad(z) + rng.uniform(0.08, 0.22)
		sz = rng.uniform(0.05, 0.12) * (0.7 + 0.5 * z / 2.4)
		_rock(b, (sz, sz * rng.uniform(0.7, 1.1), sz * 0.8), (r * math.cos(a), r * math.sin(a), z),
			  [m["stone"], m["stone_d"], m["stone_r"]][k % 3], "debris_a" if z < 1.2 else "debris_b", rng)
	for k in range(5):
		z = rng.uniform(0.5, 2.1)
		a = rng.uniform(0, 2 * math.pi)
		r = rad(z) + 0.14
		p = Vector((r * math.cos(a), r * math.sin(a), z))
		tang = Vector((-math.sin(a), math.cos(a), rng.uniform(-0.3, 0.3)))
		b.seg(tuple(p - tang * 0.14), tuple(p + tang * 0.14), 0.014, 0.008, m["twig"], "debris_a" if z < 1.2 else "debris_b", sides=4)
		b.seg(tuple(p), tuple(p + tang * 0.05 + Vector((0, 0, 0.08))), 0.009, 0.004, m["twig"], "debris_a" if z < 1.2 else "debris_b", sides=3)
	# two dim amber slits in the murk
	for s in (1, -1):
		z = 1.62
		y = -(rad(z) + 0.02)
		b.blob((0.2, 0.06, 0.1), (0.13 * s, y + 0.03, z), m["socket"], "face", rot=(0, 0, 14 * s), segs=(8, 5))
		b.blob((0.14, 0.05, 0.045), (0.13 * s, y, z), m["eye"], "face", rot=(0, 14 * s, 14 * s), segs=(8, 4))
	arm = b.build()

	def spin(t, turns):
		return {"ring_a": {"rot": (0, 0, 360 * turns * 2 * t)}, "ring_b": {"rot": (0, 0, 360 * turns * t)},
				"ring_c": {"rot": (0, 0, 360 * turns * t)}, "skirt": {"rot": (0, 0, 360 * turns * 2 * t)},
				"debris_a": {"rot": (0, 0, 360 * turns * t)}, "debris_b": {"rot": (0, 0, 360 * max(1, turns // 2) * t)}}

	def sway(t, amp, lean, cycles=1):
		return {"low": {"rot": (lean * 0.3 + amp * wave(t, cycles), amp * wave(t, cycles, 0.25), 0)},
				"mid": {"rot": (lean * 0.4 + amp * wave(t, cycles, 0.15), amp * wave(t, cycles, 0.4), 0)},
				"top": {"rot": (lean * 0.3 + amp * 1.2 * wave(t, cycles, 0.3), amp * 1.2 * wave(t, cycles, 0.55), 0)},
				"face": {"rot": (0, 0, 6 * wave(t, cycles, 0.5))}}

	def idle(t):
		return merge_scaled(sway(t, 3, 0, 1), spin(t, 3), {"root": {"loc": (0.03 * wave(t, 1), 0.03 * wave(t, 1, 0.25), 0)}})

	def walk(t):
		return merge_scaled(sway(t, 3, -10, 1), spin(t, 2))

	def run(t):
		return merge_scaled(sway(t, 4, -20, 1), spin(t, 2))

	def attack(t):   # the funnel whips over and lashes down at its foe, its bands flaring
		bend = seq(t, [(0, 0), (0.3, 8), (0.48, -26), (0.7, -22), (1, 0)])
		lunge = seq(t, [(0, 0), (0.3, -0.08), (0.48, 0.32), (0.7, 0.26), (1, 0)])
		flare = seq(t, [(0.3, 1.0), (0.48, 1.35), (0.8, 1.0)])
		return merge_scaled({"root": {"loc": (0, lunge, 0)}, "low": {"rot": (bend * 0.2, 0, 0)}, "mid": {"rot": (bend * 0.7, 0, 0)},
							 "top": {"rot": (bend, 0, 0)}, "ring_b": {"scale": (flare, flare, 1)}, "ring_c": {"scale": (flare, flare, 1)}},
							spin(t, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"low": {"rot": (8 * k, 6 * k, 0)}, "mid": {"rot": (10 * k, -6 * k, 0)}, "top": {"rot": (12 * k, 8 * k, 0)},
							 "ring_c": {"scale": (1 + 0.2 * k, 1 + 0.2 * k, 1)}}, spin(t, 1))

	def death(t):   # it winds down and slumps into a ring of dust and stones on the ground
		d = seq(t, [(0.15, 0), (0.9, 1)])
		reel = seq(t, [(0, 0), (0.2, 12), (0.4, -8), (0.6, 0)])
		spin_ = 900 * (1 - (1 - t) ** 2)
		return merge_scaled({"low": {"rot": (reel * 0.3, 0, 0), "scale": (1 + 0.9 * d, 1 + 0.9 * d, max(0.05, 1 - 0.95 * d))},
							 "mid": {"rot": (reel, 0, 0)}, "top": {"rot": (-reel, 0, 0)},
							 "ring_a": {"rot": (0, 0, spin_)}, "ring_b": {"rot": (0, 0, spin_ * 0.7)}, "ring_c": {"rot": (0, 0, spin_ * 0.5)},
							 "skirt": {"rot": (0, 0, spin_), "scale": (1 + 0.6 * d, 1 + 0.6 * d, 1)},
							 "debris_a": {"rot": (0, 0, spin_)}, "debris_b": {"rot": (0, 0, spin_ * 0.6)}})

	clip_scaled(arm, "idle", 2.0, idle, True)
	clip_scaled(arm, "walk", 1.0, walk, True)
	clip_scaled(arm, "run", 0.6, run, True)
	clip_scaled(arm, "attack", 0.8, attack, False)
	clip_scaled(arm, "hit", 0.4, hit, False)
	clip_scaled(arm, "death", 1.6, death, False)
	return arm


# ---------------------------------------------------------------- the storm-eye

def build_storm_eye():
	"""The storm-eye: a towering cyclone of slate-dark cloud with an anvil head, broken at its middle by a
	wheel of cloud turning round one great glaring eye; lightning crawling down its walls and crackling
	from the wheel, two lashing arms of cloud that fork into lightning, stones whirling at its foot."""
	import random
	rng = random.Random(3221)
	m = _rmats("storm_eye", {"dark": ("2c3240", 0.95), "cloud": ("465064", 0.95), "light": ("6c7890", 0.9, 0.05),
							 "pale": ("98a4b8", 0.9, 0.08), "bolt": ("eef8ff", 0.2, 6.5), "bolt_b": ("98d8ff", 0.2, 4.5),
							 "eye": ("fff4c4", 0.15, 3.5), "iris": ("ffc830", 0.2, 5.0), "pupil": ("140c04", 0.4),
							 "stone": ("7a6a5a", 0.9), "stone_r": ("9a5634", 0.9), "dust": ("a88058", 0.95)})
	haze = glass_material("storm_eye_haze", "3a4254", 0.6, 0.9, emit=0.05)
	b = Builder("storm_eye")
	b.bone("root", (0, 0, 0))
	b.bone("low", (0, 0, 0.05), "root")
	b.bone("mid", (0, 0, 1.7), "low")
	b.bone("top", (0, 0, 2.9), "mid")
	b.bone("wall_a", (0, 0, 0.05), "low")
	b.bone("wall_b", (0, 0, 1.7), "mid")
	b.bone("wall_c", (0, 0, 2.9), "top")
	b.bone("anvil", (0, 0, 3.9), "top")
	b.bone("wheel", (0, -0.2, 2.3), "mid")
	b.bone("eye", (0, -0.3, 2.3), "mid")
	b.bone("debris", (0, 0, 0.05), "low")
	b.bone("skirt", (0, 0, 0.02), "root")

	def rad(z):
		return 0.18 + 1.35 * (max(0.0, z) / 3.8) ** 1.4

	mats = (m["dark"], m["cloud"], m["light"], m["cloud"])
	# the column: a core of dark haze all the way up, so the walls read as one storm
	for z0, z1, bone in ((0.02, 1.7, "low"), (1.7, 2.9, "mid"), (2.9, 3.9, "top")):
		b.seg((0, 0.1, z0), (0, 0.1, z1), rad(z0) * (0.8 if z0 < 1.6 else 0.45), rad(z1) * (0.45 if z1 < 3.0 and z1 > 1.8 else 0.8),
			  haze, bone, sides=16)
	# the walls: bands of cloud below the wheel and above it, spiral streaks through the wheel's gap
	zs = [0.1 + 0.2 * k for k in range(9)] + [2.95 + 0.19 * k for k in range(5)]
	for k, z in enumerate(zs):
		r = rad(z)
		start = len(b.parts)
		g0 = rng.uniform(0, 300)
		_wrap(b, (0.03 * math.sin(k * 1.7), 0.03 * math.cos(k * 1.7), z), (r, r * 0.95), 0.16 + 0.06 * z / 3.8, 0.07, mats[k % 4],
			  rot=(rng.uniform(-5, 5), rng.uniform(-5, 5), 0), gap=(g0, g0 + rng.uniform(30, 70)), sides=20)
		_on_bone(b, start, "wall_a" if z < 1.7 else "wall_c")
		for j in range(3):   # puffs riding each band
			a = rng.uniform(0, 2 * math.pi)
			rr = rng.uniform(0.2, 0.34) * (0.7 + z / 3.8)
			b.blob((rr, rr, rr * 0.7), (r * math.cos(a), r * math.sin(a), z), mats[(k + j) % 4], "wall_a" if z < 1.7 else "wall_c", segs=(8, 5))
	for h in range(4):
		pts = []
		for k in range(41):
			f = k / 40
			z = 0.06 + 3.8 * f
			a = 2 * math.pi * (h / 4 + 1.8 * f)
			r = rad(z) + 0.06
			pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			z = (p.z + q.z) / 2
			bone = "wall_a" if z < 1.7 else "wall_b" if z < 2.9 else "wall_c"
			w = 0.03 + 0.03 * k / 40
			b.seg(tuple(p), tuple(q), w, w, m["pale"] if h % 2 else m["light"], bone, sides=4)
	# the anvil: a wide cap of storm cloud spreading over the top, lightning dropping out of it
	for k in range(16):
		a = 2 * math.pi * k / 16 + rng.uniform(-0.1, 0.1)
		r = rng.uniform(1.2, 1.9)
		sz = rng.uniform(0.6, 0.9)
		b.blob((sz, sz, sz * 0.6), (r * math.cos(a), r * math.sin(a), 4.0 + rng.uniform(-0.12, 0.16)), mats[k % 4], "anvil", segs=(9, 6))
	for k in range(7):
		a = 2 * math.pi * k / 7
		r = rng.uniform(0.3, 0.9)
		b.blob((0.9, 0.9, 0.6), (r * math.cos(a), r * math.sin(a), 4.3), mats[(k + 1) % 4], "anvil", segs=(9, 6))
	for k in range(4):
		a = 2 * math.pi * k / 4 + 0.4
		p0 = Vector((1.6 * math.cos(a), 1.6 * math.sin(a), 3.82))
		_wb_bolt(b, p0, p0 + Vector((0.3 * math.cos(a), 0.3 * math.sin(a), -0.9)), rng, 0.03, m["bolt"] if k % 2 else m["bolt_b"], "anvil", jag=0.12)
	for k in range(6):   # lightning crawling down the walls
		z0 = rng.uniform(0.4, 1.4) if k < 3 else rng.uniform(3.0, 3.6)
		a = rng.uniform(0, 2 * math.pi)
		r = rad(z0) + 0.1
		p0 = Vector((r * math.cos(a), r * math.sin(a), z0 + 0.35))
		p1 = Vector((r * 0.9 * math.cos(a + 0.5), r * 0.9 * math.sin(a + 0.5), z0 - 0.35))
		_wb_bolt(b, p0, p1, rng, 0.025, m["bolt"], "wall_a" if k < 3 else "wall_c", jag=0.1)
	# the wheel: a vertical ring of cloud turning round the eye, spokes of lightning out of it
	c = Vector((0, -0.2, 2.3))
	for ring, (rr, n, sz) in enumerate(((0.62, 12, 0.34), (0.9, 16, 0.4), (1.12, 14, 0.3))):
		for k in range(n):
			a = 2 * math.pi * k / n + ring * 0.3
			p = c + Vector((rr * math.cos(a), 0.06 * ring, rr * math.sin(a) * 0.92))
			b.blob((sz, sz * 0.8, sz * 0.9), tuple(p), mats[(k + ring) % 4], "wheel", segs=(8, 5))
	for k in range(3):   # spiral arms of the wheel
		pts = []
		for j in range(13):
			f = j / 12
			a = 2 * math.pi * (k / 3 + 0.6 * f)
			rr = 0.42 + 0.8 * f
			pts.append(c + Vector((rr * math.cos(a), -0.05 + 0.1 * f, rr * math.sin(a) * 0.92)))
		for j, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(tuple(p), tuple(q), 0.06, 0.05, m["pale"], "wheel", sides=5)
	for k in range(5):
		a = 2 * math.pi * k / 5 + 0.2
		p0 = c + Vector((0.46 * math.cos(a), -0.12, 0.46 * math.sin(a)))
		p1 = c + Vector((1.25 * math.cos(a + 0.25), -0.1, 1.2 * math.sin(a + 0.25)))
		pts = _wb_bolt(b, p0, p1, rng, 0.028, m["bolt"] if k % 2 else m["bolt_b"], "wheel", steps=5, jag=0.08)
		mid = pts[2]
		_wb_bolt(b, mid, mid + Vector((0.3 * math.cos(a - 0.6), -0.05, 0.3 * math.sin(a - 0.6))), rng, 0.018, m["bolt_b"], "wheel", steps=3, jag=0.05)
	# the eye: a great glaring orb, a golden iris and a slit pupil, heavy lids of cloud narrowing it
	e = Vector((0, -0.34, 2.3))
	b.blob((0.78, 0.4, 0.56), tuple(e), m["eye"], "eye", segs=(16, 10))
	b.seg(tuple(e + Vector((0, -0.16, 0))), tuple(e + Vector((0, -0.2, 0))), 0.21, 0.19, m["iris"], "eye", sides=18)
	b.blob((0.07, 0.05, 0.32), tuple(e + Vector((0, -0.215, 0))), m["pupil"], "eye", segs=(8, 6))
	b.blob((0.1, 0.02, 0.07), tuple(e + Vector((0.08, -0.215, 0.09))), m["bolt"], "eye", segs=(6, 4))   # a glint
	b.blob((1.0, 0.48, 0.34), tuple(e + Vector((0, -0.02, 0.28))), m["dark"], "eye", rot=(0, 0, 0), segs=(12, 7))   # the upper lid, lowered
	b.blob((0.94, 0.44, 0.26), tuple(e + Vector((0, 0.0, -0.27))), m["cloud"], "eye", segs=(12, 7))
	for s in (1, -1):   # a scowl: the lid pulled down toward the middle
		b.blob((0.4, 0.36, 0.22), tuple(e + Vector((0.2 * s, -0.08, 0.21))), m["dark"], "eye", rot=(0, 18 * s, 0), segs=(9, 6))
	# arms of cloud lashing out of the wheel, forking into claws of lightning
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		arm, claw = f"arm_{side}", f"claw_{side}"
		sh, el, wr = Vector((1.05 * s, -0.1, 2.5)), Vector((1.5 * s, -0.3, 2.1)), Vector((1.62 * s, -0.5, 1.5))
		b.bone(arm, tuple(sh), "mid")
		b.bone(claw, tuple(el), arm)
		for k in range(5):
			f = k / 4
			p = sh + (el - sh) * f
			sz = 0.5 - 0.1 * f
			b.blob((sz, sz, sz * 0.85), tuple(p), mats[k % 4], arm, segs=(8, 6))
		for k in range(4):
			f = k / 3
			p = el + (wr - el) * f
			sz = 0.4 - 0.1 * f
			b.blob((sz, sz, sz * 0.85), tuple(p), mats[(k + 1) % 4], claw, segs=(8, 6))
		for k in range(3):   # three forks of lightning for talons
			d = Vector(((k - 1) * 0.35 * s + 0.1 * s, -0.5, -1)).normalized()
			_wb_bolt(b, wr, wr + d * 0.7, rng, 0.035, m["bolt"], claw, steps=4, jag=0.06)
		_wb_bolt(b, sh + Vector((0, -0.2, 0.1)), el + Vector((0, -0.25, 0)), rng, 0.02, m["bolt_b"], arm, steps=4, jag=0.06)
	# its foot: a skirt of torn-up dust, stones and a broken branch whirling round it
	for k in range(12):
		a = 2 * math.pi * k / 12 + rng.uniform(-0.2, 0.2)
		r = rng.uniform(0.35, 0.6)
		b.blob((0.5, 0.42, 0.18), (r * math.cos(a), r * math.sin(a), 0.08), [m["dust"], m["cloud"]][k % 2], "skirt", segs=(8, 5))
	for k in range(22):
		z = rng.uniform(0.2, 1.6)
		a = rng.uniform(0, 2 * math.pi)
		r = rad(z) + rng.uniform(0.15, 0.35)
		sz = rng.uniform(0.08, 0.2)
		_rock(b, (sz, sz, sz * 0.8), (r * math.cos(a), r * math.sin(a), z), [m["stone"], m["stone_r"]][k % 2], "debris", rng)
	p = Vector((rad(1.1) + 0.3, 0, 1.1))
	b.seg(tuple(p + Vector((0, -0.4, 0.1))), tuple(p + Vector((0, 0.4, -0.1))), 0.05, 0.03, m["stone_r"], "debris", sides=5)
	b.seg(tuple(p), tuple(p + Vector((0.1, 0.1, 0.25))), 0.03, 0.01, m["stone_r"], "debris", sides=4)
	arm = b.build()

	def spin(t, turns):
		return {"wall_a": {"rot": (0, 0, 360 * turns * t)}, "wall_b": {"rot": (0, 0, 360 * turns * t)},
				"wall_c": {"rot": (0, 0, 360 * max(1, turns // 2) * t)}, "anvil": {"rot": (0, 0, -360 * t)},
				"wheel": {"rot": (0, 360 * max(1, turns // 2) * t, 0)}, "debris": {"rot": (0, 0, 360 * turns * t)},
				"skirt": {"rot": (0, 0, 360 * turns * t)}}

	def sway(t, amp, lean, cycles=1):
		return {"low": {"rot": (lean * 0.3 + amp * wave(t, cycles), amp * wave(t, cycles, 0.25), 0)},
				"mid": {"rot": (lean * 0.4 + amp * wave(t, cycles, 0.2), amp * 0.8 * wave(t, cycles, 0.45), 0)},
				"top": {"rot": (lean * 0.2 - amp * wave(t, cycles, 0.3), -amp * wave(t, cycles, 0.6), 0)}}

	def arms(t, lift, reach, cycles=1):
		return {"arm_l": {"rot": (reach + 6 * wave(t, cycles), lift + 8 * wave(t, cycles, 0.2), 0)},
				"arm_r": {"rot": (reach + 6 * wave(t, cycles, 0.5), -lift - 8 * wave(t, cycles, 0.7), 0)},
				"claw_l": {"rot": (10 * wave(t, cycles, 0.3), 12 * wave(t, cycles, 0.1), 0)},
				"claw_r": {"rot": (10 * wave(t, cycles, 0.8), -12 * wave(t, cycles, 0.6), 0)}}

	def glare(t):   # the eye rolls round, fixes, narrows
		look = seq(t, [(0, 0), (0.2, 0), (0.28, 24), (0.5, 24), (0.58, -20), (0.8, -20), (0.88, 0)])
		return {"eye": {"rot": (4 * wave(t, 1), 0, look)}}

	def idle(t):
		return merge_scaled(sway(t, 2, 0, 1), spin(t, 2), arms(t, 0, 0, 1), glare(t))

	def walk(t):
		return merge_scaled(sway(t, 2, -6, 1), spin(t, 2), arms(t, 6, -14, 1), {"eye": {"rot": (-4, 0, 0)}})

	def run(t):
		return merge_scaled(sway(t, 3, -12, 1), spin(t, 2), arms(t, 14, -30, 1), {"eye": {"rot": (-6, 0, 0)}})

	def attack(t):   # the arms rear up and slam down in forks of lightning, the eye flaring wide
		up = seq(t, [(0, 0), (0.32, 36), (0.42, 40), (0.56, -24), (0.75, -20), (1, 0)])
		reach = seq(t, [(0, 0), (0.32, -30), (0.42, -34), (0.56, 60), (0.75, 52), (1, 0)])
		lean = seq(t, [(0, 0), (0.32, 6), (0.56, -12), (0.75, -10), (1, 0)])
		flare = seq(t, [(0, 1.0), (0.32, 1.3), (0.56, 1.35), (0.85, 1.0)])
		return merge_scaled({"low": {"rot": (lean * 0.3, 0, 0)}, "mid": {"rot": (lean, 0, 0)}, "top": {"rot": (-lean * 0.5, 0, 0)},
							 "arm_l": {"rot": (reach, up, 0)}, "arm_r": {"rot": (reach, -up, 0)},
							 "claw_l": {"rot": (reach * 0.4, 0, 0)}, "claw_r": {"rot": (reach * 0.4, 0, 0)},
							 "eye": {"scale": (flare, 1, flare)}, "wheel": {"scale": (flare * 0.9 + 0.1, 1, flare * 0.9 + 0.1)}},
							spin(t, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge_scaled({"low": {"rot": (4 * k, 3 * k, 0)}, "mid": {"rot": (8 * k, -4 * k, 0)}, "top": {"rot": (8 * k, 5 * k, 0)},
							 "eye": {"rot": (6 * k, 0, 14 * k), "scale": (1, 1, 1 - 0.5 * k)}}, spin(t, 1), arms(t, 20 * k, -20 * k, 1))

	def death(t):   # the eye shuts, the wheel flies apart, the storm unwinds and sinks into a ring of cloud
		d = seq(t, [(0.2, 0), (0.95, 1)])
		shut = seq(t, [(0, 1), (0.3, 0.06)])
		reel = seq(t, [(0, 0), (0.2, 10), (0.4, -6), (0.6, 0)])
		spin_ = 720 * (1 - (1 - t) ** 2)
		return merge_scaled({"low": {"rot": (reel * 0.3, 0, 0), "scale": (1 + 0.5 * d, 1 + 0.5 * d, max(0.06, 1 - 0.94 * d))},
							 "mid": {"rot": (reel, 0, 0)}, "top": {"rot": (-reel, 0, 0)},
							 "wall_a": {"rot": (0, 0, spin_)}, "wall_b": {"rot": (0, 0, spin_)}, "wall_c": {"rot": (0, 0, spin_ * 0.6)},
							 "anvil": {"rot": (0, 0, -spin_ * 0.3), "scale": (1 + 0.8 * d, 1 + 0.8 * d, 1)},
							 "wheel": {"rot": (0, spin_, 0), "scale": (1 + 1.5 * d, 1, 1 + 1.5 * d)},
							 "eye": {"scale": (1, 1, shut)}, "debris": {"rot": (0, 0, spin_)}, "skirt": {"scale": (1 + 0.8 * d, 1 + 0.8 * d, 1)}},
							arms(t, -30 * d, 30 * d, 1))

	clip_scaled(arm, "idle", 3.0, idle, True)
	clip_scaled(arm, "walk", 1.4, walk, True)
	clip_scaled(arm, "run", 0.9, run, True)
	clip_scaled(arm, "attack", 1.0, attack, False)
	clip_scaled(arm, "hit", 0.45, hit, False)
	clip_scaled(arm, "death", 2.0, death, False)
	return arm


# ---------------------------------------------------------------- the sky birds: giant eagle, thunderbird, Skarrow

SKY_BIRD_COLORS = {
	# a golden eagle grown huge: dark brown, a golden nape and crown, pale-barred tail, yellow feet
	"eagle": {"body": "5e3c1e", "back": "442a14", "breast": "6e4624", "head": "7a5028", "nape": "d8a040", "nape_l": "f0c860",
			  "covert": "8a5a2c", "flight": "3e2814", "tip": "20150e", "tail": "5a4028", "band": "b09a74",
			  "beak": "e8c040", "beak_d": "3a2a1a", "foot": "e8b830", "talon": "1e1612", "eye": "f0a020", "trouser": "8a6636"},
	# the thunderbird: blue-black, steel-blue hackles, storm-barred tail, a pale beak
	"thunder": {"body": "222a3e", "back": "141a2a", "breast": "303c58", "head": "1e2638", "nape": "3e5a88", "nape_l": "6a90c8",
				"covert": "2a3856", "flight": "121826", "tip": "080c16", "tail": "1a2234", "band": "4a6a9a",
				"beak": "d0c080", "beak_d": "2a2620", "foot": "9a9678", "talon": "0e0e12", "eye": "fff0a0", "trouser": "283248"},
	# Skarrow: the same, blacker, a storm-white head and crest, white bars on the wings and tail
	"skarrow": {"body": "1a2034", "back": "0e1220", "breast": "283450", "head": "e2eaf4", "nape": "c8d8ec", "nape_l": "ffffff",
				"covert": "243250", "flight": "0e1424", "tip": "060a14", "tail": "141a2c", "band": "e8f0fa",
				"beak": "e8d890", "beak_d": "3a3428", "foot": "b0aa88", "talon": "0a0a0e", "eye": "ffffff", "trouser": "222c44"},
}


def build_sky_bird(name="giant_eagle", kind="eagle"):
	"""A great bird hanging in the wind on broad wings: each wing in three joints (arm, hand, the fingered
	primaries at its tip) so a beat rolls out along it; a hooked beak under a stern brow, hackles at the
	nape, a fanned tail, feathered legs with talons hanging. The thunderbird crackles with lightning along
	its leading edges and off every primary; Skarrow is bigger (built 1.45x), with a storm-white head, a
	crest and white lightning."""
	import random
	rng = random.Random({"eagle": 3301, "thunder": 3303, "skarrow": 3305}[kind])
	C = SKY_BIRD_COLORS[kind]
	storm = kind != "eagle"
	mat = {k: material(f"{name}_{k}", v, 0.85 if k not in ("beak", "beak_d", "talon", "eye") else 0.4,
					   emit=(1.0 if kind == "eagle" else 4.0) if k == "eye" else 0.0) for k, v in C.items()}
	pupil = material(f"{name}_pupil", "100c08", 0.3)
	if storm:
		white = kind == "skarrow"
		bolt = material(f"{name}_bolt", "ffffff" if white else "9adcff", 0.2, emit=6.0 if white else 4.5)
		bolt_b = material(f"{name}_bolt_b", "d8ecff" if white else "e8f8ff", 0.2, emit=5.0)
	b = Builder(name)
	H = 1.9
	b.bone("root", (0, 0, H))
	b.bone("body", (0, 0, H), "root")
	b.bone("neck", (0, -0.36, H + 0.08), "body")
	b.bone("head", (0, -0.56, H + 0.24), "neck")
	b.bone("tail", (0, 0.44, H - 0.04), "body")
	b.bone("legs", (0, 0.12, H - 0.2), "body")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"wing_{side}", (0.2 * s, -0.08, H + 0.1), "body")
		b.bone(f"hand_{side}", (0.82 * s, -0.04, H + 0.12), f"wing_{side}")
		b.bone(f"tip_{side}", (1.32 * s, 0.0, H + 0.12), f"hand_{side}")

	# the body: a heavy teardrop, dark back, the breast in overlapping feathers
	b.blob((0.56, 1.0, 0.54), (0, 0.04, H), mat["body"], "body", rot=(-8, 0, 0), segs=(14, 9))
	b.blob((0.44, 0.74, 0.2), (0, 0.1, H + 0.2), mat["back"], "body", rot=(-6, 0, 0), segs=(10, 6))
	b.blob((0.44, 0.5, 0.46), (0, -0.24, H - 0.04), mat["breast"], "body", rot=(-20, 0, 0), segs=(10, 7))
	for k in range(9):
		x = (k % 3 - 1) * 0.11
		z = H + 0.04 - 0.1 * (k // 3)
		_oblob(b, (0.12, 0.17, 0.035), (x, -0.44 + 0.04 * (k // 3), z), (0, 0.3, -1), (0, -1, 0.2),
			   mat["body"] if k % 2 else mat["breast"], "body", segs=(6, 4))
	# the neck and head: hackles at the nape, a hooked beak, a stern brow
	b.seg((0, -0.22, H + 0.06), (0, -0.5, H + 0.24), 0.17, 0.13, mat["nape"], "neck", sides=9)
	for k in range(7):
		a = math.radians(-60 + 20 * k)
		p = Vector((0.12 * math.sin(a), -0.34 + 0.08 * math.cos(a), H + 0.2 + 0.05 * math.cos(a)))
		_oblob(b, (0.08, 0.24, 0.03), tuple(p), (math.sin(a) * 0.3, 1, -0.4), (math.sin(a), 0, 1), mat["nape_l"] if k % 2 else mat["nape"],
			   "neck", segs=(6, 4))
	b.blob((0.3, 0.36, 0.3), (0, -0.6, H + 0.3), mat["head"], "head", segs=(12, 9))
	b.blob((0.26, 0.3, 0.12), (0, -0.58, H + 0.43), mat["nape_l"] if kind != "thunder" else mat["head"], "head", segs=(10, 5))
	b.seg((0, -0.74, H + 0.33), (0, -0.79, H + 0.32), 0.08, 0.07, mat["beak"], "head", sides=8)          # cere
	b.seg((0, -0.79, H + 0.32), (0, -0.94, H + 0.29), 0.066, 0.04, mat["beak"], "head", sides=7)
	b.seg((0, -0.94, H + 0.29), (0, -0.98, H + 0.19), 0.04, 0.004, mat["beak_d"], "head", sides=6)       # the hook
	b.seg((0, -0.76, H + 0.25), (0, -0.9, H + 0.24), 0.04, 0.015, mat["beak"], "head", sides=5)
	for s in (1, -1):
		b.blob((0.07, 0.06, 0.07), (0.11 * s, -0.7, H + 0.34), mat["eye"], "head", segs=(7, 5))
		b.blob((0.035, 0.03, 0.04), (0.125 * s, -0.725, H + 0.34), pupil, "head", segs=(5, 3))
		b.blob((0.14, 0.14, 0.05), (0.1 * s, -0.7, H + 0.39), mat["back"] if kind != "skarrow" else mat["nape"], "head",
			   rot=(0, -22 * s, 0), segs=(6, 3))
	if kind == "thunder":   # a short swept crest
		for k in range(3):
			x = (k - 1) * 0.05
			_oblob(b, (0.05, 0.26, 0.025), (x, -0.5, H + 0.5), (x, 0.8, 0.6), (0, -0.6, 0.8), mat["nape"], "head", segs=(6, 4))
	if kind == "skarrow":   # a tall crest of white feathers tipped with sparks
		for k in range(7):
			x = (k - 3) * 0.045
			ln = 0.42 + 0.2 * (1 - abs(k - 3) / 3)
			d = Vector((x * 1.4, 0.55, 1)).normalized()
			base = Vector((x, -0.58, H + 0.44))
			_oblob(b, (0.07, ln, 0.025), tuple(base + d * ln * 0.5), tuple(d), (0, -1, 0.4), mat["nape_l"] if k % 2 else mat["nape"],
				   "head", segs=(6, 4))
			_oblob(b, (0.06, ln * 0.3, 0.03), tuple(base + d * ln * 0.88), tuple(d), (0, -1, 0.4), mat["flight"], "head", segs=(6, 4))
			if k % 2 == 0:
				_wb_bolt(b, base + d * ln, base + d * (ln + 0.18) + Vector((0, 0.05, 0)), rng, 0.012, bolt, "head", steps=2, jag=0.03)
	# the wings: coverts over broad secondaries on the arm and hand, fingered primaries at the tip
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		wing, hand, tip = f"wing_{side}", f"hand_{side}", f"tip_{side}"
		up = (0, 0, 1)
		sh, el, wr = Vector((0.18 * s, -0.08, H + 0.1)), Vector((0.82 * s, -0.04, H + 0.12)), Vector((1.32 * s, 0.0, H + 0.12))
		b.seg(tuple(sh), tuple(el), 0.08, 0.06, mat["covert"], wing, sides=6)
		b.seg(tuple(el), tuple(wr), 0.06, 0.045, mat["covert"], hand, sides=6)
		for k in range(6):   # secondaries on the arm
			x = (0.24 + 0.1 * k) * s
			ln = 0.62 + 0.02 * k
			d = Vector((0.04 * s, 1, -0.04)).normalized()
			_oblob(b, (0.14, ln, 0.035), (x, 0.0 + ln * 0.5, H + 0.09), d, up, mat["flight"] if k % 2 else mat["back"], wing, segs=(6, 4))
			_oblob(b, (0.12, ln * 0.3, 0.04), (x, 0.0 + ln * 0.9, H + 0.085), d, up,
				   mat["band"] if kind == "skarrow" and k % 2 else mat["tip"], wing, segs=(6, 4))
		for k in range(4):
			x = (0.26 + 0.15 * k) * s
			_oblob(b, (0.18, 0.32, 0.05), (x, 0.08, H + 0.13), (0.05 * s, 1, 0), up, mat["covert"] if k % 2 else mat["body"], wing, segs=(6, 4))
		for k in range(5):   # inner primaries on the hand
			x = (0.86 + 0.1 * k) * s
			ln = 0.64 - 0.02 * k
			d = Vector((0.12 * s, 1, -0.03)).normalized()
			_oblob(b, (0.13, ln, 0.033), (x + d.x * ln * 0.5, 0.02 + ln * 0.5, H + 0.1), d, up, mat["flight"] if k % 2 else mat["back"], hand, segs=(6, 4))
			_oblob(b, (0.11, ln * 0.3, 0.038), (x + d.x * ln * 0.9, 0.02 + ln * 0.9, H + 0.095), d, up,
				   mat["band"] if kind == "skarrow" and k % 2 == 0 else mat["tip"], hand, segs=(6, 4))
		for k in range(3):
			x = (0.9 + 0.14 * k) * s
			_oblob(b, (0.16, 0.28, 0.05), (x, 0.1, H + 0.14), (0.1 * s, 1, 0), up, mat["covert"], hand, segs=(6, 4))
		fingers = []
		for k in range(6):   # the primaries splayed like fingers at the tip
			a = math.radians(-6 + 13 * k)
			d = Vector((math.cos(a) * s, math.sin(a), 0.03 + 0.03 * (5 - k) / 5)).normalized()
			ln = 0.78 - 0.04 * k
			base = wr + Vector((0, 0.02 + 0.02 * k, 0))
			_oblob(b, (0.11, ln, 0.03), tuple(base + d * ln * 0.5), tuple(d), up, mat["flight"], tip, segs=(6, 4))
			_oblob(b, (0.09, ln * 0.32, 0.035), tuple(base + d * ln * 0.86), tuple(d), up, mat["tip"], tip, segs=(6, 4))
			fingers.append((base, d, ln))
		_oblob(b, (0.2, 0.3, 0.06), tuple(wr + Vector((0.04 * s, 0.06, 0.02))), (s, 0.3, 0), up, mat["covert"], tip, segs=(6, 4))
		if storm:   # lightning running along the leading edge and crackling off each primary
			_wb_bolt(b, sh + Vector((0.06 * s, -0.08, 0.04)), el + Vector((0, -0.08, 0.04)), rng, 0.02, bolt, wing, steps=6, jag=0.035)
			_wb_bolt(b, el + Vector((0, -0.07, 0.04)), wr + Vector((0, -0.07, 0.04)), rng, 0.018, bolt, hand, steps=5, jag=0.035)
			for k, (base, d, ln) in enumerate(fingers):
				e = base + d * ln
				_wb_bolt(b, e - d * 0.1, e + d * (0.22 if k % 2 else 0.14) + Vector((0, 0.04, 0)), rng, 0.014, bolt_b if k % 2 else bolt, tip, steps=3, jag=0.04)
				if kind == "skarrow" or k % 2 == 0:   # and back along the finger's edge
					_wb_bolt(b, base + d * 0.2 + Vector((0, 0, 0.02)), e + Vector((0, 0, 0.02)), rng, 0.01, bolt, tip, steps=4, jag=0.025)
			for k in range(3):   # sparks along the trailing edge
				x = (0.35 + 0.22 * k) * s
				p = Vector((x, 0.66, H + 0.08))
				_wb_bolt(b, p, p + Vector((0.06 * s, 0.2, -0.06)), rng, 0.012, bolt_b, wing, steps=2, jag=0.03)
	# the tail: a broad fan, barred
	for k in range(9):
		yaw = math.radians((k - 4) * 8)
		d = Vector((math.sin(yaw), math.cos(yaw), -0.2)).normalized()
		a = Vector((0, 0.4, H - 0.04))
		ln = 0.74 - 0.03 * abs(k - 4)
		_oblob(b, (0.15, ln, 0.03), tuple(a + d * ln * 0.5), tuple(d), (0, 0, 1), mat["tail"], "tail", segs=(6, 4))
		_oblob(b, (0.14, 0.08, 0.035), tuple(a + d * ln * 0.62), tuple(d), (0, 0, 1), mat["band"], "tail", segs=(6, 3))
		_oblob(b, (0.13, ln * 0.2, 0.035), tuple(a + d * ln * 0.9), tuple(d), (0, 0, 1), mat["tip"], "tail", segs=(6, 4))
		if storm and k % 4 == 0:
			e = a + d * ln
			_wb_bolt(b, e - d * 0.06, e + d * 0.2 + Vector((0, 0, -0.05)), rng, 0.012, bolt, "tail", steps=3, jag=0.03)
	if kind == "skarrow":   # two long streamers
		for s in (1, -1):
			d = Vector((0.12 * s, 1, -0.3)).normalized()
			a = Vector((0.04 * s, 0.4, H - 0.06))
			_oblob(b, (0.1, 1.3, 0.025), tuple(a + d * 0.65), tuple(d), (0, 0, 1), mat["tail"], "tail", segs=(6, 4))
			_oblob(b, (0.1, 0.24, 0.03), tuple(a + d * 1.2), tuple(d), (0, 0, 1), mat["band"], "tail", segs=(6, 4))
			_wb_bolt(b, a + d * 1.3, a + d * 1.62, rng, 0.014, bolt, "tail", steps=3, jag=0.04)
	# feathered legs hanging, talons half open
	for s in (1, -1):
		b.blob((0.18, 0.22, 0.28), (0.1 * s, 0.1, H - 0.24), mat["trouser"], "legs", segs=(8, 6))
		b.seg((0.1 * s, 0.12, H - 0.36), (0.1 * s, 0.16, H - 0.6), 0.045, 0.04, mat["foot"], "legs", sides=6)
		for dx, dy in ((0.0, -0.14), (0.06, -0.1), (-0.06, -0.1), (0.0, 0.1)):
			root = Vector((0.1 * s, 0.16, H - 0.62))
			end = root + Vector((dx * s, dy, -0.05))
			b.seg(tuple(root), tuple(end), 0.03, 0.024, mat["foot"], "legs", sides=5)
			dd = (end - root).normalized()
			b.seg(tuple(end), tuple(end + dd * 0.05 + Vector((0, 0, -0.05))), 0.022, 0.003, mat["talon"], "legs", sides=4)
	k_size = 1.45 if kind == "skarrow" else 1.0
	if k_size != 1.0:
		_scaled(b, k_size)
	H *= k_size
	arm = b.build()

	def beat(t, cycles, amp=34, lift=0.0):
		"""A wingbeat rolling out along the wing: the arm leads, the hand and tip lag behind it."""
		f = amp * wave(t, cycles) + lift
		g = amp * 0.45 * wave(t, cycles, -0.1) + lift * 0.3
		h = amp * 0.35 * wave(t, cycles, -0.2)
		return {"wing_l": {"rot": (0, f, 0)}, "wing_r": {"rot": (0, -f, 0)}, "hand_l": {"rot": (0, g, 0)}, "hand_r": {"rot": (0, -g, 0)},
				"tip_l": {"rot": (0, h, 0)}, "tip_r": {"rot": (0, -h, 0)}}

	def tail(t, cycles, amp=5):
		return {"tail": {"rot": (amp * wave(t, cycles, 0.2), 0, 3 * wave(t, 1))}}

	def idle(t):   # hangs in the wind on slow, deep beats, head turning
		look = seq(t, [(0, 0), (0.25, 0), (0.32, 20), (0.55, 20), (0.62, -16), (0.85, -16), (0.92, 0)])
		return merge({"root": {"loc": (0, 0, -0.1 * wave(t, 2, 0.1))}, "body": {"rot": (4 * wave(t, 2, 0.3), 0, 0)},
					  "head": {"rot": (-4 * wave(t, 2, 0.3), 0, look)}, "legs": {"rot": (6 * wave(t, 2), 0, 0)}},
					 beat(t, 2, 36, 6), tail(t, 2))

	def walk(t):   # flies forward nose-down
		return merge({"root": {"loc": (0, 0, -0.07 * wave(t, 2, 0.1)), "rot": (-12, 0, 0)}, "head": {"rot": (10, 0, 0)},
					  "legs": {"rot": (-34, 0, 0)}}, beat(t, 2, 32, 4), tail(t, 2, 4))

	def run(t):
		return merge({"root": {"loc": (0, 0, -0.06 * wave(t, 2, 0.1)), "rot": (-22, 0, 0)}, "head": {"rot": (18, 0, 0)},
					  "legs": {"rot": (-55, 0, 0)}}, beat(t, 2, 42, 0), tail(t, 2, 3))

	def attack(t):   # rears up on high wings, then stoops in raking with its talons
		rear = seq(t, [(0, 0), (0.35, 1), (0.55, -0.6), (0.75, -0.4), (1, 0)])
		dive = seq(t, [(0, 0), (0.35, -0.12), (0.55, 0.5), (0.75, 0.4), (1, 0)])
		wings = seq(t, [(0, 0), (0.35, 50), (0.55, -36), (0.75, -18), (1, 0)])
		return merge({"root": {"loc": (0, dive * k_size, (0.12 * rear - 0.25 * max(0.0, -rear)) * k_size), "rot": (28 * rear, 0, 0)},
					  "head": {"rot": (-20 * rear + seq(t, [(0.45, 0), (0.6, -16), (0.8, 0)]), 0, 0)},
					  "legs": {"rot": (seq(t, [(0, 0), (0.35, 20), (0.55, 85), (0.75, 65), (1, 0)]), 0, 0)},
					  "wing_l": {"rot": (0, wings, 0)}, "wing_r": {"rot": (0, -wings, 0)},
					  "hand_l": {"rot": (0, wings * 0.4, 0)}, "hand_r": {"rot": (0, -wings * 0.4, 0)},
					  "tip_l": {"rot": (0, wings * 0.3, 0)}, "tip_r": {"rot": (0, -wings * 0.3, 0)}}, tail(t, 1, 14))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.2 * k, 0.1 * k), "rot": (20 * k, 14 * k, 0)}, "head": {"rot": (16 * k, 0, 20 * k)}},
					 beat(t, 2, 28, 30 * k), tail(t, 2, 10))

	def death(t):   # the wings fail; it tumbles to the ground and lies with one wing spread
		f = seq(t, [(0.1, 0), (0.7, 1)])
		g = seq(t, [(0.5, 0), (0.95, 1)])
		flap = 1 - seq(t, [(0.1, 0), (0.5, 1)])
		return merge({"root": {"loc": (0, 0.1 * f, -(H - 0.3 * k_size) * f + 0.08 * math.sin(math.pi * f)), "rot": (-16 * f, 70 * g, 0)},
					  "neck": {"rot": (-30 * g, 0, 20 * g)}, "head": {"rot": (-20 * g, 0, 30 * g)}, "legs": {"rot": (50 * g, 0, 0)},
					  "wing_l": {"rot": (0, 30 * flap * wave(t, 3) - 55 * g, 0)}, "wing_r": {"rot": (0, -30 * flap * wave(t, 3) - 65 * g, 0)},
					  "hand_l": {"rot": (0, -10 * g, 0)}, "hand_r": {"rot": (0, -6 * g, 0)},
					  "tip_l": {"rot": (0, -10 * g, 0)}, "tip_r": {"rot": (0, -4 * g, 0)}, "tail": {"rot": (10 * g, 0, 20 * g)}})

	slow = 1.2 if kind == "skarrow" else 1.0
	clip(arm, "idle", 2.4 * slow, idle, True)
	clip(arm, "walk", 1.0 * slow, walk, True)
	clip(arm, "run", 0.6 * slow, run, True)
	clip(arm, "attack", 0.8 * slow, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.4 * slow, death, False)
	return arm


def build_giant_eagle():
	return build_sky_bird("giant_eagle", "eagle")


def build_thunderbird():
	return build_sky_bird("thunderbird", "thunder")


def build_skarrow_thunderbird():
	return build_sky_bird("skarrow_thunderbird", "skarrow")


# ---------------------------------------------------------------- cliff drake

def build_cliff_drake():
	"""A lean rust-red drake of the mesa walls: the ash drake's frame with its fire put out (sandy belly,
	a spade of skin for a tail tip), a frill of ochre skin on spines fanned round its head, a ridge of
	sail along its back, pale bands down the tail and long climbing claws."""
	import random
	rng = random.Random(3231)
	arm = build_ash_drake("cliff_drake_src", False)
	_dw_recolor(arm, "cliff_drake_src", "cliff_drake", {
		"scale": ("8e3e22", 0.75, 0.0), "scale_light": ("b8643a", 0.75, 0.0), "scale_dark": ("4e1e10", 0.75, 0.0),
		"belly": ("dcae78", 0.8, 0.0), "belly_dark": ("b07a4a", 0.8, 0.0), "horn": ("e8dcc0", 0.5, 0.0),
		"horn_dark": ("7a5238", 0.6, 0.0), "membrane": ("c8703a", 0.8, 0.0), "claw": ("e0d4b8", 0.4, 0.0),
		"eye": ("f4e040", 0.2, 3.0), "ember": ("a4401e", 0.8, 0.0), "tooth": ("f2ead4", 0.4, 0.0)})
	frill = material("cliff_drake_frill", "e0943e", 0.8)
	frill_d = material("cliff_drake_frill_dark", "a8502a", 0.8)
	spine = material("cliff_drake_spine", "4e1e10", 0.6)
	pale = material("cliff_drake_band", "d8a070", 0.8)

	def more(b):
		# the frill: spines fanned round the back of the head, skin between them, dark-edged
		c = Vector((0, -0.9, 1.14))
		tips = []
		for k in range(11):
			a = math.radians(-105 + 21 * k)
			d = Vector((math.sin(a), 0.45, math.cos(a))).normalized()
			ln = 0.42 + 0.1 * math.cos(a)
			tip = c + d * ln
			b.seg(tuple(c + d * 0.1), tuple(tip), 0.025, 0.006, spine, "head", sides=4)
			tips.append(tip)
		for k, (p, q) in enumerate(zip(tips, tips[1:])):
			start = len(b.parts)
			inner = c + ((p + q) / 2 - c) * 0.18
			notch = c + ((p + q) / 2 - c) * 0.86
			_slab(b, [tuple(c + (p - c) * 0.2), tuple(p), tuple(notch)], 0.02, frill if k % 2 else frill_d)
			_slab(b, [tuple(c + (p - c) * 0.2), tuple(notch), tuple(q), tuple(c + (q - c) * 0.2)], 0.02, frill)
			_on_bone(b, start, "head")
		for k in range(7):   # a low sail of skin along the spine
			y = -0.44 + k * 0.16
			start = len(b.parts)
			_slab(b, [(0, y - 0.08, 0.96), (0, y + 0.08, 0.96), (0, y + 0.04, 1.16 - 0.03 * abs(k - 3))], 0.02, frill_d)
			_on_bone(b, start, "body")
		for k, (y, z, r, bone) in enumerate(((0.8, 0.62, 0.18, "tail1"), (1.28, 0.49, 0.12, "tail2"), (1.72, 0.37, 0.07, "tail3"))):
			start = len(b.parts)
			_wrap(b, (0, y, z), (r * 1.02, r * 1.02), 0.08, 0.015, pale, rot=(-16, 0, 0), sides=12)
			_on_bone(b, start, bone)
		for name_, (x, y) in {"leg_fl": (0.26, -0.42), "leg_fr": (-0.26, -0.42), "leg_bl": (0.27, 0.44), "leg_br": (-0.27, 0.44)}.items():
			for k in (-1, 0, 1):   # long climbing claws
				root = Vector((x + 0.06 * k, y - 0.16, 0.05))
				b.seg(tuple(root), tuple(root + Vector((0.015 * k, -0.12, -0.035))), 0.022, 0.0, spine, name_, sides=4)
	return _dw_extend(arm, more)


# ---------------------------------------------------------------- the Kitewing bandits (KayKit Rogue mesh space)

# rogue cells: tunic (0,1), collar and cape (1,1), bracers and belt (5,0), buckles (3,0) (6,0), trousers (7,1),
# boots (3,2), gloves (7,2), skin (0,0), hair (1,0). The bandits: patched brown leathers, a faded red collar,
# sand-colored trousers; the chief in a deep sky-blue coat with ochre facings
KITEWING_CELLS = {(0, 1): ("8a6440", "3a2616"), (1, 1): ("b0503a", "4a1c12"), (5, 0): ("4a3020", "1a0e08"),
				  (3, 0): ("c8a060", "6a4a1c"), (6, 0): ("c8a060", "6a4a1c"), (7, 1): ("a89270", "4a3a24"),
				  (3, 2): ("5a3e28", "1e140a"), (7, 2): ("6a4a30", "26180e"), (0, 0): ("d8a47a", "8a5a3a"),
				  (1, 0): ("3a2a1e", "120c08")}
KITEWING_CHIEF_CELLS = {(0, 1): ("2e4a7a", "0e1a34"), (1, 1): ("d0903a", "6a3a10"), (5, 0): ("3a2418", "140a06"),
						(3, 0): ("e8c060", "8a5a18"), (6, 0): ("e8c060", "8a5a18"), (7, 1): ("b09a70", "54442a"),
						(3, 2): ("3a2a1e", "120c08"), (7, 2): ("5a3e28", "1e140a"), (0, 0): ("c89470", "7a4e32"),
						(1, 0): ("8a8a86", "2e2e2c")}


def kitewing_materials(chief=False):
	p = "kitewing_chief" if chief else "kitewing"
	return _rmats(p, {"leather": ("7a5234", 0.85), "leather_d": ("3e2818", 0.9), "strap": ("4a3020", 0.85),
					  "brass": ("c8a050", 0.35), "lens": ("6ab0d8", 0.1, 0.35), "lens_d": ("2a4a6a", 0.15),
					  "scarf": ("b8502e", 0.9), "scarf_d": ("7a2e18", 0.9), "wood": ("8a6a44", 0.8), "wood_d": ("5a4028", 0.85),
					  "cloth": ("e2d4b0", 0.9), "cloth_b": ("7aa0c0", 0.9), "cloth_o": ("d08a3a", 0.9), "cloth_r": ("a8442e", 0.9),
					  "patch": ("6a7a4a", 0.9), "stitch": ("2e2418", 0.9), "rope": ("b8a070", 0.9), "iron": ("5a5a5e", 0.5),
					  "coat": ("2e4a7a", 0.85), "coat_d": ("1a2c4e", 0.9), "ochre": ("d0903a", 0.85), "hat": ("4a3424", 0.85),
					  "hat_d": ("2a1c12", 0.9), "sail": ("eee2c4", 0.9), "paint": ("b8401e", 0.85), "paint_b": ("2e5a8a", 0.85),
					  "paint_y": ("e8b440", 0.8),
					  "f_eagle": ("6a4424", 0.9), "f_gold": ("d8a040", 0.85), "f_storm": ("222a3e", 0.85),
					  "f_white": ("f2f0ea", 0.9), "f_blue": ("5a8ac8", 0.85)})


def _kite_goggles(b, m, z=1.86, band=True, r=0.535):
	"""Brass flying goggles with blue lenses, pushed up on the brow, on a leather strap round the head."""
	if band:
		_wrap(b, (0, 0.01, z - 0.02), (r, r), 0.08, 0.025, m["strap"], rot=(-6, 0, 0), sides=20)
	y = -math.sqrt(max(0.0, r * r - 0.16 * 0.16)) - 0.01
	for s in (1, -1):
		cx = 0.16 * s
		b.seg((cx, y + 0.04, z), (cx, y - 0.06, z), 0.11, 0.12, m["brass"], "x", sides=12)
		b.seg((cx, y - 0.05, z), (cx, y - 0.075, z), 0.09, 0.09, m["lens"], "x", sides=12)
		b.blob((0.06, 0.02, 0.03), (cx + 0.03, y - 0.08, z + 0.03), m["cloth"], "x", segs=(5, 3))   # a glint
	b.seg((-0.06, y - 0.03, z), (0.06, y - 0.03, z), 0.03, 0.03, m["brass"], "x", sides=5)


def build_kitewing_goggles():
	"""The bandit's head: goggles up on the brow and a sun-faded scarf pulled up over nose and mouth,
	knotted behind with its tails blowing (the Rogue's own head and hair show between)."""
	m = kitewing_materials()
	b = Builder("kitewing_goggles")
	_kite_goggles(b, m)
	_shell(b, (1.16, 1.16, 1.12), (0, 0.01, 1.6), m["scarf"], lambda d: -0.6 < d.z < -0.1, segs=(18, 16))
	_wrap(b, (0, 0.01, 1.54), (0.575, 0.575), 0.025, 0.012, m["scarf_d"], rot=(0, 0, 0), sides=20)   # a hem
	b.blob((0.2, 0.14, 0.16), (0, 0.6, 1.5), m["scarf_d"], "x", segs=(8, 5))                        # the knot
	for s, ln in ((1, 0.44), (-1, 0.36)):
		_slab(b, [(0.02 * s, 0.62, 1.5), (0.12 * s, 0.64, 1.48), (0.24 * s, 0.84, 1.2 + 0.4 - ln), (0.12 * s, 0.8, 1.16 + 0.4 - ln)],
			  0.03, m["scarf"])
	for x, z in ((0.3, 1.36), (-0.22, 1.28)):   # patches on the scarf
		_slab(b, [(x - 0.07, -0.56, z - 0.05), (x + 0.07, -0.56, z - 0.05), (x + 0.07, -0.55, z + 0.05), (x - 0.07, -0.55, z + 0.05)],
			  0.02, m["patch"] if x > 0 else m["cloth_o"])
	return b.build_static()


def _kite_harness(b, m):
	for s in (1, -1):   # straps over each shoulder, crossing at the back
		b.seg((0.2 * s, -0.37, 1.18), (0.26 * s, -0.1, 1.3), 0.03, 0.03, m["strap"], "x", sides=4)
		b.seg((0.26 * s, -0.1, 1.3), (0.24 * s, 0.25, 1.26), 0.03, 0.03, m["strap"], "x", sides=4)
		b.seg((0.24 * s, 0.25, 1.26), (-0.16 * s, 0.38, 0.72), 0.03, 0.03, m["strap"], "x", sides=4)
		b.seg((0.2 * s, -0.37, 1.18), (0.12 * s, -0.4, 0.78), 0.03, 0.03, m["strap"], "x", sides=4)
	_ring(b, (0, -0.41, 1.0), (0.06, 0.06), (0, 90), 0.018, m["brass"], sides=10)
	b.seg((0.12, -0.4, 0.98), (-0.12, -0.4, 0.98), 0.025, 0.025, m["strap"], "x", sides=4)


def build_kitewing_rig():
	"""The bandit's back: a harness, a pack, and a kite-wing folded shut on a mast above the head: ribs of
	cane hinged at the top, patched cloth folded between them, a rope coiled over the pack."""
	import random
	rng = random.Random(3241)
	m = kitewing_materials()
	b = Builder("kitewing_rig")
	_kite_harness(b, m)
	_box(b, (0.36, 0.14, 0.4), (0, 0.42, 0.96), m["leather"])
	_box(b, (0.3, 0.06, 0.14), (0, 0.5, 1.08), m["leather_d"])
	_ring(b, (0, 0.52, 0.8), (0.14, 0.1), (0, 0), 0.03, m["rope"], sides=14)                      # a coil of rope
	_ring(b, (0, 0.52, 0.84), (0.12, 0.09), (0, 0), 0.03, m["rope"], sides=14)
	top, bottom = Vector((0, 0.56, 2.36)), Vector((0, 0.52, 0.6))
	b.seg(tuple(bottom), tuple(top), 0.028, 0.024, m["wood_d"], "x", sides=6)                    # the mast
	b.blob((0.08, 0.08, 0.08), tuple(top), m["brass"], "x", segs=(6, 4))
	cloths = (m["cloth"], m["cloth_b"], m["cloth_o"], m["cloth_r"])
	for s in (1, -1):
		ribs = [top]
		for k in range(4):   # the ribs, folded down like a shut fan
			tip = Vector(((0.14 + 0.13 * k) * s, 0.6 + 0.05 * k, 0.72 + 0.1 * k))
			b.seg(tuple(top), tuple(tip), 0.018, 0.014, m["wood"], "x", sides=5)
			ribs.append(tip)
		for k in range(1, 4):   # cloth folded between them, each fold its own faded color
			p, q = ribs[k], ribs[k + 1]
			mid = (p + q) / 2 + Vector((0.02 * s, 0.05 + 0.02 * k, 0))
			_slab(b, [tuple(top), tuple(p), tuple(mid)], 0.018, cloths[(k + (s > 0)) % 4])
			_slab(b, [tuple(top), tuple(mid), tuple(q)], 0.018, cloths[(k + 1 + (s > 0)) % 4])
		_slab(b, [tuple(top), tuple(Vector((0.02 * s, 0.56, 0.7))), tuple(ribs[1])], 0.018, cloths[2])
		for k in range(2):   # patches sewn on
			u = rng.uniform(0.45, 0.7)
			p = top + (ribs[2 + k] - top) * u + Vector((0.03 * s, 0.07 + 0.02 * k, 0))
			_box(b, (0.1, 0.02, 0.1), tuple(p), m["patch"] if k else m["cloth_r"], rot=(0, rng.uniform(-20, 20), 0))
		b.seg(tuple(ribs[-1]), tuple(ribs[-1] + Vector((0.02 * s, 0.02, -0.14))), 0.012, 0.012, m["rope"], "x", sides=4)
	_wrap(b, (0, 0.62, 1.0), (0.46, 0.12), 0.05, 0.015, m["rope"], sides=16)                       # lashed shut
	return b.build_static()


def build_kitewing_belt():
	"""A belt with a grappling hook on a coil of line at one hip and pouches at the other."""
	m = kitewing_materials()
	b = Builder("kitewing_belt")
	_wrap(b, (0, 0.0, 0.66), (0.44, 0.39), 0.08, 0.025, m["strap"], sides=18)
	b.blob((0.1, 0.04, 0.08), (0, -0.41, 0.66), m["brass"], "x", segs=(6, 4))
	for k in range(3):   # a coil of line
		_ring(b, (0.46, 0.02, 0.5 + 0.04 * k), (0.03, 0.14), (0, 0), 0.025, m["rope"], sides=12)
	c = Vector((0.5, 0.06, 0.3))   # the hook: a shank and three curved tines
	b.seg((0.48, 0.04, 0.46), tuple(c), 0.022, 0.022, m["iron"], "x", sides=5)
	for k in range(3):
		a = 2 * math.pi * k / 3
		d = Vector((math.cos(a), math.sin(a), 0))
		p1 = c + d * 0.08 + Vector((0, 0, -0.04))
		p2 = p1 + d * 0.03 + Vector((0, 0, 0.08))
		b.seg(tuple(c), tuple(p1), 0.018, 0.015, m["iron"], "x", sides=4)
		b.seg(tuple(p1), tuple(p2), 0.015, 0.004, m["iron"], "x", sides=4)
	for x, y in ((-0.36, -0.22), (-0.42, 0.06)):
		b.blob((0.14, 0.1, 0.16), (x, y, 0.56), m["leather"], "x", segs=(8, 6))
		b.blob((0.12, 0.08, 0.05), (x, y, 0.64), m["leather_d"], "x", segs=(6, 4))
	return b.build_static()


def build_kitewing_chief_hat():
	"""The chief's hat: a broad brim cocked up at one side, goggles on the band, a great plume of eagle,
	thunderbird and white feathers."""
	m = kitewing_materials(True)
	b = Builder("kitewing_chief_hat")
	b.blob((1.7, 1.64, 0.07), (0, 0.0, 2.02), m["hat_d"], "x", rot=(-3, -10, 0), segs=(20, 5))       # brim, cocked
	b.seg((0, 0.0, 2.0), (0, 0.02, 2.36), 0.47, 0.41, m["hat"], "x", sides=16)
	b.blob((0.82, 0.8, 0.2), (0, 0.02, 2.36), m["hat"], "x", segs=(14, 6))
	_wrap(b, (0, 0.0, 2.1), (0.475, 0.475), 0.08, 0.02, m["ochre"], sides=18)
	_kite_goggles(b, m, z=2.14, band=False, r=0.48)
	base = Vector((0.4, 0.2, 2.14))
	for k, (mat, tip, ln, yaw, pitch) in enumerate(((m["f_eagle"], m["f_gold"], 0.9, 30, 50), (m["f_storm"], m["f_blue"], 1.0, 18, 58),
													(m["f_white"], m["f_storm"], 0.8, 40, 40), (m["f_gold"], m["f_eagle"], 0.6, 50, 30),
													(m["f_storm"], m["f_white"], 0.7, 8, 66))):
		d = Vector((math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)), math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)),
					math.sin(math.radians(pitch))))
		_oblob(b, (0.13, ln, 0.02), tuple(base + d * ln * 0.5), tuple(d), (1, -0.2, 0), mat, "x", segs=(8, 3))
		_oblob(b, (0.11, ln * 0.3, 0.025), tuple(base + d * ln * 0.86), tuple(d), (1, -0.2, 0), tip, "x", segs=(6, 3))
	b.blob((0.12, 0.1, 0.12), tuple(base), m["brass"], "x", segs=(6, 4))
	return b.build_static()


def build_kitewing_chief_coat():
	"""The chief's coat top (collar, lapels, feathered epaulettes) and the rig on his back: a great kite
	spread on its spars behind him, the sails painted with Vayuketh's spiral wind and a red sun."""
	m = kitewing_materials(True)
	b = Builder("kitewing_chief_coat")
	_wrap(b, (0, 0.04, 1.36), (0.36, 0.32), 0.18, 0.05, m["coat_d"], rot=(-12, 0, 0), gap=(245, 295), sides=18)
	_slab(b, [(-0.1, -0.39, 1.26), (0.1, -0.39, 1.26), (0.12, -0.4, 0.74), (-0.12, -0.4, 0.74)], 0.02, m["ochre"])
	for s in (1, -1):
		_slab(b, [(0.1 * s, -0.4, 1.3), (0.28 * s, -0.37, 1.3), (0.2 * s, -0.4, 1.02), (0.13 * s, -0.41, 0.98)], 0.03, m["coat_d"])
		for k in range(4):
			b.blob((0.05, 0.03, 0.05), (0.16 * s, -0.415, 1.12 - 0.12 * k), m["brass"], "x", segs=(6, 4))
		for k in range(6):   # epaulettes of feathers
			a = math.radians(-60 + 24 * k)
			p = Vector((0.4 * s, 0.14 * math.sin(a), 1.28))
			d = Vector((0.5 * s, math.sin(a) * 0.4, -0.8)).normalized()
			_oblob(b, (0.1, 0.26, 0.02), tuple(p + d * 0.12), tuple(d), (s, 0, 0.4), [m["f_eagle"], m["f_storm"], m["f_white"]][k % 3], "x", segs=(6, 3))
		b.blob((0.3, 0.3, 0.1), (0.38 * s, 0.0, 1.29), m["coat"], "x", rot=(0, 16 * s, 0), segs=(10, 5))
	_kite_harness(b, m)
	# the kite: a mast up the back, spars out to each wingtip, sails between, all spread
	top, bottom = Vector((0, 0.56, 2.5)), Vector((0, 0.54, 0.62))
	b.seg(tuple(bottom), tuple(top), 0.032, 0.026, m["wood_d"], "x", sides=6)
	b.blob((0.09, 0.09, 0.09), tuple(top), m["brass"], "x", segs=(6, 4))
	_box(b, (0.34, 0.14, 0.36), (0, 0.44, 0.98), m["leather"])
	for s in (1, -1):
		wing_tip = Vector((1.36 * s, 0.78, 1.66))
		low_tip = Vector((0.82 * s, 0.72, 0.96))
		mid = Vector((0, 0.56, 0.8))
		b.seg(tuple(top), tuple(wing_tip), 0.024, 0.016, m["wood"], "x", sides=5)
		b.seg(tuple(Vector((0, 0.55, 1.5))), tuple(wing_tip), 0.02, 0.015, m["wood"], "x", sides=5)   # a cross-spar
		b.seg(tuple(mid), tuple(low_tip), 0.02, 0.015, m["wood"], "x", sides=5)
		b.seg(tuple(wing_tip), tuple(low_tip), 0.012, 0.012, m["rope"], "x", sides=4)                   # the trailing line
		_slab(b, [tuple(top + Vector((0.02 * s, 0.02, 0))), tuple(wing_tip + Vector((0, 0.02, 0))), tuple(low_tip + Vector((0, 0.02, 0))),
				  tuple(mid + Vector((0.02 * s, 0.02, 0)))], 0.02, m["sail"])
		# the painting, on both faces: a red sun with a blue spiral of wind across it, a band at the edge
		n = (wing_tip - top).cross(low_tip - top).normalized()
		if n.y < 0:
			n = -n
		cen = (top + wing_tip + low_tip + mid) / 4 + Vector((0.06 * s, 0.02, 0))
		for side_ in (1, -1):
			off = n * 0.045 * side_
			_sun(b, tuple(cen + off), tuple(n * side_), 0.2, m["paint"], m["paint_y"], count=10, ray_len=0.5, thick=0.01)
			pts = []
			for k in range(14):
				f = k / 13
				a = 2 * math.pi * 1.4 * f
				r = 0.04 + 0.2 * f
				u = n.cross(Vector((0, 0, 1))).normalized()
				v = n.cross(u).normalized()
				pts.append(cen + off * 1.6 + (u * math.cos(a) + v * math.sin(a)) * r)
			for p, q in zip(pts, pts[1:]):
				b.seg(tuple(p), tuple(q), 0.014, 0.014, m["paint_b"], "x", sides=4)
			for p, q in ((top, wing_tip), (wing_tip, low_tip)):   # a painted band along the edges
				a_ = p + (cen - p) * 0.07 + off * 1.3
				c_ = q + (cen - q) * 0.07 + off * 1.3
				b.seg(tuple(a_), tuple(c_), 0.02, 0.02, m["paint"], "x", sides=4)
		for k in range(3):   # ribbons streaming off the wingtip
			start = len(b.parts)
			_wb_ribbon(b, [wing_tip, wing_tip + Vector((0.1 * s, 0.25, -0.1 - 0.06 * k)), wing_tip + Vector((0.06 * s, 0.5, -0.3 - 0.1 * k))],
					   0.05, [m["paint"], m["paint_b"], m["paint_y"]][k], "x", up=(s, 0, 0.3), taper=0.4)
	return b.build_static()


def build_kitewing_chief_tails():
	"""The long coat's skirts to the shins, split behind for riding the wind, an ochre sash and brass buckle."""
	m = kitewing_materials(True)
	b = Builder("kitewing_chief_tails")
	_shell(b, (1.0, 0.92, 1.9), (0, 0.02, 0.74), m["coat"], lambda d: d.y > -0.45 and -0.74 < d.z < -0.02 and abs(d.x) > 0.05, segs=(18, 18))
	_shell(b, (1.02, 0.94, 1.9), (0, 0.02, 0.74), m["ochre"], lambda d: d.y > -0.45 and -0.74 < d.z < -0.67 and abs(d.x) > 0.05, segs=(18, 18))
	_wrap(b, (0, 0.0, 0.68), (0.45, 0.4), 0.14, 0.03, m["ochre"], sides=18)
	_wrap(b, (0, 0.0, 0.76), (0.46, 0.41), 0.05, 0.03, m["strap"], sides=18)
	b.blob((0.14, 0.05, 0.1), (0, -0.44, 0.76), m["brass"], "x", segs=(6, 4))
	for k in range(3):   # a coil of line at the hip
		_ring(b, (0.48, 0.04, 0.52 + 0.04 * k), (0.03, 0.14), (0, 0), 0.025, m["rope"], sides=12)
	return b.build_static()


def build_kite_hook():
	"""The Kitewing's weapon (KayKit weapons' frame: grip at the origin, up +Z): a short cane haft with a
	hooked iron blade for catching lines and throats, a loop of rope at the butt."""
	m = kitewing_materials()
	steel = metal_material("kite_hook_steel", "a8acb0", 0.3, 0.6)
	b = Builder("kite_hook")
	b.seg((0, 0, -0.16), (0, 0, 0.5), 0.028, 0.025, m["wood"], "x", sides=7)
	for k in range(4):
		z = -0.12 + 0.07 * k
		b.seg((0, 0, z), (0, 0, z + 0.03), 0.034, 0.034, m["strap"], "x", sides=7)
	_ring(b, (0, 0, -0.24), (0.05, 0.02), (90, 0), 0.012, m["rope"], sides=10)
	b.seg((0, 0, 0.46), (0, 0, 0.56), 0.035, 0.035, m["iron"], "x", sides=6)
	pts = []   # the hook: a blade curling over and back down
	for k in range(9):
		a = math.radians(-90 + 200 * k / 8)
		pts.append(Vector((0.1 + 0.1 * math.cos(a), 0, 0.64 + 0.12 * math.sin(a))))
	pts = [Vector((0, 0, 0.54))] + pts
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		w = 0.04 * (1 - k / len(pts)) + 0.008
		n = Vector((0, 1, 0))
		dd = (q - p).normalized()
		o = dd.cross(n).normalized()
		_slab(b, [tuple(p), tuple(q), tuple(q + o * w), tuple(p + o * w)], 0.014, steel)
	b.seg((0, 0, 0.56), (-0.03, 0, 0.72), 0.02, 0.0, steel, "x", sides=4)   # a spike on the back
	return b.build_static()


# ---------------------------------------------------------------- the stone giants (KayKit Barbarian mesh space)

# the barbarian as a stone giant: skin (0,0) (1,3) (3,1) weathered gray stone, trousers (7,1) hide, boots (3,2)
# bare stone feet, vest (7,0) moss, fur trim (2,1) lichen, leather (6,0) (6,1) (5,1), iron (3,0) stone,
# hand wraps (7,2) rope
STONE_GIANT_CELLS = {(0, 0): ("a8a89c", "545650"), (1, 3): ("a8a89c", "545650"), (3, 1): ("9c9c90", "4a4c46"),
					 (7, 1): ("7a6c56", "2e2618"), (3, 2): ("8a8a80", "3a3a36"), (7, 0): ("6e7a48", "2a3218"),
					 (2, 1): ("b4ac6c", "54502c"), (6, 0): ("6a5a44", "261e14"), (6, 1): ("6a5a44", "261e14"),
					 (3, 0): ("8a8a82", "3a3a36"), (5, 1): ("6a5a44", "261e14"), (7, 2): ("a8946a", "4a3e28")}
STACKSTONE_CELLS = {(0, 0): ("8e9088", "3e403a"), (1, 3): ("8e9088", "3e403a"), (3, 1): ("868880", "383a34"),
					(7, 1): ("5e5446", "221e16"), (3, 2): ("76786e", "30322c"), (7, 0): ("56663a", "1e2812"),
					(2, 1): ("c8d0a0", "5e6a44"), (6, 0): ("5a4c3a", "1e1810"), (6, 1): ("5a4c3a", "1e1810"),
					(3, 0): ("76786e", "30322c"), (5, 1): ("5a4c3a", "1e1810"), (7, 2): ("9a8a60", "443a22")}


def stone_giant_materials(elder=False):
	p = "old_stackstone" if elder else "stone_giant"
	return _rmats(p, {"stone": ("9a9c92", 0.95) if not elder else ("868880", 0.95), "stone_d": ("5e605a", 0.95) if not elder else ("4a4c46", 0.95),
					  "stone_l": ("bcbcb0", 0.9) if not elder else ("a8a89c", 0.9), "moss": ("5e7434", 0.95), "moss_l": ("8a9a48", 0.95),
					  "lichen": ("c8c47a", 0.95), "lichen_o": ("d8903a", 0.95), "lichen_p": ("b8c8b0", 0.95),
					  "eye": ("c8e4f0", 0.2, 1.4), "socket": ("26282a", 0.95), "grass": ("a8a050", 0.9),
					  "rope": ("b09a6a", 0.9), "rope_d": ("7a6a44", 0.9), "hide": ("7a6a52", 0.9), "hide_d": ("4a4034", 0.9),
					  "beard": ("a8b490", 0.95), "beard_d": ("7a8a66", 0.95), "cloth": ("5a8ac8", 0.9), "cloth_w": ("f0ead8", 0.9)})


def _lichen(b, rng, center, radii, count, mats, arc=(0, 360), elev=(-40, 70), size=0.06):
	"""Flat crusts of lichen scattered over an ellipsoid's face."""
	c = Vector(center)
	rx, ry, rz = radii
	for k in range(count):
		a = math.radians(rng.uniform(*arc))
		e = math.radians(rng.uniform(*elev))
		d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
		p = c + Vector((rx * d.x, ry * d.y, rz * d.z))
		n = Vector((d.x / rx, d.y / ry, d.z / rz)).normalized()
		sz = size * rng.uniform(0.6, 1.4)
		_oblob(b, (sz, sz * rng.uniform(0.7, 1.3), 0.025), tuple(p + n * 0.005), tuple(n.orthogonal()), tuple(n), mats[k % len(mats)], "x", segs=(6, 3))


def _stone_giant_head(b, m, elder, rng):
	st, dk, lt = m["stone"], m["stone_d"], m["stone_l"]
	b.blob((0.58, 0.56, 0.62), (0, -0.02, 1.64), st, "x", segs=(12, 9))                            # a blocky skull
	for loc, size in (((0.18, -0.12, 1.84), (0.26, 0.3, 0.22)), ((-0.16, -0.08, 1.86), (0.28, 0.32, 0.2)),
					  ((0.0, 0.12, 1.86), (0.4, 0.3, 0.2)), ((0.22, 0.06, 1.62), (0.2, 0.3, 0.3)), ((-0.22, 0.06, 1.6), (0.2, 0.3, 0.3))):
		_rock(b, size, loc, [st, lt, dk][rng.randrange(3)], "x", rng, jitter=0.14)                  # planes chipped by the wind
	_rock(b, (0.66, 0.24, 0.2), (0, -0.25, 1.77), dk, "x", rng, jitter=0.1)                        # the ledge of a brow
	b.blob((0.58, 0.46, 0.3), (0, -0.1, 1.42), st, "x", segs=(10, 7))                               # a jaw like a lintel
	_rock(b, (0.3, 0.2, 0.18), (0, -0.28, 1.36), lt, "x", rng, jitter=0.12)                        # chin
	_rock(b, (0.15, 0.18, 0.22), (0, -0.36, 1.64), lt, "x", rng, jitter=0.12)                      # a flat nose
	b.seg((-0.12, -0.33, 1.47), (0.12, -0.33, 1.47), 0.018, 0.018, m["socket"], "x", sides=4)      # a thin hard mouth
	for s in (1, -1):
		b.blob((0.15, 0.06, 0.08), (0.13 * s, -0.3, 1.69), m["socket"], "x", segs=(8, 5))
		b.blob((0.07, 0.03, 0.04), (0.13 * s, -0.33, 1.69), m["eye"], "x", segs=(6, 4))
		_rock(b, (0.12, 0.16, 0.18), (0.3 * s, -0.02, 1.62), st, "x", rng)                         # ears worn to nubs
		_rock(b, (0.2, 0.18, 0.16), (0.2 * s, -0.24, 1.5), st, "x", rng)                           # cheeks
	_lichen(b, rng, (0, -0.02, 1.64), (0.3, 0.29, 0.32), 10 if not elder else 16, (m["lichen"], m["lichen_o"], m["lichen_p"]), size=0.07)
	# a cap of moss on the crown with tufts of dry grass in it
	_shell(b, (0.66, 0.64, 0.68), (0, 0.0, 1.66), m["moss"], lambda d: d.z > (0.45 if not elder else 0.3), segs=(14, 10))
	for k in range(5 if not elder else 8):
		a = rng.uniform(0, 2 * math.pi)
		r = rng.uniform(0.0, 0.2)
		p = Vector((r * math.cos(a), r * math.sin(a), 1.97 - r * 0.5))
		_tuft(b, tuple(p), (math.cos(a) * 0.4, math.sin(a) * 0.4 + 0.2, 1), 0.16, 6, 0.4, (m["grass"], m["moss_l"]), 3250 + k, width=0.014)
	if not elder:   # a stubble of moss on the jaw
		_shell(b, (0.6, 0.5, 0.34), (0, -0.1, 1.41), m["moss"], lambda d: d.y < -0.2 and d.z < 0.2, segs=(12, 8))
		return
	# the elder: a long beard of lichen hanging to the belly, stones knotted into it, a heavier brow
	_rock(b, (0.72, 0.28, 0.24), (0, -0.27, 1.82), dk, "x", rng, jitter=0.1)
	_shell(b, (0.64, 0.52, 0.38), (0, -0.1, 1.41), m["beard_d"], lambda d: d.y < -0.1 and d.z < 0.3, segs=(12, 8))
	for k in range(13):
		x = (k - 6) * 0.042
		top = Vector((x, -0.3 - 0.04 * (1 - abs(x) / 0.3), 1.44))
		ln = 0.72 - 0.4 * abs(x) / 0.26 + rng.uniform(-0.06, 0.06)
		sway = rng.uniform(-0.04, 0.04)
		pts = [top, top + Vector((sway, -0.07, -ln * 0.4)), top + Vector((sway * 2, -0.05, -ln * 0.75)), top + Vector((sway * 2.5, -0.02, -ln))]
		_chain(b, pts, 0.04, 0.012, m["beard"] if k % 2 else m["beard_d"], sides=5)
		if k % 4 == 1:
			b.blob((0.06, 0.06, 0.06), tuple(pts[2]), m["stone_l"], "x", segs=(6, 4))
	for s in (1, -1):   # moustaches of it
		_chain(b, [(0.06 * s, -0.33, 1.52), (0.2 * s, -0.33, 1.46), (0.26 * s, -0.3, 1.22)], 0.035, 0.012, m["beard"], sides=5)


def _stone_giant_chest(b, m, elder, rng):
	st = m["stone"]
	b.seg((0, 0.0, 1.22), (0, -0.04, 1.44), 0.2, 0.18, st, "x", sides=10)
	b.blob((0.9, 0.58, 0.46), (0, -0.09, 1.16), st, "x", segs=(12, 8))
	b.blob((0.84, 0.5, 0.52), (0, 0.12, 1.2), st, "x", segs=(12, 8))
	for s in (1, -1):
		_rock(b, (0.48, 0.5, 0.42), (0.36 * s, 0.02, 1.3), [st, m["stone_l"]][s > 0], "x", rng, jitter=0.12)   # boulder shoulders
		_rock(b, (0.36, 0.16, 0.26), (0.18 * s, -0.32, 1.14), m["stone_l"], "x", rng, jitter=0.12)
		_shell(b, (0.46, 0.46, 0.4), (0.37 * s, 0.02, 1.34), m["moss"], lambda d: d.z > 0.72, segs=(10, 7))   # moss on top
		_tuft(b, (0.36 * s, 0.06, 1.53), (0.2 * s, 0.1, 1), 0.14, 5, 0.4, (m["grass"], m["moss_l"]), 3260 + (s > 0), width=0.014)
	_lichen(b, rng, (0, -0.02, 1.18), (0.46, 0.34, 0.26), 12 if not elder else 18, (m["lichen"], m["lichen_o"], m["lichen_p"]), size=0.08)
	for k in range(5):   # cracks and seams in the stone
		x = rng.uniform(-0.3, 0.3)
		z = rng.uniform(0.98, 1.3)
		y = -0.09 - 0.29 * math.sqrt(max(0.0, 1 - (x / 0.45) ** 2 - ((z - 1.16) / 0.23) ** 2)) - 0.01
		b.seg((x, y, z), (x + rng.uniform(-0.1, 0.1), y, z - rng.uniform(0.08, 0.16)), 0.01, 0.006, m["socket"], "x", sides=4)
	# a rope sling over one shoulder to the other hip
	b.seg((0.34, -0.34, 1.34), (-0.36, -0.36, 0.8), 0.035, 0.035, m["rope"], "x", sides=5)
	b.seg((0.34, 0.34, 1.34), (-0.36, 0.38, 0.82), 0.035, 0.035, m["rope"], "x", sides=5)
	if not elder:   # a small cairn of stones slung in a net at the back
		for k, (x, z, sz) in enumerate(((0.0, 0.9, 0.34), (0.05, 1.1, 0.28), (-0.03, 1.27, 0.2))):
			_rock(b, (sz, sz * 0.7, sz * 0.55), (x, 0.52, z), [m["stone_l"], m["stone_d"], m["stone_l"]][k], "x", rng, jitter=0.1)
		for s in (1, -1):   # the net's cords
			_chain(b, [(0.12 * s, 0.4, 1.34), (0.14 * s, 0.62, 1.2), (0.16 * s, 0.66, 0.9), (0.1 * s, 0.56, 0.72)], 0.018, 0.018, m["rope_d"], sides=4)
		b.seg((-0.18, 0.66, 1.0), (0.18, 0.66, 1.0), 0.018, 0.018, m["rope_d"], "x", sides=4)
		return
	# the elder: a tall cairn of flat stones stacked on his back, lashed on, moss on the ledges, a
	# strip of blue-and-white prayer cloth to Vayuketh streaming from the top stone
	z = 0.7
	for k in range(7):
		w = 0.66 - 0.07 * k
		h = 0.2 + 0.03 * (k % 2)
		y = 0.8 + 0.03 * math.sin(k * 1.7)
		_rock(b, (w, w * 0.75, h), (0.04 * math.sin(k * 2.3), y, z + h / 2), [st, m["stone_l"], m["stone_d"]][k % 3], "x", rng,
			  rot=(0, rng.uniform(-6, 6), rng.uniform(0, 40)), jitter=0.08)
		if k % 2 == 0:
			_shell(b, (w * 0.8, w * 0.6, h * 1.3), (0.04 * math.sin(k * 2.3) + 0.06, y, z + h / 2), m["moss"], lambda d: d.z > 0.62, segs=(10, 6))
		z += h * 0.92
	top = Vector((0, 0.82, z + 0.02))
	b.seg((0, 0.82, z - 0.2), tuple(top + Vector((0, 0, 0.5))), 0.025, 0.02, m["rope_d"], "x", sides=5)   # a stick jammed in the top
	for k in range(4):
		p = top + Vector((0, 0, 0.44 - 0.1 * k))
		_wb_ribbon(b, [p, p + Vector((0.18, 0.1, -0.02)), p + Vector((0.34, 0.22, -0.08))], 0.07, [m["cloth"], m["cloth_w"]][k % 2], "x",
				   up=(0, -1, 0), taper=0.6)
	for s in (1, -1):   # the lashings: ropes from the shoulders down over the stack's face to the belt
		_chain(b, [(0.26 * s, 0.3, 1.36), (0.2 * s, 0.6, 1.52), (0.16 * s, 0.94, 1.32), (0.2 * s, 1.0, 0.94), (0.24 * s, 0.72, 0.74), (0.3 * s, 0.4, 0.7)],
			   0.025, 0.025, m["rope"], sides=5)
	b.seg((-0.2, 1.0, 1.1), (0.2, 1.0, 1.1), 0.022, 0.022, m["rope"], "x", sides=4)


def _stone_giant_kilt(b, m, elder, rng=None):
	_wrap(b, (0, 0.0, 0.7), (0.47, 0.4), 0.1, 0.04, m["rope"], sides=18)
	_shell(b, (0.96, 0.84, 2.0), (0, 0.0, 0.8), m["hide"], lambda d: d.y < -0.72 and -0.5 < d.z < -0.04, segs=(18, 24))
	_shell(b, (0.96, 0.84, 2.0), (0, 0.0, 0.8), m["hide_d"], lambda d: d.y > 0.72 and -0.44 < d.z < -0.04, segs=(18, 24))
	for s in (1, -1):   # ragged fringe at the flaps' hems
		for k in range(3):
			x = (0.06 + 0.1 * k) * s
			b.seg((x, -0.43, 0.36), (x * 1.05, -0.44, 0.26 - 0.03 * (k % 2)), 0.03, 0.01, m["hide"], "x", sides=4)
	for x, z in ((-0.36, 0.56), (0.3, 0.5), (0.44, 0.6)):   # stones hung from the belt on cords
		b.seg((x, -0.3 if abs(x) < 0.4 else -0.1, 0.66), (x, -0.32 if abs(x) < 0.4 else -0.14, z), 0.01, 0.01, m["rope_d"], "x", sides=4)
		b.blob((0.08, 0.06, 0.09), (x, -0.33 if abs(x) < 0.4 else -0.15, z - 0.04), m["stone_l"], "x", segs=(6, 4))
	if elder:
		b.blob((0.16, 0.08, 0.12), (0, -0.44, 0.7), m["stone_l"], "x", segs=(8, 5))   # a stone buckle


def _stone_giant_arm(name, s, elder):
	import random
	rng = random.Random(3271 + (s > 0) + 7 * elder)
	m = stone_giant_materials(elder)
	b = Builder(name)
	b.seg((0.2 * s, 0.0, 1.12), (0.47 * s, 0.01, 1.1), 0.17, 0.14, m["stone"], "x", sides=10)
	_rock(b, (0.26, 0.28, 0.28), (0.33 * s, -0.02, 1.15), m["stone_l"], "x", rng, jitter=0.12)
	_lichen(b, rng, (0.33 * s, 0.0, 1.12), (0.14, 0.16, 0.16), 4, (m["lichen"], m["lichen_o"]), size=0.06)
	return b.build_static()


def _stone_giant_bracer(name, s, elder):
	m = stone_giant_materials(elder)
	b = Builder(name)
	b.seg((0.46 * s, 0.01, 1.1), (0.7 * s, 0.0, 1.1), 0.13, 0.12, m["stone"], "x", sides=10)
	for k in range(4):   # rope wound round the forearm
		x = 0.5 + 0.055 * k
		b.seg((x * s, 0.0, 1.1), ((x + 0.03) * s, 0.0, 1.1), 0.14, 0.14, m["rope"] if k % 2 else m["rope_d"], "x", sides=10)
	return b.build_static()


def _stone_part(name, fn, elder, seed):
	import random
	b = Builder(name)
	fn(b, stone_giant_materials(elder), elder, random.Random(seed))
	return b.build_static()


def _giant_slab(name, elder):
	"""A slab of standing stone for a giant's hand (KayKit weapons' frame: grip at the origin, up +Z): one
	end worked narrow and bound in rope for a grip, the face patched with lichen; the elder's is longer,
	carved with Vayuketh's spiral and hung with a prayer cloth."""
	import random
	rng = random.Random(3281 + elder)
	m = stone_giant_materials(elder)
	b = Builder(name)
	ln = 1.3 if elder else 1.05
	b.seg((0, 0, -0.2), (0, 0, 0.2), 0.06, 0.07, m["stone_d"], "x", sides=7)
	for k in range(6):
		z = -0.17 + 0.06 * k
		b.seg((0, 0, z), (0, 0, z + 0.035), 0.075, 0.075, m["rope"] if k % 2 else m["rope_d"], "x", sides=8)
	_rock(b, (0.18, 0.14, 0.16), (0, 0, -0.24), m["stone"], "x", rng, jitter=0.1)
	_rock(b, (0.26, 0.16, 0.24), (0, 0, 0.26), m["stone"], "x", rng, jitter=0.08)
	_rock(b, (0.4 if not elder else 0.46, 0.16 if not elder else 0.19, ln), (0, 0, 0.24 + ln / 2), m["stone"], "x", rng, jitter=0.07)
	_rock(b, (0.3, 0.17, 0.3), (0.04, 0.0, 0.2 + ln * 0.8), m["stone_l"], "x", rng, jitter=0.1)
	_lichen(b, rng, (0, 0, 0.24 + ln / 2), (0.2, 0.08, ln / 2), 7, (m["lichen"], m["lichen_o"], m["lichen_p"]), arc=(180, 360), elev=(-60, 60), size=0.06)
	_shell(b, (0.36, 0.18, ln * 0.3), (0.04, 0.0, 0.24 + ln * 0.9), m["moss"], lambda d: d.z > 0.55, segs=(10, 6))
	if elder:
		c = Vector((0, -0.1, 0.24 + ln * 0.5))
		pts = []
		for k in range(16):
			f = k / 15
			a = 2 * math.pi * 1.6 * f
			r = 0.02 + 0.13 * f
			pts.append(c + Vector((r * math.cos(a), 0, r * math.sin(a) * 1.4)))
		for p, q in zip(pts, pts[1:]):
			b.seg(tuple(p), tuple(q), 0.012, 0.012, m["socket"], "x", sides=4)
		p = Vector((0.06, 0.0, 0.2))
		_wb_ribbon(b, [p, p + Vector((0.12, -0.04, -0.14)), p + Vector((0.18, -0.02, -0.32))], 0.06, m["cloth"], "x", up=(0, 1, 0), taper=0.5)
		_wb_ribbon(b, [p, p + Vector((0.06, -0.04, -0.18)), p + Vector((0.12, 0.0, -0.36))], 0.05, m["cloth_w"], "x", up=(0, 1, 0), taper=0.5)
	return b.build_static()


def build_stone_giant_head():
	return _stone_part("stone_giant_head", _stone_giant_head, False, 3251)


def build_old_stackstone_head():
	return _stone_part("old_stackstone_head", _stone_giant_head, True, 3253)


def build_stone_giant_chest():
	return _stone_part("stone_giant_chest", _stone_giant_chest, False, 3255)


def build_old_stackstone_chest():
	return _stone_part("old_stackstone_chest", _stone_giant_chest, True, 3257)


def build_stone_giant_kilt():
	return _stone_part("stone_giant_kilt", _stone_giant_kilt, False, 0)


def build_old_stackstone_kilt():
	return _stone_part("old_stackstone_kilt", _stone_giant_kilt, True, 0)


def build_stone_slab():
	return _giant_slab("stone_slab", False)


def build_stackstone_slab():
	return _giant_slab("stackstone_slab", True)


# Windbreak: registered here, beside its builders
CREATURES.update({"gale_spirit": build_gale_spirit, "dust_devil": build_dust_devil, "storm_eye": build_storm_eye,
				  "giant_eagle": build_giant_eagle, "thunderbird": build_thunderbird,
				  "skarrow_thunderbird": build_skarrow_thunderbird, "cliff_drake": build_cliff_drake})
BODIES.update({"kitewing_bandit_body": (KAYKIT + "Rogue.glb", "kitewing_bandit_texture", KITEWING_CELLS, None),
			   "kitewing_chief_body": (KAYKIT + "Rogue.glb", "kitewing_chief_texture", KITEWING_CHIEF_CELLS, None),
			   "stone_giant_body": (KAYKIT + "Barbarian.glb", "stone_giant_texture", STONE_GIANT_CELLS, None),
			   "old_stackstone_body": (KAYKIT + "Barbarian.glb", "old_stackstone_texture", STACKSTONE_CELLS, None)})
ATTACHMENTS.update({"kitewing_goggles": build_kitewing_goggles, "kitewing_rig": build_kitewing_rig,
					"kitewing_belt": build_kitewing_belt, "kitewing_chief_hat": build_kitewing_chief_hat,
					"kitewing_chief_coat": build_kitewing_chief_coat, "kitewing_chief_tails": build_kitewing_chief_tails,
					"kite_hook": build_kite_hook,
					"stone_giant_head": build_stone_giant_head, "old_stackstone_head": build_old_stackstone_head,
					"stone_giant_chest": build_stone_giant_chest, "old_stackstone_chest": build_old_stackstone_chest,
					"stone_giant_kilt": build_stone_giant_kilt, "old_stackstone_kilt": build_old_stackstone_kilt,
					"stone_slab": build_stone_slab, "stackstone_slab": build_stackstone_slab})
for _pre, _elder in (("stone_giant", False), ("old_stackstone", True)):
	for _s, _side in ((1, "l"), (-1, "r")):
		ATTACHMENTS[f"{_pre}_arm_{_side}"] = (lambda n, s, e: lambda: _stone_giant_arm(n, s, e))(f"{_pre}_arm_{_side}", _s, _elder)
		ATTACHMENTS[f"{_pre}_bracer_{_side}"] = (lambda n, s, e: lambda: _stone_giant_bracer(n, s, e))(f"{_pre}_bracer_{_side}", _s, _elder)
# ================================================================ end of Windbreak


# ================================================================ The Long Grass (the Standing Sky, 34-38)
# An endless sea of head-high grass under Vayuketh's wind: tawny grass stalkers and Tawnyjaw the
# man-eater, spotted grass howlers, shaggy thunderhooves and Old Thunderhoof the herd-king, dirkhorns
# with their long straight horns, the hoofborn (horse-folk: a horse's body with a rider's torso rising
# from the shoulders; riders with spears, archers, Khan Oruk), and the dead horse-lords of the burial
# mounds (barrow wights and the Barrow Lord: Skeleton_Warrior in bronze, a rotted fur mantle, green eye-light).


def _lg_skin_tree(b):
	"""A BVH of everything built so far, for laying scars and patches on the outermost skin."""
	from mathutils.bvhtree import BVHTree
	bm = bmesh.new()
	for p in b.parts:
		bm.from_mesh(p.data)
	tree = BVHTree.FromBMesh(bm)
	bm.free()
	return tree


def _lg_scars(b, tree, starts, direction, mat, bone, width=0.03, length=0.3, count=3, gap=0.1):
	"""Parallel claw scars raked across the skin: for each start (a point outside the body and the
	direction to cast toward it), `count` strokes `length` long, `gap` apart."""
	for origin, cast in starts:
		o, c = Vector(origin), Vector(cast).normalized()
		d = Vector(direction).normalized()
		side = d.cross(c).normalized()
		for k in range(count):
			line = []
			for u in (0, 0.25, 0.5, 0.75, 1.0):
				hit, n, _, _ = tree.ray_cast(o + side * gap * k + d * length * u, c)
				if hit is not None:
					line.append((hit - c * 0.006, n))
			for (p, n), (q, _) in zip(line, line[1:]):
				_oblob(b, (width, (q - p).length * 1.4, width * 0.45), tuple((p + q) / 2), q - p, n if n.dot(c) < 0 else -n, mat, bone, segs=(5, 3))


def _lg_shag(b, center, radii, count, mats, bone, rng, size=(0.16, 0.3, 0.07), zmin=-1.0, ymin=-9.0, ymax=9.0, flow=(0, 1, -0.6)):
	"""Tufts of hair laid on the outermost skin round `center` (rays in from an ellipsoid of `radii`),
	each an ellipsoid `size` combed along `flow` over the surface."""
	tree = _lg_skin_tree(b)
	c, r = Vector(center), Vector(radii)
	placed = tries = 0
	while placed < count and tries < count * 30:
		tries += 1
		u = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
		if u.z < zmin:
			continue
		aim = c + Vector((u.x * r.x, u.y * r.y, u.z * r.z))
		if not ymin <= aim.y <= ymax:
			continue
		hit, n, _, _ = tree.ray_cast(aim + u * 3.0, -u)
		if hit is None:
			continue
		if n.dot(u) < 0:
			n = -n
		f = Vector(flow)
		f = (f - n * f.dot(n))
		if f.length < 1e-3:
			f = n.orthogonal()
		k = rng.uniform(0.8, 1.2)
		_oblob(b, (size[0] * k, size[1] * k, size[2]), tuple(hit + f.normalized() * size[1] * 0.3 * k), f, n, mats[placed % len(mats)], bone, segs=(6, 4))
		placed += 1


# ---------------------------------------------------------------- grass stalker and Tawnyjaw
# A great tawny plains cat, low-slung for creeping through the grass: a short dark mane round the
# neck and shoulders, faint stripes on the flanks, a tufted tail. Tawnyjaw, the man-eater, is huge
# (built at 1.7), darker-maned, clawed across the face and flank, one ear torn, one fang broken,
# the left eye a milky scar.

def _plains_cat(name, old=False):
	import random
	rng = random.Random(3413 if old else 3411)
	fur = material(f"{name}_fur", "b88a4c" if old else "cc9e5a", 0.9)
	back = material(f"{name}_back", "9a703a" if old else "b08448", 0.9)
	pale = material(f"{name}_pale", "e2d2b0" if old else "eee0c0", 0.9)
	stripe = material(f"{name}_stripe", "8a6434" if old else "a47c44", 0.9)      # faint: only a shade darker
	mane = material(f"{name}_mane", "3e2616" if old else "6e4a26", 0.95)
	mane_l = material(f"{name}_mane_light", "5e3e22" if old else "8e6632", 0.95)
	eye = material(f"{name}_eye", "e8b83a", 0.25, emit=1.0)
	blind = material(f"{name}_blind", "d8dcd0", 0.3, emit=0.3)
	nose = material(f"{name}_nose", "5a3a30", 0.5)
	dark = material(f"{name}_dark", "2a2018", 0.6)
	pupil = material(f"{name}_pupil", "0e0c0a", 0.2)
	tooth = material(f"{name}_tooth", "f2ecd8", 0.4)
	scar = material(f"{name}_scar", "c89484", 0.7)
	gray = material(f"{name}_gray", "b8ae9a", 0.9)
	b = Builder(name)
	legs = {"leg_fl": (0.22, -0.54), "leg_fr": (-0.22, -0.54), "leg_bl": (0.23, 0.54), "leg_br": (-0.23, 0.54)}
	b.bone("root", (0, 0, 0.62))
	b.bone("body", (0, 0.0, 0.66), "root")
	b.bone("head", (0, -0.84, 0.84), "body")
	b.bone("jaw", (0, -1.02, 0.74), "head")
	b.bone("tail1", (0, 0.86, 0.72), "body")
	b.bone("tail2", (0, 1.3, 0.5), "tail1")
	b.bone("tail3", (0, 1.74, 0.34), "tail2")

	# a long, lean body slung low between the shoulders and the haunches
	b.blob((0.66, 1.76, 0.56), (0, 0.02, 0.7), fur, "body", segs=(14, 9))
	b.blob((0.74, 0.66, 0.64), (0, -0.5, 0.74), fur, "body", segs=(12, 8))                   # shoulders
	b.blob((0.68, 0.64, 0.6), (0, 0.54, 0.72), fur, "body", segs=(12, 8))                    # haunches
	b.blob((0.5, 1.36, 0.24), (0, 0.02, 0.48), pale, "body", segs=(12, 6))                   # pale belly
	b.blob((0.42, 1.36, 0.18), (0, 0.06, 0.97), back, "body", segs=(10, 6))                  # darker spine
	b.blob((0.4, 0.28, 0.38), (0, -0.78, 0.62), pale, "body", segs=(10, 7))                  # pale throat
	_stripes(b, (0, 0.66), -0.24, 0.84, 7, 0.46, stripe, "body", rng, a0=24, a1=84, width=0.05, thick=0.025, slant=0.1)
	if old:   # three raked scars down the left flank
		_lg_scars(b, _lg_skin_tree(b), [((2.0, -0.2, 0.96), (-1, 0, 0))], (0, 0.5, -0.8), scar, "body", width=0.035, length=0.36, gap=0.1)
	# the mane: a short ruff round the neck and over the shoulders, longer under the throat
	grow = 1.3 if old else 1.0
	b.blob((0.72 * grow, 0.5, 0.7 * grow), (0, -0.6, 0.84), mane, "body", segs=(12, 8))          # the collar of the mane
	b.blob((0.4 * grow, 0.66, 0.3), (0, -0.52, 1.02), mane_l, "body", segs=(10, 6))             # over the withers
	for layer, (y0, r0) in enumerate(((-0.72, 0.31), (-0.56, 0.33), (-0.4, 0.3))):
		for k in range(16):
			a = 2 * math.pi * (k + 0.5 * layer) / 16
			out = Vector((math.cos(a), 0, math.sin(a)))
			if math.sin(a) < -0.6 and layer == 2:
				continue   # the belly behind the forelegs stays bare
			root_ = Vector((0, y0, 0.86)) + Vector((out.x * r0 * grow, 0, out.z * r0 * (1.1 if out.z > 0 else 0.95)))
			ln = (0.26 if math.sin(a) < -0.3 else 0.18) * grow * rng.uniform(0.8, 1.15)
			tip = root_ + (out * 0.3 + Vector((0, 0.9, -0.3 if math.sin(a) < -0.3 else -0.08))).normalized() * ln
			b.seg(tuple(root_), tuple(tip), 0.09 * grow, 0.02, (mane, mane_l)[(k + layer) % 2], "body", sides=5)
	# the head: broad, a heavy tan muzzle, small round ears with dark backs
	b.seg((0, -0.54, 0.8), (0, -0.8, 0.84), 0.24, 0.22, fur, "head", sides=10)
	b.blob((0.56, 0.52, 0.46), (0, -0.92, 0.88), fur, "head", segs=(12, 9))
	b.blob((0.38, 0.32, 0.24), (0, -1.16, 0.8), pale, "head", segs=(10, 7))                  # muzzle
	b.blob((0.4, 0.26, 0.12), (0, -1.06, 0.7), pale, "head", segs=(8, 5))                    # chin
	b.blob((0.13, 0.08, 0.08), (0, -1.31, 0.85), nose, "head", segs=(6, 4))
	b.seg((0, -1.26, 0.76), (0, -1.3, 0.82), 0.012, 0.012, dark, "head", sides=3)
	b.blob((0.24, 0.18, 0.09), (0, -1.08, 0.69), pale, "jaw", segs=(8, 5))                   # lower jaw
	b.blob((0.2, 0.05, 0.03), (0, -1.2, 0.735), dark, "head", segs=(8, 3))                   # the dark lip line
	for s in (1, -1):
		scarred_eye = old and s < 0
		b.blob((0.15, 0.08, 0.05), (0.13 * s, -1.12, 0.98), pale, "head", segs=(8, 4))      # pale brows
		b.blob((0.1, 0.07, 0.065), (0.12 * s, -1.13, 0.935), blind if scarred_eye else eye, "head", segs=(8, 5))
		if not scarred_eye:
			b.blob((0.03, 0.03, 0.055), (0.125 * s, -1.16, 0.935), pupil, "head", segs=(4, 3))
		b.seg((0.05 * s, -1.23, 0.84), (0.1 * s, -1.19, 0.94), 0.018, 0.012, dark, "head", sides=4)   # tear lines
		torn = old and s > 0
		if torn:
			for dx in (-0.03, 0.035):
				b.seg((0.2 * s + dx, -0.84, 1.08), (0.23 * s + dx * 1.5, -0.83, 1.15), 0.035, 0.02, fur, "head", sides=6)
			b.blob((0.11, 0.05, 0.05), (0.215 * s, -0.85, 1.12), dark, "head", segs=(8, 5))
		else:
			b.seg((0.2 * s, -0.84, 1.07), (0.23 * s, -0.83, 1.17), 0.08, 0.05, fur, "head", sides=8)
			b.blob((0.12, 0.05, 0.1), (0.225 * s, -0.85, 1.17), dark, "head", segs=(8, 5))
			b.blob((0.07, 0.03, 0.05), (0.225 * s, -0.875, 1.16), pale, "head", segs=(6, 4))
		broken = old and s > 0
		b.seg((0.05 * s, -1.24, 0.72), (0.05 * s, -1.245, 0.7 if broken else 0.655), 0.017, 0.008 if broken else 0.003, tooth, "jaw", sides=4)   # fangs
		b.seg((0.055 * s, -1.24, 0.79), (0.055 * s, -1.245, 0.76 if broken else 0.72), 0.018, 0.008 if broken else 0.003, tooth, "head", sides=4)
		for k in range(3):   # whisker spots
			b.blob((0.025, 0.02, 0.025), ((0.05 + 0.03 * k) * s, -1.29, 0.8 - 0.02 * k), dark, "head", segs=(4, 3))
		for k in range(2):   # faint stripes on the cheek
			_oblob(b, (0.028, 0.12, 0.02), (0.26 * s, -0.94 + 0.07 * k, 0.86), (0, 0.4, -1), (s, 0, 0), stripe, "head", segs=(5, 3))
	# mane framing the face
	for k in range(13):   # a fringe framing the face, from ear to ear under the chin
		a = math.radians(-200 + 220 * k / 12)
		out = Vector((math.cos(a), 0, math.sin(a)))
		root_ = Vector((0, -0.84, 0.88)) + Vector((out.x * 0.27, 0, out.z * 0.22))
		tip = root_ + (out * 0.45 + Vector((0, 0.9, 0))).normalized() * 0.17 * grow
		b.seg(tuple(root_), tuple(tip), 0.07 * grow, 0.015, mane if k % 2 else mane_l, "head", sides=5)
	if old:   # claw scars across the blind eye, a grizzled muzzle
		def face(x, z):
			k2 = 1 - (x / 0.28) ** 2 - ((z - 0.88) / 0.23) ** 2
			return Vector((x, -0.92 - 0.26 * math.sqrt(max(0.0, k2)) - 0.004, z))
		for k in range(3):
			line = [face(-0.04 - 0.045 * k - 0.04 * u, 1.07 - 0.2 * u) for u in (0, 0.25, 0.5, 0.75, 1.0)]
			for p, q in zip(line, line[1:]):
				_oblob(b, (0.022, (q - p).length * 1.4, 0.012), tuple((p + q) / 2), q - p, (0, -1, 0.2), scar, "head", segs=(5, 3))
		b.blob((0.3, 0.16, 0.12), (0, -1.2, 0.84), gray, "head", segs=(8, 5))
	# the tail: long and thin, a dark tuft at the tip
	pts = [(0, 0.84, 0.74), (0, 1.3, 0.5), (0, 1.74, 0.34), (0, 2.02, 0.32), (0, 2.16, 0.42)]
	for k, (p, q) in enumerate(zip(pts, pts[1:])):
		bone = CAT_TAIL[min(k, 2)]
		b.seg(p, q, 0.075, 0.065, fur, bone, sides=8)
		b.blob((0.14, 0.14, 0.14), q, fur, bone, segs=(8, 6))
	b.blob((0.2, 0.26, 0.2), (0, 2.2, 0.46), mane, "tail3", segs=(8, 6))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.56), "root")
		back_leg = y > 0
		b.blob((0.28, 0.42 if back_leg else 0.34, 0.46), (x * 1.08, y + (0.04 if back_leg else 0), 0.56), fur, name_, segs=(8, 6))
		b.seg((x, y, 0.46), (x, y + (0.05 if back_leg else 0.02), 0.18), 0.1, 0.085, fur, name_, sides=8)
		b.seg((x, y + (0.05 if back_leg else 0.02), 0.18), (x, y - 0.01, 0.06), 0.085, 0.085, fur, name_, sides=8)
		b.blob((0.2, 0.24, 0.11), (x, y - 0.04, 0.055), pale, name_, segs=(8, 5))
		for k in (-1, 0, 1):
			b.blob((0.06, 0.07, 0.055), (x + 0.06 * k, y - 0.15, 0.045), pale, name_, segs=(5, 4))
		_oblob(b, (0.045, 0.14, 0.02), (x * 1.5, y, 0.4), (0, 0.5, -1), (x, 0, 0), stripe, name_, segs=(5, 3))
	_scaled(b, 1.7 if old else 1.25)
	arm = b.build()

	def tail(t, amp, cycles=1.0, flick=0.0):
		return {"tail1": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))},
				"tail2": {"rot": (0, 0, amp * wave(t, cycles, -0.15))},
				"tail3": {"rot": (flick, 0, amp * 1.4 * wave(t, cycles, -0.3))}}

	def idle(t):   # crouched, watching over the grass; the tail tip twitches
		look = seq(t, [(0, 0), (0.3, 0), (0.4, 24), (0.6, 24), (0.7, 0)])
		return merge({"body": {"loc": (0, 0, 0.012 * wave(t, 2))}, "head": {"rot": (3 * wave(t, 1, 0.3), 0, look)}},
					 tail(t, 5, 1.0, 14 * wave(t, 3)))

	def walk(t):   # the stalk: head low, shoulders rolling, belly near the grass
		return merge(_quad_legs(wave(t), 20), tail(t, 6),
					 {"root": {"loc": (0, 0, -0.05 + 0.012 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 0)},
					  "head": {"rot": (-10, 0, -3 * wave(t))}})

	def run(t):
		f, k = 44 * wave(t), 44 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.85, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.85, 0, 0)},
					  "root": {"loc": (0, 0, 0.08 * max(0.0, wave(t, 1, 0.25))), "rot": (7 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-6 * wave(t, 1, 0.1), 0, 0)}}, tail(t, 4, 1.0, -10))

	def attack(t):   # springs from a crouch, rakes with a forepaw and bites
		crouch = seq(t, [(0, 0), (0.25, 1), (0.4, 0), (1, 0)])
		lunge = seq(t, [(0, 0), (0.25, -0.12), (0.45, 0.42), (0.6, 0.32), (1, 0)])
		rear = seq(t, [(0, 0), (0.25, -4), (0.42, 18), (0.6, 2), (1, 0)])
		paw = seq(t, [(0, 0), (0.3, 30), (0.42, 80), (0.55, -10), (1, 0)])
		jaw = seq(t, [(0, 0), (0.35, -38), (0.5, 4), (0.7, 0)])
		return merge({"root": {"loc": (0, lunge, -0.12 * crouch + 0.1 * max(0.0, rear) / 18), "rot": (rear, 0, 0)},
					  "leg_fl": {"rot": (paw, 0, 0)}, "leg_fr": {"rot": (paw * 0.3, 0, 0)},
					  "leg_bl": {"rot": (-rear, 0, 0)}, "leg_br": {"rot": (-rear, 0, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.3, 12), (0.5, -10), (1, 0)]), 0, 0)}, "jaw": {"rot": (jaw, 0, 0)}},
					 tail(t, 14, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.12 * k, 0.03 * k), "rot": (7 * k, 0, 0)}, "head": {"rot": (14 * k, 0, 12 * k)},
					  "jaw": {"rot": (-26 * k, 0, 0)}}, tail(t, 18 * k, 2))

	def death(t):
		roll = seq(t, [(0.15, 0), (0.6, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.15, 0), (0.6, -0.34)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (-12 * curl, 0, 14 * curl)}, "jaw": {"rot": (-12 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (30 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
					  "leg_bl": {"rot": (-26 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}},
					 {"tail1": {"rot": (-8 * curl, 0, 20 * curl)}, "tail2": {"rot": (0, 0, 24 * curl)}, "tail3": {"rot": (0, 0, 20 * curl)}})

	clip(arm, "idle", 3.2, idle, True)
	clip(arm, "walk", 1.0, walk, True)
	clip(arm, "run", 0.5, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


def build_grass_stalker():
	return _plains_cat("grass_stalker")


def build_tawnyjaw():
	return _plains_cat("tawnyjaw", old=True)


# ---------------------------------------------------------------- grass howler
# A lean spotted hunter of the herds: tall shoulders, a back that slopes down to short hind legs,
# a thick neck and big crushing jaws, round ears, a bristly dark mane along the spine, a short
# bushy tail. Its whooping call carries for miles over the grass.

def build_grass_howler(name="grass_howler"):
	import random
	rng = random.Random(3421)
	fur = material(f"{name}_fur", "b09a70", 0.95)
	fur_d = material(f"{name}_fur_dark", "8a7654", 0.95)
	pale = material(f"{name}_pale", "d0c09a", 0.95)
	spot = material(f"{name}_spot", "3a2a1c", 0.9)
	mane = material(f"{name}_mane", "2e2218", 0.95)
	face = material(f"{name}_face", "2a2018", 0.8)
	eye = material(f"{name}_eye", "d8a030", 0.25, emit=1.0)
	pupil = material(f"{name}_pupil", "0e0c0a", 0.2)
	tooth = material(f"{name}_tooth", "e8dcc0", 0.45)
	mouth = material(f"{name}_mouth", "6a2a24", 0.7)
	b = Builder(name)
	legs = {"leg_fl": (0.2, -0.5, 0.86), "leg_fr": (-0.2, -0.5, 0.86), "leg_bl": (0.19, 0.5, 0.6), "leg_br": (-0.19, 0.5, 0.6)}
	b.bone("root", (0, 0, 0.72))
	b.bone("body", (0, 0.0, 0.76), "root")
	b.bone("head", (0, -0.78, 1.04), "body")
	b.bone("jaw", (0, -0.98, 0.94), "head")
	b.bone("tail", (0, 0.66, 0.66), "body")

	b.blob((0.6, 1.4, 0.56), (0, 0.0, 0.78), fur, "body", rot=(-12, 0, 0), segs=(12, 8))         # the sloping barrel
	b.blob((0.7, 0.62, 0.66), (0, -0.46, 0.92), fur, "body", segs=(12, 8))                      # the big shoulders
	b.blob((0.54, 0.5, 0.5), (0, 0.46, 0.66), fur, "body", segs=(10, 7))                        # small haunches
	b.blob((0.44, 1.1, 0.22), (0, -0.02, 0.58), pale, "body", rot=(-10, 0, 0), segs=(10, 6))     # belly
	_spots(b, (0, 0.0, 0.8), (0.3, 0.7, 0.3), 30, spot, "body", rng, zmin=-0.45, size=0.14, rosette=False)
	for k in range(12):   # the bristly mane from the nape down the sloping back
		y = -0.66 + k * 0.1
		z = 1.2 - 0.035 * k - (0.012 * (k - 5) ** 2 if k > 5 else 0.0)
		root_ = Vector((0, y, z))
		b.seg(tuple(root_), tuple(root_ + Vector((0, 0.08, 0.16 - 0.008 * k))), 0.06, 0.008, mane, "body", sides=4)
	# the head: a thick neck, a broad skull, a short heavy muzzle, round ears
	b.seg((0, -0.5, 0.98), (0, -0.8, 1.04), 0.25, 0.22, fur, "head", sides=9)
	b.blob((0.44, 0.44, 0.4), (0, -0.84, 1.06), fur, "head", segs=(10, 8))
	b.blob((0.28, 0.2, 0.16), (0.0, -0.84, 0.88), fur_d, "head", segs=(8, 5))                   # heavy jaw muscles
	b.seg((0, -0.98, 1.06), (0, -1.22, 0.98), 0.14, 0.1, face, "head", sides=8)                  # dark muzzle
	b.blob((0.14, 0.09, 0.1), (0, -1.24, 1.0), material(f"{name}_nose", "141010", 0.4), "head", segs=(6, 4))
	b.blob((0.24, 0.2, 0.1), (0, -1.06, 0.87), face, "jaw", segs=(8, 5))                         # the lower jaw, heavy
	b.seg((0, -1.06, 0.9), (0, -1.2, 0.9), 0.08, 0.06, face, "jaw", sides=6)
	b.blob((0.18, 0.2, 0.05), (0, -1.1, 0.935), mouth, "jaw", segs=(8, 3))
	for s in (1, -1):
		b.blob((0.08, 0.06, 0.06), (0.12 * s, -1.02, 1.14), eye, "head", segs=(6, 4))
		b.blob((0.03, 0.02, 0.04), (0.125 * s, -1.05, 1.14), pupil, "head", segs=(4, 3))
		b.seg((0.16 * s, -0.8, 1.22), (0.2 * s, -0.78, 1.36), 0.1, 0.08, fur_d, "head", sides=8)   # round ears
		b.blob((0.16, 0.05, 0.16), (0.2 * s, -0.8, 1.36), fur_d, "head", segs=(8, 5))
		b.blob((0.1, 0.03, 0.1), (0.2 * s, -0.83, 1.35), face, "head", segs=(6, 4))
		for k in range(3):   # big teeth, top and bottom
			x = (0.03 + 0.03 * k) * s
			b.seg((x, -1.2 + 0.03 * k, 0.96), (x, -1.2 + 0.03 * k, 0.92), 0.016 if k == 0 else 0.012, 0.0, tooth, "head", sides=4)
			b.seg((x, -1.17 + 0.03 * k, 0.93), (x, -1.17 + 0.03 * k, 0.965), 0.014 if k == 0 else 0.011, 0.0, tooth, "jaw", sides=4)
	_spots(b, (0, -0.84, 1.06), (0.2, 0.2, 0.2), 6, spot, "head", rng, zmin=-0.2, ymax=0.6, size=0.07, rosette=False)
	# a short bushy tail, dark at the end
	b.seg((0, 0.64, 0.7), (0, 0.84, 0.52), 0.06, 0.07, fur, "tail", sides=6)
	b.blob((0.2, 0.22, 0.36), (0, 0.9, 0.38), mane, "tail", rot=(-20, 0, 0), segs=(7, 5))
	for name_, (x, y, hip) in legs.items():
		b.bone(name_, (x, y, hip), "root")
		front = y < 0
		b.blob((0.3, 0.36, 0.5 if front else 0.42), (x * 1.08, y, hip - 0.1), fur, name_, segs=(8, 6))
		knee = (x, y + (0.0 if front else 0.08), hip * 0.4)
		b.seg((x, y, hip - 0.12), knee, 0.115, 0.08, fur, name_, sides=7)
		b.seg(knee, (x, y - 0.02, 0.07), 0.075, 0.06, fur_d, name_, sides=7)
		b.blob((0.16, 0.2, 0.09), (x, y - 0.06, 0.045), face, name_, segs=(6, 4))
		_spots(b, (x, y, hip * 0.6), (0.08, 0.1, 0.2), 3, spot, name_, rng, zmin=-0.6, size=0.06, rosette=False)
	_scaled(b, 1.15)
	arm = b.build()

	def tail(t, amp, cycles=1.0):
		return {"tail": {"rot": (6 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))}}

	def idle(t):   # sniffs about, then lifts its head and whoops
		call = seq(t, [(0.5, 0), (0.58, 1), (0.8, 1), (0.88, 0)])
		whoop = call * (0.5 + 0.5 * wave(t, 6))
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))},
					  "head": {"rot": (-8 * (1 - call) * (0.5 + 0.5 * wave(t, 2)) + 30 * call, 0, 10 * wave(t, 0.5) * (1 - call))},
					  "jaw": {"rot": (-22 * whoop, 0, 0)}}, tail(t, 10))

	def walk(t):   # a rolling, loose-limbed lope, the head swinging low
		return merge(_quad_legs(wave(t), 24), tail(t, 8),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 0)},
					  "head": {"rot": (-6 + 4 * wave(t, 2), 0, 4 * wave(t))}})

	def run(t):
		f, k = 40 * wave(t), 40 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.07 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-8, 0, 0)}}, tail(t, 5))

	def attack(t):   # lunges and bites, then wrenches its head side to side
		lunge = seq(t, [(0, 0), (0.25, -0.1), (0.45, 0.36), (0.8, 0.2), (1, 0)])
		head = seq(t, [(0, 0), (0.25, 16), (0.45, -16), (0.8, -8), (1, 0)])
		jaw = seq(t, [(0, 0), (0.25, -40), (0.45, 2), (0.9, 0)])
		shake = seq(t, [(0.45, 0), (0.55, 1), (0.8, 1), (0.9, 0)]) * 18 * wave(t, 5)
		return merge({"root": {"loc": (0, lunge, 0.04 * max(0.0, lunge)), "rot": (seq(t, [(0, 0), (0.25, 6), (0.45, -6), (1, 0)]), 0, 0)},
					  "head": {"rot": (head, shake * 0.4, shake)}, "jaw": {"rot": (jaw, 0, 0)}}, tail(t, 14, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.14 * k, 0.03 * k), "rot": (8 * k, 0, 0)}, "head": {"rot": (16 * k, 0, 12 * k)},
					  "jaw": {"rot": (-26 * k, 0, 0)}}, tail(t, 18 * k, 2))

	def death(t):
		roll = seq(t, [(0.15, 0), (0.6, 86), (0.72, 80), (0.85, 88)])
		drop = seq(t, [(0.15, 0), (0.6, -0.32)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.2, 10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (-12 * curl, 0, 12 * curl)}, "jaw": {"rot": (-18 * curl, 0, 0)}},
					 {"leg_fl": {"rot": (28 * curl, 0, 0)}, "leg_fr": {"rot": (14 * curl, 0, 0)},
					  "leg_bl": {"rot": (-24 * curl, 0, 0)}, "leg_br": {"rot": (-12 * curl, 0, 0)}}, tail(t, 0))

	clip(arm, "idle", 3.4, idle, True)
	clip(arm, "walk", 0.8, walk, True)
	clip(arm, "run", 0.45, run, True)
	clip(arm, "attack", 0.8, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.1, death, False)
	return arm


# ---------------------------------------------------------------- thunderhoof and Old Thunderhoof
# A giant shaggy grazer of the plains: a towering hump over the shoulders, the head slung low under a
# mat of woolly hair, a beard, short black horns hooking up, a thin tufted tail; the forequarters are
# dark and woolly, the hindquarters short-haired and lighter. Old Thunderhoof, the herd-king, is built
# at 1.75: white streaks through his mane and beard, the left horn snapped off short, old scars.

def _bison(name, old=False):
	import random
	rng = random.Random(3433 if old else 3431)
	wool = material(f"{name}_wool", "3a2616" if old else "4a3020", 0.95)
	wool_l = material(f"{name}_wool_light", "5e4028" if old else "6e4c2e", 0.95)
	coat = material(f"{name}_coat", "6a4a2e" if old else "7a5634", 0.9)
	coat_d = material(f"{name}_coat_dark", "4a3220", 0.9)
	white = material(f"{name}_white", "c4bcae", 0.95)
	horn = material(f"{name}_horn", "1e1a16", 0.45)
	horn_l = material(f"{name}_horn_light", "4a4238", 0.5)
	hoof = material(f"{name}_hoof", "181410", 0.5)
	nose = material(f"{name}_nose", "1a1614", 0.4)
	eye = material(f"{name}_eye", "1a120c", 0.2)
	glint = material(f"{name}_glint", "f0e0b0", 0.2, emit=0.8)
	scar = material(f"{name}_scar", "8a6a5a", 0.8)
	gray = material(f"{name}_gray", "8a8078", 0.9)
	b = Builder(name)
	legs = {"leg_fl": (0.26, -0.52), "leg_fr": (-0.26, -0.52), "leg_bl": (0.25, 0.62), "leg_br": (-0.25, 0.62)}
	b.bone("root", (0, 0, 0.66))
	b.bone("body", (0, 0.0, 0.9), "root")
	b.bone("head", (0, -0.86, 0.94), "body")
	b.bone("tail", (0, 0.96, 1.02), "body")

	def streak(k):   # the old king's mane is shot through with white
		return white if old and k % 4 == 0 else None

	b.blob((0.84, 1.7, 0.78), (0, 0.18, 0.98), coat, "body", segs=(14, 10))                    # the barrel
	b.blob((0.72, 0.6, 0.66), (0, 0.72, 0.98), coat, "body", segs=(10, 8))                      # lean haunches
	b.blob((0.98, 1.0, 0.96), (0, -0.42, 1.1), wool, "body", segs=(14, 10))                     # woolly forequarters
	b.blob((0.74, 1.2, 0.62), (0, -0.2, 1.44), wool, "body", rot=(-14, 0, 0), segs=(12, 9))     # the hump, sloping away behind
	b.blob((0.6, 0.7, 0.3), (0, -0.44, 1.7), wool, "body", rot=(-20, 0, 0), segs=(10, 7))       # its crest over the shoulders
	white_ = [white] if old else []
	_lg_shag(b, (0, -0.3, 1.3), (0.5, 0.6, 0.5), 70, [wool_l, wool, wool] + white_, "body", rng, size=(0.2, 0.34, 0.08),
			 zmin=-0.5, ymax=0.2, flow=(0, 0.6, -1))
	for k in range(18):   # long shaggy hair hanging from the chest and the backs of the forelegs
		x = (k % 6 - 2.5) * 0.14
		row = k // 6
		ln = 0.5 - 0.1 * row
		m = streak(k + 1) or (wool, wool_l)[k % 2]
		_oblob(b, (0.16, 0.14, ln), (x, -0.8 + 0.16 * row, 0.86 - ln * 0.3), (0, 1, 0), (0, 0.2, 1), m, "body", segs=(6, 4))
	# the head: massive and low, buried in wool, a dark bare muzzle, a long beard
	b.seg((0, -0.66, 1.02), (0, -0.9, 0.94), 0.34, 0.3, wool, "head", sides=10)
	b.blob((0.6, 0.52, 0.6), (0, -1.0, 0.92), wool, "head", segs=(12, 9))
	b.blob((0.7, 0.5, 0.4), (0, -0.96, 1.2), wool_l, "head", segs=(12, 7))        # the woolly poll between the horns
	b.blob((0.36, 0.3, 0.34), (0, -1.24, 0.78), coat_d, "head", segs=(10, 7))                  # muzzle
	b.blob((0.28, 0.1, 0.18), (0, -1.38, 0.78), nose, "head", segs=(8, 5))
	for k in range(7):   # the beard
		x = (k - 3) * 0.07
		ln = 0.46 - 0.04 * abs(k - 3)
		m = streak(k) or (wool, wool_l)[k % 2]
		_oblob(b, (0.1, 0.1, ln), (x, -1.12 + 0.02 * abs(k - 3), 0.62 - ln * 0.3), (0, 1, 0), (0, 0.25, 1), m, "head", segs=(6, 4))
	for s in (1, -1):
		b.blob((0.07, 0.05, 0.06), (0.2 * s, -1.2, 0.98), eye, "head", segs=(6, 4))
		b.blob((0.025, 0.02, 0.025), (0.21 * s, -1.23, 0.99), glint, "head", segs=(4, 3))
		b.seg((0.28 * s, -0.94, 1.02), (0.42 * s, -0.94, 0.94), 0.07, 0.03, wool, "head", sides=5)   # ears in the wool
		broken = old and s > 0
		# the horns: short and thick, out sideways from the wool then hooking up and in
		pts = [(0.24 * s, -0.98, 1.16), (0.4 * s, -0.96, 1.2), (0.5 * s, -0.98, 1.32), (0.46 * s, -1.02, 1.46)]
		radii = [0.08, 0.065, 0.045, 0.004]
		if broken:
			pts, radii = pts[:3], [0.08, 0.065, 0.058]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(p, q, radii[k], radii[k + 1], horn if k else horn_l, "head", sides=8)
			b.blob((radii[k + 1] * 2.1,) * 3, q, horn, "head", segs=(6, 4))
		if broken:   # the snapped end: a jagged pale stump
			q = Vector(pts[-1])
			for k in range(4):
				a = k * math.pi / 2 + 0.4
				tip = q + Vector((0.03 * math.cos(a), 0.03 * math.sin(a), 0.03 + 0.03 * (k % 2)))
				b.seg(tuple(q), tuple(tip), 0.03, 0.0, horn_l, "head", sides=4)
	b.seg((0, 0.96, 1.06), (0, 1.06, 0.66), 0.045, 0.03, coat, "tail", sides=6)             # the thin tail and its tuft
	b.blob((0.14, 0.12, 0.3), (0, 1.08, 0.5), wool, "tail", segs=(7, 5))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.66), "root")
		front = y < 0
		b.blob((0.34, 0.4, 0.5), (x, y, 0.62), wool if front else coat, name_, segs=(8, 6))
		if front:   # woolly "trousers" on the forelegs
			for k in range(4):
				a = k * math.pi / 2 + 0.3
				_oblob(b, (0.14, 0.1, 0.36), (x + 0.12 * math.cos(a), y + 0.12 * math.sin(a), 0.44), (0, 1, 0), (math.cos(a), math.sin(a), 0.5), streak(k) or wool_l, name_, segs=(5, 4))
		b.seg((x, y, 0.48), (x, y + (0.0 if front else 0.04), 0.14), 0.11, 0.085, coat_d, name_, sides=7)
		b.seg((x, y - 0.01, 0.12), (x, y - 0.03, 0.0), 0.085, 0.1, hoof, name_, sides=7)
	if old:   # scars on the flank and a gray muzzle
		tree = _lg_skin_tree(b)
		_lg_scars(b, tree, [((2.0, 0.2, 1.2), (-1, 0, 0)), ((-2.0, 0.46, 1.1), (1, 0, 0))], (0, 0.4, -0.7), scar, "body", width=0.04, length=0.4, gap=0.12)
		b.blob((0.3, 0.2, 0.22), (0, -1.3, 0.8), gray, "head", segs=(8, 5))
	_scaled(b, 1.75 if old else 1.25)
	arm = b.build()

	def tail(t, amp, cycles=2.0):
		return {"tail": {"rot": (0, 0, amp * wave(t, cycles))}}

	def idle(t):   # grazes, then lifts its head and bellows
		graze = seq(t, [(0, 0), (0.12, 0), (0.25, 1), (0.6, 1), (0.72, 0)])
		snort = seq(t, [(0.8, 0), (0.84, 1), (0.92, 0)])
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))},
					  "head": {"rot": (-24 * graze + 3 * graze * wave(t, 7) + 10 * snort, 0, 8 * snort * wave(t, 6))}},
					 tail(t, 18, 3))

	def walk(t):
		return merge(_quad_legs(wave(t), 20), tail(t, 10),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "body": {"rot": (0, 3 * wave(t), 0)},
					  "head": {"rot": (-4 + 4 * wave(t, 2), 0, 4 * wave(t))}})

	def run(t):   # a thundering gallop
		f, k = 34 * wave(t), 34 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.07 * max(0.0, wave(t, 1, 0.25))), "rot": (5 * wave(t, 1, 0.1), 0, 0)},
					  "head": {"rot": (-10, 0, 0)}}, tail(t, 8))

	def attack(t):   # paws the ground, lowers its head and hooks up with the horns
		paw = seq(t, [(0, 0), (0.12, 30), (0.24, 0)])
		lunge = seq(t, [(0.2, 0), (0.35, -0.12), (0.52, 0.42), (0.64, 0.34), (1, 0)])
		head = seq(t, [(0, 0), (0.35, -28), (0.5, -30), (0.6, 16), (0.74, 8), (1, 0)])
		yaw = seq(t, [(0, 0), (0.5, -6), (0.6, 16), (1, 0)])
		return merge({"root": {"loc": (0, lunge, 0), "rot": (seq(t, [(0.2, 0), (0.35, -4), (0.6, 6), (1, 0)]), 0, 0)},
					  "head": {"rot": (head, 0, yaw)}, "leg_fr": {"rot": (paw, 0, 0)},
					  "leg_bl": {"rot": (seq(t, [(0.2, 0), (0.48, -24), (0.72, 0)]), 0, 0)},
					  "leg_br": {"rot": (seq(t, [(0.2, 0), (0.48, -20), (0.72, 0)]), 0, 0)}}, tail(t, 22, 3))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.02 * k), "rot": (6 * k, 4 * k, 0)},
					  "head": {"rot": (14 * k, 0, -12 * k)}}, tail(t, 22 * k, 3))

	def death(t):   # the knees buckle, then it rolls onto its side
		roll = seq(t, [(0.25, 0), (0.66, 84), (0.76, 78), (0.88, 86)])
		drop = seq(t, [(0.1, 0), (0.3, -0.14), (0.66, -0.36)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.25, -10), (0.5, 0)]), roll, 0)},
					  "head": {"rot": (seq(t, [(0, 0), (0.2, 14), (0.6, -8)]), 0, 14 * curl)}},
					 {"leg_fl": {"rot": (seq(t, [(0, 0), (0.25, 40), (0.6, 20)]), 0, 0)},
					  "leg_fr": {"rot": (seq(t, [(0, 0), (0.25, 40), (0.6, 10)]), 0, 0)},
					  "leg_bl": {"rot": (-20 * curl, 0, 0)}, "leg_br": {"rot": (-8 * curl, 0, 0)}})

	clip(arm, "idle", 4.0, idle, True)
	clip(arm, "walk", 1.2, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 1.1, attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.5, death, False)
	return arm


def build_thunderhoof():
	return _bison("thunderhoof")


def build_old_thunderhoof():
	return _bison("old_thunderhoof", old=True)


# ---------------------------------------------------------------- dirkhorn
# A stocky plains antelope armed with two long, straight, ringed horns swept back like a pair of
# dirks: grey-brown with a white belly, a black band along the flank, a black-and-white face mask,
# a short dark mane and a black tail switch. It lowers its head to charge, horns leveled.

def build_dirkhorn(name="dirkhorn"):
	coat = material(f"{name}_coat", "8a7e6c", 0.9)
	coat_d = material(f"{name}_coat_dark", "6a5e4e", 0.9)
	white = material(f"{name}_white", "e8e2d4", 0.9)
	black = material(f"{name}_black", "221e1a", 0.85)
	horn = material(f"{name}_horn", "2e2a26", 0.45)
	horn_r = material(f"{name}_horn_ring", "48423a", 0.6)
	hoof = material(f"{name}_hoof", "1a1612", 0.5)
	eye = material(f"{name}_eye", "120c08", 0.2)
	glint = material(f"{name}_glint", "f0e0b0", 0.2, emit=0.8)
	b = Builder(name)
	legs = {"leg_fl": (0.2, -0.5), "leg_fr": (-0.2, -0.5), "leg_bl": (0.2, 0.5), "leg_br": (-0.2, 0.5)}
	b.bone("root", (0, 0, 0.8))
	b.bone("body", (0, 0.0, 1.0), "root")
	b.bone("neck", (0, -0.6, 1.16), "body")
	b.bone("head", (0, -0.86, 1.46), "neck")
	b.bone("tail", (0, 0.72, 1.12), "body")

	b.blob((0.66, 1.5, 0.62), (0, 0.0, 1.06), coat, "body", segs=(14, 9))                      # the barrel, deep and stocky
	b.blob((0.66, 0.56, 0.66), (0, -0.46, 1.1), coat, "body", segs=(10, 8))                    # shoulders
	b.blob((0.64, 0.54, 0.6), (0, 0.48, 1.08), coat, "body", segs=(10, 8))                     # haunches
	b.blob((0.52, 1.2, 0.24), (0, 0.0, 0.82), white, "body", segs=(10, 6))                     # white belly
	for s in (1, -1):   # the black band along the flank, between the gray back and the white belly
		_oblob(b, (0.06, 1.3, 0.1), (0.3 * s, 0.0, 0.9), (0, 1, 0), (s, 0, -0.3), black, "body", segs=(10, 4))
	# the neck, thick for a charging beast, a short dark mane along its top
	b.seg((0, -0.46, 1.16), (0, -0.8, 1.44), 0.2, 0.15, coat, "neck", sides=9)
	b.seg((0, -0.5, 1.02), (0, -0.78, 1.32), 0.14, 0.1, white, "neck", sides=8)
	for k in range(6):
		u = k / 5
		root_ = Vector((0, -0.42 - 0.34 * u, 1.34 + 0.24 * u))
		b.seg(tuple(root_), tuple(root_ + Vector((0, 0.07, 0.12))), 0.05, 0.01, black, "neck", sides=4)
	# the head: long, a black-and-white mask
	b.blob((0.28, 0.36, 0.3), (0, -0.9, 1.5), coat, "head", segs=(10, 8))
	b.seg((0, -0.96, 1.5), (0, -1.28, 1.36), 0.13, 0.09, white, "head", sides=8)               # pale muzzle
	b.blob((0.16, 0.1, 0.12), (0, -1.3, 1.36), black, "head", segs=(8, 5))                     # the black nose
	b.seg((0, -0.94, 1.6), (0, -1.22, 1.44), 0.06, 0.04, black, "head", sides=6)               # a black blaze
	for s in (1, -1):
		b.seg((0.1 * s, -0.86, 1.56), (0.08 * s, -1.2, 1.38), 0.045, 0.03, black, "head", sides=5)   # black stripes through the eyes
		b.blob((0.06, 0.05, 0.05), (0.12 * s, -1.0, 1.52), eye, "head", segs=(6, 4))
		b.blob((0.02, 0.015, 0.02), (0.13 * s, -1.02, 1.53), glint, "head", segs=(4, 3))
		b.seg((0.12 * s, -0.84, 1.6), (0.28 * s, -0.78, 1.66), 0.05, 0.02, coat, "head", sides=5)   # ears
		# the horns: long, straight and ringed, swept back from the brow in a shallow V
		root_ = Vector((0.06 * s, -0.9, 1.64))
		d = Vector((0.12 * s, 0.62, 0.78)).normalized()
		length = 1.15
		b.seg(tuple(root_), tuple(root_ + d * length), 0.05, 0.006, horn, "head", sides=7)
		for k in range(6):   # the rings on the lower half
			c = root_ + d * (0.06 + 0.08 * k)
			b.seg(tuple(c), tuple(c + d * 0.025), 0.054 - 0.005 * k, 0.052 - 0.005 * k, horn_r, "head", sides=7)
	b.seg((0, 0.72, 1.16), (0, 0.9, 0.8), 0.04, 0.03, coat_d, "tail", sides=5)               # the tail and its black switch
	b.blob((0.1, 0.1, 0.34), (0, 0.94, 0.62), black, "tail", segs=(6, 5))
	for name_, (x, y) in legs.items():
		b.bone(name_, (x, y, 0.84), "root")
		front = y < 0
		b.blob((0.26, 0.34, 0.5), (x, y, 0.84), coat, name_, segs=(8, 6))
		knee = (x, y + (0.0 if front else 0.08), 0.42)
		b.seg((x, y, 0.72), knee, 0.08, 0.055, coat, name_, sides=6)
		b.seg(knee, (x, y - 0.01, 0.1), 0.05, 0.045, white if front else coat_d, name_, sides=6)
		b.blob((0.08, 0.08, 0.08), (x, y, 0.42), black, name_, segs=(6, 4))                  # black knee patches
		b.seg((x, y - 0.01, 0.1), (x, y - 0.03, 0.0), 0.05, 0.06, hoof, name_, sides=6)
	_scaled(b, 1.15)
	arm = b.build()

	def tail(t, amp, cycles=2.0):
		return {"tail": {"rot": (0, 0, amp * wave(t, cycles))}}

	def idle(t):   # grazes, then throws its head up to look about
		graze = seq(t, [(0, 0), (0.15, 0), (0.28, 1), (0.6, 1), (0.72, 0)])
		look = seq(t, [(0.74, 0), (0.8, 1), (0.92, 1), (0.98, 0)])
		return merge({"body": {"loc": (0, 0, 0.01 * wave(t, 2))},
					  "neck": {"rot": (-44 * graze, 0, 0)}, "head": {"rot": (-10 * graze + 3 * graze * wave(t, 8), 0, 20 * look)}},
					 tail(t, 20, 4))

	def walk(t):
		return merge(_quad_legs(wave(t), 24), tail(t, 12),
					 {"root": {"loc": (0, 0, 0.02 * abs(wave(t, 2)))}, "neck": {"rot": (3 * wave(t, 2), 0, 0)}})

	def run(t):
		f, k = 40 * wave(t), 40 * wave(t, 1, 0.5)
		return merge({"leg_fl": {"rot": (f, 0, 0)}, "leg_fr": {"rot": (f * 0.8, 0, 0)},
					  "leg_bl": {"rot": (k, 0, 0)}, "leg_br": {"rot": (k * 0.8, 0, 0)},
					  "root": {"loc": (0, 0, 0.08 * max(0.0, wave(t, 1, 0.25))), "rot": (6 * wave(t, 1, 0.1), 0, 0)},
					  "neck": {"rot": (-12, 0, 0)}}, tail(t, 6))

	def attack(t):   # drops its head to level the horns and drives them forward, then tosses up
		lower = seq(t, [(0, 0), (0.3, 1), (0.55, 1), (0.7, 0.3), (1, 0)])
		lunge = seq(t, [(0.2, 0), (0.32, -0.1), (0.5, 0.46), (0.66, 0.36), (1, 0)])
		toss = seq(t, [(0.5, 0), (0.62, 1), (0.8, 0)])
		return merge({"root": {"loc": (0, lunge, 0), "rot": (-6 * lower, 0, 0)},
					  "neck": {"rot": (-40 * lower + 20 * toss, 0, 0)}, "head": {"rot": (-40 * lower + 20 * toss, 0, 0)},
					  "leg_bl": {"rot": (seq(t, [(0.2, 0), (0.46, -26), (0.7, 0)]), 0, 0)},
					  "leg_br": {"rot": (seq(t, [(0.2, 0), (0.46, -22), (0.7, 0)]), 0, 0)}}, tail(t, 24, 3))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.03 * k), "rot": (6 * k, 4 * k, 0)},
					  "neck": {"rot": (16 * k, 0, -10 * k)}}, tail(t, 22 * k, 3))

	def death(t):
		roll = seq(t, [(0.25, 0), (0.66, 84), (0.76, 78), (0.88, 86)])
		drop = seq(t, [(0.1, 0), (0.3, -0.14), (0.66, -0.52)])
		curl = seq(t, [(0.3, 0), (0.85, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.25, -10), (0.5, 0)]), roll, 0)},
					  "neck": {"rot": (seq(t, [(0, 0), (0.2, 20), (0.7, -30)]), 0, 20 * curl)}},
					 {"leg_fl": {"rot": (seq(t, [(0, 0), (0.25, 44), (0.6, 24)]), 0, 0)},
					  "leg_fr": {"rot": (seq(t, [(0, 0), (0.25, 44), (0.6, 12)]), 0, 0)},
					  "leg_bl": {"rot": (-24 * curl, 0, 0)}, "leg_br": {"rot": (-10 * curl, 0, 0)}})

	clip(arm, "idle", 3.6, idle, True)
	clip(arm, "walk", 0.9, walk, True)
	clip(arm, "run", 0.5, run, True)
	clip(arm, "attack", 1.0, attack, False)
	clip(arm, "hit", 0.4, hit, False)
	clip(arm, "death", 1.3, death, False)
	return arm


# ---------------------------------------------------------------- the hoofborn (horse-folk of the plains)
# A horse's body with a rider's torso rising from its shoulders: a chestnut coat with pale socks,
# a dark mane of braids, leather armor sewn with plates of bone, a painted saddle-cloth over the
# back. Own rig: four legs of two bones each walk and gallop; the torso fights. Weapons are built
# in: the rider's spear, the archer's bow, Khan Oruk's curved blade (and his horned fur hat and the
# horsetail standard on his back). Riders are built at 0.92, the khan at 1.12.

HOOFBORN_LEGS = {"fl": (0.18, -0.52, 1.06), "fr": (-0.18, -0.52, 1.06), "bl": (0.19, 0.64, 1.1), "br": (-0.19, 0.64, 1.1)}


def hoofborn_materials(kind):
	khan = kind == "khan"
	return _rmats(f"hoofborn_{kind}", {
		"coat": ("7a3e1c" if khan else "8e4a22", 0.85), "coat_d": ("5a2c12" if khan else "6a3418", 0.85),
		"coat_l": ("a8643a" if khan else "b06a3a", 0.85), "sock": ("e8e0d0", 0.85), "hoof": ("2a2018", 0.5),
		"hair": ("1e140e" if khan else "2e1a10", 0.9), "hair_l": ("3a2416" if khan else "4a2c1a", 0.9),
		"skin": ("b88058", 0.7), "skin_d": ("8a5a3a", 0.75), "lip": ("8a4e3a", 0.7),
		"eye": ("1a120c", 0.2), "white": ("f0ece0", 0.4), "brow": ("2a1a10", 0.9),
		"leather": ("5a3a22", 0.85), "leather_d": ("3a2414", 0.85), "bone": ("e6dcc0", 0.6), "bone_d": ("b0a282", 0.7),
		"cloth": ("9a2a1e" if khan else "a8742a", 0.9), "cloth_d": ("5e1a12" if khan else "6a4418", 0.9),
		"trim": ("e0b040" if khan else "3a5a6a", 0.8), "wood": ("6a4a2e", 0.85), "iron": ("8a9090", 0.35),
		"steel": ("c8d0d4", 0.25), "gold": ("d8a83a", 0.35), "fur": ("4a3424", 0.95), "fur_l": ("6e5238", 0.95),
		"horn": ("e8dcc0", 0.5), "horn_d": ("5a4e40", 0.55), "white_hair": ("e8e4dc", 0.9),
		"feather": ("2a2622", 0.8), "string": ("d8ccb0", 0.8),
	})


def _hoofborn(name, kind="rider"):
	import random
	rng = random.Random({"rider": 3441, "archer": 3443, "khan": 3447}[kind])
	khan = kind == "khan"
	m = hoofborn_materials(kind)
	b = Builder(name)
	b.bone("root", (0, 0, 1.0))
	b.bone("body", (0, 0.05, 1.15), "root")
	b.bone("waist", (0, -0.62, 1.48), "body")
	b.bone("chest", (0, -0.64, 1.78), "waist")
	b.bone("head", (0, -0.68, 2.1), "chest")
	b.bone("tail", (0, 0.9, 1.3), "body")
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		b.bone(f"upper_{side}", (0.3 * s, -0.66, 2.0), "chest")
		b.bone(f"fore_{side}", (0.36 * s, -0.66, 1.72), f"upper_{side}")
	b.bone("grip", (-0.37, -0.8, 1.5), "fore_r")      # the weapon hand's wrist: spear, blade
	b.bone("bow", (0.37, -0.8, 1.5), "fore_l")        # the bow hand's wrist, so the bow stays upright as the arm rises

	# ---- the horse
	b.blob((0.66, 1.46, 0.66), (0, 0.08, 1.16), m["coat"], "body", segs=(14, 10))
	b.blob((0.64, 0.62, 0.74), (0, -0.46, 1.22), m["coat"], "body", segs=(12, 9))             # the breast
	b.blob((0.66, 0.66, 0.68), (0, 0.62, 1.2), m["coat"], "body", segs=(12, 9))               # the quarters
	b.blob((0.5, 1.1, 0.2), (0, 0.06, 0.88), m["coat_l"], "body", segs=(10, 6))               # the belly
	start = len(b.parts)
	# the saddle-cloth: a painted blanket over the back with a trimmed edge, a girth strap
	for s in (1, -1):
		_slab(b, [(0.0, -0.3, 1.52), (0.0, 0.46, 1.52), (0.3 * s, 0.46, 1.36), (0.36 * s, 0.4, 1.1), (0.36 * s, -0.24, 1.1), (0.3 * s, -0.3, 1.36)], 0.03, m["cloth"])
		_slab(b, [(0.36 * s, -0.24, 1.12), (0.36 * s, 0.4, 1.12), (0.37 * s, 0.4, 1.06), (0.37 * s, -0.24, 1.06)], 0.035, m["trim"])
		for k in range(3):   # painted diamonds
			y = -0.12 + 0.18 * k
			_slab(b, [(0.345 * s, y, 1.3), (0.35 * s, y + 0.06, 1.22), (0.345 * s, y, 1.14), (0.34 * s, y - 0.06, 1.22)], 0.035, m["cloth_d"])
	_on_bone(b, start, "body")
	start = len(b.parts)
	_wrap(b, (0, -0.2, 1.14), (0.35, 0.36), 0.08, 0.02, m["leather_d"], rot=(90, 0, 90), sides=16)
	_on_bone(b, start, "body")
	# the tail: a long dark fall of hair, braided at the root
	for k in range(5):   # strands falling from the dock, splayed a little
		x = (k - 2) * 0.035
		pts = [Vector((x * 0.5, 0.9, 1.32)), Vector((x, 1.06, 1.14)), Vector((x * 1.6, 1.12, 0.86)), Vector((x * 2.2, 1.12, 0.56))]
		_chain(b, pts, 0.07, 0.025, m["hair"] if k % 2 == 0 else m["hair_l"], "tail", sides=6)
	for k in range(3):
		b.seg((0, 0.96 + 0.05 * k, 1.28 - 0.05 * k), (0, 1.0 + 0.05 * k, 1.24 - 0.05 * k), 0.07, 0.07, m["trim"] if k == 1 else m["leather"], "tail", sides=6)
	for leg, (x, y, hip) in HOOFBORN_LEGS.items():
		front = leg[0] == "f"
		up, low = f"leg_{leg}", f"shin_{leg}"
		knee = (x, y + (0.0 if front else 0.1), 0.52)
		b.bone(up, (x, y, hip), "root")
		b.bone(low, knee, up)
		b.blob((0.24, 0.34 if front else 0.44, 0.5), (x * 1.08, y + (0.0 if front else 0.02), hip - 0.16), m["coat"], up, segs=(8, 6))
		b.seg((x, y, hip - 0.2), knee, 0.1, 0.07, m["coat"], up, sides=7)
		b.blob((0.13, 0.14, 0.14), knee, m["coat_d"], low, segs=(6, 5))
		sock = leg in ("fl", "br") or khan
		b.seg(knee, (x, y - 0.02, 0.1), 0.06, 0.055, m["sock"] if sock else m["coat_d"], low, sides=7)
		b.blob((0.13, 0.13, 0.1), (x, y - 0.02, 0.13), m["sock"] if sock else m["coat_d"], low, segs=(6, 4))   # feathered fetlock
		b.seg((x, y - 0.02, 0.1), (x, y - 0.04, 0.0), 0.07, 0.085, m["hoof"], low, sides=7)
		if khan:   # tassels bound under the knees
			b.seg((x, knee[1], 0.46), (x, knee[1], 0.42), 0.075, 0.075, m["cloth"], low, sides=7)

	# ---- the rider's torso, rising from the breast
	b.blob((0.46, 0.4, 0.34), (0, -0.62, 1.44), m["coat"], "waist", segs=(10, 7))            # where hide meets skin
	b.blob((0.42, 0.34, 0.3), (0, -0.63, 1.54), m["skin"], "waist", segs=(10, 7))
	b.blob((0.46, 0.36, 0.36), (0, -0.64, 1.66), m["leather"], "waist", segs=(10, 7))         # the leather jerkin's skirt
	start = len(b.parts)
	_wrap(b, (0, -0.64, 1.56), (0.24, 0.19), 0.08, 0.025, m["leather_d"], sides=14)            # the belt
	_on_bone(b, start, "waist")
	b.blob((0.07, 0.04, 0.07), (0, -0.84, 1.56), m["gold"] if khan else m["bone"], "waist", segs=(6, 4))
	for k in range(7):   # the hanging skirt of leather strips over the horse's breast
		a = math.radians(200 + 140 * k / 6)
		c = Vector((0.26 * math.cos(a), -0.64 + 0.2 * math.sin(a), 1.44))
		_oblob(b, (0.1, 0.03, 0.22), tuple(c), (0, 0, -1), (math.cos(a), math.sin(a), 0), m["leather"] if k % 2 else m["leather_d"], "waist", segs=(5, 3))
	b.blob((0.56, 0.36, 0.44) if not khan else (0.62, 0.4, 0.48), (0, -0.66, 1.88), m["leather"], "chest", segs=(12, 8))   # the jerkin
	b.blob((0.24, 0.1, 0.14), (0, -0.83, 2.02), m["skin"], "chest", segs=(8, 5))              # skin at the open collar
	# plates of bone sewn over the chest, and a necklace of teeth
	for row in range(2):
		for k in range(3 if row == 0 else 2):
			x = (k - (1 if row == 0 else 0.5)) * 0.14
			_oblob(b, (0.12, 0.14, 0.03), (x, -0.84 + 0.02 * row, 1.9 - 0.14 * row), (0, 0.2, -1), (0, -1, 0.1), m["bone"] if (k + row) % 2 else m["bone_d"], "chest", segs=(6, 3))
	for k in range(9):
		a = math.radians(210 + 120 * k / 8)
		c = Vector((0.16 * math.cos(a), -0.66 + 0.2 * math.sin(a), 2.02 - 0.03 * math.sin(a * 2)))
		b.seg(tuple(c), tuple(c + Vector((0, -0.01, -0.07))), 0.018, 0.0, m["horn"], "chest", sides=4)
	b.seg((0, -0.66, 2.0), (0, -0.68, 2.14), 0.09, 0.08, m["skin"], "head", sides=8)           # the neck
	# the head: a strong face, dark braided hair
	b.blob((0.26, 0.28, 0.32), (0, -0.7, 2.26), m["skin"], "head", segs=(10, 8))
	b.blob((0.16, 0.08, 0.14), (0, -0.82, 2.2), m["skin"], "head", segs=(8, 5))               # jaw and cheeks
	b.seg((0, -0.83, 2.28), (0, -0.87, 2.22), 0.03, 0.035, m["skin_d"], "head", sides=5)      # the nose
	b.blob((0.08, 0.02, 0.02), (0, -0.84, 2.17), m["lip"], "head", segs=(6, 3))
	for s in (1, -1):
		b.blob((0.05, 0.03, 0.03), (0.06 * s, -0.82, 2.28), m["white"], "head", segs=(6, 3))
		b.blob((0.025, 0.02, 0.025), (0.06 * s, -0.835, 2.28), m["eye"], "head", segs=(4, 3))
		b.blob((0.08, 0.03, 0.025), (0.06 * s, -0.83, 2.32), m["brow"], "head", rot=(0, 10 * s, 0), segs=(5, 3))
		b.blob((0.04, 0.05, 0.07), (0.13 * s, -0.7, 2.26), m["skin_d"], "head", segs=(5, 4))   # ears
	b.blob((0.3, 0.32, 0.2), (0, -0.68, 2.38), m["hair"], "head", segs=(10, 6))               # the hair
	b.blob((0.28, 0.2, 0.3), (0, -0.6, 2.28), m["hair"], "head", segs=(10, 7))
	for s in (1, -1):   # two long braids down the back
		pts = [Vector((0.09 * s, -0.56, 2.26)), Vector((0.12 * s, -0.5, 2.06)), Vector((0.12 * s, -0.5, 1.84)), Vector((0.11 * s, -0.52, 1.66))]
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			bone = "head" if k == 0 else "chest"
			for j in range(3):
				c = p + (q - p) * (j + 0.5) / 3
				b.blob((0.06, 0.06, 0.09), tuple(c), m["hair"] if j % 2 else m["hair_l"], bone, segs=(6, 4))
		b.blob((0.05, 0.05, 0.05), tuple(pts[-1]), m["trim"], "chest", segs=(5, 4))
		b.seg(tuple(pts[-1]), tuple(pts[-1] + Vector((0, 0, -0.12))), 0.04, 0.005, m["hair"], "chest", sides=5)
	if khan:   # a drooping mustache and a braided beard
		for s in (1, -1):
			b.seg((0.02 * s, -0.85, 2.2), (0.08 * s, -0.84, 2.14), 0.018, 0.012, m["hair"], "head", sides=4)
			b.seg((0.08 * s, -0.84, 2.14), (0.08 * s, -0.83, 2.04), 0.012, 0.004, m["hair"], "head", sides=4)
		b.seg((0, -0.83, 2.12), (0, -0.84, 1.98), 0.03, 0.012, m["hair"], "head", sides=5)
	# the arms, with bone pauldrons and leather bracers
	for s in (1, -1):
		side = "l" if s > 0 else "r"
		up, fore = f"upper_{side}", f"fore_{side}"
		b.blob((0.18, 0.18, 0.18), (0.3 * s, -0.66, 2.0), m["skin"], up, segs=(8, 6))
		b.seg((0.3 * s, -0.66, 2.0), (0.36 * s, -0.66, 1.72), 0.075, 0.06, m["skin"], up, sides=7)
		_oblob(b, (0.24, 0.26, 0.06), (0.33 * s, -0.66, 2.06), (0, 1, 0), (0.6 * s, 0, 1), m["bone"], up, segs=(8, 4))   # pauldron
		_oblob(b, (0.18, 0.2, 0.05), (0.37 * s, -0.66, 1.98), (0, 1, 0), (0.9 * s, 0, 0.6), m["bone_d"], up, segs=(8, 4))
		b.seg((0.36 * s, -0.66, 1.72), (0.37 * s, -0.8, 1.5), 0.06, 0.05, m["skin"], fore, sides=7)
		b.seg((0.362 * s, -0.7, 1.64), (0.37 * s, -0.78, 1.52), 0.068, 0.06, m["leather_d"], fore, sides=7)
		b.blob((0.09, 0.1, 0.1), (0.37 * s, -0.81, 1.47), m["skin"], fore, segs=(6, 5))          # the fist
	if kind == "rider":   # the spear: an ash shaft, a long iron head, a tuft of horsehair below it
		d = Vector((0, -0.34, 0.94)).normalized()
		h = Vector((-0.37, -0.81, 1.47))
		b.seg(tuple(h - d * 0.9), tuple(h + d * 1.44), 0.025, 0.022, m["wood"], "grip", sides=6)
		tip = h + d * 1.44
		_oblob(b, (0.1, 0.4, 0.03), tuple(tip + d * 0.18), tuple(d), (1, 0, 0), m["iron"], "grip", segs=(6, 4))
		b.seg(tuple(tip - d * 0.04), tuple(tip + d * 0.02), 0.035, 0.035, m["leather_d"], "grip", sides=6)
		for k in range(5):
			a = 2 * math.pi * k / 5
			o = Vector((0.03 * math.cos(a), 0.03 * math.sin(a), 0))
			b.seg(tuple(tip - d * 0.04 + o), tuple(tip - d * 0.3 + o * 2.4 + Vector((0, 0.03, 0))), 0.022, 0.006, m["cloth"] if k % 2 else m["hair"], "grip", sides=4)
		b.seg(tuple(h - d * 0.9), tuple(h - d * 0.98), 0.024, 0.0, m["iron"], "grip", sides=5)
		# a round hide shield on the left forearm
		c = Vector((0.46, -0.76, 1.6))
		_oblob(b, (0.46, 0.46, 0.06), tuple(c), (0, 0, 1), (1, -0.25, 0), m["leather"], "fore_l", segs=(12, 4))
		start = len(b.parts)
		_ring(b, tuple(c + Vector((0.03, -0.008, 0))), (0.22, 0.22), (90 - 14, 0), 0.02, m["bone_d"], sides=14)
		for p in b.parts[start:]:
			p.data.transform(Matrix.Translation(c) @ Matrix.Rotation(math.radians(0), 4, "Z") @ Matrix.Translation(-c))
		_on_bone(b, start, "fore_l")
		b.blob((0.1, 0.06, 0.1), tuple(c + Vector((0.04, -0.01, 0))), m["bone"], "fore_l", segs=(6, 4))
	elif kind == "archer":   # a horn-and-sinew recurve bow in the left fist, a quiver on the back
		c = Vector((0.37, -0.84, 1.47))
		pts = []
		for k in range(9):
			u = (k - 4) / 4
			z = 0.62 * u
			y = -0.1 * (1 - u * u) + 0.08 * abs(u) ** 3   # bellied away, the tips recurving
			pts.append(c + Vector((0, y - 0.02, z)))
		for k, (p, q) in enumerate(zip(pts, pts[1:])):
			b.seg(tuple(p), tuple(q), 0.03 if 2 <= k <= 5 else 0.022, 0.03 if 2 <= k <= 5 else 0.018, m["horn_d"] if k in (3, 4) else m["wood"], "bow", sides=6)
		b.seg(tuple(pts[0]), tuple(pts[-1]), 0.006, 0.006, m["string"], "bow", sides=3)
		# the quiver slung across the back, arrows with dark fletching
		q0, q1 = Vector((-0.2, -0.44, 1.66)), Vector((0.14, -0.4, 2.16))
		b.seg(tuple(q0), tuple(q1), 0.08, 0.09, m["leather"], "chest", sides=8)
		for k in range(5):
			o = Vector(((k - 2) * 0.03, 0.01 * (k % 2), 0))
			b.seg(tuple(q1 + o), tuple(q1 + o + (q1 - q0).normalized() * 0.16), 0.01, 0.01, m["wood"], "chest", sides=3)
			_oblob(b, (0.05, 0.1, 0.01), tuple(q1 + o + (q1 - q0).normalized() * 0.14), tuple(q1 - q0), (0, 1, 0), m["feather"], "chest", segs=(4, 3))
		b.seg((-0.22, -0.84, 1.84), (0.3, -0.84, 2.0), 0.02, 0.02, m["leather_d"], "chest", sides=4)   # the strap across the chest
	else:   # the khan: a curved blade in his fist, a horned fur hat, the horsetail standard on his back
		h = Vector((-0.37, -0.81, 1.47))
		b.seg(tuple(h + Vector((0, 0, -0.12))), tuple(h + Vector((0, 0, 0.12))), 0.03, 0.03, m["leather_d"], "grip", sides=6)
		b.blob((0.07, 0.07, 0.07), tuple(h + Vector((0, 0, -0.14))), m["gold"], "grip", segs=(6, 5))
		b.seg(tuple(h + Vector((0, 0.1, 0.13))), tuple(h + Vector((0, -0.1, 0.13))), 0.024, 0.024, m["gold"], "grip", sides=6)
		pts = []
		for k in range(9):
			u = k / 8
			pts.append((h + Vector((0, -0.34 * u * u, 0.15 + 0.92 * u)), 0.05 + 0.025 * math.sin(math.pi * u * 0.85)))
		for (p, w), (q, w2) in zip(pts, pts[1:]):
			n = Vector((0, -1, 0))
			_slab(b, [tuple(p - n * w * 0.3), tuple(p + n * w), tuple(q + n * w2), tuple(q - n * w2 * 0.3)], 0.02, m["steel"])
		tip, w = pts[-1]
		_slab(b, [tuple(tip + Vector((0, 0.014, 0))), tuple(tip + Vector((0, -w, 0))), tuple(tip + Vector((0, -0.14, 0.1)))], 0.018, m["steel"])
		_on_bone(b, len(b.parts) - 9, "grip")
		# the hat: a crown of dark fur, a pointed felt top with a gold boss, a pair of curving horns
		b.blob((0.4, 0.4, 0.2), (0, -0.7, 2.4), m["fur"], "head", segs=(12, 7))
		b.seg((0, -0.7, 2.44), (0, -0.72, 2.66), 0.15, 0.04, m["cloth"], "head", sides=10)
		b.blob((0.06, 0.06, 0.06), (0, -0.72, 2.68), m["gold"], "head", segs=(6, 5))
		for s in (1, -1):
			hp = [Vector((0.16 * s, -0.74, 2.44)), Vector((0.3 * s, -0.74, 2.5)), Vector((0.38 * s, -0.76, 2.64)), Vector((0.36 * s, -0.82, 2.78))]
			rr = [0.05, 0.04, 0.025, 0.004]
			for k, (p, q) in enumerate(zip(hp, hp[1:])):
				b.seg(tuple(p), tuple(q), rr[k], rr[k + 1], m["horn"] if k < 2 else m["horn_d"], "head", sides=6)
		_lg_shag(b, (0, -0.7, 2.4), (0.2, 0.2, 0.1), 16, [m["fur"], m["fur_l"]], "head", rng, size=(0.08, 0.12, 0.04), zmin=-0.3, flow=(0, 0, -1))
		# the standard: a pole up his back, a gilt crescent atop it, horsetails hanging from a ring beneath
		base, top = Vector((0.14, -0.44, 1.5)), Vector((0.2, -0.38, 3.2))
		b.seg(tuple(base), tuple(top), 0.03, 0.026, m["wood"], "chest", sides=6)
		b.seg((0.13, -0.47, 1.84), (-0.14, -0.84, 1.96), 0.02, 0.02, m["leather_d"], "chest", sides=4)   # its strap
		for k in range(8):
			a = math.pi * k / 7
			p = top + Vector((0.14 * math.cos(a), 0, 0.14 * math.sin(a) + 0.02))
			q = top + Vector((0.14 * math.cos(a + math.pi / 7), 0, 0.14 * math.sin(a + math.pi / 7) + 0.02))
			if k < 7:
				b.seg(tuple(p), tuple(q), 0.02, 0.02, m["gold"], "chest", sides=5)
		b.seg(tuple(top), tuple(top + Vector((0, 0, 0.3))), 0.02, 0.0, m["gold"], "chest", sides=5)
		ring_c = top + Vector((0, 0, -0.1))
		b.seg(tuple(ring_c + Vector((0, 0, -0.02))), tuple(ring_c + Vector((0, 0, 0.02))), 0.11, 0.11, m["gold"], "chest", sides=10)
		for k in range(9):   # the horsetails
			a = 2 * math.pi * k / 9
			root_ = ring_c + Vector((0.09 * math.cos(a), 0.09 * math.sin(a), -0.02))
			ln = rng.uniform(0.66, 0.9)
			hair = (m["hair"], m["white_hair"], m["hair_l"])[k % 3]
			_oblob(b, (0.07, 0.07, ln), tuple(root_ + Vector((0.05 * math.cos(a), 0.05 * math.sin(a), -ln * 0.46))), (0, 1, 0), (0, 0, 1), hair, "chest", segs=(6, 5))
	pivot = Vector((0, -0.68, 2.12))   # a bolder head, nearer the KayKit folk's proportions
	for part in b.parts:
		if part.vertex_groups[0].name == "head":
			part.data.transform(Matrix.Translation(pivot) @ Matrix.Scale(1.22, 4) @ Matrix.Translation(-pivot))
	_scaled(b, 1.12 if khan else 0.92)
	arm = b.build()

	def legs_walk(t, amp, bend, phases, lift=0.0):
		out = {}
		for leg, ph in phases.items():
			a = wave(t, 1, ph)
			swing = max(0.0, math.cos(2 * math.pi * (t + ph)))   # the leg coming forward bends at the knee
			front = leg[0] == "f"
			out[f"leg_{leg}"] = {"rot": (amp * a + (lift * swing if front else -lift * 0.4 * swing), 0, 0)}
			out[f"shin_{leg}"] = {"rot": (-bend * swing if front else bend * 0.7 * swing, 0, 0)}
		return out

	WALK = {"bl": 0.0, "fl": 0.25, "br": 0.5, "fr": 0.75}
	GALLOP = {"bl": 0.0, "br": 0.1, "fl": 0.45, "fr": 0.55}

	def arms_rest(t, sway=0.0):
		pose = {"upper_l": {"rot": (6 + 4 * sway, 0, 0)}, "upper_r": {"rot": (6 - 4 * sway, 0, 0)},
				"fore_l": {"rot": (10, 0, 0)}, "fore_r": {"rot": (10, 0, 0)}}
		if kind == "archer":   # the bow held low at the left side
			pose["fore_l"] = {"rot": (20, 0, 0)}
		return pose

	def tail(t, amp, cycles=1.0):
		return {"tail": {"rot": (4 * wave(t, cycles, 0.2), 0, amp * wave(t, cycles))}}

	def idle(t):   # stamps a forehoof, looks about, the torso breathing
		stamp = seq(t, [(0.6, 0), (0.65, 1), (0.7, 0), (0.75, 1), (0.8, 0)])
		look = seq(t, [(0.1, 0), (0.2, 24), (0.4, 24), (0.5, -18), (0.62, -18), (0.72, 0)])
		return merge({"body": {"loc": (0, 0, 0.008 * wave(t, 2))}, "chest": {"rot": (1.5 * wave(t, 2), 0, look * 0.3)},
					  "head": {"rot": (0, 0, look * 0.7)}, "leg_fr": {"rot": (26 * stamp, 0, 0)}, "shin_fr": {"rot": (-50 * stamp, 0, 0)}},
					 arms_rest(t, wave(t, 2)), tail(t, 10, 2))

	def walk(t):
		return merge(legs_walk(t, 20, 46, WALK, 10), tail(t, 8),
					 {"root": {"loc": (0, 0, 0.018 * wave(t, 2))}, "body": {"rot": (0, 2 * wave(t), 0)},
					  "chest": {"rot": (0, 0, 3 * wave(t))}}, arms_rest(t, wave(t)))

	def run(t):   # a gallop, the rider leaning into it
		return merge(legs_walk(t, 40, 70, GALLOP, 14), tail(t, 4),
					 {"root": {"loc": (0, 0, 0.1 * max(0.0, wave(t, 1, 0.3))), "rot": (7 * wave(t, 1, 0.05), 0, 0)},
					  "waist": {"rot": (-14 - 5 * wave(t, 1, 0.05), 0, 0)}, "head": {"rot": (10, 0, 0)}},
					 {"tail": {"rot": (30, 0, 0)}}, arms_rest(t))

	def attack(t):
		if kind == "rider":   # draws the spear back and drives it forward, rearing a little into the thrust
			draw = seq(t, [(0, 0), (0.3, 1), (0.42, 0), (1, 0)])
			thrust = seq(t, [(0.3, 0), (0.45, 1), (0.65, 1), (1, 0)])
			lean = -18 * thrust + 10 * draw
			return merge({"waist": {"rot": (lean, 0, 14 * draw - 8 * thrust)},
						  "upper_r": {"rot": (30 * draw + 70 * thrust, 0, 0)}, "fore_r": {"rot": (60 * draw + 20 * thrust, 0, 0)},
						  "grip": {"rot": (-40 * draw - 150 * thrust, 0, 0)},
						  "upper_l": {"rot": (30 * draw + 20 * thrust, -10 * thrust, 0)},
						  "root": {"loc": (0, 0.2 * thrust, 0), "rot": (6 * draw - 3 * thrust, 0, 0)},
						  "leg_fl": {"rot": (20 * draw, 0, 0)}, "leg_fr": {"rot": (14 * draw, 0, 0)}}, tail(t, 12, 2), {"head": {"rot": (-lean * 0.5, 0, 0)}})
		if kind == "archer":   # raises the bow, draws to the cheek, looses
			raise_ = seq(t, [(0, 0), (0.25, 1), (0.8, 1), (1, 0)])
			draw = seq(t, [(0.2, 0), (0.5, 1), (0.6, 1), (0.64, 0.2), (0.8, 0.2), (1, 0)])
			return merge({"waist": {"rot": (0, 0, 20 * raise_)}, "head": {"rot": (0, 0, -24 * raise_)},
						  "upper_l": {"rot": (84 * raise_, 0, 16 * raise_)}, "fore_l": {"rot": (-6 * raise_, 0, 0)},
						  "bow": {"rot": (-78 * raise_, 0, 0)},
						  "upper_r": {"rot": (84 * raise_, 0, 6 * raise_ - 46 * draw)},
						  "fore_r": {"rot": (0, 0, 20 * raise_ + 110 * draw)}}, tail(t, 8, 2))
		# the khan: raises the blade overhead and cuts down and across, the horse half rearing
		up = seq(t, [(0, 0), (0.35, 1), (0.5, 0), (1, 0)])
		cut = seq(t, [(0.35, 0), (0.52, 1), (0.7, 1), (1, 0)])
		rear = seq(t, [(0, 0), (0.3, 1), (0.55, 0)])
		return merge({"root": {"rot": (10 * rear, 0, 0), "loc": (0, 0.24 * cut, 0.12 * rear)},
					  "leg_fl": {"rot": (50 * rear, 0, 0)}, "leg_fr": {"rot": (40 * rear, 0, 0)},
					  "shin_fl": {"rot": (-70 * rear, 0, 0)}, "shin_fr": {"rot": (-60 * rear, 0, 0)},
					  "waist": {"rot": (8 * up - 20 * cut, 0, 20 * up - 24 * cut)},
					  "upper_r": {"rot": (160 * up + 60 * cut, -20 * up, 0)}, "fore_r": {"rot": (30 * up + 10 * cut, 0, 0)},
					  "grip": {"rot": (20 * up - 60 * cut, 0, 0)},
					  "upper_l": {"rot": (30 * up, 30 * up, 0)}}, tail(t, 14, 2))

	def hit(t):
		k = seq(t, [(0, 0), (0.25, 1), (1, 0)])
		return merge({"root": {"loc": (0, -0.1 * k, 0.02 * k), "rot": (6 * k, 0, 0)},
					  "waist": {"rot": (14 * k, 0, 10 * k)}, "head": {"rot": (10 * k, 0, -14 * k)},
					  "upper_l": {"rot": (30 * k, 20 * k, 0)}}, arms_rest(t), tail(t, 18 * k, 2))

	def death(t):   # the forelegs fold, the body rolls onto its side, the rider slumps over
		fold = seq(t, [(0, 0), (0.3, 1), (0.6, 0.4)])
		roll = seq(t, [(0.25, 0), (0.66, 84), (0.76, 78), (0.88, 84)])
		drop = seq(t, [(0.1, 0), (0.3, -0.26), (0.66, -0.62)])
		slump = seq(t, [(0.2, 0), (0.8, 1)])
		return merge({"root": {"loc": (0, 0, drop), "rot": (seq(t, [(0, 0), (0.3, -12), (0.6, 0)]), roll, 0)},
					  "leg_fl": {"rot": (50 * fold, 0, 0)}, "leg_fr": {"rot": (50 * fold, 0, 0)},
					  "shin_fl": {"rot": (-100 * fold, 0, 0)}, "shin_fr": {"rot": (-90 * fold, 0, 0)},
					  "leg_bl": {"rot": (-20 * slump, 0, 0)}, "leg_br": {"rot": (-8 * slump, 0, 0)},
					  "waist": {"rot": (30 * slump, -30 * slump, 0)}, "head": {"rot": (30 * slump, 0, 20 * slump)},
					  "upper_l": {"rot": (40 * slump, 50 * slump, 0)}, "upper_r": {"rot": (60 * slump, -20 * slump, 0)}},
					 tail(t, 0))

	clip(arm, "idle", 3.6, idle, True)
	clip(arm, "walk", 1.1, walk, True)
	clip(arm, "run", 0.6, run, True)
	clip(arm, "attack", 0.9 if kind == "rider" else (1.2 if kind == "archer" else 1.0), attack, False)
	clip(arm, "hit", 0.45, hit, False)
	clip(arm, "death", 1.5, death, False)
	return arm


def build_hoofborn_rider():
	return _hoofborn("hoofborn_rider", "rider")


def build_hoofborn_archer():
	return _hoofborn("hoofborn_archer", "archer")


def build_khan_oruk():
	return _hoofborn("khan_oruk", "khan")


# ---------------------------------------------------------------- barrow wights and the Barrow Lord
# The dead horse-lords of the burial mounds: Skeleton_Warrior repainted old yellowed bone in bronze gone
# green at the edges, a rotted fur mantle over bronze scale armor, a bronze circlet and cold green light
# in the sockets (the KayKit helmet and eyes are hidden). The Barrow Lord wears a tall bronze helm with a
# horse-hair crest and a death mask, a torc and a heavier mantle. Bolt-ons in KayKit mesh space.

BARROW_CELLS = {(1, 1): ("d4c8a0", "5e5238"), (3, 0): ("c8964a", "4a2e14"), (4, 0): ("c8964a", "4a2e14"),
				(6, 0): ("4a3a2a", "16100a"), (7, 0): ("4a3a2a", "16100a"), (2, 2): ("5a4632", "1a120a"),
				(1, 2): ("7aa08a", "24382e"), (5, 2): ("7aa08a", "24382e"), (2, 0): ("4a3a2a", "16100a"),
				(7, 3): ("eaffd8", "58e070")}
BARROW_LORD_CELLS = {(1, 1): ("ccc098", "564a32"), (3, 0): ("dcaa56", "5a3814"), (4, 0): ("dcaa56", "5a3814"),
					 (6, 0): ("3a2c20", "100a06"), (7, 0): ("3a2c20", "100a06"), (2, 2): ("6a2418", "1e0806"),
					 (1, 2): ("e0b454", "5a3a10"), (5, 2): ("e0b454", "5a3a10"), (2, 0): ("3a2c20", "100a06"),
					 (7, 3): ("eaffd8", "58e070")}


def barrow_materials(lord=False):
	return _rmats("barrow_lord" if lord else "barrow", {
		"bronze": ("d0a050" if lord else "b88a44", 0.35), "bronze_d": ("8a5e24" if lord else "7a5a2a", 0.45),
		"verdigris": ("6a9a82", 0.7), "gold": ("e8c060", 0.3), "fur": ("4a3a2a", 0.95), "fur_d": ("2e241a", 0.95),
		"fur_l": ("6a5840", 0.95), "ghost": ("b8ffb0", 0.2, 4.0), "ghost_d": ("58e070", 0.3, 2.0),
		"crest": ("7a1e14", 0.9), "crest_d": ("3a0e0a", 0.9), "leather": ("3a2a1c", 0.85), "dark": ("0e0a08", 0.8),
	})


def _lg_kaykit_tree(path, parts):
	"""A BVH of a KayKit model's named mesh parts in its rest pose (mesh space), so bolt-ons can be laid on it."""
	from mathutils.bvhtree import BVHTree
	before = set(bpy.data.objects)
	bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
	new = [o for o in bpy.data.objects if o not in before]
	bm = bmesh.new()
	for o in new:
		if o.type == "MESH" and o.name in parts:
			me = o.data.copy()
			me.transform(o.matrix_world)
			bm.from_mesh(me)
			bpy.data.meshes.remove(me)
	tree = BVHTree.FromBMesh(bm)
	bm.free()
	for o in new:
		bpy.data.objects.remove(o, do_unlink=True)
	return tree


def _barrow_eyes(b, m):
	for s in (1, -1):
		b.blob((0.13, 0.06, 0.1), (0.155 * s, -0.27, 1.645), m["ghost"], "x", segs=(8, 5))
		b.blob((0.2, 0.03, 0.16), (0.155 * s, -0.25, 1.645), m["ghost_d"], "x", segs=(8, 4))


def _barrow_scales(b, m, tree, rows, xs, lord):
	"""Rows of overlapping bronze scales laid on the chest, front and back, the lowest row greened."""
	for side in (-1, 1):   # -1: the front
		for r, z in enumerate(rows):
			off = 0.04 if r % 2 else 0.0
			for x in xs:
				o = Vector((x + off, side * 1.5, z))
				hit, n, _, _ = tree.ray_cast(o, Vector((0, -side, 0)))
				if hit is None:
					continue
				if n.y * side < 0:
					n = -n
				mat = m["verdigris"] if r == len(rows) - 1 and not lord else (m["bronze"] if (r + int(x * 20)) % 3 else m["bronze_d"])
				_oblob(b, (0.085, 0.1, 0.022), tuple(hit + n * 0.02 + Vector((0, 0, -0.02))), (0, 0.25 * side, -1), tuple(n), mat, "x", segs=(6, 3))


def _barrow_mantle(b, m, rng, lord):
	"""The rotted fur mantle: a thick collar over the shoulders, ragged fur hanging down the back."""
	g = 1.12 if lord else 1.0
	for k in range(22):
		a = 2 * math.pi * k / 22
		if math.sin(a) < -0.75:
			continue   # open at the throat, so it lies on the shoulders rather than under the jaw
		c = Vector((0.44 * g * math.cos(a), 0.34 * g * math.sin(a), 1.18 + 0.04 * abs(math.cos(a))))
		out = Vector((math.cos(a), math.sin(a), 0))
		_oblob(b, (0.22 * g, 0.28 * g, 0.12), tuple(c + out * 0.04), (0, 0, -1) if math.sin(a) > -0.3 else (out.x, out.y, -1.5),
			   tuple(out + Vector((0, 0, 0.8))), (m["fur"], m["fur_d"], m["fur_l"])[k % 3], "x", segs=(7, 4))
	for k in range(9):   # ragged fur hanging down the back
		x = (k - 4) * 0.09
		ln = rng.uniform(0.34, 0.6) * g
		_oblob(b, (0.12, ln, 0.06), (x, 0.38 * g, 1.14 - ln * 0.45), (0, 0.1, -1), (0, 1, 0), (m["fur_d"], m["fur"])[k % 2], "x", segs=(6, 4))
	for s in (1, -1):   # clasps at the collarbones
		b.blob((0.09, 0.05, 0.09), (0.2 * s, -0.33 * g, 1.16), m["bronze"], "x", segs=(8, 5))
		b.blob((0.04, 0.03, 0.04), (0.2 * s, -0.36 * g, 1.16), m["verdigris"] if not lord else m["gold"], "x", segs=(6, 4))


def build_barrow_wight_circlet():
	"""A bronze circlet round the skull, a greened boss over the brow, green light in the eyes."""
	m = barrow_materials()
	b = Builder("barrow_wight_circlet")
	_wrap(b, (0, 0.0, 1.9), (0.43, 0.46), 0.07, 0.03, m["bronze"], rot=(-6, 0, 0), sides=20)
	for k in range(7):   # studs round the band
		a = math.radians(270 + (k - 3) * 22)
		b.blob((0.05, 0.05, 0.05), (0.45 * math.cos(a), 0.48 * math.sin(a), 1.88 + 0.05 * math.sin(a) * 0), m["bronze_d"], "x", segs=(6, 4))
	b.blob((0.12, 0.05, 0.14), (0, -0.5, 1.89), m["verdigris"], "x", segs=(8, 5))
	b.blob((0.06, 0.03, 0.07), (0, -0.52, 1.89), m["ghost_d"], "x", segs=(6, 4))
	_barrow_eyes(b, m)
	return b.build_static()


def build_barrow_wight_mantle():
	import random
	rng = random.Random(3451)
	m = barrow_materials()
	b = Builder("barrow_wight_mantle")
	tree = _lg_kaykit_tree(SKELETONS + "Skeleton_Warrior.glb", {"Skeleton_Warrior_Body"})
	_barrow_scales(b, m, tree, [1.14, 1.06, 0.98, 0.9, 0.82], [x * 0.08 for x in range(-4, 4)], False)
	_barrow_mantle(b, m, rng, False)
	return b.build_static()


def build_barrow_lord_helm():
	"""A tall bronze helm over the whole skull, a crest of dark red horse-hair from brow to nape, a
	gilt death mask with green light behind its eye slits."""
	import random
	rng = random.Random(3457)
	m = barrow_materials(True)
	b = Builder("barrow_lord_helm")
	b.blob((0.98, 1.02, 0.86), (0, 0.02, 1.9), m["bronze"], "x", segs=(16, 12))                   # the bowl
	b.seg((0, 0.02, 2.2), (0, 0.04, 2.62), 0.24, 0.05, m["bronze"], "x", sides=12)              # its tall peak
	_wrap(b, (0, 0.02, 1.62), (0.5, 0.52), 0.1, 0.03, m["bronze_d"], sides=22)                   # the rim
	_wrap(b, (0, 0.02, 2.02), (0.46, 0.48), 0.06, 0.025, m["gold"], sides=22)
	for s in (1, -1):   # cheek guards
		_oblob(b, (0.3, 0.34, 0.06), (0.44 * s, -0.16, 1.5), (0, 0, -1), (s, -0.3, 0), m["bronze_d"], "x", segs=(8, 4))
	_oblob(b, (0.6, 0.3, 0.07), (0, 0.48, 1.5), (0, 0.3, -1), (0, 1, 0), m["bronze_d"], "x", segs=(10, 4))   # neck guard
	# the death mask: a gilt face over the front of the helm, eye slits lit green
	_oblob(b, (0.56, 0.62, 0.08), (0, -0.5, 1.66), (0, 0, 1), (0, -1, 0), m["gold"], "x", segs=(12, 6))
	b.seg((0, -0.55, 1.76), (0, -0.6, 1.56), 0.05, 0.06, m["gold"], "x", sides=6)                   # the nose
	b.blob((0.42, 0.06, 0.06), (0, -0.55, 1.8), m["gold"], "x", segs=(10, 4))                       # the brow ridge
	b.blob((0.2, 0.04, 0.03), (0, -0.55, 1.46), m["dark"], "x", segs=(8, 3))                        # the closed mouth
	for s in (1, -1):
		b.blob((0.13, 0.04, 0.04), (0.14 * s, -0.55, 1.7), m["ghost"], "x", rot=(0, -8 * s, 0), segs=(8, 3))
		b.blob((0.2, 0.03, 0.08), (0.14 * s, -0.53, 1.7), m["ghost_d"], "x", segs=(8, 3))
	# the crest: a bronze ridge from brow to nape, and a fall of horse-hair streaming back from it
	pts = [Vector((0, -0.36 + 0.9 * u, 2.3 + 0.36 * math.sin(math.pi * (0.2 + 0.7 * u)))) for u in [k / 8 for k in range(9)]]
	_chain(b, pts, 0.04, 0.03, m["bronze_d"], sides=5)
	for k, p in enumerate(pts):
		for j in range(3):
			d = Vector((rng.uniform(-0.12, 0.12), 0.7 + 0.1 * k, 0.5 - 0.14 * k)).normalized()
			ln = 0.34 + 0.04 * k + rng.uniform(0, 0.1)
			b.seg(tuple(p), tuple(p + d * ln), 0.05, 0.008, (m["crest"], m["crest_d"])[(k + j) % 2], "x", sides=4)
	return b.build_static()


def build_barrow_lord_mantle():
	import random
	rng = random.Random(3461)
	m = barrow_materials(True)
	b = Builder("barrow_lord_mantle")
	tree = _lg_kaykit_tree(SKELETONS + "Skeleton_Warrior.glb", {"Skeleton_Warrior_Body"})
	_barrow_scales(b, m, tree, [1.16, 1.09, 1.02, 0.95, 0.88, 0.81], [x * 0.075 for x in range(-5, 5)], True)
	_barrow_mantle(b, m, rng, True)
	_wrap(b, (0, 0.0, 1.3), (0.2, 0.18), 0.05, 0.04, m["gold"], gap=(250, 290), sides=16)            # the torc
	for s in (1, -1):
		b.blob((0.07, 0.07, 0.07), (0.07 * s, -0.19, 1.3), m["gold"], "x", segs=(6, 5))
	return b.build_static()


def _barrow_sword(name, lord):
	"""A bronze leaf-blade (KayKit weapons' frame: grip at the origin, blade up +Z): the wight's greened
	and notched, the lord's longer, bright, with a gold pommel and a horse-head guard."""
	m = barrow_materials(lord)
	b = Builder(name)
	edge = material(f"{name}_edge", "f0d494" if lord else "a8b89a", 0.3)
	b.seg((0, 0, -0.14), (0, 0, 0.12), 0.03, 0.028, m["leather"], "x", sides=6)
	b.blob((0.09, 0.07, 0.08) if lord else (0.07, 0.06, 0.07), (0, 0, -0.17), m["gold"] if lord else m["bronze_d"], "x", segs=(6, 5))
	b.blob((0.26 if lord else 0.2, 0.06, 0.05), (0, 0, 0.13), m["gold"] if lord else m["bronze_d"], "x", segs=(8, 4))
	if lord:
		for s in (1, -1):   # the guard's ends curl up into horse heads
			b.seg((0.12 * s, 0, 0.13), (0.15 * s, 0, 0.22), 0.025, 0.02, m["gold"], "x", sides=5)
			b.seg((0.15 * s, 0, 0.22), (0.1 * s, 0, 0.25), 0.022, 0.012, m["gold"], "x", sides=5)
	length = 1.0 if lord else 0.78
	pts = []
	for k in range(9):   # the leaf shape: narrow at the hilt, swelling, then drawn to a point
		u = k / 8
		w = (0.035 + 0.05 * math.sin(math.pi * min(1.0, u * 1.25) * 0.9)) * (1.12 if lord else 1.0)
		if not lord and k in (3, 6):
			w *= 0.75   # notches
		pts.append((0.15 + length * u, w * (1 - u ** 3)))
	for (z0, w0), (z1, w1) in zip(pts, pts[1:]):
		_slab(b, [(-w0, 0, z0), (w0, 0, z0), (w1, 0, z1), (-w1, 0, z1)], 0.022, m["bronze"] if lord else (m["bronze"] if z0 < 0.5 else m["bronze_d"]))
		for s in (1, -1):
			_slab(b, [(s * w0, 0, z0), (s * (w0 + 0.012), 0, z0), (s * (w1 + 0.012), 0, z1), (s * w1, 0, z1)], 0.012, edge)
	b.seg((0, 0, 0.15), (0, 0, 0.15 + length * 0.8), 0.014, 0.004, m["bronze_d"] if lord else m["verdigris"], "x", sides=4)   # the midrib
	_slab(b, [(-0.01, 0, 0.15 + length), (0.01, 0, 0.15 + length), (0, 0, 0.23 + length)], 0.016, edge)
	return b.build_static()


def build_barrow_blade():
	return _barrow_sword("barrow_blade", False)


def build_barrow_lord_sword():
	return _barrow_sword("barrow_lord_sword", True)


LONG_GRASS_CREATURES = {"grass_stalker": build_grass_stalker, "tawnyjaw": build_tawnyjaw,
						"grass_howler": build_grass_howler,
						"thunderhoof": build_thunderhoof, "old_thunderhoof": build_old_thunderhoof, "dirkhorn": build_dirkhorn,
						"hoofborn_rider": build_hoofborn_rider, "hoofborn_archer": build_hoofborn_archer, "khan_oruk": build_khan_oruk}
CREATURES.update(LONG_GRASS_CREATURES)
ATTACHMENTS.update({"barrow_wight_circlet": build_barrow_wight_circlet, "barrow_wight_mantle": build_barrow_wight_mantle,
					"barrow_lord_helm": build_barrow_lord_helm, "barrow_lord_mantle": build_barrow_lord_mantle,
					"barrow_blade": build_barrow_blade, "barrow_lord_sword": build_barrow_lord_sword})
BODIES.update({"barrow_wight_body": (SKELETONS + "Skeleton_Warrior.glb", "barrow_wight_texture", BARROW_CELLS, None),
			   "barrow_lord_body": (SKELETONS + "Skeleton_Warrior.glb", "barrow_lord_texture", BARROW_LORD_CELLS, None)})
# ================================================================ end of The Long Grass


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
	# back off for creatures bigger than a wolf, so the whole of a big one is in frame
	pts = [o.matrix_world @ Vector(c) for o in arm.children for c in o.bound_box]
	size = max([1.6] + [max(abs(p.x), abs(p.y), p.z * 0.75) for p in pts])
	top = max([1.0] + [p.z for p in pts])
	cam.rotation_euler = (math.radians(66), 0, math.radians(43))
	fwd = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))
	cam.location = Vector((0, 0, top * 0.42)) - fwd * size * 2.4
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
