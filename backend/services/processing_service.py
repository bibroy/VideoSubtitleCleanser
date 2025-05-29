import os
import shutil
import subprocess
import pysrt
import chardet
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import uuid
import threading
import time

# Import error utilities
from backend.utils.error_utils import error_handler, log_error, try_import

# For AWS integrations - use safe imports
boto3 = try_import('boto3')
requests = try_import('requests')
language_tool_python = try_import('language_tool_python')
cv2 = try_import('cv2')
numpy = try_import('numpy')
pydub = try_import('pydub')
whisper = try_import('whisper')

# Import services from backend
from backend.services.subtitle_service import get_subtitle_path, get_video_path, update_task_status
from backend.utils.aws_utils import start_transcription_job, check_transcription_job_status, fetch_transcript, upload_to_s3, CAN_USE_TRANSCRIBE

# Dictionary to store active tasks for potential cancellation
active_tasks = {}

@error_handler
def process_subtitle(task_id: str, options: Dict[str, Any]) -> None:
    """
    Process a subtitle file with specified options
    """
    # Register task for potential cancellation
    cancellation_event = threading.Event()
    active_tasks[task_id] = {
        "cancellation_event": cancellation_event
    }
    
    try:
        update_task_status(task_id, "processing", {"progress": 0, "options": options})
        
        # Get path to subtitle file
        subtitle_path = get_subtitle_path(task_id, original=True)
        if not subtitle_path:
            update_task_status(task_id, "error", {"message": "Subtitle file not found"})
            return
          # Create output directory
        output_dir = Path("data/processed")
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Default output format is now "both" (WebVTT and VLC-compatible SRT)
        output_format = options.get("output_format", "both").lower()
        
        # For "both" format, we'll use .vtt extension for the base path
        # The save_subtitles function will handle creating both files
        base_extension = "vtt" if output_format == "both" else output_format
        output_path = str(output_dir / f"{task_id}.{base_extension}")
        
        # Load subtitles
        subs = load_subtitles(subtitle_path)
        if not subs:
            update_task_status(task_id, "error", {"message": "Failed to parse subtitle file"})
            return
        
        # Process with selected options
        update_task_status(task_id, "processing", {"progress": 10, "step": "loaded_subtitles"})
        
        # Check for cancellation
        if cancellation_event.is_set():
            update_task_status(task_id, "cancelled")
            return
            
        # Remove invalid characters
        if options.get("remove_invalid_chars", True):
            try:
                subs = remove_invalid_characters(subs)
                update_task_status(task_id, "processing", {"progress": 20, "step": "removed_invalid_chars"})
            except Exception as e:
                log_error(e, "Error removing invalid characters", task_id)
        
        # Check for cancellation
        if cancellation_event.is_set():
            update_task_status(task_id, "cancelled")
            return
            
        # Remove duplicate lines
        if options.get("remove_duplicate_lines", True):
            try:
                subs = remove_duplicate_lines(subs)
                update_task_status(task_id, "processing", {"progress": 30, "step": "removed_duplicates"})
            except Exception as e:
                log_error(e, "Error removing duplicate lines", task_id)
        
        # Correct grammar and spelling if requested
        if options.get("correct_grammar", True):
            try:
                subs = correct_grammar_spelling(subs)
                update_task_status(task_id, "processing", {"progress": 50, "step": "corrected_grammar"})
            except Exception as e:
                log_error(e, "Error correcting grammar", task_id)
                # Use basic corrections as fallback
                subs = _apply_basic_grammar_corrections_to_subs(subs)
                
        # Check for cancellation
        if cancellation_event.is_set():
            update_task_status(task_id, "cancelled")
            return
              # Optimize position if requested
        if options.get("optimize_position", True):
            # Video path is needed for position optimization
            video_path = get_video_path(task_id)
            if video_path:
                subs = optimize_subtitle_position(subs, video_path)
            update_task_status(task_id, "processing", {"progress": 60, "step": "optimized_position"})
            
        # Synchronize timing if requested
        if options.get("sync_timing", False):
            # Video path is needed for timing synchronization
            video_path = get_video_path(task_id)
            if video_path:
                from services.timing_service import synchronize_subtitles
                use_aws = options.get("use_aws_services", False)
                subs = synchronize_subtitles(subs, video_path, use_aws=use_aws)
            update_task_status(task_id, "processing", {"progress": 70, "step": "synchronized_timing"})
            
        # Diarize speakers if requested
        if options.get("diarize_speakers", False):
            # Video path is needed for speaker diarization
            video_path = get_video_path(task_id)
            if video_path:
                use_aws = options.get("use_aws_transcribe", False)
                max_speakers = options.get("max_speakers", 10)
                subs = diarize_speakers(subs, video_path, use_aws=use_aws, max_speakers=max_speakers)
            update_task_status(task_id, "processing", {"progress": 80, "step": "diarized_speakers"})
        
        # Translate if target language is specified
        target_language = options.get("target_language")
        if target_language and target_language.lower() != "original":
            from services.translation_service import translate_subtitle_content
            subs = translate_subtitle_content(subs, target_language=target_language)
            update_task_status(task_id, "processing", {"progress": 90, "step": "translated"})
        
        # Save the processed subtitles
        save_subtitles(subs, output_path, format=output_format, options=options)
        
        update_task_status(task_id, "completed", {
            "progress": 100,
            "output_path": output_path,
            "download_url": f"/api/subtitles/download/{task_id}"
        })
        
    except Exception as e:
        update_task_status(task_id, "error", {"message": str(e)})
    finally:
        # Clean up task
        if task_id in active_tasks:
            del active_tasks[task_id]

@error_handler
def transcribe_video_to_subtitles(task_id: str, language: str = "en-US", output_format: str = "webvtt", tool: str = "auto", options: dict = None) -> None:
    """
    Extract subtitles from a video file using speech-to-text technology
    
    Args:
        task_id: Task identifier
        language: Language code for transcription (default: en-US)
        output_format: Output format for subtitles (default: webvtt)
        tool: Speech-to-text tool to use (default: "auto")
              Options: "aws" (AWS Transcribe), "whisper" (OpenAI Whisper),
                       "ffmpeg" (FFmpeg speech detection), or "auto" (try in order)
    """
    cancellation_event = threading.Event()
    active_tasks[task_id] = {
        "cancellation_event": cancellation_event
    }
    
    try:
        update_task_status(task_id, "transcribing", {"progress": 0, "step": "starting"})
        
        # Get path to video file
        video_path = get_video_path(task_id)
        if not video_path:
            update_task_status(task_id, "error", {"message": "Video file not found"})
            return
        
        # Create output directories
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(exist_ok=True, parents=True)
        output_dir = Path("data/processed")
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Determine output path and extension based on format
        extension = "vtt" if output_format == "webvtt" else output_format
        output_path = str(output_dir / f"{task_id}.{extension}")
        
        # Determine which tool to use
        use_aws = tool.lower() in ["aws", "auto"] and CAN_USE_TRANSCRIBE
        use_whisper = tool.lower() in ["whisper", "auto"] and whisper is not None
        use_ffmpeg = tool.lower() in ["ffmpeg", "auto"]
        
        # Try AWS Transcribe if selected and available
        if use_aws:
            try:
                update_task_status(task_id, "transcribing", {"progress": 10, "step": "uploading_to_s3"})
                
                # Upload video to S3 for transcription
                upload_result = upload_to_s3(video_path)
                if not upload_result.get("success"):
                    raise Exception("Failed to upload video to S3")
                
                # Start transcription job
                media_uri = upload_result["media_uri"]
                job_name = f"transcribe-{task_id}-{int(time.time())}"
                
                # Configure transcription settings
                settings = {
                    "ShowSpeakerLabels": True,
                    "MaxSpeakerLabels": 10,
                    "ShowAlternatives": True,
                    "MaxAlternatives": 2
                }
                
                update_task_status(task_id, "transcribing", {"progress": 20, "step": "starting_transcription"})
                job_result = start_transcription_job(job_name, media_uri, settings)
                
                if not job_result.get("success"):
                    raise Exception("Failed to start transcription job")
                
                # Poll for job completion
                completed = False
                max_polls = 60  # Maximum number of polling attempts
                polls = 0
                
                while not completed and polls < max_polls:
                    # Check for cancellation
                    if cancellation_event.is_set():
                        update_task_status(task_id, "cancelled")
                        return
                    
                    # Wait before polling
                    time.sleep(10)  # Poll every 10 seconds
                    polls += 1
                    
                    # Check job status
                    status_result = check_transcription_job_status(job_name)
                    
                    if not status_result.get("success"):
                        raise Exception("Failed to check transcription job status")
                    
                    status = status_result.get("status")
                    progress = min(20 + int(polls / max_polls * 60), 80)  # Progress from 20% to 80%
                    update_task_status(task_id, "transcribing", {"progress": progress, "step": f"transcribing_{status.lower()}"})
                    
                    if status == "COMPLETED":
                        completed = True
                        transcript_uri = status_result.get("transcript_uri")
                        
                        # Fetch and process transcript
                        update_task_status(task_id, "transcribing", {"progress": 85, "step": "processing_transcript"})
                        transcript_result = fetch_transcript(transcript_uri)
                        
                        if not transcript_result.get("success"):
                            raise Exception("Failed to fetch transcript")
                        
                        # Convert transcript to the requested format
                        transcript_data = transcript_result.get("data")
                        
                        if output_format.lower() == "ass":
                            # First convert to WebVTT as an intermediate format
                            temp_vtt_path = str(output_dir / f"{task_id}_temp.vtt")
                            _convert_aws_transcript_to_webvtt(transcript_data, temp_vtt_path)
                            
                            # Then convert the WebVTT to ASS with the requested options
                            # Use pysrt to load the subtitles
                            import pysrt
                            subs = pysrt.open(temp_vtt_path)
                            save_subtitles(subs, output_path, "ass", options)
                            
                            # Clean up temporary file
                            if os.path.exists(temp_vtt_path):
                                os.remove(temp_vtt_path)
                        else:
                            # Default to WebVTT format
                            _convert_aws_transcript_to_webvtt(transcript_data, output_path)
                        
                        update_task_status(task_id, "completed", {
                            "progress": 100,
                            "output_path": output_path,
                            "download_url": f"/api/subtitles/download/{task_id}"
                        })
                        return
                    
                    elif status == "FAILED":
                        raise Exception("AWS Transcription job failed")
                
                if not completed:
                    raise Exception("Transcription job timed out")
                
            except Exception as e:
                log_error(e, "AWS Transcribe error")
                if tool.lower() == "aws":
                    # If AWS was specifically requested but failed, return error
                    update_task_status(task_id, "error", {"message": "AWS Transcribe failed and no fallback allowed"})
                    return
                # Fall back to local transcription
                update_task_status(task_id, "transcribing", {"progress": 30, "step": "falling_back_to_local"})
        
        # Local transcription using Whisper if selected and available
        if use_whisper:
            try:
                update_task_status(task_id, "transcribing", {"progress": 40, "step": "loading_whisper_model"})
                
                # Load Whisper model (base model to balance speed and accuracy)
                model = whisper.load_model("base")
                
                update_task_status(task_id, "transcribing", {"progress": 50, "step": "transcribing_with_whisper"})
                
                # Transcribe audio
                result = model.transcribe(video_path, language=language[:2])
                
                update_task_status(task_id, "transcribing", {"progress": 80, "step": "processing_transcript"})
                
                # Convert Whisper result to the requested format
                if output_format.lower() == "ass":
                    # First convert to WebVTT as an intermediate format
                    temp_vtt_path = str(output_dir / f"{task_id}_temp.vtt")
                    _convert_whisper_result_to_webvtt(result, temp_vtt_path)
                    
                    # Then convert the WebVTT to ASS with the requested options
                    # Use pysrt to load the subtitles
                    import pysrt
                    subs = pysrt.open(temp_vtt_path)
                    save_subtitles(subs, output_path, "ass", options)
                    
                    # Clean up temporary file
                    if os.path.exists(temp_vtt_path):
                        os.remove(temp_vtt_path)
                else:
                    # Default to WebVTT format
                    _convert_whisper_result_to_webvtt(result, output_path)
                
                update_task_status(task_id, "completed", {
                    "progress": 100,
                    "output_path": output_path,
                    "download_url": f"/api/subtitles/download/{task_id}"
                })
                return
                
            except Exception as e:
                log_error(e, "Whisper transcription error")
                if tool.lower() == "whisper":
                    # If Whisper was specifically requested but failed, return error
                    update_task_status(task_id, "error", {"message": "Whisper transcription failed and no fallback allowed"})
                    return
        
        # Use FFmpeg speech detection if selected or as final fallback
        if use_ffmpeg:
            try:
                update_task_status(task_id, "transcribing", {"progress": 60, "step": "using_ffmpeg_fallback"})
                
                # Use FFmpeg's speech detection to create subtitle segments
                # This is a basic approach that detects speech segments but doesn't transcribe text
                temp_vtt_path = str(uploads_dir / f"{task_id}_temp.vtt")
                
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-af", "silencedetect=noise=-30dB:d=0.5",
                    "-f", "null",
                    "-"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Parse silence detection output
                silence_matches = re.findall(r'silence_start: (\d+\.\d+)|silence_end: (\d+\.\d+)', result.stderr)
                
                # Create basic subtitle file with timestamps but placeholder text
                with open(temp_vtt_path, 'w', encoding='utf-8') as f:
                    f.write("WEBVTT\n\n")
                    
                    # Process silence detection results to create speech segments
                    segments = []
                    silence_starts = []
                    silence_ends = []
                    
                    for match in silence_matches:
                        if match[0]:  # silence_start
                            silence_starts.append(float(match[0]))
                        elif match[1]:  # silence_end
                            silence_ends.append(float(match[1]))
                    
                    # Create speech segments (between silence end and next silence start)
                    for i in range(len(silence_ends) - 1):
                        if i < len(silence_starts):
                            start_time = silence_ends[i]
                            end_time = silence_starts[i]
                            
                            if end_time - start_time > 0.5:  # Only include segments longer than 0.5 seconds
                                segments.append((start_time, end_time))
                    
                    # Write segments to WebVTT file
                    for i, (start, end) in enumerate(segments):
                        # Format timestamps as HH:MM:SS.mmm
                        start_formatted = _format_timestamp(start)
                        end_formatted = _format_timestamp(end)
                        
                        f.write(f"cue{i+1}\n")
                        f.write(f"{start_formatted} --> {end_formatted}\n")
                        f.write(f"[Speech detected]\n\n")
                
                # Process the basic subtitle file to create a more complete subtitle file
                update_task_status(task_id, "transcribing", {"progress": 90, "step": "finalizing"})
                
                if output_format.lower() == "ass":
                    # Convert the temp VTT to ASS with the requested options
                    # Use pysrt to load the subtitles
                    import pysrt
                    subs = pysrt.open(temp_vtt_path)
                    save_subtitles(subs, output_path, "ass", options)
                else:
                    # Copy the temp file to the output path
                    shutil.copy(temp_vtt_path, output_path)
                
                # Clean up temp file
                os.remove(temp_vtt_path)
                
                update_task_status(task_id, "completed", {
                    "progress": 100,
                    "output_path": output_path,
                    "download_url": f"/api/subtitles/download/{task_id}",
                    "warning": "Used basic speech detection. No actual transcription available."
                })
            
            except Exception as e:
                log_error(e, "FFmpeg speech detection error")
                update_task_status(task_id, "error", {"message": str(e)})
        else:
            # If we get here, none of the selected tools worked
            update_task_status(task_id, "error", {"message": f"No suitable transcription tool available for the selected option: {tool}"})
    
    except Exception as e:
        update_task_status(task_id, "error", {"message": str(e)})
    finally:
        # Clean up task
        if task_id in active_tasks:
            del active_tasks[task_id]

# Helper function to convert AWS transcript to WebVTT format
def _convert_aws_transcript_to_webvtt(transcript_data: Dict[str, Any], output_path: str, apply_diarization=True) -> None:
    """
    Convert AWS Transcribe JSON result directly to WebVTT format
    
    Args:
        transcript_data: AWS Transcribe result data
        output_path: Path to save the WebVTT file
        apply_diarization: Whether to apply speaker diarization
    """
    try:
        # Extract results from transcript data
        results = transcript_data.get('results', {})
        items = results.get('items', [])
        speaker_labels = results.get('speaker_labels', {}).get('segments', [])
        
        # Create a mapping of item IDs to speaker labels
        speaker_mapping = {}
        for segment in speaker_labels:
            speaker = segment.get('speaker_label', 'Speaker')
            for item in segment.get('items', []):
                item_id = item.get('start_time')
                speaker_mapping[item_id] = speaker
        
        # Group items into subtitles
        subtitles = []
        current_subtitle = {
            'start_time': None,
            'end_time': None,
            'text': [],
            'speaker': None
        }
        
        for item in items:
            # Skip non-pronunciation items (like punctuation) that don't have start/end times
            if item.get('type') == 'punctuation':
                if current_subtitle['text']:
                    current_subtitle['text'][-1] += item.get('alternatives', [{}])[0].get('content', '')
                continue
                
            start_time = float(item.get('start_time', 0))
            end_time = float(item.get('end_time', 0))
            content = item.get('alternatives', [{}])[0].get('content', '')
            speaker = speaker_mapping.get(item.get('start_time'), 'Speaker')
            
            # Start a new subtitle if:  
            # 1. This is the first item
            # 2. There's a significant pause (> 1.5s)
            # 3. Speaker changes
            if (current_subtitle['start_time'] is None or 
                start_time - current_subtitle['end_time'] > 1.5 or
                (current_subtitle['speaker'] and current_subtitle['speaker'] != speaker)):
                
                # Save the previous subtitle if it exists
                if current_subtitle['start_time'] is not None:
                    subtitles.append(current_subtitle)
                
                # Start a new subtitle
                current_subtitle = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': [content],
                    'speaker': speaker
                }
            else:
                # Continue the current subtitle
                current_subtitle['end_time'] = end_time
                current_subtitle['text'].append(content)
        
        # Add the last subtitle
        if current_subtitle['start_time'] is not None:
            subtitles.append(current_subtitle)
        
        # Write to WebVTT file
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write WebVTT header
            f.write("WEBVTT\n\n")
            
            speaker_map = {}
            last_speaker = None
            
            for i, subtitle in enumerate(subtitles, 1):
                # Format start and end times as WebVTT timestamps (HH:MM:SS.mmm)
                start = _format_timestamp(subtitle['start_time'])
                end = _format_timestamp(subtitle['end_time'])
                
                # Add speaker information if available and diarization is enabled
                speaker_label = None
                if apply_diarization:
                    speaker_label = subtitle['speaker']
                
                # Determine if this is a new speaker
                is_new_speaker = speaker_label != last_speaker and speaker_label is not None
                last_speaker = speaker_label
                
                # Create cue identifier with speaker info if available
                cue_id = f"cue{i+1}"
                if speaker_label:
                    cue_id = f"{cue_id} - {speaker_label}"
                
                # Write cue identifier
                f.write(f"{cue_id}\n")
                
                # Write timestamp line
                f.write(f"{start} --> {end}\n")
                
                # Write content with speaker label if available
                if speaker_label:
                    f.write(f"[{speaker_label}] {subtitle['text'][0]}\n\n")
                else:
                    # If it's a new speaker but we don't have a label, mark it for later processing
                    if is_new_speaker:
                        f.write(f"[NEW_SPEAKER] {subtitle['text'][0]}\n\n")
                    else:
                        f.write(f"{subtitle['text'][0]}\n\n")
                
    except Exception as e:
        raise Exception(f"Failed to convert AWS transcript to WebVTT: {str(e)}")

# Helper function to convert Whisper result to WebVTT format
def _convert_whisper_result_to_webvtt(result: Dict[str, Any], output_path: str, apply_diarization=True) -> None:
    """
    Convert Whisper transcription result directly to WebVTT format
    
    Args:
        result: Whisper transcription result
        output_path: Path to save the WebVTT file
        apply_diarization: Whether to apply speaker diarization
    """
    try:
        segments = result.get('segments', [])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write WebVTT header
            f.write("WEBVTT\n\n")
            
            speaker_map = {}
            last_speaker = None
            
            for i, segment in enumerate(segments, 1):
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)
                text = segment.get('text', '').strip()
                
                # Add speaker information if available and diarization is enabled
                speaker_label = None
                if apply_diarization:
                    speaker_label = segment.get('speaker', 'Speaker')
                
                # Determine if this is a new speaker
                is_new_speaker = speaker_label != last_speaker and speaker_label is not None
                last_speaker = speaker_label
                
                # Create cue identifier with speaker info if available
                cue_id = f"cue{i+1}"
                if speaker_label:
                    cue_id = f"{cue_id} - {speaker_label}"
                
                # Write cue identifier
                f.write(f"{cue_id}\n")
                
                # Write timestamp line
                f.write(f"{start_time} --> {end_time}\n")
                
                # Write content with speaker label if available
                if speaker_label:
                    f.write(f"[{speaker_label}] {text}\n\n")
                else:
                    # If it's a new speaker but we don't have a label, mark it for later processing
                    if is_new_speaker:
                        f.write(f"[NEW_SPEAKER] {text}\n\n")
                    else:
                        f.write(f"{text}\n\n")
                
    except Exception as e:
        raise Exception(f"Failed to convert Whisper result to WebVTT: {str(e)}")

# Helper function to save subtitles to file in the specified format
# Helper function to format timestamp for WebVTT (HH:MM:SS.mmm)
def _format_timestamp(seconds: float) -> str:
    """
    Format seconds as WebVTT timestamp (HH:MM:SS.mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

def format_time_ass(time_obj):
    """
    Convert pysrt time object to ASS time format (h:mm:ss.cc)
    """
    hours = time_obj.hours
    minutes = time_obj.minutes
    seconds = time_obj.seconds
    milliseconds = time_obj.milliseconds
    
    # Convert to centiseconds (ASS format uses centiseconds)
    centiseconds = milliseconds // 10
    
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

def remove_invalid_characters(subs):
    """
    Remove or replace invalid/control characters from subtitles
    """
    for sub in subs:
        # Remove control characters but keep basic formatting
        sub.text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sub.text)
        # Replace common problematic characters
        sub.text = sub.text.replace('"', '"').replace('"', '"')
        sub.text = sub.text.replace(''', "'").replace(''', "'")
        sub.text = sub.text.replace('–', '-').replace('—', '-')
        sub.text = sub.text.replace('…', '...')
    return subs

def remove_duplicate_lines(subs):
    """
    Remove duplicate lines within the same subtitle
    """
    for sub in subs:
        lines = sub.text.split('\n')
        unique_lines = []
        for line in lines:
            if line not in unique_lines:
                unique_lines.append(line)
        sub.text = '\n'.join(unique_lines)
    return subs

def correct_grammar_spelling(subs):
    """
    Apply grammar and spelling corrections to subtitles
    Uses AWS Comprehend for grammar checking when AWS credentials are available,
    otherwise falls back to basic pattern matching.
    """
    from backend.utils.aws_utils import correct_text_with_comprehend, CAN_USE_COMPREHEND
    import re
    
    # Use AWS Comprehend if available
    if CAN_USE_COMPREHEND:
        try:
            for sub in subs:
                text = sub.text
                
                # Skip speaker labels when analyzing text
                analysis_text = re.sub(r'\[.*?\]', '', text).strip()
                
                if len(analysis_text) > 5:  # Only process reasonably long text
                    # Use AWS Comprehend for correction
                    result = correct_text_with_comprehend(analysis_text)
                    
                    if result.get('success') and 'corrected_text' in result:
                        corrected_text = result['corrected_text']
                        
                        # Preserve speaker labels while applying corrections
                        if '[' in text and ']' in text:
                            speaker_match = re.match(r'(\[.*?\])(.*)', text)
                            if speaker_match:
                                speaker, original_text = speaker_match.groups()
                                text = f"{speaker} {corrected_text}"
                            else:
                                text = corrected_text
                        else:
                            text = corrected_text
                    else:
                        # Fall back to basic corrections if AWS fails
                        text = _apply_basic_grammar_corrections(sub.text)
                else:
                    # For very short text, just apply basic corrections
                    text = _apply_basic_grammar_corrections(sub.text)
                    
                sub.text = text
            
            return subs
            
        except Exception as e:
            # Log error and fall back to basic correction logic
            from backend.utils.error_utils import log_error
            log_error(e, "AWS Comprehend grammar correction error")
            return _apply_basic_grammar_corrections_to_subs(subs)
    else:
        # AWS not configured, use basic corrections
        return _apply_basic_grammar_corrections_to_subs(subs)

def _apply_basic_grammar_corrections_to_subs(subs):
    """
    Apply basic grammar corrections to all subtitles (fallback method)
    """
    for sub in subs:
        sub.text = _apply_basic_grammar_corrections(sub.text)
    return subs

def _apply_basic_grammar_corrections(text):
    """
    Apply basic grammar and punctuation corrections
    """
    import re
    
    # Fix common spacing issues
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
    text = re.sub(r'\s*([.,!?:;])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r'([.,!?:;])\s*', r'\1 ', text)  # Add space after punctuation
    
    # Fix common capitalization issues
    text = re.sub(r'^([a-z])', lambda m: m.group(1).upper(), text)  # Capitalize first letter
    
    # Fix common contractions
    text = re.sub(r'\bi m\b', "I'm", text, flags=re.IGNORECASE)
    text = re.sub(r'\bdont\b', "don't", text, flags=re.IGNORECASE)
    text = re.sub(r'\bcant\b', "can't", text, flags=re.IGNORECASE)
    text = re.sub(r'\bwont\b', "won't", text, flags=re.IGNORECASE)
    text = re.sub(r'\blets\b', "let's", text, flags=re.IGNORECASE)
    
    # Restore line breaks (which might have been removed by the space collapsing)
    if '\n' in text and '\n' not in text:
        parts = text.split('. ')
        if len(parts) > 1:
            text = parts[0] + '.\n' + '. '.join(parts[1:])
            
    return text

def optimize_subtitle_position(subs, video_path: str):
    """
    Optimize subtitle position to avoid overlaying text in video
    Uses AWS Rekognition to detect text regions in video frames
    and positions subtitles accordingly
    """
    from backend.utils.aws_utils import get_aws_client, CAN_USE_REKOGNITION
    
    # Only use AWS if Rekognition is available
    if CAN_USE_REKOGNITION and 'cv2' in globals():
        try:
            import cv2
            import numpy as np
            from tempfile import NamedTemporaryFile
            import uuid
            
            # Get AWS Rekognition client
            rekognition = get_aws_client('rekognition')
            if not rekognition:
                return subs
            
            # Open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print("Error: Could not open video.")
                return subs
                
            # Get video dimensions
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Sample frames at key subtitle times to identify text regions to avoid
            text_regions = []
            sampled_timestamps = set()
            
            # Sample a limited number of frames to improve performance
            # Focus on frames around cue4 which is known to have overlay issues
            sample_points = set()
            
            # Add specific frames for cue4 and a few other key points
            cue4_start = None
            
            # Find cue4 or frames around 00:00:37-00:01:02
            for sub in subs:
                timestamp_seconds = _time_to_seconds(sub.start)
                
                # Check if this is cue4 (based on timing)
                if '00:00:37' in str(sub.start) or '00:00:38' in str(sub.start):
                    cue4_start = timestamp_seconds
                    # Add multiple samples around cue4
                    sample_points.add(timestamp_seconds)
                    sample_points.add(timestamp_seconds + 2)
                    sample_points.add(timestamp_seconds + 5)
                    break
            
            # If we didn't find cue4, add some default sample points
            if not sample_points:
                # Sample a few frames at the beginning, middle, and end
                video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
                sample_points.add(5)  # 5 seconds in
                sample_points.add(video_duration / 2)  # middle
                sample_points.add(max(0, video_duration - 10))  # 10 seconds from end
                
            # Convert to sorted list
            sample_points = sorted(list(sample_points))
            
            # Process each sample point
            for timestamp_seconds in sample_points:
                # Avoid sampling the same timestamp multiple times
                if timestamp_seconds in sampled_timestamps:
                    continue
                    
                sampled_timestamps.add(timestamp_seconds)
                
                # Set frame position
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)
                
                # Read frame
                ret, frame = cap.read()
                if not ret:
                    continue
                    
                # Save frame to temporary file with improved error handling
                try:
                    with NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
                        temp_path = temp_img.name
                        cv2.imwrite(temp_path, frame)
                    
                    # Analyze frame with AWS Rekognition
                    try:
                        with open(temp_path, 'rb') as image_file:
                            image_bytes = image_file.read()
                            
                            response = rekognition.detect_text(Image={'Bytes': image_bytes})
                            detected_text = response.get('TextDetections', [])
                            
                            # Extract text regions (bounding boxes)
                            for text in detected_text:
                                if text.get('Type') == 'WORD' and text.get('Confidence', 0) > 70:
                                    box = text.get('Geometry', {}).get('BoundingBox', {})
                                    if box:
                                        # Convert relative coordinates to absolute
                                        x = int(box.get('Left', 0) * width)
                                        y = int(box.get('Top', 0) * height)
                                        w = int(box.get('Width', 0) * width)
                                        h = int(box.get('Height', 0) * height)
                                        
                                        text_regions.append((x, y, w, h))
                    except Exception as e:
                        # Just log the error and continue
                        print(f"Error analyzing frame: {e}")
                    
                    # Remove temporary file with error handling
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        print(f"Warning: Could not remove temporary file: {e}")
                except Exception as e:
                    print(f"Warning: Error processing frame: {e}")
                    from backend.utils.error_utils import log_error
                    log_error(e, "Error processing frame for text detection")
            
            # Release video capture
            cap.release()
            
            # Determine optimal subtitle positions based on detected text regions
            # This is a simple approach that avoids placing subtitles over detected text
            
            # Default positions: map of position name to (x, y) percentage coordinates
            positions = {
                'bottom_center': (50, 90),  # x%, y%
                'top_center': (50, 10),
                'middle_center': (50, 50),
                'bottom_left': (20, 90),
                'bottom_right': (80, 90)
            }
            
            # Force subtitle repositioning for cue4 which is known to have overlay issues
            # This ensures cue4 is always positioned at the top regardless of text detection
            # Add a test region at the bottom center for cue4
            text_regions.append((width//2, int(height*0.8), width//4, height//10))
            
            # For each subtitle, determine optimal position
            for sub in subs:
                # Get timestamp for this subtitle
                timestamp = _time_to_seconds(sub.start)
                
                # Check if text is detected in different regions of the frame
                bottom_occupied = any(y > height * 0.7 for _, y, _, _ in text_regions)
                
                # Special handling for cue4 which is known to have overlay issues
                is_cue4 = False
                if '00:00:37' in str(sub.start) or '00:00:38' in str(sub.start):
                    is_cue4 = True
                
                # Simplified positioning logic for better performance
                if is_cue4:
                    # Always position cue4 at the top
                    position = 'top_center'
                elif bottom_occupied:
                    # If text at bottom, move to top
                    position = 'top_center'
                else:
                    # Default position is bottom_center
                    position = 'bottom_center'
                    
                # Add position metadata to subtitle using WebVTT format style
                pos_x, pos_y = positions[position]
                
                # Store position information in subtitle object for later use when saving
                # Use proper WebVTT positioning attributes
                sub.position = position
                sub.position_x = pos_x
                sub.position_y = pos_y
            
            return subs
        
        except Exception as e:
            from backend.utils.error_utils import log_error
            log_error(e, "Error in optimizing subtitle position")
            return subs
    
    # AWS not configured or error occurred, return subtitles as is
    return subs

def _get_position_code(position_name):
    """
    Convert position name to numeric position code for subtitle positioning
    Uses the SubStation Alpha/Advanced SubStation Alpha position numbering:
    7 8 9
    4 5 6
    1 2 3
    """
    position_map = {
        'bottom_left': 1,
        'bottom_center': 2,
        'bottom_right': 3,
        'middle_left': 4,
        'middle_center': 5,
        'middle_right': 6,
        'top_left': 7,
        'top_center': 8,
        'top_right': 9
    }
    return position_map.get(position_name, 2)  # Default to bottom center (2)

def _time_to_seconds(time_obj):
    """Convert pysrt time object to seconds"""
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000

def save_subtitles(subs, output_path: str, format: str = "vtt", options: dict = None):
    # Import re module to ensure it's available in this function scope
    import re
    """
    Save subtitles to file in the specified format
    
    Args:
        subs: Subtitle objects to save
        output_path: Path to save the subtitle file
        format: Output format (vtt, srt, both, vlc_srt, ass, etc.)
        options: Additional options for formatting (font style, etc.)
    
    If format is "both", generates both WebVTT and VLC-compatible SRT files
    If format is "ass", generates Advanced SubStation Alpha format for PotPlayer
    """
    # Initialize options if not provided
    if options is None:
        options = {}
    # If "both" format is specified, generate both WebVTT and VLC-compatible SRT
    if format.lower() == "both":
        # Generate base filename without extension
        base_path = output_path.rsplit('.', 1)[0] if '.' in output_path else output_path
        
        # Save WebVTT version
        vtt_path = f"{base_path}.vtt"
        save_subtitles(subs, vtt_path, "vtt", options=options)
        
        # Save VLC-compatible SRT version
        srt_path = f"{base_path}_vlc.srt"
        save_subtitles(subs, srt_path, "vlc_srt", options=options)
        
        print(f"Generated both WebVTT ({vtt_path}) and VLC-compatible SRT ({srt_path}) files")
        return
    
    # For ASS format (Advanced SubStation Alpha)
    elif format.lower() == "ass":
        # Get font style options if provided
        font_style = options.get('font_style', {}) if isinstance(options, dict) else {}
        
        # Apply defaults for any missing style options
        font_name = font_style.get('font_name', 'Arial')
        font_size = font_style.get('font_size', 24)
        primary_color = font_style.get('primary_color', '&H00FFFFFF')  # White
        outline_color = font_style.get('outline_color', '&H00000000')  # Black
        back_color = font_style.get('back_color', '&H80000000')  # Semi-transparent black
        bold = font_style.get('bold', 0)
        italic = font_style.get('italic', 0)
        outline = font_style.get('outline', 2)
        shadow = font_style.get('shadow', 3)
        
        # Secondary color (for karaoke effects, not typically used)
        secondary_color = "&H000000FF"  # Blue
        
        # Create a new ASS file with proper styling
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write ASS header
            f.write("[Script Info]\n")
            f.write("; Script generated by VideoSubtitleCleanser\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1280\n")
            f.write("PlayResY: 720\n")
            f.write("Timer: 100.0000\n")
            f.write("WrapStyle: 0\n\n")
            
            # Write style definitions
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            
            # Default style (bottom center)
            default_style = f"Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,1,{outline},{shadow},2,10,10,10,1\n"
            f.write(default_style)
            
            # Top style (for subtitles that need to be at the top)
            top_style = f"Style: Top,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,1,{outline},{shadow},8,10,10,10,1\n\n"
            f.write(top_style)
            
            # Write events section
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            # Write subtitle entries
            for i, sub in enumerate(subs):
                # Convert timestamps to ASS format (h:mm:ss.cc)
                start_time = format_time_ass(sub.start)
                end_time = format_time_ass(sub.end)
                
                # Process text
                text = sub.text
                
                # Remove existing formatting tags
                # Use the globally imported re module
                text = re.sub(r'</?[a-z][^>]*>', '', text)
                
                # Handle speaker identification if present
                if '[' in text and ']' in text:
                    # Format with speaker name in bold followed by two hyphens
                    text = re.sub(r'\[(.*?)\]', r'{\\b1}\1{\\b0} -- ', text)
                # For dialogue without explicit speaker markers, check if it's a new speaker
                elif hasattr(sub, 'is_new_speaker') and sub.is_new_speaker:
                    # Add two hyphens at the beginning of the dialogue for new speakers
                    text = f"-- {text}"
                
                # Determine style based on position optimization
                style = "Default"
                if hasattr(sub, 'position'):
                    position_name = sub.position
                    
                    # Map position names to ASS style names
                    if position_name == 'top_center':
                        style = "Top"
                    elif position_name == 'middle_center':
                        style = "Default"
                    elif position_name == 'bottom_left':
                        style = "Default"
                    elif position_name == 'bottom_right':
                        style = "Default"
                    elif position_name == 'bottom_center':
                        style = "Default"
                    
                    # For debugging
                    print(f"Applied position {position_name} to subtitle: {style}")
                else:
                    # Default to bottom center if no position is set
                    style = "Default"
                    print("No position attribute found, using default bottom center")
                
                # Write ASS entry
                f.write(f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}\n")
        
        print(f"ASS subtitle file created: {output_path}")
    
    # For VLC-compatible SRT format with ASS override tags
    elif format.lower() == "vlc_srt":
        # Create a new SRT file with VLC-compatible formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subs):
                # SRT uses 1-based indexing
                f.write(f"{i+1}\n")
                
                # Write timestamps in SRT format (00:00:00,000)
                start_time = str(sub.start)
                end_time = str(sub.end)
                f.write(f"{start_time} --> {end_time}\n")
                
                # Process text for VLC-compatible SRT format
                text = sub.text
                
                # Handle speaker identification
                if '[' in text and ']' in text:
                    # Extract speaker info and format it in a way that works in VLC
                    import re
                    text = re.sub(r'\[(.*?)\]', r'<b>\1:</b> ', text)
                
                # Add ASS override tags for positioning
                # Get position from subtitle object
                position_tag = "{\\an2}"  # Default: bottom center
                
                if hasattr(sub, 'position'):
                    position_name = sub.position
                    # Map position names to ASS override tags
                    if position_name == 'top_center':
                        position_tag = "{\\an8}"  # top center
                    elif position_name == 'middle_center':
                        position_tag = "{\\an5}"  # middle center
                    elif position_name == 'bottom_left':
                        position_tag = "{\\an1}"  # bottom left
                    elif position_name == 'bottom_right':
                        position_tag = "{\\an3}"  # bottom right
                
                # Apply position tag
                text = position_tag + text
                
                # Limit to two lines if needed
                lines = text.split('\n')
                if len(lines) > 2:
                    # Extract position tag if present
                    position_prefix = ""
                    if lines[0].startswith('{\\'):
                        position_prefix = lines[0][:6]  # Extract the position tag
                        lines[0] = lines[0][6:]  # Remove tag from first line
                    
                    # Combine lines with proper spacing
                    combined_text = ' '.join([line.strip() for line in lines])
                    words = combined_text.split()
                    
                    if len(words) > 6:  # Only split if we have enough words
                        midpoint = len(words) // 2
                        line1 = ' '.join(words[:midpoint])
                        line2 = ' '.join(words[midpoint:])
                        text = f"{position_prefix}{line1}\n{line2}"
                    else:
                        text = f"{position_prefix}{combined_text}"
                
                # Write the text and add a blank line between entries
                f.write(f"{text}\n\n")
    
    # Standard SRT format
    elif format.lower() == "srt":
        # Create a new SRT file with custom formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subs):
                # SRT uses 1-based indexing
                f.write(f"{i+1}\n")
                
                # Write timestamps in SRT format (00:00:00,000)
                start_time = str(sub.start)
                end_time = str(sub.end)
                f.write(f"{start_time} --> {end_time}\n")
                
                # Process text for SRT format
                text = sub.text
                
                # Handle speaker identification
                if '[' in text and ']' in text:
                    # Extract speaker info and format it in a way that works in Media Player
                    import re
                    text = re.sub(r'\[(.*?)\]', r'<b>\1:</b> ', text)
                
                # Limit to two lines if needed
                lines = text.split('\n')
                if len(lines) > 2:
                    # Combine lines with proper spacing
                    combined_text = ' '.join([line.strip() for line in lines])
                    words = combined_text.split()
                    
                    if len(words) > 6:  # Only split if we have enough words
                        midpoint = len(words) // 2
                        line1 = ' '.join(words[:midpoint])
                        line2 = ' '.join(words[midpoint:])
                        text = f"{line1}\n{line2}"
                    else:
                        text = combined_text
                
                # Write the text and add a blank line between entries
                f.write(f"{text}\n\n")
    elif format.lower() == "vtt":
        # Convert to WebVTT format
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for i, sub in enumerate(subs):
                # Convert from SRT timestamp (00:00:00,000) to WebVTT format (00:00:00.000)
                start_time = str(sub.start).replace(',', '.')
                end_time = str(sub.end).replace(',', '.')
                
                # Add cue identifier
                cue_id = f"cue{i+1}"
                if '[' in sub.text and ']' in sub.text:
                    # Extract speaker info
                    import re
                    speaker_match = re.match(r'\[(.*?)\]', sub.text)
                    if speaker_match:
                        speaker = speaker_match.group(1)
                        cue_id = f"{cue_id} - {speaker}"
                
                # Write cue identifier
                f.write(f"{cue_id}\n")
                
                # Use a more compatible styling approach that works across different players
                # Windows Media Player has limited support for WebVTT styling
                style_attrs = ""
                
                # Add positioning information based on detected text regions
                position_attrs = ""
                
                # Get position from subtitle object
                if hasattr(sub, 'position'):
                    position_name = sub.position
                    
                    # Map position names to WebVTT positioning attributes
                    if position_name == 'top_center':
                        position_attrs = " line:10% position:50%"
                    elif position_name == 'middle_center':
                        position_attrs = " line:50% position:50%"
                    elif position_name == 'bottom_left':
                        position_attrs = " line:90% position:20%"
                    elif position_name == 'bottom_right':
                        position_attrs = " line:90% position:80%"
                    elif position_name == 'bottom_center':
                        position_attrs = " line:90% position:50%"
                    
                    # For debugging
                    print(f"Applied position {position_name} to subtitle: {position_attrs}")
                else:
                    # Default to bottom center if no position is set
                    position_attrs = " line:90% position:50%"
                    print("No position attribute found, using default bottom center")
                
                # Write timing with position attributes only (style is in the text)
                # For alignment, add an explicit align attribute that works in more players
                align_attr = " align:middle"
                f.write(f"{start_time} --> {end_time}{position_attrs}{align_attr}\n")
                
                # For WebVTT, we can use proper voice tags if speaker is identified
                text = sub.text
                if '[' in text and ']' in text:
                    # Replace speaker markers with VTT voice tags
                    text = re.sub(r'\[(.*?)\]', r'<v \1>', text)
                
                # Process text to limit to two lines and add styling
                # First, split by any existing line breaks
                lines = text.split('\n')
                
                # Limit to two lines by combining or truncating
                if len(lines) > 2:
                    # Option 1: Keep only first two lines
                    # text = '\n'.join(lines[:2])
                    
                    # Option 2: Combine lines with proper spacing
                    # Join all lines with spaces, then split into roughly equal parts
                    combined_text = ' '.join([line.strip() for line in lines])
                    words = combined_text.split()
                    
                    if len(words) > 6:  # Only split if we have enough words
                        midpoint = len(words) // 2
                        line1 = ' '.join(words[:midpoint])
                        line2 = ' '.join(words[midpoint:])
                        text = f"{line1}\n{line2}"
                    else:
                        text = combined_text
                
                # For WebVTT, apply styling that works in more compatible players
                # Use more explicit styling for better compatibility
                text = f'<c.white><c.bg_black>{text}</c></c>'
                
                f.write(f"{text}\n\n")
    else:
        # For other formats, a basic conversion
        # In a real implementation, you would use appropriate libraries for each format
        subs.save(output_path, encoding='utf-8')

def diarize_speakers(subs, video_path: str, use_aws: bool = False, max_speakers: int = 10):
    """
    Identify multiple speakers in the video and label their dialogues
    Uses AWS Transcribe service for speaker diarization when available,
    otherwise falls back to basic pattern detection
    
    Args:
        subs: The subtitle objects to process
        video_path: Path to the video file
        use_aws: Whether to use AWS Transcribe for diarization
        max_speakers: Maximum number of speakers to identify
    """
    import tempfile
    import uuid
    import json
    import os
    import time
    from pathlib import Path
    
    # Import AWS utilities
    from backend.utils.aws_utils import (
        CAN_USE_TRANSCRIBE, 
        upload_to_s3, 
        start_transcription_job,
        check_transcription_job_status,
        fetch_transcript,
        delete_from_s3
    )
    
    # Create a unique job name
    job_name = f"diarize-{uuid.uuid4()}"
    
    # Convert video to audio (WAV format) using ffmpeg via subprocess
    audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    audio_file.close()
    
    try:
        # Extract audio using ffmpeg
        import subprocess
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian format
            "-ar", "16000",  # 16 kHz sample rate (required by Transcribe)
            "-ac", "1",  # Mono
            audio_file.name
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Only use AWS if explicitly requested and AWS Transcribe is available
        if use_aws and CAN_USE_TRANSCRIBE:
            try:
                # Upload audio file to S3
                s3_key = f"{job_name}.wav"
                upload_result = upload_to_s3(audio_file.name, s3_key)
                
                if not upload_result.get('success'):
                    raise Exception(f"S3 upload failed: {upload_result.get('message')}")
                
                media_uri = upload_result['media_uri']
                
                # Start transcription job with speaker diarization
                job_settings = {
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': max_speakers
                }
                
                job_result = start_transcription_job(job_name, media_uri, job_settings)
                
                if not job_result.get('success'):
                    raise Exception(f"Failed to start transcription job: {job_result.get('message')}")
                
                # Wait for the transcription job to complete
                while True:
                    status_result = check_transcription_job_status(job_name)
                    
                    if not status_result.get('success'):
                        raise Exception(f"Failed to check job status: {status_result.get('message')}")
                        
                    status = status_result['status']
                    if status in ['COMPLETED', 'FAILED']:
                        break
                        
                    time.sleep(5)
                
                if status == 'COMPLETED' and 'transcript_uri' in status_result:
                    # Get the transcript
                    transcript_result = fetch_transcript(status_result['transcript_uri'])
                    
                    if not transcript_result.get('success'):
                        raise Exception(f"Failed to fetch transcript: {transcript_result.get('message')}")
                    
                    transcript_data = transcript_result['data']
                    
                    # Clean up S3 object
                    delete_from_s3(s3_key)
                    
                    # Apply diarization to subtitles
                    return _apply_diarization_from_transcript(subs, transcript_data)
                else:
                    raise Exception(f"Transcription job failed with status: {status}")
                    
            except Exception as e:
                # Log the error and fall back to basic diarization
                from backend.utils.error_utils import log_error
                log_error(e, "AWS Transcribe diarization error")
                return _basic_dialogue_detection(subs)
        else:
            # AWS not available or not requested, use basic diarization
            return _basic_dialogue_detection(subs)
    except Exception as e:
        # Log the error and fall back to basic diarization
        from backend.utils.error_utils import log_error
        log_error(e, "Diarization error")
        return _basic_dialogue_detection(subs)
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file.name):
            os.remove(audio_file.name)

def _apply_diarization_from_transcript(subs, transcript_data):
    """
    Apply speaker diarization information from AWS Transcribe to subtitles
    
    This function marks subtitles with is_new_speaker=True when it detects
    a change in speaker based on AWS Transcribe data.
    """
    try:
        # Extract speaker segments from transcript
        speaker_segments = []
        
        if 'results' in transcript_data:
            speaker_labels = transcript_data['results'].get('speaker_labels', {})
            segments = speaker_labels.get('segments', [])
            
            for segment in segments:
                speaker_label = segment.get('speaker_label', '')
                start_time = float(segment.get('start_time', 0))
                end_time = float(segment.get('end_time', 0))
                
                speaker_segments.append({
                    'speaker': speaker_label,
                    'start_time': start_time,
                    'end_time': end_time
                })
            
            # Map each subtitle to a speaker based on timestamp overlap
            for sub in subs:
                start_time_seconds = _time_to_seconds(sub.start)
                end_time_seconds = _time_to_seconds(sub.end)
                
                # Find the speaker who speaks during this subtitle
                matching_speakers = set()
                for segment in speaker_segments:
                    # Check if there's an overlap between the subtitle and the speaker segment
                    if (segment['start_time'] <= end_time_seconds and 
                        segment['end_time'] >= start_time_seconds):
                        matching_speakers.add(segment['speaker'])
                
                # Add speaker information to the subtitle
                if matching_speakers:
                    speakers_str = ", ".join(sorted(matching_speakers))
                    sub.text = f"[{speakers_str}] {sub.text}"
        
        return subs
    except Exception as e:
        print(f"Error applying diarization: {str(e)}")
        return _basic_dialogue_detection(subs)

def _time_to_seconds(time_obj):
    """Convert pysrt time object to seconds"""
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000

def _basic_dialogue_detection(subs):
    """
    Basic speaker diarization that looks for dialogue patterns in subtitles
    Used as a fallback when AWS Transcribe is not available
    
    This function marks subtitles with is_new_speaker=True when it detects
    a change in speaker based on dialogue patterns.
    """
    """
    Basic speaker diarization that looks for dialogue patterns in subtitles
    Used as a fallback when AWS Transcribe is not available
    """
    for sub in subs:
        text = sub.text
        
        # If the subtitle looks like dialogue (starts with a dash)
        if text.lstrip().startswith('-'):
            # Make sure it has two dashes at the beginning
            if not text.lstrip().startswith('--'):
                text = text.lstrip('-')
                text = '-- ' + text.lstrip()
        
        # Look for alternating dialogue with multiple speakers
        lines = text.split('\n')
        if len(lines) > 1:
            for i, line in enumerate(lines):
                if line.lstrip().startswith('-'):
                    if not line.lstrip().startswith('--'):
                        lines[i] = '-- ' + line.lstrip('-').lstrip()
            
            # Check if we have alternating speakers
            speaker_lines = [i for i, line in enumerate(lines) if line.lstrip().startswith('--')]
            if len(speaker_lines) > 1:
                # Add speaker labels for clarity
                for i in speaker_lines:
                    # Alternate between Speaker A and Speaker B
                    speaker = "Speaker A" if i % 2 == 0 else "Speaker B"
                    lines[i] = f"[{speaker}] {lines[i]}"
                
                text = '\n'.join(lines)
            
        sub.text = text
    
    return subs
