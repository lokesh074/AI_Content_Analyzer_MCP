
from youtube_transcript_api import YouTubeTranscriptApi
import re

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?]*)',
        r'youtube\.com\/embed\/([^&\n?]*)',
        r'youtube\.com\/v\/([^&\n?]*)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL")

def extract_yt_transcript(video_url):       # Extract video ID and get transcript
        video_id = extract_video_id(video_url)
        print("video ID : ",video_id)
        obj=YouTubeTranscriptApi()
        transcript_list = obj.fetch(video_id, languages=["en", "hi"]) 
        # for snippet in transcript_list:
        #         print(snippet.text)
        # Combine transcript into full text
        full_transcript = " ".join([entry.text for entry in transcript_list])
        return full_transcript