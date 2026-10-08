import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import QuickVault
from vault import Vault


class AppTests(unittest.TestCase):
    def test_toolbar_save_and_delete_at_small_window(self):
        with tempfile.TemporaryDirectory() as directory:
            app = QuickVault()
            try:
                app.vault = Vault(Path(directory) / 'vault.json')
                app.vault.unlock('temporary test password')
                app.workspace()
                app.geometry('800x560')
                app.update()
                for button in (app.save_button, app.delete_button):
                    self.assertTrue(button.winfo_viewable())
                    self.assertLess(button.winfo_rooty() + button.winfo_height(), app.winfo_rooty() + app.winfo_height())
                app.title_var.set('Test note')
                app.content.insert('1.0', 'Test value')
                self.assertTrue(app.save())
                self.assertEqual(len(app.vault.entries), 1)
                self.assertEqual(str(app.delete_button['state']), 'normal')
                with patch('app.messagebox.askyesno', return_value=True):
                    app.delete()
                self.assertEqual(app.vault.entries, [])
            finally:
                app.destroy()
