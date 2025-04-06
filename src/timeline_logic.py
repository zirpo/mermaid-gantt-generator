import pandas as pd
import logging
from datetime import timedelta
from pandas.tseries.offsets import BusinessDay # Import BusinessDay

def calculate_duration(start_date: pd.Timestamp, end_date: pd.Timestamp) -> int:
    """Calculates the duration between two dates in days (inclusive)."""
    if pd.isna(start_date) or pd.isna(end_date) or end_date < start_date:
        return 0
    # Add one day because Gantt duration is often inclusive
    return (end_date - start_date).days + 1

def get_task_status(percent_complete: float | None) -> str:
    """Determines the Mermaid status tag based on completion percentage."""
    # Treat None, NaN, or 0% as 'active' for simplicity in Gantt
    if percent_complete is None or pd.isna(percent_complete) or percent_complete <= 0:
        return "active"
    elif percent_complete >= 100:
        return "done"
    elif percent_complete > 0: # Covers > 0 and < 100
        return "active"
    else: # Should technically not be reached if <= 0 is active
        return "active"

def calculate_end_date(start_date: pd.Timestamp, working_days: int | float | None) -> pd.Timestamp:
    """
    Calculates the end date by adding working days (Mon-Fri) to the start date.
    Note: The start date itself counts as the first working day if it's a business day.
    Returns start_date if working_days is invalid (None, NaN, <= 0).
    """
    # Return start_date for invalid inputs instead of NaT
    if pd.isna(start_date) or pd.isna(working_days):
        return start_date
    
    # Ensure working_days is an integer, handle potential float input
    try:
        # Use floor to handle potential float inputs like 3.7 days -> 3 days
        wd_int = int(working_days) 
    except (ValueError, TypeError):
         # If conversion fails, treat as invalid duration
        return start_date

    # If duration is 0 or less after conversion, return start date
    if wd_int <= 0:
        return start_date

    # BusinessDay(n) adds n business days. If start_date is a business day,
    # adding (n-1) business days gives the correct end date for an n-day task.
    # If start_date is NOT a business day, BusinessDay() rolls forward to the next
    # business day automatically before adding days.
    # We subtract 1 because the duration includes the start day.
    # Example: Start Mon, 1 working day -> End Mon (Mon + BDay(0))
    # Example: Start Mon, 2 working days -> End Tue (Mon + BDay(1))
    # Example: Start Fri, 3 working days -> End Tue (Fri + BDay(2))
    # Example: Start Sat, 1 working day -> End Mon (Sat rolls to Mon, Mon + BDay(0))
    # BusinessDay calculation remains the same for wd_int > 0
    # Subtract 1 day from the count because the start day is included
    # Apply the offset
    return start_date + BusinessDay(wd_int - 1)


def process_timeline_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the parsed DataFrame to calculate end dates (if using working days),
    durations, statuses,
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

    # --- Ensure required columns exist ---
    required_cols = ['WorkStream', 'WorkPackage', 'Start']
    missing_req_cols = [col for col in required_cols if col not in df.columns]
    if missing_req_cols:
        logging.error(f"Input data missing required columns: {missing_req_cols}. Cannot process.")
        return pd.DataFrame()

    # --- Ensure optional columns exist with defaults if missing ---
    # This prevents KeyErrors later when accessing them
    if 'End' not in df.columns:
        df['End'] = pd.NaT
    if 'WorkingDays' not in df.columns:
        df['WorkingDays'] = pd.NA # Use pandas NA for numeric missing
    if 'PercentComplete' not in df.columns:
        df['PercentComplete'] = pd.NA # Use pandas NA
    if 'IsMilestone' not in df.columns:
        df['IsMilestone'] = False # Default to False
    if 'MilestoneGroup' not in df.columns:
        df['MilestoneGroup'] = '' # Default to empty string

    # --- Convert types and handle errors early ---
    df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
    df['End'] = pd.to_datetime(df['End'], errors='coerce')
    df['WorkingDays'] = pd.to_numeric(df['WorkingDays'], errors='coerce')
    df['PercentComplete'] = pd.to_numeric(df['PercentComplete'], errors='coerce')
    # Convert boolean-like values for IsMilestone
    df['IsMilestone'] = df['IsMilestone'].replace({
             'True': True, 'False': False, 'yes': True, 'no': False,
             '1': True, '0': False, 1: True, 0: False,
             True: True, False: False # Handle actual booleans too
         }).fillna(False).astype(bool) # Fill NA with False and ensure boolean type
    df['MilestoneGroup'] = df['MilestoneGroup'].fillna('').astype(str) # Fill NA with empty string

    # Drop rows where Start date is invalid after conversion
    invalid_start_rows = df[df['Start'].isna()].index
    if not invalid_start_rows.empty:
        logging.warning(f"Dropping rows {invalid_start_rows.tolist()} due to invalid 'Start' date.")
        df.drop(index=invalid_start_rows, inplace=True)
        if df.empty: return pd.DataFrame() # Return if all rows dropped

    # --- Calculate End Date if WorkingDays is provided ---
    # Identify rows where End is missing but WorkingDays is present and valid
    needs_end_date_calc = df['End'].isna() & df['WorkingDays'].notna() & (df['WorkingDays'] > 0)

    if needs_end_date_calc.any():
        logging.info(f"Calculating End dates for {needs_end_date_calc.sum()} rows based on 'WorkingDays'.")
        df.loc[needs_end_date_calc, 'End'] = df.loc[needs_end_date_calc].apply(
            lambda row: calculate_end_date(row['Start'], row['WorkingDays']), axis=1
        )
        # Ensure the 'End' column remains datetime type after updates
        df['End'] = pd.to_datetime(df['End'], errors='coerce')

        # Check if any calculations resulted in the End date still being NaT (e.g., if calculate_end_date returned start_date due to invalid WD)
        # We might not need to drop these, just ensure they are handled later (e.g., duration calculation)
        failed_calc = needs_end_date_calc & df['End'].isna()
        if failed_calc.any():
             failed_indices = df[failed_calc].index.tolist()
             logging.warning(f"End date could not be calculated for rows: {failed_indices}. 'End' remains NaT.")
             # Don't drop, let duration calculation handle NaT End date

    # --- Calculate Duration (Calendar Days) and Status ---
    # Ensure 'End' is set to 'Start' if it's still NaT after potential calculation
    # This ensures duration calculation doesn't fail for rows where only Start was given
    df['End'] = df['End'].fillna(df['Start'])

    df['Duration'] = df.apply(lambda row: calculate_duration(row['Start'], row['End']), axis=1)
    df['Status'] = df['PercentComplete'].apply(get_task_status)

    # --- Identify Explicit Milestones ---
    explicit_milestones = df[df['IsMilestone'] == True].copy()
    for index, row in explicit_milestones.iterrows():
        # Explicit milestones use their own 'End' date as the milestone date
        milestone_date = row['End']
        # If End date is NaT (was missing or invalid), use Start date
        if pd.isna(milestone_date):
             milestone_date = row['Start']
        # If Start date was also invalid (already dropped), this row wouldn't exist here.
        # But double-check milestone_date validity before adding.
        if pd.isna(milestone_date):
            logging.warning(f"Explicit milestone '{row['WorkPackage']}' has no valid date (Start or End). Skipping.")
            continue

        milestones_to_add.append({
            'WorkPackage': row['WorkPackage'],
            'IsGeneratedMilestone': True,
            'MilestoneDate': milestone_date.strftime('%Y-%m-%d'),
            'WorkStream': row['WorkStream']
        })
        # Set status for the original row in df to 'milestone' for filtering later
        df.loc[index, 'Status'] = 'milestone'


    # --- Identify Grouped Milestones ---
    # Filter out explicit milestone rows and rows not part of any group
    # Ensure 'End' date exists before checking completion for grouped milestones
    workpackage_df = df[(df['IsMilestone'] == False) & (df['MilestoneGroup'] != '') & df['End'].notna()].copy()

    if not workpackage_df.empty:
        grouped = workpackage_df.groupby('MilestoneGroup')
        for name, group in grouped:
            # Ensure PercentComplete is not NaN before checking min()
            if group['PercentComplete'].isna().any():
                 logging.info(f"Grouped milestone '{name}' skipped: contains tasks with missing completion status.")
                 continue

            all_complete = group['PercentComplete'].min() >= 100
            if all_complete:
                latest_end_date = group['End'].max()
                # latest_end_date should be valid here because we filtered for End.notna()
                if pd.isna(latest_end_date):
                     logging.error(f"Unexpected NaT end date for completed grouped milestone '{name}'. Skipping.") # Should not happen
                     continue

                milestones_to_add.append({
                    'WorkPackage': name,
                    'IsGeneratedMilestone': True,
                    'MilestoneDate': latest_end_date.strftime('%Y-%m-%d'),
                    'WorkStream': group['WorkStream'].iloc[0] if not group.empty else 'Milestones'
                })
            else:
                logging.info(f"Grouped milestone '{name}' condition not met (not all WorkPackages 100% complete).")


    # --- Combine regular WorkPackages and milestones ---
    # Select columns needed for Mermaid generation for regular WorkPackages
    # Filter out rows that were defined as explicit milestones (using the status we set)
    # Ensure Start and Duration are valid before including
    regular_wp_df = df[
        (df['Status'] != 'milestone') & # Filter out rows marked as explicit milestones
        df['Start'].notna() &
        df['Duration'].notna() & (df['Duration'] > 0)
    ][['WorkStream', 'WorkPackage', 'Status', 'Start', 'Duration']].copy()

    if not regular_wp_df.empty:
        regular_wp_df['Start'] = regular_wp_df['Start'].dt.strftime('%Y-%m-%d') # Format date
        regular_wp_df['IsGeneratedMilestone'] = False # Add flag

    # Create DataFrame for generated milestones
    milestones_df = pd.DataFrame(milestones_to_add)
    if not milestones_df.empty:
        milestones_df['Status'] = 'milestone'
        milestones_df['Start'] = milestones_df['MilestoneDate']
        milestones_df['Duration'] = 0 # Milestones have 0 duration in Mermaid syntax
        milestones_df['IsGeneratedMilestone'] = True # Ensure flag is set

    # Concatenate regular WorkPackages and generated milestones
    final_df = pd.concat([regular_wp_df, milestones_df], ignore_index=True)

    if final_df.empty:
         logging.warning("No valid tasks or milestones found after processing.")
         return pd.DataFrame()

    # Sort potentially by WorkStream then Start date for better organization in Mermaid
    # Convert 'Start' back to datetime for proper sorting if needed, handle potential errors
    final_df['SortDate'] = pd.to_datetime(final_df['Start'], errors='coerce')
    # Handle potential NaT in SortDate if Start date string was somehow invalid
    final_df = final_df.sort_values(by=['WorkStream', 'SortDate'], na_position='last').drop(columns=['SortDate'])


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
