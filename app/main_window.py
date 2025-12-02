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
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QTabWidget,
    QListWidget,
    QListWidgetItem
)
from PySide6.QtCore import Qt
import webbrowser
from urllib.parse import quote_plus
from app.google_routes import get_route_info, RouteError


class CarConfigDialog(QDialog):
    def __init__(self, parent=None, existing_config=None):
        super().__init__(parent)

        self.setWindowTitle("Saját jármű konfigurálása")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Autó neve (opcionális)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Pl. Saját autóm")
        form.addRow("Autó neve:", self.name_input)

        # Fogyasztás l/100km
        self.consumption_input = QDoubleSpinBox()
        self.consumption_input.setRange(1.0, 30.0)
        self.consumption_input.setDecimals(1)
        self.consumption_input.setSingleStep(0.1)
        self.consumption_input.setValue(7.0)  # default
        form.addRow("Átlagfogyasztás (l/100 km):", self.consumption_input)

        # Üzemanyag ár Ft/liter
        self.fuel_price_input = QDoubleSpinBox()
        self.fuel_price_input.setRange(100.0, 2000.0)
        self.fuel_price_input.setDecimals(0)
        self.fuel_price_input.setSingleStep(10.0)
        self.fuel_price_input.setValue(650.0)  # default pl. 650 Ft/l
        form.addRow("Üzemanyag ár (Ft / liter):", self.fuel_price_input)

        layout.addLayout(form)

        # Ha volt már meglévő config, töltsük be
        if existing_config:
            self.name_input.setText(existing_config.get("name", ""))
            self.consumption_input.setValue(existing_config.get("consumption_l_per_100km", 7.0))
            self.fuel_price_input.setValue(existing_config.get("fuel_price_per_liter", 650.0))

        # OK / Mégse gombok
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self):
        return {
            "name": self.name_input.text().strip() or "Saját jármű",
            "consumption_l_per_100km": float(self.consumption_input.value()),
            "fuel_price_per_liter": float(self.fuel_price_input.value()),
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.car_config = None  # ide mentjük a felhasználó autójának beállítását (dict)

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
            "Repülő",
        ])
        form_layout.addRow("Mivel:", self.mode_combo)

        left_layout.addLayout(form_layout)

        # Saját jármű konfigurálása gomb
        self.car_button = QPushButton("Saját jármű konfigurálása…")
        self.car_button.clicked.connect(self.on_configure_car_clicked)
        left_layout.addWidget(self.car_button)

        # Útvonal megjelenítése térképen
        self.route_button = QPushButton("Útvonal megjelenítése térképen")
        self.route_button.clicked.connect(self.on_route_clicked)
        left_layout.addWidget(self.route_button)

        # Költség tervezés (Directions API + számolás)
        self.cost_button = QPushButton("Költség tervezés")
        self.cost_button.clicked.connect(self.on_cost_clicked)
        left_layout.addWidget(self.cost_button)

        left_layout.addStretch()

        # ==== Jobb oldal: tabok (Napló + AI ajánló) ====
        right_tabs = QTabWidget(self)

        # --- 1. fül: Napló / infók (a régi panel) ---
        log_panel = QWidget(self)
        log_layout = QVBoxLayout(log_panel)

        result_label = QLabel("Információk / napló")
        result_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        log_layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText(
            "Itt látod majd az útvonaladatokat, költségbecslést, stb."
        )
        log_layout.addWidget(self.result_text)

        right_tabs.addTab(log_panel, "Napló")

        # --- 2. fül: AI úti cél ajánló ---
        ai_panel = QWidget(self)
        ai_layout = QVBoxLayout(ai_panel)

        ai_title = QLabel("AI úti cél ajánló")
        ai_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        ai_layout.addWidget(ai_title)

        # Felhasználói kívánság (prompt az AI-nak)
        self.ai_prompt = QTextEdit()
        self.ai_prompt.setPlaceholderText(
            "Írd le, milyen jellegű utazást szeretnél.\n"
            "Pl.: „olasz tengerpart, közelben városokkal és kiránduló helyekkel, "
            "ne legyen túl zsúfolt.”"
        )
        self.ai_prompt.setFixedHeight(120)
        ai_layout.addWidget(self.ai_prompt)

        # Gomb az AI hívására
        self.ai_button = QPushButton("Ajánlások lekérése")
        self.ai_button.clicked.connect(self.on_ai_request_clicked)
        ai_layout.addWidget(self.ai_button)

        # Lista az ajánlott úti céloknak
        self.ai_list = QListWidget()
        self.ai_list.itemSelectionChanged.connect(self.on_ai_item_selected)
        ai_layout.addWidget(self.ai_list)

        # Részletek kijelölés után
        self.ai_details = QTextEdit()
        self.ai_details.setReadOnly(True)
        self.ai_details.setPlaceholderText(
            "Itt jelennek meg a kiválasztott úti cél részletei."
        )
        ai_layout.addWidget(self.ai_details)

        right_tabs.addTab(ai_panel, "AI ajánló")

        # --- jobb oldal hozzáadása a fő layouthoz ---
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_tabs, 2)

        self.statusBar().showMessage(
            "Add meg a honnan–hová adatokat, vagy próbáld ki az AI úti cél ajánlót."
        )

        # ide mentjük az AI-tól kapott találatokat (lista dict-ekkel)
        self.ai_destinations = []

    # --- Segéd: a comboboxból Google travelmode + felirat ---
    def _get_travelmode(self):
        mode_text = self.mode_combo.currentText()
        if mode_text == "Autó":
            return "driving", mode_text
        elif mode_text == "Tömegközlekedés":
            return "transit", mode_text
        elif mode_text == "Repülő":
            # Directions API nem tud airplane módot,
            # driving-et használunk a távolság/idő becsléshez.
            return "driving", mode_text
        else:
            return "driving", mode_text

    # ==== Útvonal megjelenítése térképen ====
    def on_route_clicked(self):
        origin = self.origin_input.text().strip()
        destination = self.destination_input.text().strip()

        if not origin or not destination:
            self.statusBar().showMessage("Hiba: töltsd ki a Honnan és Hová mezőket!")
            return

        travelmode, mode_text = self._get_travelmode()

        origin_enc = quote_plus(origin)
        destination_enc = quote_plus(destination)

        url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={origin_enc}"
            f"&destination={destination_enc}"
            f"&travelmode={travelmode}"
        )

        webbrowser.open(url)

        self.result_text.setPlainText(
            "Útvonal megjelenítése térképen:\n\n"
            f"Honnan: {origin}\n"
            f"Hová: {destination}\n"
            f"Mivel: {mode_text}\n\n"
            f"Megnyitott Google Maps URL:\n{url}"
        )
        self.statusBar().showMessage("Útvonal megnyitva a Google Maps-ben.")

    # ==== Költség tervezés (Directions API + számolás) ====
    def on_cost_clicked(self):
        origin = self.origin_input.text().strip()
        destination = self.destination_input.text().strip()

        if not origin or not destination:
            self.statusBar().showMessage("Hiba: töltsd ki a Honnan és Hová mezőket!")
            return

        travelmode, mode_text = self._get_travelmode()

        # Directions API hívása
        try:
            info = get_route_info(origin, destination, travelmode)
        except RouteError as e:
            self.result_text.setPlainText(
                f"Nem sikerült lekérdezni az útvonal adatait:\n{e}"
            )
            self.statusBar().showMessage("Hiba a Directions API hívásakor.")
            return

        distance_km = info["distance_km"]
        duration_min = info["duration_min"]
        traffic_duration_min = info["traffic_duration_min"]
        warnings = info["warnings"]
        transit_segments = info.get("transit_segments") or []

        hours = int(duration_min // 60)
        mins = int(duration_min % 60)

        lines = []
        lines.append("Útvonal adatai (Directions API alapján):\n")
        lines.append(f"- Honnan: {origin}")
        lines.append(f"- Hová: {destination}")
        lines.append(f"- Mivel: {mode_text}")
        lines.append(f"- Távolság: {distance_km:.1f} km")

        if mode_text == "Autó":
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

        # Autós költség csak akkor, ha autó + van saját jármű
        if mode_text == "Autó" and self.car_config is not None:
            cons = self.car_config["consumption_l_per_100km"]
            price = self.car_config["fuel_price_per_liter"]
            liters = distance_km / 100.0 * cons
            cost = liters * price

            lines.append("\nSaját jármű költségbecslés:")
            lines.append(f"- Autó: {self.car_config['name']}")
            lines.append(f"- Fogyasztás: {cons:.1f} l/100 km")
            lines.append(f"- Üzemanyag ár: {price:.0f} Ft/l")
            lines.append(f"- Becsült üzemanyag igény: {liters:.1f} liter")
            lines.append(f"- Becsült üzemanyagköltség: {cost:,.0f} Ft".replace(",", " "))
        elif self.mode_combo.currentText() == "Autó" and self.car_config is None:
            lines.append("\n[Saját jármű nincs konfigurálva – az autós költségbecsléshez állítsd be a járművet.]")

        # Repülő költségmodell (nagyon egyszerű becslés)
        if mode_text == "Repülő":
            d = distance_km

            if d < 800:
                base = 20000.0
                per_km = 50.0
            elif d < 2500:
                base = 30000.0
                per_km = 40.0
            else:
                base = 40000.0
                per_km = 35.0

            one_way = base + d * per_km
            round_trip = one_way * 2.0

            low_one_way = one_way * 0.7
            high_one_way = one_way * 1.3
            low_round = round_trip * 0.7
            high_round = round_trip * 1.3

            lines.append("\nRepülőjegy költségbecslés (becsült sáv):")
            lines.append(f"Távolság alapú modell (nem valós árlista)")
            lines.append(
                f"- Odaút: ~ {low_one_way:,.0f} – {high_one_way:,.0f} Ft".replace(",", " ")
            )
            lines.append(
                f"- Oda-vissza: ~ {low_round:,.0f} – {high_round:,.0f} Ft".replace(",", " ")
            )

        if mode_text == "Tömegközlekedés":
            d = distance_km

            # hosszabb az út,  olcsóbb / km
            if d < 300:
                base = 1000.0
                per_km = 25.0
            elif d < 1500:
                base = 2000.0
                per_km = 18.0
            else:
                base = 4000.0
                per_km = 15.0

            one_way = base + d * per_km
            round_trip = one_way * 2.0

            low_one_way = one_way * 0.8
            high_one_way = one_way * 1.2
            low_round = round_trip * 0.8
            high_round = round_trip * 1.2

            lines.append("\nTömegközlekedés költségbecslés (becsült sáv):")
            lines.append(f"- Km alapú, egyszerű modell (busz + vonat)")
            lines.append(
                f"- Odaút: ~ {low_one_way:,.0f} – {high_one_way:,.0f} Ft".replace(",", " ")
            )
            lines.append(
                f"- Oda-vissza: ~ {low_round:,.0f} – {high_round:,.0f} Ft".replace(",", " ")
            )

            # ==== Transit szakaszok kiírása ====
            if transit_segments:
                lines.append("\nTömegközlekedés részletei:")
                for idx, seg in enumerate(transit_segments, start=1):
                    dep_time = seg.get("departure_time")
                    dep_stop = seg.get("departure_stop")
                    arr_time = seg.get("arrival_time")
                    arr_stop = seg.get("arrival_stop")
                    line_name = seg.get("line_name")
                    vehicle_type = seg.get("vehicle_type")

                    lines.append(f"\n  Szakasz {idx}:")
                    if dep_time or dep_stop:
                        lines.append(
                            f"    - Indulás:  {dep_time or 'ismeretlen idő'} – {dep_stop or 'ismeretlen megálló'}"
                        )
                    if arr_time or arr_stop:
                        lines.append(
                            f"    - Érkezés:  {arr_time or 'ismeretlen idő'} – {arr_stop or 'ismeretlen megálló'}"
                        )
                    if line_name or vehicle_type:
                        vt = vehicle_type or "ISMERETLEN"
                        lines.append(
                            f"    - Jármű: {vt} – {line_name or 'ismeretlen járat'}"
                        )

        if warnings:
            lines.append("\nFigyelmeztetések / akadályok:")
            for w in warnings:
                lines.append(f"  • {w}")

        self.result_text.setPlainText("\n".join(lines))
        self.statusBar().showMessage("Költségbecslés elkészült.")

    def on_configure_car_clicked(self):
        dialog = CarConfigDialog(self, existing_config=self.car_config)
        if dialog.exec() == QDialog.Accepted:
            self.car_config = dialog.get_config()
            name = self.car_config["name"]
            self.statusBar().showMessage(f"Saját jármű beállítva: {name}")
            self.result_text.append(f"\n[Saját jármű frissítve] {name}")
    # ==== AI úti cél ajánló – ajánlások lekérése ====
    def on_ai_request_clicked(self):
        text = self.ai_prompt.toPlainText().strip()
        if not text:
            self.statusBar().showMessage("Írd le, milyen utazást szeretnél az AI-nak.")
            return

        # --- Itt később a HF API-t fogjuk hívni ---
        # from app.ai_recommend import suggest_destinations
        # self.ai_destinations = suggest_destinations(text)

        # Egyelőre DUMMY adatok, hogy lásd a működést:
        self.ai_destinations = [
            {
                "name": "Bari",
                "country": "Olaszország",
                "short_description": "Dél-olasz kikötőváros, közel szép tengerpartokkal "
                                     "és kis városokkal (Polignano a Mare, Monopoli).",
                "tags": ["tengerpart", "városnézés", "kirándulás"],
            },
            {
                "name": "Trieste",
                "country": "Olaszország",
                "short_description": "Tengerparti város az olasz–szlovén határnál, "
                                     "közel hegyekkel és kiránduló helyekkel.",
                "tags": ["tengerpart", "városnézés"],
            },
        ]

        # Mezők clearelés + lista feltöltése
        self.ai_list.clear()
        self.ai_details.clear()

        for dest in self.ai_destinations:
            item = QListWidgetItem(f"{dest['name']} ({dest['country']})")
            self.ai_list.addItem(item)

        # Promptot is ürítjük, hogy 'új lappal' kezdjen a user
        self.ai_prompt.clear()

        self.statusBar().showMessage("AI ajánlások frissítve.")

    # ==== AI úti cél ajánló – listaelem kiválasztása ====
    def on_ai_item_selected(self):
        idx = self.ai_list.currentRow()
        if idx < 0 or idx >= len(self.ai_destinations):
            return

        dest = self.ai_destinations[idx]

        lines = [
            f"Név: {dest.get('name')}",
            f"Ország: {dest.get('country')}",
            "",
            dest.get("short_description", ""),
        ]

        tags = dest.get("tags")
        if tags:
            lines.append("")
            lines.append("Címkék: " + ", ".join(tags))

        self.ai_details.setPlainText("\n".join(lines))
