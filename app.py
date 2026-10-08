"""QuickVault: a comfortable Qt desktop app for encrypted notes and secrets."""
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QComboBox, QCheckBox, QPlainTextEdit, QStackedWidget, QMessageBox)
from vault import Vault

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets'
STYLE = '''
QWidget { background: #f7f6f2; color: #263c34; font-family: 'Segoe UI'; font-size: 14px; }
QFrame#sidebar { background: #e9eee6; border-right: 1px solid #dce3d8; }
QFrame#sidebar QLabel { background: transparent; }
QLabel#heading { font-size: 28px; font-weight: 700; }
QLabel#brand { font-size: 23px; font-weight: 700; }
QLabel#muted { color: #738177; }
QLabel#eyebrow { color: #738177; font-size: 11px; font-weight: 700; }
QLineEdit, QPlainTextEdit, QComboBox { background: #ffffff; border: 1px solid #dce3d8; border-radius: 9px; padding: 10px; selection-background-color: #32735c; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #32735c; }
QPlainTextEdit { font-family: Consolas; font-size: 15px; }
QPushButton { background: #ffffff; border: 1px solid #dce3d8; border-radius: 9px; padding: 10px 16px; font-weight: 600; }
QPushButton:hover { background: #edf3ec; border-color: #a5b7a7; }
QPushButton#primary { background: #32735c; color: white; border: none; }
QPushButton#primary:hover { background: #275e49; }
QPushButton#danger { color: #a85045; }
QPushButton:disabled { color: #a4aaa3; background: #eeefea; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 14px 10px; border-radius: 8px; margin-bottom: 5px; }
QListWidget::item:selected { background: #32735c; color: white; }
QListWidget::item:hover:!selected { background: #dce5d8; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QStatusBar { background: #edf1e9; color: #738177; font-size: 12px; }
'''


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


def button(text, callback, name=None):
    widget = QPushButton(text)
    if name:
        widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    return widget


class QuickVault(QMainWindow):
    def __init__(self, vault=None):
        super().__init__()
        self.vault = vault or Vault()
        self.current = None
        self.dirty = False
        self.loading = False
        self.copied_value = None
        self.setWindowTitle('QuickVault')
        self.setWindowIcon(QIcon(str(ASSETS / 'quickvault.ico')))
        self.resize(1100, 740)
        self.setMinimumSize(820, 620)
        self.setStyleSheet(STYLE)
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.auto_lock)
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.setSingleShot(True)
        self.clipboard_timer.timeout.connect(self.clear_clipboard)
        QApplication.instance().installEventFilter(self)
        for keys, callback in [('Ctrl+S', self.save), ('Ctrl+N', self.new), ('Ctrl+L', self.lock)]:
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(callback)
        self.gate()

    def replace_page(self, widget):
        old = self.takeCentralWidget()
        if old:
            old.hide()
            old.deleteLater()
        self.setCentralWidget(widget)

    def gate(self):
        self.current = None
        self.dirty = False
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addStretch()
        card = QWidget()
        card.setMaximumWidth(440)
        form = QVBoxLayout(card)
        form.setSpacing(14)
        image = QLabel()
        image.setPixmap(QPixmap(str(ASSETS / 'quickvault.png')).scaled(88, 88, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        form.addWidget(image)
        form.addWidget(label('QuickVault', 'heading'))
        form.addWidget(label('A quiet place for your notes & secrets.', 'muted'))
        creating = not self.vault.path.exists()
        form.addSpacing(14)
        form.addWidget(label('CREATE YOUR VAULT' if creating else 'WELCOME BACK', 'eyebrow'))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText('Master password')
        self.password.returnPressed.connect(self.unlock)
        form.addWidget(self.password)
        self.confirmation = QLineEdit()
        self.confirmation.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirmation.setPlaceholderText('Confirm master password')
        self.confirmation.returnPressed.connect(self.unlock)
        self.confirmation.setVisible(creating)
        form.addWidget(self.confirmation)
        form.addWidget(button('Create vault' if creating else 'Unlock vault', self.unlock, 'primary'))
        form.addWidget(label('At least 10 characters. Keep your password safe — there is no reset.' if creating else 'Your vault stays encrypted on this computer.', 'muted'))
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.replace_page(root)
        self.statusBar().showMessage('Private by design · Stored on your computer')
        self.password.setFocus()

    def unlock(self):
        password = self.password.text()
        if not self.vault.path.exists() and (len(password) < 10 or password != self.confirmation.text()):
            QMessageBox.warning(self, 'Check password', 'Use at least 10 characters and matching passwords.')
            return
        try:
            self.vault.unlock(password)
        except Exception:
            QMessageBox.warning(self, 'Unable to unlock', 'Incorrect password, or the vault cannot be read.')
            return
        self.password.clear()
        self.confirmation.clear()
        self.workspace()
        self.activity()

    def workspace(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(275)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 28, 22, 22)
        side.setSpacing(16)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ASSETS / 'quickvault.png')).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand.addWidget(logo)
        brand.addWidget(label('QuickVault', 'brand'))
        side.addLayout(brand)
        side.addWidget(label('Keep the little things close.', 'muted'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search titles & tags…')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        side.addWidget(self.search)
        side.addWidget(button('+  New entry', self.new, 'primary'))
        self.count_label = label('YOUR ENTRIES', 'eyebrow')
        side.addWidget(self.count_label)
        self.listbox = QListWidget()
        self.listbox.currentItemChanged.connect(self.select)
        side.addWidget(self.listbox, 1)
        side.addWidget(button('Lock vault   ·   Ctrl+L', self.lock))
        layout.addWidget(sidebar)
        main = QWidget()
        editor = QVBoxLayout(main)
        editor.setContentsMargins(30, 28, 30, 24)
        editor.setSpacing(14)
        editor.addWidget(label('Your everyday pocket', 'heading'))
        editor.addWidget(label('A little less to remember. A safe place to keep it.', 'muted'))
        actions = QHBoxLayout()
        self.save_button = button('Save   ·   Ctrl+S', self.save, 'primary')
        self.delete_button = button('Delete entry', self.delete, 'danger')
        actions.addWidget(self.save_button)
        actions.addWidget(button('Copy value', self.copy))
        actions.addStretch()
        actions.addWidget(self.delete_button)
        editor.addLayout(actions)
        editor.addWidget(label('TITLE', 'eyebrow'))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText('Give this entry a name')
        self.title_edit.textChanged.connect(self.changed)
        editor.addWidget(self.title_edit)
        options = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItems(['Note', 'API key', 'Environment variable'])
        self.kind.currentTextChanged.connect(self.changed)
        self.kind.currentTextChanged.connect(self.visibility)
        options.addWidget(self.kind)
        options.addStretch()
        self.reveal = QCheckBox('Reveal secret')
        self.reveal.toggled.connect(self.visibility)
        options.addWidget(self.reveal)
        editor.addLayout(options)
        editor.addWidget(label('CONTENT / VALUE', 'eyebrow'))
        self.content_stack = QStackedWidget()
        self.content = QPlainTextEdit()
        self.content.setPlaceholderText('Write a quick note, or paste a value here…')
        self.content.textChanged.connect(self.changed)
        self.content_stack.addWidget(self.content)
        self.cover = label('Secret hidden\n\nEnable “Reveal secret” to view or edit this value.', 'muted')
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet('background: white; border: 1px solid #dce3d8; border-radius: 9px;')
        self.content_stack.addWidget(self.cover)
        editor.addWidget(self.content_stack, 1)
        editor.addWidget(label('TAGS', 'eyebrow'))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText('work, personal, project…')
        self.tags_edit.textChanged.connect(self.changed)
        editor.addWidget(self.tags_edit)
        layout.addWidget(main, 1)
        self.replace_page(root)
        self.refresh()
        self.load(None)
        self.statusBar().showMessage('Encrypted locally · Auto-lock after 5 minutes of inactivity')

    def changed(self, *args):
        if not self.loading:
            self.dirty = True
            self.statusBar().showMessage('Unsaved changes · Ctrl+S to save')

    def visibility(self, *args):
        secret = self.kind.currentText() != 'Note'
        self.reveal.setEnabled(secret)
        self.content_stack.setCurrentIndex(1 if secret and not self.reveal.isChecked() else 0)

    def refresh(self, *args):
        query = self.search.text().casefold()
        entries = sorted((e for e in self.vault.entries if query in (e['title'] + ' ' + e['tags']).casefold()), key=lambda e: e['updated'], reverse=True)
        self.listbox.blockSignals(True)
        self.listbox.clear()
        for entry in entries:
            item = QListWidgetItem(entry['title'] + '\n' + entry['kind'])
            item.setData(Qt.ItemDataRole.UserRole, entry['id'])
            self.listbox.addItem(item)
            if entry['id'] == self.current:
                self.listbox.setCurrentItem(item)
        self.listbox.blockSignals(False)
        self.count_label.setText(f'YOUR ENTRIES  ·  {len(entries)}')

    def select(self, item, previous):
        if item is None:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        if entry_id == self.current:
            return
        if self.leave():
            entry = next((e for e in self.vault.entries if e['id'] == entry_id), None)
            self.load(entry)
            self.refresh()
        else:
            self.refresh()

    def load(self, entry):
        self.loading = True
        self.current = entry['id'] if entry else None
        self.title_edit.setText(entry['title'] if entry else '')
        self.kind.setCurrentText(entry['kind'] if entry else 'Note')
        self.tags_edit.setText(entry['tags'] if entry else '')
        self.content.setPlainText(entry['content'] if entry else '')
        self.reveal.setChecked(False)
        self.visibility()
        self.loading = False
        self.dirty = False
        self.delete_button.setEnabled(self.current is not None)

    def leave(self):
        if not self.dirty:
            return True
        result = QMessageBox.question(self, 'Unsaved changes', 'Save this entry before continuing?', QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if result == QMessageBox.StandardButton.Save:
            return self.save()
        return result == QMessageBox.StandardButton.Discard

    def new(self):
        if self.vault.cipher and self.leave():
            self.load(None)
            self.refresh()
            self.title_edit.setFocus()

    def save(self):
        if self.vault.cipher is None:
            return False
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.information(self, 'Add a title', 'Give this entry a title before saving.')
            return False
        entry = dict(id=self.current or str(uuid.uuid4()), title=title, kind=self.kind.currentText(), tags=self.tags_edit.text().strip(), content=self.content.toPlainText(), updated=datetime.now().isoformat())
        previous = self.vault.entries
        self.vault.entries = [e for e in previous if e['id'] != entry['id']] + [entry]
        try:
            self.vault.save()
        except OSError as error:
            self.vault.entries = previous
            QMessageBox.warning(self, 'Could not save', str(error))
            return False
        self.current = entry['id']
        self.dirty = False
        self.delete_button.setEnabled(True)
        self.refresh()
        self.statusBar().showMessage('Saved securely · ' + datetime.now().strftime('%H:%M'))
        return True

    def copy(self):
        self.copied_value = self.content.toPlainText()
        QApplication.clipboard().setText(self.copied_value)
        self.clipboard_timer.start(30000)
        self.statusBar().showMessage('Copied · Clipboard clears in 30 seconds')

    def clear_clipboard(self):
        self.clipboard_timer.stop()
        if self.copied_value is not None and QApplication.clipboard().text() == self.copied_value:
            QApplication.clipboard().clear()
        self.copied_value = None

    def delete(self):
        if not self.current:
            return
        result = QMessageBox.question(self, 'Delete entry', 'Permanently delete this entry?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return
        previous = self.vault.entries
        self.vault.entries = [e for e in previous if e['id'] != self.current]
        try:
            self.vault.save()
        except OSError as error:
            self.vault.entries = previous
            QMessageBox.warning(self, 'Could not delete', str(error))
            return
        self.load(None)
        self.refresh()
        self.statusBar().showMessage('Entry deleted')

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel):
            self.activity()
        return super().eventFilter(obj, event)

    def activity(self):
        if self.vault.cipher:
            self.idle_timer.start(300000)

    def auto_lock(self):
        if self.dirty and not self.save():
            self.activity()
            return
        self.lock(force=True)

    def lock(self, force=False):
        if self.vault.cipher and (force or self.leave()):
            self.idle_timer.stop()
            self.clear_clipboard()
            # Clear editor and undo history before disposing of the unlocked page.
            self.loading = True
            self.content.clear()
            self.title_edit.clear()
            self.tags_edit.clear()
            self.loading = False
            self.vault.lock()
            self.gate()

    def closeEvent(self, event):
        if self.vault.cipher is None or self.leave():
            self.idle_timer.stop()
            self.clear_clipboard()
            self.vault.lock()
            QApplication.instance().removeEventFilter(self)
            event.accept()
        else:
            event.ignore()


def main():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('QuickVault.Desktop.2')
    application = QApplication(sys.argv)
    application.setApplicationName('QuickVault')
    application.setStyle('Fusion')
    window = QuickVault()
    window.show()
    if '--smoke-test' in sys.argv:
        QTimer.singleShot(1000, window.close)
    return application.exec()


if __name__ == '__main__':
    sys.exit(main())
