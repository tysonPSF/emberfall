"""Renders an inventory icon for every item into assets/icons/<item>.png.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/icons.py -- --out assets/icons [--only cloth_cap,gnoll_fang] [--size 128]

Where the picture comes from, per item (data/items/*.json):
  "wear"   a small model built here if there is one (trousers: KayKit's leg
           parts are mostly boots on these short legs), else the KayKit parts
           it swaps onto the body (models.json "body_parts"), else the gear
           pieces from gear.py
  "model"  the weapon or shield scene named in data/models.json "weapons"
  else     a small model built here (drops, jewelry, bags), in the Dungeon
           palette like everything else
Icons are square, transparent, lit from the upper left and seen from a fixed
three-quarter angle, so a row of them reads as one set. Quality variants
(Fine, Superior...) share the base item's icon; the game tints the frame.
"""

import glob
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import gear  # noqa: E402
import props  # noqa: E402
from props import (BONE, CLAY, CLOTH_RED, CLOTH_WHITE, EMBER, GOLD, HIDE, IRON, LEAF, PETAL_PURPLE, PINE, Prop, RUNE, STONE_DARK,  # noqa: E402
				   STONE_WARM, STONE_LIGHT, WATER, WOOD, WOOD_GRAY)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _res(path):
	return os.path.join(ROOT, path.replace("res://", ""))


# ---------------------------------------------------------------- small models

def gnoll_fang():
	p = Prop("gnoll_fang", 201)
	p.seg((0, 0, 0), (0.05, 0, 0.9), 0.16, 0.0, BONE, sides=7, grad=(0.0, 0.7))
	p.seg((0, 0, -0.05), (0, 0, 0.05), 0.17, 0.16, WOOD, sides=7)                 # root
	return p.build()


def beetle_eye():
	p = Prop("beetle_eye", 203)
	p.blob((0.7, 0.7, 0.7), (0, 0, 0.35), EMBER, segs=(14, 9), grad=(0.0, 0.6), glow=1.2)
	p.blob((0.3, 0.2, 0.3), (0, -0.28, 0.42), STONE_DARK, segs=(8, 6))            # pupil
	return p.build()


def bone_chips():
	p = Prop("bone_chips", 205)
	for k in range(5):
		a = k * 1.3
		p.rock((0.34, 0.26, 0.16), (math.cos(a) * 0.28, math.sin(a) * 0.28, 0.08 + k * 0.03), BONE, jitter=0.12)
	return p.build()


def rat_whiskers():
	p = Prop("rat_whiskers", 207)
	for k in range(6):
		a = math.radians(-35 + k * 14)
		p.seg((0, 0, 0.1), (math.cos(a) * 0.9, math.sin(a) * 0.3, 0.1 + math.sin(a) * 0.2), 0.02, 0.006, WOOD_GRAY, sides=4)
	p.blob((0.14, 0.14, 0.1), (0, 0, 0.1), HIDE, segs=(6, 4))
	return p.build()


def fishing_bait():
	p = Prop("fishing_bait", 209)
	p.seg((0, 0, 0), (0, 0, 0.55), 0.36, 0.36, IRON, sides=12, grad=(0.1, 0.6))
	p.seg((0, 0, 0.55), (0, 0, 0.58), 0.33, 0.33, STONE_DARK, sides=12)
	for k in range(3):                                                             # worms poking out
		a = k * 2.1
		p.seg((math.cos(a) * 0.15, math.sin(a) * 0.15, 0.55), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.85), 0.05, 0.04, CLOTH_RED, sides=5)
	return p.build()


def _cord(p, radius, z, swatch=WOOD_GRAY):
	for k in range(16):
		a0, a1 = k * math.tau / 16, (k + 1) * math.tau / 16
		p.seg((math.cos(a0) * radius, math.sin(a0) * radius * 0.6, z + math.sin(a0) * 0.2),
			  (math.cos(a1) * radius, math.sin(a1) * radius * 0.6, z + math.sin(a1) * 0.2), 0.025, 0.025, swatch, sides=4)


def bone_charm():
	p = Prop("bone_charm", 211)
	_cord(p, 0.5, 0.6)
	p.blob((0.3, 0.1, 0.4), (0, -0.3, 0.2), BONE, segs=(8, 6))
	p.blob((0.1, 0.06, 0.1), (0, -0.36, 0.24), RUNE, segs=(6, 4), glow=0.8)
	return p.build()


def fang_necklace():
	p = Prop("fang_necklace", 213)
	_cord(p, 0.55, 0.6)
	for k in range(5):
		a = math.radians(-70 + k * 35)
		x, y = math.sin(a) * 0.5, -math.cos(a) * 0.3
		p.seg((x, y, 0.45), (x * 1.05, y * 1.05, 0.12), 0.07, 0.0, BONE, sides=5)
	return p.build()


def _ring(p, swatch, stone=None):
	for k in range(14):
		a0, a1 = k * math.tau / 14, (k + 1) * math.tau / 14
		p.seg((math.cos(a0) * 0.4, 0, 0.4 + math.sin(a0) * 0.4), (math.cos(a1) * 0.4, 0, 0.4 + math.sin(a1) * 0.4),
			  0.09, 0.09, swatch, sides=6)
	if stone:
		p.blob((0.22, 0.18, 0.2), (0, 0, 0.86), stone, segs=(8, 6), glow=0.6)


def tarnished_ring():
	p = Prop("tarnished_ring", 215)
	_ring(p, WOOD_GRAY)
	return p.build()


def copper_band():
	p = Prop("copper_band", 217)
	_ring(p, EMBER, stone=LEAF)
	return p.build()


def bonecarved_talisman():
	p = Prop("bonecarved_talisman", 219)
	_cord(p, 0.5, 0.75, HIDE)
	p.seg((0, -0.25, 0.0), (0, -0.25, 0.6), 0.28, 0.24, BONE, sides=6, grad=(0.0, 0.6))
	p.blob((0.16, 0.06, 0.16), (0, -0.5, 0.32), RUNE, segs=(6, 4), glow=1.0)
	return p.build()


def _bag(p, swatch, w, d, h, strap=WOOD, flap=True):
	p.blob((w, d, h), (0, 0, h * 0.5), swatch, segs=(12, 8), grad=(0.1, 0.9))
	if flap:
		p.box((w * 0.8, 0.05, h * 0.35), (0, -d * 0.5, h * 0.72), swatch, rot=(-12, 0, 0), grad=(0.0, 0.6))
	p.seg((-w * 0.35, 0, h * 0.95), (w * 0.35, 0, h * 0.95), 0.04, 0.04, strap, sides=5)


def small_sack():
	p = Prop("small_sack", 221)
	p.blob((0.8, 0.7, 0.75), (0, 0, 0.38), CLOTH_WHITE, segs=(12, 8), grad=(0.1, 0.9))
	p.seg((0, 0, 0.72), (0, 0, 0.95), 0.1, 0.18, CLOTH_WHITE, sides=8)             # gathered neck
	p.seg((0, 0, 0.78), (0, 0, 0.82), 0.13, 0.13, HIDE, sides=8)                   # tie
	return p.build()


def worn_backpack():
	p = Prop("worn_backpack", 223)
	_bag(p, HIDE, 0.8, 0.5, 0.9, strap=WOOD_GRAY)
	return p.build()


def gnollhide_satchel():
	p = Prop("gnollhide_satchel", 225)
	_bag(p, WOOD, 0.9, 0.4, 0.6)
	for k in range(4):
		p.rock((0.18, 0.1, 0.12), (-0.3 + k * 0.2, -0.2, 0.62), HIDE, jitter=0.1)      # fur trim
	return p.build()


def leather_backpack():
	p = Prop("leather_backpack", 227)
	_bag(p, HIDE, 0.85, 0.55, 1.0)
	p.box((0.1, 0.06, 0.12), (0, -0.33, 0.62), GOLD)                              # buckle
	return p.build()


def braided_whisker_cord():
	p = Prop("braided_whisker_cord", 229)
	for ring in range(3):                                                          # a coil of cord, three turns
		for k in range(14):
			a0, a1 = k * math.tau / 14, (k + 1) * math.tau / 14
			r, z = 0.5 - ring * 0.04, 0.1 + ring * 0.09
			p.seg((math.cos(a0) * r, math.sin(a0) * r, z), (math.cos(a1) * r, math.sin(a1) * r, z), 0.06, 0.06, WOOD_GRAY, sides=5, twist=30)
	p.seg((0.5, 0, 0.3), (0.75, -0.2, 0.05), 0.05, 0.03, WOOD_GRAY, sides=5)       # loose end
	return p.build()


def blackpaw_pelt():
	p = Prop("blackpaw_pelt", 231)
	p.blob((1.1, 0.8, 0.12), (0, 0, 0.06), STONE_DARK, segs=(12, 6), grad=(0.0, 0.5), jitter=0.05)
	for x in (-1, 1):                                                              # legs of the hide
		p.blob((0.3, 0.22, 0.1), (x * 0.4, 0.32, 0.05), STONE_DARK, segs=(6, 4), grad=(0.0, 0.5))
		p.blob((0.3, 0.22, 0.1), (x * 0.4, -0.32, 0.05), STONE_DARK, segs=(6, 4), grad=(0.0, 0.5))
	p.blob((0.28, 0.22, 0.1), (0.52, 0, 0.1), WOOD, segs=(8, 5))                  # the paw
	return p.build()


def stitched_blackpaw_hide():
	p = Prop("stitched_blackpaw_hide", 233)
	p.box((0.9, 0.7, 0.14), (0, 0, 0.07), HIDE, grad=(0.1, 0.6))
	p.box((0.9, 0.7, 0.12), (0.03, 0.02, 0.2), STONE_DARK, rot=(0, 0, 4), grad=(0.0, 0.5))   # folded over
	for k in range(6):                                                             # stitches down the edge
		x = -0.38 + k * 0.15
		p.seg((x, -0.36, 0.3), (x + 0.06, -0.33, 0.1), 0.02, 0.02, WOOD_GRAY, sides=4)
	return p.build()


def tovins_trail_pack():
	p = Prop("tovins_trail_pack", 235)
	_bag(p, STONE_DARK, 0.85, 0.55, 1.0, strap=HIDE)
	p.blob((0.1, 0.06, 0.1), (0, -0.34, 0.62), EMBER, segs=(8, 6), glow=1.2)       # the beetle-eye clasp
	for x in (-0.3, 0.3):                                                          # side pouches
		p.blob((0.25, 0.3, 0.36), (x * 1.3, -0.02, 0.36), WOOD, segs=(8, 6))
	return p.build()


def crude_arrow():
	bpy.ops.import_scene.gltf(filepath=_res("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/arrow_bow_bundle.gltf"))


def sling_stone():
	p = Prop("sling_stone", 237)
	for k, (x, y) in enumerate([(0, 0), (0.42, 0.1), (-0.36, 0.18), (0.1, 0.4), (-0.05, -0.38)]):
		p.rock((0.32, 0.28, 0.24), (x, y, 0.12 + (0.14 if k == 0 else 0)), STONE_LIGHT, jitter=0.1)
	return p.build()


def leather_sling():
	p = Prop("leather_sling", 239)
	p.blob((0.6, 0.4, 0.2), (0, 0, 0.1), WOOD, segs=(10, 6), grad=(0.1, 0.7))      # the pouch
	p.rock((0.3, 0.26, 0.22), (0, 0, 0.24), STONE_LIGHT, jitter=0.05)
	for side in (-1, 1):                                                           # two cords, one ending in a loop
		pts = [(side * 0.3, 0, 0.12), (side * 0.6, 0.15, 0.1), (side * 0.85, 0.4, 0.08), (side * 0.95, 0.7, 0.06)]
		for a0, a1 in zip(pts, pts[1:]):
			p.seg(a0, a1, 0.05, 0.05, WOOD, sides=5)
	for k in range(8):
		a0, a1 = k * math.tau / 8, (k + 1) * math.tau / 8
		p.seg((0.95 + math.cos(a0) * 0.1, 0.8 + math.sin(a0) * 0.1, 0.06), (0.95 + math.cos(a1) * 0.1, 0.8 + math.sin(a1) * 0.1, 0.06), 0.045, 0.045, WOOD, sides=5)
	return p.build()


def _trousers(p, cloth, band, leg_r=0.2, flare=0.02):
	"""A pair of trousers laid out flat, facing the camera: waistband, seat, two legs."""
	p.box((0.72, 0.26, 0.14), (0, 0, 1.0), band, grad=(0.1, 0.6))                  # waistband
	p.box((0.66, 0.24, 0.3), (0, 0, 0.8), cloth, grad=(0.1, 0.7))                   # seat
	for x in (-1, 1):
		p.seg((x * 0.17, 0, 0.72), (x * 0.24, 0, 0.0), leg_r, leg_r + flare, cloth, sides=10, grad=(0.1, 0.8))


def patchwork_pants():
	p = Prop("patchwork_pants", 241)
	_trousers(p, WOOD, HIDE)
	for (x, z, sw) in [(-0.2, 0.45, CLOTH_WHITE), (0.24, 0.25, CLOTH_RED), (-0.12, 0.85, CLOTH_WHITE)]:  # the patches
		p.box((0.16, 0.05, 0.16), (x, -0.2, z), sw, rot=(0, 12, 0))
	return p.build()


def leather_leggings():
	p = Prop("leather_leggings", 243)
	_trousers(p, HIDE, WOOD)
	for x in (-1, 1):                                                              # knee pads and a strap each
		p.blob((0.2, 0.1, 0.16), (x * 0.2, -0.2, 0.38), WOOD, segs=(8, 5))
		p.seg((x * 0.35, 0, 0.18), (x * 0.1, 0, 0.18), 0.03, 0.03, WOOD, sides=5)
	p.box((0.1, 0.06, 0.08), (0, -0.15, 1.0), GOLD)                                 # buckle
	return p.build()


def iron_greaves():
	p = Prop("iron_greaves", 245)
	_trousers(p, STONE_LIGHT, HIDE, leg_r=0.21, flare=0.03)
	for x in (-1, 1):
		for z in (0.62, 0.42, 0.16):                                               # plate bands
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.05), 0.235, 0.24, IRON, sides=10)
		p.blob((0.22, 0.12, 0.2), (x * 0.21, -0.18, 0.38), STONE_LIGHT, segs=(8, 6))   # knee cop
	p.box((0.74, 0.28, 0.08), (0, 0, 1.05), HIDE)                                   # leather belt under the plate
	return p.build()


def wolf_pelt():
	p = Prop("wolf_pelt", 251)
	p.blob((1.1, 0.8, 0.12), (0, 0, 0.06), WOOD_GRAY, segs=(12, 6), grad=(0.0, 0.5), jitter=0.05)
	for x in (-1, 1):
		p.blob((0.3, 0.22, 0.1), (x * 0.4, 0.32, 0.05), WOOD_GRAY, segs=(6, 4), grad=(0.0, 0.5))
		p.blob((0.3, 0.22, 0.1), (x * 0.4, -0.32, 0.05), WOOD_GRAY, segs=(6, 4), grad=(0.0, 0.5))
	p.blob((0.34, 0.2, 0.12), (-0.55, 0, 0.1), STONE_LIGHT, segs=(8, 5))              # the head end
	p.seg((0.5, 0, 0.08), (0.9, 0.1, 0.06), 0.1, 0.04, WOOD_GRAY, sides=6)           # tail
	return p.build()


def dire_wolf_fang():
	p = Prop("dire_wolf_fang", 253)
	p.seg((0, 0, 0), (0.12, 0, 1.0), 0.2, 0.0, BONE, sides=7, grad=(0.0, 0.7))
	p.seg((0, 0, -0.05), (0, 0, 0.08), 0.21, 0.2, CLOTH_RED, sides=7)
	return p.build()


def bear_claw():
	p = Prop("bear_claw", 255)
	for k in range(3):
		x = -0.3 + k * 0.3
		p.seg((x, 0, 0.1), (x + 0.15, -0.1, 0.8), 0.1, 0.0, BONE, sides=6, grad=(0.0, 0.6))
	p.blob((1.0, 0.5, 0.35), (0, 0.1, 0.1), STONE_DARK, segs=(10, 6))
	return p.build()


def bear_hide():
	p = Prop("bear_hide", 257)
	p.box((0.95, 0.7, 0.16), (0, 0, 0.08), STONE_DARK, grad=(0.1, 0.7))
	p.box((0.9, 0.66, 0.14), (0.04, 0.03, 0.22), STONE_DARK, rot=(0, 0, 5), grad=(0.0, 0.6))
	p.seg((-0.5, -0.3, 0.3), (0.5, -0.3, 0.3), 0.04, 0.04, HIDE, sides=5)             # a tie
	return p.build()


def spider_silk():
	p = Prop("spider_silk", 259)
	p.blob((0.8, 0.7, 0.75), (0, 0, 0.38), CLOTH_WHITE, segs=(12, 8), grad=(0.0, 0.5))
	for k in range(5):                                                             # wound strands
		z = 0.12 + k * 0.13
		r = 0.42 - abs(k - 2) * 0.05
		for j in range(10):
			a0, a1 = j * math.tau / 10, (j + 1) * math.tau / 10
			p.seg((math.cos(a0) * r, math.sin(a0) * r * 0.9, z), (math.cos(a1) * r, math.sin(a1) * r * 0.9, z + 0.02), 0.02, 0.02, STONE_LIGHT, sides=3)
	return p.build()


def venom_sac():
	p = Prop("venom_sac", 261)
	p.blob((0.7, 0.62, 0.7), (0, 0, 0.35), LEAF, segs=(12, 8), grad=(0.0, 0.5), glow=0.8)
	p.seg((0, 0, 0.68), (0.1, -0.05, 0.95), 0.1, 0.05, CLOTH_RED, sides=6)
	return p.build()


def orc_tusk():
	p = Prop("orc_tusk", 263)
	pts = [(0, 0, 0), (0.1, 0, 0.35), (0.25, 0, 0.65), (0.48, 0, 0.85)]
	for i, (a0, a1) in enumerate(zip(pts, pts[1:])):
		p.seg(a0, a1, 0.2 - i * 0.06, 0.14 - i * 0.05, BONE, sides=7, grad=(0.0, 0.6))
	p.seg((0, 0, -0.08), (0, 0, 0.06), 0.21, 0.2, HIDE, sides=7)
	return p.build()


def hollow_watch_signet():
	p = Prop("hollow_watch_signet", 265)
	_ring(p, IRON, stone=WATER)
	return p.build()



def grolthars_tusk_necklace():
	p = Prop("grolthars_tusk_necklace", 267)
	_cord(p, 0.55, 0.6, HIDE)
	for k in range(7):  # a string of long curved tusks
		a = math.radians(-75 + k * 25)
		x, y = math.sin(a) * 0.5, -math.cos(a) * 0.3
		p.seg((x, y, 0.45), (x * 1.12, y * 1.12, 0.05), 0.07, 0.0, BONE, sides=6, grad=(0.0, 0.6))
	p.blob((0.12, 0.1, 0.12), (0, -0.33, 0.47), CLOTH_RED, segs=(8, 6))  # a red bead at the middle
	return p.build()


def hollow_watch_pendant():
	p = Prop("hollow_watch_pendant", 269)
	_cord(p, 0.5, 0.75, IRON)
	p.seg((0, -0.32, 0.64), (0, -0.36, 0.64), 0.2, 0.2, IRON, sides=6)  # an iron hexagon
	p.blob((0.12, 0.08, 0.12), (0, -0.4, 0.64), WATER, segs=(8, 6), glow=0.6)  # the Watch's pale stone
	return p.build()


# ---------------------------------------------------------------- Hollowmere

def mire_toad_skin():
	p = Prop("mire_toad_skin", 271)
	p.blob((1.1, 0.85, 0.12), (0, 0, 0.06), LEAF, segs=(12, 6), grad=(0.2, 0.8), jitter=0.05)
	for k in range(9):  # warts
		a = k * 2.4
		p.blob((0.12, 0.12, 0.08), (math.cos(a) * 0.35 * (k % 3 + 1) / 3, math.sin(a) * 0.28 * (k % 3 + 1) / 3, 0.13), WOOD, segs=(6, 4))
	for x in (-1, 1):
		p.seg((x * 0.45, 0.3, 0.05), (x * 0.75, 0.55, 0.03), 0.08, 0.05, LEAF, sides=5)
		p.seg((x * 0.45, -0.3, 0.05), (x * 0.7, -0.5, 0.03), 0.08, 0.05, LEAF, sides=5)
	return p.build()


def leech_teeth():
	p = Prop("leech_teeth", 273)
	for k in range(10):  # a ring of little hooked teeth, still in their pink rim
		a0, a1 = k * math.tau / 10, (k + 1) * math.tau / 10
		p.seg((math.cos(a0) * 0.42, math.sin(a0) * 0.42, 0.1), (math.cos(a1) * 0.42, math.sin(a1) * 0.42, 0.1), 0.1, 0.1, CLOTH_RED, sides=6)
		p.seg((math.cos(a0) * 0.36, math.sin(a0) * 0.36, 0.16), (math.cos(a0) * 0.2, math.sin(a0) * 0.2, 0.42), 0.06, 0.0, BONE, sides=4)
	return p.build()


def turtle_shell_plate():
	p = Prop("turtle_shell_plate", 275)
	p.poly([(0, 0.55, 0.1), (0.5, 0.25, 0.14), (0.45, -0.35, 0.1), (-0.05, -0.55, 0.08), (-0.5, -0.2, 0.12), (-0.4, 0.35, 0.1)],
		   [(0, 1, 2, 3, 4, 5)], WOOD_GRAY, grad=(0.2, 0.9))
	p.blob((0.9, 0.95, 0.3), (0, 0, 0.1), STONE_DARK, segs=(6, 4), grad=(0.1, 0.8))
	p.blob((0.3, 0.3, 0.12), (0.05, 0.02, 0.24), LEAF, segs=(6, 4))  # moss
	return p.build()


def mirescale_scale():
	p = Prop("mirescale_scale", 277)
	p.poly([(0, 0.6, 0.02), (0.38, 0.1, 0.1), (0.25, -0.45, 0.06), (0, -0.6, 0.02), (-0.25, -0.45, 0.06), (-0.38, 0.1, 0.1)],
		   [(0, 1, 2, 3, 4, 5)], LEAF, grad=(0.0, 0.7))
	p.seg((0, 0.55, 0.1), (0, -0.55, 0.1), 0.05, 0.03, WOOD, sides=4)  # the ridge
	return p.build()


def waterlogged_locket():
	p = Prop("waterlogged_locket", 279)
	_cord(p, 0.5, 0.75, WOOD_GRAY)
	p.blob((0.46, 0.14, 0.52), (0, -0.3, 0.3), IRON, segs=(10, 6), grad=(0.1, 0.9))
	p.blob((0.16, 0.08, 0.16), (0.08, -0.38, 0.38), LEAF, segs=(6, 4))  # weed stuck to it
	p.seg((0.0, -0.38, 0.55), (-0.2, -0.36, 0.1), 0.03, 0.02, LEAF, sides=3)
	return p.build()


def snapjaws_shell():
	p = Prop("snapjaws_shell", 281)
	p.blob((1.3, 1.1, 0.55), (0, 0, 0.25), STONE_DARK, segs=(10, 6), grad=(0.1, 0.9))
	for k in range(5):  # ridge spikes
		p.seg((0, -0.4 + k * 0.2, 0.5), (0, -0.4 + k * 0.2, 0.78), 0.08, 0.0, WOOD_GRAY, sides=4)
	for x in (-0.35, 0.35):
		for k in range(3):
			p.seg((x, -0.3 + k * 0.3, 0.42), (x * 1.1, -0.3 + k * 0.3, 0.6), 0.06, 0.0, WOOD_GRAY, sides=4)
	p.blob((0.35, 0.3, 0.12), (-0.25, 0.1, 0.52), LEAF, segs=(6, 4))
	return p.build()


def drowned_bell():
	p = Prop("drowned_bell", 283)
	p.seg((0, 0, 0.0), (0, 0, 0.75), 0.42, 0.22, IRON, sides=12, grad=(0.1, 0.9))
	p.seg((0, 0, -0.04), (0, 0, 0.04), 0.46, 0.44, IRON, sides=12)
	p.blob((0.2, 0.2, 0.18), (0, 0, 0.82), IRON, segs=(8, 5))
	for k in range(6):  # weed and verdigris
		a = k * 1.1
		p.blob((0.14, 0.08, 0.2), (math.cos(a) * 0.36, math.sin(a) * 0.36, 0.3 + (k % 3) * 0.12), LEAF, segs=(5, 4))
	p.seg((0, 0, 0.9), (0, 0, 1.1), 0.05, 0.05, WOOD_GRAY, sides=5)  # a scrap of rope
	return p.build()


def smoked_mereperch():
	p = Prop("smoked_mereperch", 285)
	p.blob((1.0, 0.35, 0.28), (0, 0, 0.14), WOOD, segs=(10, 6), grad=(0.1, 0.8))
	p.poly([(0.45, 0, 0.14), (0.8, 0.2, 0.2), (0.8, -0.2, 0.2)], [(0, 1, 2)], WOOD)  # tail
	p.blob((0.08, 0.08, 0.08), (-0.38, -0.1, 0.2), STONE_DARK, segs=(5, 4))  # eye
	p.seg((-0.2, 0, 0.3), (0.3, 0, 0.3), 0.02, 0.02, HIDE, sides=3)  # the smoking string
	return p.build()


def pearl_of_the_mere():
	p = Prop("pearl_of_the_mere", 287)
	_cord(p, 0.5, 0.75, WOOD_GRAY)
	p.blob((0.4, 0.38, 0.4), (0, -0.3, 0.28), CLOTH_WHITE, segs=(12, 8), grad=(0.0, 0.4), glow=0.4)
	p.seg((0, -0.3, 0.5), (0, -0.3, 0.62), 0.07, 0.07, GOLD, sides=6)
	return p.build()


def scaled_leggings():
	p = Prop("scaled_leggings", 289)
	_trousers(p, LEAF, WOOD)
	for x in (-1, 1):
		for z in (0.6, 0.42, 0.24):
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.06), 0.225, 0.23, LEAF, sides=8, grad=(0.0, 0.6))
	return p.build()


# ---------------------------------------------------------------- Harrowfield

def boar_tusk():
	p = Prop("boar_tusk", 291)
	pts = [(0, 0, 0), (0.12, 0, 0.3), (0.3, 0, 0.55), (0.55, 0, 0.66)]
	for i, (a0, a1) in enumerate(zip(pts, pts[1:])):
		p.seg(a0, a1, 0.14 - i * 0.04, 0.1 - i * 0.035, BONE, sides=7, grad=(0.0, 0.6))
	return p.build()


def boar_hide():
	p = Prop("boar_hide", 293)
	p.blob((1.1, 0.8, 0.12), (0, 0, 0.06), WOOD_GRAY, segs=(12, 6), grad=(0.1, 0.7), jitter=0.05)
	for k in range(7):  # the bristle ridge down the back
		p.seg((-0.4 + k * 0.13, 0, 0.1), (-0.4 + k * 0.13, 0, 0.3), 0.04, 0.0, STONE_DARK, sides=3)
	return p.build()


def brigand_armband():
	p = Prop("brigand_armband", 295)
	for k in range(12):
		a0, a1 = k * math.tau / 12, (k + 1) * math.tau / 12
		p.seg((math.cos(a0) * 0.4, math.sin(a0) * 0.4, 0.2), (math.cos(a1) * 0.4, math.sin(a1) * 0.4, 0.2), 0.14, 0.14, CLOTH_RED, sides=6)
	p.box((0.2, 0.3, 0.06), (0.42, 0, 0.12), CLOTH_RED, rot=(0, 30, 0))  # the knot's tails
	return p.build()


def garricks_ledger():
	p = Prop("garricks_ledger", 297)
	p.box((0.8, 1.0, 0.18), (0, 0, 0.09), HIDE, grad=(0.2, 0.9))
	p.box((0.74, 0.94, 0.12), (0.03, 0, 0.12), CLOTH_WHITE, grad=(0.3, 0.6))
	p.box((0.8, 0.08, 0.2), (0, 0.3, 0.1), CLOTH_RED)  # a strap
	return p.build()


def straw_heart():
	p = Prop("straw_heart", 299)
	for s_ in (-1, 1):
		p.blob((0.45, 0.35, 0.45), (s_ * 0.18, 0, 0.55), GOLD, segs=(8, 6), jitter=0.03)
	p.seg((0, 0, 0.1), (0, 0, 0.6), 0.35, 0.05, GOLD, sides=8)
	for k in range(4):  # red thread wound round it
		p.seg((-0.4, 0, 0.3 + k * 0.1), (0.4, 0, 0.35 + k * 0.1), 0.02, 0.02, CLOTH_RED, sides=3)
	return p.build()


def loaf_of_bread():
	p = Prop("loaf_of_bread", 301)
	p.blob((1.0, 0.55, 0.45), (0, 0, 0.22), WOOD, segs=(10, 6), grad=(0.0, 0.7))
	for k in range(3):
		p.box((0.06, 0.4, 0.04), (-0.25 + k * 0.25, 0, 0.44), CLOTH_WHITE, rot=(0, 0, 20))
	return p.build()


def harvest_band():
	p = Prop("harvest_band", 303)
	_ring(p, GOLD, stone=LEAF)
	return p.build()


# ---------------------------------------------------------------- Sunward Steps

def ram_horn():
	p = Prop("ram_horn", 305)
	pts = []
	for k in range(9):  # a curling spiral
		a = k * 0.8
		r = 0.5 - k * 0.04
		pts.append((math.cos(a) * r, 0, 0.55 + math.sin(a) * r))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.17 - i * 0.015, 0.155 - i * 0.015, BONE, sides=7, grad=(0.1, 0.7))
	return p.build()


def ram_fleece():
	p = Prop("ram_fleece", 307)
	for k in range(9):
		p.blob((0.4, 0.35, 0.22), (math.cos(k * 2.1) * 0.35 * (k % 3) / 2.0, math.sin(k * 2.1) * 0.3 * (k % 3) / 2.0, 0.12), CLOTH_WHITE, segs=(8, 5), grad=(0.1, 0.6))
	return p.build()


def sunhawk_feather():
	p = Prop("sunhawk_feather", 309)
	p.seg((0, 0, 0), (0.1, 0, 1.1), 0.03, 0.01, WOOD, sides=4)
	p.poly([(0.02, 0, 0.25), (0.35, 0, 0.55), (0.28, 0, 1.0), (0.1, 0, 1.12), (-0.18, 0, 0.8), (-0.12, 0, 0.35)], [(0, 1, 2, 3, 4, 5)], GOLD, grad=(0.0, 0.8))
	p.box((0.3, 0.02, 0.15), (0.12, 0, 1.0), EMBER)
	return p.build()


def sunstone_shard():
	p = Prop("sunstone_shard", 311)
	p.seg((0, 0, 0), (0.1, 0, 0.9), 0.3, 0.0, GOLD, sides=5, glow=1.4)
	p.seg((0.25, 0.1, 0), (0.35, 0.1, 0.5), 0.18, 0.0, GOLD, sides=5, glow=1.2)
	return p.build()


def linen_wrappings():
	p = Prop("linen_wrappings", 313)
	for k in range(4):
		p.seg((-0.4, 0, 0.1 + k * 0.14), (0.4, 0, 0.14 + k * 0.14), 0.12, 0.12, CLOTH_WHITE, sides=8, grad=(0.2, 0.7))
	p.box((0.12, 0.3, 0.7), (0.45, 0, 0.2), CLOTH_WHITE, rot=(0, 20, 0))  # a loose end
	return p.build()


def pilgrim_token():
	p = Prop("pilgrim_token", 315)
	p.seg((0, -0.05, 0.45), (0, 0.05, 0.45), 0.42, 0.42, STONE_WARM, sides=14)
	p.seg((0, -0.08, 0.45), (0, -0.1, 0.45), 0.2, 0.2, GOLD, sides=12, glow=0.4)
	p.seg((0, 0, 0.9), (0, 0, 1.1), 0.04, 0.04, WOOD_GRAY, sides=4)
	return p.build()


def cult_sigil():
	p = Prop("cult_sigil", 317)
	p.seg((0, -0.04, 0.5), (0, 0.04, 0.5), 0.3, 0.3, CLOTH_RED, sides=12)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.3, 0, 0.5 + math.sin(a) * 0.3), (math.cos(a) * 0.55, 0, 0.5 + math.sin(a) * 0.55), 0.07, 0.0, EMBER, sides=3)
	return p.build()


def sun_scarab():
	p = Prop("sun_scarab", 319)
	p.blob((0.7, 0.9, 0.35), (0, 0, 0.18), GOLD, segs=(10, 6), glow=0.6)
	p.blob((0.4, 0.3, 0.25), (0, -0.5, 0.18), GOLD, segs=(8, 5), glow=0.4)
	p.box((0.03, 0.8, 0.02), (0, 0.05, 0.36), STONE_DARK)
	for s_ in (-1, 1):
		for k in range(3):
			p.seg((s_ * 0.3, -0.2 + k * 0.25, 0.1), (s_ * 0.55, -0.25 + k * 0.3, 0.0), 0.04, 0.03, GOLD, sides=4)
	return p.build()


def hierophants_mask():
	p = Prop("hierophants_mask", 321)
	p.blob((0.7, 0.2, 0.85), (0, 0, 0.55), GOLD, segs=(10, 8), glow=0.5)
	for s_ in (-1, 1):
		p.blob((0.14, 0.1, 0.1), (s_ * 0.16, -0.1, 0.62), STONE_DARK, segs=(6, 4))
	for k in range(12):
		a = k * math.tau / 12
		p.seg((math.cos(a) * 0.42, 0.02, 0.55 + math.sin(a) * 0.48), (math.cos(a) * 0.72, 0.02, 0.55 + math.sin(a) * 0.8), 0.06, 0.0, EMBER, sides=3)
	return p.build()


def dawn_tusk_pendant():
	p = Prop("dawn_tusk_pendant", 323)
	_cord(p, 0.5, 0.75, GOLD)
	p.seg((0, -0.3, 0.55), (0.15, -0.34, 0.1), 0.1, 0.02, BONE, sides=6)  # a tusk
	p.seg((0, -0.32, 0.62), (0, -0.36, 0.62), 0.16, 0.16, GOLD, sides=12, glow=0.6)  # and a small sun
	return p.build()


# ---------------------------------------------------------------- The Bleach

def _stinger(p, swatch, scale=1.0, glow=0.0):
	pts = [(0, 0, 0.1), (0.25, 0, 0.35), (0.35, 0, 0.7), (0.2, 0, 1.0), (-0.05, 0, 1.08)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		a = tuple(c * scale for c in a)
		b = tuple(c * scale for c in b)
		p.seg(a, b, (0.16 - i * 0.03) * scale, (0.13 - i * 0.03) * scale, swatch, sides=7, grad=(0.1, 0.7), glow=glow)
	tip = tuple(c * scale for c in (-0.05, 0, 1.08))
	p.seg(tip, (-0.3 * scale, 0, 0.85 * scale), 0.05 * scale, 0.0, BONE, sides=5)


def chitin_plate():
	p = Prop("chitin_plate", 325)
	p.blob((0.9, 0.7, 0.18), (0, 0, 0.1), STONE_WARM, segs=(10, 6), grad=(0.1, 0.7))
	for k in range(3):  # ridges across the plate
		p.seg((-0.4, -0.3 + k * 0.3, 0.2), (0.4, -0.3 + k * 0.3, 0.2), 0.04, 0.04, CLAY, sides=5)
	return p.build()


def scorpion_stinger():
	p = Prop("scorpion_stinger", 327)
	_stinger(p, CLAY)
	return p.build()


def queens_stinger():
	p = Prop("queens_stinger", 329)
	_stinger(p, CLOTH_RED, scale=1.25, glow=0.4)
	return p.build()


def bleached_bone():
	p = Prop("bleached_bone", 331)
	p.seg((-0.55, 0, 0.3), (0.55, 0, 0.5), 0.1, 0.1, BONE, sides=8)
	for x, z in ((-0.6, 0.3), (0.6, 0.5)):
		for s_ in (-1, 1):
			p.blob((0.16, 0.16, 0.16), (x, s_ * 0.08, z + 0.08), BONE, segs=(7, 5))
	return p.build()


def salt_crystal():
	p = Prop("salt_crystal", 333)
	for (x, y, h, r) in ((0, 0, 0.9, 0.2), (0.22, 0.1, 0.55, 0.14), (-0.2, 0.05, 0.6, 0.15), (0.05, -0.2, 0.45, 0.12)):
		p.seg((x, y, 0), (x * 1.3, y * 1.3, h), r, 0.0, CLOTH_WHITE, sides=6, glow=0.2)
	return p.build()


def raider_scarf():
	p = Prop("raider_scarf", 335)
	for k in range(5):
		p.seg((-0.5, 0, 0.12 + k * 0.1), (0.5, 0, 0.16 + k * 0.1), 0.09, 0.09, STONE_WARM, sides=8, grad=(0.2, 0.7))
	p.box((0.18, 0.04, 0.6), (0.55, 0, 0.1), STONE_WARM, rot=(0, 25, 0))  # a trailing end
	p.box((0.18, 0.05, 0.05), (0.55, 0, -0.18), CLOTH_RED, rot=(0, 25, 0))
	return p.build()


def raider_warhorn():
	p = Prop("raider_warhorn", 337)
	pts = [(-0.6, 0, 0.3), (-0.2, 0, 0.2), (0.2, 0, 0.3), (0.5, 0, 0.6)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.06 + i * 0.07, 0.12 + i * 0.08, BONE, sides=10, grad=(0.1, 0.7))
	for a, b, r in (((-0.24, 0, 0.21), (-0.16, 0, 0.2), 0.16), ((0.3, 0, 0.36), (0.36, 0, 0.44), 0.24)):  # gold bands round the horn
		p.seg(a, b, r, r, GOLD, sides=10)
	return p.build()


def titans_heart():
	p = Prop("titans_heart", 339)
	p.blob((0.55, 0.5, 0.6), (0, 0, 0.5), BONE, segs=(10, 8), jitter=0.05, grad=(0.1, 0.7))
	p.blob((0.3, 0.28, 0.32), (0, -0.25, 0.5), CLOTH_RED, segs=(8, 6), glow=1.2)
	for s_ in (-1, 1):  # stumps of great vessels
		p.seg((s_ * 0.2, 0, 0.9), (s_ * 0.3, 0, 1.15), 0.12, 0.1, BONE, sides=7)
	return p.build()


def bone_talisman():
	p = Prop("bone_talisman", 341)
	_cord(p, 0.5, 0.75, HIDE)
	p.box((0.3, 0.08, 0.45), (0, -0.32, 0.3), BONE)
	p.seg((0, -0.38, 0.35), (0, -0.4, 0.35), 0.08, 0.08, CLOTH_WHITE, sides=6, glow=0.5)
	return p.build()



# ---------------------------------------------------------------- the Long Monsoon

def _fish(p, body, fin, length=1.0, fat=0.3, spots=None):
	p.blob((length, fat * 0.8, fat * 1.6), (0, 0, 0.35), body, segs=(12, 6), grad=(0.1, 0.8))
	p.poly([(length * 0.45, 0, 0.35), (length * 0.75, 0, 0.62), (length * 0.75, 0, 0.08)], [(0, 1, 2)], fin)       # tail
	p.poly([(-0.15, 0, 0.35 + fat * 0.7), (0.2, 0, 0.35 + fat * 0.7), (0.05, 0, 0.35 + fat * 1.3)], [(0, 1, 2)], fin)  # dorsal fin
	p.blob((0.09, 0.05, 0.09), (-length * 0.36, -fat * 0.3, 0.42), STONE_DARK, segs=(6, 4))                          # eye
	for (x, z) in spots or []:
		p.blob((0.1, 0.04, 0.1), (x, -fat * 0.36, z), fin, segs=(6, 4))


def river_trout():
	p = Prop("river_trout", 343)
	_fish(p, STONE_LIGHT, CLOTH_RED, spots=[(0.0, 0.42), (0.15, 0.3), (-0.12, 0.3)])
	return p.build()


def mud_carp():
	p = Prop("mud_carp", 345)
	_fish(p, WOOD, HIDE, length=0.9, fat=0.38)
	return p.build()


def lagoon_snapper():
	p = Prop("lagoon_snapper", 347)
	_fish(p, CLOTH_RED, EMBER, length=0.95, fat=0.36)
	return p.build()


def monsoon_eel():
	p = Prop("monsoon_eel", 349)
	pts = [(-0.6, 0, 0.3), (-0.3, 0, 0.45), (0.0, 0, 0.3), (0.3, 0, 0.15), (0.6, 0, 0.3)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.11 - i * 0.015, 0.1 - i * 0.02, WATER, sides=7, grad=(0.1, 0.8))
	p.blob((0.04, 0.03, 0.04), (-0.62, -0.08, 0.34), STONE_DARK, segs=(6, 4))
	return p.build()


def jungle_catfish():
	p = Prop("jungle_catfish", 351)
	_fish(p, STONE_DARK, HIDE, length=1.05, fat=0.34)
	for s_ in (-1, 1):  # whiskers
		p.seg((-0.5, s_ * 0.08, 0.32), (-0.75, s_ * 0.2, 0.2), 0.015, 0.01, HIDE, sides=3)
	return p.build()


def rainbow_koi():
	p = Prop("rainbow_koi", 353)
	_fish(p, GOLD, CLOTH_RED, length=0.95, fat=0.32, spots=[(0.0, 0.45), (0.2, 0.32), (-0.15, 0.28)])
	p.blob((0.12, 0.02, 0.1), (0.1, -0.15, 0.4), WATER, segs=(6, 4), glow=0.8)
	return p.build()


def tattered_boot():
	p = Prop("tattered_boot", 355)
	p.seg((0, 0, 0.1), (0, 0, 0.75), 0.2, 0.22, HIDE, sides=8, grad=(0.1, 0.6))
	p.blob((0.4, 0.22, 0.14), (-0.22, 0, 0.1), HIDE, segs=(8, 5))
	p.blob((0.12, 0.05, 0.1), (-0.5, -0.05, 0.14), LEAF, segs=(6, 4))  # weed hanging off it
	return p.build()


def troll_tusk():
	p = Prop("troll_tusk", 357)
	p.seg((0, 0, 0.05), (0.2, 0, 0.6), 0.16, 0.08, BONE, sides=7, grad=(0.1, 0.7))
	p.seg((0.2, 0, 0.6), (0.1, 0, 0.95), 0.08, 0.0, BONE, sides=6)
	p.seg((0, 0, 0.02), (0, 0, 0.12), 0.18, 0.18, LEAF, sides=8)  # a mossy root
	return p.build()


def frog_skin():
	p = Prop("frog_skin", 359)
	p.blob((0.7, 0.55, 0.08), (0, 0, 0.1), GOLD, segs=(10, 6))
	for (x, y) in ((-0.3, 0.1), (0.15, -0.2), (0.25, 0.2), (-0.05, 0.0)):
		p.blob((0.1, 0.1, 0.03), (x, y, 0.17), STONE_DARK, segs=(6, 4))
	return p.build()


def croc_hide():
	p = Prop("croc_hide", 361)
	p.blob((0.8, 0.5, 0.1), (0, 0, 0.1), LEAF, segs=(10, 6), grad=(0.1, 0.5))
	for k in range(5):  # scutes
		p.box((0.12, 0.35, 0.08), (-0.4 + k * 0.2, 0, 0.2), STONE_DARK)
	return p.build()


def croc_tooth():
	p = Prop("croc_tooth", 363)
	p.seg((0, 0, 0.0), (0.05, 0, 0.9), 0.16, 0.0, BONE, sides=6, grad=(0.1, 0.7))
	return p.build()


def elemental_essence():
	p = Prop("elemental_essence", 365)
	p.blob((0.4, 0.4, 0.5), (0, 0, 0.45), WATER, segs=(10, 8), glow=1.4)
	p.seg((0, 0, 0.85), (0, 0, 1.1), 0.12, 0.12, STONE_LIGHT, sides=8)  # a stoppered vial of rain
	return p.build()


def gorraks_crown():
	p = Prop("gorraks_crown", 367)
	for k in range(8):  # a ring of river stones
		a = k * math.tau / 8
		p.blob((0.16, 0.16, 0.14), (math.cos(a) * 0.45, math.sin(a) * 0.45, 0.2), STONE_LIGHT if k % 2 else STONE_DARK, segs=(6, 4))
	for s_ in (-1, 1):  # antlers
		p.seg((s_ * 0.4, 0, 0.3), (s_ * 0.6, 0, 0.9), 0.05, 0.03, BONE, sides=5)
		p.seg((s_ * 0.52, 0, 0.65), (s_ * 0.3, 0, 0.95), 0.03, 0.02, BONE, sides=4)
	p.blob((0.18, 0.14, 0.16), (0, -0.46, 0.34), BONE, segs=(6, 5))  # a small skull at the front
	return p.build()


def heart_of_the_storm():
	p = Prop("heart_of_the_storm", 369)
	p.blob((0.45, 0.45, 0.5), (0, 0, 0.5), STONE_DARK, segs=(10, 8), jitter=0.05)
	for pts in (((-0.3, -0.3, 0.9), (-0.05, -0.35, 0.6), (-0.2, -0.38, 0.45)), ((0.3, -0.3, 0.3), (0.1, -0.36, 0.5), (0.25, -0.4, 0.7))):
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.04, 0.03, GOLD, sides=4, glow=2.2)
	return p.build()


def graveljaws_tooth():
	p = Prop("graveljaws_tooth", 371)
	p.seg((0, 0, 0.0), (0.12, 0, 1.1), 0.26, 0.0, BONE, sides=7, grad=(0.05, 0.6))
	p.blob((0.12, 0.05, 0.1), (0.02, -0.18, 0.35), LEAF, segs=(6, 4))  # moss
	return p.build()


def tide_trunk_charm():
	p = Prop("tide_trunk_charm", 373)
	_cord(p, 0.5, 0.75, WATER)
	p.blob((0.3, 0.12, 0.28), (0, -0.32, 0.4), STONE_LIGHT, segs=(8, 6))            # a little stone elephant head
	p.seg((0, -0.4, 0.35), (0.05, -0.45, 0.62), 0.05, 0.03, STONE_LIGHT, sides=5)    # trunk raised
	p.blob((0.08, 0.08, 0.08), (0.06, -0.46, 0.7), WATER, segs=(6, 4), glow=1.6)     # a drop of water
	return p.build()


# ---------------------------------------------------------------- tradeskills

AMBER = (1, 3)       # baked crust, fried food
ORANGE = (4, 2)      # spice, broth
PINK = (2, 2)        # raw meat
MOSS = PINE
LAVENDER = PETAL_PURPLE


def _frame(p, lo, hi):
	"""Two specks at opposite corners, too small to see, so a set of icons
	(small and large ore, the three healing potions) share one framing and
	their sizes compare."""
	p.blob((0.001, 0.001, 0.001), lo, STONE_DARK, segs=(3, 3))
	p.blob((0.001, 0.001, 0.001), hi, STONE_DARK, segs=(3, 3))


def _loop(p, center, radius, z_axis, r, swatch, n=14, squash=1.0, glow=0.0):
	"""A ring of segments round `center`, in the xy plane (z_axis) or the xz plane."""
	cx, cy, cz = center
	for k in range(n):
		a0, a1 = k * math.tau / n, (k + 1) * math.tau / n
		if z_axis:
			a = (cx + math.cos(a0) * radius, cy + math.sin(a0) * radius * squash, cz)
			b = (cx + math.cos(a1) * radius, cy + math.sin(a1) * radius * squash, cz)
		else:
			a = (cx + math.cos(a0) * radius, cy, cz + math.sin(a0) * radius * squash)
			b = (cx + math.cos(a1) * radius, cy, cz + math.sin(a1) * radius * squash)
		p.seg(a, b, r, r, swatch, sides=5, glow=glow)


# supplies

def bag_of_flour():
	p = Prop("bag_of_flour", 401)
	p.blob((0.95, 0.8, 0.8), (0, 0, 0.4), CLOTH_WHITE, segs=(12, 8), grad=(0.15, 0.95))
	_loop(p, (0, 0, 0.74), 0.36, True, 0.07, STONE_WARM, n=14, squash=0.85)       # rolled-down rim
	p.blob((0.62, 0.52, 0.26), (0, 0, 0.78), CLOTH_WHITE, segs=(10, 6), grad=(0.0, 0.3), glow=0.25)  # the flour heap
	for k in range(4):                                                             # a wheat sprig stamped on the front
		z = 0.22 + k * 0.1
		p.blob((0.08, 0.03, 0.12), (-0.05, -0.4, z), GOLD, rot=(0, 30, 0), segs=(6, 4))
		p.blob((0.08, 0.03, 0.12), (0.05, -0.4, z), GOLD, rot=(0, -30, 0), segs=(6, 4))
	p.box((0.025, 0.02, 0.5), (0, -0.39, 0.3), GOLD)
	return p.build()


def jar_of_spices():
	p = Prop("jar_of_spices", 403)
	p.seg((0, 0, 0), (0, 0, 0.55), 0.3, 0.38, CLAY, sides=12, grad=(0.1, 0.8))
	p.seg((0, 0, 0.55), (0, 0, 0.7), 0.38, 0.26, CLAY, sides=12)
	p.blob((0.62, 0.62, 0.22), (0, 0, 0.74), CLOTH_RED, segs=(12, 6), grad=(0.0, 0.6))  # cloth over the lid
	p.seg((0, 0, 0.66), (0, 0, 0.7), 0.29, 0.29, GOLD, sides=12)                   # its tie
	for k in range(5):                                                             # a pinch spilled in front
		a = k * 1.25
		p.rock((0.2, 0.18, 0.12), (0.45 + math.cos(a) * 0.12, -0.35 + math.sin(a) * 0.1, 0.05), ORANGE, jitter=0.1)
	p.seg((0.25, -0.55, 0.04), (0.75, -0.2, 0.04), 0.05, 0.05, WOOD, sides=6)       # a cinnamon stick
	return p.build()


def vial_of_water():
	p = Prop("vial_of_water", 405)
	p.seg((0, 0, 0.12), (0, 0, 1.0), 0.16, 0.16, RUNE, sides=10, grad=(0.0, 0.5), glow=0.35)  # a thin tube of water
	p.blob((0.32, 0.32, 0.26), (0, 0, 0.13), RUNE, segs=(10, 6), grad=(0.3, 0.6), glow=0.35)
	p.seg((0, 0, 0.95), (0, 0, 1.02), 0.2, 0.2, CLOTH_WHITE, sides=10)              # the lip
	p.seg((0, 0, 1.0), (0, 0, 1.16), 0.13, 0.15, WOOD, sides=8)                     # cork
	p.box((0.05, 0.02, 0.5), (-0.07, -0.16, 0.55), CLOTH_WHITE, glow=0.6)           # the glint on the glass
	return p.build()


def tanning_salts():
	p = Prop("tanning_salts", 407)
	p.seg((0, 0, 0), (0, 0, 0.42), 0.48, 0.55, WOOD, sides=14, grad=(0.1, 0.8))    # a little tub
	for z in (0.08, 0.34):
		p.seg((0, 0, z), (0, 0, z + 0.05), 0.5 + z * 0.16 + 0.01, 0.5 + z * 0.16 + 0.02, STONE_DARK, sides=14)
	for k in range(9):                                                             # heaped with coarse white salt
		a = k * 2.4
		r = 0.1 + (k % 3) * 0.14
		p.rock((0.28, 0.26, 0.22), (math.cos(a) * r, math.sin(a) * r, 0.48 + (0.12 if k < 3 else 0.0)), CLOTH_WHITE,
			   grad=(0.0, 0.5), jitter=0.12)
	return p.build()


def spool_of_thread():
	p = Prop("spool_of_thread", 409)
	p.seg((0, 0, 0), (0, 0, 0.1), 0.42, 0.42, WOOD, sides=14)                       # flanges
	p.seg((0, 0, 0.8), (0, 0, 0.9), 0.42, 0.42, WOOD, sides=14)
	p.seg((0, 0, 0.1), (0, 0, 0.8), 0.33, 0.33, CLOTH_RED, sides=14, grad=(0.0, 0.6))  # the thread
	for k in range(6):                                                             # wound turns
		z = 0.16 + k * 0.11
		p.seg((0, 0, z), (0, 0, z + 0.02), 0.345, 0.345, CLOTH_RED, sides=14, grad=(0.9, 1.0))
	pts = [(0.3, -0.18, 0.55), (0.55, -0.35, 0.35), (0.6, -0.5, 0.1), (0.45, -0.65, 0.02)]  # a loose end
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.025, 0.025, CLOTH_RED, sides=4)
	p.seg((-0.2, -0.28, 0.25), (-0.05, -0.3, 0.95), 0.025, 0.008, STONE_LIGHT, sides=4, glow=0.4)  # a needle stuck in
	return p.build()


def bundle_of_herbs():
	p = Prop("bundle_of_herbs", 411)
	tops = [(-0.45, 0.0, 0.95), (-0.2, 0.05, 1.1), (0.05, 0.0, 1.15), (0.3, 0.05, 1.05), (0.5, 0.0, 0.85), (-0.1, -0.1, 0.95), (0.2, -0.1, 0.9)]
	for k, t in enumerate(tops):
		p.seg((t[0] * 0.08, 0, 0), t, 0.03, 0.02, LEAF, sides=4)
		for j in range(3):                                                         # leaves up the stem
			f = 0.55 + j * 0.2
			x, y, z = t[0] * f, t[1] * f, t[2] * f
			sw = MOSS if (k + j) % 2 else LEAF
			p.blob((0.2, 0.06, 0.12), (x + (0.08 if j % 2 else -0.08), y - 0.05, z), sw, rot=(0, 35 if j % 2 else -35, 0), segs=(6, 4))
		if k in (1, 3, 5):                                                         # a few in flower
			p.blob((0.1, 0.1, 0.16), (t[0], t[1], t[2] + 0.05), LAVENDER, segs=(6, 4), grad=(0.0, 0.4))
	p.seg((0, 0, 0.2), (0, 0, 0.3), 0.1, 0.1, WOOD_GRAY, sides=8)                   # the twine
	return p.build()


def _ore(p, size, loc, seed_off, glints):
	p.rock(size, loc, STONE_DARK, grad=(0.0, 0.45), jitter=0.12)
	for k in range(glints):
		a = (k + seed_off) * 2.3
		x = loc[0] + math.cos(a) * size[0] * 0.3
		z = loc[2] + (0.1 + (k % 3) * 0.12) * size[2]
		p.blob((0.1, 0.06, 0.1), (x, loc[1] - size[1] * 0.42, z), EMBER, segs=(5, 4), glow=1.0)


def small_brick_of_ore():
	p = Prop("small_brick_of_ore", 413)
	_ore(p, (0.85, 0.7, 0.6), (0, 0, 0.3), 0, 4)
	_frame(p, (-0.7, -0.5, 0.0), (0.7, 0.5, 0.85))
	return p.build()


def large_brick_of_ore():
	p = Prop("large_brick_of_ore", 415)
	p.box((1.3, 0.95, 0.55), (0, 0, 0.3), STONE_DARK, grad=(0.0, 0.5), jitter=0.06)   # a squared block
	for k in range(6):
		x = -0.45 + k * 0.18
		p.blob((0.12, 0.07, 0.12), (x, -0.48, 0.15 + (k % 3) * 0.13), EMBER, segs=(5, 4), glow=1.0)
		p.blob((0.12, 0.12, 0.07), (x + 0.05, -0.2 + (k % 2) * 0.3, 0.58), EMBER, segs=(5, 4), glow=1.0)
	_ore(p, (0.45, 0.4, 0.35), (0.25, 0.1, 0.72), 2, 2)                               # a lump on top
	_frame(p, (-0.7, -0.5, 0.0), (0.7, 0.5, 0.85))
	return p.build()


def water_flask():
	p = Prop("water_flask", 417)
	p.seg((0, -0.15, 0.45), (0, 0.15, 0.45), 0.42, 0.42, STONE_LIGHT, sides=18, grad=(0.0, 0.7))  # a round tin canteen
	p.seg((0, -0.17, 0.45), (0, -0.13, 0.45), 0.22, 0.22, WATER, sides=16, glow=0.3)             # a blue boss on its face
	p.seg((0, -0.04, 0.45), (0, 0.04, 0.45), 0.45, 0.45, HIDE, sides=18)                          # stitched leather band
	p.seg((0, 0, 0.85), (0, 0, 1.0), 0.1, 0.12, STONE_LIGHT, sides=8)
	p.seg((0, 0, 1.0), (0, 0, 1.12), 0.09, 0.11, WOOD, sides=8)                                  # cork
	pts = [(-0.44, 0, 0.5), (-0.5, 0, 0.95), (-0.3, 0, 1.25), (0.0, 0, 1.33), (0.3, 0, 1.25), (0.5, 0, 0.95), (0.44, 0, 0.5)]
	for a, b in zip(pts, pts[1:]):                                                                # carrying strap
		p.seg(a, b, 0.035, 0.035, HIDE, sides=5)
	return p.build()


def bundle_of_shafts():
	p = Prop("bundle_of_shafts", 419)
	for k in range(9):
		dy = (k % 3 - 1) * 0.1
		dz = (k // 3 - 1) * 0.1
		p.seg((-0.7 + (k % 4) * 0.04, dy, 0.1 + dz), (0.62 - (k % 3) * 0.04, dy, 0.85 + dz), 0.05, 0.05, WOOD, sides=6, grad=(0.1, 0.5))
	for t in (0.28, 0.72):                                                         # two ties
		x, z = -0.68 + t * 1.3, 0.1 + t * 0.75
		p.seg((x - 0.04, 0, z - 0.03), (x + 0.04, 0, z + 0.03), 0.22, 0.22, CLOTH_RED, sides=10)
	return p.build()


def smithy_hammer():
	p = Prop("smithy_hammer", 421)
	p.seg((-0.25, 0, 0.0), (0.05, 0, 1.0), 0.06, 0.07, WOOD, sides=8, grad=(0.1, 0.6))      # haft
	p.seg((-0.24, 0, 0.03), (-0.17, 0, 0.3), 0.08, 0.08, HIDE, sides=8)                    # grip wrap
	p.box((0.62, 0.24, 0.24), (0.08, 0, 1.02), STONE_DARK, rot=(0, 16.7, 0), grad=(0.0, 0.6))  # the head
	p.seg((0.36, 0, 0.94), (0.46, 0, 0.91), 0.17, 0.17, STONE_LIGHT, sides=8)               # striking face
	p.seg((-0.2, 0, 1.12), (-0.38, 0, 1.18), 0.1, 0.02, STONE_DARK, sides=4)                # the peen
	return p.build()


def sewing_kit():
	p = Prop("sewing_kit", 423)
	p.box((1.05, 0.65, 0.34), (0, 0, 0.17), WOOD, grad=(0.1, 0.8))                         # a little box
	p.box((1.05, 0.06, 0.62), (0, 0.36, 0.58), WOOD, rot=(-18, 0, 0), grad=(0.1, 0.7))       # its lid, open
	p.box((0.12, 0.06, 0.1), (0, -0.34, 0.26), GOLD)                                         # latch
	for k, sw in enumerate((CLOTH_RED, RUNE, GOLD)):                                         # spools inside
		x = -0.3 + k * 0.22
		p.seg((x, 0.05, 0.3), (x, 0.05, 0.5), 0.09, 0.09, sw, sides=10)
		p.seg((x, 0.05, 0.49), (x, 0.05, 0.53), 0.11, 0.11, WOOD_GRAY, sides=10)
	p.blob((0.3, 0.3, 0.24), (0.33, -0.05, 0.42), CLOTH_RED, segs=(10, 6), grad=(0.0, 0.6))  # pincushion
	for k in range(3):
		a = k * 1.1 - 1.1
		p.seg((0.33 + math.sin(a) * 0.05, -0.05, 0.5), (0.33 + math.sin(a) * 0.25, -0.1, 0.8), 0.02, 0.006, STONE_LIGHT, sides=4, glow=0.4)
		p.blob((0.05, 0.05, 0.05), (0.33 + math.sin(a) * 0.25, -0.1, 0.8), CLOTH_WHITE, segs=(5, 4))
	return p.build()


def mortar_and_pestle():
	p = Prop("mortar_and_pestle", 425)
	p.seg((0, 0, 0), (0, 0, 0.1), 0.32, 0.36, STONE_LIGHT, sides=14)
	p.seg((0, 0, 0.1), (0, 0, 0.5), 0.36, 0.55, STONE_LIGHT, sides=14, grad=(0.0, 0.8))    # the bowl
	p.seg((0, 0, 0.49), (0, 0, 0.51), 0.46, 0.46, STONE_DARK, sides=14)                    # its dark hollow
	for k in range(5):                                                                     # herbs being ground
		a = k * 1.3
		p.blob((0.14, 0.1, 0.06), (math.cos(a) * 0.22, math.sin(a) * 0.2, 0.52), LEAF, segs=(6, 4))
	p.seg((-0.15, 0.05, 0.42), (0.35, -0.05, 1.1), 0.07, 0.1, STONE_WARM, sides=10, grad=(0.0, 0.6))  # pestle
	p.blob((0.22, 0.22, 0.22), (0.36, -0.05, 1.12), STONE_WARM, segs=(8, 6))
	return p.build()


# recipe books: a standing book, cover to the camera, pages on the right

def _book(p, cover, trim=GOLD):
	p.box((0.84, 0.05, 1.08), (0, -0.12, 0.54), cover, grad=(0.1, 0.7))    # front cover
	p.box((0.84, 0.05, 1.08), (0, 0.12, 0.54), cover, grad=(0.2, 0.8))     # back cover
	p.box((0.08, 0.29, 1.08), (-0.4, 0, 0.54), cover, grad=(0.1, 0.8))     # spine
	p.box((0.78, 0.2, 1.0), (0.0, 0, 0.54), CLOTH_WHITE, grad=(0.2, 0.7))  # pages
	for x in (-0.36, 0.36):                                                 # metal corners
		for z in (0.06, 1.02):
			p.box((0.14, 0.07, 0.14), (x, -0.13, z), trim)
	p.box((0.84, 0.07, 0.05), (0, -0.13, 0.2), trim)                        # bands across the cover
	p.box((0.84, 0.07, 0.05), (0, -0.13, 0.88), trim)


def hearthside_cookbook():
	p = Prop("hearthside_cookbook", 427)
	_book(p, CLOTH_RED)
	p.blob((0.46, 0.08, 0.28), (0, -0.17, 0.55), AMBER, segs=(10, 6), grad=(0.0, 0.6))     # a loaf
	for k in range(3):
		p.box((0.04, 0.03, 0.18), (-0.12 + k * 0.12, -0.21, 0.58), CLOTH_WHITE, rot=(0, 25, 0))
	return p.build()


def tailors_pattern_book():
	p = Prop("tailors_pattern_book", 429)
	_book(p, WATER, trim=STONE_LIGHT)
	p.seg((-0.22, -0.17, 0.3), (0.22, -0.17, 0.8), 0.035, 0.008, CLOTH_WHITE, sides=5, glow=0.5)  # a needle
	_loop(p, (0.19, -0.17, 0.72), 0.045, False, 0.012, CLOTH_WHITE, n=6)
	pts = [(0.19, -0.18, 0.72), (0.3, -0.18, 0.6), (0.05, -0.18, 0.45), (0.25, -0.18, 0.32)]  # its thread
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.02, 0.02, GOLD, sides=4)
	return p.build()


def alchemists_notes():
	p = Prop("alchemists_notes", 431)
	_book(p, MOSS, trim=GOLD)
	p.blob((0.3, 0.08, 0.26), (0, -0.17, 0.46), RUNE, segs=(10, 6), glow=1.2)       # a flask
	p.box((0.09, 0.07, 0.2), (0, -0.17, 0.66), CLOTH_WHITE)
	p.box((0.14, 0.07, 0.04), (0, -0.17, 0.76), CLOTH_WHITE)
	for s_ in (-1, 1):                                                           # loose papers
		p.box((0.3, 0.02, 0.4), (0.3 * s_ + 0.1, -0.02, 0.9), CLOTH_WHITE, rot=(0, s_ * 20, 0))
	return p.build()


def smiths_handbook():
	p = Prop("smiths_handbook", 433)
	_book(p, STONE_DARK, trim=EMBER)
	p.seg((-0.12, -0.17, 0.3), (0.08, -0.17, 0.72), 0.03, 0.03, WOOD, sides=5)          # a hammer
	p.box((0.34, 0.08, 0.14), (0.1, -0.18, 0.72), EMBER, rot=(0, 25, 0), glow=0.9)
	return p.build()


# drops

def raw_meat():
	p = Prop("raw_meat", 435)
	tilt = Euler((math.radians(50), 0, math.radians(8)))

	def at(x, y, z):
		return tuple(tilt.to_matrix() @ Vector((x, y, z)) + Vector((0, 0, 0.45)))
	rot = (50, 0, 8)
	p.blob((1.15, 0.9, 0.3), at(0, 0, -0.04), CLOTH_WHITE, rot=rot, segs=(14, 6), grad=(0.1, 0.5))      # fat rind
	p.blob((1.05, 0.8, 0.32), at(-0.03, -0.02, 0.04), CLOTH_RED, rot=rot, segs=(14, 6), grad=(0.0, 0.7), jitter=0.02)
	for k in range(4):                                                               # marbling
		p.box((0.28, 0.05, 0.03), at(-0.32 + k * 0.17, -0.18 + (k % 2) * 0.28, 0.2), PINK, rot=(50, 0, 30 + k * 20))
	p.seg(at(0.24, 0.08, 0.1), at(0.24, 0.08, 0.26), 0.14, 0.14, BONE, sides=10)          # the bone
	p.seg(at(0.24, 0.08, 0.25), at(0.24, 0.08, 0.28), 0.07, 0.07, STONE_WARM, sides=8)
	return p.build()


def _frog_pair(p, swatch, flat=False, lift=0.0):
	"""Two frog legs joined at the hip: thigh, shin and a webbed foot each."""
	def at(x, h):
		return (x, h * 0.7 - 0.45, 0.14 + lift + (0.02 if h > 0.5 else 0.0)) if flat else (x, 0, h)
	p.blob((0.3, 0.22, 0.2) if not flat else (0.3, 0.2, 0.18), at(0, 1.0), swatch, segs=(8, 5))
	for s_ in (-1, 1):
		hip, knee, ankle = at(s_ * 0.08, 0.98), at(s_ * 0.42, 0.55), at(s_ * 0.18, 0.18)
		p.seg(hip, knee, 0.14, 0.1, swatch, sides=8, grad=(0.1, 0.7))
		p.blob((0.2, 0.18, 0.18), knee, swatch, segs=(6, 4))
		p.seg(knee, ankle, 0.09, 0.05, swatch, sides=7, grad=(0.1, 0.7))
		toes = [at(s_ * 0.12, -0.05), at(s_ * 0.28, -0.08), at(s_ * 0.4, 0.0)]
		for t in toes:
			p.seg(ankle, t, 0.03, 0.02, swatch, sides=4)
		p.poly([ankle] + toes, [(0, 1, 2), (0, 2, 3)], swatch)


def frog_legs():
	p = Prop("frog_legs", 437)
	_frog_pair(p, LEAF)
	return p.build()


# intermediates

def tanned_leather():
	p = Prop("tanned_leather", 439)
	p.poly([(-0.5, 0.0, 0.05), (0.5, 0.0, 0.05), (0.55, -0.35, 0.03), (0.35, -0.7, 0.02), (-0.2, -0.75, 0.02), (-0.55, -0.4, 0.03)],
		   [(0, 1, 2, 3, 4, 5)], HIDE, grad=(0.0, 0.3))                                     # the sheet, unrolled
	p.seg((-0.55, 0.1, 0.28), (0.55, 0.1, 0.28), 0.26, 0.26, HIDE, sides=14, grad=(0.0, 0.8))  # rolled up behind
	p.seg((0.55, 0.1, 0.28), (0.57, 0.1, 0.28), 0.18, 0.18, WOOD, sides=12)               # the end of the roll
	for x in (-0.3, 0.3):
		p.seg((x - 0.03, 0.1, 0.28), (x + 0.03, 0.1, 0.28), 0.28, 0.28, WOOD, sides=12)      # ties
	return p.build()


def thick_leather():
	p = Prop("thick_leather", 441)
	for k in range(3):                                                               # a folded stack
		p.box((1.1 - k * 0.06, 0.8 - k * 0.04, 0.14), (k * 0.03, k * 0.02, 0.07 + k * 0.15), MOSS, rot=(0, 0, k * 4 - 4), grad=(0.1, 0.7))
	for r in range(3):                                                               # rows of scutes on top
		for c in range(4):
			p.blob((0.18, 0.14, 0.1), (-0.36 + c * 0.24 + 0.06, -0.24 + r * 0.24 + 0.04, 0.43), LEAF, segs=(6, 4), grad=(0.0, 0.5))
	p.seg((-0.1, -0.45, 0.25), (-0.1, 0.45, 0.25), 0.05, 0.05, HIDE, sides=5)              # strap round the stack
	p.box((0.08, 0.9, 0.52), (-0.1, 0.0, 0.26), HIDE)
	return p.build()


def _bolt(p, cloth, grad=(0.0, 0.7), glow=0.0, stripe=None):
	p.seg((-0.6, 0.15, 0.36), (0.6, 0.15, 0.36), 0.34, 0.34, cloth, sides=16, grad=grad, glow=glow)   # the roll
	for x in (-0.62, 0.62):                                                               # the board it's wound on
		p.box((0.04, 0.2, 0.2), (x, 0.15, 0.36), WOOD)
	p.box((1.2, 0.5, 0.03), (0, -0.3, 0.02), cloth, grad=grad, glow=glow)                  # a length unrolled
	if stripe:
		for x in (-0.45, 0.45):
			p.seg((x, 0.15, 0.36), (x + 0.04, 0.15, 0.36), 0.35, 0.35, stripe, sides=16)
			p.box((0.04, 0.5, 0.035), (x, -0.3, 0.025), stripe)


def wool_cloth():
	p = Prop("wool_cloth", 443)
	_bolt(p, CLOTH_RED, stripe=CLOTH_WHITE)
	return p.build()


def silk_cloth():
	p = Prop("silk_cloth", 445)
	_bolt(p, LAVENDER, grad=(0.0, 0.3), glow=0.35, stripe=CLOTH_WHITE)
	return p.build()


def _ingot(p, swatch, grad=(0.0, 0.5)):
	w0, d0, w1, d1, h = 0.55, 0.26, 0.42, 0.17, 0.26
	vs = [(-w0, -d0, 0), (w0, -d0, 0), (w0, d0, 0), (-w0, d0, 0), (-w1, -d1, h), (w1, -d1, h), (w1, d1, h), (-w1, d1, h)]
	faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
	p.poly(vs, faces, swatch, grad=grad)
	p.box((0.18, 0.1, 0.01), (0, 0, h + 0.005), STONE_DARK if swatch != STONE_DARK else IRON)  # a maker's stamp


def iron_bar():
	p = Prop("iron_bar", 447)
	_ingot(p, WOOD_GRAY, grad=(0.0, 0.7))
	for (x, y) in ((-0.3, -0.27), (0.2, -0.27), (0.45, 0.0)):                             # rust
		p.blob((0.12, 0.04, 0.08), (x, y, 0.12), EMBER, segs=(6, 4), grad=(0.6, 0.9))
	return p.build()


def steel_bar():
	p = Prop("steel_bar", 449)
	_ingot(p, STONE_LIGHT, grad=(0.0, 0.45))
	p.box((0.7, 0.02, 0.04), (0, -0.22, 0.14), CLOTH_WHITE, glow=0.8)                       # a bright edge
	return p.build()


# food

def roast_meat():
	p = Prop("roast_meat", 451)
	p.blob((0.75, 0.62, 0.9), (-0.12, 0, 0.42), WOOD, rot=(0, 35, 0), segs=(12, 8), grad=(0.0, 0.9))  # the haunch
	p.blob((0.5, 0.42, 0.55), (-0.2, -0.12, 0.5), AMBER, rot=(0, 35, 0), segs=(10, 6), grad=(0.0, 0.8))  # glazed
	p.seg((0.15, 0, 0.65), (0.55, 0, 1.05), 0.09, 0.08, BONE, sides=8)                        # the bone
	for s_ in (-1, 1):
		p.blob((0.16, 0.16, 0.16), (0.58 + s_ * 0.05, s_ * 0.06, 1.08 - s_ * 0.05), BONE, segs=(7, 5))
	for k in range(3):                                                                    # char lines
		p.box((0.3, 0.03, 0.03), (-0.25 + k * 0.12, -0.36, 0.3 + k * 0.14), STONE_DARK, rot=(0, -30, 0))
	return p.build()


def _fish_at(p, body, fin, loc, s=1.0, fat=0.3):
	x0, y0, z0 = loc
	def at(x, y, z):
		return (x0 + x * s, y0 + y * s, z0 + z * s)
	p.blob((s, fat * 0.8 * s, fat * 1.6 * s), at(0, 0, 0), body, segs=(12, 6), grad=(0.1, 0.8))
	p.poly([at(0.45, 0, 0), at(0.75, 0, 0.27), at(0.75, 0, -0.27)], [(0, 1, 2)], fin)
	p.poly([at(-0.15, 0, fat * 0.7), at(0.2, 0, fat * 0.7), at(0.05, 0, fat * 1.2)], [(0, 1, 2)], fin)
	p.blob((0.09 * s, 0.05 * s, 0.09 * s), at(-0.36, -fat * 0.3, 0.07), STONE_DARK, segs=(6, 4))


def grilled_trout():
	p = Prop("grilled_trout", 453)
	p.box((1.5, 0.6, 0.08), (0.05, 0, 0.04), WOOD, grad=(0.1, 0.5))                             # a plank
	_fish_at(p, AMBER, EMBER, (0, 0, 0.35), fat=0.28)
	for k in range(4):                                                                     # grill marks
		p.box((0.04, 0.02, 0.36), (-0.25 + k * 0.17, -0.115, 0.36), STONE_DARK, rot=(0, 25, 0))
	p.blob((0.22, 0.14, 0.12), (-0.55, -0.15, 0.13), GOLD, segs=(8, 5), glow=0.3)             # a wedge of lemon
	p.blob((0.2, 0.1, 0.05), (0.55, -0.18, 0.1), LEAF, segs=(6, 4))                            # and a sprig
	return p.build()


def _bowl(p, swatch=WOOD, r=0.62, h=0.45):
	p.seg((0, 0, 0), (0, 0, 0.08), r * 0.45, r * 0.5, swatch, sides=14)
	p.seg((0, 0, 0.08), (0, 0, h), r * 0.55, r, swatch, sides=16, grad=(0.1, 0.8))


def fish_stew():
	p = Prop("fish_stew", 455)
	_bowl(p)
	p.seg((0, 0, 0.4), (0, 0, 0.43), 0.56, 0.56, ORANGE, sides=16, grad=(0.1, 0.3))          # the broth
	for k in range(6):                                                                     # fish and herbs in it
		a = k * 1.05
		sw = CLOTH_WHITE if k % 2 else LEAF
		p.blob((0.16, 0.12, 0.07), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.45), sw, segs=(6, 4))
	p.seg((0.1, 0.1, 0.42), (0.6, 0.35, 0.95), 0.04, 0.05, WOOD_GRAY, sides=6)             # a spoon
	for k in range(2):                                                                     # steam
		x = -0.15 + k * 0.3
		p.seg((x, 0, 0.55), (x + 0.08, 0, 0.8), 0.05, 0.02, CLOTH_WHITE, sides=5, glow=0.3)
		p.seg((x + 0.08, 0, 0.8), (x, 0, 1.0), 0.02, 0.0, CLOTH_WHITE, sides=5, glow=0.3)
	return p.build()


def hunters_pie():
	p = Prop("hunters_pie", 457)
	p.seg((0, 0, 0), (0, 0, 0.2), 0.62, 0.72, CLAY, sides=18)                                  # the dish
	p.blob((1.3, 1.3, 0.4), (0, 0, 0.22), AMBER, segs=(16, 8), grad=(0.0, 0.7))              # the crust
	_loop(p, (0, 0, 0.24), 0.64, True, 0.07, GOLD, n=16)                                      # crimped edge
	for k in range(3):                                                                     # vents
		a = k * math.tau / 3 + 0.3
		p.box((0.2, 0.04, 0.04), (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.42), WOOD, rot=(0, 0, math.degrees(a)))
	p.blob((0.16, 0.12, 0.08), (0, 0, 0.43), LEAF, segs=(6, 4))                                # a sprig on top
	return p.build()


def _plate(p, swatch=STONE_LIGHT, r=0.7):
	p.seg((0, 0, 0), (0, 0, 0.05), r * 0.8, r, swatch, sides=18, grad=(0.0, 0.6))
	p.seg((0, 0, 0.05), (0, 0, 0.07), r, r * 1.02, swatch, sides=18, grad=(0.0, 0.4))


def frog_legs_saute():
	p = Prop("frog_legs_saute", 459)
	_plate(p, STONE_WARM, r=0.62)
	_frog_pair(p, AMBER, flat=True, lift=0.0)
	for k in range(5):                                                                     # herbs
		a = k * 1.3
		p.blob((0.1, 0.08, 0.04), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.1), LEAF, segs=(5, 4))
	return p.build()


def lagoon_feast():
	p = Prop("lagoon_feast", 461)
	p.blob((1.9, 1.2, 0.12), (0, 0, 0.06), WOOD, segs=(18, 6), grad=(0.1, 0.6))                # a wide board
	for k in range(4):                                                                     # banana leaves
		p.blob((0.7, 0.22, 0.03), (-0.3 + k * 0.2, 0.1, 0.13), LEAF, rot=(0, 0, -30 + k * 20), segs=(8, 4))
	_fish_at(p, CLOTH_RED, EMBER, (-0.15, 0.1, 0.32), s=0.8, fat=0.3)                           # a snapper
	p.blob((0.34, 0.34, 0.24), (0.6, -0.25, 0.2), WOOD, segs=(10, 6), grad=(0.3, 0.9))          # half a coconut
	p.seg((0.6, -0.25, 0.3), (0.6, -0.25, 0.32), 0.15, 0.15, CLOTH_WHITE, sides=10)
	for k in range(3):                                                                     # fruit
		p.blob((0.2, 0.2, 0.2), (-0.65 + k * 0.17, -0.35 + (k % 2) * 0.08, 0.22), ORANGE, segs=(8, 6), grad=(0.0, 0.5))
	for k in range(3):                                                                     # prawns
		x = 0.25 + k * 0.14
		p.seg((x, 0.35, 0.16), (x + 0.08, 0.4, 0.3), 0.06, 0.03, PINK, sides=6)
	return p.build()


def koi_platter():
	p = Prop("koi_platter", 463)
	_plate(p, WATER, r=0.8)
	for k in range(5):                                                                     # a bed of leaves
		a = k * math.tau / 5
		p.blob((0.45, 0.18, 0.03), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.09), LEAF, rot=(0, 0, math.degrees(a)), segs=(8, 4))
	_fish_at(p, CLOTH_WHITE, EMBER, (0, 0, 0.3), s=0.95, fat=0.3)
	for (x, z, sw) in ((0.0, 0.08, CLOTH_RED), (0.2, -0.03, EMBER), (-0.17, -0.05, GOLD), (0.05, -0.08, CLOTH_RED)):  # koi patches
		p.blob((0.2, 0.04, 0.15), (x, -0.12, 0.3 + z), sw, segs=(6, 4))
	p.blob((0.12, 0.03, 0.1), (0.1, -0.13, 0.36), WATER, segs=(6, 4), glow=0.8)                  # the rainbow sheen
	for k in range(4):                                                                     # jeweled garnish round the rim
		a = k * math.tau / 4 + 0.6
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.68, math.sin(a) * 0.68, 0.12), (RUNE, LAVENDER, LEAF, EMBER)[k], segs=(6, 4), glow=0.8)
	return p.build()


# potions: the liquid is the bottle; glass shows as neck, lip, a glint and a cork

def _potion(p, top, neck=0.28, neck_r=0.1, cork=WOOD):
	"""Glass neck, lip and cork on a bottle whose shoulder ends at `top`."""
	p.seg((0, 0, top - 0.05), (0, 0, top + neck), neck_r, neck_r * 0.9, CLOTH_WHITE, sides=10, grad=(0.1, 0.5))
	p.seg((0, 0, top + neck - 0.02), (0, 0, top + neck + 0.04), neck_r * 1.3, neck_r * 1.3, CLOTH_WHITE, sides=10)
	p.seg((0, 0, top + neck + 0.03), (0, 0, top + neck + 0.16), neck_r * 0.85, neck_r, cork, sides=8)
	return top + neck


POTION_FRAME = ((-0.5, -0.5, 0.0), (0.5, 0.5, 1.38))


def minor_healing_potion():
	p = Prop("minor_healing_potion", 465)
	p.blob((0.62, 0.62, 0.62), (0, 0, 0.31), CLOTH_RED, segs=(12, 8), grad=(0.0, 0.6), glow=0.9)
	_potion(p, 0.58, neck=0.16, neck_r=0.08)
	p.box((0.04, 0.02, 0.16), (-0.12, -0.3, 0.38), CLOTH_WHITE, glow=0.8)
	_frame(p, *POTION_FRAME)
	return p.build()


def healing_potion():
	p = Prop("healing_potion", 467)
	p.blob((0.8, 0.8, 0.8), (0, 0, 0.4), CLOTH_RED, segs=(14, 8), grad=(0.0, 0.6), glow=1.0)
	_potion(p, 0.76, neck=0.24, neck_r=0.09)
	p.box((0.05, 0.02, 0.22), (-0.16, -0.38, 0.5), CLOTH_WHITE, glow=0.8)
	_frame(p, *POTION_FRAME)
	return p.build()


def greater_healing_potion():
	p = Prop("greater_healing_potion", 469)
	p.blob((1.0, 1.0, 0.86), (0, 0, 0.43), CLOTH_RED, segs=(16, 10), grad=(0.0, 0.6), glow=1.2)
	p.seg((0, 0, 0.74), (0, 0, 0.95), 0.26, 0.13, CLOTH_RED, sides=12, glow=1.2)            # a pear-shaped shoulder
	p.seg((0, 0, 0.9), (0, 0, 1.12), 0.13, 0.12, CLOTH_WHITE, sides=10)
	p.seg((0, 0, 0.98), (0, 0, 1.03), 0.16, 0.16, GOLD, sides=10)                           # gold collar
	p.seg((0, 0, 1.1), (0, 0, 1.3), 0.1, 0.14, GOLD, sides=8, glow=0.3)                      # gold stopper
	p.blob((0.12, 0.12, 0.12), (0, 0, 1.32), GOLD, segs=(6, 4))
	p.box((0.06, 0.02, 0.28), (-0.22, -0.46, 0.5), CLOTH_WHITE, glow=0.8)
	_frame(p, *POTION_FRAME)
	return p.build()


def antidote():
	p = Prop("antidote", 471)
	p.seg((0, 0, 0.05), (0, 0, 0.85), 0.2, 0.2, LEAF, sides=12, grad=(0.0, 0.6), glow=0.9)    # a tall slim vial
	p.seg((0, 0, 0.0), (0, 0, 0.06), 0.18, 0.2, LEAF, sides=12, glow=0.9)
	p.seg((0, 0, 0.85), (0, 0, 0.92), 0.2, 0.12, CLOTH_WHITE, sides=12)
	_potion(p, 0.95, neck=0.12, neck_r=0.08)
	p.box((0.26, 0.02, 0.3), (0, -0.21, 0.45), CLOTH_WHITE, grad=(0.1, 0.4))                  # a paper label
	p.box((0.16, 0.025, 0.04), (0, -0.22, 0.5), LEAF)
	p.box((0.04, 0.025, 0.16), (0, -0.22, 0.5), LEAF)
	return p.build()


def clarity_tonic():
	p = Prop("clarity_tonic", 473)
	p.seg((0, 0, 0.05), (0, 0, 0.45), 0.2, 0.46, RUNE, sides=6, grad=(0.0, 0.5), glow=1.1)    # a cut-crystal bottle
	p.seg((0, 0, 0.45), (0, 0, 0.8), 0.46, 0.14, RUNE, sides=6, grad=(0.0, 0.5), glow=1.1)
	_potion(p, 0.8, neck=0.12, neck_r=0.1, cork=STONE_LIGHT)
	p.blob((0.12, 0.12, 0.12), (0, 0, 1.12), RUNE, segs=(6, 4), glow=1.5)                     # a crystal on the stopper
	p.box((0.05, 0.02, 0.26), (-0.18, -0.36, 0.45), CLOTH_WHITE, glow=0.8)
	return p.build()


def draught_of_toughness():
	p = Prop("draught_of_toughness", 475)
	p.box((0.62, 0.5, 0.62), (0, 0, 0.31), HIDE, grad=(0.0, 0.7), glow=0.4)                    # a square-shouldered jug
	p.seg((0, 0, 0.6), (0, 0, 0.75), 0.24, 0.12, HIDE, sides=8, glow=0.4)
	_potion(p, 0.72, neck=0.1, neck_r=0.1)
	p.box((0.66, 0.54, 0.1), (0, 0, 0.18), IRON)                                               # an iron band
	for x in (-0.2, 0.2):
		p.blob((0.07, 0.04, 0.07), (x, -0.27, 0.18), STONE_LIGHT, segs=(5, 4))                 # rivets
	_loop(p, (0.36, 0, 0.42), 0.14, False, 0.04, HIDE, n=8)                                     # a handle
	return p.build()


def troll_tonic():
	p = Prop("troll_tonic", 477)
	p.blob((0.7, 0.66, 0.6), (0, 0, 0.3), MOSS, segs=(12, 8), grad=(0.0, 0.7), glow=0.8)       # a gourd
	p.blob((0.42, 0.4, 0.4), (0.05, 0, 0.72), MOSS, segs=(10, 6), grad=(0.0, 0.7), glow=0.8)
	p.seg((0.05, 0, 0.88), (0.1, 0, 1.05), 0.08, 0.07, WOOD, sides=6)                           # a stick for a stopper
	p.seg((0.05, 0, 0.55), (0.05, 0, 0.6), 0.23, 0.23, WOOD_GRAY, sides=10)                     # twine round the waist
	for k in range(5):                                                                     # clinging moss
		a = k * 1.4
		p.blob((0.16, 0.08, 0.12), (math.cos(a) * 0.3, math.sin(a) * 0.3 - 0.05, 0.12 + (k % 3) * 0.14), LEAF, segs=(5, 4))
	p.seg((0.3, -0.1, 0.62), (0.45, -0.1, 0.4), 0.06, 0.0, BONE, sides=5)                       # a troll tooth tied on
	return p.build()


def draught_of_swiftness():
	p = Prop("draught_of_swiftness", 479)
	p.seg((0, 0, 0.0), (0, 0, 0.7), 0.46, 0.1, CLOTH_WHITE, sides=14, grad=(0.0, 0.5), glow=1.0)  # a cone flask
	p.seg((0, 0, 0.0), (0, 0, 0.04), 0.46, 0.46, RUNE, sides=14, glow=0.6)
	_potion(p, 0.7, neck=0.14, neck_r=0.1)
	p.poly([(0.1, -0.05, 0.8), (0.55, -0.05, 1.2), (0.62, -0.05, 1.05), (0.2, -0.05, 0.76)], [(0, 1, 2, 3)], GOLD)  # a feather at the neck
	p.seg((0.1, -0.05, 0.78), (0.6, -0.05, 1.14), 0.015, 0.01, WOOD, sides=4)
	p.box((0.05, 0.02, 0.24), (-0.18, -0.3, 0.25), RUNE, rot=(0, 25, 0), glow=0.8)
	return p.build()


# bags

def stitched_hide_pouch():
	p = Prop("stitched_hide_pouch", 481)
	p.blob((0.75, 0.62, 0.7), (0, 0, 0.35), HIDE, segs=(12, 8), grad=(0.1, 0.9))
	p.seg((0, 0, 0.64), (0, 0, 0.9), 0.1, 0.2, HIDE, sides=8)                                   # gathered neck
	p.seg((0, 0, 0.7), (0, 0, 0.75), 0.13, 0.13, WOOD, sides=8)                                 # drawstring
	p.seg((0.1, -0.1, 0.72), (0.3, -0.2, 0.45), 0.025, 0.025, WOOD, sides=4)
	p.blob((0.06, 0.06, 0.06), (0.3, -0.2, 0.43), WOOD, segs=(5, 4))
	for k in range(6):                                                                     # a stitched seam down the front
		z = 0.12 + k * 0.09
		p.seg((-0.05, -0.34, z), (0.05, -0.34, z + 0.03), 0.018, 0.018, CLOTH_WHITE, sides=4)
	p.seg((0, -0.33, 0.1), (0, -0.33, 0.6), 0.012, 0.012, WOOD, sides=4)
	return p.build()


def wool_satchel():
	p = Prop("wool_satchel", 483)
	_bag(p, CLOTH_RED, 0.95, 0.35, 0.65, strap=HIDE)
	p.box((0.8, 0.03, 0.04), (0, -0.17, 0.18), CLOTH_WHITE)                                   # a woven stripe
	p.blob((0.1, 0.06, 0.1), (0, -0.21, 0.5), GOLD, segs=(6, 4))                               # button
	pts = []
	for k in range(9):                                                                     # a long shoulder strap
		a = math.pi * k / 8
		pts.append((-math.cos(a) * 0.45, 0, 0.55 + math.sin(a) * 0.55))
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.04, 0.04, HIDE, sides=5)
	return p.build()


def crocskin_backpack():
	p = Prop("crocskin_backpack", 485)
	_bag(p, MOSS, 0.85, 0.55, 1.0, strap=HIDE)
	for r in range(3):                                                                     # scutes
		for c in range(3):
			p.blob((0.14, 0.06, 0.1), (-0.2 + c * 0.2, -0.28, 0.2 + r * 0.14), LEAF, segs=(6, 4), grad=(0.0, 0.5))
	p.box((0.1, 0.06, 0.12), (0, -0.33, 0.62), GOLD)                                           # buckle
	for x in (-1, 1):
		p.blob((0.22, 0.28, 0.34), (x * 0.46, -0.02, 0.36), HIDE, segs=(8, 6))                 # side pouches
	p.seg((0.3, 0.2, 1.0), (0.45, 0.25, 1.12), 0.06, 0.0, BONE, sides=5)                       # a croc tooth toggle
	return p.build()


def iron_tipped_arrow():
	p = Prop("iron_tipped_arrow", 487)
	a, b = (-0.6, 0, 0.05), (0.5, 0, 0.95)
	p.seg(a, b, 0.035, 0.035, WOOD, sides=6)                                                   # shaft
	p.seg(b, (0.66, 0, 1.08), 0.09, 0.0, STONE_LIGHT, sides=4, glow=0.2)                         # iron head
	p.seg((0.46, 0, 0.92), (0.51, 0, 0.96), 0.06, 0.06, STONE_DARK, sides=6)                     # its socket
	d = (Vector(b) - Vector(a)).normalized()
	for off, sw in (((-d.z, 0, d.x), CLOTH_WHITE), ((d.z, 0, -d.x), CLOTH_RED), ((0, -1, 0), CLOTH_RED)):  # fletching
		n = Vector(off) * 0.13
		root, tip = Vector(a) + d * 0.04, Vector(a) + d * 0.3
		p.poly([tuple(root), tuple(tip), tuple(tip - d * 0.06 + n), tuple(root + n * 0.9)], [(0, 1, 2, 3)], sw)
	p.seg((-0.62, 0, 0.02), (-0.58, 0, 0.06), 0.04, 0.04, CLOTH_RED, sides=5)                    # nock
	return p.build()


# ---------------------------------------------------------------- travel

def homeward_stone():
	p = Prop("homeward_stone", 501)
	p.rock((0.95, 0.5, 0.75), (0, 0, 0.38), STONE_LIGHT, jitter=0.03)          # a smooth, flat hearthstone
	for k in range(3):   # an ember-glowing rune of a house carved in its face
		p.seg((-0.2 + k * 0.2, -0.26, 0.25), (-0.2 + k * 0.2, -0.26, 0.45), 0.035, 0.035, EMBER, sides=4, glow=2.2)
	p.seg((-0.28, -0.26, 0.43), (0.0, -0.26, 0.62), 0.035, 0.035, EMBER, sides=4, glow=2.2)
	p.seg((0.28, -0.26, 0.43), (0.0, -0.26, 0.62), 0.035, 0.035, EMBER, sides=4, glow=2.2)
	return p.build()


def grove_seed():
	p = Prop("grove_seed", 509)
	p.blob((0.62, 0.62, 0.78), (0, 0, 0.42), GOLD, segs=(16, 10), grad=(0.3, 0.9), glow=0.5)   # a plum-sized seed, warm gold
	p.seg((0, 0, 0.78), (0.04, -0.02, 0.98), 0.04, 0.03, MOSS, sides=5)   # a sprout from its tip
	p.blob((0.3, 0.14, 0.06), (0.14, -0.04, 1.02), MOSS, segs=(8, 4))   # and its first leaf
	return p.build()


def draught_of_homecoming():
	p = Prop("draught_of_homecoming", 503)
	p.blob((0.8, 0.8, 0.8), (0, 0, 0.4), GOLD, segs=(14, 8), grad=(0.0, 0.6), glow=1.2)
	_potion(p, 0.76, neck=0.24, neck_r=0.09)
	p.seg((-0.12, -0.38, 0.32), (0.0, -0.4, 0.5), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=0.8)   # a little roof on the label
	p.seg((0.12, -0.38, 0.32), (0.0, -0.4, 0.5), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=0.8)
	_frame(p, *POTION_FRAME)
	return p.build()


# ---------------------------------------------------------------- the High Terrace and Ashfall

FLAME = props.FLAME
TEAL = (3, 3)         # gray-green: troll hide
ASH = (5, 3)          # soft gray: ash, smoke
CRIMSON = (4, 1)      # deep red-magenta


def _vane(p, base, tip, width, swatch, bars=None, tip_swatch=None, glow=0.0):
	"""A feather: quill from base to tip and a vane round it in the picture plane,
	with optional dark bars across it and a pale tip."""
	base, tip = Vector(base), Vector(tip)
	d = tip - base
	n = Vector((-d.z, 0, d.x)).normalized()
	outline = []
	for t, w in ((0.12, 0.35), (0.3, 0.85), (0.55, 1.0), (0.78, 0.8), (0.93, 0.45), (1.0, 0.0)):
		outline.append(base + d * t + n * width * w)
	for t, w in ((0.93, 0.4), (0.78, 0.75), (0.55, 0.95), (0.3, 0.8), (0.12, 0.3)):
		outline.append(base + d * t - n * width * w)
	p.poly([tuple(v) for v in outline], [tuple(range(len(outline)))], swatch, grad=(0.0, 0.7))
	if tip_swatch:   # the pale tip, laid just in front
		front = Vector((0, -0.01, 0))
		tip_pts = [base + d * 0.8 + n * width * 0.76, base + d * 0.93 + n * width * 0.45, tip,
				   base + d * 0.93 - n * width * 0.4, base + d * 0.8 - n * width * 0.72]
		p.poly([tuple(v + front) for v in tip_pts], [tuple(range(5))], tip_swatch)
	for t in (bars or ()):
		w = 0.9 * width
		p.seg(tuple(base + d * t + n * w + Vector((0, -0.015, 0))), tuple(base + d * (t + 0.06) - n * w + Vector((0, -0.015, 0))),
			  0.025, 0.025, WOOD, sides=4)
	p.seg(tuple(base - d * 0.12), tuple(tip), 0.035, 0.01, CLOTH_WHITE if swatch != CLOTH_WHITE else STONE_LIGHT, sides=5, glow=glow)


def griffon_feather():
	p = Prop("griffon_feather", 601)
	_vane(p, (-0.35, 0, 0.0), (0.4, 0, 1.2), 0.24, HIDE, bars=(0.3, 0.48, 0.66), tip_swatch=CLOTH_WHITE)
	return p.build()


def harpy_talon():
	p = Prop("harpy_talon", 603)
	p.seg((-0.35, 0, 0.9), (-0.05, 0, 0.45), 0.13, 0.12, GOLD, sides=7)                  # a scaly yellow toe
	for k in range(3):
		t = 0.25 + k * 0.25
		p.seg((-0.35 + 0.3 * t - 0.02, -0.02, 0.9 - 0.45 * t), (-0.35 + 0.3 * t + 0.02, -0.02, 0.9 - 0.45 * t - 0.04), 0.135, 0.135, AMBER, sides=7)
	pts = [(-0.05, 0, 0.45), (0.2, 0, 0.28), (0.4, 0, 0.12), (0.52, 0, -0.08), (0.5, 0, -0.28)]  # and its black, hooked claw
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.12 - i * 0.03, 0.09 - i * 0.03 if i < 3 else 0.0, STONE_DARK, sides=7, grad=(0.0, 0.6))
	for k in range(3):                                                                    # tufts of feather at the top
		p.seg((-0.35, 0, 0.9), (-0.55 + k * 0.18, -0.02, 1.2), 0.07, 0.0, WOOD, sides=4)
	return p.build()


def prayer_bead():
	p = Prop("prayer_bead", 605)
	p.blob((0.7, 0.7, 0.66), (0, 0, 0.45), GOLD, segs=(14, 10), grad=(0.35, 1.0))          # a tarnished brass bead
	p.seg((0, 0, 0.72), (0, 0, 0.8), 0.14, 0.14, STONE_DARK, sides=10)                     # its hole
	for k, (a, z) in enumerate(((0.5, 0.52), (2.2, 0.35), (4.1, 0.6), (5.3, 0.3))):       # green patina
		p.blob((0.16, 0.08, 0.12), (math.cos(a) * 0.3, math.sin(a) * 0.3 - 0.05, z), TEAL, segs=(6, 4))
	_loop(p, (0, 0, 0.45), 0.35, True, 0.03, STONE_WARM, n=18)                             # an engraved band
	for sx in (-1, 1):                                                                    # the frayed cord through it
		p.seg((0, 0, 0.8), (sx * 0.22, 0, 1.08), 0.025, 0.02, WOOD_GRAY, sides=4)
	return p.build()


def abbots_seal():
	p = Prop("abbots_seal", 607)
	for sx in (-1, 1):                                                                    # ribbon tails
		p.box((0.14, 0.03, 0.55), (sx * 0.15, 0.05, 0.1), GOLD, rot=(0, sx * -15, 0))
	p.seg((0, 0.04, 0.55), (0, -0.08, 0.55), 0.46, 0.44, CLOTH_RED, sides=16, grad=(0.1, 0.9))   # a disc of red wax
	for k in range(7):                                                                    # its puddled rim
		a = k * math.tau / 7 + 0.2
		p.blob((0.2, 0.12, 0.18), (math.cos(a) * 0.44, -0.02, 0.55 + math.sin(a) * 0.44), CLOTH_RED, segs=(6, 4))
	_loop(p, (0, -0.1, 0.55), 0.33, False, 0.025, CLOTH_RED, n=16)
	p.seg((0, -0.08, 0.55), (0, -0.13, 0.55), 0.13, 0.13, CLOTH_RED, sides=12)            # the abbot's sun, pressed in
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.15, -0.11, 0.55 + math.sin(a) * 0.15), (math.cos(a) * 0.27, -0.11, 0.55 + math.sin(a) * 0.27),
			  0.03, 0.0, CLOTH_RED, sides=4)
	return p.build()


def gargoyle_shard():
	p = Prop("gargoyle_shard", 609)
	p.seg((-0.1, 0, 0.0), (0.05, 0, 1.0), 0.34, 0.0, STONE_LIGHT, sides=5, jitter=0.03)    # a jagged shard of carved stone
	p.seg((0.3, 0.1, 0.0), (0.42, 0.1, 0.55), 0.2, 0.0, STONE_LIGHT, sides=5, jitter=0.03)
	p.rock((0.55, 0.45, 0.3), (0.05, 0, 0.1), STONE_LIGHT, jitter=0.06)
	for k in range(3):                                                                    # the scalloped edge of a stone wing
		p.blob((0.2, 0.1, 0.14), (-0.22 + k * 0.05, -0.2, 0.25 + k * 0.2), STONE_DARK, segs=(6, 4))
	pts = [(-0.02, -0.25, 0.15), (0.08, -0.25, 0.4), (-0.02, -0.25, 0.62), (0.05, -0.2, 0.8)]   # a faint glowing crack
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.03, 0.03, RUNE, sides=4, glow=2.0)
	return p.build()


def leopard_pelt():
	p = Prop("leopard_pelt", 611)
	p.blob((1.1, 0.8, 0.16), (0, 0, 0.08), CLOTH_WHITE, segs=(12, 6), grad=(0.2, 0.9), jitter=0.05)   # a pale, thick pelt
	for x in (-1, 1):
		p.blob((0.32, 0.24, 0.12), (x * 0.4, 0.34, 0.06), CLOTH_WHITE, segs=(6, 4), grad=(0.2, 0.9))
		p.blob((0.32, 0.24, 0.12), (x * 0.4, -0.34, 0.06), CLOTH_WHITE, segs=(6, 4), grad=(0.2, 0.9))
	p.blob((0.38, 0.32, 0.2), (-0.6, 0, 0.14), CLOTH_WHITE, segs=(8, 5), grad=(0.2, 0.9))     # the head end
	for sy in (-1, 1):
		p.seg((-0.66, sy * 0.1, 0.2), (-0.7, sy * 0.14, 0.34), 0.07, 0.0, CLOTH_WHITE, sides=4)
	pts = [(0.5, 0, 0.1), (0.8, 0.12, 0.12), (0.98, 0.32, 0.16), (1.0, 0.55, 0.2)]         # a long, thick tail
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.1, 0.09, CLOTH_WHITE, sides=6, grad=(0.2, 0.9))
	for k in range(3):
		p.blob((0.2, 0.2, 0.2), pts[k + 1], STONE_DARK, segs=(6, 4))
	for k in range(12):                                                                   # dark spots
		a = k * 2.4
		r = 0.1 + 0.3 * ((k * 7) % 5) / 4
		x, y = math.cos(a) * r * 1.1, math.sin(a) * r * 0.9
		p.blob((0.13, 0.13, 0.05), (x, y, 0.16), STONE_DARK, segs=(6, 4))
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(40), 4, "X"))                         # tipped up to show its spots
	return obj


def yak_hair():
	p = Prop("yak_hair", 613)
	import random
	rnd = random.Random(613)
	for k in range(16):                                                                   # long shaggy strands
		x0 = rnd.uniform(-0.1, 0.1)
		sway = rnd.uniform(-0.35, 0.35)
		pts = [(x0, rnd.uniform(-0.08, 0.08), 1.0), (x0 + sway * 0.4, 0, 0.6), (x0 + sway, 0, 0.2), (x0 + sway * 1.3, 0, -0.05)]
		sw = WOOD if k % 3 else HIDE
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.05 - i * 0.012, 0.04 - i * 0.012 if i < 2 else 0.0, sw, sides=4)
	p.seg((0, 0, 0.9), (0, 0, 1.1), 0.14, 0.12, CLOTH_RED, sides=8)                       # bound with a red cord
	p.blob((0.22, 0.18, 0.18), (0, 0, 1.18), WOOD, segs=(8, 5))
	return p.build()


def troll_hide():
	p = Prop("troll_hide", 615)
	p.blob((1.15, 0.85, 0.16), (0, 0, 0.08), TEAL, segs=(12, 6), grad=(0.0, 0.7), jitter=0.07)   # a thick gray-green hide
	p.blob((0.8, 0.6, 0.16), (0.12, -0.08, 0.2), TEAL, rot=(0, 0, 25), segs=(10, 6), grad=(0.0, 0.8), jitter=0.05)  # folded over
	for k in range(8):                                                                    # warts
		a = k * 2.2
		r = 0.1 + 0.25 * ((k * 3) % 4) / 3
		p.blob((0.09, 0.09, 0.07), (0.12 + math.cos(a) * r, -0.08 + math.sin(a) * r * 0.7, 0.3), PINE, segs=(6, 4))
	for k in range(3):                                                                    # coarse black bristles on its edge
		p.seg((-0.5 + k * 0.1, 0.25, 0.1), (-0.62 + k * 0.1, 0.4, 0.25), 0.02, 0.0, STONE_DARK, sides=3)
	return p.build()


def colossus_heartstone():
	p = Prop("colossus_heartstone", 617)
	p.rock((0.9, 0.7, 0.95), (0, 0, 0.48), STONE_WARM, jitter=0.07)                          # a heart of carved stone
	p.seg((0, -0.18, 0.55), (0, -0.36, 0.55), 0.3, 0.2, AMBER, sides=6, glow=2.0)            # with a burning amber core
	p.blob((0.2, 0.1, 0.2), (0, -0.4, 0.55), GOLD, segs=(6, 4), glow=2.8)
	for a in (0.6, 2.0, 3.6, 5.0):                                                       # veins of gold out from it
		p.seg((math.cos(a) * 0.25, -0.34, 0.55 + math.sin(a) * 0.25), (math.cos(a) * 0.42, -0.3, 0.55 + math.sin(a) * 0.4),
			  0.03, 0.015, GOLD, sides=4, glow=2.0)
	return p.build()


def skyrend_plume():
	p = Prop("skyrend_plume", 619)
	for (bx, tip, sw, tips) in (((-0.02, 0), (-0.6, 1.1), WATER, CLOTH_WHITE), ((0.02, 0), (0.55, 1.1), WATER, CLOTH_WHITE),
							   ((0, 0), (0.0, 1.35), CLOTH_WHITE, RUNE)):
		_vane(p, (bx[0], 0.05 if sw == WATER else -0.05, 0.1), (tip[0], 0.05 if sw == WATER else -0.05, tip[1]), 0.2, sw, tip_swatch=tips, glow=0.8)
	p.seg((0, -0.1, -0.05), (0, -0.1, 0.25), 0.1, 0.1, GOLD, sides=8)                       # a gold clasp binds them
	p.blob((0.12, 0.08, 0.12), (0, -0.2, 0.12), RUNE, segs=(6, 4), glow=2.2)
	return p.build()


def magma_core():
	p = Prop("magma_core", 621)
	p.blob((0.85, 0.85, 0.8), (0, 0, 0.42), EMBER, segs=(12, 8), glow=1.8)                    # a molten heart
	for k in range(9):                                                                    # under a cracked black crust
		a, b = k * 0.7, (k % 3) * 0.6 - 0.6
		p.rock((0.4, 0.3, 0.3), (math.cos(a) * 0.36 * math.cos(b), math.sin(a) * 0.36 * math.cos(b), 0.42 + math.sin(b) * 0.36),
			   STONE_DARK, rot=(0, math.degrees(b), math.degrees(a)), jitter=0.05)
	p.rock((0.42, 0.3, 0.2), (0, 0, 0.8), STONE_DARK, jitter=0.05)
	return p.build()


def _slab(p, outline, y0, y1, swatch, grad=(0.1, 0.8)):
	"""A flat plate cut to an outline in the picture plane, from y0 (front) to y1."""
	n = len(outline)
	verts = [(x, y0, z) for x, z in outline] + [(x, y1, z) for x, z in outline]
	faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
	p.poly(verts, faces, swatch, grad=grad)


def drake_scale():
	p = Prop("drake_scale", 623)
	for dx, dy, dz, s_ in ((-0.35, 0.15, 0.3, 0.75), (0.1, 0.0, 0.0, 1.0)):              # an ash-dark scale over a smaller one
		outline = []
		for k in range(15):                                                               # rounded free edge, pointed root
			a = math.radians(200 + k * (140 / 14))
			outline.append((dx + math.cos(a) * 0.45 * s_, dz + (0.45 + math.sin(a) * 0.45) * s_))
		outline += [(dx + 0.3 * s_, dz + 0.8 * s_), (dx, dz + 1.15 * s_), (dx - 0.3 * s_, dz + 0.8 * s_)]
		_slab(p, outline, dy - 0.06 * s_, dy + 0.06 * s_, STONE_DARK)
		p.seg((dx, dy - 0.08 * s_, dz + 0.1 * s_), (dx, dy - 0.08 * s_, dz + 1.0 * s_), 0.045 * s_, 0.015, STONE_LIGHT, sides=4)   # its keel
		for a, b in zip(outline[:14], outline[1:15]):                                     # edged with ember-red
			p.seg((a[0], dy - 0.07 * s_, a[1]), (b[0], dy - 0.07 * s_, b[1]), 0.04 * s_, 0.04 * s_, EMBER, sides=4, glow=1.8)
	return p.build()


def salamander_tail():
	p = Prop("salamander_tail", 625)
	pts = []
	for k in range(12):                                                                   # a tapering, curling tail
		t = k / 11
		a = t * 2.4
		pts.append((-0.6 + t * 1.0 + math.sin(a) * 0.1, 0, 0.2 + math.sin(t * math.pi) * 0.45 + t * 0.2))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		r = 0.2 * (1 - i / 11) + 0.02
		p.seg(a, b, r, r * 0.92, EMBER if i % 2 else CLOTH_RED, sides=8, glow=0.6)
		if i % 3 == 1:
			p.blob((r * 0.8, r * 0.5, r * 0.6), (b[0], -r * 0.8, b[2] + r * 0.3), STONE_DARK, segs=(6, 4))
	p.blob((0.12, 0.12, 0.12), pts[-1], FLAME, segs=(6, 4), glow=3.0)                      # still smoldering at the tip
	p.blob((0.45, 0.42, 0.42), pts[0], CLOTH_RED, segs=(8, 6))                              # the torn end
	p.seg(pts[0], (pts[0][0] - 0.05, -0.2, pts[0][2]), 0.14, 0.14, PINK, sides=8)
	return p.build()


def ember_sigil():
	p = Prop("ember_sigil", 627)
	p.seg((0, 0.05, 0.5), (0, -0.05, 0.5), 0.5, 0.5, STONE_DARK, sides=8, grad=(0.1, 0.8))    # an iron token
	_loop(p, (0, -0.06, 0.5), 0.44, False, 0.035, IRON, n=8)
	p.blob((0.3, 0.1, 0.3), (0, -0.07, 0.42), EMBER, segs=(8, 5), glow=2.2)                   # its flame rune, burning
	p.seg((0, -0.1, 0.48), (0.03, -0.1, 0.82), 0.12, 0.0, FLAME, sides=6, glow=2.6)
	for sx in (-1, 1):
		p.seg((sx * 0.1, -0.1, 0.45), (sx * 0.2, -0.1, 0.68), 0.06, 0.0, FLAME, sides=5, glow=2.2)
	return p.build()


def ashkars_brand():
	p = Prop("ashkars_brand", 629)
	p.seg((0.6, 0, 1.05), (0.3, 0, 0.7), 0.1, 0.1, WOOD, sides=7)                        # a wrapped grip
	for k in range(3):
		p.seg((0.55 - k * 0.1, 0, 0.99 - k * 0.12), (0.53 - k * 0.1, 0, 0.96 - k * 0.12), 0.11, 0.11, HIDE, sides=7)
	p.seg((0.3, 0, 0.7), (-0.08, 0, 0.25), 0.06, 0.06, STONE_DARK, sides=6)               # an iron rod
	c = (-0.3, -0.02, 0.0)                                                                 # and the brand, white-hot
	_loop(p, c, 0.3, False, 0.06, FLAME, n=14, glow=2.8)
	p.seg((c[0] - 0.3, c[1], c[2]), (c[0] + 0.3, c[1], c[2]), 0.06, 0.06, FLAME, sides=5, glow=2.8)
	p.seg((c[0], c[1], c[2] - 0.3), (c[0], c[1], c[2] + 0.3), 0.06, 0.06, FLAME, sides=5, glow=2.8)
	p.seg((-0.08, 0, 0.25), (c[0] + 0.2, c[1], c[2] + 0.22), 0.06, 0.06, EMBER, sides=6, glow=1.6)
	return p.build()


def cindermaw_heart():
	p = Prop("cindermaw_heart", 631)
	for sx in (-1, 1):                                                                    # a great scorched heart
		p.blob((0.55, 0.5, 0.55), (sx * 0.22, 0, 0.62), CRIMSON, segs=(10, 8), grad=(0.2, 0.9))
	p.seg((0, 0, 0.6), (0.05, 0, -0.05), 0.46, 0.0, CRIMSON, sides=10)
	for x, z, s in ((-0.25, 0.7, 0.3), (0.2, 0.35, 0.34), (0.3, 0.75, 0.22)):              # patched with black crust
		p.rock((s, s * 0.6, s * 0.7), (x, -0.2, z), STONE_DARK, jitter=0.04)
	for a, b in (((-0.1, 0.8), (0.0, 0.5)), ((0.0, 0.5), (-0.1, 0.25)), ((0.0, 0.5), (0.15, 0.55))):  # molten veins
		p.seg((a[0], -0.27, a[1]), (b[0], -0.27, b[1]), 0.035, 0.035, FLAME, sides=4, glow=2.8)
	for sx in (-1, 1):                                                                    # stumps of great vessels
		p.seg((sx * 0.15, 0, 0.85), (sx * 0.22, 0, 1.15), 0.1, 0.09, CRIMSON, sides=7)
		p.seg((sx * 0.22, 0, 1.13), (sx * 0.22, 0, 1.16), 0.07, 0.07, EMBER, sides=7, glow=2.5)
	return p.build()


def ash_essence():
	p = Prop("ash_essence", 633)
	p.blob((0.8, 0.8, 0.8), (0, 0, 0.4), STONE_LIGHT, segs=(14, 8), grad=(0.4, 1.0))        # a stoppered vial of ash
	top = _potion(p, 0.76, neck=0.24, neck_r=0.09, cork=STONE_DARK)
	pts = []
	for k in range(16):                                                                   # a pale wisp swirling inside
		t = k / 15
		a = t * 3.5 * math.pi
		pts.append((math.cos(a) * (0.05 + 0.22 * t), -0.36 - math.sin(a) * 0.04, 0.15 + t * 0.5))
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.035, 0.035, CLOTH_WHITE, sides=4, glow=1.4)
	for k in range(3):                                                                    # ash curling off the cork
		p.blob((0.1 + k * 0.03,) * 3, (0.06 * (k % 2), 0, top + 0.28 + k * 0.1), STONE_LIGHT, segs=(6, 4))
	_frame(p, *POTION_FRAME)
	return p.build()


def charred_bone():
	p = Prop("charred_bone", 635)
	p.seg((-0.5, 0, 0.3), (0.5, 0, 0.55), 0.14, 0.14, STONE_DARK, sides=8, grad=(0.1, 0.6))   # a bone, burned black
	for x, z, sw in ((-0.55, 0.3, BONE), (0.55, 0.55, STONE_DARK)):
		for s_ in (-1, 1):
			p.blob((0.24, 0.24, 0.24), (x, s_ * 0.1, z + 0.1), sw, segs=(8, 6), grad=(0.1, 0.9))
	for k, t in enumerate((0.25, 0.5, 0.75)):                                              # still glowing in its cracks
		x, z = -0.5 + 1.0 * t, 0.3 + 0.25 * t
		p.seg((x - 0.04, -0.14, z - 0.05), (x + 0.05, -0.14, z + 0.05), 0.035, 0.035, EMBER, sides=4, glow=2.6)
	p.blob((0.12, 0.12, 0.12), (0.12, 0.0, 0.82), ASH, segs=(6, 4))                          # a curl of smoke
	p.blob((0.16, 0.16, 0.16), (0.05, 0.0, 0.98), ASH, segs=(6, 4))
	return p.build()


def pilgrims_prayer_beads():
	p = Prop("pilgrims_prayer_beads", 637)
	for k in range(18):                                                                   # a loop of wooden beads
		a = k * math.tau / 18
		x, y, z = math.cos(a) * 0.55, math.sin(a) * 0.55 * 0.6, 0.62 + math.sin(a) * 0.2
		big = k == 13
		p.blob((0.2 if big else 0.14,) * 3, (x, y, z), GOLD if big else WOOD, segs=(8, 6))
	p.seg((0, -0.33, 0.42), (0, -0.33, 0.1), 0.03, 0.03, WOOD_GRAY, sides=4)               # a drop to the charm
	p.seg((0, -0.36, 0.02), (0, -0.38, 0.02), 0.18, 0.18, GOLD, sides=12, glow=0.6)          # a pilgrim's sun token
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.18, -0.38, 0.02 + math.sin(a) * 0.18), (math.cos(a) * 0.28, -0.38, 0.02 + math.sin(a) * 0.28), 0.03, 0.0, GOLD, sides=4, glow=0.6)
	for sx in (-0.05, 0.05):                                                               # and a red tassel
		p.seg((sx - 0.2, -0.3, 0.3), (sx * 3 - 0.28, -0.3, -0.05), 0.03, 0.02, CLOTH_RED, sides=4)
	return p.build()


def heartstone_ring():
	p = Prop("heartstone_ring", 639)
	_ring(p, GOLD)
	for sx in (-1, 1):                                                                    # prongs
		p.seg((sx * 0.12, 0, 0.78), (sx * 0.16, -0.05, 1.0), 0.03, 0.02, GOLD, sides=4)
	p.rock((0.36, 0.3, 0.36), (0, -0.02, 0.95), AMBER, jitter=0.03)                           # a chip of the colossus's heartstone
	p.blob((0.18, 0.1, 0.18), (0, -0.14, 0.95), GOLD, segs=(6, 4), glow=2.6)
	return p.build()


def wraithbone_ring():
	p = Prop("wraithbone_ring", 641)
	_ring(p, BONE)
	for k in range(5):                                                                    # carved knuckles of bone
		a = math.radians(-60 + k * 30)
		p.blob((0.16, 0.2, 0.16), (math.cos(a) * 0.4, 0, 0.4 + math.sin(a) * 0.4), BONE, segs=(6, 4))
	p.blob((0.24, 0.2, 0.24), (0, -0.02, 0.86), PETAL_PURPLE, segs=(8, 6), glow=2.2)          # a wraith's pale light
	for k in range(3):
		x = -0.2 + k * 0.2
		p.seg((x * 0.5, -0.05, 0.95), (x * 1.6, -0.05, 1.25 + (k % 2) * 0.1), 0.05, 0.0, PETAL_PURPLE, sides=5, glow=1.8)
	return p.build()


def scouts_signet():
	p = Prop("scouts_signet", 643)
	_ring(p, STONE_LIGHT)
	p.seg((0, 0.08, 0.86), (0, -0.1, 0.86), 0.26, 0.26, STONE_LIGHT, sides=8)              # a flat signet face
	p.seg((0, -0.1, 0.86), (0, -0.12, 0.86), 0.21, 0.21, STONE_DARK, sides=8)
	p.box((0.2, 0.04, 0.08), (0, -0.14, 0.93), EMBER, glow=1.4)                              # Forgehold's hammer on it
	p.box((0.05, 0.04, 0.2), (0, -0.14, 0.8), EMBER, glow=1.4)
	return p.build()


def terrace_tea():
	p = Prop("terrace_tea", 645)
	p.seg((0, 0, 0.0), (0, 0, 0.06), 0.62, 0.66, CLOTH_WHITE, sides=18)                    # a saucer
	p.seg((0, 0, 0.06), (0, 0, 0.5), 0.3, 0.42, CLOTH_WHITE, sides=16, grad=(0.1, 0.7))     # a little cup
	p.seg((0, 0, 0.44), (0, 0, 0.47), 0.39, 0.39, (0, 2), sides=16)                        # of green tea
	_loop(p, (0, 0, 0.5), 0.42, True, 0.025, GOLD, n=16)                                   # a gold rim
	for k in range(3):                                                                    # and its steam
		x = -0.15 + k * 0.15
		pts = [(x, -0.05, 0.55), (x + 0.1, -0.05, 0.75), (x - 0.05, -0.05, 0.95), (x + 0.08, -0.05, 1.15)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.035, 0.02, CLOTH_WHITE, sides=4, glow=0.8)
	return p.build()


def obsidian_arrow():
	p = Prop("obsidian_arrow", 647)
	a, b = (-0.6, 0, 0.05), (0.5, 0, 0.95)
	p.seg(a, b, 0.035, 0.035, WOOD, sides=6)                                                   # shaft
	p.seg(b, (0.72, 0, 1.13), 0.11, 0.0, STONE_DARK, sides=4, grad=(0.0, 0.5))                  # a knapped obsidian head
	p.seg((0.52, -0.04, 0.97), (0.7, -0.04, 1.11), 0.02, 0.0, EMBER, sides=3, glow=1.8)          # glinting red
	p.seg((0.44, 0, 0.9), (0.51, 0, 0.96), 0.05, 0.05, HIDE, sides=6)                            # bound on
	d = (Vector(b) - Vector(a)).normalized()
	for off, sw in (((-d.z, 0, d.x), EMBER), ((d.z, 0, -d.x), STONE_DARK), ((0, -1, 0), EMBER)):  # fletching
		n = Vector(off) * 0.13
		root, tip = Vector(a) + d * 0.04, Vector(a) + d * 0.3
		p.poly([tuple(root), tuple(tip), tuple(tip - d * 0.06 + n), tuple(root + n * 0.9)], [(0, 1, 2, 3)], sw)
	p.seg((-0.62, 0, 0.02), (-0.58, 0, 0.06), 0.04, 0.04, STONE_DARK, sides=5)                  # nock
	return p.build()


def magma_heart_amulet():
	p = Prop("magma_heart_amulet", 649)
	_cord(p, 0.4, 0.82, GOLD)
	for sx in (-1, 1):                                                                    # a heart-shaped gold setting
		p.blob((0.34, 0.12, 0.34), (sx * 0.13, -0.3, 0.38), GOLD, segs=(10, 6))
	p.seg((0, -0.3, 0.38), (0, -0.3, -0.02), 0.3, 0.0, GOLD, sides=4, twist=45)
	for sx in (-1, 1):                                                                    # round a molten heart
		p.blob((0.26, 0.1, 0.26), (sx * 0.1, -0.38, 0.39), EMBER, segs=(8, 6), glow=2.2)
	p.seg((0, -0.37, 0.38), (0, -0.37, 0.08), 0.21, 0.0, EMBER, sides=4, glow=2.2, twist=45)
	p.seg((-0.02, -0.46, 0.45), (0.03, -0.46, 0.3), 0.022, 0.022, STONE_DARK, sides=4)
	p.seg((0.03, -0.46, 0.3), (-0.02, -0.46, 0.18), 0.022, 0.022, STONE_DARK, sides=4)
	p.seg((0, -0.32, 0.72), (0, -0.32, 0.5), 0.05, 0.05, GOLD, sides=6)                       # its bail
	return p.build()


# ---------------------------------------------------------------- Reedmere and Drownfast

AQUA = (5, 1)         # pale aqua to deep teal: naga, sea glass
SEAFOAM = (0, 2)      # sea green
SKY = (6, 2)          # sky blue to deep blue (RUNE)


def _rot2(pts, deg, origin=(0.0, 0.0)):
	"""Turns (x, z) points about origin in the picture plane (positive = counterclockwise)."""
	a = math.radians(deg)
	c, s = math.cos(a), math.sin(a)
	return [(origin[0] + x * c - z * s, origin[1] + x * s + z * c) for x, z in pts]


def _oval(p, c, u, v, ru, rv, r, swatch, n=12, glow=0.0):
	"""A ring (chain link, band) round c in the plane of unit vectors u and v."""
	c, u, v = Vector(c), Vector(u), Vector(v)
	pts = [c + u * math.cos(k * math.tau / n) * ru + v * math.sin(k * math.tau / n) * rv for k in range(n + 1)]
	for a, b in zip(pts, pts[1:]):
		p.seg(tuple(a), tuple(b), r, r, swatch, sides=5, glow=glow)


def _lotus(p, c, s, petal, glow=0.0, pad=True):
	"""A lotus: two rings of petals round a gold seed head, on a lily pad."""
	cx, cy, cz = c
	if pad:
		p.blob((1.3 * s, 1.1 * s, 0.08 * s), (cx, cy + 0.1 * s, cz - 0.05 * s), LEAF, segs=(14, 4), grad=(0.1, 0.6))
	for ring, (n, tilt, reach, h) in enumerate(((8, 55, 0.3, 0.42), (6, 25, 0.16, 0.5))):
		for k in range(n):
			a = k * math.tau / n + ring * 0.4
			p.blob((0.2 * s, 0.1 * s, h * s), (cx + math.cos(a) * reach * s, cy + math.sin(a) * reach * s, cz + (0.18 + ring * 0.08) * s),
				   petal, rot=(0, tilt, math.degrees(a)), segs=(8, 6), grad=(0.0, 0.5), glow=glow)
	p.seg((cx, cy, cz + 0.2 * s), (cx, cy, cz + 0.34 * s), 0.12 * s, 0.14 * s, GOLD, sides=10, glow=glow * 0.5)


def pondkin_fetish():
	p = Prop("pondkin_fetish", 651)
	p.seg((-0.2, 0, -0.1), (0.1, 0, 0.75), 0.05, 0.06, WOOD, sides=6)                        # a crooked stick
	p.blob((0.6, 0.4, 0.34), (0.12, 0, 0.88), LEAF, segs=(10, 6), grad=(0.1, 0.8))            # a fat carved frog on top
	for sx in (-1, 1):
		p.blob((0.17, 0.16, 0.17), (0.12 + sx * 0.17, -0.06, 1.03), LEAF, segs=(8, 5))
		p.blob((0.09, 0.06, 0.09), (0.12 + sx * 0.17, -0.14, 1.05), GOLD, segs=(6, 4), glow=1.4)   # painted eyes
		p.seg((0.12 + sx * 0.22, -0.05, 0.78), (0.12 + sx * 0.4, -0.08, 0.66), 0.06, 0.04, LEAF, sides=5)   # splayed legs
	p.seg((0.12 - 0.2, -0.18, 0.84), (0.12 + 0.2, -0.18, 0.84), 0.025, 0.025, CLOTH_RED, sides=4)           # a painted mouth
	for k in range(3):                                                                    # a reed binding
		z = 0.35 + k * 0.08
		p.seg((-0.08 + k * 0.03, 0, z), (0.0 + k * 0.03, 0, z + 0.01), 0.085, 0.085, HIDE, sides=6)
	for k, sw in enumerate((LEAF, BONE, PINE)):                                           # dangling reeds and a bead
		x = -0.06 + k * 0.05
		p.seg((x, -0.06, 0.4), (x - 0.25 + k * 0.08, -0.08, 0.02), 0.02, 0.01, sw if sw != BONE else HIDE, sides=4)
	p.blob((0.1, 0.1, 0.1), (-0.13, -0.08, 0.1), BONE, segs=(6, 4))
	return p.build()


def reedstalker_plume():
	p = Prop("reedstalker_plume", 653)
	_vane(p, (-0.3, 0, 0.0), (0.35, 0, 1.2), 0.2, STONE_LIGHT, tip_swatch=STONE_DARK)          # a long blue-gray heron feather
	for k in range(4):                                                                    # wisps of breeding plume
		p.seg((-0.2, 0.05, 0.1), (-0.55 + k * 0.08, 0.05, 1.0 - k * 0.12), 0.018, 0.005, CLOTH_WHITE, sides=4)
	return p.build()


def eel_skin():
	p = Prop("eel_skin", 655)
	pts = []
	for k in range(14):                                                                   # a long slick strip, curling at one end
		t = k / 13
		if t < 0.7:
			pts.append((-0.7 + t * 1.6, 0, 0.2 + math.sin(t * 9) * 0.08))
		else:
			a = (t - 0.7) / 0.3 * math.pi * 1.4
			pts.append((0.42 + math.sin(a) * 0.22, 0, 0.42 - math.cos(a) * 0.22))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		ang = -math.degrees(math.atan2(b[2] - a[2], b[0] - a[0]))
		mid = (Vector(a) + Vector(b)) / 2
		p.box(((Vector(b) - Vector(a)).length + 0.04, 0.05, 0.3 - i * 0.01), tuple(mid), PINE, rot=(0, ang, 0), grad=(0.1, 0.9))
		p.box(((Vector(b) - Vector(a)).length + 0.04, 0.05, 0.07), tuple(mid + Vector((0, -0.03, 0))), BONE, rot=(0, ang, 0))  # its pale belly stripe
		if i % 2 == 0 and i < 9:
			p.blob((0.07, 0.04, 0.07), (a[0] + 0.02, -0.05, a[2] + 0.08), STONE_DARK, segs=(5, 4))
	return p.build()


def bogwing_wing():
	p = Prop("bogwing_wing", 657)
	for off, s_, sw in ((0.14, 0.85, SEAFOAM), (-0.02, 1.0, AQUA)):                        # a pair of long veined wings
		outline = _rot2([(0, 0), (0.25 * s_, 0.12), (0.8 * s_, 0.2), (1.25 * s_, 0.12), (1.35 * s_, 0.0), (1.2 * s_, -0.1),
						 (0.7 * s_, -0.12), (0.2 * s_, -0.06)], 30 if off > 0 else 12, (-0.6, 0.1 + off * 2))
		_slab(p, outline, off - 0.02, off + 0.02, sw, grad=(0.0, 0.6))
		for a, b in zip(outline[1:4], outline[5:8][::-1]):                                 # cross veins
			p.seg((a[0], off - 0.04, a[1]), (b[0], off - 0.04, b[1]), 0.012, 0.012, IRON, sides=3)
		base, tip = outline[0], outline[4]
		p.seg((base[0], off - 0.04, base[1]), (tip[0], off - 0.04, tip[1]), 0.022, 0.01, IRON, sides=4)   # the leading vein
		p.blob((0.1, 0.03, 0.06), (outline[3][0] - 0.05, off - 0.05, outline[3][1] - 0.05), STONE_DARK, segs=(6, 4))  # a dark spot
	p.blob((0.14, 0.14, 0.14), (-0.62, 0.05, 0.2), STONE_DARK, segs=(6, 4))                  # torn from the body
	return p.build()


def sunken_charm():
	p = Prop("sunken_charm", 659)
	_cord(p, 0.5, 0.78, WOOD_GRAY)
	p.seg((0, -0.26, 0.34), (0, -0.34, 0.34), 0.34, 0.34, TEAL, sides=14, grad=(0.1, 0.9))    # a green-crusted bronze disc
	_loop(p, (0, -0.35, 0.34), 0.3, False, 0.03, GOLD, n=14)
	for k in range(5):                                                                    # a lotus scratched on it
		a = math.radians(90 + (k - 2) * 30)
		p.seg((0, -0.37, 0.24), (math.cos(a) * 0.2, -0.37, 0.24 + math.sin(a) * 0.22), 0.04, 0.0, GOLD, sides=4)
	for (x, z) in ((-0.22, 0.2), (0.2, 0.46), (0.25, 0.18)):                              # barnacles
		p.seg((x, -0.34, z), (x, -0.42, z), 0.06, 0.03, STONE_LIGHT, sides=6)
	p.seg((0.1, -0.36, 0.62), (-0.15, -0.38, 0.05), 0.03, 0.015, LEAF, sides=3)            # weed trailing off it
	p.seg((0.3, -0.36, 0.55), (0.35, -0.38, 0.1), 0.025, 0.012, LEAF, sides=3)
	return p.build()


def sedge_charm():
	p = Prop("sedge_charm", 661)
	for k in range(7):                                                                    # a little doll of knotted sedge
		x = -0.12 + k * 0.04
		p.seg((x * 0.6, 0, 0.95), (x * 2.2, 0, 0.0), 0.03, 0.02, LEAF if k % 2 else PINE, sides=4)
	p.blob((0.3, 0.2, 0.3), (0, 0, 0.9), PINE, segs=(8, 6))                                 # its head
	for sx in (-1, 1):
		p.seg((0, -0.02, 0.65), (sx * 0.38, -0.02, 0.5), 0.035, 0.025, LEAF, sides=4)      # arms
	for z in (0.72, 0.4):                                                                 # red twine
		p.seg((0, 0, z), (0, 0, z + 0.05), 0.11 if z > 0.5 else 0.16, 0.11 if z > 0.5 else 0.16, CLOTH_RED, sides=6)
	for sx in (-1, 1):                                                                    # button eyes of bone
		p.blob((0.07, 0.04, 0.07), (sx * 0.07, -0.14, 0.92), BONE, segs=(6, 4))
	p.blob((0.12, 0.1, 0.14), (0.16, -0.12, 0.55), BONE, segs=(6, 4))                       # a knucklebone tied to its chest
	return p.build()


def tidesworn_insignia():
	p = Prop("tidesworn_insignia", 663)
	outline = [(-0.42, 1.0), (0.42, 1.0), (0.42, 0.45), (0.0, -0.05), (-0.42, 0.45)]       # a shield-shaped badge
	_slab(p, outline, -0.05, 0.05, IRON)
	for a, b in zip(outline, outline[1:] + outline[:1]):
		p.seg((a[0], -0.07, a[1]), (b[0], -0.07, b[1]), 0.035, 0.035, TEAL, sides=4)
	p.seg((0, -0.09, 0.12), (0, -0.09, 0.85), 0.03, 0.03, GOLD, sides=5, glow=0.6)          # the Tide Kings' trident
	p.seg((-0.2, -0.09, 0.62), (0.2, -0.09, 0.62), 0.03, 0.03, GOLD, sides=5, glow=0.6)
	for x in (-0.2, 0.0, 0.2):
		p.seg((x, -0.09, 0.62), (x, -0.09, 0.9 if x == 0 else 0.84), 0.03, 0.0, GOLD, sides=4, glow=0.6)
	for (x, z) in ((-0.3, 0.85), (0.28, 0.4), (-0.15, 0.25)):                             # barnacles
		p.seg((x, -0.06, z), (x, -0.14, z), 0.05, 0.025, STONE_LIGHT, sides=6)
	return p.build()


def naga_scale():
	p = Prop("naga_scale", 665)
	outline = []
	for k in range(15):                                                                   # a broad, rounded scale
		a = math.radians(200 + k * (140 / 14))
		outline.append((math.cos(a) * 0.5, 0.5 + math.sin(a) * 0.5))
	outline += [(0.36, 0.85), (0.0, 1.2), (-0.36, 0.85)]
	_slab(p, outline, -0.05, 0.05, AQUA, grad=(0.0, 0.8))
	for a, b in zip(outline[:14], outline[1:15]):                                         # edged in gold
		p.seg((a[0], -0.06, a[1]), (b[0], -0.06, b[1]), 0.04, 0.04, GOLD, sides=4, glow=0.4)
	for k, x in enumerate((-0.22, 0.0, 0.22)):                                             # iridescent ridges
		p.seg((x * 0.5, -0.07, 1.0 - abs(x)), (x, -0.07, 0.12 + abs(x) * 0.4), 0.03, 0.015, SEAFOAM, sides=4, glow=0.8)
	return p.build()


def tempest_shard():
	p = Prop("tempest_shard", 667)
	p.seg((0, 0, 0.0), (0.08, 0, 1.2), 0.3, 0.0, SKY, sides=5, glow=1.2, twist=10)          # a jagged crystal of storm
	p.seg((0.25, 0.05, 0.0), (0.42, 0.05, 0.6), 0.16, 0.0, SKY, sides=5, glow=1.0)
	p.seg((-0.22, 0.05, 0.0), (-0.36, 0.05, 0.5), 0.13, 0.0, SKY, sides=5, glow=1.0)
	p.rock((0.6, 0.45, 0.2), (0, 0, 0.02), STONE_DARK, jitter=0.05)
	pts = [(0.05, -0.2, 1.0), (-0.08, -0.22, 0.72), (0.08, -0.22, 0.6), (-0.05, -0.22, 0.3)]   # lightning trapped inside
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.035, 0.03, CLOTH_WHITE, sides=4, glow=3.0)
	for (x, z) in ((0.35, 1.0), (-0.3, 0.85), (0.45, 0.45)):                               # sparks
		p.blob((0.06, 0.06, 0.06), (x, -0.2, z), GOLD, segs=(5, 3), glow=3.0)
	return p.build()


def crab_carapace():
	p = Prop("crab_carapace", 669)
	p.blob((1.2, 0.9, 0.4), (0, 0, 0.18), CLAY, segs=(14, 8), grad=(0.0, 0.8))               # a broad red-brown shell
	for k in range(7):                                                                    # a spiny front edge
		a = math.radians(200 + k * 20)
		p.seg((math.cos(a) * 0.55, math.sin(a) * 0.42, 0.18), (math.cos(a) * 0.72, math.sin(a) * 0.52, 0.2), 0.06, 0.0, EMBER, sides=4)
	for (x, y) in ((-0.25, 0.05), (0.25, 0.05), (0.0, -0.15), (0.0, 0.2)):                 # bumps
		p.blob((0.14, 0.14, 0.08), (x, y, 0.37), EMBER, segs=(6, 4))
	for sx in (-1, 1):                                                                    # eye sockets
		p.blob((0.1, 0.08, 0.08), (sx * 0.12, -0.42, 0.24), STONE_DARK, segs=(6, 4))
	return p.build()


def bloatking_crown():
	p = Prop("bloatking_crown", 671)
	_loop(p, (0, 0, 0.18), 0.48, True, 0.1, GOLD, n=16, squash=0.9)                      # a squat gold band, dented
	for k in range(6):                                                                    # stubby, uneven points
		a = k * math.tau / 6 + 0.25
		h = 0.5 + (k % 3) * 0.08
		p.seg((math.cos(a) * 0.48, math.sin(a) * 0.43, 0.22), (math.cos(a) * 0.5, math.sin(a) * 0.45, h), 0.1, 0.03, GOLD, sides=5)
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.5, math.sin(a) * 0.45, h + 0.03), LEAF, segs=(6, 4), glow=0.8)
	p.blob((0.9, 0.75, 0.06), (0.15, 0.1, 0.44), LEAF, rot=(8, -12, 0), segs=(12, 4), grad=(0.1, 0.6))   # a lily pad worn over one side
	p.blob((0.2, 0.12, 0.2), (0, -0.46, 0.24), CLOTH_RED, segs=(8, 6), glow=0.8)            # a great red stone in front
	return p.build()


def stilt_legs_plume():
	p = Prop("stilt_legs_plume", 673)
	for (tip, sw) in (((-0.55, 1.2), STONE_LIGHT), ((0.5, 1.25), STONE_LIGHT), ((0.0, 1.5), CLOTH_WHITE)):   # an old heron's crest
		_vane(p, (0.0, -0.05 if sw == CLOTH_WHITE else 0.05, 0.1), (tip[0], -0.05 if sw == CLOTH_WHITE else 0.05, tip[1]), 0.17, sw,
			  tip_swatch=STONE_DARK)
	for k in range(2):                                                                    # its two long black crest plumes
		pts = [(0.05, -0.1, 0.3), (0.3 + k * 0.1, -0.1, 0.9), (0.7 + k * 0.1, -0.1, 1.35 - k * 0.15)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.03, 0.02, STONE_DARK, sides=4)
	p.seg((0, -0.1, -0.05), (0, -0.1, 0.2), 0.1, 0.1, WOOD_GRAY, sides=8)                   # bound with old reed cord
	return p.build()


def headwomans_lotus():
	p = Prop("headwomans_lotus", 675)
	_lotus(p, (0, 0, 0.1), 1.2, PINK, glow=0.9)                                            # a pale lotus that still glows
	for k in range(4):                                                                    # ghostly motes over it
		a = k * 1.6
		p.blob((0.07, 0.07, 0.07), (math.cos(a) * 0.4, -0.2, 0.85 + (k % 2) * 0.18), CLOTH_WHITE, segs=(5, 3), glow=2.4)
	return p.build()


def marrowroot_heart():
	p = Prop("marrowroot_heart", 677)
	for sx in (-1, 1):                                                                    # a heart grown of root and bark
		p.blob((0.55, 0.45, 0.55), (sx * 0.22, 0, 0.66), WOOD, segs=(10, 8), grad=(0.2, 0.9), jitter=0.02)
	p.seg((0, 0, 0.64), (0.03, 0, -0.02), 0.47, 0.0, WOOD, sides=10, grad=(0.2, 0.9))
	for sx in (-1, 1):                                                                    # root stumps where vessels would be
		p.seg((sx * 0.15, 0, 0.85), (sx * 0.3, 0, 1.12), 0.09, 0.05, WOOD_GRAY, sides=6)
		p.seg((sx * 0.3, 0, 1.12), (sx * 0.45, 0, 1.18), 0.05, 0.02, WOOD_GRAY, sides=5)
	for sx in (-1, 1):                                                                    # a few rootlets curling off the point
		p.seg((sx * 0.08, 0, 0.12), (sx * 0.3, -0.05, -0.05), 0.04, 0.015, WOOD_GRAY, sides=4)
	for a, b in (((-0.25, 0.85), (-0.08, 0.6)), ((-0.08, 0.6), (-0.18, 0.35)), ((-0.08, 0.6), (0.18, 0.66)), ((0.18, 0.66), (0.25, 0.88)),
				 ((0.18, 0.66), (0.1, 0.35))):
		p.seg((a[0], -0.27, a[1]), (b[0], -0.27, b[1]), 0.04, 0.035, (6, 1), sides=4, glow=2.4)   # sickly green veins, still beating
	for (x, z) in ((0.28, 0.85), (-0.3, 0.45)):                                           # moss
		p.blob((0.2, 0.12, 0.14), (x, -0.2, z), LEAF, segs=(6, 4))
	return p.build()


def varundra_crown():
	p = Prop("varundra_crown", 679)
	_loop(p, (0, 0, 0.15), 0.46, True, 0.09, GOLD, n=18)                                   # a tall gold crown
	_loop(p, (0, 0, 0.36), 0.44, True, 0.05, GOLD, n=18)
	for k in range(7):                                                                    # tines like tridents and waves
		a = math.radians(-90 + (k - 3) * 30)
		x, y = math.cos(a) * 0.46, math.sin(a) * 0.46
		h = 0.95 if k == 3 else (0.78 if k % 2 else 0.68)
		p.seg((x, y, 0.2), (x * 1.08, y * 1.08, h), 0.07, 0.02, GOLD, sides=5, glow=0.3)
		p.blob((0.1, 0.1, 0.1), (x * 1.08, y * 1.08, h + 0.02), CLOTH_WHITE, segs=(8, 6), glow=0.5)   # pearls
	for k in range(4):                                                                    # the back of the crown
		a = math.radians(30 + k * 40)
		p.seg((math.cos(a) * 0.46, math.sin(a) * 0.46, 0.2), (math.cos(a) * 0.48, math.sin(a) * 0.48, 0.6), 0.06, 0.02, GOLD, sides=5)
	p.blob((0.2, 0.12, 0.26), (0, -0.52, 0.28), WATER, segs=(8, 6), glow=1.6)                # a great sea-blue stone
	for sx in (-1, 1):
		p.blob((0.12, 0.08, 0.12), (sx * 0.3, -0.4, 0.26), SKY, segs=(6, 4), glow=1.2)
	return p.build()


def sessavi_pearl():
	p = Prop("sessavi_pearl", 681)
	p.blob((0.62, 0.6, 0.62), (0, 0, 0.62), PETAL_PURPLE, segs=(16, 12), grad=(0.0, 0.6), glow=0.8)   # a great dark pearl
	p.blob((0.14, 0.06, 0.1), (-0.12, -0.3, 0.76), CLOTH_WHITE, segs=(6, 4), glow=1.5)          # its sheen
	for k in range(4):                                                                    # held in golden serpent coils
		a = k * math.tau / 4 + 0.4
		pts = [(math.cos(a) * 0.22, math.sin(a) * 0.22, 0.05), (math.cos(a) * 0.34, math.sin(a) * 0.34, 0.35),
			   (math.cos(a + 0.4) * 0.3, math.sin(a + 0.4) * 0.3, 0.72)]
		for u, v in zip(pts, pts[1:]):
			p.seg(u, v, 0.05, 0.04, GOLD, sides=5)
		p.blob((0.09, 0.07, 0.07), pts[-1], GOLD, segs=(6, 4))
	p.seg((0, 0, -0.05), (0, 0, 0.12), 0.3, 0.2, AQUA, sides=10)                            # on a sea-glass base
	return p.build()


def wardens_chain():
	p = Prop("wardens_chain", 683)
	d = Vector((1.0, 0, 0.8)).normalized()
	side = Vector((-d.z, 0, d.x))
	o = Vector((-0.7, 0, 0.0))
	for k in range(3):                                                                    # heavy iron links
		c = o + d * (0.42 * k)
		_oval(p, c, d, Vector((0, 1, 0)) if k % 2 else side, 0.3, 0.17, 0.1, STONE_DARK, n=14)
	c = o + d * 1.26                                                                      # the last one burst open
	for k in range(7):
		a0, a1 = 0.7 + k * 0.7, 0.7 + (k + 1) * 0.7
		p.seg(tuple(c + d * math.cos(a0) * 0.3 + side * math.sin(a0) * 0.17), tuple(c + d * math.cos(a1) * 0.3 + side * math.sin(a1) * 0.17),
			  0.1, 0.1, STONE_DARK, sides=5)
	for pts in (((0.15, -0.3, 0.95), (0.0, -0.3, 0.75), (0.2, -0.3, 0.65), (0.08, -0.3, 0.45)),                # still crackling with storm
				((-0.45, -0.3, 0.55), (-0.3, -0.3, 0.42), (-0.4, -0.3, 0.26)),
				((0.55, -0.3, 1.25), (0.72, -0.3, 1.1), (0.6, -0.3, 0.95))):
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.045, 0.04, SKY, sides=4, glow=2.8)
	return p.build()


def chitterjaw_claw():
	p = Prop("chitterjaw_claw", 685)
	p.blob((0.7, 0.45, 0.5), (-0.3, 0, 0.35), CLOTH_RED, segs=(12, 8), grad=(0.0, 0.8))       # a massive crab claw
	pts = [(-0.05, 0, 0.45), (0.35, 0, 0.62), (0.62, 0, 0.72), (0.8, 0, 0.62)]               # the fixed finger
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.2 - i * 0.05, 0.15 - i * 0.05, CLOTH_RED, sides=8, grad=(0.0, 0.7))
	pts = [(-0.05, 0, 0.25), (0.3, 0, 0.12), (0.55, 0, 0.18), (0.7, 0, 0.35)]               # and the moving one, open
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.16 - i * 0.04, 0.12 - i * 0.04, CLOTH_RED, sides=8, grad=(0.0, 0.7))
	for k in range(4):                                                                    # jagged teeth along both
		x = 0.15 + k * 0.14
		p.seg((x, -0.02, 0.52 + k * 0.03), (x + 0.03, -0.02, 0.42 + k * 0.03), 0.04, 0.0, BONE, sides=4)
		p.seg((x, -0.02, 0.2 + k * 0.01), (x + 0.03, -0.02, 0.3 + k * 0.01), 0.035, 0.0, BONE, sides=4)
	p.seg((-0.62, 0, 0.3), (-0.8, 0, 0.2), 0.16, 0.14, PINK, sides=8)                       # the torn stump
	for (x, z) in ((-0.4, 0.55), (-0.2, 0.58), (-0.3, 0.2)):                               # old barnacles
		p.seg((x, -0.18, z), (x, -0.26, z), 0.05, 0.025, STONE_LIGHT, sides=6)
	return p.build()


def reedwalker_boots():
	p = Prop("reedwalker_boots", 687)
	p.seg((0, 0, 0.18), (0.02, 0, 0.9), 0.2, 0.23, HIDE, sides=10, grad=(0.1, 0.7))         # a tall supple boot
	p.blob((0.62, 0.3, 0.26), (-0.2, 0, 0.13), HIDE, segs=(10, 6), grad=(0.2, 0.9))          # its foot
	p.seg((-0.2, 0, 0.0), (-0.2, 0, 0.04), 0.3, 0.3, WOOD, sides=10)                          # a sole
	for k in range(4):                                                                    # wrapped in woven reed
		z = 0.3 + k * 0.15
		p.seg((0, 0, z), (0.02, 0, z + 0.05), 0.225, 0.23, LEAF if k % 2 else PINE, sides=10)
	p.seg((0.02, 0, 0.9), (0.02, 0, 0.98), 0.25, 0.25, WOOD, sides=10)                        # cuff
	p.seg((0.2, -0.1, 0.94), (0.35, -0.12, 1.15), 0.035, 0.0, LEAF, sides=4)                 # a reed tucked in
	return p.build()


def bloatking_scepter():
	p = Prop("bloatking_scepter", 689)
	p.seg((-0.5, 0, -0.2), (0.15, 0, 0.7), 0.05, 0.06, WOOD, sides=8)                         # a reed-wrapped shaft
	for k in range(4):
		t = 0.2 + k * 0.12
		p.seg((-0.5 + 0.65 * t, 0, -0.2 + 0.9 * t), (-0.47 + 0.65 * t, 0, -0.16 + 0.9 * t), 0.07, 0.07, GOLD, sides=8)
	p.blob((0.62, 0.5, 0.5), (0.25, 0, 0.9), LEAF, segs=(12, 8), grad=(0.0, 0.8))             # a bloated frog's head
	p.blob((0.3, 0.26, 0.24), (0.24, -0.1, 0.75), GOLD, segs=(8, 6), glow=0.4)                # its swollen throat sac
	for sx in (-1, 1):
		p.blob((0.2, 0.18, 0.2), (0.25 + sx * 0.18, -0.08, 1.1), LEAF, segs=(8, 5))
		p.blob((0.1, 0.06, 0.1), (0.25 + sx * 0.18, -0.18, 1.12), CLOTH_RED, segs=(6, 4), glow=1.8)   # ruby eyes
	for k in range(3):                                                                    # a little gold crown on it
		x = 0.13 + k * 0.12
		p.seg((x, 0, 1.12), (x, 0, 1.3), 0.05, 0.0, GOLD, sides=4)
	return p.build()


def heronfeather_cloak():
	p = Prop("heronfeather_cloak", 691)
	outline = [(-0.28, 1.0), (0.28, 1.0), (0.6, 0.05), (-0.6, 0.05)]                      # a mantle of heron feathers
	_slab(p, outline, 0.02, 0.08, STONE_DARK)
	for row in range(5):                                                                  # layered rows of feathers
		z = 0.85 - row * 0.18
		w = 0.28 + (1 - z) * 0.33
		n = 3 + row
		for k in range(n):
			x = -w + (k + 0.5) * (2 * w / n)
			p.blob((2 * w / n * 1.1, 0.06, 0.3), (x, -0.02 - row * 0.01, z - 0.08), STONE_LIGHT if (k + row) % 3 else CLOTH_WHITE,
				   segs=(6, 4), grad=(0.0, 0.7))
	p.seg((-0.3, -0.05, 1.0), (0.3, -0.05, 1.0), 0.05, 0.05, HIDE, sides=6)                  # a leather collar
	p.blob((0.16, 0.08, 0.16), (0, -0.12, 0.98), GOLD, segs=(8, 6), glow=0.4)                 # and its clasp
	return p.build()


def veyamar_locket():
	p = Prop("veyamar_locket", 693)
	_cord(p, 0.45, 0.82, STONE_LIGHT)
	p.blob((0.46, 0.14, 0.58), (0, -0.3, 0.32), STONE_LIGHT, segs=(12, 8), grad=(0.0, 0.7))   # an oval silver locket
	_loop(p, (0, -0.38, 0.32), 0.21, False, 0.025, GOLD, n=16, squash=1.28)
	for k in range(5):                                                                    # a lotus worked in pink enamel
		a = math.radians(90 + (k - 2) * 28)
		p.blob((0.07, 0.04, 0.17), (math.cos(a) * 0.08, -0.39, 0.26 + math.sin(a) * 0.08), PINK, rot=(0, -math.degrees(a) + 90, 0),
			   segs=(6, 4), glow=0.6)
	p.seg((0, -0.3, 0.62), (0, -0.3, 0.7), 0.06, 0.06, GOLD, sides=6)                         # its bail
	return p.build()


def sedgebane_charm():
	p = Prop("sedgebane_charm", 695)
	_ring(p, WOOD)                                                                         # a band of rowan wood
	for k in range(10):                                                                   # bound in pale braided twine
		a = k * math.tau / 10 + 0.3
		p.seg((math.cos(a) * 0.4, -0.1, 0.4 + math.sin(a) * 0.4), (math.cos(a + 0.2) * 0.4, 0.1, 0.4 + math.sin(a + 0.2) * 0.4),
			  0.035, 0.035, BONE, sides=4)
	p.seg((0, 0.06, 0.86), (0, -0.1, 0.86), 0.2, 0.2, GOLD, sides=8)                          # a setting
	p.blob((0.26, 0.14, 0.26), (0, -0.14, 0.88), CLOTH_WHITE, segs=(8, 6), glow=1.8)          # a warding stone, white-hot against hexes
	for k in range(6):
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.18, -0.16, 0.88 + math.sin(a) * 0.18), (math.cos(a) * 0.3, -0.16, 0.88 + math.sin(a) * 0.3), 0.03, 0.0, GOLD,
			  sides=4, glow=1.2)
	return p.build()


def tideking_helm():
	p = Prop("tideking_helm", 697)
	for z0, z1, r0, r1 in ((0.0, 0.3, 0.42, 0.42), (0.3, 0.52, 0.42, 0.34), (0.52, 0.68, 0.34, 0.2), (0.68, 0.76, 0.2, 0.0)):
		p.seg((0, 0, z0), (0, 0, z1), r0, r1, TEAL, sides=16, grad=(0.0, 0.8))             # a sea-green bronze dome
	_loop(p, (0, 0, 0.3), 0.41, True, 0.05, GOLD, n=18)                                      # a gold brow band
	p.seg((0, -0.44, 0.3), (0, -0.44, 0.05), 0.07, 0.04, GOLD, sides=5)                       # nasal guard
	for sx in (-1, 1):                                                                    # cheek guards
		p.box((0.16, 0.25, 0.32), (sx * 0.33, -0.2, 0.12), TEAL, rot=(0, 0, sx * -20))
	outline = [(-0.05, 0.62), (0.15, 1.12), (0.3, 1.07), (0.4, 0.87), (0.48, 0.7), (0.3, 0.45)]  # a fish-fin crest
	_slab(p, outline, -0.03, 0.03, AQUA, grad=(0.0, 0.8))
	for k in range(4):
		x = 0.05 + k * 0.1
		p.seg((x, -0.04, 0.62), (x + 0.07, -0.04, 1.04 - k * 0.07), 0.02, 0.015, GOLD, sides=4)
	p.blob((0.14, 0.08, 0.14), (0, -0.45, 0.4), WATER, segs=(8, 6), glow=1.6)                # a pearl-blue stone on the brow
	return p.build()


def pearl_of_the_deeps():
	p = Prop("pearl_of_the_deeps", 699)
	_cord(p, 0.45, 0.82, GOLD)
	for k in range(5):                                                                    # a cage of branching coral
		a = k * math.tau / 5 + 0.3
		p.seg((math.cos(a) * 0.12, -0.3 + math.sin(a) * 0.06, 0.02), (math.cos(a) * 0.28, -0.3 + math.sin(a) * 0.1, 0.35), 0.04, 0.03, CLOTH_RED, sides=5)
		p.seg((math.cos(a) * 0.28, -0.3 + math.sin(a) * 0.1, 0.35), (math.cos(a) * 0.1, -0.3 + math.sin(a) * 0.05, 0.62), 0.03, 0.02, CLOTH_RED, sides=5)
	p.blob((0.42, 0.4, 0.42), (0, -0.3, 0.33), CLOTH_WHITE, segs=(14, 10), grad=(0.0, 0.4), glow=0.6)   # a perfect pearl
	for k in range(6):                                                                    # a deep-sea glow round it
		a = k * math.tau / 6
		p.blob((0.07, 0.04, 0.07), (math.cos(a) * 0.36, -0.42, 0.33 + math.sin(a) * 0.36), WATER, segs=(5, 3), glow=2.6)
	p.seg((0, -0.3, 0.6), (0, -0.3, 0.72), 0.07, 0.07, GOLD, sides=6)
	return p.build()


def stormbound_bracer():
	p = Prop("stormbound_bracer", 700)
	c, d = Vector((0, 0, 0.45)), Vector((0.7, 0, 0.7)).normalized()
	p.seg(tuple(c - d * 0.4), tuple(c + d * 0.4), 0.34, 0.28, STONE_DARK, sides=14, grad=(0.1, 0.8))     # a heavy iron bracer, tapering
	for t, r in ((-0.36, 0.36), (0.36, 0.3)):                                             # gold rims
		p.seg(tuple(c + d * (t - 0.04)), tuple(c + d * (t + 0.04)), r, r, GOLD, sides=14)
	p.seg(tuple(c + d * 0.4), tuple(c + d * 0.38), 0.2, 0.2, STONE_DARK, sides=14)           # hollow
	n = Vector((-d.z, 0, d.x))
	pts = [c - d * 0.25 + n * 0.1, c - d * 0.05 - n * 0.08, c + d * 0.05 + n * 0.1, c + d * 0.25 - n * 0.06]   # a lightning rune
	for a, b in zip(pts, pts[1:]):
		p.seg(tuple(a + Vector((0, -0.36, 0))), tuple(b + Vector((0, -0.36, 0))), 0.035, 0.03, SKY, sides=4, glow=2.6)
	for k in range(3):                                                                    # studs
		q = c + d * (-0.2 + k * 0.2) + n * 0.3
		p.blob((0.09, 0.09, 0.09), tuple(q + Vector((0, -0.12, 0))), GOLD, segs=(6, 4))
	return p.build()


def chitin_shield():
	p = Prop("chitin_shield", 702)
	p.seg((0, 0.06, 0.6), (0, -0.1, 0.6), 0.62, 0.55, CLAY, sides=16, grad=(0.1, 0.8))        # a round shield of crab shell
	p.blob((1.0, 0.3, 1.0), (0, -0.1, 0.6), CLOTH_RED, segs=(14, 8), grad=(0.0, 0.8))          # domed, red
	for k in range(10):                                                                   # a spiny rim
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.55, -0.05, 0.6 + math.sin(a) * 0.55), (math.cos(a) * 0.78, -0.05, 0.6 + math.sin(a) * 0.78), 0.07, 0.0,
			  EMBER, sides=4)
	for (x, z, s) in ((-0.2, 0.75, 0.14), (0.2, 0.75, 0.14), (0, 0.45, 0.18), (-0.25, 0.4, 0.1), (0.25, 0.4, 0.1)):   # knobs
		p.blob((s, s * 0.8, s), (x, -0.23, z), EMBER, segs=(6, 4))
	for sx in (-1, 1):
		p.seg((sx * 0.08, -0.2, 0.95), (sx * 0.08, -0.32, 0.95), 0.06, 0.04, STONE_DARK, sides=6)   # old eye stalks
	return p.build()


def tidesworn_blade():
	p = Prop("tidesworn_blade", 704)
	loc = []
	for k in range(9):                                                                    # a sea-steel blade with a rippling edge
		s = 0.3 + k * 0.12
		loc.append((s, 0.1 + math.sin(k * 1.6) * 0.025))
	loc.append((1.45, 0.0))
	for k in range(8, -1, -1):
		s = 0.3 + k * 0.12
		loc.append((s, -0.09))
	_slab(p, _rot2(loc, 48, (-0.55, -0.35)), -0.03, 0.03, STONE_LIGHT, grad=(0.0, 0.6))
	edge = _rot2([(0.35, 0.0), (1.3, 0.0)], 48, (-0.55, -0.35))
	p.seg((edge[0][0], -0.05, edge[0][1]), (edge[1][0], -0.05, edge[1][1]), 0.02, 0.01, WATER, sides=4, glow=1.4)   # a blue fuller
	g = _rot2([(0.28, -0.35), (0.28, 0.35)], 48, (-0.55, -0.35))                          # a crossguard curled like waves
	p.seg((g[0][0], 0, g[0][1]), (g[1][0], 0, g[1][1]), 0.05, 0.05, GOLD, sides=6)
	for end in g:
		p.blob((0.12, 0.1, 0.12), (end[0], 0, end[1]), GOLD, segs=(6, 4))
	h = _rot2([(0.28, 0.0), (-0.05, 0.0), (-0.12, 0.0)], 48, (-0.55, -0.35))
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.055, TEAL, sides=6)          # a sharkskin grip
	p.blob((0.14, 0.14, 0.14), (h[2][0], 0, h[2][1]), WATER, segs=(8, 6), glow=1.2)           # a sea-glass pommel
	return p.build()


def naga_fang_dirk():
	p = Prop("naga_fang_dirk", 706)
	pts = [(-0.05, 0, 0.3), (0.2, 0, 0.62), (0.38, 0, 0.9), (0.45, 0, 1.15)]                  # a long curved serpent fang for a blade
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.13 - i * 0.04, 0.09 - i * 0.04 if i < 2 else 0.0, BONE, sides=6, grad=(0.0, 0.6))
	gy = (-0.14, -0.1, -0.06)
	for k, (a, b) in enumerate(zip(pts[:3], pts[1:3])):                                   # its venom groove, glowing
		p.seg((a[0] + 0.02, gy[k], a[2]), (b[0] + 0.02, gy[k + 1] if k < 1 else gy[k], b[2]), 0.025, 0.02, SEAFOAM, sides=4, glow=2.2)
	p.seg((-0.22, 0, 0.42), (0.14, 0, 0.18), 0.05, 0.05, GOLD, sides=6)                       # a gold guard
	p.seg((-0.05, 0, 0.3), (-0.3, 0, -0.05), 0.065, 0.06, AQUA, sides=6)                      # a scaled aqua grip
	for k in range(3):
		t = 0.2 + k * 0.25
		p.seg((-0.05 - 0.25 * t, 0, 0.3 - 0.35 * t), (-0.07 - 0.25 * t, 0, 0.27 - 0.35 * t), 0.075, 0.075, TEAL, sides=6)
	p.blob((0.16, 0.14, 0.16), (-0.33, 0, -0.09), GOLD, segs=(8, 5))                         # a snake-head pommel
	p.blob((0.05, 0.04, 0.05), (-0.36, -0.08, -0.06), CLOTH_RED, segs=(5, 3), glow=1.8)
	p.blob((0.07, 0.05, 0.07), (0.47, -0.05, 1.05), SEAFOAM, segs=(5, 3), glow=2.0)            # a drop at the tip
	return p.build()


# ---------------------------------------------------------------- gloves, sleeves and bracers
# KayKit arms end in a hand, so the body-part path drew gloves and sleeves alike.
# Hands items are drawn as a pair of gloves standing fingers up; arms items as a
# forearm piece lying on the diagonal with an empty wrist, so the two never mix.

SEA_STONE = (2, 1)    # blue-gray: shark hide


def _hand_frame(off, tilt, sx):
	"""Maps a glove's own coordinates (x across the hand, -y its back, z up the
	fingers) into the scene: mirrored by sx, leaned by tilt degrees, moved to off."""
	ca, sa = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))

	def f(x, y, z):
		x *= sx
		return (off[0] + x * ca + z * sa, off[1] + y, off[2] - x * sa + z * ca)
	f.tilt = tilt
	return f


FINGERS = ((-0.17, 0.26), (-0.057, 0.33), (0.057, 0.36), (0.17, 0.32))   # (x, length) little finger to index


def _finger(p, f, x, length, r, swatch, grad, glow=0.0, lames=0, lame_swatch=None, tip=True):
	base, top = (x, 0, 0.7), (x * 1.25, 0, 0.7 + length)
	if lames:
		for k in range(lames):                                                       # jointed plates, each a little wider at its base
			a, b = k / lames, (k + 0.92) / lames
			pa = tuple(base[i] + (top[i] - base[i]) * a for i in range(3))
			pb = tuple(base[i] + (top[i] - base[i]) * b for i in range(3))
			p.seg(f(*pa), f(*pb), r * 1.12, r * 0.95, lame_swatch if k % 2 else swatch, sides=8, grad=grad)
		p.seg(f(*top), f(top[0] * 1.03, 0, top[2] + 0.08), r * 0.95, 0.0, swatch, sides=8, grad=grad)   # a pointed tip
		return
	p.seg(f(*base), f(*top), r, r * 0.88, swatch, sides=8, grad=grad, glow=glow)
	if tip:
		p.blob((r * 1.76, r * 1.76, r * 1.76), f(*top), swatch, segs=(8, 5), grad=grad, glow=glow)


def _glove(p, f, body, cuff, trim, grad=(0.1, 0.8), style="glove", cuff_r=0.24, skin=HIDE):
	"""One glove. style: glove, gauntlet (plates, knuckle ridge, flared cuff),
	mitt (fingers in one pouch) or wrap (bandaged, fingertips bare)."""
	rot = (0, f.tilt, 0)
	if style == "gauntlet":
		p.seg(f(0, 0, -0.02), f(0, 0, 0.34), 0.34, 0.21, cuff, sides=14, grad=grad)             # flared cuff
		p.seg(f(0, 0, -0.04), f(0, 0, 0.02), 0.36, 0.35, trim, sides=14)                       # its rolled rim
		p.seg(f(0, 0, 0.16), f(0, 0, 0.2), 0.29, 0.28, trim, sides=14)
		p.blob((0.52, 0.26, 0.46), f(0, 0, 0.55), body, rot=rot, segs=(12, 8), grad=grad)
		p.blob((0.48, 0.12, 0.34), f(0, -0.09, 0.56), cuff, rot=rot, segs=(10, 6), grad=grad)   # back-of-hand plate
		for x, _ in FINGERS:                                                          # knuckle plates
			p.blob((0.14, 0.12, 0.11), f(x * 1.05, -0.08, 0.74), trim, rot=rot, segs=(8, 5))
		for x, length in FINGERS:
			_finger(p, f, x, length, 0.07, body, grad, lames=3, lame_swatch=cuff)
		p.seg(f(0.2, -0.02, 0.45), f(0.4, -0.04, 0.64), 0.09, 0.08, cuff, sides=8, grad=grad)   # thumb
		p.seg(f(0.4, -0.04, 0.64), f(0.47, -0.05, 0.78), 0.08, 0.0, body, sides=8, grad=grad)
		return
	if style == "wrap":
		for k in range(5):                                                            # wound bands up the wrist, each askew
			z = 0.0 + k * 0.1
			p.seg(f(0, 0, z), f(0.02, 0, z + 0.09), 0.2 + k * 0.004, 0.2, body if k % 2 else cuff, sides=12, grad=grad, twist=k * 20)
		p.blob((0.5, 0.25, 0.44), f(0, 0, 0.57), body, rot=rot, segs=(12, 8), grad=grad)
		for k in range(3):                                                            # bands across the back of the hand
			z = 0.44 + k * 0.12
			p.seg(f(-0.25, -0.1, z - 0.04), f(0.25, -0.1, z + 0.04), 0.03, 0.03, cuff, sides=5)
		p.seg(f(-0.26, -0.02, 0.74), f(0.26, -0.02, 0.74), 0.08, 0.08, cuff, sides=8)       # the knuckle band
		for x, length in FINGERS:                                                    # bare fingertips out the top
			_finger(p, f, x, length * 0.7, 0.062, skin, (0.0, 0.5))
		p.seg(f(0.2, -0.02, 0.45), f(0.4, -0.04, 0.66), 0.085, 0.075, body, sides=8, grad=grad)
		p.blob((0.13, 0.13, 0.13), f(0.4, -0.04, 0.66), skin, segs=(6, 4), grad=(0.0, 0.5))
		p.seg(f(-0.2, -0.12, 0.2), f(-0.34, -0.14, -0.12), 0.05, 0.03, trim, sides=5)        # the loose tail of the wrap
		return
	p.seg(f(0, 0, 0.0), f(0, 0, 0.34), cuff_r, 0.2, cuff, sides=12, grad=grad)                 # cuff
	p.seg(f(0, 0, -0.02), f(0, 0, 0.05), cuff_r + 0.02, cuff_r + 0.02, trim, sides=12)
	p.blob((0.5, 0.24, 0.46), f(0, 0, 0.55), body, rot=rot, segs=(12, 8), grad=grad)
	if style == "mitt":
		p.blob((0.46, 0.22, 0.52), f(0.02, 0, 0.86), body, rot=rot, segs=(12, 8), grad=grad)   # the fingers in one pouch
		p.seg(f(-0.2, -0.1, 0.72), f(0.2, -0.1, 0.72), 0.02, 0.02, trim, sides=4)          # a stitched seam
	else:
		for x, length in FINGERS:
			_finger(p, f, x, length, 0.068, body, grad)
	p.seg(f(0.2, -0.02, 0.45), f(0.4, -0.04, 0.66), 0.08, 0.072, body, sides=8, grad=grad)     # thumb
	p.blob((0.13, 0.13, 0.13), f(0.4, -0.04, 0.66), body, segs=(8, 5), grad=grad)


def _glove_pair(name, seed, body, cuff, trim, **kw):
	"""A pair: the left glove behind, the right in front. Returns the Prop and both frames."""
	p = Prop(name, seed)
	frames = [_hand_frame((-0.38, 0.3, 0.14), 16, -1), _hand_frame((0.12, -0.12, 0.0), -8, 1)]
	for f in frames:
		_glove(p, f, body, cuff, trim, **kw)
	return p, frames


def _studs(p, frames, swatch, z=0.62, n=3, y=-0.13, glow=0.0):
	for f in frames:
		for k in range(n):
			x = -0.14 + k * 0.28 / max(n - 1, 1)
			p.blob((0.07, 0.06, 0.07), f(x, y, z), swatch, segs=(6, 4), glow=glow)


def cloth_gloves():
	p, fr = _glove_pair("cloth_gloves", 801, HIDE, BONE, WOOD_GRAY, grad=(0.0, 0.6))
	return p.build()


def leather_gloves():
	p, fr = _glove_pair("leather_gloves", 803, WOOD, WOOD_GRAY, HIDE, grad=(0.1, 0.8))
	return p.build()


def handsewn_leather_gloves():
	p, fr = _glove_pair("handsewn_leather_gloves", 805, CLAY, WOOD, BONE, grad=(0.2, 0.9))
	for f in fr:                                                                     # big hand stitches down the back
		for k in range(4):
			z = 0.42 + k * 0.08
			p.seg(f(-0.03, -0.13, z), f(0.03, -0.13, z + 0.04), 0.014, 0.014, BONE, sides=4)
	return p.build()


def hardened_leather_gloves():
	p, fr = _glove_pair("hardened_leather_gloves", 807, WOOD, STONE_DARK, IRON, grad=(0.4, 1.0))
	for f in fr:                                                                     # a boiled-leather knuckle pad, riveted
		p.blob((0.46, 0.1, 0.14), f(0, -0.1, 0.72), WOOD_GRAY, rot=(0, f.tilt, 0), segs=(10, 5), grad=(0.3, 0.9))
	_studs(p, fr, STONE_LIGHT, z=0.73, n=4, y=-0.16)
	return p.build()


def farmhands_gloves():
	p, fr = _glove_pair("farmhands_gloves", 809, AMBER, WOOD, WOOD_GRAY, grad=(0.3, 0.95), cuff_r=0.27)
	f = fr[1]
	p.blob((0.2, 0.05, 0.18), f(-0.08, -0.13, 0.52), HIDE, rot=(0, f.tilt + 10, 0), segs=(6, 4))   # a patch
	for k in range(4):                                                              # straw caught in the cuff
		a = math.radians(-40 + k * 25)
		p.seg(f(math.sin(a) * 0.2, -0.18, 0.12), f(math.sin(a) * 0.4, -0.22, -0.14 + k * 0.03), 0.014, 0.008, GOLD, sides=4)
	return p.build()


def sharkskin_gloves():
	p, fr = _glove_pair("sharkskin_gloves", 811, SEA_STONE, STONE_DARK, CLOTH_WHITE, grad=(0.35, 1.0))
	for f in fr:                                                                     # a little fin down the back of each
		p.seg(f(0.0, -0.12, 0.4), f(0.0, -0.3, 0.52), 0.07, 0.0, SEA_STONE, sides=4, grad=(0.5, 1.0))
	for f in fr:
		p.seg(f(-0.2, -0.1, 0.12), f(0.2, -0.1, 0.12), 0.015, 0.015, CLOTH_WHITE, sides=4)   # pale belly-hide stripe
	return p.build()


def trollhide_gloves():
	p, fr = _glove_pair("trollhide_gloves", 813, TEAL, WOOD_GRAY, PINE, grad=(0.35, 1.0), cuff_r=0.27)
	for f in fr:                                                                     # warts
		for (x, z) in ((-0.12, 0.5), (0.1, 0.62), (0.02, 0.44), (-0.05, 0.66)):
			p.blob((0.07, 0.05, 0.07), f(x, -0.12, z), PINE, segs=(6, 4))
		for k in range(5):                                                         # a ragged fur trim at the cuff
			a = -0.2 + k * 0.1
			p.seg(f(a, -0.2, 0.02), f(a * 1.2, -0.24, -0.12), 0.04, 0.0, WOOD_GRAY, sides=4)
	return p.build()


def frogskin_gloves():
	p, fr = _glove_pair("frogskin_gloves", 815, LEAF, PINE, GOLD, grad=(0.0, 0.6))
	for f in fr:                                                                     # dark spots and one yellow
		for (x, z, sw) in ((-0.12, 0.5, PINE), (0.08, 0.62, PINE), (0.1, 0.42, GOLD), (-0.04, 0.68, PINE), (-0.17, 0.3, PINE)):
			p.blob((0.09, 0.04, 0.09), f(x, -0.12 if z > 0.36 else -0.2, z), sw, segs=(6, 4), grad=(0.1, 0.5))
	return p.build()


def cinderscale_gloves():
	p, fr = _glove_pair("cinderscale_gloves", 817, IRON, CLOTH_RED, CRIMSON, grad=(0.0, 0.5))
	for f in fr:                                                                     # overlapping charcoal scales, red at the seams
		for row in range(3):
			for k in range(3 - row % 2):
				x = -0.14 + k * 0.14 + (0.07 if row % 2 else 0)
				p.blob((0.13, 0.05, 0.1), f(x, -0.12, 0.44 + row * 0.1), STONE_DARK if (k + row) % 2 else IRON, rot=(0, f.tilt, 0),
					   segs=(6, 4), grad=(0.0, 0.6))
		p.seg(f(-0.2, -0.13, 0.38), f(0.2, -0.13, 0.38), 0.018, 0.018, EMBER, sides=4, glow=1.8)
	return p.build()


def silkweave_gloves():
	p, fr = _glove_pair("silkweave_gloves", 819, CLOTH_WHITE, PETAL_PURPLE, STONE_LIGHT, grad=(0.0, 0.5))
	for f in fr:                                                                     # a web picked out in thread
		for a in (-50, 0, 50):
			r = math.radians(a)
			p.seg(f(0, -0.13, 0.52), f(math.sin(r) * 0.18, -0.13, 0.52 + math.cos(r) * 0.16), 0.01, 0.01, PETAL_PURPLE, sides=4)
	return p.build()


def silkweave_mitts():
	p, fr = _glove_pair("silkweave_mitts", 821, CLOTH_WHITE, PETAL_PURPLE, GOLD, grad=(0.0, 0.5), style="mitt", cuff_r=0.26)
	return p.build()


def rainsilk_gloves():
	p, fr = _glove_pair("rainsilk_gloves", 823, SKY, WATER, CLOTH_WHITE, grad=(0.0, 0.6))
	for f in fr:                                                                     # a raindrop pearl on the back
		p.blob((0.1, 0.06, 0.13), f(0, -0.13, 0.54), AQUA, segs=(8, 5), glow=1.2)
		p.seg(f(0, -0.13, 0.6), f(0, -0.13, 0.66), 0.05, 0.0, AQUA, sides=6, glow=1.2)
	return p.build()


def dawnweave_gloves():
	p, fr = _glove_pair("dawnweave_gloves", 825, PINK, GOLD, GOLD, grad=(0.0, 0.5))
	for f in fr:                                                                     # a small sun on the back
		p.blob((0.1, 0.05, 0.1), f(0, -0.13, 0.54), GOLD, segs=(8, 5), glow=1.0)
		for k in range(6):
			a = k * math.tau / 6
			p.seg(f(math.cos(a) * 0.07, -0.13, 0.54 + math.sin(a) * 0.07), f(math.cos(a) * 0.12, -0.13, 0.54 + math.sin(a) * 0.12),
				  0.015, 0.0, GOLD, sides=4, glow=1.0)
	return p.build()


def ashweave_gloves():
	p, fr = _glove_pair("ashweave_gloves", 827, ASH, STONE_DARK, EMBER, grad=(0.35, 0.7))
	for f in fr:                                                                     # an ember thread across the knuckles
		p.seg(f(-0.22, -0.12, 0.7), f(0.22, -0.12, 0.7), 0.016, 0.016, EMBER, sides=4, glow=2.0)
		p.seg(f(-0.2, -0.2, 0.2), f(0.2, -0.2, 0.2), 0.016, 0.016, EMBER, sides=4, glow=2.0)
	return p.build()


def monks_wraps():
	p, fr = _glove_pair("monks_wraps", 829, CLOTH_WHITE, BONE, CLOTH_RED, grad=(0.0, 0.5), style="wrap")
	return p.build()


def iron_gauntlets():
	p, fr = _glove_pair("iron_gauntlets", 831, STONE_DARK, STONE_DARK, IRON, grad=(0.0, 0.7), style="gauntlet")
	return p.build()


def tempered_gauntlets():
	p, fr = _glove_pair("tempered_gauntlets", 833, STONE_DARK, STONE_LIGHT, SEA_STONE, grad=(0.2, 0.9), style="gauntlet")
	return p.build()


def steel_gauntlets():
	p, fr = _glove_pair("steel_gauntlets", 835, STONE_LIGHT, STONE_LIGHT, IRON, grad=(0.0, 0.45), style="gauntlet")
	_studs(p, fr, GOLD, z=0.3, n=3, y=-0.25)
	return p.build()


def tidesteel_gauntlets():
	p, fr = _glove_pair("tidesteel_gauntlets", 837, AQUA, SEAFOAM, STONE_LIGHT, grad=(0.1, 0.8), style="gauntlet")
	for f in fr:
		p.blob((0.09, 0.07, 0.09), f(0, -0.17, 0.56), CLOTH_WHITE, segs=(8, 5), glow=0.5)   # a pearl in the back plate
	return p.build()


def emberforged_gauntlets():
	p, fr = _glove_pair("emberforged_gauntlets", 839, IRON, STONE_DARK, EMBER, grad=(0.0, 0.6), style="gauntlet")
	for f in fr:                                                                     # forge-glow in the seams
		p.seg(f(-0.2, -0.17, 0.46), f(0.2, -0.17, 0.46), 0.016, 0.016, EMBER, sides=4, glow=2.4)
		p.seg(f(0, -0.17, 0.4), f(0, -0.17, 0.66), 0.016, 0.016, EMBER, sides=4, glow=2.4)
		p.seg(f(-0.28, -0.22, 0.1), f(0.28, -0.22, 0.1), 0.016, 0.016, EMBER, sides=4, glow=2.4)
	return p.build()


# Forearm pieces lie along D through C, elbow low-left, the open wrist high-right toward the camera.
FA_C, FA_D = Vector((0, 0, 0.45)), Vector((0.7, 0, 0.7)).normalized()


def _fa(t, r=0.0, ang=0.0, c=FA_C, d=FA_D):
	"""A point on the forearm: t along it, r out from its axis, ang round it (0 faces the camera)."""
	a = math.radians(ang)
	n = Vector((-d.z, 0, d.x))
	return tuple(c + d * t + (Vector((0, -1, 0)) * math.cos(a) + n * math.sin(a)) * r)


def _fa_r(t, r0, r1, t0, t1):
	return r0 + (r1 - r0) * (t - t0) / (t1 - t0)


SL_C, SL_D = Vector((0, 0, 0.55)), Vector((0.32, 0, -1)).normalized()   # a sleeve hangs from its shoulder, wrist low right


def _sl(t, r=0.0, ang=0.0):
	"""_fa for a hanging sleeve."""
	return _fa(t, r, ang, SL_C, SL_D)


def _sleeve(p, body, hem, grad=(0.1, 0.8), folds=3):
	"""A soft sleeve hanging from an open shoulder, wrinkled, with a flared hem;
	returns its frame's (t0, t1, r0, r1) for trims laid on with _sl."""
	t0, t1, r0, r1 = -0.6, 0.5, 0.36, 0.2
	p.seg(_sl(t0), _sl(t1), r0, r1, body, sides=18, grad=grad)
	p.seg(_sl(t0 - 0.02), _sl(t0 + 0.07), r0 + 0.025, r0 + 0.01, hem, sides=18)            # shoulder seam
	p.seg(_sl(t0 - 0.03), _sl(t0 - 0.02), r0 - 0.04, r0 - 0.04, STONE_DARK, sides=18)       # the open shoulder
	for k in range(folds):                                                            # wrinkles across the front
		tc = -0.3 + k * 0.24
		pts = []
		for j in range(7):
			ang = -80 + j * 26
			t = tc + 0.05 * math.sin(math.radians(ang * 2 + k * 40))
			pts.append(_sl(t, _fa_r(t, r0, r1, t0, t1) + 0.005, ang))
		for u, v in zip(pts, pts[1:]):
			p.seg(u, v, 0.028, 0.028, body, sides=5, grad=(min(grad[1] + 0.1, 1.0), 1.0))
	p.seg(_sl(t1 - 0.1), _sl(t1 + 0.04), r1 + 0.02, r1 + 0.08, hem, sides=18)               # a flared hem
	p.seg(_sl(t1 + 0.04), _sl(t1 + 0.05), r1 + 0.03, r1 + 0.03, STONE_DARK, sides=18)        # and the empty cuff
	return t0, t1, r0, r1


def _vambrace(p, plate, trim, strap, buckle, grad=(0.1, 0.8), glow_line=None):
	"""A hard forearm guard in overlapping plates, a raised ridge, two straps and an empty wrist."""
	t0, t1, r0, r1 = -0.42, 0.42, 0.33, 0.26
	for k in range(3):                                                                # lames, each wider where it overlaps the next
		a = t0 + k * 0.28
		b = a + 0.3
		p.seg(_fa(a), _fa(b), _fa_r(a, r0, r1, t0, t1) + 0.02, _fa_r(b, r0, r1, t0, t1), plate, sides=16, grad=grad)
		p.seg(_fa(a), _fa(a + 0.03), _fa_r(a, r0, r1, t0, t1) + 0.035, _fa_r(a, r0, r1, t0, t1) + 0.035, trim, sides=16)
	p.seg(_fa(t1 - 0.03), _fa(t1 + 0.01), r1 + 0.03, r1 + 0.03, trim, sides=16)            # wrist rim
	p.seg(_fa(t0 + 0.02, r0 + 0.01, -25), _fa(t1 - 0.02, r1 + 0.01, -25), 0.04, 0.035, trim, sides=6)   # the ridge
	for t in (-0.2, 0.18):                                                             # straps and buckles
		r = _fa_r(t, r0, r1, t0, t1) + 0.04
		p.seg(_fa(t - 0.04), _fa(t + 0.04), r, r, strap, sides=16)
		p.box((0.1, 0.05, 0.1), _fa(t, r + 0.02, 35), buckle, rot=(0, -45, 0))
	if glow_line:
		for t in (-0.3, 0.02, 0.3):
			r = _fa_r(t, r0, r1, t0, t1) + 0.025
			p.seg(_fa(t - 0.12, r, 20), _fa(t + 0.08, r, 20), 0.018, 0.018, glow_line, sides=4, glow=2.4)
	p.seg(_fa(t1 + 0.01), _fa(t1 + 0.02), 0.2, 0.2, STONE_DARK, sides=16)                    # the empty wrist
	return t0, t1, r0, r1


def cloth_sleeves():
	p = Prop("cloth_sleeves", 851)
	_sleeve(p, HIDE, BONE, grad=(0.0, 0.6))
	return p.build()


def leather_sleeves():
	p = Prop("leather_sleeves", 853)
	t0, t1, r0, r1 = _sleeve(p, WOOD, WOOD_GRAY, folds=2)
	for k in range(5):                                                                # laced down the seam
		t = -0.5 + k * 0.19
		r = _fa_r(t, r0, r1, t0, t1) + 0.015
		p.seg(_sl(t, r, -30), _sl(t + 0.09, r, 10), 0.014, 0.014, HIDE, sides=4)
		p.seg(_sl(t, r, 10), _sl(t + 0.09, r, -30), 0.014, 0.014, HIDE, sides=4)
	return p.build()


def netmakers_sleeves():
	p = Prop("netmakers_sleeves", 855)
	t0, t1, r0, r1 = _sleeve(p, BONE, WOOD, grad=(0.0, 0.7), folds=0)
	for sgn in (-1, 1):                                                               # knotted netting spiralled round it
		for k in range(8):
			for j in range(6):
				ta, tb = t0 + 0.08 + j * 0.16, t0 + 0.08 + (j + 1) * 0.16
				if tb > t1 - 0.12:
					break
				aa, ab = k * 45 + sgn * j * 40, k * 45 + sgn * (j + 1) * 40
				p.seg(_sl(ta, _fa_r(ta, r0, r1, t0, t1) + 0.015, aa), _sl(tb, _fa_r(tb, r0, r1, t0, t1) + 0.015, ab),
					  0.012, 0.012, WOOD_GRAY, sides=4)
	p.blob((0.14, 0.12, 0.2), _sl(-0.1, 0.36, 60), WOOD, segs=(8, 5))                        # a cork float tied on
	p.seg(_sl(-0.1, 0.27, 60), _sl(-0.1, 0.33, 60), 0.01, 0.01, WOOD_GRAY, sides=4)
	return p.build()


def vale_patrol_bracer():
	p = Prop("vale_patrol_bracer", 857)
	t0, t1, r0, r1 = -0.34, 0.34, 0.31, 0.27
	p.seg(_fa(t0), _fa(t1), r0, r1, WOOD, sides=16, grad=(0.2, 0.9))                        # a plain leather cuff
	for t in (t0, t1 - 0.04):
		p.seg(_fa(t), _fa(t + 0.04), _fa_r(t, r0, r1, t0, t1) + 0.02, _fa_r(t, r0, r1, t0, t1) + 0.02, HIDE, sides=16)
	for k in range(3):                                                                # laced shut down the side
		t = -0.24 + k * 0.18
		r = _fa_r(t, r0, r1, t0, t1) + 0.01
		p.seg(_fa(t, r, 50), _fa(t + 0.12, r, 80), 0.014, 0.014, HIDE, sides=4)
		p.seg(_fa(t, r, 80), _fa(t + 0.12, r, 50), 0.014, 0.014, HIDE, sides=4)
	c = Vector(_fa(0.0, 0.3, -10))                                                    # the patrol's badge: a gold disc, a green leaf
	p.seg(tuple(c), _fa(0.0, 0.36, -10), 0.14, 0.14, GOLD, sides=12, grad=(0.0, 0.6))
	p.blob((0.07, 0.07, 0.14), _fa(0.0, 0.37, -10), PINE, rot=(0, -45, 0), segs=(6, 4))
	p.seg(_fa(t1 + 0.0), _fa(t1 + 0.01), 0.21, 0.21, STONE_DARK, sides=16)                   # the empty wrist
	return p.build()


def tempered_vambraces():
	p = Prop("tempered_vambraces", 859)
	_vambrace(p, STONE_DARK, SEA_STONE, WOOD, IRON, grad=(0.2, 0.9))
	return p.build()


def steel_vambraces():
	p = Prop("steel_vambraces", 861)
	_vambrace(p, STONE_LIGHT, IRON, WOOD, GOLD, grad=(0.0, 0.45))
	return p.build()


def tidesteel_vambraces():
	p = Prop("tidesteel_vambraces", 863)
	_vambrace(p, AQUA, STONE_LIGHT, SEAFOAM, CLOTH_WHITE, grad=(0.1, 0.8))
	p.blob((0.1, 0.08, 0.1), _fa(-0.02, 0.33, -25), CLOTH_WHITE, segs=(8, 5), glow=0.5)       # a pearl on the ridge
	return p.build()


def emberforged_vambraces():
	p = Prop("emberforged_vambraces", 865)
	_vambrace(p, IRON, STONE_DARK, STONE_DARK, EMBER, grad=(0.0, 0.6), glow_line=EMBER)
	return p.build()


def _cape_outline(top_w, hem_w, sag, n=9, dags=0):
	"""A cape seen from behind: a straight collar at z = 1, a hem curving down to its middle,
	optionally cut into points (dags)."""
	pts = [(-top_w, 1.0), (top_w, 1.0)]
	for k in range(n + 1):
		u = 1 - 2 * k / n                                                           # right to left along the hem
		z = 0.05 - sag * (1 - u * u)
		if dags and k % 2 == 1:
			z -= 0.1
		pts.append((u * hem_w, z))
	return pts


def skyrend_cloak():
	p = Prop("skyrend_cloak", 871)
	_slab(p, _cape_outline(0.3, 0.62, 0.12), 0.04, 0.1, WOOD, grad=(0.2, 0.9))        # a tawny hide cape under the plumes
	for row, (z0, length, n, spread) in enumerate(((0.62, 0.72, 7, 0.5), (0.86, 0.6, 5, 0.34))):   # two fans of griffon plumes
		for k in range(n):
			u = -1 + 2 * k / (n - 1)
			base = (u * spread * 0.55, -0.02 - row * 0.05, z0)
			ang = math.radians(u * 26)
			tip = (base[0] + math.sin(ang) * length, base[1], z0 - math.cos(ang) * length)
			_vane(p, base, tip, 0.13 if row == 0 else 0.11, HIDE if (k + row) % 2 else AMBER,
				  bars=(0.35, 0.55) if row == 0 else None, tip_swatch=CLOTH_WHITE)
	for k in range(7):                                                              # a collar of white down
		x = -0.3 + k * 0.1
		p.blob((0.16, 0.1, 0.14), (x, -0.13, 0.97 + 0.02 * math.cos(x * 5)), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.5))
	p.blob((0.24, 0.1, 0.24), (0, -0.2, 0.95), SKY, segs=(10, 6), glow=1.2)          # the sky-blue clasp
	p.seg((0, -0.2, 0.95), (0, -0.26, 0.95), 0.07, 0.07, CLOTH_WHITE, sides=8)
	return p.build()


def _scale_outline(cx, cz, w, h, n=6):
	"""A drake scale hanging point down: straight top, rounded sides to a point."""
	pts = [(cx - w, cz), (cx + w, cz)]
	for k in range(1, n):
		a = math.radians(k * 90 / n)
		pts.append((cx + w * math.cos(a) * (1 - 0.3 * k / n), cz - h * math.sin(a)))
	pts.append((cx, cz - h * 1.1))
	for k in range(n - 1, 0, -1):
		a = math.radians(k * 90 / n)
		pts.append((cx - w * math.cos(a) * (1 - 0.3 * k / n), cz - h * math.sin(a)))
	return pts


def drakescale_cloak():
	p = Prop("drakescale_cloak", 873)
	outline = _cape_outline(0.32, 0.64, 0.1, n=8, dags=True)
	_slab(p, [(x * 1.1, z - 0.06 if z < 0.9 else z + 0.02) for x, z in outline], 0.1, 0.14, EMBER, grad=(0.0, 0.45))   # ember lining round the edge
	_slab(p, outline, 0.04, 0.1, IRON, grad=(0.0, 0.5))
	rows = 5
	for r in range(rows):                                                           # shingled scales, upper rows over lower
		z = 0.95 - r * 0.18
		half = 0.3 + 0.32 * (0.95 - z) / 0.95
		n = 3 + r
		for k in range(n):
			cx = -half + (k + 0.5) * 2 * half / n + (0.05 if r % 2 else 0.0)
			dark = (k + r) % 3 == 0
			_slab(p, _scale_outline(cx, z, half / n * 1.45, 0.25), -0.01 - (rows - r) * 0.015, 0.04, STONE_DARK if dark else CLOTH_RED,
				  grad=(0.2, 0.8) if dark else (0.5, 1.0))
	p.seg((-0.34, -0.1, 1.0), (0.34, -0.1, 1.0), 0.06, 0.06, STONE_DARK, sides=6)         # an iron collar band
	for sx in (-1, 1):                                                              # a bone fang clasp on an iron ring
		p.seg((sx * 0.2, -0.18, 0.99), (sx * 0.03, -0.2, 0.88), 0.06, 0.0, BONE, sides=6)
	p.seg((0, -0.18, 0.96), (0, -0.23, 0.96), 0.1, 0.1, STONE_LIGHT, sides=10)
	p.seg((0, -0.23, 0.96), (0, -0.24, 0.96), 0.055, 0.055, IRON, sides=10)
	return p.build()


# ---------------------------------------------------------------- Dewstep

DAWN = (7, 1)         # peach to rose: dawn light


def _tip_back(obj, deg):
	"""Leans a flat-laid icon back so its face turns up to the camera."""
	obj.data.transform(Matrix.Rotation(math.radians(deg), 4, "X"))
	return obj


def moth_wing():
	p = Prop("moth_wing", 901)
	fore = _rot2([(0, 0), (0.3, 0.14), (0.8, 0.26), (1.2, 0.26), (1.34, 0.12), (1.24, -0.12), (0.8, -0.24), (0.3, -0.14)], 25, (-0.6, 0.15))
	hind = _rot2([(0, 0), (0.3, 0.12), (0.62, 0.1), (0.82, -0.05), (0.74, -0.32), (0.4, -0.4), (0.12, -0.18)], -22, (-0.6, 0.1))
	_slab(p, hind, 0.05, 0.09, BONE, grad=(0.3, 0.9))                                        # a cream hindwing behind
	_slab(p, fore, -0.02, 0.02, BONE, grad=(0.0, 0.5))                                       # and the long forewing
	for outline, y in ((fore, -0.03), (hind, 0.04)):
		base = outline[0]
		for q in outline[2:6]:                                                             # fine brown veins
			p.seg((base[0], y, base[1]), (q[0] * 0.85 + base[0] * 0.15, y, q[1] * 0.85 + base[1] * 0.15), 0.012, 0.008, WOOD, sides=3)
		for a, b in zip(outline[2:6], outline[3:7]):                                       # a dusky border
			p.seg((a[0], y - 0.005, a[1]), (b[0], y - 0.005, b[1]), 0.03, 0.03, HIDE, sides=4)
	for (lx, lz), s, y, rot in (((0.86, 0.02), 1.0, -0.04, 25), ((0.5, -0.16), 0.65, 0.03, -22)):   # an eye spot on each wing
		c = _rot2([(lx, lz)], rot, (-0.6, 0.15 if rot > 0 else 0.1))[0]
		p.blob((0.36 * s, 0.02, 0.32 * s), (c[0], y, c[1]), STONE_DARK, segs=(12, 4))
		p.blob((0.26 * s, 0.02, 0.23 * s), (c[0], y - 0.01, c[1]), AMBER, segs=(12, 4), grad=(0.0, 0.4))
		p.blob((0.1 * s, 0.02, 0.09 * s), (c[0] + 0.02, y - 0.02, c[1] + 0.02), GOLD, segs=(8, 4), glow=2.0)
	p.blob((0.2, 0.14, 0.16), (-0.6, 0.02, 0.12), HIDE, segs=(8, 5), jitter=0.02)              # a tuft of fuzz where it tore free
	return p.build()


def rice_beetle_shell():
	p = Prop("rice_beetle_shell", 903)
	for sx in (-1, 1):                                                                    # two glossy wing cases, parted
		p.blob((0.46, 1.0, 0.34), (sx * 0.25, 0, 0.14), PINE, rot=(0, 0, sx * -7), segs=(14, 8), grad=(0.0, 0.7))
		for k in range(3):                                                                # rows of pale spots
			p.blob((0.1, 0.12, 0.04), (sx * (0.25 + (k % 2) * 0.06), -0.25 + k * 0.25, 0.3 - abs(k - 1) * 0.02), AMBER, segs=(6, 4), grad=(0.0, 0.3))
		p.seg((sx * 0.02, -0.48, 0.2), (sx * 0.05, 0.48, 0.2), 0.022, 0.022, GOLD, sides=4)   # gilt edges along the seam
	p.blob((0.34, 0.26, 0.2), (0, -0.56, 0.1), STONE_DARK, segs=(8, 5))                      # the neck shield
	for (x, y) in ((0.62, -0.3), (0.72, -0.05), (0.6, 0.2)):                               # and a few grains of rice
		p.blob((0.1, 0.2, 0.08), (x, y, 0.04), CLOTH_WHITE, rot=(0, 0, x * 60), segs=(8, 4), grad=(0.0, 0.3))
	return _tip_back(p.build(), 40)


def stolen_trinket():
	p = Prop("stolen_trinket", 905)
	p.seg((0.08, 0, -0.08), (0.08, 0, 0.02), 0.62, 0.58, WOOD, sides=14)                   # a little carved plinth
	p.blob((0.8, 0.52, 0.58), (0, 0, 0.56), GOLD, segs=(12, 8), grad=(0.0, 0.8))             # a brass elephant
	for x in (-0.24, 0.24):
		for y in (-0.15, 0.15):
			p.seg((x, y, 0.45), (x, y, 0.03), 0.1, 0.11, GOLD, sides=8, grad=(0.3, 0.9))
	p.box((0.4, 0.56, 0.06), (-0.02, 0, 0.84), CLOTH_RED, rot=(0, 0, 0))                   # a red saddle cloth
	p.blob((0.4, 0.4, 0.42), (0.4, 0, 0.76), GOLD, segs=(10, 8), grad=(0.0, 0.8))             # its head
	for sy in (-1, 1):
		p.blob((0.08, 0.36, 0.42), (0.34, sy * 0.24, 0.74), GOLD, segs=(8, 6), grad=(0.2, 0.9))   # ears
		p.seg((0.52, sy * 0.1, 0.62), (0.68, sy * 0.13, 0.52), 0.035, 0.0, BONE, sides=5)          # tusks
	trunk = [(0.58, 0, 0.7), (0.7, 0, 0.5), (0.7, 0, 0.3), (0.8, 0, 0.18)]
	for i, (a, b) in enumerate(zip(trunk, trunk[1:])):
		p.seg(a, b, 0.09 - i * 0.02, 0.07 - i * 0.02, GOLD, sides=7)
	p.blob((0.1, 0.06, 0.1), (0.5, -0.02, 0.92), CLOTH_RED, segs=(6, 4), glow=1.8)             # a ruby on its brow
	p.seg((-0.4, 0, 0.6), (-0.46, 0, 0.3), 0.03, 0.02, GOLD, sides=4)                          # tail
	return p.build()


def jackal_pelt():
	p = Prop("jackal_pelt", 907)
	p.blob((1.1, 0.72, 0.12), (0, 0, 0.06), AMBER, segs=(12, 6), grad=(0.45, 0.95), jitter=0.05)   # a golden-tan hide
	for x in (-1, 1):
		for y in (-1, 1):
			p.blob((0.3, 0.2, 0.1), (x * 0.4, y * 0.32, 0.05), AMBER, segs=(6, 4), grad=(0.45, 0.95))
	p.blob((0.85, 0.36, 0.08), (0.08, 0, 0.12), WOOD_GRAY, segs=(10, 5), grad=(0.3, 0.9), jitter=0.02)         # a dark saddle down its back
	p.blob((0.34, 0.26, 0.12), (-0.58, 0, 0.1), AMBER, segs=(8, 5), grad=(0.45, 0.95))                           # the head end
	p.seg((-0.7, 0, 0.1), (-0.95, 0, 0.08), 0.1, 0.04, AMBER, sides=6, grad=(0.45, 0.95))                         # a long muzzle
	for sy in (-1, 1):                                                                    # tall ears
		p.seg((-0.55, sy * 0.1, 0.14), (-0.5, sy * 0.2, 0.46), 0.08, 0.0, AMBER, sides=4, grad=(0.45, 0.95))
		p.seg((-0.56, sy * 0.1 - 0.02, 0.16), (-0.52, sy * 0.19 - 0.02, 0.36), 0.04, 0.0, BONE, sides=4)
	pts = [(0.5, 0, 0.08), (0.75, 0.08, 0.1), (0.95, 0.2, 0.12)]                           # a bushy tail, dark-tipped
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.1, 0.12, AMBER, sides=6, grad=(0.45, 0.95))
	p.blob((0.2, 0.18, 0.18), (1.02, 0.25, 0.12), STONE_DARK, segs=(6, 4))
	return _tip_back(p.build(), 50)


def cobra_fang():
	p = Prop("cobra_fang", 909)
	pts = [(0, 0, 1.0), (0.1, 0, 0.7), (0.12, 0, 0.4), (0.02, 0, 0.12)]                   # a slender curved fang, tip down
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.14 - i * 0.045, 0.095 - i * 0.045 if i < 2 else 0.0, BONE, sides=7, grad=(0.0, 0.6))
	p.seg((0.05, -0.1, 0.85), (0.1, -0.06, 0.45), 0.02, 0.015, LEAF, sides=4, glow=2.0)       # its venom groove
	p.seg((0, 0, 1.12), (0, 0, 0.98), 0.17, 0.15, WOOD, sides=8)                              # the dark root
	p.blob((0.12, 0.12, 0.16), (0.0, 0, 0.0), LEAF, segs=(8, 6), glow=2.2)                    # a drop of venom at the tip
	p.seg((0.0, 0, 0.02), (0.02, 0, 0.12), 0.06, 0.0, LEAF, sides=6, glow=2.2)
	return p.build()


def tiger_pelt():
	p = Prop("tiger_pelt", 911)
	p.blob((1.1, 0.8, 0.16), (0, 0, 0.08), ORANGE, segs=(12, 6), grad=(0.3, 1.0), jitter=0.05)   # a bright orange pelt
	for x in (-1, 1):
		for y in (-1, 1):
			p.blob((0.32, 0.24, 0.12), (x * 0.4, y * 0.34, 0.06), ORANGE, segs=(6, 4), grad=(0.3, 1.0))
			p.blob((0.12, 0.12, 0.08), (x * 0.44, y * 0.46, 0.06), CLOTH_WHITE, segs=(6, 4))   # pale paws
	p.blob((0.38, 0.32, 0.2), (-0.6, 0, 0.14), ORANGE, segs=(8, 5), grad=(0.3, 1.0))           # the head end
	p.blob((0.18, 0.24, 0.1), (-0.74, 0, 0.14), CLOTH_WHITE, segs=(8, 5))                      # white muzzle
	for sy in (-1, 1):
		p.seg((-0.6, sy * 0.13, 0.2), (-0.62, sy * 0.17, 0.34), 0.08, 0.02, STONE_DARK, sides=5)
	for k in range(7):                                                                    # black stripes across the back
		x = -0.36 + k * 0.13
		half = 0.34 if k % 2 else 0.24
		pts = [(x - 0.03, -half, 0.12), (x + 0.03, -half * 0.3, 0.17), (x - 0.02, half * 0.3, 0.17), (x + 0.03, half, 0.12)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.035 if i == 1 else 0.028, 0.035 if i == 1 else 0.028, IRON, sides=4)
	pts = [(0.5, 0, 0.1), (0.8, 0.12, 0.12), (0.98, 0.32, 0.16), (1.0, 0.55, 0.2)]         # a striped tail
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.09, 0.08, ORANGE, sides=6, grad=(0.3, 1.0))
	for k in range(3):
		c = pts[k + 1]
		p.seg((c[0] - 0.02, c[1] - 0.02, c[2]), (c[0] + 0.02, c[1] + 0.02, c[2]), 0.1, 0.1, IRON, sides=6)
	return _tip_back(p.build(), 40)


def dustpaw_beads():
	p = Prop("dustpaw_beads", 913)
	pts = []
	for k in range(15):                                                                   # a loose string of clay beads
		t = k / 14
		pts.append((-0.9 + t * 1.8, math.sin(t * math.pi * 1.6) * 0.34, 0.12))
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.022, 0.022, WOOD_GRAY, sides=4)
	for k, c in enumerate(pts[1:-1]):
		if k % 4 == 3:
			p.seg((c[0] - 0.045, c[1], c[2]), (c[0] + 0.045, c[1], c[2]), 0.17, 0.17, BONE, sides=10)   # bone disks between
		else:
			p.rock((0.26, 0.26, 0.24), c, AMBER if k % 2 else CLOTH_RED, grad=(0.3, 0.9), jitter=0.03)
	for end, d in ((pts[0], -1), (pts[-1], 1)):                                           # knotted ends
		p.blob((0.1, 0.1, 0.1), end, WOOD_GRAY, segs=(6, 4))
		p.seg(end, (end[0] + d * 0.12, end[1] - 0.12, 0.08), 0.02, 0.01, WOOD_GRAY, sides=4)
	p.seg((0.95, -0.05, 0.1), (1.05, -0.3, 0.1), 0.05, 0.0, BONE, sides=5)                   # a jackal's tooth tied on
	return _tip_back(p.build(), 40)


def wisp_light():
	p = Prop("wisp_light", 915)
	p.blob((0.46, 0.46, 0.46), (0.1, 0, 0.72), CLOTH_WHITE, segs=(14, 10), glow=3.0)          # a pale bead of light
	for k in range(8):                                                                    # a faint shell of glow round it
		a = k * math.tau / 8
		p.blob((0.14, 0.1, 0.14), (0.1 + math.cos(a) * 0.36, -0.05, 0.72 + math.sin(a) * 0.36), AQUA, segs=(6, 4), grad=(0.0, 0.3), glow=1.6)
	for k in range(9):                                                                    # its tail curling away below
		t = k / 8
		a = t * 4.2
		x, z = 0.1 - t * 0.6 + math.cos(a) * 0.18 * (1 - t), 0.4 - t * 0.5 + math.sin(a) * 0.15
		s = 0.24 * (1 - t) + 0.05
		p.blob((s, s, s), (x, 0.05, z), AQUA, segs=(8, 5), grad=(0.0, 0.3), glow=2.0 - t)
	for (x, z) in ((0.55, 1.0), (-0.3, 1.02), (0.6, 0.4)):                                # motes
		p.blob((0.06, 0.06, 0.06), (x, -0.1, z), GOLD, segs=(5, 3), glow=2.0)
	return p.build()


def funeral_coin():
	p = Prop("funeral_coin", 917)
	R, h, cx, cz = 0.6, 0.15, 0.0, 0.6                                                    # an old bronze coin with a square hole
	for k in range(4):
		a = math.radians(k * 90)
		arc = [(cx + math.cos(a + math.radians(d)) * R, cz + math.sin(a + math.radians(d)) * R) for d in range(-45, 46, 15)]
		corner = lambda d: (cx + math.cos(a + math.radians(d)) * h * math.sqrt(2), cz + math.sin(a + math.radians(d)) * h * math.sqrt(2))
		_slab(p, arc + [corner(45), corner(-45)], -0.04, 0.04, CLAY, grad=(0.2, 0.9))
	_loop(p, (cx, -0.04, cz), R - 0.02, False, 0.035, CLAY, n=24)                           # its raised rim
	sq = [(cx - h, cz - h), (cx + h, cz - h), (cx + h, cz + h), (cx - h, cz + h)]
	for a, b in zip(sq, sq[1:] + sq[:1]):                                                 # and the rim round the hole
		p.seg((a[0], -0.05, a[1]), (b[0], -0.05, b[1]), 0.03, 0.03, CLAY, sides=4)
	for k in range(4):                                                                    # four worn characters
		a = math.radians(k * 90 + 90)
		gx, gz = cx + math.cos(a) * 0.38, cz + math.sin(a) * 0.38
		p.seg((gx - 0.08, -0.05, gz), (gx + 0.08, -0.05, gz), 0.022, 0.022, WOOD, sides=4)
		p.seg((gx, -0.05, gz - 0.08), (gx + 0.02, -0.05, gz + 0.08), 0.022, 0.022, WOOD, sides=4)
	for (x, z, s) in ((0.3, 0.3, 0.12), (-0.35, 0.8, 0.09), (0.1, 1.0, 0.07)):            # green with age
		p.blob((s, 0.02, s * 0.8), (x, -0.055, z), SEAFOAM, segs=(8, 4), grad=(0.2, 0.6))
	p.seg((-0.12, 0.3, 0.72), (0.12, -0.3, 0.5), 0.03, 0.03, CLOTH_RED, sides=5)            # a red cord through it
	p.seg((0.12, -0.3, 0.5), (0.45, -0.3, -0.05), 0.03, 0.02, CLOTH_RED, sides=5)
	return p.build()


def pilfers_bangle():
	p = Prop("pilfers_bangle", 919)
	u, v = Vector((1, 0, 0)), Vector((0, 0.55, 0.84))
	_oval(p, (0, 0, 0.45), u, v, 0.52, 0.52, 0.09, GOLD, n=24)                                # a heavy gold bangle, tilted
	for off in (-0.08, 0.08):                                                             # engraved edges
		_oval(p, (0, -0.84 * off, 0.45 + 0.55 * off), u, v, 0.54, 0.54, 0.02, EMBER, n=24)
	for k in range(5):                                                                    # set with stones
		a = math.radians(-90 + (k - 2) * 28)
		c = Vector((0, 0, 0.45)) + u * math.cos(a) * 0.55 + v * math.sin(a) * 0.55
		p.blob((0.12, 0.1, 0.12), tuple(c + Vector((0, -0.06, 0))), CLOTH_RED if k % 2 == 0 else SEAFOAM, segs=(6, 4), glow=1.4)
	for k in range(3):                                                                    # little bells hanging off it
		a = math.radians(-60 + k * 60)
		c = Vector((0, 0, 0.45)) + u * math.cos(a + math.pi) * 0.55 + v * math.sin(a + math.pi) * 0.55
		p.seg(tuple(c), tuple(c + Vector((0, -0.04, -0.14))), 0.015, 0.015, GOLD, sides=4)
		p.blob((0.1, 0.1, 0.1), tuple(c + Vector((0, -0.05, -0.18))), GOLD, segs=(6, 4))
	return p.build()


def amberstripes_fang():
	p = Prop("amberstripes_fang", 921)
	pts = [(0, 0, 0.25), (0.12, 0, 0.6), (0.18, 0, 0.9), (0.1, 0, 1.2)]                   # a great tiger's fang
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.2 - i * 0.06, 0.14 - i * 0.06 if i < 2 else 0.0, BONE, sides=8, grad=(0.1, 0.9))
	p.seg((-0.01, 0, -0.1), (0.01, 0, 0.3), 0.23, 0.21, ORANGE, sides=10, grad=(0.3, 0.9), jitter=0.02)   # bound in its own striped fur
	for z in (-0.02, 0.1, 0.22):
		p.seg((0, 0, z), (0, 0, z + 0.04), 0.235, 0.225, IRON, sides=10)
	p.seg((0, 0, 0.3), (0, 0, 0.34), 0.22, 0.2, GOLD, sides=10)                                # a gold band
	p.blob((0.1, 0.06, 0.1), (0.0, -0.21, 0.32), EMBER, segs=(6, 4), glow=1.4)                # an amber bead
	return p.build()


def rattlejaws_necklace():
	p = Prop("rattlejaws_necklace", 923)
	_cord(p, 0.55, 0.75, HIDE)
	for k in range(7):                                                                    # teeth, bones and red beads
		a = math.radians(-90 + (k - 3) * 24)
		x, y, z = math.cos(a) * 0.55, math.sin(a) * 0.55 * 0.6, 0.75 + math.sin(a) * 0.2
		if k == 3:
			continue
		if k % 2:
			p.seg((x, y, z), (x * 1.05, y * 1.05, z - 0.32), 0.06, 0.0, BONE, sides=5)
		else:
			p.seg((x, y, z - 0.02), (x, y, z - 0.14), 0.05, 0.05, BONE, sides=6)
			p.blob((0.1, 0.1, 0.1), (x, y, z - 0.18), CLOTH_RED, segs=(6, 4))
	p.blob((0.34, 0.3, 0.3), (0, -0.36, 0.42), BONE, segs=(10, 7), grad=(0.0, 0.7))          # a small jackal skull in the middle
	p.seg((0, -0.44, 0.38), (0, -0.66, 0.3), 0.1, 0.06, BONE, sides=7)                        # its snout
	for sx in (-1, 1):
		p.blob((0.09, 0.06, 0.08), (sx * 0.08, -0.5, 0.48), STONE_DARK, segs=(6, 4))
		p.seg((sx * 0.04, -0.62, 0.28), (sx * 0.04, -0.64, 0.2), 0.02, 0.0, BONE, sides=4)
	for sx in (-1, 1):                                                                    # dry seed rattles
		p.blob((0.14, 0.12, 0.18), (sx * 0.3, -0.3, 0.38), AMBER, segs=(8, 5), grad=(0.4, 1.0))
	return p.build()


def widows_lantern():
	p = Prop("widows_lantern", 925)
	cz, rz, rr = 0.62, 0.46, 0.42
	p.blob((rr * 2, rr * 2, rz * 2), (0, 0, cz), BONE, segs=(16, 12), grad=(0.0, 0.5), glow=1.4)   # a glowing paper lantern
	for k in range(1, 6):                                                                 # its bamboo ribs
		z = cz - rz + k * rz * 2 / 6
		r = rr * math.sqrt(max(1 - ((z - cz) / rz) ** 2, 0)) + 0.01
		_loop(p, (0, 0, z), r, True, 0.014, WOOD, n=20)
	p.seg((0, 0, cz + rz - 0.06), (0, 0, cz + rz + 0.06), 0.2, 0.18, STONE_DARK, sides=12)    # black lacquered caps
	p.seg((0, 0, cz - rz + 0.06), (0, 0, cz - rz - 0.06), 0.2, 0.18, STONE_DARK, sides=12)
	arc = [(math.cos(a) * 0.16, 0, cz + rz + 0.06 + math.sin(a) * 0.2) for a in [k * math.pi / 8 for k in range(9)]]
	for a, b in zip(arc, arc[1:]):                                                        # a wire handle
		p.seg(a, b, 0.02, 0.02, STONE_DARK, sides=4)
	for k in range(3):                                                                    # a painted mourning character
		p.seg((-0.12 + k * 0.1, -0.43, 0.78 - k * 0.04), (-0.05 + k * 0.1, -0.44, 0.52 + k * 0.03), 0.022, 0.018, CLOTH_RED, sides=4)
	z0 = cz - rz - 0.06
	p.seg((0, 0, z0), (0, 0, z0 - 0.1), 0.03, 0.03, CLOTH_RED, sides=5)                     # a red tassel
	p.blob((0.12, 0.12, 0.12), (0, 0, z0 - 0.12), CLOTH_RED, segs=(8, 5))
	for k in range(7):
		a = k * math.tau / 7
		p.seg((math.cos(a) * 0.03, math.sin(a) * 0.03, z0 - 0.16), (math.cos(a) * 0.07, math.sin(a) * 0.07, z0 - 0.5), 0.022, 0.018, CLOTH_RED, sides=4)
	return p.build()


def _sandal(p, ox, oz, mirror):
	sole = [(0, 1.0), (0.14, 0.97), (0.24, 0.86), (0.27, 0.7), (0.24, 0.5), (0.2, 0.3), (0.2, 0.12), (0.14, 0.02), (0, 0),
			(-0.14, 0.02), (-0.2, 0.12), (-0.2, 0.3), (-0.22, 0.5), (-0.25, 0.7), (-0.22, 0.86), (-0.12, 0.97)]
	sole = [(ox + x * mirror, oz + z) for x, z in sole]
	_slab(p, sole, 0.0, 0.08, AMBER, grad=(0.0, 0.5))                                      # a woven straw sole
	for k in range(8):                                                                    # its weave
		z = 0.08 + k * 0.115
		w = 0.2 if z < 0.5 else 0.24 - abs(z - 0.72) * 0.4
		p.seg((ox - w, -0.01, oz + z), (ox + w, -0.01, oz + z + 0.02), 0.018, 0.018, HIDE, sides=4)
	p.seg((ox, -0.01, oz + 0.06), (ox, -0.01, oz + 0.92), 0.016, 0.016, WOOD, sides=4)
	toe = (ox, -0.02, oz + 0.8)                                                           # tea-green cord straps
	for sx in (-1, 1):
		pts = [toe, (ox + sx * 0.12, -0.18, oz + 0.62), (ox + sx * 0.23, -0.03, oz + 0.44)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.03, 0.03, LEAF, sides=5, grad=(0.3, 0.8))
		pts = [(ox + sx * 0.2, -0.03, oz + 0.34), (ox + sx * 0.18, -0.2, oz + 0.2), (ox, -0.24, oz + 0.12)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.03, 0.03, LEAF, sides=5, grad=(0.3, 0.8))
	p.blob((0.07, 0.07, 0.07), toe, LEAF, segs=(6, 4))


def teagarden_sandals():
	p = Prop("teagarden_sandals", 927)
	_sandal(p, -0.3, 0.0, 1)
	_sandal(p, 0.32, 0.12, -1)
	return _tip_back(p.build(), -45)


def dawnlight_ring():
	p = Prop("dawnlight_ring", 929)
	_ring(p, GOLD)
	p.seg((0, 0.06, 0.86), (0, -0.1, 0.86), 0.2, 0.2, GOLD, sides=10)                        # a setting
	p.blob((0.26, 0.14, 0.26), (0, -0.14, 0.88), DAWN, segs=(10, 6), grad=(0.0, 0.5), glow=2.0)   # a dawn-rose stone
	for k in range(10):                                                                   # rays of morning light
		a = k * math.tau / 10
		ln = 0.34 if k % 2 else 0.28
		p.seg((math.cos(a) * 0.17, -0.16, 0.88 + math.sin(a) * 0.17), (math.cos(a) * ln, -0.16, 0.88 + math.sin(a) * ln), 0.03, 0.0, GOLD,
			  sides=4, glow=1.2)
	return p.build()


def jackalhide_leggings():
	p = Prop("jackalhide_leggings", 931)
	_trousers(p, HIDE, WOOD)
	for x in (-1, 1):
		p.seg((x * 0.3, -0.15, 0.7), (x * 0.37, -0.15, 0.08), 0.03, 0.03, WOOD_GRAY, sides=5)   # dark jackal stripes down the legs
		p.seg((x * 0.24, 0, 0.08), (x * 0.245, 0, -0.04), 0.25, 0.26, BONE, sides=10, jitter=0.025)   # pale fur cuffs
	p.box((0.1, 0.06, 0.08), (0, -0.15, 1.0), GOLD)                                         # buckle
	pts = [(0.36, -0.16, 0.98), (0.46, -0.2, 0.75), (0.5, -0.22, 0.5)]                      # a jackal's tail hung at the hip
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.07, 0.09, HIDE, sides=6, grad=(0.0, 0.5))
	p.blob((0.16, 0.16, 0.2), (0.51, -0.22, 0.42), STONE_DARK, segs=(6, 5))
	return p.build()


def cobrafang_dagger():
	p = Prop("cobrafang_dagger", 933)
	org, rot = (-0.55, -0.35), 48
	up, lo = [], []
	for k in range(11):                                                                   # a wavy kris blade
		s = 0.34 + k * 0.1
		c = math.sin(k * 1.1) * 0.05
		hw = 0.15 * (1 - k / 11) + 0.035
		up.append((s, c + hw))
		lo.append((s, c - hw))
	outline = up + [(1.48, 0.0)] + lo[::-1]
	_slab(p, _rot2(outline, rot, org), -0.03, 0.03, STONE_LIGHT, grad=(0.0, 0.35))
	mid = _rot2([(0.34 + k * 0.1, math.sin(k * 1.1) * 0.05) for k in range(11)], rot, org)
	for a, b in zip(mid, mid[1:]):                                                        # green venom down its spine
		p.seg((a[0], -0.04, a[1]), (b[0], -0.04, b[1]), 0.014, 0.014, LEAF, sides=4, glow=1.4)
	hood = _rot2([(0.34, 0.12), (0.26, 0.3), (0.2, 0.34), (0.12, 0.26), (0.14, -0.12), (0.2, -0.2), (0.3, -0.18), (0.34, -0.12)], rot, org)
	_slab(p, hood, -0.05, 0.05, GOLD, grad=(0.1, 0.8))                                      # the guard: a cobra's spread hood
	for (s, w) in ((0.24, 0.16), (0.24, -0.06)):                                          # its spectacle marks
		c = _rot2([(s, w)], rot, org)[0]
		p.blob((0.08, 0.03, 0.08), (c[0], -0.06, c[1]), STONE_DARK, segs=(6, 4))
	head = _rot2([(0.28, 0.36)], rot, org)[0]
	p.blob((0.16, 0.12, 0.12), (head[0], -0.02, head[1]), GOLD, segs=(8, 5))
	p.blob((0.04, 0.03, 0.04), (head[0], -0.09, head[1] + 0.02), CLOTH_RED, segs=(5, 3), glow=2.0)
	h = _rot2([(0.14, 0.0), (-0.24, 0.0), (-0.3, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.06, 0.065, WOOD, sides=6)         # a dark wood grip
	for t in (0.25, 0.5, 0.75):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, 0, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.02, 0, q[2] - 0.02), (q[0] + 0.02, 0, q[2] + 0.02), 0.07, 0.07, GOLD, sides=6)
	p.blob((0.14, 0.13, 0.14), (h[2][0], 0, h[2][1]), GOLD, segs=(8, 5))
	tip = _rot2([(1.46, -0.02)], rot, org)[0]
	p.blob((0.08, 0.06, 0.1), (tip[0] + 0.02, -0.04, tip[1] - 0.1), LEAF, segs=(6, 4), glow=2.2)   # a drop at the point
	return p.build()


def tigerstripe_mantle():
	p = Prop("tigerstripe_mantle", 935)
	outline = [(-0.26, 1.0), (0.26, 1.0), (0.5, 0.86), (0.66, 0.6), (0.7, 0.3), (0.58, 0.12), (0.3, 0.02), (0.0, 0.0), (-0.3, 0.02),
			   (-0.58, 0.12), (-0.7, 0.3), (-0.66, 0.6), (-0.5, 0.86)]                        # a shoulder mantle of tiger hide
	_slab(p, outline, -0.02, 0.06, ORANGE, grad=(0.3, 1.0))
	for k in range(7):                                                                    # black stripes, from the hem up and the sides in
		x = -0.54 + k * 0.18
		zb = 0.04 + 0.12 * abs(x) ** 1.5 + 0.02
		zt = zb + (0.42 if k % 2 else 0.3)
		pts = [(x, zb), (x + 0.05, (zb + zt) / 2), (x - 0.01, zt)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg((a[0], -0.03, a[1]), (b[0], -0.03, b[1]), 0.05 if i == 0 else 0.035, 0.035 if i == 0 else 0.0, IRON, sides=4)
	for sx in (-1, 1):
		for k in range(2):
			z = 0.52 + k * 0.16
			p.seg((sx * 0.68, -0.03, z), (sx * 0.4, -0.03, z + 0.06), 0.04, 0.0, IRON, sides=4)
	for k in range(9):                                                                    # a thick pale fur collar
		t = k / 8
		x = -0.34 + t * 0.68
		p.blob((0.2, 0.18, 0.18), (x, -0.06, 0.97 - math.sin(t * math.pi) * 0.1), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.5), jitter=0.02)
	p.blob((0.18, 0.1, 0.18), (0, -0.14, 0.82), GOLD, segs=(8, 5), glow=0.4)                 # a gold clasp
	for dx in (-0.07, 0.0, 0.07):                                                         # hung with claws
		p.seg((dx, -0.16, 0.76), (dx * 1.4, -0.18, 0.5), 0.04, 0.0, BONE, sides=5)
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(-15), 4, "X"))
	return obj


def wardens_buckler():
	p = Prop("wardens_buckler", 937)
	c = (0, 0.6)
	p.seg((0, 0.06, c[1]), (0, -0.05, c[1]), 0.55, 0.55, WOOD, sides=24, grad=(0.1, 0.8))      # a small round buckler of wood
	_loop(p, (0, -0.05, c[1]), 0.54, False, 0.05, IRON, n=24)                               # an iron rim
	_loop(p, (0, -0.06, c[1]), 0.34, False, 0.03, DAWN, n=20)                               # a painted dawn ring
	for k in range(8):                                                                    # rivets
		a = k * math.tau / 8 + 0.2
		p.blob((0.06, 0.05, 0.06), (math.cos(a) * 0.45, -0.07, c[1] + math.sin(a) * 0.45), STONE_LIGHT, segs=(6, 4))
	p.blob((0.34, 0.24, 0.34), (0, -0.08, c[1]), GOLD, segs=(12, 8), grad=(0.0, 0.7), glow=0.5)   # a sun boss
	for k in range(12):
		a = k * math.tau / 12
		ln = 0.3 if k % 2 else 0.25
		p.seg((math.cos(a) * 0.17, -0.07, c[1] + math.sin(a) * 0.17), (math.cos(a) * ln, -0.07, c[1] + math.sin(a) * ln), 0.04, 0.0, GOLD,
			  sides=4, glow=0.5)
	return p.build()


def dawnsteel_shortsword():
	p = Prop("dawnsteel_shortsword", 939)
	org, rot = (-0.5, -0.3), 48
	outline = [(0.32, 0.09), (0.6, 0.1), (0.9, 0.11), (1.08, 0.09), (1.24, 0.04), (1.32, 0.0), (1.24, -0.04), (1.08, -0.09), (0.9, -0.11),
			   (0.6, -0.1), (0.32, -0.09)]
	_slab(p, _rot2(outline, rot, org), -0.03, 0.03, STONE_LIGHT, grad=(0.0, 0.3))           # a bright steel blade
	f = _rot2([(0.36, 0.0), (1.08, 0.0)], rot, org)
	p.seg((f[0][0], -0.045, f[0][1]), (f[1][0], -0.045, f[1][1]), 0.022, 0.012, CLOTH_WHITE, sides=4, glow=0.8)   # a shining fuller
	g = _rot2([(0.3, -0.3), (0.3, 0.3)], rot, org)
	p.seg((g[0][0], 0, g[0][1]), (g[1][0], 0, g[1][1]), 0.05, 0.05, GOLD, sides=6)            # a gold crossguard
	for end in g:
		p.blob((0.1, 0.1, 0.1), (end[0], 0, end[1]), GOLD, segs=(6, 4))
	s = _rot2([(0.3, 0.0)], rot, org)[0]
	p.seg((s[0], 0.02, s[1]), (s[0], -0.08, s[1]), 0.15, 0.15, GOLD, sides=14, glow=0.8)       # a gold sun at its heart
	for k in range(10):
		a = k * math.tau / 10
		p.seg((s[0] + math.cos(a) * 0.14, -0.06, s[1] + math.sin(a) * 0.14), (s[0] + math.cos(a) * 0.24, -0.06, s[1] + math.sin(a) * 0.24),
			  0.03, 0.0, GOLD, sides=4, glow=0.8)
	p.blob((0.1, 0.05, 0.1), (s[0], -0.1, s[1]), DAWN, segs=(6, 4), glow=1.6)
	h = _rot2([(0.24, 0.0), (-0.08, 0.0), (-0.14, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.055, CLOTH_RED, sides=6)     # a red-wrapped grip
	p.blob((0.14, 0.14, 0.14), (h[2][0], 0, h[2][1]), GOLD, segs=(8, 6))
	return p.build()


def ravis_prayer_beads():
	p = Prop("ravis_prayer_beads", 941)
	for k in range(20):                                                                   # a loop of dark seed beads
		a = k * math.tau / 20
		x, y, z = math.cos(a) * 0.55, math.sin(a) * 0.55 * 0.6, 0.62 + math.sin(a) * 0.2
		if k == 15:
			p.blob((0.22, 0.22, 0.22), (x, y, z), SEAFOAM, segs=(10, 6), grad=(0.0, 0.6), glow=0.4)   # a jade guru bead
		elif k % 5 == 0:
			p.blob((0.09, 0.09, 0.09), (x, y, z), GOLD, segs=(6, 4))
		else:
			p.rock((0.15, 0.15, 0.15), (x, y, z), WOOD, grad=(0.4, 1.0), jitter=0.04)
	p.seg((0, -0.33, 0.3), (0, -0.33, 0.14), 0.03, 0.03, ORANGE, sides=4)                   # a saffron tassel
	p.blob((0.1, 0.1, 0.1), (0, -0.33, 0.12), ORANGE, segs=(6, 4))
	for k in range(6):
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.03, -0.33 + math.sin(a) * 0.03, 0.08), (math.cos(a) * 0.08, -0.33 + math.sin(a) * 0.06, -0.26), 0.022, 0.018,
			  ORANGE, sides=4)
	return p.build()


def lampwardens_charm():
	p = Prop("lampwardens_charm", 943)
	_cord(p, 0.45, 0.86, GOLD)
	cx, cy = 0.0, -0.3                                                                    # a little brass lantern
	p.seg((cx, cy, 0.02), (cx, cy, 0.08), 0.17, 0.17, GOLD, sides=6)
	p.seg((cx, cy, 0.46), (cx, cy, 0.52), 0.18, 0.18, GOLD, sides=6)
	p.seg((cx, cy, 0.52), (cx, cy, 0.66), 0.16, 0.0, GOLD, sides=6)                        # its roof
	_loop(p, (cx, cy, 0.7), 0.05, False, 0.018, GOLD, n=8)
	for k in range(6):                                                                    # posts
		a = k * math.tau / 6
		p.seg((cx + math.cos(a) * 0.15, cy + math.sin(a) * 0.15, 0.08), (cx + math.cos(a) * 0.15, cy + math.sin(a) * 0.15, 0.46), 0.02, 0.02, GOLD, sides=4)
	p.blob((0.2, 0.2, 0.3), (cx, cy, 0.26), FLAME, segs=(8, 6), grad=(0.0, 0.5), glow=2.6)   # the flame it keeps
	p.seg((cx, cy, 0.3), (cx, cy, 0.44), 0.07, 0.0, FLAME, sides=6, glow=2.6)
	for k in range(6):                                                                    # its light on the chain
		a = k * math.tau / 6 + 0.5
		p.blob((0.05, 0.05, 0.05), (cx + math.cos(a) * 0.3, cy - 0.12, 0.26 + math.sin(a) * 0.3), GOLD, segs=(5, 3), glow=2.0)
	return p.build()


def rattlejaws_cleaver():
	p = Prop("rattlejaws_cleaver", 945)
	org, rot = (-0.45, -0.35), 45
	blade = [(0.2, -0.12), (0.95, -0.1), (1.04, 0.02), (1.02, 0.32), (0.94, 0.46), (0.82, 0.44), (0.74, 0.52), (0.62, 0.46),
			 (0.5, 0.5), (0.4, 0.42), (0.3, 0.46), (0.2, 0.34)]                             # a broad, chipped slab of iron
	_slab(p, _rot2(blade, rot, org), -0.04, 0.04, STONE_DARK, grad=(0.0, 0.7))
	edge = _rot2([(1.02, 0.32), (0.94, 0.46), (0.82, 0.44), (0.74, 0.52), (0.62, 0.46), (0.5, 0.5), (0.4, 0.42), (0.3, 0.46)], rot, org)
	for a, b in zip(edge, edge[1:]):                                                      # a ragged honed edge
		p.seg((a[0], -0.045, a[1]), (b[0], -0.045, b[1]), 0.03, 0.03, STONE_LIGHT, sides=4)
	for (s, w, r) in ((0.7, 0.15, 0.1), (0.4, 0.05, 0.08), (0.9, 0.0, 0.07)):              # rust
		c = _rot2([(s, w)], rot, org)[0]
		p.blob((r, 0.02, r * 0.8), (c[0], -0.045, c[1]), CLAY, segs=(8, 4), grad=(0.3, 0.9))
	c = _rot2([(0.88, -0.0)], rot, org)[0]
	p.seg((c[0], 0.06, c[1]), (c[0], -0.06, c[1]), 0.06, 0.06, IRON, sides=10)               # a hanging hole
	h = _rot2([(0.22, 0.0), (-0.4, 0.0), (-0.48, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.075, 0.085, WOOD, sides=6, jitter=0.01)   # a rough wooden haft
	for t in (0.15, 0.4, 0.65, 0.9):                                                      # bound with hide
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.025, 0, q[1] - 0.025), (q[0] + 0.025, 0, q[1] + 0.025), 0.09, 0.09, HIDE, sides=6)
	p.blob((0.16, 0.14, 0.16), (h[2][0], 0, h[2][1]), BONE, segs=(8, 5))                      # a knuckle-bone pommel
	for k in range(3):                                                                    # rattling teeth tied to it
		p.seg((h[2][0], -0.05, h[2][1]), (h[2][0] + 0.05 + k * 0.08, -0.08, h[2][1] - 0.2 - k * 0.04), 0.012, 0.012, WOOD_GRAY, sides=4)
		p.seg((h[2][0] + 0.05 + k * 0.08, -0.08, h[2][1] - 0.2 - k * 0.04), (h[2][0] + 0.06 + k * 0.08, -0.08, h[2][1] - 0.34 - k * 0.04),
			  0.035, 0.0, BONE, sides=5)
	return p.build()


# ---------------------------------------------------------------- Forgehold, the Burn and Blackglass
# Magmasteel is dark steel split by glowing orange seams, Emberhide charcoal-red
# scaled leather, Flameweave deep red cloth stitched with gold flames; the
# Blackglass is obsidian, near black with a violet sheen, and pale sea-glass.

OBSIDIAN = IRON        # black glass: the near-black swatch
VIOLET = PETAL_PURPLE  # the sheen on it


def _seam(p, pts, swatch=EMBER, r=0.018, glow=2.4):
	"""A glowing line through pts."""
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, r, r, swatch, sides=4, glow=glow)


def _flame_mark(p, c, s=1.0, swatch=GOLD, glow=1.2):
	"""A little flame worked on a surface that faces the camera: a tall tongue and two small ones."""
	x, y, z = c
	p.seg((x, y, z - 0.04 * s), (x + 0.03 * s, y, z + 0.3 * s), 0.075 * s, 0.0, swatch, sides=5, glow=glow)
	for sx in (-1, 1):
		p.seg((x + sx * 0.06 * s, y, z - 0.04 * s), (x + sx * 0.13 * s, y, z + 0.15 * s), 0.05 * s, 0.0, swatch, sides=4, glow=glow)
	p.blob((0.2 * s, 0.05, 0.1 * s), (x, y, z - 0.04 * s), swatch, segs=(6, 4), glow=glow)


def _front(x, z, off=0.02):
	"""A point on the front of a torso (an ellipsoid round (0, 0, 0.5)), off toward the camera."""
	q = 1 - (x / 0.5) ** 2 - ((z - 0.5) / 0.55) ** 2
	return (x, -0.28 * math.sqrt(max(q, 0.0)) - off, z)


def _torso(p, body, trim, grad=(0.0, 0.7), pauldrons=True, belt=None):
	"""A chest piece standing up, front to the camera: a rounded body, a collar,
	optionally plate pauldrons, a belt and tassets."""
	p.blob((1.0, 0.56, 1.1), (0, 0, 0.5), body, segs=(18, 12), grad=grad)
	p.seg((0, 0, 0.94), (0, 0, 1.1), 0.26, 0.23, trim, sides=16, grad=grad)             # the collar
	p.seg((0, 0, 1.095), (0, 0, 1.105), 0.19, 0.19, STONE_DARK, sides=16)
	p.blob((0.82, 0.5, 0.16), (0, 0, 0.1), belt or trim, segs=(16, 6), grad=(0.1, 0.6))  # the belt
	if pauldrons:
		for sx in (-1, 1):
			p.blob((0.52, 0.6, 0.28), (sx * 0.46, 0, 0.8), body, rot=(0, sx * 32, 0), segs=(12, 8), grad=grad)
			p.blob((0.44, 0.56, 0.2), (sx * 0.55, 0, 0.66), trim, rot=(0, sx * 36, 0), segs=(12, 6), grad=grad)


def _scales(p, pts, swatches, size=(0.15, 0.05, 0.12), glow=0.0):
	for k, c in enumerate(pts):
		p.blob(size, c, swatches[k % len(swatches)], segs=(6, 4), grad=(0.0, 0.6), glow=glow)


def magmasteel_breastplate():
	p = Prop("magmasteel_breastplate", 1001)
	_torso(p, STONE_DARK, IRON, grad=(0.0, 0.55))
	p.seg(_front(0, 0.22, 0.0), _front(0, 0.92, 0.0), 0.035, 0.03, IRON, sides=5)             # a raised keel
	for z, bend in ((0.34, 0.03), (0.58, -0.04)):                                        # glowing seams between the plates
		_seam(p, [_front(-0.44 + k * 0.088, z + bend * math.cos(k * 0.63), 0.0) for k in range(11)])
	for sx in (-1, 1):
		_seam(p, [(sx * (0.36 + k * 0.05), -0.2 - k * 0.02, 0.78 - k * 0.05) for k in range(4)])
	c = _front(0, 0.76, 0.03)                                                             # a molten anvil on the chest
	p.box((0.3, 0.06, 0.07), (c[0], c[1], c[2] + 0.04), FLAME, glow=2.6)
	p.box((0.12, 0.06, 0.12), (c[0], c[1], c[2] - 0.04), FLAME, glow=2.6)
	p.box((0.26, 0.06, 0.05), (c[0], c[1], c[2] - 0.11), FLAME, glow=2.6)
	for k in range(5):                                                                    # rivets on the belt
		p.blob((0.05, 0.04, 0.05), (-0.3 + k * 0.15, -0.24 - 0.05 * (1 - abs(k - 2) / 2), 0.1), EMBER, segs=(6, 4), glow=1.6)
	return p.build()


def magmasteel_helm():
	p = Prop("magmasteel_helm", 1003)
	for z0, z1, r0, r1 in ((0.0, 0.3, 0.42, 0.42), (0.3, 0.52, 0.42, 0.34), (0.52, 0.68, 0.34, 0.2), (0.68, 0.76, 0.2, 0.0)):
		p.seg((0, 0, z0), (0, 0, z1), r0, r1, STONE_DARK, sides=16, grad=(0.0, 0.6))            # a dark steel dome
	_loop(p, (0, 0, 0.3), 0.42, True, 0.045, IRON, n=18)
	_loop(p, (0, 0, 0.36), 0.405, True, 0.016, EMBER, n=18, glow=2.4)                     # a seam of forge-glow above the brow
	p.box((0.6, 0.12, 0.36), (0, -0.37, 0.12), IRON, grad=(0.0, 0.6))               # a flat face plate
	p.box((0.44, 0.04, 0.05), (0, -0.44, 0.22), FLAME, glow=2.8)                          # its T-slit glowing from within
	p.box((0.06, 0.04, 0.22), (0, -0.44, 0.1), FLAME, glow=2.8)
	for k in range(9):                                                                    # a crest ridge over the top
		a0, a1 = math.radians(-70 + k * 17), math.radians(-70 + (k + 1) * 17)
		p.seg((0, math.sin(a0) * 0.44, 0.3 + math.cos(a0) * 0.46), (0, math.sin(a1) * 0.44, 0.3 + math.cos(a1) * 0.46), 0.06, 0.06, IRON, sides=5)
		p.seg((0.0, math.sin(a0) * 0.47, 0.3 + math.cos(a0) * 0.49), (0.0, math.sin(a1) * 0.47, 0.3 + math.cos(a1) * 0.49), 0.02, 0.02, EMBER,
			  sides=4, glow=2.4)
	for sx in (-1, 1):                                                                    # rivets down the plate
		for z in (0.02, 0.2):
			p.blob((0.05, 0.04, 0.05), (sx * 0.24, -0.44, z), EMBER, segs=(6, 4), glow=1.6)
	return p.build()


def magmasteel_vambraces():
	p = Prop("magmasteel_vambraces", 1005)
	t0, t1, r0, r1 = _vambrace(p, STONE_DARK, IRON, STONE_DARK, FLAME, grad=(0.0, 0.5), glow_line=EMBER)
	for t in (-0.29, 0.0, 0.28):                                                          # the lames' edges run molten
		r = _fa_r(t, r0, r1, t0, t1) + 0.03
		p.seg(_fa(t, 0, 0), _fa(t + 0.02, 0, 0), r, r, EMBER, sides=16, glow=1.6)
	return p.build()


def magmasteel_gauntlets():
	p, fr = _glove_pair("magmasteel_gauntlets", 1007, STONE_DARK, STONE_DARK, IRON, grad=(0.0, 0.5), style="gauntlet")
	for f in fr:
		for x, _ in FINGERS:                                                              # molten knuckles
			p.blob((0.09, 0.06, 0.07), f(x * 1.05, -0.15, 0.74), FLAME, segs=(6, 4), glow=2.4)
		_seam(p, [f(-0.22, -0.16, 0.5), f(0, -0.17, 0.46), f(0.22, -0.16, 0.5)])
		_seam(p, [f(-0.3, -0.26, 0.16), f(0, -0.3, 0.16), f(0.3, -0.26, 0.16)])
	return p.build()


def magmasteel_greaves():
	p = Prop("magmasteel_greaves", 1009)
	_trousers(p, STONE_DARK, IRON, leg_r=0.21, flare=0.03)
	for x in (-1, 1):
		for z in (0.64, 0.44, 0.18):                                                      # plate bands, their seams aglow
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.06), 0.235, 0.245, IRON, sides=12, grad=(0.0, 0.6))
			p.seg((x * 0.21, 0, z - 0.075), (x * 0.212, 0, z - 0.09), 0.235, 0.235, EMBER, sides=12, glow=2.2)
		p.blob((0.24, 0.14, 0.22), (x * 0.21, -0.18, 0.34), STONE_DARK, segs=(8, 6), grad=(0.0, 0.5))   # knee cop
		p.blob((0.08, 0.05, 0.08), (x * 0.21, -0.26, 0.34), FLAME, segs=(6, 4), glow=2.6)
	p.box((0.1, 0.06, 0.1), (0, -0.15, 1.0), FLAME, glow=2.0)
	return p.build()


def _boot(p, ox, oy, body, cuff, sole, grad=(0.1, 0.8), shaft=0.8, r=0.2):
	"""A tall boot standing, toe to the left; returns its shaft radius."""
	p.seg((ox, oy, 0.16), (ox + 0.02, oy, shaft), r, r + 0.03, body, sides=14, grad=grad)
	p.blob((0.66, r * 1.55, 0.3), (ox - 0.2, oy, 0.15), body, segs=(12, 8), grad=grad)
	p.blob((0.72, r * 1.7, 0.08), (ox - 0.2, oy, 0.02), sole, segs=(12, 4), grad=(0.1, 0.6))
	p.seg((ox + 0.02, oy, shaft), (ox + 0.02, oy, shaft + 0.09), r + 0.05, r + 0.05, cuff, sides=14, grad=grad)
	p.seg((ox + 0.02, oy, shaft + 0.09), (ox + 0.02, oy, shaft + 0.095), r + 0.01, r + 0.01, STONE_DARK, sides=14)   # hollow
	return r


def magmasteel_boots():
	p = Prop("magmasteel_boots", 1011)
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, STONE_DARK, IRON, IRON, grad=(0.0, 0.55), shaft=0.72, r=0.22)
		p.blob((0.32, 0.4, 0.26), (ox - 0.38, oy, 0.15), IRON, segs=(10, 6), grad=(0.0, 0.6))   # a toe cap
		for z in (0.32, 0.54):                                                            # glowing seams round the shaft
			_loop(p, (ox + 0.01, oy, z), r + 0.02, True, 0.016, EMBER, n=16, glow=2.4)
		p.blob((0.08, 0.05, 0.08), (ox + 0.02, oy - 0.27, 0.77), FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def magmasteel_shield():
	p = Prop("magmasteel_shield", 1013)
	outline = [(-0.46, 1.32), (0.0, 1.38), (0.46, 1.32), (0.46, 0.4), (0.3, 0.08), (0.0, -0.08), (-0.3, 0.08), (-0.46, 0.4)]
	_slab(p, outline, -0.05, 0.06, STONE_DARK, grad=(0.0, 0.6))                                  # a tall dark steel tower shield
	for a, b in zip(outline, outline[1:] + outline[:1]):                                  # a heavy rim
		p.seg((a[0], -0.06, a[1]), (b[0], -0.06, b[1]), 0.06, 0.06, IRON, sides=6)
	_seam(p, [(0, -0.07, 1.28), (0, -0.07, 0.0)], r=0.022)                                  # molten seams in a cross
	_seam(p, [(-0.42, -0.07, 0.86), (0.42, -0.07, 0.86)], r=0.022)
	p.seg((0, -0.06, 0.8), (0, -0.2, 0.8), 0.2, 0.16, IRON, sides=12)                 # an iron boss
	p.blob((0.2, 0.1, 0.2), (0, -0.21, 0.8), FLAME, segs=(10, 6), glow=2.8)                 # with a coal set in it
	for x, z in ((-0.34, 1.2), (0.34, 1.2), (-0.34, 0.45), (0.34, 0.45)):                    # rivets
		p.blob((0.07, 0.05, 0.07), (x, -0.08, z), IRON, segs=(6, 4))
	return p.build()


def _emberhide_scales(p, xs, zs, front):
	"""Rows of overlapping charcoal-red scales laid on a surface; front(x, z) gives the point."""
	pts, sw = [], []
	for row, z in enumerate(zs):
		for k, x in enumerate(xs):
			x2 = x + (0.5 * (xs[1] - xs[0]) if row % 2 else 0.0)
			pts.append(front(x2, z))
			sw.append(CLOTH_RED if (k + row) % 3 == 0 else STONE_DARK)
	for c, s in zip(pts, sw):
		p.blob((0.15, 0.05, 0.12), c, s, segs=(6, 4), grad=(0.0, 0.7))


def emberhide_jerkin():
	p = Prop("emberhide_jerkin", 1015)
	_torso(p, CLOTH_RED, STONE_DARK, grad=(0.55, 1.0), pauldrons=False, belt=WOOD)
	for sx in (-1, 1):                                                                    # leather shoulder caps
		p.blob((0.4, 0.58, 0.16), (sx * 0.38, 0, 0.86), STONE_DARK, rot=(0, sx * 28, 0), segs=(12, 6), grad=(0.1, 0.7))
	_emberhide_scales(p, [-0.36, -0.24, -0.12, 0.12, 0.24, 0.36], [0.28, 0.4, 0.52, 0.64, 0.76], lambda x, z: _front(x, z, -0.005))
	for k in range(5):                                                                    # laced up the front
		z = 0.24 + k * 0.13
		p.seg(_front(-0.07, z, 0.0), _front(0.07, z + 0.07, 0.0), 0.014, 0.014, HIDE, sides=4)
		p.seg(_front(0.07, z, 0.0), _front(-0.07, z + 0.07, 0.0), 0.014, 0.014, HIDE, sides=4)
	p.box((0.12, 0.06, 0.1), (0, -0.26, 0.1), GOLD)                                        # buckle
	p.seg(_front(-0.3, 0.2, 0.0), _front(0.3, 0.2, 0.0), 0.012, 0.012, EMBER, sides=4, glow=1.6)   # an ember-red seam
	return p.build()


def emberhide_leggings():
	p = Prop("emberhide_leggings", 1017)
	_trousers(p, CLOTH_RED, STONE_DARK)
	for x in (-1, 1):                                                                     # scaled thighs
		pts = []
		for row, z in enumerate((0.64, 0.54, 0.44)):
			for k in range(3):
				pts.append((x * 0.2 + (k - 1) * 0.12 + (0.06 if row % 2 else 0.0), -0.2, z))
		_scales(p, pts, [STONE_DARK, CLOTH_RED, STONE_DARK])
		p.blob((0.22, 0.12, 0.18), (x * 0.21, -0.2, 0.3), STONE_DARK, segs=(8, 5), grad=(0.1, 0.7))   # knee pads
		p.seg((x * 0.36, 0, 0.12), (x * 0.1, 0, 0.12), 0.03, 0.03, STONE_DARK, sides=5)
	p.box((0.1, 0.06, 0.08), (0, -0.15, 1.0), GOLD)
	return p.build()


def emberhide_gloves():
	p, fr = _glove_pair("emberhide_gloves", 1019, CLOTH_RED, STONE_DARK, EMBER, grad=(0.5, 1.0))
	for f in fr:                                                                          # charcoal-red scales down the back
		for row in range(3):
			for k in range(3 - row % 2):
				x = -0.14 + k * 0.14 + (0.07 if row % 2 else 0)
				p.blob((0.13, 0.05, 0.1), f(x, -0.12, 0.44 + row * 0.1), CLOTH_RED if (k + row) % 3 == 0 else STONE_DARK, rot=(0, f.tilt, 0),
					   segs=(6, 4), grad=(0.0, 0.6))
		for k in range(4):
			a = -0.21 + k * 0.14
			p.seg(f(a, -0.24, 0.18), f(a + 0.06, -0.24, 0.26), 0.014, 0.014, HIDE, sides=4)   # laced cuff
	return p.build()


def emberhide_boots():
	p = Prop("emberhide_boots", 1021)
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, CLOTH_RED, STONE_DARK, WOOD, grad=(0.55, 1.0), shaft=0.76)
		pts = []
		for row, z in enumerate((0.64, 0.52, 0.4, 0.28)):                                # scales down the shin
			for k in range(2):
				pts.append((ox + (k - 0.5) * 0.14 + (0.07 if row % 2 else 0.0), oy - r - 0.01, z))
		_scales(p, pts, [STONE_DARK, CLOTH_RED, STONE_DARK])
		p.seg((ox - 0.42, oy - 0.1, 0.22), (ox - 0.1, oy - 0.2, 0.22), 0.02, 0.02, EMBER, sides=4, glow=1.4)   # ember welt
	return p.build()


def _cap_cone(p, sw, band, pts, grad=(0.1, 0.8)):
	"""A soft cap: a band and a cone through (x, z, r) points, tip last."""
	p.seg((0, 0, 0.0), (0, 0, 0.16), 0.43, 0.43, band, sides=18, grad=(0.0, 0.6))
	for a, b in zip(pts, pts[1:]):
		p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), a[2], b[2], sw, sides=16, grad=grad)
		p.blob((b[2] * 2, b[2] * 2, b[2] * 2), (b[0], 0, b[1]), sw, segs=(10, 6), grad=grad)


def flameweave_cap():
	p = Prop("flameweave_cap", 1023)
	p.seg((0, 0, 0.0), (0, 0, 0.72), 0.42, 0.33, CLOTH_RED, sides=18, grad=(0.1, 0.9))        # a tall deep-red cap, flat on top
	p.seg((0, 0, 0.72), (0, 0, 0.78), 0.33, 0.28, CLOTH_RED, sides=18, grad=(0.1, 0.5))
	p.seg((0, 0, -0.02), (0, 0, 0.14), 0.44, 0.43, GOLD, sides=18)                            # a gold band
	_loop(p, (0, 0, 0.72), 0.335, True, 0.025, GOLD, n=18)
	for k in range(5):                                                                    # gold flames climbing its sides
		a = math.radians(228 + k * 21)
		r = 0.4 - 0.02
		_flame_mark(p, (math.cos(a) * r, math.sin(a) * r - 0.015, 0.2), 0.95 if k % 2 == 0 else 0.7)
	p.blob((0.16, 0.16, 0.1), (0, 0, 0.8), GOLD, segs=(8, 5))                                 # a gold button on top
	p.seg((0, 0, 0.82), (0.03, 0, 1.05), 0.08, 0.0, FLAME, sides=6, glow=2.6)                   # holding a little flame
	return p.build()


def flameweave_robe():
	p = Prop("flameweave_robe", 1025)
	rz = lambda z: 0.62 + (0.34 - 0.62) * (z + 0.5) / 1.45
	p.seg((0, 0, -0.5), (0, 0, 0.95), 0.62, 0.34, CLOTH_RED, sides=20, grad=(0.1, 0.9))     # a long deep-red robe
	p.blob((0.98, 0.56, 0.34), (0, 0, 0.92), CLOTH_RED, segs=(14, 8), grad=(0.1, 0.6))       # its shoulders
	for sx in (-1, 1):                                                                    # wide hanging sleeves
		p.seg((sx * 0.4, 0, 0.92), (sx * 0.66, 0, 0.2), 0.14, 0.25, CLOTH_RED, sides=12, grad=(0.1, 0.9))
		p.seg((sx * 0.66, 0, 0.2), (sx * 0.69, 0, 0.12), 0.26, 0.27, ORANGE, sides=12)
		p.seg((sx * 0.69, 0, 0.12), (sx * 0.695, 0, 0.11), 0.2, 0.2, STONE_DARK, sides=12)
	p.seg((0, 0, 0.98), (0, 0, 1.1), 0.21, 0.25, GOLD, sides=14)                              # a gold collar
	p.seg((0, 0, 1.095), (0, 0, 1.105), 0.17, 0.17, STONE_DARK, sides=14)
	p.seg((0, 0, 0.42), (0, 0, 0.52), rz(0.42) + 0.02, rz(0.52) + 0.02, GOLD, sides=20)       # a gold sash
	p.seg((0.08, -rz(0.44) - 0.02, 0.44), (0.16, -rz(0.1) - 0.02, 0.1), 0.05, 0.03, GOLD, sides=5)
	p.seg((0, -rz(0.95), 0.95), (0, -rz(-0.5), -0.5), 0.035, 0.035, ORANGE, sides=5)         # the front opening, trimmed
	p.seg((0, 0, -0.5), (0, 0, -0.42), 0.635, 0.63, ORANGE, sides=20)                         # an orange hem
	for k in range(7):                                                                    # gold flames climbing from it
		a = math.radians(205 + k * 21.7)
		r = rz(-0.36) + 0.01
		_flame_mark(p, (math.cos(a) * r, math.sin(a) * r, -0.36), 0.9 if k % 2 else 0.65)
	for sx in (-1, 1):
		_flame_mark(p, (sx * 0.64, -0.24, 0.3), 0.45)
	return p.build()


def flameweave_gloves():
	p, fr = _glove_pair("flameweave_gloves", 1027, CLOTH_RED, GOLD, ORANGE, grad=(0.1, 0.8))
	for f in fr:                                                                          # a gold flame on the back of each
		x, y, z = f(0, -0.13, 0.46)
		_flame_mark(p, (x, y, z), 0.55)
	return p.build()


def _slipper(p, ox, oy, body, trim):
	p.blob((0.7, 0.36, 0.3), (ox, oy, 0.15), body, segs=(14, 8), grad=(0.1, 0.8))            # a soft slipper, toe to the left
	p.seg((ox + 0.14, oy, 0.2), (ox + 0.14, oy, 0.3), 0.17, 0.18, trim, sides=14)
	p.seg((ox + 0.14, oy, 0.3), (ox + 0.14, oy, 0.305), 0.14, 0.14, STONE_DARK, sides=14)
	pts = [(ox - 0.3, oy, 0.1), (ox - 0.44, oy, 0.16), (ox - 0.5, oy, 0.28), (ox - 0.44, oy, 0.38)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):                                        # its curled toe
		p.seg(a, b, 0.1 - i * 0.03, 0.07 - i * 0.03, body, sides=8, grad=(0.1, 0.8))
	p.blob((0.08, 0.08, 0.08), pts[-1], GOLD, segs=(6, 4), glow=1.2)
	p.blob((0.74, 0.38, 0.05), (ox, oy, 0.01), WOOD, segs=(12, 4))
	_flame_mark(p, (ox - 0.02, oy - 0.18, 0.1), 0.45)


def flameweave_slippers():
	p = Prop("flameweave_slippers", 1029)
	_slipper(p, -0.2, 0.3, CLOTH_RED, GOLD)
	_slipper(p, 0.3, -0.12, CLOTH_RED, GOLD)
	return p.build()


def _molten_edge(p, pts, y, r=0.022):
	_seam(p, [(x, y, z) for x, z in pts], r=r, glow=2.6)


def magmasteel_sword():
	p = Prop("magmasteel_sword", 1031)
	org, rot = (-0.55, -0.42), 48
	up = [(0.32, 0.1), (0.8, 0.11), (1.2, 0.1), (1.44, 0.06)]
	tip = (1.6, 0.0)
	outline = up + [tip] + [(x, -z) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.035, 0.035, STONE_DARK, grad=(0.0, 0.55))             # a dark steel blade
	for sgn in (1, -1):                                                                   # its edges molten
		_molten_edge(p, _rot2([(x, sgn * (z - 0.012)) for x, z in up[1:]] + [(tip[0] - 0.02, 0.0)], rot, org), -0.045)
	f = _rot2([(0.4, 0.0), (1.3, 0.0)], rot, org)
	p.seg((f[0][0], -0.045, f[0][1]), (f[1][0], -0.045, f[1][1]), 0.025, 0.012, IRON, sides=4)   # a fuller
	g = _rot2([(0.3, -0.32), (0.3, 0.32)], rot, org)
	p.seg((g[0][0], 0, g[0][1]), (g[1][0], 0, g[1][1]), 0.06, 0.06, IRON, sides=6)       # a heavy crossguard
	for end in g:
		p.blob((0.12, 0.12, 0.12), (end[0], 0, end[1]), EMBER, segs=(6, 4), glow=1.8)
	h = _rot2([(0.26, 0.0), (-0.12, 0.0), (-0.2, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.06, WOOD_GRAY, sides=6)     # a leather grip
	for t in (0.25, 0.55, 0.85):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.02, 0, q[1] - 0.02), (q[0] + 0.02, 0, q[1] + 0.02), 0.068, 0.068, STONE_DARK, sides=6)
	p.blob((0.16, 0.16, 0.16), (h[2][0], 0, h[2][1]), IRON, segs=(8, 6))               # a pommel with a coal in it
	p.blob((0.08, 0.05, 0.08), (h[2][0], -0.08, h[2][1]), FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def _haft(p, org, rot, s0, s1, r, swatch=WOOD_GRAY, bands=(), band_swatch=IRON):
	a, b = _rot2([(s0, 0.0), (s1, 0.0)], rot, org)
	p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), r, r, swatch, sides=8, grad=(0.2, 0.9))
	for s in bands:
		q0, q1 = _rot2([(s - 0.03, 0.0), (s + 0.03, 0.0)], rot, org)
		p.seg((q0[0], 0, q0[1]), (q1[0], 0, q1[1]), r * 1.25, r * 1.25, band_swatch, sides=8)


AXE_BLADE = [(1.12, 0.02), (1.44, 0.02), (1.5, -0.2), (1.62, -0.42), (1.78, -0.62), (1.64, -0.72), (1.45, -0.79), (1.27, -0.81),
			 (1.09, -0.79), (0.9, -0.72), (0.76, -0.62), (0.92, -0.42), (1.06, -0.2)]
AXE_EDGE = AXE_BLADE[4:11]


def magmasteel_war_axe():
	p = Prop("magmasteel_war_axe", 1033)
	org, rot = (-0.5, -0.5), 60
	_haft(p, org, rot, -0.1, 1.6, 0.06, bands=(0.1, 0.5, 1.1))
	_slab(p, _rot2(AXE_BLADE, rot, org), -0.05, 0.05, STONE_DARK, grad=(0.0, 0.55))              # a bearded dark steel head
	_molten_edge(p, _rot2([(x + 0.01, z) for x, z in AXE_EDGE], rot, org), -0.06, r=0.028)    # its edge still molten
	spike = _rot2([(1.18, 0.0), (1.4, 0.0), (1.3, 0.32)], rot, org)                          # a back spike
	_slab(p, spike, -0.04, 0.04, IRON, grad=(0.0, 0.6))
	c = _rot2([(1.28, -0.06)], rot, org)[0]
	p.seg((c[0], 0.06, c[1]), (c[0], -0.07, c[1]), 0.08, 0.08, IRON, sides=8)            # the head's wedge
	p.blob((0.06, 0.04, 0.06), (c[0], -0.08, c[1]), FLAME, segs=(6, 4), glow=2.4)
	return p.build()


def magmasteel_greataxe():
	p = Prop("magmasteel_greataxe", 1035)
	org, rot = (-0.5, -0.7), 62
	_haft(p, org, rot, -0.2, 2.0, 0.065, bands=(0.0, 0.4, 0.8, 1.2))
	for sgn in (1, -1):                                                                   # a double-bitted head
		blade = [(x + 0.1, sgn * z) for x, z in AXE_BLADE]
		_slab(p, _rot2(blade, rot, org), -0.05, 0.05, STONE_DARK, grad=(0.0, 0.55))
		_molten_edge(p, _rot2([(x + 0.11, sgn * z) for x, z in AXE_EDGE], rot, org), -0.06, r=0.028)
	top = _rot2([(1.5, -0.07), (1.5, 0.07), (1.92, 0.0)], rot, org)                          # a spike on top
	_slab(p, top, -0.04, 0.04, IRON, grad=(0.0, 0.6))
	c = _rot2([(1.4, 0.0)], rot, org)[0]
	p.seg((c[0], 0.07, c[1]), (c[0], -0.08, c[1]), 0.1, 0.1, IRON, sides=8)
	p.blob((0.08, 0.05, 0.08), (c[0], -0.09, c[1]), FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def blackglass_dirk():
	p = Prop("blackglass_dirk", 1037)
	org, rot = (-0.5, -0.35), 48
	up = [(0.3, 0.1), (0.5, 0.15), (0.75, 0.15), (0.98, 0.11), (1.16, 0.05)]
	tip = (1.3, 0.0)
	outline = up + [tip] + [(x, -z) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.04, 0.04, OBSIDIAN, grad=(0.0, 0.35))            # a knapped blade of black glass
	for k in range(4):                                                                    # its flake scars, catching the light
		s = 0.42 + k * 0.2
		a, b = _rot2([(s, 0.12 - k * 0.02), (s + 0.12, -0.02)], rot, org)
		p.seg((a[0], -0.05, a[1]), (b[0], -0.05, b[1]), 0.012, 0.008, VIOLET, sides=4, glow=1.4)
	for sgn in (1, -1):
		e = _rot2([(x, sgn * (z - 0.01)) for x, z in up] + [(tip[0] - 0.01, 0.0)], rot, org)
		for a, b in zip(e, e[1:]):
			p.seg((a[0], -0.045, a[1]), (b[0], -0.045, b[1]), 0.01, 0.01, CLOTH_WHITE if sgn > 0 else VIOLET, sides=4, glow=0.8)
	g = _rot2([(0.28, -0.2), (0.28, 0.2)], rot, org)
	p.seg((g[0][0], 0, g[0][1]), (g[1][0], 0, g[1][1]), 0.05, 0.05, STONE_DARK, sides=6)       # an iron guard
	h = _rot2([(0.24, 0.0), (-0.16, 0.0), (-0.24, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.05, 0.055, HIDE, sides=6)          # a hide-wrapped grip
	for t in (0.2, 0.45, 0.7, 0.95):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.015, 0, q[1] - 0.015), (q[0] + 0.015, 0, q[1] + 0.015), 0.06, 0.06, WOOD, sides=6)
	p.rock((0.18, 0.16, 0.18), (h[2][0], 0, h[2][1]), OBSIDIAN, grad=(0.0, 0.4), jitter=0.04)   # a glass pommel
	return p.build()


def forgeheart_staff():
	p = Prop("forgeheart_staff", 1039)
	org, rot = (-0.3, -0.7), 72
	_haft(p, org, rot, 0.0, 1.6, 0.06, swatch=WOOD, bands=(0.3, 0.9, 1.5), band_swatch=STONE_DARK)
	c = _rot2([(1.95, 0.0)], rot, org)[0]                                                  # a great coal in an iron claw
	p.blob((0.56, 0.5, 0.56), (c[0], 0, c[1]), EMBER, segs=(14, 10), glow=2.4)
	for k in range(6):
		a = k * math.tau / 6 + 0.4
		p.rock((0.22, 0.14, 0.2), (c[0] + math.cos(a) * 0.2, -0.13, c[1] + math.sin(a) * 0.2), IRON, jitter=0.03)
	p.blob((0.2, 0.08, 0.2), (c[0] + 0.02, -0.26, c[1] + 0.02), FLAME, segs=(8, 5), glow=3.0)
	base = _rot2([(1.6, 0.0)], rot, org)[0]
	for sgn in (-1, 1, 0):                                                                # three iron prongs round it
		y = -0.05 if sgn else 0.26
		pts = [(base[0], y * 0.3, base[1]), (c[0] + sgn * 0.38 - 0.06, y, c[1] - 0.1), (c[0] + sgn * 0.33 - 0.04, y, c[1] + 0.3),
			   (c[0] + sgn * 0.1, y * 0.5, c[1] + 0.44)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.06 - i * 0.012, 0.048 - i * 0.012, STONE_DARK, sides=6)
	p.seg((base[0], 0, base[1] - 0.06), (base[0], 0, base[1] + 0.08), 0.12, 0.1, STONE_DARK, sides=8)
	for k in range(3):                                                                    # sparks rising
		p.blob((0.06, 0.06, 0.06), (c[0] - 0.15 + k * 0.17, -0.15, c[1] + 0.5 + (k % 2) * 0.16), GOLD, segs=(5, 3), glow=2.4)
	return p.build()


def forgehold_longbow():
	p = Prop("forgehold_longbow", 1041)
	org, rot = (0.0, 0.6), 50
	pts = []
	for k in range(17):                                                                   # a long limb of dark wood, recurved at the tips
		t = -1 + k / 8
		w = 0.3 * (1 - t * t) - 0.08 * max(0.0, abs(t) - 0.75) / 0.25
		pts.append((t * 1.1, w))
	lp = _rot2(pts, rot, org)
	for i, (a, b) in enumerate(zip(lp, lp[1:])):
		mid = abs(i - 7.5) / 8
		r = 0.075 - mid * 0.04
		p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), r, r, WOOD, sides=6, grad=(0.55, 1.0))
	for k in (2, 4, 11, 13):                                                              # ember inlays along the limbs
		q = lp[k]
		p.blob((0.07, 0.05, 0.07), (q[0], -0.06, q[1]), FLAME, segs=(6, 4), glow=2.4)
	for k in (0, 16):                                                                     # iron-capped tips
		p.seg((lp[k][0], 0, lp[k][1]), (lp[k + (1 if k == 0 else -1)][0], 0, lp[k + (1 if k == 0 else -1)][1]), 0.05, 0.045, STONE_DARK, sides=6)
	g0, g1 = lp[7], lp[9]
	p.seg((g0[0], 0, g0[1]), (g1[0], 0, g1[1]), 0.09, 0.09, HIDE, sides=8)                   # a hide grip between iron bands
	for q in (g0, g1):
		p.seg((q[0] - 0.02, 0, q[1] - 0.02), (q[0] + 0.02, 0, q[1] + 0.02), 0.1, 0.1, STONE_DARK, sides=8)
	p.seg((lp[0][0], 0.02, lp[0][1]), (lp[16][0], 0.02, lp[16][1]), 0.012, 0.012, CLOTH_WHITE, sides=4)   # the string
	return p.build()


def magmasteel_arrow():
	p = Prop("magmasteel_arrow", 1043)
	a, b = (-0.6, 0, 0.05), (0.5, 0, 0.95)
	p.seg(a, b, 0.035, 0.035, WOOD_GRAY, sides=6)                                          # shaft
	p.seg(b, (0.74, 0, 1.15), 0.12, 0.0, IRON, sides=4, grad=(0.0, 0.5))                    # a dark steel head
	p.seg((0.52, -0.05, 0.97), (0.72, -0.05, 1.13), 0.022, 0.0, EMBER, sides=3, glow=2.4)    # its edge glowing
	p.seg((0.44, 0, 0.9), (0.51, 0, 0.96), 0.055, 0.055, STONE_DARK, sides=6)
	d = (Vector(b) - Vector(a)).normalized()
	for off, sw in (((-d.z, 0, d.x), FLAME), ((d.z, 0, -d.x), STONE_DARK), ((0, -1, 0), FLAME)):   # fletching
		n = Vector(off) * 0.13
		root, tip = Vector(a) + d * 0.04, Vector(a) + d * 0.3
		p.poly([tuple(root), tuple(tip), tuple(tip - d * 0.06 + n), tuple(root + n * 0.9)], [(0, 1, 2, 3)], sw)
	p.seg((-0.62, 0, 0.02), (-0.58, 0, 0.06), 0.04, 0.04, STONE_DARK, sides=5)
	return p.build()


# the Burn's drops

def _strands(p, seed, n, root, spread, length, fur, tip, tip_glow, up=False):
	import random
	rnd = random.Random(seed)
	for k in range(n):
		x0 = root[0] + rnd.uniform(-0.1, 0.1)
		sway = rnd.uniform(-spread, spread)
		d = 1 if up else -1
		z0 = root[2]
		pts = [(x0, root[1] + rnd.uniform(-0.08, 0.08), z0), (x0 + sway * 0.4, root[1], z0 + d * length * 0.4),
			   (x0 + sway, root[1], z0 + d * length * 0.8), (x0 + sway * 1.3, root[1], z0 + d * length)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			last = i == 2
			p.seg(a, b, 0.055 - i * 0.012, 0.043 - i * 0.012 if not last else 0.0, tip if last else fur[k % len(fur)], sides=4,
				  glow=tip_glow if last else 0.0)


def firehound_mane():
	p = Prop("firehound_mane", 1051)
	_strands(p, 1051, 14, (0, 0, 1.0), 0.35, 1.0, [STONE_DARK, WOOD_GRAY, CLOTH_RED], FLAME, 2.4)   # coarse dark hair, its ends burning
	p.seg((0, 0, 0.88), (0, 0, 1.08), 0.15, 0.13, STONE_DARK, sides=8)                        # bound with an iron ring
	p.seg((0, 0, 0.94), (0, 0, 0.98), 0.16, 0.16, EMBER, sides=8, glow=1.6)
	p.blob((0.22, 0.18, 0.18), (0, 0, 1.14), CLOTH_RED, segs=(8, 5))
	return p.build()


def imp_horn():
	p = Prop("imp_horn", 1053)
	pts = []
	for k in range(9):                                                                    # a small curled horn
		t = k / 8
		a = t * 2.2
		pts.append((-0.4 + math.sin(a) * 0.55, 0, 0.1 + (1 - math.cos(a)) * 0.45))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		r = 0.2 * (1 - i / 8) + 0.01
		sw = CLOTH_RED if i < 3 else CRIMSON if i < 6 else STONE_DARK
		p.seg(a, b, r, max(r - 0.022, 0.0) if i < 7 else 0.0, sw, sides=8, grad=(0.1, 0.8))
		if i < 6:                                                                         # ridged rings
			p.seg(b, tuple(b[j] + (pts[i + 2][j] - b[j]) * 0.15 for j in range(3)), r - 0.005, r - 0.02, STONE_DARK, sides=8)
	p.blob((0.08, 0.08, 0.08), pts[-1], EMBER, segs=(6, 4), glow=2.4)                      # still hot at the tip
	p.seg((pts[0][0], 0, pts[0][2] - 0.1), pts[0], 0.24, 0.2, STONE_DARK, sides=8, jitter=0.02)   # its torn, scorched root
	return p.build()


def smoke_essence():
	p = Prop("smoke_essence", 1055)
	p.blob((0.78, 0.78, 0.86), (0, 0, 0.43), CLOTH_WHITE, segs=(14, 10), grad=(0.3, 0.9))    # a clear flask
	top = _potion(p, 0.82, neck=0.22, neck_r=0.09, cork=WOOD)
	p.blob((0.26, 0.26, 0.14), (0, 0, top + 0.14), CLOTH_RED, segs=(8, 5))                   # sealed with red wax
	pts = []
	for k in range(22):                                                                   # thick smoke coiling inside
		t = k / 21
		a = t * 4.0 * math.pi
		pts.append((math.cos(a) * (0.12 + 0.2 * math.sin(t * math.pi)), -0.36 - 0.04 * math.sin(a), 0.12 + t * 0.6))
	for k, c in enumerate(pts):
		s = 0.12 + 0.08 * math.sin(k / 21 * math.pi)
		p.blob((s, s * 0.6, s), c, STONE_DARK if k % 3 else ASH, segs=(6, 4), grad=(0.2, 0.8))
	for k in range(3):                                                                    # a wisp slipping past the seal
		p.blob((0.1 + k * 0.04,) * 3, (0.1 + 0.08 * (k % 2), -0.04, top + 0.3 + k * 0.12), ASH, segs=(6, 4))
	_frame(p, *POTION_FRAME)
	return p.build()


def giants_coal():
	p = Prop("giants_coal", 1057)
	for sx in (-1, 1):                                                                    # a lump of coal the shape of a heart
		p.rock((0.62, 0.55, 0.58), (sx * 0.22, 0, 0.66), STONE_DARK, jitter=0.07)
	p.rock((0.66, 0.56, 0.66), (0.0, 0, 0.32), STONE_DARK, jitter=0.07)
	p.rock((0.3, 0.3, 0.3), (0.02, 0, 0.02), STONE_DARK, jitter=0.06)
	p.blob((0.46, 0.2, 0.42), (0, -0.2, 0.5), EMBER, segs=(10, 6), glow=2.0)                  # burning at its heart
	for a, b in (((-0.3, 0.8), (-0.1, 0.55)), ((-0.1, 0.55), (0.0, 0.3)), ((0.0, 0.3), (0.05, 0.08)), ((-0.1, 0.55), (0.25, 0.7)),
				 ((0.25, 0.7), (0.35, 0.85)), ((0.0, 0.3), (0.22, 0.28))):                  # cracks full of fire
		p.seg((a[0], -0.3, a[1]), (b[0], -0.3, b[1]), 0.03, 0.03, FLAME, sides=4, glow=2.8)
	return p.build()


def firebird_feather():
	p = Prop("firebird_feather", 1059)
	_vane(p, (-0.35, 0, 0.0), (0.4, 0, 1.25), 0.26, FLAME, tip_swatch=EMBER, glow=2.0)       # a long feather of living fire
	for k, (x, z) in enumerate(((0.35, 0.3), (-0.3, 0.75), (0.55, 0.8), (0.1, 1.35), (-0.4, 0.3))):   # sparks shed off it
		p.blob((0.05 + 0.02 * (k % 2),) * 3, (x, -0.05, z), GOLD, segs=(5, 3), glow=2.6)
	return p.build()


def ashmaws_mane():
	p = Prop("ashmaws_mane", 1061)
	p.blob((0.9, 0.5, 0.4), (0, 0, 0.2), ASH, segs=(12, 6), grad=(0.3, 1.0), jitter=0.04)       # a great hank of ashen mane
	_strands(p, 1061, 18, (0, 0, 0.2), 0.45, 0.95, [ASH, STONE_DARK, WOOD_GRAY], FLAME, 2.8, up=True)   # rising in flame
	for x, h in ((-0.3, 0.9), (0.05, 1.25), (0.35, 0.95)):                                   # tongues of fire over it
		p.seg((x, -0.1, 0.5), (x + 0.05, -0.1, 0.5 + h), 0.14, 0.0, FLAME, sides=6, glow=2.6)
	p.seg((-0.5, -0.02, 0.1), (0.5, -0.02, 0.1), 0.1, 0.1, GOLD, sides=8)                     # bound in a gold cuff
	p.seg((0, -0.12, 0.1), (0.02, -0.2, -0.2), 0.06, 0.0, BONE, sides=5)                     # a fang hung from it
	return p.build()


def cackleflames_crown():
	p = Prop("cackleflames_crown", 1063)
	_loop(p, (0, 0, 0.12), 0.4, True, 0.07, STONE_DARK, n=16)                               # a little blackened circlet
	_loop(p, (0, 0, 0.12), 0.41, True, 0.02, EMBER, n=16, glow=2.0)
	for k in range(9):                                                                    # its points are flames
		a = k * math.tau / 9 + 0.3
		h = 0.42 + (0.22 if k % 2 else 0.0)
		x, y = math.cos(a) * 0.4, math.sin(a) * 0.4
		p.seg((x, y, 0.14), (x * 1.08, y * 1.08, 0.14 + h), 0.1, 0.0, FLAME, sides=6, glow=2.6)
		p.seg((x, y, 0.14), (x * 1.02, y * 1.02, 0.14 + h * 0.55), 0.06, 0.0, GOLD, sides=5, glow=3.0)
	p.blob((0.14, 0.08, 0.14), (0, -0.42, 0.14), GOLD, segs=(8, 5), glow=2.4)                # a grinning imp's gem
	return p.build()


def thanes_iron_crown():
	p = Prop("thanes_iron_crown", 1065)
	p.seg((0, 0, 0.0), (0, 0, 0.34), 0.52, 0.52, IRON, sides=20, grad=(0.0, 0.6))            # a thick band of dark iron
	p.seg((0, 0, 0.335), (0, 0, 0.345), 0.44, 0.44, STONE_DARK, sides=20)
	for z in (0.02, 0.32):
		p.seg((0, 0, z - 0.02), (0, 0, z + 0.02), 0.54, 0.54, STONE_DARK, sides=20)
	for k in range(8):                                                                    # square battlements
		a = k * math.tau / 8
		p.box((0.18, 0.12, 0.24), (math.cos(a) * 0.48, math.sin(a) * 0.48, 0.44), IRON, rot=(0, 0, math.degrees(a) + 90), grad=(0.0, 0.6))
		b = a + math.tau / 16
		p.seg((math.cos(b) * 0.535, math.sin(b) * 0.535, 0.06), (math.cos(b) * 0.535, math.sin(b) * 0.535, 0.28), 0.018, 0.018, EMBER,
			  sides=4, glow=2.4)                                                          # seams glowing between the plates
	for k in range(3):                                                                    # molten stones in front
		a = math.radians(250 + k * 20)
		p.blob((0.14, 0.08, 0.14), (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.17), FLAME, segs=(8, 5), glow=2.6)
	return p.build()


def phoenix_ember():
	p = Prop("phoenix_ember", 1067)
	p.blob((0.46, 0.46, 0.5), (0, 0, 0.55), FLAME, segs=(14, 10), glow=3.2)                  # an ember that will not go out
	p.blob((0.24, 0.1, 0.24), (-0.04, -0.22, 0.6), CLOTH_WHITE, segs=(8, 5), glow=3.0)
	for k in range(7):                                                                    # a crown of flame round it
		a = math.radians(20 + k * 23)
		p.seg((math.cos(a) * 0.16, 0.02, 0.55 + math.sin(a) * 0.16), (math.cos(a) * 0.5, 0.02, 0.55 + math.sin(a) * 0.62), 0.09, 0.0, EMBER,
			  sides=5, glow=2.4)
	for sx in (-1, 1):                                                                    # small wings of feather
		_vane(p, (sx * 0.12, 0.06, 0.45), (sx * 0.85, 0.06, 0.7), 0.16, ORANGE, tip_swatch=FLAME)
	for x, z in ((-0.4, 0.15), (0.3, 0.1), (0.05, -0.05)):                                  # sparks falling
		p.blob((0.05, 0.05, 0.05), (x, -0.1, z), GOLD, segs=(5, 3), glow=2.6)
	return p.build()


# the Blackglass's drops

def glass_core():
	p = Prop("glass_core", 1071)
	p.seg((0, 0, 0.0), (0, 0, 0.5), 0.0, 0.42, AQUA, sides=6, grad=(0.0, 0.5))               # a faceted crystal heart
	p.seg((0, 0, 0.5), (0, 0, 1.1), 0.42, 0.0, AQUA, sides=6, grad=(0.0, 0.5))
	p.blob((0.34, 0.24, 0.4), (0, -0.3, 0.52), CLOTH_WHITE, segs=(8, 6), glow=3.0)             # its light
	for k in range(9):                                                                    # a cage of black glass shards round it
		a = k * math.tau / 9 + 0.2
		b = ((k % 3) - 1) * 0.45
		c = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b) * 0.6, math.sin(b)))
		base = Vector((0, 0.1, 0.52)) + c * 0.3
		p.seg(tuple(base), tuple(base + c * (0.42 + 0.14 * (k % 2))), 0.14, 0.0, OBSIDIAN, sides=4, grad=(0.0, 0.4))
		p.seg(tuple(base + c * 0.1 + Vector((0, -0.08, 0))), tuple(base + c * 0.34 + Vector((0, -0.05, 0))), 0.015, 0.0, VIOLET, sides=3, glow=2.0)
	return p.build()


def obsidian_scale():
	p = Prop("obsidian_scale", 1073)
	outline = []
	for k in range(17):                                                                   # one great scale of black glass
		a = math.radians(195 + k * (150 / 16))
		outline.append((math.cos(a) * 0.55, (0.55 + math.sin(a) * 0.55)))
	outline += [(0.4, 0.95), (0.0, 1.4), (-0.4, 0.95)]
	_slab(p, outline, -0.06, 0.06, OBSIDIAN, grad=(0.0, 0.4))
	p.seg((0, -0.08, 0.1), (0, -0.08, 1.25), 0.05, 0.015, STONE_DARK, sides=4)               # its keel
	for a, b in zip(outline, outline[1:] + outline[:1]):                                  # a violet sheen round the edge
		p.seg((a[0], -0.07, a[1]), (b[0], -0.07, b[1]), 0.025, 0.025, VIOLET, sides=4, glow=1.8)
	p.seg((-0.28, -0.08, 0.35), (-0.12, -0.08, 0.95), 0.03, 0.01, CLOTH_WHITE, sides=4, glow=1.0)   # a glint
	return p.build()


def glass_silk():
	p = Prop("glass_silk", 1075)
	for sx in (-1, 1):                                                                    # a spool
		p.seg((sx * 0.46, 0, 0.45), (sx * 0.38, 0, 0.45), 0.42, 0.42, WOOD_GRAY, sides=14, grad=(0.1, 0.7))
	p.seg((-0.38, 0, 0.45), (0.38, 0, 0.45), 0.31, 0.31, AQUA, sides=14, grad=(0.0, 0.45))   # wound with glassy thread
	for k in range(7):
		x = -0.33 + k * 0.11
		_oval(p, (x, 0, 0.45), (0, 1, 0), (0, 0, 1), 0.32, 0.32, 0.012, CLOTH_WHITE, n=14, glow=1.2)
	pts = [(0.2, -0.3, 0.3), (0.45, -0.4, 0.15), (0.7, -0.35, 0.05), (0.9, -0.3, 0.12)]      # a loose strand, beaded with glass
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.014, 0.014, CLOTH_WHITE, sides=4, glow=1.2)
	for c in pts[1:]:
		p.blob((0.07, 0.07, 0.07), c, AQUA, segs=(6, 4), glow=1.8)
	return p.build()


def glassbound_insignia():
	p = Prop("glassbound_insignia", 1077)
	for sx in (-1, 1):                                                                    # ribbon tails
		p.box((0.14, 0.03, 0.5), (sx * 0.16, 0.06, 1.08), RUNE, rot=(0, sx * -12, 0))
	outline = [(-0.45, 1.1), (0.45, 1.1), (0.45, 0.55), (0.3, 0.22), (0.0, 0.0), (-0.3, 0.22), (-0.45, 0.55)]
	_slab(p, outline, -0.04, 0.05, OBSIDIAN, grad=(0.0, 0.4))                               # a badge gone to black glass
	for a, b in zip(outline, outline[1:] + outline[:1]):                                  # its silver rim
		p.seg((a[0], -0.05, a[1]), (b[0], -0.05, b[1]), 0.035, 0.035, STONE_LIGHT, sides=5)
	p.seg((0, -0.06, 0.95), (0, -0.06, 0.2), 0.04, 0.0, STONE_LIGHT, sides=4)                 # a knight's sword on it
	p.seg((-0.16, -0.06, 0.82), (0.16, -0.06, 0.82), 0.03, 0.03, STONE_LIGHT, sides=4)
	p.blob((0.07, 0.04, 0.07), (0, -0.07, 0.96), RUNE, segs=(6, 4), glow=1.0)
	_seam(p, [(-0.4, -0.06, 0.4), (-0.22, -0.06, 0.52), (-0.15, -0.06, 0.4), (0.05, -0.06, 0.58), (0.4, -0.06, 0.66)], VIOLET, r=0.014, glow=2.0)
	return p.build()


def colossus_heart():
	p = Prop("colossus_heart", 1079)
	p.rock((1.0, 0.8, 1.05), (0, 0.1, 0.52), OBSIDIAN, grad=(0.0, 0.45), jitter=0.06)        # a black glass heart
	p.blob((0.66, 0.36, 0.66), (0, -0.3, 0.52), EMBER, segs=(14, 8), glow=2.2)                 # a molten core swelling out of it
	p.blob((0.34, 0.12, 0.34), (-0.04, -0.47, 0.56), FLAME, segs=(10, 6), glow=3.0)
	for a, b in (((-0.28, 0.78), (0.0, 0.54)), ((0.0, 0.54), (0.26, 0.34)), ((0.0, 0.54), (-0.22, 0.3)), ((0.0, 0.54), (0.24, 0.72))):
		p.seg((a[0], -0.5, a[1]), (b[0], -0.5, b[1]), 0.03, 0.03, OBSIDIAN, sides=4)       # held in cracked glass
	for x, z in ((-0.42, 0.95), (0.44, 0.9), (0.12, 1.08), (-0.5, 0.3)):                    # shards jutting from it
		p.seg((x * 0.75, 0.05, z - 0.2), (x, 0.0, z + 0.14), 0.13, 0.0, OBSIDIAN, sides=4, grad=(0.0, 0.4))
	for x, z in ((-0.36, 0.62), (0.36, 0.5)):
		p.blob((0.05, 0.03, 0.05), (x, -0.4, z), VIOLET, segs=(5, 3), glow=2.0)
	return p.build()


def vitrax_eye():
	p = Prop("vitrax_eye", 1081)
	p.blob((1.0, 1.0, 1.0), (0, 0, 0.5), CLOTH_WHITE, segs=(18, 12), grad=(0.0, 0.55))        # a huge glass eye
	p.blob((0.66, 0.24, 0.66), (0, -0.4, 0.52), VIOLET, segs=(16, 8), grad=(0.0, 0.7), glow=1.2)   # a violet iris
	p.blob((0.1, 0.1, 0.52), (0, -0.51, 0.52), OBSIDIAN, segs=(8, 6))                        # a drake's slit pupil
	p.blob((0.12, 0.04, 0.1), (-0.14, -0.52, 0.68), CLOTH_WHITE, segs=(6, 4), glow=2.0)      # a glint
	for k in range(6):                                                                    # veins of black glass
		a = math.radians(-20 + k * 60)
		p.seg((math.cos(a) * 0.47, -0.12, 0.5 + math.sin(a) * 0.47), (math.cos(a) * 0.36, -0.36, 0.5 + math.sin(a) * 0.36), 0.02, 0.01,
			  OBSIDIAN, sides=4)
	for k in range(5):                                                                    # and the socket's shards behind
		a = math.radians(20 + k * 35)
		p.seg((math.cos(a) * 0.3, 0.2, 0.5 + math.sin(a) * 0.3), (math.cos(a) * 0.72, 0.25, 0.5 + math.sin(a) * 0.72), 0.12, 0.0,
			  OBSIDIAN, sides=4, grad=(0.0, 0.4))
	return p.build()


def shardmothers_crown():
	p = Prop("shardmothers_crown", 1083)
	_loop(p, (0, 0, 0.12), 0.44, True, 0.08, OBSIDIAN, n=16)                                # a ring of black glass
	for k in range(11):                                                                   # grown into a crown of shards
		a = k * math.tau / 11 + 0.2
		h = 0.35 + 0.35 * ((k * 7) % 5) / 4
		lean = 0.12 + 0.08 * (k % 2)
		x, y = math.cos(a) * 0.44, math.sin(a) * 0.44
		sw, glow = ((AQUA, 0.8), (OBSIDIAN, 0.0), (VIOLET, 1.2))[k % 3]
		p.seg((x, y, 0.1), (x * (1 + lean), y * (1 + lean), 0.1 + h), 0.09, 0.0, sw, sides=4, grad=(0.0, 0.45), glow=glow)
	p.seg((0, -0.45, 0.14), (0, -0.52, 0.8), 0.12, 0.0, AQUA, sides=4, grad=(0.0, 0.4), glow=1.0)   # the tallest in front
	p.blob((0.12, 0.08, 0.12), (0, -0.5, 0.16), CLOTH_WHITE, segs=(6, 4), glow=2.2)
	return p.build()


def aldrics_banner():
	p = Prop("aldrics_banner", 1085)
	p.seg((-0.5, 0.05, -0.3), (-0.5, 0.05, 1.45), 0.045, 0.045, WOOD_GRAY, sides=8)          # a pole
	p.seg((-0.5, 0.05, 1.45), (-0.5, 0.05, 1.62), 0.07, 0.0, STONE_LIGHT, sides=4)           # its spear point
	p.seg((-0.55, 0.0, 1.32), (0.45, 0.0, 1.32), 0.035, 0.035, WOOD_GRAY, sides=6)           # a crossbar
	cloth = [(-0.45, 1.3), (0.4, 1.3), (0.4, 0.3), (0.28, 0.12), (0.18, 0.3), (0.0, 0.08), (-0.14, 0.3), (-0.26, 0.1), (-0.45, 0.3)]
	_slab(p, cloth, 0.0, 0.03, RUNE, grad=(0.3, 1.0))                                        # a knight's blue banner, ragged
	p.seg((-0.03, -0.02, 1.1), (-0.03, -0.02, 0.45), 0.04, 0.0, STONE_LIGHT, sides=4)          # its silver sword
	p.seg((-0.2, -0.02, 0.98), (0.14, -0.02, 0.98), 0.03, 0.03, STONE_LIGHT, sides=4)
	for x, z, h, a in ((0.25, 0.7, 0.3, 30), (-0.3, 0.55, 0.25, -35), (0.1, 0.35, 0.22, 10), (0.3, 1.1, 0.2, 60)):   # black glass grown through it
		r = math.radians(a)
		p.seg((x, 0.0, z), (x + math.sin(r) * h, -0.1, z + math.cos(r) * h), 0.08, 0.0, OBSIDIAN, sides=4, grad=(0.0, 0.4))
		p.blob((0.05, 0.03, 0.05), (x + math.sin(r) * h * 0.5, -0.07, z + math.cos(r) * h * 0.5), VIOLET, segs=(5, 3), glow=1.8)
	return p.build()


# the Burn and Blackglass's rewards

def coalhand_gauntlets():
	p, fr = _glove_pair("coalhand_gauntlets", 1091, STONE_DARK, WOOD_GRAY, IRON, grad=(0.1, 0.7), style="gauntlet")
	for f in fr:                                                                          # a live coal set in the back of each
		p.rock((0.36, 0.16, 0.32), f(0, -0.16, 0.55), IRON, jitter=0.04)
		p.blob((0.24, 0.1, 0.22), f(0, -0.23, 0.55), FLAME, segs=(8, 5), glow=2.8)
		for a in (0.3, 1.9, 3.5, 5.0):                                                    # glowing cracks out from it
			p.seg(f(math.cos(a) * 0.12, -0.2, 0.55 + math.sin(a) * 0.1), f(math.cos(a) * 0.24, -0.17, 0.55 + math.sin(a) * 0.2),
				  0.014, 0.01, EMBER, sides=4, glow=2.2)
	return p.build()


def thanes_hammer():
	p = Prop("thanes_hammer", 1093)
	org, rot = (-0.5, -0.8), 62
	_haft(p, org, rot, -0.2, 1.7, 0.075, swatch=WOOD, bands=(-0.1, 0.3, 0.7, 1.1))
	head = [(1.35, -0.55), (1.95, -0.55), (2.0, -0.45), (2.0, 0.45), (1.95, 0.55), (1.35, 0.55), (1.3, 0.45), (1.3, -0.45)]
	_slab(p, _rot2(head, rot, org), -0.26, 0.26, IRON, grad=(0.0, 0.55))                    # a great block of dark iron
	for sgn in (1, -1):                                                                   # striking faces
		face = [(1.36, sgn * 0.55), (1.94, sgn * 0.55), (1.94, sgn * 0.62), (1.36, sgn * 0.62)]
		_slab(p, _rot2(face, rot, org), -0.23, 0.23, STONE_DARK, grad=(0.0, 0.6))
	for s in (1.45, 1.85):                                                                # molten bands round it
		_seam(p, [(q[0], -0.28, q[1]) for q in _rot2([(s, -0.5), (s, 0.5)], rot, org)], r=0.03, glow=2.6)
	c = _rot2([(1.65, 0.0)], rot, org)[0]                                                  # a forge rune burning on its face
	_loop(p, (c[0], -0.28, c[1]), 0.18, False, 0.03, FLAME, n=12, glow=2.6)
	_seam(p, [(c[0] - 0.1, -0.29, c[1] + 0.1), (c[0] + 0.1, -0.29, c[1] - 0.1)], FLAME, r=0.03, glow=2.6)
	_seam(p, [(c[0] - 0.1, -0.29, c[1] - 0.1), (c[0] + 0.1, -0.29, c[1] + 0.1)], FLAME, r=0.03, glow=2.6)
	e = _rot2([(-0.25, 0.0)], rot, org)[0]
	p.blob((0.2, 0.2, 0.2), (e[0], 0, e[1]), STONE_DARK, segs=(8, 6))                          # an iron butt cap
	return p.build()


def firehound_mantle():
	p = Prop("firehound_mantle", 1095)
	outline = [(-0.26, 1.0), (0.26, 1.0), (0.5, 0.86), (0.66, 0.6), (0.7, 0.3), (0.58, 0.12), (0.3, 0.02), (0.0, 0.0), (-0.3, 0.02),
			   (-0.58, 0.12), (-0.7, 0.3), (-0.66, 0.6), (-0.5, 0.86)]                        # a mantle of dark firehound hide
	_slab(p, outline, -0.02, 0.06, STONE_DARK, grad=(0.2, 0.9))
	for k in range(6):                                                                    # glowing cracks in it
		x = -0.5 + k * 0.2
		pts = [(x, -0.03, 0.08 + 0.1 * abs(x)), (x + 0.06, -0.03, 0.3), (x - 0.02, -0.03, 0.46 + 0.05 * (k % 2))]
		_seam(p, pts, EMBER, r=0.02, glow=2.0)
	for k in range(9):                                                                    # a collar of its burning mane
		t = k / 8
		x = -0.36 + t * 0.72
		z = 0.97 - math.sin(t * math.pi) * 0.1
		p.blob((0.2, 0.16, 0.18), (x, -0.06, z), CLOTH_RED, segs=(6, 4), grad=(0.2, 0.9))
		p.seg((x, -0.08, z + 0.02), (x + 0.03 * (k % 3 - 1), -0.08, z + 0.2 + 0.08 * (k % 2)), 0.07, 0.0, FLAME, sides=5, glow=2.4)
	p.seg((0, -0.1, 0.82), (0, -0.16, 0.82), 0.11, 0.11, STONE_DARK, sides=10)                # an iron ring clasp
	for dx in (-0.07, 0.07):                                                               # and fangs
		p.seg((dx, -0.16, 0.76), (dx * 1.4, -0.18, 0.52), 0.045, 0.0, BONE, sides=5)
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(-15), 4, "X"))
	return obj


def ashmaws_fang_pendant():
	p = Prop("ashmaws_fang_pendant", 1097)
	_cord(p, 0.45, 0.84, STONE_DARK)
	pts = [(0, -0.3, 0.5), (0.06, -0.3, 0.25), (0.05, -0.3, 0.0), (-0.05, -0.3, -0.22)]       # a great curved fang
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.14 - i * 0.045, 0.095 - i * 0.045 if i < 2 else 0.0, BONE, sides=7, grad=(0.0, 0.6))
	p.seg((0, -0.3, 0.46), (0, -0.3, 0.6), 0.16, 0.15, IRON, sides=8)                        # capped in iron
	p.seg((0, -0.3, 0.5), (0, -0.3, 0.54), 0.165, 0.165, EMBER, sides=8, glow=2.0)
	for x, h in ((-0.12, 0.2), (0.1, 0.26), (0.0, 0.32)):                                   # a tuft of its mane, still burning
		p.seg((x, -0.34, 0.58), (x * 1.5, -0.36, 0.58 + h), 0.05, 0.0, FLAME, sides=5, glow=2.4)
	p.seg((0, -0.3, 0.6), (0, -0.3, 0.72), 0.04, 0.04, STONE_DARK, sides=6)
	return p.build()


def tallpine_signet():
	p = Prop("tallpine_signet", 1099)
	_ring(p, GOLD)
	p.seg((0, 0.08, 0.86), (0, -0.1, 0.86), 0.27, 0.27, GOLD, sides=10)                       # a signet face
	p.seg((0, -0.1, 0.86), (0, -0.12, 0.86), 0.22, 0.22, STONE_DARK, sides=10)               # of charred wood
	for k, (z, w) in enumerate(((0.7, 0.14), (0.8, 0.11), (0.9, 0.08))):                     # a tall pine on it
		p.seg((0, -0.13, z), (0, -0.13, z + 0.14), w, 0.0, PINE, sides=4)
	p.seg((0, -0.13, 0.66), (0, -0.13, 0.72), 0.025, 0.025, WOOD, sides=4)
	p.blob((0.05, 0.03, 0.05), (0.12, -0.14, 0.72), EMBER, segs=(5, 3), glow=2.4)           # an ember at its foot
	return p.build()


def smokeweave_sash():
	p = Prop("smokeweave_sash", 1101)
	u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
	n = u.cross(v)
	R, c = 0.55, Vector((0, 0.1, 0.72))
	N = 28
	for band, (h0, h1, sw) in enumerate(((-0.16, -0.06, ASH), (-0.06, -0.035, EMBER), (-0.035, 0.035, STONE_DARK), (0.035, 0.06, EMBER),
										  (0.06, 0.16, ASH))):
		for k in range(N):                                                                # a broad banded sash, looped
			a0, a1 = k * math.tau / N, (k + 1) * math.tau / N
			p0, p1 = c + u * math.cos(a0) * R + v * math.sin(a0) * R, c + u * math.cos(a1) * R + v * math.sin(a1) * R
			quad = [p0 + n * h0, p1 + n * h0, p1 + n * h1, p0 + n * h1]
			p.poly([tuple(q) for q in quad], [(0, 1, 2, 3)], sw, grad=(0.2, 0.7))
	for h in (-0.048, 0.048):                                                             # ember threads woven through
		_oval(p, tuple(c + n * h), u, v, R + 0.006, R + 0.006, 0.012, EMBER, n=N, glow=2.0)
	k0 = c + v * -R                                                                        # knotted at the front
	p.blob((0.3, 0.2, 0.26), tuple(k0 + Vector((0.05, -0.06, 0))), ASH, segs=(8, 6), grad=(0.2, 0.8))
	for k, (dx, ln) in enumerate(((-0.12, 0.6), (0.14, 0.5))):                             # two tails trailing smoke
		top = k0 + Vector((dx * 0.5, -0.08, -0.05))
		end = top + Vector((dx, -0.04, -ln))
		w = Vector((0.1, 0, 0))
		p.poly([tuple(top - w), tuple(top + w), tuple(end + w * 1.2), tuple(end - w * 1.2)], [(0, 1, 2, 3)], STONE_DARK if k else ASH, grad=(0.2, 0.9))
		p.seg(tuple(end - w * 1.2 + Vector((0, -0.01, 0.02))), tuple(end + w * 1.2 + Vector((0, -0.01, 0.02))), 0.02, 0.02, EMBER, sides=4, glow=1.8)
		for j in range(3):
			p.blob((0.12 + j * 0.05,) * 3, tuple(end + Vector((0.05 * j, -0.02, -0.1 - j * 0.12))), ASH, segs=(6, 4), grad=(0.0, 0.5))
	return p.build()


def cackleflame_scepter():
	p = Prop("cackleflame_scepter", 1103)
	p.seg((-0.5, 0, -0.3), (0.1, 0, 0.6), 0.05, 0.06, STONE_DARK, sides=8)                   # a blackened iron rod
	for k in range(3):
		t = 0.25 + k * 0.25
		p.seg((-0.5 + 0.6 * t, 0, -0.3 + 0.9 * t), (-0.48 + 0.6 * t, 0, -0.27 + 0.9 * t), 0.075, 0.075, GOLD, sides=8)
	c = (0.2, 0, 0.8)                                                                      # topped with a grinning imp's head
	p.blob((0.5, 0.44, 0.46), c, CLOTH_RED, segs=(12, 8), grad=(0.0, 0.8))
	for sx in (-1, 1):
		p.seg((c[0] + sx * 0.14, 0, c[2] + 0.16), (c[0] + sx * 0.3, -0.02, c[2] + 0.38), 0.06, 0.0, STONE_DARK, sides=5)   # horns
		p.blob((0.1, 0.05, 0.08), (c[0] + sx * 0.1, -0.21, c[2] + 0.06), FLAME, segs=(6, 4), glow=2.8)                    # eyes
		p.seg((c[0] + sx * 0.22, 0, c[2]), (c[0] + sx * 0.34, 0, c[2] + 0.08), 0.06, 0.0, CLOTH_RED, sides=4)               # ears
	grin = [(c[0] - 0.13, -0.2, c[2] - 0.06), (c[0] - 0.05, -0.23, c[2] - 0.12), (c[0] + 0.05, -0.23, c[2] - 0.12), (c[0] + 0.13, -0.2, c[2] - 0.06)]
	_seam(p, grin, GOLD, r=0.022, glow=2.2)
	for k in range(3):                                                                    # flames for hair
		x = c[0] - 0.08 + k * 0.08
		p.seg((x, 0.02, c[2] + 0.18), (x + 0.02, 0.02, c[2] + 0.42 + (k % 2) * 0.1), 0.07, 0.0, FLAME, sides=5, glow=2.6)
	return p.build()


def firefeather_cap():
	p = Prop("firefeather_cap", 1105)
	for z0, z1, r0, r1 in ((0.0, 0.2, 0.42, 0.42), (0.2, 0.42, 0.42, 0.34), (0.42, 0.56, 0.34, 0.16), (0.56, 0.6, 0.16, 0.0)):
		p.seg((0, 0, z0), (0, 0, z1), r0, r1, CRIMSON, sides=16, grad=(0.1, 0.9))           # a crimson felt cap
	p.seg((0, 0, 0.0), (0, 0, 0.14), 0.44, 0.44, GOLD, sides=16)                             # a gold band
	for k, (tip, sw) in enumerate((((0.55, 1.3), ORANGE), ((0.2, 1.45), FLAME), ((0.75, 1.05), ORANGE))):   # firebird feathers in it
		_vane(p, (0.28, -0.1 - k * 0.03, 0.2), (tip[0], -0.1 - k * 0.03, tip[1]), 0.14, sw, tip_swatch=EMBER, glow=1.6)
	p.blob((0.14, 0.08, 0.14), (0.28, -0.4, 0.14), FLAME, segs=(8, 5), glow=2.4)              # pinned with a fire opal
	return p.build()


def ring_of_the_phoenix():
	p = Prop("ring_of_the_phoenix", 1107)
	_ring(p, GOLD)
	p.seg((0, 0.06, 0.86), (0, -0.1, 0.86), 0.18, 0.18, GOLD, sides=10)
	p.blob((0.28, 0.16, 0.3), (0, -0.14, 0.9), FLAME, segs=(10, 6), glow=2.8)                 # a stone of living fire
	for sx in (-1, 1):                                                                    # gold wings folded round it
		_vane(p, (sx * 0.12, -0.08, 0.84), (sx * 0.62, -0.08, 1.08), 0.13, GOLD, tip_swatch=EMBER)
	p.seg((0, -0.16, 1.02), (0.02, -0.16, 1.3), 0.07, 0.0, FLAME, sides=5, glow=2.6)
	return p.build()


def glasswrights_lenses():
	p = Prop("glasswrights_lenses", 1109)
	_oval(p, (0, 0.12, 0.5), (1, 0, 0), (0, 0.9, 0.3), 0.52, 0.5, 0.05, WOOD, n=22)          # a leather strap
	for sx in (-1, 1):                                                                    # two brass-rimmed lenses
		x = sx * 0.22
		p.seg((x, -0.3, 0.45), (x, -0.46, 0.45), 0.18, 0.17, GOLD, sides=14, grad=(0.0, 0.6))
		p.seg((x, -0.46, 0.45), (x, -0.48, 0.45), 0.135, 0.135, AQUA, sides=14, grad=(0.0, 0.4))
		p.blob((0.07, 0.03, 0.05), (x - 0.05, -0.49, 0.5), CLOTH_WHITE, segs=(6, 4), glow=2.0)
	p.seg((-0.06, -0.42, 0.47), (0.06, -0.42, 0.47), 0.04, 0.04, GOLD, sides=6)                # the bridge
	c = (0.36, -0.58, 0.8)                                                                 # a loupe swung up on a hinge
	p.seg((0.36, -0.44, 0.58), c, 0.025, 0.025, GOLD, sides=5)
	p.seg((c[0], c[1] + 0.03, c[2]), (c[0], c[1] - 0.05, c[2] + 0.03), 0.12, 0.12, GOLD, sides=12)
	p.seg((c[0], c[1] - 0.05, c[2] + 0.03), (c[0], c[1] - 0.06, c[2] + 0.034), 0.09, 0.09, VIOLET, sides=12)
	return p.build()


def heart_of_the_colossus():
	p = Prop("heart_of_the_colossus", 1111)
	_cord(p, 0.42, 0.84, STONE_DARK)
	p.seg((0, -0.3, 0.52), (0, -0.3, 0.22), 0.0, 0.34, OBSIDIAN, sides=6, grad=(0.0, 0.4))    # a teardrop of black glass
	p.seg((0, -0.3, 0.22), (0, -0.3, -0.36), 0.34, 0.0, OBSIDIAN, sides=6, grad=(0.0, 0.4))
	p.blob((0.3, 0.16, 0.38), (0, -0.56, 0.16), EMBER, segs=(10, 6), glow=2.6)                # molten at its heart
	p.blob((0.12, 0.06, 0.14), (-0.03, -0.64, 0.2), FLAME, segs=(6, 4), glow=3.0)
	for sx in (-1, 1):                                                                    # iron claws holding it
		p.seg((sx * 0.08, -0.36, 0.52), (sx * 0.3, -0.5, 0.26), 0.035, 0.015, STONE_DARK, sides=5)
	p.seg((0, -0.3, 0.52), (0, -0.3, 0.7), 0.05, 0.05, STONE_DARK, sides=6)
	return p.build()


def obsidian_scale_leggings():
	p = Prop("obsidian_scale_leggings", 1113)
	_trousers(p, STONE_DARK, WOOD, leg_r=0.21)
	for x in (-1, 1):                                                                     # shingled black glass scales
		for row, z in enumerate((0.66, 0.54, 0.42, 0.3, 0.18)):
			for k in range(2):
				cx = x * 0.21 + (k - 0.5) * 0.15 + (0.07 if row % 2 else 0.0) * x
				p.blob((0.16, 0.05, 0.14), (cx, -0.21, z), OBSIDIAN, segs=(6, 4), grad=(0.0, 0.4))
				p.seg((cx - 0.06, -0.235, z - 0.05), (cx + 0.06, -0.235, z - 0.05), 0.01, 0.01, VIOLET, sides=4, glow=1.6)
	p.box((0.1, 0.06, 0.08), (0, -0.15, 1.0), STONE_LIGHT)
	return p.build()


def eye_of_vitrax():
	p = Prop("eye_of_vitrax", 1115)
	_ring(p, OBSIDIAN)
	for sx in (-1, 1):                                                                    # glass claws
		p.seg((sx * 0.14, 0, 0.76), (sx * 0.2, -0.06, 1.02), 0.04, 0.0, OBSIDIAN, sides=4)
	p.blob((0.36, 0.26, 0.36), (0, -0.04, 0.92), CLOTH_WHITE, segs=(12, 8), grad=(0.0, 0.5))   # a glass eye for a stone
	p.blob((0.24, 0.1, 0.24), (0, -0.14, 0.92), VIOLET, segs=(10, 6), glow=1.6)
	p.blob((0.05, 0.05, 0.2), (0, -0.19, 0.92), OBSIDIAN, segs=(6, 4))
	return p.build()


def glassweb_gloves():
	p, fr = _glove_pair("glassweb_gloves", 1117, STONE_LIGHT, OBSIDIAN, AQUA, grad=(0.0, 0.6))
	for f in fr:                                                                          # a web of glassy thread over the back
		c = (0, -0.13, 0.52)
		for a in (-70, -35, 0, 35, 70):
			r = math.radians(a)
			p.seg(f(*c), f(math.sin(r) * 0.2, -0.13, 0.52 + math.cos(r) * 0.2), 0.011, 0.011, AQUA, sides=4, glow=1.6)
		for rr in (0.08, 0.15):
			pts = [f(math.sin(math.radians(a)) * rr, -0.135, 0.52 + math.cos(math.radians(a)) * rr) for a in (-70, -35, 0, 35, 70)]
			_seam(p, pts, AQUA, r=0.009, glow=1.6)
		p.blob((0.07, 0.05, 0.07), f(*c), CLOTH_WHITE, segs=(6, 4), glow=2.0)
	return p.build()


def shardmothers_fang():
	p = Prop("shardmothers_fang", 1119)
	pts = [(-0.05, 0, 0.3), (0.18, 0, 0.62), (0.36, 0, 0.92), (0.42, 0, 1.2)]                  # a long curved fang of glass
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.14 - i * 0.04, 0.1 - i * 0.04 if i < 2 else 0.0, AQUA, sides=5, grad=(0.0, 0.45))
	for a, b in zip(pts[:3], pts[1:3]):                                                   # a bright core down it
		p.seg((a[0] + 0.02, -0.1, a[2]), (b[0] + 0.02, -0.08, b[2]), 0.02, 0.015, CLOTH_WHITE, sides=4, glow=1.8)
	for k in range(4):                                                                    # black glass shards for a guard
		a = math.radians(-60 + k * 40)
		p.seg((-0.05, 0, 0.3), (-0.05 + math.cos(a) * 0.26, -0.02, 0.3 + math.sin(a) * 0.16 - 0.06), 0.06, 0.0, OBSIDIAN, sides=4)
	p.seg((-0.05, 0, 0.3), (-0.3, 0, -0.05), 0.065, 0.06, OBSIDIAN, sides=6)                  # a grip wound with glass silk
	for k in range(4):
		t = 0.15 + k * 0.22
		p.seg((-0.05 - 0.25 * t, 0, 0.3 - 0.35 * t), (-0.07 - 0.25 * t, 0, 0.27 - 0.35 * t), 0.075, 0.075, CLOTH_WHITE, sides=6)
	p.rock((0.16, 0.14, 0.16), (-0.33, 0, -0.09), OBSIDIAN, jitter=0.04)
	p.blob((0.06, 0.04, 0.06), (0.44, -0.05, 1.1), VIOLET, segs=(5, 3), glow=2.0)
	return p.build()


def glassbound_greaves():
	p = Prop("glassbound_greaves", 1121)
	_trousers(p, OBSIDIAN, STONE_DARK, leg_r=0.21, flare=0.03)
	for x in (-1, 1):
		for z in (0.62, 0.4, 0.16):                                                       # old steel bands under the glass
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.05), 0.235, 0.24, STONE_LIGHT, sides=10, grad=(0.0, 0.5))
		p.blob((0.22, 0.12, 0.2), (x * 0.21, -0.18, 0.3), STONE_LIGHT, segs=(8, 6))          # knee cop
		for k, (dx, z, h, a) in enumerate(((0.08, 0.5, 0.26, 35), (-0.1, 0.28, 0.2, -30), (0.04, 0.08, 0.18, 60))):   # glass shards grown through
			r = math.radians(a * x)
			base = (x * 0.21 + dx, -0.18, z)
			p.seg(base, (base[0] + math.sin(r) * h, -0.3, z + math.cos(r) * h), 0.07, 0.0, OBSIDIAN, sides=4, grad=(0.0, 0.4))
			p.blob((0.04, 0.03, 0.04), (base[0], -0.24, z + 0.02), VIOLET, segs=(5, 3), glow=2.0)
	p.box((0.74, 0.28, 0.08), (0, 0, 1.05), STONE_DARK)
	return p.build()


def aldrics_glass_blade():
	p = Prop("aldrics_glass_blade", 1123)
	org, rot = (-0.55, -0.42), 48
	up = [(0.32, 0.09), (0.8, 0.095), (1.2, 0.09), (1.45, 0.05)]
	tip = (1.62, 0.0)
	outline = up + [tip] + [(x, -z) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.035, 0.035, OBSIDIAN, grad=(0.0, 0.4))             # a knight's blade turned to black glass
	crack = _rot2([(0.4, 0.02), (0.6, -0.04), (0.78, 0.05), (1.0, -0.03), (1.22, 0.03), (1.45, 0.0)], rot, org)
	_seam(p, [(a[0], -0.045, a[1]) for a in crack], VIOLET, r=0.013, glow=2.0)               # a pale crack of light down it
	for sgn in (1, -1):
		e = _rot2([(x, sgn * (z - 0.01)) for x, z in up] + [(tip[0] - 0.01, 0.0)], rot, org)
		for a, b in zip(e, e[1:]):
			p.seg((a[0], -0.042, a[1]), (b[0], -0.042, b[1]), 0.009, 0.009, CLOTH_WHITE, sides=4, glow=0.6)
	g = _rot2([(0.3, -0.36), (0.3, 0.36)], rot, org)
	p.seg((g[0][0], 0, g[0][1]), (g[1][0], 0, g[1][1]), 0.05, 0.05, STONE_LIGHT, sides=6)      # still its silver crossguard
	for end in g:
		p.seg((end[0], 0, end[1]), (end[0] + 0.02, 0, end[1] + 0.14), 0.05, 0.0, STONE_LIGHT, sides=5)
	h = _rot2([(0.26, 0.0), (-0.12, 0.0), (-0.2, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.055, RUNE, sides=6)          # a blue-wrapped grip
	p.blob((0.15, 0.15, 0.15), (h[2][0], 0, h[2][1]), STONE_LIGHT, segs=(8, 6))
	p.blob((0.07, 0.05, 0.07), (h[2][0], -0.08, h[2][1]), RUNE, segs=(6, 4), glow=1.6)
	return p.build()


# ---------------------------------------------------------------- Dawnwatch, Mirror Flats, the Silted Reach and Tidemouth
# Dawnwatch is the dawn god's snowbound fortress (gold suns on pale steel, ice
# blue), Mirror Flats salt-white and mirror-silver, the Silted Reach mud brown
# and river green, Tidemouth sea blue, whalebone and storm light.


def _line(p, pts, r0, r1, sw, sides=6, grad=(0.1, 0.8), glow=0.0):
	"""A tapering tube along pts, r0 at the first point to r1 at the last."""
	n = len(pts) - 1
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n, sw, sides=sides, grad=grad, glow=glow)


def _sun(p, c, r, sw=GOLD, rays=12, ray=0.5, glow=0.6, y=None):
	"""A sun disc facing the camera with pointed rays, r its disc radius, ray the rays' length over r."""
	x, cy, z = c
	p.seg((x, cy + 0.03, z), (x, cy - 0.03, z), r, r, sw, sides=16, grad=(0.0, 0.6), glow=glow)
	for k in range(rays):
		a = k * math.tau / rays
		ln = r * (1 + ray * (1.0 if k % 2 == 0 else 0.6))
		p.seg((x + math.cos(a) * r * 0.9, cy, z + math.sin(a) * r * 0.9), (x + math.cos(a) * ln, cy, z + math.sin(a) * ln), r * 0.22, 0.0, sw,
			  sides=4, glow=glow)


def _belt(p, band, edge, buckle, R=0.58, h=0.2, grad=(0.2, 0.8), stripes=()):
	"""A belt coiled in a ring, its buckle toward the camera. Returns the buckle's
	center, the outward direction there and the belt's tangent."""
	c, N = Vector((0, 0.1, 0.5)), 30
	for k in range(N):
		a0, a1 = k * math.tau / N, (k + 1) * math.tau / N
		p0 = c + Vector((math.cos(a0) * R, math.sin(a0) * R, 0))
		p1 = c + Vector((math.cos(a1) * R, math.sin(a1) * R, 0))
		dz = Vector((0, 0, h / 2))
		p.poly([tuple(p0 - dz), tuple(p1 - dz), tuple(p1 + dz), tuple(p0 + dz)], [(0, 1, 2, 3)], band, grad=grad)
	u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
	for z in (-h / 2, h / 2):
		_oval(p, tuple(c + Vector((0, 0, z))), u, v, R + 0.005, R + 0.005, 0.022, edge, n=N)
	for z, sw, glow in stripes:
		_oval(p, tuple(c + Vector((0, 0, z))), u, v, R + 0.01, R + 0.01, 0.018, sw, n=N, glow=glow)
	af = math.radians(-61)
	out = Vector((math.cos(af), math.sin(af), 0))
	tan = Vector((-math.sin(af), math.cos(af), 0))
	f = c + out * (R + 0.03)
	rot = (0, 0, math.degrees(af) + 90)
	p.box((0.3, 0.07, h * 1.5), tuple(f), buckle, rot=rot, grad=(0.0, 0.6))
	p.box((0.18, 0.08, h * 0.9), tuple(f + out * 0.01), band, rot=rot, grad=grad)
	p.seg(tuple(f + out * 0.05 - tan * 0.02 + Vector((0, 0, 0.0))), tuple(f + out * 0.05 + tan * 0.1), 0.025, 0.025, buckle, sides=5)   # the tongue
	return f, out, tan


def _scallop(p, c, s, sw, rib, eyes=None, glow=0.0):
	"""A scallop shell standing in the picture plane, hinge at c, fanning up."""
	x, y, z = c
	fan = [(x, z)] + [(x + math.cos(math.radians(a)) * s, z + math.sin(math.radians(a)) * s * 1.05) for a in range(10, 171, 16)]
	_slab(p, fan, y - 0.03, y + 0.03, sw, grad=(0.0, 0.8))
	for a in range(18, 165, 16):
		r = math.radians(a)
		p.seg((x, y - 0.035, z), (x + math.cos(r) * s * 0.97, y - 0.035, z + math.sin(r) * s * 1.02), 0.02 * s / 0.5, 0.035 * s / 0.5, rib, sides=4)
	for a in range(10, 171, 16):                                                        # a scalloped rim
		r = math.radians(a)
		p.blob((0.1 * s, 0.05, 0.08 * s), (x + math.cos(r) * s, y - 0.01, z + math.sin(r) * s * 1.05), rib, segs=(6, 4))
	p.box((0.34 * s, 0.07, 0.14 * s), (x, y - 0.01, z + 0.02), sw)                         # the hinge ears
	if eyes:
		for sx in (-1, 1):
			p.blob((0.2 * s, 0.05, 0.14 * s), (x + sx * 0.3 * s, y - 0.06, z + 0.55 * s), eyes, segs=(8, 5), glow=glow)


def _twist_ring(p, c, u, v, R, r, sws, turns=7, gap=0.0, n=40):
	"""Two strands twisted round a ring in the plane of u and v, an opening of `gap` radians at the top."""
	c, u, v = Vector(c), Vector(u), Vector(v)
	w = u.cross(v)
	for strand, sw in enumerate(sws):
		pts = []
		for k in range(n + 1):
			a = math.pi / 2 + gap / 2 + k * (math.tau - gap) / n
			radial = u * math.cos(a) + v * math.sin(a)
			phi = a * turns + strand * math.pi
			pts.append(tuple(c + radial * (R + math.cos(phi) * r) + w * math.sin(phi) * r))
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, r * 1.05, r * 1.05, sw, sides=6, grad=(0.0, 0.6))


def _crystal(p, base, tip, r, sw=CLOTH_WHITE, glow=0.3):
	"""A four-sided pointed crystal."""
	base, tip = Vector(base), Vector(tip)
	mid = base + (tip - base) * 0.7
	p.seg(tuple(base), tuple(mid), r, r, sw, sides=4, grad=(0.0, 0.5), glow=glow)
	p.seg(tuple(mid), tuple(tip), r, 0.0, sw, sides=4, grad=(0.0, 0.4), glow=glow)


def _zap(p, pts, r=0.03, sw=CLOTH_WHITE, glow=3.0):
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, r, r * 0.8, sw, sides=4, glow=glow)


# Dawnwatch

def stonebrow_tusk():
	p = Prop("stonebrow_tusk", 1201)
	pts = [(-0.12, 0, 0.05), (0.08, 0, 0.42), (0.3, 0, 0.78), (0.3, 0, 1.08), (0.16, 0, 1.3)]
	_line(p, pts, 0.28, 0.02, BONE, sides=9, grad=(0.0, 0.8))                                # a thick, blunt ogre's tusk
	for z, x in ((0.3, 0.02), (0.6, 0.2)):                                                # gray streaks, like the stone of their brows
		p.seg((x - 0.1, -0.21, z), (x + 0.06, -0.19, z + 0.24), 0.035, 0.02, STONE_WARM, sides=4)
	for k in range(3):                                                                    # tally notches cut round it
		z = 0.18 + k * 0.1
		p.seg((-0.05 + k * 0.035, 0, z), (-0.04 + k * 0.035, 0, z + 0.03), 0.27 - k * 0.012, 0.27 - k * 0.012, WOOD, sides=9)
	p.rock((0.62, 0.5, 0.34), (-0.16, 0.02, -0.06), STONE_WARM, jitter=0.07)                  # torn out with a chunk of gray hide
	p.rock((0.3, 0.3, 0.2), (0.12, 0.08, -0.1), STONE_DARK, jitter=0.05)
	return p.build()


def roc_feather():
	p = Prop("roc_feather", 1203)
	_vane(p, (-0.6, 0, -0.15), (0.55, 0, 1.4), 0.27, AMBER, bars=(0.22, 0.38, 0.54, 0.7), tip_swatch=WOOD)   # a huge barred golden feather
	for k in range(4):                                                                    # down at the base of the quill
		p.blob((0.14, 0.1, 0.12), (-0.62 + k * 0.07, -0.02, -0.08 + (k % 2) * 0.08), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.4), jitter=0.02)
	return p.build()


def wyvern_barb():
	p = Prop("wyvern_barb", 1205)
	_line(p, [(-0.75, 0, -0.15), (-0.5, 0, 0.1), (-0.22, 0, 0.26), (0.02, 0, 0.4)], 0.15, 0.09, PINE, sides=8, grad=(0.1, 0.9))   # a length of tail
	for k in range(3):                                                                    # spines down its back
		x, z = -0.6 + k * 0.25, 0.06 + k * 0.12
		p.seg((x, 0, z + 0.1), (x + 0.02, 0, z + 0.28), 0.06, 0.0, BONE, sides=4)
	org, rot = (0.0, 0.4), 38
	spade = [(0.0, 0.08), (0.2, 0.34), (0.1, 0.5), (0.5, 0.36), (0.9, 0.12), (1.12, 0.0), (0.9, -0.12), (0.5, -0.36), (0.1, -0.5), (0.2, -0.34),
			 (0.0, -0.08)]                                                                 # a barbed, spade-shaped sting
	_slab(p, _rot2(spade, rot, org), -0.06, 0.06, CRIMSON, grad=(0.0, 0.9))
	mid = _rot2([(0.02, 0.0), (1.02, 0.0)], rot, org)
	p.seg((mid[0][0], -0.07, mid[0][1]), (mid[1][0], -0.07, mid[1][1]), 0.04, 0.01, STONE_DARK, sides=4)   # its dark midrib
	tip = _rot2([(1.18, -0.06)], rot, org)[0]
	p.blob((0.1, 0.08, 0.13), (tip[0], -0.04, tip[1] - 0.06), LEAF, segs=(6, 4), glow=2.2)    # venom beading at the point
	return p.build()


def frozen_breath():
	p = Prop("frozen_breath", 1207)
	p.blob((0.34, 0.34, 0.34), (0, -0.05, 0.62), SKY, segs=(12, 8), glow=2.4)                   # a cold blue heart of breath
	for k in range(18):                                                                   # swirling frost round it
		t = k / 17
		a = t * math.tau * 1.4
		r = 0.62 - t * 0.35
		s = 0.44 - t * 0.2
		p.blob((s, s * 0.8, s * 0.8), (math.cos(a) * r, math.sin(a) * r * 0.5, 0.35 + t * 0.62), CLOTH_WHITE if k % 3 else SKY,
			   segs=(8, 5), grad=(0.0, 0.4), glow=0.8 if k % 3 else 1.6)
	for k in range(5):                                                                    # ice crystals grown out of it
		a = math.radians(200 + k * 35)
		b = (math.cos(a) * 0.2, -0.1, 0.35 + math.sin(a) * 0.1)
		_crystal(p, b, (math.cos(a) * 0.62, -0.18, 0.2 + math.sin(a) * 0.35), 0.06, STONE_LIGHT if k % 2 else CLOTH_WHITE, glow=0.6)
	for (x, z) in ((0.62, 1.05), (-0.55, 1.0), (0.1, 1.2)):                                # snow motes
		p.blob((0.06, 0.06, 0.06), (x, -0.2, z), CLOTH_WHITE, segs=(5, 3), glow=2.0)
	return p.build()


def sentinels_sunbadge():
	p = Prop("sentinels_sunbadge", 1209)
	outline = [(-0.46, 1.0), (0.46, 1.0), (0.46, 0.52), (0.32, 0.22), (0.0, 0.0), (-0.32, 0.22), (-0.46, 0.52)]
	_slab(p, outline, -0.04, 0.04, STONE_LIGHT, grad=(0.0, 0.5))                             # a steel badge shaped like a shield
	for a, b in zip(outline, outline[1:] + outline[:1]):
		p.seg((a[0], -0.05, a[1]), (b[0], -0.05, b[1]), 0.04, 0.04, GOLD, sides=5)
	_sun(p, (0, -0.07, 0.56), 0.14, GOLD, rays=12, ray=0.9, glow=0.7)                        # the dawn god's sun on it
	p.blob((0.1, 0.05, 0.1), (0, -0.11, 0.56), DAWN, segs=(6, 4), glow=1.6)
	p.seg((0.18, -0.07, 0.9), (0.36, -0.07, 0.62), 0.018, 0.012, STONE_DARK, sides=4)          # a deep scratch across it
	p.seg((0.36, -0.07, 0.62), (0.3, -0.07, 0.4), 0.014, 0.008, STONE_DARK, sides=4)
	for sx in (-1, 1):                                                                    # a torn red ribbon it hung from
		p.poly([(sx * 0.06, -0.06, 1.0), (sx * 0.2, -0.06, 1.0), (sx * 0.34, -0.1, 1.28), (sx * 0.2, -0.1, 1.3)], [(0, 1, 2, 3)], CLOTH_RED)
	return p.build()


# Mirror Flats

def mirror_shard():
	p = Prop("mirror_shard", 1211)
	shard = [(-0.36, 0.0), (0.06, 0.1), (0.42, 0.36), (0.26, 0.86), (0.06, 1.34), (-0.12, 0.84), (-0.42, 0.46)]
	_slab(p, shard, 0.0, 0.05, STONE_LIGHT, grad=(0.0, 0.4))                                # a jagged shard of mirror
	inner = [(-0.3, 0.05), (0.06, 0.14), (0.36, 0.38), (0.22, 0.84), (0.06, 1.24), (-0.1, 0.82), (-0.36, 0.47)]
	_slab(p, inner, -0.02, 0.0, SKY, grad=(0.0, 0.9))                                         # the sky caught in it
	p.poly([(-0.34, -0.03, 0.36), (-0.26, -0.03, 0.54), (0.36, -0.03, 0.46), (0.38, -0.03, 0.38)], [(0, 1, 2, 3)], CLOTH_WHITE)   # a white horizon of salt
	for a, b in zip(shard, shard[1:] + shard[:1]):                                        # its dark silvered edge
		p.seg((a[0], -0.01, a[1]), (b[0], -0.01, b[1]), 0.022, 0.022, STONE_DARK, sides=4)
	c = (0.06, -0.06, 0.94)                                                               # a bright glint
	for dx, dz in ((0.2, 0), (0, 0.24), (0.12, 0.12), (0.12, -0.12)):
		p.seg((c[0] - dx, c[1], c[2] - dz), (c[0] + dx, c[1], c[2] + dz), 0.02, 0.0, CLOTH_WHITE, sides=4, glow=3.0)
	return p.build()


def salt_crab_claw():
	p = Prop("salt_crab_claw", 1213)
	p.blob((0.62, 0.42, 0.46), (-0.3, 0, 0.36), BONE, segs=(12, 8), grad=(0.1, 0.9))           # a pale crab's claw
	_line(p, [(-0.06, 0, 0.46), (0.3, 0, 0.62), (0.58, 0, 0.66), (0.72, 0, 0.54)], 0.18, 0.02, BONE, sides=8, grad=(0.1, 0.9))
	_line(p, [(-0.06, 0, 0.26), (0.28, 0, 0.14), (0.52, 0, 0.2), (0.64, 0, 0.36)], 0.14, 0.02, BONE, sides=8, grad=(0.1, 0.9))
	for tip in ((0.72, 0, 0.54), (0.64, 0, 0.36)):                                        # dark tips
		p.blob((0.08, 0.08, 0.08), tip, STONE_DARK, segs=(6, 4))
	p.seg((-0.6, 0, 0.3), (-0.76, 0, 0.22), 0.14, 0.12, PINK, sides=8)
	rng = p.rng
	for k in range(9):                                                                    # crusted with salt crystals
		x, z = rng.uniform(-0.55, 0.3), rng.uniform(0.2, 0.62)
		p.box((0.1, 0.1, 0.1), (x, -0.2 - rng.uniform(0, 0.06), z), CLOTH_WHITE,
			  rot=(rng.uniform(0, 90), rng.uniform(0, 90), rng.uniform(0, 90)), grad=(0.0, 0.3), glow=0.3)
	return p.build()


def nomad_veil():
	p = Prop("nomad_veil", 1215)
	drape = [(-0.42, 1.1), (0.42, 1.1), (0.56, 0.6), (0.62, 0.12), (0.3, 0.0), (0.0, 0.06), (-0.3, 0.0), (-0.62, 0.12), (-0.56, 0.6)]
	_slab(p, drape, 0.0, 0.04, RUNE, grad=(0.3, 1.0))                                          # an indigo veil, hanging
	for x in (-0.3, -0.1, 0.12, 0.32):                                                    # its folds
		p.seg((x * 0.8, -0.02, 1.04), (x * 1.2, -0.02, 0.1), 0.03, 0.05, WATER, sides=4, grad=(0.5, 1.0))
	p.seg((-0.45, -0.03, 1.08), (0.45, -0.03, 1.08), 0.05, 0.05, AMBER, sides=6)            # a sand-colored band
	hem = [(0.62, 0.12), (0.3, 0.0), (0.0, 0.06), (-0.3, 0.0), (-0.62, 0.12)]
	for k in range(9):                                                                    # a fringe of little gold coins
		t = k / 8 * (len(hem) - 1)
		i = min(int(t), len(hem) - 2)
		f = t - i
		x = hem[i][0] + (hem[i + 1][0] - hem[i][0]) * f
		z = hem[i][1] + (hem[i + 1][1] - hem[i][1]) * f
		p.seg((x, -0.02, z), (x, -0.02, z - 0.08), 0.01, 0.01, GOLD, sides=4)
		p.seg((x, 0.0, z - 0.14), (x, -0.04, z - 0.14), 0.07, 0.07, GOLD, sides=10, glow=0.5)
	for sx in (-1, 1):                                                                    # the eye slit's edge
		p.seg((sx * 0.05, -0.03, 0.82), (sx * 0.4, -0.03, 0.84), 0.025, 0.025, AMBER, sides=4)
	return p.build()


def wader_plume():
	p = Prop("wader_plume", 1217)
	_vane(p, (-0.2, 0.06, -0.1), (-0.5, 0.06, 1.2), 0.12, CLOTH_WHITE, tip_swatch=STONE_DARK)   # a thin white plume behind
	_vane(p, (-0.25, 0, -0.1), (0.4, 0, 1.4), 0.2, PINK, tip_swatch=DAWN)                     # a long pink wader's plume
	p.seg((-0.3, -0.04, -0.12), (-0.18, -0.04, 0.08), 0.05, 0.05, GOLD, sides=6)              # bound with gold thread
	return p.build()


# the Silted Reach

def whisker_barbel():
	p = Prop("whisker_barbel", 1219)
	pts = []
	for k in range(16):                                                                   # a long fleshy barbel, curling
		t = k / 15
		a = t * 4.2
		r = 0.7 * (1 - t) + 0.12
		pts.append((-0.1 + math.cos(a) * r * 0.9 + t * 0.2, 0, 0.55 + math.sin(a) * r * 0.7))
	_line(p, pts, 0.15, 0.03, WOOD_GRAY, sides=8, grad=(0.1, 0.8))
	_line(p, [(-0.6, 0.1, 0.35), (-0.8, 0.1, 0.1), (-0.72, 0.1, -0.1), (-0.5, 0.1, -0.18)], 0.08, 0.02, WOOD_GRAY, sides=6)   # a shorter one
	p.blob((0.3, 0.26, 0.24), (-0.6, 0.02, 0.42), PINK, segs=(8, 6), grad=(0.2, 0.9))          # where they were cut from the lip
	for k in range(5):                                                                    # a wet sheen
		c = pts[3 + k * 2]
		p.blob((0.035, 0.03, 0.035), (c[0], -0.1, c[2] + 0.04), CLOTH_WHITE, segs=(5, 3), glow=1.6)
	return p.build()


def hippo_tusk():
	p = Prop("hippo_tusk", 1221)
	pts = [(-0.55, 0, 0.12), (-0.15, 0, 0.1), (0.25, 0, 0.3), (0.5, 0, 0.72), (0.5, 0, 1.08)]
	_line(p, pts, 0.3, 0.1, BONE, sides=10, grad=(0.0, 0.7))                                 # a great curved ivory tusk
	p.seg((0.5, 0, 1.08), (0.44, -0.02, 1.2), 0.1, 0.04, CLOTH_WHITE, sides=10)               # its worn chisel tip
	p.seg((-0.1, -0.2, 0.2), (0.3, -0.2, 0.42), 0.03, 0.02, AMBER, sides=4)                 # a yellowed streak
	p.rock((0.5, 0.52, 0.42), (-0.6, 0.02, 0.1), PINK, jitter=0.06)                           # a lump of pink gum at the root
	p.rock((0.3, 0.36, 0.3), (-0.72, 0.06, -0.04), STONE_WARM, jitter=0.05)
	return p.build()


def mud_charm():
	p = Prop("mud_charm", 1223)
	p.seg((0, 0.05, 0.55), (0, -0.07, 0.55), 0.5, 0.46, CLAY, sides=14, grad=(0.1, 0.9), jitter=0.03)   # a disc of dried river mud
	pts = []
	for k in range(22):                                                                   # a spiral pressed into it
		t = k / 21
		a = t * math.tau * 2.2
		pts.append((math.cos(a) * 0.36 * t, -0.08, 0.55 + math.sin(a) * 0.36 * t))
	_line(p, pts, 0.02, 0.03, WOOD, sides=4)
	p.blob((0.2, 0.08, 0.16), (0.22, -0.1, 0.28), BONE, segs=(8, 5), grad=(0.0, 0.6))        # a river shell pressed in
	for k in range(3):                                                                    # cracks from drying
		a = math.radians(60 + k * 110)
		p.seg((math.cos(a) * 0.3, -0.075, 0.55 + math.sin(a) * 0.3), (math.cos(a) * 0.48, -0.075, 0.55 + math.sin(a) * 0.46), 0.015, 0.01,
			  STONE_DARK, sides=4)
	_loop(p, (0, 0, 1.08), 0.08, False, 0.022, LEAF, n=10)                                  # a reed loop to hang it by
	for sx in (-1, 1):                                                                    # reed tassels
		_line(p, [(sx * 0.4, -0.02, 0.3), (sx * 0.5, -0.04, 0.0), (sx * 0.46, -0.04, -0.2)], 0.025, 0.012, LEAF, sides=4)
	return p.build()


def serpent_scale():
	p = Prop("serpent_scale", 1225)
	for dx, dy, dz, s in ((-0.34, 0.14, 0.24, 0.7), (0.08, 0.0, 0.0, 1.0)):              # a smaller scale behind a big one
		sc = [(dx + x * s, dz + z * s) for x, z in ((0.0, 0.0), (0.34, 0.3), (0.42, 0.7), (0.24, 1.1), (0.0, 1.3), (-0.24, 1.1), (-0.42, 0.7),
												   (-0.34, 0.3))]
		_slab(p, sc, dy - 0.04, dy + 0.04, LEAF, grad=(0.45, 1.0))                          # olive-green, keeled
		p.seg((dx, dy - 0.07, dz + 0.1 * s), (dx, dy - 0.07, dz + 1.18 * s), 0.05 * s, 0.02 * s, PINE, sides=4)
		for k in range(2):                                                                # mud-brown bands
			z = dz + (0.45 + k * 0.35) * s
			w = 0.36 * s if k == 0 else 0.3 * s
			p.seg((dx - w, dy - 0.05, z), (dx + w, dy - 0.05, z + 0.04), 0.035 * s, 0.035 * s, WOOD, sides=4)
		for a, b in zip(sc, sc[1:] + sc[:1]):                                             # a yellow rim
			p.seg((a[0], dy - 0.045, a[1]), (b[0], dy - 0.045, b[1]), 0.018, 0.018, AMBER, sides=4)
	return p.build()


def smugglers_token():
	p = Prop("smugglers_token", 1227)
	octa = [(math.cos(math.radians(22.5 + k * 45)) * 0.5, 0.55 + math.sin(math.radians(22.5 + k * 45)) * 0.5) for k in range(8)]
	octa[1] = (octa[1][0] - 0.1, octa[1][1] - 0.12)                                        # a notch cut in one corner
	_slab(p, octa, -0.05, 0.05, STONE_WARM, grad=(0.1, 0.9))                               # a pewter token
	for a, b in zip(octa, octa[1:] + octa[:1]):
		p.seg((a[0], -0.06, a[1]), (b[0], -0.06, b[1]), 0.03, 0.03, STONE_DARK, sides=4)
	p.poly([(-0.26, -0.07, 0.42), (0.26, -0.07, 0.42), (0.18, -0.07, 0.3), (-0.18, -0.07, 0.3)], [(0, 1, 2, 3)], GOLD)   # a little boat stamped in brass
	p.seg((0, -0.07, 0.42), (0, -0.07, 0.82), 0.02, 0.02, GOLD, sides=4)
	p.poly([(0.02, -0.075, 0.8), (0.02, -0.075, 0.46), (0.24, -0.075, 0.48)], [(0, 1, 2)], GOLD)
	p.seg((0, 0.05, 0.9), (0, -0.07, 0.9), 0.05, 0.05, STONE_DARK, sides=8)                # a hole with a tarred string
	_line(p, [(0, -0.02, 0.92), (0.1, -0.05, 1.1), (0.3, -0.06, 1.18), (0.48, -0.06, 1.1)], 0.02, 0.02, STONE_DARK, sides=4)
	return p.build()


# Tidemouth

def reaver_armring():
	p = Prop("reaver_armring", 1229)
	u, v = Vector((1, 0, 0)), Vector((0, 0.55, 0.84))
	_twist_ring(p, (0, 0, 0.5), u, v, 0.55, 0.07, (STONE_LIGHT, IRON), turns=9, gap=0.9)   # a heavy twisted silver arm-ring, open
	for s in (-1, 1):                                                                    # its ends: wolf heads
		a = math.pi / 2 + s * 0.45
		c = Vector((0, 0, 0.5)) + (u * math.cos(a) + v * math.sin(a)) * 0.55
		p.blob((0.2, 0.18, 0.18), tuple(c), GOLD, segs=(8, 6), grad=(0.0, 0.6))
		tip = c + (u * -math.sin(a) + v * math.cos(a)) * (0.14 * s)
		p.seg(tuple(c), tuple(tip), 0.08, 0.03, GOLD, sides=6)
		p.blob((0.05, 0.04, 0.05), tuple(c + Vector((0, -0.1, 0.03))), CLOTH_RED, segs=(5, 3), glow=1.8)
	return p.build()


def clawfolk_pincer():
	p = Prop("clawfolk_pincer", 1231)
	p.blob((0.46, 0.36, 0.72), (0, 0, 0.36), PETAL_PURPLE, segs=(12, 8), grad=(0.0, 0.8))      # a long purple pincer, standing
	_line(p, [(-0.1, 0, 0.66), (-0.16, 0, 0.98), (-0.1, 0, 1.26), (0.04, 0, 1.4)], 0.14, 0.02, PETAL_PURPLE, sides=8, grad=(0.0, 0.8))
	_line(p, [(0.1, 0, 0.66), (0.18, 0, 0.94), (0.14, 0, 1.18), (0.04, 0, 1.3)], 0.11, 0.02, PETAL_PURPLE, sides=8, grad=(0.0, 0.8))
	for k in range(4):                                                                    # serrated inner edges
		z = 0.8 + k * 0.12
		p.seg((-0.08, -0.02, z), (-0.01, -0.02, z - 0.03), 0.03, 0.0, BONE, sides=4)
		p.seg((0.1, -0.02, z - 0.02), (0.03, -0.02, z - 0.05), 0.03, 0.0, BONE, sides=4)
	for (x, z, s) in ((-0.1, 0.5, 0.08), (0.1, 0.34, 0.06), (-0.02, 0.2, 0.05), (0.12, 0.56, 0.05)):   # sea-green spots
		p.blob((s, 0.04, s), (x, -0.18, z), AQUA, segs=(6, 4), glow=0.4)
	for k in range(3):                                                                    # the stump bound in rope
		z = -0.06 + k * 0.07
		p.seg((0, 0, z), (0, 0, z + 0.05), 0.2, 0.2, HIDE, sides=10, twist=k * 30)
	return p.build()


def sea_serpent_scale():
	p = Prop("sea_serpent_scale", 1233)
	for k, (dx, dy, dz, sz) in enumerate(((-0.42, 0.12, 0.52, 0.62), (0.4, 0.1, 0.5, 0.62), (0.0, 0.0, 0.1, 0.8))):   # three round scales, overlapping
		disc = [(dx + math.cos(math.radians(a)) * sz * 0.62, dz + 0.5 * sz + math.sin(math.radians(a)) * sz * 0.66) for a in range(0, 360, 20)]
		_slab(p, disc, dy - 0.04, dy + 0.04, AQUA, grad=(0.0, 0.9))                       # sea-green, iridescent
		for a, b in zip(disc, disc[1:] + disc[:1]):
			p.seg((a[0], dy - 0.05, a[1]), (b[0], dy - 0.05, b[1]), 0.022, 0.022, SKY, sides=4, glow=0.9)
		for r in (0.22, 0.4):                                                             # growth rings
			arc = [(dx + math.cos(math.radians(a)) * r * sz, dz + 0.5 * sz + 0.1 * sz + math.sin(math.radians(a)) * r * sz * 1.1)
				   for a in range(-20, -161, -20)]
			_line(p, [(x, dy - 0.055, z) for x, z in arc], 0.018, 0.018, SEAFOAM, sides=4, glow=0.6)
	p.blob((0.2, 0.05, 0.14), (-0.08, -0.07, 0.62), CLOTH_WHITE, segs=(8, 4), glow=1.6)        # a wet sheen
	p.seg((0.26, -0.05, 0.22), (0.26, -0.14, 0.22), 0.08, 0.03, STONE_LIGHT, sides=6)          # a barnacle
	return p.build()


def gull_feather():
	p = Prop("gull_feather", 1235)
	_vane(p, (-0.45, 0, -0.15), (0.5, 0, 1.35), 0.26, CLOTH_WHITE, tip_swatch=STONE_DARK)     # a big white gull's feather, black-tipped
	p.blob((0.1, 0.02, 0.1), (0.36, -0.03, 1.1), CLOTH_WHITE, segs=(6, 4))                    # the white spot in the black
	for t in (0.35, 0.5):                                                                 # a gray wash across the vane
		p.seg((-0.45 + 0.95 * t - 0.2, -0.015, -0.15 + 1.5 * t + 0.08), (-0.45 + 0.95 * t + 0.16, -0.015, -0.15 + 1.5 * t - 0.12), 0.05, 0.05, ASH,
			  sides=4, grad=(0.3, 0.4))
	return p.build()


def bottled_lightning():
	p = Prop("bottled_lightning", 1237)
	p.blob((0.7, 0.7, 0.86), (0, 0, 0.43), WATER, segs=(14, 10), grad=(0.1, 0.9), glow=0.5)     # a stormy blue bottle
	_potion(p, 0.82, neck=0.22, neck_r=0.1)
	p.seg((0, 0, 1.18), (0, 0, 1.24), 0.12, 0.12, CLOTH_RED, sides=10)                        # sealed with red wax
	_zap(p, [(-0.1, -0.36, 0.78), (0.1, -0.36, 0.56), (-0.06, -0.37, 0.46), (0.12, -0.36, 0.18)], r=0.04)   # a bolt of lightning inside
	_zap(p, [(0.1, -0.33, 0.56), (0.24, -0.3, 0.5)], r=0.025, sw=SKY)
	p.blob((0.2, 0.1, 0.2), (0.0, -0.3, 0.46), CLOTH_WHITE, segs=(8, 5), glow=2.0)
	for (a, b) in (((0.3, -0.1, 1.05), (0.44, -0.1, 1.18)), ((-0.3, -0.1, 1.02), (-0.46, -0.1, 1.1))):   # sparks leaking out
		_zap(p, [a, ((a[0] + b[0]) / 2 + 0.04, a[1], (a[2] + b[2]) / 2 - 0.04), b], r=0.02, sw=SKY)
	return p.build()


# the named ones

def uthraks_war_horn():
	p = Prop("uthraks_war_horn", 1239)
	pts = [(-0.75, 0, 0.62), (-0.4, 0, 0.42), (0.0, 0, 0.34), (0.36, 0, 0.44), (0.62, 0, 0.72)]
	_line(p, pts, 0.07, 0.34, STONE_WARM, sides=12, grad=(0.1, 0.9), )                       # a huge gray horn, rough
	p.seg((0.62, 0, 0.72), (0.66, 0, 0.77), 0.34, 0.34, STONE_DARK, sides=12)                 # its dark bell
	for c, r in ((pts[1], 0.14), (pts[3], 0.28)):                                         # iron bands with spikes
		p.seg((c[0] - 0.04, 0, c[2]), (c[0] + 0.04, 0, c[2] + 0.02), r, r, IRON, sides=12)
		for a in (-100, -60, -20):
			ar = math.radians(a)
			p.seg((c[0], math.sin(ar) * r, c[2] + math.cos(ar) * r), (c[0], math.sin(ar) * (r + 0.14), c[2] + math.cos(ar) * (r + 0.14)),
				  0.04, 0.0, STONE_LIGHT, sides=4)
	p.seg((-0.78, 0, 0.64), (-0.88, 0, 0.7), 0.08, 0.09, IRON, sides=8)                      # an iron mouthpiece
	_line(p, [(-0.5, -0.02, 0.5), (-0.3, -0.05, 0.98), (0.15, -0.05, 1.1), (0.4, -0.02, 0.8)], 0.035, 0.035, WOOD, sides=5)   # a hide strap
	p.seg((-0.2, -0.3, 0.34), (-0.1, -0.3, 0.37), 0.05, 0.05, CLOTH_RED, sides=5)              # red war-paint marks
	p.seg((0.12, -0.36, 0.38), (0.22, -0.36, 0.42), 0.05, 0.05, CLOTH_RED, sides=5)
	return p.build()


def sunwing_plume():
	p = Prop("sunwing_plume", 1241)
	_vane(p, (-0.35, 0.06, -0.1), (-0.7, 0.06, 1.1), 0.18, AMBER, tip_swatch=CLOTH_RED)        # a smaller plume behind
	_vane(p, (-0.3, 0, -0.15), (0.5, 0, 1.4), 0.3, GOLD, tip_swatch=FLAME, glow=2.0)          # a great golden plume, lit like the sun
	for (x, z) in ((0.6, 1.2), (0.3, 1.45), (0.62, 0.8), (-0.05, 1.25)):                  # sparks of light round it
		p.blob((0.06, 0.06, 0.06), (x, -0.1, z), GOLD, segs=(5, 3), glow=2.6)
	p.seg((-0.36, -0.04, -0.2), (-0.26, -0.04, 0.0), 0.05, 0.05, DAWN, sides=6, glow=0.8)
	return p.build()


def storm_crown_shard():
	p = Prop("storm_crown_shard", 1243)
	arc = [(x, -0.3 + 0.35 * x * x, 0.3 + 0.1 * x * x) for x in [-0.62 + k * 0.1 for k in range(12)]]   # the front of a silver crown, broken off
	_line(p, arc, 0.12, 0.12, STONE_LIGHT, sides=6, grad=(0.0, 0.6))
	_line(p, [(q[0], q[1], q[2] + 0.16) for q in arc], 0.055, 0.055, STONE_LIGHT, sides=5, grad=(0.0, 0.6))
	mid = arc[6]
	_line(p, [mid, (mid[0] - 0.1, mid[1], mid[2] + 0.42), (mid[0] + 0.1, mid[1], mid[2] + 0.54), (mid[0] - 0.04, mid[1], mid[2] + 1.0)],
		  0.13, 0.02, STONE_LIGHT, sides=5, grad=(0.0, 0.5))                                 # a lightning-bolt tine
	for q, h in ((arc[2], 0.5), (arc[10], 0.3)):                                          # a lesser one, and one snapped short
		_line(p, [q, (q[0] + 0.06, q[1], q[2] + h * 0.5), (q[0] - 0.02, q[1], q[2] + h)], 0.09, 0.03 if h > 0.4 else 0.07, STONE_LIGHT, sides=5)
	p.blob((0.26, 0.14, 0.3), (mid[0], mid[1] - 0.14, mid[2] + 0.06), SKY, segs=(8, 6), glow=2.2)   # a storm-blue stone
	end = arc[-1]                                                                         # the broken end, still crackling
	_zap(p, [end, (end[0] + 0.16, end[1] - 0.1, end[2] + 0.2), (end[0] + 0.06, end[1] - 0.12, end[2] + 0.36), (end[0] + 0.24, end[1] - 0.14, end[2] + 0.54)],
		 r=0.03, sw=SKY, glow=2.6)
	_zap(p, [end, (end[0] + 0.22, end[1] - 0.1, end[2] - 0.06), (end[0] + 0.34, end[1] - 0.12, end[2] + 0.08)], r=0.025, sw=CLOTH_WHITE, glow=2.6)
	for k in range(3):                                                                    # jagged break
		p.seg(end, (end[0] + 0.08, end[1] - 0.02, end[2] + (k - 1) * 0.08), 0.07, 0.0, STONE_LIGHT, sides=4)
	return p.build()


def halvards_sun_banner():
	p = Prop("halvards_sun_banner", 1245)
	p.seg((-0.5, 0.05, -0.3), (-0.5, 0.05, 1.45), 0.045, 0.045, WOOD, sides=8)                # a pole
	_sun(p, (-0.5, 0.05, 1.55), 0.07, GOLD, rays=8, ray=1.0, glow=0.8)                        # a gold sun finial
	p.seg((-0.55, 0.0, 1.32), (0.45, 0.0, 1.32), 0.035, 0.035, GOLD, sides=6)                # a gilt crossbar
	cloth = [(-0.45, 1.3), (0.4, 1.3), (0.4, 0.34), (0.22, 0.1), (0.06, 0.26), (-0.12, 0.06), (-0.3, 0.24), (-0.45, 0.2)]
	_slab(p, cloth, 0.0, 0.03, CLOTH_WHITE, grad=(0.0, 0.8))                                 # a white banner, singed and torn
	for a, b in zip(cloth[:3], cloth[1:4]):                                               # a red border
		p.seg((a[0], -0.01, a[1]), (b[0], -0.01, b[1]), 0.035, 0.035, CLOTH_RED, sides=4)
	p.seg((-0.45, -0.01, 1.3), (-0.45, -0.01, 0.2), 0.035, 0.035, CLOTH_RED, sides=4)
	_sun(p, (-0.02, -0.03, 0.76), 0.2, GOLD, rays=12, ray=0.8, glow=0.7)                      # the dawn god's gold sun
	p.blob((0.2, 0.03, 0.14), (0.24, -0.02, 0.36), STONE_DARK, segs=(8, 4), jitter=0.02)       # a scorch mark
	return p.build()


def cracked_mirror_face():
	p = Prop("cracked_mirror_face", 1247)
	face = [(math.sin(math.radians(a)) * 0.46, 0.64 + math.cos(math.radians(a)) * (0.64 if a < 90 or a > 270 else 0.6)) for a in range(0, 360, 20)]
	_slab(p, face, -0.02, 0.05, STONE_LIGHT, grad=(0.0, 0.45))                               # a silver mirror-glass face
	p.seg((0, -0.04, 0.78), (0, -0.14, 0.52), 0.06, 0.09, STONE_LIGHT, sides=5, grad=(0.0, 0.4))   # its nose
	for sx in (-1, 1):
		p.blob((0.2, 0.04, 0.1), (sx * 0.18, -0.05, 0.8), STONE_DARK, segs=(8, 4))            # empty eyes
		p.seg((sx * 0.3, -0.04, 0.92), (sx * 0.06, -0.04, 0.9), 0.025, 0.02, STONE_LIGHT, sides=4)   # brows
	p.seg((-0.14, -0.05, 0.34), (0.14, -0.05, 0.34), 0.03, 0.03, STONE_DARK, sides=4)           # a thin mouth
	for pts in (((-0.1, 1.24), (0.0, 1.0), (-0.08, 0.86), (0.08, 0.66), (0.02, 0.4), (0.2, 0.1)),   # cracks through it
				((0.0, 1.0), (0.3, 0.9), (0.44, 0.96)), ((0.08, 0.66), (-0.3, 0.52), (-0.44, 0.4)), ((0.02, 0.4), (0.34, 0.46))):
		_line(p, [(x, -0.07, z) for x, z in pts], 0.024, 0.014, STONE_DARK, sides=4)
	p.poly([(0.12, -0.06, 1.1), (0.34, -0.06, 1.02), (0.3, -0.06, 0.94), (0.14, -0.06, 1.0)], [(0, 1, 2, 3)], SKY)   # sky in a fragment
	for c in ((0.3, -0.08, 1.06), (-0.3, -0.08, 0.3)):                                    # glints
		p.blob((0.05, 0.03, 0.05), c, CLOTH_WHITE, segs=(5, 3), glow=3.0)
	return p.build()


def saltclaws_pearl():
	p = Prop("saltclaws_pearl", 1249)
	rng = p.rng
	for k in range(9):                                                                    # a nest of salt crystals
		a = k * math.tau / 9
		r = rng.uniform(0.3, 0.55)
		_crystal(p, (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.0), (math.cos(a) * r, math.sin(a) * r * 0.8, rng.uniform(0.3, 0.55)), 0.09,
				 CLOTH_WHITE if k % 2 else STONE_LIGHT, glow=0.3)
	p.blob((0.62, 0.62, 0.62), (0, -0.05, 0.56), CLOTH_WHITE, segs=(16, 12), grad=(0.0, 0.6), glow=0.5)   # a great white pearl
	p.blob((0.2, 0.08, 0.16), (-0.14, -0.33, 0.66), PINK, segs=(8, 5), glow=1.2)               # a rosy sheen on it
	p.blob((0.07, 0.03, 0.07), (-0.12, -0.36, 0.72), CLOTH_WHITE, segs=(5, 3), glow=3.0)
	p.seg((0.36, -0.1, 0.2), (0.56, -0.12, 0.66), 0.08, 0.02, BONE, sides=6)                   # a claw tip clasping it
	p.seg((0.56, -0.12, 0.66), (0.4, -0.2, 0.86), 0.03, 0.0, BONE, sides=5)
	return p.build()


def asras_salt_crown():
	p = Prop("asras_salt_crown", 1251)
	_loop(p, (0, 0, 0.2), 0.48, True, 0.07, CLAY, n=20)                                     # a bronze band
	_loop(p, (0, 0, 0.3), 0.47, True, 0.04, CLAY, n=20)
	for k in range(9):                                                                    # crowned with tall salt crystals
		a = math.radians(-90 + (k - 4) * 26)
		x, y = math.cos(a) * 0.48, math.sin(a) * 0.48
		h = 0.95 if k == 4 else 0.55 + 0.2 * (1 - abs(k - 4) / 4) + 0.08 * (k % 2)
		_crystal(p, (x, y, 0.28), (x * 1.12, y * 1.12, h), 0.07 if k == 4 else 0.055, CLOTH_WHITE, glow=0.5)
	for k in range(4):                                                                    # the back of it
		a = math.radians(40 + k * 34)
		_crystal(p, (math.cos(a) * 0.48, math.sin(a) * 0.48, 0.28), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.6), 0.05, STONE_LIGHT)
	p.blob((0.16, 0.1, 0.2), (0, -0.52, 0.22), AQUA, segs=(8, 6), glow=1.6)                   # a turquoise stone
	for sx in (-1, 1):
		p.blob((0.08, 0.06, 0.08), (sx * 0.3, -0.42, 0.2), GOLD, segs=(6, 4))
	return p.build()


def sky_ray_spine():
	p = Prop("sky_ray_spine", 1253)
	org, rot = (-0.55, -0.45), 50
	up, lo = [], []
	for k in range(10):                                                                   # a long serrated barb
		s = k * 0.16
		hw = 0.1 * (1 - k / 10) + 0.03
		up.append((s, hw + (0.04 if k % 2 else 0.0)))
		lo.append((s, -hw - (0.04 if k % 2 == 0 and k else 0.0)))
	outline = up + [(1.72, 0.0)] + lo[::-1]
	_slab(p, _rot2(outline, rot, org), -0.04, 0.04, BONE, grad=(0.0, 0.7))
	mid = _rot2([(0.0, 0.0), (1.6, 0.0)], rot, org)
	p.seg((mid[0][0], -0.05, mid[0][1]), (mid[1][0], -0.05, mid[1][1]), 0.03, 0.01, SKY, sides=4, glow=1.4)   # a blue glow along its groove
	tail = _rot2([(-0.02, 0.0), (-0.3, 0.06), (-0.55, 0.0), (-0.75, -0.12)], rot, org)
	_line(p, [(x, 0.02, z) for x, z in tail], 0.12, 0.04, SEA_STONE, sides=8, grad=(0.1, 0.8))   # on a stub of blue-gray tail
	return p.build()


def river_kings_pearl_crown():
	p = Prop("river_kings_pearl_crown", 1255)
	_loop(p, (0, 0, 0.18), 0.5, True, 0.09, CLAY, n=16)                                     # a crude bronze crown
	for k in range(7):                                                                    # uneven tines, each with a pearl
		a = math.radians(-90 + (k - 3) * 30)
		x, y = math.cos(a) * 0.5, math.sin(a) * 0.5
		h = 0.62 + 0.12 * ((k * 7) % 3) + (0.16 if k == 3 else 0.0)
		p.seg((x, y, 0.2), (x * 1.05 + 0.02 * (k % 2), y * 1.05, h), 0.07, 0.04, CLAY, sides=5, jitter=0.01)
		p.blob((0.13, 0.13, 0.13), (x * 1.05 + 0.02 * (k % 2), y * 1.05, h + 0.06), CLOTH_WHITE, segs=(8, 6), grad=(0.0, 0.5), glow=0.5)
	for k in range(4):
		a = math.radians(30 + k * 40)
		p.seg((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.2), (math.cos(a) * 0.52, math.sin(a) * 0.52, 0.56), 0.06, 0.03, CLAY, sides=5)
	for (a, s) in ((-120, 0.14), (-50, 0.12)):                                            # clods of river mud
		r = math.radians(a)
		p.rock((s, s, s * 0.8), (math.cos(r) * 0.52, math.sin(r) * 0.52 - 0.04, 0.18), WOOD, jitter=0.03)
	for a in (-105, -75, -30):                                                            # green weed trailing off it
		r = math.radians(a)
		x, y = math.cos(r) * 0.54, math.sin(r) * 0.54
		_line(p, [(x, y, 0.14), (x * 1.05, y * 1.05 - 0.02, -0.08), (x * 1.1 + 0.05, y * 1.1, -0.28)], 0.03, 0.012, LEAF, sides=4)
	return p.build()


def shell_mask():
	p = Prop("shell_mask", 1257)
	_scallop(p, (0, 0, 0.0), 0.72, AMBER, CLAY, eyes=STONE_DARK)                             # a great scallop shell worn as a face
	for sx in (-1, 1):                                                                    # mud daubs beneath the eyes
		p.seg((sx * 0.2, -0.06, 0.28), (sx * 0.24, -0.06, 0.12), 0.035, 0.03, WOOD, sides=4)
		p.blob((0.06, 0.04, 0.06), (sx * 0.22, -0.1, 0.4), CLOTH_WHITE, segs=(5, 3), glow=1.8)   # pale lights where eyes should be
		_line(p, [(sx * 0.66, 0.0, 0.4), (sx * 0.82, -0.02, 0.2), (sx * 0.78, -0.02, -0.1)], 0.025, 0.02, LEAF, sides=4)   # reed ties
	p.blob((0.12, 0.08, 0.12), (0, -0.07, 0.58), CLOTH_WHITE, segs=(8, 5), glow=0.6)            # a pearl on the brow
	return p.build()


def coilmothers_fang():
	p = Prop("coilmothers_fang", 1259)
	pts = [(0, 0, 1.15), (0.2, 0, 0.84), (0.3, 0, 0.46), (0.2, 0, 0.12), (-0.04, 0, -0.08)]   # a huge hooked fang, tip down
	_line(p, pts, 0.24, 0.0, BONE, sides=9, grad=(0.0, 0.7))
	_line(p, [(0.1, -0.2, 0.92), (0.2, -0.24, 0.6), (0.18, -0.2, 0.3)], 0.03, 0.02, LEAF, sides=4, glow=2.0)   # its venom groove
	p.rock((0.62, 0.5, 0.34), (0.0, 0.02, 1.22), TEAL, jitter=0.05)                           # a lump of scaled jaw at the root
	for k in range(5):
		a = k * 1.25
		p.blob((0.12, 0.06, 0.1), (math.cos(a) * 0.22, -0.2, 1.24 + math.sin(a) * 0.08), PINE, segs=(6, 4))
	p.blob((0.14, 0.14, 0.2), (-0.08, 0, -0.2), LEAF, segs=(8, 6), glow=2.4)                  # venom dripping off the point
	p.blob((0.08, 0.08, 0.1), (-0.1, 0, -0.42), LEAF, segs=(6, 4), glow=2.4)
	return p.build()


def blackwaters_ledger():
	p = Prop("blackwaters_ledger", 1261)
	_book(p, STONE_DARK, trim=GOLD)                                                        # a black ledger with brass corners
	for (x, z, s) in ((0.12, 0.6, 0.22), (-0.2, 0.34, 0.14)):                            # water stains
		p.blob((s, 0.02, s * 0.8), (x, -0.15, z), SEA_STONE, segs=(10, 4), grad=(0.3, 0.8))
	_line(p, [(0.2, -0.15, 0.9), (0.24, -0.16, 0.3), (0.28, -0.17, -0.12)], 0.025, 0.025, CLOTH_RED, sides=4)   # a red ribbon
	p.box((0.12, 0.06, 0.1), (0.42, -0.16, 0.54), GOLD)                                    # a brass clasp
	for k in range(4):                                                                    # coins spilling out beside it
		p.seg((0.55 + k * 0.08, -0.3 - k * 0.04, 0.02 + k * 0.035), (0.55 + k * 0.08, -0.3 - k * 0.04, 0.05 + k * 0.035), 0.1, 0.1, GOLD, sides=12,
			  glow=0.3)
	return p.build()


def saltbeards_whalebone_crown():
	p = Prop("saltbeards_whalebone_crown", 1263)
	_loop(p, (0, 0, 0.2), 0.5, True, 0.13, HIDE, n=18)                                      # a band of tarred rope
	for k in range(18):
		a = k * math.tau / 18
		p.seg((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.13), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.27), 0.03, 0.03, WOOD, sides=4)
	for k in range(7):                                                                    # curved whalebone tines, like ribs
		a = math.radians(-90 + (k - 3) * 28)
		x, y = math.cos(a) * 0.5, math.sin(a) * 0.5
		h = 0.95 if k == 3 else (0.8 if k % 2 == 0 else 0.7)
		_line(p, [(x, y, 0.2), (x * 1.2, y * 1.2, 0.48), (x * 1.22, y * 1.22, h - 0.12), (x * 1.08, y * 1.08, h)], 0.12, 0.03, BONE, sides=6, grad=(0.0, 0.6))
	for k in range(3):
		a = math.radians(50 + k * 40)
		_line(p, [(math.cos(a) * 0.5, math.sin(a) * 0.5, 0.2), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.64)], 0.1, 0.02, BONE, sides=5)
	p.blob((0.24, 0.12, 0.24), (0, -0.62, 0.22), SEAFOAM, segs=(8, 6), glow=1.4)              # a lump of sea glass
	_line(p, [(0.3, -0.42, 0.14), (0.32, -0.44, -0.12), (0.36, -0.46, -0.28), (0.44, -0.46, -0.24)], 0.025, 0.02, IRON, sides=4)   # a fishhook hung off it
	return p.build()


def horror_lure():
	p = Prop("horror_lure", 1265)
	pts = [(-0.55, 0, -0.1), (-0.5, 0, 0.3), (-0.3, 0, 0.72), (0.05, 0, 0.98), (0.4, 0, 0.92), (0.52, 0, 0.68)]
	_line(p, pts, 0.1, 0.04, CRIMSON, sides=8, grad=(0.3, 1.0))                             # a fleshy stalk
	p.blob((0.46, 0.46, 0.5), (0.54, -0.02, 0.44), SEAFOAM, segs=(14, 10), grad=(0.0, 0.5), glow=2.6)   # the glowing lure
	p.blob((0.22, 0.14, 0.22), (0.5, -0.2, 0.46), CLOTH_WHITE, segs=(8, 6), glow=3.2)
	for k in range(4):                                                                    # filaments trailing off it
		a = math.radians(210 + k * 35)
		c = (0.54 + math.cos(a) * 0.2, -0.05, 0.44 + math.sin(a) * 0.22)
		_line(p, [c, (c[0] + math.cos(a) * 0.14, -0.06, c[2] - 0.2), (c[0] + math.cos(a) * 0.1, -0.06, c[2] - 0.38)], 0.02, 0.008, SEAFOAM, sides=4,
			  glow=1.6)
	p.rock((0.4, 0.4, 0.28), (-0.56, 0.02, -0.12), PETAL_PURPLE, jitter=0.06)                   # torn from the horror's brow
	return p.build()


def whitefins_fin():
	p = Prop("whitefins_fin", 1267)
	fin = [(-0.62, 0.0), (0.55, 0.0), (0.44, 0.1), (0.3, 0.32), (0.26, 0.6), (0.36, 0.94), (0.5, 1.28), (0.2, 1.0), (-0.1, 0.72), (-0.4, 0.34)]
	_slab(p, fin, -0.06, 0.06, CLOTH_WHITE, grad=(0.0, 0.7))                                # a great white dorsal fin
	for a, b in zip(fin[5:], fin[6:] + fin[:1]):                                          # a gray leading edge
		p.seg((a[0], -0.07, a[1]), (b[0], -0.07, b[1]), 0.03, 0.03, ASH, sides=4, grad=(0.5, 0.6))
	for (x0, z0, x1, z1) in ((-0.2, 0.3, 0.0, 0.5), (0.0, 0.2, 0.16, 0.36), (0.1, 0.7, 0.3, 0.86)):   # old scars
		p.seg((x0, -0.07, z0), (x1, -0.07, z1), 0.02, 0.02, STONE_WARM, sides=4)
	p.poly([(0.36, -0.07, 0.94), (0.28, -0.07, 0.82), (0.36, -0.07, 0.78)], [(0, 1, 2)], STONE_DARK)   # a notch bitten out
	p.box((1.16, 0.14, 0.08), (-0.04, 0, -0.02), CRIMSON, grad=(0.3, 1.0))                  # hacked off at the base
	return p.build()


def tempest_heart():
	p = Prop("tempest_heart", 1269)
	p.blob((0.72, 0.62, 0.72), (0, 0, 0.6), STONE_DARK, segs=(14, 10), grad=(0.0, 0.9))       # a heart of storm cloud
	for k in range(8):                                                                    # billowing round it
		a = k * math.tau / 8
		p.blob((0.34, 0.3, 0.3), (math.cos(a) * 0.36, -0.06 + math.sin(a) * 0.1, 0.6 + math.sin(a) * 0.32), ASH, segs=(8, 6), grad=(0.3, 0.9))
	p.blob((0.3, 0.12, 0.3), (0, -0.3, 0.6), SKY, segs=(10, 6), glow=3.0)                     # its blazing core
	for a in (20, 120, 200, 300):                                                         # lightning forking out of it
		r = math.radians(a)
		c, d = Vector((0, -0.34, 0.6)), Vector((math.cos(r), 0, math.sin(r)))
		n = Vector((-d.z, 0, d.x))
		pts = [c + d * 0.1, c + d * 0.28 + n * 0.08, c + d * 0.4 - n * 0.06, c + d * 0.62 + n * 0.04]
		_zap(p, [tuple(q) for q in pts], r=0.03)
	return p.build()


# rewards

def dawnwatch_bracer():
	p = Prop("dawnwatch_bracer", 1271)
	_vambrace(p, STONE_LIGHT, GOLD, CLOTH_RED, GOLD, grad=(0.0, 0.45))                     # a bright steel vambrace, gold trimmed
	c = _fa(-0.02, 0.32, -10)
	_sun(p, c, 0.1, GOLD, rays=10, ray=1.0, glow=1.0)                                        # a gold sun on it
	p.blob((0.07, 0.04, 0.07), (c[0], c[1] - 0.04, c[2]), DAWN, segs=(6, 4), glow=2.0)
	p.seg(_fa(-0.46), _fa(-0.4), 0.36, 0.36, CLOTH_WHITE, sides=16, jitter=0.02)              # a snow-white fur lining
	return p.build()


def ogrehide_belt():
	p = Prop("ogrehide_belt", 1273)
	f, out, tan = _belt(p, STONE_WARM, WOOD, IRON, R=0.6, h=0.26, grad=(0.2, 0.9))           # a thick belt of gray ogre hide
	for k in range(7):                                                                    # rows of rivets
		a = math.radians(-160 + k * 22)
		if abs(a - math.radians(-61)) < 0.2:
			continue
		q = Vector((0, 0.1, 0.5)) + Vector((math.cos(a), math.sin(a), 0)) * 0.62
		p.blob((0.05, 0.05, 0.05), tuple(q), STONE_LIGHT, segs=(6, 4))
	tusk = f + tan * 0.3 + Vector((0, 0, -0.14))                                          # a tusk hung from it
	_line(p, [tuple(tusk), tuple(tusk + Vector((0.02, -0.06, -0.3))), tuple(tusk + Vector((0.1, -0.1, -0.48)))], 0.07, 0.0, BONE, sides=6)
	return p.build()


def rocfeather_cloak():
	p = Prop("rocfeather_cloak", 1275)
	_slab(p, _cape_outline(0.3, 0.64, 0.14), 0.04, 0.1, WOOD, grad=(0.2, 0.9))              # a hide cape
	for row in range(4):                                                                  # shingled with golden roc feathers
		z = 0.92 - row * 0.24
		n = 6 + (row % 2)
		spread = 0.3 + row * 0.1
		for k in range(n):
			u = -1 + 2 * k / (n - 1)
			x = u * spread
			tip = (x + u * 0.04, 0.0, z - 0.4)
			_vane(p, (x, 0.0 - row * 0.012, z), (tip[0], -row * 0.012, tip[2]), 0.075 + row * 0.02, GOLD if (k + row) % 2 else AMBER, bars=(0.5,),
				  tip_swatch=WOOD if row == 3 else None)
	p.blob((0.22, 0.1, 0.22), (0, -0.14, 0.96), DAWN, segs=(10, 6), glow=1.4)                 # a dawn-rose clasp
	p.seg((0, -0.12, 0.96), (0, -0.2, 0.96), 0.08, 0.08, GOLD, sides=10)
	return p.build()


def frostspirit_ring():
	p = Prop("frostspirit_ring", 1277)
	_ring(p, STONE_LIGHT)                                                                  # a silver ring
	for k, (dx, h, r) in enumerate(((0.0, 0.5, 0.08), (-0.14, 0.34, 0.06), (0.15, 0.36, 0.06), (0.06, 0.26, 0.045))):   # grown with ice
		_crystal(p, (dx * 0.5, -0.02, 0.8), (dx, -0.06 - k * 0.02, 0.8 + h), r, SKY if k == 0 else CLOTH_WHITE, glow=1.8 if k == 0 else 0.6)
	for (x, z) in ((-0.3, 1.1), (0.34, 1.16), (0.0, 1.42)):
		p.blob((0.05, 0.05, 0.05), (x, -0.1, z), CLOTH_WHITE, segs=(5, 3), glow=2.4)
	return p.build()


def stormcrown_circlet():
	p = Prop("stormcrown_circlet", 1279)
	_loop(p, (0, 0, 0.2), 0.48, True, 0.08, STONE_LIGHT, n=20)                             # a silver circlet
	_loop(p, (0, 0, 0.1), 0.49, True, 0.045, GOLD, n=20)                                    # edged in gold
	for k, (a, h) in enumerate(((-90, 0.95), (-125, 0.6), (-55, 0.6), (-160, 0.4), (-20, 0.4))):   # rising in lightning bolts
		r = math.radians(a)
		x, y = math.cos(r) * 0.5, math.sin(r) * 0.5
		_line(p, [(x, y, 0.2), (x + 0.1, y, 0.2 + h * 0.45), (x - 0.08, y, 0.2 + h * 0.55), (x + 0.03, y, 0.2 + h)], 0.09, 0.0, STONE_LIGHT,
			  sides=5, grad=(0.0, 0.5))
	p.blob((0.16, 0.1, 0.2), (0, -0.56, 0.24), SKY, segs=(8, 6), glow=2.2)                   # a storm-blue stone
	_zap(p, [(0.02, -0.6, 0.36), (0.1, -0.6, 0.5), (0.04, -0.6, 0.56)], r=0.015, sw=CLOTH_WHITE, glow=2.4)
	return _tip_back(p.build(), -22)


def sunbadge_pendant():
	p = Prop("sunbadge_pendant", 1281)
	_cord(p, 0.46, 0.9, GOLD)                                                              # a gold chain
	_sun(p, (0, -0.3, 0.36), 0.2, GOLD, rays=14, ray=0.9, glow=0.8)                          # a gold sun pendant
	_loop(p, (0, -0.33, 0.36), 0.14, False, 0.02, CLOTH_RED, n=14)                           # red enamel round a dawn-rose stone
	p.blob((0.14, 0.06, 0.14), (0, -0.36, 0.36), DAWN, segs=(8, 5), glow=1.8)
	p.seg((0, -0.3, 0.6), (0, -0.3, 0.72), 0.03, 0.03, GOLD, sides=5)
	return p.build()


def halvards_sunblade():
	p = Prop("halvards_sunblade", 1283)
	org, rot = (-0.55, -0.45), 48
	outline = [(0.32, 0.1), (0.8, 0.11), (1.3, 0.1), (1.56, 0.06), (1.72, 0.0), (1.56, -0.06), (1.3, -0.1), (0.8, -0.11), (0.32, -0.1)]
	_slab(p, _rot2(outline, rot, org), -0.03, 0.03, STONE_LIGHT, grad=(0.0, 0.3))             # a long bright blade
	for sgn in (1, -1):                                                                   # its edges lit gold
		e = _rot2([(0.4, sgn * 0.09), (1.3, sgn * 0.09), (1.56, sgn * 0.05), (1.7, 0.0)], rot, org)
		_line(p, [(x, -0.04, z) for x, z in e], 0.014, 0.01, GOLD, sides=4, glow=1.6)
	f = _rot2([(0.42, 0.0), (1.4, 0.0)], rot, org)
	p.seg((f[0][0], -0.045, f[0][1]), (f[1][0], -0.045, f[1][1]), 0.025, 0.01, DAWN, sides=4, glow=1.6)   # a dawn-lit fuller
	for sgn in (1, -1):                                                                   # a winged gold guard
		wing = [(0.26, sgn * 0.04), (0.36, sgn * 0.06), (0.46, sgn * 0.24), (0.56, sgn * 0.44), (0.42, sgn * 0.4), (0.32, sgn * 0.3), (0.22, sgn * 0.14)]
		_slab(p, _rot2(wing, rot, org), -0.04, 0.04, GOLD, grad=(0.0, 0.7))
	s = _rot2([(0.3, 0.0)], rot, org)[0]
	_sun(p, (s[0], -0.06, s[1]), 0.12, GOLD, rays=10, ray=0.8, glow=0.9)
	p.blob((0.1, 0.05, 0.1), (s[0], -0.1, s[1]), DAWN, segs=(6, 4), glow=2.0)
	h = _rot2([(0.24, 0.0), (-0.16, 0.0), (-0.24, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.055, CLOTH_WHITE, sides=6)     # a white grip
	for t in (0.3, 0.65):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.02, 0, q[1] - 0.02), (q[0] + 0.02, 0, q[1] + 0.02), 0.065, 0.065, GOLD, sides=6)
	p.blob((0.16, 0.16, 0.16), (h[2][0], 0, h[2][1]), FLAME, segs=(8, 6), glow=1.6)             # a sunstone pommel
	return p.build()


def warlords_war_horn():
	p = Prop("warlords_war_horn", 1285)
	_line(p, [(-0.62, -0.1, 0.22), (-0.25, -0.1, 0.1), (0.15, -0.1, 0.16), (0.5, -0.1, 0.42)], 0.05, 0.2, BONE, sides=10, grad=(0.0, 0.7))   # a polished war horn
	p.seg((0.5, -0.1, 0.42), (0.54, -0.1, 0.46), 0.2, 0.2, STONE_DARK, sides=10)
	for x, z, r in ((-0.36, 0.13, 0.1), (0.0, 0.11, 0.15), (0.34, 0.27, 0.2)):              # gold bands
		p.seg((x - 0.03, -0.1, z), (x + 0.03, -0.1, z + 0.01), r, r, GOLD, sides=10)
	p.seg((-0.62, -0.1, 0.22), (-0.72, -0.1, 0.26), 0.06, 0.07, GOLD, sides=8)                # a gold mouthpiece
	for (x, z) in ((-0.36, 0.13), (0.34, 0.27)):                                           # hung on a red baldric
		_line(p, [(x, -0.1, z + 0.12), (x * 0.6, -0.02, 0.7), (0.0, 0.1, 1.0)], 0.03, 0.03, CLOTH_RED, sides=5)
	for k in range(4):                                                                    # a tuft of ogre fur
		p.blob((0.12, 0.1, 0.14), (-0.3 + k * 0.05, -0.16, 0.0 - (k % 2) * 0.06), STONE_WARM, segs=(6, 4), jitter=0.02)
	return p.build()


def mirrorglass_gloves():
	p, fr = _glove_pair("mirrorglass_gloves", 1287, STONE_LIGHT, CLOTH_WHITE, SKY, grad=(0.0, 0.45))
	for f in fr:                                                                          # a mirror set in the back of each
		p.blob((0.3, 0.06, 0.26), f(0, -0.15, 0.55), SKY, segs=(10, 5), glow=1.2)
		p.blob((0.14, 0.03, 0.08), f(-0.05, -0.18, 0.6), CLOTH_WHITE, segs=(6, 4), glow=2.6)
		for x, _ in FINGERS:                                                              # glass chips on the knuckles
			p.box((0.07, 0.04, 0.07), f(x * 1.05, -0.1, 0.76), CLOTH_WHITE, rot=(0, 45 + f.tilt, 0), glow=0.8)
	return p.build()


def saltcrust_boots():
	p = Prop("saltcrust_boots", 1289)
	rng = p.rng
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, HIDE, BONE, WOOD, grad=(0.1, 0.8), shaft=0.74)                 # tan leather boots
		for k in range(8):                                                                # crusted white with salt to the shin
			a = rng.uniform(-2.6, -0.6)
			z = rng.uniform(0.05, 0.36)
			x = ox - 0.2 + rng.uniform(-0.25, 0.28) if z < 0.2 else ox + math.cos(a) * r
			p.box((0.09, 0.09, 0.09), (x, oy + math.sin(a) * (r + 0.05) - 0.04, z), CLOTH_WHITE,
				  rot=(rng.uniform(0, 90), rng.uniform(0, 90), rng.uniform(0, 90)), glow=0.3)
		_loop(p, (ox + 0.01, oy, 0.36), r + 0.02, True, 0.035, CLOTH_WHITE, n=14, squash=1.0)   # a salt tide line
	return p.build()


def skiffrunner_sash():
	p = Prop("skiffrunner_sash", 1291)
	f, out, tan = _belt(p, SKY, CLOTH_WHITE, AMBER, R=0.56, h=0.3, grad=(0.1, 0.8), stripes=((-0.05, CLOTH_WHITE, 0.0), (0.05, CLOTH_WHITE, 0.0)))   # a sky-blue sash
	for k, (dx, ln) in enumerate(((-0.1, 0.62), (0.12, 0.5))):                             # knotted, its tails fluttering
		top = f + out * 0.06 + Vector((dx * 0.5, 0, -0.1))
		end = top + Vector((dx + 0.1, -0.06, -ln))
		w = Vector((0.08, 0, 0))
		p.poly([tuple(top - w), tuple(top + w), tuple(end + w * 1.3), tuple(end - w * 1.3)], [(0, 1, 2, 3)], SKY if k else RUNE, grad=(0.1, 0.9))
		for j in range(3):                                                                # tipped with little gold coins
			q = end + Vector((-0.1 + j * 0.1, -0.02, -0.06))
			p.seg(tuple(q + Vector((0, 0.02, 0))), tuple(q + Vector((0, -0.02, 0))), 0.05, 0.05, GOLD, sides=10, glow=0.5)
	return p.build()


def waderplume_cap():
	p = Prop("waderplume_cap", 1293)
	p.blob((0.9, 0.9, 0.7), (0, 0, 0.12), SEAFOAM, segs=(16, 10), grad=(0.1, 0.8))           # a soft sea-green cap
	p.seg((0, 0, -0.2), (0, 0, 0.0), 0.47, 0.46, SEAFOAM, sides=16, grad=(0.3, 0.9))
	p.seg((0, 0, -0.02), (0, 0, 0.08), 0.48, 0.47, AMBER, sides=16)                        # a reed-woven band
	p.seg((0, 0, -0.21), (0, 0, -0.19), 0.36, 0.36, STONE_DARK, sides=16)
	_vane(p, (0.3, -0.2, 0.1), (0.82, -0.2, 1.14), 0.14, PINK, tip_swatch=DAWN)             # a pink wader's plume
	_vane(p, (0.3, -0.16, 0.1), (0.44, -0.16, 1.02), 0.09, CLOTH_WHITE, tip_swatch=STONE_DARK)
	p.blob((0.12, 0.08, 0.12), (0.3, -0.26, 0.06), GOLD, segs=(8, 5), glow=0.6)
	return p.build()


def mask_of_the_reflection():
	p = Prop("mask_of_the_reflection", 1295)
	face = [(math.sin(math.radians(a)) * 0.44, 0.62 + math.cos(math.radians(a)) * 0.62) for a in range(0, 360, 20)]
	_slab(p, face, -0.02, 0.05, STONE_LIGHT, grad=(0.0, 0.35))                               # a flawless mirror mask
	for a, b in zip(face, face[1:] + face[:1]):                                           # rimmed in gold
		p.seg((a[0], -0.03, a[1]), (b[0], -0.03, b[1]), 0.035, 0.035, GOLD, sides=5)
	p.seg((0, -0.04, 0.76), (0, -0.12, 0.52), 0.05, 0.08, STONE_LIGHT, sides=5, grad=(0.0, 0.3))
	for sx in (-1, 1):
		p.blob((0.2, 0.04, 0.07), (sx * 0.17, -0.05, 0.8), SKY, segs=(8, 4), glow=2.4)         # eyes glowing sky blue
		_line(p, [(sx * 0.44, 0.0, 0.7), (sx * 0.62, -0.02, 0.55), (sx * 0.58, -0.02, 0.2)], 0.035, 0.03, CLOTH_WHITE, sides=5)   # white ribbons
	p.poly([(-0.3, -0.04, 1.02), (-0.1, -0.04, 1.16), (-0.02, -0.04, 1.08), (-0.26, -0.04, 0.92)], [(0, 1, 2, 3)], CLOTH_WHITE)   # a sheen
	p.seg((-0.14, -0.05, 0.34), (0.14, -0.05, 0.34), 0.025, 0.025, STONE_DARK, sides=4)
	return p.build()


def saltclaw_pearl_ring():
	p = Prop("saltclaw_pearl_ring", 1297)
	_ring(p, GOLD)
	for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):                                   # four white claws
		_line(p, [(sx * 0.08, sy * 0.06, 0.78), (sx * 0.2, sy * 0.14, 0.98), (sx * 0.12, sy * 0.08, 1.14)], 0.04, 0.0, BONE, sides=5)
	p.blob((0.5, 0.5, 0.5), (0, -0.06, 1.06), CLOTH_WHITE, segs=(12, 8), grad=(0.0, 0.6), glow=0.6)      # a big pearl
	p.blob((0.12, 0.04, 0.1), (-0.08, -0.3, 1.12), PINK, segs=(6, 4), glow=1.2)
	return p.build()


def asras_skiff_blade():
	p = Prop("asras_skiff_blade", 1299)
	org, rot = (-0.5, -0.4), 42
	curve = lambda s: 0.22 * ((s - 0.3) / 1.3) ** 2
	up = [(s, curve(s) + 0.11 * (1 - (s - 0.3) / 1.8)) for s in (0.3, 0.6, 0.9, 1.2, 1.45)]
	lo = [(s, curve(s) - 0.08) for s in (0.3, 0.6, 0.9, 1.2, 1.45)]
	outline = up + [(1.66, curve(1.66) + 0.06)] + lo[::-1]
	_slab(p, _rot2(outline, rot, org), -0.025, 0.025, STONE_LIGHT, grad=(0.0, 0.3))           # a slender curved saber
	e = _rot2([(s, curve(s) - 0.075) for s in (0.35, 0.8, 1.2, 1.45)] + [(1.64, curve(1.66) + 0.05)], rot, org)
	_line(p, [(x, -0.035, z) for x, z in e], 0.012, 0.008, CLOTH_WHITE, sides=4, glow=1.6)    # its honed edge
	g = _rot2([(0.3, 0.0)], rot, org)[0]
	p.seg((g[0], 0.03, g[1]), (g[0], -0.05, g[1]), 0.15, 0.15, CLAY, sides=12)               # a bronze disc guard
	h = _rot2([(0.26, 0.0), (-0.14, 0.0), (-0.2, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.05, 0.05, SKY, sides=6)             # a sky-blue wrapped grip
	p.blob((0.12, 0.12, 0.12), (h[2][0], 0, h[2][1]), CLAY, segs=(8, 5))
	_line(p, [(h[2][0], -0.04, h[2][1]), (h[2][0] - 0.02, -0.06, h[2][1] - 0.2), (h[2][0] + 0.06, -0.06, h[2][1] - 0.4)], 0.035, 0.05, RUNE, sides=5)   # a blue tassel
	p.blob((0.07, 0.07, 0.07), (h[2][0] - 0.01, -0.06, h[2][1] - 0.1), GOLD, segs=(6, 4))
	return p.build()


def rayspine_staff():
	p = Prop("rayspine_staff", 1301)
	org, rot = (-0.3, -0.7), 72
	_haft(p, org, rot, 0.0, 1.5, 0.06, swatch=BONE, bands=(0.3, 0.9, 1.4), band_swatch=HIDE)   # a staff of pale driftwood
	ray = [(1.4, 0.0), (1.66, 0.62), (1.84, 0.78), (1.98, 0.36), (2.14, 0.0), (1.98, -0.36), (1.84, -0.78), (1.66, -0.62)]
	_slab(p, _rot2(ray, rot, org), -0.04, 0.04, SEA_STONE, grad=(0.0, 0.8))                   # a sky ray's wings spread at the top
	belly = [(1.54, 0.0), (1.72, 0.4), (1.9, 0.28), (2.02, 0.0), (1.9, -0.28), (1.72, -0.4)]
	_slab(p, _rot2(belly, rot, org), -0.06, -0.04, CLOTH_WHITE, grad=(0.0, 0.6))
	sp = _rot2([(2.05, 0.0), (2.3, 0.03), (2.55, 0.0), (2.8, -0.04)], rot, org)            # and its long spine above
	_line(p, [(x, -0.02, z) for x, z in sp], 0.07, 0.0, BONE, sides=5)
	for k in range(3):
		q = _rot2([(2.18 + k * 0.17, 0.05), (2.22 + k * 0.17, 0.13)], rot, org)
		p.seg((q[0][0], -0.02, q[0][1]), (q[1][0], -0.02, q[1][1]), 0.025, 0.0, BONE, sides=4)
	c = _rot2([(1.8, 0.0)], rot, org)[0]
	p.blob((0.2, 0.08, 0.2), (c[0], -0.08, c[1]), SKY, segs=(8, 5), glow=2.2)                   # a sky-blue stone in its heart
	return p.build()


def barbel_whip_belt():
	p = Prop("barbel_whip_belt", 1303)
	f, out, tan = _belt(p, WOOD, HIDE, CLAY, R=0.58, h=0.22, grad=(0.1, 0.9))                 # a brown leather belt
	for k, a in enumerate((-110, -85, -40, -15)):                                          # long catfish barbels hanging off it like whips
		r = math.radians(a)
		q = Vector((0, 0.1, 0.4)) + Vector((math.cos(r), math.sin(r), 0)) * 0.6
		pts = [tuple(q + Vector((0.03 * math.sin(j * 1.3 + k) , -0.02 * j, -0.13 * j))) for j in range(6)]
		_line(p, pts, 0.05, 0.012, WOOD_GRAY, sides=6)
	for a in (-135, 10):                                                                  # bronze studs
		r = math.radians(a)
		p.blob((0.07, 0.07, 0.07), tuple(Vector((0, 0.1, 0.5)) + Vector((math.cos(r), math.sin(r), 0)) * 0.6), CLAY, segs=(6, 4))
	return p.build()


def hippohide_jerkin():
	p = Prop("hippohide_jerkin", 1305)
	_torso(p, CLAY, HIDE, grad=(0.1, 0.85), pauldrons=False, belt=WOOD)                     # a jerkin of thick ruddy hippo hide
	for sx in (-1, 1):                                                                    # thick gray hide over the shoulders
		p.blob((0.46, 0.62, 0.22), (sx * 0.38, 0, 0.86), STONE_WARM, rot=(0, sx * 28, 0), segs=(12, 6), grad=(0.1, 0.8))
		for k in range(3):                                                                # studded with bronze
			p.blob((0.05, 0.05, 0.05), (sx * (0.3 + k * 0.08), -0.24, 0.88 - k * 0.06), GOLD, segs=(6, 4))
	for sx in (-1, 1):                                                                    # a V opening, edged in dark hide
		p.seg(_front(sx * 0.16, 0.92, 0.0), _front(sx * 0.02, 0.5, 0.0), 0.03, 0.03, STONE_WARM, sides=4)
	for z in (0.56, 0.68, 0.8):                                                           # fastened with tusk toggles
		p.seg(_front(-0.1, z, 0.03), _front(0.1, z + 0.02, 0.03), 0.04, 0.03, BONE, sides=5)
	for (x, z) in ((-0.28, 0.4), (0.26, 0.3), (0.3, 0.56)):                              # old scars in the hide
		p.seg(_front(x - 0.06, z - 0.04, 0.0), _front(x + 0.06, z + 0.04, 0.0), 0.016, 0.016, PINK, sides=4)
	p.box((0.12, 0.06, 0.1), (0, -0.26, 0.1), GOLD)
	return p.build()


def pearl_crown_of_the_river():
	p = Prop("pearl_crown_of_the_river", 1307)
	_loop(p, (0, 0, 0.16), 0.48, True, 0.09, STONE_LIGHT, n=20)                             # a silver diadem
	for k in range(9):                                                                    # wave-shaped tines, each topped with a pearl
		a = math.radians(-90 + (k - 4) * 22)
		x, y = math.cos(a) * 0.48, math.sin(a) * 0.48
		h = 0.8 - abs(k - 4) * 0.08 + (0.14 if k == 4 else 0.0)
		_line(p, [(x, y, 0.16), (x * 1.03 + 0.07, y * 1.03, 0.16 + (h - 0.16) * 0.55), (x * 1.05, y * 1.05, h)], 0.07, 0.03, STONE_LIGHT, sides=5,
			  grad=(0.0, 0.5))
		p.blob((0.15, 0.15, 0.15), (x * 1.05, y * 1.05, h + 0.07), CLOTH_WHITE, segs=(8, 6), glow=0.7)
	for k in range(9):                                                                    # a strand of pearls hung below
		t = k / 8
		a = math.radians(-140 + t * 100)
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.04 - math.sin(t * math.pi) * 0.16), CLOTH_WHITE, segs=(6, 4), glow=0.5)
	p.blob((0.26, 0.12, 0.32), (0, -0.54, 0.3), WATER, segs=(8, 6), glow=1.8)                 # a river-blue stone
	return _tip_back(p.build(), -22)


def mudcharm_bracelet():
	p = Prop("mudcharm_bracelet", 1309)
	t0, t1, r0, r1 = -0.24, 0.24, 0.3, 0.28
	p.seg(_fa(t0), _fa(t1), r0, r1, WOOD, sides=16, grad=(0.2, 0.9))                        # a leather cuff
	for t in (t0, t1 - 0.05):
		p.seg(_fa(t), _fa(t + 0.05), _fa_r(t, r0, r1, t0, t1) + 0.025, _fa_r(t, r0, r1, t0, t1) + 0.025, LEAF, sides=16)   # bound in green reed
	for k, (t, ang) in enumerate(((-0.1, -35), (0.1, 5), (-0.02, 50))):                   # big mud charms tied on
		r = _fa_r(t, r0, r1, t0, t1)
		c = _fa(t, r + 0.1, ang)
		p.seg(_fa(t, r, ang), c, 0.02, 0.02, HIDE, sides=4)
		p.seg(tuple(Vector(c) + Vector((0, 0.04, 0))), tuple(Vector(c) + Vector((0, -0.06, 0))), 0.19, 0.17, CLAY, sides=12, grad=(0.1, 0.9), jitter=0.01)
		sp = []
		for j in range(12):                                                               # each pressed with a spiral
			u = j / 11
			a = u * math.tau * 1.6
			sp.append((c[0] + math.cos(a) * 0.13 * u, c[1] - 0.07, c[2] + math.sin(a) * 0.13 * u))
		_line(p, sp, 0.014, 0.02, WOOD, sides=4)
	p.seg(_fa(t1), _fa(t1 + 0.01), 0.22, 0.22, STONE_DARK, sides=16)                          # the empty wrist
	return p.build()


def shellmask_amulet():
	p = Prop("shellmask_amulet", 1311)
	_cord(p, 0.46, 1.0, HIDE)                                                              # a hide cord
	_scallop(p, (0, -0.3, -0.05), 0.56, AMBER, CLAY, eyes=CLOTH_WHITE, glow=1.4)            # a scallop-shell face
	for sx in (-1, 1):
		p.blob((0.12, 0.12, 0.12), (sx * 0.24, -0.3, 0.62), SEAFOAM, segs=(6, 4))
	p.seg((0, -0.3, 0.52), (0, -0.3, 0.66), 0.03, 0.03, HIDE, sides=4)
	return p.build()


def serpentscale_gloves():
	p, fr = _glove_pair("serpentscale_gloves", 1313, LEAF, WOOD, AMBER, grad=(0.45, 1.0))    # dark green scaled gloves
	for f in fr:
		pts = []
		for row, z in enumerate((0.44, 0.56, 0.68)):                                      # scales over the back of the hand
			for k in range(3 - row % 2):
				pts.append(f(-0.14 + k * 0.14 + (0.07 if row % 2 else 0.0), -0.13, z))
		_scales(p, pts, [PINE, AMBER, PINE])
		for z in (0.12, 0.24):                                                            # banded cuff
			p.seg(f(0, 0, z), f(0, 0, z + 0.04), 0.23, 0.23, AMBER, sides=12)
	return p.build()


def coilmother_fang_dirk():
	p = Prop("coilmother_fang_dirk", 1315)
	org, rot = (-0.55, -0.35), 48
	curve = lambda s: -0.2 * ((s - 0.3) / 1.1) ** 2
	up = [(s, curve(s) + 0.14 * (1 - (s - 0.3) / 1.15)) for s in (0.3, 0.55, 0.8, 1.05, 1.25)]
	lo = [(s, curve(s) - 0.14 * (1 - (s - 0.3) / 1.15)) for s in (0.3, 0.55, 0.8, 1.05, 1.25)]
	outline = up + [(1.42, curve(1.42) - 0.02)] + lo[::-1]
	_slab(p, _rot2(outline, rot, org), -0.04, 0.04, BONE, grad=(0.0, 0.6))                    # a blade that is a great curved fang
	g = _rot2([(s, curve(s)) for s in (0.36, 0.7, 1.0, 1.25)], rot, org)
	_line(p, [(x, -0.05, z) for x, z in g], 0.022, 0.01, LEAF, sides=4, glow=2.0)             # venom down its groove
	c = _rot2([(0.28, 0.0)], rot, org)[0]
	for sgn in (1, -1):                                                                   # the guard: two coiled serpents
		pts = [_rot2([(0.3 - 0.06 * math.sin(k * 0.9), sgn * (0.06 + k * 0.05))], rot, org)[0] for k in range(6)]
		_line(p, [(x, -0.02, z) for x, z in pts], 0.05, 0.035, TEAL, sides=6)
		p.blob((0.09, 0.07, 0.07), (pts[-1][0], -0.03, pts[-1][1]), TEAL, segs=(6, 4))
		p.blob((0.03, 0.02, 0.03), (pts[-1][0], -0.08, pts[-1][1] + 0.02), GOLD, segs=(4, 3), glow=2.0)
	h = _rot2([(0.22, 0.0), (-0.2, 0.0), (-0.28, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.06, PINE, sides=6)           # a scaled green grip
	for t in (0.2, 0.45, 0.7, 0.95):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.015, 0, q[1] - 0.015), (q[0] + 0.015, 0, q[1] + 0.015), 0.066, 0.066, TEAL, sides=6)
	p.blob((0.14, 0.13, 0.14), (h[2][0], 0, h[2][1]), LEAF, segs=(8, 5), glow=1.2)             # a venom-green pommel stone
	tip = _rot2([(1.42, curve(1.42) - 0.04)], rot, org)[0]
	p.blob((0.08, 0.06, 0.1), (tip[0] + 0.02, -0.04, tip[1] - 0.1), LEAF, segs=(6, 4), glow=2.2)
	return p.build()


def blackwater_cutlass():
	p = Prop("blackwater_cutlass", 1317)
	org, rot = (-0.5, -0.4), 44
	curve = lambda s: 0.1 * (s - 0.3) ** 2
	up = [(0.3, 0.1), (0.7, 0.12), (1.05, 0.15), (1.28, 0.17)]
	outline = [(s, z + curve(s)) for s, z in up] + [(1.42, 0.1 + curve(1.42)), (1.52, -0.04 + curve(1.52))] + \
			  [(s, curve(s) - 0.09) for s in (1.3, 0.9, 0.5, 0.3)]
	_slab(p, _rot2(outline, rot, org), -0.03, 0.03, IRON, grad=(0.0, 0.6))                    # a broad blackened cutlass
	e = _rot2([(s, curve(s) - 0.085) for s in (0.35, 0.7, 1.0, 1.3)] + [(1.5, curve(1.5) - 0.03)], rot, org)
	_line(p, [(x, -0.04, z) for x, z in e], 0.02, 0.014, STONE_LIGHT, sides=4, glow=0.4)       # a bright honed edge
	arc = [(0.3 - 0.54 * t, -0.1 - 0.22 * math.sin(math.pi * t)) for t in [k / 8 for k in range(9)]]
	for off in (0.0, 0.07):                                                               # a brass basket hilt
		pts = _rot2([(s, w - off * math.sin(math.pi * k / 8)) for k, (s, w) in enumerate(arc)], rot, org)
		_line(p, [(x, -0.02 - off, z) for x, z in pts], 0.03, 0.03, GOLD, sides=5)
	g = _rot2([(0.3, -0.14), (0.3, 0.16)], rot, org)
	p.seg((g[0][0], 0, g[0][1]), (g[1][0], 0, g[1][1]), 0.05, 0.05, GOLD, sides=6)
	h = _rot2([(0.28, 0.0), (-0.22, 0.0), (-0.28, 0.0)], rot, org)
	p.seg((h[0][0], 0.02, h[0][1]), (h[1][0], 0.02, h[1][1]), 0.05, 0.055, STONE_DARK, sides=6)   # a tarred grip
	p.blob((0.13, 0.13, 0.13), (h[2][0], 0.02, h[2][1]), GOLD, segs=(8, 5))
	return p.build()


def reaver_armring_band():
	p = Prop("reaver_armring_band", 1319)
	_twist_ring(p, (0, 0, 0.42), (1, 0, 0), (0, 0, 1), 0.4, 0.06, (STONE_LIGHT, IRON), turns=8)   # a twisted silver band
	p.seg((0, 0.02, 0.86), (0, -0.1, 0.86), 0.16, 0.14, GOLD, sides=10)                       # a garnet in a gold setting
	p.blob((0.2, 0.12, 0.2), (0, -0.14, 0.88), CLOTH_RED, segs=(10, 6), glow=1.6)
	return p.build()


def saltbeards_axe():
	p = Prop("saltbeards_axe", 1321)
	org, rot = (-0.5, -0.5), 60
	_haft(p, org, rot, -0.1, 1.6, 0.065, swatch=BONE, bands=(0.1, 0.45, 1.05), band_swatch=HIDE)   # a haft of whalebone, rope-bound
	_slab(p, _rot2(AXE_BLADE, rot, org), -0.05, 0.05, IRON, grad=(0.0, 0.6))                   # a bearded iron head
	_line(p, [(x, -0.06, z) for x, z in _rot2([(x + 0.01, z) for x, z in AXE_EDGE], rot, org)], 0.024, 0.024, STONE_LIGHT, sides=4, glow=0.3)
	hook = _rot2([(1.18, 0.02), (1.4, 0.02), (1.36, 0.22), (1.22, 0.36), (1.26, 0.2)], rot, org)   # a hooked back like a gaff
	_slab(p, hook, -0.04, 0.04, IRON, grad=(0.0, 0.6))
	for s in (1.14, 1.2):                                                                 # rope lashing the head
		q0, q1 = _rot2([(s, -0.12), (s, 0.12)], rot, org)
		p.seg((q0[0], -0.07, q0[1]), (q1[0], -0.07, q1[1]), 0.025, 0.025, HIDE, sides=4)
	e = _rot2([(-0.12, 0.0)], rot, org)[0]                                                  # a whale's tail carved at the butt
	tail = [(e[0], e[1]), (e[0] - 0.22, e[1] - 0.04), (e[0] - 0.12, e[1] - 0.12), (e[0] + 0.04, e[1] - 0.12), (e[0] + 0.1, e[1] - 0.26), (e[0] + 0.14, e[1] - 0.06)]
	_slab(p, tail, -0.04, 0.04, BONE, grad=(0.0, 0.7))
	return p.build()


def clawfolk_carapace_shield():
	p = Prop("clawfolk_carapace_shield", 1323)
	c = (0, 0.66)
	oval = [(math.cos(math.radians(a)) * 0.58, c[1] + math.sin(math.radians(a)) * 0.72) for a in range(0, 360, 20)]
	_slab(p, oval, -0.08, 0.06, PETAL_PURPLE, grad=(0.0, 0.9))                               # an oval of purple carapace
	for a, b in zip(oval, oval[1:] + oval[:1]):
		p.seg((a[0], -0.09, a[1]), (b[0], -0.09, b[1]), 0.04, 0.04, STONE_DARK, sides=4)
	for z in (0.28, 1.04):                                                                # segment ridges
		w = math.sqrt(max(1 - ((z - c[1]) / 0.72) ** 2, 0)) * 0.56
		_line(p, [(-w, -0.09, z), (0, -0.12, z + (0.05 if z > c[1] else -0.05)), (w, -0.09, z)], 0.035, 0.035, SEA_STONE, sides=4)
	for k in range(9):                                                                    # spines round the rim
		a = math.radians(k * 40 + 10)
		p.seg((math.cos(a) * 0.56, -0.02, c[1] + math.sin(a) * 0.7), (math.cos(a) * 0.74, -0.02, c[1] + math.sin(a) * 0.9), 0.05, 0.0, BONE, sides=4)
	p.blob((0.4, 0.2, 0.3), (0, -0.14, 0.62), PETAL_PURPLE, segs=(10, 6), grad=(0.0, 0.7))    # a clawfolk pincer mounted across it
	_line(p, [(0.14, -0.2, 0.7), (0.34, -0.22, 0.82), (0.48, -0.22, 0.74)], 0.08, 0.02, PETAL_PURPLE, sides=6, grad=(0.0, 0.7))
	_line(p, [(0.14, -0.2, 0.54), (0.34, -0.22, 0.46), (0.46, -0.22, 0.56)], 0.07, 0.02, PETAL_PURPLE, sides=6, grad=(0.0, 0.7))
	for (x, z) in ((-0.3, 0.9), (-0.3, 0.4), (0.3, 1.0), (0.0, 1.14), (-0.1, 0.2)):         # sea-green spots
		p.blob((0.07, 0.03, 0.07), (x, -0.1, z), AQUA, segs=(6, 4), glow=0.5)
	return p.build()


def lure_of_the_deep():
	p = Prop("lure_of_the_deep", 1325)
	_cord(p, 0.46, 0.92, STONE_DARK)                                                       # a dark cord
	c = (0, -0.3, 0.32)
	p.blob((0.3, 0.3, 0.3), c, SEAFOAM, segs=(12, 8), glow=2.8)                               # a glowing deep-sea lure
	p.blob((0.12, 0.08, 0.12), (c[0], c[1] - 0.12, c[2] + 0.02), CLOTH_WHITE, segs=(6, 4), glow=3.2)
	for k in range(6):                                                                    # caged in needle teeth
		a = k * math.tau / 6
		top = (c[0] + math.cos(a) * 0.05, c[1] + math.sin(a) * 0.05, c[2] + 0.26)
		mid = (c[0] + math.cos(a) * 0.24, c[1] + math.sin(a) * 0.24, c[2])
		bot = (c[0] + math.cos(a) * 0.06, c[1] + math.sin(a) * 0.06, c[2] - 0.26)
		_line(p, [top, mid, bot], 0.025, 0.005, BONE, sides=4)
	p.seg((0, -0.3, 0.58), (0, -0.3, 0.72), 0.04, 0.03, CRIMSON, sides=5)                    # on a curl of its stalk
	return p.build()


def serpentskin_leggings():
	p = Prop("serpentskin_leggings", 1327)
	_trousers(p, LEAF, WOOD, leg_r=0.2, flare=0.02)
	for x in (-1, 1):                                                                     # scaled down each leg
		pts = []
		for row, z in enumerate((0.64, 0.52, 0.4, 0.28, 0.16)):
			for k in range(2):
				pts.append((x * (0.2 + (z - 0.72) * -0.1) + (k - 0.5) * 0.14 + (0.07 if row % 2 else 0.0), -0.2, z))
		_scales(p, pts, [PINE, AMBER, PINE, PINE])
		p.seg((x * 0.24, 0, 0.08), (x * 0.245, 0, -0.02), 0.23, 0.24, AMBER, sides=10)       # yellow-banded cuffs
	p.box((0.1, 0.06, 0.08), (0, -0.15, 1.0), GOLD)
	return p.build()


def whitefin_cloak():
	p = Prop("whitefin_cloak", 1329)
	_slab(p, _cape_outline(0.3, 0.64, 0.14), 0.04, 0.1, SEA_STONE, grad=(0.0, 0.8))         # a cape of blue-gray sharkskin
	_slab(p, [(-0.3, 1.0), (0.3, 1.0), (0.2, 0.4), (0.0, 0.1), (-0.2, 0.4)], 0.0, 0.04, CLOTH_WHITE, grad=(0.0, 0.5))   # Whitefin's pale hide down its back
	fin = [(0.0, 0.3), (0.0, 0.8), (-0.52, 1.02), (-0.36, 0.78), (-0.18, 0.5)]             # his great white fin standing out from it
	for x in (-0.02, 0.02):
		p.poly([(x, y, z) for y, z in fin], [tuple(range(len(fin)))], CLOTH_WHITE, grad=(0.0, 0.5))
	_line(p, [(0.03, -0.52, 1.02), (0.03, -0.36, 0.78), (0.03, -0.18, 0.5), (0.03, 0.0, 0.3)], 0.02, 0.02, ASH, sides=4, grad=(0.5, 0.6))
	for (x0, z0, x1, z1) in ((-0.5, 0.3, -0.34, 0.45), (0.36, 0.2, 0.5, 0.4)):            # old scars
		p.seg((x0, 0.02, z0), (x1, 0.02, z1), 0.02, 0.02, STONE_DARK, sides=4)
	for k in range(5):                                                                    # a collar of shark teeth
		x = -0.24 + k * 0.12
		p.seg((x, -0.02, 1.0), (x, -0.06, 0.86), 0.045, 0.0, BONE, sides=4)
	return p.build()


def gullfeather_boots():
	p = Prop("gullfeather_boots", 1331)
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, WOOD_GRAY, CLOTH_WHITE, STONE_DARK, grad=(0.1, 0.8), shaft=0.7)   # gray sea boots
		for k, dx in enumerate((-0.12, 0.02, 0.15)):                                      # white gull feathers tucked in the cuff
			_vane(p, (ox + dx * 0.6, oy - r - 0.04, 0.66), (ox + dx * 2.2, oy - r - 0.06, 1.2 - abs(dx)), 0.07, CLOTH_WHITE, tip_swatch=STONE_DARK)
	return p.build()


def tempest_heart_staff():
	p = Prop("tempest_heart_staff", 1333)
	org, rot = (-0.3, -0.7), 72
	_haft(p, org, rot, 0.0, 1.62, 0.06, swatch=STONE_DARK, bands=(0.3, 0.9, 1.5), band_swatch=STONE_LIGHT)   # a dark haft, silver banded
	c = _rot2([(1.98, 0.0)], rot, org)[0]
	p.blob((0.46, 0.4, 0.46), (c[0], 0, c[1]), STONE_DARK, segs=(12, 8))                      # the storm heart
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.22, 0.2, 0.2), (c[0] + math.cos(a) * 0.22, -0.04, c[1] + math.sin(a) * 0.22), ASH, segs=(8, 5), grad=(0.3, 0.9))
	p.blob((0.2, 0.1, 0.2), (c[0], -0.22, c[1]), SKY, segs=(8, 5), glow=3.0)
	base = _rot2([(1.62, 0.0)], rot, org)[0]
	for sgn in (-1, 1):                                                                   # silver prongs holding it
		pts = [(base[0], 0, base[1]), (c[0] + sgn * 0.34, -0.05, c[1] - 0.1), (c[0] + sgn * 0.28, -0.05, c[1] + 0.26), (c[0] + sgn * 0.08, -0.03, c[1] + 0.38)]
		_line(p, pts, 0.05, 0.02, STONE_LIGHT, sides=6)
	for a in (30, 150, 250):                                                              # lightning crackling off it
		r = math.radians(a)
		d = Vector((math.cos(r), 0, math.sin(r)))
		n = Vector((-d.z, 0, d.x))
		q = Vector((c[0], -0.24, c[1]))
		_zap(p, [tuple(q + d * 0.1), tuple(q + d * 0.3 + n * 0.08), tuple(q + d * 0.42 - n * 0.06), tuple(q + d * 0.6)], r=0.025)
	return p.build()


# ---------------------------------------------------------------- the Standing Sky: Galehold, Windbreak and the Long Grass
# The wind god Vayuketh's country: pale blue, white and ochre, streaming banners.
# Skyforged plate is bright steel enameled pale blue and worked with wings,
# Windrunner tan leather striped blue and hung with feathers, Galeweave white
# cloth embroidered with sky-blue swirls. Windbreak's drops are bottled wind,
# eagle and thunderbird parts, kite silk and painted stone; the Long Grass's are
# tawny hide, horn, horsehair and green-patinated barrow bronze.

OCHRE = ORANGE         # orange-yellow: the plains' ochre paint
BRONZE = AMBER         # gold-brown: old bronze
PATINA = SEAFOAM       # sea green: verdigris on barrow bronze


def _flat(y):
	"""Maps (x, z[, off]) on a plane facing the camera at depth y into the scene."""
	return lambda x, z, off=0.0: (x, y - off, z)


def _tangent(a, r, cx=0.0, cy=0.0):
	"""Maps (u, z[, off]) onto the plane touching a round surface of radius r at angle a (degrees)."""
	ang = math.radians(a)
	ca, sa = math.cos(ang), math.sin(ang)
	return lambda u, z, off=0.0: (cx + ca * (r + off) - sa * u, cy + sa * (r + off) + ca * u, z)


FRONT_A = -61          # the angle round a vertical surface that faces the camera


def _wing(p, to3, c, s, sx, sw, arm=None, n=5, lift=30, glow=0.0):
	"""A spread wing: an arm from c out to side sx, rising `lift` degrees, and n flat
	feathers hanging from it, longest at the tip. (x, z) points go through to3."""
	a = math.radians(lift)
	d = Vector((sx * math.cos(a), math.sin(a)))
	fd = Vector((sx * math.sin(a), -math.cos(a)))
	arm_pts = []
	for k in range(n + 1):
		t = k / n
		q = Vector(c) + d * s * t - fd * s * 0.08 * math.sin(math.pi * t)
		arm_pts.append(q)
	for k in range(n, 0, -1):                                                         # outer feathers behind inner ones
		t = k / n
		base = arm_pts[k] - d * s * 0.04
		f = (fd * (1 - 0.5 * t) + d * 0.5 * t).normalized()
		pn = Vector((-f.y, f.x))
		ln, w = s * (0.34 + 0.42 * t), s * 0.24
		pts = [base + pn * w * 0.5, base + f * ln * 0.75 + pn * w * 0.5, base + f * ln, base + f * ln * 0.75 - pn * w * 0.5, base - pn * w * 0.5]
		off = 0.004 * (n - k)
		p.poly([to3(q.x, q.y, off) for q in pts], [tuple(range(5))], sw, grad=(0.0, 0.5))
	_line(p, [to3(q.x, q.y, 0.03) for q in arm_pts], s * 0.06, s * 0.03, arm or sw, sides=5, grad=(0.0, 0.5), glow=glow)


def _swirl(p, to3, c, r, sw, turns=1.5, w=0.022, sx=1, glow=0.0, n=24, off=0.0, start=0.0):
	"""A spiral from c winding out to radius r: embroidery, wind, a storm's eye."""
	pts = []
	for k in range(n + 1):
		t = k / n
		ang = start + sx * t * turns * math.tau
		rr = r * (0.12 + 0.88 * t)
		pts.append(to3(c[0] + math.cos(ang) * rr, c[1] + math.sin(ang) * rr, off))
	_line(p, pts, w * 0.5, w, sw, sides=4, grad=(0.0, 0.5), glow=glow)


def _gust(p, to3, start, length, sw, curl=0.1, w=0.024, wave=0.035, glow=0.0, off=0.0, sx=1):
	"""A wind stroke: a gentle wave running along x (sx) that ends curling up."""
	x0, z0 = start
	pts = [(x0 + sx * length * k / 8, z0 + wave * math.sin(k / 8 * math.tau)) for k in range(9)]
	ex, ez = pts[-1]
	cz = ez + curl
	for k in range(1, 11):
		ang = -math.pi / 2 + k * 1.45 * math.pi / 10
		rr = curl * (1 - k * 0.05)
		pts.append((ex + sx * math.cos(ang) * rr, cz + math.sin(ang) * rr))
	_line(p, [to3(x, z, off) for x, z in pts], w, w * 0.7, sw, sides=4, grad=(0.0, 0.5), glow=glow)


def _streamer(p, to3, start, d, length, width, sw, waves=1.3, amp=0.09, n=14, tip_sw=None, stripe=None):
	"""A ribbon streaming from start along d, rippling, as a flat strip; forked at its end."""
	d = Vector(d).normalized()
	nrm = Vector((-d.y, d.x))
	rows = []
	for k in range(n + 1):
		t = k / n
		c = Vector(start) + d * length * t + nrm * amp * math.sin(t * waves * math.tau) * (0.3 + t)
		w = width * (1 - 0.3 * t)
		rows.append((c + nrm * w / 2, c - nrm * w / 2, c))
	for k in range(n):
		a0, a1, _ = rows[k]
		b0, b1, bc = rows[k + 1]
		sw_k = tip_sw if tip_sw and k >= n - 3 else sw
		if k == n - 1:                                                                # a swallowtail
			p.poly([to3(a0.x, a0.y), to3(b0.x, b0.y), to3(bc.x, bc.y, 0.001), to3(b1.x, b1.y), to3(a1.x, a1.y)], [(0, 1, 2, 3, 4)], sw_k, grad=(0.1, 0.7))
		else:
			p.poly([to3(a0.x, a0.y), to3(b0.x, b0.y), to3(b1.x, b1.y), to3(a1.x, a1.y)], [(0, 1, 2, 3)], sw_k, grad=(0.1, 0.7))
		if stripe and k < n - 1:
			p.seg(to3(rows[k][2].x, rows[k][2].y, 0.004), to3(bc.x, bc.y, 0.004), width * 0.12, width * 0.12, stripe, sides=4)


def _blade_frame(rot, org, y=-0.04):
	"""to3 for a weapon's picture-plane frame: (u along the blade, v across it)."""
	def to3(u, v, off=0.0):
		q = _rot2([(u, v)], rot, org)[0]
		return (q[0], y - off, q[1])
	return to3


def _handprint(p, to3, c, s, sw=OCHRE, glow=0.0):
	"""A painted handprint, fingers up: palm, four fingers and a thumb."""
	x, z = c
	p.blob((0.36 * s, 0.03, 0.34 * s), to3(x, z), sw, segs=(10, 6), grad=(0.0, 0.5), glow=glow)
	for k, (dx, ln) in enumerate(((-0.13, 0.26), (-0.045, 0.33), (0.045, 0.34), (0.13, 0.28))):
		p.seg(to3(x + dx * s, z + 0.12 * s, 0.002), to3(x + dx * 1.3 * s, z + (0.12 + ln) * s, 0.002), 0.045 * s, 0.04 * s, sw, sides=6,
			  grad=(0.0, 0.5), glow=glow)
	p.seg(to3(x + 0.16 * s, z - 0.02 * s, 0.002), to3(x + 0.34 * s, z + 0.14 * s, 0.002), 0.05 * s, 0.042 * s, sw, sides=6, grad=(0.0, 0.5), glow=glow)


# Galehold's Skyforged plate

def skyforged_helm():
	p = Prop("skyforged_helm", 1401)
	for z0, z1, r0, r1 in ((0.0, 0.3, 0.42, 0.42), (0.3, 0.52, 0.42, 0.34), (0.52, 0.68, 0.34, 0.2), (0.68, 0.76, 0.2, 0.0)):
		p.seg((0, 0, z0), (0, 0, z1), r0, r1, STONE_LIGHT, sides=16, grad=(0.0, 0.45))       # a bright steel dome
	_loop(p, (0, 0, 0.3), 0.425, True, 0.05, SKY, n=18)                                       # bands of pale-blue enamel
	_loop(p, (0, 0, 0.03), 0.425, True, 0.035, SKY, n=18)
	p.seg((0, -0.42, 0.34), (0, -0.46, -0.1), 0.06, 0.045, STONE_LIGHT, sides=5, grad=(0.0, 0.45))   # a nasal
	for k in range(9):                                                                    # an enameled crest ridge
		a0, a1 = math.radians(-70 + k * 17), math.radians(-70 + (k + 1) * 17)
		p.seg((0, math.sin(a0) * 0.44, 0.3 + math.cos(a0) * 0.46), (0, math.sin(a1) * 0.44, 0.3 + math.cos(a1) * 0.46), 0.05, 0.05, SKY, sides=5)
	for sx in (-1, 1):                                                                    # white wings rising from its sides
		_wing(p, _flat(-0.06), (sx * 0.36, 0.3), 0.62, sx, CLOTH_WHITE, arm=STONE_LIGHT, lift=62, n=5)
		p.blob((0.12, 0.08, 0.12), (sx * 0.38, -0.2, 0.3), SKY, segs=(8, 5), glow=1.0)
	return p.build()


def skyforged_breastplate():
	p = Prop("skyforged_breastplate", 1403)
	_torso(p, STONE_LIGHT, SKY, grad=(0.0, 0.45))
	p.seg(_front(0, 0.2, 0.0), _front(0, 0.52, 0.0), 0.035, 0.03, STONE_LIGHT, sides=5)          # a raised keel
	fr = lambda x, z, off=0.0: _front(x, z, 0.05 + off)
	for sx in (-1, 1):                                                                    # white wings spread across the chest
		_wing(p, fr, (sx * 0.08, 0.64), 0.42, sx, CLOTH_WHITE, arm=SKY, lift=24)
	c = _front(0, 0.66, 0.05)
	p.seg((c[0], c[1] + 0.04, c[2]), (c[0], c[1] - 0.03, c[2]), 0.11, 0.11, SKY, sides=14, glow=0.6)   # a pale-blue enamel boss
	p.blob((0.1, 0.05, 0.1), (c[0], c[1] - 0.04, c[2]), CLOTH_WHITE, segs=(6, 4), glow=1.2)
	_line(p, [_front(-0.44 + k * 0.088, 0.36, 0.0) for k in range(11)], 0.024, 0.024, SKY, sides=4)   # an enamel band
	for k in range(5):
		p.blob((0.05, 0.04, 0.05), (-0.3 + k * 0.15, -0.24 - 0.05 * (1 - abs(k - 2) / 2), 0.1), STONE_LIGHT, segs=(6, 4))
	return p.build()


def _fa_to3(t, r, ang=-10):
	"""to3 on the forearm's surface at t: u along the arm, v across it."""
	c = Vector(_fa(t, r, ang))
	d = FA_D
	nrm = Vector((-d.z, 0, d.x))
	return lambda u, v, off=0.0: tuple(c + d * u + nrm * v + Vector((0, -1, 0)) * off)


def skyforged_vambraces():
	p = Prop("skyforged_vambraces", 1405)
	t0, t1, r0, r1 = _vambrace(p, STONE_LIGHT, SKY, HIDE, STONE_LIGHT, grad=(0.0, 0.45))
	to3 = _fa_to3(0.0, _fa_r(0.0, r0, r1, t0, t1) + 0.03)
	for sx in (-1, 1):                                                                    # a white wing along it
		_wing(p, to3, (sx * 0.03, 0.02), 0.26, sx, CLOTH_WHITE, arm=SKY, lift=25, n=4)
	p.blob((0.09, 0.06, 0.09), to3(0, 0.02, 0.03), SKY, segs=(6, 4), glow=1.4)
	return p.build()


def skyforged_gauntlets():
	p, fr = _glove_pair("skyforged_gauntlets", 1407, STONE_LIGHT, SKY, STONE_LIGHT, grad=(0.0, 0.45), style="gauntlet")
	for f in fr:                                                                          # a small wing on the back of each
		to3 = lambda x, z, off=0.0, f=f: f(x, -0.17 - off, z)
		for sx in (-1, 1):
			_wing(p, to3, (sx * 0.02, 0.5), 0.2, sx, CLOTH_WHITE, arm=SKY, lift=30, n=4)
		p.blob((0.08, 0.05, 0.08), f(0, -0.2, 0.52), SKY, segs=(6, 4), glow=1.4)
	return p.build()


def skyforged_greaves():
	p = Prop("skyforged_greaves", 1409)
	_trousers(p, STONE_LIGHT, SKY, leg_r=0.21, flare=0.03)
	for x in (-1, 1):
		for z in (0.62, 0.4, 0.16):                                                       # plate bands edged in blue enamel
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.05), 0.235, 0.24, STONE_LIGHT, sides=12, grad=(0.0, 0.45))
			p.seg((x * 0.21, 0, z - 0.055), (x * 0.212, 0, z - 0.075), 0.242, 0.242, SKY, sides=12)
		p.blob((0.24, 0.14, 0.22), (x * 0.21, -0.18, 0.3), STONE_LIGHT, segs=(8, 6), grad=(0.0, 0.45))   # knee cop
		for sx in (-1, 1):                                                                # winged
			_wing(p, _flat(-0.27), (x * 0.21 + sx * 0.03, 0.31), 0.18, sx, CLOTH_WHITE, arm=SKY, lift=30, n=3)
	p.box((0.1, 0.06, 0.1), (0, -0.15, 1.0), CLOTH_WHITE)
	return p.build()


def skyforged_boots():
	p = Prop("skyforged_boots", 1411)
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, STONE_LIGHT, SKY, STONE_DARK, grad=(0.0, 0.45), shaft=0.72, r=0.22)
		p.blob((0.32, 0.4, 0.26), (ox - 0.38, oy, 0.15), STONE_LIGHT, segs=(10, 6), grad=(0.0, 0.45))   # a toe cap
		_loop(p, (ox + 0.01, oy, 0.4), r + 0.02, True, 0.022, SKY, n=16)
		_wing(p, _flat(oy - r - 0.05), (ox + 0.08, 0.5), 0.36, 1, CLOTH_WHITE, arm=SKY, lift=38, n=4)   # a wing at the heel
	return p.build()


def skyforged_shield():
	p = Prop("skyforged_shield", 1413)
	outline = [(-0.5, 1.28), (0.0, 1.38), (0.5, 1.28), (0.48, 0.8), (0.32, 0.36), (0.0, -0.12), (-0.32, 0.36), (-0.48, 0.8)]
	_slab(p, outline, -0.05, 0.06, SKY, grad=(0.0, 0.5))                                      # a kite shield enameled pale blue
	for a, b in zip(outline, outline[1:] + outline[:1]):                                  # a bright steel rim
		p.seg((a[0], -0.06, a[1]), (b[0], -0.06, b[1]), 0.055, 0.055, STONE_LIGHT, sides=6, grad=(0.0, 0.45))
	for sx in (-1, 1):                                                                    # white wings across it
		_wing(p, _flat(-0.07), (sx * 0.08, 0.86), 0.42, sx, CLOTH_WHITE, arm=STONE_LIGHT, lift=22)
	p.seg((0, -0.06, 0.86), (0, -0.18, 0.86), 0.14, 0.12, STONE_LIGHT, sides=12, grad=(0.0, 0.45))   # a steel boss
	p.blob((0.12, 0.08, 0.12), (0, -0.19, 0.86), SKY, segs=(8, 5), glow=1.4)
	_line(p, [(0, -0.07, 0.62), (0, -0.07, 0.0)], 0.04, 0.02, STONE_LIGHT, sides=5)             # a steel point down the tail
	return p.build()


# Windrunner leather

def windrunner_jerkin():
	p = Prop("windrunner_jerkin", 1415)
	_torso(p, HIDE, WOOD, grad=(0.1, 0.8), pauldrons=False, belt=WOOD)
	for sx in (-1, 1):                                                                    # leather shoulder caps
		p.blob((0.4, 0.58, 0.16), (sx * 0.38, 0, 0.86), WOOD, rot=(0, sx * 28, 0), segs=(12, 6), grad=(0.1, 0.7))
	fr = lambda x, z, off=0.0: _front(x, z, 0.005 + off)
	for k, z in enumerate((0.3, 0.5, 0.7)):                                               # blue wind-stripes sweeping across
		_gust(p, fr, (-0.4 + 0.06 * k, z), 0.6 - 0.08 * k, SKY, curl=0.07, w=0.032, wave=0.03)
	for k in range(4):                                                                    # laced
		z = 0.2 + k * 0.1
		p.seg(_front(-0.06, z, 0.0), _front(0.06, z + 0.05, 0.0), 0.012, 0.012, WOOD, sides=4)
	p.box((0.12, 0.06, 0.1), (0, -0.26, 0.1), STONE_LIGHT)                                    # buckle
	p.seg((0.28, -0.3, 0.86), (0.3, -0.32, 0.74), 0.015, 0.015, WOOD, sides=4)              # feathers tied at the shoulder
	_vane(p, (0.3, -0.33, 0.76), (0.36, -0.33, 0.3), 0.08, CLOTH_WHITE, tip_swatch=SKY)
	_vane(p, (0.3, -0.35, 0.76), (0.46, -0.35, 0.38), 0.065, OCHRE, tip_swatch=CLOTH_WHITE)
	return p.build()


def windrunner_leggings():
	p = Prop("windrunner_leggings", 1417)
	_trousers(p, HIDE, WOOD)
	for x in (-1, 1):
		for dx in (-0.06, 0.06):                                                          # blue stripes down each leg
			pts = [(x * (0.17 + 0.07 * t) + dx + 0.025 * math.sin(t * 9), -0.205 - 0.01 * t, 0.7 - 0.66 * t) for t in (k / 10 for k in range(11))]
			_line(p, pts, 0.022, 0.022, SKY, sides=4)
		p.blob((0.2, 0.1, 0.16), (x * 0.2, -0.2, 0.38), WOOD, segs=(8, 5))                  # knee pads
		p.seg((x * 0.38, -0.12, 0.44), (x * 0.4, -0.2, 0.4), 0.014, 0.014, WOOD, sides=4)
		_vane(p, (x * 0.4, -0.24, 0.42), (x * 0.47, -0.24, 0.04), 0.07, CLOTH_WHITE, tip_swatch=SKY)   # a feather at each knee
	p.box((0.1, 0.06, 0.08), (0, -0.15, 1.0), STONE_LIGHT)
	return p.build()


def windrunner_gloves():
	p, fr = _glove_pair("windrunner_gloves", 1419, HIDE, WOOD, SKY, grad=(0.1, 0.8))
	for f in fr:
		to3 = lambda x, z, off=0.0, f=f: f(x, -0.135 - off, z)
		for z in (0.44, 0.58):                                                            # wind-stripes across the back
			_gust(p, to3, (-0.2, z), 0.3, SKY, curl=0.04, w=0.022, wave=0.02)
	f = fr[1]                                                                             # a feather hung from the front cuff
	p.seg(f(0.22, -0.24, 0.12), f(0.26, -0.26, 0.02), 0.012, 0.012, WOOD, sides=4)
	_vane(p, f(0.26, -0.28, 0.04), f(0.36, -0.28, -0.4), 0.08, CLOTH_WHITE, tip_swatch=SKY)
	return p.build()


def windrunner_boots():
	p = Prop("windrunner_boots", 1421)
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, HIDE, WOOD, WOOD, shaft=0.76)
		to3 = _flat(oy - r - 0.01)
		for z in (0.36, 0.56):                                                            # blue wind-stripes round the shin
			_gust(p, to3, (ox - 0.15, z), 0.24, SKY, curl=0.04, w=0.024, wave=0.02)
		p.seg((ox + 0.2, oy - 0.16, 0.84), (ox + 0.24, oy - 0.24, 0.74), 0.012, 0.012, WOOD, sides=4)   # a feather at the cuff
		_vane(p, (ox + 0.24, oy - r - 0.06, 0.76), (ox + 0.34, oy - r - 0.06, 0.36), 0.07, CLOTH_WHITE, tip_swatch=SKY)
	return p.build()


# Galeweave cloth

def galeweave_cap():
	p = Prop("galeweave_cap", 1423)
	_cap_cone(p, CLOTH_WHITE, SKY, [(0, 0.14, 0.41), (0.04, 0.42, 0.34), (0.16, 0.66, 0.22), (0.36, 0.8, 0.1)], grad=(0.0, 0.6))   # a soft white cap
	for k, a in enumerate((FRONT_A - 26, FRONT_A + 20)):                                    # sky-blue swirls stitched on it
		_swirl(p, _tangent(a, 0.36), (0.0, 0.33), 0.09, SKY, turns=1.6, w=0.024, sx=1 if k else -1)
	for k in range(9):                                                                    # white waves on the band
		a = math.radians(FRONT_A - 60 + k * 15)
		p.blob((0.07, 0.07, 0.05), (math.cos(a) * 0.44, math.sin(a) * 0.44, 0.08 + 0.03 * (k % 2)), CLOTH_WHITE, segs=(6, 4))
	p.blob((0.14, 0.14, 0.14), (0.4, 0, 0.8), SKY, segs=(8, 5))                                # a tassel at the tip
	p.seg((0.42, 0, 0.78), (0.5, -0.02, 0.5), 0.05, 0.02, SKY, sides=5)
	return p.build()


def galeweave_robe():
	p = Prop("galeweave_robe", 1425)
	rz = lambda z: 0.62 + (0.34 - 0.62) * (z + 0.5) / 1.45
	p.seg((0, 0, -0.5), (0, 0, 0.95), 0.62, 0.34, CLOTH_WHITE, sides=20, grad=(0.0, 0.6))   # a long white robe
	p.blob((0.98, 0.56, 0.34), (0, 0, 0.92), CLOTH_WHITE, segs=(14, 8), grad=(0.0, 0.5))
	for sx in (-1, 1):                                                                    # wide sleeves, cuffed in blue
		p.seg((sx * 0.4, 0, 0.92), (sx * 0.66, 0, 0.2), 0.14, 0.25, CLOTH_WHITE, sides=12, grad=(0.0, 0.6))
		p.seg((sx * 0.66, 0, 0.2), (sx * 0.69, 0, 0.12), 0.26, 0.27, SKY, sides=12)
		p.seg((sx * 0.69, 0, 0.12), (sx * 0.695, 0, 0.11), 0.2, 0.2, STONE_DARK, sides=12)
	p.seg((0, 0, 0.98), (0, 0, 1.1), 0.21, 0.25, SKY, sides=14)                               # a blue collar
	p.seg((0, 0, 1.095), (0, 0, 1.105), 0.17, 0.17, STONE_DARK, sides=14)
	p.seg((0, 0, 0.42), (0, 0, 0.52), rz(0.42) + 0.02, rz(0.52) + 0.02, SKY, sides=20)         # a blue sash
	_streamer(p, _tangent(FRONT_A + 10, rz(0.45) + 0.03), (0.05, 0.44), (0.35, -1), 0.5, 0.1, SKY, amp=0.04, n=8)
	p.seg((0, -rz(0.95), 0.95), (0, -rz(-0.5), -0.5), 0.035, 0.035, SKY, sides=5)             # the opening, trimmed
	p.seg((0, 0, -0.5), (0, 0, -0.4), 0.635, 0.63, SKY, sides=20)                              # a blue hem
	for k in range(6):                                                                    # swirls embroidered above it
		a = FRONT_A - 55 + k * 22
		_swirl(p, _tangent(a, rz(-0.2) + 0.012), (0.0, -0.22), 0.1, SKY, turns=1.5, w=0.024, sx=1 if k % 2 else -1)
	for sx in (-1, 1):
		_swirl(p, _flat(-0.3), (sx * 0.4, 0.62), 0.06, SKY, turns=1.4, w=0.018, sx=sx)
	return p.build()


def galeweave_gloves():
	p, fr = _glove_pair("galeweave_gloves", 1427, CLOTH_WHITE, SKY, SKY, grad=(0.0, 0.6))
	for f in fr:                                                                          # a blue swirl on the back of each
		to3 = lambda x, z, off=0.0, f=f: f(x, -0.135 - off, z)
		_swirl(p, to3, (0.0, 0.53), 0.14, SKY, turns=1.7, w=0.026)
	return p.build()


def _gale_slipper(p, ox, oy):
	p.blob((0.7, 0.36, 0.3), (ox, oy, 0.15), CLOTH_WHITE, segs=(14, 8), grad=(0.0, 0.6))      # a soft white slipper, toe to the left
	p.seg((ox + 0.14, oy, 0.2), (ox + 0.14, oy, 0.3), 0.17, 0.18, SKY, sides=14)
	p.seg((ox + 0.14, oy, 0.3), (ox + 0.14, oy, 0.305), 0.14, 0.14, STONE_DARK, sides=14)
	pts = [(ox - 0.3, oy, 0.1), (ox - 0.44, oy, 0.16), (ox - 0.5, oy, 0.28), (ox - 0.44, oy, 0.38)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):                                        # its curled toe
		p.seg(a, b, 0.1 - i * 0.03, 0.07 - i * 0.03, CLOTH_WHITE, sides=8, grad=(0.0, 0.6))
	p.blob((0.09, 0.09, 0.09), pts[-1], SKY, segs=(6, 4))
	p.blob((0.74, 0.38, 0.05), (ox, oy, 0.01), SKY, segs=(12, 4), grad=(0.3, 0.9))
	_swirl(p, _flat(oy - 0.17), (ox - 0.04, 0.16), 0.09, SKY, turns=1.5, w=0.022)


def galeweave_slippers():
	p = Prop("galeweave_slippers", 1429)
	_gale_slipper(p, -0.2, 0.3)
	_gale_slipper(p, 0.3, -0.12)
	return p.build()


# Skyforged weapons, the Zephyr Dirk, the Stormwood Staff, the Galehold Longbow

def skyforged_sword():
	p = Prop("skyforged_sword", 1431)
	org, rot = (-0.55, -0.42), 48
	up = [(0.32, 0.1), (0.8, 0.11), (1.2, 0.1), (1.44, 0.06)]
	tip = (1.6, 0.0)
	outline = up + [tip] + [(x, -z) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.035, 0.035, STONE_LIGHT, grad=(0.0, 0.4))          # a bright steel blade
	bf = _blade_frame(rot, org, -0.04)
	p.seg(bf(0.4, 0.0), bf(1.3, 0.0), 0.028, 0.012, SKY, sides=4, glow=0.8)                   # a pale-blue fuller
	for sgn in (1, -1):
		_line(p, [bf(x, sgn * (z - 0.012), 0.005) for x, z in up[1:]] + [bf(tip[0] - 0.02, 0.0, 0.005)], 0.01, 0.01, CLOTH_WHITE, sides=4)
		_wing(p, lambda x, z, off=0.0: bf(0.3 + z, x, off), (sgn * 0.05, 0.0), 0.36, sgn, CLOTH_WHITE, arm=SKY, lift=35, n=4)   # a guard of swept wings
	h = _rot2([(0.26, 0.0), (-0.12, 0.0), (-0.2, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.06, SKY, sides=6)            # a blue-wrapped grip
	for t in (0.25, 0.55, 0.85):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.02, 0, q[1] - 0.02), (q[0] + 0.02, 0, q[1] + 0.02), 0.068, 0.068, CLOTH_WHITE, sides=6)
	p.blob((0.16, 0.16, 0.16), (h[2][0], 0, h[2][1]), STONE_LIGHT, segs=(8, 6), grad=(0.0, 0.45))
	p.blob((0.08, 0.05, 0.08), (h[2][0], -0.08, h[2][1]), SKY, segs=(6, 4), glow=1.8)
	return p.build()


def skyforged_war_axe():
	p = Prop("skyforged_war_axe", 1433)
	org, rot = (-0.5, -0.5), 60
	_haft(p, org, rot, -0.1, 1.6, 0.06, swatch=WOOD, bands=(0.1, 0.5, 1.1), band_swatch=STONE_LIGHT)
	_slab(p, _rot2(AXE_BLADE, rot, org), -0.05, 0.05, STONE_LIGHT, grad=(0.0, 0.42))           # a bright steel head
	bf = _blade_frame(rot, org, -0.055)
	_line(p, [bf(x + 0.01, z) for x, z in AXE_EDGE], 0.022, 0.022, CLOTH_WHITE, sides=4, glow=0.6)   # a keen white edge
	_wing(p, lambda x, z, off=0.0: bf(1.0 + x, -0.3 + z, off), (0.0, 0.0), 0.5, 1, SKY, arm=CLOTH_WHITE, lift=12, n=4)   # an enameled wing
	spike = _rot2([(1.18, 0.0), (1.4, 0.0), (1.3, 0.32)], rot, org)
	_slab(p, spike, -0.04, 0.04, STONE_LIGHT, grad=(0.0, 0.5))
	c = _rot2([(1.28, -0.06)], rot, org)[0]
	p.seg((c[0], 0.06, c[1]), (c[0], -0.07, c[1]), 0.08, 0.08, STONE_LIGHT, sides=8)
	p.blob((0.06, 0.04, 0.06), (c[0], -0.08, c[1]), SKY, segs=(6, 4), glow=1.8)
	_streamer(p, _blade_frame(rot, org, -0.07), (0.05, 0.0), (-0.3, -1), 0.65, 0.17, SKY, tip_sw=CLOTH_WHITE)   # a pennant streaming off the haft
	return p.build()


def skyforged_greataxe():
	p = Prop("skyforged_greataxe", 1435)
	org, rot = (-0.5, -0.7), 62
	_haft(p, org, rot, -0.2, 2.0, 0.065, swatch=WOOD, bands=(0.0, 0.4, 0.8, 1.2), band_swatch=STONE_LIGHT)
	bf = _blade_frame(rot, org, -0.055)
	for sgn in (1, -1):                                                                   # a double-bitted steel head
		blade = [(x + 0.1, sgn * z) for x, z in AXE_BLADE]
		_slab(p, _rot2(blade, rot, org), -0.05, 0.05, STONE_LIGHT, grad=(0.0, 0.42))
		_line(p, [bf(x + 0.11, sgn * z) for x, z in AXE_EDGE], 0.024, 0.024, CLOTH_WHITE, sides=4, glow=0.6)
		_wing(p, lambda x, z, off=0.0, sgn=sgn: bf(1.12 + x, sgn * (-0.3 + z), off), (0.0, 0.0), 0.48, 1, SKY, arm=CLOTH_WHITE, lift=12, n=4)
	top = _rot2([(1.5, -0.07), (1.5, 0.07), (1.92, 0.0)], rot, org)
	_slab(p, top, -0.04, 0.04, STONE_LIGHT, grad=(0.0, 0.5))
	c = _rot2([(1.4, 0.0)], rot, org)[0]
	p.seg((c[0], 0.07, c[1]), (c[0], -0.08, c[1]), 0.1, 0.1, STONE_LIGHT, sides=8)
	p.blob((0.08, 0.05, 0.08), (c[0], -0.09, c[1]), SKY, segs=(6, 4), glow=1.8)
	for k, sw in enumerate((SKY, CLOTH_WHITE)):                                            # twin pennants under the head
		_streamer(p, _blade_frame(rot, org, -0.08 - 0.01 * k), (1.08, 0.08 - 0.16 * k), (-1, -0.25 + 0.5 * k), 0.65, 0.15, sw, amp=0.06, n=10)
	return p.build()


def zephyr_dirk():
	p = Prop("zephyr_dirk", 1437)
	org, rot = (-0.5, -0.35), 48
	up = [(0.3, 0.08), (0.55, 0.13), (0.8, 0.12), (1.02, 0.08), (1.2, 0.04)]
	tip = (1.34, 0.0)
	outline = up + [tip] + [(x, -z * 0.8) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.035, 0.035, STONE_LIGHT, grad=(0.0, 0.4))          # a slim leaf-bladed dirk
	bf = _blade_frame(rot, org, -0.04)
	_swirl(p, lambda x, z, off=0.0: bf(0.52 + x, z, off), (0.0, 0.0), 0.085, SKY, turns=1.6, w=0.018, glow=1.4)   # a swirl etched in it
	_line(p, [bf(0.62, 0.0), bf(1.2, 0.0)], 0.018, 0.006, SKY, sides=4, glow=1.4)
	for sgn in (1, -1):                                                                   # the guard: two curls of wind
		_swirl(p, lambda x, z, off=0.0, sgn=sgn: bf(0.27 + z, sgn * (0.13 + x), off), (0.0, 0.0), 0.1, STONE_LIGHT, turns=1.2, w=0.04, sx=-sgn,
			   start=math.pi)
	_line(p, [bf(0.3, -0.2, -0.04), bf(0.3, 0.2, -0.04)], 0.045, 0.045, STONE_LIGHT, sides=6)
	h = _rot2([(0.26, 0.0), (-0.14, 0.0), (-0.22, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.048, 0.052, CLOTH_WHITE, sides=6)    # a white-wrapped grip
	for t in (0.2, 0.5, 0.8):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.015, 0, q[1] - 0.015), (q[0] + 0.015, 0, q[1] + 0.015), 0.058, 0.058, SKY, sides=6)
	p.blob((0.13, 0.13, 0.13), (h[2][0], 0, h[2][1]), STONE_LIGHT, segs=(8, 6))
	_vane(p, (h[2][0], -0.06, h[2][1] - 0.04), (h[2][0] + 0.12, -0.06, h[2][1] - 0.5), 0.07, CLOTH_WHITE, tip_swatch=SKY)   # a feather on a thong
	for k in range(2):                                                                    # a breath of wind along it
		_gust(p, lambda x, z, off=0.0: bf(x, z, 0.02 + off), (0.45 + 0.15 * k, 0.26 + 0.1 * k), 0.5, CLOTH_WHITE, curl=0.05, w=0.014, wave=0.02,
			  glow=0.8)
	return p.build()


def stormwood_staff():
	p = Prop("stormwood_staff", 1439)
	org, rot = (-0.3, -0.7), 72
	_haft(p, org, rot, 0.0, 1.6, 0.06, swatch=WOOD_GRAY, bands=(0.3, 0.9), band_swatch=SKY)   # pale storm-struck wood
	bf = _blade_frame(rot, org, -0.06)
	_line(p, [bf(0.4, 0.0), bf(0.55, 0.03), bf(0.62, -0.02), bf(0.8, 0.02)], 0.012, 0.012, SKY, sides=4, glow=1.8)   # a lightning scar
	c = _rot2([(1.95, 0.0)], rot, org)[0]
	p.seg((c[0], 0, c[1] - 0.36), (c[0], 0, c[1]), 0.0, 0.24, SKY, sides=6, grad=(0.0, 0.5), glow=1.6)   # a crackling blue gem
	p.seg((c[0], 0, c[1]), (c[0], 0, c[1] + 0.36), 0.24, 0.0, SKY, sides=6, grad=(0.0, 0.5), glow=1.6)
	p.blob((0.2, 0.1, 0.24), (c[0], -0.2, c[1]), CLOTH_WHITE, segs=(8, 5), glow=3.0)
	base = _rot2([(1.6, 0.0)], rot, org)[0]
	for sgn in (-1, 1, 0):                                                                # gnarled branches cradling it
		y = -0.05 if sgn else 0.22
		pts = [(base[0], y * 0.3, base[1]), (c[0] + sgn * 0.34 - 0.06, y, c[1] - 0.12), (c[0] + sgn * 0.3 - 0.04, y, c[1] + 0.22),
			   (c[0] + sgn * 0.08, y * 0.5, c[1] + 0.4)]
		_line(p, pts, 0.055, 0.02, WOOD_GRAY, sides=6)
	for a in (15, 100, 170, 250, 320):                                                    # lightning crackling off it
		r = math.radians(a)
		d, n = Vector((math.cos(r), 0, math.sin(r))), Vector((-math.sin(r), 0, math.cos(r)))
		q = Vector((c[0], -0.26, c[1]))
		_zap(p, [tuple(q + d * 0.22), tuple(q + d * 0.36 + n * 0.08), tuple(q + d * 0.46 - n * 0.06), tuple(q + d * 0.62)], r=0.022,
			 sw=CLOTH_WHITE if a % 2 else SKY)
	return p.build()


def galehold_longbow():
	p = Prop("galehold_longbow", 1441)
	org, rot = (0.0, 0.6), 50
	pts = []
	for k in range(17):                                                                   # a long limb of pale ash, recurved at the tips
		t = -1 + k / 8
		w = 0.3 * (1 - t * t) - 0.08 * max(0.0, abs(t) - 0.75) / 0.25
		pts.append((t * 1.1, w))
	lp = _rot2(pts, rot, org)
	for i, (a, b) in enumerate(zip(lp, lp[1:])):
		mid = abs(i - 7.5) / 8
		r = 0.075 - mid * 0.04
		p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), r, r, BONE, sides=6, grad=(0.3, 0.9))
	for k in (2, 5, 11, 14):                                                              # pale-blue bands along the limbs
		q0, q1 = lp[k], lp[k + 1]
		mid = abs(k - 7.5) / 8
		p.seg((q0[0], 0, q0[1]), ((q0[0] + q1[0]) / 2, 0, (q0[1] + q1[1]) / 2), 0.085 - mid * 0.04, 0.085 - mid * 0.04, SKY, sides=6)
	for k in (0, 16):                                                                     # steel-capped tips
		j = 1 if k == 0 else 15
		p.seg((lp[k][0], 0, lp[k][1]), (lp[j][0], 0, lp[j][1]), 0.05, 0.045, STONE_LIGHT, sides=6)
	g0, g1 = lp[7], lp[9]
	p.seg((g0[0], 0, g0[1]), (g1[0], 0, g1[1]), 0.09, 0.09, SKY, sides=8)                     # a blue-wrapped grip
	for q in (g0, g1):
		p.seg((q[0] - 0.02, 0, q[1] - 0.02), (q[0] + 0.02, 0, q[1] + 0.02), 0.1, 0.1, CLOTH_WHITE, sides=8)
	p.seg((lp[0][0], 0.02, lp[0][1]), (lp[16][0], 0.02, lp[16][1]), 0.012, 0.012, CLOTH_WHITE, sides=4)   # the string
	gm = lp[8]
	for k, sw in enumerate((SKY, CLOTH_WHITE)):                                            # ribbons streaming from the grip
		_streamer(p, _flat(-0.1 - 0.01 * k), (gm[0] - 0.02, gm[1]), (1, -0.55 - 0.35 * k), 0.75, 0.08, sw, amp=0.06, n=10, tip_sw=OCHRE)
	return p.build()


def windcutter_arrow():
	p = Prop("windcutter_arrow", 1443)
	a, b = (-0.6, 0, 0.05), (0.5, 0, 0.95)
	p.seg(a, b, 0.035, 0.035, BONE, sides=6, grad=(0.2, 0.8))                              # a pale shaft
	d = (Vector(b) - Vector(a)).normalized()
	n = Vector((-d.z, 0, d.x))
	tipv = Vector(b) + d * 0.3
	head = [Vector(b) - d * 0.02 + n * 0.1, tipv, Vector(b) - d * 0.02 - n * 0.1, Vector(b) + d * 0.06]   # a crescent-backed steel head
	p.poly([tuple(v + Vector((0, -0.02, 0))) for v in (head[0], head[3], tipv)], [(0, 1, 2)], STONE_LIGHT, grad=(0.0, 0.45))
	p.poly([tuple(v + Vector((0, -0.02, 0))) for v in (head[2], tipv, head[3])], [(0, 1, 2)], STONE_LIGHT, grad=(0.0, 0.45))
	p.seg(tuple(Vector(b) + d * 0.04), tuple(tipv), 0.05, 0.0, STONE_LIGHT, sides=4, grad=(0.0, 0.4))
	p.seg((0.44, 0, 0.9), (0.51, 0, 0.96), 0.055, 0.055, SKY, sides=6)
	p.seg(tuple(Vector(a) + d * 0.36), tuple(Vector(a) + d * 0.4), 0.045, 0.045, SKY, sides=6)
	for off, sw in (((-d.z, 0, d.x), SKY), ((d.z, 0, -d.x), CLOTH_WHITE), ((0, -1, 0), SKY)):   # blue and white fletching
		nn = Vector(off) * 0.13
		root, tip = Vector(a) + d * 0.04, Vector(a) + d * 0.3
		p.poly([tuple(root), tuple(tip), tuple(tip - d * 0.06 + nn), tuple(root + nn * 0.9)], [(0, 1, 2, 3)], sw)
	p.seg((-0.62, 0, 0.02), (-0.58, 0, 0.06), 0.04, 0.04, SKY, sides=5)
	_gust(p, _flat(-0.08), (-0.2, 0.62), 0.42, CLOTH_WHITE, curl=0.06, w=0.014, wave=0.02, glow=1.0)   # cutting the wind
	return p.build()


# Windbreak's drops

def gale_essence():
	p = Prop("gale_essence", 1451)
	p.blob((0.78, 0.78, 0.86), (0, 0, 0.43), SKY, segs=(14, 10), grad=(0.0, 0.4))              # a pale-blue glass flask
	top = _potion(p, 0.82, neck=0.22, neck_r=0.09, cork=WOOD)
	p.blob((0.26, 0.26, 0.14), (0, 0, top + 0.14), OCHRE, segs=(8, 5))                         # sealed with ochre wax
	_swirl(p, _flat(-0.4), (0.0, 0.43), 0.3, CLOTH_WHITE, turns=1.8, w=0.04, glow=1.2)          # a gale whirling inside
	_swirl(p, _flat(-0.41), (0.02, 0.45), 0.16, CLOTH_WHITE, turns=1.3, w=0.025, glow=1.6, start=2.0)
	for k in range(2):                                                                    # a wisp slipping past the seal
		_gust(p, _flat(-0.1), (0.08 + 0.05 * k, top + 0.28 + 0.14 * k), 0.26 - 0.06 * k, CLOTH_WHITE, curl=0.05, w=0.018, wave=0.02, glow=1.0)
	_frame(p, *POTION_FRAME)
	return p.build()


def eagle_talon():
	p = Prop("eagle_talon", 1453)
	toe = [(-0.62, 0, 0.08), (-0.3, 0, 0.2), (0.0, 0, 0.3), (0.12, 0, 0.36)]
	_line(p, toe, 0.2, 0.15, OCHRE, sides=10, grad=(0.1, 0.8))                               # a yellow, scaled toe
	for k in range(4):
		x = -0.5 + k * 0.16
		z = 0.12 + (x + 0.62) * 0.36
		p.seg((x - 0.02, 0, z - 0.01), (x + 0.02, 0, z + 0.01), 0.19 - k * 0.01, 0.19 - k * 0.01, AMBER, sides=10)
	claw = [(0.1, 0, 0.36), (0.34, 0, 0.52), (0.56, 0, 0.5), (0.72, 0, 0.32), (0.72, 0, 0.1)]
	_line(p, claw, 0.15, 0.0, IRON, sides=8, grad=(0.0, 0.5))                                # a great hooked black talon
	p.seg((0.3, -0.12, 0.5), (0.6, -0.08, 0.46), 0.02, 0.01, STONE_LIGHT, sides=4)            # its shine
	for k in range(5):                                                                    # a ruff of feathers where it was cut off
		a = math.radians(-60 + k * 30)
		_vane(p, (-0.6, -0.06, 0.1), (-0.6 - math.cos(a) * 0.45, -0.06 - 0.01 * k, 0.1 + math.sin(a) * 0.45), 0.09,
			  CLOTH_WHITE if k % 2 else HIDE)
	return p.build()


def thunder_feather():
	p = Prop("thunder_feather", 1455)
	_vane(p, (-0.35, 0, 0.0), (0.4, 0, 1.25), 0.26, WATER, tip_swatch=CLOTH_WHITE, bars=(0.3, 0.5), glow=1.4)   # a storm-blue feather
	for pts in (((-0.3, 0.35), (-0.46, 0.5), (-0.38, 0.62), (-0.56, 0.8)), ((0.2, 0.62), (0.42, 0.58), (0.38, 0.76), (0.6, 0.8)),
				((0.36, 1.2), (0.48, 1.3), (0.44, 1.42))):                                   # lightning crackling off it
		_zap(p, [(x, -0.06, z) for x, z in pts], r=0.024, sw=CLOTH_WHITE)
	_zap(p, [(-0.05, -0.06, 0.4), (0.05, -0.06, 0.55), (-0.02, -0.06, 0.62), (0.1, -0.06, 0.8)], r=0.02, sw=SKY)
	return p.build()


def kite_silk():
	p = Prop("kite_silk", 1457)
	c = (0.0, 0.6)
	corners = [(0.0, 1.3), (0.52, 0.72), (0.0, -0.1), (-0.52, 0.72)]
	for k, sw in enumerate((SKY, OCHRE, CLOTH_WHITE, CLOTH_RED)):                          # a scrap of kite silk in four panels
		a, b = corners[k], corners[(k + 1) % 4]
		_slab(p, [c, a, b], 0.0, 0.02, sw, grad=(0.1, 0.6))
	for k in range(4):                                                                    # stitched seams
		a, b = corners[k], corners[(k + 1) % 4]
		p.seg((c[0], -0.01, c[1]), (a[0], -0.01, a[1]), 0.012, 0.012, CLOTH_WHITE, sides=4)
		for j in range(5):                                                                # a frayed edge
			t = (j + 0.5) / 5
			q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
			out = Vector((q[0] - c[0], q[1] - c[1])).normalized()
			p.seg((q[0], 0.0, q[1]), (q[0] + out.x * 0.07, -0.005, q[1] + out.y * 0.07), 0.012, 0.004, CLOTH_WHITE, sides=3)
	_swirl(p, _flat(-0.012), (0.0, 0.6), 0.14, CLOTH_WHITE, turns=1.5, w=0.02)               # a painted swirl
	_streamer(p, _flat(-0.01), (0.0, -0.08), (0.4, -1), 0.6, 0.08, SKY, amp=0.08, n=10, tip_sw=OCHRE)   # a torn tail ribbon
	return _tip_back(p.build(), -15)


def giants_standing_stone():
	p = Prop("giants_standing_stone", 1459)
	p.blob((0.9, 0.56, 1.1), (0, 0, 0.55), STONE_WARM, segs=(14, 10), grad=(0.05, 0.8), jitter=0.025)   # a smooth, heavy river stone
	mf = lambda x, z, off=0.0: (x, -0.28 * math.sqrt(max(1 - (x / 0.45) ** 2 - ((z - 0.55) / 0.55) ** 2, 0.0)) - 0.005 - off, z)
	_handprint(p, mf, (-0.02, 0.36), 1.25)                                                   # a giant's handprint in ochre
	for k in range(4):                                                                    # dots of blue round it
		a = math.radians(30 + k * 40)
		p.blob((0.07, 0.03, 0.07), mf(0.28 * math.cos(a) + 0.02, 0.42 + 0.34 * math.sin(a), 0.0), SKY, segs=(6, 4))
	return p.build()


# the Long Grass's drops

def stalker_pelt():
	p = Prop("stalker_pelt", 1461)
	p.blob((1.2, 0.8, 0.12), (0, 0, 0.06), AMBER, segs=(12, 6), grad=(0.0, 0.5), jitter=0.04)      # a tawny pelt
	for x in (-1, 1):                                                                     # legs of the hide
		p.blob((0.3, 0.22, 0.1), (x * 0.44, 0.34, 0.05), AMBER, segs=(6, 4), grad=(0.0, 0.5))
		p.blob((0.3, 0.22, 0.1), (x * 0.44, -0.34, 0.05), AMBER, segs=(6, 4), grad=(0.0, 0.5))
	for k in range(6):                                                                    # faint dark stripes across it
		x = -0.42 + k * 0.17
		p.seg((x - 0.04, -0.28, 0.12), (x + 0.04, 0.0, 0.13), 0.035, 0.025, WOOD, sides=4)
		p.seg((x + 0.04, 0.0, 0.13), (x - 0.02, 0.28, 0.12), 0.025, 0.02, WOOD, sides=4)
	_line(p, [(0.58, 0.0, 0.06), (0.8, 0.1, 0.08), (0.95, 0.3, 0.1), (0.98, 0.5, 0.1)], 0.07, 0.05, AMBER, sides=6)   # its tail
	p.blob((0.14, 0.14, 0.14), (0.98, 0.54, 0.1), STONE_DARK, segs=(6, 4))
	p.blob((0.34, 0.3, 0.14), (-0.66, 0, 0.08), AMBER, segs=(8, 5))                           # the head end, ears up
	for sy in (-1, 1):
		p.seg((-0.7, sy * 0.1, 0.12), (-0.8, sy * 0.14, 0.24), 0.06, 0.0, WOOD, sides=4)
	return p.build()


def thunderhoof_horn():
	p = Prop("thunderhoof_horn", 1463)
	pts = [(-0.45, 0, 0.1), (-0.1, 0, 0.16), (0.25, 0, 0.34), (0.44, 0, 0.66), (0.4, 0, 0.98), (0.24, 0, 1.14)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):                                        # a thick, upswept hoofbeast horn
		r0 = 0.24 - i * 0.045
		p.seg(a, b, r0, max(r0 - 0.045, 0.0) if i < 4 else 0.0, STONE_WARM if i < 2 else STONE_DARK, sides=10, grad=(0.1, 0.8))
		if i < 3:                                                                         # rough growth ridges
			p.seg(b, tuple(b[j] + (pts[i + 2][j] - b[j]) * 0.12 for j in range(3)), r0 - 0.035, r0 - 0.05, WOOD_GRAY, sides=10)
	p.blob((0.46, 0.44, 0.4), (-0.52, 0, 0.1), WOOD_GRAY, segs=(10, 6), jitter=0.03)          # a shaggy scrap of its brow
	_zap(p, [(0.3, -0.2, 0.6), (0.42, -0.2, 0.7), (0.34, -0.2, 0.78), (0.46, -0.2, 0.9)], r=0.02, sw=CLOTH_WHITE, glow=2.0)   # a static spark
	return p.build()


def horsetail_braid():
	p = Prop("horsetail_braid", 1465)
	path = [Vector((0.3, 0, 1.25)), Vector((0.12, 0, 0.95)), Vector((0.05, 0, 0.62)), Vector((-0.1, 0, 0.35))]
	pts = []
	for k in range(15):                                                                   # a thick braid of dark horsehair
		t = k / 14
		i = min(int(t * 3), 2)
		u = t * 3 - i
		pts.append(path[i] + (path[i + 1] - path[i]) * u)
	for k, q in enumerate(pts):
		d = (pts[min(k + 1, 14)] - pts[max(k - 1, 0)]).normalized()
		n = Vector((-d.z, 0, d.x))
		side = 1 if k % 2 else -1
		p.blob((0.2, 0.16, 0.13), tuple(q + n * 0.05 * side), WOOD_GRAY if k % 2 else STONE_DARK, rot=(0, math.degrees(math.atan2(d.x, d.z)) + side * 30, 0),
			   segs=(8, 5), grad=(0.1, 0.8))
	p.seg(tuple(path[0] + Vector((0.03, 0, 0.1))), tuple(path[0] - Vector((0.02, 0, 0.06))), 0.12, 0.12, OCHRE, sides=8)   # bound with ochre cord
	p.blob((0.12, 0.12, 0.12), tuple(path[0] + Vector((0.06, -0.1, 0.02))), SKY, segs=(6, 4), glow=0.6)
	_strands(p, 1465, 11, (-0.1, 0, 0.36), 0.28, 0.5, [STONE_DARK, WOOD_GRAY], STONE_DARK, 0.0)       # the loose tail
	p.seg((-0.13, 0, 0.3), (-0.08, 0, 0.42), 0.1, 0.1, OCHRE, sides=8)
	return p.build()


def barrow_bronze():
	p = Prop("barrow_bronze", 1467)
	outline = [(-0.72, 0.98), (-0.34, 0.82), (0.34, 0.82), (0.72, 0.98), (0.56, 0.52), (0.72, 0.06), (0.34, 0.22), (-0.34, 0.22), (-0.72, 0.06),
			   (-0.56, 0.52)]
	_slab(p, outline, -0.07, 0.07, BRONZE, grad=(0.1, 0.9))                                   # an old oxhide ingot of bronze
	for a, b in zip(outline, outline[1:] + outline[:1]):
		p.seg((a[0], -0.075, a[1]), (b[0], -0.075, b[1]), 0.02, 0.02, AMBER, sides=4, grad=(0.3, 1.0))
	for x, z, s in ((-0.44, 0.78, 0.2), (0.4, 0.3, 0.26), (0.5, 0.82, 0.14), (-0.3, 0.3, 0.12)):   # green patina
		p.blob((s, 0.04, s * 0.8), (x, -0.075, z), PATINA, segs=(8, 4), grad=(0.0, 0.6), jitter=0.01)
	_swirl(p, _flat(-0.08), (0.0, 0.53), 0.17, WOOD, turns=2.0, w=0.022)                      # a spiral stamped in it
	return _tip_back(p.build(), -12)


# the named drops

def storm_eye_heart():
	p = Prop("storm_eye_heart", 1471)
	p.seg((0, 0.06, 0.6), (0, -0.02, 0.6), 0.62, 0.62, WATER, sides=24, grad=(0.3, 1.0))     # a storm seen from above, flattened to a disc
	for j in range(3):                                                                    # its three arms of cloud whirling in
		for k in range(12):
			t = k / 11
			ang = j * math.tau / 3 + t * 2.4
			rr = 0.6 - 0.46 * t
			s = 0.26 - 0.13 * t
			p.blob((s, 0.08, s * 0.7), (math.cos(ang) * rr, -0.06 - 0.01 * t, 0.6 + math.sin(ang) * rr), CLOTH_WHITE if k % 3 else ASH,
				   rot=(0, -math.degrees(ang), 0), segs=(8, 5), grad=(0.0, 0.6))
	p.blob((0.2, 0.1, 0.2), (0, -0.1, 0.6), SKY, segs=(10, 6), glow=3.0)                        # the calm, bright eye
	p.blob((0.09, 0.06, 0.09), (0, -0.14, 0.6), CLOTH_WHITE, segs=(6, 4), glow=3.4)
	for a in (40, 160, 280):                                                              # lightning at its rim
		r = math.radians(a)
		d, n = Vector((math.cos(r), 0, math.sin(r))), Vector((-math.sin(r), 0, math.cos(r)))
		q = Vector((0, -0.12, 0.6))
		_zap(p, [tuple(q + d * 0.5), tuple(q + d * 0.62 + n * 0.06), tuple(q + d * 0.7 - n * 0.04), tuple(q + d * 0.84)], r=0.024)
	return p.build()


def skarrows_crest():
	p = Prop("skarrows_crest", 1473)
	for k in range(5):                                                                    # a fan of storm-blue crest plumes
		u = -1 + k / 2
		ang = math.radians(u * 26)
		ln = 1.2 - abs(u) * 0.25
		_vane(p, (u * 0.06, -0.02 * k, 0.1), (math.sin(ang) * ln, -0.02 * k, 0.1 + math.cos(ang) * ln), 0.13, WATER if k % 2 else SKY,
			  bars=(0.45,), tip_swatch=CLOTH_WHITE, glow=1.2)
	p.seg((0, -0.05, -0.12), (0, -0.05, 0.18), 0.14, 0.12, OCHRE, sides=10)                     # bound at the quill in ochre cord
	for z in (-0.06, 0.04, 0.14):
		p.seg((0, -0.05, z), (0, -0.05, z + 0.03), 0.15, 0.15, CLOTH_WHITE, sides=10)
	for x, z in ((-0.5, 1.12), (0.52, 1.06), (0.05, 1.42)):                                  # sparks at the tips
		_zap(p, [(x, -0.12, z), (x + 0.08, -0.12, z + 0.1), (x + 0.02, -0.12, z + 0.16), (x + 0.1, -0.12, z + 0.26)], r=0.02, sw=CLOTH_WHITE)
	return p.build()


def tarns_painted_sail():
	p = Prop("tarns_painted_sail", 1475)
	nose, lt, rt, tail = (0.0, 1.4), (-0.95, 0.2), (0.95, 0.2), (0.0, 0.46)
	_slab(p, [nose, rt, tail, lt], 0.0, 0.02, CLOTH_WHITE, grad=(0.0, 0.5))                    # a kite-wing's sail
	for sx in (-1, 1):                                                                    # painted blue wingtips
		t = (sx * 0.95, 0.2)
		_slab(p, [t, (sx * 0.52, 0.76), (sx * 0.5, 0.31)], -0.01, 0.0, SKY, grad=(0.0, 0.6))
		_slab(p, [(sx * 0.5, 0.31), (sx * 0.52, 0.76), (sx * 0.4, 0.9), (sx * 0.36, 0.35)], -0.01, 0.0, OCHRE, grad=(0.0, 0.6))
	p.seg((0, -0.012, 0.8), (0, -0.02, 0.8), 0.19, 0.19, OCHRE, sides=16)                      # a painted eye
	p.seg((0, -0.02, 0.8), (0, -0.028, 0.8), 0.12, 0.12, SKY, sides=16)
	p.seg((0, -0.028, 0.8), (0, -0.034, 0.8), 0.055, 0.055, STONE_DARK, sides=12)
	for a, b in ((nose, lt), (nose, rt), (nose, tail), ((-0.5, 0.62), (0.5, 0.62))):         # bamboo spars
		p.seg((a[0], -0.04, a[1]), (b[0], -0.04, b[1]), 0.028, 0.024, WOOD, sides=6)
	for x in (-0.3, 0.3):                                                                 # rigging down to a hand bar
		p.seg((x, -0.05, 0.62), (x * 0.4, -0.2, 0.0), 0.008, 0.008, BONE, sides=3)
	p.seg((-0.2, -0.2, 0.0), (0.2, -0.2, 0.0), 0.03, 0.03, WOOD, sides=6)
	for sx in (-1, 1):
		_streamer(p, _flat(-0.01), (sx * 0.92, 0.2), (sx * 0.4, -1), 0.4, 0.06, CLOTH_RED, amp=0.05, n=8)   # tassels streaming
	return _tip_back(p.build(), -10)


def stackstones_capstone():
	p = Prop("stackstones_capstone", 1477)
	p.rock((1.4, 0.9, 0.5), (0, 0, 0.3), STONE_WARM, jitter=0.05)                             # a broad capstone off a giant's stack
	p.box((1.2, 0.76, 0.1), (0, 0.02, 0.52), STONE_WARM, grad=(0.0, 0.4), jitter=0.02)       # its worn flat top
	for x, y, s in ((-0.32, 0.1, 0.24), (0.2, -0.12, 0.2), (0.46, 0.18, 0.16)):             # lichen
		p.blob((s, s * 0.8, 0.05), (x, y, 0.57), LEAF, segs=(8, 4), grad=(0.2, 0.7))
	fr = _flat(-0.41)
	_swirl(p, fr, (-0.26, 0.28), 0.14, OCHRE, turns=1.8, w=0.03)                              # ochre spirals painted on its face
	_swirl(p, fr, (0.14, 0.3), 0.12, OCHRE, turns=1.8, w=0.028, sx=-1)
	_gust(p, fr, (0.3, 0.2), 0.2, SKY, curl=0.05, w=0.02, wave=0.015)
	for k in range(2):                                                                    # two stones still stacked on it
		p.rock((0.4 - k * 0.12, 0.32 - k * 0.08, 0.2 - k * 0.04), (0.05 + k * 0.06, 0.05, 0.66 + k * 0.17), STONE_LIGHT if k else STONE_WARM, jitter=0.06)
	return p.build()


def tawnyjaws_fang():
	p = Prop("tawnyjaws_fang", 1479)
	pts = [(-0.1, 0, 0.2), (0.08, 0, 0.6), (0.22, 0, 0.96), (0.24, 0, 1.3)]
	_line(p, pts, 0.24, 0.0, BONE, sides=9, grad=(0.0, 0.7))                                  # a man-eater's great fang
	p.seg((-0.13, -0.02, 0.3), (0.12, -0.2, 0.62), 0.02, 0.01, CLOTH_RED, sides=4)            # stained
	for k in range(9):                                                                    # a tuft of its tawny hide at the root
		a = k * math.tau / 9
		p.blob((0.22, 0.2, 0.18), (-0.1 + math.cos(a) * 0.2, math.sin(a) * 0.14, 0.12 + 0.03 * (k % 2)), AMBER if k % 3 else WOOD, segs=(6, 4),
			   grad=(0.1, 0.8))
	p.seg((-0.1, 0, -0.06), (-0.1, 0, 0.1), 0.2, 0.24, AMBER, sides=10, jitter=0.02)
	return p.build()


def herd_kings_horn():
	p = Prop("herd_kings_horn", 1481)
	pts = []
	for k in range(11):                                                                   # a huge sweeping horn
		t = k / 10
		a = t * 2.6
		pts.append((-0.7 + math.sin(a) * 0.8 + t * 0.2, 0, 0.1 + (1 - math.cos(a)) * 0.55))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		r0 = 0.3 * (1 - i / 10) + 0.02
		p.seg(a, b, r0, max(r0 - 0.028, 0.0) if i < 9 else 0.0, BONE if i < 6 else STONE_WARM if i < 8 else STONE_DARK, sides=12, grad=(0.1, 0.8))
	for i in (1, 4, 7):                                                                   # gold bands
		a, b = pts[i], pts[i + 1]
		r0 = 0.3 * (1 - i / 10) + 0.04
		p.seg(a, tuple(a[j] + (b[j] - a[j]) * 0.3 for j in range(3)), r0, r0 - 0.01, GOLD, sides=12)
	for i in (2, 5):                                                                      # lightning scars across it
		a = pts[i]
		_zap(p, [(a[0] - 0.12, -0.28 + i * 0.03, a[2] - 0.05), (a[0], -0.3 + i * 0.03, a[2] + 0.05), (a[0] + 0.05, -0.3 + i * 0.03, a[2] - 0.02),
				 (a[0] + 0.16, -0.27 + i * 0.03, a[2] + 0.08)], r=0.02, sw=CLOTH_WHITE, glow=2.2)
	p.seg((pts[0][0], 0, pts[0][2] - 0.1), pts[0], 0.36, 0.32, WOOD_GRAY, sides=12, jitter=0.03)   # the torn root
	_strands(p, 1481, 6, (pts[0][0] + 0.05, -0.2, pts[0][2]), 0.12, 0.4, [OCHRE, CLOTH_RED], OCHRE, 0.0)   # a painted tassel
	return p.build()


def khans_horsetail_banner():
	p = Prop("khans_horsetail_banner", 1483)
	p.seg((0, 0.05, -0.45), (0, 0.05, 1.4), 0.045, 0.045, WOOD, sides=8)                     # a tall pole
	p.seg((0, 0.05, 1.3), (0, 0.05, 1.72), 0.09, 0.0, GOLD, sides=4, grad=(0.0, 0.6))          # a gilded trident
	for sx in (-1, 1):
		_line(p, [(0, 0.05, 1.3), (sx * 0.18, 0.05, 1.34), (sx * 0.2, 0.05, 1.56)], 0.035, 0.0, GOLD, sides=4, grad=(0.0, 0.6))
	p.seg((0, 0.05, 1.18), (0, 0.05, 1.3), 0.2, 0.16, GOLD, sides=14, grad=(0.0, 0.6))          # over a gold disc
	p.seg((0, 0.05, 1.08), (0, 0.05, 1.18), 0.3, 0.2, OCHRE, sides=14)
	_strands(p, 1483, 22, (0, 0.05, 1.08), 0.34, 0.95, [STONE_DARK, IRON, WOOD_GRAY], IRON, 0.0)   # and a great hank of black horsetail
	for k, sw in enumerate((SKY, CLOTH_WHITE)):                                            # streamers of the sky's colors
		_streamer(p, _flat(-0.08 - 0.01 * k), (0.02, 1.16 - 0.04 * k), (1, -0.2 - 0.3 * k), 0.75, 0.14, sw, amp=0.07, n=10)
	return p.build()


def _mask_face(p, cx, cz, w, h, y0, depth, sw, eyes, eye_glow=0.0, beard=True):
	"""A bronze funerary face: a curved plate with brow, nose, shut eyes, mouth and a beard.
	Returns the surface mapping."""
	p.blob((w * 2, depth * 2, h * 2), (cx, y0, cz), sw, segs=(16, 10), grad=(0.0, 0.85))
	mf = lambda x, z, off=0.0: (cx + x, y0 - depth * math.sqrt(max(1 - (x / w) ** 2 - (z / h) ** 2, 0.0)) - 0.005 - off, cz + z)
	for sx in (-1, 1):
		_line(p, [mf(sx * 0.04 * w / 0.44, 0.24 * h / 0.6), mf(sx * 0.2 * w / 0.44, 0.28 * h / 0.6), mf(sx * 0.33 * w / 0.44, 0.22 * h / 0.6)], 0.03, 0.02,
			  sw, sides=5, grad=(0.0, 0.6))                                               # brows
		e = [mf(sx * (0.08 + 0.05 * k) * w / 0.44, (0.14 - 0.025 * math.sin(k / 4 * math.pi)) * h / 0.6, 0.004) for k in range(5)]
		_line(p, e, 0.018, 0.018, eyes, sides=4, glow=eye_glow)                          # eyes shut
	_line(p, [mf(0, 0.2 * h / 0.6, 0.01), mf(0, -0.04 * h / 0.6, 0.06)], 0.035, 0.07, sw, sides=6, grad=(0.0, 0.6))   # nose
	_line(p, [mf(-0.1 * w / 0.44, -0.18 * h / 0.6, 0.004), mf(0, -0.2 * h / 0.6, 0.004), mf(0.1 * w / 0.44, -0.18 * h / 0.6, 0.004)], 0.016, 0.016,
		  STONE_DARK, sides=4)                                                            # a thin mouth
	if beard:
		for k in range(7):                                                                # a beard of bronze strands
			x = (-0.24 + k * 0.08) * w / 0.44
			_line(p, [mf(x, -0.27 * h / 0.6, 0.0), (cx + x * 1.1, y0 - depth * 0.7, cz - h * 1.08), (cx + x * 0.8, y0 - depth * 0.5, cz - h * 1.25)], 0.03,
				  0.012, sw, sides=5, grad=(0.1, 0.8))
	return mf


def barrow_lords_death_mask():
	p = Prop("barrow_lords_death_mask", 1485)
	mf = _mask_face(p, 0.0, 0.62, 0.44, 0.6, 0.0, 0.2, BRONZE, STONE_DARK)                    # a bronze funerary mask
	for x, z, s in ((-0.3, 0.9, 0.16), (0.28, 0.4, 0.2), (0.2, 1.02, 0.12), (-0.26, 0.3, 0.12)):   # green with age
		p.blob((s, 0.03, s * 0.8), mf(x, z - 0.62, 0.0), PATINA, segs=(8, 4), grad=(0.0, 0.6))
	for sx in (-1, 1):                                                                    # holes where it was tied on
		p.seg(mf(sx * 0.38, 0.1, 0.0), mf(sx * 0.38, 0.1, 0.02), 0.03, 0.03, STONE_DARK, sides=8)
	return p.build()


# rewards

def galescout_bracer():
	p = Prop("galescout_bracer", 1491)
	t0, t1, r0, r1 = -0.34, 0.34, 0.31, 0.27
	p.seg(_fa(t0), _fa(t1), r0, r1, HIDE, sides=16, grad=(0.1, 0.8))                        # a tan leather bracer
	for t in (t0, t1 - 0.04):
		p.seg(_fa(t), _fa(t + 0.04), _fa_r(t, r0, r1, t0, t1) + 0.02, _fa_r(t, r0, r1, t0, t1) + 0.02, WOOD, sides=16)
	for k, t in enumerate((-0.18, 0.02)):                                                 # blue wind-stripes along it
		_gust(p, _fa_to3(t, _fa_r(t, r0, r1, t0, t1) + 0.005, -10), (-0.14, 0.0), 0.28, SKY, curl=0.05, w=0.024, wave=0.02)
	for k in range(3):                                                                    # laced shut down the side
		t = -0.24 + k * 0.18
		r = _fa_r(t, r0, r1, t0, t1) + 0.01
		p.seg(_fa(t, r, 50), _fa(t + 0.12, r, 80), 0.014, 0.014, WOOD, sides=4)
		p.seg(_fa(t, r, 80), _fa(t + 0.12, r, 50), 0.014, 0.014, WOOD, sides=4)
	q = Vector(_fa(0.2, 0.33, -40))                                                       # a scout's feather tied on
	p.seg(tuple(q), tuple(q + Vector((0.04, -0.03, -0.1))), 0.012, 0.012, WOOD, sides=4)
	_vane(p, tuple(q + Vector((0.04, -0.05, -0.08))), tuple(q + Vector((0.2, -0.05, -0.55))), 0.07, CLOTH_WHITE, tip_swatch=SKY)
	p.seg(_fa(t1), _fa(t1 + 0.01), 0.21, 0.21, STONE_DARK, sides=16)                          # the empty wrist
	return p.build()


def storm_eye_amulet():
	p = Prop("storm_eye_amulet", 1493)
	_cord(p, 0.45, 0.88, STONE_LIGHT)                                                      # a silver chain
	c = (0, -0.3, 0.38)
	p.seg((c[0], c[1] + 0.04, c[2]), (c[0], c[1] - 0.03, c[2]), 0.26, 0.26, STONE_LIGHT, sides=18, grad=(0.0, 0.45))   # a silver disc
	for j in range(3):                                                                    # a storm whirling on it
		_swirl(p, _flat(c[1] - 0.04), (0.0, c[2]), 0.23, SKY if j % 2 else CLOTH_WHITE, turns=0.55, w=0.03, start=j * math.tau / 3, sx=-1)
	p.blob((0.14, 0.08, 0.14), (0, c[1] - 0.07, c[2]), SKY, segs=(8, 5), glow=2.6)             # a bright blue eye
	p.seg((0, -0.3, 0.64), (0, -0.3, 0.78), 0.03, 0.03, STONE_LIGHT, sides=5)
	return p.build()


def talon_ring():
	p = Prop("talon_ring", 1495)
	_ring(p, STONE_LIGHT)                                                                  # a silver band
	p.blob((0.34, 0.34, 0.34), (0, -0.04, 1.02), SKY, segs=(12, 8), grad=(0.0, 0.5), glow=1.0)   # a sky-blue stone
	for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):                    # held in a black eagle's talons
		_line(p, [(sx * 0.06, sy * 0.05, 0.78), (sx * 0.22, sy * 0.16 - 0.04, 0.94), (sx * 0.2, sy * 0.12 - 0.06, 1.12), (sx * 0.08, sy * 0.06 - 0.06, 1.2)],
			  0.05, 0.0, IRON, sides=5, grad=(0.0, 0.5))
	p.seg((0, 0, 0.74), (0, 0, 0.84), 0.12, 0.1, OCHRE, sides=8)                               # its yellow scaled toe
	return p.build()


def thunderwing_cloak():
	p = Prop("thunderwing_cloak", 1497)
	_slab(p, _cape_outline(0.3, 0.64, 0.14), 0.04, 0.1, WATER, grad=(0.3, 1.0))              # a storm-blue cape
	for row in range(3):                                                                  # shingled thunderbird feathers
		z = 0.9 - row * 0.3
		n = 5 + (row % 2)
		spread = 0.3 + row * 0.14
		for k in range(n):
			u = -1 + 2 * k / (n - 1)
			x = u * spread
			_vane(p, (x, -row * 0.015, z), (x + u * 0.06, -row * 0.015, z - 0.5), 0.12 + row * 0.03, WATER if (k + row) % 2 else SKY,
				  tip_swatch=CLOTH_WHITE if row == 2 else None)
	for pts in (((-0.42, 0.5), (-0.3, 0.38), (-0.36, 0.26), (-0.2, 0.1)), ((0.34, 0.66), (0.44, 0.5), (0.36, 0.4), (0.5, 0.2))):   # lightning over it
		_zap(p, [(x, -0.08, z) for x, z in pts], r=0.026, sw=CLOTH_WHITE)
	for k in range(7):                                                                    # a white collar of down
		x = -0.3 + k * 0.1
		p.blob((0.16, 0.1, 0.14), (x, -0.13, 0.97 + 0.02 * math.cos(x * 5)), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.5))
	p.blob((0.22, 0.1, 0.22), (0, -0.2, 0.95), SKY, segs=(10, 6), glow=1.8)                     # a storm-blue clasp
	p.seg((0, -0.18, 0.95), (0, -0.25, 0.95), 0.08, 0.08, STONE_LIGHT, sides=10)
	return p.build()


def kitesilk_sash():
	p = Prop("kitesilk_sash", 1499)
	u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
	n = u.cross(v)
	R, c = 0.55, Vector((0, 0.1, 0.72))
	N = 28
	for h0, h1, sw in ((-0.16, -0.06, SKY), (-0.06, 0.06, CLOTH_WHITE), (0.06, 0.16, SKY)):
		for k in range(N):                                                                # a banded silk sash, looped
			a0, a1 = k * math.tau / N, (k + 1) * math.tau / N
			p0, p1 = c + u * math.cos(a0) * R + v * math.sin(a0) * R, c + u * math.cos(a1) * R + v * math.sin(a1) * R
			p.poly([tuple(q) for q in (p0 + n * h0, p1 + n * h0, p1 + n * h1, p0 + n * h1)], [(0, 1, 2, 3)], sw, grad=(0.1, 0.6))
	for k in range(8):                                                                    # ochre kite diamonds down the middle
		a = math.radians(FRONT_A - 70 + k * 20)
		q = c + Vector((math.cos(a), math.sin(a), 0)) * (R + 0.01)
		t = Vector((-math.sin(a), math.cos(a), 0))
		dia = [q + n * 0.05, q + t * 0.05, q - n * 0.05, q - t * 0.05]
		p.poly([tuple(d) for d in dia], [(0, 1, 2, 3)], OCHRE)
	k0 = c + v * -R                                                                        # knotted at the front
	p.blob((0.3, 0.2, 0.26), tuple(k0 + Vector((0.05, -0.06, 0))), SKY, segs=(8, 6), grad=(0.1, 0.7))
	for k, (dx, ln) in enumerate(((-0.12, 0.62), (0.16, 0.52))):                           # two tails streaming
		top = k0 + Vector((dx * 0.5, -0.1, -0.05))
		_streamer(p, _flat(top.y - 0.01 * k), (top.x, top.z), (dx * 1.6, -1), ln, 0.14, SKY if k else CLOTH_WHITE, amp=0.05, n=8,
				  tip_sw=OCHRE, stripe=OCHRE if k else SKY)
	return p.build()


def tarns_skyblade():
	p = Prop("tarns_skyblade", 1501)
	org, rot = (-0.55, -0.42), 48
	up = [(0.32, 0.075), (0.9, 0.08), (1.3, 0.07), (1.55, 0.04)]
	tip = (1.72, 0.0)
	outline = up + [tip] + [(x, -z) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.03, 0.03, STONE_LIGHT, grad=(0.0, 0.35))           # a long, slender pale blade
	bf = _blade_frame(rot, org, -0.035)
	for sgn in (1, -1):                                                                   # its edges glowing sky blue
		_line(p, [bf(x, sgn * (z - 0.01)) for x, z in up[1:]] + [bf(tip[0] - 0.02, 0.0)], 0.012, 0.012, SKY, sides=4, glow=1.8)
		_vane(p, bf(0.3, sgn * 0.04, 0.01), bf(0.52, sgn * 0.42, 0.01), 0.07, CLOTH_WHITE, tip_swatch=SKY)   # a guard of white feathers
		_vane(p, bf(0.3, sgn * 0.04, 0.02), bf(0.34, sgn * 0.36, 0.02), 0.06, CLOTH_WHITE)
	h = _rot2([(0.28, 0.0), (-0.12, 0.0), (-0.2, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.05, 0.055, WOOD, sides=6)           # a cord-bound grip
	for t in (0.2, 0.45, 0.7, 0.95):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.015, 0, q[1] - 0.015), (q[0] + 0.015, 0, q[1] + 0.015), 0.062, 0.062, OCHRE, sides=6)
	p.blob((0.14, 0.14, 0.14), (h[2][0], 0, h[2][1]), STONE_LIGHT, segs=(8, 6))
	_streamer(p, _flat(-0.08), (h[2][0], h[2][1]), (1, -0.5), 0.8, 0.14, SKY, amp=0.08, n=12, tip_sw=OCHRE, stripe=CLOTH_WHITE)   # a strip of painted sail
	return p.build()


def handstone_pendant():
	p = Prop("handstone_pendant", 1503)
	_cord(p, 0.45, 0.86, HIDE)                                                             # a leather thong
	c = (0, -0.3, 0.32)
	p.blob((0.56, 0.2, 0.62), c, STONE_WARM, segs=(12, 8), grad=(0.05, 0.8))                   # a smooth stone
	_handprint(p, _flat(c[1] - 0.1), (c[0] - 0.02, c[2] - 0.12), 0.62)                         # with a giant's handprint in ochre
	p.seg((0, -0.3, 0.6), (0, -0.3, 0.74), 0.035, 0.035, HIDE, sides=5)
	p.blob((0.1, 0.1, 0.1), (0, -0.3, 0.66), SKY, segs=(6, 4), glow=0.8)
	return p.build()


def capstone_maul():
	p = Prop("capstone_maul", 1505)
	org, rot = (-0.5, -0.8), 62
	_haft(p, org, rot, -0.2, 1.55, 0.075, swatch=WOOD, bands=(0.0, 0.5), band_swatch=OCHRE)
	c = _rot2([(1.72, 0.0)], rot, org)[0]
	p.rock((1.15, 0.72, 0.85), (c[0], 0, c[1]), STONE_WARM, rot=(0, -rot + 90, 0), jitter=0.05)   # a slab of the capstone for a head
	for s in (-0.2, 0.2):                                                                 # lashed on with rawhide
		q0, q1 = _rot2([(1.72 + s, -0.5), (1.72 + s, 0.5)], rot, org)
		p.seg((q0[0], -0.3, q0[1]), (q1[0], -0.3, q1[1]), 0.04, 0.04, HIDE, sides=5)
	_swirl(p, _flat(-0.38), c, 0.17, OCHRE, turns=1.8, w=0.032)                                  # an ochre spiral painted on it
	for k in range(3):
		p.blob((0.08, 0.04, 0.08), (c[0] + 0.34 * math.cos(1 + k * 1.9), -0.36, c[1] + 0.24 * math.sin(1 + k * 1.9)), SKY, segs=(6, 4))
	return p.build()


def stalkerhide_boots():
	p = Prop("stalkerhide_boots", 1507)
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, AMBER, AMBER, WOOD, grad=(0.1, 0.8), shaft=0.76)            # tawny stalker-hide boots
		for k in range(4):                                                                # dark stripes up the shaft
			z = 0.28 + k * 0.14
			p.seg((ox - 0.12, oy - r - 0.01, z), (ox + 0.04, oy - r - 0.02, z + 0.06), 0.022, 0.012, WOOD, sides=4)
			p.seg((ox + 0.04, oy - r - 0.02, z + 0.06), (ox + 0.14, oy - r + 0.02, z + 0.02), 0.012, 0.006, WOOD, sides=4)
		for k in range(8):                                                                # a fur cuff
			a = k * math.tau / 8
			p.blob((0.16, 0.14, 0.14), (ox + 0.02 + math.cos(a) * (r + 0.04), oy + math.sin(a) * (r + 0.04), 0.86), AMBER, segs=(6, 4), grad=(0.0, 0.5))
	return p.build()


def tawnyjaw_fang_dirk():
	p = Prop("tawnyjaw_fang_dirk", 1509)
	pts = [(-0.05, 0, 0.3), (0.18, 0, 0.62), (0.34, 0, 0.92), (0.4, 0, 1.2)]                   # a man-eater's fang for a blade
	_line(p, pts, 0.14, 0.0, BONE, sides=7, grad=(0.0, 0.6))
	p.seg((0.1, -0.1, 0.5), (0.3, -0.08, 0.85), 0.015, 0.008, WOOD, sides=4)                 # a groove along it
	for k in range(8):                                                                    # a collar of tawny fur
		a = k * math.tau / 8
		p.blob((0.16, 0.14, 0.14), (-0.05 + math.cos(a) * 0.12, math.sin(a) * 0.1, 0.28 + 0.02 * (k % 2)), AMBER if k % 3 else WOOD, segs=(6, 4))
	p.seg((-0.05, 0, 0.28), (-0.3, 0, -0.08), 0.065, 0.06, HIDE, sides=6)                   # a hide-bound grip
	for k in range(4):
		t = 0.15 + k * 0.22
		p.seg((-0.05 - 0.25 * t, 0, 0.28 - 0.36 * t), (-0.07 - 0.25 * t, 0, 0.25 - 0.36 * t), 0.075, 0.075, WOOD, sides=6)
	_line(p, [(-0.32, 0, -0.1), (-0.4, -0.02, -0.2), (-0.36, -0.03, -0.3)], 0.06, 0.0, IRON, sides=5)   # a claw for a pommel
	return p.build()


def hornbone_gauntlets():
	p, fr = _glove_pair("hornbone_gauntlets", 1511, BONE, STONE_WARM, WOOD, grad=(0.1, 0.75), style="gauntlet")   # plates of bone and horn
	for f in fr:
		for x, _ in FINGERS:                                                              # horn spikes over the knuckles
			p.seg(f(x * 1.05, -0.12, 0.74), f(x * 1.1, -0.28, 0.8), 0.05, 0.0, STONE_DARK, sides=6)
		p.seg(f(0, -0.13, 0.46), f(0.02, -0.3, 0.56), 0.08, 0.0, STONE_DARK, sides=6, grad=(0.0, 0.6))   # and a horn on the back of the hand
		for k in range(3):                                                                # horn ridges round the cuff
			p.seg(f(-0.26 + k * 0.26, -0.28, 0.1), f(-0.26 + k * 0.26, -0.33, 0.22), 0.045, 0.0, STONE_WARM, sides=5)
	return p.build()


def herd_kings_helm():
	p = Prop("herd_kings_helm", 1513)
	for z0, z1, r0, r1 in ((0.0, 0.28, 0.42, 0.42), (0.28, 0.5, 0.42, 0.33), (0.5, 0.64, 0.33, 0.16), (0.64, 0.7, 0.16, 0.0)):
		p.seg((0, 0, z0), (0, 0, z1), r0, r1, STONE_DARK, sides=16, grad=(0.0, 0.6))         # a dark iron cap
	p.seg((0, 0, 0.02), (0, 0, 0.18), 0.44, 0.44, OCHRE, sides=18)                              # an ochre-painted brow band
	for k in range(10):                                                                   # rimmed with shaggy hide
		a = k * math.tau / 10
		p.blob((0.2, 0.18, 0.16), (math.cos(a) * 0.44, math.sin(a) * 0.44, -0.02), WOOD_GRAY, segs=(6, 4), jitter=0.02)
	for sx in (-1, 1):                                                                    # the herd-king's great horns
		pts = [(sx * 0.36, -0.02, 0.36), (sx * 0.62, -0.04, 0.4), (sx * 0.84, -0.06, 0.56), (sx * 0.9, -0.06, 0.8), (sx * 0.8, -0.05, 0.98)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			r0 = 0.15 - i * 0.034
			p.seg(a, b, r0, max(r0 - 0.034, 0.0) if i < 3 else 0.0, BONE if i < 2 else STONE_WARM if i < 3 else STONE_DARK, sides=10, grad=(0.1, 0.8))
		p.seg(pts[1], tuple(pts[1][j] + (pts[2][j] - pts[1][j]) * 0.18 for j in range(3)), 0.13, 0.12, GOLD, sides=10)   # gold rings
	p.blob((0.12, 0.08, 0.12), (0, -0.44, 0.1), SKY, segs=(8, 5), glow=1.0)
	return p.build()


def horsetail_charm():
	p = Prop("horsetail_charm", 1515)
	_ring(p, GOLD)                                                                         # a gold band
	p.blob((0.24, 0.22, 0.24), (0, -0.02, 0.88), SKY, segs=(10, 6), glow=0.8)                  # a sky-blue bead
	p.seg((0, -0.02, 0.98), (0, -0.02, 1.08), 0.08, 0.07, OCHRE, sides=8)                       # bound at the top
	_strands(p, 1515, 9, (0.02, -0.18, 1.04), 0.24, 0.62, [STONE_DARK, WOOD_GRAY, IRON], STONE_DARK, 0.0)   # a tuft of horsetail hanging in front
	p.seg((0.0, -0.22, 0.98), (0.02, -0.22, 1.06), 0.07, 0.07, OCHRE, sides=8)
	return p.build()


def khans_curved_blade():
	p = Prop("khans_curved_blade", 1517)
	org, rot = (-0.6, -0.35), 38
	top, bot = [], []
	for k in range(9):                                                                    # a curved saber
		u = 0.3 + k * 0.16
		bend = 0.26 * ((u - 0.3) / 1.3) ** 2
		w = 0.11 - 0.02 * k / 8
		top.append((u, bend + w * 0.5))
		bot.append((u, bend - w * 0.9))
	tip = (1.66, 0.32)
	outline = bot + [tip] + list(reversed(top))
	_slab(p, _rot2(outline, rot, org), -0.035, 0.035, STONE_LIGHT, grad=(0.0, 0.4))
	bf = _blade_frame(rot, org, -0.04)
	_line(p, [bf(x, z + 0.01) for x, z in bot[1:]] + [bf(tip[0] - 0.03, tip[1] - 0.02)], 0.01, 0.01, CLOTH_WHITE, sides=4, glow=0.6)   # a bright edge
	g = [bf(0.28, -0.24, -0.04), bf(0.26, 0.0, -0.04), bf(0.28, 0.24, -0.04)]
	_line(p, g, 0.05, 0.05, GOLD, sides=6)                                                   # a gilded guard
	for end, s in ((g[0], -1), (g[2], 1)):
		p.blob((0.1, 0.1, 0.1), end, GOLD, segs=(6, 4))
	h = _rot2([(0.26, 0.0), (-0.12, -0.02), (-0.2, -0.04)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.06, CLOTH_RED, sides=6)      # a red leather grip
	p.blob((0.15, 0.15, 0.15), (h[2][0], 0, h[2][1]), GOLD, segs=(8, 6))
	_strands(p, 1517, 8, (h[2][0], -0.02, h[2][1] - 0.02), 0.16, 0.5, [STONE_DARK, IRON], IRON, 0.0)   # a horsetail tassel
	p.seg((h[2][0], -0.02, h[2][1] - 0.1), (h[2][0], -0.02, h[2][1] + 0.02), 0.06, 0.06, OCHRE, sides=8)
	return p.build()


def barrow_bronze_greaves():
	p = Prop("barrow_bronze_greaves", 1519)
	_trousers(p, BRONZE, WOOD_GRAY, leg_r=0.21, flare=0.03)
	for x in (-1, 1):
		for z in (0.62, 0.16):                                                            # raised bronze bands
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.05), 0.235, 0.24, AMBER, sides=12, grad=(0.3, 1.0))
		p.blob((0.26, 0.14, 0.24), (x * 0.21, -0.17, 0.36), BRONZE, segs=(8, 6), grad=(0.0, 0.7))   # knee cop
		_swirl(p, _flat(-0.25), (x * 0.21, 0.36), 0.08, WOOD, turns=1.8, w=0.016, sx=x)          # spirals worked into it
		for (dx, z, s) in ((0.08, 0.5, 0.1), (-0.06, 0.22, 0.12), (0.05, 0.05, 0.08)):         # green with age
			p.blob((s, 0.04, s * 0.8), (x * 0.21 + dx * x, -0.225, z), PATINA, segs=(8, 4), grad=(0.0, 0.6))
	p.box((0.1, 0.06, 0.1), (0, -0.15, 1.0), BRONZE)
	return p.build()


def death_mask_cowl():
	p = Prop("death_mask_cowl", 1521)
	p.seg((0, 0.1, -0.2), (0, 0.1, 0.25), 0.62, 0.44, STONE_DARK, sides=18, grad=(0.3, 1.0))     # a dark cowl over the shoulders
	p.blob((0.96, 0.9, 1.1), (0, 0.1, 0.62), STONE_DARK, segs=(16, 10), grad=(0.2, 0.9))        # its hood
	p.seg((0, 0.1, 1.12), (0.1, 0.3, 1.26), 0.1, 0.0, STONE_DARK, sides=8)                      # peaked
	outline = [(math.sin(math.radians(a)) * 0.3, 0.6 + math.cos(math.radians(a)) * 0.42) for a in range(0, 360, 24)]
	_slab(p, outline, -0.36, -0.3, IRON, grad=(0.3, 1.0))                                      # the shadow inside
	_mask_face(p, 0.0, 0.58, 0.24, 0.34, -0.36, 0.1, BRONZE, PATINA, eye_glow=2.4, beard=False)   # a bronze death mask, eyes aglow
	for a, b in zip(outline, outline[1:] + outline[:1]):                                  # its edge stitched in bronze thread
		p.seg((a[0], -0.37, a[1]), (b[0], -0.37, b[1]), 0.028, 0.028, BRONZE, sides=5)
	return p.build()


# ---------------------------------------------------------------- Agnavar's Hearth and Smokewood
# The Hearth is the fire god's forge-temple: black iron, molten gold, court red
# and salamander orange. Smokewood is a smoldering forest: charred wood and ash
# gray split by ember cracks, lit by the fire moths' amber glow.


def _heart(p, c, s, sw, glow=0.0, grad=(0.0, 0.7)):
	"""A plump heart facing the camera, its lobes at the top, point down; c its middle."""
	x, y, z = c
	for sx in (-1, 1):
		p.blob((0.58 * s, 0.5 * s, 0.56 * s), (x + sx * 0.2 * s, y, z + 0.14 * s), sw, segs=(12, 8), grad=grad, glow=glow)
	p.seg((x, y, z + 0.12 * s), (x, y, z - 0.5 * s), 0.42 * s, 0.0, sw, sides=12, grad=grad, glow=glow)


def _antler(p, base, sx, s=1.0, sw=ASH, tip=EMBER, glow=2.0):
	"""A branched antler rising from base and sweeping out to side sx: a beam, three tines,
	a bony burr at the root and charred tips still glowing."""
	bx, by, bz = base
	beam = [(bx, by, bz), (bx + sx * 0.18 * s, by, bz + 0.28 * s), (bx + sx * 0.32 * s, by + 0.04 * s, bz + 0.6 * s),
			(bx + sx * 0.3 * s, by + 0.08 * s, bz + 0.95 * s), (bx + sx * 0.18 * s, by + 0.1 * s, bz + 1.2 * s)]
	_line(p, beam, 0.075 * s, 0.035 * s, sw, sides=6, grad=(0.0, 0.7))
	p.seg(beam[-1], (bx + sx * 0.12 * s, by + 0.1 * s, bz + 1.36 * s), 0.035 * s, 0.0, tip, sides=5, glow=glow)
	for k, dx, dz in ((1, 0.3, 0.16), (2, 0.3, 0.26), (3, -0.26, 0.26)):
		a = beam[k]
		mid = (a[0] + sx * dx * 0.5 * s, a[1] - 0.02 * s, a[2] + dz * 0.3 * s)
		end = (a[0] + sx * dx * s, a[1] - 0.03 * s, a[2] + dz * s)
		_line(p, [a, mid, end], 0.05 * s, 0.028 * s, sw, sides=5, grad=(0.0, 0.7))
		p.seg(end, (end[0] + sx * dx * 0.3 * s, end[1], end[2] + dz * 0.4 * s), 0.028 * s, 0.0, tip, sides=5, glow=glow)
	p.seg((bx, by, bz - 0.04 * s), (bx + sx * 0.02 * s, by, bz + 0.06 * s), 0.1 * s, 0.09 * s, BONE, sides=8, jitter=0.01 * s)   # the burr


def _moth_wings(p, fore_sw, hind_sw, border, vein, eye, org=(-0.6, 0.15), s=1.0, y=0.0, vein_glow=0.0, eye_glow=2.0):
	"""A moth's fore and hind wing from org, spread up and right, with veins, a border and an eye spot."""
	sc = lambda pts: [(x * s, z * s) for x, z in pts]
	fore = _rot2(sc([(0, 0), (0.3, 0.14), (0.8, 0.26), (1.2, 0.26), (1.34, 0.12), (1.24, -0.12), (0.8, -0.24), (0.3, -0.14)]), 25, org)
	hind = _rot2(sc([(0, 0), (0.3, 0.12), (0.62, 0.1), (0.82, -0.05), (0.74, -0.32), (0.4, -0.4), (0.12, -0.18)]), -22, (org[0], org[1] - 0.05 * s))
	_slab(p, hind, y + 0.05 * s, y + 0.09 * s, hind_sw, grad=(0.2, 0.9))
	_slab(p, fore, y - 0.02 * s, y + 0.02 * s, fore_sw, grad=(0.0, 0.6))
	for outline, yy in ((fore, y - 0.03 * s), (hind, y + 0.04 * s)):
		base = outline[0]
		for q in outline[2:6]:
			p.seg((base[0], yy, base[1]), (q[0] * 0.85 + base[0] * 0.15, yy, q[1] * 0.85 + base[1] * 0.15), 0.014 * s, 0.009 * s, vein, sides=3,
				  glow=vein_glow)
		for a, b in zip(outline[2:], outline[3:] + outline[:1]):
			p.seg((a[0], yy - 0.005, a[1]), (b[0], yy - 0.005, b[1]), 0.04 * s, 0.04 * s, border, sides=4)
	for (lx, lz), es, yy, rot, o in (((0.86, 0.02), 1.0, y - 0.04 * s, 25, org), ((0.5, -0.16), 0.65, y + 0.03 * s, -22, (org[0], org[1] - 0.05 * s))):
		c = _rot2([(lx * s, lz * s)], rot, o)[0]
		p.blob((0.36 * es * s, 0.02, 0.32 * es * s), (c[0], yy, c[1]), STONE_DARK, segs=(12, 4))
		p.blob((0.26 * es * s, 0.02, 0.23 * es * s), (c[0], yy - 0.01, c[1]), eye, segs=(12, 4), grad=(0.0, 0.4), glow=eye_glow * 0.5)
		p.blob((0.1 * es * s, 0.02, 0.09 * s * es), (c[0] + 0.02 * s, yy - 0.02, c[1] + 0.02 * s), GOLD, segs=(8, 4), glow=eye_glow)
	return fore, hind


# the Hearth's drops

def court_signet():
	p = Prop("court_signet", 1601)
	for k in range(14):                                                                   # a heavy band sized for a giant's finger
		a0, a1 = k * math.tau / 14, (k + 1) * math.tau / 14
		p.seg((math.cos(a0) * 0.42, 0, 0.42 + math.sin(a0) * 0.42), (math.cos(a1) * 0.42, 0, 0.42 + math.sin(a1) * 0.42), 0.13, 0.13, GOLD, sides=6)
	p.seg((0, 0.1, 0.9), (0, -0.12, 0.9), 0.34, 0.34, GOLD, sides=8, grad=(0.0, 0.6))          # an octagonal seal
	p.seg((0, -0.12, 0.9), (0, -0.14, 0.9), 0.28, 0.28, CLOTH_RED, sides=8)                    # of court-red enamel
	y, cz = -0.16, 0.82                                                                    # stamped with the ember court's crown
	p.box((0.3, 0.04, 0.08), (0, y, cz), GOLD, glow=1.2)
	for x, h in ((-0.12, 0.15), (0.0, 0.22), (0.12, 0.15)):
		p.seg((x, y, cz + 0.03), (x, y, cz + 0.03 + h), 0.05, 0.0, GOLD, sides=4, glow=1.2)
		p.blob((0.05, 0.03, 0.05), (x, y - 0.01, cz + 0.05 + h), FLAME, segs=(5, 3), glow=2.6)
	return p.build()


def salamander_scale():
	p = Prop("salamander_scale", 1603)
	outline = [(math.cos(math.radians(a)) * 0.5, 0.55 + math.sin(math.radians(a)) * 0.58) for a in range(90, 450, 30)]
	_slab(p, outline, -0.05, 0.06, ORANGE, grad=(0.0, 0.85))                                 # a round orange scale, bright at the top
	for a, b in zip(outline, outline[1:] + outline[:1]):                                  # its rim still glowing hot
		p.seg((a[0], -0.06, a[1]), (b[0], -0.06, b[1]), 0.035, 0.035, EMBER, sides=4, glow=1.8)
	p.blob((0.46, 0.14, 0.5), (0, -0.05, 0.56), CLOTH_RED, segs=(12, 6), grad=(0.0, 0.7))       # a raised boss
	p.seg((0, -0.1, 0.56), (0.02, -0.26, 0.64), 0.1, 0.0, CLOTH_RED, sides=6)                 # with a little spine
	for k in range(8):                                                                    # black spots round it
		a = k * math.tau / 8 + 0.3
		p.blob((0.1, 0.03, 0.09), (math.cos(a) * 0.36, -0.07, 0.56 + math.sin(a) * 0.4), STONE_DARK, segs=(6, 4))
	return p.build()


def heart_of_flame():
	p = Prop("heart_of_flame", 1605)
	_heart(p, (0, 0, 0.6), 1.0, EMBER, glow=1.6)                                           # a heart made of fire
	_heart(p, (-0.03, -0.14, 0.64), 0.6, FLAME, glow=2.2)
	_heart(p, (-0.05, -0.24, 0.68), 0.26, CLOTH_WHITE, glow=2.6)                              # white-hot at its middle
	for x, h in ((-0.3, 0.45), (-0.1, 0.62), (0.12, 0.7), (0.32, 0.5)):                       # flames licking up off it
		p.seg((x, 0.0, 0.78), (x + 0.04, 0.0, 0.78 + h), 0.13, 0.0, FLAME, sides=6, glow=2.0)
	for x, z in ((-0.5, 0.15), (0.45, 0.25), (0.35, 1.45)):
		p.blob((0.06, 0.06, 0.06), (x, -0.1, z), GOLD, segs=(5, 3), glow=2.6)
	return p.build()


def heretics_charm():
	p = Prop("heretics_charm", 1607)
	_cord(p, 0.45, 0.86, WOOD_GRAY)
	c = (0, -0.3, 0.36)
	p.seg((0, c[1] + 0.04, c[2]), (0, c[1] - 0.04, c[2]), 0.3, 0.3, STONE_DARK, sides=14, grad=(0.1, 0.8))   # a blackened iron disc
	_loop(p, (0, c[1] - 0.04, c[2]), 0.3, False, 0.03, EMBER, n=14)
	y = c[1] - 0.06                                                                        # its flame turned upside down
	p.seg((0.0, y, c[2] + 0.14), (0.02, y, c[2] - 0.22), 0.1, 0.0, FLAME, sides=5, glow=2.0)
	for sx in (-1, 1):
		p.seg((sx * 0.08, y, c[2] + 0.14), (sx * 0.14, y, c[2] - 0.06), 0.065, 0.0, FLAME, sides=4, glow=2.0)
	p.blob((0.24, 0.04, 0.1), (0, y, c[2] + 0.15), FLAME, segs=(6, 4), glow=2.0)
	_line(p, [(-0.24, y - 0.01, c[2] + 0.2), (-0.06, y - 0.01, c[2] + 0.02), (0.02, y - 0.01, c[2] + 0.06), (0.22, y - 0.01, c[2] - 0.18)],
		  0.02, 0.02, IRON, sides=4)                                                      # a crack struck through it
	for sx in (-1, 1):                                                                    # tied up with torn red cloth
		p.seg((sx * 0.02, c[1], c[2] + 0.3), (sx * 0.2, c[1] - 0.02, c[2] + 0.46), 0.05, 0.03, CLOTH_RED, sides=4)
	p.seg((0, c[1], c[2] + 0.28), (0, c[1], c[2] + 0.5), 0.04, 0.04, STONE_DARK, sides=6)
	return p.build()


def brannaghs_molten_crown():
	p = Prop("brannaghs_molten_crown", 1609)
	p.seg((0, 0, 0.0), (0, 0, 0.3), 0.5, 0.52, GOLD, sides=20, grad=(0.0, 0.6))               # a great gold band
	p.seg((0, 0, 0.295), (0, 0, 0.305), 0.44, 0.44, STONE_DARK, sides=20)
	_loop(p, (0, 0, 0.02), 0.51, True, 0.035, STONE_DARK, n=20)
	for k in range(8):                                                                    # tall points, each tipped with a molten bead
		a = k * math.tau / 8 + 0.2
		h = 0.62 if k % 2 == 0 else 0.44
		x, y = math.cos(a) * 0.5, math.sin(a) * 0.5
		p.seg((x, y, 0.28), (x * 1.06, y * 1.06, 0.28 + h), 0.12, 0.0, GOLD, sides=5, grad=(0.0, 0.6))
		p.blob((0.12, 0.12, 0.12), (x * 1.06, y * 1.06, 0.3 + h), FLAME, segs=(6, 4), glow=2.6)
	for k in range(7):                                                                    # molten gold running down it
		a = math.radians(215 + k * 19)
		x, y = math.cos(a) * 0.53, math.sin(a) * 0.53
		ln = 0.14 + 0.12 * ((k * 5) % 3)
		p.seg((x, y, 0.3), (x * 1.01, y * 1.01, 0.3 - ln), 0.035, 0.03, FLAME, sides=5, glow=2.4)
		p.blob((0.08, 0.08, 0.1), (x * 1.01, y * 1.01, 0.3 - ln), FLAME, segs=(6, 4), glow=2.6)
	a = math.radians(FRONT_A)
	p.blob((0.2, 0.12, 0.24), (math.cos(a) * 0.54, math.sin(a) * 0.54, 0.16), CLOTH_RED, segs=(10, 6), glow=1.4)   # a great ruby
	return p.build()


def scorchtongues_brazier():
	p = Prop("scorchtongues_brazier", 1611)
	p.seg((0, 0, 0.42), (0, 0, 0.72), 0.24, 0.52, IRON, sides=16, grad=(0.0, 0.6))            # a black iron bowl
	_loop(p, (0, 0, 0.72), 0.52, True, 0.04, GOLD, n=18)
	for k in range(3):                                                                    # on three clawed legs
		a = k * math.tau / 3 + 0.9
		d = (math.cos(a), math.sin(a))
		pts = [(d[0] * 0.2, d[1] * 0.2, 0.46), (d[0] * 0.36, d[1] * 0.36, 0.28), (d[0] * 0.38, d[1] * 0.38, 0.1), (d[0] * 0.46, d[1] * 0.46, 0.0)]
		_line(p, pts, 0.05, 0.04, STONE_DARK, sides=6)
		p.blob((0.12, 0.12, 0.06), pts[-1], STONE_DARK, segs=(6, 4))
	for k in range(7):                                                                    # heaped coals
		a = k * 0.9
		p.rock((0.2, 0.2, 0.14), (math.cos(a) * 0.26, math.sin(a) * 0.26, 0.74), EMBER, jitter=0.03)
	for x, h in ((-0.2, 0.55), (0.0, 0.8), (0.2, 0.6), (0.08, 0.45)):                       # tall flames
		p.seg((x, -0.05, 0.72), (x + 0.04, -0.05, 0.72 + h), 0.16, 0.0, FLAME, sides=6, glow=2.6)
	for sx in (-1, 1):                                                                    # salamander heads for handles
		p.blob((0.22, 0.16, 0.14), (sx * 0.58, -0.08, 0.68), ORANGE, segs=(8, 5), grad=(0.0, 0.7))
		p.seg((sx * 0.64, -0.08, 0.68), (sx * 0.74, -0.08, 0.66), 0.06, 0.02, ORANGE, sides=5)
		p.blob((0.05, 0.04, 0.05), (sx * 0.6, -0.17, 0.72), GOLD, segs=(5, 3), glow=2.2)
	return p.build()


def forgeheart_core():
	p = Prop("forgeheart_core", 1613)
	p.blob((0.8, 0.8, 0.8), (0, 0, 0.55), EMBER, segs=(16, 12), glow=1.8)                    # a molten sphere
	p.blob((0.36, 0.16, 0.36), (-0.06, -0.34, 0.6), FLAME, segs=(8, 6), glow=2.6)
	c = Vector((0, 0, 0.55))
	z = Vector((0, 0, 1))
	for deg in (-61 + 90, -61 + 30, -61 - 30):                                             # caged in heavy iron bands
		a = math.radians(deg)
		_oval(p, tuple(c), Vector((math.cos(a), math.sin(a), 0)), z, 0.44, 0.44, 0.06, IRON, n=24)
	_oval(p, tuple(c), Vector((1, 0, 0)), Vector((0, 1, 0)), 0.44, 0.44, 0.07, STONE_DARK, n=24)
	for deg in (-61 + 30, -61 - 30):                                                         # riveted where they cross
		a = math.radians(deg + 90)
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.46, math.sin(a) * 0.46, 0.55), GOLD, segs=(6, 4))
	p.blob((0.12, 0.12, 0.12), (0, 0, 1.0), GOLD, segs=(6, 4))
	for x, z in ((-0.5, 1.0), (0.44, 1.05), (0.1, 1.2)):                                     # sparks thrown off
		p.blob((0.05, 0.05, 0.05), (x, -0.1, z), GOLD, segs=(5, 3), glow=2.6)
	return p.build()


def stolen_ember():
	p = Prop("stolen_ember", 1615)
	piv = Vector((0.0, 0.0, 0.4))
	for sgn in (1, -1):                                                                   # a pair of smith's tongs
		handle = [piv, piv + Vector((-0.5, 0.0, -0.36 + sgn * 0.1)), piv + Vector((-0.72, 0.0, -0.5 + sgn * 0.16))]
		jaw = [piv, piv + Vector((0.3, 0.0, 0.3 - sgn * 0.04)), piv + Vector((0.46, 0.0, 0.52 - sgn * 0.12))]
		_line(p, [tuple(q + Vector((0, -0.03 * sgn, 0))) for q in handle], 0.045, 0.04, STONE_DARK, sides=6)
		_line(p, [tuple(q + Vector((0, -0.03 * sgn, 0))) for q in jaw], 0.045, 0.05, IRON, sides=6)
	p.seg((0, 0.08, 0.4), (0, -0.1, 0.4), 0.07, 0.07, GOLD, sides=8)                           # the rivet
	e = (0.58, -0.02, 0.72)                                                                # gripping one live ember
	p.rock((0.4, 0.34, 0.36), e, EMBER, jitter=0.05)
	p.blob((0.24, 0.12, 0.22), (e[0] - 0.02, e[1] - 0.14, e[2] + 0.02), FLAME, segs=(8, 5), glow=3.0)
	for k in range(3):
		p.seg((e[0] - 0.1 + k * 0.1, e[1] - 0.02, e[2] + 0.16), (e[0] - 0.08 + k * 0.1, e[1] - 0.02, e[2] + 0.36 + (k % 2) * 0.12), 0.07, 0.0,
			  FLAME, sides=5, glow=2.6)
	return p.build()


# Smokewood's drops

def ember_heartwood():
	p = Prop("ember_heartwood", 1621)
	a, b = Vector((-0.45, 0.45, 0.36)), Vector((0.3, -0.3, 0.36))                            # a split log, its end to the camera
	p.seg(tuple(a), tuple(b), 0.36, 0.36, STONE_DARK, sides=12, grad=(0.1, 0.8), jitter=0.02)   # charred bark
	d = (b - a).normalized()
	for r, sw, glow in ((0.33, WOOD, 0.0), (0.26, HIDE, 0.0), (0.19, WOOD, 0.0), (0.12, EMBER, 1.8), (0.06, FLAME, 3.0)):
		p.seg(tuple(b), tuple(b + d * (0.02 + (0.33 - r) * 0.06)), r, r, sw, sides=12, glow=glow)   # rings round a burning heart
	n = Vector((0, 0, 1)).cross(d).normalized()
	for k, t in enumerate((0.2, 0.45, 0.7)):                                               # ember cracks down the bark
		q = a + (b - a) * t
		pts = [q + Vector((0, 0, 0.33)) + n * 0.04 * ((j % 2) * 2 - 1) + d * j * 0.06 for j in range(4)]
		_seam(p, [tuple(v) for v in pts], r=0.02, glow=2.2)
		side = q + Vector((0, 0, 0.08)) - n * 0.35                                       # and down its near side
		_seam(p, [tuple(side + Vector((0, 0, j * 0.08)) + d * (j % 2) * 0.05) for j in range(3)], r=0.02, glow=2.2)
	return p.build()


def smoke_pelt():
	p = Prop("smoke_pelt", 1623)
	p.blob((1.1, 0.8, 0.14), (0, 0, 0.07), STONE_DARK, segs=(12, 6), grad=(0.0, 0.6), jitter=0.05)   # a charcoal pelt
	for x in (-1, 1):
		for y in (-1, 1):
			p.blob((0.3, 0.22, 0.1), (x * 0.4, y * 0.34, 0.05), STONE_DARK, segs=(6, 4), grad=(0.0, 0.6))
			p.blob((0.12, 0.12, 0.08), (x * 0.44, y * 0.46, 0.05), IRON, segs=(6, 4))   # sooty paws
	p.blob((0.36, 0.3, 0.18), (-0.6, 0, 0.12), STONE_DARK, segs=(8, 5), grad=(0.0, 0.6))               # the head end
	p.blob((0.16, 0.2, 0.1), (-0.76, 0, 0.12), ASH, segs=(8, 5))
	for sy in (-1, 1):
		p.seg((-0.58, sy * 0.12, 0.18), (-0.6, sy * 0.16, 0.34), 0.07, 0.0, IRON, sides=5)
	p.blob((0.9, 0.18, 0.06), (0.0, 0, 0.14), IRON, segs=(10, 4))                               # a black stripe down the spine
	p.seg((0.5, 0, 0.1), (0.8, 0.08, 0.11), 0.11, 0.08, STONE_DARK, sides=6, grad=(0.0, 0.6))     # a bushy tail, its tip gone to smoke
	p.seg((0.8, 0.08, 0.11), (0.98, 0.14, 0.13), 0.08, 0.02, ASH, sides=6)
	for k, (x, y) in enumerate(((-0.2, 0.3), (0.32, 0.36))):                             # smoke still curling off its far edge
		for j in range(3):
			s = 0.12 + j * 0.06
			p.blob((s * 1.4, s * 0.8, s), (x + 0.1 * math.sin(j * 1.9 + k), y + 0.05, 0.2 + j * 0.13), ASH, segs=(8, 5), grad=(0.5, 1.0))
	return _tip_back(p.build(), 22)


def soot_mask_fragment():
	p = Prop("soot_mask_fragment", 1625)
	outline = [(0.02, 1.02), (-0.18, 0.98), (-0.34, 0.86), (-0.44, 0.66), (-0.44, 0.44), (-0.36, 0.22), (-0.2, 0.06), (0.0, 0.0),
			   (0.1, 0.14), (-0.02, 0.28), (0.12, 0.42), (0.0, 0.56), (0.14, 0.72), (0.02, 0.86)]   # half a carved mask, snapped down the middle
	_slab(p, outline, -0.05, 0.05, WOOD_GRAY, grad=(0.1, 0.9))
	for x, z, s in ((-0.3, 0.3, 0.18), (-0.1, 0.12, 0.14), (-0.36, 0.72, 0.12)):              # smeared with soot
		p.blob((s, 0.03, s * 0.8), (x, -0.055, z), STONE_DARK, segs=(8, 4))
	eye = [(-0.3, 0.62), (-0.2, 0.68), (-0.08, 0.64), (-0.14, 0.56), (-0.26, 0.56)]
	_slab(p, eye, -0.07, -0.055, IRON, grad=(0.6, 1.0))                                     # an empty eye
	p.blob((0.05, 0.02, 0.05), (-0.18, -0.075, 0.61), EMBER, segs=(5, 3), glow=2.2)
	_line(p, [(-0.36, -0.07, 0.76), (-0.2, -0.07, 0.8), (-0.04, -0.07, 0.76)], 0.03, 0.02, STONE_DARK, sides=5)   # a heavy brow
	for k in range(3):                                                                    # carved flame grooves on the cheek
		x = -0.34 + k * 0.1
		_line(p, [(x, -0.06, 0.2), (x + 0.04, -0.06, 0.34), (x - 0.01, -0.06, 0.46)], 0.018, 0.01, EMBER, sides=4, glow=1.4)
	obj = p.build()
	return _tip_back(obj, -12)


def fire_moth_dust():
	p = Prop("fire_moth_dust", 1627)
	p.blob((0.8, 0.7, 0.66), (-0.1, 0.1, 0.33), HIDE, segs=(12, 8), grad=(0.1, 0.9))          # a little hide pouch, open
	_loop(p, (-0.1, 0.1, 0.62), 0.28, True, 0.05, WOOD, n=14)
	p.blob((0.46, 0.4, 0.2), (-0.1, 0.1, 0.66), GOLD, segs=(10, 6), glow=2.4)                   # heaped with glowing dust
	p.blob((0.56, 0.4, 0.12), (0.34, -0.3, 0.05), GOLD, segs=(10, 5), glow=2.0)                  # spilled at its foot
	p.blob((0.3, 0.2, 0.08), (0.2, -0.1, 0.08), ORANGE, segs=(8, 4), glow=1.6)
	import random
	rnd = random.Random(1627)
	for k in range(12):                                                                   # motes drifting up
		x, z = rnd.uniform(-0.5, 0.6), rnd.uniform(0.7, 1.35)
		s = rnd.uniform(0.035, 0.07)
		p.blob((s, s, s), (x, -0.2, z), GOLD if k % 3 else FLAME, segs=(5, 3), glow=2.8)
	p.seg((-0.3, 0.1, 0.62), (-0.55, -0.05, 0.3), 0.025, 0.02, WOOD, sides=4)                   # its loose drawstring
	return p.build()


def glowcap():
	p = Prop("glowcap", 1629)
	p.blob((1.0, 0.8, 0.14), (0, 0, 0.04), WOOD_GRAY, segs=(12, 5), jitter=0.04)             # a clod of ashy earth
	for (x, y, h, r, tilt) in ((-0.12, 0.05, 0.62, 0.36, -6), (0.3, -0.18, 0.36, 0.22, 14), (-0.4, -0.2, 0.26, 0.16, -18)):
		top = (x + math.sin(math.radians(tilt)) * h, y, h)
		p.seg((x, y, 0.04), top, r * 0.35, r * 0.28, BONE, sides=8, grad=(0.0, 0.6))          # pale stems
		p.blob((r * 2.1, r * 2.1, r * 0.7), (top[0], top[1], top[2] + r * 0.12), ORANGE, rot=(0, tilt, 0), segs=(14, 8), grad=(0.1, 0.8), glow=0.7)
		p.blob((r * 1.8, r * 1.8, r * 0.2), (top[0], top[1], top[2] - r * 0.08), EMBER, rot=(0, tilt, 0), segs=(12, 4), glow=2.2)   # glowing gills
		for k in range(4):                                                                # bright spots on the cap
			a = math.radians(200 + k * 40)
			p.blob((r * 0.28, r * 0.2, r * 0.16), (top[0] + math.cos(a) * r * 0.6, top[1] + math.sin(a) * r * 0.6, top[2] + r * 0.36), GOLD,
				   segs=(6, 4), glow=2.6)
	return p.build()


def emberhearts_heart():
	p = Prop("emberhearts_heart", 1631)
	_heart(p, (0, 0, 0.6), 1.0, WOOD, grad=(0.55, 1.0))                                    # a heart of living wood
	for x, z, s in ((-0.32, 0.8, 0.16), (0.3, 0.64, 0.14)):                                  # knots in its bark
		p.rock((s, s * 0.6, s), (x, -0.27, z), STONE_DARK, jitter=0.03)
	p.blob((0.3, 0.12, 0.3), (0.02, -0.26, 0.6), FLAME, segs=(10, 6), glow=2.4)                 # burning inside
	for a, b in (((-0.3, 0.9), (-0.08, 0.64)), ((-0.08, 0.64), (0.02, 0.38)), ((0.02, 0.38), (0.0, 0.16)), ((-0.08, 0.64), (0.26, 0.82)),
				 ((0.02, 0.38), (0.24, 0.36))):
		p.seg((a[0], -0.3, a[1]), (b[0], -0.3, b[1]), 0.03, 0.03, EMBER, sides=4, glow=2.4)
	for k, (dx, ln) in enumerate(((-0.3, 0.4), (0.0, 0.5), (0.28, 0.36))):                 # roots trailing below
		_line(p, [(dx * 0.3, 0, 0.2), (dx * 0.9, -0.04, 0.06), (dx * 1.5 + 0.06, -0.02, 0.02 - ln * 0.25)], 0.06, 0.015, STONE_DARK, sides=5)
	return p.build()


def ashen_antler():
	p = Prop("ashen_antler", 1633)
	_antler(p, (-0.3, 0.0, 0.0), 1, s=1.3, sw=ASH, tip=EMBER, glow=2.4)                     # a great ash-gray antler, its tips smoldering
	p.blob((0.24, 0.2, 0.1), (-0.3, 0.0, -0.08), STONE_DARK, segs=(8, 5))                    # a charred stump of skull
	return p.build()


def kolts_antlered_mask():
	p = Prop("kolts_antlered_mask", 1635)
	mf = _mask_face(p, 0.0, 0.5, 0.38, 0.5, 0.0, 0.18, WOOD_GRAY, FLAME, eye_glow=0.0, beard=False)   # a carved wooden face
	for sx in (-1, 1):                                                                    # soot-black around glowing eyes
		p.blob((0.26, 0.04, 0.14), mf(sx * 0.14, 0.12, 0.0), STONE_DARK, segs=(10, 4))
		p.blob((0.1, 0.03, 0.05), mf(sx * 0.14, 0.12, 0.02), FLAME, segs=(6, 4), glow=2.8)
		for k in range(3):                                                                # black soot stripes down the cheeks
			x = sx * (0.12 + k * 0.07)
			_line(p, [mf(x, -0.02, 0.005), mf(x + sx * 0.01, -0.3, 0.005)], 0.02, 0.012, STONE_DARK, sides=4)
		_antler(p, (sx * 0.26, 0.04, 0.82), sx, s=0.62, sw=ASH, tip=EMBER, glow=2.0)       # antlers from its brow
	return p.build()


def moth_queens_wing():
	p = Prop("moth_queens_wing", 1637)
	_moth_wings(p, ORANGE, CLOTH_RED, STONE_DARK, EMBER, FLAME, org=(-0.7, 0.1), s=1.2, vein_glow=1.8, eye_glow=2.8)   # a great ember-bright wing
	for k, (x, z) in enumerate(((0.9, 1.0), (0.6, 1.25), (1.05, 0.55), (0.3, -0.45))):      # dust shed off it
		p.blob((0.05, 0.05, 0.05), (x, -0.1, z), GOLD, segs=(5, 3), glow=2.6)
	p.blob((0.24, 0.16, 0.2), (-0.7, 0.02, 0.08), HIDE, segs=(8, 5), jitter=0.02)              # a tuft of fuzz where it tore free
	return p.build()


# rewards

def courtiers_bracer():
	p = Prop("courtiers_bracer", 1641)
	_vambrace(p, IRON, GOLD, CLOTH_RED, GOLD, grad=(0.0, 0.6), glow_line=EMBER)              # black iron trimmed in gold
	p.seg(_fa(0.0, 0.3, -10), _fa(0.0, 0.37, -10), 0.15, 0.15, CLOTH_RED, sides=12)          # the court's badge: a gold crown on red
	to3 = _fa_to3(0.0, 0.38, -10)
	p.box((0.16, 0.03, 0.05), to3(-0.04, 0.0), GOLD, rot=(0, -45, 0), glow=1.0)
	for v in (-0.06, 0.0, 0.06):
		p.seg(to3(-0.02, v), to3(0.06, v * 1.2), 0.03, 0.0, GOLD, sides=4, glow=1.0)
	return p.build()


def brannaghs_scepter():
	p = Prop("brannaghs_scepter", 1643)
	org, rot = (-0.5, -0.8), 62
	_haft(p, org, rot, -0.2, 1.6, 0.07, swatch=STONE_DARK, bands=(-0.1, 0.4, 0.9, 1.4), band_swatch=GOLD)   # a long black iron haft
	bf = _blade_frame(rot, org, 0.0)
	c = bf(1.95, 0.0)
	p.blob((0.56, 0.56, 0.56), c, FLAME, segs=(14, 10), glow=2.8)                            # a molten orb
	p.blob((0.2, 0.1, 0.2), (c[0] - 0.04, c[1] - 0.26, c[2] + 0.04), CLOTH_WHITE, segs=(8, 5), glow=3.0)
	p.seg(bf(1.56, 0.0), bf(1.7, 0.0), 0.12, 0.2, GOLD, sides=10)                              # in a crown of gold
	for v in (-1, 1, 0):                                                                  # its points curling round the orb
		y = -0.18 if v == 0 else 0.0
		pts = [bf(1.68, v * 0.16), bf(1.82, v * 0.36), bf(2.08, v * 0.36), bf(2.26, v * 0.18)]
		_line(p, [(q[0], y, q[2]) for q in pts], 0.055, 0.03, GOLD, sides=6, grad=(0.0, 0.6))
		p.blob((0.08, 0.08, 0.08), (pts[-1][0], y, pts[-1][2]), CLOTH_RED, segs=(6, 4), glow=1.4)
	e = bf(-0.26, 0.0)
	p.blob((0.2, 0.2, 0.2), e, GOLD, segs=(8, 6))                                             # a gold pommel
	p.blob((0.08, 0.05, 0.08), (e[0], e[1] - 0.1, e[2]), CLOTH_RED, segs=(6, 4), glow=1.4)
	return p.build()


def salamanderscale_boots():
	p = Prop("salamanderscale_boots", 1645)
	for ox, oy in ((-0.34, 0.3), (0.26, -0.12)):
		r = _boot(p, ox, oy, ORANGE, CLOTH_RED, STONE_DARK, grad=(0.1, 0.9), shaft=0.76)
		pts = []
		for row, z in enumerate((0.66, 0.54, 0.42, 0.3)):                                # orange scales down the shin
			for k in range(2):
				pts.append((ox + (k - 0.5) * 0.14 + (0.07 if row % 2 else 0.0), oy - r - 0.01, z))
		_scales(p, pts, [CLOTH_RED, ORANGE, STONE_DARK])
		for k in range(4):                                                                # black spots along the foot
			p.blob((0.08, 0.04, 0.06), (ox - 0.48 + k * 0.12, oy - 0.26, 0.2 + 0.02 * (k % 2)), STONE_DARK, segs=(6, 4))
		for k in range(4):                                                                # a crest of little spines up the back
			z = 0.3 + k * 0.14
			p.seg((ox + r + 0.02, oy, z), (ox + r + 0.14, oy, z + 0.08), 0.04, 0.0, CLOTH_RED, sides=4)
	return p.build()


def scorchtongue_staff():
	p = Prop("scorchtongue_staff", 1647)
	org, rot = (-0.3, -0.7), 72
	_haft(p, org, rot, 0.0, 1.7, 0.06, swatch=STONE_DARK, bands=(0.2, 1.6), band_swatch=GOLD)   # a charred staff
	bf = _blade_frame(rot, org, 0.0)
	c = bf(1.85, 0.0)                                                                      # topped with a little brazier
	top = (c[0] + 0.02, c[1], c[2] + 0.12)
	p.seg((c[0], c[1], c[2] - 0.12), top, 0.1, 0.3, IRON, sides=12, grad=(0.0, 0.6))
	_loop(p, top, 0.3, True, 0.03, GOLD, n=14)
	for k in range(4):
		a = k * 1.4
		p.rock((0.14, 0.14, 0.1), (top[0] + math.cos(a) * 0.14, top[1] + math.sin(a) * 0.14, top[2]), EMBER, jitter=0.02)
	for dx, h in ((-0.12, 0.4), (0.02, 0.6), (0.14, 0.42)):
		p.seg((top[0] + dx, top[1] - 0.04, top[2]), (top[0] + dx + 0.03, top[1] - 0.04, top[2] + h), 0.1, 0.0, FLAME, sides=6, glow=2.6)
	a = math.radians(rot)                                                                   # an orange salamander coiled up the staff
	d, n = Vector((math.cos(a), 0, math.sin(a))), Vector((-math.sin(a), 0, math.cos(a)))
	base = Vector((org[0], 0, org[1]))
	pts = []
	for k in range(25):
		t = k / 24
		s = 0.55 + t * 1.1
		ang = t * 2.4 * math.tau
		pts.append(tuple(base + d * s + n * math.cos(ang) * 0.1 + Vector((0, -1, 0)) * math.sin(ang) * 0.1))
	_line(p, pts, 0.015, 0.075, ORANGE, sides=6, grad=(0.0, 0.7))
	head = Vector(pts[-1]) + d * 0.1
	p.blob((0.2, 0.15, 0.13), tuple(head), ORANGE, rot=(0, -rot, 0), segs=(8, 5), grad=(0.0, 0.7))
	for sy in (-1, 1):
		p.blob((0.05, 0.04, 0.05), tuple(head + n * 0.05 + Vector((0, sy * 0.06, 0))), GOLD, segs=(5, 3), glow=2.2)
	for k in range(0, 24, 4):                                                             # black spots along its back
		p.blob((0.05, 0.04, 0.05), tuple(Vector(pts[k]) + Vector((0, -0.05, 0.02))), STONE_DARK, segs=(5, 3))
	return p.build()


def flameheart_ring():
	p = Prop("flameheart_ring", 1649)
	_ring(p, GOLD)
	_loop(p, (0, -0.02, 0.4), 0.4, False, 0.035, EMBER, n=14, glow=1.8)                      # an ember inlay round the band
	p.seg((0, 0.06, 0.86), (0, -0.08, 0.86), 0.2, 0.2, GOLD, sides=10)
	_heart(p, (0, -0.12, 0.98), 0.44, CLOTH_RED, glow=1.8)                                    # a heart-shaped fire stone
	_heart(p, (-0.02, -0.2, 1.0), 0.2, FLAME, glow=3.0)
	for sx in (-1, 1):                                                                    # held in gold prongs
		p.seg((sx * 0.14, -0.06, 0.84), (sx * 0.2, -0.16, 1.04), 0.035, 0.0, GOLD, sides=4)
	return p.build()


def forgeheart_amulet():
	p = Prop("forgeheart_amulet", 1651)
	_cord(p, 0.45, 0.88, STONE_DARK)
	anvil = [(-0.36, 0.52), (0.4, 0.52), (0.4, 0.44), (0.22, 0.4), (0.14, 0.3), (0.14, 0.14), (0.28, 0.06), (0.28, 0.0),
			 (-0.26, 0.0), (-0.26, 0.06), (-0.12, 0.14), (-0.12, 0.3), (-0.2, 0.4), (-0.46, 0.46)]   # a little iron anvil
	outline = [(x, z - 0.02) for x, z in anvil]
	_slab(p, outline, -0.36, -0.24, IRON, grad=(0.0, 0.6))
	for a, b in zip(outline, outline[1:] + outline[:1]):
		p.seg((a[0], -0.37, a[1]), (b[0], -0.37, b[1]), 0.02, 0.02, GOLD, sides=4)
	p.blob((0.26, 0.1, 0.26), (0.01, -0.38, 0.22), FLAME, segs=(10, 6), glow=3.0)             # the forge's heart glowing in its waist
	_loop(p, (0.01, -0.38, 0.22), 0.13, False, 0.02, GOLD, n=12)
	p.seg((0.02, -0.3, 0.5), (0.02, -0.3, 0.72), 0.04, 0.04, STONE_DARK, sides=6)
	return p.build()


def penitents_sash():
	p = Prop("penitents_sash", 1653)
	c = Vector((0, 0.1, 0.62))
	_twist_ring(p, tuple(c), (1, 0, 0), (0, 1, 0), 0.55, 0.045, (HIDE, BONE), turns=14)      # a plain twisted rope
	a = math.radians(FRONT_A)
	k0 = c + Vector((math.cos(a), math.sin(a), 0)) * 0.57
	p.blob((0.2, 0.18, 0.18), tuple(k0), HIDE, segs=(8, 6), grad=(0.1, 0.8))                  # knotted at the front
	cloth = [(-0.14, 0.0), (0.14, 0.0), (0.16, -0.5), (0.02, -0.42), (-0.12, -0.52)]          # a strip of ashy sackcloth
	_slab(p, [(k0.x - 0.1 + x, k0.z - 0.06 + z) for x, z in cloth], k0.y - 0.02, k0.y + 0.02, ASH, grad=(0.1, 0.9))
	for j, dx in enumerate((-0.2, 0.16)):                                                   # two cords hanging with penance knots
		pts = [k0 + Vector((dx * 0.3, -0.06, -0.06)), k0 + Vector((dx * 0.8, -0.08, -0.3)), k0 + Vector((dx, -0.08, -0.6))]
		_line(p, [tuple(q) for q in pts], 0.03, 0.025, BONE, sides=5)
		for q in pts[1:]:
			p.blob((0.08, 0.08, 0.08), tuple(q), HIDE, segs=(6, 4))
	t = k0 + Vector((-0.2, -0.1, -0.64))                                                    # a scorched wooden token
	p.seg(tuple(t + Vector((0, 0.03, 0))), tuple(t - Vector((0, 0.03, 0))), 0.13, 0.13, STONE_DARK, sides=12)
	_flame_mark(p, tuple(t - Vector((0, 0.04, 0.06))), 0.5, GOLD, glow=1.6)
	return p.build()


def unburnt_mantle():
	p = Prop("unburnt_mantle", 1655)
	outline = [(-0.26, 1.0), (0.26, 1.0), (0.5, 0.86), (0.66, 0.6), (0.7, 0.3), (0.58, 0.12), (0.3, 0.02), (0.0, 0.0), (-0.3, 0.02),
			   (-0.58, 0.12), (-0.7, 0.3), (-0.66, 0.6), (-0.5, 0.86)]                        # a pale mantle the fire cannot touch
	_slab(p, outline, -0.02, 0.06, CLOTH_WHITE, grad=(0.1, 0.8))
	for a, b in zip(outline[2:12], outline[3:13]):                                        # its gold hem
		p.seg((a[0], -0.03, a[1]), (b[0], -0.03, b[1]), 0.04, 0.04, GOLD, sides=5)
	for k in range(9):                                                                    # flames licking up round the hem, harmless
		t = k / 8
		x = -0.62 + t * 1.24
		z = 0.1 + 0.2 * (2 * abs(t - 0.5)) ** 2
		h = 0.24 + 0.12 * (k % 2)
		p.seg((x, -0.05, z), (x + 0.03, -0.05, z + h), 0.08, 0.0, FLAME, sides=5, glow=2.4)
	for k in range(9):                                                                    # a gold-embroidered collar
		t = k / 8
		x = -0.36 + t * 0.72
		p.blob((0.16, 0.1, 0.14), (x, -0.05, 0.97 - math.sin(t * math.pi) * 0.1), GOLD, segs=(6, 4), grad=(0.0, 0.6))
	_flame_mark(p, (0, -0.06, 0.52), 1.1, CLOTH_RED, glow=1.0)                                # the unburnt flame on its back
	p.seg((0, -0.08, 0.82), (0, -0.14, 0.82), 0.11, 0.11, GOLD, sides=10)                     # a gold clasp with a ruby
	p.blob((0.1, 0.06, 0.1), (0, -0.15, 0.82), CLOTH_RED, segs=(6, 4), glow=1.4)
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(-15), 4, "X"))
	return obj


def heartwood_shield():
	p = Prop("heartwood_shield", 1657)
	c = (0, 0, 0.7)
	p.seg((0, 0.06, 0.7), (0, -0.06, 0.7), 0.7, 0.7, WOOD, sides=24, grad=(0.1, 0.9))          # a round of heartwood
	for r, sw in ((0.58, HIDE), (0.44, WOOD_GRAY), (0.3, HIDE)):                              # its growth rings
		_loop(p, (0, -0.07, 0.7), r, False, 0.018, sw, n=22)
	for k in range(14):                                                                   # rimmed in rough bark
		a0, a1 = k * math.tau / 14, (k + 1) * math.tau / 14
		p.seg((math.cos(a0) * 0.7, -0.02, 0.7 + math.sin(a0) * 0.7), (math.cos(a1) * 0.7, -0.02, 0.7 + math.sin(a1) * 0.7), 0.08, 0.08,
			  STONE_DARK, sides=5, jitter=0.012)
	for a in (0.5, 1.9, 3.3, 4.6, 5.7):                                                    # ember cracks running out from the heart
		pts = [(math.cos(a) * r + 0.03 * math.sin(r * 20), -0.075, 0.7 + math.sin(a) * r) for r in (0.18, 0.3, 0.42, 0.52)]
		_seam(p, pts, r=0.02, glow=2.0)
	_heart(p, (0, -0.1, 0.72), 0.34, EMBER, glow=2.4)                                        # its heart still burning
	_heart(p, (-0.01, -0.16, 0.74), 0.16, FLAME, glow=3.0)
	for k in range(4):                                                                    # iron studs
		a = k * math.tau / 4 + math.pi / 4
		p.blob((0.08, 0.06, 0.08), (math.cos(a) * 0.52, -0.08, 0.7 + math.sin(a) * 0.52), IRON, segs=(6, 4))
	return p.build()


def emberheart_bow():
	p = Prop("emberheart_bow", 1659)
	org, rot = (0.0, 0.6), 50
	pts = []
	for k in range(17):                                                                   # a gnarled limb of charred wood
		t = -1 + k / 8
		w = 0.3 * (1 - t * t) + 0.025 * math.sin(k * 2.1)
		pts.append((t * 1.1, w))
	lp = _rot2(pts, rot, org)
	for i, (a, b) in enumerate(zip(lp, lp[1:])):
		r = 0.08 - abs(i - 7.5) / 8 * 0.04
		p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), r, r, STONE_DARK, sides=6, grad=(0.1, 0.8))
	for rng in ((1, 7), (9, 15)):                                                           # an ember crack running down each limb
		_seam(p, [(lp[k][0] + 0.015 * (k % 2), -0.07, lp[k][1] + 0.015 * (k % 2)) for k in range(*rng)], r=0.02, glow=2.4)
	for k, sgn in ((3, 1), (12, -1)):                                                     # twigs still sprouting, one ember leaf each
		q = lp[k]
		tip = (q[0] + 0.12, -0.02, q[1] + 0.16 * sgn + 0.08)
		p.seg((q[0], 0, q[1]), tip, 0.03, 0.012, STONE_DARK, sides=4)
		p.blob((0.16, 0.04, 0.09), (tip[0] + 0.05, -0.03, tip[2] + 0.02), ORANGE, rot=(0, -30, 0), segs=(6, 4), glow=1.4)
	g0, g1 = lp[7], lp[9]
	p.seg((g0[0], 0, g0[1]), (g1[0], 0, g1[1]), 0.095, 0.095, ASH, sides=8)                  # an ash-gray grip
	p.blob((0.12, 0.08, 0.12), ((g0[0] + g1[0]) / 2, -0.09, (g0[1] + g1[1]) / 2), FLAME, segs=(6, 4), glow=2.8)   # an ember at its heart
	p.seg((lp[0][0], 0.02, lp[0][1]), (lp[16][0], 0.02, lp[16][1]), 0.012, 0.012, CLOTH_WHITE, sides=4)   # the string
	return p.build()


def smokehide_gloves():
	p, fr = _glove_pair("smokehide_gloves", 1661, ASH, STONE_DARK, WOOD_GRAY, grad=(0.2, 0.9))
	for f in fr:
		for k in range(3):                                                                # dark bands across the back, like a smoke wolf's
			p.seg(f(-0.22, -0.13, 0.44 + k * 0.1), f(0.22, -0.13, 0.48 + k * 0.1), 0.025, 0.025, STONE_DARK, sides=4)
		_seam(p, [f(-0.24, -0.25, 0.3), f(0, -0.27, 0.28), f(0.24, -0.25, 0.3)], r=0.014, glow=1.8)   # ember stitching at the cuff
		for j in range(3):                                                                # smoke rising off it
			s = 0.1 + j * 0.05
			x, y, z = f(-0.1 + j * 0.06, -0.1, 1.2 + j * 0.16)
			p.blob((s, s * 0.7, s), (x, y, z), ASH, segs=(6, 4), grad=(0.3, 0.9))
	return p.build()


def ashen_antler_helm():
	p = Prop("ashen_antler_helm", 1663)
	for z0, z1, r0, r1 in ((0.0, 0.3, 0.42, 0.42), (0.3, 0.52, 0.42, 0.34), (0.52, 0.68, 0.34, 0.2), (0.68, 0.76, 0.2, 0.0)):
		p.seg((0, 0, z0), (0, 0, z1), r0, r1, IRON, sides=16, grad=(0.0, 0.6))              # a blackened iron helm
	_loop(p, (0, 0, 0.04), 0.43, True, 0.045, ASH, n=18)
	_loop(p, (0, 0, 0.3), 0.425, True, 0.03, EMBER, n=18, glow=1.8)
	p.box((0.1, 0.1, 0.4), (0, -0.43, 0.08), IRON, grad=(0.0, 0.6))                           # a nasal
	for sx in (-1, 1):
		p.blob((0.16, 0.08, 0.1), (sx * 0.16, -0.4, 0.18), FLAME, segs=(6, 4), glow=2.2)      # glowing eye-holes behind it
		_antler(p, (sx * 0.3, 0.02, 0.5), sx, s=0.8, sw=ASH, tip=EMBER, glow=2.2)           # the Ashen Stag's antlers
	return p.build()


def sootveil_hood():
	p = Prop("sootveil_hood", 1665)
	p.seg((0, 0.1, -0.2), (0, 0.1, 0.25), 0.62, 0.44, ASH, sides=18, grad=(0.2, 1.0))          # an ash-gray hood over the shoulders
	p.blob((0.96, 0.9, 1.1), (0, 0.1, 0.62), ASH, segs=(16, 10), grad=(0.1, 0.9))
	p.seg((0, 0.1, 1.12), (0.08, 0.32, 1.22), 0.1, 0.0, ASH, sides=8)
	outline = [(math.sin(math.radians(a)) * 0.3, 0.6 + math.cos(math.radians(a)) * 0.42) for a in range(0, 360, 24)]
	_slab(p, outline, -0.36, -0.3, IRON, grad=(0.3, 1.0))                                      # the shadow inside
	for sx in (-1, 1):
		p.blob((0.1, 0.03, 0.05), (sx * 0.1, -0.37, 0.74), FLAME, segs=(6, 4), glow=2.8)       # eyes glowing out of it
	veil = [(-0.34, 0.66), (0.34, 0.66), (0.3, 0.3), (0.2, 0.08), (0.08, -0.02), (0.0, 0.06), (-0.1, -0.04), (-0.22, 0.08), (-0.32, 0.3)]
	_slab(p, veil, -0.42, -0.38, STONE_DARK, grad=(0.2, 1.0))                                  # a sooty veil over the face
	_seam(p, [(x, -0.43, z) for x, z in veil[:2]], r=0.02, glow=1.8)                          # hemmed in ember thread
	for a, b in zip(outline, outline[1:] + outline[:1]):
		p.seg((a[0], -0.37, a[1]), (b[0], -0.37, b[1]), 0.028, 0.028, STONE_DARK, sides=5)
	return p.build()


def kolts_brand():
	p = Prop("kolts_brand", 1667)
	org, rot = (-0.55, -0.42), 48
	up = [(0.32, 0.1), (0.8, 0.11), (1.2, 0.1), (1.44, 0.06)]
	tip = (1.6, 0.0)
	outline = up + [tip] + [(x, -z) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.035, 0.035, STONE_DARK, grad=(0.0, 0.6))             # a sooty blade
	bf = _blade_frame(rot, org, -0.045)
	_line(p, [bf(0.36, 0.0), bf(1.0, 0.0), bf(1.45, 0.0)], 0.035, 0.02, EMBER, sides=4, glow=2.6)   # burning down its middle
	for k, u in enumerate((0.45, 0.62, 0.8, 0.98, 1.16, 1.34)):                            # flames licking off its edge
		v = 0.1 if u < 1.3 else 0.07
		h = 0.2 + 0.08 * (k % 2)
		p.seg(bf(u, v), bf(u + 0.08, v + h), 0.06, 0.0, FLAME, sides=5, glow=2.4)
	g = [bf(0.3, -0.3, -0.04), bf(0.26, 0.0, -0.04), bf(0.3, 0.3, -0.04)]
	_line(p, g, 0.05, 0.05, ASH, sides=6)                                                      # a guard of antler
	for end, s in ((g[0], -1), (g[2], 1)):
		e2 = bf(0.46, s * 0.4, -0.04)
		p.seg(end, e2, 0.045, 0.0, ASH, sides=5)
		p.seg(end, bf(0.2, s * 0.44, -0.04), 0.04, 0.0, EMBER, sides=5, glow=1.8)
	h = _rot2([(0.26, 0.0), (-0.12, 0.0), (-0.2, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.06, STONE_DARK, sides=6)     # a soot-black grip
	for t in (0.25, 0.55, 0.85):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.02, 0, q[1] - 0.02), (q[0] + 0.02, 0, q[1] + 0.02), 0.068, 0.068, ASH, sides=6)
	p.blob((0.16, 0.16, 0.16), (h[2][0], 0, h[2][1]), ASH, segs=(8, 6))
	p.blob((0.08, 0.05, 0.08), (h[2][0], -0.08, h[2][1]), FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def mothwing_cloak():
	p = Prop("mothwing_cloak", 1669)
	_slab(p, _cape_outline(0.3, 0.6, 0.12), 0.08, 0.12, WOOD, grad=(0.2, 1.0))                # a dusky brown cape
	for sx in (-1, 1):                                                                    # laid over with two great moth wings
		fore = [(0.0, 0.98), (0.5, 0.94), (0.72, 0.7), (0.66, 0.42), (0.36, 0.34), (0.06, 0.42)]
		hind = [(0.02, 0.46), (0.4, 0.38), (0.56, 0.16), (0.44, -0.04), (0.16, -0.06), (0.02, 0.1)]
		for outline, y, sw in ((hind, 0.05, HIDE), (fore, 0.0, BONE)):
			pts = [(sx * x, z) for x, z in outline]
			_slab(p, pts, y - 0.02, y + 0.02, sw, grad=(0.0, 0.7))
			for a, b in zip(pts[1:5], pts[2:6]):
				p.seg((a[0], y - 0.03, a[1]), (b[0], y - 0.03, b[1]), 0.03, 0.03, WOOD, sides=4)
		for (x, z, s, y) in ((0.4, 0.66, 1.0, -0.03), (0.3, 0.16, 0.7, 0.02)):             # eye spots glowing like embers
			p.blob((0.26 * s, 0.02, 0.24 * s), (sx * x, y, z), STONE_DARK, segs=(12, 4))
			p.blob((0.18 * s, 0.02, 0.17 * s), (sx * x, y - 0.01, z), ORANGE, segs=(12, 4), glow=1.2)
			p.blob((0.07 * s, 0.02, 0.07 * s), (sx * x, y - 0.02, z), GOLD, segs=(8, 4), glow=2.4)
	for k in range(7):                                                                    # a furry collar
		x = -0.3 + k * 0.1
		p.blob((0.16, 0.12, 0.14), (x, -0.08, 0.99 + 0.02 * math.cos(x * 5)), ASH, segs=(6, 4), grad=(0.0, 0.6))
	for sx in (-1, 1):                                                                    # feathery antennae over the clasp
		_line(p, [(sx * 0.04, -0.14, 0.98), (sx * 0.14, -0.16, 1.16), (sx * 0.26, -0.16, 1.24)], 0.02, 0.012, WOOD, sides=4)
	p.blob((0.18, 0.1, 0.18), (0, -0.16, 0.96), GOLD, segs=(8, 5), glow=1.6)
	return p.build()


def moth_queens_diadem():
	p = Prop("moth_queens_diadem", 1671)
	_loop(p, (0, 0, 0.12), 0.46, True, 0.04, GOLD, n=20)                                     # a slender gold circlet
	a = math.radians(FRONT_A)
	f = Vector((math.cos(a), math.sin(a), 0)) * 0.48
	to3 = lambda x, z, off=0.0: tuple(f + Vector((-math.sin(a), math.cos(a), 0)) * x + Vector((math.cos(a), math.sin(a), 0)) * (0.02 + off)
									 + Vector((0, 0, z)))
	for sx in (-1, 1):                                                                    # a golden moth spread across its brow
		fore = [(0.04, 0.2), (0.24, 0.5), (0.46, 0.56), (0.5, 0.36), (0.3, 0.18)]
		hind = [(0.04, 0.14), (0.28, 0.08), (0.34, -0.12), (0.16, -0.14)]
		for outline, sw, off in ((hind, CLOTH_RED, 0.0), (fore, ORANGE, 0.01)):
			pts = [to3(sx * x, z, off) for x, z in outline]
			p.poly(pts, [tuple(range(len(pts)))], sw, grad=(0.0, 0.6))
			_line(p, [to3(sx * x, z, off + 0.01) for x, z in outline + outline[:1]], 0.018, 0.018, GOLD, sides=4)
		p.blob((0.1, 0.03, 0.09), to3(sx * 0.34, 0.4, 0.03), GOLD, segs=(6, 4), glow=2.4)
		_line(p, [to3(sx * 0.02, 0.3, 0.02), to3(sx * 0.1, 0.52, 0.02), to3(sx * 0.2, 0.66, 0.02)], 0.016, 0.01, GOLD, sides=4)   # antennae
		p.blob((0.05, 0.05, 0.05), to3(sx * 0.2, 0.66, 0.02), GOLD, segs=(5, 3), glow=2.0)
	_line(p, [to3(0, 0.34, 0.03), to3(0, 0.12, 0.04), to3(0, -0.06, 0.03)], 0.05, 0.03, GOLD, sides=6, grad=(0.0, 0.6))   # its body
	p.blob((0.12, 0.08, 0.14), to3(0, 0.16, 0.06), FLAME, segs=(8, 5), glow=2.8)               # an amber gem for its heart
	return p.build()


# ---------------------------------------------------------------- the Standing Sky's summit: Galehold's 40-45 gear, Stonesail, Hollow Air, Vayuketh's Step
# Galehold's new tier reuses the Skyforged, Windrunner and Galeweave shapes repainted:
# Stormcrest plate in storm-blue steel with silver, Cloudhide in pale gray-white
# leather, Skysilk in sky-blue silk. Stonesail is humming gray moor stone and
# heather; Hollow Air is cloud white and storm blue; Vayuketh's Step is temple
# bronze gone green, lightning and pale crystal.


def _repaint(obj, swaps):
	"""Moves a built icon's paint from one palette swatch to another: {old: (new, g0, g1)},
	the old swatch's gradient squeezed into g0..g1 of the new one. Every swap reads the
	original paint, so two swatches can trade places."""
	uv = obj.data.uv_layers[0]
	for d in uv.data:
		u, v = d.uv
		col, row = round((u * 1024 - 48) / 128), min(int((1 - v) / 0.25), 3)
		if (col, row) not in swaps:
			continue
		(nc, nr), g0, g1 = swaps[(col, row)]
		g = min(max(((1 - row * 0.25 - v) / 0.25 - 0.02) / 0.96, 0.0), 1.0)
		g = g0 + (g1 - g0) * g
		d.uv = ((nc * 128 + 48) / 1024, 1 - nr * 0.25 - 0.25 * (0.02 + 0.96 * g))
	return obj


def _repainted(name, base, swaps, extra=None):
	"""An icon builder that draws `base`'s shape repainted with `swaps`; `extra`
	adds parts of its own (a separate Prop that renders with it)."""
	def build():
		obj = _repaint(base(), swaps)
		obj.name = name
		if extra:
			extra()
		return obj
	build.__name__ = name
	return build


STORMCREST = {STONE_LIGHT: (WATER, 0.45, 0.95), SKY: (STONE_LIGHT, 0.0, 0.35)}                # storm-blue steel, silver where the enamel was
CLOUDHIDE = {HIDE: (CLOTH_WHITE, 0.25, 1.0), WOOD: (SEA_STONE, 0.1, 0.8), CLOTH_WHITE: (SKY, 0.0, 0.5), OCHRE: (STONE_LIGHT, 0.0, 0.4)}
SKYSILK = {CLOTH_WHITE: (SKY, 0.0, 0.55), SKY: (CLOTH_WHITE, 0.0, 0.4)}


def _thundercloud_puffs():
	p = Prop("thundercloud_puffs", 1703)
	c = _rot2([(1.95, 0.0)], 72, (-0.3, -0.7))[0]
	for k, (dx, dz, s) in enumerate(((-0.4, -0.06, 0.5), (0.4, -0.1, 0.46), (-0.24, 0.3, 0.48), (0.26, 0.28, 0.5), (0.0, 0.44, 0.44), (0.0, -0.2, 0.4))):
		p.blob((s, s * 0.7, s * 0.8), (c[0] + dx, 0.2, c[1] + dz), ASH if k % 2 else SEA_STONE, segs=(10, 6), grad=(0.3, 1.0))   # a thundercloud behind the gem
	return p.build()


def _stormfeather_zap():
	p = Prop("stormfeather_zap", 1705)
	_zap(p, [(-0.5, -0.1, 0.36), (-0.42, -0.1, 0.46), (-0.48, -0.1, 0.52), (-0.38, -0.1, 0.64)], r=0.02, sw=SKY)
	_zap(p, [(0.1, -0.1, 0.36), (0.2, -0.1, 0.42), (0.16, -0.1, 0.5), (0.28, -0.1, 0.56)], r=0.02, sw=CLOTH_WHITE)
	return p.build()


stormcrest_helm = _repainted("stormcrest_helm", skyforged_helm, STORMCREST)
stormcrest_breastplate = _repainted("stormcrest_breastplate", skyforged_breastplate, STORMCREST)
stormcrest_vambraces = _repainted("stormcrest_vambraces", skyforged_vambraces, STORMCREST)
stormcrest_gauntlets = _repainted("stormcrest_gauntlets", skyforged_gauntlets, STORMCREST)
stormcrest_greaves = _repainted("stormcrest_greaves", skyforged_greaves, STORMCREST)
stormcrest_boots = _repainted("stormcrest_boots", skyforged_boots, STORMCREST)
stormcrest_shield = _repainted("stormcrest_shield", skyforged_shield, {SKY: (WATER, 0.45, 0.95), STONE_LIGHT: (STONE_LIGHT, 0.0, 0.35)})
cloudhide_jerkin = _repainted("cloudhide_jerkin", windrunner_jerkin, CLOUDHIDE)
cloudhide_leggings = _repainted("cloudhide_leggings", windrunner_leggings, CLOUDHIDE)
cloudhide_gloves = _repainted("cloudhide_gloves", windrunner_gloves, CLOUDHIDE)
cloudhide_boots = _repainted("cloudhide_boots", windrunner_boots, CLOUDHIDE)
skysilk_cap = _repainted("skysilk_cap", galeweave_cap, SKYSILK)
skysilk_robe = _repainted("skysilk_robe", galeweave_robe, SKYSILK)
skysilk_gloves = _repainted("skysilk_gloves", galeweave_gloves, SKYSILK)
skysilk_slippers = _repainted("skysilk_slippers", galeweave_slippers, SKYSILK)
stormcrest_sword = _repainted("stormcrest_sword", skyforged_sword, STORMCREST)
stormcrest_war_axe = _repainted("stormcrest_war_axe", skyforged_war_axe, STORMCREST)
stormcrest_greataxe = _repainted("stormcrest_greataxe", skyforged_greataxe, STORMCREST)
cloudpiercer_dirk = _repainted("cloudpiercer_dirk", zephyr_dirk, {CLOTH_WHITE: (WATER, 0.4, 0.9), SKY: (CLOTH_WHITE, 0.0, 0.4)})
thundercloud_staff = _repainted("thundercloud_staff", stormwood_staff, {WOOD_GRAY: (STONE_DARK, 0.0, 0.8), SKY: (WATER, 0.2, 0.7)}, _thundercloud_puffs)
summit_longbow = _repainted("summit_longbow", galehold_longbow, {BONE: (CLOTH_WHITE, 0.1, 0.9), SKY: (WATER, 0.4, 0.95), OCHRE: (STONE_LIGHT, 0.0, 0.4)})
stormfeather_arrow = _repainted("stormfeather_arrow", windcutter_arrow, {SKY: (WATER, 0.4, 0.95), BONE: (SEA_STONE, 0.0, 0.6)}, _stormfeather_zap)


def _hum(p, to3, c, sx, n=3, r0=0.3, dr=0.14, spread=40, sw=CLOTH_WHITE, w=0.018, glow=1.2):
	"""Arcs of sound spreading from c toward side sx: a singing stone's hum."""
	for k in range(n):
		r = r0 + k * dr
		pts = [to3(c[0] + sx * math.cos(math.radians(a)) * r, c[1] + math.sin(math.radians(a)) * r) for a in range(-spread, spread + 1, 10)]
		_line(p, pts, w, w, sw, sides=4, grad=(0.0, 0.5), glow=glow)


def _fork(p, to3, c, s, sw, grad=(0.0, 0.8)):
	"""A tuning fork of stone standing in the picture plane, the bottom of its U at c."""
	x, z = c
	pts = [to3(x + math.cos(math.radians(a)) * 0.2 * s, z + 0.2 * s + math.sin(math.radians(a)) * 0.2 * s) for a in range(180, 361, 20)]
	_line(p, pts, 0.08 * s, 0.08 * s, sw, sides=8, grad=grad)
	for sx in (-1, 1):
		p.seg(to3(x + sx * 0.2 * s, z + 0.2 * s), to3(x + sx * 0.2 * s, z + 0.85 * s), 0.08 * s, 0.07 * s, sw, sides=8, grad=grad)
		p.blob((0.15 * s, 0.15 * s, 0.1 * s), to3(x + sx * 0.2 * s, z + 0.86 * s), sw, segs=(8, 5), grad=grad)


def _rune(p, to3, c, s, sw=SKY, glow=2.2, r=0.02):
	"""A glowing rune: a stem, two branches and a hooked foot."""
	x, z = c
	_line(p, [to3(x, z - 0.3 * s), to3(x, z + 0.3 * s)], r, r, sw, sides=4, glow=glow)
	_line(p, [to3(x, z + 0.12 * s), to3(x + 0.18 * s, z + 0.28 * s)], r, r, sw, sides=4, glow=glow)
	_line(p, [to3(x, z - 0.02 * s), to3(x - 0.16 * s, z + 0.14 * s)], r, r, sw, sides=4, glow=glow)
	_line(p, [to3(x, z - 0.3 * s), to3(x + 0.14 * s, z - 0.2 * s), to3(x + 0.1 * s, z - 0.08 * s)], r, r, sw, sides=4, glow=glow)


def _front_of(c, size):
	"""(x, z[, off]) onto the camera side of a blob of `size` centered at c."""
	cx, cy, cz = c
	w, d, h = size[0] / 2, size[1] / 2, size[2] / 2
	return lambda x, z, off=0.0: (x, cy - d * math.sqrt(max(1 - ((x - cx) / w) ** 2 - ((z - cz) / h) ** 2, 0.0)) - 0.005 - off, z)


# Stonesail's drops

def singing_stone_chip():
	p = Prop("singing_stone_chip", 1711)
	c, size = (-0.12, 0.0, 0.42), (0.9, 0.56, 0.8)
	p.blob(size, c, SEA_STONE, segs=(12, 8), grad=(0.0, 0.8), jitter=0.05)                      # a chip of wind-worn moor stone
	mf = _front_of(c, size)
	for x, z, s in ((-0.24, 0.52, 0.12), (0.04, 0.3, 0.09)):                                   # holes the wind sings through
		p.blob((s * 2, 0.06, s * 1.6), mf(x, z, -0.02), STONE_DARK, segs=(10, 5))
	_line(p, [mf(-0.4, 0.2, 0.0), mf(-0.2, 0.14, 0.0), mf(0.1, 0.18, 0.0)], 0.016, 0.016, STONE_DARK, sides=4)
	_hum(p, _flat(-0.2), (0.3, 0.44), 1, n=3, r0=0.12, dr=0.14, glow=1.6)                       # and hums still
	for x, y in ((-0.32, 0.0), (0.1, 0.1)):                                                 # lichen
		p.blob((0.16, 0.12, 0.06), (x, y, 0.8), LEAF, segs=(6, 4), grad=(0.2, 0.7))
	return p.build()


moor_hide = _repainted("moor_hide", stalker_pelt, {AMBER: (WOOD_GRAY, 0.0, 0.8), WOOD: (STONE_DARK, 0.2, 1.0)})


def rune_shard():
	p = Prop("rune_shard", 1713)
	outline = [(-0.32, 0.0), (0.26, 0.04), (0.42, 0.5), (0.24, 1.14), (-0.04, 1.36), (-0.2, 1.0), (-0.4, 0.62)]
	_slab(p, outline, -0.1, 0.12, SEA_STONE, grad=(0.0, 0.8))                                 # a broken shard of standing stone
	for a, b in ((outline[3], outline[4]), (outline[4], outline[5])):                     # its fresh break, paler
		p.seg((a[0], -0.11, a[1]), (b[0], -0.11, b[1]), 0.025, 0.025, STONE_LIGHT, sides=4)
	_rune(p, _flat(-0.11), (0.02, 0.62), 1.2, glow=2.4, r=0.03)                                  # a rune cut in it, glowing
	return p.build()


def hags_hair_knot():
	p = Prop("hags_hair_knot", 1715)
	c = Vector((0, 0, 0.72))
	for k, (ax, sw) in enumerate(((0, ASH), (60, WOOD_GRAY), (120, CLOTH_WHITE), (30, ASH), (150, WOOD_GRAY))):   # a tangle of gray hair
		a = math.radians(ax)
		u = Vector((math.cos(a), 0, math.sin(a)))
		v = Vector((0, 1, 0)).lerp(Vector((-math.sin(a), 0, math.cos(a))), 0.3 + 0.15 * k).normalized()
		_oval(p, tuple(c), u, v, 0.3 - 0.02 * k, 0.24, 0.04, sw, n=14)
	p.blob((0.3, 0.26, 0.28), tuple(c), ASH, segs=(8, 6), jitter=0.03)
	_strands(p, 1715, 10, (0.0, -0.05, 0.5), 0.26, 0.6, [ASH, CLOTH_WHITE, WOOD_GRAY], ASH, 0.0)   # straggling ends
	p.seg((-0.08, -0.2, 0.62), (0.1, -0.2, 0.66), 0.07, 0.07, BONE, sides=8)                    # a bone bead knotted in
	p.blob((0.12, 0.08, 0.12), (0.22, -0.24, 0.84), LEAF, segs=(6, 4), glow=1.2)               # and a glint of her green witch-light
	_line(p, [(0.2, -0.12, 0.9), (0.44, -0.1, 1.12), (0.52, -0.12, 1.3)], 0.025, 0.012, WOOD, sides=4)   # a twig of heather
	for k in range(4):
		p.blob((0.07, 0.07, 0.07), (0.44 + 0.03 * k, -0.14, 1.12 + 0.05 * k), PETAL_PURPLE, segs=(5, 3))
	return p.build()


# Hollow Air's drops

def tempest_mote():
	p = Prop("tempest_mote", 1717)
	c = Vector((0, 0, 0.62))
	p.blob((0.86, 0.86, 0.86), tuple(c), WATER, segs=(14, 10), grad=(0.5, 1.0), glow=0.2)       # a knot of storm
	for k, (ax, sw) in enumerate(((20, CLOTH_WHITE), (-40, SKY), (80, CLOTH_WHITE))):          # winds whirling round it
		a = math.radians(ax)
		_oval(p, tuple(c), Vector((1, 0, 0)), Vector((0, math.cos(a), math.sin(a))), 0.52 + 0.05 * k, 0.48 + 0.05 * k, 0.018, sw, n=24, glow=1.4)
	for j in range(3):                                                                    # its clouds whirling in
		_swirl(p, _flat(-0.42), (0.0, 0.62), 0.36, CLOTH_WHITE if j % 2 == 0 else ASH, turns=0.55, w=0.05, start=j * math.tau / 3, sx=-1, glow=0.8)
	p.blob((0.22, 0.1, 0.22), (0, -0.44, 0.62), CLOTH_WHITE, segs=(8, 5), glow=3.0)
	for a in (30, 150, 260):                                                              # sparks thrown off
		r = math.radians(a)
		d, n = Vector((math.cos(r), 0, math.sin(r))), Vector((-math.sin(r), 0, math.cos(r)))
		q = c + Vector((0, -0.3, 0))
		_zap(p, [tuple(q + d * 0.5), tuple(q + d * 0.6 + n * 0.06), tuple(q + d * 0.68 - n * 0.05), tuple(q + d * 0.82)], r=0.022)
	return p.build()


def serpent_plume():
	p = Prop("serpent_plume", 1719)
	for k, (ang, ln, sw) in enumerate(((-24, 1.05, SKY), (22, 1.1, SKY), (0, 1.4, AQUA))):   # a sky serpent's crest plume, three long feathers
		a = math.radians(ang)
		_vane(p, (0, -0.03 * k, 0.1), (math.sin(a) * ln, -0.03 * k, 0.1 + math.cos(a) * ln), 0.17 if k == 2 else 0.13, sw, tip_swatch=CLOTH_WHITE,
			  glow=0.8 if k == 2 else 0.0)
	for t, s_ in ((0.5, 1.0), (0.78, 0.7)):                                               # eyes shimmering on the longest
		q = (0, -0.1, 0.1 + 1.4 * t)
		p.blob((0.2 * s_, 0.03, 0.18 * s_), q, WATER, segs=(10, 4), glow=0.8)
		p.blob((0.09 * s_, 0.03, 0.08 * s_), (0, -0.12, q[2]), CLOTH_WHITE, segs=(8, 4), glow=2.0)
	p.seg((0, -0.05, -0.12), (0, -0.05, 0.16), 0.1, 0.09, STONE_LIGHT, sides=10, grad=(0.0, 0.45))   # bound at the quills in silver
	for k in range(2):                                                                    # a breath of wind along it
		_gust(p, _flat(-0.14), (-0.5 + 0.1 * k, 0.5 + 0.3 * k), 0.36, CLOTH_WHITE, curl=0.05, w=0.014, wave=0.02, glow=1.0)
	return p.build()


def cloudstone():
	p = Prop("cloudstone", 1721)
	c, size = (0.0, 0.0, 0.5), (1.1, 0.7, 0.9)
	p.blob(size, c, STONE_LIGHT, segs=(14, 10), grad=(0.0, 0.6), jitter=0.03)                    # a white-silver stone
	mf = _front_of(c, size)
	for k, (x, z, ln) in enumerate(((-0.42, 0.66, 0.6), (-0.3, 0.42, 0.7), (-0.38, 0.22, 0.5))):   # veined with cloud
		_gust(p, mf, (x, z), ln, CLOTH_WHITE, curl=0.07 - 0.015 * k, w=0.03, wave=0.03, glow=0.6)
	for x, z, s in ((-0.18, 0.84, 0.3), (0.12, 0.88, 0.34), (0.34, 0.78, 0.24)):              # and a wisp of cloud clinging to its top
		p.blob((s, s * 0.8, s * 0.6), (x, -0.05, z), CLOTH_WHITE, segs=(8, 6), grad=(0.0, 0.4))
	p.blob((0.1, 0.06, 0.1), mf(0.3, 0.4, 0.0), SKY, segs=(6, 4), glow=1.6)
	return p.build()


def skyship_sailcloth():
	p = Prop("skyship_sailcloth", 1723)
	_bolt(p, BONE, grad=(0.0, 0.5), stripe=SKY)                                                # a roll of skyship canvas, striped blue
	for x in (-0.3, 0.3):                                                                 # brass grommets along the unrolled edge
		p.seg((x, -0.52, 0.03), (x, -0.52, 0.05), 0.06, 0.06, GOLD, sides=10)
	pts = [(0.62, -0.5, 0.05), (0.8, -0.56, 0.08), (0.9, -0.44, 0.12), (0.8, -0.34, 0.1), (0.7, -0.42, 0.06), (0.86, -0.6, 0.04)]
	_line(p, pts, 0.03, 0.03, WOOD, sides=5)                                                # a coil of rigging line
	return p.build()


# Vayuketh's Step's drops

def titans_thunderstone():
	p = Prop("titans_thunderstone", 1725)
	c, size = (0.0, 0.0, 0.5), (1.1, 0.8, 0.95)
	p.blob(size, c, STONE_DARK, segs=(14, 10), grad=(0.0, 0.8), jitter=0.04)                    # a dark, heavy stone
	mf = _front_of(c, size)
	for pts in (((-0.4, 0.8), (-0.2, 0.6), (-0.28, 0.44), (-0.06, 0.24)), ((0.1, 0.84), (0.2, 0.62), (0.08, 0.48), (0.3, 0.3)),
				((-0.28, 0.44), (-0.44, 0.3))):                                            # split by glowing lightning
		_seam(p, [mf(x, z) for x, z in pts], swatch=SKY, r=0.03, glow=2.6)
	for pts in (((0.2, 1.0), (0.3, 1.14), (0.22, 1.22), (0.34, 1.36)), ((-0.3, 1.0), (-0.38, 1.12), (-0.3, 1.2))):   # crackling off its top
		_zap(p, [(x, -0.1, z) for x, z in pts], r=0.024)
	return p.build()


def temple_bronze():
	p = Prop("temple_bronze", 1727)
	outline = [(-0.66, 0.9), (0.4, 0.94), (0.62, 0.7), (0.5, 0.52), (0.66, 0.3), (0.5, 0.04), (-0.2, 0.0), (-0.36, 0.14), (-0.62, 0.08),
			   (-0.54, 0.46)]
	_slab(p, outline, -0.06, 0.06, BRONZE, grad=(0.4, 1.0))                                   # a broken plate of temple bronze
	for a, b in zip(outline[:2], outline[1:3]):
		p.seg((a[0], -0.065, a[1]), (b[0], -0.065, b[1]), 0.03, 0.03, GOLD, sides=4)           # a molded rim along its top
	fr = _flat(-0.07)
	for sx in (-1, 1):                                                                    # Vayuketh's wings cast on it
		_wing(p, fr, (sx * 0.04, 0.5), 0.46, sx, GOLD, arm=BRONZE, lift=22, n=5)
	p.blob((0.16, 0.08, 0.16), (0.0, -0.1, 0.5), GOLD, segs=(8, 5))
	for x, z, s in ((-0.42, 0.24, 0.2), (0.44, 0.2, 0.16), (0.3, 0.8, 0.14), (-0.5, 0.76, 0.12)):   # green with age
		p.blob((s, 0.03, s * 0.8), (x, -0.08, z), PATINA, segs=(8, 4), grad=(0.0, 0.6), jitter=0.01)
	return _tip_back(p.build(), -12)


stormscale = _repainted("stormscale", drake_scale, {STONE_DARK: (WATER, 0.35, 0.95), EMBER: (SKY, 0.0, 0.4), STONE_LIGHT: (CLOTH_WHITE, 0.0, 0.4)})


def shard_of_broken_breath():
	p = Prop("shard_of_broken_breath", 1729)
	base, top = Vector((-0.1, 0, 0.0)), Vector((0.18, 0, 1.1))
	p.seg(tuple(base), tuple(top), 0.3, 0.24, SKY, sides=6, grad=(0.0, 0.3), glow=0.3)          # a pale crystal
	d = (top - base).normalized()
	n = Vector((-d.z, 0, d.x))
	for k, (off, h) in enumerate(((-0.12, 0.22), (0.02, 0.1), (0.14, 0.26))):             # snapped off in jagged teeth
		q = top + n * off
		p.seg(tuple(q - d * 0.02), tuple(q + d * h), 0.1, 0.0, SKY, sides=4, grad=(0.0, 0.3), glow=0.3)
	for pts in (((0.0, 0.9), (0.08, 0.7), (-0.04, 0.56)), ((0.12, 0.4), (0.22, 0.3))):     # cracked through
		_line(p, [(x, -0.3, z) for x, z in pts], 0.012, 0.012, SEA_STONE, sides=4)
	_swirl(p, _flat(-0.31), (0.04, 0.5), 0.18, CLOTH_WHITE, turns=1.7, w=0.03, glow=2.4)          # a breath of wind caught inside
	for k in range(2):                                                                    # slipping out at the break
		_gust(p, _flat(-0.1), (0.2 + 0.05 * k, 1.2 + 0.14 * k), 0.28 - 0.06 * k, CLOTH_WHITE, curl=0.05, w=0.016, wave=0.02, glow=1.2)
	p.rock((0.26, 0.2, 0.2), (0.5, -0.1, 0.1), SKY, jitter=0.05)                               # a splinter fallen beside it
	return p.build()


# the named drops

def orlas_tuning_stone():
	p = Prop("orlas_tuning_stone", 1731)
	fr = _flat(0.0)
	p.seg((0, 0, -0.1), (0, 0, 0.36), 0.09, 0.08, WOOD, sides=8)                               # a wooden grip
	p.seg((0, 0, 0.0), (0, 0, 0.06), 0.11, 0.11, STONE_LIGHT, sides=8)
	_fork(p, fr, (0.0, 0.4), 1.2, SEA_STONE)                                                 # a tuning fork of singing stone
	p.seg((0, 0, 0.36), (0, 0, 0.44), 0.12, 0.12, STONE_LIGHT, sides=8)                        # banded in silver
	_rune(p, _flat(-0.1), (0.0, 0.46), 0.3, glow=2.0, r=0.016)
	for sx in (-1, 1):
		_hum(p, _flat(-0.05), (sx * 0.24, 1.08), sx, n=3, r0=0.14, dr=0.12, glow=1.8)
	return p.build()


def skathes_barbed_tail():
	p = Prop("skathes_barbed_tail", 1733)
	pts = [(-0.72, 0, 0.12), (-0.36, 0, 0.16), (0.0, 0, 0.3), (0.3, 0, 0.58), (0.42, 0, 0.9)]
	_line(p, pts, 0.2, 0.08, SEAFOAM, sides=10, grad=(0.1, 0.9))                               # a length of wyvern tail
	for i in range(4):                                                                    # spines down its back
		a, b = Vector(pts[i]), Vector(pts[i + 1])
		q = a.lerp(b, 0.5)
		dd = (b - a).normalized()
		up = Vector((-dd.z, 0, dd.x))
		r = 0.2 - 0.03 * i
		p.seg(tuple(q + up * r * 0.8), tuple(q + up * (r + 0.16) - dd * 0.08), 0.05, 0.0, STONE_DARK, sides=4)
	p.seg((-0.74, 0, 0.12), (-0.78, 0, 0.12), 0.2, 0.2, PINK, sides=10)                         # where it was cut off
	tip = Vector((0.42, 0, 0.9))
	sting = [tuple(tip - Vector((0.02, 0, 0.06))), (0.5, 0, 1.12), (0.46, 0, 1.4), (0.3, 0, 1.6)]
	_line(p, sting, 0.17, 0.0, BONE, sides=8, grad=(0.0, 0.6))                                 # the great barbed stinger
	for sx, z in ((-1, 1.02), (1, 1.1), (-1, 1.26), (1, 1.34)):
		q = (0.47 + sx * 0.1, -0.02, z)
		p.seg(q, (q[0] + sx * 0.2, -0.02, z - 0.18), 0.05, 0.0, BONE, sides=4)
	p.blob((0.1, 0.1, 0.12), (0.28, -0.02, 1.58), LEAF, segs=(6, 4), glow=2.2)                   # venom beading at its point
	return p.build()


def thrums_heartstone():
	p = Prop("thrums_heartstone", 1735)
	c, size = (0.0, 0.0, 0.6), (0.84, 0.62, 1.1)
	p.blob(size, c, SEA_STONE, segs=(16, 12), grad=(0.0, 0.8))                                  # the singing stone's heart, egg-smooth
	mf = _front_of(c, size)
	_rune(p, lambda x, z, off=0.0: mf(x, z, off + 0.03), (0.0, 0.6), 1.1, glow=3.0, r=0.045)    # its rune burning bright
	for a in range(0, 360, 45):                                                           # a ring of lesser marks round it
		r = math.radians(a + 22)
		p.blob((0.06, 0.04, 0.06), mf(math.cos(r) * 0.3, 0.62 + math.sin(r) * 0.4, -0.01), SKY, segs=(5, 3), glow=2.2)
	for sx in (-1, 1):
		_hum(p, _flat(-0.2), (sx * 0.5, 0.7), sx, n=2, r0=0.1, dr=0.12, glow=1.8)
	return p.build()


def mirewhistles_ladle():
	p = Prop("mirewhistles_ladle", 1737)
	p.seg((-0.2, 0, 0.38), (0.58, 0, 1.3), 0.05, 0.04, WOOD, sides=8)                          # a long, crooked wooden ladle
	_line(p, [(0.58, 0, 1.3), (0.66, 0, 1.4), (0.6, 0, 1.48)], 0.04, 0.03, WOOD, sides=6)
	c = (-0.3, 0.0, 0.26)
	p.seg((c[0], c[1], c[2] - 0.2), (c[0], c[1], c[2] + 0.12), 0.18, 0.36, WOOD, sides=14, grad=(0.1, 0.9))   # its deep bowl
	p.seg((c[0], c[1], c[2] + 0.1), (c[0], c[1], c[2] + 0.13), 0.33, 0.33, LEAF, sides=14, glow=1.4)   # brimming with green brew
	for x, z, s in ((-0.4, 0.44, 0.08), (-0.22, 0.46, 0.06)):                              # bubbling
		p.blob((s, s, s), (x, -0.04, z), LEAF, segs=(6, 4), glow=1.8)
	for x, ln in ((-0.6, 0.2), (-0.1, 0.14)):                                             # dripping over the rim
		p.seg((x, -0.08, 0.36), (x, -0.08, 0.36 - ln), 0.03, 0.01, LEAF, sides=4, glow=1.6)
	p.seg((0.52, -0.05, 1.18), (0.54, -0.1, 1.0), 0.012, 0.012, WOOD_GRAY, sides=4)            # a charm hung from the handle
	p.seg((0.54, -0.1, 1.02), (0.54, -0.1, 0.9), 0.05, 0.03, BONE, sides=6)
	for k in range(3):                                                                    # and a sprig of heather
		p.blob((0.06, 0.06, 0.06), (0.46 + 0.02 * k, -0.08, 1.12 - 0.05 * k), PETAL_PURPLE, segs=(5, 3))
	return p.build()


def hollow_winds_eye():
	p = Prop("hollow_winds_eye", 1739)
	c = (0, 0, 0.62)
	p.blob((1.0, 1.0, 1.0), c, SKY, segs=(16, 12), grad=(0.0, 0.5), glow=0.3)                   # a pale orb of wind
	p.seg((0, -0.47, 0.62), (0, -0.5, 0.62), 0.26, 0.26, STONE_DARK, sides=18)                  # hollow at its middle
	p.seg((0, -0.5, 0.62), (0, -0.52, 0.62), 0.14, 0.14, IRON, sides=14)
	for j in range(3):                                                                    # winds whirling into it
		_swirl(p, _flat(-0.5), (0.0, 0.62), 0.44, CLOTH_WHITE if j % 2 == 0 else SKY, turns=0.6, w=0.035, start=j * math.tau / 3, sx=-1, glow=1.4)
	for k in range(2):
		_gust(p, _flat(-0.3), (-0.8 + 0.06 * k, 0.2 + 0.7 * k), 0.4, CLOTH_WHITE, curl=0.06, w=0.016, wave=0.02, glow=1.0)
	return p.build()


def coilclouds_fang():
	p = Prop("coilclouds_fang", 1741)
	pts = [(-0.2, 0, 0.2), (0.06, 0, 0.56), (0.24, 0, 0.9), (0.24, 0, 1.18), (0.1, 0, 1.34)]
	_line(p, pts, 0.2, 0.0, BONE, sides=9, grad=(0.0, 0.6))                                   # a long, curved serpent's fang
	_line(p, [(-0.04, -0.17, 0.4), (0.14, -0.14, 0.72), (0.24, -0.1, 1.0)], 0.02, 0.012, SKY, sides=4, glow=2.0)   # its venom groove crackling blue
	for k in range(7):                                                                    # a puff of cloud about its root
		a = k * math.tau / 7
		p.blob((0.26, 0.2, 0.2), (-0.2 + math.cos(a) * 0.24, math.sin(a) * 0.14, 0.14 + 0.05 * (k % 2)), CLOTH_WHITE if k % 3 else ASH, segs=(8, 5),
			   grad=(0.0, 0.6))
	_zap(p, [(0.36, -0.14, 1.1), (0.48, -0.14, 1.2), (0.42, -0.14, 1.28), (0.54, -0.14, 1.38)], r=0.02, sw=CLOTH_WHITE)
	return p.build()


def hauvars_mist_crown():
	p = Prop("hauvars_mist_crown", 1743)
	p.seg((0, 0, 0.0), (0, 0, 0.18), 0.5, 0.52, STONE_LIGHT, sides=20, grad=(0.0, 0.5))          # a silver circlet
	_loop(p, (0, 0, 0.0), 0.51, True, 0.03, SKY, n=20)
	for k in range(7):                                                                    # tall points of pale crystal
		a = k * math.tau / 7 + 0.3
		h = 0.56 if k % 2 == 0 else 0.38
		x, y = math.cos(a) * 0.5, math.sin(a) * 0.5
		_crystal(p, (x, y, 0.14), (x * 1.08, y * 1.08, 0.18 + h), 0.07, sw=SKY, glow=0.8)
	for k in range(10):                                                                   # mist pouring round it
		a = math.radians(170 + k * 22)
		x, y = math.cos(a) * 0.6, math.sin(a) * 0.6
		p.blob((0.3, 0.24, 0.2), (x, y, 0.02 + 0.06 * (k % 3)), CLOTH_WHITE if k % 2 else ASH, segs=(8, 5), grad=(0.0, 0.5))
	a = math.radians(FRONT_A)
	for k in range(2):
		_gust(p, _tangent(FRONT_A, 0.7), (-0.4, 0.36 + 0.16 * k), 0.6, CLOTH_WHITE, curl=0.06, w=0.018, wave=0.03, glow=1.2)
	p.blob((0.14, 0.1, 0.16), (math.cos(a) * 0.53, math.sin(a) * 0.53, 0.1), SKY, segs=(8, 5), glow=2.4)
	return p.build()


def mirelas_spyglass():
	p = Prop("mirelas_spyglass", 1745)
	a, b = Vector((-0.66, 0, 0.18)), Vector((0.66, 0, 1.0))
	d = (b - a).normalized()
	for k, (t0, t1, r, sw) in enumerate(((0.0, 0.42, 0.17, GOLD), (0.42, 0.72, 0.14, WOOD), (0.72, 1.0, 0.11, GOLD))):   # three brass draws
		p.seg(tuple(a.lerp(b, t0)), tuple(a.lerp(b, t1)), r, r * 0.97, sw, sides=12, grad=(0.0, 0.6))
		p.seg(tuple(a.lerp(b, t0)), tuple(a.lerp(b, t0) + d * 0.05), r + 0.03, r + 0.03, GOLD, sides=12, grad=(0.3, 0.9))
	p.seg(tuple(a - d * 0.02), tuple(a - d * 0.05), 0.15, 0.15, SKY, sides=12, glow=1.6)            # its big lens
	p.seg(tuple(b), tuple(b + d * 0.04), 0.08, 0.08, STONE_DARK, sides=10)
	for t in (0.1, 0.3):                                                                  # a strap of sailcloth
		p.seg(tuple(a.lerp(b, t)), tuple(a.lerp(b, t) + d * 0.03), 0.18, 0.18, SKY, sides=12)
	_streamer(p, _flat(-0.2), (-0.36, 0.3), (0.3, -1), 0.4, 0.07, SKY, amp=0.04, n=8, tip_sw=CLOTH_WHITE)
	return p.build()


def _torc(p, c, R, r, sws, knob, gem, gap=1.1, gem_glow=2.0):
	"""An open torc facing the camera, its terminals either side of the gap at the top."""
	_twist_ring(p, c, (1, 0, 0), (0, 0, 1), R, r, sws, turns=9, gap=gap, n=44)
	ends = []
	for s in (1, -1):
		a = math.pi / 2 + s * (gap / 2 - 0.02)
		q = (c[0] + math.cos(a) * R, c[1], c[2] + math.sin(a) * R)
		p.blob((r * 4.4, r * 4.4, r * 4.4), q, knob, segs=(10, 6), grad=(0.0, 0.6))
		p.blob((r * 2.2, r * 1.6, r * 2.2), (q[0], q[1] - r * 1.9, q[2]), gem, segs=(8, 5), glow=gem_glow)
		ends.append(q)
	return ends


def vorlaugs_thunder_torc():
	p = Prop("vorlaugs_thunder_torc", 1747)
	ends = _torc(p, (0, 0, 0.6), 0.58, 0.075, (BRONZE, GOLD), STONE_DARK, SKY, gap=1.0, gem_glow=2.6)   # a giant's heavy bronze torc
	l, r = ends[1], ends[0]
	_zap(p, [(l[0] + 0.12, -0.2, l[2] + 0.06), (-0.04, -0.2, l[2] + 0.18), (0.04, -0.2, l[2] + 0.08), (r[0] - 0.12, -0.2, r[2] + 0.06)], r=0.026)   # thunder arcing across the gap
	for x, z, s in ((-0.5, 0.2, 0.12), (0.36, 0.12, 0.1)):                                 # green where the bronze is oldest
		p.blob((s, 0.05, s * 0.8), (x, -0.08, z), PATINA, segs=(6, 4))
	return p.build()


def first_guardians_seal():
	p = Prop("first_guardians_seal", 1749)
	p.seg((0, 0.06, 0.62), (0, -0.06, 0.62), 0.62, 0.62, BRONZE, sides=24, grad=(0.0, 0.8))     # a great bronze seal
	_loop(p, (0, -0.06, 0.62), 0.6, False, 0.04, GOLD, n=24)
	_loop(p, (0, -0.07, 0.62), 0.46, False, 0.02, GOLD, n=22)
	for k in range(12):                                                                   # notches round its rim
		a = k * math.tau / 12
		p.blob((0.05, 0.03, 0.05), (math.cos(a) * 0.53, -0.08, 0.62 + math.sin(a) * 0.53), STONE_DARK, segs=(5, 3))
	fr = _flat(-0.08)
	for sx in (-1, 1):                                                                    # stamped with Vayuketh's wings
		_wing(p, fr, (sx * 0.05, 0.6), 0.34, sx, GOLD, arm=BRONZE, lift=24, n=4)
	p.seg((0, -0.08, 0.64), (0, -0.14, 0.64), 0.1, 0.1, GOLD, sides=12)                        # and the guardian's eye
	p.blob((0.1, 0.06, 0.1), (0, -0.15, 0.64), SKY, segs=(8, 5), glow=2.4)
	for x, z, s in ((-0.36, 0.28, 0.18), (0.4, 0.92, 0.14), (0.3, 0.26, 0.12)):             # green with age
		p.blob((s, 0.03, s * 0.8), (x, -0.075, z), PATINA, segs=(8, 4), grad=(0.0, 0.6))
	return p.build()


def elder_drakes_stormheart():
	p = Prop("elder_drakes_stormheart", 1751)
	_heart(p, (0, 0, 0.6), 1.0, WATER, glow=1.0, grad=(0.2, 0.9))                              # a storm-blue drake's heart
	_heart(p, (-0.03, -0.14, 0.64), 0.56, SKY, glow=2.0)
	_heart(p, (-0.05, -0.24, 0.68), 0.22, CLOTH_WHITE, glow=3.0)                               # white-hot with lightning at its middle
	for pts in (((-0.46, 0.9), (-0.6, 1.02), (-0.54, 1.12), (-0.7, 1.26)), ((0.44, 0.94), (0.58, 1.02), (0.52, 1.14), (0.66, 1.3)),
				((0.36, 0.2), (0.5, 0.12), (0.46, 0.0)), ((-0.36, 0.3), (-0.52, 0.2), (-0.5, 0.06))):
		_zap(p, [(x, -0.2, z) for x, z in pts], r=0.024)
	p.seg((-0.08, 0.1, 1.0), (-0.14, 0.1, 1.22), 0.1, 0.08, WATER, sides=8, grad=(0.3, 1.0))      # torn vessels
	p.seg((0.14, 0.1, 1.0), (0.2, 0.1, 1.18), 0.08, 0.06, WATER, sides=8, grad=(0.3, 1.0))
	return p.build()


def fallen_breaths_sigh():
	p = Prop("fallen_breaths_sigh", 1753)
	p.blob((0.56, 0.56, 0.66), (0, 0, 0.36), CLOTH_WHITE, segs=(14, 10), grad=(0.1, 0.5))       # a small vial of pale glass
	top = _potion(p, 0.66, neck=0.24, neck_r=0.08, cork=STONE_LIGHT)
	_loop(p, (0, 0, 0.7), 0.1, True, 0.025, STONE_LIGHT, n=12)
	_swirl(p, _flat(-0.28), (0.0, 0.36), 0.2, SKY, turns=1.8, w=0.032, glow=2.6)                 # the last wisp of a dying wind inside
	_swirl(p, _flat(-0.29), (0.01, 0.38), 0.1, CLOTH_WHITE, turns=1.3, w=0.02, glow=3.0, start=2.0)
	_line(p, [(-0.2, -0.26, 0.5), (-0.06, -0.28, 0.46)], 0.01, 0.01, STONE_LIGHT, sides=4)      # a fine crack in the glass
	_frame(p, *POTION_FRAME)
	return p.build()


# rewards

def singers_torque():
	p = Prop("singers_torque", 1761)
	ends = _torc(p, (0, 0, 0.6), 0.5, 0.05, (STONE_LIGHT, SEA_STONE), SEA_STONE, SKY, gap=1.1)   # a torque of silver and stone
	for q, sx in zip(ends, (1, -1)):                                                      # its stone ends humming
		_hum(p, _flat(-0.2), (q[0] + sx * 0.12, q[2]), sx, n=2, r0=0.1, dr=0.1, spread=35, glow=1.8)
	return p.build()


def orlas_resonant_staff():
	p = Prop("orlas_resonant_staff", 1763)
	org, rot = (-0.3, -0.75), 74
	_haft(p, org, rot, 0.0, 1.62, 0.06, swatch=WOOD_GRAY, bands=(0.3, 0.9, 1.55), band_swatch=STONE_LIGHT)
	c = _rot2([(1.62, 0.0)], rot, org)[0]
	_fork(p, _flat(0.0), (c[0], c[1]), 0.9, SEA_STONE)                                       # crowned with a fork of singing stone
	p.blob((0.2, 0.16, 0.24), (c[0], -0.02, c[1] + 0.46), SKY, segs=(8, 6), glow=2.4)           # a blue stone humming in the fork
	for sx in (-1, 1):
		_hum(p, _flat(-0.1), (c[0] + sx * 0.22, c[1] + 0.62), sx, n=3, r0=0.12, dr=0.12, glow=1.8)
	return p.build()


def moorhide_cloak():
	p = Prop("moorhide_cloak", 1765)
	_slab(p, _cape_outline(0.3, 0.6, 0.12), 0.04, 0.1, STONE_DARK, grad=(0.2, 0.9))           # a cloak of shaggy moor-beast hide
	for row in range(4):                                                                  # its long hair in overlapping locks
		z = 0.94 - row * 0.25
		n = 6 + (row % 2)
		spread = 0.26 + row * 0.11
		w, ln = 0.09 + 0.01 * row, 0.42
		for k in range(n):
			x = (-1 + 2 * k / (n - 1)) * spread
			lean = x * 0.12
			pts = [(x - w, z), (x + w, z), (x + w * 0.8 + lean * 0.7, z - ln * 0.7), (x + lean + 0.02, z - ln), (x - w * 0.8 + lean * 0.7, z - ln * 0.7)]
			y = 0.03 - 0.012 * row - 0.002 * k
			p.poly([(a, y, b) for a, b in pts], [tuple(range(5))], WOOD_GRAY if (k + row) % 2 else STONE_WARM, grad=(0.2, 1.0))
			p.seg((x, y - 0.004, z - 0.04), (x + lean, y - 0.004, z - ln * 0.85), 0.012, 0.006, STONE_DARK, sides=3)
	for k in range(7):                                                                    # a thick collar
		x = -0.3 + k * 0.1
		p.blob((0.2, 0.14, 0.18), (x, -0.06, 0.99 + 0.02 * math.cos(x * 5)), WOOD_GRAY, segs=(6, 4), grad=(0.1, 0.7), jitter=0.015)
	p.blob((0.16, 0.08, 0.16), (0, -0.16, 0.97), STONE_LIGHT, segs=(8, 5))                      # pinned with a sprig of heather
	for k in range(4):
		p.blob((0.08, 0.08, 0.08), (0.08 + 0.04 * k, -0.2, 1.01 + 0.04 * k), PETAL_PURPLE, segs=(5, 3))
	return p.build()


def skathes_stinger():
	p = Prop("skathes_stinger", 1767)
	org, rot = (-0.5, -0.35), 50
	bf = _blade_frame(rot, org, 0.0)
	_line(p, [bf(0.3, 0.0), bf(0.7, 0.04), bf(1.05, 0.03), bf(1.36, -0.04)], 0.13, 0.0, BONE, sides=8, grad=(0.0, 0.6))   # a wyvern's stinger for a blade
	for u, s in ((0.62, 1), (0.8, -1), (0.98, 1)):                                        # barbed
		p.seg(bf(u, s * 0.07), bf(u - 0.14, s * 0.2), 0.04, 0.0, BONE, sides=4)
	p.seg(bf(0.6, 0.0, 0.1), bf(1.2, -0.02, 0.06), 0.014, 0.008, LEAF, sides=4, glow=1.8)        # venom glowing down its groove
	p.blob((0.08, 0.08, 0.08), bf(1.36, -0.05, 0.02), LEAF, segs=(6, 4), glow=2.2)
	for s in (1, -1):                                                                     # a guard of tail spines
		p.seg(bf(0.28, 0.0), bf(0.34, s * 0.26), 0.05, 0.0, STONE_DARK, sides=5)
	p.seg(bf(0.3, 0.0), bf(0.26, 0.0), 0.15, 0.15, SEAFOAM, sides=10)
	h = _rot2([(0.26, 0.0), (-0.14, 0.0), (-0.22, 0.0)], rot, org)
	p.seg((h[0][0], 0, h[0][1]), (h[1][0], 0, h[1][1]), 0.055, 0.06, SEAFOAM, sides=6)          # a grip of wyvern hide
	for t in (0.2, 0.5, 0.8):
		q = (h[0][0] + (h[1][0] - h[0][0]) * t, h[0][1] + (h[1][1] - h[0][1]) * t)
		p.seg((q[0] - 0.015, 0, q[1] - 0.015), (q[0] + 0.015, 0, q[1] + 0.015), 0.066, 0.066, STONE_DARK, sides=6)
	p.blob((0.14, 0.14, 0.14), (h[2][0], 0, h[2][1]), STONE_DARK, segs=(8, 6))
	return p.build()


def runeshard_ring():
	p = Prop("runeshard_ring", 1769)
	_ring(p, STONE_LIGHT)                                                                  # a silver band
	outline = [(-0.2, 0.74), (0.18, 0.76), (0.26, 1.02), (0.08, 1.36), (-0.16, 1.2), (-0.26, 0.98)]
	_slab(p, outline, -0.08, 0.08, SEA_STONE, grad=(0.0, 0.8))                               # set with a shard of standing stone
	for sx in (-1, 1):                                                                    # held by silver claws
		p.seg((sx * 0.16, -0.06, 0.74), (sx * 0.24, -0.1, 0.92), 0.035, 0.02, STONE_LIGHT, sides=5)
	_rune(p, _flat(-0.09), (0.0, 1.02), 0.6, glow=2.6, r=0.022)
	return p.build()


def thrumstone_greathammer():
	p = Prop("thrumstone_greathammer", 1771)
	org, rot = (-0.5, -0.8), 62
	_haft(p, org, rot, -0.2, 1.55, 0.075, swatch=WOOD, bands=(0.0, 0.5, 1.0), band_swatch=STONE_LIGHT)
	c = _rot2([(1.72, 0.0)], rot, org)[0]
	p.box((1.2, 0.62, 0.62), (c[0], 0, c[1]), SEA_STONE, rot=(0, -rot + 90, 0), grad=(0.0, 0.8), jitter=0.03)   # a block of Old Thrum's stone
	long_axis = Euler((0, math.radians(-rot + 90), 0)).to_matrix() @ Vector((1, 0, 0))
	for s in (-0.36, 0.36):                                                               # banded in silver
		q = Vector((c[0], 0, c[1])) + long_axis * s
		p.box((0.1, 0.68, 0.68), tuple(q), STONE_LIGHT, rot=(0, -rot + 90, 0), grad=(0.0, 0.45))
	_rune(p, _flat(-0.34), (c[0], c[1]), 0.5, glow=2.8, r=0.03)                                  # its rune glowing
	for pts in (((c[0] + 0.2, c[1] + 0.5), (c[0] + 0.3, c[1] + 0.62), (c[0] + 0.24, c[1] + 0.7), (c[0] + 0.36, c[1] + 0.82)),):
		_zap(p, [(x, -0.3, z) for x, z in pts], r=0.022, sw=SKY)
	_hum(p, _flat(-0.3), (c[0] + 0.62, c[1] - 0.1), 1, n=2, r0=0.1, dr=0.12, glow=1.8)
	return p.build()


def hagknot_charm():
	p = Prop("hagknot_charm", 1773)
	_twist_ring(p, (0, 0, 0.4), (1, 0, 0), (0, 0, 1), 0.4, 0.05, (ASH, WOOD_GRAY), turns=8)   # a band braided of gray hair
	p.blob((0.3, 0.26, 0.28), (0, -0.02, 0.86), ASH, segs=(8, 6), jitter=0.03)                   # tied off in a hag's knot
	_oval(p, (0, -0.02, 0.86), (1, 0, 0), (0, 0.6, 0.8), 0.18, 0.14, 0.035, WOOD_GRAY, n=12)
	p.seg((-0.08, -0.16, 0.86), (0.08, -0.16, 0.9), 0.06, 0.06, BONE, sides=8)                   # a bone bead
	p.blob((0.1, 0.08, 0.1), (0.14, -0.2, 1.0), LEAF, segs=(6, 4), glow=1.6)
	_strands(p, 1773, 6, (0.0, -0.1, 0.8), 0.2, 0.4, [ASH, CLOTH_WHITE], ASH, 0.0)
	return p.build()


def mirewhistle_shawl():
	p = Prop("mirewhistle_shawl", 1775)
	top = [(-0.8, 0.84), (-0.5, 0.98), (0.0, 1.02), (0.5, 0.98), (0.8, 0.84)]
	outline = top + [(0.0, -0.1)]
	_slab(p, outline, 0.0, 0.06, PINE, grad=(0.1, 0.8))                                       # a knitted shawl, moss green, hung point down
	for k, sw in enumerate((PETAL_PURPLE, WOOD_GRAY, PETAL_PURPLE)):                       # heather stripes following its edges
		d = 0.14 + 0.18 * k
		pts = [(-0.8 + d * 1.2, 0.84 - d * 0.1), (0.0, -0.1 + d * 1.25), (0.8 - d * 1.2, 0.84 - d * 0.1)]
		_line(p, [(x, -0.01, z) for x, z in pts], 0.035, 0.035, sw, sides=4)
	for a, b in ((top[0], (0.0, -0.1)), (top[-1], (0.0, -0.1))):                           # a fringe of tassels along its edges
		for k in range(8):
			q = Vector(a).lerp(Vector(b), (k + 0.5) / 8)
			out = -1 if a[0] < 0 else 1
			p.seg((q.x, 0.0, q.y), (q.x + out * 0.03, -0.01, q.y - 0.14), 0.03, 0.018, PETAL_PURPLE if k % 2 else PINE, sides=4)
	_line(p, [(x, -0.01, z + 0.01) for x, z in top], 0.03, 0.03, WOOD_GRAY, sides=5)             # a rolled top edge
	p.seg((0, -0.02, 0.98), (0, -0.1, 0.98), 0.09, 0.09, WOOD, sides=8)                          # a wooden toggle
	p.blob((0.22, 0.08, 0.07), (0, -0.12, 0.98), BONE, segs=(8, 4))
	for x, z in ((-0.34, 0.6), (0.2, 0.34)):                                               # patched and darned
		p.box((0.14, 0.02, 0.12), (x, -0.015, z), HIDE)
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(29), 4, "Z"))                          # turned to face the viewer
	return obj


tempest_bracer = _repainted("tempest_bracer", galescout_bracer, {HIDE: (WATER, 0.4, 0.95), WOOD: (STONE_DARK, 0.1, 0.7), SKY: (CLOTH_WHITE, 0.0, 0.4),
																   CLOTH_WHITE: (SKY, 0.0, 0.5)})


def hollow_eye_amulet():
	p = Prop("hollow_eye_amulet", 1777)
	_cord(p, 0.45, 0.88, STONE_LIGHT)                                                      # a silver chain
	c = (0, -0.3, 0.36)
	_oval(p, c, (1, 0, 0), (0, 0, 1), 0.26, 0.26, 0.045, STONE_LIGHT, n=20)                   # a silver hoop, hollow in the middle
	p.blob((0.22, 0.22, 0.22), c, SKY, segs=(10, 8), grad=(0.0, 0.5), glow=2.0)               # a bead of wind held in it
	for j in range(2):
		_swirl(p, _flat(c[1] - 0.12), (0.0, c[2]), 0.2, CLOTH_WHITE, turns=0.6, w=0.022, start=j * math.pi, sx=-1, glow=1.6)
	for s in (1, -1):                                                                     # on silver spokes
		p.seg((s * 0.11, c[1], c[2]), (s * 0.24, c[1], c[2]), 0.015, 0.015, STONE_LIGHT, sides=4)
	p.seg((0, -0.3, 0.62), (0, -0.3, 0.78), 0.03, 0.03, STONE_LIGHT, sides=5)
	return p.build()


def plumed_belt():
	p = Prop("plumed_belt", 1779)
	f, out, tan = _belt(p, SEA_STONE, STONE_LIGHT, STONE_LIGHT)                              # a blue-gray leather belt, silver buckle
	for k, (dx, ln, sw) in enumerate(((-0.12, 0.62, AQUA), (0.02, 0.72, SKY), (0.16, 0.58, AQUA))):   # sky serpent plumes hung from it
		base = f + out * 0.08 + tan * dx - Vector((0, 0, 0.12))
		tip = base + Vector((dx * 0.8, 0, -ln))
		_vane(p, tuple(base), tuple(tip), 0.1, sw, tip_swatch=CLOTH_WHITE)
	return p.build()


coilcloud_bow = _repainted("coilcloud_bow", galehold_longbow, {BONE: (AQUA, 0.0, 0.7), SKY: (CLOTH_WHITE, 0.0, 0.4), OCHRE: (SKY, 0.0, 0.5)})
cloudstone_pauldrons = _repainted("cloudstone_pauldrons", skyforged_vambraces, {STONE_LIGHT: (CLOTH_WHITE, 0.15, 0.85), SKY: (STONE_LIGHT, 0.0, 0.5),
																				 CLOTH_WHITE: (SKY, 0.0, 0.4)})


def mistcrown_helm():
	p = Prop("mistcrown_helm", 1781)
	for z0, z1, r0, r1 in ((0.0, 0.3, 0.42, 0.42), (0.3, 0.52, 0.42, 0.34), (0.52, 0.68, 0.34, 0.2), (0.68, 0.76, 0.2, 0.0)):
		p.seg((0, 0, z0), (0, 0, z1), r0, r1, STONE_LIGHT, sides=16, grad=(0.0, 0.45))       # a bright silver dome
	p.seg((0, 0, 0.2), (0, 0, 0.3), 0.44, 0.44, CLOTH_WHITE, sides=18, grad=(0.0, 0.4))           # circled by the mist-crown
	for k in range(7):                                                                    # its pale crystal points
		a = math.radians(FRONT_A - 72 + k * 24)
		x, y = math.cos(a) * 0.44, math.sin(a) * 0.44
		_crystal(p, (x, y, 0.26), (x * 1.06, y * 1.06, 0.5 + (0.16 if k % 2 == 1 else 0.0) + (0.1 if k == 3 else 0.0)), 0.05, sw=SKY, glow=0.8)
	p.seg((0, -0.42, 0.34), (0, -0.46, -0.1), 0.06, 0.045, STONE_LIGHT, sides=5, grad=(0.0, 0.45))   # a nasal
	for sx in (-1, 1):                                                                    # cheek guards
		p.seg((sx * 0.36, -0.2, 0.1), (sx * 0.34, -0.24, -0.26), 0.12, 0.08, STONE_LIGHT, sides=6, grad=(0.0, 0.45))
	for k in range(9):                                                                    # mist spilling off the brim
		a = math.radians(150 + k * 26)
		p.blob((0.26, 0.2, 0.16), (math.cos(a) * 0.5, math.sin(a) * 0.5, -0.02 + 0.05 * (k % 2)), CLOTH_WHITE if k % 2 else ASH, segs=(8, 5),
			   grad=(0.0, 0.5))
	a = math.radians(FRONT_A)
	p.blob((0.12, 0.08, 0.12), (math.cos(a) * 0.46, math.sin(a) * 0.46, 0.25), SKY, segs=(8, 5), glow=2.4)
	return p.build()


sailcloth_gloves = _repainted("sailcloth_gloves", windrunner_gloves, {HIDE: (BONE, 0.0, 0.7), SKY: (WATER, 0.3, 0.9)})
driftwind_cutlass = _repainted("driftwind_cutlass", khans_curved_blade, {CLOTH_RED: (SKY, 0.2, 0.8), GOLD: (STONE_LIGHT, 0.0, 0.4), OCHRE: (CLOTH_WHITE, 0.0, 0.4),
																		 IRON: (CLOTH_WHITE, 0.0, 0.5), STONE_DARK: (SKY, 0.0, 0.6)})


def thunderstone_girdle():
	p = Prop("thunderstone_girdle", 1783)
	f, out, tan = _belt(p, WOOD, STONE_LIGHT, STONE_DARK, stripes=((0.0, SKY, 1.2),))          # a broad girdle, a blue thread glowing through it
	q = f + out * 0.1
	p.blob((0.28, 0.16, 0.3), tuple(q), STONE_DARK, segs=(10, 6), grad=(0.0, 0.8))               # set with a thunderstone
	_seam(p, [tuple(q + out * 0.08 + tan * -0.06 + Vector((0, 0, 0.1))), tuple(q + out * 0.08 + tan * 0.02 + Vector((0, 0, 0.0))),
			  tuple(q + out * 0.08 + tan * -0.02 + Vector((0, 0, -0.04))), tuple(q + out * 0.08 + tan * 0.06 + Vector((0, 0, -0.12)))], swatch=SKY, r=0.02,
		  glow=2.6)
	_zap(p, [tuple(q + tan * 0.2 + Vector((0, -0.05, 0.12))), tuple(q + tan * 0.3 + Vector((0, -0.05, 0.22))), tuple(q + tan * 0.26 + Vector((0, -0.05, 0.3))),
			 tuple(q + tan * 0.36 + Vector((0, -0.05, 0.42)))], r=0.02)
	return p.build()


def vorlaugs_torc():
	p = Prop("vorlaugs_torc", 1785)
	_torc(p, (0, 0, 0.6), 0.5, 0.055, (GOLD, STONE_LIGHT), GOLD, SKY, gap=1.1, gem_glow=2.4)  # a giant's torc, cut down and polished
	for x, z in ((-0.62, 0.3), (0.6, 0.36)):                                                # small sparks
		_zap(p, [(x, -0.12, z), (x + 0.06, -0.12, z + 0.08), (x + 0.02, -0.12, z + 0.14)], r=0.018, sw=SKY)
	return p.build()


temple_bronze_boots = _repainted("temple_bronze_boots", skyforged_boots, {STONE_LIGHT: (BRONZE, 0.35, 0.95), SKY: (PATINA, 0.0, 0.6), CLOTH_WHITE: (GOLD, 0.0, 0.5)})
guardians_sealblade = _repainted("guardians_sealblade", skyforged_sword, {STONE_LIGHT: (BRONZE, 0.3, 0.8), SKY: (PATINA, 0.0, 0.6), CLOTH_WHITE: (GOLD, 0.0, 0.5)})
stormscale_leggings = _repainted("stormscale_leggings", scaled_leggings, {LEAF: (WATER, 0.35, 0.95), WOOD: (STONE_DARK, 0.1, 0.8)})


def stormheart_shield():
	p = Prop("stormheart_shield", 1787)
	p.seg((0, 0.06, 0.7), (0, -0.06, 0.7), 0.7, 0.7, WATER, sides=24, grad=(0.35, 1.0))        # a round storm-blue shield
	for k in range(16):                                                                   # rimmed in silver
		a0, a1 = k * math.tau / 16, (k + 1) * math.tau / 16
		p.seg((math.cos(a0) * 0.7, -0.03, 0.7 + math.sin(a0) * 0.7), (math.cos(a1) * 0.7, -0.03, 0.7 + math.sin(a1) * 0.7), 0.07, 0.07, STONE_LIGHT, sides=6,
			  grad=(0.0, 0.45))
	for a in (0.4, 1.5, 2.6, 3.6, 4.7, 5.6):                                              # lightning forking out from its heart
		pts = [(math.cos(a) * r + 0.04 * math.sin(r * 23 + a), -0.075, 0.7 + math.sin(a) * r + 0.04 * math.cos(r * 19)) for r in (0.2, 0.32, 0.44, 0.58)]
		_zap(p, pts, r=0.02, sw=CLOTH_WHITE, glow=2.4)
	_heart(p, (0, -0.1, 0.72), 0.36, SKY, glow=2.2)                                          # the drake's stormheart for a boss
	_heart(p, (-0.01, -0.16, 0.74), 0.16, CLOTH_WHITE, glow=3.0)
	for k in range(4):                                                                    # silver studs
		a = k * math.tau / 4 + math.pi / 4
		p.blob((0.08, 0.06, 0.08), (math.cos(a) * 0.52, -0.08, 0.7 + math.sin(a) * 0.52), STONE_LIGHT, segs=(6, 4))
	return p.build()


def breathshard_ring():
	p = Prop("breathshard_ring", 1789)
	_ring(p, STONE_LIGHT)                                                                  # a silver band
	p.seg((0.0, 0, 0.78), (0.04, 0, 1.22), 0.13, 0.1, SKY, sides=6, grad=(0.0, 0.3), glow=0.4)   # a shard of the broken breath
	p.seg((0.04, 0, 1.22), (0.06, 0, 1.34), 0.1, 0.0, SKY, sides=6, grad=(0.0, 0.3), glow=0.4)
	for sx in (-1, 1):
		p.seg((sx * 0.1, -0.02, 0.76), (sx * 0.14, -0.08, 0.9), 0.03, 0.02, STONE_LIGHT, sides=5)
	_swirl(p, _flat(-0.14), (0.02, 1.0), 0.08, CLOTH_WHITE, turns=1.6, w=0.018, glow=2.6)
	return p.build()


def _last_breath_wisps():
	p = Prop("last_breath_wisps", 1791)
	for k in range(3):                                                                    # its wind still leaving it
		_gust(p, _flat(-0.2), (-0.5 + 0.1 * k, 0.2 + 0.26 * k), 0.8 - 0.1 * k, SKY, curl=0.07, w=0.024, wave=0.03, glow=1.8)
	return p.build()


mantle_of_the_last_breath = _repainted("mantle_of_the_last_breath", thunderwing_cloak,
									   {WATER: (CLOTH_WHITE, 0.2, 0.9), SKY: (STONE_LIGHT, 0.0, 0.4), CLOTH_WHITE: (SKY, 0.0, 0.3)}, _last_breath_wisps)


SKY_SUMMIT = [stormcrest_helm, stormcrest_breastplate, stormcrest_vambraces, stormcrest_gauntlets, stormcrest_greaves, stormcrest_boots,
			  stormcrest_shield, cloudhide_jerkin, cloudhide_leggings, cloudhide_gloves, cloudhide_boots, skysilk_cap, skysilk_robe,
			  skysilk_gloves, skysilk_slippers, stormcrest_sword, stormcrest_war_axe, stormcrest_greataxe, cloudpiercer_dirk,
			  thundercloud_staff, summit_longbow, stormfeather_arrow, singing_stone_chip, moor_hide, rune_shard, hags_hair_knot,
			  tempest_mote, serpent_plume, cloudstone, skyship_sailcloth, titans_thunderstone, temple_bronze, stormscale,
			  shard_of_broken_breath, orlas_tuning_stone, skathes_barbed_tail, thrums_heartstone, mirewhistles_ladle, hollow_winds_eye,
			  coilclouds_fang, hauvars_mist_crown, mirelas_spyglass, vorlaugs_thunder_torc, first_guardians_seal, elder_drakes_stormheart,
			  fallen_breaths_sigh, singers_torque, orlas_resonant_staff, moorhide_cloak, skathes_stinger, runeshard_ring,
			  thrumstone_greathammer, hagknot_charm, mirewhistle_shawl, tempest_bracer, hollow_eye_amulet, plumed_belt, coilcloud_bow,
			  cloudstone_pauldrons, mistcrown_helm, sailcloth_gloves, driftwind_cutlass, thunderstone_girdle, vorlaugs_torc,
			  temple_bronze_boots, guardians_sealblade, stormscale_leggings, stormheart_shield, breathshard_ring, mantle_of_the_last_breath]


# ---------------------------------------------------------------- the Boneyard: Barrowhold's 45-50 gear, Fogfall, the Ivory Field, the Unlit
# Barrowhold's tier repaints the Stormcrest, Cloudhide and Skysilk shapes: Eclipsed
# plate in blackened steel with violet and silver, Umbral leather in violet-black,
# Starweave in midnight-blue silk scattered with silver stars. Fogfall is tarnished
# silver, gargoyle stone and fog; the Ivory Field is ivory, bone and carrion black;
# the Unlit is violet dark, pale moonlight and a vampire house's crimson.

ECLIPSED = {STONE_LIGHT: (IRON, 0.0, 0.45), SKY: (PETAL_PURPLE, 0.15, 0.7), CLOTH_WHITE: (STONE_LIGHT, 0.0, 0.35)}
UMBRAL = {HIDE: (PETAL_PURPLE, 0.6, 1.0), WOOD: (IRON, 0.0, 0.5), CLOTH_WHITE: (PETAL_PURPLE, 0.1, 0.45), SKY: (STONE_LIGHT, 0.0, 0.4),
		  OCHRE: (STONE_LIGHT, 0.0, 0.4)}
STARWEAVE = {CLOTH_WHITE: (WATER, 0.86, 1.0), SKY: (STONE_LIGHT, 0.0, 0.3)}


def _star(p, c, s, sw=CLOTH_WHITE, glow=2.6):
	"""A four-pointed star facing the camera, c its middle."""
	x, y, z = c
	for dx, dz in ((1, 0), (0, 1)):
		p.seg((x - dx * s, y, z - dz * s), (x, y, z), 0.0, s * 0.22, sw, sides=4, glow=glow)
		p.seg((x, y, z), (x + dx * s, y, z + dz * s), s * 0.22, 0.0, sw, sides=4, glow=glow)


def _stars(name, seed, pts):
	"""An extra for _repainted: silver star points at (x, y, z, size)."""
	def build():
		p = Prop(name, seed)
		for x, y, z, s in pts:
			_star(p, (x, y, z), s)
		return p.build()
	return build


def _starry(name, base, swaps, spots):
	"""_repainted with silver stars scattered over the front of the shape: spots are
	(x, z, size), x and z as fractions of its width and height."""
	def build():
		obj = _repaint(base(), swaps)
		obj.name = name
		vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
		lo = [min(v[i] for v in vs) for i in range(3)]
		hi = [max(v[i] for v in vs) for i in range(3)]
		p = Prop(name + "_stars", 1851)
		for fx, fz, sz in spots:
			_star(p, (lo[0] + (hi[0] - lo[0]) * fx, lo[1] - 0.02, lo[2] + (hi[2] - lo[2]) * fz), sz)
		p.build()
		return obj
	build.__name__ = name
	return build


def _crescent(p, c, R, sw=CLOTH_WHITE, glow=1.6, turn=0.0):
	"""A crescent moon facing the camera, its horns turned by `turn` degrees."""
	x, y, z = c
	pts = []
	for k in range(13):
		a = math.radians(turn + 50 + k * 260 / 12)
		t = abs(k - 6) / 6
		pts.append(((x + math.cos(a) * R, y, z + math.sin(a) * R), R * (0.3 - 0.26 * t)))
	for (a, ra), (b, rb) in zip(pts, pts[1:]):
		p.seg(a, b, ra, rb, sw, sides=6, grad=(0.0, 0.4), glow=glow)


def _moonwood_moon():
	p = Prop("moonwood_moon", 1801)
	c = _rot2([(1.95, 0.0)], 72, (-0.3, -0.7))[0]
	_crescent(p, (c[0] - 0.04, -0.16, c[1] + 0.04), 0.46, sw=FLAME, glow=0.8, turn=160)                           # a crescent moon round the staff's stone
	for x, z, s in ((-0.36, 0.4, 0.07), (0.34, 0.16, 0.06)):
		_star(p, (c[0] + x, -0.14, c[1] + z), s)
	return p.build()


def _nightwing_stars():
	p = Prop("nightwing_stars", 1803)
	for x, z, s in ((-0.5, 0.62, 0.07), (0.16, 0.66, 0.06), (-0.14, 0.3, 0.05)):
		_star(p, (x, -0.12, z), s, sw=PETAL_PURPLE, glow=2.2)
	return p.build()


eclipsed_helm = _repainted("eclipsed_helm", skyforged_helm, ECLIPSED)
eclipsed_breastplate = _repainted("eclipsed_breastplate", skyforged_breastplate, ECLIPSED)
eclipsed_vambraces = _repainted("eclipsed_vambraces", skyforged_vambraces, ECLIPSED)
eclipsed_gauntlets = _repainted("eclipsed_gauntlets", skyforged_gauntlets, ECLIPSED)
eclipsed_greaves = _repainted("eclipsed_greaves", skyforged_greaves, ECLIPSED)
eclipsed_boots = _repainted("eclipsed_boots", skyforged_boots, ECLIPSED)
eclipsed_shield = _repainted("eclipsed_shield", skyforged_shield, {SKY: (IRON, 0.0, 0.45), STONE_LIGHT: (PETAL_PURPLE, 0.1, 0.6),
																   CLOTH_WHITE: (STONE_LIGHT, 0.0, 0.3)})
umbral_jerkin = _repainted("umbral_jerkin", windrunner_jerkin, UMBRAL)
umbral_leggings = _repainted("umbral_leggings", windrunner_leggings, UMBRAL)
umbral_gloves = _repainted("umbral_gloves", windrunner_gloves, UMBRAL)
umbral_boots = _repainted("umbral_boots", windrunner_boots, UMBRAL)
starweave_cap = _starry("starweave_cap", galeweave_cap, STARWEAVE, [(0.42, 0.72, 0.09), (0.74, 0.54, 0.08), (0.56, 0.4, 0.07)])
starweave_robe = _starry("starweave_robe", galeweave_robe, STARWEAVE, [(0.46, 0.66, 0.09), (0.72, 0.42, 0.08), (0.5, 0.24, 0.07), (0.8, 0.76, 0.07)])
starweave_gloves = _starry("starweave_gloves", galeweave_gloves, STARWEAVE, [(0.52, 0.66, 0.08), (0.68, 0.4, 0.07)])
starweave_slippers = _starry("starweave_slippers", galeweave_slippers, STARWEAVE, [(0.42, 0.62, 0.08), (0.78, 0.52, 0.07)])
eclipse_blade = _repainted("eclipse_blade", skyforged_sword, ECLIPSED)
umbral_war_axe = _repainted("umbral_war_axe", skyforged_war_axe, ECLIPSED)
nightfall_greataxe = _repainted("nightfall_greataxe", skyforged_greataxe, {STONE_LIGHT: (IRON, 0.0, 0.45), SKY: (WATER, 0.72, 1.0),
																		   CLOTH_WHITE: (PETAL_PURPLE, 0.0, 0.4)})
starshard_dirk = _repainted("starshard_dirk", zephyr_dirk, {CLOTH_WHITE: (SKY, 0.0, 0.25), SKY: (WATER, 0.72, 1.0)})
moonwood_staff = _repainted("moonwood_staff", stormwood_staff, {WOOD_GRAY: (BONE, 0.2, 0.9), SKY: (SKY, 0.0, 0.3)}, _moonwood_moon)
barrowhold_longbow = _repainted("barrowhold_longbow", galehold_longbow, {BONE: (IRON, 0.0, 0.5), SKY: (PETAL_PURPLE, 0.2, 0.8),
																		 OCHRE: (STONE_LIGHT, 0.0, 0.4)})
nightwing_arrow = _repainted("nightwing_arrow", windcutter_arrow, {SKY: (PETAL_PURPLE, 0.45, 1.0), BONE: (IRON, 0.0, 0.5),
																	CLOTH_WHITE: (ASH, 0.55, 0.85)}, _nightwing_stars)


# Fogfall's drops

def tarnished_court_silver():
	p = Prop("tarnished_court_silver", 1805)
	p.seg((0, 0, 0.0), (0, 0, 0.05), 0.34, 0.34, STONE_LIGHT, sides=18, grad=(0.1, 0.6))       # a court goblet of silver
	p.seg((0, 0, 0.05), (0, 0, 0.16), 0.3, 0.08, STONE_LIGHT, sides=18, grad=(0.1, 0.6))
	p.seg((0, 0, 0.16), (0, 0, 0.58), 0.07, 0.07, STONE_LIGHT, sides=10, grad=(0.1, 0.6))
	p.blob((0.2, 0.2, 0.14), (0, 0, 0.36), STONE_LIGHT, segs=(10, 6), grad=(0.1, 0.6))
	p.seg((0, 0, 0.56), (0, 0, 0.68), 0.08, 0.3, STONE_LIGHT, sides=18, grad=(0.1, 0.6))
	p.seg((0, 0, 0.68), (0, 0, 1.14), 0.3, 0.4, STONE_LIGHT, sides=18, grad=(0.0, 0.55))
	p.seg((0, 0, 1.12), (0, 0, 1.15), 0.37, 0.37, STONE_DARK, sides=18)                          # its dark inside
	_loop(p, (0, 0, 1.14), 0.4, True, 0.025, STONE_LIGHT, n=18)
	a = math.radians(FRONT_A)
	cx, cy = math.cos(a) * 0.36, math.sin(a) * 0.36
	p.blob((0.2, 0.06, 0.22), (cx, cy, 0.9), GOLD, segs=(8, 5))                                 # the court's crest, gilt
	for k in range(9):                                                                    # gone black with tarnish
		b = math.radians(FRONT_A - 70 + k * 19)
		z = 0.76 + 0.3 * ((k * 7) % 5) / 5
		r = 0.3 + (z - 0.68) * 0.22 + 0.01
		p.blob((0.12 + 0.03 * (k % 3), 0.04, 0.1), (math.cos(b) * r, math.sin(b) * r, z), IRON, segs=(6, 4), grad=(0.2, 0.6))
	for x, y, z in ((0.52, -0.3, 0.14), (0.4, -0.5, 0.05)):                                   # tarnished coins at its foot
		p.seg((x, y, z - 0.03), (x, y, z + 0.03), 0.2, 0.2, STONE_LIGHT, sides=16, grad=(0.3, 0.8))
		p.blob((0.1, 0.1, 0.02), (x + 0.04, y, z + 0.035), IRON, segs=(6, 3))
	return p.build()


def gargoyle_stone():
	p = Prop("gargoyle_stone", 1807)
	p.rock((0.9, 0.7, 0.4), (0.0, 0.1, 0.18), STONE_DARK, jitter=0.07)                         # a gargoyle's head broken off at the neck
	p.blob((0.78, 0.66, 0.62), (0.0, 0.0, 0.62), SEA_STONE, segs=(12, 8), grad=(0.0, 0.8), jitter=0.04)
	p.blob((0.5, 0.5, 0.36), (0.02, -0.3, 0.5), SEA_STONE, segs=(10, 6), grad=(0.0, 0.8), jitter=0.03)   # its snout
	for sx in (-1, 1):
		p.seg((sx * 0.3, -0.22, 0.8), (sx * 0.06, -0.32, 0.74), 0.06, 0.05, STONE_DARK, sides=5)      # a scowling brow
		p.blob((0.1, 0.06, 0.07), (sx * 0.17, -0.32, 0.69), FLAME, segs=(6, 4), glow=2.6)            # eyes still lit
		_line(p, [(sx * 0.24, 0.05, 0.86), (sx * 0.44, 0.08, 1.12), (sx * 0.4, 0.12, 1.36)], 0.1, 0.0, STONE_DARK, sides=6)   # horns
		p.seg((sx * 0.1, -0.5, 0.38), (sx * 0.12, -0.52, 0.24), 0.04, 0.0, STONE_LIGHT, sides=4)      # fangs
	for x, z in ((-0.16, 0.5), (0.18, 0.54)):                                             # nostrils
		p.blob((0.05, 0.03, 0.04), (x * 0.5, -0.55, z), STONE_DARK, segs=(5, 3))
	for x, y, z, s in ((-0.34, -0.12, 0.92, 0.14), (0.3, 0.12, 0.3, 0.12), (-0.4, -0.2, 0.2, 0.1)):   # moss
		p.blob((s, s * 0.8, s * 0.5), (x, y, z), PINE, segs=(6, 4), grad=(0.2, 0.7))
	return p.build()


fog_hound_pelt = _repainted("fog_hound_pelt", wolf_pelt, {WOOD_GRAY: (ASH, 0.3, 0.55), STONE_LIGHT: (CLOTH_WHITE, 0.0, 0.5)})


def stolen_grave_goods():
	p = Prop("stolen_grave_goods", 1809)
	p.seg((-0.1, 0.1, 0.0), (-0.1, 0.1, 0.08), 0.2, 0.26, BRONZE, sides=14)                    # a grave's bronze urn
	p.seg((-0.1, 0.1, 0.08), (-0.1, 0.1, 0.5), 0.26, 0.4, BRONZE, sides=14, grad=(0.2, 0.9))
	p.seg((-0.1, 0.1, 0.5), (-0.1, 0.1, 0.8), 0.4, 0.2, BRONZE, sides=14, grad=(0.2, 0.9))
	p.seg((-0.1, 0.1, 0.8), (-0.1, 0.1, 0.9), 0.17, 0.22, BRONZE, sides=14)
	for z in (0.46, 0.56):                                                                # banded with a key pattern
		_loop(p, (-0.1, 0.1, z), 0.41, True, 0.02, GOLD, n=16)
	for x, y, z, s in ((-0.36, -0.14, 0.3, 0.14), (0.1, -0.2, 0.66, 0.1)):                    # green with age
		p.blob((s, 0.04, s * 0.8), (x, y, z), PATINA, segs=(6, 4))
	p.seg((0.42, -0.08, 0.86), (0.5, -0.04, 1.02), 0.2, 0.1, BRONZE, sides=10)                   # its lid pried off beside it
	for k, (x, y) in enumerate(((0.4, -0.4), (0.62, -0.2), (0.2, -0.56), (0.66, -0.52), (0.46, -0.66))):   # coins for the dead
		z = 0.02 + 0.03 * (k % 2)
		p.seg((x, y, z), (x, y, z + 0.04), 0.13, 0.13, GOLD, sides=14, grad=(0.1, 0.6))
	c = (0.16, -0.42, 0.3)                                                                # a gold ring
	_oval(p, c, (1, 0, 0), (0, 0.4, 0.9), 0.16, 0.16, 0.04, GOLD, n=14)
	p.blob((0.1, 0.08, 0.1), (c[0], c[1] - 0.04, c[2] + 0.16), CLOTH_RED, segs=(6, 4), glow=0.6)
	for k in range(9):                                                                    # a string of beads spilling out
		t = k / 8
		p.blob((0.08, 0.08, 0.08), (-0.4 + 0.5 * t, -0.3 - 0.2 * math.sin(t * 3), 0.05), DAWN if k % 2 else BONE, segs=(6, 4))
	return p.build()


ismays_mourning_veil = _repainted("ismays_mourning_veil", nomad_veil, {WATER: (PETAL_PURPLE, 0.6, 1.0), GOLD: (STONE_LIGHT, 0.0, 0.4), SKY: (IRON, 0.05, 0.5),
																	   AMBER: (STONE_DARK, 0.0, 0.6)})


def grimwatchs_stone_heart():
	p = Prop("grimwatchs_stone_heart", 1811)
	_heart(p, (0, 0, 0.6), 1.0, STONE_DARK, grad=(0.0, 0.7))                                   # a heart of gargoyle stone
	for pts in (((-0.34, 0.9), (-0.22, 0.7), (-0.3, 0.52), (-0.1, 0.36), (-0.02, 0.12)), ((0.3, 0.86), (0.2, 0.66), (0.3, 0.5)),
				((-0.1, 0.36), (0.14, 0.3))):                                              # cracked, and burning inside
		_seam(p, [(x, -0.32, z) for x, z in pts], swatch=FLAME, r=0.028, glow=2.6)
	for x, z, s in ((-0.36, 0.3, 0.16), (0.36, 0.96, 0.12)):                                 # moss in its cracks
		p.blob((s, 0.08, s * 0.7), (x, -0.26, z), PINE, segs=(6, 4))
	for x, z, s in ((0.5, 0.0, 0.14), (0.66, 0.1, 0.1), (-0.5, -0.04, 0.12)):               # chips fallen from it
		p.rock((s, s, s * 0.8), (x, -0.1, z), SEA_STONE, jitter=0.03)
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(26), 4, "Z"))                          # turned to face the viewer
	return obj


def whitemaws_collar():
	p = Prop("whitemaws_collar", 1813)
	f, out, tan = _belt(p, WOOD, IRON, IRON, R=0.56, h=0.24)                                   # a great hound's leather collar
	for k in range(14):                                                                   # ringed with iron spikes
		a = k * math.tau / 14 + 0.2
		d = Vector((math.cos(a), math.sin(a), 0))
		if d.dot(out) > 0.93:
			continue
		q = Vector((0, 0.1, 0.5)) + d * 0.57
		p.seg(tuple(q), tuple(q + d * 0.2), 0.05, 0.0, STONE_LIGHT, sides=5, grad=(0.0, 0.5))
	q = f + out * 0.08 - Vector((0, 0, 0.14))                                             # an iron ring for the chain
	_oval(p, tuple(q - Vector((0, 0, 0.1))), tuple(tan), (0, 0, 1), 0.1, 0.12, 0.025, IRON, n=12)
	for k, (dx, dz) in enumerate(((-0.34, 0.1), (-0.22, 0.14), (0.28, 0.08))):          # tufts of white fur caught in it
		b = f + tan * dx + out * 0.04 + Vector((0, 0, dz))
		p.blob((0.14, 0.1, 0.1), tuple(b), CLOTH_WHITE, segs=(6, 4), grad=(0.0, 0.5))
		p.seg(tuple(b), tuple(b + Vector((0.02, -0.04, -0.16))), 0.05, 0.0, CLOTH_WHITE, sides=4, grad=(0.0, 0.5))
	return p.build()


crowes_black_lantern = _repainted("crowes_black_lantern", widows_lantern, {BONE: (IRON, 0.1, 0.6), WOOD: (STONE_DARK, 0.2, 1.0),
																		   CLOTH_RED: (PETAL_PURPLE, 0.2, 0.7)})


# the Ivory Field's drops

def ivory_shard():
	p = Prop("ivory_shard", 1815)
	pts = [Vector(q) for q in ((-0.5, 0, 0.1), (-0.22, 0, 0.36), (0.08, 0, 0.64), (0.32, 0, 0.96))]
	_line(p, [tuple(q) for q in pts], 0.26, 0.2, BONE, sides=10, grad=(0.0, 0.6))                # a length of ivory broken from a tusk
	d0, d1 = (pts[1] - pts[0]).normalized(), (pts[3] - pts[2]).normalized()
	p.seg(tuple(pts[0] - d0 * 0.012), tuple(pts[0] + d0 * 0.01), 0.262, 0.262, AMBER, sides=10, grad=(0.0, 0.3))   # its old yellowed break
	p.seg(tuple(pts[0] - d0 * 0.018), tuple(pts[0] - d0 * 0.022), 0.14, 0.14, STONE_WARM, sides=10)
	n = Vector((-d1.z, 0, d1.x))
	for off, h in ((-0.13, 0.26), (0.02, 0.12), (0.13, 0.34), (0.0, 0.2)):                # snapped off in splinters at the other end
		q = pts[3] + n * off + Vector((0, -0.06 if off == 0.0 else 0.04, 0))
		p.seg(tuple(q - d1 * 0.04), tuple(q + d1 * h), 0.09, 0.0, BONE, sides=4, grad=(0.0, 0.5))
	for k in range(3):                                                                    # its grain
		a, b = pts[k], pts[k + 1]
		p.seg(tuple(a + Vector((0.03, -0.24, 0.02))), tuple(b + Vector((0.02, -0.2, -0.02))), 0.01, 0.01, STONE_WARM, sides=4)
	return p.build()


def _tusk(p, base, ang, s, curl, r, sw=BONE, grad=(0.0, 0.6), y=0.0, n=8):
	"""A tusk in the picture plane from base, heading `ang` degrees and curling `curl`
	over its length s. Returns its points."""
	pts, q = [], Vector((base[0], base[1]))
	for k in range(n + 1):
		pts.append((q.x, y, q.y))
		a = math.radians(ang + curl * k / n)
		q = q + Vector((math.cos(a), math.sin(a))) * s / n
	_line(p, pts, r, r * 0.12, sw, sides=10, grad=grad)
	return pts


def poached_ivory():
	p = Prop("poached_ivory", 1817)
	for k, (b, ang, curl) in enumerate((((-0.6, 0.2), 22, 40), ((-0.66, -0.2), 4, 44))):   # two tusks sawn off at the root
		pts = _tusk(p, b, ang, 1.5, curl, 0.2, y=-0.16 * k)
		d = (Vector(pts[1]) - Vector(pts[0])).normalized()
		p.seg(tuple(Vector(pts[0]) - d * 0.01), tuple(Vector(pts[0]) + d * 0.015), 0.205, 0.205, STONE_WARM, sides=10)   # the saw cut
		p.seg(tuple(Vector(pts[0]) - d * 0.015), tuple(Vector(pts[0]) - d * 0.02), 0.12, 0.12, PINK, sides=10)
	for t in (0.14, 0.2):                                                                 # lashed together with rope
		c = (-0.6 + 1.5 * t * 0.95, 0.07, 0.1 + 1.5 * t * 0.45)
		_oval(p, c, (0.4, 0, -0.9), (0, 1, 0), 0.26, 0.3, 0.03, WOOD, n=12)
	p.seg((-0.3, -0.2, 0.34), (-0.36, -0.24, 0.1), 0.02, 0.02, WOOD, sides=4)                  # a poacher's tally tag
	p.box((0.16, 0.03, 0.2), (-0.36, -0.25, 0.02), CLOTH_RED, rot=(0, 10, 0))
	return p.build()


carrion_feather = _repainted("carrion_feather", gull_feather, {CLOTH_WHITE: (IRON, 0.0, 0.55), ASH: (STONE_DARK, 0.3, 1.0), STONE_LIGHT: (BONE, 0.3, 0.9)})


def _ghost_wisps():
	p = Prop("ghost_wisps", 1819)
	for k in range(3):
		_gust(p, _flat(-0.3), (-0.1 + 0.14 * k, 0.3 + 0.2 * k), 0.4, SKY, curl=0.06, w=0.02, wave=0.03, glow=1.8)
	return p.build()


ghost_ivory = _repainted("ghost_ivory", orc_tusk, {BONE: (SKY, 0.0, 0.25), HIDE: (CLOTH_WHITE, 0.2, 0.7)}, _ghost_wisps)


# the Unlit's drops

shade_essence = _repainted("shade_essence", smoke_essence, {STONE_DARK: (IRON, 0.0, 0.5), ASH: (PETAL_PURPLE, 0.45, 0.95),
															 CLOTH_WHITE: (PETAL_PURPLE, 0.0, 0.25), CLOTH_RED: (PETAL_PURPLE, 0.3, 0.6)})
shadowhide = _repainted("shadowhide", smoke_pelt, {ASH: (PETAL_PURPLE, 0.55, 0.95), STONE_DARK: (IRON, 0.0, 0.55), IRON: (PETAL_PURPLE, 0.8, 1.0)})
luminous_dust = _repainted("luminous_dust", fire_moth_dust, {GOLD: (SKY, 0.0, 0.35), FLAME: (CLOTH_WHITE, 0.0, 0.3), OCHRE: (SKY, 0.1, 0.5),
															  WOOD: (STONE_DARK, 0.0, 0.8), HIDE: (ASH, 0.3, 0.6)})


def _bat(p, c, s, sw, y_off=0.0, grad=(0.0, 0.6)):
	"""A bat with spread wings, flat toward the camera, c its body's middle."""
	x, y, z = c
	for sx in (-1, 1):                                                                    # scalloped wings
		pts = [(0.06, 0.1), (0.3, 0.26), (0.56, 0.3), (0.76, 0.16), (0.62, 0.02), (0.54, -0.1), (0.42, 0.0), (0.3, -0.12), (0.2, 0.0), (0.08, -0.1)]
		_slab(p, [(x + sx * px * s, z + pz * s) for px, pz in (pts if sx > 0 else pts[::-1])], y - 0.01, y + 0.02, sw, grad=grad)
	p.blob((0.16 * s, 0.1 * s, 0.34 * s), (x, y - 0.03, z), sw, segs=(8, 5), grad=grad)            # its body
	p.blob((0.14 * s, 0.1 * s, 0.13 * s), (x, y - 0.04, z + 0.2 * s), sw, segs=(8, 5), grad=grad)
	for sx in (-1, 1):
		p.seg((x + sx * 0.04 * s, y - 0.04, z + 0.26 * s), (x + sx * 0.07 * s, y - 0.04, z + 0.36 * s), 0.03 * s, 0.0, sw, sides=4)   # ears


HEATER = [(-0.5, 1.2), (0.5, 1.2), (0.5, 0.6), (0.4, 0.3), (0.2, 0.08), (0.0, 0.0), (-0.2, 0.08), (-0.4, 0.3), (-0.5, 0.6)]   # a heater shield's outline


def morvaine_crest():
	p = Prop("morvaine_crest", 1821)
	_slab(p, HEATER, -0.05, 0.05, CRIMSON, grad=(0.3, 1.0))                                  # House Morvaine's crest: a crimson field
	for a, b in zip(HEATER, HEATER[1:] + HEATER[:1]):                                    # rimmed in silver
		p.seg((a[0], -0.06, a[1]), (b[0], -0.06, b[1]), 0.04, 0.04, STONE_LIGHT, sides=6, grad=(0.0, 0.45))
	_bat(p, (0.0, -0.07, 0.66), 0.62, IRON)                                                   # its black bat
	for sx in (-1, 1):
		p.blob((0.03, 0.02, 0.02), (sx * 0.03, -0.12, 0.8), CRIMSON, segs=(4, 3), glow=2.0)
	for k in range(5):                                                                    # under a silver coronet
		x = -0.2 + 0.1 * k
		p.seg((x, -0.02, 1.22), (x, -0.02, 1.34 + 0.06 * (k % 2)), 0.035, 0.0, STONE_LIGHT, sides=4)
	p.seg((-0.24, -0.02, 1.2), (0.24, -0.02, 1.26), 0.04, 0.04, STONE_LIGHT, sides=6)
	return p.build()


# the named drops

def ossuary_heartbone():
	p = Prop("ossuary_heartbone", 1823)
	_heart(p, (0, 0, 0.62), 0.95, BONE, grad=(0.0, 0.7))                                       # a heart of fused bone
	for pts in (((-0.3, 0.86), (-0.2, 0.64), (-0.26, 0.46), (-0.06, 0.3), (0.0, 0.1)), ((0.26, 0.84), (0.18, 0.62), (0.3, 0.44))):
		_seam(p, [(x, -0.31, z) for x, z in pts], swatch=SKY, r=0.03, glow=2.6)                  # a ghost-blue light in its seams
	for sx, ang in ((-1, 110), (1, 70), (-1, 150), (1, 30)):                               # rib-ends and knuckles growing from it
		a = math.radians(ang)
		b = Vector((sx * 0.22 + math.cos(a) * 0.3, 0.0, 0.82 + math.sin(a) * 0.3))
		tip = b + Vector((math.cos(a), 0, math.sin(a))) * 0.3
		p.seg(tuple(b), tuple(tip), 0.06, 0.05, BONE, sides=6, grad=(0.0, 0.6))
		p.blob((0.12, 0.12, 0.12), tuple(tip), BONE, segs=(6, 4), grad=(0.0, 0.6))
	for x, z in ((-0.14, 0.42), (0.14, 0.36), (0.0, 0.6)):                                  # sockets
		p.blob((0.07, 0.04, 0.06), (x, -0.32, z), STONE_DARK, segs=(6, 3))
	return p.build()


def vargas_tusk_saw():
	p = Prop("vargas_tusk_saw", 1825)
	org, rot = (-0.6, 0.0), 32
	bf = _blade_frame(rot, org, 0.0)
	blade = [(0.3, 0.14), (1.5, 0.1), (1.56, 0.02), (1.5, -0.2), (0.3, -0.24)]
	_slab(p, [bf(u, v)[0::2] for u, v in blade], -0.02, 0.02, STONE_LIGHT, grad=(0.0, 0.5))   # a long saw blade
	for k in range(15):                                                                   # its big teeth
		u = 0.34 + k * 0.08
		pts = [bf(u, -0.23)[0::2], bf(u + 0.08, -0.23)[0::2], bf(u + 0.07, -0.33)[0::2]]
		_slab(p, pts, -0.02, 0.02, STONE_LIGHT, grad=(0.3, 0.7))
	p.seg(bf(0.3, 0.12), bf(1.5, 0.08), 0.03, 0.03, IRON, sides=6)                            # a stiffened back
	for u in (0.6, 1.1):                                                                  # clotted with ivory dust and worse
		p.blob((0.12, 0.04, 0.06), bf(u, -0.2, 0.03), BONE, segs=(6, 3))
	p.blob((0.08, 0.04, 0.05), bf(0.84, -0.18, 0.03), CLOTH_RED, segs=(6, 3))
	h = [(0.3, 0.2), (0.04, 0.28), (-0.2, 0.18), (-0.24, -0.1), (-0.06, -0.3), (0.3, -0.3)]   # a pistol-grip handle of dark wood
	_line(p, [bf(u, v) for u, v in h], 0.07, 0.07, WOOD, sides=6)
	for u, v in ((0.22, 0.0), (0.26, -0.18)):
		p.seg(bf(u, v, 0.02), bf(u, v, 0.08), 0.03, 0.03, GOLD, sides=6)                       # brass rivets
	return p.build()


def _beak(p, c, s, sw=STONE_WARM, tip=IRON):
	"""A vulture's hooked beak in the picture plane, its base at c, pointing right."""
	x, y, z = c
	up = [(0.0, 0.0), (0.3, 0.08), (0.62, 0.08), (0.86, 0.0), (0.98, -0.16), (0.92, -0.3)]
	pts = [(x + u * s, y, z + v * s) for u, v in up]
	_line(p, pts[:4], 0.2 * s, 0.1 * s, sw, sides=10, grad=(0.1, 0.8))                        # the upper bill
	_line(p, pts[3:], 0.1 * s, 0.0, tip, sides=8, grad=(0.0, 0.6))                            # hooked at its dark tip
	_line(p, [(x + 0.02 * s, y, z - 0.18 * s), (x + 0.36 * s, y, z - 0.18 * s), (x + 0.64 * s, y, z - 0.12 * s)], 0.13 * s, 0.03 * s, sw, sides=8)   # the lower bill
	p.blob((0.06 * s, 0.04 * s, 0.04 * s), (x + 0.24 * s, y - 0.18 * s, z + 0.04 * s), STONE_DARK, segs=(6, 3))   # nostril
	return pts


def gorgemaws_beak():
	p = Prop("gorgemaws_beak", 1827)
	_beak(p, (-0.5, 0.0, 0.5), 1.25)                                                          # the great carrion bird's beak
	for k in range(9):                                                                    # torn off with a ruff of black feathers
		a = math.radians(90 + k * 22)
		b = (-0.58, 0.02 * k, 0.4)
		_vane(p, b, (b[0] + math.cos(a) * 0.44 - 0.1, b[1], b[2] + math.sin(a) * 0.46), 0.14, IRON if k % 2 else STONE_DARK)
	p.blob((0.1, 0.06, 0.08), (-0.2, -0.24, 0.3), CLOTH_RED, segs=(6, 3))                      # still bloody
	return p.build()


def grandmothers_tusk():
	p = Prop("grandmothers_tusk", 1829)
	pts = _tusk(p, (-0.7, -0.1), 20, 2.2, 70, 0.34, grad=(0.1, 0.8))                          # an ancient matriarch's great tusk
	for i, t in enumerate((2, 4, 6)):                                                      # carved bands and gold rings
		a, b = Vector(pts[t]), Vector(pts[t + 1])
		d = (b - a).normalized()
		r = 0.34 - 0.3 * t / 8 + 0.03
		p.seg(tuple(a), tuple(a + d * 0.05), r, r, GOLD if i != 1 else STONE_WARM, sides=10)
	for k in range(4):                                                                    # carved lines of the herd's memory
		a, b = Vector(pts[3]), Vector(pts[4])
		q = a.lerp(b, 0.2 + 0.2 * k) + Vector((0, -0.2, 0))
		p.seg(tuple(q + Vector((-0.04, 0, 0.06))), tuple(q + Vector((0.04, 0, -0.06))), 0.015, 0.015, STONE_WARM, sides=4)
	q = Vector(pts[2]) + Vector((0, -0.2, -0.1))                                          # prayer cords hung from it
	for k, sw in enumerate((CLOTH_RED, GOLD, CLOTH_RED)):
		e = q + Vector((-0.06 + 0.08 * k, 0, -0.36 - 0.06 * k))
		p.seg(tuple(q), tuple(e), 0.015, 0.015, WOOD, sides=4)
		p.blob((0.07, 0.07, 0.07), tuple(e), sw, segs=(6, 4))
	for x, z in ((0.1, 0.36), (-0.1, 0.22)):                                               # and old cracks
		p.seg((x, -0.24, z), (x + 0.1, -0.24, z + 0.04), 0.012, 0.012, STONE_WARM, sides=4)
	return p.build()


def nameless_echo():
	p = Prop("nameless_echo", 1831)
	for k, (sw, glow) in enumerate(((PETAL_PURPLE, 1.2), (PETAL_PURPLE, 0.6), (CLOTH_WHITE, 0.0))):   # a blank face, and its echoes behind it
		x, y, z = 0.28 - 0.14 * k, 0.3 - 0.15 * k, 0.72 - 0.05 * k
		p.blob((0.62, 0.22, 0.86), (x, y, z), sw, segs=(14, 10), grad=(0.0, 0.5) if k == 2 else (0.3, 0.9), glow=glow)
		for sx in (-1, 1):
			p.blob((0.1, 0.06, 0.06), (x + sx * 0.13, y - 0.1, z + 0.1), IRON, segs=(6, 3))          # no mouth, no name
	for sx in (-1, 1):
		_hum(p, _flat(-0.3), (sx * 0.44 - 0.02, 0.62), sx, n=3, r0=0.12, dr=0.12, sw=PETAL_PURPLE, glow=2.0)
	return p.build()


starveils_eye = _repainted("starveils_eye", vitrax_eye, {PETAL_PURPLE: (WATER, 0.6, 1.0), CLOTH_WHITE: (SKY, 0.0, 0.2)},
						   _stars("starveil_stars", 1833, [(-0.1, -0.7, 0.9, 0.08), (0.12, -0.7, 0.56, 0.06), (0.5, -0.4, 1.1, 0.07)]))


def moon_moths_antenna():
	p = Prop("moon_moths_antenna", 1835)
	pts = [(-0.3, 0.0, 0.0), (-0.16, 0.0, 0.4), (0.02, 0.0, 0.8), (0.24, 0.0, 1.16), (0.5, 0.0, 1.42)]
	_line(p, pts, 0.05, 0.025, STONE_LIGHT, sides=6, grad=(0.0, 0.5))                         # a moon moth's feathered antenna
	for i in range(len(pts) - 1):
		a, b = Vector(pts[i]), Vector(pts[i + 1])
		d = (b - a).normalized()
		n = Vector((-d.z, 0, d.x))
		for k in range(5):
			t = (i + k / 5) / (len(pts) - 1)
			q = a.lerp(b, k / 5)
			ln = 0.34 * math.sin(math.pi * (0.1 + 0.85 * t))
			for s in (-1, 1):                                                              # combed with fine barbs
				p.seg(tuple(q), tuple(q + n * s * ln + d * ln * 0.45), 0.018, 0.006, CLOTH_WHITE if k % 2 else SKY, sides=4, grad=(0.0, 0.4),
					  glow=0.5)
	p.blob((0.1, 0.1, 0.1), pts[-1], CLOTH_WHITE, segs=(8, 5), glow=3.0)                      # its tip still glowing
	p.blob((0.12, 0.1, 0.12), pts[0], STONE_DARK, segs=(8, 5))
	return p.build()


countess_locket = _repainted("countess_locket", veyamar_locket, {GOLD: (IRON, 0.0, 0.5), PINK: (CRIMSON, 0.2, 0.8)})


# rewards

courtiers_signet = _repainted("courtiers_signet", court_signet, {GOLD: (STONE_LIGHT, 0.0, 0.5), FLAME: (STONE_LIGHT, 0.0, 0.3), CLOTH_RED: (WATER, 0.6, 1.0)})



mourning_veil_cowl = _repainted("mourning_veil_cowl", sootveil_hood, {ASH: (IRON, 0.0, 0.5), STONE_DARK: (ASH, 0.5, 0.8), FLAME: (SKY, 0.0, 0.3),
																	  EMBER: (STONE_LIGHT, 0.0, 0.4)})


def gargoyle_hide_vambraces():
	p = Prop("gargoyle_hide_vambraces", 1839)
	t0, t1, r0, r1 = _vambrace(p, SEA_STONE, STONE_DARK, WOOD, IRON, grad=(0.0, 0.85), glow_line=FLAME)   # plates of gargoyle hide, stone-hard
	for t in (-0.3, -0.06, 0.18):                                                         # stone horns along the ridge
		r = _fa_r(t, r0, r1, t0, t1) + 0.03
		p.seg(_fa(t, r, -25), _fa(t + 0.1, r + 0.2, -25), 0.06, 0.0, STONE_DARK, sides=5)
	for t, ang in ((-0.2, 20), (0.1, -50)):                                               # and moss on it
		r = _fa_r(t, r0, r1, t0, t1) + 0.02
		p.blob((0.1, 0.06, 0.08), _fa(t, r, ang), PINE, segs=(6, 4))
	return p.build()


stoneheart_shield = _repainted("stoneheart_shield", stormheart_shield, {WATER: (STONE_DARK, 0.2, 1.0), STONE_LIGHT: (STONE_WARM, 0.2, 0.9),
																		 SKY: (SEA_STONE, 0.2, 0.9), CLOTH_WHITE: (FLAME, 0.0, 0.5)})
foghound_cloak = _repainted("foghound_cloak", moorhide_cloak, {WOOD_GRAY: (CLOTH_WHITE, 0.2, 0.8), STONE_WARM: (ASH, 0.15, 0.4), STONE_DARK: (ASH, 0.45, 0.7),
															  PETAL_PURPLE: (SKY, 0.0, 0.4)})
whitemaw_fang_dirk = _repainted("whitemaw_fang_dirk", tawnyjaw_fang_dirk, {WOOD: (IRON, 0.0, 0.6), AMBER: (CLOTH_WHITE, 0.1, 0.6), HIDE: (ASH, 0.2, 0.5)})
robbers_sash = _repainted("robbers_sash", skiffrunner_sash, {CLOTH_WHITE: (WOOD, 0.3, 1.0), SKY: (STONE_DARK, 0.2, 1.0), AMBER: (IRON, 0.0, 0.6)})
black_lantern_charm = _repainted("black_lantern_charm", lampwardens_charm, {GOLD: (IRON, 0.0, 0.5), FLAME: (PETAL_PURPLE, 0.0, 0.4)})
ivory_bracer = _repainted("ivory_bracer", courtiers_bracer, {IRON: (BONE, 0.05, 0.6), CLOTH_RED: (HIDE, 0.4, 1.0), EMBER: (WOOD, 0.3, 0.9)})
def ossuary_greatmaul():
	p = Prop("ossuary_greatmaul", 1853)
	org, rot = (-0.5, -0.8), 62
	_haft(p, org, rot, -0.2, 1.55, 0.075, swatch=WOOD_GRAY, bands=(0.0, 0.5, 1.0), band_swatch=BONE)
	cx, cz = _rot2([(1.74, 0.0)], rot, org)[0]
	c = Vector((cx, 0, cz))
	a = math.radians(rot)
	d, n = Vector((math.cos(a), 0, math.sin(a))), Vector((-math.sin(a), 0, math.cos(a)))
	p.seg(tuple(c - n * 0.52), tuple(c + n * 0.52), 0.2, 0.2, BONE, sides=12, grad=(0.0, 0.6))   # a great beast's thighbone for a head
	for s in (-1, 1):                                                                     # knuckled at both ends
		for e in (-1, 1):
			p.blob((0.34, 0.32, 0.34), tuple(c + n * s * 0.56 + d * e * 0.13), BONE, segs=(10, 7), grad=(0.0, 0.6))
	p.seg(tuple(c - d * 0.24), tuple(c + d * 0.24), 0.23, 0.23, IRON, sides=10, grad=(0.1, 0.6))   # bound to the haft with iron
	for s in (-1, 1):
		p.seg(tuple(c + n * s * 0.26 - Vector((0, 0.22, 0))), tuple(c + n * s * 0.26 - Vector((0, 0.18, 0)) + d * 0.04), 0.03, 0.03, STONE_DARK, sides=4)
	_seam(p, [tuple(c + n * 0.08 + Vector((0, -0.2, 0))), tuple(c + n * 0.24 + d * 0.06 + Vector((0, -0.19, 0))),
			  tuple(c + n * 0.4 - d * 0.04 + Vector((0, -0.19, 0)))], swatch=SKY, r=0.022, glow=2.4)   # a ghost-blue crack
	return p.build()
poachers_bane_gloves = _repainted("poachers_bane_gloves", serpentscale_gloves, {LEAF: (WOOD, 0.3, 1.0), AMBER: (BONE, 0.0, 0.6), PINE: (HIDE, 0.4, 1.0)})
tusksaw_cleaver = _repainted("tusksaw_cleaver", rattlejaws_cleaver, {STONE_DARK: (BONE, 0.0, 0.6), CLAY: (STONE_WARM, 0.2, 0.8)})
carrion_feather_cloak = _repainted("carrion_feather_cloak", rocfeather_cloak, {CLOTH_WHITE: (IRON, 0.0, 0.5), WOOD: (STONE_DARK, 0.2, 1.0), DAWN: (CRIMSON, 0.5, 1.0),
																			  GOLD: (ASH, 0.6, 0.9), AMBER: (IRON, 0.0, 0.6)})


def gorgemaw_beak_amulet():
	p = Prop("gorgemaw_beak_amulet", 1841)
	_cord(p, 0.45, 0.88, WOOD)                                                             # a leather thong
	p.seg((0, -0.27, 0.68), (0, -0.27, 0.58), 0.05, 0.05, GOLD, sides=8)                        # a gold cap
	_beak(p, (-0.02, -0.28, 0.5), 0.46)                                                        # Gorgemaw's beak hanging from it, hook down
	for sx in (-1, 1):                                                                    # between two black feathers
		_vane(p, (sx * 0.08, -0.26, 0.62), (sx * 0.3, -0.26, 0.2), 0.08, IRON)
	return p.build()


ghost_ivory_ring = _repainted("ghost_ivory_ring", wraithbone_ring, {BONE: (SKY, 0.0, 0.3), PETAL_PURPLE: (CLOTH_WHITE, 0.0, 0.3)})


def grandmothers_blessing():
	p = Prop("grandmothers_blessing", 1843)
	_cord(p, 0.45, 0.88, CLOTH_RED)                                                        # a red prayer cord
	pts = _tusk(p, (-0.14, 0.52), -80, 0.62, 50, 0.1, y=-0.3)                                 # a little tusk, carved from the Grandmother's
	p.seg((-0.14, -0.3, 0.46), (-0.14, -0.3, 0.56), 0.11, 0.11, GOLD, sides=10)                 # capped in gold
	for k in range(3):                                                                    # carved rings
		q = Vector(pts[2 + k])
		p.seg(tuple(q), tuple(q + Vector((0.01, 0, -0.02))), 0.1 - 0.02 * k, 0.1 - 0.02 * k, STONE_WARM, sides=8)
	for sx in (-1, 1):                                                                    # beads either side
		for k in range(3):
			p.blob((0.06, 0.06, 0.06), (sx * (0.14 + 0.08 * k) - 0.02, -0.28, 0.62 + 0.05 * k), GOLD if k % 2 else CLOTH_RED, segs=(6, 4))
	return p.build()


shade_silk_gloves = _repainted("shade_silk_gloves", glassweb_gloves, {STONE_LIGHT: (PETAL_PURPLE, 0.55, 0.95), AQUA: (IRON, 0.0, 0.5), CLOTH_WHITE: (PETAL_PURPLE, 0.0, 0.3)})


def echo_of_the_nameless():
	p = Prop("echo_of_the_nameless", 1845)
	_ring(p, IRON)                                                                         # a black band
	for k, (sw, glow) in enumerate(((PETAL_PURPLE, 1.0), (CLOTH_WHITE, 0.2))):             # set with a blank face and its echo
		p.blob((0.3, 0.12, 0.4), (0.08 - 0.08 * k, 0.08 - 0.1 * k, 0.94 - 0.02 * k), sw, segs=(10, 8), grad=(0.0, 0.5), glow=glow)
	for sx in (-1, 1):
		p.blob((0.05, 0.03, 0.03), (sx * 0.06, -0.08, 0.96), IRON, segs=(5, 3))
		_hum(p, _flat(-0.1), (sx * 0.24, 0.94), sx, n=2, r0=0.08, dr=0.1, spread=35, sw=PETAL_PURPLE, glow=2.0)
	return p.build()


shadowhide_boots = _repainted("shadowhide_boots", stalkerhide_boots, {AMBER: (PETAL_PURPLE, 0.6, 1.0), WOOD: (IRON, 0.0, 0.5), STONE_DARK: (IRON, 0.0, 0.5)})
starveil_bow = _repainted("starveil_bow", emberheart_bow, {EMBER: (SKY, 0.0, 0.4), OCHRE: (STONE_LIGHT, 0.0, 0.4), FLAME: (CLOTH_WHITE, 0.0, 0.3),
														   STONE_DARK: (WATER, 0.75, 1.0)},
						  _stars("starveil_bow_stars", 1847, [(-0.3, -0.2, 0.9, 0.08), (0.3, -0.2, 0.3, 0.07)]))
moonsilk_sash = _repainted("moonsilk_sash", kitesilk_sash, {SKY: (CLOTH_WHITE, 0.1, 0.6), OCHRE: (WATER, 0.5, 0.9), CLOTH_WHITE: (SKY, 0.0, 0.4)})
moonwing_mantle = _repainted("moonwing_mantle", mothwing_cloak, {ASH: (CLOTH_WHITE, 0.1, 0.7), OCHRE: (SKY, 0.1, 0.6), GOLD: (WATER, 0.5, 0.9), HIDE: (SKY, 0.0, 0.3), BONE: (CLOTH_WHITE, 0.0, 0.4),
																 WOOD: (STONE_LIGHT, 0.2, 0.8), STONE_DARK: (WATER, 0.7, 1.0)})


def morvaine_signet_ring():
	p = Prop("morvaine_signet_ring", 1849)
	_ring(p, STONE_LIGHT)                                                                  # a heavy silver band
	crest = [(x * 0.44, 0.72 + z * 0.44) for x, z in HEATER]
	_slab(p, crest, -0.1, 0.06, CRIMSON, grad=(0.3, 1.0))                                  # its face: House Morvaine's crimson crest
	for a, b in zip(crest, crest[1:] + crest[:1]):
		p.seg((a[0], -0.11, a[1]), (b[0], -0.11, b[1]), 0.025, 0.025, STONE_LIGHT, sides=5)
	_bat(p, (0.0, -0.12, 1.0), 0.3, IRON)                                                    # and its black bat
	return p.build()


countess_crimson_blade = _repainted("countess_crimson_blade", aldrics_glass_blade, {CLOTH_WHITE: (CRIMSON, 0.15, 0.7), PETAL_PURPLE: (IRON, 0.0, 0.4),
																				   SKY: (CRIMSON, 0.5, 1.0)})


BONEYARD = [eclipsed_helm, eclipsed_breastplate, eclipsed_vambraces, eclipsed_gauntlets, eclipsed_greaves, eclipsed_boots, eclipsed_shield,
			umbral_jerkin, umbral_leggings, umbral_gloves, umbral_boots, starweave_cap, starweave_robe, starweave_gloves, starweave_slippers,
			eclipse_blade, umbral_war_axe, nightfall_greataxe, starshard_dirk, moonwood_staff, barrowhold_longbow, nightwing_arrow,
			tarnished_court_silver, gargoyle_stone, fog_hound_pelt, stolen_grave_goods, ismays_mourning_veil, grimwatchs_stone_heart,
			whitemaws_collar, crowes_black_lantern, ivory_shard, poached_ivory, carrion_feather, ghost_ivory, shade_essence, shadowhide,
			luminous_dust, morvaine_crest, ossuary_heartbone, vargas_tusk_saw, gorgemaws_beak, grandmothers_tusk, nameless_echo,
			starveils_eye, moon_moths_antenna, countess_locket, courtiers_signet, mourning_veil_cowl, gargoyle_hide_vambraces,
			stoneheart_shield, foghound_cloak, whitemaw_fang_dirk, robbers_sash, black_lantern_charm, ivory_bracer, ossuary_greatmaul,
			poachers_bane_gloves, tusksaw_cleaver, carrion_feather_cloak, gorgemaw_beak_amulet, ghost_ivory_ring, grandmothers_blessing,
			shade_silk_gloves, echo_of_the_nameless, shadowhide_boots, starveil_bow, moonsilk_sash, moonwing_mantle, morvaine_signet_ring,
			countess_crimson_blade]



# ---------------------------------------------------------------- the Boneyard's summit: Lastwalk and Timiraj's Table
# Lastwalk is the battlefield where the gods went to war, turned to stone: divine
# bronze gone gray, godfire gold still glowing in its cracks. Timiraj's Table is the
# dark god's feast under the stars: grave-gold, black silver, violet and starlight.
# The last lord's three drops and the Crown of the Table are drawn fresh, and glow most.

PETRIFIED = SEA_STONE   # blue-gray: flesh and bronze turned to stone


def _rising_smoke(p, x, y, z0, h, sw=PETAL_PURPLE, glow=1.4, w=0.03, puff=ASH, turns=1.2, amp=0.08, phase=0.0):
	"""A wavering thread of smoke rising from (x, y, z0), h tall, ending in a puff."""
	pts = [(x + amp * math.sin(phase + k / 10 * turns * math.tau) * (0.4 + k / 10), y, z0 + h * k / 10) for k in range(11)]
	_line(p, pts, w, w * 0.4, sw, sides=5, grad=(0.0, 0.5), glow=glow)
	if puff:
		p.blob((w * 3.2, w * 2.4, w * 2.6), pts[-1], puff, segs=(8, 5), grad=(0.2, 0.7), glow=glow * 0.4)


def _stone_crust(p, pts, y, sw=PETRIFIED, crack=GOLD):
	"""A patch of stone crust laid over a face toward the camera: outline pts (x, z) at depth y,
	with a crack of godfire through it."""
	_slab(p, pts, y - 0.02, y + 0.015, sw, grad=(0.0, 0.8))
	cx = sum(x for x, _ in pts) / len(pts)
	cz = sum(z for _, z in pts) / len(pts)
	_seam(p, [(cx - 0.12, y - 0.025, cz + 0.06), (cx - 0.02, y - 0.025, cz - 0.02), (cx + 0.1, y - 0.025, cz + 0.03)], swatch=crack, r=0.016, glow=2.4)


# Lastwalk's drops

def godwar_insignia():
	p = Prop("godwar_insignia", 1901)
	badge = [(x * 0.9, z * 0.9) for x, z in HEATER]
	_slab(p, badge, -0.05, 0.05, BRONZE, grad=(0.2, 0.9))                                   # a war-badge of bronze
	for a, b in zip(badge, badge[1:] + badge[:1]):
		p.seg((a[0], -0.06, a[1]), (b[0], -0.06, b[1]), 0.04, 0.04, GOLD, sides=6, grad=(0.0, 0.5))
	_sun(p, (-0.2, -0.08, 0.74), 0.13, GOLD, rays=10, ray=0.8, glow=1.0)                      # one god's sun
	_crescent(p, (0.2, -0.08, 0.74), 0.16, sw=PETAL_PURPLE, glow=1.4, turn=160)              # against another's moon
	_seam(p, [(0.0, -0.09, 1.08), (0.04, -0.09, 0.86), (-0.03, -0.09, 0.62), (0.03, -0.09, 0.4)], swatch=GOLD, r=0.018, glow=2.6)   # split between them
	_stone_crust(p, [(-0.45, 0.5), (-0.22, 0.4), (-0.02, 0.46), (0.2, 0.34), (0.36, 0.3), (0.18, 0.07), (0.0, 0.0), (-0.18, 0.07), (-0.36, 0.27)],
				 -0.06)                                                                  # its foot turned to stone
	for sx in (-1, 1):                                                                    # torn ribbons
		p.box((0.1, 0.03, 0.3), (sx * 0.22, 0.02, 1.2), CLOTH_RED, rot=(0, sx * 12, 0))
	return p.build()


def petrified_shard():
	p = Prop("petrified_shard", 1903)
	p.rock((0.9, 0.6, 0.34), (0.0, 0.1, 0.1), STONE_DARK, jitter=0.06)                         # a slab of the battlefield
	for x, y, h, r, ang, sw in ((0.0, 0.0, 1.25, 0.3, 6, PETRIFIED), (-0.3, 0.12, 0.8, 0.22, -26, STONE_LIGHT),
								(0.3, 0.14, 0.68, 0.2, 32, STONE_LIGHT), (0.14, -0.2, 0.42, 0.14, 52, PETRIFIED)):
		a = math.radians(ang)                                                             # broken into stone shards
		p.seg((x, y, 0.1), (x + math.sin(a) * h, y, 0.1 + math.cos(a) * h), r, 0.0, sw, sides=5, grad=(0.1, 0.8), jitter=0.02)
	p.seg((-0.2, -0.3, 0.62), (0.2, -0.3, 0.7), 0.035, 0.035, STONE_LIGHT, sides=5)            # a stone sword-hilt still caught in it
	p.seg((0.0, -0.3, 0.66), (-0.04, -0.3, 0.98), 0.045, 0.04, STONE_LIGHT, sides=6)
	p.blob((0.08, 0.08, 0.08), (-0.05, -0.3, 1.02), STONE_LIGHT, segs=(6, 4))
	_seam(p, [(0.02, -0.26, 0.2), (0.08, -0.26, 0.4), (0.02, -0.26, 0.55)], swatch=GOLD, r=0.02, glow=2.6)   # godfire in the cracks
	_seam(p, [(-0.3, -0.12, 0.3), (-0.36, -0.1, 0.46)], swatch=GOLD, r=0.016, glow=2.6)
	return p.build()


def divine_bronze():
	p = Prop("divine_bronze", 1905)
	_ingot(p, BRONZE, grad=(0.1, 0.8))                                                      # a bar of the gods' own bronze
	p.seg((0, 0, 0.262), (0, 0, 0.275), 0.12, 0.12, GOLD, sides=16, grad=(0.0, 0.4), glow=2.2)   # stamped with a sun that still glows
	for k in range(10):
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.13, math.sin(a) * 0.1, 0.268), (math.cos(a) * 0.22, math.sin(a) * 0.15, 0.268), 0.025, 0.0, GOLD, sides=4, glow=2.2)
	for x, z in ((-0.3, 0.1), (0.0, 0.07), (0.3, 0.1)):                                       # godfire runes down its side
		p.seg((x - 0.05, -0.23, z - 0.02), (x + 0.05, -0.23, z + 0.04), 0.014, 0.014, GOLD, sides=4, glow=2.4)
		p.seg((x, -0.235, z - 0.05), (x, -0.235, z + 0.06), 0.014, 0.014, GOLD, sides=4, glow=2.4)
	_stone_crust(p, [(0.3, 0.02), (0.52, 0.02), (0.44, 0.2), (0.3, 0.16)], -0.24)              # one end already stone
	for x, z, s in ((-0.5, 0.6, 0.1), (0.46, 0.5, 0.08), (0.1, 0.72, 0.07)):
		_star(p, (x, -0.1, z), s, sw=GOLD, glow=2.6)
	return p.build()


def stolen_relic():
	p = Prop("stolen_relic", 1907)
	p.box((0.8, 0.46, 0.5), (0, 0, 0.35), GOLD, grad=(0.1, 0.8))                              # a little gilt reliquary
	p.poly([(-0.44, -0.27, 0.6), (0.44, -0.27, 0.6), (0.44, 0.27, 0.6), (-0.44, 0.27, 0.6), (-0.44, 0.0, 0.86), (0.44, 0.0, 0.86)],
		   [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)], GOLD, grad=(0.0, 0.6))   # its peaked roof
	p.box((0.5, 0.02, 0.3), (0, -0.235, 0.36), CRIMSON, grad=(0.4, 1.0))                        # a window onto crimson velvet
	p.seg((-0.18, -0.26, 0.3), (0.16, -0.26, 0.42), 0.03, 0.03, BONE, sides=6)                   # and a saint's finger-bone
	for x, z in ((-0.18, 0.3), (0.16, 0.42)):
		p.blob((0.07, 0.05, 0.06), (x, -0.26, z), BONE, segs=(6, 4))
	for sx in (-1, 1):
		p.seg((sx * 0.42, -0.25, 0.1), (sx * 0.42, -0.25, 0.6), 0.035, 0.035, GOLD, sides=6, grad=(0.0, 0.4))   # corner posts
		p.blob((0.1, 0.1, 0.08), (sx * 0.4, -0.2, 0.08), GOLD, segs=(6, 4))                  # on little feet
	p.blob((0.12, 0.1, 0.12), (0, 0, 0.92), PETAL_PURPLE, segs=(8, 5), glow=1.6)               # a gem on the ridge
	_line(p, [(0.4, -0.24, 0.62), (0.56, -0.3, 0.44), (0.6, -0.36, 0.2), (0.7, -0.34, 0.1)], 0.02, 0.02, WOOD, sides=4)   # the cut cord it hung by
	return p.build()


# Timiraj's Table's drops

def grave_gold():
	p = Prop("grave_gold", 1909)
	for k, (x, y) in enumerate(((-0.3, 0.1), (0.3, 0.2), (0.02, -0.26))):                     # grave-gold spilled
		for j in range(3 - k):
			z = j * 0.07
			p.seg((x, y, z), (x, y, z + 0.06), 0.3, 0.3, GOLD, sides=18, grad=(0.2, 0.9))
			p.blob((0.12, 0.1, 0.02), (x + 0.1, y - 0.08, z + 0.062), IRON, segs=(6, 3))        # tarnished black
	x, y, z = 0.1, -0.5, 0.44                                                             # one coin standing, stamped with a skull
	p.seg((x, y + 0.04, z), (x, y - 0.04, z), 0.38, 0.38, GOLD, sides=20, grad=(0.1, 0.7))
	_oval(p, (x, y - 0.045, z), (1, 0, 0), (0, 0, 1), 0.33, 0.33, 0.02, IRON, n=20)
	p.blob((0.3, 0.06, 0.26), (x, y - 0.06, z + 0.04), BONE, segs=(10, 6), grad=(0.0, 0.5))
	p.box((0.16, 0.05, 0.12), (x, y - 0.06, z - 0.12), BONE, grad=(0.0, 0.5))
	for sx in (-1, 1):
		p.blob((0.08, 0.04, 0.07), (x + sx * 0.07, y - 0.1, z + 0.04), PETAL_PURPLE, segs=(6, 3), glow=2.2)   # its eyes lit violet
	return p.build()


def star_fragment():
	p = Prop("star_fragment", 1911)
	p.rock((0.62, 0.5, 0.3), (0.0, 0.1, 0.1), IRON, jitter=0.06)                               # a fallen star's black husk
	for x, y, h, r, ang, sw, g in ((0.0, 0.0, 1.05, 0.24, 4, CLOTH_WHITE, 1.6), (-0.24, 0.1, 0.66, 0.16, -30, SKY, 1.2),
								   (0.26, 0.08, 0.56, 0.15, 34, SKY, 1.2), (0.1, -0.16, 0.36, 0.1, 58, CLOTH_WHITE, 1.4)):
		a = math.radians(ang)                                                             # cracked open on a crystal of starlight
		p.seg((x, y, 0.16), (x + math.sin(a) * h, y, 0.16 + math.cos(a) * h), r, 0.0, sw, sides=6, grad=(0.0, 0.5), glow=g)
	for x, z, s in ((-0.44, 1.0, 0.12), (0.36, 1.12, 0.09), (0.5, 0.56, 0.07), (-0.5, 0.5, 0.06)):
		_star(p, (x, -0.2, z), s)
	return p.build()


def shadowfur():
	p = Prop("shadowfur", 1913)
	p.blob((1.3, 0.8, 0.28), (0, 0, 0.14), IRON, segs=(14, 6), grad=(0.0, 0.6), jitter=0.04)       # a folded shadow-black pelt
	p.blob((1.1, 0.7, 0.26), (0.06, -0.02, 0.36), PETAL_PURPLE, segs=(14, 6), grad=(0.6, 1.0), jitter=0.04)
	for k in range(22):                                                                   # long fur with a violet sheen
		a = k * math.tau / 22
		r = 0.5 + 0.06 * (k % 3)
		b = (0.06 + math.cos(a) * r, math.sin(a) * r * 0.6, 0.38)
		p.seg(b, (b[0] + math.cos(a) * 0.2, b[1] + math.sin(a) * 0.12, 0.34 + 0.08 * (k % 2)), 0.05, 0.0, IRON if k % 2 else PETAL_PURPLE,
			  sides=4, grad=(0.3, 0.9))
	_line(p, [(0.6, 0.0, 0.3), (0.9, -0.1, 0.36), (1.02, -0.26, 0.5), (0.96, -0.36, 0.66)], 0.1, 0.03, IRON, sides=6)   # its tail
	_oval(p, (-0.28, 0.0, 0.26), (0, 1, 0), (0, 0, 1), 0.42, 0.28, 0.025, WOOD, n=14)          # tied with a cord
	for x, z, s in ((-0.3, 0.72, 0.08), (0.28, 0.66, 0.06)):                                  # stars caught in it
		_star(p, (x, -0.3, z), s, sw=CLOTH_WHITE, glow=2.2)
	return p.build()


def blackened_offering():
	p = Prop("blackened_offering", 1915)
	_plate(p, GOLD, r=0.72)                                                               # a grave-gold plate
	p.blob((0.64, 0.44, 0.34), (-0.14, 0.08, 0.2), STONE_DARK, segs=(12, 7), grad=(0.3, 1.0), jitter=0.03)   # a burnt loaf
	for x in (-0.3, -0.14, 0.02):
		p.seg((x - 0.04, -0.12, 0.34), (x + 0.04, -0.12, 0.3), 0.02, 0.02, EMBER, sides=4, glow=2.2)   # still smoldering in its cuts
	for x, y, s in ((0.3, -0.24, 0.2), (0.44, 0.02, 0.18), (0.2, 0.3, 0.16)):                 # black fruit
		p.blob((s, s, s), (x, y, 0.07 + s / 2), IRON, segs=(8, 6), grad=(0.1, 0.7))
		p.seg((x, y, 0.07 + s), (x + 0.02, y, 0.12 + s), 0.012, 0.012, WOOD, sides=4)
	_rising_smoke(p, -0.2, -0.1, 0.36, 0.7, phase=0.0)                                       # and a violet smoke going up to the dark god
	_rising_smoke(p, 0.12, 0.0, 0.3, 0.56, phase=2.0, w=0.024)
	return p.build()


# Lastwalk's named drops

def marshals_broken_standard():
	p = Prop("marshals_broken_standard", 1917)
	p.seg((-0.5, 0.05, -0.3), (-0.5, 0.05, 0.62), 0.05, 0.05, WOOD, sides=8)                  # the standard's pole, snapped
	for k in range(4):
		a = k * math.tau / 4 + 0.3
		p.seg((-0.5 + math.cos(a) * 0.03, 0.05 + math.sin(a) * 0.03, 0.6), (-0.5 + math.cos(a) * 0.04, 0.05 + math.sin(a) * 0.04, 0.72 + 0.05 * (k % 2)),
			  0.025, 0.0, WOOD, sides=4)
	_stone_crust(p, [(-0.56, -0.28), (-0.44, -0.28), (-0.44, 0.1), (-0.56, 0.2)], -0.01)
	q = Prop("marshals_standard_top", 1918)                                               # its top fallen aslant
	q.seg((-0.5, 0.05, 0.7), (-0.5, 0.05, 1.45), 0.05, 0.05, WOOD, sides=8)
	for k in range(3):
		a = k * math.tau / 3
		q.seg((-0.5 + math.cos(a) * 0.03, 0.05 + math.sin(a) * 0.03, 0.72), (-0.5, 0.05, 0.62), 0.025, 0.0, WOOD, sides=4)
	q.seg((-0.5, 0.05, 1.45), (-0.5, 0.05, 1.66), 0.08, 0.0, BRONZE, sides=4)                  # a bronze spear point
	q.seg((-0.56, 0.0, 1.32), (0.46, 0.0, 1.32), 0.04, 0.04, BRONZE, sides=6)
	cloth = [(-0.45, 1.3), (0.4, 1.3), (0.4, 0.5), (0.24, 0.36), (0.1, 0.48), (-0.06, 0.3), (-0.24, 0.44), (-0.45, 0.36)]
	_slab(q, cloth, 0.0, 0.03, CLOTH_RED, grad=(0.2, 0.9))                                    # a war-banner in red and gold
	for a, b in zip(cloth[:3], cloth[1:4]):
		q.seg((a[0], -0.01, a[1]), (b[0], -0.01, b[1]), 0.035, 0.035, GOLD, sides=4)
	q.seg((-0.45, -0.01, 1.3), (-0.45, -0.01, 0.36), 0.035, 0.035, GOLD, sides=4)
	for sgn in (1, -1):                                                                   # crossed gold swords
		q.seg((-0.2 * sgn - 0.02, -0.03, 0.66), (0.2 * sgn - 0.02, -0.03, 1.16), 0.035, 0.0, GOLD, sides=4, glow=0.4)
		q.seg((-0.2 * sgn - 0.08 * sgn - 0.02, -0.03, 0.8), (-0.2 * sgn + 0.06 * sgn - 0.02, -0.03, 0.72), 0.025, 0.025, GOLD, sides=4)
	_stone_crust(q, [(-0.45, 0.36), (-0.24, 0.44), (-0.06, 0.3), (0.1, 0.48), (0.24, 0.36), (0.4, 0.5), (0.4, 0.7), (0.1, 0.62), (-0.2, 0.74), (-0.45, 0.66)],
				 -0.03)                                                                   # its hem gone to stone
	top = q.build()
	piv = Vector((-0.5, 0.05, 0.64))
	top.data.transform(Matrix.Translation(piv + Vector((0.2, -0.06, -0.12))) @ Matrix.Rotation(math.radians(34), 4, "Y") @ Matrix.Translation(-piv))
	return p.build()


def champions_stone_crest():
	p = Prop("champions_stone_crest", 1919)
	p.blob((0.9, 0.7, 0.44), (0.0, 0.1, 0.08), PETRIFIED, segs=(12, 7), grad=(0.0, 0.8), jitter=0.02)   # the crown of a champion's helm, turned to stone
	_loop(p, (0.0, 0.1, 0.1), 0.45, True, 0.035, BRONZE, n=18, squash=0.78)                  # its bronze rim showing through
	c, a0, a1 = (0.0, 0.1), 172, 38                                                        # a great arched plume of horsehair, all stone now,
	outer = [(c[0] + math.cos(math.radians(a)) * 0.98, c[1] + math.sin(math.radians(a)) * 0.9) for a in range(a0, a1 - 1, -6)]
	inner = [(c[0] + math.cos(math.radians(a)) * 0.5, c[1] + math.sin(math.radians(a)) * 0.46) for a in range(a1, a0 + 1, 6)]
	brk = [(0.8, 0.62), (0.7, 0.5), (0.74, 0.42), (0.52, 0.36)]                               # snapped off at its tail
	_slab(p, outer + brk + inner, -0.12, 0.1, STONE_LIGHT, grad=(0.0, 0.8))
	for a in range(a0 - 4, a1, -9):                                                       # combed in strands
		r = math.radians(a)
		p.seg((math.cos(r) * 0.52, -0.13, c[1] + math.sin(r) * 0.48), (math.cos(r - 0.12) * 0.94, -0.13, c[1] + math.sin(r - 0.12) * 0.86), 0.018, 0.012,
			  PETRIFIED, sides=4)
	_line(p, [(math.cos(math.radians(a)) * 0.48, -0.02, c[1] + math.sin(math.radians(a)) * 0.44) for a in range(a0, a1 - 1, -12)], 0.07, 0.07, BRONZE,
		  sides=6)                                                                          # on a bronze saddle
	for pts in (((-0.62, 0.5), (-0.5, 0.62), (-0.56, 0.78)), ((0.1, 0.9), (0.16, 0.76), (0.1, 0.62)), ((0.52, 0.66), (0.62, 0.56))):   # godfire in its cracks
		_seam(p, [(x, -0.14, z) for x, z in pts], swatch=GOLD, r=0.022, glow=2.6)
	for x, s in ((0.7, 0.12), (0.86, 0.08), (0.56, 0.07)):                                  # chips broken from it
		p.rock((s, s, s * 0.8), (x, -0.2, 0.0), STONE_LIGHT, jitter=0.03)
	return p.build()


godforged_core = _repainted("godforged_core", forgeheart_core, {EMBER: (GOLD, 0.0, 0.45), FLAME: (CLOTH_WHITE, 0.0, 0.3), IRON: (BRONZE, 0.1, 0.8),
																 STONE_DARK: (PETRIFIED, 0.1, 0.8)},
							_stars("godforged_stars", 1921, [(-0.66, -0.3, 0.9, 0.1), (0.62, -0.3, 0.3, 0.08), (0.5, -0.3, 1.14, 0.07)]))


def oszkars_relic_crown():
	p = Prop("oszkars_relic_crown", 1923)
	p.seg((0, 0, 0.0), (0, 0, 0.28), 0.5, 0.5, BRONZE, sides=20, grad=(0.1, 0.8))              # a bronze crown pieced from plunder
	p.seg((0, 0, 0.27), (0, 0, 0.28), 0.44, 0.44, STONE_DARK, sides=20)
	for z in (0.02, 0.26):
		_loop(p, (0, 0, z), 0.515, True, 0.03, GOLD, n=20)
	fa = math.radians(FRONT_A)
	tops = []
	for k in range(7):                                                                    # its points topped with stolen holy things
		a = fa + (k - 3) * 0.52
		d = Vector((math.cos(a), math.sin(a), 0))
		h = (0.62, 0.42, 0.52, 0.8, 0.52, 0.42, 0.62)[k]
		b = d * 0.5 + Vector((0, 0, 0.26))
		p.seg(tuple(b), tuple(b + Vector((0, 0, h - 0.2))), 0.06, 0.03, GOLD if k % 2 else BRONZE, sides=5, grad=(0.0, 0.6))
		tops.append(b + Vector((0, 0, h - 0.18)))
	t = tops[3]
	_sun(p, (t.x, t.y - 0.02, t.z + 0.1), 0.1, GOLD, rays=10, ray=0.8, glow=1.4)            # a god's sun
	_crescent(p, (tops[1].x, tops[1].y - 0.02, tops[1].z + 0.08), 0.1, sw=STONE_LIGHT, glow=0.6, turn=200)   # another's moon
	p.seg(tuple(tops[5]), tuple(tops[5] + Vector((0.04, 0, 0.18))), 0.05, 0.0, BONE, sides=5)       # a saint's tooth
	for i in (0, 6):
		p.blob((0.09, 0.09, 0.09), tuple(tops[i]), CLOTH_RED, segs=(6, 4), glow=0.8)            # and gems
	for i in (2, 4):
		p.blob((0.08, 0.08, 0.08), tuple(tops[i]), BONE, segs=(6, 4))
	for k, (off, ln, sw) in enumerate(((-0.4, 0.3, BONE), (0.0, 0.22, GOLD), (0.4, 0.28, PETAL_PURPLE))):   # relics hung on chains
		a = fa + off
		b = Vector((math.cos(a) * 0.53, math.sin(a) * 0.53, 0.02))
		e = b + Vector((0, 0, -ln))
		p.seg(tuple(b), tuple(e), 0.012, 0.012, GOLD, sides=4)
		if k == 0:
			p.seg(tuple(e), tuple(e + Vector((0.02, 0, -0.16))), 0.035, 0.03, sw, sides=5)       # a finger-bone
		elif k == 1:
			p.box((0.1, 0.06, 0.14), tuple(e + Vector((0, 0, -0.06))), sw, grad=(0.0, 0.6))     # a tiny reliquary
		else:
			p.blob((0.1, 0.08, 0.12), tuple(e + Vector((0, 0, -0.04))), sw, segs=(6, 4), glow=1.6)
	for off, s in ((0.25, 0.12), (0.4, 0.1), (0.52, 0.08)):                                 # stone creeping over it
		a = fa + off
		p.rock((s, s, s * 1.2), (math.cos(a) * 0.52, math.sin(a) * 0.52, 0.12), PETRIFIED, jitter=0.03)
	return p.build()


# Timiraj's Table's named drops

long_table_goblet = _repainted("long_table_goblet", tarnished_court_silver, {STONE_LIGHT: (IRON, 0.0, 0.5), IRON: (GOLD, 0.2, 0.7), GOLD: (PETAL_PURPLE, 0.2, 0.6),
																		   STONE_DARK: (CRIMSON, 0.6, 1.0)},
							   _stars("long_table_goblet_stars", 1925, [(-0.58, -0.4, 1.2, 0.09), (0.56, -0.4, 1.02, 0.07), (-0.46, -0.4, 0.4, 0.06)]))


def astraels_star_heart():
	p = Prop("astraels_star_heart", 1927)
	_heart(p, (0, 0, 0.6), 1.0, WATER, grad=(0.55, 1.0), glow=0.3)                            # a heart of night sky
	_star(p, (0.0, -0.36, 0.66), 0.3, glow=3.2)                                               # a star still burning in it
	p.blob((0.14, 0.06, 0.14), (0.0, -0.34, 0.66), CLOTH_WHITE, segs=(8, 5), glow=3.4)
	for x, z, s in ((-0.28, 0.9, 0.06), (0.3, 0.86, 0.07), (-0.14, 0.3, 0.05), (0.22, 0.42, 0.05), (0.34, 0.66, 0.04)):
		_star(p, (x, -0.32, z), s, sw=SKY, glow=2.4)                                        # and a sky of little ones
	for a in range(0, 360, 45):                                                           # shining round it
		r = math.radians(a)
		b = (math.cos(r) * 0.76, 0.0, 0.64 + math.sin(r) * 0.72)
		p.seg(b, (b[0] * 1.2, 0.0, 0.64 + (b[2] - 0.64) * 1.2), 0.03, 0.0, CLOTH_WHITE, sides=4, glow=2.0)
	return p.build()


def nightjaws_fang():
	p = Prop("nightjaws_fang", 1929)
	pts = _tusk(p, (-0.1, 1.1), -70, 1.25, -34, 0.26, sw=BONE, grad=(0.1, 0.8))               # the great night-hound's fang, hanging point down
	_line(p, pts[6:], 0.26 * 0.34 + 0.015, 0.04, PETAL_PURPLE, sides=10, grad=(0.3, 0.9))      # its point stained with the dark
	p.blob((0.1, 0.06, 0.1), pts[-1], PETAL_PURPLE, segs=(6, 4), glow=2.6)
	p.blob((0.44, 0.34, 0.26), (-0.1, 0.0, 1.14), CRIMSON, segs=(10, 6), grad=(0.3, 1.0))        # torn out at the root
	for k in range(2):                                                                    # a dark smoke coming off it
		_rising_smoke(p, 0.24 + 0.2 * k, -0.1, 0.3 + 0.2 * k, 0.5, w=0.02, glow=1.8, puff=None, phase=k * 1.6)
	_star(p, (-0.46, -0.3, 0.5), 0.1)
	return p.build()


def crown_of_the_uninvited():
	p = Prop("crown_of_the_uninvited", 1931)
	p.seg((0, 0, 0.0), (0, 0, 0.26), 0.5, 0.5, IRON, sides=20, grad=(0.0, 0.6))               # a black iron crown
	p.seg((0, 0, 0.25), (0, 0, 0.26), 0.44, 0.44, STONE_DARK, sides=20)
	_loop(p, (0, 0, 0.02), 0.51, True, 0.03, PETAL_PURPLE, n=20)
	fa = math.radians(FRONT_A)
	for k in range(11):                                                                   # ringed in crooked thorns
		a = fa + (k - 5) * 0.57
		d = Vector((math.cos(a), math.sin(a), 0))
		h = 0.34 + 0.28 * ((k * 5) % 3) / 2 + (0.2 if k == 5 else 0.0)
		b = d * 0.5 + Vector((0, 0, 0.24))
		lean = Vector((math.cos(a + 1.6), math.sin(a + 1.6), 0)) * 0.08 * (1 if k % 2 else -1)
		_line(p, [tuple(b), tuple(b + d * 0.04 + lean + Vector((0, 0, h * 0.55))), tuple(b + d * 0.08 - lean + Vector((0, 0, h)))], 0.07, 0.0, IRON,
			  sides=5, grad=(0.0, 0.6))
	c = Vector((math.cos(fa) * 0.53, math.sin(fa) * 0.53, 0.14))
	p.blob((0.2, 0.12, 0.22), tuple(c), PETAL_PURPLE, segs=(8, 6), glow=2.6)                   # a violet stone for an eye
	for k, (dx, h) in enumerate(((-0.34, 0.8), (0.06, 1.0), (0.38, 0.7))):                    # a curse rising off it
		_rising_smoke(p, dx, 0.1, 0.3, h + 0.2, w=0.022, glow=2.0, puff=None, phase=k * 1.7)
	return p.build()


# rewards

def godwar_pauldrons():
	p = Prop("godwar_pauldrons", 1933)
	t0, t1, r0, r1 = _vambrace(p, BRONZE, GOLD, WOOD, GOLD, grad=(0.1, 0.8), glow_line=GOLD)   # divine bronze plates
	for t, ang, s in ((-0.24, -20, 0.14), (0.14, 30, 0.12), (0.3, -40, 0.1)):              # crusted with stone
		r = _fa_r(t, r0, r1, t0, t1) + 0.02
		p.rock((s, s * 0.6, s), _fa(t, r, ang), PETRIFIED, jitter=0.03)
	r = _fa_r(0.0, r0, r1, t0, t1) + 0.04
	_sun(p, _fa(0.0, r, -10), 0.08, GOLD, rays=8, ray=0.8, glow=1.8)                          # stamped with a sun
	return p.build()


def _standard_pennant():
	p = Prop("standard_pennant", 1935)
	org, rot = (-0.55, -0.42), 48
	g = _rot2([(0.3, -0.1)], rot, org)[0]
	_streamer(p, _flat(-0.06), g, (1.0, -0.55), 0.8, 0.18, CRIMSON, tip_sw=GOLD, stripe=GOLD)   # a scrap of the war-banner tied at the guard
	return p.build()


marshals_standard_blade = _repainted("marshals_standard_blade", skyforged_sword, {SKY: (BRONZE, 0.1, 0.8), CLOTH_WHITE: (GOLD, 0.0, 0.5)}, _standard_pennant)


def stoneskin_girdle():
	p = Prop("stoneskin_girdle", 1937)
	f, out, tan = _belt(p, WOOD, BRONZE, BRONZE, R=0.58, h=0.24)                            # a belt set with plates of stone
	for k in range(12):
		a = k * math.tau / 12 + 0.26
		d = Vector((math.cos(a), math.sin(a), 0))
		if d.dot(out) > 0.9:
			continue
		q = Vector((0, 0.1, 0.5)) + d * 0.62
		p.box((0.24, 0.07, 0.3), tuple(q), PETRIFIED if k % 2 else STONE_LIGHT, rot=(0, 0, math.degrees(a) + 90), grad=(0.0, 0.8), jitter=0.01)
	for s in (-1, 1):
		q = f + tan * s * 0.34 + out * 0.06
		_seam(p, [tuple(q + Vector((0, 0, 0.1))), tuple(q + tan * 0.04), tuple(q + Vector((0, 0, -0.1)))], swatch=GOLD, r=0.016, glow=2.4)
	p.blob((0.1, 0.06, 0.1), tuple(f + out * 0.07), GOLD, segs=(6, 4), glow=2.0)
	return p.build()


def champions_crest_shield():
	p = Prop("champions_crest_shield", 1939)
	_slab(p, HEATER, -0.06, 0.06, PETRIFIED, grad=(0.0, 0.8))                                # a champion's heater shield, gone to stone
	for a, b in zip(HEATER, HEATER[1:] + HEATER[:1]):                                    # rimmed in bronze
		p.seg((a[0], -0.07, a[1]), (b[0], -0.07, b[1]), 0.05, 0.05, BRONZE, sides=6, grad=(0.0, 0.6))
	p.blob((0.34, 0.12, 0.3), (0.0, -0.09, 0.62), STONE_LIGHT, segs=(10, 6), grad=(0.0, 0.6))  # his plumed helm for a crest
	p.box((0.36, 0.06, 0.14), (0.0, -0.1, 0.5), STONE_LIGHT, grad=(0.0, 0.6))
	p.seg((-0.08, -0.16, 0.56), (0.08, -0.16, 0.56), 0.02, 0.02, STONE_DARK, sides=4)
	arc = [(math.cos(math.radians(a)) * 0.2, 0.7 + math.sin(math.radians(a)) * 0.28) for a in range(160, 19, -20)]
	for k, (x, z) in enumerate(arc):
		a = math.atan2(z - 0.62, x)
		p.seg((x, -0.1, z), (x + math.cos(a) * 0.14 - 0.1, -0.1, z + math.sin(a) * 0.14 + 0.03), 0.05, 0.01, GOLD, sides=4, glow=0.6)
	for pts in (((-0.3, 1.06), (-0.22, 0.9), (-0.3, 0.78)), ((0.34, 0.4), (0.24, 0.26), (0.16, 0.2))):   # godfire in its cracks
		_seam(p, [(x, -0.08, z) for x, z in pts], swatch=GOLD, r=0.018, glow=2.6)
	return p.build()


def divine_bronze_ring():
	p = Prop("divine_bronze_ring", 1941)
	_ring(p, BRONZE)                                                                       # a band of the gods' bronze
	_sun(p, (0.0, -0.02, 0.9), 0.14, GOLD, rays=12, ray=0.9, glow=1.4)                        # set with a sunburst
	p.blob((0.12, 0.08, 0.12), (0.0, -0.08, 0.9), CLOTH_WHITE, segs=(8, 5), glow=2.8)
	return p.build()


def godforged_heart_amulet():
	p = Prop("godforged_heart_amulet", 1943)
	_cord(p, 0.45, 0.88, GOLD)                                                              # a gold chain
	c = Vector((0.0, -0.3, 0.34))
	p.seg(tuple(c + Vector((0, 0, 0.22))), tuple(c + Vector((0, 0, 0.3))), 0.04, 0.04, GOLD, sides=6)
	p.blob((0.3, 0.3, 0.3), tuple(c), GOLD, segs=(12, 8), grad=(0.0, 0.4), glow=2.2)          # a little godforged heart
	p.blob((0.12, 0.06, 0.12), tuple(c + Vector((-0.03, -0.14, 0.03))), CLOTH_WHITE, segs=(6, 4), glow=3.0)
	for deg in (-61 + 90, -61 + 30, -61 - 30):                                             # in a bronze cage
		a = math.radians(deg)
		_oval(p, tuple(c), Vector((math.cos(a), math.sin(a), 0)), Vector((0, 0, 1)), 0.18, 0.18, 0.022, BRONZE, n=16)
	return p.build()


scavengers_gloves = _repainted("scavengers_gloves", smokehide_gloves, {ASH: (HIDE, 0.3, 0.9), STONE_DARK: (WOOD, 0.4, 1.0), WOOD_GRAY: (BRONZE, 0.1, 0.7)})


def relic_crown_circlet():
	p = Prop("relic_crown_circlet", 1945)
	_loop(p, (0, 0, 0.2), 0.48, True, 0.05, GOLD, n=22)                                     # a slender gold circlet
	_loop(p, (0, 0, 0.12), 0.485, True, 0.03, BRONZE, n=22)
	fa = math.radians(FRONT_A)
	c = Vector((math.cos(fa) * 0.52, math.sin(fa) * 0.52, 0.22))
	out = Vector((math.cos(fa), math.sin(fa), 0))
	p.seg(tuple(c - out * 0.02), tuple(c + out * 0.05), 0.2, 0.2, GOLD, sides=14, grad=(0.0, 0.5))   # a reliquary medallion on the brow
	p.seg(tuple(c + out * 0.04), tuple(c + out * 0.06), 0.13, 0.13, CRIMSON, sides=14, grad=(0.3, 0.9))
	p.blob((0.08, 0.06, 0.08), tuple(c + out * 0.08), BONE, segs=(6, 4), glow=0.6)            # a holy sliver behind glass
	for s in (-1, 1):                                                                     # small bone charms at the temples
		a = fa + s * 0.7
		b = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.1))
		p.seg(tuple(b), tuple(b + Vector((0, 0, -0.14))), 0.01, 0.01, GOLD, sides=4)
		p.seg(tuple(b + Vector((0, 0, -0.14))), tuple(b + Vector((0, 0, -0.26))), 0.03, 0.02, BONE, sides=5)
	return _tip_back(p.build(), -22)


def grave_gold_signet():
	p = Prop("grave_gold_signet", 1947)
	_ring(p, GOLD)                                                                         # a heavy grave-gold band
	oct_ = [(math.cos(math.radians(22.5 + k * 45)) * 0.28, 0.9 + math.sin(math.radians(22.5 + k * 45)) * 0.24) for k in range(8)]
	_slab(p, oct_, -0.1, 0.08, IRON, grad=(0.1, 0.7))                                        # a black onyx face
	for a, b in zip(oct_, oct_[1:] + oct_[:1]):
		p.seg((a[0], -0.11, a[1]), (b[0], -0.11, b[1]), 0.025, 0.025, GOLD, sides=5)
	p.blob((0.2, 0.05, 0.18), (0.0, -0.12, 0.93), BONE, segs=(8, 5), grad=(0.0, 0.5))         # cut with a skull
	p.box((0.1, 0.04, 0.07), (0.0, -0.12, 0.83), BONE, grad=(0.0, 0.5))
	for sx in (-1, 1):
		p.blob((0.05, 0.03, 0.045), (sx * 0.045, -0.15, 0.93), PETAL_PURPLE, segs=(5, 3), glow=2.0)
	return p.build()


def long_table_chalice_charm():
	p = Prop("long_table_chalice_charm", 1949)
	_cord(p, 0.45, 0.88, STONE_LIGHT)                                                       # a black-silver chain
	x, y = 0.0, -0.3
	p.seg((x, y, 0.62), (x, y, 0.66), 0.03, 0.03, STONE_LIGHT, sides=6)
	p.seg((x, y, 0.08), (x, y, 0.12), 0.14, 0.14, GOLD, sides=14)                              # a little gold chalice
	p.seg((x, y, 0.12), (x, y, 0.3), 0.04, 0.04, GOLD, sides=8)
	p.blob((0.1, 0.1, 0.07), (x, y, 0.22), PETAL_PURPLE, segs=(8, 5), glow=1.6)
	p.seg((x, y, 0.3), (x, y, 0.56), 0.05, 0.2, GOLD, sides=14, grad=(0.0, 0.5))
	p.seg((x, y, 0.55), (x, y, 0.57), 0.18, 0.18, CRIMSON, sides=14, grad=(0.5, 1.0))          # brimming with dark wine
	_loop(p, (x, y, 0.56), 0.2, True, 0.015, GOLD, n=14)
	for sx in (-1, 1):                                                                    # its handles
		_line(p, [(sx * 0.18, y, 0.5), (sx * 0.3, y, 0.46), (sx * 0.26, y, 0.34), (sx * 0.08, y, 0.3)], 0.02, 0.02, GOLD, sides=4)
	_star(p, (0.26, y - 0.06, 0.66), 0.07)
	return p.build()


starfragment_boots = _starry("starfragment_boots", stalkerhide_boots, {AMBER: (WATER, 0.7, 1.0), WOOD: (IRON, 0.0, 0.5)},
							 [(0.34, 0.66, 0.08), (0.62, 0.44, 0.07), (0.8, 0.2, 0.06), (0.2, 0.34, 0.06)])


def _star_heart_head():
	p = Prop("star_heart_head", 1951)
	c = _rot2([(1.95, 0.0)], 72, (-0.3, -0.7))[0]
	_heart(p, (c[0], -0.4, c[1] - 0.02), 0.56, WATER, grad=(0.45, 1.0), glow=0.5)             # a heart of night sky over the gem
	_star(p, (c[0], -0.64, c[1]), 0.2, glow=3.2)
	for x, z, s in ((-0.4, 0.32, 0.07), (0.38, 0.18, 0.06), (0.3, -0.4, 0.05), (-0.34, -0.3, 0.05)):
		_star(p, (c[0] + x, -0.3, c[1] + z), s, sw=SKY, glow=2.4)
	return p.build()


star_heart_staff = _repainted("star_heart_staff", stormwood_staff, {WOOD_GRAY: (IRON, 0.05, 0.55), SKY: (WATER, 0.6, 1.0)}, _star_heart_head)
shadowfur_cloak = _repainted("shadowfur_cloak", moorhide_cloak, {WOOD_GRAY: (IRON, 0.0, 0.5), STONE_WARM: (PETAL_PURPLE, 0.6, 0.9), STONE_DARK: (PETAL_PURPLE, 0.8, 1.0),
																 STONE_LIGHT: (ASH, 0.3, 0.6), PETAL_PURPLE: (CLOTH_WHITE, 0.0, 0.3)})


def _nightjaw_fangs():
	p = Prop("nightjaw_fangs", 1953)
	org, rot = (0.0, 0.6), 50
	for s in (-1, 1):                                                                     # great fangs bound to its tips
		tip, back = _rot2([(s * 1.1, -0.08), (s * 0.96, 0.02)], rot, org)
		d = Vector((tip[0] - back[0], tip[1] - back[1])).normalized()
		n = Vector((-d.y, d.x))
		b = Vector(tip) - d * 0.08
		pts = [(b.x + d.x * 0.3 * k / 4 + n.x * 0.12 * (k / 4) ** 2, -0.04, b.y + d.y * 0.3 * k / 4 + n.y * 0.12 * (k / 4) ** 2) for k in range(5)]
		_line(p, pts, 0.08, 0.0, BONE, sides=6, grad=(0.1, 0.7))
	g = _rot2([(0.0, 0.08)], rot, org)[0]
	for k in range(3):                                                                    # and a fang-and-bead charm at the grip
		q = (g[0] + 0.1 + 0.06 * k, -0.1, g[1] - 0.2 - 0.1 * k)
		p.seg((q[0], q[1], q[2] + 0.1), q, 0.012, 0.012, WOOD, sides=4)
		if k == 2:
			p.seg(q, (q[0] + 0.02, q[1], q[2] - 0.2), 0.05, 0.0, BONE, sides=5)
		else:
			p.blob((0.06, 0.06, 0.06), q, PETAL_PURPLE, segs=(6, 4), glow=1.6)
	return p.build()


nightjaw_fang_bow = _repainted("nightjaw_fang_bow", forgehold_longbow, {WOOD: (IRON, 0.0, 0.55), FLAME: (PETAL_PURPLE, 0.2, 0.6), HIDE: (PETAL_PURPLE, 0.7, 1.0),
																	   STONE_DARK: (BONE, 0.3, 0.8)}, _nightjaw_fangs)
offering_bearers_sash = _repainted("offering_bearers_sash", kitesilk_sash, {SKY: (CRIMSON, 0.3, 0.9), OCHRE: (GOLD, 0.0, 0.6), CLOTH_WHITE: (IRON, 0.0, 0.5)})


# the last lord's drops and the Crown of the Table: the best things in the game

def crown_of_the_table():
	p = Prop("crown_of_the_table", 1955)
	p.seg((0, 0, 0.0), (0, 0, 0.36), 0.5, 0.5, STONE_LIGHT, sides=24, grad=(0.15, 0.8))        # a crown of dark silver
	p.seg((0, 0, 0.31), (0, 0, 0.32), 0.44, 0.44, IRON, sides=24)
	for z in (0.02, 0.3):
		_loop(p, (0, 0, z), 0.52, True, 0.035, IRON, n=24)
	_loop(p, (0, 0, 0.16), 0.51, True, 0.014, PETAL_PURPLE, n=24, glow=1.4)                   # a violet thread of light round it
	fa = math.radians(FRONT_A)
	for k in range(9):                                                                    # tall fleur points
		a = fa + (k - 4) * 0.5
		d = Vector((math.cos(a), math.sin(a), 0))
		b = d * 0.5 + Vector((0, 0, 0.34))
		h = (0.5, 0.7, 0.52, 0.84, 1.3, 0.84, 0.52, 0.7, 0.5)[k]
		tip = b + Vector((0, 0, h))
		p.seg(tuple(b - Vector((0, 0, 0.02))), tuple(tip), 0.12, 0.02, STONE_LIGHT, sides=4, grad=(0.05, 0.75))
		if k != 4:
			p.blob((0.07, 0.07, 0.07), tuple(tip), STONE_LIGHT, segs=(6, 4), grad=(0.0, 0.5))
			if k % 2:
				p.blob((0.08, 0.06, 0.1), tuple(b + d * 0.05 + Vector((0, 0, h * 0.4))), PETAL_PURPLE, segs=(6, 4), glow=2.0)
	top = Vector((math.cos(fa), math.sin(fa), 0)) * 0.5 + Vector((0, 0, 1.7))
	_star(p, (top.x, top.y - 0.06, top.z + 0.1), 0.26, glow=3.4)                              # crowned with a star
	p.blob((0.1, 0.08, 0.1), (top.x, top.y - 0.08, top.z + 0.1), CLOTH_WHITE, segs=(8, 5), glow=3.6)
	for a, s in ((30, 0.12), (140, 0.1), (230, 0.08), (320, 0.1)):
		r = math.radians(a)
		p.seg((top.x + math.cos(r) * 0.12, top.y - 0.06, top.z + 0.1 + math.sin(r) * 0.12),
			  (top.x + math.cos(r) * (0.12 + s * 1.6), top.y - 0.06, top.z + 0.1 + math.sin(r) * (0.12 + s * 1.6)), 0.018, 0.0, CLOTH_WHITE, sides=4, glow=2.8)
	out = Vector((math.cos(fa), math.sin(fa), 0))
	c = out * 0.5 + Vector((0, 0, 0.18))
	p.seg(tuple(c), tuple(c + out * 0.06), 0.2, 0.2, STONE_LIGHT, sides=18, grad=(0.0, 0.5))    # set with an eclipse:
	p.seg(tuple(c + out * 0.05), tuple(c + out * 0.07), 0.16, 0.16, GOLD, sides=18, grad=(0.0, 0.3), glow=3.2)   # a blazing corona
	p.seg(tuple(c + out * 0.07), tuple(c + out * 0.1), 0.125, 0.125, IRON, sides=18, grad=(0.6, 1.0))              # round a black sun
	for k in range(12):
		a = k * math.tau / 12
		u = Vector((-out.y, out.x, 0)) * math.cos(a) + Vector((0, 0, 1)) * math.sin(a)
		p.seg(tuple(c + out * 0.07 + u * 0.16), tuple(c + out * 0.07 + u * (0.24 + 0.06 * (k % 2))), 0.02, 0.0, GOLD, sides=4, glow=3.0)
	for x, z, s in ((-0.74, 1.2, 0.09), (0.76, 1.0, 0.08), (-0.66, 0.6, 0.06), (0.66, 1.5, 0.06)):   # stars glinting round it
		_star(p, (x, -0.5, z), s)
	return p.build()


def unlit_worldblade():
	p = Prop("unlit_worldblade", 1957)
	org, rot = (-0.6, -0.62), 46
	up = [(0.5, 0.32), (0.62, 0.27), (1.1, 0.3), (1.6, 0.27), (2.0, 0.19), (2.26, 0.08)]
	tip = (2.42, 0.0)
	outline = up + [tip] + [(x, -z) for x, z in reversed(up)]
	_slab(p, _rot2(outline, rot, org), -0.045, 0.045, IRON, grad=(0.0, 0.55))               # a great blade of black steel
	bf = _blade_frame(rot, org, -0.05)
	for sgn in (1, -1):                                                                   # its edges catching a violet light
		_line(p, [bf(x, sgn * (z - 0.015), 0.003) for x, z in up[1:]] + [bf(tip[0] - 0.03, 0.0, 0.003)], 0.014, 0.01, PETAL_PURPLE, sides=4, glow=1.2)
	p.seg(bf(0.66, 0.0), bf(2.1, 0.0), 0.1, 0.03, STONE_DARK, sides=4)                        # a deep fuller
	for k in range(6):                                                                    # carved with glowing runes
		u = 0.74 + k * 0.23
		sh = (k * 3) % 4
		p.seg(bf(u, -0.1, 0.04), bf(u + 0.14, 0.1, 0.04), 0.022, 0.022, PETAL_PURPLE, sides=4, glow=3.2)
		p.seg(bf(u + 0.03 * sh, 0.1, 0.04), bf(u + 0.14, -0.03 - 0.02 * sh, 0.04), 0.022, 0.022, PETAL_PURPLE, sides=4, glow=3.2)
		if k % 2:
			p.seg(bf(u + 0.17, -0.1, 0.04), bf(u + 0.17, 0.1, 0.04), 0.022, 0.022, PETAL_PURPLE, sides=4, glow=3.2)
	guard = [(0.5, 0.0), (0.46, 0.34), (0.4, 0.56), (0.5, 0.74), (0.62, 0.72)]                  # a crossguard of black iron swept into crescents
	for sgn in (1, -1):
		_line(p, [bf(u, sgn * v, 0.0) for u, v in guard], 0.08, 0.03, IRON, sides=6, grad=(0.0, 0.6))
		_line(p, [bf(u, sgn * v, 0.02) for u, v in guard[1:]], 0.03, 0.012, STONE_LIGHT, sides=4, grad=(0.0, 0.4))
		p.blob((0.07, 0.06, 0.07), bf(0.62, sgn * 0.72, 0.02), PETAL_PURPLE, segs=(6, 4), glow=2.4)
	p.blob((0.24, 0.16, 0.24), bf(0.5, 0.0, 0.0), IRON, segs=(10, 6), grad=(0.0, 0.6))
	p.blob((0.14, 0.08, 0.14), bf(0.5, 0.0, 0.08), PETAL_PURPLE, segs=(8, 5), glow=3.0)        # a violet stone at its heart
	h0, h1 = bf(0.42, 0.0, -0.04), bf(-0.3, 0.0, -0.04)
	p.seg(h0, h1, 0.065, 0.07, STONE_DARK, sides=8)                                         # a long two-hand grip
	for k in range(6):
		t = (k + 0.5) / 6
		q = Vector(h0).lerp(Vector(h1), t)
		p.seg(tuple(q - Vector((0.02, 0, 0.02))), tuple(q + Vector((0.02, 0, 0.02))), 0.078, 0.078, PETAL_PURPLE if k % 2 else IRON, sides=8)
	pm = Vector(bf(-0.42, 0.0, 0.02))
	p.blob((0.26, 0.16, 0.26), tuple(pm), IRON, segs=(10, 6), grad=(0.0, 0.6))              # an eclipse for a pommel
	p.seg(tuple(pm + Vector((0, -0.07, 0))), tuple(pm + Vector((0, -0.09, 0))), 0.13, 0.13, GOLD, sides=16, glow=3.0)
	p.seg(tuple(pm + Vector((0, -0.09, 0))), tuple(pm + Vector((0, -0.11, 0))), 0.1, 0.1, IRON, sides=16, grad=(0.6, 1.0))
	for k in range(3):                                                                    # a dark smoke curling off the blade
		b = Vector(bf(1.1 + 0.45 * k, 0.3, 0.0))
		_rising_smoke(p, b.x, b.y - 0.04, b.z, 0.34 + 0.08 * k, w=0.022, glow=2.0, puff=None, phase=k * 2.0)
	for u, v, s in ((2.2, 0.55, 0.1), (1.4, -0.56, 0.08), (2.6, -0.3, 0.07)):
		_star(p, bf(u, v, 0.05), s)
	return p.build()


LONG_TABLE = {CLOTH_RED: (PETAL_PURPLE, 0.6, 1.0), ORANGE: (PETAL_PURPLE, 0.15, 0.5), STONE_DARK: (IRON, 0.0, 0.5)}   # a violet-black robe, still hemmed in gold
_long_table_robe = _starry("mantle_of_the_long_table", flameweave_robe, LONG_TABLE,
						   [(0.3, 0.7, 0.08), (0.7, 0.62, 0.09), (0.44, 0.46, 0.07), (0.78, 0.36, 0.08), (0.26, 0.28, 0.07), (0.6, 0.2, 0.08)])


def mantle_of_the_long_table():
	obj = _long_table_robe()
	vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
	lo = [min(v[i] for v in vs) for i in range(3)]
	hi = [max(v[i] for v in vs) for i in range(3)]
	p = Prop("long_table_brooch", 1959)
	c = (lo[0] + (hi[0] - lo[0]) * 0.52, lo[1] - 0.06, lo[2] + (hi[2] - lo[2]) * 0.8)
	p.seg((c[0], c[1] + 0.02, c[2]), (c[0], c[1] - 0.02, c[2]), 0.16, 0.16, GOLD, sides=18, grad=(0.0, 0.3), glow=3.0)   # an eclipse brooch at the throat
	p.seg((c[0], c[1] - 0.02, c[2]), (c[0], c[1] - 0.05, c[2]), 0.12, 0.12, IRON, sides=18, grad=(0.6, 1.0))
	for k in range(12):
		a = k * math.tau / 12
		p.seg((c[0] + math.cos(a) * 0.16, c[1], c[2] + math.sin(a) * 0.16), (c[0] + math.cos(a) * (0.24 + 0.05 * (k % 2)), c[1], c[2] + math.sin(a) * (0.24 + 0.05 * (k % 2))),
			  0.022, 0.0, GOLD, sides=4, glow=2.8)
	for fx, fz, s in ((0.1, 0.9, 0.09), (0.94, 0.94, 0.08), (0.96, 0.1, 0.07)):                # its starlight spilling off
		_star(p, (lo[0] + (hi[0] - lo[0]) * fx, lo[1] - 0.1, lo[2] + (hi[2] - lo[2]) * fz), s, sw=GOLD, glow=2.6)
	p.build()
	return obj


def ring_of_the_empty_chair():
	p = Prop("ring_of_the_empty_chair", 1961)
	_ring(p, STONE_LIGHT)                                                                  # a band of dark silver
	for k in range(5):
		a = math.radians(-50 + k * 25 - 180)
		p.blob((0.07, 0.07, 0.07), (math.cos(a) * 0.4, -0.08, 0.4 + math.sin(a) * 0.4), PETAL_PURPLE, segs=(6, 4), glow=1.6)
	p.box((0.44, 0.34, 0.06), (0.0, 0.0, 0.86), IRON, grad=(0.0, 0.6))                        # set with a tiny throne
	for sx in (-1, 1):
		for sy in (-1, 1):
			p.seg((sx * 0.18, sy * 0.13, 0.83), (sx * 0.18, sy * 0.13, 0.76), 0.03, 0.03, IRON, sides=5)
		p.seg((sx * 0.21, -0.14, 0.89), (sx * 0.21, 0.12, 0.98), 0.03, 0.03, STONE_LIGHT, sides=5)   # its armrests
	_slab(p, [(-0.22, 0.88), (0.22, 0.88), (0.22, 1.32), (0.12, 1.4), (0.0, 1.56), (-0.12, 1.4), (-0.22, 1.32)], 0.13, 0.19, IRON, grad=(0.0, 0.6))
	for a, b in (((-0.22, 1.32), (0.0, 1.56)), ((0.0, 1.56), (0.22, 1.32))):
		p.seg((a[0], 0.12, a[1]), (b[0], 0.12, b[1]), 0.022, 0.022, STONE_LIGHT, sides=4)
	p.box((0.34, 0.26, 0.02), (0.0, -0.01, 0.9), PETAL_PURPLE, grad=(0.4, 1.0))              # its cushion, and no one on it
	_star(p, (0.0, 0.1, 1.24), 0.1, glow=3.0)                                                # but a star where a head would be
	for k in range(2):
		_rising_smoke(p, -0.1 + 0.2 * k, -0.06, 0.94, 0.3, w=0.016, glow=1.8, puff=None, phase=k * 2.2)
	return p.build()


BONEYARD_SUMMIT = [godwar_insignia, petrified_shard, divine_bronze, stolen_relic, grave_gold, star_fragment, shadowfur, blackened_offering,
				   marshals_broken_standard, champions_stone_crest, godforged_core, oszkars_relic_crown, long_table_goblet, astraels_star_heart,
				   nightjaws_fang, crown_of_the_uninvited, godwar_pauldrons, marshals_standard_blade, stoneskin_girdle, champions_crest_shield,
				   divine_bronze_ring, godforged_heart_amulet, scavengers_gloves, relic_crown_circlet, grave_gold_signet, long_table_chalice_charm,
				   starfragment_boots, star_heart_staff, shadowfur_cloak, nightjaw_fang_bow, offering_bearers_sash, crown_of_the_table,
				   unlit_worldblade, mantle_of_the_long_table, ring_of_the_empty_chair]


# ---------------------------------------------------------------- bag quests: Tamu's rainproof pack (Rainhold) and Moti's tea-picker's satchel (Dewstep)
# The same kind of line as Tovin's trail pack: gather the makings, have them worked,
# get the bag. Rainhold's is oiled black netting over reed-green with gnoll-fang
# toggles; Dewstep's is golden jackal hide sewn with pale moth silk and shut with a
# lacquered beetle-shell clasp.


def _egg_front(c, r, x, z, off=0.0):
	"""The point on an egg's (a blob's) front face at (x, z), pushed out along its normal by off."""
	cx, cy, cz = c
	a, b, cc = r
	q = max(1 - ((x - cx) / a) ** 2 - ((z - cz) / cc) ** 2, 0.0)
	y = cy - b * math.sqrt(q)
	n = Vector(((x - cx) / a ** 2, (y - cy) / b ** 2, (z - cz) / cc ** 2))
	n = n.normalized() if n.length > 1e-6 else Vector((0, -1, 0))
	return tuple(Vector((x, y, z)) + n * off)


def _egg_q(c, r, x, z):
	return 1 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2


def _egg_flap(p, c, r, fw, bottom, sag, sw, off=0.03, grad=(0.1, 0.8)):
	"""A flap laid over an egg-shaped bag from near its top down to a rounded edge;
	returns the points along its edge (left side, bottom, right side)."""
	n, m = 12, 6
	def z_top(x):
		return c[2] + r[2] * 0.93 * math.sqrt(max(1 - (x / r[0]) ** 2, 0.0))
	def z_bot(x):
		return bottom + sag * (x / fw) ** 2
	verts, faces = [], []
	for i in range(n + 1):
		x = -fw + 2 * fw * i / n
		for j in range(m + 1):
			z = z_top(x) + (z_bot(x) - z_top(x)) * j / m
			verts.append(_egg_front(c, r, x, z, off))
	for i in range(n):
		for j in range(m):
			k = i * (m + 1) + j
			faces.append((k, k + 1, k + m + 2, k + m + 1))
	p.poly(verts, faces, sw, grad=grad)
	edge = [verts[j] for j in range(m + 1)] + [verts[i * (m + 1) + m] for i in range(1, n)] + [verts[n * (m + 1) + j] for j in range(m, -1, -1)]
	_line(p, [_egg_front(c, r, v[0], v[2], off + 0.005) for v in edge], 0.028, 0.028, sw, sides=5, grad=grad)   # its thick edge
	return edge


def _egg_net(p, c, r, z0, z1, cell, sw, knot, off=0.035):
	"""Diamond netting over an egg's front between heights z0 and z1, knotted where the cords cross."""
	lim = r[0] + r[2]
	k = -lim
	while k <= lim:
		for sx in (1, -1):
			run = []
			s = -lim
			while s <= lim + 1e-6:
				x, z = s, c[2] + sx * (s - k)
				ok = z0 <= z <= z1 and _egg_q(c, r, x, z) > 0.08
				if ok:
					run.append(_egg_front(c, r, x, z, off))
				if (not ok or s + 0.04 > lim) and len(run) > 1:
					_line(p, run, 0.018, 0.018, sw, sides=4, grad=(0.1, 0.6))
				if not ok:
					run = []
				s += 0.04
		k += cell
	k1 = -lim
	while k1 <= lim:
		k2 = -lim
		while k2 <= lim:
			x, z = (k1 + k2) / 2, c[2] + (k2 - k1) / 2
			if z0 <= z <= z1 and _egg_q(c, r, x, z) > 0.08:
				p.blob((0.05, 0.05, 0.05), _egg_front(c, r, x, z, off + 0.005), knot, segs=(6, 4), grad=(0.0, 0.5))
			k2 += cell
		k1 += cell


def _flat_net(p, to3, x0, x1, z0, z1, cell, sw, knot, r=0.016, ragged=0.0, grad=(0.1, 0.6)):
	"""Diamond netting on a plane (to3 maps (x, z[, off])), knots at the crossings."""
	lim = abs(x0) + abs(x1) + abs(z0) + abs(z1)
	def inside(x, z):
		return x0 <= x <= x1 and z0 - ragged * math.sin(x * 9) ** 2 <= z <= z1
	k = -lim
	while k <= lim:
		for sx in (1, -1):
			run = []
			s = x0
			while s <= x1 + 1e-6:
				z = sx * (s - k)
				if inside(s, z):
					run.append(to3(s, z))
				elif len(run) > 1:
					_line(p, run, r, r, sw, sides=4, grad=grad)
					run = []
				else:
					run = []
				s += 0.03
			if len(run) > 1:
				_line(p, run, r, r, sw, sides=4, grad=grad)
		k += cell
	k1 = -lim
	while k1 <= lim:
		k2 = -lim
		while k2 <= lim:
			x, z = (k1 + k2) / 2, (k2 - k1) / 2
			if inside(x, z):
				p.blob((r * 3.2, r * 3.2, r * 2.6), to3(x, z, 0.004), knot, segs=(6, 4), grad=grad)
			k2 += cell
		k1 += cell


def bone_netting_needles():
	p = Prop("bone_netting_needles", 1971)
	tie = Vector((0.0, 0.0, 0.62))
	for k, (deg, y, ln) in enumerate(((50, 0.07, 1.1), (58, 0.0, 1.1), (66, -0.07, 1.05))):   # three long needles crossing at the tie
		d = Vector((math.cos(math.radians(deg)), 0, math.sin(math.radians(deg))))
		butt, tip = tie - d * 0.62 * ln + Vector((0, y, 0)), tie + d * 0.72 * ln + Vector((0, y, 0))
		p.seg(tuple(butt), tuple(butt + (tip - butt) * 0.8), 0.045, 0.04, BONE, sides=7, grad=(0.0, 0.45))
		p.seg(tuple(butt + (tip - butt) * 0.8), tuple(tip), 0.04, 0.0, BONE, sides=7, grad=(0.0, 0.45))
		_oval(p, butt - d * 0.04, d, Vector((d.z, 0, -d.x)), 0.08, 0.05, 0.022, BONE, n=10)       # its filed eye
		p.blob((0.07, 0.03, 0.035), tuple(butt - d * 0.04 + Vector((0, -0.03, 0))), STONE_DARK, rot=(0, -deg, 0), segs=(6, 4))   # the hole through it
	d = Vector((math.cos(math.radians(58)), 0, math.sin(math.radians(58))))
	perp = Vector((d.z, 0, -d.x))
	for k in range(4):                                                                     # a few turns of cord round the middle
		_oval(p, tie + d * (-0.06 + k * 0.04), perp, Vector((0, 1, 0)), 0.1, 0.09, 0.017, WOOD, n=12)
	a = tie + perp * 0.1 + Vector((0, -0.06, 0))                                           # and a loose end
	_line(p, [tuple(a), tuple(a + Vector((0.1, -0.02, -0.06))), tuple(a + Vector((0.14, -0.03, -0.18)))], 0.017, 0.012, WOOD, sides=5)
	return p.build()


def oiled_fishnet():
	p = Prop("oiled_fishnet", 1973)
	for k in range(3):                                                                    # folded in three, each fold a rolled edge
		w, d, z = 1.3 - k * 0.1, 0.92 - k * 0.08, 0.07 + k * 0.14
		p.box((w, d, 0.13), (k * 0.02, k * 0.03, z), IRON, rot=(0, 0, k * 3 - 3), grad=(0.3, 0.9))
		p.seg((-w * 0.5, -d * 0.5 + k * 0.02, z), (w * 0.5, -d * 0.5 + k * 0.02, z), 0.075, 0.075, IRON, sides=8, grad=(0.2, 0.7))
		p.seg((-w * 0.45, -d * 0.5 - 0.05 + k * 0.02, z + 0.04), (w * 0.3, -d * 0.5 - 0.05 + k * 0.02, z + 0.05), 0.01, 0.006, CLOTH_WHITE, sides=4, glow=0.7)
		for j in range(9):                                                                # knots along the fold
			x = -w * 0.45 + j * w * 0.1125
			p.blob((0.06, 0.05, 0.05), (x, -d * 0.5 - 0.06 + k * 0.02, z + 0.03 * ((j + k) % 2)), WOOD, segs=(6, 4), grad=(0.7, 1.0))
	top = 0.07 + 2 * 0.14 + 0.066
	_flat_net(p, lambda x, z, off=0.0: (x + 0.04, z + 0.06, top + off), -0.5, 0.5, -0.33, 0.33, 0.16, WOOD, WOOD, r=0.02, grad=(0.65, 1.0))
	_flat_net(p, lambda x, z, off=0.0: (x - 0.1, z - 0.78, 0.02 + off), -0.55, 0.45, -0.3, 0.25, 0.16, WOOD, WOOD, r=0.02, ragged=0.12, grad=(0.65, 1.0))  # a spill of it on the ground
	for (x0, y0, x1, y1) in ((-0.42, -0.2, -0.1, 0.12), (0.05, -0.28, 0.32, -0.05), (-0.2, -0.95, 0.1, -0.7)):   # the oil's shine
		z = top + 0.03 if y0 > -0.5 else 0.05
		p.seg((x0, y0, z), (x1, y1, z), 0.014, 0.008, CLOTH_WHITE, sides=4, glow=0.9)
	p.seg((0.55, -0.72, 0.0), (0.55, -0.72, 0.16), 0.12, 0.12, AMBER, sides=10, grad=(0.1, 0.6))   # a cork float
	p.rock((0.14, 0.12, 0.1), (-0.66, -0.95, 0.05), STONE_LIGHT, jitter=0.1)                    # and a stone sinker
	return p.build()


def tamus_rainproof_pack():
	p = Prop("tamus_rainproof_pack", 1975)
	c, r = (0, 0, 0.5), (0.43, 0.29, 0.5)
	p.blob((0.86, 0.58, 1.0), c, LEAF, segs=(16, 10), grad=(0.2, 0.8))                         # a reed-green lining
	for sx in (-1, 1):
		p.blob((0.24, 0.3, 0.4), (sx * 0.47, 0.0, 0.34), LEAF, segs=(8, 6), grad=(0.35, 0.95))    # side pouches
		_loop(p, (sx * 0.5, 0.0, 0.34), 0.13, True, 0.02, IRON, n=10, squash=1.2)              # netted round
	_egg_net(p, c, r, 0.08, 0.66, 0.15, IRON, IRON)                                            # the oiled netting over it
	edge = _egg_flap(p, c, r, 0.36, 0.6, 0.1, IRON, off=0.05, grad=(0.1, 0.7))                   # an oiled flap
	for (x0, z0, x1, z1) in ((-0.24, 0.9, -0.06, 0.94), (-0.28, 0.82, -0.14, 0.84)):          # rain shining on it
		p.seg(_egg_front(c, r, x0, z0, 0.065), _egg_front(c, r, x1, z1, 0.065), 0.012, 0.008, CLOTH_WHITE, sides=4, glow=0.9)
	for x in (-0.17, 0.17):                                                                    # gnoll-fang toggles in cord loops
		z = 0.6 + 0.1 * (x / 0.36) ** 2
		a = _egg_front(c, r, x, z, 0.06)
		b = _egg_front(c, r, x, z - 0.2, 0.08)
		_oval(p, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 0.02, (a[2] + b[2]) / 2 - 0.02), (1, 0, 0), (0, 0, 1), 0.035, 0.12, 0.016, WOOD, n=10)
		p.seg((b[0] - 0.13, b[1] - 0.05, b[2]), (b[0] + 0.13, b[1] - 0.05, b[2]), 0.04, 0.0, BONE, sides=6, grad=(0.0, 0.5))
		p.blob((0.06, 0.06, 0.06), (b[0] - 0.13, b[1] - 0.05, b[2]), BONE, segs=(6, 4), grad=(0.3, 0.6))
	p.seg((-0.46, 0.06, 1.02), (0.46, 0.06, 1.02), 0.13, 0.13, AMBER, sides=10, grad=(0.45, 0.85))   # a rolled reed mat on top
	for sx in (-1, 1):
		p.seg((sx * 0.46, 0.06, 1.02), (sx * 0.47, 0.06, 1.02), 0.1, 0.1, WOOD, sides=10, grad=(0.3, 0.7))
		_oval(p, (sx * 0.26, 0.06, 1.02), (0, 1, 0), (0, 0, 1), 0.14, 0.14, 0.022, IRON, n=10)
	return p.build()


def moth_silk_thread():
	p = Prop("moth_silk_thread", 1977)
	p.seg((0, 0, 0), (0, 0, 0.1), 0.42, 0.42, WOOD, sides=16)                                  # a spool
	p.seg((0, 0, 0.8), (0, 0, 0.9), 0.42, 0.42, WOOD, sides=16)
	p.seg((0, 0, 0.1), (0, 0, 0.8), 0.33, 0.33, CLOTH_WHITE, sides=16, grad=(0.0, 0.3), glow=0.25)   # wound with pale silk
	for k in range(9):                                                                         # that shimmers pink and blue
		z = 0.15 + k * 0.075
		p.seg((0, 0, z), (0, 0, z + 0.018), 0.337, 0.337, DAWN if k % 2 else AQUA, sides=16, grad=(0.0, 0.1), glow=0.9)
	pts = [(0.3, -0.18, 0.5), (0.5, -0.36, 0.32), (0.66, -0.5, 0.12), (0.85, -0.5, 0.03)]
	_line(p, pts, 0.016, 0.012, CLOTH_WHITE, sides=4, grad=(0.0, 0.2))                          # a loose strand
	for q in pts[1:]:
		p.blob((0.035, 0.035, 0.035), q, CLOTH_WHITE, segs=(5, 4), glow=2.0)
	to3 = _tangent(FRONT_A, 0.345)                                                             # a pale silk moth resting on it
	for sx in (-1, 1):
		fore = [(sx * x, z) for x, z in _rot2([(0, 0), (0.12, 0.06), (0.26, 0.1), (0.34, 0.04), (0.32, -0.06), (0.18, -0.1), (0.05, -0.05)], 18)]
		hind = [(sx * x, z) for x, z in _rot2([(0, 0), (0.1, 0.0), (0.2, -0.04), (0.22, -0.14), (0.12, -0.2), (0.03, -0.1)], -12)]
		for outline, off, sw, g in ((hind, 0.02, HIDE, (0.0, 0.4)), (fore, 0.035, DAWN, (0.25, 0.55))):
			pts = [to3(x, 0.5 + z, off) for x, z in outline]
			p.poly(pts, [tuple(range(len(pts)))], sw, grad=g)
		e = (sx * 0.2, 0.56)
		p.blob((0.08, 0.08, 0.07), to3(e[0], e[1], 0.045), WOOD, segs=(8, 4), grad=(0.3, 0.7))          # eye spots
		p.blob((0.03, 0.03, 0.03), to3(e[0], e[1], 0.055), CLOTH_WHITE, segs=(6, 4), glow=2.0)
		p.seg(to3(sx * 0.02, 0.6, 0.05), to3(sx * 0.12, 0.74, 0.05), 0.008, 0.004, HIDE, sides=3)       # feathery feelers
	p.seg(to3(0, 0.62, 0.05), to3(0, 0.38, 0.05), 0.035, 0.02, CLOTH_WHITE, sides=6, grad=(0.2, 0.5))   # its furry body
	return p.build()


SATCHEL_C, SATCHEL_R = (0, 0, 0.38), (0.52, 0.2, 0.38)


def _pickers_satchel(p):
	"""The jackal-hide satchel, sewn with pale moth silk; returns where the clasp goes."""
	c, r = SATCHEL_C, SATCHEL_R
	p.blob((1.04, 0.4, 0.76), c, AMBER, segs=(16, 10), grad=(0.6, 1.0))                      # golden jackal hide
	p.blob((0.9, 0.34, 0.12), (0, 0, 0.04), AMBER, segs=(14, 5), grad=(0.8, 1.0))            # a flat bottom
	edge = _egg_flap(p, c, r, 0.44, 0.2, 0.16, HIDE, off=0.035, grad=(0.1, 0.6))            # a paler flap
	for k in range(len(edge) - 1):                                                          # pale silk stitching inside its edge
		if k % 2:
			continue
		a, b = edge[k], edge[k + 1]
		a2 = (a[0] * 0.9, a[2] + (c[2] + 0.2 - a[2]) * 0.1)
		b2 = (b[0] * 0.9, b[2] + (c[2] + 0.2 - b[2]) * 0.1)
		p.seg(_egg_front(c, r, a2[0], a2[1], 0.055), _egg_front(c, r, b2[0], b2[1], 0.055), 0.016, 0.016, CLOTH_WHITE, sides=4, glow=0.8)
	for sx in (-1, 1):                                                                      # and down both side seams
		for k in range(4):
			z = 0.1 + k * 0.08
			x = sx * r[0] * 0.86 * math.sqrt(max(1 - ((z - c[2]) / r[2]) ** 2, 0.0))
			p.seg(_egg_front(c, r, x, z, 0.02), _egg_front(c, r, x, z + 0.04, 0.02), 0.015, 0.015, CLOTH_WHITE, sides=4, glow=0.8)
	pts = []
	for k in range(11):                                                                     # a long shoulder strap
		a = math.pi * k / 10
		pts.append((-math.cos(a) * 0.5, 0.1, 0.4 + math.sin(a) * 0.62))
	_line(p, pts, 0.045, 0.045, HIDE, sides=5, grad=(0.3, 0.8))
	return _egg_front(c, r, 0.0, 0.22, 0.07)


def stitched_pickers_satchel():
	p = Prop("stitched_pickers_satchel", 1979)
	clasp = _pickers_satchel(p)
	_oval(p, (clasp[0], clasp[1] + 0.02, clasp[2] - 0.05), (1, 0, 0), (0, 0, 1), 0.05, 0.04, 0.014, WOOD, n=10)   # an empty loop where the clasp will go
	a = _egg_front(SATCHEL_C, SATCHEL_R, 0.44, 0.39, 0.05)                                   # the needle still hanging on its silk
	pts = [a, (a[0] + 0.08, a[1] - 0.06, a[2] - 0.12), (a[0] + 0.12, a[1] - 0.1, a[2] - 0.28)]
	_line(p, pts, 0.012, 0.012, CLOTH_WHITE, sides=4, grad=(0.0, 0.2))
	e = Vector(pts[-1])
	p.seg(tuple(e), tuple(e + Vector((0.03, -0.02, -0.3))), 0.025, 0.0, BONE, sides=6, grad=(0.0, 0.4))
	return p.build()


def _tea_leaf(p, base, deg, ln, y):
	w = ln * 0.3
	pts = [(0, 0), (w * 0.8, ln * 0.3), (w, ln * 0.55), (w * 0.6, ln * 0.82), (0, ln), (-w * 0.6, ln * 0.82), (-w, ln * 0.55), (-w * 0.8, ln * 0.3)]
	pts = _rot2(pts, deg, (0, 0))
	_slab(p, [(base[0] + x, base[1] + z) for x, z in pts], y - 0.012, y + 0.012, LEAF, grad=(0.1, 0.7))
	tip = _rot2([(0, ln * 0.9)], deg, (0, 0))[0]
	p.seg((base[0], y - 0.016, base[1]), (base[0] + tip[0], y - 0.016, base[1] + tip[1]), 0.012, 0.004, SEAFOAM, sides=3)   # its midrib


def motis_tea_pickers_satchel():
	p = Prop("motis_tea_pickers_satchel", 1981)
	clasp = _pickers_satchel(p)
	x, y, z = clasp
	p.blob((0.36, 0.16, 0.3), (x, y - 0.02, z), WOOD, segs=(12, 8), grad=(0.6, 1.0))        # a lacquered beetle-shell clasp
	p.seg((x, y - 0.1, z + 0.12), (x, y - 0.1, z - 0.12), 0.011, 0.011, STONE_DARK, sides=4)  # the seam of its wing cases
	p.blob((0.08, 0.03, 0.05), (x - 0.07, y - 0.09, z + 0.06), CLOTH_WHITE, segs=(6, 4), glow=1.5)   # the lacquer's shine
	p.blob((0.035, 0.02, 0.025), (x + 0.07, y - 0.09, z + 0.05), CLOTH_WHITE, segs=(5, 4), glow=1.2)
	p.seg((x, y + 0.02, z + 0.14), (x, y - 0.04, z + 0.2), 0.02, 0.02, GOLD, sides=5)          # pinned to the flap
	for bx, deg, ln, yy in ((-0.2, 22, 0.42, -0.02), (-0.04, -8, 0.5, 0.0), (0.14, -30, 0.4, -0.03)):   # fresh tea leaves peeking out
		_tea_leaf(p, (bx, 0.6), deg, ln, yy)
	return p.build()


BAG_QUESTS = [bone_netting_needles, oiled_fishnet, tamus_rainproof_pack, moth_silk_thread, stitched_pickers_satchel,
			  motis_tea_pickers_satchel]


AGNAVAR_HEARTH_SMOKEWOOD = [court_signet, salamander_scale, heart_of_flame, heretics_charm, brannaghs_molten_crown, scorchtongues_brazier,
							forgeheart_core, stolen_ember, ember_heartwood, smoke_pelt, soot_mask_fragment, fire_moth_dust, glowcap,
							emberhearts_heart, ashen_antler, kolts_antlered_mask, moth_queens_wing, courtiers_bracer, brannaghs_scepter,
							salamanderscale_boots, scorchtongue_staff, flameheart_ring, forgeheart_amulet, penitents_sash, unburnt_mantle,
							heartwood_shield, emberheart_bow, smokehide_gloves, ashen_antler_helm, sootveil_hood, kolts_brand, mothwing_cloak,
							moth_queens_diadem]


STANDING_SKY = [skyforged_helm, skyforged_breastplate, skyforged_vambraces, skyforged_gauntlets, skyforged_greaves, skyforged_boots,
				skyforged_shield, windrunner_jerkin, windrunner_leggings, windrunner_gloves, windrunner_boots, galeweave_cap, galeweave_robe,
				galeweave_gloves, galeweave_slippers, skyforged_sword, skyforged_war_axe, skyforged_greataxe, zephyr_dirk, stormwood_staff,
				galehold_longbow, windcutter_arrow, gale_essence, eagle_talon, thunder_feather, kite_silk, giants_standing_stone, stalker_pelt,
				thunderhoof_horn, horsetail_braid, barrow_bronze, storm_eye_heart, skarrows_crest, tarns_painted_sail, stackstones_capstone,
				tawnyjaws_fang, herd_kings_horn, khans_horsetail_banner, barrow_lords_death_mask, galescout_bracer, storm_eye_amulet, talon_ring,
				thunderwing_cloak, kitesilk_sash, tarns_skyblade, handstone_pendant, capstone_maul, stalkerhide_boots, tawnyjaw_fang_dirk,
				hornbone_gauntlets, herd_kings_helm, horsetail_charm, khans_curved_blade, barrow_bronze_greaves, death_mask_cowl]


PART3_ZONES = [stonebrow_tusk, roc_feather, wyvern_barb, frozen_breath, sentinels_sunbadge, mirror_shard, salt_crab_claw, nomad_veil,
			   wader_plume, whisker_barbel, hippo_tusk, mud_charm, serpent_scale, smugglers_token, reaver_armring, clawfolk_pincer,
			   sea_serpent_scale, gull_feather, bottled_lightning, uthraks_war_horn, sunwing_plume, storm_crown_shard, halvards_sun_banner,
			   cracked_mirror_face, saltclaws_pearl, asras_salt_crown, sky_ray_spine, river_kings_pearl_crown, shell_mask, coilmothers_fang,
			   blackwaters_ledger, saltbeards_whalebone_crown, horror_lure, whitefins_fin, tempest_heart, dawnwatch_bracer, ogrehide_belt,
			   rocfeather_cloak, frostspirit_ring, stormcrown_circlet, sunbadge_pendant, halvards_sunblade, warlords_war_horn,
			   mirrorglass_gloves, saltcrust_boots, skiffrunner_sash, waderplume_cap, mask_of_the_reflection, saltclaw_pearl_ring,
			   asras_skiff_blade, rayspine_staff, barbel_whip_belt, hippohide_jerkin, pearl_crown_of_the_river, mudcharm_bracelet,
			   shellmask_amulet, serpentscale_gloves, coilmother_fang_dirk, blackwater_cutlass, reaver_armring_band, saltbeards_axe,
			   clawfolk_carapace_shield, lure_of_the_deep, serpentskin_leggings, whitefin_cloak, gullfeather_boots, tempest_heart_staff]


FORGEHOLD_BURN = [magmasteel_helm, magmasteel_breastplate, magmasteel_vambraces, magmasteel_gauntlets, magmasteel_greaves, magmasteel_boots,
				  magmasteel_shield, emberhide_jerkin, emberhide_leggings, emberhide_gloves, emberhide_boots, flameweave_cap, flameweave_robe,
				  flameweave_gloves, flameweave_slippers, magmasteel_sword, magmasteel_war_axe, magmasteel_greataxe, blackglass_dirk,
				  forgeheart_staff, forgehold_longbow, magmasteel_arrow, firehound_mane, imp_horn, smoke_essence, giants_coal,
				  firebird_feather, glass_core, obsidian_scale, glass_silk, glassbound_insignia, ashmaws_mane, cackleflames_crown,
				  thanes_iron_crown, phoenix_ember, colossus_heart, vitrax_eye, shardmothers_crown, aldrics_banner, coalhand_gauntlets,
				  thanes_hammer, firehound_mantle, ashmaws_fang_pendant, tallpine_signet, smokeweave_sash, cackleflame_scepter,
				  firefeather_cap, ring_of_the_phoenix, glasswrights_lenses, heart_of_the_colossus, obsidian_scale_leggings, eye_of_vitrax,
				  glassweb_gloves, shardmothers_fang, glassbound_greaves, aldrics_glass_blade]


DEWSTEP = [moth_wing, rice_beetle_shell, stolen_trinket, jackal_pelt, cobra_fang, tiger_pelt, dustpaw_beads, wisp_light, funeral_coin,
		   pilfers_bangle, amberstripes_fang, rattlejaws_necklace, widows_lantern, teagarden_sandals, dawnlight_ring,
		   jackalhide_leggings, cobrafang_dagger, tigerstripe_mantle, wardens_buckler, dawnsteel_shortsword, ravis_prayer_beads,
		   lampwardens_charm, rattlejaws_cleaver]


HANDS_ARMS = [cloth_gloves, leather_gloves, handsewn_leather_gloves, hardened_leather_gloves, farmhands_gloves, sharkskin_gloves,
			  trollhide_gloves, frogskin_gloves, cinderscale_gloves, silkweave_gloves, silkweave_mitts, rainsilk_gloves,
			  dawnweave_gloves, ashweave_gloves, monks_wraps, iron_gauntlets, tempered_gauntlets, steel_gauntlets,
			  tidesteel_gauntlets, emberforged_gauntlets, cloth_sleeves, leather_sleeves, netmakers_sleeves, vale_patrol_bracer,
			  tempered_vambraces, steel_vambraces, tidesteel_vambraces, emberforged_vambraces, skyrend_cloak, drakescale_cloak]


MONSOON_WEST = [pondkin_fetish, reedstalker_plume, eel_skin, bogwing_wing, sunken_charm, sedge_charm, tidesworn_insignia, naga_scale,
				tempest_shard, crab_carapace, bloatking_crown, stilt_legs_plume, headwomans_lotus, marrowroot_heart, varundra_crown,
				sessavi_pearl, wardens_chain, chitterjaw_claw, reedwalker_boots, bloatking_scepter, heronfeather_cloak, veyamar_locket,
				sedgebane_charm, tideking_helm, pearl_of_the_deeps, stormbound_bracer, chitin_shield, tidesworn_blade, naga_fang_dirk]


HIGH_TERRACE_ASHFALL = [griffon_feather, harpy_talon, prayer_bead, abbots_seal, gargoyle_shard, leopard_pelt, yak_hair, troll_hide,
						colossus_heartstone, skyrend_plume, magma_core, drake_scale, salamander_tail, ember_sigil, ashkars_brand,
						cindermaw_heart, ash_essence, charred_bone, pilgrims_prayer_beads, heartstone_ring, wraithbone_ring,
						scouts_signet, terrace_tea, obsidian_arrow, magma_heart_amulet]


TRADESKILLS = [bag_of_flour, jar_of_spices, vial_of_water, tanning_salts, spool_of_thread, bundle_of_herbs, small_brick_of_ore,
			   large_brick_of_ore, water_flask, bundle_of_shafts, smithy_hammer, sewing_kit, mortar_and_pestle, hearthside_cookbook,
			   tailors_pattern_book, alchemists_notes, smiths_handbook, raw_meat, frog_legs, tanned_leather, thick_leather, wool_cloth,
			   silk_cloth, iron_bar, steel_bar, roast_meat, grilled_trout, fish_stew, hunters_pie, frog_legs_saute, lagoon_feast,
			   koi_platter, minor_healing_potion, antidote, healing_potion, clarity_tonic, draught_of_toughness, troll_tonic,
			   draught_of_swiftness, greater_healing_potion, stitched_hide_pouch, wool_satchel, crocskin_backpack, iron_tipped_arrow,
			   homeward_stone, draught_of_homecoming, grove_seed]


SMALL = {f.__name__: f for f in [gnoll_fang, beetle_eye, bone_chips, rat_whiskers, fishing_bait, bone_charm,
								 fang_necklace, tarnished_ring, copper_band, bonecarved_talisman, small_sack,
								 worn_backpack, gnollhide_satchel, leather_backpack, braided_whisker_cord, blackpaw_pelt,
									 stitched_blackpaw_hide, tovins_trail_pack, crude_arrow, sling_stone, leather_sling,
									 patchwork_pants, leather_leggings, iron_greaves, wolf_pelt, dire_wolf_fang, bear_claw,
									 bear_hide, spider_silk, venom_sac, orc_tusk, hollow_watch_signet, grolthars_tusk_necklace, hollow_watch_pendant,
									 mire_toad_skin, leech_teeth, turtle_shell_plate, mirescale_scale, waterlogged_locket,
									 snapjaws_shell, drowned_bell, smoked_mereperch, pearl_of_the_mere, scaled_leggings,
									 boar_tusk, boar_hide, brigand_armband, garricks_ledger, straw_heart, loaf_of_bread, harvest_band,
									 ram_horn, ram_fleece, sunhawk_feather, sunstone_shard, linen_wrappings, pilgrim_token, cult_sigil,
									 sun_scarab, hierophants_mask, dawn_tusk_pendant, chitin_plate, scorpion_stinger, queens_stinger,
									 bleached_bone, salt_crystal, raider_scarf, raider_warhorn, titans_heart, bone_talisman,
									 river_trout, mud_carp, lagoon_snapper, monsoon_eel, jungle_catfish, rainbow_koi, tattered_boot, troll_tusk,
									 frog_skin, croc_hide, croc_tooth, elemental_essence, gorraks_crown, heart_of_the_storm, graveljaws_tooth, tide_trunk_charm] + TRADESKILLS + HIGH_TERRACE_ASHFALL + MONSOON_WEST + HANDS_ARMS + DEWSTEP + FORGEHOLD_BURN + PART3_ZONES + STANDING_SKY + AGNAVAR_HEARTH_SMOKEWOOD + SKY_SUMMIT + BONEYARD + BONEYARD_SUMMIT + BAG_QUESTS}
SMALL.update({"emberforged_greaves": iron_greaves, "steel_greaves": iron_greaves,  # drawn legs beat the body part's boots
			  "cinderscale_leggings": leather_leggings})


# ---------------------------------------------------------------- rendering

def load_items():
	items = {}
	for path in sorted(glob.glob(os.path.join(ROOT, "data/items/*.json"))):
		items.update(json.load(open(path)))
	return items


def _body_parts(look, models):
	"""Imports a KayKit character and keeps only the parts a wearable swaps in,
	tinted as the game tints them."""
	entry = models["characters"][look["model"]]
	bpy.ops.import_scene.gltf(filepath=_res(entry["path"] if isinstance(entry, dict) else entry))
	parts = look["parts"]
	if all("Arm" in n for n in parts):
		parts = [n for n in parts if n.endswith("ArmLeft")]  # one arm, hung straight down, reads better than a T-pose pair
	for o in list(bpy.context.scene.objects):
		if o.type == "MESH" and o.name not in parts:
			bpy.data.objects.remove(o, do_unlink=True)
	if parts != look["parts"]:
		for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
			world = o.matrix_world.copy()
			o.parent = None
			for m in [m for m in o.modifiers if m.type == "ARMATURE"]:
				o.modifiers.remove(m)
			o.matrix_world = Matrix.Rotation(math.radians(90), 4, "Y") @ world
	if "tint" not in look:
		return
	tint = [int(look["tint"][i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
	for o in bpy.context.scene.objects:
		if o.type != "MESH":
			continue
		for slot in o.material_slots:
			mat = slot.material.copy()
			slot.material = mat
			nodes, links = mat.node_tree.nodes, mat.node_tree.links
			bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
			src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
			mix = nodes.new("ShaderNodeMix")
			mix.data_type = "RGBA"
			mix.blend_type = "MULTIPLY"
			mix.inputs["Factor"].default_value = 1.0
			if src:
				links.new(src, mix.inputs["A"])
			mix.inputs["B"].default_value = tint + [1.0]
			links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])


def build_subject(item_id, item, models):
	"""Puts the item's model in the (empty) scene; False if there is none."""
	wear = item.get("wear", "")
	if item_id in SMALL and (wear != "" or item.get("model")):  # a drawn icon beats the body part (KayKit legs are mostly boots) and the shared weapon model
		SMALL[item_id]()
		return True
	if wear in models.get("body_parts", {}):
		_body_parts(models["body_parts"][wear], models)
		return True
	if wear:
		for piece in gear.OUTFITS.get(wear, []):
			gear._build_piece(piece)
		return True
	if item.get("model") and item["model"] in models["weapons"]:
		bpy.ops.import_scene.gltf(filepath=_res(models["weapons"][item["model"]]))
		return True
	if item_id in SMALL:
		SMALL[item_id]()
		return True
	return False


def render_icon(path, size):
	scene = bpy.context.scene
	meshes = [o for o in scene.objects if o.type == "MESH"]
	lo = Vector((1e9, 1e9, 1e9))
	hi = Vector((-1e9, -1e9, -1e9))
	for o in meshes:
		for c in o.bound_box:
			w = o.matrix_world @ Vector(c)
			lo = Vector((min(lo[i], w[i]) for i in range(3)))
			hi = Vector((max(hi[i], w[i]) for i in range(3)))
	center = (lo + hi) / 2
	span = max((hi - lo).length, 0.01)
	scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
	scene.render.resolution_x = scene.render.resolution_y = size
	scene.render.film_transparent = True
	scene.view_settings.view_transform = "Standard"
	world = bpy.data.worlds.new("w")
	world.use_nodes = True
	world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.88, 1)
	world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
	scene.world = world
	sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
	sun.data.energy = 3.5
	sun.rotation_euler = (math.radians(40), math.radians(-20), math.radians(-35))
	bpy.context.collection.objects.link(sun)
	cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
	cam.data.type = "ORTHO"
	cam.data.ortho_scale = span * 0.95
	bpy.context.collection.objects.link(cam)
	direction = Vector((0.55, -1.0, 0.6)).normalized()
	cam.location = center + direction * span * 3
	cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
	scene.camera = cam
	scene.render.filepath = path
	bpy.ops.render.render(write_still=True)


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/icons", "--only": "", "--size": "128"}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) if opts["--only"] else None
	models = json.load(open(os.path.join(ROOT, "data/models.json")))
	missing = []
	for item_id, item in load_items().items():
		if only and item_id not in only:
			continue
		props.reset_scene()
		props._materials.clear()
		if not build_subject(item_id, item, models):
			missing.append(item_id)
			continue
		render_icon(os.path.abspath(os.path.join(opts["--out"], item_id + ".png")), int(opts["--size"]))
		print("icon %s" % item_id)
	if missing:
		print("NO ICON (add a model): %s" % ", ".join(missing))


if __name__ == "__main__":
	main()
