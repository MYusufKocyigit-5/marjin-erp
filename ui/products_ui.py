import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QTextEdit,
    QMessageBox, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.database import get_all_products, upsert_product, delete_product
from ui.design import (CARD_STYLE, TABLE_STYLE, INPUT_STYLE, DIALOG_STYLE,
                        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
                        BG_BASE, BG_SURFACE, BG_INPUT, BORDER,
                        btn_primary, btn_secondary, btn_danger, btn_ghost,
                        section_title)


class ProductDialog(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle("Ürün Düzenle" if product else "Yeni Ürün")
        self.setMinimumWidth(440)
        self.setStyleSheet(DIALOG_STYLE)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Ürün Düzenle" if self.product else "Yeni Ürün Ekle")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def lbl(text):
            l = QLabel(text)
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            return l

        self.stok_input = QLineEdit()
        self.stok_input.setStyleSheet(INPUT_STYLE)
        self.stok_input.setPlaceholderText("Örn: ES-MYKKS")
        if self.product:
            self.stok_input.setText(self.product.get("stok_kodu", ""))
            self.stok_input.setReadOnly(True)
            self.stok_input.setStyleSheet(INPUT_STYLE + f"QLineEdit {{ color: {TEXT_MUTED}; }}")
        form.addRow(lbl("Stok Kodu"), self.stok_input)

        self.model_input = QLineEdit()
        self.model_input.setStyleSheet(INPUT_STYLE)
        self.model_input.setPlaceholderText("Örn: ES-MYK3")
        if self.product:
            self.model_input.setText(self.product.get("model_kodu", "") or "")
        form.addRow(lbl("Model Kodu"), self.model_input)

        self.urun_input = QLineEdit()
        self.urun_input.setStyleSheet(INPUT_STYLE)
        self.urun_input.setPlaceholderText("Ürün adı")
        if self.product:
            self.urun_input.setText(self.product.get("urun_adi", ""))
        form.addRow(lbl("Ürün Adı"), self.urun_input)

        self.alis_input = QDoubleSpinBox()
        self.alis_input.setStyleSheet(INPUT_STYLE)
        self.alis_input.setRange(0, 99999)
        self.alis_input.setDecimals(2)
        self.alis_input.setSuffix("  ₺")
        if self.product:
            self.alis_input.setValue(float(self.product.get("alis_maliyeti", 0)))
        form.addRow(lbl("Alış Maliyeti"), self.alis_input)

        self.not_input = QTextEdit()
        self.not_input.setStyleSheet(INPUT_STYLE)
        self.not_input.setPlaceholderText("Notlar (opsiyonel)")
        self.not_input.setMaximumHeight(65)
        if self.product:
            self.not_input.setPlainText(self.product.get("notlar", "") or "")
        form.addRow(lbl("Notlar"), self.not_input)

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
            "stok_kodu":    self.stok_input.text().strip(),
            "model_kodu":   self.model_input.text().strip(),
            "urun_adi":     self.urun_input.text().strip(),
            "alis_maliyeti":self.alis_input.value(),
            "notlar":       self.not_input.toPlainText().strip(),
        }


class ProductsWidget(QWidget):
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
        header.addWidget(section_title("Ürün Maliyetleri"))
        header.addStretch()

        excel_btn = QPushButton("📥  Excel'den İçe Aktar")
        excel_btn.setStyleSheet(btn_secondary())
        excel_btn.clicked.connect(self._import_from_excel)
        header.addWidget(excel_btn)

        add_btn = QPushButton("+ Yeni Ürün")
        add_btn.setStyleSheet(btn_primary())
        add_btn.clicked.connect(self._add_product)
        header.addWidget(add_btn)
        layout.addLayout(header)

        info = QLabel("⚠  Alış maliyeti girilmemiş ürünler için Net Kar hesabı eksik kalır.")
        info.setStyleSheet(f"""
            color: #d29922;
            background-color: rgba(210,153,34,0.1);
            border: 1px solid rgba(210,153,34,0.3);
            border-radius: 6px;
            padding: 8px 14px; font-size: 12px;
        """)
        info.setWordWrap(True)
        layout.addWidget(info)

        # Arama
        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setStyleSheet(INPUT_STYLE)
        self.search_box.setPlaceholderText("Stok kodu, model veya ürün adı ara...")
        self.search_box.setMaximumWidth(340)
        self.search_box.textChanged.connect(self._filter)
        search_row.addWidget(self.search_box)
        search_row.addStretch()
        self.count_lbl = QLabel("0 ürün")
        self.count_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        search_row.addWidget(self.count_lbl)
        layout.addLayout(search_row)

        # Tablo
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Stok Kodu", "Model", "Ürün Adı", "Alış Maliyeti", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 170)
        self.table.setShowGrid(False)
        frame_layout.addWidget(self.table)
        layout.addWidget(frame)

    def refresh(self):
        self._all_products = get_all_products()
        self._fill_table(self._all_products)

    def _filter(self, text):
        if not text:
            self._fill_table(self._all_products)
            return
        t = text.lower()
        filtered = [p for p in self._all_products
                    if t in p.get("stok_kodu","").lower()
                    or t in p.get("urun_adi","").lower()
                    or t in (p.get("model_kodu","") or "").lower()]
        self._fill_table(filtered)

    def _fill_table(self, products):
        self.table.setRowCount(len(products))
        self.count_lbl.setText(f"{len(products)} ürün")
        for i, p in enumerate(products):
            self.table.setRowHeight(i, 42)
            self.table.setItem(i, 0, QTableWidgetItem(p.get("stok_kodu","")))
            self.table.setItem(i, 1, QTableWidgetItem(p.get("model_kodu","") or ""))
            self.table.setItem(i, 2, QTableWidgetItem(p.get("urun_adi","")[:60]))
            alis = p.get("alis_maliyeti", 0) or 0
            alis_item = QTableWidgetItem(f"₺{alis:.2f}")
            alis_item.setForeground(QColor(ACCENT_RED if alis == 0 else ACCENT_GREEN))
            self.table.setItem(i, 3, alis_item)

            btn_w = QWidget()
            btn_w.setStyleSheet("background: transparent;")
            btn_l = QHBoxLayout(btn_w)
            btn_l.setContentsMargins(8, 4, 8, 4)
            btn_l.setSpacing(8)
            edit_btn = QPushButton("Düzenle")
            edit_btn.setStyleSheet(btn_ghost())
            edit_btn.setFixedHeight(28)
            edit_btn.setMinimumWidth(72)
            edit_btn.clicked.connect(lambda _, prod=p: self._edit_product(prod))
            del_btn = QPushButton("Sil")
            del_btn.setStyleSheet(btn_danger())
            del_btn.setFixedHeight(28)
            del_btn.setMinimumWidth(48)
            del_btn.clicked.connect(lambda _, prod=p: self._delete_product(prod))
            btn_l.addWidget(edit_btn)
            btn_l.addWidget(del_btn)
            self.table.setCellWidget(i, 4, btn_w)

    def _add_product(self):
        dlg = ProductDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["stok_kodu"]:
                QMessageBox.warning(self, "Hata", "Stok kodu boş olamaz.")
                return
            upsert_product(**data)
            self.refresh()

    def _edit_product(self, product):
        dlg = ProductDialog(self, product=product)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            upsert_product(**data)
            self.refresh()

    def _delete_product(self, product):
        reply = QMessageBox.question(
            self, "Ürün Sil",
            f"'{product['stok_kodu']}' silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_product(product["stok_kodu"])
            self.refresh()

    def _import_from_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ürünler Excel Dosyası Seç", "",
            "Excel Dosyaları (*.xlsx *.xls)")
        if not path:
            return
        try:
            df = pd.read_excel(path, sheet_name="Ürünler")
            required = ["Tedarikçi Stok Kodu", "Model Kodu", "Ürün Adı"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                QMessageBox.critical(self, "Hata",
                    f"Excel'de şu sütunlar bulunamadı:\n{', '.join(missing)}")
                return

            added = 0
            skipped = 0
            for _, row in df.iterrows():
                stok_kodu = str(row.get("Tedarikçi Stok Kodu", "")).strip()
                model_kodu = str(row.get("Model Kodu", "")).strip()
                urun_adi = str(row.get("Ürün Adı", "")).strip()
                if not stok_kodu or stok_kodu == "nan":
                    skipped += 1
                    continue
                upsert_product(
                    stok_kodu=stok_kodu,
                    model_kodu=model_kodu if model_kodu != "nan" else "",
                    urun_adi=urun_adi[:200] if urun_adi != "nan" else "",
                    alis_maliyeti=0,
                )
                added += 1

            self.refresh()
            QMessageBox.information(self, "Tamamlandı",
                f"✅  {added} ürün içe aktarıldı.\n"
                f"Alış maliyetlerini tek tek girebilirsiniz.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel okunamadı:\n{str(e)}")
