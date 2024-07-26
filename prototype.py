import os
import sys
import tkinter as tk
import ttkbootstrap as ttk
from tkinter.filedialog import askdirectory
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.toast import ToastNotification
from ttkbootstrap.icons import Icon, Emoji
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont
from pprint import pprint
import threading
import queue
from dataclasses import dataclass
import traceback
import subprocess


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024


def open_file(file_path):
    if sys.platform == "win32":
        os.startfile(file_path)
    elif sys.platform == "darwin":
        subprocess.call(['open', file_path])


def show_error(e):
    error_message = f"An unexpected error occurred:\n{str(e)}\n\nPlease restart the application."
    # Log the error details (optional)
    with open("error_log.txt", "a") as log_file:
        log_file.write(traceback.format_exc())
    # Show the error message to the user
    Messagebox.show_error(error_message, "Error")


class Panel:

    def __init__(self, file_name: str):
        self.file_name = file_name

        # get the basename of the Image
        # split the basename by the underscore
        image_basename = os.path.basename(file_name)
        image_basename = os.path.splitext(image_basename)[0]
        self.name_parts = image_basename.split('_')

    def __str__(self):
        return f"Episode: {self.episode}, Scene: {self.scene}, Frame: {self.frame}:end"

    def __lt__(self, other):
        return self.frame < other.frame

    @property
    def frame(self):
        try:
            return self.name_parts[0]
        except IndexError:
            return 'Undefined'

    @property
    def episode(self):
        try:
            return self.name_parts[1]
        except IndexError:
            return 'Undefined'

    @property
    def scene(self):
        try:
            return self.name_parts[2]
        except IndexError:
            return 'Undefined'


@dataclass
class Theme:
    name: str
    font_color: tuple[int, int, int]
    background_color: tuple[int, int, int]

    @classmethod
    def from_dict(cls, d):
        return Theme(
            name=d['name'],
            font_color=d['font_color'],
            background_color=d['background_color']
        )


THEMES = {
    "Dark": Theme.from_dict({
        "name": "Dark",
        "font_color": (122, 138, 163),
        "background_color": (0, 0, 0)
    }),
    "Light": Theme.from_dict({
        "name": "Light",
        "font_color": (0, 0, 0),
        "background_color": (255, 255, 255)
    }),
    "Previs": Theme.from_dict({
        "name": "Previs",
        "font_color": (254, 215, 0),
        "background_color": (0, 0, 0)
    })
}


class App(ttk.Window):

    def __init__(self):
        super().__init__(themename="darkly")

        self.message_queue = queue.Queue()
        self.check_queue()

        self.title("Magick Prototype")
        self.set_icon()
        self.geometry("1200x800")

        # Buttons
        self.buttons_frame = ttk.Frame(self)
        self.buttons_frame.pack(fill=X, pady=20, padx=20)

        self.select_dir_button = ttk.Button(self.buttons_frame, text="Select Folder", command=self.select_dir,
                                            style=PRIMARY)
        self.select_dir_button.grid(row=0, column=0, padx=(0, 10))

        self.pdf_button = ttk.Button(self.buttons_frame, text="Create PDFs", command=self.start_create_pdf_thread,
                                     state=DISABLED, style=SUCCESS)
        self.pdf_button.grid(row=0, column=1, padx=(0, 10))

        self.stop_pdf_button = ttk.Button(self.buttons_frame, text="Stop", command=self.stop, state=DISABLED,
                                          style=DANGER)
        self.stop_pdf_button.grid(row=0, column=2, padx=(0, 10))

        self.open_pdf_button = ttk.Button(self.buttons_frame, text="Open PDFs", command=self.open_pdf, state=DISABLED)
        self.open_pdf_button.grid(row=0, column=3, padx=(0, 10))

        self.reset_button = ttk.Button(self.buttons_frame, text="Reset", command=self.reset, style=WARNING)
        self.buttons_frame.grid_columnconfigure(4, weight=1)
        self.reset_button.grid(row=0, column=4, sticky=E)

        # Settings
        self.settings_frame = ttk.Frame(self)
        self.settings_frame.pack(fill=X, pady=(0, 20), padx=20)

        self.label_theme = ttk.Label(self.settings_frame, text="Theme", style=LIGHT)
        self.label_theme.grid(row=0, column=0, padx=(0, 0))

        self.select_theme = ttk.Combobox(self.settings_frame, values=list(THEMES.keys()), state=READONLY)
        self.select_theme.bind("<<ComboboxSelected>>", self.on_theme_selected)
        self.select_theme.current(0)
        self.select_theme.grid(row=0, column=1, padx=(10, 20))

        self.label_name = ttk.Label(self.settings_frame, text="Name", style=LIGHT)
        self.label_name.grid(row=0, column=2, padx=(0, 0))

        self.entry_name = ttk.Entry(self.settings_frame, width=60)
        self.entry_name.grid(row=0, column=3, padx=(10, 20))

        self.my_dir = None
        self.image_files_map: dict[Panel, str] = {}
        self.pdf_singles_save_path = None
        self.pdf_grid_save_path = None
        self.stop_pdf = False

        self.dir_label = ttk.Label(self, text="No directory selected", style=f"{INVERSE} {SECONDARY}")
        self.dir_label.pack(fill=X, padx=20, pady=(0, 10))

        # Treeview
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill=X, padx=20)

        self.tv = ttk.Treeview(self.tree_frame, show='headings', height=20, style=PRIMARY)
        self.tv.configure(columns=(
            'image queue', 'episode', 'scene', 'frame', 'state'
        ))
        self.tv.column('image queue', width=150, stretch=True)

        for col in self.tv['columns']:
            self.tv.heading(col, text=col.title(), anchor=W)

        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=self.scrollbar.set)

        self.tv.pack(side=LEFT, fill=BOTH, expand=True)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        # Progress Bar
        self.progress_frame = ttk.Frame(self)
        # Progress frame will be shown when the folder is selected

        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=HORIZONTAL, mode=DETERMINATE,
                                            style=f"{SUCCESS} {STRIPED}")
        self.progress_bar.pack(fill=X, expand=True)

        self.progress_label = ttk.Label(self.progress_frame, text="0 / 0 Images Processed", style=LIGHT, anchor=W)
        self.progress_label.pack(fill=X, pady=(5, 0))

        # GLOBAL SETTINGS
        default_theme = list(THEMES.keys())[0]
        self.font_color = THEMES[default_theme].font_color
        self.background_color = THEMES[default_theme].background_color

        # GRID PDF SETTINGS
        self.page_padding = 50
        self.page_title_padding = 100
        self.page_footer_padding = 70
        self.panel_padding = 50
        self.panel_rows = 3
        self.panel_columns = 3

        self.panel_page_map: dict[int, list[Panel]] = {}

    def set_icon(self):
        # if macOS use icns, if windows use ico
        # if sys.platform == "darwin":
        #     icon = f"{icon_name}.icns"
        # else:
        #     icon = f"{icon_name}.ico"
        # self.iconbitmap(resource_path(icon))
        self.iconphoto(False, tk.PhotoImage(file=resource_path("icon.png")))

    def on_theme_selected(self, event):
        selected_theme = self.select_theme.get()
        self.font_color = THEMES[selected_theme].font_color
        self.background_color = THEMES[selected_theme].background_color

    def check_queue(self):
        try:
            message = self.message_queue.get_nowait()
            if message == "PDFs created":
                ToastNotification(
                    title="Accio PDFs!",
                    message="Your files have been summoned",
                ).show_toast()
        except queue.Empty:
            pass
        self.after(100, self.check_queue)

    def get_image_size(self, image_path):
        full_path = os.path.join(self.my_dir, image_path)  # Get the full path of the item
        try:
            return format_size(os.path.getsize(full_path))  # Get the size of the item
        except OSError:
            return "Unavailable"  # In case of an error, e.g., file not found

    def select_dir(self):
        try:
            self.my_dir = askdirectory()

            if not self.my_dir:
                return

            self.reset()
            self.dir_label.config(text=self.my_dir)

            # Get a list of all the files in the directory
            list_dir = os.listdir(self.my_dir)

            panels: list[Panel] = []

            # Add the files to the text box
            for item in list_dir:
                # check if the item is an image file
                if not item.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                panels.append(Panel(item))

            panels.sort()

            for panel in panels:
                self.image_files_map[panel] = self.tv.insert('', 'end', values=(
                    panel.file_name, panel.episode, panel.scene, panel.frame, 'Pending'
                ))

            self.pdf_button.config(state=NORMAL)

            if self.entry_name.get() == "":
                self.entry_name.insert(0, os.path.basename(self.my_dir))

            self.progress_label.config(text=f"0 / {len(self.image_files_map)} Images Processed")
            self.show_progress()

        except Exception as e:
            show_error(e)

    def reset(self):
        self.image_files_map = {}
        self.dir_label.config(text='No directory selected')
        self.pdf_singles_save_path = None
        self.pdf_grid_save_path = None
        self.pdf_button.config(state=DISABLED)
        self.stop_pdf_button.config(state=DISABLED)
        self.open_pdf_button.config(state=DISABLED)
        # self.reset_theme()
        self.reset_progress()
        self.entry_name.delete(0, 'end')
        for i in self.tv.get_children():
            self.tv.delete(i)

    def reset_theme(self):
        default_theme = list(THEMES.keys())[0]
        self.select_theme.set(default_theme)
        self.font_color = THEMES[default_theme].font_color
        self.background_color = THEMES[default_theme].background_color

    def reset_progress(self):
        self.progress_frame.pack_forget()
        self.progress_bar['value'] = 0
        self.progress_label.config(text="0 / 0 Images Processed")

    def show_progress(self):
        self.progress_frame.pack(fill=X, padx=20, pady=10)

    def update_tv_item_state(self, tv_item, state):
        values = self.tv.item(tv_item, 'values')
        self.tv.item(tv_item, values=(values[0], values[1], values[2], values[3], state))
        self.update_idletasks()

    def stop(self):
        self.stop_pdf = True
        self.stop_pdf_button.config(state=DISABLED)
        self.reset_button.config(state=NORMAL)

    def start_create_pdf_thread(self):
        self.select_dir_button.config(state=DISABLED)
        self.stop_pdf_button.config(state=NORMAL)
        self.reset_button.config(state=DISABLED)
        self.stop_pdf = False

        pdf_thread = threading.Thread(target=self.create_pdf)
        pdf_thread.start()

    def create_pdf(self):
        try:
            if not self.image_files_map:
                return

            pdf_file_name = self.entry_name.get()
            target_dir = os.path.dirname(self.my_dir)
            self.pdf_singles_save_path = f"{target_dir}/{pdf_file_name}.pdf"
            self.pdf_grid_save_path = f"{target_dir}/{pdf_file_name}_grid.pdf"

            background_color = tuple(value / 255 for value in self.background_color)

            c_singles = None
            c_grid = None
            grid_row = 0
            grid_column = 0
            grid_page = 1
            counter = 0
            for panel, tv_item in self.image_files_map.items():

                if self.stop_pdf:
                    break

                # Update the Treeview item to indicate processing
                self.update_tv_item_state(tv_item, 'Processing')

                single_panel_img_path, single_panel_img = self.create_panel_image(panel, style="single")
                grid_panel_img_path, grid_panel_img = self.create_panel_image(panel, style="grid")

                self.update_tv_item_state(tv_item, 'Adding to PDFs')

                # adjust the canvas size
                if not c_singles:
                    c_singles = canvas.Canvas(self.pdf_singles_save_path,
                                              pagesize=[single_panel_img.width, single_panel_img.height])

                c_singles.drawImage(f"{single_panel_img_path}", 0, 0)
                self.add_filename(c_singles, pdf_file_name, offset=10, font_size=18)
                c_singles.showPage()

                grid_page_width = (
                        (grid_panel_img.width * self.panel_columns) +
                        (self.panel_padding * (self.panel_columns - 1)) +
                        (self.page_padding * 2)
                )
                grid_page_height = (
                        (grid_panel_img.height * self.panel_rows) +
                        (self.panel_padding * (self.panel_rows - 1)) +
                        (self.page_padding * 2) +
                        self.page_title_padding +
                        self.page_footer_padding
                )
                if not c_grid:
                    c_grid = canvas.Canvas(self.pdf_grid_save_path, pagesize=[grid_page_width, grid_page_height])
                    c_grid.setFillColorRGB(*background_color)
                    c_grid.rect(0, 0, grid_page_width, grid_page_height, fill=1)

                if grid_row < self.panel_rows:
                    x_offset, y_offset = self.calculate_xy_offsets(grid_panel_img, grid_row, grid_column,
                                                                   grid_page_height)
                    c_grid.drawImage(f"{grid_panel_img_path}", x=x_offset, y=y_offset)
                    self.add_panel_to_page(panel, grid_page)

                    if grid_column < (self.panel_columns - 1):
                        grid_column += 1
                    else:
                        grid_row += 1
                        grid_column = 0
                else:
                    self.add_page_number(c_grid, grid_page, grid_page_width)
                    self.add_filename(c_grid, pdf_file_name)
                    self.add_page_title(c_grid, grid_page, grid_page_width, grid_page_height)

                    # Start New Page
                    c_grid.showPage()
                    c_grid.setFillColorRGB(*background_color)
                    c_grid.rect(0, 0, grid_page_width, grid_page_height, fill=1)
                    grid_row = 0
                    grid_column = 0
                    grid_page += 1

                    # First Image of the new Page
                    x_offset, y_offset = self.calculate_xy_offsets(grid_panel_img, grid_row, grid_column,
                                                                   grid_page_height)
                    c_grid.drawImage(f"{grid_panel_img_path}", x=x_offset, y=y_offset)
                    self.add_panel_to_page(panel, grid_page)

                # if is last item, add the page number and title
                if panel == list(self.image_files_map.keys())[-1]:
                    self.add_page_number(c_grid, grid_page, grid_page_width)
                    self.add_filename(c_grid, pdf_file_name)
                    self.add_page_title(c_grid, grid_page, grid_page_width, grid_page_height)

                # Remove the item from the Treeview and the image_files_map
                self.tv.delete(tv_item)

                # Update progress
                counter += 1
                self.progress_bar['value'] = (100 / len(self.image_files_map)) * counter
                self.progress_label.config(text=f"{counter} / {len(self.image_files_map)} Images Processed")

                # Make sure we see the GUI updates
                self.update_idletasks()

            c_singles.save()
            c_grid.save()

            # Update the app state
            self.image_files_map = {}
            self.panel_page_map = {}
            self.open_pdf_button.config(state=NORMAL)
            self.stop_pdf_button.config(state=DISABLED)
            self.pdf_button.config(state=DISABLED)
            self.reset_button.config(state=NORMAL)
            self.select_dir_button.config(state=NORMAL)

            # Post a message to the queue
            self.message_queue.put("PDFs created")

        except Exception as e:
            show_error(e)

    def add_panel_to_page(self, panel: Panel, page: int):
        if page not in self.panel_page_map:
            self.panel_page_map[page] = []
        self.panel_page_map[page].append(panel)

    def add_page_title(self, c, page_number, page_width, page_height):
        included_panels = self.panel_page_map[page_number]

        # get the first and last episode numbers
        first_episode = included_panels[0].episode
        last_episode = included_panels[-1].episode

        combined_episode = f"{first_episode}-{last_episode}" if first_episode != last_episode else first_episode

        # get the first and last scene numbers
        first_scene = included_panels[0].scene
        last_scene = included_panels[-1].scene

        combined_scene = f"{first_scene}-{last_scene}" if first_scene != last_scene else first_scene

        text = f"{combined_episode}_{combined_scene}"
        font_color = tuple(value / 255 for value in self.font_color)
        c.setFillColorRGB(*font_color)
        c.setFont("Helvetica", 48)
        text_width = c.stringWidth(text, "Helvetica", 48)
        c.drawString(((page_width - text_width) / 2), (page_height - self.page_title_padding), text)

    def add_page_number(self, c, page_number, page_width):
        font_color = tuple(value / 255 for value in self.font_color)
        c.setFillColorRGB(*font_color)
        c.setFont("Helvetica", 32)
        c.drawString(page_width - 50, 50, str(page_number))

    def add_filename(self, c, text, offset=50, font_size=32):
        font_color = tuple(value / 255 for value in self.font_color)
        c.setFillColorRGB(*font_color)
        c.setFont("Helvetica", font_size)
        c.drawString(offset, offset, text)

    def calculate_xy_offsets(self, panel_img, row, col, page_height):
        """
        - row and col start at 0
        - 0 x-offset and 0 y-offset is the bottom left corner of the canvas
        - the position of a placed image is oriented from its bottom left corner
        """
        x_offset = (panel_img.width * col) + (self.panel_padding * col) + self.page_padding
        y_offset = page_height - self.page_padding - self.page_title_padding - panel_img.height - (
                (panel_img.height + self.panel_padding) * row)
        return x_offset, y_offset

    def create_panel_image(self, panel: Panel, style="single"):

        add_header = True
        add_footer = True

        if style == "grid":
            add_header = False

        # todo: allow user to adjust these settings at runtime
        header_padding = 30 if add_header else 0
        footer_padding = 30 if add_footer else 0
        header_font_size = 24
        footer_font_size = 35
        header_text_padding = 10 if add_header else 0
        footer_text_padding = 15 if add_footer else 0

        font_color = self.font_color
        background_color = self.background_color

        ########################################

        original_image = Image.open(f"{self.my_dir}/{panel.file_name}")
        original_width, original_height = original_image.size

        header_text = f"{panel.episode}_{panel.scene}"
        footer_text = f"{panel.frame}"

        # create header and footer text
        # font = ImageFont.truetype(font="arial.ttf", size=24)
        header_font = ImageFont.load_default(size=header_font_size)  # Use the built-in default font
        footer_font = ImageFont.load_default(size=footer_font_size)  # Use the built-in default font
        ht_left, ht_top, ht_right, ht_bottom = header_font.getbbox(header_text)
        bt_left, bt_top, bt_right, bt_bottom = footer_font.getbbox(footer_text)

        # Add space for text and some padding
        total_height = original_height + header_padding + footer_padding

        # Create a new blank image
        new_image = Image.new("RGB", (original_width, int(total_height)), color=background_color)

        # Paste the original image below the header
        new_image.paste(original_image, (0, header_padding))

        # Draw the image
        draw = ImageDraw.Draw(new_image)

        # Add text above
        if add_header:
            header_text_x = int((original_width - ht_right) / 2)  # Center the text
            text_image = Image.new("RGB", (ht_right, ht_bottom), color=background_color)
            draw = ImageDraw.Draw(text_image)
            draw.text((0, 0), header_text, fill=font_color, font=header_font)
            new_image.paste(text_image, (header_text_x, header_text_padding))

        # Add text below
        if add_footer:
            footer_text_x = int((original_width - bt_right) / 2)  # Center the text
            text_image = Image.new("RGB", (bt_right, bt_bottom), color=background_color)
            draw = ImageDraw.Draw(text_image)
            draw.text((0, 0), footer_text, fill=font_color, font=footer_font)
            footer_text_y = total_height - bt_bottom - footer_text_padding
            new_image.paste(text_image, (footer_text_x, footer_text_y))

        # create panel dir if not exists
        panel_dir = f"{os.path.dirname(self.my_dir)}/panels/{style}"
        if not os.path.exists(panel_dir):
            os.makedirs(panel_dir, exist_ok=True)

        # Save or display the new image
        new_image_path = f"{panel_dir}/{panel.frame}_{panel.episode}_{panel.scene}.jpg"
        new_image.save(new_image_path, "JPEG")
        return new_image_path, new_image

    def open_pdf(self):
        if self.pdf_singles_save_path:
            open_file(self.pdf_singles_save_path)
        if self.pdf_grid_save_path:
            open_file(self.pdf_grid_save_path)


if __name__ == "__main__":
    app = App()
    app.mainloop()
