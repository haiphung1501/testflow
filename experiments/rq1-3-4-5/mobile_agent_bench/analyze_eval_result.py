import os
import json
import pandas as pd

METHOD = "guardian"
EVAL_DIR = os.path.join("evals", f"evals-{METHOD}")


def prefix_complete(evals):
    if not evals:
        return 0.0
    count = 0
    for val in evals:
        if val:
            count += 1
        else:
            break
    return count / len(evals)


def load_groundtruth_actions(gt_csv_path: str) -> dict:
    df = pd.read_csv(gt_csv_path, encoding='utf-8', engine='python')
    if "task_name" not in df.columns or "actions" not in df.columns:
        raise ValueError("groundtruth CSV must contain 'task_name' and 'actions'")

    task_to_gt = {}
    for _, row in df.iterrows():
        task = row['task_name']
        actions_str = str(row['actions']).replace('\r\n', '\n').replace('\r', '\n').strip()
        actions = [line for line in actions_str.split('\n') if line]
        task_to_gt[task] = actions
    return task_to_gt


def analyze(gt_csv_path: str):
    task_to_gt = load_groundtruth_actions(gt_csv_path)

    results = []
    total_correct_actions = 0
    total_actions = 0
    total_exact_match = 0
    total_tasks_completed = 0
    total_tasks_achieved = 0
    total_not_done_but_end = 0

    for fname in os.listdir(EVAL_DIR):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(EVAL_DIR, fname), 'r', encoding='utf-8') as f:
            data = json.load(f)

        task_name = data.get('task_name')
        candidate_actions = data.get('actions', [])
        evals = data.get('evals', [])
        end_correctly = bool(data.get('end_correctly', False))

        gt_actions = task_to_gt.get(task_name, [])

        # Don't trim candidate_actions or evals - extra steps should be counted as incorrect

        correct_actions = int(sum(bool(x) for x in evals))
        total_actions_task = int(len(evals))
        precision = (correct_actions / total_actions_task) if total_actions_task > 0 else 0.0
        # Task achieved: reached correct end state (end_correctly True)
        task_achieved = end_correctly
        # Task completed: last action correct AND end_correctly True (no excess steps)
        task_completed = (bool(evals[-1]) if evals else False) and end_correctly
        # Exact match: all actions correct AND end_correctly True
        all_correct = (all(evals) if evals else False) and end_correctly
        # Not done but end: last action correct but task not completed (has excess steps)
        not_done_but_end = (bool(evals[-1]) if evals else False) and not task_completed
        pref = prefix_complete(evals)

        total_correct_actions += correct_actions
        total_actions += total_actions_task
        total_exact_match += 1 if all_correct else 0
        total_tasks_completed += 1 if task_completed else 0
        total_tasks_achieved += 1 if task_achieved else 0
        total_not_done_but_end += 1 if not_done_but_end else 0

        results.append({
            'task_name': task_name,
            'gt_actions': len(gt_actions),
            'candidate_actions': len(candidate_actions),
            'correct_actions': correct_actions,
            'total_actions': total_actions_task,
            'precision': precision,
            'all_correct': all_correct,
            'task_completed': task_completed,
            'task_achieved': task_achieved,
            'not_done_but_end': not_done_but_end,
            'end_correctly': end_correctly,
            'prefix_complete': pref,
        })

    results_df = pd.DataFrame(results).sort_values('task_name')

    total_tasks = len(results_df)
    metrics = {
        'total_tasks': total_tasks,
        'total_exact_match_tasks': total_exact_match,
        'exact_match_percentage': (total_exact_match / total_tasks) if total_tasks else 0.0,
        'average_prefix_match': results_df['prefix_complete'].mean() if total_tasks else 0.0,
        'total_correct_actions': int(total_correct_actions),
        'total_actions': int(total_actions),
        'macro_average_precision': results_df['precision'].mean() if total_tasks else 0.0,
        'micro_average_precision': (total_correct_actions / total_actions) if total_actions else 0.0,
        'task_achieved': int(total_tasks_achieved),
        'total_tasks_completed': int(total_tasks_completed),
        'task_completion_percentage': (total_tasks_completed / total_tasks) if total_tasks else 0.0,
        'task_not_done_but_end': int(total_not_done_but_end),
    }

    out_dir = os.path.join("summary")
    os.makedirs(out_dir, exist_ok=True)
    results_df.to_csv(os.path.join(out_dir, f"{METHOD}_evals_mobile_agent_bench.csv"), index=False)
    with open(os.path.join(out_dir, f"{METHOD}_result_mobile_agent_bench.json"), 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=4, ensure_ascii=False)

    print("Saved:")
    print(f"- {os.path.join(out_dir, f'{METHOD}_evals_mobile_agent_bench.csv')}")
    print(f"- {os.path.join(out_dir, f'{METHOD}_result_mobile_agent_bench.json')}")


if __name__ == "__main__":
    analyze("benchmark_report_gt.csv")


