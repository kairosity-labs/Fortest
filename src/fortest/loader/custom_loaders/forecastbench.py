
import os
import json
import logging
from typing import Dict, Any, List
from fortest.loader.loader import ProblemLoader, base_process_problem
from fortest.scripts.setup_datasets import ensure_forecastbench_data, TARGET_DIR

logger = logging.getLogger(__name__)

@ProblemLoader.register("forecastbench")
def load_forecastbench_dataset(raw_problems: List[Dict], dataset_name: str = None, limit: int = None, **kwargs) -> Dict[str, Any]:
    """
    Loads problems from the ForecastBench dataset.
    
    Args:
        raw_problems: Ignored, as we load from files.
        dataset_name: Name of the dataset to load (e.g., '2019', '2020', etc.). 
                      If None, tries to load all available datasets.
        limit: Max number of problems to return.
    """
    ensure_forecastbench_data()
    
    base_data_path = os.path.join(TARGET_DIR, "datasets")
    question_dir = os.path.join(base_data_path, "question_sets")
    resolution_dir = os.path.join(base_data_path, "resolution_sets")
    
    # Identify datasets to load
    if dataset_name:
        datasets = [dataset_name]
    else:
        # Infer datasets from existing files in question dir
        files = os.listdir(question_dir)
        datasets = [f.replace(".json", "") for f in files if f.endswith(".json")]
    
    all_problems = {}
    

    for ds in datasets:
        q_path = os.path.join(question_dir, f"{ds}.json")
        # The resolution file naming seems to be slightly different, often has "_resolution_set" suffix or similar
        # Based on file listing, it is "{ds}_resolution_set.json" if ds is like "2024-07-21"
        # Since ds came from "2024-07-21-human.json", the resolution file might be "2024-07-21_resolution_set.json"?
        # Actually in the file list I saw "2024-07-21_resolution_set.json".
        # The question file list has "2024-07-21-human.json", "2024-07-21-llm.json".
        # The resolution file has "question_set": "2024-07-21-llm.json" inside.
        # This implies a many-to-one or specific mapping. 
        # For simplicity, we will try to find a resolution file that matches the pattern or just load all into a big dict if feasible, 
        # but let's stick to trying to find the specific one.
        # Given the complexity, let's try a heuristic: check if there's a file with the date prefix in resolution_sets.
        
        # Extract date part if possible.
        date_part = ds.split("-llm")[0].split("-human")[0]
        r_path_candidate = os.path.join(resolution_dir, f"{date_part}_resolution_set.json")
        
        if not os.path.exists(q_path):
            logger.warning(f"Dataset {ds} question file not found at {q_path}")
            continue
            
        try:
            with open(q_path, "r") as f:
                q_data = json.load(f)
                questions = q_data.get("questions", [])
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from {q_path}")
            continue
            
        resolutions = {}
        if os.path.exists(r_path_candidate):
            try:
                with open(r_path_candidate, "r") as f:
                    r_data = json.load(f)
                    # Support both list directly or dict with "resolutions" key
                    r_list = r_data.get("resolutions", []) if isinstance(r_data, dict) else r_data
                    
                    # Create dict for O(1) lookup
                    # Only map string IDs to avoid hashing issues with list IDs (combinations)
                    for r in r_list:
                        if isinstance(r.get("id"), str):
                            resolutions[r["id"]] = r
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode resolution JSON from {r_path_candidate}")
        
        for q in questions:
            pid = str(q.get("id"))
            
            res_data = resolutions.get(pid, {})
            
            # Map fields
            problem = {
                "problem_id": f"fb_{ds}_{pid}",
                "question": q.get("question") or q.get("title"),
                "time_start": q.get("market_info_open_datetime") or q.get("start_date") or q.get("publish_date"),
                "time_end": q.get("market_info_close_datetime") or q.get("end_date") or q.get("close_date"),
                "metadata": {
                    "source": "ForecastBench",
                    "dataset": ds,
                    "original_id": pid,
                    "choices": q.get("choices"), 
                    "background": q.get("background"),
                    "resolution_criteria": q.get("resolution_criteria"),
                    "url": q.get("url")
                }
            }
            
            # Handle resolution
            if res_data and res_data.get("resolved"):
                problem["resolved_flag"] = True
                # 'resolved_to' seems to be the field for outcome (0.0 or 1.0 or value)
                problem["resolution_status"] = res_data.get("resolved_to")
            else:
                problem["resolved_flag"] = False
                problem["resolution_status"] = None

            # Add time_testing from freeze_datetime if available
            time_testing = q.get("freeze_datetime")

            processed = base_process_problem(problem, time_testing=time_testing)
            all_problems[processed["problem_id"]] = processed
            
            if limit and len(all_problems) >= limit:
                break
        
        if limit and len(all_problems) >= limit:
            break
            
    return all_problems
            
    return all_problems
