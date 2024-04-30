# -*- coding: utf-8 -*-
"""
Diese Datei enthält die Beschreibung (Klasse) der graphischen Benutzeroberfläche der Stick-App.

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

class stick_app(tk.Frame):
    
    def __init__(self,master):
        super().__init__(master)
        self.eingabe_datei = None
        self.pack()
        self.ladeknopf = ttk.Button(self, text="Bild auswählen", command=self.laden)
        self.ladeknopf.pack()
        self.startknopf = ttk.Button(self, text="Stickmuster erzeugen", command=self.starten)
        self.startknopf.pack()
        self.bild = ttk.Label(self)
        self.bild.pack()
        
        
    def laden(self):
        self.eingabe_datei = fd.askopenfilename()
        zwischen_bild = Image.open(self.eingabe_datei)
        zwischen_bild = zwischen_bild.resize((zwischen_bild.width*700//zwischen_bild.height,700))
        eingabe_bild = ImageTk.PhotoImage(zwischen_bild)
        self.bild.configure(image=eingabe_bild)
        self.bild.image = eingabe_bild
        
    def starten(self):
        if self.eingabe_datei == None:
            mb.showerror(message="Keine Datei ausgewählt")
        else:
            ausgabe_string = path.split(path.splitext(self.eingabe_datei)[0])
            ausgabe_string = 'Stickmuster_' + ausgabe_string[1] + '.jpg'
            self.ausgabe_datei = fd.asksaveasfile(initialfile=ausgabe_string,defaultextension='jpg')
            sf.muster_generieren(self.eingabe_datei, self.ausgabe_datei)  
            zwischen_bild = Image.open(self.ausgabe_datei.name)
            zwischen_bild = zwischen_bild.resize((zwischen_bild.width*700//zwischen_bild.height,700))
            ausgabe_bild = ImageTk.PhotoImage(zwischen_bild)
            self.bild.configure(image=ausgabe_bild)
            self.bild.image = ausgabe_bild