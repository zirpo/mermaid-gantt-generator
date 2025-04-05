import pandas as pd
import logging
# Removed itertools as it's no longer needed for color cycling

# Removed COLOR_PALETTE definition

def generate_mermaid_gantt(df: pd.DataFrame, project_title: str) -> str:
    """
    Generates the Mermaid Gantt chart syntax from the processed DataFrame.
    (Reverted: Removed stream-based color coding due to CLI compatibility issues).

    Args:
        df: The processed DataFrame from timeline_logic.process_timeline_data.
        project_title: The title for the Gantt chart.

    Returns:
        A string containing the Mermaid Gantt chart syntax.
    """
    if df is None or df.empty:
        logging.warning("Input DataFrame is empty or None. Cannot generate Mermaid chart.")
        return ""

    mermaid_lines = [
        "gantt",
        f"    title {project_title}",
        "    dateFormat  YYYY-MM-DD"
    ]

    # Removed Milestone Styling Setup

    # --- Generate Sections and Items ---
    # Group by WorkStream to create sections
    # Use dropna=False to handle potential NaN WorkStream names during grouping
    grouped = df.groupby('WorkStream', sort=False, dropna=False)

    for workstream, group in grouped:
        # Add section header, handle potential NaN/empty workstream names
        section_name = str(workstream) if pd.notna(workstream) and str(workstream).strip() else "General Tasks"
        mermaid_lines.append(f"    section {section_name}")

        # Removed determination of item_class

        for index, row in group.iterrows():
            # Use WorkPackage as the display name
            item_name = str(row['WorkPackage']).strip()
            if not item_name:
                # Log message refers to WorkPackage
                logging.warning(f"Skipping row {index} due to empty WorkPackage name.")
                continue

            # Reverted: No custom styling application
            if row.get('IsGeneratedMilestone', False):
                # Milestone formatting (standard)
                milestone_date = row['MilestoneDate']
                mermaid_lines.append(f"    {item_name} :milestone, {milestone_date}, 0d")
            else:
                # Regular WorkPackage formatting (standard, includes status)
                status = str(row['Status']).strip() # Use original status again
                start_date = row['Start']
                duration = row['Duration']

                # Format: Item Name :status, startDate, duration
                # Handle cases where status might be empty
                if status:
                    mermaid_lines.append(f"    {item_name} :{status}, {start_date}, {duration}d")
                else:
                    # If status is empty (e.g., not started), omit the status tag
                    mermaid_lines.append(f"    {item_name} : {start_date}, {duration}d")

    # Removed adding class definitions at the end

    logging.info("Mermaid Gantt chart syntax generated successfully.") # Reverted log message
    return "\n".join(mermaid_lines)

if __name__ == '__main__':
    # Example Usage (requires updated timeline_logic and input_parser)
    from input_parser import parse_csv
    from timeline_logic import process_timeline_data
    import os

    # Create a dummy CSV for testing (No Task column)
    dummy_data = {
        'WorkStream': ['Stream A', 'Stream A', 'Stream B', 'Stream B', 'Stream C', 'Stream D', 'Stream D', 'Stream E', None], # Removed Stream F
        'WorkPackage': ['Package 1', 'Package 2', 'Package 3', 'Package 4', 'Explicit MS Pkg', 'Group WP 1', 'Group WP 2', 'Group WP 3', 'Package 5'], # WP holds name
        'Start': ['2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15', '2024-01-20', '2024-02-01', '2024-02-05', '2024-02-10', '2024-03-01'],
        'End': ['2024-01-04', '2024-01-09', '2024-01-14', '2024-01-19', '2024-01-20', '2024-02-04', '2024-02-09', '2024-02-15', '2024-03-05'],
        'PercentComplete': [100, 50, 100, 100, None, 100, 100, 0, 20], # G2 complete
        'IsMilestone': [False, False, False, False, True, False, False, False, False],
        'MilestoneGroup': ['', '', 'G1', 'G1', '', 'G2', 'G2', 'G3', '']
    }
    # Use original dummy file name for consistency if needed, or a new one
    dummy_file = 'dummy_generator_input_no_color.csv'
    pd.DataFrame(dummy_data).to_csv(dummy_file, index=False)

    print(f"--- Testing generator with '{dummy_file}' (Standard Colors) ---")
    parsed_df = parse_csv(dummy_file)
    if parsed_df is not None:
        processed_df = process_timeline_data(parsed_df)
        if not processed_df.empty:
            mermaid_output = generate_mermaid_gantt(processed_df, "Dummy Project Title")
            print("\nGenerated Mermaid Syntax:")
            print(mermaid_output)

    # Clean up (use updated dummy file names)
    if os.path.exists(dummy_file):
        os.remove(dummy_file)
    # Clean up older test files if they exist
    for f in ['dummy_input_no_task.csv', 'missing_wp_col.csv', 'dummy_logic_input_no_task.csv', 'dummy_generator_input_no_task.csv', 'dummy_generator_input_color_test.csv']:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass # Ignore if file is somehow locked
