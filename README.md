# Magick Prototype

## Run pip install

```pip install -r requirements.txt```

## Create executable

### Windows

```pyinstaller --onefile --windowed --add-data "icon.ico;." --icon=icon.ico --name=MagickPrototype prototype.py```

### MacOS

```pyinstaller --onefile --windowed --add-data "icon.icns:." --icon=icon.icns --name=MagickPrototype prototype.py```