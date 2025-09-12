import pandas as pd
import json
import os
import ast
import re

def parse_action_eval(action_eval_str):
    """Parse the guardian_action_eval string to get list of boolean values"""
    try:
        # Remove brackets and split by comma
        action_eval_str = action_eval_str.strip()
        if action_eval_str.startswith('[') and action_eval_str.endswith(']'):
            action_eval_str = action_eval_str[1:-1]
        
        # Split by comma and convert to boolean
        eval_list = []
        for item in action_eval_str.split(','):
            item = item.strip().lower()
            if item == 'true':
                eval_list.append(True)
            elif item == 'false':
                eval_list.append(False)
            else:
                print(f"Warning: Unknown eval value: {item}")
                eval_list.append(False)
        return eval_list
    except Exception as e:
        print(f"Error parsing action_eval: {action_eval_str}, Error: {e}")
        return []

def count_groundtruth_actions(groundtruth):
    """Count the number of actions in groundtruth"""
    if pd.isna(groundtruth) or groundtruth == "":
        return 0
    # Count lines that start with "- ACTION"
    lines = groundtruth.strip().split('\n')
    action_count = 0
    for line in lines:
        if line.strip().startswith('- ACTION'):
            action_count += 1
    return action_count

def trim_guardian_actions(guardian_actions, action_evals, groundtruth):
    """
    Trim Guardian actions to match groundtruth length by removing excess steps.
    Returns trimmed actions and corresponding evals.
    """
    if pd.isna(groundtruth) or groundtruth == "":
        return guardian_actions, action_evals
    
    # Count groundtruth actions
    gt_action_count = count_groundtruth_actions(groundtruth)
    
    if gt_action_count == 0:
        return guardian_actions, action_evals
    
    # Split guardian actions into lines
    guardian_lines = guardian_actions.strip().split('\n')
    
    # Filter out non-action lines (like "Task completed?")
    action_lines = []
    for line in guardian_lines:
        if line.strip().startswith('-ACTION') and not 'Task completed?' in line:
            action_lines.append(line)
    
    # Trim to match groundtruth length
    if len(action_lines) > gt_action_count:
        action_lines = action_lines[:gt_action_count]
    
    # Trim action_evals to match
    if len(action_evals) > gt_action_count:
        action_evals = action_evals[:gt_action_count]
    
    return '\n'.join(action_lines), action_evals

def prefix_complete(evals, gt):
    """Calculate prefix completion ratio - count the first consecutive True evaluations"""
    if not evals:
        return 0.0
    
    # Convert evals to list of booleans if it's a string
    if isinstance(evals, str):
        eval_list = [eval.strip().lower() == 'true' for eval in evals.split('\n') if eval.strip()]
    else:
        eval_list = evals
    
    # Count the first consecutive True evaluations
    count = 0
    for eval_val in eval_list:
        if eval_val:
            count += 1
        else:
            break
    
    return count / len(eval_list) if eval_list else 0.0

def calculate_metrics(trimmed_actions, trimmed_evals, groundtruth, is_achieved=False):
    """Calculate metrics for trimmed actions"""
    if not trimmed_actions or not trimmed_evals:
        return {
            'correct_actions': 0,
            'total_actions': 0,
            'precision': 0.0,
            'all_correct': False,
            'task_completed': False,
            'prefix_complete': 0.0
        }
    
    # Count correct actions
    correct_actions = sum(trimmed_evals)
    total_actions = len(trimmed_evals)
    
    # Calculate precision
    precision = correct_actions / total_actions if total_actions > 0 else 0.0
    
    # Check if all actions are correct
    all_correct = all(trimmed_evals) if trimmed_evals else False
    
    # Calculate prefix completion
    prefix_complete_ratio = prefix_complete(trimmed_evals, groundtruth)
    
    # Check if task is completed
    # If task is achieved, then it's completed (since we trimmed to groundtruth length)
    # Otherwise, check if last action is correct
    if is_achieved:
        task_completed = True
    else:
        task_completed = trimmed_evals[-1] if trimmed_evals else False
    
    return {
        'correct_actions': correct_actions,
        'total_actions': total_actions,
        'precision': precision,
        'all_correct': all_correct,
        'task_completed': task_completed,
        'prefix_complete': prefix_complete_ratio
    }

def evaluate_guardian_complete():
    """Main function to evaluate Guardian on all 150 tasks with updated achieved tasks"""
    
    # Read the Guardian data for groundtruth
    print("Reading Guardian data for groundtruth...")
    df = pd.read_csv("guardian_data.csv")
    
    # Read Guardian evaluation files
    eval_folder = "evals/evals-guardian"
    eval_files = os.listdir(eval_folder)
    
    print(f"Found {len(eval_files)} Guardian evaluation files")
    
    # Create a mapping of evaluation data by hash
    eval_data_map = {}
    for file in eval_files:
        with open(os.path.join(eval_folder, file)) as f:
            data = json.load(f)
        hash_val = data['hash']
        eval_data_map[hash_val] = data
    
    # Process all 150 tasks
    results = []
    total_correct_actions = 0
    total_actions = 0
    total_exact_match = 0
    total_task_completed = 0
    total_achieved_tasks = 0
    
    for idx, row in df.iterrows():
        app_name = row['app_name']
        task_desc = row['task_desc']
        hash_val = row['hash']
        groundtruth = row['groundtruth']
        guardian_actions = row['guardian']
        action_eval_str = row['guardian_action_eval']
        
        print(f"\nProcessing: {app_name} - {task_desc}")
        
        # Check if we have evaluation data for this task
        if hash_val in eval_data_map:
            eval_data = eval_data_map[hash_val]
            actions = eval_data['actions']
            evals = eval_data['evals']
            end_correctly = eval_data['end_correctly']
            
            print(f"Found evaluation data - End correctly: {end_correctly}, Last eval: {evals[-1]}")
            
            # Use the same logic as original analyze_eval_result.py
            task_completed = evals[-1]
            last_action_eval = evals[-2] if len(evals) > 1 else False
            
            # Determine if task is achieved
            if task_completed:
                total_achieved_tasks += 1
                print("Task achieved - will trim excess steps")
                
                # Convert actions list to string
                guardian_actions = '\n'.join(actions)
                
                # Count groundtruth actions
                gt_action_count = count_groundtruth_actions(groundtruth)
                print(f"Groundtruth action count: {gt_action_count}")
                print(f"Original action count: {len(evals)}")
                
                # Trim Guardian actions
                trimmed_actions, trimmed_evals = trim_guardian_actions(
                    guardian_actions, evals, groundtruth
                )
                print(f"Trimmed action count: {len(trimmed_evals)}")
                
                # Calculate metrics
                metrics = calculate_metrics(trimmed_actions, trimmed_evals, groundtruth, is_achieved=True)
                
                # Update totals
                total_correct_actions += metrics['correct_actions']
                total_actions += metrics['total_actions']
                if metrics['all_correct']:
                    total_exact_match += 1
                if metrics['task_completed']:
                    total_task_completed += 1
                
                # Store result with trimmed data
                result = {
                    'app_name': app_name,
                    'task_desc': task_desc,
                    'hash': hash_val,
                    'original_actions': len(evals),
                    'groundtruth_actions': gt_action_count,
                    'trimmed_actions': len(trimmed_evals),
                    'correct_actions': metrics['correct_actions'],
                    'total_actions': metrics['total_actions'],
                    'precision': metrics['precision'],
                    'all_correct': metrics['all_correct'],
                    'task_completed': metrics['task_completed'],
                    'prefix_complete': metrics['prefix_complete'],
                    'end_correctly': end_correctly,
                    'last_action_eval': last_action_eval,
                    'is_achieved': True,
                    'guardian_actions': trimmed_actions,
                    'action_evals': trimmed_evals
                }
                
                print(f"Precision: {metrics['precision']:.3f}, All correct: {metrics['all_correct']}, Task completed: {metrics['task_completed']}")
                
            else:
                print("Task not achieved - using original data")
                
                # Parse original action evaluations
                action_evals = parse_action_eval(action_eval_str)
                
                # Count groundtruth actions
                gt_action_count = count_groundtruth_actions(groundtruth)
                
                # Calculate metrics using original data
                correct_actions = sum(action_evals)
                total_actions_count = len(action_evals)
                precision = correct_actions / total_actions_count if total_actions_count > 0 else 0.0
                all_correct = all(action_evals) if action_evals else False
                # Non-achieved tasks should never be considered completed
                task_completed = False
                # Calculate prefix completion
                prefix_complete_ratio = prefix_complete(action_evals, groundtruth)
                
                # Update totals
                total_correct_actions += correct_actions
                total_actions += total_actions_count
                if all_correct:
                    total_exact_match += 1
                if task_completed:
                    total_task_completed += 1
                
                # Store result with original data
                result = {
                    'app_name': app_name,
                    'task_desc': task_desc,
                    'hash': hash_val,
                    'original_actions': len(action_evals),
                    'groundtruth_actions': gt_action_count,
                    'trimmed_actions': len(action_evals),
                    'correct_actions': correct_actions,
                    'total_actions': total_actions_count,
                    'precision': precision,
                    'all_correct': all_correct,
                    'task_completed': task_completed,
                    'prefix_complete': prefix_complete_ratio,
                    'end_correctly': end_correctly,
                    'last_action_eval': action_evals[-2] if len(action_evals) > 1 else False,
                    'is_achieved': False,
                    'guardian_actions': guardian_actions,
                    'action_evals': action_evals
                }
                
                print(f"Precision: {precision:.3f}, All correct: {all_correct}, Task completed: {task_completed}")
        else:
            print("No evaluation data found - using original data")
            
            # Parse original action evaluations
            action_evals = parse_action_eval(action_eval_str)
            
            # Count groundtruth actions
            gt_action_count = count_groundtruth_actions(groundtruth)
            
            # Calculate metrics using original data
            correct_actions = sum(action_evals)
            total_actions_count = len(action_evals)
            precision = correct_actions / total_actions_count if total_actions_count > 0 else 0.0
            all_correct = all(action_evals) if action_evals else False
            # Non-achieved tasks should never be considered completed
            task_completed = False
            # Calculate prefix completion
            prefix_complete_ratio = prefix_complete(action_evals, groundtruth)
            
            # Update totals
            total_correct_actions += correct_actions
            total_actions += total_actions_count
            if all_correct:
                total_exact_match += 1
            if task_completed:
                total_task_completed += 1
            
            # Store result with original data
            result = {
                'app_name': app_name,
                'task_desc': task_desc,
                'hash': hash_val,
                'original_actions': len(action_evals),
                'groundtruth_actions': gt_action_count,
                'trimmed_actions': len(action_evals),
                'correct_actions': correct_actions,
                'total_actions': total_actions_count,
                'precision': precision,
                'all_correct': all_correct,
                'task_completed': task_completed,
                'prefix_complete': prefix_complete_ratio,
                'end_correctly': False,
                'last_action_eval': action_evals[-2] if len(action_evals) > 1 else False,
                'is_achieved': False,
                'guardian_actions': guardian_actions,
                'action_evals': action_evals
            }
            
            print(f"Precision: {precision:.3f}, All correct: {all_correct}, Task completed: {task_completed}")
        
        results.append(result)
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Calculate overall metrics for all 150 tasks
    total_tasks = 150
    overall_metrics = {
        'total_tasks': total_tasks,
        'total_exact_match_tasks': total_exact_match,
        'exact_match_percentage': total_exact_match / total_tasks if total_tasks > 0 else 0.0,
        'average_prefix_match': results_df['prefix_complete'].mean() if len(results_df) > 0 else 0.0,
        'total_correct_actions': total_correct_actions,
        'total_actions': total_actions,
        'macro_average_precision': results_df['precision'].mean() if len(results_df) > 0 else 0.0,
        'micro_average_precision': total_correct_actions / total_actions if total_actions > 0 else 0.0,
        'total_tasks_completed': total_task_completed,
        'task_completion_percentage': total_task_completed / total_tasks if total_tasks > 0 else 0.0,
        'total_achieved_tasks': total_achieved_tasks,
        'achieved_tasks_percentage': total_achieved_tasks / total_tasks if total_tasks > 0 else 0.0,
    }
    
    # Save results
    results_df.to_csv("guardian_complete_evaluation_results.csv", index=False)
    
    # Save overall metrics
    with open("guardian_complete_evaluation_metrics.json", 'w') as f:
        json.dump(overall_metrics, f, indent=4)
    
    # Print summary
    print(f"\n{'='*50}")
    print("GUARDIAN COMPLETE EVALUATION SUMMARY (150 TASKS)")
    print(f"{'='*50}")
    print(f"Total tasks: {total_tasks}")
    print(f"Total achieved tasks: {total_achieved_tasks} ({overall_metrics['achieved_tasks_percentage']*100:.1f}%)")
    print(f"Exact match tasks: {total_exact_match} ({overall_metrics['exact_match_percentage']*100:.1f}%)")
    print(f"Task completed: {total_task_completed} ({overall_metrics['task_completion_percentage']*100:.1f}%)")
    print(f"Average prefix match: {overall_metrics['average_prefix_match']*100:.1f}%")
    print(f"Total correct actions: {total_correct_actions}")
    print(f"Total actions: {total_actions}")
    print(f"Macro average precision: {overall_metrics['macro_average_precision']*100:.1f}%")
    print(f"Micro average precision: {overall_metrics['micro_average_precision']*100:.1f}%")
    
    return results_df, overall_metrics

if __name__ == "__main__":
    try:
        results_df, metrics = evaluate_guardian_complete()
        print("\n✅ Guardian complete evaluation completed successfully!")
        print("Results saved to:")
        print("- guardian_complete_evaluation_results.csv")
        print("- guardian_complete_evaluation_metrics.json")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
