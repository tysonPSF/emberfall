class_name AccountStore
extends RefCounted
## The server's accounts and characters, as JSON files under one data folder
## (--data=<dir>, default user://server):
##   accounts/<account>.json    {salt, hash, characters: [names]}
##   characters/<name>.json     the character's save, exactly as offline saves look
## Clients send a hash of (account, password), never the password itself; the
## server stores that hash salted and stretched again.

const NAME_RULE := "^[A-Za-z]{3,15}$"
const ACCOUNT_RULE := "^[A-Za-z0-9_]{3,20}$"
const STRETCH := 2000

var root := "user://server"


func _init(data_dir: String) -> void:
	root = data_dir
	for sub in ["accounts", "characters"]:
		DirAccess.make_dir_recursive_absolute(root.path_join(sub))


## Returns "" on success, or why not.
func create_account(account: String, pw_hash: String) -> String:
	if RegEx.create_from_string(ACCOUNT_RULE).search(account) == null:
		return "Account names are 3-20 letters, digits or underscores."
	if FileAccess.file_exists(_account_path(account)):
		return "That account name is taken."
	var salt := Crypto.new().generate_random_bytes(16).hex_encode()
	_write(_account_path(account), {"salt": salt, "hash": _stretch(salt, pw_hash), "characters": []})
	return ""


func check_login(account: String, pw_hash: String) -> String:
	var a := _read(_account_path(account))
	if a.is_empty() or _stretch(str(a["salt"]), pw_hash) != str(a["hash"]):
		return "Wrong account name or password."
	return ""


## [{name, class, level, zone}] for the character select screen.
func characters(account: String) -> Array:
	var out: Array = []
	for name: String in _read(_account_path(account)).get("characters", []):
		var c := load_character(name)
		if not c.is_empty():
			out.append({"name": c["name"], "class": c["class"], "level": int(c.get("level", 1)),
					"zone": c.get("zone", ""), "deity": c.get("deity", "")})
	return out


func owns(account: String, name: String) -> bool:
	return name in _read(_account_path(account)).get("characters", [])


## A brand-new level 1 character, or why not. Offline characters come in
## through import_character instead.
func create_character(account: String, name: String, cls: String, deity: String, start_zone: String) -> String:
	var why := _name_problem(name)
	if why != "":
		return why
	if not GameData.classes.has(cls):
		return "Unknown class."
	if not GameData.deities.has(deity):
		return "Choose a deity."
	return _add(account, {"name": name.to_lower().capitalize(), "class": cls, "deity": deity, "zone": start_zone})


## Brings an offline character onto the server once, cleaned up: unknown
## items dropped, level kept within the cap.
func import_character(account: String, save: Dictionary) -> String:
	var name := str(save.get("name", ""))
	var why := _name_problem(name)
	if why != "":
		return why
	if not GameData.classes.has(str(save.get("class", ""))):
		return "That character's class doesn't exist here."
	var d := save.duplicate(true)
	d["level"] = clampi(int(d.get("level", 1)), 1, int(GameData.config.get("max_level", 10)))
	var known := func(id: Variant) -> bool: return GameData.items.has(GameData.base_item(str(id)))
	d["inventory"] = (d.get("inventory", []) as Array).filter(known)
	d["bank_items"] = (d.get("bank_items", []) as Array).filter(known)
	var eq: Dictionary = d.get("equipment", {})
	for slot: String in eq.keys():
		if not known.call(eq[slot]):
			eq.erase(slot)
	return _add(account, d)


func load_character(name: String) -> Dictionary:
	return _read(_character_path(name))


func save_character(save: Dictionary) -> void:
	_write(_character_path(str(save["name"])), save)


func _add(account: String, save: Dictionary) -> String:
	var a := _read(_account_path(account))
	if a.is_empty():
		return "Not logged in."
	save_character(save)
	(a["characters"] as Array).append(str(save["name"]))
	_write(_account_path(account), a)
	return ""


func _name_problem(name: String) -> String:
	if RegEx.create_from_string(NAME_RULE).search(name) == null:
		return "Names must be 3-15 letters, no spaces or numbers."
	if FileAccess.file_exists(_character_path(name)):
		return "Someone on this server already goes by %s." % name.to_lower().capitalize()
	return ""


func _stretch(salt: String, pw_hash: String) -> String:
	var h := salt + pw_hash
	for k in STRETCH:
		h = (salt + h).sha256_text()
	return h


func _account_path(account: String) -> String:
	return root.path_join("accounts/%s.json" % account.to_lower())


func _character_path(name: String) -> String:
	return root.path_join("characters/%s.json" % name.to_lower())


func _read(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


func _write(path: String, d: Dictionary) -> void:
	var tmp := path + ".tmp"  # write then swap, so a crash never leaves half a file
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_error("Could not write %s" % path)
		return
	f.store_string(JSON.stringify(d, "  "))
	f.close()
	DirAccess.rename_absolute(tmp, path)
