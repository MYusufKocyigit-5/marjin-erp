import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QProgressBar, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QScrollArea, QComboBox,
    QDoubleSpinBox, QDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from core.excel_parser import parse_excel
from core.database import (save_orders, create_import_record,
                            get_all_boxes, get_cargo_price)
from ui.design import (CARD_STYLE, TABLE_STYLE, INPUT_STYLE, PROGRESS_STYLE,
                        COMBO_STYLE, DIALOG_STYLE,
                        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE,
                        BG_BASE, BG_SURFACE, BG_INPUT, BORDER,
                        btn_primary, btn_secondary, section_title)


class ImportThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            self.progress.emit(30, "Excel okunuyor...")
            orders, pending, warnings = parse_excel(self.filepath)
            self.progress.emit(90, "Tamamlandı...")
            self.finished.emit({
                "orders":   orders,
                "pending":  pending,
                "warnings": warnings,
            })
        except Exception as e:
            self.error.emit(str(e))


class ManualBoxDialog(QDialog):
    """Stok kodu bazlı gruplu koli seçimi"""
    def __init__(self, parent, orders, boxes):
        super().__init__(parent)
        self.orders = orders
        self.boxes = boxes
        self.setWindowTitle("Koli / Desi Seçimi")
        self.setMinimumWidth(900)
        self.setMinimumHeight(560)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG_SURFACE}; }}
            QLabel {{ color: {TEXT_PRIMARY}; font-size: 13px; background: transparent; }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Her stok kodu + adet kombinasyonu için koli seçin")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel("Her satır farklı bir kombinasyonu temsil eder (örn: ES-MYKKS 1 adet, ES-MYKKS 2 adet).\nKoli seçince desi otomatik gelir.")
        info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Stok kodu + adet kombinasyonlarını grupla
        self.groups = {}
        for o in self.orders:
            sk   = o["stok_kodu"]
            adet = o["adet"]
            key  = (sk, adet)
            if key not in self.groups:
                self.groups[key] = {
                    "stok_kodu":    sk,
                    "urun_adi":     o["urun_adi"][:50],
                    "adet":         adet,
                    "orders":       [],
                    "kargo_firmasi":o.get("kargo_firmasi",""),
                }
            self.groups[key]["orders"].append(o)

        # Tablo
        self.table = QTableWidget()
        self.table.setStyleSheet(TABLE_STYLE + f"QTableWidget {{ background: {BG_BASE}; }}")
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Stok Kodu", "Ürün Adı", "Adet", "Koli Seç", "Desi"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 220)
        self.table.setColumnWidth(4, 100)
        self.table.horizontalHeader().setMinimumSectionSize(80)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setRowCount(len(self.groups))

        self.combos    = {}
        self.desi_spins = {}
        box_items = [f"{b['koli_adi']} ({b['desi']} desi)" for b in self.boxes]

        for i, (key, grp) in enumerate(self.groups.items()):
            sk, adet = key
            self.table.setRowHeight(i, 46)
            self.table.setItem(i, 0, QTableWidgetItem(sk))
            self.table.setItem(i, 1, QTableWidgetItem(grp["urun_adi"]))
            adet_item = QTableWidgetItem(f"{adet} adet")
            adet_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, adet_item)

            combo = QComboBox()
            combo.setStyleSheet(COMBO_STYLE)
            combo.addItem("— Koli seç —", None)
            for j, b in enumerate(self.boxes):
                combo.addItem(box_items[j], b["id"])

            desi_spin = QDoubleSpinBox()
            desi_spin.setStyleSheet(INPUT_STYLE)
            desi_spin.setRange(0, 500)
            desi_spin.setDecimals(1)
            desi_spin.setMinimumWidth(80)

            def on_combo(idx, spin=desi_spin, k=key):
                box_id = self.combos[k].currentData()
                if box_id:
                    box = next((b for b in self.boxes if b["id"] == box_id), None)
                    if box:
                        spin.setValue(float(box["desi"]))

            combo.currentIndexChanged.connect(on_combo)
            self.combos[key]     = combo
            self.desi_spins[key] = desi_spin

            self.table.setCellWidget(i, 3, combo)
            self.table.setCellWidget(i, 4, desi_spin)

        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        skip_btn = QPushButton("Geç (desi=0 olarak kaydet)")
        skip_btn.setStyleSheet(btn_secondary())
        skip_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("✓  Tamamla ve Kaydet")
        ok_btn.setStyleSheet(btn_primary())
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(skip_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def get_results(self):
        """(stok_kodu, adet) → {koli_id, koli_adi, koli_desi, koli_maliyet} map döndür"""
        results = {}
        for key in self.groups:
            box_id   = self.combos[key].currentData()
            desi_val = self.desi_spins[key].value()
            box      = next((b for b in self.boxes if b["id"] == box_id), None)
            results[key] = {
                "koli_id":     box_id,
                "koli_adi":    box["koli_adi"] if box else "",
                "koli_desi":   float(box["desi"]) if box else desi_val,
                "koli_maliyet":float(box["alis_maliyeti"]) if box else 0.0,
            }
        return results


class ImportWidget(QWidget):
    def __init__(self, on_import_complete=None):
        super().__init__()
        self.on_import_complete = on_import_complete
        self.selected_file = None
        self._build_ui()

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

        layout.addWidget(section_title("Excel İçe Aktar"))

        sub = QLabel("Trendyol sipariş raporunuzu seçin. Excel yüklendikten sonra her ürün için koli ve desi seçimi yapabilirsiniz.")
        sub.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Dosya seçim
        drop_frame = QFrame()
        drop_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG_SURFACE};
                border: 2px dashed {BORDER};
                border-radius: 10px;
            }}
        """)
        drop_frame.setFixedHeight(130)
        drop_l = QVBoxLayout(drop_frame)
        drop_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_l.setSpacing(10)

        self.file_label = QLabel("Trendyol Excel dosyası seçin")
        self.file_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_l.addWidget(self.file_label)

        select_btn = QPushButton("Dosya Seç")
        select_btn.setStyleSheet(btn_secondary())
        select_btn.setFixedWidth(130)
        select_btn.clicked.connect(self._select_file)
        drop_l.addWidget(select_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(drop_frame)

        # Progress
        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(
            f"background: {BG_SURFACE}; border-radius: 8px; border: 1px solid {BORDER};")
        self.progress_frame.setVisible(False)
        prog_l = QVBoxLayout(self.progress_frame)
        prog_l.setContentsMargins(16, 12, 16, 12)
        self.progress_label = QLabel("İşleniyor...")
        self.progress_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(PROGRESS_STYLE)
        self.progress_bar.setFixedHeight(6)
        prog_l.addWidget(self.progress_label)
        prog_l.addWidget(self.progress_bar)
        layout.addWidget(self.progress_frame)

        self.import_btn = QPushButton("İçe Aktar")
        self.import_btn.setStyleSheet(btn_primary())
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._start_import)
        layout.addWidget(self.import_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Sonuç
        self.result_frame = QFrame()
        self.result_frame.setObjectName("card")
        self.result_frame.setStyleSheet(CARD_STYLE)
        self.result_frame.setVisible(False)
        result_l = QVBoxLayout(self.result_frame)
        result_l.setContentsMargins(16, 14, 16, 16)

        self.result_title = QLabel("Sonuçlar")
        self.result_title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
        result_l.addWidget(self.result_title)

        self.result_table = QTableWidget()
        self.result_table.setStyleSheet(TABLE_STYLE + f"QTableWidget {{ background: {BG_BASE}; }}")
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setFixedHeight(260)
        self.result_table.setShowGrid(False)
        result_l.addWidget(self.result_table)

        self.warnings_list = QListWidget()
        self.warnings_list.setStyleSheet(f"""
            QListWidget {{
                background: rgba(210,153,34,0.08);
                color: {ACCENT_ORANGE};
                border: 1px solid rgba(210,153,34,0.3);
                border-radius: 6px; font-size: 12px; padding: 4px;
            }}
        """)
        self.warnings_list.setVisible(False)
        self.warnings_list.setMaximumHeight(100)
        result_l.addWidget(self.warnings_list)
        layout.addWidget(self.result_frame)
        layout.addStretch()

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Trendyol Excel Raporu Seç", "",
            "Excel Dosyaları (*.xlsx *.xls)")
        if path:
            self.selected_file = path
            fname = os.path.basename(path)
            self.file_label.setText(f"✓  {fname}")
            self.file_label.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 14px;")
            self.import_btn.setEnabled(True)

    def _start_import(self):
        if not self.selected_file:
            return
        self.import_btn.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_frame.setVisible(False)

        self.thread = ImportThread(self.selected_file)
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_parsed)
        self.thread.error.connect(self._on_error)
        self.thread.start()

    def _on_progress(self, value, msg):
        self.progress_bar.setValue(value)
        self.progress_label.setText(msg)

    def _on_parsed(self, result):
        orders   = result["orders"]
        warnings = result["warnings"]

        self.progress_frame.setVisible(False)

        # Her zaman koli seçim dialog'u aç
        boxes = get_all_boxes()
        if not boxes:
            QMessageBox.warning(self, "Uyarı",
                "Henüz koli tanımlanmamış!\nPaketleme ekranından koli ekleyin.")
            self.import_btn.setEnabled(True)
            return

        dlg = ManualBoxDialog(self, orders, boxes)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            manual_map = dlg.get_results()
        else:
            # Geç — tüm koliler boş
            manual_map = {(o["stok_kodu"], o["adet"]): {"koli_id": None, "koli_adi": "", "koli_desi": 0.0, "koli_maliyet": 0.0}
                          for o in orders}

        # Siparişlere koli uygula ve net kar hesapla
        for order in orders:
            key = (order["stok_kodu"], order["adet"])
            mr  = manual_map.get(key, {})
            order["koli_id"]      = mr.get("koli_id")
            order["koli_adi"]     = mr.get("koli_adi", "")
            order["koli_desi"]    = mr.get("koli_desi", 0.0)
            order["koli_maliyet"] = mr.get("koli_maliyet", 0.0)

            firma = order.get("kargo_firmasi","")
            desi  = order["koli_desi"]
            if firma and desi > 0:
                order["kargo_hesaplanan"] = round(get_cargo_price(firma, desi), 2)
            else:
                order["kargo_hesaplanan"] = 0.0

            order["net_kar"] = round(
                order["faturalanacak_kdvsiz"]
                - order["komisyon_tutari"]
                - order["kargo_hesaplanan"]
                - order["koli_maliyet"]
                - order["alis_maliyeti"] * order["adet"], 2)

        # Kaydet
        toplam_ciro = sum(o["faturalanacak_tutar"] for o in orders)
        toplam_kar  = sum(o["net_kar"] for o in orders)
        dosya_adi   = os.path.basename(self.selected_file)
        import_id   = create_import_record(dosya_adi, len(orders), toplam_ciro, toplam_kar)
        save_orders(orders, import_id)

        self.import_btn.setEnabled(True)
        self._show_results(orders, warnings, toplam_ciro, toplam_kar)
        if self.on_import_complete:
            self.on_import_complete()

    def _show_results(self, orders, warnings, toplam_ciro, toplam_kar):
        self.result_title.setText(
            f"✅  {len(orders)} sipariş  |  Ciro: ₺{toplam_ciro:,.0f}  |  Net Kar: ₺{toplam_kar:,.0f}")
        self.result_frame.setVisible(True)

        cols = ["Tarih", "Stok Kodu", "Ürün", "Adet",
                "KDV Hariç", "Komisyon", "Koli", "Kargo", "Maliyet", "Net Kar"]
        self.result_table.setColumnCount(len(cols))
        self.result_table.setHorizontalHeaderLabels(cols)
        self.result_table.setRowCount(len(orders))
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        for i, o in enumerate(orders):
            self.result_table.setRowHeight(i, 36)
            self.result_table.setItem(i, 0, QTableWidgetItem(str(o["siparis_tarihi"])[:10]))
            self.result_table.setItem(i, 1, QTableWidgetItem(o["stok_kodu"]))
            self.result_table.setItem(i, 2, QTableWidgetItem(o["urun_adi"][:40]))
            self.result_table.setItem(i, 3, QTableWidgetItem(str(o["adet"])))
            self.result_table.setItem(i, 4, QTableWidgetItem(f"₺{o['faturalanacak_kdvsiz']:.2f}"))
            self.result_table.setItem(i, 5, QTableWidgetItem(f"₺{o['komisyon_tutari']:.2f}"))
            self.result_table.setItem(i, 6, QTableWidgetItem(o.get("koli_adi","") or "—"))
            self.result_table.setItem(i, 7, QTableWidgetItem(f"₺{o.get('kargo_hesaplanan',0):.2f}"))
            maliyet = o.get("alis_maliyeti",0) * o.get("adet",1)
            self.result_table.setItem(i, 8, QTableWidgetItem(f"₺{maliyet:.2f}"))
            kar_item = QTableWidgetItem(f"₺{o['net_kar']:.2f}")
            kar_item.setForeground(QColor(ACCENT_GREEN if o["net_kar"] >= 0 else ACCENT_RED))
            self.result_table.setItem(i, 9, kar_item)

        if warnings:
            self.warnings_list.setVisible(True)
            self.warnings_list.clear()
            self.warnings_list.addItem(QListWidgetItem(f"⚠  {len(warnings)} ürünün alış maliyeti girilmemiş:"))
            for w in warnings[:15]:
                self.warnings_list.addItem(QListWidgetItem(f"   • {w}"))

    def _on_error(self, msg):
        self.import_btn.setEnabled(True)
        self.progress_frame.setVisible(False)
        QMessageBox.critical(self, "Hata", f"İçe aktarma başarısız:\n\n{msg}")


class ImportHistoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.addWidget(section_title("Import Geçmişi"))
        header.addStretch()
        refresh_btn = QPushButton("Yenile")
        refresh_btn.setStyleSheet(btn_secondary())
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        info = QLabel("⚠  Bir importu sildiğinizde o importa ait tüm siparişler kalıcı olarak silinir.")
        info.setStyleSheet(f"""
            color: {ACCENT_RED}; background: rgba(248,81,73,0.08);
            border: 1px solid rgba(248,81,73,0.3); border-radius: 6px;
            padding: 8px 14px; font-size: 12px;
        """)
        info.setWordWrap(True)
        layout.addWidget(info)

        frame = QFrame()
        frame.setObjectName("card")
        frame.setStyleSheet(CARD_STYLE)
        frame_l = QVBoxLayout(frame)
        frame_l.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Tarih", "Dosya Adı", "Sipariş", "Ciro (₺)", "Net Kar (₺)", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 80)
        frame_l.addWidget(self.table)
        layout.addWidget(frame)

    def refresh(self):
        from core.database import get_all_imports
        imports = get_all_imports()
        self.table.setRowCount(len(imports))
        for i, imp in enumerate(imports):
            self.table.setRowHeight(i, 42)
            self.table.setItem(i, 0, QTableWidgetItem(str(imp.get("import_tarihi",""))[:16]))
            self.table.setItem(i, 1, QTableWidgetItem(imp.get("dosya_adi","")))
            self.table.setItem(i, 2, QTableWidgetItem(str(imp.get("gercek_siparis",0))))
            ciro = imp.get("toplam_ciro",0) or 0
            kar  = imp.get("toplam_kar",0) or 0
            self.table.setItem(i, 3, QTableWidgetItem(f"₺{ciro:,.0f}"))
            kar_item = QTableWidgetItem(f"₺{kar:,.0f}")
            kar_item.setForeground(QColor(ACCENT_GREEN if kar >= 0 else ACCENT_RED))
            self.table.setItem(i, 4, kar_item)

            del_btn = QPushButton("Sil")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {ACCENT_RED};
                    border: 1px solid {ACCENT_RED}; border-radius: 6px;
                    padding: 4px 12px; font-size: 12px;
                }}
                QPushButton:hover {{ background: rgba(248,81,73,0.1); }}
            """)
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, imp_id=imp["id"], fname=imp.get("dosya_adi",""):
                                     self._delete_import(imp_id, fname))
            w = QWidget()
            w.setStyleSheet("background: transparent;")
            wl = QHBoxLayout(w)
            wl.setContentsMargins(6, 4, 6, 4)
            wl.addWidget(del_btn)
            self.table.setCellWidget(i, 5, w)

    def _delete_import(self, import_id, fname):
        from core.database import delete_import
        reply = QMessageBox.question(
            self, "Import Sil",
            f"'{fname}' dosyasına ait tüm siparişler silinsin mi?\nBu işlem geri alınamaz.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_import(import_id)
            self.refresh()
            QMessageBox.information(self, "Silindi", "Import ve siparişleri silindi.")
