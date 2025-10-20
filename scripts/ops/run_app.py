#!/usr/bin/env python3
"""
HeartBeat Engine - Application Launcher
Montreal Canadiens Advanced Analytics Assistant

Launch script for the HeartBeat Streamlit application.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    
    required_packages = [
        'streamlit',
        'plotly', 
        'pandas',
        'boto3',
        'langgraph',
        'vertex'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")
        print("Installing missing dependencies...")
        
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "app/requirements.txt"
        ])

def setup_environment():
    """Set up environment variables and configuration"""
    
    # Set Python path to include project root
    project_root = Path(__file__).parent.absolute()
    os.environ['PYTHONPATH'] = str(project_root)
    
    # Set default environment variables if not already set
    env_defaults = {
        'HEARTBEAT_DEBUG': 'false',
        'HEARTBEAT_LOG_LEVEL': 'INFO'
    }
    
    for key, value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value

def main():
    """Main launcher function"""
    
    print("🏒 HeartBeat Engine - Montreal Canadiens Analytics")
    print("=" * 50)
    
    # Check dependencies
    print("Checking dependencies...")
    check_dependencies()
    
    # Setup environment
    print("Setting up environment...")
    setup_environment()
    
    # Launch Streamlit app
    print("Launching application...")
    print("🚀 Starting HeartBeat Engine web interface...")
    print("📱 Open your browser to the URL shown below")
    print("=" * 50)
    
    # Run Streamlit app
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "app/main.py",
        "--server.port", "8501",
        "--server.address", "localhost",
        "--browser.gatherUsageStats", "false",
        "--theme.primaryColor", "#AF1E2D",
        "--theme.backgroundColor", "#FFFFFF",
        "--theme.secondaryBackgroundColor", "#F0F2F6",
        "--theme.textColor", "#262730"
    ])

if __name__ == "__main__":
    main()
