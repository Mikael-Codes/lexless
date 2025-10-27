# How Lexless Works

Lexless is a framework that automatically removes interviewer segments from podcast audio, leaving only the guest's valuable content. This document explains the technical details of each processing stage.

## Overview

The Lexless pipeline consists of four main stages:

1. **Audio Download/Input** - Obtain the podcast audio
2. **Speaker Diarization** - Identify who is speaking at each moment
3. **Interviewer Identification** - Determine which speaker to remove
4. **Audio Processing** - Cut out segments and save the result

---

## Stage 1: Audio Download/Input

### YouTube Download

**Library**: `yt-dlp` (a robust YouTube downloader)

**Process**:
- Takes a YouTube URL as input
- Fetches video metadata (title, duration, etc.)
- Downloads the audio stream in high quality (192kbps MP3 by default)
- Converts to audio-only format using FFmpeg
- Saves to local `downloads/` directory

**Key Features**:
- Checks if file already exists before downloading (saves time on re-runs)
- Handles various YouTube formats and quality levels
- Provides progress feedback during download

### Local File Input

**Supported Formats**: MP3, WAV, FLAC, M4A, and other formats supported by `librosa`

**Process**:
- Automatically detects if input is a file path (vs URL)
- Validates file exists and is readable
- Extracts metadata (duration, sample rate, etc.)
- Proceeds directly to diarization

---

## Stage 2: Speaker Diarization

**Library**: `pyannote.audio` with pre-trained models

**What is Speaker Diarization?**
Speaker diarization is the process of answering "who spoke when?" in an audio recording. It identifies different speakers and creates a timeline showing when each person was speaking.

### Model Details

**Model**: `pyannote/speaker-diarization@2.1`

This model is actually a **pipeline** consisting of multiple neural networks:
1. **Voice Activity Detection (VAD)** - Identifies when speech is occurring vs silence
2. **Speaker Embedding** - Creates a numerical representation of each speaker's voice
3. **Clustering** - Groups similar voice embeddings into distinct speakers
4. **Segmentation** - Determines precise start/end times for each speech segment

### Processing Steps

1. **Model Loading**:
   - Downloads models from Hugging Face (first run only)
   - Requires authentication token and acceptance of model terms
   - Models are cached locally for future use (~500MB total)

2. **Audio Analysis**:
   - Input: Audio file path
   - Output: List of speech segments with speaker labels
   - Example output:
     ```
     [(0:00 - 0:05, "SPEAKER_00"),  # Speaker 1 speaks for 5 seconds
      (0:05 - 0:12, "SPEAKER_01"),  # Speaker 2 speaks for 7 seconds
      (0:12 - 0:15, "SPEAKER_00"),  # Speaker 1 speaks again
      ...]
     ```

3. **Performance**:
   - Processing time: Approximately **0.5-2 minutes per minute of audio**
   - Time varies based on:
     - Hardware (CPU/GPU)
     - Number of speakers
     - Audio quality
   - Progress indicator updates every 5 seconds during processing

### Why It Takes Time

The model performs intensive neural network computations:
- Analyzing each audio segment (10-30ms windows)
- Extracting voice characteristics
- Comparing speakers to distinguish between them
- Running multiple passes for accuracy

---

## Stage 3: Interviewer Identification

After diarization, we know when each speaker spoke, but we need to identify which one is the interviewer.

### Detection Methods

#### 1. Duration-Based Detection (Default)

**Assumption**: The interviewer typically talks less than the guest

**Process**:
1. Sum up total speaking time for each speaker
2. Calculate total duration for `SPEAKER_00`, `SPEAKER_01`, etc.
3. Remove the speaker with the **shortest** total duration

**Example**:
```
Speaker 0: 12.5 minutes total
Speaker 1: 47.3 minutes total
→ Remove Speaker 0 (the interviewer)
```

**Pros**: Works well for most podcasts
**Cons**: Fails if interviewers are particularly chatty

#### 2. First Speaker Detection

**Assumption**: The first person to speak is usually the interviewer

**Process**:
1. Identify which speaker starts the recording
2. Remove that speaker

**Pros**: Simple and fast
**Cons**: Not always accurate (guest sometimes starts)

#### 3. Manual Selection

**Process**:
1. Let user preview the speakers
2. Manually select which speaker to remove

**Note**: Not yet implemented in the current version

### Configuration

Set in `config.yaml`:
```yaml
speaker:
  num_speakers: 2
  detection_method: "duration"  # or "first"
```

---

## Stage 4: Audio Processing & Cutting

**Libraries**: `librosa`, `soundfile`, `numpy`

### Audio Format Conversion

1. **Load Audio**:
   - Reads the original audio file
   - Converts to mono (single channel)
   - Resamples to 22,050 Hz (sufficient for speech)
   - Converts to numpy array for processing

2. **Sample Rate**:
   - Standard: 22,050 Hz (files processed at this rate)
   - Higher rates can be configured but increase processing time

### Segment Removal

**Process**:
1. Create a binary mask indicating which samples to keep
2. For each segment to remove:
   - Mark those samples as "delete"
   - Apply smooth fade-out before the cut
   - Apply smooth fade-in after the cut
3. Filter audio array to keep only "keep" samples

**Smooth Transitions**:

To avoid audible "pops" or clicks at cut points, Lexless applies crossfades:

- **Fade-out**: Last 0.1 seconds before cut gradually reduce to silence
- **Fade-in**: First 0.1 seconds after cut gradually increase from silence

```
Audio: [----SPEAKER_A----|CUT|----SPEAKER_B----]
        fade-out ↑        ↑   ↑ fade-in
```

Default fade duration: 0.1 seconds (configurable)

### Normalization

**Purpose**: Ensure consistent volume levels throughout the audio

**Process**:
1. Find the peak amplitude in the audio
2. Scale all samples to maximum possible level without clipping
3. Maintains relative volume differences while maximizing loudness

**Example**:
```
Before: [-0.3, 0.5, -0.2, 0.4]  # Peak is 0.5
After:  [-0.6, 1.0, -0.4, 0.8]  # Scaled to use full range
```

### Saving Output

1. **File Naming**:
   - Default pattern: `{original_name}_clean.mp3`
   - Example: `Lex_Fridman_Podcast_475.mp3` → `Lex_Fridman_Podcast_475_clean.mp3`

2. **Output Format**:
   - Format: MP3
   - Quality: 192 kbps (default, configurable)
   - Sample rate: Original audio's sample rate

3. **Metadata**:
   - Preserves original file metadata where possible
   - File size and duration reported at completion

---

## Technical Deep Dive

### PyAnnote Model Architecture

The speaker diarization pipeline uses:

1. **Segmentation Model** (`pyannote/segmentation`)
   - Detects speech boundaries
   - Binary classifier: speech vs non-speech
   - Architecture: LSTM-based neural network

2. **Embedding Model** (`speechbrain/spkrec-ecapa-voxceleb`)
   - Extracts speaker characteristics
   - Converts audio → 192-dimensional vector
   - Encoder architecture based on ResNet
   - Pre-trained on 1M+ speaker identities

3. **Clustering** (built-in)
   - Groups similar embeddings
   - Uses agglomerative hierarchical clustering
   - Automatically determines number of speakers

### Audio Processing Pipeline

```
Raw Audio File (MP3/WAV/etc.)
    ↓
[librosa.load()]
    ↓
Numpy Array (mono, 22050 Hz)
    ↓
[Generate Keep/Delete Mask]
    ↓
[Apply Crossfades at Boundaries]
    ↓
[Filter to Keep Samples]
    ↓
[Normalize Amplitude]
    ↓
[soundfile.write()]
    ↓
Cleaned Audio File (MP3)
```

### Performance Characteristics

**Memory Usage**:
- Audio loading: ~50-200 MB per hour of audio (at 22kHz)
- Model loading: ~1-2 GB (first time), ~500 MB (cached)
- Peak RAM: Audio size + Model size + ~200 MB overhead

**Processing Speed** (typical hardware):
- Diarization: 0.5x to 2x real-time (i.e., 1 hour audio takes 30 minutes to 2 hours to process)
- Cutting/Normalizing: Near-instant (< 1 second per hour)

**Factors Affecting Speed**:
- CPU: More cores = faster diarization
- GPU: CUDA support can speed up by 2-5x (if configured)
- RAM: More RAM allows processing longer files
- Storage: SSD faster than HDD for model loading

### Error Handling

Lexless includes robust error handling at each stage:

1. **Download Failures**: 
   - Retries network errors
   - Handles authentication issues
   - Validates downloaded file integrity

2. **Model Loading**:
   - Checks for required dependencies
   - Validates Hugging Face authentication
   - Provides clear error messages with fixes

3. **Audio Processing**:
   - Validates file formats
   - Handles corrupt or unreadable files
   - Checks disk space before saving

4. **User Feedback**:
   - Clear error messages with actionable fixes
   - Progress indicators during long operations
   - Detailed logging of each stage

---

## Configuration Options

All customizable behavior is controlled via `config.yaml`:

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
  detection_method: "duration"  # "duration", "first", or "manual"
```

### Processing Options
```yaml
processing:
  transition_smooth: 0.1  # seconds of fade at cuts
  min_segment_length: 2.0  # minimum segment to keep (not yet implemented)
  noise_reduction: false  # future feature
```

### Output Settings
```yaml
output:
  filename_pattern: "{original_name}_clean"
  format: "mp3"
  normalize_audio: true
```

---

## Limitations & Future Improvements

### Current Limitations

1. **Number of Speakers**: Best with 2 speakers (interviewer + guest). May struggle with:
   - Multiple guests
   - Overlapping speech
   - Background voices

2. **Audio Quality**: Works best with:
   - Clear audio (not phone recordings)
   - Minimal background noise
   - Distinct voices

3. **Processing Time**: 
   - Can take 1-2 hours for very long podcasts
   - No GPU acceleration by default

4. **Detection Accuracy**:
   - "Duration" method fails if interviewer talks a lot
   - "First" method assumes interviewer speaks first
   - No manual verification step

### Potential Improvements

1. **GPU Acceleration**: Use CUDA for faster processing
2. **Manual Verification**: Preview and manually select speakers
3. **Multiple Guests**: Support for 3+ speakers
4. **Smart Cuts**: Preserve interviewer's interesting questions
5. **Progress Persistence**: Resume interrupted processing
6. **Batch Processing**: Process multiple files at once
7. **Alternative Models**: Support for other diarization models

---

## Troubleshooting Guide

### Common Issues

**"No Hugging Face token provided"**
- Solution: Set token with `--hf-token` or environment variable

**"Model terms not accepted"**
- Solution: Accept terms at https://huggingface.co/pyannote/speaker-diarization

**"Windows permission error"**
- Solution: Run PowerShell as Administrator

**"Poor speaker detection"**
- Try different `detection_method` in config
- Ensure good audio quality
- Check that there are actually 2 distinct speakers

**"Processing takes forever"**
- This is normal! Expect 1-2 minutes per minute of audio
- Check CPU usage to confirm it's working
- Progress indicator updates every 5 seconds

### Getting Help

If you encounter issues not covered here:

1. Check the error message - it usually includes the solution
2. Review the configuration file
3. Ensure all dependencies are installed
4. Check that you have sufficient disk space and RAM
5. Try with a shorter audio file first to isolate issues

---

## Summary

Lexless provides an automated pipeline to clean podcast audio by:

1. **Downloading** audio from YouTube or processing local files
2. **Identifying** different speakers using advanced AI models
3. **Detecting** which speaker is the interviewer
4. **Removing** interviewer segments with smooth transitions
5. **Saving** a clean output file with just the guest content

The entire process takes about 1-2 minutes per minute of audio, with progress updates throughout. The result is a podcast episode containing only the valuable guest content, with all the interviewer's comments removed.
