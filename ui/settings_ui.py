import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QProgressBar, QScrollArea,
    QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from core.database import (save_cargo_prices, get_cargo_update_date,
                            get_connection, get_setting, set_setting)
from ui.design import (CARD_STYLE, TABLE_STYLE, INPUT_STYLE, PROGRESS_STYLE,
                        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE,
                        BG_BASE, BG_SURFACE, BG_INPUT, BORDER,
                        btn_primary, btn_secondary, section_title)


class CargoPDFThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            import pdfplumber
            self.progress.emit(20, "PDF okunuyor...")
            results = {}
            tarih = datetime.now().strftime("%Y-%m-%d")

            firma_cols = {"TEX": None, "DHL eCommerce": None, "Aras": None}
            all_rows = []
            headers = []

            with pdfplumber.open(self.filepath) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if not table:
                        continue
                    for row in table:
                        if not row or not row[0]:
                            continue
                        # Başlık satırı: tam olarak "Desi/KG" ile başlar
                        row0 = str(row[0]).strip()
                        if row0 == "Desi/KG":
                            headers = row
                            continue
                        # Veri satırı — ilk sütun sayı olmalı
                        if headers:
                            try:
                                int(row0.split(".")[0].split(",")[0])
                                all_rows.append(row)
                            except:
                                continue

            self.progress.emit(50, "Sütunlar eşleştiriliyor...")

            if not headers:
                self.error.emit("PDF formatı tanınamadı — başlık satırı bulunamadı.")
                return

            # Sütun indekslerini bul
            for i, h in enumerate(headers):
                if not h:
                    continue
                h_str = str(h).strip()
                if h_str == "TEX":
                    firma_cols["TEX"] = i
                elif "DHL" in h_str:
                    firma_cols["DHL eCommerce"] = i
                elif h_str == "Aras":
                    firma_cols["Aras"] = i

            self.progress.emit(70, "Fiyatlar kaydediliyor...")

            for firma, col_idx in firma_cols.items():
                if col_idx is None:
                    continue
                prices = {}
                for row in all_rows:
                    try:
                        desi_str = str(row[0]).strip().split(".")[0].split(",")[0]
                        desi = int(desi_str)
                        if col_idx >= len(row) or not row[col_idx]:
                            continue
                        fiyat_str = str(row[col_idx]).strip().replace(".", "").replace(",", ".")
                        fiyat = float(fiyat_str)
                        prices[desi] = fiyat
                    except:
                        continue
                if prices:
                    save_cargo_prices(firma, prices, tarih)
                    results[firma] = len(prices)

            self.progress.emit(100, "Tamamlandı!")
            self.finished.emit(results)

        except ImportError:
            self.error.emit("pdfplumber eksik.\nKomut: pip install pdfplumber")
        except Exception as e:
            self.error.emit(str(e))


def get_cargo_sample_prices():
    """Her firma için ilk 10 desi fiyatını getir"""
    conn = get_connection()
    result = {}
    for firma in ["TEX", "DHL eCommerce", "Aras"]:
        rows = conn.execute("""
            SELECT desi, fiyat FROM cargo_prices
            WHERE firma=? ORDER BY desi LIMIT 10
        """, (firma,)).fetchall()
        result[firma] = [dict(r) for r in rows]
    conn.close()
    return result


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
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

        layout.addWidget(section_title("⚙️ Ayarlar"))

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER}; border-radius: 8px; background: {BG_SURFACE};
            }}
            QTabBar::tab {{
                background: {BG_BASE}; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-bottom: none;
                padding: 8px 20px; font-size: 13px; border-radius: 6px 6px 0 0;
            }}
            QTabBar::tab:selected {{
                background: {BG_SURFACE}; color: {ACCENT_BLUE};
                border-bottom: 2px solid {ACCENT_BLUE};
            }}
        """)

        tabs.addTab(self._build_cargo_tab(), "Kargo Fiyatları")
        tabs.addTab(self._build_general_tab(), "Genel")
        layout.addWidget(tabs)

    def _build_cargo_tab(self):
        tab = QWidget()
        tab.setStyleSheet(f"background: {BG_SURFACE};")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Kargo Fiyat Listesi Güncelle")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("Trendyol'dan gelen güncel kargo fiyat PDF'ini yükleyin.\nSistem TEX, DHL eCommerce ve Aras sütunlarını otomatik okur.")
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(desc)

        # Son güncelleme tarihleri
        self.dates_frame = QFrame()
        self.dates_frame.setStyleSheet(f"background: {BG_INPUT}; border-radius: 6px; border: 1px solid {BORDER};")
        dates_layout = QHBoxLayout(self.dates_frame)
        dates_layout.setContentsMargins(16, 12, 16, 12)

        self.date_labels = {}
        for i, firma in enumerate(["TEX", "DHL eCommerce", "Aras"]):
            tarih = get_cargo_update_date(firma)
            vbox = QVBoxLayout()
            lbl1 = QLabel(firma)
            lbl1.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
            lbl2 = QLabel(tarih if tarih else "Henüz yüklenmedi")
            lbl2.setStyleSheet(f"color: {ACCENT_GREEN if tarih else ACCENT_RED}; font-size: 13px;")
            self.date_labels[firma] = lbl2
            vbox.addWidget(lbl1)
            vbox.addWidget(lbl2)
            dates_layout.addLayout(vbox)
            if i < 2:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setStyleSheet(f"color: {BORDER};")
                dates_layout.addWidget(sep)
        layout.addWidget(self.dates_frame)

        # Fiyat önizleme tablosu
        preview_lbl = QLabel("Yüklü Fiyatlar (ilk 10 desi)")
        preview_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: bold;")
        layout.addWidget(preview_lbl)

        self.preview_table = QTableWidget()
        self.preview_table.setStyleSheet(TABLE_STYLE + f"QTableWidget {{ background: {BG_BASE}; }}")
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["Desi", "TEX (₺)", "DHL eCommerce (₺)", "Aras (₺)"])
        self.preview_table.setFixedHeight(220)
        self.preview_table.setShowGrid(False)
        for i in range(4):
            self.preview_table.setColumnWidth(i, 120)
        layout.addWidget(self.preview_table)
        self._refresh_preview()

        # Upload alanı
        upload_frame = QFrame()
        upload_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG_INPUT};
                border: 2px dashed {BORDER};
                border-radius: 8px;
            }}
        """)
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(20, 20, 20, 20)
        upload_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upload_layout.setSpacing(10)

        self.file_lbl = QLabel("PDF dosyası seçin")
        self.file_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")
        self.file_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upload_layout.addWidget(self.file_lbl)

        sel_btn = QPushButton("Dosya Seç")
        sel_btn.setStyleSheet(btn_secondary())
        sel_btn.setFixedWidth(140)
        sel_btn.clicked.connect(self._select_pdf)
        upload_layout.addWidget(sel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(upload_frame)

        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(f"background: {BG_INPUT}; border-radius: 6px; border: 1px solid {BORDER};")
        self.progress_frame.setVisible(False)
        prog_l = QVBoxLayout(self.progress_frame)
        prog_l.setContentsMargins(16, 12, 16, 12)
        self.prog_lbl = QLabel("İşleniyor...")
        self.prog_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self.prog_bar = QProgressBar()
        self.prog_bar.setStyleSheet(PROGRESS_STYLE)
        self.prog_bar.setFixedHeight(6)
        prog_l.addWidget(self.prog_lbl)
        prog_l.addWidget(self.prog_bar)
        layout.addWidget(self.progress_frame)

        self.upload_btn = QPushButton("Fiyatları Yükle ve Güncelle")
        self.upload_btn.setStyleSheet(btn_primary())
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self._upload_pdf)
        layout.addWidget(self.upload_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

        self.selected_pdf = None
        return tab

    def _build_general_tab(self):
        tab = QWidget()
        tab.setStyleSheet(f"background: {BG_SURFACE};")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Genel Ayarlar")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        kdv_row = QHBoxLayout()
        kdv_lbl = QLabel("KDV Oranı (%)")
        kdv_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        kdv_row.addWidget(kdv_lbl)
        kdv_row.addStretch()
        self.kdv_spin = QDoubleSpinBox()
        self.kdv_spin.setStyleSheet(INPUT_STYLE)
        self.kdv_spin.setRange(0, 100)
        self.kdv_spin.setDecimals(1)
        self.kdv_spin.setFixedWidth(120)
        self.kdv_spin.setValue(float(get_setting("kdv_orani", "20")))
        kdv_row.addWidget(self.kdv_spin)
        layout.addLayout(kdv_row)

        save_btn = QPushButton("Ayarları Kaydet")
        save_btn.setStyleSheet(btn_primary())
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return tab

    def _refresh_preview(self):
        samples = get_cargo_sample_prices()
        
        # Tüm firmalardan gelen desi değerlerini birleştir
        all_desi = set()
        for firma_data in samples.values():
            for r in firma_data:
                all_desi.add(r["desi"])
        
        if not all_desi:
            self.preview_table.setRowCount(1)
            self.preview_table.setItem(0, 0, QTableWidgetItem("Henüz veri yok"))
            return

        desi_list = sorted(all_desi)[:10]
        self.preview_table.setRowCount(len(desi_list))
        
        for i, desi in enumerate(desi_list):
            self.preview_table.setRowHeight(i, 36)
            self.preview_table.setItem(i, 0, QTableWidgetItem(str(desi)))
            for j, firma in enumerate(["TEX", "DHL eCommerce", "Aras"]):
                firma_data = {r["desi"]: r["fiyat"] for r in samples.get(firma, [])}
                fiyat = firma_data.get(desi)
                item = QTableWidgetItem(f"₺{fiyat:.2f}" if fiyat else "—")
                if not fiyat:
                    item.setForeground(QColor(TEXT_MUTED))
                else:
                    item.setForeground(QColor(ACCENT_GREEN))
                self.preview_table.setItem(i, j + 1, item)

    def _select_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Kargo Fiyat PDF", "", "PDF Dosyaları (*.pdf)")
        if path:
            self.selected_pdf = path
            fname = os.path.basename(path)
            self.file_lbl.setText(f"✓  {fname}")
            self.file_lbl.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 14px;")
            self.upload_btn.setEnabled(True)

    def _upload_pdf(self):
        if not self.selected_pdf:
            return
        self.upload_btn.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.prog_bar.setValue(0)

        self.thread = CargoPDFThread(self.selected_pdf)
        self.thread.progress.connect(lambda v, m: (self.prog_bar.setValue(v), self.prog_lbl.setText(m)))
        self.thread.finished.connect(self._on_finished)
        self.thread.error.connect(self._on_error)
        self.thread.start()

    def _on_finished(self, results):
        self.upload_btn.setEnabled(True)
        self.progress_frame.setVisible(False)

        # Tarihleri güncelle
        for firma, lbl in self.date_labels.items():
            tarih = get_cargo_update_date(firma)
            if tarih:
                lbl.setText(tarih)
                lbl.setStyleSheet(f"color: {ACCENT_GREEN}; font-size: 13px;")
            else:
                lbl.setText("Yüklenemedi")
                lbl.setStyleSheet(f"color: {ACCENT_RED}; font-size: 13px;")

        # Önizleme tablosunu temizle ve yeniden doldur
        self.preview_table.clearContents()
        self._refresh_preview()
        self.preview_table.viewport().update()

        msg = "\n".join([f"✓  {f}: {c} desi fiyatı" for f, c in results.items()])
        QMessageBox.information(self, "Başarılı", f"Kargo fiyatları güncellendi:\n\n{msg}")

    def _on_error(self, msg):
        self.upload_btn.setEnabled(True)
        self.progress_frame.setVisible(False)
        QMessageBox.critical(self, "Hata", f"PDF işlenemedi:\n\n{msg}")

    def _save_settings(self):
        set_setting("kdv_orani", str(self.kdv_spin.value()))
        QMessageBox.information(self, "Kaydedildi", "Ayarlar kaydedildi.")
