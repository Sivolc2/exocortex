# Automated Data Fetching Scheduler

This directory contains the logic for the automated data fetching scheduler, which periodically syncs data from configured sources.

## How It Works

The scheduler is built using the `APScheduler` library and runs as a persistent background process.

1.  **`main.py`**: This is the entry point for the scheduler. It reads the project's `config.yaml`, initializes the scheduler, and adds a job for each enabled data source that has a `schedule` configuration.
2.  **Configuration**: The schedule for each data source is defined in `config.yaml` under the `schedule.frequency` key. This can be a simple interval (`hourly`, `daily`, `weekly`) or a standard cron expression for more complex schedules.
3.  **Jobs**: Each scheduled job calls the `run_source_fetch_pipeline` from `repo_src/backend/pipelines/data_processing.py`. This ensures that both manual runs (via `pnpm data:combine`) and scheduled runs use the exact same logic for fetching, processing, and saving data.

## Usage

To run the scheduler, use the following command from the project root:

```bash
pnpm dev:scheduler
```

This will start the scheduler in your terminal. You should see output indicating that the scheduler has started and which jobs have been scheduled. It's recommended to run this in a separate terminal or using a process manager like `tmux` for long-running applications.

## Configuring Schedules

You can easily change how often data is fetched by editing `config.yaml`.

**Example Configurations:**

```yaml
data_sources:
  discord:
    enabled: true
    # ... other settings
    schedule:
      frequency: "hourly" # Fetch every hour

  notion:
    enabled: true
    # ... other settings
    schedule:
      frequency: "0 4 * * *" # Fetch every day at 4 AM (UTC)
```