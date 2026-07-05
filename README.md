# Insurgency:Sandstorm MOD.IO Manager

## Overview

This project is a desktop application that imports the Mod.IO `state.json` file from the game *Insurgency:Sandstorm* and provides a user-friendly interface to view all installed mods. It allows users to easily access and manage mod commands through an intuitive table interface, making it simpler to work with console commands for the game. 

Mod.IO stores mods for your game each in a separate folder. You need to locate the correct mod folder (NUMBER) and then paste this script into the ~/metadata folder next to the 'state.json' file there.

Startup may feel slow - I'm looking at how to make that faster, give it a few seconds.

<img width="1240" height="793" alt="modmanager" src="https://github.com/user-attachments/assets/670da3f3-fe85-4155-8f22-fd0ca4f56a19" />
<img width="1242" height="791" alt="modmanager2" src="https://github.com/user-attachments/assets/b684ea37-4877-4eb5-89f1-667e5f11b451" />
<img width="1236" height="787" alt="modmanager1" src="https://github.com/user-attachments/assets/b96d725d-adf4-4d68-b9d6-6bda77a1b9d1" />
<img width="1183" height="740" alt="consolegenerator" src="https://github.com/user-attachments/assets/ac4ff081-c2be-4b20-a8d4-b249b993d924" />


## Purpose

The application imports mod data from the game's `state.json` file and displays it in a clean, searchable table. Users can:
- View all installed mods with their properties
- Search and filter mods by any field
- See detailed mod information including descriptions
- Manage metadata associated with mods
- Reimport updated mod data from the game

## Scripts

### insurgency_manager.py
The main application that provides a GUI interface for managing Insurgency:Sandstorm mods.

### console_generator.py
A utility script that generates console commands for mods. This script requires a cache file to populate the mod data correctly.

## Dependencies

Both scripts require the following dependencies:

1. **PyWebView** - For creating the desktop GUI interface
2. **Python 3.x** - The scripting language used for the backend

### Installing Dependencies

To install the required dependencies, run:

```bash
pip install pywebview
```

## Usage

### Running the Main Application

To start the main application, run:

```bash
python insurgency_manager.py
```

or

```bash
python3 insurgency_manager.py
```

To update the mods.db via commandline, run:

```bash
python insurgency_manager.py reimport
```

or

```bash
python3 insurgency_manager.py reimport
```

### Running the Console Generator

To run the console generator, run:

```bash
python console_generator.py
```

or

```bash
python3 console_generator.py
```

### How It Works

1. The application automatically loads data from the `state.json` file in the same directory
2. It creates a SQLite database (`mods.db`) to store and manage the mod information
3. The main window displays all mods in a searchable table
4. Users can:
   - Search mods by any field
   - View detailed mod information
   - Reimport updated mod data from the game
   - Manage metadata associated with mods

### File Structure

The application expects these files in the same directory:
- `state.json` - The game's mod state file
- `insurgency_manager.py` - The main application script
- `console_generator.py` - The console command generator script

## Features

- **Mod Management**: View all installed mods in a clean table interface
- **Search Functionality**: Search through all mod properties
- **Detailed Views**: See full descriptions and metadata
- **Reimport Capability**: Update mod data from the game
- **Dark/Light Theme**: Toggle between color themes
- **Metadata Management**: Add and manage custom metadata for mods
- **Console Command Generation**: Generate console commands for mods

## Known Issues

Both apps are not currently designed to work efficiently, they will have a Slow startup - in most cases just wait.

- **insurgency_manager.py** Last imported tag is not persistent or accurate. Too much of a headache for me at this stage to sort out.

- **console_generator.py** often needs to be restarted multiple times after waiting a bit to pick up the cached object required to populate it.

## Requirements

- Python 3.x
- PyWebView library
- The game *Insurgency:Sandstorm* with a valid Mod.IO `state.json` file

## AI usage

- This was vibecoded across a week with OpenCode and Qwen3-Coder-12b-GGUF

