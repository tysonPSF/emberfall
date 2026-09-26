"""Original zone music in the spirit of classic EverQuest's MIDI themes: gentle
modal loops, one per zone, synthesized here from scratch (no samples) and
encoded to OGG Vorbis with Blender's bundled FFmpeg.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/audio/music.py -- --out assets/music [--only greenmoor] [--wav]

Every track is a small score: a key and mode, a tempo and meter, a chord
progression per section, and a form (A A' B A). Melodies are composed per
phrase from the chords (chord tones on strong beats, scale steps between,
a contour that rises and settles, cadences on the tonic) with a seeded random
source, so a track always comes out the same. Phrase A is written once and
reused, varied, so each piece has a tune you can recognize.

Instruments are additive synthesis in numpy: harp and lute (plucked partials
decaying at different rates), a recorder-like flute (vibrato, breath), a soft
pad, a round bass, a frame drum and a bell; a convolution reverb (decaying
noise) puts them in one room. Tracks loop seamlessly: the reverb tail wraps
onto the start.
"""

import math
import os
import sys
import wave

import numpy as np

SR = 44100
MODES = {
	"major": [0, 2, 4, 5, 7, 9, 11],
	"mixolydian": [0, 2, 4, 5, 7, 9, 10],
	"dorian": [0, 2, 3, 5, 7, 9, 10],
	"aeolian": [0, 2, 3, 5, 7, 8, 10],
}


# ---------------------------------------------------------------- instruments

def _t(dur):
	return np.arange(int(dur * SR)) / SR


def _env(n, attack, release):
	e = np.ones(n)
	a = min(int(attack * SR), n)
	r = min(int(release * SR), n - a)
	if a > 0:
		e[:a] = np.linspace(0, 1, a)
	if r > 0:
		e[n - r:] *= np.linspace(1, 0, r)
	return e


def harp(f, dur, vel=0.6, bright=1.0):
	t = _t(dur + 1.8)
	out = np.zeros_like(t)
	for k in range(1, 9):
		if f * k > SR / 2.2:
			break
		out += (1.0 / k ** (1.5 - 0.3 * bright)) * np.sin(2 * np.pi * f * k * t + k) * np.exp(-t * (1.1 + 0.8 * k))
	return out * _env(len(t), 0.004, 0.2) * vel * 0.5


def lute(f, dur, vel=0.6):
	t = _t(dur + 1.0)
	out = np.zeros_like(t)
	for k in range(1, 11):
		if f * k > SR / 2.2:
			break
		det = 1.0 + 0.0015 * (k % 3 - 1)
		out += (1.0 / k ** 1.05) * np.sin(2 * np.pi * f * k * det * t) * np.exp(-t * (2.2 + 1.4 * k))
	return out * _env(len(t), 0.003, 0.15) * vel * 0.45


def flute(f, dur, vel=0.6, rng=None):
	t = _t(dur + 0.25)
	vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.4, 0, 1)  # vibrato eases in
	phase = 2 * np.pi * f * np.cumsum(vib) / SR
	tone = np.sin(phase) + 0.22 * np.sin(2 * phase) + 0.07 * np.sin(3 * phase)
	noise = (rng or np.random.default_rng(1)).standard_normal(len(t))
	breath = np.convolve(noise, np.ones(40) / 40, mode="same") * 0.35
	e = _env(len(t), 0.07, 0.22) * (0.85 + 0.15 * np.exp(-t * 3))  # a little push at the start
	return (tone + breath) * e * vel * 0.32


def pad(f, dur, vel=0.4):
	t = _t(dur + 1.5)
	out = np.zeros_like(t)
	for det in (-0.004, 0.0, 0.0045):
		for k in range(1, 6):
			out += (1.0 / k ** 1.6) * np.sin(2 * np.pi * f * (1 + det) * k * t + det * 900)
	out *= 1.0 + 0.08 * np.sin(2 * np.pi * 0.35 * t)
	return out * _env(len(t), min(1.2, dur * 0.5), 1.5) * vel * 0.09


def bass(f, dur, vel=0.6):
	t = _t(dur + 0.6)
	out = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 3)
	return out * np.exp(-t * 1.2) * _env(len(t), 0.006, 0.3) * vel * 0.5


def drum(vel=0.5, rng=None):
	t = _t(0.6)
	f = 62 + 40 * np.exp(-t * 18)
	body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
	noise = (rng or np.random.default_rng(2)).standard_normal(len(t))
	slap = np.convolve(noise, np.ones(8) / 8, mode="same") * np.exp(-t * 60) * 0.5
	return (body + slap) * vel * 0.5


def horn(f, dur, vel=0.6):
	"""A soft brass voice: the upper partials swell in after the attack."""
	t = _t(dur + 0.3)
	vib = 1.0 + 0.003 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.2) / 0.3, 0, 1)
	phase = 2 * np.pi * f * np.cumsum(vib) / SR
	bright = np.clip(t / 0.12, 0, 1)
	out = np.zeros_like(t)
	for k in range(1, 9):
		if f * k > SR / 2.2:
			break
		out += (1.0 / k ** 1.3) * np.sin(k * phase) * (bright if k > 2 else 1.0)
	return out * _env(len(t), 0.05, 0.2) * vel * 0.2


def bell(f, dur, vel=0.4):
	t = _t(dur + 3.0)
	out = np.zeros_like(t)
	for ratio, amp, decay in ((1.0, 1.0, 0.9), (2.76, 0.45, 1.8), (5.4, 0.25, 3.2), (8.9, 0.1, 5.0)):
		out += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * decay)
	return out * _env(len(t), 0.002, 0.5) * vel * 0.18


# ---------------------------------------------------------------- theory

def midi_hz(m):
	return 440.0 * 2 ** ((m - 69) / 12)


class Key:
	def __init__(self, root, mode):
		self.root = root  # midi note of the tonic (octave 4-ish)
		self.steps = MODES[mode]

	def note(self, degree, octave=0):
		"""Scale degree (0 = tonic, may be negative or above 6) to a midi note."""
		o, d = divmod(degree, 7)
		return self.root + 12 * (o + octave) + self.steps[d]

	def chord(self, degree):
		"""Degrees of the triad on a scale degree."""
		return [degree, degree + 2, degree + 4]


# ---------------------------------------------------------------- composing

RHYTHMS = {  # per bar, in beats; 3/4 and 4/4
	3: [[2, 1], [1, 1, 1], [1.5, 0.5, 1], [3], [1, 2], [0.5, 0.5, 1, 1]],
	4: [[2, 2], [1, 1, 2], [1.5, 0.5, 2], [4], [2, 1, 1], [1, 1, 1, 1], [3, 1]],
}


def compose_phrase(key, chords, beats, rng, low=7, high=14, cadence=True, sparse=0.0):
	"""A melody over one chord per bar: [(start beat, length beats, degree)].
	Strong beats land on chord tones, the rest step through the scale, the
	contour rises in the middle of the phrase and settles, and the last note
	rests long on the tonic (or the chord's root for a half cadence)."""
	notes = []
	cur = 9  # start around the third above the tonic, an octave up
	bars = len(chords)
	for b, ch in enumerate(chords):
		rhythm = list(RHYTHMS[beats][rng.integers(len(RHYTHMS[beats]))])
		if b == bars - 1:
			rhythm = [beats]  # end the phrase on one long note
		pos = 0.0
		target_high = low + (high - low) * math.sin(math.pi * (b + 0.5) / bars)  # arch contour
		for i, length in enumerate(rhythm):
			strong = pos == 0 or (beats == 4 and pos == 2)
			if rng.random() < sparse and not strong and b != bars - 1:
				pos += length
				continue  # a breath
			tones = [d + 7 * o for d in key.chord(ch) for o in (0, 1, 2)]
			if b == bars - 1 and cadence:
				cands = [d for d in tones if d % 7 == 0] or [d for d in tones if d % 7 == ch % 7]  # tonic, else the chord's root
			elif strong:
				cands = tones
			else:
				cands = [cur + s for s in (-2, -1, 1, 2)]
			cands = [c for c in cands if low - 2 <= c <= high + 2] or tones
			# prefer small steps, drift toward the contour
			weights = np.array([1.0 / (1 + abs(c - cur)) ** 1.6 * (1.0 / (1 + abs(c - target_high) * 0.25))
								* (0.15 if c == cur else 1.0) for c in cands])  # a tune moves: repeats are rare
			cur = cands[rng.choice(len(cands), p=weights / weights.sum())]
			notes.append((b * beats + pos, length, cur))
			pos += length
	return notes


def vary(phrase, rng, amount=0.3):
	"""Phrase A again, slightly different: a few inner notes step elsewhere."""
	out = []
	for i, (s, l, d) in enumerate(phrase):
		if 0 < i < len(phrase) - 1 and rng.random() < amount:
			d += int(rng.choice([-1, 1]))
		out.append((s, l, d))
	return out


# ---------------------------------------------------------------- tracks

TRACKS = {
	"title": {
		"key": (62, "aeolian"), "bpm": 76, "beats": 4, "seed": 11,
		"sections": {"A": [0, 5, 2, 6], "B": [3, 4, 0, 4], "C": [5, 6, 3, 4]},
		"form": ["A", "A", "B", "C", "A"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 1, 2, 1, 0, 2, 1, 2], "pad": True, "bass": True,
		"drum": [0, 2.5], "drum_sections": ["B", "C"], "reverb": 2.8, "sparse": 0.1,
	},
	"emberhold": {
		"key": (62, "major"), "bpm": 92, "beats": 3, "seed": 5,
		"sections": {"A": [0, 3, 4, 0, 5, 1, 4, 0], "B": [3, 0, 3, 4, 5, 3, 4, 4]},
		"form": ["A", "A", "B", "A"],
		"melody": "flute", "arp": "lute", "arp_pattern": [0, 2, 1], "pad": False, "bass": True,
		"drum": [0, 2], "drum_sections": ["A", "B"], "reverb": 1.6, "sparse": 0.0,
	},
	"combat": {
		"key": (64, "aeolian"), "bpm": 132, "beats": 4, "seed": 41,
		"sections": {"A": [0, 5, 6, 0], "B": [3, 0, 5, 4], "C": [0, 5, 3, 4]},
		"form": ["A", "A", "B", "A", "C"],
		"melody": "horn", "arp": "lute", "arp_pattern": [0, 1, 2, 1, 0, 1, 2, 3], "pad": True, "bass": True, "bass_eighths": True,
		"drum": [0, 1, 1.5, 2, 3, 3.5], "drum_sections": ["A", "B", "C"], "reverb": 1.4, "sparse": 0.0,
	},
	"thornwood": {
		"key": (52, "aeolian"), "bpm": 60, "beats": 3, "seed": 71,
		"sections": {"A": [0, 5, 3, 4, 0, 5, 6, 0], "B": [5, 6, 0, 3, 5, 3, 4, 4]},
		"form": ["A", "B", "A", "B"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 2, 4], "pad": True, "bass": True,
		"drum": [0], "drum_sections": ["B"], "reverb": 3.6, "sparse": 0.3, "bells": 0.2,
	},
	"hollowmere": {
		"key": (55, "dorian"), "bpm": 54, "beats": 4, "seed": 97,
		"sections": {"A": [0, 6, 3, 0], "B": [5, 3, 6, 4], "C": [0, 3, 6, 6]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 1, 2, 4, 2, 1, 0, 2], "pad": True, "bass": False,
		"drum": [], "drum_sections": [], "reverb": 4.4, "sparse": 0.45, "bells": 0.45,
	},
	"greenmoor": {
		"key": (57, "dorian"), "bpm": 68, "beats": 4, "seed": 23,
		"sections": {"A": [0, 3, 0, 6], "B": [3, 6, 0, 4], "C": [2, 3, 0, 0]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 2, 4, 2, 1, 2, 4, 2], "pad": True, "bass": False,
		"drum": [], "drum_sections": [], "reverb": 3.2, "sparse": 0.35, "bells": 0.3,
	},
}


def render(name, spec):
	rng = np.random.default_rng(spec["seed"])
	key = Key(*spec["key"])
	beats, bpm = spec["beats"], spec["bpm"]
	beat = 60.0 / bpm
	bars_total = sum(len(spec["sections"][s]) for s in spec["form"])
	length = bars_total * beats * beat
	n = int((length + 4.0) * SR)
	L, R = np.zeros(n), np.zeros(n)

	def put(sig, at, pan=0.0, gain=1.0):
		i = max(0, int(at * SR))  # a humanized note at 0:00 can't start before the track
		j = min(n, i + len(sig))
		if i >= n:
			return
		L[i:j] += sig[:j - i] * gain * math.cos((pan + 1) * math.pi / 4)
		R[i:j] += sig[:j - i] * gain * math.sin((pan + 1) * math.pi / 4)

	phrases = {}  # each section's tune, written the first time it's heard
	bar = 0
	for si, sec in enumerate(spec["form"]):
		chords = spec["sections"][sec]
		if sec not in phrases:
			phrases[sec] = compose_phrase(key, chords, beats, rng, sparse=spec.get("sparse", 0.0),
										  cadence=(sec != "B"))
			tune = phrases[sec]
		else:
			tune = vary(phrases[sec], rng)
		t0 = bar * beats * beat
		# melody
		for s, l, d in tune:
			f = midi_hz(key.note(d))
			vel = 0.55 + 0.1 * rng.random()
			voice = horn(f, l * beat * 0.95, vel) if spec["melody"] == "horn" else flute(f, l * beat * 0.95, vel, rng)
			put(voice, t0 + s * beat + rng.normal(0, 0.006), pan=0.15)
		# harmony, per bar
		for b, ch in enumerate(chords):
			tb = t0 + b * beats * beat
			triad = [key.note(d, -1) for d in key.chord(ch)]
			if spec["pad"]:
				for m in triad:
					put(pad(midi_hz(m), beats * beat * 1.02, 0.45), tb, pan=-0.2)
			if spec.get("bass_eighths"):  # a driving ostinato: root and octave on every half beat
				for k in range(beats * 2):
					m = key.note(ch, -2) + (12 if k % 4 == 3 else 0)
					put(bass(midi_hz(m), beat * 0.45, 0.5 if k % 2 == 0 else 0.38), tb + k * beat / 2)
			elif spec["bass"]:
				put(bass(midi_hz(key.note(ch, -2)), beats * beat * 0.9, 0.55), tb)
			pattern = spec["arp_pattern"]
			step = beats * beat / len(pattern)
			tones = [key.note(d, -1) for d in key.chord(ch)] + [key.note(ch + 7, -1), key.note(ch + 9, -1)]
			for k, idx in enumerate(pattern):
				f = midi_hz(tones[idx])
				vel = (0.5 if k == 0 else 0.34) + 0.06 * rng.random()
				inst = lute(f, step * 1.5, vel) if spec["arp"] == "lute" else harp(f, step * 2.5, vel)
				put(inst, tb + k * step + rng.normal(0, 0.004), pan=-0.35 if k % 2 else -0.15)
			if sec in spec["drum_sections"]:
				for d in spec["drum"]:
					put(drum(0.55 if d == 0 or d == 2 else 0.35, rng), tb + d * beat, pan=0.05)
			if spec.get("bells") and rng.random() < spec["bells"]:
				put(bell(midi_hz(key.note(rng.choice(key.chord(ch)), 1)), 2.0, 0.5), tb + beat * rng.integers(1, beats), pan=0.4)
		bar += len(chords)

	# the room: a decaying-noise reverb, a little different on each side
	for chan, seed in ((L, 101), (R, 202)):
		ir_t = _t(spec["reverb"])
		noise = np.random.default_rng(seed).standard_normal(len(ir_t))
		noise = np.convolve(noise, np.ones(6) / 6, mode="same")  # darker tail
		ir = noise * np.exp(-ir_t * 6.9 / spec["reverb"])
		ir[: int(0.012 * SR)] = 0  # pre-delay
		ir /= np.sqrt(np.sum(ir ** 2))
		size = 1 << int(math.ceil(math.log2(len(chan) + len(ir))))
		wet = np.fft.irfft(np.fft.rfft(chan, size) * np.fft.rfft(ir, size), size)[: len(chan)]
		chan[:] = chan * 0.78 + wet * 0.42
	# loop: fold everything after the end back onto the start, so it wraps seamlessly
	end = int(length * SR)
	for chan in (L, R):
		tail = chan[end:]
		chan[: len(tail)] += tail
	L, R = L[:end], R[:end]
	peak = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
	scale = 0.8 / peak
	return np.stack([L * scale, R * scale], axis=1), length


def write_wav(path, stereo):
	data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
	with wave.open(path, "wb") as w:
		w.setnchannels(2)
		w.setsampwidth(2)
		w.setframerate(SR)
		w.writeframes(data.tobytes())


def encode_ogg(wav_path, ogg_path, seconds):
	"""Blender's FFmpeg: a sound strip mixed down to OGG Vorbis."""
	import bpy
	bpy.ops.wm.read_factory_settings(use_empty=True)
	scene = bpy.context.scene
	scene.render.fps = 30
	scene.frame_start = 1
	scene.frame_end = int(math.ceil(seconds * 30))
	ed = scene.sequence_editor_create()
	strips = ed.strips if hasattr(ed, "strips") else ed.sequences
	strip = strips.new_sound("music", wav_path, 1, 1)
	scene.frame_end = strip.frame_final_end - 1  # end inside the strip: a scene longer than its sound mixes down empty
	bpy.ops.sound.mixdown(filepath=ogg_path, container="OGG", codec="VORBIS", format="S16", bitrate=160,
						  mixrate=SR, accuracy=1024)
	# the mixdown keeps writing after the call returns: wait for the file to
	# stop growing, or the next track (or quitting) cuts it short
	import time
	last, still = -1, 0
	while still < 8:
		time.sleep(0.25)
		size = os.path.getsize(ogg_path) if os.path.exists(ogg_path) else 0
		still = still + 1 if size == last and size > 0 else 0
		last = size


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	out = argv[argv.index("--out") + 1] if "--out" in argv else "assets/music"
	only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
	keep_wav = "--wav" in argv
	os.makedirs(out, exist_ok=True)
	for name, spec in TRACKS.items():
		if only and name not in only:
			continue
		stereo, seconds = render(name, spec)
		wav = os.path.abspath(os.path.join(out, name + ".wav"))
		write_wav(wav, stereo)
		encode_ogg(wav, os.path.abspath(os.path.join(out, name + ".ogg")), seconds)
		if not keep_wav:
			os.remove(wav)
		print("track %s: %.1f s" % (name, seconds))


if __name__ == "__main__":
	main()
