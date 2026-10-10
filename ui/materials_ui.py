from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QComboBox,
    QCheckBox, QMessageBox, QScrollArea, QSpinBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.database import (get_all_materials, upsert_material, delete_material,
                            add_material_movement, get_material_movements,
                            get_critical_materials)
from ui.design import (CARD_STYLE, TABLE_STYLE, COMBO_STYLE, INPUT_STYLE,
                        DIALOG_STYLE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_RED, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_BLUE,
                        BG_BASE, BG_SURFACE, BG_INPUT, BORDER,
                        btn_primary, btn_secondary, btn_danger, btn_ghost,
                        section_title)

MATERIAL_TYPES = ["Kumaş", "Çerçeve", "Duy", "Cam", "Bali"]
UNITS = ["Adet", "Top", "Kutu", "Metre", "Kg"]


class MaterialDialog(QDialog):
    def __init__(self, parent=None, material=None):
        super().__init__(parent)
        self.material = material
        self.setWindowTitle("Hammadde Düzenle" if material else "Yeni Hammadde")
        self.setMinimumWidth(420)
        self.setStyleSheet(DIALOG_STYLE)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Hammadde Düzenle" if self.material else "Yeni Hammadde Ekle")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            return l

        self.tur_combo = QComboBox()
        self.tur_combo.setStyleSheet(COMBO_STYLE)
        self.tur_combo.addItems(MATERIAL_TYPES)
        if self.material:
            idx = self.tur_combo.findText(self.material.get("tur",""))
            if idx >= 0: self.tur_combo.setCurrentIndex(idx)
        form.addRow(lbl("Tür"), self.tur_combo)

        self.ad_input = QLineEdit()
        self.ad_input.setStyleSheet(INPUT_STYLE)
        self.ad_input.setPlaceholderText("Örn: E27 Duy, MYK Alt Çerçeve")
        if self.material:
            self.ad_input.setText(self.material.get("ad",""))
        form.addRow(lbl("Ad"), self.ad_input)

        self.varyant_input = QLineEdit()
        self.varyant_input.setStyleSheet(INPUT_STYLE)
        self.varyant_input.setPlaceholderText("Örn: Gri, Füme, Bej (opsiyonel)")
        if self.material:
            self.varyant_input.setText(self.material.get("varyant",""))
        form.addRow(lbl("Renk/Varyant"), self.varyant_input)

        self.birim_combo = QComboBox()
        self.birim_combo.setStyleSheet(COMBO_STYLE)
        self.birim_combo.addItems(UNITS)
        if self.material:
            idx = self.birim_combo.findText(self.material.get("birim","Adet"))
            if idx >= 0: self.birim_combo.setCurrentIndex(idx)
        form.addRow(lbl("Birim"), self.birim_combo)

        self.stok_input = QDoubleSpinBox()
        self.stok_input.setStyleSheet(INPUT_STYLE)
        self.stok_input.setRange(0, 999999)
        self.stok_input.setDecimals(1)
        if self.material:
            self.stok_input.setValue(float(self.material.get("stok",0)))
        form.addRow(lbl("Mevcut Stok"), self.stok_input)

        self.esik_input = QDoubleSpinBox()
        self.esik_input.setStyleSheet(INPUT_STYLE)
        self.esik_input.setRange(0, 999999)
        self.esik_input.setDecimals(1)
        if self.material:
            self.esik_input.setValue(float(self.material.get("kritik_esik",0)))
        form.addRow(lbl("Kritik Eşik"), self.esik_input)

        self.alarm_check = QCheckBox("Kritik stok alarmı aktif")
        self.alarm_check.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        alarm_aktif = bool(self.material.get("alarm_aktif", 1)) if self.material else True
        self.alarm_check.setChecked(alarm_aktif)
        form.addRow("", self.alarm_check)

        layout.addLayout(form)

        note = QLabel("Not: Bali için alarm eşiğini 0 bırakın.")
        note.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("İptal")
        cancel.setStyleSheet(btn_secondary())
        cancel.clicked.connect(self.reject)
        save = QPushButton("Kaydet")
        save.setStyleSheet(btn_primary())
        save.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def get_data(self):
        return {
            "tur": self.tur_combo.currentText(),
            "ad": self.ad_input.text().strip(),
            "varyant": self.varyant_input.text().strip(),
            "birim": self.birim_combo.currentText(),
            "stok": self.stok_input.value(),
            "kritik_esik": self.esik_input.value(),
            "alarm_aktif": 1 if self.alarm_check.isChecked() else 0,
        }


class MovementDialog(QDialog):
    def __init__(self, parent=None, material=None):
        super().__init__(parent)
        self.material = material
        self.setWindowTitle("Stok Hareketi")
        self.setMinimumWidth(360)
        self.setStyleSheet(DIALOG_STYLE)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        if self.material:
            ad = self.material.get("ad","")
            varyant = self.material.get("varyant","")
            birim = self.material.get("birim","Adet")
            mevcut = self.material.get("stok", 0)
            info = QLabel(f"{ad} {varyant}\nMevcut stok: {mevcut} {birim}")
            info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
            layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            return l

        self.tip_combo = QComboBox()
        self.tip_combo.setStyleSheet(COMBO_STYLE)
        self.tip_combo.addItems(["giris", "cikis"])
        form.addRow(lbl("Hareket Türü"), self.tip_combo)

        self.miktar_input = QDoubleSpinBox()
        self.miktar_input.setStyleSheet(INPUT_STYLE)
        self.miktar_input.setRange(0.1, 99999)
        self.miktar_input.setDecimals(1)
        self.miktar_input.setValue(1)
        form.addRow(lbl("Miktar"), self.miktar_input)

        self.aciklama_input = QLineEdit()
        self.aciklama_input.setStyleSheet(INPUT_STYLE)
        self.aciklama_input.setPlaceholderText("Açıklama (opsiyonel)")
        form.addRow(lbl("Açıklama"), self.aciklama_input)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("İptal")
        cancel.setStyleSheet(btn_secondary())
        cancel.clicked.connect(self.reject)
        save = QPushButton("Kaydet")
        save.setStyleSheet(btn_primary())
        save.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def get_data(self):
        return {
            "hareket_turu": self.tip_combo.currentText(),
            "miktar": self.miktar_input.value(),
            "aciklama": self.aciklama_input.text().strip(),
        }


class MaterialsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background: {BG_BASE};")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        header.addWidget(section_title("🧰 Hammadde Takibi"))
        header.addStretch()
        add_btn = QPushButton("+ Yeni Hammadde")
        add_btn.setStyleSheet(btn_primary())
        add_btn.clicked.connect(self._add_material)
        header.addWidget(add_btn)
        layout.addLayout(header)

        # Kritik uyarı bandı
        self.alert_frame = QFrame()
        self.alert_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(248,81,73,0.1);
                border: 1px solid rgba(248,81,73,0.4);
                border-radius: 6px;
            }}
        """)
        alert_layout = QHBoxLayout(self.alert_frame)
        alert_layout.setContentsMargins(14, 10, 14, 10)
        self.alert_lbl = QLabel("")
        self.alert_lbl.setStyleSheet(f"color: {ACCENT_RED}; font-size: 12px; background: transparent;")
        self.alert_lbl.setWordWrap(True)
        alert_layout.addWidget(self.alert_lbl)
        self.alert_frame.setVisible(False)
        layout.addWidget(self.alert_frame)

        # Tür filtresi
        filter_row = QHBoxLayout()
        self.tur_filter = QComboBox()
        self.tur_filter.setStyleSheet(COMBO_STYLE)
        self.tur_filter.addItems(["Tümü"] + MATERIAL_TYPES)
        self.tur_filter.currentTextChanged.connect(self._filter)
        filter_row.addWidget(QLabel("Filtre:"))
        filter_row.addWidget(self.tur_filter)
        filter_row.addStretch()
        self.count_lbl = QLabel("0 hammadde")
        self.count_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        filter_row.addWidget(self.count_lbl)
        layout.addLayout(filter_row)

        # Table
        frame = QFrame()
        frame.setObjectName("card")
        frame.setStyleSheet(CARD_STYLE)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Tür", "Ad", "Renk/Varyant", "Birim", "Stok", "Kritik Eşik", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 220)
        self.table.setShowGrid(False)
        frame_layout.addWidget(self.table)
        layout.addWidget(frame)

    def refresh(self):
        self._all_materials = get_all_materials()
        self._update_alerts()
        self._filter(self.tur_filter.currentText() if hasattr(self, 'tur_filter') else "Tümü")

    def _update_alerts(self):
        criticals = get_critical_materials()
        if criticals:
            names = ", ".join([f"{m['ad']} {m['varyant']}".strip() for m in criticals])
            self.alert_lbl.setText(f"⚠  Kritik stok: {names}")
            self.alert_frame.setVisible(True)
        else:
            self.alert_frame.setVisible(False)

    def _filter(self, tur):
        if tur == "Tümü":
            filtered = self._all_materials
        else:
            filtered = [m for m in self._all_materials if m.get("tur") == tur]
        self._fill_table(filtered)

    def _fill_table(self, materials):
        self.table.setRowCount(len(materials))
        self.count_lbl.setText(f"{len(materials)} hammadde")
        for i, m in enumerate(materials):
            self.table.setRowHeight(i, 42)
            self.table.setItem(i, 0, QTableWidgetItem(m.get("tur","")))
            self.table.setItem(i, 1, QTableWidgetItem(m.get("ad","")))
            self.table.setItem(i, 2, QTableWidgetItem(m.get("varyant","") or "—"))
            self.table.setItem(i, 3, QTableWidgetItem(m.get("birim","Adet")))

            stok = m.get("stok", 0) or 0
            esik = m.get("kritik_esik", 0) or 0
            alarm = m.get("alarm_aktif", 1)

            stok_item = QTableWidgetItem(f"{stok:.1f}")
            if alarm and esik > 0 and stok <= esik:
                stok_item.setForeground(QColor(ACCENT_RED))
                stok_item.setText(f"{stok:.1f} ⚠")
            elif stok > esik * 2:
                stok_item.setForeground(QColor(ACCENT_GREEN))
            else:
                stok_item.setForeground(QColor(ACCENT_ORANGE))
            self.table.setItem(i, 4, stok_item)

            esik_text = f"{esik:.1f}" if alarm and esik > 0 else "—"
            self.table.setItem(i, 5, QTableWidgetItem(esik_text))

            # Butonlar
            btn_w = QWidget()
            btn_w.setStyleSheet("background: transparent;")
            btn_l = QHBoxLayout(btn_w)
            btn_l.setContentsMargins(4, 3, 4, 3)
            btn_l.setSpacing(4)

            mv_btn = QPushButton("Hareket")
            mv_btn.setStyleSheet(btn_ghost())
            mv_btn.setFixedHeight(28)
            mv_btn.setMinimumWidth(62)
            mv_btn.clicked.connect(lambda _, mat=m: self._add_movement(mat))

            edit_btn = QPushButton("Düzenle")
            edit_btn.setStyleSheet(btn_ghost())
            edit_btn.setFixedHeight(28)
            edit_btn.setMinimumWidth(68)
            edit_btn.clicked.connect(lambda _, mat=m: self._edit_material(mat))

            del_btn = QPushButton("Sil")
            del_btn.setStyleSheet(btn_danger())
            del_btn.setFixedHeight(28)
            del_btn.setMinimumWidth(44)
            del_btn.clicked.connect(lambda _, mat=m: self._delete_material(mat))

            btn_l.addWidget(mv_btn)
            btn_l.addWidget(edit_btn)
            btn_l.addWidget(del_btn)
            self.table.setCellWidget(i, 6, btn_w)

    def _add_material(self):
        dlg = MaterialDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if not d["ad"]:
                QMessageBox.warning(self, "Hata", "Ad boş olamaz.")
                return
            upsert_material(**d)
            self.refresh()

    def _edit_material(self, material):
        dlg = MaterialDialog(self, material=material)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            upsert_material(mat_id=material["id"], **d)
            self.refresh()

    def _delete_material(self, material):
        ad = f"{material.get('ad','')} {material.get('varyant','')}".strip()
        reply = QMessageBox.question(self, "Hammadde Sil",
            f"'{ad}' silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_material(material["id"])
            self.refresh()

    def _add_movement(self, material):
        dlg = MovementDialog(self, material=material)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            add_material_movement(material["id"], d["hareket_turu"],
                                   d["miktar"], d["aciklama"])
            self.refresh()
