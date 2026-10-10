from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QScrollArea, QTabWidget,
    QComboBox, QSpinBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.database import (get_all_boxes, upsert_box, delete_box,
                            get_box_rules, upsert_box_rule, delete_box_rule,
                            get_unique_models_from_products, get_all_products)
from ui.design import (CARD_STYLE, TABLE_STYLE, COMBO_STYLE, INPUT_STYLE,
                        DIALOG_STYLE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_RED, ACCENT_BLUE, BG_BASE, BG_SURFACE, BG_INPUT,
                        BORDER, btn_primary, btn_secondary, btn_danger, btn_ghost,
                        section_title)


class BoxDialog(QDialog):
    def __init__(self, parent=None, box=None):
        super().__init__(parent)
        self.box = box
        self.setWindowTitle("Koli Düzenle" if box else "Yeni Koli")
        self.setMinimumWidth(380)
        self.setStyleSheet(DIALOG_STYLE)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Koli Düzenle" if self.box else "Yeni Koli Ekle")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            return l

        self.ad_input = QLineEdit()
        self.ad_input.setStyleSheet(INPUT_STYLE)
        self.ad_input.setPlaceholderText("Örn: MYK Kolisi")
        if self.box:
            self.ad_input.setText(self.box.get("koli_adi", ""))
        form.addRow(lbl("Koli Adı"), self.ad_input)

        self.desi_input = QDoubleSpinBox()
        self.desi_input.setStyleSheet(INPUT_STYLE)
        self.desi_input.setRange(0, 500)
        self.desi_input.setDecimals(1)
        self.desi_input.setSuffix("  desi")
        if self.box:
            self.desi_input.setValue(float(self.box.get("desi", 0)))
        form.addRow(lbl("Desi"), self.desi_input)

        self.maliyet_input = QDoubleSpinBox()
        self.maliyet_input.setStyleSheet(INPUT_STYLE)
        self.maliyet_input.setRange(0, 9999)
        self.maliyet_input.setDecimals(2)
        self.maliyet_input.setSuffix("  ₺")
        if self.box:
            self.maliyet_input.setValue(float(self.box.get("alis_maliyeti", 0)))
        form.addRow(lbl("Alış Maliyeti"), self.maliyet_input)

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
            "koli_adi": self.ad_input.text().strip(),
            "desi": self.desi_input.value(),
            "alis_maliyeti": self.maliyet_input.value(),
        }


class BoxRuleDialog(QDialog):
    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle("Koli Kuralı")
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_STYLE)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Koli Kuralı Ekle")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        sub = QLabel("Hangi model, kaç adet sipariş geldiğinde hangi koli kullanılsın?")
        sub.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            return l

        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(COMBO_STYLE)
        models = get_unique_models_from_products()
        self.model_combo.addItems(models)
        if self.rule:
            idx = self.model_combo.findText(self.rule.get("model_kodu",""))
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
        form.addRow(lbl("Model Kodu"), self.model_combo)

        self.adet_input = QSpinBox()
        self.adet_input.setStyleSheet(INPUT_STYLE)
        self.adet_input.setRange(1, 20)
        self.adet_input.setSuffix("  adet")
        if self.rule:
            self.adet_input.setValue(int(self.rule.get("adet", 1)))
        form.addRow(lbl("Sipariş Adedi"), self.adet_input)

        self.box_combo = QComboBox()
        self.box_combo.setStyleSheet(COMBO_STYLE)
        self._boxes = get_all_boxes()
        for b in self._boxes:
            self.box_combo.addItem(f"{b['koli_adi']} ({b['desi']} desi)", b["id"])
        if self.rule:
            for i, b in enumerate(self._boxes):
                if b["id"] == self.rule.get("box_id"):
                    self.box_combo.setCurrentIndex(i)
                    break
        form.addRow(lbl("Koli"), self.box_combo)

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
            "model_kodu": self.model_combo.currentText(),
            "adet": self.adet_input.value(),
            "box_id": self.box_combo.currentData(),
        }


class PackagingWidget(QWidget):
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
        layout.setSpacing(20)

        layout.addWidget(section_title("📦 Paketleme"))

        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 8px;
                background: {BG_SURFACE};
            }}
            QTabBar::tab {{
                background: {BG_BASE};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-bottom: none;
                padding: 8px 20px;
                font-size: 13px;
                border-radius: 6px 6px 0 0;
            }}
            QTabBar::tab:selected {{
                background: {BG_SURFACE};
                color: {ACCENT_BLUE};
                border-bottom: 2px solid {ACCENT_BLUE};
            }}
            QTabBar::tab:hover {{ color: {TEXT_PRIMARY}; }}
        """)

        # Tab 1: Koli tanımları
        tab1 = QWidget()
        tab1.setStyleSheet(f"background: {BG_SURFACE};")
        t1_layout = QVBoxLayout(tab1)
        t1_layout.setContentsMargins(16, 16, 16, 16)
        t1_layout.setSpacing(12)

        t1_header = QHBoxLayout()
        t1_lbl = QLabel("Koli Tanımları")
        t1_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold;")
        t1_header.addWidget(t1_lbl)
        t1_header.addStretch()
        add_box_btn = QPushButton("+ Yeni Koli")
        add_box_btn.setStyleSheet(btn_primary())
        add_box_btn.clicked.connect(self._add_box)
        t1_header.addWidget(add_box_btn)
        t1_layout.addLayout(t1_header)

        self.boxes_table = QTableWidget()
        self.boxes_table.setStyleSheet(TABLE_STYLE)
        self.boxes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.boxes_table.verticalHeader().setVisible(False)
        self.boxes_table.setColumnCount(4)
        self.boxes_table.setHorizontalHeaderLabels(["Koli Adı", "Desi", "Alış Maliyeti", "İşlem"])
        self.boxes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.boxes_table.setColumnWidth(1, 100)
        self.boxes_table.setColumnWidth(2, 130)
        self.boxes_table.setColumnWidth(3, 170)
        self.boxes_table.setShowGrid(False)
        t1_layout.addWidget(self.boxes_table)
        tabs.addTab(tab1, "Koli Tanımları")

        # Tab 2: Koli kuralları
        tab2 = QWidget()
        tab2.setStyleSheet(f"background: {BG_SURFACE};")
        t2_layout = QVBoxLayout(tab2)
        t2_layout.setContentsMargins(16, 16, 16, 16)
        t2_layout.setSpacing(12)

        t2_header = QHBoxLayout()
        t2_lbl = QLabel("Model Bazlı Koli Kuralları")
        t2_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold;")
        t2_header.addWidget(t2_lbl)
        t2_header.addStretch()
        add_rule_btn = QPushButton("+ Yeni Kural")
        add_rule_btn.setStyleSheet(btn_primary())
        add_rule_btn.clicked.connect(self._add_rule)
        t2_header.addWidget(add_rule_btn)
        t2_layout.addLayout(t2_header)

        info = QLabel("Tanımsız kombinasyonlar için import sırasında manuel koli girişi istenir.")
        info.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        t2_layout.addWidget(info)

        self.rules_table = QTableWidget()
        self.rules_table.setStyleSheet(TABLE_STYLE)
        self.rules_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.setColumnCount(4)
        self.rules_table.setHorizontalHeaderLabels(["Model Kodu", "Adet", "Koli", "İşlem"])
        self.rules_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.rules_table.setColumnWidth(0, 150)
        self.rules_table.setColumnWidth(1, 80)
        self.rules_table.setColumnWidth(3, 90)
        self.rules_table.setShowGrid(False)
        t2_layout.addWidget(self.rules_table)
        tabs.addTab(tab2, "Koli Kuralları")

        layout.addWidget(tabs)

    def refresh(self):
        self._refresh_boxes()
        self._refresh_rules()

    def _refresh_boxes(self):
        boxes = get_all_boxes()
        self.boxes_table.setRowCount(len(boxes))
        for i, b in enumerate(boxes):
            self.boxes_table.setRowHeight(i, 40)
            self.boxes_table.setItem(i, 0, QTableWidgetItem(b["koli_adi"]))
            self.boxes_table.setItem(i, 1, QTableWidgetItem(f"{b['desi']} desi"))
            maliyet = b.get("alis_maliyeti", 0) or 0
            m_item = QTableWidgetItem(f"₺{maliyet:.2f}")
            if maliyet == 0:
                m_item.setForeground(QColor("#d29922"))
            self.boxes_table.setItem(i, 2, m_item)

            btn_w = QWidget()
            btn_w.setStyleSheet("background: transparent;")
            btn_l = QHBoxLayout(btn_w)
            btn_l.setContentsMargins(6, 4, 6, 4)
            btn_l.setSpacing(6)
            edit = QPushButton("Düzenle")
            edit.setStyleSheet(btn_ghost())
            edit.setFixedHeight(28)
            edit.setMinimumWidth(70)
            edit.clicked.connect(lambda _, box=b: self._edit_box(box))
            dlt = QPushButton("Sil")
            dlt.setStyleSheet(btn_danger())
            dlt.setFixedHeight(28)
            dlt.setMinimumWidth(44)
            dlt.clicked.connect(lambda _, box=b: self._delete_box(box))
            btn_l.addWidget(edit)
            btn_l.addWidget(dlt)
            self.boxes_table.setCellWidget(i, 3, btn_w)

    def _refresh_rules(self):
        rules = get_box_rules()
        self.rules_table.setRowCount(len(rules))
        for i, r in enumerate(rules):
            self.rules_table.setRowHeight(i, 40)
            self.rules_table.setItem(i, 0, QTableWidgetItem(r.get("model_kodu","")))
            self.rules_table.setItem(i, 1, QTableWidgetItem(f"{r.get('adet','')} adet"))
            koli_adi = r.get("koli_adi","") or "—"
            desi = r.get("desi","")
            self.rules_table.setItem(i, 2, QTableWidgetItem(f"{koli_adi} ({desi} desi)"))

            del_w = QWidget()
            del_w.setStyleSheet("background: transparent;")
            del_l = QHBoxLayout(del_w)
            del_l.setContentsMargins(6, 4, 6, 4)
            dlt = QPushButton("Sil")
            dlt.setStyleSheet(btn_danger())
            dlt.setFixedHeight(28)
            dlt.clicked.connect(lambda _, rule=r: self._delete_rule(rule))
            del_l.addWidget(dlt)
            del_l.addStretch()
            self.rules_table.setCellWidget(i, 3, del_w)

    def _add_box(self):
        dlg = BoxDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if not d["koli_adi"]:
                QMessageBox.warning(self, "Hata", "Koli adı boş olamaz.")
                return
            upsert_box(d["koli_adi"], d["desi"], d["alis_maliyeti"])
            self._refresh_boxes()

    def _edit_box(self, box):
        dlg = BoxDialog(self, box=box)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            upsert_box(d["koli_adi"], d["desi"], d["alis_maliyeti"], box_id=box["id"])
            self._refresh_boxes()

    def _delete_box(self, box):
        reply = QMessageBox.question(self, "Koli Sil",
            f"'{box['koli_adi']}' kolisi silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_box(box["id"])
            self._refresh_boxes()

    def _add_rule(self):
        models = get_unique_models_from_products()
        if not models:
            QMessageBox.information(self, "Bilgi",
                "Önce Ürün Maliyetleri ekranında ürünlere model kodu atayın.")
            return
        dlg = BoxRuleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            upsert_box_rule(d["model_kodu"], d["adet"], d["box_id"])
            self._refresh_rules()

    def _delete_rule(self, rule):
        delete_box_rule(rule["id"])
        self._refresh_rules()
