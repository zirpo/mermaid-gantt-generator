import pandas as pd
import logging

# Configure logging
import os # Add os import for path manipulation
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def parse_input_file(file_path: str) -> pd.DataFrame | None:
    """
    Parses the input CSV or Excel file, validates required columns and data types,
    and cleans the data.

    Args:
        file_path: Path to the input CSV file.

    Returns:
        A pandas DataFrame with validated and cleaned data, or None if errors occur.
    """
    # Updated: Task column removed, WorkPackage is now required for display
    required_columns = ['WorkStream', 'WorkPackage', 'Start', 'End']
    optional_columns = ['PercentComplete', 'IsMilestone', 'MilestoneGroup']
    date_columns = ['Start', 'End']

    try:
        # Determine file type and read accordingly
        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()

        if file_extension == '.csv':
            df = pd.read_csv(file_path, dtype={'WorkStream': str, 'WorkPackage': str})
        elif file_extension in ['.xlsx', '.xls']:
            # For Excel, pandas often infers types well, but specify string columns if needed
            # Also, handle potential date parsing issues in Excel more carefully below
            df = pd.read_excel(file_path, engine='openpyxl', dtype={'WorkStream': str, 'WorkPackage': str})
            # Excel might read empty cells as NaN which can cause issues with string ops later
            # Convert potential NaN in string columns to empty strings AFTER reading
            for col in ['WorkStream', 'WorkPackage', 'MilestoneGroup']:
                 if col in df.columns:
                     df[col] = df[col].fillna('')
        else:
            logging.error(f"Unsupported file type: '{file_extension}'. Please provide a .csv or .xlsx file.")
            return None

        # --- Column Validation ---
        missing_required = [col for col in required_columns if col not in df.columns]
        if missing_required:
            logging.error(f"Missing required columns: {', '.join(missing_required)}")
            return None

        # Add missing optional columns with default values
        for col in optional_columns:
            if col not in df.columns:
                df[col] = None
                logging.warning(f"Optional column '{col}' not found. Added with default values (None).")

        # --- Data Cleaning and Type Conversion ---

        # Handle potential leading/trailing whitespace more robustly
        for col in df.select_dtypes(include=['object']).columns:
            # Apply strip only to actual string instances within the column
            if df[col].notna().any():
                 df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

        # Dates - Try parsing multiple formats
        for col in date_columns:
            # Convert date columns to string BEFORE parsing to handle Excel's date objects/numbers
            # This standardizes the input for pd.to_datetime
            df[col] = df[col].astype(str)
            # Attempt parsing dd.mm.yyyy first
            parsed_dates_eu = pd.to_datetime(df[col], format='%d.%m.%Y', errors='coerce')
            # Attempt parsing YYYY-MM-DD for those that failed the first format
            parsed_dates_iso = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')
            # Combine results: Use EU format if valid, otherwise use ISO format
            df[col] = parsed_dates_eu.combine_first(parsed_dates_iso)

            # Check for any remaining NaNs after trying both formats
            if df[col].isnull().any():
                invalid_rows = df[df[col].isnull()].index.tolist()
                logging.error(f"Invalid date format found in column '{col}' for rows (0-based index): {invalid_rows}. Expected DD.MM.YYYY or YYYY-MM-DD.")
                # return None # Stricter approach: Exit if any date is invalid

        # PercentComplete
        if 'PercentComplete' in df.columns:
            # Convert to numeric, coercing errors. Fill NaNs resulting from coercion or original NaNs with 0.
            df['PercentComplete'] = pd.to_numeric(df['PercentComplete'], errors='coerce').fillna(0)
            # Clamp values between 0 and 100
            df['PercentComplete'] = df['PercentComplete'].clip(0, 100)
        else:
             df['PercentComplete'] = 0 # Ensure column exists if not optional

        # IsMilestone
        if 'IsMilestone' in df.columns:
            # Map various truthy/falsy values to boolean, default NaNs to False
            true_values = ['true', 'yes', '1', 't', 'y']
            df['IsMilestone'] = df['IsMilestone'].fillna(False).astype(str).str.lower().isin(true_values)
        else:
            df['IsMilestone'] = False # Ensure column exists if not optional

        # MilestoneGroup - fillna with empty string for easier grouping later
        if 'MilestoneGroup' in df.columns:
            df['MilestoneGroup'] = df['MilestoneGroup'].fillna('')
        else:
            df['MilestoneGroup'] = '' # Ensure column exists if not optional

        # Drop rows where essential data (like WorkPackage name or dates) might be missing after cleaning
        # Check for NaNs in required columns that shouldn't be NaN after processing
        # Updated: Check WorkPackage instead of Task
        if df[['WorkPackage', 'Start', 'End']].isnull().any().any():
             logging.warning("Rows with missing essential data (WorkPackage, Start, End) detected after cleaning.")
             # Decide whether to drop or raise error - dropping for now
             df.dropna(subset=['WorkPackage', 'Start', 'End'], inplace=True)


        logging.info(f"Successfully parsed and validated '{file_path}'.")
        return df

    except FileNotFoundError:
        logging.error(f"Input file not found: {file_path}")
        return None
    except pd.errors.EmptyDataError:
        logging.error(f"Input file is empty: {file_path}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during parsing: {e}")
        return None

if __name__ == '__main__':
    # Example usage for testing the parser directly
    # --- Test CSV ---
    dummy_csv_data = {
        'WorkStream': ['CSV Stream A', 'CSV Stream A', 'CSV Stream B', 'CSV Stream B', 'CSV Stream C'],
        'WorkPackage': ['Package 1', 'Package 2', 'Package 3', 'Package 4', 'Milestone Pkg'], # WorkPackage now holds the name
        'Start': ['2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15', '2024-01-20'],
        'End': ['2024-01-04', '2024-01-09', '2024-01-14', '2024-01-19', '2024-01-20'],
        'PercentComplete': [100, 50, 'abc', None, 100], # Include bad data
        'IsMilestone': [False, 'False', True, 'yes', 'TRUE'],
        'MilestoneGroup': ['', '', 'G1', 'G1', '']
    }
    dummy_csv_file = 'dummy_input_parser_test.csv'
    pd.DataFrame(dummy_csv_data).to_csv(dummy_csv_file, index=False)

    print(f"--- Testing parser with CSV: '{dummy_csv_file}' ---")
    parsed_df_csv = parse_input_file(dummy_csv_file)
    if parsed_df_csv is not None:
        print("Parsed CSV DataFrame:")
        print(parsed_df_csv)
        print("\nCSV DataFrame Info:")
        parsed_df_csv.info()

    # --- Test Excel ---
    try:
        import openpyxl # Check if installed for Excel test
        dummy_excel_data = {
            'WorkStream': ['Excel Stream 1', 'Excel Stream 2'],
            'WorkPackage': ['Excel Pkg 1', 'Excel Pkg 2'],
            'Start': ['15.05.2024', '2024-05-20'], # Mixed formats
            'End': ['2024-05-19', '25.05.2024'],
            'PercentComplete': [25, 75.5],
            'IsMilestone': [False, True],
            'MilestoneGroup': ['EG1', '']
        }
        dummy_excel_file = 'dummy_input_parser_test.xlsx'
        pd.DataFrame(dummy_excel_data).to_excel(dummy_excel_file, index=False)

        print(f"\n--- Testing parser with Excel: '{dummy_excel_file}' ---")
        parsed_df_excel = parse_input_file(dummy_excel_file)
        if parsed_df_excel is not None:
            print("Parsed Excel DataFrame:")
            print(parsed_df_excel)
            print("\nExcel DataFrame Info:")
            parsed_df_excel.info()
    except ImportError:
        print("\n--- Skipping Excel test: openpyxl not installed ---")
        dummy_excel_file = None # Ensure it's defined for cleanup check

    print("\n--- Testing with non-existent file ---")
    parse_input_file('non_existent_file.xyz')

    print("\n--- Testing with unsupported file type ---")
    with open('dummy_unsupported.txt', 'w') as f: f.write('test')
    parse_input_file('dummy_unsupported.txt')

    print("\n--- Testing with missing required column (WorkPackage) ---")
    df_missing_col = pd.DataFrame(dummy_csv_data).drop(columns=['WorkPackage'])
    df_missing_col.to_csv('missing_wp_col.csv', index=False)
    parse_input_file('missing_wp_col.csv')


    # Clean up dummy files
    # import os # Already imported
    if os.path.exists(dummy_csv_file): os.remove(dummy_csv_file)
    if dummy_excel_file and os.path.exists(dummy_excel_file): os.remove(dummy_excel_file)
    if os.path.exists('missing_wp_col.csv'): os.remove('missing_wp_col.csv')
    if os.path.exists('dummy_unsupported.txt'): os.remove('dummy_unsupported.txt')
