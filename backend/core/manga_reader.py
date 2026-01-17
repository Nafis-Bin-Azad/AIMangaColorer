"""
Manga Reader UI Component
Advanced manga reader with zoom, bookmarks, thumbnails, and keyboard shortcuts
"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from pathlib import Path
from typing import List, Optional
import logging
from manga_library import MangaLibrary

logger = logging.getLogger(__name__)


class MangaReaderFrame(ttk.Frame):
    """Advanced manga reader with zoom, bookmarks, thumbnails"""
    
    def __init__(self, parent, library: MangaLibrary, manga_title: str, chapter: str = None):
        """
        Initialize manga reader.
        
        Args:
            parent: Parent widget
            library: MangaLibrary instance
            manga_title: Title of manga to read
            chapter: Initial chapter (None = auto-detect)
        """
        super().__init__(parent)
        
        self.library = library
        self.manga_title = manga_title
        self.current_page = 0
        self.pages: List[Path] = []
        self.zoom_level = 1.0
        self.fit_mode = "width"  # width, height, actual
        self.current_image = None
        self.photo_image = None
        self.show_thumbnails = False
        
        # Get available chapters
        manga_path = library.downloads_dir / manga_title
        self.chapters = sorted([
            d.name for d in manga_path.iterdir()
            if d.is_dir() and d.name.startswith('Ch_')
        ])
        
        if not self.chapters:
            messagebox.showerror("Error", f"No chapters found for {manga_title}")
            return
        
        # Determine starting chapter
        if chapter and chapter in self.chapters:
            self.current_chapter = chapter
        else:
            # Try to get last read chapter
            progress = None
            if manga_title in library.progress:
                latest = max(
                    library.progress[manga_title].items(),
                    key=lambda item: item[1].last_read
                )
                self.current_chapter = latest[0]
                progress = latest[1]
            else:
                self.current_chapter = self.chapters[0]
            
            # Restore page if progress exists
            if progress:
                self.current_page = progress.page
        
        self._create_ui()
        self._load_chapter()
        self._setup_keyboard_shortcuts()
        self._display_page()
        
        # Add to history
        self.library.add_to_history(self.manga_title, self.current_chapter)
    
    def _create_ui(self):
        """Create reader interface"""
        self.pack(fill=tk.BOTH, expand=True)
        
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        
        # Back button (first element)
        ttk.Button(toolbar, text="← Back to Library", 
                  command=self.close_reader).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        # Chapter selector
        ttk.Label(toolbar, text="Chapter:").pack(side=tk.LEFT, padx=5)
        self.chapter_var = tk.StringVar(value=self.current_chapter)
        chapter_dropdown = ttk.Combobox(
            toolbar,
            textvariable=self.chapter_var,
            values=self.chapters,
            state="readonly",
            width=15
        )
        chapter_dropdown.pack(side=tk.LEFT, padx=5)
        chapter_dropdown.bind('<<ComboboxSelected>>', lambda e: self.change_chapter(self.chapter_var.get()))
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Version selector (Original/Colored)
        ttk.Label(toolbar, text="Version:").pack(side=tk.LEFT, padx=5)
        self.version_var = tk.StringVar(value="Original")
        
        # Check if colored version exists
        has_colored = self.library.has_colored_version(self.manga_title, self.current_chapter)
        version_options = ["Original", "Colored"] if has_colored else ["Original"]
        
        self.version_dropdown = ttk.Combobox(
            toolbar,
            textvariable=self.version_var,
            values=version_options,
            state="readonly" if has_colored else "disabled",
            width=10
        )
        self.version_dropdown.pack(side=tk.LEFT, padx=5)
        self.version_dropdown.bind('<<ComboboxSelected>>', lambda e: self._reload_with_version())
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Zoom controls
        ttk.Label(toolbar, text="Zoom:").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="−", command=lambda: self.set_zoom(self.zoom_level - 0.1), width=3).pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = ttk.Label(toolbar, text="100%", width=6)
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(toolbar, text="+", command=lambda: self.set_zoom(self.zoom_level + 0.1), width=3).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Fit mode buttons
        ttk.Button(toolbar, text="Fit Width", command=lambda: self.set_fit_mode("width")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Fit Height", command=lambda: self.set_fit_mode("height")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Actual Size", command=lambda: self.set_fit_mode("actual")).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Bookmark button
        self.bookmark_btn = ttk.Button(toolbar, text="★ Bookmark", command=self.toggle_bookmark)
        self.bookmark_btn.pack(side=tk.LEFT, padx=5)
        
        # Thumbnails toggle
        ttk.Button(toolbar, text="Thumbnails", command=self.toggle_thumbnails).pack(side=tk.LEFT, padx=5)
        
        # Colorize button for current chapter
        ttk.Button(toolbar, text="🎨 Colorize Chapter", 
                  command=self._colorize_current_chapter).pack(side=tk.RIGHT, padx=5)
        
        # Close button
        ttk.Button(toolbar, text="✕ Close", command=self.close_reader).pack(side=tk.RIGHT, padx=5)
        
        # Main content area
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for page display
        canvas_frame = ttk.Frame(content_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#2b2b2b', highlightthickness=0)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Click zones for navigation
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        
        # Mousewheel scrolling
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)  # Windows/Mac
        self.canvas.bind('<Button-4>', self._on_mousewheel)    # Linux scroll up
        self.canvas.bind('<Button-5>', self._on_mousewheel)    # Linux scroll down
        
        # Thumbnail panel (initially hidden)
        self.thumbnail_frame = ttk.Frame(content_frame, width=150)
        self.thumbnail_canvas = tk.Canvas(self.thumbnail_frame, width=150, bg='#1e1e1e')
        thumb_scrollbar = ttk.Scrollbar(self.thumbnail_frame, orient=tk.VERTICAL,
                                        command=self.thumbnail_canvas.yview)
        self.thumbnail_canvas.config(yscrollcommand=thumb_scrollbar.set)
        
        self.thumbnail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        thumb_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottom toolbar
        bottom_toolbar = ttk.Frame(self)
        bottom_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation buttons
        ttk.Button(bottom_toolbar, text="◄◄ Prev", command=self.prev_page).pack(side=tk.LEFT, padx=5)
        
        # Page indicator
        self.page_label = ttk.Label(bottom_toolbar, text="Page 1 / 1")
        self.page_label.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(bottom_toolbar, text="Next ►►", command=self.next_page).pack(side=tk.LEFT, padx=5)
        
        # Jump to page
        ttk.Label(bottom_toolbar, text="Go to:").pack(side=tk.LEFT, padx=(20, 5))
        self.page_entry = ttk.Entry(bottom_toolbar, width=5)
        self.page_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom_toolbar, text="Go", command=self.jump_to_page).pack(side=tk.LEFT, padx=2)
        
        # Keyboard shortcuts hint
        ttk.Label(bottom_toolbar, text="[←/→: Navigate  +/-: Zoom  F/H/0: Fit  B: Bookmark  T: Thumbnails  Esc: Close]",
                 foreground="gray").pack(side=tk.RIGHT, padx=5)
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard navigation"""
        # Bind to both the frame and canvas for better reliability
        for widget in [self, self.canvas]:
            widget.bind('<Left>', lambda e: self.prev_page())
            widget.bind('<Right>', lambda e: self.next_page())
            widget.bind('<space>', lambda e: self.next_page())
            widget.bind('<Prior>', lambda e: self.prev_page())  # Page Up
            widget.bind('<Next>', lambda e: self.next_page())  # Page Down
            
            widget.bind('<plus>', lambda e: self.set_zoom(self.zoom_level + 0.1))
            widget.bind('<equal>', lambda e: self.set_zoom(self.zoom_level + 0.1))  # + without shift
            widget.bind('<minus>', lambda e: self.set_zoom(self.zoom_level - 0.1))
            
            widget.bind('f', lambda e: self.set_fit_mode("width"))
            widget.bind('h', lambda e: self.set_fit_mode("height"))
            widget.bind('0', lambda e: self.set_fit_mode("actual"))
            
            widget.bind('b', lambda e: self.toggle_bookmark())
            widget.bind('t', lambda e: self.toggle_thumbnails())
            
            widget.bind('<Escape>', lambda e: self.close_reader())
        
        # Set focus to canvas for immediate keyboard control
        self.canvas.focus_set()
        
        # Ensure focus returns to canvas after interactions
        self.bind('<FocusIn>', lambda e: self.after(100, lambda: self.canvas.focus_set() if self.canvas.winfo_exists() else None))
    
    def _load_chapter(self):
        """Load chapter pages"""
        use_colored = (self.version_var.get() == "Colored")
        self.pages = self.library.get_chapter_pages(self.manga_title, self.current_chapter, use_colored=use_colored)
        
        if not self.pages:
            messagebox.showerror("Error", f"No pages found in {self.current_chapter}")
            return
        
        logger.info(f"Loaded {len(self.pages)} pages from {self.current_chapter} ({'colored' if use_colored else 'original'})")
        
        # Ensure current page is valid
        if self.current_page >= len(self.pages):
            self.current_page = 0
        
        # Update thumbnails if visible
        if self.show_thumbnails:
            self._update_thumbnails()
    
    def _reload_with_version(self):
        """Reload chapter with selected version"""
        use_colored = (self.version_var.get() == "Colored")
        self.pages = self.library.get_chapter_pages(
            self.manga_title, 
            self.current_chapter,
            use_colored=use_colored
        )
        
        if not self.pages:
            messagebox.showwarning("Version Not Available", 
                                  f"{'Colored' if use_colored else 'Original'} version not available for this chapter")
            # Revert to previous version
            self.version_var.set("Original" if use_colored else "Colored")
            return
        
        logger.info(f"Switched to {'colored' if use_colored else 'original'} version")
        
        # Keep current page if valid, otherwise reset to 0
        if self.current_page >= len(self.pages):
            self.current_page = 0
        
        self._display_page()
        
        # Update thumbnails if visible
        if self.show_thumbnails:
            self._update_thumbnails()
    
    def _display_page(self):
        """Display current page with zoom/fit applied"""
        if not self.pages or self.current_page >= len(self.pages):
            return
        
        try:
            # Load image
            page_path = self.pages[self.current_page]
            self.current_image = Image.open(page_path)
            
            # Apply fit mode
            if self.fit_mode == "width":
                # Fit to canvas width
                canvas_width = self.canvas.winfo_width()
                if canvas_width > 1:  # Canvas initialized
                    scale = canvas_width / self.current_image.width
                    new_width = canvas_width
                    new_height = int(self.current_image.height * scale)
                    display_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    display_image = self.current_image
            
            elif self.fit_mode == "height":
                # Fit to canvas height
                canvas_height = self.canvas.winfo_height()
                if canvas_height > 1:
                    scale = canvas_height / self.current_image.height
                    new_height = canvas_height
                    new_width = int(self.current_image.width * scale)
                    display_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    display_image = self.current_image
            
            else:  # actual
                # Use zoom level
                if self.zoom_level != 1.0:
                    new_width = int(self.current_image.width * self.zoom_level)
                    new_height = int(self.current_image.height * self.zoom_level)
                    display_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    display_image = self.current_image
            
            # Convert to PhotoImage
            self.photo_image = ImageTk.PhotoImage(display_image)
            
            # Display on canvas
            self.canvas.delete('all')
            self.canvas.create_image(
                display_image.width // 2,
                display_image.height // 2,
                image=self.photo_image,
                anchor=tk.CENTER
            )
            
            # Update scroll region
            self.canvas.config(scrollregion=(0, 0, display_image.width, display_image.height))
            
            # Update page label
            self.page_label.config(text=f"Page {self.current_page + 1} / {len(self.pages)}")
            
            # Update bookmark button
            bookmarks = self.library.get_bookmarks(self.manga_title, self.current_chapter)
            if self.current_page in bookmarks:
                self.bookmark_btn.config(text="★ Bookmarked")
            else:
                self.bookmark_btn.config(text="☆ Bookmark")
            
            # Save progress
            self._save_progress()
            
        except Exception as e:
            logger.error(f"Failed to display page: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to display page: {e}")
    
    def _on_canvas_click(self, event):
        """Handle canvas click for navigation"""
        canvas_width = self.canvas.winfo_width()
        
        # Click left 1/3 = previous, right 1/3 = next
        if event.x < canvas_width / 3:
            self.prev_page()
        elif event.x > 2 * canvas_width / 3:
            self.next_page()
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        if event.num == 5 or event.delta < 0:
            # Scroll down
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            # Scroll up
            self.canvas.yview_scroll(-1, "units")
    
    def next_page(self):
        """Next page"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self._display_page()
        else:
            # Try next chapter
            current_idx = self.chapters.index(self.current_chapter)
            if current_idx < len(self.chapters) - 1:
                if messagebox.askyesno("Next Chapter", "End of chapter. Go to next chapter?"):
                    self.change_chapter(self.chapters[current_idx + 1])
    
    def prev_page(self):
        """Previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self._display_page()
        else:
            # Try previous chapter
            current_idx = self.chapters.index(self.current_chapter)
            if current_idx > 0:
                if messagebox.askyesno("Previous Chapter", "Start of chapter. Go to previous chapter?"):
                    prev_chapter = self.chapters[current_idx - 1]
                    self.change_chapter(prev_chapter, start_at_end=True)
    
    def change_chapter(self, chapter: str, start_at_end: bool = False):
        """Switch to different chapter"""
        if chapter not in self.chapters:
            return
        
        self.current_chapter = chapter
        self.current_page = 0
        
        # Update version dropdown based on colored availability for this chapter
        has_colored = self.library.has_colored_version(self.manga_title, chapter)
        version_options = ["Original", "Colored"] if has_colored else ["Original"]
        self.version_dropdown['values'] = version_options
        self.version_dropdown['state'] = "readonly" if has_colored else "disabled"
        
        # If colored not available but was selected, switch to original
        if not has_colored and self.version_var.get() == "Colored":
            self.version_var.set("Original")
        
        self._load_chapter()
        
        if start_at_end:
            self.current_page = len(self.pages) - 1
        
        self._display_page()
        self.library.add_to_history(self.manga_title, self.current_chapter)
    
    def set_zoom(self, level: float):
        """Set zoom level"""
        self.zoom_level = max(0.1, min(3.0, level))
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        
        if self.fit_mode == "actual":
            self._display_page()
    
    def set_fit_mode(self, mode: str):
        """Set fit mode"""
        self.fit_mode = mode
        if mode != "actual":
            self.zoom_level = 1.0
            self.zoom_label.config(text="100%")
        self._display_page()
    
    def toggle_bookmark(self):
        """Toggle bookmark for current page"""
        bookmarks = self.library.get_bookmarks(self.manga_title, self.current_chapter)
        
        if self.current_page in bookmarks:
            self.library.remove_bookmark(self.manga_title, self.current_chapter, self.current_page)
            self.bookmark_btn.config(text="☆ Bookmark")
        else:
            self.library.add_bookmark(self.manga_title, self.current_chapter, self.current_page)
            self.bookmark_btn.config(text="★ Bookmarked")
    
    def toggle_thumbnails(self):
        """Toggle thumbnail panel"""
        self.show_thumbnails = not self.show_thumbnails
        
        if self.show_thumbnails:
            self.thumbnail_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5))
            self._update_thumbnails()
        else:
            self.thumbnail_frame.pack_forget()
    
    def _update_thumbnails(self):
        """Update thumbnail panel"""
        # Clear existing thumbnails
        self.thumbnail_canvas.delete('all')
        
        # Create thumbnail grid
        y_offset = 5
        for idx, page_path in enumerate(self.pages):
            try:
                img = Image.open(page_path)
                img.thumbnail((120, 180), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                
                # Store reference to prevent garbage collection
                if not hasattr(self, 'thumbnail_images'):
                    self.thumbnail_images = []
                self.thumbnail_images.append(photo)
                
                # Create clickable thumbnail
                self.thumbnail_canvas.create_image(75, y_offset + 90, image=photo, anchor=tk.CENTER)
                self.thumbnail_canvas.create_text(75, y_offset + 185, text=f"Page {idx + 1}",
                                                 fill='white', font=('TkDefaultFont', 8))
                
                # Add click handler
                self.thumbnail_canvas.tag_bind(f'thumb_{idx}', '<Button-1>',
                                              lambda e, p=idx: self.jump_to_page_direct(p))
                
                y_offset += 200
                
            except Exception as e:
                logger.error(f"Failed to create thumbnail for page {idx}: {e}")
        
        self.thumbnail_canvas.config(scrollregion=(0, 0, 150, y_offset))
    
    def jump_to_page(self):
        """Jump to page from entry"""
        try:
            page_num = int(self.page_entry.get())
            self.jump_to_page_direct(page_num - 1)  # Convert to 0-based index
        except ValueError:
            messagebox.showwarning("Invalid Page", "Please enter a valid page number")
    
    def jump_to_page_direct(self, page_idx: int):
        """Jump to specific page index"""
        if 0 <= page_idx < len(self.pages):
            self.current_page = page_idx
            self._display_page()
        else:
            messagebox.showwarning("Invalid Page", f"Page must be between 1 and {len(self.pages)}")
    
    def _save_progress(self):
        """Auto-save reading progress"""
        self.library.save_progress(
            self.manga_title,
            self.current_chapter,
            self.current_page,
            len(self.pages)
        )
    
    def close_reader(self):
        """Close reader and return to library"""
        try:
            self._save_progress()
            
            # Clear reader reference in GUI
            if hasattr(self.master, 'reader_frame'):
                self.master.reader_frame = None
            
            # Unbind all events to prevent errors
            self.unbind_all('<Escape>')
            
            # Destroy this widget
            self.destroy()
            
            # Recreate library UI
            if hasattr(self.master, '_recreate_library_ui'):
                self.after(10, self.master._recreate_library_ui)
            elif hasattr(self.master, 'refresh_library'):
                # Fallback for old code
                self.after(10, self.master.refresh_library)
                
        except Exception as e:
            logger.error(f"Error closing reader: {e}", exc_info=True)
            # Force cleanup even if there's an error
            try:
                self.destroy()
            except:
                pass
    
    def _colorize_current_chapter(self):
        """Colorize the current chapter"""
        from pathlib import Path
        
        chapter_path = self.library.downloads_dir / self.manga_title / self.current_chapter
        
        if not chapter_path.exists():
            messagebox.showerror("Error", "Chapter path not found")
            return
        
        # Check if already colored
        has_colored = self.library.has_colored_version(self.manga_title, self.current_chapter)
        
        if has_colored:
            result = messagebox.askyesno(
                "Already Colorized",
                f"{self.current_chapter} is already colorized.\n\nColorize again (will overwrite existing)?",
                icon='question'
            )
            if not result:
                return
        
        # Add to batch processing in main GUI
        if hasattr(self.master, 'batch_items') and hasattr(self.master, 'batch_listbox'):
            # Add to batch
            self.master.batch_items.append(('folder', chapter_path))
            display_text = f"📁 {self.manga_title} / {self.current_chapter}"
            self.master.batch_listbox.insert(tk.END, display_text)
            
            # Switch to batch tab
            if hasattr(self.master, 'notebook') and hasattr(self.master, 'batch_tab'):
                self.master.notebook.select(self.master.batch_tab)
            
            messagebox.showinfo(
                "Added to Batch",
                f"Chapter {self.current_chapter} added to batch processing.\n\nSwitch to Batch tab to start colorization."
            )
        else:
            messagebox.showwarning(
                "Not Available",
                "Batch colorization not available from reader.\n\nPlease use the Library tab instead."
            )