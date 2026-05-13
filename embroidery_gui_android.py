"""
GUI version for use on Android devices
"""
import io
import threading
from os import path, makedirs
import json

import PIL.Image
import numpy as np

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty, NumericProperty

# Import your existing logic
import embroidery_logic as el

class EmbroideryCanvas(ScatterLayout):
    """Custom widget to handle the pattern display and touch-to-edit."""
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.img_widget = KivyImage(allow_stretch=True, keep_ratio=True)
        self.add_widget(self.img_widget)
        self.do_rotation = False

    def on_touch_down(self, touch):
        # Handle zoom/pan first
        if super().on_touch_down(touch):
            # If we are in "paint" mode and it's a single touch, we might want to paint
            if self.app.edit_mode == "paint" and not touch.is_multitouch:
                self.process_paint_touch(touch)
            return True

    def on_touch_move(self, touch):
        if super().on_touch_move(touch):
            if self.app.edit_mode == "paint" and not touch.is_multitouch:
                self.process_paint_touch(touch)
            return True

    def process_paint_touch(self, touch):
        if not self.app.current_pattern:
            return

        # Map touch coordinates to the local image space
        local_x, local_y = self.to_local(*touch.pos)
        
        # Get image dimensions and scale
        img = self.app.current_pattern['pil_image']
        w, h = img.size
        
        # Normalize coordinates (0 to 1) relative to the widget size
        # Kivy (0,0) is bottom-left, PIL (0,0) is top-left
        norm_x = local_x / self.width
        norm_y = 1.0 - (local_y / self.height)

        if 0 <= norm_x <= 1 and 0 <= norm_y <= 1:
            grid_h, grid_w = self.app.current_pattern['matrix'].shape
            col = int(norm_x * grid_w)
            row = int(norm_y * grid_h)
            self.app.apply_edit(row, col)

class MainApp(App):
    edit_mode = StringProperty("none")
    
    def build(self):
        self.title = "Embroidery App"
        self.input_path = None
        self.current_pattern = None
        self.history = []
        self.selected_color_idx = 255
        self.texts = {}
        
        # Load settings and translations
        self.load_settings()
        self.load_translations()

        # UI Layout
        self.root_layout = BoxLayout(orientation='vertical')

        # Top Bar (Simplified Menu)
        self.action_bar = BoxLayout(size_hint_y=None, height='50dp', bg_color=(0.2, 0.2, 0.2, 1))
        btn_load = Button(text="Load Image")
        btn_load.bind(on_release=self.show_file_picker)
        
        self.btn_gen = Button(text="Generate", disabled=True)
        self.btn_gen.bind(on_release=lambda x: self.start_processing(False))

        btn_settings = Button(text="Settings")
        btn_settings.bind(on_release=self.open_settings)

        self.action_bar.add_widget(btn_load)
        self.action_bar.add_widget(self.btn_gen)
        self.action_bar.add_widget(btn_settings)

        # Main View Area
        self.canvas_area = EmbroideryCanvas(self)
        
        self.root_layout.add_widget(self.action_bar)
        self.root_layout.add_widget(self.canvas_area)

        return self.root_layout

    def load_translations(self):
        # Basic placeholder for your JSON logic
        self.texts = {"msg_loading": "Processing image..."}

    def load_settings(self):
        # Use your existing JSON logic here
        self.settings = {
            "kmeans_n_clusters": 20,
            "crosses_x": 150,
            "score_threshold": 0.75,
            "num_objects": 1,
            "model_version": "Version 1"
        }

    def show_file_picker(self, instance):
        content = BoxLayout(orientation='vertical')
        file_chooser = FileChooserIconView(path='.')
        content.add_widget(file_chooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height='50dp')
        btn_cancel = Button(text="Cancel")
        btn_load = Button(text="Load")
        
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_load)
        content.add_widget(btn_layout)

        popup = Popup(title="Select Image", content=content, size_hint=(0.9, 0.9))
        
        def load_selection(inst):
            if file_chooser.selection:
                self.input_path = file_chooser.selection[0]
                self.display_pil_image(PIL.Image.open(self.input_path))
                self.btn_gen.disabled = False
                popup.dismiss()

        btn_load.bind(on_release=load_selection)
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def display_pil_image(self, pil_img):
        """Converts PIL image to Kivy Texture and displays it."""
        # Ensure RGB
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        # Flip vertically for Kivy coordinate system
        pil_img = pil_img.transpose(PIL.Image.FLIP_TOP_BOTTOM)
        
        data = pil_img.tobytes()
        texture = Texture.create(size=pil_img.size, colorfmt='rgb')
        texture.blit_buffer(data, colorfmt='rgb', bufferfmt='ubyte')
        
        self.canvas_area.img_widget.texture = texture

    def start_processing(self, remove_bg):
        self.loading_popup = Popup(title="Please Wait", content=Label(text=self.texts["msg_loading"]),
                                   size_hint=(0.5, 0.3), auto_dismiss=False)
        self.loading_popup.open()
        
        # Run logic in a thread to keep UI alive
        threading.Thread(target=self.run_logic, args=(remove_bg,)).start()

    def run_logic(self, remove_bg):
        try:
            img = PIL.Image.open(self.input_path)
            # ... calls to el.remove_background and el.generate_embroidery_pattern ...
            # Using your existing logic:
            self.current_pattern = el.generate_embroidery_pattern(
                img, self.settings["kmeans_n_clusters"], self.settings["crosses_x"]
            )
            
            # Update UI on main thread
            Clock.schedule_once(lambda dt: self.on_process_finished())
        except Exception as e:
            print(f"Error: {e}")
            Clock.schedule_once(lambda dt: self.loading_popup.dismiss())

    def on_process_finished(self):
        self.display_pil_image(self.current_pattern['pil_image'])
        self.loading_popup.dismiss()
        self.show_palette_popup()

    def show_palette_popup(self):
        content = BoxLayout(orientation='vertical')
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        centers = self.current_pattern['cluster_centers']
        for i, color in enumerate(centers):
            rgb = [c/255.0 for c in color]
            btn = Button(text=f"Color {i}", background_color=(*rgb, 1), size_hint_y=None, height='40dp')
            btn.bind(on_release=lambda x, idx=i: self.set_edit_mode(idx))
            grid.add_widget(btn)

        scroll.add_widget(grid)
        content.add_widget(scroll)
        
        self.palette_popup = Popup(title="Select Color to Paint", content=content, size_hint=(0.4, 0.8))
        self.palette_popup.open()

    def set_edit_mode(self, color_idx):
        self.selected_color_idx = color_idx
        self.edit_mode = "paint"
        self.palette_popup.dismiss()

    def apply_edit(self, row, col):
        # Call your existing logic
        self.current_pattern = el.update_pattern_at_coord(
            self.current_pattern, row, col, self.selected_color_idx
        )
        # Refresh the texture
        self.display_pil_image(self.current_pattern['pil_image'])

    def open_settings(self, instance):
        # Implement a basic Popup with Sliders/Inputs to replace your Settings Window
        pass

if __name__ == '__main__':
    MainApp().run()
