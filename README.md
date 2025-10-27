# Lexless

**Automatically cut out the interviewer segments from podcast audio.**

Lexless is a Python framework that downloads YouTube podcast videos, identifies when the interviewer is speaking, and removes those segments, leaving you with just the interesting guest content.

## Features

- 🎤 **Automatic Speaker Detection**: Uses state-of-the-art speaker diarization to identify different speakers
- ✂️ **Smart Segment Removal**: Automatically identifies and removes interviewer segments
- 🎯 **Configurable**: Flexible configuration system for different podcast styles
- 🔧 **Generalizable**: Works for any podcast with interviewer + guest format
- 🎵 **Audio Processing**: Smooth transitions and optional normalization

## Installation

1. Clone this repository:
```bash
git clone https://github.com/mikael-codes/lexless.git
cd lexless
```

2. Install system dependencies (required for building some Python packages):
   
   **On Fedora/RHEL:**
   ```bash
   sudo dnf install -y python3-devel
   ```
   
   **On Ubuntu/Debian:**
   ```bash
   sudo apt-get install -y python3-dev
   ```
   
   **On macOS:**
   ```bash
   xcode-select --install
   # or if using Homebrew
   brew install python3
   ```
   
   **On Arch Linux:**
   ```bash
   sudo pacman -S python
   ```

3. Install Python dependencies:
```bash
# Option 1: Install as a package (recommended)
python -m pip install -e .

# Option 2: Install dependencies only
python -m pip install -r requirements.txt
```

**Note:** If `pip` is not in your PATH, use `python -m pip` instead.

4. Set up Hugging Face token:
   
   Lexless uses the pyannote speaker diarization model which requires Hugging Face authentication.
   
   **Step-by-step setup:**
   
   a. Create a Hugging Face account at https://huggingface.co
   
   b. Create an access token:
      - Go to https://huggingface.co/settings/tokens
      - Click "New token"
      - Give it a name (e.g., "lexless")
      - Select "Read" access
      - Click "Generate token"
      - Copy the token (starts with `hf_`)
   
   c. Accept model terms (required for both models):
      - Go to https://huggingface.co/pyannote/speaker-diarization and click "Agree and access repository"
      - Go to https://huggingface.co/pyannote/segmentation and click "Agree and access repository"
      - This is required to download the models
   
   d. Authenticate with your token (choose one method):
      
      **Method 1 - One-time login:**
      ```bash
      python -c "from huggingface_hub import login; login(token='YOUR_TOKEN')"
      ```
      
      **Method 2 - Environment variable:**
      - Windows PowerShell: `$env:HF_TOKEN="your_token"`
      - Windows CMD: `set HF_TOKEN=your_token`
      - Linux/Mac: `export HF_TOKEN=your_token`
      
      **Method 3 - Pass with each command:**
      ```bash
      lexless URL --hf-token YOUR_TOKEN
      ```

5. Copy and edit configuration:
    ```bash
    # On Linux/Mac:
    cp config.example.yaml config.yaml

    # On Windows:
    copy config.example.yaml config.yaml
    ```

## Usage

After installing with `pip install .`, you can use the `lexless` command directly:

Basic usage:
```bash
lexless https://www.youtube.com/watch?v=VIDEO_ID
```

With custom output name:
```bash
lexless https://www.youtube.com/watch?v=VIDEO_ID --output "my_podcast"
```

Using environment variable for token:
```bash
export HF_TOKEN=your_token_here
lexless https://www.youtube.com/watch?v=VIDEO_ID
```

Or pass token directly:
```bash
lexless https://www.youtube.com/watch?v=VIDEO_ID --hf-token your_token_here
```

Process a local audio file instead of downloading:
```bash
lexless path/to/podcast.mp3 --file --hf-token your_token_here
```

Alternatively, if you only installed dependencies with `pip install -r requirements.txt`, use:
```bash
python -m lexless.main https://www.youtube.com/watch?v=VIDEO_ID
```

## Configuration

Edit `config.yaml` to customize behavior:

### Download Settings
```yaml
download:
  output_dir: "downloads"
  audio_format: "mp3"
  audio_bitrate: "192k"
```

### Speaker Detection
```yaml
speaker:
  num_speakers: 2
  detection_method: "duration"  # Options: "duration", "first"
```

- **duration**: Removes the speaker who talks less (usually the interviewer)
- **first**: Removes the first detected speaker

### Processing Options
```yaml
processing:
  transition_smooth: 0.1  # Seconds of fade at transitions
  min_segment_length: 2.0
  noise_reduction: false
```

### Output Settings
```yaml
output:
  filename_pattern: "{original_name}_clean"
  format: "mp3"
  normalize_audio: true
```

## How It Works

1. **Download**: Downloads YouTube video and extracts audio
2. **Diarize**: Identifies different speakers using deep learning
3. **Identify**: Determines which speaker is the interviewer
4. **Cut**: Removes interviewer segments with smooth transitions
5. **Output**: Saves cleaned audio file

## Troubleshooting

### Cannot compile `Python.h` / Building numpy from source fails
- You need to install Python development headers on your system
- **Fedora/RHEL**: `sudo dnf install -y python3-devel`
- **Ubuntu/Debian**: `sudo apt-get install -y python3-dev`
- **Arch Linux**: `sudo pacman -S python`
- **macOS**: `xcode-select --install` or use Homebrew Python

### "No Hugging Face token provided"
- Set your token: `export HF_TOKEN=your_token`
- Or pass it with `--hf-token your_token`
- Don't forget to accept the model terms at the Hugging Face link

### "Could not load pyannote model"
- Ensure you've accepted the model terms
- Check your Hugging Face token is valid
- Try running with `--hf-token` to explicitly provide the token

### Poor speaker detection
- Try adjusting `num_speakers` in config
- Switch detection method from "duration" to "first" or vice versa
- Ensure good audio quality in the source video

## Development

Project structure:
```
lexless/
├── downloader.py      # YouTube download functionality
├── speaker_diarization.py  # Speaker identification
├── audio_processor.py      # Audio cutting and processing
└── main.py           # CLI interface
```

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

