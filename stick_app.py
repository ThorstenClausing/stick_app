# -*- coding: utf-8 -*-
"""
Dieses Script startet die graphische Benutzeroberfläche der Stick-App

Created on Sat Apr 27 18:34:16 2024

@author: Thorsten
"""

import tkinter as tk
from app_funktionalitaet import stick_app

def main():
    """
    Launches the main GUI application.

    This function creates the Tkinter root window, initializes the stick_app 
    GUI, sets the window size and position, and starts the main event loop.
    """
    root = tk.Tk()
    gui = stick_app(root)
    breite = 1100
    hoehe = 800
    bildschirm_breite = root.winfo_screenwidth()
    bildschirm_hoehe = root.winfo_screenheight()
    x = (bildschirm_breite - breite)/2 
    y = (bildschirm_hoehe - hoehe)/2 - 25
    root.geometry('%dx%d+%d+%d' % (breite, hoehe, x, y))
    root.title("Stick-App")
    gui.mainloop()
    
if __name__ == "__main__":
    main()
