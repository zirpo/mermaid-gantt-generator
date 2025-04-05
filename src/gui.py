import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
from pathlib import Path
import logging

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

        self._create_widgets()

    def _create_widgets(self):
        # Frame for input selection
        input_frame = ttk.Frame(self, padding="10")
        input_frame.pack(fill=tk.X)
        ttk.Label(input_frame, text="Input CSV:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(input_frame, textvariable=self.input_file_path, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(input_frame, text="Browse...", command=self._select_input_file).pack(side=tk.LEFT)

        # Frame for output folder selection
        output_frame = ttk.Frame(self, padding="10")
        output_frame.pack(fill=tk.X)
        ttk.Label(output_frame, text="Output Folder:").pack(side=tk.LEFT, padx=(0, 5))
        # Make entry read-only? Or allow typing? For now, allow typing but browse is primary.
        ttk.Entry(output_frame, textvariable=self.output_folder_path, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        # Ensure the button is created and packed correctly
        ttk.Button(output_frame, text="Browse...", command=self._select_output_folder).pack(side=tk.LEFT)

        # Frame for format and generation
        action_frame = ttk.Frame(self, padding="10")
        action_frame.pack(fill=tk.X)

        # Format selection
        format_frame = ttk.Frame(action_frame)
        format_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(format_frame, text="Format:").pack(side=tk.LEFT, padx=(0, 5))
        # Remove command linking to _update_output_extension
        ttk.Radiobutton(format_frame, text="PNG", variable=self.output_format, value="png").pack(side=tk.LEFT)
        ttk.Radiobutton(format_frame, text="SVG", variable=self.output_format, value="svg").pack(side=tk.LEFT)

        # Generate button
        ttk.Button(action_frame, text="Generate Chart", command=self._generate_chart).pack(side=tk.RIGHT)

        # Status bar
        status_bar = ttk.Frame(self, relief=tk.SUNKEN, padding="2 5")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status_bar, textvariable=self.status_text).pack(side=tk.LEFT)

    def _select_input_file(self):
        filetypes = (("CSV files", "*.csv"), ("All files", "*.*"))
        filepath = filedialog.askopenfilename(title="Select Input CSV", filetypes=filetypes)
        if filepath:
            self.input_file_path.set(filepath)
            # Set default output folder to input file's directory
            input_dir = os.path.dirname(filepath)
            self.output_folder_path.set(input_dir)
            self.status_text.set("Input file selected. Output folder defaulted.")

    # Remove _suggest_output_path and _update_output_extension methods

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


if __name__ == "__main__":
    app = GanttApp()
    app.mainloop()
