class_name GuildStore
extends RefCounted
## Guilds, kept where the rules run: a server's <data>/guilds.json, or
## user://guilds.json offline. A guild is keyed by its name in lower case:
##   {name, motd, founded, members: {name lower: {name, rank, level, class, zone, seen, grove}}}
## Each member's line is what the roster shows when they're offline (level,
## class, last zone, when last seen) and the gods they've earned, so the
## Grove can share them with guildmates who aren't online (World.grove_sees).
## Ranks: "leader" (one), "officer", "member".

const RANKS := ["member", "officer", "leader"]  # lowest first: a rank's index is its power

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


func save_if_dirty() -> void:
	if _dirty:
		save()


func save() -> void:
	_dirty = false
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(guilds, "  "))
