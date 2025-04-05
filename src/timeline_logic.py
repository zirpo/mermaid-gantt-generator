import pandas as pd
import logging
from datetime import timedelta

def calculate_duration(start_date: pd.Timestamp, end_date: pd.Timestamp) -> int:
    """Calculates the duration between two dates in days (inclusive)."""
    if pd.isna(start_date) or pd.isna(end_date) or end_date < start_date:
        return 0
    # Add one day because Gantt duration is often inclusive
    return (end_date - start_date).days + 1

def get_task_status(percent_complete: float | None) -> str:
    """Determines the Mermaid status tag based on completion percentage."""
    if percent_complete is None or pd.isna(percent_complete) or percent_complete <= 0:
        return "" # Default/Not started - Mermaid doesn't have a specific tag, empty implies default
    elif percent_complete >= 100:
        return "done"
    elif percent_complete > 0:
        return "active"
    else:
        return "" # Should not happen with cleaning, but default case

def process_timeline_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the parsed DataFrame to calculate durations, statuses,
    and identify/calculate milestones.

    Args:
        df: The input DataFrame from input_parser.

    Returns:
        A DataFrame containing tasks and calculated milestones ready for Mermaid generation.
    """
    if df is None or df.empty:
        logging.warning("Input DataFrame is empty or None. Cannot process timeline data.")
        return pd.DataFrame() # Return empty DataFrame

    processed_tasks = []
    milestones_to_add = []

    # --- Calculate Duration and Status for regular tasks ---
    df['Duration'] = df.apply(lambda row: calculate_duration(row['Start'], row['End']), axis=1)
    df['Status'] = df['PercentComplete'].apply(get_task_status)

    # --- Identify Explicit Milestones ---
    explicit_milestones = df[df['IsMilestone'] == True].copy()
    for index, row in explicit_milestones.iterrows():
        # Explicit milestones use their own 'End' date as the milestone date
        milestone_date = row['End']
        if pd.isna(milestone_date):
             # If End date is missing for an explicit milestone, try Start date
             milestone_date = row['Start']
        if pd.isna(milestone_date):
             # Updated: Use WorkPackage in log message
            logging.warning(f"Explicit milestone '{row['WorkPackage']}' has no valid Start or End date. Skipping.")
            continue

        milestones_to_add.append({
            'WorkPackage': row['WorkPackage'], # Updated: Use WorkPackage name from the milestone row
            'IsGeneratedMilestone': True, # Flag to distinguish from regular tasks
            'MilestoneDate': milestone_date.strftime('%Y-%m-%d'),
            'WorkStream': row['WorkStream'] # Keep WorkStream for potential sectioning
        })

    # --- Identify Grouped Milestones ---
    # Filter out explicit milestone rows and rows not part of any group
    # Updated: Still group by MilestoneGroup, but process WorkPackages within
    workpackage_df = df[(df['IsMilestone'] == False) & (df['MilestoneGroup'] != '')].copy()
    grouped = workpackage_df.groupby('MilestoneGroup')

    for name, group in grouped:
        all_complete = group['PercentComplete'].min() >= 100 # Check if all WorkPackages in the group are 100%
        if all_complete:
            latest_end_date = group['End'].max()
            if pd.isna(latest_end_date):
                 # Updated: Log message refers to WorkPackages
                 logging.warning(f"Grouped milestone '{name}' has WorkPackages with missing end dates. Cannot determine milestone date. Skipping.")
                 continue

            # Use the MilestoneGroup name as the milestone name
            milestones_to_add.append({
                'WorkPackage': name, # Updated: Use MilestoneGroup name as the WorkPackage name for the milestone entry
                'IsGeneratedMilestone': True,
                'MilestoneDate': latest_end_date.strftime('%Y-%m-%d'),
                # Try to get a representative WorkStream, e.g., from the first WorkPackage in the group
                'WorkStream': group['WorkStream'].iloc[0] if not group.empty else 'Milestones'
            })
        else:
             # Updated: Log message refers to WorkPackages
            logging.info(f"Grouped milestone '{name}' condition not met (not all WorkPackages 100% complete).")


    # --- Combine regular WorkPackages and milestones ---
    # Select columns needed for Mermaid generation for regular WorkPackages
    # Filter out rows that were ONLY defined as explicit milestones
    # Updated: Select WorkPackage instead of Task
    regular_wp_df = df[df['IsMilestone'] == False][['WorkStream', 'WorkPackage', 'Status', 'Start', 'Duration']].copy()
    regular_wp_df['Start'] = regular_wp_df['Start'].dt.strftime('%Y-%m-%d') # Format date
    regular_wp_df['IsGeneratedMilestone'] = False # Add flag

    # Create DataFrame for generated milestones (using WorkPackage column now)
    milestones_df = pd.DataFrame(milestones_to_add)
    if not milestones_df.empty:
        # Add placeholder columns needed for concatenation if milestones exist
        milestones_df['Status'] = 'milestone'
        milestones_df['Start'] = milestones_df['MilestoneDate'] # Use milestone date as 'Start' for sorting/consistency
        milestones_df['Duration'] = 0 # Milestones have 0 duration in Mermaid syntax

    # Concatenate regular WorkPackages and generated milestones
    # Updated: Concatenate regular_wp_df
    final_df = pd.concat([regular_wp_df, milestones_df], ignore_index=True)

    # Sort potentially by WorkStream then Start date for better organization in Mermaid
    # Convert 'Start' back to datetime for proper sorting if needed, handle potential errors
    final_df['SortDate'] = pd.to_datetime(final_df['Start'], errors='coerce')
    final_df = final_df.sort_values(by=['WorkStream', 'SortDate']).drop(columns=['SortDate'])


    logging.info("Timeline data processed successfully.")
    return final_df


if __name__ == '__main__':
    # Example Usage (requires input_parser module - use updated parser)
    from input_parser import parse_csv # Assumes updated input_parser.py
    import os

    # Create a dummy CSV for testing (Updated: No Task column)
    dummy_data = {
        'WorkStream': ['Stream A', 'Stream A', 'Stream B', 'Stream B', 'Stream C', 'Stream D', 'Stream D', 'Stream E'],
        'WorkPackage': ['Package 1', 'Package 2', 'Package 3', 'Package 4', 'Explicit MS Pkg', 'Group WP 1', 'Group WP 2', 'Group WP 3'], # WP holds name
        'Start': ['2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15', '2024-01-20', '2024-02-01', '2024-02-05', '2024-02-10'],
        'End': ['2024-01-04', '2024-01-09', '2024-01-14', '2024-01-19', '2024-01-20', '2024-02-04', '2024-02-09', '2024-02-15'],
        'PercentComplete': [100, 50, 100, 100, None, 100, 100, 90],
        'IsMilestone': [False, False, False, False, True, False, False, False],
        'MilestoneGroup': ['', '', 'G1', 'G1', '', 'G2', 'G2', 'G3'] # G1 incomplete, G2 complete
    }
    dummy_file = 'dummy_logic_input_no_task.csv'
    pd.DataFrame(dummy_data).to_csv(dummy_file, index=False)

    print(f"--- Testing logic with '{dummy_file}' (No Task Column) ---")
    parsed_df = parse_csv(dummy_file)
    if parsed_df is not None:
        processed_df = process_timeline_data(parsed_df)
        print("Processed DataFrame for Mermaid:")
        print(processed_df)

    # Clean up (use updated dummy file names)
    if os.path.exists(dummy_file):
        os.remove(dummy_file)
    if os.path.exists('dummy_input_no_task.csv'): # From previous test
         os.remove('dummy_input_no_task.csv')
    if os.path.exists('missing_wp_col.csv'): # From previous test
         os.remove('missing_wp_col.csv')
