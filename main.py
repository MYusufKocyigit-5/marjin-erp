import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QStackedWidget, QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from ui.dashboard_ui import DashboardWidget
from ui.import_ui import ImportWidget, ImportHistoryWidget
from ui.products_ui import ProductsWidget
from ui.orders_ui import OrdersWidget
from ui.packaging_ui import PackagingWidget
from ui.materials_ui import MaterialsWidget
from ui.settings_ui import SettingsWidget
from ui.kdv_ui import KDVWidget
from ui.rapor_ui import RaporWidget
from core.database import initialize_db
from ui.design import (APP_STYLE, SIDEBAR_STYLE, NAV_BTN_STYLE,
                        BG_BASE, BG_SURFACE, BORDER, TEXT_PRIMARY,
                        TEXT_SECONDARY, TEXT_MUTED, ACCENT_BLUE)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        initialize_db()
        self.setWindowTitle("Marjin ERP — Sipariş & Kâr/Zarar Paneli")
        self.setMinimumSize(1280, 780)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background: {BG_BASE};")
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {BG_BASE};")

        self.dashboard    = DashboardWidget()
        self.import_w     = ImportWidget(on_import_complete=self._on_import)
        self.import_hist  = ImportHistoryWidget()
        self.products     = ProductsWidget()
        self.orders       = OrdersWidget()
        self.packaging    = PackagingWidget()
        self.materials    = MaterialsWidget()
        self.kdv_w        = KDVWidget()
        self.rapor_w      = RaporWidget()
        self.settings_w   = SettingsWidget()

        for w in [self.dashboard, self.import_w, self.import_hist,
                  self.products, self.orders, self.packaging,
                  self.materials, self.kdv_w, self.rapor_w, self.settings_w]:
            self.stack.addWidget(w)

        layout.addWidget(self.stack, 1)

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet(SIDEBAR_STYLE)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo = QWidget()
        logo.setFixedHeight(60)
        logo.setStyleSheet(f"background: transparent; border-bottom: 1px solid #252830;")
        logo_l = QVBoxLayout(logo)
        logo_l.setContentsMargins(22, 0, 0, 0)
        logo_l.setSpacing(2)
        t1 = QLabel("Marjin ERP")
        t1.setStyleSheet(f"color: #E8EAF0; font-size: 15px; font-weight: 600; letter-spacing: -0.3px;")
        t2 = QLabel("Sipariş Paneli")
        t2.setStyleSheet(f"color: #5B6CE2; font-size: 11px; font-weight: 500; letter-spacing: 0.2px;")
        logo_l.addWidget(t1)
        logo_l.addWidget(t2)
        layout.addWidget(logo)

        layout.addSpacing(4)

        self.nav_btns = []

        # ── OPERATIONS
        grp1 = QLabel("OPERATIONS")
        grp1.setStyleSheet(f"color: #525B6E; font-size: 10px; font-weight: 600; letter-spacing: 1.4px; padding: 14px 22px 4px 22px; background: transparent;")
        layout.addWidget(grp1)
        for text, index in [("Dashboard",0),("Excel İçe Aktar",1),("Import Geçmişi",2)]:
            btn = QPushButton(text); btn.setCheckable(True); btn.setStyleSheet(NAV_BTN_STYLE)
            btn.clicked.connect(lambda _, i=index: self._navigate(i))
            layout.addWidget(btn); self.nav_btns.append(btn)

        # ── CATALOGUE
        sep1 = QWidget(); sep1.setFixedHeight(1); sep1.setStyleSheet(f"background: #252830; margin: 0 16px;")
        layout.addWidget(sep1)
        grp2 = QLabel("CATALOGUE")
        grp2.setStyleSheet(f"color: #525B6E; font-size: 10px; font-weight: 600; letter-spacing: 1.4px; padding: 14px 22px 4px 22px; background: transparent;")
        layout.addWidget(grp2)
        for text, index in [("Ürün Maliyetleri",3),("Siparişler",4),("Paketleme",5),("Hammadde",6)]:
            btn = QPushButton(text); btn.setCheckable(True); btn.setStyleSheet(NAV_BTN_STYLE)
            btn.clicked.connect(lambda _, i=index: self._navigate(i))
            layout.addWidget(btn); self.nav_btns.append(btn)

        # ── FINANCE
        sep2 = QWidget(); sep2.setFixedHeight(1); sep2.setStyleSheet(f"background: #252830; margin: 0 16px;")
        layout.addWidget(sep2)
        grp3 = QLabel("FINANCE")
        grp3.setStyleSheet(f"color: #525B6E; font-size: 10px; font-weight: 600; letter-spacing: 1.4px; padding: 14px 22px 4px 22px; background: transparent;")
        layout.addWidget(grp3)
        for text, index in [("KDV Takibi",7),("Raporlar",8)]:
            btn = QPushButton(text); btn.setCheckable(True); btn.setStyleSheet(NAV_BTN_STYLE)
            btn.clicked.connect(lambda _, i=index: self._navigate(i))
            layout.addWidget(btn); self.nav_btns.append(btn)

        self.nav_btns[0].setChecked(True)
        layout.addStretch()

        sep3 = QWidget(); sep3.setFixedHeight(1)
        sep3.setStyleSheet("background: #252830; margin: 0 16px;")
        layout.addWidget(sep3)

        settings_btn = QPushButton("Ayarlar")
        settings_btn.setCheckable(True)
        settings_btn.setStyleSheet(NAV_BTN_STYLE)
        settings_btn.clicked.connect(lambda: self._navigate(9))
        layout.addWidget(settings_btn)
        self.nav_btns.append(settings_btn)

        ver = QLabel("v2.7.0")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet(f"color: #525B6E; font-size: 10px; padding: 10px; letter-spacing: 0.5px;")
        layout.addWidget(ver)

        return sidebar

    def _navigate(self, index):
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.dashboard.refresh()
        elif index == 2:
            self.import_hist.refresh()
        elif index == 4:
            self.orders.refresh()
        elif index == 6:
            self.materials.refresh()
        elif index == 7:
            self.kdv_w.refresh()

    def _on_import(self):
        self.dashboard.refresh()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Marjin ERP")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor("#0E0F11")) # BG_BASE
    palette.setColor(QPalette.ColorRole.WindowText,      QColor("#EDEDEF")) # TEXT_PRIMARY
    palette.setColor(QPalette.ColorRole.Base,            QColor("#161719")) # BG_SURFACE (for some widgets default)
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#1D1E20")) # BG_ELEVATED
    palette.setColor(QPalette.ColorRole.Text,            QColor("#EDEDEF")) # TEXT_PRIMARY
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#EDEDEF")) # TEXT_PRIMARY
    palette.setColor(QPalette.ColorRole.Button,          QColor("#161719")) # BG_SURFACE
    palette.setColor(QPalette.ColorRole.Highlight,       QColor("#4F59C7")) # ACCENT_BLUE
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
