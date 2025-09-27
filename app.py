# app.py
import os
import sys
import json
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QSpinBox, QPushButton, QTextEdit, QLabel, QListWidget, QTabWidget,
    QSplitter, QSizePolicy, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from FunklesScraper.paths import CACHE_DIR, SETTINGS_PATH
from FunklesScraper.scrape import scrape
from FunklesScraper.label_and_summarize import Labeler
from FunklesScraper.chat import talk

# ----------------------------
# Utility: redirect print() to QTextEdit
# ----------------------------
class EmittingStream(QWidget):
    def __init__(self, console):
        super().__init__()
        self.console = console

    def write(self, text):
        if text.strip():
            self.console.append(text)

    def flush(self):
        pass

# ----------------------------
# Worker for scraping + labeling
# ----------------------------
class ScrapeLabelWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, form_type, days):
        super().__init__()
        self.form_type = form_type
        self.days = days

    def run(self):
        try:
            result = scrape(self.form_type, self.days)
            labeler = Labeler()
            labeler.run()
            self.finished_signal.emit(result)
        except Exception:
            self.error_signal.emit(traceback.format_exc())

# ----------------------------
# Load settings
# ----------------------------
try:
    with open(SETTINGS_PATH, "r") as f:
        settings = json.load(f)
except Exception:
    # default fallback
    settings = {
        "form_types": ["SCHEDULE 13D", "10-K"],
        "form_type_index": 0,
        "date_range_days": 1
    }

# ----------------------------
# Load filings metadata
# ----------------------------
def load_filings():
    filings_list = []
    for root, dirs, files in os.walk(CACHE_DIR):
        for file in files:
            if file.endswith(".meta.json"):
                try:
                    with open(os.path.join(root, file), "r") as f:
                        data = json.load(f)
                        if data:  # skip None
                            filings_list.append(data)
                except Exception as e:
                    print(f"Failed to load {file}: {e}")
    return filings_list

filings = load_filings()

# ----------------------------
# Filings Viewer Tab
# ----------------------------
class FilingsViewerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.reload_filings()

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_label = QLabel("<b>Filter by label:</b>")
        filter_label.setFont(QFont("Arial", 10))
        self.label_dropdown = QComboBox()
        self.label_dropdown.addItem("All")
        self.label_dropdown.addItems(self.labels)
        self.label_dropdown.currentTextChanged.connect(self.update_list)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.label_dropdown)
        filter_layout.addStretch()
        self.layout.addLayout(filter_layout)

        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # List
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.show_details)
        self.splitter.addWidget(self.list_widget)
        # Details
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout()
        self.details_widget.setLayout(self.details_layout)
        self.date_label = QLabel()
        self.form_label = QLabel()
        self.cik_label = QLabel()
        self.share_label = QLabel()
        for lbl in [self.date_label, self.form_label, self.cik_label, self.share_label]:
            lbl.setFont(QFont("Arial", 10))
            self.details_layout.addWidget(lbl)
        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setFont(QFont("Consolas", 11))
        self.details_layout.addWidget(QLabel("<b>Summary:</b>"))
        self.details_layout.addWidget(self.summary_box, stretch=1)
        self.splitter.addWidget(self.details_widget)
        self.splitter.setSizes([300, 700])
        self.layout.addWidget(self.splitter)
        self.update_list()

    def reload_filings(self):
        global filings
        filings = load_filings()
        self.labels = sorted({f.get("label") or "Unlabeled" for f in filings})
        if hasattr(self, 'label_dropdown'):
            self.label_dropdown.clear()
            self.label_dropdown.addItem("All")
            self.label_dropdown.addItems(self.labels)
        if hasattr(self, 'list_widget'):
            self.update_list()

    def update_list(self):
        self.list_widget.clear()
        selected_label = self.label_dropdown.currentText()
        for f in filings:
            if selected_label == "All" or f.get("label") == selected_label:
                display_name = f"{f['filename']} ({f.get('date','')})"
                self.list_widget.addItem(display_name)

    def show_details(self):
        self.summary_box.clear()
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            filename = selected_items[0].text().split(" (")[0]
            for f in filings:
                if f["filename"] == filename:
                    self.date_label.setText(f"<b>Date:</b> {f.get('date','')}")
                    self.form_label.setText(f"<b>Form:</b> {f.get('form','')}")
                    self.cik_label.setText(f"<b>CIK:</b> {f.get('cik','')}")
                    share_pct = f.get("share %")
                    self.share_label.setText(f"<b>Share %:</b> {share_pct:.2%}" if share_pct else "")
                    self.summary_box.setText(f.get("summary", "No summary available."))
                    break

# ----------------------------
# Control Panel Tab
# ----------------------------
class ControlPanelTab(QWidget):
    def __init__(self, viewer_tab: FilingsViewerTab):
        super().__init__()
        self.viewer_tab = viewer_tab
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Form type selector
        self.form_type_dropdown = QComboBox()
        self.form_type_dropdown.addItems(settings["form_types"])
        self.form_type_dropdown.setCurrentIndex(settings["form_type_index"])
        self.layout.addWidget(QLabel("<b>Select Form Type:</b>"))
        self.layout.addWidget(self.form_type_dropdown)

        # Date range selector
        self.date_spin = QSpinBox()
        self.date_spin.setMinimum(1)
        self.date_spin.setValue(settings["date_range_days"])
        self.layout.addWidget(QLabel("<b>Date Range (days):</b>"))
        self.layout.addWidget(self.date_spin)

        # Run button
        self.run_button = QPushButton("Run Scrape & Label")
        self.run_button.clicked.connect(self.run_scrape_label)
        self.layout.addWidget(self.run_button)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        self.layout.addWidget(QLabel("<b>Debug Console:</b>"))
        self.layout.addWidget(self.console, stretch=1)

        # Redirect print
        sys.stdout = EmittingStream(self.console)
        sys.stderr = EmittingStream(self.console)

    def run_scrape_label(self):
        self.console.append("Starting scrape & labeling...")
        form_type = self.form_type_dropdown.currentText()
        days = self.date_spin.value()
        self.worker = ScrapeLabelWorker(form_type, days)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def on_success(self, msg):
        self.console.append(msg)
        self.viewer_tab.reload_filings()

    def on_error(self, msg):
        self.console.append("Error:\n" + msg)

# ----------------------------
# Chat Tab
# ----------------------------
class ChatTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.input_field = QLineEdit()
        self.layout.addWidget(QLabel("<b>Enter your message:</b>"))
        self.layout.addWidget(self.input_field)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setFont(QFont("Consolas", 11))
        self.layout.addWidget(QLabel("<b>AI Response:</b>"))
        self.layout.addWidget(self.output_box, stretch=1)

    def send_message(self):
        text = self.input_field.text()
        if text.strip():
            self.output_box.append(f"<b>You:</b> {text}")
            try:
                response = talk(text)
                self.output_box.append(f"<b>AI:</b> {response}")
            except Exception:
                self.output_box.append("<b>AI:</b> Error processing message.")
                self.output_box.append(traceback.format_exc())
            self.input_field.clear()

# ----------------------------
# Main App
# ----------------------------
class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Funkles SEC")
        self.setMinimumSize(1000, 600)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.tabs = QTabWidget()
        self.viewer_tab = FilingsViewerTab()
        self.control_tab = ControlPanelTab(self.viewer_tab)
        self.tabs.addTab(self.viewer_tab, "Filings Viewer")
        self.tabs.addTab(self.control_tab, "Control Panel")
        self.tabs.addTab(ChatTab(), "AI Chat")
        self.layout.addWidget(self.tabs)

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())
