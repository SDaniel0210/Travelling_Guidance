from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTextEdit,
    QLabel,
)
from PySide6.QtCore import Qt
import webbrowser
from urllib.parse import quote_plus
from app.google_routes import get_route_info, RouteError


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Travelling Guidance")
        self.setMinimumSize(900, 600)

        # Központi widget + fő (vízszintes) layout
        central = QWidget(self)
        main_layout = QHBoxLayout(central)
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # ==== Bal oldal: útvonal beállítások ====
        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_panel.setLayout(left_layout)

        title_label = QLabel("Útvonal beállításai")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        left_layout.addWidget(title_label)

        form_layout = QFormLayout()

        # Honnan
        self.origin_input = QLineEdit()
        self.origin_input.setPlaceholderText("Pl. Budapest")
        form_layout.addRow("Honnan:", self.origin_input)

        # Hová
        self.destination_input = QLineEdit()
        self.destination_input.setPlaceholderText("Pl. Róma")
        form_layout.addRow("Hová:", self.destination_input)

        # Mivel
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Autó",
            "Tömegközlekedés",
            "Gyalog",
            "Kerékpár",
        ])
        form_layout.addRow("Mivel:", self.mode_combo)

        left_layout.addLayout(form_layout)

        # Gomb: útvonal megjelenítése
        self.route_button = QPushButton("Útvonal megnyitása Google Maps-ben")
        self.route_button.clicked.connect(self.on_route_clicked)
        left_layout.addWidget(self.route_button)

        left_layout.addStretch()

        # ==== Jobb oldal: infó / log ====
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_panel.setLayout(right_layout)

        result_label = QLabel("Információk / napló")
        result_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        right_layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText(
            "Itt látod majd, hogy milyen Google Maps URLt nyitottunk meg,\n"
            "később ide jöhetnek plusz infók az útról."
        )
        right_layout.addWidget(self.result_text)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        self.statusBar().showMessage("Add meg a honnan–hová adatokat, majd kattints az útvonal gombra.")

    # ==== Gomb logika: Google Maps megnyitása ====
    def on_route_clicked(self):
        origin = self.origin_input.text().strip()
        destination = self.destination_input.text().strip()

        if not origin or not destination:
            self.statusBar().showMessage("Hiba: töltsd ki a Honnan és Hová mezőket!")
            return

        # Utazási mód leképezése Google Maps travelmode-re
        mode_text = self.mode_combo.currentText()
        if mode_text == "Autó":
            travelmode = "driving"
        elif mode_text == "Tömegközlekedés":
            travelmode = "transit"
        elif mode_text == "Gyalog":
            travelmode = "walking"
        elif mode_text == "Kerékpár":
            travelmode = "bicycling"
        else:
            travelmode = "driving"

        # --- 1) Google Maps URL megnyitása böngészőben (megtartjuk) ---
        origin_enc = quote_plus(origin)
        destination_enc = quote_plus(destination)

        url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={origin_enc}"
            f"&destination={destination_enc}"
            f"&travelmode={travelmode}"
        )
        webbrowser.open(url)

        # --- 2) Directions API hívása részletes infókért ---
        try:
            info = get_route_info(origin, destination, travelmode)
        except RouteError as e:
            self.result_text.setPlainText(
                f"Nem sikerült lekérdezni az útvonal adatait:\n{e}\n\n"
                f"Megnyitottuk a Maps-et itt:\n{url}"
            )
            self.statusBar().showMessage("Hiba a Directions API hívásakor.")
            return

        distance_km = info["distance_km"]
        duration_min = info["duration_min"]
        traffic_duration_min = info["traffic_duration_min"]
        warnings = info["warnings"]

        # Szép formázás
        hours = int(duration_min // 60)
        mins = int(duration_min % 60)

        lines = []
        lines.append("Útvonal adatai (Directions API alapján):\n")
        lines.append(f"- Távolság: {distance_km:.1f} km")
        if hours > 0:
            lines.append(f"- Becsült idő: {hours} óra {mins} perc")
        else:
            lines.append(f"- Becsült idő: {mins} perc")

        if traffic_duration_min is not None:
            t_hours = int(traffic_duration_min // 60)
            t_mins = int(traffic_duration_min % 60)
            if t_hours > 0:
                lines.append(f"- Forgalommal: {t_hours} óra {t_mins} perc")
            else:
                lines.append(f"- Forgalommal: {t_mins} perc")

        if warnings:
            lines.append("\nFigyelmeztetések / akadályok:")
            for w in warnings:
                lines.append(f"  • {w}")

        lines.append("\nMegnyitott Google Maps URL:")
        lines.append(url)

        self.result_text.setPlainText("\n".join(lines))
        self.statusBar().showMessage("Útvonaladatok sikeresen lekérve.")
