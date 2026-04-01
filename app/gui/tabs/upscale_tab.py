
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QGroupBox, QFormLayout,
    QCheckBox, QComboBox, QSpinBox, QMessageBox, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt
from app.core.i18n import tr, add_language_observer
from app.core.upscale_engine import UpscaleEngine
from app.gui.base_worker import InstallWorker
from app.scripts.setup_dependencies import install_upscale, uninstall_upscale, resolve_project_root

class UpscaleTab(QWidget):
    """
    Tab for Upscale Configuration & Management.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = UpscaleEngine()
        self.init_ui()
        add_language_observer(self.retranslate_ui)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        self.lbl_title = QLabel(tr("upscale_title"))
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(self.lbl_title)
        
        self.lbl_desc = QLabel(tr("upscale_desc"))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #aaa; margin-bottom: 5px;")
        layout.addWidget(self.lbl_desc)

        # Activation / Installation
        self.chk_activate = QCheckBox(tr("upscale_activate"))
        self.chk_activate.setStyleSheet("font-weight: bold; padding: 5px;")
        self.chk_activate.clicked.connect(self.on_toggle_activation)
        layout.addWidget(self.chk_activate)

        # Settings Group
        self.settings_group = QGroupBox(tr("upscale_group_settings"))
        form_layout = QFormLayout()
        
        # Model Selection
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "RealESRGAN_x4plus", 
            "RealESRNet_x4plus",
            "RealESRGAN_x4plus_anime_6B"
        ])
        self.lbl_model = QLabel(tr("upscale_lbl_model"))
        form_layout.addRow(self.lbl_model, self.model_combo)
        
        # Model Description
        self.model_desc = QLabel("")
        self.model_desc.setStyleSheet("color: #888; font-style: italic; margin-bottom: 5px;")
        self.model_desc.setWordWrap(True)
        form_layout.addRow("", self.model_desc)
        
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        
        # Status Label
        self.status_label = QLabel("")
        self.lbl_status = QLabel(tr("upscale_lbl_status"))
        form_layout.addRow(self.lbl_status, self.status_label)
        
        # Download Button (Visible only if missing)
        self.btn_download = QPushButton(tr("upscale_btn_download"))
        self.btn_download.clicked.connect(self.download_current_model)
        self.btn_download.setVisible(False)
        form_layout.addRow("", self.btn_download)
        self.scale_combo = QComboBox()
        self.scale_combo.addItems([tr("upscale_scale_x4"), tr("upscale_scale_x2"), tr("upscale_scale_x1")])
        self.scale_combo.setCurrentIndex(2) # Default to x1 (Enhance only)
        self.scale_combo.setToolTip(tr("upscale_tip_scale"))
        self.lbl_scale = QLabel(tr("upscale_lbl_scale"))
        form_layout.addRow(self.lbl_scale, self.scale_combo)

        # Performance Profile
        self.profile_combo = QComboBox()
        self.profile_combo.addItems([
            tr("upscale_profile_safe"),
            tr("upscale_profile_quality"),
            tr("upscale_profile_speed"),
            tr("upscale_profile_ultimate"),
            tr("upscale_profile_custom")
        ])
        self.profile_combo.setToolTip(tr("upscale_tip_profile"))
        self.lbl_profile = QLabel(tr("upscale_lbl_profile"))
        form_layout.addRow(self.lbl_profile, self.profile_combo)
        
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        
        # Tile Size (Memory management)
        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(0, 4096)
        self.tile_spin.setValue(512) # Default to 512 for safety on Air/8GB
        self.tile_spin.setSingleStep(128)
        self.tile_spin.setSuffix(" px")
        self.tile_spin.setToolTip(tr("upscale_tip_tile"))
        self.tile_spin.valueChanged.connect(self.on_manual_change)
        self.lbl_tile = QLabel(tr("upscale_lbl_tile"))
        form_layout.addRow(self.lbl_tile, self.tile_spin)
        
        # Face Enhance Option
        self.face_enhance = QCheckBox(tr("upscale_check_face"))
        self.face_enhance.setToolTip(tr("upscale_tip_face"))
        form_layout.addRow("", self.face_enhance)

        # FP16 Option
        self.fp16_check = QCheckBox(tr("upscale_lbl_fp16"))
        self.fp16_check.setToolTip(tr("upscale_tip_fp16"))
        self.fp16_check.setChecked(True) # Default true for mac
        self.fp16_check.toggled.connect(self.on_manual_change)
        self.lbl_fp16 = QLabel(tr("upscale_lbl_fp16"))
        form_layout.addRow(self.lbl_fp16, self.fp16_check)
        
        self.settings_group.setLayout(form_layout)
        layout.addWidget(self.settings_group)
        
        layout.addStretch()
        
        # Initial State Check
        # Always enabled now
        self.settings_group.setEnabled(True)
        # Check dependencies just for status label, but don't block
        if not self.engine.is_installed():
            # Should behave if setup_dependencies ran, but show warning if not
            # Should behave if setup_dependencies ran, but show warning if not
            self.status_label.setText(tr("upscale_status_deps_missing"))
            # self.settings_group.setEnabled(False) # Let user try anyway/debug

        self.on_model_changed()
        
        self._updating_profile = False

    def on_profile_changed(self):
        if self._updating_profile: return
        
        idx = self.profile_combo.currentIndex()
        self._updating_profile = True
        
        if idx == 0: # Safe
            self.tile_spin.setValue(512)
            self.fp16_check.setChecked(True)
        elif idx == 1: # Quality Max
            self.tile_spin.setValue(512)
            self.fp16_check.setChecked(False)
        elif idx == 2: # Speed (High VRAM)
            self.tile_spin.setValue(0)
            self.fp16_check.setChecked(True)
        elif idx == 3: # Ultimate
            self.tile_spin.setValue(0)
            self.fp16_check.setChecked(False)
            
        self._updating_profile = False

    def on_manual_change(self):
        if self._updating_profile: return
        # Switch to Custom if parameters don't match current profile
        # Simple approach: just switch to Custom whenever user touches controls
        self.profile_combo.setCurrentIndex(4) # Custom

    def on_model_changed(self):
        self.update_model_desc()
        self.check_model_status()

    def update_model_desc(self):
        txt = self.model_combo.currentText()
        desc = ""
        if "x4plus_anime" in txt:
            desc = tr("upscale_desc_anime")
        elif "x4plus" in txt:
            desc = tr("upscale_desc_x4plus")
        elif "x4net" in txt:
            desc = tr("upscale_desc_x4net")
        self.model_desc.setText(desc)

    def check_model_status(self):
        if not self.engine.is_installed():
            self.status_label.setText(tr("upscale_status_not_installed"))
            return
            
        model = self.model_combo.currentText()
        if self.engine.check_model_availability(model):
            self.status_label.setText(tr("upscale_status_available"))
            self.status_label.setStyleSheet("color: green;")
            self.btn_download.setVisible(False)
        else:
            self.status_label.setText(tr("upscale_status_missing_model"))
            self.status_label.setStyleSheet("color: orange;")
            self.btn_download.setVisible(True)

    def download_current_model(self):
        model = self.model_combo.currentText()
        self.btn_download.setEnabled(False)
        self._progress = QProgressDialog(tr("upscale_msg_downloading", model), None, 0, 0, self)
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.show()

        self._download_worker = InstallWorker(
            lambda: self.engine.download_model(model),
            tr("upscale_msg_success_download")
        )
        self._download_worker.finished_signal.connect(self._on_download_finished)
        self._download_worker.start()

    def _on_download_finished(self, success, message):
        self._progress.close()
        self.btn_download.setEnabled(True)
        if success:
            QMessageBox.information(self, tr("msg_success"), message)
            self.check_model_status()
        else:
            QMessageBox.critical(self, tr("msg_error"), tr("upscale_msg_err_download"))

    def on_toggle_activation(self):
        if self.chk_activate.isChecked():
            # Activation requested
            if not self.engine.is_installed():
                reply = QMessageBox.question(
                    self,
                    tr("install_required"),
                    tr("upscale_install_confirm"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                     self.install_deps()
                else:
                    self.chk_activate.setChecked(False)
            else:
                self.settings_group.setEnabled(True)
        else:
            # Deactivation requested
            reply = QMessageBox.question(
                self,
                tr("upscale_deactivate_title"),
                tr("upscale_deactivate_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.uninstall_deps()
            else:
                self.settings_group.setEnabled(False)

    def install_deps(self):
        self.chk_activate.setEnabled(False)
        self._progress = QProgressDialog(tr("upscale_msg_downloading", "Real-ESRGAN"), None, 0, 0, self)
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.show()

        self._install_worker = InstallWorker(install_upscale, tr("upscale_msg_installed"))
        self._install_worker.finished_signal.connect(self._on_install_finished)
        self._install_worker.start()

    def _on_install_finished(self, success, message):
        self._progress.close()
        self.chk_activate.setEnabled(True)
        if success:
            QMessageBox.information(self, tr("msg_success"), message)
            self.settings_group.setEnabled(True)
            self.check_model_status()
        else:
            QMessageBox.critical(self, tr("msg_error"), tr("upscale_msg_install_err"))
            self.chk_activate.setChecked(False)
            self.settings_group.setEnabled(False)

    def uninstall_deps(self):
        self.chk_activate.setEnabled(False)
        self._progress = QProgressDialog(tr("upscale_deactivate_title"), None, 0, 0, self)
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.show()

        self._uninstall_worker = InstallWorker(uninstall_upscale, tr("upscale_msg_uninstalled"))
        self._uninstall_worker.finished_signal.connect(self._on_uninstall_finished)
        self._uninstall_worker.start()

    def _on_uninstall_finished(self, success, message):
        self._progress.close()
        self.chk_activate.setEnabled(True)
        if success:
            QMessageBox.information(self, tr("msg_success"), message)
            self.settings_group.setEnabled(False)
            self.status_label.setText(tr("upscale_status_not_installed"))
        else:
            QMessageBox.critical(self, tr("msg_error"), message)
            self.chk_activate.setChecked(True)
            self.settings_group.setEnabled(True)

    def get_params(self):
        return {
            "enabled": self.chk_activate.isChecked(),
            "model_name": self.model_combo.currentText(),
            "tile": self.tile_spin.value(),
            "target_scale": self.get_scale_factor(),
            "face_enhance": self.face_enhance.isChecked(),
            "fp16": self.fp16_check.isChecked()
        }
        
    def get_scale_factor(self):
        idx = self.scale_combo.currentIndex()
        if idx == 1: return 2
        if idx == 2: return 1
        return 4

    def set_params(self, params):
        if not params: return
        if "enabled" in params:
            self.chk_activate.setChecked(params["enabled"])
            self.settings_group.setEnabled(params["enabled"])
        if "tile" in params: self.tile_spin.setValue(params["tile"])
        if "fp16" in params: self.fp16_check.setChecked(params["fp16"])
        if "model_name" in params: self.model_combo.setCurrentText(params["model_name"])

    def get_state(self):
        return self.get_params()
        
    def set_state(self, state):
        self.set_params(state)

    def retranslate_ui(self):
        """Update texts when language changes"""
        self.lbl_title.setText(tr("upscale_title"))
        self.lbl_desc.setText(tr("upscale_desc"))
        self.chk_activate.setText(tr("upscale_activate"))
        self.settings_group.setTitle(tr("upscale_group_settings"))
        self.lbl_model.setText(tr("upscale_lbl_model"))
        self.lbl_status.setText(tr("upscale_lbl_status"))
        self.btn_download.setText(tr("upscale_btn_download"))
        self.lbl_scale.setText(tr("upscale_lbl_scale"))
        self.scale_combo.setToolTip(tr("upscale_tip_scale"))
        self.scale_combo.setItemText(0, tr("upscale_scale_x4"))
        self.scale_combo.setItemText(1, tr("upscale_scale_x2"))
        self.scale_combo.setItemText(2, tr("upscale_scale_x1"))
        
        self.lbl_profile.setText(tr("upscale_lbl_profile", "Profil Performance"))
        # Update profile combo items if localized
        
        self.lbl_tile.setText(tr("upscale_lbl_tile"))
        self.tile_spin.setToolTip(tr("upscale_tip_tile"))
        self.face_enhance.setText(tr("upscale_check_face"))
        self.face_enhance.setToolTip(tr("upscale_tip_face"))
        self.lbl_fp16.setText(tr("upscale_lbl_fp16", "Demi-précision (FP16)"))

        self.profile_combo.setItemText(0, tr("upscale_profile_safe"))
        self.profile_combo.setItemText(1, tr("upscale_profile_quality"))
        self.profile_combo.setItemText(2, tr("upscale_profile_speed"))
        self.profile_combo.setItemText(3, tr("upscale_profile_ultimate"))
        self.profile_combo.setItemText(4, tr("upscale_profile_custom"))

        self.check_model_status()
        self.update_model_desc()
