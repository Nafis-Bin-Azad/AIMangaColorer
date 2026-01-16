"""
Manga Colorizer - Tkinter Desktop App
Simple GUI for colorizing manga pages using Stable Diffusion 1.5 + ControlNet
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
from pathlib import Path
import logging

from sd_pipeline import SD15Pipeline
from image_utils import ImageUtils
from config import DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT, COLORIZATION_PARAMS, OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MangaColorizerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Manga Colorizer - SD1.5")
        self.root.geometry("1200x700")
        
        # State
        self.input_path = None
        self.output_path = None
        self.original_image = None
        self.colored_image = None
        self.pipeline = None
        self.mcv2_engine = None
        self.image_utils = None
        self.is_processing = False
        
        # Create UI
        self._create_ui()
        
        # Output directory
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
    
    def _create_ui(self):
        """Create the UI layout"""
        # Top controls frame
        controls_frame = ttk.Frame(self.root, padding="10")
        controls_frame.pack(fill=tk.X)
        
        # File selection
        ttk.Label(controls_frame, text="Input:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.input_label = ttk.Label(controls_frame, text="No file selected", foreground="gray")
        self.input_label.grid(row=0, column=1, padx=5, sticky=tk.W)
        
        self.browse_btn = ttk.Button(controls_frame, text="Browse...", command=self.select_file)
        self.browse_btn.grid(row=0, column=2, padx=5)
        
        self.colorize_btn = ttk.Button(controls_frame, text="Colorize", command=self.start_colorization, state=tk.DISABLED)
        self.colorize_btn.grid(row=0, column=3, padx=5)
        
        self.save_btn = ttk.Button(controls_frame, text="Save As...", command=self.save_result, state=tk.DISABLED)
        self.save_btn.grid(row=0, column=4, padx=5)
        
        # Engine selection
        ttk.Label(controls_frame, text="Engine:").grid(row=1, column=0, padx=5, sticky=tk.W)
        self.engine_var = tk.StringVar(value="Fast (Manga v2)")
        engine_dropdown = ttk.Combobox(
            controls_frame,
            textvariable=self.engine_var,
            values=["Fast (Manga v2)", "SD1.5 (Slow, fallback)"],
            state="readonly",
            width=25
        )
        engine_dropdown.grid(row=1, column=1, columnspan=2, padx=5, sticky=tk.W)
        
        ttk.Label(controls_frame, text="Fast: 30-60s, preserves text perfectly", foreground="gray", font=("TkDefaultFont", 9)).grid(row=1, column=3, columnspan=2, padx=5, sticky=tk.W)
        
        # Progress frame
        progress_frame = ttk.Frame(self.root, padding="10")
        progress_frame.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="green")
        self.status_label.pack()
        
        # Images frame
        images_frame = ttk.Frame(self.root, padding="10")
        images_frame.pack(fill=tk.BOTH, expand=True)
        
        # Original image
        original_frame = ttk.LabelFrame(images_frame, text="Original", padding="10")
        original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.original_canvas = tk.Canvas(original_frame, bg="gray20")
        self.original_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Colored image
        colored_frame = ttk.LabelFrame(images_frame, text="Colored", padding="10")
        colored_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.colored_canvas = tk.Canvas(colored_frame, bg="gray20")
        self.colored_canvas.pack(fill=tk.BOTH, expand=True)
    
    def select_file(self):
        """Open file dialog to select manga image"""
        filetypes = (
            ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("All files", "*.*")
        )
        
        filename = filedialog.askopenfilename(
            title="Select manga image",
            filetypes=filetypes
        )
        
        if filename:
            self.input_path = Path(filename)
            self.input_label.config(text=filename, foreground="black")
            self.colorize_btn.config(state=tk.NORMAL)
            
            # Load and display original image
            try:
                self.original_image = Image.open(self.input_path)
                self._display_image(self.original_image, self.original_canvas)
                logger.info(f"Loaded image: {self.input_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
                logger.error(f"Failed to load image: {e}")
    
    def _display_image(self, image, canvas):
        """Display image on canvas, scaling to fit"""
        if image is None:
            return
        
        # Get canvas size
        canvas.update()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 400
            canvas_height = 500
        
        # Calculate scaling
        img_width, img_height = image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize and display
        display_img = image.resize((new_width, new_height), Image.LANCZOS)
        photo = ImageTk.PhotoImage(display_img)
        
        canvas.delete("all")
        canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
        canvas.image = photo  # Keep a reference
    
    def start_colorization(self):
        """Start colorization in a separate thread"""
        if self.is_processing:
            return
        
        if not self.input_path:
            messagebox.showwarning("No File", "Please select an image first")
            return
        
        self.is_processing = True
        self.colorize_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.update_status("Initializing...", "blue")
        
        # Run in thread to prevent UI freeze
        thread = threading.Thread(target=self.colorize_image, daemon=True)
        thread.start()
    
    def colorize_image(self):
        """Perform colorization (runs in separate thread)"""
        try:
            # Initialize image utils if needed
            if self.image_utils is None:
                self.image_utils = ImageUtils()
            
            # Determine which engine to use
            engine_choice = self.engine_var.get()
            
            if "Fast" in engine_choice:
                # Use MCV2 engine (FAST)
                if self.mcv2_engine is None:
                    self.update_status("Loading Fast Colorizer (first time, ~600MB download)...", "blue")
                    from mcv2_engine import MangaColorizationV2Engine
                    from config import MCV2_PARAMS
                    
                    self.mcv2_engine = MangaColorizationV2Engine()
                    self.mcv2_engine.ensure_weights()
                    self.mcv2_engine.load_model()
                
                # Preprocess (MCV2 can handle larger images)
                self.update_status("Preprocessing image...", "blue")
                processed, metadata = self.image_utils.preprocess(
                    self.original_image,
                    max_side=1024
                )
                
                # Colorize with MCV2
                self.update_status("Colorizing (30-60 seconds)...", "orange")
                from config import MCV2_PARAMS
                colored = self.mcv2_engine.colorize(
                    processed,
                    preserve_ink=MCV2_PARAMS["preserve_ink"],
                    ink_threshold=MCV2_PARAMS["ink_threshold"],
                    size=MCV2_PARAMS["size"],
                    denoise=MCV2_PARAMS["denoise"],
                    denoise_sigma=MCV2_PARAMS["denoise_sigma"]
                )
                
                # Postprocess
                self.update_status("Finalizing...", "blue")
                final = self.image_utils.postprocess(colored, metadata)
                
            else:
                # Use SD1.5 fallback (SLOW)
                if self.pipeline is None:
                    self.update_status("Loading SD1.5 (first time, ~2GB download)...", "blue")
                    from config import SD15_PARAMS
                    self.pipeline = SD15Pipeline(progress_callback=self.update_progress)
                    self.pipeline.load_models()
                
                # Preprocess
                self.update_status("Preprocessing image...", "blue")
                from config import SD15_PARAMS
                processed, metadata = self.image_utils.preprocess(
                    self.original_image,
                    max_side=SD15_PARAMS["max_side"]
                )
                
                # Extract lineart for control
                self.update_status("Extracting lineart...", "blue")
                lineart = self.image_utils.extract_lineart(processed)
                
                # Ensure lineart matches processed size
                if lineart.size != processed.size:
                    lineart = lineart.resize(processed.size, Image.LANCZOS)
                
                # Detect text bubbles
                self.update_status("Detecting text bubbles...", "blue")
                text_mask = self.image_utils.detect_text_bubbles(processed)
                
                # Colorize with SD1.5
                self.update_status("Colorizing (5-7 minutes)...", "orange")
                colored = self.pipeline.colorize(
                    image=processed,
                    control_image=lineart,
                    mask=text_mask,
                    prompt=DEFAULT_PROMPT,
                    negative_prompt=DEFAULT_NEGATIVE_PROMPT,
                    **SD15_PARAMS
                )
                
                # Preserve ink
                self.update_status("Preserving original lineart...", "blue")
                colored = self.image_utils.preserve_ink(processed, colored)
                
                # Postprocess
                self.update_status("Finalizing...", "blue")
                final = self.image_utils.postprocess(colored, metadata)
            
            # Save to output directory
            output_filename = self.input_path.stem + "_colored.png"
            self.output_path = self.output_dir / output_filename
            final.save(self.output_path, "PNG")
            
            # Update UI
            self.colored_image = final
            self.root.after(0, self._display_result)
            
            logger.info(f"Colorization complete: {self.output_path}")
            self.update_status(f"Complete! Saved to {self.output_path}", "green")
            
        except Exception as e:
            logger.error(f"Colorization failed: {e}", exc_info=True)
            self.root.after(0, lambda: messagebox.showerror("Error", f"Colorization failed: {e}"))
            self.update_status("Failed", "red")
        finally:
            self.is_processing = False
            self.root.after(0, self._enable_controls)
    
    def _display_result(self):
        """Display the colored result"""
        if self.colored_image:
            self._display_image(self.colored_image, self.colored_canvas)
            self.save_btn.config(state=tk.NORMAL)
    
    def _enable_controls(self):
        """Re-enable controls after processing"""
        self.colorize_btn.config(state=tk.NORMAL)
        self.browse_btn.config(state=tk.NORMAL)
    
    def update_progress(self, stage, current, total):
        """Update progress bar and status"""
        if total > 0:
            percent = int((current / total) * 100)
            self.root.after(0, lambda: self.progress_bar.config(value=percent))
        
        # Map stage to readable message
        stage_messages = {
            'preprocessing': 'Preprocessing image...',
            'colorizing': f'Colorizing step {current}/{total}...',
            'post_processing': 'Applying final touches...',
        }
        
        message = stage_messages.get(stage, f'{stage}...')
        self.root.after(0, lambda: self.update_status(message, "blue"))
    
    def update_status(self, message, color="black"):
        """Update status label"""
        def _update():
            self.status_label.config(text=message, foreground=color)
        self.root.after(0, _update)
    
    def save_result(self):
        """Save colored image to user-selected location"""
        if not self.colored_image:
            return
        
        filetypes = (
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg"),
            ("All files", "*.*")
        )
        
        filename = filedialog.asksaveasfilename(
            title="Save colored image",
            defaultextension=".png",
            filetypes=filetypes,
            initialfile=self.input_path.stem + "_colored.png" if self.input_path else "colored.png"
        )
        
        if filename:
            try:
                self.colored_image.save(filename)
                messagebox.showinfo("Saved", f"Image saved to {filename}")
                logger.info(f"Image saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")
                logger.error(f"Failed to save image: {e}")
    
    def run(self):
        """Start the application"""
        logger.info("Starting Manga Colorizer GUI")
        self.root.mainloop()


if __name__ == "__main__":
    app = MangaColorizerApp()
    app.run()
