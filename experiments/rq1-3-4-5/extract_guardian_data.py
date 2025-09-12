import pandas as pd
import os

def extract_guardian_data():
    """
    Extract all Guardian-related columns from the merged CSV file and save to a new CSV file.
    """
    # Read the original CSV file
    input_file = "merged_all_tasks_before_update.csv"
    output_file = "guardian_data.csv"
    
    print(f"Reading data from {input_file}...")
    # Try different encodings to handle the file
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(input_file, encoding=encoding)
            print(f"Successfully read file with {encoding} encoding")
            break
        except UnicodeDecodeError:
            print(f"Failed to read with {encoding} encoding, trying next...")
            continue
    
    if df is None:
        raise Exception("Could not read the CSV file with any of the attempted encodings")
    
    # Identify all Guardian-related columns
    guardian_columns = []
    for col in df.columns:
        if 'guardian' in col.lower():
            guardian_columns.append(col)
    
    print(f"Found Guardian-related columns: {guardian_columns}")
    
    # Define the base columns we want to keep (as mentioned in the request)
    base_columns = ['app_name', 'task_desc', 'hash', 'n_actions', 'actions', 'groundtruth']
    
    # Combine base columns with Guardian columns
    selected_columns = base_columns + guardian_columns
    
    # Filter the dataframe to only include selected columns
    guardian_df = df[selected_columns]
    
    # Save to new CSV file
    guardian_df.to_csv(output_file, index=False)
    
    print(f"Guardian data saved to {output_file}")
    print(f"Total rows: {len(guardian_df)}")
    print(f"Total columns: {len(guardian_df.columns)}")
    
    # Display column information
    print("\nColumns in the output file:")
    for i, col in enumerate(guardian_df.columns, 1):
        print(f"{i}. {col}")
    
    # Display first few rows for verification
    print(f"\nFirst 3 rows of the output file:")
    print(guardian_df.head(3))
    
    return guardian_df

if __name__ == "__main__":
    try:
        guardian_data = extract_guardian_data()
        print("\n✅ Guardian data extraction completed successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
