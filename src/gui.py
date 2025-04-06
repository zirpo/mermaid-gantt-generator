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
        self.geometry("600x250") # Increased width

        self.input_file_path = tk.StringVar()
        # Change output_file_path to output_folder_path
        self.output_folder_path = tk.StringVar(value=str(project_root / "output")) # Default to ./output
        self.output_format = tk.StringVar(value="png") # Default to png
        self.status_text = tk.StringVar(value="Ready")
        self.temp_file_path = None # To store the path of the temporary file

        self._create_widgets()

    def _open_timeline_editor(self):
        # Placeholder for the editor window logic
        editor_window = TimelineEditorWindow(self)
        # We might need to wait for this window and get data back
        # For now, just opens it

    def _create_widgets(self):
        # --- Top Frame (Input/Output Selection) ---
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X, expand=True)

        # Input selection
        input_frame = ttk.Frame(top_frame)
        input_frame.pack(fill=tk.X, pady=(0, 5)) # Add padding below
        ttk.Label(input_frame, text="Input File:").pack(side=tk.LEFT, padx=(0, 5)) # Changed label
        ttk.Entry(input_frame, textvariable=self.input_file_path, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(input_frame, text="Browse...", command=self._select_input_file).pack(side=tk.LEFT)

        # Output folder selection
        output_frame = ttk.Frame(top_frame)
        output_frame.pack(fill=tk.X)
        ttk.Label(output_frame, text="Output Folder:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(output_frame, textvariable=self.output_folder_path, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(output_frame, text="Browse...", command=self._select_output_folder).pack(side=tk.LEFT)


        # --- Middle Frame (Format / Templates) ---
        middle_frame = ttk.Frame(self, padding="10")
        middle_frame.pack(fill=tk.X, expand=True)

        # Format selection (moved to left of middle frame)
        format_frame = ttk.Frame(middle_frame)
        format_frame.pack(side=tk.LEFT, padx=(0, 30)) # Add more padding to separate
        ttk.Label(format_frame, text="Output Format:").pack(anchor=tk.W) # Anchor West
        format_radio_frame = ttk.Frame(format_frame) # Frame for radios
        format_radio_frame.pack(anchor=tk.W)
        ttk.Radiobutton(format_radio_frame, text="PNG", variable=self.output_format, value="png").pack(side=tk.LEFT)
        ttk.Radiobutton(format_radio_frame, text="SVG", variable=self.output_format, value="svg").pack(side=tk.LEFT)

        # Template download buttons (moved to right of middle frame)
        template_frame = ttk.Frame(middle_frame)
        template_frame.pack(side=tk.RIGHT)
        ttk.Label(template_frame, text="Download Templates:").pack(anchor=tk.W)
        template_button_frame = ttk.Frame(template_frame) # Frame for buttons
        template_button_frame.pack(anchor=tk.W)
        ttk.Button(template_button_frame, text="CSV", command=lambda: self._download_template('csv')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(template_button_frame, text="Excel", command=lambda: self._download_template('xlsx')).pack(side=tk.LEFT)

        # --- Editor Button ---
        editor_button_frame = ttk.Frame(middle_frame)
        editor_button_frame.pack(side=tk.LEFT, padx=(20, 0)) # Add padding to separate
        ttk.Button(editor_button_frame, text="Create / Edit Data...", command=self._open_timeline_editor).pack()


        # --- Bottom Frame (Generate Button / Status) ---
        bottom_frame = ttk.Frame(self, padding="10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM) # Pack at bottom

        # Generate button (moved to bottom right)
        ttk.Button(bottom_frame, text="Generate Chart", command=self._generate_chart).pack(side=tk.RIGHT)

        # Status bar (moved to bottom left)
        status_bar = ttk.Frame(bottom_frame, relief=tk.SUNKEN, padding="2 5")
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True) # Expand to fill space left of button
        ttk.Label(status_bar, textvariable=self.status_text).pack(side=tk.LEFT)


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
            self.output_folder_path.set(input_dir)
            self.status_text.set("Input file selected. Output folder defaulted.")


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


    def _generate_chart(self):
        input_file = self.input_file_path.get()
        output_folder = self.output_folder_path.get()
        img_format = self.output_format.get()

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
        # The core function will add the timestamp internally
        input_p = Path(input_file)
        output_p = Path(output_folder)
        target_filename = f"{input_p.stem}.{img_format}"
        target_output_path = str(output_p / target_filename)

        self.status_text.set("Generating chart...")
        self.update_idletasks() # Update GUI to show status

        try:
            # Call the refactored core logic function with the target path
            success = generate_gantt_chart(input_file, target_output_path, img_format)

            if success:
                # Note: We don't know the exact final filename with timestamp here easily
                # unless generate_gantt_chart returns it. For now, just confirm success.
                self.status_text.set(f"Chart successfully generated in folder: {output_folder}")
                messagebox.showinfo("Success", f"Gantt chart saved with timestamp in:\n{output_folder}")
            else:
                # Error messages should be logged by generate_gantt_chart
                self.status_text.set("Generation failed. Check logs.")
                messagebox.showerror("Error", "Failed to generate Gantt chart. Please check the console/logs for details.")

        except Exception as e:
            logger.error(f"An unexpected error occurred in the GUI: {e}", exc_info=True)
            self.status_text.set(f"An unexpected error occurred: {e}")
            messagebox.showerror("Unexpected Error", f"An error occurred:\n{e}")
        finally:
            # --- Cleanup Temporary File ---
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.remove(self.temp_file_path)
                    logger.info(f"Cleaned up temporary file: {self.temp_file_path}")
                    self.temp_file_path = None # Reset path
                except OSError as e:
                    logger.warning(f"Could not remove temporary file '{self.temp_file_path}': {e}")


# Placeholder for the new Editor Window Class
class TimelineEditorWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master # Reference to the main GanttApp instance
        self.title("Timeline Editor")
        self.geometry("800x600") # Adjust size as needed

        # Prevent interaction with main window while editor is open
        self.grab_set()
        self.focus_set()

        self._create_editor_widgets()
        self._load_initial_data() # Load data if main app has a file selected

    def _create_editor_widgets(self):
        # --- Main Frame ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Treeview Frame ---
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Define columns
        columns = ("name", "start", "end", "complete", "is_milestone", "group")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings") # show="tree headings" to show hierarchy lines

        # Define headings
        self.tree.heading("name", text="WorkStream / WorkPackage")
        self.tree.heading("start", text="Start Date")
        self.tree.heading("end", text="End Date")
        self.tree.heading("complete", text="% Complete")
        self.tree.heading("is_milestone", text="Is Milestone?")
        self.tree.heading("group", text="Milestone Group")

        # Configure column widths (adjust as needed)
        self.tree.column("name", width=250, anchor=tk.W)
        self.tree.column("start", width=100, anchor=tk.CENTER)
        self.tree.column("end", width=100, anchor=tk.CENTER)
        self.tree.column("complete", width=80, anchor=tk.CENTER)
        self.tree.column("is_milestone", width=80, anchor=tk.CENTER)
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


    def _load_initial_data(self):
        # TODO: Optionally load data from master_app.input_file_path if it exists and is valid
        # For now, starts empty
        # TODO: Optionally load data from master_app.input_file_path if it exists and is valid
        # For now, starts empty
        # Example: If master_app.input_file_path.get() is valid, parse it and populate tree
        pass

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
        def _on_add_dialog_close(result):
            if result: # Check if user clicked OK
                wp_name, start_date, end_date, percent_complete, is_milestone, milestone_group = result
                # --- Add to Treeview under the selected WorkStream ---
                self.tree.insert(selected_id, tk.END, values=(
                    wp_name,
                    start_date, # Already formatted as string or empty
                    end_date,   # Already formatted as string or empty
                    percent_complete,
                    "Yes" if is_milestone else "No",
                    milestone_group
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
            initial_data = {
                "name": item_values[0],
                "start": item_values[1],
                "end": item_values[2],
                "complete": item_values[3],
                "is_milestone": item_values[4].lower() == 'yes',
                "group": item_values[5]
            }

            # --- Use Custom Dialog with Callback ---
            def _on_edit_dialog_close(result):
                 if result:
                    wp_name, start_date, end_date, percent_complete, is_milestone, milestone_group = result
                    # Update the item in the Treeview
                    self.tree.item(selected_id, values=(
                        wp_name,
                        start_date,
                        end_date,
                        percent_complete,
                        "Yes" if is_milestone else "No",
                        milestone_group
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
                    # Convert 'Yes'/'No' back to True/False for DataFrame/CSV
                    is_milestone_bool = str(pkg_values[4]).lower() == 'yes'
                    row_data = {
                        'WorkStream': stream_name,
                        'WorkPackage': pkg_values[0],
                        'Start': pkg_values[1],
                        'End': pkg_values[2],
                        'PercentComplete': pkg_values[3],
                        # Save as True/False strings for CSV compatibility with parser
                        'IsMilestone': str(is_milestone_bool),
                        'MilestoneGroup': pkg_values[5]
                    }
                    data.append(row_data)

            if not data:
                messagebox.showwarning("Empty Data", "No data entered. Cannot proceed.", parent=self)
                return

            df = pd.DataFrame(data)

            # --- Create and save temporary file ---
            # Ensure previous temp file is cleaned up if user edits multiple times
            if self.master_app.temp_file_path and os.path.exists(self.master_app.temp_file_path):
                try: os.remove(self.master_app.temp_file_path)
                except OSError: pass # Ignore cleanup error

            # Create a new temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=".csv", prefix="timeline_gui_")
            os.close(temp_fd) # Close the file descriptor

            # Save DataFrame to the temporary CSV
            # Use standard CSV columns expected by input_parser
            # Ensure boolean 'IsMilestone' is converted correctly if needed (already string 'True'/'False')
            df.to_csv(temp_path, index=False, quoting=csv.QUOTE_NONNUMERIC,
                      columns=['WorkStream', 'WorkPackage', 'Start', 'End',
                               'PercentComplete', 'IsMilestone', 'MilestoneGroup'])

            # Update the main app's input path and store temp path for cleanup
            self.master_app.input_file_path.set(temp_path)
            self.master_app.temp_file_path = temp_path
            self.master_app.status_text.set(f"Using data edited in GUI (temp file: {os.path.basename(temp_path)})")

            logger.info(f"Saved edited data to temporary file: {temp_path}")
            self.destroy() # Close the editor window

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

        # Populate initial date values if provided, otherwise default Start Date to today
        start_date_provided = self._parse_initial_date("start", self.start_day_var, self.start_month_var, self.start_year_var)
        if not start_date_provided:
            # Default Start Date to today if not editing or if start date was blank
            today = datetime.now()
            self.start_day_var.set(str(today.day))
            self.start_month_var.set(str(today.month))
            self.start_year_var.set(str(today.year))

        # Parse end date if provided, otherwise leave blank
        self._parse_initial_date("end", self.end_day_var, self.end_month_var, self.end_year_var)


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

        # Clear Button for End Date
        ttk.Button(end_date_frame, text="Clear", width=5,
                   command=lambda: (self.end_day_var.set(""), self.end_month_var.set(""), self.end_year_var.set(""))
                  ).pack(side=tk.LEFT)


        ttk.Label(master, text="% Complete:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        # Use Spinbox or Scale for better integer input? For now, Entry + validation
        complete_entry = ttk.Entry(master, textvariable=self.percent_complete_var, width=5)
        complete_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        # Add validation later if needed

        ttk.Label(master, text="Is Milestone?").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        ms_check = ttk.Checkbutton(master, variable=self.is_milestone_var, onvalue=True, offvalue=False)
        ms_check.grid(row=4, column=1, columnspan=3, sticky=tk.W, padx=5, pady=2) # Span 3

        ttk.Label(master, text="Milestone Group (Optional):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        group_entry = ttk.Entry(master, textvariable=self.milestone_group_var, width=40)
        group_entry.grid(row=5, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=2) # Span 3

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

        # --- Assemble and Validate Dates ---
        start_date_str = self._assemble_date_string(self.start_day_var, self.start_month_var, self.start_year_var)
        if start_date_str == "INVALID":
            messagebox.showwarning("Input Error", "Invalid Start Date selected.", parent=self)
            return

        end_date_str = self._assemble_date_string(self.end_day_var, self.end_month_var, self.end_year_var)
        if end_date_str == "INVALID":
            messagebox.showwarning("Input Error", "Invalid End Date selected.", parent=self)
            return

        # Optional: Validate start <= end if both are provided
        if start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
                if start_dt > end_dt:
                    messagebox.showwarning("Input Error", "Start Date cannot be after End Date.", parent=self)
                    return
            except ValueError:
                 messagebox.showwarning("Input Error", "Internal error validating date range.", parent=self)
                 return # Should not happen if assemble worked

        self.result = (
            self.wp_name_var.get(),
            start_date_str,
            end_date_str,
            self.percent_complete_var.get(),
            self.is_milestone_var.get(),
            self.milestone_group_var.get()
        )
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
