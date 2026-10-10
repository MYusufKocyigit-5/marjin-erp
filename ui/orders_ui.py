from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.database import get_orders_for_table
from ui.design import (CARD_STYLE, TABLE_STYLE, COMBO_STYLE, INPUT_STYLE,
                        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
                        ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE, ACCENT_BLUE,
                        BG_BASE, BG_SURFACE, BG_INPUT, BORDER,
                        section_title)


class OrdersWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._orders_data = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        main = QWidget()
        main.setStyleSheet(f"background: {BG_BASE};")
        layout = QVBoxLayout(main)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        outer.addWidget(main)

        # Header
        header = QHBoxLayout()
        header.addWidget(section_title("Siparişler"))
        header.addStretch()
        layout.addLayout(header)

        # Filtreler
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        lbl = QLabel("Dönem:")
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        filter_row.addWidget(lbl)

        self.period_combo = QComboBox()
        self.period_combo.setStyleSheet(COMBO_STYLE)
        self.period_combo.addItems(["Bu Ay", "Bu Hafta", "Bugün", "Tümü"])
        self.period_combo.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.period_combo)

        self.search_box = QLineEdit()
        self.search_box.setStyleSheet(INPUT_STYLE)
        self.search_box.setPlaceholderText("Stok kodu veya ürün adı ara...")
        self.search_box.setFixedWidth(260)
        self.search_box.textChanged.connect(self._filter_table)
        filter_row.addWidget(self.search_box)
        filter_row.addStretch()

        self.count_label = QLabel("0 sipariş")
        self.count_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        filter_row.addWidget(self.count_label)
        layout.addLayout(filter_row)

        # Özet şerit
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG_SURFACE};
                border-radius: 8px;
                border: 1px solid {BORDER};
            }}
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(16, 10, 16, 10)
        summary_layout.setSpacing(32)

        self.sum_ciro     = self._make_sum("Toplam Ciro", "₺0")
        self.sum_kdv      = self._make_sum("KDV", "₺0", ACCENT_ORANGE)
        self.sum_komisyon = self._make_sum("Komisyon", "₺0")
        self.sum_kargo    = self._make_sum("Kargo", "₺0")
        self.sum_maliyet  = self._make_sum("Maliyet", "₺0")
        self.sum_kar      = self._make_sum("Net Kar", "₺0", ACCENT_GREEN)

        for pair in [self.sum_ciro, self.sum_kdv, self.sum_komisyon,
                     self.sum_kargo, self.sum_maliyet, self.sum_kar]:
            vbox = QVBoxLayout()
            vbox.setSpacing(2)
            vbox.addWidget(pair[0])
            vbox.addWidget(pair[1])
            summary_layout.addLayout(vbox)
        summary_layout.addStretch()
        layout.addWidget(self.summary_frame)

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
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(False)

        cols = ["Tarih", "Sipariş No", "Stok Kodu", "Ürün Adı", "Adet",
                "Fiyat", "Faturalanacak", "KDV", "KDV Hariç",
                "Komisyon", "Kargo", "Koli", "Maliyet", "Net Kar", "Durum"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 95)
        self.table.setColumnWidth(1, 115)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(4, 50)

        frame_layout.addWidget(self.table)
        layout.addWidget(frame)

    def _make_sum(self, title, value, color=None):
        t = QLabel(title)
        t.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {color or TEXT_SECONDARY}; font-size: 14px; font-weight: bold;")
        return t, v

    def _period_key(self):
        return {"Bu Ay":"month","Bu Hafta":"week","Bugün":"day","Tümü":"all"}.get(
            self.period_combo.currentText(), "month")

    def refresh(self):
        self._orders_data = get_orders_for_table(self._period_key())
        self._fill_table(self._orders_data)

    def _filter_table(self, text):
        if not text:
            self._fill_table(self._orders_data)
            return
        t = text.lower()
        filtered = [o for o in self._orders_data
                    if t in str(o.get("stok_kodu","")).lower()
                    or t in str(o.get("urun_adi","")).lower()]
        self._fill_table(filtered)

    def _fill_table(self, orders):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(orders))

        tc = tk = tko = tka = tm = tkar = 0

        for i, o in enumerate(orders):
            self.table.setRowHeight(i, 38)
            self.table.setItem(i, 0,  QTableWidgetItem(str(o.get("siparis_tarihi",""))[:10]))
            self.table.setItem(i, 1,  QTableWidgetItem(str(o.get("siparis_no",""))))
            self.table.setItem(i, 2,  QTableWidgetItem(str(o.get("stok_kodu",""))))
            self.table.setItem(i, 3,  QTableWidgetItem(str(o.get("urun_adi",""))[:50]))
            self.table.setItem(i, 4,  QTableWidgetItem(str(o.get("adet",""))))
            self.table.setItem(i, 5,  QTableWidgetItem(f"₺{o.get('birim_fiyat',0):.2f}"))

            fatura  = o.get("faturalanacak_tutar",0) or 0
            kdv     = o.get("kdv_tutari",0) or 0
            kdvsiz  = o.get("faturalanacak_kdvsiz",0) or 0
            kom     = o.get("komisyon_tutari",0) or 0
            kargo   = o.get("kargo_hesaplanan",0) or 0
            koli    = o.get("koli_maliyet",0) or 0
            maliyet = (o.get("alis_maliyeti",0) or 0) * (o.get("adet",1) or 1)
            kar     = o.get("net_kar",0) or 0

            self.table.setItem(i, 6,  QTableWidgetItem(f"₺{fatura:.2f}"))
            kdv_item = QTableWidgetItem(f"₺{kdv:.2f}")
            kdv_item.setForeground(QColor(ACCENT_ORANGE))
            self.table.setItem(i, 7,  kdv_item)
            self.table.setItem(i, 8,  QTableWidgetItem(f"₺{kdvsiz:.2f}"))
            self.table.setItem(i, 9,  QTableWidgetItem(f"₺{kom:.2f}"))
            self.table.setItem(i, 10, QTableWidgetItem(f"₺{kargo:.2f}"))
            self.table.setItem(i, 11, QTableWidgetItem(f"₺{koli:.2f}"))
            self.table.setItem(i, 12, QTableWidgetItem(f"₺{maliyet:.2f}"))

            kar_item = QTableWidgetItem(f"₺{kar:.2f}")
            kar_item.setForeground(QColor(ACCENT_GREEN if kar >= 0 else ACCENT_RED))
            self.table.setItem(i, 13, kar_item)
            self.table.setItem(i, 14, QTableWidgetItem(str(o.get("siparis_durumu",""))))

            tc += fatura; tk += kdv; tko += kom
            tka += kargo; tm += maliyet; tkar += kar

        self.table.setSortingEnabled(True)
        self.count_label.setText(f"{len(orders)} sipariş")

        self.sum_ciro[1].setText(f"₺{tc:,.0f}")
        self.sum_kdv[1].setText(f"₺{tk:,.0f}")
        self.sum_komisyon[1].setText(f"₺{tko:,.0f}")
        self.sum_kargo[1].setText(f"₺{tka:,.0f}")
        self.sum_maliyet[1].setText(f"₺{tm:,.0f}")
        self.sum_kar[1].setText(f"₺{tkar:,.0f}")
        self.sum_kar[1].setStyleSheet(
            f"color: {ACCENT_GREEN if tkar>=0 else ACCENT_RED}; font-size: 14px; font-weight: bold;")
