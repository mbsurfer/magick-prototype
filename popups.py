import os
import sys
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.constants import *


def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class App(ttk.Window):

    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Python exe with popups")
        self.iconbitmap(resource_path('icon.ico'))
        self.geometry("700x450")

        self.messagebox_label = ttk.Label(self, text="Enter your name:")
        self.messagebox_label.pack(pady=20)

        self.my_entry = ttk.Entry(self, width=30)
        self.my_entry.pack(pady=0)

        self.mb_button = ttk.Button(self, text="Say Hello", command=self.popup)
        self.mb_button.pack(pady=40)

    def popup(self):
        if not self.my_entry.get():
            Messagebox.show_warning("You must enter a name!", "Warning")
        else:
            Messagebox.show_info(f"Hello, {self.my_entry.get()}!", "Greetings")


app = App()
app.mainloop()
