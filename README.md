# Mermaid Timeline Generator

A Python tool to generate Mermaid Gantt chart images (PNG/SVG) from project timeline data in CSV format.

## Features

*   Parses CSV files containing project tasks with start/end dates, completion status, and work streams.
*   Calculates task durations and determines status (`done`, `active`).
*   Supports explicit milestones defined in the CSV.
*   Supports grouped milestones triggered when all constituent tasks (sharing the same `MilestoneGroup` identifier) are 100% complete.
*   Generates Mermaid Gantt chart syntax, organizing work packages into sections based on `WorkStream`.
*   Uses Mermaid's default status colors (active, done, default) for WorkPackage bars.
*   Uses the Mermaid CLI (`mmdc`) to convert the generated syntax into PNG or SVG images.
*   Derives the chart title from the input CSV filename.

## Prerequisites

*   **Python 3.8+**
*   **Node.js and npm:** Required to install and run the Mermaid CLI. You can download them from [https://nodejs.org/](https://nodejs.org/).
*   **Mermaid CLI (`mmdc`):** Install globally using npm:
    ```bash
    npm install -g @mermaid-js/mermaid-cli
    ```

## Setup

1.  **Clone the repository (or ensure you are in the project directory):**
    ```bash
    # git clone <repository_url> # If applicable
    cd mermaid_timeline_generator
    ```

2.  **Create and activate a Python virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script from the command line, providing the input CSV file path and the desired output image file path.

```bash
python src/main.py <path_to_input.csv> <path_to_output_image.[png|svg]> [--format <png|svg>]
```

**Arguments:**

*   `input_file`: Path to the input CSV file containing timeline data. (See `data/sample_timeline.csv` for format).
*   `output_file`: Path where the generated image should be saved. The file extension (`.png` or `.svg`) determines the output format if `--format` is not specified, and must match the `--format` argument if it is provided.
*   `--format` (optional): Specify the output image format (`png` or `svg`). Defaults to `png`.

**Example:**

```bash
# Generate a PNG image from the sample data
python src/main.py data/sample_timeline.csv output/my_project_timeline.png

# Generate an SVG image
python src/main.py data/sample_timeline.csv output/my_project_timeline.svg --format svg
```

The script will:
1.  Read and process `data/sample_timeline.csv`.
2.  Generate Mermaid syntax.
3.  Save the syntax to `output/my_project_timeline.mmd`.
4.  Use `mmdc` to convert the `.mmd` file into `output/my_project_timeline.png` (or `.svg`).
5.  Log progress and any errors to the console.

## Input CSV Format

The input CSV file must contain the following columns:

*   `WorkStream`: Category/group for items (used for sections).
*   `WorkPackage`: The name of the work package or milestone to be displayed on the Gantt chart.
*   `Start`: Item start date (Format: `YYYY-MM-DD`).
*   `End`: Item end date (Format: `YYYY-MM-DD`).

Optional columns:

*   `PercentComplete`: Work package completion percentage (0-100). Defaults to 0 if missing or invalid. Used to determine `active` or `done` status.
*   `IsMilestone`: Flag (`True`, `False`, `yes`, `no`, `1`, `0`). If `True`, the row (identified by `WorkPackage`) is treated as an explicit milestone using its `End` date (or `Start` date if `End` is missing).
*   `MilestoneGroup`: Identifier string. Work packages sharing the same identifier belong to a group. If all work packages in a group reach 100% completion, a milestone is automatically generated using this identifier as its name, placed at the latest `End` date of the constituent work packages.

See `data/sample_timeline.csv` and `data/detailed_sample_wp_level.csv` for concrete examples.

## Testing

(Test suite implementation using `pytest` is planned but not yet included in this initial version).

To run tests (once implemented):
```bash
pytest tests/
