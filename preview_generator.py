
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess
import tempfile
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class PreviewGenerator:
    def __init__(self, temp_folder: str):
        self.temp_folder = temp_folder
        self.preview_cache = {}
        
    def generate_face_preview(self, face_path: str, max_size: Tuple[int, int] = (300, 300)) -> str:
        """Generate a preview thumbnail for face input"""
        try:
            preview_filename = f"face_preview_{os.path.basename(face_path)}.jpg"
            preview_path = os.path.join(self.temp_folder, preview_filename)
            
            if face_path.lower().endswith(('.mp4', '.avi', '.mov')):
                # Video file - extract first frame
                cap = cv2.VideoCapture(face_path)
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    # Resize frame
                    h, w = frame.shape[:2]
                    scale = min(max_size[0]/w, max_size[1]/h)
                    new_w, new_h = int(w*scale), int(h*scale)
                    frame = cv2.resize(frame, (new_w, new_h))
                    
                    # Save preview
                    cv2.imwrite(preview_path, frame)
                else:
                    raise Exception("Could not extract frame from video")
            else:
                # Image file
                img = cv2.imread(face_path)
                if img is None:
                    raise Exception("Could not load image")
                
                # Resize image
                h, w = img.shape[:2]
                scale = min(max_size[0]/w, max_size[1]/h)
                new_w, new_h = int(w*scale), int(h*scale)
                img = cv2.resize(img, (new_w, new_h))
                
                # Save preview
                cv2.imwrite(preview_path, img)
            
            return preview_path
            
        except Exception as e:
            logger.error(f"Error generating face preview: {e}")
            return None
    
    def generate_audio_waveform(self, audio_path: str, width: int = 400, height: int = 100) -> str:
        """Generate a waveform visualization for audio input"""
        try:
            preview_filename = f"audio_preview_{os.path.basename(audio_path)}.png"
            preview_path = os.path.join(self.temp_folder, preview_filename)
            
            # Extract audio data using ffmpeg
            temp_wav = os.path.join(self.temp_folder, "temp_audio_preview.wav")
            cmd = f'ffmpeg -y -i "{audio_path}" -ac 1 -ar 16000 "{temp_wav}"'
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            
            # Read audio data
            import librosa
            y, sr = librosa.load(temp_wav, sr=16000)
            
            # Generate waveform
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Downsample audio for visualization
            samples_per_pixel = len(y) // width
            if samples_per_pixel > 0:
                waveform_data = []
                for i in range(width):
                    start_idx = i * samples_per_pixel
                    end_idx = min(start_idx + samples_per_pixel, len(y))
                    if start_idx < len(y):
                        chunk = y[start_idx:end_idx]
                        waveform_data.append(np.max(np.abs(chunk)) if len(chunk) > 0 else 0)
                    else:
                        waveform_data.append(0)
                
                # Draw waveform
                center_y = height // 2
                for i, amplitude in enumerate(waveform_data):
                    wave_height = int(amplitude * center_y)
                    draw.line([i, center_y - wave_height, i, center_y + wave_height], 
                             fill='blue', width=1)
            
            # Add labels
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            duration = len(y) / sr
            draw.text((5, 5), f"Duration: {duration:.1f}s", fill='black', font=font)
            draw.text((5, height-20), f"Sample Rate: {sr}Hz", fill='black', font=font)
            
            img.save(preview_path)
            
            # Clean up temp file
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            
            return preview_path
            
        except Exception as e:
            logger.error(f"Error generating audio waveform: {e}")
            return None
    
    def generate_comparison_preview(self, original_face: str, result_video: str, 
                                  timestamp: float = 1.0) -> str:
        """Generate a before/after comparison preview"""
        try:
            preview_filename = f"comparison_{os.path.basename(result_video)}.jpg"
            preview_path = os.path.join(self.temp_folder, preview_filename)
            
            # Extract frame from original
            if original_face.lower().endswith(('.mp4', '.avi', '.mov')):
                cap = cv2.VideoCapture(original_face)
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, original_frame = cap.read()
                cap.release()
                if not ret:
                    cap = cv2.VideoCapture(original_face)
                    ret, original_frame = cap.read()
                    cap.release()
            else:
                original_frame = cv2.imread(original_face)
            
            # Extract frame from result
            cap = cv2.VideoCapture(result_video)
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, result_frame = cap.read()
            cap.release()
            if not ret:
                cap = cv2.VideoCapture(result_video)
                ret, result_frame = cap.read()
                cap.release()
            
            if original_frame is None or result_frame is None:
                raise Exception("Could not extract frames for comparison")
            
            # Resize frames to same height
            target_height = 300
            orig_h, orig_w = original_frame.shape[:2]
            result_h, result_w = result_frame.shape[:2]
            
            orig_scale = target_height / orig_h
            result_scale = target_height / result_h
            
            orig_new_w = int(orig_w * orig_scale)
            result_new_w = int(result_w * result_scale)
            
            original_frame = cv2.resize(original_frame, (orig_new_w, target_height))
            result_frame = cv2.resize(result_frame, (result_new_w, target_height))
            
            # Create comparison image
            total_width = orig_new_w + result_new_w + 20  # 20px gap
            comparison = np.ones((target_height + 60, total_width, 3), dtype=np.uint8) * 255
            
            # Place original frame
            comparison[30:30+target_height, 0:orig_new_w] = original_frame
            
            # Place result frame
            comparison[30:30+target_height, orig_new_w+20:orig_new_w+20+result_new_w] = result_frame
            
            # Add labels
            cv2.putText(comparison, "Original", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 0, 0), 2)
            cv2.putText(comparison, "Lip-Synced", (orig_new_w + 30, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            
            # Add divider line
            cv2.line(comparison, (orig_new_w + 10, 0), (orig_new_w + 10, target_height + 60), 
                    (200, 200, 200), 2)
            
            cv2.imwrite(preview_path, comparison)
            return preview_path
            
        except Exception as e:
            logger.error(f"Error generating comparison preview: {e}")
            return None
    
    def generate_grid_preview(self, file_paths: List[str], grid_size: Tuple[int, int] = (3, 3)) -> str:
        """Generate a grid preview of multiple files"""
        try:
            preview_filename = f"grid_preview_{len(file_paths)}_files.jpg"
            preview_path = os.path.join(self.temp_folder, preview_filename)
            
            rows, cols = grid_size
            cell_width, cell_height = 150, 150
            gap = 10
            
            total_width = cols * cell_width + (cols - 1) * gap
            total_height = rows * cell_height + (rows - 1) * gap
            
            grid_img = np.ones((total_height, total_width, 3), dtype=np.uint8) * 240
            
            for i, file_path in enumerate(file_paths[:rows*cols]):
                row = i // cols
                col = i % cols
                
                x = col * (cell_width + gap)
                y = row * (cell_height + gap)
                
                try:
                    # Load and resize image/video frame
                    if file_path.lower().endswith(('.mp4', '.avi', '.mov')):
                        cap = cv2.VideoCapture(file_path)
                        ret, frame = cap.read()
                        cap.release()
                        if ret:
                            img = frame
                        else:
                            continue
                    else:
                        img = cv2.imread(file_path)
                        if img is None:
                            continue
                    
                    # Resize to fit cell
                    img = cv2.resize(img, (cell_width, cell_height))
                    grid_img[y:y+cell_height, x:x+cell_width] = img
                    
                    # Add filename label
                    filename = os.path.basename(file_path)
                    if len(filename) > 15:
                        filename = filename[:12] + "..."
                    
                    cv2.putText(grid_img, filename, (x + 5, y + cell_height - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
                    
                except Exception as e:
                    logger.warning(f"Could not process file {file_path} for grid: {e}")
                    continue
            
            cv2.imwrite(preview_path, grid_img)
            return preview_path
            
        except Exception as e:
            logger.error(f"Error generating grid preview: {e}")
            return None
    
    def get_video_info(self, video_path: str) -> Dict:
        """Extract video information"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            info = {
                'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            }
            
            cap.release()
            return info
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}
    
    def cleanup_previews(self, max_age_hours: int = 24):
        """Clean up old preview files"""
        try:
            import time
            current_time = time.time()
            
            for filename in os.listdir(self.temp_folder):
                if filename.startswith(('face_preview_', 'audio_preview_', 'comparison_', 'grid_preview_')):
                    file_path = os.path.join(self.temp_folder, filename)
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_hours * 3600:  # Convert hours to seconds
                        os.remove(file_path)
                        logger.info(f"Cleaned up old preview: {filename}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up previews: {e}")

# Global preview generator instance
preview_generator = None

def get_preview_generator(temp_folder: str) -> PreviewGenerator:
    """Get or create the global preview generator instance"""
    global preview_generator
    if preview_generator is None:
        preview_generator = PreviewGenerator(temp_folder)
    return preview_generator
