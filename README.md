# Health Monitoring System (HMS)

## Overview

The Health Monitoring System (HMS) is a comprehensive platform designed to monitor and analyze health data from wearable devices. It leverages machine learning to provide insights into user health metrics, including activity levels, sleep patterns, and heart rate.

## Features

- **BLE Integration**: Connects with wearable devices via Bluetooth Low Energy (BLE).
- **Data Collection**: Collects health data from wearable devices.
- **Data Preprocessing**: Preprocesses raw health data for analysis.
- **Machine Learning**: Trains and uses machine learning models to predict health trends.
- **Web Interface**: Provides a user-friendly web interface for data visualization and interaction.

## Project Structure

- `api/`: Contains API endpoints for authentication, predictions, and wearable device management.
- `ble/`: Handles BLE communication with wearable devices.
- `collector/`: Manages data collection from wearable devices.
- `data/`: Stores raw and processed health data.
- `database/`: Manages database operations and models.
- `frontend/`: Contains the web interface files.
- `model_training/`: Includes scripts for data preprocessing and model training.
- `main.py`: The main entry point for the application.

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/hms.git
   cd hms
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the root directory and add the following variables:
   ```
   SECRET_KEY=your-secret-key-here
   FLASK_DEBUG=true
   PORT=5000
   ```

4. **Run the Application**:
   ```bash
   python main.py
   ```

5. **Access the Web Interface**:
   Open your browser and navigate to `http://localhost:5000`.

## API Endpoints

- **Authentication**:
  - `POST /api/auth/login`: User login.
  - `POST /api/auth/signup`: User registration.

- **Predictions**:
  - `POST /api/predict`: Get health predictions.

- **Wearable Devices**:
  - `GET /api/wearable/status`: Get status of connected wearable devices.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
