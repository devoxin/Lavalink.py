@echo off
py setup.py sdist
twine upload dist/*
rmdir /S /Q dist
rmdir /S /Q lavalink.egg-info

echo "Published to PyPi."
pause
