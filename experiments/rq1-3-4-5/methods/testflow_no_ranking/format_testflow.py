# testflow\hai-testflow-results-with-score.xlsx

import os
import pandas as pd

file = r'methods\testflow_no_ranking\hai-testflow-results-with-score.xlsx'
dir = os.path.dirname(file)
testflow = pd.read_excel(file)

for index, row in testflow.iterrows():
    testflow.at[index, 'soa'] = row['soa'].replace('Jade Green ', '').replace('content_desc', 'content-desc')
    
# sort by app_name then task_desc
testflow = testflow.sort_values(by=['app_name', 'task_desc'])
testflow["app_task"] = testflow["app_name"] + " - " + testflow["task_desc"]
unique_app_tasks = testflow['app_task'].unique()


for app_task in unique_app_tasks:
    app_task_rows = testflow[testflow['app_task'] == app_task]
    print(f"App task: {app_task}, len before: {len(app_task_rows)}")
    if len(app_task_rows) == 3:
        continue
    if len(app_task_rows) < 3:
        selected_row = app_task_rows[app_task_rows['selected'] == False]
        if len(selected_row) == 0:
            selected_row = app_task_rows[app_task_rows['selected'] == True]
        if len(selected_row) != 1:
            selected_row = app_task_rows.iloc[0]
        missing = 3 - len(app_task_rows)
        for i in range(missing):
            testflow = testflow._append(selected_row)
    else:
        offset = len(app_task_rows) - 3
        while offset > 0:
            app_task_rows = testflow[testflow['app_task'] == app_task]
            lowest_score = app_task_rows['related_score'].min()
            if len(app_task_rows[app_task_rows['related_score'] == lowest_score]) > 0:
                selected_row = app_task_rows[app_task_rows['related_score'] == lowest_score].iloc[0]
                testflow = testflow.drop(selected_row.name)
            offset -= 1
            
    print(f"App task: {app_task}, len after: {len(testflow[testflow['app_task'] == app_task])}")
    
            


testflow.to_excel(f'{dir}/all_tasks_.xlsx', index=False)   
# all apps
apps = testflow['app_name'].unique()
with open(f'{dir}/apps.txt', 'w') as f:
    for app in apps:
        f.write(app + '\n')