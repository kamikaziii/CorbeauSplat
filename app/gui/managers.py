import os
import sys
import json
import subprocess
from pathlib import Path
from app.core.system import resolve_project_root
from app.core.params import ColmapParams
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

class SessionManager:
    """[AUDIT] SOLID-SRP : Gestion responsable uniquement de la persistance JSON"""
    def __init__(self, main_window):
        self.mw = main_window
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)

    def get_session_file(self) -> Path:
        return resolve_project_root() / "config.json"

    def save(self, immediate=False):
        """[AUDIT] Optimisation Perf-IO : Debounce de la sauvegarde JSON pour ne pas geler l'UI"""
        if immediate:
            self._save_timer.stop()
            self._do_save()
        else:
            self._save_timer.start(1500) # Debounce 1.5s

    def _do_save(self):
        state = {
            "language": self.mw.config_tab.combo_lang.currentData(),
        }
        
        tab_mapping = {
            "config": self.mw.config_tab,
            "colmap_params": self.mw.params_tab,
            "brush_params": self.mw.brush_tab,
            "sharp_params": self.mw.sharp_tab,
            "upscale_params": self.mw.upscale_tab,
            "extractor_360_params": self.mw.extractor_360_tab,
            "four_dgs_params": self.mw.four_dgs_tab,
            "superplat_params": self.mw.superplat_tab,
        }
        
        for key, tab in tab_mapping.items():
            if hasattr(tab, 'get_state'):
                state[key] = tab.get_state()
            elif hasattr(tab, 'get_params'):
                state[key] = tab.get_params()
                if hasattr(state[key], 'to_dict'):
                    state[key] = state[key].to_dict()

        try:
            with open(self.get_session_file(), 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Erreur sauvegarde session: {e}")

    def load(self):
        session_file = self.get_session_file()
        if not session_file.exists():
            return
            
        try:
            with open(session_file, 'r') as f:
                state = json.load(f)
                
            tab_mapping = {
                "config": self.mw.config_tab,
                "colmap_params": self.mw.params_tab,
                "brush_params": self.mw.brush_tab,
                "sharp_params": self.mw.sharp_tab,
                "upscale_params": self.mw.upscale_tab,
                "extractor_360_params": self.mw.extractor_360_tab,
                "four_dgs_params": self.mw.four_dgs_tab,
                "superplat_params": self.mw.superplat_tab,
            }
            
            for key, tab in tab_mapping.items():
                if key in state:
                    if hasattr(tab, 'set_state'):
                        tab.set_state(state[key])
                    elif hasattr(tab, 'set_params'):
                        if key == "colmap_params":
                            tab.set_params(ColmapParams.from_dict(state[key]))
                        else:
                            tab.set_params(state[key])
        except Exception as e:
            print(f"Erreur chargement session: {e}")


class AppLifecycle:
    """[AUDIT] SOLID-SRP : Responsable du redemarrage OS et processus externes"""
    @staticmethod
    def restart(save_callback=None):
        if save_callback:
            try: save_callback()
            except Exception as e: print(f"Error saving session before restart: {e}")

        root_dir = resolve_project_root()
        python = sys.executable
        main_py = root_dir / "main.py"

        engines_dir = root_dir / "engines"
        needs_setup = any([
            not (engines_dir / "brush").exists() and (engines_dir / "brush.version").exists() is False,
            not (engines_dir / "brush").exists(),
        ])

        if needs_setup and sys.platform != "win32":
            print("Reinstall detected: running setup before relaunch...")
            extra_argv = [a for a in sys.argv[1:] if a not in ("--gui",)]
            main_args = " ".join(f'"{a}"' for a in extra_argv)
            cmd = (
                f'sleep 1 && '
                f'"{python}" -m app.scripts.setup_dependencies --startup && '
                f'"{python}" "{main_py}" {main_args}'
            )
            subprocess.Popen(cmd, shell=True, cwd=str(root_dir), start_new_session=True)
            QApplication.quit()
            sys.exit(0)

        # Relance normale
        args = [python, str(main_py)] + sys.argv[1:]
        print(f"Relaunching via execv: {args}")

        if sys.platform != "win32":
            try:
                os.execv(python, args)
            except Exception as e:
                print(f"execv failed: {e}. Falling back to Popen.")

        kwargs = {}
        if sys.platform != "win32":
            kwargs["start_new_session"] = True

        subprocess.Popen(args, cwd=str(root_dir), **kwargs)
        QApplication.quit()
        sys.exit(0)
        
    @staticmethod
    def reset_factory(deep=False):
        QApplication.quit()
        
        root_dir = resolve_project_root()
        run_cmd = root_dir / "run.command"
        
        to_delete = [
            root_dir / ".venv",
            root_dir / ".venv_sharp",
            root_dir / ".venv_360"
        ]
        
        if deep:
            to_delete.append(root_dir / "engines")
            to_delete.append(root_dir / "config.json")
            for p in root_dir.glob("config.sync-conflict-*"):
                to_delete.append(p)
        
        delete_cmd = " ".join([f'"{str(p)}"' for p in to_delete])
        
        print(f"Reset Factory {'DEEP' if deep else 'LIGHT'} initie sur: {root_dir}")
        print(f"Commande relance: {run_cmd}")
        
        cmd = f"sleep 2 && rm -rf {delete_cmd} && \"{run_cmd}\" &"
        subprocess.Popen(cmd, shell=True, cwd=str(root_dir))
        sys.exit(0)
