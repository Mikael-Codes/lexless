"""Main CLI interface for Lexless."""

import click
import yaml
from pathlib import Path
from typing import Optional
import os

from lexless.downloader import YouTubeDownloader
from lexless.speaker_diarization import SpeakerDiarizer
from lexless.audio_processor import AudioProcessor


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        click.echo(f"Config file not found: {config_path}")
        click.echo("Copy config.example.yaml to config.yaml and edit as needed")
        raise
    except Exception as e:
        click.echo(f"Error loading config: {e}")
        raise


@click.command()
@click.argument('input_source')
@click.option('--config', '-c', default='config.yaml', 
              help='Path to configuration file')
@click.option('--output', '-o', 
              help='Output filename (without extension)')
@click.option('--hf-token', 
              help='Hugging Face token for pyannote models')
@click.option('--file', '-f', is_flag=True,
              help='Treat input as local file path instead of URL')
def main(input_source: str, config: str, output: Optional[str], hf_token: Optional[str], file: bool):
    """Remove interviewer segments from podcast audio.
    
    INPUT_SOURCE can be either a YouTube URL or path to a local audio file.
    Use --file flag to process a local audio file instead of downloading.
    """
    
    # Load configuration
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"Creating default config file: {config_path}")
        example_config = Path('config.example.yaml')
        if example_config.exists():
            import shutil
            shutil.copy(example_config, config_path)
            click.echo("Please edit config.yaml with your settings and run again")
            return
    
    cfg = load_config(config_path)
    
    # Get Hugging Face token
    token = hf_token or os.getenv('HF_TOKEN')
    if not token:
        click.echo("\nWarning: No Hugging Face token provided.")
        click.echo("You need a token to use pyannote models.")
        click.echo("Get one at: https://huggingface.co/settings/tokens")
        click.echo("And accept the terms at: https://huggingface.co/pyannote/speaker-diarization")
        click.echo("\nSet it with --hf-token or HF_TOKEN environment variable")
        return
    
    # Check if processing local file or downloading from URL
    # Auto-detect: if it's not a URL, treat as file path
    is_local_file = file or (not input_source.startswith('http://') and not input_source.startswith('https://'))
    
    if is_local_file:
        # Process local audio file
        audio_path = Path(input_source)
        if not audio_path.exists():
            click.echo(f"Error: File not found: {audio_path}")
            click.echo("If you meant to process a URL, make sure it starts with http:// or https://")
            return
        
        click.echo(f"\nProcessing local audio file: {audio_path}")
        
        # Get file metadata
        import soundfile as sf
        import librosa
        info = sf.info(str(audio_path))
        duration_seconds = info.frames / info.samplerate
        video_info = {
            'title': audio_path.stem,
            'length': int(duration_seconds)
        }
    else:
        # Download from YouTube URL
        click.echo(f"\nChecking YouTube URL: {input_source}")
        downloader = YouTubeDownloader(output_dir=cfg['download']['output_dir'])
        
        video_info = downloader.get_video_info(input_source)
        click.echo(f"Title: {video_info['title']}")
        click.echo(f"Duration: {video_info['length'] // 60} minutes")
        
        # Check if file already exists
        safe_title = "".join(c for c in video_info['title'] if c.isalnum() or c in (' ', '-', '_'))
        safe_title = safe_title.strip().replace(' ', '_')
        expected_path = downloader.output_dir / f"{safe_title}.mp3"
        
        if expected_path.exists():
            click.echo(f"File already exists: {expected_path}")
            audio_path = expected_path
        else:
            click.echo("Downloading audio...")
            audio_path = downloader.download_audio(input_source, filename=output)
            click.echo(f"Downloaded to: {audio_path}\n")
    
    # Identify interviewer segments
    click.echo("\n" + "="*60)
    click.echo("STEP 2: Identifying speakers")
    click.echo("="*60)
    diarizer = SpeakerDiarizer(hf_token=token)
    
    detection_method = cfg['speaker'].get('detection_method', 'duration')
    num_speakers = cfg['speaker'].get('num_speakers', 2)
    
    click.echo(f"Detection method: {detection_method}")
    click.echo(f"Number of speakers: {num_speakers}")
    
    timestamps = diarizer.get_speaker_timestamps(
        audio_path,
        num_speakers=num_speakers,
        detection_method=detection_method
    )
    
    click.echo(f"\nFound {len(timestamps)} segments to remove")
    total_removed = sum(end - start for start, end in timestamps)
    click.echo(f"Total time to remove: {total_removed:.2f} seconds ({total_removed/60:.2f} minutes)\n")
    
    # Process audio
    click.echo("="*60)
    click.echo("STEP 3: Processing and cutting audio")
    click.echo("="*60)
    
    output_filename = output or video_info['title']
    output_filename = "".join(c for c in output_filename if c.isalnum() or c in (' ', '-', '_'))
    output_filename = output_filename.strip().replace(' ', '_')
    
    # Build output path robustly
    pattern = cfg['output'].get('filename_pattern', '{original_name}_clean')
    base_name = pattern.format(original_name=output_filename)
    output_path = Path(f"{base_name}.mp3")
    
    processor = AudioProcessor(sample_rate=22050)
    
    try:
        processor.process_audio(
            audio_path=audio_path,
            timestamps_to_remove=timestamps,
            output_path=output_path,
            normalize=cfg['output'].get('normalize_audio', True),
            smooth_transition=cfg['processing'].get('transition_smooth', 0.1)
        )
        
        click.echo("\n" + "="*60)
        click.echo("COMPLETE!")
        click.echo("="*60)
        click.echo(f"Cleaned audio saved to: {output_path}")
        click.echo(f"File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    except Exception as e:
        click.echo(f"\nError processing audio: {e}", err=True)
        raise


if __name__ == '__main__':
    main()

