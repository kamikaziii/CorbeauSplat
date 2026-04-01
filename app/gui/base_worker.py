from PyQt6.QtCore import QThread, pyqtSignal
import subprocess
import os
from app.core.i18n import tr

class BaseWorker(QThread):
    """Classe de base pour les workers avec signaux standardisés"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.process = None
        
    def stop(self):
        """Arrêt générique du thread et du processus associé"""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                # On ne fait pas wait() ici car on veut que l'interface reste réactive
                # Le thread se terminera de lui-même quand run() s'arrêtera
            except Exception:
                pass
        self.requestInterruption()
        
    def run_subprocess(self, cmd, cwd=None, env=None, log_prefix=""):
        """Méthode utilitaire pour exécuter un sous-processus et capturer ses logs"""
        try:
            # Fusionner l'env
            actual_env = os.environ.copy()
            if env:
                actual_env.update(env)
            
            self.log_signal.emit(tr("msg_exec_cmd", ' '.join(cmd)))
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                cwd=cwd,
                env=actual_env,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in self.process.stdout:
                if not self.is_running or self.isInterruptionRequested():
                    self.log_signal.emit(tr("msg_user_stopped"))
                    self.process.terminate()
                    break
                
                clean_line = line.strip()
                if clean_line:
                    self.log_signal.emit(f"{log_prefix}{clean_line}")
                    self.parse_line(clean_line)
                    
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            return self.process.returncode == 0
        except Exception as e:
            self.log_signal.emit(tr("err_critical_process", str(e)))
            import traceback
            self.log_signal.emit(traceback.format_exc())
            return False

    def parse_line(self, line):
        """A surcharger pour extraire la progression ou des infos spécifiques"""


class InstallWorker(QThread):
    """Generic worker for blocking install/uninstall/download operations."""
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, fn, success_msg="", parent=None):
        super().__init__(parent)
        self._fn = fn
        self._success_msg = success_msg

    def run(self):
        try:
            result = self._fn()
            self.finished_signal.emit(result is not False, self._success_msg)
        except Exception as e:
            self.finished_signal.emit(False, str(e))
