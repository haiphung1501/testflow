import os
import pandas as pd
import re


def load_csv_safely(path: str) -> pd.DataFrame:
    """Read a CSV with pandas, handling delimiter autodetection, BOMs, and extra columns.

    - Auto-detect delimiter using engine='python' sep=None
    - Drop unnamed/empty columns
    - Normalize column names: strip, lowercase, replace spaces/hyphens with underscores
    """
    df = pd.read_csv(path, encoding="utf-8", engine="python", sep=None)
    # Drop unnamed placeholder columns that sometimes appear when saving CSVs from Excel
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", case=False)]
    # Normalize column names
    def _normalize(name: str) -> str:
        return name.strip().lower().replace(" ", "_").replace("-", "_")

    df.columns = [_normalize(c) for c in df.columns]
    return df


def find_best_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the existing column name in df that best matches any of candidates.

    Comparison is done on normalized names (lowercase, underscores, stripped).
    """
    normalized_cols = {c.strip().lower().replace(" ", "_").replace("-", "_"): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower().replace(" ", "_").replace("-", "_")
        if key in normalized_cols:
            return normalized_cols[key]
    return None


def guess_column_by_substring(df: pd.DataFrame, include_terms: list[str]) -> str | None:
    """Heuristically choose a column whose normalized name contains any include_terms."""
    cols = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    for idx, col in enumerate(cols):
        for term in include_terms:
            if term in col:
                return df.columns[idx]
    return None


def main() -> None:
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "all_tasks.csv")
    droidtask_path = os.path.join(base_dir, "droidtask.csv")

    # Load inputs
    all_tasks_csv = load_csv_safely(csv_path)
    droidtask_csv = load_csv_safely(droidtask_path)

    # Resolve canonical column names from both sources
    app_col = (
        find_best_column(all_tasks_csv, ["app_name", "app", "app id", "app-title"]) or
        guess_column_by_substring(all_tasks_csv, ["app"]) or
        (all_tasks_csv.columns[0] if len(all_tasks_csv.columns) > 0 else None)
    )
    task_col = (
        find_best_column(all_tasks_csv, ["task_desc", "task", "task_description"]) or
        guess_column_by_substring(all_tasks_csv, ["task", "desc", "instruction", "goal"]) or
        (all_tasks_csv.columns[1] if len(all_tasks_csv.columns) > 1 else None)
    )
    hash_col_csv = (
        find_best_column(all_tasks_csv, ["hash"]) or
        guess_column_by_substring(all_tasks_csv, ["hash"]) or
        None
    )
    actions_col = (
        find_best_column(all_tasks_csv, ["actions", "soa", "steps_text"]) or
        guess_column_by_substring(all_tasks_csv, ["action", "soa", "step_text", "steps_text"])  # may be None
    )
    steps_col = (
        find_best_column(all_tasks_csv, ["agent_steps", "n_actions", "num_steps"]) or
        guess_column_by_substring(all_tasks_csv, ["steps", "n_actions", "num_actions", "num_steps"])  # may be None
    )

    if app_col is None or task_col is None:
        raise ValueError(
            f"Unable to determine app/task columns from CSV headers: {list(all_tasks_csv.columns)}"
        )

    app_col_droid = find_best_column(droidtask_csv, ["app_name", "app"]) or "app_name"
    task_col_droid = find_best_column(droidtask_csv, ["task_desc", "task", "task_description"]) or "task_desc"
    hash_col_droid = find_best_column(droidtask_csv, ["hash"]) or "hash"

    # Keep only the key columns we care about from droidtask for joining
    droidtask_small = droidtask_csv[[app_col_droid, task_col_droid, hash_col_droid]].copy()
    droidtask_small.columns = ["app_name", "task_desc", "hash_from_droidtask"]

    # Build a fast prefix lookup per app for matching task_desc that encodes hash prefixes
    # e.g., task_desc like "applauncher_11a062dc" -> prefix "11a062dc"
    prefix_lookup_by_app: dict[str, dict[str, str]] = {}
    for app, hash_full in droidtask_small[["app_name", "hash_from_droidtask"]].dropna().itertuples(index=False):
        app_map = prefix_lookup_by_app.setdefault(str(app), {})
        h = str(hash_full)
        # generate prefixes of length 6..12
        for L in range(6, 13):
            app_map.setdefault(h[:L], h)

    # Some CSVs may already have hash; prefer hash from droidtask when available
    left = all_tasks_csv[[app_col, task_col]].copy()
    left.columns = ["app_name", "task_desc"]
    left["hash_csv"] = all_tasks_csv[hash_col_csv] if hash_col_csv in all_tasks_csv.columns else None

    merged = left.merge(
        droidtask_small,
        on=["app_name", "task_desc"],
        how="left",
        suffixes=("", "_from_droidtask"),
    )

    # Choose hash from droidtask when present; else fall back to CSV value
    merged["hash_final"] = merged["hash_from_droidtask"].fillna(merged["hash_csv"]).fillna("")

    # If hash is still empty, try to infer from task_desc prefix pattern
    def extract_hash_hint(task_desc_value: str) -> str | None:
        if not isinstance(task_desc_value, str):
            return None
        # common pattern: appname_<hexdigits>
        m = re.search(r"([0-9a-fA-F]{6,64})", task_desc_value)
        if m:
            return m.group(1).lower()
        return None

    need_infer_mask = merged["hash_final"].astype(str).eq("") | merged["hash_final"].isna()
    if need_infer_mask.any():
        hints = merged.loc[need_infer_mask, "task_desc"].map(extract_hash_hint)
        inferred_hashes: list[str] = []
        for (idx, app_name_value), hint in zip(merged.loc[need_infer_mask, ["app_name"]].itertuples(), hints):
            full_hash = ""
            if hint:
                app_map = prefix_lookup_by_app.get(str(app_name_value), {})
                # try descending prefix lengths in case the hint is shorter/longer than generated
                for L in range(min(len(hint), 12), 5, -1):
                    cand = hint[:L]
                    if cand in app_map:
                        full_hash = app_map[cand]
                        break
            inferred_hashes.append(full_hash)
        # assign back
        merged.loc[need_infer_mask, "hash_final"] = inferred_hashes

    # Use task_desc from droidtask when we have a hash match
    droidtask_by_hash = droidtask_csv[[app_col_droid, hash_col_droid, task_col_droid]].copy()
    droidtask_by_hash.columns = ["app_name", "hash_final", "task_desc_from_droidtask"]
    merged = merged.merge(
        droidtask_by_hash,
        on=["app_name", "hash_final"],
        how="left",
    )
    # Prefer canonical task description from droidtask; fallback to existing
    merged["task_desc_final"] = merged["task_desc_from_droidtask"].fillna(merged["task_desc"]) 

    # Map soa and n_actions from all_tasks.csv when available
    soa_series = ""
    n_actions_series = 0

    if actions_col and actions_col in all_tasks_csv.columns:
        actions_map = all_tasks_csv[[app_col, task_col, actions_col]].copy()
        actions_map.columns = ["app_name", "task_desc", "actions"]
        merged = merged.merge(actions_map, on=["app_name", "task_desc"], how="left")
        soa_series = merged["actions"].fillna("")
    else:
        soa_series = ""

    if steps_col and steps_col in all_tasks_csv.columns:
        steps_map = all_tasks_csv[[app_col, task_col, steps_col]].copy()
        steps_map.columns = ["app_name", "task_desc", "agent_steps"]
        merged = merged.merge(steps_map, on=["app_name", "task_desc"], how="left", suffixes=("", "_dup"))
        # Handle potential duplicate columns if both merges occurred
        if "agent_steps_dup" in merged.columns and merged["agent_steps"].isna().all():
            merged["agent_steps"] = merged["agent_steps_dup"]
        n_actions_series = merged["agent_steps"].fillna(0).astype(int)
    else:
        n_actions_series = 0

    # Construct output DataFrame with exact columns and order
    out_df = pd.DataFrame({
        "app_name": merged["app_name"],
        "task_desc": merged["task_desc_final"],
        "hash": merged["hash_final"],
        "n_actions": n_actions_series,
        "soa": soa_series,
    })

    # Sort for deterministic output similar to droidagent example
    out_df = out_df.sort_values(by=["app_name", "task_desc"]).reset_index(drop=True)

    # Write xlsx next to the CSV
    xlsx_path = os.path.join(base_dir, "all_tasks.xlsx")
    out_df.to_excel(xlsx_path, index=False)


if __name__ == "__main__":
    main()


