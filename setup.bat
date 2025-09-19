@echo off
python -m venv keylogger
call keylogger\Scripts\activate
pip install pynput requests Pillow
echo Setup complete! Virtual environment activated.
pause
