"""Renders the hotbar icons: one per spell and ability (assets/icons/spell_<id>.png)
and one per hotbar action (assets/icons/action_<name>.png).

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/spell_icons.py -- --out assets/icons [--only kick,gate] [--size 128]

Same camera, light and Dungeon palette as the item icons (icons.py), so the
hotbar and the bags read as one set. Magic glows (Prop's `glow`); the HUD puts
each icon on a gem colored by what the spell does, so shapes carry the meaning
and color carries the kind.
"""

import json
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import icons  # noqa: E402
import props  # noqa: E402
from props import (BONE, CLOTH_RED, CLOTH_WHITE, EMBER, FLAME, GOLD, HIDE, IRON, LEAF, Prop, RUNE,  # noqa: E402
				   STONE_DARK, STONE_LIGHT, WATER, WOOD, WOOD_GRAY)


def _ring(p, radius, z, r, swatch, glow=0.0, sides=18, tilt=0.0):
	for k in range(sides):
		a0, a1 = k * math.tau / sides, (k + 1) * math.tau / sides
		pt = lambda a: (math.cos(a) * radius, math.sin(a) * radius * math.cos(tilt), z + math.sin(a) * radius * math.sin(tilt))
		p.seg(pt(a0), pt(a1), r, r, swatch, sides=5, glow=glow)


def _import(path, rot=(0, 0, 0), loc=(0, 0, 0)):
	before = set(bpy.data.objects)
	bpy.ops.import_scene.gltf(filepath=icons._res(path))
	for o in set(bpy.data.objects) - before:
		if o.parent is None:
			o.rotation_mode = "XYZ"
			o.rotation_euler = [math.radians(a) for a in rot]
			o.location = loc


# ---------------------------------------------------------------- warrior abilities

def kick():
	p = Prop("kick", 301)
	p.seg((0, 0, 0.9), (0, 0, 0.25), 0.2, 0.22, HIDE, sides=8)                     # shaft
	p.blob((0.62, 0.34, 0.3), (0.2, 0, 0.15), HIDE, segs=(10, 6))                   # foot
	p.seg((0, 0, 0.9), (0, 0, 0.98), 0.23, 0.23, WOOD, sides=8)                     # cuff
	for k in range(3):                                                             # motion lines
		p.seg((-0.35, 0.2, 0.2 + k * 0.22), (-0.8, 0.2, 0.25 + k * 0.22), 0.03, 0.0, CLOTH_WHITE, sides=4)
	return p.build()


def taunt():
	p = Prop("taunt", 303)
	p.box((0.22, 0.2, 0.75), (0, 0, 0.62), CLOTH_RED, glow=1.6)                    # an angry "!"
	p.blob((0.26, 0.24, 0.26), (0, 0, 0.05), CLOTH_RED, segs=(8, 6), glow=1.6)
	for x in (-1, 1):                                                              # shouted at, from both sides
		for k in range(3):
			a = math.radians(-30 + k * 30)
			p.seg((x * 0.3, 0, 0.6 + math.sin(a) * 0.2), (x * (0.3 + math.cos(a) * 0.35), 0, 0.6 + math.sin(a) * 0.55), 0.04, 0.0, FLAME, sides=4, glow=1.4)
	return p.build()


def bash():
	p = Prop("bash", 305)
	p.seg((0, 0, 0.55), (0, -0.12, 0.55), 0.62, 0.62, WOOD, sides=20)              # a round shield, face on
	_ring(p, 0.62, 0.55, 0.06, IRON, sides=20, tilt=math.pi / 2)
	p.blob((0.3, 0.2, 0.3), (0, -0.15, 0.55), IRON, segs=(10, 6))                  # boss
	for k in range(6):                                                             # the impact, off its edge
		a = k * math.tau / 6 + 0.3
		p.seg((0.62, -0.2, 0.95), (0.62 + math.cos(a) * 0.4, -0.2, 0.95 + math.sin(a) * 0.4), 0.06, 0.0, FLAME, sides=4, glow=1.5)
	return p.build()


def bind_wound():
	p = Prop("bind_wound", 307)
	p.seg((0, 0, 0), (0, 0, 0.45), 0.4, 0.4, CLOTH_WHITE, sides=16, grad=(0.0, 0.5))  # a roll of bandage, standing
	p.seg((0, 0, 0.44), (0, 0, 0.47), 0.13, 0.13, WOOD_GRAY, sides=10)
	p.box((0.35, 0.1, 0.02), (0.18, -0.36, 0.47), CLOTH_RED)                        # red cross on the end
	p.box((0.1, 0.35, 0.02), (0.18, -0.36, 0.47), CLOTH_RED)
	p.box((0.5, 0.02, 0.4), (0.3, -0.4, 0.2), CLOTH_WHITE, rot=(0, 0, 25))          # the loose end unwinding
	return p.build()


def battle_cry():
	p = Prop("battle_cry", 309)
	pts = [(math.cos(t) * 0.55, 0, 0.35 + math.sin(t) * 0.35) for t in [i * math.pi / 6 for i in range(-1, 6)]]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):                                 # curved horn, widening to the bell
		p.seg(a, b, 0.06 + i * 0.04, 0.1 + i * 0.04, BONE, sides=10)
	for i in (1, 3):
		p.blob((0.2 + i * 0.07, 0.2 + i * 0.07, 0.08), pts[i], GOLD, segs=(10, 4))
	for k in range(3):                                                             # the sound
		_ring(p, 0.2 + k * 0.18, 0.15, 0.025, FLAME, glow=1.2, sides=10, tilt=math.pi / 2)
	return p.build()


# ---------------------------------------------------------------- healing

def _cross(p, s, swatch, glow):
	p.box((0.22 * s, 0.2 * s, 0.8 * s), (0, 0, 0.4 * s), swatch, glow=glow)
	p.box((0.62 * s, 0.2 * s, 0.22 * s), (0, 0, 0.5 * s), swatch, glow=glow)


def minor_healing():
	p = Prop("minor_healing", 311)
	for x in (-1, 1):                                                              # two leaves around a light
		p.blob((0.28, 0.08, 0.6), (x * 0.25, 0, 0.4), LEAF, rot=(0, x * 35, 0), segs=(8, 6), glow=0.6)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.3), GOLD, segs=(10, 8), glow=2.0)
	return p.build()


def light_healing():
	p = Prop("light_healing", 313)
	_cross(p, 1.0, GOLD, 1.8)
	_ring(p, 0.55, 0.45, 0.03, LEAF, glow=1.5, tilt=math.pi / 2)
	return p.build()


def circle_of_mending():
	p = Prop("circle_of_mending", 315)
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.22, 0.22, 0.22), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.12), LEAF, segs=(8, 6), glow=1.8)
	_ring(p, 0.6, 0.12, 0.035, GOLD, glow=1.2)
	_cross(p, 0.55, GOLD, 1.6)
	return p.build()


# ---------------------------------------------------------------- damage

def _mace(p, swatch, glow):
	p.seg((0, 0, 0), (0, 0, 0.75), 0.05, 0.05, WOOD, sides=6)
	p.blob((0.34, 0.34, 0.38), (0, 0, 0.88), swatch, segs=(8, 6), glow=glow)
	for k in range(6):
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.14, math.sin(a) * 0.14, 0.88), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.88), 0.06, 0.0, swatch, sides=4, glow=glow)


def strike():
	p = Prop("strike", 317)
	_mace(p, IRON, 0.0)
	for k in range(4):                                                             # a flash where it lands
		a = k * math.tau / 4 + 0.4
		p.seg((0, 0, 0.88), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.88 + 0.25), 0.05, 0.0, GOLD, sides=4, glow=1.6)
	return p.build()


def smite():
	p = Prop("smite", 319)
	_mace(p, GOLD, 1.4)
	for k in range(10):                                                            # sunburst
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.3, -0.05, 0.88 + math.sin(a) * 0.3), (math.cos(a) * 0.8, -0.05, 0.88 + math.sin(a) * 0.8), 0.05, 0.0, FLAME, sides=4, glow=2.0)
	return p.build()


def blast_of_frost():
	p = Prop("blast_of_frost", 321)
	for k, (x, y, h, lean) in enumerate([(0, 0, 1.0, 0), (0.28, 0.1, 0.7, 20), (-0.26, 0.05, 0.75, -22), (0.1, -0.25, 0.55, 12), (-0.1, 0.28, 0.6, -10)]):
		top = (x + math.sin(math.radians(lean)) * h, y, math.cos(math.radians(lean)) * h)
		p.seg((x, y, 0), top, 0.14, 0.0, WATER, sides=5, glow=1.2)
	return p.build()


def fire_bolt():
	p = Prop("fire_bolt", 323)
	p.blob((0.36, 0.36, 0.36), (0.45, 0, 0.5), FLAME, segs=(10, 8), glow=2.5)       # the head
	p.seg((0.45, 0, 0.5), (-0.7, 0, 0.35), 0.2, 0.0, EMBER, sides=8, glow=1.8)       # the tail
	p.seg((0.3, 0.05, 0.6), (-0.4, 0.1, 0.62), 0.08, 0.0, FLAME, sides=5, glow=2.0)
	return p.build()


def burning_embers():
	p = Prop("burning_embers", 325)
	for k in range(7):
		a = k * 2.4
		p.rock((0.3, 0.26, 0.2), (math.cos(a) * 0.3 * (k % 3), math.sin(a) * 0.3 * (k % 3), 0.1 + (0.12 if k == 0 else 0)), STONE_DARK, jitter=0.1)
	for k in range(5):
		a = k * 1.3
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.28 + k * 0.05), EMBER, segs=(6, 4), glow=3.0)
	for k in range(3):                                                             # little flames
		a = k * 2.1
		p.seg((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.2), (math.cos(a) * 0.25, math.sin(a) * 0.25, 0.7 + k * 0.1), 0.1, 0.0, FLAME, sides=5, glow=2.2)
	return p.build()


# ---------------------------------------------------------------- utility

def gate():
	p = Prop("gate", 327)
	_ring(p, 0.6, 0.65, 0.08, RUNE, glow=2.0, sides=22, tilt=math.pi / 2)
	for k in range(3):                                                             # the swirl inside
		_ring(p, 0.42 - k * 0.12, 0.65, 0.03, WATER, glow=1.5, sides=14, tilt=math.pi / 2)
	p.box((1.2, 0.5, 0.1), (0, 0, 0.0), STONE_LIGHT)                                # standing stone base
	return p.build()


def root():
	p = Prop("root", 329)
	p.seg((0, 0, 0), (0, 0, 0.02), 0.7, 0.7, LEAF, sides=16)                        # ground
	for k in range(5):
		a = k * math.tau / 5
		pts = [(math.cos(a + t * 0.6) * (0.5 - t * 0.12), math.sin(a + t * 0.6) * (0.5 - t * 0.12), t * 0.22) for t in range(5)]
		for i, (b, c) in enumerate(zip(pts, pts[1:])):
			p.seg(b, c, 0.09 - i * 0.015, 0.075 - i * 0.015, WOOD, sides=6)
	return p.build()


def minor_shielding():
	p = Prop("minor_shielding", 331)
	p.box((0.8, 0.12, 0.95), (0, 0, 0.5), RUNE, glow=1.2)                          # a shield of light
	p.seg((0, -0.07, 0.05), (0, -0.07, 0.03), 0.4, 0.0, RUNE, sides=4, glow=1.2)
	p.seg((0, 0, 0.0), (0, 0, -0.3), 0.4, 0.0, RUNE, sides=4, glow=1.2)            # pointed foot
	p.box((0.1, 0.05, 0.6), (0, -0.09, 0.5), GOLD, glow=1.0)
	p.box((0.45, 0.05, 0.1), (0, -0.09, 0.6), GOLD, glow=1.0)
	return p.build()


def courage():
	p = Prop("courage", 333)
	p.seg((0, 0, 0.1), (0, 0, 1.0), 0.07, 0.02, IRON, sides=4, glow=0.4)            # an upright blade
	p.box((0.5, 0.1, 0.08), (0, 0, 0.12), GOLD)
	p.seg((0, 0, 0.12), (0, 0, -0.2), 0.05, 0.05, WOOD, sides=6)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.15, -0.1, 0.6 + math.sin(a) * 0.15), (math.cos(a) * 0.55, -0.1, 0.6 + math.sin(a) * 0.55), 0.04, 0.0, FLAME, sides=4, glow=1.8)
	return p.build()


def hearthward():
	p = Prop("hearthward", 335)
	p.box((0.8, 0.6, 0.55), (0, 0, 0.28), STONE_LIGHT)                             # a little house
	p.poly([(-0.5, -0.35, 0.55), (0.5, -0.35, 0.55), (0.5, 0.35, 0.55), (-0.5, 0.35, 0.55), (0, -0.35, 0.95), (0, 0.35, 0.95)],
		   [(0, 1, 4), (3, 2, 5), (0, 4, 5, 3), (1, 2, 5, 4)], CLOTH_RED)
	p.box((0.22, 0.02, 0.22), (0, -0.31, 0.25), FLAME, glow=2.5)                   # the hearth's light
	_ring(p, 0.72, 0.4, 0.03, GOLD, glow=1.4, sides=20)
	return p.build()


def hearthbond():
	p = Prop("hearthbond", 337)
	_ring(p, 0.35, 0.45, 0.07, GOLD, glow=0.8, tilt=math.pi / 2)
	for k in range(18):                                                            # a second ring through the first
		a0, a1 = k * math.tau / 18, (k + 1) * math.tau / 18
		pt = lambda a: (0.4 + math.cos(a) * 0.35, math.sin(a) * 0.35, 0.45)
		p.seg(pt(a0), pt(a1), 0.07, 0.07, GOLD, sides=5, glow=0.8)
	p.blob((0.25, 0.25, 0.25), (0.2, 0, 0.45), EMBER, segs=(8, 6), glow=2.5)
	return p.build()


def blessing_of_the_elders():
	p = Prop("blessing_of_the_elders", 351)
	for s in (-1, 1):                               # a pair of tusks curving up, like the elephant gods'
		pts = [(s * 0.35, 0, 0.05), (s * 0.42, 0, 0.4), (s * 0.36, 0, 0.72), (s * 0.18, 0, 0.98)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.14 - i * 0.035, 0.1 - i * 0.03, GOLD, sides=8, glow=0.8)
	p.blob((0.34, 0.34, 0.34), (0, 0, 0.5), FLAME, segs=(10, 8), glow=2.5)   # the light between them
	_ring(p, 0.62, 0.45, 0.03, GOLD, glow=1.2, sides=20, tilt=math.pi / 2)
	return p.build()


# ---------------------------------------------------------------- levels 11-15

def _sword(p, glow=0.0, swatch=IRON):
	p.seg((0, 0, 0.25), (0, 0, 1.15), 0.07, 0.015, swatch, sides=4, glow=glow)       # blade
	p.box((0.46, 0.1, 0.08), (0, 0, 0.24), GOLD)                                     # guard
	p.seg((0, 0, 0.22), (0, 0, -0.1), 0.045, 0.045, WOOD, sides=6)                   # grip
	p.blob((0.1, 0.1, 0.1), (0, 0, -0.13), GOLD, segs=(6, 4))


def heroic_strike():
	p = Prop("heroic_strike", 361)
	_sword(p, glow=0.4)
	for k in range(7):                                                            # the swing's arc
		a = math.radians(200 + k * 20)
		p.seg((math.cos(a) * 0.7, -0.1, 0.65 + math.sin(a) * 0.7), (math.cos(a + 0.3) * 0.7, -0.1, 0.65 + math.sin(a + 0.3) * 0.7),
			  0.05 - k * 0.005, 0.04 - k * 0.005, FLAME, sides=4, glow=1.6)
	return p.build()


def rally():
	p = Prop("rally", 363)
	p.seg((0, 0, 0), (0, 0, 1.2), 0.04, 0.035, WOOD, sides=6)                       # a war banner
	p.box((0.62, 0.05, 0.62), (0.33, 0, 0.84), CLOTH_RED, grad=(0.1, 0.6))
	p.poly([(0.02, 0, 0.53), (0.64, 0, 0.53), (0.33, 0, 0.3)], [(0, 1, 2)], CLOTH_RED)
	p.box((0.18, 0.06, 0.18), (0.33, -0.03, 0.86), GOLD, glow=0.8)
	for k in range(3):
		_ring(p, 0.25 + k * 0.18, 0.2, 0.025, FLAME, glow=1.2, sides=12, tilt=math.pi / 2)
	return p.build()


def shield_wall():
	p = Prop("shield_wall", 365)
	for x, y in ((-0.28, 0.1), (0.28, 0.1), (0.0, -0.1)):                             # shields locked edge to edge
		p.seg((x, y, 0.5), (x, y - 0.1, 0.5), 0.34, 0.34, WOOD, sides=14)
		p.blob((0.14, 0.08, 0.14), (x, y - 0.13, 0.5), IRON, segs=(8, 5))
	p.box((1.3, 0.05, 1.2), (0, 0.2, 0.55), RUNE, glow=0.6, grad=(0.3, 0.6))            # the ward behind
	return p.build()


def healing():
	p = Prop("healing", 367)
	_cross(p, 1.1, GOLD, 2.2)
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.16, 0.16, 0.16), (math.cos(a) * 0.55, 0, 0.5 + math.sin(a) * 0.55), LEAF, segs=(6, 4), glow=1.8)
	return p.build()


def blessed_armor():
	p = Prop("blessed_armor", 369)
	p.blob((0.8, 0.45, 0.9), (0, 0, 0.45), GOLD, segs=(12, 8), glow=0.4)               # a breastplate
	p.box((0.08, 0.05, 0.7), (0, -0.23, 0.48), STONE_LIGHT, glow=0.6)
	for s in (-1, 1):
		p.blob((0.34, 0.3, 0.2), (s * 0.44, 0, 0.85), GOLD, segs=(8, 5))              # pauldrons
	_ring(p, 0.7, 0.45, 0.03, FLAME, glow=1.6, sides=20, tilt=math.pi / 2)
	return p.build()


def circle_of_renewal():
	p = Prop("circle_of_renewal", 371)
	_ring(p, 0.66, 0.12, 0.05, LEAF, glow=1.4, sides=22)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.66, math.sin(a) * 0.66, 0.12), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.9), 0.05, 0.0, LEAF, sides=4, glow=1.8)
	_cross(p, 0.5, GOLD, 2.0)
	return p.build()


def hallowed_strike():
	p = Prop("hallowed_strike", 373)
	p.seg((0, 0, 0), (0, 0, 0.8), 0.05, 0.05, WOOD, sides=6)                           # a hammer
	p.box((0.62, 0.3, 0.3), (0, 0, 0.9), GOLD, glow=1.2)
	for k in range(12):
		a = k * math.tau / 12
		p.seg((math.cos(a) * 0.35, -0.1, 0.9 + math.sin(a) * 0.35), (math.cos(a) * 0.8, -0.1, 0.9 + math.sin(a) * 0.8), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.2)
	return p.build()


def frost_lance():
	p = Prop("frost_lance", 375)
	p.seg((-0.7, 0, 0.1), (0.75, 0, 1.0), 0.13, 0.0, WATER, sides=6, glow=1.4)
	for k in range(4):
		t = 0.15 + k * 0.2
		x, z = -0.7 + t * 1.45, 0.1 + t * 0.9
		p.seg((x, 0, z), (x - 0.18, 0.1 * (k % 2 * 2 - 1), z + 0.2), 0.05, 0.0, WATER, sides=4, glow=1.0)
	return p.build()


def emberstorm():
	p = Prop("emberstorm", 377)
	for k in range(26):                                                           # a spiral of embers
		t = k / 26
		a = t * math.tau * 2.2
		r = 0.2 + t * 0.55
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * r, math.sin(a) * r, 0.1 + t * 0.9), EMBER if k % 3 else FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def greater_shielding():
	p = Prop("greater_shielding", 379)
	p.blob((1.2, 1.2, 1.1), (0, 0, 0.0), RUNE, segs=(14, 8), glow=1.0, grad=(0.2, 0.5))   # a dome of force
	p.box((0.12, 0.1, 0.8), (0, -0.62, 0.3), GOLD, glow=1.4)
	p.box((0.55, 0.1, 0.12), (0, -0.62, 0.45), GOLD, glow=1.4)
	return p.build()


def ice_comet():
	p = Prop("ice_comet", 381)
	p.blob((0.55, 0.55, 0.55), (0.45, 0, 0.35), WATER, segs=(12, 8), glow=1.8)
	for k, (dy, dz) in enumerate(((0, 0), (0.12, 0.1), (-0.1, -0.08))):
		p.seg((0.45, dy, 0.35 + dz), (-0.8, dy * 2, 1.05 + dz), 0.22 - k * 0.05, 0.0, CLOTH_WHITE, sides=6, glow=1.2)
	return p.build()


# ---------------------------------------------------------------- monsters' (shown as debuffs)

def thornback_venom():
	p = Prop("thornback_venom", 391)
	p.seg((0, 0, 1.0), (0, 0, 0.35), 0.2, 0.05, STONE_DARK, sides=6)                  # a fang
	for k in range(3):                                                            # dripping venom
		z = 0.25 - k * 0.3
		p.blob((0.16 - k * 0.02, 0.16 - k * 0.02, 0.24 - k * 0.03), (0.02 * k, 0, z), LEAF, segs=(8, 6), glow=1.8)
	_ring(p, 0.55, 0.55, 0.03, LEAF, glow=1.0, sides=16, tilt=math.pi / 2)
	return p.build()


def grave_chill():
	p = Prop("grave_chill", 393)
	p.blob((0.55, 0.5, 0.55), (0, 0, 0.55), BONE, segs=(10, 8))                     # a skull
	for s in (-1, 1):
		p.blob((0.14, 0.08, 0.14), (s * 0.13, -0.24, 0.58), WATER, segs=(6, 4), glow=2.0)
	for k in range(6):                                                            # frost around it
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.35, 0, 0.55 + math.sin(a) * 0.35), (math.cos(a) * 0.7, 0, 0.55 + math.sin(a) * 0.7), 0.06, 0.0, WATER, sides=4, glow=1.2)
	return p.build()


def spirit_bolt():
	p = Prop("spirit_bolt", 395)
	for k in range(3):
		t = k / 3
		p.blob((0.3 - k * 0.07, 0.3 - k * 0.07, 0.3 - k * 0.07), (0.4 - t * 0.9, 0, 0.55 + t * 0.2), LEAF, segs=(8, 6), glow=2.2 - k * 0.5)
	p.seg((0.4, 0, 0.55), (-0.7, 0, 0.85), 0.14, 0.0, CLOTH_WHITE, sides=6, glow=1.4)
	return p.build()


def leech_bite():
	p = Prop("leech_bite", 397)
	_ring(p, 0.45, 0.55, 0.12, CLOTH_RED, sides=14, tilt=math.pi / 2)            # the sucker
	for k in range(9):                                                            # its teeth
		a = k * math.tau / 9
		p.seg((math.cos(a) * 0.38, 0, 0.55 + math.sin(a) * 0.38), (math.cos(a) * 0.16, -0.05, 0.55 + math.sin(a) * 0.16), 0.06, 0.0, BONE, sides=4)
	for k in range(3):                                                            # blood
		p.blob((0.12, 0.12, 0.18), (0.1 * k - 0.1, 0, 0.05 - k * 0.12), CLOTH_RED, segs=(8, 6), glow=1.2)
	return p.build()


def marsh_bolt():
	p = Prop("marsh_bolt", 399)
	for k in range(4):
		t = k / 4
		p.blob((0.34 - k * 0.07,) * 3, (0.45 - t * 1.0, 0, 0.5 + t * 0.25), LEAF, segs=(8, 6), glow=1.6 - k * 0.3)
	for k in range(5):                                                            # stinking bubbles
		p.blob((0.1, 0.1, 0.1), (0.3 - k * 0.2, 0, 0.85 + (k % 2) * 0.12), WOOD_GRAY, segs=(6, 4))
	return p.build()


def drowning_cold():
	p = Prop("drowning_cold", 401)
	p.blob((0.5, 0.46, 0.5), (0, 0, 0.62), BONE, segs=(10, 8))                     # a skull
	for s_ in (-1, 1):
		p.blob((0.12, 0.08, 0.12), (s_ * 0.12, -0.22, 0.64), WATER, segs=(6, 4), glow=2.0)
	p.box((1.4, 1.4, 0.5), (0, 0, 0.25), WATER, glow=0.6)                          # the water rising over it
	for k in range(4):                                                            # bubbles
		p.blob((0.1, 0.1, 0.1), (0.3 - k * 0.15, -0.3, 0.95 + k * 0.12), WATER, segs=(6, 4), glow=1.0)
	return p.build()


# ---------------------------------------------------------------- actions

def action_attack():
	for x, yaw in ((-0.12, 35), (0.12, -35)):
		_import("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/sword_1handed.gltf", rot=(0, yaw, 0), loc=(x, 0, 0))


def action_ranged():
	_import("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/bow_withString.gltf", rot=(0, 30, 0))
	_import("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/arrow_bow.gltf", rot=(0, -60, 0), loc=(0.05, -0.05, 0.1))


def action_sit():
	p = Prop("action_sit", 341)
	p.seg((0, 0, 0.5), (0, 0, 0.58), 0.45, 0.45, WOOD, sides=12)                   # a stool
	for k in range(3):
		a = k * math.tau / 3
		p.seg((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.5), (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.0), 0.05, 0.05, WOOD_GRAY, sides=5)
	for k in range(3):                                                             # resting "z"s
		s = 0.12 + k * 0.05
		x, z = 0.35 + k * 0.2, 0.8 + k * 0.25
		p.box((s * 2, 0.04, 0.04), (x, 0, z + s), CLOTH_WHITE, glow=0.6)
		p.box((s * 2, 0.04, 0.04), (x, 0, z - s), CLOTH_WHITE, glow=0.6)
		p.box((s * 2.6, 0.04, 0.04), (x, 0, z), CLOTH_WHITE, rot=(0, 45, 0), glow=0.6)
	return p.build()


def action_consider():
	p = Prop("action_consider", 343)
	p.blob((1.0, 0.5, 0.6), (0, 0, 0.3), CLOTH_WHITE, segs=(14, 10))               # an eye
	p.blob((0.42, 0.2, 0.42), (0, -0.2, 0.3), RUNE, segs=(12, 8), glow=0.8)
	p.blob((0.2, 0.1, 0.2), (0, -0.28, 0.3), STONE_DARK, segs=(8, 6))
	return p.build()


def action_skills():
	p = Prop("action_skills", 345)
	for x in (-1, 1):                                                              # an open book
		p.box((0.55, 0.7, 0.05), (x * 0.3, 0, 0.1), CLOTH_WHITE, rot=(0, x * -12, 0))
		p.box((0.6, 0.75, 0.04), (x * 0.3, 0, 0.05), CLOTH_RED, rot=(0, x * -12, 0))
	for k in range(4):
		p.box((0.35, 0.03, 0.01), (-0.3, -0.2 + k * 0.12, 0.14), STONE_DARK, rot=(0, 12, 0))
	return p.build()


SPELLS = {f.__name__: f for f in [kick, taunt, bash, bind_wound, battle_cry, minor_healing, light_healing,
								  circle_of_mending, strike, smite, blast_of_frost, fire_bolt, burning_embers,
								  gate, root, minor_shielding, courage, hearthward, hearthbond, blessing_of_the_elders,
								  heroic_strike, rally, shield_wall, healing, blessed_armor, circle_of_renewal,
								  hallowed_strike, frost_lance, emberstorm, greater_shielding, ice_comet,
								  thornback_venom, grave_chill, spirit_bolt, leech_bite, marsh_bolt, drowning_cold]}
ACTIONS = {f.__name__: f for f in [action_attack, action_ranged, action_sit, action_consider, action_skills]}


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/icons", "--only": "", "--size": "128"}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) if opts["--only"] else None
	spells = json.load(open(os.path.join(icons.ROOT, "data/spells.json")))
	missing = [s for s in spells if s not in SPELLS]
	jobs = [("spell_" + k, f) for k, f in SPELLS.items()] + list(ACTIONS.items())
	for name, build in jobs:
		if only and name not in only and name.replace("spell_", "") not in only:
			continue
		props.reset_scene()
		props._materials.clear()
		build()
		icons.render_icon(os.path.abspath(os.path.join(opts["--out"], name + ".png")), int(opts["--size"]))
		print("icon %s" % name)
	if missing:
		print("NO ICON (add a builder): %s" % ", ".join(missing))


if __name__ == "__main__":
	main()
