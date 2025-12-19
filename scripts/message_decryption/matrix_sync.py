#!/usr/bin/env python3

import asyncio
import argparse
from matrix_aggregator.main import MatrixAggregator

async def main():
    parser = argparse.ArgumentParser(description='Matrix Message Aggregator')
    parser.add_argument('config', help='Path to matrix_config.json')
    parser.add_argument('--schedule', action='store_true', help='Run in scheduled mode')
    parser.add_argument('--backfill', type=int, default=500, help='Number of messages to backfill per room')
    
    args = parser.parse_args()
    
    aggregator = MatrixAggregator(args.config)
    await aggregator.initialize()
    
    if args.schedule:
        print("Starting scheduled sync...")
        aggregator.start_scheduler()
    else:
        print("Running one-time sync...")
        exported_files = await aggregator.sync_messages()
        print(f"Sync complete. Exported {len(exported_files)} rooms to {aggregator.config['output_directory']}")
        for file_path in exported_files:
            print(f"  - {file_path}")

if __name__ == "__main__":
    asyncio.run(main())