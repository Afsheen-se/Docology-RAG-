#!/usr/bin/env python3
"""
Docology Frontend Runner
Run this script to start the Vite development server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Change to frontend directory
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    # Check if node_modules exists
    if not Path("node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], check=True)
    
    # Start the development server
    print("Starting Docology frontend development server...")
    print("Frontend will be available at: http://localhost:5173")
    print("Press Ctrl+C to stop the server")
    
    subprocess.run(["npm", "run", "dev"])

if __name__ == "__main__":
    main()
