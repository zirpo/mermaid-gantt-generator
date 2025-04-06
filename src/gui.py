import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
from pathlib import Path
import logging
import shutil # Import shutil for file copying
import tempfile # For temporary files
import csv # For writing temporary CSV
import pandas as pd # For creating DataFrame before saving temp CSV
from tkinter import simpledialog # For simple input dialogs
# Removed tkcalendar import
from datetime import datetime # For date handling
import calendar # For getting days in month
from PIL import Image, ImageTk # For image preview

# Adjust sys.path to import the refactored function
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import the core logic function (ensure main.py doesn't auto-run on import)
try:
    # Assuming generate_gantt_chart is defined in main.py
    from src.main import generate_gantt_chart
except ImportError as e:
    messagebox.showerror("Import Error", f"Failed to import core logic from src.main: {e}\nPlease ensure src/main.py exists and is structured correctly.")
    sys.exit(1)

# Configure basic logging for the GUI (optional, could use main's logger)
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger(__name__)

class GanttApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mermaid Gantt Generator")
        # Adjusted initial size for vertical layout
        self.geometry("650x700")

        self.input_file_path = tk.StringVar()
        self.output_folder_path = tk.StringVar(value=str(project_root / "output")) # Default to ./output
        self.output_format = tk.StringVar(value="png") # Default to png
        self.status_text = tk.StringVar(value="Ready")
        self.temp_file_path = None # To store the path of the temporary file used by editor

        # Variables/Widgets for preview
        self.preview_frame = None
        self.preview_label = None
        self.preview_image_tk = None # Keep reference to avoid garbage collection
        self.last_generated_image_path = None # Store path of the generated image for preview

        self._create_widgets()

    def _open_timeline_editor(self):
        # Placeholder for the editor window logic
        editor_window = TimelineEditorWindow(self)
        # We might need to wait for this window and get data back
        # For now, just opens it

    def _create_widgets(self):
        # --- Bottom Frame (Generate Button / Status) ---
        # Define this first and pack it at the bottom of the root window
        bottom_frame = ttk.Frame(self, padding="10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM) # Pack at bottom of root window

        # Generate button (moved to bottom right)
        ttk.Button(bottom_frame, text="Generate Chart", command=self._generate_chart).pack(side=tk.RIGHT)

        # Status bar (moved to bottom left)
        status_bar = ttk.Frame(bottom_frame, relief=tk.SUNKEN, padding="2 5")
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True) # Expand to fill space left of button
        ttk.Label(status_bar, textvariable=self.status_text).pack(side=tk.LEFT)

        # --- Main Content Frame (Above Bottom Frame) ---
        # This frame will hold the PanedWindow
        main_content_frame = ttk.Frame(self)
        main_content_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP) # Fill remaining space

        # --- Main Paned Window (Splits Controls and Preview Vertically) ---
        main_pane = tk.PanedWindow(main_content_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # --- Top Pane (Controls) ---
        controls_frame = ttk.Frame(main_pane, padding="10")
        main_pane.add(controls_frame, height=200) # Add controls frame to the top pane with initial height

        # --- Top Section (Input/Output Selection) ---
        top_section_frame = ttk.Frame(controls_frame)
        top_section_frame.pack(fill=tk.X, expand=False, pady=(0,10)) # Don't expand vertically

        # Input selection
        input_frame = ttk.Frame(top_section_frame)
        input_frame.pack(fill=tk.X, pady=(0, 5)) # Add padding below
        ttk.Label(input_frame, text="Input File:").pack(side=tk.LEFT, padx=(0, 5)) # Changed label
        ttk.Entry(input_frame, textvariable=self.input_file_path, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(input_frame, text="Browse...", command=self._select_input_file).pack(side=tk.LEFT)

        # Output folder selection
        output_frame = ttk.Frame(top_section_frame)
        output_frame.pack(fill=tk.X)
        ttk.Label(output_frame, text="Output Folder:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(output_frame, textvariable=self.output_folder_path, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(output_frame, text="Browse...", command=self._select_output_folder).pack(side=tk.LEFT)


        # --- Middle Section (Format / Templates / Editor) ---
        middle_section_frame = ttk.Frame(controls_frame)
        middle_section_frame.pack(fill=tk.X, expand=False, pady=(0,10)) # Don't expand vertically

        # Format selection (moved to left of middle frame)
        format_frame = ttk.Frame(middle_section_frame)
        format_frame.pack(side=tk.LEFT, padx=(0, 30)) # Add more padding to separate
        ttk.Label(format_frame, text="Output Format:").pack(anchor=tk.W) # Anchor West
        format_radio_frame = ttk.Frame(format_frame) # Frame for radios
        format_radio_frame.pack(anchor=tk.W)
        ttk.Radiobutton(format_radio_frame, text="PNG", variable=self.output_format, value="png").pack(side=tk.LEFT)
        ttk.Radiobutton(format_radio_frame, text="SVG", variable=self.output_format, value="svg").pack(side=tk.LEFT)

        # Editor Button (Center)
        editor_button_frame = ttk.Frame(middle_section_frame)
        editor_button_frame.pack(side=tk.LEFT, padx=(20, 20)) # Add padding
        ttk.Button(editor_button_frame, text="Create / Edit Data...", command=self._open_timeline_editor).pack()

        # Template download buttons (moved to right of middle frame)
        template_frame = ttk.Frame(middle_section_frame)
        template_frame.pack(side=tk.LEFT) # Pack left after editor button
        ttk.Label(template_frame, text="Download Templates:").pack(anchor=tk.W)
        template_button_frame = ttk.Frame(template_frame) # Frame for buttons
        template_button_frame.pack(anchor=tk.W)
        ttk.Button(template_button_frame, text="CSV", command=lambda: self._download_template('csv')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(template_button_frame, text="Excel", command=lambda: self._download_template('xlsx')).pack(side=tk.LEFT)

        # --- Bottom Pane (Preview) ---
        self.preview_frame = ttk.Frame(main_pane, padding="10", relief=tk.SUNKEN)
        main_pane.add(self.preview_frame) # Add preview frame to the bottom pane

        # Label to display the image
        self.preview_label = ttk.Label(self.preview_frame, text="Chart preview will appear here.", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)


    def _select_input_file(self):
        # Add Excel files to the selection dialog
        filetypes = (
            ("Spreadsheet files", "*.csv *.xlsx"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx"),
            ("All files", "*.*")
            )
        filepath = filedialog.askopenfilename(title="Select Input File (CSV or Excel)", filetypes=filetypes)
        if filepath:
            self.input_file_path.set(filepath)
            # Set default output folder to input file's directory
            input_dir = os.path.dirname(filepath)
            self.output_folder_path.set(input_dir) # Update the output folder variable
            self.status_text.set("Input file selected. Output folder set to input directory.")


    def _select_output_folder(self):
        """Opens a dialog to select the output directory."""
        # Use current value as initial directory if it exists and is valid
        initial_dir = self.output_folder_path.get()
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = str(project_root) # Fallback to project root

        directory = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=initial_dir
            )
        if directory:
            self.output_folder_path.set(directory)
            self.status_text.set("Output folder selected.")


    def _download_template(self, file_type: str):
        """Handles downloading the template file."""
        template_folder = project_root / "templates"
        template_filename = f"template.{file_type}"
        source_path = template_folder / template_filename

        if not source_path.exists():
            messagebox.showerror("Error", f"Template file not found:\n{source_path}")
            self.status_text.set(f"Error: {template_filename} not found in templates folder.")
            return

        # Define file types for save dialog
        if file_type == 'csv':
            filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))
        elif file_type == 'xlsx':
             filetypes = (("Excel files", "*.xlsx"), ("All files", "*.*"))
        else:
            filetypes = (("All files", "*.*"),) # Should not happen

        # Open "Save As" dialog
        save_path = filedialog.asksaveasfilename(
            title=f"Save {file_type.upper()} Template As",
            initialdir=str(Path.home() / "Downloads"), # Suggest Downloads folder
            initialfile=template_filename,
            defaultextension=f".{file_type}",
            filetypes=filetypes
        )

        if save_path:
            try:
                shutil.copy2(source_path, save_path) # copy2 preserves metadata
                self.status_text.set(f"{file_type.upper()} template saved.")
                messagebox.showinfo("Success", f"Template saved to:\n{save_path}")
            except Exception as e:
                logger.error(f"Failed to copy template {source_path} to {save_path}: {e}", exc_info=True)
                self.status_text.set(f"Error saving template: {e}")
                messagebox.showerror("Error", f"Could not save template:\n{e}")

    def _update_preview(self, image_path=None):
        """Updates the preview pane with the image or clears it."""
        try:
            # Clear previous image first
            if self.preview_image_tk:
                self.preview_label.config(image='')
                self.preview_image_tk = None

            if image_path and os.path.exists(image_path):
                # Open the image using Pillow
                img = Image.open(image_path)

                # --- Resize image to fit the preview pane (optional but recommended) ---
                # Get preview pane size (might need to update geometry first)
                self.preview_frame.update_idletasks()
                pane_width = self.preview_frame.winfo_width() - 20 # Subtract padding
                pane_height = self.preview_frame.winfo_height() - 20 # Subtract padding

                if pane_width > 1 and pane_height > 1: # Ensure valid dimensions
                    img_width, img_height = img.size
                    # Calculate aspect ratio
                    ratio = min(pane_width / img_width, pane_height / img_height)
                    if ratio < 1: # Only downscale, don't upscale
                        new_width = int(img_width * ratio)
                        new_height = int(img_height * ratio)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Convert to Tkinter PhotoImage
                self.preview_image_tk = ImageTk.PhotoImage(img)
                self.preview_label.config(image=self.preview_image_tk, text="") # Display image, clear text
                self.status_text.set("Chart generated and preview updated.")
            else:
                # Clear preview if no image path or path invalid
                self.preview_label.config(image='', text="Chart preview will appear here.")
                if image_path is None: # Only update status if clearing intentionally
                     self.status_text.set("Preview cleared.")

        except Exception as e:
            logger.error(f"Failed to update preview with image {image_path}: {e}", exc_info=True)
            self.preview_label.config(image='', text=f"Error loading preview:\n{e}")
            self.status_text.set("Error loading preview.")


    def _generate_chart(self):
        input_file = self.input_file_path.get()
        output_folder = self.output_folder_path.get()
        img_format = self.output_format.get()
        temp_preview_png = None # Path for temporary PNG if SVG is chosen

        # Clear previous preview immediately
        self._update_preview(None)
        self.last_generated_image_path = None

        if not input_file or not output_folder:
            messagebox.showerror("Error", "Please select an input file and an output folder.")
            return

        if not os.path.exists(input_file):
             messagebox.showerror("Error", f"Input file not found:\n{input_file}")
             return
        if not os.path.isdir(output_folder):
             messagebox.showerror("Error", f"Output folder not found or is not a directory:\n{output_folder}")
             return

        # Construct the target output path (without timestamp)
        input_p = Path(input_file)
        output_p = Path(output_folder)
        target_filename_base = input_p.stem # Base name without extension
        target_output_path = str(output_p / f"{target_filename_base}.{img_format}")

        self.status_text.set("Generating chart...")
        self.update_idletasks() # Update GUI to show status

        generated_image_path = None
        try:
            # Call the updated core logic function
            generated_image_path = generate_gantt_chart(input_file, target_output_path, img_format)

            if generated_image_path:
                self.last_generated_image_path = generated_image_path
                self.status_text.set(f"Chart successfully generated: {os.path.basename(generated_image_path)}")
                messagebox.showinfo("Success", f"Gantt chart saved as:\n{generated_image_path}")

                # --- Handle Preview ---
                preview_image_to_load = generated_image_path
                if img_format == 'svg':
                    # If SVG, generate a temporary PNG for preview
                    png_preview_path = str(output_p / f"{Path(generated_image_path).stem}_preview.png")
                    logger.info(f"Generating temporary PNG preview for SVG: {png_preview_path}")
                    # Need the mmd path - generate_gantt_chart doesn't return it anymore.
                    # Re-generate mmd or modify generate_gantt_chart again?
                    # Quick fix: Re-run parts of generate_gantt_chart logic here (less ideal)
                    # Let's assume for now we need to modify generate_gantt_chart to optionally keep mmd
                    # OR: Modify image_converter to accept mermaid string directly?
                    # --- Simpler approach: Call generate_gantt_chart again for PNG ---
                    temp_preview_png_path_obj = Path(tempfile.gettempdir()) / f"{target_filename_base}_preview_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    temp_preview_png = str(temp_preview_png_path_obj)
                    logger.info(f"Generating temporary PNG preview at: {temp_preview_png}")
                    # Call generate_gantt_chart again, but outputting PNG to temp location
                    preview_png_success_path = generate_gantt_chart(input_file, temp_preview_png, 'png')
                    if preview_png_success_path:
                         preview_image_to_load = preview_png_success_path
                         temp_preview_png = preview_png_success_path # Store path for cleanup
                    else:
                         logger.error("Failed to generate temporary PNG for SVG preview.")
                         preview_image_to_load = None # Cannot show preview

                # Update the preview pane
                self._update_preview(preview_image_to_load)

            else:
                # Error messages logged by generate_gantt_chart
                self.status_text.set("Generation failed. Check logs.")
                messagebox.showerror("Error", "Failed to generate Gantt chart. Please check the console/logs for details.")
                self._update_preview(None) # Clear preview on failure

        except Exception as e:
            logger.error(f"An unexpected error occurred in the GUI: {e}", exc_info=True)
            self.status_text.set(f"An unexpected error occurred: {e}")
            messagebox.showerror("Unexpected Error", f"An error occurred:\n{e}")
            self._update_preview(None) # Clear preview on error
        finally:
            # --- Cleanup Temporary Files ---
            # Editor temp file
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.remove(self.temp_file_path)
                    logger.info(f"Cleaned up editor temporary file: {self.temp_file_path}")
                    self.temp_file_path = None # Reset path
                except OSError as e:
                    logger.warning(f"Could not remove editor temporary file '{self.temp_file_path}': {e}")
            # Preview temp file (if created for SVG)
            if temp_preview_png and os.path.exists(temp_preview_png):
                 try:
                     os.remove(temp_preview_png)
                     logger.info(f"Cleaned up temporary preview PNG: {temp_preview_png}")
                 except OSError as e:
                     logger.warning(f"Could not remove temporary preview file '{temp_preview_png}': {e}")


# Placeholder for the new Editor Window Class
class TimelineEditorWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master # Reference to the main GanttApp instance
        self.title("Timeline Editor")
        self.geometry("800x600") # Adjust size as needed
        self.original_file_path = None # Store the path of the file loaded into the editor

        # Prevent interaction with main window while editor is open
        self.grab_set()
        self.focus_set()

        self._create_editor_widgets()
        # Load data if main app has a file selected
        initial_file = self.master_app.input_file_path.get()
        if initial_file and os.path.exists(initial_file):
             self._load_initial_data(initial_file)
        else:
             logger.info("No valid input file selected in main window. Editor starts empty.")

    def _create_editor_widgets(self):
        # --- Main Frame ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Treeview Frame ---
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Define columns - Added 'working_days'
        columns = ("name", "start", "end", "working_days", "complete", "is_milestone", "group")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings") # show="tree headings" to show hierarchy lines

        # Define headings - Added 'working_days'
        self.tree.heading("name", text="WorkStream / WorkPackage")
        self.tree.heading("start", text="Start Date")
        self.tree.heading("end", text="End Date")
        self.tree.heading("working_days", text="Work Days") # New heading
        self.tree.heading("complete", text="% Complete")
        self.tree.heading("is_milestone", text="Is Milestone?")
        self.tree.heading("group", text="Milestone Group")

        # Configure column widths (adjust as needed) - Added 'working_days'
        self.tree.column("name", width=250, anchor=tk.W)
        self.tree.column("start", width=90, anchor=tk.CENTER)
        self.tree.column("end", width=90, anchor=tk.CENTER)
        self.tree.column("working_days", width=70, anchor=tk.CENTER) # New column width
        self.tree.column("complete", width=70, anchor=tk.CENTER)
        self.tree.column("is_milestone", width=70, anchor=tk.CENTER)
        self.tree.column("group", width=100, anchor=tk.W)

        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # --- Button Frame ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Add WorkStream", command=self._add_workstream).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add WorkPackage", command=self._add_workpackage).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Item", command=self._edit_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Item", command=self._delete_item).pack(side=tk.LEFT, padx=5)
        # Add Load/Save buttons later if needed

        # --- Bottom Frame (OK/Cancel) ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(bottom_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="OK / Use This Data", command=self._use_data).pack(side=tk.RIGHT, padx=5)


    def _load_initial_data(self, file_path: str):
        """Loads data from the specified file path into the Treeview."""
        logger.info(f"Attempting to load data into editor from: {file_path}")
        # Import the parser function here to avoid circular dependency at module level if gui is imported elsewhere
        try:
            from src.input_parser import parse_input_file
        except ImportError:
             messagebox.showerror("Import Error", "Could not import the input parser.", parent=self)
             return

        # Parse the input file
        df = parse_input_file(file_path)

        if df is None:
            messagebox.showerror("Load Error", f"Failed to parse input file:\n{file_path}\n\nPlease check file format and logs.", parent=self)
            return
        if df.empty:
            messagebox.showinfo("Empty File", "The selected file is empty or contains no valid data.", parent=self)
            return

        # Clear existing tree data
        self.tree.delete(*self.tree.get_children())

        # Populate treeview
        try:
            # Group by WorkStream, handle potential NaN WorkStream names
            df['WorkStream'] = df['WorkStream'].fillna('Unknown WorkStream') # Replace NaN streams
            grouped = df.groupby('WorkStream', sort=False)
            stream_iids = {} # Keep track of stream item IDs

            for workstream_name, group in grouped:
                # Add WorkStream as top-level item
                stream_iid = self.tree.insert("", tk.END, text=workstream_name, values=(workstream_name, "", "", "", "", "", ""), open=True)
                stream_iids[workstream_name] = stream_iid

                # Add WorkPackages under this stream
                for index, row in group.iterrows():
                    # Format data for display
                    start_date_str = row['Start'].strftime('%Y-%m-%d') if pd.notna(row['Start']) else ""
                    end_date_str = row['End'].strftime('%Y-%m-%d') if pd.notna(row['End']) else ""
                    # Handle potential pandas NA for nullable Int64
                    working_days_str = str(row['WorkingDays']) if pd.notna(row['WorkingDays']) else ""
                    percent_str = str(int(row['PercentComplete'])) if pd.notna(row['PercentComplete']) else "0"
                    is_milestone_str = "Yes" if row['IsMilestone'] else "No"
                    group_str = str(row['MilestoneGroup']) if pd.notna(row['MilestoneGroup']) else ""
                    wp_name_str = str(row['WorkPackage']) if pd.notna(row['WorkPackage']) else "Unnamed Package"

                    # Insert package under the correct stream
                    self.tree.insert(stream_iid, tk.END, values=(
                        wp_name_str,
                        start_date_str,
                        end_date_str,
                        working_days_str,
                        percent_str,
                        is_milestone_str,
                        group_str
                    ))
            logger.info(f"Successfully loaded data from {file_path} into editor.")
        except Exception as e:
             logger.error(f"Error populating editor treeview: {e}", exc_info=True)
             messagebox.showerror("Load Error", f"An error occurred while loading data into the editor:\n{e}", parent=self)
             # Clear tree again on error to avoid partial load state
             self.tree.delete(*self.tree.get_children())
             self.original_file_path = None # Reset original path on load error
        else:
             # Successfully loaded, store the path
             self.original_file_path = file_path

    def _add_workstream(self):
        """Adds a new WorkStream (top-level item) to the Treeview."""
        stream_name = simpledialog.askstring("Add WorkStream", "Enter WorkStream Name:", parent=self)
        if stream_name:
            # Add as a top-level item. Use the 'text' attribute for the stream name itself.
            # The 'values' will be for the columns, which are mostly relevant for packages.
            # We insert with blank values for columns, but set the 'text' which isn't a column.
            # Let's adjust Treeview setup slightly to make this clearer.
            # Re-inserting with just the name in the first column for simplicity for now.
            self.tree.insert("", tk.END, iid=stream_name, values=(stream_name, "", "", "", "", ""), open=True) # Use stream_name as item ID (iid)

    def _add_workpackage(self):
        """Adds a new WorkPackage under the selected WorkStream."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a WorkStream first.", parent=self)
            return

        selected_id = selected_item[0]
        # Check if the selected item is a top-level item (WorkStream)
        # Treeview items have parents; top-level items have "" as parent.
        if self.tree.parent(selected_id) != "":
             messagebox.showwarning("Invalid Selection", "Please select a WorkStream (top-level item), not a WorkPackage.", parent=self)
             return

        # --- Use Custom Dialog with Callback ---
        def _on_add_dialog_close(result_dict):
            if result_dict: # Check if user clicked OK (result is now a dict)
                # --- Add to Treeview under the selected WorkStream ---
                # Order must match the 'columns' definition
                self.tree.insert(selected_id, tk.END, values=(
                    result_dict["WorkPackage"],
                    result_dict["Start"],
                    result_dict["End"],
                    result_dict["WorkingDays"], # Add working days value
                    result_dict["PercentComplete"],
                    "Yes" if result_dict["IsMilestone"] else "No",
                    result_dict["MilestoneGroup"]
                ))

        # Instantiate dialog, passing the callback, do not wait
        dialog = WorkPackageDialog(self, title="Add WorkPackage", on_close_callback=_on_add_dialog_close)


    def _edit_item(self):
        """Edits the selected WorkStream or WorkPackage in the Treeview."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select an item to edit.", parent=self)
            return

        selected_id = selected_item[0]
        item_values = self.tree.item(selected_id, "values")
        is_workstream = self.tree.parent(selected_id) == ""

        if is_workstream:
            # --- Edit WorkStream Name ---
            old_name = item_values[0]
            new_name = simpledialog.askstring("Edit WorkStream", "Enter new WorkStream Name:",
                                              initialvalue=old_name, parent=self)
            if new_name and new_name != old_name:
                # Update the first column's value for the selected item
                self.tree.item(selected_id, values=(new_name,) + item_values[1:])
        else:
            # --- Edit WorkPackage using Custom Dialog ---
            # Map treeview columns back to initial_data keys for the dialog
            initial_data = {
                "name": item_values[0],
                "start": item_values[1],
                "end": item_values[2],
                "working_days": item_values[3], # Add working days
                "complete": item_values[4],
                "is_milestone": item_values[5].lower() == 'yes',
                "group": item_values[6]
            }

            # --- Use Custom Dialog with Callback ---
            def _on_edit_dialog_close(result_dict):
                 if result_dict:
                    # Update the item in the Treeview using the dictionary result
                    # Order must match the 'columns' definition
                    self.tree.item(selected_id, values=(
                        result_dict["WorkPackage"],
                        result_dict["Start"],
                        result_dict["End"],
                        result_dict["WorkingDays"], # Add working days value
                        result_dict["PercentComplete"],
                        "Yes" if result_dict["IsMilestone"] else "No",
                        result_dict["MilestoneGroup"]
                    ))

            # Instantiate dialog, passing the callback, do not wait
            dialog = WorkPackageDialog(self, title="Edit WorkPackage", initial_data=initial_data, on_close_callback=_on_edit_dialog_close)


    def _delete_item(self):
        """Deletes the selected item (and children if it's a WorkStream)."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select an item to delete.", parent=self)
            return

        selected_id = selected_item[0]
        item_name = self.tree.item(selected_id, "values")[0]
        is_workstream = self.tree.parent(selected_id) == ""
        item_type = "WorkStream" if is_workstream else "WorkPackage"

        # Confirmation dialog
        confirm_msg = f"Are you sure you want to delete the {item_type} '{item_name}'?"
        if is_workstream:
            confirm_msg += "\n(This will also delete all WorkPackages within it.)"

        if messagebox.askyesno("Confirm Deletion", confirm_msg, parent=self):
            try:
                self.tree.delete(selected_id)
                logger.info(f"Deleted {item_type}: {item_name}")
            except Exception as e:
                 logger.error(f"Failed to delete item {selected_id}: {e}", exc_info=True)
                 messagebox.showerror("Error", f"Failed to delete item:\n{e}", parent=self)


    def _use_data(self):
        # Gather data from the Treeview, create DataFrame, save to temp CSV, update master_app
        try:
            data = []
            # Iterate through top-level items (WorkStreams)
            for stream_iid in self.tree.get_children(""): # Get children of root ""
                stream_values = self.tree.item(stream_iid, "values")
                stream_name = stream_values[0] # Get stream name from the first column

                # Iterate through children of this WorkStream (WorkPackages)
                for package_iid in self.tree.get_children(stream_iid):
                    pkg_values = self.tree.item(package_iid, "values")
                    # Map values to column names based on Treeview column order
                    # Convert 'Yes'/'No' back to True/False strings for CSV
                    is_milestone_str = str(str(pkg_values[5]).lower() == 'yes')
                    row_data = {
                        'WorkStream': stream_name,
                        'WorkPackage': pkg_values[0],
                        'Start': pkg_values[1],
                        'End': pkg_values[2],
                        'WorkingDays': pkg_values[3], # Add WorkingDays
                        'PercentComplete': pkg_values[4],
                        'IsMilestone': is_milestone_str,
                        'MilestoneGroup': pkg_values[6]
                    }
                    data.append(row_data)

            if not data:
                messagebox.showwarning("Empty Data", "No data entered. Cannot proceed.", parent=self)
                return

            df = pd.DataFrame(data)

            # --- Determine Default Save Location and Filename ---
            default_dir = ""
            default_filename = ""
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if self.original_file_path: # Data was loaded from a file
                original_p = Path(self.original_file_path)
                default_dir = str(original_p.parent)
                base_name = original_p.stem
                default_filename = f"{base_name}_{timestamp}.csv"
                dialog_title = "Save Edited Timeline As"
            else: # New data created in editor
                default_dir = self.master_app.output_folder_path.get() # Use main window's output folder
                # Prompt for project name
                project_name = simpledialog.askstring("Project Name", "Enter a name for this timeline project:", parent=self)
                if not project_name:
                     logger.info("User cancelled project name input.")
                     return # Abort if user cancels name input
                # Sanitize project name slightly for filename (replace spaces, etc.) - basic example
                safe_project_name = project_name.replace(" ", "_").replace("/", "-")
                default_filename = f"{safe_project_name}.csv"
                dialog_title = "Save New Timeline As"

            # --- Ask User to Confirm/Change Save Path ---
            save_path = filedialog.asksaveasfilename(
                title=dialog_title,
                initialdir=default_dir,
                initialfile=default_filename,
                defaultextension=".csv",
                filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
            )

            if not save_path:
                logger.info("User cancelled save dialog.")
                return # Abort if user cancels save dialog

            # --- Save DataFrame to the chosen path ---
            try:
                csv_columns = ['WorkStream', 'WorkPackage', 'Start', 'End', 'WorkingDays',
                               'PercentComplete', 'IsMilestone', 'MilestoneGroup']
                df.to_csv(save_path, index=False, quoting=csv.QUOTE_NONNUMERIC, columns=csv_columns)
                logger.info(f"Saved edited data to permanent file: {save_path}")

                # --- Update Main App Window ---
                self.master_app.input_file_path.set(save_path)
                # Also update the output folder to where the CSV was saved
                saved_dir = os.path.dirname(save_path)
                self.master_app.output_folder_path.set(saved_dir)
                self.master_app.status_text.set(f"Saved edited data to: {os.path.basename(save_path)}")

                # --- Cleanup Old Temp File (if any existed) ---
                if self.master_app.temp_file_path and os.path.exists(self.master_app.temp_file_path):
                    try:
                        os.remove(self.master_app.temp_file_path)
                        logger.info(f"Cleaned up old temporary file: {self.master_app.temp_file_path}")
                    except OSError as e:
                        logger.warning(f"Could not remove old temporary file '{self.master_app.temp_file_path}': {e}")
                self.master_app.temp_file_path = None # Ensure temp path is cleared

                self.destroy() # Close the editor window

            except Exception as e:
                 logger.error(f"Failed to save edited data to {save_path}: {e}", exc_info=True)
                 messagebox.showerror("Save Error", f"Could not save the timeline data:\n{e}", parent=self)

        except Exception as e:
            logger.error(f"Failed to process or save edited data: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to use edited data:\n{e}", parent=self)


# --- Custom Dialog for WorkPackage Input ---
class WorkPackageDialog(tk.Toplevel):
    def __init__(self, parent, title=None, initial_data=None, on_close_callback=None):
        super().__init__(parent)
        self.transient(parent) # Associate with parent window
        if title:
            self.title(title)

        self.parent = parent
        self.initial_data = initial_data or {}
        self.on_close_callback = on_close_callback # Store the callback
        self.result = None # Store the results here

        # --- Variables ---
        self.wp_name_var = tk.StringVar(value=self.initial_data.get("name", ""))
        # Date variables - Day, Month, Year for Start and End
        self.start_day_var = tk.StringVar()
        self.start_month_var = tk.StringVar()
        self.start_year_var = tk.StringVar()
        self.end_day_var = tk.StringVar()
        self.end_month_var = tk.StringVar()
        self.end_year_var = tk.StringVar()
        self.percent_complete_var = tk.IntVar(value=self._parse_initial_int(self.initial_data.get("complete", 0)))
        self.is_milestone_var = tk.BooleanVar(value=self.initial_data.get("is_milestone", False))
        self.milestone_group_var = tk.StringVar(value=self.initial_data.get("group", ""))
        # New variables for duration input mode and working days
        self.duration_mode_var = tk.StringVar(value="end_date") # 'end_date' or 'working_days'
        self.working_days_var = tk.StringVar(value=self._parse_initial_int(self.initial_data.get("working_days", ""))) # Store as string initially

        # Populate initial date values if provided, otherwise default Start Date to today
        start_date_provided = self._parse_initial_date("start", self.start_day_var, self.start_month_var, self.start_year_var)
        if not start_date_provided:
            # Default Start Date to today if not editing or if start date was blank
            today = datetime.now()
            self.start_day_var.set(str(today.day))
            self.start_month_var.set(str(today.month))
            self.start_year_var.set(str(today.year))

        # Parse end date if provided, otherwise leave blank
        end_date_provided = self._parse_initial_date("end", self.end_day_var, self.end_month_var, self.end_year_var)

        # Determine initial duration mode based on provided data
        if not end_date_provided and self.working_days_var.get():
             self.duration_mode_var.set("working_days")
        else:
             self.duration_mode_var.set("end_date") # Default to end_date if both or neither provided


        # --- Layout ---
        body = ttk.Frame(self, padding="10")
        self.initial_focus = self._create_body(body)
        body.pack(padx=5, pady=5)

        self._create_buttons()

        # --- Dialog Behavior ---
        self.grab_set() # Restore modality

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50)) # Position relative to parent

        self.initial_focus.focus_set()
        # Do NOT call self.wait_window(self) here - lifecycle managed by callback


    def _parse_initial_date(self, date_key, day_var, month_var, year_var) -> bool:
        """
        Parse initial date string (YYYY-MM-DD) and set combobox vars.
        Returns True if a valid date was parsed and set, False otherwise.
        """
        date_str = self.initial_data.get(date_key, "")
        if date_str and isinstance(date_str, str) and len(date_str) == 10:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                year_var.set(str(dt.year))
                month_var.set(str(dt.month))
                day_var.set(str(dt.day))
                return True # Successfully parsed and set
            except ValueError:
                # Ignore invalid initial date format
                pass
        return False # No valid date provided or parsed

    def _parse_initial_int(self, value):
        """Safely parse initial integer value which might be string from tree."""
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _create_body(self, master):
        """Create dialog body. Return widget that should have initial focus."""
        ttk.Label(master, text="WorkPackage Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        name_entry = ttk.Entry(master, textvariable=self.wp_name_var, width=40)
        name_entry.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=2) # Span 3 for date combos

        # --- Start Date ---
        ttk.Label(master, text="Start Date (Optional):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        start_date_frame = ttk.Frame(master)
        start_date_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W)

        # Day Combobox
        days = [""] + [str(d) for d in range(1, 32)]
        start_day_combo = ttk.Combobox(start_date_frame, textvariable=self.start_day_var, values=days, width=3, state="readonly")
        start_day_combo.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(start_date_frame, text="/").pack(side=tk.LEFT)

        # Month Combobox
        months = [""] + [str(m) for m in range(1, 13)]
        start_month_combo = ttk.Combobox(start_date_frame, textvariable=self.start_month_var, values=months, width=3, state="readonly")
        start_month_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(start_date_frame, text="/").pack(side=tk.LEFT)

        # Year Combobox
        current_year = datetime.now().year
        years = [""] + [str(y) for y in range(current_year - 10, current_year + 11)] # Range of years
        start_year_combo = ttk.Combobox(start_date_frame, textvariable=self.start_year_var, values=years, width=5, state="readonly")
        start_year_combo.pack(side=tk.LEFT, padx=(2, 5))

        # Clear Button for Start Date
        ttk.Button(start_date_frame, text="Clear", width=5,
                   command=lambda: (self.start_day_var.set(""), self.start_month_var.set(""), self.start_year_var.set(""))
                  ).pack(side=tk.LEFT)

        # --- End Date ---
        ttk.Label(master, text="End Date (Optional):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        end_date_frame = ttk.Frame(master)
        end_date_frame.grid(row=2, column=1, columnspan=3, sticky=tk.W)

        # Day Combobox
        end_day_combo = ttk.Combobox(end_date_frame, textvariable=self.end_day_var, values=days, width=3, state="readonly")
        end_day_combo.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(end_date_frame, text="/").pack(side=tk.LEFT)

        # Month Combobox
        end_month_combo = ttk.Combobox(end_date_frame, textvariable=self.end_month_var, values=months, width=3, state="readonly")
        end_month_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(end_date_frame, text="/").pack(side=tk.LEFT)

        # Year Combobox
        end_year_combo = ttk.Combobox(end_date_frame, textvariable=self.end_year_var, values=years, width=5, state="readonly")
        end_year_combo.pack(side=tk.LEFT, padx=(2, 5))

        self.end_date_frame = end_date_frame # Store frame reference
        self.end_day_combo = end_day_combo
        self.end_month_combo = end_month_combo
        self.end_year_combo = end_year_combo
        self.end_clear_button = ttk.Button(end_date_frame, text="Clear", width=5,
                   command=lambda: (self.end_day_var.set(""), self.end_month_var.set(""), self.end_year_var.set("")))
        self.end_clear_button.pack(side=tk.LEFT)

        # --- Duration Mode Selection ---
        duration_frame = ttk.Frame(master)
        duration_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        ttk.Label(duration_frame, text="Duration Input:").pack(side=tk.LEFT, padx=(0, 10))
        self.end_date_radio = ttk.Radiobutton(duration_frame, text="End Date", variable=self.duration_mode_var, value="end_date", command=self._toggle_duration_fields)
        self.end_date_radio.pack(side=tk.LEFT)
        self.working_days_radio = ttk.Radiobutton(duration_frame, text="Working Days", variable=self.duration_mode_var, value="working_days", command=self._toggle_duration_fields)
        self.working_days_radio.pack(side=tk.LEFT, padx=(10, 0))

        # --- Working Days Input ---
        ttk.Label(master, text="Working Days:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.working_days_entry = ttk.Entry(master, textvariable=self.working_days_var, width=5)
        self.working_days_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)


        ttk.Label(master, text="% Complete:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        # Use Spinbox or Scale for better integer input? For now, Entry + validation
        complete_entry = ttk.Entry(master, textvariable=self.percent_complete_var, width=5)
        complete_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)
        # Add validation later if needed

        ttk.Label(master, text="Is Milestone?").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        ms_check = ttk.Checkbutton(master, variable=self.is_milestone_var, onvalue=True, offvalue=False)
        ms_check.grid(row=6, column=1, columnspan=3, sticky=tk.W, padx=5, pady=2) # Span 3

        ttk.Label(master, text="Milestone Group (Optional):").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
        group_entry = ttk.Entry(master, textvariable=self.milestone_group_var, width=40)
        group_entry.grid(row=7, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=2) # Span 3

        # Initial state update for duration fields
        self._toggle_duration_fields()

        return name_entry # Initial focus

    def _create_buttons(self):
        """Create OK and Cancel buttons."""
        box = ttk.Frame(self)

        ok_button = ttk.Button(box, text="OK", width=10, command=self._ok, default=tk.ACTIVE)
        ok_button.pack(side=tk.LEFT, padx=5, pady=5)
        cancel_button = ttk.Button(box, text="Cancel", width=10, command=self._cancel)
        cancel_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self._ok)
        self.bind("<Escape>", self._cancel)

        box.pack()

    def _toggle_duration_fields(self):
        """Enable/disable End Date or Working Days fields based on radio selection."""
        mode = self.duration_mode_var.get()
        if mode == "end_date":
            # Enable End Date fields
            self.end_day_combo.config(state="readonly")
            self.end_month_combo.config(state="readonly")
            self.end_year_combo.config(state="readonly")
            self.end_clear_button.config(state="normal")
            # Disable Working Days field
            self.working_days_entry.config(state="disabled")
            # Clear working days value when switching to end date
            # self.working_days_var.set("")
        elif mode == "working_days":
            # Disable End Date fields
            self.end_day_combo.config(state="disabled")
            self.end_month_combo.config(state="disabled")
            self.end_year_combo.config(state="disabled")
            self.end_clear_button.config(state="disabled")
            # Enable Working Days field
            self.working_days_entry.config(state="normal")
            # Clear end date value when switching to working days
            # self.end_day_var.set("")
            # self.end_month_var.set("")
            # self.end_year_var.set("")
        else: # Should not happen
             self.end_day_combo.config(state="disabled")
             self.end_month_combo.config(state="disabled")
             self.end_year_combo.config(state="disabled")
             self.end_clear_button.config(state="disabled")
             self.working_days_entry.config(state="disabled")

    def _ok(self, event=None):
        """Handle OK button click."""
        if not self.wp_name_var.get():
            messagebox.showwarning("Input Error", "WorkPackage Name is required.", parent=self)
            return

        # Validate percent complete (basic)
        try:
            pc = self.percent_complete_var.get()
            if not (0 <= pc <= 100):
                raise ValueError("Percentage must be between 0 and 100.")
        except (tk.TclError, ValueError) as e:
             messagebox.showwarning("Input Error", f"Invalid % Complete: {e}", parent=self)
             return

        # --- Assemble and Validate Dates / Working Days ---
        start_date_str = self._assemble_date_string(self.start_day_var, self.start_month_var, self.start_year_var)
        if start_date_str == "INVALID":
            messagebox.showwarning("Input Error", "Invalid Start Date selected.", parent=self)
            return
        if not start_date_str: # Start date is required
             messagebox.showwarning("Input Error", "Start Date is required.", parent=self)
             return

        end_date_str = ""
        working_days_val = ""
        duration_mode = self.duration_mode_var.get()

        if duration_mode == "end_date":
            end_date_str = self._assemble_date_string(self.end_day_var, self.end_month_var, self.end_year_var)
            if end_date_str == "INVALID":
                messagebox.showwarning("Input Error", "Invalid End Date selected.", parent=self)
                return
            if not end_date_str:
                 messagebox.showwarning("Input Error", "End Date is required when 'End Date' mode is selected.", parent=self)
                 return
            # Validate start <= end
            try:
                    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
                    if start_dt > end_dt:
                        messagebox.showwarning("Input Error", "Start Date cannot be after End Date.", parent=self)
                        return
            except ValueError:
                 messagebox.showwarning("Input Error", "Internal error validating date range.", parent=self)
                 return # Should not happen if assemble worked
        elif duration_mode == "working_days":
            try:
                wd = int(self.working_days_var.get())
                if wd <= 0:
                    raise ValueError("Working days must be a positive integer.")
                working_days_val = str(wd) # Store as string for consistency if needed later
            except (ValueError, TypeError):
                 messagebox.showwarning("Input Error", "Working Days must be a positive integer.", parent=self)
                 return
            if not working_days_val: # Double check after conversion
                 messagebox.showwarning("Input Error", "Working Days is required when 'Working Days' mode is selected.", parent=self)
                 return
        else: # Should not happen
            messagebox.showerror("Internal Error", "Invalid duration mode selected.", parent=self)
            return


        # Result now includes working_days (which will be empty if end_date mode was used)
        self.result = {
            "WorkPackage": self.wp_name_var.get(),
            "Start": start_date_str,
            "End": end_date_str, # Will be "" if working_days mode
            "WorkingDays": working_days_val, # Will be "" if end_date mode
            "PercentComplete": self.percent_complete_var.get(),
            "IsMilestone": self.is_milestone_var.get(),
            "MilestoneGroup": self.milestone_group_var.get()
        }
        self.withdraw() # Hide window
        self.update_idletasks() # Process pending events
        # Call the callback before destroying
        if self.on_close_callback:
            self.on_close_callback(self.result)
        self._destroy_dialog() # Use a separate method to destroy

    def _cancel(self, event=None):
        """Handle Cancel button click or window close."""
        # Call the callback with None to indicate cancellation
        if self.on_close_callback:
            self.on_close_callback(None)
        self._destroy_dialog()

    def _destroy_dialog(self):
        """Cleanly destroy the dialog."""
        self.parent.focus_set() # Put focus back to the parent window
        self.destroy()

    def _assemble_date_string(self, day_var, month_var, year_var):
        """Assembles YYYY-MM-DD string from comboboxes, returns "" or "INVALID"."""
        day = day_var.get()
        month = month_var.get()
        year = year_var.get()

        # If all are empty, it's an intentionally blank date
        if not day and not month and not year:
            return ""

        # If any part is missing, it's incomplete (treat as blank for now, could warn)
        if not day or not month or not year:
             # Optionally show a warning here if partial date is not allowed
             # messagebox.showwarning("Input Error", "Incomplete date selected. Clearing date.", parent=self)
             return "" # Treat incomplete as blank

        try:
            day_int = int(day)
            month_int = int(month)
            year_int = int(year)
            # Basic validation: Check if day is valid for the given month/year
            max_days = calendar.monthrange(year_int, month_int)[1]
            if not (1 <= day_int <= max_days):
                return "INVALID" # Indicate invalid date combination

            # Format to YYYY-MM-DD
            return f"{year_int:04d}-{month_int:02d}-{day_int:02d}"
        except (ValueError, TypeError):
            return "INVALID" # Handle non-integer values if they somehow get in


if __name__ == "__main__":
    app = GanttApp()
    app.mainloop()
