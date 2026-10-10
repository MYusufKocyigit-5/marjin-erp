from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from core.database import get_dashboard_summary, get_critical_materials
from ui.design import (CARD_STYLE, TABLE_STYLE, COMBO_STYLE, TEXT_PRIMARY,
                        TEXT_SECONDARY, TEXT_MUTED, ACCENT_BLUE, ACCENT_GREEN,
                        ACCENT_RED, ACCENT_ORANGE, BG_BASE, BG_SURFACE, BG_INPUT,
                        BORDER, ACCENT_PURPLE, make_metric_card, section_title,
                        btn_secondary)


class ChartWidget(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(8, 2.8), facecolor="#161b22")
        super().__init__(self.fig)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(220)
        self.fig.patch.set_facecolor("#161b22")

    def plot(self, chart_data):
        self.fig.clear()
        ax = self.fig.add_subplot(111, facecolor="#161b22")

        if not chart_data:
            ax.text(0.5, 0.5, "Henüz veri yok", color="#484f58",
                    ha="center", va="center", transform=ax.transAxes, fontsize=13)
            self.draw()
            return

        labels = [d["tarih"][:10] if d["tarih"] else "" for d in chart_data]
        ciro   = [d["ciro"] or 0 for d in chart_data]
        kar    = [d["kar"]  or 0 for d in chart_data]
        x = range(len(labels))
        w = 0.38

        ax.bar([i - w/2 for i in x], ciro, w, color=ACCENT_BLUE,
               alpha=0.7, label="Ciro", zorder=3)
        ax.bar([i + w/2 for i in x], kar, w, color=ACCENT_GREEN,
               alpha=0.85, label="Net Kar", zorder=3)

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30, ha="right",
                           color="#8b949e", fontsize=8)
        ax.tick_params(colors="#8b949e", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#30363d")
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#1c2128", linewidth=0.8)
        ax.set_ylabel("₺", color="#8b949e", fontsize=9)
        ax.legend(facecolor="#161b22", edgecolor="#30363d",
                  labelcolor="#e6edf3", fontsize=9)
        self.fig.tight_layout(pad=1.2)
        self.draw()


class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        QTimer.singleShot(100, self.refresh)

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

        self.layout_main = QVBoxLayout(content)
        self.layout_main.setContentsMargins(28, 24, 28, 24)
        self.layout_main.setSpacing(18)

        # Header
        header_row = QHBoxLayout()
        header_row.addWidget(section_title("Dashboard"))
        header_row.addStretch()
        self.period_combo = QComboBox()
        self.period_combo.setStyleSheet(COMBO_STYLE)
        self.period_combo.addItems(["Bu Ay", "Bu Hafta", "Bugün", "Tümü"])
        self.period_combo.currentIndexChanged.connect(self.refresh)
        header_row.addWidget(self.period_combo)
        self.layout_main.addLayout(header_row)

        # Hammadde uyarı kartı
        self.mat_alert = QFrame()
        self.mat_alert.setStyleSheet(f"""
            QFrame {{
                background: rgba(248,81,73,0.08);
                border: 1px solid rgba(248,81,73,0.35);
                border-radius: 8px;
            }}
        """)
        mat_l = QHBoxLayout(self.mat_alert)
        mat_l.setContentsMargins(16, 10, 16, 10)
        self.mat_alert_lbl = QLabel("")
        self.mat_alert_lbl.setStyleSheet(f"color: {ACCENT_RED}; font-size: 12px; background: transparent;")
        self.mat_alert_lbl.setWordWrap(True)
        mat_l.addWidget(self.mat_alert_lbl)
        self.mat_alert.setVisible(False)
        self.layout_main.addWidget(self.mat_alert)

        # Metrik kartlar — 5 adet
        self.cards_row = QHBoxLayout()
        self.cards_row.setSpacing(12)

        self.card_ciro,    self.v_ciro    = make_metric_card("Toplam Ciro", "₺0", "KDV dahil")
        self.card_kdv,     self.v_kdv     = make_metric_card("KDV (%20)", "₺0", "Ciroda gömülü", ACCENT_ORANGE)
        self.card_kar,     self.v_kar     = make_metric_card("Net Kar", "₺0", "Tüm giderler düşüldükten sonra", ACCENT_GREEN)
        self.card_siparis, self.v_siparis = make_metric_card("Sipariş", "0", "Dönem toplam", ACCENT_BLUE)
        self.card_marj,    self.v_marj    = make_metric_card("Kar Marjı", "%0", "Net kar / KDV hariç ciro", ACCENT_PURPLE)

        for card in [self.card_ciro, self.card_kdv, self.card_kar,
                     self.card_siparis, self.card_marj]:
            self.cards_row.addWidget(card)
        self.layout_main.addLayout(self.cards_row)

        # Grafik
        chart_frame = QFrame()
        chart_frame.setObjectName("card")
        chart_frame.setStyleSheet(CARD_STYLE)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 14, 16, 10)

        chart_header = QHBoxLayout()
        chart_title = QLabel("Günlük Ciro & Kar")
        chart_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: bold;")
        chart_header.addWidget(chart_title)
        chart_header.addStretch()
        chart_layout.addLayout(chart_header)

        self.chart = ChartWidget()
        chart_layout.addWidget(self.chart)
        self.layout_main.addWidget(chart_frame)

        # En karlı ürünler
        tbl_frame = QFrame()
        tbl_frame.setObjectName("card")
        tbl_frame.setStyleSheet(CARD_STYLE)
        tbl_layout = QVBoxLayout(tbl_frame)
        tbl_layout.setContentsMargins(16, 14, 16, 0)

        tbl_title = QLabel("En Karlı Ürünler")
        tbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: bold; margin-bottom: 8px;")
        tbl_layout.addWidget(tbl_title)

        self.top_table = QTableWidget()
        self.top_table.setStyleSheet(TABLE_STYLE + f"""
            QTableWidget {{ background: {BG_SURFACE}; }}
        """)
        self.top_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.top_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setColumnCount(5)
        self.top_table.setHorizontalHeaderLabels(
            ["Stok Kodu", "Ürün Adı", "Adet", "Ciro (₺)", "Net Kar (₺)"])
        self.top_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.top_table.setColumnWidth(0, 110)
        self.top_table.setColumnWidth(2, 70)
        self.top_table.setColumnWidth(3, 110)
        self.top_table.setColumnWidth(4, 110)
        self.top_table.setFixedHeight(260)
        self.top_table.setShowGrid(False)
        tbl_layout.addWidget(self.top_table)
        self.layout_main.addWidget(tbl_frame)

    def _period_key(self):
        return {"Bu Ay":"month","Bu Hafta":"week","Bugün":"day","Tümü":"all"}.get(
            self.period_combo.currentText(), "month")

    def refresh(self):
        data = get_dashboard_summary(self._period_key())
        s = data["summary"]

        ciro    = s.get("toplam_ciro") or 0
        kdv     = s.get("toplam_kdv")  or 0
        kar     = s.get("toplam_kar")  or 0
        siparis = s.get("siparis_sayisi") or 0
        marj    = s.get("kar_marji")   or 0

        self.v_ciro.setText(f"₺{ciro:,.0f}")
        self.v_kdv.setText(f"₺{kdv:,.0f}")
        self.v_kar.setText(f"₺{kar:,.0f}")
        self.v_kar.setStyleSheet(
            f"color: {ACCENT_GREEN if kar >= 0 else ACCENT_RED}; font-size: 24px; font-weight: bold; background: transparent;")
        self.v_siparis.setText(str(siparis))
        self.v_marj.setText(f"%{marj:.1f}")

        self.chart.plot(data["chart_data"])

        # Top products
        products = data["top_products"]
        self.top_table.setRowCount(len(products))
        for i, p in enumerate(products):
            self.top_table.setRowHeight(i, 38)
            self.top_table.setItem(i, 0, QTableWidgetItem(str(p.get("stok_kodu",""))))
            self.top_table.setItem(i, 1, QTableWidgetItem(str(p.get("urun_adi",""))[:55]))
            self.top_table.setItem(i, 2, QTableWidgetItem(str(p.get("toplam_adet",0))))
            self.top_table.setItem(i, 3, QTableWidgetItem(f"₺{p.get('toplam_ciro',0):,.0f}"))
            kar_val = p.get("toplam_kar",0) or 0
            kar_item = QTableWidgetItem(f"₺{kar_val:,.0f}")
            kar_item.setForeground(QColor(ACCENT_GREEN if kar_val >= 0 else ACCENT_RED))
            self.top_table.setItem(i, 4, kar_item)

        # Hammadde uyarı
        criticals = get_critical_materials()
        if criticals:
            names = ", ".join([f"{m['ad']} {m.get('varyant','')}".strip() for m in criticals])
            self.mat_alert_lbl.setText(f"⚠  Kritik hammadde stoku: {names}")
            self.mat_alert.setVisible(True)
        else:
            self.mat_alert.setVisible(False)
