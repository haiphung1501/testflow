import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd

# Configuration
GT_FILE = "benchmark_report_gt.csv"
CANDIDATE_FILE = "benchmark_report_guardian.csv"
METHOD_NAME = "guardian"
EVAL_DIR = os.path.join("evals", f"evals-{METHOD_NAME}")


def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def parse_actions_cell(cell: str) -> list:
    if pd.isna(cell) or cell is None:
        return []
    # Normalize newlines and split
    text = str(cell).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    return text.split("\n")


class EvaluationApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("Mobile Agent Bench - Action Evaluation (GT vs Candidate)")
        try:
            master.state('zoomed')  # Windows
        except Exception:
            master.attributes('-zoomed', True)

        ensure_dir(EVAL_DIR)

        # Load data
        self.df = self._load_and_merge()
        if len(self.df) == 0:
            messagebox.showwarning("No tasks", "No overlapping tasks found between GT and Candidate by task_name.")

        # UI state
        self.current_index = 0
        self.candidate_entries = []

        # Build UI
        self._build_ui()
        self.update_display()

    def _load_and_merge(self) -> pd.DataFrame:
        # Read CSVs
        gt_df = pd.read_csv(GT_FILE, encoding='utf-8', engine='python')
        cand_df = pd.read_csv(CANDIDATE_FILE, encoding='utf-8', engine='python')

        # Normalize columns needed
        gt_required = ["app", "task_name", "actions", "prompt"]
        cand_required = ["app", "task_name", "actions"]
        for col in gt_required:
            if col not in gt_df.columns:
                raise ValueError(f"Missing column '{col}' in groundtruth CSV")
        for col in cand_required:
            if col not in cand_df.columns:
                raise ValueError(f"Missing column '{col}' in candidate CSV")

        # Merge on task_name (unique)
        merged = pd.merge(
            gt_df[["app", "task_name", "prompt", "actions"]].rename(columns={"actions": "gt_actions"}),
            cand_df[["app", "task_name", "actions"]].rename(columns={"actions": f"{METHOD_NAME}_actions"}),
            on="task_name",
            suffixes=("_gt", f"_{METHOD_NAME}")
        )

        # Prefer the GT app label if mismatch
        merged["app"] = merged["app_gt"]
        merged.drop(columns=["app_gt", f"app_{METHOD_NAME}"], inplace=True)

        # Add an evaluated flag based on presence of saved file
        def _has_eval(row):
            path = os.path.join(EVAL_DIR, f"{row['task_name']}.json")
            return os.path.exists(path)

        merged["evaluated"] = merged.apply(_has_eval, axis=1)
        return merged

    def _build_ui(self) -> None:
        # Canvas + frame + scrollbar
        self.canvas = tk.Canvas(self.master)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")

        scrollbar = ttk.Scrollbar(self.master, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=scrollbar.set)

        # Top bar with file info and navigation
        self.title_label = tk.Label(self.frame, text="", font=("Arial", 16), anchor="center", fg="blue", wraplength=900)
        self.title_label.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        self.prompt_label = tk.Label(self.frame, text="", font=("Arial", 12), anchor="w", wraplength=900, fg="#333333")
        self.prompt_label.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

        self.progress_label = tk.Label(self.frame, text="", font=("Arial", 12), anchor="center")
        self.progress_label.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

        self.prev_button = tk.Button(self.frame, text="Previous", command=self.show_previous)
        self.prev_button.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.next_button = tk.Button(self.frame, text="Next", command=self.show_next)
        self.next_button.grid(row=3, column=2, padx=10, pady=5, sticky="e")

        # Headers
        gt_header = tk.Label(self.frame, text="Ground Truth Actions", font=("Arial", 14), anchor="w")
        gt_header.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        cand_header = tk.Label(self.frame, text=f"Candidate Actions ({METHOD_NAME})", font=("Arial", 14), anchor="w")
        cand_header.grid(row=4, column=1, padx=10, pady=10, sticky="w")
        input_header = tk.Label(self.frame, text="Eval (t/f)", font=("Arial", 14), anchor="w")
        input_header.grid(row=4, column=2, padx=10, pady=10, sticky="w")

        self.body_start_row = 5

        self.frame.bind("<Configure>", lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all")))

        # Global keyboard navigation: Left/Right to switch tasks
        self.master.bind_all("<Right>", lambda e: self.show_next())
        self.master.bind_all("<Left>", lambda e: self.show_previous())

    def show_previous(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()

    def show_next(self) -> None:
        if not self.save_results():
            return
        if self.current_index < len(self.df) - 1:
            self.current_index += 1
            self.update_display()
        else:
            messagebox.showinfo("End", "Reached the last task.")

    def clear_body(self) -> None:
        for widget in self.frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) >= self.body_start_row:
                widget.destroy()

    def load_results(self, task_name: str):
        path = os.path.join(EVAL_DIR, f"{task_name}.json")
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data
            except Exception:
                return None

    def save_results(self) -> bool:
        if len(self.candidate_entries) == 0:
            return True
        row = self.df.iloc[self.current_index]
        app = row['app']
        task_name = row['task_name']
        cand_actions = parse_actions_cell(row[f"{METHOD_NAME}_actions"]) or []
        prompt = str(row.get('prompt', '') or '')

        results = {
            'app': app,
            'task_name': task_name,
            'actions': cand_actions,
            'evals': [],
            'end_correctly': False,
        }

        # Read entries
        for entry in self.candidate_entries:
            value = entry.get().strip().lower()
            if value not in ("t", "f"):
                entry.delete(0, tk.END)
                entry.focus()
                return False
            results['evals'].append(True if value == 't' else False)

        # Read end_correctly entry if present
        end_val = self.end_entry.get().strip().lower() if hasattr(self, 'end_entry') else ''
        if end_val in ("t", "f"):
            results['end_correctly'] = True if end_val == 't' else False

        ensure_dir(EVAL_DIR)
        out_path = os.path.join(EVAL_DIR, f"{task_name}.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        return True

    def update_display(self) -> None:
        self.clear_body()
        if len(self.df) == 0:
            return
        row = self.df.iloc[self.current_index]

        app = row['app']
        task_name = row['task_name']
        prompt = row['prompt']
        gt_actions = parse_actions_cell(row['gt_actions'])
        cand_actions = parse_actions_cell(row[f"{METHOD_NAME}_actions"]) or []

        self.title_label.config(text=f"{app} - {task_name}")
        self.prompt_label.config(text=f"Prompt: {prompt}")
        self.progress_label.config(text=f"Progress: {self.current_index + 1}/{len(self.df)}")

        # Pad both lists to the same length for display
        max_len = max(len(gt_actions), len(cand_actions))
        gt_actions += [""] * (max_len - len(gt_actions))
        cand_actions += [""] * (max_len - len(cand_actions))

        # Load existing evals if any
        self.candidate_entries = []
        existing = self.load_results(task_name)
        existing_evals = existing.get('evals') if isinstance(existing, dict) else None
        existing_end = existing.get('end_correctly') if isinstance(existing, dict) else None

        for i, (gt, cand) in enumerate(zip(gt_actions, cand_actions)):
            gt_label = tk.Label(self.frame, text=gt, anchor="w", wraplength=600, font=("Arial", 12))
            gt_label.grid(row=self.body_start_row + i, column=0, padx=10, pady=3, sticky="w")

            cand_label = tk.Label(self.frame, text=cand, anchor="w", wraplength=600, font=("Arial", 12))
            cand_label.grid(row=self.body_start_row + i, column=1, padx=10, pady=3, sticky="w")

            entry = tk.Entry(self.frame, width=5)
            entry.grid(row=self.body_start_row + i, column=2, padx=10, pady=3, sticky="w")

            if existing_evals is not None and i < len(existing_evals):
                entry.delete(0, tk.END)
                entry.insert(0, 't' if existing_evals[i] else 'f')
            # Bind keyboard navigation for entries: Up/Down move between actions, Right/Left switch tasks
            entry.bind("<Down>", self._focus_next_entry)
            entry.bind("<Up>", self._focus_prev_entry)
            entry.bind("<Return>", self._focus_next_entry)
            self.candidate_entries.append(entry)

        if self.candidate_entries:
            self.candidate_entries[0].focus()

        # End correctly input row
        end_row = self.body_start_row + len(gt_actions) + 1
        end_label = tk.Label(self.frame, text="End correctly (t/f):", font=("Arial", 12), anchor="w")
        end_label.grid(row=end_row, column=1, padx=10, pady=8, sticky="e")
        self.end_entry = tk.Entry(self.frame, width=5)
        self.end_entry.grid(row=end_row, column=2, padx=10, pady=8, sticky="w")
        if isinstance(existing_end, bool):
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, 't' if existing_end else 'f')
        # Allow Up/Down to move focus, Right to save/next, Left to previous
        self.end_entry.bind("<Down>", self._focus_next_entry)
        self.end_entry.bind("<Up>", self._focus_prev_entry)
        self.end_entry.bind("<Return>", lambda e: self.show_next())

    def _focus_next_entry(self, event=None):
        try:
            idx = self.candidate_entries.index(event.widget)
        except Exception:
            idx = -1
        target = min(len(self.candidate_entries) - 1, idx + 1)
        if target >= 0 and self.candidate_entries:
            self.candidate_entries[target].focus()
            self.candidate_entries[target].selection_range(0, tk.END)
        return "break"

    def _focus_prev_entry(self, event=None):
        try:
            idx = self.candidate_entries.index(event.widget)
        except Exception:
            idx = 0
        target = max(0, idx - 1)
        if self.candidate_entries:
            self.candidate_entries[target].focus()
            self.candidate_entries[target].selection_range(0, tk.END)
        return "break"


if __name__ == "__main__":
    root = tk.Tk()
    app = EvaluationApp(root)
    root.mainloop()


