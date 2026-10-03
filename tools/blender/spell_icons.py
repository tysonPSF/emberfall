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
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import icons  # noqa: E402
import props  # noqa: E402
from props import (BONE, CLOTH_RED, CLOTH_WHITE, EMBER, FLAME, GOLD, HIDE, IRON, LEAF, Prop, RUNE,  # noqa: E402
				   PINE, STONE_DARK, STONE_LIGHT, STONE_WARM, WATER, WOOD, WOOD_GRAY)


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


def homeward():
	p = Prop("homeward", 649)
	_ring(p, 0.62, 0.62, 0.07, GOLD, glow=2.0, sides=22, tilt=math.pi / 2)
	p.box((0.44, 0.3, 0.32), (0, 0, 0.5), STONE_WARM)                                  # a little house in the ring
	p.poly([(-0.3, -0.16, 0.66), (0.3, -0.16, 0.66), (0.3, 0.16, 0.66), (-0.3, 0.16, 0.66), (0, -0.16, 0.9), (0, 0.16, 0.9)],
		   [(0, 1, 4), (3, 2, 5), (0, 4, 5, 3), (1, 2, 5, 4)], CLOTH_RED)
	p.box((0.1, 0.02, 0.14), (0, -0.16, 0.45), FLAME, glow=2.5)                       # its lit door
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


def backstab():
	p = Prop("backstab", 403)
	p.seg((0.45, 0, 1.0), (-0.25, 0, 0.25), 0.07, 0.0, STONE_LIGHT, sides=4, glow=0.4)     # a dagger driving down
	p.box((0.36, 0.1, 0.08), (0.48, 0, 1.02), GOLD, rot=(0, 45, 0))                       # its guard
	p.seg((0.52, 0, 1.08), (0.72, 0, 1.28), 0.06, 0.05, WOOD, sides=6)                    # grip
	p.blob((0.9, 0.35, 0.7), (-0.2, 0.15, 0.2), CLOTH_RED, segs=(10, 6))                  # a back, struck
	return p.build()


def hide():
	p = Prop("hide", 405)
	p.blob((0.7, 0.6, 0.9), (0, 0, 0.55), STONE_DARK, segs=(10, 8), glow=0.0)             # a hooded shape
	p.blob((0.46, 0.3, 0.4), (0, -0.22, 0.7), IRON, segs=(8, 6))                          # the dark under the hood
	for s_ in (-1, 1):
		p.blob((0.08, 0.05, 0.05), (s_ * 0.1, -0.36, 0.72), LEAF, segs=(6, 4), glow=2.0)    # two eyes
	return p.build()


def sneak():
	p = Prop("sneak", 407)
	for k in range(3):                                                                    # soft footprints
		for s_ in (-1, 1):
			p.blob((0.2, 0.3, 0.05), (s_ * 0.2 + k * 0.05, -0.6 + k * 0.55 + (0.2 if s_ > 0 else 0), 0.05), STONE_LIGHT, segs=(8, 4), glow=0.3 - k * 0.1)
	return p.build()


def evade():
	p = Prop("evade", 409)
	for k in range(3):                                                                    # a figure fading out of a swirl
		p.blob((0.5 - k * 0.1, 0.3, 0.8 - k * 0.15), (-0.4 + k * 0.35, 0, 0.5), CLOTH_WHITE if k == 0 else STONE_LIGHT, segs=(8, 6), glow=0.6 - k * 0.2)
	_ring(p, 0.6, 0.5, 0.04, CLOTH_WHITE, glow=0.8, sides=16, tilt=math.pi / 2)
	return p.build()


def envenom_blade():
	p = Prop("envenom_blade", 411)
	p.seg((0, 0, 0.1), (0, 0, 1.1), 0.1, 0.0, STONE_LIGHT, sides=4)                       # a blade point up
	p.box((0.4, 0.1, 0.08), (0, 0, 0.1), GOLD)
	for k in range(4):                                                                    # green drips down it
		p.blob((0.1, 0.1, 0.16), (0.05 * (k % 2 * 2 - 1), 0, 0.9 - k * 0.2), LEAF, segs=(6, 4), glow=1.6)
	return p.build()


def rogue_venom():
	p = Prop("rogue_venom", 413)
	p.blob((0.55, 0.55, 0.7), (0, 0, 0.4), LEAF, segs=(10, 8), glow=1.2)                   # a vial of it
	p.seg((0, 0, 0.72), (0, 0, 0.95), 0.12, 0.12, STONE_LIGHT, sides=8)
	p.seg((0, 0, 0.95), (0, 0, 1.05), 0.14, 0.14, WOOD, sides=8)
	return p.build()


def rake():
	p = Prop("rake", 415)
	for k in range(3):                                                                    # three claw-slashes
		x = -0.3 + k * 0.3
		p.seg((x - 0.25, 0, 1.0), (x + 0.25, 0, 0.1), 0.06, 0.02, CLOTH_RED, sides=4, glow=1.2)
	return p.build()


# ---------------------------------------------------------------- levels 16-20

def provoke():
	p = Prop("provoke", 417)
	p.blob((0.5, 0.45, 0.55), (0, 0, 0.55), CLOTH_RED, segs=(10, 8), glow=0.8)            # a roaring face of red
	for k in range(3):
		_ring(p, 0.45 + k * 0.22, 0.55, 0.03, CLOTH_RED, glow=1.2 - k * 0.3, sides=16, tilt=math.pi / 2)
	return p.build()


def defensive_stance():
	p = Prop("defensive_stance", 419)
	p.blob((0.95, 0.25, 1.05), (0, 0, 0.55), IRON, segs=(12, 8))                         # a tower shield
	p.box((0.12, 0.3, 0.8), (0, -0.1, 0.55), STONE_LIGHT)
	p.box((0.6, 0.3, 0.12), (0, -0.1, 0.7), STONE_LIGHT)
	return p.build()


def cleave():
	p = Prop("cleave", 421)
	for k in range(5):                                                                    # a wide arc
		a0, a1 = math.radians(200 + k * 28), math.radians(228 + k * 28)
		p.seg((math.cos(a0) * 0.7, 0, 0.55 + math.sin(a0) * 0.7), (math.cos(a1) * 0.7, 0, 0.55 + math.sin(a1) * 0.7), 0.08, 0.08, GOLD, sides=4, glow=1.4)
	p.seg((0.2, 0, 0.1), (0.2, 0, 0.9), 0.05, 0.05, WOOD, sides=5)                        # an axe at the center
	p.blob((0.4, 0.08, 0.3), (0.38, 0, 0.8), IRON, segs=(8, 4))
	return p.build()


def greater_healing():
	p = Prop("greater_healing", 423)
	p.box((0.28, 0.1, 0.95), (0, 0, 0.55), GOLD, glow=1.8)                                 # a bright cross
	p.box((0.95, 0.1, 0.28), (0, 0, 0.6), GOLD, glow=1.8)
	_ring(p, 0.6, 0.58, 0.04, CLOTH_WHITE, glow=1.2, sides=18, tilt=math.pi / 2)
	return p.build()


def divine_aura():
	p = Prop("divine_aura", 425)
	p.blob((0.4, 0.3, 0.6), (0, 0, 0.5), CLOTH_WHITE, segs=(8, 6))                         # a figure
	p.blob((1.2, 1.2, 1.3), (0, 0, 0.55), GOLD, segs=(12, 8), glow=0.8)                    # in a golden shell
	return p.build()


def sunfire():
	p = Prop("sunfire", 427)
	p.blob((0.55, 0.55, 0.55), (0, 0, 0.6), GOLD, segs=(12, 8), glow=2.4)                  # a small sun
	for k in range(10):
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.38, 0, 0.6 + math.sin(a) * 0.38), (math.cos(a) * 0.75, 0, 0.6 + math.sin(a) * 0.75), 0.07, 0.0, EMBER, sides=4, glow=1.6)
	return p.build()


def lightning_bolt():
	p = Prop("lightning_bolt", 429)
	pts = [(0.3, 0, 1.1), (-0.05, 0, 0.7), (0.15, 0, 0.62), (-0.3, 0, 0.05)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.09, 0.07, CLOTH_WHITE, sides=5, glow=2.4)
	return p.build()


def frost_snare():
	p = Prop("frost_snare", 431)
	_ring(p, 0.5, 0.2, 0.08, WATER, glow=1.4, sides=16)                                   # a frost ring at the feet
	for k in range(6):                                                                    # ice spikes rising
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.45, math.sin(a) * 0.45, 0.1), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.75), 0.09, 0.0, WATER, sides=4, glow=1.0)
	return p.build()


def fireball():
	p = Prop("fireball", 433)
	p.blob((0.7, 0.7, 0.7), (0.15, 0, 0.7), EMBER, segs=(12, 8), glow=2.2)
	for k in range(4):                                                                    # its trail
		p.blob((0.35 - k * 0.07,) * 3, (-0.35 - k * 0.22, 0, 0.5 - k * 0.12), FLAME, segs=(8, 6), glow=1.6 - k * 0.3)
	return p.build()


def assassinate():
	p = Prop("assassinate", 435)
	p.seg((0.35, 0, 1.05), (-0.3, 0, 0.1), 0.08, 0.0, STONE_LIGHT, sides=4, glow=0.5)     # a blade plunging
	p.box((0.36, 0.1, 0.08), (0.38, 0, 1.08), CLOTH_RED, rot=(0, 45, 0))
	p.blob((0.1, 0.06, 0.1), (-0.05, 0, 0.35), CLOTH_RED, segs=(6, 4), glow=1.4)           # a drop of blood
	p.blob((0.08, 0.05, 0.08), (0.1, 0, 0.2), CLOTH_RED, segs=(6, 4), glow=1.4)
	return p.build()


def blind():
	p = Prop("blind", 437)
	p.blob((0.7, 0.3, 0.45), (0, 0, 0.6), CLOTH_WHITE, segs=(10, 6))                       # an eye...
	p.blob((0.25, 0.1, 0.25), (0, -0.14, 0.6), STONE_DARK, segs=(8, 6))
	for k in range(8):                                                                    # ...in a cloud of dust
		a = k * math.tau / 8
		p.blob((0.18, 0.18, 0.18), (math.cos(a) * 0.55, -0.1, 0.6 + math.sin(a) * 0.4), HIDE, segs=(6, 4))
	return p.build()


def deadly_poison():
	p = Prop("deadly_poison", 439)
	for s_ in (-1, 1):                                                                    # two blades crossed, dripping
		p.seg((s_ * 0.45, 0, 0.1), (-s_ * 0.3, 0, 1.0), 0.07, 0.0, STONE_LIGHT, sides=4)
	for k in range(5):
		p.blob((0.1, 0.1, 0.15), (0.2 * (k - 2) * 0.5, 0, 0.35 - (k % 2) * 0.1), LEAF, segs=(6, 4), glow=1.8)
	p.blob((0.3, 0.12, 0.3), (0, -0.1, 0.9), BONE, segs=(8, 5))                            # a small skull
	return p.build()


def deadly_venom():
	p = Prop("deadly_venom", 441)
	p.blob((0.6, 0.6, 0.75), (0, 0, 0.42), LEAF, segs=(10, 8), glow=1.6)
	p.seg((0, 0, 0.78), (0, 0, 1.0), 0.13, 0.13, STONE_LIGHT, sides=8)
	p.blob((0.3, 0.12, 0.3), (0, -0.28, 0.45), BONE, segs=(8, 5))
	return p.build()


def dawn_tusk_blessing():
	p = Prop("dawn_tusk_blessing", 443)
	p.blob((0.6, 0.5, 0.55), (0, 0, 0.4), STONE_LIGHT, segs=(10, 8))                      # an elephant's head
	for s_ in (-1, 1):
		p.blob((0.1, 0.35, 0.4), (s_ * 0.36, 0.05, 0.42), STONE_LIGHT, segs=(6, 5))        # ears
		p.seg((s_ * 0.12, -0.25, 0.25), (s_ * 0.2, -0.45, 0.15), 0.05, 0.02, BONE, sides=5)  # tusks
	p.seg((0, -0.3, 0.3), (0, -0.4, 0.85), 0.09, 0.06, STONE_LIGHT, sides=6)               # the trunk, raised
	p.seg((0, -0.42, 1.05), (0, -0.46, 1.05), 0.26, 0.26, GOLD, sides=14, glow=1.6)        # holding the sun
	return p.build()


# ---------------------------------------------------------------- The Bleach (monster spells)

def scorpion_venom():
	p = Prop("scorpion_venom", 445)
	pts = [(0.35, 0, 0.1), (0.45, 0, 0.55), (0.25, 0, 0.95), (-0.1, 0, 1.05)]            # a stinger's curve
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.14 - i * 0.03, 0.11 - i * 0.03, HIDE, sides=6)
	p.seg((-0.1, 0, 1.05), (-0.3, 0, 0.8), 0.05, 0.0, STONE_DARK, sides=5)
	p.blob((0.12, 0.12, 0.16), (-0.32, 0, 0.62), GOLD, segs=(6, 4), glow=1.8)             # a drop of venom
	return p.build()


def salt_gaze():
	p = Prop("salt_gaze", 447)
	p.blob((0.75, 0.3, 0.45), (0, 0, 0.6), CLOTH_WHITE, segs=(10, 6), glow=0.4)          # a pale reptile eye
	p.box((0.08, 0.1, 0.4), (0, -0.14, 0.6), STONE_DARK)
	for k in range(6):                                                                    # salt crystals round it
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.55, 0, 0.6 + math.sin(a) * 0.45), (math.cos(a) * 0.8, 0, 0.6 + math.sin(a) * 0.62), 0.07, 0.0, STONE_LIGHT, sides=4)
	return p.build()


# ---------------------------------------------------------------- levels 21-25

def shield_slam():
	p = Prop("shield_slam", 449)
	p.seg((0, 0.1, 0.55), (0, -0.05, 0.55), 0.45, 0.45, WOOD, sides=14)                   # a round shield
	p.blob((0.16, 0.1, 0.16), (0, -0.1, 0.55), IRON, segs=(8, 5))
	for k in range(5):                                                                    # stars of the stun
		a = k * math.tau / 5 + 0.3
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.62, -0.15, 1.02 + math.sin(a) * 0.12), GOLD, segs=(5, 4), glow=2.0)
	return p.build()


def battle_fury():
	p = Prop("battle_fury", 451)
	for s_ in (-1, 1):                                                                    # two blades in motion
		p.seg((s_ * 0.4, 0, 0.1), (-s_ * 0.2, 0, 1.0), 0.07, 0.0, IRON, sides=4)
	for k in range(4):                                                                    # speed lines of fire
		p.seg((-0.7, -0.1, 0.2 + k * 0.22), (-0.2, -0.1, 0.25 + k * 0.22), 0.04, 0.0, FLAME, sides=4, glow=1.8)
	p.blob((0.25, 0.2, 0.25), (0, -0.05, 0.55), CLOTH_RED, segs=(8, 5), glow=1.4)
	return p.build()


def whirlwind():
	p = Prop("whirlwind", 453)
	for k in range(4):                                                                    # a spiral of cuts
		_ring(p, 0.3 + k * 0.14, 0.2 + k * 0.22, 0.04, GOLD if k % 2 else CLOTH_WHITE, glow=1.4, sides=14)
	_sword(p, glow=0.4)
	return p.build()


def healing_tide():
	p = Prop("healing_tide", 455)
	for k in range(3):                                                                    # waves
		for j in range(6):
			x0, x1 = -0.75 + j * 0.25, -0.5 + j * 0.25
			z = 0.2 + k * 0.28
			p.seg((x0, 0, z + (0.08 if j % 2 else 0)), (x1, 0, z + (0 if j % 2 else 0.08)), 0.06, 0.06, WATER, sides=5, glow=1.0)
	_cross(p, 0.45, GOLD, 2.0)
	return p.build()


def word_of_awe():
	p = Prop("word_of_awe", 457)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.6), CLOTH_WHITE, segs=(8, 6), glow=2.6)               # a burst of holy light
	for k in range(12):
		a = k * math.tau / 12
		r1 = 0.8 if k % 2 else 0.55
		p.seg((math.cos(a) * 0.3, 0, 0.6 + math.sin(a) * 0.3), (math.cos(a) * r1, 0, 0.6 + math.sin(a) * r1), 0.06, 0.0, GOLD, sides=4, glow=1.8)
	return p.build()


def armor_of_faith():
	p = Prop("armor_of_faith", 459)
	p.blob((0.8, 0.45, 0.9), (0, 0, 0.45), STONE_LIGHT, segs=(12, 8), glow=0.3)           # a breastplate
	_cross(p, 0.45, GOLD, 1.8)
	for s_ in (-1, 1):
		p.blob((0.34, 0.3, 0.2), (s_ * 0.44, 0, 0.85), STONE_LIGHT, segs=(8, 5))
	_ring(p, 0.72, 0.45, 0.03, GOLD, glow=1.4, sides=20, tilt=math.pi / 2)
	return p.build()


def chain_lightning():
	p = Prop("chain_lightning", 461)
	for ox, oz, sc in ((0.0, 0.1, 1.0), (-0.5, 0.0, 0.6), (0.5, 0.05, 0.6)):               # a bolt forking to two more
		pts = [(ox + 0.25 * sc, 0, oz + 1.0 * sc), (ox - 0.05 * sc, 0, oz + 0.62 * sc), (ox + 0.12 * sc, 0, oz + 0.55 * sc), (ox - 0.25 * sc, 0, oz)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.07 * sc + 0.02, 0.05 * sc + 0.02, CLOTH_WHITE, sides=5, glow=2.4)
	return p.build()


def arcane_harvest():
	p = Prop("arcane_harvest", 463)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.45), RUNE, segs=(10, 8), glow=2.2)                   # mana drawn inward
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.85, 0, 0.45 + math.sin(a) * 0.6), (math.cos(a) * 0.4, 0, 0.45 + math.sin(a) * 0.3), 0.0, 0.06, RUNE, sides=4, glow=1.6)
	return p.build()


def meteor():
	p = Prop("meteor", 465)
	p.blob((0.55, 0.5, 0.5), (-0.2, 0, 0.35), STONE_DARK, segs=(10, 8), jitter=0.06)       # a burning stone
	p.blob((0.45, 0.45, 0.45), (-0.15, -0.05, 0.4), EMBER, segs=(10, 8), glow=1.2)
	for k in range(4):                                                                    # plunging from high up
		p.blob((0.3 - k * 0.05,) * 3, (0.2 + k * 0.2, 0, 0.7 + k * 0.2), FLAME, segs=(8, 6), glow=1.8 - k * 0.3)
	return p.build()


def crippling_poison():
	p = Prop("crippling_poison", 467)
	p.seg((0.35, 0, 0.1), (-0.3, 0, 1.0), 0.08, 0.0, STONE_LIGHT, sides=4)                 # a blade...
	for k in range(4):                                                                    # ...dripping pale green
		p.blob((0.09, 0.09, 0.13), (0.1 - k * 0.1, -0.05, 0.4 + k * 0.12), WATER, segs=(6, 4), glow=1.6)
	_ring(p, 0.35, 0.08, 0.05, WATER, glow=1.2, sides=12)                                 # binding the feet
	return p.build()


def crippling_venom():
	p = Prop("crippling_venom", 469)
	_ring(p, 0.5, 0.15, 0.08, WATER, glow=1.4, sides=16)
	p.blob((0.4, 0.4, 0.5), (0, 0, 0.55), WATER, segs=(10, 8), glow=1.2)
	return p.build()


def eviscerate():
	p = Prop("eviscerate", 471)
	for k in range(3):                                                                    # three raking slashes
		p.seg((-0.5 + k * 0.3, 0, 1.0), (-0.1 + k * 0.3, 0, 0.1), 0.06, 0.02, CLOTH_RED, sides=4, glow=1.6)
	p.seg((0.5, 0, 0.9), (0.2, 0, 0.3), 0.06, 0.0, STONE_LIGHT, sides=4)
	return p.build()


def vanish():
	p = Prop("vanish", 473)
	for k in range(6):                                                                    # a hood fading to smoke
		p.blob((0.45 - k * 0.05, 0.35 - k * 0.04, 0.3), (0, 0, 0.3 + k * 0.15), STONE_DARK, segs=(8, 6))
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * 0.6, 0, 0.7 + math.sin(a) * 0.35), RUNE, segs=(6, 4), glow=1.2)
	return p.build()


# ---------------------------------------------------------------- the Long Monsoon

def storm_bolt():
	p = Prop("storm_bolt", 475)
	p.blob((0.9, 0.5, 0.35), (0, 0, 1.0), STONE_DARK, segs=(10, 6))                        # a storm cloud
	pts = [(0.15, 0, 0.85), (-0.1, 0, 0.5), (0.1, 0, 0.45), (-0.2, 0, 0.0)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.08, 0.06, GOLD, sides=5, glow=2.4)
	return p.build()


def frog_poison():
	p = Prop("frog_poison", 477)
	p.blob((0.7, 0.55, 0.4), (0, 0, 0.35), GOLD, segs=(10, 6), glow=0.6)                   # a warning-yellow back
	for (x, y) in ((-0.2, -0.1), (0.15, 0.1), (0.05, -0.18)):
		p.blob((0.14, 0.14, 0.08), (x, y, 0.55), STONE_DARK, segs=(6, 4))
	for k in range(3):
		p.blob((0.08, 0.08, 0.12), (-0.3 + k * 0.3, -0.25, 0.05), LEAF, segs=(6, 4), glow=1.6)
	return p.build()


def death_roll():
	p = Prop("death_roll", 479)
	for k in range(3):                                                                    # a rolling swirl of water
		_ring(p, 0.3 + k * 0.18, 0.55, 0.05, WATER, glow=1.0, sides=16, tilt=math.pi / 2)
	for s_ in (-1, 1):                                                                    # jaws
		p.seg((0.0, 0, 0.55), (0.7, 0, 0.55 + s_ * 0.25), 0.1, 0.05, LEAF, sides=5)
	return p.build()


def tide_trunk_blessing():
	p = Prop("tide_trunk_blessing", 481)
	p.blob((0.6, 0.5, 0.55), (0, 0, 0.4), STONE_LIGHT, segs=(10, 8))                      # an elephant's head
	for s_ in (-1, 1):
		p.blob((0.1, 0.35, 0.4), (s_ * 0.36, 0.05, 0.42), STONE_LIGHT, segs=(6, 5))
		p.seg((s_ * 0.12, -0.25, 0.25), (s_ * 0.2, -0.45, 0.15), 0.05, 0.02, BONE, sides=5)
	p.seg((0, -0.3, 0.3), (0, -0.4, 0.85), 0.09, 0.06, STONE_LIGHT, sides=6)               # the trunk, raised...
	for k in range(5):                                                                    # ...spraying rain
		p.blob((0.08, 0.08, 0.12), (-0.3 + k * 0.15, -0.45, 1.05 - abs(k - 2) * 0.08), WATER, segs=(6, 4), glow=1.6)
	return p.build()


def fish():
	p = Prop("fish", 483)
	p.seg((-0.5, 0, 0.0), (0.5, 0, 1.1), 0.03, 0.015, WOOD, sides=5)                        # a rod
	p.seg((0.5, 0, 1.1), (0.55, 0, 0.3), 0.008, 0.008, CLOTH_WHITE, sides=3)                # the line
	p.blob((0.1, 0.1, 0.1), (0.55, 0, 0.3), CLOTH_RED, segs=(6, 4))                         # a float
	_ring(p, 0.3, 0.2, 0.025, WATER, glow=1.0, sides=16)                                  # ripples
	return p.build()


# ---------------------------------------------------------------- Magician and Necromancer

PURPLE = (3, 1)       # deep violet, for death magic
SICKLY = (6, 1)       # lime-to-teal, for disease
AMBER = (1, 3)        # warm orange-gold
CRIMSON = (4, 1)      # deep red-magenta


def _flame(p, x, z, s, glow=1.8):
	"""A licking flame: an ember core under a tapering yellow tongue."""
	p.blob((0.55 * s, 0.45 * s, 0.5 * s), (x, 0, z + 0.25 * s), EMBER, segs=(10, 6), glow=glow)
	p.seg((x, 0, z + 0.3 * s), (x + 0.05 * s, 0, z + 1.15 * s), 0.26 * s, 0.0, FLAME, sides=8, glow=glow + 0.4)
	for sx in (-1, 1):
		p.seg((x + sx * 0.15 * s, 0, z + 0.3 * s), (x + sx * 0.32 * s, 0, z + 0.85 * s), 0.13 * s, 0.0, FLAME, sides=6, glow=glow)


def _swirl(p, cx, cz, r0, r1, turns, swatch, glow, thick=0.06, steps=30):
	"""A flat spiral in the picture plane, from r0 out to r1."""
	pts = []
	for k in range(steps + 1):
		t = k / steps
		a = t * turns * math.tau
		r = r0 + (r1 - r0) * t
		pts.append((cx + math.cos(a) * r, 0, cz + math.sin(a) * r))
	for k, (a, b) in enumerate(zip(pts, pts[1:])):
		w = thick * (0.4 + 0.6 * k / steps)
		p.seg(a, b, w, w, swatch, sides=5, glow=glow)


def _elemental(p, swatch, s=1.0, glow=0.0):
	"""A small stocky elemental figure: head, body, fists."""
	p.blob((0.55 * s, 0.4 * s, 0.6 * s), (0, 0, 0.45 * s), swatch, segs=(10, 6), glow=glow)
	p.blob((0.32 * s, 0.3 * s, 0.3 * s), (0, 0, 0.95 * s), swatch, segs=(8, 6), glow=glow)
	for sx in (-1, 1):
		p.seg((sx * 0.25 * s, 0, 0.65 * s), (sx * 0.45 * s, 0, 0.3 * s), 0.1 * s, 0.1 * s, swatch, sides=6, glow=glow)
		p.blob((0.2 * s, 0.2 * s, 0.2 * s), (sx * 0.47 * s, 0, 0.25 * s), swatch, segs=(6, 5), glow=glow)
		p.seg((sx * 0.14 * s, 0, 0.2 * s), (sx * 0.18 * s, 0, 0.0), 0.1 * s, 0.1 * s, swatch, sides=6, glow=glow)


def _skull(p, x, z, s, swatch=BONE, eyes=None, eye_glow=2.0):
	p.blob((0.62 * s, 0.55 * s, 0.6 * s), (x, 0, z + 0.1 * s), swatch, segs=(12, 8))     # cranium
	p.blob((0.38 * s, 0.4 * s, 0.25 * s), (x, -0.02 * s, z - 0.22 * s), swatch, segs=(8, 5))  # jaw
	for sx in (-1, 1):
		p.blob((0.17 * s, 0.1 * s, 0.17 * s), (x + sx * 0.14 * s, -0.24 * s, z + 0.05 * s), eyes or STONE_DARK,
			   segs=(6, 4), glow=eye_glow if eyes else 0.0)
	p.blob((0.07 * s, 0.06 * s, 0.1 * s), (x, -0.27 * s, z - 0.1 * s), STONE_DARK, segs=(5, 4))  # nose
	for k in range(4):                                                                    # teeth
		p.box((0.05 * s, 0.03 * s, 0.07 * s), (x - 0.1 * s + k * 0.066 * s, -0.2 * s, z - 0.3 * s), STONE_DARK)


def _drop(p, x, z, s, swatch, glow):
	p.blob((0.4 * s, 0.4 * s, 0.4 * s), (x, 0, z), swatch, segs=(10, 6), glow=glow)
	p.seg((x, 0, z + 0.1 * s), (x, 0, z + 0.48 * s), 0.19 * s, 0.0, swatch, sides=10, glow=glow)


def call_of_earth():
	p = Prop("call_of_earth", 501)
	p.rock((1.0, 0.8, 1.0), (0, 0, 0.55), STONE_WARM, jitter=0.06)                          # a boulder fist, raised
	for k in range(4):                                                                    # knuckles
		p.rock((0.28, 0.28, 0.28), (-0.36 + k * 0.24, -0.34, 0.95), STONE_WARM, jitter=0.04)
	p.rock((0.3, 0.3, 0.4), (0.5, -0.2, 0.55), STONE_WARM, jitter=0.04)                     # thumb
	for k in range(3):                                                                    # amber cracks
		p.seg((-0.3 + k * 0.28, -0.42, 0.75), (-0.2 + k * 0.28, -0.42, 0.25), 0.045, 0.025, AMBER, sides=4, glow=2.6)
	_ring(p, 0.55, 0.0, 0.035, AMBER, glow=1.8, sides=18)                                 # summoning circle
	return p.build()


def call_of_water():
	p = Prop("call_of_water", 503)
	_swirl(p, 0, 0.7, 0.05, 0.6, 2.2, WATER, 1.4, thick=0.11)
	p.blob((0.2, 0.2, 0.2), (0, -0.05, 0.7), CLOTH_WHITE, segs=(8, 6), glow=1.6)
	_ring(p, 0.5, 0.0, 0.035, WATER, glow=1.8, sides=18)
	return p.build()


def call_of_fire():
	p = Prop("call_of_fire", 505)
	_flame(p, 0, 0.05, 1.3, glow=1.8)
	_ring(p, 0.55, 0.0, 0.035, FLAME, glow=1.8, sides=18)
	return p.build()


def call_of_air():
	p = Prop("call_of_air", 507)
	for k in range(6):                                                                    # a funnel of wind
		_ring(p, 0.1 + k * 0.1, 0.1 + k * 0.2, 0.04, CLOTH_WHITE if k % 2 else RUNE, glow=1.2, sides=16, tilt=0.35)
	_ring(p, 0.5, 0.0, 0.035, RUNE, glow=1.8, sides=18)
	return p.build()


def call_of_the_primal():
	p = Prop("call_of_the_primal", 509)
	for x, z, s in ((-0.35, 0.55, 0.5), (0.3, 0.55, 0.55), (0, 0.7, 0.6)):               # a storm cloud
		p.blob((s, s * 0.7, s * 0.8), (x, 0, z), STONE_DARK, segs=(10, 6))
	for k in range(5):                                                                    # a crown of lightning
		x = -0.4 + k * 0.2
		h = 1.25 if k % 2 == 0 else 1.1
		p.seg((x, -0.05, 0.9), (x, -0.05, h), 0.06, 0.0, GOLD, sides=4, glow=2.6)
	pts = [(0.1, -0.1, 0.35), (-0.1, -0.1, 0.1), (0.08, -0.1, 0.05), (-0.12, -0.1, -0.3)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.07, 0.05, GOLD, sides=5, glow=2.4)
	return p.build()


def renew_elements():
	p = Prop("renew_elements", 511)
	_elemental(p, STONE_WARM, s=0.9)
	for k in range(5):                                                                    # rising healing motes
		a = k * math.tau / 5 + 0.4
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.62, -0.1, 0.5 + math.sin(a) * 0.45), LEAF, segs=(6, 4), glow=2.0)
	p.box((0.08, 0.06, 0.3), (0, -0.25, 0.45), GOLD, glow=2.2)                             # a small gold cross on the chest
	p.box((0.3, 0.06, 0.08), (0, -0.25, 0.48), GOLD, glow=2.2)
	return p.build()


def greater_renewal():
	p = Prop("greater_renewal", 513)
	_elemental(p, STONE_WARM, s=1.1)
	_ring(p, 0.8, 0.55, 0.05, LEAF, glow=2.0, sides=22, tilt=math.pi / 2)                  # a halo of green
	for k in range(8):
		a = k * math.tau / 8
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * 0.8, -0.1, 0.55 + math.sin(a) * 0.8), GOLD, segs=(6, 4), glow=2.2)
	p.box((0.1, 0.06, 0.4), (0, -0.28, 0.5), GOLD, glow=2.4)
	p.box((0.4, 0.06, 0.1), (0, -0.28, 0.54), GOLD, glow=2.4)
	return p.build()


def burnout():
	p = Prop("burnout", 515)
	_flame(p, 0.2, 0.05, 0.85, glow=2.0)
	for k in range(4):                                                                    # speed lines
		p.seg((-0.85, 0, 0.15 + k * 0.22), (-0.3, 0, 0.18 + k * 0.22), 0.045, 0.0, FLAME if k % 2 else EMBER, sides=4, glow=1.6)
	return p.build()


def elemental_bond():
	p = Prop("elemental_bond", 517)
	_ring(p, 0.55, 0.55, 0.035, GOLD, glow=1.6, sides=20, tilt=math.pi / 2)               # linked in a ring
	for (a, sw) in ((math.pi / 2, FLAME), (0, WATER), (-math.pi / 2, STONE_WARM), (math.pi, CLOTH_WHITE)):
		p.blob((0.34, 0.34, 0.34), (math.cos(a) * 0.55, -0.05, 0.55 + math.sin(a) * 0.55), sw, segs=(10, 6),
			   glow=0.4 if sw == STONE_WARM else 1.4)
	return p.build()


def primal_fury():
	p = Prop("primal_fury", 519)
	p.blob((0.5, 0.45, 0.5), (0, 0, 0.5), EMBER, segs=(10, 8), glow=2.2)                   # an exploding flame
	for k in range(10):
		a = k * math.tau / 10 + 0.15
		r1 = 0.95 if k % 2 else 0.7
		p.seg((math.cos(a) * 0.2, 0, 0.5 + math.sin(a) * 0.2), (math.cos(a) * r1, 0, 0.5 + math.sin(a) * r1),
			  0.13, 0.0, FLAME if k % 2 else CLOTH_RED, sides=6, glow=2.2)
	return p.build()


def elemental_aegis():
	p = Prop("elemental_aegis", 521)
	p.blob((1.4, 1.2, 1.5), (0, 0, 0.1), STONE_WARM, segs=(14, 10), jitter=0.03)          # a stone dome
	p.blob((1.9, 1.7, 0.14), (0, 0, 0.1), STONE_DARK, segs=(16, 4))                        # on dark ground
	for z in (0.35, 0.6):                                                                 # its courses of stone
		rz = math.sqrt(max(0.0, 1 - ((z - 0.1) / 0.75) ** 2))
		_ring(p, 0.72 * rz, z, 0.03, STONE_DARK, sides=20)
	_ring(p, 0.74, 0.14, 0.05, AMBER, glow=2.0, sides=22)
	p.blob((0.22, 0.12, 0.22), (0, -0.6, 0.45), AMBER, segs=(8, 6), glow=2.4)
	return p.build()


def raise_bones():
	p = Prop("raise_bones", 523)
	p.blob((1.5, 1.0, 0.25), (0, 0, 0.0), STONE_DARK, segs=(14, 6))                       # the ground
	for k in range(5):                                                                    # dirt thrown up
		a = k * math.tau / 5
		p.rock((0.16, 0.16, 0.14), (math.cos(a) * 0.45, math.sin(a) * 0.3, 0.12), WOOD_GRAY)
	p.seg((0, 0, 0.05), (0.02, 0, 0.55), 0.07, 0.06, BONE, sides=6)                        # forearm bones
	p.seg((0.08, 0, 0.05), (0.1, 0, 0.55), 0.05, 0.05, BONE, sides=6)
	p.blob((0.3, 0.14, 0.2), (0.05, 0, 0.62), BONE, segs=(8, 5))                           # the palm
	for k in range(4):                                                                    # clawing fingers
		x = -0.1 + k * 0.1
		p.seg((x, 0, 0.7), (x - 0.02, 0, 0.9 - abs(k - 1.5) * 0.04), 0.03, 0.025, BONE, sides=5)
		p.seg((x - 0.02, 0, 0.9 - abs(k - 1.5) * 0.04), (x - 0.05, -0.06, 1.02 - abs(k - 1.5) * 0.05), 0.025, 0.0, BONE, sides=5)
	p.seg((0.16, 0, 0.58), (0.3, 0, 0.78), 0.035, 0.0, BONE, sides=5)                      # thumb
	for k in range(4):                                                                    # a sickly glow round the grave
		a = k * math.tau / 4 + 0.6
		p.blob((0.08, 0.08, 0.08), (math.cos(a) * 0.5, -0.1, 0.35 + math.sin(a) * 0.25), SICKLY, segs=(6, 4), glow=2.0)
	return p.build()


def raise_skeletal_knight():
	p = Prop("raise_skeletal_knight", 525)
	_skull(p, 0, 0.45, 1.0, eyes=SICKLY, eye_glow=2.6)
	p.blob((0.74, 0.66, 0.5), (0, 0.06, 0.74), IRON, segs=(12, 8))                         # an open helm over it
	p.seg((-0.37, -0.02, 0.62), (0.37, -0.02, 0.62), 0.05, 0.05, IRON, sides=6)             # its brow band
	p.box((0.07, 0.08, 0.3), (0, -0.3, 0.6), IRON)                                          # nasal guard
	p.seg((0, 0.1, 0.95), (0, 0.2, 1.25), 0.07, 0.02, CLOTH_RED, sides=5)                   # a crest
	for sx in (-1, 1):                                                                    # cheek guards, beside the face
		p.box((0.08, 0.35, 0.4), (sx * 0.36, 0.05, 0.4), IRON)
	return p.build()


def _bone(p, a, b, r, glow=0.0):
	a, b = list(a), list(b)
	p.seg(a, b, r, r, BONE, sides=8, glow=glow)
	for end, other in ((a, b), (b, a)):
		d = [(e - o) for e, o in zip(end, other)]
		n = math.sqrt(sum(c * c for c in d))
		perp = (-d[2] / n, 0, d[0] / n)
		for s_ in (-1, 1):
			p.blob((r * 2.4, r * 2.4, r * 2.4), (end[0] + perp[0] * r * s_, 0, end[2] + perp[2] * r * s_), BONE, segs=(8, 6), glow=glow)


def mend_bones():
	p = Prop("mend_bones", 527)
	_bone(p, (-0.6, 0, 0.1), (0.6, 0, 0.9), 0.09)
	for k in range(4):                                                                    # green stitches knitting it
		t = 0.3 + k * 0.13
		cx, cz = -0.6 + 1.2 * t, 0.1 + 0.8 * t
		p.seg((cx - 0.12, -0.12, cz + 0.16), (cx + 0.12, -0.12, cz - 0.16), 0.035, 0.035, LEAF, sides=4, glow=2.2)
	for k in range(5):
		a = k * math.tau / 5
		p.blob((0.08, 0.08, 0.08), (math.cos(a) * 0.7, -0.1, 0.5 + math.sin(a) * 0.55), LEAF, segs=(6, 4), glow=1.8)
	return p.build()


def dark_empowerment():
	p = Prop("dark_empowerment", 529)
	for k in range(8):                                                                    # a purple aura
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.5, 0.1, 0.5 + math.sin(a) * 0.5), (math.cos(a) * 0.85, 0.1, 0.5 + math.sin(a) * 0.85), 0.1, 0.0, PURPLE, sides=5, glow=2.0)
	_skull(p, 0, 0.5, 1.3, eyes=PURPLE, eye_glow=3.0)
	return p.build()


def _stream(p, x0, x1, z, amp, r, swatch, glow, n=12):
	pts = [(x0 + (x1 - x0) * k / n, 0, z + math.sin(k / n * math.tau * 1.2) * amp) for k in range(n + 1)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, r, r, swatch, sides=5, glow=glow)


def lifetap():
	p = Prop("lifetap", 531)
	_stream(p, -0.85, 0.35, 0.45, 0.12, 0.035, CLOTH_RED, 1.8)                             # a thin stream...
	_drop(p, 0.5, 0.35, 0.8, CLOTH_RED, 1.8)                                                # ...pulling a drop along
	for k in range(3):
		p.blob((0.08, 0.08, 0.08), (-0.6 + k * 0.35, -0.05, 0.45 + (0.12 if k % 2 else -0.08)), CLOTH_RED, segs=(6, 4), glow=2.0)
	return p.build()


def siphon_life():
	p = Prop("siphon_life", 533)
	for dz, amp in ((0.0, 0.18), (0.18, 0.12), (-0.18, 0.12)):                             # a braided torrent
		_stream(p, -0.9, 0.3, 0.5 + dz, amp, 0.06, CLOTH_RED, 2.0)
	_drop(p, 0.5, 0.35, 1.2, CLOTH_RED, 2.0)
	return p.build()


def soul_rend():
	p = Prop("soul_rend", 535)
	for sx, tilt in ((-1, 12), (1, -12)):                                                  # a ghostly soul torn in two
		cx = sx * 0.28
		p.blob((0.38, 0.3, 0.42), (cx, 0, 0.85), CLOTH_RED, rot=(0, tilt, 0), segs=(10, 6), glow=2.0)
		p.seg((cx, 0, 0.75), (cx + sx * 0.2, 0, 0.05), 0.2, 0.02, CLOTH_RED, sides=8, glow=1.8)
		for k in range(3):                                                                # the jagged tear
			z = 0.95 - k * 0.3
			p.seg((cx - sx * 0.14, -0.02, z), (cx - sx * 0.2, -0.02, z - 0.15), 0.05, 0.0, CRIMSON, sides=4, glow=1.4)
	for sx in (-1, 1):                                                                     # hollow eyes on the halves
		p.blob((0.08, 0.06, 0.1), (sx * 0.2, -0.16, 0.9), STONE_DARK, segs=(6, 4))
	return p.build()


def disease_cloud():
	p = Prop("disease_cloud", 537)
	for x, z, s in ((-0.4, 0.5, 0.55), (0.35, 0.5, 0.6), (0, 0.72, 0.7), (-0.1, 0.4, 0.6)):
		p.blob((s, s * 0.7, s * 0.8), (x, 0, z), SICKLY, segs=(10, 6), glow=0.8)
	rng = [(-0.6, 0.05), (-0.25, -0.05), (0.15, 0.1), (0.5, 0.0), (-0.45, 1.05), (0.4, 1.0), (0.0, 1.15), (0.7, 0.55), (-0.75, 0.6)]
	for x, z in rng:                                                                        # floating specks
		p.blob((0.09, 0.09, 0.09), (x, -0.3, z), LEAF if x > 0 else PINE, segs=(5, 4), glow=1.6)
	return p.build()


def venom_bolt():
	p = Prop("venom_bolt", 539)
	p.seg((-0.7, 0, 0.95), (0.35, 0, 0.35), 0.0, 0.2, LEAF, sides=8, glow=1.8)              # a streaking bolt
	p.blob((0.42, 0.42, 0.42), (0.4, 0, 0.32), LEAF, segs=(10, 8), glow=2.0)
	for k in range(3):                                                                    # dripping
		x = -0.25 + k * 0.25
		_drop(p, x, 0.3 - k * 0.12 + 0.1 * (k == 0), 0.35, SICKLY, 1.8)
	for k in range(3):                                                                    # its trail
		x = -0.8 + k * 0.15
		p.seg((x, 0, 1.1 - k * 0.1), (x + 0.3, 0, 0.95 - k * 0.12), 0.03, 0.0, SICKLY, sides=4, glow=1.4)
	return p.build()


def bond_of_death():
	p = Prop("bond_of_death", 541)
	_drop(p, -0.6, 0.25, 0.9, CLOTH_RED, 1.8)                                               # two drops...
	_drop(p, 0.6, 0.25, 0.9, CLOTH_RED, 1.8)
	for k, x in enumerate((-0.28, 0.0, 0.28)):                                            # ...chained together
		tilt = math.pi / 2 if k % 2 == 0 else 0.0
		for s_ in range(14):
			a0, a1 = s_ * math.tau / 14, (s_ + 1) * math.tau / 14
			pt = lambda a: (x + math.cos(a) * 0.17, math.sin(a) * 0.1 * math.cos(tilt), 0.35 + math.sin(a) * 0.1 * math.sin(tilt) + math.sin(a) * 0.1 * (1 - math.sin(tilt)))
			p.seg(pt(a0), pt(a1), 0.04, 0.04, IRON if k != 1 else PURPLE, sides=5, glow=0.0 if k != 1 else 1.8)
	return p.build()


def dread():
	p = Prop("dread", 543)
	p.blob((0.95, 0.5, 1.05), (0, 0.1, 0.5), PURPLE, segs=(14, 10), glow=0.4)              # a dark face...
	for sx in (-1, 1):                                                                     # ...wide staring eyes
		p.blob((0.28, 0.1, 0.34), (sx * 0.2, -0.16, 0.68), CLOTH_WHITE, segs=(10, 6), glow=1.2)
		p.blob((0.08, 0.06, 0.08), (sx * 0.2, -0.22, 0.66), STONE_DARK, segs=(6, 4))
		p.seg((sx * 0.08, -0.16, 0.95), (sx * 0.34, -0.14, 0.88), 0.03, 0.03, STONE_DARK, sides=4)   # brows up
	p.blob((0.24, 0.1, 0.34), (0, -0.16, 0.2), STONE_DARK, segs=(10, 6))                  # a screaming mouth
	return p.build()


def mass_dread():
	p = Prop("mass_dread", 545)
	for k in range(3):                                                                    # a shockwave rolling out
		_ring(p, 0.3 + k * 0.28, 0.1, 0.06 - k * 0.012, PURPLE, glow=2.2 - k * 0.5, sides=22)
	for k in range(3):                                                                    # tiny faces fleeing
		a = math.radians(210 + k * 60)
		x, y = math.cos(a) * 0.95, math.sin(a) * 0.6
		p.blob((0.2, 0.2, 0.22), (x, y, 0.25), PURPLE, segs=(8, 6), glow=0.6)
		for sx in (-1, 1):
			p.blob((0.06, 0.04, 0.07), (x + sx * 0.05, y - 0.1, 0.28), CLOTH_WHITE, segs=(5, 4), glow=1.4)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.15), PURPLE, segs=(8, 6), glow=2.6)
	return p.build()


def feign_death():
	p = Prop("feign_death", 547)
	p.box((0.5, 0.2, 0.8), (0.45, 0.25, 0.4), STONE_LIGHT)                                 # a tombstone
	p.seg((0.45, 0.35, 0.8), (0.45, 0.15, 0.8), 0.25, 0.25, STONE_LIGHT, sides=12)
	p.box((0.06, 0.03, 0.35), (0.45, 0.13, 0.55), STONE_DARK)                               # its cross
	p.box((0.22, 0.03, 0.06), (0.45, 0.13, 0.62), STONE_DARK)
	p.blob((1.1, 0.4, 0.3), (-0.3, -0.2, 0.15), CLOTH_RED, segs=(10, 6))                    # a figure lying flat
	p.blob((0.3, 0.3, 0.3), (-0.95, -0.2, 0.2), HIDE, segs=(8, 6))
	for sx in (-1, 1):                                                                     # limbs sprawled
		p.seg((-0.55, -0.2 + sx * 0.18, 0.15), (-0.45, -0.2 + sx * 0.42, 0.1), 0.06, 0.05, HIDE, sides=5)
		p.seg((0.2, -0.2 + sx * 0.1, 0.12), (0.4, -0.2 + sx * 0.2, 0.1), 0.08, 0.07, STONE_DARK, sides=5)
	for k in range(3):                                                                    # "z" wisps, not quite asleep
		p.blob((0.1, 0.1, 0.1), (-0.8 + k * 0.2, -0.3, 0.45 + k * 0.15), PURPLE, segs=(5, 4), glow=1.6)
	return p.build()


def clinging_darkness():
	p = Prop("clinging_darkness", 549)
	for sx in (-1, 1):                                                                     # a pair of feet
		p.seg((sx * 0.22, 0.05, 0.7), (sx * 0.22, 0.05, 0.25), 0.1, 0.12, WOOD, sides=8)       # boots
		p.blob((0.26, 0.5, 0.22), (sx * 0.22, -0.12, 0.15), WOOD, segs=(8, 5))
	for k in range(6):                                                                    # tendrils coiling up round them
		x = -0.6 + k * 0.24
		pts = [(x, -0.25, 0.0), (x + 0.12, -0.35, 0.25), (x - 0.05, -0.38, 0.5), (x + 0.1, -0.35, 0.8 - abs(k - 2.5) * 0.12)]
		for j, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.07 - j * 0.02, 0.05 - j * 0.02, PURPLE, sides=5, glow=1.2)
	p.blob((1.4, 0.9, 0.12), (0, 0, 0.0), STONE_DARK, segs=(12, 6))                        # a pool of shadow
	return p.build()


def elemental_flame():
	p = Prop("elemental_flame", 551)
	_flame(p, 0, 0, 0.8, glow=2.0)
	for k in range(3):                                                                    # licking sideways
		p.seg((0.1, 0, 0.35 + k * 0.2), (0.7, 0, 0.55 + k * 0.25), 0.1, 0.0, FLAME, sides=6, glow=2.0)
	return p.build()


def gust_of_wind():
	p = Prop("gust_of_wind", 553)
	for k, z in enumerate((0.25, 0.55, 0.85)):                                             # three gust lines, curling
		x0 = -0.8 + k * 0.15
		p.seg((x0, 0, z), (0.3, 0, z), 0.04, 0.04, CLOTH_WHITE if k != 1 else RUNE, sides=5, glow=1.2)
		_swirl(p, 0.3, z + 0.13, 0.13, 0.02, 0.8, CLOTH_WHITE if k != 1 else RUNE, 1.2, thick=0.05, steps=10)
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


def action_hail():
	p = Prop("action_hail", 347)
	p.blob((0.5, 0.3, 0.55), (0, 0, 0.45), HIDE, segs=(10, 8))                      # an open hand raised
	for k in range(4):
		x = -0.22 + k * 0.15
		p.seg((x, 0, 0.7), (x * 1.1, 0, 1.05 - abs(k - 1.5) * 0.06), 0.06, 0.05, HIDE, sides=6)
	p.seg((0.28, 0, 0.45), (0.5, 0, 0.7), 0.06, 0.05, HIDE, sides=6)                  # thumb
	for k in range(3):                                                               # a wave
		_ring(p, 0.55 + k * 0.14, 0.6, 0.02, GOLD, glow=1.0, sides=6, tilt=math.pi / 2)
	return p.build()


def action_friends():
	p = Prop("action_friends", 357)
	for x, c in ((-0.28, HIDE), (0.28, CLOTH_WHITE)):                               # two figures, side by side
		p.blob((0.3, 0.28, 0.3), (x, 0, 0.82), c, segs=(10, 8))
		p.blob((0.4, 0.3, 0.5), (x, 0, 0.36), c, segs=(10, 8))
	p.blob((0.22, 0.08, 0.2), (0, -0.32, 0.5), CLOTH_RED, segs=(8, 6), glow=0.8)  # a heart between them
	return p.build()


def action_journal():
	p = Prop("action_journal", 361)
	p.box((0.7, 0.05, 0.85), (0, 0, 0.5), CLOTH_WHITE, rot=(0, 0, 8))              # a quest scroll, unrolled
	for z in (0.08, 0.92):                                                          # its two rolled ends
		p.seg((-0.42, 0, z), (0.42, 0, z), 0.07, 0.07, HIDE, sides=8)
	for k in range(4):                                                              # lines of writing
		p.box((0.42 - (k % 2) * 0.12, 0.02, 0.03), (-0.04, -0.04, 0.72 - k * 0.14), STONE_DARK)
	p.blob((0.12, 0.05, 0.12), (0.22, -0.05, 0.22), CLOTH_RED, segs=(8, 6), glow=0.4)  # a wax seal
	return p.build()


def velassas_company():
	p = Prop("velassas_company", 2401)
	p.blob((0.9, 0.7, 0.8), (0, 0, 0.5), STONE_LIGHT, segs=(14, 10))                  # Velassa's gray head
	for s in (1, -1):
		p.seg((0.3 * s, 0.05, 0.75), (0.42 * s, 0.05, 1.12), 0.17, 0.0, STONE_LIGHT, sides=4)   # ears
		p.seg((0.3 * s, -0.02, 0.78), (0.4 * s, -0.02, 1.02), 0.09, 0.0, CLOTH_RED, sides=4)
		p.blob((0.2, 0.08, 0.22), (0.2 * s, -0.33, 0.56), PETAL_PURPLE, segs=(8, 6), glow=1.2)   # violet eyes
		p.blob((0.05, 0.04, 0.16), (0.2 * s, -0.37, 0.56), STONE_DARK, segs=(6, 4))
	p.blob((0.38, 0.2, 0.22), (0, -0.33, 0.3), CLOTH_WHITE, segs=(8, 6))               # her white muzzle
	p.blob((0.08, 0.05, 0.06), (0, -0.43, 0.36), CLOTH_RED, segs=(6, 4))
	p.blob((0.22, 0.12, 0.22), (0, -0.28, 0.02), PETAL_PURPLE, segs=(8, 6), glow=1.5)   # her collar charm
	return p.build()


def action_delete():
	p = Prop("action_delete", 367)
	p.seg((0, 0, 0.02), (0, 0, 0.82), 0.3, 0.37, STONE_LIGHT, sides=12)            # a tin rubbish bin, wider at the top
	for k in range(5):                                                              # its ribs
		a = math.radians(-60 + 30 * k)
		p.box((0.05, 0.05, 0.7), (0.34 * math.sin(a), -0.34 * math.cos(a), 0.43), STONE_DARK, rot=(0, 0, math.degrees(a)))
	p.seg((0, 0, 0.84), (0, 0, 0.92), 0.42, 0.42, STONE_DARK, sides=12)            # the lid, lifted a little
	p.seg((-0.12, 0, 0.98), (0.12, 0, 0.98), 0.04, 0.04, STONE_DARK, sides=6)      # its handle
	for x in (-0.12, 0.12):
		p.seg((x, 0, 0.92), (x, 0, 0.98), 0.03, 0.03, STONE_DARK, sides=6)
	return p.build()


def action_guild():
	p = Prop("action_guild", 359)
	p.seg((-0.35, 0, 0.0), (-0.35, 0, 1.1), 0.05, 0.05, WOOD, sides=6)             # a banner on its pole
	p.box((0.6, 0.04, 0.7), (0.0, 0, 0.7), CLOTH_RED)
	p.blob((0.18, 0.05, 0.18), (0.0, -0.05, 0.72), GOLD, segs=(8, 6), glow=0.9)     # its device
	p.seg((-0.35, 0, 1.1), (-0.35, 0, 1.18), 0.08, 0.0, GOLD, sides=6)
	return p.build()


def action_loot():
	p = Prop("action_loot", 349)
	p.blob((0.8, 0.6, 0.6), (0, 0, 0.3), HIDE, segs=(10, 8))                         # a sack...
	p.seg((0, 0, 0.62), (0, 0, 0.78), 0.12, 0.18, HIDE, sides=8)
	for k in range(4):                                                               # ...spilling coins
		p.seg((-0.5 + k * 0.28, -0.3, 0.05), (-0.5 + k * 0.28, -0.3, 0.1), 0.13, 0.13, GOLD, sides=10, glow=0.6)
	return p.build()


def _pet_head(p):
	p.blob((0.5, 0.42, 0.5), (0, 0, 0.55), STONE_LIGHT, segs=(10, 8))                # a small elemental's head
	for s_ in (-1, 1):
		p.blob((0.1, 0.06, 0.1), (s_ * 0.12, -0.2, 0.6), GOLD, segs=(6, 4), glow=1.6)


def action_pet_attack():
	p = Prop("action_pet_attack", 351)
	_pet_head(p)
	p.seg((0.3, 0, 0.1), (0.9, 0, 0.95), 0.06, 0.0, IRON, sides=4)                    # a blade behind it
	return p.build()


def action_pet_back():
	p = Prop("action_pet_back", 353)
	_pet_head(p)
	for k in range(3):                                                               # arrows pointing back
		p.seg((0.9 - k * 0.05, 0, 0.2 + k * 0.3), (0.45, 0, 0.2 + k * 0.3), 0.04, 0.04, CLOTH_WHITE, sides=4, glow=0.8)
		p.seg((0.45, 0, 0.2 + k * 0.3), (0.58, 0, 0.3 + k * 0.3), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=0.8)
	return p.build()


def action_pet_follow():
	p = Prop("action_pet_follow", 355)
	_pet_head(p)
	for k in range(3):                                                               # footprints
		p.blob((0.12, 0.2, 0.03), (-0.5 + k * 0.25, -0.1, 0.02 + (k % 2) * 0.12), LEAF, segs=(6, 4), glow=0.8)
	return p.build()


def action_pet_guard():
	p = Prop("action_pet_guard", 357)
	_pet_head(p)
	p.seg((0.55, 0.1, 0.5), (0.55, -0.05, 0.5), 0.3, 0.3, WOOD, sides=12)             # a shield beside it
	p.blob((0.12, 0.08, 0.12), (0.55, -0.08, 0.5), IRON, segs=(8, 5))
	return p.build()


def action_pet_sit():
	p = Prop("action_pet_sit", 359)
	_pet_head(p)
	for k in range(2):                                                               # resting z's
		x, z = 0.5 + k * 0.2, 0.8 + k * 0.25
		p.box((0.24, 0.04, 0.04), (x, 0, z + 0.1), CLOTH_WHITE, glow=0.6)
		p.box((0.24, 0.04, 0.04), (x, 0, z - 0.1), CLOTH_WHITE, glow=0.6)
		p.box((0.3, 0.04, 0.04), (x, 0, z), CLOTH_WHITE, rot=(0, 45, 0), glow=0.6)
	return p.build()


# ---------------------------------------------------------------- shaman

def _paw(p, x, z, s, swatch, glow):
	"""A paw print standing upright to face the camera: a pad and four toes."""
	p.blob((0.42 * s, 0.1, 0.36 * s), (x, 0, z), swatch, segs=(10, 6), glow=glow)
	for k, (dx, dz) in enumerate(((-0.27, 0.3), (-0.1, 0.42), (0.1, 0.42), (0.27, 0.3))):
		p.blob((0.15 * s, 0.1, 0.18 * s), (x + dx * s, 0, z + dz * s), swatch, segs=(8, 5), glow=glow)


def _swarm(p, n, spread, swatch, glow, seed):
	import random
	rnd = random.Random(seed)
	for k in range(n):   # insects: a body and two pale wings each
		x, z = rnd.uniform(-spread, spread), 0.5 + rnd.uniform(-spread, spread) * 0.8
		p.blob((0.2, 0.14, 0.13), (x, -0.1, z), swatch, segs=(6, 4), glow=glow)
		for sx in (-1, 1):
			p.blob((0.17, 0.03, 0.1), (x + sx * 0.14, -0.14, z + 0.09), CLOTH_WHITE, rot=(0, sx * 30, 0), segs=(5, 3), glow=0.6)


def _snowflake(p, cx, cz, r, glow):
	for k in range(6):
		a = k * math.tau / 6
		tip = (cx + math.cos(a) * r, 0, cz + math.sin(a) * r)
		p.seg((cx, 0, cz), tip, 0.05, 0.02, WATER, sides=5, glow=glow)
		mid = (cx + math.cos(a) * r * 0.6, 0, cz + math.sin(a) * r * 0.6)
		for b in (-0.6, 0.6):
			p.seg(mid, (mid[0] + math.cos(a + b) * r * 0.25, 0, mid[2] + math.sin(a + b) * r * 0.25), 0.03, 0.01, WATER, sides=4, glow=glow)


def _moon(p, cx, cz, r, glow):
	for k in range(9):   # a crescent: blobs along an arc, thinning at the horns
		a = math.radians(110 + k * 17.5)
		w = 0.2 * r * math.sin(math.radians(k * 180 / 8)) + 0.05
		p.blob((w * 2, 0.1, w * 2), (cx + math.cos(a) * r, 0, cz + math.sin(a) * r), GOLD, segs=(8, 5), glow=glow)


def _zs(p, x, z, s, glow=0.8):
	p.box((0.24 * s, 0.04, 0.04 * s), (x, 0, z + 0.1 * s), CLOTH_WHITE, glow=glow)
	p.box((0.24 * s, 0.04, 0.04 * s), (x, 0, z - 0.1 * s), CLOTH_WHITE, glow=glow)
	p.box((0.3 * s, 0.04, 0.04 * s), (x, 0, z), CLOTH_WHITE, rot=(0, 45, 0), glow=glow)


def frost_rift():
	p = Prop("frost_rift", 601)
	for k in range(5):   # a jagged crack in the ground
		x0, x1 = -0.8 + k * 0.32, -0.48 + k * 0.32
		p.seg((x0, 0, 0.1 + 0.06 * (k % 2)), (x1, 0, 0.1 + 0.06 * ((k + 1) % 2)), 0.06, 0.06, STONE_DARK, sides=4)
	for x, h, lean in ((-0.45, 0.55, -15), (-0.1, 0.9, 5), (0.25, 0.7, 12), (0.55, 0.45, 25)):   # ice shards bursting up
		top = (x + math.sin(math.radians(lean)) * h, 0, 0.1 + math.cos(math.radians(lean)) * h)
		p.seg((x, 0, 0.1), top, 0.13, 0.0, WATER, sides=5, glow=1.4)
	return p.build()


def sicken():
	p = Prop("sicken", 603)
	_swirl(p, 0, 0.55, 0.1, 0.55, 1.6, SICKLY, 1.4, thick=0.08)
	for x, z in ((-0.55, 0.1), (0.1, 0.02), (0.6, 0.15)):
		_drop(p, x, z, 0.35, SICKLY, 1.6)
	return p.build()


def strengthen():
	p = Prop("strengthen", 605)
	p.blob((0.6, 0.45, 0.55), (0, 0, 0.5), HIDE, segs=(10, 8))   # a clenched fist
	for k in range(4):
		p.blob((0.17, 0.2, 0.17), (-0.22 + k * 0.15, -0.2, 0.68), HIDE, segs=(6, 5))
	p.seg((0, 0, 0.25), (0, 0, -0.2), 0.2, 0.22, HIDE, sides=8)
	_ring(p, 0.72, 0.5, 0.05, FLAME, glow=1.8, sides=16)
	return p.build()


def inner_fire():
	p = Prop("inner_fire", 607)
	_flame(p, 0, 0.3, 0.9, glow=2.2)
	_ring(p, 0.62, 0.55, 0.06, GOLD, glow=1.2, sides=18)
	return p.build()


def drowsy():
	p = Prop("drowsy", 609)
	p.blob((1.2, 0.35, 0.25), (0, 0, 0.12), SICKLY, segs=(12, 6), glow=0.4)   # a slow snail's body
	p.seg((0.5, 0, 0.15), (0.72, 0, 0.45), 0.1, 0.08, SICKLY, sides=6, glow=0.4)   # its head, up
	for dx in (0.0, 0.1):   # drooping eye stalks
		p.seg((0.68 + dx, 0, 0.45), (0.8 + dx, -0.05, 0.62), 0.03, 0.02, SICKLY, sides=4, glow=0.4)
	_swirl(p, -0.1, 0.55, 0.05, 0.42, 2.0, WOOD, 0.3, thick=0.1)   # its shell
	p.blob((0.85, 0.3, 0.85), (-0.1, 0.08, 0.55), AMBER, segs=(12, 8))
	_zs(p, 0.45, 1.05, 0.7)
	return p.build()


def spirit_of_bear():
	p = Prop("spirit_of_bear", 611)
	_paw(p, 0, 0.35, 1.35, WOOD, 0.6)
	for k in range(4):   # claws
		dx = (-0.36, -0.13, 0.13, 0.36)[k]
		p.seg((dx, -0.05, 0.95), (dx * 1.1, -0.05, 1.15), 0.05, 0.0, BONE, sides=4)
	return p.build()


def spirit_mend():
	p = Prop("spirit_mend", 613)
	p.blob((0.55, 0.12, 0.85), (0, 0, 0.5), LEAF, rot=(0, 25, 0), segs=(10, 6), glow=1.2)   # a leaf
	p.seg((0.22, -0.02, 0.05), (-0.2, -0.02, 0.9), 0.025, 0.01, PINE, sides=4)
	for k in range(4):   # slow motes rising round it
		a = k * math.tau / 4
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.62, -0.1, 0.5 + math.sin(a) * 0.5), LEAF, segs=(6, 4), glow=2.0)
	return p.build()


def tainted_breath():
	p = Prop("tainted_breath", 615)
	_stream(p, -0.8, 0.7, 0.5, 0.18, 0.12, SICKLY, 1.2)
	for x, z, r in ((0.45, 0.62, 0.3), (0.7, 0.45, 0.25), (0.25, 0.42, 0.22)):
		p.blob((r, r * 0.8, r), (x, 0, z), LEAF, segs=(8, 6), glow=1.0)
	return p.build()


def feet_like_cat():
	p = Prop("feet_like_cat", 617)
	_paw(p, -0.35, 0.25, 0.8, GOLD, 1.0)
	_paw(p, 0.35, 0.65, 0.8, GOLD, 1.0)
	return p.build()


def frost_strike():
	p = Prop("frost_strike", 619)
	p.seg((-0.7, 0, 1.0), (0.45, 0, 0.2), 0.12, 0.12, WATER, sides=6, glow=1.4)   # an ice spear
	p.seg((0.45, 0, 0.2), (0.7, 0, 0.02), 0.2, 0.0, WATER, sides=6, glow=2.0)
	for k in range(3):
		p.seg((-0.7 + k * 0.2, 0.1, 1.0 - k * 0.14), (-0.95 + k * 0.2, 0.1, 1.12 - k * 0.14), 0.03, 0.0, CLOTH_WHITE, sides=4, glow=0.8)
	return p.build()


def walking_sleep():
	p = Prop("walking_sleep", 621)
	_moon(p, -0.1, 0.5, 0.5, 1.4)
	_zs(p, 0.5, 0.85, 0.8)
	_zs(p, 0.7, 0.45, 0.55)
	return p.build()


def spirit_healing():
	p = Prop("spirit_healing", 623)
	_cross(p, 0.9, LEAF, 1.8)
	_swirl(p, 0, 0.5, 0.55, 0.75, 1.0, CLOTH_WHITE, 0.8, thick=0.04)
	return p.build()


def quickness():
	p = Prop("quickness", 625)
	for k in range(3):   # chevrons racing forward
		x = -0.55 + k * 0.4
		p.seg((x - 0.2, 0, 0.85), (x + 0.15, 0, 0.5), 0.07, 0.07, GOLD, sides=5, glow=1.4 + k * 0.3)
		p.seg((x + 0.15, 0, 0.5), (x - 0.2, 0, 0.15), 0.07, 0.07, GOLD, sides=5, glow=1.4 + k * 0.3)
	return p.build()


def talisman_of_the_totem():
	p = Prop("talisman_of_the_totem", 627)
	for k, sw in enumerate((WOOD, CLOTH_RED, WOOD)):   # a little totem pole of three faces
		z = 0.2 + k * 0.36
		p.box((0.46, 0.4, 0.32), (0, 0, z), sw)
		for sx in (-1, 1):
			p.blob((0.08, 0.05, 0.06), (sx * 0.1, -0.21, z + 0.05), CLOTH_WHITE if k != 1 else GOLD, segs=(6, 4), glow=0.8)
	for sx in (-1, 1):   # its wings at the top
		p.seg((0, 0, 0.9), (sx * 0.7, 0, 1.05), 0.12, 0.03, STONE_WARM, sides=4)
	return p.build()


def envenomed_breath():
	p = Prop("envenomed_breath", 629)
	for x, z, r in ((-0.3, 0.5, 0.5), (0.25, 0.45, 0.55), (0, 0.75, 0.5)):
		p.blob((r, r * 0.7, r * 0.8), (x, 0, z), PINE, segs=(10, 6), glow=0.8)
	p.seg((0.05, -0.3, 0.55), (0.12, -0.35, 0.05), 0.12, 0.0, BONE, sides=5)   # a dripping fang
	_drop(p, 0.14, -0.15, 0.3, SICKLY, 2.0)
	return p.build()


def spirit_regrowth():
	p = Prop("spirit_regrowth", 631)
	p.seg((0, 0, 0.0), (0.05, 0, 0.9), 0.05, 0.03, PINE, sides=5, glow=0.6)   # a sprout
	for k, (z, side) in enumerate(((0.3, -1), (0.52, 1), (0.74, -1))):
		p.blob((0.4, 0.08, 0.2), (side * 0.2, 0, z), LEAF, rot=(0, side * -25, 0), segs=(8, 4), glow=1.4)
	_ring(p, 0.7, 0.45, 0.04, LEAF, glow=1.6, sides=18)
	return p.build()


def tagars_insects():
	p = Prop("tagars_insects", 633)
	_swarm(p, 7, 0.6, STONE_DARK, 0.4, 7)
	return p.build()


def winters_roar():
	p = Prop("winters_roar", 635)
	_snowflake(p, 0, 0.55, 0.62, 1.6)
	return p.build()


def spirit_of_the_wolf():
	p = Prop("spirit_of_the_wolf", 637)
	p.blob((0.62, 0.55, 0.58), (0, 0, 0.5), WATER, segs=(10, 8), glow=0.9)   # a spirit wolf's head
	p.seg((0, -0.25, 0.42), (0, -0.62, 0.32), 0.2, 0.1, WATER, sides=8, glow=0.9)   # muzzle
	p.blob((0.12, 0.1, 0.1), (0, -0.66, 0.36), STONE_DARK, segs=(6, 4))
	for sx in (-1, 1):
		p.seg((sx * 0.2, 0, 0.72), (sx * 0.3, 0.05, 1.08), 0.12, 0.0, WATER, sides=4, glow=0.9)   # ears
		p.blob((0.09, 0.05, 0.07), (sx * 0.16, -0.26, 0.6), CLOTH_WHITE, segs=(6, 4), glow=2.5)
	return p.build()


def chant_of_the_pack():
	p = Prop("chant_of_the_pack", 639)
	for x, z in ((-0.5, 0.2), (0.0, 0.62), (0.5, 0.2)):
		_paw(p, x, z, 0.6, WOOD_GRAY, 0.9)
	return p.build()


def winters_grasp():
	p = Prop("winters_grasp", 641)
	p.blob((0.55, 0.35, 0.35), (0, 0, 0.2), WATER, segs=(10, 6), glow=1.0)   # an icy palm
	for k in range(5):   # clawed fingers curling up
		x = -0.36 + k * 0.18
		pts = [(x, 0, 0.3), (x * 1.2, -0.05, 0.65), (x * 0.9, -0.15, 0.95)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.07, 0.05, WATER, sides=5, glow=1.3)
		p.seg(pts[-1], (x * 0.7, -0.25, 1.08), 0.05, 0.0, CLOTH_WHITE, sides=4, glow=1.5)
	return p.build()


def turgurs_insects():
	p = Prop("turgurs_insects", 643)
	_swarm(p, 10, 0.7, AMBER, 1.2, 11)
	return p.build()


def kraggs_mending():
	p = Prop("kraggs_mending", 645)
	for sx in (-1, 1):   # a glowing heart
		p.blob((0.5, 0.35, 0.5), (sx * 0.22, 0, 0.66), LEAF, segs=(10, 8), glow=1.8)
	p.seg((0, 0, 0.6), (0, 0, 0.05), 0.42, 0.0, LEAF, sides=10, glow=1.8)
	_ring(p, 0.8, 0.5, 0.04, GOLD, glow=1.4, sides=20)
	return p.build()


def ancestral_ward():
	p = Prop("ancestral_ward", 647)
	for k in range(3):   # three standing stones, each with a spirit's glowing eyes
		a = math.radians(210 + k * 60)
		x = math.cos(a) * 0.6
		p.box((0.28, 0.25, 0.8 - 0.15 * (k != 1)), (x, 0, 0.4), STONE_LIGHT)
		for sx in (-1, 1):
			p.blob((0.06, 0.04, 0.05), (x + sx * 0.06, -0.14, 0.55), GOLD, segs=(5, 3), glow=2.5)
	_ring(p, 0.85, 0.05, 0.05, GOLD, glow=1.6, sides=20, tilt=1.2)
	return p.build()


# ---------------------------------------------------------------- ranger, level 30 and the Ashfall / High Terrace monsters

MIST = (5, 3)         # soft gray: ash, smoke, stone dust
CLAY = props.CLAY
PETAL_PURPLE = props.PETAL_PURPLE


def _ring_at(p, cx, cz, radius, r, swatch, glow=0.0, sides=18, a0=0.0, a1=math.tau, y=0.0):
	"""A ring (or an arc from a0 to a1) standing in the picture plane around (cx, cz)."""
	for k in range(sides):
		t0, t1 = a0 + (a1 - a0) * k / sides, a0 + (a1 - a0) * (k + 1) / sides
		p.seg((cx + math.cos(t0) * radius, y, cz + math.sin(t0) * radius),
			  (cx + math.cos(t1) * radius, y, cz + math.sin(t1) * radius), r, r, swatch, sides=5, glow=glow)


def _arrow(p, a, b, head=STONE_LIGHT, shaft=WOOD, fletch=CLOTH_WHITE, glow=0.0, r=0.035, hs=1.0, barbs=False):
	"""An arrow from its nock at a to its point at b, fletched in the picture plane."""
	a, b = Vector(a), Vector(b)
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(a, b, r, r, shaft, sides=6)
	p.seg(b - d * 0.04 * hs, b + d * 0.24 * hs, 0.095 * hs, 0.0, head, sides=4, glow=glow)
	if barbs:   # hooks along the head, raking back
		for k in range(3):
			base = b + d * (0.18 - k * 0.1) * hs
			for sgn in (-1, 1):
				p.seg(base, base - d * 0.14 * hs + n * sgn * 0.13 * hs, 0.035 * hs, 0.0, head, sides=4, glow=glow)
	for sgn, sw in ((1, fletch), (-1, fletch)):
		nn = n * sgn * 0.12 * hs
		root, tip = a + d * 0.03, a + d * 0.3 * hs
		p.poly([tuple(root), tuple(tip), tuple(tip - d * 0.07 * hs + nn), tuple(root + nn * 0.9)], [(0, 1, 2, 3)], sw)
	p.seg(a - d * 0.03, a + d * 0.03, r * 1.3, r * 1.3, CLOTH_RED, sides=5)


def _fl(p, x, y, z, s, glow=2.0, core=EMBER, tongue=FLAME):
	"""A flame like _flame, but at any depth."""
	p.blob((0.55 * s, 0.45 * s, 0.5 * s), (x, y, z + 0.25 * s), core, segs=(10, 6), glow=glow)
	p.seg((x, y, z + 0.3 * s), (x + 0.05 * s, y, z + 1.15 * s), 0.26 * s, 0.0, tongue, sides=8, glow=glow + 0.4)
	for sx in (-1, 1):
		p.seg((x + sx * 0.15 * s, y, z + 0.3 * s), (x + sx * 0.32 * s, y, z + 0.85 * s), 0.13 * s, 0.0, tongue, sides=6, glow=glow)


def _feather_fan(p, cx, cz, angles, length, swatch, tip=None, glow=0.0, r=0.08):
	for k, deg in enumerate(angles):
		a = math.radians(deg)
		end = (cx + math.cos(a) * length, 0, cz + math.sin(a) * length)
		p.seg((cx, 0, cz), end, r, r * 0.35, swatch, sides=5, glow=glow)
		if tip:
			p.seg(end, (end[0] + math.cos(a) * 0.12, 0, end[2] + math.sin(a) * 0.12), r * 0.35, 0.0, tip, sides=5, glow=glow)


def _dagger(p, base, tip, glow=0.0, blade=STONE_LIGHT, edge=None, w=0.075):
	base, tip = Vector(base), Vector(tip)
	d = (tip - base).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(base, tip, w, 0.0, blade, sides=4, glow=glow)
	p.seg(base - n * w * 2, base + n * w * 2, w * 0.5, w * 0.5, GOLD, sides=5)
	p.seg(base, base - d * w * 3, w * 0.55, w * 0.55, WOOD, sides=6)
	p.blob((w, w, w), tuple(base - d * w * 3.3), GOLD, segs=(6, 4))
	if edge:
		p.seg(base + d * 0.05 - Vector((0, 0.05, 0)), tip - Vector((0, 0.05, 0)), 0.02, 0.0, edge, sides=4, glow=2.2)


def false_sunfire():
	p = Prop("false_sunfire", 701)
	for k in range(12):                                                                   # crooked, blood-red rays
		a = k * math.tau / 12
		r1 = 0.95 if k % 2 else 0.78
		mid = (math.cos(a + 0.18) * 0.62, 0.05, 0.55 + math.sin(a + 0.18) * 0.62)
		p.seg((math.cos(a) * 0.4, 0.05, 0.55 + math.sin(a) * 0.4), mid, 0.07, 0.05, CRIMSON, sides=4, glow=1.6)
		p.seg(mid, (math.cos(a - 0.1) * r1, 0.05, 0.55 + math.sin(a - 0.1) * r1), 0.05, 0.0, EMBER, sides=4, glow=2.0)
	p.blob((0.82, 0.4, 0.82), (0, 0, 0.55), PURPLE, segs=(14, 10), glow=0.9)                # a dark sun
	_ring_at(p, 0, 0.55, 0.42, 0.035, FLAME, glow=2.2, sides=22, y=-0.05)
	p.blob((0.46, 0.12, 0.2), (0, -0.18, 0.55), FLAME, segs=(10, 6), glow=3.0)              # with an eye
	p.blob((0.09, 0.06, 0.2), (0, -0.25, 0.55), STONE_DARK, segs=(6, 4))
	return p.build()


def aimed_shot():
	p = Prop("aimed_shot", 703)
	_arrow(p, (-0.75, 0, 0.0), (0.28, 0, 0.72), hs=1.2)
	_ring_at(p, 0.45, 0.84, 0.3, 0.03, GOLD, glow=1.8, sides=20)                           # the mark it's aimed at
	for a in range(4):
		t = a * math.pi / 2 + math.pi / 4
		p.seg((0.45 + math.cos(t) * 0.22, -0.02, 0.84 + math.sin(t) * 0.22),
			  (0.45 + math.cos(t) * 0.42, -0.02, 0.84 + math.sin(t) * 0.42), 0.03, 0.03, GOLD, sides=4, glow=1.8)
	return p.build()


def track():
	p = Prop("track", 705)
	for k, (x, z) in enumerate(((-0.62, -0.1), (-0.15, 0.12), (0.3, -0.02))):          # a trail of prints
		_paw(p, x, z, 0.6, HIDE, 0.3 + k * 0.3)
	p.blob((0.8, 0.16, 0.42), (0.1, -0.05, 0.85), CLOTH_WHITE, segs=(12, 6), glow=0.5)  # a watching eye above
	p.blob((0.34, 0.1, 0.34), (0.1, -0.12, 0.85), LEAF, segs=(8, 6), glow=1.4)
	p.blob((0.13, 0.06, 0.18), (0.1, -0.18, 0.85), STONE_DARK, segs=(6, 4))
	_ring_at(p, 0.1, 0.72, 0.5, 0.04, WOOD, a0=0.5, a1=math.pi - 0.5, sides=10, y=-0.05)
	return p.build()


def flame_lick():
	p = Prop("flame_lick", 707)
	for sx in (-1, 1):                                                                    # two crossed twigs
		p.seg((sx * -0.55, 0, 0.0), (sx * 0.55, 0, 0.22), 0.07, 0.06, WOOD, sides=6)
	_fl(p, 0, -0.05, 0.1, 0.62, glow=2.2)
	p.seg((0.1, -0.1, 0.45), (0.35, -0.1, 0.8), 0.06, 0.0, FLAME, sides=5, glow=2.4)     # a licking tongue
	return p.build()


def ensnare():
	p = Prop("ensnare", 709)
	_ring(p, 0.48, 0.05, 0.05, HIDE, sides=20)                                            # a noose on the ground
	pts = [(0.5, 0, 0.0), (0.62, 0, 0.35), (0.62, 0, 0.75), (0.45, 0, 1.05), (0.15, 0, 1.15)]  # a bent sapling
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.07 - i * 0.012, 0.06 - i * 0.012, WOOD, sides=6)
	for x, z in ((0.3, 1.15), (0.6, 0.95)):
		p.blob((0.2, 0.08, 0.12), (x, 0, z + 0.06), LEAF, segs=(6, 4), glow=0.6)
	p.seg((0.15, 0, 1.15), (0.0, -0.1, 0.1), 0.03, 0.03, HIDE, sides=4)                  # the line down to the loop
	p.blob((0.12, 0.12, 0.12), (0.0, -0.45, 0.06), HIDE, segs=(6, 4))                     # its knot
	for k in range(5):                                                                    # a green glow round the snare
		a = k * math.tau / 5 + 0.3
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.62, math.sin(a) * 0.62, 0.2), LEAF, segs=(6, 4), glow=2.0)
	return p.build()


def salve():
	p = Prop("salve", 711)
	p.seg((0, 0, 0.0), (0, 0, 0.45), 0.36, 0.42, CLAY, sides=14)                          # a little clay pot
	p.seg((0, 0, 0.42), (0, 0, 0.5), 0.46, 0.46, CLAY, sides=14)
	p.blob((0.8, 0.8, 0.2), (0, 0, 0.52), LEAF, segs=(12, 6), glow=1.6)                     # of green ointment
	p.blob((0.5, 0.12, 0.2), (0.25, -0.1, 0.72), LEAF, rot=(0, -35, 0), segs=(8, 4), glow=0.8)   # a leaf on it
	p.seg((0.05, -0.1, 0.6), (0.45, -0.1, 0.85), 0.02, 0.01, PINE, sides=4)
	for k in range(3):
		p.blob((0.1, 0.1, 0.1), (-0.3 + k * 0.28, -0.1, 0.85 + (k % 2) * 0.18), GOLD, segs=(6, 4), glow=2.0)
	return p.build()


def strength_of_the_wild():
	p = Prop("strength_of_the_wild", 713)
	_ring_at(p, 0.0, 0.55, 0.78, 0.04, LEAF, glow=1.4, sides=24, y=0.25)                   # a green aura
	p.seg((-0.65, 0, 0.3), (0.12, 0, 0.3), 0.16, 0.15, HIDE, sides=8)                    # a flexed arm
	p.blob((0.52, 0.34, 0.36), (-0.22, 0, 0.44), HIDE, segs=(10, 6))                       # its bicep
	p.seg((0.12, 0, 0.3), (0.28, 0, 0.88), 0.14, 0.13, HIDE, sides=8)
	p.blob((0.32, 0.3, 0.3), (0.12, 0, 0.3), HIDE, segs=(8, 6))
	p.blob((0.36, 0.34, 0.34), (0.3, 0, 0.98), HIDE, segs=(10, 6))                         # fist
	for k in range(6):                                                                    # a band of leaves
		a = k * math.tau / 6
		p.blob((0.16, 0.06, 0.1), (0.2 + math.cos(a) * 0.17, math.sin(a) * 0.17, 0.6), LEAF, rot=(0, 0, math.degrees(a)), segs=(6, 4), glow=1.0)
	return p.build()


def icicle():
	p = Prop("icicle", 715)
	p.blob((1.2, 0.45, 0.24), (0, 0, 1.05), CLOTH_WHITE, segs=(12, 6))                      # a snowy ledge
	for x, h, r in ((0, 1.05, 0.2), (-0.35, 0.55, 0.11), (0.33, 0.7, 0.13)):              # icicles hanging off it
		p.seg((x, 0, 1.0), (x + 0.02, 0, 1.0 - h), r, 0.0, WATER, sides=6, glow=1.3)
	_drop(p, 0.03, -0.35, 0.28, WATER, 1.8)
	return p.build()


def entangle():
	p = Prop("entangle", 717)
	for v in range(3):                                                                    # three vines twisting up
		pts = []
		for k in range(19):
			t = k / 18
			a = v * math.tau / 3 + t * 2.2 * math.pi
			r = 0.45 - t * 0.2
			pts.append((math.cos(a) * r, math.sin(a) * r, t * 1.15))
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.075 - i * 0.003, 0.072 - i * 0.003, PINE, sides=6)
			if i % 4 == 2:
				p.blob((0.24, 0.08, 0.13), b, LEAF, rot=(0, 30 * (1 if v % 2 else -1), 0), segs=(6, 4), glow=0.8)
	p.blob((1.2, 1.0, 0.1), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	return p.build()


def eagle_eye():
	p = Prop("eagle_eye", 719)
	_feather_fan(p, 0, 0.62, (60, 80, 100, 120), 0.6, WOOD, tip=CLOTH_WHITE, r=0.09)      # a crest of feathers
	p.blob((1.1, 0.2, 0.52), (0, 0, 0.45), CLOTH_WHITE, segs=(14, 6))                        # an eye
	p.blob((0.46, 0.1, 0.46), (0, -0.1, 0.45), GOLD, segs=(10, 8), glow=1.6)
	p.blob((0.2, 0.06, 0.26), (0, -0.16, 0.45), STONE_DARK, segs=(8, 5))
	_ring_at(p, 0, 0.1, 0.5, 0.04, HIDE, a0=0.55, a1=math.pi - 0.55, sides=10, y=-0.05)   # its brow
	return p.build()


def multishot():
	p = Prop("multishot", 721)
	for deg in (18, 42, 66):                                                              # three arrows, fanned
		a = math.radians(deg)
		_arrow(p, (-0.7, 0, 0.0), (-0.7 + math.cos(a) * 1.35, 0, math.sin(a) * 1.35), glow=0.4)
	return p.build()


def natures_mend():
	p = Prop("natures_mend", 723)
	p.seg((0, 0, -0.1), (0.05, 0, 0.55), 0.05, 0.04, PINE, sides=5)                     # a stem
	for sx in (-1, 1):
		p.blob((0.4, 0.08, 0.16), (sx * 0.2, 0, 0.12), LEAF, rot=(0, sx * -30, 0), segs=(8, 4), glow=0.8)
	for k in range(5):                                                                    # a white bloom
		a = k * math.tau / 5 + math.pi / 2
		p.blob((0.34, 0.1, 0.34), (math.cos(a) * 0.26, -0.02, 0.72 + math.sin(a) * 0.26), CLOTH_WHITE, segs=(8, 5), glow=1.2)
	p.blob((0.24, 0.12, 0.24), (0, -0.1, 0.72), GOLD, segs=(8, 5), glow=2.2)
	for k in range(4):
		a = k * math.tau / 4 + 0.6
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.72, -0.1, 0.55 + math.sin(a) * 0.55), LEAF, segs=(6, 4), glow=2.0)
	return p.build()


def call_of_flame():
	p = Prop("call_of_flame", 725)
	p.blob((0.7, 0.1, 1.0), (0, 0.05, 0.5), LEAF, rot=(0, -20, 0), segs=(12, 6))          # a forest leaf
	p.seg((0.18, 0.0, 0.0), (-0.18, 0.0, 1.0), 0.03, 0.015, PINE, sides=4)
	for x, z, s in ((-0.35, 0.05, 0.5), (0.32, 0.25, 0.55), (-0.12, 0.6, 0.6), (0.22, 0.75, 0.45)):  # caught fire
		_fl(p, x, -0.12, z, s, glow=2.0)
	return p.build()


def thornskin():
	p = Prop("thornskin", 727)
	p.seg((0, 0.06, 0.55), (0, -0.08, 0.55), 0.58, 0.58, WOOD, sides=18)                   # a bark shield
	_ring_at(p, 0, 0.55, 0.36, 0.03, WOOD_GRAY, sides=16, y=-0.09)
	_ring_at(p, 0, 0.55, 0.18, 0.03, WOOD_GRAY, sides=12, y=-0.09)
	for k in range(10):                                                                   # ringed with thorns
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.5, 0, 0.55 + math.sin(a) * 0.5), (math.cos(a) * 0.85, 0, 0.55 + math.sin(a) * 0.85), 0.08, 0.0, PINE, sides=5)
	for x, z in ((-0.25, 0.75), (0.25, 0.75), (0.0, 0.3), (0.3, 0.4), (-0.3, 0.38)):
		p.seg((x, -0.08, z), (x * 1.2, -0.35, z + 0.08), 0.06, 0.0, LEAF, sides=5, glow=0.8)
	return p.build()


def rapid_fire():
	p = Prop("rapid_fire", 729)
	for k, (x, z) in enumerate(((-0.35, 0.95), (-0.1, 0.55), (0.15, 0.15))):             # three arrows in quick flight
		_arrow(p, (x - 0.6, 0, z), (x + 0.55, 0, z + 0.05), head=GOLD, glow=1.4)
		for j in range(2):                                                                # speed streaks
			p.seg((x - 1.05, 0.05, z + 0.08 - j * 0.16), (x - 0.7, 0.05, z + 0.08 - j * 0.16), 0.025, 0.0, GOLD, sides=4, glow=1.8)
	return p.build()


def barbed_arrow():
	p = Prop("barbed_arrow", 731)
	_arrow(p, (-0.7, 0, 0.0), (0.35, 0, 0.9), head=CRIMSON, glow=1.2, hs=1.5, barbs=True)
	for x, z, s in ((0.62, 0.55, 0.25), (0.72, 0.2, 0.2)):                                # dripping blood
		_drop(p, x, z, s, CLOTH_RED, 1.0)
	return p.build()


def frost_wind():
	p = Prop("frost_wind", 733)
	for k, (z, x1, sw) in enumerate(((0.95, 0.35, CLOTH_WHITE), (0.55, 0.55, WATER), (0.15, 0.2, CLOTH_WHITE))):  # gusts ending in curls
		p.seg((-0.85, 0, z), (x1, 0, z), 0.045, 0.045, sw, sides=5, glow=1.2)
		_swirl(p, x1, z + 0.13, 0.13, 0.02, -0.9, sw, 1.2, thick=0.05, steps=14)
	_snowflake(p, 0.65, 0.95, 0.2, 1.8)
	_snowflake(p, -0.35, 0.35, 0.14, 1.8)
	_snowflake(p, 0.55, 0.05, 0.12, 1.8)
	return p.build()


def call_of_the_hawk():
	p = Prop("call_of_the_hawk", 735)
	for sx in (-1, 1):                                                                    # spread wings
		base = 90 - sx * 90
		angs = [base + sx * d for d in (-10, 5, 20, 35, 50)]
		_feather_fan(p, sx * 0.12, 0.62, angs, 0.78, WOOD, tip=CLOTH_WHITE, r=0.09)
	_feather_fan(p, 0, 0.35, (-115, -90, -65), 0.4, WOOD, tip=CLOTH_WHITE, r=0.08)       # tail
	p.blob((0.3, 0.28, 0.55), (0, -0.05, 0.52), HIDE, segs=(10, 6))                        # body
	p.blob((0.26, 0.24, 0.26), (0, -0.05, 0.9), WOOD, segs=(8, 6))                         # head
	p.seg((0, -0.2, 0.92), (0, -0.34, 0.82), 0.06, 0.0, GOLD, sides=5)                    # hooked beak
	for sx in (-1, 1):
		p.blob((0.06, 0.04, 0.06), (sx * 0.08, -0.17, 0.95), GOLD, segs=(5, 3), glow=2.0)
	_ring(p, 0.55, -0.05, 0.035, GOLD, glow=1.8, sides=18)                                # summoning circle
	return p.build()


def volley():
	p = Prop("volley", 737)
	for deg in (50, 70, 90, 110, 130):                                                    # five arrows loosed at once
		a = math.radians(deg)
		_arrow(p, (0, 0, -0.1), (math.cos(a) * 1.25, 0, -0.1 + math.sin(a) * 1.25), glow=0.5, hs=0.9)
	_ring_at(p, 0, -0.1, 1.45, 0.03, GOLD, glow=1.6, sides=16, a0=math.radians(40), a1=math.radians(140))
	return p.build()


def guardian_of_the_wild():
	p = Prop("guardian_of_the_wild", 739)
	p.blob((0.42, 0.38, 0.52), (0, 0, 0.45), HIDE, segs=(10, 8))                           # a stag's head
	p.seg((0, -0.12, 0.35), (0, -0.3, 0.05), 0.17, 0.1, HIDE, sides=8)                    # muzzle
	p.blob((0.12, 0.08, 0.08), (0, -0.33, 0.06), STONE_DARK, segs=(6, 4))
	for sx in (-1, 1):
		p.blob((0.08, 0.05, 0.08), (sx * 0.13, -0.18, 0.52), LEAF, segs=(6, 4), glow=2.6)
		p.seg((sx * 0.2, 0, 0.55), (sx * 0.42, 0.05, 0.62), 0.07, 0.0, HIDE, sides=5)      # ears
		pts = [(sx * 0.12, 0, 0.72), (sx * 0.3, 0, 0.95), (sx * 0.5, 0, 1.15), (sx * 0.62, 0, 1.4)]  # antlers of light
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.05, 0.04, LEAF, sides=5, glow=1.5)
		for (bx, bz), (tx, tz) in (((0.3, 0.95), (0.18, 1.25)), ((0.5, 1.15), (0.4, 1.42)), ((0.4, 1.05), (0.72, 1.1))):
			p.seg((sx * bx, 0, bz), (sx * tx, 0, tz), 0.04, 0.0, LEAF, sides=5, glow=1.5)
	_ring(p, 0.62, -0.05, 0.035, GOLD, glow=1.6, sides=18)
	return p.build()


def natures_renewal():
	p = Prop("natures_renewal", 741)
	p.seg((0, 0, 0.0), (0, 0, 0.55), 0.12, 0.08, WOOD, sides=7)                          # a tree of life
	for sx in (-1, 1):
		p.seg((0, 0, 0.05), (sx * 0.3, 0, -0.02), 0.07, 0.02, WOOD, sides=5)
		p.seg((0, 0, 0.45), (sx * 0.25, 0, 0.7), 0.05, 0.03, WOOD, sides=5)
	for x, z, s in ((0, 0.95, 0.62), (-0.35, 0.78, 0.46), (0.35, 0.78, 0.46), (-0.2, 1.15, 0.4), (0.22, 1.12, 0.42)):
		p.blob((s, s * 0.8, s * 0.85), (x, 0, z), LEAF, segs=(10, 6), glow=1.3)
	for k in range(7):                                                                    # golden motes round it
		a = k * math.tau / 7
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.8, -0.2, 0.7 + math.sin(a) * 0.6), GOLD, segs=(6, 4), glow=2.4)
	_ring(p, 0.55, 0.0, 0.035, LEAF, glow=1.8, sides=18)
	return p.build()


def piercing_shot():
	p = Prop("piercing_shot", 743)
	n = Vector((0.75, -0.66, 0.0))
	c = Vector((0.0, 0.0, 0.5))
	p.seg(tuple(c - n * 0.06), tuple(c + n * 0.06), 0.5, 0.5, WOOD, sides=14)            # a plank shield, run through
	side = Vector((0.66, 0.75, 0.0))
	for k in (-1, 1):                                                                     # its plank seams
		off = c - n * 0.075 + Vector((0, 0, k * 0.2))
		p.seg(tuple(off - side * 0.42), tuple(off + side * 0.42), 0.02, 0.02, WOOD_GRAY, sides=4)
	_arrow(p, (-0.95, 0, 0.2), (0.85, 0, 0.8), glow=0.8, hs=1.1)
	for k in range(6):                                                                    # splinters bursting out
		a = k * math.tau / 6 + 0.3
		p.box((0.16, 0.05, 0.05), (0.18 + math.cos(a) * 0.16, -0.12, 0.58 + math.sin(a) * 0.16), WOOD, rot=(0, -math.degrees(a), 0))
	for j in (-1, 1):                                                                     # a streak along its path
		p.seg((-0.95, 0.05, 0.2 + j * 0.1), (-0.35, 0.05, 0.4 + j * 0.1), 0.025, 0.0, CLOTH_WHITE, sides=4, glow=1.6)
	return p.build()


def wildfire():
	p = Prop("wildfire", 745)
	p.seg((0, 0, 0.0), (0, 0, 0.25), 0.08, 0.08, WOOD, sides=6)                          # a pine, burning
	for k, (z, r) in enumerate(((0.2, 0.5), (0.5, 0.4), (0.78, 0.3))):
		p.seg((0, 0, z), (0, 0, z + 0.45), r, 0.0, PINE, sides=8)
	for x, y, z, s in ((-0.45, -0.2, 0.0, 0.55), (0.45, -0.2, 0.0, 0.6), (-0.22, -0.3, 0.35, 0.5), (0.25, -0.3, 0.55, 0.45), (0.0, -0.1, 0.9, 0.55)):
		_fl(p, x, y, z, s, glow=2.2)
	p.blob((1.6, 0.9, 0.1), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	return p.build()


def hawks_fury():
	p = Prop("hawks_fury", 747)
	p.blob((0.62, 0.5, 0.58), (-0.3, 0, 0.6), WOOD, segs=(10, 8))                           # a hawk's head, screaming
	p.blob((0.36, 0.3, 0.3), (-0.22, -0.12, 0.48), CLOTH_WHITE, segs=(8, 6))                 # pale cheek
	p.seg((-0.05, 0, 0.66), (0.28, 0, 0.6), 0.14, 0.05, GOLD, sides=6)                     # hooked beak
	p.seg((0.28, 0, 0.6), (0.3, 0, 0.44), 0.05, 0.0, GOLD, sides=5)
	p.seg((-0.05, 0, 0.52), (0.18, 0, 0.44), 0.06, 0.0, GOLD, sides=5)
	p.blob((0.14, 0.06, 0.1), (-0.12, -0.25, 0.72), FLAME, segs=(6, 4), glow=3.0)           # a furious eye
	p.seg((-0.25, -0.24, 0.84), (0.0, -0.24, 0.76), 0.04, 0.04, STONE_DARK, sides=4)        # its brow
	for k in range(3):                                                                    # fiery talon rakes
		x = 0.45 + k * 0.2
		p.seg((x, -0.1, 1.15 - k * 0.05), (x - 0.25, -0.1, 0.05 - k * 0.05), 0.06, 0.02, FLAME, sides=4, glow=2.2)
	for k in range(3):
		p.seg((-0.55, 0.05, 0.85 - k * 0.12), (-0.95, 0.05, 0.95 - k * 0.2), 0.08, 0.02, WOOD, sides=5)   # swept-back crest
	return p.build()


def trueshot():
	p = Prop("trueshot", 749)
	for k, (r, sw) in enumerate(((0.62, CLOTH_RED), (0.48, CLOTH_WHITE), (0.34, CLOTH_RED), (0.2, CLOTH_WHITE), (0.08, GOLD))):  # a target
		p.seg((0, 0.04 - k * 0.025, 0.6), (0, -0.0 - k * 0.025, 0.6), r, r, sw, sides=20, glow=2.0 if sw == GOLD else 0.0)
	for sx in (-1, 1):
		p.seg((sx * 0.3, 0.1, 0.3), (sx * 0.5, 0.25, -0.2), 0.05, 0.05, WOOD, sides=5)
	_arrow(p, (-0.62, -0.75, 1.1), (0, -0.12, 0.6), glow=1.0)                             # dead center
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.1, -0.2, 0.6 + math.sin(a) * 0.1), (math.cos(a) * 0.3, -0.2, 0.6 + math.sin(a) * 0.3), 0.025, 0.0, GOLD, sides=4, glow=2.4)
	return p.build()


def storm_of_arrows():
	p = Prop("storm_of_arrows", 751)
	for x, z, s in ((-0.45, 1.25, 0.55), (0.1, 1.35, 0.65), (0.55, 1.22, 0.5), (-0.1, 1.15, 0.5)):  # a dark cloud
		p.blob((s, s * 0.6, s * 0.7), (x, 0.1, z), STONE_DARK, segs=(10, 6))
	for k, (x, z) in enumerate(((-0.7, 0.55), (-0.45, 0.2), (-0.2, 0.65), (0.05, 0.1), (0.3, 0.55), (0.55, 0.15), (0.75, 0.6), (-0.05, -0.3))):  # raining arrows
		_arrow(p, (x - 0.08, -0.1, z + 0.55), (x + 0.08, -0.1, z), glow=0.8, hs=0.7, r=0.028)
	return p.build()


def mighty_blow():
	p = Prop("mighty_blow", 753)
	p.blob((1.6, 1.0, 0.12), (0, 0, 0.0), STONE_DARK, segs=(12, 4))                          # the ground, cracking
	for k in range(5):
		a = k * math.tau / 5 + 0.4
		p.seg((0, 0, 0.06), (math.cos(a) * 0.75, math.sin(a) * 0.5, 0.06), 0.04, 0.01, FLAME, sides=4, glow=2.0)
	c = Vector((-0.05, 0, 0.42))
	d = Vector((0.55, 0, 0.83)).normalized()
	perp = Vector((-d.z, 0, d.x))
	p.seg(tuple(c), tuple(c + d * 1.0), 0.06, 0.06, WOOD, sides=6)                         # a great maul
	p.seg(tuple(c - perp * 0.42), tuple(c + perp * 0.42), 0.25, 0.25, STONE_LIGHT, sides=8)
	for sgn in (-1, 1):
		p.seg(tuple(c + perp * sgn * 0.3), tuple(c + perp * sgn * 0.36), 0.27, 0.27, IRON, sides=8)
	p.blob((0.12, 0.12, 0.12), tuple(c + d * 1.02), IRON, segs=(6, 4))
	for k in range(9):                                                                    # the impact
		a = math.pi * (0.05 + k * 0.11)
		p.seg((0.25 + math.cos(a) * 0.4, -0.3, 0.05 + math.sin(a) * 0.35), (0.25 + math.cos(a) * 0.75, -0.3, 0.05 + math.sin(a) * 0.62),
			  0.045, 0.0, GOLD, sides=4, glow=2.2)
	return p.build()


def unbreakable():
	p = Prop("unbreakable", 755)
	_ring_at(p, 0, 0.5, 0.8, 0.04, CLOTH_WHITE, glow=1.6, sides=24, y=0.3)                # a silver halo
	p.box((1.0, 0.42, 0.22), (0.05, 0, 0.75), STONE_LIGHT)                                 # an anvil
	p.seg((-0.45, 0, 0.75), (-0.85, 0, 0.8), 0.12, 0.0, STONE_LIGHT, sides=8)             # its horn
	p.box((0.4, 0.3, 0.35), (0.05, 0, 0.5), STONE_LIGHT)
	p.box((0.8, 0.5, 0.2), (0.05, 0, 0.23), STONE_LIGHT)
	p.box((1.02, 0.44, 0.04), (0.05, 0, 0.87), CLOTH_WHITE, glow=1.2)
	for x, z, g in ((0.62, 1.1, 0.3), (-0.62, 0.15, 0.22)):                              # a glint
		p.seg((x, -0.25, z - g), (x, -0.25, z + g), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.5)
		p.seg((x, -0.25, z + g * 0.05), (x, -0.25, z - g), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.5)
		p.seg((x - g * 0.7, -0.25, z), (x + g * 0.7, -0.25, z), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=2.5)
	return p.build()


def _axe(p, a, b, flip=1):
	a, b = Vector(a), Vector(b)
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x)) * flip
	fwd = Vector((0, -0.07, 0))
	p.seg(a, b + d * 0.05, 0.055, 0.055, WOOD, sides=6)
	top, bot = b - d * 0.02, b - d * 0.5
	pts = [top, top + n * 0.3 + d * 0.1, top + n * 0.6 + d * 0.14, bot + n * 0.6 - d * 0.14, bot + n * 0.3 - d * 0.1, bot]
	p.poly([tuple(v + fwd) for v in pts], [(0, 1, 2, 3, 4, 5)], STONE_LIGHT)
	e0, e1 = top + n * 0.6 + d * 0.14, bot + n * 0.6 - d * 0.14
	p.seg(tuple(e0 + fwd), tuple(e1 + fwd), 0.035, 0.035, CLOTH_WHITE, sides=4, glow=1.0)   # its bright edge
	p.box((0.16, 0.16, 0.16), tuple(b - d * 0.2), IRON)


def rampage():
	p = Prop("rampage", 757)
	for k in range(12):                                                                   # a red burst of rage
		a = k * math.tau / 12
		r1 = 0.95 if k % 2 else 0.7
		p.seg((math.cos(a) * 0.25, 0.3, 0.5 + math.sin(a) * 0.25), (math.cos(a) * r1 * 0.9, 0.3, 0.5 + math.sin(a) * r1 * 0.9), 0.12, 0.0,
			  CRIMSON if k % 2 else CLOTH_RED, sides=5, glow=1.8)
	_axe(p, (-0.55, 0, -0.1), (0.55, 0, 1.0), flip=-1)                                    # two axes crossed
	_axe(p, (0.55, -0.1, -0.1), (-0.55, -0.1, 1.0), flip=1)
	return p.build()


def superior_healing():
	p = Prop("superior_healing", 759)
	for sx in (-1, 1):                                                                    # wings of light
		base = 90 - sx * 90
		_feather_fan(p, sx * 0.2, 0.62, [base + sx * d for d in (-25, -5, 15, 35)], 0.7, CLOTH_WHITE, glow=1.0, r=0.1)
	p.box((0.26, 0.24, 0.95), (0, -0.05, 0.5), GOLD, glow=2.2)                               # a great gold cross
	p.box((0.7, 0.24, 0.26), (0, -0.05, 0.62), GOLD, glow=2.2)
	for k in range(6):
		a = k * math.tau / 6 + 0.25
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.95, -0.2, 0.55 + math.sin(a) * 0.65), LEAF, segs=(6, 4), glow=2.2)
	return p.build()


def dawns_wrath():
	p = Prop("dawns_wrath", 761)
	p.seg((0, 0.2, 0.4), (0, 0.1, 0.4), 0.5, 0.5, GOLD, sides=20, glow=2.2)               # the dawn sun on the horizon
	for k in range(7):
		a = math.radians(15 + k * 25)
		p.seg((math.cos(a) * 0.55, 0.15, 0.4 + math.sin(a) * 0.55), (math.cos(a) * 1.0, 0.15, 0.4 + math.sin(a) * 1.0), 0.07, 0.0, FLAME, sides=4, glow=2.2)
	p.box((1.9, 0.6, 0.45), (0, 0.1, 0.1), STONE_WARM)                                    # the horizon hides its lower half
	for sx in (-1, 1):                                                                    # two gleaming tusks sweeping up
		pts = [(sx * 0.55, -0.3, 0.2), (sx * 0.4, -0.35, 0.55), (sx * 0.15, -0.4, 0.8), (sx * -0.1, -0.4, 0.95)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.1 - i * 0.03, 0.07 - i * 0.03 if i < 2 else 0.0, BONE, sides=7, glow=0.8)
	return p.build()


def aegis_of_the_dawn():
	p = Prop("aegis_of_the_dawn", 763)
	_ring_at(p, 0, 0.55, 0.95, 0.04, CLOTH_WHITE, glow=1.4, sides=24, y=0.2)                # a group halo
	p.box((1.0, 0.12, 0.72), (0, 0.02, 0.8), GOLD, glow=0.8)                                # a kite shield, gold-rimmed
	p.seg((0, 0.02, 0.45), (0, 0.02, -0.35), 0.71, 0.0, GOLD, sides=4, glow=0.8, twist=45)
	p.box((0.84, 0.1, 0.6), (0, -0.03, 0.8), CLOTH_WHITE, glow=0.3)
	p.seg((0, -0.03, 0.51), (0, -0.03, -0.22), 0.6, 0.0, CLOTH_WHITE, sides=4, glow=0.3, twist=45)
	p.seg((0, -0.09, 0.6), (0, -0.14, 0.6), 0.28, 0.28, FLAME, sides=14, glow=2.2)          # its rising-sun blazon
	for k in range(5):
		a = math.radians(20 + k * 35)
		p.seg((math.cos(a) * 0.32, -0.12, 0.6 + math.sin(a) * 0.32), (math.cos(a) * 0.5, -0.12, 0.6 + math.sin(a) * 0.5), 0.05, 0.0, FLAME, sides=4, glow=2.4)
	p.box((0.8, 0.08, 0.2), (0, -0.12, 0.44), STONE_WARM)
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(29), 4, "Z"))                          # turned to face the viewer
	return obj


def glacial_spike():
	p = Prop("glacial_spike", 765)
	p.blob((1.5, 0.9, 0.3), (0, 0, 0.0), CLOTH_WHITE, segs=(12, 5))                          # icy ground
	p.seg((-0.35, 0, 0.0), (0.3, 0, 1.0), 0.26, 0.22, WATER, sides=6, glow=1.1)            # a spear of ice as big as a man
	p.seg((0.3, 0, 1.0), (0.45, 0, 1.3), 0.22, 0.0, WATER, sides=6, glow=1.5)
	p.seg((-0.3, -0.18, 0.1), (0.35, -0.18, 1.05), 0.04, 0.02, CLOTH_WHITE, sides=4, glow=1.6)  # a bright facet
	for x, h, lean in ((-0.65, 0.4, -25), (0.35, 0.35, 30), (0.6, 0.25, 40)):
		top = (x + math.sin(math.radians(lean)) * h, -0.1, 0.05 + math.cos(math.radians(lean)) * h)
		p.seg((x, -0.1, 0.05), top, 0.1, 0.0, RUNE, sides=5, glow=1.2)
	return p.build()


def mana_ward():
	p = Prop("mana_ward", 767)
	p.seg((0, 0.06, 0.55), (0, -0.04, 0.55), 0.7, 0.7, PURPLE, sides=6, glow=1.0)          # a hexagon ward
	for k in range(6):
		a0, a1 = k * math.tau / 6, (k + 1) * math.tau / 6
		for r, sw, g in ((0.72, CLOTH_WHITE, 1.4), (0.42, RUNE, 2.0)):
			p.seg((math.cos(a0) * r, -0.06, 0.55 + math.sin(a0) * r), (math.cos(a1) * r, -0.06, 0.55 + math.sin(a1) * r), 0.035, 0.035, sw, sides=5, glow=g)
		p.seg((math.cos(a0) * 0.42, -0.06, 0.55 + math.sin(a0) * 0.42), (math.cos(a0) * 0.72, -0.06, 0.55 + math.sin(a0) * 0.72), 0.025, 0.025, RUNE, sides=4, glow=1.6)
	p.blob((0.22, 0.14, 0.34), (0, -0.1, 0.55), CLOTH_WHITE, rot=(0, 0, 0), segs=(4, 3), glow=2.6)   # a rune-gem
	return p.build()


def inferno():
	p = Prop("inferno", 769)
	p.blob((1.9, 1.0, 0.12), (0, 0.1, 0.0), STONE_DARK, segs=(12, 4))
	for x, y, s in ((-0.62, 0.1, 0.7), (0.62, 0.1, 0.75), (-0.3, -0.05, 0.95), (0.3, -0.05, 1.0), (0.0, -0.2, 1.2)):  # a wall of fire
		_fl(p, x, y, 0.0, s, glow=2.0, core=CLOTH_RED if s > 0.9 else EMBER)
	for k in range(6):                                                                    # sparks
		a = k * 1.1
		p.blob((0.07, 0.07, 0.07), (math.cos(a) * 0.7, -0.3, 1.1 + math.sin(a) * 0.25), FLAME, segs=(5, 3), glow=3.0)
	return p.build()


def shadowstrike():
	p = Prop("shadowstrike", 771)
	for x, z, s in ((-0.45, 0.25, 0.6), (-0.2, 0.05, 0.55), (-0.55, 0.6, 0.45), (-0.05, 0.35, 0.5)):  # a shadow
		p.blob((s, s * 0.8, s), (x, 0.1, z), PURPLE, segs=(10, 6), glow=0.5)
	_dagger(p, (-0.15, -0.15, 0.35), (0.85, -0.15, 1.25), edge=PETAL_PURPLE, w=0.12)                 # a blade out of it
	for k in range(3):
		p.seg((-0.3 + k * 0.1, -0.05, 0.6 + k * 0.15), (0.25 + k * 0.1, -0.05, 1.1 + k * 0.08), 0.02, 0.0, PURPLE, sides=4, glow=2.0)
	return p.build()


def blade_flurry():
	p = Prop("blade_flurry", 773)
	for k in range(4):                                                                    # daggers spinning like a wheel
		a = k * math.tau / 4 + 0.3
		base = (math.cos(a) * 0.32, 0, 0.55 + math.sin(a) * 0.32)
		tip = (math.cos(a) * 0.95, 0, 0.55 + math.sin(a) * 0.95)
		_dagger(p, base, tip, w=0.12)
		_ring_at(p, 0, 0.55, 1.0, 0.035, CLOTH_WHITE, glow=1.8, sides=6, a0=a + 0.3, a1=a + 1.25)
	p.blob((0.2, 0.2, 0.2), (0, 0, 0.55), GOLD, segs=(8, 5), glow=1.5)
	return p.build()


def deathmark():
	p = Prop("deathmark", 775)
	_ring_at(p, 0, 0.62, 0.6, 0.06, CRIMSON, glow=1.8, sides=22)                           # a mark on the foe
	for sx in (-1, 1):
		p.seg((sx * -0.45, -0.05, 1.05), (sx * 0.45, -0.05, 0.2), 0.1, 0.06, CLOTH_RED, sides=5, glow=1.6)
	for x, z, s in ((-0.25, -0.1, 0.25), (0.3, -0.2, 0.3), (0.0, -0.4, 0.22)):             # bleeding
		_drop(p, x, z, s, CLOTH_RED, 1.0)
	return p.build()


def elemental_mending():
	p = Prop("elemental_mending", 777)
	_fl(p, 0, 0.1, 0.0, 1.1, glow=1.6, core=AMBER)                                          # an elemental's flame
	p.box((0.18, 0.1, 0.6), (0, -0.35, 0.5), LEAF, glow=2.4)                                # knit back with green
	p.box((0.55, 0.1, 0.18), (0, -0.35, 0.55), LEAF, glow=2.4)
	_ring_at(p, 0, 0.6, 0.8, 0.035, LEAF, glow=1.4, sides=24, a0=math.radians(200), a1=math.radians(340))
	for k in range(3):
		p.blob((0.1, 0.1, 0.1), (-0.55 + k * 0.55, -0.3, 1.2 - (k % 2) * 0.15), LEAF, segs=(6, 4), glow=2.2)
	return p.build()


def primal_surge():
	p = Prop("primal_surge", 779)
	for v, sw in enumerate((FLAME, WATER, STONE_WARM, CLOTH_WHITE)):                      # four elements spiraling up
		pts = []
		for k in range(21):
			t = k / 20
			a = v * math.tau / 4 + t * 1.5 * math.pi
			r = 0.75 * (1 - t) + 0.08
			pts.append((math.cos(a) * r, math.sin(a) * r * 0.5, t * 0.95))
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			w = 0.1 - i * 0.003
			p.seg(a, b, w, w, sw, sides=6, glow=0.6 if sw == STONE_WARM else 1.6)
	p.seg((0, 0, 0.9), (0, 0, 1.4), 0.26, 0.0, GOLD, sides=4, glow=2.4)                   # surging to a point
	return p.build()


def call_of_the_elemental_lord():
	p = Prop("call_of_the_elemental_lord", 781)
	_elemental(p, STONE_DARK, s=1.05)                                                      # a lord of stone and fire
	p.blob((0.3, 0.1, 0.3), (0, -0.2, 0.5), EMBER, segs=(8, 6), glow=3.0)                   # molten heart
	for sx in (-1, 1):
		_fl(p, sx * 0.28, 0, 0.62, 0.3, glow=2.2)
		p.blob((0.08, 0.05, 0.06), (sx * 0.08, -0.15, 1.0), FLAME, segs=(5, 3), glow=3.0)
	for k in range(5):                                                                    # a crown
		x = -0.2 + k * 0.1
		p.seg((x, 0, 1.08), (x, 0, 1.3 if k % 2 == 0 else 1.2), 0.05, 0.0, GOLD, sides=4, glow=1.4)
	_ring(p, 0.14, 1.1, 0.03, GOLD, glow=1.4, sides=12)
	_ring(p, 0.7, 0.0, 0.04, FLAME, glow=2.0, sides=20)
	return p.build()


def soul_harvest():
	p = Prop("soul_harvest", 783)
	p.seg((0.45, 0, -0.15), (-0.3, 0, 1.15), 0.05, 0.05, WOOD, sides=6)                  # a scythe
	blade = []
	for k in range(9):
		t = k / 8
		a = math.radians(80 + t * 110)
		blade.append((-0.3 + 0.75 + math.cos(a) * 0.75, 0, 1.15 - 0.45 + math.sin(a) * 0.45))
	for i, (a, b) in enumerate(zip(blade, blade[1:])):
		w = 0.09 * (1 - i / 8) + 0.01
		p.seg(a, b, w, w * 0.9, STONE_LIGHT, sides=4)
	for x, z, s in ((0.45, 0.55, 0.3), (0.2, 0.25, 0.24), (0.62, 0.95, 0.22)):             # souls torn loose
		p.blob((s, s * 0.8, s), (x, -0.15, z), PETAL_PURPLE, segs=(8, 6), glow=2.2)
		p.seg((x, -0.15, z), (x + s * 1.3, -0.15, z - s * 0.9), s * 0.35, 0.0, PURPLE, sides=5, glow=1.8)
	return p.build()


def plague():
	p = Prop("plague", 785)
	for x, z, s in ((-0.45, 0.45, 0.6), (0.45, 0.5, 0.6), (0, 0.85, 0.6), (0, 0.2, 0.6)):  # a green miasma
		p.blob((s, s * 0.7, s * 0.8), (x, 0.3, z), SICKLY, segs=(10, 6), glow=0.9)
	_skull(p, 0, 0.5, 0.95, eyes=SICKLY, eye_glow=3.0)
	for k in range(5):                                                                    # flies
		a = k * math.tau / 5 + 0.5
		x, z = math.cos(a) * 0.72, 0.55 + math.sin(a) * 0.62
		p.blob((0.09, 0.07, 0.07), (x, -0.3, z), STONE_DARK, segs=(5, 3))
		p.blob((0.1, 0.02, 0.06), (x, -0.33, z + 0.05), CLOTH_WHITE, segs=(5, 3), glow=0.5)
	return p.build()


def raise_bone_colossus():
	p = Prop("raise_bone_colossus", 787)
	p.blob((1.7, 1.0, 0.2), (0, 0, -0.35), STONE_DARK, segs=(14, 5))
	p.seg((0, 0.05, -0.3), (0, 0.05, 0.75), 0.07, 0.07, BONE, sides=6)                    # spine
	for k in range(4):                                                                    # a great ribcage
		z = 0.62 - k * 0.2
		w = 0.62 - k * 0.07
		for sx in (-1, 1):
			pts = [(0, 0.05, z), (sx * w * 0.7, -0.05, z + 0.02), (sx * w, -0.2, z - 0.12), (sx * w * 0.7, -0.35, z - 0.25)]
			for a, b in zip(pts, pts[1:]):
				p.seg(a, b, 0.045, 0.04, BONE, sides=5)
	for sx in (-1, 1):                                                                    # shoulder knobs
		p.blob((0.3, 0.3, 0.26), (sx * 0.62, 0, 0.72), BONE, segs=(8, 6))
	_skull(p, 0, 1.0, 0.75, eyes=SICKLY, eye_glow=3.0)
	for sx in (-1, 1):                                                                    # horns
		p.seg((sx * 0.2, 0, 1.18), (sx * 0.48, 0, 1.45), 0.07, 0.0, BONE, sides=6)
	return p.build()


def glacial_roar():
	p = Prop("glacial_roar", 789)
	p.blob((0.62, 0.55, 0.58), (-0.35, 0, 0.6), WATER, segs=(10, 8), glow=0.9)           # an ice bear's head, roaring
	for sx in (-1, 1):
		p.blob((0.2, 0.12, 0.2), (-0.35 + sx * 0.2, 0.05, 0.92), WATER, segs=(8, 5), glow=0.9)   # round ears
	p.seg((-0.15, 0, 0.7), (0.25, 0, 0.78), 0.17, 0.13, WATER, sides=8, glow=0.9)          # upper jaw
	p.seg((-0.2, 0, 0.45), (0.18, 0, 0.35), 0.13, 0.1, WATER, sides=8, glow=0.9)           # lower jaw
	for k in range(3):
		x = -0.02 + k * 0.1
		p.seg((x, -0.08, 0.66), (x, -0.08, 0.54), 0.035, 0.0, CLOTH_WHITE, sides=4, glow=1.2)
		p.seg((x - 0.02, -0.08, 0.44), (x - 0.02, -0.08, 0.54), 0.03, 0.0, CLOTH_WHITE, sides=4, glow=1.2)
	p.blob((0.1, 0.06, 0.08), (0.27, -0.05, 0.82), STONE_DARK, segs=(6, 4))
	p.blob((0.1, 0.05, 0.07), (-0.2, -0.26, 0.78), CLOTH_WHITE, segs=(6, 4), glow=2.6)
	for k in range(3):                                                                    # its roar, freezing
		_ring_at(p, 0.25, 0.56, 0.3 + k * 0.2, 0.035, CLOTH_WHITE, glow=1.6, sides=8, a0=-0.7, a1=0.7)
	return p.build()


def tigirs_swarm():
	p = Prop("tigirs_swarm", 791)
	for z in (0.0, 1.0):                                                                  # an hourglass
		p.seg((0, 0, z - 0.04), (0, 0, z + 0.04), 0.38, 0.38, WOOD, sides=10)
	for k in range(3):
		a = k * math.tau / 3 + 0.5
		p.seg((math.cos(a) * 0.32, math.sin(a) * 0.32, 0.0), (math.cos(a) * 0.32, math.sin(a) * 0.32, 1.0), 0.03, 0.03, WOOD, sides=5)
	p.seg((0, 0, 0.94), (0, 0, 0.5), 0.26, 0.04, CLOTH_WHITE, sides=10, glow=0.3)
	p.seg((0, 0, 0.06), (0, 0, 0.5), 0.26, 0.04, CLOTH_WHITE, sides=10, glow=0.3)
	p.seg((0, -0.02, 0.07), (0, -0.02, 0.3), 0.22, 0.0, AMBER, sides=10, glow=1.2)        # sand running low
	_swarm(p, 7, 0.65, AMBER, 1.2, 13)
	return p.build()


def ancestral_avatar():
	p = Prop("ancestral_avatar", 793)
	for k in range(9):                                                                    # a headdress of feathers
		deg = 20 + k * 17.5
		a = math.radians(deg)
		_feather_fan(p, 0, 0.62, (deg,), 0.72, CLOTH_WHITE if k % 2 else CLOTH_RED, tip=STONE_DARK, glow=0.6, r=0.08)
	p.blob((0.72, 0.25, 0.92), (0, -0.05, 0.5), GOLD, segs=(12, 8), glow=1.2)                # a spirit mask
	for sx in (-1, 1):
		p.blob((0.2, 0.1, 0.12), (sx * 0.15, -0.18, 0.62), STONE_DARK, segs=(8, 4))
		p.blob((0.08, 0.05, 0.06), (sx * 0.15, -0.22, 0.62), CLOTH_WHITE, segs=(5, 3), glow=3.0)
		p.box((0.05, 0.03, 0.25), (sx * 0.24, -0.16, 0.38), CLOTH_RED)
	p.seg((0, -0.15, 0.55), (0, -0.25, 0.4), 0.06, 0.04, AMBER, sides=5)
	p.box((0.28, 0.05, 0.06), (0, -0.2, 0.24), STONE_DARK)
	return p.build()


def harpy_shriek():
	p = Prop("harpy_shriek", 795)
	_feather_fan(p, -0.4, 0.62, (100, 130, 160, 190), 0.55, WOOD, tip=CLOTH_WHITE, r=0.08)   # a feathered mane
	p.blob((0.46, 0.4, 0.5), (-0.3, 0, 0.62), HIDE, segs=(10, 8))                             # a harpy's head
	p.seg((-0.12, 0, 0.7), (0.2, 0, 0.72), 0.1, 0.0, GOLD, sides=5)                           # beak, open
	p.seg((-0.12, 0, 0.58), (0.12, 0, 0.47), 0.07, 0.0, GOLD, sides=5)
	p.blob((0.1, 0.05, 0.08), (-0.22, -0.2, 0.74), CLOTH_RED, segs=(6, 4), glow=2.6)
	for k in range(3):                                                                    # the shriek
		_ring_at(p, 0.15, 0.6, 0.28 + k * 0.2, 0.035, GOLD, glow=1.8, sides=8, a0=-0.75, a1=0.75)
	return p.build()


def monk_palm():
	p = Prop("monk_palm", 797)
	for k in range(10):                                                                   # the force of the blow
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.5, 0.25, 0.6 + math.sin(a) * 0.5), (math.cos(a) * 0.95, 0.25, 0.6 + math.sin(a) * 0.95), 0.06, 0.0, AMBER, sides=4, glow=2.0)
	p.blob((0.55, 0.22, 0.55), (0, 0, 0.45), HIDE, segs=(10, 6))                            # an open palm
	for k, (x, h) in enumerate(((-0.2, 0.4), (-0.07, 0.48), (0.07, 0.46), (0.2, 0.38))):
		p.seg((x, 0, 0.65), (x * 1.1, 0, 0.65 + h), 0.07, 0.06, HIDE, sides=6)
		p.blob((0.12, 0.12, 0.12), (x * 1.1, 0, 0.65 + h), HIDE, segs=(6, 4))
	p.seg((-0.25, 0, 0.4), (-0.48, 0, 0.62), 0.08, 0.06, HIDE, sides=6)                   # thumb
	p.seg((0, 0, 0.2), (0, 0, -0.15), 0.18, 0.18, CLOTH_WHITE, sides=8)                   # a wrapped wrist
	return p.build()


def ember_breath():
	p = Prop("ember_breath", 799)
	p.blob((0.55, 0.45, 0.45), (-0.5, 0, 0.7), STONE_DARK, segs=(10, 6))                   # a drake's head
	p.seg((-0.3, 0, 0.78), (0.05, 0, 0.72), 0.16, 0.1, STONE_DARK, sides=7)               # upper jaw
	p.seg((-0.35, 0, 0.55), (0.0, 0, 0.5), 0.1, 0.07, STONE_DARK, sides=7)                 # lower jaw, gaping
	for sx in (-1, 1):
		p.seg((-0.6, sx * 0.12, 0.85), (-0.95, sx * 0.12, 1.1), 0.08, 0.0, BONE, sides=5)  # horns
	p.blob((0.12, 0.06, 0.07), (-0.38, -0.2, 0.84), FLAME, segs=(6, 4), glow=3.0)
	for k in range(9):                                                                    # a breath of embers
		t = k / 8
		x = 0.05 + t * 0.85
		z = 0.63 - t * 0.35 + math.sin(k * 2.1) * t * 0.2
		s = 0.12 + t * 0.14
		p.blob((s, s, s), (x, -0.05, z), EMBER if k % 2 else FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def cinder_bolt():
	p = Prop("cinder_bolt", 801)
	for k in range(4):                                                                    # a trail of ash smoke
		x, z, s = 0.0 - k * 0.3, 0.55 - k * 0.14, 0.46 - k * 0.08
		p.blob((s, s * 0.8, s * 0.9), (x, 0.1, z), MIST, segs=(8, 6), jitter=0.03)
	p.rock((0.78, 0.7, 0.7), (0.4, 0, 0.72), STONE_DARK, jitter=0.1)                        # a burning cinder
	p.blob((0.62, 0.5, 0.55), (0.42, 0.05, 0.72), EMBER, segs=(8, 6), glow=2.0)             # glowing through its cracks
	for a, b in (((0.2, 0.95), (0.4, 0.72)), ((0.4, 0.72), (0.62, 0.85)), ((0.4, 0.72), (0.36, 0.45)), ((0.62, 0.85), (0.7, 0.62))):
		p.seg((a[0], -0.36, a[1]), (b[0], -0.36, b[1]), 0.045, 0.045, FLAME, sides=4, glow=3.0)
	for k in range(6):                                                                    # and sparks
		p.blob((0.08, 0.08, 0.08), (0.0 - k * 0.2, -0.3, 0.85 - k * 0.1 + (k % 2) * 0.2), FLAME, segs=(5, 3), glow=3.0)
	return p.build()


def ash_chill():
	p = Prop("ash_chill", 803)
	p.blob((0.55, 0.4, 0.55), (0, 0, 0.85), STONE_LIGHT, segs=(10, 8), glow=0.3)             # an ash wraith
	p.seg((0, 0, 0.8), (0.1, 0, 0.2), 0.27, 0.12, STONE_LIGHT, sides=8, glow=0.3)
	_swirl(p, 0.2, 0.2, 0.2, 0.05, 1.0, STONE_LIGHT, 0.3, thick=0.1, steps=12)
	for sx in (-1, 1):
		p.blob((0.12, 0.06, 0.16), (sx * 0.1, -0.2, 0.88), STONE_DARK, segs=(6, 4))
	p.blob((0.12, 0.06, 0.1), (0, -0.2, 0.72), STONE_DARK, segs=(6, 4))
	for sx in (-1, 1):                                                                    # reaching, clawed arms
		p.seg((sx * 0.2, 0, 0.62), (sx * 0.6, -0.1, 0.5), 0.07, 0.03, STONE_LIGHT, sides=5, glow=0.3)
		for d in (-0.1, 0.0, 0.1):
			p.seg((sx * 0.6, -0.1, 0.5), (sx * 0.72, -0.12, 0.5 + d), 0.025, 0.0, STONE_LIGHT, sides=4)
	for k in range(8):                                                                    # drifting ash
		a = k * 0.8
		p.blob((0.06, 0.06, 0.06), (math.cos(a) * (0.5 + 0.05 * k), -0.2, 0.55 + math.sin(a) * 0.5), MIST, segs=(5, 3))
	return p.build()


def searing_blow():
	p = Prop("searing_blow", 805)
	p.blob((1.7, 1.0, 0.12), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	for k in range(6):                                                                    # molten cracks
		a = k * math.tau / 6
		p.seg((0, 0, 0.06), (math.cos(a) * 0.8, math.sin(a) * 0.5, 0.06), 0.045, 0.01, EMBER, sides=4, glow=2.4)
	p.rock((0.6, 0.55, 0.55), (0, 0, 0.35), EMBER, jitter=0.08)                               # a glowing lump of rock
	p.blob((0.4, 0.4, 0.36), (0, -0.06, 0.38), FLAME, segs=(8, 6), glow=2.2)
	for k in range(7):                                                                    # splashing on impact
		a = math.radians(20 + k * 23)
		p.seg((math.cos(a) * 0.35, -0.2, 0.25 + math.sin(a) * 0.3), (math.cos(a) * 0.8, -0.2, 0.25 + math.sin(a) * 0.7), 0.06, 0.0, FLAME, sides=4, glow=2.4)
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.88, -0.2, 0.25 + math.sin(a) * 0.78), EMBER, segs=(5, 3), glow=2.6)
	return p.build()


# ---------------------------------------------------------------- Reedmere and Drownfast monsters

AQUA = (5, 1)         # pale aqua to deep teal: naga, sea glass
SEAFOAM = (0, 2)      # sea green


def _hand(p, x, z, s, swatch, glow=0.0, curl=0.0, y=0.0):
	"""A hand reaching up: palm, four fingers (curl bends their tips in) and a thumb."""
	p.blob((0.5 * s, 0.24 * s, 0.5 * s), (x, y, z), swatch, segs=(10, 6), glow=glow)
	for k, (fx, h) in enumerate(((-0.18, 0.36), (-0.06, 0.44), (0.06, 0.42), (0.18, 0.34))):
		base = (x + fx * s, y, z + 0.2 * s)
		mid = (x + fx * 1.15 * s, y, z + (0.2 + h * 0.65) * s)
		tip = (x + fx * 1.1 * s, y - curl * 0.25 * s, z + (0.2 + h * (0.95 - curl * 0.35)) * s)
		p.seg(base, mid, 0.065 * s, 0.055 * s, swatch, sides=6, glow=glow)
		p.seg(mid, tip, 0.055 * s, 0.03 * s, swatch, sides=5, glow=glow)
	p.seg((x - 0.22 * s, y, z - 0.05 * s), (x - 0.42 * s, y - curl * 0.15 * s, z + 0.2 * s), 0.07 * s, 0.045 * s, swatch, sides=6, glow=glow)
	p.seg((x, y, z - 0.2 * s), (x, y, z - 0.6 * s), 0.17 * s, 0.2 * s, swatch, sides=8, glow=glow)          # the wrist


def _bolt_line(p, pts, r, swatch, glow, y=0.0):
	for a, b in zip(pts, pts[1:]):
		p.seg((a[0], y, a[1]), (b[0], y, b[1]), r, r * 0.8, swatch, sides=5, glow=glow)


def mud_spit():
	p = Prop("mud_spit", 807)
	p.seg((0.1, 0, 0.1), (0.15, 0, 0.8), 0.18, 0.2, HIDE, sides=8, grad=(0.4, 0.9))          # a leg in a boot
	p.seg((0.15, 0, 0.78), (0.16, 0, 0.9), 0.22, 0.22, WOOD, sides=8)                       # its cuff
	p.seg((0.16, 0, 0.9), (0.18, 0, 1.15), 0.2, 0.19, CLOTH_RED, sides=8, grad=(0.3, 0.9))   # a trouser leg
	p.blob((0.5, 0.26, 0.2), (-0.05, 0, 0.1), HIDE, segs=(8, 5))
	for x, z, s in ((0.12, 0.2, 0.62), (0.0, 0.45, 0.5), (0.25, 0.4, 0.4), (-0.15, 0.12, 0.45)):   # plastered in brown mud
		p.blob((s, s * 0.8, s * 0.7), (x, -0.08, z), WOOD, segs=(8, 6), jitter=0.03)
	for k, (x, z, s) in enumerate(((-0.75, 1.05, 0.3), (-0.5, 0.9, 0.22), (-0.3, 0.78, 0.16))):   # the gob flying in
		p.blob((s, s, s * 0.85), (x, -0.1, z), WOOD, segs=(8, 6))
	for k in range(4):                                                                    # splatter
		a = math.radians(-20 + k * 50)
		p.blob((0.1, 0.08, 0.1), (0.12 + math.cos(a) * 0.55, -0.15, 0.3 + math.sin(a) * 0.45), CLAY, segs=(6, 4))
	for k in range(3):                                                                    # slow: heavy drips
		_drop(p, -0.15 + k * 0.25, -0.1, 0.22, WOOD, 0.0)
	return p.build()


def bog_bolt():
	p = Prop("bog_bolt", 809)
	p.blob((0.7, 0.62, 0.66), (0.35, 0, 0.5), WOOD_GRAY, segs=(12, 8), jitter=0.02)          # a ball of murky bogwater
	p.blob((0.5, 0.4, 0.48), (0.35, -0.12, 0.52), (6, 1), segs=(10, 6), glow=1.2)             # glowing sickly through it
	for k in range(5):                                                                    # a spattering trail
		t = k / 4
		p.blob((0.2 - t * 0.1,) * 3, (-0.1 - t * 0.7, 0, 0.62 + t * 0.25), WOOD_GRAY, segs=(6, 4))
	for k in range(3):                                                                    # its stench
		x = 0.1 + k * 0.22
		pts = [(x, 0.95), (x + 0.08, 1.08), (x - 0.04, 1.2), (x + 0.06, 1.32)]
		_bolt_line(p, pts, 0.035, (6, 1), 1.6, y=-0.1)
	for (x, z) in ((0.2, 0.62), (0.5, 0.4), (0.45, 0.7)):                                 # bubbles on its skin
		p.blob((0.1, 0.06, 0.1), (x, -0.34, z), STONE_LIGHT, segs=(6, 4))
	return p.build()


def eel_shock():
	p = Prop("eel_shock", 811)
	pts = [(-0.7, 0.3), (-0.4, 0.55), (-0.1, 0.35), (0.2, 0.15), (0.5, 0.35), (0.7, 0.6)]   # a writhing eel
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		r = 0.13 - i * 0.018
		p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), r + 0.01, r, PINE, sides=8)
	p.blob((0.3, 0.24, 0.24), (-0.72, 0, 0.3), PINE, segs=(8, 6))
	p.blob((0.07, 0.04, 0.07), (-0.8, -0.12, 0.35), GOLD, segs=(6, 4), glow=2.0)
	for (x, z) in ((-0.45, 0.9), (0.15, 0.7), (0.55, 0.95), (-0.1, -0.1), (0.45, -0.05)):   # crackling off it
		pts = [(x - 0.12, z + 0.2), (x + 0.05, z + 0.05), (x - 0.05, z - 0.02), (x + 0.1, z - 0.2)]
		_bolt_line(p, pts, 0.04, GOLD, 2.8, y=-0.15)
	for (x, z) in ((-0.2, 1.15), (0.3, 1.2)):                                               # stunned stars
		for k in range(4):
			a = k * math.pi / 4
			p.seg((x - math.cos(a) * 0.1, -0.2, z - math.sin(a) * 0.1), (x + math.cos(a) * 0.1, -0.2, z + math.sin(a) * 0.1), 0.03, 0.03,
				  CLOTH_WHITE, sides=4, glow=2.0)
	return p.build()


def bogwing_sting():
	p = Prop("bogwing_sting", 813)
	for sx, sw in ((-1, SEAFOAM), (1, AQUA)):                                             # veined wings at the top
		p.blob((0.95, 0.04, 0.24), (-0.3 + sx * 0.05, 0.1, 1.05 + sx * 0.1), sw, rot=(0, sx * 18, 0), segs=(10, 4), glow=0.4)
	pts = [(-0.55, 0.95), (-0.3, 0.75), (-0.05, 0.55), (0.18, 0.38), (0.36, 0.22)]           # a bogwing's banded tail
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		r = 0.2 - i * 0.03
		p.blob((r * 2.4, r * 1.8, r * 1.8), ((a[0] + b[0]) / 2, 0, (a[1] + b[1]) / 2), AQUA if i % 2 else STONE_DARK,
			   rot=(0, 38, 0), segs=(10, 6))
	p.seg((0.36, 0, 0.22), (0.62, -0.05, -0.05), 0.08, 0.0, STONE_DARK, sides=6)             # the sting
	for k in range(3):                                                                    # venom dripping
		_drop(p, 0.64 - k * 0.02, -0.2 - k * 0.24, 0.3 - k * 0.05, SEAFOAM, 2.2)
	p.blob((0.45, 0.2, 0.3), (-0.4, -0.2, 0.05), CLOTH_RED, segs=(10, 6), glow=0.8)          # and the swelling it leaves
	p.blob((0.1, 0.06, 0.1), (-0.4, -0.32, 0.12), SEAFOAM, segs=(6, 4), glow=2.0)
	return p.build()


def hex_of_rot():
	p = Prop("hex_of_rot", 815)
	for k in range(7):                                                                    # a witch's sedge doll
		x = -0.12 + k * 0.04
		p.seg((x * 0.6, 0, 0.95), (x * 2.2, 0, 0.0), 0.035, 0.025, PINE if k % 2 else WOOD_GRAY, sides=4)
	p.blob((0.34, 0.24, 0.34), (0, 0, 0.92), PINE, segs=(8, 6))
	for sx in (-1, 1):
		p.seg((0, -0.02, 0.65), (sx * 0.42, -0.02, 0.48), 0.04, 0.03, PINE, sides=4)
		p.blob((0.08, 0.04, 0.08), (sx * 0.08, -0.16, 0.95), (6, 1), segs=(6, 4), glow=2.4)   # sickly eyes
	p.seg((0, 0, 0.72), (0, 0, 0.77), 0.12, 0.12, CLOTH_RED, sides=6)
	p.seg((0.6, -0.3, 0.9), (-0.25, 0.2, 0.45), 0.04, 0.0, BONE, sides=5)                      # a thorn driven through
	_ring_at(p, 0, 0.5, 0.72, 0.035, (6, 1), glow=1.6, sides=20, y=0.15)                   # the hex round it
	for k in range(4):                                                                    # rot dripping off
		_drop(p, -0.3 + k * 0.2, -0.05 - (k % 2) * 0.15, 0.22, (6, 1), 1.8)
	return p.build()


def mire_grip():
	p = Prop("mire_grip", 817)
	p.blob((1.8, 1.1, 0.14), (0, 0, 0.0), WOOD, segs=(14, 5), grad=(0.3, 0.9))              # a bog pool
	for k in range(6):                                                                    # bubbles in it
		a = k * 1.05
		p.blob((0.1, 0.1, 0.07), (math.cos(a) * 0.65, math.sin(a) * 0.35, 0.07), WOOD_GRAY, segs=(6, 4))
	for x, lean, s in ((-0.35, 12, 0.85), (0.35, -12, 0.95)):                             # muddy hands rising, clutching
		_hand(p, x, 0.72 * s, s, WOOD_GRAY, curl=1.0)
	for x in (-0.35, 0.35):                                                               # dripping with muck
		p.blob((0.12, 0.08, 0.12), (x + 0.1, -0.15, 0.35), WOOD, segs=(6, 4))
	return p.build()


def undertow():
	p = Prop("undertow", 819)
	_swirl(p, 0, 0.5, 0.08, 0.72, 2.2, WATER, 1.0, thick=0.08, steps=36)                   # a whirling current
	for k in range(3):                                                                    # pulling downward
		x = -0.35 + k * 0.35
		p.seg((x, -0.2, 0.55), (x, -0.2, 0.05), 0.04, 0.04, CLOTH_WHITE, sides=5, glow=1.4)
		p.seg((x, -0.2, 0.12), (x, -0.2, -0.12), 0.12, 0.0, CLOTH_WHITE, sides=4, glow=1.4)
	for k in range(5):                                                                    # foam
		a = k * 1.3
		p.blob((0.1, 0.06, 0.1), (math.cos(a) * 0.62, -0.15, 0.5 + math.sin(a) * 0.62), CLOTH_WHITE, segs=(6, 4), glow=0.6)
	return p.build()


def naga_venom():
	p = Prop("naga_venom", 821)
	p.blob((0.8, 0.5, 0.45), (-0.2, 0, 0.85), AQUA, segs=(12, 8), grad=(0.0, 0.8))            # a serpent's head, striking
	p.seg((-0.55, 0, 0.8), (-0.8, 0, 0.3), 0.2, 0.18, AQUA, sides=8)                         # its neck
	p.seg((0.0, 0, 0.72), (0.3, 0, 0.66), 0.14, 0.06, AQUA, sides=7)                         # lower jaw, gaping
	for sx in (-1, 1):
		p.blob((0.12, 0.06, 0.08), (-0.1, sx * 0.12 - 0.1, 0.98), GOLD, segs=(6, 4), glow=2.0)  # slit eyes
	p.blob((0.4, 0.3, 0.06), (-0.05, 0, 1.05), GOLD, segs=(8, 4))                            # a gold crest scale
	for dx in (0.0, 0.12):                                                                # long fangs
		p.seg((0.08 + dx, -0.08, 0.72), (0.12 + dx, -0.1, 0.38), 0.05, 0.0, BONE, sides=5)
	for k in range(3):                                                                    # venom dripping
		_drop(p, 0.14 + k * 0.03, 0.2 - k * 0.28, 0.3 - k * 0.04, SEAFOAM, 2.2)
	return p.build()


def tidal_bolt():
	p = Prop("tidal_bolt", 823)
	wave = [(-0.8, 0.0), (0.8, 0.0), (0.6, 0.15), (0.3, 0.3), (0.12, 0.5), (0.28, 0.66), (0.42, 0.62), (0.52, 0.72), (0.4, 0.92),
			(0.15, 1.05), (-0.2, 1.0), (-0.45, 0.8), (-0.62, 0.5), (-0.75, 0.22)]              # a wave rearing to break
	icons._slab(p, wave, -0.08, 0.08, WATER, grad=(0.0, 0.8))
	for (x, z, s) in ((0.3, 0.98, 0.13), (0.45, 0.85, 0.12), (0.1, 1.07, 0.14), (-0.15, 1.04, 0.13), (0.5, 0.7, 0.1),
					  (-0.4, 0.86, 0.12), (0.38, 0.62, 0.08)):                              # white foam along its crest
		p.blob((s, s, s), (x, -0.12, z), CLOTH_WHITE, segs=(8, 5), glow=0.8)
	for k in range(3):                                                                    # the lines of its face
		pts = [(-0.55 + k * 0.2, 0.15), (-0.45 + k * 0.2, 0.45 - k * 0.05), (-0.25 + k * 0.18, 0.72 - k * 0.12)]
		for a, b in zip(pts, pts[1:]):
			p.seg((a[0], -0.1, a[1]), (b[0], -0.1, b[1]), 0.03, 0.03, (2, 1), sides=4, glow=0.6)
	for k in range(4):                                                                    # spray flung ahead
		p.blob((0.07, 0.07, 0.07), (0.62 + k * 0.1, -0.12, 0.6 - k * 0.14), CLOTH_WHITE, segs=(5, 3), glow=1.2)
	return p.build()


def lightning_lash():
	p = Prop("lightning_lash", 825)
	for x, z, s in ((-0.55, 1.0, 0.5), (-0.25, 1.05, 0.45), (-0.4, 1.2, 0.42)):            # a tempest spirit's wisp
		p.blob((s, s * 0.7, s * 0.6), (x, 0.1, z), (2, 1), segs=(8, 6), glow=0.4)
	pts = []                                                                              # a whip of lightning, cracking down
	for k in range(12):
		t = k / 11
		pts.append((-0.4 + t * 1.1 + math.sin(t * 7) * 0.08 * (1 - t), 0.9 - t * 0.9 + math.sin(t * 5.5) * 0.25))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		r = 0.075 - i * 0.004
		p.seg((a[0], -0.05, a[1]), (b[0], -0.05, b[1]), r, r * 0.9, CLOTH_WHITE, sides=5, glow=3.0)
		p.seg((a[0], 0.02, a[1]), (b[0], 0.02, b[1]), r * 1.6, r * 1.5, RUNE, sides=5, glow=1.6)
	end = pts[-1]
	for k in range(6):                                                                    # the crack where it lands
		a = k * math.tau / 6 + 0.2
		p.seg((end[0], -0.1, end[1]), (end[0] + math.cos(a) * 0.3, -0.1, end[1] + math.sin(a) * 0.3), 0.04, 0.0, GOLD, sides=4, glow=2.6)
	return p.build()


def crushing_claw():
	p = Prop("crushing_claw", 827)
	p.blob((0.7, 0.45, 0.5), (-0.4, 0, 0.45), CLOTH_RED, segs=(12, 8), grad=(0.0, 0.8))      # a great crab claw
	pts = [(-0.12, 0.6), (0.2, 0.72), (0.45, 0.65), (0.55, 0.48)]                          # snapping shut
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), 0.19 - i * 0.05, 0.14 - i * 0.05, CLOTH_RED, sides=8, grad=(0.0, 0.7))
	pts = [(-0.12, 0.3), (0.2, 0.22), (0.42, 0.3), (0.52, 0.44)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg((a[0], 0, a[1]), (b[0], 0, b[1]), 0.15 - i * 0.04, 0.11 - i * 0.04, CLOTH_RED, sides=8, grad=(0.0, 0.7))
	for k in range(7):                                                                    # the crunch
		a = math.radians(-60 + k * 20)
		p.seg((0.55 + math.cos(a) * 0.15, -0.2, 0.46 + math.sin(a) * 0.15), (0.55 + math.cos(a) * 0.5, -0.2, 0.46 + math.sin(a) * 0.5),
			  0.05, 0.0, FLAME, sides=4, glow=2.4)
	for (x, z) in ((-0.5, 0.62), (-0.3, 0.3)):                                            # barnacles
		p.seg((x, -0.18, z), (x, -0.26, z), 0.05, 0.025, STONE_LIGHT, sides=6)
	return p.build()


def drowning_grasp():
	p = Prop("drowning_grasp", 829)
	_hand(p, 0.0, 0.45, 1.25, WATER, glow=1.2, curl=0.8)                                   # a hand of seawater, closing
	for k in range(6):                                                                    # the last breath bubbling away
		x = -0.45 + (k % 3) * 0.12 + (k // 3) * 0.7
		z = 0.75 + (k % 3) * 0.2
		p.blob((0.1 + (k % 3) * 0.03,) * 3, (x, -0.25, z), CLOTH_WHITE, segs=(8, 5), glow=0.6)
	_ring_at(p, 0, 0.1, 0.62, 0.04, WATER, glow=0.8, sides=16, a0=math.pi, a1=math.tau, y=-0.1)   # rising water
	return p.build()


def cobra_venom():
	p = Prop("cobra_venom", 831)
	body = (AMBER, (0.4, 0.95))
	for z, r, k0 in ((0.06, 0.5, 0), (0.2, 0.38, 3)):                                   # a hooded cobra, coiled
		pts = [(math.cos(a) * r, math.sin(a) * r * 0.7, z + math.sin(a) * 0.02) for a in [k0 * 0.3 + k * math.tau / 16 for k in range(17)]]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.12, 0.12, body[0], sides=7, grad=body[1])
	neck = [(0.2, 0, 0.28), (0.1, 0, 0.55), (-0.05, 0, 0.8), (-0.02, 0, 0.95)]             # rearing up
	for a, b in zip(neck, neck[1:]):
		p.seg(a, b, 0.13, 0.12, body[0], sides=8, grad=body[1])
	hood = []
	for k in range(24):                                                                   # its spread hood, narrowing to the neck
		t = k * math.tau / 24
		z = 0.93 + math.cos(t) * 0.38
		hood.append((math.sin(t) * 0.5 * (0.45 + 0.55 * (z - 0.55) / 0.76) ** 0.6, z))
	icons._slab(p, [(x - 0.04, z) for x, z in hood], 0.04, 0.1, body[0], grad=(0.5, 1.0))
	for a, b in zip(hood, hood[1:] + hood[:1]):                                           # edged dark
		p.seg((a[0] - 0.04, 0.02, a[1]), (b[0] - 0.04, 0.02, b[1]), 0.035, 0.035, WOOD, sides=4, grad=(0.6, 1.0))
	for sx in (-1, 1):                                                                    # dark eye marks on the hood
		p.blob((0.16, 0.04, 0.2), (sx * 0.3 - 0.04, 0.0, 0.95), WOOD, segs=(8, 5), grad=(0.6, 1.0))
		p.blob((0.07, 0.04, 0.09), (sx * 0.3 - 0.04, -0.02, 0.95), AMBER, segs=(6, 4), grad=(0.0, 0.3))
	for k in range(3):                                                                    # pale throat bands
		z = 0.66 + k * 0.1
		p.seg((-0.13, -0.08, z), (0.11, -0.08, z + 0.01), 0.03, 0.03, BONE, sides=4)
	p.seg((-0.02, 0, 0.95), (0.18, -0.2, 1.2), 0.12, 0.11, body[0], sides=8, grad=(0.1, 0.6))   # the head thrust out from the hood
	p.blob((0.44, 0.34, 0.26), (0.26, -0.26, 1.26), body[0], rot=(0, -15, 0), segs=(12, 8), grad=(0.0, 0.5))
	p.seg((0.26, -0.3, 1.12), (0.56, -0.36, 1.02), 0.1, 0.04, body[0], sides=6, grad=(0.3, 0.7))   # lower jaw, gaping
	p.blob((0.24, 0.08, 0.08), (0.4, -0.36, 1.14), CLOTH_RED, segs=(6, 4))                     # the mouth
	for sy in (-1, 1):
		p.blob((0.1, 0.05, 0.08), (0.24, -0.26 + sy * 0.13, 1.34), GOLD, segs=(6, 4), glow=2.0)   # slit eyes
	for dx in (0.0, 0.1):                                                                 # fangs
		p.seg((0.4 + dx, -0.36, 1.2), (0.42 + dx, -0.38, 1.02), 0.035, 0.0, BONE, sides=5)
	for k in range(3):                                                                    # green venom dripping
		_drop(p, 0.52 + k * 0.05, 0.8 - k * 0.26, 0.28 - k * 0.05, LEAF, 2.2)
	for k in range(4):                                                                    # and spat ahead
		p.blob((0.07, 0.06, 0.07), (0.72 + k * 0.1, -0.36, 1.1 - k * 0.05), LEAF, segs=(5, 3), glow=2.0)
	return p.build()


# ---------------------------------------------------------------- level 35 and the Forgehold / glass-country monsters

def _star(p, cx, cz, r, swatch, glow=2.2, y=0.0, points=5, inner=0.42, spin=90.0):
	"""A pointed star standing in the picture plane."""
	p.blob((r * 0.9, 0.12 * r / 0.3, r * 0.9), (cx, y, cz), swatch, segs=(10, 6), glow=glow)
	for k in range(points):
		a = math.radians(spin) + k * math.tau / points
		p.seg((cx + math.cos(a) * r * inner, y, cz + math.sin(a) * r * inner), (cx + math.cos(a) * r * 1.35, y, cz + math.sin(a) * r * 1.35),
			  r * 0.34, 0.0, swatch, sides=4, glow=glow)


def _heart(p, cx, cz, s, swatch=CLOTH_RED, y=0.0, depth=0.16, rim=None, glow=0.0):
	"""A heart in the picture plane, s = its half width."""
	outline = []
	for k in range(32):
		t = k * math.tau / 32
		x = 16 * math.sin(t) ** 3
		z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
		outline.append((cx + x / 16 * s, cz + z / 16 * s))
	icons._slab(p, outline, y - depth / 2, y + depth / 2, swatch, grad=(0.1, 0.7))
	p.blob((s * 0.7, depth * 0.9, s * 0.55), (cx - s * 0.35, y - depth * 0.2, cz + s * 0.25), swatch, segs=(8, 5), grad=(0.0, 0.4))  # a round front
	if rim:
		for a, b in zip(outline, outline[1:] + outline[:1]):
			p.seg((a[0], y - depth * 0.6, a[1]), (b[0], y - depth * 0.6, b[1]), 0.03, 0.03, rim, sides=4, glow=glow)


def _shard(p, base, tip, w, swatch, glow=0.0, y=0.0, grad=(0.1, 0.8)):
	"""A four-sided splinter of glass or crystal from base to its point."""
	p.seg((base[0], y, base[1]), (tip[0], y, tip[1]), w, 0.0, swatch, sides=4, glow=glow, grad=grad)
	d = Vector((tip[0] - base[0], 0, tip[1] - base[1]))
	p.seg((base[0], y, base[1]), (base[0] - d.x * 0.25, y, base[1] - d.z * 0.25), w, 0.0, swatch, sides=4, glow=glow, grad=grad)


def _fangs(p, cx, cz, w, gap, n, swatch, length=0.22, glow=0.0, y=-0.1):
	"""Two rows of fangs biting shut on (cx, cz): an upper jaw's pointing down, a lower jaw's up."""
	for k in range(n):
		x = cx - w / 2 + w * k / max(n - 1, 1)
		big = 1.0 if k in (0, n - 1) else 0.7
		p.seg((x, y, cz + gap), (x, y, cz + gap - length * big), 0.06, 0.0, swatch, sides=5, glow=glow)
		p.seg((x, y, cz - gap), (x, y, cz - gap + length * big), 0.055, 0.0, swatch, sides=5, glow=glow)


def sundering_blow():
	p = Prop("sundering_blow", 901)
	for sx in (-1, 1):                                                                    # a breastplate, split in two
		off = sx * 0.16
		pts = [(0.0, 1.0), (0.0, 0.05), (sx * 0.25, -0.05), (sx * 0.52, 0.12), (sx * 0.62, 0.62), (sx * 0.7, 0.95), (sx * 0.35, 1.0), (sx * 0.2, 0.82)]
		outline = [(x + off, z) for x, z in pts]
		icons._slab(p, outline, -0.06 + (0.04 if sx > 0 else 0), 0.1, STONE_LIGHT, grad=(0.1, 0.6))
		p.seg((sx * 0.42 + off, -0.04, 0.7), (sx * 0.38 + off, -0.04, 0.25), 0.05, 0.05, IRON, sides=5)      # its ribbing
	for k in range(5):                                                                    # the split, torn jagged
		z0, z1 = 1.05 - k * 0.24, 1.05 - (k + 1) * 0.24
		p.seg(((-1) ** k * 0.05, -0.2, z0), ((-1) ** (k + 1) * 0.05, -0.2, z1), 0.035, 0.035, CLOTH_WHITE, sides=4, glow=2.6)
	p.seg((-0.55, -0.3, 1.35), (0.5, -0.3, -0.25), 0.05, 0.0, CLOTH_WHITE, sides=4, glow=1.8)      # the stroke that did it
	for x, z, s in ((-0.55, 0.3, 0.1), (0.62, 0.05, 0.08), (-0.4, -0.05, 0.07)):          # chips flying
		p.rock((s * 1.2, s, s), (x, -0.25, z), STONE_LIGHT, jitter=0.2)
	for x, z in ((0.55, 1.2), (0.8, 0.95)):                                               # stunned stars
		_star(p, x, z, 0.09, GOLD, glow=2.4, y=-0.3)
	return p.build()


def last_stand():
	p = Prop("last_stand", 903)
	p.blob((1.5, 0.9, 0.3), (0, 0, -0.05), STONE_DARK, segs=(12, 5))                          # a last patch of ground
	for k in range(9):                                                                    # a golden aura
		a = math.radians(10 + k * 20)
		p.seg((math.cos(a) * 0.55, 0.25, 0.25 + math.sin(a) * 0.55), (math.cos(a) * 0.95, 0.25, 0.25 + math.sin(a) * 0.95), 0.06, 0.0, GOLD, sides=4, glow=2.0)
	c = Vector((0, 0, 0.1))
	p.seg(tuple(c), tuple(c + Vector((0, 0, 0.95))), 0.09, 0.09, STONE_LIGHT, sides=4, twist=45)     # a sword driven into it
	p.seg(tuple(c), tuple(c - Vector((0, 0, 0.12))), 0.09, 0.0, STONE_LIGHT, sides=4, twist=45)
	p.box((0.62, 0.14, 0.1), (0, 0, 1.08), GOLD)
	p.seg((0, 0, 1.12), (0, 0, 1.42), 0.055, 0.055, WOOD, sides=6)
	p.blob((0.14, 0.14, 0.14), (0, 0, 1.46), GOLD, segs=(6, 4))
	p.seg((-0.35, -0.15, 0.1), (-0.35, -0.15, 0.95), 0.1, 0.1, CLOTH_RED, sides=6)          # a torn banner tied to it
	outline = [(0.0, 0.95), (-0.7, 0.9), (-0.62, 0.5), (-0.75, 0.3), (-0.45, 0.42), (-0.3, 0.2), (0.0, 0.55)]
	icons._slab(p, [(x + 0.02, z) for x, z in outline], -0.08, -0.02, CLOTH_RED, grad=(0.2, 0.7))
	p.seg((0, -0.12, 0.72), (0.0, -0.12, 0.92), 0.12, 0.12, WOOD, sides=6)
	for x, z in ((0.55, 0.62), (0.7, 0.35)):                                                # holding: +
		p.box((0.26, 0.06, 0.07), (x, -0.3, z), LEAF, glow=2.2)
		p.box((0.07, 0.06, 0.26), (x, -0.3, z), LEAF, glow=2.2)
	return p.build()


def earthshaker():
	p = Prop("earthshaker", 905)
	p.blob((2.0, 1.4, 0.18), (0, 0, 0.0), STONE_WARM, segs=(14, 5))                         # the ground
	for k, r in enumerate((0.35, 0.62, 0.9)):                                             # the quake rolling out
		_ring(p, r, 0.1 + k * 0.01, 0.035, AMBER, glow=1.8 - k * 0.3, sides=22)
	for k in range(7):                                                                    # stone thrown up in slabs
		a = k * math.tau / 7 + 0.3
		r = 0.72 + (k % 2) * 0.15
		base = (math.cos(a) * r, math.sin(a) * r * 0.8, 0.05)
		lean = 0.35
		top = (base[0] * (1 + lean), base[1] * (1 + lean), 0.45 + (k % 3) * 0.12)
		p.seg(base, top, 0.14, 0.03, STONE_DARK, sides=4, jitter=0.02)
	for x, z, s in ((-0.4, 0.95, 0.16), (0.2, 1.15, 0.12), (0.5, 0.85, 0.14), (-0.1, 1.35, 0.09)):   # and rocks flung high
		p.rock((s * 1.2, s, s), (x, -0.1, z), STONE_WARM, jitter=0.2)
	p.rock((0.5, 0.45, 0.4), (0, 0, 0.25), STONE_DARK, jitter=0.15)                           # at the heart, a stamped crater
	p.blob((0.3, 0.3, 0.1), (0, -0.05, 0.42), AMBER, segs=(8, 5), glow=2.4)
	for k in range(6):
		a = k * math.tau / 6
		p.seg((0, 0, 0.12), (math.cos(a) * 0.5, math.sin(a) * 0.4, 0.1), 0.04, 0.01, AMBER, sides=4, glow=2.2)
	return p.build()


def circle_of_dawn():
	p = Prop("circle_of_dawn", 907)
	_ring(p, 0.85, 0.0, 0.05, GOLD, glow=2.2, sides=26)                                   # a ring of dawn light on the ground
	for k in range(5):                                                                    # a friend at each point of it
		a = k * math.tau / 5 + 0.6
		x, y = math.cos(a) * 0.85, math.sin(a) * 0.85
		p.seg((x, y, 0.0), (x, y, 0.7), 0.11, 0.03, FLAME, sides=6, glow=1.4)            # a column of light rising
		p.blob((0.2, 0.2, 0.2), (x, y, 0.35), CLOTH_WHITE, segs=(8, 5), glow=1.8)
	p.seg((0, 0, 0.35), (0, 0, 0.45), 0.3, 0.3, GOLD, sides=16, glow=2.6)                   # the sun at its center...
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.32, math.sin(a) * 0.32, 0.4), (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.4), 0.05, 0.0, FLAME, sides=4, glow=2.4)
	p.box((0.16, 0.12, 0.5), (0, 0, 0.85), LEAF, glow=2.2)                                   # ...and a healing cross above
	p.box((0.4, 0.12, 0.14), (0, 0, 0.92), LEAF, glow=2.2)
	return p.build()


def dawnbreak():
	p = Prop("dawnbreak", 909)
	p.blob((1.5, 0.9, 0.14), (0, 0, 0.0), STONE_DARK, segs=(12, 4))                           # dark ground
	p.seg((0, 0.05, 1.45), (0, 0.05, 1.3), 0.34, 0.34, GOLD, sides=18, glow=2.6)            # the sun, breaking open above
	for k in range(9):
		a = math.radians(-20 + k * 27.5)
		p.seg((math.cos(a) * 0.38, 0.05, 1.38 + math.sin(a) * 0.38), (math.cos(a) * 0.62, 0.05, 1.38 + math.sin(a) * 0.62), 0.05, 0.0, FLAME, sides=4, glow=2.4)
	p.seg((0, 0, 1.2), (0, 0, 0.1), 0.1, 0.24, CLOTH_WHITE, sides=10, glow=2.4)              # a spear of light driving down
	p.seg((0, -0.02, 1.2), (0, -0.02, 0.1), 0.2, 0.36, GOLD, sides=10, glow=0.9)
	for k in range(10):                                                                   # bursting where it lands
		a = math.radians(5 + k * 19)
		p.seg((math.cos(a) * 0.3, -0.3, 0.08 + math.sin(a) * 0.2), (math.cos(a) * 0.8, -0.3, 0.08 + math.sin(a) * 0.55), 0.05, 0.0,
			  GOLD if k % 2 else CLOTH_WHITE, sides=4, glow=2.4)
	for k in range(4):                                                                    # cracks of light in the ground
		a = k * math.tau / 4 + 0.5
		p.seg((0, 0, 0.08), (math.cos(a) * 0.7, math.sin(a) * 0.45, 0.08), 0.04, 0.01, FLAME, sides=4, glow=2.2)
	return p.build()


def dawns_embrace():
	p = Prop("dawns_embrace", 911)
	for sx in (-1, 1):                                                                    # two cupped hands...
		before = len(p.parts)
		_hand(p, 0, 0, 0.75, CLOTH_WHITE, glow=0.5, curl=0.6)
		for o in p.parts[before:]:
			o.data.transform(Matrix.Rotation(math.radians(-sx * 38), 4, "Y"))
			o.data.transform(Matrix.Translation((sx * 0.38, 0, 0.1)))
	p.seg((0, 0.02, 0.72), (0, -0.05, 0.72), 0.3, 0.3, GOLD, sides=18, glow=2.8)            # ...cradling the dawn
	for k in range(10):
		a = k * math.tau / 10 + 0.2
		p.seg((math.cos(a) * 0.34, -0.02, 0.72 + math.sin(a) * 0.34), (math.cos(a) * (0.62 if k % 2 else 0.5), -0.02, 0.72 + math.sin(a) * (0.62 if k % 2 else 0.5)),
			  0.05, 0.0, FLAME, sides=4, glow=2.4)
	_ring_at(p, 0, 0.72, 0.85, 0.03, LEAF, glow=1.6, sides=24, a0=math.radians(20), a1=math.radians(160), y=0.1)   # warm, healing light
	for x, z in ((-0.62, 1.2), (0.62, 1.2), (0, 1.5)):
		p.blob((0.1, 0.1, 0.1), (x, -0.1, z), LEAF, segs=(6, 4), glow=2.4)
	return p.build()


def obsidian_lance():
	p = Prop("obsidian_lance", 913)
	a, b = Vector((-0.6, 0, 0.1)), Vector((0.6, 0, 1.1))
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(tuple(a), tuple(b), 0.3, 0.0, STONE_DARK, sides=4, twist=45)                     # a lance of black glass
	p.seg(tuple(a), tuple(a - d * 0.4), 0.3, 0.0, STONE_DARK, sides=4, twist=45)
	for k in range(4):                                                                    # molten veins down its facets
		t0, t1 = 0.0 + k * 0.2, 0.14 + k * 0.2
		w = 0.13 * (1 - t0)
		p0, p1 = a + (b - a) * t0 + n * (w if k % 2 else -w), a + (b - a) * t1 + n * (-w if k % 2 else w)
		p.seg(tuple(p0 - Vector((0, 0.2, 0))), tuple(p1 - Vector((0, 0.2, 0))), 0.04, 0.035, EMBER, sides=4, glow=2.8)
	p.seg(tuple(a - d * 0.3 - Vector((0, 0.16, 0))), tuple(b - d * 0.1 - Vector((0, 0.1, 0))), 0.025, 0.0, CLOTH_WHITE, sides=4, glow=1.4)  # a glassy glint
	p.seg(tuple(b - d * 0.25), tuple(b + d * 0.03), 0.09, 0.0, FLAME, sides=4, glow=3.0)    # its point, white-hot
	for k in range(7):                                                                    # dripping fire behind
		t = k / 6
		c = a - d * (0.45 + t * 0.4) + n * math.sin(k * 2.3) * 0.2
		s = 0.2 - t * 0.11
		p.blob((s, s, s), tuple(c), EMBER if k % 2 else FLAME, segs=(6, 4), glow=2.6)
	return p.build()

def frost_prison():
	p = Prop("frost_prison", 915)
	p.blob((1.5, 1.2, 0.16), (0, 0, -0.02), CLOTH_WHITE, segs=(12, 5))                        # frozen ground
	p.blob((0.4, 0.35, 0.45), (0, 0.05, 0.35), PURPLE, segs=(8, 6))                           # a foe, caught
	p.blob((0.3, 0.3, 0.3), (0, 0.05, 0.72), PURPLE, segs=(8, 6))
	for sx in (-1, 1):
		p.blob((0.07, 0.05, 0.05), (sx * 0.07, -0.1, 0.75), CLOTH_WHITE, segs=(5, 3), glow=2.0)
	for k in range(8):                                                                    # bars of ice all round it
		a = k * math.tau / 8 + 0.2
		x, y = math.cos(a) * 0.55, math.sin(a) * 0.45
		p.seg((x, y, 0.0), (x * 0.92, y * 0.92, 1.0), 0.09, 0.06, WATER, sides=6, glow=1.2)
		p.seg((x * 0.92, y * 0.92, 1.0), (x * 0.5, y * 0.5, 1.28), 0.06, 0.0, WATER, sides=5, glow=1.4)
	_ring(p, 0.55, 0.05, 0.07, WATER, glow=1.0, sides=16)
	_ring(p, 0.51, 1.0, 0.05, CLOTH_WHITE, glow=1.4, sides=16)
	for x, z in ((-0.7, 1.05), (0.72, 0.7)):
		_snowflake(p, x, z, 0.18, 1.8)
	return p.build()


def starfall():
	p = Prop("starfall", 917)
	p.blob((1.7, 1.0, 0.12), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	for k in range(5):                                                                    # a blue burst on the ground
		a = k * math.tau / 5 + 0.3
		p.seg((0.15, 0, 0.06), (0.15 + math.cos(a) * 0.6, math.sin(a) * 0.4, 0.06), 0.04, 0.01, RUNE, sides=4, glow=2.0)
	for x, z, r, trail in ((-0.55, 1.15, 0.17, 0.55), (0.1, 0.55, 0.22, 0.7), (0.62, 1.2, 0.13, 0.45), (-0.2, 0.28, 0.12, 0.35)):  # stars falling
		_star(p, x, z, r, CLOTH_WHITE if r > 0.15 else GOLD, glow=2.6, y=-0.1)
		p.seg((x - 0.06, 0.05, z + r), (x - trail * 0.35, 0.05, z + trail), r * 0.55, 0.0, RUNE, sides=6, glow=1.8)   # their blue tails
	return p.build()


def throat_cut():
	p = Prop("throat_cut", 919)
	pts = [(math.cos(a) * 0.8, 0, 0.35 + math.sin(a) * 0.35) for a in [math.radians(200 + k * 17) for k in range(9)]]   # the cut: a red crescent
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		w = 0.1 * math.sin(math.pi * (i + 0.5) / 8) + 0.01
		p.seg(a, b, w, w, CRIMSON, sides=5, glow=1.8)
	for x, z, s in ((-0.3, -0.25, 0.22), (0.05, -0.35, 0.26), (0.35, -0.2, 0.2)):          # spilling
		_drop(p, x, z - 0.1, s, CLOTH_RED, 1.0)
	for k in range(9):                                                                    # a curved knife that made it
		t = k / 8
		a = math.radians(160 - t * 90)
		c = (0.55 + math.cos(a) * 0.55, -0.15, 0.4 + math.sin(a) * 0.55)
		c2 = (0.55 + math.cos(a - 0.2) * 0.55, -0.15, 0.4 + math.sin(a - 0.2) * 0.55)
		p.seg(c, c2, 0.07 * (1 - t) + 0.015, 0.07 * (1 - t * 0.9), STONE_LIGHT, sides=4)
	hilt = (0.55 + math.cos(math.radians(160)) * 0.55, -0.15, 0.4 + math.sin(math.radians(160)) * 0.55)
	p.seg((hilt[0] + 0.02, -0.15, hilt[2] - 0.12), (hilt[0] - 0.02, -0.15, hilt[2] + 0.12), 0.04, 0.04, GOLD, sides=5)
	p.seg(hilt, (hilt[0] - 0.3, -0.15, hilt[2] - 0.1), 0.05, 0.05, WOOD, sides=6)
	for x, z in ((-0.55, 1.05), (-0.2, 1.2)):                                              # reeling
		_star(p, x, z, 0.09, GOLD, glow=2.4, y=-0.2)
	return p.build()


def shadow_dance():
	p = Prop("shadow_dance", 921)
	_swirl(p, 0, 0.6, 0.12, 0.85, 1.3, PURPLE, 1.4, thick=0.14, steps=34)                  # a whirl of shadow
	for k, (a, g) in enumerate(((0.3, 0.0), (2.4, 0.0), (4.4, 0.0))):                      # blades dancing round it
		base = (math.cos(a) * 0.25, -0.1, 0.6 + math.sin(a) * 0.25)
		tip = (math.cos(a + 0.5) * 0.9, -0.1, 0.6 + math.sin(a + 0.5) * 0.9)
		_dagger(p, base, tip, w=0.1, edge=PETAL_PURPLE)
		for j in (1, 2):                                                                 # each trailing afterimages
			aj = a - j * 0.28
			b2 = (math.cos(aj) * 0.25, 0.05 + j * 0.05, 0.6 + math.sin(aj) * 0.25)
			t2 = (math.cos(aj + 0.5) * 0.9, 0.05 + j * 0.05, 0.6 + math.sin(aj + 0.5) * 0.9)
			p.seg(b2, t2, 0.07 - j * 0.015, 0.0, PURPLE, sides=4, glow=1.6 - j * 0.4)
	p.blob((0.22, 0.2, 0.22), (0, -0.1, 0.6), STONE_DARK, segs=(8, 5))
	p.blob((0.1, 0.06, 0.06), (0, -0.2, 0.62), PETAL_PURPLE, segs=(6, 4), glow=3.0)
	return p.build()


def heartseeker():
	p = Prop("heartseeker", 923)
	for x, z, s in ((0.3, 0.8, 0.7), (-0.35, 0.35, 0.6), (0.4, 0.2, 0.55)):                # the shadows it came out of
		p.blob((s, s * 0.6, s), (x, 0.4, z), PURPLE, segs=(10, 6), glow=0.4)
	_heart(p, 0, 0.55, 0.52, CLOTH_RED, y=0.0, rim=CRIMSON, glow=1.6)                       # a heart
	_dagger(p, (0.85, 0.3, 1.25), (-0.55, -0.4, 0.05), w=0.1, edge=CLOTH_WHITE)             # run through from behind, the point out the front
	for k in range(3):
		_drop(p, -0.45 + k * 0.14, -0.1 - k * 0.12, 0.16, CLOTH_RED, 0.8)
	return p.build()


def forgefire_mantle():
	p = Prop("forgefire_mantle", 925)
	for x, s in ((-0.55, 0.75), (0.55, 0.8), (0.0, 1.05)):                                # forge fire rising behind
		_fl(p, x, 0.45, 0.45, s, glow=2.0)
	for sx in (-1, 1):                                                                    # a great mantle of plate: two pauldrons
		for k in range(3):
			z = 0.78 - k * 0.2
			w = 0.62 - k * 0.06
			p.blob((w, 0.62, 0.3), (sx * (0.4 + k * 0.07), 0, z), STONE_LIGHT, rot=(0, sx * (18 + k * 12), 0), segs=(12, 6), grad=(0.1, 0.55))
			p.seg((sx * (0.14 + k * 0.07), -0.3, z - 0.02 - k * 0.02), (sx * (0.66 + k * 0.07), -0.3, z - 0.14 - k * 0.07), 0.035, 0.035, GOLD, sides=4, glow=0.8)
		p.blob((0.13, 0.1, 0.13), (sx * 0.42, -0.34, 0.84), EMBER, segs=(6, 4), glow=2.8)    # rivets glowing hot
	p.seg((0, 0.05, 0.45), (0, 0.05, 0.8), 0.24, 0.22, IRON, sides=10)                   # a gorget between them
	p.seg((0, 0.03, 0.8), (0, 0.03, 0.88), 0.25, 0.25, GOLD, sides=10, glow=0.8)
	p.blob((0.2, 0.1, 0.2), (0, -0.2, 0.6), EMBER, segs=(8, 5), glow=2.6)                    # a forge-gem at the collar
	return p.build()


def forge_flare():
	p = Prop("forge_flare", 927)
	for k in range(9):                                                                    # a stone forge mouth
		a = math.radians(k * 22.5)
		p.box((0.24, 0.5, 0.18), (-0.45 + math.cos(a) * 0.42, 0.1, 0.35 + math.sin(a) * 0.42), STONE_DARK, rot=(0, -math.degrees(a) + 90, 0))
	p.box((1.1, 0.6, 0.2), (-0.45, 0.1, -0.02), STONE_DARK)
	p.blob((0.6, 0.3, 0.5), (-0.45, 0.25, 0.4), EMBER, segs=(10, 6), glow=2.6)                # its heart, glowing
	for k in range(8):                                                                    # a gout of white-hot flame
		t = k / 7
		x = -0.35 + t * 1.3
		z = 0.42 + t * 0.35
		s = 0.22 + t * 0.3
		sw = CLOTH_WHITE if t < 0.3 else (FLAME if t < 0.75 else EMBER)
		p.blob((s, s * 0.8, s * 0.85), (x, -0.1 - t * 0.1, z + math.sin(k * 1.9) * 0.05), sw, segs=(8, 6), glow=3.0 - t)
	for k in range(5):                                                                    # sparks
		p.blob((0.06, 0.06, 0.06), (0.1 + k * 0.2, -0.3, 1.0 + (k % 2) * 0.15 - k * 0.05), GOLD, segs=(5, 3), glow=3.0)
	return p.build()


def elemental_tempest():
	p = Prop("elemental_tempest", 929)
	p.blob((0.34, 0.3, 0.34), (0, -0.05, 0.55), CLOTH_WHITE, segs=(10, 6), glow=3.0)          # where they meet
	for k in range(8):
		a = k * math.tau / 8 + 0.2
		p.seg((math.cos(a) * 0.18, -0.1, 0.55 + math.sin(a) * 0.18), (math.cos(a) * 0.38, -0.1, 0.55 + math.sin(a) * 0.38), 0.04, 0.0, GOLD, sides=4, glow=2.6)
	corners = ((-0.75, 1.25), (0.75, 1.25), (-0.75, -0.15), (0.75, -0.15))
	for (x, z), kind in zip(corners, ("fire", "water", "earth", "air")):                   # the four elements, converging
		c = Vector((x, 0, z))
		d = (Vector((0, 0, 0.55)) - c).normalized()
		tail = c - d * 0.1
		head = c + d * 0.5
		if kind == "fire":
			_fl(p, x, 0, z - 0.2, 0.42, glow=2.2)
			p.seg(tuple(head), tuple(c), 0.04, 0.12, FLAME, sides=5, glow=1.8)
		elif kind == "water":
			_drop(p, x, z - 0.15, 0.55, WATER, 1.4)
			p.seg(tuple(head), tuple(c), 0.04, 0.12, WATER, sides=5, glow=1.4)
		elif kind == "earth":
			p.rock((0.4, 0.36, 0.34), (x, 0, z), STONE_WARM, jitter=0.12)
			p.seg(tuple(head), tuple(c), 0.04, 0.12, STONE_WARM, sides=5, glow=0.3)
		else:
			_swirl(p, x, z, 0.04, 0.26, 1.5, CLOTH_WHITE, 1.4, thick=0.08, steps=18)
			p.seg(tuple(head), tuple(c), 0.04, 0.1, CLOTH_WHITE, sides=5, glow=1.2)
	return p.build()


def wither():
	p = Prop("wither", 931)
	p.blob((1.2, 0.8, 0.14), (0, 0, 0.0), WOOD, segs=(10, 4))                                 # dead earth
	stem = [(0.0, 0, 0.05), (0.05, 0, 0.45), (0.0, 0, 0.8), (-0.2, 0, 1.0), (-0.45, 0, 0.95), (-0.55, 0, 0.75)]   # a flower bowed over
	for i, (a, b) in enumerate(zip(stem, stem[1:])):
		p.seg(a, b, 0.05, 0.045, SICKLY if i < 2 else WOOD, sides=6)
	for k in range(5):                                                                    # its head, browned and shedding
		a = math.radians(-60 + k * 30)
		c = (-0.55, -0.05, 0.72)
		p.blob((0.12, 0.06, 0.28), (c[0] + math.sin(a) * 0.18, c[1], c[2] - math.cos(a) * 0.18), WOOD if k % 2 else CLAY,
			   rot=(0, -math.degrees(a), 0), segs=(6, 4))
	p.blob((0.14, 0.14, 0.14), (-0.55, -0.1, 0.72), STONE_DARK, segs=(6, 4))
	for x, z, ang in ((0.35, 0.35, 30), (-0.25, 0.3, -50)):                                 # leaves curling dry
		p.blob((0.34, 0.06, 0.12), (x, 0, z), WOOD, rot=(0, ang, 0), segs=(8, 4))
	for x, z in ((-0.7, 0.3), (-0.35, 0.18)):                                              # fallen petals
		p.blob((0.12, 0.06, 0.05), (x, -0.1, z), CLAY, rot=(0, 30, 0), segs=(6, 3))
	for k in range(6):                                                                    # a sickly rot in the air
		a = k * 1.05
		p.blob((0.08, 0.08, 0.08), (math.cos(a) * 0.55 + 0.1, -0.2, 0.7 + math.sin(a) * 0.45), SICKLY, segs=(5, 3), glow=2.4)
	_swirl(p, 0.25, 0.75, 0.05, 0.4, 1.2, SICKLY, 1.6, thick=0.05, steps=20)
	return p.build()


def grave_pact():
	p = Prop("grave_pact", 933)
	p.blob((1.5, 0.9, 0.14), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	outline = [(-0.42, 0.0), (0.42, 0.0), (0.42, 0.85)] + [(math.cos(a) * 0.42, 0.85 + math.sin(a) * 0.35) for a in [k * math.pi / 8 for k in range(1, 8)]] + [(-0.42, 0.85)]
	icons._slab(p, outline, -0.08, 0.14, STONE_LIGHT, grad=(0.1, 0.6))                     # a gravestone
	_ring_at(p, 0, 0.62, 0.26, 0.03, PETAL_PURPLE, glow=2.6, sides=18, y=-0.12)             # sealed with a glowing sigil
	for k in range(3):
		a0 = math.radians(90 + k * 120)
		a1 = a0 + math.radians(120) * 2
		p.seg((math.cos(a0) * 0.26, -0.12, 0.62 + math.sin(a0) * 0.26), (math.cos(a1) * 0.26, -0.12, 0.62 + math.sin(a1) * 0.26), 0.025, 0.025, PETAL_PURPLE, sides=4, glow=2.6)
	for sx in (-1, 1):                                                                    # two bony hands clasping over it
		pts = [(sx * 0.8, -0.2, 0.2), (sx * 0.55, -0.25, 0.8), (sx * 0.12, -0.3, 1.05)]
		for a, b in zip(pts, pts[1:]):
			_bone(p, a, b, 0.05)
		p.blob((0.2, 0.14, 0.16), (sx * 0.05, -0.32, 1.08), BONE, segs=(8, 5))
		for d in (-0.05, 0.03, 0.1):
			p.seg((sx * 0.05, -0.32, 1.08 + d), (-sx * 0.14, -0.35, 1.1 + d), 0.03, 0.02, BONE, sides=4)
	for k in range(5):                                                                    # a pact struck in violet light
		a = math.radians(30 + k * 30)
		p.seg((math.cos(a) * 0.22, -0.35, 1.1 + math.sin(a) * 0.22), (math.cos(a) * 0.42, -0.35, 1.1 + math.sin(a) * 0.42), 0.035, 0.0, PURPLE, sides=4, glow=2.4)
	return p.build()


def devour_soul():
	p = Prop("devour_soul", 935)
	p.blob((0.95, 0.6, 1.0), (-0.3, 0.2, 0.55), PURPLE, segs=(12, 8), glow=0.5)               # a shade, all mouth
	p.blob((0.62, 0.3, 0.52), (-0.18, -0.02, 0.52), STONE_DARK, segs=(10, 6))                 # its maw
	for k in range(5):
		x = -0.42 + k * 0.12
		p.seg((x, -0.2, 0.8), (x, -0.2, 0.62), 0.045, 0.0, BONE, sides=5)
		p.seg((x + 0.05, -0.2, 0.26), (x + 0.05, -0.2, 0.42), 0.04, 0.0, BONE, sides=5)
	for sx in (-1, 1):
		p.blob((0.12, 0.06, 0.08), (-0.3 + sx * 0.16, -0.25, 0.98), PETAL_PURPLE, segs=(6, 4), glow=3.0)
	p.blob((0.3, 0.26, 0.34), (0.62, -0.1, 0.62), CLOTH_WHITE, segs=(8, 6), glow=1.8)          # a pale soul...
	for sx in (-1, 1):
		p.blob((0.06, 0.04, 0.08), (0.62 + sx * 0.07, -0.25, 0.68), STONE_DARK, segs=(5, 3))
	p.blob((0.07, 0.04, 0.1), (0.62, -0.26, 0.55), STONE_DARK, segs=(5, 3))
	for k in range(6):                                                                    # ...dragged in, streaming
		t = k / 5
		x = 0.45 - t * 0.6
		z = 0.6 + math.sin(t * math.pi * 1.5) * 0.12
		s = 0.2 - t * 0.12
		p.blob((s, s * 0.8, s * 0.8), (x, -0.15, z), CLOTH_WHITE, segs=(6, 4), glow=1.8)
	_stream(p, 0.9, 0.25, 0.3, 0.12, 0.04, CLOTH_RED, 2.2)                                 # its life drunk
	return p.build()


def frostbite_curse():
	p = Prop("frostbite_curse", 937)
	_snowflake(p, 0, 0.55, 0.42, 2.0)                                                     # the cold, bitten
	for side, sz in ((1, 1), (-1, -1)):                                                   # jaws of ice closing on it
		pts = [(math.cos(a) * 0.75, 0, 0.55 + side * math.sin(a) * 0.5) for a in [math.radians(20 + k * 17.5) for k in range(9)]]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.08, 0.08, WATER, sides=6, glow=0.8)
		for k, (x, _, z) in enumerate(pts[1:-1]):                                        # icicle fangs
			if k % 2 == 0 or k in (0, 6):
				p.seg((x, -0.05, z), (x * 0.7, -0.05, 0.55 + (z - 0.55) * 0.35), 0.06, 0.0, CLOTH_WHITE, sides=5, glow=1.4)
	for sx in (-1, 1):                                                                    # a spirit's cold eyes
		p.blob((0.1, 0.05, 0.07), (0.2 * sx - 0.1, -0.2, 1.15), RUNE, segs=(6, 4), glow=3.0)
	for k in range(4):
		_drop(p, -0.3 + k * 0.2, -0.2 - (k % 2) * 0.1, 0.14, WATER, 1.6)
	return p.build()


def chorus_of_ancestors():
	p = Prop("chorus_of_ancestors", 939)
	for k, (x, z, s) in enumerate(((-0.62, 0.35, 0.8), (0.0, 0.55, 1.0), (0.62, 0.35, 0.8))):   # three ancestor spirits, singing
		p.blob((0.46 * s, 0.4 * s, 0.56 * s), (x, 0.1 * k, z + 0.3 * s), LEAF, segs=(10, 8), glow=1.0)
		p.seg((x, 0.1 * k, z + 0.1 * s), (x + 0.06, 0.1 * k, z - 0.35 * s), 0.2 * s, 0.03, LEAF, sides=8, glow=1.0)
		for sx in (-1, 1):
			p.blob((0.1 * s, 0.05, 0.08 * s), (x + sx * 0.1 * s, 0.1 * k - 0.2 * s, z + 0.4 * s), STONE_DARK, segs=(6, 4))
		p.blob((0.12 * s, 0.05, 0.16 * s), (x, 0.1 * k - 0.21 * s, z + 0.18 * s), STONE_DARK, segs=(8, 5))    # mouths open in song
		for j in range(3):                                                               # feathers in their hair
			p.seg((x + (j - 1) * 0.08 * s, 0.1 * k, z + 0.55 * s), (x + (j - 1) * 0.2 * s, 0.1 * k, z + 0.85 * s), 0.04 * s, 0.0,
				  CLOTH_WHITE if j != 1 else CLOTH_RED, sides=4)
	for k in range(3):                                                                    # their song rising
		_ring_at(p, 0, 1.25, 0.2 + k * 0.18, 0.03, GOLD, glow=2.0, sides=10, a0=math.radians(40), a1=math.radians(140), y=-0.2)
	for x, z in ((-0.9, 1.0), (0.9, 1.0), (-0.35, 1.25), (0.35, 1.25)):
		p.box((0.14, 0.06, 0.04), (x, -0.25, z), LEAF, glow=2.4)
		p.box((0.04, 0.06, 0.14), (x, -0.25, z), LEAF, glow=2.4)
	return p.build()


def totem_of_fury():
	p = Prop("totem_of_fury", 941)
	for x, s in ((-0.45, 0.7), (0.45, 0.7), (0.0, 0.95)):                                 # rage burning behind it
		_fl(p, x, 0.3, 0.6, s, glow=2.0, core=CLOTH_RED)
	p.seg((0, 0, -0.2), (0, 0, 0.4), 0.16, 0.18, WOOD, sides=8)                           # a post
	p.blob((0.78, 0.5, 0.82), (0, 0, 0.72), CLOTH_RED, segs=(10, 8))                         # a snarling carved head
	for sx in (-1, 1):
		pts = [(sx * 0.35, 0, 0.95), (sx * 0.62, 0, 1.12), (sx * 0.7, 0, 1.45)]          # horns
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.09, 0.04, BONE, sides=6)
		p.box((0.22, 0.06, 0.07), (sx * 0.16, -0.25, 0.92), STONE_DARK, rot=(0, sx * -25, 0))   # scowling brows
		p.blob((0.14, 0.06, 0.1), (sx * 0.16, -0.24, 0.8), FLAME, segs=(6, 4), glow=3.0)          # blazing eyes
	p.box((0.5, 0.08, 0.16), (0, -0.24, 0.5), STONE_DARK)                                     # a roaring mouth
	for k in range(4):
		x = -0.18 + k * 0.12
		p.seg((x, -0.3, 0.58), (x, -0.3, 0.47), 0.035, 0.0, CLOTH_WHITE, sides=4)
	for sx in (-1, 1):
		p.seg((sx * 0.2, -0.3, 0.42), (sx * 0.22, -0.3, 0.6), 0.04, 0.0, CLOTH_WHITE, sides=4)
	p.box((0.4, 0.06, 0.05), (0, -0.25, 0.66), GOLD)                                         # painted stripes
	return p.build()


def heartpiercer():
	p = Prop("heartpiercer", 943)
	_heart(p, 0.1, 0.5, 0.5, CLOTH_RED, y=0.0, rim=GOLD, glow=1.4)                           # a heart
	_arrow(p, (-0.95, -0.25, 1.05), (0.75, 0.2, 0.05), hs=1.2, glow=0.8, r=0.04)            # an arrow clean through it
	for k in range(4):                                                                    # its flight, a gold streak
		t = k / 3
		p.seg((-1.05 - t * 0.25, -0.25, 1.1 + t * 0.15), (-1.35 - t * 0.25, -0.25, 1.28 + t * 0.15), 0.03, 0.0, GOLD, sides=4, glow=2.2)
	for k in range(3):
		_drop(p, 0.55 + k * 0.1, -0.15 - k * 0.12, 0.14, CLOTH_RED, 0.8)
	return p.build()


def predators_focus():
	p = Prop("predators_focus", 945)
	_ring_at(p, 0, 0.55, 0.78, 0.04, LEAF, glow=2.0, sides=28, y=0.1)                     # a hunter's sights
	for k in range(4):
		a = k * math.pi / 2
		p.seg((math.cos(a) * 0.62, 0.05, 0.55 + math.sin(a) * 0.62), (math.cos(a) * 0.98, 0.05, 0.55 + math.sin(a) * 0.98), 0.035, 0.035, LEAF, sides=4, glow=2.0)
	p.blob((0.95, 0.2, 0.46), (0, 0, 0.55), GOLD, segs=(14, 8), glow=1.0)                     # a narrowed predator's eye
	p.blob((0.1, 0.1, 0.38), (0, -0.08, 0.55), STONE_DARK, segs=(6, 6))                       # slit pupil
	p.blob((0.05, 0.04, 0.06), (0.06, -0.14, 0.64), CLOTH_WHITE, segs=(5, 3), glow=2.0)
	for sz in (1, -1):                                                                    # dark lids
		pts = [(math.cos(a) * 0.5, -0.05, 0.55 + sz * math.sin(a) * 0.24) for a in [math.radians(k * 22.5) for k in range(9)]]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.035, 0.035, STONE_DARK, sides=4)
	for k in range(3):                                                                    # claw rakes beneath
		x = -0.28 + k * 0.28
		p.seg((x + 0.1, -0.1, 0.12), (x - 0.12, -0.1, -0.35), 0.055, 0.0, LEAF, sides=4, glow=2.2)
	return p.build()


def hailstorm_volley():
	p = Prop("hailstorm_volley", 947)
	for k, (x, z) in enumerate(((-0.7, 0.9), (-0.35, 0.5), (0.0, 0.95), (0.3, 0.35), (0.62, 0.8), (-0.05, 0.0))):   # arrows tipped with ice, diving
		a = (x - 0.35, -0.1, z + 0.6)
		b = (x + 0.12, -0.1, z)
		_arrow(p, a, b, head=WATER, fletch=CLOTH_WHITE, glow=1.8, hs=0.75, r=0.03)
		p.seg(a, (a[0] - 0.25, -0.05, a[2] + 0.3), 0.03, 0.0, WATER, sides=4, glow=1.4)   # frost streaming off them
	for x, z, s in ((-0.5, 1.25, 0.11), (0.2, 1.3, 0.09), (0.75, 1.2, 0.1), (-0.85, 0.45, 0.08), (0.5, 0.15, 0.09), (-0.4, 0.05, 0.08),
					(0.9, 0.5, 0.07), (0.15, 0.7, 0.07)):                                  # and hail between them
		p.blob((s, s, s), (x, -0.2, z), CLOTH_WHITE, segs=(6, 4), glow=1.4)
	_snowflake(p, -0.9, 1.15, 0.16, 1.8)
	return p.build()


def burning_bite():
	p = Prop("burning_bite", 949)
	_fl(p, 0, 0.1, 0.1, 0.85, glow=2.2)                                                    # fire in the wound
	for side in (1, -1):                                                                  # a hound's jaws snapping shut on it
		pts = [(math.cos(a) * 0.7, -0.05, 0.55 + side * math.sin(a) * 0.45) for a in [math.radians(15 + k * 18.75) for k in range(9)]]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.1, 0.1, STONE_DARK, sides=6)
		for k, (x, _, z) in enumerate(pts[1:-1]):
			big = 0.28 if k in (1, 5) else 0.16
			p.seg((x, -0.12, z), (x * 0.9, -0.12, z - side * big), 0.06 if big > 0.2 else 0.045, 0.0, BONE, sides=5)
	for k in range(6):                                                                    # embers flying
		a = k * 1.1 + 0.3
		p.blob((0.07, 0.07, 0.07), (math.cos(a) * 0.95, -0.25, 0.55 + math.sin(a) * 0.65), FLAME, segs=(5, 3), glow=3.0)
	return p.build()


def choking_smoke():
	p = Prop("choking_smoke", 951)
	for k, (x, z, s) in enumerate(((-0.35, 1.0, 0.55), (0.25, 1.1, 0.6), (0.0, 0.75, 0.7), (-0.5, 0.6, 0.45), (0.5, 0.65, 0.45))):   # a dark smoke spirit
		p.blob((s, s * 0.8, s * 0.8), (x, 0.2, z), WOOD_GRAY if k % 2 else MIST, segs=(10, 6), jitter=0.03)
	for sx in (-1, 1):                                                                    # its ember eyes
		p.blob((0.22, 0.1, 0.14), (sx * 0.17, -0.25, 0.85), EMBER, segs=(8, 5), glow=3.2)
	p.blob((0.26, 0.1, 0.16), (0, -0.22, 0.58), STONE_DARK, segs=(8, 5))
	pts = []                                                                              # its smoky tail coiling down into a noose
	for k in range(31):
		t = k / 30
		a = -math.pi / 2 + t * math.tau * 1.6
		r = 0.08 + 0.34 * min(t * 2.5, 1.0)
		pts.append((math.cos(a) * r, math.sin(a) * r * 0.5, 0.45 - t * 0.6))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		w = 0.13 - i * 0.002
		p.seg(a, b, w, w, WOOD_GRAY if (i // 3) % 2 else MIST, sides=6)
	for k in range(4):                                                                    # choked, gasping puffs
		p.blob((0.1 + k * 0.03, 0.08, 0.1 + k * 0.03), (0.62 + k * 0.13, -0.3, 0.05 - k * 0.1), STONE_DARK, segs=(6, 4))
	return p.build()


def shard_burst():
	p = Prop("shard_burst", 953)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.55), CLOTH_WHITE, segs=(10, 6), glow=3.0)                # the flash of breaking glass
	for k in range(11):                                                                   # razor shards flying out
		a = k * math.tau / 11 + 0.15
		r0 = 0.22
		r1 = 0.75 + (k % 3) * 0.15
		sw = (STONE_LIGHT, RUNE, PETAL_PURPLE)[k % 3]
		_shard(p, (math.cos(a) * r0, 0.55 + math.sin(a) * r0), (math.cos(a) * r1, 0.55 + math.sin(a) * r1), 0.08, sw, glow=0.9 if sw != STONE_LIGHT else 0.3,
			   y=-0.05 * (k % 2))
		p.seg((math.cos(a) * r0 * 0.6, -0.2, 0.55 + math.sin(a) * r0 * 0.6), (math.cos(a) * r1 * 0.75, -0.2, 0.55 + math.sin(a) * r1 * 0.75),
			  0.012, 0.0, CLOTH_WHITE, sides=3, glow=2.0)
	for k in range(6):                                                                    # glittering dust
		a = k * 1.05 + 0.5
		p.blob((0.05, 0.05, 0.05), (math.cos(a) * 1.1, -0.2, 0.55 + math.sin(a) * 1.0), CLOTH_WHITE, segs=(4, 3), glow=2.4)
	return p.build()


def obsidian_breath():
	p = Prop("obsidian_breath", 955)
	p.blob((1.6, 1.0, 0.12), (0.25, 0, 0.0), STONE_DARK, segs=(12, 4))
	p.blob((1.0, 0.7, 0.08), (0.4, -0.05, 0.06), EMBER, segs=(12, 4), glow=2.0)              # a pool of molten glass...
	for x, y, s in ((0.1, 0.1, 0.4), (0.6, 0.15, 0.5), (0.85, -0.1, 0.32), (0.35, -0.2, 0.3)):   # ...setting into black glass spikes
		p.seg((x, y, 0.05), (x + 0.06, y, 0.05 + s * 1.4), s * 0.32, 0.0, STONE_DARK, sides=4)
		p.seg((x - s * 0.1, y - s * 0.3, 0.1), (x + 0.04, y - s * 0.2, 0.05 + s * 1.2), 0.02, 0.0, EMBER, sides=3, glow=2.4)
	a, b = Vector((-0.9, 0, 1.3)), Vector((0.3, 0, 0.25))                                  # the breath: a gout of molten glass
	p.seg(tuple(a), tuple(b), 0.08, 0.34, FLAME, sides=10, glow=2.2)
	p.seg(tuple(a + (b - a) * 0.15), tuple(b + (b - a) * 0.05), 0.04, 0.2, CLOTH_WHITE, sides=8, glow=2.6)
	for k in range(6):                                                                    # black shards carried in it
		t = 0.2 + k * 0.13
		c = a + (b - a) * t
		off = 0.15 + 0.1 * t
		sgn = 1 if k % 2 else -1
		_shard(p, (c.x - 0.05, c.z + sgn * off * 0.7), (c.x + 0.22, c.z + sgn * off * 0.7 - 0.12), 0.06, STONE_DARK, y=-0.35)
	p.blob((0.45, 0.35, 0.36), (-1.05, 0.05, 1.4), STONE_DARK, segs=(8, 6))                   # the drake's jaw at the edge
	for k in range(3):
		p.seg((-0.95 + k * 0.08, -0.15, 1.24), (-0.93 + k * 0.08, -0.15, 1.12), 0.035, 0.0, BONE, sides=4)
	return p.build()

def glass_venom():
	p = Prop("glass_venom", 957)
	for sx in (-1, 1):                                                                    # a pair of glass fangs
		pts = [(sx * 0.3, 0, 1.2), (sx * 0.34, 0, 0.9), (sx * 0.26, 0, 0.62), (sx * 0.12, 0, 0.42)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.14 - i * 0.04, 0.1 - i * 0.04 if i < 2 else 0.0, RUNE, sides=5, glow=0.7)
		p.seg((sx * 0.3 - 0.04, -0.12, 1.15), (sx * 0.2 - 0.03, -0.1, 0.55), 0.02, 0.0, CLOTH_WHITE, sides=4, glow=2.2)  # glinting
		p.blob((0.34, 0.3, 0.2), (sx * 0.3, 0.05, 1.25), STONE_LIGHT, segs=(8, 5))
	for k, (x, z, s) in enumerate(((0.12, 0.2, 0.22), (-0.12, 0.05, 0.18), (0.1, -0.3, 0.26))):   # dripping pale-blue venom
		_drop(p, x, z, s, WATER, 2.2)
	p.blob((0.9, 0.6, 0.06), (0, 0, -0.5), WATER, segs=(12, 4), glow=1.6)                     # a pool of it
	for k in range(5):                                                                    # tiny glass crystals growing in it
		a = k * math.tau / 5 + 0.3
		x, y = math.cos(a) * 0.32, math.sin(a) * 0.2
		p.seg((x, y, -0.5), (x * 1.3, y, -0.25), 0.05, 0.0, STONE_LIGHT, sides=4)
	return p.build()


def ember_tusk_blessing():
	p = Prop("ember_tusk_blessing", 959)
	p.blob((0.6, 0.5, 0.55), (0, 0, 0.4), STONE_LIGHT, segs=(10, 8))                      # an elephant's head
	for s_ in (-1, 1):
		p.blob((0.1, 0.35, 0.4), (s_ * 0.36, 0.05, 0.42), STONE_LIGHT, segs=(6, 5))
		p.seg((s_ * 0.12, -0.25, 0.25), (s_ * 0.2, -0.45, 0.15), 0.05, 0.02, EMBER, sides=5, glow=2.0)   # tusks glowing like hot iron
	p.seg((0, -0.3, 0.3), (0, -0.4, 0.85), 0.09, 0.06, STONE_LIGHT, sides=6)               # the trunk, raised...
	_fl(p, 0, -0.44, 0.85, 0.42, glow=2.4)                                                  # ...holding a flame
	return p.build()


LEVEL_35 = [sundering_blow, last_stand, earthshaker, circle_of_dawn, dawnbreak, dawns_embrace, obsidian_lance, frost_prison, starfall,
			throat_cut, shadow_dance, heartseeker, forgefire_mantle, forge_flare, elemental_tempest, wither, grave_pact, devour_soul,
			frostbite_curse, chorus_of_ancestors, totem_of_fury, heartpiercer, predators_focus, hailstorm_volley,
			burning_bite, choking_smoke, shard_burst, obsidian_breath, glass_venom, ember_tusk_blessing]


# ---------------------------------------------------------------- level 40 and the Galehold / steppe monsters

def _wind(p, a, b, swatch=CLOTH_WHITE, glow=1.4, r=0.045, y=-0.2, curl=0.14, up=1, turns=0.8):
	"""A gust line from a to b (picture-plane (x, z) points), thin at its tail, curling at its head."""
	a, b = Vector((a[0], y, a[1])), Vector((b[0], y, b[1]))
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x)) * up
	p.seg(a, b, r * 0.35, r, swatch, sides=5, glow=glow)
	c = b + n * curl
	a0 = math.atan2((b - c).z, (b - c).x)
	pts = []
	for k in range(11):
		t = k / 10
		ang = a0 + up * t * turns * math.tau
		rr = curl * (1 - 0.55 * t)
		pts.append(Vector((c.x + math.cos(ang) * rr, y, c.z + math.sin(ang) * rr)))
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w = r * (1 - 0.6 * k / 10)
		p.seg(u, v, w, w, swatch, sides=5, glow=glow)


def _crescent(p, cx, cz, radius, a0, a1, w, swatch, glow=0.0, y=0.0, steps=14):
	"""A crescent stroke along an arc, fattest in its middle."""
	pts = [(cx + math.cos(a0 + (a1 - a0) * k / steps) * radius, y, cz + math.sin(a0 + (a1 - a0) * k / steps) * radius) for k in range(steps + 1)]
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w0 = w * math.sin(math.pi * k / steps) + 0.008
		w1 = w * math.sin(math.pi * (k + 1) / steps) + 0.008
		p.seg(u, v, w0, w1, swatch, sides=5, glow=glow)


def _elephant(p, ear=STONE_LIGHT):
	"""The gods' elephant head the blessings share, without its ears."""
	p.blob((0.6, 0.5, 0.55), (0, 0, 0.4), STONE_LIGHT, segs=(10, 8))
	for s_ in (-1, 1):
		p.seg((s_ * 0.12, -0.25, 0.25), (s_ * 0.2, -0.45, 0.15), 0.05, 0.02, BONE, sides=5)
	p.seg((0, -0.3, 0.3), (0, -0.4, 0.85), 0.09, 0.06, STONE_LIGHT, sides=6)


def skybreaker():
	p = Prop("skybreaker", 961)
	cx, cz, R = 0.35, 0.95, 0.62
	for k in range(7):                                                                    # the sky, shattering
		a0, a1 = k * math.tau / 7 + 0.2, (k + 1) * math.tau / 7 + 0.2
		mid = (a0 + a1) / 2
		off = (math.cos(mid) * 0.07 * (1 + k % 2), math.sin(mid) * 0.07 * (1 + k % 2))
		outline = [(cx + off[0], cz + off[1])] + [(cx + off[0] + math.cos(a0 + (a1 - a0) * i / 4) * R, cz + off[1] + math.sin(a0 + (a1 - a0) * i / 4) * R) for i in range(5)]
		icons._slab(p, outline[::-1], 0.12, 0.22, WATER if k % 2 else RUNE, grad=(0.1, 0.6))
	for x, z, s in ((0.55, 1.2, 0.22), (0.72, 1.1, 0.18), (0.1, 1.3, 0.16)):               # a cloud on it
		p.blob((s, 0.08, s * 0.7), (x, 0.08, z), CLOTH_WHITE, segs=(8, 5), glow=0.6)
	for k in range(7):                                                                    # light through the cracks
		a = k * math.tau / 7 + 0.2
		p.seg((cx, 0.05, cz), (cx + math.cos(a) * (R + 0.15), 0.05, cz + math.sin(a) * (R + 0.15)), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.6)
	c = Vector((0.02, -0.15, 0.62))
	d = Vector((0.62, 0, 0.8)).normalized()
	perp = Vector((-d.z, 0, d.x))
	p.seg(tuple(c - d * 0.95), tuple(c), 0.06, 0.06, WOOD, sides=6)                         # a war hammer, striking up
	p.seg(tuple(c - perp * 0.3), tuple(c + perp * 0.3), 0.21, 0.21, STONE_LIGHT, sides=8)
	for sgn in (-1, 1):
		p.seg(tuple(c + perp * sgn * 0.3), tuple(c + perp * sgn * 0.36), 0.23, 0.23, IRON, sides=8)
	p.seg(tuple(c + d * 0.1), tuple(c + d * 0.3), 0.07, 0.0, IRON, sides=4)
	for x, z in ((-0.45, 1.25), (-0.2, 1.45)):                                            # stunned stars
		_star(p, x, z, 0.1, GOLD, glow=2.4, y=-0.3)
	return p.build()


def rallying_standard():
	p = Prop("rallying_standard", 963)
	_ring(p, 0.7, 0.0, 0.045, GOLD, glow=1.8, sides=24)                                   # the group it rallies
	p.seg((0, 0, 0.0), (0, 0, 1.6), 0.05, 0.045, WOOD, sides=6)                            # a standard...
	p.seg((0, 0, 1.6), (0, 0, 1.85), 0.09, 0.0, GOLD, sides=4, glow=1.2)
	p.seg((-0.05, 0, 1.5), (0.82, 0, 1.5), 0.035, 0.035, WOOD, sides=6)
	outline = [(0.03, 1.48), (0.8, 1.48), (0.8, 0.62), (0.415, 0.4), (0.03, 0.62)]          # ...flying a sky-blue banner
	icons._slab(p, outline, -0.02, 0.04, WATER, grad=(0.05, 0.6))
	edge = outline + outline[:1]
	for u, v in zip(edge, edge[1:]):
		p.seg((u[0], -0.04, u[1]), (v[0], -0.04, v[1]), 0.03, 0.03, GOLD, sides=4, glow=0.8)
	for k in range(3):                                                                    # its blazon: rising chevrons
		z = 0.62 + k * 0.24
		for sx in (-1, 1):
			p.seg((0.415, -0.08, z + 0.14), (0.415 + sx * 0.22, -0.08, z), 0.045, 0.045, GOLD, sides=5, glow=2.2)
	for x in (-0.55, 0.62):                                                               # and those around it standing up
		p.seg((x, -0.3, 0.15), (x, -0.3, 0.55), 0.04, 0.04, GOLD, sides=4, glow=2.0)
		p.seg((x, -0.3, 0.62), (x, -0.3, 0.46), 0.1, 0.0, GOLD, sides=4, glow=2.0)
	return p.build()


def gale_cleave():
	p = Prop("gale_cleave", 965)
	_crescent(p, 0, 0.45, 0.95, math.radians(-25), math.radians(205), 0.11, CLOTH_WHITE, glow=1.8, y=0.2)   # a sweep of wind
	_crescent(p, 0, 0.45, 0.72, math.radians(-10), math.radians(190), 0.07, RUNE, glow=1.6, y=0.2)
	for a in (math.radians(-25), math.radians(205)):
		sx = 1 if math.cos(a) > 0 else -1
		_wind(p, (math.cos(a) * 0.95 - sx * 0.02, 0.45 + math.sin(a) * 0.95), (math.cos(a) * 0.95 + sx * 0.12, 0.45 + math.sin(a) * 0.95 - 0.16),
			  r=0.05, up=-sx, y=0.2, curl=0.12)
	_axe(p, (-0.35, -0.1, -0.2), (0.3, -0.1, 1.05), flip=-1)                              # a great axe through it
	for a in (math.radians(160), math.radians(90), math.radians(20)):                     # every foe it catches
		x, z = math.cos(a) * 0.95, 0.45 + math.sin(a) * 0.95
		for k in range(4):
			b = k * math.pi / 2 + 0.4
			p.seg((x, -0.1, z), (x + math.cos(b) * 0.16, -0.1, z + math.sin(b) * 0.16), 0.04, 0.0, CLOTH_RED, sides=4, glow=1.8)
	return p.build()


def sunrise_ward():
	p = Prop("sunrise_ward", 967)
	p.blob((1.9, 1.3, 0.12), (0, 0, -0.05), STONE_WARM, segs=(14, 4))                        # the ground
	for k in range(3):                                                                    # a group, sheltered
		x = -0.38 + k * 0.38
		h = 0.95 if k == 1 else 0.85
		p.seg((x, 0.05 - (k == 1) * 0.1, 0.0), (x, 0.05 - (k == 1) * 0.1, h * 0.45), 0.15, 0.08, CLOTH_WHITE, sides=8)
		p.blob((0.18, 0.18, 0.18), (x, 0.05 - (k == 1) * 0.1, h * 0.55), CLOTH_WHITE, segs=(8, 6))
	_ring(p, 0.85, 0.02, 0.045, GOLD, glow=1.8, sides=24)                                 # under a dome of dawn light
	for sx in (1.0, 0.55):
		for sgn in (-1, 1):
			pts = [(sgn * math.cos(math.radians(a)) * 0.85 * sx, -0.3 * (1 - sx) * 0, math.sin(math.radians(a)) * 0.85) for a in range(0, 91, 10)]
			for u, v in zip(pts, pts[1:]):
				p.seg(u, v, 0.035, 0.035, GOLD, sides=5, glow=1.6)
	_ring_at(p, 0, 0.0, 0.85, 0.035, FLAME, glow=1.4, sides=14, a0=0.0, a1=math.pi, y=-0.02)
	p.seg((0, 0.05, 0.95), (0, -0.05, 0.95), 0.2, 0.2, GOLD, sides=16, glow=2.6)             # crowned by the rising sun
	for k in range(7):
		a = math.radians(10 + k * 26.7)
		p.seg((math.cos(a) * 0.26, -0.02, 0.95 + math.sin(a) * 0.26), (math.cos(a) * 0.45, -0.02, 0.95 + math.sin(a) * 0.45), 0.05, 0.0, FLAME, sides=4, glow=2.4)
	return p.build()


def radiant_smite():
	p = Prop("radiant_smite", 969)
	cx, cz = 0.3, 0.85
	for k in range(14):                                                                   # noon, bursting
		a = k * math.tau / 14 + 0.1
		r1 = 0.95 if k % 2 else 0.68
		p.seg((cx + math.cos(a) * 0.2, 0.3, cz + math.sin(a) * 0.2), (cx + math.cos(a) * r1, 0.3, cz + math.sin(a) * r1), 0.08, 0.0,
			  GOLD if k % 2 else CLOTH_WHITE, sides=4, glow=2.4)
	p.blob((0.5, 0.2, 0.5), (cx, 0.3, cz), CLOTH_WHITE, segs=(12, 6), glow=3.0)
	a, top = Vector((-0.65, -0.1, -0.35)), Vector((0.15, -0.1, 0.62))                       # a flanged mace, striking into it
	d = (top - a).normalized()
	p.seg(tuple(a), tuple(top), 0.055, 0.055, WOOD, sides=6)
	p.blob((0.1, 0.1, 0.1), tuple(a), GOLD, segs=(6, 4))
	head = top + d * 0.12
	p.blob((0.3, 0.3, 0.36), tuple(head), GOLD, segs=(10, 6), glow=1.0)
	perp = Vector((-d.z, 0, d.x))
	for k in range(6):
		ang = k * math.tau / 6
		out = perp * math.cos(ang) + Vector((0, 1, 0)) * math.sin(ang)
		p.seg(tuple(head - d * 0.13 + out * 0.1), tuple(head + out * 0.28), 0.07, 0.02, GOLD, sides=4, glow=1.0)
	p.seg(tuple(head + d * 0.14), tuple(head + d * 0.3), 0.07, 0.0, GOLD, sides=4, glow=1.2)
	return p.build()


def circle_of_radiance():
	p = Prop("circle_of_radiance", 971)
	_ring_at(p, 0, 0.55, 0.6, 0.07, GOLD, glow=2.2, sides=30, y=0.1)                        # a ring of radiance
	for k in range(18):
		a = k * math.tau / 18
		r1 = 1.0 if k % 2 else 0.85
		p.seg((math.cos(a) * 0.7, 0.1, 0.55 + math.sin(a) * 0.7), (math.cos(a) * r1, 0.1, 0.55 + math.sin(a) * r1), 0.06, 0.0,
			  FLAME if k % 2 else GOLD, sides=4, glow=2.2)
	p.box((0.2, 0.12, 0.66), (0, -0.05, 0.55), LEAF, glow=2.4)                               # healing at its heart
	p.box((0.66, 0.12, 0.2), (0, -0.05, 0.6), LEAF, glow=2.4)
	for k in range(4):                                                                    # for all within it
		a = k * math.tau / 4 + math.pi / 4
		x, z = math.cos(a) * 0.6, 0.55 + math.sin(a) * 0.6
		p.box((0.16, 0.08, 0.05), (x, -0.12, z), CLOTH_WHITE, glow=2.6)
		p.box((0.05, 0.08, 0.16), (x, -0.12, z), CLOTH_WHITE, glow=2.6)
	return p.build()


def tempest_lance():
	p = Prop("tempest_lance", 973)
	a, b = Vector((-0.8, 0, -0.15)), Vector((0.62, 0, 1.0))
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(tuple(a), tuple(b), 0.08, 0.1, RUNE, sides=6, glow=2.0)                          # a lance of storm-light
	p.seg(tuple(b), tuple(b + d * 0.45), 0.16, 0.0, CLOTH_WHITE, sides=6, glow=2.8)
	p.seg(tuple(b - d * 0.05), tuple(b + d * 0.05), 0.18, 0.18, GOLD, sides=8, glow=1.6)
	L = (b - a).length
	pts = []
	for k in range(41):                                                                   # wound with wind
		t = k / 40
		w = t * 4.5 * math.tau
		rr = 0.22 * (1 - 0.35 * t)
		pts.append(a + d * (0.15 + t * (L - 0.15)) + n * math.cos(w) * rr + Vector((0, -1, 0)) * math.sin(w) * rr)
	for u, v in zip(pts, pts[1:]):
		p.seg(tuple(u), tuple(v), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=1.4)
	for t, sgn in ((0.35, 1), (0.6, -1), (0.8, 1)):                                       # throwing lightning
		base = a + d * L * t
		zig = [base, base + n * sgn * 0.18 + d * 0.08, base + n * sgn * 0.26 - d * 0.04, base + n * sgn * 0.45 + d * 0.06]
		for u, v in zip(zig, zig[1:]):
			p.seg(tuple(u - Vector((0, 0.1, 0))), tuple(v - Vector((0, 0.1, 0))), 0.035, 0.025, GOLD, sides=4, glow=2.6)
	return p.build()


def windshear():
	p = Prop("windshear", 975)
	p.seg((0.1, 0, 0.3), (0.16, 0, 1.0), 0.2, 0.24, WOOD, sides=10)                        # a boot, straining forward
	p.seg((0.16, 0, 0.98), (0.17, 0, 1.12), 0.29, 0.29, HIDE, sides=10)
	p.blob((0.7, 0.38, 0.36), (0.36, 0, 0.22), WOOD, segs=(10, 6))
	p.box((0.74, 0.38, 0.08), (0.36, 0, 0.05), STONE_DARK)
	for k, z in enumerate((0.42, 0.72)):                                                  # wound in wind...
		_ring(p, 0.32, z, 0.03, CLOTH_WHITE if k % 2 else RUNE, glow=1.8, sides=18, tilt=0.5)
	for k, z in enumerate((0.3, 0.62, 0.95)):                                             # ...dragging it back
		_wind(p, (-0.2, z + 0.05), (-0.85 - (k % 2) * 0.1, z), r=0.05, up=-1, y=-0.1, swatch=CLOTH_WHITE if k != 1 else RUNE)
	return p.build()


def skyfall():
	p = Prop("skyfall", 977)
	p.blob((2.0, 1.4, 0.16), (0, 0, -0.05), STONE_DARK, segs=(14, 5))                        # the ground
	for k in range(6):                                                                    # cracking
		a = k * math.tau / 6 + 0.3
		p.seg((0.1, 0, 0.04), (0.1 + math.cos(a) * 0.9, math.sin(a) * 0.6, 0.04), 0.05, 0.01, CLOTH_WHITE, sides=4, glow=2.0)
	for x, z, s in ((-0.55, 0.12, 0.28), (0.7, 0.1, 0.25), (-0.3, 0.05, 0.2)):             # dust thrown up
		p.blob((s, s * 0.8, s * 0.7), (x, -0.2, z), MIST, segs=(8, 5))
	outline = [(0.1, 0.05), (0.75, 0.55), (0.6, 1.05), (0.85, 1.35), (0.2, 1.5), (-0.1, 1.2), (-0.55, 1.1), (-0.45, 0.6)]   # a torn piece of sky
	icons._slab(p, outline, -0.08, 0.1, WATER, grad=(0.0, 0.7))
	edge = outline + outline[:1]
	for u, v in zip(edge, edge[1:]):
		p.seg((u[0], -0.1, u[1]), (v[0], -0.1, v[1]), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=1.6)
	p.seg((0.3, -0.1, 1.15), (0.3, -0.16, 1.15), 0.17, 0.17, GOLD, sides=14, glow=2.4)      # its sun
	for x, z, s in ((-0.2, 0.85, 0.24), (0.02, 0.9, 0.3), (0.22, 0.8, 0.22), (0.4, 0.62, 0.18)):   # its clouds
		p.blob((s, 0.12, s * 0.7), (x, -0.14, z), CLOTH_WHITE, segs=(8, 5), glow=0.5)
	for k in range(4):                                                                    # falling fast
		x = -0.5 + k * 0.4
		p.seg((x - 0.2, -0.1, 1.6 + (k % 2) * 0.15), (x - 0.3, -0.1, 2.0 + (k % 2) * 0.15), 0.04, 0.0, RUNE, sides=4, glow=1.8)
	return p.build()


def windstep_strike():
	p = Prop("windstep_strike", 979)
	for k, (dx, sw, g) in enumerate(((-0.72, RUNE, 1.0), (-0.42, RUNE, 1.5), (-0.14, CLOTH_WHITE, 2.0))):   # afterimages of the step
		base = Vector((dx - 0.3, 0.1 + 0.05 * (2 - k), 0.35))
		tip = base + Vector((0.8, 0, 0.36)) * (0.7 + 0.15 * k)
		p.seg(tuple(base), tuple(tip), 0.08 + 0.015 * k, 0.0, sw, sides=4, glow=g)
	_dagger(p, (0.0, -0.15, 0.35), (0.95, -0.15, 0.8), w=0.12, edge=CLOTH_WHITE)          # the strike, already landed
	for z in (0.1, 0.95):                                                                 # and the wind it left behind
		_wind(p, (-0.95, z), (-0.1, z + 0.06), r=0.04, up=1 if z < 0.5 else -1, y=-0.25)
	for k in range(4):                                                                    # a flash where it lands
		a = k * math.pi / 2 + 0.4
		p.seg((1.0, -0.2, 0.82), (1.0 + math.cos(a) * 0.2, -0.2, 0.82 + math.sin(a) * 0.2), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.6)
	return p.build()


def razor_wind():
	p = Prop("razor_wind", 981)
	for k in range(5):                                                                    # a whirlwind...
		z = 0.08 + k * 0.27
		r = 0.18 + k * 0.13
		_ring(p, r, z, 0.03, RUNE if k % 2 else CLOTH_WHITE, glow=1.3, sides=18, tilt=0.3)
		for j in range(3):                                                                # ...of razor blades
			a = j * math.tau / 3 + k * 0.9
			x, y = math.cos(a) * r, math.sin(a) * r * 0.5
			zz = z + math.sin(a) * r * 0.3
			s = 0.1 + k * 0.03
			_crescent(p, x, zz, s, math.radians(-40) + a, math.radians(140) + a, 0.05 + k * 0.01, STONE_LIGHT, glow=0.4, y=y - 0.05)
			_crescent(p, x, zz, s + 0.02, math.radians(-40) + a, math.radians(140) + a, 0.015, CLOTH_WHITE, glow=2.4, y=y - 0.1)
	return p.build()


def assassins_mark():
	p = Prop("assassins_mark", 983)
	outline = [(0, 1.1), (0.55, 0.58), (0, 0.06), (-0.55, 0.58)]                            # a brand...
	icons._slab(p, outline, 0.05, 0.14, CRIMSON, grad=(0.1, 0.6))
	edge = outline + outline[:1]
	inner = [(x * 0.62, 0.58 + (z - 0.58) * 0.62) for x, z in outline]
	inner = inner + inner[:1]
	for u, v in zip(edge, edge[1:]):
		p.seg((u[0], 0.0, u[1]), (v[0], 0.0, v[1]), 0.04, 0.04, CLOTH_RED, sides=4, glow=1.8)
	for u, v in zip(inner, inner[1:]):
		p.seg((u[0], 0.0, u[1]), (v[0], 0.0, v[1]), 0.025, 0.025, FLAME, sides=4, glow=2.0)
	p.blob((0.3, 0.08, 0.16), (0, -0.02, 0.58), CLOTH_WHITE, segs=(10, 5), glow=1.6)        # ...an open eye on the foe
	p.blob((0.11, 0.06, 0.13), (0, -0.06, 0.58), STONE_DARK, segs=(6, 4))
	_dagger(p, (0.55, -0.2, 1.3), (-0.12, -0.2, 0.52), w=0.11, edge=CRIMSON)              # a knife in it
	for x, z, s in ((-0.15, -0.1, 0.25), (0.12, -0.3, 0.3), (-0.02, -0.55, 0.22)):          # bleeding heavily
		_drop(p, x, z, s, CLOTH_RED, 1.2)
	return p.build()


def skyforge_mantle():
	p = Prop("skyforge_mantle", 985)
	cape = [(-0.3, 0.85), (0.3, 0.85), (0.62, 0.3), (0.9, -0.05), (0.45, 0.05), (0.2, -0.02), (-0.2, 0.05), (-0.55, -0.05)]   # a sky-blue mantle
	icons._slab(p, cape, 0.22, 0.3, WATER, grad=(0.05, 0.7))
	_elemental(p, STONE_LIGHT, s=1.0)                                                      # on the pet...
	for sx in (-1, 1):                                                                    # ...with forged pauldrons
		p.blob((0.34, 0.34, 0.24), (sx * 0.3, -0.02, 0.76), IRON, segs=(10, 6))
		p.seg((sx * 0.3, -0.1, 0.84), (sx * 0.45, -0.1, 1.0), 0.06, 0.0, CLOTH_WHITE, sides=4, glow=1.8)
	p.box((0.2, 0.08, 0.2), (0, -0.22, 0.5), RUNE, rot=(0, 45, 0), glow=2.6)                  # a sky-gem at its heart
	p.blob((0.1, 0.06, 0.07), (-0.07, -0.16, 0.98), CLOTH_WHITE, segs=(5, 3), glow=2.6)
	p.blob((0.1, 0.06, 0.07), (0.07, -0.16, 0.98), CLOTH_WHITE, segs=(5, 3), glow=2.6)
	for k, z in enumerate((0.2, 0.55)):                                                   # the wind in its mantle
		_wind(p, (-0.3, z), (-0.95, z + 0.12), r=0.04, up=-1, y=0.3, swatch=CLOTH_WHITE if k else RUNE)
	for x in (0.72, 0.9):                                                                 # made stronger
		p.seg((x, -0.3, 0.55 + (x - 0.72)), (x, -0.3, 0.95 + (x - 0.72)), 0.035, 0.035, GOLD, sides=4, glow=2.2)
		p.seg((x, -0.3, 1.02 + (x - 0.72)), (x, -0.3, 0.9 + (x - 0.72)), 0.09, 0.0, GOLD, sides=4, glow=2.2)
	return p.build()


def cyclone_blast():
	p = Prop("cyclone_blast", 987)
	for k in range(8):                                                                    # a cyclone on its side...
		x = -0.75 + k * 0.2
		r = 0.06 + k * 0.075
		zc = 0.55 + math.sin(k * 0.8) * 0.05
		sw = CLOTH_WHITE if k % 2 else RUNE
		for j in range(16):
			a0, a1 = j * math.tau / 16, (j + 1) * math.tau / 16
			p.seg((x + 0.03 * math.sin(a0), math.cos(a0) * r, zc + math.sin(a0) * r), (x + 0.03 * math.sin(a1), math.cos(a1) * r, zc + math.sin(a1) * r),
				  0.03, 0.03, sw, sides=4, glow=1.5)
	for k in range(7):                                                                    # ...blasting out its mouth
		a = math.radians(-60 + k * 20)
		p.seg((0.9, -0.1, 0.55 + math.sin(a) * 0.3), (0.9 + math.cos(a) * 0.4, -0.1, 0.55 + math.sin(a) * 0.75), 0.045, 0.0, CLOTH_WHITE, sides=4, glow=2.2)
	for x, z, s in ((1.05, 1.05, 0.12), (1.2, 0.2, 0.1), (0.6, 1.2, 0.09)):                 # with debris
		p.rock((s * 1.2, s, s), (x, -0.2, z), STONE_WARM, jitter=0.2)
	return p.build()


def elemental_maelstrom():
	p = Prop("elemental_maelstrom", 989)
	for v, sw in enumerate((FLAME, WATER, STONE_WARM, CLOTH_WHITE)):                      # every element, whirled together
		pts = []
		for k in range(25):
			t = k / 24
			a = v * math.tau / 4 + t * 1.3 * math.pi
			r = 0.12 + t * 0.8
			pts.append((math.cos(a) * r, 0.02 * v, 0.55 + math.sin(a) * r))
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			w = 0.03 + 0.08 * i / 24
			p.seg(a, b, w, w, sw, sides=6, glow=0.5 if sw == STONE_WARM else 1.6)
		end = pts[-1]
		if sw == FLAME:
			_fl(p, end[0], -0.1, end[2] - 0.1, 0.28, glow=2.2)
		elif sw == WATER:
			_drop(p, end[0], end[2], 0.3, WATER, 1.8)
		elif sw == STONE_WARM:
			p.rock((0.26, 0.24, 0.24), (end[0], -0.1, end[2]), STONE_WARM, jitter=0.15)
		else:
			_swirl(p, end[0], end[2], 0.14, 0.02, 0.8, CLOTH_WHITE, 1.6, thick=0.05, steps=10)
	p.blob((0.34, 0.2, 0.34), (0, -0.1, 0.55), GOLD, segs=(10, 6), glow=3.0)                  # its eye
	return p.build()


def barrow_rot():
	p = Prop("barrow_rot", 991)
	p.blob((2.0, 1.2, 0.95), (0, 0.2, 0.0), PINE, segs=(16, 8))                              # a barrow mound
	p.blob((2.4, 1.5, 0.1), (0, 0.1, -0.02), STONE_DARK, segs=(14, 4))
	p.blob((0.5, 0.2, 0.55), (0, -0.28, 0.22), STONE_DARK, segs=(10, 6))                     # its door
	p.blob((0.34, 0.1, 0.4), (0, -0.36, 0.2), SICKLY, segs=(10, 6), glow=2.4)                # full of rot
	for sx in (-1, 1):
		p.box((0.16, 0.2, 0.62), (sx * 0.34, -0.3, 0.28), STONE_LIGHT, jitter=0.02)
	p.box((0.95, 0.24, 0.16), (0, -0.3, 0.62), STONE_LIGHT, jitter=0.02)
	for k, (x, z, s) in enumerate(((-0.15, 0.9, 0.34), (0.2, 1.15, 0.28), (-0.05, 1.42, 0.22))):   # the rot rising
		p.blob((s, s * 0.7, s * 0.8), (x, -0.2, z), SICKLY, segs=(8, 6), glow=1.1)
		_swirl(p, x + 0.12, z + 0.05, 0.1, 0.02, 0.7, SICKLY, 2.0, thick=0.035, steps=8)
	for x, z, s in ((-0.62, 0.4, 0.12), (0.6, 0.35, 0.1), (0.45, 0.7, 0.08)):              # bubbling out of the grass
		p.blob((s, s, s), (x, -0.4, z), SICKLY, segs=(6, 4), glow=2.2)
	return p.build()


def unholy_frenzy():
	p = Prop("unholy_frenzy", 993)
	for k in range(3):                                                                    # purple claw-rakes...
		off = (k - 1) * 0.28
		_crescent(p, 0.9 + off, 1.1 + off, 1.0, math.radians(200), math.radians(260), 0.09, PETAL_PURPLE, glow=2.2, y=-0.2)
	p.blob((0.45, 0.2, 0.4), (-0.35, 0, 0.2), BONE, segs=(10, 6))                            # ...from a skeletal claw
	for k in range(4):
		a = math.radians(40 + k * 22)
		root = Vector((-0.35 + math.cos(a) * 0.18, 0, 0.2 + math.sin(a) * 0.18))
		mid = root + Vector((math.cos(a - 0.2), 0, math.sin(a - 0.2))) * 0.3
		tip = mid + Vector((math.cos(a - 0.7), 0, math.sin(a - 0.7))) * 0.25
		_bone(p, tuple(root), tuple(mid), 0.04)
		p.seg(tuple(mid), tuple(tip), 0.05, 0.0, BONE, sides=5)
		p.seg(tuple(tip), tuple(tip + Vector((math.cos(a - 1.2), 0, math.sin(a - 1.2))) * 0.14), 0.035, 0.0, STONE_DARK, sides=4)
	_bone(p, (-0.45, 0, 0.05), (-0.8, 0, -0.35), 0.05)
	for k in range(3):                                                                    # fast
		z = -0.2 + k * 0.18
		p.seg((-0.2, -0.1, z), (0.35 - k * 0.1, -0.1, z - 0.02), 0.035, 0.0, PURPLE, sides=4, glow=2.0)
	return p.build()


def soul_eater():
	p = Prop("soul_eater", 995)
	_ring_at(p, 0, 0.75, 0.7, 0.05, PURPLE, glow=1.6, sides=24, y=0.3)                    # a dark aura
	p.blob((0.5, 0.35, 0.55), (0, 0, 0.95), CLOTH_WHITE, segs=(12, 8), glow=1.6)              # a soul, its face aghast
	p.seg((0, 0, 0.8), (-0.3, 0, 1.55), 0.18, 0.0, CLOTH_WHITE, sides=8, glow=1.6)
	for sx in (-1, 1):
		p.blob((0.1, 0.06, 0.13), (sx * 0.1, -0.17, 1.02), STONE_DARK, segs=(6, 4))
	p.blob((0.1, 0.06, 0.14), (0, -0.17, 0.85), STONE_DARK, segs=(6, 4))
	for k in range(5):                                                                    # in a clutching bone hand
		a = math.radians(-20 + k * 42) if k < 4 else math.radians(200)
		root = (math.cos(a) * 0.2, -0.05, 0.5 + math.sin(a) * 0.12)
		tip = (math.cos(a) * 0.38, -0.2, 0.9 + (0.25 if k < 4 else 0.0))
		_bone(p, root, (root[0] * 1.6, -0.1, 0.72), 0.035)
		p.seg((root[0] * 1.6, -0.12, 0.72), tip, 0.045, 0.0, BONE, sides=5)
	p.blob((0.5, 0.3, 0.3), (0, 0, 0.45), BONE, segs=(10, 6))
	_bone(p, (0, 0, 0.35), (0, 0, -0.1), 0.06)
	for x0, x1, z in ((0.1, 0.9, 0.2), (-0.1, -0.85, 0.15)):                               # its life drawn out, red
		_stream(p, x0, x1, z, 0.08, 0.035, CLOTH_RED, 2.0, n=10)
	return p.build()


def windbite_curse():
	p = Prop("windbite_curse", 997)
	cx, cz = 0.2, 0.55
	_crescent(p, cx, cz + 0.05, 0.62, math.radians(10), math.radians(170), 0.1, CLOTH_WHITE, glow=1.6)   # a jaw of wind...
	_crescent(p, cx, cz - 0.05, 0.62, math.radians(190), math.radians(350), 0.1, RUNE, glow=1.6)
	for k in range(5):                                                                    # ...with icicle teeth
		a = math.radians(40 + k * 25)
		x = cx + math.cos(a) * 0.55
		p.seg((x, -0.1, cz + 0.05 + math.sin(a) * 0.5), (x, -0.1, cz + 0.05 + math.sin(a) * 0.5 - 0.3), 0.06, 0.0, WATER, sides=5, glow=1.8)
		a = math.radians(-40 - k * 25)
		p.seg((cx + math.cos(a) * 0.55, -0.1, cz - 0.05 + math.sin(a) * 0.5), (cx + math.cos(a) * 0.55, -0.1, cz - 0.05 + math.sin(a) * 0.5 + 0.26),
			  0.055, 0.0, WATER, sides=5, glow=1.8)
	for k, z in enumerate((0.3, 0.55, 0.8)):                                              # blown on a cold wind
		_wind(p, (-1.1, z + (k - 1) * 0.08), (-0.55, z), r=0.04, up=1 if k != 1 else -1, y=-0.05)
	_snowflake(p, cx, cz, 0.18, 2.2)
	return p.build()


def spirit_of_the_plains():
	p = Prop("spirit_of_the_plains", 999)
	for k in range(9):                                                                    # the long grass
		x = -0.8 + k * 0.2
		p.seg((x, 0.1, -0.1), (x + 0.12, 0.1, 0.25 + (k % 3) * 0.1), 0.05, 0.0, LEAF, sides=4)
	p.blob((1.05, 0.7, 0.62), (0, 0.25, 0.78), AMBER, segs=(12, 8), glow=1.0)                 # a spirit bison's hump
	p.blob((0.66, 0.6, 0.66), (0, -0.05, 0.55), AMBER, segs=(12, 8), glow=1.2)                # its head
	p.blob((0.46, 0.34, 0.32), (0, -0.3, 0.35), HIDE, segs=(10, 6), glow=0.2)                 # its muzzle
	p.blob((0.35, 0.3, 0.3), (0, -0.05, 0.15), HIDE, segs=(8, 6), glow=0.4)                   # its beard
	for sx in (-1, 1):
		pts = [(sx * 0.28, -0.2, 0.72), (sx * 0.58, -0.22, 0.74), (sx * 0.72, -0.22, 0.95), (sx * 0.62, -0.25, 1.15)]
		for i, (u, v) in enumerate(zip(pts, pts[1:])):
			p.seg(u, v, 0.1 - i * 0.03, 0.07 - i * 0.03 if i < 2 else 0.0, CLOTH_WHITE, sides=6, glow=0.8)
		p.blob((0.12, 0.06, 0.1), (sx * 0.17, -0.37, 0.62), CLOTH_WHITE, segs=(6, 4), glow=3.0)
	_ring(p, 0.85, 0.0, 0.04, GOLD, glow=1.8, sides=24)                                   # watching over the group
	return p.build()


def gale_of_torpor():
	p = Prop("gale_of_torpor", 1001)
	p.seg((-0.75, 0, 0.1), (0.55, 0, 0.12), 0.1, 0.15, SEAFOAM, sides=8)                   # a snail
	p.blob((0.34, 0.3, 0.34), (0.62, 0, 0.3), SEAFOAM, segs=(10, 6))
	for sx, h in ((-1, 0.78), (1, 0.84)):
		p.seg((0.62 + sx * 0.06, 0, 0.42), (0.66 + sx * 0.16, 0, h), 0.03, 0.025, SEAFOAM, sides=5)
		p.blob((0.09, 0.09, 0.09), (0.66 + sx * 0.16, 0, h), STONE_DARK, segs=(6, 4))
	p.blob((0.95, 0.5, 0.95), (-0.12, 0.05, 0.62), AMBER, segs=(14, 8))                       # its shell
	pts = [(-0.12 + math.cos(t * 2.0 * math.tau) * (0.04 + 0.4 * t), -0.24, 0.62 + math.sin(t * 2.0 * math.tau) * (0.04 + 0.4 * t))
		   for t in (k / 30 for k in range(31))]
	for u, v in zip(pts, pts[1:]):                                                        # its spiral, on the front
		p.seg(u, v, 0.05, 0.05, WOOD, sides=5)
	for k, z in enumerate((0.45, 0.8, 1.15)):                                             # in a sleepy gale
		_wind(p, (-1.1 + k * 0.1, z), (0.35 + k * 0.15, z + 0.08), r=0.045, y=-0.3, swatch=RUNE if k % 2 else CLOTH_WHITE)
	_zs(p, 0.95, 1.2, 0.8)
	return p.build()


def windrider_shot():
	p = Prop("windrider_shot", 1003)
	pts = []                                                                              # a great curl of wind...
	for k in range(26):
		t = k / 25
		a = math.radians(-90) - t * 1.4 * math.tau
		r = 0.55 * (1 - 0.8 * t)
		pts.append((-0.35 + math.cos(a) * r, 0.1, 0.5 + math.sin(a) * r))
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w = 0.1 * (1 - 0.7 * k / 25)
		p.seg(u, v, w, w, CLOTH_WHITE, sides=6, glow=1.4)
	p.seg((-0.35, 0.1, -0.05), (0.9, 0.1, -0.05), 0.1, 0.02, CLOTH_WHITE, sides=6, glow=1.4)
	p.seg((-0.2, 0.1, 0.1), (0.7, 0.1, 0.1), 0.05, 0.02, RUNE, sides=5, glow=1.6)
	_arrow(p, (-0.95, -0.1, 0.35), (0.85, -0.1, 1.0), hs=1.3, r=0.045, glow=1.2, fletch=RUNE)   # ...carrying an arrow
	for k in range(3):
		p.seg((-0.2 + k * 0.35, -0.2, 0.62 + k * 0.1), (-0.65 + k * 0.35, -0.2, 0.45 + k * 0.1), 0.03, 0.0, RUNE, sides=4, glow=2.0)
	return p.build()


def gale_snare():
	p = Prop("gale_snare", 1005)
	p.blob((1.2, 0.7, 0.2), (0, 0.1, -0.05), HIDE, segs=(10, 4))                            # a tussock...
	for k in range(9):                                                                    # ...whose grass the wind knots
		x = -0.5 + k * 0.125
		pts = []
		for i in range(7):
			t = i / 6
			pts.append((x + math.sin(t * 2.2) * (0.35 - x * 0.3) * t, 0.05 * (k % 3), 0.0 + t * (0.75 + (k % 3) * 0.12)))
		for i, (u, v) in enumerate(zip(pts, pts[1:])):
			w = 0.055 * (1 - i / 7)
			p.seg(u, v, w, w * 0.8, LEAF if k % 2 else PINE, sides=4, glow=0.6)
	for k, z in enumerate((0.55, 0.78)):                                                  # into loops
		_ring(p, 0.38 - k * 0.06, z, 0.05, LEAF, glow=2.0, sides=18, tilt=0.5 + k * 0.4)
	for k, z in enumerate((0.35, 0.9, 1.15)):
		_wind(p, (-1.0, z), (-0.45 + k * 0.2, z + 0.05), r=0.04, y=-0.3, up=1 if k != 1 else -1)
	return p.build()


def skystorm_volley():
	p = Prop("skystorm_volley", 1007)
	_swirl(p, 0, 1.45, 0.05, 0.55, 1.8, RUNE, 1.6, thick=0.08)                             # an eye in the storm
	_swirl(p, 0, 1.45, 0.05, 0.42, 1.6, CLOTH_WHITE, 1.4, thick=0.05)
	for k in range(7):                                                                    # arrows fanning down from it
		a = math.radians(-150 + k * 20)
		base = (math.cos(a) * 0.45, -0.1, 1.3 + math.sin(a) * 0.35)
		tip = (math.cos(a) * 1.1, -0.1, 1.3 + math.sin(a) * 1.25)
		_arrow(p, base, tip, hs=0.7, r=0.028, fletch=RUNE)
	_ring(p, 0.8, -0.1, 0.035, CLOTH_RED, glow=1.6, sides=22)                               # on everything under it
	_bolt_line(p, [(0.05, 1.2), (-0.1, 0.8), (0.08, 0.72), (-0.05, 0.3)], 0.06, GOLD, 2.6, y=-0.15)
	return p.build()


def gale_buffet():
	p = Prop("gale_buffet", 1009)
	for x, z, s in ((-0.55, 0.55, 0.8), (-0.25, 0.85, 0.7), (-0.2, 0.3, 0.6), (-0.85, 0.35, 0.5), (-0.8, 0.8, 0.5)):   # a cloud...
		p.blob((s, s * 0.7, s * 0.8), (x, 0.1, z), CLOTH_WHITE, segs=(10, 6), glow=0.3)
	for sx in (-1, 1):                                                                    # ...with a face, puffing
		p.blob((0.12, 0.06, 0.14), (-0.45 + sx * 0.14, -0.2, 0.75), STONE_DARK, segs=(6, 4))
		p.blob((0.28, 0.2, 0.22), (-0.45 + sx * 0.24, -0.15, 0.5), CLOTH_WHITE, segs=(8, 6), glow=0.4)
	_ring_at(p, -0.2, 0.52, 0.09, 0.03, STONE_DARK, sides=10, y=-0.26)
	for k, z in enumerate((0.25, 0.52, 0.8)):                                             # blowing hard
		_wind(p, (-0.05, 0.52 + (z - 0.52) * 0.3), (0.85 + (k == 1) * 0.15, z), r=0.055, up=1 if k < 2 else -1, y=-0.2,
			  swatch=RUNE if k == 1 else CLOTH_WHITE)
	return p.build()


def thunder_strike():
	p = Prop("thunder_strike", 1011)
	p.blob((0.4, 0.3, 0.6), (0, 0, 0.9), WATER, segs=(10, 6), glow=0.4)                       # a thunderbird
	p.blob((0.28, 0.26, 0.28), (0, -0.05, 1.25), WATER, segs=(8, 6), glow=0.4)
	p.seg((0, -0.18, 1.25), (0.05, -0.38, 1.18), 0.07, 0.0, GOLD, sides=5)
	for sx in (-1, 1):
		p.blob((0.07, 0.05, 0.07), (sx * 0.08, -0.16, 1.3), GOLD, segs=(5, 3), glow=2.8)
		_feather_fan(p, sx * 0.15, 1.0, [90 - sx * 90 + sx * d for d in (-25, -5, 15, 35, 55)], 0.8, WATER, tip=CLOTH_WHITE, glow=0.5, r=0.1)
	_feather_fan(p, 0, 0.7, (250, 270, 290), 0.35, WATER, tip=CLOTH_WHITE, glow=0.5, r=0.08)
	_bolt_line(p, [(0.05, 0.55), (-0.18, 0.2), (0.1, 0.12), (-0.12, -0.35)], 0.09, GOLD, 2.8, y=-0.2)   # loosing lightning
	for sx in (-1, 1):
		_bolt_line(p, [(sx * 0.95, 1.05), (sx * 1.05, 0.8), (sx * 0.92, 0.72), (sx * 1.02, 0.45)], 0.045, GOLD, 2.4, y=-0.1)
	return p.build()


def barrow_chill():
	p = Prop("barrow_chill", 1013)
	p.blob((1.4, 0.8, 0.28), (0, 0.1, -0.08), PINE, segs=(12, 5))                           # out of the barrow's earth...
	_hand(p, 0.0, 0.5, 1.15, SEAFOAM, glow=1.3, curl=0.45)                                  # ...a wight's hand
	for k, (x, z, s) in enumerate(((-0.55, 0.35, 0.3), (0.5, 0.5, 0.26), (-0.4, 0.85, 0.2), (0.45, 0.95, 0.18))):   # a chill mist
		p.blob((s, s * 0.6, s * 0.7), (x, 0.15, z), SEAFOAM, segs=(8, 5), glow=0.8)
	_snowflake(p, 0.62, 1.3, 0.16, 2.0)
	_snowflake(p, -0.6, 1.15, 0.12, 2.0)
	return p.build()


def trample():
	p = Prop("trample", 1015)
	p.blob((2.0, 1.4, 0.16), (0, 0, -0.05), STONE_WARM, segs=(14, 5))                        # the ground
	for k in range(7):                                                                    # cracked
		a = k * math.tau / 7 + 0.2
		p.seg((0, 0, 0.04), (math.cos(a) * 0.9, math.sin(a) * 0.65, 0.04), 0.05, 0.01, STONE_DARK, sides=4)
	p.seg((0.15, 0.05, 1.5), (0.02, 0.05, 0.55), 0.26, 0.22, HIDE, sides=10)                 # a great beast's leg...
	p.blob((0.62, 0.62, 0.3), (0.02, 0.05, 0.5), HIDE, segs=(10, 6))                          # its shaggy fetlock
	for sx in (-1, 1):                                                                    # ...its cloven hoof stamping
		p.blob((0.3, 0.52, 0.42), (sx * 0.14, 0.0, 0.2), STONE_DARK, segs=(10, 6), grad=(0.3, 0.9))
	for k in range(9):                                                                    # the impact
		a = math.pi * (0.05 + k * 0.11)
		p.seg((math.cos(a) * 0.55, -0.35, 0.05 + math.sin(a) * 0.35), (math.cos(a) * 0.9, -0.35, 0.05 + math.sin(a) * 0.6),
			  0.045, 0.0, AMBER, sides=4, glow=2.0)
	for x, z, s in ((-0.6, 0.15, 0.22), (0.62, 0.12, 0.2)):                                # dust
		p.blob((s, s * 0.8, s * 0.7), (x, -0.25, z), MIST, segs=(8, 5))
	return p.build()


def vayuketh_breath():
	p = Prop("vayuketh_breath", 1017)
	_elephant(p)
	for s_ in (-1, 1):                                                                    # great ears, spread like sails
		p.blob((0.08, 0.95, 1.0), (s_ * 0.42, 0.32, 0.5), STONE_LIGHT, rot=(0, 0, s_ * 12), segs=(12, 8))
		for k in range(16):                                                               # rimmed in sky
			a0, a1 = k * math.tau / 16, (k + 1) * math.tau / 16
			pt = lambda a: Vector((0, math.cos(a) * 0.47, math.sin(a) * 0.5))
			rot = Matrix.Rotation(math.radians(s_ * 12), 3, "Z")
			off = Vector((s_ * 0.42 - s_ * 0.05, 0.32, 0.5))
			p.seg(tuple(rot @ pt(a0) + off), tuple(rot @ pt(a1) + off), 0.03, 0.03, RUNE, sides=4, glow=1.8)
	for k, (dx, dz, c, up) in enumerate(((-0.3, 0.5, 0.13, -1), (0.02, 0.7, 0.14, 1), (0.32, 0.45, 0.12, 1))):   # the trunk raised, breathing wind
		_wind(p, (0.0, 0.9), (dx, 0.9 + dz), r=0.05, up=up, y=-0.45, swatch=RUNE if k == 1 else CLOTH_WHITE, curl=c, glow=1.8)
	return p.build()


LEVEL_40 = [skybreaker, rallying_standard, gale_cleave, sunrise_ward, radiant_smite, circle_of_radiance, tempest_lance, windshear, skyfall,
			windstep_strike, razor_wind, assassins_mark, skyforge_mantle, cyclone_blast, elemental_maelstrom, barrow_rot, unholy_frenzy,
			soul_eater, windbite_curse, spirit_of_the_plains, gale_of_torpor, windrider_shot, gale_snare, skystorm_volley,
			gale_buffet, thunder_strike, barrow_chill, trample, vayuketh_breath]


# ---------------------------------------------------------------- the magician's bolts: each flies out of a summoning ring

def _conjure_ring(p, cx, cz, r, swatch, runes=None, glow=2.0, y=0.12):
	"""The magician's portal: a ring in the picture plane with four rune studs (one swatch each, or all `swatch`)."""
	_ring_at(p, cx, cz, r, 0.045, swatch, glow=glow, sides=20, y=y)
	_ring_at(p, cx, cz, r * 0.7, 0.022, swatch, glow=glow * 0.8, sides=16, y=y)
	for k in range(4):
		a = math.radians(45 + k * 90)
		sw = runes[k] if runes else swatch
		c = (cx + math.cos(a) * r, y - 0.03, cz + math.sin(a) * r)
		p.blob((0.1, 0.06, 0.1), c, sw, rot=(0, 45, 0), segs=(4, 2), glow=glow + 0.6)
	p.blob((r * 1.2, 0.03, r * 1.2), (cx, y + 0.05, cz), STONE_DARK, segs=(12, 6))           # the dark beyond it


RING = (-0.55, 0.12, 0.3)   # where the ring stands (x, z, radius): low left, the bolt bursting out of it up and right


def cinder_dart():
	p = Prop("cinder_dart", 1101)
	_conjure_ring(p, *RING, EMBER)
	a, b = Vector((-0.5, 0, 0.15)), Vector((0.55, 0, 0.9))
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	root = b - d * 0.75
	p.seg(tuple(root), tuple(b), 0.17, 0.0, STONE_DARK, sides=4, twist=45)                 # a stubby dart of black cinder
	p.seg(tuple(root), tuple(root - d * 0.18), 0.17, 0.05, STONE_DARK, sides=4, twist=45)
	for k in range(3):                                                                    # glowing through its cracks
		c0 = root + d * (0.1 + k * 0.2) + n * (0.05 if k % 2 else -0.05) - Vector((0, 0.13, 0))
		p.seg(tuple(c0), tuple(c0 + d * 0.16 + n * (-0.07 if k % 2 else 0.07)), 0.035, 0.02, EMBER, sides=4, glow=3.0)
	p.blob((0.1, 0.1, 0.1), tuple(b), FLAME, segs=(6, 4), glow=3.2)                         # its hot point
	for sgn in (-1, 1):                                                                   # fletched with flames
		p.seg(tuple(root), tuple(root - d * 0.4 + n * sgn * 0.22), 0.1, 0.0, FLAME, sides=5, glow=2.4)
	p.seg(tuple(root), tuple(root - d * 0.45), 0.09, 0.0, EMBER, sides=5, glow=2.4)
	for k in range(6):                                                                    # shedding cinders
		t = k / 5
		c = root - d * (0.3 + t * 0.55) + n * math.sin(k * 2.1 + 1) * 0.2
		s = 0.12 - t * 0.05
		p.rock((s, s, s), tuple(c), STONE_DARK, jitter=0.2)
		p.blob((s * 0.55, s * 0.55, s * 0.55), tuple(c - Vector((0, s * 0.6, 0))), EMBER if k % 2 else FLAME, segs=(5, 3), glow=3.0)
	return p.build()


def elemental_bolt():
	p = Prop("elemental_bolt", 1103)
	_conjure_ring(p, *RING, GOLD, runes=[FLAME, WATER, STONE_WARM, CLOTH_WHITE])
	head = Vector((0.45, -0.05, 0.8))
	tail = Vector((-0.55, -0.05, 0.12))
	d = (head - tail).normalized()
	n = Vector((-d.z, 0, d.x))
	L = (head - tail).length
	for j, sw in enumerate((FLAME, WATER, LEAF, CLOTH_WHITE)):                            # four elements braided into one bolt
		pts = []
		for k in range(25):
			t = k / 24
			ph = t * 1.6 * math.tau + j * math.tau / 4
			rr = 0.24 * (1 - t) + 0.05
			pts.append(tail + d * L * t + n * math.cos(ph) * rr + Vector((0, -1, 0)) * math.sin(ph) * rr)
		for k, (u, v) in enumerate(zip(pts, pts[1:])):
			w = 0.035 + 0.045 * k / 24
			p.seg(tuple(u), tuple(v), w, w, sw, sides=5, glow=2.0)
	p.blob((0.36, 0.36, 0.36), tuple(head + d * 0.08), CLOTH_WHITE, segs=(10, 8), glow=3.0)   # a white-hot core
	for j, sw in enumerate((FLAME, WATER, LEAF, GOLD)):                                   # the four orbiting it
		a = math.radians(45 + j * 90)
		p.blob((0.15, 0.15, 0.15), tuple(head + d * 0.08 + Vector((math.cos(a) * 0.3, -0.15, math.sin(a) * 0.3))), sw, segs=(6, 4), glow=2.4)
	return p.build()


def earthen_shard():
	p = Prop("earthen_shard", 1105)
	_conjure_ring(p, *RING, AMBER)
	a, b = Vector((-0.4, 0, 0.2)), Vector((0.6, 0, 0.95))
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	ang = -math.degrees(math.atan2(d.z, d.x))
	mid = (a + b) / 2
	p.rock((1.05, 0.4, 0.34), tuple(mid), STONE_WARM, rot=(0, ang, 0), jitter=0.12)        # a jagged shard of stone
	p.seg(tuple(mid + d * 0.3), tuple(b + d * 0.15), 0.16, 0.0, STONE_WARM, sides=4, twist=30)   # its point
	p.rock((0.36, 0.34, 0.3), tuple(a + d * 0.05 + n * 0.1), CLAY, rot=(0, ang, 0), jitter=0.15)   # torn from the bedrock
	for k in range(3):                                                                    # amber cracks down its face
		c0 = a + d * (0.25 + k * 0.22) + n * (0.07 if k % 2 else -0.07) - Vector((0, 0.2, 0))
		c1 = c0 + d * 0.2 + n * (-0.1 if k % 2 else 0.1)
		p.seg(tuple(c0), tuple(c1), 0.045, 0.025, AMBER, sides=4, glow=2.8)
	for k, (t, side, s) in enumerate(((0.05, 1, 0.13), (0.3, -1, 0.11), (0.55, 1, 0.09), (0.2, 1.8, 0.08), (0.45, -1.7, 0.07))):   # pebbles flung alongside
		p.rock((s, s, s), tuple(a + d * t + n * side * 0.28 - Vector((0, 0.1, 0))), STONE_WARM if k % 2 else CLAY, jitter=0.2)
	return p.build()


def scalding_torrent():
	p = Prop("scalding_torrent", 1107)
	_conjure_ring(p, *RING, WATER)
	pts = []
	for k in range(15):                                                                   # a gushing jet of water
		t = k / 14
		pts.append(Vector((-0.55 + t * 1.15, -0.05, 0.12 + t * 0.5 + math.sin(t * math.pi * 1.5) * 0.1)))
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w0, w1 = 0.13 + 0.17 * k / 14, 0.13 + 0.17 * (k + 1) / 14
		p.seg(tuple(u), tuple(v), w0, w1, WATER, sides=8, glow=1.3)
		if k % 3 == 1:
			p.seg(tuple(u - Vector((0, w0 * 0.9, 0))), tuple(v - Vector((0, w1 * 0.9, 0))), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=1.8)
	end = pts[-1]
	for k in range(6):                                                                    # bursting at its head
		a = math.radians(-70 + k * 28)
		p.seg(tuple(end), tuple(end + Vector((math.cos(a) * 0.38, -0.1, math.sin(a) * 0.38))), 0.09, 0.0, WATER, sides=5, glow=1.6)
	for x, z, s in ((-0.25, 0.55, 0.2), (0.05, 0.8, 0.24), (0.38, 1.0, 0.26)):             # boiling off in billows of steam
		p.blob((s, s * 0.8, s * 0.8), (x, -0.05, z), CLOTH_WHITE, segs=(8, 5), glow=0.7)
		p.blob((s * 0.75, s * 0.6, s * 0.65), (x + s * 0.8, -0.05, z + s * 0.35), MIST, segs=(8, 5), glow=0.5)
		p.blob((s * 0.6, s * 0.5, s * 0.55), (x - s * 0.7, -0.05, z + s * 0.25), CLOTH_WHITE, segs=(8, 5), glow=0.7)
	return p.build()


def spear_of_flame():
	p = Prop("spear_of_flame", 1109)
	_conjure_ring(p, *RING, FLAME)
	a, b = Vector((-0.65, 0, 0.05)), Vector((0.35, 0, 0.9))
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(tuple(a), tuple(b), 0.09, 0.11, EMBER, sides=6, glow=2.2)                        # a long haft of living flame
	p.seg(tuple(b), tuple(b + d * 0.7), 0.24, 0.0, FLAME, sides=4, glow=2.6, twist=45)     # a broad head, white-hot at its heart
	p.seg(tuple(b - Vector((0, 0.13, 0))), tuple(b + d * 0.45 - Vector((0, 0.13, 0))), 0.08, 0.0, CLOTH_WHITE, sides=4, glow=3.0)
	p.seg(tuple(b - n * 0.28), tuple(b + n * 0.28), 0.07, 0.07, EMBER, sides=5, glow=2.4)  # its crossguard
	for k in range(6):                                                                    # flames licking back along the haft
		t = 0.12 + k * 0.14
		base = a + (b - a) * t
		sgn = 1 if k % 2 else -1
		p.seg(tuple(base), tuple(base - d * 0.3 + n * sgn * 0.28), 0.1, 0.0, FLAME if k % 2 else EMBER, sides=5, glow=2.4)
	return p.build()


def storm_javelin():
	p = Prop("storm_javelin", 1111)
	_conjure_ring(p, *RING, RUNE)
	a, b = Vector((-0.55, 0, 0.15)), Vector((0.4, 0, 0.85))
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	zig = [a]                                                                             # a javelin forked out of lightning
	for k in range(1, 5):
		zig.append(a + (b - a) * (k / 5) + n * (0.11 if k % 2 else -0.11))
	zig.append(b)
	for u, v in zip(zig, zig[1:]):
		p.seg(tuple(u), tuple(v), 0.075, 0.075, GOLD, sides=5, glow=2.8)
	p.seg(tuple(b), tuple(b + d * 0.5), 0.17, 0.0, CLOTH_WHITE, sides=4, glow=3.0, twist=45)   # a white point
	for sgn in (-1, 1):                                                                   # barbed with sparks
		p.seg(tuple(b), tuple(b - d * 0.2 + n * sgn * 0.24), 0.05, 0.0, GOLD, sides=4, glow=2.8)
	for off, up, sw in ((0.3, 1, CLOTH_WHITE), (-0.3, -1, CLOTH_WHITE)):                  # riding two gusts of wind
		s0, s1 = a + n * off + d * 0.05, b + n * off * 0.55 - d * 0.1
		_wind(p, (s0.x, s0.z), (s1.x, s1.z), swatch=sw, up=up, y=-0.1, r=0.07, curl=0.14, glow=1.8)
	return p.build()


MAGE_BOLTS = [cinder_dart, elemental_bolt, earthen_shard, scalding_torrent, spear_of_flame, storm_javelin]


# ---------------------------------------------------------------- level 45: the summit, the storm and the open sky

def _cloud(p, cx, cz, s, swatch=CLOTH_WHITE, glow=0.4, y=0.0, depth=0.7):
	"""A puffy cloud in the picture plane, about 2.2 s wide."""
	for dx, dz, d in ((-0.62, -0.05, 0.75), (-0.22, 0.22, 0.95), (0.3, 0.18, 0.85), (0.7, -0.04, 0.7), (0.02, -0.14, 0.8)):
		p.blob((d * s, d * s * depth, d * s * 0.85), (cx + dx * s, y, cz + dz * s), swatch, segs=(10, 6), glow=glow)


def _gauntlet(p, sx, fist, glow=0.0):
	"""A mailed arm reaching in from one side (sx = -1 left, 1 right) to a fist at `fist` (x, z)."""
	fx, fz = fist
	p.seg((sx * 1.05, 0.05, fz - 0.35), (fx + sx * 0.22, 0.0, fz - 0.05), 0.13, 0.12, IRON, sides=8)
	p.seg((sx * 0.98, 0.05, fz - 0.37), (sx * 0.8, 0.05, fz - 0.3), 0.19, 0.18, STONE_DARK, sides=8)
	p.blob((0.42, 0.36, 0.38), (fx, 0.0, fz), IRON, segs=(10, 6), glow=glow)
	for k in range(3):                                                                    # knuckle plates
		p.blob((0.12, 0.12, 0.1), (fx - sx * 0.1, -0.16, fz + 0.1 - k * 0.1), STONE_LIGHT, segs=(6, 4))


def thunderclap_strike():
	p = Prop("thunderclap_strike", 1201)
	cx, cz = 0.0, 0.7
	p.blob((0.4, 0.3, 0.4), (cx, 0.1, cz), CLOTH_WHITE, segs=(10, 6), glow=3.0)              # a thunderclap...
	for k in range(12):
		a = k * math.tau / 12 + 0.13
		r1 = 1.0 if k % 2 else 0.72
		p.seg((cx + math.cos(a) * 0.2, 0.15, cz + math.sin(a) * 0.2), (cx + math.cos(a) * r1, 0.15, cz + math.sin(a) * r1), 0.07, 0.0,
			  GOLD if k % 2 else CLOTH_WHITE, sides=4, glow=2.6)
	for rad in (0.6, 0.85):
		for a0, a1 in ((math.radians(40), math.radians(140)), (math.radians(220), math.radians(320))):
			_ring_at(p, cx, cz, rad, 0.035, RUNE, glow=2.0, sides=8, a0=a0, a1=a1, y=0.1)
	for sx in (-1, 1):                                                                    # ...between two mailed fists, clapped
		fx, fz = sx * 0.27, cz - 0.05
		p.seg((sx * 0.95, -0.1, 0.05), (fx + sx * 0.12, -0.2, fz - 0.12), 0.15, 0.13, IRON, sides=8)
		p.seg((sx * 0.98, -0.08, 0.0), (sx * 0.82, -0.1, 0.14), 0.2, 0.2, CLOTH_RED, sides=8)
		p.blob((0.42, 0.4, 0.46), (fx, -0.25, fz), STONE_LIGHT, segs=(10, 6))
		for k in range(4):                                                                # knuckle plates
			p.blob((0.13, 0.1, 0.11), (fx - sx * 0.17, -0.3, fz + 0.15 - k * 0.1), IRON, segs=(6, 4))
		p.seg((fx + sx * 0.02, -0.4, fz + 0.12), (fx - sx * 0.08, -0.45, fz - 0.12), 0.06, 0.06, IRON, sides=6)   # thumb
	for x, z in ((-0.62, 1.45), (0.6, 1.5)):                                             # stunned stars
		_star(p, x, z, 0.11, GOLD, glow=2.4, y=-0.3)
	return p.build()


def bulwark_of_the_sky():
	p = Prop("bulwark_of_the_sky", 1203)
	outline = [(-0.52, 1.35), (0.52, 1.35), (0.56, 0.62), (0.0, -0.15), (-0.56, 0.62)]      # a tower shield, sky blue...
	icons._slab(p, outline, -0.05, 0.12, WATER, grad=(0.05, 0.7))
	edge = outline + outline[:1]
	for u, v in zip(edge, edge[1:]):
		p.seg((u[0], -0.07, u[1]), (v[0], -0.07, v[1]), 0.055, 0.055, GOLD, sides=5, glow=1.0)
	p.seg((0, -0.08, 1.33), (0, -0.08, -0.1), 0.03, 0.03, GOLD, sides=4, glow=1.0)
	_cloud(p, 0.0, 0.72, 0.3, glow=1.0, y=-0.14)                                           # ...with a cloud on it
	for sx in (-1, 1):                                                                    # winged, standing in the sky
		_feather_fan(p, sx * 0.5, 1.05, [90 - sx * 90 + sx * d for d in (-35, -15, 5, 25, 45)], 0.62, CLOTH_WHITE, tip=RUNE, glow=0.8, r=0.08)
	return p.build()


def tempest_whirl():
	p = Prop("tempest_whirl", 1205)
	cx, cz = 0.0, 0.62
	pts = []                                                                              # a spinning tempest of a swing...
	for k in range(49):
		t = k / 48
		a = math.radians(150) - t * 1.75 * math.tau
		r = 0.95 - 0.35 * t
		pts.append((cx + math.cos(a) * r, 0.1, cz + math.sin(a) * r))
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w = 0.02 + 0.07 * (k / 48)
		p.seg(u, v, w, w, RUNE if (k // 8) % 2 else CLOTH_WHITE, sides=5, glow=2.0)
	d = Vector((0.75, 0, 0.66)).normalized()                                              # ...from a greatsword swung round
	base = Vector((cx, -0.15, cz)) - d * 0.35
	tip = base + d * 1.2
	n = Vector((-d.z, 0, d.x))
	p.seg(tuple(base), tuple(tip), 0.14, 0.02, STONE_LIGHT, sides=4)
	p.seg(tuple(base + d * 0.05 - Vector((0, 0.1, 0))), tuple(tip - Vector((0, 0.1, 0))), 0.03, 0.0, CLOTH_WHITE, sides=4, glow=2.4)
	p.seg(tuple(base - n * 0.3), tuple(base + n * 0.3), 0.06, 0.06, GOLD, sides=5)
	p.seg(tuple(base), tuple(base - d * 0.35), 0.055, 0.055, WOOD, sides=6)
	p.blob((0.15, 0.15, 0.15), tuple(base - d * 0.38), GOLD, segs=(6, 4))
	for a in (math.radians(200), math.radians(290), math.radians(20), math.radians(110)):   # every foe it catches
		x, z = cx + math.cos(a) * 1.05, cz + math.sin(a) * 1.05
		for j in range(4):
			b = j * math.pi / 2 + 0.4
			p.seg((x, -0.2, z), (x + math.cos(b) * 0.17, -0.2, z + math.sin(b) * 0.17), 0.045, 0.0, CLOTH_RED, sides=4, glow=2.0)
	return p.build()


def zenith_ward():
	p = Prop("zenith_ward", 1207)
	_ring(p, 0.85, 0.0, 0.045, GOLD, glow=1.8, sides=24)                                   # over the group...
	for sx in (-1, 1):                                                                    # ...a beam from straight above
		p.seg((sx * 0.62, 0.1, 0.0), (sx * 0.2, 0.1, 1.35), 0.03, 0.03, GOLD, sides=4, glow=2.0)
	outline = [(-0.42, 1.0), (0.42, 1.0), (0.42, 0.52), (0.0, 0.02), (-0.42, 0.52)]          # a white shield
	icons._slab(p, outline, -0.05, 0.08, CLOTH_WHITE, grad=(0.1, 0.6))
	edge = outline + outline[:1]
	for u, v in zip(edge, edge[1:]):
		p.seg((u[0], -0.07, u[1]), (v[0], -0.07, v[1]), 0.045, 0.045, GOLD, sides=5, glow=1.2)
	p.box((0.12, 0.06, 0.42), (0, -0.1, 0.55), LEAF, glow=2.2)                               # its mending cross
	p.box((0.36, 0.06, 0.12), (0, -0.1, 0.62), LEAF, glow=2.2)
	cz = 1.45                                                                             # the sun at its zenith
	p.seg((0, 0.05, cz), (0, -0.05, cz), 0.22, 0.22, GOLD, sides=16, glow=2.8)
	for k in range(12):
		a = k * math.tau / 12
		r1 = 0.52 if k % 2 else 0.4
		p.seg((math.cos(a) * 0.27, -0.02, cz + math.sin(a) * 0.27), (math.cos(a) * r1, -0.02, cz + math.sin(a) * r1), 0.05, 0.0, FLAME, sides=4, glow=2.4)
	return p.build()


def _comet(p, x, z, dx, dz, s, glow=2.6, y=-0.1):
	"""A falling ball of fire at (x, z), its tail streaming back along (dx, dz)."""
	p.blob((0.3 * s, 0.3 * s, 0.3 * s), (x, y, z), FLAME, segs=(10, 6), glow=glow + 0.4)
	p.seg((x, y + 0.02, z), (x + dx * s, y + 0.02, z + dz * s), 0.15 * s, 0.0, EMBER, sides=6, glow=glow)
	p.seg((x, y - 0.03, z), (x + dx * s * 0.7 + 0.05, y - 0.03, z + dz * s * 0.7), 0.07 * s, 0.0, FLAME, sides=5, glow=glow)


def skyfire_judgment():
	p = Prop("skyfire_judgment", 1209)
	cz = 1.45                                                                             # the scales of judgment...
	p.seg((0, 0.1, cz - 0.4), (0, 0.1, cz + 0.12), 0.04, 0.04, GOLD, sides=6, glow=1.2)
	p.blob((0.1, 0.1, 0.1), (0, 0.1, cz + 0.16), GOLD, segs=(6, 4), glow=1.2)
	p.seg((-0.6, 0.1, cz), (0.6, 0.1, cz), 0.035, 0.035, GOLD, sides=5, glow=1.2)
	for sx in (-1, 1):
		for dx in (-0.1, 0.1):
			p.seg((sx * 0.6, 0.1, cz), (sx * 0.6 + dx, 0.1, cz - 0.3), 0.012, 0.012, GOLD, sides=4, glow=1.2)
		p.blob((0.34, 0.24, 0.08), (sx * 0.6, 0.1, cz - 0.32), GOLD, segs=(10, 4), glow=1.2)
	p.blob((2.0, 1.4, 0.14), (0, 0.2, -0.05), STONE_WARM, segs=(14, 5))                     # ...pouring fire on the ground
	for x, z, s in ((-0.55, 0.55, 0.9), (0.15, 0.3, 1.1), (0.7, 0.75, 0.8)):
		_comet(p, x, z, -0.15, 0.55, s)
	for k in range(9):                                                                    # where it lands
		a = math.pi * (0.05 + k * 0.11)
		p.seg((0.15 + math.cos(a) * 0.28, -0.3, 0.02 + math.sin(a) * 0.15), (0.15 + math.cos(a) * 0.6, -0.3, 0.02 + math.sin(a) * 0.4),
			  0.04, 0.0, FLAME, sides=4, glow=2.2)
	return p.build()


def breath_of_life():
	p = Prop("breath_of_life", 1211)
	_ring(p, 0.9, 0.0, 0.04, GOLD, glow=1.6, sides=24)                                     # for the group...
	p.box((0.26, 0.14, 0.8), (0.1, -0.05, 0.72), LEAF, glow=2.4)                              # ...healing...
	p.box((0.72, 0.14, 0.26), (0.1, -0.05, 0.8), LEAF, glow=2.4)
	for k, (z0, z1, sw, up) in enumerate(((0.25, 0.45, GOLD, 1), (1.2, 1.1, CLOTH_WHITE, -1))):   # ...on a warm wind
		_wind(p, (-1.0, z0), (0.75, z1), swatch=sw, r=0.08, up=up, curl=0.2, glow=2.2, y=-0.3)
	_wind(p, (-1.05, 0.8), (-0.3, 0.82), swatch=GOLD, r=0.06, up=1, curl=0.14, glow=2.2, y=-0.3)
	for x, z, a in ((-0.6, 0.45, 30), (0.45, 1.3, -20), (-0.4, 1.05, 50), (0.75, 0.35, 10)):   # carrying leaves
		p.blob((0.3, 0.06, 0.14), (x, -0.4, z), LEAF, rot=(0, a, 0), segs=(8, 4), glow=1.2)
	return p.build()


def lightning_spear():
	p = Prop("lightning_spear", 1213)
	_cloud(p, -0.55, 1.2, 0.5, swatch=STONE_DARK, glow=0.0, y=0.2)                          # out of a storm cloud...
	_cloud(p, -0.3, 1.32, 0.34, swatch=MIST, glow=0.0, y=0.3)
	a, b = Vector((-0.5, -0.1, 0.95)), Vector((0.55, -0.1, 0.05))                            # ...a spear of lightning
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(tuple(a), tuple(b), 0.09, 0.09, RUNE, sides=6, glow=2.0)
	p.seg(tuple(a - Vector((0, 0.08, 0))), tuple(b - Vector((0, 0.08, 0))), 0.05, 0.05, CLOTH_WHITE, sides=6, glow=3.0)
	L = (b - a).length
	pts = [a + d * L * (k / 8) + n * (0.17 if k % 2 else -0.17) * (0 if k in (0, 8) else 1) - Vector((0, 0.12, 0)) for k in range(9)]
	for u, v in zip(pts, pts[1:]):
		p.seg(tuple(u), tuple(v), 0.055, 0.045, GOLD, sides=5, glow=2.8)
	outline = [(0, 0), (0.14, 0.18), (0, 0.62), (-0.14, 0.18)]                                 # its leaf-shaped point
	pt = [tuple(b + d * v + n * u) for u, v in outline]
	icons._slab(p, [(q[0], q[2]) for q in pt], -0.2, 0.0, CLOTH_WHITE, grad=(0.3, 0.9))
	for u, v in zip(pt, pt[1:] + pt[:1]):
		p.seg((u[0], -0.22, u[2]), (v[0], -0.22, v[2]), 0.03, 0.03, GOLD, sides=4, glow=2.6)
	tip = b + d * 0.62
	for k in range(6):                                                                    # striking
		ang = k * math.tau / 6 + 0.3
		p.seg(tuple(tip - Vector((0, 0.1, 0))), tuple(tip + Vector((math.cos(ang) * 0.3, -0.1, math.sin(ang) * 0.3))), 0.045, 0.0, RUNE, sides=4, glow=2.6)
	return p.build()


def cloudbind():
	p = Prop("cloudbind", 1215)
	_ring(p, 0.72, 0.0, 0.05, RUNE, glow=2.2, sides=22)                                    # held where it stands
	p.seg((0, 0.1, 0.0), (0, 0.1, 0.95), 0.22, 0.16, STONE_DARK, sides=8)                     # a foe...
	p.blob((0.34, 0.34, 0.36), (0, 0.1, 1.15), STONE_DARK, segs=(8, 6))
	for sx in (-1, 1):
		p.blob((0.08, 0.05, 0.06), (sx * 0.07, -0.07, 1.17), CLOTH_RED, segs=(5, 3), glow=2.6)
	for k, (z, r) in enumerate(((0.15, 0.45), (0.62, 0.36))):                             # ...wrapped in thick bands of cloud
		for j in range(12):
			a = j * math.tau / 12 + k * 0.4
			zz = z + math.sin(a + 0.8) * 0.12
			s = 0.36 + 0.06 * math.sin(a * 3)
			p.blob((s, s * 0.8, s * 0.72), (math.cos(a) * r, math.sin(a) * r * 0.7, zz), CLOTH_WHITE, segs=(8, 5), glow=0.7)
	return p.build()


def heavenfall():
	p = Prop("heavenfall", 1217)
	p.blob((2.2, 1.6, 0.14), (0, 0.2, -0.05), STONE_DARK, segs=(14, 5))                      # the ground
	for k in range(10):                                                                   # a ring of cloud, opening...
		a = k * math.tau / 10
		p.blob((0.4, 0.3, 0.3), (math.cos(a) * 0.62, math.sin(a) * 0.45, 1.55 + math.sin(a) * 0.05), CLOTH_WHITE, segs=(8, 5), glow=0.6)
	p.seg((0, 0, 1.5), (0, 0, 0.05), 0.3, 0.52, GOLD, sides=16, glow=2.0, grad=(0.3, 0.9))    # ...and heaven pouring down
	p.seg((0, -0.05, 1.5), (0, -0.05, 0.05), 0.14, 0.24, CLOTH_WHITE, sides=12, glow=3.0)
	_ring(p, 0.7, 0.04, 0.05, RUNE, glow=2.4, sides=24)                                     # on everything near it
	_ring(p, 0.95, 0.03, 0.03, CLOTH_WHITE, glow=2.0, sides=24)
	for k in range(8):
		a = k * math.tau / 8 + 0.2
		p.seg((math.cos(a) * 0.55, math.sin(a) * 0.4, 0.05), (math.cos(a) * 1.15, math.sin(a) * 0.8, 0.1), 0.05, 0.0, GOLD, sides=4, glow=2.4)
	for x, z in ((-0.62, 0.95), (0.62, 0.8)):
		_star(p, x, z, 0.09, CLOTH_WHITE, glow=2.6, y=-0.3)
	return p.build()


def cloudcutter():
	p = Prop("cloudcutter", 1219)
	d = Vector((0.85, 0, 0.55)).normalized()
	n = Vector((-d.z, 0, d.x))
	c = Vector((0.0, 0, 0.6))
	for sgn, sw in ((1, CLOTH_WHITE), (-1, CLOTH_WHITE)):                                   # a cloud, parted in two
		for t, s in ((-0.55, 0.36), (-0.2, 0.46), (0.18, 0.46), (0.52, 0.34)):
			q = c + d * t + n * sgn * (0.12 + s * 0.45)
			p.blob((s, s * 0.7, s * 0.8), tuple(q + Vector((0, 0.1, 0))), sw, segs=(10, 6), glow=0.5)
	a, b = c - d * 1.1, c + d * 0.75                                                      # by a cut of light
	p.seg(tuple(a - Vector((0, 0.1, 0))), tuple(c - Vector((0, 0.1, 0))), 0.01, 0.05, RUNE, sides=4, glow=2.6)
	p.seg(tuple(c - Vector((0, 0.1, 0))), tuple(b - Vector((0, 0.1, 0))), 0.05, 0.02, CLOTH_WHITE, sides=4, glow=3.0)
	_dagger(p, tuple(b + d * 0.05 - Vector((0, 0.2, 0))), tuple(b + d * 0.75 - Vector((0, 0.2, 0))), w=0.11, edge=CLOTH_WHITE)   # too quick to see
	for k in range(3):
		off = n * (k - 1) * 0.14
		p.seg(tuple(b - d * 0.35 + off - Vector((0, 0.25, 0))), tuple(b - d * 0.05 + off - Vector((0, 0.25, 0))), 0.0, 0.03, CLOTH_WHITE, sides=4, glow=2.0)
	return p.build()


def whirling_edges():
	p = Prop("whirling_edges", 1221)
	cx, cz = 0.0, 0.6
	for k in range(4):                                                                    # four blades, spinning
		a = k * math.pi / 2 + 0.3
		base = Vector((cx + math.cos(a) * 0.2, -0.05, cz + math.sin(a) * 0.2))
		t = a + math.pi / 2 - 0.5
		tip = base + Vector((math.cos(a) * 0.68 + math.cos(t) * 0.22, 0, math.sin(a) * 0.68 + math.sin(t) * 0.22))
		_dagger(p, tuple(base), tuple(tip), w=0.12, edge=CLOTH_WHITE)
		_crescent(p, cx, cz, 0.98, a + 0.35, a + 1.35, 0.07, RUNE if k % 2 else CLOTH_WHITE, glow=2.2, y=0.05)   # their trails
		_crescent(p, cx, cz, 0.78, a + 0.55, a + 1.25, 0.035, CLOTH_WHITE, glow=1.8, y=0.08)
	p.blob((0.3, 0.2, 0.3), (cx, -0.12, cz), GOLD, segs=(10, 6), glow=1.6)
	return p.build()


def hollow_heart():
	p = Prop("hollow_heart", 1223)
	cx, cz, s = 0.0, 0.75, 0.62
	outline = []
	for k in range(40):                                                                   # a heart, only its rim left...
		t = k * math.tau / 40
		x = 16 * math.sin(t) ** 3
		z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
		outline.append((cx + x / 16 * s, cz + z / 16 * s))
	for u, v in zip(outline, outline[1:] + outline[:1]):
		p.seg((u[0], 0.0, u[1]), (v[0], 0.0, v[1]), 0.11, 0.11, CRIMSON, sides=6, glow=0.6)
		p.seg((u[0], -0.1, u[1]), (v[0], -0.1, v[1]), 0.035, 0.035, CLOTH_RED, sides=4, glow=2.0)
	for k, z in enumerate((0.6, 0.9)):                                                    # ...the wind blowing through it
		_wind(p, (-0.95, z), (0.9, z + 0.05), r=0.045, up=1 if k else -1, y=0.0, swatch=CLOTH_WHITE if k else RUNE)
	for x, z, sz in ((0.0, -0.15, 0.3), (-0.12, -0.5, 0.24), (0.1, -0.78, 0.2), (-0.42, 0.25, 0.2), (0.45, 0.3, 0.22)):   # bleeding very heavily
		_drop(p, x, z, sz, CLOTH_RED, 1.4)
	return p.build()


def stormbound_mantle():
	p = Prop("stormbound_mantle", 1225)
	_elemental(p, RUNE, s=1.0, glow=0.5)                                                   # the pet...
	for sx in (-1, 1):
		p.blob((0.1, 0.06, 0.07), (sx * 0.07, -0.16, 0.98), GOLD, segs=(5, 3), glow=2.8)
	for k in range(7):                                                                    # ...cloaked in a storm cloud
		a = math.radians(-10 + k * 33)
		p.blob((0.34, 0.3, 0.26), (math.cos(a) * 0.42, 0.05, 0.72 + math.sin(a) * 0.22), STONE_DARK, segs=(8, 5))
	for x0, z0, sgn in ((-0.5, 0.7, -1), (0.5, 0.72, 1), (-0.3, 0.95, -1)):               # crackling
		_bolt_line(p, [(x0, z0), (x0 + sgn * 0.15, z0 - 0.12), (x0 + sgn * 0.08, z0 - 0.2), (x0 + sgn * 0.25, z0 - 0.42)], 0.035, GOLD, 2.8, y=-0.25)
	for x in (0.72, 0.9):                                                                 # made stronger
		p.seg((x, -0.3, 0.55 + (x - 0.72)), (x, -0.3, 0.95 + (x - 0.72)), 0.035, 0.035, GOLD, sides=4, glow=2.2)
		p.seg((x, -0.3, 1.02 + (x - 0.72)), (x, -0.3, 0.9 + (x - 0.72)), 0.09, 0.0, GOLD, sides=4, glow=2.2)
	return p.build()


def thunderhead():
	p = Prop("thunderhead", 1227)
	p.blob((1.9, 0.7, 0.3), (0, 0.15, 1.55), MIST, segs=(14, 6))                              # an anvil-topped thunderhead...
	_cloud(p, 0.0, 1.2, 0.55, swatch=STONE_DARK, glow=0.0, y=0.05)
	_cloud(p, 0.1, 1.05, 0.4, swatch=MIST, glow=0.0, y=-0.1)
	_bolt_line(p, [(0.05, 0.9), (-0.2, 0.55), (0.08, 0.48), (-0.12, 0.05)], 0.09, GOLD, 3.0, y=-0.3)   # ...breaking over the foe
	_bolt_line(p, [(-0.2, 0.55), (-0.45, 0.35)], 0.05, GOLD, 2.6, y=-0.3)
	for k in range(6):                                                                    # in sheets of rain
		x = -0.8 + k * 0.32
		if abs(x + 0.05) < 0.15:
			continue
		p.seg((x, -0.15, 0.85 - (k % 2) * 0.1), (x - 0.12, -0.15, 0.35 - (k % 2) * 0.1), 0.025, 0.015, RUNE, sides=4, glow=1.6)
	for k in range(7):
		a = math.pi * (0.05 + k * 0.15)
		p.seg((-0.12, -0.35, 0.0), (-0.12 + math.cos(a) * 0.4, -0.35, math.sin(a) * 0.3), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.4)
	return p.build()


def wrath_of_the_sky():
	p = Prop("wrath_of_the_sky", 1229)
	_ring(p, 0.95, 0.0, 0.045, CLOTH_RED, glow=1.8, sides=26)                               # on all near the target...
	for k in range(10):                                                                   # ...a funnel coming down
		z = 0.05 + k * 0.14
		r = 0.08 + (k / 9) ** 1.4 * 0.62
		_ring(p, r, z, 0.03, CLOTH_WHITE if k % 2 else RUNE, glow=1.6, sides=16, tilt=0.15)
	_cloud(p, 0.0, 1.55, 0.55, swatch=STONE_DARK, glow=0.0, y=0.1)                         # out of a wrathful sky
	for sx in (-1, 1):
		_bolt_line(p, [(sx * 0.7, 1.4), (sx * 0.85, 1.1), (sx * 0.72, 1.02), (sx * 0.95, 0.6)], 0.05, GOLD, 2.8, y=-0.3)
	for k in range(5):                                                                    # whipping debris round
		a = k * math.tau / 5 + 0.4
		r = 0.35 + k * 0.08
		p.rock((0.12, 0.1, 0.1), (math.cos(a) * r, math.sin(a) * r * 0.6, 0.3 + k * 0.2), STONE_WARM, jitter=0.2)
	return p.build()


def grave_wind():
	p = Prop("grave_wind", 1231)
	p.blob((1.0, 0.6, 0.16), (-0.6, 0.15, -0.05), PINE, segs=(10, 4))                        # out of a grave...
	outline = [(-0.9, 0.0), (-0.9, 0.62)] + [(-0.66 + math.cos(math.radians(a)) * 0.24, 0.62 + math.sin(math.radians(a)) * 0.24) for a in range(180, -1, -30)] + [(-0.42, 0.0)]
	icons._slab(p, outline, 0.1, 0.25, STONE_LIGHT, grad=(0.1, 0.7))
	p.box((0.06, 0.04, 0.3), (-0.66, 0.08, 0.45), STONE_DARK)
	p.box((0.2, 0.04, 0.06), (-0.66, 0.08, 0.52), STONE_DARK)
	for k, (z0, z1, sw) in enumerate(((0.3, 0.15, SICKLY), (0.62, 0.62, SEAFOAM), (0.95, 1.12, SICKLY))):   # ...a sickly wind
		_wind(p, (-0.6, z0), (0.95, z1), swatch=sw, r=0.06, up=1 if k != 1 else -1, curl=0.16, glow=1.8, y=0.1)
	_skull(p, 0.2, 0.68, 0.72, eyes=SICKLY, eye_glow=3.2)                                    # with the dead riding it
	p.seg((0.02, 0.15, 0.86), (-0.45, 0.2, 1.0), 0.16, 0.0, SICKLY, sides=6, glow=1.2)
	p.seg((0.02, 0.15, 0.5), (-0.4, 0.2, 0.42), 0.12, 0.0, SICKLY, sides=6, glow=1.2)
	return p.build()


def deathless_fury():
	p = Prop("deathless_fury", 1233)
	for x, z, s in ((0.0, 0.55, 0.9), (-0.4, 0.4, 0.62), (0.4, 0.4, 0.62)):               # purple fire...
		_fl(p, x, 0.2, z, s, glow=2.2, core=PURPLE, tongue=PURPLE)
	for sgn in (-1, 1):                                                                   # ...round crossed bones
		_bone(p, (sgn * -0.55, -0.05, 0.05), (sgn * 0.55, -0.05, 0.7), 0.05)
	_skull(p, 0.0, 0.75, 0.8, eyes=PURPLE, eye_glow=3.2)                                   # the undying skull
	for k in range(3):                                                                    # in a frenzy
		_crescent(p, 0.0, 0.75, 0.62 + k * 0.1, math.radians(20), math.radians(70), 0.035, PURPLE, glow=2.4, y=-0.3)
	return p.build()


def breathtaker():
	p = Prop("breathtaker", 1235)
	fx, fz = -0.62, 0.55                                                                  # a foe's pale face, gasping...
	p.blob((0.5, 0.42, 0.62), (fx, 0.05, fz), CLOTH_WHITE, segs=(10, 8))
	for sx in (-1, 1):
		p.blob((0.1, 0.05, 0.08), (fx + sx * 0.11, -0.17, fz + 0.1), STONE_DARK, segs=(6, 4))
	_ring_at(p, fx + 0.02, fz - 0.14, 0.07, 0.025, STONE_DARK, sides=10, y=-0.2)
	pts = []                                                                              # ...its last breath drawn out of it
	for k in range(21):
		t = k / 20
		pts.append((fx + 0.1 + t * 0.95, -0.2, fz - 0.1 + math.sin(t * math.pi) * 0.4 + t * 0.12))
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w = 0.03 + 0.05 * math.sin(math.pi * k / 20)
		p.seg(u, v, w, w, CLOTH_WHITE, sides=6, glow=1.8)
	_swirl(p, 0.45, 0.6, 0.03, 0.42, 1.6, PURPLE, 2.2, thick=0.09)                          # into a dark vortex
	p.blob((0.2, 0.1, 0.2), (0.45, -0.05, 0.6), STONE_DARK, segs=(8, 5))
	_heart(p, 0.62, 1.25, 0.2, swatch=CLOTH_RED, y=-0.2, depth=0.1, rim=FLAME, glow=2.0)       # and you live on it
	return p.build()


def hailbite_curse():
	p = Prop("hailbite_curse", 1237)
	_cloud(p, -0.05, 1.3, 0.45, swatch=WATER, glow=0.4, y=0.1)                              # a biting cold cloud...
	_cloud(p, 0.1, 1.42, 0.3, swatch=CLOTH_WHITE, glow=0.6, y=0.0)
	p.rock((1.1, 0.7, 0.35), (0.05, 0.1, 0.0), STONE_DARK, jitter=0.1)                       # ...battering a foe
	for k in range(5):
		a = k * math.tau / 5 + 0.4
		p.seg((0.05, -0.2, 0.2), (0.05 + math.cos(a) * 0.45, -0.2, 0.2 + math.sin(a) * 0.12), 0.03, 0.01, CLOTH_WHITE, sides=4, glow=2.0)
	for x, z, s in ((-0.55, 0.85, 0.18), (-0.15, 0.62, 0.22), (0.35, 0.9, 0.17), (0.6, 0.55, 0.2), (0.1, 0.32, 0.2), (-0.45, 0.4, 0.16)):   # with hailstones
		p.rock((s, s, s), (x, -0.2, z), CLOTH_WHITE, jitter=0.15)
		p.seg((x + 0.04, -0.15, z + 0.08), (x + 0.12, -0.15, z + 0.35), 0.03, 0.0, RUNE, sides=4, glow=1.8)
	_snowflake(p, 0.8, 1.05, 0.14, 2.2)
	return p.build()


def spirit_of_the_summit():
	p = Prop("spirit_of_the_summit", 1239)
	p.seg((0.0, 1.3, 0.0), (0.0, 1.3, 1.6), 1.0, 0.0, STONE_DARK, sides=5, grad=(0.1, 0.6))   # a mountain...
	p.seg((0.0, 1.3, 1.1), (0.0, 1.3, 1.6), 0.33, 0.0, CLOTH_WHITE, sides=5, glow=0.4)
	hx, hz = 0.0, 0.66                                                                    # ...and the spirit ram of its summit
	p.blob((0.66, 0.56, 0.66), (hx, -0.3, hz), CLOTH_WHITE, segs=(10, 8), glow=1.0)
	p.seg((hx, -0.42, hz - 0.08), (hx, -0.55, hz - 0.55), 0.22, 0.15, CLOTH_WHITE, sides=8, glow=1.0)   # its long face
	p.blob((0.26, 0.16, 0.14), (hx, -0.68, hz - 0.55), STONE_LIGHT, segs=(8, 5))
	for sx in (-1, 1):
		p.blob((0.12, 0.05, 0.09), (hx + sx * 0.16, -0.6, hz + 0.02), RUNE, segs=(5, 3), glow=3.0)
		c = (hx + sx * 0.46, hz + 0.02)                                                    # great curled horns
		pts = []
		for k in range(22):
			t = k / 21
			a = math.radians(160) - t * 1.3 * math.tau
			r = 0.34 * (1 - 0.65 * t)
			pts.append((c[0] + sx * math.cos(a) * r, -0.2, c[1] + math.sin(a) * r))
		for i, (u, v) in enumerate(zip(pts, pts[1:])):
			w = 0.12 * (1 - 0.6 * i / 21)
			p.seg(u, v, w, w * 0.95, GOLD, sides=6, glow=0.8)
	_ring(p, 0.9, 0.0, 0.04, GOLD, glow=1.8, sides=24)                                     # watching over the group
	return p.build()


def stillness_of_stone():
	p = Prop("stillness_of_stone", 1241)
	for z in (0.0, 1.3):                                                                  # an hourglass...
		p.box((0.95, 0.6, 0.14), (0, 0, z), STONE_DARK, jitter=0.02)
	for k in range(3):
		a = k * math.tau / 3 + 0.5
		p.seg((math.cos(a) * 0.38, math.sin(a) * 0.22, 0.05), (math.cos(a) * 0.38, math.sin(a) * 0.22, 1.25), 0.05, 0.05, STONE_LIGHT, sides=6)
	p.seg((0, 0, 1.23), (0, 0, 0.66), 0.34, 0.03, STONE_WARM, sides=12)                      # ...its sand gone to stone
	p.seg((0, 0, 0.07), (0, 0, 0.62), 0.34, 0.03, STONE_WARM, sides=12)
	p.seg((0, 0, 0.64), (0, 0, 0.36), 0.025, 0.025, STONE_WARM, sides=5)                     # the last grain, stopped
	p.blob((0.07, 0.07, 0.07), (0, -0.02, 0.33), AMBER, segs=(6, 4), glow=2.4)
	for k in range(5):                                                                    # cracks, glowing faintly
		x0 = -0.3 + k * 0.15
		p.seg((x0, -0.32, 1.28), (x0 + 0.06, -0.32, 1.24 - (k % 2) * 0.04), 0.02, 0.01, AMBER, sides=4, glow=1.8)
	for x, z in ((-0.75, 0.9), (0.72, 0.45)):                                              # and time dragging to a halt
		_ring_at(p, x, z, 0.16, 0.025, MIST, sides=12, a0=0.3, a1=math.tau - 0.3, y=-0.2, glow=0.8)
		p.seg((x, -0.22, z), (x, -0.22, z + 0.11), 0.02, 0.02, MIST, sides=4, glow=0.8)
		p.seg((x, -0.22, z), (x + 0.08, -0.22, z), 0.02, 0.02, MIST, sides=4, glow=0.8)
	return p.build()


def skypiercer():
	p = Prop("skypiercer", 1243)
	for sgn in (-1, 1):                                                                   # a cloud, split...
		for dx, dz, s in ((0.3, 0.0, 0.46), (0.6, 0.08, 0.4), (0.85, -0.02, 0.3)):
			p.blob((s, s * 0.7, s * 0.8), (0.05 + sgn * dx, 0.15, 0.9 + dz), CLOTH_WHITE, segs=(10, 6), glow=0.5)
	_arrow(p, (-0.3, -0.1, -0.4), (0.2, -0.1, 1.5), hs=1.7, r=0.06, head=GOLD, glow=1.8, fletch=RUNE)   # ...by an arrow flying straight up
	tip = (0.2 + 0.1, -0.15, 1.5 + 0.4)
	for k in range(10):                                                                   # into the sun
		a = k * math.tau / 10
		r1 = 0.38 if k % 2 else 0.26
		p.seg(tip, (tip[0] + math.cos(a) * r1, -0.15, tip[2] + math.sin(a) * r1), 0.05, 0.0, GOLD if k % 2 else CLOTH_WHITE, sides=4, glow=2.6)
	for k in range(3):                                                                    # a white streak behind it
		x = -0.1 + (k - 1) * 0.2
		p.seg((x, -0.2, 0.3 - abs(k - 1) * 0.15), (x - 0.1, -0.2, -0.2 - abs(k - 1) * 0.15), 0.035, 0.0, CLOTH_WHITE, sides=4, glow=2.0)
	return p.build()


def heights_eye():
	p = Prop("heights_eye", 1245)
	for x, h, s in ((-0.65, 0.7, 0.5), (0.55, 0.85, 0.55)):                               # far peaks below...
		p.seg((x, 0.5, -0.1), (x, 0.5, h), s, 0.0, STONE_LIGHT, sides=5, grad=(0.1, 0.6))
		p.seg((x, 0.5, h * 0.62), (x, 0.5, h), s * 0.38, 0.0, CLOTH_WHITE, sides=5)
	_feather_fan(p, -0.05, 0.75, (215, 235, 255, 275, 295), 0.72, WOOD, tip=HIDE, r=0.13)
	hx, hz = -0.05, 0.95                                                                  # ...its white head, in profile
	p.blob((0.78, 0.55, 0.62), (hx, -0.1, hz), CLOTH_WHITE, segs=(12, 8))
	p.blob((0.4, 0.45, 0.4), (hx + 0.28, -0.1, hz - 0.05), CLOTH_WHITE, segs=(10, 6))
	beak = [(hx + 0.42, hz + 0.05), (hx + 0.66, hz + 0.02), (hx + 0.78, hz - 0.1), (hx + 0.74, hz - 0.26)]   # its hooked yellow beak
	for i, (u, v) in enumerate(zip(beak, beak[1:])):
		p.seg((u[0], -0.12, u[1]), (v[0], -0.12, v[1]), 0.13 - i * 0.04, 0.09 - i * 0.04 if i < 2 else 0.0, GOLD, sides=6)
	p.seg((hx + 0.42, -0.12, hz - 0.08), (hx + 0.62, -0.12, hz - 0.12), 0.07, 0.03, GOLD, sides=5)
	p.blob((0.2, 0.1, 0.18), (hx + 0.2, -0.38, hz + 0.08), GOLD, segs=(8, 5), glow=2.8)             # its keen eye
	p.blob((0.09, 0.06, 0.1), (hx + 0.23, -0.44, hz + 0.08), STONE_DARK, segs=(6, 4))
	p.seg((hx + 0.02, -0.36, hz + 0.2), (hx + 0.36, -0.36, hz + 0.15), 0.045, 0.025, STONE_DARK, sides=4)   # its fierce brow
	for k in range(5):                                                                    # seeing far
		a = math.radians(-10 + k * 12)
		p.seg((hx + 0.85, -0.4, hz + 0.25 + math.sin(a) * 0.1), (hx + 0.85 + math.cos(a) * 0.4, -0.4, hz + 0.25 + math.sin(a) * 0.45), 0.03, 0.0, GOLD, sides=4, glow=2.2)
	return p.build()


def tempest_of_arrows():
	p = Prop("tempest_of_arrows", 1247)
	cx, cz = 0.0, 0.72
	_ring(p, 1.0, -0.05, 0.045, CLOTH_RED, glow=1.8, sides=26)                               # on all it catches
	_swirl(p, cx, cz, 0.05, 0.36, 1.6, CLOTH_WHITE, 1.8, thick=0.07)                         # a tempest...
	for k in range(5):                                                                    # ...of arrows, whirling round it
		a = k * math.tau / 5 + 0.3
		r = 0.72
		out = Vector((math.cos(a), 0, math.sin(a)))
		t = Vector((-math.sin(a), 0, math.cos(a)))
		mid = Vector((cx, -0.1, cz)) + out * r
		_arrow(p, tuple(mid - t * 0.42 - out * 0.12), tuple(mid + t * 0.42 + out * 0.08), hs=1.0, r=0.035, fletch=RUNE, head=CLOTH_WHITE, glow=1.2)
		_crescent(p, cx, cz, 0.62, a - 0.8, a - 0.1, 0.035, RUNE, glow=1.8, y=0.05)
	return p.build()



def stone_song():
	p = Prop("stone_song", 1249)
	p.blob((1.4, 0.9, 0.14), (0, 0.1, -0.05), PINE, segs=(12, 4))                            # a standing stone...
	p.rock((0.5, 0.42, 1.25), (0, 0.05, 0.6), STONE_LIGHT, jitter=0.05)
	for k in range(3):                                                                    # ...its runes humming
		p.box((0.14, 0.05, 0.05), (0, -0.2, 0.35 + k * 0.28), RUNE, rot=(0, 20 - k * 20, 0), glow=2.6)
	for sx in (-1, 1):                                                                    # singing out rings of sound
		for k in range(3):
			_ring_at(p, 0, 0.7, 0.45 + k * 0.2, 0.035, RUNE if k % 2 else CLOTH_WHITE, glow=2.0, sides=8,
					 a0=(math.radians(-35) if sx > 0 else math.radians(145)), a1=(math.radians(35) if sx > 0 else math.radians(215)), y=-0.1)
	return p.build()


def wyvern_venom():
	p = Prop("wyvern_venom", 1251)
	pts = [(-0.9, 1.1), (-0.55, 1.2), (-0.2, 1.05), (0.1, 0.8), (0.25, 0.5)]                  # a wyvern's tail, curling down...
	for i, (u, v) in enumerate(zip(pts, pts[1:])):
		p.seg((u[0], 0, u[1]), (v[0], 0, v[1]), 0.16 - i * 0.02, 0.14 - i * 0.02, SEAFOAM, sides=8)
		p.seg((u[0], -0.12, u[1] + 0.12), (u[0] + 0.05, -0.12, u[1] + 0.25), 0.05, 0.0, WOOD, sides=4)   # its spines
	p.seg((0.25, 0, 0.5), (0.35, 0, 0.05), 0.14, 0.0, BONE, sides=6)                          # ...to a barbed stinger
	for k in range(2):
		z = 0.35 - k * 0.15
		for sgn in (-1, 1):
			p.seg((0.3 - k * 0.02, -0.02, z), (0.3 + sgn * 0.14, -0.02, z + 0.1), 0.035, 0.0, BONE, sides=4)
	for x, z, s in ((0.36, -0.15, 0.3), (0.3, -0.45, 0.24), (0.42, -0.7, 0.2)):              # dripping green venom
		_drop(p, x, z, s, SICKLY, 2.0)
	p.blob((0.12, 0.08, 0.1), (0.36, -0.08, 0.1), SICKLY, segs=(6, 4), glow=2.4)
	return p.build()


def bog_curse():
	p = Prop("bog_curse", 1253)
	p.blob((1.8, 1.2, 0.14), (0, 0.1, -0.05), SEAFOAM, segs=(14, 4), glow=0.3)               # bog water...
	for x, y in ((-0.6, -0.1), (0.55, 0.05), (0.2, -0.35)):
		p.seg((x, y, 0.0), (x + 0.05, y, 0.4), 0.03, 0.0, LEAF, sides=4)
	for x, z, s in ((-0.3, 0.05, 0.12), (0.3, 0.06, 0.1)):
		p.blob((s, s, s * 0.8), (x, -0.25, z), SICKLY, segs=(6, 4), glow=1.6)
	_hand(p, 0.0, 1.05, 0.9, SEAFOAM, curl=0.3, glow=0.2)                                     # ...under a hag's clawed hand...
	for k in range(4):
		fx = (-0.18, -0.06, 0.06, 0.18)[k]
		p.seg((fx * 1.1 * 0.9, -0.05, 1.05 + 0.6 * 0.9), (fx * 0.9, -0.1, 1.05 + 0.72 * 0.9), 0.03, 0.0, STONE_DARK, sides=4)
	_swirl(p, 0.0, 2.0, 0.05, 0.42, 1.8, SICKLY, 2.4, thick=0.08)                           # ...raising a green curse
	for k in range(3):
		x = -0.2 + k * 0.2
		p.seg((x, 0.0, 1.62), (x * 1.4, 0.0, 1.78), 0.03, 0.0, SICKLY, sides=4, glow=2.2)
	return p.build()


def tempest_bolt():
	p = Prop("tempest_bolt", 1255)
	_cloud(p, 0.0, 1.25, 0.55, swatch=STONE_DARK, glow=0.0, y=0.1)                          # a dark storm cloud...
	_cloud(p, 0.2, 1.1, 0.35, swatch=MIST, glow=0.0, y=-0.05)
	_bolt_line(p, [(0.0, 1.0), (-0.3, 0.6), (0.05, 0.52), (-0.2, 0.0)], 0.1, GOLD, 3.0, y=-0.25)   # ...loosing a bolt
	_bolt_line(p, [(-0.3, 0.6), (-0.55, 0.4)], 0.05, GOLD, 2.6, y=-0.25)
	for k in range(6):                                                                    # striking
		a = math.pi * (0.1 + k * 0.16)
		p.seg((-0.2, -0.3, 0.0), (-0.2 + math.cos(a) * 0.4, -0.3, math.sin(a) * 0.3), 0.04, 0.0, RUNE, sides=4, glow=2.4)
	for k, z in enumerate((0.55, 0.85)):                                                  # on a gale
		_wind(p, (0.25, z), (0.95, z + 0.05), r=0.04, up=1 if k else -1, y=-0.2)
	return p.build()

LEVEL_45 = [thunderclap_strike, bulwark_of_the_sky, tempest_whirl, zenith_ward, skyfire_judgment, breath_of_life, lightning_spear, cloudbind,
			heavenfall, cloudcutter, whirling_edges, hollow_heart, stormbound_mantle, thunderhead, wrath_of_the_sky, grave_wind, deathless_fury,
			breathtaker, hailbite_curse, spirit_of_the_summit, stillness_of_stone, skypiercer, heights_eye, tempest_of_arrows,
			stone_song, wyvern_venom, bog_curse, tempest_bolt]


# ---------------------------------------------------------------- level 50: night, the stars, the eclipse and the Unlit

NIGHT = WATER          # its deep end (grad near 1) is a night-sky navy
LILAC = (0.0, 0.3)     # PURPLE's pale end
SILVER = STONE_LIGHT


def _twinkle(p, x, z, s, swatch=CLOTH_WHITE, glow=2.6, y=-0.2):
	"""A four-pointed glint of starlight."""
	_star(p, x, z, s, swatch, glow=glow, y=y, points=4, inner=0.3, spin=90.0)


def _eclipse(p, cx, cz, r, y=0.1, corona=CLOTH_WHITE, glow=2.6, rays=12):
	"""A black sun: a dark disk ringed by a burning pale corona."""
	p.seg((cx, y - 0.06, cz), (cx, y + 0.06, cz), r, r, IRON, sides=24)
	_ring_at(p, cx, cz, r * 1.04, r * 0.08, corona, glow=glow, sides=24, y=y)
	_ring_at(p, cx, cz, r * 1.18, r * 0.05, PURPLE, glow=glow * 0.8, sides=24, y=y + 0.03)
	for k in range(rays):
		a = k * math.tau / rays + 0.1
		r1 = r * (1.75 if k % 2 else 1.45)
		p.seg((cx + math.cos(a) * r * 1.1, y + 0.05, cz + math.sin(a) * r * 1.1), (cx + math.cos(a) * r1, y + 0.05, cz + math.sin(a) * r1),
			  r * 0.12, 0.0, corona if k % 2 else PURPLE, sides=4, glow=glow)


def _silver_moon(p, cx, cz, r, glow=1.6, y=0.0, a0=110.0):
	"""A crescent moon in silver-white (the older _moon is gold)."""
	_crescent(p, cx, cz, r, math.radians(a0), math.radians(a0 + 150), 0.26 * r, CLOTH_WHITE, glow=glow, y=y, steps=20)


def eclipse_strike():
	p = Prop("eclipse_strike", 1301)
	_eclipse(p, 0.3, 1.0, 0.5, y=0.3)                                                      # the light blotted out...
	c = Vector((0.0, -0.2, 0.72))                                                         # ...by a great hammer's blow
	d = Vector((0.7, 0, 0.72)).normalized()
	perp = Vector((-d.z, 0, d.x))
	p.seg(tuple(c - d * 1.15), tuple(c), 0.065, 0.065, WOOD, sides=6)
	p.blob((0.12, 0.12, 0.12), tuple(c - d * 1.18), SILVER, segs=(6, 4))
	head = c - perp * 0.05
	p.seg(tuple(head - perp * 0.34), tuple(head + perp * 0.3), 0.23, 0.23, SILVER, sides=8)
	for sgn in (-1, 1):
		p.seg(tuple(head + perp * sgn * 0.32), tuple(head + perp * sgn * 0.38), 0.26, 0.26, STONE_DARK, sides=8)
	p.seg(tuple(head - Vector((0, 0.2, 0)) - perp * 0.3), tuple(head - Vector((0, 0.2, 0)) + perp * 0.26), 0.03, 0.03, PURPLE, sides=4, glow=2.4, grad=LILAC)
	for x, z in ((-0.62, 1.3), (-0.4, 1.55)):                                              # stunned, under dark stars
		_star(p, x, z, 0.1, CLOTH_WHITE, glow=2.4, y=-0.3)
	return p.build()


def wall_of_the_unlit():
	p = Prop("wall_of_the_unlit", 1303)
	for row in range(4):                                                                  # a wall of black stone...
		z = 0.12 + row * 0.33
		off = 0.2 if row % 2 else 0.0
		for k in range(5):
			x = -0.95 + off + k * 0.42
			if x > 0.95:
				continue
			p.box((0.38, 0.3, 0.29), (x, 0.35, z), STONE_DARK, jitter=0.02)
		p.seg((-1.0, 0.18, z + 0.165), (1.0, 0.18, z + 0.165), 0.02, 0.02, PURPLE, sides=4, glow=2.2, grad=LILAC)   # mortared with violet light
	outline = [(-0.5, 1.2), (0.5, 1.2), (0.54, 0.55), (0.0, -0.1), (-0.54, 0.55)]            # ...behind a dark shield
	icons._slab(p, outline, -0.05, 0.12, PURPLE, grad=(0.6, 1.0))
	edge = outline + outline[:1]
	for u, v in zip(edge, edge[1:]):
		p.seg((u[0], -0.07, u[1]), (v[0], -0.07, v[1]), 0.055, 0.055, SILVER, sides=5, glow=0.8)
	_silver_moon(p, 0.02, 0.62, 0.3, glow=2.2, y=-0.12, a0=100)                               # the Unlit's crescent on it
	for x, z, s in ((0.14, 0.88, 0.07), (0.25, 0.5, 0.05), (-0.05, 0.28, 0.05)):
		_twinkle(p, x, z, s, glow=2.6, y=-0.14)
	return p.build()


def worldbreaker():
	p = Prop("worldbreaker", 1305)
	_ring(p, 1.02, -0.05, 0.045, CLOTH_RED, glow=1.8, sides=26)                               # every foe near it...
	cx, cz = 0.0, 0.8
	p.blob((1.3, 1.3, 1.3), (cx, 0.1, cz), WATER, segs=(16, 12), grad=(0.0, 0.55))              # ...and the world itself
	for x, z, w, h in ((-0.3, 0.25, 0.42, 0.3), (0.25, 0.05, 0.36, 0.42), (-0.15, -0.3, 0.3, 0.2), (0.35, 0.4, 0.2, 0.16)):
		yy = -math.sqrt(max(0.0, 0.42 - x * x - z * z)) + 0.1
		p.blob((w, 0.14, h), (cx + x, yy, cz + z), LEAF, segs=(8, 5))
	crack = [(0.12, 1.5), (-0.08, 1.2), (0.1, 0.95), (-0.12, 0.7), (0.06, 0.45), (-0.06, 0.1)]   # broken by a blazing crack
	_bolt_line(p, crack, 0.16, PURPLE, 2.4, y=-0.62)
	_bolt_line(p, crack, 0.07, CLOTH_WHITE, 3.2, y=-0.72)
	_bolt_line(p, [(0.1, 0.95), (0.42, 1.05), (0.55, 0.92)], 0.05, CLOTH_WHITE, 3.0, y=-0.62)
	_bolt_line(p, [(-0.12, 0.7), (-0.45, 0.6), (-0.58, 0.72)], 0.05, CLOTH_WHITE, 3.0, y=-0.62)
	for k in range(10):                                                                   # its light bursting out
		a = k * math.tau / 10 + 0.25
		p.seg((cx + math.cos(a) * 0.75, -0.3, cz + math.sin(a) * 0.75), (cx + math.cos(a) * 1.02, -0.3, cz + math.sin(a) * 1.02),
			  0.05, 0.0, CLOTH_WHITE if k % 2 else PURPLE, sides=4, glow=2.6)
	for x, z, sz in ((-0.9, 1.35, 0.14), (0.95, 0.35, 0.12), (0.82, 1.45, 0.1)):          # chunks of it flung off
		p.rock((sz, sz, sz), (x, -0.1, z), STONE_WARM, jitter=0.2)
	return p.build()


def starlight_ward():
	p = Prop("starlight_ward", 1307)
	_ring(p, 0.9, 0.0, 0.045, GOLD, glow=1.8, sides=24)                                    # over the group...
	for k in range(7):                                                                    # ...a dome of starlight
		a = math.radians(15 + k * 25)
		p.seg((math.cos(a) * 0.9, 0.2, 0.0), (math.cos(a) * 0.25, 0.2, 1.05), 0.018, 0.018, RUNE, sides=4, glow=1.6)
	_ring_at(p, 0, 0.0, 0.9, 0.03, CLOTH_WHITE, glow=1.8, sides=16, a0=0.0, a1=math.pi, y=0.15)
	cz = 0.72                                                                             # a great silver star keeps it
	_star(p, 0, cz, 0.4, CLOTH_WHITE, glow=2.8, y=-0.2, points=8, inner=0.32, spin=90)
	_star(p, 0, cz, 0.27, RUNE, glow=2.4, y=-0.1, points=8, inner=0.4, spin=112.5)
	p.box((0.08, 0.06, 0.26), (0, -0.35, cz), LEAF, glow=2.4)                               # its mending cross
	p.box((0.24, 0.06, 0.08), (0, -0.35, cz + 0.03), LEAF, glow=2.4)
	for x, z, s in ((-0.62, 0.45, 0.07), (0.6, 0.55, 0.08), (-0.35, 1.05, 0.06), (0.4, 1.12, 0.06)):
		_twinkle(p, x, z, s, glow=2.6, y=-0.25)
	return p.build()


def dawn_in_darkness():
	p = Prop("dawn_in_darkness", 1309)
	cx, cz = 0.0, 0.7
	p.seg((cx, 0.15, cz), (cx, 0.3, cz), 0.95, 0.95, NIGHT, sides=28, grad=(0.85, 1.0))       # the dark around the foe...
	_ring_at(p, cx, cz, 0.95, 0.04, PURPLE, glow=1.6, sides=28, y=0.1)
	for x, z in ((-0.6, 1.2), (0.55, 1.28), (-0.72, 0.4), (0.72, 0.3)):
		_twinkle(p, x, z, 0.05, glow=2.2, y=0.05)
	p.seg((cx, 0.0, cz), (cx, -0.05, cz), 0.3, 0.3, GOLD, sides=20, glow=3.0)                 # ...a dawn breaking in it
	p.blob((0.22, 0.1, 0.22), (cx, -0.12, cz), CLOTH_WHITE, segs=(10, 6), glow=3.2)
	for k in range(16):
		a = k * math.tau / 16
		r1 = 0.9 if k % 2 == 0 else 0.58
		p.seg((cx + math.cos(a) * 0.32, -0.08, cz + math.sin(a) * 0.32), (cx + math.cos(a) * r1, -0.08, cz + math.sin(a) * r1),
			  0.06 if k % 2 == 0 else 0.04, 0.0, GOLD if k % 2 == 0 else FLAME, sides=4, glow=2.8)
	return p.build()


def covenant_of_light():
	p = Prop("covenant_of_light", 1311)
	_ring(p, 0.92, 0.0, 0.045, GOLD, glow=1.8, sides=24)                                   # for the whole group...
	for sx in (-1, 1):                                                                    # ...two hands clasped in a covenant
		p.seg((sx * 1.05, 0.0, 0.1), (sx * 0.34, -0.05, 0.55), 0.2, 0.17, CLOTH_WHITE, sides=8)
		p.seg((sx * 1.02, 0.0, 0.08), (sx * 0.8, 0.0, 0.22), 0.24, 0.24, GOLD, sides=8)
	p.blob((0.62, 0.46, 0.42), (-0.2, -0.08, 0.6), HIDE, segs=(10, 6))
	p.blob((0.62, 0.46, 0.42), (0.2, -0.18, 0.56), HIDE, segs=(10, 6))
	for k in range(4):                                                                    # fingers wrapped over
		p.seg((0.08 + k * 0.03, -0.38, 0.76 - k * 0.1), (-0.36, -0.36, 0.72 - k * 0.1), 0.065, 0.055, HIDE, sides=5)
	p.seg((-0.18, -0.42, 0.8), (0.16, -0.44, 0.88), 0.07, 0.055, HIDE, sides=5)
	cz = 1.3                                                                              # under the light they swore by
	p.blob((0.42, 0.16, 0.42), (0, -0.05, cz), CLOTH_WHITE, segs=(10, 6), glow=3.2)
	for k in range(12):
		a = k * math.tau / 12 + math.pi / 2
		r1 = 0.7 if k % 3 == 0 else 0.46
		p.seg((math.cos(a) * 0.2, 0.0, cz + math.sin(a) * 0.2), (math.cos(a) * r1, 0.0, cz + math.sin(a) * r1), 0.05, 0.0, GOLD, sides=4, glow=2.6)
	for sx in (-1, 1):                                                                    # its healing falling on them
		p.box((0.08, 0.05, 0.24), (sx * 0.62, -0.3, 0.95), LEAF, glow=2.4)
		p.box((0.22, 0.05, 0.08), (sx * 0.62, -0.3, 0.98), LEAF, glow=2.4)
	return p.build()


def starfire_lance():
	p = Prop("starfire_lance", 1313)
	a, b = Vector((-0.85, -0.05, -0.05)), Vector((0.35, -0.05, 1.0))                        # a lance of starfire...
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(tuple(a), tuple(b), 0.02, 0.12, PURPLE, sides=8, glow=2.0, grad=LILAC)
	p.seg(tuple(a - Vector((0, 0.08, 0))), tuple(b - Vector((0, 0.08, 0))), 0.01, 0.06, CLOTH_WHITE, sides=6, glow=3.0)
	tip = b + d * 0.32
	_star(p, tip.x, tip.z, 0.26, CLOTH_WHITE, glow=3.0, y=-0.15, points=6, inner=0.35)          # ...headed with a star
	_ring_at(p, tip.x, tip.z, 0.42, 0.025, RUNE, glow=2.2, sides=16, y=-0.05)
	for k, t in enumerate((0.2, 0.42, 0.62, 0.82)):                                      # shedding sparks of the night sky
		q = a + (b - a) * t + n * (0.22 if k % 2 else -0.22)
		_twinkle(p, q.x, q.z, 0.06 + 0.02 * t, swatch=CLOTH_WHITE if k % 2 else RUNE, glow=2.6, y=-0.2)
	return p.build()


def shadowbind():
	p = Prop("shadowbind", 1315)
	p.blob((1.2, 0.8, 0.05), (0.0, 0.0, 0.0), IRON, segs=(14, 5))                             # the foe's own shadow...
	_ring(p, 0.8, 0.02, 0.045, PURPLE, glow=2.2, sides=22)
	p.seg((0, 0.15, 0.05), (0, 0.15, 0.95), 0.22, 0.16, STONE_LIGHT, sides=8)                 # ...rising round the foe
	p.blob((0.34, 0.34, 0.36), (0, 0.15, 1.15), STONE_LIGHT, segs=(8, 6))
	for sx in (-1, 1):
		p.blob((0.08, 0.05, 0.06), (sx * 0.07, -0.02, 1.17), CLOTH_RED, segs=(5, 3), glow=2.6)
	for k in range(5):                                                                    # in grasping dark hands of it
		a = k * math.tau / 5 + 0.3
		base = Vector((math.cos(a) * 0.55, math.sin(a) * 0.4, 0.02))
		pts = []
		for j in range(9):
			t = j / 8
			ang = a + t * 2.2
			rr = 0.55 - 0.32 * t
			pts.append((math.cos(ang) * rr, math.sin(ang) * rr * 0.75, 0.02 + t * (0.55 + 0.1 * (k % 2))))
		for j, (u, v) in enumerate(zip(pts, pts[1:])):
			w = 0.1 * (1 - 0.7 * j / 8)
			p.seg(u, v, w, w, PURPLE, sides=5, grad=(0.3, 0.8), glow=1.2)
		p.blob((0.05, 0.05, 0.05), pts[-1], PURPLE, segs=(5, 3), glow=2.2, grad=LILAC)
	return p.build()


def black_sun():
	p = Prop("black_sun", 1317)
	_ring(p, 1.0, -0.05, 0.045, CLOTH_RED, glow=1.8, sides=26)                               # on the target and all near it...
	for x, s in ((-0.5, 0.45), (0.0, 0.6), (0.5, 0.45)):                                  # ...violet fire, raining down
		_fl(p, x, -0.1, 0.0, s, glow=2.0, core=PURPLE, tongue=PURPLE)
	cz = 1.2                                                                              # from a black sun burning above
	for k in range(14):
		a = k * math.tau / 14
		r1 = 0.72 if k % 2 else 0.55
		p.seg((math.cos(a) * 0.4, 0.15, cz + math.sin(a) * 0.4), (math.cos(a) * r1 * 1.25, 0.15, cz + math.sin(a) * r1 * 1.25), 0.1, 0.0, PURPLE, sides=5, glow=2.4, grad=LILAC)
	p.blob((0.8, 0.8, 0.8), (0, 0.0, cz), IRON, segs=(14, 10))
	_ring_at(p, 0, cz, 0.42, 0.045, PURPLE, glow=2.8, sides=24, y=-0.05)
	for x in (-0.35, 0.0, 0.35):
		p.seg((x * 0.5, 0.05, cz - 0.4), (x * 1.3, 0.05, 0.55), 0.04, 0.02, PURPLE, sides=4, glow=2.2, grad=LILAC)
	return p.build()


def nightblade():
	p = Prop("nightblade", 1319)
	_silver_moon(p, -0.15, 0.85, 0.72, glow=1.8, y=0.35, a0=95)                              # out of the night...
	for x, z, s in ((0.45, 1.35, 0.07), (0.7, 0.95, 0.05), (0.2, 1.55, 0.05)):
		_twinkle(p, x, z, s, glow=2.4, y=0.3)
	base, tip = Vector((0.55, -0.1, 1.25)), Vector((-0.35, -0.1, 0.05))                     # ...a dark blade, striking unseen
	d = (tip - base).normalized()
	nn = Vector((-d.z, 0, d.x))
	p.seg(tuple(base), tuple(tip), 0.2, 0.0, PURPLE, sides=4, grad=(0.45, 0.9))
	p.seg(tuple(base + d * 0.05 - Vector((0, 0.08, 0)) + nn * 0.06), tuple(tip - Vector((0, 0.08, 0))), 0.025, 0.0, CLOTH_WHITE, sides=4, glow=2.6)
	p.seg(tuple(base - nn * 0.26), tuple(base + nn * 0.26), 0.045, 0.045, SILVER, sides=5)
	p.seg(tuple(base), tuple(base - d * 0.3), 0.05, 0.05, IRON, sides=6)
	p.blob((0.08, 0.08, 0.08), tuple(base - d * 0.34), PURPLE, segs=(6, 4), glow=2.4, grad=LILAC)
	for k in range(3):                                                                    # the cut
		off = nn * (k - 1) * 0.13
		p.seg(tuple(tip + d * 0.1 + off - Vector((0, 0.2, 0))), tuple(tip + d * 0.35 + off - Vector((0, 0.2, 0))), 0.035, 0.0, CRIMSON, sides=4, glow=2.0)
	return p.build()


def nightfall_edges():
	p = Prop("nightfall_edges", 1321)
	cx, cz = 0.0, 0.62
	for sgn in (-1, 1):                                                                   # two blades, crossed...
		base = Vector((cx - sgn * 0.45, -0.1 - (0.05 if sgn > 0 else 0.0), cz - 0.45))
		tip = Vector((cx + sgn * 0.55, -0.1 - (0.05 if sgn > 0 else 0.0), cz + 0.62))
		_dagger(p, tuple(base), tuple(tip), w=0.11, blade=SILVER, edge=CLOTH_WHITE)
	for sgn in (-1, 1):                                                                   # ...trailing nightfall behind them
		a0 = math.radians(90 + sgn * 30)
		a1 = math.radians(90 + sgn * 150)
		_crescent(p, cx, cz, 0.95, a0, a1, 0.14, PURPLE, glow=1.2, y=0.2)
		for k in range(4):
			a = a0 + (a1 - a0) * (0.2 + k * 0.2)
			_twinkle(p, cx + math.cos(a) * 0.95, cz + math.sin(a) * 0.95, 0.055, glow=2.8, y=0.05)
	for x in (0.82, 0.98):                                                                # faster
		p.seg((x, -0.3, 0.0), (x, -0.3, 0.35), 0.03, 0.03, GOLD, sides=4, glow=2.2)
		p.seg((x, -0.3, 0.42), (x, -0.3, 0.3), 0.08, 0.0, GOLD, sides=4, glow=2.2)
	return p.build()


def umbral_wound():
	p = Prop("umbral_wound", 1323)
	cx, cz, ang = 0.0, 0.85, math.radians(28)
	ca, sa = math.cos(ang), math.sin(ang)
	rot = lambda x, z: (cx + x * ca - z * sa, cz + x * sa + z * ca)
	upper = [rot(-1.0 + 2.0 * k / 16, 0.3 * math.sin(math.pi * k / 16)) for k in range(17)]
	lower = [rot(1.0 - 2.0 * k / 16, -0.3 * math.sin(math.pi * k / 16)) for k in range(1, 16)]
	outline = upper + lower                                                               # a deep gash, cut through...
	icons._slab(p, outline[::-1], 0.0, 0.1, IRON, grad=(0.3, 1.0))
	for u, v in zip(outline, outline[1:] + outline[:1]):
		p.seg((u[0], -0.03, u[1]), (v[0], -0.03, v[1]), 0.07, 0.07, PURPLE, sides=5, glow=1.8, grad=LILAC)
	for t, off, sz in ((-0.55, 0.05, 0.05), (-0.15, -0.08, 0.08), (0.25, 0.08, 0.055), (0.6, -0.03, 0.045)):   # ...into the starry dark
		x, z = rot(t, off)
		_twinkle(p, x, z, sz, glow=2.8, y=-0.06)
	for x, z, sz in ((-0.4, 0.2, 0.55), (0.05, -0.15, 0.65), (0.45, 0.3, 0.45), (0.12, -0.72, 0.42)):   # bleeding darkness, heavily
		_drop(p, x, z, sz, PURPLE, 2.0)
	return p.build()


def starforged_mantle():
	p = Prop("starforged_mantle", 1325)
	for k in range(7):                                                                    # a mantle of the night sky...
		a = math.radians(-15 + k * 35)
		p.blob((0.34, 0.28, 0.3), (math.cos(a) * 0.45, 0.12, 0.62 + math.sin(a) * 0.3), PURPLE, segs=(8, 5), grad=(0.55, 0.95))
	_elemental(p, SILVER, s=1.0, glow=0.3)                                                # ...on the pet
	for sx in (-1, 1):
		p.blob((0.1, 0.06, 0.07), (sx * 0.07, -0.16, 0.98), RUNE, segs=(5, 3), glow=2.8)
	_star(p, 0.0, 0.52, 0.13, CLOTH_WHITE, glow=3.0, y=-0.25)                                  # forged with a star
	for x, z, s in ((-0.55, 1.05, 0.06), (0.52, 1.0, 0.07), (-0.72, 0.45, 0.05), (0.66, 0.4, 0.05)):
		_twinkle(p, x, z, s, glow=2.6, y=-0.1)
	for k, x in enumerate((-0.62, 0.62)):                                                 # made stronger
		for z in (1.2, 1.38):
			p.seg((x - 0.1, -0.3, z - 0.08), (x, -0.3, z), 0.035, 0.035, GOLD, sides=4, glow=2.2)
			p.seg((x + 0.1, -0.3, z - 0.08), (x, -0.3, z), 0.035, 0.035, GOLD, sides=4, glow=2.2)
	return p.build()


def starcall():
	p = Prop("starcall", 1327)
	_conjure_ring(p, -0.5, 1.25, 0.32, PURPLE, runes=(CLOTH_WHITE, RUNE, CLOTH_WHITE, RUNE))   # a ring opened on the night sky...
	for x, z in ((-0.62, 1.32), (-0.42, 1.18)):
		_twinkle(p, x, z, 0.04, glow=2.6, y=0.0)
	a, b = Vector((-0.4, -0.1, 1.1)), Vector((0.3, -0.15, 0.3))                             # ...and a star called down out of it
	p.seg(tuple(a), tuple(b), 0.02, 0.2, RUNE, sides=8, glow=1.8)
	p.seg(tuple(a - Vector((0, 0.05, 0))), tuple(b - Vector((0, 0.05, 0))), 0.01, 0.11, CLOTH_WHITE, sides=6, glow=2.8)
	_star(p, b.x, b.z + 0.1, 0.4, CLOTH_WHITE, glow=3.0, y=-0.3, spin=70)
	p.blob((1.6, 1.0, 0.1), (0.3, 0.2, -0.05), STONE_DARK, segs=(12, 4))                       # onto the foe
	for k in range(7):
		ang = math.pi * (0.05 + k * 0.15)
		p.seg((0.3, -0.3, 0.0), (0.3 + math.cos(ang) * 0.6, -0.3, math.sin(ang) * 0.3), 0.045, 0.0, RUNE if k % 2 else CLOTH_WHITE, sides=4, glow=2.4)
	return p.build()


def cataclysm():
	p = Prop("cataclysm", 1329)
	_ring(p, 1.02, -0.05, 0.045, CLOTH_RED, glow=1.8, sides=26)                               # on all near the target...
	for k in range(6):                                                                    # ...the ground heaving up in plates
		a = k * math.tau / 6 + 0.3
		x, y = math.cos(a) * 0.62, math.sin(a) * 0.45
		p.box((0.6, 0.48, 0.12), (x, y, 0.1), STONE_DARK, rot=(math.sin(a) * 25, -math.cos(a) * 25, math.degrees(a)), jitter=0.05)
	p.seg((0, 0, 0.0), (0, 0, 1.15), 0.42, 0.18, EMBER, sides=10, glow=2.4)                    # every element breaking loose:
	p.seg((0, -0.12, 0.1), (0, -0.12, 1.35), 0.22, 0.02, FLAME, sides=8, glow=2.8)            # fire,
	_drop(p, -0.72, 1.1, 0.28, WATER, 1.6)                                                   # water,
	_drop(p, -0.5, 1.45, 0.18, WATER, 1.6)
	for x, z, s in ((0.62, 1.2, 0.16), (0.8, 0.85, 0.12), (0.45, 1.5, 0.1)):               # earth,
		p.rock((s, s, s), (x, -0.1, z), STONE_WARM, jitter=0.2)
	_wind(p, (-0.95, 0.55), (-0.35, 0.72), swatch=CLOTH_WHITE, r=0.06, curl=0.14, glow=2.0, y=-0.3)   # and air
	_wind(p, (0.95, 0.5), (0.4, 0.62), swatch=CLOTH_WHITE, r=0.06, curl=0.14, up=-1, glow=2.0, y=-0.3)
	_star(p, 0.0, 1.5, 0.16, CLOTH_WHITE, glow=3.0, y=-0.2, points=8, inner=0.3)
	return p.build()


def unlit_rot():
	p = Prop("unlit_rot", 1331)
	cx, cz, r = 0.0, 1.1, 0.4                                                             # a dead black moon...
	p.blob((r * 2, r * 1.2, r * 2), (cx, 0.1, cz), IRON, segs=(14, 10))
	_ring_at(p, cx, cz, r * 1.02, 0.035, SICKLY, glow=2.0, sides=24, y=0.05)
	for x, z, s in ((-0.15, 1.2, 0.2), (0.18, 0.98, 0.16), (0.08, 1.35, 0.12)):
		p.blob((s, 0.04, s), (cx + x, -0.32, z), MIST, segs=(8, 5), grad=(0.6, 1.0))
	for x, z, s in ((-0.25, 0.48, 0.2), (0.08, 0.36, 0.24), (0.3, 0.52, 0.17)):              # ...dripping its rot
		_drop(p, x, z, s, SICKLY, 1.6)
		p.seg((x, -0.2, cz - r * 0.75), (x, -0.2, z + s * 0.4), 0.05, 0.03, SICKLY, sides=4, glow=1.6)
	p.blob((1.7, 1.0, 0.12), (0, 0.1, -0.02), PINE, segs=(12, 4), grad=(0.6, 1.0))             # onto blighted ground
	for x, s in ((-0.5, 0.1), (0.4, 0.12), (-0.1, 0.08), (0.65, 0.07)):
		p.blob((s, s, s * 0.8), (x, -0.2, 0.08), SICKLY, segs=(6, 4), glow=1.8)
	_bone(p, (-0.75, -0.25, 0.1), (-0.3, -0.25, 0.14), 0.04)
	return p.build()


def grave_ascendance():
	p = Prop("grave_ascendance", 1333)
	p.blob((1.5, 0.9, 0.12), (0, 0.2, -0.02), PINE, segs=(12, 4))                              # out of an open grave...
	p.box((0.9, 0.5, 0.06), (0, 0.0, 0.06), IRON)
	for sx in (-1, 1):                                                                    # ...rising on dark wings
		_feather_fan(p, sx * 0.25, 0.85, [90 - sx * 90 + sx * dd for dd in (-40, -18, 4, 26, 48)], 0.72, PURPLE, tip=CLOTH_WHITE, glow=1.0, r=0.1)
	for k in range(3):                                                                    # its bones
		_bone(p, (0, -0.05, 0.25 + k * 0.05), (0, -0.05, 0.65), 0.05)
		p.seg((-0.22 + 0.0, -0.08, 0.4 + k * 0.1), (0.22, -0.08, 0.4 + k * 0.1), 0.03, 0.03, BONE, sides=5)
	_skull(p, 0.0, 0.95, 0.72, eyes=PURPLE, eye_glow=3.2)                                   # the undead, crowned
	for k in range(5):
		x = -0.2 + k * 0.1
		p.seg((x, -0.05, 1.18), (x * 1.1, -0.05, 1.18 + (0.18 if k % 2 == 0 else 0.1)), 0.035, 0.0, SILVER, sides=4, glow=1.2)
	p.seg((-0.23, -0.05, 1.17), (0.23, -0.05, 1.17), 0.03, 0.03, SILVER, sides=5, glow=1.2)
	for x in (0.8, 0.95):                                                                 # made faster
		p.seg((x, -0.3, 0.25), (x, -0.3, 0.6), 0.03, 0.03, GOLD, sides=4, glow=2.2)
		p.seg((x, -0.3, 0.67), (x, -0.3, 0.55), 0.08, 0.0, GOLD, sides=4, glow=2.2)
	return p.build()


def soul_reaver():
	p = Prop("soul_reaver", 1335)
	a, b = Vector((0.85, 0.05, -0.15)), Vector((0.25, 0.05, 1.5))                             # a reaper's scythe...
	p.seg(tuple(a), tuple(b), 0.06, 0.06, IRON, sides=6)
	p.blob((0.12, 0.12, 0.12), tuple(a), SILVER, segs=(6, 4))
	pts = []
	for k in range(17):                                                                   # ...its long curved blade, sweeping left
		t = k / 16
		pts.append((b.x - t * 1.15, 0.0, b.z + 0.05 - math.sin(t * math.pi * 0.85) * 0.05 - t * t * 0.45))
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w0 = 0.16 * (1 - k / 16) + 0.01
		w1 = 0.16 * (1 - (k + 1) / 16) + 0.01
		p.seg((u[0], 0.0, u[2] - w0 * 0.4), (v[0], 0.0, v[2] - w1 * 0.4), w0, w1, SILVER, sides=4)
		p.seg((u[0], -0.12, u[2] - w0 * 1.1), (v[0], -0.12, v[2] - w1 * 1.1), 0.03, 0.02, PURPLE, sides=4, glow=2.8, grad=LILAC)
	p.box((0.16, 0.16, 0.2), tuple(b - Vector((0, 0.02, 0.05))), IRON)
	sx, sz = -0.35, 0.55                                                                  # reaping a soul...
	p.blob((0.6, 0.42, 0.62), (sx, -0.1, sz), CLOTH_WHITE, segs=(12, 8), glow=1.6)
	p.seg((sx, -0.1, sz - 0.2), (sx - 0.2, -0.1, sz - 0.8), 0.24, 0.0, CLOTH_WHITE, sides=8, glow=1.6)
	for ex in (-1, 1):
		p.blob((0.11, 0.06, 0.15), (sx + ex * 0.12, -0.32, sz + 0.07), STONE_DARK, segs=(6, 4))
	p.blob((0.1, 0.06, 0.15), (sx, -0.32, sz - 0.13), STONE_DARK, segs=(6, 4))
	_stream(p, -0.1, 0.55, 0.1, 0.08, 0.04, CLOTH_RED, 2.0, n=10)                             # ...its life for yours
	_heart(p, 0.68, 0.22, 0.2, swatch=CLOTH_RED, y=-0.25, depth=0.1, rim=FLAME, glow=2.0)
	return p.build()


def frostfang_curse():
	p = Prop("frostfang_curse", 1337)
	_swirl(p, 0.0, 0.4, 0.05, 0.5, 1.6, PURPLE, 2.0, thick=0.09)                            # a curse on the foe...
	for k in range(9):                                                                    # ...a frost wolf's upper jaw
		t = k / 8
		x = -0.8 + t * 1.6
		z = 1.45 - math.sin(t * math.pi) * 0.2
		p.blob((0.3, 0.26, 0.26), (x, 0.0, z), CLOTH_WHITE, segs=(8, 5), glow=0.6)
	for sx in (-1, 1):                                                                    # its two great fangs of ice, biting down
		pts = []
		for k in range(10):
			t = k / 9
			pts.append((sx * (0.55 - 0.3 * t ** 1.4), -0.15, 1.32 - t * 0.95))
		for k, (u, v) in enumerate(zip(pts, pts[1:])):
			w0, w1 = 0.19 * (1 - k / 9) + 0.01, 0.19 * (1 - (k + 1) / 9) + 0.005
			p.seg(u, v, w0, w1, WATER, sides=6, glow=1.0, grad=(0.0, 0.4))
			p.seg((u[0] - sx * 0.05, -0.32, u[2]), (v[0] - sx * 0.05, -0.32, v[2]), w0 * 0.3, w1 * 0.3, CLOTH_WHITE, sides=4, glow=2.4)
	for x in (-0.2, 0.0, 0.2):                                                            # and the small ones between
		p.seg((x, -0.12, 1.3), (x, -0.12, 1.05), 0.06, 0.0, WATER, sides=5, glow=1.2, grad=(0.0, 0.4))
	_drop(p, 0.25, 0.18, 0.12, WATER, 1.6)
	_snowflake(p, 0.85, 0.75, 0.15, 2.2)
	_snowflake(p, -0.85, 0.6, 0.12, 2.2)
	return p.build()


def spirit_of_the_ancients():
	p = Prop("spirit_of_the_ancients", 1339)
	_ring(p, 0.92, 0.0, 0.045, GOLD, glow=1.8, sides=24)                                   # over the group...
	hx, hz = 0.0, 0.98                                                                    # ...the face of an ancient spirit
	for k in range(5):                                                                    # a crown of old feathers
		a = math.radians(50 + k * 20)
		p.seg((hx + math.cos(a) * 0.2, 0.15, hz + 0.2), (hx + math.cos(a) * 0.62, 0.15, hz + 0.2 + math.sin(a) * 0.55), 0.08, 0.02, GOLD if k % 2 else CLOTH_RED, sides=5, glow=0.6)
	p.blob((0.74, 0.58, 0.8), (hx, 0.0, hz), RUNE, segs=(12, 8), glow=0.8, grad=(0.0, 0.3))
	p.seg((hx, -0.12, hz - 0.28), (hx, -0.22, hz - 1.0), 0.42, 0.0, CLOTH_WHITE, sides=8, glow=0.9)   # his long beard
	for sx in (-1, 1):
		p.seg((hx + sx * 0.27, -0.05, hz - 0.15), (hx + sx * 0.2, -0.14, hz - 0.72), 0.12, 0.0, CLOTH_WHITE, sides=6, glow=0.9)
		p.blob((0.12, 0.05, 0.08), (hx + sx * 0.14, -0.3, hz + 0.06), CLOTH_WHITE, segs=(6, 4), glow=3.2)   # glowing eyes
		p.seg((hx + sx * 0.03, -0.3, hz + 0.18), (hx + sx * 0.32, -0.26, hz + 0.22), 0.06, 0.02, CLOTH_WHITE, sides=4, glow=0.6)   # heavy brows
	p.seg((hx, -0.34, hz + 0.02), (hx, -0.4, hz - 0.14), 0.06, 0.045, RUNE, sides=5, grad=(0.0, 0.3))   # nose
	for x, z in ((-0.72, 1.45), (0.75, 1.4), (-0.85, 0.75), (0.82, 0.7)):                 # from the old night sky
		_twinkle(p, x, z, 0.06, glow=2.6, y=-0.2)
	return p.build()


def timeless_stillness():
	p = Prop("timeless_stillness", 1341)
	cx, cz = 0.0, 0.7
	p.seg((cx, 0.1, cz), (cx, 0.22, cz), 0.72, 0.72, NIGHT, sides=28, grad=(0.85, 1.0))       # a clock face of the night sky...
	_ring_at(p, cx, cz, 0.74, 0.07, SILVER, sides=28, y=0.05)
	for k in range(12):                                                                   # stars for its hours
		a = k * math.tau / 12
		_twinkle(p, cx + math.cos(a) * 0.58, cz + math.sin(a) * 0.58, 0.05 if k % 3 else 0.08, glow=2.4, y=0.02)
	p.seg((cx, -0.02, cz), (cx, -0.02, cz + 0.48), 0.045, 0.01, SILVER, sides=4, glow=0.6)      # ...its hands stopped
	p.seg((cx, -0.04, cz), (cx + 0.3, -0.04, cz - 0.18), 0.055, 0.01, SILVER, sides=4, glow=0.6)
	p.blob((0.07, 0.05, 0.07), (cx, -0.06, cz), GOLD, segs=(6, 4), glow=1.6)
	for k in range(3):                                                                    # by a ring of still frost
		_ring_at(p, cx, cz, 0.86 + k * 0.1, 0.022, MIST if k % 2 else WATER, glow=1.4, sides=24, a0=math.radians(200 + k * 20), a1=math.radians(340 + k * 20), y=-0.1)
	for x, z in ((-0.8, 1.3), (0.8, 0.15)):
		_snowflake(p, x, z, 0.11, 1.8)
	return p.build()


def starpiercer():
	p = Prop("starpiercer", 1343)
	cx, cz = 0.25, 0.95
	_star(p, cx, cz, 0.36, CLOTH_WHITE, glow=2.6, y=0.1, spin=90)                             # a star...
	_ring_at(p, cx, cz, 0.62, 0.025, RUNE, glow=2.0, sides=18, y=0.15)
	_arrow(p, (-0.9, -0.1, 0.05), (0.8, -0.1, 1.6), hs=1.4, r=0.05, head=CLOTH_WHITE, glow=2.4, fletch=PURPLE)   # ...pierced through
	for k in range(6):                                                                    # shards of its light
		a = math.radians(-30 + k * 60)
		p.seg((cx + math.cos(a) * 0.5, -0.2, cz + math.sin(a) * 0.5), (cx + math.cos(a) * 0.75, -0.2, cz + math.sin(a) * 0.75), 0.04, 0.0, GOLD, sides=4, glow=2.4)
	for x, z in ((-0.55, 0.6), (-0.25, 0.25)):
		_twinkle(p, x, z, 0.05, glow=2.4, y=-0.25)
	return p.build()


def nighthunters_eye():
	p = Prop("nighthunters_eye", 1345)
	_silver_moon(p, 0.6, 1.35, 0.32, glow=2.0, y=0.45, a0=100)                                 # by moonlight...
	hx, hz = 0.0, 0.78                                                                    # ...an owl's face
	p.blob((0.95, 0.5, 0.82), (hx, 0.1, hz), WOOD_GRAY, segs=(14, 10))
	for sx in (-1, 1):
		p.seg((hx + sx * 0.3, 0.05, hz + 0.3), (hx + sx * 0.5, 0.05, hz + 0.72), 0.14, 0.0, WOOD_GRAY, sides=5)   # ear tufts
		p.blob((0.46, 0.1, 0.46), (hx + sx * 0.25, -0.28, hz + 0.02), HIDE, segs=(12, 6))                   # facial discs
		p.blob((0.3, 0.08, 0.3), (hx + sx * 0.25, -0.36, hz + 0.02), GOLD, segs=(12, 6), glow=2.8)           # great glowing eyes
		p.blob((0.15, 0.05, 0.17), (hx + sx * 0.25, -0.43, hz + 0.02), IRON, segs=(8, 5))
		p.blob((0.045, 0.02, 0.045), (hx + sx * 0.22, -0.47, hz + 0.07), CLOTH_WHITE, segs=(5, 3), glow=2.0)
		p.seg((hx + sx * 0.05, -0.4, hz + 0.22), (hx + sx * 0.5, -0.35, hz + 0.3), 0.045, 0.02, IRON, sides=4)   # fierce brows
	p.seg((hx, -0.42, hz - 0.08), (hx, -0.48, hz - 0.3), 0.08, 0.0, GOLD, sides=5)            # its hooked beak
	for x, z in ((-0.8, 1.45), (0.8, 1.2), (0.62, 1.55)):
		_twinkle(p, x, z, 0.05, glow=2.4, y=-0.1)
	return p.build()


def starfall_volley():
	p = Prop("starfall_volley", 1347)
	_ring(p, 1.0, -0.05, 0.045, CLOTH_RED, glow=1.8, sides=26)                               # on all near the target
	d = Vector((0.45, 0, -1.0)).normalized()
	for k, (x, z) in enumerate(((-0.75, 1.55), (-0.3, 1.7), (0.15, 1.6), (-0.55, 1.05), (-0.05, 1.12), (0.45, 1.2))):   # arrows falling like stars
		tip = Vector((x, -0.1, z)) + d * 0.9
		base = Vector((x, -0.1, z))
		p.seg(tuple(base - d * 0.55 + Vector((0, 0.08, 0))), tuple(base + Vector((0, 0.08, 0))), 0.0, 0.07, RUNE if k % 2 else PURPLE, sides=6, glow=2.0, grad=LILAC)
		_arrow(p, tuple(base), tuple(tip), hs=0.9, r=0.03, head=CLOTH_WHITE, glow=2.6, fletch=CLOTH_WHITE)
		_twinkle(p, tip.x + d.x * 0.25, tip.z + d.z * 0.25, 0.06, glow=2.8, y=-0.2)
	return p.build()


def veil_of_the_unlit():
	p = Prop("veil_of_the_unlit", 1349)
	outline = [(-0.3, 1.45), (0.3, 1.45), (0.62, 0.95), (0.8, 0.1), (0.55, -0.05), (0.3, 0.08), (0.05, -0.08),
			   (-0.22, 0.06), (-0.5, -0.06), (-0.8, 0.1), (-0.62, 0.95)]                          # a veil of the dark sky...
	icons._slab(p, outline[::-1], 0.0, 0.1, PURPLE, grad=(0.55, 1.0))
	for u, v in zip(outline, outline[1:] + outline[:1]):
		p.seg((u[0], -0.03, u[1]), (v[0], -0.03, v[1]), 0.04, 0.04, SILVER, sides=5, glow=1.2)
	for x in (-0.35, 0.0, 0.35):                                                          # ...falling in folds
		p.seg((x * 0.6, -0.02, 1.35), (x * 1.5, -0.02, 0.1), 0.025, 0.04, PURPLE, sides=5, grad=(0.85, 1.0))
	_silver_moon(p, 0.0, 1.05, 0.22, glow=2.2, y=-0.08, a0=100)                              # Timiraj's moon on its crown
	for x, z, s in ((-0.35, 0.7, 0.07), (0.3, 0.5, 0.06), (-0.1, 0.35, 0.05), (0.45, 0.95, 0.05), (-0.5, 0.3, 0.045), (0.1, 0.75, 0.05)):   # and its stars
		_twinkle(p, x, z, s, glow=2.6, y=-0.08)
	return p.build()


def crimson_kiss():
	p = Prop("crimson_kiss", 1351)
	cx, cz = 0.0, 0.85
	for sgn in (1, -1):                                                                   # red lips, parted...
		pts = []
		for k in range(15):
			t = k / 14
			x = -0.8 + t * 1.6
			bow = 0.12 * math.cos(t * math.tau * 2) * (1 if sgn > 0 else 0) if 0.3 < t < 0.7 else 0.0
			h = math.sin(t * math.pi) * (0.28 if sgn > 0 else 0.34)
			pts.append((cx + x, -0.05, cz + sgn * (0.08 + h - bow * 0.3)))
		for k, (u, v) in enumerate(zip(pts, pts[1:])):
			w = 0.03 + 0.13 * math.sin(math.pi * (k + 0.5) / 14)
			p.seg(u, v, w, w, CRIMSON, sides=8)
	p.seg((cx - 0.72, 0.05, cz), (cx + 0.72, 0.05, cz), 0.07, 0.07, IRON, sides=6)
	for sx in (-1, 1):                                                                    # ...over two fangs
		p.seg((cx + sx * 0.28, -0.02, cz + 0.12), (cx + sx * 0.26, -0.08, cz - 0.35), 0.075, 0.0, CLOTH_WHITE, sides=6, glow=0.8)
	_drop(p, cx + 0.26, cz - 0.62, 0.22, CLOTH_RED, 1.6)                                    # and a drop of blood
	p.seg((cx + 0.26, -0.1, cz - 0.38), (cx + 0.26, -0.1, cz - 0.5), 0.03, 0.05, CLOTH_RED, sides=5, glow=1.6)
	return p.build()


def shade_touch():
	p = Prop("shade_touch", 1353)
	_hand(p, 0.0, 0.65, 1.3, PURPLE, curl=0.4, glow=1.8, y=0.15)                              # a shade's glow...
	_hand(p, 0.0, 0.66, 1.2, IRON, curl=0.4, glow=0.0, y=0.0)                                # ...round its cold dark hand, reaching
	for k, (x0, z0) in enumerate(((0.55, 0.05), (-0.55, 0.15))):                         # shadow wisping off it
		_wind(p, (x0, z0), (x0 * 1.3, z0 + 0.75), swatch=MIST, r=0.06, up=1 if k else -1, curl=0.15, glow=0.8, y=-0.1)
	for x, z in ((-0.26, 1.55), (-0.08, 1.68), (0.1, 1.66), (0.27, 1.52)):                # frost at its fingertips
		p.blob((0.1, 0.08, 0.1), (x, -0.3, z), WATER, segs=(6, 4), glow=2.6, grad=(0.0, 0.3))
	_snowflake(p, 0.78, 1.3, 0.15, 2.2)
	_snowflake(p, -0.78, 1.1, 0.12, 2.2)
	return p.build()


def spirit_trumpet():
	p = Prop("spirit_trumpet", 1355)
	GHOST = (0.0, 0.3)                                                                    # RUNE's pale end: a ghost's blue
	hx, hz = 0.0, 0.7                                                                     # a great herd's ghost...
	for sx in (-1, 1):                                                                    # its broad ears
		p.blob((0.62, 0.14, 0.85), (hx + sx * 0.52, 0.15, hz + 0.02), RUNE, rot=(0, sx * 12, 0), segs=(10, 6), glow=0.6, grad=GHOST)
		p.blob((0.46, 0.1, 0.66), (hx + sx * 0.52, 0.06, hz + 0.02), CLOTH_WHITE, rot=(0, sx * 12, 0), segs=(10, 6), glow=0.8)
	p.blob((0.78, 0.66, 0.8), (hx, 0.0, hz), RUNE, segs=(12, 8), glow=0.8, grad=GHOST)
	for sx in (-1, 1):
		p.blob((0.1, 0.05, 0.1), (hx + sx * 0.17, -0.34, hz + 0.1), CLOTH_WHITE, segs=(6, 4), glow=3.2)   # its eyes
		p.seg((hx + sx * 0.15, -0.3, hz - 0.2), (hx + sx * 0.36, -0.42, hz - 0.5), 0.07, 0.0, BONE, sides=5, glow=0.4)   # tusks
	pts = []                                                                              # ...its trunk raised, trumpeting
	for k in range(15):
		t = k / 14
		pts.append((hx + 0.62 * t ** 1.3, -0.35 - 0.1 * t, hz - 0.1 - 0.45 * math.sin(t * math.pi * 0.9) + t * 1.0))
	for k, (u, v) in enumerate(zip(pts, pts[1:])):
		w = 0.15 - 0.07 * k / 14
		p.seg(u, v, w, w * 0.95, RUNE, sides=6, glow=0.8, grad=GHOST)
	tx, tz = pts[-1][0], pts[-1][2]
	p.blob((0.2, 0.1, 0.2), (tx, -0.46, tz), CLOTH_WHITE, segs=(8, 5), glow=1.6)
	for k in range(3):                                                                    # rings of sound
		_ring_at(p, tx, tz, 0.2 + k * 0.16, 0.04, CLOTH_WHITE if k % 2 else GOLD, glow=2.4, sides=8, a0=math.radians(-30), a1=math.radians(100), y=-0.5)
	for k in range(3):                                                                    # fading away below
		x = hx - 0.25 + k * 0.25
		p.seg((x, 0.1, hz - 0.3), (x - 0.08, 0.15, hz - 0.85 - (k % 2) * 0.12), 0.12, 0.0, RUNE, sides=5, glow=0.8, grad=GHOST)
	return p.build()


LEVEL_50 = [eclipse_strike, wall_of_the_unlit, worldbreaker, starlight_ward, dawn_in_darkness, covenant_of_light, starfire_lance, shadowbind,
			black_sun, nightblade, nightfall_edges, umbral_wound, starforged_mantle, starcall, cataclysm, unlit_rot, grave_ascendance,
			soul_reaver, frostfang_curse, spirit_of_the_ancients, timeless_stillness, starpiercer, nighthunters_eye, starfall_volley,
			veil_of_the_unlit, crimson_kiss, shade_touch, spirit_trumpet]



# ---------------------------------------------------------------- the Boneyard's summit: Lastwalk's stone soldiers and Timiraj's Table

def godfire():
	p = Prop("godfire", 1351)
	_ring_at(p, 0.0, 0.75, 0.78, 0.035, GOLD, glow=1.8, sides=26, y=0.3)                     # the gods' fire, under a halo
	for k in range(12):
		a = k * math.tau / 12 + 0.13
		r1 = 1.1 if k % 2 else 0.95
		p.seg((math.cos(a) * 0.84, 0.3, 0.75 + math.sin(a) * 0.84), (math.cos(a) * r1, 0.3, 0.75 + math.sin(a) * r1), 0.05, 0.0, GOLD, sides=4, glow=2.2)
	p.blob((0.9, 0.6, 0.6), (0.0, 0.0, 0.3), AMBER, segs=(12, 8), glow=1.2, grad=(0.0, 0.5))   # a flame of gold
	p.seg((0.0, 0.0, 0.34), (0.06, 0.0, 1.6), 0.42, 0.0, GOLD, sides=10, glow=1.3)
	for sx, h, lean in ((-1, 1.15, 0.18), (1, 1.05, 0.2), (-1, 0.75, 0.42), (1, 0.7, 0.44)):
		p.seg((sx * 0.2, 0.0, 0.3), (sx * (0.2 + lean), 0.0, h), 0.2, 0.0, GOLD, sides=8, glow=1.1, grad=(0.0, 0.6))
	p.blob((0.4, 0.3, 0.36), (0.0, -0.2, 0.36), CLOTH_WHITE, segs=(10, 6), glow=3.2)           # white-hot at its heart
	p.seg((0.0, -0.2, 0.4), (0.03, -0.2, 1.1), 0.18, 0.0, CLOTH_WHITE, sides=8, glow=3.2)
	for x, z, s in ((-0.7, 1.4, 0.08), (0.66, 1.52, 0.07), (0.5, 0.2, 0.06)):                 # sparks
		_twinkle(p, x, z, s, swatch=GOLD, glow=2.8, y=-0.3)
	return p.build()


def petrifying_blow():
	p = Prop("petrifying_blow", 1353)
	p.rock((0.95, 0.8, 0.9), (0.1, 0, 0.6), MIST, jitter=0.06)                               # a fist of gray stone
	for k in range(4):                                                                    # knuckles
		p.rock((0.28, 0.28, 0.28), (-0.26 + k * 0.23, -0.34, 1.0), MIST, jitter=0.04)
	p.rock((0.3, 0.3, 0.42), (0.6, -0.2, 0.6), MIST, jitter=0.04)                            # thumb
	p.seg((0.1, 0.05, 0.2), (0.25, 0.05, -0.3), 0.3, 0.34, MIST, sides=7, grad=(0.1, 0.9))     # its wrist
	for pts in (((-0.2, 1.04), (-0.12, 0.8), (-0.22, 0.6), (-0.08, 0.36)), ((0.3, 1.02), (0.24, 0.78), (0.36, 0.58)),
				((-0.12, 0.8), (0.1, 0.72)), ((0.24, 0.78), (0.46, 0.7))):                # cracking open
		_bolt_line(p, pts, 0.03, STONE_DARK, 0.0, y=-0.46)
		_bolt_line(p, pts, 0.014, GOLD, 2.6, y=-0.5)
	for a in (100, 140, 180, 60, 20):                                                     # as it strikes
		r = math.radians(a)
		p.seg((0.1 + math.cos(r) * 0.8, -0.3, 1.25 + math.sin(r) * 0.4 - 0.2), (0.1 + math.cos(r) * 1.1, -0.3, 1.25 + math.sin(r) * 0.6 - 0.2),
			  0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.4)
	for x, z, s in ((-0.72, 1.3, 0.13), (0.86, 1.2, 0.1), (-0.8, 0.8, 0.09), (0.8, 1.55, 0.08)):   # stone chips flying
		p.rock((s, s, s), (x, -0.3, z), STONE_LIGHT, jitter=0.2)
	return p.build()


def starfall_bolt():
	p = Prop("starfall_bolt", 1355)
	sx, sz = -0.3, 0.3                                                                    # a star falling...
	d = Vector((1.0, 0, 1.0)).normalized()
	n = Vector((-d.z, 0, d.x))
	for k, (w, sw, g, off) in enumerate(((0.3, NIGHT, 0.6, 0.12), (0.2, RUNE, 1.8, 0.0), (0.09, CLOTH_WHITE, 3.0, -0.06))):
		a = Vector((sx, off, sz)) + d * 0.1
		b = Vector((sx, off, sz)) + d * (1.8 - 0.3 * k)
		p.seg(tuple(a), tuple(b), w, 0.0, sw, sides=8, glow=g, grad=(0.0, 0.6) if sw == NIGHT else (0.1, 0.8))   # its long blazing tail
	for s, off in ((1, 0.2), (-1, 0.14)):
		a = Vector((sx, -0.02, sz)) + n * s * off + d * 0.2
		p.seg(tuple(a), tuple(a + d * 1.0), 0.03, 0.0, CLOTH_WHITE, sides=4, glow=2.6)
	_star(p, sx, sz, 0.32, CLOTH_WHITE, glow=3.2, y=-0.2, spin=-45)                             # ...its head a burning star
	p.blob((0.2, 0.12, 0.2), (sx, -0.3, sz), CLOTH_WHITE, segs=(8, 5), glow=3.6)
	for x, z, s in ((0.6, 0.3, 0.1), (-0.8, 1.2, 0.08), (0.2, 1.5, 0.07), (-0.84, 0.7, 0.06)):
		_twinkle(p, x, z, s, glow=2.6, y=-0.2)
	return p.build()


def uninvited_curse():
	p = Prop("uninvited_curse", 1357)
	for k, (x0, h, ph) in enumerate(((-0.46, 1.25, 0.0), (0.06, 1.45, 2.0), (0.5, 1.15, 4.0))):   # a violet curse smoking up behind...
		pts = [(x0 + 0.16 * math.sin(ph + t * 6.0) * (0.3 + t), 0.3, 0.5 + h * t) for t in (i / 12 for i in range(13))]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			w = 0.05 * (1 - i / 13) + 0.012
			p.seg(a, b, w, w * 0.9, PURPLE, sides=5, glow=2.0, grad=LILAC if k % 2 else (0.2, 0.7))
	cz = 0.2                                                                              # ...a dark crown
	band = [(-0.66, cz), (0.66, cz), (0.66, cz + 0.32), (-0.66, cz + 0.32)]
	icons._slab(p, band, -0.08, 0.08, IRON, grad=(0.1, 0.7))
	for z in (cz, cz + 0.32):
		p.seg((-0.68, -0.09, z), (0.68, -0.09, z), 0.035, 0.035, SILVER, sides=5)
	for k in range(7):                                                                    # of crooked black thorns
		x = -0.57 + k * 0.19
		h = (0.5, 0.7, 0.46, 0.95, 0.46, 0.7, 0.5)[k]
		lean = 0.09 * (1 if k % 2 else -1)
		mid = (x + lean, 0.0, cz + 0.3 + h * 0.55)
		p.seg((x, 0.0, cz + 0.3), mid, 0.1, 0.055, IRON, sides=5, grad=(0.1, 0.7))
		p.seg(mid, (x - lean * 0.5, 0.0, cz + 0.3 + h), 0.055, 0.0, SILVER, sides=5, grad=(0.2, 0.8))
	p.blob((0.26, 0.12, 0.24), (0.0, -0.1, cz + 0.16), PURPLE, segs=(8, 6), glow=2.8)         # a violet stone for an eye
	for x in (-0.4, 0.4):
		p.blob((0.12, 0.08, 0.12), (x, -0.08, cz + 0.16), PURPLE, segs=(6, 4), glow=2.2)
	for x, h in ((-0.3, 0.3), (0.12, 0.42), (0.46, 0.26)):                                  # its curse dripping down
		p.seg((x, -0.1, cz + 0.02), (x, -0.1, cz - h), 0.045, 0.0, PURPLE, sides=5, glow=2.2)
	for x, z, s in ((-0.62, 1.2, 0.1), (0.66, 1.5, 0.08)):
		p.blob((s, s * 0.8, s), (x, 0.1, z), PURPLE, segs=(6, 4), glow=1.6, grad=LILAC)
	return p.build()


BONEYARD_SUMMIT = [godfire, petrifying_blow, starfall_bolt, uninvited_curse]


MONSOON_WEST = [mud_spit, bog_bolt, eel_shock, bogwing_sting, hex_of_rot, mire_grip, undertow, naga_venom, tidal_bolt, lightning_lash,
				crushing_claw, drowning_grasp, cobra_venom]


NEW_SPELLS = [false_sunfire, aimed_shot, track, flame_lick, ensnare, salve, strength_of_the_wild, icicle, entangle, eagle_eye,
			  multishot, natures_mend, call_of_flame, thornskin, rapid_fire, barbed_arrow, frost_wind, call_of_the_hawk, volley,
			  guardian_of_the_wild, natures_renewal, piercing_shot, wildfire, hawks_fury, trueshot, storm_of_arrows, mighty_blow,
			  unbreakable, rampage, superior_healing, dawns_wrath, aegis_of_the_dawn, glacial_spike, mana_ward, inferno, shadowstrike,
			  blade_flurry, deathmark, elemental_mending, primal_surge, call_of_the_elemental_lord, soul_harvest, plague,
			  raise_bone_colossus, glacial_roar, tigirs_swarm, ancestral_avatar, harpy_shriek, monk_palm, ember_breath, cinder_bolt,
			  ash_chill, searing_blow]


# ---------------------------------------------------------------- The Blackwater gods

BOG_GREEN = (6, 1)     # yellow-green into teal
SEA_GREEN = (0, 2)     # sea green
OCHRE = (4, 2)         # orange-yellow
COPPER = (2, 0)        # the clay swatch reads as polished copper


def makarosh_blessing():
	"""Deep-Jaw's Patience: the crocodile god of the black water, jaws open, one eye burning over it."""
	p = Prop("makarosh_blessing", 2201)
	upper = [(-0.95, 0.66), (-0.9, 0.78), (-0.6, 0.8), (-0.2, 0.86), (0.15, 0.98), (0.45, 1.1), (0.72, 1.06), (0.9, 0.86), (0.9, 0.6),
			 (0.5, 0.58), (0.0, 0.6), (-0.5, 0.6)]
	icons._slab(p, upper[::-1], -0.12, 0.12, PINE, grad=(0.55, 1.0))                        # the upper jaw and skull
	lower = [(-0.86, 0.34), (-0.8, 0.26), (-0.3, 0.2), (0.2, 0.2), (0.62, 0.3), (0.9, 0.56), (0.5, 0.46), (0.0, 0.4), (-0.5, 0.38)]
	icons._slab(p, lower[::-1], -0.1, 0.1, PINE, grad=(0.7, 1.0))                          # the lower jaw, dropped open
	icons._slab(p, [(-0.8, 0.36), (-0.8, 0.6), (0.85, 0.6), (0.85, 0.5)][::-1], 0.02, 0.06, CLOTH_RED, grad=(0.5, 1.0))   # its dark maw
	for k in range(7):                                                                    # teeth down from the upper jaw...
		x = -0.82 + k * 0.22
		p.seg((x, -0.13, 0.63), (x + 0.02, -0.13, 0.48), 0.04, 0.0, BONE, sides=4)
	for k in range(6):                                                                    # ...and up from the lower
		x = -0.72 + k * 0.22
		p.seg((x, -0.11, 0.37), (x - 0.02, -0.11, 0.5), 0.035, 0.0, BONE, sides=4)
	for k in range(5):                                                                    # a row of scutes along the brow
		x = -0.2 + k * 0.2
		p.seg((x, 0.0, 0.88 + k * 0.05), (x + 0.03, 0.0, 0.98 + k * 0.05), 0.07, 0.0, IRON, sides=4)
	p.blob((0.12, 0.1, 0.1), (-0.88, -0.1, 0.8), IRON, segs=(6, 4))                           # a nostril knob
	p.blob((0.34, 0.26, 0.26), (0.46, -0.06, 1.1), PINE, segs=(10, 6), grad=(0.5, 1.0))      # the eye, raised
	p.blob((0.24, 0.1, 0.18), (0.46, -0.18, 1.1), GOLD, segs=(10, 6), glow=2.4)               # burning gold
	p.blob((0.05, 0.06, 0.17), (0.46, -0.23, 1.1), IRON, segs=(6, 4))                          # a slit pupil
	for k in range(3):                                                                    # the black water it waits in
		z = 0.02 - k * 0.1
		pts = [(-0.95 + t * 0.19, -0.15, z + math.sin(t * 1.4 + k) * 0.03) for t in range(11)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.028 - k * 0.006, 0.028 - k * 0.006, SEA_GREEN if k == 0 else BOG_GREEN, sides=4, glow=1.6 - k * 0.4)
	return p.build()


def mahishra_blessing():
	"""Mud-Horn's Strength: the water-buffalo god's head under great sweeping horns."""
	p = Prop("mahishra_blessing", 2203)
	p.blob((0.56, 0.5, 0.74), (0, 0, 0.5), COPPER, segs=(12, 8), grad=(0.3, 1.0))           # a broad copper-dark head
	p.blob((0.5, 0.4, 0.34), (0, -0.12, 0.2), COPPER, segs=(10, 6), grad=(0.0, 0.5))         # its muzzle
	for sx in (-1, 1):
		p.blob((0.08, 0.05, 0.1), (sx * 0.1, -0.31, 0.2), IRON, segs=(6, 4))                  # nostrils
		p.blob((0.1, 0.08, 0.08), (sx * 0.2, -0.22, 0.58), GOLD, segs=(6, 4), glow=2.2)      # eyes, glowing
		p.blob((0.3, 0.12, 0.14), (sx * 0.38, 0.0, 0.62), COPPER, rot=(0, sx * 20, 0), segs=(8, 5), grad=(0.2, 0.8))   # ears
		pts = []                                                                          # great horns sweeping out, back and up
		for k in range(12):
			t = k / 11
			a = math.radians(215 + t * 185)
			pts.append((sx * (0.62 + math.cos(a) * 0.5), 0.05 + t * 0.08, 1.12 + math.sin(a) * 0.5))
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			r0 = 0.15 * (1 - i / 11) + 0.02
			r1 = 0.15 * (1 - (i + 1) / 11) + 0.02 if i < 10 else 0.0
			p.seg(a, b, r0, r1, OCHRE, sides=8, grad=(0.0, 0.8))
		for i in (1, 3, 5):                                                               # ridged near the base
			a = Vector(pts[i])
			d = (Vector(pts[i + 1]) - a).normalized()
			r = 0.15 * (1 - i / 11) + 0.035
			p.seg(tuple(a), tuple(a + d * 0.03), r, r, WOOD, sides=8)
	p.seg((-0.2, 0.02, 0.84), (0.2, 0.02, 0.84), 0.13, 0.13, COPPER, sides=8, grad=(0.4, 1.0))   # the boss between them
	for k in range(5):                                                                    # a shaggy forelock
		x = -0.14 + k * 0.07
		p.seg((x, -0.18, 0.9), (x * 1.2, -0.28, 0.66 - (k % 2) * 0.06), 0.04, 0.0, WOOD, sides=4)
	c = (0, -0.3, 0.04)
	for k in range(12):                                                                   # a copper ring through its nose, gleaming
		a0, a1 = k * math.tau / 12, (k + 1) * math.tau / 12
		p.seg((c[0] + math.cos(a0) * 0.1, c[1], c[2] + math.sin(a0) * 0.1), (c[0] + math.cos(a1) * 0.1, c[1], c[2] + math.sin(a1) * 0.1),
			  0.025, 0.025, GOLD, sides=5, glow=1.8)
	return p.build()


BLACKWATER = [makarosh_blessing, mahishra_blessing]


# ---------------------------------------------------------------- the dusk gods (Duskhold)

def tantuvi_blessing():
	"""The Many-Eyed's Sight: the spider goddess's face, crowned with pale eyes, before her web of stars."""
	p = Prop("tantuvi_blessing", 2207)
	c = (0.0, 0.3, 0.62)
	for k in range(12):                                                                   # the web behind her: spokes...
		a = k * math.tau / 12 + 0.13
		p.seg(c, (math.cos(a) * 0.98, 0.3, 0.62 + math.sin(a) * 0.98), 0.014, 0.01, CLOTH_WHITE, sides=4, glow=1.4)
		if k % 2 == 0:                                                                    # ...stars where they end...
			_star(p, math.cos(a) * 1.0, 0.62 + math.sin(a) * 1.0, 0.09, CLOTH_WHITE, glow=2.6, y=0.28, points=4, inner=0.3)
	for rr in (0.36, 0.56, 0.76, 0.94):                                                  # ...and the spiral strung across them
		_ring_at(p, 0.0, 0.62, rr, 0.011, CLOTH_WHITE, glow=1.2, sides=12, y=0.3)
	for sx in (-1, 1):                                                                    # four legs a side, arching out
		for k in range(4):
			hip = (sx * 0.3, 0.12, 0.5 - 0.06 * k)
			knee = (sx * (0.62 + 0.06 * k), 0.12, 1.0 - 0.14 * k)
			foot = (sx * (0.86 + 0.02 * k), 0.12, 0.34 - 0.12 * k)
			p.seg(hip, knee, 0.06, 0.05, PURPLE, sides=6, grad=(0.7, 1.0))
			p.seg(knee, foot, 0.05, 0.015, PURPLE, sides=6, grad=(0.7, 1.0))
			p.blob((0.09, 0.09, 0.09), knee, PURPLE, segs=(6, 4), grad=(0.5, 0.9))
			band = tuple(knee[i] + (foot[i] - knee[i]) * 0.35 for i in range(3))
			p.seg(band, tuple(band[i] + (foot[i] - knee[i]) * 0.06 for i in range(3)), 0.058, 0.058, STONE_LIGHT, sides=6)
	p.blob((0.86, 0.6, 0.78), (0, 0, 0.56), PURPLE, segs=(14, 10), grad=(0.65, 1.0))      # her head, violet-black
	for (x, z, r) in ((0.15, 0.6, 0.22), (0.36, 0.64, 0.14), (0.12, 0.84, 0.12), (0.3, 0.84, 0.09), (0.44, 0.78, 0.07)):
		for sx in (-1, 1):                                                                # many eyes, glowing moon-white
			p.blob((r, r * 0.7, r), (sx * x, -0.26, z), CLOTH_WHITE, segs=(8, 6), glow=2.6)
	for k in range(9):                                                                    # a silver circlet over the brow
		a0, a1 = math.radians(20 + 140 * k / 9), math.radians(20 + 140 * (k + 1) / 9)
		p.seg((math.cos(a0) * 0.42, -0.22, 0.62 + math.sin(a0) * 0.42), (math.cos(a1) * 0.42, -0.22, 0.62 + math.sin(a1) * 0.42),
			  0.03, 0.03, STONE_LIGHT, sides=5)
	p.blob((0.12, 0.08, 0.15), (0, -0.26, 1.06), PURPLE, segs=(8, 6), grad=(0.0, 0.3), glow=1.6)   # a moonstone at its crown
	for sx in (-1, 1):                                                                    # the chelicerae and silver fangs
		p.blob((0.22, 0.2, 0.3), (sx * 0.12, -0.2, 0.22), PURPLE, segs=(8, 6), grad=(0.6, 1.0))
		p.seg((sx * 0.13, -0.24, 0.1), (sx * 0.1, -0.28, -0.08), 0.06, 0.03, STONE_LIGHT, sides=6)
		p.seg((sx * 0.1, -0.28, -0.08), (sx * 0.03, -0.27, -0.16), 0.03, 0.0, STONE_LIGHT, sides=6)
	return p.build()


def dipanti_blessing():
	"""The Lamp-Eater's Veil: the moth goddess, wings spread, a lamp burning in each of them."""
	p = Prop("dipanti_blessing", 2209)
	fore = [(0.1, 0.62), (0.4, 0.98), (0.78, 1.18), (1.0, 1.16), (1.04, 0.96), (0.9, 0.7), (0.6, 0.5), (0.3, 0.46)]
	hind = [(0.1, 0.44), (0.42, 0.42), (0.72, 0.34), (0.84, 0.12), (0.72, -0.08), (0.46, -0.14), (0.22, 0.0), (0.08, 0.22)]
	for sx in (-1, 1):
		for pts, spot, rr in ((fore, (0.66, 0.86), 0.17), (hind, (0.48, 0.14), 0.14)):
			out = [(sx * x, z) for x, z in pts]
			if sx < 0:
				out = out[::-1]
			cx = sum(x for x, _ in out) / len(out)
			cz = sum(z for _, z in out) / len(out)
			inner = [(cx + (x - cx) * 0.86, cz + (z - cz) * 0.86) for x, z in out]
			root = [(sx * 0.1 + (x - sx * 0.1) * 0.5, 0.45 + (z - 0.45) * 0.5) for x, z in out]
			icons._slab(p, out, 0.06, 0.1, GOLD, grad=(0.3, 0.8))                         # a dusky gold margin
			icons._slab(p, inner, 0.02, 0.06, MIST, grad=(0.2, 0.7))                      # the ash-gray wing
			icons._slab(p, root, -0.01, 0.02, PURPLE, grad=(0.3, 0.8))                    # washed violet at the root
			x, z = sx * spot[0], spot[1]                                                   # the lamp: a dark ring round gold...
			p.seg((x, -0.03, z), (x, 0.0, z), rr, rr, IRON, sides=16)
			p.seg((x, -0.05, z), (x, -0.02, z), rr * 0.78, rr * 0.78, GOLD, sides=16, glow=0.8)
			p.seg((x, -0.07, z), (x, -0.04, z), rr * 0.6, rr * 0.6, IRON, sides=16)
			p.blob((rr * 0.55, 0.04, rr * 0.7), (x, -0.08, z - rr * 0.08), FLAME, segs=(8, 5), glow=2.8)   # ...round a candle flame
			p.seg((x, -0.08, z + rr * 0.1), (x, -0.08, z + rr * 0.6), rr * 0.26, 0.0, FLAME, sides=6, glow=2.8)
	for k in range(6):                                                                    # a soft furred body
		z = 0.72 - k * 0.13
		r = 0.17 - 0.014 * k
		p.blob((r * 2, r * 1.6, 0.16), (0, -0.1, z), MIST if k % 2 == 0 else PURPLE, segs=(10, 6), grad=(0.3, 0.9))
	p.blob((0.46, 0.34, 0.2), (0, -0.14, 0.74), GOLD, segs=(10, 6), grad=(0.5, 0.9))       # the gold ruff at her collar
	p.blob((0.34, 0.3, 0.28), (0, -0.16, 0.9), MIST, segs=(10, 6), grad=(0.4, 0.9))        # her head
	for sx in (-1, 1):
		p.blob((0.16, 0.12, 0.18), (sx * 0.12, -0.28, 0.9), IRON, segs=(8, 6))            # great dark eyes...
		p.blob((0.04, 0.03, 0.05), (sx * 0.15, -0.34, 0.94), FLAME, segs=(5, 4), glow=2.6) # ...each holding a point of lamplight
		base = Vector((sx * 0.08, -0.2, 1.02))                                            # feathery antennae
		prev = base
		for k in range(1, 7):
			t = k / 6
			q = Vector((sx * (0.08 + 0.3 * t), -0.2, 1.02 + 0.34 * t - 0.12 * t * t))
			p.seg(tuple(prev), tuple(q), 0.022, 0.018, WOOD, sides=4)
			d = (q - prev).normalized()
			for sd in (-1, 1):
				n = Vector((-d.z, 0, d.x)) * sd
				p.seg(tuple(q), tuple(q + (n + d * 0.5).normalized() * 0.08 * math.sin(math.pi * (0.2 + 0.8 * t))), 0.016, 0.0, GOLD, sides=4)
			prev = q
	for k in range(7):                                                                    # a thread of smoke from a lamp put out
		t0, t1 = k / 7, (k + 1) / 7
		p.seg((0.06 * math.sin(t0 * 7), -0.1, 0.02 - 0.3 * t0), (0.06 * math.sin(t1 * 7), -0.1, 0.02 - 0.3 * t1), 0.03, 0.03, MIST, sides=4)
	return p.build()


DUSK = [tantuvi_blessing, dipanti_blessing]


SPELLS = {f.__name__: f for f in [kick, taunt, bash, bind_wound, battle_cry, minor_healing, light_healing,
								  circle_of_mending, strike, smite, blast_of_frost, fire_bolt, burning_embers,
								  gate, root, minor_shielding, courage, hearthward, hearthbond, blessing_of_the_elders,
								  heroic_strike, rally, shield_wall, healing, blessed_armor, circle_of_renewal,
								  hallowed_strike, frost_lance, emberstorm, greater_shielding, ice_comet,
								  thornback_venom, grave_chill, spirit_bolt, leech_bite, marsh_bolt, drowning_cold,
								  backstab, hide, sneak, evade, envenom_blade, rogue_venom, rake,
								  provoke, defensive_stance, cleave, greater_healing, divine_aura, sunfire, lightning_bolt, frost_snare,
								  fireball, assassinate, blind, deadly_poison, deadly_venom, dawn_tusk_blessing,
								  scorpion_venom, salt_gaze, shield_slam, battle_fury, whirlwind, healing_tide, word_of_awe,
								  armor_of_faith, chain_lightning, arcane_harvest, meteor, crippling_poison, crippling_venom, eviscerate, vanish,
								  storm_bolt, frog_poison, death_roll, tide_trunk_blessing, fish,
								  call_of_earth, call_of_water, call_of_fire, call_of_air, call_of_the_primal, renew_elements, greater_renewal, burnout, elemental_bond, primal_fury, elemental_aegis,
								  raise_bones, raise_skeletal_knight, mend_bones, dark_empowerment, lifetap, siphon_life, soul_rend, disease_cloud, venom_bolt,
								  bond_of_death, dread, mass_dread, feign_death, clinging_darkness, elemental_flame, gust_of_wind,
								  frost_rift, sicken, strengthen, inner_fire, drowsy, spirit_of_bear, spirit_mend, tainted_breath, feet_like_cat,
								  frost_strike, walking_sleep, spirit_healing, quickness, talisman_of_the_totem, envenomed_breath, spirit_regrowth,
								  tagars_insects, winters_roar, spirit_of_the_wolf, chant_of_the_pack, winters_grasp, turgurs_insects, kraggs_mending, ancestral_ward, homeward] + NEW_SPELLS + MONSOON_WEST + LEVEL_35 + LEVEL_40 + MAGE_BOLTS + LEVEL_45 + LEVEL_50 + BONEYARD_SUMMIT + BLACKWATER + DUSK}
ACTIONS = {f.__name__: f for f in [action_attack, action_ranged, action_sit, action_consider, action_skills, action_hail, action_loot,
								   action_pet_attack, action_pet_back, action_pet_follow, action_pet_guard, action_pet_sit,
								   action_friends, action_guild, action_journal, action_delete]}
SPELLS["velassas_company"] = velassas_company


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/icons", "--only": "", "--size": "128"}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) if opts["--only"] else None
	spells = json.load(open(os.path.join(icons.ROOT, "data/spells.json")))
	missing = [s for s in spells if s not in SPELLS and not s.startswith(("meal_", "potion_"))]  # those show their item's icon
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
