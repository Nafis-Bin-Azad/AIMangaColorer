"""
Manga Colorizer - Tkinter Desktop App
Simple GUI for colorizing manga pages using Stable Diffusion 1.5 + ControlNet
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
from pathlib import Path
from typing import List
import logging

from image_utils import ImageUtils
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MangaColorizerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Manga Colorizer - Single & Batch Mode")
        self.root.geometry("1200x750")
        
        # Single image state
        self.input_path = None
        self.output_path = None
        self.original_image = None
        self.colored_image = None
        self.is_processing = False
        
        # Batch processing state
        self.batch_items = []  # List of (type, path) tuples
        self.batch_processor = None
        self.batch_thread = None
        
        # Manga browser state
        self.source_manager = None
        self.manga_results = []
        self.manga_chapters = []
        self.selected_manga = None
        self.manga_downloader = None
        
        # Manga reader state
        self.manga_library = None
        self.reader_frame = None
        self.library_manga_list = []
        self.library_cover_images = []
        
        # Shared engines
        self.pipeline = None
        self.mcv2_engine = None
        self.image_utils = None
        
        # Create UI
        self._create_ui()
        
        # Output directory
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
    
    def _create_ui(self):
        """Create the UI layout with tabs"""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Single Image
        self.single_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.single_tab, text="Single Image")
        self._create_single_image_ui(self.single_tab)
        
        # Tab 2: Batch Processing
        self.batch_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_tab, text="Batch Processing")
        self._create_batch_ui(self.batch_tab)
        
        # Tab 3: Manga Browser
        self.manga_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.manga_tab, text="Manga Browser")
        self._create_manga_browser_ui(self.manga_tab)
        
        # Tab 4: Manga Reader
        self.reader_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reader_tab, text="Manga Reader")
        self._create_reader_tab_ui(self.reader_tab)
        
        # Bind tab change event for auto-refresh
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
    
    def _create_single_image_ui(self, parent):
        """Create single image mode UI"""
        # Top controls frame
        controls_frame = ttk.Frame(parent, padding="10")
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
        
        # Engine info label
        ttk.Label(controls_frame, text="Engine: Manga Colorization v2 (Fast, preserves text perfectly)", 
                 foreground="gray", font=("TkDefaultFont", 9)).grid(row=1, column=0, columnspan=3, padx=5, sticky=tk.W)
        
        # Progress frame
        progress_frame = ttk.Frame(parent, padding="10")
        progress_frame.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="green")
        self.status_label.pack()
        
        # Images frame
        images_frame = ttk.Frame(parent, padding="10")
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
    
    def _create_batch_ui(self, parent):
        """Create batch processing UI"""
        # Input controls
        input_frame = ttk.LabelFrame(parent, text="Input Sources", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(input_frame, text="Add Files", 
                   command=self.add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="Add Zip", 
                   command=self.add_zip).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="Add Folder", 
                   command=self.add_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="Clear All", 
                   command=self.clear_batch).pack(side=tk.RIGHT, padx=5)
        
        # Items list with reordering
        list_frame = ttk.LabelFrame(parent, text="Items (select and use buttons to reorder)", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollable listbox
        list_container = ttk.Frame(list_frame)
        list_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.batch_listbox = tk.Listbox(list_container, height=8)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, 
                                   command=self.batch_listbox.yview)
        self.batch_listbox.config(yscrollcommand=scrollbar.set)
        self.batch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Reorder buttons
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        ttk.Button(btn_frame, text="Move Up", width=10, 
                   command=self.move_up).pack(pady=2)
        ttk.Button(btn_frame, text="Move Down", width=10, 
                   command=self.move_down).pack(pady=2)
        ttk.Button(btn_frame, text="Remove", width=10, 
                   command=self.remove_item).pack(pady=2)
        
        # Output settings
        output_frame = ttk.LabelFrame(parent, text="Output", padding=10)
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(output_frame, text="Format:").pack(side=tk.LEFT, padx=5)
        self.output_format = tk.StringVar(value="auto")
        ttk.Radiobutton(output_frame, text="Folder", 
                        variable=self.output_format, 
                        value="folder").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(output_frame, text="Zip", 
                        variable=self.output_format, 
                        value="zip").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(output_frame, text="Auto", 
                        variable=self.output_format, 
                        value="auto").pack(side=tk.LEFT, padx=5)
        
        # Engine info label
        ttk.Label(output_frame, text="Engine: Manga Colorization v2", 
                 foreground="gray").pack(side=tk.LEFT, padx=(20, 5))
        
        # Progress section
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=10)
        progress_frame.pack(fill=tk.BOTH, padx=10, pady=5)
        
        self.batch_status = ttk.Label(progress_frame, text="Ready - Add files to begin", foreground="gray")
        self.batch_status.pack(pady=5)
        
        self.batch_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.batch_progress.pack(pady=5, fill=tk.X, padx=20)
        
        # Thumbnail + details
        preview_frame = ttk.Frame(progress_frame)
        preview_frame.pack(fill=tk.X, pady=5)
        
        self.batch_thumbnail_canvas = tk.Canvas(preview_frame, width=150, height=150, bg='gray30')
        self.batch_thumbnail_canvas.pack(side=tk.LEFT, padx=10)
        
        self.batch_details = ttk.Label(preview_frame, text="", justify=tk.LEFT)
        self.batch_details.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        
        # Control buttons
        btn_control_frame = ttk.Frame(parent, padding=10)
        btn_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.batch_start_btn = ttk.Button(btn_control_frame, text="Start Batch", 
                                           command=self.start_batch)
        self.batch_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.batch_cancel_btn = ttk.Button(btn_control_frame, text="Cancel", 
                                            command=self.cancel_batch, state=tk.DISABLED)
        self.batch_cancel_btn.pack(side=tk.LEFT, padx=5)
    
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
            # Use MCV2 engine
            if self.mcv2_engine is None:
                self.update_status("Loading Manga Colorization v2 (first time, ~600MB download)...", "blue")
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
    
    # Batch processing methods
    
    def add_files(self):
        """Add multiple image files"""
        files = filedialog.askopenfilenames(
            title="Select manga pages",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("All files", "*.*")
            ]
        )
        for file in files:
            self.batch_items.append(('file', Path(file)))
            self.batch_listbox.insert(tk.END, f"File: {Path(file).name}")
        
        if files:
            self.batch_status.config(text=f"{len(self.batch_items)} items ready", foreground="blue")
    
    def add_zip(self):
        """Add zip file(s)"""
        files = filedialog.askopenfilenames(
            title="Select zip files",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")]
        )
        for file in files:
            self.batch_items.append(('zip', Path(file)))
            self.batch_listbox.insert(tk.END, f"Zip: {Path(file).name}")
        
        if files:
            self.batch_status.config(text=f"{len(self.batch_items)} items ready", foreground="blue")
    
    def add_folder(self):
        """Add folder"""
        folder = filedialog.askdirectory(title="Select manga folder")
        if folder:
            self.batch_items.append(('folder', Path(folder)))
            self.batch_listbox.insert(tk.END, f"Folder: {Path(folder).name}")
            self.batch_status.config(text=f"{len(self.batch_items)} items ready", foreground="blue")
    
    def clear_batch(self):
        """Clear all batch items"""
        self.batch_items.clear()
        self.batch_listbox.delete(0, tk.END)
        self.batch_status.config(text="Ready - Add files to begin", foreground="gray")
        self.batch_progress['value'] = 0
        self.batch_details.config(text="")
        self.batch_thumbnail_canvas.delete("all")
    
    def move_up(self):
        """Move selected item up"""
        selection = self.batch_listbox.curselection()
        if selection and selection[0] > 0:
            idx = selection[0]
            # Swap in data list
            self.batch_items[idx], self.batch_items[idx-1] = \
                self.batch_items[idx-1], self.batch_items[idx]
            # Swap in listbox
            item = self.batch_listbox.get(idx)
            self.batch_listbox.delete(idx)
            self.batch_listbox.insert(idx-1, item)
            self.batch_listbox.selection_set(idx-1)
    
    def move_down(self):
        """Move selected item down"""
        selection = self.batch_listbox.curselection()
        if selection and selection[0] < len(self.batch_items) - 1:
            idx = selection[0]
            # Swap in data list
            self.batch_items[idx], self.batch_items[idx+1] = \
                self.batch_items[idx+1], self.batch_items[idx]
            # Swap in listbox
            item = self.batch_listbox.get(idx)
            self.batch_listbox.delete(idx)
            self.batch_listbox.insert(idx+1, item)
            self.batch_listbox.selection_set(idx+1)
    
    def remove_item(self):
        """Remove selected item"""
        selection = self.batch_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.batch_items[idx]
            self.batch_listbox.delete(idx)
            self.batch_status.config(text=f"{len(self.batch_items)} items ready", foreground="blue")
    
    def start_batch(self):
        """Start batch processing in background thread"""
        if not self.batch_items:
            messagebox.showwarning("No Items", "Please add files, zips, or folders first")
            return
        
        # Disable controls
        self.batch_start_btn.config(state=tk.DISABLED)
        self.batch_cancel_btn.config(state=tk.NORMAL)
        self.batch_status.config(text="Initializing...", foreground="blue")
        
        # Initialize image utils if needed
        if self.image_utils is None:
            self.image_utils = ImageUtils()
        
        # Initialize MCV2 engine
        if self.mcv2_engine is None:
            self.batch_status.config(text="Loading Manga Colorization v2 (first time)...", foreground="blue")
            from mcv2_engine import MangaColorizationV2Engine
            self.mcv2_engine = MangaColorizationV2Engine()
            self.mcv2_engine.ensure_weights()
            self.mcv2_engine.load_model()
        
        # Create processor
        from batch_processor import BatchProcessor
        self.batch_processor = BatchProcessor(
            engine=self.mcv2_engine,
            image_utils=self.image_utils,
            progress_callback=self.update_batch_progress
        )
        
        # Start processing thread
        self.batch_thread = threading.Thread(
            target=self._run_batch_processing,
            daemon=True
        )
        self.batch_thread.start()
    
    def _run_batch_processing(self):
        """Run batch processing (in background thread)"""
        try:
            output_path = self.output_dir / "batch_result"
            output_format = self.output_format.get()
            
            num_processed = self.batch_processor.process_batch(
                input_items=self.batch_items,
                output_path=output_path,
                output_format=output_format
            )
            
            # Determine actual output location
            if output_format == 'zip' or (output_format == 'auto' and 
                any(item_type == 'zip' for item_type, _ in self.batch_items)):
                final_path = output_path.with_suffix('.zip')
            else:
                final_path = output_path
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Complete", 
                f"Batch processing complete!\n\nProcessed {num_processed} images\nOutput: {final_path}"
            ))
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}", exc_info=True)
            self.root.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Batch processing failed: {e}"
            ))
        finally:
            self.root.after(0, self._reset_batch_controls)
    
    def update_batch_progress(self, stage, current, total, eta, thumbnail):
        """Update progress display (called from batch processor)"""
        def update():
            # Update status
            self.batch_status.config(text=f"{stage} ({current}/{total})", foreground="blue")
            
            # Update progress bar
            progress_pct = (current / total) * 100
            self.batch_progress['value'] = progress_pct
            
            # Update details
            eta_min = int(eta // 60)
            eta_sec = int(eta % 60)
            eta_str = f"{eta_min}m {eta_sec}s" if eta_min > 0 else f"{eta_sec}s"
            
            self.batch_details.config(
                text=f"Progress: {progress_pct:.1f}%\nETA: {eta_str}\nCurrent: {stage}"
            )
            
            # Update thumbnail
            if thumbnail:
                self.batch_thumbnail_canvas.delete("all")
                try:
                    photo = ImageTk.PhotoImage(thumbnail)
                    self.batch_thumbnail_canvas.create_image(
                        75, 75, image=photo, anchor=tk.CENTER
                    )
                    self.batch_thumbnail_canvas.image = photo  # Keep reference
                except Exception as e:
                    logger.error(f"Failed to update thumbnail: {e}")
        
        self.root.after(0, update)
    
    def cancel_batch(self):
        """Cancel the batch processing"""
        if self.batch_processor:
            self.batch_processor.cancel()
            self.batch_status.config(text="Cancelling...", foreground="orange")
            self.batch_cancel_btn.config(state=tk.DISABLED)
    
    def _reset_batch_controls(self):
        """Reset batch controls after completion"""
        self.batch_start_btn.config(state=tk.NORMAL)
        self.batch_cancel_btn.config(state=tk.DISABLED)
        self.batch_progress['value'] = 0
    
    def _on_tab_changed(self, event):
        """Handle tab switch events - refresh library when switching to Reader tab"""
        try:
            current_tab = self.notebook.select()
            tab_index = self.notebook.index(current_tab)
            
            # Reader tab is index 3 (0: Single, 1: Batch, 2: Browser, 3: Reader)
            if tab_index == 3:
                # Check if we're showing reader or library
                if hasattr(self, 'reader_frame') and self.reader_frame is not None:
                    # Reader is open - keep it, don't refresh library
                    try:
                        if self.reader_frame.winfo_exists():
                            return  # Reader still active, don't touch it
                    except tk.TclError:
                        pass  # Reader was destroyed, fall through to refresh
                
                # Show library view
                if hasattr(self, 'library_frame') and self.library_frame.winfo_exists():
                    self.refresh_library()
        except tk.TclError as e:
            # Widget doesn't exist - this is normal during tab initialization or destruction
            logger.debug(f"Tab change - widget not ready: {e}")
        except Exception as e:
            logger.error(f"Tab change error: {e}", exc_info=True)
    
    # Manga browser methods
    
    def _create_manga_browser_ui(self, parent):
        """Create manga browser UI"""
        # Source selection
        source_frame = ttk.LabelFrame(parent, text="Manga Source", padding=10)
        source_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(source_frame, text="Source:").pack(side=tk.LEFT, padx=5)
        self.manga_source_var = tk.StringVar(value="All Sources")
        source_dropdown = ttk.Combobox(
            source_frame,
            textvariable=self.manga_source_var,
            values=[
                "All Sources",
                "MangaDex",
                "Mangakakalot",
                "ComicK",
                "MangaFire",
                "Mangasee123",
                "AsuraScans",
                "MangaFreak",
                "MangaBuddy",
                "MangaHere",
                "TCBScans"
            ],
            state="readonly",
            width=20
        )
        source_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(source_frame, text="Free API, huge library", foreground="gray", font=("TkDefaultFont", 9)).pack(side=tk.LEFT, padx=10)
        
        # Search bar
        search_frame = ttk.Frame(parent, padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.manga_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.manga_search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind('<Return>', lambda e: self.search_manga())
        
        ttk.Button(search_frame, text="Search", command=self.search_manga).pack(side=tk.LEFT, padx=5)
        
        # Results list
        results_frame = ttk.LabelFrame(parent, text="Search Results (double-click to view chapters)", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollable listbox for manga results
        self.manga_results_listbox = tk.Listbox(results_frame, height=8)
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, 
                                   command=self.manga_results_listbox.yview)
        self.manga_results_listbox.config(yscrollcommand=scrollbar.set)
        self.manga_results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.manga_results_listbox.bind('<Double-Button-1>', self.on_manga_selected)
        
        # Chapter list (appears after selecting manga)
        chapter_frame = ttk.LabelFrame(parent, text="Chapters (select multiple with Cmd/Ctrl+Click)", padding=10)
        chapter_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chapter_listbox = tk.Listbox(chapter_frame, height=8, selectmode=tk.EXTENDED)
        ch_scrollbar = ttk.Scrollbar(chapter_frame, orient=tk.VERTICAL,
                                      command=self.chapter_listbox.yview)
        self.chapter_listbox.config(yscrollcommand=ch_scrollbar.set)
        self.chapter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ch_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Download options
        download_frame = ttk.Frame(parent, padding=10)
        download_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.auto_colorize_manga_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            download_frame,
            text="Auto-colorize after download (uses Fast engine)",
            variable=self.auto_colorize_manga_var
        ).pack(side=tk.LEFT, padx=5)
        
        self.download_manga_btn = ttk.Button(download_frame, text="Download Selected", 
                                              command=self.download_manga)
        self.download_manga_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_download_btn = ttk.Button(download_frame, text="Cancel", 
                                               command=self.cancel_manga_download, state=tk.DISABLED)
        self.cancel_download_btn.pack(side=tk.LEFT, padx=5)
        
        # Status and progress
        status_frame = ttk.Frame(parent, padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.manga_status = ttk.Label(status_frame, text="Select a source and search for manga", foreground="gray")
        self.manga_status.pack()
        
        self.manga_download_progress = ttk.Progressbar(status_frame, length=400, mode='determinate')
        self.manga_download_progress.pack(pady=5, fill=tk.X)
    
    def search_manga(self):
        """Search for manga from selected source(s)"""
        query = self.manga_search_var.get().strip()
        if not query:
            messagebox.showwarning("Empty Search", "Please enter a search term")
            return
        
        # Initialize source manager if needed
        if self.source_manager is None:
            from manga_source_manager import SourceManager
            self.source_manager = SourceManager()
        
        source_name = self.manga_source_var.get()
        
        self.manga_status.config(text=f"Searching {source_name}...", foreground="blue")
        
        # Search in thread
        def search_thread():
            try:
                if source_name == "All Sources":
                    # Universal search across all sources
                    results = self._search_all_sources(query)
                else:
                    # Single source search
                    scraper = self.source_manager.get_scraper(source_name)
                    if not scraper:
                        self.root.after(0, lambda: messagebox.showerror(
                            "Error", f"Source {source_name} not available"
                        ))
                        return
                    results = scraper.search(query)
                
                self.manga_results = results
                self.root.after(0, lambda: self._display_manga_results(results, source_name))
                
            except Exception as e:
                logger.error(f"Search failed: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror(
                    "Search Failed", f"Error: {e}"
                ))
                self.root.after(0, lambda: self.manga_status.config(text="Search failed", foreground="red"))
        
        threading.Thread(target=search_thread, daemon=True).start()
    
    def _search_all_sources(self, query: str) -> List:
        """Search all sources in parallel"""
        import concurrent.futures
        
        sources = self.source_manager.get_available_sources()
        all_results = []
        
        def search_single_source(source_name):
            """Search a single source with error handling"""
            try:
                scraper = self.source_manager.get_scraper(source_name)
                if scraper:
                    results = scraper.search(query)
                    return (source_name, results, None)
            except Exception as e:
                logger.warning(f"Search failed for {source_name}: {e}")
                return (source_name, [], str(e))
            return (source_name, [], None)
        
        # Search all sources in parallel with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_source = {executor.submit(search_single_source, src): src 
                               for src in sources}
            
            for future in concurrent.futures.as_completed(future_to_source):
                source_name, results, error = future.result()
                if results:
                    all_results.append({
                        'source': source_name,
                        'results': results,
                        'count': len(results),
                        'error': error
                    })
        
        return all_results
    
    def _display_manga_results(self, results, source_name="single"):
        """Display search results (single source or grouped)"""
        self.manga_results_listbox.delete(0, tk.END)
        
        if source_name == "All Sources":
            # Display grouped results by source
            total_count = 0
            
            for group in results:
                if group['results']:
                    # Add source header
                    header = f"━━━ {group['source']} ({group['count']} results) ━━━"
                    self.manga_results_listbox.insert(tk.END, header)
                    try:
                        self.manga_results_listbox.itemconfig(tk.END, {'bg': '#e0e0e0', 'fg': '#333'})
                    except:
                        pass
                    
                    # Add manga from this source (limit to 5 per source)
                    for manga in group['results'][:5]:
                        display_text = f"  {manga.title}"
                        if manga.status:
                            display_text += f" [{manga.status}]"
                        self.manga_results_listbox.insert(tk.END, display_text)
                    
                    total_count += group['count']
            
            self.manga_status.config(
                text=f"Found {total_count} results across {len(results)} sources. Double-click to view chapters.",
                foreground="green"
            )
        else:
            # Single source display
            for manga in results:
                display_text = f"{manga.title}"
                if manga.status:
                    display_text += f" [{manga.status}]"
                if manga.authors:
                    display_text += f" - {', '.join(manga.authors[:2])}"
                
                self.manga_results_listbox.insert(tk.END, display_text)
            
            self.manga_status.config(
                text=f"Found {len(results)} results. Double-click to view chapters.",
                foreground="green"
            )
        
        # Clear chapter list
        self.chapter_listbox.delete(0, tk.END)
    
    def on_manga_selected(self, event):
        """Load chapters when manga is double-clicked"""
        selection = self.manga_results_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        
        # Handle grouped results (All Sources search)
        if isinstance(self.manga_results, list) and self.manga_results and isinstance(self.manga_results[0], dict) and 'source' in self.manga_results[0]:
            # This is a grouped result from universal search
            # Need to find which manga was clicked
            listbox_text = self.manga_results_listbox.get(idx)
            
            # Skip if it's a header line
            if listbox_text.startswith("━━━"):
                return
            
            # Find the manga in the grouped results
            for group in self.manga_results:
                for manga in group['results']:
                    if manga.title in listbox_text:
                        self.selected_manga = manga
                        break
                if self.selected_manga:
                    break
        else:
            # Single source search result
            manga = self.manga_results[idx]
            self.selected_manga = manga
        
        self.manga_status.config(text=f"Loading chapters for {manga.title}...", foreground="blue")
        
        # Load chapters in thread
        def load_chapters():
            try:
                scraper = self.source_manager.get_scraper(manga.source)
                chapters = scraper.get_chapters(manga.id)
                self.manga_chapters = chapters
                
                self.root.after(0, lambda: self._display_chapters(chapters))
            except Exception as e:
                logger.error(f"Failed to load chapters: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", f"Failed to load chapters: {e}"
                ))
                self.root.after(0, lambda: self.manga_status.config(text="Failed to load chapters", foreground="red"))
        
        threading.Thread(target=load_chapters, daemon=True).start()
    
    def _display_chapters(self, chapters):
        """Display chapter list"""
        self.chapter_listbox.delete(0, tk.END)
        
        for ch in chapters:
            chapter_text = f"Ch {ch.chapter_number}"
            if ch.title:
                chapter_text += f": {ch.title}"
            if ch.pages > 0:
                chapter_text += f" ({ch.pages} pages)"
            
            self.chapter_listbox.insert(tk.END, chapter_text)
        
        self.manga_status.config(text=f"Loaded {len(chapters)} chapters. Select and click Download.", foreground="green")
    
    def download_manga(self):
        """Download selected chapters"""
        selection = self.chapter_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Select chapters to download (use Cmd/Ctrl+Click for multiple)")
            return
        
        if not self.selected_manga:
            messagebox.showerror("Error", "No manga selected")
            return
        
        selected_chapters = [self.manga_chapters[i] for i in selection]
        
        self.download_manga_btn.config(state=tk.DISABLED)
        self.cancel_download_btn.config(state=tk.NORMAL)
        
        # Download in thread
        def download_thread():
            from manga_downloader import MangaDownloader
            
            try:
                scraper = self.source_manager.get_scraper(self.selected_manga.source)
                downloader = MangaDownloader(scraper, Path("downloads"))
                self.manga_downloader = downloader
                
                self.root.after(0, lambda: self.manga_status.config(
                    text=f"Downloading {len(selected_chapters)} chapters...",
                    foreground="orange"
                ))
                
                # Download chapters
                chapter_dirs = downloader.download_multiple_chapters(
                    selected_chapters,
                    self.selected_manga.title,
                    progress_callback=self.update_manga_download_progress
                )
                
                # Auto-colorize if enabled
                if self.auto_colorize_manga_var.get() and chapter_dirs:
                    self.root.after(0, lambda: self.manga_status.config(
                        text="Auto-colorizing downloaded chapters...",
                        foreground="blue"
                    ))
                    self._colorize_downloaded_chapters(chapter_dirs)
                
                self.root.after(0, lambda: messagebox.showinfo(
                    "Complete",
                    f"Downloaded {len(chapter_dirs)} chapters!\n\nLocation: downloads/{self.selected_manga.title}/"
                ))
                
                self.root.after(0, lambda: self.manga_status.config(
                    text=f"Download complete! Saved to downloads/",
                    foreground="green"
                ))
                
            except Exception as e:
                logger.error(f"Download failed: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror(
                    "Download Failed", f"Error: {e}"
                ))
                self.root.after(0, lambda: self.manga_status.config(
                    text="Download failed",
                    foreground="red"
                ))
            finally:
                self.root.after(0, self._reset_manga_download_controls)
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def update_manga_download_progress(self, current, total, info):
        """Update manga download progress"""
        def update():
            progress = (current / total) * 100
            self.manga_download_progress['value'] = progress
            self.manga_status.config(
                text=f"Downloading: {info} ({current}/{total})",
                foreground="orange"
            )
        
        self.root.after(0, update)
    
    def cancel_manga_download(self):
        """Cancel manga download"""
        if self.manga_downloader:
            self.manga_downloader.cancel()
            self.manga_status.config(text="Cancelling download...", foreground="orange")
            self.cancel_download_btn.config(state=tk.DISABLED)
    
    def _reset_manga_download_controls(self):
        """Reset manga download controls"""
        self.download_manga_btn.config(state=tk.NORMAL)
        self.cancel_download_btn.config(state=tk.DISABLED)
        self.manga_download_progress['value'] = 0
    
    def _colorize_downloaded_chapters(self, chapter_dirs: List[Path]):
        """Colorize downloaded manga chapters using batch processor"""
        try:
            # Initialize engine if needed
            if self.mcv2_engine is None:
                from mcv2_engine import MangaColorizationV2Engine
                self.mcv2_engine = MangaColorizationV2Engine()
                self.mcv2_engine.ensure_weights()
                self.mcv2_engine.load_model()
            
            if self.image_utils is None:
                self.image_utils = ImageUtils()
            
            # Create batch processor with progress callback
            from batch_processor import BatchProcessor
            processor = BatchProcessor(
                engine=self.mcv2_engine,
                image_utils=self.image_utils,
                engine_type='mcv2',
                progress_callback=self.update_colorization_progress
            )
            
            # Process each chapter separately to preserve chapter structure
            base_output_path = self.output_dir / f"{self.selected_manga.title}_colored"
            
            for chapter_dir in chapter_dirs:
                chapter_name = chapter_dir.name  # e.g., "Ch_30.0"
                output_chapter_path = base_output_path / chapter_name
                
                logger.info(f"Colorizing {chapter_name} to {output_chapter_path}")
                
                processor.process_batch(
                    input_items=[('folder', chapter_dir)],
                    output_path=output_chapter_path,
                    output_format='folder'
                )
            
            logger.info(f"Auto-colorization complete: {base_output_path}")
            
        except Exception as e:
            logger.error(f"Auto-colorization failed: {e}", exc_info=True)
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: messagebox.showwarning(
                "Colorization Failed",
                f"Chapters downloaded but colorization failed: {msg}"
            ))
    
    def update_colorization_progress(self, current=None, total=None, status=None, stage=None, **kwargs):
        """Update colorization progress - accepts various parameter formats"""
        def update():
            # Handle different callback signatures
            if current is not None and total is not None and total > 0:
                progress = (current / total) * 100
                self.manga_download_progress['value'] = progress
                display_status = stage or status or f"Image {current}/{total}"
                self.manga_status.config(
                    text=f"Colorizing: {display_status} ({current}/{total})",
                    foreground="blue"
                )
        
        self.root.after(0, update)
    
    # Manga reader/library methods
    
    def _create_reader_tab_ui(self, parent):
        """Create manga reader/library tab"""
        # Container for library or reader
        self.reader_container = ttk.Frame(parent)
        self.reader_container.pack(fill=tk.BOTH, expand=True)
        
        # Top controls
        controls_frame = ttk.Frame(self.reader_container, padding=10)
        controls_frame.pack(fill=tk.X)
        
        ttk.Button(controls_frame, text="⟳ Refresh Library", 
                   command=self.refresh_library).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls_frame, text="Sort by:").pack(side=tk.LEFT, padx=5)
        self.library_sort_var = tk.StringVar(value="recent")
        sort_dropdown = ttk.Combobox(controls_frame, textvariable=self.library_sort_var,
                                     values=["recent", "title", "chapters"],
                                     state="readonly", width=15)
        sort_dropdown.pack(side=tk.LEFT, padx=5)
        sort_dropdown.bind('<<ComboboxSelected>>', lambda e: self.refresh_library())
        
        self.library_search_var = tk.StringVar()
        self.library_search_var.trace('w', lambda *args: self.refresh_library())
        search_entry = ttk.Entry(controls_frame, textvariable=self.library_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(controls_frame, text="🔍 Search", foreground="gray").pack(side=tk.LEFT)
        
        # Library view (scrollable grid of manga covers)
        library_canvas_frame = ttk.Frame(self.reader_container)
        library_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.library_canvas = tk.Canvas(library_canvas_frame, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(library_canvas_frame, orient=tk.VERTICAL, 
                                   command=self.library_canvas.yview)
        self.library_canvas.config(yscrollcommand=scrollbar.set)
        self.library_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Library will display manga as grid of thumbnails with titles
        self.library_frame = ttk.Frame(self.library_canvas)
        self.library_canvas_window = self.library_canvas.create_window((0, 0), window=self.library_frame, anchor='nw')
        
        # Update scroll region when library frame size changes
        self.library_frame.bind('<Configure>', lambda e: self.library_canvas.configure(
            scrollregion=self.library_canvas.bbox('all')
        ))
        
        # Status bar
        self.library_status = ttk.Label(self.reader_container, 
                                       text="Library empty. Download manga from Browser tab.",
                                       foreground="gray")
        self.library_status.pack(pady=5)
        
        # Load library on startup (delayed)
        self.root.after(500, self.refresh_library)
    
    def refresh_library(self):
        """Refresh manga library display"""
        try:
            # Check if library frame exists and is valid
            if not hasattr(self, 'library_frame') or not self.library_frame.winfo_exists():
                return
            
            # Initialize library manager if needed
            if self.manga_library is None:
                from manga_library import MangaLibrary
                self.manga_library = MangaLibrary(
                    downloads_dir=Path("downloads"),
                    data_file=Path("manga_data.json")
                )
            
            # Scan for manga
            manga_list = self.manga_library.scan_library()
            
            # Apply sorting
            sort_by = self.library_sort_var.get()
            if sort_by == "recent":
                manga_list.sort(key=lambda m: m.last_read or "", reverse=True)
            elif sort_by == "title":
                manga_list.sort(key=lambda m: m.title.lower())
            elif sort_by == "chapters":
                manga_list.sort(key=lambda m: m.total_chapters, reverse=True)
            
            # Apply search filter
            search_term = self.library_search_var.get().lower()
            if search_term:
                manga_list = [m for m in manga_list if search_term in m.title.lower()]
            
            self.library_manga_list = manga_list
            
            # Clear current display
            for widget in self.library_frame.winfo_children():
                widget.destroy()
            
            self.library_cover_images = []  # Keep references to prevent garbage collection
            
            # Display as grid (3 columns)
            if not manga_list:
                ttk.Label(self.library_frame, text="No manga in library.\n\nDownload manga from the Browser tab.",
                         font=('TkDefaultFont', 12), foreground='gray').grid(row=0, column=0, padx=50, pady=50)
                if hasattr(self, 'library_status') and self.library_status.winfo_exists():
                    self.library_status.config(text="Library empty")
                return
        except Exception as e:
            logger.error(f"Error refreshing library: {e}", exc_info=True)
            return
        
        columns = 3
        for idx, manga in enumerate(manga_list):
            row = idx // columns
            col = idx % columns
            
            # Create manga card
            card = ttk.Frame(self.library_frame, relief=tk.RAISED, borderwidth=1)
            card.grid(row=row, column=col, padx=10, pady=10, sticky='n')
            
            # Cover image
            if manga.cover_path and manga.cover_path.exists():
                try:
                    cover_img = Image.open(manga.cover_path)
                    cover_photo = ImageTk.PhotoImage(cover_img)
                    self.library_cover_images.append(cover_photo)  # Keep reference
                    
                    cover_label = ttk.Label(card, image=cover_photo)
                    cover_label.pack(pady=5)
                except Exception as e:
                    logger.error(f"Failed to load cover for {manga.title}: {e}")
                    # Create placeholder frame for no cover
                    placeholder = tk.Frame(card, width=150, height=200, bg='lightgray', relief=tk.SUNKEN, bd=2)
                    placeholder.pack(pady=5)
                    placeholder.pack_propagate(False)
                    ttk.Label(placeholder, text="[No Cover]").place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            else:
                # Create placeholder frame for no cover
                placeholder = tk.Frame(card, width=150, height=200, bg='lightgray', relief=tk.SUNKEN, bd=2)
                placeholder.pack(pady=5)
                placeholder.pack_propagate(False)
                ttk.Label(placeholder, text="[No Cover]").place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # Title (truncated if too long)
            title_text = manga.title if len(manga.title) <= 30 else manga.title[:27] + "..."
            ttk.Label(card, text=title_text, font=('TkDefaultFont', 10, 'bold'),
                     wraplength=200).pack(pady=5)
            
            # Chapter count
            ttk.Label(card, text=f"{manga.total_chapters} chapters",
                     foreground="gray").pack()
            
            # Progress bar (if any progress exists)
            if manga.title in self.manga_library.progress:
                chapters_read = len(self.manga_library.progress[manga.title])
                progress_pct = (chapters_read / manga.total_chapters) * 100
                
                progress_bar = ttk.Progressbar(card, length=180, mode='determinate', 
                                               value=progress_pct)
                progress_bar.pack(pady=5)
                ttk.Label(card, text=f"{int(progress_pct)}% read",
                         font=('TkDefaultFont', 8), foreground="blue").pack()
            
            # Buttons
            btn_frame = ttk.Frame(card)
            btn_frame.pack(pady=5)
            
            ttk.Button(btn_frame, text="📖 Read", 
                      command=lambda m=manga: self.open_manga_reader(m.title)).pack(side=tk.LEFT, padx=2)
            
            ttk.Button(btn_frame, text="🎨 Colorize", 
                      command=lambda m=manga: self.colorize_manga(m.title)).pack(side=tk.LEFT, padx=2)
        
        # Update status if it exists
        if hasattr(self, 'library_status') and self.library_status.winfo_exists():
            self.library_status.config(text=f"Library: {len(manga_list)} manga")
        
        # Update canvas scroll region
        self.library_frame.update_idletasks()
        if hasattr(self, 'library_canvas') and self.library_canvas.winfo_exists():
            self.library_canvas.configure(scrollregion=self.library_canvas.bbox('all'))
    
    def open_manga_reader(self, manga_title: str, chapter: str = None):
        """Open manga in reader"""
        try:
            # Clear reader container
            for widget in self.reader_container.winfo_children():
                widget.destroy()
            
            # Create reader frame and track it
            from manga_reader import MangaReaderFrame
            self.reader_frame = MangaReaderFrame(
                self.reader_container,
                self.manga_library,
                manga_title,
                chapter
            )
            
            logger.info(f"Opened reader for {manga_title}")
            
        except Exception as e:
            logger.error(f"Failed to open reader: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to open reader: {e}")
            # Reset state
            self.reader_frame = None
            # Restore library view
            self._recreate_library_ui()
    
    def _recreate_library_ui(self):
        """Recreate library UI after reader closes"""
        try:
            # Clear container
            for widget in self.reader_container.winfo_children():
                widget.destroy()
            
            # Recreate library UI structure
            self._create_reader_tab_ui(self.reader_tab)
        except Exception as e:
            logger.error(f"Failed to recreate library UI: {e}", exc_info=True)
    
    def _show_chapter_selection_dialog(self, manga_title: str, chapter_dirs: List[Path]) -> List[Path]:
        """
        Show dialog to select chapters for colorization.
        
        Args:
            manga_title: Title of manga
            chapter_dirs: List of available chapter directories
            
        Returns:
            List of selected chapter directories
        """
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Select Chapters to Colorize - {manga_title}")
        dialog.geometry("600x650")
        dialog.transient(self.root)
        dialog.grab_set()
        
        selected_chapters = []
        
        # Instructions
        ttk.Label(dialog, text="Select chapters to colorize:", 
                 font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
        
        # Frame for chapter list
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollable listbox with checkboxes
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create checkbox for each chapter
        check_vars = []
        for chapter_dir in chapter_dirs:
            var = tk.BooleanVar(value=False)
            check_vars.append((var, chapter_dir))
            
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Check if colored version exists
            has_colored = self.manga_library.has_colored_version(manga_title, chapter_dir.name)
            status = " ✓ (colored)" if has_colored else ""
            
            cb = ttk.Checkbutton(
                frame,
                text=f"{chapter_dir.name}{status}",
                variable=var
            )
            cb.pack(side=tk.LEFT)
            
            # Show page count
            pages = self.manga_library.get_chapter_pages(manga_title, chapter_dir.name)
            ttk.Label(frame, text=f"({len(pages)} pages)", 
                     foreground="gray").pack(side=tk.RIGHT)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Selection buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def select_all():
            for var, _ in check_vars:
                var.set(True)
        
        def select_none():
            for var, _ in check_vars:
                var.set(False)
        
        def select_uncolored():
            for var, chapter_dir in check_vars:
                has_colored = self.manga_library.has_colored_version(manga_title, chapter_dir.name)
                var.set(not has_colored)
        
        ttk.Button(btn_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Select None", command=select_none).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Select Uncolored", command=select_uncolored).pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        action_frame = ttk.Frame(dialog)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def on_confirm():
            nonlocal selected_chapters
            selected_chapters = [chapter_dir for var, chapter_dir in check_vars if var.get()]
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(action_frame, text="Colorize Selected", 
                  command=on_confirm).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Cancel", 
                  command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        # Show selection count
        count_label = ttk.Label(action_frame, text="0 chapters selected")
        count_label.pack(side=tk.LEFT, padx=5)
        
        def update_count(*args):
            count = sum(1 for var, _ in check_vars if var.get())
            count_label.config(text=f"{count} chapter{'s' if count != 1 else ''} selected")
        
        # Bind count update to all checkboxes
        for var, _ in check_vars:
            var.trace('w', update_count)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return selected_chapters
    
    def colorize_manga(self, manga_title: str):
        """Colorize selected chapters of a manga"""
        # Get all chapter directories
        manga_path = Path("downloads") / manga_title
        chapter_dirs = sorted([
            d for d in manga_path.iterdir()
            if d.is_dir() and d.name.startswith('Ch_')
        ])
        
        if not chapter_dirs:
            messagebox.showwarning("No Chapters", f"No chapters found for {manga_title}")
            return
        
        # Show chapter selection dialog
        selected_chapters = self._show_chapter_selection_dialog(manga_title, chapter_dirs)
        
        if not selected_chapters:
            # User cancelled or selected nothing
            return
        
        # Switch to batch tab and add selected folders
        self.notebook.select(self.batch_tab)
        
        # Add to batch
        for chapter_dir in selected_chapters:
            self.batch_items.append(('folder', chapter_dir))
            display_text = f"📁 {manga_title} / {chapter_dir.name}"
            self.batch_listbox.insert(tk.END, display_text)
        
        messagebox.showinfo("Added to Batch", 
                          f"Added {len(selected_chapters)} chapter{'s' if len(selected_chapters) != 1 else ''} to batch processing.\n\nGo to Batch tab to start colorization.")
    
    def run(self):
        """Start the application"""
        logger.info("Starting Manga Colorizer GUI")
        self.root.mainloop()


if __name__ == "__main__":
    app = MangaColorizerApp()
    app.run()
