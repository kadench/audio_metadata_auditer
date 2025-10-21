# Music Library Metadata Editor (CLI-ONLY)
![AI Used](https://img.shields.io/badge/%E2%9C%A8-AI%20USED-blue)
[![TECH STACK](https://img.shields.io/badge/%F0%9F%92%BB-PYTHON%20|%203.10%2B-red)](https://python.org/downloads)

I continued on with the music-related aspect. With the recent update of Alexa and Siri, there's not a point for my previous project anymore. This new one has a use even if technology advances.  
May I introduce to you: a cli-based audio metadata auditor tool you can use to quickly and efficiently scan your audio (file) music library.

---

### Quick Install
- Click [here]() to go to the most recent release page to download the program.  
- Click [here](#syntax) to view syntax.

---

## How It Works
This is a **read-only**, text-based summary scanner. It scans your folders, checks metadata, and reports problems, but never changes your files.  
Each report includes:
1. A health bar showing the overall state of your library  
2. Quick totals (albums, tracks, size, duration)  
3. A short list of albums with any problems found

Example:
```txt
"E:\Music" Library Scan
==============================================================
Health: [===============================.....] 85%
Albums: 42  Tracks: 514  Size: 18.4 GB  Duration: 1d 3h 28m
==============================================================

[WARN] Hybrid Theory (Linkin Park)
    - Cover artwork differs across tracks in this album.
```

---

## Command Options

1. `--folder` / `-f`  
**Required.** Tells the program which folder to scan. Without it, the program stops with an error.

2. `--terminal` / `-t`  
Shows the progress bar and final results in your command window.  
If not used, results only appear if no file or clipboard option is selected.

3. `--to-file` / `-tf`  
Saves the report to a text file. Does not change the content, just the destination.

4. `--output-path` / `-op`  
Sets where the output file is saved when using `--to-file`.  
If not used, the file is created in the same directory as the program.

5. `--copy` / `-c`  
Copies the finished report to your clipboard instead of saving or printing it.

6. `--max-depth` / `-md`  
Sets how many subfolders deep the program scans. The default is **5**.  
Does not affect the format of the report.

7. `--per-album` / `-pa`  
Adds each album’s total duration and size to its header line.  

---

### #7 Example
**Before:**
```txt
[WARN] Hybrid Theory (Linkin Park):
    - Cover artwork differs across tracks.
```

**With `--per-album`:**
```txt
[WARN] Hybrid Theory (Linkin Park) | Duration: 47m 2s, Size: 428.32 MB
    - Cover artwork differs across tracks.
```

---

8. `--no-quick-stats` / `-nqs`  
Removes the default quick stats line:
```txt
Albums: 42  Tracks: 514  Size: 18.4 GB  Duration: 1d 3h 28m
```
The health bar still appears, but totals are hidden.

---

9. `--debug` / `-d`  
Adds a debug section at the end showing scanned paths, nested folder depths and any skipped files.  

---

### #9 Example
```text
Debug
[debug] entering: {file_path} - {album_name} (depth={depth_amount})
[debug] entering: {file_path} - {album_name} (depth={depth_amount})
[debug] entering: {file_path} - {album_name} (depth={depth_amount})
```

---

10. `--help` / `-h`  
Shows all available options and descriptions. Exits immediately after displaying help.

---

## How to Install

You can run this program **two different ways**, depending on your preference:

### Option 1: Run the EXE Directly (no setup required)
1. Download the latest `.exe` from the [Releases page]().  
2. Place it anywhere convenient (for example, on your Desktop or inside your Music folder).  
3. Open that folder in File Explorer, click in the address bar, type `cmd`, and press Enter.  
4. Run the program from that folder:
   ```bash
   ama.exe -f "E:\Music" -t
   ```
   The scan runs right where the `.exe` is located. No installation or PATH setup needed.

---

### Option 2: Run from Python Source
1. Make sure [Python 3.10 or newer](https://python.org/downloads) is installed.  
2. Download the `.py` version instead of the `.exe`.  
3. Open the folder containing the script.  
4. In the address bar, type `cmd` and press Enter.  
5. Run the command:
   ```bash
   python ama.py -f "E:\Music" -t
   ```
   You can also add extra flags (like `-pa` or `-nqs`) in the same way.
    > Optional: You can download the `ama_unittest.py` to view the tests AI gave me.

Both versions produce identical results.  

---

## Syntax
```txt
usage: ama.py [-h] --folder FOLDER [--to-file] [--terminal]
               [--output-path OUTPUT_PATH] [--copy] [--debug]
               [--max-depth MAX_DEPTH] [--per-album] [--no-quick-stats]

Return an overall health report of all audio files in a given folder.

options:
  -h, --help            show this help message and exit
  --folder, -f FOLDER   Path of the folder to scan.
  --to-file, -tf        Save results to a file.
  --terminal, -t        Print results to the terminal.
  --output-path, -op OUTPUT_PATH
                        File path to save results to.
  --copy, -c            Copy results to clipboard.
  --debug, -d           Include a debug section at the end.
  --max-depth MAX_DEPTH
                        Maximum subfolder depth to scan (default 5).
  --per-album, -pa      Show per-album duration and size on the header line.
  --no-quick-stats, -nqs
                        Hide the global quick stats line (the line under the health bar).
```

---

## System Requirements
- Windows 10 or later  
- Read-only file access to scanned folders  
- About 512 MB RAM recommended for large libraries  
    > Optional: Python 3.10 or newer if running the `.py` version