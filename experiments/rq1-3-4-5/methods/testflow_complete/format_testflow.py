# testflow\hai-testflow-results-with-score.xlsx

import pandas as pd

file = r'hai-testflow-results-with-score-ranked.xlsx'
testflow = pd.read_excel(file)
testflow = testflow[testflow['selected']]
testflow = testflow.drop(columns=['selected', 'related_score'])

for index, row in testflow.iterrows():
    testflow.at[index, 'soa'] = row['soa'].replace('Jade Green ', '').replace('content_desc', 'content-desc')
    
# sort by app_name then task_desc
testflow = testflow.sort_values(by=['app_name', 'task_desc'])
    
testflow.to_excel(r'all_tasks_.xlsx', index=False)
# all apps
apps = testflow['app_name'].unique()
with open(r'apps.txt', 'w') as f:
    for app in apps:
        f.write(app + '\n')