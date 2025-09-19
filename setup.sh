#!/bin/bash
python3 -m venv keylogger
source keylogger/bin/activate
pip install pynput
pip install Pillow
pip install requests
pip install psutil
echo "Setup complete! Virtual environment activated."
