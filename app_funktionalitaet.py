# -*- coding: utf-8 -*-
"""
This file contains the description (class) of the graphical user interface of the Stick-App.

@author: thors
"""

import tkinter as tk
import tkinter.filedialog as fd
from tkinter import ttk
import tkinter.messagebox as mb
from os import path
from PIL import ImageTk, Image
import stick_funktionalitaet as sf

class StickApp(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.pack(fill="both", expand=True)
        
        self.input_path = None
        self.current_pattern = None

        # --- Default Settings ---
        self.settings = {
            "crosses_x": tk.IntVar(value=150),
            "kmeans_n_clusters": tk.IntVar(value=20),
            "score_threshold": tk.DoubleVar(value=0.75),
            "num_objects": tk.IntVar(value=1),
            "paper_size": tk.StringVar(value="A4")
        }
        
        self.create_menubar()
        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=20, padx=20, expand=True)

    def create_menubar(self):
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # Datei Menu
        self.datei_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Datei", menu=self.datei_menu)
        self.datei_menu.add_command(label="Bild auswählen", command=self.load_image)
        self.datei_menu.add_command(label="Muster speichern", command=self.save_pattern, state="disabled")
        self.datei_menu.add_separator()
        self.datei_menu.add_command(label="Beenden", command=self.master.destroy)

        # Stickmuster Menu
        self.stick_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Stickmuster", menu=self.stick_menu)
        self.stick_menu.add_command(label="Muster generieren", command=lambda: self.process(False), state="disabled")
        self.stick_menu.add_command(label="Muster (ohne Hintergrund)", command=lambda: self.process(True), state="disabled")

        # Einstellungen Menu (NEW)
        self.settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Einstellungen", menu=self.settings_menu)
        self.settings_menu.add_command(label="Parameter anpassen", command=self.open_settings)

    def open_settings(self):
        """Opens a dialog window to change pattern parameters."""
        settings_win = tk.Toplevel(self)
        settings_win.title("Einstellungen")
        settings_win.geometry("300x350")
        settings_win.grab_set() # Make modal

        container = ttk.Frame(settings_win, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Anzahl Kreuzstiche horizontal:").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["crosses_x"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="Anzahl Farben:").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["kmeans_n_clusters"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="KI-Schwellenwert (0.1 - 1.0):").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["score_threshold"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="Anzahl Vordegrundobjekte:").pack(anchor="w")
        ttk.Entry(container, textvariable=self.settings["num_objects"]).pack(fill="x", pady=(0, 10))

        ttk.Label(container, text="PDF Papierformat:").pack(anchor="w")
        ttk.Combobox(container, textvariable=self.settings["paper_size"], 
                     values=["A4", "A3"], state="readonly").pack(fill="x", pady=(0, 20))

        ttk.Button(container, text="Schließen", command=settings_win.destroy).pack()

    def load_image(self):
        self.input_path = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if self.input_path:
            self.display_image(Image.open(self.input_path))
            self.current_pattern = None
            self.stick_menu.entryconfig("Muster generieren", state="normal")
            self.stick_menu.entryconfig("Muster (ohne Hintergrund)", state="normal")
            self.datei_menu.entryconfig("Muster speichern", state="disabled")

    def process(self, remove_bg):
        if not self.input_path: return
        img = Image.open(self.input_path)
        self.master.config(cursor="watch")
        self.master.update()
        
        try:
            if remove_bg:
                img = sf.remove_background(
                    img, 
                    score_threshold=self.settings["score_threshold"].get(),
                    num_objects=self.settings["num_objects"].get())
            
            self.current_pattern = sf.generate_embroidery_pattern(
                img, 
                kmeans_n_clusters=self.settings["kmeans_n_clusters"].get(),
                crosses_x=self.settings["crosses_x"].get()
            )
            self.display_image(self.current_pattern['pil_image'])
            self.datei_menu.entryconfig("Muster speichern", state="normal")
        except Exception as e:
            mb.showerror("Fehler", f"Verarbeitungsfehler: {e}")
        finally:
            self.master.config(cursor="")

    def save_pattern(self):
        if not self.current_pattern: return
        base_name = path.basename(path.splitext(self.input_path)[0])
        output_path = fd.asksaveasfilename(
            initialfile=f"Stickmuster_{base_name}",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf"), ("JPEG Image", "*.jpg")]
        )

        if output_path:
            if output_path.lower().endswith('.pdf'):
                # Map string selection to reportlab object
                p_size = sf.A3 if self.settings["paper_size"].get() == "A3" else sf.A4
                sf.save_as_pdf(output_path, self.current_pattern, f"Stickmuster: {base_name}", pagesize=p_size)
            else:
                sf.save_as_jpeg(output_path, self.current_pattern)
            mb.showinfo("Erfolg", "Datei gespeichert.")

    def display_image(self, pil_img):
        display_h = 600
        display_w = int(pil_img.width * (display_h / pil_img.height))
        if display_w > 1000:
            display_w = 1000
            display_h = int(pil_img.height * (display_w / pil_img.width))
        img_resized = pil_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img_resized)
        self.image_label.configure(image=photo)
        self.image_label.image = photo
