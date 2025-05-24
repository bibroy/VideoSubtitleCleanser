import pytest
import os
import sys
import uuid
from pathlib import Path

# Add the parent directory to the path so we can import from the backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services import processing_service, subtitle_service
from backend.utils import file_utils

# Sample SRT content for testing
SAMPLE_SRT_CONTENT = """1
00:00:01,000 --> 00:00:04,000
This is the first subtitle.

2
00:00:05,000 --> 00:00:09,000
This is the second subtitle
with multiple lines.

3
00:00:10,000 --> 00:00:14,000
This subtitle has "quotes" and special characters: é à ç.
"""

@pytest.fixture
def temp_subtitle_file():
    """Create a temporary subtitle file for testing."""
    # Generate a unique task_id for this test
    task_id = str(uuid.uuid4())
    
    # Create the uploads directory if it doesn't exist
    os.makedirs('data/uploads', exist_ok=True)
    
    # Write the sample SRT content to the file
    file_path = f'data/uploads/{task_id}.srt'
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(SAMPLE_SRT_CONTENT)
    
    yield task_id
    
    # Clean up after the test
    try:
        os.remove(file_path)
    except:
        pass

def test_load_subtitles(temp_subtitle_file):
    """Test loading a subtitle file."""
    # Get path to the subtitle file
    subtitle_path = subtitle_service.get_subtitle_path(temp_subtitle_file)
    assert subtitle_path is not None
    
    # Load the subtitles
    subs = processing_service.load_subtitles(subtitle_path)
    assert subs is not None
    assert len(subs) == 3

def test_remove_invalid_characters():
    """Test removing invalid characters from subtitles."""
    # Create a sample subtitle object with some invalid characters
    from pysrt import SubRipFile, SubRipItem
    
    subs = SubRipFile()
    subs.append(SubRipItem(1, start='00:00:01,000', end='00:00:04,000', text='This has \x07 control \x1F characters.'))
    
    # Process the subtitles
    cleaned_subs = processing_service.remove_invalid_characters(subs)
    
    # Verify the results
    assert '\x07' not in cleaned_subs[0].text
    assert '\x1F' not in cleaned_subs[0].text

def test_remove_duplicate_lines():
    """Test removing duplicate lines from subtitles."""
    # Create a sample subtitle object with duplicate lines
    from pysrt import SubRipFile, SubRipItem
    
    subs = SubRipFile()
    subs.append(SubRipItem(1, start='00:00:01,000', end='00:00:04,000', 
                          text='This is a line.\nThis is a line.\nThis is another line.'))
    
    # Process the subtitles
    cleaned_subs = processing_service.remove_duplicate_lines(subs)
    
    # Verify the results
    expected_text = 'This is a line.\nThis is another line.'
    assert cleaned_subs[0].text == expected_text

def test_analyze_subtitle(temp_subtitle_file):
    """Test analyzing a subtitle file."""
    # Analyze the subtitle file
    analysis = processing_service.analyze_subtitle(temp_subtitle_file)
    
    # Verify the results
    assert 'statistics' in analysis
    assert 'total_subtitles' in analysis['statistics']
    assert analysis['statistics']['total_subtitles'] == 3

def test_timestamp_utils():
    """Test the timestamp utility functions."""
    # Test parsing a timestamp string to milliseconds
    ms = file_utils.parse_timestamp('01:30:45,500')
    assert ms == 5445500  # 1h 30m 45s 500ms = 5445500ms
    
    # Test formatting milliseconds to a timestamp string
    ts = file_utils.format_timestamp(5445500)
    assert ts == '01:30:45,500'
