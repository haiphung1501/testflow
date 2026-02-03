import pandas as pd

def filter_tasks_by_success():
    """Filter tasks: keep SUCCESS if available, otherwise keep 1 FAILURE per task"""
    
    # Read the formatted CSV
    input_file = r'hai-testflow-results-with-score.csv'
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Original file has {len(df)} rows")
    print(f"Unique tasks: {df['task_desc'].nunique()}")
    print(f"Success rows: {len(df[df['success'] == 'SUCCESS'])}")
    print(f"Failure rows: {len(df[df['success'] == 'FAILURE'])}")
    
    # Group by task_desc and filter
    filtered_rows = []
    
    for task_desc, group in df.groupby('task_desc'):
        success_rows = group[group['success'] == 'SUCCESS']
        failure_rows = group[group['success'] == 'FAILURE']
        
        if len(success_rows) > 0:
            # Keep only 1 SUCCESS row per task (first one)
            filtered_rows.append(success_rows.head(1))
            print(f"Task '{task_desc}': Keeping 1 SUCCESS row (out of {len(success_rows)} available)")
        else:
            # Keep only 1 FAILURE row if no SUCCESS exists
            if len(failure_rows) > 0:
                filtered_rows.append(failure_rows.head(1))
                print(f"Task '{task_desc}': Keeping 1 FAILURE row (no SUCCESS available)")
    
    # Combine all filtered rows
    filtered_df = pd.concat(filtered_rows, ignore_index=True)
    
    print(f"\nAfter filtering:")
    print(f"Total rows: {len(filtered_df)}")
    print(f"Unique tasks: {filtered_df['task_desc'].nunique()}")
    print(f"Success rows: {len(filtered_df[filtered_df['success'] == 'SUCCESS'])}")
    print(f"Failure rows: {len(filtered_df[filtered_df['success'] == 'FAILURE'])}")
    
    # Sort by app_name then task_desc
    filtered_df = filtered_df.sort_values(by=['app_name', 'task_desc'])
    
    # Update the CSV file
    filtered_df.to_csv(input_file, index=False)
    print(f"\nUpdated {input_file}")
    
    # Update the Excel file
    excel_file = r'hai-testflow-results-with-score.xlsx'
    filtered_df.to_excel(excel_file, index=False)
    print(f"Updated {excel_file}")
    
    # Update all_tasks.xlsx (filtered by selected=True, without selected and related_score columns)
    all_tasks_df = filtered_df[filtered_df['selected']].copy()
    all_tasks_df = all_tasks_df.drop(columns=['selected', 'related_score'])
    
    # Clean SOA field for all_tasks.xlsx
    for index, row in all_tasks_df.iterrows():
        if pd.isna(row['soa']):
            all_tasks_df.at[index, 'soa'] = ''
        else:
            all_tasks_df.at[index, 'soa'] = str(row['soa']).replace('Jade Green ', '').replace('content_desc', 'content-desc')
    
    all_tasks_output = r'all_tasks.xlsx'
    all_tasks_df.to_excel(all_tasks_output, index=False)
    print(f"Updated {all_tasks_output}")
    
    # Update apps.txt
    apps = filtered_df['app_name'].unique()
    apps_output = r'apps.txt'
    with open(apps_output, 'w') as f:
        for app in sorted(apps):
            f.write(app + '\n')
    print(f"Updated {apps_output}")
    
    return filtered_df

if __name__ == "__main__":
    df = filter_tasks_by_success()

