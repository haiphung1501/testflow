import pandas as pd
import os
import json

def calculate_test_gen_success_percentages(csv_file_path, eval_dir="evals/evals-testflow"):
    """
    Calculate the percentage of successful test script generation with three metrics:
    1. exact-match (x/76 tasks) - tasks with test_gen_success = 1 AND all actions correct AND end correctly
    2. all task (on total 100 tasks) - tasks with test_gen_success = 1 out of total tasks
    3. completion task (x/77 tasks) - tasks with test_gen_success = 1 AND last action correct AND end correctly
    """
    
    # Read the CSV file
    df = pd.read_csv(csv_file_path, encoding='utf-8', engine='python')
    
    # Remove header row if it exists and count actual tasks
    total_tasks = len(df)
    
    # Count successful test generation (test_gen_success = 1)
    successful_test_gen_tasks = len(df[df['test_gen_success'] == 1])
    
    # Count failed test generation (test_gen_success = 0)
    failed_test_gen_tasks = len(df[df['test_gen_success'] == 0])
    
    # Count tasks with no test_gen_success value (empty or NaN)
    no_value_tasks = total_tasks - successful_test_gen_tasks - failed_test_gen_tasks
    
    print("=" * 60)
    print("TEST SCRIPT GENERATION SUCCESS ANALYSIS")
    print("=" * 60)
    print(f"Total tasks in dataset: {total_tasks}")
    print(f"Successful test generation: {successful_test_gen_tasks}")
    print(f"Failed test generation: {failed_test_gen_tasks}")
    print(f"No test_gen_success value: {no_value_tasks}")
    print()
    
    # Now analyze the evaluation files for the successful test generation tasks
    print("ANALYZING EVALUATION FILES FOR SUCCESSFUL TEST GENERATION TASKS...")
    print("-" * 60)
    
    exact_match_count = 0
    completion_count = 0
    task_achieved_count = 0
    total_evaluated = 0
    
    # Get list of tasks with successful test generation
    successful_tasks = df[df['test_gen_success'] == 1]['task_name'].tolist()
    
    print(f"Tasks with successful test generation: {len(successful_tasks)}")
    print(f"Evaluation directory: {eval_dir}")
    
    # Check if evaluation directory exists
    if not os.path.exists(eval_dir):
        print(f"Warning: Evaluation directory {eval_dir} not found!")
        print("Cannot calculate exact-match and completion metrics without evaluation files.")
        return
    
    # Analyze each successful task's evaluation file
    for task_name in successful_tasks:
        eval_file_path = os.path.join(eval_dir, f"{task_name}.json")
        
        if os.path.exists(eval_file_path):
            try:
                with open(eval_file_path, 'r', encoding='utf-8') as f:
                    eval_data = json.load(f)
                
                evals = eval_data.get('evals', [])
                end_correctly = eval_data.get('end_correctly', False)
                
                # Calculate metrics based on analyze_eval_result.py logic
                # Task achieved: reached correct end state (end_correctly True)
                task_achieved = end_correctly
                
                # Task completed: last action correct AND end_correctly True (no excess steps)
                task_completed = (bool(evals[-1]) if evals else False) and end_correctly
                
                # Exact match: all actions correct AND end_correctly True
                all_correct = (all(evals) if evals else False) and end_correctly
                
                if task_achieved:
                    task_achieved_count += 1
                if task_completed:
                    completion_count += 1
                if all_correct:
                    exact_match_count += 1
                
                total_evaluated += 1
                
            except Exception as e:
                print(f"Error reading evaluation file for {task_name}: {e}")
        else:
            print(f"Warning: No evaluation file found for {task_name}")
    
    print(f"Total tasks evaluated: {total_evaluated}")
    print(f"Tasks that achieved correct end state: {task_achieved_count}")
    print(f"Tasks completed correctly: {completion_count}")
    print(f"Tasks with exact match: {exact_match_count}")
    print()
    
    # Calculate percentages for the three metrics
    # 1. exact-match (x/76 tasks) - from evaluation files
    exact_match_percentage = (exact_match_count / 76) * 100
    
    # 2. all task (x/100 tasks) - from test_gen_success column
    all_task_percentage = (successful_test_gen_tasks / 100) * 100
    
    # 3. completion task (x/77 tasks) - from evaluation files
    completion_task_percentage = (completion_count / 77) * 100
    
    # Also calculate percentage based on actual total tasks
    actual_total_percentage = (successful_test_gen_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    print("PERCENTAGE METRICS:")
    print("-" * 30)
    print(f"1. Exact-match (x/76 tasks): {exact_match_count}/76 = {exact_match_percentage:.2f}%")
    print(f"   (Based on evaluation files: all actions correct AND end correctly)")
    print(f"2. All task (x/100 tasks): {successful_test_gen_tasks}/100 = {all_task_percentage:.2f}%")
    print(f"   (Based on test_gen_success column: test script generated successfully)")
    print(f"3. Completion task (x/77 tasks): {completion_count}/77 = {completion_task_percentage:.2f}%")
    print(f"   (Based on evaluation files: last action correct AND end correctly)")
    print(f"4. Actual total percentage: {successful_test_gen_tasks}/{total_tasks} = {actual_total_percentage:.2f}%")
    print()
    
    # Detailed breakdown by app
    print("BREAKDOWN BY APP:")
    print("-" * 30)
    app_breakdown = df.groupby('app')['test_gen_success'].apply(lambda x: (x == 1).sum()).reset_index()
    app_breakdown.columns = ['App', 'Successful_Tasks']
    app_breakdown['Total_Tasks'] = df.groupby('app').size().values
    app_breakdown['Success_Rate'] = (app_breakdown['Successful_Tasks'] / app_breakdown['Total_Tasks'] * 100).round(2)
    
    for _, row in app_breakdown.iterrows():
        print(f"{row['App']:15}: {row['Successful_Tasks']:2}/{row['Total_Tasks']:2} = {row['Success_Rate']:5.2f}%")
    
    print()
    
    # Save detailed results to CSV
    output_file = "test_gen_success_analysis.csv"
    detailed_results = df[['app', 'task_name', 'test_gen_success', 'success']].copy()
    detailed_results['test_gen_success'] = detailed_results['test_gen_success'].fillna('No Value')
    detailed_results.to_csv(output_file, index=False)
    print(f"Detailed results saved to: {output_file}")
    
    # Save summary to JSON
    summary = {
        'total_tasks': total_tasks,
        'successful_test_gen_tasks': successful_test_gen_tasks,
        'failed_test_gen_tasks': failed_test_gen_tasks,
        'no_value_tasks': no_value_tasks,
        'evaluation_analysis': {
            'total_evaluated': total_evaluated,
            'task_achieved': task_achieved_count,
            'task_completed': completion_count,
            'exact_match': exact_match_count
        },
        'metrics': {
            'exact_match_76': {
                'count': exact_match_count,
                'total': 76,
                'percentage': round(exact_match_percentage, 2),
                'description': 'Based on evaluation files: all actions correct AND end correctly'
            },
            'all_task_100': {
                'count': successful_test_gen_tasks,
                'total': 100,
                'percentage': round(all_task_percentage, 2),
                'description': 'Based on test_gen_success column: test script generated successfully'
            },
            'completion_task_77': {
                'count': completion_count,
                'total': 77,
                'percentage': round(completion_task_percentage, 2),
                'description': 'Based on evaluation files: last action correct AND end correctly'
            },
            'actual_total': {
                'count': successful_test_gen_tasks,
                'total': total_tasks,
                'percentage': round(actual_total_percentage, 2)
            }
        },
        'app_breakdown': app_breakdown.to_dict('records')
    }
    
    summary_file = "test_gen_success_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Summary saved to: {summary_file}")
    
    return summary

if __name__ == "__main__":
    # Default file path
    csv_file = "benchmark_report_testflow.csv"
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found!")
        print("Please make sure the CSV file is in the same directory as this script.")
        exit(1)
    
    # Calculate and display results
    results = calculate_test_gen_success_percentages(csv_file)
