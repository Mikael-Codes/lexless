"""Audio processing and cutting module."""

import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
from typing import List, Tuple
import warnings

warnings.filterwarnings('ignore')


class AudioProcessor:
    """Processes audio and removes specified segments."""
    
    def __init__(self, sample_rate: int = 22050):
        """Initialize audio processor.
        
        Args:
            sample_rate: Sample rate for audio processing
        """
        self.sample_rate = sample_rate
    
    def load_audio(self, audio_path: Path) -> Tuple[np.ndarray, int]:
        """Load audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio data, sample rate)
        """
        y, sr = librosa.load(str(audio_path), sr=self.sample_rate)
        return y, sr
    
    def cut_segments(self, audio: np.ndarray, 
                    timestamps_to_remove: List[Tuple[float, float]],
                    smooth_transition: float = 0.1) -> np.ndarray:
        """Remove specified time segments from audio.
        
        Args:
            audio: Audio data as numpy array
            timestamps_to_remove: List of (start, end) timestamps to remove
            smooth_transition: Seconds to fade in/out at transitions
            
        Returns:
            Audio with segments removed
        """
        # Sort timestamps
        timestamps_to_remove = sorted(timestamps_to_remove)
        
        # Create a mask for samples to keep
        samples_to_keep = np.ones(len(audio), dtype=bool)
        
        # Convert timestamps to sample indices
        for start_time, end_time in timestamps_to_remove:
            start_sample = int(start_time * self.sample_rate)
            end_sample = int(end_time * self.sample_rate)
            
            # Ensure indices are within bounds
            start_sample = max(0, start_sample)
            end_sample = min(len(audio), end_sample)
            
            # Apply smooth fade-out before cut
            if smooth_transition > 0 and start_sample > 0:
                fade_samples = int(smooth_transition * self.sample_rate)
                fade_start = max(0, start_sample - fade_samples)
                fade_array = np.linspace(1.0, 0.0, start_sample - fade_start)
                audio[fade_start:start_sample] *= fade_array[:start_sample - fade_start]
            
            # Apply smooth fade-in after cut
            if smooth_transition > 0 and end_sample < len(audio):
                fade_samples = int(smooth_transition * self.sample_rate)
                fade_end = min(len(audio), end_sample + fade_samples)
                fade_array = np.linspace(0.0, 1.0, fade_end - end_sample)
                audio[end_sample:fade_end] *= fade_array[:fade_end - end_sample]
            
            # Mark samples for removal
            samples_to_keep[start_sample:end_sample] = False
        
        # Filter audio
        processed_audio = audio[samples_to_keep]
        
        return processed_audio
    
    def save_audio(self, audio: np.ndarray, output_path: Path, 
                   sample_rate: int = None):
        """Save audio to file.
        
        Args:
            audio: Audio data
            output_path: Path to save audio
            sample_rate: Sample rate (defaults to instance sample_rate)
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        sf.write(str(output_path), audio, sample_rate)
    
    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio levels.
        
        Args:
            audio: Audio data
            
        Returns:
            Normalized audio data
        """
        # Simple peak normalization
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val
        return audio
    
    def process_audio(self, audio_path: Path,
                     timestamps_to_remove: List[Tuple[float, float]],
                     output_path: Path,
                     normalize: bool = True,
                     smooth_transition: float = 0.1) -> Path:
        """Complete audio processing pipeline.
        
        Args:
            audio_path: Input audio file path
            timestamps_to_remove: Segments to remove
            output_path: Output file path
            normalize: Whether to normalize audio
            smooth_transition: Fade duration at cuts
            
        Returns:
            Path to processed audio
        """
        # Load audio
        print("Loading audio...")
        audio, sr = self.load_audio(audio_path)
        
        print(f"Original duration: {len(audio) / sr:.2f} seconds")
        
        # Cut segments
        print("Removing segments...")
        processed_audio = self.cut_segments(audio, timestamps_to_remove, smooth_transition)
        
        print(f"New duration: {len(processed_audio) / sr:.2f} seconds")
        print(f"Removed: {len(audio) / sr - len(processed_audio) / sr:.2f} seconds")
        
        # Normalize if requested
        if normalize:
            print("Normalizing audio...")
            processed_audio = self.normalize_audio(processed_audio)
        
        # Save
        print(f"Saving to {output_path}...")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.save_audio(processed_audio, output_path, sr)
        
        print(f"Successfully saved {len(processed_audio) / sr / 60:.2f} minutes of audio")
        
        return output_path

