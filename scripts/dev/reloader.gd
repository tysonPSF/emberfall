extends CanvasLayer
## Dev convenience: notices when scripts, data or art change on disk and
## offers a reload. F9 saves, re-imports assets, and restarts the game with
## --resume so you land back where you were, skipping the character screen.
## Only runs from the project folder, never in an exported build.

const WATCH := ["res://scripts", "res://data", "res://assets/props", "res://assets/creatures"]
const EXTENSIONS := ["gd", "gdshader", "json", "glb", "gltf", "png"]
const SCAN_SECONDS := 2.0

var save_game: Callable  # main's save, called before restarting

var _stamps: Dictionary = {}  # path -> modified time when the game started
var _timer := 0.0
## The scan looks at some 1,600 files, over 100 ms on a Mac: on the main thread
## it froze the game every SCAN_SECONDS (a stutter-step while running), so it
## runs on a worker and only its answer comes back.
var _task := -1
var _changed := false
var _notice: Label
var _reloading := false


func _ready() -> void:
	add_to_group("reloader")  # the Esc menu offers a reload button when this exists
	layer = 100
	_notice = UIKit.label("Update ready  -  press F9 to reload", 16, UIKit.GOLD)
	UIKit.place(_notice, Vector2(0.5, 0), Vector2(0, 14))
	_notice.visible = false
	add_child(_notice)
	_stamps = _scan()


func _process(delta: float) -> void:
	if _notice.visible or _reloading:
		return
	if _task >= 0:
		if not WorkerThreadPool.is_task_completed(_task):
			return
		WorkerThreadPool.wait_for_task_completion(_task)
		_task = -1
		if _changed:
			_notice.visible = true
			return
	_timer += delta
	if _timer < SCAN_SECONDS:
		return
	_timer = 0.0
	_task = WorkerThreadPool.add_task(func() -> void: _changed = _scan() != _stamps)


func _exit_tree() -> void:
	if _task >= 0:
		WorkerThreadPool.wait_for_task_completion(_task)
		_task = -1


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("reload") and not _reloading:
		get_viewport().set_input_as_handled()
		reload()


func reload() -> void:
	if _reloading:
		return
	_reloading = true
	_notice.text = "Reloading..."
	_notice.visible = true
	await get_tree().process_frame
	await get_tree().process_frame  # let the notice draw before the import blocks
	var resume := false
	if save_game.is_valid():
		resume = bool(save_game.call())
	var exe := OS.get_executable_path()
	var project := ProjectSettings.globalize_path("res://")
	OS.execute(exe, ["--headless", "--path", project, "--import"])
	var args := ["--path", project]
	if resume:
		args.append_array(["--", "--resume"])
	OS.create_process(exe, args)
	get_tree().quit()


func _scan() -> Dictionary:
	var out := {}
	for dir: String in WATCH:
		_scan_dir(dir, out)
	return out


func _scan_dir(dir: String, out: Dictionary) -> void:
	for f in DirAccess.get_files_at(dir):
		if f.get_extension() in EXTENSIONS:
			var path := dir.path_join(f)
			out[path] = FileAccess.get_modified_time(path)
	for sub in DirAccess.get_directories_at(dir):
		_scan_dir(dir.path_join(sub), out)
