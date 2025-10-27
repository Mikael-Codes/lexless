"""Speaker diarization module to identify who is speaking."""

import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import torch
from pyannote.core import Segment
import librosa
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')


class SpeakerDiarizer:
    """Identifies and separates different speakers in audio."""
    
    def __init__(self, hf_token: Optional[str] = None):
        """Initialize speaker diarizer.
        
        Args:
            hf_token: Hugging Face token for pyannote models (if needed)
        """
        self.hf_token = hf_token
        self.inference = None
        
        # Don't initialize model here - load it lazily when needed
        # This avoids loading the model if user just wants to check the CLI
    
    def _load_model(self):
        """Lazily load the speaker diarization model."""
        if self.inference is None:
            try:
                import os
                import shutil
                from pathlib import Path
                from pyannote.audio import Pipeline
                
                print("Loading speaker diarization model (this may take a moment)...")
                
                # Workaround for Windows file permission issues
                # Ensure torch cache directories exist
                try:
                    import torch
                    torch_cache = Path.home() / ".cache" / "torch"
                    pyannote_dir = torch_cache / "pyannote"
                    pyannote_dir.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass  # Continue anyway
                
                if self.hf_token:
                    # Login first to ensure token is active
                    try:
                        from huggingface_hub import login
                        login(token=self.hf_token)
                    except ImportError:
                        pass  # huggingface_hub not installed, continue anyway
                    
                    # Use the Pipeline API which is more stable
                    pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization@2.1",
                        use_auth_token=self.hf_token
                    )
                else:
                    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization@2.1")
                
                self.inference = pipeline
                print("Model loaded successfully!")
            except Exception as e:
                error_msg = str(e)
                
                # Check for Windows permission error
                if "WinError 1314" in error_msg or "privilege" in error_msg.lower():
                    raise RuntimeError(
                        f"Windows file permission error: {error_msg}\n\n"
                        "FIX: Run your terminal as Administrator:\n"
                        "1. Close this terminal\n"
                        "2. Right-click PowerShell/Terminal\n"
                        "3. Select 'Run as Administrator'\n"
                        "4. Run your lexless command again"
                    )
                
                raise RuntimeError(
                    f"Could not load pyannote model: {error_msg}\n\n"
                    "Please follow these steps:\n"
                    "1. Accept the model terms at: https://huggingface.co/pyannote/speaker-diarization\n"
                    "2. Accept segmentation model terms at: https://huggingface.co/pyannote/segmentation\n"
                    "3. Make sure you're logged into Hugging Face and have accepted both agreements\n"
                    "4. Your token must have access to the models\n"
                    "5. Try setting your token with: --hf-token YOUR_TOKEN"
                )
    
    def diarize(self, audio_path: Path, num_speakers: int = 2) -> List[Tuple[Segment, str]]:
        """Identify which segments belong to which speaker.
        
        Args:
            audio_path: Path to audio file
            num_speakers: Number of speakers to detect
            
        Returns:
            List of (segment, speaker_id) tuples
        """
        # Load model if not already loaded
        self._load_model()
        
        # Get audio duration for progress estimation
        try:
            import soundfile as sf
            info = sf.info(str(audio_path))
            duration = info.frames / info.samplerate
            est_time = duration * 2  # Rough estimate: 2 min per audio minute
            print(f"Audio duration: {duration/60:.2f} minutes")
            print(f"Estimated processing time: {est_time/60:.1f} minutes")
            print("Starting speaker diarization...\n")
        except Exception:
            print("Starting speaker diarization...\n")
            est_time = None
        
        # Add a progress indicator thread
        import threading
        import time
        progress_active = threading.Event()
        progress_active.set()
        
        def show_progress():
            elapsed = 0
            dots = 0
            while progress_active.is_set():
                time.sleep(5)
                elapsed += 5
                dots = (dots + 1) % 4
                dot_str = "." * dots + " " * (3 - dots)
                if est_time:
                    progress_pct = min(100, int((elapsed / est_time) * 100))
                    print(f"Processing{dot_str} ({elapsed//60}m {elapsed%60}s elapsed, ~{progress_pct}%)", end='\r')
                else:
                    print(f"Processing{dot_str} ({elapsed//60}m {elapsed%60}s elapsed)", end='\r')
        
        progress_thread = threading.Thread(target=show_progress, daemon=True)
        progress_thread.start()
        
        try:
            # Perform diarization
            # Pipeline expects {"uri": "path", "audio": "path"}
            diarization = self.inference({"uri": str(audio_path), "audio": str(audio_path)})
        finally:
            progress_active.clear()
            print()  # New line after progress
        
        print("Diarization complete! Processing results...")
        
        # Convert to list of tuples
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append((turn, speaker))
        
        print(f"Found {len(segments)} speech segments")
        return segments
    
    def get_speaker_segments(self, segments: List[Tuple[Segment, str]], 
                           speaker_id: str) -> List[Segment]:
        """Get all segments for a specific speaker.
        
        Args:
            segments: List of (segment, speaker_id) tuples
            speaker_id: Speaker identifier (e.g., "SPEAKER_00")
            
        Returns:
            List of segments for the specified speaker
        """
        return [seg for seg, speaker in segments if speaker == speaker_id]
    
    def identify_interviewer(self, segments: List[Tuple[Segment, str]], 
                            method: str = "duration") -> str:
        """Identify which speaker is the interviewer.
        
        Args:
            segments: List of (segment, speaker_id) tuples
            method: Detection method - "duration" (shorter speaker), 
                   "first" (first speaker), or "manual"
                   
        Returns:
            Speaker ID of the interviewer
        """
        if not segments:
            return ""
        
        # Get unique speakers
        speakers = list(set(speaker for _, speaker in segments))
        
        if len(speakers) <= 1:
            return speakers[0] if speakers else ""
        
        if method == "first":
            # First speaker is usually the interviewer
            return segments[0][1]
        
        elif method == "duration":
            # Calculate total speaking time for each speaker
            speaker_duration = {}
            for segment, speaker in segments:
                if speaker not in speaker_duration:
                    speaker_duration[speaker] = 0
                speaker_duration[speaker] += segment.duration
            
            # Usually the interviewer talks less than the guest
            # Return the speaker with less total duration
            return min(speaker_duration.items(), key=lambda x: x[1])[0]
        
        elif method == "manual":
            # Manual selection - would prompt user
            raise NotImplementedError("Manual selection not implemented")
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def get_speaker_timestamps(self, audio_path: Path, 
                             num_speakers: int = 2,
                             target_speaker: Optional[str] = None,
                             detection_method: str = "duration") -> List[Tuple[float, float]]:
        """Get timestamps for segments to remove.
        
        Args:
            audio_path: Path to audio file
            num_speakers: Number of speakers to detect
            target_speaker: Specific speaker to remove (optional)
            detection_method: Method to identify interviewer
            
        Returns:
            List of (start_time, end_time) tuples to remove
        """
        # Perform diarization
        segments = self.diarize(audio_path, num_speakers)
        
        # Identify which speaker to remove
        if target_speaker is None:
            interviewer_id = self.identify_interviewer(segments, detection_method)
        else:
            interviewer_id = target_speaker
        
        # Get segments for the interviewer
        interviewer_segments = self.get_speaker_segments(segments, interviewer_id)
        
        # Convert to (start, end) tuples
        timestamps = [(seg.start, seg.end) for seg in interviewer_segments]
        
        return timestamps

