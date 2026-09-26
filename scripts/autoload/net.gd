extends Node
## Networking. One server runs the game rules (World); clients mirror what the
## server tells them and send their World.request_* calls up to it.
##
## Modes:
##   "offline" - single player: the rules run here and the player is local.
##   "server"  - dedicated and headless (--server): the rules run here and every
##               player is on another machine.
##   "client"  - connected to a server: nothing is simulated here. Entities are
##               puppets that follow the server's snapshots; only the local
##               player's own movement starts here, and the server checks it.
##
## Everything travels as RPCs on this autoload, so both ends share the path
## /root/Net. Server-to-client calls are named _s_*, client-to-server _c_*.

signal connected_ok  # client: the connection is up; log in next
signal characters_listed(list: Array)  # client: logged in; the account's characters
signal server_message(text: String, is_error: bool)  # client: a note for the login screens
signal joined(player_id: int, zone_id: String, pos: Vector3, rot: float, save: Dictionary)  # client: we're in the world
signal join_failed(reason: String)  # client: could not connect
signal left_server(reason: String)  # client: disconnected or kicked
signal zone_moved(zone_id: String, pos: Vector3)  # client: the server moved us to another zone
signal camp_done  # client: our camp finished; back to character select

const DEFAULT_PORT := 7777
const PROTOCOL := 11  # bump when the messages change, so old clients are turned away
const MAX_PLAYERS := 32
const SNAPSHOT_HZ := 15.0
const SELF_HZ := 5.0
const MOVE_HZ := 20.0
const SAVE_SECONDS := 30.0  # server: everyone online is written to disk this often
const KEYFRAME_SECONDS := 1.0  # every entity's state is resent this often, in case packets were lost
const STATE_STRIDE := 9  # floats per entity in a snapshot
const ROWS_PER_PACKET := 30  # keeps each snapshot packet under the network's ~1400 byte limit
const CH_STATE := 1  # unreliable channel for snapshots
const CH_MOVE := 2  # unreliable channel for client movement

var mode := "offline"
var my_player_id := -1  # client: our player's id on the server
var address := ""  # client: the server we're connected to

# server: set up by main
var accounts: AccountStore
var start_zone := ""
var make_player: Callable  # (peer_id, save) -> Player, or null to refuse
var save_of: Callable  # (Player) -> Dictionary
var remove_player: Callable  # (Player) -> void, takes it out of the world

var _sessions := {}  # peer id -> account name, once logged in
var _peer_player := {}  # peer id -> player entity id, while in the world
var _known := {}  # peer id -> {object id: true} already spawned on that client
var _sent := {}  # peer id -> {object id: PackedFloat32Array last sent}
var _keyframe_timer := 0.0
var _keyframe := false
var _teleport_seq := {}  # player id -> int, bumped whenever the server moves the player
var _last_move := {}  # player id -> msec of the last accepted move
var _snap_timer := 0.0
var _self_timer := 0.0
var _save_timer := 0.0

# client
var _move_timer := 0.0
var _pending_spawns: Array = []  # spawns that arrived while our zone was being rebuilt
var _seq := 0  # the newest teleport seen; moves from before it are dropped by the server


func is_authority() -> bool:
	return mode != "client"


# --- connecting --------------------------------------------------------------

func host(port := DEFAULT_PORT) -> Error:
	var peer := ENetMultiplayerPeer.new()
	var err := peer.create_server(port, MAX_PLAYERS, 3)
	if err != OK:
		return err
	multiplayer.multiplayer_peer = peer
	mode = "server"
	multiplayer.peer_disconnected.connect(_on_peer_left)
	print("Emberfall server listening on UDP port %d" % port)
	return OK


## Client: connect to "host", "host:port" or "" (this machine). Then log in.
func connect_to(server: String) -> void:
	leave()
	address = server.strip_edges()
	var host_name := address
	var port := DEFAULT_PORT
	if host_name.contains(":"):
		port = int(host_name.get_slice(":", 1))
		host_name = host_name.get_slice(":", 0)
	var peer := ENetMultiplayerPeer.new()
	var err := peer.create_client(host_name if host_name != "" else "127.0.0.1", port, 3)
	if err != OK:
		join_failed.emit("Could not reach %s (%s)." % [address, error_string(err)])
		return
	multiplayer.multiplayer_peer = peer
	mode = "client"
	multiplayer.connected_to_server.connect(func() -> void: connected_ok.emit(), CONNECT_ONE_SHOT)
	multiplayer.connection_failed.connect(func() -> void: _drop("No answer from %s." % address, true), CONNECT_ONE_SHOT)
	multiplayer.server_disconnected.connect(func() -> void: _drop("The server closed the connection.", false), CONNECT_ONE_SHOT)


## Client: the password never leaves this machine; the server gets a hash of it.
func login(account: String, password: String, create := false) -> void:
	login_hashed(account, password_hash(account, password), create)


## What the server checks instead of the password (and what "Remember
## password" keeps, so the password itself is never written down).
static func password_hash(account: String, password: String) -> String:
	return ("emberfall:%s:%s" % [account.to_lower(), password]).sha256_text()


func login_hashed(account: String, pw_hash: String, create := false) -> void:
	_c_login.rpc_id(1, account.strip_edges(), pw_hash, PROTOCOL, create)


func create_character(name: String, cls: String, deity: String) -> void:
	_c_create_character.rpc_id(1, name, cls, deity)


## Client: bring an offline character onto the server (once).
func import_character(save: Dictionary) -> void:
	_c_import.rpc_id(1, save)


func enter_world(name: String) -> void:
	_c_enter.rpc_id(1, name)


## Client: hang up and go back to offline.
func leave() -> void:
	_disconnect_signals()
	if multiplayer.multiplayer_peer != null:
		multiplayer.multiplayer_peer.close()
	multiplayer.multiplayer_peer = null
	mode = "offline"
	my_player_id = -1
	_pending_spawns = []


func _drop(reason: String, during_connect: bool) -> void:
	leave()
	if during_connect:
		join_failed.emit(reason)
	else:
		left_server.emit(reason)


func _disconnect_signals() -> void:
	for s: Signal in [multiplayer.connected_to_server, multiplayer.connection_failed, multiplayer.server_disconnected]:
		for c: Dictionary in s.get_connections():
			s.disconnect(c["callable"])


# --- accounts and characters (client -> server) ----------------------------------

@rpc("any_peer", "reliable")
func _c_login(account: String, pw_hash: String, protocol: int, create: bool) -> void:
	if mode != "server":
		return
	var peer := multiplayer.get_remote_sender_id()
	if protocol != PROTOCOL:
		_s_message.rpc_id(peer, "This server runs a different version of Emberfall. Update your game and try again.", true)
		return
	var why := accounts.create_account(account, pw_hash) if create else accounts.check_login(account, pw_hash)
	if why != "":
		_s_message.rpc_id(peer, why, true)
		return
	for other: int in _sessions:
		if str(_sessions[other]).to_lower() == account.to_lower() and other != peer:
			_s_message.rpc_id(peer, "That account is already logged in.", true)
			return
	_sessions[peer] = account
	print("%s logged in (peer %d)" % [account, peer])
	_send_characters(peer)


@rpc("any_peer", "reliable")
func _c_create_character(name: String, cls: String, deity: String) -> void:
	var peer := multiplayer.get_remote_sender_id()
	if not _sessions.has(peer):
		return
	var why := accounts.create_character(_sessions[peer], name, cls, deity, start_zone)
	if why != "":
		_s_message.rpc_id(peer, why, true)
		return
	_send_characters(peer)


@rpc("any_peer", "reliable")
func _c_import(save: Dictionary) -> void:
	var peer := multiplayer.get_remote_sender_id()
	if not _sessions.has(peer):
		return
	var why := accounts.import_character(_sessions[peer], save)
	if why != "":
		_s_message.rpc_id(peer, why, true)
		return
	_s_message.rpc_id(peer, "%s is now on this server." % str(save.get("name", "")).to_lower().capitalize(), false)
	_send_characters(peer)


@rpc("any_peer", "reliable")
func _c_enter(name: String) -> void:
	var peer := multiplayer.get_remote_sender_id()
	if not _sessions.has(peer) or _peer_player.has(peer) or not accounts.owns(_sessions[peer], name):
		return
	var save := accounts.load_character(name)
	var p: Player = make_player.call(peer, save)
	if p == null:
		_s_message.rpc_id(peer, "The server could not load %s." % name, true)
		return
	_peer_player[peer] = p.entity_id
	_known[peer] = {p.entity_id: true}  # the client builds its own player
	_sent.erase(peer)
	_teleport_seq[p.entity_id] = 0
	_last_move[p.entity_id] = Time.get_ticks_msec()
	_s_welcome.rpc_id(peer, p.entity_id, World.zone_of(p).zone_id, p.global_position, p.rotation.y, save_of.call(p))
	_send_self(peer)
	print("%s entered the world (peer %d)" % [p.display_name, peer])


func _send_characters(peer: int) -> void:
	_s_characters.rpc_id(peer, accounts.characters(_sessions[peer]))


@rpc("authority", "reliable")
func _s_characters(list: Array) -> void:
	characters_listed.emit(list)


@rpc("authority", "reliable")
func _s_message(text: String, is_error: bool) -> void:
	server_message.emit(text, is_error)


@rpc("authority", "reliable")
func _s_welcome(player_id: int, zone_id: String, pos: Vector3, rot: float, save: Dictionary) -> void:
	my_player_id = player_id
	joined.emit(player_id, zone_id, pos, rot, save)


## Server: writes a player's character to disk.
func save_player(p: Player) -> void:
	if accounts != null and is_instance_valid(p):
		accounts.save_character(save_of.call(p))


## Server: the player left the world (camp or disconnect): save, then remove.
func _take_out(peer: int) -> void:
	var p := player_of_peer(peer)
	_peer_player.erase(peer)
	_known.erase(peer)
	_sent.erase(peer)
	if p != null:
		save_player(p)
		remove_player.call(p)


func _on_peer_left(peer: int) -> void:
	var p := player_of_peer(peer)
	if p != null:
		print("%s left (peer %d)" % [p.display_name, peer])
	_take_out(peer)
	_sessions.erase(peer)


# --- lookups -------------------------------------------------------------------

func player_of_peer(peer: int) -> Player:
	return World.get_object(int(_peer_player.get(peer, -1))) as Player


func peer_of(p: Player) -> int:
	for peer: int in _peer_player:
		if _peer_player[peer] == p.entity_id:
			return peer
	return 0


## True for a player whose game runs on another machine.
func is_remote(p: Player) -> bool:
	return mode == "server" and peer_of(p) != 0


# --- requests (client -> server) -----------------------------------------------

## Client: send a World.request_* call up. The first argument (our own id) is
## replaced by the server with the sender's player, so nobody can act for
## someone else.
func send_request(method: StringName, args: Array) -> void:
	if method == &"request_set_target" and World.local_player != null:
		World.local_player.target = World.get_object(int(args[1])) if int(args[1]) >= 0 else null  # feel instant
	_c_request.rpc_id(1, method, args)


@rpc("any_peer", "reliable")
func _c_request(method: StringName, args: Array) -> void:
	var peer := multiplayer.get_remote_sender_id()
	var p := player_of_peer(peer)
	if p == null or not String(method).begins_with("request_") or not World.has_method(method) or args.is_empty():
		return
	args[0] = p.entity_id
	World.callv(method, args)
	_send_self(peer)


# --- movement ------------------------------------------------------------------

## Client: our player's position, sent a few times a second.
func send_move(p: Player, delta: float) -> void:
	_move_timer += delta
	if _move_timer < 1.0 / MOVE_HZ:
		return
	_move_timer = 0.0
	_c_move.rpc_id(1, p.global_position, p.rotation.y, _seq)


@rpc("any_peer", "unreliable_ordered", "call_remote", CH_MOVE)
func _c_move(pos: Vector3, rot: float, seq: int) -> void:
	var p := player_of_peer(multiplayer.get_remote_sender_id())
	if p == null or p.dead or seq != int(_teleport_seq.get(p.entity_id, 0)):
		return
	var now := Time.get_ticks_msec()
	var dt := maxf(0.05, (now - int(_last_move.get(p.entity_id, now))) / 1000.0)
	_last_move[p.entity_id] = now
	var flat := Vector2(pos.x - p.global_position.x, pos.z - p.global_position.z).length()
	var top := Player.RUN_SPEED * (1.0 + GameData.deity_bonus(p.deity, "run_speed_pct") / 100.0) * float(World.cfg("sprint_speed_mult", 1.55))
	var allowed := top * 1.3 * dt + 2.0
	if flat > allowed:
		teleport(p, p.global_position)  # too fast: put them back
		return
	p.global_position = pos
	p.rotation.y = rot


## Server: the rules moved a player (gate, respawn, zoning). Tell their client,
## and ignore movement it sent from before the jump.
func teleport(p: Player, pos: Vector3) -> void:
	if not is_remote(p):
		return
	var seq := int(_teleport_seq.get(p.entity_id, 0)) + 1
	_teleport_seq[p.entity_id] = seq
	_s_teleport.rpc_id(peer_of(p), pos, seq)


@rpc("authority", "reliable")
func _s_teleport(pos: Vector3, seq: int) -> void:
	_seq = seq
	var p := World.local_player
	if p != null:
		p.global_position = pos
		p.velocity = Vector3.ZERO


# --- messages and windows (server -> one client) -------------------------------

func send_say(p: Player, text: String, color: Color) -> void:
	if is_remote(p):
		_s_say.rpc_id(peer_of(p), text, color)


@rpc("authority", "reliable")
func _s_say(text: String, color: Color) -> void:
	World.log_message.emit(text, color)


## Server: a World signal meant for one player's HUD (loot, trade, shop...).
## Objects travel as ids; corpse contents and shop stock ride along so the
## client's windows can draw them.
func send_ui(p: Player, sig: StringName, args: Array) -> void:
	var peer := peer_of(p)
	if peer == 0:
		return
	_send_self(peer)  # inventory and the like first, so the window draws current state
	var packed: Array = []
	var extra := {}
	for a: Variant in args:
		if a is Corpse:
			packed.append({"obj": (a as Corpse).object_id})
			extra["corpse"] = {"id": (a as Corpse).object_id, "entries": (a as Corpse).entries, "coin": (a as Corpse).coin}
		elif a is Entity:
			packed.append({"obj": (a as Entity).entity_id})
		else:
			packed.append(a)
	var npc := World.get_object(p.service_npc_id) as Npc
	if npc != null:
		extra["stock"] = {"npc": npc.npc_id, "items": World.merchant_stock.get(npc.npc_id, {})}
	_s_ui.rpc_id(peer, sig, packed, extra)


@rpc("authority", "reliable")
func _s_ui(sig: StringName, packed: Array, extra: Dictionary) -> void:
	if extra.has("corpse"):
		var c := World.get_object(int(extra["corpse"]["id"])) as Corpse
		if c != null:
			c.entries = extra["corpse"]["entries"]
			c.coin = int(extra["corpse"]["coin"])
	if extra.has("stock"):
		World.merchant_stock[extra["stock"]["npc"]] = extra["stock"]["items"]
	var args: Array = []
	for a: Variant in packed:
		args.append(World.get_object(int(a["obj"])) if a is Dictionary and (a as Dictionary).has("obj") else a)
	if sig == &"loot_closed" and args[0] == null and packed[0] is Dictionary:
		return  # the corpse is already gone here, and nothing of it is open
	World.emit_signal.callv([sig] + args)


## Server: the player's camp finished: save, leave the world, and go back to
## character select (still logged in).
func camped_out(p: Player) -> void:
	var peer := peer_of(p)
	if peer == 0:
		return
	_take_out(peer)
	_s_camped.rpc_id(peer)
	_send_characters(peer)


@rpc("authority", "reliable")
func _s_camped() -> void:
	my_player_id = -1
	camp_done.emit()


## Server: everyone moved to another zone (until each zone can run on its own).
func send_zone(p: Player, zone_id: String) -> void:
	var peer := peer_of(p)
	if peer == 0:
		return
	_known[peer] = {p.entity_id: true}
	_sent.erase(peer)
	var seq := int(_teleport_seq.get(p.entity_id, 0)) + 1
	_teleport_seq[p.entity_id] = seq
	_s_zone.rpc_id(peer, zone_id, p.global_position, seq)


@rpc("authority", "reliable")
func _s_zone(zone_id: String, pos: Vector3, seq: int) -> void:
	_seq = seq
	zone_moved.emit(zone_id, pos)


# --- animations and looks (server -> everyone who can see it) ------------------

func broadcast_anim(e: Entity, action: String) -> void:
	if mode != "server":
		return
	for peer: int in _known:
		if _known[peer].has(e.entity_id) or _peer_player[peer] == e.entity_id:
			_s_anim.rpc_id(peer, e.entity_id, action)


@rpc("authority", "reliable")
func _s_anim(id: int, action: String) -> void:
	var e := World.get_object(id) as Entity
	if e != null:
		e.animate(action)


## A spell landing, for everyone who can see the caster or the target.
func broadcast_fx(from: Entity, to: Entity, spell_id: String) -> void:
	if mode != "server" or from == null or to == null:
		return
	for peer: int in _known:
		var sees: Dictionary = _known[peer]
		if sees.has(to.entity_id) or sees.has(from.entity_id) or _peer_player[peer] == to.entity_id or _peer_player[peer] == from.entity_id:
			_s_fx.rpc_id(peer, from.entity_id, to.entity_id, spell_id)


@rpc("authority", "reliable")
func _s_fx(from_id: int, to_id: int, spell_id: String) -> void:
	World.spell_fx.emit(World.get_object(from_id) as Entity, World.get_object(to_id) as Entity, spell_id)


## A ranged attack, for everyone who can see the shooter or the target.
func broadcast_shot(from: Entity, to: Entity, projectile: String) -> void:
	if mode != "server":
		return
	for peer: int in _known:
		var sees: Dictionary = _known[peer]
		if sees.has(from.entity_id) or sees.has(to.entity_id) or _peer_player[peer] == from.entity_id:
			_s_shot.rpc_id(peer, from.entity_id, to.entity_id, projectile)


@rpc("authority", "reliable")
func _s_shot(from_id: int, to_id: int, projectile: String) -> void:
	var from := World.get_object(from_id) as Entity
	var to := World.get_object(to_id) as Entity
	if from != null and to != null:
		World.shot_fired.emit(from, to, projectile)


func broadcast_look(e: Entity) -> void:
	if mode != "server":
		return
	for peer: int in _known:
		if _known[peer].has(e.entity_id) or _peer_player[peer] == e.entity_id:
			_s_look.rpc_id(peer, e.entity_id, e.look)


@rpc("authority", "reliable")
func _s_look(id: int, look: Dictionary) -> void:
	var e := World.get_object(id) as Entity
	if e != null and e.visual is CharacterModel:
		e.look = look
		(e.visual as CharacterModel).set_tiers(look.get("tiers", {}))
		(e.visual as CharacterModel).set_weapon(str(look.get("weapon", "")))
		(e.visual as CharacterModel).set_offhand(str(look.get("offhand", "")))
		if look.has("worn"):
			(e.visual as CharacterModel).set_worn(look["worn"])


# --- replication (server -> clients) --------------------------------------------

func _physics_process(delta: float) -> void:
	if mode == "server":
		_serve(delta)
	elif mode == "client" and World.local_player != null:
		send_move(World.local_player, delta)
		if not _pending_spawns.is_empty() and World.zone != null and World.zone.is_inside_tree():
			var list := _pending_spawns
			_pending_spawns = []
			_s_spawn(list)


func _serve(delta: float) -> void:
	_snap_timer += delta
	_self_timer += delta
	_save_timer += delta
	_keyframe_timer += delta
	if _snap_timer >= 1.0 / SNAPSHOT_HZ:
		_snap_timer = 0.0
		_keyframe = _keyframe_timer >= KEYFRAME_SECONDS
		if _keyframe:
			_keyframe_timer = 0.0
		for peer: int in _peer_player:
			_replicate(peer)
	if _self_timer >= 1.0 / SELF_HZ:
		_self_timer = 0.0
		for peer: int in _peer_player:
			_send_self(peer)
	if _save_timer >= SAVE_SECONDS:
		_save_timer = 0.0
		for peer: int in _peer_player:
			save_player(player_of_peer(peer))


## Spawns what the client hasn't seen, despawns what's gone, then sends the
## position and health of whatever changed (everything, once a second).
func _replicate(peer: int) -> void:
	var own := int(_peer_player[peer])
	var own_zone := World.zone_of(World.get_object(own))
	var known: Dictionary = _known[peer]
	var sent: Dictionary = _sent.get_or_add(peer, {})
	var seen := {}
	var spawns: Array = []
	var states := PackedFloat32Array()
	for id: int in World.objects:
		var obj := World.get_object(id)
		if obj == null or not obj.is_inside_tree() or not (obj is Entity or obj is Corpse or obj is GroundItem) or World.zone_of(obj) != own_zone:
			continue  # only what's in this player's zone
		seen[id] = true
		if not known.has(id):
			known[id] = true
			spawns.append(_spawn_info(obj))
		if obj is Entity and id != own:
			var e := obj as Entity
			var p := e.global_position
			var flags := (1 if e.dead else 0) | (2 if e.sitting else 0) | (4 if not e.cast.is_empty() else 0) | (8 if e.hidden else 0)
			var row := PackedFloat32Array([id, p.x, p.y, p.z, e.rotation.y, e.hp, e.max_hp, e.level, flags])
			if _keyframe or sent.get(id) != row:
				sent[id] = row
				states.append_array(row)
	var gone: Array = []
	for id: int in known.keys():
		if not seen.has(id):
			known.erase(id)
			sent.erase(id)
			gone.append(id)
	if not gone.is_empty():
		_s_despawn.rpc_id(peer, gone)
	if not spawns.is_empty():
		_s_spawn.rpc_id(peer, spawns)
	var chunk := STATE_STRIDE * ROWS_PER_PACKET
	for i in range(0, states.size(), chunk):
		_s_state.rpc_id(peer, states.slice(i, i + chunk))


func _spawn_info(obj: Node3D) -> Dictionary:
	var info := {"id": -1, "pos": obj.global_position, "rot": obj.rotation.y}
	if obj is Corpse:
		var c := obj as Corpse
		info.merge({"id": c.object_id, "kind": "corpse", "name": c.display_name, "look": c.look, "owner": c.owner_name}, true)
		return info
	if obj is GroundItem:
		info.merge({"id": (obj as GroundItem).object_id, "kind": "ground", "entry": (obj as GroundItem).entry}, true)
		return info
	var e := obj as Entity
	info.merge({"id": e.entity_id, "name": e.display_name, "level": e.level, "look": e.look, "hp": e.hp, "max_hp": e.max_hp}, true)
	if e is Player:
		info.merge({"kind": "player", "class": (e as Player).char_class}, true)
	elif e is Mob:
		info.merge({"kind": "mob", "mob_id": (e as Mob).mob_id}, true)
	elif e is Npc:
		info.merge({"kind": "npc", "npc_id": (e as Npc).npc_id}, true)
	return info


@rpc("authority", "reliable")
func _s_spawn(list: Array) -> void:
	if World.zone == null or not World.zone.is_inside_tree():
		_pending_spawns.append_array(list)  # placed once the new zone is up
		return
	for info: Dictionary in list:
		if World.get_object(int(info["id"])) != null:
			continue
		var node: Node3D
		match str(info["kind"]):
			"corpse":
				var c := Corpse.new()
				c.setup("", info["look"], [], 0, 1e9, str(info["owner"]))
				c.display_name = str(info["name"])
				c.object_id = int(info["id"])
				node = c
			"ground":
				var g := GroundItem.new()
				g.entry = info["entry"]
				g.object_id = int(info["id"])
				node = g
			"player":
				var p := Player.new()
				p.setup_remote(info)
				node = p
			"mob":
				var m := Mob.new()
				m.setup_remote(info)
				node = m
			"npc":
				var n := Npc.new()
				n.setup(str(info["npc_id"]), str(info["name"]))
				n.entity_id = int(info["id"])
				n.hp = int(info["hp"])
				node = n
		if node == null:
			continue
		node.position = info["pos"]
		node.rotation.y = float(info["rot"])
		World.zone.add_child(node)
		if node is Entity:
			(node as Entity).net_pos = info["pos"]
			(node as Entity).net_rot = float(info["rot"])


@rpc("authority", "reliable")
func _s_despawn(ids: Array) -> void:
	for id: int in ids:
		var obj := World.get_object(id)
		if obj != null and obj != World.local_player:
			if obj is Corpse:
				World.loot_closed.emit(obj)
			obj.queue_free()


@rpc("authority", "unreliable_ordered", "call_remote", CH_STATE)
func _s_state(s: PackedFloat32Array) -> void:
	for i in range(0, s.size() - STATE_STRIDE + 1, STATE_STRIDE):
		var e := World.get_object(int(s[i])) as Entity
		if e == null or e == World.local_player:
			continue
		e.net_pos = Vector3(s[i + 1], s[i + 2], s[i + 3])
		e.net_rot = s[i + 4]
		e.hp = int(s[i + 5])
		e.max_hp = int(s[i + 6])
		e.level = int(s[i + 7])
		var flags := int(s[i + 8])
		e.set_net_flags(flags & 1 != 0, flags & 2 != 0, flags & 4 != 0, flags & 8 != 0)


# --- the player's own state (server -> its client) ------------------------------

func _send_self(peer: int) -> void:
	var p := player_of_peer(peer)
	if p == null:
		return
	var t := -1
	if is_instance_valid(p.target):
		t = (p.target as Entity).entity_id if p.target is Entity else (p.target as Corpse).object_id
	var d := {
		"level": p.level, "xp": p.xp, "coin": p.coin, "hp": p.hp, "max_hp": p.max_hp, "mana": p.mana,
		"max_mana": p.max_mana, "ac": p.ac, "dmg_min": p.dmg_min, "dmg_max": p.dmg_max,
		"attack_delay": p.attack_delay, "attack_verb": p.attack_verb, "attributes": p.attributes,
		"pack": p.pack.to_save(), "cursor": p.cursor, "equipment": p.equipment, "spells": p.spells, "quests": p.quests,
		"factions": p.factions, "bank": p.bank, "bank_coin": p.bank_coin,
		"cast": p.cast, "cooldowns": p.cooldowns, "buffs": p.buffs, "dead": p.dead, "sitting": p.sitting,
		"auto_attack": p.auto_attack, "target": t, "trade_npc_id": p.trade_npc_id, "trade_items": p.trade_items,
		"service_npc_id": p.service_npc_id, "service": p.service, "camp_left": p.camp_left, "look": p.look,
		"root_left": p.root_left, "dots": p.dots, "stamina": p.stamina, "max_stamina": p.max_stamina, "sprinting": p.sprinting, "threatened": p.threatened, "hidden": p.hidden, "sneaking": p.sneaking, "snare_left": p.snare_left,
		"group": p.group, "skills": p.skills,
	}
	_s_self.rpc_id(peer, d)


@rpc("authority", "reliable")
func _s_self(d: Dictionary) -> void:
	var p := World.local_player
	if p == null:
		return
	p.apply_self(d)
