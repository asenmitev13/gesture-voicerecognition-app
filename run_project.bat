@echo off
cd /d %~dp0

call C:\Users\ivanm\anaconda3\Scripts\activate.bat gestures
python main.py

pause