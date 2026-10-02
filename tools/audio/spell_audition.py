"""Candidate magic sounds to listen to before they go in the game (2026-10-01).

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \\
        -P tools/audio/spell_audition.py -- --out <dir>

Renders two or three takes of each spell sound (casting by element, landing by
look, level up) from the temple's instruments in sfx.py (singing bowls, gongs,
temple bells, chimes, the conch) with an element's texture under them, as
short mono WAVs plus manifest.json for a sound board. The chosen takes move into
sfx.py's SOUNDS.
"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx  # noqa: E402
import music  # noqa: E402

SR = sfx.SR
hz = music.midi_hz


def mix(*parts):
	"""(signal, gain, delay s) layers summed."""
	n = max(int(d * SR) + len(x) for x, g, d in parts)
	out = np.zeros(n)
	for x, g, d in parts:
		i = int(d * SR)
		out[i:i + len(x)] += x / max(np.abs(x).max(), 1e-9) * g
	return out


def rec(ref, rate=1.0):
	return sfx.rate_change(sfx.trim(sfx.load(ref)), rate)


def crackle(dur=3.0):
	"""Fire's crackle from the RPG pack's spell_fire takes, laid end to end and looped to length."""
	parts = [rec("RPG:spell_fire_0%d" % k) for k in (2, 3, 4, 5)]
	x = np.concatenate(parts)
	reps = int(np.ceil(dur * SR / len(x)))
	return np.tile(x, reps)[: int(dur * SR)]


def splash(k=1):
	import glob
	hits = sorted(glob.glob(os.path.join(sfx._cache_dir, "WAT", "**", "*.ogg"), recursive=True))
	return hits


def water_rec(name):
	return rec("WAT:" + name)


def fade(x, out=0.3):
	k = min(len(x) // 3, int(out * SR))
	x = x.copy()
	x[-k:] *= np.linspace(1, 0, k)
	return x


C = {}  # id -> (group, label, description, signal, loop)


def add(cid, group, label, desc, sig, loop=False, peak=0.6):
	sig = sig / max(np.abs(sig).max(), 1e-9) * peak
	C[cid] = (group, label, desc, sig, loop)


def build():
	D = 3.4  # loops: rendered long, folded into a seamless 3 s
	# ---- channeling: one sound for every spell (the touch below adds the element)
	add("cast_base_a", "Channeling", "A", "Gathering air with a faint high shimmer.", sfx.loopable(sfx.channel_air(D)), True, 0.4)
	add("cast_base_b", "Channeling", "B", "A warm, low swell that breathes in and out.", sfx.loopable(sfx.channel_warm(D)), True, 0.32)
	add("cast_base_c", "Channeling", "C", "Glassy high tones, turning slowly.", sfx.loopable(sfx.channel_glass(D)), True, 0.3)
	# ---- the element's touch: quiet, played over the channel
	T = 0.16
	add("touch_water", "Element touches", "Water / frost", "Droplets.", sfx.loopable(sfx.droplets(D, 9, 71)), True, T)
	add("touch_fire", "Element touches", "Fire", "Ember crackle.", sfx.loopable(crackle(D)), True, T + 0.04)
	add("touch_lightning", "Element touches", "Lightning", "Electric snaps.", sfx.loopable(sfx.zaps(D, 8, 72)), True, T)
	add("touch_wind", "Element touches", "Wind", "A breeze.", sfx.loopable(sfx.breath(D, 73, 700, 3400)), True, T)
	add("touch_dark", "Element touches", "Dark", "A low murmur.", sfx.loopable(sfx.lowpass(sfx.whisper(D, 74), 2800.0)), True, T)
	add("touch_light", "Element touches", "Light / healing", "Tiny bells.", sfx.loopable(sfx.wind_chimes(10, D, 75, 93)), True, T)
	add("touch_earth", "Element touches", "Earth / stone", "A low rumble.", sfx.loopable(sfx.rumble(D, 76)), True, T + 0.06)
	add("touch_poison", "Element touches", "Poison / nature", "Soft bubbling.", sfx.loopable(sfx.bubbles(D, 14, 77)), True, T)
	# ---- landing: one sound for what harms, one for what helps, and a quick touch of the element (no bowls, no bells)
	def thump(f0=110.0, f1=42.0, d=0.32):
		t = sfx._t(d)
		f = f1 + (f0 - f1) * np.exp(-t * 14)
		return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

	def puff(d=0.4, seed=1, cut=1800.0):
		rng = np.random.default_rng(seed)
		t = sfx._t(d)
		return sfx.lowpass(rng.standard_normal(len(t)), cut) * np.exp(-t * 11) * np.clip(t / 0.004, 0, 1)

	add("land_hit_a", "Landing: harmful", "A", "A soft magical burst with a low thump.",
		fade(mix((sfx.whoosh(0.36, 400, 2600, 201, 0.25), 1.0, 0), (thump(), 0.8, 0.04)), 0.15), peak=0.55)
	add("land_hit_b", "Landing: harmful", "B", "A deep whump.",
		fade(mix((thump(150, 38, 0.45), 1.0, 0), (puff(0.3, 202, 900.0), 0.5, 0)), 0.15), peak=0.55)
	add("land_hit_c", "Landing: harmful", "C", "A quick swell into a puff of release.",
		fade(mix((sfx.whoosh(0.18, 300, 1400, 203, 0.95), 0.6, 0), (puff(0.45, 204, 2200.0), 1.0, 0.17)), 0.15), peak=0.55)
	add("land_help_a", "Landing: helpful", "A", "A soft rising whoosh.",
		fade(sfx.whoosh(0.7, 300, 3200, 211, 0.8), 0.2), peak=0.45)
	t = sfx._t(0.9)
	swell = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((261.6, 1.0), (329.6, 0.6), (392.0, 0.5))) * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 2
	add("land_help_b", "Landing: helpful", "B", "A warm swell, in and out.", swell, peak=0.38)
	add("land_help_c", "Landing: helpful", "C", "A breath of air.", fade(sfx.breath(0.8, 212, 500, 2400) * np.sin(np.pi * sfx._t(0.8)[:int(0.8 * SR)] / 0.8), 0.1), peak=0.42)

	def glints(d=0.6, n=12, seed=7):
		rng = np.random.default_rng(seed)
		out = np.zeros(int(d * SR))
		for k in range(n):
			g = rng.standard_normal(int(0.012 * SR))
			g = (g - sfx.lowpass(g, 6000.0)) * np.exp(-np.arange(len(g)) / SR * 300)
			at = int(rng.uniform(0, d - 0.02) * SR)
			out[at:at + len(g)] += g * rng.uniform(0.3, 1.0)
		return out
	H = 0.35  # the touch's level against the base
	add("tl_water", "Landing touch: Water / frost", "Water / frost", "A splash.", rec("WAT:splash_04"), peak=H)
	add("tl_fire", "Landing touch: Fire", "Fire", "A flare.", fade(rec("RPG:spell_fire_06")[: int(0.7 * SR)], 0.2), peak=H)
	add("tl_lightning", "Landing touch: Lightning", "Lightning", "A crack.", sfx.zaps(0.25, 4, 221), peak=H)
	add("tl_wind", "Landing touch: Wind", "Wind", "A gust.", sfx.whoosh(0.5, 600, 3600, 222, 0.4), peak=H)
	add("tl_dark", "Landing touch: Dark", "Dark", "A low swoosh and a murmur.", mix((sfx.whoosh(0.5, 150, 700, 223, 0.4), 1.0, 0), (sfx.lowpass(sfx.whisper(0.5, 224), 2600.0), 0.4, 0.05)), peak=H)
	add("tl_light", "Landing touch: Light / healing", "Light / healing", "Glints of air.", glints(), peak=H * 0.8)
	add("tl_earth", "Landing touch: Earth / stone", "Earth / stone", "A stone thud.", mix((rec("RPG:stones_04", 0.85), 1.0, 0), (rec("IMP:impactMining_001"), 0.6, 0)), peak=H)
	add("tl_poison", "Landing touch: Poison / nature", "Poison / nature", "A fizz and a bubble.", mix((rec("WAT:bubble_01"), 1.0, 0), (puff(0.4, 225, 6000.0) - puff(0.4, 225, 2000.0), 0.6, 0)), peak=H)
	# ---- level up
	notes = [(0.0, 72), (0.14, 76), (0.28, 79), (0.48, 84)]
	fl = mix(*[(music.flute(hz(m), 0.5 if m == 84 else 0.16, 0.7), 0.6, at) for at, m in notes])
	add("level_up_a", "Level up", "A", "A temple bell, a rising flute phrase and a frame drum.",
		fade(mix((sfx.temple_bell(hz(72), 3.0), 1.0, 0), (fl, 0.8, 0.12), (sfx.frame_drum(0.8, 131), 0.6, 0), (sfx.frame_drum(0.6, 132), 0.4, 0.48))), peak=0.7)
	add("level_up_b", "Level up", "B", "A conch call over a bell chord.",
		fade(mix((sfx.conch(hz(60), 1.6, 133), 0.9, 0), (sfx.temple_bell(hz(72), 3.0, 0.8), 0.6, 0.3), (sfx.temple_bell(hz(76), 3.0, 0.7), 0.5, 0.3), (sfx.temple_bell(hz(79), 3.0, 0.7), 0.5, 0.3))), peak=0.7)
	add("level_up_c", "Level up", "C", "Bells climbing a chord over a little drum roll, then a gong.",
		fade(mix(*([(sfx.temple_bell(hz(m), 2.2, 0.7), 0.6, k * 0.12) for k, m in enumerate((72, 76, 79, 84))]
				   + [(sfx.frame_drum(0.3 + 0.08 * k, 140 + k), 0.4, k * 0.06) for k in range(8)] + [(sfx.gong(130, 2.4, 149), 0.7, 0.5)]))), peak=0.7)


def write(path, x, rate=22050):
	import wave
	x = np.interp(np.arange(0, len(x) * rate / SR) * SR / rate, np.arange(len(x)), x)
	data = (np.clip(x, -1, 1) * 32767).astype("<i2")
	with wave.open(path, "wb") as w:
		w.setnchannels(1)
		w.setsampwidth(2)
		w.setframerate(rate)
		w.writeframes(data.tobytes())


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	out = argv[argv.index("--out") + 1]
	sfx._cache_dir = argv[argv.index("--cache") + 1] if "--cache" in argv else os.path.expanduser("~/.cache/emberfall_sfx")
	sfx.fetch(sfx._cache_dir)
	build()
	os.makedirs(out, exist_ok=True)
	man = []
	for cid, (group, label, desc, sig, loop) in C.items():
		write(os.path.join(out, cid + ".wav"), sig)
		man.append({"id": cid, "group": group, "label": label, "desc": desc, "loop": loop, "seconds": round(len(sig) / SR, 2)})
	json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
	print("wrote %d takes to %s" % (len(man), out))


if __name__ == "__main__":
	main()
