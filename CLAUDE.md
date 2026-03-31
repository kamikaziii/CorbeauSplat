# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CorbeauSplat** (v0.9) — macOS-focused Python GUI application for end-to-end 3D Gaussian Splatting. Converts video/images into trained splat models through COLMAP reconstruction, Brush training, and SuperSplat visualization. Built with PyQt6, targets Apple Silicon (MPS) with CPU/CUDA fallback.

## Running the Application

```bash
# GUI (default when no args)
python3 main.py

# CLI modes
python3 main.py --input <path> --output <path>              # COLMAP pipeline
python3 main.py --train --input <project> --output <out>     # Brush training
python3 main.py --predict --input <image> --output <out>     # Sharp prediction
python3 main.py --view --input <ply_file>                    # SuperSplat viewer
```

Full CLI reference in `CLI.md`.

**Dependencies**: `pip install -r requirements.txt` (PyQt6, requests, numpy<2, send2trash, realesrgan stack). External binaries (COLMAP, Brush, FFmpeg) resolved via `engines/` directory or system PATH — see `app/core/system.py:resolve_binary()`.

**No test suite exists.** Verify imports with `python3 verify_imports.py`.

## Architecture

### Two-layer design: headless engines + PyQt6 GUI

**Engines** (`app/core/`) run external tools via subprocess. Each engine extends `BaseEngine` which provides:
- `_execute_command()` — template method for process execution with cancellation support
- `IProcessRunner` / `SubprocessRunner` — injectable process abstraction (DIP for testability)
- Path validation via `validate_path()` (traversal prevention)
- Process group management (`os.setsid` + `os.killpg`) for clean subprocess tree termination

**GUI** (`app/gui/`) uses tab-based QMainWindow. Each feature is a tab (`app/gui/tabs/`) with a corresponding QThread worker (`app/gui/workers.py`) that delegates to an engine. Workers extend `BaseWorker` with standardized signals: `log_signal`, `progress_signal`, `status_signal`, `finished_signal`.

### Key modules

| Module | Role |
|--------|------|
| `app/core/engine.py` | ColmapEngine — orchestrates feature extraction → matching → mapping → undistortion |
| `app/core/brush_engine.py` | BrushEngine — Gaussian Splat training via Brush binary |
| `app/core/superplat_engine.py` | SuperSplatEngine — launches web viewer + CORS data server |
| `app/core/sharp_engine.py` | SharpEngine — Apple ML single-image-to-3D |
| `app/core/i18n.py` | LanguageManager singleton — observer pattern, 9 languages in `assets/locales/` |
| `app/core/system.py` | Platform detection, binary resolution (`engines/` dir → system PATH), Apple Silicon P-core threading |
| `app/gui/managers.py` | SessionManager (debounced JSON persistence to `config.json`), AppLifecycle |
| `app/gui/styles.py` | Dark theme stylesheet |

### Data flow

1. User configures in tabs → tab emits signal
2. MainWindow creates a Worker (QThread) with parameters
3. Worker calls corresponding Engine method
4. Engine spawns subprocess via `_execute_command()` / `SubprocessRunner`
5. Output streams back through signals → LogsTab displays in real time
6. Worker emits `finished_signal(success, message)`

### Session persistence

`SessionManager` saves all tab state to `config.json` at project root with 1.5s debounce. Each tab implements `get_state()`/`set_state()` or `get_params()`/`set_params()`.

## Conventions

- **Language**: Code comments and internal strings are in French; UI strings use i18n keys via `tr("key")` from `app/core/i18n.py`
- **Default language**: French (`fr`). Translations in `assets/locales/*.json`
- **New UI text**: Add the key to all 9 locale JSON files
- **New features**: Create an engine in `app/core/`, a tab in `app/gui/tabs/`, and a worker in `app/gui/workers.py`. Wire through `main_window.py`
- **Binary resolution**: External tools go in `engines/` directory. `resolve_binary()` checks there first, then system PATH
- **Version**: Single source of truth in `app/__init__.py`
