"""QuickVault — a small, comfortable Windows notes and secrets app."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import uuid
from pathlib import Path
import sys

from vault import Vault

BG = '#f6f4ef'
PANEL = '#eaece5'
INK = '#263c34'
ACCENT = '#32735c'


class QuickVault(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('QuickVault')
        assets = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets'
        if (assets / 'quickvault.ico').exists():
            self.iconbitmap(str(assets / 'quickvault.ico'))
        self.geometry('1020x690')
        self.minsize(800, 560)
        self.configure(bg=BG)
        self.vault = Vault()
        self.current = None
        self.dirty = False
        self.clipboard_job = None
        self.idle_job = None
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TFrame', background=BG)
        self.style.configure('TLabel', background=BG, foreground=INK, font=('Segoe UI', 11))
        self.style.configure('TButton', font=('Segoe UI', 10), padding=(14, 9))
        self.style.configure('Accent.TButton', background=ACCENT, foreground='white')
        self.style.map('Accent.TButton', background=[('active', '#255b48')])
        self.style.configure('TEntry', padding=8, font=('Segoe UI', 11))
        self.bind_all('<Control-s>', lambda e: self.save())
        self.bind_all('<Control-n>', lambda e: self.new())
        self.bind_all('<Control-l>', lambda e: self.lock())
        self.bind_all('<KeyPress>', self.activity, add='+')
        self.bind_all('<ButtonPress>', self.activity, add='+')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.gate()

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def gate(self):
        self.clear()
        self.current = None
        self.dirty = False
        card = ttk.Frame(self, padding=40)
        card.place(relx=.5, rely=.5, anchor='center')
        ttk.Label(card, text='QuickVault', font=('Segoe UI', 30, 'bold')).pack(anchor='w')
        ttk.Label(card, text='A quiet place for your notes & secrets.', foreground='#6c7a70').pack(anchor='w', pady=(8, 30))
        creating = not self.vault.path.exists()
        ttk.Label(card, text='Create a master password' if creating else 'Welcome back. Unlock your vault.').pack(anchor='w')
        password = ttk.Entry(card, show='•', width=38)
        password.pack(pady=12)
        confirmation = None
        if creating:
            ttk.Label(card, text='Confirm password').pack(anchor='w')
            confirmation = ttk.Entry(card, show='•', width=38)
            confirmation.pack(pady=10)
            ttk.Label(card, text='Use at least 10 characters. Keep it safe: there is no reset.', font=('Segoe UI', 9)).pack(pady=8)

        def unlock():
            if creating and (len(password.get()) < 10 or password.get() != confirmation.get()):
                messagebox.showerror('Check password', 'Use at least 10 characters and matching passwords.', parent=self)
                return
            try:
                self.vault.unlock(password.get())
            except Exception:
                messagebox.showerror('Unable to unlock', 'The password is incorrect, or the vault cannot be read.', parent=self)
                return
            self.workspace()
            self.activity()

        ttk.Button(card, text='Create vault' if creating else 'Unlock vault', style='Accent.TButton', command=unlock).pack(fill='x', pady=16)
        password.bind('<Return>', lambda e: unlock())
        if confirmation:
            confirmation.bind('<Return>', lambda e: unlock())
        password.focus_set()

    def workspace(self):
        self.clear()
        sidebar = tk.Frame(self, bg=PANEL, width=280, padx=20, pady=24)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text='QuickVault', bg=PANEL, fg=INK, font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        tk.Label(sidebar, text='Keep the little things close.', bg=PANEL, fg='#6c7a70', font=('Segoe UI', 10)).pack(anchor='w', pady=(4, 24))
        self.search = tk.StringVar()
        ttk.Entry(sidebar, textvariable=self.search).pack(fill='x')
        tk.Label(sidebar, text='Search titles & tags', bg=PANEL, fg='#6c7a70', font=('Segoe UI', 9)).pack(anchor='w', pady=(5, 15))
        ttk.Button(sidebar, text='+  New entry   Ctrl+N', style='Accent.TButton', command=self.new).pack(fill='x', pady=(0, 16))
        self.listbox = tk.Listbox(sidebar, bg=PANEL, fg=INK, selectbackground=ACCENT, selectforeground='white', borderwidth=0, highlightthickness=0, font=('Segoe UI', 12), activestyle='none', exportselection=False)
        self.listbox.pack(fill='both', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.select)
        ttk.Button(sidebar, text='Lock vault   Ctrl+L', command=self.lock).pack(fill='x', pady=(18, 0))
        self.search.trace_add('write', lambda *a: self.refresh())
        main = ttk.Frame(self, padding=30)
        main.pack(side='left', fill='both', expand=True)
        actions = ttk.Frame(main)
        actions.pack(fill='x', pady=(0, 16))
        self.save_button = ttk.Button(actions, text='Save   Ctrl+S', style='Accent.TButton', command=self.save)
        self.save_button.pack(side='left')
        ttk.Button(actions, text='Copy value', command=self.copy).pack(side='left', padx=8)
        self.delete_button = ttk.Button(actions, text='Delete entry', command=self.delete)
        self.delete_button.pack(side='right')
        ttk.Label(main, text='Your everyday pocket', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
        ttk.Label(main, text='Notes, environment variables, and keys — all in one place.', foreground='#6c7a70').pack(anchor='w', pady=(6, 23))
        self.title_var = tk.StringVar()
        self.kind_var = tk.StringVar(value='Note')
        self.tags_var = tk.StringVar()
        ttk.Label(main, text='TITLE').pack(anchor='w')
        ttk.Entry(main, textvariable=self.title_var).pack(fill='x', pady=(6, 16))
        row = ttk.Frame(main)
        row.pack(fill='x')
        ttk.Label(row, text='Type').pack(side='left')
        ttk.Combobox(row, values=['Note', 'API key', 'Environment variable'], textvariable=self.kind_var, state='readonly', width=22).pack(side='left', padx=10)
        self.reveal = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text='Reveal secret', variable=self.reveal, command=self.visibility).pack(side='right')
        ttk.Label(main, text='CONTENT / VALUE').pack(anchor='w', pady=(20, 6))
        body = ttk.Frame(main)
        body.pack(fill='both', expand=True)
        self.content = tk.Text(body, height=5, width=30, wrap='word', bg='white', fg=INK, insertbackground=INK, relief='flat', padx=14, pady=14, font=('Consolas', 12), undo=True)
        scroll = ttk.Scrollbar(body, command=self.content.yview)
        self.content.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.content.pack(fill='both', expand=True)
        self.content.tag_configure('hidden', elide=True)
        self.cover = tk.Label(body, text='Secret hidden\nEnable “Reveal secret” to edit.', bg='white', fg='#6c7a70', font=('Segoe UI', 12))
        ttk.Label(main, text='TAGS  ·  comma separated').pack(anchor='w', pady=(16, 6))
        ttk.Entry(main, textvariable=self.tags_var).pack(fill='x')
        self.status = tk.StringVar(value='Encrypted locally · Locks after 5 minutes of inactivity')
        ttk.Label(main, textvariable=self.status, font=('Segoe UI', 9), foreground='#6c7a70').pack(anchor='w')
        for var in (self.title_var, self.tags_var, self.kind_var):
            var.trace_add('write', self.changed)
        self.kind_var.trace_add('write', lambda *a: self.visibility())
        self.content.bind('<<Modified>>', self.content_changed)
        self.refresh()
        self.load(None)

    def changed(self, *args):
        self.dirty = True

    def content_changed(self, event):
        if self.content.edit_modified():
            self.dirty = True
            self.content.edit_modified(False)

    def visibility(self):
        hidden = self.kind_var.get() != 'Note' and not self.reveal.get()
        self.content.configure(state='normal')
        self.content.tag_remove('hidden', '1.0', 'end')
        if hidden:
            self.content.tag_add('hidden', '1.0', 'end')
            self.content.configure(state='disabled')
            self.cover.place(relx=0, rely=0, relwidth=.95, relheight=1)
        else:
            self.cover.place_forget()

    def refresh(self):
        query = self.search.get().casefold()
        self.visible = [e for e in self.vault.entries if query in (e['title'] + ' ' + e['tags']).casefold()]
        self.visible.sort(key=lambda e: e['updated'], reverse=True)
        self.listbox.delete(0, 'end')
        for e in self.visible:
            self.listbox.insert('end', ('≡  ' if e['kind'] == 'Note' else '◆  ') + e['title'])

    def leave(self):
        if not self.dirty:
            return True
        result = messagebox.askyesnocancel('Unsaved entry', 'Save your changes before continuing?', parent=self)
        return self.save() if result else result is False

    def load(self, entry):
        self.current = entry['id'] if entry else None
        self.title_var.set(entry['title'] if entry else '')
        self.kind_var.set(entry['kind'] if entry else 'Note')
        self.tags_var.set(entry['tags'] if entry else '')
        self.content.configure(state='normal')
        self.content.delete('1.0', 'end')
        self.content.insert('1.0', entry['content'] if entry else '')
        self.content.edit_modified(False)
        self.reveal.set(False)
        self.visibility()
        self.dirty = False
        self.delete_button.configure(state='normal' if self.current else 'disabled')

    def select(self, event):
        indices = self.listbox.curselection()
        if indices:
            entry = self.visible[indices[0]]
            if entry['id'] != self.current and self.leave():
                self.load(entry)

    def new(self):
        if self.vault.cipher and self.leave():
            self.load(None)

    def save(self):
        if self.vault.cipher is None:
            return False
        title = self.title_var.get().strip()
        if not title:
            messagebox.showinfo('Add a title', 'Give this entry a title before saving.', parent=self)
            return False
        entry = dict(id=self.current or str(uuid.uuid4()), title=title, kind=self.kind_var.get(), tags=self.tags_var.get().strip(), content=self.content.get('1.0', 'end-1c'), updated=datetime.now().isoformat())
        previous = self.vault.entries
        self.vault.entries = [e for e in previous if e['id'] != entry['id']] + [entry]
        try:
            self.vault.save()
        except OSError as error:
            self.vault.entries = previous
            messagebox.showerror('Could not save', str(error), parent=self)
            return False
        self.current = entry['id']
        self.delete_button.configure(state='normal')
        self.dirty = False
        self.refresh()
        self.status.set('Saved securely · ' + datetime.now().strftime('%H:%M'))
        return True

    def copy(self):
        value = self.content.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(value)
        if self.clipboard_job:
            self.after_cancel(self.clipboard_job)
        def clear():
            try:
                if self.clipboard_get() == value:
                    self.clipboard_clear()
            except tk.TclError:
                pass
            self.clipboard_job = None
        self.clipboard_job = self.after(30000, clear)
        self.status.set('Copied · clipboard clears in 30 seconds')

    def delete(self):
        if self.current and messagebox.askyesno('Delete entry', 'Permanently delete this entry?', parent=self):
            previous = self.vault.entries
            self.vault.entries = [e for e in previous if e['id'] != self.current]
            try:
                self.vault.save()
            except OSError as error:
                self.vault.entries = previous
                messagebox.showerror('Could not delete', str(error), parent=self)
                return
            self.load(None)
            self.refresh()

    def activity(self, event=None):
        if self.idle_job:
            self.after_cancel(self.idle_job)
        if self.vault.cipher:
            self.idle_job = self.after(300000, self.auto_lock)

    def auto_lock(self):
        if self.dirty and not self.save():
            self.activity()
            return
        self.lock(force=True)

    def lock(self, force=False):
        if self.vault.cipher and (force or self.leave()):
            if self.idle_job:
                self.after_cancel(self.idle_job)
                self.idle_job = None
            self.clipboard_clear()
            self.vault.lock()
            self.gate()

    def close(self):
        if self.vault.cipher is None or self.leave():
            self.clipboard_clear()
            self.destroy()


if __name__ == '__main__':
    QuickVault().mainloop()
