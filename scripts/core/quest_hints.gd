class_name QuestHints
## Where to find what a quest wants, and where its giver stands, worked out
## from the game's own data (which monsters drop an item and where the zones
## spawn them, which waters it's fished from, which quest hands it out) so
## every quest gets hints without anyone writing them. A quest may still say
## it better itself: "hints": {item id: text} in quests.json wins.

const WHERE := ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
const NEAR := {
	"obelisk": "the obelisk", "camp": "the camp", "ruins": "the ruins", "outpost": "the outpost",
	"watchtower": "the watchtower", "cave": "the cave", "sun_shrine": "a shrine", "waystation": "the waystation",
	"stilt_village": "the stilt village", "lizard_camp": "the lizardfolk camp", "sunken_ruins": "the sunken ruins",
	"windmill": "the windmill", "orchard": "the orchard", "cabin": "the cabin", "spider_nest": "the spider nest",
	"bridge": "the bridge", "fields": "the fields", "house": "the houses",
}

const NEAR_PROPS := {
	"jungle_temple": "Jalendra's temple", "troll_hut": "the troll huts", "jalendra_head_fallen": "the fallen stone head",
	"waterfall": "the waterfall", "titan_ribcage": "the titan's bones", "caravan_wagon": "the wagons", "mesa": "the mesa",
	"windmill": "the windmill", "well": "the well", "market_stall": "the market",
}

static var _zones: Dictionary = {}  # zone id -> its data file


static func zones() -> Dictionary:
	if _zones.is_empty():
		for f in DirAccess.get_files_at("res://data/zones"):
			if f.ends_with(".json"):
				var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/zones/" + f))
				if parsed is Dictionary:
					_zones[f.get_basename()] = parsed
	return _zones


## Lines telling where to get `item_id` for `quest_id`. `here` / `at` are the
## player's zone id and position, for "northwest of you" when it's close by.
static func item_hint(quest_id: String, item_id: String, here: String, at: Vector3) -> PackedStringArray:
	var out: PackedStringArray = []
	var name := GameData.item_name(item_id)
	var q: Dictionary = GameData.quests.get(quest_id, {})
	var written: Dictionary = q.get("hints", {})
	if written.has(item_id):
		out.append("%s: %s" % [name, written[item_id]])
		return out
	# monsters that drop it, by zone
	var droppers: Array[String] = []
	for mob_id: String in GameData.mobs:
		for l: Dictionary in GameData.mobs[mob_id].get("loot", []):
			if str(l.get("item", "")) == item_id:
				droppers.append(mob_id)
				break
	for zone_id: String in zones():
		var z: Dictionary = zones()[zone_id]
		var common: Array[String] = []
		var common_at: Array[Vector2] = []
		var common_night := true
		var named: Dictionary = {}  # mob id -> [positions, night only, its rare spot's placeholder pool or {}]
		for s: Dictionary in z.get("spawns", []):
			var pos := Vector2(float(s["pos"][0]), float(s["pos"][1]))
			var night := str(s.get("when", "")) == "night"
			for mob_id: String in (s.get("pool", {}) as Dictionary):
				if mob_id not in droppers:
					continue
				if GameData.mobs[mob_id].get("named", false):
					var n: Array = named.get(mob_id, [[], true, {}])
					(n[0] as Array).append(pos)
					n[1] = bool(n[1]) and night
					var rare := SpawnPoint.rare_spot(z.get("spawns", []), s)
					if not rare.is_empty():
						n[2] = rare["pool"]
					named[mob_id] = n
				else:
					if mob_id not in common:
						common.append(mob_id)
					common_at.append(pos)
					common_night = common_night and night
		var zone_name := str(z.get("name", zone_id.capitalize()))
		if not common.is_empty():
			var who := _list(common.map(func(m: String) -> String: return _plural(str(GameData.mobs[m]["name"]))))
			out.append("%s: %s drop them in %s, %s%s.%s" % [name, who, zone_name, _region(z, common_at, zone_id == here, at),
					" (only at night)" if common_night else "",
					" Circled on your map (M)." if zone_id == here and areas(quest_id, item_id).any(func(a: Dictionary) -> bool: return a["zone"] == zone_id) else ""])
		for mob_id: String in named:
			var n: Array = named[mob_id]
			var who := str(GameData.mobs[mob_id]["name"])
			var line := "%s: %s carries %s in %s, %s%s." % [name, who, "one" if common.is_empty() else "them too",
					zone_name, _region(z, n[0], zone_id == here, at), " (only at night)" if n[1] else ""]
			var ph: Dictionary = n[2]
			if not ph.is_empty():  # a rare spawn: say what stands in its place, so nobody thinks it's gone
				var holders := _list(ph.keys().map(func(m: String) -> String: return _plural(str(GameData.mobs[m]["name"]))))
				line += " Not always there: %s hold the spot. Keep clearing them, and sooner or later the one you want shows up." % holders
			if zone_id == here:
				line += " Its haunt is circled on your map (M)."
			out.append(line)
		var fish: Dictionary = z.get("fish", {})
		if fish.has(item_id):
			out.append("%s: fished from the water in %s (a fishing pole and bait)." % [name, zone_name])
	# handed out by an earlier quest
	for other_id: String in GameData.quests:
		var o: Dictionary = GameData.quests[other_id]
		if str(o.get("first_reward_item", "")) == item_id:
			out.append("%s: %s gives it for finishing %s." % [name, _npc_name(str(o["giver"])), o["name"]])
	# sold, or made
	for npc_id: String in GameData.npcs:
		var m: Variant = GameData.npcs[npc_id].get("merchant")
		if m is Dictionary and item_id in (m as Dictionary).get("sells", []):
			out.append("%s: %s sells it." % [name, _npc_name(npc_id)])
	var recipes: Dictionary = GameData.recipes.get("recipes", {})
	for r_id: String in recipes:
		if item_id in JSON.stringify(recipes[r_id].get("out", "")):
			out.append("%s: made with %s." % [name, str(recipes[r_id].get("skill", "a tradeskill")).capitalize()])
			break
	if out.is_empty():
		out.append("%s: nobody seems to know where these come from." % name)
	return out


## Rough circles on a zone's map where `item_id` for `quest_id` is to be had
## from monsters: one round each named that carries it, one round the
## ordinary ones that drop it (none when they're all over the zone). Each is
## {zone, center, radius, label, quest, item}, deliberately loose: at least
## 60 m across the spots' spread, its middle nudged off them by up to a third
## of that (the same nudge every time), so it says where to look, not where
## it stands.
static func areas(quest_id: String, item_id: String) -> Array:
	var key := quest_id + ":" + item_id
	if _areas.has(key):
		return _areas[key]
	var out: Array = []
	var droppers: Array[String] = []
	for mob_id: String in GameData.mobs:
		for l: Dictionary in GameData.mobs[mob_id].get("loot", []):
			if str(l.get("item", "")) == item_id:
				droppers.append(mob_id)
				break
	for zone_id: String in zones():
		var z: Dictionary = zones()[zone_id]
		var groups: Dictionary = {}  # mob id (a named) or "" (the ordinary ones) -> positions
		for s: Dictionary in z.get("spawns", []):
			var pos := Vector2(float(s["pos"][0]), float(s["pos"][1]))
			for mob_id: String in (s.get("pool", {}) as Dictionary):
				if mob_id in droppers:
					var g := mob_id if GameData.mobs[mob_id].get("named", false) else ""
					var list: Array = groups.get(g, [])
					list.append(pos)
					groups[g] = list
		var size := float(z.get("size", 384.0))
		for g: String in groups:
			var spots: Array = groups[g]
			var c := Vector2.ZERO
			for p: Vector2 in spots:
				c += p
			c /= spots.size()
			var spread := 0.0
			for p: Vector2 in spots:
				spread = maxf(spread, p.distance_to(c))
			if g == "" and spots.size() > 2 and spread > size * 0.4:
				continue  # all over the zone: no circle would help
			var radius := clampf(spread + 35.0, 60.0, 160.0)
			var rng := RandomNumberGenerator.new()
			rng.seed = hash(key + zone_id + g)
			var nudge := Vector2.from_angle(rng.randf() * TAU) * rng.randf_range(0.15, 0.33) * radius
			var label := ""
			if g != "":
				label = _cap(str(GameData.mobs[g]["name"])) + "'s haunt"
			else:
				var names: Array = []
				for s: Dictionary in z.get("spawns", []):
					for mob_id: String in (s.get("pool", {}) as Dictionary):
						if mob_id in droppers and not GameData.mobs[mob_id].get("named", false) and _plural(str(GameData.mobs[mob_id]["name"])) not in names:
							names.append(_plural(str(GameData.mobs[mob_id]["name"])))
				label = _cap(_list(names.slice(0, 2)))
			out.append({"zone": zone_id, "center": c + nudge, "radius": radius, "label": label, "quest": quest_id, "item": item_id})
	_areas[key] = out
	return out


static var _areas: Dictionary = {}  # "quest:item" -> areas(), worked out once (the data doesn't change)


## The areas for every item still wanted on p's active quests in `zone_id`.
static func open_areas(p: Player, zone_id: String) -> Array:
	var out: Array = []
	for quest_id: String in p.quests:
		if not p.quests[quest_id].get("active", false) or not GameData.quests.has(quest_id):
			continue
		var have := World.quest_progress(p, quest_id)
		var wants: Dictionary = GameData.quests[quest_id]["wants"]
		for item_id: String in wants:
			if int(have[item_id]) >= int(wants[item_id]):
				continue
			for a: Dictionary in areas(quest_id, item_id):
				if a["zone"] == zone_id:
					out.append(a)
	return out


## Whether p stands inside one of the areas for this quest's item, here.
static func inside(p: Player, quest_id: String, item_id: String, zone_id: String) -> bool:
	for a: Dictionary in areas(quest_id, item_id):
		if a["zone"] == zone_id and Vector2(p.global_position.x, p.global_position.z).distance_to(a["center"]) <= float(a["radius"]):
			return true
	return false


static func _cap(t: String) -> String:
	return t.left(1).to_upper() + t.substr(1)


## Where a quest's giver stands, for handing it in; or, if someone in the
## field also takes it ("also_taken_by"), the nearest of them: one in this
## zone before one elsewhere.
static func giver_hint(quest_id: String, here: String, at: Vector3) -> String:
	var q: Dictionary = GameData.quests.get(quest_id, {})
	var giver := str(q.get("giver", ""))
	var takers: Array = [giver] + Array(q.get("also_taken_by", []))
	var best: Array = []  # [rank, npc id, zone id, pos]
	for zone_id: String in zones():
		var z: Dictionary = zones()[zone_id]
		for n: Dictionary in z.get("npcs", []):
			if str(n.get("id", "")) in takers:
				var pos := Vector2(float(n["pos"][0]), float(n["pos"][1]))
				var rank := pos.distance_to(Vector2(at.x, at.z)) if zone_id == here else 1e9 + takers.find(str(n["id"]))
				if best.is_empty() or rank < float(best[0]):
					best = [rank, str(n["id"]), zone_id, pos]
	if best.is_empty():
		return "%s: hand it in to %s." % [q.get("name", quest_id), _npc_name(giver)]
	var bz: Dictionary = zones()[best[2]]
	return "%s: hand it in to %s in %s, %s." % [q["name"], _npc_name(best[1]), bz.get("name", best[2]), _region(bz, [best[3]], best[2] == here, at)]


static func _npc_name(npc_id: String) -> String:
	return str(GameData.npcs.get(npc_id, {}).get("name", npc_id.capitalize()))


## "to the west, near the camp", "all over", and when you're in that zone,
## "(northwest of you, about 140 m)".
static func _region(z: Dictionary, spots: Array, here: bool, at: Vector3) -> String:
	var c := Vector2.ZERO
	for p: Vector2 in spots:
		c += p
	c /= maxf(1.0, spots.size())
	var spread := 0.0
	for p: Vector2 in spots:
		spread = maxf(spread, p.distance_to(c))
	var size := float(z.get("size", 384.0))
	var text := ""
	if spots.size() > 2 and spread > size * 0.4:
		text = "all over the zone"
	elif c.length() < size * 0.12:
		text = "in the middle"
	else:
		text = "to the " + _compass(c)
		var near := _landmark_near(z, c, maxf(40.0, spread + 25.0))
		if near != "":
			text += ", near " + near
	if here:
		var d := c - Vector2(at.x, at.z)
		text += " (%s)" % ("right around you" if d.length() < 30.0 else "%s of you, about %d m" % [_compass(d), roundi(d.length() / 10.0) * 10])
	return text


## Map directions: -z is north, +x east.
static func _compass(d: Vector2) -> String:
	var deg := rad_to_deg(atan2(d.x, -d.y))
	return WHERE[posmod(roundi(deg / 45.0), 8)]


static func _landmark_near(z: Dictionary, c: Vector2, within: float) -> String:
	var best := ""
	var best_d := within
	for lm: Dictionary in z.get("landmarks", []):
		var kind := str(lm.get("type", ""))
		var label := str(NEAR_PROPS.get(str(lm.get("id", "")), "")) if kind == "prop" else str(NEAR.get(kind, ""))
		if label == "" or not lm.has("pos"):
			continue
		var d := c.distance_to(Vector2(float(lm["pos"][0]), float(lm["pos"][1])))
		if d < best_d:
			best_d = d
			best = label
	return best


## "a timber wolf" -> "timber wolves", "a cultist of the false sun" ->
## "cultists of the false sun".
static func _plural(mob_name: String) -> String:
	var n := mob_name
	for article: String in ["a ", "an ", "the "]:
		if n.begins_with(article):
			n = n.substr(article.length())
	var of := n.find(" of ")
	if of > 0:
		return _plural(n.left(of)) + n.substr(of)
	if n.ends_with("f"):
		return n.left(-1) + "ves"
	if n.ends_with("y") and not n.substr(n.length() - 2, 1) in ["a", "e", "o", "u"]:
		return n.left(-1) + "ies"
	if n.ends_with("s") or n.ends_with("x") or n.ends_with("ch") or n.ends_with("sh"):
		return n + "es"
	return n + "s"


static func _list(words: Array) -> String:
	if words.size() <= 1:
		return "".join(words)
	return ", ".join(words.slice(0, -1)) + " and " + str(words[-1])
