import pandas as pd
import os
import sys

# Add the project root to Python path
sys.path.append('.')

from model_training.preprocess import HealthDataPreprocessor

def test_data_loading():
    """Test loading and basic analysis of the Fitbit dataset"""
    
    # Initialize preprocessor
    preprocessor = HealthDataPreprocessor()
    
    print("=" * 50)
    print("FITBIT DATA LOADING TEST")
    print("=" * 50)
    
    # Load data
    print("\n1. Loading raw data...")
    raw_data = preprocessor.load_fitbit_data()
    
    if raw_data is None:
        print(" Failed to load data. Check if files are in data/raw/ folder")
        return False
    
    print(" Data loaded successfully!")
    
    # Analyze heart rate data
    print("\n2. Analyzing Heart Rate Data...")
    if raw_data['heart_rate'] is not None:
        hr_df = raw_data['heart_rate']
        print(f"   - Records: {len(hr_df):,}")
        print(f"   - Users: {hr_df['Id'].nunique()}")
        print(f"   - Date range: {hr_df['Time'].min()} to {hr_df['Time'].max()}")
        print(f"   - Heart rate range: {hr_df['Value'].min()} - {hr_df['Value'].max()} BPM")
        print(f"   - Columns: {list(hr_df.columns)}")
    else:
        print("    No heart rate data found")
    
    # Analyze daily activity data
    print("\n3. Analyzing Daily Activity Data...")
    if raw_data['daily_activity'] is not None:
        activity_df = raw_data['daily_activity']
        print(f"   - Records: {len(activity_df):,}")
        print(f"   - Users: {activity_df['Id'].nunique()}")
        print(f"   - Date range: {activity_df['ActivityDate'].min()} to {activity_df['ActivityDate'].max()}")
        print(f"   - Steps range: {activity_df['TotalSteps'].min()} - {activity_df['TotalSteps'].max()}")
        print(f"   - Columns: {list(activity_df.columns)}")
    else:
        print("    No daily activity data found")
    
    # Analyze sleep data
    print("\n4. Analyzing Sleep Data...")
    if raw_data['sleep'] is not None:
        sleep_df = raw_data['sleep']
        print(f"   - Records: {len(sleep_df):,}")
        print(f"   - Users: {sleep_df['Id'].nunique()}")
        print(f"   - Columns: {list(sleep_df.columns)}")
        print(f"   - Sample values: {sleep_df['value'].value_counts().head()}")
    else:
        print("    No sleep data found")
    
    # Test cleaning functions
    print("\n5. Testing Data Cleaning...")
    
    # Clean heart rate data
    if raw_data['heart_rate'] is not None:
        hr_clean = preprocessor.clean_heart_rate_data(raw_data['heart_rate'])
        if hr_clean is not None:
            print(f"    Heart rate cleaned: {len(hr_clean):,} records")
        else:
            print("    Heart rate cleaning failed")
    
    # Clean activity data
    if raw_data['daily_activity'] is not None:
        activity_clean = preprocessor.clean_daily_activity_data(raw_data['daily_activity'])
        if activity_clean is not None:
            print(f"    Activity data cleaned: {len(activity_clean):,} records")
        else:
            print("    Activity cleaning failed")
    
    # Clean sleep data
    if raw_data['sleep'] is not None:
        sleep_clean = preprocessor.clean_sleep_data(raw_data['sleep'])
        if sleep_clean is not None:
            print(f"    Sleep data cleaned: {len(sleep_clean):,} records")
        else:
            print("    Sleep cleaning failed")
    
    print("\n6. Sample Data Preview...")
    
    # Show sample heart rate data
    if raw_data['heart_rate'] is not None:
        print("\n   Heart Rate Sample:")
        print(raw_data['heart_rate'].head(3))
    
    # Show sample activity data
    if raw_data['daily_activity'] is not None:
        print("\n   Daily Activity Sample:")
        print(raw_data['daily_activity'].head(3))
    
    print("\n" + "=" * 50)
    print("Data loading test completed successfully!")
    print("=" * 50)
    
    return True

def check_file_structure():
    """Check if all required files exist"""
    print("Checking file structure...")
    
    required_files = [
        'data/raw/heartrate_seconds_merged.csv',
        'data/raw/dailyActivity_merged.csv',
        'data/raw/minuteSleep_merged.csv'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
            print(f" Missing: {file}")
        else:
            print(f" Found: {file}")
    
    if missing_files:
        print(f"\n  Missing {len(missing_files)} files. Please download the Fitbit dataset.")
        return False
    
    print("\n All required files found!")
    return True

if __name__ == "__main__":
    print("FITBIT DATASET VERIFICATION")
    print("=" * 50)
    
    # Check file structure first
    if not check_file_structure():
        print("\nPlease download the Fitbit dataset and place the CSV files in data/raw/ folder")
        sys.exit(1)
    
    # Test data loading
    if test_data_loading():
        print("\nReady for next step: Run the full preprocessing pipeline!")
        print("Command: python model_training/preprocess.py")
    else:
        print("\nSome issues found. Please check the error messages above.")