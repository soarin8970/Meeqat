
import sys
from datetime import datetime, date, timedelta

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import (
    QAction, QPainter, QPainterPath, QColor, QIcon, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QSystemTrayIcon,
    QMenu, QStyle
)

from prayer_engine import get_prayer_times, LOCATION, TIMEZONE


PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]


def local_datetime(value, target_date):
    """Convert prayer times into timezone-aware local datetimes."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=TIMEZONE)
        return value.astimezone(TIMEZONE)

    return datetime.combine(
        target_date, value
    ).replace(tzinfo=TIMEZONE)

class CrescentLogo(QWidget):

    def __init__(self, size=30):
        super().__init__()
        self.setFixedSize(size, size)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        outer = QPainterPath()
        outer.addEllipse(3, 3, 24, 24)
 
        inner = QPainterPath()
        inner.addEllipse(10, 0, 23, 23)

        crescent = outer.subtracted(inner)

        painter.fillPath(
            crescent,
            QColor("#E6CD91")
        )

        painter.end()


class MeeqatWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Meeqat Prayer Times")
        self.setFixedSize(QSize(350, 550))

        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.drag_position = None
        self.schedule = {}
        self.schedule_date = None
        self.rows = {}

        self.build_interface()
        self.refresh_schedule()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

    def build_interface(self):

        self.setStyleSheet("""

            QWidget {
    	        background-color: #142D29;
                color: #F4F1E8;
                font-family: Arial;
            }

            QLabel#title {
                color: #E6CD91;
                font-size: 23px;
                font-weight: bold;
            }

            QLabel#subtitle {
                color: #AFC5B9;
                font-size: 11px;
            }

            QLabel#section {
                color: #AFC5B9;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }

            QLabel#next_title {
                background-color: transparent;
                color: #BFD0C5;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
            }

            QLabel#next_name {
                background-color: transparent;
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
                
            }

            QLabel#countdown {
                background-color: transparent;
                color: #E6CD91;
                font-size: 18px;
                font-weight: bold;
            }

            QFrame#next_card {
                background-color: #1B3730;
                border: none;
                border-radius: 22px;
            }

            QFrame#prayer_row {
                background-color: #1B3730;
                border: 1px solid transparent;
                border-radius: 10px;
            }

            QFrame#prayer_row_active {
                background-color: #29483D;
                border: 1px solid #CDB77F;
                border-radius: 10px;
            }

            QLabel#prayer_name {
                color: #F4F1E8;
                font-size: 14px;
            }

            QLabel#prayer_time {
                color: #E6CD91;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton {
                background-color: transparent;
                color: #AFC5B9;
                border: none;
                font-size: 20px;
            }

            QPushButton:hover {
                color: #E6CD91;
            }


        """)

        main = QVBoxLayout(self)
        main.setContentsMargins(20, 18, 20, 18)
        main.setSpacing(11)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        
        logo = CrescentLogo(30)

        title = QLabel("MEEQAT")
        title.setObjectName("title")

        close_button = QPushButton("×")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.hide)

        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_button)

        main.addLayout(header)

        self.date_label = QLabel()
        self.date_label.setObjectName("subtitle")
        main.addWidget(self.date_label)

        # Next prayer card
        next_card = QFrame()
        next_card.setObjectName("next_card")
        next_card.setFixedHeight(112)

        card_layout = QVBoxLayout(next_card)
        card_layout.setContentsMargins(19, 12, 19, 12)
        card_layout.setSpacing(2)

        next_title = QLabel("NEXT PRAYER")
        next_title.setObjectName("next_title")
        next_title.setFixedHeight(16)

        self.next_name = QLabel("--")
        self.next_name.setObjectName("next_name")
        self.next_name.setMinimumHeight(32)
        self.next_name.setAlignment(
            Qt.AlignmentFlag.AlignLeft |
            Qt.AlignmentFlag.AlignVCenter
        )
        self.countdown = QLabel("--:--:--")
        self.countdown.setObjectName("countdown")

        card_layout.addWidget(next_title)
        card_layout.addWidget(self.next_name)
        card_layout.addWidget(self.countdown)

        main.addWidget(next_card)

        # Prayer schedule heading
        schedule_heading = QHBoxLayout()

        section_label = QLabel("TODAY'S PRAYERS")
        section_label.setObjectName("section")

        schedule_heading.addWidget(section_label)
        schedule_heading.addStretch()

        main.addLayout(schedule_heading)

        # Prayer rows
        for prayer in PRAYERS:

            row = QFrame()
            row.setObjectName("prayer_row")

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(15, 11, 15, 11)

            name_label = QLabel(prayer)
            name_label.setObjectName("prayer_name")

            time_label = QLabel("--:--")
            time_label.setObjectName("prayer_time")
            time_label.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )

            row_layout.addWidget(name_label)
            row_layout.addStretch()
            row_layout.addWidget(time_label)

            main.addWidget(row)

            self.rows[prayer] = (row, time_label)

        # Sunrise
        self.sunrise_label = QLabel("☀  Sunrise: --:--")
        self.sunrise_label.setObjectName("sunrise")
        self.sunrise_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        main.addWidget(self.sunrise_label)

        # Footer
        footer = QLabel(
            "PISCATAWAY, NEW JERSEY  •  ISNA  •  HANAFI"
        )
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main.addWidget(footer)

        calculation_note = QLabel("Calculated prayer times")
        calculation_note.setObjectName("footer")
        calculation_note.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main.addWidget(calculation_note)

    def refresh_schedule(self):

        today = datetime.now(TIMEZONE).date()

        self.schedule = get_prayer_times(today)
        self.schedule_date = today

        for prayer in PRAYERS:
            value = local_datetime(
                self.schedule[prayer], today
            )

            self.rows[prayer][1].setText(
                value.strftime("%I:%M %p")
            )

        sunrise = local_datetime(
            self.schedule["Sunrise"], today
        )

        self.sunrise_label.setText(
            "☀  Sunrise: " + sunrise.strftime("%I:%M %p")
        )

        self.date_label.setText(
            today.strftime("%A, %B %d, %Y")
        )

    def get_next_prayer(self):

        now = datetime.now(TIMEZONE)

        if self.schedule_date != now.date():
            self.refresh_schedule()

        for prayer in PRAYERS:

            prayer_time = local_datetime(
                self.schedule[prayer], now.date()
            )

            if prayer_time > now:
                return prayer, prayer_time

        # All today's prayers have passed.
        tomorrow = now.date() + timedelta(days=1)
        tomorrow_schedule = get_prayer_times(tomorrow)

        fajr = local_datetime(
            tomorrow_schedule["Fajr"], tomorrow
        )

        return "Fajr", fajr

    def update_display(self):

        now = datetime.now(TIMEZONE)

        if self.schedule_date != now.date():
            self.refresh_schedule()

        prayer, prayer_time = self.get_next_prayer()

        remaining = prayer_time - now
        seconds = max(0, int(remaining.total_seconds()))

        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        self.next_name.setText(prayer)

        self.countdown.setText(
            f"{hours:02}:{minutes:02}:{seconds:02}"
        )

        for name, (row, _) in self.rows.items():

            if name == prayer:
                row.setObjectName("prayer_row_active")
            else:
                row.setObjectName("prayer_row")

            row.style().unpolish(row)
            row.style().polish(row)
            row.update()

    # Allow the floating widget to be dragged.
    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):

        if (
            self.drag_position is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )

    def mouseReleaseEvent(self, event):
        self.drag_position = None

    def closeEvent(self, event):
        event.ignore()
        self.hide()


def main():

    app = QApplication(sys.argv)
    app.setApplicationName("Meeqat Prayer Times")
    app.setQuitOnLastWindowClosed(False)

    widget = MeeqatWidget()
    
    def show_widget():
        widget.show()
        widget.raise_()
        widget.activateWindow()

    # macOS menu bar icon
    logo = CrescentLogo(30)
 
    tray_pixmap = QPixmap(30, 30)
    tray_pixmap.fill(Qt.GlobalColor.transparent)

    logo.render(tray_pixmap)

    tray = QSystemTrayIcon(
        QIcon(tray_pixmap),
        app
    )

    menu = QMenu()

    show_action = QAction("Show Meeqat", app)
    hide_action = QAction("Hide Meeqat", app)
    quit_action = QAction("Quit Meeqat", app)

    show_action.triggered.connect(show_widget)
    hide_action.triggered.connect(widget.hide)
    quit_action.triggered.connect(app.quit)

    menu.addAction(show_action)
    menu.addAction(hide_action)
    menu.addSeparator()
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.setToolTip("Meeqat Prayer Times")

    tray.activated.connect(
        lambda reason: show_widget()
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )

    tray.show()
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

