#!/usr/bin/env python3
'''
Desktop Reminder App
Self‑contained PyQt6 reminder application that auto‑installs its own dependency.
'''

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

# ---------------- Dependency bootstrap ---------------- #

def ensure_pyqt6():
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print('PyQt6 not found. Installing...')
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'PyQt6>=6.6.0'])
        except subprocess.CalledProcessError as exc:
            print('Automatic installation failed. Please install PyQt6 manually and rerun.')
            sys.exit(exc.returncode)

ensure_pyqt6()
# ------------------------------------------------------- #

from PyQt6.QtCore import QTimer, Qt, QDateTime
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QDialog,
    QLabel,
    QLineEdit,
    QDateTimeEdit,
    QDialogButtonBox,
    QMessageBox,
    QSystemTrayIcon,
)
from PyQt6.QtGui import QIcon

DATA_FILE = Path.home() / '.reminder_app_tasks.json'

class AddTaskDialog(QDialog):
    '''Dialog for adding a new reminder.'''

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Task')
        self.setFixedWidth(320)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel('Task Description:'))
        self.task_edit = QLineEdit()
        layout.addWidget(self.task_edit)

        layout.addWidget(QLabel('Due Date & Time:'))
        self.time_edit = QDateTimeEdit()
        self.time_edit.setDisplayFormat('dd/MM/yyyy HH:mm')
        self.time_edit.setMinimumDateTime(QDateTime.currentDateTime())
        self.time_edit.setCalendarPopup(True)
        layout.addWidget(self.time_edit)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self):
        return self.task_edit.text().strip(), self.time_edit.dateTime().toPyDateTime()

class MainWindow(QMainWindow):
    '''Main reminder window.'''

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Desktop Reminder App')
        self.setMinimumSize(600, 450)

        self.tasks = []
        self.load_tasks()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        vbox = QVBoxLayout(central_widget)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Task', 'Due'])
        self.table.horizontalHeader().setStretchLastSection(True)
        vbox.addWidget(self.table)
        self.refresh_table()

        hbox = QHBoxLayout()
        self.add_btn = QPushButton('Add Task')
        self.rem_btn = QPushButton('Remove Selected')
        hbox.addWidget(self.add_btn)
        hbox.addWidget(self.rem_btn)
        hbox.addStretch()
        vbox.addLayout(hbox)

        self.add_btn.clicked.connect(self.add_task)
        self.rem_btn.clicked.connect(self.remove_selected)

        self.tray = QSystemTrayIcon(QIcon.fromTheme('alarm'))
        self.tray.setToolTip('Reminder App')
        self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_tasks)
        self.timer.start(30_000)

    # Persistence
    def load_tasks(self):
        if DATA_FILE.exists():
            try:
                self.tasks = json.loads(DATA_FILE.read_text())
            except Exception:
                self.tasks = []

    def save_tasks(self):
        DATA_FILE.write_text(json.dumps(self.tasks, indent=2))
        self.refresh_table()

    # UI
    def refresh_table(self):
        self.table.setRowCount(len(self.tasks))
        for row, task in enumerate(self.tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task['desc']))
            due_dt = datetime.fromisoformat(task['due'])
            self.table.setItem(row, 1, QTableWidgetItem(due_dt.strftime('%d/%m/%Y %H:%M')))
            for col in range(2):
                self.table.item(row, col).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

    # Task ops
    def add_task(self):
        dlg = AddTaskDialog(self)
        if dlg.exec():
            desc, due = dlg.get_data()
            if desc:
                self.tasks.append({'desc': desc, 'due': due.isoformat(), 'notified': False})
                self.save_tasks()
            else:
                QMessageBox.warning(self, 'Input Error', 'Task description cannot be empty.')

    def remove_selected(self):
        selected_rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in selected_rows:
            del self.tasks[row]
        if selected_rows:
            self.save_tasks()

    # Notification
    def check_tasks(self):
        now = datetime.now()
        for task in self.tasks:
            if not task['notified'] and datetime.fromisoformat(task['due']) <= now:
                self.send_notification(task['desc'])
                task['notified'] = True
        self.save_tasks()

    def send_notification(self, message):
        self.tray.showMessage('⏰ Reminder', message, QSystemTrayIcon.MessageIcon.Information, 10_000)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(
        '''
        QMainWindow { background: #121212; color: #ECECEC; }
        QPushButton {
            background: #1E88E5; border: none; border-radius: 6px; padding: 6px 12px;
            font-weight: 600; color: #FFFFFF;
        }
        QPushButton:hover { background: #42A5F5; }
        QPushButton:pressed { background: #1565C0; }
        QTableWidget { background: #1E1E1E; gridline-color: #333; }
        QHeaderView::section { background: #2C2C2C; color: #ECECEC; padding: 4px; }
        '''
    )
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
