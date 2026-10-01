class_name GuildStore
extends RefCounted
## Guilds, kept where the rules run: a server's <data>/guilds.json, or
## user://guilds.json offline. A guild is keyed by its name in lower case:
##   {name, motd, founded, members: {name lower: {name, rank, level, class, zone, seen, grove}}}
## Each member's line is what the roster shows when they're offline (level,
## class, last zone, when last seen) and the gods they've earned, so the
## Grove can share them with guildmates who aren't online (World.grove_sees).
## Ranks: "leader" (one), "officer", "member".
## The guild bank lives with the guild: "bank" (BANK_SLOTS entries, {} for an
## empty slot, bags with their contents), "bank_coin" and "bank_log" (the
## last BANK_LOG deposits and withdrawals: {at, who, what}).

const RANKS := ["member", "officer", "leader"]  # lowest first: a rank's index is its power
const BANK_SLOTS := 40
const BANK_LOG := 100

var path := ""
var guilds: Dictionary = {}
var _of: Dictionary = {}  # character name lower -> guild key
var _dirty := false


func _init(file_path: String) -> void:
	path = file_path
	if FileAccess.file_exists(path):
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
		if parsed is Dictionary:
			guilds = parsed
	for key: String in guilds:
		for member: String in guilds[key].get("members", {}):
			_of[member] = key


## The guild a character belongs to ({} for none).
func guild_of(char_name: String) -> Dictionary:
	return guilds.get(_of.get(char_name.to_lower(), ""), {})


func key_of(char_name: String) -> String:
	return str(_of.get(char_name.to_lower(), ""))


func rank_of(char_name: String) -> String:
	var g := guild_of(char_name)
	return str(g["members"][char_name.to_lower()]["rank"]) if not g.is_empty() else ""


static func power(rank: String) -> int:
	return RANKS.find(rank)


func name_taken(guild_name: String) -> bool:
	return guilds.has(guild_name.to_lower())


func found(guild_name: String, leader: Dictionary) -> void:
	var key := guild_name.to_lower()
	guilds[key] = {"name": guild_name, "motd": "", "founded": Time.get_datetime_string_from_system(), "members": {}}
	join(key, leader, "leader")


## Adds (or updates) a member: `who` is their roster line (name, level, class, zone, grove).
func join(key: String, who: Dictionary, rank: String) -> void:
	var line := who.duplicate()
	line["rank"] = rank
	guilds[key]["members"][str(who["name"]).to_lower()] = line
	_of[str(who["name"]).to_lower()] = key
	save()


func leave(char_name: String) -> void:
	var key := key_of(char_name)
	if key == "":
		return
	guilds[key]["members"].erase(char_name.to_lower())
	_of.erase(char_name.to_lower())
	if (guilds[key]["members"] as Dictionary).is_empty():
		guilds.erase(key)  # the last one out closes the door
	save()


func disband(key: String) -> void:
	for member: String in guilds.get(key, {}).get("members", {}):
		_of.erase(member)
	guilds.erase(key)
	save()


func set_rank(char_name: String, rank: String) -> void:
	var g := guild_of(char_name)
	if not g.is_empty():
		g["members"][char_name.to_lower()]["rank"] = rank
		save()


func set_motd(key: String, text: String) -> void:
	guilds[key]["motd"] = text
	save()


## An online member's roster line kept current (level, zone, gods); written
## out with the next save rather than at once.
func touch(char_name: String, fields: Dictionary) -> void:
	var g := guild_of(char_name)
	if g.is_empty():
		return
	var line: Dictionary = g["members"][char_name.to_lower()]
	for k: String in fields:
		if line.get(k) != fields[k]:
			line[k] = fields[k]
			_dirty = true


## The guild's bank (its dictionary, with "bank", "bank_coin" and "bank_log"
## made if it had none); {} for no guild.
func bank_of(key: String) -> Dictionary:
	if not guilds.has(key):
		return {}
	var g: Dictionary = guilds[key]
	if not g.has("bank"):
		g["bank"] = []
	var slots: Array = g["bank"]
	while slots.size() < BANK_SLOTS:
		slots.append({})
	for i in slots.size():  # JSON brings counts back as floats
		if not (slots[i] as Dictionary).is_empty():
			slots[i]["count"] = int(slots[i].get("count", 1))
	g["bank_coin"] = int(g.get("bank_coin", 0))
	if not g.has("bank_log"):
		g["bank_log"] = []
	return g


func bank_empty(key: String) -> bool:
	var g := bank_of(key)
	return g.is_empty() or (int(g["bank_coin"]) <= 0 and (g["bank"] as Array).all(func(e: Dictionary) -> bool: return e.is_empty()))


## A line in the bank's log, then saved at once: what's in the bank is never left to a later save.
func bank_note(key: String, who: String, what: String) -> void:
	var g := bank_of(key)
	if g.is_empty():
		return
	var log: Array = g["bank_log"]
	log.append({"at": int(Time.get_unix_time_from_system()), "who": who, "what": what})
	while log.size() > BANK_LOG:
		log.remove_at(0)
	save()


func save_if_dirty() -> void:
	if _dirty:
		save()


func save() -> void:
	_dirty = false
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(guilds, "  "))
