# -*- coding: utf-8 -*-
"""
This file contains the description (class) of the graphical user interface of the Stick-App.

Created on Sat Apr 27 18:34:16 2024

@author: Thorsten
"""

import tkinter as tk
import tkinter.filedialog as fd
import tkinter.ttk as ttk
import tkinter.messagebox as mb
from os import path
from PIL import ImageTk, Image

import stick_funktionalitaet as sf

class StickApp(tk.Frame):
    """
    A GUI application for generating embroidery patterns from images.

    This class creates a simple Tkinter window with two buttons:
    - "Bild auswählen" (Select Image): Opens a file dialog to choose an image file.
    - "Stickmuster erzeugen" (Generate Embroidery Pattern): Processes the selected
      image and generates an embroidery pattern, saving it to a file chosen by the user.
    """

    def __init__(self, master):
        """
        Initializes the StickApp GUI.

        Args:
            master: The parent Tkinter widget.
        """
        super().__init__(master)
        self.input_file = None
        self.pack()

        # Buttons
        self.load_button = ttk.Button(self, text="Bild auswählen", command=self.load_image)
        self.load_button.pack()
        self.start_button = ttk.Button(self, text="Stickmuster erzeugen", command=self.generate_pattern)
        self.start_button.pack()

        # Image display label
        self.image_label = ttk.Label(self)
        self.image_label.pack()

    def load_image(self):
        """
        Opens a file dialog to select an image and displays it in the GUI.
        """
        self.input_file = fd.askopenfilename()
        if self.input_file:
            image = Image.open(self.input_file)
            image = image.resize((image.width * 700 // image.height, 700))
            photo = ImageTk.PhotoImage(image)
            self.image_label.configure(image=photo)
            self.image_label.image = photo

    def generate_pattern(self):
        """
        Generates an embroidery pattern from the selected image and displays it.
        """
        if self.input_file is None:
            mb.showerror(message="Keine Datei ausgewählt")
        else:
            output_filename = path.split(path.splitext(self.input_file)[0])
            output_filename = 'Stickmuster_' + output_filename[1] + '.jpg'
            output_file = fd.asksaveasfile(initialfile=output_filename, defaultextension='jpg')
            if output_file:
                sf.muster_generieren(self.input_file, output_file)
                image = Image.open(output_file.name)
                image = image.resize((image.width * 700 // image.height, 700))
                photo = ImageTk.PhotoImage(image)
                self.image_label.configure(image=photo)
                self.image_label.image = photo
