import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from app import QuickVault
from vault import Vault


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setStyle('Fusion')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        vault = Vault(Path(self.temp.name) / 'vault.json')
        vault.unlock('temporary test password')
        self.app = QuickVault(vault)
        self.app.workspace()
        self.app.show()
        self.qt.processEvents()

    def tearDown(self):
        self.app.dirty = False
        self.app.close()
        self.qt.processEvents()
        self.temp.cleanup()

    def save_note(self, title='Test note', content='Test value'):
        self.app.title_edit.setText(title)
        self.app.content.setPlainText(content)
        self.assertTrue(self.app.save())

    def test_save_delete_and_minimum_layout(self):
        self.app.resize(820, 620)
        self.qt.processEvents()
        for widget in (self.app.save_button, self.app.delete_button, self.app.tags_edit):
            self.assertTrue(widget.isVisible())
            point = widget.mapTo(self.app, widget.rect().bottomRight())
            self.assertLess(point.y(), self.app.height())
        self.save_note()
        self.assertTrue(self.app.delete_button.isEnabled())
        with patch('app.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            self.app.delete()
        self.assertEqual(self.app.vault.entries, [])
        self.assertFalse(self.app.delete_button.isEnabled())

    def test_secret_search_copy_and_lock_roundtrip(self):
        self.save_note('Service token', 'sk-test-only')
        self.app.kind.setCurrentText('API key')
        self.assertTrue(self.app.save())
        self.assertEqual(self.app.content_stack.currentIndex(), 1)
        self.app.reveal.setChecked(True)
        self.assertEqual(self.app.content_stack.currentIndex(), 0)
        self.app.search.setText('service')
        self.assertEqual(self.app.listbox.count(), 1)
        self.app.copy()
        self.assertEqual(QApplication.clipboard().text(), 'sk-test-only')
        self.app.clear_clipboard()
        self.assertEqual(QApplication.clipboard().text(), '')
        self.app.lock(force=True)
        self.assertIsNone(self.app.vault.cipher)
        self.app.password.setText('temporary test password')
        self.app.unlock()
        self.assertEqual(self.app.vault.entries[0]['content'], 'sk-test-only')

    def test_cancel_selection_preserves_draft(self):
        self.save_note('First')
        self.app.new()
        self.save_note('Second')
        self.app.content.setPlainText('Unsaved draft')
        current = self.app.current
        with patch('app.QMessageBox.question', return_value=QMessageBox.StandardButton.Cancel):
            self.app.listbox.setCurrentRow(1)
        self.assertEqual(self.app.current, current)
        self.assertEqual(self.app.content.toPlainText(), 'Unsaved draft')
        self.assertEqual(self.app.listbox.currentItem().data(Qt.ItemDataRole.UserRole), current)

    def test_failed_save_preserves_entries(self):
        self.save_note()
        previous = list(self.app.vault.entries)
        self.app.content.setPlainText('Changed value')
        with patch.object(self.app.vault, 'save', side_effect=OSError('disk unavailable')), patch('app.QMessageBox.warning'):
            self.assertFalse(self.app.save())
        self.assertEqual(self.app.vault.entries, previous)
        self.assertTrue(self.app.dirty)
