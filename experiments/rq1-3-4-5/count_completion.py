import os
import json

def count_completion(method_name):
    eval_dir = f"mobile_agent_bench/evals/evals-{method_name}"
    count = 0
    
    if not os.path.exists(eval_dir):
        print(f"Directory {eval_dir} not found")
        return 0
    
    for filename in os.listdir(eval_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(eval_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    end_correctly = data.get('end_correctly', False)
                    actions = data.get('actions', [])
                    
                    # Count as completion if end_correctly=True AND has actions
                    if end_correctly and len(actions) > 0:
                        count += 1
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    
    return count

# Count for each method
methods = ['appagent', 'autodroid', 'droidagent', 'testflow']
for method in methods:
    count = count_completion(method)
    print(f"{method}: {count}")
