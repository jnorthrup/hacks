**summarize2 Documentation**

**Overview**
The `summarize2` script is a Bash utility for processing audio files and generating transcripts using Whisper-CPP. It supports both URL inputs and local audio files, with automatic conversions and caching.

**Features**
- URL Handling: When provided with a URL, the script uses `yt-dlp` to download the audio.
- Audio Conversion: If the input audio is not in WAV format, it converts the file to a 16kHz stereo WAV file using `ffmpeg`.
- Transcription Caching: The script caches transcript outputs to avoid redundant processing. Cached transcripts are reused if available.
- Transcription with Whisper-CPP: It invokes `whisper-cli` to transcribe the WAV audio.
  **Important:** The environment variable `MODEL_PATH` must be set to the Whisper-CPP model path.
- Text Transcript Cleaning: For textual transcript files (with extensions `.vtt` or `.out`), it calls appropriate Python cleaning scripts (`vttclean.py` or `clean-transcript.py`).
- VTT Handling: The script now correctly handles `.vtt` files by skipping the audio conversion and directly cleaning the transcript.

**Requirements**
- Dependencies:
  - `ffmpeg`
  - `whisper-cli`
  - `yt-dlp`
  - Python (for running cleaning scripts)
- Environment Variables:
  - `MODEL_PATH` – path to the Whisper-CPP model. This variable must be defined prior to running the script.

**Usage**
Run the script from a terminal with an audio file or URL as the argument:
````bash
./summarize2 /path/to/audio/file.mp3
# or
./summarize2 https://example.com/path/to/audio
````

For URL inputs, the script downloads the audio and processes it accordingly.

**Common Error**
- "MODEL_PATH: unbound variable":
  This error occurs if the `MODEL_PATH` environment variable is not set. To resolve, ensure you define it in your environment before running the script:
  ````bash
  export MODEL_PATH="/path/to/whisper/model.bin"
  ````

**Workflow Summary**
1. **Input Check:**
   - Validates input and downloads audio from a URL if necessary.
2. **File Processing:**
   - Converts the audio to WAV if not already in WAV format (unless it's a `.vtt` or `.out` file).
3. **Transcription:**
   - Uses `whisper-cli` to transcribe the audio, utilizing caching to save outputs.
4. **Cleaning & Scheduling:**
   - Cleans transcripts for textual files and schedules additional processing jobs.

**Additional Notes**
- The script assumes that dependencies are correctly installed and available in the system PATH.
- Further processing (e.g., converting to OGG Opus and cleanup) may be appended in future updates.

**ollm_bridge.py Documentation**
The `ollm_bridge.py` script is a Python tool that creates symbolic links between Ollama models and LMStudio. It allows users to manage their models in both Ollama and LMStudio by creating symbolic links between the model directories.

Here's a breakdown of the script's functionality:

- `run_command(command, debug=False)`: Runs a given command using `subprocess` and returns the output. It also handles debugging and error logging.
- `get_ollama_models_dir()`: Determines the Ollama models directory based on the environment variable `OLLAMA_MODELS` or platform-specific default paths.
- `list_ollama_models()`: Lists available Ollama models using the `ollama list` command.
- `check_directory_permissions(directory: str)`: Checks if the script has the necessary permissions to read and write to the specified directory.
- `validate_model_format(model_path: str)`: Checks if a given model file has a supported file extension (`.gguf` or `.ggml`).
- `check_lmstudio_version()`: Checks the LM Studio version using the `lmstudio version` command.
- `import_model(model_path: str, cli_path: str, cli_name: str)`: Imports a model into LM Studio using the LM Studio CLI.
- `get_lmstudio_cli_path()`: Returns the platform-specific path to the LM Studio CLI.
- `get_lmstudio_models_dir()`: Retrieves the LM Studio models directory using the LM Studio CLI.
- `get_model_files(ollama_dir: str, model_name: str)`: Retrieves the actual model files from the Ollama models directory, with format validation.
- `create_symlinks(source_dir: str, target_dir: str, models: List[str], link_type: str = 'soft', force: bool = False)`: Creates symbolic links for the specified models from the source directory to the target directory.
- `main()`: The main function that parses command-line arguments, determines the source and target directories, and creates the symbolic links.

The script supports the following command-line arguments:

- `-d` or `--debug`: Enables debug output.
- `-i` or `--interactive`: Enables interactive model selection.
- `--dry-run`: Preview changes without making them.
- `--direction`: Specifies the direction of model linking (ollama-to-lmstudio or lmstudio-to-ollama).
- `--link-type`: Specifies the type of link to create (soft, hard, or ntfs).
- `--force`: Forces overwrite existing links.
- `--import-only`: Only import models, no linking.

**2ocr.sh Documentation**
The script `2ocr.sh` is a Bash script that performs OCR (Optical Character Recognition) on a directory of TIFF files and combines the results into a single searchable PDF.

Here's a breakdown of the script's functionality:

- **Initialization**:
  - Defines variables for the input directory (`INPUT_DIR`), output PDF file (`OUTPUT_PDF`), and temporary directory (`TEMP_DIR`).
  - Creates the temporary directory to store processed files.
- **OCR Processing**:
  - Iterates through each TIFF file in the input directory.
  - Extracts the filename without the extension.
  - Runs Tesseract OCR on each file, outputting a PDF for each page into the temporary directory.
- **PDF Combination**:
  - Checks if `pdfunite` (from `poppler-utils`) is available.
    - If available, it combines all individual page PDFs in the temporary directory into a single PDF using `pdfunite`.
    - If not available, it falls back to using ImageMagick's `convert` to combine the PDFs.
- **Cleanup**:
  - Removes the temporary directory and its contents.
- **Completion**:
  - Prints a message indicating the name of the created searchable PDF.

To use the script:

1.  Ensure that Tesseract OCR and either `pdfunite` (from `poppler-utils`) or ImageMagick are installed.
2.  Place the TIFF files in the directory specified by the `INPUT_DIR` variable.
3.  Run the script.

**clean-transcript.py Documentation**
The script `clean-transcript.py` is a Python script that cleans and formats transcript text from an input file (typically generated by a speech-to-text system) and prints the cleaned output to standard output. The cleaning process includes removing HTML tags, removing leading whitespace, and removing speaker turn tags. The script reads from standard input and writes to standard output.

Here's a breakdown of the script's functionality:

- **`clean_transcript(raw_text, is_vtt=False)`**: Takes raw text as input and applies cleaning functions. It:
  - Removes HTML tags.
  - Removes specific speaker prefixes followed by timestamps.
  - Removes leading whitespace.
  - Removes `[SPEAKER_TURN]` tags.
  - Applies line and word stutter removal.
- **Main execution block**: Reads the entire input from standard input (`sys.stdin`), cleans it using `clean_transcript`, and prints the result to standard output (`sys.stdout`).

To use the script:

1.  Save the script to a file named `clean-transcript.py`.
2.  Run the script, piping in the input file:
    ```bash
    cat input_file.txt | python3 clean-transcript.py
    ```

**vttclean.py Documentation**
The script `vttclean.py` is a Python script that cleans and processes VTT (Video Text Tracks) files. It removes HTML tags, multiple spaces, and metadata, and it also attempts to keep only the most complete line in cases where captions are split into multiple lines.

Here's a breakdown of the script's functionality:

- **`clean_text(text)`**: Removes HTML tags and multiple spaces from the given text and strips leading/trailing whitespace.
- **`is_prefix(a, b)`**: Checks if string `a` is a prefix of string `b`.
- **`process_vtt(content)`**: Processes the VTT content. It:
  - Removes the WEBVTT header and metadata.
  - Splits the content into captions.
  - Extracts the start time (without milliseconds) and the text from each caption.
  - Cleans the caption text using `clean_text`.
  - Maintains a buffer to keep track of caption lines.
  - Only appends a new line to the buffer if its text is a prefix of the previous line's text, otherwise it flushes the buffer and starts a new one.
- **Main execution block**:
  - Checks for a filename argument.
  - Reads the content of the specified VTT file.
  - Calls `process_vtt` to clean the content.
  - Prints the cleaned VTT content to standard output.

To use the script:

1.  Save the script to a file named `vttclean.py`.
2.  Run the script with the VTT file as an argument:
    ```bash
    python3 vttclean.py input.vtt
