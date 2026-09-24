"""Builds wearable gear that shows on characters, exported as GLBs.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/gear.py -- --out assets/gear [--preview DIR] [--only cloth_cap]

Each piece is authored in KayKit character mesh space (Blender Z up, facing
-Y, about 2.3 units tall), the same space as the gnoll head in creatures.py:
the game pins it to the named bone and offsets it by that bone's inverse rest
pose, so it lands where it was modeled and then follows the animation. Pieces
use the Dungeon pack palette through props.py's Prop helpers, so gear matches
the world's colors.

Heads: every class head fits inside x +-0.58, y -0.56..0.58, z 1.05..2.28, with
the face toward -Y below z ~1.85. Headgear sits over the crown and stays off
the face. Paired pieces (gloves, boots, sleeves, leg plates) are built for the
left side and exported mirrored for the right. --preview renders cloth,
leather and iron outfits on every class; --manifest <file> writes the
models.json "gear" entries.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import props  # noqa: E402  (the shared palette helpers)
from props import (BONE, CLOTH_RED, CLOTH_WHITE, GOLD, HIDE, LEAF, Prop, STONE_DARK, STONE_LIGHT,  # noqa: E402
				   WOOD, WOOD_GRAY)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHARACTERS = os.path.join(ROOT, "assets/KayKit_Adventurers_2.0_FREE/Characters/gltf")
PREVIEW_CLASSES = [("Barbarian", ["Barbarian_BearHat"]), ("Knight", ["Knight_Helmet", "Knight_HelmetVisor"]),
				   ("Mage", ["Mage_Hat"])]


class Gear(Prop):
	"""Prop plus the shapes headgear needs."""

	def dome(self, radii, base, swatch, grad=(0.05, 0.7), segs=(16, 10), jitter=0.0):
		"""Upper half of an ellipsoid standing on `base` (its open rim)."""
		bm = bmesh.new()
		bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
		bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context="VERTS")
		for v in bm.verts:
			v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2])) + Vector(base)
		return self._add(bm, swatch, grad, 0.0, jitter)

	def ring(self, radius, z, height, swatch, y=0.0, sides=16, taper=0.0, grad=(0.2, 0.7)):
		"""A band around the head: an open tube, wider at the bottom by `taper`."""
		return self.seg((0, y, z - height / 2), (0, y, z + height / 2), radius + taper, radius, swatch, sides=sides, grad=grad)


# ---------------------------------------------------------------- headgear
# Domes are sized to swallow the tallest hair (the Knight's crown tuft, ~2.28)
# and the widest (the Mage's, x +-0.57 around z 2.0).

DOME = (0.7, 0.67, 0.62)  # x, y, z radii of a close-fitting crown
DOME_BASE = (0, 0.04, 1.78)


def cloth_cap():
	g = Gear("cloth_cap", 101)
	g.dome(DOME, DOME_BASE, CLOTH_RED, grad=(0.05, 0.6))
	g.ring(0.71, 1.83, 0.13, CLOTH_WHITE, y=0.04, taper=0.01)           # turned-up band
	g.blob((0.14, 0.14, 0.1), (0, 0.04, 2.4), CLOTH_RED, segs=(8, 5))    # little knot on top
	return g.build()


def leather_cap():
	g = Gear("leather_cap", 103)
	g.dome((0.72, 0.69, 0.63), DOME_BASE, HIDE, grad=(0.1, 0.8), jitter=0.004)
	g.ring(0.73, 1.8, 0.1, WOOD, y=0.04)                                 # stitched rim
	for s in (1, -1):                                                     # ear flaps
		g.box((0.08, 0.3, 0.36), (0.7 * s, 0.08, 1.64), HIDE, rot=(0, -6 * s, 0), grad=(0.2, 0.9))
		g.blob((0.05, 0.05, 0.05), (0.75 * s, 0.08, 1.52), WOOD, segs=(6, 4))  # tie
	return g.build()


def floppy_hat():
	g = Gear("floppy_hat", 105)
	g.dome((0.66, 0.64, 0.56), (0, 0.04, 1.86), HIDE, grad=(0.1, 0.6))
	g.seg((0, 0.04, 1.74), (0, 0.04, 1.9), 0.9, 0.62, HIDE, sides=18, grad=(0.25, 0.8))   # drooping brim
	g.ring(0.67, 1.95, 0.1, LEAF, y=0.04)                                                  # hat band
	g.blob((0.08, 0.05, 0.05), (0.5, -0.24, 1.98), CLOTH_RED, segs=(6, 4))                 # a fishing fly
	g.seg((0.5, -0.24, 1.98), (0.58, -0.34, 2.02), 0.012, 0.004, GOLD, sides=3)
	return g.build()


def bone_helm():
	g = Gear("bone_helm", 107)
	g.dome((0.72, 0.69, 0.63), (0, 0.04, 1.76), BONE, grad=(0.05, 0.75), jitter=0.01)
	g.box((0.1, 0.95, 0.14), (0, 0.06, 2.38), BONE, grad=(0.0, 0.5))                        # crest
	g.box((1.0, 0.12, 0.1), (0, -0.62, 1.84), BONE, rot=(-8, 0, 0), grad=(0.1, 0.8))         # brow plate
	for s in (1, -1):
		g.seg((0.6 * s, -0.1, 2.08), (0.84 * s, -0.2, 2.36), 0.08, 0.0, BONE, sides=6)       # horns
		g.box((0.06, 0.2, 0.24), (0.7 * s, -0.24, 1.7), BONE, rot=(0, 0, 10 * s))             # cheek guards
	g.box((0.03, 0.05, 0.3), (0.22, -0.66, 2.08), STONE_DARK, rot=(0, 20, 0))                  # the crack
	return g.build()


def iron_coif():
	g = Gear("iron_coif", 109)
	g.dome((0.73, 0.7, 0.64), (0, 0.04, 1.74), STONE_LIGHT, grad=(0.15, 0.7))
	g.ring(0.73, 1.76, 0.08, WOOD_GRAY, y=0.04)                                               # rim over the brow
	# chain falls around the sides and back of the head to the shoulders, open at the face
	for a in range(20, 341, 20):
		r = math.radians(a + 90)
		x, y = math.cos(r) * 0.7, 0.06 + math.sin(r) * 0.68
		if y < -0.3:
			continue
		g.box((0.26, 0.06, 0.58), (x, y, 1.46), STONE_LIGHT, rot=(0, 0, math.degrees(r) + 90), grad=(0.2, 0.85))
	g.ring(0.58, 1.16, 0.12, STONE_LIGHT, y=0.06, taper=0.08)                                 # collar
	return g.build()


# ---------------------------------------------------------------- body gear
# Built for the LEFT side (+x); the export mirrors each to the right. The body,
# arms and legs of every class fit inside: torso x +-0.45, y +-0.41, z 0.35-1.39;
# arms along x at z ~1.11 (thickness ~0.3), hand x 0.78-0.97; legs centered at
# x +-0.17, thigh z 0.3-0.53, shin 0.12-0.3, foot z 0-0.2 with toes toward -y.

ARM_Z = 1.11


def _cuff(g, x0, x1, r0, r1, swatch):
	g.seg((x0, 0, ARM_Z), (x1, 0, ARM_Z), r0, r1, swatch, sides=10, grad=(0.2, 0.8))


def cloth_gloves():
	g = Gear("cloth_gloves", 121)
	g.blob((0.24, 0.33, 0.33), (0.875, 0, ARM_Z), CLOTH_WHITE, segs=(10, 7))
	_cuff(g, 0.7, 0.79, 0.17, 0.165, CLOTH_WHITE)
	return g.build()


def leather_gloves():
	g = Gear("leather_gloves", 123)
	g.blob((0.25, 0.34, 0.34), (0.875, 0, ARM_Z), HIDE, segs=(10, 7))
	_cuff(g, 0.66, 0.79, 0.185, 0.165, HIDE)
	_cuff(g, 0.7, 0.73, 0.19, 0.19, WOOD)
	return g.build()


def iron_gauntlets():
	g = Gear("iron_gauntlets", 125)
	g.blob((0.27, 0.36, 0.36), (0.875, 0, ARM_Z), STONE_LIGHT, segs=(10, 7))
	_cuff(g, 0.6, 0.79, 0.21, 0.17, STONE_LIGHT)
	g.box((0.12, 0.2, 0.03), (0.89, 0, ARM_Z + 0.165), STONE_DARK)          # knuckle plate
	return g.build()


def cloth_sleeves_lower():
	g = Gear("cloth_sleeves_lower", 127)
	_cuff(g, 0.45, 0.73, 0.165, 0.17, CLOTH_WHITE)
	return g.build()


def cloth_sleeves_upper():
	g = Gear("cloth_sleeves_upper", 128)
	_cuff(g, 0.2, 0.47, 0.18, 0.165, CLOTH_WHITE)
	return g.build()


def leather_sleeves_lower():
	g = Gear("leather_sleeves_lower", 129)
	_cuff(g, 0.48, 0.72, 0.168, 0.178, HIDE)                                  # bracer
	for x in (0.53, 0.66):
		_cuff(g, x, x + 0.03, 0.185, 0.185, WOOD)                             # straps
	return g.build()


def leather_sleeves_upper():
	g = Gear("leather_sleeves_upper", 130)
	_cuff(g, 0.22, 0.46, 0.175, 0.168, HIDE)
	g.blob((0.3, 0.36, 0.16), (0.3, 0, ARM_Z + 0.15), HIDE, segs=(10, 6))    # shoulder cap
	return g.build()


def sandals():
	g = Gear("sandals", 131)
	g.box((0.27, 0.45, 0.05), (0.17, -0.08, 0.025), WOOD, grad=(0.3, 0.9))
	for y in (-0.2, -0.02):
		g.box((0.29, 0.05, 0.11), (0.17, y, 0.09), HIDE)
	g.seg((0.17, 0.02, 0.05), (0.17, 0.02, 0.22), 0.145, 0.14, HIDE, sides=10)  # ankle strap
	return g.build()


def leather_boots():
	g = Gear("leather_boots", 133)
	g.blob((0.29, 0.47, 0.25), (0.17, -0.08, 0.1), HIDE, segs=(10, 7))
	g.seg((0.17, 0.0, 0.1), (0.17, 0.0, 0.33), 0.155, 0.16, HIDE, sides=10)
	g.seg((0.17, 0.0, 0.3), (0.17, 0.0, 0.34), 0.17, 0.17, WOOD, sides=10)       # turned-over top
	return g.build()


def iron_boots():
	g = Gear("iron_boots", 135)
	g.blob((0.3, 0.48, 0.26), (0.17, -0.08, 0.1), STONE_LIGHT, segs=(10, 7))
	g.seg((0.17, 0.0, 0.1), (0.17, 0.0, 0.34), 0.165, 0.17, STONE_LIGHT, sides=10)
	g.blob((0.2, 0.18, 0.14), (0.17, -0.27, 0.1), STONE_DARK, segs=(8, 5))        # toe cap
	return g.build()


def _leg(g, z0, z1, r0, r1, swatch):
	g.seg((0.17, 0.0, z0), (0.17, 0.0, z1), r0, r1, swatch, sides=10, grad=(0.2, 0.8))


def patchwork_pants_thigh():
	g = Gear("patchwork_pants_thigh", 141)
	_leg(g, 0.3, 0.53, 0.15, 0.16, CLOTH_RED)
	g.box((0.1, 0.03, 0.1), (0.2, -0.155, 0.42), HIDE, rot=(0, 15, 0))           # a patch
	return g.build()


def patchwork_pants_shin():
	g = Gear("patchwork_pants_shin", 142)
	_leg(g, 0.13, 0.31, 0.14, 0.15, CLOTH_RED)
	g.box((0.08, 0.03, 0.08), (0.14, -0.145, 0.22), CLOTH_WHITE, rot=(0, -10, 0))
	return g.build()


def leather_leggings_thigh():
	g = Gear("leather_leggings_thigh", 143)
	_leg(g, 0.3, 0.53, 0.155, 0.165, HIDE)
	return g.build()


def leather_leggings_shin():
	g = Gear("leather_leggings_shin", 144)
	_leg(g, 0.13, 0.31, 0.145, 0.155, HIDE)
	_leg(g, 0.27, 0.3, 0.16, 0.16, WOOD)                                           # knee strap
	return g.build()


def iron_greaves_shin():
	g = Gear("iron_greaves_shin", 145)
	_leg(g, 0.12, 0.31, 0.155, 0.165, STONE_LIGHT)
	g.blob((0.16, 0.1, 0.14), (0.17, -0.14, 0.31), STONE_DARK, segs=(8, 5))        # knee cop
	return g.build()


def _torso(g, swatch, rx=0.48, ry=0.45, grad=(0.15, 0.85)):
	"""A shell over the torso, open at the neck: sides from the belt line up to
	the shoulders, then sloping in toward the collar."""
	bm = bmesh.new()
	bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=1.0, radius2=1.0, depth=0.56)
	for v in bm.verts:
		v.co = Vector((v.co.x * rx, v.co.y * ry, v.co.z + 0.9))
	g._add(bm, swatch, grad, 0.0, 0.0)
	bm = bmesh.new()
	bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=1.0, radius2=0.62, depth=0.14)
	for v in bm.verts:
		v.co = Vector((v.co.x * rx, v.co.y * ry, v.co.z + 1.25))
	g._add(bm, swatch, (grad[0], grad[0] + 0.2), 0.0, 0.0)


def patchwork_tunic():
	g = Gear("patchwork_tunic", 151)
	_torso(g, CLOTH_RED)
	g.box((0.16, 0.03, 0.14), (-0.18, -0.455, 0.84), HIDE, rot=(0, 12, 0))
	g.box((0.12, 0.03, 0.12), (0.2, -0.455, 1.02), CLOTH_WHITE, rot=(0, -8, 0))
	g.box((0.14, 0.03, 0.1), (0.1, 0.455, 0.78), HIDE)
	return g.build()


def leather_tunic():
	g = Gear("leather_tunic", 153)
	_torso(g, HIDE, grad=(0.2, 0.9))
	for z in (0.8, 0.92, 1.04):                                                    # laces
		g.box((0.12, 0.03, 0.025), (0, -0.455, z), WOOD, rot=(0, 25, 0))
		g.box((0.12, 0.03, 0.025), (0, -0.455, z), WOOD, rot=(0, -25, 0))
	return g.build()


def studded_tunic():
	g = Gear("studded_tunic", 155)
	_torso(g, HIDE, grad=(0.25, 0.95))
	for x in (-0.28, -0.14, 0.0, 0.14, 0.28):
		for z in (0.76, 0.9, 1.04):
			g.blob((0.05, 0.03, 0.05), (x, -0.455 + abs(x) * 0.08, z), GOLD, segs=(6, 4))
	return g.build()


def mangy_hide_vest():
	g = Gear("mangy_hide_vest", 157)
	_torso(g, HIDE, rx=0.49, ry=0.46, grad=(0.3, 1.0))
	for s in (1, -1):                                                              # ragged fur at the shoulders
		for k in range(4):
			g.rock((0.18, 0.16, 0.12), (s * (0.26 + k * 0.05), 0.02 - k * 0.1 + 0.15, 1.3 - k * 0.02), WOOD, jitter=0.12)
	return g.build()


def rope_belt():
	g = Gear("rope_belt", 161)
	g.seg((0, 0, 0.62), (0, 0, 0.67), 0.46, 0.46, WOOD_GRAY, sides=16)
	g.blob((0.1, 0.08, 0.08), (0.14, -0.44, 0.63), WOOD_GRAY, segs=(6, 4))          # knot
	g.seg((0.14, -0.44, 0.6), (0.16, -0.45, 0.48), 0.025, 0.02, WOOD_GRAY, sides=4)  # ends
	g.seg((0.12, -0.44, 0.6), (0.1, -0.45, 0.5), 0.025, 0.02, WOOD_GRAY, sides=4)
	return g.build()


def leather_belt():
	g = Gear("leather_belt", 163)
	g.seg((0, 0, 0.6), (0, 0, 0.69), 0.465, 0.465, HIDE, sides=16)
	g.box((0.15, 0.04, 0.12), (0, -0.47, 0.645), GOLD)                              # buckle
	g.box((0.07, 0.05, 0.06), (0, -0.48, 0.645), WOOD)
	return g.build()


# name -> (builder, bone). A bone ending in ".l" is built on the left and also
# exported mirrored as <name>_r for the matching ".r" bone.
PIECES = {
	"cloth_cap": (cloth_cap, "head"),
	"leather_cap": (leather_cap, "head"),
	"floppy_hat": (floppy_hat, "head"),
	"bone_helm": (bone_helm, "head"),
	"iron_coif": (iron_coif, "head"),
	"cloth_gloves": (cloth_gloves, "hand.l"),
	"leather_gloves": (leather_gloves, "hand.l"),
	"iron_gauntlets": (iron_gauntlets, "hand.l"),
	"cloth_sleeves_lower": (cloth_sleeves_lower, "lowerarm.l"),
	"cloth_sleeves_upper": (cloth_sleeves_upper, "upperarm.l"),
	"leather_sleeves_lower": (leather_sleeves_lower, "lowerarm.l"),
	"leather_sleeves_upper": (leather_sleeves_upper, "upperarm.l"),
	"sandals": (sandals, "foot.l"),
	"leather_boots": (leather_boots, "foot.l"),
	"iron_boots": (iron_boots, "foot.l"),
	"patchwork_pants_thigh": (patchwork_pants_thigh, "upperleg.l"),
	"patchwork_pants_shin": (patchwork_pants_shin, "lowerleg.l"),
	"leather_leggings_thigh": (leather_leggings_thigh, "upperleg.l"),
	"leather_leggings_shin": (leather_leggings_shin, "lowerleg.l"),
	"iron_greaves_shin": (iron_greaves_shin, "lowerleg.l"),
	"patchwork_tunic": (patchwork_tunic, "chest"),
	"leather_tunic": (leather_tunic, "chest"),
	"studded_tunic": (studded_tunic, "chest"),
	"mangy_hide_vest": (mangy_hide_vest, "chest"),
	"rope_belt": (rope_belt, "spine"),
	"leather_belt": (leather_belt, "spine"),
}

# What each wearable is made of, for models.json "gear".
OUTFITS = {
	"cloth_cap": ["cloth_cap"], "leather_cap": ["leather_cap"], "floppy_hat": ["floppy_hat"],
	"bone_helm": ["bone_helm"], "iron_coif": ["iron_coif"],
	"cloth_gloves": ["cloth_gloves"], "leather_gloves": ["leather_gloves"], "iron_gauntlets": ["iron_gauntlets"],
	"cloth_sleeves": ["cloth_sleeves_lower", "cloth_sleeves_upper"],
	"leather_sleeves": ["leather_sleeves_lower", "leather_sleeves_upper"],
	"sandals": ["sandals"], "leather_boots": ["leather_boots"], "iron_boots": ["iron_boots"],
	"patchwork_pants": ["patchwork_pants_thigh", "patchwork_pants_shin"],
	"leather_leggings": ["leather_leggings_thigh", "leather_leggings_shin"],
	"iron_greaves": ["iron_greaves_shin"],
	"patchwork_tunic": ["patchwork_tunic"], "leather_tunic": ["leather_tunic"], "studded_tunic": ["studded_tunic"],
	"mangy_hide_vest": ["mangy_hide_vest"], "rope_belt": ["rope_belt"], "leather_belt": ["leather_belt"],
}

PREVIEW_OUTFITS = {
	"cloth": ["cloth_cap", "cloth_gloves", "cloth_sleeves", "sandals", "patchwork_pants", "patchwork_tunic", "rope_belt"],
	"leather": ["leather_cap", "leather_gloves", "leather_sleeves", "leather_boots", "leather_leggings", "studded_tunic", "leather_belt"],
	"iron": ["iron_coif", "iron_gauntlets", "iron_boots", "iron_greaves", "mangy_hide_vest"],
}


def manifest():
	"""models.json "gear": {wearable: {pieces: [{path, bone}]}}."""
	out = {}
	for wearable, names in OUTFITS.items():
		pieces = []
		for n in names:
			bone = PIECES[n][1]
			pieces.append({"path": "res://assets/gear/%s.glb" % n, "bone": bone})
			if bone.endswith(".l"):
				pieces.append({"path": "res://assets/gear/%s_r.glb" % n, "bone": bone[:-2] + ".r"})
		out[wearable] = {"pieces": pieces}
	return out


def _mirror(obj):
	"""Flips a left-side piece to the right: x negated, faces turned back out."""
	for v in obj.data.vertices:
		v.co.x = -v.co.x
	bm = bmesh.new()
	bm.from_mesh(obj.data)
	bmesh.ops.reverse_faces(bm, faces=bm.faces)
	bm.to_mesh(obj.data)
	bm.free()


# ---------------------------------------------------------------- export + preview

def _stage(cls, hats):
	"""A class body (own hat removed), lights and a camera; returns the camera."""
	bpy.ops.import_scene.gltf(filepath=os.path.join(CHARACTERS, cls + ".glb"))
	for o in list(bpy.context.scene.objects):
		if o.name.split(".")[0] in hats:
			bpy.data.objects.remove(o, do_unlink=True)
	scene = bpy.context.scene
	scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
	scene.render.resolution_x, scene.render.resolution_y = 360, 420
	world = bpy.data.worlds.new("w")
	world.use_nodes = True
	world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.7, 1)
	scene.world = world
	sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
	sun.data.energy = 3.0
	sun.rotation_euler = (math.radians(50), 0, math.radians(30))
	bpy.context.collection.objects.link(sun)
	cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
	bpy.context.collection.objects.link(cam)
	scene.camera = cam
	return cam


def _shoot(cam, path, views):
	for view, loc, aim in views:
		cam.location = loc
		cam.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
		bpy.context.scene.render.filepath = path % view
		bpy.ops.render.render(write_still=True)


def _build_piece(name, mirrored=False):
	props._materials.clear()
	obj = PIECES[name][0]()
	if mirrored:
		_mirror(obj)
	return obj


def preview_outfits(out_dir):
	"""Each preview outfit on each class, front and back three-quarter."""
	for outfit, wearables in PREVIEW_OUTFITS.items():
		for cls, hats in PREVIEW_CLASSES:
			props.reset_scene()
			for w in wearables:
				for n in OUTFITS[w]:
					_build_piece(n)
					if PIECES[n][1].endswith(".l"):
						_build_piece(n, mirrored=True)
			cam = _stage(cls, hats)
			_shoot(cam, os.path.join(out_dir, "%s_%s_%%s.png" % (outfit, cls.lower())),
				   [("front", (1.4, -4.2, 1.6), (0, 0, 0.95)), ("back", (-2.6, 3.4, 1.9), (0, 0, 0.95))])


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/gear", "--preview": "", "--only": "", "--manifest": ""}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	if opts["--manifest"]:
		import json
		with open(opts["--manifest"], "w") as f:
			json.dump(manifest(), f, indent=2)
		print("wrote %s" % opts["--manifest"])
		return
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) if opts["--only"] else None
	for name, (build, bone) in PIECES.items():
		if only and name not in only:
			continue
		for mirrored in ([False, True] if bone.endswith(".l") else [False]):
			props.reset_scene()
			_build_piece(name, mirrored)
			out = name + ("_r" if mirrored else "")
			props.export(os.path.abspath(os.path.join(opts["--out"], out + ".glb")))
			print("exported %s" % out)
	if opts["--preview"]:
		os.makedirs(opts["--preview"], exist_ok=True)
		preview_outfits(opts["--preview"])


if __name__ == "__main__":
	main()
