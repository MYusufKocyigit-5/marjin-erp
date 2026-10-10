# Marjin ERP — Enterprise ERP Design System
# Inspired by: SAP Fiori Horizon, Linear, Dynamics 365, Odoo
# VISUAL ONLY — zero logic changes

# ── COLOUR TOKENS ────────────────────────────────────────────────────────────
BG_BASE      = "#111318"
BG_SURFACE   = "#181B21"
BG_ELEVATED  = "#1F2229"
BG_INPUT     = "#181B21"
BG_SIDEBAR   = "#0D0F13"

BORDER       = "#252830"
BORDER_MED   = "#2E3240"
BORDER_FOCUS = "#5B6CE2"

TEXT_PRIMARY   = "#E8EAF0"
TEXT_SECONDARY = "#8892A4"
TEXT_MUTED     = "#525B6E"

ACCENT_BLUE   = "#5B6CE2"
ACCENT_GREEN  = "#2DB87D"
ACCENT_RED    = "#E05C6C"
ACCENT_ORANGE = "#D98A3A"
ACCENT_PURPLE = "#9B6FE8"

SIDEBAR_BG     = BG_SIDEBAR
SIDEBAR_ACTIVE = "rgba(91, 108, 226, 0.10)"
SIDEBAR_HOVER  = "rgba(255, 255, 255, 0.04)"

APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 13px;
}}
QScrollArea  {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 5px; border-radius: 3px; margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_MED}; border-radius: 3px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 5px; border-radius: 3px; margin: 0 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_MED}; border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{ background: {TEXT_MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QToolTip {{
    background-color: {BG_ELEVATED}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MED}; border-radius: 5px;
    padding: 5px 10px; font-size: 12px;
}}
"""

SIDEBAR_STYLE = f"""
QWidget#sidebar {{
    background-color: {BG_SIDEBAR};
    border-right: 1px solid {BORDER};
}}
"""

NAV_BTN_STYLE = f"""
QPushButton {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-left: 2px solid transparent;
    text-align: left;
    padding: 9px 16px 9px 22px;
    margin: 1px 6px;
    font-size: 13px;
    font-weight: 400;
    border-radius: 0px 6px 6px 0px;
}}
QPushButton:hover {{
    background-color: {SIDEBAR_HOVER};
    color: {TEXT_PRIMARY};
    border-left: 2px solid {BORDER_MED};
}}
QPushButton:checked {{
    background-color: {SIDEBAR_ACTIVE};
    color: {ACCENT_BLUE};
    border-left: 2px solid {ACCENT_BLUE};
    font-weight: 500;
}}
"""

NAV_GROUP_STYLE = f"""
QLabel {{
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.4px;
    padding: 16px 22px 5px 22px;
    background: transparent;
}}
"""

DIVIDER_STYLE = f"background: {BORDER}; max-height: 1px; min-height: 1px; margin: 0 6px;"

CARD_STYLE = f"""
QFrame#card {{
    background-color: {BG_SURFACE};
    border-radius: 8px;
    border: 1px solid {BORDER};
}}
"""

TABLE_STYLE = f"""
QTableWidget {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: none;
    gridline-color: transparent;
    font-size: 13px;
    outline: none;
}}
QTableWidget::item {{
    padding: 0px 14px;
    border: none;
    border-bottom: 1px solid {BORDER};
    height: 44px;
}}
QTableWidget::item:selected {{
    background-color: rgba(91, 108, 226, 0.12);
    color: {TEXT_PRIMARY};
}}
QTableWidget::item:hover {{
    background-color: {BG_ELEVATED};
}}
QHeaderView::section {{
    background-color: {BG_SURFACE};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 0px 14px;
    height: 38px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
}}
QHeaderView::section:hover {{ background-color: {BG_ELEVATED}; color: {TEXT_SECONDARY}; }}
QTableCornerButton::section {{ background-color: {BG_SURFACE}; border: none; }}
"""

COMBO_STYLE = f"""
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MED};
    border-radius: 6px;
    padding: 6px 32px 6px 12px;
    font-size: 13px;
    min-width: 140px;
}}
QComboBox:hover {{ border-color: {TEXT_MUTED}; }}
QComboBox:focus {{ border-color: {BORDER_FOCUS}; outline: none; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MED};
    border-radius: 6px;
    selection-background-color: {SIDEBAR_ACTIVE};
    outline: none;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    border-radius: 4px;
    padding: 7px 10px;
    min-height: 28px;
}}
"""

INPUT_STYLE = f"""
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MED};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    selection-background-color: rgba(91,108,226,0.3);
}}
QLineEdit:hover, QTextEdit:hover, QSpinBox:hover,
QDoubleSpinBox:hover, QDateEdit:hover {{ border-color: {TEXT_MUTED}; }}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QDateEdit:focus {{
    border-color: {BORDER_FOCUS};
    background-color: {BG_ELEVATED};
    outline: none;
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button,
QDateEdit::up-button, QDateEdit::down-button {{
    background: transparent; border: none; width: 20px;
}}
QDateEdit::drop-down {{ border: none; width: 24px; }}
"""

DIALOG_STYLE = f"""
QDialog {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER_MED};
    border-radius: 10px;
}}
QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    background: transparent;
}}
QLineEdit, QTextEdit, QDoubleSpinBox, QSpinBox, QDateEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MED};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus,
QDateEdit:focus {{ border-color: {BORDER_FOCUS}; outline: none; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button,
QDateEdit::up-button, QDateEdit::down-button {{
    background: transparent; border: none; width: 20px;
}}
QDateEdit::drop-down {{ border: none; width: 24px; }}
"""

PROGRESS_STYLE = f"""
QProgressBar {{
    background-color: {BG_ELEVATED};
    border-radius: 3px; height: 4px;
    color: transparent; border: none;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_BLUE}; border-radius: 3px;
}}
"""

def btn_primary():
    return f"""
    QPushButton {{
        background-color: {ACCENT_BLUE};
        color: #ffffff; border: none; border-radius: 6px;
        padding: 7px 18px; font-size: 13px; font-weight: 500;
    }}
    QPushButton:hover   {{ background-color: #6B7CEE; }}
    QPushButton:pressed {{ background-color: #4A5AC0; }}
    QPushButton:disabled {{ background-color: {BG_ELEVATED}; color: {TEXT_MUTED}; border: 1px solid {BORDER}; }}
    """

def btn_secondary():
    return f"""
    QPushButton {{
        background-color: transparent; color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_MED}; border-radius: 6px;
        padding: 6px 16px; font-size: 13px; font-weight: 400;
    }}
    QPushButton:hover   {{ background-color: {BG_ELEVATED}; border-color: {TEXT_MUTED}; }}
    QPushButton:pressed {{ background-color: {BG_SURFACE}; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; border-color: {BORDER}; }}
    """

def btn_danger():
    return f"""
    QPushButton {{
        background-color: transparent; color: {ACCENT_RED};
        border: 1px solid {BORDER}; border-radius: 6px;
        padding: 6px 14px; font-size: 13px; font-weight: 400;
    }}
    QPushButton:hover   {{ background-color: rgba(224,92,108,0.10); border-color: {ACCENT_RED}; }}
    QPushButton:pressed {{ background-color: rgba(224,92,108,0.18); }}
    """

def btn_ghost():
    return f"""
    QPushButton {{
        background-color: transparent; color: {TEXT_SECONDARY};
        border: none; border-radius: 6px;
        padding: 6px 14px; font-size: 13px; font-weight: 400;
    }}
    QPushButton:hover   {{ background-color: rgba(91,108,226,0.09); color: {ACCENT_BLUE}; }}
    QPushButton:pressed {{ background-color: rgba(91,108,226,0.16); color: {ACCENT_BLUE}; }}
    """

def make_metric_card(title, value, subtitle="", value_color=None):
    from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
    frame = QFrame()
    frame.setObjectName("card")
    frame.setStyleSheet(CARD_STYLE)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(5)
    t = QLabel(title)
    t.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600; letter-spacing: 0.6px; background: transparent;")
    layout.addWidget(t)
    v = QLabel(value)
    color = value_color or TEXT_PRIMARY
    v.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 600; background: transparent; letter-spacing: -0.5px;")
    layout.addWidget(v)
    if subtitle:
        s = QLabel(subtitle)
        s.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        layout.addWidget(s)
    return frame, v

def metric_card_colored(title, value, subtitle="", accent=None):
    from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
    accent = accent or ACCENT_BLUE
    frame = QFrame()
    frame.setObjectName("card")
    frame.setStyleSheet(f"""
        QFrame#card {{
            background-color: {BG_SURFACE};
            border-radius: 8px;
            border: 1px solid {BORDER};
            border-top: 2px solid {accent};
        }}
    """)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(5)
    t = QLabel(title)
    t.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600; letter-spacing: 0.6px; background: transparent;")
    layout.addWidget(t)
    v = QLabel(str(value))
    v.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; background: transparent; letter-spacing: -0.3px;")
    layout.addWidget(v)
    if subtitle:
        s = QLabel(subtitle)
        s.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        layout.addWidget(s)
    return frame, v

def section_title(text):
    from PyQt6.QtWidgets import QLabel
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 17px; font-weight: 600; background: transparent; letter-spacing: -0.3px;")
    return lbl
