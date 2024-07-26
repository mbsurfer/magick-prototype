# Magick Prototype

## Run pip install

```pip install -r requirements.txt```

## Create executable

### Windows

```pyinstaller --onefile --windowed --add-data "icon.ico;." --add-data "images;images" prototype.py```

### MacOS

```pyinstaller --onefile --windowed --add-data "icon.ico:." --add-data "images:images" prototype.py```