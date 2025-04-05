import argparse
import os
import logging
import sys
from pathlib import Path
from datetime import datetime # Add datetime import

# Adjust sys.path to import sibling modules
project_root = Path(__file__).resolve().parent.parent # Go up two levels from src/main.py to mermaid_timeline_generator/
sys.path.insert(0, str(project_root))

from src.input_parser import parse_csv
from src.timeline_logic import process_timeline_data
from src.mermaid_generator import generate_mermaid_gantt
from src.image_converter import save_mermaid_file, convert_mermaid_to_image

# Configure logging
# Use a more specific logger name if desired
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger(__name__)


def get_project_title_from_filename(filepath: str) -> str:
    """Extracts a project title from the input filename."""
    try:
        base_name = os.path.basename(filepath)
        title, _ = os.path.splitext(base_name)
        # Replace underscores/hyphens with spaces and capitalize
        title = title.replace('_', ' ').replace('-', ' ').title()
        return title
    except Exception:
        logger.warning("Could not derive project title from filename. Using default.")
        return "Project Timeline"

def generate_gantt_chart(input_path_str: str, output_path_str: str, image_format: str) -> bool:
    """
    Core logic to generate a Gantt chart image from a CSV file.

    Args:
        input_path_str: Path to the input CSV file.
        output_path_str: Path for the output image file.
        image_format: Output image format ('png' or 'svg').

    Returns:
        True if successful, False otherwise.
    """
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)
    image_format = image_format.lower()

    # Validate output file extension matches format
    expected_extension = f".{image_format}"
    if output_path.suffix.lower() != expected_extension:
        logger.error(f"Output file extension '{output_path.suffix}' does not match the specified format '{image_format}'. Please ensure the output filename ends with '{expected_extension}'.")
        return False

    # Ensure output directory exists
    output_dir = output_path.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory '{output_dir}': {e}")
        return False

    # --- 1. Parse CSV ---
    logger.info(f"Parsing input file: {input_path}")
    df = parse_csv(str(input_path))
    if df is None:
        logger.error("Failed to parse CSV file.")
        return False
    if df.empty:
        logger.warning("Parsed CSV is empty. No chart will be generated.")
        return True # Considered success as there's no error, just nothing to do

    # --- 2. Process Data ---
    logger.info("Processing timeline data...")
    processed_df = process_timeline_data(df)
    if processed_df.empty:
        logger.error("Failed to process timeline data or data resulted in empty set.")
        return False

    # --- 3. Generate Mermaid Syntax ---
    project_title = get_project_title_from_filename(str(input_path))
    logger.info(f"Generating Mermaid syntax with title: '{project_title}'")
    mermaid_string = generate_mermaid_gantt(processed_df, project_title)
    if not mermaid_string:
        logger.error("Failed to generate Mermaid syntax.")
        return False

    # --- Generate Timestamped Filename ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = output_path.stem
    extension = output_path.suffix # Includes the dot, e.g., '.png'
    timestamped_base_filename = f"{base_name}_{timestamp}"
    timestamped_output_path = output_dir / f"{timestamped_base_filename}{extension}"

    # --- 4. Save Mermaid File (with timestamped name) ---
    mmd_output_dir = str(output_dir)
    # Use the timestamped base name for the .mmd file as well
    logger.info(f"Saving Mermaid syntax to .mmd file in: {mmd_output_dir} with base name {timestamped_base_filename}")
    mmd_filepath = save_mermaid_file(mermaid_string, mmd_output_dir, timestamped_base_filename)
    if not mmd_filepath:
        logger.error("Failed to save .mmd file.")
        return False

    # --- 5. Convert to Image (using timestamped output path) ---
    logger.info(f"Converting '{mmd_filepath}' to '{timestamped_output_path}' (Format: {image_format})...")
    success = convert_mermaid_to_image(mmd_filepath, str(timestamped_output_path), image_format)

    if success:
        logger.info(f"Successfully generated timeline image: {timestamped_output_path}")
        # Optional: Clean up the intermediate .mmd file
        # try:
        #     os.remove(mmd_filepath)
        #     logger.info(f"Cleaned up intermediate file: {mmd_filepath}")
        # except OSError as e:
        #     logger.warning(f"Could not remove intermediate file '{mmd_filepath}': {e}")
        return True
    else:
        logger.error("Failed to convert Mermaid file to image. Please check Mermaid CLI installation and logs.")
        return False

def main_cli():
    """Handles Command Line Interface execution."""
    parser = argparse.ArgumentParser(description="Generate a Mermaid Gantt chart image from a project timeline CSV.")
    parser.add_argument("input_file", help="Path to the input CSV file.")
    parser.add_argument("output_file", help="Path for the output image file (e.g., output/timeline.png or output/timeline.svg).")
    parser.add_argument("--format", choices=['png', 'svg'], default='png', help="Output image format (default: png).")
    # parser.add_argument("--title", help="Optional title for the Gantt chart (overrides filename derivation).") # Add later if needed

    args = parser.parse_args()

    success = generate_gantt_chart(args.input_file, args.output_file, args.format)

    if success:
        sys.exit(0) # Success
    else:
        sys.exit(1) # Failure


if __name__ == "__main__":
    main_cli()
