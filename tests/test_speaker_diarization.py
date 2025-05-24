import unittest
import os
import tempfile
import shutil
import pysrt
from pathlib import Path

# Add parent directory to path to import the backend modules
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.processing_service import diarize_speakers, _basic_dialogue_detection, _time_to_seconds, _apply_diarization_from_transcript


class TestSpeakerDiarization(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a sample subtitle file
        self.sample_srt = pysrt.SubRipFile()
        
        # Add some sample subtitle entries with dialogue patterns
        self.sample_srt.append(pysrt.SubRipItem(
            index=1,
            start=pysrt.SubRipTime(0, 0, 1, 0),
            end=pysrt.SubRipTime(0, 0, 5, 0),
            text="Hello, how are you today?"
        ))
        
        self.sample_srt.append(pysrt.SubRipItem(
            index=2,
            start=pysrt.SubRipTime(0, 0, 6, 0),
            end=pysrt.SubRipTime(0, 0, 10, 0),
            text="- I'm doing well, thank you."
        ))
        
        self.sample_srt.append(pysrt.SubRipItem(
            index=3,
            start=pysrt.SubRipTime(0, 0, 11, 0),
            end=pysrt.SubRipTime(0, 0, 15, 0),
            text="- That's great to hear!\n- Yes, it's a beautiful day."
        ))
        
        # Save the sample SRT file
        self.srt_path = os.path.join(self.temp_dir, "sample.srt")
        self.sample_srt.save(self.srt_path, encoding='utf-8')
        
        # Create a mock video file (empty file for testing purposes)
        self.video_path = os.path.join(self.temp_dir, "sample.mp4")
        with open(self.video_path, 'w') as f:
            f.write("mock video content")

    def tearDown(self):
        # Clean up temp directory
        shutil.rmtree(self.temp_dir)

    def test_basic_dialogue_detection(self):
        """Test the basic dialogue detection logic"""
        # Run the basic detection
        result = _basic_dialogue_detection(self.sample_srt)
        
        # Check if dashes were added correctly
        self.assertTrue(result[0].text == "Hello, how are you today?")  # No change expected
        self.assertTrue(result[1].text.startswith("--"))  # Should add double dash
        
        # Check multi-line dialogue
        lines = result[2].text.split("\n")
        self.assertTrue(all(line.startswith("--") for line in lines))
        
    def test_time_to_seconds_conversion(self):
        """Test the time conversion function"""
        time_obj = pysrt.SubRipTime(0, 1, 30, 500)  # 0h, 1m, 30s, 500ms
        seconds = _time_to_seconds(time_obj)
        self.assertEqual(seconds, 90.5)
        
    def test_apply_diarization_from_transcript(self):
        """Test applying diarization from a transcript"""
        # Create a mock transcript response similar to what AWS would return
        mock_transcript = {
            "results": {
                "speaker_labels": {
                    "segments": [
                        {
                            "speaker_label": "spk_0",
                            "start_time": "1.0",
                            "end_time": "5.0"
                        },
                        {
                            "speaker_label": "spk_1",
                            "start_time": "6.0",
                            "end_time": "10.0"
                        },
                        {
                            "speaker_label": "spk_0",
                            "start_time": "11.0",
                            "end_time": "13.0"
                        },
                        {
                            "speaker_label": "spk_1",
                            "start_time": "13.0",
                            "end_time": "15.0"
                        }
                    ]
                }
            }
        }
        
        # Apply the diarization
        result = _apply_diarization_from_transcript(self.sample_srt, mock_transcript)
        
        # Check if speaker labels were added correctly
        self.assertTrue("[spk_0]" in result[0].text)
        self.assertTrue("[spk_1]" in result[1].text)
        
        # For the third subtitle, both speakers should be tagged in the right places
        self.assertTrue("[spk_0]" in result[2].text or "[spk_1]" in result[2].text)


if __name__ == "__main__":
    unittest.main()
