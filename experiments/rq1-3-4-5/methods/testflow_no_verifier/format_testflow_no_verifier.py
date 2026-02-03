import pandas as pd
import re

def format_app_name(app_name):
    """Convert app name to lowercase without spaces"""
    return app_name.lower().replace(' ', '')

def clean_soa(soa):
    """Clean the soa field: keep original format (Jade Green and content_desc) to match testflow_complete format"""
    # The cleaning (removing 'Jade Green ' and replacing 'content_desc' with 'content-desc') 
    # will be done later by format_testflow.py when creating all_tasks.xlsx
    if pd.isna(soa):
        return soa
    return str(soa)

def format_testflow_no_verifier():
    """Format testflow_no_verifier CSV to match testflow_complete format"""
    
    # Read the input CSV file
    input_file = r'.._evaluation_v4_all_train_merged.csv'
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Original file has {len(df)} rows")
    
    # Map columns to the target format
    formatted_df = pd.DataFrame()
    
    # Map App Name -> app_name (lowercase, no spaces)
    formatted_df['app_name'] = df['App Name'].apply(format_app_name)
    
    # Map Task -> task_desc
    formatted_df['task_desc'] = df['Task']
    
    # Map Summary -> gpt_gen_result
    formatted_df['gpt_gen_result'] = df['Summary']
    
    # Map Task Result -> success
    formatted_df['success'] = df['Task Result']
    
    # Map Steps Count -> n_actions
    formatted_df['n_actions'] = df['Steps Count']
    
    # Map History Action -> soa (with cleaning)
    formatted_df['soa'] = df['History Action'].apply(clean_soa)
    
    # Add related_score column (can be calculated later, set to None for now)
    formatted_df['related_score'] = None
    
    # Add selected column (set to True for all initially)
    formatted_df['selected'] = True
    
    # Sort by app_name then task_desc
    formatted_df = formatted_df.sort_values(by=['app_name', 'task_desc'])
    
    # Save to CSV (similar to hai-testflow-results-with-score.csv)
    output_csv = r'hai-testflow-results-with-score.csv'
    formatted_df.to_csv(output_csv, index=False)
    print(f"Formatted CSV saved to: {output_csv}")
    
    # Save to Excel (similar to hai-testflow-results-with-score.xlsx)
    output_xlsx = r'hai-testflow-results-with-score.xlsx'
    formatted_df.to_excel(output_xlsx, index=False)
    print(f"Formatted Excel saved to: {output_xlsx}")
    
    # Create all_tasks.xlsx (filtered by selected=True, without selected and related_score columns)
    all_tasks_df = formatted_df[formatted_df['selected']].copy()
    all_tasks_df = all_tasks_df.drop(columns=['selected', 'related_score'])
    all_tasks_output = r'all_tasks.xlsx'
    all_tasks_df.to_excel(all_tasks_output, index=False)
    print(f"All tasks Excel saved to: {all_tasks_output}")
    
    # Create apps.txt (list of unique app names)
    apps = formatted_df['app_name'].unique()
    apps_output = r'apps.txt'
    with open(apps_output, 'w') as f:
        for app in sorted(apps):
            f.write(app + '\n')
    print(f"Apps list saved to: {apps_output}")
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total rows: {len(formatted_df)}")
    print(f"Unique apps: {len(apps)}")
    print(f"Success count: {len(formatted_df[formatted_df['success'] == 'SUCCESS'])}")
    print(f"Failure count: {len(formatted_df[formatted_df['success'] == 'FAILURE'])}")
    
    return formatted_df

if __name__ == "__main__":
    df = format_testflow_no_verifier()

