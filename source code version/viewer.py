import os
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk


PALETTE = {
    "bg": "#f7f1e8",
    "panel": "#fffaf4",
    "panel_alt": "#f8ece7",
    "panel_soft": "#f3e3dd",
    "accent": "#d9909f",
    "accent_dark": "#bb7484",
    "accent_soft": "#f4dde3",
    "text": "#342b2e",
    "muted": "#7c6b70",
    "border": "#ead8cf",
    "thumb": "#fff7f1",
    "thumb_active": "#f4d8df",
    "canvas": "#f1e6de",
}

# ---------------- Samantha loader ---------------- #

def load_samantha(file_path):
    with open(file_path, "rb") as f:
        if f.read(3) != b"SAM":
            raise ValueError("Invalid .samantha file")

        width = int.from_bytes(f.read(2), "big")
        height = int.from_bytes(f.read(2), "big")

        if width <= 0 or height <= 0 or width > 5000 or height > 5000:
            raise ValueError("Invalid image size")

        pixels = []
        for _ in range(width * height):
            r = int.from_bytes(f.read(1), "big")
            g = int.from_bytes(f.read(1), "big")
            b = int.from_bytes(f.read(1), "big")
            pixels.append((r, g, b))

    return width, height, pixels


def make_image(width, height, pixels):
    img = Image.new("RGB", (width, height))
    img.putdata(pixels)
    return img


# ---------------- App state ---------------- #

current_img = None
tk_img = None
zoom_level = 1.0
fit_to_window = True
images = []
filtered_images = []
current_index = 0
current_path = None
current_folder = None
thumb_buttons = {}
search_var = None
info_panels_visible = False


# ---------------- UI actions ---------------- #

def get_visible_images():
    return filtered_images if filtered_images else images


def compute_fit_zoom(img):
    stage_width = image_stage.winfo_width() - 48
    stage_height = image_stage.winfo_height() - 48
    if stage_width <= 1 or stage_height <= 1:
        return max(zoom_level, 1.0)

    width, height = img.size
    width_ratio = stage_width / width
    height_ratio = stage_height / height
    return max(0.1, min(width_ratio, height_ratio))


def display_image(img):
    global tk_img, current_img

    current_img = img
    effective_zoom = compute_fit_zoom(img) if fit_to_window else zoom_level

    width, height = img.size
    scaled_width = max(1, int(width * effective_zoom))
    scaled_height = max(1, int(height * effective_zoom))
    scaled = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

    tk_img = ImageTk.PhotoImage(scaled)

    main_label.config(image=tk_img, text="")
    main_label.image = tk_img
    empty_state_label.place_forget()
    main_label.place(in_=image_stage, relx=0.5, rely=0.5, anchor="center")
    update_info_labels(width, height, effective_zoom)


def update_status(message):
    status_value.config(text=message)


def update_info_labels(width=None, height=None, effective_zoom=None):
    file_name = os.path.basename(current_path) if current_path else "No image selected"
    file_value.config(text=file_name)

    if width and height:
        size_value.config(text=f"{width} x {height}")
    elif current_img:
        img_width, img_height = current_img.size
        size_value.config(text=f"{img_width} x {img_height}")
    else:
        size_value.config(text="-")

    active_zoom = effective_zoom if effective_zoom is not None else zoom_level
    zoom_value.config(text=f"{active_zoom:.2f}x")
    mode_value.config(text="Fit" if fit_to_window else "Manual")
    folder_value.config(text=current_folder if current_folder else "No folder opened")
    collection_value.config(text=str(len(images)))
    results_value.config(text=str(len(get_visible_images()) if images else 0))

    if current_path and current_path in images:
        position_value.config(text=f"{images.index(current_path) + 1} / {len(images)}")
    else:
        position_value.config(text="-")


def update_thumbnail_selection():
    for path, button in thumb_buttons.items():
        is_active = path == current_path
        button.config(
            bg=PALETTE["thumb_active"] if is_active else PALETTE["thumb"],
            highlightbackground=PALETTE["accent"] if is_active else PALETTE["border"],
            highlightcolor=PALETTE["accent"],
            highlightthickness=2 if is_active else 1,
        )


def show_empty_state(message):
    main_label.config(image="", text="")
    main_label.image = None
    empty_state_label.config(text=message)
    empty_state_label.place(relx=0.5, rely=0.5, anchor="center")
    update_info_labels()


def load_file(path):
    global current_index, current_path

    try:
        path = os.path.normpath(path)
        w, h, pixels = load_samantha(path)
        img = make_image(w, h, pixels)
        current_path = path
        current_index = images.index(path)
        display_image(img)

        root.title(f".samantha Gallery - {os.path.basename(path)}")

        update_thumbnail_selection()
        update_info_labels(w, h)
        update_status("Image loaded")

    except Exception as e:
        messagebox.showerror("Error", str(e))


def rebuild_file_list(folder):
    global images, current_folder

    current_folder = folder
    images = []
    for file_name in os.listdir(folder):
        if file_name.lower().endswith(".samantha"):
            images.append(os.path.normpath(os.path.join(folder, file_name)))
    images.sort()


def open_folder():
    folder = filedialog.askdirectory(title="Open a folder of .samantha images")

    if not folder:
        return

    rebuild_file_list(folder)

    if not images:
        messagebox.showinfo("No files", "No .samantha files found in this folder")
        return

    search_var.set("")
    apply_search_filter()
    load_file(images[0])
    update_status("Folder loaded")


def open_file():
    selected_path = filedialog.askopenfilename(
        title="Select a .samantha file",
        filetypes=[("Samantha files", "*.samantha")],
    )

    if not selected_path:
        return

    selected_path = os.path.normpath(selected_path)
    rebuild_file_list(os.path.dirname(selected_path))

    if not images:
        messagebox.showinfo("No files", "No .samantha files found in this folder")
        return

    search_var.set("")
    apply_search_filter()
    load_file(selected_path)
    update_status("File loaded")


def load_thumbnails():
    global thumb_buttons

    thumb_buttons = {}

    for widget in thumb_list.winfo_children():
        widget.destroy()

    for path in get_visible_images():
        try:
            w, h, pixels = load_samantha(path)
            img = make_image(w, h, pixels)
            img.thumbnail((120, 120), Image.Resampling.LANCZOS)

            thumb = ImageTk.PhotoImage(img)

            btn = tk.Button(
                thumb_list,
                image=thumb,
                text=os.path.basename(path),
                compound="top",
                font=("Segoe UI", 10, "bold"),
                fg=PALETTE["text"],
                bg=PALETTE["thumb"],
                activebackground=PALETTE["thumb_active"],
                activeforeground=PALETTE["text"],
                relief="flat",
                bd=0,
                padx=12,
                pady=12,
                wraplength=140,
                justify="center",
                cursor="hand2",
                command=lambda p=path: load_file(p),
            )
            btn.image = thumb
            btn.pack(fill="x", padx=10, pady=8)
            thumb_buttons[path] = btn

        except Exception:
            continue

    thumb_canvas.update_idletasks()
    thumb_canvas.configure(scrollregion=thumb_canvas.bbox("all"))
    update_thumbnail_selection()
    update_info_labels()


def apply_search_filter(*_args):
    global filtered_images

    search_text = search_var.get().strip().lower()
    if search_text:
        filtered_images = [path for path in images if search_text in os.path.basename(path).lower()]
    else:
        filtered_images = images.copy()

    load_thumbnails()

    if current_path and current_path not in filtered_images:
        update_status("Current image is outside the filtered results")
    elif filtered_images:
        update_status("Gallery updated")
    elif images:
        update_status("No items match your search")


def show_previous(_event=None):
    visible_images = get_visible_images()
    if not visible_images or not current_path:
        return

    current_visible_index = visible_images.index(current_path) if current_path in visible_images else 0
    next_index = (current_visible_index - 1) % len(visible_images)
    load_file(visible_images[next_index])


def show_next(_event=None):
    visible_images = get_visible_images()
    if not visible_images or not current_path:
        return

    current_visible_index = visible_images.index(current_path) if current_path in visible_images else 0
    next_index = (current_visible_index + 1) % len(visible_images)
    load_file(visible_images[next_index])


def zoom_in(_event=None):
    global zoom_level, fit_to_window
    fit_to_window = False
    zoom_level += 0.15
    if current_img:
        display_image(current_img)
        update_status("Zoom updated")


def zoom_out(_event=None):
    global zoom_level, fit_to_window
    fit_to_window = False
    zoom_level = max(0.1, zoom_level - 0.15)
    if current_img:
        display_image(current_img)
        update_status("Zoom updated")


def fit_image():
    global fit_to_window
    fit_to_window = True
    if current_img:
        display_image(current_img)
        update_status("Image fitted to view")


def reset_zoom():
    global zoom_level, fit_to_window
    fit_to_window = False
    zoom_level = 1.0
    if current_img:
        display_image(current_img)
        update_status("Zoom reset")


def toggle_info_panels():
    global info_panels_visible

    info_panels_visible = not info_panels_visible

    if info_panels_visible:
        info_strip.pack(fill="x", after=toolbar)
        folder_row.pack(fill="x", after=info_strip)
        info_button.config(text="Hide Info")
    else:
        folder_row.pack_forget()
        info_strip.pack_forget()
        info_button.config(text="Info")


def style_button(button, *, accent=False):
    button.configure(
        font=("Segoe UI", 10, "bold"),
        fg="#ffffff" if accent else PALETTE["text"],
        bg=PALETTE["accent"] if accent else PALETTE["panel"],
        activeforeground="#ffffff" if accent else PALETTE["text"],
        activebackground=PALETTE["accent_dark"] if accent else PALETTE["panel_soft"],
        relief="flat",
        bd=0,
        padx=18,
        pady=10,
        cursor="hand2",
    )


def refresh_thumb_scrollregion(_event=None):
    thumb_canvas.configure(scrollregion=thumb_canvas.bbox("all"))


def on_mousewheel(event):
    thumb_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def on_stage_resize(_event):
    if fit_to_window and current_img:
        display_image(current_img)


# ---------------- GUI ---------------- #

root = tk.Tk()
root.title(".samantha Gallery")
root.geometry("1440x900")
root.minsize(1180, 780)
root.configure(bg=PALETTE["bg"])

search_var = tk.StringVar()
search_var.trace_add("write", apply_search_filter)

# Header
header_frame = tk.Frame(root, bg=PALETTE["bg"], padx=28, pady=24)
header_frame.pack(fill="x")

title_label = tk.Label(
    header_frame,
    text=".samantha Gallery",
    font=("Georgia", 26, "bold"),
    fg=PALETTE["text"],
    bg=PALETTE["bg"],
)
title_label.pack(anchor="w")

subtitle_label = tk.Label(
    header_frame,
    text="A soft, modern gallery for browsing .samantha artwork",
    font=("Segoe UI", 11),
    fg=PALETTE["muted"],
    bg=PALETTE["bg"],
)
subtitle_label.pack(anchor="w", pady=(4, 0))

# Toolbar
toolbar = tk.Frame(root, bg=PALETTE["bg"], padx=28, pady=6)
toolbar.pack(fill="x")

toolbar_card = tk.Frame(toolbar, bg=PALETTE["panel"], padx=16, pady=16, highlightbackground=PALETTE["border"], highlightthickness=1)
toolbar_card.pack(fill="x")

open_button = tk.Button(toolbar_card, text="Open File", command=open_file)
style_button(open_button, accent=True)
open_button.pack(side="left", padx=(0, 10))

open_folder_button = tk.Button(toolbar_card, text="Open Folder", command=open_folder)
style_button(open_folder_button)
open_folder_button.pack(side="left", padx=(0, 10))

prev_button = tk.Button(toolbar_card, text="Previous", command=show_previous)
style_button(prev_button)
prev_button.pack(side="left", padx=(0, 10))

next_button = tk.Button(toolbar_card, text="Next", command=show_next)
style_button(next_button)
next_button.pack(side="left", padx=(0, 18))

info_button = tk.Button(toolbar_card, text="Info", command=toggle_info_panels)
style_button(info_button)
info_button.pack(side="left", padx=(0, 10))

status_value = tk.Label(
    toolbar_card,
    text="Open a .samantha file to start browsing",
    font=("Segoe UI", 10),
    fg=PALETTE["muted"],
    bg=PALETTE["panel"],
)
status_value.pack(side="right")

# Info strip
info_strip = tk.Frame(root, bg=PALETTE["bg"], padx=28, pady=6)
info_strip.pack(fill="x")

info_card = tk.Frame(info_strip, bg=PALETTE["panel"], padx=20, pady=16, highlightbackground=PALETTE["border"], highlightthickness=1)
info_card.pack(fill="x")

def make_info_block(parent, column, title):
    caption = tk.Label(parent, text=title, font=("Segoe UI", 9, "bold"), fg=PALETTE["muted"], bg=PALETTE["panel"])
    caption.grid(row=0, column=column, sticky="w", padx=(24 if column else 0, 0))
    value = tk.Label(parent, text="-", font=("Segoe UI", 11, "bold"), fg=PALETTE["text"], bg=PALETTE["panel"])
    value.grid(row=1, column=column, sticky="w", padx=(24 if column else 0, 0), pady=(4, 0))
    return value


file_value = make_info_block(info_card, 0, "Current file")
size_value = make_info_block(info_card, 1, "Resolution")
zoom_value = make_info_block(info_card, 2, "Zoom")
mode_value = make_info_block(info_card, 3, "View mode")
position_value = make_info_block(info_card, 4, "Position")
collection_value = make_info_block(info_card, 5, "Collection")
results_value = make_info_block(info_card, 6, "Visible")

folder_row = tk.Frame(root, bg=PALETTE["bg"], padx=28, pady=6)
folder_row.pack(fill="x")

folder_card = tk.Frame(folder_row, bg=PALETTE["panel_alt"], padx=18, pady=14, highlightbackground=PALETTE["border"], highlightthickness=1)
folder_card.pack(fill="x")

folder_label = tk.Label(folder_card, text="Folder", font=("Segoe UI", 9, "bold"), fg=PALETTE["muted"], bg=PALETTE["panel_alt"])
folder_label.pack(anchor="w")

folder_value = tk.Label(folder_card, text="No folder opened", font=("Segoe UI", 10, "bold"), fg=PALETTE["text"], bg=PALETTE["panel_alt"])
folder_value.pack(anchor="w", pady=(4, 0))

info_strip.pack_forget()
folder_row.pack_forget()

# Main layout
container = tk.Frame(root, bg=PALETTE["bg"], padx=28, pady=18)
container.pack(fill="both", expand=True)

# Thumbnail sidebar
sidebar = tk.Frame(
    container,
    width=280,
    bg=PALETTE["panel"],
    highlightbackground=PALETTE["border"],
    highlightthickness=1,
)
sidebar.pack(side="left", fill="y", padx=(0, 20))
sidebar.pack_propagate(False)

sidebar_title = tk.Label(
    sidebar,
    text="Collection",
    font=("Georgia", 18, "bold"),
    fg=PALETTE["text"],
    bg=PALETTE["panel"],
)
sidebar_title.pack(anchor="w", padx=16, pady=(18, 4))

sidebar_subtitle = tk.Label(
    sidebar,
    text="Search and browse thumbnails from the current folder.",
    font=("Segoe UI", 10),
    fg=PALETTE["muted"],
    bg=PALETTE["panel"],
    wraplength=220,
    justify="left",
)
sidebar_subtitle.pack(anchor="w", padx=16, pady=(0, 14))

search_entry = tk.Entry(
    sidebar,
    textvariable=search_var,
    relief="flat",
    bd=0,
    bg=PALETTE["panel_soft"],
    fg=PALETTE["text"],
    font=("Segoe UI", 10),
    insertbackground=PALETTE["text"],
)
search_entry.pack(fill="x", padx=16, pady=(0, 14), ipady=10)

thumb_frame = tk.Frame(sidebar, bg=PALETTE["panel"])
thumb_frame.pack(fill="both", expand=True, padx=8, pady=(0, 12))

thumb_canvas = tk.Canvas(
    thumb_frame,
    bg=PALETTE["panel"],
    highlightthickness=0,
    bd=0,
    relief="flat",
)
thumb_scrollbar = tk.Scrollbar(thumb_frame, orient="vertical", command=thumb_canvas.yview)
thumb_canvas.configure(yscrollcommand=thumb_scrollbar.set)

thumb_scrollbar.pack(side="right", fill="y")
thumb_canvas.pack(side="left", fill="both", expand=True)

thumb_list = tk.Frame(thumb_canvas, bg=PALETTE["panel"])
thumb_canvas.create_window((0, 0), window=thumb_list, anchor="nw")
thumb_list.bind("<Configure>", refresh_thumb_scrollregion)
thumb_canvas.bind_all("<MouseWheel>", on_mousewheel)

# Main image area
main_frame = tk.Frame(
    container,
    bg=PALETTE["panel"],
    highlightbackground=PALETTE["border"],
    highlightthickness=1,
)
main_frame.pack(side="right", fill="both", expand=True)

stage_header = tk.Frame(main_frame, bg=PALETTE["panel"], padx=20, pady=18)
stage_header.pack(fill="x")

stage_title = tk.Label(stage_header, text="Preview", font=("Georgia", 20, "bold"), fg=PALETTE["text"], bg=PALETTE["panel"])
stage_title.pack(side="left", anchor="w")

stage_controls = tk.Frame(stage_header, bg=PALETTE["panel"])
stage_controls.pack(side="right")

fit_button = tk.Button(stage_controls, text="Fit", command=fit_image)
style_button(fit_button)
fit_button.pack(side="left", padx=(0, 10))

zoom_out_button = tk.Button(stage_controls, text="Zoom Out", command=zoom_out)
style_button(zoom_out_button)
zoom_out_button.pack(side="left", padx=(0, 10))

zoom_in_button = tk.Button(stage_controls, text="Zoom In", command=zoom_in)
style_button(zoom_in_button)
zoom_in_button.pack(side="left", padx=(0, 10))

reset_zoom_button = tk.Button(stage_controls, text="Reset Zoom", command=reset_zoom)
style_button(reset_zoom_button)
reset_zoom_button.pack(side="left")

image_stage = tk.Frame(main_frame, bg=PALETTE["canvas"], padx=28, pady=28)
image_stage.pack(fill="both", expand=True, padx=20, pady=(0, 20))
image_stage.bind("<Configure>", on_stage_resize)

main_label = tk.Label(image_stage, bg=PALETTE["canvas"], bd=0)
main_label.place(relx=0.5, rely=0.5, anchor="center")

empty_state_label = tk.Label(
    image_stage,
    text="Open a .samantha image to start your gallery view.",
    font=("Segoe UI", 15),
    fg=PALETTE["muted"],
    bg=PALETTE["canvas"],
)
empty_state_label.place(relx=0.5, rely=0.5, anchor="center")

update_info_labels()
show_empty_state("Open a .samantha image to start your gallery view.")

root.bind("<Left>", show_previous)
root.bind("<Right>", show_next)
root.bind("<plus>", zoom_in)
root.bind("<minus>", zoom_out)
root.bind("<Key-equal>", zoom_in)
root.bind("f", lambda _event: fit_image())

root.mainloop()