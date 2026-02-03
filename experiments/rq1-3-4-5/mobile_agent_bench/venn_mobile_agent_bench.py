import json
import os
import pandas as pd
from venny4py.venny4py import *
import matplotlib.pyplot as plt

# Read summary CSV files for completion data
summary_dir = "mobile_agent_bench/summary"

# Load summary evaluation files
appagent_summary = pd.read_csv(f"{summary_dir}/appagent_evals_mobile_agent_bench.csv")
autodroid_summary = pd.read_csv(f"{summary_dir}/autodroid_evals_mobile_agent_bench.csv")
androidgen_summary = pd.read_csv(f"{summary_dir}/androidgen_evals_mobile_agent_bench.csv")
testflow_summary = pd.read_csv(f"{summary_dir}/testflow_evals_mobile_agent_bench.csv")

# Create task identifiers (app_task_name format)
def create_task_id(row):
    return f"{row['app']}_{row['task_name']}"

# Get completed tasks for each method using task_completed column
appagent_successful = set()
autodroid_successful = set()
androidgen_successful = set()
testflow_successful = set()

# For each method, check which tasks have task_completed=True
for _, row in appagent_summary.iterrows():
    if row['task_completed'] == True:
        # Extract app name from task_name (e.g., "calculator_add" -> "calculator")
        task_parts = row['task_name'].split('_', 1)
        if len(task_parts) == 2:
            app_name, task_name = task_parts
            task_id = f"{app_name}_{task_name}"
            appagent_successful.add(task_id)

for _, row in autodroid_summary.iterrows():
    if row['task_completed'] == True:
        task_parts = row['task_name'].split('_', 1)
        if len(task_parts) == 2:
            app_name, task_name = task_parts
            task_id = f"{app_name}_{task_name}"
            autodroid_successful.add(task_id)

for _, row in androidgen_summary.iterrows():
    if row['task_completed'] == True:
        task_parts = row['task_name'].split('_', 1)
        if len(task_parts) == 2:
            app_name, task_name = task_parts
            task_id = f"{app_name}_{task_name}"
            androidgen_successful.add(task_id)

for _, row in testflow_summary.iterrows():
    if row['task_completed'] == True:
        task_parts = row['task_name'].split('_', 1)
        if len(task_parts) == 2:
            app_name, task_name = task_parts
            task_id = f"{app_name}_{task_name}"
            testflow_successful.add(task_id)

# Create sets dictionary for Venn diagram (ordered)
sets = {
    'AppAgent': appagent_successful,
    'AutoDroid': autodroid_successful,
    'TestFlow': testflow_successful,
    'AndroidGen': androidgen_successful,
}

# Add counts to set names
sets = {f"{k}: {len(v)}": v for k, v in sets.items()}

# Generate Venn diagram
venny4py(sets=sets, out='venn_mobile_agent_bench.pdf')

# Get intersections for analysis
intersection = get_unique(sets)

# Print intersection statistics
print("=== Mobile Agent Benchmark Venn Diagram Analysis ===")
print(f"Total unique tasks across all methods: {len(set().union(*sets.values()))}")

# Debug: Check total tasks and completion rates
print(f"AppAgent total tasks: {len(appagent_summary)}, completed (task_completed=True): {len(appagent_successful)}")
print(f"AutoDroid total tasks: {len(autodroid_summary)}, completed (task_completed=True): {len(autodroid_successful)}")
print(f"androidgen total tasks: {len(androidgen_summary)}, completed (task_completed=True): {len(androidgen_successful)}")
print(f"TestFlow total tasks: {len(testflow_summary)}, completed (task_completed=True): {len(testflow_successful)}")

# Check for unique task names across all datasets
all_tasks = set()
for df in [appagent_summary, autodroid_summary, androidgen_summary, testflow_summary]:
    all_tasks.update(df['task_name'].apply(lambda x: x.split('_', 1)[0] + '_' + x.split('_', 1)[1] if '_' in x else x))
print(f"Total unique task identifiers across all datasets: {len(all_tasks)}")
print()

# Print intersection details
for set_name in intersection:
    print(f"{set_name}: {len(intersection[set_name])} tasks")
    if len(intersection[set_name]) > 0:
        print("Sample tasks:", list(intersection[set_name])[:3])
    print()

# Create analysis folder and save detailed results
analysis_folder = 'mobile_agent_bench_analysis'
os.makedirs(analysis_folder, exist_ok=True)

# Save intersection details to files
for set_name in intersection:
    if len(intersection[set_name]) > 0:
        tasks = list(intersection[set_name])
        # Split tasks into app and task_name
        task_details = []
        for task in tasks:
            parts = task.split('_', 1)
            if len(parts) == 2:
                app, task_name = parts
                task_details.append({'app': app, 'task_name': task_name, 'full_task': task})
        
        if task_details:
            task_df = pd.DataFrame(task_details)
            filename = set_name.replace(' ', '_').replace(':', '_').replace('(', '').replace(')', '').replace(',', '')
            task_df.to_excel(f"{analysis_folder}/{filename}.xlsx", index=False)
            print(f"Saved {len(task_details)} tasks to {analysis_folder}/{filename}.xlsx")

print(f"\nVenn diagram saved as: venn_mobile_agent_bench.pdf")
print(f"Detailed analysis saved in: {analysis_folder}/")
