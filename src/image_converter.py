import subprocess
import logging
import os
import tempfile

def save_mermaid_file(mermaid_string: str, output_dir: str, base_filename: str) -> str | None:
    """
    Saves the Mermaid syntax string to a .mmd file in the specified directory.

    Args:
        mermaid_string: The string containing the Mermaid syntax.
        output_dir: The directory where the .mmd file should be saved.
        base_filename: The base name for the file (without extension).

    Returns:
        The full path to the saved .mmd file, or None if an error occurs.
    """
    if not mermaid_string:
        logging.error("Mermaid string is empty. Cannot save file.")
        return None

    mmd_filename = f"{base_filename}.mmd"
    mmd_filepath = os.path.join(output_dir, mmd_filename)

    try:
        os.makedirs(output_dir, exist_ok=True) # Ensure output directory exists
        with open(mmd_filepath, 'w', encoding='utf-8') as f:
            f.write(mermaid_string)
        logging.info(f"Mermaid syntax saved to: {mmd_filepath}")
        return mmd_filepath
    except IOError as e:
        logging.error(f"Failed to write Mermaid file '{mmd_filepath}': {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving Mermaid file: {e}")
        return None


def convert_mermaid_to_image(mmd_filepath: str, output_image_path: str, image_format: str = 'png') -> bool:
    """
    Converts a .mmd file to an image (PNG or SVG) using the Mermaid CLI (mmdc).

    Args:
        mmd_filepath: Path to the input .mmd file.
        output_image_path: Desired path for the output image file (including extension).
        image_format: The desired output format ('png' or 'svg'). Defaults to 'png'.

    Returns:
        True if conversion was successful, False otherwise.
    """
    if not os.path.exists(mmd_filepath):
        logging.error(f"Input Mermaid file not found: {mmd_filepath}")
        return False

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_image_path)
    if output_dir: # Handle cases where output path is just a filename in the CWD
        os.makedirs(output_dir, exist_ok=True)

    command = [
        'mmdc',
        '-i', mmd_filepath,
        '-o', output_image_path,
        # Optional: Add background color if needed, e.g., for transparency in PNG
        # '-b', 'white'
    ]

    # Add format specific flags if necessary (mmdc usually infers from -o extension)
    # if image_format.lower() == 'svg':
    #     command.extend(['--outputFormat', 'svg']) # Usually not needed

    logging.info(f"Executing Mermaid CLI command: {' '.join(command)}")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False) # check=False to handle errors manually

        if result.returncode != 0:
            logging.error(f"Mermaid CLI failed with exit code {result.returncode}.")
            logging.error(f"Stderr:\n{result.stderr}")
            logging.error(f"Stdout:\n{result.stdout}")
            # Attempt to delete potentially incomplete output file
            if os.path.exists(output_image_path):
                 try:
                     os.remove(output_image_path)
                 except OSError:
                     logging.warning(f"Could not delete potentially incomplete output file: {output_image_path}")
            return False
        else:
            logging.info(f"Mermaid diagram successfully converted to: {output_image_path}")
            if result.stderr: # Log stderr even on success, might contain warnings
                 logging.warning(f"Mermaid CLI stderr (might contain warnings):\n{result.stderr}")
            return True

    except FileNotFoundError:
        logging.error("Mermaid CLI command 'mmdc' not found. Please ensure it is installed and in your system's PATH.")
        logging.error("Installation instructions: npm install -g @mermaid-js/mermaid-cli")
        return False
    except subprocess.TimeoutExpired:
        logging.error("Mermaid CLI command timed out.")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during Mermaid CLI execution: {e}")
        return False

if __name__ == '__main__':
    # Example Usage (requires mmdc to be installed)
    print("--- Testing Image Converter ---")

    # Create a dummy mermaid string and save it
    dummy_mermaid = """
gantt
    title Test Chart
    dateFormat  YYYY-MM-DD
    section Test Section
    Task 1 :done, 2024-01-01, 5d
    Task 2 :active, 2024-01-03, 7d
    Milestone A :milestone, 2024-01-10, 0d
    """
    temp_dir = tempfile.gettempdir()
    base_name = "test_mermaid_chart"
    mmd_file = save_mermaid_file(dummy_mermaid, temp_dir, base_name)

    if mmd_file:
        print(f"Dummy Mermaid file saved to: {mmd_file}")

        # Test PNG conversion
        png_output = os.path.join(temp_dir, f"{base_name}.png")
        print(f"\nAttempting PNG conversion to: {png_output}")
        success_png = convert_mermaid_to_image(mmd_file, png_output, 'png')
        if success_png:
            print(f"PNG conversion successful: {os.path.exists(png_output)}")
            # Clean up PNG
            # os.remove(png_output)
        else:
            print("PNG conversion failed.")

        # Test SVG conversion
        svg_output = os.path.join(temp_dir, f"{base_name}.svg")
        print(f"\nAttempting SVG conversion to: {svg_output}")
        success_svg = convert_mermaid_to_image(mmd_file, svg_output, 'svg')
        if success_svg:
            print(f"SVG conversion successful: {os.path.exists(svg_output)}")
            # Clean up SVG
            # os.remove(svg_output)
        else:
            print("SVG conversion failed.")

        # Clean up MMD file
        # os.remove(mmd_file)
        print(f"\nTest files (if created) are in: {temp_dir}")
        print("Manual cleanup may be required if tests failed to delete files.")

    else:
        print("Failed to save dummy Mermaid file. Cannot test conversion.")

    print("\n--- Testing with non-existent input file ---")
    convert_mermaid_to_image("non_existent.mmd", "output.png")
