"""YouTube video downloader module."""

import os
import yt_dlp
from pathlib import Path
from typing import Optional


class YouTubeDownloader:
    """Downloads YouTube videos and extracts audio."""
    
    def __init__(self, output_dir: str = "downloads"):
        """Initialize downloader.
        
        Args:
            output_dir: Directory to save downloaded files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def download_audio(self, url: str, filename: Optional[str] = None) -> Path:
        """Download audio from YouTube video.
        
        Args:
            url: YouTube video URL
            filename: Optional custom filename (without extension)
            
        Returns:
            Path to downloaded audio file
        """
        try:
            # Prepare output path
            if filename is None:
                filename = "%(title)s"
            
            output_template = str(self.output_dir / f"{filename}.%(ext)s")
            
            # Configure yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': output_template,
                'quiet': False,
                'noprogress': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download
                info = ydl.extract_info(url, download=True)
                
                # Get the actual downloaded file path
                title = info.get('title', 'video')
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
                safe_title = safe_title.strip().replace(' ', '_')
                
                downloaded_file = self.output_dir / f"{safe_title}.mp3"
                
                return downloaded_file
                
        except Exception as e:
            raise RuntimeError(f"Failed to download video: {e}")
    
    def get_video_info(self, url: str) -> dict:
        """Get information about a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dict with video information
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "title": info.get('title', 'Unknown'),
                    "author": info.get('uploader', 'Unknown'),
                    "length": info.get('duration', 0),
                    "thumbnail": info.get('thumbnail', ''),
                    "description": info.get('description', '')[:500] if info.get('description') else ""
                }
        except Exception as e:
            raise RuntimeError(f"Failed to get video info: {e}")

