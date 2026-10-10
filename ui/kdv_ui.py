from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QDateEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from core.database import (get_kdv_ozet, get_gider_faturalari,
                            add_gider_fatura, delete_gider_fatura,
                            get_setting)
from ui.design import (CARD_STYLE, TABLE_STYLE, INPUT_STYLE, DIALOG_STYLE,
                        COMBO_STYLE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE,
                        BG_BASE, BG_SURFACE, BG_INPUT, BG_ELEVATED, BORDER,
                        btn_primary, btn_secondary, btn_danger, section_title)


class GiderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gider Faturası Ekle")
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_STYLE)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Gider Faturası Ekle")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 600;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            return l

        self.tarih_edit = QDateEdit()
        self.tarih_edit.setStyleSheet(INPUT_STYLE)
        self.tarih_edit.setDate(QDate.currentDate())
        self.tarih_edit.setCalendarPopup(True)
        form.addRow(lbl("Tarih"), self.tarih_edit)

        self.aciklama_edit = QLineEdit()
        self.aciklama_edit.setStyleSheet(INPUT_STYLE)
        self.aciklama_edit.setPlaceholderText("Örn: Kumaş alımı, Kargo faturası...")
        form.addRow(lbl("Açıklama"), self.aciklama_edit)

        self.tutar_spin = QDoubleSpinBox()
        self.tutar_spin.setStyleSheet(INPUT_STYLE)
        self.tutar_spin.setRange(0, 999999)
        self.tutar_spin.setDecimals(2)
        self.tutar_spin.setSuffix("  ₺")
        form.addRow(lbl("KDV Hariç Tutar"), self.tutar_spin)

        self.kdv_spin = QDoubleSpinBox()
        self.kdv_spin.setStyleSheet(INPUT_STYLE)
        self.kdv_spin.setRange(0, 999999)
        self.kdv_spin.setDecimals(2)
        self.kdv_spin.setSuffix("  ₺")
        form.addRow(lbl("KDV Tutarı"), self.kdv_spin)

        # Otomatik KDV hesapla
        def auto_kdv():
            kdv_oran = float(get_setting("kdv_orani", "20")) / 100
            self.kdv_spin.setValue(round(self.tutar_spin.value() * kdv_oran, 2))
        self.tutar_spin.editingFinished.connect(auto_kdv)

        layout.addLayout(form)

        info = QLabel("💡 KDV tutarını boş bırakırsanız otomatik hesaplanır (%20)")
        info.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(info)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("İptal")
        cancel.setStyleSheet(btn_secondary())
        cancel.clicked.connect(self.reject)
        save = QPushButton("Kaydet")
        save.setStyleSheet(btn_primary())
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _save(self):
        if not self.aciklama_edit.text().strip():
            QMessageBox.warning(self, "Hata", "Açıklama boş olamaz.")
            return
        if self.tutar_spin.value() == 0 and self.kdv_spin.value() == 0:
            QMessageBox.warning(self, "Hata", "Tutar giriniz.")
            return
        self.accept()

    def get_data(self):
        tarih = self.tarih_edit.date().toString("yyyy-MM-dd")
        tutar = self.tutar_spin.value()
        kdv   = self.kdv_spin.value()
        if kdv == 0 and tutar > 0:
            kdv = round(tutar * float(get_setting("kdv_orani","20")) / 100, 2)
        return {
            "tarih":     tarih,
            "aciklama":  self.aciklama_edit.text().strip(),
            "tutar":     tutar,
            "kdv_tutari": kdv,
        }


class KDVWidget(QWidget):
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

        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(28, 24, 28, 24)
        self.layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        header.addWidget(section_title("KDV Takibi"))
        header.addStretch()

        self.ay_combo = QComboBox()
        self.ay_combo.setStyleSheet(COMBO_STYLE)
        self.ay_combo.setMinimumWidth(160)
        self._fill_ay_combo()
        self.ay_combo.currentIndexChanged.connect(self.refresh)
        header.addWidget(QLabel("Dönem:"))
        header.addWidget(self.ay_combo)
        self.layout.addLayout(header)

        # KDV özet kartları
        self.ozet_frame = QFrame()
        ozet_layout = QHBoxLayout(self.ozet_frame)
        ozet_layout.setContentsMargins(0, 0, 0, 0)
        ozet_layout.setSpacing(12)
        self.layout.addWidget(self.ozet_frame)

        # İki kolon
        cols = QHBoxLayout()
        cols.setSpacing(20)

        # Sol — KDV detay
        sol = QFrame()
        sol.setObjectName("card")
        sol.setStyleSheet(CARD_STYLE)
        sol_l = QVBoxLayout(sol)
        sol_l.setContentsMargins(20, 18, 20, 18)
        sol_l.setSpacing(0)

        sol_title = QLabel("KDV Hesaplama Detayı")
        sol_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600; margin-bottom: 14px;")
        sol_l.addWidget(sol_title)

        self.kdv_table = QTableWidget()
        self.kdv_table.setStyleSheet(TABLE_STYLE)
        self.kdv_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.kdv_table.verticalHeader().setVisible(False)
        self.kdv_table.setColumnCount(2)
        self.kdv_table.setHorizontalHeaderLabels(["Kalem", "Tutar"])
        self.kdv_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.kdv_table.setColumnWidth(1, 120)
        self.kdv_table.setShowGrid(False)
        self.kdv_table.setFixedHeight(260)
        sol_l.addWidget(self.kdv_table)
        cols.addWidget(sol, 1)

        # Sağ — Gider faturaları
        sag = QFrame()
        sag.setObjectName("card")
        sag.setStyleSheet(CARD_STYLE)
        sag_l = QVBoxLayout(sag)
        sag_l.setContentsMargins(20, 18, 20, 18)
        sag_l.setSpacing(10)

        sag_header = QHBoxLayout()
        sag_title = QLabel("Gider Faturaları (Alış KDV'si)")
        sag_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        sag_header.addWidget(sag_title)
        sag_header.addStretch()
        add_btn = QPushButton("+ Fatura Ekle")
        add_btn.setStyleSheet(btn_primary())
        add_btn.clicked.connect(self._add_fatura)
        sag_header.addWidget(add_btn)
        sag_l.addLayout(sag_header)

        self.gider_table = QTableWidget()
        self.gider_table.setStyleSheet(TABLE_STYLE)
        self.gider_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.gider_table.verticalHeader().setVisible(False)
        self.gider_table.setColumnCount(5)
        self.gider_table.setHorizontalHeaderLabels(["Tarih", "Açıklama", "Tutar", "KDV", ""])
        self.gider_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.gider_table.setColumnWidth(0, 90)
        self.gider_table.setColumnWidth(2, 90)
        self.gider_table.setColumnWidth(3, 80)
        self.gider_table.setColumnWidth(4, 60)
        self.gider_table.setShowGrid(False)
        self.gider_table.setFixedHeight(220)
        sag_l.addWidget(self.gider_table)
        cols.addWidget(sag, 1)

        self.layout.addLayout(cols)

        # Beyanname notu
        self.beyan_frame = QFrame()
        self.beyan_frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(79,89,199,0.08);
                border: 1px solid rgba(79,89,199,0.2);
                border-radius: 8px;
            }}
        """)
        beyan_l = QHBoxLayout(self.beyan_frame)
        beyan_l.setContentsMargins(16, 12, 16, 12)
        self.beyan_lbl = QLabel()
        self.beyan_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        self.beyan_lbl.setWordWrap(True)
        beyan_l.addWidget(self.beyan_lbl)
        self.layout.addWidget(self.beyan_frame)
        self.layout.addStretch()

    def _fill_ay_combo(self):
        self.ay_combo.blockSignals(True)
        self.ay_combo.clear()
        self.ay_combo.addItem("Tümü", None)
        # Son 12 ayı ekle
        from datetime import date
        now = date.today()
        for i in range(12):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12; y -= 1
            ay_str = f"{y}-{m:02d}"
            ay_label = f"{['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'][m-1]} {y}"
            self.ay_combo.addItem(ay_label, ay_str)
        self.ay_combo.blockSignals(False)

    def refresh(self):
        ay = self.ay_combo.currentData()
        ozet = get_kdv_ozet(ay)
        self._fill_ozet_cards(ozet)
        self._fill_kdv_table(ozet)
        self._fill_gider_table(ay)
        self._update_beyan(ozet)

    def _fill_ozet_cards(self, ozet):
        # Kartları temizle
        for i in reversed(range(self.ozet_frame.layout().count())):
            w = self.ozet_frame.layout().itemAt(i).widget()
            if w:
                w.deleteLater()

        cards = [
            ("Hesaplanan KDV",  f"₺{ozet['hesaplanan_kdv']:,.2f}",  ACCENT_ORANGE),
            ("İndirilecek KDV", f"₺{ozet['indirilecek_kdv']:,.2f}", ACCENT_GREEN),
            ("Ödenecek KDV",    f"₺{ozet['odenecek_kdv']:,.2f}",    ACCENT_RED if ozet['odenecek_kdv'] > 0 else ACCENT_GREEN),
        ]
        for title, value, color in cards:
            frame = QFrame()
            frame.setObjectName("card")
            frame.setStyleSheet(f"""
                QFrame#card {{
                    background: {BG_SURFACE};
                    border: 1px solid {BORDER};
                    border-radius: 8px;
                    border-top: 3px solid {color};
                }}
            """)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(18, 14, 18, 14)
            fl.setSpacing(4)
            t = QLabel(title)
            t.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600; text-transform: uppercase; background: transparent;")
            v = QLabel(value)
            v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 600; background: transparent;")
            fl.addWidget(t)
            fl.addWidget(v)
            self.ozet_frame.layout().addWidget(frame)

    def _fill_kdv_table(self, ozet):
        rows = [
            ("Satış KDV'si (Hesaplanan)",     ozet["hesaplanan_kdv"],  True,  False),
            ("— Komisyon KDV'si",              ozet["komisyon_kdv"],    False, True),
            ("— Kargo KDV'si",                 ozet["kargo_kdv"],       False, True),
            ("— Platform Hizmet KDV'si",       ozet["platform_kdv"],    False, True),
            ("— Alış Fatura KDV'si",           ozet["alis_kdv"],        False, True),
            ("İndirilecek KDV (Toplam)",       ozet["indirilecek_kdv"], True,  False),
            ("ÖDENECEK NET KDV",               ozet["odenecek_kdv"],    True,  False),
        ]
        self.kdv_table.setRowCount(len(rows))
        for i, (lbl, val, bold, indent) in enumerate(rows):
            self.kdv_table.setRowHeight(i, 36)
            lbl_item = QTableWidgetItem(lbl)
            if bold:
                font = lbl_item.font()
                font.setBold(True)
                lbl_item.setFont(font)
            if indent:
                lbl_item.setForeground(QColor(TEXT_MUTED))
            self.kdv_table.setItem(i, 0, lbl_item)

            sign = "-" if indent else ""
            val_item = QTableWidgetItem(f"{sign}₺{val:,.2f}")
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if i == len(rows) - 1:
                val_item.setForeground(QColor(ACCENT_RED if val > 0 else ACCENT_GREEN))
                font = val_item.font()
                font.setBold(True)
                val_item.setFont(font)
            elif indent:
                val_item.setForeground(QColor(ACCENT_GREEN))
            self.kdv_table.setItem(i, 1, val_item)

    def _fill_gider_table(self, ay):
        faturalar = get_gider_faturalari(ay)
        self.gider_table.setRowCount(len(faturalar))
        for i, f in enumerate(faturalar):
            self.gider_table.setRowHeight(i, 36)
            self.gider_table.setItem(i, 0, QTableWidgetItem(str(f.get("tarih",""))[:10]))
            self.gider_table.setItem(i, 1, QTableWidgetItem(f.get("aciklama","")))
            self.gider_table.setItem(i, 2, QTableWidgetItem(f"₺{f.get('tutar',0):.2f}"))
            kdv_item = QTableWidgetItem(f"₺{f.get('kdv_tutari',0):.2f}")
            kdv_item.setForeground(QColor(ACCENT_GREEN))
            self.gider_table.setItem(i, 3, kdv_item)

            del_btn = QPushButton("Sil")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {ACCENT_RED};
                    border: 1px solid {BORDER}; border-radius: 4px;
                    padding: 2px 8px; font-size: 11px;
                }}
                QPushButton:hover {{ background: rgba(224,79,95,0.1); }}
            """)
            del_btn.clicked.connect(lambda _, fid=f["id"]: self._del_fatura(fid))
            w = QWidget(); w.setStyleSheet("background: transparent;")
            wl = QHBoxLayout(w); wl.setContentsMargins(4,2,4,2)
            wl.addWidget(del_btn)
            self.gider_table.setCellWidget(i, 4, w)

    def _update_beyan(self, ozet):
        now = datetime.now()
        son_gun = 28
        self.beyan_lbl.setText(
            f"📋  KDV beyannamesi her ayın {son_gun}. günü akşamına kadar verilmelidir.  "
            f"Ödenecek KDV: ₺{ozet['odenecek_kdv']:,.2f}  |  "
            f"Sipariş sayısı: {ozet['siparis_sayisi']}"
        )

    def _add_fatura(self):
        dlg = GiderDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            add_gider_fatura(d["tarih"], d["aciklama"], d["tutar"], d["kdv_tutari"])
            self.refresh()

    def _del_fatura(self, fatura_id):
        reply = QMessageBox.question(self, "Sil", "Bu fatura silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_gider_fatura(fatura_id)
            self.refresh()
