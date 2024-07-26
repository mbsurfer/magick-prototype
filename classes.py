import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class App(ttk.Window):

    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Tkinter.com - Object Oriented Programming")
        self.iconbitmap('icon.ico')
        self.geometry("700x450")

        self.my_label = ttk.Label(self, text="Hello, World!")
        self.my_label.pack(pady=20)

        self.my_button = ttk.Button(self, text="Click Me!", command=self.change, style=PRIMARY)
        self.my_button.pack(pady=20)

        self.phrases = ["I am changed!", "I am different!", "I am new!"]
        self.phrases_iterator = iter(self.phrases)

        MyFrame(self)

    def change(self):
        try:
            next_phrase = next(self.phrases_iterator)
        except StopIteration:
            self.phrases_iterator = iter(self.phrases)
            next_phrase = next(self.phrases_iterator)
        self.my_label.config(text=next_phrase)


class MyFrame(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        self.pack(pady=20)
        self.my_button1 = ttk.Button(self, text="Click Me!", command=parent.change)
        self.my_button2 = ttk.Button(self, text="Click Me!", command=parent.change)
        self.my_button3 = ttk.Button(self, text="Click Me!", command=parent.change)

        self.my_button1.grid(row=0, column=0, padx=10)
        self.my_button2.grid(row=0, column=1, padx=10)
        self.my_button3.grid(row=0, column=2, padx=10)


app = App()
app.mainloop()
