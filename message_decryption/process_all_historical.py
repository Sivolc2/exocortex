#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Import the UltrahumanExporter
from ultrahuman_exporter import UltrahumanExporter

def main():
    # Get user email from environment variable
    email = os.getenv('ULTRAHUMAN_EMAIL')
    if not email or email == 'your_email@example.com':
        print("Error: Please set ULTRAHUMAN_EMAIL in .env file to your actual email address")
        sys.exit(1)
    
    print(f"Processing all historical data for user: {email}")
    
    exporter = UltrahumanExporter()
    
    # Fetch all available historical data (2 years)
    print("Fetching all available historical data (past 2 years)...")
    data = exporter.get_all_historical_data(email)
    
    if data:
        # Create comprehensive filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_id = email.split('@')[0]
        filename = f"ultrahuman_complete_history_{user_id}_{timestamp}.json"
        exporter.export_to_json(data, filename)
        print(f"Successfully exported {len(data)} days of historical data to {filename}")
        
        # Summary of data collected
        total_metrics = 0
        for day_data in data:
            if 'data' in day_data and 'metric_data' in day_data['data']:
                total_metrics += len(day_data['data']['metric_data'])
        
        print(f"Total metrics collected: {total_metrics}")
        print("Biometric types included: heart rate, temperature, HRV, steps, resting HR, sleep, recovery index, movement index, active minutes, VO2 max")
        
    else:
        print("Failed to fetch historical data from Ultrahuman API")
        sys.exit(1)

if __name__ == "__main__":
    main()