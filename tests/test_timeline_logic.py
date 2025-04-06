import pandas as pd
import pytest
from datetime import date
from src.timeline_logic import (
    calculate_duration,
    get_task_status,
    calculate_end_date,
    process_timeline_data,
)

# Helper function to create sample DataFrames
def create_sample_df(data):
    df = pd.DataFrame(data)
    # Convert date columns to datetime objects if they exist, handling mixed formats
    for col in ['Start', 'End']:
        if col in df.columns:
            # Store original series to attempt second format if first fails
            original_series = df[col]
            # Attempt YYYY-MM-DD first
            df[col] = pd.to_datetime(original_series, format='%Y-%m-%d', errors='coerce')
            # Identify where parsing failed (became NaT)
            failed_parse_mask = df[col].isna()
            # Attempt dd.mm.yyyy on the originally failed ones
            if failed_parse_mask.any():
                df.loc[failed_parse_mask, col] = pd.to_datetime(original_series[failed_parse_mask], format='%d.%m.%Y', errors='coerce')

    if 'PercentComplete' in df.columns:
         # Ensure PercentComplete is numeric, coercing errors to NaN
         df['PercentComplete'] = pd.to_numeric(df['PercentComplete'], errors='coerce')
    if 'WorkingDays' in df.columns:
         df['WorkingDays'] = pd.to_numeric(df['WorkingDays'], errors='coerce')
    if 'IsMilestone' in df.columns:
         # Convert common boolean representations to actual booleans
         df['IsMilestone'] = df['IsMilestone'].replace({
             'True': True, 'False': False,
             'yes': True, 'no': False,
             '1': True, '0': False,
             1: True, 0: False,
             True: True, False: False # Handle actual booleans too
         }).astype(bool) # Ensure boolean type

    return df

# --- Tests for calculate_end_date ---

def test_calculate_end_date_no_weekends():
    start = pd.Timestamp('2024-01-01') # Monday
    assert calculate_end_date(start, 5) == pd.Timestamp('2024-01-05') # Friday

def test_calculate_end_date_crossing_weekend():
    start = pd.Timestamp('2024-01-04') # Thursday
    assert calculate_end_date(start, 3) == pd.Timestamp('2024-01-08') # Monday (Thu, Fri, Mon)

def test_calculate_end_date_starting_friday_crossing_weekend():
    start = pd.Timestamp('2024-01-05') # Friday
    assert calculate_end_date(start, 2) == pd.Timestamp('2024-01-08') # Monday (Fri, Mon)

def test_calculate_end_date_zero_days():
    start = pd.Timestamp('2024-01-01')
    assert calculate_end_date(start, 0) == start # Duration 0 means end is same as start

def test_calculate_end_date_one_day():
    start = pd.Timestamp('2024-01-01') # Monday
    assert calculate_end_date(start, 1) == start # Duration 1 means end is same as start

def test_calculate_end_date_none_days():
    start = pd.Timestamp('2024-01-01')
    assert calculate_end_date(start, None) == start # None duration should likely default to start date

def test_calculate_end_date_float_days():
    start = pd.Timestamp('2024-01-01') # Monday
    # Floats should probably be rounded or truncated - assuming truncation/floor
    assert calculate_end_date(start, 3.7) == pd.Timestamp('2024-01-03') # Wednesday (Mon, Tue, Wed)

# --- Tests for get_task_status ---

def test_get_task_status_done():
    assert get_task_status(100) == 'done'
    assert get_task_status(100.0) == 'done'

def test_get_task_status_active():
    assert get_task_status(0) == 'active'
    assert get_task_status(50) == 'active'
    assert get_task_status(99.9) == 'active'

def test_get_task_status_none():
    assert get_task_status(None) == 'active' # Assuming None means not started or active

def test_get_task_status_nan():
     assert get_task_status(float('nan')) == 'active' # Assuming NaN means active

# --- Tests for calculate_duration (Assuming it calculates inclusive days) ---
# Note: The actual implementation might differ (e.g., working days only).
# These tests assume simple date difference + 1 for inclusiveness. Adjust if needed.

def test_calculate_duration_same_day():
     start = pd.Timestamp('2024-01-01')
     end = pd.Timestamp('2024-01-01')
     assert calculate_duration(start, end) == 1 # Inclusive duration

def test_calculate_duration_multiple_days():
     start = pd.Timestamp('2024-01-01')
     end = pd.Timestamp('2024-01-05')
     assert calculate_duration(start, end) == 5 # Inclusive duration

def test_calculate_duration_invalid_order():
     # Behavior might vary: return 0, negative, or raise error. Assuming 0 or negative.
     start = pd.Timestamp('2024-01-05')
     end = pd.Timestamp('2024-01-01')
     assert calculate_duration(start, end) <= 0 # Or check for specific error if it raises

# --- Tests for process_timeline_data ---

def test_process_timeline_data_basic():
    data = {
        'WorkStream': ['WS1'],
        'WorkPackage': ['Task 1'],
        'Start': ['2024-01-01'],
        'End': ['2024-01-03'],
        'PercentComplete': [50]
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy()) # Pass copy to avoid modifying original

    assert not df_processed.empty
    assert 'Duration' in df_processed.columns
    assert 'Status' in df_processed.columns
    assert df_processed.loc[0, 'Duration'] == 3 # Check calculated duration
    assert df_processed.loc[0, 'Status'] == 'active'
    # Check the final string format of the date
    assert df_processed.loc[0, 'Start'] == '2024-01-01'
    # 'End' column is not expected in the final output DataFrame

def test_process_timeline_data_working_days():
    data = {
        'WorkStream': ['WS1'],
        'WorkPackage': ['Task WD'],
        'Start': ['2024-01-04'], # Thursday
        'WorkingDays': [3],
        'PercentComplete': [100]
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Check Duration which reflects the calculated end date (Thu, Fri, Mon -> 5 calendar days)
    # Note: The original df inside process_timeline_data would have End='2024-01-08'
    assert df_processed.loc[0, 'Duration'] == 5
    assert df_processed.loc[0, 'Status'] == 'done'
    assert df_processed.loc[0, 'Start'] == '2024-01-04'

def test_process_timeline_data_end_date_precedence():
    # End date should take precedence over WorkingDays if both are provided
    data = {
        'WorkStream': ['WS1'],
        'WorkPackage': ['Task Both'],
        'Start': ['2024-01-01'], # Monday
        'End': ['2024-01-03'], # Wednesday (Explicit End)
        'WorkingDays': [5],    # Should be ignored
        'PercentComplete': [0]
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Check Duration reflects the explicit End date (Jan 1 to Jan 3 -> 3 days)
    assert df_processed.loc[0, 'Duration'] == 3
    assert df_processed.loc[0, 'Start'] == '2024-01-01'
    assert df_processed.loc[0, 'Status'] == 'active' # 0% complete

def test_process_timeline_data_explicit_milestone():
    data = {
        'WorkStream': ['Milestones'],
        'WorkPackage': ['M1'],
        'Start': ['2024-01-10'], # Date used if End is missing
        'End': ['2024-01-15'],   # Date used for milestone
        'IsMilestone': [True],
        'PercentComplete': [None] # Should not affect milestone status
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Find the milestone row in the output
    milestone_row = df_processed[df_processed['WorkPackage'] == 'M1']
    assert not milestone_row.empty
    assert milestone_row.iloc[0]['IsGeneratedMilestone'] == True # Check the flag
    assert milestone_row.iloc[0]['Status'] == 'milestone'
    assert milestone_row.iloc[0]['Start'] == '2024-01-15' # Milestone 'Start' is its date
    assert milestone_row.iloc[0]['Duration'] == 0 # Milestones have 0 duration

def test_process_timeline_data_explicit_milestone_no_end():
    data = {
        'WorkStream': ['Milestones'],
        'WorkPackage': ['M2'],
        'Start': ['2024-01-12'], # Date used for milestone
        'IsMilestone': [True]
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Find the milestone row in the output
    milestone_row = df_processed[df_processed['WorkPackage'] == 'M2']
    assert not milestone_row.empty
    assert milestone_row.iloc[0]['IsGeneratedMilestone'] == True
    assert milestone_row.iloc[0]['Status'] == 'milestone'
    assert milestone_row.iloc[0]['Start'] == '2024-01-12' # Uses Start date if End is missing
    assert milestone_row.iloc[0]['Duration'] == 0

def test_process_timeline_data_grouped_milestone_incomplete():
    data = {
        'WorkStream': ['WS1', 'WS1'],
        'WorkPackage': ['Task A', 'Task B'],
        'Start': ['2024-01-01', '2024-01-03'],
        'End': ['2024-01-05', '2024-01-08'],
        'PercentComplete': [100, 50], # Task B not complete
        'MilestoneGroup': ['Group1', 'Group1']
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Check that no milestone row was added
    assert len(df_processed) == 2
    assert not df_processed['WorkPackage'].str.contains('Group1').any()

def test_process_timeline_data_grouped_milestone_complete():
    data = {
        'WorkStream': ['WS1', 'WS1', 'WS2'],
        'WorkPackage': ['Task A', 'Task B', 'Task C'],
        'Start': ['2024-01-01', '2024-01-03', '2024-01-02'],
        'End': ['2024-01-05', '2024-01-08', '2024-01-06'], # Max end date is 2024-01-08
        'PercentComplete': [100, 100, 50], # Group1 tasks are complete
        'MilestoneGroup': ['Group1', 'Group1', 'Group2'] # Task C is unrelated
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Check that a milestone row was added for Group1
    assert len(df_processed) == 4 # Original 3 + 1 milestone
    milestone_row = df_processed[df_processed['WorkPackage'] == 'Group1']
    assert not milestone_row.empty
    assert milestone_row.iloc[0]['IsGeneratedMilestone'] == True # Check flag
    assert milestone_row.iloc[0]['Status'] == 'milestone'
    # Milestone date should be the max end date of constituent tasks
    assert milestone_row.iloc[0]['Start'] == '2024-01-08' # Check milestone date (in Start col)
    assert milestone_row.iloc[0]['Duration'] == 0
    # Milestone should likely inherit the WorkStream of its constituents if consistent,
    # or handle inconsistencies (e.g., place in a default 'Milestones' stream). Assuming WS1 here.
    assert milestone_row.iloc[0]['WorkStream'] == 'WS1' # Check WorkStream inherited

def test_process_timeline_data_missing_columns():
    # Should handle missing optional columns gracefully (e.g., default values)
    data = {
        'WorkStream': ['WS1'],
        'WorkPackage': ['Task Minimal'],
        'Start': ['2024-01-01'],
        # Missing End, WorkingDays, PercentComplete, IsMilestone, MilestoneGroup
    }
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Check the single row in the output
    assert len(df_processed) == 1
    assert df_processed.loc[0, 'Start'] == '2024-01-01'
    # End defaults to Start if missing, so duration is 1
    assert df_processed.loc[0, 'Duration'] == 1
    assert df_processed.loc[0, 'Status'] == 'active' # Default status
    assert df_processed.loc[0, 'IsGeneratedMilestone'] == False # Default milestone status

def test_process_timeline_data_invalid_dates():
    data = {
        'WorkStream': ['WS1'],
        'WorkPackage': ['Task Bad Date'],
        'Start': ['invalid-date'],
        'End': ['2024-01-01']
    }
    df_input = create_sample_df(data)
    # The function now drops rows with invalid start dates and logs a warning
    df_processed = process_timeline_data(df_input.copy())
    # Assert that the resulting DataFrame is empty because the only row was dropped
    assert df_processed.empty

def test_process_timeline_data_empty_input():
    df_input = pd.DataFrame(columns=['WorkStream', 'WorkPackage', 'Start', 'End', 'PercentComplete', 'IsMilestone', 'MilestoneGroup'])
    df_processed = process_timeline_data(df_input.copy())
    assert df_processed.empty

def test_process_timeline_data_date_formats():
    data = {
        'WorkStream': ['WS1', 'WS1'],
        'WorkPackage': ['Task YMD', 'Task DMY'],
        'Start': ['2024-02-10', '15.03.2024'],
        'End': ['2024-02-12', '16.03.2024'],
        'PercentComplete': [50, 50]
    }
    # create_sample_df handles parsing, this tests if process_timeline_data uses them correctly
    # create_sample_df handles parsing, this tests if process_timeline_data uses them correctly
    df_input = create_sample_df(data)
    df_processed = process_timeline_data(df_input.copy())

    # Check the final string format and calculated durations
    assert df_processed.loc[0, 'Start'] == '2024-02-10'
    assert df_processed.loc[1, 'Start'] == '2024-03-15'
    # 'End' is not in the final df, check duration instead
    assert df_processed.loc[0, 'Duration'] == 3 # Feb 10 to Feb 12 inclusive
    assert df_processed.loc[1, 'Duration'] == 2 # Mar 15 to Mar 16 inclusive
