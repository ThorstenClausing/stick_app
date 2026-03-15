# -*- coding: utf-8 -*-
"""
This file contains the description (class) of the graphical user interface of the Stick-App.

Created on Sat Apr 27 18:34:16 2024

@author: Thorsten
"""

import tkinter as tk
import tkinter.filedialog as fd
from tkinter import ttk
import tkinter.messagebox as mb
from os import path
from PIL import ImageTk, Image
import stick_funktionalitaet as sf

class StickApp(tk.Frame):
    """
    GUI application for generating and saving embroidery patterns.
    """
    def __init__(self, master):
        """
        Initializes the StickApp.

        Args:
            master: Parent Tkinter widget.
        """
        super().__init__(master)
        self.pack(pady=20)
        
        self.input_path = None
        self.current_pattern = None  # Stores the generated pattern dict
        
        # UI Elements
        self.load_button = ttk.Button(self, text="Bild auswählen", command=self.load_image)
        self.load_button.grid(row=0, column=0, padx=5, pady=5)

        self.gen_button = ttk.Button(self, text="Muster generieren", command=lambda: self.process(False))
        self.gen_button.grid(row=0, column=1, padx=5, pady=5)

        self.gen_no_bg_button = ttk.Button(self, text="Muster (ohne Hintergrund)", command=lambda: self.process(True))
        self.gen_no_bg_button.grid(row=0, column=2, padx=5, pady=5)

        self.save_button = ttk.Button(self, text="Muster speichern", command=self.save_pattern, state="disabled")
        self.save_button.grid(row=0, column=3, padx=5, pady=5)

        self.image_label = ttk.Label(self)
        self.image_label.grid(row=1, column=0, columnspan=4, pady=20)

    def load_image(self):
        """Opens a file dialog to select a source image."""
        self.input_path = fd.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if self.input_path:
            self.display_image(Image.open(self.input_path))
            self.current_pattern = None
            self.save_button.config(state="disabled")

    def process(self, remove_bg):
        """
        Generates the embroidery pattern and updates the UI preview.

        Args:
            remove_bg (bool): Whether to perform background removal.
        """
        if not self.input_path:
            mb.showerror("Fehler", "Bitte zuerst ein Bild auswählen.")
            return

        img = Image.open(self.input_path)
        if remove_bg:
            img = sf.remove_background(img)
        
        # Generate the pattern data
        self.current_pattern = sf.generate_embroidery_pattern(img)
        
        # Update UI
        self.display_image(self.current_pattern['pil_image'])
        self.save_button.config(state="normal")
        mb.showinfo("Fertig", "Stickmuster wurde generiert. Sie können es jetzt speichern.")

    def save_pattern(self):
        """Opens a save dialog and exports the current pattern to JPEG or PDF."""
        if not self.current_pattern:
            return

        base_name = path.basename(path.splitext(self.input_path)[0])
        output_path = fd.asksaveasfilename(
            initialfile=f"Stickmuster_{base_name}",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf"), ("JPEG Image", "*.jpg")]
        )

        if output_path:
            if output_path.lower().endswith('.pdf'):
                sf.save_as_pdf(output_path, self.current_pattern, f"Stickmuster: {base_name}")
            else:
                sf.save_as_jpeg(output_path, self.current_pattern)
            mb.showinfo("Erfolg", f"Datei gespeichert unter:\n{output_path}")

    def display_image(self, pil_img):
        """
        Resizes and displays a PIL image in the GUI label.

        Args:
            pil_img (PIL.Image): Image to display.
        """
        # Resize for preview while maintaining aspect ratio
        display_h = 600
        display_w = int(pil_img.width * (display_h / pil_img.height))
        img_resized = pil_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(img_resized)
        self.image_label.configure(image=photo)
        self.image_label.image = photo