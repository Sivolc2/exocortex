import sys
import time
from pathlib import Path
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Setup Paths ---
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

from repo_src.backend.pipelines.data_processing import run_source_fetch_pipeline

def load_config():
    """Loads the main YAML configuration file."""
    print(f"Scheduler: Loading configuration from {CONFIG_PATH}...")
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    if "data_sources" not in config:
        raise ValueError("Configuration file must contain a 'data_sources' key.")
    return config

def schedule_jobs(scheduler, config):
    """Adds jobs to the scheduler based on the configuration."""
    data_sources_config = config.get("data_sources", {})
    sync_options = config.get("sync_options", {})

    print("Scheduler: Setting up jobs...")
    
    for source_name, source_config in data_sources_config.items():
        if source_config.get("enabled"):
            schedule_info = source_config.get("schedule")
            if schedule_info and "frequency" in schedule_info:
                freq = schedule_info["frequency"]
                trigger = None

                # Map simple frequencies to cron triggers for predictability
                if freq == "hourly":
                    trigger = CronTrigger(minute=0)
                elif freq == "daily":
                    trigger = CronTrigger(hour=2, minute=0) # 2 AM UTC
                elif freq == "weekly":
                    trigger = CronTrigger(day_of_week='sun', hour=2, minute=0) # 2 AM UTC on Sunday
                else:
                    # Assume it's a cron string
                    try:
                        trigger = CronTrigger.from_crontab(freq)
                    except ValueError:
                        print(f"WARNING: Invalid cron string for {source_name}: '{freq}'. Skipping job.")
                        continue
                
                if trigger:
                    scheduler.add_job(
                        run_source_fetch_pipeline,
                        trigger=trigger,
                        args=[source_name, sync_options],
                        id=f"job_{source_name}",
                        name=f"Fetch {source_name.title()}",
                        replace_existing=True
                    )
                    print(f"  - Scheduled '{source_name}' with frequency: {freq}")
            else:
                print(f"  - Skipping '{source_name}': no schedule configured.")
        else:
            print(f"  - Skipping '{source_name}': disabled in config.")

def main():
    """Initializes and starts the scheduler."""
    print("--- Starting Automated Data Fetching Scheduler ---")
    config = load_config()
    scheduler = BlockingScheduler(timezone="UTC")
    schedule_jobs(scheduler, config)

    print("\nScheduler started. Current jobs:")
    scheduler.print_jobs()
    print("\nPress Ctrl+C to exit.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")

if __name__ == "__main__":
    main()